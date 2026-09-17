"""Dynamic Gesture Trajectory Recorder, Stroke Classifier, and Pinch-Zoom Engine.

Tracks landmark trajectories over time to recognize continuous dynamic gestures:
- Directional swipes (SWIPE_LEFT, SWIPE_RIGHT, SWIPE_UP, SWIPE_DOWN)
- Circle stroke detection using angular winding integration (CIRCLE_CW, CIRCLE_CCW)
- Two-finger pinch-to-zoom scaling ratio and delta calculation

100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class TrajectoryPoint:
    """Timestamped 2D coordinate for stroke tracking."""

    x: float
    y: float
    timestamp: float  # Unix timestamp in seconds


@dataclass
class TrajectoryStroke:
    """Summarized path trajectory over a gesture time window."""

    points: List[TrajectoryPoint]
    duration_seconds: float
    total_path_length: float
    net_dx: float
    net_dy: float
    average_velocity: float
    dominant_direction: str  # 'LEFT', 'RIGHT', 'UP', 'DOWN', 'STATIONARY'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "point_count": len(self.points),
            "duration_seconds": round(self.duration_seconds, 3),
            "total_path_length": round(self.total_path_length, 4),
            "net_dx": round(self.net_dx, 4),
            "net_dy": round(self.net_dy, 4),
            "average_velocity": round(self.average_velocity, 3),
            "dominant_direction": self.dominant_direction,
        }


class TrajectoryTracker:
    """Sliding-window buffer for detecting continuous strokes and gestures."""

    def __init__(self, max_points: int = 60, window_seconds: float = 1.0) -> None:
        self.max_points = max_points
        self.window_seconds = window_seconds
        self.points: List[TrajectoryPoint] = []

    def add_point(self, x: float, y: float, timestamp: Optional[float] = None) -> None:
        """Add a landmark position point with timestamp."""
        t = timestamp if timestamp is not None else time.time()
        self.points.append(TrajectoryPoint(x=x, y=y, timestamp=t))
        self._prune(t)

    def clear(self) -> None:
        """Reset the trajectory buffer."""
        self.points.clear()

    def _prune(self, current_time: float) -> None:
        """Remove points older than the time window or exceeding max count."""
        cutoff = current_time - self.window_seconds
        self.points = [p for p in self.points if p.timestamp >= cutoff]
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    def get_stroke(self) -> Optional[TrajectoryStroke]:
        """Compute stroke kinematics from current buffer."""
        if len(self.points) < 2:
            return None

        duration = self.points[-1].timestamp - self.points[0].timestamp
        if duration <= 0:
            duration = 1e-4

        path_length = 0.0
        for i in range(1, len(self.points)):
            dx = self.points[i].x - self.points[i - 1].x
            dy = self.points[i].y - self.points[i - 1].y
            path_length += math.hypot(dx, dy)

        net_dx = self.points[-1].x - self.points[0].x
        net_dy = self.points[-1].y - self.points[0].y
        avg_v = path_length / duration

        abs_dx = abs(net_dx)
        abs_dy = abs(net_dy)

        if max(abs_dx, abs_dy) < 0.05:
            direction = "STATIONARY"
        elif abs_dx > abs_dy:
            direction = "RIGHT" if net_dx > 0 else "LEFT"
        else:
            direction = "DOWN" if net_dy > 0 else "UP"

        return TrajectoryStroke(
            points=list(self.points),
            duration_seconds=duration,
            total_path_length=path_length,
            net_dx=net_dx,
            net_dy=net_dy,
            average_velocity=avg_v,
            dominant_direction=direction,
        )

    def detect_swipe(
        self,
        min_displacement: float = 0.15,
        max_duration: float = 0.8,
        min_velocity: float = 0.3,
    ) -> Optional[str]:
        """Detect rapid swipe motion across screen space.

        Returns:
            'SWIPE_LEFT', 'SWIPE_RIGHT', 'SWIPE_UP', 'SWIPE_DOWN', or None.
        """
        stroke = self.get_stroke()
        if not stroke or stroke.duration_seconds > max_duration or stroke.average_velocity < min_velocity:
            return None

        abs_dx = abs(stroke.net_dx)
        abs_dy = abs(stroke.net_dy)

        if abs_dx >= min_displacement and abs_dx > abs_dy * 1.5:
            return "SWIPE_RIGHT" if stroke.net_dx > 0 else "SWIPE_LEFT"

        if abs_dy >= min_displacement and abs_dy > abs_dx * 1.5:
            return "SWIPE_DOWN" if stroke.net_dy > 0 else "SWIPE_UP"

        return None

    def detect_circle(
        self,
        min_points: int = 8,
        min_winding_ratio: float = 0.75,
    ) -> Optional[str]:
        """Detect circular drawing motion using signed angle integration.

        Returns:
            'CIRCLE_CLOCKWISE', 'CIRCLE_COUNTERCLOCKWISE', or None.
        """
        if len(self.points) < min_points:
            return None

        # Compute centroid
        cx = sum(p.x for p in self.points) / len(self.points)
        cy = sum(p.y for p in self.points) / len(self.points)

        # Calculate angles relative to centroid
        angles = [math.atan2(p.y - cy, p.x - cx) for p in self.points]

        # Integrate unwrapped angular delta
        total_angle = 0.0
        for i in range(1, len(angles)):
            da = angles[i] - angles[i - 1]
            # Wrap to [-pi, pi]
            while da > math.pi:
                da -= 2 * math.pi
            while da < -math.pi:
                da += 2 * math.pi
            total_angle += da

        # Full circle is 2*pi radians (~6.283)
        revolutions = total_angle / (2 * math.pi)

        if abs(revolutions) >= min_winding_ratio:
            # Positive angular change in standard screen space (Y down) is clockwise
            return "CIRCLE_CLOCKWISE" if revolutions > 0 else "CIRCLE_COUNTERCLOCKWISE"

        return None


def calculate_pinch_zoom_delta(
    p1_current: Tuple[float, float],
    p2_current: Tuple[float, float],
    p1_prev: Tuple[float, float],
    p2_prev: Tuple[float, float],
) -> float:
    """Calculate the pinch zoom ratio between two fingers across consecutive frames.

    Args:
        p1_current: (x, y) of thumb/finger 1 currently
        p2_current: (x, y) of index/finger 2 currently
        p1_prev: (x, y) of thumb/finger 1 previously
        p2_prev: (x, y) of index/finger 2 previously

    Returns:
        float: Scale multiplier. 1.0 = no change, >1.0 = pinch out (zoom in), <1.0 = pinch in (zoom out).
    """
    d_current = math.hypot(p1_current[0] - p2_current[0], p1_current[1] - p2_current[1])
    d_prev = math.hypot(p1_prev[0] - p2_prev[0], p1_prev[1] - p2_prev[1])

    if d_prev <= 1e-5:
        return 1.0

    return round(d_current / d_prev, 4)
