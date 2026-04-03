from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.wslUbuntu.wslUbuntu")
logger.debug("Loaded tool module: wslUbuntu.wslUbuntu")

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
    name="wsl_ubuntu_start",
    description="Start the Ubuntu WSL distro.",
    params={},
)
def wsl_ubuntu_start():
    return _run(["wsl", "-d", "Ubuntu", "--", "echo", "WSL Ubuntu started"])


@tool(
    name="wsl_ubuntu_run",
    description="Run a command in WSL (Ubuntu distro).",
    params={
        "command": {"type": "string", "description": "Command to run inside Ubuntu"},
        "user": {"type": "string", "description": "Username (optional)"},
        "cwd": {"type": "string", "description": "Working directory inside WSL (optional)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (optional)"},
    },
)
def wsl_ubuntu_run(command: str, user: str = "", cwd: str = "", timeout: int | None = None):
    cmd = ["wsl", "-d", "Ubuntu"]
    if user:
        cmd += ["-u", user]
    if cwd:
        cmd += ["--cd", cwd]
    cmd += ["--", "bash", "-lc", command]
    return _run(cmd, timeout=timeout)


@tool(
    name="wsl_ubuntu_stop",
    description="Stop the Ubuntu WSL distro.",
    params={},
)
def wsl_ubuntu_stop():
    return _run(["wsl", "-t", "Ubuntu"])
