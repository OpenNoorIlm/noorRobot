from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.ytTranscript.ytTranscript")
logger.debug("Loaded tool module: ytTranscript.ytTranscript")

import re
from app.utils.groq import tool

try:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    from youtube_transcript_api.formatters import TextFormatter  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    YouTubeTranscriptApi = None
    TextFormatter = None


def _extract_video_id(video_id_or_url: str) -> str:
    if "youtube.com" in video_id_or_url or "youtu.be" in video_id_or_url:
        patterns = [
            r"v=([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"shorts/([A-Za-z0-9_-]{11})",
        ]
        for pat in patterns:
            m = re.search(pat, video_id_or_url)
            if m:
                return m.group(1)
    return video_id_or_url.strip()


def _require_lib():
    if YouTubeTranscriptApi is None:
        raise RuntimeError("youtube-transcript-api is not installed.")


@tool(
    name="yt_get_transcript",
    description="Get a YouTube transcript (list of segments).",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "languages": {"type": "array", "description": "Preferred languages list (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
        "preserve_formatting": {"type": "boolean", "description": "Preserve formatting (optional)"},
    },
)
def yt_get_transcript(
    video_id_or_url: str,
    languages: list[str] | None = None,
    proxies: dict | None = None,
    cookies: str | None = None,
    preserve_formatting: bool = False,
):
    _require_lib()
    vid = _extract_video_id(video_id_or_url)
    return YouTubeTranscriptApi.get_transcript(
        vid,
        languages=languages,
        proxies=proxies,
        cookies=cookies,
        preserve_formatting=preserve_formatting,
    )


@tool(
    name="yt_get_transcript_text",
    description="Get a YouTube transcript as plain text.",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "languages": {"type": "array", "description": "Preferred languages list (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
        "preserve_formatting": {"type": "boolean", "description": "Preserve formatting (optional)"},
    },
)
def yt_get_transcript_text(
    video_id_or_url: str,
    languages: list[str] | None = None,
    proxies: dict | None = None,
    cookies: str | None = None,
    preserve_formatting: bool = False,
) -> str:
    _require_lib()
    segments = yt_get_transcript(
        video_id_or_url,
        languages=languages,
        proxies=proxies,
        cookies=cookies,
        preserve_formatting=preserve_formatting,
    )
    if TextFormatter is None:
        return "\n".join([s.get("text", "") for s in segments])
    formatter = TextFormatter()
    return formatter.format_transcript(segments)


@tool(
    name="yt_list_transcripts",
    description="List available transcripts and languages for a video.",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
    },
)
def yt_list_transcripts(
    video_id_or_url: str,
    proxies: dict | None = None,
    cookies: str | None = None,
):
    _require_lib()
    vid = _extract_video_id(video_id_or_url)
    transcripts = YouTubeTranscriptApi.list_transcripts(
        vid, proxies=proxies, cookies=cookies
    )
    items = []
    for t in transcripts:
        items.append({
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
            "is_translatable": t.is_translatable,
        })
    return items


@tool(
    name="yt_get_transcript_by_language",
    description="Get transcript for a specific language (manual or generated).",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "language_code": {"type": "string", "description": "Language code, e.g. en"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
        "preserve_formatting": {"type": "boolean", "description": "Preserve formatting (optional)"},
    },
)
def yt_get_transcript_by_language(
    video_id_or_url: str,
    language_code: str,
    proxies: dict | None = None,
    cookies: str | None = None,
    preserve_formatting: bool = False,
):
    _require_lib()
    vid = _extract_video_id(video_id_or_url)
    transcripts = YouTubeTranscriptApi.list_transcripts(
        vid, proxies=proxies, cookies=cookies
    )
    t = transcripts.find_transcript([language_code])
    return t.fetch(preserve_formatting=preserve_formatting)


