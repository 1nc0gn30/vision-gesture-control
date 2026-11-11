#!/usr/bin/env python3
"""Vision Gesture Control Standalone Production Server on Port 8089.

Provides real REST API endpoints:
  - /health & /api/health
  - /api/presets
  - /api/mcp/config
  - /api/diagnostics
  - /api/classify
  - /api/dwell
  - /api/face
  - /api/export-bundle
and serves the standalone Vision Studio from public/.
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
PUBLIC_DIR = ROOT_DIR / "public"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from vision_gesture_control import MCP_TOOLS_DEFINITIONS, __version__
from vision_gesture_control.ui_server import run_ui_server

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Vision Gesture Control Standalone Workstation")
    parser.add_argument("--version", action="version", version=f"vision-gesture-control {__version__}")
    parser.add_argument("--port", type=int, default=8089, help="Port to listen on (default: 8089)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--status", action="store_true", help="Print status payload and exit")
    parser.add_argument("--json", action="store_true", help="Emit JSON output and exit")
    args = parser.parse_args()

    if args.status or args.json:
        print(json.dumps({
            "tool": "vision-gesture-control",
            "version": __version__,
            "status": "ready",
            "host": args.host,
            "port": args.port,
            "local_url": f"http://{args.host}:{args.port}",
            "studio_url": "https://zoth.nullai.tech/tools/vision-gesture-control",
            "mcp_tools": [t["name"] for t in MCP_TOOLS_DEFINITIONS],
        }, indent=2))
        sys.exit(0)

    print(f"Starting Vision Gesture Control Server on {args.host}:{args.port}...")
    run_ui_server(host=args.host, port=args.port, public_dir=str(PUBLIC_DIR))
