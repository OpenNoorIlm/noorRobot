from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.quran.quran")
logger.debug("Loaded tool module: quran.quran")

import json
from pathlib import Path
from app.utils.groq import tool

_DB_DIR = Path(__file__).resolve().parents[3] / "database" / "quran"

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


def _resolve_dataset(edition: str) -> str:
    e = (edition or "").lower()
    if e in ("quran", "quran_uthmani", "uthmani", "ar", "arabic"):
        return "quran_uthmani"
    if e in ("kanzuliman", "kanzul_iman", "ahmedraza", "ahmed_raza"):
        return "kanzul_iman"
    if e in ("jalalayn", "tafsir_jalalayn", "tafsir_jalayn"):
        return "tafsir_jalalayn"
    return edition


@tool(
    name="quran_get_ayah",
    description="Get a single ayah by surah/ayah from local dataset.",
    params={
        "surah": {"type": "integer", "description": "Surah number (1-114)"},
        "ayah": {"type": "integer", "description": "Ayah number"},
        "edition": {"type": "string", "description": "Edition, e.g. quran-uthmani, en.asad (optional)"},
    },
)
def quran_get_ayah(surah: int, ayah: int, edition: str = "quran-uthmani"):
    ds = _resolve_dataset(edition)
    data = _load(ds)
    for row in data:
        if int(row.get("surah", 0)) == int(surah) and int(row.get("ayah", 0)) == int(ayah):
            return row
    return {}


@tool(
    name="quran_get_surah",
    description="Get a full surah by number from local dataset.",
    params={
        "surah": {"type": "integer", "description": "Surah number (1-114)"},
        "edition": {"type": "string", "description": "Edition, e.g. quran-uthmani, en.asad (optional)"},
    },
)
def quran_get_surah(surah: int, edition: str = "quran-uthmani"):
    ds = _resolve_dataset(edition)
    data = _load(ds)
    return [row for row in data if int(row.get("surah", 0)) == int(surah)]


@tool(
    name="quran_get_tafsir",
    description="Get tafsir for an ayah from local dataset.",
    params={
        "surah": {"type": "integer", "description": "Surah number (1-114)"},
        "ayah": {"type": "integer", "description": "Ayah number"},
        "tafsir": {"type": "string", "description": "jalalayn|kanzuliman or custom edition"},
    },
)
def quran_get_tafsir(
    surah: int,
    ayah: int,
    tafsir: str = "jalalayn",
):
    ds = _resolve_dataset(tafsir)
    data = _load(ds)
    for row in data:
        if int(row.get("surah", 0)) == int(surah) and int(row.get("ayah", 0)) == int(ayah):
            return row
    return {}


@tool(
    name="quran_search",
    description="Search Quran/tafsir text in local datasets.",
    params={
        "query": {"type": "string", "description": "Search query"},
        "language": {"type": "string", "description": "Language code (optional)"},
        "page": {"type": "integer", "description": "Page number (optional)"},
        "per_page": {"type": "integer", "description": "Results per page (optional)"},
    },
)
def quran_search(query: str, language: str = "en", page: int = 1, per_page: int = 10):
    # language is kept for compatibility; local datasets are not language-tagged here.
    q = (query or "").lower()
    data = _load("quran_uthmani")
    results = [row for row in data if q in str(row.get("text", "")).lower()]
    start = max(0, (int(page) - 1) * int(per_page))
    end = start + int(per_page)
    return {"results": results[start:end], "total": len(results)}


@tool(
    name="quran_get_surah_list",
    description="Get the list of all surahs.",
    params={},
)
def quran_get_surah_list():
    data = _load("quran_uthmani")
    surah_counts: dict[int, int] = {}
    for row in data:
        s = int(row.get("surah", 0))
        surah_counts[s] = surah_counts.get(s, 0) + 1
    return [{"surah": k, "ayah_count": surah_counts[k]} for k in sorted(surah_counts.keys())]
