"""
groq.py  —  NoorRobot Groq Client & LLM Utilities
===================================================
Provides:
  - Multi-key rotation (GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 from app/utils/.env)
  - @tool decorator for registering function-calling tools
  - chat()         — simple one-shot text completion
  - stream_chat()  — streaming text completion (used by RAG.py)
  - vision()       — image + text completion
  - agent()        — agentic loop with tool calling
  - vision_agent() — vision + tool calling combined
  - get_client()   — public key-rotating Groq client (used by RAGService)

RAG.py integration:
    from app.utils.groq import get_client, GROQ_MODEL, TEXT_MODEL, VISION_MODEL
"""

import os
import json
import base64
import random
import logging
import functools
from groq import Groq
from dotenv import load_dotenv
# NOTE: Do not import app.skills/tools/speak here to avoid circular imports.

logger = logging.getLogger("NoorRobot.Groq")

# ============================================
# LOAD API KEYS FROM .env
# ============================================

_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_PATH)

ASSISTANT_NAME     = os.getenv("ASSISTANT_NAME",     "Noor")
JARVIS_USER_TITLE  = os.getenv("JARVIS_USER_TITLE",  "User")

def _load_api_keys():
    """Finds GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 from app/utils/.env"""
    keys = []
    base = os.environ.get("GROQ_API_KEY")
    if base:
        keys.append(base)
    for i in range(2, 10):
        key = os.environ.get(f"GROQ_API_KEY_{i}")
        if key:
            keys.append(key)
    if not keys:
        raise ValueError("❌ No GROQ_API_KEY found in app/utils/.env! Add at least GROQ_API_KEY=your_key")
    return keys

API_KEYS = _load_api_keys()
logger.info("Loaded %d API key(s)", len(API_KEYS))

def _get_client() -> Groq:
    """Returns a Groq client with a randomly chosen API key (internal)."""
    return Groq(api_key=random.choice(API_KEYS))

def get_client() -> Groq:
    """
    Public key-rotating Groq client factory.
    Imported by RAGService so it benefits from multi-key rotation
    instead of using a single key.

    Usage:
        from app.utils.groq import get_client
        client = get_client()
        resp = client.chat.completions.create(...)
    """
    return _get_client()

# ============================================
# CONFIG — Change models here if needed
# ============================================

TEXT_MODEL   = os.getenv("GROQ_MODEL",        "llama-3.3-70b-versatile")
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

# Alias used by RAG.py (reads GROQ_MODEL env var; falls back to TEXT_MODEL)
GROQ_MODEL = TEXT_MODEL

# ============================================
# TOOL REGISTRATION SYSTEM
# ============================================

TOOLS     = []
FUNCTIONS = {}


def _augment_system_for_tools(system: str) -> str:
    hint = (
        "When calling tools, use the tool-calling interface with valid JSON arguments. "
        "Do not write <function=...> tags, brackets, or tool calls in plain text. "
        "Return tool calls only via the tool-calling interface."
    )
    if hint.lower() in system.lower():
        return system
    return system.rstrip() + "\n\n" + hint


def _select_tools(max_tools: int = 50, include_auto: bool = False, allowlist: list[str] | None = None):
    """
    Return a pruned tool list to satisfy API limits.
    Prioritize non-auto_ tools, then auto_ tools if space remains.
    """
    # Dedupe by name (last one wins), but prefer web-search tool when name == "search"
    by_name = {}
    for t in TOOLS:
        name = t.get("function", {}).get("name", "")
        if not name:
            continue
        if allowlist is not None and name not in allowlist:
            continue
        if name == "search" and name in by_name:
            desc = str(t.get("function", {}).get("description", "")).lower()
            existing_desc = str(by_name[name].get("function", {}).get("description", "")).lower()
            if "web" in desc and "web" not in existing_desc:
                by_name[name] = t
            continue
        by_name[name] = t

    core = []
    auto = []
    for t in by_name.values():
        name = t.get("function", {}).get("name", "")
        if name.startswith("auto_"):
            auto.append(t)
        else:
            core.append(t)
    selected = core + (auto if include_auto else [])
    if len(selected) > max_tools:
        logger.warning("Tool list truncated: %d -> %d", len(selected), max_tools)
        selected = selected[:max_tools]
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

def chat(prompt, system=f"You are {ASSISTANT_NAME}, a helpful assistant.", history=None,
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
    messages = [{"role": "system", "content": system}]
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
    system=f"You are {ASSISTANT_NAME}, an AI assistant. Use tools to complete tasks.",
    max_tokens=1024,
    temperature: float = 0.2,
    max_steps: int = 6,
    max_return_context: int = 4000,
    *,
    include_auto_tools: bool = False,
    max_tools: int = 50,
    tool_allowlist: list[str] | None = None,
    tool_choice: str | dict | None = None,
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
    system = _augment_system_for_tools(system)
    client   = _get_client()   # pin one key for the whole session
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user_input},
    ]

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
    tools_enabled = True
    last_tool_output = None
    while True:
        tools_payload = _select_tools(max_tools=max_tools, include_auto=include_auto_tools, allowlist=tool_allowlist) if (TOOLS and tools_enabled and tool_choice != "none") else None
        logger.info("groq.agent: calling API with tool_choice=%s tools=%s", tool_choice, tools_payload)
        response = client.chat.completions.create(
            model=TEXT_MODEL,
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
            output = func(**args) if func and args is not None else f"Tool '{call.function.name}' not found or invalid args!"
            last_tool_output = output
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
        if tool_steps >= max_steps:
            return str(last_tool_output) if last_tool_output is not None else "⚠️ Tool loop limit reached."

# ============================================
# VISION AGENT  (image + tool calling)
# ============================================

def vision_agent(
    prompt,
    image,
    system="You are a vision AI. Analyze the image and use tools if needed.",
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
    system = _augment_system_for_tools(system)
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
