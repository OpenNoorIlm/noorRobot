from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.audio_tools.audio_tools")
logger.debug("Loaded tool module: audio_tools.audio_tools")

from pathlib import Path
from app.utils.groq import tool

try:
    from pydub import AudioSegment, effects  # type: ignore
except Exception:
    AudioSegment = None
    effects = None


def _require():
    if AudioSegment is None:
        raise RuntimeError("pydub not installed")


@tool(
    name="audio_info",
    description="Get audio duration and channels.",
    params={"path": {"type": "string"}},
)
def audio_info(path: str):
    _require()
    a = AudioSegment.from_file(path)
    return {"duration_ms": len(a), "channels": a.channels, "frame_rate": a.frame_rate}


@tool(
    name="audio_trim",
    description="Trim audio between start_ms and end_ms.",
    params={
        "path": {"type": "string"},
        "start_ms": {"type": "integer"},
        "end_ms": {"type": "integer"},
        "out": {"type": "string"},
        "fade_ms": {"type": "integer", "description": "Fade in/out ms (optional)"},
    },
)
def audio_trim(path: str, start_ms: int, end_ms: int, out: str, fade_ms: int = 0):
    _require()
    a = AudioSegment.from_file(path)
    clip = a[int(start_ms):int(end_ms)]
    if fade_ms:
        clip = clip.fade_in(int(fade_ms)).fade_out(int(fade_ms))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    clip.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_convert",
    description="Convert audio format.",
    params={
        "path": {"type": "string"},
        "out": {"type": "string"},
        "bitrate": {"type": "string", "description": "Bitrate like 192k (optional)"},
    },
)
def audio_convert(path: str, out: str, bitrate: str = ""):
    _require()
    a = AudioSegment.from_file(path)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    a.export(outp, format=outp.suffix.lstrip("."), bitrate=bitrate or None)
    return str(outp.resolve())


@tool(
    name="audio_volume",
    description="Change audio volume by dB.",
    params={
        "path": {"type": "string"},
        "db": {"type": "number"},
        "out": {"type": "string"},
    },
)
def audio_volume(path: str, db: float, out: str):
    _require()
    a = AudioSegment.from_file(path)
    a = a + float(db)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    a.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_concat",
    description="Concatenate multiple audio files in order.",
    params={
        "paths": {"type": "array", "description": "Audio paths in order"},
        "out": {"type": "string"},
        "crossfade_ms": {"type": "integer", "description": "Crossfade ms (optional)"},
    },
)
def audio_concat(paths: list[str], out: str, crossfade_ms: int = 0):
    _require()
    if not paths:
        raise ValueError("paths is empty")
    combined = AudioSegment.from_file(paths[0])
    for p in paths[1:]:
        seg = AudioSegment.from_file(p)
        combined = combined.append(seg, crossfade=int(crossfade_ms) if crossfade_ms else 0)
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    combined.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_fade",
    description="Apply fade in/out to audio.",
    params={
        "path": {"type": "string"},
        "fade_in_ms": {"type": "integer", "description": "Fade in ms (optional)"},
        "fade_out_ms": {"type": "integer", "description": "Fade out ms (optional)"},
        "out": {"type": "string"},
    },
)
def audio_fade(path: str, fade_in_ms: int = 0, fade_out_ms: int = 0, out: str = ""):
    _require()
    a = AudioSegment.from_file(path)
    if fade_in_ms:
        a = a.fade_in(int(fade_in_ms))
    if fade_out_ms:
        a = a.fade_out(int(fade_out_ms))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    a.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_speed",
    description="Change audio speed (playback rate).",
    params={
        "path": {"type": "string"},
        "rate": {"type": "number", "description": "Speed multiplier (e.g., 1.2)"},
        "out": {"type": "string"},
    },
)
def audio_speed(path: str, rate: float, out: str):
    _require()
    if effects is None:
        raise RuntimeError("pydub effects not available")
    a = AudioSegment.from_file(path)
    sped = effects.speedup(a, playback_speed=float(rate))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    sped.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_mix",
    description="Overlay one audio on another.",
    params={
        "base_path": {"type": "string"},
        "overlay_path": {"type": "string"},
        "position_ms": {"type": "integer", "description": "Start position ms (optional)"},
        "gain_during_overlay": {"type": "number", "description": "Reduce base during overlay in dB (optional)"},
        "out": {"type": "string"},
    },
)
def audio_mix(base_path: str, overlay_path: str, position_ms: int = 0, gain_during_overlay: float = 0.0, out: str = ""):
    _require()
    base = AudioSegment.from_file(base_path)
    over = AudioSegment.from_file(overlay_path)
    mixed = base.overlay(over, position=int(position_ms), gain_during_overlay=float(gain_during_overlay))
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    mixed.export(outp, format=outp.suffix.lstrip("."))
    return str(outp.resolve())


@tool(
    name="audio_split",
    description="Split audio into chunks by fixed duration.",
    params={
        "path": {"type": "string"},
        "chunk_ms": {"type": "integer", "description": "Chunk length ms"},
        "out_dir": {"type": "string"},
        "prefix": {"type": "string", "description": "Filename prefix (optional)"},
    },
)
def audio_split(path: str, chunk_ms: int, out_dir: str, prefix: str = "chunk"):
    _require()
    a = AudioSegment.from_file(path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(0, len(a), int(chunk_ms)):
        part = a[i:i + int(chunk_ms)]
        fp = out / f"{prefix}_{i//int(chunk_ms):04d}{Path(path).suffix}"
        part.export(fp, format=fp.suffix.lstrip("."))
        files.append(str(fp.resolve()))
    return files
