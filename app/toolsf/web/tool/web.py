from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.web.web")
logger.debug("Loaded tool module: web.web")

import os
from pathlib import Path
from html import unescape
from urllib.parse import quote_plus
from app.utils.groq import tool

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if load_dotenv is not None:
    load_dotenv(_ENV_PATH)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()


def _http_get(url: str, timeout: int = 15) -> str:
    if requests is None:
        from urllib.request import urlopen
        with urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; NoorRobot/1.0)"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def _tavily_search(
    query: str,
    num_results: int = 5,
    *,
    auto_parameters: bool | None = None,
    topic: str | None = None,
    search_depth: str | None = None,
    chunks_per_source: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_answer: str | bool | None = None,
    include_raw_content: str | bool | None = None,
    include_images: bool | None = None,
    include_image_descriptions: bool | None = None,
    include_favicon: bool | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    exact_match: bool | None = None,
) -> list[dict]:
    if requests is None:
        raise RuntimeError("requests is required for Tavily search.")
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not found in app/toolsf/web/.env")
    payload = {
        "query": query,
        "max_results": max(0, int(num_results)),
    }
    # Optional parameters (only include when provided)
    if auto_parameters is not None:
        payload["auto_parameters"] = auto_parameters
    if topic:
        payload["topic"] = topic
    if search_depth:
        payload["search_depth"] = search_depth
    if chunks_per_source is not None:
        payload["chunks_per_source"] = int(chunks_per_source)
    if time_range:
        payload["time_range"] = time_range
    if days is not None:
        payload["days"] = int(days)
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if include_answer is not None:
        payload["include_answer"] = include_answer
    if include_raw_content is not None:
        payload["include_raw_content"] = include_raw_content
    if include_images is not None:
        payload["include_images"] = include_images
    if include_image_descriptions is not None:
        payload["include_image_descriptions"] = include_image_descriptions
    if include_favicon is not None:
        payload["include_favicon"] = include_favicon
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if country:
        payload["country"] = country
    if exact_match is not None:
        payload["exact_match"] = exact_match

    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        "https://api.tavily.com/search", json=payload, headers=headers, timeout=20
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for r in data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        })
        if len(results) >= num_results:
            break
    return results


def _extract_results_ddg(html: str, limit: int) -> list[dict]:
    results: list[dict] = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for res in soup.select("div.result"):
            a = res.select_one("a.result__a")
            if not a:
                continue
            url = a.get("href", "")
            title = a.get_text(strip=True)
            snippet_el = res.select_one("a.result__snippet, div.result__snippet")
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= limit:
                break
        return results

    # Fallback: very simple parsing (best-effort)
    import re
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html):
        url = unescape(m.group(1))
        title = unescape(re.sub("<.*?>", "", m.group(2)))
        results.append({"title": title, "url": url, "snippet": ""})
        if len(results) >= limit:
            break
    return results


@tool(
    name="search",
    description="Search the web and return results.",
    params={
        "query": {"type": "string", "description": "Search query"},
        "num_results": {"type": "integer", "description": "Number of results (default 5)"},
        "provider": {"type": "string", "description": "Search provider: ddg or tavily (default ddg)"},
        "auto_parameters": {"type": "boolean", "description": "Tavily: auto-configure parameters (optional)"},
        "topic": {"type": "string", "description": "Tavily: general|news|finance (optional)"},
        "search_depth": {"type": "string", "description": "Tavily: basic|advanced (optional)"},
        "chunks_per_source": {"type": "integer", "description": "Tavily: 1-3 (advanced only)"},
        "time_range": {"type": "string", "description": "Tavily: day|week|month|year (optional)"},
        "days": {"type": "integer", "description": "Tavily: days back (news only)"},
        "start_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "end_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "include_answer": {"type": "string", "description": "Tavily: false|basic|advanced (optional)"},
        "include_raw_content": {"type": "string", "description": "Tavily: false|markdown|text (optional)"},
        "include_images": {"type": "boolean", "description": "Tavily: include image results"},
        "include_image_descriptions": {"type": "boolean", "description": "Tavily: include image descriptions"},
        "include_favicon": {"type": "boolean", "description": "Tavily: include favicon URL"},
        "include_domains": {"type": "array", "description": "Tavily: include domains list"},
        "exclude_domains": {"type": "array", "description": "Tavily: exclude domains list"},
        "country": {"type": "string", "description": "Tavily: boost country (optional)"},
        "exact_match": {"type": "boolean", "description": "Tavily: exact match search"},
    },
)
def search(
    query: str,
    num_results: int = 5,
    provider: str = "ddg",
    auto_parameters: bool | None = None,
    topic: str | None = None,
    search_depth: str | None = None,
    chunks_per_source: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_answer: str | bool | None = None,
    include_raw_content: str | bool | None = None,
    include_images: bool | None = None,
    include_image_descriptions: bool | None = None,
    include_favicon: bool | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    exact_match: bool | None = None,
):
    if provider == "tavily":
        return _tavily_search(
            query,
            num_results=num_results,
            auto_parameters=auto_parameters,
            topic=topic,
            search_depth=search_depth,
            chunks_per_source=chunks_per_source,
            time_range=time_range,
            days=days,
            start_date=start_date,
            end_date=end_date,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_favicon=include_favicon,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            country=country,
            exact_match=exact_match,
        )
    q = quote_plus(query)
    html = _http_get(f"https://duckduckgo.com/html/?q={q}")
    return _extract_results_ddg(html, max(1, int(num_results)))


