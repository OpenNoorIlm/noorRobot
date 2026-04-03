from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.todo.todo")
logger.debug("Loaded tool module: todo.todo")

import json
from pathlib import Path
from app.utils.groq import tool

_DB = Path(__file__).resolve().parent / "todo.json"


def _load():
    if _DB.exists():
        return json.loads(_DB.read_text(encoding="utf-8"))
    return []


def _save(items):
    _DB.write_text(json.dumps(items, indent=2), encoding="utf-8")


@tool(
    name="todo_add",
    description="Add a todo item.",
    params={
        "title": {"type": "string"},
        "due": {"type": "string"},
        "priority": {"type": "string", "description": "low|medium|high (optional)"},
    },
)
def todo_add(title: str, due: str = "", priority: str = ""):
    items = _load()
    item = {"id": len(items) + 1, "title": title, "due": due, "priority": priority, "done": False}
    items.append(item)
    _save(items)
    return item


@tool(
    name="todo_list",
    description="List todo items.",
    params={},
)
def todo_list():
    return _load()


@tool(
    name="todo_done",
    description="Mark todo item as done.",
    params={"id": {"type": "integer"}},
)
def todo_done(id: int):
    items = _load()
    for it in items:
        if it["id"] == id:
            it["done"] = True
    _save(items)
    return {"ok": True}


@tool(
    name="todo_delete",
    description="Delete a todo item.",
    params={"id": {"type": "integer"}},
)
def todo_delete(id: int):
    items = [it for it in _load() if it["id"] != id]
    _save(items)
    return {"ok": True}


@tool(
    name="todo_update",
    description="Update a todo item.",
    params={
        "id": {"type": "integer"},
        "title": {"type": "string", "description": "New title (optional)"},
        "due": {"type": "string", "description": "New due date (optional)"},
        "priority": {"type": "string", "description": "low|medium|high (optional)"},
        "done": {"type": "boolean", "description": "Set done (optional)"},
    },
)
def todo_update(id: int, title: str = "", due: str = "", priority: str = "", done: bool | None = None):
    items = _load()
    for it in items:
        if it["id"] == id:
            if title:
                it["title"] = title
            if due:
                it["due"] = due
            if priority:
                it["priority"] = priority
            if done is not None:
                it["done"] = bool(done)
    _save(items)
    return {"ok": True}


@tool(
    name="todo_search",
    description="Search todos by keyword.",
    params={"query": {"type": "string"}},
)
def todo_search(query: str):
    q = query.lower()
    return [it for it in _load() if q in it.get("title", "").lower()]


@tool(
    name="todo_list_filter",
    description="List todos with optional filters.",
    params={
        "done": {"type": "boolean", "description": "Filter by done (optional)"},
        "priority": {"type": "string", "description": "Filter by priority (optional)"},
    },
)
def todo_list_filter(done: bool | None = None, priority: str = ""):
    items = _load()
    if done is not None:
        items = [it for it in items if it.get("done") == bool(done)]
    if priority:
        items = [it for it in items if it.get("priority") == priority]
    return items


@tool(
    name="todo_clear_done",
    description="Delete all completed todos.",
    params={},
)
def todo_clear_done():
    items = [it for it in _load() if not it.get("done")]
    _save(items)
    return {"ok": True}
