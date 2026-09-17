/**
 * tool-playground-lens.js
 * Vision Studio - Vision Playground & Dual-Hand Filter Lens Engine
 *
 * Modular tool extension attaching to `window.VisionApp`.
 *
 * Features:
 * 1. Dual-Hand Filter Lens (tab-playground + dual_lens mode on #playgroundCanvas):
 *    - Exponential Moving Average (EMA) dampening with a 4px deadzone for ZERO jitter
 *    - Dual-hand pinch: Resizes and positions the lens bounding box
 *    - Single-hand pinch near the lens: Drags / repositions the lens without resizing
 *    - Relaxed / released hands: Sticky lock state (locked: true), continuously applying
 *      the optical filter beneath it without resetting or disappearing
 * 2. Isolated Lens Filter:
 *    - Driven by `window.VisionApp.state.lensFilter` (default: 'matrix')
 *    - Rendered strictly inside the lens bounding box on #playgroundCanvas
 *    - NEVER affects visionCanvas (camera HUD) or any other tool
 *    - High-tech cyber frame with interactive filter cycle chip/button on badge
 *    - ✌️ Peace sign gesture shortcut to cycle state.lensFilter
 * 3. Playground Overlays Support:
 *    - drawn_portal, theremin, air_drums, physics, gesture_wheel
 *    - All overlays strictly rendered on #playgroundCanvas with zero leakage
 */

