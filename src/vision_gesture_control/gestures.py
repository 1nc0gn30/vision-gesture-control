"""Geometry Analyzer, Gesture Classifiers, Dwell Detector, and Action Binding Schema.

Provides pure Python (zero runtime external dependencies) algorithms for:
- 21-hand landmark geometry analysis and gesture classification (PINCH, POINT, PALM,
  FIST, THUMBS_UP, THUMBS_DOWN, PEACE, ROCK, OK_SIGN, CALL_ME, etc.).
- Dwell zone tracking over time (ms) with continuous progress calculation (0.0 to 1.0).
- Facial landmark analysis (Eye Aspect Ratio / EAR, Mouth Aspect Ratio / MAR, Smile Curvature).
- Action binding configuration schema and event dispatcher mapping gestures to actions.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Point & Landmark Types
# ---------------------------------------------------------------------------

@dataclass
class Point3D:
    """3D point representation with optional z-coordinate."""
    x: float
    y: float
    z: float = 0.0

    def to_tuple_2d(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_tuple_3d(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @classmethod
    def from_any(cls, point: Union[Point3D, Tuple[float, ...], List[float], Dict[str, float]]) -> Point3D:
        """Converts diverse point input representations into a normalized Point3D."""
        if isinstance(point, Point3D):
            return point
        if isinstance(point, (tuple, list)):
            x = float(point[0])
            y = float(point[1])
            z = float(point[2]) if len(point) > 2 else 0.0
            return cls(x=x, y=y, z=z)
        if isinstance(point, dict):
            x = float(point.get("x", 0.0))
            y = float(point.get("y", 0.0))
            z = float(point.get("z", 0.0))
            return cls(x=x, y=y, z=z)
        raise ValueError(f"Cannot convert {type(point)} to Point3D: {point}")


# ---------------------------------------------------------------------------
# Landmark Indices Constants
# ---------------------------------------------------------------------------

class HandLandmark(int, Enum):
    """Standard 21-hand landmark indices (MediaPipe Hand specification)."""
    WRIST = 0
    # Thumb (1-4)
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    # Index finger (5-8)
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    # Middle finger (9-12)
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    # Ring finger (13-16)
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    # Pinky finger (17-20)
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


class GestureType(str, Enum):
    """Recognized hand and face gesture types."""
    # Hand gestures
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    PINCH = "PINCH"
    PINCH_MIDDLE = "PINCH_MIDDLE"
    PINCH_RING = "PINCH_RING"
    PINCH_PINKY = "PINCH_PINKY"
    POINT = "POINT"
    PALM = "PALM"
    FIST = "FIST"
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"
    PEACE = "PEACE"
    ROCK = "ROCK"
    OK_SIGN = "OK_SIGN"
    CALL_ME = "CALL_ME"
    THREE_FINGERS = "THREE_FINGERS"
    FOUR_FINGERS = "FOUR_FINGERS"
    # Face gestures
    BLINK_LEFT = "BLINK_LEFT"
    BLINK_RIGHT = "BLINK_RIGHT"
    BLINK_BOTH = "BLINK_BOTH"
    MOUTH_OPEN = "MOUTH_OPEN"
    SMILE = "SMILE"
    HEAD_NOD = "HEAD_NOD"
    HEAD_SHAKE = "HEAD_SHAKE"


# ---------------------------------------------------------------------------
# Pure Math & Geometry Utilities
# ---------------------------------------------------------------------------

def euclidean_distance(
    p1: Union[Point3D, Sequence[float], Dict[str, float]],
    p2: Union[Point3D, Sequence[float], Dict[str, float]],
    include_z: bool = False,
) -> float:
    """Calculates Euclidean distance between two points (2D or 3D)."""
    pt1 = Point3D.from_any(p1)
    pt2 = Point3D.from_any(p2)
    dx = pt1.x - pt2.x
    dy = pt1.y - pt2.y
    if include_z:
        dz = pt1.z - pt2.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.sqrt(dx * dx + dy * dy)


def manhattan_distance(
    p1: Union[Point3D, Sequence[float], Dict[str, float]],
    p2: Union[Point3D, Sequence[float], Dict[str, float]],
) -> float:
    """Calculates 2D Manhattan distance between two points."""
    pt1 = Point3D.from_any(p1)
    pt2 = Point3D.from_any(p2)
    return abs(pt1.x - pt2.x) + abs(pt1.y - pt2.y)


def angle_between_points(
    a: Union[Point3D, Sequence[float], Dict[str, float]],
    b: Union[Point3D, Sequence[float], Dict[str, float]],
    c: Union[Point3D, Sequence[float], Dict[str, float]],
) -> float:
    """Calculates the angle in degrees at vertex B formed by line segments BA and BC.

    Args:
        a: First endpoint.
        b: Middle vertex.
        c: Second endpoint.

    Returns:
        Angle in degrees between 0.0 and 180.0.
    """
    pt_a = Point3D.from_any(a)
    pt_b = Point3D.from_any(b)
    pt_c = Point3D.from_any(c)

    v1_x = pt_a.x - pt_b.x
    v1_y = pt_a.y - pt_b.y
    v2_x = pt_c.x - pt_b.x
    v2_y = pt_c.y - pt_b.y

    mag1 = math.sqrt(v1_x * v1_x + v1_y * v1_y)
    mag2 = math.sqrt(v2_x * v2_x + v2_y * v2_y)

    if mag1 < 1e-7 or mag2 < 1e-7:
        return 0.0

    dot = v1_x * v2_x + v1_y * v2_y
    cosine = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cosine))


def bounding_box(
    landmarks: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]],
) -> Tuple[float, float, float, float]:
    """Calculates the 2D bounding box (min_x, min_y, max_x, max_y) of a set of landmarks."""
    if not landmarks:
        return (0.0, 0.0, 0.0, 0.0)

    pts = [Point3D.from_any(p) for p in landmarks]
    min_x = min(p.x for p in pts)
    min_y = min(p.y for p in pts)
    max_x = max(p.x for p in pts)
    max_y = max(p.y for p in pts)
    return (min_x, min_y, max_x, max_y)


def center_of_mass(
    landmarks: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]],
) -> Point3D:
    """Calculates centroid of a set of landmarks."""
    if not landmarks:
        return Point3D(0.0, 0.0, 0.0)
    pts = [Point3D.from_any(p) for p in landmarks]
    n = len(pts)
    return Point3D(
        x=sum(p.x for p in pts) / n,
        y=sum(p.y for p in pts) / n,
        z=sum(p.z for p in pts) / n,
    )


# ---------------------------------------------------------------------------
# Hand Gesture Classifier
# ---------------------------------------------------------------------------

@dataclass
class GestureResult:
    """Result of hand gesture classification."""
    gesture: str
    confidence: float
    handedness: str = "Right"
    finger_states: Dict[str, bool] = field(default_factory=dict)
    pinch_distance: float = 0.0
    pinch_point: Optional[Tuple[float, float]] = None
    landmarks: Optional[List[Point3D]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class HandGestureClassifier:
    """Classifies gestures from 21 2D/3D hand landmarks."""

    def __init__(
        self,
        pinch_threshold: float = 0.065,
        curl_threshold: float = 1.1,
        angle_extended_threshold: float = 150.0,
    ) -> None:
        """Initializes the hand gesture classifier.

        Args:
            pinch_threshold: Normalized distance threshold for thumb-index pinch.
            curl_threshold: Ratio threshold for tip-to-wrist vs PIP-to-wrist distance.
            angle_extended_threshold: Joint angle in degrees above which a finger is extended.
        """
        self.pinch_threshold = pinch_threshold
        self.curl_threshold = curl_threshold
        self.angle_extended_threshold = angle_extended_threshold

    def get_hand_scale(self, pts: List[Point3D]) -> float:
        """Computes scale of the hand (distance between wrist and middle MCP).

        Used to normalize distances across varying camera distances.
        """
        if len(pts) <= HandLandmark.MIDDLE_MCP:
            return 1.0
        wrist = pts[HandLandmark.WRIST]
        middle_mcp = pts[HandLandmark.MIDDLE_MCP]
        dist = euclidean_distance(wrist, middle_mcp)
        return max(dist, 0.001)

    def is_finger_extended(
        self,
        pts: List[Point3D],
        finger: str,
        handedness: str = "Right",
        scale: Optional[float] = None,
    ) -> bool:
        """Determines whether a specific finger is extended or curled.

        Args:
            pts: 21 landmark points.
            finger: One of 'thumb', 'index', 'middle', 'ring', 'pinky'.
            handedness: 'Right' or 'Left'.
            scale: Optional normalization hand scale.

        Returns:
            True if finger is extended, False if curled.
        """
        if len(pts) < 21:
            return False

        wrist = pts[HandLandmark.WRIST]

        if finger == "thumb":
            thumb_tip = pts[HandLandmark.THUMB_TIP]
            thumb_ip = pts[HandLandmark.THUMB_IP]
            thumb_mcp = pts[HandLandmark.THUMB_MCP]
            index_mcp = pts[HandLandmark.INDEX_MCP]
            pinky_mcp = pts[HandLandmark.PINKY_MCP]

            # 1. Joint angle at IP
            angle = angle_between_points(thumb_mcp, thumb_ip, thumb_tip)
            # 2. Distance from pinky MCP (thumb extends away from pinky)
            dist_tip_pinky = euclidean_distance(thumb_tip, pinky_mcp)
            dist_mcp_pinky = euclidean_distance(thumb_mcp, pinky_mcp)
            # 3. Distance from index MCP
            dist_tip_index = euclidean_distance(thumb_tip, index_mcp)
            dist_ip_index = euclidean_distance(thumb_ip, index_mcp)
            # 4. Tip distance to thumb MCP vs thumb IP distance to thumb MCP
            dist_tip_mcp = euclidean_distance(thumb_tip, thumb_mcp)
            dist_ip_mcp = euclidean_distance(thumb_ip, thumb_mcp)

            is_straight = angle > 135.0 and dist_tip_mcp > dist_ip_mcp * 1.1
            is_far = (dist_tip_pinky > dist_mcp_pinky * 1.15) or (dist_tip_index > dist_ip_index * 1.15)

            return is_straight and is_far

        # Non-thumb fingers: Index, Middle, Ring, Pinky
        finger_map = {
            "index": (HandLandmark.INDEX_MCP, HandLandmark.INDEX_PIP, HandLandmark.INDEX_DIP, HandLandmark.INDEX_TIP),
            "middle": (HandLandmark.MIDDLE_MCP, HandLandmark.MIDDLE_PIP, HandLandmark.MIDDLE_DIP, HandLandmark.MIDDLE_TIP),
            "ring": (HandLandmark.RING_MCP, HandLandmark.RING_PIP, HandLandmark.RING_DIP, HandLandmark.RING_TIP),
            "pinky": (HandLandmark.PINKY_MCP, HandLandmark.PINKY_PIP, HandLandmark.PINKY_DIP, HandLandmark.PINKY_TIP),
        }

        mcp_idx, pip_idx, dip_idx, tip_idx = finger_map[finger]
        mcp = pts[mcp_idx]
        pip = pts[pip_idx]
        dip = pts[dip_idx]
        tip = pts[tip_idx]

        # Metric 1: Distance from wrist (Tip should be further from wrist than PIP)
        dist_tip_wrist = euclidean_distance(tip, wrist)
        dist_pip_wrist = euclidean_distance(pip, wrist)
        ratio = dist_tip_wrist / max(dist_pip_wrist, 1e-6)

        # Metric 2: Joint angles at PIP and DIP
        angle_pip = angle_between_points(mcp, pip, dip)
        angle_dip = angle_between_points(pip, dip, tip)

        # In standard webcam view (pointing upwards), tip.y < pip.y
        is_extended_y = tip.y < pip.y and tip.y < dip.y
        is_straight = angle_pip > 135.0 and angle_dip > 130.0
        is_farther = ratio > self.curl_threshold

        return (is_farther or is_straight) and (is_extended_y or is_straight)

    def get_finger_states(
        self,
        pts: List[Point3D],
        handedness: str = "Right",
    ) -> Dict[str, bool]:
        """Returns dictionary of boolean extension states for all 5 fingers."""
        scale = self.get_hand_scale(pts)
        return {
            "thumb": self.is_finger_extended(pts, "thumb", handedness, scale),
            "index": self.is_finger_extended(pts, "index", handedness, scale),
            "middle": self.is_finger_extended(pts, "middle", handedness, scale),
            "ring": self.is_finger_extended(pts, "ring", handedness, scale),
            "pinky": self.is_finger_extended(pts, "pinky", handedness, scale),
        }

    def classify(
        self,
        landmarks: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]],
        handedness: str = "Right",
    ) -> GestureResult:
        """Classifies the hand gesture from 21 landmarks.

        Recognizes: PINCH, POINT, PALM, FIST, THUMBS_UP, THUMBS_DOWN, PEACE,
        ROCK, OK_SIGN, CALL_ME, THREE_FINGERS, FOUR_FINGERS.

        Args:
            landmarks: Sequence of 21 landmark points.
            handedness: 'Right' or 'Left'.

        Returns:
            GestureResult with recognized gesture, confidence score, and metrics.
        """
        if not landmarks or len(landmarks) < 21:
            return GestureResult(
                gesture=GestureType.NONE.value,
                confidence=0.0,
                handedness=handedness,
            )

        pts = [Point3D.from_any(p) for p in landmarks]
        scale = self.get_hand_scale(pts)
        finger_states = self.get_finger_states(pts, handedness)

        thumb_ext = finger_states["thumb"]
        index_ext = finger_states["index"]
        middle_ext = finger_states["middle"]
        ring_ext = finger_states["ring"]
        pinky_ext = finger_states["pinky"]

        # Calculate pinch distances (normalized by hand scale)
        thumb_tip = pts[HandLandmark.THUMB_TIP]
        index_tip = pts[HandLandmark.INDEX_TIP]
        middle_tip = pts[HandLandmark.MIDDLE_TIP]
        ring_tip = pts[HandLandmark.RING_TIP]
        pinky_tip = pts[HandLandmark.PINKY_TIP]
        wrist = pts[HandLandmark.WRIST]
        thumb_mcp = pts[HandLandmark.THUMB_MCP]

        raw_pinch_dist = euclidean_distance(thumb_tip, index_tip)
        norm_pinch_dist = raw_pinch_dist / scale

        pinch_center = (
            (thumb_tip.x + index_tip.x) / 2.0,
            (thumb_tip.y + index_tip.y) / 2.0,
        )

        # Multi-finger pinch metrics
        norm_middle_pinch = euclidean_distance(thumb_tip, middle_tip) / scale
        norm_ring_pinch = euclidean_distance(thumb_tip, ring_tip) / scale
        norm_pinky_pinch = euclidean_distance(thumb_tip, pinky_tip) / scale

        is_index_pinch = norm_pinch_dist < self.pinch_threshold
        is_middle_pinch = norm_middle_pinch < self.pinch_threshold

        # Total extended non-thumb fingers count
        extended_non_thumb = sum([index_ext, middle_ext, ring_ext, pinky_ext])

        # 1. OK SIGN (Index pinched to thumb, while middle, ring, pinky extended)
        if is_index_pinch and middle_ext and ring_ext and pinky_ext:
            conf = min(1.0, max(0.6, 1.0 - norm_pinch_dist))
            return GestureResult(
                gesture=GestureType.OK_SIGN.value,
                confidence=conf,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                pinch_point=pinch_center,
                landmarks=pts,
            )

        # 2. PINCH (Thumb tip touching Index tip)
        if is_index_pinch and not (middle_ext and ring_ext and pinky_ext):
            conf = min(1.0, max(0.5, 1.0 - (norm_pinch_dist / self.pinch_threshold) * 0.5))
            return GestureResult(
                gesture=GestureType.PINCH.value,
                confidence=conf,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                pinch_point=pinch_center,
                landmarks=pts,
                metadata={"pinch_type": "index"},
            )

        # 2b. MIDDLE PINCH
        if is_middle_pinch and not index_ext:
            return GestureResult(
                gesture=GestureType.PINCH_MIDDLE.value,
                confidence=0.85,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_middle_pinch,
                landmarks=pts,
            )

        # 3. POINT (Index extended, middle/ring/pinky curled)
        if index_ext and not middle_ext and not ring_ext and not pinky_ext:
            # Check thumb state: point can have thumb relaxed or curled
            conf = 0.95 if not thumb_ext else 0.88
            return GestureResult(
                gesture=GestureType.POINT.value,
                confidence=conf,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
                metadata={"point_tip": (index_tip.x, index_tip.y)},
            )

        # 4. PEACE / VICTORY (Index + Middle extended, ring + pinky curled)
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            return GestureResult(
                gesture=GestureType.PEACE.value,
                confidence=0.92,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        # 5. ROCK / HORNS (Index + Pinky extended, middle + ring curled)
        if index_ext and pinky_ext and not middle_ext and not ring_ext:
            return GestureResult(
                gesture=GestureType.ROCK.value,
                confidence=0.90,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        # 6. CALL ME (Thumb + Pinky extended, index + middle + ring curled)
        if thumb_ext and pinky_ext and not index_ext and not middle_ext and not ring_ext:
            return GestureResult(
                gesture=GestureType.CALL_ME.value,
                confidence=0.88,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        # 7. THUMBS UP / THUMBS DOWN (Thumb extended, 4 other fingers curled)
        if thumb_ext and extended_non_thumb == 0:
            # Evaluate vertical direction: thumb tip relative to thumb MCP & wrist
            is_up = thumb_tip.y < thumb_mcp.y and thumb_tip.y < wrist.y
            is_down = thumb_tip.y > thumb_mcp.y and thumb_tip.y > wrist.y

            if is_up:
                return GestureResult(
                    gesture=GestureType.THUMBS_UP.value,
                    confidence=0.94,
                    handedness=handedness,
                    finger_states=finger_states,
                    pinch_distance=norm_pinch_dist,
                    landmarks=pts,
                )
            elif is_down:
                return GestureResult(
                    gesture=GestureType.THUMBS_DOWN.value,
                    confidence=0.94,
                    handedness=handedness,
                    finger_states=finger_states,
                    pinch_distance=norm_pinch_dist,
                    landmarks=pts,
                )

        # 8. OPEN PALM (All 5 or 4 non-thumb fingers extended)
        if extended_non_thumb == 4 and (thumb_ext or norm_pinch_dist > self.pinch_threshold * 1.5):
            return GestureResult(
                gesture=GestureType.PALM.value,
                confidence=0.96 if thumb_ext else 0.88,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        # 9. FIST (All 5 fingers curled)
        if extended_non_thumb == 0 and not thumb_ext:
            return GestureResult(
                gesture=GestureType.FIST.value,
                confidence=0.95,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        # 10. THREE FINGERS / FOUR FINGERS
        if index_ext and middle_ext and ring_ext and not pinky_ext:
            return GestureResult(
                gesture=GestureType.THREE_FINGERS.value,
                confidence=0.85,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )
        if extended_non_thumb == 4:
            return GestureResult(
                gesture=GestureType.FOUR_FINGERS.value,
                confidence=0.85,
                handedness=handedness,
                finger_states=finger_states,
                pinch_distance=norm_pinch_dist,
                landmarks=pts,
            )

        return GestureResult(
            gesture=GestureType.UNKNOWN.value,
            confidence=0.3,
            handedness=handedness,
            finger_states=finger_states,
            pinch_distance=norm_pinch_dist,
            landmarks=pts,
        )


# ---------------------------------------------------------------------------
# Dwell Detector
# ---------------------------------------------------------------------------

@dataclass
class DwellZone:
    """Represents an interactive dwell zone bounding box."""
    zone_id: str
    bbox: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    dwell_time_ms: float = 800.0
    label: str = ""
    on_trigger: Optional[Callable[[str, Any], None]] = None

    def contains(self, x: float, y: float) -> bool:
        min_x, min_y, max_x, max_y = self.bbox
        return min_x <= x <= max_x and min_y <= y <= max_y


@dataclass
class DwellStatus:
    """Status update from dwell detection step."""
    is_dwelling: bool
    progress: float  # 0.0 to 1.0
    triggered: bool
    elapsed_ms: float
    zone_id: Optional[str] = None
    position: Tuple[float, float] = (0.0, 0.0)


class DwellDetector:
    """Tracks coordinate within bounding box zones over time and triggers events upon dwell completion."""

    def __init__(
        self,
        dwell_time_ms: float = 800.0,
        jitter_radius: float = 0.05,
        retrigger_cooldown_ms: float = 500.0,
    ) -> None:
        """Initializes dwell detector.

        Args:
            dwell_time_ms: Required dwell duration in milliseconds (default 800ms).
            jitter_radius: Radius within which small cursor jitter is tolerated.
            retrigger_cooldown_ms: Cooldown period after triggering before zone can fire again.
        """
        self.default_dwell_time_ms = dwell_time_ms
        self.jitter_radius = jitter_radius
        self.retrigger_cooldown_ms = retrigger_cooldown_ms

        self.zones: Dict[str, DwellZone] = {}
        self.active_zone_id: Optional[str] = None
        self.start_time_ms: Optional[float] = None
        self.last_position: Tuple[float, float] = (0.0, 0.0)
        self.is_triggered: bool = False
        self.last_trigger_time_ms: float = -1e9

    def add_zone(
        self,
        zone_id: str,
        bbox: Tuple[float, float, float, float],
        dwell_time_ms: Optional[float] = None,
        label: str = "",
        on_trigger: Optional[Callable[[str, Any], None]] = None,
    ) -> DwellZone:
        """Registers a new interactive dwell zone.

        Args:
            zone_id: Unique string identifier for zone.
            bbox: (min_x, min_y, max_x, max_y) coordinates.
            dwell_time_ms: Specific dwell time for this zone, or default.
            label: Descriptive label for the zone.
            on_trigger: Callback invoked when dwell completes.

        Returns:
            The created DwellZone instance.
        """
        zone = DwellZone(
            zone_id=zone_id,
            bbox=bbox,
            dwell_time_ms=dwell_time_ms if dwell_time_ms is not None else self.default_dwell_time_ms,
            label=label or zone_id,
            on_trigger=on_trigger,
        )
        self.zones[zone_id] = zone
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        """Removes a registered zone."""
        if zone_id in self.zones:
            del self.zones[zone_id]
            if self.active_zone_id == zone_id:
                self.reset()
            return True
        return False

    def reset(self) -> None:
        """Resets active dwell state."""
        self.active_zone_id = None
        self.start_time_ms = None
        self.is_triggered = False

    def update(
        self,
        x: float,
        y: float,
        timestamp_ms: Optional[float] = None,
        zone_id: Optional[str] = None,
        zone_bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> DwellStatus:
        """Updates dwell tracker with new cursor coordinate.

        Args:
            x: Current X coordinate.
            y: Current Y coordinate.
            timestamp_ms: Current timestamp in ms (defaults to time.time() * 1000).
            zone_id: Optional single ad-hoc zone ID.
            zone_bbox: Optional single ad-hoc zone bounding box.

        Returns:
            DwellStatus indicating dwell progress (0.0 - 1.0) and trigger state.
        """
        current_time = timestamp_ms if timestamp_ms is not None else time.time() * 1000.0
        self.last_position = (x, y)

        # Handle ad-hoc bounding box
        target_zone_id: Optional[str] = None
        required_dwell_ms = self.default_dwell_time_ms

        if zone_bbox is not None:
            min_x, min_y, max_x, max_y = zone_bbox
            if min_x <= x <= max_x and min_y <= y <= max_y:
                target_zone_id = zone_id or "adhoc_zone"
        elif self.zones:
            # Check registered zones
            for zid, zone in self.zones.items():
                if zone.contains(x, y):
                    target_zone_id = zid
                    required_dwell_ms = zone.dwell_time_ms
                    break

        if target_zone_id is None:
            # Cursor is outside any target zone
            self.reset()
            return DwellStatus(
                is_dwelling=False,
                progress=0.0,
                triggered=False,
                elapsed_ms=0.0,
                zone_id=None,
                position=(x, y),
            )

        # Cursor is in a zone
        if self.active_zone_id != target_zone_id:
            # Switched or entered new zone
            self.active_zone_id = target_zone_id
            self.start_time_ms = current_time
            self.is_triggered = False

        elapsed = current_time - (self.start_time_ms or current_time)
        progress = min(1.0, max(0.0, elapsed / max(1.0, required_dwell_ms)))

        triggered_now = False
        if progress >= 1.0 and not self.is_triggered:
            # Check cooldown
            if current_time - self.last_trigger_time_ms >= self.retrigger_cooldown_ms:
                self.is_triggered = True
                self.last_trigger_time_ms = current_time
                triggered_now = True
                # Fire zone callback if available
                if target_zone_id in self.zones and self.zones[target_zone_id].on_trigger:
                    try:
                        self.zones[target_zone_id].on_trigger(target_zone_id, (x, y))
                    except Exception:
                        pass

        return DwellStatus(
            is_dwelling=True,
            progress=progress,
            triggered=triggered_now,
            elapsed_ms=elapsed,
            zone_id=target_zone_id,
            position=(x, y),
        )


# ---------------------------------------------------------------------------
# Face Gesture Classifier (EAR, MAR, Smile)
# ---------------------------------------------------------------------------

@dataclass
class FaceGestureResult:
    """Result of facial landmark analysis and gesture detection."""
    left_ear: float = 0.0
    right_ear: float = 0.0
    avg_ear: float = 0.0
    mar: float = 0.0
    smile_ratio: float = 0.0
    is_left_blink: bool = False
    is_right_blink: bool = False
    is_both_blink: bool = False
    is_mouth_open: bool = False
    is_smiling: bool = False
    active_gestures: List[str] = field(default_factory=list)


class FaceGestureClassifier:
    """Computes Eye Aspect Ratio (EAR), Mouth Aspect Ratio (MAR), and smile curvature."""

    def __init__(
        self,
        ear_blink_threshold: float = 0.21,
        mar_open_threshold: float = 0.55,
        smile_curvature_threshold: float = 0.12,
    ) -> None:
        """Initializes face gesture classifier.

        Args:
            ear_blink_threshold: Eye Aspect Ratio below which blink is detected.
            mar_open_threshold: Mouth Aspect Ratio above which open mouth is detected.
            smile_curvature_threshold: Relative elevation ratio of mouth corners for smile.
        """
        self.ear_blink_threshold = ear_blink_threshold
        self.mar_open_threshold = mar_open_threshold
        self.smile_curvature_threshold = smile_curvature_threshold

    @staticmethod
    def compute_ear(eye_points: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]]) -> float:
        """Calculates Eye Aspect Ratio (EAR) using standard 6-point formulation.

        Formula: EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        where p1, p4 are eye corners and p2, p3, p5, p6 are upper/lower eyelids.

        Args:
            eye_points: 6 landmark points ordered [corner1, top1, top2, corner2, bot2, bot1].

        Returns:
            Calculated Eye Aspect Ratio (float).
        """
        if len(eye_points) < 6:
            return 0.0

        pts = [Point3D.from_any(p) for p in eye_points]
        p1, p2, p3, p4, p5, p6 = pts[0], pts[1], pts[2], pts[3], pts[4], pts[5]

        # Vertical distances
        v1 = euclidean_distance(p2, p6)
        v2 = euclidean_distance(p3, p5)
        # Horizontal distance
        h = euclidean_distance(p1, p4)

        if h < 1e-6:
            return 0.0

        return (v1 + v2) / (2.0 * h)

    @staticmethod
    def compute_mar(mouth_points: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]]) -> float:
        """Calculates Mouth Aspect Ratio (MAR) for mouth openness detection.

        Supports:
        - 8-point outer mouth: [left_corner, top1, top2, top3, right_corner, bot3, bot2, bot1]
        - 4-point cardinal mouth: [left_corner, top_center, right_corner, bot_center]

        Args:
            mouth_points: Sequence of mouth boundary landmarks.

        Returns:
            Calculated Mouth Aspect Ratio (float).
        """
        if len(mouth_points) < 4:
            return 0.0

        pts = [Point3D.from_any(p) for p in mouth_points]

        if len(pts) >= 8:
            # Standard 8-point outer lip formulation
            # p0: left, p1: top-left, p2: top-center, p3: top-right,
            # p4: right, p5: bot-right, p6: bot-center, p7: bot-left
            p0, p1, p2, p3, p4, p5, p6, p7 = pts[:8]
            v1 = euclidean_distance(p1, p7)
            v2 = euclidean_distance(p2, p6)
            v3 = euclidean_distance(p3, p5)
            h = euclidean_distance(p0, p4)
            if h < 1e-6:
                return 0.0
            return (v1 + v2 + v3) / (2.0 * h)
        else:
            # 4-point cardinal representation: [left, top, right, bottom]
            left, top, right, bottom = pts[0], pts[1], pts[2], pts[3]
            v = euclidean_distance(top, bottom)
            h = euclidean_distance(left, right)
            if h < 1e-6:
                return 0.0
            return v / h

    @staticmethod
    def compute_smile_curvature(
        mouth_points: Sequence[Union[Point3D, Sequence[float], Dict[str, float]]],
        nose_point: Optional[Union[Point3D, Sequence[float], Dict[str, float]]] = None,
    ) -> float:
        """Calculates smile curvature based on relative upward elevation of mouth corners.

        Args:
            mouth_points: Mouth landmarks (minimally [left_corner, top_lip, right_corner, bot_lip]
                          or 8-point contour).
            nose_point: Optional reference nose tip landmark.

        Returns:
            Smile curvature ratio (positive indicates corners raised relative to center).
        """
        if len(mouth_points) < 4:
            return 0.0

        pts = [Point3D.from_any(p) for p in mouth_points]
        left_corner = pts[0]
        right_corner = pts[2] if len(pts) == 4 else pts[4]
        top_lip = pts[1] if len(pts) == 4 else pts[2]
        bot_lip = pts[3] if len(pts) == 4 else pts[6]

        lip_center_y = (top_lip.y + bot_lip.y) / 2.0
        corners_avg_y = (left_corner.y + right_corner.y) / 2.0
        mouth_width = euclidean_distance(left_corner, right_corner)

        if mouth_width < 1e-6:
            return 0.0

        # In image coordinates, Y points downward.
        # A smile raises the corners (lower Y value than center).
        elevation = (lip_center_y - corners_avg_y) / mouth_width
        return elevation

    def classify_face(
        self,
        left_eye: Optional[Sequence[Union[Point3D, Sequence[float], Dict[str, float]]]] = None,
        right_eye: Optional[Sequence[Union[Point3D, Sequence[float], Dict[str, float]]]] = None,
        mouth: Optional[Sequence[Union[Point3D, Sequence[float], Dict[str, float]]]] = None,
        face_landmarks: Optional[Dict[str, Any]] = None,
    ) -> FaceGestureResult:
        """Classifies face gestures from landmark subsets.

        Args:
            left_eye: 6 points of left eye.
            right_eye: 6 points of right eye.
            mouth: 4 or 8 points of mouth.
            face_landmarks: Optional dictionary container with 'left_eye', 'right_eye', 'mouth'.

        Returns:
            FaceGestureResult containing metrics and active gesture flags.
        """
        if face_landmarks:
            left_eye = left_eye or face_landmarks.get("left_eye")
            right_eye = right_eye or face_landmarks.get("right_eye")
            mouth = mouth or face_landmarks.get("mouth")

        left_ear = self.compute_ear(left_eye) if left_eye else 0.3
        right_ear = self.compute_ear(right_eye) if right_eye else 0.3
        avg_ear = (left_ear + right_ear) / 2.0

        mar = self.compute_mar(mouth) if mouth else 0.0
        smile_ratio = self.compute_smile_curvature(mouth) if mouth else 0.0

        is_left_blink = bool(left_eye and left_ear < self.ear_blink_threshold)
        is_right_blink = bool(right_eye and right_ear < self.ear_blink_threshold)
        is_both_blink = bool(is_left_blink and is_right_blink)
        is_mouth_open = bool(mouth and mar > self.mar_open_threshold)
        is_smiling = bool(mouth and smile_ratio > self.smile_curvature_threshold)

        active: List[str] = []
        if is_both_blink:
            active.append(GestureType.BLINK_BOTH.value)
        elif is_left_blink:
            active.append(GestureType.BLINK_LEFT.value)
        elif is_right_blink:
            active.append(GestureType.BLINK_RIGHT.value)

        if is_mouth_open:
            active.append(GestureType.MOUTH_OPEN.value)
        if is_smiling:
            active.append(GestureType.SMILE.value)

        return FaceGestureResult(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            mar=mar,
            smile_ratio=smile_ratio,
            is_left_blink=is_left_blink,
            is_right_blink=is_right_blink,
            is_both_blink=is_both_blink,
            is_mouth_open=is_mouth_open,
            is_smiling=is_smiling,
            active_gestures=active,
        )


# ---------------------------------------------------------------------------
# Action Binding Schema & Dispatcher
# ---------------------------------------------------------------------------

@dataclass
class ActionBinding:
    """Maps a gesture event to an action."""
    gesture: str
    action: str
    target: Optional[str] = None
    cooldown_ms: float = 300.0
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActionBinding:
        return cls(
            gesture=str(data.get("gesture", "")),
            action=str(data.get("action", "")),
            target=data.get("target"),
            cooldown_ms=float(data.get("cooldown_ms", 300.0)),
            enabled=bool(data.get("enabled", True)),
            parameters=dict(data.get("parameters", {})),
        )


@dataclass
class ActionBindingSchema:
    """Complete serializable action binding profile."""
    name: str = "Default Profile"
    description: str = "Standard gesture action mappings"
    version: str = "1.0.0"
    bindings: List[ActionBinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "bindings": [b.to_dict() for b in self.bindings],
        }

    def to_json(self, indent: int = 2) -> str:
        """Exports profile to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActionBindingSchema:
        """Parses profile from dictionary."""
        bindings = [ActionBinding.from_dict(b) for b in data.get("bindings", [])]
        return cls(
            name=data.get("name", "Untitled Profile"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            bindings=bindings,
        )

    @classmethod
    def from_json(cls, json_str: str) -> ActionBindingSchema:
        """Parses profile from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """Validates bindings and returns list of error messages (empty if valid)."""
        errors = []
        if not self.name.strip():
            errors.append("Profile name cannot be empty.")
        for idx, b in enumerate(self.bindings):
            if not b.gesture.strip():
                errors.append(f"Binding #{idx + 1}: Missing gesture identifier.")
            if not b.action.strip():
                errors.append(f"Binding #{idx + 1}: Missing action identifier.")
            if b.cooldown_ms < 0:
                errors.append(f"Binding #{idx + 1}: Cooldown cannot be negative.")
        return errors

    def save_to_file(self, path: Union[str, Path]) -> None:
        """Saves schema to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> ActionBindingSchema:
        """Loads schema from JSON file."""
        content = Path(path).read_text(encoding="utf-8")
        return cls.from_json(content)


# ---------------------------------------------------------------------------
# Presets Generator
# ---------------------------------------------------------------------------

def create_presentation_preset() -> ActionBindingSchema:
    """Creates action binding preset for slide presentations."""
    return ActionBindingSchema(
        name="Presentation Mode",
        description="Navigate slides, pause, and control laser pointer",
        bindings=[
            ActionBinding(gesture="PEACE", action="NEXT_SLIDE", cooldown_ms=500.0),
            ActionBinding(gesture="ROCK", action="PREV_SLIDE", cooldown_ms=500.0),
            ActionBinding(gesture="PALM", action="TOGGLE_PAUSE", cooldown_ms=600.0),
            ActionBinding(gesture="POINT", action="LASER_POINTER", cooldown_ms=50.0),
            ActionBinding(gesture="THUMBS_UP", action="START_PRESENTATION", cooldown_ms=1000.0),
            ActionBinding(gesture="FIST", action="BLACKOUT_SCREEN", cooldown_ms=800.0),
        ],
    )


def create_browser_preset() -> ActionBindingSchema:
    """Creates action binding preset for web browsing and media navigation."""
    return ActionBindingSchema(
        name="Browser Navigation Mode",
        description="Scroll, click, tab management, and link navigation",
        bindings=[
            ActionBinding(gesture="PINCH", action="MOUSE_CLICK", cooldown_ms=250.0),
            ActionBinding(gesture="POINT", action="MOVE_CURSOR", cooldown_ms=16.0),
            ActionBinding(gesture="THUMBS_UP", action="SCROLL_UP", cooldown_ms=100.0, parameters={"speed": 15}),
            ActionBinding(gesture="THUMBS_DOWN", action="SCROLL_DOWN", cooldown_ms=100.0, parameters={"speed": 15}),
            ActionBinding(gesture="PEACE", action="NEW_TAB", cooldown_ms=800.0),
            ActionBinding(gesture="FIST", action="CLOSE_TAB", cooldown_ms=1000.0),
            ActionBinding(gesture="PALM", action="STOP_SCROLL", cooldown_ms=200.0),
        ],
    )


def create_media_preset() -> ActionBindingSchema:
    """Creates action binding preset for video/audio player control."""
    return ActionBindingSchema(
        name="Media Player Mode",
        description="Play, pause, volume, and track skipping",
        bindings=[
            ActionBinding(gesture="PALM", action="PLAY_PAUSE", cooldown_ms=500.0),
            ActionBinding(gesture="THUMBS_UP", action="VOLUME_UP", cooldown_ms=150.0, parameters={"step": 5}),
            ActionBinding(gesture="THUMBS_DOWN", action="VOLUME_DOWN", cooldown_ms=150.0, parameters={"step": 5}),
            ActionBinding(gesture="PEACE", action="NEXT_TRACK", cooldown_ms=600.0),
            ActionBinding(gesture="ROCK", action="PREV_TRACK", cooldown_ms=600.0),
            ActionBinding(gesture="FIST", action="MUTE", cooldown_ms=500.0),
        ],
    )


# ---------------------------------------------------------------------------
# Action Dispatcher
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """Outcome of action dispatch."""
    action: str
    gesture: str
    target: Optional[str]
    parameters: Dict[str, Any]
    executed: bool
    message: str = ""


class ActionDispatcher:
    """Dispatches actions triggered by gestures respecting cooldowns and handlers."""

    def __init__(self, schema: Optional[ActionBindingSchema] = None) -> None:
        self.schema = schema or ActionBindingSchema()
        self.handlers: Dict[str, Callable[[ActionBinding, Dict[str, Any]], Any]] = {}
        self.last_triggered_ms: Dict[str, float] = {}

    def register_handler(
        self,
        action_name: str,
        handler: Callable[[ActionBinding, Dict[str, Any]], Any],
    ) -> None:
        """Registers a callback handler for an action identifier."""
        self.handlers[action_name] = handler

    def dispatch(
        self,
        gesture: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp_ms: Optional[float] = None,
    ) -> Optional[ActionResult]:
        """Evaluates gesture against bindings and invokes registered handler if not in cooldown.

        Args:
            gesture: Detected gesture string identifier.
            metadata: Context metadata (e.g. cursor position, hand scale).
            timestamp_ms: Timestamp in ms.

        Returns:
            ActionResult if a binding matched and fired, None otherwise.
        """
        now = timestamp_ms if timestamp_ms is not None else time.time() * 1000.0
        meta = metadata or {}

        for binding in self.schema.bindings:
            if not binding.enabled or binding.gesture != gesture:
                continue

            # Check cooldown
            key = f"{binding.gesture}:{binding.action}"
            last_time = self.last_triggered_ms.get(key, 0.0)
            if now - last_time < binding.cooldown_ms:
                # In cooldown
                return None

            self.last_triggered_ms[key] = now

            handler = self.handlers.get(binding.action)
            executed = False
            msg = ""
            if handler:
                try:
                    handler(binding, meta)
                    executed = True
                    msg = "Handler executed successfully"
                except Exception as e:
                    msg = f"Handler error: {e}"
            else:
                msg = f"No handler registered for action '{binding.action}'"

            return ActionResult(
                action=binding.action,
                gesture=binding.gesture,
                target=binding.target,
                parameters=binding.parameters,
                executed=executed,
                message=msg,
            )

        return None
