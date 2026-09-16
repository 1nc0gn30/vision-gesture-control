# 🎨 Touchless Air-Drawing App

The **Touchless Air-Drawing App** is an interactive web canvas that enables users to paint, sketch, and annotate in free 3D air using hand gestures tracked via webcam or computer vision telemetry.

---

## ✨ Key Features

- **🤏 Pinch-to-Draw**: Touch index and thumb tips together in the air to paint continuous, pressure-smoothed strokes.
- **🎨 Material 3 Color Palette**: Select between Google Blue, Red, Yellow, Green, Purple, and Black.
- **🖌️ Adjustable Brush Sizes**: Switch from Fine (4px) to Chisel (28px) with dynamic stroke interpolation.
- **🧹 Open-Palm Wipe**: Hover a wide open hand for 2 seconds to trigger instant canvas clearing.
- **💾 PNG Export**: Save your air drawings directly to high-resolution PNG image files.
- **↩️ Non-Destructive Undo**: Undo prior strokes without latency.

---

## 🚀 Running the App

### Option A: Standard Local Web Server
```bash
cd examples/air-drawing-app
python3 -m http.server 8080
```
Open `http://localhost:8080` in Chrome, Firefox, Safari, or Edge.

### Option B: Vision Gesture Control Native App
```bash
vision-gesture-control draw --camera 0
```

---

## 🎮 Gesture Mapping

| Gesture | Action | Description |
| :--- | :--- | :--- |
| **Pinch** (`PINCH`) | Draw / Paint | Thumb tip + Index tip proximity < 0.05 normalized distance |
| **Open Palm** (`OPEN_PALM`) | Hover / Move | Move pointer across the screen without painting |
| **Wide Palm Hold** | Clear Canvas | Hold open palm in view for 2.0 seconds to wipe the board |
| **Point Index** (`POINTING_INDEX`) | Fine Detail | Precision line drawing using index fingertip |

---

## 🔒 Privacy Guarantee

All vision calculations, landmark skeleton tracking, and gesture classifications run 100% locally in-memory. No raw webcam frames are saved to disk or transmitted over any network.
