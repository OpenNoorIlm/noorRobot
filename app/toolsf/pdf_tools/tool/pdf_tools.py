from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.pdf_tools.pdf_tools")
logger.debug("Loaded tool module: pdf_tools.pdf_tools")

from pathlib import Path
from app.utils.groq import tool

try:
    from PyPDF2 import PdfReader, PdfWriter  # type: ignore
except Exception:
    PdfReader = None
    PdfWriter = None


def _require():
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError("PyPDF2 not installed")


@tool(
    name="pdf_extract_text",
    description="Extract text from a PDF.",
    params={
        "path": {"type": "string", "description": "PDF path"},
        "start_page": {"type": "integer", "description": "Start page (1-based, optional)"},
        "end_page": {"type": "integer", "description": "End page (1-based, optional)"},
    },
)
def pdf_extract_text(path: str, start_page: int | None = None, end_page: int | None = None):
    _require()
    reader = PdfReader(path)
    pages = reader.pages
    s = (start_page - 1) if start_page else 0
    e = end_page if end_page else len(pages)
    return "\n".join([(p.extract_text() or "") for p in pages[s:e]])


@tool(
    name="pdf_merge",
    description="Merge PDFs into one.",
    params={
        "inputs": {"type": "array", "description": "PDF paths"},
        "output": {"type": "string", "description": "Output PDF path"},
    },
)
def pdf_merge(inputs: list[str], output: str):
    _require()
    writer = PdfWriter()
    for p in inputs:
        r = PdfReader(p)
        for page in r.pages:
            writer.add_page(page)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)
    return str(out.resolve())


@tool(
    name="pdf_split",
    description="Split a PDF into individual pages.",
    params={
        "path": {"type": "string", "description": "PDF path"},
        "out_dir": {"type": "string", "description": "Output directory"},
        "start_page": {"type": "integer", "description": "Start page (1-based, optional)"},
        "end_page": {"type": "integer", "description": "End page (1-based, optional)"},
    },
)
def pdf_split(path: str, out_dir: str, start_page: int | None = None, end_page: int | None = None):
    _require()
    reader = PdfReader(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    s = (start_page - 1) if start_page else 0
    e = end_page if end_page else len(reader.pages)
    for i, page in enumerate(reader.pages[s:e], start=s + 1):
        writer = PdfWriter()
        writer.add_page(page)
        fp = out / f"page_{i}.pdf"
        with fp.open("wb") as f:
            writer.write(f)
        files.append(str(fp.resolve()))
    return files
