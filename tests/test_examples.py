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
        assert "Vision Studio" in html_content

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


class TestToolAirDrawingJs:
    """Test suite for public/js/tool-air-drawing.js modular extension."""

    @pytest.fixture
    def script_content(self) -> str:
        script_path = REPO_ROOT / "public" / "js" / "tool-air-drawing.js"
        assert script_path.exists(), f"Missing {script_path}"
        content = script_path.read_text(encoding="utf-8")
        assert len(content) > 500, "tool-air-drawing.js is unexpectedly small"
        return content

    def test_file_exists_and_syntax_valid(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-air-drawing.js"
        cmd = ["node", "-e", f'new Function(require("fs").readFileSync("{script_path}", "utf-8"))']
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"JS syntax check failed: {res.stderr}"

    def test_attaches_to_vision_app(self, script_content: str):
        assert "VisionApp.tools.airDrawing" in script_content or "VisionApp.tools['airDrawing']" in script_content
        assert "VisionApp.tools = VisionApp.tools || {}" in script_content

    def test_smoothed_fingertip_reticle_kinematics(self, script_content: str):
        assert "updateSmoothedFingertip" in script_content
        assert "minSmoothingAlpha" in script_content
        assert "velocityDamping" in script_content
        assert "deadzoneThreshold" in script_content
        assert "drawing-cursor-hover" in script_content
        assert "drawing-cursor-drawing" in script_content

    def test_natural_drawing_pipeline(self, script_content: str):
        assert "quadraticCurveTo" in script_content
        assert "velocityScale" in script_content or "velocity" in script_content
        assert "renderSplineSegment" in script_content or "quadratic" in script_content

    def test_brush_sizes_and_swatches(self, script_content: str):
        assert "brushSizes" in script_content
        assert "fine" in script_content and "medium" in script_content and "broad" in script_content and "chisel" in script_content
        assert "setColor" in script_content
        assert "setBrushSize" in script_content

    def test_open_palm_hold_clear_and_audio(self, script_content: str):
        assert "palmHoldThresholdMs: 350" in script_content or "350" in script_content
        assert "OPEN_PALM" in script_content
        assert "clearCanvas" in script_content
        assert "playClearChime" in script_content or "playClearChimeCue" in script_content

    def test_undo_and_png_export(self, script_content: str):
        assert "undoStroke" in script_content or "undo" in script_content
        assert "exportHighResPNG" in script_content or "exportPNG" in script_content
        assert "toDataURL('image/png')" in script_content

    def test_workspace_isolation(self, script_content: str):
        assert "tab-drawing" in script_content
        assert "manualFilterLockTime" in script_content

    def test_node_execution_interface(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-air-drawing.js"
        node_code = f"""
        const tool = require('{script_path}');
        const cfg = tool.getConfig();
        if (cfg.palmHoldThresholdMs !== 350) process.exit(1);
        if (cfg.brushSizes.fine !== 4 || cfg.brushSizes.chisel !== 28) process.exit(2);
        const sm = tool.updateSmoothedFingertip(0.5, 0.5, 100);
        if (typeof sm.x !== 'number' || typeof sm.y !== 'number') process.exit(3);
        console.log('SUCCESS');
        """
        res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True)
        assert res.returncode == 0, f"Node execution test failed: {res.stderr}"



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


class TestGestureFxToolExtension:
    """Test suite for public/js/tool-gesturefx.js Gesture FX Studio & Touchless Macropad."""

    @pytest.fixture
    def script_content(self) -> str:
        script_path = REPO_ROOT / "public" / "js" / "tool-gesturefx.js"
        assert script_path.exists(), f"File {script_path} does not exist"
        content = script_path.read_text(encoding="utf-8")
        assert len(content) > 1000, "public/js/tool-gesturefx.js is unexpectedly small"
        return content

    def test_script_syntax_with_node(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-gesturefx.js"
        cmd = ["node", "-e", f'new Function(require("fs").readFileSync("{script_path}", "utf-8"))']
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Node syntax error in tool-gesturefx.js: {res.stderr}"

    def test_spell_particle_emitters(self, script_content: str):
        # Fireball, Cryo Frost, Tesla Arc Lightning, Grav Repulsor, Chrono Time Echoes
        assert "fireball" in script_content.lower()
        assert "cryo" in script_content.lower()
        assert "lightning" in script_content.lower()
        assert "repulsor" in script_content.lower()
        assert "chrono" in script_content.lower() or "bullet_time" in script_content.lower()
        assert "particles" in script_content.lower()

    def test_posture_triggering(self, script_content: str):
        # Open palm charging, index finger aiming/casting, two-hand shockwave bursts
        assert "OPEN_PALM" in script_content
        assert "POINTING_INDEX" in script_content
        assert "charging" in script_content.lower()
        assert "aiming" in script_content.lower()
        assert "shockwave" in script_content.lower()

    def test_dj_audio_filter_engine(self, script_content: str):
        # BiquadFilterNode Low-Pass filter, 200 Hz - 12000 Hz, 0.5 - 15.0 Q, analyser
        assert "BiquadFilter" in script_content or "biquad" in script_content.lower()
        assert "lowpass" in script_content.lower()
        assert "analyser" in script_content.lower()
        assert "12000" in script_content or "12,000" in script_content
        assert "cutoff" in script_content.lower()
        assert "resonance" in script_content.lower()

    def test_touchless_macropad(self, script_content: str):
        # Collision detection, hover glow, dwell/trigger
        assert "macropad" in script_content.lower()
        assert "hover" in script_content.lower()
        assert "bullet_time" in script_content.lower()
        assert "snapshot" in script_content.lower()
        assert "reset_all" in script_content.lower() or "clear" in script_content.lower()

    def test_vision_app_attachment(self, script_content: str):
        assert "VisionApp" in script_content
        assert "gestureFx" in script_content
        assert "castSpell" in script_content
        assert "executeMacroAction" in script_content


class TestPresentationSpatialToolExtension:
    """Test suite for public/js/tool-presentation-spatial.js Touchless Presentation & 3D Spatial Portal."""

    @pytest.fixture
    def script_content(self) -> str:
        script_path = REPO_ROOT / "public" / "js" / "tool-presentation-spatial.js"
        assert script_path.exists(), f"File {script_path} does not exist"
        content = script_path.read_text(encoding="utf-8")
        assert len(content) > 1000, "public/js/tool-presentation-spatial.js is unexpectedly small"
        return content

    def test_script_syntax_with_node(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-presentation-spatial.js"
        cmd = ["node", "-e", f'new Function(require("fs").readFileSync("{script_path}", "utf-8"))']
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Node syntax error in tool-presentation-spatial.js: {res.stderr}"

    def test_presentation_controller_features(self, script_content: str):
        # Laser reticle, motion trail canvas, dwell ring, bounding box hit testing
        assert "presMotionTrailCanvas" in script_content
        assert "laserPointer" in script_content
        assert "dwell" in script_content.lower()
        assert "presDwellCircle" in script_content or "dwellCircleEl" in script_content
        assert "getBoundingClientRect" in script_content
        assert "SWIPE_RIGHT" in script_content
        assert "SWIPE_LEFT" in script_content
        assert "FIST" in script_content
        assert "goToSlide" in script_content
        assert "nextSlide" in script_content
        assert "prevSlide" in script_content

    def test_3d_spatial_portal_features(self, script_content: str):
        # WebGL Three.js core, zero-dimension safe handling, two-hand span zoom, pinch roll
        assert "THREE" in script_content
        assert "WebGLRenderer" in script_content
        assert "ResizeObserver" in script_content or "handleResize" in script_content
        assert "multiHandLandmarks" in script_content
        assert "spanInter" in script_content or "targetScale" in script_content
        assert "lerp" in script_content.lower() or "targetScale" in script_content
        assert "rotation" in script_content

    def test_all_five_shape_geometries(self, script_content: str):
        # Icosahedron, TorusKnot, Dodecahedron, Octahedron, Sphere
        for shape in ["Icosahedron", "TorusKnot", "Dodecahedron", "Octahedron", "Sphere"]:
            assert shape in script_content, f"Missing shape geometry: {shape}"

    def test_neon_color_palettes(self, script_content: str):
        # Quantum Cyan, Solar Amber, Matrix Emerald, Hyper Ruby, Cosmic Violet, Electric Plasma
        for palette in ["Quantum Cyan", "Solar Amber", "Matrix Emerald", "Hyper Ruby", "Cosmic Violet", "Electric Plasma"]:
            assert palette in script_content, f"Missing neon palette: {palette}"

    def test_vision_app_attachment(self, script_content: str):
        assert "VisionApp" in script_content
        assert "presentationSpatial" in script_content
        assert "updatePresentation" in script_content
        assert "updateSpatial" in script_content
        assert "cycleShape" in script_content
        assert "cyclePalette" in script_content
        assert "resetSpatial" in script_content


class TestPlaygroundLensToolExtension:
    """Test suite for public/js/tool-playground-lens.js Vision Playground & Dual-Hand Filter Lens."""

    @pytest.fixture
    def script_content(self) -> str:
        script_path = REPO_ROOT / "public" / "js" / "tool-playground-lens.js"
        assert script_path.exists(), f"File {script_path} does not exist"
        content = script_path.read_text(encoding="utf-8")
        assert len(content) > 1000, "public/js/tool-playground-lens.js is unexpectedly small"
        return content

    def test_script_syntax_with_node(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-playground-lens.js"
        cmd = ["node", "-e", f'new Function(require("fs").readFileSync("{script_path}", "utf-8"))']
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Node syntax error in tool-playground-lens.js: {res.stderr}"

    def test_deadzone_and_ema_smoothing(self, script_content: str):
        assert "DEADZONE_PX" in script_content or "deadzone" in script_content.lower()
        assert "EMA_ALPHA" in script_content or "ema" in script_content.lower()
        assert "applyEmaDeadzone" in script_content

    def test_rock_solid_sticky_lock_state(self, script_content: str):
        assert "locked" in script_content
        assert "active" in script_content
        assert "mode" in script_content
        assert "isPointNearLens" in script_content
        assert "dragAnchor" in script_content

    def test_isolated_lens_filter(self, script_content: str):
        assert "lensFilter" in script_content
        assert "renderShaderFilter" in script_content
        assert "renderRoiLensFrame" in script_content
        assert "cycleLensFilter" in script_content
        assert "VICTORY_PEACE" in script_content

    def test_playground_overlays_support(self, script_content: str):
        for overlay in ["drawn_portal", "theremin", "air_drums", "physics", "gesture_wheel"]:
            assert overlay in script_content, f"Missing overlay support for {overlay}"

    def test_node_execution_interface(self):
        import subprocess
        script_path = REPO_ROOT / "public" / "js" / "tool-playground-lens.js"
        node_code = f"""
        const tool = require('{script_path}');
        if (tool.name !== 'playgroundLens') process.exit(1);
        if (typeof tool.applyEmaDeadzone !== 'function') process.exit(2);
        // Test zero jitter in deadzone
        const val1 = tool.applyEmaDeadzone(100, 102, 0.24, 4.0);
        if (val1 !== 100) process.exit(3);
        const val2 = tool.applyEmaDeadzone(100, 98, 0.24, 4.0);
        if (val2 !== 100) process.exit(4);
        // Test smooth movement outside deadzone
        const val3 = tool.applyEmaDeadzone(100, 120, 0.24, 4.0);
        if (val3 <= 100 || val3 >= 120) process.exit(5);
        console.log('PLAYGROUND_LENS_SUCCESS');
        """
        res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True)
        assert res.returncode == 0, f"Node execution test failed: {res.stderr}"
        assert "PLAYGROUND_LENS_SUCCESS" in res.stdout



