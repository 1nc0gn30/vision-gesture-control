"""Unit tests for filter_pipeline.py (Frame Filters, PixelBuffer, and Composable Filter Pipeline)."""

import math
from typing import List, Tuple

import pytest

from vision_gesture_control.filter_pipeline import (
    FilterPipeline,
    FilterStep,
    PixelBuffer,
    ThermalColorMap,
    box_blur,
    cyber_matrix_scanlines,
    grayscale_to_rgb,
    invert_colors,
    neon_contour_mapping,
    rgb_to_grayscale,
    sobel_edge_detection,
    thermal_false_color,
)


class TestPixelBufferAndConversions:
    """Tests for PixelBuffer data structure and format conversion utilities."""

    def test_create_empty_and_get_set_pixel(self):
        buf = PixelBuffer.create_empty(width=10, height=10, channels=3, fill=0)
        assert buf.width == 10
        assert buf.height == 10
        assert buf.channels == 3
        assert len(buf.data) == 300

        # Set & Get pixel
        buf.set_pixel(5, 5, (255, 128, 64))
        assert buf.get_pixel(5, 5) == (255, 128, 64)

        # Boundary clamping
        assert buf.get_pixel(-1, -1) == buf.get_pixel(0, 0)
        assert buf.get_pixel(20, 20) == buf.get_pixel(9, 9)

    def test_buffer_size_mismatch_raises(self):
        with pytest.raises(ValueError):
            PixelBuffer(data=bytearray(10), width=10, height=10, channels=3)

    def test_matrix_roundtrip_rgb(self):
        matrix: List[List[Tuple[int, int, int]]] = [
            [(255, 0, 0), (0, 255, 0)],
            [(0, 0, 255), (255, 255, 255)],
        ]
        buf = PixelBuffer.from_matrix(matrix)
        assert buf.width == 2
        assert buf.height == 2
        assert buf.channels == 3

        restored = buf.to_matrix()
        assert restored == matrix

    def test_matrix_roundtrip_grayscale(self):
        matrix_gray = [
            [0, 128],
            [200, 255],
        ]
        buf = PixelBuffer.from_matrix(matrix_gray)
        assert buf.width == 2
        assert buf.height == 2
        assert buf.channels == 1

        restored = buf.to_matrix()
        assert restored == matrix_gray

    def test_rgb_to_grayscale_and_back(self):
        # Pure White (255, 255, 255) -> Luminance 255
        # Pure Black (0, 0, 0) -> Luminance 0
        raw_rgb = bytes([255, 255, 255, 0, 0, 0])
        rgb_buf = PixelBuffer.from_bytes(raw_rgb, width=2, height=1, channels=3)

        gray_buf = rgb_to_grayscale(rgb_buf)
        assert gray_buf.channels == 1
        assert gray_buf.data[0] == 255
        assert gray_buf.data[1] == 0

        rgb_restored = grayscale_to_rgb(gray_buf)
        assert rgb_restored.channels == 3
        assert rgb_restored.get_pixel(0, 0) == (255, 255, 255)
        assert rgb_restored.get_pixel(1, 0) == (0, 0, 0)


class TestSobelEdgeDetection:
    """Tests for Sobel spatial convolution gradient edge detector."""

    def test_vertical_edge_detection(self):
        # Create a 6x6 image with sharp vertical boundary (left half black, right half white)
        w, h = 6, 6
        matrix = []
        for y in range(h):
            row = []
            for x in range(w):
                row.append((0, 0, 0) if x < 3 else (255, 255, 255))
            matrix.append(row)

        buf = PixelBuffer.from_matrix(matrix)
        edges = sobel_edge_detection(buf, threshold=50, return_rgb=False)

        # Center columns (x=2 or x=3) should have strong edge magnitudes
        assert edges.data[2 * w + 2] > 100 or edges.data[2 * w + 3] > 100
        # Far edges should be 0
        assert edges.data[2 * w + 0] == 0

    def test_horizontal_edge_detection(self):
        # Create a 6x6 image with sharp horizontal boundary (top half black, bottom half white)
        w, h = 6, 6
        matrix = []
        for y in range(h):
            row = []
            for x in range(w):
                row.append((0, 0, 0) if y < 3 else (255, 255, 255))
            matrix.append(row)

        buf = PixelBuffer.from_matrix(matrix)
        edges = sobel_edge_detection(buf, threshold=50, return_rgb=False)

        # Center rows (y=2 or y=3) should show strong edge response
        assert edges.data[2 * w + 3] > 100 or edges.data[3 * w + 3] > 100

    def test_flat_image_no_edges(self):
        # Uniform gray image should produce 0 edge magnitude
        buf = PixelBuffer.create_empty(width=10, height=10, channels=3, fill=128)
        edges = sobel_edge_detection(buf, threshold=10, return_rgb=False)
        assert all(val == 0 for val in edges.data)

    def test_colored_edge_rgb_output(self):
        # Image with edge
        matrix = [[(0, 0, 0)] * 5 + [(255, 255, 255)] * 5 for _ in range(10)]
        buf = PixelBuffer.from_matrix(matrix)

        edge_color = (0, 255, 0)  # Pure Green
        bg_color = (20, 0, 0)    # Dark Red
        out = sobel_edge_detection(
            buf,
            threshold=50,
            edge_color=edge_color,
            bg_color=bg_color,
            return_rgb=True,
        )
        assert out.channels == 3
        # Background pixel should be dark red
        assert out.get_pixel(0, 0) == bg_color


