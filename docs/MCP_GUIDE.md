# Model Context Protocol (MCP) Server Architecture & Integration Guide

`vision-gesture-control` ships a pure Python stdlib JSON-RPC 2.0 Model Context Protocol (MCP) server (`2024-11-05`) over `stdio` so coding agents (`Claude Desktop`, `Cursor`, `Cline`, `Zed`) can classify 21-joint hand landmarks, analyze dual-hand geometry, evaluate dwell zones, inspect facial expression metrics, and generate gesture-to-action maps.

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Stdio Transport](#2-stdio-transport)
3. [MCP Tool Catalog & Schemas](#3-mcp-tool-catalog--schemas)
4. [Client Configuration Templates](#4-client-configuration-templates)
5. [Latency & Performance Targets](#5-latency--performance-targets)

## 1. Architecture Overview

```text
AI Agent Core (Claude Desktop / Cursor / Cline / Zed)
        │ JSON-RPC 2.0 (stdio / Content-Length or NDJSON)
        ▼
vision_gesture_control.mcp_server (MCPServer)
        │ Pure Python 3D Geometry & Dwell Heuristics
        ▼
8 Deterministic Vision & Telemetry Tools
```

## 2. Stdio Transport

Launch the MCP server directly over standard input/output:

```bash
python3 -m vision_gesture_control.mcp_server
# or via the unified CLI:
vision-control mcp
```

Inspect the JSON tool definitions or generate client config snippets:

```bash
vision-control mcp --tools
vision-control mcp --config all
```

## 3. MCP Tool Catalog & Schemas

| Tool Name | Required Inputs | Description |
| :--- | :--- | :--- |
| `vision_classify_gesture` | `landmarks` | Classifies 21 3D/2D hand landmarks (`Right`, `Left`, `Unknown`) into `open_palm`, `fist`, `pointing_up`, `peace_sign`, `pinch`, `thumbs_up`, `thumbs_down`, `rock_on`, or `ok_sign` with confidence, pinch ratio, and per-finger extension states. |
| `vision_analyze_dual_hands` | `hand0_landmarks`, `hand1_landmarks` | Computes wrist-to-wrist span, index-tip span, relative Z depth, dual-pinch state, and dynamic ROI filter lens bounding box coordinates. |
| `vision_calculate_dwell` | `x`, `y`, `zone` | Evaluates pointer dwell progress (`0.0` to `1.0`), remaining milliseconds, and trigger completion inside an `{x, y, width, height}` target zone. |
| `vision_classify_face` | *(optional `face_landmarks`)* | Evaluates 468-point MediaPipe Face Mesh arrays or precomputed feature ratios for mouth opening, smile expression, and Eye Aspect Ratio (EAR) blink states. |
| `vision_generate_action_map` | *(optional `preset`, `overrides`)* | Generates gesture-to-key action bindings for `presentation`, `media`, `media_player`, `drawing`, `gaming`, or `accessibility`. |
| `vision_get_shader_filters` | *(none)* | Returns the 13 live optical shader filters (`normal`, `matrix`, `thermal`, `sobel`, `cyber_vhs`, `hologram`, `solar_gold`, `vortex_blackhole`, `lightning_plasma`, `hyper_kaleidoscope`, `cyber_glitch_mosh`, `fire_inferno`, `chrono_echo`) and their gesture triggers. |
| `vision_get_solfeggio_frequencies` | *(none)* | Returns the 9 Solfeggio frequencies (`174 Hz` to `963 Hz`) and dual-hand spatial audio Theremin mapping equations. |
| `vision_get_diagnostics` | *(optional `extended`)* | Returns OS, display server (`X11`/`Wayland`/macOS/Windows), Python runtime, CPU core count, and detected `/dev/video*` camera telemetry. |

## 4. Client Configuration Templates

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vision-gesture-control": {
      "command": "python3",
      "args": ["-m", "vision_gesture_control.mcp_server"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "vision-gesture-control": {
      "command": "python3",
      "args": ["-m", "vision_gesture_control", "mcp"]
    }
  }
}
```

### Zed

Add to `settings.json`:

```json
{
  "context_servers": {
    "vision-gesture-control": {
      "command": {
        "path": "python3",
        "args": ["-m", "vision_gesture_control.mcp_server"]
      }
    }
  }
}
```

## 5. Latency & Performance Targets

| Stage | Target | Typical |
| :--- | :--- | :--- |
| Landmark Extraction (WebAssembly/WebGL) | `< 15 ms` | `~11 ms` |
| 21-Joint Geometric Classification | `< 1 ms` | `~0.3 ms` |
| MCP Stdio Tool Dispatch | `< 5 ms` | `~1.8 ms` |
