from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.calendar.calendar")
logger.debug("Loaded tool module: calendar.calendar")

from datetime import datetime
from pathlib import Path
from app.utils.groq import tool


def _ics_dt(dt: str):
    return datetime.fromisoformat(dt.replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%SZ")


@tool(
    name="calendar_create_event",
    description="Create an event in an ICS calendar file.",
    params={
        "calendar_path": {"type": "string", "description": "ICS file path"},
        "title": {"type": "string", "description": "Event title"},
        "start": {"type": "string", "description": "Start ISO datetime"},
        "end": {"type": "string", "description": "End ISO datetime"},
        "description": {"type": "string", "description": "Description (optional)"},
        "location": {"type": "string", "description": "Location (optional)"},
        "uid": {"type": "string", "description": "Event UID (optional)"},
    },
)
def calendar_create_event(calendar_path: str, title: str, start: str, end: str, description: str = "", location: str = "", uid: str = ""):
    p = Path(calendar_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//NoorRobot//EN\nEND:VCALENDAR\n", encoding="utf-8")
    data = p.read_text(encoding="utf-8")
    vevent = "\n".join([
        "BEGIN:VEVENT",
        f"UID:{uid or title}-{_ics_dt(start)}",
        f"SUMMARY:{title}",
        f"DTSTART:{_ics_dt(start)}",
        f"DTEND:{_ics_dt(end)}",
        f"DESCRIPTION:{description}",
        f"LOCATION:{location}",
        "END:VEVENT",
    ])
    data = data.replace("END:VCALENDAR", vevent + "\nEND:VCALENDAR")
    p.write_text(data, encoding="utf-8")
    return {"ok": True}


@tool(
    name="calendar_list_events",
    description="List events from an ICS calendar file.",
    params={"calendar_path": {"type": "string", "description": "ICS file path"}},
)
def calendar_list_events(calendar_path: str):
    p = Path(calendar_path)
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    events = []
    cur = {}
    in_event = False
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            cur = {}
        elif line == "END:VEVENT":
            if cur:
                events.append(cur)
            in_event = False
        elif in_event and ":" in line:
            k, v = line.split(":", 1)
            cur[k] = v
    return events


@tool(
    name="calendar_find_events",
    description="Find events by keyword in summary/description.",
    params={
        "calendar_path": {"type": "string", "description": "ICS file path"},
        "query": {"type": "string", "description": "Keyword"},
    },
)
def calendar_find_events(calendar_path: str, query: str):
    q = query.lower()
    events = calendar_list_events(calendar_path)
    out = []
    for e in events:
        summary = str(e.get("SUMMARY", "")).lower()
        desc = str(e.get("DESCRIPTION", "")).lower()
        if q in summary or q in desc:
            out.append(e)
    return out


@tool(
    name="calendar_delete_event",
    description="Delete an event by UID.",
    params={
        "calendar_path": {"type": "string", "description": "ICS file path"},
        "uid": {"type": "string", "description": "Event UID"},
    },
)
def calendar_delete_event(calendar_path: str, uid: str):
    p = Path(calendar_path)
    if not p.exists():
        return {"ok": False}
    lines = p.read_text(encoding="utf-8").splitlines()
    out_lines = []
    in_event = False
    keep = True
    cur_uid = ""
    for line in lines:
        if line == "BEGIN:VEVENT":
            in_event = True
            keep = True
            cur_uid = ""
            out_lines.append(line)
            continue
        if line == "END:VEVENT":
            if keep:
                out_lines.append(line)
            in_event = False
            continue
        if in_event and line.startswith("UID:"):
            cur_uid = line.split(":", 1)[1]
            if cur_uid == uid:
                keep = False
            if keep:
                out_lines.append(line)
            continue
        if not in_event:
            out_lines.append(line)
        else:
            if keep:
                out_lines.append(line)
    p.write_text("\n".join(out_lines), encoding="utf-8")
    return {"ok": True}
