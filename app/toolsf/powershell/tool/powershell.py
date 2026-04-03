from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.powershell.powershell")
logger.debug("Loaded tool module: powershell.powershell")

import subprocess
import threading
import queue
import time
import uuid
from app.utils.groq import tool

_proc: subprocess.Popen | None = None
_q: "queue.Queue[str]" = queue.Queue()
_reader_thread: threading.Thread | None = None


def _reader_loop(proc: subprocess.Popen):
    try:
        for line in proc.stdout:  # type: ignore[assignment]
            _q.put(line)
    except Exception:
        pass


def _start_ps():
    global _proc, _reader_thread
    if _proc is not None and _proc.poll() is None:
        return
    _proc = subprocess.Popen(
        ["powershell.exe", "-NoLogo", "-NoProfile"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    _reader_thread = threading.Thread(
        target=_reader_loop, args=(_proc,), daemon=True
    )
    _reader_thread.start()


@tool(
    name="ps_open",
    description="Open a persistent Windows PowerShell session.",
    params={},
)
def ps_open() -> str:
    _start_ps()
    return "powershell session opened"


@tool(
    name="ps_run",
    description="Run a command in the persistent PowerShell session.",
    params={
        "command": {"type": "string", "description": "PowerShell command to execute"},
        "timeout": {"type": "integer", "description": "Max seconds to wait (optional)"},
    },
)
def ps_run(command: str, timeout: int | None = None) -> str:
    _start_ps()
    if _proc is None or _proc.stdin is None:
        return "powershell session not available"

    # Clear any buffered output from prior commands
    try:
        while True:
            _q.get_nowait()
    except queue.Empty:
        pass

    token = f"__END_{uuid.uuid4().hex}__"
    _proc.stdin.write(f"{command}\n")
    _proc.stdin.write(f"Write-Output {token}\n")
    _proc.stdin.flush()

    deadline = time.time() + (timeout if timeout is not None else 30)
    lines: list[str] = []
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            lines.append("[timeout]")
            break
        try:
            line = _q.get(timeout=remaining)
        except queue.Empty:
            lines.append("[timeout]")
            break
        if line.strip() == token:
            break
        lines.append(line.rstrip("\r\n"))

    return "\n".join(lines).strip()


@tool(
    name="ps_close",
    description="Close the persistent PowerShell session.",
    params={},
)
def ps_close() -> str:
    global _proc
    if _proc is None:
        return "powershell session not running"
    try:
        _proc.terminate()
    except Exception:
        pass
    _proc = None
    return "powershell session closed"


@tool(
    name="ps_run_once",
    description="Run a single PowerShell command (non-persistent).",
    params={
        "command": {"type": "string", "description": "PowerShell command"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def ps_run_once(command: str, timeout: int | None = None):
    res = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
