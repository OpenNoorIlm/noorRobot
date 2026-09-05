#!/usr/bin/env python3
"""
smart_start.py — Drop-in launcher that catches ModuleNotFoundError,
auto-installs the missing package, and retries until clean.

Usage:
    python smart_start.py           # runs start.sh + run.py
    python smart_start.py --dry-run # simulate without actually starting anything
"""

import subprocess
import sys
import re
import os
import time
import argparse
from datetime import datetime
from pathlib import Path

# ── Bootstrap: install our own display deps if missing ────────────────────────
def _bootstrap(pkg: str, import_as: str = None):
    import_as = import_as or pkg
    try:
        __import__(import_as)
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            stdout=subprocess.DEVNULL,
        )

_bootstrap("rich")
_bootstrap("tqdm")
_bootstrap("tabulate")

# ── Imports (safe after bootstrap) ────────────────────────────────────────────
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from tqdm import tqdm
import tabulate as _tabulate_mod  # noqa – just ensuring it's available

console = Console()

# ── Config ────────────────────────────────────────────────────────────────────
MAX_RETRIES = 20  # give up after this many install attempts

# Known package → pip-name mapping (add more as you hit them)
MODULE_TO_PKG = {
    "jwt":          "PyJWT",
    "passlib":      "passlib",
    "fastapi":      "fastapi",
    "uvicorn":      "uvicorn",
    "pydantic":     "pydantic",
    "dotenv":       "python-dotenv",
    "sklearn":      "scikit-learn",
    "cv2":          "opencv-python",
    "PIL":          "Pillow",
    "bs4":          "beautifulsoup4",
    "yaml":         "PyYAML",
    "multipart":    "python-multipart",
    "python-multipart": "python-multipart",
}

LOG_FILE = Path(__file__).parent / "smart_start.log"

# ── Helpers ───────────────────────────────────────────────────────────────────
install_log: list[dict] = []   # [{module, pkg, status, ts}]

def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def log_write(msg: str):
    with LOG_FILE.open("a") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")

def extract_missing_module(output: str) -> str | None:
    """
    Parse missing package from output. Handles:
      - ModuleNotFoundError: No module named 'jwt'
      - RuntimeError + pip install hint: pip install python-multipart
    """
    # Standard import error
    m = re.search(r"ModuleNotFoundError: No module named '([^']+)'", output)
    if m:
        return m.group(1).split(".")[0]
    # pip install hint anywhere in output (catches RuntimeError cases)
    m = re.search(r"pip install ([\w\-]+)", output)
    if m:
        pkg = m.group(1)
        # Return the pip package name directly (will be used as-is)
        return pkg
    return None

def pip_install_name(module: str) -> str:
    """For pip-hint matches the module IS already the pip name."""
    return MODULE_TO_PKG.get(module, module)

def pip_name(module: str) -> str:
    return MODULE_TO_PKG.get(module, module)  # kept for compat

def install_package(module: str) -> bool:
    pkg = pip_name(module)
    label = f"module [cyan]{module}[/cyan]" if pkg != module else f"[cyan]{pkg}[/cyan]"
    console.print(f"  [yellow]⬇  Installing[/yellow] [bold]{pkg}[/bold] ({label}) …")
    log_write(f"Installing {pkg} for missing module {module}")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", pkg, "-q"],
        capture_output=True, text=True
    )
    ok = result.returncode == 0
    install_log.append({
        "module":  module,
        "package": pkg,
        "status":  "✅ ok" if ok else "❌ fail",
        "time":    ts(),
    })
    if not ok:
        console.print(f"  [red]  pip error:[/red] {result.stderr.strip()[:200]}")
        log_write(f"pip FAILED for {pkg}: {result.stderr.strip()}")
    else:
        log_write(f"pip OK for {pkg}")
    return ok

