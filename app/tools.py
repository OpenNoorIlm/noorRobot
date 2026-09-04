from pathlib import Path
from app.utils.groq import tool, FUNCTIONS, TOOLS
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


def _tool_matches(query: str = ""):
    terms = {term for term in query.lower().replace("_", " ").split() if len(term) > 1}
    matches = []
    descriptions = {
        item.get("function", {}).get("name", ""): item.get("function", {}).get("description", "")
        for item in TOOLS
    }
    for schema in FUNCTIONS:
        text = (schema + " " + descriptions.get(schema, "")).lower().replace("_", " ")
        if not terms or any(term in text for term in terms):
            matches.append(schema)
    return sorted(matches)


@tool(
    name="list_tools",
    description="List registered NoorRobot tools matching an optional query. Use query 'all' to list every tool.",
    params={
        "query": {"type": "string", "description": "Topic or tool name, or 'all'"},
        "limit": {"type": "integer", "description": "Maximum names to return"},
    },
)
def list_tools(query: str = "", limit: int = 40):
    names = _tool_matches("" if query.strip().lower() == "all" else query)
    return names[:max(1, min(int(limit), len(names) or 1))]


@tool(
    name="load_tools",
    description="Find tools for a task and return the matching tool names. Call this before using a specialized tool that is not currently visible.",
    params={
        "query": {"type": "string", "description": "Task or category, such as email, ESP32, ringtone, calendar, or files"},
        "limit": {"type": "integer", "description": "Maximum names to return"},
    },
)
def load_tools(query: str, limit: int = 40):
    return {"query": query, "tools": _tool_matches(query)[:max(1, min(int(limit), 80))]}
