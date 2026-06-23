"""
╔══════════════════════════════════════════════════════════════════╗
║        visioning_tools.py  —  ESP32-CAM Vision Tool Layer       ║
║   Wraps visioning.py (YOLOv8 cinematic detector) as @tool calls ║
║   so the robot agent can start/stop/query the vision pipeline.  ║
╚══════════════════════════════════════════════════════════════════╝

Depends on:
    visioning.py (same directory)
    pip install ultralytics opencv-python numpy torch torchvision

The detector runs in a background thread.  Tools allow the agent to
start and stop it, query which objects are currently visible, move
the camera to a target angle before a scan, and save a snapshot.
"""

import threading
import time
import queue
import base64
import cv2
import numpy as np

from app.utils.groq import tool

# ── shared reference to the running detector session ──────────────────────────
_session_lock = threading.Lock()
_session: "DetectorSession | None" = None

ESP32_CAM_HOST = "10.162.128.94"
DEFAULT_PORT   = 8082
DEFAULT_MODEL  = "yolov26x.onnx"


# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL: thin DetectorSession that reuses visioning.py classes
# ══════════════════════════════════════════════════════════════════════════════
class DetectorSession:
    """Runs StreamReader + InferenceWorker + SmoothTracker in background."""

    def __init__(self, ip: str, port: int, model: str, alpha: float):
        # Import from visioning.py living in the same package / directory
        from visioning import (
            StreamReader, InferenceWorker, SmoothTracker, DEVICE,
        )

        self.stream_url = f"http://{ip}:{port}/stream"
        self.result_q   = queue.Queue(maxsize=2)
        self.reader     = StreamReader(self.stream_url)
        self.worker     = InferenceWorker(model, DEVICE, self.result_q)
        self.tracker    = SmoothTracker(alpha=alpha)
        self._current_tracks: list = []
        self._tracks_lock = threading.Lock()
        self._stop_flag   = False
        self._merge_thread: threading.Thread | None = None

    def start(self) -> str:
        self.reader.start()
        self.worker.start()

        # Wait up to 5 s for the first frame
        for _ in range(50):
            if self.reader.ok:
                break
            time.sleep(0.1)
        if not self.reader.ok:
            return f"error: cannot reach {self.stream_url}"

        # Background thread: drain result_q and keep tracker fresh
        self._merge_thread = threading.Thread(target=self._merge_loop, daemon=True)
        self._merge_thread.start()
        return f"ok: connected to {self.stream_url}"

    def _merge_loop(self):
        while not self._stop_flag:
            frame = self.reader.latest()
            if frame is not None:
                self.worker.submit(frame)
            try:
                dets = self.result_q.get(timeout=0.05)
                self.tracker.update(dets)
                with self._tracks_lock:
                    self._current_tracks = self.tracker.get()
            except queue.Empty:
                pass

    def stop(self):
        self._stop_flag = True
        self.worker.stop()

    def get_tracks(self) -> list:
        with self._tracks_lock:
            return list(self._current_tracks)

    def grab_jpeg(self) -> bytes | None:
        """Grab the latest frame and encode as JPEG bytes."""
        frame = self.reader.latest()
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return bytes(buf) if ok else None


# ══════════════════════════════════════════════════════════════════════════════
#  TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@tool(
    name="start_vision",
    description=(
        "Start the YOLOv8 cinematic object-detection pipeline on the ESP32-CAM "
        "MJPEG stream. Must be called before any other vision tools. "
        "Returns 'ok' on success or an error string."
    ),
    params={
        "ip":    {"type": "string",  "description": "ESP32-CAM IP address. Defaults to the robot's camera host."},
        "port":  {"type": "integer", "description": "MJPEG stream port. Default 8082."},
        "model": {"type": "string",  "description": "YOLOv8 model variant: yolov8n / yolov8s / yolov8m / yolov8l / yolov8x, or a path to a .pt / .onnx file. Default yolov8n."},
        "alpha": {"type": "number",  "description": "Box-smoothing factor 0.1 (very smooth) – 1.0 (instant). Default 0.45."},
    },
)
def startVision(
    ip: str    = ESP32_CAM_HOST,
    port: int  = DEFAULT_PORT,
    model: str = DEFAULT_MODEL,
    alpha: float = 0.45,
) -> str:
    global _session
    with _session_lock:
        if _session is not None:
            return "vision already running — call stop_vision first if you want to restart"
        sess = DetectorSession(ip, port, model, alpha)
        result = sess.start()
        if result.startswith("error"):
            return result
        _session = sess
    return result


@tool(
    name="stop_vision",
    description="Stop the running YOLOv8 detection pipeline and free resources.",
    params={},
)
def stopVision() -> str:
    global _session
    with _session_lock:
        if _session is None:
            return "vision is not running"
        _session.stop()
        _session = None
    return "ok: vision stopped"


