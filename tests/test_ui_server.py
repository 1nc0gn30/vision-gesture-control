"""
Unit tests for UI Server and REST API endpoints in vision-gesture-control.
"""

import io
import json
import os
import shutil
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile

from vision_gesture_control.ui_server import UIServer


class TestUIServer(unittest.TestCase):
    """Tests the ThreadingHTTPServer, REST API endpoints, static assets, and bundle export."""

    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for public static files
        cls.temp_dir = tempfile.mkdtemp()
        cls.public_dir = os.path.join(cls.temp_dir, "public")
        os.makedirs(cls.public_dir, exist_ok=True)

        # Bind to port 0 so the OS assigns an available ephemeral port
        cls.server = UIServer(host="127.0.0.1", port=0, public_dir=cls.public_dir)
        cls.server.start()
        cls.base_url = cls.server.get_url()
        # Give server a moment to start
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)

    def _http_get(self, path: str):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read()

    def _http_post(self, path: str, json_data: dict = None, raw_body: bytes = None, headers: dict = None):
        url = f"{self.base_url}{path}"
        if raw_body is not None:
            body = raw_body
        elif json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
        else:
            body = b"{}"

        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read()

    def test_health_endpoint(self):
        status, headers, body = self._http_get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["service"], "vision-gesture-control")
        self.assertGreaterEqual(data["uptime_seconds"], 0.0)

    def test_classify_endpoint(self):
        # 21 synthetic landmarks
        pts = [{"x": 0.5, "y": 0.8, "z": 0.0}] * 21
        status, headers, body = self._http_post("/api/classify", json_data={
            "landmarks": pts,
            "handedness": "Right",
        })
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("gesture", data)
        self.assertIn("confidence", data)
        self.assertEqual(data["handedness"], "Right")

    def test_dwell_endpoint(self):
        status, headers, body = self._http_post("/api/dwell", json_data={
            "x": 0.5,
            "y": 0.5,
            "zone": {"x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6},
            "duration_ms": 1000.0,
            "elapsed_ms": 750.0,
        })
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["in_zone"])
        self.assertEqual(data["progress"], 0.75)
        self.assertFalse(data["triggered"])
        self.assertEqual(data["remaining_ms"], 250.0)

    def test_face_endpoint(self):
        status, headers, body = self._http_post("/api/face", json_data={
            "face_landmarks": {
                "mouth_open_ratio": 0.55,
                "smile_score": 0.88,
                "left_ear": 0.15,
                "right_ear": 0.15,
            }
        })
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["mouth_open"])
        self.assertTrue(data["smiling"])
        self.assertTrue(data["both_eyes_blink"])

    def test_presets_endpoint(self):
        # All presets
        status, headers, body = self._http_get("/api/presets")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("presentation", data)
        self.assertIn("media", data)
        self.assertIn("drawing", data)
        self.assertIn("gaming", data)
        self.assertIn("accessibility", data)

        # Single preset query
        status2, _, body2 = self._http_get("/api/presets?preset=media")
        self.assertEqual(status2, 200)
        data2 = json.loads(body2.decode("utf-8"))
        self.assertEqual(data2["preset_id"], "media")

    def test_mcp_config_endpoint(self):
        status, headers, body = self._http_get("/api/mcp/config?client=cursor")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("mcpServers", data)
        self.assertIn("vision-gesture-control", data["mcpServers"])

    def test_diagnostics_endpoint(self):
        status, headers, body = self._http_get("/api/diagnostics")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertIn("system", data)
        self.assertIn("python", data)
        self.assertIn("hardware", data)

    def test_export_bundle_endpoint(self):
        status, headers, body = self._http_post("/api/export-bundle")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/zip")
        self.assertIn("attachment", headers.get("Content-Disposition", ""))

        # Verify ZIP archive contents
        with zipfile.ZipFile(io.BytesIO(body), "r") as zf:
            file_list = zf.namelist()
            self.assertIn("index.html", file_list)
            self.assertIn("manifest.json", file_list)
            self.assertIn("action_maps.json", file_list)
            self.assertIn("mcp_configs.json", file_list)
            self.assertIn("README.md", file_list)

            # Validate json files in zip
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            self.assertIn("name", manifest)

            maps = json.loads(zf.read("action_maps.json").decode("utf-8"))
            self.assertIn("presentation", maps)

    def test_fallback_index_html(self):
        status, headers, body = self._http_get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        html_str = body.decode("utf-8")
        self.assertIn("Vision Studio", html_str)
        self.assertIn("Live Vision Gesture Tracking", html_str)

    def test_custom_static_file_serving(self):
        # Create a custom file in public dir
        test_file_path = os.path.join(self.public_dir, "test_asset.txt")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("Hello Material 3 Vision Studio!")

        status, headers, body = self._http_get("/test_asset.txt")
        self.assertEqual(status, 200)
        self.assertEqual(body.decode("utf-8"), "Hello Material 3 Vision Studio!")

    def test_404_not_found(self):
        try:
            self._http_get("/non_existent_page.html")
            self.fail("Expected HTTPError 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)
            err_data = json.loads(e.read().decode("utf-8"))
            self.assertIn("error", err_data)

    def test_options_cors(self):
        url = f"{self.base_url}/api/classify"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))


if __name__ == "__main__":
    unittest.main()
