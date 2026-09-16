# 🤖 Model Context Protocol (MCP) Client Setup Guide

This directory contains configuration templates for connecting **Vision Gesture Control** to leading AI agents, IDEs, and assistants via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

---

## 📋 Client Configuration Matrix

| Client | Configuration File | Config Path |
| :--- | :--- | :--- |
| **Claude Desktop** | `claude_desktop_config.json` | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`<br>Windows: `%APPDATA%\Claude\claude_desktop_config.json`<br>Linux: `~/.config/Claude/claude_desktop_config.json` |
| **Cursor IDE** | `cursor_mcp.json` | Project Root: `.cursor/mcp.json` or Global Settings |
| **Cline (VS Code)** | `cline_mcp.json` | VS Code Extension Settings: `cline_mcp_settings.json` |
| **Zed Editor** | `zed_settings.json` | `~/.config/zed/settings.json` under `context_servers` |

---

## 🛠️ Step-by-Step Installation

### 1. Claude Desktop Setup

1. Locate your Claude configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`
2. Merge the following configuration into your `mcpServers` object:

```json
{
  "mcpServers": {
    "vision-gesture-control": {
      "command": "python",
      "args": [
        "-m",
        "vision_gesture_control.mcp"
      ],
      "env": {
        "GESTURE_DETECTION_CONFIDENCE": "0.75",
        "GESTURE_SMOOTHING_FACTOR": "0.6",
        "CAMERA_INDEX": "0"
      }
    }
  }
}
```

3. Restart Claude Desktop. You will see a hammer icon 🔨 indicating that `vision-gesture-control` tools are active.

---

### 2. Cursor IDE Setup

1. Open Cursor and navigate to **Settings** > **Features** > **MCP Servers**.
2. Click **Add New MCP Server**:
   - **Name**: `vision-gesture-control`
   - **Type**: `command`
   - **Command**: `python -m vision_gesture_control.mcp`
3. Or place `cursor_mcp.json` into `.cursor/mcp.json` in your workspace.

---

### 3. Cline (VS Code) Setup

1. Open the Cline tab in VS Code.
2. Click the MCP icon in the top right header to open MCP configuration settings.
3. Paste the contents of `cline_mcp.json`.

---

### 4. Zed Editor Setup

1. Open `~/.config/zed/settings.json`.
2. Add the `vision-gesture-control` block under the `context_servers` key:

```json
{
  "context_servers": {
    "vision-gesture-control": {
      "command": {
        "path": "python",
        "args": ["-m", "vision_gesture_control.mcp"]
      }
    }
  }
}
```

---

## 🧰 Available MCP Tools

When connected, AI agents gain access to the following tools:

- `get_active_gesture`: Returns the currently classified hand gesture, confidence score, and dwell status.
- `get_hand_landmarks`: Returns normalized 3D coordinates (X, Y, Z) for all 21 hand landmarks.
- `trigger_key_event`: Injects virtual keystrokes or navigation events.
- `capture_frame_telemetry`: Provides high-level telemetry including Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR).
- `adjust_sensitivity`: Configures detection thresholds, dwell timers, and smoothing factors dynamically.
- `get_system_health`: Checks camera availability, frame rate, and processing latency.

---

## 🔍 Troubleshooting

- **Python Not Found**: Ensure `python` or `python3` is available on your system `PATH`, or specify the absolute path to your virtual environment (e.g. `/path/to/venv/bin/python`).
- **Camera In Use**: If another app is locking your webcam, close other video applications or configure `CAMERA_INDEX=1`.
