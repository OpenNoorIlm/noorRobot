# Noor 🤖 - Islamic AI-Powered Robot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Arduino](https://img.shields.io/badge/Arduino-Compatible-green.svg)](https://www.arduino.cc/)
[![ESP32](https://img.shields.io/badge/ESP32-Compatible-blue.svg)](https://www.espressif.com/)

**Noor** is an advanced Islamic AI-powered robot system featuring sophisticated Retrieval-Augmented Generation (RAG) with Islamic texts, extensive tool integrations, and seamless hardware control for Arduino, ESP32, and ESP32-CAM boards. The system provides intelligent robotic assistance with Islamic knowledge integration, real-time sensor processing, and autonomous decision-making capabilities.

## 🌟 Key Features

### 🕌 Islamic Knowledge Integration
- **Comprehensive Islamic Database**: Quran (Uthmani script), Hadith collections (Bukhari, Muslim), and Tafsir (Kanzul Iman, Jalalayn)
- **Advanced RAG Pipeline**: Multi-stage retrieval with query expansion, re-ranking, and context assembly
- **Semantic Search**: FAISS-powered vector search over 100k+ text chunks
- **Source Attribution**: Transparent citation of Islamic sources in responses

### 🛠️ Extensive Tool Ecosystem
**30+ Specialized Tools** across multiple domains:

#### **Productivity & Automation**
- **Browser Control**: Web scraping, automation, screenshot capture
- **Calendar**: Event management, scheduling, reminders
- **Gmail**: Email reading, sending, organization
- **Git Tools**: Repository management, commits, diffs
- **File System**: Advanced file operations, search, organization

#### **Media & Content Processing**
- **Audio Tools**: Speech-to-text, audio processing, transcription
- **Video Tools**: Video processing, YouTube transcript extraction
- **Image Tools**: OCR, image analysis, manipulation
- **PDF Tools**: Text extraction, manipulation, conversion
- **Grapher**: Data visualization, chart generation

#### **System & Development**
- **Code Executor**: Safe code execution in isolated environments
- **System Info**: Hardware monitoring, network diagnostics
- **Process Manager**: Task scheduling, background job management
- **Network Tools**: HTTP requests, API testing
- **PowerShell/WSL**: Cross-platform shell integration

#### **Islamic & Educational**
- **Quran Tools**: Verse lookup, recitation, translation
- **Hadith Tools**: Narration search, authentication
- **Notes**: Personal knowledge management
- **Prompt Library**: Reusable prompt templates

### 🚀 High-Performance API
- **RESTful Design**: Clean, intuitive endpoints
- **Streaming Support**: Real-time response streaming for chat and RAG
- **Multi-modal**: Text, vision, and agent interactions
- **Authentication**: Optional API key protection
- **CORS Support**: Configurable cross-origin policies
- **Threading**: Concurrent request handling

### 🧠 Advanced AI Capabilities
- **Groq Integration**: Access to state-of-the-art LLMs (Llama 3.3 70B)
- **Context-Aware**: Maintains conversation history and user preferences
- **Tool Calling**: Dynamic function execution with parameter validation
- **Vision Processing**: Image understanding and analysis
- **Memory Management**: Efficient context window utilization

## 📋 Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Hardware Setup](#hardware-setup)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Hardware Integration](#hardware-integration)
- [Islamic Features](#islamic-features)
- [Architecture](#architecture)
- [Tool System](#tool-system)
- [RAG Pipeline](#rag-pipeline)
- [Development](#development)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🔌 Hardware Requirements

### Supported Boards
- **Arduino Uno/Nano/Mega**: Basic robotic control
- **ESP32 DevKit**: Advanced WiFi/Bluetooth capabilities
- **ESP32-CAM**: Vision-enabled applications
- **ESP8266**: Basic IoT connectivity (limited features)

### Required Components
- **Microcontrollers**: Arduino/ESP32 boards
- **Sensors**: Ultrasonic, IR, temperature, humidity, motion sensors
- **Actuators**: Servo motors, DC motors, stepper motors
- **Communication**: WiFi module (ESP32), Bluetooth (optional)
- **Power Supply**: 5V-12V DC power source with adequate current
- **Camera**: OV2640 camera module for ESP32-CAM

### System Requirements
- **Host Computer**: Raspberry Pi 4+, Jetson Nano, or x86-64 PC
- **RAM**: Minimum 4GB, recommended 8GB+
- **Storage**: 10GB+ for datasets and vector stores
- **Network**: Stable internet for Groq API and dataset downloads

## 🛠️ Installation

### Prerequisites

- **Python**: 3.8 or higher
- **Git**: For cloning the repository
- **Arduino IDE**: For firmware development
- **PlatformIO**: Alternative development environment
- **Virtual Environment**: Recommended for dependency isolation

### Step-by-Step Setup

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd noorRobot
```

#### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows
.venv\Scripts\activate

# Activate on Unix/Mac
source .venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Download Islamic Datasets
```bash
python app/services/datasets_download.py
```

This downloads:
- Quran text (Uthmani script)
- Translation (Kanzul Iman)
- Tafsir (Jalalayn)
- Hadith collections (Bukhari, Muslim)

#### 5. Build Vector Store (Optional)
```bash
python -c "from app.utils.vectorStore import vector_store; vector_store.load_or_build()"
```

### System Dependencies

Some tools require additional system packages:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr ffmpeg

# macOS
brew install tesseract ffmpeg

# Windows (using Chocolatey)
choco install tesseract ffmpeg
```

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional
NOOR_API_KEY=your_api_key_for_auth
NOOR_CORS_ORIGIN=*
GROQ_MODEL=llama-3.3-70b-versatile
RAG_MAX_CTX=6000
RAG_THRESHOLD=0.25
```

## � Hardware Setup

### Arduino Setup
1. **Install Arduino IDE**
2. **Add ESP32 Board Support**:
   - Open Arduino IDE
   - Go to File > Preferences
   - Add board URL: `https://dl.espressif.com/dl/package_esp32_index.json`
   - Install ESP32 board via Board Manager

3. **Install Required Libraries**:
   ```cpp
   // Required libraries for Arduino
   #include <WiFi.h>
   #include <HTTPClient.h>
   #include <ArduinoJson.h>
   #include <Servo.h>
   ```

### ESP32 Setup
1. **Flash MicroPython** (recommended for complex applications):
   ```bash
   # Install esptool
   pip install esptool

   # Erase flash
   esptool.py --port /dev/ttyUSB0 erase_flash

   # Flash MicroPython
   esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-20220117-v1.18.bin
   ```

2. **Install Required Libraries**:
   ```python
   # MicroPython libraries
   import urequests
   import ujson
   import machine
   import time
   ```

### Basic Arduino Connection
```cpp
// Arduino WiFi Connection Example
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid = "your_wifi_ssid";
const char* password = "your_wifi_password";
const char* serverUrl = "http://192.168.1.100:8000";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
  }
  Serial.println("Connected to WiFi");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl + "/health");
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
      String payload = http.getString();
      Serial.println(payload);
    }
    http.end();
  }
  delay(5000);
}
```

## �🚀 Quick Start

### Basic Usage

1. **Start the Server**
```bash
python run.py
```

2. **Health Check**
```bash
curl http://localhost:8000/health
```

3. **Simple Chat**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Noor!"}'
```

4. **Islamic Question**
```bash
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the Quran say about patience?"}'
```

### Docker Usage (Future)

```bash
# Build image
docker build -t noorrobot .

# Run container
docker run -p 8000:8000 -e GROQ_API_KEY=your_key noorrobot
```

## ⚙️ Configuration

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | Required: Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model to use |
| `NOOR_API_KEY` | - | Optional: API authentication key |
| `NOOR_CORS_ORIGIN` | `*` | CORS allowed origins |

### Hardware Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SERIAL_PORT` | `/dev/ttyUSB0` | Serial port for direct hardware connection |
| `BAUD_RATE` | `115200` | Serial communication baud rate |
| `WIFI_SSID` | - | WiFi network name for robot connection |
| `WIFI_PASSWORD` | - | WiFi password |

### Islamic Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PRAYER_CALC_METHOD` | `1` | Islamic prayer calculation method (1-15) |
| `QIBLA_LATITUDE` | - | Location latitude for Qibla calculation |
| `QIBLA_LONGITUDE` | - | Location longitude for Qibla calculation |
| `HIJRI_ADJUSTMENT` | `0` | Hijri date adjustment offset |

### RAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_MAX_CTX` | `6000` | Maximum context characters |
| `RAG_HIST_TURNS` | `8` | Conversation history turns |
| `RAG_THRESHOLD` | `0.25` | Retrieval relevance threshold |
| `RAG_TEMP` | `0.7` | Generation temperature |
| `RAG_MAX_TOK` | `1024` | Maximum tokens per response |

### Dataset URLs (Advanced)

| Variable | Default | Description |
|----------|---------|-------------|
| `QURAN_TEXT_URL` | CDN URL | Quran text source |
| `KANZUL_IMAN_URL` | Tanzil.net | Translation source |
| `JALALAYN_URL` | Tanzil.net | Tafsir source |
| `HADITH_DATASET` | HuggingFace | Hadith dataset |

## 📡 API Reference

### Base URL
```
http://localhost:8000
```

### Authentication
Include API key in header if configured:
```
Authorization: Bearer your_api_key
```

### Endpoints

#### Health & System Info
```http
GET /health
GET /version
```

#### Tools Management
```http
GET  /tools/list
GET  /tools/info?name=tool_name
GET  /tools/schema
POST /tools/call
POST /tools/call_batch
```

#### Hardware Control
```http
POST /robot/command
POST /robot/motor
POST /robot/servo
POST /robot/sensor
POST /robot/camera
GET  /robot/sensors
```

#### Islamic Features
```http
GET  /islamic/prayer-times
GET  /islamic/qibla
POST /islamic/quran/recite
POST /islamic/hadith/search
```

#### Chat & Agent
```http
POST /chat
POST /chat/stream
POST /agent
```

#### Vision
```http
POST /vision
POST /vision/robot
POST /vision/stream
```
POST /vision/agent
```

#### RAG (Islamic Knowledge)
```http
POST /rag/ask
POST /rag/stream
POST /rag/rebuild
```

### Request/Response Examples

#### Chat Completion
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the meaning of life?",
    "history": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi there!"}
    ]
  }'
```

Response:
```json
{
  "response": "The meaning of life is a profound philosophical question...",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 200,
    "total_tokens": 350
  }
}
```

#### RAG Query
```bash
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does Islam teach about charity?",
    "include_sources": true
  }'
```

Response:
```json
{
  "answer": "In Islam, charity (Zakat and Sadaqah) is...",
  "sources": ["Quran 2:177", "Bukhari 1:7"],
  "retrieved_chunks": 5,
  "used_chunks": 3,
  "retrieval_ms": 45.2,
  "generation_ms": 234.1
}
```

#### Tool Call
```bash
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "time_current",
    "parameters": {"timezone": "UTC"}
  }'
```

Response:
```json
{
  "result": "2024-01-15T10:30:00Z",
  "success": true
}
```

#### Streaming Response
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a story"}'
```

Returns Server-Sent Events stream.

## 🔌 Hardware Integration

### Arduino Communication
```cpp
// Arduino HTTP Client Example
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* serverUrl = "http://192.168.1.100:8000";

void sendSensorData(float temperature, float humidity) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl + String("/robot/sensor"));
    http.addHeader("Content-Type", "application/json");
    
    DynamicJsonDocument doc(1024);
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["timestamp"] = millis();
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    int httpResponseCode = http.POST(jsonString);
    if (httpResponseCode > 0) {
      Serial.println("Data sent successfully");
    }
    http.end();
  }
}
```

### ESP32 MicroPython
```python
# ESP32 MicroPython Robot Control
import urequests
import ujson
import machine
import time

SERVER_URL = "http://192.168.1.100:8000"

def control_motor(speed, direction):
    data = {
        "command": "motor_control",
        "speed": speed,
        "direction": direction
    }
    
    try:
        response = urequests.post(f"{SERVER_URL}/robot/motor", 
                                json=data, timeout=5)
        result = response.json()
        response.close()
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

# Main control loop
while True:
    # Read sensors
    temp = read_temperature()
    distance = read_ultrasonic()
    
    # Send sensor data
    sensor_data = {
        "temperature": temp,
        "distance": distance,
        "timestamp": time.time()
    }
    
    try:
        response = urequests.post(f"{SERVER_URL}/robot/sensor", 
                                json=sensor_data)
        response.close()
    except:
        pass
    
    time.sleep(1)
```

### ESP32-CAM Vision Processing
```cpp
// ESP32-CAM Vision Integration
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "base64.h"

void sendFrameToAI() {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) return;
  
  // Convert to base64
  String base64Image = base64::encode(fb->buf, fb->len);
  
  HTTPClient http;
  http.begin("http://server:8000/vision/robot");
  http.addHeader("Content-Type", "application/json");
  
  String jsonPayload = "{";
  jsonPayload += "\"image\":\"" + base64Image + "\",";
  jsonPayload += "\"analyze\":true,";
  jsonPayload += "\"context\":\"islamic_environment\"";
  jsonPayload += "}";
  
  int httpCode = http.POST(jsonPayload);
  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    // Process AI response for robot actions
    processAIResponse(response);
  }
  
  http.end();
  esp_camera_fb_return(fb);
}
```

### Real-time Communication
```javascript
// WebSocket client for real-time control
const ws = new WebSocket('ws://localhost:8000/robot/ws');

ws.onopen = function() {
    console.log('Connected to Noor robot');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'sensor_update') {
        updateSensorDisplay(data.sensors);
    } else if (data.type === 'command') {
        executeRobotCommand(data.command);
    }
};

// Send commands
function sendRobotCommand(command, params) {
    ws.send(JSON.stringify({
        type: 'command',
        command: command,
        parameters: params
    }));
}
```

## 🕌 Islamic Features

### Prayer Time Management
```python
# Get prayer times
response = requests.get("http://localhost:8000/islamic/prayer-times", 
                       params={"lat": 24.7136, "lon": 46.6753})
prayer_times = response.json()

# Schedule robot actions
for prayer, time in prayer_times.items():
    schedule_robot_action(f"azan_{prayer}", time)
```

### Qibla Direction Finding
```python
# Get Qibla direction
response = requests.get("http://localhost:8000/islamic/qibla",
                       params={"lat": 24.7136, "lon": 46.6753})
qibla_data = response.json()

# Rotate robot towards Qibla
robot.rotate_to_angle(qibla_data['direction'])
```

### Quran Recitation Control
```python
# Request specific verse recitation
response = requests.post("http://localhost:8000/islamic/quran/recite", json={
    "surah": 1,
    "ayah": 1,
    "translation": True
})

# Robot speaks the verse
robot.speak(response.json()['arabic_text'])
```

### Hadith Search and Explanation
```python
# Search for hadith about patience
response = requests.post("http://localhost:8000/rag/ask", json={
    "message": "Find hadith about patience and perseverance",
    "include_sources": True
})

# Robot explains the hadith
for hadith in response.json()['sources']:
    robot.explain_hadith(hadith)
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Hardware      │────│   Noor API       │────│   AI Engine     │
│   (Arduino/     │    │   Server         │    │   (Groq)        │
│    ESP32)       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Sensors &     │    │  Islamic RAG     │    │   Tool System   │
│   Actuators     │    │   Pipeline       │    │   (35+ tools)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Components

#### 1. Hardware Abstraction Layer
- **Multi-board Support**: Arduino, ESP32, ESP32-CAM compatibility
- **Protocol Agnostic**: HTTP, MQTT, Serial, WebSocket support
- **Real-time Processing**: Low-latency sensor data handling
- **Power Management**: Efficient power consumption for battery-operated robots

#### 2. Islamic AI Integration
- **Context-Aware Responses**: Location and time-based Islamic guidance
- **Cultural Sensitivity**: Appropriate responses for Islamic contexts
- **Multi-language Support**: Arabic, English, and other Islamic languages
- **Ethical AI**: Islamic principles-guided decision making

#### 3. Robot Control System
- **Modular Architecture**: Plugin-based tool system
- **Concurrent Operations**: Multi-threaded task execution
- **Error Recovery**: Automatic fault detection and recovery
- **Remote Management**: Cloud-based monitoring and control

#### 4. HTTP API Server
- **Framework**: Python's built-in `http.server` with threading
- **Endpoints**: RESTful design with JSON payloads
- **Streaming**: Server-Sent Events for real-time responses
- **Authentication**: Optional Bearer token validation

#### 5. RAG Pipeline
- **Query Analysis**: Determines if retrieval is needed
- **Query Expansion**: Enhances search queries
- **Retrieval**: FAISS vector similarity search
- **Re-ranking**: Keyword-based relevance scoring
- **Context Assembly**: Token-bounded context packing
- **Generation**: LLM completion with context injection

### Data Flow

1. **Sensor Input**: Hardware sensors send data to API
2. **AI Processing**: Sensor data + Islamic context → AI analysis
3. **Decision Making**: AI generates appropriate robot actions
4. **Actuator Control**: Commands sent to motors/servos
5. **Feedback Loop**: Results fed back for continuous learning

**Software Flow:**
1. **Request Reception**: HTTP request parsed and validated
2. **Intent Analysis**: Determine if query needs RAG or direct LLM
3. **Retrieval Phase**: Query → Expansion → Vector Search → Re-ranking
4. **Context Building**: Assemble relevant chunks within token limits
5. **LLM Generation**: Inject context into prompt → Generate response
6. **Post-processing**: Clean output, add metadata, format response

## 🔧 Tool System

### Tool Structure

Each tool follows a consistent structure:

```
toolsf/
└── tool_name/
    ├── skill/
    │   └── tool_name.skill  # Declarative specification
    └── tool/
        └── tool_name.py     # Implementation
```

### Skill Definition Format

```json
{
  "name": "time_current",
  "description": "Get current time in specified timezone",
  "parameters": {
    "timezone": {
      "type": "string",
      "description": "Timezone (e.g., 'UTC', '+05:30')",
      "default": ""
    }
  },
  "returns": {
    "type": "string",
    "description": "ISO 8601 formatted timestamp"
  }
}
```

### Tool Implementation

```python
from app.utils.groq import tool

@tool(
    name="time_current",
    description="Get current time in specified timezone",
    params={
        "timezone": {"type": "string", "description": "Timezone"}
    }
)
def time_current(timezone: str = "") -> str:
    # Implementation here
    return datetime.now().isoformat()
```

### Tool Categories

#### Robotics & Hardware Control
- **Motor Control**: Precise servo and DC motor management
- **Sensor Processing**: Real-time data acquisition from multiple sensor types
- **Camera Integration**: Vision processing with ESP32-CAM
- **Audio Processing**: Speech recognition and Islamic recitation playback
- **LED Control**: RGB LED arrays for status indication and Islamic lighting

#### Islamic Applications
- **Prayer Management**: Automated prayer time announcements and Qibla direction
- **Quran Recitation**: Audio playback with verse tracking
- **Hadith Search**: Intelligent narration lookup and explanation
- **Islamic Calendar**: Hijri date calculations and Islamic event tracking
- **Zakat Calculator**: Automated charitable giving calculations

#### Productivity & Automation
- **Browser Control**: Web scraping and automation for Islamic research
- **Calendar**: Islamic event scheduling and reminder system
- **Gmail**: Email integration for Islamic correspondence
- **Git Tools**: Version control for robot firmware and AI models
- **File System**: Document management for Islamic texts and research

#### Media & Content Processing
- **Audio Tools**: Islamic lecture processing and transcription
- **Video Tools**: Islamic content analysis and YouTube integration
- **Image Tools**: OCR for Arabic text recognition
- **PDF Tools**: Islamic document processing
- **Grapher**: Data visualization for sensor analytics

#### System & Development
- **Code Executor**: Safe code execution for robot behavior scripting
- **System Info**: Hardware monitoring and diagnostics
- **Process Manager**: Task scheduling and background operations
- **Network Tools**: IoT connectivity testing and management
- **PowerShell/WSL**: Cross-platform development support

## 🧠 RAG Pipeline

### Pipeline Stages

#### 1. Query Analysis
- **Purpose**: Determine if retrieval is needed
- **Logic**: Pattern matching for conversational queries
- **Examples**:
  - ✅ Needs retrieval: "What does the Quran say about prayer?"
  - ❌ Direct response: "Hello" or "What time is it?"

#### 2. Query Expansion
- **Technique**: Keyword extraction + HyDE-lite
- **Input**: "patience in Islam"
- **Expanded**: "Context about: patience in Islam\nKeywords: patience islam"

#### 3. Retrieval
- **Method**: Cosine similarity in FAISS vector space
- **Top-K**: Configurable number of candidates (default: 10)
- **Sources**: Quran, Hadith, Tafsir chunks

#### 4. Re-ranking
- **Algorithm**: Jaccard keyword overlap scoring
- **Threshold**: Configurable relevance cutoff (default: 0.25)
- **Purpose**: Filter noise and prioritize relevant chunks

#### 5. Context Assembly
- **Strategy**: Greedy selection by score
- **Limit**: Character-based context window (default: 6000)
- **Format**: `[Source] Content` with separators

#### 6. Prompt Engineering
- **Persona**: Noor system prompt injection
- **Context**: Retrieved chunks + conversation history
- **Optimization**: Token-efficient formatting

#### 7. Generation
- **Model**: Groq Llama 3.3 70B Versatile
- **Parameters**: Temperature, max tokens, streaming
- **Safety**: Hallucination detection and filtering

### Performance Characteristics

- **Retrieval Latency**: <50ms for typical queries
- **Generation Latency**: 200-500ms per response
- **Memory Usage**: ~2GB for vector store
- **Concurrent Requests**: Threaded handling (up to 100+)

## 💻 Development

### Project Structure

```
noorRobot/
├── app/
│   ├── services/
│   │   ├── api.py                 # HTTP API server
│   │   └── datasets_download.py   # Dataset management
│   ├── toolsf/                   # Tool implementations
│   │   ├── audio_tools/
│   │   ├── browser_control/
│   │   └── ... (30+ tools)
│   ├── database/                 # Islamic datasets
│   │   ├── quran/
│   │   ├── hadith/
│   │   └── vector/               # FAISS indices
│   ├── utils/                    # Core utilities
│   │   ├── groq.py              # LLM integration
│   │   ├── RAG.py               # RAG pipeline
│   │   └── vectorStore.py       # Vector operations
│   ├── RAG.py                   # Public RAG API
│   ├── skills.py                # Skill management
│   └── tools.py                 # Tool orchestration
├── requirements.txt
├── run.py                       # Main entry point
├── test.py                      # Test suite
└── README.md
```

### Adding New Tools

#### 1. Create Tool Directory
```bash
mkdir -p app/toolsf/my_tool/{skill,tool}
```

#### 2. Define Skill Specification
Create `app/toolsf/my_tool/skill/my_tool.skill`:

```json
{
  "name": "my_tool_function",
  "description": "What my tool does",
  "parameters": {
    "param1": {
      "type": "string",
      "description": "Parameter description"
    }
  }
}
```

#### 3. Implement Tool
Create `app/toolsf/my_tool/tool/my_tool.py`:

```python
from app.utils.groq import tool

@tool(
    name="my_tool_function",
    description="What my tool does",
    params={
        "param1": {"type": "string", "description": "Parameter description"}
    }
)
def my_tool_function(param1: str) -> str:
    # Your implementation
    return f"Processed: {param1}"
```

#### 4. Test Tool
```bash
python test.py  # Check if tool loads
curl -X POST http://localhost:8000/tools/call \
  -d '{"tool_name": "my_tool_function", "parameters": {"param1": "test"}}'
```

### Testing

Run the test suite:
```bash
python test.py
```

Tests cover:
- Vector store loading
- Tool discovery and loading
- Dataset presence verification
- Basic functionality checks

### Code Style

- **Python**: PEP 8 compliant
- **Imports**: Absolute imports preferred
- **Type Hints**: Strongly encouraged
- **Docstrings**: Google-style format
- **Logging**: Structured logging with context

### Debugging

Enable debug logging:
```bash
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Your debug code here
"
```

## 📚 Examples

### Complete Robot Setup

#### 1. Arduino Sensor Node
```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <Ultrasonic.h>

#define DHT_PIN 4
#define TRIG_PIN 5
#define ECHO_PIN 18

DHT dht(DHT_PIN, DHT11);
Ultrasonic ultrasonic(TRIG_PIN, ECHO_PIN);

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin("ssid", "password");
}

void loop() {
  float temp = dht.readTemperature();
  float dist = ultrasonic.read();
  
  // Send to Noor API
  HTTPClient http;
  http.begin("http://server:8000/robot/sensor");
  http.addHeader("Content-Type", "application/json");
  
  String data = "{";
  data += "\"temperature\":" + String(temp) + ",";
  data += "\"distance\":" + String(dist);
  data += "}";
  
  http.POST(data);
  http.end();
  
  delay(1000);
}
```

#### 2. Python Robot Control
```python
import requests
import time

class NoorRobot:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
    
    def move_forward(self, speed=100, duration=1000):
        requests.post(f"{self.api_url}/robot/command", json={
            "command": "move_forward",
            "speed": speed,
            "duration": duration
        })
    
    def get_sensor_data(self):
        response = requests.get(f"{self.api_url}/robot/sensors")
        return response.json()
    
    def ask_islamic_question(self, question):
        response = requests.post(f"{self.api_url}/rag/ask", json={
            "message": question
        })
        return response.json()

# Usage
robot = NoorRobot()

# Move robot
robot.move_forward(speed=80, duration=2000)

# Get sensor readings
sensors = robot.get_sensor_data()
print(f"Temperature: {sensors['temperature']}°C")

# Ask Islamic question
answer = robot.ask_islamic_question("What is the importance of prayer in Islam?")
print(answer['answer'])
```

#### 3. Islamic Prayer Robot
```python
import requests
from datetime import datetime
import time

class IslamicRobot:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.location = {"lat": 24.7136, "lon": 46.6753}  # Mecca coordinates
    
    def get_prayer_times(self):
        response = requests.get(f"{self.api_url}/islamic/prayer-times", 
                              params=self.location)
        return response.json()
    
    def announce_prayer(self, prayer_name, prayer_time):
        # Move robot to indicate prayer time
        requests.post(f"{self.api_url}/robot/command", json={
            "command": "pray_position"
        })
        
        # Play Adhan
        requests.post(f"{self.api_url}/islamic/audio/play", json={
            "audio": "adhan",
            "prayer": prayer_name
        })
    
    def qibla_finder(self):
        response = requests.get(f"{self.api_url}/islamic/qibla",
                              params=self.location)
        direction = response.json()['direction']
        
        # Rotate robot towards Qibla
        requests.post(f"{self.api_url}/robot/servo", json={
            "servo_id": 1,
            "angle": direction
        })

# Usage
islamic_robot = IslamicRobot()

# Find Qibla direction
islamic_robot.qibla_finder()

# Schedule prayer announcements
prayer_times = islamic_robot.get_prayer_times()
for prayer, time_str in prayer_times.items():
    prayer_time = datetime.fromisoformat(time_str)
    # Schedule announcement (implementation depends on scheduling system)
    schedule_prayer_announcement(prayer, prayer_time)
```

### Basic Chat
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "message": "Hello Noor!"
})
print(response.json()["response"])
```

### Islamic Q&A
```python
response = requests.post("http://localhost:8000/rag/ask", json={
    "message": "What are the five pillars of Islam?",
    "include_sources": True
})
data = response.json()
print(f"Answer: {data['answer']}")
print(f"Sources: {data['sources']}")
```

### Tool Usage
```python
# Get current time
response = requests.post("http://localhost:8000/tools/call", json={
    "tool_name": "time_current",
    "parameters": {"timezone": "UTC"}
})
print(response.json()["result"])

