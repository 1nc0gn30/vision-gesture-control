"""
MCP Server implementation for vision-gesture-control.
Provides a pure Python stdlib JSON-RPC 2.0 Model Context Protocol (MCP) server over stdio.
"""

from __future__ import annotations

import glob
import json
import math
import os
import platform
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Protocol constants
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "vision-gesture-control-mcp"
SERVER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Core Algorithms (Pure Python stdlib, Zero External Dependencies)
# ---------------------------------------------------------------------------

def _euclidean_distance(p1: Dict[str, float], p2: Dict[str, float], use_3d: bool = True) -> float:
    dx = p1.get("x", 0.0) - p2.get("x", 0.0)
    dy = p1.get("y", 0.0) - p2.get("y", 0.0)
    if use_3d:
        dz = p1.get("z", 0.0) - p2.get("z", 0.0)
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.sqrt(dx * dx + dy * dy)


def _normalize_landmarks(raw_landmarks: Any) -> List[Dict[str, float]]:
    """
    Parses various landmark representations (list of dicts, list of lists/tuples, flat list)
    into a standardized list of 21 landmark dicts with {'x', 'y', 'z'}.
    """
    if not raw_landmarks:
        return []

    # If it's a JSON string, decode it
    if isinstance(raw_landmarks, str):
        try:
            raw_landmarks = json.loads(raw_landmarks)
        except Exception:
            return []

    # If it's a dict containing a landmarks key
    if isinstance(raw_landmarks, dict) and "landmarks" in raw_landmarks:
        raw_landmarks = raw_landmarks["landmarks"]

    normalized: List[Dict[str, float]] = []

    if isinstance(raw_landmarks, list):
        # Case 1: list of coordinate dicts or lists
        if len(raw_landmarks) > 0 and isinstance(raw_landmarks[0], (dict, list, tuple)):
            for item in raw_landmarks:
                if isinstance(item, dict):
                    normalized.append({
                        "x": float(item.get("x", 0.0)),
                        "y": float(item.get("y", 0.0)),
                        "z": float(item.get("z", 0.0)),
                    })
                elif isinstance(item, (list, tuple)):
                    x = float(item[0]) if len(item) > 0 else 0.0
                    y = float(item[1]) if len(item) > 1 else 0.0
                    z = float(item[2]) if len(item) > 2 else 0.0
                    normalized.append({"x": x, "y": y, "z": z})
        # Case 2: flat list of floats [x0, y0, z0, x1, y1, z1, ...] or [x0, y0, ...]
        elif len(raw_landmarks) >= 42:
            step = 3 if len(raw_landmarks) >= 63 else 2
            for i in range(0, min(len(raw_landmarks), 21 * step), step):
                x = float(raw_landmarks[i])
                y = float(raw_landmarks[i + 1]) if i + 1 < len(raw_landmarks) else 0.0
                z = float(raw_landmarks[i + 2]) if step == 3 and i + 2 < len(raw_landmarks) else 0.0
                normalized.append({"x": x, "y": y, "z": z})

    return normalized


