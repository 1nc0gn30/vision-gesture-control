"""Unit tests for compat.py (Cross-platform compatibility layer)."""

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from vision_gesture_control.compat import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    configure_utf8_streams,
    diagnostics_summary,
    from_posix_path,
    get_system_diagnostics,
    get_terminal_size,
    is_android,
    is_headless,
    is_linux,
    is_macos,
    is_termux,
    is_windows,
    is_wsl,
    open_url,
    resolve_path,
    safe_print,
    sanitize_filename,
    to_posix_path,
)


class TestStreamAndEncoding:
    """Tests for stream and encoding helpers."""

    def test_configure_utf8_streams(self):
        result = configure_utf8_streams()
        assert isinstance(result, bool)

    def test_safe_print_standard(self, capsys):
        safe_print("Hello", "World", 123)
        captured = capsys.readouterr()
        assert "Hello World 123\n" == captured.out

    def test_safe_print_unicode(self, capsys):
        unicode_str = "Vision ✨ 🖐 👁 🚀 日本語"
        safe_print(unicode_str)
        captured = capsys.readouterr()
        assert unicode_str in captured.out

    def test_safe_print_custom_stream(self):
        stream = io.StringIO()
        safe_print("Testing custom stream", file=stream)
        assert "Testing custom stream\n" == stream.getvalue()

    def test_safe_print_encoding_error_fallback(self):
        # Mock stream that raises UnicodeEncodeError on write
        class FailingStream:
            def __init__(self):
                self.encoding = "ascii"
                self.buf = ""

            def write(self, s):
                if any(ord(c) > 127 for c in s):
                    raise UnicodeEncodeError("ascii", s, 0, 1, "ordinal not in range")
                self.buf += s

            def flush(self):
                pass

        stream = FailingStream()
        safe_print("Test \u2728", file=stream)
        assert "Test" in stream.buf


class TestAtomicFileOperations:
    """Tests for atomic write utilities."""

    def test_atomic_write_bytes(self, tmp_path):
        target = tmp_path / "test.bin"
        data = b"\x00\x01\x02\xFF\xFE\xFD"
        atomic_write_bytes(target, data)

        assert target.exists()
        assert target.read_bytes() == data

    def test_atomic_write_text(self, tmp_path):
        target = tmp_path / "nested" / "dir" / "test.txt"
        text = "Hello Vision Control! 🌟\nMulti-line string"
        atomic_write_text(target, text)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == text

    def test_atomic_write_json(self, tmp_path):
        target = tmp_path / "data.json"
        payload = {
            "name": "Gesture Test",
            "threshold": 0.065,
            "tags": ["vision", "camera", "🔥"],
            "nested": {"active": True},
        }
        atomic_write_json(target, payload, indent=2)

        assert target.exists()
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded == payload

    def test_atomic_write_overwrite(self, tmp_path):
        target = tmp_path / "overwrite.txt"
        atomic_write_text(target, "Version 1")
        assert target.read_text(encoding="utf-8") == "Version 1"

        atomic_write_text(target, "Version 2")
        assert target.read_text(encoding="utf-8") == "Version 2"

    def test_atomic_write_error_cleanup(self, tmp_path):
        target = tmp_path / "fail.txt"
        with mock.patch("os.replace", side_effect=OSError("Simulated disk error")):
            with pytest.raises(OSError):
                atomic_write_text(target, "Will fail")
        # Ensure target file was not left in corrupt state
        assert not target.exists()


