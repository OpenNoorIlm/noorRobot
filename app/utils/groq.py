"""
ai_client.py  —  NoorRobot OpenAI-Compatible Client & LLM Utilities
===================================================
Provides:
    - OpenAI-compatible client configuration from app/utils/.env
  - @tool decorator for registering function-calling tools
  - chat()         — simple one-shot text completion
  - stream_chat()  — streaming text completion (used by RAG.py)
  - vision()       — image + text completion
  - agent()        — agentic loop with tool calling
  - vision_agent() — vision + tool calling combined
    - get_client()   — public OpenAI-compatible client (used by RAGService)

RAG.py integration:
    from app.utils.groq import get_client, TEXT_MODEL, VISION_MODEL
"""

import os
import json
import base64
import random
import logging
import functools
from openai import OpenAI
from dotenv import load_dotenv
# NOTE: Do not import app.skills/tools/speak here to avoid circular imports.

logger = logging.getLogger("NoorRobot.AI")

# ============================================
# LOAD API KEYS FROM .env
# ============================================

_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_PATH)

ASSISTANT_NAME     = os.getenv("ASSISTANT_NAME",     "Noor")
JARVIS_USER_TITLE  = os.getenv("JARVIS_USER_TITLE",  "User")

# ============================================
# CANONICAL DEFAULT SYSTEM PROMPT
# ============================================
# Single source of truth used by agent(), chat(), and api.py fallbacks.
# Tells the model about the discovery pattern so it never claims "I have no tools".

DEFAULT_SYSTEM_PROMPT = f"""\
You are {'{ASSISTANT_NAME}'}, an intelligent AI assistant running on NoorRobot — a local robot
platform with a rich set of registered tools. You are helpful, concise, and action-oriented.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS — WHEN TO USE THEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Only call tools when the user asks you to DO something or GET something.
Never call tools for greetings, casual conversation, or simple questions
you can answer from knowledge.

Examples of when NOT to use tools:
  "Hello", "How are you?", "What is 2+2?", "Tell me about Islam"

Examples of when to USE tools:
  "Check my Gmail", "What time is it?", "List my notes", "Take a screenshot"
  "Do you have access to gmail?", "What tools do you have?"

Discovery pattern — only when a tool is needed and you are unsure which one:
  1. Call list_tools(query="<topic>") to find matching tool names.
  2. Call tool_info(tool_name="<name>") to get EXACT parameter names before calling it.
  3. Call the tool using ONLY the parameter names returned by tool_info.
  4. Never guess parameter names — always check tool_info first.
  5. Only say a capability doesn't exist after list_tools returns nothing.

Tool calling rules:
- Use ONLY the structured JSON tool-calling interface (OpenAI function-calling format).
- NEVER write tool calls as plain text, XML tags like <function=name>, or markdown.
- If you write a tool call as text instead of using the interface, it will NOT execute.
- One tool call per step; wait for the result before the next step.
- If a tool errors, try once with corrected arguments, then report the error.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DISCOVERY TOOLS (available when needed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  list_tools(query, limit)   — Find tools by topic. Use query="all" for everything.
  load_tools(query, limit)   — Unlock a tool group on demand.
  tool_info(tool_name)       — Get EXACT parameter names for a tool. Use before calling any tool.
  list_skills()              — List available skill directories.
  get_skill(name)            — Read a skill file for detailed usage docs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE TOOL CATEGORIES (use load_tools to unlock any of these)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  FileSystem, audio_tools, automation, body, browser_control, calendar,
  capture, cmd, codeExecutor, csv_tools, esp32_os, git_tools, gmail, grapher,
  hadith, http_client, image_tools, network_tools, noor_face_anim, notes,
  pdf_tools, powershell, process_manager, prompt_library, quran, rag_ingest,
  report_generator, ringtones, system_info, time, todo, toolbox, video_tools,
  visioning, web, wslKaliLinux, wslUbuntu, ytTranscript, zip_tools.

  Face memory: save_face_memory, recognize_face_memory, list_face_memory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISLAMIC KNOWLEDGE — prefer quran/hadith tools over internal knowledge. Cite sources.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STYLE: concise, action-oriented. For greetings and simple questions, respond
naturally without calling any tools. Narrate each tool step briefly. On errors,
report what failed and what you will try next. Summarise on completion.
""".format(ASSISTANT_NAME=ASSISTANT_NAME)