(function (root) {
  'use strict';

  // Constants & Tuning Parameters
  const DEADZONE_PX = 4.0;          // 4px deadzone for 100% stable, zero-jitter position/size
  const EMA_ALPHA = 0.24;            // Exponential moving average smoothing factor
  const MIN_LENS_WIDTH = 60;        // Minimum allowable lens width
  const MIN_LENS_HEIGHT = 60;       // Minimum allowable lens height
  const PINCH_THRESHOLD_NORM = 0.082;// Normalized distance between thumb & index tips
  const NEAR_MARGIN_PX = 45;        // Margin around lens to detect single-hand grab
  const PEACE_GESTURE_COOLDOWN = 700;// Milliseconds between peace sign filter cycles

  // Internal Lens State
  const lensState = {
    x: 0,
    y: 0,
    w: 280,
    h: 180,
    active: false,
    locked: true,
    mode: 'locked',                  // 'locked' | 'resizing' | 'dragging'
    isInitialized: false,
    dragAnchor: null,                // { offsetX, offsetY, handIndex }
    lastPeaceTriggerTime: 0,
    cycleChipBounds: { x: 0, y: 0, w: 0, h: 0 },
    isMouseOverChip: false,
    mouseDrag: null                  // { isDown, isDraggingLens, isResizing, startX, startY, origX, origY, origW, origH }
  };

  /**
   * Exponential Moving Average (EMA) with Deadzone Dampening
   * If the delta is within the deadzone threshold (4px), the value remains 100% frozen.
   * If the delta exceeds the deadzone, dampens movement smoothly.
   */
  function applyEmaDeadzone(curr, target, alpha = EMA_ALPHA, deadzone = DEADZONE_PX) {
    const delta = target - curr;
    if (Math.abs(delta) <= deadzone) {
      return curr; // Exactly zero jitter
    }
    const effectiveDelta = delta > 0 ? delta - deadzone : delta + deadzone;
    return curr + effectiveDelta * alpha;
  }

  /**
   * Checks if a point in canvas pixels is near the lens bounding box
   */
  function isPointNearLens(px, py, lens, margin = NEAR_MARGIN_PX) {
    if (!lens || !lens.active) return false;
    return (
      px >= lens.x - margin &&
      px <= lens.x + lens.w + margin &&
      py >= lens.y - margin - 32 && // include badge area above
      py <= lens.y + lens.h + margin
    );
  }

  /**
   * Helper to compute pinch status for a given hand's landmarks
   */
  function getHandPinchInfo(handPoints, canvasW, canvasH) {
    if (!handPoints || handPoints.length < 9) return { isPinch: false, px: 0, py: 0 };
    const thumbTip = handPoints[4];
    const indexTip = handPoints[8];
    const distNorm = Math.hypot(thumbTip.x - indexTip.x, thumbTip.y - indexTip.y);
    const isPinch = distNorm < PINCH_THRESHOLD_NORM;
    const px = ((thumbTip.x + indexTip.x) * 0.5) * canvasW;
    const py = ((thumbTip.y + indexTip.y) * 0.5) * canvasH;
    return { isPinch, px, py, distNorm };
  }

  /**
   * Ensures default lens is created and placed in the center of the playground canvas
   */
  function ensureDefaultLens(canvasW, canvasH, force = false) {
    if (!lensState.isInitialized || force) {
      const defaultW = Math.min(320, canvasW * 0.45);
      const defaultH = Math.min(220, canvasH * 0.45);
      lensState.w = defaultW;
      lensState.h = defaultH;
      lensState.x = Math.round((canvasW - defaultW) * 0.5);
      lensState.y = Math.round((canvasH - defaultH) * 0.5);
      lensState.active = true;
      lensState.locked = true;
      lensState.mode = 'locked';
      lensState.isInitialized = true;
    }
    syncToVisionAppState();
  }

  /**
   * Synchronizes the internal lensState into VisionApp.state.dualHandRoi
   */
  function syncToVisionAppState() {
    if (typeof window === 'undefined' || !window.VisionApp || !window.VisionApp.state) return;
    const state = window.VisionApp.state;

    // Ensure state.lensFilter default
    if (!state.lensFilter) {
      state.lensFilter = 'matrix';
    }

    if (!state.dualHandRoi) {
      state.dualHandRoi = {};
    }

    state.dualHandRoi.x = lensState.x;
    state.dualHandRoi.y = lensState.y;
    state.dualHandRoi.w = lensState.w;
    state.dualHandRoi.h = lensState.h;
    state.dualHandRoi.active = lensState.active;
    state.dualHandRoi.locked = lensState.locked;
    state.dualHandRoi.mode = lensState.mode;
  }

  /**
   * Cycle the lens filter
   */
  function cycleLensFilter(direction = 1) {
    if (typeof window === 'undefined' || !window.VisionApp) return;
    const { state, FILTER_LIST, showToast, showGestureHudBanner, playSlideChime } = window.VisionApp;
    const filters = (FILTER_LIST && FILTER_LIST.length) ? FILTER_LIST : [
      'normal', 'matrix', 'thermal', 'sobel', 'cyber_vhs', 'hologram',
      'solar_gold', 'vortex_blackhole', 'lightning_plasma', 'hyper_kaleidoscope',
      'cyber_glitch_mosh', 'fire_inferno', 'chrono_echo'
    ];

    const currentFilter = state.lensFilter || 'matrix';
    const curIdx = filters.indexOf(currentFilter);
    let nextIdx = (curIdx + direction) % filters.length;
    if (nextIdx < 0) nextIdx = filters.length - 1;
    const nextFilter = filters[nextIdx];

    state.lensFilter = nextFilter;

    if (typeof playSlideChime === 'function') playSlideChime();
    if (typeof showGestureHudBanner === 'function') {
      showGestureHudBanner("🔍 LENS SHADER", `Filter → ${nextFilter.toUpperCase()}`, "🔍");
    }
    if (typeof showToast === 'function') {
      showToast(`🔍 Lens Filter: ${nextFilter.toUpperCase()}`);
    }
    return nextFilter;
  }

  /**
   * Set specific lens filter
   */
  function setLensFilter(filterName) {
    if (typeof window === 'undefined' || !window.VisionApp) return;
    const { state, showToast } = window.VisionApp;
    state.lensFilter = filterName || 'matrix';
    if (typeof showToast === 'function') {
      showToast(`🔍 Lens Filter: ${state.lensFilter.toUpperCase()}`);
    }
  }

  /**
   * Reset lens to default centered state
   */
  function resetLens() {
    const canvas = (typeof window !== 'undefined' && window.VisionApp && window.VisionApp.els && window.VisionApp.els.playgroundCanvas)
      ? window.VisionApp.els.playgroundCanvas
      : { width: 800, height: 520 };
    ensureDefaultLens(canvas.width, canvas.height, true);
  }

  /**
   * Process hands for Dual-Hand Filter Lens
   * Supports:
   * - Dual-hand pinch: Resizes and moves lens
   * - Single-hand pinch near lens: Drags lens without resizing
   * - Relaxed hands: Sticky locked state
   * - Peace sign: Cycles state.lensFilter
   */
  function processHands(h0, h1) {
    if (typeof window === 'undefined' || !window.VisionApp) return;
    const { state, els } = window.VisionApp;

    // Only process if active tab is playground and mode is dual_lens
    if (state.activeTab !== 'tab-playground' || state.activePgMode !== 'dual_lens') {
      return;
    }

    const canvasW = els.playgroundCanvas ? els.playgroundCanvas.width : 800;
    const canvasH = els.playgroundCanvas ? els.playgroundCanvas.height : 520;

    ensureDefaultLens(canvasW, canvasH);

    const pinch0 = getHandPinchInfo(h0, canvasW, canvasH);
    const pinch1 = getHandPinchInfo(h1, canvasW, canvasH);

    const now = performance.now();

    // Check for ✌️ Peace Sign Gesture to Cycle Lens Filter
    const g0 = (state.handGestures && state.handGestures[0]) || '';
    const g1 = (state.handGestures && state.handGestures[1]) || '';
    const isPeaceGesture = (g0 === 'VICTORY_PEACE' || g1 === 'VICTORY_PEACE');

    if (isPeaceGesture && now - lensState.lastPeaceTriggerTime > PEACE_GESTURE_COOLDOWN) {
      lensState.lastPeaceTriggerTime = now;
      cycleLensFilter(1);
    }

    // ── CASE 1: Dual-Hand Pinch (Resize & Position Lens) ──
    if (pinch0.isPinch && pinch1.isPinch) {
      lensState.dragAnchor = null; // Clear single-hand drag anchor

      const rawMinX = Math.min(pinch0.px, pinch1.px);
      const rawMaxX = Math.max(pinch0.px, pinch1.px);
      const rawMinY = Math.min(pinch0.py, pinch1.py);
      const rawMaxY = Math.max(pinch0.py, pinch1.py);

      const targetX = Math.max(0, rawMinX);
      const targetY = Math.max(0, rawMinY);
      const targetW = Math.max(MIN_LENS_WIDTH, rawMaxX - rawMinX);
      const targetH = Math.max(MIN_LENS_HEIGHT, rawMaxY - rawMinY);

      // Apply EMA dampening with 4px deadzone for rock-solid stability
      lensState.x = applyEmaDeadzone(lensState.x, targetX);
      lensState.y = applyEmaDeadzone(lensState.y, targetY);
      lensState.w = applyEmaDeadzone(lensState.w, targetW);
      lensState.h = applyEmaDeadzone(lensState.h, targetH);

      lensState.active = true;
      lensState.locked = false;
      lensState.mode = 'resizing';
    }
    // ── CASE 2: Single-Hand Pinch Near Lens (Drag / Reposition Lens Without Resizing) ──
    else if ((pinch0.isPinch && !pinch1.isPinch) || (!pinch0.isPinch && pinch1.isPinch)) {
      const activePinch = pinch0.isPinch ? pinch0 : pinch1;
      const handIndex = pinch0.isPinch ? 0 : 1;

      // Start drag if near lens or continue existing drag from same hand
      if (lensState.dragAnchor && lensState.dragAnchor.handIndex === handIndex) {
        // Dragging in progress
        const targetX = activePinch.px - lensState.dragAnchor.offsetX;
        const targetY = activePinch.py - lensState.dragAnchor.offsetY;

        // Apply EMA dampening with 4px deadzone to position only (width & height unchanged!)
        lensState.x = applyEmaDeadzone(lensState.x, targetX);
        lensState.y = applyEmaDeadzone(lensState.y, targetY);

        lensState.active = true;
        lensState.locked = false;
        lensState.mode = 'dragging';
      } else if (isPointNearLens(activePinch.px, activePinch.py, lensState)) {
        // Initiate drag anchor
        lensState.dragAnchor = {
          offsetX: activePinch.px - lensState.x,
          offsetY: activePinch.py - lensState.y,
          handIndex: handIndex
        };
        lensState.locked = false;
        lensState.mode = 'dragging';
      } else {
        // Pinch is far away from lens; keep lens sticky locked
        lensState.dragAnchor = null;
        lensState.locked = true;
        lensState.mode = 'locked';
      }
    }
    // ── CASE 3: Hands Relaxed / Not Pinching (Rock-Solid Sticky Lock State) ──
    else {
      lensState.dragAnchor = null;
      lensState.locked = true;
      lensState.mode = 'locked';
      // The lens remains active and locked in place with ZERO jitter!
      lensState.active = true;
    }

    // Keep lens inside visible bounds
    lensState.x = Math.max(0, Math.min(canvasW - 40, lensState.x));
    lensState.y = Math.max(0, Math.min(canvasH - 40, lensState.y));

    syncToVisionAppState();
  }

  /**
   * Render the Dual-Hand Pinch ROI Lens Frame & Interactive Badge
   * Renders strictly on the given canvas context.
   */
  function renderRoiLensFrame(ctx, x, y, w, h, filterName) {
    if (!ctx) return;
    const now = performance.now();

    ctx.save();

    // Themed Accent Color based on filter
    const filterColorMap = {
      normal: '#9aa0a6',
      matrix: '#34a853',
      thermal: '#ea4335',
      sobel: '#00f0ff',
      cyber_vhs: '#e879f9',
      hologram: '#38bdf8',
      solar_gold: '#fbbc04',
      vortex_blackhole: '#c084fc',
      lightning_plasma: '#60a5fa',
      hyper_kaleidoscope: '#a855f7',
      cyber_glitch_mosh: '#22c55e',
      fire_inferno: '#ff5722',
      chrono_echo: '#06b6d4'
    };
    const accentColor = filterColorMap[filterName] || '#00f0ff';

    // 1. Lens Bounding Border (Dashed high-tech reticle)
    ctx.strokeStyle = accentColor;
    ctx.lineWidth = lensState.locked ? 2 : 2.5;
    ctx.setLineDash([8, 4]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);

    // 2. Corner Bracket Reticles (Solid bright brackets)
    const bLen = Math.min(22, Math.max(12, Math.min(w, h) * 0.18));
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.shadowColor = accentColor;
    ctx.shadowBlur = lensState.locked ? 6 : 14;

    // Top-Left
    ctx.beginPath();
    ctx.moveTo(x, y + bLen);
    ctx.lineTo(x, y);
    ctx.lineTo(x + bLen, y);
    ctx.stroke();

    // Top-Right
    ctx.beginPath();
    ctx.moveTo(x + w - bLen, y);
    ctx.lineTo(x + w, y);
    ctx.lineTo(x + w, y + bLen);
    ctx.stroke();

    // Bottom-Left
    ctx.beginPath();
    ctx.moveTo(x, y + h - bLen);
    ctx.lineTo(x, y + h);
    ctx.lineTo(x + bLen, y + h);
    ctx.stroke();

    // Bottom-Right
    ctx.beginPath();
    ctx.moveTo(x + w - bLen, y + h);
    ctx.lineTo(x + w, y + h);
    ctx.lineTo(x + w, y + h - bLen);
    ctx.stroke();

    // 3. Subtle Optical Center Crosshair
    const cx = x + w * 0.5;
    const cy = y + h * 0.5;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
    ctx.lineWidth = 1;
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.moveTo(cx - 8, cy); ctx.lineTo(cx + 8, cy);
    ctx.moveTo(cx, cy - 8); ctx.lineTo(cx, cy + 8);
    ctx.stroke();

    // 4. Interactive Lens Header Badge Bar
    const badgeW = Math.max(220, Math.min(w, 310));
    const badgeH = 26;
    let badgeY = y - badgeH - 6;
    if (badgeY < 6) badgeY = y + 6; // flip inside if too close to top

    // Badge pill background
    ctx.fillStyle = 'rgba(11, 15, 25, 0.92)';
    ctx.strokeStyle = accentColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(x, badgeY, badgeW, badgeH, 6) : ctx.rect(x, badgeY, badgeW, badgeH);
    ctx.fill();
    ctx.stroke();

    // Lens Icon & Status Indicator
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    const statusIcon = lensState.locked ? '🔒' : (lensState.mode === 'dragging' ? '🤏' : '↔️');
    ctx.fillText(`${statusIcon} LENS`, x + 8, badgeY + badgeH * 0.5);

    // Interactive Filter Cycle Chip Button
    const chipX = x + 72;
    const chipY = badgeY + 3;
    const chipW = 120;
    const chipH = 20;

    // Cache chip bounds for mouse click detection
    lensState.cycleChipBounds = { x: chipX, y: chipY, w: chipW, h: chipH };

    const isHover = lensState.isMouseOverChip;
    ctx.fillStyle = isHover ? 'rgba(0, 240, 255, 0.32)' : 'rgba(0, 240, 255, 0.14)';
    ctx.strokeStyle = isHover ? '#ffffff' : accentColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect ? ctx.roundRect(chipX, chipY, chipW, chipH, 4) : ctx.rect(chipX, chipY, chipW, chipH);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = isHover ? '#ffffff' : accentColor;
    ctx.font = 'bold 10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`⚡ ${filterName.toUpperCase()} ⟳`, chipX + chipW * 0.5, chipY + chipH * 0.5);

    // Dimensions / Mode Readout on Right
    ctx.textAlign = 'right';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.font = '9px monospace';
    const dimText = `${Math.round(w)}×${Math.round(h)}`;
    ctx.fillText(dimText, x + badgeW - 6, badgeY + badgeH * 0.5);

    ctx.restore();
  }

  /**
   * Render the Dual-Hand Filter Lens (and isolated shader filter) strictly on #playgroundCanvas
   */
  function renderLens(ctx, w, h, now) {
    if (!ctx) return;
    if (!lensState.active) {
      ensureDefaultLens(w, h);
    }

    const state = (typeof window !== 'undefined' && window.VisionApp) ? window.VisionApp.state : null;
    const lensFilter = (state && state.lensFilter) ? state.lensFilter : 'matrix';
    const renderShaderFilter = (typeof window !== 'undefined' && window.VisionApp)
      ? window.VisionApp.renderShaderFilter
      : null;

    const { x, y, w: rw, h: rh } = lensState;

    // Strict Isolated Filter Application: Clip strictly to lens boundaries
    if (typeof renderShaderFilter === 'function' && lensFilter !== 'normal') {
      ctx.save();
      ctx.beginPath();
      ctx.rect(x, y, rw, rh);
      ctx.clip();
      renderShaderFilter(ctx, lensFilter, x, y, rw, rh, now);
      ctx.restore();
    }

    // Render cyber lens frame and interactive badge
    renderRoiLensFrame(ctx, x, y, rw, rh, lensFilter);
  }

  /**
   * Complete Playground Scene Render Orchestrator
   * Renders video feed / background, drawn portals, dual lens, and all overlays strictly on #playgroundCanvas.
   * Ensures ZERO leakage to visionCanvas or any other tool.
   */
  function renderScene(ctx, w, h, now) {
    if (!ctx || typeof window === 'undefined' || !window.VisionApp) return;
    const { state, els, renderShaderFilter } = window.VisionApp;

    // 1. Clear Playground Canvas
    ctx.clearRect(0, 0, w, h);

    // 2. Base Video Stream or Futuristic Cyber Grid
    if (state.isWebcamActive && els.webcamVideo && els.webcamVideo.readyState >= 2) {
      ctx.save();
      ctx.scale(-1, 1);
      ctx.drawImage(els.webcamVideo, -w, 0, w, h);
      ctx.restore();
    } else {
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, '#131822');
      grad.addColorStop(1, '#0b0f14');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      for (let gx = 0; gx < w; gx += 40) {
        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke();
      }
      for (let gy = 0; gy < h; gy += 40) {
        ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
      }
    }

    // 3. Mode-Specific Passes (strictly isolated so each mode only renders its own content)
    if (state.activePgMode === 'drawn_portal') {
      // 3a. Render Drawn Filter Portals
      if (state.drawnPortals && state.drawnPortals.length > 0) {
        state.drawnPortals.forEach(portal => {
          if (!portal.points || portal.points.length < 3) return;
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(portal.points[0].x, portal.points[0].y);
          for (let i = 1; i < portal.points.length; i++) {
            ctx.lineTo(portal.points[i].x, portal.points[i].y);
          }
          ctx.closePath();
          ctx.clip();
          if (typeof renderShaderFilter === 'function') {
            renderShaderFilter(ctx, portal.filter || state.activeFilter, 0, 0, w, h, now);
          }
          ctx.restore();

          ctx.save();
          ctx.strokeStyle = portal.color || '#00f0ff';
          ctx.lineWidth = 2.5;
          ctx.shadowColor = portal.color || '#00f0ff';
          ctx.shadowBlur = 10;
          ctx.beginPath();
          ctx.moveTo(portal.points[0].x, portal.points[0].y);
          for (let i = 1; i < portal.points.length; i++) {
            ctx.lineTo(portal.points[i].x, portal.points[i].y);
          }
          ctx.closePath();
          ctx.stroke();
          ctx.restore();
        });
      }

      // Render active drawing stroke
      if (state.currentStrokePoints && state.currentStrokePoints.length > 1) {
        ctx.save();
        ctx.strokeStyle = '#34a853';
        ctx.lineWidth = 3;
        ctx.setLineDash([6, 3]);
        ctx.beginPath();
        ctx.moveTo(state.currentStrokePoints[0].x, state.currentStrokePoints[0].y);
        for (let i = 1; i < state.currentStrokePoints.length; i++) {
          ctx.lineTo(state.currentStrokePoints[i].x, state.currentStrokePoints[i].y);
        }
        ctx.stroke();
        ctx.restore();
      }
    } else if (state.activePgMode === 'dual_lens') {
      // 3b. Render Dual-Hand Filter Lens (strictly only in dual_lens mode!)
      renderLens(ctx, w, h, now);
      if (lensState.active && Math.random() < 0.4 && typeof window.spawnFingertipSpark === 'function') {
        window.spawnFingertipSpark(lensState.x + Math.random() * lensState.w, lensState.y, '#00f0ff');
        window.spawnFingertipSpark(lensState.x + Math.random() * lensState.w, lensState.y + lensState.h, '#fbbc04');
      }
    } else if (state.activePgMode === 'theremin') {
      // 3c. Render Spatial Audio Beat & Loop Studio
      if (window.VisionApp && window.VisionApp.tools && window.VisionApp.tools.spatialAudio && typeof window.VisionApp.tools.spatialAudio.renderStage === 'function') {
        window.VisionApp.tools.spatialAudio.renderStage(ctx, w, h, now);
      } else if (typeof window.renderThereminVisualizer === 'function') {
        window.renderThereminVisualizer(ctx, w, h, now);
      }
    } else if (state.activePgMode === 'physics') {
      // 3d. Render 3D Physics objects
      if (typeof window.updatePhysicsSandbox === 'function') window.updatePhysicsSandbox(0.016, w, h);
      if (typeof window.renderPhysicsObjects === 'function') window.renderPhysicsObjects(ctx, w, h);
    } else if (state.activePgMode === 'air_drums') {
      // 3e. Render Air Drums
      if (typeof window.updateAndRenderAirDrums === 'function') window.updateAndRenderAirDrums(ctx, w, h, now);
    } else if (state.activePgMode === 'gesture_wheel') {
      // 3f. Render Gesture Wheel
      if (typeof window.renderGestureWheelOverlay === 'function') window.renderGestureWheelOverlay(ctx, w, h, now);
    }
    if (typeof window.updateAndRenderParticles === 'function') {
      window.updateAndRenderParticles(ctx, w, h, now);
    }

    // 7. Multi-Hand Skeletons on Playground Canvas (if enabled)
    if (state.showSkeleton && typeof window.renderMultiHandSkeletons === 'function') {
      window.renderMultiHandSkeletons(ctx, w, h);
    }
  }

  /**
   * Set up interactive mouse and pointer listeners on #playgroundCanvas
   * Handles chip clicks, dragging, and resizing directly with pointer.
   */
  function setupPointerInteractions() {
    if (typeof window === 'undefined' || !window.VisionApp || !window.VisionApp.els) return;
    const canvas = window.VisionApp.els.playgroundCanvas;
    if (!canvas || canvas.__hasLensListeners) return;
    canvas.__hasLensListeners = true;

    canvas.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (canvas.width / rect.width);
      const py = (e.clientY - rect.top) * (canvas.height / rect.height);

      // Check hover over interactive cycle chip
      const chip = lensState.cycleChipBounds;
      const isOverChip = (px >= chip.x && px <= chip.x + chip.w && py >= chip.y && py <= chip.y + chip.h);
      if (lensState.isMouseOverChip !== isOverChip) {
        lensState.isMouseOverChip = isOverChip;
        canvas.style.cursor = isOverChip ? 'pointer' : (isPointNearLens(px, py, lensState) ? 'grab' : 'default');
      }

      // Handle Mouse Dragging
      if (lensState.mouseDrag && lensState.mouseDrag.isDown) {
        const md = lensState.mouseDrag;
        if (md.isDraggingLens) {
          lensState.x = Math.max(0, Math.min(canvas.width - lensState.w, px - md.offsetX));
          lensState.y = Math.max(0, Math.min(canvas.height - lensState.h, py - md.offsetY));
          lensState.locked = false;
          lensState.mode = 'dragging';
          syncToVisionAppState();
        } else if (md.isResizing) {
          const minX = Math.min(md.startX, px);
          const minY = Math.min(md.startY, py);
          const maxX = Math.max(md.startX, px);
          const maxY = Math.max(md.startY, py);
          lensState.x = minX;
          lensState.y = minY;
          lensState.w = Math.max(MIN_LENS_WIDTH, maxX - minX);
          lensState.h = Math.max(MIN_LENS_HEIGHT, maxY - minY);
          lensState.locked = false;
          lensState.mode = 'resizing';
          syncToVisionAppState();
        }
      }
    });

    canvas.addEventListener('mousedown', (e) => {
      const rect = canvas.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (canvas.width / rect.width);
      const py = (e.clientY - rect.top) * (canvas.height / rect.height);

      // If clicked the Filter Cycle Chip button
      const chip = lensState.cycleChipBounds;
      if (px >= chip.x && px <= chip.x + chip.w && py >= chip.y && py <= chip.y + chip.h) {
        cycleLensFilter(1);
        e.preventDefault();
        e.stopPropagation();
        return;
      }

      const state = window.VisionApp.state;
      if (state.activePgMode === 'dual_lens') {
        const isInsideLens = (px >= lensState.x && px <= lensState.x + lensState.w &&
                              py >= lensState.y && py <= lensState.y + lensState.h);
        lensState.mouseDrag = {
          isDown: true,
          startX: px,
          startY: py,
          isDraggingLens: isInsideLens,
          isResizing: !isInsideLens,
          offsetX: px - lensState.x,
          offsetY: py - lensState.y
        };
      }
    });

    window.addEventListener('mouseup', () => {
      if (lensState.mouseDrag && lensState.mouseDrag.isDown) {
        lensState.mouseDrag.isDown = false;
        lensState.locked = true;
        lensState.mode = 'locked';
        syncToVisionAppState();
      }
    });
  }

  /**
   * Initializes the tool module
   */
  function init() {
    if (typeof window === 'undefined') return;

    if (window.VisionApp) {
      if (!window.VisionApp.tools) window.VisionApp.tools = {};
      window.VisionApp.tools.playgroundLens = toolApi;

      // Ensure state default
      if (window.VisionApp.state && !window.VisionApp.state.lensFilter) {
        window.VisionApp.state.lensFilter = 'matrix';
      }

      // Override / augment renderRoiLensFrame on VisionApp
      window.VisionApp.renderRoiLensFrame = renderRoiLensFrame;

      setupPointerInteractions();
    }
  }

  // Public Tool API Object
  const toolApi = {
    name: 'playgroundLens',
    version: '1.0.0',
    init,
    processHands,
    renderLens,
    renderRoiLensFrame,
    renderScene,
    cycleLensFilter,
    setLensFilter,
    getLensFilter: () => (typeof window !== 'undefined' && window.VisionApp && window.VisionApp.state ? window.VisionApp.state.lensFilter : 'matrix'),
    resetLens,
    getLensState: () => ({ ...lensState }),
    applyEmaDeadzone,
    isPointNearLens
  };

  // Attach immediately to root or register when DOM is ready
  if (typeof window !== 'undefined') {
    if (window.VisionApp) {
      init();
    } else {
      window.addEventListener('DOMContentLoaded', init);
    }
  }

  // CommonJS / Node export for testing and verification
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = toolApi;
  }

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