@tool(
    name="search_website",
    description="Search within a specific website domain.",
    params={
        "query": {"type": "string", "description": "Search query"},
        "site": {"type": "string", "description": "Domain or site (e.g. example.com)"},
        "num_results": {"type": "integer", "description": "Number of results (default 5)"},
        "provider": {"type": "string", "description": "Search provider: ddg or tavily (default ddg)"},
        "auto_parameters": {"type": "boolean", "description": "Tavily: auto-configure parameters (optional)"},
        "topic": {"type": "string", "description": "Tavily: general|news|finance (optional)"},
        "search_depth": {"type": "string", "description": "Tavily: basic|advanced (optional)"},
        "chunks_per_source": {"type": "integer", "description": "Tavily: 1-3 (advanced only)"},
        "time_range": {"type": "string", "description": "Tavily: day|week|month|year (optional)"},
        "days": {"type": "integer", "description": "Tavily: days back (news only)"},
        "start_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "end_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "include_answer": {"type": "string", "description": "Tavily: false|basic|advanced (optional)"},
        "include_raw_content": {"type": "string", "description": "Tavily: false|markdown|text (optional)"},
        "include_images": {"type": "boolean", "description": "Tavily: include image results"},
        "include_image_descriptions": {"type": "boolean", "description": "Tavily: include image descriptions"},
        "include_favicon": {"type": "boolean", "description": "Tavily: include favicon URL"},
        "include_domains": {"type": "array", "description": "Tavily: include domains list"},
        "exclude_domains": {"type": "array", "description": "Tavily: exclude domains list"},
        "country": {"type": "string", "description": "Tavily: boost country (optional)"},
        "exact_match": {"type": "boolean", "description": "Tavily: exact match search"},
    },
)
def search_website(
    query: str,
    site: str,
    num_results: int = 5,
    provider: str = "ddg",
    auto_parameters: bool | None = None,
    topic: str | None = None,
    search_depth: str | None = None,
    chunks_per_source: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_answer: str | bool | None = None,
    include_raw_content: str | bool | None = None,
    include_images: bool | None = None,
    include_image_descriptions: bool | None = None,
    include_favicon: bool | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    exact_match: bool | None = None,
):
    if provider == "tavily":
        domains = include_domains or [site]
        return search(
            query,
            num_results=num_results,
            provider=provider,
            auto_parameters=auto_parameters,
            topic=topic,
            search_depth=search_depth,
            chunks_per_source=chunks_per_source,
            time_range=time_range,
            days=days,
            start_date=start_date,
            end_date=end_date,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_favicon=include_favicon,
            include_domains=domains,
            exclude_domains=exclude_domains,
            country=country,
            exact_match=exact_match,
        )
    site_query = f"site:{site} {query}"
    return search(site_query, num_results=num_results, provider=provider)


@tool(
    name="get_content",
    description="Fetch a URL and return readable text.",
    params={
        "url": {"type": "string", "description": "URL to fetch"},
        "max_chars": {"type": "integer", "description": "Max characters to return (default 4000)"},
        "text_only": {"type": "boolean", "description": "Return only plain text (default true)"},
        "include_title": {"type": "boolean", "description": "Include page title"},
        "include_links": {"type": "boolean", "description": "Include links list"},
        "include_images": {"type": "boolean", "description": "Include image URLs"},
        "selector": {"type": "string", "description": "CSS selector to extract (optional)"},
        "user_agent": {"type": "string", "description": "Custom user-agent (optional)"},
    },
)
def get_content(
    url: str,
    max_chars: int = 4000,
    text_only: bool = True,
    include_title: bool = False,
    include_links: bool = False,
    include_images: bool = False,
    selector: str = "",
    user_agent: str = "",
):
    if requests is not None and user_agent:
        resp = requests.get(
            url, headers={"User-Agent": user_agent}, timeout=15
        )
        resp.raise_for_status()
        html = resp.text
    else:
        html = _http_get(url)

    title = ""
    links: list[str] = []
    images: list[str] = []

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        if selector:
            section = soup.select_one(selector)
            text = " ".join(section.stripped_strings) if section else ""
        else:
            text = " ".join(soup.stripped_strings)
        if include_title and soup.title and soup.title.string:
            title = soup.title.string.strip()
        if include_links:
            links = [a.get("href", "") for a in soup.find_all("a") if a.get("href")]
        if include_images:
            images = [img.get("src", "") for img in soup.find_all("img") if img.get("src")]
    else:
        import re
        text = re.sub("<script.*?>.*?</script>", " ", html, flags=re.S | re.I)
        text = re.sub("<style.*?>.*?</style>", " ", text, flags=re.S | re.I)
        text = re.sub("<[^>]+>", " ", text)
        text = " ".join(text.split())
    text = unescape(text)
    content = text[: max(0, int(max_chars))]

    if text_only and not (include_title or include_links or include_images):
        return content
    return {
        "title": title,
        "text": content,
        "links": links,
        "images": images,
    }


