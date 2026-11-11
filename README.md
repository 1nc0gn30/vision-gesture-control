<div align="center">
  <img src="assets/hero-banner.svg" alt="Vision Gesture Control Banner" width="100%" />
</div>

# Vision Gesture Control

**Touchless 21-Joint 3D Hand Tracking, Spatial Air Drawing, Dwell Navigation & Model Context Protocol (MCP) Server (`v2.5.0`)**

- **Zoth Studio Dossier**: [https://zoth.nullai.tech/tools/vision-gesture-control](https://zoth.nullai.tech/tools/vision-gesture-control)
- **Local Workstation URL**: `http://127.0.0.1:8089`
- **Repository**: [https://github.com/1nc0gn30/vision-gesture-control](https://github.com/1nc0gn30/vision-gesture-control)
- **Author**: [1nc0gn30](https://1nc0gn30.si) (`@1nc0gn30`) • [NullAI](https://nullai.tech)

## Overview

Vision Gesture Control combines a client-side WebAssembly/WebGL computer vision workstation (`public/`) with a zero-dependency Python standard-library HTTP server, CLI, and JSON-RPC 2.0 Model Context Protocol (MCP) server (`src/vision_gesture_control/`).

Key capabilities:
- **Sub-15ms Latency Hand & Face Kinematics**: Tracks 21 3D hand landmarks per hand with adaptive `OneEuroFilter` smoothing, curl-angle heuristics, pinch ratios, dual-hand span/ROI lens framing, and 468-point facial EAR/MAR metrics.
- **Interactive Browser Workspaces**: Touchless presentation slide controller with dwell rings, velocity-sensitive spline air-drawing canvas, 3D Three.js spatial geometry portal, 13 optical shader filters, and a 41-preset WebAudio spatial loop/Solfeggio studio (including a built-in Virtual Hand Simulator when no webcam is attached).
- **Zero Cloud Egress**: Video frames remain in volatile local memory for coordinate extraction and are never uploaded or written to disk.

## Architecture

```text
vision-gesture-control/
├── server.py                             # Standalone workstation entrypoint on 127.0.0.1:8089
├── bin/vision-gesture.js                 # Unified Node/ZothOS CLI & Electron desktop wrapper
├── public/
│   ├── index.html                        # Multi-tab Vision Studio UI & Virtual Hand Simulator
│   └── js/
│       ├── tool-air-drawing.js           # Quadratic spline air-drawing & palm-hold clear engine
│       ├── tool-presentation-spatial.js  # Slide laser/dwell controller & Three.js 3D portal
│       ├── tool-playground-lens.js       # Dual-hand EMA/deadzone ROI shader lens
│       ├── tool-gesturefx.js             # Gesture particle emitters, macropad & Biquad audio filter
│       └── tool-spatial-audio.js         # 41-preset WebAudio loop, synth, vocal & Solfeggio engine
└── src/vision_gesture_control/
    ├── cli.py                            # `vision-control` CLI (serve, classify, dwell, mcp, map, platform, test, status)
    ├── ui_server.py                      # ThreadingHTTPServer & REST API on 127.0.0.1:8089
    ├── mcp_server.py                     # Stdio JSON-RPC 2.0 MCP server (8 tools)
    ├── gestures.py                       # 3D joint-angle, pinch, dwell & facial EAR/MAR classifiers
    ├── filter_pipeline.py                # OneEuroFilter, 3D landmark smoother & filter pipeline
    ├── trajectory.py                     # Swipe velocity & pinch-zoom delta tracker
    └── compat.py                         # Multi-OS display server (X11/Wayland/macOS/Windows) & camera discovery
```

## Quick Start

```bash
git clone https://github.com/1nc0gn30/vision-gesture-control.git
cd vision-gesture-control
pip install -e .
python3 server.py --port 8089
```

Open `http://127.0.0.1:8089` in any WebGL-capable browser. No external Python runtime packages are required to run `server.py` or `PYTHONPATH=src python3 -m vision_gesture_control`.

## CLI & MCP Usage

### Python & ZothOS v3.4.0 CLI

On ZothOS v3.4.0 (or after `pip install -e .`), invoke `vision-control` or `node bin/vision-gesture.js`:

```bash
# Inspect CLI flags and subcommands
vision-control --help
node bin/vision-gesture.js --status --json

# Start the web studio on 127.0.0.1:8089
vision-control serve --host 127.0.0.1 --port 8089

# Classify 21 hand landmarks from a JSON file, inline JSON, or built-in sample
vision-control classify
vision-control classify --landmarks-json landmarks.json --handedness Right --confidence-threshold 0.6

# Evaluate pointer dwell progress inside an interactive bounding box (x,y,width,height)
vision-control dwell --x 0.45 --y 0.50 --zone 0.2,0.2,0.6,0.6 --duration 1000 --elapsed 650

# Export gesture-to-action key maps (presentation, media, drawing, gaming, accessibility)
vision-control map --preset presentation --format table

# Run OS, display server, and camera telemetry diagnostics
vision-control platform --extended

# Dump MCP tool schemas or client configuration snippets
vision-control mcp --tools
vision-control mcp --config claude_desktop
```

### REST API Endpoints (`127.0.0.1:8089`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health`, `/api/health` | Service health status, version (`2.5.0`), and uptime in seconds |
| `GET` | `/api/presets` | Gesture action maps (`?preset=presentation\|media\|drawing\|gaming\|accessibility\|all`) |
| `GET` | `/api/mcp/config` | Client config JSON (`?client=claude_desktop\|cursor\|cline\|zed\|all`) |
| `GET` | `/api/diagnostics` | System, Python, display server, CPU, and camera telemetry (`?extended=true`) |
| `POST` | `/api/classify` | Classify `{ "landmarks": [...21 pts...], "handedness": "Right" }` |
| `POST` | `/api/dwell` | Compute dwell progress for `{ "x", "y", "zone", "duration_ms", "elapsed_ms" }` |
| `POST` | `/api/face` | Classify facial blink/smile/mouth states from `{ "face_landmarks": ... }` |
| `GET` / `POST` | `/api/export-bundle` | Download standalone offline `vision-gesture-studio-standalone.zip` bundle |

### MCP Server Tools (`stdio`)

Configure your MCP host with `python3 -m vision_gesture_control.mcp_server` (see [`docs/MCP_GUIDE.md`](docs/MCP_GUIDE.md)):

- `vision_classify_gesture` — Classify 21 3D/2D hand landmarks with confidence, pinch state, and finger extension flags.
- `vision_analyze_dual_hands` — Compute inter-hand wrist/index span, Z-depth delta, dual-pinch state, and ROI lens bounds.
- `vision_calculate_dwell` — Evaluate normalized dwell progress and trigger state inside a bounding box.
- `vision_classify_face` — Evaluate facial landmarks or EAR/MAR ratios for blink, smile, and mouth-open states.
- `vision_generate_action_map` — Generate preset or custom-overridden gesture key bindings.
- `vision_get_shader_filters` — List the 13 optical shader filters and their gesture triggers.
- `vision_get_solfeggio_frequencies` — List the 9 Solfeggio frequencies (`174 Hz`–`963 Hz`) and Theremin axis mappings.
- `vision_get_diagnostics` — Query OS, display server, CPU, and camera diagnostics.

## Testing & Verification

```bash
# Run full unit & integration test suite (ephemeral port=0)
PYTHONPATH=src python3 -m pytest -q

# Run built-in stdlib self-tests
PYTHONPATH=src python3 -m vision_gesture_control --test

# Verify CLI status JSON
python3 server.py --status --json
```

## Support

Vision Gesture Control is 100% free and open-source with zero paywalls or feature gates. Optional support: [Buy Us a Coffee (Stripe)](https://buy.stripe.com/3cIfZg27PdKo2D64Ocfw40X).

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 [1nc0gn30](https://1nc0gn30.si) & [NullAI](https://nullai.tech).
