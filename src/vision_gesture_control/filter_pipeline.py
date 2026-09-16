"""Frame Filter Pipeline and Visual Processing Algorithms.

Provides high-performance pure-Python (zero runtime external dependencies) frame
filter algorithms operating on RGB/grayscale pixel buffers or 2D matrices:
- Sobel Edge Detection (horizontal & vertical spatial gradient convolution).
- Thermal False-Color Mapping (Ironbow, Rainbow, Jet, Hot Metal simulation with LUTs).
- Neon Contour Mapping (High-frequency edge extraction, neon tinting, and glow overlay).
- Cyber Matrix Scanline Simulator (CRT monitor scanlines, phosphor tinting, vignette, flicker).
- FilterPipeline engine with composable filter chains, benchmarking, and buffer utilities.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Pixel Buffer Representation
# ---------------------------------------------------------------------------

@dataclass
class PixelBuffer:
    """Represents a flat 1D byte buffer for RGB or Grayscale raster images."""
    data: bytearray
    width: int
    height: int
    channels: int = 3  # 3 for RGB, 1 for Grayscale

    def __post_init__(self) -> None:
        expected_size = self.width * self.height * self.channels
        if len(self.data) != expected_size:
            if len(self.data) == 0 and expected_size > 0:
                self.data = bytearray(expected_size)
            else:
                raise ValueError(
                    f"Buffer data length ({len(self.data)}) does not match dimensions "
                    f"({self.width}x{self.height}x{self.channels} = {expected_size})"
                )

    @classmethod
    def create_empty(cls, width: int, height: int, channels: int = 3, fill: int = 0) -> PixelBuffer:
        """Creates an empty pixel buffer filled with a constant value."""
        data = bytearray([fill] * (width * height * channels))
        return cls(data=data, width=width, height=height, channels=channels)

    @classmethod
    def from_bytes(
        cls,
        raw_bytes: Union[bytes, bytearray, Sequence[int]],
        width: int,
        height: int,
        channels: int = 3,
    ) -> PixelBuffer:
        """Creates a PixelBuffer from raw bytes or sequence of integers."""
        data = bytearray(raw_bytes)
        return cls(data=data, width=width, height=height, channels=channels)

    @classmethod
    def from_matrix(
        cls,
        matrix: Sequence[Sequence[Union[Tuple[int, int, int], int, Sequence[int]]]],
    ) -> PixelBuffer:
        """Creates a PixelBuffer from a 2D matrix of RGB tuples or grayscale integers."""
        if not matrix or not matrix[0]:
            return cls(data=bytearray(), width=0, height=0, channels=3)

        height = len(matrix)
        width = len(matrix[0])
        first_elem = matrix[0][0]

        if isinstance(first_elem, (tuple, list)):
            channels = len(first_elem)
            data = bytearray()
            for row in matrix:
                for pixel in row:
                    for ch in pixel:
                        data.append(max(0, min(255, int(ch))))
            return cls(data=data, width=width, height=height, channels=channels)
        else:
            channels = 1
            data = bytearray()
            for row in matrix:
                for val in row:
                    data.append(max(0, min(255, int(val))))  # type: ignore[arg-type]
            return cls(data=data, width=width, height=height, channels=channels)

    def to_matrix(self) -> List[List[Any]]:
        """Converts pixel buffer into a 2D matrix of (R, G, B) tuples or grayscale ints."""
        matrix: List[List[Any]] = []
        if self.channels == 3:
            for y in range(self.height):
                row: List[Tuple[int, int, int]] = []
                row_offset = y * self.width * 3
                for x in range(self.width):
                    idx = row_offset + x * 3
                    row.append((self.data[idx], self.data[idx + 1], self.data[idx + 2]))
                matrix.append(row)
        elif self.channels == 1:
            for y in range(self.height):
                row_gray: List[int] = []
                row_offset = y * self.width
                for x in range(self.width):
                    row_gray.append(self.data[row_offset + x])
                matrix.append(row_gray)
        return matrix

    def copy(self) -> PixelBuffer:
        """Creates a deep copy of the buffer."""
        return PixelBuffer(
            data=bytearray(self.data),
            width=self.width,
            height=self.height,
            channels=self.channels,
        )

    def get_pixel(self, x: int, y: int) -> Tuple[int, ...]:
        """Gets pixel value at (x, y)."""
        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))
        idx = (y * self.width + x) * self.channels
        if self.channels == 3:
            return (self.data[idx], self.data[idx + 1], self.data[idx + 2])
        elif self.channels == 1:
            return (self.data[idx],)
        return tuple(self.data[idx : idx + self.channels])

    def set_pixel(self, x: int, y: int, color: Union[Tuple[int, ...], Sequence[int], int]) -> None:
        """Sets pixel value at (x, y)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        idx = (y * self.width + x) * self.channels
        if isinstance(color, int):
            self.data[idx] = max(0, min(255, color))
            if self.channels == 3:
                self.data[idx + 1] = max(0, min(255, color))
                self.data[idx + 2] = max(0, min(255, color))
        else:
            for c in range(min(self.channels, len(color))):
                self.data[idx + c] = max(0, min(255, int(color[c])))


