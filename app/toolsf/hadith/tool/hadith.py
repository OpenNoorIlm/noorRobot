from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.hadith.hadith")
logger.debug("Loaded tool module: hadith.hadith")

import json
from pathlib import Path
from app.utils.groq import tool

_DB_DIR = Path(__file__).resolve().parents[3] / "database" / "hadith"
_CACHE: dict[str, list[dict]] = {}


def _load(name: str) -> list[dict]:
    if name in _CACHE:
        return _CACHE[name]
    path = _DB_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}. Run dataset download.")
    data = json.loads(path.read_text(encoding="utf-8"))
    _CACHE[name] = data
    return data


def _resolve_collection(collection: str) -> str:
    c = (collection or "").lower()
    if "bukhari" in c:
        return "bukhari"
    if "muslim" in c:
        return "muslim"
    return collection


@tool(
    name="hadith_get",
    description="Get a hadith by collection and number from local dataset.",
    params={
        "collection": {"type": "string", "description": "bukhari|muslim"},
        "number": {"type": "integer", "description": "Hadith number"},
    },
)
def hadith_get(collection: str, number: int):
    coll = _resolve_collection(collection)
    data = _load(coll)
    num = int(number)
    for row in data:
        if int(row.get("hadith_no_in_book", -1)) == num or int(row.get("hadith_id", -1)) == num:
            return row
    return {}


@tool(
    name="hadith_search",
    description="Search hadith in a collection (local dataset).",
    params={
        "collection": {"type": "string", "description": "bukhari|muslim"},
        "query": {"type": "string", "description": "Search query"},
        "page": {"type": "integer", "description": "Page number (optional)"},
        "per_page": {"type": "integer", "description": "Results per page (optional)"},
    },
)
def hadith_search(collection: str, query: str, page: int = 1, per_page: int = 10):
    coll = _resolve_collection(collection)
    data = _load(coll)
    q = (query or "").lower()
    results = [
        row for row in data
        if q in str(row.get("arabic_full", "")).lower()
        or q in str(row.get("english_full", "")).lower()
    ]
    start = max(0, (int(page) - 1) * int(per_page))
    end = start + int(per_page)
    return {"results": results[start:end], "total": len(results)}


@tool(
    name="hadith_collections",
    description="List available collections in local dataset.",
    params={
    },
)
def hadith_collections():
    cols = []
    for name in ("bukhari", "muslim"):
        path = _DB_DIR / f"{name}.json"
        if path.exists():
            cols.append(name)
    return cols
