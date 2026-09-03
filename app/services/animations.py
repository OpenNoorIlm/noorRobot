"""Local face-animation catalog and media access for NoorRobot."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

_DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "database" / "animations"
ROOT = Path(os.getenv("NOOR_ANIMATIONS_DIR", str(_DEFAULT_ROOT))).resolve()
DB_PATH = ROOT / "animations.db"


def _db() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Animation database not found: {DB_PATH}")
    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "name": row["name"],
        "description": row["description"],
        "anim_type": row["anim_type"],
        "eye_key": row["eye_key"],
        "mouth_key": row["mouth_key"],
        "video": row["video"],
        "static": row["static"],
        "timeline": {"0-5": row["timeline_0_5"], "5-10": row["timeline_5_10"]},
    }


def list_animations(eye_key=None, mouth_key=None, anim_type=None, limit=50, offset=0):
    limit = max(1, min(500, int(limit)))
    offset = max(0, int(offset))
    clauses, params = [], []
    for column, value in (("eye_key", eye_key), ("mouth_key", mouth_key), ("anim_type", anim_type)):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = " AND ".join(clauses) or "1=1"
    with _db() as db:
        total = db.execute(f"SELECT COUNT(*) FROM animations WHERE {where}", params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM animations WHERE {where} ORDER BY name LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "results": [_row(item) for item in rows]}


def search_animations(eye=None, mouth=None):
    return list_animations(eye_key=eye, mouth_key=mouth, limit=500)["results"]


def get_animation(name: str) -> dict[str, Any]:
    with _db() as db:
        result = _row(db.execute("SELECT * FROM animations WHERE name = ?", (name,)).fetchone())
    if result is None:
        raise KeyError(f"Animation '{name}' not found")
    return result


def get_file(name: str, kind: str) -> tuple[Path, str]:
    animation = get_animation(name)
    relative = animation["video"] if kind == "video" else animation["static"]
    path = (ROOT / relative).resolve()
    if ROOT not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Animation {kind} file not found")
    return path, "video/x-msvideo" if kind == "video" else "image/jpeg"


def keys() -> dict[str, list[str]]:
    with _db() as db:
        values = {}
        for column, output in (("eye_key", "eye_keys"), ("mouth_key", "mouth_keys"), ("anim_type", "anim_types")):
            values[output] = [row[0] for row in db.execute(f"SELECT DISTINCT {column} FROM animations ORDER BY {column}")]
    return values


def stats() -> dict[str, Any]:
    with _db() as db:
        total = db.execute("SELECT COUNT(*) FROM animations").fetchone()[0]
        types = {row[0]: row[1] for row in db.execute("SELECT anim_type, COUNT(*) FROM animations GROUP BY anim_type")}
        eyes = db.execute("SELECT COUNT(DISTINCT eye_key) FROM animations").fetchone()[0]
        mouths = db.execute("SELECT COUNT(DISTINCT mouth_key) FROM animations").fetchone()[0]
    return {"total_animations": total, "unique_eye_keys": eyes, "unique_mouth_keys": mouths, "by_anim_type": types}


def key_values(kind: str) -> list[str]:
    column = {"eye": "eye_key", "mouth": "mouth_key", "anim_type": "anim_type"}.get(kind)
    if column is None:
        raise ValueError("unknown animation key type")
    with _db() as db:
        return [row[0] for row in db.execute(f"SELECT DISTINCT {column} FROM animations ORDER BY {column}")]


def key_animations(kind: str, value: str) -> list[dict[str, Any]]:
    column = {"eye": "eye_key", "mouth": "mouth_key", "anim_type": "anim_type"}.get(kind)
    if column is None:
        raise ValueError("unknown animation key type")
    return list_animations(**{column: value}, limit=500)["results"]


def combo(eye_key: str, mouth_key: str) -> list[dict[str, Any]]:
    return list_animations(eye_key=eye_key, mouth_key=mouth_key, limit=500)["results"]


def config() -> dict[str, str]:
    with _db() as db:
        return {row["name"]: row["video"] for row in db.execute("SELECT name, video FROM animations ORDER BY name")}
