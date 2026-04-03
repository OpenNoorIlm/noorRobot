from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.FileSystem.FileSystem")
logger.debug("Loaded tool module: FileSystem.FileSystem")

import shutil
import base64
import hashlib
from pathlib import Path
from app.utils.groq import tool

BASE_DIR = Path(__file__).resolve().parents[3]
ALLOWED_DIRS = [BASE_DIR]


def _to_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


@tool(
    name="read_file_deprecated",
    description="Read a text file (deprecated).",
    params={"path": {"type": "string", "description": "File path"}},
)
def read_file_deprecated(path: str) -> str:
    return read_text_file(path)


@tool(
    name="read_text_file",
    description="Read a text file and return its contents.",
    params={"path": {"type": "string", "description": "File path"}},
)
def read_text_file(path: str) -> str:
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_text(encoding="utf-8")


@tool(
    name="read_binary_file",
    description="Read a binary file and return base64 content.",
    params={"path": {"type": "string", "description": "File path"}},
)
def read_binary_file(path: str) -> str:
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    data = p.read_bytes()
    return base64.b64encode(data).decode("ascii")


@tool(
    name="read_multiple_files",
    description="Read multiple text files and return a mapping of path to contents.",
    params={"paths": {"type": "array", "description": "List of file paths"}},
)
def read_multiple_files(paths: list[str]):
    result = {}
    for path in paths:
        p = _to_path(path)
        if not p.exists():
            result[str(p)] = "[missing]"
            continue
        result[str(p)] = p.read_text(encoding="utf-8")
    return result


@tool(
    name="list_directory",
    description="List files and folders in a directory.",
    params={"path": {"type": "string", "description": "Directory path"}},
)
def list_directory(path: str = "."):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")
    return sorted([child.name for child in p.iterdir()])


@tool(
    name="list_directory_recursive",
    description="List files and folders recursively.",
    params={
        "path": {"type": "string", "description": "Directory path"},
        "max_depth": {"type": "integer", "description": "Max depth (optional)"},
    },
)
def list_directory_recursive(path: str = ".", max_depth: int = 5):
    root = _to_path(path)
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    items = []
    for p in root.rglob("*"):
        depth = len(p.relative_to(root).parts)
        if max_depth and depth > int(max_depth):
            continue
        items.append(str(p))
    return sorted(items)


@tool(
    name="list_directory_with_sizes",
    description="List files and folders in a directory with sizes (bytes).",
    params={"path": {"type": "string", "description": "Directory path"}},
)
def list_directory_with_sizes(path: str = "."):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {p}")
    items = []
    for child in p.iterdir():
        size = child.stat().st_size if child.is_file() else 0
        items.append({"name": child.name, "is_dir": child.is_dir(), "size": size})
    return sorted(items, key=lambda x: x["name"])


@tool(
    name="directory_tree",
    description="Return a directory tree up to a max depth.",
    params={
        "path": {"type": "string", "description": "Directory path"},
        "max_depth": {"type": "integer", "description": "Max depth (default 3)"},
    },
)
def directory_tree(path: str = ".", max_depth: int = 3):
    root = _to_path(path)
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    def _walk(dir_path: Path, depth: int):
        if depth > max_depth:
            return []
        entries = []
        for child in sorted(dir_path.iterdir(), key=lambda p: p.name):
            node = {"name": child.name, "is_dir": child.is_dir()}
            if child.is_dir():
                node["children"] = _walk(child, depth + 1)
            entries.append(node)
        return entries

    return {"root": str(root), "tree": _walk(root, 1)}


@tool(
    name="search_files",
    description="Search for files matching a glob pattern.",
    params={
        "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py'"},
        "base": {"type": "string", "description": "Base directory (default '.')"},
    },
)
def search_files(pattern: str, base: str = "."):
    base_path = _to_path(base)
    if not base_path.exists():
        raise FileNotFoundError(f"Base path not found: {base_path}")
    return sorted([str(p) for p in base_path.glob(pattern)])


@tool(
    name="get_file_info",
    description="Get file or folder metadata.",
    params={"path": {"type": "string", "description": "Path to inspect"}},
)
def get_file_info(path: str):
    return stat(path)


@tool(
    name="list_allowed_directories",
    description="List directories allowed for file operations.",
    params={},
)
def list_allowed_directories():
    return [str(p) for p in ALLOWED_DIRS]


