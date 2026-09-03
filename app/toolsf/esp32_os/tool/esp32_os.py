"""Client tools for the ESP32-OS HTTP API."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import requests

from app.utils.groq import tool

_BASE = os.getenv("ESP32_URL", "http://127.0.0.1:8083").rstrip("/")
_TIMEOUT = max(1, int(os.getenv("ESP32_TIMEOUT", "10")))


def _request(path: str, params: dict[str, str] | None = None):
    parsed = urlparse(_BASE)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("ESP32_URL must be an absolute http:// or https:// URL")
    response = requests.get(f"{_BASE}{path}", params=params, timeout=_TIMEOUT)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    return response.json() if "json" in content_type else response.text.strip()


@tool(
    "esp32_eyes",
    "Set the ESP32-OS TFT robot eye expression. Supports emotion and optional x/y offsets.",
    {
        "expression": {"type": "string", "description": "Emotion such as Happy, Sad, Angry, Surprised, Love"},
        "offset_x": {"type": "integer", "description": "Horizontal pixel offset"},
        "offset_y": {"type": "integer", "description": "Vertical pixel offset"},
    },
)
def esp32_eyes(expression: str, offset_x: int = 0, offset_y: int = 0):
    if not expression.strip() or any(char in expression for char in "\r\n,"):
        raise ValueError("expression must be one eye expression without commas or newlines")
    return _request("/eyes", {"q": f"{expression.strip()},{int(offset_x)},{int(offset_y)}"})


@tool(
    "esp32_move",
    "Move the ESP32-OS robot or stop it.",
    {
        "direction": {"type": "string", "description": "forward, backward, left, right, or stop"},
        "value": {"type": "string", "description": "Duration/speed for forward/backward or angle for left/right"},
        "speed": {"type": "string", "description": "Optional motor speed for forward/backward"},
    },
)
def esp32_move(direction: str, value: str = "", speed: str = ""):
    direction = direction.strip().lower()
    routes = {"forward": "/forward", "backward": "/backward", "left": "/left", "right": "/right", "stop": "/stop"}
    if direction not in routes:
        raise ValueError("direction must be forward, backward, left, right, or stop")
    params = {}
    if direction in {"forward", "backward"}:
        params = {"q": value or "1", "speed": speed or "255"}
    elif direction in {"left", "right"}:
        params = {"q": value or "90"}
    return _request(routes[direction], params)


@tool("esp32_sensor", "Read an ESP32-OS sensor endpoint.", {"sensor": {"type": "string", "description": "distance, temperature, or temperature_esp32"}})
def esp32_sensor(sensor: str):
    routes = {"distance": "/distance", "temperature": "/temperature", "temperature_esp32": "/temperature_esp32"}
    key = sensor.strip().lower()
    if key not in routes:
        raise ValueError("sensor must be distance, temperature, or temperature_esp32")
    return _request(routes[key], {"q": "c"} if key == "temperature" else None)


@tool("esp32_help", "Read the ESP32-OS robot API help response.", {})
def esp32_help():
    return _request("/help")