# ---------------------------------------------------------------------------
# Buffer Conversion Helpers
# ---------------------------------------------------------------------------

def _normalize_input_buffer(
    buffer: Union[PixelBuffer, bytes, bytearray, Sequence[int]],
    width: Optional[int] = None,
    height: Optional[int] = None,
    channels: int = 3,
) -> PixelBuffer:
    """Coerces various buffer types into a standard PixelBuffer."""
    if isinstance(buffer, PixelBuffer):
        return buffer
    if width is None or height is None:
        raise ValueError("width and height are required when buffer is raw bytes/sequence")
    return PixelBuffer.from_bytes(buffer, width=width, height=height, channels=channels)


def rgb_to_grayscale(buffer: Union[PixelBuffer, bytes, bytearray], width: Optional[int] = None, height: Optional[int] = None) -> PixelBuffer:
    """Converts an RGB PixelBuffer to Grayscale using standard ITU-R luminance: Y = 0.299R + 0.587G + 0.114B."""
    buf = _normalize_input_buffer(buffer, width, height, channels=3)
    if buf.channels == 1:
        return buf.copy()

    total_pixels = buf.width * buf.height
    gray_data = bytearray(total_pixels)

    src_data = buf.data
    for i in range(total_pixels):
        src_idx = i * 3
        # Fast fixed-point luminance: (R * 77 + G * 150 + B * 29) >> 8
        y = (src_data[src_idx] * 77 + src_data[src_idx + 1] * 150 + src_data[src_idx + 2] * 29) >> 8
        gray_data[i] = y

    return PixelBuffer(data=gray_data, width=buf.width, height=buf.height, channels=1)


def grayscale_to_rgb(buffer: Union[PixelBuffer, bytes, bytearray], width: Optional[int] = None, height: Optional[int] = None) -> PixelBuffer:
    """Converts a 1-channel Grayscale buffer to a 3-channel RGB buffer."""
    buf = _normalize_input_buffer(buffer, width, height, channels=1)
    if buf.channels == 3:
        return buf.copy()

    total_pixels = buf.width * buf.height
    rgb_data = bytearray(total_pixels * 3)

    src_data = buf.data
    for i in range(total_pixels):
        val = src_data[i]
        dst_idx = i * 3
        rgb_data[dst_idx] = val
        rgb_data[dst_idx + 1] = val
        rgb_data[dst_idx + 2] = val

    return PixelBuffer(data=rgb_data, width=buf.width, height=buf.height, channels=3)


# ---------------------------------------------------------------------------
# 1. Sobel Edge Detection
# ---------------------------------------------------------------------------

