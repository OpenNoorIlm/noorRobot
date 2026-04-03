from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.zip_tools.zip_tools")
logger.debug("Loaded tool module: zip_tools.zip_tools")

import zipfile
from pathlib import Path
from app.utils.groq import tool


@tool(
    name="zip_create",
    description="Create a zip archive from files/folders.",
    params={
        "paths": {"type": "array", "description": "Paths to include"},
        "zip_path": {"type": "string", "description": "Output zip file"},
        "base_dir": {"type": "string", "description": "Base dir for relative paths (optional)"},
    },
)
def zip_create(paths: list[str], zip_path: str, base_dir: str = ""):
    zp = Path(zip_path)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        base = Path(base_dir).resolve() if base_dir else None
        for p in paths:
            path = Path(p)
            if path.is_dir():
                for f in path.rglob("*"):
                    if f.is_file():
                        arc = f.relative_to(base) if base and f.is_relative_to(base) else f.relative_to(path.parent)
                        z.write(f, arc)
            elif path.is_file():
                arc = path.relative_to(base) if base and path.is_relative_to(base) else path.name
                z.write(path, arc)
    return str(zp.resolve())


@tool(
    name="zip_extract",
    description="Extract a zip archive.",
    params={
        "zip_path": {"type": "string", "description": "Zip file"},
        "out_dir": {"type": "string", "description": "Output directory"},
        "members": {"type": "array", "description": "Specific members to extract (optional)"},
    },
)
def zip_extract(zip_path: str, out_dir: str, members: list[str] | None = None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        if members:
            z.extractall(out, members=members)
        else:
            z.extractall(out)
    return str(out.resolve())


@tool(
    name="zip_list",
    description="List entries in a zip archive.",
    params={"zip_path": {"type": "string", "description": "Zip file"}},
)
def zip_list(zip_path: str):
    with zipfile.ZipFile(zip_path, "r") as z:
        return z.namelist()


@tool(
    name="zip_info",
    description="Get detailed info for zip entries.",
    params={"zip_path": {"type": "string", "description": "Zip file"}},
)
def zip_info(zip_path: str):
    with zipfile.ZipFile(zip_path, "r") as z:
        return [
            {"name": i.filename, "size": i.file_size, "compressed": i.compress_size}
            for i in z.infolist()
        ]


@tool(
    name="zip_add",
    description="Append files/folders to an existing zip.",
    params={
        "zip_path": {"type": "string", "description": "Zip file"},
        "paths": {"type": "array", "description": "Paths to add"},
        "base_dir": {"type": "string", "description": "Base dir for relative paths (optional)"},
    },
)
def zip_add(zip_path: str, paths: list[str], base_dir: str = ""):
    zp = Path(zip_path)
    base = Path(base_dir).resolve() if base_dir else None
    with zipfile.ZipFile(zp, "a", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            path = Path(p)
            if path.is_dir():
                for f in path.rglob("*"):
                    if f.is_file():
                        arc = f.relative_to(base) if base and f.is_relative_to(base) else f.relative_to(path.parent)
                        z.write(f, arc)
            elif path.is_file():
                arc = path.relative_to(base) if base and path.is_relative_to(base) else path.name
                z.write(path, arc)
    return str(zp.resolve())
