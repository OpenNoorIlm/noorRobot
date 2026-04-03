from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.http_client.http_client")
logger.debug("Loaded tool module: http_client.http_client")

from app.utils.groq import tool

try:
    import requests  # type: ignore
except Exception:
    requests = None


@tool(
    name="http_request",
    description="Make an HTTP request.",
    params={
        "method": {"type": "string", "description": "GET/POST/etc"},
        "url": {"type": "string", "description": "URL"},
        "headers": {"type": "object", "description": "Headers (optional)"},
        "params": {"type": "object", "description": "Query params (optional)"},
        "data": {"type": "string", "description": "Body data (optional)"},
        "json": {"type": "object", "description": "JSON body (optional)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
        "auth": {"type": "array", "description": "Basic auth [user, pass] (optional)"},
        "verify": {"type": "boolean", "description": "Verify TLS (optional)"},
        "allow_redirects": {"type": "boolean", "description": "Follow redirects (optional)"},
    },
)
def http_request(
    method: str,
    url: str,
    headers: dict | None = None,
    params: dict | None = None,
    data: str = "",
    json: dict | None = None,
    timeout: int = 20,
    auth: list | None = None,
    verify: bool | None = None,
    allow_redirects: bool | None = None,
):
    if requests is None:
        raise RuntimeError("requests not installed")
    resp = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        data=data or None,
        json=json,
        timeout=timeout,
        auth=tuple(auth) if auth else None,
        verify=True if verify is None else verify,
        allow_redirects=True if allow_redirects is None else allow_redirects,
    )
    return {"status": resp.status_code, "headers": dict(resp.headers), "text": resp.text}


@tool(
    name="http_head",
    description="Make an HTTP HEAD request.",
    params={
        "url": {"type": "string", "description": "URL"},
        "headers": {"type": "object", "description": "Headers (optional)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def http_head(url: str, headers: dict | None = None, timeout: int = 20):
    if requests is None:
        raise RuntimeError("requests not installed")
    resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
    return {"status": resp.status_code, "headers": dict(resp.headers)}


@tool(
    name="http_download",
    description="Download a URL to a local file.",
    params={
        "url": {"type": "string"},
        "out": {"type": "string"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def http_download(url: str, out: str, timeout: int = 30):
    if requests is None:
        raise RuntimeError("requests not installed")
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    from pathlib import Path
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return str(outp.resolve())
