from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.cmd.cmd")
logger.debug("Loaded tool module: cmd.cmd")

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


def _start_cmd():
    global _proc, _reader_thread
    if _proc is not None and _proc.poll() is None:
        return
    _proc = subprocess.Popen(
        ["cmd.exe"],
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
    name="cmd_open",
    description="Open a persistent Windows cmd session.",
    params={},
)
def cmd_open() -> str:
    _start_cmd()
    return "cmd session opened"


@tool(
    name="cmd_run",
    description="Run a command in the persistent cmd session.",
    params={
        "command": {"type": "string", "description": "Command to execute"},
        "timeout": {"type": "integer", "description": "Max seconds to wait (optional)"},
    },
)
def cmd_run(command: str, timeout: int | None = None) -> str:
    _start_cmd()
    if _proc is None or _proc.stdin is None:
        return "cmd session not available"

    # Clear any buffered output from prior commands
    try:
        while True:
            _q.get_nowait()
    except queue.Empty:
        pass

    token = f"__END_{uuid.uuid4().hex}__"
    _proc.stdin.write(f"{command}\n")
    _proc.stdin.write(f"echo {token}\n")
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
    name="cmd_close",
    description="Close the persistent cmd session.",
    params={},
)
def cmd_close() -> str:
    global _proc
    if _proc is None:
        return "cmd session not running"
    try:
        _proc.terminate()
    except Exception:
        pass
    _proc = None
    return "cmd session closed"


@tool(
    name="cmd_run_once",
    description="Run a single cmd command (non-persistent).",
    params={
        "command": {"type": "string", "description": "Command to execute"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def cmd_run_once(command: str, timeout: int | None = None):
    res = subprocess.run(["cmd.exe", "/c", command], capture_output=True, text=True, timeout=timeout)
    return {"exit_code": res.returncode, "stdout": res.stdout, "stderr": res.stderr}