@tool(
    name="get_url_by_query",
    description="Search the web and return the first result URL.",
    params={
        "query": {"type": "string", "description": "Search query"},
        "provider": {"type": "string", "description": "Search provider: ddg or tavily (default ddg)"},
        "auto_parameters": {"type": "boolean", "description": "Tavily: auto-configure parameters (optional)"},
        "topic": {"type": "string", "description": "Tavily: general|news|finance (optional)"},
        "search_depth": {"type": "string", "description": "Tavily: basic|advanced (optional)"},
        "chunks_per_source": {"type": "integer", "description": "Tavily: 1-3 (advanced only)"},
        "time_range": {"type": "string", "description": "Tavily: day|week|month|year (optional)"},
        "days": {"type": "integer", "description": "Tavily: days back (news only)"},
        "start_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "end_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "include_answer": {"type": "string", "description": "Tavily: false|basic|advanced (optional)"},
        "include_raw_content": {"type": "string", "description": "Tavily: false|markdown|text (optional)"},
        "include_images": {"type": "boolean", "description": "Tavily: include image results"},
        "include_image_descriptions": {"type": "boolean", "description": "Tavily: include image descriptions"},
        "include_favicon": {"type": "boolean", "description": "Tavily: include favicon URL"},
        "include_domains": {"type": "array", "description": "Tavily: include domains list"},
        "exclude_domains": {"type": "array", "description": "Tavily: exclude domains list"},
        "country": {"type": "string", "description": "Tavily: boost country (optional)"},
        "exact_match": {"type": "boolean", "description": "Tavily: exact match search"},
    },
)
def get_url_by_query(
    query: str,
    provider: str = "ddg",
    auto_parameters: bool | None = None,
    topic: str | None = None,
    search_depth: str | None = None,
    chunks_per_source: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_answer: str | bool | None = None,
    include_raw_content: str | bool | None = None,
    include_images: bool | None = None,
    include_image_descriptions: bool | None = None,
    include_favicon: bool | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    exact_match: bool | None = None,
) -> str:
    results = search(
        query,
        num_results=1,
        provider=provider,
        auto_parameters=auto_parameters,
        topic=topic,
        search_depth=search_depth,
        chunks_per_source=chunks_per_source,
        time_range=time_range,
        days=days,
        start_date=start_date,
        end_date=end_date,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
        include_images=include_images,
        include_image_descriptions=include_image_descriptions,
        include_favicon=include_favicon,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        country=country,
        exact_match=exact_match,
    )
    if not results:
        return ""
    return results[0].get("url", "")


