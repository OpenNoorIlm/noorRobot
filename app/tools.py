from pathlib import Path
from app.utils.groq import tool
from app.utils.face_memory import list_faces, recognize_face, save_face

BASE_DIR = Path(__file__).resolve().parent
UTILS_DIR = BASE_DIR / "utils"
TOOLSF_DIR = BASE_DIR / "toolsf"


@tool("save_face_memory", "Save a face image as a privacy-preserving hash; the image itself is never stored.", {
    "label": {"type": "string", "description": "Person label", "required": True},
    "image": {"type": "string", "description": "Local image path or base64 data URL", "required": True},
})
def save_face_memory(label: str, image: str):
    return save_face(label, image)


@tool("recognize_face_memory", "Recognize a face from privacy-preserving stored fingerprints.", {
    "image": {"type": "string", "description": "Local image path or base64 data URL", "required": True},
})
def recognize_face_memory(image: str):
    return recognize_face(image)


@tool("list_face_memory", "List known face labels without image data.", {})
def list_face_memory():
    return list_faces()


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
