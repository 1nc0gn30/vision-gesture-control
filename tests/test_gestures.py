"""Unit tests for gestures.py (Geometry Analyzer, Gesture Classifiers, Dwell Detector, Action Schema)."""

import json
import math
from typing import Dict, List, Tuple

import pytest

from vision_gesture_control.gestures import (
    ActionBinding,
    ActionBindingSchema,
    ActionDispatcher,
    DwellDetector,
    DwellZone,
    FaceGestureClassifier,
    FaceGestureResult,
    GestureResult,
    GestureType,
    HandGestureClassifier,
    HandLandmark,
    Point3D,
    angle_between_points,
    bounding_box,
    center_of_mass,
    create_browser_preset,
    create_media_preset,
    create_presentation_preset,
    euclidean_distance,
    manhattan_distance,
)


# ---------------------------------------------------------------------------
# Helper: Synthetic 21-Hand Landmark Generators
# ---------------------------------------------------------------------------

def create_base_hand_landmarks(wrist: Tuple[float, float] = (0.5, 0.8)) -> List[Point3D]:
    """Creates a template 21-point hand skeleton."""
    pts = [Point3D(wrist[0], wrist[1], 0.0)] * 21
    # Wrist (0)
    pts[0] = Point3D(wrist[0], wrist[1], 0.0)
    # Thumb (1-4)
    pts[1] = Point3D(0.46, 0.75, 0.0)
    pts[2] = Point3D(0.42, 0.70, 0.0)
    pts[3] = Point3D(0.38, 0.65, 0.0)
    pts[4] = Point3D(0.35, 0.60, 0.0)
    # Index (5-8)
    pts[5] = Point3D(0.46, 0.60, 0.0)
    pts[6] = Point3D(0.45, 0.50, 0.0)
    pts[7] = Point3D(0.45, 0.42, 0.0)
    pts[8] = Point3D(0.45, 0.35, 0.0)
    # Middle (9-12)
    pts[9] = Point3D(0.50, 0.58, 0.0)
    pts[10] = Point3D(0.50, 0.48, 0.0)
    pts[11] = Point3D(0.50, 0.40, 0.0)
    pts[12] = Point3D(0.50, 0.32, 0.0)
    # Ring (13-16)
    pts[13] = Point3D(0.54, 0.60, 0.0)
    pts[14] = Point3D(0.54, 0.50, 0.0)
    pts[15] = Point3D(0.54, 0.43, 0.0)
    pts[16] = Point3D(0.54, 0.37, 0.0)
    # Pinky (17-20)
    pts[17] = Point3D(0.58, 0.64, 0.0)
    pts[18] = Point3D(0.59, 0.56, 0.0)
    pts[19] = Point3D(0.60, 0.50, 0.0)
    pts[20] = Point3D(0.60, 0.44, 0.0)
    return pts


def create_curled_finger(pts: List[Point3D], mcp_idx: int, pip_idx: int, dip_idx: int, tip_idx: int) -> None:
    """Modifies landmarks to curl a finger downward towards MCP."""
    mcp_x, mcp_y = pts[mcp_idx].x, pts[mcp_idx].y
    pts[pip_idx] = Point3D(mcp_x, mcp_y - 0.05, 0.0)
    pts[dip_idx] = Point3D(mcp_x, mcp_y - 0.02, 0.0)
    pts[tip_idx] = Point3D(mcp_x, mcp_y + 0.03, 0.0)  # tip is lower than PIP


def create_extended_finger(pts: List[Point3D], mcp_idx: int, pip_idx: int, dip_idx: int, tip_idx: int, x_offset: float = 0.0) -> None:
    """Modifies landmarks to extend a finger straight upward."""
    base_x = pts[mcp_idx].x + x_offset
    pts[pip_idx] = Point3D(base_x, 0.48, 0.0)
    pts[dip_idx] = Point3D(base_x, 0.38, 0.0)
    pts[tip_idx] = Point3D(base_x, 0.28, 0.0)  # tip is high up


# ---------------------------------------------------------------------------
# Test Suites
# ---------------------------------------------------------------------------