def sobel_edge_detection(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
    threshold: int = 0,
    edge_color: Tuple[int, int, int] = (255, 255, 255),
    bg_color: Tuple[int, int, int] = (0, 0, 0),
    invert: bool = False,
    return_rgb: bool = True,
) -> PixelBuffer:
    """Performs Sobel spatial gradient convolution for edge detection.

    Kernels:
        Gx = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
        Gy = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]

    Args:
        buffer: Input RGB or Grayscale buffer.
        width: Frame width (if raw bytes).
        height: Frame height (if raw bytes).
        threshold: Magnitude threshold below which edges are suppressed (0-255).
        edge_color: RGB color to draw detected edges.
        bg_color: RGB background color.
        invert: Whether to invert edge brightness.
        return_rgb: If True returns 3-channel RGB, otherwise 1-channel grayscale.

    Returns:
        Processed PixelBuffer with highlighted contours.
    """
    input_buf = _normalize_input_buffer(buffer, width, height)
    gray = rgb_to_grayscale(input_buf) if input_buf.channels == 3 else input_buf

    w = gray.width
    h = gray.height
    src = gray.data

    if w < 3 or h < 3:
        return grayscale_to_rgb(gray) if return_rgb else gray.copy()

    # Allocate output buffer
    if return_rgb:
        out_data = bytearray(w * h * 3)
        bg_r, bg_g, bg_b = bg_color
        edge_r, edge_g, edge_b = edge_color
        # Fill with bg color
        for i in range(w * h):
            out_data[i * 3] = bg_r
            out_data[i * 3 + 1] = bg_g
            out_data[i * 3 + 2] = bg_b
    else:
        out_data = bytearray(w * h)

    # Convolve 3x3 Sobel kernels
    for y in range(1, h - 1):
        row_above = (y - 1) * w
        row_curr = y * w
        row_below = (y + 1) * w

        for x in range(1, w - 1):
            # 3x3 window neighborhood
            p00 = src[row_above + x - 1]
            p01 = src[row_above + x]
            p02 = src[row_above + x + 1]

            p10 = src[row_curr + x - 1]
            p12 = src[row_curr + x + 1]

            p20 = src[row_below + x - 1]
            p21 = src[row_below + x]
            p22 = src[row_below + x + 1]

            # Horizontal gradient Gx
            gx = (p02 + 2 * p12 + p22) - (p00 + 2 * p10 + p20)
            # Vertical gradient Gy
            gy = (p20 + 2 * p21 + p22) - (p00 + 2 * p01 + p02)

            # Gradient magnitude approximation: |Gx| + |Gy| (or sqrt)
            mag = int(math.isqrt(gx * gx + gy * gy))
            mag = min(255, mag)

            if threshold > 0:
                mag = 255 if mag >= threshold else 0

            if invert:
                mag = 255 - mag

            curr_idx = row_curr + x
            if return_rgb:
                dst_idx = curr_idx * 3
                if mag > 0:
                    alpha = mag / 255.0
                    out_data[dst_idx] = int(bg_r * (1.0 - alpha) + edge_r * alpha)
                    out_data[dst_idx + 1] = int(bg_g * (1.0 - alpha) + edge_g * alpha)
                    out_data[dst_idx + 2] = int(bg_b * (1.0 - alpha) + edge_b * alpha)
            else:
                out_data[curr_idx] = mag

    return PixelBuffer(
        data=out_data,
        width=w,
        height=h,
        channels=3 if return_rgb else 1,
    )


# ---------------------------------------------------------------------------
# 2. Thermal False-Color Mapping
# ---------------------------------------------------------------------------

class ThermalColorMap(str, Enum):
    """Available false-color thermal palettes."""
    IRONBOW = "ironbow"
    RAINBOW = "rainbow"
    JET = "jet"
    HOT_METAL = "hot_metal"
    CYBERPUNK = "cyberpunk"
    ARCTIC = "arctic"


def _interpolate_palette(stops: Sequence[Tuple[float, Tuple[int, int, int]]]) -> List[Tuple[int, int, int]]:
    """Generates a 256-entry RGB lookup table from normalized color stops."""
    lut: List[Tuple[int, int, int]] = []
    sorted_stops = sorted(stops, key=lambda s: s[0])

    for i in range(256):
        pos = i / 255.0
        # Find enclosing stop pair
        lower = sorted_stops[0]
        upper = sorted_stops[-1]
        for idx in range(len(sorted_stops) - 1):
            if sorted_stops[idx][0] <= pos <= sorted_stops[idx + 1][0]:
                lower = sorted_stops[idx]
                upper = sorted_stops[idx + 1]
                break

        range_len = upper[0] - lower[0]
        if range_len < 1e-7:
            lut.append(lower[1])
        else:
            t = (pos - lower[0]) / range_len
            r = int(lower[1][0] + t * (upper[1][0] - lower[1][0]))
            g = int(lower[1][1] + t * (upper[1][1] - lower[1][1]))
            b = int(lower[1][2] + t * (upper[1][2] - lower[1][2]))
            lut.append((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))

    return lut


