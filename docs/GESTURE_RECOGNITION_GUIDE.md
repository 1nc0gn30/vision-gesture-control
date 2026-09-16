# 🖐️ Gesture Recognition & Mathematical Architecture Guide

This guide provides an in-depth technical specification of the mathematical models, geometric heuristics, temporal filtering pipelines, and state machines powering **Vision Gesture Control**.

---

## 📑 Table of Contents
1. [Landmark Coordinate Topology](#1-landmark-coordinate-topology)
2. [Vector Geometry & Joint Angles](#2-vector-geometry--joint-angles)
3. [Palm Plane Orientation](#3-palm-plane-orientation)
4. [Temporal Smoothing & Jitter Reduction](#4-temporal-smoothing--jitter-reduction)
5. [Gesture State Machine & Hysteresis](#5-gesture-state-machine--hysteresis)
6. [Core Gesture Classifications](#6-core-gesture-classifications)
7. [Facial Expression Telemetry (EAR & MAR)](#7-facial-expression-telemetry-ear--mar)
8. [Authoring Custom Gestures in Python](#8-authoring-custom-gestures-in-python)

---

## 1. Landmark Coordinate Topology

The vision engine extracts **21 three-dimensional landmarks** per hand in normalized camera coordinates $(x, y, z) \in [0, 1] \times [0, 1] \times [-1, 1]$:

```
                    8 (INDEX_TIP)
                    |
                    7 (INDEX_DIP)    12 (MIDDLE_TIP)
                    |                |
                    6 (INDEX_PIP)   11 (MIDDLE_DIP)   16 (RING_TIP)
                    |                |                |
   4 (THUMB_TIP)    5 (INDEX_MCP)   10 (MIDDLE_PIP)   15 (RING_DIP)   20 (PINKY_TIP)
        |           |                |                |                |
   3 (THUMB_IP)     |                9 (MIDDLE_MCP)   14 (RING_PIP)   19 (PINKY_DIP)
        |           |                |                |                |
   2 (THUMB_MCP)    |                |                13 (RING_MCP)   18 (PINKY_PIP)
        |           |                |                |                |
   1 (THUMB_CMC)----+----------------+----------------+----------------17 (PINKY_MCP)
                    \                                 /
                     \                               /
                      \                             /
                       \                           /
                        \                         /
                         ------- 0 (WRIST) -------
```

### Landmark Indices Table

| ID | Name | Joint Category | Description |
| :--- | :--- | :--- | :--- |
| `0` | `WRIST` | Base | Root of the hand kinematic chain |
| `1`–`4` | `THUMB_*` | Thumb | CMC (`1`), MCP (`2`), IP (`3`), Tip (`4`) |
| `5`–`8` | `INDEX_*` | Index Finger | MCP (`5`), PIP (`6`), DIP (`7`), Tip (`8`) |
| `9`–`12` | `MIDDLE_*` | Middle Finger | MCP (`9`), PIP (`10`), DIP (`11`), Tip (`12`) |
| `13`–`16` | `RING_*` | Ring Finger | MCP (`13`), PIP (`14`), DIP (`15`), Tip (`16`) |
| `17`–`20` | `PINKY_*` | Pinky Finger | MCP (`17`), PIP (`18`), DIP (`19`), Tip (`20`) |

---

## 2. Vector Geometry & Joint Angles

To determine finger extension and flexion, we compute the interior angle $\theta$ between consecutive bone segments formed by points $\mathbf{A}$, $\mathbf{B}$ (joint vertex), and $\mathbf{C}$:

$$\mathbf{u} = \mathbf{A} - \mathbf{B}, \quad \mathbf{v} = \mathbf{C} - \mathbf{B}$$

$$\theta = \arccos\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}\right) \times \frac{180^\circ}{\pi}$$

```python
import numpy as np

def calculate_joint_angle(p_a: np.ndarray, p_b: np.ndarray, p_c: np.ndarray) -> float:
    """Calculates interior angle in degrees at joint p_b."""
    u = p_a - p_b
    v = p_c - p_b
    cosine_angle = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-7)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine_angle)))
```

### Extension Thresholds:
- **Extended Finger**: $\theta_{\text{PIP}} > 160^\circ$ and $\theta_{\text{DIP}} > 155^\circ$
- **Curled / Folded Finger**: $\theta_{\text{PIP}} < 95^\circ$ and $\theta_{\text{DIP}} < 90^\circ$

---

## 3. Palm Plane Orientation

The orientation of the palm is determined by computing the normal vector $\mathbf{n}_{\text{palm}}$ from the cross product of two non-collinear vectors lying on the palm:

$$\mathbf{v}_1 = \mathbf{P}_{\text{Index\_MCP}} - \mathbf{P}_{\text{Wrist}}$$

$$\mathbf{v}_2 = \mathbf{P}_{\text{Pinky\_MCP}} - \mathbf{P}_{\text{Wrist}}$$

$$\mathbf{n}_{\text{palm}} = \frac{\mathbf{v}_1 \times \mathbf{v}_2}{\|\mathbf{v}_1 \times \mathbf{v}_2\|}$$

- **Facing Camera (Open)**: $n_z < -0.65$
- **Facing Away**: $n_z > 0.65$
- **Side Profile**: $|n_x| > 0.70$

---

## 4. Temporal Smoothing & Jitter Reduction

Raw webcam landmark coordinates exhibit high-frequency jitter. To provide buttery smooth tracking without introducing lag, we implement the **1€ (OneEuro) Adaptive Filter**:

### 1€ Filter Equations:
Given coordinate $x_t$ at timestamp $t$:

$$\text{Speed}: \dot{x}_t = \frac{x_t - \hat{x}_{t-1}}{\Delta t}$$

$$\text{Filtered Speed}: \hat{\dot{x}}_t = \alpha_d \dot{x}_t + (1 - \alpha_d) \hat{\dot{x}}_{t-1}$$

$$\text{Cutoff Frequency}: f_c = f_{c,\min} + \beta |\hat{\dot{x}}_t|$$

$$\text{Smoothing Factor}: \alpha = \frac{1}{1 + \frac{1}{2\pi f_c \Delta t}}$$

$$\text{Filtered Output}: \hat{x}_t = \alpha x_t + (1 - \alpha) \hat{x}_{t-1}$$

When the hand is stationary, $f_c \to f_{c,\min}$, eliminating jitter. When the hand moves rapidly, $f_c$ scales with speed $\beta |\hat{\dot{x}}_t|$, eliminating lag!

---

## 5. Gesture State Machine & Hysteresis

To prevent gesture flickering when near threshold boundaries, each gesture passes through a state debounce automaton:

```
┌────────────────┐      Threshold Met for N Frames      ┌────────────────┐
│   IDLE / NONE  ├─────────────────────────────────────►│    CONFIRMED   │
└───────▲────────┘                                      └───────┬────────┘
        │                                                       │
        │               Below Threshold for M Frames            │
        └───────────────────────────────────────────────────────┘
```

- **Confirmation Window**: $N = 3$ consecutive frames ($\approx 50\text{ms}$).
- **Release Window**: $M = 4$ consecutive frames.
- **Cooldown Timeout**: $T_{\text{cooldown}} = 200\text{ms}$ to prevent repeated trigger spamming.

---

## 6. Core Gesture Classifications

### 1. `PINCH`
- **Definition**: Index fingertip (`8`) proximity to Thumb fingertip (`4`).
- **Equation**: $\|\mathbf{P}_8 - \mathbf{P}_4\| < 0.05 \times \text{PalmSize}$.
- **Use Cases**: Air drawing, object dragging, digital slider manipulation.

### 2. `POINTING_INDEX`
- **Definition**: Index finger fully extended ($\theta_6 > 165^\circ$), other 3 fingers curled ($\theta < 95^\circ$).
- **Use Cases**: Laser pointer presentation mode, UI button hover.

### 3. `SWIPE_LEFT` / `SWIPE_RIGHT`
- **Definition**: Velocity $\frac{\Delta x}{\Delta t} > 0.45\text{ units/s}$ sustained over a window of 5 frames with finger extension preserved.
- **Use Cases**: Slide navigation, page scrolling, media track skipping.

### 4. `FIST`
- **Definition**: All 4 fingers curled into palm ($\theta_{\text{PIP}} < 85^\circ$), thumb folded over fingers.
- **Use Cases**: Deck reset, emergency pause, grab canvas.

### 5. `VICTORY_PEACE`
- **Definition**: Index (`5-8`) and Middle (`9-12`) extended with separation angle $15^\circ < \phi < 45^\circ$, Ring & Pinky curled.
- **Use Cases**: Mode switching, screenshot trigger.

### 6. `DWELL`
- **Definition**: Pointer position variance $\sigma^2 < 0.002$ sustained within radius $r = 0.03$ for duration $\Delta t \ge 600\text{ms}$.
- **Use Cases**: Touchless clicking without physical contact or pinching.

---

## 7. Facial Expression Telemetry (EAR & MAR)

When facial landmarks are present, **Vision Gesture Control** calculates ocular and oral aspect ratios:

### Eye Aspect Ratio (EAR)
Evaluates eyelid closure for blink detection and fatigue analysis:

$$\text{EAR} = \frac{\|\mathbf{P}_2 - \mathbf{P}_6\| + \|\mathbf{P}_3 - \mathbf{P}_5\|}{2 \|\mathbf{P}_1 - \mathbf{P}_4\|}$$

- **Open Eye**: $\text{EAR} \approx 0.28 - 0.35$
- **Blink / Closed**: $\text{EAR} < 0.20$

### Mouth Aspect Ratio (MAR)
Evaluates oral opening for speech, smile, or yawn detection:

$$\text{MAR} = \frac{\|\mathbf{P}_2 - \mathbf{P}_8\| + \|\mathbf{P}_3 - \mathbf{P}_7\| + \|\mathbf{P}_4 - \mathbf{P}_6\|}{2 \|\mathbf{P}_1 - \mathbf{P}_5\|}$$

- **Closed Mouth**: $\text{MAR} < 0.12$
- **Speaking / Open**: $\text{MAR} > 0.35$

---

## 8. Authoring Custom Gestures in Python

You can easily register custom gesture recognizers using the `GestureRecognizer` base class:

```python
from vision_gesture_control.gestures.base import BaseGestureRecognizer, GestureEvent
import numpy as np

class RockOnRecognizer(BaseGestureRecognizer):
    """Recognizes the 'Rock On' (🤘) gesture: Index + Pinky extended, Middle + Ring curled."""
    
    name = "ROCK_ON"
    
    def evaluate(self, landmarks: np.ndarray, handedness: str) -> bool:
        # Check Index (5-8) and Pinky (17-20) extended
        index_extended = self.is_finger_extended(landmarks, 5, 6, 7, 8)
        pinky_extended = self.is_finger_extended(landmarks, 17, 18, 19, 20)
        
        # Check Middle (9-12) and Ring (13-16) curled
        middle_curled = self.is_finger_curled(landmarks, 9, 10, 11, 12)
        ring_curled = self.is_finger_curled(landmarks, 13, 14, 15, 16)
        
        return index_extended and pinky_extended and middle_curled and ring_curled

# Register recognizer
from vision_gesture_control.engine import GestureEngine
engine = GestureEngine()
engine.register_recognizer(RockOnRecognizer())
```
