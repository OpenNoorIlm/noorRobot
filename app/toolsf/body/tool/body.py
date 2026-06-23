import base64
import socket
from urllib.parse import quote

from app.utils.groq import tool

ESP32_HOST = "192.0.242.3"
ESP32_CAM_HOST = "192.0.242.3"


def _build_request_path(url: str, query=None, **extra_params) -> str:
    params = []
    if query is not None:
        params.append(f"q={quote(str(query), safe=',')}")
    for key, value in extra_params.items():
        if value is not None:
            params.append(f"{key}={quote(str(value), safe=',')}")
    if not params:
        return url
    return f"{url}?{'&'.join(params)}"


def _send_http_request(
    url: str,
    query=None,
    *,
    host: str,
    port: int,
    timeout: int = 5,
    recv_size: int = 1024,
    **extra_params,
) -> str:
    request_path = _build_request_path(url, query, **extra_params)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    request = (
        f"GET {request_path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n\r\n"
    )
    s.sendall(request.encode())
    chunks = []
    while True:
        chunk = s.recv(recv_size)
        if not chunk:
            break
        chunks.append(chunk)
    s.close()
    raw = b"".join(chunks).decode(errors="replace")
    if "\r\n\r\n" in raw:
        return raw.split("\r\n\r\n", 1)[1].strip()
    return raw.strip()


def _send_get_request(url: str, query=None, host: str = ESP32_HOST, port: int = 2673, **extra_params) -> str:
    return _send_http_request(url, query, host=host, port=port, **extra_params)


def _send_cam_request(url: str, query=None, host: str = ESP32_CAM_HOST, port: int = 2674, **extra_params) -> str:
    return _send_http_request(url, query, host=host, port=port, **extra_params)


def _get_cam_picture(url: str, query=None, host: str = ESP32_CAM_HOST, port: int = 2674, **extra_params) -> str:
    request_path = _build_request_path(url, query, **extra_params)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((host, port))
    request = (
        f"GET {request_path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Connection: close\r\n\r\n"
    )
    s.sendall(request.encode())
    chunks = []
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
    s.close()
    raw = b"".join(chunks)
    if b"\r\n\r\n" not in raw:
        return "error: no image body received"
    body = raw.split(b"\r\n\r\n", 1)[1]
    if len(body) < 100:
        return f"error: image too small ({len(body)} bytes)"
    b64 = base64.b64encode(body).decode()
    return f"data:image/jpeg;base64,{b64}"


@tool(
    name="forward",
    description="Move the robot forward for a number of 100ms steps. Optional speed range is 0-255.",
    params={
        "steps": {"type": "integer", "description": "Number of 100ms steps to move forward."},
        "speed": {"type": "integer", "description": "Motor speed from 0 to 255. Default is 255."},
    },
)
def forward(steps: int, speed: int = 255):
    return _send_get_request("/forward", steps, speed=speed)


@tool(
    name="backward",
    description="Move the robot backward for a number of 100ms steps. Optional speed range is 0-255.",
    params={
        "steps": {"type": "integer", "description": "Number of 100ms steps to move backward."},
        "speed": {"type": "integer", "description": "Motor speed from 0 to 255. Default is 255."},
    },
)
def backward(steps: int, speed: int = 255):
    return _send_get_request("/backward", steps, speed=speed)


@tool(
    name="right",
    description="Turn the robot body to the right by the provided motor value.",
    params={"angle": {"type": "integer", "description": "Right turn motor value."}},
)
def right(angle: int):
    return _send_get_request("/right", angle)


@tool(
    name="left",
    description="Turn the robot body to the left by the provided motor value.",
    params={"angle": {"type": "integer", "description": "Left turn motor value."}},
)
def left(angle: int):
    return _send_get_request("/left", angle)


@tool(name="stop", description="Stop all body motors immediately.", params={})
def stop():
    return _send_get_request("/stop")


@tool(
    name="check_temperature",
    description="Check the Arduino-side body temperature sensor result.",
    params={},
)
def checkTemperature(unit: str = "C"):
    return _send_get_request("/temperature", unit)


@tool(
    name="check_distance",
    description="Check distance to the nearest obstacle at a given servo angle.",
    params={"angle": {"type": "integer", "description": "Servo angle for the distance scan."}},
)
def checkDistance(angle: int = 0):
    return _send_get_request("/distance", angle)


@tool(
    name="check_temperature_esp32",
    description="Check the ESP32 board temperature.",
    params={},
)
def checkTempEsp32():
    return _send_get_request("/temperature_esp32")


@tool(
    name="check_temperature_esp32cam",
    description="Check the ESP32-CAM board temperature.",
    params={},
)
def checkTempEsp32Cam():
    return _send_cam_request("/temperature")


