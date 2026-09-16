"""
Unit tests for MCP Server and Core Geometry algorithms in vision-gesture-control.
"""

import io
import json
import unittest
from vision_gesture_control.mcp_server import (
    MCPServer,
    calculate_dwell,
    classify_face,
    classify_gesture,
    generate_action_map,
    generate_mcp_client_config,
    get_diagnostics,
    MCP_TOOLS_DEFINITIONS,
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
)


def make_landmarks_for_gesture(gesture: str):
    """Helper to generate 21 landmarks for testing."""
    pts = []
    # Wrist (0)
    pts.append({"x": 0.5, "y": 0.8, "z": 0.0})

    is_fist = (gesture == "fist")
    is_pointing = (gesture == "pointing_up")
    is_peace = (gesture == "peace_sign")
    is_pinch = (gesture == "pinch")
    is_thumbs_up = (gesture == "thumbs_up")
    is_thumbs_down = (gesture == "thumbs_down")
    is_rock = (gesture == "rock_on")
    is_ok = (gesture == "ok_sign")

    # Thumb: 1, 2, 3, 4
    pts.append({"x": 0.45, "y": 0.72, "z": -0.01})
    pts.append({"x": 0.40, "y": 0.65, "z": -0.02})
    pts.append({"x": 0.35, "y": 0.58, "z": -0.02})

    if is_pinch or is_ok:
        pts.append({"x": 0.46, "y": 0.28, "z": -0.03})  # Touch index tip
    elif is_thumbs_up:
        pts.append({"x": 0.30, "y": 0.40, "z": -0.03})  # Pointing straight up
    elif is_thumbs_down:
        pts.append({"x": 0.30, "y": 0.85, "z": -0.03})  # Pointing straight down
    elif is_fist:
        pts.append({"x": 0.42, "y": 0.68, "z": 0.02})  # Tucked
    else:
        pts.append({"x": 0.25, "y": 0.50, "z": -0.03})  # Extended thumb

    # Index: 5, 6, 7, 8
    pts.append({"x": 0.46, "y": 0.55, "z": -0.01})
    pts.append({"x": 0.46, "y": 0.45, "z": -0.02})
    pts.append({"x": 0.46, "y": 0.38, "z": -0.02})
    if is_fist or is_thumbs_up or is_thumbs_down:
        pts.append({"x": 0.46, "y": 0.58, "z": 0.02})
    else:
        pts.append({"x": 0.46, "y": 0.28, "z": -0.03})

    # Middle: 9, 10, 11, 12
    pts.append({"x": 0.50, "y": 0.53, "z": 0.0})
    pts.append({"x": 0.50, "y": 0.42, "z": -0.01})
    pts.append({"x": 0.50, "y": 0.35, "z": -0.01})
    if is_fist or is_pointing or is_thumbs_up or is_thumbs_down or is_rock or is_pinch:
        pts.append({"x": 0.50, "y": 0.57, "z": 0.02})
    else:
        pts.append({"x": 0.50, "y": 0.24, "z": -0.02})

    # Ring: 13, 14, 15, 16
    pts.append({"x": 0.54, "y": 0.55, "z": 0.01})
    pts.append({"x": 0.54, "y": 0.45, "z": 0.01})
    pts.append({"x": 0.54, "y": 0.38, "z": 0.01})
    if is_fist or is_pointing or is_peace or is_thumbs_up or is_thumbs_down or is_rock or is_pinch:
        pts.append({"x": 0.54, "y": 0.58, "z": 0.02})
    else:
        pts.append({"x": 0.54, "y": 0.28, "z": -0.01})

    # Pinky: 17, 18, 19, 20
    pts.append({"x": 0.58, "y": 0.58, "z": 0.02})
    pts.append({"x": 0.58, "y": 0.49, "z": 0.02})
    pts.append({"x": 0.58, "y": 0.43, "z": 0.02})
    if is_fist or is_pointing or is_peace or is_thumbs_up or is_thumbs_down or is_pinch:
        pts.append({"x": 0.58, "y": 0.60, "z": 0.03})
    else:
        pts.append({"x": 0.58, "y": 0.35, "z": 0.0})

    return pts


