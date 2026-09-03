"""
Open WebUI tool for a running NoorRobot server.

Import this file in Open WebUI as a Tool. It is a client only: it does not
start NoorRobot or create an HTTP server.
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        noorrobot_url: str = Field(
            default="http://127.0.0.1:8000",
            description="Base URL of the already-running NoorRobot server",
        )
        noorrobot_api_key: str = Field(
            default="",
            description="Optional NOOR_API_KEY used by the NoorRobot server",
        )
        request_timeout: int = Field(default=120, description="HTTP timeout in seconds")
        retry_count: int = Field(default=2, description="Retries for timeouts and transient HTTP errors")
        verify_tls: bool = Field(default=True, description="Verify HTTPS certificates")

    def __init__(self):
        self.valves = self.Valves()

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        base_url = self.valves.noorrobot_url.strip().rstrip("/")
        if not base_url:
            raise ValueError("noorrobot_url is required")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("noorrobot_url must be an absolute http:// or https:// URL")
        headers = {"Content-Type": "application/json"}
        if self.valves.noorrobot_api_key:
            headers["Authorization"] = f"Bearer {self.valves.noorrobot_api_key}"
        attempts = max(0, min(5, self.valves.retry_count)) + 1
        transient_statuses = {408, 425, 429, 500, 502, 503, 504}
        response = None
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = requests.request(
                    method.upper(),
                    f"{base_url}{path}",
                    headers=headers,
                    json=payload,
                    timeout=max(1, self.valves.request_timeout),
                    verify=self.valves.verify_tls,
                )
                if response.status_code not in transient_statuses or attempt == attempts - 1:
                    break
            except requests.RequestException as exc:
                last_error = exc
                if attempt == attempts - 1:
                    raise RuntimeError(f"Could not reach NoorRobot at {base_url}: {exc}") from exc
            time.sleep(min(2.0, 0.25 * (2 ** attempt)))
        if response is None:
            raise RuntimeError(f"Could not reach NoorRobot at {base_url}: {last_error}")
        try:
            data = response.json()
        except ValueError:
            data = {"text": response.text}
        if not response.ok:
            raise RuntimeError(f"NoorRobot returned HTTP {response.status_code}: {data}")
        return data

    def noor_chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Send OpenAI-format messages to NoorRobot and return the assistant text."""
        data = self._request(
            "POST",
            "/v1/chat/completions",
            {
                "messages": messages,
                "model": model or None,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        choices = data.get("choices", [])
        if choices and choices[0].get("message"):
            return str(choices[0]["message"].get("content", ""))
        return json.dumps(data, ensure_ascii=False)

    def noor_rag(
        self,
        query: str,
        history: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Ask NoorRobot's Islamic RAG system and include source metadata."""
        data = self._request("POST", "/rag/ask", {
            "query": query,
            "history": history or [],
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        answer = data.get("answer", "")
        sources = data.get("sources", [])
        return f"{answer}\n\nSources: {json.dumps(sources, ensure_ascii=False)}" if sources else str(answer)

    def noor_vision(self, prompt: str, image: str, max_tokens: int = 1024) -> str:
        """Send an image path, URL, or data URL to NoorRobot vision."""
        data = self._request("POST", "/vision", {
            "prompt": prompt,
            "image": image,
            "max_tokens": max_tokens,
        })
        return str(data.get("reply", json.dumps(data, ensure_ascii=False)))

    def noor_agent(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        """Ask NoorRobot to complete a task using its registered tools."""
        data = self._request(
            "POST",
            "/agent",
            {"input": prompt, "max_tokens": max_tokens, "temperature": temperature},
        )
        return str(data.get("reply", json.dumps(data, ensure_ascii=False)))

    def noor_list_tools(self) -> str:
        """List tools registered by the running NoorRobot server."""
        return json.dumps(self._request("GET", "/tools/list"), ensure_ascii=False)

    def noor_call_tool(self, tool_name: str, tool_params: dict[str, Any] | None = None) -> str:
        """Call one NoorRobot tool by name."""
        data = self._request(
            "POST",
            "/tools/call",
            {"tool_name": tool_name, "tool_params": tool_params or {}},
        )
        return json.dumps(data, ensure_ascii=False)

    def noor_call_tools(self, calls: list[dict[str, Any]]) -> str:
        """Call multiple NoorRobot tools in one request."""
        data = self._request("POST", "/tools/call_batch", {"calls": calls})
        return json.dumps(data, ensure_ascii=False)

    def noor_models(self) -> str:
        """List models exposed by the running NoorRobot OpenAI-compatible API."""
        return json.dumps(self._request("GET", "/v1/models"), ensure_ascii=False)

    def noor_animation_list(
        self,
        eye_key: str = "",
        mouth_key: str = "",
        anim_type: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """List bundled face animations with optional eye, mouth, and type filters."""
        params = {"limit": max(1, min(500, limit)), "offset": max(0, offset)}
        if eye_key:
            params["eye_key"] = eye_key
        if mouth_key:
            params["mouth_key"] = mouth_key
        if anim_type:
            params["anim_type"] = anim_type
        data = self._request("GET", "/animations", params=params)
        return json.dumps(data, ensure_ascii=False)

    def noor_animation_get(self, name: str) -> str:
        """Get metadata and media paths for a bundled face animation."""
        if not name.strip():
            raise ValueError("animation name is required")
        return json.dumps(self._request("GET", f"/animation/{name.strip()}"), ensure_ascii=False)

    def noor_animation_keys(self) -> str:
        """List available eye keys, mouth keys, and animation types."""
        return json.dumps(self._request("GET", "/keys"), ensure_ascii=False)

    def noor_animation_stats(self) -> str:
        """Return counts and type breakdown for bundled face animations."""
        return json.dumps(self._request("GET", "/stats"), ensure_ascii=False)

    def noor_esp32_eyes(self, expression: str, offset_x: int = 0, offset_y: int = 0) -> str:
        """Control ESP32-OS TFT eyes through NoorRobot's registered bridge tool."""
        return self.noor_call_tool("esp32_eyes", {
            "expression": expression,
            "offset_x": offset_x,
            "offset_y": offset_y,
        })

    def noor_esp32_move(self, direction: str, value: str = "", speed: str = "") -> str:
        """Move or stop the ESP32-OS robot through NoorRobot."""
        return self.noor_call_tool("esp32_move", {
            "direction": direction,
            "value": value,
            "speed": speed,
        })

    def noor_esp32_sensor(self, sensor: str) -> str:
        """Read a sensor from the ESP32-OS robot through NoorRobot."""
        return self.noor_call_tool("esp32_sensor", {"sensor": sensor})

    def noor_save_face(self, label: str, image: str) -> str:
        """Save a face fingerprint through NoorRobot; the image is not stored there."""
        data = self._request("POST", "/memory/faces/save", {"label": label, "image": image})
        return json.dumps(data, ensure_ascii=False)

    def noor_recognize_face(self, image: str) -> str:
        """Recognize a face using NoorRobot's hashed face-memory store."""
        data = self._request("POST", "/memory/faces/recognize", {"image": image})
        return json.dumps(data, ensure_ascii=False)

    def noor_list_faces(self) -> str:
        """List known face labels without returning image data."""
        return json.dumps(self._request("GET", "/memory/faces"), ensure_ascii=False)

    def noor_health(self) -> str:
        """Check whether the NoorRobot server is reachable."""
        return json.dumps(self._request("GET", "/health"), ensure_ascii=False)
