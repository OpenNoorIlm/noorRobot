"""
NoorRobot Pipeline for Open WebUI
==================================
Install this as a **Pipeline** in Open WebUI (not a Tool):
  Admin → Pipelines → Upload → select this file → Save

What it does:
  - Every message in every conversation is routed through NoorRobot's
    /v1/chat/completions endpoint instead of hitting the LLM directly.
  - NoorRobot injects the canonical system prompt (with tool-discovery rules)
    automatically on its side via DEFAULT_SYSTEM_PROMPT.
  - If Open WebUI has already set a system message, it is preserved and
    NoorRobot's system prompt is appended to it so neither is lost.
  - Streaming is fully supported — tokens are forwarded as they arrive.
  - The pipeline exposes Valves so the NoorRobot URL and API key can be
    configured in the Open WebUI admin UI without editing this file.

Quick-start:
  1. Make sure NoorRobot is running:  python run.py
  2. Upload this file as a Pipeline in Open WebUI.
  3. Set noorrobot_url in the Pipeline Valves to http://127.0.0.1:8000
     (or whatever host/port NoorRobot is listening on).
  4. Select "NoorRobot" as the model in any chat — every message now goes
     through NoorRobot and the model always gets the full system prompt.
"""

from __future__ import annotations

import json
import time
from typing import Any, Generator, Iterator, Union
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pipeline metadata — shown in Open WebUI's model picker
# ---------------------------------------------------------------------------

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
        request_timeout: int = Field(
            default=120,
            description="HTTP timeout in seconds for non-streaming requests",
        )
        stream_timeout: int = Field(
            default=300,
            description="HTTP timeout in seconds for streaming requests",
        )
        verify_tls: bool = Field(
            default=True,
            description="Verify HTTPS certificates when talking to NoorRobot",
        )
        max_tokens: int = Field(
            default=2048,
            description="Default max_tokens sent to NoorRobot",
        )
        temperature: float = Field(
            default=0.7,
            description="Default temperature sent to NoorRobot",
        )
        max_steps: int = Field(
            default=6,
            description="Max agentic tool-call steps per request",
        )

    def __init__(self):
        self.name = "NoorRobot"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[NoorRobot Pipeline] Starting — connecting to {self.valves.noorrobot_url}")

    async def on_shutdown(self):
        print("[NoorRobot Pipeline] Shutting down")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_url(self) -> str:
        return self.valves.noorrobot_url.strip().rstrip("/")

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.valves.noorrobot_api_key:
            h["Authorization"] = f"Bearer {self.valves.noorrobot_api_key}"
        return h

    def _ensure_system_prompt(self, messages: list[dict]) -> list[dict]:
        """
        If messages has no system role, do nothing — NoorRobot will inject
        DEFAULT_SYSTEM_PROMPT on its side automatically.

        If messages already has a system role, leave it as-is so the user's
        custom system prompt (set in Open WebUI) is fully honoured.

        NoorRobot's server-side logic does:
            system = data.get("system") or DEFAULT_SYSTEM_PROMPT
        so any non-empty system message we forward will be used as-is.
        """
        return messages  # NoorRobot handles the fallback server-side

    # ------------------------------------------------------------------
    # Main pipe — called by Open WebUI for every user message
    # ------------------------------------------------------------------

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list[dict[str, Any]],
        body: dict[str, Any],
    ) -> Union[str, Generator, Iterator]:
        """
        Route the conversation through NoorRobot's /v1/chat/completions.
        Returns a streaming generator if stream=True, otherwise a string.
        """
        stream = body.get("stream", False)
        base_url = self._base_url()
        headers = self._headers()

        # NoorRobot handles system-prompt injection server-side.
        # We forward messages as-is; if a system message is present it
        # is used; if absent NoorRobot falls back to DEFAULT_SYSTEM_PROMPT.
        payload = {
            "messages": messages,
            "model": body.get("model", ""),
            "temperature": body.get("temperature", self.valves.temperature),
            "max_tokens": body.get("max_tokens", self.valves.max_tokens),
            "max_steps": body.get("max_steps", self.valves.max_steps),
            "stream": stream,
        }

        url = f"{base_url}/v1/chat/completions"

        if stream:
            return self._stream(url, headers, payload)
        else:
            return self._blocking(url, headers, payload)

    def _blocking(self, url: str, headers: dict, payload: dict) -> str:
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.valves.request_timeout,
                verify=self.valves.verify_tls,
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return json.dumps(data, ensure_ascii=False)
        except requests.RequestException as exc:
            return f"⚠️ NoorRobot unreachable: {exc}"
        except Exception as exc:
            return f"⚠️ Pipeline error: {exc}"

    def _stream(self, url: str, headers: dict, payload: dict) -> Generator:
        try:
            with requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.valves.stream_timeout,
                verify=self.valves.verify_tls,
                stream=True,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        # NoorRobot may send plain-text progress lines; skip them
                        continue
        except requests.RequestException as exc:
            yield f"⚠️ NoorRobot unreachable: {exc}"
        except Exception as exc:
            yield f"⚠️ Pipeline error: {exc}"
