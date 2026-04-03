from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.capture.capture")
logger.debug("Loaded tool module: capture.capture")

from pathlib import Path
from datetime import datetime
from app.utils.groq import tool

try:
    from PIL import ImageGrab  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    ImageGrab = None


def _default_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path.cwd() / f"screenshot_{stamp}.png"


@tool(
    name="capture_screen",
    description="Capture a screenshot of the screen and save to a file.",
    params={
        "path": {"type": "string", "description": "Output file path (optional)"},
        "region": {"type": "array", "description": "Region [left, top, right, bottom] (optional)"},
        "all_screens": {"type": "boolean", "description": "Capture all monitors (optional)"},
        "format": {"type": "string", "description": "Image format (default PNG)"},
    },
)
def capture_screen(path: str = "", region: list[int] | None = None, all_screens: bool = False, format: str = "PNG") -> str:
    if ImageGrab is None:
        raise RuntimeError("Pillow (PIL) is not installed. Install it to enable screenshots.")

    out_path = Path(path).expanduser() if path else _default_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bbox = None
    if region and len(region) == 4:
        bbox = tuple(int(x) for x in region)
    image = ImageGrab.grab(bbox=bbox, all_screens=bool(all_screens))
    image.save(out_path, format=(format or "PNG").upper())
    return f"Saved screenshot to {out_path.resolve()}"


@tool(
    name="capture_region",
    description="Capture a specific screen region.",
    params={
        "left": {"type": "integer"},
        "top": {"type": "integer"},
        "right": {"type": "integer"},
        "bottom": {"type": "integer"},
        "path": {"type": "string", "description": "Output file path (optional)"},
        "format": {"type": "string", "description": "Image format (default PNG)"},
    },
)
def capture_region(left: int, top: int, right: int, bottom: int, path: str = "", format: str = "PNG"):
    return capture_screen(path=path, region=[left, top, right, bottom], all_screens=False, format=format)


@tool(
    name="capture_all_screens",
    description="Capture all monitors into a single image.",
    params={
        "path": {"type": "string", "description": "Output file path (optional)"},
        "format": {"type": "string", "description": "Image format (default PNG)"},
    },
)
def capture_all_screens(path: str = "", format: str = "PNG"):
    return capture_screen(path=path, region=None, all_screens=True, format=format)
