from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.browser_control.browser_control")
logger.debug("Loaded tool module: browser_control.browser_control")

import webbrowser
from app.utils.groq import tool

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:
    sync_playwright = None


def _require():
    if sync_playwright is None:
        raise RuntimeError("playwright not installed")


def _context_kwargs(user_agent: str = "", viewport: dict | None = None, headers: dict | None = None):
    kwargs = {}
    if user_agent:
        kwargs["user_agent"] = user_agent
    if viewport:
        kwargs["viewport"] = viewport
    if headers:
        kwargs["extra_http_headers"] = headers
    return kwargs


@tool(
    name="browser_open",
    description="Open a URL in the default browser.",
    params={"url": {"type": "string"}},
)
def browser_open(url: str):
    webbrowser.open(url)
    return {"ok": True}


@tool(
    name="browser_screenshot",
    description="Take a screenshot of a web page (requires playwright).",
    params={"url": {"type": "string"}, "out": {"type": "string"}},
)
def browser_screenshot(url: str, out: str):
    return browser_screenshot_adv(url=url, out=out)


@tool(
    name="browser_screenshot_adv",
    description="Take a screenshot with advanced options (requires playwright).",
    params={
        "url": {"type": "string"},
        "out": {"type": "string"},
        "full_page": {"type": "boolean"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
        "selector": {"type": "string", "description": "CSS selector to screenshot (optional)"},
        "user_agent": {"type": "string", "description": "User-Agent (optional)"},
        "headers": {"type": "object", "description": "Extra headers (optional)"},
        "viewport": {"type": "object", "description": "Viewport {width,height} (optional)"},
        "cookies": {"type": "array", "description": "Cookies list (optional)"},
    },
)
def browser_screenshot_adv(
    url: str,
    out: str,
    full_page: bool = True,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
    selector: str = "",
    user_agent: str = "",
    headers: dict | None = None,
    viewport: dict | None = None,
    cookies: list[dict] | None = None,
):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(**_context_kwargs(user_agent, viewport, headers))
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        if selector:
            el = page.query_selector(selector)
            if el is None:
                raise RuntimeError("selector not found")
            el.screenshot(path=out)
        else:
            page.screenshot(path=out, full_page=full_page)
        browser.close()
    return out


@tool(
    name="browser_get_html",
    description="Fetch page HTML (requires playwright).",
    params={
        "url": {"type": "string"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
        "selector": {"type": "string", "description": "CSS selector to get inner HTML (optional)"},
        "user_agent": {"type": "string", "description": "User-Agent (optional)"},
        "headers": {"type": "object", "description": "Extra headers (optional)"},
        "viewport": {"type": "object", "description": "Viewport {width,height} (optional)"},
        "cookies": {"type": "array", "description": "Cookies list (optional)"},
    },
)
def browser_get_html(
    url: str,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
    selector: str = "",
    user_agent: str = "",
    headers: dict | None = None,
    viewport: dict | None = None,
    cookies: list[dict] | None = None,
):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(**_context_kwargs(user_agent, viewport, headers))
        if cookies:
            ctx.add_cookies(cookies)
        page = ctx.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        if selector:
            el = page.query_selector(selector)
            if el is None:
                raise RuntimeError("selector not found")
            html = el.inner_html()
        else:
            html = page.content()
        browser.close()
    return html


@tool(
    name="browser_pdf",
    description="Save page as PDF (requires playwright).",
    params={
        "url": {"type": "string"},
        "out": {"type": "string"},
        "format": {"type": "string", "description": "Page format like A4 (optional)"},
        "landscape": {"type": "boolean", "description": "Landscape (optional)"},
        "print_background": {"type": "boolean", "description": "Print background (optional)"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
    },
)
def browser_pdf(
    url: str,
    out: str,
    format: str = "A4",
    landscape: bool = False,
    print_background: bool = True,
    wait_until: str = "networkidle",
    timeout_ms: int = 30000,
):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        page.pdf(path=out, format=format, landscape=landscape, print_background=print_background)
        browser.close()
    return out


@tool(
    name="browser_eval",
    description="Evaluate JS on a page and return result (requires playwright).",
    params={
        "url": {"type": "string"},
        "script": {"type": "string", "description": "JavaScript expression"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
    },
)
def browser_eval(url: str, script: str, wait_until: str = "networkidle", timeout_ms: int = 30000):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        result = page.evaluate(script)
        browser.close()
    return result


@tool(
    name="browser_click",
    description="Open a page and click a selector (requires playwright).",
    params={
        "url": {"type": "string"},
        "selector": {"type": "string"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
    },
)
def browser_click(url: str, selector: str, wait_until: str = "networkidle", timeout_ms: int = 30000):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        page.click(selector, timeout=timeout_ms)
        browser.close()
    return {"ok": True}


@tool(
    name="browser_fill",
    description="Open a page and fill an input (requires playwright).",
    params={
        "url": {"type": "string"},
        "selector": {"type": "string"},
        "text": {"type": "string"},
        "wait_until": {"type": "string", "description": "load|domcontentloaded|networkidle (optional)"},
        "timeout_ms": {"type": "integer", "description": "Timeout ms (optional)"},
    },
)
def browser_fill(url: str, selector: str, text: str, wait_until: str = "networkidle", timeout_ms: int = 30000):
    _require()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        page.fill(selector, text, timeout=timeout_ms)
        browser.close()
    return {"ok": True}