def run_start_sh() -> tuple[int, str]:
    """
    Run start.sh with stdout+stderr merged and piped through us line by line.
    Kills the whole process group the moment a ModuleNotFoundError line appears.
    Returns (returncode, all_output_so_far).
    """
    sh = Path(__file__).parent / "start.sh"
    proc = subprocess.Popen(
        ["bash", str(sh)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # merge stderr into stdout
        text=True,
        preexec_fn=os.setsid,       # new process group so we can kill bash + children
    )
    lines: list[str] = []
    console.print("[dim]── start.sh ──[/dim]")
    try:
        for line in proc.stdout:
            line = line.rstrip()
            lines.append(line)
            console.print(f"  [dim]{line}[/dim]")
            log_write(f"  {line}")
            if "ModuleNotFoundError: No module named" in line or "pip install " in line:
                try:
                    os.killpg(os.getpgid(proc.pid), 9)
                except Exception:
                    proc.kill()
                break
    except Exception as e:
        log_write(f"run_start_sh exception: {e}")
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            proc.kill()
    proc.wait()
    return proc.returncode, "\n".join(lines)

def print_install_table():
    if not install_log:
        return
    table = Table(
        title="Auto-Install Log",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("Time",    style="dim",       width=10)
    table.add_column("Module",  style="cyan",      width=20)
    table.add_column("Package", style="yellow",    width=22)
    table.add_column("Result",  justify="center",  width=10)

    for row in install_log:
        table.add_row(row["time"], row["module"], row["package"], row["status"])
    console.print(table)

def print_banner():
    console.print(Panel(
        Text("NoorRobot  Smart Launcher", justify="center", style="bold white"),
        subtitle="[dim]auto-heal on ModuleNotFoundError[/dim]",
        border_style="bright_blue",
    ))

# ── (Pipelines is launched by start.sh — no separate launcher needed) ───────

# ── Main retry loop ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen, don't run")
    args = parser.parse_args()

    print_banner()
    LOG_FILE.write_text("")  # reset log each run
    log_write("=== smart_start.py begin ===")

    already_installed: set[str] = set()

    pbar = tqdm(
        total=MAX_RETRIES,
        desc="Attempt 1",
        bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}]",
        colour="cyan",
        file=sys.stdout,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        pbar.set_description(f"Attempt {attempt}")

        if args.dry_run:
            console.print("[dim][DRY-RUN] Would run start.sh here[/dim]")
            break

        rc, output = run_start_sh()

        # No error at all — clean boot
        if rc == 0 and "ModuleNotFoundError" not in output:
            pbar.close()
            console.print(f"\n[bold green]✔ start.sh completed cleanly on attempt {attempt}![/bold green]")
            log_write(f"Clean start on attempt {attempt}")
            break

        missing = extract_missing_module(output)

        if missing is None:
            pbar.close()
            console.print("\n[red bold]✘ Non-import error — cannot auto-fix:[/red bold]")
            console.print(output[-800:])
            log_write(f"Non-import error:\n{output[-800:]}")
            break

        if missing in already_installed:
            pbar.close()
            console.print(f"\n[red]✘ Already tried installing '{missing}' — pip install didn't fix it.[/red]")
            console.print("[dim]Check smart_start.log for details.[/dim]")
            log_write(f"Re-encountered '{missing}' after install — giving up")
            break

        console.print(f"\n[dim][attempt {attempt}][/dim] Missing module: [cyan bold]{missing}[/cyan bold]")
        ok = install_package(missing)
        already_installed.add(missing)

        if not ok:
            pbar.close()
            console.print("[red]✘ Install failed. Stopping.[/red]")
            break

        pbar.update(1)
        time.sleep(0.3)
    else:
        pbar.close()
        console.print(f"[red]✘ Gave up after {MAX_RETRIES} attempts.[/red]")
        log_write(f"Gave up after {MAX_RETRIES} attempts")

    print_install_table()
    console.print(f"\n[dim]Full log → {LOG_FILE}[/dim]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)
