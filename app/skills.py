from pathlib import Path
from app.utils.groq import tool

BASE_DIR = Path(__file__).resolve().parent
UTILS_DIR = BASE_DIR / "utils"
TOOLSF_DIR = BASE_DIR / "toolsf"


@tool(
    name="list_skills",
    description="List available tool skill directories.",
    params={}
)
def list_skills():
    if not UTILS_DIR.exists() and not TOOLSF_DIR.exists():
        raise FileNotFoundError(
            f"Skill directories not found: {UTILS_DIR} and {TOOLSF_DIR}"
        )
    skills = []
    if UTILS_DIR.exists():
        skills.extend([p.name for p in UTILS_DIR.iterdir() if p.is_dir()])
    if TOOLSF_DIR.exists():
        skills.extend([p.name for p in TOOLSF_DIR.iterdir() if p.is_dir()])
    return sorted(set(skills))


@tool(
    name="list_skill",
    description="List available tool skill directories (alias of list_skills).",
    params={}
)
def list_skill():
    return list_skills()


@tool(
    name="get_skill",
    description="Get the contents of a skill .skill file by name.",
    params={"name": {"type": "string", "description": "Skill name"}}
)
def get_skill(name: str) -> str:
    if not UTILS_DIR.exists() and not TOOLSF_DIR.exists():
        raise FileNotFoundError(
            f"Skill directories not found: {UTILS_DIR} and {TOOLSF_DIR}"
        )
    candidates = [
        UTILS_DIR / name / "skill" / f"{name}.skill",
        TOOLSF_DIR / name / "skill" / f"{name}.skill",
    ]
    for skill_path in candidates:
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Skill file not found for: {name}")
