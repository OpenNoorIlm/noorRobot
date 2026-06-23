import socket
import time
from app.utils.groq import tool


def _send_get_request(url: str, query, host: str = "localhost", port: int = 2673) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((host, port))
    request = f"GET {url}?q={query} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    s.sendall(request.encode())
    chunks = []
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        chunks.append(chunk)
    s.close()
    raw = b"".join(chunks).decode(errors="replace")
    if "\r\n\r\n" in raw:
        return raw.split("\r\n\r\n", 1)[1].strip()
    return raw.strip()


def _send_cam_request(url: str, query, host: str = "localhost", port: int = 2674) -> str:
    """Separate port for ESP32-CAM requests."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((host, port))
    request = f"GET {url}?q={query} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    s.sendall(request.encode())
    chunks = []
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        chunks.append(chunk)
    s.close()
    raw = b"".join(chunks).decode(errors="replace")
    if "\r\n\r\n" in raw:
        return raw.split("\r\n\r\n", 1)[1].strip()
    return raw.strip()


# ── Movement ───────────────────────────────────────────────────────────────────
@tool(
    name="forward",
    description="Moves the body forward for a number of steps.",
    params={"steps": {"type": "integer", "description": "Number of steps to move forward."}}
)
def forward(steps: int):
    if steps:
        for _ in range(steps):
            _send_get_request("/forward", 1)
            time.sleep(0.1)


@tool(
    name="backward",
    description="Moves the body backwards for a number of steps.",
    params={"steps": {"type": "integer", "description": "Number of steps to move backward."}}
)
def backward(steps: int):
    if steps:
        for _ in range(steps):
            _send_get_request("/backward", 1)
            time.sleep(0.1)


@tool(
    name="right",
    description="Turns the body to the right by a given angle.",
    params={"angle": {"type": "integer", "description": "Angle in degrees to turn right."}}
)
def right(angle: int):
    if angle:
        return _send_get_request("/right", angle)


@tool(
    name="left",
    description="Turns the body to the left by a given angle.",
    params={"angle": {"type": "integer", "description": "Angle in degrees to turn left."}}
)
def left(angle: int):
    if angle:
        return _send_get_request("/left", angle)


# ── Sensors ────────────────────────────────────────────────────────────────────
@tool(
    name="check_temperature",
    description="Check the current temperature of the body. Turns fan on above 100 ST or off if below.",
    params={}
)
def checkTemperature(unit: str = "C"):
    result = _send_get_request("/temperature", unit)
    return (
        f"If the temperature is above 100 ST or 120 ST degrees then turn on the fans, "
        f"else if fans are on then turn them off. Tool result: {result}"
    )


@tool(
    name="check_distance",
    description="Check the distance to the nearest obstacle at a given servo angle.",
    params={"angle": {"type": "integer", "description": "Servo angle to measure distance at (default 0 = straight ahead)."}}
)
def checkDistance(angle: int = 0):
    return _send_get_request("/distance", angle)


@tool(
    name="check_temperature_esp32",
    description="Check the current temperature of the ESP32.",
    params={}
)
def checkTempEsp32(unit: str = "C"):
    return _send_get_request("/temperature_esp32", unit)


@tool(
    name="check_temperature_esp32cam",
    description="Check the current temperature of the ESP32-CAM.",
    params={}
)
def checkTempEsp32Cam(unit: str = "C"):
    return _send_cam_request("/temperature", unit)


# ── Camera ─────────────────────────────────────────────────────────────────────
@tool(
    name="take_picture",
    description="Take a picture using the body's camera.",
    params={}
)
def takePicture():
    return _send_cam_request("/picture", "True")


@tool(
    name="take_picture_by_angle",
    description="Move the ESP32-CAM servos to horizontal/vertical angle then take a picture.",
    params={
        "angleX": {"type": "integer", "description": "Horizontal angle 0-180 (left/right servo)."},
        "angleY": {"type": "integer", "description": "Vertical angle 0-180 (up/down servo)."}
    }
)
def takePictureByAngle(angleX: int = 90, angleY: int = 90):
    return _send_cam_request("/picture_by_angle", f"{angleX},{angleY}")


@tool(
    name="move_camera",
    description="Move the ESP32-CAM to a horizontal/vertical angle without taking a picture.",
    params={
        "angleX": {"type": "integer", "description": "Horizontal angle 0-180 (left/right servo)."},
        "angleY": {"type": "integer", "description": "Vertical angle 0-180 (up/down servo)."}
    }
)
def moveCamera(angleX: int = 90, angleY: int = 90):
    return _send_cam_request("/move_camera", f"{angleX},{angleY}")


# ── Fan ────────────────────────────────────────────────────────────────────────
@tool(name="on_fan", description="Turn on the cooling fan.", params={})
def onFan():
    return _send_get_request("/fan", "on")


@tool(name="off_fan", description="Turn off the cooling fan.", params={})
def offFan():
    return _send_get_request("/fan", "off")


# ── Power / shutdown ───────────────────────────────────────────────────────────
@tool(name="shut_down_now", description="Shut down the system immediately.", params={})
def shutDown():
    return _send_get_request("/shutdown", "True")


@tool(
    name="shut_down",
    description="Shut down the system after a delay in seconds.",
    params={"durationSeconds": {"type": "integer", "description": "Seconds before shutdown."}}
)
def shutDownBySeconds(durationSeconds: int):
    return _send_get_request("/shutdownbyseconds", str(durationSeconds))


@tool(
    name="shut_down_by_time",
    description="Shut down the system at a specific clock time (24-hour).",
    params={
        "hour":   {"type": "integer", "description": "Hour (0-23) to shut down."},
        "minute": {"type": "integer", "description": "Minute (0-59) to shut down."}
    }
)
def shutDownByTime(hour: int, minute: int):
    t = time.localtime()
    duration_seconds = (hour - t.tm_hour) * 3600 + (minute - t.tm_min) * 60
    if duration_seconds < 0:
        return "Specified time is in the past. Please provide a future time."
    return _send_get_request("/shutdownbytime", str(duration_seconds))


@tool(name="shut_on", description="Turn the system back on.", params={})
def shutOn():
    return _send_get_request("/shuton", "True")


@tool(
    name="shut_on_by_seconds",
    description="Turn the system on after a delay in seconds.",
    params={"durationSeconds": {"type": "integer", "description": "Seconds before power-on."}}
)
def shutOnBySeconds(durationSeconds: int):
    return _send_get_request("/shutonbyseconds", str(durationSeconds))


@tool(
    name="shut_on_by_time",
    description="Turn the system on at a specific clock time (24-hour).",
    params={
        "hour":   {"type": "integer", "description": "Hour (0-23) to power on."},
        "minute": {"type": "integer", "description": "Minute (0-59) to power on."}
    }
)
def shutOnByTime(hour: int, minute: int):
    t = time.localtime()
    duration_seconds = (hour - t.tm_hour) * 3600 + (minute - t.tm_min) * 60
    if duration_seconds < 0:
        return "Specified time is in the past. Please provide a future time."
    return _send_get_request("/shutonbytime", str(duration_seconds))


# ── Diagnostics ────────────────────────────────────────────────────────────────
@tool(
    name="check_pin_availability",
    description="Check if a specific Arduino pin number is available for use.",
    params={"pinNumber": {"type": "integer", "description": "The pin number to check."}}
)
def pinsNotAvailable(pinNumber: int):
    return "Pin numbers 10 and 11 are not available (used by SoftwareSerial RX/TX)."


# ── OLED eyes ──────────────────────────────────────────────────────────────────
@tool(
    name="check_eyes",
    description="Set the robot's OLED eye expression.",
    params={
        "type": {"type": "string",  "description": "Expression: Cry, Angry, Happy, Sad, Surprised, Normal"},
        "x":    {"type": "integer", "description": "Horizontal offset in pixels (default 0)."},
        "y":    {"type": "integer", "description": "Vertical offset in pixels (default 0)."}
    }
)
def eyes(type: str, x: int = 0, y: int = 0):
    return _send_get_request("/eyes", f"{type},{x},{y}")

onFan()