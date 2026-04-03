from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.process_manager.process_manager")
logger.debug("Loaded tool module: process_manager.process_manager")

import subprocess
from app.utils.groq import tool

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


@tool(
    name="proc_list",
    description="List processes.",
    params={
        "limit": {"type": "integer", "description": "Max processes (optional)"},
        "name": {"type": "string", "description": "Filter by name (optional)"},
    },
)
def proc_list(limit: int | None = None, name: str = ""):
    procs = []
    if psutil:
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            if name and name.lower() not in str(p.info.get("name", "")).lower():
                continue
            procs.append({"pid": p.info.get("pid"), "name": p.info.get("name"), "cmdline": p.info.get("cmdline")})
    else:
        out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
        procs = out.splitlines()
    return procs[:limit] if limit else procs


@tool(
    name="proc_kill",
    description="Kill a process by PID.",
    params={"pid": {"type": "integer", "description": "Process ID"}},
)
def proc_kill(pid: int):
    if psutil:
        psutil.Process(int(pid)).terminate()
        return {"ok": True}
    subprocess.check_call(["taskkill", "/PID", str(pid), "/F"])
    return {"ok": True}


@tool(
    name="proc_start",
    description="Start a process.",
    params={
        "command": {"type": "string", "description": "Command"},
        "cwd": {"type": "string", "description": "Working directory (optional)"},
    },
)
def proc_start(command: str, cwd: str = ""):
    p = subprocess.Popen(command, cwd=cwd or None, shell=True)
    return {"pid": p.pid}


@tool(
    name="proc_info",
    description="Get process info by PID.",
    params={"pid": {"type": "integer", "description": "Process ID"}},
)
def proc_info(pid: int):
    if not psutil:
        return {}
    p = psutil.Process(int(pid))
    return {
        "pid": p.pid,
        "name": p.name(),
        "exe": p.exe(),
        "cmdline": p.cmdline(),
        "status": p.status(),
        "cpu": p.cpu_percent(interval=0.1),
        "memory": p.memory_info()._asdict(),
    }


@tool(
    name="proc_find",
    description="Find processes by name (case-insensitive).",
    params={"name": {"type": "string", "description": "Process name substring"}},
)
def proc_find(name: str):
    return proc_list(name=name)


@tool(
    name="proc_suspend",
    description="Suspend a process by PID.",
    params={"pid": {"type": "integer", "description": "Process ID"}},
)
def proc_suspend(pid: int):
    if not psutil:
        return {"ok": False}
    psutil.Process(int(pid)).suspend()
    return {"ok": True}


@tool(
    name="proc_resume",
    description="Resume a process by PID.",
    params={"pid": {"type": "integer", "description": "Process ID"}},
)
def proc_resume(pid: int):
    if not psutil:
        return {"ok": False}
    psutil.Process(int(pid)).resume()
    return {"ok": True}


@tool(
    name="proc_wait",
    description="Wait for a process to finish.",
    params={
        "pid": {"type": "integer", "description": "Process ID"},
        "timeout": {"type": "number", "description": "Timeout seconds (optional)"},
    },
)
def proc_wait(pid: int, timeout: float | None = None):
    if not psutil:
        return {"ok": False}
    p = psutil.Process(int(pid))
    try:
        p.wait(timeout=timeout)
        return {"ok": True}
    except Exception:
        return {"ok": False}


@tool(
    name="proc_run_capture",
    description="Run a command and capture output.",
    params={
        "command": {"type": "string", "description": "Command"},
        "cwd": {"type": "string", "description": "Working directory (optional)"},
        "timeout": {"type": "number", "description": "Timeout seconds (optional)"},
    },
)
def proc_run_capture(command: str, cwd: str = "", timeout: float | None = None):
    p = subprocess.run(command, cwd=cwd or None, shell=True, text=True, capture_output=True, timeout=timeout)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
