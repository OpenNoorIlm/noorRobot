from __future__ import annotations

import argparse
import importlib.util
import logging
from pathlib import Path

from colorama import Fore, Style
from rich.logging import RichHandler

from app.services.api import run


def _import_toolsf():
    base = Path(__file__).resolve().parent / "app" / "toolsf"
    if not base.exists():
        logging.getLogger("NoorRobot.Run").warning("toolsf folder missing: %s", base)
        return
    for tool_file in base.glob("*/tool/*.py"):
        if tool_file.name.startswith("_"):
            continue
        mod_name = f"toolsf_{tool_file.parent.parent.name}_{tool_file.stem}"
        try:
            logging.getLogger("NoorRobot.Run").debug("Importing tool module: %s", tool_file)
            spec = importlib.util.spec_from_file_location(mod_name, tool_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
        except Exception as exc:
            logging.getLogger("NoorRobot.Run").exception("Failed to import %s: %s", tool_file, exc)


def _datasets_ready() -> bool:
    base = Path(__file__).resolve().parent / "app" / "database"
    q = base / "quran" / "quran_uthmani.json"
    h1 = base / "hadith" / "bukhari.json"
    h2 = base / "hadith" / "muslim.json"
    return q.exists() and h1.exists() and h2.exists()


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    log = logging.getLogger("NoorRobot.Run")
    log.info("%sNoorRobot starting...%s", Fore.CYAN, Style.RESET_ALL)

    parser = argparse.ArgumentParser(description="Run NoorRobot API server.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default 8000)")
    args = parser.parse_args()

    if not _datasets_ready():
        log.warning("%sIslamic datasets not found.%s", Fore.YELLOW, Style.RESET_ALL)
        log.warning("Run: python app/services/datasets_download.py")
    else:
        log.info("%sIslamic datasets found.%s", Fore.GREEN, Style.RESET_ALL)

    # Ensure all tools under app/toolsf are imported/registered
    _import_toolsf()

    log.info("Starting API on %s:%s", args.host, args.port)
    run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