class TestPointAndGeometryMath:
    """Tests for vector math, distances, angles, bounding box, and centroids."""

    def test_point3d_creation(self):
        p1 = Point3D(1.0, 2.0, 3.0)
        assert p1.to_tuple_2d() == (1.0, 2.0)
        assert p1.to_tuple_3d() == (1.0, 2.0, 3.0)

        p2 = Point3D.from_any((4.0, 5.0))
        assert p2.x == 4.0 and p2.y == 5.0 and p2.z == 0.0

        p3 = Point3D.from_any({"x": 7.0, "y": 8.0, "z": 9.0})
        assert p3.x == 7.0 and p3.y == 8.0 and p3.z == 9.0

        with pytest.raises(ValueError):
            Point3D.from_any("invalid")  # type: ignore

    def test_euclidean_distance(self):
        assert euclidean_distance((0, 0), (3, 4)) == pytest.approx(5.0)
        assert euclidean_distance((0, 0, 0), (0, 0, 10), include_z=True) == pytest.approx(10.0)

    def test_manhattan_distance(self):
        assert manhattan_distance((1, 2), (4, 6)) == pytest.approx(7.0)

    def test_angle_between_points(self):
        # 90-degree right angle at (0, 0)
        a = (0, 1)
        b = (0, 0)
        c = (1, 0)
        assert angle_between_points(a, b, c) == pytest.approx(90.0)

        # 180-degree straight line
        a2 = (-1, 0)
        b2 = (0, 0)
        c2 = (1, 0)
        assert angle_between_points(a2, b2, c2) == pytest.approx(180.0)

        # 0 distance edge case
        assert angle_between_points((0, 0), (0, 0), (1, 1)) == 0.0

    def test_bounding_box(self):
        pts = [(0.1, 0.2), (0.8, 0.4), (0.3, 0.9)]
        min_x, min_y, max_x, max_y = bounding_box(pts)
        assert min_x == pytest.approx(0.1)
        assert min_y == pytest.approx(0.2)
        assert max_x == pytest.approx(0.8)
        assert max_y == pytest.approx(0.9)

        assert bounding_box([]) == (0.0, 0.0, 0.0, 0.0)

    def test_center_of_mass(self):
        pts = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
        c = center_of_mass(pts)
        assert c.x == pytest.approx(1.0)
        assert c.y == pytest.approx(1.0)


