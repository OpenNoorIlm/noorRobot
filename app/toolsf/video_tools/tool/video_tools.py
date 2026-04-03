from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.video_tools.video_tools")
logger.debug("Loaded tool module: video_tools.video_tools")

import subprocess
import tempfile
from pathlib import Path
from app.utils.groq import tool


def _run(args):
    return subprocess.check_output(args, text=True, errors="ignore")


def _call(args):
    subprocess.check_call(args)


@tool(
    name="video_info",
    description="Get video info via ffprobe.",
    params={"path": {"type": "string"}},
)
def video_info(path: str):
    return _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", path])


@tool(
    name="video_trim",
    description="Trim a video using ffmpeg.",
    params={"path": {"type": "string"}, "start": {"type": "string"}, "duration": {"type": "string"}, "out": {"type": "string"}},
)
def video_trim(path: str, start: str, duration: str, out: str):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    _call(["ffmpeg", "-y", "-ss", start, "-i", path, "-t", duration, str(outp)])
    return str(outp.resolve())


@tool(
    name="video_extract_frames",
    description="Extract frames from a video.",
    params={"path": {"type": "string"}, "fps": {"type": "string"}, "out_dir": {"type": "string"}},
)
def video_extract_frames(path: str, fps: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pattern = str(out / "frame_%04d.png")
    _call(["ffmpeg", "-y", "-i", path, "-vf", f"fps={fps}", pattern])
    return str(out.resolve())


@tool(
    name="video_convert",
    description="Convert video format with optional codecs.",
    params={
        "path": {"type": "string"},
        "out": {"type": "string"},
        "vcodec": {"type": "string", "description": "Video codec (optional)"},
        "acodec": {"type": "string", "description": "Audio codec (optional)"},
        "crf": {"type": "string", "description": "CRF value (optional)"},
        "preset": {"type": "string", "description": "Encoding preset (optional)"},
        "bitrate": {"type": "string", "description": "Video bitrate (optional)"},
        "audio_bitrate": {"type": "string", "description": "Audio bitrate (optional)"},
        "extra_args": {"type": "array", "description": "Extra ffmpeg args (optional)"},
    },
)
def video_convert(
    path: str,
    out: str,
    vcodec: str = "",
    acodec: str = "",
    crf: str = "",
    preset: str = "",
    bitrate: str = "",
    audio_bitrate: str = "",
    extra_args: list[str] | None = None,
):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    args = ["ffmpeg", "-y", "-i", path]
    if vcodec:
        args += ["-c:v", vcodec]
    if acodec:
        args += ["-c:a", acodec]
    if crf:
        args += ["-crf", str(crf)]
    if preset:
        args += ["-preset", preset]
    if bitrate:
        args += ["-b:v", bitrate]
    if audio_bitrate:
        args += ["-b:a", audio_bitrate]
    if extra_args:
        args += list(extra_args)
    args.append(str(outp))
    _call(args)
    return str(outp.resolve())


@tool(
    name="video_resize",
    description="Resize video to width/height.",
    params={
        "path": {"type": "string"},
        "width": {"type": "integer"},
        "height": {"type": "integer"},
        "out": {"type": "string"},
        "keep_aspect": {"type": "boolean"},
    },
)
def video_resize(path: str, width: int, height: int, out: str, keep_aspect: bool = True):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    if keep_aspect:
        vf = f"scale=w={int(width)}:h={int(height)}:force_original_aspect_ratio=decrease"
    else:
        vf = f"scale={int(width)}:{int(height)}"
    _call(["ffmpeg", "-y", "-i", path, "-vf", vf, str(outp)])
    return str(outp.resolve())


@tool(
    name="video_extract_audio",
    description="Extract audio track from video.",
    params={
        "path": {"type": "string"},
        "out": {"type": "string"},
        "acodec": {"type": "string", "description": "Audio codec (optional)"},
        "bitrate": {"type": "string", "description": "Audio bitrate (optional)"},
    },
)
def video_extract_audio(path: str, out: str, acodec: str = "", bitrate: str = ""):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    args = ["ffmpeg", "-y", "-i", path, "-vn"]
    if acodec:
        args += ["-c:a", acodec]
    if bitrate:
        args += ["-b:a", bitrate]
    args.append(str(outp))
    _call(args)
    return str(outp.resolve())


@tool(
    name="video_add_audio",
    description="Replace or add audio track to a video.",
    params={
        "video_path": {"type": "string"},
        "audio_path": {"type": "string"},
        "out": {"type": "string"},
        "shortest": {"type": "boolean", "description": "Stop at shortest stream (optional)"},
    },
)
def video_add_audio(video_path: str, audio_path: str, out: str, shortest: bool = True):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    args = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac"]
    if shortest:
        args += ["-shortest"]
    args.append(str(outp))
    _call(args)
    return str(outp.resolve())


@tool(
    name="video_concat",
    description="Concatenate videos (same codec/format).",
    params={
        "paths": {"type": "array", "description": "Video paths"},
        "out": {"type": "string"},
    },
)
def video_concat(paths: list[str], out: str):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        list_path = Path(td) / "inputs.txt"
        list_path.write_text("\n".join([f"file '{Path(p).as_posix()}'" for p in paths]), encoding="utf-8")
        _call(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(outp)])
    return str(outp.resolve())


@tool(
    name="video_set_fps",
    description="Change video FPS.",
    params={"path": {"type": "string"}, "fps": {"type": "string"}, "out": {"type": "string"}},
)
def video_set_fps(path: str, fps: str, out: str):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    _call(["ffmpeg", "-y", "-i", path, "-vf", f"fps={fps}", str(outp)])
    return str(outp.resolve())


@tool(
    name="video_screenshot",
    description="Capture a frame from video at timestamp.",
    params={"path": {"type": "string"}, "timestamp": {"type": "string"}, "out": {"type": "string"}},
)
def video_screenshot(path: str, timestamp: str, out: str):
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    _call(["ffmpeg", "-y", "-ss", timestamp, "-i", path, "-frames:v", "1", str(outp)])
    return str(outp.resolve())
