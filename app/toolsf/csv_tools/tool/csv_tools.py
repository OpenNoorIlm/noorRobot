from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.csv_tools.csv_tools")
logger.debug("Loaded tool module: csv_tools.csv_tools")

import csv
import json
from pathlib import Path
from app.utils.groq import tool


@tool(
    name="csv_read",
    description="Read a CSV file into list of dicts.",
    params={
        "path": {"type": "string", "description": "CSV path"},
        "delimiter": {"type": "string", "description": "Delimiter (optional)"},
        "encoding": {"type": "string", "description": "Encoding (optional)"},
        "limit": {"type": "integer", "description": "Max rows (optional)"},
    },
)
def csv_read(path: str, delimiter: str = ",", encoding: str = "utf-8", limit: int | None = None):
    p = Path(path)
    with p.open("r", encoding=encoding, newline="") as f:
        rows = list(csv.DictReader(f, delimiter=delimiter))
    return rows[:limit] if limit else rows


@tool(
    name="csv_write",
    description="Write rows (list of dicts) to CSV.",
    params={
        "path": {"type": "string", "description": "CSV path"},
        "rows": {"type": "array", "description": "List of dict rows"},
        "delimiter": {"type": "string", "description": "Delimiter (optional)"},
        "encoding": {"type": "string", "description": "Encoding (optional)"},
    },
)
def csv_write(path: str, rows: list[dict], delimiter: str = ",", encoding: str = "utf-8"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        p.write_text("", encoding="utf-8")
        return str(p.resolve())
    with p.open("w", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)
    return str(p.resolve())


@tool(
    name="csv_filter",
    description="Filter CSV rows by column equals value.",
    params={
        "path": {"type": "string", "description": "CSV path"},
        "column": {"type": "string", "description": "Column name"},
        "value": {"type": "string", "description": "Value to match"},
        "delimiter": {"type": "string", "description": "Delimiter (optional)"},
        "encoding": {"type": "string", "description": "Encoding (optional)"},
    },
)
def csv_filter(path: str, column: str, value: str, delimiter: str = ",", encoding: str = "utf-8"):
    rows = csv_read(path, delimiter=delimiter, encoding=encoding)
    return [r for r in rows if str(r.get(column, "")) == value]


@tool(
    name="csv_stats",
    description="Basic stats: row count and columns.",
    params={
        "path": {"type": "string", "description": "CSV path"},
        "delimiter": {"type": "string", "description": "Delimiter (optional)"},
        "encoding": {"type": "string", "description": "Encoding (optional)"},
    },
)
def csv_stats(path: str, delimiter: str = ",", encoding: str = "utf-8"):
    rows = csv_read(path, delimiter=delimiter, encoding=encoding)
    cols = list(rows[0].keys()) if rows else []
    return {"rows": len(rows), "columns": cols}


@tool(
    name="csv_select_columns",
    description="Select specific columns from a CSV.",
    params={
        "path": {"type": "string"},
        "columns": {"type": "array"},
        "delimiter": {"type": "string"},
        "encoding": {"type": "string"},
    },
)
def csv_select_columns(path: str, columns: list[str], delimiter: str = ",", encoding: str = "utf-8"):
    rows = csv_read(path, delimiter=delimiter, encoding=encoding)
    return [{k: r.get(k) for k in columns} for r in rows]


@tool(
    name="csv_sort",
    description="Sort CSV rows by a column.",
    params={
        "path": {"type": "string"},
        "column": {"type": "string"},
        "reverse": {"type": "boolean"},
        "delimiter": {"type": "string"},
        "encoding": {"type": "string"},
    },
)
def csv_sort(path: str, column: str, reverse: bool = False, delimiter: str = ",", encoding: str = "utf-8"):
    rows = csv_read(path, delimiter=delimiter, encoding=encoding)
    return sorted(rows, key=lambda r: r.get(column), reverse=reverse)


@tool(
    name="csv_to_json",
    description="Convert CSV to JSON file.",
    params={
        "path": {"type": "string"},
        "out": {"type": "string"},
        "delimiter": {"type": "string"},
        "encoding": {"type": "string"},
    },
)
def csv_to_json(path: str, out: str, delimiter: str = ",", encoding: str = "utf-8"):
    rows = csv_read(path, delimiter=delimiter, encoding=encoding)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return str(outp.resolve())


@tool(
    name="csv_from_json",
    description="Write JSON list of objects to CSV.",
    params={
        "json_path": {"type": "string"},
        "out": {"type": "string"},
        "delimiter": {"type": "string"},
        "encoding": {"type": "string"},
    },
)
def csv_from_json(json_path: str, out: str, delimiter: str = ",", encoding: str = "utf-8"):
    data = json.loads(Path(json_path).read_text(encoding=encoding))
    return csv_write(out, data, delimiter=delimiter, encoding=encoding)