class TestHandGestureClassifier:
    """Tests for 21-hand landmark classifier across all primary gestures."""

    @pytest.fixture
    def classifier(self) -> HandGestureClassifier:
        return HandGestureClassifier()

    def test_empty_or_short_landmarks(self, classifier):
        res = classifier.classify([])
        assert res.gesture == GestureType.NONE.value
        assert res.confidence == 0.0

        res2 = classifier.classify([Point3D(0, 0)] * 10)
        assert res2.gesture == GestureType.NONE.value

    def test_open_palm_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # All 5 fingers extended straight up
        create_extended_finger(pts, 5, 6, 7, 8)
        create_extended_finger(pts, 9, 10, 11, 12)
        create_extended_finger(pts, 13, 14, 15, 16)
        create_extended_finger(pts, 17, 18, 19, 20)
        pts[4] = Point3D(0.28, 0.50, 0.0)  # Thumb extended out

        res = classifier.classify(pts)
        assert res.gesture == GestureType.PALM.value
        assert res.confidence > 0.85
        assert res.finger_states["index"] is True
        assert res.finger_states["middle"] is True

    def test_fist_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Curl all 4 fingers
        create_curled_finger(pts, 5, 6, 7, 8)
        create_curled_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_curled_finger(pts, 17, 18, 19, 20)
        # Curl thumb tucked over index MCP
        pts[1] = Point3D(0.46, 0.70, 0.0)
        pts[2] = Point3D(0.48, 0.65, 0.0)
        pts[3] = Point3D(0.50, 0.63, 0.0)
        pts[4] = Point3D(0.48, 0.68, 0.0)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.FIST.value
        assert res.confidence > 0.85
        assert all(state is False for state in res.finger_states.values())

    def test_point_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Index extended, others curled
        create_extended_finger(pts, 5, 6, 7, 8)
        create_curled_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_curled_finger(pts, 17, 18, 19, 20)
        pts[4] = Point3D(0.46, 0.62, 0.0)  # thumb curled

        res = classifier.classify(pts)
        assert res.gesture == GestureType.POINT.value
        assert res.finger_states["index"] is True
        assert res.finger_states["middle"] is False

    def test_peace_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Index and middle extended, ring & pinky curled
        create_extended_finger(pts, 5, 6, 7, 8)
        create_extended_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_curled_finger(pts, 17, 18, 19, 20)
        pts[4] = Point3D(0.46, 0.62, 0.0)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.PEACE.value
        assert res.finger_states["index"] is True
        assert res.finger_states["middle"] is True
        assert res.finger_states["ring"] is False

    def test_rock_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Index and pinky extended, middle & ring curled
        create_extended_finger(pts, 5, 6, 7, 8)
        create_curled_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_extended_finger(pts, 17, 18, 19, 20)
        pts[4] = Point3D(0.46, 0.62, 0.0)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.ROCK.value
        assert res.finger_states["index"] is True
        assert res.finger_states["pinky"] is True
        assert res.finger_states["middle"] is False

    def test_pinch_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Bring thumb tip (4) and index tip (8) very close
        pts[4] = Point3D(0.45, 0.40, 0.0)
        pts[8] = Point3D(0.455, 0.405, 0.0)  # distance < 0.01
        create_curled_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_curled_finger(pts, 17, 18, 19, 20)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.PINCH.value
        assert res.pinch_distance < 0.065
        assert res.pinch_point is not None

    def test_ok_sign_gesture(self, classifier):
        pts = create_base_hand_landmarks()
        # Thumb & index tip touching, middle, ring, pinky extended
        pts[4] = Point3D(0.45, 0.40, 0.0)
        pts[8] = Point3D(0.452, 0.402, 0.0)
        create_extended_finger(pts, 9, 10, 11, 12)
        create_extended_finger(pts, 13, 14, 15, 16)
        create_extended_finger(pts, 17, 18, 19, 20)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.OK_SIGN.value

    def test_thumbs_up_gesture(self, classifier):
        pts = create_base_hand_landmarks(wrist=(0.5, 0.8))
        # Thumb pointed straight up (tip y=0.35, mcp y=0.65)
        pts[1] = Point3D(0.46, 0.70, 0.0)
        pts[2] = Point3D(0.44, 0.62, 0.0)
        pts[3] = Point3D(0.42, 0.50, 0.0)
        pts[4] = Point3D(0.40, 0.35, 0.0)
        # All 4 other fingers curled
        create_curled_finger(pts, 5, 6, 7, 8)
        create_curled_finger(pts, 9, 10, 11, 12)
        create_curled_finger(pts, 13, 14, 15, 16)
        create_curled_finger(pts, 17, 18, 19, 20)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.THUMBS_UP.value

    def test_thumbs_down_gesture(self, classifier):
        pts = create_base_hand_landmarks(wrist=(0.5, 0.3))
        # Thumb pointed downwards (tip y=0.75, mcp y=0.45)
        pts[1] = Point3D(0.46, 0.40, 0.0)
        pts[2] = Point3D(0.44, 0.48, 0.0)
        pts[3] = Point3D(0.42, 0.60, 0.0)
        pts[4] = Point3D(0.40, 0.75, 0.0)
        # All 4 other fingers curled
        pts[5] = Point3D(0.5, 0.35, 0.0)
        pts[6] = Point3D(0.5, 0.38, 0.0)
        pts[7] = Point3D(0.5, 0.40, 0.0)
        pts[8] = Point3D(0.5, 0.36, 0.0)
        pts[9] = Point3D(0.54, 0.35, 0.0)
        pts[10] = Point3D(0.54, 0.38, 0.0)
        pts[11] = Point3D(0.54, 0.40, 0.0)
        pts[12] = Point3D(0.54, 0.36, 0.0)
        pts[13] = Point3D(0.58, 0.35, 0.0)
        pts[14] = Point3D(0.58, 0.38, 0.0)
        pts[15] = Point3D(0.58, 0.40, 0.0)
        pts[16] = Point3D(0.58, 0.36, 0.0)
        pts[17] = Point3D(0.62, 0.35, 0.0)
        pts[18] = Point3D(0.62, 0.38, 0.0)
        pts[19] = Point3D(0.62, 0.40, 0.0)
        pts[20] = Point3D(0.62, 0.36, 0.0)

        res = classifier.classify(pts)
        assert res.gesture == GestureType.THUMBS_DOWN.value