class TestThermalFalseColorMapping:
    """Tests for thermal false-color palette simulation and lookups."""

    @pytest.mark.parametrize("cmap", [
        ThermalColorMap.IRONBOW,
        ThermalColorMap.RAINBOW,
        ThermalColorMap.JET,
        ThermalColorMap.HOT_METAL,
        ThermalColorMap.CYBERPUNK,
        ThermalColorMap.ARCTIC,
    ])
    def test_thermal_palettes_generate_valid_rgb(self, cmap):
        # Gradient ramp from 0 to 255
        ramp_data = bytearray(range(256))
        buf = PixelBuffer.from_bytes(ramp_data, width=16, height=16, channels=1)

        thermal = thermal_false_color(buf, colormap=cmap)
        assert thermal.channels == 3
        assert thermal.width == 16
        assert thermal.height == 16
        assert len(thermal.data) == 16 * 16 * 3

    def test_thermal_monotonicity(self):
        # In ironbow, black (0) should map to black/near-black (0, 0, 0),
        # while 255 maps to bright white (255, 255, 255)
        buf = PixelBuffer.from_bytes(bytes([0, 255]), width=2, height=1, channels=1)
        thermal = thermal_false_color(buf, colormap="ironbow")

        p_cold = thermal.get_pixel(0, 0)
        p_hot = thermal.get_pixel(1, 0)

        assert sum(p_cold) < 50  # very dark
        assert sum(p_hot) > 700  # near white

    def test_auto_gain_contrast_stretching(self):
        # Low contrast input (values 100 to 110)
        data = bytearray([100, 105, 110, 105])
        buf = PixelBuffer.from_bytes(data, width=2, height=2, channels=1)

        normal = thermal_false_color(buf, auto_gain=False)
        gained = thermal_false_color(buf, auto_gain=True)

        # Gained output should stretch across full colormap (first pixel cold, third pixel hot)
        assert gained.get_pixel(0, 0) != gained.get_pixel(1, 0)


class TestNeonContourMapping:
    """Tests for neon contour highlight and colored contour overlay."""

    def test_neon_contour_highlight(self):
        # Image with rectangle in center
        matrix = [[(0, 0, 0)] * 12 for _ in range(12)]
        for y in range(3, 9):
            for x in range(3, 9):
                matrix[y][x] = (200, 200, 200)

        buf = PixelBuffer.from_matrix(matrix)
        neon_color = (0, 255, 240)
        out = neon_contour_mapping(buf, neon_color=neon_color, edge_threshold=20)

        assert out.channels == 3
        assert out.width == 12
        assert out.height == 12
        # Center of rectangle (flat area) should be dimmed
        p_center = out.get_pixel(5, 5)
        assert p_center[0] < 100

        # Edge of rectangle (x=3, y=5) should have strong neon cyan component
        p_edge = out.get_pixel(3, 5)
        assert p_edge[1] > 100 or p_edge[2] > 100