# Precomputed 256-entry lookup tables for all thermal palettes
_THERMAL_PALETTES: Dict[str, List[Tuple[int, int, int]]] = {
    ThermalColorMap.IRONBOW.value: _interpolate_palette([
        (0.0, (0, 0, 0)),
        (0.2, (50, 0, 110)),
        (0.4, (160, 20, 120)),
        (0.7, (230, 100, 20)),
        (0.9, (255, 220, 50)),
        (1.0, (255, 255, 255)),
    ]),
    ThermalColorMap.RAINBOW.value: _interpolate_palette([
        (0.0, (0, 0, 120)),
        (0.2, (0, 120, 255)),
        (0.4, (0, 255, 120)),
        (0.6, (255, 255, 0)),
        (0.8, (255, 100, 0)),
        (1.0, (255, 0, 0)),
    ]),
    ThermalColorMap.JET.value: _interpolate_palette([
        (0.0, (0, 0, 140)),
        (0.125, (0, 0, 255)),
        (0.375, (0, 255, 255)),
        (0.625, (255, 255, 0)),
        (0.875, (255, 0, 0)),
        (1.0, (128, 0, 0)),
    ]),
    ThermalColorMap.HOT_METAL.value: _interpolate_palette([
        (0.0, (0, 0, 0)),
        (0.25, (140, 0, 0)),
        (0.5, (230, 80, 0)),
        (0.75, (255, 220, 0)),
        (1.0, (255, 255, 255)),
    ]),
    ThermalColorMap.CYBERPUNK.value: _interpolate_palette([
        (0.0, (10, 0, 30)),
        (0.3, (120, 0, 180)),
        (0.6, (255, 0, 128)),
        (0.85, (0, 240, 255)),
        (1.0, (255, 255, 255)),
    ]),
    ThermalColorMap.ARCTIC.value: _interpolate_palette([
        (0.0, (0, 10, 30)),
        (0.3, (0, 80, 160)),
        (0.6, (50, 180, 220)),
        (0.85, (180, 240, 255)),
        (1.0, (255, 255, 255)),
    ]),
}


def thermal_false_color(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
    colormap: Union[str, ThermalColorMap] = ThermalColorMap.IRONBOW,
    auto_gain: bool = False,
) -> PixelBuffer:
    """Maps frame luminance to a thermal false-color heatmap simulation.

    Args:
        buffer: Input image buffer.
        width: Frame width.
        height: Frame height.
        colormap: Palette name ('ironbow', 'rainbow', 'jet', 'hot_metal', 'cyberpunk', 'arctic').
        auto_gain: Whether to perform dynamic contrast stretching across min/max luminance.

    Returns:
        Processed 3-channel RGB thermal false-color PixelBuffer.
    """
    input_buf = _normalize_input_buffer(buffer, width, height)
    gray = rgb_to_grayscale(input_buf) if input_buf.channels == 3 else input_buf

    cmap_key = colormap.value if isinstance(colormap, ThermalColorMap) else str(colormap).lower()
    lut = _THERMAL_PALETTES.get(cmap_key, _THERMAL_PALETTES[ThermalColorMap.IRONBOW.value])

    w = gray.width
    h = gray.height
    src = gray.data
    total_pixels = w * h

    # Calculate min/max for auto_gain if requested
    min_val = 0
    max_val = 255
    if auto_gain and total_pixels > 0:
        min_val = min(src)
        max_val = max(src)
        if max_val == min_val:
            max_val = min_val + 1

    out_data = bytearray(total_pixels * 3)

    for i in range(total_pixels):
        val = src[i]
        if auto_gain:
            norm_idx = int(((val - min_val) / (max_val - min_val)) * 255)
            norm_idx = max(0, min(255, norm_idx))
        else:
            norm_idx = val

        r, g, b = lut[norm_idx]
        dst_idx = i * 3
        out_data[dst_idx] = r
        out_data[dst_idx + 1] = g
        out_data[dst_idx + 2] = b

    return PixelBuffer(data=out_data, width=w, height=h, channels=3)


# ---------------------------------------------------------------------------
# 3. Neon Contour Mapping
# ---------------------------------------------------------------------------