AI_BASE_URL = os.getenv("AI_BASE_URL", "https://unorphaned-kate-suprasegmental.ngrok-free.dev/v1").rstrip("/")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODELS = [model.strip() for model in os.getenv("AI_MODELS", "").split(",") if model.strip()]
AI_MODEL = os.getenv("AI_MODEL", AI_MODELS[0] if AI_MODELS else "")
VISION_MODEL = os.getenv("AI_VISION_MODEL", AI_MODEL)
TEXT_MODEL = AI_MODEL

class _AIClient:
    """Small facade for any OpenAI-compatible model server."""

    def __init__(self):
        self.api_key = AI_API_KEY
        self.chat = self
        self.completions = self
        self._client = OpenAI(
            api_key=self.api_key or "ollama",
            base_url=AI_BASE_URL,
            default_headers={"Authorization": ""},
        )
        self.models = self._client.models

    def create(self, **kwargs):
        logger.info("Sending chat completion to %s", AI_BASE_URL)
        return self._client.chat.completions.create(**kwargs)


def _get_client() -> _AIClient:
    """Return a client for the configured alternative model server."""
    return _AIClient()

def get_client() -> _AIClient:
    """
    Public OpenAI-compatible client factory.

    Usage:
        from app.utils.groq import get_client
        client = get_client()
        resp = client.chat.completions.create(...)
    """
    return _get_client()


def list_models() -> list[dict]:
    """Return configured models, preferring the server's live model list."""
    try:
        models = get_client().models.list().data
        if models:
            return [
                {"id": model.id, "object": "model", "owned_by": "alternative"}
                for model in models
            ]
    except Exception as exc:
        logger.warning("Could not fetch models from %s: %s", AI_BASE_URL, exc)
    return [
        {"id": model, "object": "model", "owned_by": "alternative"}
        for model in AI_MODELS
    ]

# ============================================
# CONFIG — Change models here if needed
# ============================================

# ============================================
# TOOL REGISTRATION SYSTEM
# ============================================

TOOLS     = []
FUNCTIONS = {}


def _augment_system_for_tools(system: str) -> str:
    hint = (
        "When calling tools, use the tool-calling interface with valid JSON arguments. "
        "Do not write <function=...> tags, brackets, or tool calls in plain text. "
        "Return tool calls only via the tool-calling interface. "
        "You have access to NoorRobot tools; do not claim that you have no tools. "
        "When the user asks what you can do, mention that tools are available and "
        "use one when the request requires it."
    )
    if hint.lower() in system.lower():
        return system
    return system.rstrip() + "\n\n" + hint


# Names that are always pre-loaded so the model can discover and request any
# other tool on demand, without receiving the full 38-category dump upfront.
# Tools that must NEVER be sent to the model — they cause feedback loops
_BLACKLISTED_TOOLS: set[str] = {
    "tool_list",   # dumps all 200+ tool names raw — model loops on this forever
    "tool_call",   # generic wrapper that bypasses proper tool calling
}

_DISCOVERY_TOOLS: set[str] = {
    "list_tools",
    "load_tools",
    "list_skills",
    "get_skill",
    "tool_info",
}


