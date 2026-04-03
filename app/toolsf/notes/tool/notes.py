from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.notes.notes")
logger.debug("Loaded tool module: notes.notes")

import json
from pathlib import Path
from app.utils.groq import tool

_DB = Path(__file__).resolve().parent / "notes.json"


def _load():
    if _DB.exists():
        return json.loads(_DB.read_text(encoding="utf-8"))
    return []


def _save(items):
    _DB.write_text(json.dumps(items, indent=2), encoding="utf-8")


@tool(
    name="note_add",
    description="Add a note.",
    params={
        "title": {"type": "string"},
        "content": {"type": "string"},
        "tags": {"type": "array"},
    },
)
def note_add(title: str, content: str, tags: list[str] | None = None):
    items = _load()
    note = {"id": len(items) + 1, "title": title, "content": content, "tags": tags or []}
    items.append(note)
    _save(items)
    return note


@tool(
    name="note_list",
    description="List notes.",
    params={},
)
def note_list():
    return _load()


@tool(
    name="note_get",
    description="Get a note by id.",
    params={"id": {"type": "integer"}},
)
def note_get(id: int):
    for n in _load():
        if n["id"] == id:
            return n
    return {}


@tool(
    name="note_delete",
    description="Delete a note.",
    params={"id": {"type": "integer"}},
)
def note_delete(id: int):
    items = [n for n in _load() if n["id"] != id]
    _save(items)
    return {"ok": True}


@tool(
    name="note_search",
    description="Search notes by keyword.",
    params={"query": {"type": "string"}, "tag": {"type": "string", "description": "Tag filter (optional)"}},
)
def note_search(query: str, tag: str = ""):
    q = query.lower()
    out = [n for n in _load() if q in n["title"].lower() or q in n["content"].lower()]
    if tag:
        out = [n for n in out if tag in n.get("tags", [])]
    return out


@tool(
    name="note_update",
    description="Update a note by id.",
    params={
        "id": {"type": "integer"},
        "title": {"type": "string", "description": "New title (optional)"},
        "content": {"type": "string", "description": "New content (optional)"},
        "tags": {"type": "array", "description": "Replace tags (optional)"},
    },
)
def note_update(id: int, title: str = "", content: str = "", tags: list[str] | None = None):
    items = _load()
    for n in items:
        if n["id"] == id:
            if title:
                n["title"] = title
            if content:
                n["content"] = content
            if tags is not None:
                n["tags"] = tags
    _save(items)
    return {"ok": True}


@tool(
    name="note_tag_add",
    description="Add a tag to a note.",
    params={"id": {"type": "integer"}, "tag": {"type": "string"}},
)
def note_tag_add(id: int, tag: str):
    items = _load()
    for n in items:
        if n["id"] == id:
            tags = set(n.get("tags", []))
            tags.add(tag)
            n["tags"] = list(tags)
    _save(items)
    return {"ok": True}


@tool(
    name="note_tag_remove",
    description="Remove a tag from a note.",
    params={"id": {"type": "integer"}, "tag": {"type": "string"}},
)
def note_tag_remove(id: int, tag: str):
    items = _load()
    for n in items:
        if n["id"] == id:
            n["tags"] = [t for t in n.get("tags", []) if t != tag]
    _save(items)
    return {"ok": True}
