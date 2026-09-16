# 📑 Touchless Presentation Controller

The **Touchless Presentation Controller** is a standalone, web-based slide presentation tool designed for hands-free public speaking, classrooms, conferences, and sterile operating environments.

---

## ✨ Features

- **👋 Touchless Hand Swiping**: Advance slides forward with a natural right swipe, or return backward with a left swipe.
- **🔴 Index Finger Laser Pointer**: Real-time laser pointer attached to your index fingertip with smooth trajectory interpolation.
- **✊ Instant Reset / Deck Overview**: Clench your fist to return immediately to the title slide.
- **🕒 Presenter Timing & Notes**: Built-in stopwatch and dynamic speaker notes synchronized to current slide index.
- **💻 Zero External Dependencies**: Runs entirely offline using modern browser APIs (`Canvas2D`, `getUserMedia`, `Fullscreen API`).
- **🛡️ 100% Local Privacy**: Vision processing executes completely in-memory on your machine; no video frames ever leave the device.

---

## 🚀 Quick Start

### 1. Launch with Python Local Server
```bash
cd examples/presentation-controller
python3 -m http.server 8080
```
Open your browser at `http://localhost:8080`.

### 2. Connect with Vision Gesture Control CLI
Alternatively, run the native Python gesture engine:
```bash
vision-gesture-control presentation --camera 0
```

---

## 🎮 Gesture Reference

| Gesture | Action | Visual HUD Feedback |
| :--- | :--- | :--- |
| **Swipe Right** (`SWIPE_RIGHT`) | Next Slide | `👉 SWIPE_RIGHT` |
| **Swipe Left** (`SWIPE_LEFT`) | Previous Slide | `👈 SWIPE_LEFT` |
| **Pointing Index** (`POINTING_INDEX`) | Toggle / Move Laser Pointer | `☝️ POINTING` (Red Dot) |
| **Closed Fist** (`FIST`) | Reset to Slide 1 | `✊ FIST` |
| **Dwell** (Fixate > 600ms) | Trigger Interactive Slide Actions | `🎯 DWELL_CONFIRM` |

---

## ⌨️ Keyboard Fallbacks

- `ArrowRight` or `Space`: Next Slide
- `ArrowLeft`: Previous Slide
- `L`: Toggle Laser Pointer
- `F`: Toggle Fullscreen Mode

---

## 🔧 Customizing Slides

Edit `examples/presentation-controller/index.html` and modify the `.slide` DOM elements to add your custom HTML content, code snippets, or diagrams.
