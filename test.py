from __future__ import annotations

from pathlib import Path
import logging

from rich.logging import RichHandler
from tabulate import tabulate

from app.utils import groq as groq_utils
from app.utils.vectorStore import vector_store


def _dataset_paths():
    base = Path(__file__).resolve().parent / "app" / "database"
    return {
        "quran": base / "quran" / "quran_uthmani.json",
        "kanzul": base / "quran" / "kanzul_iman.json",
        "jalalayn": base / "quran" / "tafsir_jalalayn.json",
        "bukhari": base / "hadith" / "bukhari.json",
        "muslim": base / "hadith" / "muslim.json",
    }


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    log = logging.getLogger("NoorRobot.Test")
    print("[test] Loading vector store...")
    try:
        vector_store.load_or_build()
        log.info("vector_store ok")
    except Exception as exc:
        log.exception("vector_store failed: %s", exc)

    tools = sorted(groq_utils.FUNCTIONS.keys())
    log.info("tools count: %s", len(tools))
    if tools:
        table = [[t] for t in tools]
        print(tabulate(table, headers=["Tool Name"]))

    # Dataset presence
    paths = _dataset_paths()
    for k, p in paths.items():
        log.info("%s dataset: %s", k, "OK" if p.exists() else "MISSING")

    # Spot-check local Quran/Hadith tools if available
    if "quran_get_ayah" in groq_utils.FUNCTIONS and paths["quran"].exists():
        q = groq_utils.FUNCTIONS["quran_get_ayah"](1, 1)
        log.info("quran_get_ayah(1,1): %s", (q.get("text") or "")[:60])

    if "hadith_collections" in groq_utils.FUNCTIONS:
        cols = groq_utils.FUNCTIONS["hadith_collections"]()
        log.info("hadith_collections: %s", cols)

    log.info("done")


if __name__ == "__main__":
    main()
