"""
CLI implementation for vision-gesture-control.
Command-line interface with subcommands for serve, classify, dwell, mcp, map, platform, and test.
Pure Python stdlib with zero external runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unittest
import webbrowser
from typing import Any, Dict, List, Optional, Sequence

from . import __version__
from .mcp_server import (
    MCPServer,
    calculate_dwell,
    classify_face,
    classify_gesture,
    generate_action_map,
    generate_mcp_client_config,
    get_diagnostics,
    MCP_TOOLS_DEFINITIONS,
)
from .ui_server import DEFAULT_HOST, DEFAULT_PORT, UIServer


def _create_sample_landmarks(gesture_type: str = "open_palm") -> List[Dict[str, float]]:
    """Generates synthetic 21-landmark coordinates for demonstration or tests."""
    landmarks = []
    # Wrist (0)
    landmarks.append({"x": 0.5, "y": 0.8, "z": 0.0})

    is_fist = (gesture_type == "fist")
    is_pointing = (gesture_type == "pointing_up")
    is_peace = (gesture_type == "peace_sign")

    # Thumb: 1, 2, 3, 4
    landmarks.append({"x": 0.45, "y": 0.72, "z": -0.01})
    landmarks.append({"x": 0.40, "y": 0.65, "z": -0.02})
    landmarks.append({"x": 0.35, "y": 0.58, "z": -0.02})
    if is_fist:
        landmarks.append({"x": 0.42, "y": 0.68, "z": 0.02})  # Tucked
    else:
        landmarks.append({"x": 0.25, "y": 0.50, "z": -0.03})  # Extended

    # Index: 5, 6, 7, 8
    landmarks.append({"x": 0.46, "y": 0.55, "z": -0.01})
    landmarks.append({"x": 0.46, "y": 0.45, "z": -0.02})
    landmarks.append({"x": 0.46, "y": 0.38, "z": -0.02})
    if is_fist:
        landmarks.append({"x": 0.46, "y": 0.58, "z": 0.02})  # Curled
    else:
        landmarks.append({"x": 0.46, "y": 0.28, "z": -0.03})  # Extended

    # Middle: 9, 10, 11, 12
    landmarks.append({"x": 0.50, "y": 0.53, "z": 0.0})
    landmarks.append({"x": 0.50, "y": 0.42, "z": -0.01})
    landmarks.append({"x": 0.50, "y": 0.35, "z": -0.01})
    if is_fist or is_pointing:
        landmarks.append({"x": 0.50, "y": 0.57, "z": 0.02})  # Curled
    else:
        landmarks.append({"x": 0.50, "y": 0.24, "z": -0.02})  # Extended

    # Ring: 13, 14, 15, 16
    landmarks.append({"x": 0.54, "y": 0.55, "z": 0.01})
    landmarks.append({"x": 0.54, "y": 0.45, "z": 0.01})
    landmarks.append({"x": 0.54, "y": 0.38, "z": 0.01})
    if is_fist or is_pointing or is_peace:
        landmarks.append({"x": 0.54, "y": 0.58, "z": 0.02})  # Curled
    else:
        landmarks.append({"x": 0.54, "y": 0.28, "z": -0.01})  # Extended

    # Pinky: 17, 18, 19, 20
    landmarks.append({"x": 0.58, "y": 0.58, "z": 0.02})
    landmarks.append({"x": 0.58, "y": 0.49, "z": 0.02})
    landmarks.append({"x": 0.58, "y": 0.43, "z": 0.02})
    if is_fist or is_pointing or is_peace:
        landmarks.append({"x": 0.58, "y": 0.60, "z": 0.03})  # Curled
    else:
        landmarks.append({"x": 0.58, "y": 0.35, "z": 0.0})  # Extended

    return landmarks


def _parse_zone_string(zone_str: str) -> Dict[str, float]:
    """Parses 'x,y,w,h' string or JSON zone object."""
    zone_str = zone_str.strip()
    if zone_str.startswith("{"):
        return json.loads(zone_str)
    parts = [float(p.strip()) for p in zone_str.split(",")]
    if len(parts) != 4:
        raise ValueError("Zone must be 4 comma-separated values: x,y,width,height")
    return {"x": parts[0], "y": parts[1], "width": parts[2], "height": parts[3]}


def cmd_serve(args: argparse.Namespace) -> int:
    """Starts Vision Studio."""
    server = UIServer(host=args.host, port=args.port)
    server.start()
    url = server.get_url()
    print(f"🌟 Vision Studio (Material 3 influenced) running at {url}")

    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    print("Press Ctrl+C to stop.")
    try:
        while True:
            import time
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.stop()
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    """Classifies landmarks from file, JSON argument, or stdin."""
    landmarks_raw = None

    if args.landmarks_json:
        if os.path.isfile(args.landmarks_json):
            with open(args.landmarks_json, "r", encoding="utf-8") as f:
                landmarks_raw = json.load(f)
        else:
            landmarks_raw = json.loads(args.landmarks_json)
    else:
        try:
            if not sys.stdin.isatty():
                content = sys.stdin.read().strip()
                if content:
                    landmarks_raw = json.loads(content)
        except Exception:
            pass

    if not landmarks_raw:
        # Fallback to sample landmark set
        landmarks_raw = _create_sample_landmarks("open_palm")

    result = classify_gesture(
        landmarks=landmarks_raw,
        handedness=args.handedness,
        confidence_threshold=args.confidence_threshold,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_dwell(args: argparse.Namespace) -> int:
    """Computes dwell state for pointer in zone."""
    try:
        zone = _parse_zone_string(args.zone)
    except Exception as e:
        print(f"Error parsing --zone: {str(e)}", file=sys.stderr)
        return 1

    result = calculate_dwell(
        x=args.x,
        y=args.y,
        zone=zone,
        duration_ms=args.duration,
        elapsed_ms=args.elapsed,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    """MCP server subcommand: runs stdio server or prints config/tools."""
    if args.tools:
        print(json.dumps({"tools": MCP_TOOLS_DEFINITIONS}, indent=2))
        return 0

    if args.config:
        config = generate_mcp_client_config(args.config)
        print(json.dumps(config, indent=2))
        return 0

    # Default: Run MCP stdio server
    server = MCPServer()
    server.run_stdio()
    return 0


def cmd_map(args: argparse.Namespace) -> int:
    """Outputs gesture key bindings for given preset."""
    action_map = generate_action_map(args.preset)

    if args.format == "table":
        print(f"=== {action_map['name']} ===")
        print(f"Description: {action_map['description']}")
        print(f"Target App:  {action_map.get('target_app', 'General')}")
        print(f"Cooldown:    {action_map.get('cooldown_ms', 500)}ms\n")
        print(f"{'GESTURE':<20} | {'KEY / ACTION':<18} | {'DESCRIPTION'}")
        print("-" * 70)
        for g, b in action_map.get("bindings", {}).items():
            key = b.get("key", b.get("action", ""))
            desc = b.get("description", "")
            print(f"{g:<20} | {key:<18} | {desc}")
    else:
        print(json.dumps(action_map, indent=2))
    return 0


def cmd_platform(args: argparse.Namespace) -> int:
    """Runs multi-OS diagnostics and outputs JSON."""
    diag = get_diagnostics(extended=args.extended)
    print(json.dumps(diag, indent=2))
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    """Runs internal self-test suite."""
    print("Running vision-gesture-control self-tests...")
    suite = unittest.TestSuite()

    # Define inline self-test cases
    class SelfTest(unittest.TestCase):
        def test_sample_classification(self):
            palm = _create_sample_landmarks("open_palm")
            res_palm = classify_gesture(palm)
            self.assertEqual(res_palm["gesture"], "open_palm")
            self.assertGreater(res_palm["confidence"], 0.8)

            fist = _create_sample_landmarks("fist")
            res_fist = classify_gesture(fist)
            self.assertEqual(res_fist["gesture"], "fist")

            peace = _create_sample_landmarks("peace_sign")
            res_peace = classify_gesture(peace)
            self.assertEqual(res_peace["gesture"], "peace_sign")

            pointing = _create_sample_landmarks("pointing_up")
            res_pointing = classify_gesture(pointing)
            self.assertEqual(res_pointing["gesture"], "pointing_up")

        def test_dwell_calc(self):
            zone = {"x": 0.2, "y": 0.2, "width": 0.4, "height": 0.4}
            # Inside zone
            r_in = calculate_dwell(0.3, 0.3, zone, duration_ms=1000, elapsed_ms=500)
            self.assertTrue(r_in["in_zone"])
            self.assertEqual(r_in["progress"], 0.5)
            self.assertFalse(r_in["triggered"])

            # Completed
            r_comp = calculate_dwell(0.3, 0.3, zone, duration_ms=1000, elapsed_ms=1000)
            self.assertTrue(r_comp["triggered"])
            self.assertEqual(r_comp["progress"], 1.0)

            # Outside zone
            r_out = calculate_dwell(0.8, 0.8, zone, duration_ms=1000, elapsed_ms=500)
            self.assertFalse(r_out["in_zone"])
            self.assertEqual(r_out["progress"], 0.0)

        def test_face_classification(self):
            r = classify_face({"mouth_open_ratio": 0.5, "smile_score": 0.8, "left_ear": 0.15, "right_ear": 0.15})
            self.assertTrue(r["mouth_open"])
            self.assertTrue(r["smiling"])
            self.assertTrue(r["both_eyes_blink"])

        def test_mcp_configs(self):
            for c in ["claude_desktop", "cursor", "cline", "zed", "all"]:
                cfg = generate_mcp_client_config(c)
                self.assertIsInstance(cfg, dict)

        def test_action_maps(self):
            for p in ["presentation", "media", "drawing", "gaming", "accessibility"]:
                am = generate_action_map(p)
                self.assertIn("bindings", am)

    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(SelfTest))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def build_parser() -> argparse.ArgumentParser:
    """Builds top-level CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="vision-control",
        description="vision-gesture-control: Zero-dependency MCP Server, CLI & Material 3 Web Studio",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--test", action="store_true", help="Run internal self-tests")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. serve
    p_serve = subparsers.add_parser("serve", help="Starts Vision Studio Web UI (design influenced by Material 3)")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind (default: {DEFAULT_PORT})")
    p_serve.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    p_serve.add_argument("--open", action="store_true", help="Automatically open web browser on start")
    p_serve.set_defaults(func=cmd_serve)

    # 2. classify
    p_classify = subparsers.add_parser("classify", help="Classifies 21 hand landmarks")
    p_classify.add_argument("--landmarks-json", type=str, help="JSON string or path to JSON file with landmarks")
    p_classify.add_argument("--handedness", type=str, default="Right", choices=["Right", "Left", "Unknown"])
    p_classify.add_argument("--confidence-threshold", type=float, default=0.5)
    p_classify.set_defaults(func=cmd_classify)

    # 3. dwell
    p_dwell = subparsers.add_parser("dwell", help="Computes dwell progress inside interactive zone")
    p_dwell.add_argument("--x", type=float, required=True, help="Pointer X position (0.0 to 1.0 or pixels)")
    p_dwell.add_argument("--y", type=float, required=True, help="Pointer Y position (0.0 to 1.0 or pixels)")
    p_dwell.add_argument("--zone", type=str, required=True, help="Bounding box 'x,y,width,height' or JSON")
    p_dwell.add_argument("--duration", type=float, default=1000.0, help="Target dwell duration in ms (default: 1000)")
    p_dwell.add_argument("--elapsed", type=float, default=0.0, help="Elapsed duration in ms (default: 0)")
    p_dwell.set_defaults(func=cmd_dwell)

    # 4. mcp
    p_mcp = subparsers.add_parser("mcp", help="Stdio JSON-RPC Model Context Protocol (MCP) server")
    p_mcp.add_argument("--tools", action="store_true", help="Print available MCP tools schema JSON")
    p_mcp.add_argument(
        "--config",
        type=str,
        choices=["claude", "claude_desktop", "cursor", "cline", "zed", "all"],
        help="Generate client configuration snippet",
    )
    p_mcp.set_defaults(func=cmd_mcp)

    # 5. map
    p_map = subparsers.add_parser("map", help="Outputs gesture key bindings")
    p_map.add_argument(
        "--preset",
        type=str,
        default="presentation",
        choices=["presentation", "media", "media_player", "drawing", "gaming", "accessibility"],
        help="Action map preset category",
    )
    p_map.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "table"],
        help="Output format (json or table)",
    )
    p_map.set_defaults(func=cmd_map)

    # 6. platform
    p_platform = subparsers.add_parser("platform", help="Multi-OS diagnostics and telemetry")
    p_platform.add_argument("--extended", action="store_true", help="Include extended environment variables")
    p_platform.set_defaults(func=cmd_platform)

    # 7. test
    p_test = subparsers.add_parser("test", help="Run internal self-test suite")
    p_test.set_defaults(func=cmd_test)

    return parser


def main(args: Optional[Sequence[str]] = None) -> int:
    """CLI main entry point."""
    parser = build_parser()
    parsed = parser.parse_args(args)

    if parsed.test:
        return cmd_test(parsed)

    if not parsed.command:
        parser.print_help()
        return 0

    if hasattr(parsed, "func"):
        return parsed.func(parsed)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