def classify_gesture(
    landmarks: Any,
    handedness: str = "Right",
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Classifies 21 3D/2D hand landmarks into gesture types with confidence.
    Follows MediaPipe 21 Hand Landmark indexing.
    """
    pts = _normalize_landmarks(landmarks)

    if len(pts) < 21:
        return {
            "gesture": "unknown",
            "confidence": 0.0,
            "error": f"Expected at least 21 landmarks, received {len(pts)}",
            "handedness": handedness,
            "pinch": {"is_pinching": False, "distance": 1.0, "normalized_distance": 1.0},
            "fingers": {},
            "landmarks_count": len(pts),
        }

    # Reference points
    wrist = pts[0]
    thumb_cmc, thumb_mcp, thumb_ip, thumb_tip = pts[1], pts[2], pts[3], pts[4]
    index_mcp, index_pip, index_dip, index_tip = pts[5], pts[6], pts[7], pts[8]
    middle_mcp, middle_pip, middle_dip, middle_tip = pts[9], pts[10], pts[11], pts[12]
    ring_mcp, ring_pip, ring_dip, ring_tip = pts[13], pts[14], pts[15], pts[16]
    pinky_mcp, pinky_pip, pinky_dip, pinky_tip = pts[17], pts[18], pts[19], pts[20]

    # Hand scale: distance from wrist to middle finger MCP
    hand_scale = _euclidean_distance(wrist, middle_mcp, use_3d=False)
    if hand_scale < 1e-4:
        hand_scale = 0.2  # default fallback normalization

    # Compute pinch distance (Thumb Tip 4 to Index Tip 8)
    pinch_dist_raw = _euclidean_distance(thumb_tip, index_tip, use_3d=True)
    pinch_dist_norm = pinch_dist_raw / hand_scale
    is_pinching = pinch_dist_norm < 0.35

    # Extension test for each finger:
    # A finger is extended if distance(wrist, tip) > distance(wrist, pip) * 1.08
    # and distance(mcp, tip) > distance(mcp, pip) * 1.10
    def is_finger_extended(mcp: Dict[str, float], pip: Dict[str, float], tip: Dict[str, float]) -> Tuple[bool, float]:
        d_wrist_tip = _euclidean_distance(wrist, tip, use_3d=False)
        d_wrist_pip = _euclidean_distance(wrist, pip, use_3d=False)
        d_mcp_tip = _euclidean_distance(mcp, tip, use_3d=False)
        d_mcp_pip = _euclidean_distance(mcp, pip, use_3d=False)

        ratio1 = d_wrist_tip / max(d_wrist_pip, 1e-4)
        ratio2 = d_mcp_tip / max(d_mcp_pip, 1e-4)

        extended = (ratio1 > 1.08) and (ratio2 > 1.10)
        curl_ratio = max(0.0, min(1.0, 1.0 - (ratio2 - 0.8) / 1.0))
        return extended, curl_ratio

    # Thumb extension test:
    # Compare thumb tip distance to pinky MCP vs thumb IP distance to pinky MCP
    d_pinky_thumb_tip = _euclidean_distance(pinky_mcp, thumb_tip, use_3d=False)
    d_pinky_thumb_ip = _euclidean_distance(pinky_mcp, thumb_ip, use_3d=False)
    thumb_extended = (d_pinky_thumb_tip / max(d_pinky_thumb_ip, 1e-4)) > 1.15
    thumb_curl = 0.1 if thumb_extended else 0.85

    idx_ext, idx_curl = is_finger_extended(index_mcp, index_pip, index_tip)
    mid_ext, mid_curl = is_finger_extended(middle_mcp, middle_pip, middle_tip)
    rng_ext, rng_curl = is_finger_extended(ring_mcp, ring_pip, ring_tip)
    pky_ext, pky_curl = is_finger_extended(pinky_mcp, pinky_pip, pinky_tip)

    # Vertical direction check for thumbs up / thumbs down
    thumb_is_up = thumb_tip["y"] < (thumb_mcp["y"] - 0.05 * hand_scale)
    thumb_is_down = thumb_tip["y"] > (thumb_mcp["y"] + 0.05 * hand_scale)

    fingers_state = {
        "thumb": {"extended": thumb_extended, "curl_ratio": round(thumb_curl, 3)},
        "index": {"extended": idx_ext, "curl_ratio": round(idx_curl, 3)},
        "middle": {"extended": mid_ext, "curl_ratio": round(mid_curl, 3)},
        "ring": {"extended": rng_ext, "curl_ratio": round(rng_curl, 3)},
        "pinky": {"extended": pky_ext, "curl_ratio": round(pky_curl, 3)},
    }

    extended_count = sum([thumb_extended, idx_ext, mid_ext, rng_ext, pky_ext])
    non_thumb_extended_count = sum([idx_ext, mid_ext, rng_ext, pky_ext])

    # Classify gesture based on finger extension geometry
    gesture = "neutral"
    confidence = 0.70

    if is_pinching and mid_ext and rng_ext and pky_ext:
        gesture = "ok_sign"
        confidence = 0.94
    elif is_pinching:
        gesture = "pinch"
        confidence = max(0.85, min(0.99, 1.0 - (pinch_dist_norm / 0.35) * 0.2))
    elif non_thumb_extended_count == 0 and not thumb_extended:
        gesture = "fist"
        confidence = 0.95
    elif non_thumb_extended_count == 4 and thumb_extended:
        gesture = "open_palm"
        confidence = 0.98
    elif non_thumb_extended_count == 4 and not thumb_extended:
        gesture = "four_fingers"
        confidence = 0.92
    elif idx_ext and mid_ext and not rng_ext and not pky_ext:
        gesture = "peace_sign"
        confidence = 0.95
    elif idx_ext and not mid_ext and not rng_ext and not pky_ext:
        gesture = "pointing_up"
        confidence = 0.96
    elif idx_ext and mid_ext and rng_ext and not pky_ext:
        gesture = "three_fingers"
        confidence = 0.91
    elif idx_ext and pky_ext and not mid_ext and not rng_ext:
        gesture = "rock_on"
        confidence = 0.94
    elif thumb_extended and pky_ext and not idx_ext and not mid_ext and not rng_ext:
        gesture = "call_me"
        confidence = 0.93
    elif non_thumb_extended_count == 0 and thumb_extended:
        if thumb_is_up:
            gesture = "thumbs_up"
            confidence = 0.95
        elif thumb_is_down:
            gesture = "thumbs_down"
            confidence = 0.95
        else:
            gesture = "thumbs_up"
            confidence = 0.85
    elif non_thumb_extended_count >= 3:
        gesture = "open_palm"
        confidence = 0.82

    # Hand center of mass calculation
    cx = sum(p["x"] for p in pts) / len(pts)
    cy = sum(p["y"] for p in pts) / len(pts)
    cz = sum(p["z"] for p in pts) / len(pts)

    return {
        "gesture": gesture,
        "confidence": round(confidence, 3),
        "handedness": handedness,
        "pinch": {
            "is_pinching": is_pinching,
            "distance": round(pinch_dist_raw, 4),
            "normalized_distance": round(pinch_dist_norm, 4),
        },
        "fingers": fingers_state,
        "landmarks_count": len(pts),
        "hand_center": {"x": round(cx, 4), "y": round(cy, 4), "z": round(cz, 4)},
        "index_tip": {"x": round(index_tip["x"], 4), "y": round(index_tip["y"], 4), "z": round(index_tip["z"], 4)},
        "thumb_tip": {"x": round(thumb_tip["x"], 4), "y": round(thumb_tip["y"], 4), "z": round(thumb_tip["z"], 4)},
    }


def calculate_dwell(
    x: float,
    y: float,
    zone: Union[Dict[str, float], List[float], Tuple[float, ...]],
    duration_ms: float = 1000.0,
    elapsed_ms: float = 0.0,
) -> Dict[str, Any]:
    """
    Evaluates dwell progress for pointer inside target interactive zone.
    Zone can be {'x', 'y', 'width', 'height'}, {'left', 'top', 'right', 'bottom'}, or [x, y, w, h].
    """
    zx, zy, zw, zh = 0.0, 0.0, 0.0, 0.0

    if isinstance(zone, dict):
        if "x" in zone and "width" in zone:
            zx = float(zone["x"])
            zy = float(zone.get("y", 0.0))
            zw = float(zone["width"])
            zh = float(zone.get("height", 0.0))
        elif "left" in zone and "right" in zone:
            zx = float(zone["left"])
            zy = float(zone.get("top", 0.0))
            zw = float(zone["right"]) - zx
            zh = float(zone.get("bottom", 0.0)) - zy
    elif isinstance(zone, (list, tuple)):
        if len(zone) >= 4:
            zx, zy, zw, zh = float(zone[0]), float(zone[1]), float(zone[2]), float(zone[3])

    duration_ms = max(1.0, float(duration_ms))
    elapsed_ms = max(0.0, float(elapsed_ms))

    in_zone = (zx <= x <= zx + zw) and (zy <= y <= zy + zh)

    if in_zone:
        progress = min(1.0, elapsed_ms / duration_ms)
        triggered = progress >= 1.0
        remaining_ms = max(0.0, duration_ms - elapsed_ms)
        dwell_state = "completed" if triggered else ("dwelling" if elapsed_ms > 0 else "entered")
    else:
        progress = 0.0
        triggered = False
        remaining_ms = duration_ms
        dwell_state = "idle" if elapsed_ms == 0 else "exited"

    return {
        "in_zone": in_zone,
        "progress": round(progress, 4),
        "triggered": triggered,
        "elapsed_ms": round(elapsed_ms, 2),
        "duration_ms": round(duration_ms, 2),
        "remaining_ms": round(remaining_ms, 2),
        "dwell_state": dwell_state,
        "pointer": {"x": round(float(x), 4), "y": round(float(y), 4)},
        "zone": {"x": round(zx, 4), "y": round(zy, 4), "width": round(zw, 4), "height": round(zh, 4)},
    }


def classify_face(
    face_landmarks: Any = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Evaluates facial landmarks or features for mouth open, smile, and blinks.
    Accepts full MediaPipe Face Mesh landmarks or feature keypoints.
    """
    # Default metric values
    mouth_open_ratio = 0.0
    smile_score = 0.0
    left_ear = 0.28
    right_ear = 0.28

    if isinstance(face_landmarks, dict):
        mouth_open_ratio = float(face_landmarks.get("mouth_open_ratio", 0.0))
        smile_score = float(face_landmarks.get("smile_score", 0.0))
        left_ear = float(face_landmarks.get("left_ear", 0.28))
        right_ear = float(face_landmarks.get("right_ear", 0.28))
    elif isinstance(face_landmarks, list) and len(face_landmarks) >= 20:
        # Standard MediaPipe Face Mesh key landmark indices:
        # Upper lip top: 13, Lower lip bottom: 14, Left corner: 61, Right corner: 291
        # Left eye: top 159, bottom 145, left 33, right 133
        # Right eye: top 386, bottom 374, left 362, right 263
        pts = _normalize_landmarks(face_landmarks)
        if len(pts) >= 300:
            # Full face mesh
            p13, p14 = pts[13], pts[14]
            p61, p291 = pts[61], pts[291]
            p159, p145, p33, p133 = pts[159], pts[145], pts[33], pts[133]
            p386, p374, p362, p263 = pts[386], pts[374], pts[362], pts[263]

            lip_h = _euclidean_distance(p13, p14, use_3d=False)
            lip_w = _euclidean_distance(p61, p291, use_3d=False)
            mouth_open_ratio = lip_h / max(lip_w, 1e-4)

            # Smile score from mouth width and corner height
            smile_score = min(1.0, max(0.0, (lip_w - 0.15) / 0.15))

            # Eye aspect ratios
            left_eye_h = _euclidean_distance(p159, p145, use_3d=False)
            left_eye_w = _euclidean_distance(p33, p133, use_3d=False)
            left_ear = left_eye_h / max(left_eye_w, 1e-4)

            right_eye_h = _euclidean_distance(p386, p374, use_3d=False)
            right_eye_w = _euclidean_distance(p362, p263, use_3d=False)
            right_ear = right_eye_h / max(right_eye_w, 1e-4)

    # Thresholds
    mouth_open = mouth_open_ratio > 0.35
    smiling = smile_score > 0.50
    left_blink = left_ear < 0.20
    right_blink = right_ear < 0.20
    both_blink = left_blink and right_blink

    expressions = []
    if smiling:
        expressions.append("smiling")
    if mouth_open:
        expressions.append("mouth_open")
    if both_blink:
        expressions.append("both_eyes_closed")
    elif left_blink:
        expressions.append("left_eye_wink")
    elif right_blink:
        expressions.append("right_eye_wink")

    return {
        "mouth_open": mouth_open,
        "mouth_open_ratio": round(mouth_open_ratio, 4),
        "smiling": smiling,
        "smile_score": round(smile_score, 4),
        "left_eye": {
            "blink": left_blink,
            "ear": round(left_ear, 4),
            "open": not left_blink,
        },
        "right_eye": {
            "blink": right_blink,
            "ear": round(right_ear, 4),
            "open": not right_blink,
        },
        "both_eyes_blink": both_blink,
        "expressions": expressions,
        "head_pose_estimate": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
    }


def generate_action_map(
    preset: str = "presentation",
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generates gesture bindings for presentation, media player, drawing, gaming, or accessibility.
    """
    preset_lower = (preset or "presentation").lower().replace("-", "_").replace(" ", "_")

    presets: Dict[str, Dict[str, Any]] = {
        "presentation": {
            "name": "Presentation Mode",
            "description": "Slide deck navigation, laser pointer, and presentation controls",
            "target_app": "Keynote / Google Slides / PowerPoint",
            "cooldown_ms": 600,
            "bindings": {
                "pointing_right": {
                    "action": "next_slide",
                    "key": "Page_Down",
                    "type": "keypress",
                    "description": "Advance to next slide",
                },
                "swipe_right": {
                    "action": "next_slide",
                    "key": "Page_Down",
                    "type": "keypress",
                    "description": "Advance to next slide",
                },
                "pointing_left": {
                    "action": "previous_slide",
                    "key": "Page_Up",
                    "type": "keypress",
                    "description": "Return to previous slide",
                },
                "swipe_left": {
                    "action": "previous_slide",
                    "key": "Page_Up",
                    "type": "keypress",
                    "description": "Return to previous slide",
                },
                "pinch": {
                    "action": "laser_pointer",
                    "key": "Ctrl+L",
                    "type": "toggle",
                    "description": "Toggle laser pointer / spotlight",
                },
                "open_palm": {
                    "action": "blank_screen",
                    "key": "b",
                    "type": "keypress",
                    "description": "Blank screen (black out)",
                },
                "fist": {
                    "action": "exit_slideshow",
                    "key": "Escape",
                    "type": "keypress",
                    "description": "Exit slideshow",
                },
                "peace_sign": {
                    "action": "toggle_timer",
                    "key": "t",
                    "type": "keypress",
                    "description": "Toggle presentation timer",
                },
                "thumbs_up": {
                    "action": "zoom_in",
                    "key": "Ctrl+Plus",
                    "type": "keypress",
                    "description": "Zoom in on current slide",
                },
                "thumbs_down": {
                    "action": "zoom_out",
                    "key": "Ctrl+Minus",
                    "type": "keypress",
                    "description": "Zoom out from current slide",
                },
            },
        },
        "media": {
            "name": "Media Player Control",
            "description": "Hands-free video and audio playback, volume, and seeking",
            "target_app": "Spotify / YouTube / VLC / QuickTime",
            "cooldown_ms": 500,
            "bindings": {
                "open_palm": {
                    "action": "play_pause",
                    "key": "Space",
                    "type": "keypress",
                    "description": "Toggle Play / Pause",
                },
                "thumbs_up": {
                    "action": "volume_up",
                    "key": "ArrowUp",
                    "type": "continuous",
                    "description": "Increase playback volume",
                },
                "thumbs_down": {
                    "action": "volume_down",
                    "key": "ArrowDown",
                    "type": "continuous",
                    "description": "Decrease playback volume",
                },
                "pointing_right": {
                    "action": "seek_forward",
                    "key": "ArrowRight",
                    "type": "keypress",
                    "description": "Seek forward 10 seconds",
                },
                "swipe_right": {
                    "action": "seek_forward",
                    "key": "ArrowRight",
                    "type": "keypress",
                    "description": "Seek forward 10 seconds",
                },
                "pointing_left": {
                    "action": "seek_backward",
                    "key": "ArrowLeft",
                    "type": "keypress",
                    "description": "Seek backward 10 seconds",
                },
                "swipe_left": {
                    "action": "seek_backward",
                    "key": "ArrowLeft",
                    "type": "keypress",
                    "description": "Seek backward 10 seconds",
                },
                "pinch": {
                    "action": "mute_toggle",
                    "key": "m",
                    "type": "toggle",
                    "description": "Mute / Unmute audio",
                },
                "fist": {
                    "action": "stop_playback",
                    "key": "s",
                    "type": "keypress",
                    "description": "Stop playback",
                },
            },
        },
        "media_player": {},  # populated below
        "drawing": {
            "name": "Canvas & Drawing Studio",
            "description": "Natural touchless sketching, color picking, and canvas manipulation",
            "target_app": "Excalidraw / Figma / Photopea / Web Canvas",
            "cooldown_ms": 250,
            "bindings": {
                "pointing_up": {
                    "action": "draw_stroke",
                    "key": "Mouse_Left_Down",
                    "type": "continuous",
                    "description": "Primary draw stroke",
                },
                "pinch": {
                    "action": "color_eyedropper",
                    "key": "i",
                    "type": "keypress",
                    "description": "Pick color under cursor",
                },
                "open_palm": {
                    "action": "pan_canvas",
                    "key": "Space+Drag",
                    "type": "continuous",
                    "description": "Pan / translate canvas view",
                },
                "peace_sign": {
                    "action": "switch_eraser",
                    "key": "e",
                    "type": "toggle",
                    "description": "Toggle eraser mode",
                },
                "fist": {
                    "action": "undo_stroke",
                    "key": "Ctrl+Z",
                    "type": "keypress",
                    "description": "Undo last stroke",
                },
                "rock_on": {
                    "action": "clear_canvas",
                    "key": "Delete",
                    "type": "keypress",
                    "description": "Clear drawing canvas",
                },
            },
        },
        "gaming": {
            "name": "Air Gaming Controller",
            "description": "Gesture-driven input for arcade, retro, and action games",
            "target_app": "Web Games / Emulators",
            "cooldown_ms": 300,
            "bindings": {
                "pointing_up": {
                    "action": "jump",
                    "key": "Space",
                    "type": "keypress",
                    "description": "Jump / Up action",
                },
                "fist": {
                    "action": "primary_attack",
                    "key": "Mouse_Left",
                    "type": "keypress",
                    "description": "Attack / Primary fire",
                },
                "pinch": {
                    "action": "secondary_action",
                    "key": "Mouse_Right",
                    "type": "keypress",
                    "description": "Aim / Block / Secondary",
                },
                "pointing_left": {
                    "action": "move_left",
                    "key": "a",
                    "type": "continuous",
                    "description": "Move left",
                },
                "pointing_right": {
                    "action": "move_right",
                    "key": "d",
                    "type": "continuous",
                    "description": "Move right",
                },
                "open_palm": {
                    "action": "pause_menu",
                    "key": "Escape",
                    "type": "keypress",
                    "description": "Open pause menu",
                },
            },
        },
        "accessibility": {
            "name": "Accessibility & Headless Dwell Navigation",
            "description": "Hands-free cursor control and dwell-based clicking for accessibility",
            "target_app": "Operating System / Web Browser",
            "cooldown_ms": 400,
            "bindings": {
                "pointing_up": {
                    "action": "move_cursor",
                    "key": "Mouse_Move",
                    "type": "continuous",
                    "description": "Track index fingertip as cursor",
                },
                "pinch": {
                    "action": "instant_click",
                    "key": "Mouse_Left_Click",
                    "type": "keypress",
                    "description": "Immediate left click on pinch",
                },
                "dwell": {
                    "action": "dwell_click",
                    "key": "Mouse_Left_Click",
                    "type": "dwell_trigger",
                    "description": "Trigger click after 1000ms hover",
                },
                "fist": {
                    "action": "right_click",
                    "key": "Mouse_Right_Click",
                    "type": "keypress",
                    "description": "Context menu / Right click",
                },
                "open_palm": {
                    "action": "scroll_mode",
                    "key": "Mouse_Scroll",
                    "type": "continuous",
                    "description": "Scroll document by vertical position",
                },
            },
        },
    }
    # Alias media_player to media
    presets["media_player"] = presets["media"]

    selected = presets.get(preset_lower, presets["presentation"]).copy()
    selected["preset_id"] = preset_lower if preset_lower in presets else "presentation"

    if overrides and isinstance(overrides, dict):
        selected["bindings"] = {**selected.get("bindings", {}), **overrides}

    return selected


def get_diagnostics(extended: bool = False) -> Dict[str, Any]:
    """
    Returns system, camera, and compute telemetry.
    """
    uname = platform.uname()

    # Discover camera devices on Linux / Unix
    cameras = []
    video_devices = sorted(glob.glob("/dev/video*"))
    for dev in video_devices:
        accessible = os.access(dev, os.R_OK | os.W_OK)
        cameras.append({"device": dev, "accessible": accessible, "type": "v4l2"})

    if not cameras and uname.system == "Darwin":
        cameras.append({"device": "AVFoundation_Default", "accessible": True, "type": "avfoundation"})
    elif not cameras and uname.system == "Windows":
        cameras.append({"device": "DirectShow_Default", "accessible": True, "type": "directshow"})

    # Session / display info
    display_server = "unknown"
    if "WAYLAND_DISPLAY" in os.environ:
        display_server = "wayland"
    elif "DISPLAY" in os.environ:
        display_server = "x11"
    elif uname.system == "Darwin":
        display_server = "quartz"
    elif uname.system == "Windows":
        display_server = "win32"

    diag = {
        "status": "healthy",
        "timestamp": time.time(),
        "system": {
            "os": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "display_server": display_server,
        },
        "python": {
            "version": platform.python_version(),
            "compiler": platform.python_compiler(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "hardware": {
            "cpu_count": os.cpu_count() or 1,
            "cameras_detected": len(cameras),
            "camera_devices": cameras,
        },
        "telemetry": {
            "time_monotonic": time.monotonic(),
            "time_res_ns": time.get_clock_info("monotonic").resolution,
            "process_pid": os.getpid(),
        },
        "capabilities": [
            "21_hand_landmarks_classification",
            "pinch_detection",
            "dwell_progress_calculation",
            "facial_expression_metrics",
            "action_map_generation",
            "material3_ui_server",
            "mcp_stdio_jsonrpc",
        ],
    }

    if extended:
        # Include environment variables filtered for security
        safe_env = {k: v for k, v in os.environ.items() if not any(s in k.lower() for s in ["key", "secret", "token", "pass", "auth"])}
        diag["environment"] = safe_env

    return diag


def generate_mcp_client_config(
    client_name: str = "claude_desktop",
    python_path: str = "python3",
) -> Dict[str, Any]:
    """
    Generates MCP client configuration snippet for Claude Desktop, Cursor, Cline, or Zed.
    """
    cname = client_name.lower().strip()

    if cname in ("claude_desktop", "claude", "anthropic"):
        return {
            "mcpServers": {
                "vision-gesture-control": {
                    "command": python_path,
                    "args": ["-m", "vision_gesture_control.mcp_server"],
                }
            }
        }
    elif cname in ("cursor", "cursor_ide"):
        return {
            "mcpServers": {
                "vision-gesture-control": {
                    "command": python_path,
                    "args": ["-m", "vision_gesture_control", "mcp"],
                }
            }
        }
    elif cname in ("cline", "roo_cline", "vscode_cline"):
        return {
            "mcpServers": {
                "vision-gesture-control": {
                    "command": python_path,
                    "args": ["-m", "vision_gesture_control.cli", "mcp"],
                    "disabled": False,
                    "autoApprove": [],
                }
            }
        }
    elif cname in ("zed", "zed_editor"):
        return {
            "context_servers": {
                "vision-gesture-control": {
                    "command": {
                        "path": python_path,
                        "args": ["-m", "vision_gesture_control.mcp_server"],
                    }
                }
            }
        }
    elif cname in ("all", "all_clients"):
        return {
            "claude_desktop": generate_mcp_client_config("claude_desktop", python_path),
            "cursor": generate_mcp_client_config("cursor", python_path),
            "cline": generate_mcp_client_config("cline", python_path),
            "zed": generate_mcp_client_config("zed", python_path),
        }
    else:
        # Default fallback: Claude Desktop format
        return {
            "mcpServers": {
                "vision-gesture-control": {
                    "command": python_path,
                    "args": ["-m", "vision_gesture_control.mcp_server"],
                }
            }
        }


# ---------------------------------------------------------------------------
# MCP Tool Schemas (Model Context Protocol JSON Schemas)
# ---------------------------------------------------------------------------

MCP_TOOLS_DEFINITIONS = [
    {
        "name": "vision_classify_gesture",
        "description": "Classifies 21 3D/2D hand landmarks (MediaPipe format) into gesture types (e.g. open_palm, fist, pointing_up, peace_sign, pinch, thumbs_up, rock_on, ok_sign) with confidence score, pinch metrics, and individual finger extension states.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "landmarks": {
                    "description": "Array of 21 3D/2D hand landmarks (dicts with x, y, z or nested coordinate arrays).",
                    "type": "array",
                    "items": {"type": "object"},
                },
                "handedness": {
                    "description": "Handedness label ('Right', 'Left', or 'Unknown').",
                    "type": "string",
                    "default": "Right",
                    "enum": ["Right", "Left", "Unknown"],
                },
                "confidence_threshold": {
                    "description": "Minimum confidence threshold (0.0 - 1.0).",
                    "type": "number",
                    "default": 0.5,
                },
            },
            "required": ["landmarks"],
        },
    },
    {
        "name": "vision_calculate_dwell",
        "description": "Evaluates dwell progress for a pointer inside a target interactive bounding box zone. Returns normalized progress (0.0 to 1.0), trigger state, remaining time, and dwell status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {
                    "description": "Pointer X coordinate (normalized 0.0 - 1.0 or pixel space).",
                    "type": "number",
                },
                "y": {
                    "description": "Pointer Y coordinate (normalized 0.0 - 1.0 or pixel space).",
                    "type": "number",
                },
                "zone": {
                    "description": "Target zone bounding box as {'x', 'y', 'width', 'height'} or [x, y, w, h].",
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "width": {"type": "number"},
                        "height": {"type": "number"},
                    },
                    "required": ["x", "y", "width", "height"],
                },
                "duration_ms": {
                    "description": "Target dwell trigger duration in milliseconds (default: 1000.0).",
                    "type": "number",
                    "default": 1000.0,
                },
                "elapsed_ms": {
                    "description": "Elapsed dwell time inside zone in milliseconds (default: 0.0).",
                    "type": "number",
                    "default": 0.0,
                },
            },
            "required": ["x", "y", "zone"],
        },
    },
    {
        "name": "vision_classify_face",
        "description": "Evaluates facial landmarks or features for mouth opening, smile expression, eye blinks, and eye aspect ratios (EAR).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "face_landmarks": {
                    "description": "Facial landmark points array (MediaPipe Face Mesh 468 points or key points dict).",
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        },
    },
    {
        "name": "vision_generate_action_map",
        "description": "Generates complete gesture-to-action key bindings for presentations, media players, drawing studios, air gaming, or accessibility navigation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "preset": {
                    "description": "Preset action map category.",
                    "type": "string",
                    "enum": ["presentation", "media", "media_player", "drawing", "gaming", "accessibility"],
                    "default": "presentation",
                },
                "overrides": {
                    "description": "Optional custom key/action overrides.",
                    "type": "object",
                },
            },
        },
    },
    {
        "name": "vision_get_diagnostics",
        "description": "Returns system, camera, display server, and compute telemetry diagnostics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "extended": {
                    "description": "Whether to include full system environment telemetry.",
                    "type": "boolean",
                    "default": False,
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# MCP Server Class (JSON-RPC 2.0 stdio engine)
# ---------------------------------------------------------------------------

class MCPServer:
    """
    Stdio JSON-RPC 2.0 Model Context Protocol (MCP) server.
    Zero external dependencies.
    """

    def __init__(self) -> None:
        self.tools = {tool["name"]: tool for tool in MCP_TOOLS_DEFINITIONS}

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an MCP tool and returns structured result."""
        if tool_name == "vision_classify_gesture":
            landmarks = arguments.get("landmarks", [])
            handedness = arguments.get("handedness", "Right")
            confidence_threshold = float(arguments.get("confidence_threshold", 0.5))
            return classify_gesture(landmarks, handedness, confidence_threshold)

        elif tool_name == "vision_calculate_dwell":
            x = float(arguments.get("x", 0.0))
            y = float(arguments.get("y", 0.0))
            zone = arguments.get("zone", {})
            duration_ms = float(arguments.get("duration_ms", 1000.0))
            elapsed_ms = float(arguments.get("elapsed_ms", 0.0))
            return calculate_dwell(x, y, zone, duration_ms, elapsed_ms)

        elif tool_name == "vision_classify_face":
            face_landmarks = arguments.get("face_landmarks", None)
            return classify_face(face_landmarks)

        elif tool_name == "vision_generate_action_map":
            preset = arguments.get("preset", "presentation")
            overrides = arguments.get("overrides", None)
            return generate_action_map(preset, overrides)

        elif tool_name == "vision_get_diagnostics":
            extended = bool(arguments.get("extended", False))
            return get_diagnostics(extended)

        else:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handles a single JSON-RPC 2.0 message and returns response dict, or None for notifications.
        """
        if not isinstance(request, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
            }

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {}) or {}

        # Handle notifications (no id)
        if req_id is None and method.startswith("notifications/"):
            return None

        # Handle methods
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            }

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": MCP_TOOLS_DEFINITIONS,
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {}) or {}

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method / Tool not found: {tool_name}",
                    },
                }

            try:
                result_data = self.execute_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_data, indent=2),
                            }
                        ],
                        "structured_data": result_data,
                        "isError": False,
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error executing tool {tool_name}: {str(e)}",
                            }
                        ],
                        "isError": True,
                    },
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    def run_stdio(self, in_stream=None, out_stream=None) -> None:
        """Runs the stdio MCP server loop."""
        in_stream = in_stream or sys.stdin
        out_stream = out_stream or sys.stdout

        while True:
            try:
                line = in_stream.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                # Handle optional Content-Length HTTP/LSP framing headers
                if line.lower().startswith("content-length:"):
                    # Read until empty line
                    try:
                        content_len = int(line.split(":")[1].strip())
                        while True:
                            h_line = in_stream.readline()
                            if not h_line or h_line.strip() == "":
                                break
                        body = in_stream.read(content_len)
                        request = json.loads(body)
                    except Exception as e:
                        out_stream.write(
                            json.dumps({
                                "jsonrpc": "2.0",
                                "id": None,
                                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                            }) + "\n"
                        )
                        out_stream.flush()
                        continue
                else:
                    try:
                        request = json.loads(line)
                    except Exception as e:
                        out_stream.write(
                            json.dumps({
                                "jsonrpc": "2.0",
                                "id": None,
                                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                            }) + "\n"
                        )
                        out_stream.flush()
                        continue

                response = self.handle_request(request)
                if response is not None:
                    out_stream.write(json.dumps(response) + "\n")
                    out_stream.flush()

            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                # Top-level unexpected error handling
                try:
                    out_stream.write(
                        json.dumps({
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                        }) + "\n"
                    )
                    out_stream.flush()
                except Exception:
                    pass


def main() -> int:
    """CLI entrypoint for running MCP server directly."""
    server = MCPServer()
    server.run_stdio()
    return 0


if __name__ == "__main__":
    sys.exit(main())