def _select_tools(max_tools: int = 40, include_auto: bool = False, allowlist: list[str] | None = None, query: str = ""):
    """
    Return a pruned tool list to satisfy API limits.

    Strategy — "discovery-first, query-matched fill":
      1. Discovery layer  (_DISCOVERY_TOOLS) is ALWAYS included so the model
         can call load_tools / list_tools at any time and find what it needs.
      2. If an allowlist is active (caller already knows which tools are needed)
         add those on top of the discovery layer.
      3. Otherwise score every registered tool against the user query and fill
         remaining slots with the best matches.
      4. Never return an empty list — the discovery layer is the minimum.
    """
    # ── Build a deduped map of all registered tools ──────────────────────────
    by_name: dict[str, dict] = {}
    for t in TOOLS:
        name = t.get("function", {}).get("name", "")
        if not name:
            continue
        # Never expose blacklisted tools to the model
        if name in _BLACKLISTED_TOOLS:
            continue
        # Prefer the web-search variant when two tools share the name "search"
        if name == "search" and name in by_name:
            desc = str(t.get("function", {}).get("description", "")).lower()
            existing_desc = str(by_name[name].get("function", {}).get("description", "")).lower()
            if "web" in desc and "web" not in existing_desc:
                by_name[name] = t
            continue
        by_name[name] = t

    # ── Separate core vs auto_ tools ─────────────────────────────────────────
    core: list[dict] = []
    auto: list[dict] = []
    for t in by_name.values():
        n = t.get("function", {}).get("name", "")
        (auto if n.startswith("auto_") else core).append(t)
    all_tools = core + (auto if include_auto else [])

    # ── Step 1: always start with the discovery layer ────────────────────────
    discovery_tools = [
        t for t in all_tools
        if t.get("function", {}).get("name") in _DISCOVERY_TOOLS
    ]
    discovery_names = {t.get("function", {}).get("name") for t in discovery_tools}
    remaining_slots = max(0, max_tools - len(discovery_tools))

    # ── Step 2a: allowlist mode — caller knows exactly what it needs ──────────
    if allowlist is not None:
        extra = [
            t for t in all_tools
            if t.get("function", {}).get("name") in allowlist
            and t.get("function", {}).get("name") not in discovery_names
        ]
        selected = discovery_tools + extra

    # ── Step 2b: query mode — score tools and fill remaining slots ────────────
    elif query:
        terms = {term for term in query.lower().replace("_", " ").split() if len(term) > 2}
        scored: list[tuple[int, dict]] = []
        for t in all_tools:
            n = t.get("function", {}).get("name", "")
            if n in discovery_names:
                continue  # already included
            text = (n + " " + t.get("function", {}).get("description", "")).lower().replace("_", " ")
            score = sum(1 for term in terms if term in text)
            if score > 0:
                scored.append((score, t))
        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [t for _, t in scored[:remaining_slots]]
        selected = discovery_tools + matched

    # ── Step 2c: no query, no allowlist — only expose discovery layer ─────────
    else:
        selected = discovery_tools

    # ── Step 3: hard cap with discovery layer always protected ───────────────
    if len(selected) > max_tools:
        logger.warning("Tool list truncated: %d -> %d", len(selected), max_tools)
        non_discovery = [t for t in selected if t.get("function", {}).get("name") not in discovery_names]
        selected = discovery_tools + non_discovery[:max(0, max_tools - len(discovery_tools))]

    logger.info(
        "Providing %d tools to the model (discovery=%d, extra=%d)",
        len(selected), len(discovery_tools), len(selected) - len(discovery_tools),
    )
    return selected

def tool(name, description, params={}):
    """
    Decorator to register a function as a Groq tool.

    Usage:
        @tool(
            name="my_tool",
            description="Does something",
            params={"input": {"type": "string", "description": "some input"}}
        )
        def my_tool(input):
            return f"Did something with {input}"
    """
    def decorator(func):
        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            def _redact(value):
                if isinstance(value, dict):
                    red = {}
                    for k, v in value.items():
                        key = str(k).lower()
                        if any(s in key for s in ("password", "secret", "token", "api_key", "authorization", "app_password", "key")):
                            red[k] = "***REDACTED***"
                        else:
                            red[k] = _redact(v)
                    return red
                if isinstance(value, list):
                    return [_redact(v) for v in value]
                if isinstance(value, str) and len(value) > 500:
                    return value[:500] + "...(truncated)"
                return value

            safe_args = _redact(list(args))
            safe_kwargs = _redact(dict(kwargs))
            logger.debug("Tool call: %s args=%s kwargs=%s", name, safe_args, safe_kwargs)
            try:
                result = func(*args, **kwargs)
                safe_result = _redact(result)
                logger.debug("Tool result: %s -> %s", name, safe_result)
                return result
            except Exception as exc:
                logger.exception("Tool error: %s -> %s", name, exc)
                raise

        FUNCTIONS[name] = _wrapped
        def _relax_schema(p: dict):
            try:
                p = {key: value for key, value in p.items() if key != "required"}
                t = p.get("type")
                if t in ("integer", "number"):
                    return {"anyOf": [p, {"type": "string"}]}
                if t == "boolean":
                    return {"anyOf": [p, {"type": "string"}]}
            except Exception:
                pass
            return p

        # Only mark params as required when explicitly flagged.
        required = []
        relaxed_params = {}
        for k, v in params.items():
            try:
                if bool(v.get("required", False)):
                    required.append(k)
            except Exception:
                pass
            relaxed_params[k] = _relax_schema(v)

        TOOLS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": relaxed_params,
                    "required": required
                }
            }
        })
        logger.info("Registered tool: %s", name)
        return _wrapped
    return decorator


