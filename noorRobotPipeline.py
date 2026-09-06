"""
NoorRobot Pipeline for Open WebUI
==================================
Official pattern from docs.openwebui.com/features/extensibility/pipelines/pipes

- Routes every message to NoorRobot /agent (NoorRobot owns all tool execution)
- Streams status events while waiting
- Renders tool calls as <details type="tool_calls"> blocks (NOT delta.tool_calls)
- Always terminates with finish_reason: "stop"
- Open WebUI NEVER re-executes anything
"""

from __future__ import annotations
import html
import json
import time
from typing import Any, Generator, Iterator, Union

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        noorrobot_url: str = Field(
            default="http://127.0.0.1:8000",
            description="Base URL of the running NoorRobot server",
        )
        noorrobot_api_key: str = Field(
            default="",
            description="Optional NOOR_API_KEY set on the NoorRobot server",
        )
        request_timeout: int = Field(default=120, description="HTTP timeout seconds")
        max_tokens: int = Field(default=2048, description="Default max_tokens")
        temperature: float = Field(default=0.7, description="Default temperature")
        max_steps: int = Field(default=3, description="Max agentic tool-call steps")

        def __init__(self, **data):
            # Coerce None to empty string so pydantic never rejects a missing api key
            if data.get("noorrobot_api_key") is None:
                data["noorrobot_api_key"] = ""
            super().__init__(**data)

    def __init__(self):
        self.name = "NoorRobot"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[NoorRobot Pipeline] Starting — {self.valves.noorrobot_url}")

    async def on_shutdown(self):
        print("[NoorRobot Pipeline] Shutdown")

    def _base_url(self) -> str:
        return self.valves.noorrobot_url.strip().rstrip("/")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        key = self.valves.noorrobot_api_key or ""
        if key:
            h["Authorization"] = f"Bearer {key}"
        return h

    # Discovery/internal tools that are noise — don't show as UI panels
    _SILENT_TOOLS = {
        "list_tools", "load_tools", "list_skills",
        "get_skill", "tool_info", "list_skill",
    }

    def _details_block(self, call_id: str, name: str, args: dict, result: Any) -> str:
        """
        Render one tool execution as an Open WebUI native collapsible panel.
        This is content — NOT delta.tool_calls — so Open WebUI never re-executes it.
        """
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
        user_message: str,
        model_id: str,
        messages: list[dict[str, Any]],
        body: dict[str, Any],
    ) -> Generator:
        """
        Stream the NoorRobot agent response.
        Tool calls are rendered as <details> blocks — never as delta.tool_calls.
        Always terminates with finish_reason: stop.
        """
        base_url = self._base_url()

        # Extract system prompt if Open WebUI set one
        system = next(
            (m.get("content", "") for m in messages if m.get("role") == "system"),
            "",
        )

        # Build history (exclude system + current user message)
        history = [
            m for m in messages
            if m.get("role") in ("user", "assistant")
        ][:-1]

        payload = {
            "input":        user_message,
            "system":       system,
            "history":      history,
            "max_tokens":   body.get("max_tokens",  self.valves.max_tokens),
            "temperature":  body.get("temperature", self.valves.temperature),
            "max_steps":    body.get("max_steps",   self.valves.max_steps),
            "return_trace": True,
        }

        # --- Call NoorRobot (blocking — agent runs its full loop internally) ---
        try:
            resp = requests.post(
                f"{base_url}/agent",
                headers=self._headers(),
                json=payload,
                timeout=self.valves.request_timeout,
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

        # --- Yield tool call detail blocks (as content, not delta.tool_calls) ---
        # Skip discovery/internal calls — they are noise in the UI
        for i, step in enumerate(trace):
            name   = step.get("name", "tool")
            if name in self._SILENT_TOOLS:
                continue
            args   = step.get("args", {})
            result = step.get("result", "")
            yield self._details_block(f"call_{i}", name, args, result)

        # --- Yield the final reply ---
        if reply:
            yield reply

        # --- Single terminating chunk with finish_reason: stop ---
        # This is critical — Open WebUI stops its retry loop when it sees "stop"
        yield {"choices": [{"delta": {}, "finish_reason": "stop"}]}