@tool(
    name="get_content_by_query",
    description="Search the web and return the content of the first result.",
    params={
        "query": {"type": "string", "description": "Search query"},
        "max_chars": {"type": "integer", "description": "Max characters to return (default 4000)"},
        "provider": {"type": "string", "description": "Search provider: ddg or tavily (default ddg)"},
        "auto_parameters": {"type": "boolean", "description": "Tavily: auto-configure parameters (optional)"},
        "topic": {"type": "string", "description": "Tavily: general|news|finance (optional)"},
        "search_depth": {"type": "string", "description": "Tavily: basic|advanced (optional)"},
        "chunks_per_source": {"type": "integer", "description": "Tavily: 1-3 (advanced only)"},
        "time_range": {"type": "string", "description": "Tavily: day|week|month|year (optional)"},
        "days": {"type": "integer", "description": "Tavily: days back (news only)"},
        "start_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "end_date": {"type": "string", "description": "Tavily: YYYY-MM-DD (optional)"},
        "include_answer": {"type": "string", "description": "Tavily: false|basic|advanced (optional)"},
        "include_raw_content": {"type": "string", "description": "Tavily: false|markdown|text (optional)"},
        "include_images": {"type": "boolean", "description": "Tavily: include image results"},
        "include_image_descriptions": {"type": "boolean", "description": "Tavily: include image descriptions"},
        "include_favicon": {"type": "boolean", "description": "Tavily: include favicon URL"},
        "include_domains": {"type": "array", "description": "Tavily: include domains list"},
        "exclude_domains": {"type": "array", "description": "Tavily: exclude domains list"},
        "country": {"type": "string", "description": "Tavily: boost country (optional)"},
        "exact_match": {"type": "boolean", "description": "Tavily: exact match search"},
        "text_only": {"type": "boolean", "description": "Normal web: return only plain text"},
        "include_title": {"type": "boolean", "description": "Normal web: include page title"},
        "include_links": {"type": "boolean", "description": "Normal web: include links list"},
        "include_images_web": {"type": "boolean", "description": "Normal web: include image URLs"},
        "selector": {"type": "string", "description": "Normal web: CSS selector to extract"},
        "user_agent": {"type": "string", "description": "Normal web: custom user-agent"},
    },
)
def get_content_by_query(
    query: str,
    max_chars: int = 4000,
    provider: str = "ddg",
    auto_parameters: bool | None = None,
    topic: str | None = None,
    search_depth: str | None = None,
    chunks_per_source: int | None = None,
    time_range: str | None = None,
    days: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    include_answer: str | bool | None = None,
    include_raw_content: str | bool | None = None,
    include_images: bool | None = None,
    include_image_descriptions: bool | None = None,
    include_favicon: bool | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    country: str | None = None,
    exact_match: bool | None = None,
    text_only: bool = True,
    include_title: bool = False,
    include_links: bool = False,
    include_images_web: bool = False,
    selector: str = "",
    user_agent: str = "",
) -> str:
    if provider == "tavily":
        results = _tavily_search(
            query,
            num_results=1,
            auto_parameters=auto_parameters,
            topic=topic,
            search_depth=search_depth,
            chunks_per_source=chunks_per_source,
            time_range=time_range,
            days=days,
            start_date=start_date,
            end_date=end_date,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            include_favicon=include_favicon,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            country=country,
            exact_match=exact_match,
        )
        if not results:
            return ""
        content = results[0].get("snippet", "")
        if content:
            return content[: max(0, int(max_chars))]
        url = results[0].get("url", "")
        return get_content(url, max_chars=max_chars) if url else ""
    url = get_url_by_query(
        query,
        provider=provider,
        auto_parameters=auto_parameters,
        topic=topic,
        search_depth=search_depth,
        chunks_per_source=chunks_per_source,
        time_range=time_range,
        days=days,
        start_date=start_date,
        end_date=end_date,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
        include_images=include_images,
        include_image_descriptions=include_image_descriptions,
        include_favicon=include_favicon,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        country=country,
        exact_match=exact_match,
    )
    if not url:
        return ""
    return get_content(
        url,
        max_chars=max_chars,
        text_only=text_only,
        include_title=include_title,
        include_links=include_links,
        include_images=include_images_web,
        selector=selector,
        user_agent=user_agent,
    )


@tool(
    name="get_links",
    description="Fetch a URL and return all links.",
    params={
        "url": {"type": "string"},
        "user_agent": {"type": "string", "description": "Custom user-agent (optional)"},
    },
)
def get_links(url: str, user_agent: str = ""):
    if user_agent and requests is not None:
        html = requests.get(url, headers={"User-Agent": user_agent}, timeout=15).text
    else:
        html = _http_get(url)
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    return [a.get("href", "") for a in soup.find_all("a") if a.get("href")]


@tool(
    name="get_images",
    description="Fetch a URL and return image URLs.",
    params={
        "url": {"type": "string"},
        "user_agent": {"type": "string", "description": "Custom user-agent (optional)"},
    },
)
def get_images(url: str, user_agent: str = ""):
    if user_agent and requests is not None:
        html = requests.get(url, headers={"User-Agent": user_agent}, timeout=15).text
    else:
        html = _http_get(url)
    if BeautifulSoup is None:
        return []
    soup = BeautifulSoup(html, "html.parser")
    return [img.get("src", "") for img in soup.find_all("img") if img.get("src")]


@tool(
    name="fetch_json",
    description="Fetch a URL and parse JSON response.",
    params={
        "url": {"type": "string"},
        "headers": {"type": "object", "description": "Headers (optional)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def fetch_json(url: str, headers: dict | None = None, timeout: int = 15):
    if requests is None:
        raise RuntimeError("requests not installed")
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


@tool(
    name="download_file",
    description="Download a URL to a local file.",
    params={
        "url": {"type": "string"},
        "out": {"type": "string"},
        "timeout": {"type": "integer", "description": "Timeout seconds (optional)"},
    },
)
def download_file(url: str, out: str, timeout: int = 30):
    if requests is None:
        raise RuntimeError("requests not installed")
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return str(outp.resolve())