@tool(
    name="take_picture",
    description="Take a picture using the ESP32-CAM and return a base64 JPEG image.",
    params={},
)
def takePicture():
    return _get_cam_picture("/picture")


@tool(
    name="take_picture_by_angle",
    description="Move the camera to the requested pan/tilt angles and then take a picture.",
    params={
        "angleX": {"type": "integer", "description": "Horizontal angle from 0 to 180."},
        "angleY": {"type": "integer", "description": "Vertical angle from 0 to 180."},
    },
)
def takePictureByAngle(angleX: int = 90, angleY: int = 90):
    return _get_cam_picture("/picture_by_angle", f"{angleX},{angleY}")


@tool(
    name="move_camera",
    description="Move the ESP32-CAM pan/tilt servos without taking a picture.",
    params={
        "angleX": {"type": "integer", "description": "Horizontal angle from 0 to 180."},
        "angleY": {"type": "integer", "description": "Vertical angle from 0 to 180."},
    },
)
def moveCamera(angleX: int = 90, angleY: int = 90):
    return _send_cam_request("/move_camera", f"{angleX},{angleY}")


@tool(name="on_fan", description="Turn on the body cooling fan.", params={})
def onFan():
    return _send_get_request("/fan", "on")


@tool(name="off_fan", description="Turn off the body cooling fan.", params={})
def offFan():
    return _send_get_request("/fan", "off")


@tool(name="check_fan_status", description="Check whether the body cooling fan is on or off.", params={})
def checkFanStatus():
    return _send_get_request("/fan", "status")


@tool(name="shut_down_now", description="Shut down the system immediately.", params={})
def shutDown():
    return _send_get_request("/shutdown", "True")


@tool(
    name="shut_down",
    description="Shut down the system after a delay in seconds.",
    params={"durationSeconds": {"type": "integer", "description": "Seconds before shutdown."}},
)
def shutDownBySeconds(durationSeconds: int):
    return _send_get_request("/shutdownbyseconds", durationSeconds)


@tool(
    name="shut_down_by_time",
    description="Forward a target shutdown time to the robot in 24-hour hour,minute format.",
    params={
        "hour": {"type": "integer", "description": "Hour from 0 to 23."},
        "minute": {"type": "integer", "description": "Minute from 0 to 59."},
    },
)
def shutDownByTime(hour: int, minute: int):
    return _send_get_request("/shutdownbytime", f"{hour},{minute}")


@tool(name="shut_on", description="Turn the system back on.", params={})
def shutOn():
    return _send_get_request("/shuton", "True")


@tool(
    name="shut_on_by_seconds",
    description="Turn the system on after a delay in seconds.",
    params={"durationSeconds": {"type": "integer", "description": "Seconds before power-on."}},
)
def shutOnBySeconds(durationSeconds: int):
    return _send_get_request("/shutonbyseconds", durationSeconds)


@tool(
    name="shut_on_by_time",
    description="Forward a target power-on time to the robot in 24-hour hour,minute format.",
    params={
        "hour": {"type": "integer", "description": "Hour from 0 to 23."},
        "minute": {"type": "integer", "description": "Minute from 0 to 59."},
    },
)
def shutOnByTime(hour: int, minute: int):
    return _send_get_request("/shutonbytime", f"{hour},{minute}")


@tool(
    name="check_pin_availability",
    description="Check whether an Arduino pin is available for body hardware expansion.",
    params={"pinNumber": {"type": "integer", "description": "Arduino pin number to check."}},
)
def pinsNotAvailable(pinNumber: int):
    unavailable_pins = {
        3: "forward motor",
        4: "ultrasonic trigger",
        5: "backward motor",
        6: "right motor",
        7: "ultrasonic echo",
        9: "left motor",
        10: "SoftwareSerial RX",
        11: "SoftwareSerial TX",
        12: "fan",
        13: "distance servo",
    }
    if pinNumber in unavailable_pins:
        return f"Pin {pinNumber} is not available because it is used for {unavailable_pins[pinNumber]}."
    return f"Pin {pinNumber} is not listed as occupied in the current Arduino sketch."


@tool(
    name="check_eyes",
    description="Set the robot OLED eye expression. Supported types include Normal, Happy, Sad, Angry, Surprised, Cry, Love, Sleepy, Confused, Excited, Dizzy, Bored, Evil, Shy, Cool, Wink, Dead, and Nervous.",
    params={
        "type": {"type": "string", "description": "Eye expression name."},
        "x": {"type": "integer", "description": "Horizontal pixel offset."},
        "y": {"type": "integer", "description": "Vertical pixel offset."},
    },
)
def eyes(type: str, x: int = 0, y: int = 0):
    return _send_get_request("/eyes", f"{type},{x},{y}")


@tool(name="clear_eyes", description="Clear the robot OLED display.", params={})
def clearEyes():
    return _send_get_request("/clear", 1)