class TestDwellDetector:
    """Tests for continuous dwell tracking and zone triggering."""

    def test_dwell_progress_and_trigger(self):
        detector = DwellDetector(dwell_time_ms=800.0, retrigger_cooldown_ms=300.0)
        detector.add_zone("btn1", bbox=(0.1, 0.1, 0.4, 0.4))

        # Enter zone at t=1000
        s1 = detector.update(0.2, 0.2, timestamp_ms=1000.0)
        assert s1.is_dwelling is True
        assert s1.progress == 0.0
        assert s1.triggered is False
        assert s1.zone_id == "btn1"

        # Halfway at t=1400 (400ms elapsed)
        s2 = detector.update(0.22, 0.22, timestamp_ms=1400.0)
        assert s2.is_dwelling is True
        assert s2.progress == pytest.approx(0.5, abs=0.01)
        assert s2.triggered is False

        # Complete at t=1800 (800ms elapsed)
        s3 = detector.update(0.21, 0.21, timestamp_ms=1800.0)
        assert s3.is_dwelling is True
        assert s3.progress == pytest.approx(1.0)
        assert s3.triggered is True

        # Still inside zone immediately after: progress 1.0, but not re-triggered
        s4 = detector.update(0.21, 0.21, timestamp_ms=1850.0)
        assert s4.is_dwelling is True
        assert s4.triggered is False

    def test_dwell_exit_resets(self):
        detector = DwellDetector(dwell_time_ms=500.0)
        detector.add_zone("zoneA", bbox=(0.0, 0.0, 0.5, 0.5))

        detector.update(0.2, 0.2, timestamp_ms=1000.0)
        detector.update(0.2, 0.2, timestamp_ms=1250.0)  # progress 0.5

        # Move outside zone
        s_out = detector.update(0.8, 0.8, timestamp_ms=1300.0)
        assert s_out.is_dwelling is False
        assert s_out.progress == 0.0
        assert s_out.zone_id is None

    def test_dwell_callback_invocation(self):
        callback_called = []

        def on_btn_trigger(zid, pos):
            callback_called.append((zid, pos))

        detector = DwellDetector(dwell_time_ms=200.0)
        detector.add_zone("click_btn", bbox=(0.0, 0.0, 1.0, 1.0), on_trigger=on_btn_trigger)

        detector.update(0.5, 0.5, timestamp_ms=100.0)
        detector.update(0.5, 0.5, timestamp_ms=350.0)

        assert len(callback_called) == 1
        assert callback_called[0][0] == "click_btn"
        assert callback_called[0][1] == (0.5, 0.5)

    def test_dwell_zone_removal(self):
        detector = DwellDetector()
        detector.add_zone("z1", (0, 0, 1, 1))
        assert "z1" in detector.zones
        assert detector.remove_zone("z1") is True
        assert detector.remove_zone("non_existent") is False


