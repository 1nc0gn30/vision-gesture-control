"""Tests for Google Vision Studio UI, Production Examples, MCP Configs, CI Workflows & Docs."""

import json
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPublicIndexHtml:
    """Test suite for public/index.html Google Material 3 Light Mode UI."""

    @pytest.fixture
    def html_content(self) -> str:
        html_path = REPO_ROOT / "public" / "index.html"
        assert html_path.exists(), f"File {html_path} does not exist"
        content = html_path.read_text(encoding="utf-8")
        assert len(content) > 500, "public/index.html is unexpectedly small"
        return content

    def test_doctype_and_title(self, html_content: str):
        assert "<!DOCTYPE html>" in html_content or "<!doctype html>" in html_content
        assert "<title>" in html_content
        assert "Google Vision Studio" in html_content

    def test_material3_google_palette(self, html_content: str):
        # Verify Google Material 3 color tokens
        expected_colors = ["#1a73e8", "#1e8e3e", "#f9ab00", "#d93025", "#9334e6"]
        for color in expected_colors:
            assert color in html_content, f"Missing expected Google color token {color}"

    def test_system_fonts_and_no_tracking(self, html_content: str):
        # Ensure offline system font stack is specified
        assert "Roboto" in html_content or "system-ui" in html_content or "Segoe UI" in html_content
        # Ensure zero external CDN font/cookie tracking scripts
        assert "fonts.googleapis.com" not in html_content
        assert "google-analytics.com" not in html_content
        assert "googletagmanager.com" not in html_content

    def test_four_interactive_workspace_tabs(self, html_content: str):
        assert "tab-presentation" in html_content
        assert "tab-drawing" in html_content
        assert "tab-telemetry" in html_content
        assert "tab-mcp" in html_content

    def test_hud_elements_and_canvas(self, html_content: str):
        assert "visionCanvas" in html_content
        assert "webcamVideo" in html_content
        assert "fpsBadge" in html_content or "fpsValue" in html_content
        assert "activeGestureBadge" in html_content or "activeGestureName" in html_content
        assert "dwell" in html_content.lower()

    def test_virtual_hand_simulator(self, html_content: str):
        assert "Virtual Hand Simulator" in html_content or "simulator" in html_content.lower()
        assert "OPEN_PALM" in html_content
        assert "PINCH" in html_content
        assert "POINTING_INDEX" in html_content
        assert "FIST" in html_content

    def test_sensitivity_sliders(self, html_content: str):
        assert "rangeDetConf" in html_content
        assert "rangeDwellTime" in html_content
        assert "rangeSwipeVel" in html_content
        assert "rangeSmoothing" in html_content


class TestPresentationControllerExample:
    """Test suite for examples/presentation-controller/."""

    def test_presentation_files_exist(self):
        html_file = REPO_ROOT / "examples" / "presentation-controller" / "index.html"
        readme_file = REPO_ROOT / "examples" / "presentation-controller" / "README.md"
        assert html_file.exists(), f"Missing {html_file}"
        assert readme_file.exists(), f"Missing {readme_file}"

    def test_presentation_html_features(self):
        html_content = (REPO_ROOT / "examples" / "presentation-controller" / "index.html").read_text(encoding="utf-8")
        assert "Touchless Presentation Controller" in html_content
        assert "laserDot" in html_content or "laserPointer" in html_content
        assert "slide" in html_content.lower()
        assert "camera" in html_content.lower() or "webcam" in html_content.lower()

    def test_presentation_readme(self):
        readme_content = (REPO_ROOT / "examples" / "presentation-controller" / "README.md").read_text(encoding="utf-8")
        assert "Touchless Presentation Controller" in readme_content
        assert "Gesture Reference" in readme_content or "gesture" in readme_content.lower()


class TestAirDrawingAppExample:
    """Test suite for examples/air-drawing-app/."""

    def test_air_drawing_files_exist(self):
        html_file = REPO_ROOT / "examples" / "air-drawing-app" / "index.html"
        readme_file = REPO_ROOT / "examples" / "air-drawing-app" / "README.md"
        assert html_file.exists(), f"Missing {html_file}"
        assert readme_file.exists(), f"Missing {readme_file}"

    def test_air_drawing_html_features(self):
        html_content = (REPO_ROOT / "examples" / "air-drawing-app" / "index.html").read_text(encoding="utf-8")
        assert "Air-Drawing" in html_content
        assert "paintCanvas" in html_content or "drawingCanvas" in html_content
        assert "swatch" in html_content.lower() or "color" in html_content.lower()
        assert "pinch" in html_content.lower()

    def test_air_drawing_readme(self):
        readme_content = (REPO_ROOT / "examples" / "air-drawing-app" / "README.md").read_text(encoding="utf-8")
        assert "Air-Drawing" in readme_content
        assert "Pinch" in readme_content


