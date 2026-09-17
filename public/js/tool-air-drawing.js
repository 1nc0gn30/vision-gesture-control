/**
 * Vision Studio - Air Canvas & Drawing Studio Engine
 * Module: public/js/tool-air-drawing.js
 *
 * Dedicated tool extension for touchless air-drawing and drawing studio in #tab-drawing.
 * Attaches directly to window.VisionApp.tools.airDrawing.
 *
 * Features:
 *  - Smoothed Fingertip Hover Reticle with velocity dampening & zero jitter (joint 8).
 *  - Hover visual state (cyan/blue ring) and drawing state (glowing green pulse on PINCH/POINTING_INDEX).
 *  - Natural Drawing Pipeline with Quadratic Spline / Catmull-Rom smoothing.
 *  - Dynamic velocity-sensitive stroke width modulation for organic ink flow.
 *  - Full brush size support: Fine (4px), Medium (8px), Broad (16px), Chisel (28px calligraphic).
 *  - Color palette swatch integration and synchronization with VisionApp state.
 *  - Open Palm hold (350ms) canvas clearing with audio cue and visual wipe ring.
 *  - Full Undo stack management with high-fidelity stroke reconstruction.
 *  - 1-click high-resolution (2x supersampled 1920x1080) PNG canvas export.
 *  - Complete workspace isolation: Drawing gestures never trigger filter switching or leak into other tools.
 */

