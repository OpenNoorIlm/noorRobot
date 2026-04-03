from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.wslKaliLinux.wslKaliLinux")
logger.debug("Loaded tool module: wslKaliLinux.wslKaliLinux")

import subprocess
from app.utils.groq import tool


def _run(cmd: list[str], timeout: int | None = None):
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}


@tool(
    name="wsl_kali_start",
    description="Start the Kali Linux WSL distro.",
    params={},
)
def wsl_kali_start():
    return _run(["wsl", "-d", "kali-linux", "--", "echo", "WSL Kali started"])


@tool(
    name="wsl_kali_run",
    description="Run a command in WSL (Kali Linux distro).",
    params={
        "command": {"type": "string", "description": "Command to run inside Kali"},
        "user": {"type": "string", "description": "Username (optional)"},
        "cwd": {"type": "string", "description": "Working directory inside WSL (optional)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (optional)"},
    },
)
def wsl_kali_run(command: str, user: str = "", cwd: str = "", timeout: int | None = None):
    cmd = ["wsl", "-d", "kali-linux"]
    if user:
        cmd += ["-u", user]
    if cwd:
        cmd += ["--cd", cwd]
    cmd += ["--", "bash", "-lc", command]
    return _run(cmd, timeout=timeout)


@tool(
    name="wsl_kali_stop",
    description="Stop the Kali Linux WSL distro.",
    params={},
)
def wsl_kali_stop():
    return _run(["wsl", "-t", "kali-linux"])
