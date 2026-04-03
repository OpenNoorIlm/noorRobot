from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.automation.automation")
logger.debug("Loaded tool module: automation.automation")

from datetime import datetime
from pathlib import Path
from app.utils.groq import tool

try:
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None


def _require():
    if pyautogui is None:
        raise RuntimeError("pyautogui is not installed.")


def _screenshot_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path.cwd() / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"automation_{stamp}.png"


def _maybe_screenshot(return_screenshot: bool):
    if not return_screenshot:
        return None
    path = _screenshot_path()
    pyautogui.screenshot(str(path))
    return str(path.resolve())


@tool(
    name="auto_call",
    description="Call any pyautogui function by name with args/kwargs.",
    params={
        "func": {"type": "string", "description": "pyautogui function name"},
        "args": {"type": "array", "description": "Positional args list (optional)"},
        "kwargs": {"type": "object", "description": "Keyword args dict (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_call(
    func: str,
    args: list | None = None,
    kwargs: dict | None = None,
    return_screenshot: bool = False,
):
    _require()
    if not hasattr(pyautogui, func):
        raise AttributeError(f"pyautogui has no function '{func}'")
    fn = getattr(pyautogui, func)
    result = fn(*(args or []), **(kwargs or {}))
    return {"result": result, "screenshot": _maybe_screenshot(return_screenshot)}


def _register_dynamic_wrappers():
    if pyautogui is None:
        return
    existing = set(globals().keys())
    for name in dir(pyautogui):
        if name.startswith("_"):
            continue
        if name in existing:
            continue
        fn = getattr(pyautogui, name)
        if not callable(fn):
            continue

        def _make_wrapper(func_name: str):
            @tool(
                name=f"auto_{func_name}",
                description=f"Wrapper for pyautogui.{func_name} (args/kwargs).",
                params={
                    "args": {"type": "array", "description": "Positional args list (optional)"},
                    "kwargs": {"type": "object", "description": "Keyword args dict (optional)"},
                    "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
                },
            )
            def _wrapper(
                args: list | None = None,
                kwargs: dict | None = None,
                return_screenshot: bool = False,
            ):
                _require()
                target = getattr(pyautogui, func_name)
                result = target(*(args or []), **(kwargs or {}))
                return {"result": result, "screenshot": _maybe_screenshot(return_screenshot)}

            return _wrapper

        globals()[f"auto_{name}"] = _make_wrapper(name)


_register_dynamic_wrappers()


@tool(
    name="auto_move_to",
    description="Move mouse to absolute coordinates.",
    params={
        "x": {"type": "integer", "description": "X coordinate"},
        "y": {"type": "integer", "description": "Y coordinate"},
        "duration": {"type": "number", "description": "Move duration in seconds (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_move_to(x: int, y: int, duration: float = 0.0, return_screenshot: bool = False):
    _require()
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_move_rel",
    description="Move mouse relative to current position.",
    params={
        "x": {"type": "integer", "description": "Delta X"},
        "y": {"type": "integer", "description": "Delta Y"},
        "duration": {"type": "number", "description": "Move duration in seconds (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_move_rel(x: int, y: int, duration: float = 0.0, return_screenshot: bool = False):
    _require()
    pyautogui.moveRel(int(x), int(y), duration=float(duration))
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_click",
    description="Click mouse at current position or coordinates.",
    params={
        "x": {"type": "integer", "description": "X coordinate (optional)"},
        "y": {"type": "integer", "description": "Y coordinate (optional)"},
        "clicks": {"type": "integer", "description": "Number of clicks (default 1)"},
        "interval": {"type": "number", "description": "Interval between clicks (optional)"},
        "button": {"type": "string", "description": "Button: left|right|middle (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_click(
    x: int | None = None,
    y: int | None = None,
    clicks: int = 1,
    interval: float = 0.0,
    button: str = "left",
    return_screenshot: bool = False,
):
    _require()
    pyautogui.click(x=x, y=y, clicks=int(clicks), interval=float(interval), button=button)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_double_click",
    description="Double click mouse.",
    params={
        "x": {"type": "integer", "description": "X coordinate (optional)"},
        "y": {"type": "integer", "description": "Y coordinate (optional)"},
        "interval": {"type": "number", "description": "Interval between clicks (optional)"},
        "button": {"type": "string", "description": "Button: left|right|middle (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_double_click(
    x: int | None = None,
    y: int | None = None,
    interval: float = 0.0,
    button: str = "left",
    return_screenshot: bool = False,
):
    _require()
    pyautogui.doubleClick(x=x, y=y, interval=float(interval), button=button)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_right_click",
    description="Right click mouse.",
    params={
        "x": {"type": "integer", "description": "X coordinate (optional)"},
        "y": {"type": "integer", "description": "Y coordinate (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_right_click(x: int | None = None, y: int | None = None, return_screenshot: bool = False):
    _require()
    pyautogui.rightClick(x=x, y=y)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_drag_to",
    description="Drag mouse to absolute coordinates.",
    params={
        "x": {"type": "integer", "description": "X coordinate"},
        "y": {"type": "integer", "description": "Y coordinate"},
        "duration": {"type": "number", "description": "Drag duration in seconds (optional)"},
        "button": {"type": "string", "description": "Button: left|right|middle (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_drag_to(
    x: int,
    y: int,
    duration: float = 0.0,
    button: str = "left",
    return_screenshot: bool = False,
):
    _require()
    pyautogui.dragTo(int(x), int(y), duration=float(duration), button=button)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_drag_rel",
    description="Drag mouse relative to current position.",
    params={
        "x": {"type": "integer", "description": "Delta X"},
        "y": {"type": "integer", "description": "Delta Y"},
        "duration": {"type": "number", "description": "Drag duration in seconds (optional)"},
        "button": {"type": "string", "description": "Button: left|right|middle (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_drag_rel(
    x: int,
    y: int,
    duration: float = 0.0,
    button: str = "left",
    return_screenshot: bool = False,
):
    _require()
    pyautogui.dragRel(int(x), int(y), duration=float(duration), button=button)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_scroll",
    description="Scroll the mouse wheel.",
    params={
        "clicks": {"type": "integer", "description": "Scroll amount (positive up, negative down)"},
        "x": {"type": "integer", "description": "X coordinate (optional)"},
        "y": {"type": "integer", "description": "Y coordinate (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_scroll(clicks: int, x: int | None = None, y: int | None = None, return_screenshot: bool = False):
    _require()
    pyautogui.scroll(int(clicks), x=x, y=y)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_type",
    description="Type text with optional interval.",
    params={
        "text": {"type": "string", "description": "Text to type"},
        "interval": {"type": "number", "description": "Delay between keystrokes (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_type(text: str, interval: float = 0.0, return_screenshot: bool = False):
    _require()
    pyautogui.typewrite(text, interval=float(interval))
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_press",
    description="Press a single key.",
    params={
        "key": {"type": "string", "description": "Key to press"},
        "presses": {"type": "integer", "description": "Number of presses (optional)"},
        "interval": {"type": "number", "description": "Interval between presses (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_press(key: str, presses: int = 1, interval: float = 0.0, return_screenshot: bool = False):
    _require()
    pyautogui.press(key, presses=int(presses), interval=float(interval))
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_hotkey",
    description="Press a combination of keys.",
    params={
        "keys": {"type": "array", "description": "List of keys to press in order"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_hotkey(keys: list[str], return_screenshot: bool = False):
    _require()
    pyautogui.hotkey(*keys)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_key_down",
    description="Hold down a key.",
    params={
        "key": {"type": "string", "description": "Key to hold"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_key_down(key: str, return_screenshot: bool = False):
    _require()
    pyautogui.keyDown(key)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_key_up",
    description="Release a held key.",
    params={
        "key": {"type": "string", "description": "Key to release"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_key_up(key: str, return_screenshot: bool = False):
    _require()
    pyautogui.keyUp(key)
    return {"ok": True, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_position",
    description="Get current mouse position.",
    params={
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_position(return_screenshot: bool = False):
    _require()
    pos = pyautogui.position()
    return {"x": pos.x, "y": pos.y, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_screen_size",
    description="Get screen size.",
    params={
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_screen_size(return_screenshot: bool = False):
    _require()
    size = pyautogui.size()
    return {"width": size.width, "height": size.height, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_screenshot",
    description="Capture a screenshot.",
    params={
        "path": {"type": "string", "description": "Output path (optional)"},
        "region": {"type": "array", "description": "Region [left, top, width, height] (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_screenshot(path: str = "", region: list[int] | None = None, return_screenshot: bool = False):
    _require()
    out_path = Path(path).expanduser() if path else _screenshot_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {}
    if region and len(region) == 4:
        kwargs["region"] = tuple(int(x) for x in region)
    pyautogui.screenshot(str(out_path), **kwargs)
    return {"ok": True, "screenshot": str(out_path.resolve()) if return_screenshot else None}


@tool(
    name="auto_locate_on_screen",
    description="Locate an image on the screen.",
    params={
        "image_path": {"type": "string", "description": "Image file path"},
        "confidence": {"type": "number", "description": "Confidence (optional, requires OpenCV)"},
        "grayscale": {"type": "boolean", "description": "Use grayscale (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_locate_on_screen(image_path: str, confidence: float | None = None, grayscale: bool = False, return_screenshot: bool = False):
    _require()
    kwargs = {"grayscale": grayscale}
    if confidence is not None:
        kwargs["confidence"] = float(confidence)
    box = pyautogui.locateOnScreen(image_path, **kwargs)
    if box is None:
        return {"found": False, "screenshot": _maybe_screenshot(return_screenshot)}
    return {"found": True, "box": [box.left, box.top, box.width, box.height], "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_locate_all_on_screen",
    description="Locate all instances of an image on the screen.",
    params={
        "image_path": {"type": "string", "description": "Image file path"},
        "confidence": {"type": "number", "description": "Confidence (optional, requires OpenCV)"},
        "grayscale": {"type": "boolean", "description": "Use grayscale (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_locate_all_on_screen(image_path: str, confidence: float | None = None, grayscale: bool = False, return_screenshot: bool = False):
    _require()
    kwargs = {"grayscale": grayscale}
    if confidence is not None:
        kwargs["confidence"] = float(confidence)
    boxes = list(pyautogui.locateAllOnScreen(image_path, **kwargs))
    out = [{"left": b.left, "top": b.top, "width": b.width, "height": b.height} for b in boxes]
    return {"boxes": out, "screenshot": _maybe_screenshot(return_screenshot)}


@tool(
    name="auto_center",
    description="Return the center of a box.",
    params={"box": {"type": "array", "description": "Box [left, top, width, height]"}},
)
def auto_center(box: list[int]):
    _require()
    if len(box) != 4:
        raise ValueError("box must be [left, top, width, height]")
    point = pyautogui.center(tuple(box))
    return {"x": point.x, "y": point.y}


@tool(
    name="auto_alert",
    description="Show a GUI alert dialog.",
    params={
        "text": {"type": "string"},
        "title": {"type": "string"},
        "button": {"type": "string"},
    },
)
def auto_alert(text: str, title: str = "Alert", button: str = "OK"):
    _require()
    return pyautogui.alert(text=text, title=title, button=button)


@tool(
    name="auto_confirm",
    description="Show a GUI confirm dialog.",
    params={
        "text": {"type": "string"},
        "title": {"type": "string"},
        "buttons": {"type": "array"},
    },
)
def auto_confirm(text: str, title: str = "Confirm", buttons: list[str] | None = None):
    _require()
    return pyautogui.confirm(text=text, title=title, buttons=buttons or ["OK", "Cancel"])


@tool(
    name="auto_prompt",
    description="Show a GUI prompt dialog.",
    params={
        "text": {"type": "string"},
        "title": {"type": "string"},
        "default": {"type": "string"},
    },
)
def auto_prompt(text: str, title: str = "Prompt", default: str = ""):
    _require()
    return pyautogui.prompt(text=text, title=title, default=default)


@tool(
    name="auto_set_pause",
    description="Set global pause between pyautogui actions.",
    params={"seconds": {"type": "number"}},
)
def auto_set_pause(seconds: float):
    _require()
    pyautogui.PAUSE = float(seconds)
    return {"ok": True}


@tool(
    name="auto_set_failsafe",
    description="Enable or disable pyautogui fail-safe.",
    params={"enabled": {"type": "boolean"}},
)
def auto_set_failsafe(enabled: bool = True):
    _require()
    pyautogui.FAILSAFE = bool(enabled)
    return {"ok": True}


@tool(
    name="auto_wait_for_image",
    description="Wait for an image to appear on screen.",
    params={
        "image_path": {"type": "string"},
        "timeout": {"type": "number", "description": "Timeout seconds (default 10)"},
        "confidence": {"type": "number", "description": "Confidence (optional, requires OpenCV)"},
        "grayscale": {"type": "boolean", "description": "Use grayscale (optional)"},
        "return_screenshot": {"type": "boolean", "description": "Return screenshot path (optional)"},
    },
)
def auto_wait_for_image(image_path: str, timeout: float = 10.0, confidence: float | None = None, grayscale: bool = False, return_screenshot: bool = False):
    _require()
    end = datetime.now().timestamp() + float(timeout)
    while datetime.now().timestamp() <= end:
        result = auto_locate_on_screen(image_path, confidence=confidence, grayscale=grayscale, return_screenshot=False)
        if result.get("found"):
            result["screenshot"] = _maybe_screenshot(return_screenshot)
            return result
    return {"found": False, "screenshot": _maybe_screenshot(return_screenshot)}