class TestMcpClientConfigs:
    """Test suite for examples/mcp-clients/."""

    @pytest.mark.parametrize(
        "filename,root_key",
        [
            ("claude_desktop_config.json", "mcpServers"),
            ("cursor_mcp.json", "mcpServers"),
            ("cline_mcp.json", "mcpServers"),
            ("zed_settings.json", "context_servers"),
        ],
    )
    def test_mcp_json_validity(self, filename: str, root_key: str):
        config_path = REPO_ROOT / "examples" / "mcp-clients" / filename
        assert config_path.exists(), f"Config file {config_path} missing"

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert root_key in data, f"Expected key '{root_key}' in {filename}"
        server_conf = data[root_key]["vision-gesture-control"]
        assert server_conf is not None

        # Verify command and arguments
        if "command" in server_conf:
            if isinstance(server_conf["command"], dict):
                assert server_conf["command"]["path"] == "python"
                assert "-m" in server_conf["command"]["args"]
                assert "vision_gesture_control.mcp" in server_conf["command"]["args"]
            else:
                assert server_conf["command"] == "python"
                assert "-m" in server_conf["args"]
                assert "vision_gesture_control.mcp" in server_conf["args"]

    def test_mcp_clients_readme(self):
        readme_path = REPO_ROOT / "examples" / "mcp-clients" / "README.md"
        assert readme_path.exists()
        content = readme_path.read_text(encoding="utf-8")
        assert "Claude Desktop" in content
        assert "Cursor IDE" in content
        assert "Cline" in content
        assert "Zed Editor" in content


class TestTopLevelExamplesIndex:
    """Test suite for examples/README.md."""

    def test_examples_readme_index(self):
        readme_path = REPO_ROOT / "examples" / "README.md"
        assert readme_path.exists()
        content = readme_path.read_text(encoding="utf-8")
        assert "presentation-controller" in content
        assert "air-drawing-app" in content
        assert "mcp-clients" in content
        assert "Architecture" in content or "Flow" in content


class TestCiCdWorkflows:
    """Test suite for .github/workflows CI/CD pipelines."""

    def test_ci_workflow_yaml_and_matrix(self):
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists(), f"Missing {ci_path}"

        with open(ci_path, "r", encoding="utf-8") as f:
            ci_data = yaml.safe_load(f)

        assert "jobs" in ci_data
        test_job = ci_data["jobs"]["test-matrix"]
        matrix = test_job["strategy"]["matrix"]

        os_list = matrix["os"]
        python_list = matrix["python-version"]

        assert len(os_list) == 3, f"Expected 3 OS, found {len(os_list)}"
        assert "ubuntu-latest" in os_list
        assert "macos-latest" in os_list
        assert "windows-latest" in os_list

        assert len(python_list) == 5, f"Expected 5 Python versions, found {len(python_list)}"
        for py_ver in ["3.9", "3.10", "3.11", "3.12", "3.13"]:
            assert py_ver in python_list, f"Missing Python {py_ver} in CI matrix"

        # Total matrix combinations = 3 * 5 = 15
        total_matrix_combinations = len(os_list) * len(python_list)
        assert total_matrix_combinations == 15

    def test_release_workflow_yaml(self):
        release_path = REPO_ROOT / ".github" / "workflows" / "release.yml"
        assert release_path.exists(), f"Missing {release_path}"

        with open(release_path, "r", encoding="utf-8") as f:
            rel_data = yaml.safe_load(f)

        assert "jobs" in rel_data
        build_job = rel_data["jobs"]["build-and-release"]
        steps = build_job["steps"]

        step_names = [s.get("name", "") for s in steps]
        assert any("Build Source Distribution" in name for name in step_names)
        assert any("Generate SHA-256 Checksums" in name for name in step_names)
        assert any("Create GitHub Release" in name for name in step_names)


class TestDocumentationCompleteness:
    """Test suite for docs/ and root README.md."""

    def test_root_readme(self):
        readme_path = REPO_ROOT / "README.md"
        assert readme_path.exists()
        content = readme_path.read_text(encoding="utf-8")
        assert "Vision Gesture Control" in content
        assert "Model Context Protocol" in content
        assert "Sub-15ms Latency" in content
        assert "Quick Start" in content
        assert "MIT License" in content

    def test_gesture_recognition_guide(self):
        guide_path = REPO_ROOT / "docs" / "GESTURE_RECOGNITION_GUIDE.md"
        assert guide_path.exists()
        content = guide_path.read_text(encoding="utf-8")
        assert "21 three-dimensional landmarks" in content or "21" in content
        assert "OneEuro" in content or "1€" in content
        assert "Eye Aspect Ratio" in content
        assert "Mouth Aspect Ratio" in content
        assert "BaseGestureRecognizer" in content or "calculate_joint_angle" in content

    def test_mcp_guide(self):
        mcp_guide_path = REPO_ROOT / "docs" / "MCP_GUIDE.md"
        assert mcp_guide_path.exists()
        content = mcp_guide_path.read_text(encoding="utf-8")
        assert "get_active_gesture" in content
        assert "get_hand_landmarks" in content
        assert "trigger_key_event" in content
        assert "capture_frame_telemetry" in content
        assert "Claude Desktop" in content

    def test_camera_security_privacy_guide(self):
        sec_path = REPO_ROOT / "docs" / "CAMERA_SECURITY_PRIVACY.md"
        assert sec_path.exists()
        content = sec_path.read_text(encoding="utf-8")
        assert "In-Memory" in content
        assert "Zero Cloud" in content
        assert "GDPR" in content
        assert "Security Audit Checklist" in content
