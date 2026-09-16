# 🤖 Model Context Protocol (MCP) Server Architecture & Integration Guide

The **Model Context Protocol (MCP)** enables AI assistants and autonomous coding agents (Claude Desktop, Cursor, Cline, Zed, etc.) to query real-time computer vision telemetry, react to physical hand gestures, and trigger physical OS actions seamlessly.

---

## 📑 Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Supported Transports](#2-supported-transports)
3. [MCP Tool Catalog & Schemas](#3-mcp-tool-catalog--schemas)
4. [Resource URIs](#4-resource-uris)
5. [Client Configuration Templates](#5-client-configuration-templates)
6. [Agent Prompting Examples](#6-agent-prompting-examples)
7. [Latency & Performance Benchmarks](#7-latency--performance-benchmarks)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       AI Agent Core                         │
│            (Claude Desktop / Cursor / Cline / Zed)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (Stdio / SSE)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Vision Gesture Control MCP Server (FastMCP / Async)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ In-Memory IPC
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Vision Engine & Camera Tracking Loop               │
│     (21 Landmarks • Gesture State Machine • Telemetry)       │
└─────────────────────────────────────────────────────────────┘
```

The MCP server runs as a background process exposing standard JSON-RPC 2.0 endpoints. It maintains a lightweight, non-blocking lock on the shared vision state buffer, ensuring that agent tool calls complete in **under 2 milliseconds**.

---

## 2. Supported Transports

### Stdio Transport (Default)
Standard input/output stream communication. Best for local IDE plugins and desktop applications:
```bash
python -m vision_gesture_control.mcp
```

### Server-Sent Events (SSE) Transport
HTTP + SSE transport for distributed agent workflows:
```bash
python -m vision_gesture_control.mcp --transport sse --port 8000
```

---

## 3. MCP Tool Catalog & Schemas

### Tool 1: `get_active_gesture`
Queries the currently recognized hand gesture and confidence score.

#### Input Schema:
```json
{
  "type": "object",
  "properties": {
    "include_history": {
      "type": "boolean",
      "description": "Whether to include the last 5 frames of gesture transitions",
      "default": false
    }
  }
}
```

#### Response Example:
```json
{
  "gesture": "PINCH",
  "confidence": 0.982,
  "handedness": "Right",
  "dwell_progress_pct": 0,
  "timestamp": "2026-09-16T18:24:00.124Z",
  "bounding_box": { "x_min": 0.35, "y_min": 0.22, "x_max": 0.65, "y_max": 0.78 }
}
```

---

### Tool 2: `get_hand_landmarks`
Retrieves normalized 3D coordinates $(X, Y, Z)$ for all 21 joints of the detected hand(s).

#### Input Schema:
```json
{
  "type": "object",
  "properties": {
    "handedness": {
      "type": "string",
      "enum": ["Right", "Left", "Both"],
      "default": "Right",
      "description": "Which hand to retrieve landmarks for"
    }
  }
}
```

#### Response Example:
```json
{
  "handedness": "Right",
  "landmark_count": 21,
  "wrist": { "x": 0.502, "y": 0.784, "z": 0.000 },
  "index_finger_tip": { "x": 0.481, "y": 0.342, "z": -0.045 },
  "thumb_tip": { "x": 0.420, "y": 0.450, "z": -0.012 },
  "palm_normal": [0.015, 0.120, -0.992]
}
```

---

### Tool 3: `trigger_key_event`
Injects virtual keystrokes or keyboard commands to control active desktop applications.

#### Input Schema:
```json
{
  "type": "object",
  "properties": {
    "key": {
      "type": "string",
      "enum": ["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Space", "Enter", "Escape"],
      "description": "The key symbol to inject"
    },
    "action": {
      "type": "string",
      "enum": ["press", "down", "up"],
      "default": "press"
    }
  },
  "required": ["key"]
}
```

#### Response Example:
```json
{
  "status": "success",
  "key_injected": "ArrowRight",
  "action": "press",
  "timestamp": "2026-09-16T18:24:01.050Z"
}
```

---

### Tool 4: `capture_frame_telemetry`
Fetches real-time facial and geometric aspect ratios (EAR, MAR, Palm Openness).

#### Input Schema:
```json
{
  "type": "object",
  "properties": {
    "include_facial": {
      "type": "boolean",
      "default": true,
      "description": "Include Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR)"
    }
  }
}
```

#### Response Example:
```json
{
  "fps": 59.8,
  "ear_left": 0.315,
  "ear_right": 0.320,
  "mar": 0.082,
  "palm_openness_pct": 94,
  "head_pose": { "pitch": 2.1, "yaw": -3.8, "roll": 0.5 },
  "blink_count": 18
}
```

---

### Tool 5: `adjust_sensitivity`
Dynamically adjusts recognition thresholds, dwell confirmation timers, and smoothing factors without restarting the engine.

#### Input Schema:
```json
{
  "type": "object",
  "properties": {
    "detection_confidence": { "type": "number", "minimum": 0.1, "maximum": 1.0 },
    "dwell_ms": { "type": "integer", "minimum": 100, "maximum": 2000 },
    "smoothing_factor": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
  }
}
```

---

### Tool 6: `get_system_health`
Performs an end-to-end diagnostic health check on camera feed, engine latency, and worker threads.

#### Response Example:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "camera_connected": true,
  "average_pipeline_latency_ms": 11.4,
  "active_mcp_connections": 1
}
```

---

## 4. Resource URIs

Agents can subscribe to dynamic MCP resources for streaming telemetry:

- `gesture://landmarks/live`: Real-time stream of 21 3D landmarks.
- `gesture://telemetry/facial`: Live stream of Eye Aspect Ratio & Mouth Aspect Ratio.
- `gesture://system/status`: Real-time system performance and FPS.

---

## 5. Client Configuration Templates

### Claude Desktop
Add to `claude_desktop_config.json`:
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

### Cursor IDE
Add to `.cursor/mcp.json`:
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

---

## 6. Agent Prompting Examples

### Example 1: Hands-Free Code Navigation
> **User Prompt**: *"Monitor my hand gestures. When I swipe right, scroll down in the current editor buffer; when I make a fist, trigger a code formatting pass."*

### Example 2: Ergonomic Posture & Fatigue Guardian
> **User Prompt**: *"Query `capture_frame_telemetry` every 30 seconds. If EAR drops below 0.22 for more than 5 minutes or blink rate drops significantly, remind me to take a visual break."*

---

## 7. Latency & Performance Benchmarks

| Metric | Target | Measured Average |
| :--- | :--- | :--- |
| **Landmark Extraction Latency** | $< 15\text{ms}$ | **11.2 ms** |
| **Gesture State Evaluation** | $< 1\text{ms}$ | **0.3 ms** |
| **MCP Tool Response Time** | $< 5\text{ms}$ | **1.8 ms** |
| **Memory Footprint** | $< 180\text{MB}$ | **112 MB** |
