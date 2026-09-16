# 🌟 Vision Gesture Control Examples Directory

This directory contains standalone, production-ready examples demonstrating real-world applications of **Vision Gesture Control**, from touchless web applications to Model Context Protocol (MCP) AI agent integrations.

---

## 📂 Example Catalog

```
examples/
├── presentation-controller/      # Touchless slide deck with laser tracking & dwell
│   ├── index.html                # Standalone HTML5 presentation app
│   └── README.md                 # Setup & usage documentation
├── air-drawing-app/              # 3D spatial air painting & sketching canvas
│   ├── index.html                # Standalone HTML5 air drawing app
│   └── README.md                 # Setup & usage documentation
├── mcp-clients/                  # Ready-to-copy AI Agent MCP configurations
│   ├── claude_desktop_config.json # Claude Desktop configuration
│   ├── cursor_mcp.json           # Cursor IDE configuration
│   ├── cline_mcp.json            # Cline (VS Code) configuration
│   ├── zed_settings.json         # Zed editor configuration
│   └── README.md                 # MCP client installation guide
└── README.md                     # This documentation index
```

---

## 🚀 Quick Execution Guide

### 1. Run the Presentation Controller
```bash
# Navigate to presentation example
cd examples/presentation-controller

# Launch a local static HTTP server
python3 -m http.server 8000
```
Visit `http://localhost:8000` to present hands-free using gestures or simulation controls.

---

### 2. Run the Air-Drawing Canvas
```bash
# Navigate to air drawing example
cd examples/air-drawing-app

# Launch a local static HTTP server
python3 -m http.server 8001
```
Visit `http://localhost:8001` to paint in the air using index/thumb pinch gestures.

---

### 3. Connect to AI Agents via MCP
```bash
# Verify the MCP server is working locally
python3 -m vision_gesture_control.mcp
```
See `examples/mcp-clients/README.md` for integrating with Claude Desktop, Cursor, Cline, or Zed.

---

## 🏗️ Architecture & Interaction Flow

```
┌────────────────────────────────────────────────────────┐
│               Webcam / Vision Sensor                   │
└──────────────────────────┬─────────────────────────────┘
                           │ 640x480 @ 60 FPS
                           ▼
┌────────────────────────────────────────────────────────┐
│           Landmark Extraction Engine                   │
│        (21 3D Joint Spatial Coordinates)               │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌─────────────────────────┐ ┌───────────────────────────┐
│ Vector Geometry Engine  │ │  Temporal Smoothing Filter│
│  (Angle & Distance)     │ │   (OneEuro / Kalman)      │
└────────────┬────────────┘ └─────────────┬─────────────┘
             │                            │
             └─────────────┬──────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│               Gesture State Machine                    │
│   (Pinch, Swipe, Point, Open Palm, Fist, Dwell)        │
└────────────┬─────────────────────────────┬─────────────┘
             │                             │
             ▼                             ▼
┌─────────────────────────┐   ┌───────────────────────────┐
│ Standalone Web Apps     │   │  MCP Server for AI Agents │
│ • Presentation Deck     │   │  • Claude Desktop         │
│ • Air-Drawing Canvas    │   │  • Cursor / Cline / Zed   │
└─────────────────────────┘   └───────────────────────────┘
```

---

## 🔒 Security & Privacy Notice

All examples in this repository follow strict **Local-First Privacy Standards**:
- Camera frames are analyzed in-memory and discarded immediately after landmark extraction.
- No biometric data, video streams, or user telemetry are sent over external network channels.
