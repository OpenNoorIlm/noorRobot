from __future__ import annotations

from utils.groq import tool

try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None


def _get_engine():
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 is not installed. Install it to enable speech.")
    return pyttsx3.init()


@tool(
    name="list_voices",
    description="List available TTS voices.",
    params={}
)
def list_voices():
    engine = _get_engine()
    voices = engine.getProperty("voices") or []
    result = []
    for v in voices:
        result.append({
            "id": getattr(v, "id", ""),
            "name": getattr(v, "name", ""),
            "languages": [str(x) for x in getattr(v, "languages", []) or []],
        })
    return result


@tool(
    name="speak",
    description="Speak text using an optional voice id.",
    params={
        "text": {"type": "string", "description": "Text to speak"},
        "voice_id": {"type": "string", "description": "Voice id from list_voices (optional)"},
        "rate": {"type": "integer", "description": "Speech rate (optional)"},
        "volume": {"type": "number", "description": "Volume 0.0 to 1.0 (optional)"},
    }
)
def speak(text: str, voice_id: str = "", rate: int | None = None, volume: float | None = None) -> str:
    engine = _get_engine()
    if voice_id:
        for v in engine.getProperty("voices") or []:
            if getattr(v, "id", "") == voice_id or getattr(v, "name", "") == voice_id:
                engine.setProperty("voice", v.id)
                break
    if rate is not None:
        engine.setProperty("rate", int(rate))
    if volume is not None:
        engine.setProperty("volume", float(volume))
    engine.say(text)
    engine.runAndWait()
    return "ok"