# List files
response = requests.post("http://localhost:8000/tools/call", json={
    "tool_name": "filesystem_list",
    "parameters": {"path": "."}
})
print(response.json()["result"])
```

### Streaming Chat
```python
import json

response = requests.post("http://localhost:8000/chat/stream", json={
    "message": "Tell me about Islamic history"
}, stream=True)

for line in response.iter_lines():
    if line:
        data = json.loads(line.decode('utf-8'))
        print(data["chunk"], end="", flush=True)
```

### Vision Analysis
```python
import base64

# Read image file
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = requests.post("http://localhost:8000/vision", json={
    "image": f"data:image/jpeg;base64,{image_data}",
    "message": "What's in this image?"
})
print(response.json()["response"])
```

## 🔍 Troubleshooting

### Common Issues

#### Hardware Issues

##### 1. Serial Connection Problems
**Problem**: Cannot connect to Arduino/ESP32
**Solution**:
```bash
# Check available ports
ls /dev/ttyUSB*  # Linux
ls /dev/cu.usb*  # macOS

# Check permissions
sudo usermod -a -G dialout $USER

# Test connection
python -c "
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
print('Connected:', ser.is_open)
ser.close()
"
```

##### 2. WiFi Connection Issues
**Problem**: ESP32 cannot connect to WiFi
**Solution**:
```cpp
// Check WiFi credentials
#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  WiFi.begin("ssid", "password");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    Serial.print(".");
    delay(500);
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected!");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nFailed to connect");
  }
}
```

##### 3. Camera Issues (ESP32-CAM)
**Problem**: Camera not working
**Solution**:
```cpp
// Camera configuration
camera_config_t config;
config.ledc_channel = LEDC_CHANNEL_0;
config.ledc_timer = LEDC_TIMER_0;
config.pin_d0 = Y2_GPIO_NUM;
config.pin_d1 = Y3_GPIO_NUM;
// ... other pin configurations

