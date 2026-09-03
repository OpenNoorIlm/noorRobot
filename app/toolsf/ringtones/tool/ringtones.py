from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from pathlib import Path

from app.utils.groq import tool

logger = logging.getLogger("NoorRobot.Tools.ringtones")

RINGTONES_DIR = Path("/home/bismillah/Downloads/recorder").resolve()
_ALLOWED_SUFFIX = ".mp3"
_player_lock = threading.Lock()
_player: subprocess.Popen | None = None
_scheduled: dict[str, threading.Timer] = {}


def _files() -> list[Path]:
    return sorted(
        path for path in RINGTONES_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == _ALLOWED_SUFFIX
    ) if RINGTONES_DIR.is_dir() else []


def _find_ringtone(name: str) -> Path:
    requested = Path(name).name
    for path in _files():
        if requested.lower() in {path.name.lower(), path.stem.lower()}:
            return path
    available = ", ".join(path.name for path in _files()) or "none"
    raise ValueError(f"Ringtone not found: {name}. Available: {available}")


def _player_command(path: Path) -> list[str]:
    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet", str(path)]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
    if shutil.which("cvlc"):
        return ["cvlc", "--play-and-exit", "--quiet", str(path)]
    raise RuntimeError("No MP3 player found. Install mpv, ffmpeg, or VLC.")


def _clear_finished_player() -> None:
    global _player
    if _player is not None and _player.poll() is not None:
        _player = None


@tool(
    name="ringtone_list",
    description="List the available NoorRobot MP3 ringtones from the recorder folder.",
    params={},
)
def ringtone_list() -> list[str]:
    return [path.name for path in _files()]


@tool(
    name="ringtone_play",
    description="Play one of the available NoorRobot MP3 ringtones by filename or name.",
    params={"name": {"type": "string", "description": "MP3 filename or stem, such as naat or hasbunallahu"}},
)
def ringtone_play(name: str) -> str:
    global _player
    path = _find_ringtone(name)
    command = _player_command(path)
    with _player_lock:
        _clear_finished_player()
        if _player is not None:
            _player.terminate()
            _player.wait(timeout=3)
        _player = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return f"Playing {path.name}"


@tool(
    name="ringtone_stop",
    description="Stop the currently playing NoorRobot ringtone.",
    params={},
)
def ringtone_stop() -> str:
    global _player
    with _player_lock:
        _clear_finished_player()
        if _player is None:
            return "No ringtone is playing"
        _player.terminate()
        _player.wait(timeout=3)
        _player = None
    return "Ringtone stopped"


@tool(
    name="ringtone_status",
    description="Report whether a NoorRobot ringtone is currently playing.",
    params={},
)
def ringtone_status() -> str:
    with _player_lock:
        _clear_finished_player()
        return "Ringtone is playing" if _player is not None else "No ringtone is playing"


@tool(
    name="ringtone_schedule",
    description="Schedule a NoorRobot MP3 ringtone to play after a delay in seconds.",
    params={
        "name": {"type": "string", "description": "MP3 filename or stem"},
        "delay_seconds": {"type": "number", "description": "Delay before playback"},
    },
)
def ringtone_schedule(name: str, delay_seconds: float) -> str:
    path = _find_ringtone(name)
    delay = max(0.0, float(delay_seconds))
    job_id = f"ringtone-{len(_scheduled) + 1}"

    def _play_scheduled() -> None:
        try:
            ringtone_play(path.name)
        finally:
            _scheduled.pop(job_id, None)

    timer = threading.Timer(delay, _play_scheduled)
    timer.daemon = True
    _scheduled[job_id] = timer
    timer.start()
    return f"Scheduled {path.name} in {delay:g} seconds (job_id={job_id})"


@tool(
    name="ringtone_schedule_cancel",
    description="Cancel a scheduled NoorRobot ringtone by job ID.",
    params={"job_id": {"type": "string", "description": "Job ID returned by ringtone_schedule"}},
)
def ringtone_schedule_cancel(job_id: str) -> str:
    timer = _scheduled.pop(job_id, None)
    if timer is None:
        return f"No scheduled ringtone found for {job_id}"
    timer.cancel()
    return f"Cancelled {job_id}"
