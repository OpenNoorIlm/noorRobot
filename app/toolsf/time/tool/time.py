from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.time.time")
logger.debug("Loaded tool module: time.time")

import json
import threading
import time as _time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from pathlib import Path

from app.utils.groq import tool, FUNCTIONS


_jobs: dict[str, dict[str, Any]] = {}
_PERSIST_PATH = Path(__file__).resolve().parent / "time_jobs.json"

try:
    from croniter import croniter  # type: ignore
except Exception:  # pragma: no cover
    croniter = None


def _parse_dt(dt_str: str) -> datetime:
    if not dt_str:
        raise ValueError("time must be provided")
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _now(tz: str = "") -> datetime:
    if tz:
        if tz.upper() == "UTC":
            return datetime.now(timezone.utc)
        # accept offsets like +05:30
        if tz.startswith(("+", "-")) and len(tz) in (6, 5):
            hours = int(tz[1:3])
            minutes = int(tz[-2:])
            delta = timedelta(hours=hours, minutes=minutes)
            if tz.startswith("-"):
                delta = -delta
            return datetime.now(timezone(delta))
    return datetime.now().astimezone()


def _call_tool(tool_name: str, tool_params: dict | None):
    fn = FUNCTIONS.get(tool_name)
    if not fn:
        raise ValueError(f"Tool not found: {tool_name}")
    return fn(**(tool_params or {}))


def _serialize_jobs():
    data = []
    for job_id, info in _jobs.items():
        if info.get("status") in ("done", "cancelled"):
            continue
        item = {
            "job_id": job_id,
            "type": info.get("type"),
            "status": info.get("status"),
            "tool_name": info.get("tool_name"),
            "tool_params": info.get("tool_params", {}),
            "run_at": info.get("run_at"),
            "interval_seconds": info.get("interval_seconds"),
            "start_at": info.get("start_at"),
            "tz": info.get("tz"),
            "repeat_count": info.get("repeat_count"),
            "end_at": info.get("end_at"),
            "immediate": info.get("immediate"),
            "cron": info.get("cron"),
            "next_run": info.get("next_run"),
        }
        data.append(item)
    return data


def _persist_jobs():
    _PERSIST_PATH.write_text(json.dumps(_serialize_jobs(), indent=2), encoding="utf-8")


def _restore_jobs():
    if not _PERSIST_PATH.exists():
        return
    try:
        data = json.loads(_PERSIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    for item in data:
        if item.get("type") == "once":
            run_at = item.get("run_at") or ""
            if not run_at:
                continue
            dt = _parse_dt(run_at)
            if dt <= _now(item.get("tz", "")):
                continue
            time_schedule_once(
                tool_name=item.get("tool_name", ""),
                tool_params=item.get("tool_params", {}),
                run_at=run_at,
                tz=item.get("tz", ""),
            )
        elif item.get("type") == "interval":
            time_schedule_interval(
                tool_name=item.get("tool_name", ""),
                tool_params=item.get("tool_params", {}),
                interval_seconds=item.get("interval_seconds", 1),
                start_at=item.get("start_at", ""),
                tz=item.get("tz", ""),
                repeat_count=item.get("repeat_count"),
                end_at=item.get("end_at", ""),
                immediate=item.get("immediate", False),
            )
        elif item.get("type") == "cron":
            time_schedule_cron(
                tool_name=item.get("tool_name", ""),
                tool_params=item.get("tool_params", {}),
                cron=item.get("cron", ""),
                tz=item.get("tz", ""),
            )


_restore_jobs()


@tool(
    name="time_now",
    description="Get current time.",
    params={
        "tz": {"type": "string", "description": "Timezone: UTC or offset like +05:30 (optional)"},
        "format": {"type": "string", "description": "strftime format (optional)"},
        "epoch": {"type": "boolean", "description": "Return Unix epoch seconds (optional)"},
    },
)
def time_now(tz: str = "", format: str = "", epoch: bool = False):
    dt = _now(tz)
    if epoch:
        return int(dt.timestamp())
    if format:
        return dt.strftime(format)
    return dt.isoformat()


@tool(
    name="time_parse",
    description="Parse an ISO datetime string into components.",
    params={"iso": {"type": "string", "description": "ISO datetime string"}},
)
def time_parse(iso: str):
    dt = _parse_dt(iso)
    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "minute": dt.minute,
        "second": dt.second,
        "tzinfo": str(dt.tzinfo) if dt.tzinfo else "",
        "iso": dt.isoformat(),
        "epoch": int(dt.timestamp()),
    }


@tool(
    name="time_format",
    description="Format an ISO datetime using strftime.",
    params={
        "iso": {"type": "string", "description": "ISO datetime string"},
        "format": {"type": "string", "description": "strftime format"},
    },
)
def time_format(iso: str, format: str):
    dt = _parse_dt(iso)
    return dt.strftime(format)


