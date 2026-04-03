from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.image_tools.image_tools")
logger.debug("Loaded tool module: image_tools.image_tools")

from pathlib import Path
from app.utils.groq import tool

try:
    from PIL import Image  # type: ignore
    from PIL import ImageDraw, ImageFont  # type: ignore
except Exception:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    import pytesseract  # type: ignore
except Exception:
    pytesseract = None


def _require():
    if Image is None:
        raise RuntimeError("Pillow not installed")


@tool(
    name="image_resize",
    description="Resize an image.",
    params={
        "path": {"type": "string"},
        "width": {"type": "integer"},
        "height": {"type": "integer"},
        "out": {"type": "string"},
        "keep_aspect": {"type": "boolean"},
    },
)
def image_resize(path: str, width: int, height: int, out: str, keep_aspect: bool = False):
    _require()
    img = Image.open(path)
    if keep_aspect:
        img.thumbnail((int(width), int(height)))
    else:
        img = img.resize((int(width), int(height)))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    img.save(outp)
    return str(outp.resolve())


@tool(
    name="image_convert",
    description="Convert image format.",
    params={"path": {"type": "string"}, "out": {"type": "string"}},
)
def image_convert(path: str, out: str):
    _require()
    img = Image.open(path)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    img.save(outp)
    return str(outp.resolve())


@tool(
    name="image_crop",
    description="Crop an image.",
    params={
        "path": {"type": "string"},
        "box": {"type": "array"},
        "out": {"type": "string"},
    },
)
def image_crop(path: str, box: list[int], out: str):
    _require()
    img = Image.open(path)
    crop = img.crop(tuple(box))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    crop.save(outp)
    return str(outp.resolve())


@tool(
    name="image_ocr",
    description="OCR an image to text.",
    params={
        "path": {"type": "string"},
        "lang": {"type": "string", "description": "OCR language (optional)"},
    },
)
def image_ocr(path: str, lang: str = ""):
    _require()
    if pytesseract is None:
        raise RuntimeError("pytesseract not installed")
    img = Image.open(path)
    return pytesseract.image_to_string(img, lang=lang) if lang else pytesseract.image_to_string(img)


@tool(
    name="image_rotate",
    description="Rotate an image.",
    params={
        "path": {"type": "string"},
        "degrees": {"type": "number"},
        "out": {"type": "string"},
        "expand": {"type": "boolean"},
    },
)
def image_rotate(path: str, degrees: float, out: str, expand: bool = True):
    _require()
    img = Image.open(path)
    rot = img.rotate(float(degrees), expand=expand)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    rot.save(outp)
    return str(outp.resolve())


@tool(
    name="image_flip",
    description="Flip an image horizontally or vertically.",
    params={
        "path": {"type": "string"},
        "mode": {"type": "string", "description": "horizontal|vertical"},
        "out": {"type": "string"},
    },
)
def image_flip(path: str, mode: str, out: str):
    _require()
    img = Image.open(path)
    if mode == "vertical":
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    else:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    img.save(outp)
    return str(outp.resolve())


@tool(
    name="image_grayscale",
    description="Convert image to grayscale.",
    params={"path": {"type": "string"}, "out": {"type": "string"}},
)
def image_grayscale(path: str, out: str):
    _require()
    img = Image.open(path).convert("L")
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    img.save(outp)
    return str(outp.resolve())


@tool(
    name="image_watermark_text",
    description="Add a text watermark to an image.",
    params={
        "path": {"type": "string"},
        "text": {"type": "string"},
        "out": {"type": "string"},
        "position": {"type": "string", "description": "e.g. bottom-right (optional)"},
        "opacity": {"type": "number", "description": "0-1 opacity (optional)"},
        "font_size": {"type": "integer", "description": "Font size (optional)"},
    },
)
def image_watermark_text(path: str, text: str, out: str, position: str = "bottom-right", opacity: float = 0.3, font_size: int = 24):
    _require()
    if ImageDraw is None:
        raise RuntimeError("Pillow not installed")
    img = Image.open(path).convert("RGBA")
    txt = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt)
    try:
        font = ImageFont.truetype("arial.ttf", int(font_size))
    except Exception:
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(text, font=font)
    margin = 10
    if position == "top-left":
        x, y = margin, margin
    elif position == "top-right":
        x, y = img.size[0] - text_w - margin, margin
    elif position == "bottom-left":
        x, y = margin, img.size[1] - text_h - margin
    else:
        x, y = img.size[0] - text_w - margin, img.size[1] - text_h - margin
    draw.text((x, y), text, fill=(255, 255, 255, int(255 * float(opacity))), font=font)
    out_img = Image.alpha_composite(img, txt).convert("RGB")
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(outp)
    return str(outp.resolve())