@tool(
    name="get_detected_objects",
    description=(
        "Return the list of objects currently detected in the camera frame. "
        "Each entry contains the object class name, confidence score, and "
        "bounding-box centre coordinates (cx, cy) as pixel fractions 0–1. "
        "start_vision must have been called first."
    ),
    params={},
)
def getDetectedObjects() -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "error: vision not running — call start_vision first"

    tracks = sess.get_tracks()
    if not tracks:
        return "no objects detected"

    lines = []
    for tid, x1, y1, x2, y2, conf, name, _trail in tracks:
        # Compute centre as fraction of unknown frame size — still useful
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        lines.append(
            f"  id={tid}  class={name}  conf={conf:.0%}  "
            f"box=({x1},{y1})-({x2},{y2})  centre=({cx:.0f},{cy:.0f}px)"
        )
    return f"{len(lines)} object(s) detected:\n" + "\n".join(lines)


@tool(
    name="is_object_visible",
    description=(
        "Check whether a specific object class is currently visible in the "
        "camera frame. Returns the count and details, or 'not visible'. "
        "start_vision must have been called first."
    ),
    params={
        "class_name": {
            "type": "string",
            "description": "COCO class name to look for, e.g. 'person', 'cat', 'bottle'.",
        },
    },
)
def isObjectVisible(class_name: str) -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "error: vision not running — call start_vision first"

    matches = [
        t for t in sess.get_tracks()
        if t[6].lower() == class_name.lower()
    ]
    if not matches:
        return f"'{class_name}' not visible"

    lines = []
    for tid, x1, y1, x2, y2, conf, name, _trail in matches:
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        lines.append(f"  id={tid}  conf={conf:.0%}  centre=({cx:.0f},{cy:.0f}px)")
    return f"'{class_name}' visible × {len(matches)}:\n" + "\n".join(lines)


@tool(
    name="scan_objects_at_angle",
    description=(
        "Move the camera pan/tilt servos to the requested angles, wait for the "
        "scene to settle, then return a snapshot of detected objects at that angle. "
        "Combines move_camera + get_detected_objects in one call."
    ),
    params={
        "angleX": {"type": "integer", "description": "Horizontal pan angle 0–180 (90 = centre)."},
        "angleY": {"type": "integer", "description": "Vertical tilt angle 0–180 (90 = centre)."},
        "settle_ms": {
            "type": "integer",
            "description": "Milliseconds to wait after moving before reading detections. Default 600.",
        },
    },
)
def scanObjectsAtAngle(angleX: int = 90, angleY: int = 90, settle_ms: int = 600) -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "error: vision not running — call start_vision first"

    # Reuse the move_camera HTTP call from body.py-style raw socket
    import socket
    from urllib.parse import quote
    host = ESP32_CAM_HOST
    port = 2674       # ESP32-CAM legacy port for servo control
    q = quote(f"{angleX},{angleY}", safe=",")
    path = f"/move_camera?q={q}"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
        s.recv(256)
        s.close()
    except Exception as e:
        return f"error moving camera: {e}"

    time.sleep(settle_ms / 1000.0)
    return getDetectedObjects()


@tool(
    name="save_vision_snapshot",
    description=(
        "Capture the current camera frame (with no YOLO overlay) and save it "
        "to a JPEG file. Returns the saved filename or an error."
    ),
    params={
        "filename": {
            "type": "string",
            "description": "Output filename, e.g. 'snapshot_001.jpg'. Defaults to a timestamped name.",
        },
    },
)
def saveVisionSnapshot(filename: str = "") -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "error: vision not running — call start_vision first"

    jpeg = sess.grab_jpeg()
    if jpeg is None:
        return "error: no frame available yet"

    if not filename:
        filename = f"snapshot_{int(time.time())}.jpg"
    try:
        with open(filename, "wb") as f:
            f.write(jpeg)
        return f"ok: saved {filename} ({len(jpeg)} bytes)"
    except Exception as e:
        return f"error saving file: {e}"


@tool(
    name="get_vision_snapshot_base64",
    description=(
        "Return the current camera frame as a base64-encoded JPEG data-URI, "
        "suitable for passing directly to a vision-capable LLM. "
        "start_vision must have been called first."
    ),
    params={},
)
def getVisionSnapshotBase64() -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "error: vision not running — call start_vision first"

    jpeg = sess.grab_jpeg()
    if jpeg is None:
        return "error: no frame available yet"
    b64 = base64.b64encode(jpeg).decode()
    return f"data:image/jpeg;base64,{b64}"


@tool(
    name="get_vision_status",
    description="Return the current status of the vision pipeline: running / stopped, stream URL, and object count.",
    params={},
)
def getVisionStatus() -> str:
    global _session
    with _session_lock:
        sess = _session
    if sess is None:
        return "vision: stopped"
    n = len(sess.get_tracks())
    return f"vision: running  stream={sess.stream_url}  objects_visible={n}"