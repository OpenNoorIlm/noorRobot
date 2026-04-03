from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.network_tools.network_tools")
logger.debug("Loaded tool module: network_tools.network_tools")

import socket
import subprocess
from app.utils.groq import tool

try:
    import requests  # type: ignore
except Exception:
    requests = None


@tool(
    name="net_ping",
    description="Ping a host.",
    params={
        "host": {"type": "string", "description": "Host"},
        "count": {"type": "integer", "description": "Count"},
    },
)
def net_ping(host: str, count: int = 4):
    out = subprocess.check_output(["ping", host, "-n", str(count)], text=True, errors="ignore")
    return out


@tool(
    name="net_traceroute",
    description="Traceroute a host.",
    params={"host": {"type": "string", "description": "Host"}},
)
def net_traceroute(host: str):
    out = subprocess.check_output(["tracert", host], text=True, errors="ignore")
    return out


@tool(
    name="net_public_ip",
    description="Get public IP address.",
    params={},
)
def net_public_ip():
    if requests is None:
        return "requests not installed"
    return requests.get("https://api.ipify.org", timeout=10).text.strip()


@tool(
    name="net_local_ip",
    description="Get local IP address.",
    params={},
)
def net_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


@tool(
    name="net_dns_lookup",
    description="Resolve DNS for a hostname.",
    params={"host": {"type": "string", "description": "Host"}},
)
def net_dns_lookup(host: str):
    return socket.gethostbyname_ex(host)


@tool(
    name="net_port_check",
    description="Check if a TCP port is open.",
    params={
        "host": {"type": "string", "description": "Host"},
        "port": {"type": "integer", "description": "Port"},
        "timeout": {"type": "number", "description": "Timeout seconds (optional)"},
    },
)
def net_port_check(host: str, port: int, timeout: float = 3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, int(port)))
        return {"open": True}
    except Exception:
        return {"open": False}
    finally:
        s.close()


@tool(
    name="net_port_scan",
    description="Scan a range of TCP ports.",
    params={
        "host": {"type": "string", "description": "Host"},
        "start_port": {"type": "integer", "description": "Start port"},
        "end_port": {"type": "integer", "description": "End port"},
        "timeout": {"type": "number", "description": "Timeout seconds (optional)"},
    },
)
def net_port_scan(host: str, start_port: int, end_port: int, timeout: float = 0.5):
    open_ports = []
    for port in range(int(start_port), int(end_port) + 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()
    return {"open_ports": open_ports}


@tool(
    name="net_http_head",
    description="HTTP HEAD request to a URL.",
    params={"url": {"type": "string", "description": "URL"}},
)
def net_http_head(url: str):
    if requests is None:
        return "requests not installed"
    r = requests.head(url, timeout=10, allow_redirects=True)
    return {"status": r.status_code, "headers": dict(r.headers)}