@tool(
    name="time_add",
    description="Add seconds to a time and return ISO.",
    params={
        "iso": {"type": "string", "description": "ISO datetime string"},
        "seconds": {"type": "number", "description": "Seconds to add (can be negative)"},
    },
)
def time_add(iso: str, seconds: float):
    dt = _parse_dt(iso)
    return (dt + timedelta(seconds=float(seconds))).isoformat()


@tool(
    name="time_diff",
    description="Get difference in seconds between two times (b - a).",
    params={
        "start": {"type": "string", "description": "Start ISO datetime"},
        "end": {"type": "string", "description": "End ISO datetime"},
    },
)
def time_diff(start: str, end: str):
    a = _parse_dt(start)
    b = _parse_dt(end)
    return (b - a).total_seconds()


@tool(
    name="time_convert_tz",
    description="Convert a time to another timezone.",
    params={
        "iso": {"type": "string", "description": "ISO datetime string"},
        "tz": {"type": "string", "description": "Target tz: UTC or offset like +05:30"},
    },
)
def time_convert_tz(iso: str, tz: str):
    dt = _parse_dt(iso)
    target = _now(tz).tzinfo
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_now().tzinfo)
    return dt.astimezone(target).isoformat()


@tool(
    name="time_sleep",
    description="Sleep for N seconds (blocking).",
    params={"seconds": {"type": "number", "description": "Seconds to sleep"}},
)
def time_sleep(seconds: float):
    _time.sleep(max(0.0, float(seconds)))
    return {"ok": True}


@tool(
    name="time_schedule_once",
    description="Schedule a one-time tool call at a specific time or after delay.",
    params={
        "tool_name": {"type": "string", "description": "Tool to call"},
        "tool_params": {"type": "object", "description": "Tool params dict (optional)"},
        "run_at": {"type": "string", "description": "ISO datetime (optional)"},
        "delay_seconds": {"type": "number", "description": "Delay in seconds (optional)"},
        "tz": {"type": "string", "description": "Timezone for run_at: UTC or offset (optional)"},
    },
)
def time_schedule_once(
    tool_name: str,
    tool_params: dict | None = None,
    run_at: str = "",
    delay_seconds: float | None = None,
    tz: str = "",
):
    if not run_at and delay_seconds is None:
        raise ValueError("Provide run_at or delay_seconds.")

    if run_at:
        dt = _parse_dt(run_at)
        if tz and dt.tzinfo is None:
            dt = dt.replace(tzinfo=_now(tz).tzinfo)
        delay = max(0.0, (dt - _now(tz)).total_seconds())
    else:
        delay = max(0.0, float(delay_seconds))

    job_id = uuid.uuid4().hex

    def _task():
        try:
            result = _call_tool(tool_name, tool_params)
            _jobs[job_id]["last_result"] = result
        except Exception as e:
            _jobs[job_id]["last_error"] = str(e)
        finally:
            _jobs[job_id]["status"] = "done"
            _persist_jobs()

    timer = threading.Timer(delay, _task)
    _jobs[job_id] = {
        "type": "once",
        "status": "scheduled",
        "tool_name": tool_name,
        "tool_params": tool_params or {},
        "run_at": (_now(tz) + timedelta(seconds=delay)).isoformat(),
        "tz": tz,
        "run_in_seconds": delay,
        "timer": timer,
    }
    timer.daemon = True
    timer.start()
    _persist_jobs()
    return {"job_id": job_id, "run_in_seconds": delay}