class TestPathConversionsAndSanitization:
    """Tests for POSIX path normalization and filename sanitization."""

    def test_to_posix_path(self):
        assert to_posix_path("C:\\Users\\neo\\project") == "C:/Users/neo/project"
        assert to_posix_path("/home/neo/vision//control") == "/home/neo/vision/control"
        assert to_posix_path("//server/share/folder") == "//server/share/folder"
        assert to_posix_path("") == ""

    def test_from_posix_path(self):
        path = "dir/subdir/file.txt"
        native = from_posix_path(path)
        if os.sep == "\\":
            assert "\\" in native
        else:
            assert "/" in native

    def test_resolve_path(self, tmp_path):
        resolved = resolve_path("relative/path", base_dir=tmp_path)
        assert to_posix_path(tmp_path) in resolved
        assert "relative/path" in resolved

    def test_sanitize_filename_standard(self):
        assert sanitize_filename("valid_name.txt") == "valid_name.txt"
        assert sanitize_filename("my file (1).png") == "my file (1).png"

    def test_sanitize_filename_illegal_chars(self):
        raw = 'file:*?<>|"name.json'
        sanitized = sanitize_filename(raw, replacement="_")
        assert "*" not in sanitized
        assert "?" not in sanitized
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "|" not in sanitized
        assert ":" not in sanitized
        assert '"' not in sanitized

    def test_sanitize_filename_reserved_windows_names(self):
        assert sanitize_filename("CON.txt").startswith("_")
        assert sanitize_filename("NUL.json").startswith("_")
        assert sanitize_filename("aux").startswith("_")

    def test_sanitize_filename_trailing_chars(self):
        assert sanitize_filename("badname... ") == "badname"

    def test_sanitize_filename_empty(self):
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

    def test_sanitize_filename_length_limit(self):
        long_name = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_name, max_length=50)
        assert len(sanitized) <= 50
        assert sanitized.endswith(".txt")


class TestRuntimeDiagnostics:
    """Tests for platform environment detection and diagnostics."""

    def test_platform_detectors_return_bool(self):
        assert isinstance(is_termux(), bool)
        assert isinstance(is_wsl(), bool)
        assert isinstance(is_android(), bool)
        assert isinstance(is_macos(), bool)
        assert isinstance(is_windows(), bool)
        assert isinstance(is_linux(), bool)
        assert isinstance(is_headless(), bool)

    def test_is_termux_environment_variable(self):
        with mock.patch.dict(os.environ, {"PREFIX": "/data/data/com.termux/files/usr"}):
            assert is_termux() is True

    def test_is_wsl_environment_variable(self):
        with mock.patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu-22.04"}):
            assert is_wsl() is True

    def test_get_terminal_size(self):
        cols, lines = get_terminal_size(default=(100, 30))
        assert isinstance(cols, int) and cols > 0
        assert isinstance(lines, int) and lines > 0

    def test_get_system_diagnostics(self):
        diag = get_system_diagnostics()
        assert "platform" in diag
        assert "python_version" in diag
        assert "cpu_count" in diag
        assert "terminal_size" in diag
        assert "is_headless" in diag
        assert "encoding" in diag

    def test_diagnostics_summary(self):
        summary = diagnostics_summary()
        assert "Vision Gesture Control: System Diagnostics" in summary
        assert "Python Version" in summary
        assert "Terminal Size" in summary


class TestBrowserOpening:
    """Tests for cross-platform browser opening utility."""

    def test_open_url_empty(self):
        assert open_url("") is False
        assert open_url(None) is False  # type: ignore

    def test_open_url_with_mocked_webbrowser(self):
        with mock.patch("webbrowser.open", return_value=True) as mock_open:
            with mock.patch("shutil.which", return_value=None):
                result = open_url("http://127.0.0.1:8088", new_tab=True)
                assert result is True
                assert mock_open.called

    def test_open_url_linux_xdg_open(self):
        with mock.patch("vision_gesture_control.compat.is_linux", return_value=True):
            with mock.patch("vision_gesture_control.compat.is_termux", return_value=False):
                with mock.patch("vision_gesture_control.compat.is_wsl", return_value=False):
                    with mock.patch("shutil.which", side_effect=lambda cmd: "/usr/bin/xdg-open" if cmd == "xdg-open" else None):
                        mock_proc = mock.MagicMock(returncode=0)
                        with mock.patch("subprocess.run", return_value=mock_proc) as mock_run:
                            result = open_url("https://github.com")
                            assert result is True
                            mock_run.assert_called_once()