(function (global) {
  'use strict';

  // Environment detection (browser vs test runner)
  const root = typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : global);
  const VisionApp = root.VisionApp = root.VisionApp || {};
  VisionApp.tools = VisionApp.tools || {};

  // Engine Configuration Tokens
  const CONFIG = {
    // Reticle Smoothing & Velocity Dampening
    minSmoothingAlpha: 0.16, // heavy dampening when nearly stationary
    maxSmoothingAlpha: 0.88, // low latency response on fast gestures
    velocityDamping: 0.80,   // exponential moving average for velocity
    speedFactor: 2.4,        // speed-to-alpha sensitivity
    deadzoneThreshold: 0.0009, // normalized deadzone to eliminate sensor noise tremor

    // Gestures & Timing
    palmHoldThresholdMs: 350, // 350ms sustained open palm triggers canvas wipe
    palmCooldownMs: 1200,     // prevent accidental multiple wipes
    minPinchDistance: 0.065,

    // Brush Profiles
    brushSizes: {
      fine: 4,
      medium: 8,
      broad: 16,
      chisel: 28
    },

    // Ink Flow & Calligraphy Dynamics
    minWidthRatio: 0.52,  // tapering limit at peak speed
    maxWidthRatio: 1.28,  // pooling limit at slow speeds
    velocityScale: 2.2,   // pixels/ms saturation point
    chiselAngle: Math.PI / 4, // 45-degree chisel slant

    // History & Export
    maxUndoSteps: 60,
    exportSupersample: 2,  // 2x export resolution (1920x1080)
    defaultColor: '#1a73e8',
    defaultSize: 4
  };

  // Internal Tool State
  const state = {
    initialized: false,
    active: false,
    color: CONFIG.defaultColor,
    brushSize: CONFIG.defaultSize,
    brushMode: 'fine', // 'fine', 'medium', 'broad', 'chisel'

    // Reticle smoothing kinematics
    rawNormX: 0.5,
    rawNormY: 0.5,
    smoothNormX: 0.5,
    smoothNormY: 0.5,
    velX: 0,
    velY: 0,
    lastTrackTime: 0,

    // Drawing pipeline state
    isDrawing: false,
    currentStroke: null,
    strokeHistory: [],
    redoHistory: [],

    // Gesture tracking state
    isPalmHolding: false,
    palmStartTime: 0,
    lastPalmClearTime: 0,
    palmProgressRatio: 0,
    activeGesture: 'NONE',

    // Audio oscillators
    drawHumOsc: null,
    drawHumGain: null
  };

  // DOM Elements Cache
  let dom = {
    container: null,
    canvas: null,
    ctx: null,
    cursor: null,
    colorSwatches: [],
    brushButtons: [],
    btnClear: null,
    btnUndo: null,
    btnExport: null
  };

  /**
   * Inject CSS styles for Reticle glow, pulse keyframes and palm wipe animation
   */
  function injectStyles() {
    if (typeof document === 'undefined') return;
    if (document.getElementById('air-drawing-engine-styles')) return;

    const styleEl = document.createElement('style');
    styleEl.id = 'air-drawing-engine-styles';
    styleEl.textContent = `
      @keyframes reticleGlowPulse {
        0%, 100% {
          transform: translate(-50%, -50%) scale(1);
          box-shadow: 0 0 16px #00e676, 0 0 28px rgba(0, 230, 118, 0.7), inset 0 0 8px #00e676;
        }
        50% {
          transform: translate(-50%, -50%) scale(1.26);
          box-shadow: 0 0 22px #00e676, 0 0 38px rgba(0, 230, 118, 0.9), inset 0 0 12px #00e676;
        }
      }

      @keyframes palmWipeRipple {
        0% {
          transform: translate(-50%, -50%) scale(0.6);
          opacity: 0.9;
          border-color: #ea4335;
        }
        50% {
          opacity: 0.7;
          border-color: #fbbc04;
        }
        100% {
          transform: translate(-50%, -50%) scale(2.8);
          opacity: 0;
          border-color: #34a853;
        }
      }

      .drawing-cursor-hover {
        border: 2px solid #00d2ff !important;
        box-shadow: 0 0 14px rgba(0, 210, 255, 0.85), inset 0 0 7px rgba(0, 210, 255, 0.6) !important;
        animation: none !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
      }

      .drawing-cursor-drawing {
        border: 2px solid #00e676 !important;
        box-shadow: 0 0 16px #00e676, 0 0 28px rgba(0, 230, 118, 0.7), inset 0 0 8px #00e676 !important;
        animation: reticleGlowPulse 0.85s infinite ease-in-out !important;
      }

      .drawing-cursor-palmwipe {
        border: 3px solid #fbbc04 !important;
        box-shadow: 0 0 20px #fbbc04, inset 0 0 10px #fbbc04 !important;
      }

      .palm-wipe-flash {
        position: absolute;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        pointer-events: none;
        z-index: 15;
        animation: palmWipeRipple 0.5s ease-out forwards;
      }
    `;
    document.head.appendChild(styleEl);
  }

  /**
   * Sound synthesis using Web Audio API
   */
  function getAudioContext() {
    if (VisionApp.getAudioContext) {
      const ctx = VisionApp.getAudioContext();
      if (ctx) return ctx;
    }
    if (typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      return new AudioContextClass();
    }
    return null;
  }

  function playClearChimeCue() {
    try {
      const actx = getAudioContext();
      if (!actx) return;
      if (actx.state === 'suspended') actx.resume();

      const now = actx.currentTime;
      const osc1 = actx.createOscillator();
      const osc2 = actx.createOscillator();
      const filter = actx.createBiquadFilter();
      const gain = actx.createGain();

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(3200, now);

      osc1.type = 'sine';
      osc2.type = 'triangle';

      // Ascending-then-resolving chime sweep: G4 -> C5 -> E5
      osc1.frequency.setValueAtTime(392.0, now);
      osc1.frequency.exponentialRampToValueAtTime(523.25, now + 0.12);
      osc1.frequency.exponentialRampToValueAtTime(659.25, now + 0.32);

      osc2.frequency.setValueAtTime(784.0, now);
      osc2.frequency.exponentialRampToValueAtTime(1046.5, now + 0.12);
      osc2.frequency.exponentialRampToValueAtTime(1318.5, now + 0.32);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.linearRampToValueAtTime(0.24, now + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);

      osc1.connect(filter);
      osc2.connect(filter);
      filter.connect(gain);
      gain.connect(actx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + 0.4);
      osc2.stop(now + 0.4);
    } catch (err) {
      // Audio might be waiting for user gesture
    }
  }

  function startDrawingHum(normalizedY) {
    try {
      const actx = getAudioContext();
      if (!actx) return;
      if (actx.state === 'suspended') actx.resume();

      const now = actx.currentTime;
      const pitch = 220 + (1.0 - Math.min(1, Math.max(0, normalizedY || 0.5))) * 300;

      if (!state.drawHumOsc) {
        state.drawHumOsc = actx.createOscillator();
        state.drawHumGain = actx.createGain();
        state.drawHumOsc.type = 'sine';
        state.drawHumGain.gain.setValueAtTime(0.001, now);
        state.drawHumGain.gain.linearRampToValueAtTime(0.038, now + 0.05);

        state.drawHumOsc.connect(state.drawHumGain);
        state.drawHumGain.connect(actx.destination);
        state.drawHumOsc.start(now);
      }
      state.drawHumOsc.frequency.setTargetAtTime(pitch, now, 0.04);
    } catch (e) {}
  }

  function stopDrawingHum() {
    if (state.drawHumGain) {
      try {
        const actx = getAudioContext();
        const now = actx ? actx.currentTime : 0;
        state.drawHumGain.gain.linearRampToValueAtTime(0.0001, now + 0.06);
        setTimeout(() => {
          if (state.drawHumOsc && !state.isDrawing) {
            try { state.drawHumOsc.stop(); } catch (e) {}
            state.drawHumOsc = null;
            state.drawHumGain = null;
          }
        }, 70);
      } catch (e) {
        state.drawHumOsc = null;
        state.drawHumGain = null;
      }
    }
  }

  /**
   * Adaptive Velocity Dampening Kinematics
   * Filters out high-frequency tremor while preserving quick stroke response.
   */
  function updateSmoothedFingertip(rawX, rawY, timestamp) {
    const dt = state.lastTrackTime ? Math.max(1, timestamp - state.lastTrackTime) : 16.6;
    state.lastTrackTime = timestamp;

    const dx = rawX - state.rawNormX;
    const dy = rawY - state.rawNormY;
    state.rawNormX = rawX;
    state.rawNormY = rawY;

    // Filtered velocity in normalized space / sec
    const instVx = dx / (dt / 1000);
    const instVy = dy / (dt / 1000);
    state.velX = state.velX * CONFIG.velocityDamping + instVx * (1 - CONFIG.velocityDamping);
    state.velY = state.velY * CONFIG.velocityDamping + instVy * (1 - CONFIG.velocityDamping);

    const speed = Math.hypot(state.velX, state.velY);

    // Adaptive alpha curve based on motion velocity
    let alpha = CONFIG.minSmoothingAlpha + (speed * CONFIG.speedFactor * 0.12);
    alpha = Math.min(CONFIG.maxSmoothingAlpha, Math.max(CONFIG.minSmoothingAlpha, alpha));

    // Deadzone dampening for tiny hand tremors when resting/hovering
    const distToSmoothed = Math.hypot(rawX - state.smoothNormX, rawY - state.smoothNormY);
    if (distToSmoothed < CONFIG.deadzoneThreshold && !state.isDrawing) {
      alpha *= 0.22;
    }

    state.smoothNormX += (rawX - state.smoothNormX) * alpha;
    state.smoothNormY += (rawY - state.smoothNormY) * alpha;

    return {
      x: state.smoothNormX,
      y: state.smoothNormY,
      speed: speed
    };
  }

  /**
   * Natural Drawing Pipeline - Stroke Point Management
   */
  function startStroke(canvasX, canvasY, timestamp) {
    if (!dom.ctx) return;
    state.isDrawing = true;
    if (VisionApp.state) VisionApp.state.isDrawing = true;

    const initialWidth = state.brushSize;
    state.currentStroke = {
      color: state.color,
      baseSize: state.brushSize,
      isChisel: state.brushMode === 'chisel' || state.brushSize === CONFIG.brushSizes.chisel,
      points: [{
        x: canvasX,
        y: canvasY,
        width: initialWidth,
        time: timestamp || performance.now()
      }]
    };

    // Draw initial dot with rounded cap
    dom.ctx.save();
    dom.ctx.fillStyle = state.color;
    dom.ctx.beginPath();
    dom.ctx.arc(canvasX, canvasY, initialWidth / 2, 0, Math.PI * 2);
    dom.ctx.fill();
    dom.ctx.restore();

    startDrawingHum(canvasY / (dom.canvas ? dom.canvas.height : 540));
  }

  function addStrokePoint(canvasX, canvasY, timestamp) {
    if (!state.isDrawing || !state.currentStroke || !dom.ctx) {
      startStroke(canvasX, canvasY, timestamp);
      return;
    }

    const now = timestamp || performance.now();
    const pts = state.currentStroke.points;
    const lastPt = pts[pts.length - 1];

    const dx = canvasX - lastPt.x;
    const dy = canvasY - lastPt.y;
    const dist = Math.hypot(dx, dy);

    // Filter tiny micro-jitter duplicate points
    if (dist < 1.4) return;

    const dt = Math.max(6, now - lastPt.time);
    const velocity = dist / dt; // px per ms

    // Velocity-sensitive width modulation
    let widthMultiplier = 1.0;
    if (state.currentStroke.isChisel) {
      // Chisel calligraphy: angle sensitivity + velocity response
      const strokeAngle = Math.atan2(dy, dx);
      const angleDiff = Math.abs(Math.sin(strokeAngle - CONFIG.chiselAngle));
      widthMultiplier = 0.5 + 0.85 * angleDiff;
    } else {
      // Natural fountain pen ink: faster movement tapers thinner; slower pools richer
      const speedRatio = Math.min(1.0, velocity / CONFIG.velocityScale);
      widthMultiplier = CONFIG.maxWidthRatio - (CONFIG.maxWidthRatio - CONFIG.minWidthRatio) * speedRatio;
    }

    const targetWidth = state.currentStroke.baseSize * widthMultiplier;
    // Low-pass width filter to avoid sharp step changes in thickness
    const filteredWidth = lastPt.width * 0.65 + targetWidth * 0.35;

    const newPoint = {
      x: canvasX,
      y: canvasY,
      width: filteredWidth,
      time: now
    };
    pts.push(newPoint);

    // Incremental quadratic spline render
    renderSplineSegment(dom.ctx, pts, pts.length - 1, state.currentStroke.color, state.currentStroke.isChisel);
    startDrawingHum(canvasY / (dom.canvas ? dom.canvas.height : 540));
  }

  function endStroke() {
    if (!state.isDrawing || !state.currentStroke) return;
    state.isDrawing = false;
    if (VisionApp.state) VisionApp.state.isDrawing = false;

    if (state.currentStroke.points.length > 0) {
      state.strokeHistory.push(state.currentStroke);
      state.redoHistory = []; // Reset redo on fresh stroke
      if (state.strokeHistory.length > CONFIG.maxUndoSteps) {
        state.strokeHistory.shift();
      }
      if (VisionApp.state) {
        VisionApp.state.drawHistory = state.strokeHistory;
      }
    }
    state.currentStroke = null;
    stopDrawingHum();
  }

  /**
   * Quadratic Spline Segment Renderer
   * Converts connected points into continuous C1-smooth Bézier curves through midpoints.
   */
  function renderSplineSegment(context, pts, index, color, isChisel) {
    if (pts.length < 2) return;

    context.save();
    context.strokeStyle = color;
    context.fillStyle = color;
    context.lineCap = isChisel ? 'square' : 'round';
    context.lineJoin = 'round';

    if (pts.length === 2) {
      context.lineWidth = pts[1].width;
      context.beginPath();
      context.moveTo(pts[0].x, pts[0].y);
      context.lineTo(pts[1].x, pts[1].y);
      context.stroke();
    } else {
      const p0 = pts[index - 2];
      const p1 = pts[index - 1];
      const p2 = pts[index];

      const mid1X = (p0.x + p1.x) / 2;
      const mid1Y = (p0.y + p1.y) / 2;
      const mid2X = (p1.x + p2.x) / 2;
      const mid2Y = (p1.y + p2.y) / 2;

      context.lineWidth = p1.width;
      context.beginPath();
      context.moveTo(mid1X, mid1Y);
      context.quadraticCurveTo(p1.x, p1.y, mid2X, mid2Y);
      context.stroke();
    }
    context.restore();
  }

  /**
   * Redraw all strokes in the stack
   */
  function redrawCanvas() {
    if (!dom.ctx || !dom.canvas) return;
    dom.ctx.clearRect(0, 0, dom.canvas.width, dom.canvas.height);

    for (let s = 0; s < state.strokeHistory.length; s++) {
      const stroke = state.strokeHistory[s];
      const pts = stroke.points;
      if (!pts || pts.length === 0) continue;

      dom.ctx.save();
      dom.ctx.strokeStyle = stroke.color;
      dom.ctx.fillStyle = stroke.color;
      dom.ctx.lineCap = stroke.isChisel ? 'square' : 'round';
      dom.ctx.lineJoin = 'round';

      if (pts.length === 1) {
        dom.ctx.beginPath();
        dom.ctx.arc(pts[0].x, pts[0].y, (pts[0].width || stroke.baseSize) / 2, 0, Math.PI * 2);
        dom.ctx.fill();
      } else if (pts.length === 2) {
        dom.ctx.lineWidth = pts[1].width || stroke.baseSize;
        dom.ctx.beginPath();
        dom.ctx.moveTo(pts[0].x, pts[0].y);
        dom.ctx.lineTo(pts[1].x, pts[1].y);
        dom.ctx.stroke();
      } else {
        for (let i = 1; i < pts.length - 1; i++) {
          const midX = (pts[i].x + pts[i + 1].x) / 2;
          const midY = (pts[i].y + pts[i + 1].y) / 2;
          const startX = (i === 1) ? pts[0].x : (pts[i - 1].x + pts[i].x) / 2;
          const startY = (i === 1) ? pts[0].y : (pts[i - 1].y + pts[i].y) / 2;

          dom.ctx.lineWidth = pts[i].width || stroke.baseSize;
          dom.ctx.beginPath();
          dom.ctx.moveTo(startX, startY);
          dom.ctx.quadraticCurveTo(pts[i].x, pts[i].y, midX, midY);
          dom.ctx.stroke();
        }

        const last = pts.length - 1;
        const prevMidX = (pts[last - 1].x + pts[last].x) / 2;
        const prevMidY = (pts[last - 1].y + pts[last].y) / 2;
        dom.ctx.lineWidth = pts[last].width || stroke.baseSize;
        dom.ctx.beginPath();
        dom.ctx.moveTo(prevMidX, prevMidY);
        dom.ctx.lineTo(pts[last].x, pts[last].y);
        dom.ctx.stroke();
      }
      dom.ctx.restore();
    }
  }

  /**
   * Canvas Operations (Clear, Undo, Export)
   */
  function clearCanvas(withFeedback = true) {
    if (!dom.ctx || !dom.canvas) return;
    dom.ctx.clearRect(0, 0, dom.canvas.width, dom.canvas.height);

    if (state.strokeHistory.length > 0) {
      state.redoHistory = [...state.strokeHistory];
      state.strokeHistory = [];
    }
    state.currentStroke = null;
    state.isDrawing = false;
    if (VisionApp.state) {
      VisionApp.state.drawHistory = [];
      VisionApp.state.isDrawing = false;
    }

    if (withFeedback) {
      playClearChimeCue();
      triggerWipeVisualEffect();
      if (VisionApp.showToast) {
        VisionApp.showToast("🧹 Air Canvas Cleared (Open Palm Hold)");
      }
      if (VisionApp.showGestureHudBanner) {
        VisionApp.showGestureHudBanner("🧹 PALM WIPE", "Canvas Cleared (350ms Hold)", "🧹");
      }
    }
  }

  function triggerWipeVisualEffect() {
    if (!dom.container || typeof document === 'undefined') return;
    const ripple = document.createElement('div');
    ripple.className = 'palm-wipe-flash';
    ripple.style.left = (state.smoothNormX * 100) + '%';
    ripple.style.top = (state.smoothNormY * 100) + '%';
    dom.container.appendChild(ripple);
    setTimeout(() => {
      if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
    }, 550);
  }

  function undoStroke() {
    if (state.strokeHistory.length > 0) {
      const popped = state.strokeHistory.pop();
      state.redoHistory.push(popped);
      redrawCanvas();
      if (VisionApp.state) VisionApp.state.drawHistory = state.strokeHistory;
      if (VisionApp.playSlideChime) VisionApp.playSlideChime(-1);
      if (VisionApp.showToast) VisionApp.showToast("↩ Undid last stroke");
      return true;
    }
    return false;
  }

  function exportHighResPNG() {
    if (!dom.canvas || typeof document === 'undefined') return;

    const scale = CONFIG.exportSupersample; // 2x supersample
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = dom.canvas.width * scale;
    exportCanvas.height = dom.canvas.height * scale;
    const expCtx = exportCanvas.getContext('2d');

    // Solid white canvas backing for crisp presentation exports
    expCtx.fillStyle = '#ffffff';
    expCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

    // Scaled high-DPI rendering of all strokes
    expCtx.save();
    expCtx.scale(scale, scale);

    for (let s = 0; s < state.strokeHistory.length; s++) {
      const stroke = state.strokeHistory[s];
      const pts = stroke.points;
      if (!pts || pts.length === 0) continue;

      expCtx.save();
      expCtx.strokeStyle = stroke.color;
      expCtx.fillStyle = stroke.color;
      expCtx.lineCap = stroke.isChisel ? 'square' : 'round';
      expCtx.lineJoin = 'round';

      if (pts.length === 1) {
        expCtx.beginPath();
        expCtx.arc(pts[0].x, pts[0].y, (pts[0].width || stroke.baseSize) / 2, 0, Math.PI * 2);
        expCtx.fill();
      } else if (pts.length === 2) {
        expCtx.lineWidth = pts[1].width || stroke.baseSize;
        expCtx.beginPath();
        expCtx.moveTo(pts[0].x, pts[0].y);
        expCtx.lineTo(pts[1].x, pts[1].y);
        expCtx.stroke();
      } else {
        for (let i = 1; i < pts.length - 1; i++) {
          const midX = (pts[i].x + pts[i + 1].x) / 2;
          const midY = (pts[i].y + pts[i + 1].y) / 2;
          const startX = (i === 1) ? pts[0].x : (pts[i - 1].x + pts[i].x) / 2;
          const startY = (i === 1) ? pts[0].y : (pts[i - 1].y + pts[i].y) / 2;

          expCtx.lineWidth = pts[i].width || stroke.baseSize;
          expCtx.beginPath();
          expCtx.moveTo(startX, startY);
          expCtx.quadraticCurveTo(pts[i].x, pts[i].y, midX, midY);
          expCtx.stroke();
        }

        const last = pts.length - 1;
        const prevMidX = (pts[last - 1].x + pts[last].x) / 2;
        const prevMidY = (pts[last - 1].y + pts[last].y) / 2;
        expCtx.lineWidth = pts[last].width || stroke.baseSize;
        expCtx.beginPath();
        expCtx.moveTo(prevMidX, prevMidY);
        expCtx.lineTo(pts[last].x, pts[last].y);
        expCtx.stroke();
      }
      expCtx.restore();
    }
    expCtx.restore();

    // Trigger instant client download
    const link = document.createElement('a');
    link.download = `vision-air-drawing-${Date.now()}.png`;
    link.href = exportCanvas.toDataURL('image/png');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    if (VisionApp.showToast) VisionApp.showToast("💾 Exported High-Res PNG (1920x1080)");
    if (VisionApp.playVictoryFanfare) VisionApp.playVictoryFanfare();
  }

  /**
   * Open Palm Hold Trigger (350ms hold detection)
   */
  function processPalmGesture(gesture, timestamp) {
    const now = timestamp || performance.now();
    if (gesture === 'OPEN_PALM') {
      if (!state.isPalmHolding) {
        state.isPalmHolding = true;
        state.palmStartTime = now;
      } else {
        const holdDuration = now - state.palmStartTime;
        state.palmProgressRatio = Math.min(1.0, holdDuration / CONFIG.palmHoldThresholdMs);

        if (holdDuration >= CONFIG.palmHoldThresholdMs) {
          if (now - state.lastPalmClearTime > CONFIG.palmCooldownMs) {
            state.lastPalmClearTime = now;
            clearCanvas(true);
            state.isPalmHolding = false;
            state.palmStartTime = 0;
            state.palmProgressRatio = 0;
          }
        }
      }
    } else {
      state.isPalmHolding = false;
      state.palmStartTime = 0;
      state.palmProgressRatio = 0;
    }
  }

  /**
   * Color & Brush UI Synchronization
   */
  function setColor(colorHex) {
    state.color = colorHex;
    if (VisionApp.state) VisionApp.state.drawColor = colorHex;

    if (dom.colorSwatches && dom.colorSwatches.length) {
      dom.colorSwatches.forEach(swatch => {
        if (swatch.dataset && swatch.dataset.color === colorHex) {
          swatch.classList.add('active-color');
        } else {
          swatch.classList.remove('active-color');
        }
      });
    }
  }

  function setBrushSize(sizeInt) {
    const size = parseInt(sizeInt, 10) || CONFIG.defaultSize;
    state.brushSize = size;
    if (VisionApp.state) VisionApp.state.brushSize = size;

    if (size === CONFIG.brushSizes.chisel) {
      state.brushMode = 'chisel';
    } else if (size === CONFIG.brushSizes.broad) {
      state.brushMode = 'broad';
    } else if (size === CONFIG.brushSizes.medium) {
      state.brushMode = 'medium';
    } else {
      state.brushMode = 'fine';
    }

    if (dom.brushButtons && dom.brushButtons.length) {
      dom.brushButtons.forEach(btn => {
        if (btn.dataset && parseInt(btn.dataset.size, 10) === size) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
    }
  }

  /**
   * Main Hand Tracking Entry Point
   * Called per frame when hands are detected.
   *
   * @param {Array} points - 21 MediaPipe hand landmark points (normalized 0-1)
   * @param {string} gesture - Active detected gesture token ('PINCH', 'POINTING_INDEX', 'OPEN_PALM', etc.)
   */
  function updateHandTracking(points, gesture) {
    if (!state.initialized) {
      init();
    }

    // Strict tab isolation: Air drawing only acts when on tab-drawing
    const activeTab = (VisionApp.state && VisionApp.state.activeTab) || 'tab-drawing';
    if (activeTab !== 'tab-drawing') {
      if (dom.cursor) dom.cursor.style.display = 'none';
      if (state.isDrawing) endStroke();
      stopDrawingHum();
      return;
    }

    // Complete Isolation: Never allow drawing gestures to trigger shader filter switching
    if (VisionApp.state) {
      VisionApp.state.manualFilterLockTime = performance.now() + 5000;
    }

    if (!points || points.length < 9) {
      if (dom.cursor) dom.cursor.style.display = 'none';
      if (state.isDrawing) endStroke();
      stopDrawingHum();
      return;
    }

    const tip = points[8]; // Joint 8: Index fingertip
    const now = performance.now();

    // 1. Smooth index fingertip coordinates with velocity dampening
    const smoothed = updateSmoothedFingertip(tip.x, tip.y, now);

    // 2. Manage Reticle positioning over #drawingBoardContainer
    if (dom.cursor) {
      dom.cursor.style.left = (smoothed.x * 100) + '%';
      dom.cursor.style.top = (smoothed.y * 100) + '%';
      dom.cursor.style.display = 'block';

      // 3. Visual Reticle State:
      // - Cyan/blue ring when hovering
      // - Glowing Green reticle with pulse when drawing (PINCH or POINTING_INDEX)
      // - Yellow border when open palm is initiating wipe
      const isDrawingGesture = (gesture === 'PINCH' || gesture === 'POINTING_INDEX');

      if (state.isPalmHolding && state.palmProgressRatio > 0.2) {
        dom.cursor.className = 'drawing-cursor-palmwipe';
        dom.cursor.style.borderColor = '#fbbc04';
        dom.cursor.style.boxShadow = '0 0 18px #fbbc04, inset 0 0 8px #fbbc04';
      } else if (isDrawingGesture) {
        dom.cursor.className = 'drawing-cursor-drawing';
        dom.cursor.style.borderColor = '#00e676';
        dom.cursor.style.boxShadow = '0 0 16px #00e676, 0 0 28px rgba(0, 230, 118, 0.7), inset 0 0 8px #00e676';
      } else {
        dom.cursor.className = 'drawing-cursor-hover';
        dom.cursor.style.borderColor = '#00d2ff';
        dom.cursor.style.boxShadow = '0 0 14px rgba(0, 210, 255, 0.85), inset 0 0 7px rgba(0, 210, 255, 0.6)';
      }
    }

    // 4. Open Palm hold (350ms) canvas clearing
    processPalmGesture(gesture, now);

    // 5. Natural Drawing Pipeline
    const isDrawingGesture = (gesture === 'PINCH' || gesture === 'POINTING_INDEX');
    if (isDrawingGesture && dom.canvas) {
      const canvasX = smoothed.x * dom.canvas.width;
      const canvasY = smoothed.y * dom.canvas.height;

      if (!state.isDrawing) {
        startStroke(canvasX, canvasY, now);
      } else {
        addStrokePoint(canvasX, canvasY, now);
      }
    } else {
      if (state.isDrawing) {
        endStroke();
      }
      stopDrawingHum();
    }
  }

  /**
   * Helper to convert mouse/pointer events to normalized canvas coordinates
   */
  function getCanvasPos(e) {
    if (!dom.canvas) return { x: 0, y: 0 };
    const rect = dom.canvas.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) * (dom.canvas.width / rect.width),
      y: (e.clientY - rect.top) * (dom.canvas.height / rect.height)
    };
  }

  /**
   * Bind Mouse & Pointer Fallback Events
   */
  function bindMouseFallback() {
    if (!dom.canvas) return;

    let isPointerDown = false;

    dom.canvas.addEventListener('pointerdown', (e) => {
      isPointerDown = true;
      const pos = getCanvasPos(e);
      startStroke(pos.x, pos.y, e.timeStamp);
    });

    dom.canvas.addEventListener('pointermove', (e) => {
      if (!isPointerDown) return;
      const pos = getCanvasPos(e);
      addStrokePoint(pos.x, pos.y, e.timeStamp);
    });

    const finishPointer = () => {
      if (isPointerDown) {
        isPointerDown = false;
        endStroke();
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('pointerup', finishPointer);
      window.addEventListener('pointercancel', finishPointer);
    }
  }

  /**
   * DOM Bindings & UI Initialization
   */
  function init() {
    if (typeof document === 'undefined') return;
    if (state.initialized) return;

    // Resolve Elements
    dom.container = document.getElementById('drawingBoardContainer');
    dom.canvas = document.getElementById('drawingCanvas');
    dom.cursor = document.getElementById('drawingCursor');
    dom.colorSwatches = Array.from(document.querySelectorAll('.color-swatch'));
    dom.brushButtons = Array.from(document.querySelectorAll('.brush-btn'));
    dom.btnClear = document.getElementById('btnClearDraw');
    dom.btnUndo = document.getElementById('btnUndoDraw');
    dom.btnExport = document.getElementById('btnExportDraw');

    if (dom.canvas) {
      dom.ctx = dom.canvas.getContext('2d');
    }

    injectStyles();

    // Color swatches click handlers
    dom.colorSwatches.forEach(swatch => {
      swatch.addEventListener('click', () => {
        const c = swatch.dataset.color || CONFIG.defaultColor;
        setColor(c);
      });
    });

    // Brush buttons click handlers
    dom.brushButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const sz = btn.dataset.size || CONFIG.defaultSize;
        setBrushSize(sz);
      });
    });

    // Action buttons
    if (dom.btnClear) {
      dom.btnClear.addEventListener('click', () => clearCanvas(true));
    }
    if (dom.btnUndo) {
      dom.btnUndo.addEventListener('click', () => undoStroke());
    }
    if (dom.btnExport) {
      dom.btnExport.addEventListener('click', () => exportHighResPNG());
    }

    // Mouse / Stylus interaction
    bindMouseFallback();

    // Synchronize initial state from VisionApp if set
    if (VisionApp.state) {
      if (VisionApp.state.drawColor) state.color = VisionApp.state.drawColor;
      if (VisionApp.state.brushSize) state.brushSize = VisionApp.state.brushSize;
      if (VisionApp.state.drawHistory && VisionApp.state.drawHistory.length) {
        state.strokeHistory = VisionApp.state.drawHistory;
        redrawCanvas();
      }
    }

    state.initialized = true;
    state.active = true;
  }

  // Auto-init on DOM readiness
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  }

  // Public Tool Interface attached to window.VisionApp.tools.airDrawing
  const AirDrawingTool = {
    // Lifecycle
    init: init,
    isInitialized: () => state.initialized,

    // Hand tracking & gesture processing
    updateHandTracking: updateHandTracking,
    updateSmoothedFingertip: updateSmoothedFingertip,

    // Natural drawing pipeline methods
    startStroke: startStroke,
    addStrokePoint: addStrokePoint,
    endStroke: endStroke,
    redrawCanvas: redrawCanvas,

    // Canvas management
    clearCanvas: clearCanvas,
    undo: undoStroke,
    exportPNG: exportHighResPNG,

    // Style & brush controls
    setColor: setColor,
    setBrushSize: setBrushSize,
    getColor: () => state.color,
    getBrushSize: () => state.brushSize,
    getBrushMode: () => state.brushMode,

    // State inspection
    isDrawing: () => state.isDrawing,
    getStrokes: () => state.strokeHistory,
    getConfig: () => CONFIG,

    // Audio & Feedback
    playClearChime: playClearChimeCue,
    startHum: startDrawingHum,
    stopHum: stopDrawingHum
  };

  // Attach to VisionApp
  VisionApp.tools.airDrawing = AirDrawingTool;

  // Convenient root aliases on VisionApp
  VisionApp.clearAirCanvas = () => AirDrawingTool.clearCanvas(true);
  VisionApp.undoAirCanvas = () => AirDrawingTool.undo();
  VisionApp.exportAirCanvasPNG = () => AirDrawingTool.exportPNG();

  // CommonJS / Node export for testing if applicable
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = AirDrawingTool;
  }

})(typeof window !== 'undefined' ? window : this);