@tool(
    name="time_schedule_interval",
    description="Schedule repeating tool calls every interval.",
    params={
        "tool_name": {"type": "string", "description": "Tool to call"},
        "tool_params": {"type": "object", "description": "Tool params dict (optional)"},
        "interval_seconds": {"type": "number", "description": "Repeat interval seconds"},
        "start_at": {"type": "string", "description": "ISO start time (optional)"},
        "tz": {"type": "string", "description": "Timezone for start_at (optional)"},
        "repeat_count": {"type": "integer", "description": "How many times to run (optional)"},
        "end_at": {"type": "string", "description": "ISO end time (optional)"},
        "immediate": {"type": "boolean", "description": "Run once immediately (default false)"},
    },
)
def time_schedule_interval(
    tool_name: str,
    tool_params: dict | None,
    interval_seconds: float,
    start_at: str = "",
    tz: str = "",
    repeat_count: int | None = None,
    end_at: str = "",
    immediate: bool = False,
):
    interval = max(0.1, float(interval_seconds))
    job_id = uuid.uuid4().hex
    stop_flag = {"stop": False}

    if start_at:
        dt = _parse_dt(start_at)
        if tz and dt.tzinfo is None:
            dt = dt.replace(tzinfo=_now(tz).tzinfo)
        start_delay = max(0.0, (dt - _now(tz)).total_seconds())
    else:
        start_delay = 0.0

    end_dt = _parse_dt(end_at) if end_at else None
    if end_dt and tz and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=_now(tz).tzinfo)

    def _loop():
        if start_delay:
            _time.sleep(start_delay)
        count = 0
        if immediate and not stop_flag["stop"]:
            try:
                _jobs[job_id]["last_result"] = _call_tool(tool_name, tool_params)
            except Exception as e:
                _jobs[job_id]["last_error"] = str(e)
            count += 1

        while not stop_flag["stop"]:
            if repeat_count is not None and count >= repeat_count:
                break
            if end_dt and _now(tz) >= end_dt:
                break
            _time.sleep(interval)
            if stop_flag["stop"]:
                break
            try:
                _jobs[job_id]["last_result"] = _call_tool(tool_name, tool_params)
            except Exception as e:
                _jobs[job_id]["last_error"] = str(e)
            count += 1

        _jobs[job_id]["status"] = "done"
        _persist_jobs()

    t = threading.Thread(target=_loop, daemon=True)
    _jobs[job_id] = {
        "type": "interval",
        "status": "scheduled",
        "tool_name": tool_name,
        "tool_params": tool_params or {},
        "interval_seconds": interval,
        "start_at": start_at,
        "tz": tz,
        "repeat_count": repeat_count,
        "end_at": end_at,
        "immediate": immediate,
        "thread": t,
        "stop_flag": stop_flag,
    }
    t.start()
    _persist_jobs()
    return {"job_id": job_id, "interval_seconds": interval}


@tool(
    name="time_cancel",
    description="Cancel a scheduled job.",
    params={"job_id": {"type": "string", "description": "Job id"}},
)
def time_cancel(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return {"ok": False, "error": "Job not found"}
    if job.get("type") == "once":
        timer = job.get("timer")
        if timer:
            timer.cancel()
    if job.get("type") == "interval":
        job.get("stop_flag", {}).update({"stop": True})
    job["status"] = "cancelled"
    _persist_jobs()
    return {"ok": True}


@tool(
    name="time_schedule_cancel",
    description="Cancel a scheduled job (alias of time_cancel).",
    params={"job_id": {"type": "string", "description": "Job id"}},
)
def time_schedule_cancel(job_id: str):
    return time_cancel(job_id)


@tool(
    name="time_list_jobs",
    description="List scheduled jobs.",
    params={},
)
def time_list_jobs():
    out = []
    for job_id, info in _jobs.items():
        out.append(
            {
                "job_id": job_id,
                "type": info.get("type"),
                "status": info.get("status"),
                "tool_name": info.get("tool_name"),
            }
        )
    return out


@tool(
    name="time_schedule_cron",
    description="Schedule tool calls using a cron expression.",
    params={
        "tool_name": {"type": "string", "description": "Tool to call"},
        "tool_params": {"type": "object", "description": "Tool params dict (optional)"},
        "cron": {"type": "string", "description": "Cron expression (5 fields)"},
        "tz": {"type": "string", "description": "Timezone for cron (optional)"},
    },
)
def time_schedule_cron(
    tool_name: str,
    tool_params: dict | None = None,
    cron: str = "",
    tz: str = "",
):
    if croniter is None:
        raise RuntimeError("croniter not installed. Install it to use cron scheduling.")
    if not cron:
        raise ValueError("cron is required")

    job_id = uuid.uuid4().hex
    stop_flag = {"stop": False}

    def _loop():
        base = _now(tz)
        it = croniter(cron, base)
        while not stop_flag["stop"]:
            next_dt = it.get_next(datetime)
            _jobs[job_id]["next_run"] = next_dt.isoformat()
            _persist_jobs()
            delay = max(0.0, (next_dt - _now(tz)).total_seconds())
            _time.sleep(delay)
            if stop_flag["stop"]:
                break
            try:
                _jobs[job_id]["last_result"] = _call_tool(tool_name, tool_params)
            except Exception as e:
                _jobs[job_id]["last_error"] = str(e)

        _jobs[job_id]["status"] = "done"
        _persist_jobs()

    t = threading.Thread(target=_loop, daemon=True)
    _jobs[job_id] = {
        "type": "cron",
        "status": "scheduled",
        "tool_name": tool_name,
        "tool_params": tool_params or {},
        "cron": cron,
        "tz": tz,
        "thread": t,
        "stop_flag": stop_flag,
    }
    t.start()
    _persist_jobs()
    return {"job_id": job_id, "cron": cron}
