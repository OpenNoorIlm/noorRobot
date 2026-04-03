from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from typing import Iterable

import requests


logger = logging.getLogger("NoorRobot.Datasets")

BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "database"
QURAN_DIR = DB_DIR / "quran"
HADITH_DIR = DB_DIR / "hadith"

QURAN_TEXT_URLS = [
    os.getenv("QURAN_TEXT_URL", ""),
    "https://cdn.jsdelivr.net/npm/quran-json@3.1.2/dist/quran.json",
]

KANZUL_IMAN_URL = os.getenv("KANZUL_IMAN_URL", "https://tanzil.net/trans/en.ahmedraza")
JALALAYN_URL = os.getenv("JALALAYN_URL", "https://tanzil.net/trans/ar.jalalayn")

HADITH_DATASET = os.getenv("HADITH_DATASET", "freococo/sunnah_dataset")


def _download_text(urls: Iterable[str]) -> str:
    last_err = None
    for url in urls:
        if not url:
            continue
        try:
            logger.info("Downloading: %s", url)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning("Failed download %s: %s", url, exc)
            last_err = exc
    raise RuntimeError(f"Failed to download text from URLs. Last error: {last_err}")


def _parse_tanzil(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        surah, ayah, content = parts[0].strip(), parts[1].strip(), "|".join(parts[2:]).strip()
        rows.append({"surah": int(surah), "ayah": int(ayah), "text": content})
    return rows


def _flatten_quran_json(data) -> list[dict]:
    rows: list[dict] = []
    if isinstance(data, list):
        for i, surah in enumerate(data, start=1):
            surah_num = int(surah.get("id") or surah.get("number") or i)
            verses = surah.get("verses") or surah.get("ayahs") or []
            for j, v in enumerate(verses, start=1):
                if isinstance(v, dict):
                    text = v.get("text") or v.get("text_uthmani") or v.get("verse") or ""
                    ayah_num = int(v.get("id") or v.get("number") or j)
                else:
                    text = str(v)
                    ayah_num = j
                rows.append({"surah": surah_num, "ayah": ayah_num, "text": text})
    return rows


def download_quran():
    QURAN_DIR.mkdir(parents=True, exist_ok=True)

    # Quran Arabic (Uthmani)
    quran_text = _download_text(QURAN_TEXT_URLS)
    try:
        quran_json = json.loads(quran_text)
        quran_rows = _flatten_quran_json(quran_json)
        if not quran_rows:
            raise ValueError("Empty quran json")
    except Exception:
        # Fallback to Tanzil format if JSON parsing fails
        quran_rows = _parse_tanzil(quran_text)
    (QURAN_DIR / "quran_uthmani.json").write_text(json.dumps(quran_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved quran_uthmani.json (%d)", len(quran_rows))

    # Kanzul Iman (Ahmed Raza Khan)
    kanzul_text = _download_text([KANZUL_IMAN_URL])
    kanzul_rows = _parse_tanzil(kanzul_text)
    (QURAN_DIR / "kanzul_iman.json").write_text(json.dumps(kanzul_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved kanzul_iman.json (%d)", len(kanzul_rows))

    # Tafsir Jalalayn
    jalalayn_text = _download_text([JALALAYN_URL])
    jalalayn_rows = _parse_tanzil(jalalayn_text)
    (QURAN_DIR / "tafsir_jalalayn.json").write_text(json.dumps(jalalayn_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved tafsir_jalalayn.json (%d)", len(jalalayn_rows))

    return {
        "quran_uthmani": len(quran_rows),
        "kanzul_iman": len(kanzul_rows),
        "tafsir_jalalayn": len(jalalayn_rows),
    }


def download_hadith():
    HADITH_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from datasets import load_dataset  # type: ignore
    except Exception as exc:
        raise RuntimeError("datasets library not installed. Add `datasets` to requirements.txt") from exc

    logger.info("Loading dataset: %s", HADITH_DATASET)
    ds = load_dataset(HADITH_DATASET, split="train")

    def _filter(name: str):
        out = []
        for row in ds:
            coll = str(row.get("collection", "")).lower()
            if name in coll:
                out.append({
                    "collection": row.get("collection"),
                    "hadith_id": row.get("hadith_id"),
                    "hadith_no_in_book": row.get("hadith_no_in_book") or row.get("hadith_no") or row.get("number"),
                    "book_no": row.get("book_no") or row.get("book_number"),
                    "book_en": row.get("book_en") or row.get("book"),
                    "chapter_no": row.get("chapter_no") or row.get("chapter_number"),
                    "arabic_full": row.get("arabic_full") or row.get("text_ar"),
                    "english_full": row.get("english_full") or row.get("text_en"),
                    "grade": row.get("grade") or row.get("gradings"),
                    "source_url": row.get("url"),
                })
        return out

    bukhari = _filter("bukhari")
    muslim = _filter("muslim")

    (HADITH_DIR / "bukhari.json").write_text(json.dumps(bukhari, ensure_ascii=False, indent=2), encoding="utf-8")
    (HADITH_DIR / "muslim.json").write_text(json.dumps(muslim, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved bukhari.json (%d)", len(bukhari))
    logger.info("Saved muslim.json (%d)", len(muslim))

    return {"bukhari": len(bukhari), "muslim": len(muslim)}


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    DB_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"quran": {}, "hadith": {}}
    meta["quran"] = download_quran()
    meta["hadith"] = download_hadith()
    (DB_DIR / "islamic_datasets.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Download complete:", meta)


if __name__ == "__main__":
    main()
