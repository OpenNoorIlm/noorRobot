"""
api.py  —  NoorRobot Local HTTP API (no extra dependencies)
==========================================================
Provides a simple JSON HTTP API using Python's stdlib.

Endpoints:
  GET  /health
  GET  /version
  GET  /tools/list
  GET  /tools/info?name=tool_name
  GET  /tools/schema
  POST /chat
  POST /chat/stream
  POST /agent
  POST /vision
  POST /vision/agent
  POST /rag/ask
  POST /rag/stream
  POST /rag/rebuild
  POST /tools/call
  POST /tools/call_batch

Run:
  python -m app.services.api

Env:
  NOOR_API_KEY      (optional) Require Bearer/X-API-Key auth
  NOOR_CORS_ORIGIN  (optional) CORS origin, default "*"
"""

from __future__ import annotations

import json
import logging
import os
import asyncio
import time
from typing import Any
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from app.utils import groq as groq_utils
from app.utils.groq import DEFAULT_SYSTEM_PROMPT
from app.utils.RAG import rag, Message
from app.utils.vectorStore import vector_store
from app.utils.face_memory import list_faces, recognize_face, save_face
from app.services import animations

logger = logging.getLogger("NoorRobot.API")

API_KEY = os.getenv("NOOR_API_KEY", "") or os.getenv("API_KEY", "")
CORS_ORIGIN = os.getenv("NOOR_CORS_ORIGIN", "*")
_VECTOR_READY = False


def _wants_tools(prompt: str, request: dict) -> bool:
    # Explicit opt-out: caller passed use_tools=false
    if request.get("use_tools") is False:
        return False
    # Explicit opt-in: caller forced it
    if request.get("force_tool") is True:
        return True
    # Default to True — always route through the agent so the discovery
    # layer (list_tools / load_tools) is always available to the model.
    # Callers that want plain chat must pass use_tools=false explicitly.
    return True


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length > 0 else b"{}"
    try:
        logger.debug("Reading JSON body (%s bytes)", length)
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        logger.exception("Failed to parse JSON")
        return {}


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200):
    logger.debug("Responding %s with keys=%s", status, list(payload.keys()))
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _file_response(handler: BaseHTTPRequestHandler, path, content_type: str):
    data = path.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _parse_history(history: list | None) -> list[Message]:
    msgs: list[Message] = []
    for item in history or []:
        role = item.get("role", "user")
        content = item.get("content", "")
        msgs.append(Message(role=role, content=content))
    return msgs


def _require_auth(handler: BaseHTTPRequestHandler) -> bool:
    if not API_KEY:
        logger.debug("No API key required")
        return True
    auth = handler.headers.get("Authorization", "")
    x_api = handler.headers.get("X-API-Key", "")
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    elif x_api:
        token = x_api.strip()
    if token != API_KEY:
        logger.warning("Unauthorized request from %s", handler.client_address)
        _json_response(handler, {"error": "unauthorized"}, status=401)
        return False
    return True


def _send_sse_headers(handler: BaseHTTPRequestHandler):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.send_header("X-Accel-Buffering", "no")
    handler.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()


def _sse_write(handler: BaseHTTPRequestHandler, data: str, event: str | None = None):
    if event:
        handler.wfile.write(f"event: {event}\n".encode("utf-8"))
    handler.wfile.write(f"data: {data}\n\n".encode("utf-8"))
    handler.wfile.flush()


class NoorAPIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        logger.info("GET %s from %s", path or "/", self.client_address)
        if not _require_auth(self):
            return

        if path in ("", "/health"):
            return _json_response(
                self,
                {
                    "ok": True,
                    "service": "NoorRobot API",
                    "vector_ready": _VECTOR_READY,
                },
            )

        if path == "/version":
            return _json_response(
                self,
                {
                    "assistant": groq_utils.ASSISTANT_NAME,
                    "text_model": groq_utils.TEXT_MODEL,
                    "vision_model": groq_utils.VISION_MODEL,
                    "tools_count": len(groq_utils.FUNCTIONS),
                },
            )

        if path in ("/v1/models", "/models"):
            models = groq_utils.list_models()
            return _json_response(self, {"object": "list", "data": models})

        if path == "/memory/faces":
            return _json_response(self, {"data": list_faces()})

        if path == "/animations":
            return _json_response(self, animations.list_animations(
                eye_key=(qs.get("eye_key") or [None])[0],
                mouth_key=(qs.get("mouth_key") or [None])[0],
                anim_type=(qs.get("anim_type") or [None])[0],
                limit=(qs.get("limit") or [50])[0],
                offset=(qs.get("offset") or [0])[0],
            ))

        if path == "/animations/search":
            results = animations.search_animations(
                eye=(qs.get("eye") or [None])[0],
                mouth=(qs.get("mouth") or [None])[0],
            )
            return _json_response(self, {"count": len(results), "results": results})

        if path.startswith("/animation/"):
            parts = path.split("/")
            if len(parts) < 3:
                return _json_response(self, {"error": "animation name required"}, status=400)
            name = parts[2]
            animation = animations.get_animation(name)
            suffix = "/" + parts[-1] if len(parts) > 3 else ""
            if suffix == "/video" or suffix == "/static":
                file_path, content_type = animations.get_file(name, suffix[1:])
                return _file_response(self, file_path, content_type)
            if suffix == "/timeline":
                return _json_response(self, {"name": name, "timeline": animation["timeline"]})
            if suffix == "/description":
                return _json_response(self, {"name": name, "description": animation["description"]})
            if suffix == "/paths":
                return _json_response(self, {"name": name, "video": animation["video"], "static": animation["static"], "video_url": f"/animation/{name}/video", "static_url": f"/animation/{name}/static"})
            if suffix == "":
                return _json_response(self, animation)
            return _json_response(self, {"error": "not found"}, status=404)

        if path == "/keys":
            return _json_response(self, animations.keys())

        if path == "/stats":
            return _json_response(self, animations.stats())

        if path == "/config":
            return _json_response(self, animations.config())

        if path in ("/keys/eye", "/keys/mouth", "/keys/anim_type"):
            kind = path.split("/")[-1]
            return _json_response(self, {f"{kind}_keys": animations.key_values(kind)})

        if path.startswith("/keys/"):
            parts = path.split("/")
            if len(parts) >= 4:
                kind, value = parts[2], parts[3]
                if len(parts) == 4:
                    return _json_response(self, {"key": value, "count": len(animations.key_animations(kind, value)), "animations": animations.key_animations(kind, value)})
                if parts[4] == "animations":
                    results = animations.key_animations(kind, value)
                    return _json_response(self, {"count": len(results), "results": results})

        if path.startswith("/keys/combo/"):
            parts = path.split("/")
            if len(parts) >= 4:
                results = animations.combo(parts[2], parts[3])
                return _json_response(self, {"count": len(results), "results": results})

        if path == "/tools/list":
            return _json_response(self, {"tools": sorted(groq_utils.FUNCTIONS.keys())})

        if path == "/tools/info":
            name = (qs.get("name") or [""])[0]
            fn = groq_utils.FUNCTIONS.get(name)
            if not fn:
                return _json_response(self, {"error": "tool not found"}, status=404)
            return _json_response(
                self,
                {
                    "name": name,
                    "doc": (fn.__doc__ or "").strip(),
                    "params": getattr(fn, "_params", None),
                },
            )

        if path == "/tools/schema":
            return _json_response(self, {"tools": groq_utils.TOOLS})

        return _json_response(self, {"error": "not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        data = _read_json(self)

        logger.info("POST %s from %s", path, self.client_address)
        if not _require_auth(self):
            return

        try:
            if path in ("/v1/chat/completions", "/chat/completions"):
                messages = data.get("messages", [])
                if not isinstance(messages, list) or not messages:
                    return _json_response(self, {"error": {"message": "messages must be a non-empty array", "type": "invalid_request_error"}}, status=400)
                user_message = messages[-1].get("content", "")
                use_tools = _wants_tools(user_message, data)
                if data.get("stream"):
                    if use_tools:
                        history = [message for message in messages[:-1] if message.get("role") != "system"]
                        system = next((message.get("content", "") for message in messages if message.get("role") == "system"), DEFAULT_SYSTEM_PROMPT)
                        _send_sse_headers(self)

                        def _tool_progress(name, args, result):
                            result_text = str(result)
                            if len(result_text) > 500:
                                result_text = result_text[:500] + "..."
                            call_id = f"noor-tool-{int(time.time() * 1000)}"
                            _sse_write(self, json.dumps({
                                "id": "noor-tool-call",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": data.get("model") or groq_utils.TEXT_MODEL,
                                "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}, "finish_reason": "tool_calls"}],
                            }))
                            _sse_write(self, json.dumps({
                                "id": "noor-tool-progress",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": data.get("model") or groq_utils.TEXT_MODEL,
                                "choices": [{"index": 0, "delta": {"role": "tool", "content": result_text}, "finish_reason": None}],
                            }))

                        reply = groq_utils.agent(
                            user_message,
                            system=system,
                            history=history,
                            model=data.get("model"),
                            max_tokens=int(data.get("max_tokens", 1024)),
                            temperature=float(data.get("temperature", 0.7)),
                            max_steps=int(data.get("max_steps", 6)),
                            max_tools=max(40, int(data.get("max_tools", 40))),
                            on_tool=_tool_progress,
                        )
                        _sse_write(self, json.dumps({
                            "id": "noor-chat-completion",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": data.get("model") or groq_utils.TEXT_MODEL,
                            "choices": [{"index": 0, "delta": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                        }))
                        _sse_write(self, "[DONE]")
                        return
                    _send_sse_headers(self)
                    for token in groq_utils.stream_chat(
                        messages,
                        max_tokens=int(data.get("max_tokens", 1024)),
                        temperature=float(data.get("temperature", 0.7)),
                        model=data.get("model"),
                    ):
                        if token:
                            _sse_write(self, json.dumps({
                                "id": "noor-chat-completion",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": data.get("model") or groq_utils.TEXT_MODEL,
                                "choices": [{"index": 0, "delta": {"role": "assistant", "content": token}, "finish_reason": None}],
                            }))
                    _sse_write(self, "[DONE]")
                    return
                if not use_tools:
                    reply = groq_utils.complete(
                        messages,
                        max_tokens=int(data.get("max_tokens", 1024)),
                        temperature=float(data.get("temperature", 0.7)),
                        model=data.get("model"),
                    )
                    return _json_response(self, {
                        "id": "noor-chat-completion",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": data.get("model") or groq_utils.TEXT_MODEL,
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    })
                history = [message for message in messages[:-1] if message.get("role") != "system"]
                system = next((message.get("content", "") for message in messages if message.get("role") == "system"), DEFAULT_SYSTEM_PROMPT)
                user_message = messages[-1].get("content", "")
                reply = groq_utils.agent(
                    user_message,
                    system=system,
                    history=history,
                    model=data.get("model"),
                    max_tokens=int(data.get("max_tokens", 1024)),
                    temperature=float(data.get("temperature", 0.7)),
                    max_steps=int(data.get("max_steps", 6)),
                    max_tools=max(40, int(data.get("max_tools", 40))),
                )
                return _json_response(self, {
                    "id": "noor-chat-completion",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": data.get("model") or groq_utils.TEXT_MODEL,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                })

            if path == "/memory/faces/save":
                return _json_response(self, save_face(str(data.get("label", "")), data.get("image", "")))

            if path == "/memory/faces/recognize":
                return _json_response(self, recognize_face(data.get("image", "")))

            if path == "/chat":
                prompt = data.get("prompt", "")
                system = data.get("system") or DEFAULT_SYSTEM_PROMPT
                history = data.get("history", [])
                max_tokens = int(data.get("max_tokens", 1024))
                temperature = float(data.get("temperature", 0.7))
                max_return_context = int(data.get("max_return_context", 4000))
                use_tools = bool(data.get("use_tools", True))
                if use_tools:
                    prompt_l = prompt.lower()
                    is_web_query = ("web search" in prompt_l or "search the web" in prompt_l or "news" in prompt_l)
                    is_cmd_query = ("execute this command" in prompt_l or "run this command" in prompt_l or "execute command" in prompt_l or "run command" in prompt_l)
                    force_tool = bool(data.get("force_tool", False))
                    allowlist = data.get("tool_allowlist")
                    logger.info("/chat: use_tools=true force_tool=%s allowlist=%s data_tool_choice=%s", force_tool, allowlist, data.get("tool_choice"))
                    if allowlist is None and is_web_query:
                        allowlist = ["search", "get_content", "get_content_by_query", "get_url_by_query"]
                        force_tool = True
                    if allowlist is None and is_cmd_query:
                        allowlist = ["cmd_run_once"]
                        force_tool = True
                    # Force a specific tool when the intent is clear to reduce tool-call hallucinations.
                    forced_choice = None
                    if is_cmd_query:
                        forced_choice = {"type": "function", "function": {"name": "cmd_run_once"}}
                    elif is_web_query:
                        forced_choice = {"type": "function", "function": {"name": "search"}}
                    if forced_choice and allowlist is not None:
                        name = forced_choice.get("function", {}).get("name")
                        if name and name not in allowlist:
                            allowlist = list(allowlist) + [name]
                    temp_for_agent = 0.0 if forced_choice else temperature
                    max_steps = 2 if forced_choice else int(data.get("max_steps", 6))
                    reply = groq_utils.agent(
                        prompt,
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temp_for_agent,
                        max_return_context=max_return_context,
                        max_steps=max_steps,
                        include_auto_tools=bool(data.get("include_auto_tools", False)),
                        max_tools=int(data.get("max_tools", 50)),
                        tool_allowlist=allowlist,
                        tool_choice=forced_choice if forced_choice else ("required" if force_tool else "auto"),
                    )
                else:
                    reply = groq_utils.chat(
                        prompt,
                        system=system,
                        history=history,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                return _json_response(self, {"reply": reply})

            if path == "/chat/stream":
                prompt = data.get("prompt", "")
                system = data.get("system") or DEFAULT_SYSTEM_PROMPT
                history = data.get("history", [])
                max_tokens = int(data.get("max_tokens", 1024))
                temperature = float(data.get("temperature", 0.7))
                messages = [{"role": "system", "content": system}]
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": prompt})
                _send_sse_headers(self)
                for tok in groq_utils.stream_chat(messages, max_tokens=max_tokens, temperature=temperature):
                    if tok:
                        _sse_write(self, tok)
                _sse_write(self, "[DONE]", event="done")
                return

            if path == "/agent":
                user_input = data.get("input", "")
                system = data.get("system") or DEFAULT_SYSTEM_PROMPT
                max_tokens = int(data.get("max_tokens", 1024))
                max_return_context = int(data.get("max_return_context", 4000))
                reply = groq_utils.agent(
                    user_input,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=float(data.get("temperature", 0.2)),
                    max_return_context=max_return_context,
                    include_auto_tools=bool(data.get("include_auto_tools", False)),
                    max_tools=int(data.get("max_tools", 50)),
                    tool_allowlist=data.get("tool_allowlist"),
                )
                return _json_response(self, {"reply": reply})

            if path == "/vision":
                prompt = data.get("prompt", "")
                image = data.get("image", "")
                system = data.get("system") or DEFAULT_SYSTEM_PROMPT
                max_tokens = int(data.get("max_tokens", 1024))
                reply = groq_utils.vision(prompt, image, system=system, max_tokens=max_tokens)
                return _json_response(self, {"reply": reply})

            if path == "/vision/agent":
                prompt = data.get("prompt", "")
                image = data.get("image", "")
                system = data.get("system") or DEFAULT_SYSTEM_PROMPT
                max_tokens = int(data.get("max_tokens", 1024))
                max_return_context = int(data.get("max_return_context", 4000))
                reply = groq_utils.vision_agent(
                    prompt,
                    image,
                    system=system,
                    max_tokens=max_tokens,
                    max_return_context=max_return_context,
                    include_auto_tools=bool(data.get("include_auto_tools", False)),
                    max_tools=int(data.get("max_tools", 50)),
                    tool_allowlist=data.get("tool_allowlist"),
                )
                return _json_response(self, {"reply": reply})

            if path == "/rag/ask":
                query = data.get("query", "")
                history = _parse_history(data.get("history", []))
                system_prompt = data.get("system_prompt", "")
                temperature = float(data.get("temperature", os.getenv("RAG_TEMP", "0.7")))
                max_tokens = int(data.get("max_tokens", os.getenv("RAG_MAX_TOK", "1024")))
                if system_prompt:
                    result = rag.ask(
                        query,
                        history,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                else:
                    result = rag.ask(
                        query,
                        history,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                return _json_response(
                    self,
                    {
                        "answer": result.answer,
                        "sources": result.sources,
                        "retrieved_chunks": result.retrieved_chunks,
                        "used_chunks": result.used_chunks,
                        "retrieval_ms": result.retrieval_ms,
                        "generation_ms": result.generation_ms,
                        "used_retrieval": result.used_retrieval,
                    },
                )

            if path == "/rag/stream":
                query = data.get("query", "")
                history = _parse_history(data.get("history", []))
                system_prompt = data.get("system_prompt", "")
                temperature = float(data.get("temperature", os.getenv("RAG_TEMP", "0.7")))
                max_tokens = int(data.get("max_tokens", os.getenv("RAG_MAX_TOK", "1024")))
                _send_sse_headers(self)

                async def _run_stream():
                    if system_prompt:
                        stream = rag.ask_stream(
                            query,
                            history,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    else:
                        stream = rag.ask_stream(
                            query,
                            history,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    async for chunk in stream:
                        _sse_write(self, chunk)

                asyncio.run(_run_stream())
                _sse_write(self, "[DONE]", event="done")
                return

            if path == "/rag/rebuild":
                rag.rebuild_index()
                return _json_response(self, {"ok": True})

            if path == "/tools/call":
                tool_name = data.get("tool_name", "")
                tool_params = data.get("tool_params", {})
                fn = groq_utils.FUNCTIONS.get(tool_name)
                if not fn:
                    return _json_response(self, {"error": "tool not found"}, status=404)
                out = fn(**(tool_params or {}))
                return _json_response(self, {"result": out})

            if path == "/tools/call_batch":
                calls = data.get("calls", []) or []
                results: list[Any] = []
                for call in calls:
                    tool_name = call.get("tool_name", "")
                    tool_params = call.get("tool_params", {})
                    fn = groq_utils.FUNCTIONS.get(tool_name)
                    if not fn:
                        results.append({"error": "tool not found", "tool_name": tool_name})
                        continue
                    try:
                        results.append({"tool_name": tool_name, "result": fn(**(tool_params or {}))})
                    except Exception as exc:
                        results.append({"tool_name": tool_name, "error": str(exc)})
                return _json_response(self, {"results": results})

        except Exception as exc:
            logger.exception("API error")
            return _json_response(self, {"error": str(exc)}, status=500)

        return _json_response(self, {"error": "not found"}, status=404)

    def log_message(self, format, *args):
        # Reduce noisy default logging; use standard logger instead.
        logger.info("%s - %s", self.address_string(), format % args)


def run(host: str = "0.0.0.0", port: int = 8000):
    global _VECTOR_READY
    try:
        vector_store.load_or_build()
        _VECTOR_READY = True
        logger.info("Vector store loaded successfully")
    except Exception as e:
        logger.error("Error during vector store setup: %s", e)
        _VECTOR_READY = False

    # Start the real API immediately so clients never receive a temporary 501
    # response from a startup-only test handler.
    try:
        logger.info("Starting main NoorRobot API server...")
        server = ThreadingHTTPServer((host, int(port)), NoorAPIHandler)
        logger.info("NoorRobot API running on http://%s:%s", host, port)
        logger.info("Server started successfully, waiting for connections...")
        server.serve_forever()
    except Exception as e:
        logger.error("Main server error: %s", e)
        logger.info("Trying alternative server binding...")
        # Try binding to localhost explicitly
        try:
            server = ThreadingHTTPServer(("localhost", int(port)), NoorAPIHandler)
            logger.info("NoorRobot API running on http://localhost:%s", port)
            server.serve_forever()
        except Exception as e2:
            logger.error("Alternative server binding also failed: %s", e2)
            raise
    finally:
        logger.info("Server shutting down")
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
