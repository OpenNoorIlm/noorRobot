from pathlib import Path
from app.utils.groq import tool

BASE_DIR = Path(__file__).resolve().parent
UTILS_DIR = BASE_DIR / "utils"
TOOLSF_DIR = BASE_DIR / "toolsf"


@tool(
    name="list_tools",
    description="List available tool modules.",
    params={}
)
def list_tools():
    if not UTILS_DIR.exists() and not TOOLSF_DIR.exists():
        raise FileNotFoundError(
            f"Tools directories not found: {UTILS_DIR} and {TOOLSF_DIR}"
        )
    tool_files = []
    if UTILS_DIR.exists():
        tool_files.extend(UTILS_DIR.glob("*/tool/*.py"))
    if TOOLSF_DIR.exists():
        tool_files.extend(TOOLSF_DIR.glob("*/tool/*.py"))
    return sorted(
        [p.stem for p in tool_files if p.is_file() and not p.name.startswith("_")]
    )