class TestFaceGestureClassifier:
    """Tests for Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR), and smile detection."""

    @pytest.fixture
    def face_clf(self) -> FaceGestureClassifier:
        return FaceGestureClassifier(ear_blink_threshold=0.20, mar_open_threshold=0.50, smile_curvature_threshold=0.10)

    def test_compute_ear_open_eye(self, face_clf):
        # 6-point eye coordinates with wide opening
        # p0: left corner, p1: top-left, p2: top-right, p3: right corner, p4: bot-right, p5: bot-left
        eye_open = [
            (0.30, 0.40),  # p0
            (0.34, 0.36),  # p1
            (0.38, 0.36),  # p2
            (0.42, 0.40),  # p3
            (0.38, 0.44),  # p4
            (0.34, 0.44),  # p5
        ]
        ear = face_clf.compute_ear(eye_open)
        # v1 = 0.08, v2 = 0.08, h = 0.12 => ear = 0.16 / (2 * 0.12) = 0.666
        assert ear > 0.30

    def test_compute_ear_closed_eye(self, face_clf):
        # 6-point eye coordinates closed/flat
        eye_closed = [
            (0.30, 0.40),
            (0.34, 0.395),
            (0.38, 0.395),
            (0.42, 0.40),
            (0.38, 0.405),
            (0.34, 0.405),
        ]
        ear = face_clf.compute_ear(eye_closed)
        assert ear < 0.15

    def test_compute_mar_open_vs_closed(self, face_clf):
        mouth_closed = [
            (0.40, 0.70),  # left
            (0.50, 0.69),  # top
            (0.60, 0.70),  # right
            (0.50, 0.71),  # bottom
        ]
        mar_closed = face_clf.compute_mar(mouth_closed)
        assert mar_closed < 0.25

        mouth_open = [
            (0.40, 0.70),
            (0.50, 0.60),  # top high
            (0.60, 0.70),
            (0.50, 0.80),  # bottom low
        ]
        mar_open = face_clf.compute_mar(mouth_open)
        assert mar_open > 0.60

    def test_compute_smile_curvature(self, face_clf):
        # Neutral mouth: lip center y = corners y
        mouth_neutral = [
            (0.40, 0.70),  # left
            (0.50, 0.69),  # top
            (0.60, 0.70),  # right
            (0.50, 0.71),  # bottom
        ]
        smile_neutral = face_clf.compute_smile_curvature(mouth_neutral)
        assert abs(smile_neutral) < 0.05

        # Smiling mouth: corners raised (lower Y values than lip center)
        mouth_smile = [
            (0.40, 0.64),  # left corner raised up
            (0.50, 0.69),  # top lip
            (0.60, 0.64),  # right corner raised up
            (0.50, 0.71),  # bot lip
        ]
        smile_val = face_clf.compute_smile_curvature(mouth_smile)
        assert smile_val > 0.15

    def test_classify_face_gestures(self, face_clf):
        eye_open = [(0.30, 0.40), (0.34, 0.36), (0.38, 0.36), (0.42, 0.40), (0.38, 0.44), (0.34, 0.44)]
        eye_closed = [(0.30, 0.40), (0.34, 0.395), (0.38, 0.395), (0.42, 0.40), (0.38, 0.405), (0.34, 0.405)]
        mouth_open = [(0.40, 0.70), (0.50, 0.60), (0.60, 0.70), (0.50, 0.80)]

        # Left blink
        res_left = face_clf.classify_face(left_eye=eye_closed, right_eye=eye_open)
        assert res_left.is_left_blink is True
        assert res_left.is_right_blink is False
        assert GestureType.BLINK_LEFT.value in res_left.active_gestures

        # Both blink
        res_both = face_clf.classify_face(left_eye=eye_closed, right_eye=eye_closed)
        assert res_both.is_both_blink is True
        assert GestureType.BLINK_BOTH.value in res_both.active_gestures

        # Mouth open
        res_mouth = face_clf.classify_face(left_eye=eye_open, right_eye=eye_open, mouth=mouth_open)
        assert res_mouth.is_mouth_open is True
        assert GestureType.MOUTH_OPEN.value in res_mouth.active_gestures