class TestMCPTools(unittest.TestCase):
    """Tests individual pure-Python MCP tool computations."""

    def test_classify_open_palm(self):
        pts = make_landmarks_for_gesture("open_palm")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "open_palm")
        self.assertGreaterEqual(res["confidence"], 0.8)
        self.assertEqual(res["landmarks_count"], 21)
        self.assertTrue(res["fingers"]["index"]["extended"])
        self.assertTrue(res["fingers"]["middle"]["extended"])

    def test_classify_fist(self):
        pts = make_landmarks_for_gesture("fist")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "fist")
        self.assertGreaterEqual(res["confidence"], 0.8)
        self.assertFalse(res["fingers"]["index"]["extended"])
        self.assertFalse(res["fingers"]["middle"]["extended"])

    def test_classify_peace_sign(self):
        pts = make_landmarks_for_gesture("peace_sign")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "peace_sign")
        self.assertTrue(res["fingers"]["index"]["extended"])
        self.assertTrue(res["fingers"]["middle"]["extended"])
        self.assertFalse(res["fingers"]["ring"]["extended"])
        self.assertFalse(res["fingers"]["pinky"]["extended"])

    def test_classify_pointing_up(self):
        pts = make_landmarks_for_gesture("pointing_up")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "pointing_up")
        self.assertTrue(res["fingers"]["index"]["extended"])
        self.assertFalse(res["fingers"]["middle"]["extended"])

    def test_classify_pinch(self):
        pts = make_landmarks_for_gesture("pinch")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "pinch")
        self.assertTrue(res["pinch"]["is_pinching"])

    def test_classify_ok_sign(self):
        pts = make_landmarks_for_gesture("ok_sign")
        res = classify_gesture(pts)
        self.assertEqual(res["gesture"], "ok_sign")
        self.assertTrue(res["pinch"]["is_pinching"])

    def test_classify_thumbs_up_and_down(self):
        up = make_landmarks_for_gesture("thumbs_up")
        res_up = classify_gesture(up)
        self.assertEqual(res_up["gesture"], "thumbs_up")

        down = make_landmarks_for_gesture("thumbs_down")
        res_down = classify_gesture(down)
        self.assertEqual(res_down["gesture"], "thumbs_down")

    def test_classify_rock_on(self):
        rock = make_landmarks_for_gesture("rock_on")
        res = classify_gesture(rock)
        self.assertEqual(res["gesture"], "rock_on")
        self.assertTrue(res["fingers"]["index"]["extended"])
        self.assertTrue(res["fingers"]["pinky"]["extended"])
        self.assertFalse(res["fingers"]["middle"]["extended"])

    def test_classify_flat_array_format(self):
        pts = make_landmarks_for_gesture("open_palm")
        flat = []
        for p in pts:
            flat.extend([p["x"], p["y"], p["z"]])
        res = classify_gesture(flat)
        self.assertEqual(res["gesture"], "open_palm")

    def test_classify_insufficient_landmarks(self):
        res = classify_gesture([{"x": 0.1, "y": 0.1}])
        self.assertEqual(res["gesture"], "unknown")
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("error", res)

    def test_calculate_dwell(self):
        zone_dict = {"x": 0.2, "y": 0.2, "width": 0.4, "height": 0.4}
        zone_list = [0.2, 0.2, 0.4, 0.4]

        # In zone, halfway
        r1 = calculate_dwell(0.3, 0.3, zone_dict, duration_ms=1000.0, elapsed_ms=500.0)
        self.assertTrue(r1["in_zone"])
        self.assertEqual(r1["progress"], 0.5)
        self.assertFalse(r1["triggered"])
        self.assertEqual(r1["dwell_state"], "dwelling")
        self.assertEqual(r1["remaining_ms"], 500.0)

        # In zone, complete
        r2 = calculate_dwell(0.3, 0.3, zone_list, duration_ms=1000.0, elapsed_ms=1200.0)
        self.assertTrue(r2["in_zone"])
        self.assertEqual(r2["progress"], 1.0)
        self.assertTrue(r2["triggered"])
        self.assertEqual(r2["dwell_state"], "completed")
        self.assertEqual(r2["remaining_ms"], 0.0)

        # Outside zone
        r3 = calculate_dwell(0.9, 0.9, zone_dict, duration_ms=1000.0, elapsed_ms=500.0)
        self.assertFalse(r3["in_zone"])
        self.assertEqual(r3["progress"], 0.0)
        self.assertFalse(r3["triggered"])

    def test_classify_face(self):
        # Feature dict
        data = {
            "mouth_open_ratio": 0.6,
            "smile_score": 0.85,
            "left_ear": 0.12,
            "right_ear": 0.12,
        }
        res = classify_face(data)
        self.assertTrue(res["mouth_open"])
        self.assertTrue(res["smiling"])
        self.assertTrue(res["both_eyes_blink"])
        self.assertIn("smiling", res["expressions"])
        self.assertIn("mouth_open", res["expressions"])
        self.assertIn("both_eyes_closed", res["expressions"])

    def test_generate_action_map(self):
        for preset in ["presentation", "media", "media_player", "drawing", "gaming", "accessibility"]:
            am = generate_action_map(preset)
            self.assertIn("bindings", am)
            self.assertIn("name", am)
            self.assertGreater(len(am["bindings"]), 3)

        # Custom override
        custom = generate_action_map("presentation", overrides={"open_palm": {"action": "custom_act"}})
        self.assertEqual(custom["bindings"]["open_palm"]["action"], "custom_act")

    def test_get_diagnostics(self):
        diag = get_diagnostics(extended=True)
        self.assertEqual(diag["status"], "healthy")
        self.assertIn("system", diag)
        self.assertIn("python", diag)
        self.assertIn("hardware", diag)
        self.assertIn("telemetry", diag)
        self.assertIn("environment", diag)

    def test_generate_mcp_client_config(self):
        clients = ["claude_desktop", "cursor", "cline", "zed", "all"]
        for c in clients:
            cfg = generate_mcp_client_config(c, python_path="/usr/bin/python3")
            self.assertIsInstance(cfg, dict)
            if c == "claude_desktop":
                self.assertIn("mcpServers", cfg)
                self.assertEqual(cfg["mcpServers"]["vision-gesture-control"]["command"], "/usr/bin/python3")
            elif c == "zed":
                self.assertIn("context_servers", cfg)


