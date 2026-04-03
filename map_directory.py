#!/usr/bin/env python3
"""
map_directory.py
Prints the full directory tree rooted at the folder this script lives in.
"""

import os
import sys
from pathlib import Path


def build_tree(
    root: Path,
    prefix: str = "",
    max_depth: int = None,
    current_depth: int = 0,
    show_hidden: bool = False,
) -> list[str]:
    """Recursively build tree lines for *root*."""
    if max_depth is not None and current_depth >= max_depth:
        return []

    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return [prefix + "  [permission denied]"]

    if not show_hidden:
        entries = [e for e in entries if not e.name.startswith(".")]

    lines = []
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        icon = "📁 " if entry.is_dir() else "📄 "
        lines.append(prefix + connector + icon + entry.name)

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(
                build_tree(
                    entry,
                    prefix=prefix + extension,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                    show_hidden=show_hidden,
                )
            )
    return lines


def count_items(root: Path, show_hidden: bool = False):
    """Return (total_dirs, total_files) under root."""
    dirs = files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if not show_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            filenames = [f for f in filenames if not f.startswith(".")]
        dirs += len(dirnames)
        files += len(filenames)
    return dirs, files


def main():
    # ── Configuration ────────────────────────────────────────────────────────
    script_dir   = Path(__file__).resolve().parent  # folder the script lives in
    max_depth    = None    # None = unlimited  |  integer = max folder depth
    show_hidden  = False   # True = include dot-files / dot-folders
    output_file  = None    # None = stdout only  |  "tree.txt" = also save to file
    # ─────────────────────────────────────────────────────────────────────────

    header = f"📂 {script_dir}"
    tree_lines = build_tree(script_dir, max_depth=max_depth, show_hidden=show_hidden)
    total_dirs, total_files = count_items(script_dir, show_hidden=show_hidden)
    summary = f"\n{total_dirs} director{'ies' if total_dirs != 1 else 'y'}, {total_files} file{'s' if total_files != 1 else ''}"

    output = "\n".join([header] + tree_lines + [summary])

    # Print to console
    print(output)

    # Optionally save to file
    if output_file:
        out_path = script_dir / output_file
        out_path.write_text(output, encoding="utf-8")
        print(f"\n✅  Tree saved to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()