esp_err_t err = esp_camera_init(&config);
if (err != ESP_OK) {
  Serial.printf("Camera init failed: 0x%x", err);
  return;
}
```

#### Software Issues

##### 1. Import Errors
**Problem**: `ModuleNotFoundError` on startup
**Solution**:
```bash
pip install -r requirements.txt
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

#### 2. Dataset Missing
**Problem**: RAG queries fail with missing data
**Solution**:
```bash
python app/services/datasets_download.py
```

#### 3. Vector Store Errors
**Problem**: FAISS loading failures
**Solution**:
```bash
rm -rf app/database/vector/
python -c "from app.utils.vectorStore import vector_store; vector_store.load_or_build()"
```

#### 4. API Key Issues
**Problem**: Authentication failures
**Solution**:
```bash
export GROQ_API_KEY=your_actual_key_here
```

#### 5. Port Already in Use
**Problem**: `Address already in use`
**Solution**:
```bash
# Find process using port 8000
lsof -i :8000  # or netstat -tulpn | grep :8000

# Kill process or change port
python run.py --port 8001
```

### Performance Tuning

#### Memory Optimization
```bash
# Reduce context window
export RAG_MAX_CTX=4000

# Lower retrieval threshold
export RAG_THRESHOLD=0.3
```

#### Speed Optimization
```bash
# Use faster model (if available)
export GROQ_MODEL=llama-3.1-8b-instant
```

