"""
NoorRobot Pipe Function for Open WebUI
========================================
Install as a FUNCTION in Open WebUI (Admin → Functions → + → paste this code).
NOT a Pipeline. This runs inside Open WebUI directly — no separate server needed.

- Every message routes to NoorRobot /agent
- Tool calls render as native <details type="tool_calls"> panels
- Discovery tool calls (list_tools etc) are hidden — only real actions show
- Always terminates with finish_reason: stop so Open WebUI never re-executes
"""

from __future__ import annotations
import html
import json
from typing import Any, Generator, Iterator, Union

import requests
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        NOORROBOT_URL: str = Field(
            default="http://172.17.0.1:8000",
            description="Base URL of the running NoorRobot server (use 172.17.0.1 from inside Docker)",
        )
        NOORROBOT_API_KEY: str = Field(
            default="",
            description="Optional NOOR_API_KEY set on the NoorRobot server",
        )
        REQUEST_TIMEOUT: int = Field(default=120, description="HTTP timeout seconds")
        MAX_TOKENS: int = Field(default=2048, description="Default max_tokens")
        TEMPERATURE: float = Field(default=0.7, description="Default temperature")
        MAX_STEPS: int = Field(default=3, description="Max agentic tool-call steps per request")

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        return [{"id": "noorrobot", "name": "NoorRobot"}]

    # Discovery/internal tools — hide from UI panels, they are noise
    _SILENT_TOOLS = {
        "list_tools", "load_tools", "list_skills",
        "get_skill", "tool_info", "list_skill",
    }

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.valves.NOORROBOT_API_KEY:
            h["Authorization"] = f"Bearer {self.valves.NOORROBOT_API_KEY}"
        return h

    def _details_block(self, call_id: str, name: str, args: dict, result: Any) -> str:
        args_str = json.dumps(args, ensure_ascii=False)
        res_str = (
            json.dumps(result, ensure_ascii=False)
            if not isinstance(result, str)
            else result
        )
        if len(res_str) > 2000:
            res_str = res_str[:2000] + "\n...[truncated]"
        return (
            f'<details type="tool_calls" done="true" '
            f'id="{html.escape(call_id)}" '
            f'name="{html.escape(name)}" '
            f'arguments="{html.escape(args_str)}">\n'
            f"<summary>{html.escape(name)}</summary>\n"
            f"{html.escape(res_str)}\n"
            f"</details>\n"
        )

    def pipe(
        self,
        body: dict[str, Any],
        __user__: dict | None = None,
        __event_emitter__=None,
    ) -> Generator:
        base_url = self.valves.NOORROBOT_URL.strip().rstrip("/")
        messages = body.get("messages", [])

        user_message = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        system = next(
            (m.get("content", "") for m in messages if m.get("role") == "system"),
            "",
        )
        history = [m for m in messages if m.get("role") in ("user", "assistant")][:-1]

        payload = {
            "input":        user_message,
            "system":       system,
            "history":      history,
            "max_tokens":   body.get("max_tokens",  self.valves.MAX_TOKENS),
            "temperature":  body.get("temperature", self.valves.TEMPERATURE),
            "max_steps":    self.valves.MAX_STEPS,
            "return_trace": True,
        }

        try:
            resp = requests.post(
                f"{base_url}/agent",
                headers=self._headers(),
                json=payload,
                timeout=self.valves.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            yield f"⚠️ NoorRobot unreachable ({base_url}): {exc}"
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
            return
        except Exception as exc:
            yield f"⚠️ Pipeline error: {exc}"
            yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
            return

        reply = data.get("reply", "")
        trace = data.get("trace", [])

        # Render non-silent tool calls as collapsible panels (NOT delta.tool_calls)
        for i, step in enumerate(trace):
            name = step.get("name", "tool")
            if name in self._SILENT_TOOLS:
                continue
            args   = step.get("args", {})
            result = step.get("result", "")
            yield self._details_block(f"call_{i}", name, args, result)

        if reply:
            yield reply

        # Always stop — never emit finish_reason: tool_calls
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