def neon_contour_mapping(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
    neon_color: Tuple[int, int, int] = (0, 255, 240),  # Electric Cyan
    glow_color: Optional[Tuple[int, int, int]] = (255, 0, 180),  # Neon Magenta
    base_dim: float = 0.25,
    edge_threshold: int = 25,
    glow_spread: int = 1,
) -> PixelBuffer:
    """Applies high-frequency neon edge highlight and colored contour glow.

    Args:
        buffer: Input RGB or Grayscale frame.
        width: Frame width.
        height: Frame height.
        neon_color: Primary neon color for sharp edges.
        glow_color: Secondary color for softer outer glow.
        base_dim: Brightness factor for underlying base image (0.0 to 1.0).
        edge_threshold: Minimum Sobel edge magnitude threshold.
        glow_spread: Radius in pixels to spread neon glow.

    Returns:
        High-contrast neon contour PixelBuffer.
    """
    input_buf = _normalize_input_buffer(buffer, width, height)
    rgb_buf = grayscale_to_rgb(input_buf) if input_buf.channels == 1 else input_buf

    w = rgb_buf.width
    h = rgb_buf.height

    # 1. Compute raw grayscale Sobel edge magnitude
    edges_gray = sobel_edge_detection(
        rgb_buf,
        threshold=edge_threshold,
        return_rgb=False,
    )
    edge_data = edges_gray.data
    src_data = rgb_buf.data

    out_data = bytearray(w * h * 3)

    nr, ng, nb = neon_color
    gr, gg, gb = glow_color or neon_color

    for y in range(h):
        row_offset = y * w
        for x in range(x_start := 0, w):
            idx = row_offset + x
            dst_idx = idx * 3

            # Base darkened background
            orig_r = int(src_data[dst_idx] * base_dim)
            orig_g = int(src_data[dst_idx + 1] * base_dim)
            orig_b = int(src_data[dst_idx + 2] * base_dim)

            edge_val = edge_data[idx]

            # Check local neighbor glow if spread > 0 and no direct edge
            glow_val = 0
            if edge_val < 200 and glow_spread > 0:
                for dy in range(-glow_spread, glow_spread + 1):
                    ny = y + dy
                    if 0 <= ny < h:
                        n_row = ny * w
                        for dx in range(-glow_spread, glow_spread + 1):
                            nx = x + dx
                            if 0 <= nx < w:
                                glow_val = max(glow_val, edge_data[n_row + nx])

            # Composite: base + glow + sharp edge
            edge_alpha = edge_val / 255.0
            glow_alpha = (glow_val / 255.0) * 0.5

            res_r = int(orig_r * (1.0 - max(edge_alpha, glow_alpha)) + gr * glow_alpha + nr * edge_alpha)
            res_g = int(orig_g * (1.0 - max(edge_alpha, glow_alpha)) + gg * glow_alpha + ng * edge_alpha)
            res_b = int(orig_b * (1.0 - max(edge_alpha, glow_alpha)) + gb * glow_alpha + nb * edge_alpha)

            out_data[dst_idx] = min(255, res_r)
            out_data[dst_idx + 1] = min(255, res_g)
            out_data[dst_idx + 2] = min(255, res_b)

    return PixelBuffer(data=out_data, width=w, height=h, channels=3)


# ---------------------------------------------------------------------------
# 4. Cyber Matrix Scanline Simulator
# ---------------------------------------------------------------------------