@tool(
    name="write_file",
    description="Write text to a file (overwrite by default).",
    params={
        "path": {"type": "string", "description": "File path"},
        "content": {"type": "string", "description": "Text content"},
        "overwrite": {"type": "boolean", "description": "Overwrite if exists (default true)"},
    },
)
def write_file(path: str, content: str, overwrite: bool = True) -> str:
    p = _to_path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {p}"


@tool(
    name="write_binary_file",
    description="Write a binary file from base64 content.",
    params={
        "path": {"type": "string", "description": "File path"},
        "content_b64": {"type": "string", "description": "Base64 content"},
        "overwrite": {"type": "boolean", "description": "Overwrite if exists (default true)"},
    },
)
def write_binary_file(path: str, content_b64: str, overwrite: bool = True) -> str:
    p = _to_path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(content_b64.encode("ascii"))
    p.write_bytes(data)
    return f"Wrote {len(data)} bytes to {p}"


@tool(
    name="edit_file",
    description="Edit a file by replacing text.",
    params={
        "path": {"type": "string", "description": "File path"},
        "search": {"type": "string", "description": "Text to find"},
        "replace": {"type": "string", "description": "Replacement text"},
        "count": {"type": "integer", "description": "Max replacements (optional)"},
    },
)
def edit_file(path: str, search: str, replace: str, count: int | None = None) -> str:
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    data = p.read_text(encoding="utf-8")
    if count is None:
        new_data = data.replace(search, replace)
    else:
        new_data = data.replace(search, replace, int(count))
    p.write_text(new_data, encoding="utf-8")
    return "ok"


@tool(
    name="find_text_in_files",
    description="Find text in files under a directory.",
    params={
        "base": {"type": "string", "description": "Base directory"},
        "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
        "query": {"type": "string", "description": "Text to search"},
        "case_sensitive": {"type": "boolean", "description": "Case sensitive (optional)"},
        "max_matches": {"type": "integer", "description": "Max matches (optional)"},
    },
)
def find_text_in_files(base: str, pattern: str, query: str, case_sensitive: bool = False, max_matches: int = 200):
    base_path = _to_path(base)
    if not base_path.exists():
        raise FileNotFoundError(f"Base path not found: {base_path}")
    results = []
    q = query if case_sensitive else query.lower()
    for p in base_path.glob(pattern):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            hay = line if case_sensitive else line.lower()
            if q in hay:
                results.append({"path": str(p), "line": i, "text": line})
                if len(results) >= max_matches:
                    return results
    return results


@tool(
    name="append_file",
    description="Append text to a file (creates file if missing).",
    params={
        "path": {"type": "string", "description": "File path"},
        "content": {"type": "string", "description": "Text content to append"},
    },
)
def append_file(path: str, content: str) -> str:
    p = _to_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} chars to {p}"


@tool(
    name="head_file",
    description="Return the first N lines of a text file.",
    params={
        "path": {"type": "string"},
        "lines": {"type": "integer", "description": "Number of lines (default 10)"},
    },
)
def head_file(path: str, lines: int = 10):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    data = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(data[: int(lines)])


@tool(
    name="tail_file",
    description="Return the last N lines of a text file.",
    params={
        "path": {"type": "string"},
        "lines": {"type": "integer", "description": "Number of lines (default 10)"},
    },
)
def tail_file(path: str, lines: int = 10):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    data = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(data[-int(lines):])


@tool(
    name="delete_path",
    description="Delete a file or folder.",
    params={
        "path": {"type": "string", "description": "File or folder path"},
        "recursive": {"type": "boolean", "description": "Delete folders recursively (default false)"},
    },
)
def delete_path(path: str, recursive: bool = False) -> str:
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    if p.is_dir():
        if not recursive:
            p.rmdir()
        else:
            shutil.rmtree(p)
    else:
        p.unlink()
    return f"Deleted {p}"


@tool(
    name="create_directory",
    description="Create a directory (including parents).",
    params={
        "path": {"type": "string", "description": "Directory path"},
        "exist_ok": {"type": "boolean", "description": "No error if exists (default true)"},
    },
)
def create_directory(path: str, exist_ok: bool = True) -> str:
    return make_dir(path, exist_ok)


