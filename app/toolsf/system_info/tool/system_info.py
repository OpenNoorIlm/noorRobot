from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.system_info.system_info")
logger.debug("Loaded tool module: system_info.system_info")

import os
import platform
import subprocess
from datetime import datetime
from app.utils.groq import tool

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


def _gpu_info():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], text=True)
        return [line.strip() for line in out.strip().splitlines() if line.strip()]
    except Exception:
        return []


@tool(
    name="system_info",
    description="Get system information (OS, CPU, memory, disk, GPU).",
    params={
        "include_disks": {"type": "boolean", "description": "Include disk usage"},
        "include_network": {"type": "boolean", "description": "Include network interfaces"},
        "include_users": {"type": "boolean", "description": "Include logged-in users (optional)"},
        "include_env": {"type": "boolean", "description": "Include environment variables (optional)"},
        "include_battery": {"type": "boolean", "description": "Include battery info (optional)"},
    },
)
def system_info(
    include_disks: bool = True,
    include_network: bool = False,
    include_users: bool = False,
    include_env: bool = False,
    include_battery: bool = False,
):
    info = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": platform.node(),
        "time": datetime.now().isoformat(),
        "gpu": _gpu_info(),
    }
    if psutil:
        info["cpu_count"] = psutil.cpu_count(logical=True)
        info["cpu_freq"] = getattr(psutil.cpu_freq(), "current", None)
        vm = psutil.virtual_memory()
        info["memory"] = {"total": vm.total, "available": vm.available, "percent": vm.percent}
        if include_disks:
            disks = []
            for p in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    disks.append({"device": p.device, "mount": p.mountpoint, "total": usage.total, "used": usage.used, "percent": usage.percent})
                except Exception:
                    continue
            info["disks"] = disks
        if include_network:
            info["network"] = list(psutil.net_if_addrs().keys())
        if include_users:
            info["users"] = [u._asdict() for u in psutil.users()]
        if include_battery:
            try:
                bat = psutil.sensors_battery()
                info["battery"] = bat._asdict() if bat else None
            except Exception:
                info["battery"] = None
    if include_env:
        info["env"] = dict(os.environ)
    return info