### Logs and Debugging

Enable verbose logging:
```bash
export PYTHONPATH=.
python run.py 2>&1 | tee noorrobot.log
```

Check tool loading:
```bash
python -c "
from app.utils import groq as groq_utils
print('Loaded tools:', len(groq_utils.FUNCTIONS))
for name in sorted(groq_utils.FUNCTIONS.keys())[:5]:
    print(f'  {name}')
"
```

## 🤝 Contributing

### Development Workflow

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/yourusername/noorRobot.git`
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Make** your changes
5. **Test** thoroughly: `python test.py`
6. **Commit** your changes: `git commit -m 'Add amazing feature'`
7. **Push** to the branch: `git push origin feature/amazing-feature`
8. **Open** a Pull Request

### Contribution Guidelines

#### Code Quality
- Follow PEP 8 style guidelines
- Add type hints for function parameters and return values
- Write comprehensive docstrings
- Add unit tests for new functionality

#### Tool Development
- Follow the established tool structure
- Provide clear skill definitions
- Handle errors gracefully
- Add appropriate logging

#### Documentation
- Update README.md for new features
- Add examples for complex functionality
- Document configuration options

### Reporting Issues

When reporting bugs, please include:
- **Version**: Output of `GET /version`
- **Environment**: Python version, OS, dependencies
- **Steps to reproduce**: Minimal example
- **Expected vs actual behavior**
- **Logs**: Relevant error messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**Religious Guidance**: Noor is designed to provide information based on Islamic texts and general knowledge. For religious rulings, guidance, or interpretations, please consult qualified Islamic scholars and official religious authorities.

**Hardware Safety**: Robot operations involve mechanical and electrical components. Ensure proper safety measures, supervision, and compliance with local regulations when operating robotic systems.

**AI Limitations**: While Noor strives for accuracy, AI-generated responses may contain errors. Always verify important information through reliable sources.

**Usage Responsibility**: Users are responsible for how they use this robot system. Ensure compliance with applicable laws, ethical guidelines, and Islamic principles.

## 🙏 Acknowledgments

- **Islamic Dataset Providers**: Tanzil.net, HuggingFace, and Islamic scholars
- **Hardware Communities**: Arduino, ESP32, and maker communities
- **AI Research**: Groq for fast inference, and the broader AI community
- **Open Source Contributors**: Libraries and frameworks that power Noor

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/OpenNoorIlm/noorRobot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/OpenNoorIlm/noorRobot/discussions)
- **Hardware Forum**: Community discussions for hardware integration
- **Documentation**: This README and inline code documentation

---

**Noor 🤖** - Bridging Islamic Knowledge with Robotics 🤖🕌

# Note Will Release The Arduino Esp32 Esp32-CAM boards code folders soon!
---
# See the folder structure/code to understand more about this code as this documentation is created by AI.