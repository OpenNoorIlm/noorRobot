"""
Open WebUI tool for a running NoorRobot server.

Import this file in Open WebUI as a Tool. It is a client only: it does not
start NoorRobot or create an HTTP server.

Changes vs previous version:
  - NOOR_SYSTEM_PROMPT constant — the recommended system prompt is embedded here
    so Open WebUI tools can inject it automatically.
  - noor_system_prompt()  — returns the prompt as a string (useful for piping
    into noor_chat / noor_agent from a pipeline or function).
  - noor_chat() and noor_agent() both accept an optional `system` parameter;
    when omitted they default to NOOR_SYSTEM_PROMPT so every call is tool-aware.
  - noor_discover_tools() — convenience wrapper: calls /tools/list on the server
    and returns a formatted summary without needing the agent loop.

NOTE: This file is a Tool, not a Pipeline. The system prompt here only applies
when one of these tool methods is explicitly called by the model. For the prompt
to be applied to EVERY conversation automatically, use noorRobotPipeline.py
as an Open WebUI Pipeline instead (or in addition to this tool).
"""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Recommended system prompt — keep in sync with SystemPrompt.md
# ---------------------------------------------------------------------------

NOOR_SYSTEM_PROMPT = """\
You are Noor, an intelligent AI assistant running on NoorRobot — a local robot
platform with a rich set of registered tools. You are helpful, concise, and
action-oriented.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS — CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You ALWAYS have access to tools. Never say "I have no tools" or "I cannot do that".

Discovery pattern — follow this every time before claiming a tool is unavailable:

  1. Call list_tools(query="<topic>") to check if a matching tool exists.
  2. If unsure, call load_tools(query="<task>") to get relevant tool names.
  3. Use the returned tool name directly in your next tool call.
  4. Only after list_tools returns nothing for your query should you say the
     capability does not exist.

Tool calling rules:
- ALWAYS use the structured tool-calling interface. Never write tool calls as
  plain text, XML tags, function(...) syntax, or markdown code blocks.
- Arguments must be valid JSON. Infer sensible defaults for optional params.
- One tool call per step; wait for the result before deciding the next step.
- If a tool errors, try once with corrected arguments, then report the error clearly.
- When the user asks "what tools do you have?" or "what can you do?",
  call list_tools(query="all") and summarise the result — do not guess.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISCOVERY TOOLS (always visible to you in every call)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  list_tools(query, limit)   — Find registered tools by topic or name.
                               Use query="all" for the full list.
  load_tools(query, limit)   — Return tool names for a task category.
                               Call this to unlock a group of tools on demand.
  list_skills()              — List available skill directories (toolsf folders).
  list_skill()               — Alias of list_skills.
  get_skill(name)            — Read a .skill file for detailed usage docs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE TOOL CATEGORIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use load_tools(query="<category>") to unlock tools in any of these areas:

  FileSystem       — Read, write, list, search files on the host machine.
  audio_tools      — Convert, trim, mix, fade, speed-adjust audio files.
  automation       — Mouse, keyboard, screen automation (auto_* tools).
  body             — Robot body / servo control.
  browser_control  — Click, fill, evaluate JS in a browser.
  calendar         — Read and create calendar events.
  capture          — Screenshot and screen recording.
  cmd              — Run shell commands on the host (cmd_run_once).
  codeExecutor     — Execute Python or JS code snippets.
  csv_tools        — Parse and transform CSV data.
  esp32_os         — Control the ESP32 robot: eyes, movement, sensors.
  git_tools        — Git status, commit, push, diff.
  gmail            — Read, search, send, draft emails via Gmail.
  grapher          — Plot charts and graphs from data.
  hadith           — Search Bukhari and Muslim hadith collections.
  http_client      — Make arbitrary HTTP requests.
  image_tools      — Resize, crop, convert images.
  network_tools    — Ping, port-scan, network diagnostics.
  noor_face_anim   — Play face animations on the NoorRobot display.
  notes            — Create and retrieve personal notes.
  pdf_tools        — Read, merge, split, annotate PDF files.
  powershell       — Run PowerShell commands (Windows).
  process_manager  — List, kill, monitor running processes.
  prompt_library   — Save and retrieve prompt templates.
  quran            — Search Quran verses and translations.
  rag_ingest       — Add documents to the Islamic RAG knowledge base.
  report_generator — Generate formatted reports from data.
  ringtones        — Manage and play ringtones.
  system_info      — CPU, RAM, disk, battery info.
  time             — Current time, timezones, date calculations.
  todo             — Create and manage a to-do list.
  toolbox          — Miscellaneous utility tools.
  video_tools      — Trim, convert, extract frames from video.
  visioning        — Run vision/image analysis tasks.
  web              — Search the web and fetch page content.
  wslKaliLinux     — Run commands inside WSL Kali Linux.
  wslUbuntu        — Run commands inside WSL Ubuntu.
  ytTranscript     — Fetch YouTube video transcripts.
  zip_tools        — Compress and extract ZIP/tar archives.

  Face memory (always available):
    save_face_memory(label, image)  — Register a face fingerprint (no image stored).
    recognize_face_memory(image)    — Identify a known face.
    list_face_memory()              — List known face labels.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISLAMIC KNOWLEDGE (RAG)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NoorRobot has a retrieval-augmented knowledge base loaded with Quran translations
and hadith (Bukhari, Muslim). For Islamic questions, prefer the quran and hadith
tools over your internal knowledge. Always cite sources when answering.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Be concise. Prefer action over lengthy explanation.
- For multi-step tasks, briefly narrate what you are doing before and after each tool call.
- On errors, report what failed and what you will try next.
- When a task is complete, give a short summary of what was done.
- Do not repeat tool arguments back to the user verbatim — summarise instead.
- Maintain a friendly, calm tone. You are a helpful robot assistant named Noor.
"""


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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def noor_system_prompt(self) -> str:
        """
        Return the recommended NoorRobot system prompt.
        Inject this into the 'system' field of noor_chat or noor_agent to
        ensure the model always uses the tool-discovery pattern correctly.
        """
        return NOOR_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # Core chat / agent
    # ------------------------------------------------------------------

    def noor_chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system: str = "",
    ) -> str:
        """
        Send OpenAI-format messages to NoorRobot and return the assistant text.
        If no system message is present in `messages` and `system` is empty,
        the recommended NOOR_SYSTEM_PROMPT is injected automatically so the
        model always has tool-discovery instructions.
        """
        effective_system = system or NOOR_SYSTEM_PROMPT
        # Inject system message if not already present
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            messages = [{"role": "system", "content": effective_system}] + list(messages)
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

    def noor_agent(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        system: str = "",
        max_steps: int = 6,
    ) -> str:
        """
        Ask NoorRobot to complete a task using its registered tools.
        Uses NOOR_SYSTEM_PROMPT by default so the model always knows how to
        discover and invoke tools correctly.
        """
        data = self._request(
            "POST",
            "/agent",
            {
                "input": prompt,
                "system": system or NOOR_SYSTEM_PROMPT,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "max_steps": max_steps,
            },
        )
        return str(data.get("reply", json.dumps(data, ensure_ascii=False)))

    # ------------------------------------------------------------------
    # RAG / Vision
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Tool management
    # ------------------------------------------------------------------

    def noor_list_tools(self) -> str:
        """List all tools registered by the running NoorRobot server."""
        return json.dumps(self._request("GET", "/tools/list"), ensure_ascii=False)

    def noor_discover_tools(self, query: str = "all") -> str:
        """
        Ask NoorRobot's agent to call list_tools and return a human-readable
        summary. More useful than noor_list_tools when you want the model to
        also describe what each tool does.
        Use query="all" for everything or a topic like "gmail", "esp32", "audio".
        """
        return self.noor_agent(
            prompt=f'Call list_tools with query="{query}" and give me a clear, grouped summary of the results.',
            system=NOOR_SYSTEM_PROMPT,
        )

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

    # ------------------------------------------------------------------
    # Models / info
    # ------------------------------------------------------------------

    def noor_models(self) -> str:
        """List models exposed by the running NoorRobot OpenAI-compatible API."""
        return json.dumps(self._request("GET", "/v1/models"), ensure_ascii=False)

    # ------------------------------------------------------------------
    # Animations
    # ------------------------------------------------------------------

    def noor_animation_list(
        self,
        eye_key: str = "",
        mouth_key: str = "",
        anim_type: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """List bundled face animations with optional eye, mouth, and type filters."""
        params: dict[str, Any] = {"limit": max(1, min(500, limit)), "offset": max(0, offset)}
        if eye_key:
            params["eye_key"] = eye_key
        if mouth_key:
            params["mouth_key"] = mouth_key
        if anim_type:
            params["anim_type"] = anim_type
        data = self._request("GET", "/animations", params)
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

    # ------------------------------------------------------------------
    # ESP32 shortcuts
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Face memory
    # ------------------------------------------------------------------

    def noor_save_face(self, label: str, image: str) -> str:
        """Save a face fingerprint through NoorRobot; the image is not stored."""
        data = self._request("POST", "/memory/faces/save", {"label": label, "image": image})
        return json.dumps(data, ensure_ascii=False)

    def noor_recognize_face(self, image: str) -> str:
        """Recognize a face using NoorRobot's hashed face-memory store."""
        data = self._request("POST", "/memory/faces/recognize", {"image": image})
        return json.dumps(data, ensure_ascii=False)

    def noor_list_faces(self) -> str:
        """List known face labels without returning image data."""
        return json.dumps(self._request("GET", "/memory/faces"), ensure_ascii=False)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def noor_health(self) -> str:
        """Check whether the NoorRobot server is reachable."""
        return json.dumps(self._request("GET", "/health"), ensure_ascii=False)