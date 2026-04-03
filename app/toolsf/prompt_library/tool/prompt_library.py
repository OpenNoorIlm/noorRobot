from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.prompt_library.prompt_library")
logger.debug("Loaded tool module: prompt_library.prompt_library")

import json
from pathlib import Path
from app.utils.groq import tool

_DB = Path(__file__).resolve().parent / "prompts.json"


def _load():
    if _DB.exists():
        return json.loads(_DB.read_text(encoding="utf-8"))
    return []


def _save(items):
    _DB.write_text(json.dumps(items, indent=2), encoding="utf-8")


@tool(
    name="prompt_add",
    description="Add a prompt template.",
    params={"name": {"type": "string"}, "content": {"type": "string"}, "tags": {"type": "array"}},
)
def prompt_add(name: str, content: str, tags: list[str] | None = None):
    items = _load()
    items.append({"name": name, "content": content, "tags": tags or []})
    _save(items)
    return {"ok": True}


@tool(
    name="prompt_list",
    description="List prompt templates.",
    params={},
)
def prompt_list():
    return _load()


@tool(
    name="prompt_get",
    description="Get prompt template by name.",
    params={"name": {"type": "string"}},
)
def prompt_get(name: str):
    for p in _load():
        if p["name"] == name:
            return p
    return {}


@tool(
    name="prompt_delete",
    description="Delete a prompt template.",
    params={"name": {"type": "string"}},
)
def prompt_delete(name: str):
    items = [p for p in _load() if p["name"] != name]
    _save(items)
    return {"ok": True}


@tool(
    name="prompt_update",
    description="Update a prompt template by name.",
    params={
        "name": {"type": "string"},
        "content": {"type": "string", "description": "New content (optional)"},
        "tags": {"type": "array", "description": "New tags (optional)"},
    },
)
def prompt_update(name: str, content: str = "", tags: list[str] | None = None):
    items = _load()
    for p in items:
        if p["name"] == name:
            if content:
                p["content"] = content
            if tags is not None:
                p["tags"] = tags
            _save(items)
            return p
    return {}


@tool(
    name="prompt_search",
    description="Search prompt templates by keyword or tag.",
    params={
        "query": {"type": "string"},
        "tag": {"type": "string", "description": "Tag filter (optional)"},
    },
)
def prompt_search(query: str, tag: str = ""):
    q = query.lower()
    items = [p for p in _load() if q in p.get("name", "").lower() or q in p.get("content", "").lower()]
    if tag:
        items = [p for p in items if tag in p.get("tags", [])]
    return items


@tool(
    name="prompt_export",
    description="Export prompt library to a JSON file.",
    params={"path": {"type": "string"}},
)
def prompt_export(path: str):
    data = _load()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(p.resolve())


@tool(
    name="prompt_import",
    description="Import prompt templates from a JSON file.",
    params={
        "path": {"type": "string"},
        "merge": {"type": "boolean", "description": "Merge with existing (optional)"},
    },
)
def prompt_import(path: str, merge: bool = True):
    p = Path(path)
    if not p.exists():
        return {"ok": False}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not merge:
        _save(data)
        return {"ok": True, "count": len(data)}
    items = _load()
    names = {i["name"] for i in items}
    for it in data:
        if it.get("name") not in names:
            items.append(it)
    _save(items)
    return {"ok": True, "count": len(items)}