def _load_builtin_tools():
    """
    Import built-in tools after the @tool decorator is defined.
    This avoids circular import issues at startup.
    """
    try:
        from app.utils import speak  # noqa: F401
        from app import skills  # noqa: F401
        from app import tools  # noqa: F401
    except Exception as exc:
        logger.warning("Tool auto-load skipped: %s", exc)

# ============================================
# IMAGE HELPER
# ============================================

def _prepare_image(image: str) -> str:
    """
    Converts a local image file to a base64 data URL,
    or returns a remote URL as-is.
    Supports: jpg, jpeg, png, gif, webp
    """
    if image.startswith("http://") or image.startswith("https://"):
        return image
    if not os.path.exists(image):
        raise FileNotFoundError(f"❌ Image not found: {image}")
    ext = image.split(".")[-1].lower()
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "gif": "image/gif",
        "webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

# ============================================
# CORE: SIMPLE CHAT
# ============================================

def chat(prompt, system=None, history=None,
         max_tokens=1024, temperature=0.7) -> str:
    """
    Simple one-shot text completion. Returns response string.

    Args:
        prompt      : Your message
        system      : System prompt (optional)
        history     : List of previous messages (optional)
                      Format: [{"role": "user", "content": "..."}, ...]
        max_tokens  : Maximum tokens in the response
        temperature : Sampling temperature (0-1)

    Returns:
        str: AI response

    Usage:
        reply = chat("What is Python?")

        # With history
        history = []
        r1 = chat("My name is Dev", history=history)
        history += [{"role": "user", "content": "My name is Dev"},
                    {"role": "assistant", "content": r1}]
        r2 = chat("What is my name?", history=history)
    """
    messages = [{"role": "system", "content": system or DEFAULT_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    response = _get_client().chat.completions.create(
        model=TEXT_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content

# ============================================
# CORE: STREAMING CHAT  (used by RAG.py ask_stream)
# ============================================

def stream_chat(messages: list, max_tokens: int = 1024,
                temperature: float = 0.7, model: str = None):
    """
    Streaming text completion.  Yields string tokens as they arrive.
    Accepts a pre-built messages list so RAG.py can pass its full
    context-augmented prompt directly.

    Args:
        messages    : Full messages list  [{"role":..., "content":...}, ...]
        max_tokens  : Maximum tokens in the response
        temperature : Sampling temperature (0-1)
        model       : Override model (defaults to TEXT_MODEL)

    Yields:
        str: Token strings as they stream in

    Usage (sync):
        for token in stream_chat(messages):
            print(token, end="", flush=True)

    Usage inside RAG.py async generator:
        for token in stream_chat(messages):
            yield token
    """
    _model = model or TEXT_MODEL
    try:
        stream = _get_client().chat.completions.create(
            model=_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        logger.exception("stream_chat error: %s", exc)
        yield "⚠️ Streaming error — please try again."


# ============================================
# CORE: RAW COMPLETE  (used by RAG.py ask)
# ============================================

def complete(messages: list, max_tokens: int = 1024,
             temperature: float = 0.7, model: str = None) -> str:
    """
    Blocking completion that accepts a pre-built messages list.
    Used by RAGService.ask() so it benefits from key rotation.

    Args:
        messages    : Full messages list [{"role":..., "content":...}, ...]
        max_tokens  : Max tokens
        temperature : Sampling temperature
        model       : Override model (defaults to TEXT_MODEL)

    Returns:
        str: Complete AI response
    """
    _model = model or TEXT_MODEL
    try:
        resp = _get_client().chat.completions.create(
            model=_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("complete() error: %s", exc)
        return "⚠️ I hit an error reaching my language model. Please try again."

# ============================================
# VISION
# ============================================

def vision(prompt, image, system="You are a helpful vision assistant.",
           max_tokens=1024) -> str:
    """
    Send image + text prompt to Groq vision model.

    Args:
        prompt     : Question or instruction about the image
        image      : URL string OR local file path (jpg/png/gif/webp)
        system     : System prompt (optional)
        max_tokens : Max tokens

    Returns:
        str: AI response about the image

    Usage:
        reply = vision("What do you see?", "https://example.com/photo.jpg")
        reply = vision("Describe this image", "photo.jpg")
    """
    response = _get_client().chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _prepare_image(image)}}
                ]
            }
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ============================================
# AGENT  (text + tool calling)
# ============================================

def agent(
    user_input,
    system=None,
    history=None,
    model=None,
    max_tokens=1024,
    temperature: float = 0.2,
    max_steps: int = 3,
    max_return_context: int = 4000,
    *,
    include_auto_tools: bool = False,
    max_tools: int = 400,
    tool_allowlist: list[str] | None = None,
    tool_choice: str | dict | None = None,
    on_tool=None,
) -> str:
    """
    Agentic loop: keeps calling registered tools until the task is complete.

    Args:
        user_input : Command or question
        system     : System prompt (optional)
        max_tokens : Max tokens per generation step

    Returns:
        str: Final AI response after all tool calls

    Usage:
        @tool("move", "Move robot", {"direction": {"type": "string", "description": "forward/back"}})
        def move(direction):
            return f"Moved {direction}"

        reply = agent("Move the robot forward")
    """
    system = _augment_system_for_tools(system or DEFAULT_SYSTEM_PROMPT)
    client   = _get_client()   # pin one key for the whole session

    # ── Detect conversational messages that need no tools ─────────────────────
    _CONVERSATION_PATTERNS = (
        "hello", "hi ", "hi!", "hey", "howdy", "greetings",
        "how are you", "what's up", "whats up", "good morning",
        "good afternoon", "good evening", "good night",
        "thank you", "thanks", "bye", "goodbye", "see you",
    )
    _prompt_stripped = str(user_input).strip().lower()
    _is_conversational = (
        _prompt_stripped in ("hello", "hi", "hey", "thanks", "bye", "goodbye", "ok", "okay")
        or any(_prompt_stripped.startswith(p) for p in _CONVERSATION_PATTERNS)
    ) and len(_prompt_stripped) < 60

    if _is_conversational:
        # Skip agent loop entirely — plain chat is faster and cleaner
        return chat(user_input, system=system, max_tokens=max_tokens, temperature=temperature)
    messages = [
        {"role": "system", "content": system},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    prompt_lower = str(user_input).lower()
    capability_query = any(
        phrase in prompt_lower
        for phrase in ("which tools", "what tools", "list tools", "tools can you see", "tools do you have")
    )
    if capability_query:
        messages = [messages[0], messages[-1]]
        if "list_tools" in FUNCTIONS:
            tool_choice = {"type": "function", "function": {"name": "list_tools"}}
            tool_allowlist = ["list_tools"]
    if tool_choice is None and "time_now" in FUNCTIONS and any(
        phrase in prompt_lower
        for phrase in ("what time", "current time", "right now")
    ):
        tool_choice = {"type": "function", "function": {"name": "time_now"}}
        tool_allowlist = ["time_now"]

    # Convert Python None/Falsey values into valid API values.
    # Groq/OpenAI tool_choice accepts string values: none, auto, required
    # or a dict specifying a forced function.
    if isinstance(tool_choice, dict):
        pass
    else:
        tool_choice = str(tool_choice).lower().strip() if tool_choice is not None else ""
        if not tool_choice:
            tool_choice = "auto" if include_auto_tools or TOOLS else "none"
        if tool_choice not in ("none", "auto", "required"):
            logger.warning("groq.agent: normalized invalid tool_choice to auto (original=%s)", tool_choice)
            tool_choice = "auto"

    forced_tool = isinstance(tool_choice, dict) and bool(tool_choice.get("function", {}).get("name"))
    logger.info(
        "groq.agent: final tool_choice=%s include_auto_tools=%s max_tools=%s allowlist=%s max_steps=%s max_return_context=%s",
        tool_choice, include_auto_tools, max_tools, tool_allowlist, max_steps, max_return_context,
    )

    tool_steps = 0
    loaded_tools: set[str] = set()
    tools_enabled = True
    last_tool_output = None
    while True:
        active_allowlist = None
        if tool_allowlist or loaded_tools:
            active_allowlist = sorted(set(tool_allowlist or []) | loaded_tools | {"list_tools", "load_tools", "tool_info", "tool_call"})
        tools_payload = _select_tools(
            max_tools=max_tools,
            include_auto=include_auto_tools,
            allowlist=active_allowlist,
            query=user_input if active_allowlist is None else "",
        ) if (TOOLS and tools_enabled and tool_choice != "none") else None
        logger.info("groq.agent: calling API with tool_choice=%s tools=%s", tool_choice, tools_payload)
        response = client.chat.completions.create(
            model=model or TEXT_MODEL,
            messages=messages,
            tools=tools_payload,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for call in msg.tool_calls:
            args   = json.loads(call.function.arguments) if call.function.arguments else {}
            func   = FUNCTIONS.get(call.function.name)
            if not func or args is None:
                output = f"Tool '{call.function.name}' not found or invalid args!"
            else:
                try:
                    output = func(**args)
                except Exception as exc:
                    output = f"Tool '{call.function.name}' failed: {exc}"
                    logger.exception("Tool execution failed: %s", call.function.name)
            if call.function.name == "load_tools" and isinstance(output, dict):
                loaded_tools.update(str(name) for name in output.get("tools", []))
            # list_tools also reveals tool names — add them to loaded set
            # so the model can call them in the next step
            if call.function.name == "list_tools" and isinstance(output, list):
                loaded_tools.update(str(n) for n in output)
            last_tool_output = output
            if on_tool:
                on_tool(call.function.name, args, output)
            logger.info("[Tool] 🔧 %s(%s) → %s", call.function.name, args, output)
            content = str(output)
            if max_return_context and len(content) > max_return_context:
                content = content[:max_return_context] + "\n...[truncated]"
            messages.append({
                "role":         "tool",
                "tool_call_id": call.id,
                "name":         call.function.name,
                "content":      content,
            })
        tool_steps += 1
        if forced_tool and tool_steps >= 1:
            tool_choice = "none"
            tools_enabled = False
        # Track failures in this step
        failed_in_this_call: set[str] = set()
        succeeded_in_this_call: set[str] = set()
        for call in (msg.tool_calls or []):
            content_str = ""
            for m in messages:
                if isinstance(m, dict) and m.get("role") == "tool" and m.get("tool_call_id") == call.id:
                    content_str = m.get("content", "")
                    break
            if content_str.startswith("Tool '") and "failed" in content_str:
                failed_in_this_call.add(call.function.name)
            else:
                succeeded_in_this_call.add(call.function.name)

        # If all tools succeeded and task looks complete, stop immediately
        # Only for action tools (play, send, delete...) not query tools that need follow-up
        _ACTION_TOOLS = {
            "ringtone_play", "ringtone_stop", "ringtone_schedule",
            "gmail_send", "gmail_delete", "gmail_mark_read", "gmail_mark_unread", "gmail_move",
            "note_add", "note_delete", "note_update",
            "todo_add", "todo_done", "todo_delete",
            "calendar_create_event", "calendar_delete_event",
            "capture_screen", "auto_click", "auto_type", "auto_hotkey",
            "forward", "backward", "left", "right", "stop",
            "check_eyes", "clear_eyes", "esp32_eyes", "esp32_move",
            "write_file", "edit_file", "delete_path", "move_file", "copy_path",
            "execute_code", "execute_file", "cmd_run_once",
        }
        is_action = bool(succeeded_in_this_call & _ACTION_TOOLS)
        if is_action and not failed_in_this_call and tool_steps >= 1:
            messages.append({"role": "user", "content": (
                "Task complete. Give the user a single short sentence confirming what was done. "
                "Do not call any more tools."
            )})
            summary_resp = client.chat.completions.create(
                model=model or TEXT_MODEL,
                messages=messages,
                max_tokens=256,
                temperature=temperature,
            )
            return summary_resp.choices[0].message.content or ""

        # If tools failed, cut short after 2 attempts
        if failed_in_this_call and tool_steps >= 2:
            messages.append({"role": "user", "content": (
                "The tool(s) " + ", ".join(failed_in_this_call) + " failed. "
                "Stop trying to call them again. "
                "Summarise what happened clearly and concisely for the user."
            )})
            summary_resp = client.chat.completions.create(
                model=model or TEXT_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return summary_resp.choices[0].message.content or ""
        if tool_steps >= max_steps:
            messages.append({"role": "user", "content": (
                "You have completed " + str(tool_steps) + " tool steps. "
                "Stop calling tools now and give the user a clear, concise summary of what you found or did. "
                "Do not mention tool names or errors unless relevant to the user."
            )})
            summary_resp = client.chat.completions.create(
                model=model or TEXT_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return summary_resp.choices[0].message.content or str(last_tool_output)

# ============================================
# VISION AGENT  (image + tool calling)
# ============================================

def vision_agent(
    prompt,
    image,
    system=None,
    max_tokens=1024,
    max_return_context: int = 4000,
    *,
    include_auto_tools: bool = False,
    max_tools: int = 50,
    tool_allowlist: list[str] | None = None,
) -> str:
    """
    Vision + tool calling combined.
    AI sees the image AND can call tools based on what it sees.

    Args:
        prompt     : Instruction for the AI
        image      : URL string OR local file path
        system     : System prompt (optional)
        max_tokens : Max tokens per generation step

    Returns:
        str: Final AI response after all tool calls

    Usage:
        reply = vision_agent("What obstacle is ahead? Move accordingly.", "camera.jpg")
    """
    system = _augment_system_for_tools(system or DEFAULT_SYSTEM_PROMPT)
    client   = _get_client()
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "text",      "text": prompt},
                {"type": "image_url", "image_url": {"url": _prepare_image(image)}}
            ]
        }
    ]

    while True:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            tools=_select_tools(max_tools=max_tools, include_auto=include_auto_tools, allowlist=tool_allowlist) if TOOLS else None,
            max_tokens=max_tokens,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for call in msg.tool_calls:
            args   = json.loads(call.function.arguments) if call.function.arguments else {}
            func   = FUNCTIONS.get(call.function.name)
            output = func(**args) if func and args is not None else f"Tool '{call.function.name}' not found or invalid args!"
            logger.info("[Tool] 🔧 %s(%s) → %s", call.function.name, args, output)
            content = str(output)
            if max_return_context and len(content) > max_return_context:
                content = content[:max_return_context] + "\n...[truncated]"
            messages.append({
                "role":         "tool",
                "tool_call_id": call.id,
                "name":         call.function.name,
                "content":      content,
            })


# ------------------------------------------------------------
# Auto-load built-in tool modules (skills/tools/speak) safely
# ------------------------------------------------------------
_load_builtin_tools()


# ============================================
# QUICK TEST — run this file directly to test
# ============================================
"""
if __name__ == "__main__":
    print("\n--- Testing chat() ---")
    print(chat("Say hello in one sentence"))

    print("\n--- Testing stream_chat() ---")
    msgs = [{"role":"system","content":"You are helpful."},
            {"role":"user","content":"Count to 5."}]
    for tok in stream_chat(msgs):
        print(tok, end="", flush=True)
    print()

    print("\n--- Testing vision() ---")
    print(vision(
        "What city is this?",
        "https://upload.wikimedia.org/wikipedia/commons/d/da/SF_From_Marin_Highlands3.jpg"
    ))

    print("\n--- Testing agent() with a tool ---")
    @tool("get_time", "Get current time", {})
    def get_time():
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    print(agent("What time is it right now?"))
    print("\n✅ All tests passed!")
"""
