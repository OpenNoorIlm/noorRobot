from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.noor_face_anim.noor_face_anim")
logger.debug("Loaded tool module: noor_face_anim.noor_face_anim")

import os
import requests as _requests
from app.utils.groq import tool

_BASE = os.getenv("NOOR_API_URL", "http://127.0.0.1:8000").rstrip("/")


def _get(path: str, params: dict | None = None):
    resp = _requests.get(f"{_BASE}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ─── Animation ────────────────────────────────────────────────────────────────

@tool(
    name="face_anim_list",
    description="List face animations with optional filters (eye_key, mouth_key, anim_type). Supports pagination via limit/offset.",
    params={
        "eye_key":   {"type": "string",  "description": "Filter by eye shape key (optional)"},
        "mouth_key": {"type": "string",  "description": "Filter by mouth shape key (optional)"},
        "anim_type": {"type": "string",  "description": "Filter by anim_type: both | eye_anim_mouth_holds | eye_anim_mouth_static | mouth_anim_eye_static (optional)"},
        "limit":     {"type": "integer", "description": "Max results (1–500, default 50)"},
        "offset":    {"type": "integer", "description": "Pagination offset (default 0)"},
    },
)
def face_anim_list(
    eye_key: str | None = None,
    mouth_key: str | None = None,
    anim_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    params = {"limit": limit, "offset": offset}
    if eye_key:   params["eye_key"]   = eye_key
    if mouth_key: params["mouth_key"] = mouth_key
    if anim_type: params["anim_type"] = anim_type
    return _get("/animations", params)


@tool(
    name="face_anim_search",
    description="Search face animations by eye and/or mouth shape key combo.",
    params={
        "eye":   {"type": "string", "description": "Eye shape key (optional)"},
        "mouth": {"type": "string", "description": "Mouth shape key (optional)"},
    },
)
def face_anim_search(eye: str | None = None, mouth: str | None = None):
    params = {}
    if eye:   params["eye"]   = eye
    if mouth: params["mouth"] = mouth
    return _get("/animations/search", params)


@tool(
    name="face_anim_get",
    description="Get full metadata for a face animation by its name e.g. EBlink||MSmile.",
    params={"name": {"type": "string", "description": "Animation name e.g. EBlink||MSmile"}},
)
def face_anim_get(name: str):
    return _get(f"/animation/{name}")


@tool(
    name="face_anim_get_timeline",
    description="Get just the timeline (0-5 and 5-10 frame descriptions) for an animation.",
    params={"name": {"type": "string", "description": "Animation name"}},
)
def face_anim_get_timeline(name: str):
    return _get(f"/animation/{name}/timeline")


@tool(
    name="face_anim_get_description",
    description="Get just the description string for an animation.",
    params={"name": {"type": "string", "description": "Animation name"}},
)
def face_anim_get_description(name: str):
    return _get(f"/animation/{name}/description")


@tool(
    name="face_anim_get_paths",
    description="Get the file paths and API URLs for an animation's video and static image.",
    params={"name": {"type": "string", "description": "Animation name"}},
)
def face_anim_get_paths(name: str):
    return _get(f"/animation/{name}/paths")


@tool(
    name="face_anim_download_video",
    description="Download the AVI video clip for an animation to a local file.",
    params={
        "name": {"type": "string", "description": "Animation name e.g. EBlink||MSmile"},
        "out":  {"type": "string", "description": "Local output file path"},
    },
)
def face_anim_download_video(name: str, out: str):
    from pathlib import Path
    resp = _requests.get(f"{_BASE}/animation/{name}/video", stream=True, timeout=30)
    resp.raise_for_status()
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return str(outp.resolve())


@tool(
    name="face_anim_download_static",
    description="Download the static first-frame JPEG for an animation to a local file.",
    params={
        "name": {"type": "string", "description": "Animation name"},
        "out":  {"type": "string", "description": "Local output file path"},
    },
)
def face_anim_download_static(name: str, out: str):
    from pathlib import Path
    resp = _requests.get(f"{_BASE}/animation/{name}/static", stream=True, timeout=10)
    resp.raise_for_status()
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        f.write(resp.content)
    return str(outp.resolve())


# ─── Keys ─────────────────────────────────────────────────────────────────────

@tool(
    name="face_anim_keys_all",
    description="Get all available eye keys, mouth keys and animation types.",
    params={},
)
def face_anim_keys_all():
    return _get("/keys")


@tool(
    name="face_anim_keys_eye_list",
    description="List all distinct eye shape keys available in the face animation database.",
    params={},
)
def face_anim_keys_eye_list():
    return _get("/keys/eye")


@tool(
    name="face_anim_keys_eye_get",
    description="Get info about a specific eye shape key — total animations, available mouth combos, animation types.",
    params={"eye_key": {"type": "string", "description": "Eye shape key e.g. Blink, Angry, LT"}},
)
def face_anim_keys_eye_get(eye_key: str):
    return _get(f"/keys/eye/{eye_key}")


@tool(
    name="face_anim_keys_eye_animations",
    description="Get all animations that use a specific eye shape key.",
    params={"eye_key": {"type": "string", "description": "Eye shape key"}},
)
def face_anim_keys_eye_animations(eye_key: str):
    return _get(f"/keys/eye/{eye_key}/animations")


@tool(
    name="face_anim_keys_mouth_list",
    description="List all distinct mouth shape keys available in the face animation database.",
    params={},
)
def face_anim_keys_mouth_list():
    return _get("/keys/mouth")


@tool(
    name="face_anim_keys_mouth_get",
    description="Get info about a specific mouth shape key — total animations, available eye combos, animation types.",
    params={"mouth_key": {"type": "string", "description": "Mouth shape key e.g. Smile, Frown, AH"}},
)
def face_anim_keys_mouth_get(mouth_key: str):
    return _get(f"/keys/mouth/{mouth_key}")


@tool(
    name="face_anim_keys_mouth_animations",
    description="Get all animations that use a specific mouth shape key.",
    params={"mouth_key": {"type": "string", "description": "Mouth shape key"}},
)
def face_anim_keys_mouth_animations(mouth_key: str):
    return _get(f"/keys/mouth/{mouth_key}/animations")


@tool(
    name="face_anim_keys_anim_type_list",
    description="List all distinct animation types in the face animation database.",
    params={},
)
def face_anim_keys_anim_type_list():
    return _get("/keys/anim_type")


@tool(
    name="face_anim_keys_anim_type_get",
    description="Get info about a specific animation type — total count, eye keys, mouth keys used.",
    params={"anim_type": {"type": "string", "description": "Animation type e.g. both, eye_anim_mouth_static"}},
)
def face_anim_keys_anim_type_get(anim_type: str):
    return _get(f"/keys/anim_type/{anim_type}")


@tool(
    name="face_anim_keys_anim_type_animations",
    description="Get all animations of a specific animation type. Supports pagination.",
    params={
        "anim_type": {"type": "string", "description": "Animation type"},
        "limit":     {"type": "integer", "description": "Max results (default 50)"},
        "offset":    {"type": "integer", "description": "Pagination offset (default 0)"},
    },
)
def face_anim_keys_anim_type_animations(anim_type: str, limit: int = 50, offset: int = 0):
    return _get(f"/keys/anim_type/{anim_type}/animations", {"limit": limit, "offset": offset})


@tool(
    name="face_anim_combo_get",
    description="Get all animations for a specific eye+mouth combo.",
    params={
        "eye_key":   {"type": "string", "description": "Eye shape key"},
        "mouth_key": {"type": "string", "description": "Mouth shape key"},
    },
)
def face_anim_combo_get(eye_key: str, mouth_key: str):
    return _get(f"/keys/combo/{eye_key}/{mouth_key}")


@tool(
    name="face_anim_combo_download_video",
    description="Download the video for a specific eye+mouth combo. Optionally filter by anim_type.",
    params={
        "eye_key":   {"type": "string", "description": "Eye shape key"},
        "mouth_key": {"type": "string", "description": "Mouth shape key"},
        "anim_type": {"type": "string", "description": "Animation type filter (optional)"},
        "out":       {"type": "string", "description": "Local output file path"},
    },
)
def face_anim_combo_download_video(eye_key: str, mouth_key: str, out: str, anim_type: str | None = None):
    from pathlib import Path
    params = {}
    if anim_type:
        params["anim_type"] = anim_type
    resp = _requests.get(f"{_BASE}/keys/combo/{eye_key}/{mouth_key}/video", params=params, stream=True, timeout=30)
    resp.raise_for_status()
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return str(outp.resolve())


@tool(
    name="face_anim_combo_download_static",
    description="Download the static first-frame image for a specific eye+mouth combo.",
    params={
        "eye_key":   {"type": "string", "description": "Eye shape key"},
        "mouth_key": {"type": "string", "description": "Mouth shape key"},
        "out":       {"type": "string", "description": "Local output file path"},
    },
)
def face_anim_combo_download_static(eye_key: str, mouth_key: str, out: str):
    from pathlib import Path
    resp = _requests.get(f"{_BASE}/keys/combo/{eye_key}/{mouth_key}/show", stream=True, timeout=10)
    resp.raise_for_status()
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        f.write(resp.content)
    return str(outp.resolve())


# ─── Stats & Config ───────────────────────────────────────────────────────────

@tool(
    name="face_anim_stats",
    description="Get overall statistics about the face animation database — total animations, unique keys, type breakdown.",
    params={},
)
def face_anim_stats():
    return _get("/stats")


@tool(
    name="face_anim_config",
    description="Get the full config map of all animation names to their video file paths.",
    params={},
)
def face_anim_config():
    return _get("/config")
