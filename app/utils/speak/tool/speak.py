from __future__ import annotations
import os, tempfile, subprocess, struct, wave, requests
from utils.groq import tool

# ── Config ────────────────────────────────────────────────────────────────────
# Set ESP32_AUDIO_URL to your robot's IP, e.g. http://10.162.87.118
# Falls back to laptop speaker (pyttsx3) if not set or unreachable
ESP32_AUDIO_URL = os.environ.get("ESP32_AUDIO_URL", "")

try:
    import pyttsx3
except Exception:
    pyttsx3 = None


def _get_engine():
    if pyttsx3 is None:
        raise RuntimeError("pyttsx3 not installed")
    return pyttsx3.init()


def _tts_to_wav(text: str, voice_id: str = "", rate: int = 150, volume: float = 1.0) -> str:
    """Synthesize text to a temp WAV file using espeak (preferred) or pyttsx3."""
    tmp = tempfile.mktemp(suffix=".wav")

    # Try espeak first — it's headless and produces a file directly
    try:
        cmd = ["espeak", "-w", tmp, "--stdout"]
        # rate: espeak default 175 wpm
        cmd = ["espeak", f"-s{rate}", "-w", tmp, text]
        subprocess.run(cmd, check=True, capture_output=True)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            return tmp
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Fallback: pyttsx3 save to file
    if pyttsx3 is not None:
        engine = _get_engine()
        if voice_id:
            for v in engine.getProperty("voices") or []:
                if getattr(v, "id", "") == voice_id or getattr(v, "name", "") == voice_id:
                    engine.setProperty("voice", v.id)
                    break
        engine.setProperty("rate", int(rate))
        engine.setProperty("volume", float(volume))
        engine.save_to_file(text, tmp)
        engine.runAndWait()
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            return tmp

    raise RuntimeError("No TTS engine available (espeak or pyttsx3 required)")


def _convert_for_esp32(wav_in: str) -> str:
    """Convert WAV to 8kHz mono u8 PCM WAV for ESP32 DAC."""
    tmp = tempfile.mktemp(suffix="_esp32.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_in,
        "-ar", "8000", "-ac", "1", "-acodec", "pcm_u8",
        "-af", "loudnorm=I=-9:TP=-1:LRA=7,acompressor=threshold=-6dB:ratio=3:attack=5:release=50",
        tmp
    ], check=True, capture_output=True)
    return tmp


def _send_to_esp32(wav_path: str, url: str) -> bool:
    """Upload WAV to ESP32 audio player and trigger playback."""
    try:
        with open(wav_path, "rb") as f:
            r = requests.post(
                url.rstrip("/") + "/upload",
                files={"audio": ("speech.wav", f, "audio/wav")},
                timeout=10
            )
        return r.status_code == 200
    except Exception as e:
        print(f"[speak] ESP32 send failed: {e}")
        return False


@tool(
    name="list_voices",
    description="List available TTS voices.",
    params={}
)
def list_voices():
    engine = _get_engine()
    voices = engine.getProperty("voices") or []
    return [{"id": getattr(v,"id",""), "name": getattr(v,"name",""),
             "languages": [str(x) for x in getattr(v,"languages",[]) or []]}
            for v in voices]


@tool(
    name="speak",
    description="Speak text. If ESP32_AUDIO_URL is set, plays through the robot's PAM8403 speaker. Otherwise uses laptop speaker.",
    params={
        "text":     {"type": "string",  "description": "Text to speak"},
        "voice_id": {"type": "string",  "description": "Voice id from list_voices (optional)"},
        "rate":     {"type": "integer", "description": "Speech rate wpm (optional, default 150)"},
        "volume":   {"type": "number",  "description": "Volume 0.0 to 1.0 (optional)"},
        "use_robot":{"type": "boolean", "description": "Force robot speaker (True) or laptop (False). Default: auto"},
    }
)
def speak(text: str, voice_id: str = "", rate: int = 150,
          volume: float = 1.0, use_robot: bool | None = None) -> str:

    prefer_robot = use_robot if use_robot is not None else bool(ESP32_AUDIO_URL)

    if prefer_robot and ESP32_AUDIO_URL:
        # TTS → WAV → convert → send to ESP32
        try:
            raw_wav  = _tts_to_wav(text, voice_id, rate, volume)
            esp32wav = _convert_for_esp32(raw_wav)
            ok = _send_to_esp32(esp32wav, ESP32_AUDIO_URL)
            # cleanup
            for f in [raw_wav, esp32wav]:
                try: os.remove(f)
                except: pass
            if ok:
                return "ok (robot speaker)"
            # fall through to laptop
        except Exception as e:
            print(f"[speak] Robot path failed ({e}), falling back to laptop")

    # Laptop speaker fallback
    engine = _get_engine()
    if voice_id:
        for v in engine.getProperty("voices") or []:
            if getattr(v,"id","") == voice_id or getattr(v,"name","") == voice_id:
                engine.setProperty("voice", v.id)
                break
    engine.setProperty("rate", int(rate))
    engine.setProperty("volume", float(volume))
    engine.say(text)
    engine.runAndWait()
    return "ok (laptop speaker)"
