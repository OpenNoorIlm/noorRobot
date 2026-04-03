from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.rag_ingest.rag_ingest")
logger.debug("Loaded tool module: rag_ingest.rag_ingest")

import json
from pathlib import Path
from app.utils.groq import tool

_DB = Path(__file__).resolve().parent / "rag_index.json"


def _save(data):
    _DB.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load():
    if _DB.exists():
        return json.loads(_DB.read_text(encoding="utf-8"))
    return []


@tool(
    name="rag_ingest_folder",
    description="Index text files from a folder into a simple JSON store.",
    params={
        "folder": {"type": "string"},
        "pattern": {"type": "string", "description": "Glob pattern, default **/*.txt"},
        "max_chars": {"type": "integer", "description": "Max chars per file"},
    },
)
def rag_ingest_folder(folder: str, pattern: str = "**/*.txt", max_chars: int = 20000):
    base = Path(folder)
    items = []
    for p in base.glob(pattern):
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
            items.append({"path": str(p), "text": text[:max_chars]})
    data = _load() + items
    _save(data)
    return {"indexed": len(items)}


@tool(
    name="rag_search",
    description="Simple keyword search over indexed items.",
    params={
        "query": {"type": "string"},
        "limit": {"type": "integer", "description": "Max results (optional)"},
    },
)
def rag_search(query: str, limit: int | None = None):
    q = query.lower()
    results = [it for it in _load() if q in it.get("text", "").lower()]
    return results[:limit] if limit else results


@tool(
    name="rag_ingest_text",
    description="Index raw text with optional metadata.",
    params={
        "name": {"type": "string", "description": "Item name"},
        "text": {"type": "string", "description": "Text content"},
        "metadata": {"type": "object", "description": "Metadata (optional)"},
        "max_chars": {"type": "integer", "description": "Max chars to store (optional)"},
    },
)
def rag_ingest_text(name: str, text: str, metadata: dict | None = None, max_chars: int = 20000):
    data = _load()
    data.append({"path": name, "text": text[:max_chars], "metadata": metadata or {}})
    _save(data)
    return {"ok": True}


@tool(
    name="rag_ingest_files",
    description="Index a list of text files.",
    params={
        "paths": {"type": "array", "description": "File paths"},
        "max_chars": {"type": "integer", "description": "Max chars per file"},
    },
)
def rag_ingest_files(paths: list[str], max_chars: int = 20000):
    items = []
    for p in paths:
        fp = Path(p)
        if fp.is_file():
            text = fp.read_text(encoding="utf-8", errors="ignore")
            items.append({"path": str(fp), "text": text[:max_chars]})
    data = _load() + items
    _save(data)
    return {"indexed": len(items)}


@tool(
    name="rag_list",
    description="List indexed items (optionally limited).",
    params={"limit": {"type": "integer", "description": "Max items (optional)"}},
)
def rag_list(limit: int | None = None):
    items = _load()
    return items[:limit] if limit else items


@tool(
    name="rag_delete",
    description="Delete indexed items by path/name.",
    params={"name": {"type": "string"}},
)
def rag_delete(name: str):
    items = [it for it in _load() if it.get("path") != name]
    _save(items)
    return {"ok": True}


@tool(
    name="rag_clear",
    description="Clear all indexed items.",
    params={},
)
def rag_clear():
    _save([])
    return {"ok": True}
