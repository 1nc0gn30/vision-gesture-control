"""
Unit tests for CLI interface in vision-gesture-control.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from vision_gesture_control.cli import build_parser, main
from vision_gesture_control.mcp_server import classify_gesture


class TestCLI(unittest.TestCase):
    """Tests CLI subcommands and argument parser."""

    def test_version_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
            self.assertEqual(cm.exception.code, 0)
        self.assertIn("vision-control 1.0.0", buf.getvalue())

    def test_help_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["--help"])
            self.assertEqual(cm.exception.code, 0)
        self.assertIn("vision-gesture-control", buf.getvalue())
        self.assertIn("serve", buf.getvalue())
        self.assertIn("classify", buf.getvalue())
        self.assertIn("dwell", buf.getvalue())
        self.assertIn("mcp", buf.getvalue())
        self.assertIn("map", buf.getvalue())
        self.assertIn("platform", buf.getvalue())

    def test_no_args_shows_help(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main([])
            self.assertEqual(ret, 0)
        self.assertIn("usage: vision-control", buf.getvalue())

    def test_classify_default_sample(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["classify"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("gesture", data)
        self.assertIn("confidence", data)
        self.assertEqual(data["gesture"], "open_palm")

    def test_classify_json_argument(self):
        # Pass JSON with 21 synthetic points
        pts = [{"x": 0.5, "y": 0.8, "z": 0.0}] * 21
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["classify", "--landmarks-json", json.dumps(pts)])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("gesture", data)
        self.assertEqual(data["landmarks_count"], 21)

    def test_classify_file_input(self):
        pts = [{"x": 0.5, "y": 0.8, "z": 0.0}] * 21
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
            json.dump(pts, tf)
            tf_path = tf.name

        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                ret = main(["classify", "--landmarks-json", tf_path])
                self.assertEqual(ret, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["landmarks_count"], 21)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_dwell_command(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main([
                "dwell",
                "--x", "0.5",
                "--y", "0.5",
                "--zone", "0.2,0.2,0.6,0.6",
                "--duration", "1000",
                "--elapsed", "500",
            ])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["in_zone"])
        self.assertEqual(data["progress"], 0.5)
        self.assertFalse(data["triggered"])

    def test_dwell_invalid_zone(self):
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            ret = main([
                "dwell",
                "--x", "0.5",
                "--y", "0.5",
                "--zone", "invalid_zone_str",
            ])
            self.assertEqual(ret, 1)

    def test_mcp_tools_flag(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["mcp", "--tools"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("tools", data)
        self.assertGreaterEqual(len(data["tools"]), 5)

    def test_mcp_config_flag(self):
        for client in ["claude", "cursor", "cline", "zed", "all"]:
            buf = io.StringIO()
            with redirect_stdout(buf):
                ret = main(["mcp", "--config", client])
                self.assertEqual(ret, 0)
            data = json.loads(buf.getvalue())
            self.assertIsInstance(data, dict)

    def test_map_command(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["map", "--preset", "media"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("bindings", data)
        self.assertEqual(data["preset_id"], "media")

    def test_map_table_format(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["map", "--preset", "presentation", "--format", "table"])
            self.assertEqual(ret, 0)
        output = buf.getvalue()
        self.assertIn("Presentation Mode", output)
        self.assertIn("GESTURE", output)
        self.assertIn("KEY / ACTION", output)

    def test_platform_command(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["platform"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "healthy")
        self.assertIn("system", data)
        self.assertIn("hardware", data)

    def test_platform_extended_command(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["platform", "--extended"])
            self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("environment", data)

    def test_internal_test_runner(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = main(["test"])
            self.assertEqual(ret, 0)

        buf_flag = io.StringIO()
        with redirect_stdout(buf_flag):
            ret_flag = main(["--test"])
            self.assertEqual(ret_flag, 0)


if __name__ == "__main__":
    unittest.main()
