<div align="center">

# 🖐️ Vision Gesture Control

### Ultra-Low-Latency Touchless Computer Vision, Gesture Recognition & Model Context Protocol (MCP) Engine

[![CI](https://github.com/google/vision-gesture-control/actions/workflows/ci.yml/badge.svg)](https://github.com/google/vision-gesture-control/actions/workflows/ci.yml)
[![Python 3.9 - 3.13](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![OS Matrix](https://img.shields.io/badge/OS-Ubuntu%20%7C%20macOS%20%7C%20Windows-green.svg)](https://github.com/google/vision-gesture-control)
[![MCP Ready](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[**Live Web Studio**](public/index.html) • [**Gesture Math Guide**](docs/GESTURE_RECOGNITION_GUIDE.md) • [**MCP Integration Guide**](docs/MCP_GUIDE.md) • [**Privacy & Security**](docs/CAMERA_SECURITY_PRIVACY.md) • [**Examples**](examples/README.md)

</div>

---

## 🌟 Overview

**Vision Gesture Control** is an enterprise-grade, privacy-first computer vision framework designed for real-time human-computer interaction, touchless UI navigation, 3D air drawing, and seamless Model Context Protocol (MCP) connectivity with autonomous AI agents (Claude Desktop, Cursor, Cline, Zed, and custom LLM tool loops).

Operating with **sub-15ms pipeline latency** and zero external tracking dependencies, Vision Gesture Control processes all video frames locally in volatile memory, extracting 21 three-dimensional hand landmarks and facial telemetry metrics (EAR/MAR) without persisting or transmitting raw video frames.

---

## 🚀 Key Features

- ⚡ **Sub-15ms Latency Engine**: Real-time landmark extraction with 1€ (OneEuro) and Kalman adaptive smoothing filters.
- 🖐️ **21-Joint 3D Hand Tracking**: Complete kinematic joint topology with trigonometric joint angle calculations.
- 🤖 **Native Model Context Protocol (MCP)**: Turn your physical gestures into AI agent tool invocations with zero setup.
- 🎨 **Material 3 Vision Studio**: Clean, responsive, offline-first light mode UI (design influenced by Material 3) with 4 interactive workspaces.
- 📑 **Touchless Presentation Controller**: Hands-free slide deck navigation with index finger laser pointer and dwell actions.
- 🖌️ **Spatial Air-Drawing Canvas**: Smooth 3D finger painting, color palette selection, and PNG export.
- 🔒 **100% Local-First Privacy**: Frames are processed purely in-memory and discarded immediately; zero cloud exfiltration.
- 🧪 **15-Job CI Matrix Tested**: Verified on Ubuntu, macOS, and Windows across Python 3.9, 3.10, 3.11, 3.12, and 3.13.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Webcam / Video Device Feed                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ 640x480 @ 60 FPS (In-Memory)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Landmark Extraction Engine                  │
│             (21 3D Spatial Joints + Face Mesh)              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
┌───────────────────────────────┐ ┌───────────────────────────┐
│     Vector Geometry Engine    │ │  1€ Adaptive Jitter Filter│
│  (Angles, Distance, Normals)  │ │ (Velocity-based smoothing)│
└───────────────┬───────────────┘ └───────────┬───────────────┘
                │                             │
                └──────────────┬──────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Gesture State Machine Engine                │
│    (Open Palm, Pinch, Point, Victory, Fist, Swipe, Dwell)   │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────────┐ ┌───────────────────────────┐
│   Interactive Web Studio      │ │ MCP Server for AI Agents  │
│   • Presentation Controller   │ │ • Claude Desktop          │
│   • Air Drawing Canvas        │ │ • Cursor / Cline / Zed    │
│   • Visual Filters/Telemetry  │ │ • Autonomous Tool Loops   │
└───────────────────────────────┘ └───────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/google/vision-gesture-control.git
cd vision-gesture-control

# Install with pip
pip install -e .
```

### 2. Launch Vision Studio (Web UI)

Open `public/index.html` in any modern web browser or serve it locally:

```bash
python3 -m http.server 8000 --directory public
```
Navigate to `http://localhost:8000` to access the interactive 4-tab Vision Studio (design influenced by Material 3)!

---

## 🤖 Model Context Protocol (MCP) Integration

Integrate Vision Gesture Control with Claude Desktop, Cursor, Cline, or Zed in seconds!

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vision-gesture-control": {
      "command": "python",
      "args": ["-m", "vision_gesture_control.mcp"]
    }
  }
}
```

### Supported MCP Tools:
| Tool Name | Description |
| :--- | :--- |
| `get_active_gesture` | Returns the currently recognized gesture, confidence, and handedness |
| `get_hand_landmarks` | Returns normalized 3D coordinates $(X, Y, Z)$ for all 21 hand joints |
| `trigger_key_event` | Injects virtual key presses (`ArrowRight`, `ArrowLeft`, `Space`, etc.) |
| `capture_frame_telemetry`| Returns Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR), and FPS |
| `adjust_sensitivity` | Dynamically updates detection thresholds, dwell timers, and smoothing |
| `get_system_health` | Performs health diagnostics on camera connectivity and pipeline latency |

---

## 🐍 Python API Usage

```python
from vision_gesture_control.engine import GestureEngine

# Initialize the real-time gesture engine
engine = GestureEngine(camera_index=0, smoothing_factor=0.6)

# Register a custom callback for swipe events
@engine.on("SWIPE_RIGHT")
def handle_swipe_right(event):
    print(f"👉 Swiped Right with confidence {event.confidence:.2f}!")

# Start the non-blocking background tracking loop
engine.start()
```

---

## 📂 Repository Structure

```
vision-gesture-control/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # 15-job cross-platform CI matrix
│       └── release.yml            # Wheel packaging, checksums & GitHub release
├── docs/
│   ├── GESTURE_RECOGNITION_GUIDE.md # Landmark math, vector geometry & smoothing
│   ├── MCP_GUIDE.md               # MCP server & client integration specification
│   └── CAMERA_SECURITY_PRIVACY.md # Local-first in-memory privacy & GDPR compliance
├── examples/
│   ├── presentation-controller/   # Touchless slide deck web application
│   ├── air-drawing-app/           # 3D spatial air painting canvas
│   ├── mcp-clients/               # Client config JSONs for Claude, Cursor, Cline, Zed
│   └── README.md                  # Examples directory guide
├── public/
│   └── index.html                 # Vision Studio (Material 3 Light UI influenced)
├── src/
│   └── vision_gesture_control/    # Core Python package & MCP server
├── tests/
│   └── test_examples.py           # Comprehensive unit & integration test suite
└── README.md                      # This master documentation
```

---

## 🧪 Running Tests

Run the complete test suite locally with `pytest`:

```bash
PYTHONPATH=src pytest tests/test_examples.py -v
```

---

## 🔒 Security & Privacy

Vision Gesture Control strictly adheres to **Zero-Knowledge Local Processing**:
- No video frames are ever recorded to persistent storage.
- No network connections are initiated unless explicitly configured by the user.
- Biometric landmarks are computed ephemerally in RAM and wiped upon stream close.

See [docs/CAMERA_SECURITY_PRIVACY.md](docs/CAMERA_SECURITY_PRIVACY.md) for full compliance audits.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