def cyber_matrix_scanlines(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
    line_spacing: int = 3,
    scanline_darken: float = 0.55,
    tint_mode: str = "green",  # 'green', 'amber', 'cyan', 'none'
    vignette: bool = True,
    phase_offset: int = 0,
    phosphor_bleed: float = 0.15,
) -> PixelBuffer:
    """Simulates a Cyber Matrix / Retro CRT monitor scanline overlay.

    Features:
    - Periodic horizontal raster scanlines with controllable darkening factor.
    - Phosphor color tinting (Matrix Green, Retro Amber, Cyber Cyan).
    - Radial vignette edge darkening simulating curved CRT glass.
    - Phase shifting for rolling scanline animation.

    Args:
        buffer: Input frame.
        width: Frame width.
        height: Frame height.
        line_spacing: Number of pixels between scanline dark bands.
        scanline_darken: Darkening multiplier for scanline rows (0.0 = black, 1.0 = no effect).
        tint_mode: Phosphor tinting ('green', 'amber', 'cyan', 'none').
        vignette: Whether to apply CRT glass vignette darkening.
        phase_offset: Vertical offset for animated scanline scroll.
        phosphor_bleed: Green/amber phosphor bloom bleed into neighboring channels.

    Returns:
        Filtered Cyber Matrix PixelBuffer.
    """
    input_buf = _normalize_input_buffer(buffer, width, height)
    rgb_buf = grayscale_to_rgb(input_buf) if input_buf.channels == 1 else input_buf

    w = rgb_buf.width
    h = rgb_buf.height
    src_data = rgb_buf.data
    out_data = bytearray(w * h * 3)

    center_x = w / 2.0
    center_y = h / 2.0
    max_radius_sq = (center_x * center_x) + (center_y * center_y)

    for y in range(h):
        # Scanline calculation
        is_scanline = ((y + phase_offset) % max(1, line_spacing)) == 0
        line_factor = scanline_darken if is_scanline else 1.0

        row_offset = y * w * 3
        dy_sq = (y - center_y) * (y - center_y)

        for x in range(w):
            idx = row_offset + x * 3

            r = src_data[idx]
            g = src_data[idx + 1]
            b = src_data[idx + 2]

            # 1. Color tinting
            lum = (r * 77 + g * 150 + b * 29) >> 8

            if tint_mode == "green":
                # Classic Matrix green phosphor
                r = int(lum * 0.15 + r * phosphor_bleed)
                g = int(min(255, lum * 1.35 + 20))
                b = int(lum * 0.2 + b * phosphor_bleed)
            elif tint_mode == "amber":
                # Retro amber terminal
                r = int(min(255, lum * 1.3 + 25))
                g = int(lum * 0.7 + 10)
                b = int(lum * 0.05)
            elif tint_mode == "cyan":
                # Cyber cyan
                r = int(lum * 0.1)
                g = int(min(255, lum * 1.1 + 15))
                b = int(min(255, lum * 1.3 + 20))

            # 2. Scanline darkening
            r = int(r * line_factor)
            g = int(g * line_factor)
            b = int(b * line_factor)

            # 3. CRT Vignette
            if vignette:
                dx_sq = (x - center_x) * (x - center_x)
                dist_ratio = (dx_sq + dy_sq) / max_radius_sq
                vignette_factor = max(0.2, 1.0 - 0.6 * dist_ratio)
                r = int(r * vignette_factor)
                g = int(g * vignette_factor)
                b = int(b * vignette_factor)

            out_data[idx] = max(0, min(255, r))
            out_data[idx + 1] = max(0, min(255, g))
            out_data[idx + 2] = max(0, min(255, b))

    return PixelBuffer(data=out_data, width=w, height=h, channels=3)


# ---------------------------------------------------------------------------
# Additional Utility Filters
# ---------------------------------------------------------------------------

def box_blur(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
    radius: int = 1,
) -> PixelBuffer:
    """Performs fast separable 2D box blur."""
    input_buf = _normalize_input_buffer(buffer, width, height)
    w, h, c = input_buf.width, input_buf.height, input_buf.channels
    src = input_buf.data

    if radius <= 0 or w < 2 or h < 2:
        return input_buf.copy()

    # Horizontal pass
    temp = bytearray(len(src))
    for y in range(h):
        row_offset = y * w * c
        for x in range(w):
            for ch in range(c):
                val_sum = 0
                count = 0
                for dx in range(-radius, radius + 1):
                    nx = x + dx
                    if 0 <= nx < w:
                        val_sum += src[row_offset + nx * c + ch]
                        count += 1
                temp[row_offset + x * c + ch] = val_sum // count

    # Vertical pass
    out = bytearray(len(src))
    for y in range(h):
        for x in range(w):
            for ch in range(c):
                val_sum = 0
                count = 0
                for dy in range(-radius, radius + 1):
                    ny = y + dy
                    if 0 <= ny < h:
                        val_sum += temp[(ny * w + x) * c + ch]
                        count += 1
                out[(y * w + x) * c + ch] = val_sum // count

    return PixelBuffer(data=out, width=w, height=h, channels=c)