class TestMCPServerProtocol(unittest.TestCase):
    """Tests JSON-RPC 2.0 MCP protocol handling."""

    def setUp(self):
        self.server = MCPServer()

    def test_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = self.server.handle_request(req)
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], PROTOCOL_VERSION)
        self.assertEqual(resp["result"]["serverInfo"]["name"], SERVER_NAME)
        self.assertEqual(resp["result"]["serverInfo"]["version"], SERVER_VERSION)

    def test_ping(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        resp = self.server.handle_request(req)
        self.assertEqual(resp["id"], 2)
        self.assertEqual(resp["result"], {})

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        resp = self.server.handle_request(req)
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 5)
        names = [t["name"] for t in tools]
        self.assertIn("vision_classify_gesture", names)
        self.assertIn("vision_calculate_dwell", names)
        self.assertIn("vision_classify_face", names)
        self.assertIn("vision_generate_action_map", names)
        self.assertIn("vision_get_diagnostics", names)

    def test_tools_call_classify(self):
        pts = make_landmarks_for_gesture("open_palm")
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "vision_classify_gesture",
                "arguments": {"landmarks": pts, "handedness": "Right"},
            },
        }
        resp = self.server.handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structured_data"]["gesture"], "open_palm")

    def test_tools_call_dwell(self):
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "vision_calculate_dwell",
                "arguments": {
                    "x": 0.5,
                    "y": 0.5,
                    "zone": {"x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6},
                    "duration_ms": 1000,
                    "elapsed_ms": 1000,
                },
            },
        }
        resp = self.server.handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        self.assertTrue(resp["result"]["structured_data"]["triggered"])

    def test_tools_call_face(self):
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "vision_classify_face",
                "arguments": {
                    "face_landmarks": {"mouth_open_ratio": 0.5, "smile_score": 0.9},
                },
            },
        }
        resp = self.server.handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        self.assertTrue(resp["result"]["structured_data"]["smiling"])

    def test_tools_call_action_map(self):
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "vision_generate_action_map",
                "arguments": {"preset": "media"},
            },
        }
        resp = self.server.handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structured_data"]["preset_id"], "media")

    def test_tools_call_diagnostics(self):
        req = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "vision_get_diagnostics",
                "arguments": {"extended": False},
            },
        }
        resp = self.server.handle_request(req)
        self.assertFalse(resp["result"]["isError"])
        self.assertEqual(resp["result"]["structured_data"]["status"], "healthy")

    def test_unknown_tool(self):
        req = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {"name": "non_existent_tool", "arguments": {}},
        }
        resp = self.server.handle_request(req)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 10, "method": "unknown_method"}
        resp = self.server.handle_request(req)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_stdio_runner(self):
        # Simulate stdio streaming with StringIO
        req_lines = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}),
        ]
        in_stream = io.StringIO("\n".join(req_lines) + "\n")
        out_stream = io.StringIO()

        self.server.run_stdio(in_stream=in_stream, out_stream=out_stream)

        output = out_stream.getvalue().strip().split("\n")
        self.assertEqual(len(output), 2)
        resp1 = json.loads(output[0])
        resp2 = json.loads(output[1])
        self.assertEqual(resp1["id"], 1)
        self.assertEqual(resp2["id"], 2)


if __name__ == "__main__":
    unittest.main()
