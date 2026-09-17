"""Tests for dynamic gesture trajectory recorder and pinch-zoom engine."""

import math
from vision_gesture_control.trajectory import (
    TrajectoryPoint,
    TrajectoryStroke,
    TrajectoryTracker,
    calculate_pinch_zoom_delta,
)


def test_trajectory_tracker_basic():
    tracker = TrajectoryTracker(max_points=50, window_seconds=2.0)
    tracker.add_point(0.1, 0.5, timestamp=1.0)
    tracker.add_point(0.2, 0.5, timestamp=1.1)
    tracker.add_point(0.4, 0.5, timestamp=1.2)

    stroke = tracker.get_stroke()
    assert isinstance(stroke, TrajectoryStroke)
    assert stroke.dominant_direction == "RIGHT"
    assert stroke.net_dx > 0.2
    assert stroke.duration_seconds > 0.1


def test_detect_swipe_right():
    tracker = TrajectoryTracker()
    # Fast swipe from x=0.2 to x=0.8 in 0.2s
    for i in range(10):
        t = 10.0 + (i * 0.02)
        x = 0.2 + (i * 0.06)
        tracker.add_point(x, 0.5, timestamp=t)

    swipe = tracker.detect_swipe(min_displacement=0.3, max_duration=0.5)
    assert swipe == "SWIPE_RIGHT"


def test_detect_swipe_up():
    tracker = TrajectoryTracker()
    # Swipe up: y decreases in standard screen coordinates
    for i in range(8):
        t = 1.0 + (i * 0.02)
        y = 0.8 - (i * 0.06)
        tracker.add_point(0.5, y, timestamp=t)

    swipe = tracker.detect_swipe(min_displacement=0.3, max_duration=0.5)
    assert swipe == "SWIPE_UP"


def test_detect_circle_clockwise():
    tracker = TrajectoryTracker(max_points=100, window_seconds=3.0)
    cx, cy, r = 0.5, 0.5, 0.2
    # Trace a clockwise circle (angle increasing 0 to 2*pi)
    for step in range(20):
        theta = (step / 20) * 2 * math.pi
        x = cx + r * math.cos(theta)
        y = cy + r * math.sin(theta)
        tracker.add_point(x, y, timestamp=1.0 + (step * 0.05))

    circle = tracker.detect_circle(min_points=12, min_winding_ratio=0.7)
    assert circle == "CIRCLE_CLOCKWISE"


def test_pinch_zoom_delta():
    # Previous frame: distance = 0.1
    p1_prev = (0.45, 0.5)
    p2_prev = (0.55, 0.5)

    # Current frame: pinched out (distance = 0.2)
    p1_curr = (0.40, 0.5)
    p2_curr = (0.60, 0.5)

    scale = calculate_pinch_zoom_delta(p1_curr, p2_curr, p1_prev, p2_prev)
    assert scale == 2.0  # Doubled distance = 2.0x zoom

    # Pinched in (distance = 0.05)
    p1_in = (0.475, 0.5)
    p2_in = (0.525, 0.5)
    scale_in = calculate_pinch_zoom_delta(p1_in, p2_in, p1_prev, p2_prev)
    assert scale_in == 0.5