class TestActionBindingSchemaAndDispatcher:
    """Tests for ActionBinding, Schema serialization, validation, and dispatcher."""

    def test_schema_serialization_and_validation(self, tmp_path):
        schema = ActionBindingSchema(
            name="Custom Rig",
            description="Test bindings",
            bindings=[
                ActionBinding(gesture="PINCH", action="CLICK", cooldown_ms=200.0),
                ActionBinding(gesture="PALM", action="PAUSE", cooldown_ms=400.0),
            ],
        )
        assert len(schema.validate()) == 0

        # JSON export and import
        json_str = schema.to_json()
        restored = ActionBindingSchema.from_json(json_str)
        assert restored.name == "Custom Rig"
        assert len(restored.bindings) == 2
        assert restored.bindings[0].gesture == "PINCH"

        # File IO
        file_path = tmp_path / "schema.json"
        schema.save_to_file(file_path)
        assert file_path.exists()

        loaded = ActionBindingSchema.load_from_file(file_path)
        assert loaded.name == schema.name

    def test_schema_validation_errors(self):
        invalid_schema = ActionBindingSchema(
            name="",
            bindings=[
                ActionBinding(gesture="", action="CLICK"),
                ActionBinding(gesture="PINCH", action="", cooldown_ms=-50.0),
            ],
        )
        errors = invalid_schema.validate()
        assert len(errors) >= 3

    def test_presets_generation(self):
        pres = create_presentation_preset()
        assert pres.name == "Presentation Mode"
        assert any(b.gesture == "PEACE" and b.action == "NEXT_SLIDE" for b in pres.bindings)

        browser = create_browser_preset()
        assert browser.name == "Browser Navigation Mode"
        assert any(b.gesture == "PINCH" and b.action == "MOUSE_CLICK" for b in browser.bindings)

        media = create_media_preset()
        assert media.name == "Media Player Mode"
        assert any(b.gesture == "PALM" and b.action == "PLAY_PAUSE" for b in media.bindings)

    def test_action_dispatcher_execution_and_cooldown(self):
        schema = ActionBindingSchema(
            bindings=[
                ActionBinding(gesture="PINCH", action="CLICK", cooldown_ms=300.0),
            ]
        )
        dispatcher = ActionDispatcher(schema=schema)

        clicked = []

        def click_handler(binding, meta):
            clicked.append((binding.action, meta.get("target")))

        dispatcher.register_handler("CLICK", click_handler)

        # First dispatch at t=1000ms -> should execute
        r1 = dispatcher.dispatch("PINCH", metadata={"target": "button#1"}, timestamp_ms=1000.0)
        assert r1 is not None
        assert r1.executed is True
        assert len(clicked) == 1

        # Second dispatch at t=1100ms (100ms later < 300ms cooldown) -> should be suppressed
        r2 = dispatcher.dispatch("PINCH", metadata={"target": "button#1"}, timestamp_ms=1100.0)
        assert r2 is None
        assert len(clicked) == 1

        # Third dispatch at t=1400ms (400ms later > 300ms cooldown) -> should execute
        r3 = dispatcher.dispatch("PINCH", metadata={"target": "button#2"}, timestamp_ms=1400.0)
        assert r3 is not None
        assert r3.executed is True
        assert len(clicked) == 2

    def test_additional_gestures(self):
        classifier = HandGestureClassifier()

        # Call Me (Thumb + Pinky extended)
        pts_call = create_base_hand_landmarks()
        pts_call[4] = Point3D(0.28, 0.40, 0.0)  # Thumb extended far left
        create_curled_finger(pts_call, 5, 6, 7, 8)
        create_curled_finger(pts_call, 9, 10, 11, 12)
        create_curled_finger(pts_call, 13, 14, 15, 16)
        create_extended_finger(pts_call, 17, 18, 19, 20)
        res_call = classifier.classify(pts_call)
        assert res_call.gesture == GestureType.CALL_ME.value

        # Three Fingers (Index, Middle, Ring extended)
        pts_three = create_base_hand_landmarks()
        pts_three[4] = Point3D(0.48, 0.68, 0.0)
        create_extended_finger(pts_three, 5, 6, 7, 8)
        create_extended_finger(pts_three, 9, 10, 11, 12)
        create_extended_finger(pts_three, 13, 14, 15, 16)
        create_curled_finger(pts_three, 17, 18, 19, 20)
        res_three = classifier.classify(pts_three)
        assert res_three.gesture == GestureType.THREE_FINGERS.value

        # Four Fingers (Index, Middle, Ring, Pinky extended, thumb curled)
        pts_four = create_base_hand_landmarks()
        pts_four[4] = Point3D(0.48, 0.68, 0.0)
        create_extended_finger(pts_four, 5, 6, 7, 8)
        create_extended_finger(pts_four, 9, 10, 11, 12)
        create_extended_finger(pts_four, 13, 14, 15, 16)
        create_extended_finger(pts_four, 17, 18, 19, 20)
        res_four = classifier.classify(pts_four)
        assert res_four.gesture in (GestureType.FOUR_FINGERS.value, GestureType.PALM.value)

    def test_adhoc_bounding_box_dwell(self):
        detector = DwellDetector(dwell_time_ms=500.0)
        bbox = (0.2, 0.2, 0.6, 0.6)

        # Inside adhoc zone
        s1 = detector.update(0.3, 0.3, timestamp_ms=100.0, zone_id="custom_adhoc", zone_bbox=bbox)
        assert s1.is_dwelling is True
        assert s1.zone_id == "custom_adhoc"

        # Complete adhoc dwell
        s2 = detector.update(0.3, 0.3, timestamp_ms=650.0, zone_id="custom_adhoc", zone_bbox=bbox)
        assert s2.is_dwelling is True
        assert s2.triggered is True
        assert s2.progress == 1.0