def invert_colors(
    buffer: Union[PixelBuffer, bytes, bytearray],
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> PixelBuffer:
    """Inverts all color channels (255 - value)."""
    input_buf = _normalize_input_buffer(buffer, width, height)
    out = bytearray(255 - b for b in input_buf.data)
    return PixelBuffer(data=out, width=input_buf.width, height=input_buf.height, channels=input_buf.channels)


# ---------------------------------------------------------------------------
# Composable Filter Pipeline
# ---------------------------------------------------------------------------

@dataclass
class FilterStep:
    """A single configured filter in the pipeline."""
    name: str
    filter_func: Callable[..., PixelBuffer]
    kwargs: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class PipelineBenchmarkResult:
    """Benchmark performance execution statistics."""
    total_time_ms: float
    avg_frame_time_ms: float
    fps: float
    step_times_ms: Dict[str, float]
    iterations: int
    frame_size: Tuple[int, int]


class FilterPipeline:
    """Chainable image processing pipeline for real-time video filter streams."""

    def __init__(self) -> None:
        self.steps: List[FilterStep] = []
        self._filter_registry: Dict[str, Callable[..., PixelBuffer]] = {
            "sobel": sobel_edge_detection,
            "thermal": thermal_false_color,
            "neon": neon_contour_mapping,
            "matrix_scanline": cyber_matrix_scanlines,
            "scanlines": cyber_matrix_scanlines,
            "grayscale": rgb_to_grayscale,
            "blur": box_blur,
            "invert": invert_colors,
        }

    def register_filter(self, name: str, func: Callable[..., PixelBuffer]) -> FilterPipeline:
        """Registers a custom filter function."""
        self._filter_registry[name.lower()] = func
        return self

    def add_step(
        self,
        filter_ref: Union[str, Callable[..., PixelBuffer]],
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> FilterPipeline:
        """Appends a filter step to the execution pipeline.

        Args:
            filter_ref: Filter registry name ('sobel', 'thermal', 'neon', 'matrix_scanline') or callable.
            name: Optional descriptive label.
            **kwargs: Arguments forwarded to the filter function.

        Returns:
            Self instance for method chaining.
        """
        if isinstance(filter_ref, str):
            key = filter_ref.lower()
            if key not in self._filter_registry:
                raise KeyError(f"Unknown filter name '{filter_ref}'. Available: {list(self._filter_registry.keys())}")
            func = self._filter_registry[key]
            step_name = name or filter_ref
        else:
            func = filter_ref
            step_name = name or getattr(func, "__name__", "custom_filter")

        self.steps.append(FilterStep(name=step_name, filter_func=func, kwargs=kwargs))
        return self

    def remove_step(self, index: int) -> bool:
        """Removes a step by index."""
        if 0 <= index < len(self.steps):
            self.steps.pop(index)
            return True
        return False

    def clear(self) -> FilterPipeline:
        """Clears all pipeline steps."""
        self.steps.clear()
        return self

    def process(
        self,
        buffer: Union[PixelBuffer, bytes, bytearray, Sequence[int]],
        width: Optional[int] = None,
        height: Optional[int] = None,
        channels: int = 3,
    ) -> PixelBuffer:
        """Executes all enabled filter steps in sequential order on the frame.

        Args:
            buffer: Input frame buffer.
            width: Frame width.
            height: Frame height.
            channels: Channels count.

        Returns:
            The final processed PixelBuffer.
        """
        curr = _normalize_input_buffer(buffer, width, height, channels=channels)

        for step in self.steps:
            if not step.enabled:
                continue
            curr = step.filter_func(curr, **step.kwargs)

        return curr

    def benchmark(
        self,
        buffer: Union[PixelBuffer, bytes, bytearray],
        width: Optional[int] = None,
        height: Optional[int] = None,
        iterations: int = 5,
    ) -> PipelineBenchmarkResult:
        """Benchmarks the pipeline execution speed over multiple iterations.

        Args:
            buffer: Sample test frame.
            width: Frame width.
            height: Frame height.
            iterations: Number of benchmark runs.

        Returns:
            PipelineBenchmarkResult with frame times, FPS, and per-step breakdowns.
        """
        test_buf = _normalize_input_buffer(buffer, width, height)
        step_times: Dict[str, float] = {step.name: 0.0 for step in self.steps}

        start_total = time.perf_counter()
        for _ in range(iterations):
            curr = test_buf.copy()
            for step in self.steps:
                if not step.enabled:
                    continue
                t0 = time.perf_counter()
                curr = step.filter_func(curr, **step.kwargs)
                t1 = time.perf_counter()
                step_times[step.name] += (t1 - t0) * 1000.0

        total_time_ms = (time.perf_counter() - start_total) * 1000.0
        avg_frame_ms = total_time_ms / max(1, iterations)
        fps = 1000.0 / avg_frame_ms if avg_frame_ms > 0 else 0.0

        for k in step_times:
            step_times[k] /= max(1, iterations)

        return PipelineBenchmarkResult(
            total_time_ms=total_time_ms,
            avg_frame_time_ms=avg_frame_ms,
            fps=fps,
            step_times_ms=step_times,
            iterations=iterations,
            frame_size=(test_buf.width, test_buf.height),
        )