@tool(
    name="yt_translate_transcript",
    description="Translate a transcript to another language (if available).",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "language_code": {"type": "string", "description": "Target language code"},
        "source_language_code": {"type": "string", "description": "Source language code (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
        "preserve_formatting": {"type": "boolean", "description": "Preserve formatting (optional)"},
    },
)
def yt_translate_transcript(
    video_id_or_url: str,
    language_code: str,
    source_language_code: str = "",
    proxies: dict | None = None,
    cookies: str | None = None,
    preserve_formatting: bool = False,
):
    _require_lib()
    vid = _extract_video_id(video_id_or_url)
    transcripts = YouTubeTranscriptApi.list_transcripts(
        vid, proxies=proxies, cookies=cookies
    )
    if source_language_code:
        t = transcripts.find_transcript([source_language_code])
    else:
        t = transcripts.find_generated_transcript([t.language_code for t in transcripts])
    translated = t.translate(language_code)
    return translated.fetch(preserve_formatting=preserve_formatting)


@tool(
    name="yt_get_best_transcript",
    description="One-shot: get the best available transcript as plain text.",
    params={
        "video_id_or_url": {"type": "string", "description": "YouTube video ID or URL"},
        "languages": {"type": "array", "description": "Preferred languages list (optional)"},
        "target_language": {"type": "string", "description": "Auto-translate to this language if needed (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
        "preserve_formatting": {"type": "boolean", "description": "Preserve formatting (optional)"},
    },
)
def yt_get_best_transcript(
    video_id_or_url: str,
    languages: list[str] | None = None,
    target_language: str = "",
    proxies: dict | None = None,
    cookies: str | None = None,
    preserve_formatting: bool = False,
) -> str:
    _require_lib()
    try:
        return yt_get_transcript_text(
            video_id_or_url,
            languages=languages,
            proxies=proxies,
            cookies=cookies,
            preserve_formatting=preserve_formatting,
        )
    except Exception:
        # Fallback: first available transcript
        vid = _extract_video_id(video_id_or_url)
        transcripts = YouTubeTranscriptApi.list_transcripts(
            vid, proxies=proxies, cookies=cookies
        )
        if target_language:
            for t in transcripts:
                try:
                    translated = t.translate(target_language)
                    segments = translated.fetch(preserve_formatting=preserve_formatting)
                    if TextFormatter is None:
                        return "\n".join([s.get("text", "") for s in segments])
                    formatter = TextFormatter()
                    return formatter.format_transcript(segments)
                except Exception:
                    continue
        for t in transcripts:
            try:
                segments = t.fetch(preserve_formatting=preserve_formatting)
                if TextFormatter is None:
                    return "\n".join([s.get("text", "") for s in segments])
                formatter = TextFormatter()
                return formatter.format_transcript(segments)
            except Exception:
                continue
        raise RuntimeError("No transcript available for this video.")


@tool(
    name="yt_transcript_range",
    description="Get transcript segments within a time range (seconds).",
    params={
        "video_id_or_url": {"type": "string"},
        "start": {"type": "number", "description": "Start seconds"},
        "end": {"type": "number", "description": "End seconds"},
        "languages": {"type": "array", "description": "Preferred languages list (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
    },
)
def yt_transcript_range(
    video_id_or_url: str,
    start: float,
    end: float,
    languages: list[str] | None = None,
    proxies: dict | None = None,
    cookies: str | None = None,
):
    segments = yt_get_transcript(
        video_id_or_url,
        languages=languages,
        proxies=proxies,
        cookies=cookies,
        preserve_formatting=False,
    )
    out = []
    for s in segments:
        t = float(s.get("start", 0.0))
        if t >= float(start) and t <= float(end):
            out.append(s)
    return out


@tool(
    name="yt_transcript_search",
    description="Search transcript text for a keyword.",
    params={
        "video_id_or_url": {"type": "string"},
        "query": {"type": "string"},
        "languages": {"type": "array", "description": "Preferred languages list (optional)"},
        "proxies": {"type": "object", "description": "Proxies dict (optional)"},
        "cookies": {"type": "string", "description": "Cookies file path (optional)"},
    },
)
def yt_transcript_search(
    video_id_or_url: str,
    query: str,
    languages: list[str] | None = None,
    proxies: dict | None = None,
    cookies: str | None = None,
):
    q = query.lower()
    segments = yt_get_transcript(
        video_id_or_url,
        languages=languages,
        proxies=proxies,
        cookies=cookies,
        preserve_formatting=False,
    )
    return [s for s in segments if q in str(s.get("text", "")).lower()]
