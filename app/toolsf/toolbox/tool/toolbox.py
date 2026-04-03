from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.toolbox.toolbox")
logger.debug("Loaded tool module: toolbox.toolbox")

from app.utils.groq import tool, FUNCTIONS


@tool(
    name="tool_call",
    description="Call any registered tool by name with params.",
    params={
        "tool_name": {"type": "string"},
        "tool_params": {"type": "object"},
    },
)
def tool_call(tool_name: str, tool_params: dict | None = None):
    fn = FUNCTIONS.get(tool_name)
    if not fn:
        raise ValueError(f"Tool not found: {tool_name}")
    return fn(**(tool_params or {}))


@tool(
    name="tool_list",
    description="List all registered tool names.",
    params={},
)
def tool_list():
    return sorted(FUNCTIONS.keys())


@tool(
    name="tool_info",
    description="Get a tool's docstring and parameter info if available.",
    params={"tool_name": {"type": "string"}},
)
def tool_info(tool_name: str):
    fn = FUNCTIONS.get(tool_name)
    if not fn:
        return {}
    return {
        "name": tool_name,
        "doc": (fn.__doc__ or "").strip(),
        "params": getattr(fn, "_params", None),
    }