class TestCyberMatrixScanlineSimulator:
    """Tests for CRT scanlines, tinting, and vignette overlay."""

    def test_scanline_darkening_periodic(self):
        # Uniform white image
        buf = PixelBuffer.create_empty(width=10, height=10, channels=3, fill=200)
        out = cyber_matrix_scanlines(
            buf,
            line_spacing=2,
            scanline_darken=0.5,
            tint_mode="none",
            vignette=False,
            phase_offset=0,
        )

        # Even rows (0, 2, 4...) should be darkened by ~50%
        # Odd rows (1, 3, 5...) should be unattenuated (200)
        row0_val = out.get_pixel(5, 0)[0]
        row1_val = out.get_pixel(5, 1)[0]
        assert row0_val < row1_val
        assert row0_val == pytest.approx(100, abs=5)
        assert row1_val == pytest.approx(200, abs=5)

    def test_matrix_green_tint(self):
        buf = PixelBuffer.create_empty(width=10, height=10, channels=3, fill=150)
        out = cyber_matrix_scanlines(buf, tint_mode="green", vignette=False)

        p = out.get_pixel(5, 1)  # non-scanline row
        # Green channel should dominate
        assert p[1] > p[0] and p[1] > p[2]

    def test_vignette_darkening_at_corners(self):
        buf = PixelBuffer.create_empty(width=20, height=20, channels=3, fill=200)
        out = cyber_matrix_scanlines(buf, tint_mode="none", vignette=True, scanline_darken=1.0)

        center_pixel = out.get_pixel(10, 10)
        corner_pixel = out.get_pixel(0, 0)

        # Corner should be significantly darker than center due to vignette
        assert corner_pixel[0] < center_pixel[0]


class TestUtilityFilters:
    """Tests for Box Blur and Invert filters."""

    def test_box_blur_smoothing(self):
        # Impulse spike in center
        buf = PixelBuffer.create_empty(width=5, height=5, channels=1, fill=0)
        buf.set_pixel(2, 2, 255)

        blurred = box_blur(buf, radius=1)
        # Center should be smoothed down, neighbors should have non-zero value
        assert blurred.get_pixel(2, 2)[0] < 255
        assert blurred.get_pixel(2, 1)[0] > 0
        assert blurred.get_pixel(1, 2)[0] > 0

    def test_invert_colors(self):
        buf = PixelBuffer.from_bytes(bytes([0, 100, 255]), width=3, height=1, channels=1)
        inv = invert_colors(buf)
        assert inv.data[0] == 255
        assert inv.data[1] == 155
        assert inv.data[2] == 0


class TestFilterPipelineEngine:
    """Tests for composable FilterPipeline chaining, execution, and benchmarking."""

    def test_pipeline_chaining(self):
        pipeline = FilterPipeline()
        pipeline.add_step("grayscale")
        pipeline.add_step("invert")

        input_frame = PixelBuffer.create_empty(width=8, height=8, channels=3, fill=0)
        result = pipeline.process(input_frame)

        assert result.channels == 1
        # Inverted black becomes white (255)
        assert result.data[0] == 255

    def test_pipeline_add_remove_clear(self):
        pipeline = FilterPipeline()
        pipeline.add_step("sobel", threshold=30)
        pipeline.add_step("matrix_scanline", tint_mode="amber")
        assert len(pipeline.steps) == 2

        assert pipeline.remove_step(0) is True
        assert len(pipeline.steps) == 1
        assert pipeline.steps[0].name == "matrix_scanline"

        pipeline.clear()
        assert len(pipeline.steps) == 0

    def test_pipeline_custom_filter(self):
        pipeline = FilterPipeline()

        def custom_tint(buf: PixelBuffer, factor: int = 50) -> PixelBuffer:
            res = buf.copy()
            for i in range(len(res.data)):
                res.data[i] = min(255, res.data[i] + factor)
            return res

        pipeline.register_filter("custom_tint", custom_tint)
        pipeline.add_step("custom_tint", factor=30)

        buf = PixelBuffer.create_empty(width=4, height=4, channels=1, fill=10)
        out = pipeline.process(buf)
        assert out.data[0] == 40

    def test_pipeline_benchmark(self):
        pipeline = FilterPipeline()
        pipeline.add_step("sobel")
        pipeline.add_step("thermal")

        buf = PixelBuffer.create_empty(width=16, height=16, channels=3, fill=100)
        bench = pipeline.benchmark(buf, iterations=3)

        assert bench.iterations == 3
        assert bench.total_time_ms > 0
        assert bench.fps > 0
        assert "sobel" in bench.step_times_ms
        assert "thermal" in bench.step_times_ms
        assert bench.frame_size == (16, 16)
