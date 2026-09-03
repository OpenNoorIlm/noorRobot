"""Privacy-preserving face-image fingerprints."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

_STORE_PATH = Path(__file__).resolve().parents[1] / "database" / "memory" / "face_memory.json"
_LOCK = threading.Lock()


def _image_bytes(image: str | bytes) -> bytes:
    if isinstance(image, bytes):
        return image
    if image.startswith("data:"):
        _, encoded = image.split(",", 1)
        return base64.b64decode(encoded)
    if image.startswith(("http://", "https://")):
        raise ValueError("Remote image URLs are not accepted by private face memory")
    return Path(image).read_bytes()


def _fingerprints(image: str | bytes) -> tuple[str, str]:
    raw = _image_bytes(image)
    digest = hashlib.sha256(raw).hexdigest()
    with Image.open(io.BytesIO(raw)) as source:
        pixels = list(source.convert("L").resize((9, 8)).getdata())
    bits = "".join(
        "1" if pixels[row * 9 + col] > pixels[row * 9 + col + 1] else "0"
        for row in range(8) for col in range(8)
    )
    return digest, f"{int(bits, 2):016x}"


def _read() -> list[dict[str, Any]]:
    if not _STORE_PATH.exists():
        return []
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write(records: list[dict[str, Any]]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = _STORE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, _STORE_PATH)
    try:
        _STORE_PATH.chmod(0o600)
    except OSError:
        pass


def save_face(label: str, image: str | bytes) -> dict[str, Any]:
    """Save only a hashed face fingerprint under a label."""
    if not label or not label.strip():
        raise ValueError("label is required")
    digest, perceptual = _fingerprints(image)
    record = {"label": label.strip(), "sha256": digest, "perceptual_hash": perceptual,
              "created_at": datetime.now(timezone.utc).isoformat()}
    with _LOCK:
        records = [item for item in _read() if item.get("label") != record["label"]]
        records.append(record)
        _write(records)
    return {"label": record["label"], "saved": True, "sha256": digest}


def recognize_face(image: str | bytes, max_distance: int = 12) -> dict[str, Any]:
    """Match an image against stored fingerprints without exposing image data."""
    _, perceptual = _fingerprints(image)
    target = int(perceptual, 16)
    with _LOCK:
        records = _read()
    matches = []
    for record in records:
        distance = (target ^ int(record["perceptual_hash"], 16)).bit_count()
        if distance <= max_distance:
            matches.append({"label": record["label"], "distance": distance})
    matches.sort(key=lambda item: item["distance"])
    return {"recognized": bool(matches), "matches": matches}


def list_faces() -> list[dict[str, str]]:
    """List labels and timestamps, never image data."""
    with _LOCK:
        return [{"label": item["label"], "created_at": item["created_at"]} for item in _read()]