@tool(
    name="move_file",
    description="Move or rename a file/folder.",
    params={
        "src": {"type": "string", "description": "Source path"},
        "dst": {"type": "string", "description": "Destination path"},
        "overwrite": {"type": "boolean", "description": "Overwrite destination (default false)"},
    },
)
def move_file(src: str, dst: str, overwrite: bool = False) -> str:
    s = _to_path(src)
    d = _to_path(dst)
    if not s.exists():
        raise FileNotFoundError(f"Source not found: {s}")
    if d.exists():
        if not overwrite:
            raise FileExistsError(f"Destination exists: {d}")
        if d.is_dir():
            shutil.rmtree(d)
        else:
            d.unlink()
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(s), str(d))
    return f"Moved {s} -> {d}"


@tool(
    name="copy_file_to_claude",
    description="Copy a file to a local Claude drop folder.",
    params={
        "src": {"type": "string", "description": "Source file path"},
        "dst_name": {"type": "string", "description": "Destination filename (optional)"},
        "overwrite": {"type": "boolean", "description": "Overwrite destination (default false)"},
    },
)
def copy_file_to_claude(src: str, dst_name: str = "", overwrite: bool = False) -> str:
    s = _to_path(src)
    if not s.exists():
        raise FileNotFoundError(f"Source not found: {s}")
    if s.is_dir():
        raise IsADirectoryError(f"Source is a directory: {s}")
    claude_dir = BASE_DIR / "claude_files"
    claude_dir.mkdir(parents=True, exist_ok=True)
    dst = claude_dir / (dst_name if dst_name else s.name)
    if dst.exists():
        if not overwrite:
            raise FileExistsError(f"Destination exists: {dst}")
        dst.unlink()
    shutil.copy2(s, dst)
    return f"Copied {s} -> {dst}"


@tool(
    name="copy_path",
    description="Copy a file or folder.",
    params={
        "src": {"type": "string", "description": "Source path"},
        "dst": {"type": "string", "description": "Destination path"},
        "overwrite": {"type": "boolean", "description": "Overwrite destination (default false)"},
    },
)
def copy_path(src: str, dst: str, overwrite: bool = False) -> str:
    s = _to_path(src)
    d = _to_path(dst)
    if not s.exists():
        raise FileNotFoundError(f"Source not found: {s}")
    if d.exists():
        if not overwrite:
            raise FileExistsError(f"Destination exists: {d}")
        if d.is_dir():
            shutil.rmtree(d)
        else:
            d.unlink()
    d.parent.mkdir(parents=True, exist_ok=True)
    if s.is_dir():
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)
    return f"Copied {s} -> {d}"


@tool(
    name="make_dir",
    description="Create a directory (including parents).",
    params={
        "path": {"type": "string", "description": "Directory path"},
        "exist_ok": {"type": "boolean", "description": "No error if exists (default true)"},
    },
)
def make_dir(path: str, exist_ok: bool = True) -> str:
    p = _to_path(path)
    p.mkdir(parents=True, exist_ok=exist_ok)
    return f"Created directory {p}"


@tool(
    name="exists",
    description="Check if a path exists.",
    params={"path": {"type": "string", "description": "Path to check"}},
)
def exists(path: str) -> bool:
    return _to_path(path).exists()


@tool(
    name="stat",
    description="Get file or folder metadata.",
    params={"path": {"type": "string", "description": "Path to inspect"}},
)
def stat(path: str):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {p}")
    info = p.stat()
    return {
        "path": str(p),
        "is_dir": p.is_dir(),
        "size": info.st_size,
        "modified": info.st_mtime,
        "created": info.st_ctime,
    }


@tool(
    name="file_hash",
    description="Compute a file hash (md5/sha1/sha256).",
    params={
        "path": {"type": "string"},
        "algorithm": {"type": "string", "description": "md5|sha1|sha256 (default sha256)"},
    },
)
def file_hash(path: str, algorithm: str = "sha256"):
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    algo = algorithm.lower()
    h = hashlib.new(algo)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@tool(
    name="fs_search",
    description="Search for paths matching a glob pattern (filesystem).",
    params={
        "pattern": {"type": "string", "description": "Glob pattern, e.g. '**/*.py'"},
        "base": {"type": "string", "description": "Base directory (default '.')"},
    },
)
def fs_search(pattern: str, base: str = "."):
    return search_files(pattern, base)
