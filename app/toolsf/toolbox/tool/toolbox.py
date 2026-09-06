from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.toolbox.toolbox")
logger.debug("Loaded tool module: toolbox.toolbox")

from app.utils.groq import tool, FUNCTIONS, TOOLS


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
    description="List all registered tool names. Use list_tools(query=X) for filtered search.",
    params={},
)
def tool_list():
    return sorted(FUNCTIONS.keys())


@tool(
    name="tool_info",
    description=(
        "Get a tool's parameter names and types. "
        "ALWAYS call this before calling an unfamiliar tool so you use the correct parameter names."
    ),
    params={"tool_name": {"type": "string", "description": "Exact tool name"}},
)
def tool_info(tool_name: str):
    fn = FUNCTIONS.get(tool_name)
    if not fn:
        return {"error": f"Tool '{tool_name}' not found. Call list_tools to see available tools."}
    # Extract schema from the TOOLS registry (populated by @tool decorator)
    schema = next(
        (t for t in TOOLS if t.get("function", {}).get("name") == tool_name),
        None,
    )
    params = {}
    if schema:
        props = schema.get("function", {}).get("parameters", {}).get("properties", {})
        required = schema.get("function", {}).get("parameters", {}).get("required", [])
        for pname, pschema in props.items():
            params[pname] = {
                "type": pschema.get("type") or "any",
                "description": pschema.get("description", ""),
                "required": pname in required,
            }
    return {
        "name": tool_name,
        "description": schema.get("function", {}).get("description", "") if schema else "",
        "params": params,
        "example_call": {
            "tool_name": tool_name,
            "tool_params": {k: f"<{v['type']}>" for k, v in params.items()},
        },
    }
