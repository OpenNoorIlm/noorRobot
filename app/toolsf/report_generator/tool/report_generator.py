from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.report_generator.report_generator")
logger.debug("Loaded tool module: report_generator.report_generator")

from pathlib import Path
from app.utils.groq import tool


@tool(
    name="report_generate",
    description="Generate a markdown report from sections.",
    params={
        "title": {"type": "string"},
        "sections": {"type": "array", "description": "List of {heading, content}"},
        "out": {"type": "string", "description": "Output markdown path"},
        "front_matter": {"type": "object", "description": "YAML front matter (optional)"},
        "include_toc": {"type": "boolean", "description": "Include table of contents (optional)"},
        "footer": {"type": "string", "description": "Footer text (optional)"},
    },
)
def report_generate(
    title: str,
    sections: list[dict],
    out: str,
    front_matter: dict | None = None,
    include_toc: bool = False,
    footer: str = "",
):
    lines = []
    if front_matter:
        lines.append("---")
        for k, v in front_matter.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    if include_toc:
        lines.append("## Table of Contents")
        for s in sections:
            h = s.get("heading", "Section")
            anchor = h.lower().replace(" ", "-")
            lines.append(f"- [{h}](#{anchor})")
        lines.append("")
    for s in sections:
        h = s.get("heading", "Section")
        c = s.get("content", "")
        lines.append(f"## {h}")
        lines.append(c)
        lines.append("")
    if footer:
        lines.append(footer)
        lines.append("")
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(lines), encoding="utf-8")
    return str(outp.resolve())


@tool(
    name="report_generate_from_template",
    description="Generate a markdown report from a template with variables.",
    params={
        "template_path": {"type": "string"},
        "variables": {"type": "object"},
        "out": {"type": "string"},
    },
)
def report_generate_from_template(template_path: str, variables: dict, out: str):
    tpl = Path(template_path).read_text(encoding="utf-8")
    text = tpl.format(**variables)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(text, encoding="utf-8")
    return str(outp.resolve())
