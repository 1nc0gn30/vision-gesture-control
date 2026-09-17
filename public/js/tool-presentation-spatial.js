/**
 * Vision Studio - Touchless Presentation & 3D Holographic Spatial Portal
 * Module: public/js/tool-presentation-spatial.js
 *
 * Objectives:
 * 1. Touchless Presentation Controller:
 *    - High-precision laser pointer reticle inside #presViewport with fluid motion trail.
 *    - Precise Dwell Click: Bounding box mapping to #presViewport buttons (prev, next, slide dots, fullscreen)
 *      with glowing circular dwell progress ring (0% -> 100% fill with audio/visual click confirmation).
 *    - Velocity-thresholded horizontal swipe right (next slide) & swipe left (prev slide) with audio chimes.
 *    - Fist gesture reset to Slide 1.
 * 2. 3D Holographic Spatial Portal:
 *    - WebGL Three.js spatial core: handles viewport resize and zero-dimension load safely.
 *    - Two-hand span zoom with smooth lerp dampening.
 *    - Dual-hand pitch and yaw rotation, and pinch roll.
 *    - Shape geometry cycler (Icosahedron, TorusKnot, Dodecahedron, Octahedron, Sphere).
 *    - Neon color palette switcher (Quantum Cyan, Solar Amber, Matrix Emerald, Hyper Ruby, Cosmic Violet, Electric Plasma).
 * 3. Decoupled from all other tools and filter lenses.
 */

(function (root, factory) {
  'use strict';
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ─────────────────────────────────────────────────────────────
  // 1. INJECT DEDICATED STYLES FOR RETICLE, DWELL RING & HUD
  // ─────────────────────────────────────────────────────────────
  function injectStyles() {
    if (typeof document === 'undefined') return;
    if (document.getElementById('tool-pres-spatial-styles')) return;

    const styleEl = document.createElement('style');
    styleEl.id = 'tool-pres-spatial-styles';
    styleEl.textContent = `
      /* Presentation Viewport Motion Trail Canvas */
      #presMotionTrailCanvas {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 45;
      }

      /* Enhanced Laser Pointer Reticle */
      #laserPointer {
        position: absolute;
        width: 36px;
        height: 36px;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 55;
        display: none;
        transition: transform 0.05s ease-out;
      }

      .laser-reticle-container {
        position: relative;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .laser-center-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #ff1744;
        box-shadow: 0 0 10px #ff1744, 0 0 20px #ff5252;
        border: 1.5px solid #ffffff;
        transition: transform 0.15s ease, background-color 0.2s ease;
      }

      .laser-targeting-crosshair {
        position: absolute;
        inset: 4px;
        border: 1.5px dashed rgba(255, 23, 68, 0.7);
        border-radius: 50%;
        animation: spinLaserReticle 8s linear infinite;
        transition: border-color 0.2s ease;
      }

      @keyframes spinLaserReticle {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      /* Glowing Circular Dwell Progress Ring */
      .laser-dwell-svg {
        position: absolute;
        top: -4px;
        left: -4px;
        width: 44px;
        height: 44px;
        transform: rotate(-90deg);
        pointer-events: none;
        filter: drop-shadow(0 0 6px rgba(26, 115, 232, 0.8));
      }

      .laser-dwell-track {
        fill: none;
        stroke: rgba(255, 255, 255, 0.15);
        stroke-width: 3;
      }

      .laser-dwell-indicator {
        fill: none;
        stroke: #1a73e8;
        stroke-width: 3.5;
        stroke-linecap: round;
        stroke-dasharray: 113.1;
        stroke-dashoffset: 113.1;
        transition: stroke-dashoffset 0.04s linear, stroke 0.2s ease;
      }

      .laser-dwell-active .laser-center-dot {
        background: #1e8e3e;
        box-shadow: 0 0 12px #1e8e3e, 0 0 24px #34a853;
        transform: scale(1.15);
      }

      .laser-dwell-active .laser-targeting-crosshair {
        border-color: rgba(30, 142, 62, 0.9);
      }

      .laser-dwell-active .laser-dwell-indicator {
        stroke: #1e8e3e;
        filter: drop-shadow(0 0 8px #1e8e3e);
      }

      .laser-dwell-badge {
        position: absolute;
        top: 38px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 0.68rem;
        font-weight: 700;
        color: #ffffff;
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(4px);
        padding: 2px 8px;
        border-radius: 999px;
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.15s ease, transform 0.15s ease;
        border: 1px solid rgba(255, 255, 255, 0.18);
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      }

      .laser-dwell-active .laser-dwell-badge {
        opacity: 1;
        transform: translateX(-50%) translateY(2px);
      }

      /* In-Viewport Touchless Floating HUD */
      .pres-viewport-hud {
        position: absolute;
        bottom: 16px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 14px;
        background: rgba(26, 32, 44, 0.78);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 999px;
        z-index: 52;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        transition: opacity 0.25s ease;
      }

      .pres-hud-btn {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: #ffffff;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 999px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.15s ease;
        user-select: none;
      }

      .pres-hud-btn:hover,
      .pres-hud-btn.dwell-target-active {
        background: rgba(26, 115, 232, 0.35);
        border-color: #1a73e8;
        transform: scale(1.06);
        box-shadow: 0 0 12px rgba(26, 115, 232, 0.6);
      }

      .pres-hud-dots {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .pres-hud-dot {
        width: 11px;
        height: 11px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.28);
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid transparent;
      }

      .pres-hud-dot.active {
        background: #1a73e8;
        box-shadow: 0 0 10px #1a73e8;
        transform: scale(1.25);
        border-color: #ffffff;
      }

      .pres-hud-dot.dwell-target-active {
        background: #1e8e3e;
        box-shadow: 0 0 12px #1e8e3e;
        transform: scale(1.3);
      }

      /* Edge Nav Hotspots */
      .pres-nav-edge {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        width: 42px;
        height: 72px;
        background: rgba(26, 32, 44, 0.35);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        font-size: 1.3rem;
        cursor: pointer;
        z-index: 52;
        transition: all 0.2s ease;
        user-select: none;
      }

      .pres-nav-edge.prev { left: 10px; }
      .pres-nav-edge.next { right: 10px; }

      .pres-nav-edge:hover,
      .pres-nav-edge.dwell-target-active {
        background: rgba(26, 115, 232, 0.45);
        border-color: #1a73e8;
        box-shadow: 0 0 16px rgba(26, 115, 232, 0.6);
        transform: translateY(-50%) scale(1.08);
      }

      /* Dwell target button visual pulse */
      .btn.dwell-target-active,
      .slide-dot.dwell-target-active {
        outline: 2px solid #1e8e3e !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 14px rgba(30, 142, 62, 0.7) !important;
      }

      /* 3D Spatial Viewport Enhancements */
      #spatial3dHost {
        position: relative;
        overflow: hidden;
        min-height: 440px;
        background: radial-gradient(circle at center, rgba(15, 23, 42, 0.6) 0%, rgba(10, 14, 23, 0.95) 100%);
      }

      #spatial3dHost canvas {
        display: block;
        width: 100% !important;
        height: 100% !important;
      }
    `;
    document.head.appendChild(styleEl);
  }

  // ─────────────────────────────────────────────────────────────
  // 2. PRESENTATION CONTROLLER ENGINE
  // ─────────────────────────────────────────────────────────────
  class TouchlessPresentationController {
    constructor(visionApp) {
      this.app = visionApp || (typeof window !== 'undefined' ? window.VisionApp : null);
      this.presViewport = null;
      this.laserPointerEl = null;
      this.trailCanvas = null;
      this.trailCtx = null;
      this.trailPoints = [];
      this.maxTrailPoints = 20;
      this.trailDuration = 380; // ms

      // Laser & Dwell State
      this.laserPos = { x: 0.5, y: 0.5 };
      this.targetPos = { x: 0.5, y: 0.5 };
      this.isPointing = false;
      this.dwellTargetEl = null;
      this.dwellStartTime = 0;
      this.isDwelling = false;
      this.dwellDuration = 600; // ms
      this.dwellCooldownUntil = 0;

      // Swipe Detection State
      this.wristHistory = [];
      this.lastSwipeTime = 0;
      this.swipeCooldownMs = 550;
      this.swipeVelocityThreshold = 0.42;

      // Fist Reset State
      this.lastFistTime = 0;
      this.fistCooldownMs = 800;

      // Slide State
      this.activeSlide = 1;
      this.totalSlides = 4;

      // Bound elements
      this.interactiveElements = [];
    }

    init() {
      if (typeof document === 'undefined') return;
      injectStyles();

      this.presViewport = document.getElementById('presViewport');
      if (!this.presViewport) return;

      this.setupTrailCanvas();
      this.setupLaserReticle();
      this.setupFloatingHud();
      this.bindPresentationButtons();
      this.bindMouseFallback();
      this.syncActiveSlide(1);

      // Handle resize
      window.addEventListener('resize', () => this.resizeTrailCanvas());
    }

    setupTrailCanvas() {
      let canvas = document.getElementById('presMotionTrailCanvas');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'presMotionTrailCanvas';
        this.presViewport.appendChild(canvas);
      }
      this.trailCanvas = canvas;
      this.trailCtx = canvas.getContext('2d');
      this.resizeTrailCanvas();
    }

    resizeTrailCanvas() {
      if (!this.trailCanvas || !this.presViewport) return;
      const rect = this.presViewport.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.max(rect.width, 320);
      const h = Math.max(rect.height, 240);

      if (this.trailCanvas.width !== Math.floor(w * dpr) || this.trailCanvas.height !== Math.floor(h * dpr)) {
        this.trailCanvas.width = Math.floor(w * dpr);
        this.trailCanvas.height = Math.floor(h * dpr);
        this.trailCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      }
    }

    setupLaserReticle() {
      let laser = document.getElementById('laserPointer');
      if (!laser) {
        laser = document.createElement('div');
        laser.id = 'laserPointer';
        this.presViewport.appendChild(laser);
      }

      laser.innerHTML = `
        <div class="laser-reticle-container">
          <svg class="laser-dwell-svg" viewBox="0 0 44 44">
            <circle class="laser-dwell-track" cx="22" cy="22" r="18" />
            <circle class="laser-dwell-indicator" id="presDwellCircle" cx="22" cy="22" r="18" />
          </svg>
          <div class="laser-targeting-crosshair"></div>
          <div class="laser-center-dot"></div>
          <div class="laser-dwell-badge" id="presDwellBadge">0%</div>
        </div>
      `;

      this.laserPointerEl = laser;
      this.dwellCircleEl = document.getElementById('presDwellCircle');
      this.dwellBadgeEl = document.getElementById('presDwellBadge');
    }

    setupFloatingHud() {
      if (!this.presViewport) return;
      if (document.getElementById('presViewportHud')) return;

      const hud = document.createElement('div');
      hud.className = 'pres-viewport-hud';
      hud.id = 'presViewportHud';
      hud.innerHTML = `
        <button class="pres-hud-btn" id="presHudPrev" title="Previous Slide (Swipe Left)">◀ Prev</button>
        <div class="pres-hud-dots" id="presHudDots">
          <div class="pres-hud-dot active" data-target="1" title="Slide 1"></div>
          <div class="pres-hud-dot" data-target="2" title="Slide 2"></div>
          <div class="pres-hud-dot" data-target="3" title="Slide 3"></div>
          <div class="pres-hud-dot" data-target="4" title="Slide 4"></div>
        </div>
        <button class="pres-hud-btn" id="presHudNext" title="Next Slide (Swipe Right)">Next ▶</button>
        <button class="pres-hud-btn" id="presHudFs" title="Toggle Fullscreen">⛶</button>
      `;

      // Edge hotspots for quick flick navigation
      const edgePrev = document.createElement('div');
      edgePrev.className = 'pres-nav-edge prev';
      edgePrev.id = 'presEdgePrev';
      edgePrev.innerHTML = '‹';
      edgePrev.title = 'Previous Slide';

      const edgeNext = document.createElement('div');
      edgeNext.className = 'pres-nav-edge next';
      edgeNext.id = 'presEdgeNext';
      edgeNext.innerHTML = '›';
      edgeNext.title = 'Next Slide';

      this.presViewport.appendChild(edgePrev);
      this.presViewport.appendChild(edgeNext);
      this.presViewport.appendChild(hud);

      // Bind HUD listeners
      edgePrev.addEventListener('click', () => this.prevSlide());
      edgeNext.addEventListener('click', () => this.nextSlide());
      document.getElementById('presHudPrev')?.addEventListener('click', () => this.prevSlide());
      document.getElementById('presHudNext')?.addEventListener('click', () => this.nextSlide());
      document.getElementById('presHudFs')?.addEventListener('click', () => this.toggleFullscreen());

      const dots = hud.querySelectorAll('.pres-hud-dot');
      dots.forEach(dot => {
        dot.addEventListener('click', () => {
          const target = parseInt(dot.dataset.target, 10);
          this.goToSlide(target);
        });
      });
    }

    bindPresentationButtons() {
      const btnPrev = document.getElementById('btnPrevSlide');
      const btnNext = document.getElementById('btnNextSlide');
      const btnFs = document.getElementById('btnFullscreenPres');
      const btnLaser = document.getElementById('btnToggleLaser');
      const dots = document.querySelectorAll('.slide-indicators .slide-dot');

      if (btnPrev) btnPrev.addEventListener('click', () => this.prevSlide());
      if (btnNext) btnNext.addEventListener('click', () => this.nextSlide());
      if (btnFs) btnFs.addEventListener('click', () => this.toggleFullscreen());
      if (btnLaser) {
        btnLaser.addEventListener('click', () => {
          this.isPointing = !this.isPointing;
          if (this.laserPointerEl) {
            this.laserPointerEl.style.display = this.isPointing ? 'block' : 'none';
          }
          this.app?.showToast?.(this.isPointing ? '🔴 Laser Pointer Active' : 'Laser Pointer Off');
        });
      }

      dots.forEach(dot => {
        dot.addEventListener('click', () => {
          const target = parseInt(dot.dataset.target, 10);
          this.goToSlide(target);
        });
      });
    }

    bindMouseFallback() {
      if (!this.presViewport) return;
      this.presViewport.addEventListener('mousemove', (e) => {
        const rect = this.presViewport.getBoundingClientRect();
        const nx = (e.clientX - rect.left) / rect.width;
        const ny = (e.clientY - rect.top) / rect.height;
        this.targetPos = { x: Math.max(0, Math.min(1, nx)), y: Math.max(0, Math.min(1, ny)) };

        if (this.app?.state?.laserActive || this.isPointing) {
          this.updateLaserReticle(this.targetPos.x, this.targetPos.y, performance.now());
          this.processDwellHitTesting(this.targetPos.x, this.targetPos.y, performance.now());
        }
      });

      this.presViewport.addEventListener('mouseleave', () => {
        this.resetDwell();
      });
    }

    syncActiveSlide(n) {
      if (n < 1 || n > this.totalSlides) return;
      this.activeSlide = n;
      if (this.app?.state) this.app.state.activeSlide = n;

      const slides = document.querySelectorAll('#presViewport .slide');
      slides.forEach(slide => {
        const sNum = parseInt(slide.dataset.slide, 10);
        if (sNum === n) {
          slide.classList.add('active-slide');
        } else {
          slide.classList.remove('active-slide');
        }
      });

      // Sync both external and in-viewport dots
      const allDots = document.querySelectorAll('.slide-dot, .pres-hud-dot');
      allDots.forEach(dot => {
        const dTarget = parseInt(dot.dataset.target, 10);
        if (dTarget === n) {
          dot.classList.add('active');
        } else {
          dot.classList.remove('active');
        }
      });
    }

    goToSlide(n) {
      if (n < 1 || n > this.totalSlides) return;
      this.syncActiveSlide(n);
      this.app?.showToast?.(`Slide ${n} of ${this.totalSlides}`);
    }

    nextSlide() {
      if (this.activeSlide < this.totalSlides) {
        this.goToSlide(this.activeSlide + 1);
      } else {
        this.app?.showToast?.('Reached final slide (Slide 4)');
      }
    }

    prevSlide() {
      if (this.activeSlide > 1) {
        this.goToSlide(this.activeSlide - 1);
      } else {
        this.app?.showToast?.('First slide (Slide 1)');
      }
    }

    toggleFullscreen() {
      if (!this.presViewport) return;
      if (!document.fullscreenElement) {
        this.presViewport.requestFullscreen?.().catch(() => {
          this.app?.showToast?.('Fullscreen mode blocked or unavailable');
        });
      } else {
        document.exitFullscreen?.();
      }
    }

    // ─────────────────────────────────────────────────────────────
    // Presentation Frame Handler (Called from render loop or hook)
    // ─────────────────────────────────────────────────────────────
    update(state, points, gesture) {
      const now = performance.now();
      const isActiveTab = state ? state.activeTab === 'tab-presentation' : true;

      if (!isActiveTab) {
        if (this.laserPointerEl) this.laserPointerEl.style.display = 'none';
        this.resetDwell();
        this.trailPoints = [];
        this.clearTrailCanvas();
        return;
      }

      // Check swipe gesture
      if (points && points.length > 0) {
        this.detectSwipe(points[0], gesture, now);
      }

      // Check fist reset
      if (gesture === 'FIST') {
        this.detectFistReset(now);
      }

      // Laser Reticle & Dwell Tracking
      const isLaserGesture = gesture === 'POINTING_INDEX' || gesture === 'PINCH';
      const forceLaser = state?.laserActive || this.isPointing;

      if (points && points.length >= 9 && (isLaserGesture || forceLaser)) {
        const tip = points[8]; // Index finger tip
        // Smooth lerp for fluid tracking
        this.targetPos.x = tip.x;
        this.targetPos.y = tip.y;
        this.laserPos.x += (this.targetPos.x - this.laserPos.x) * 0.45;
        this.laserPos.y += (this.targetPos.y - this.laserPos.y) * 0.45;

        this.updateLaserReticle(this.laserPos.x, this.laserPos.y, now);
        this.addTrailPoint(this.laserPos.x, this.laserPos.y, now);

        if (isLaserGesture) {
          this.processDwellHitTesting(this.laserPos.x, this.laserPos.y, now);
        } else {
          this.resetDwell();
        }
      } else if (!forceLaser) {
        if (this.laserPointerEl) this.laserPointerEl.style.display = 'none';
        this.resetDwell();
      }

      this.renderTrail(now);
    }

    updateLaserReticle(normX, normY, now) {
      if (!this.laserPointerEl || !this.presViewport) return;
      this.laserPointerEl.style.left = (normX * 100).toFixed(2) + '%';
      this.laserPointerEl.style.top = (normY * 100).toFixed(2) + '%';
      this.laserPointerEl.style.display = 'block';
    }

    // ─────────────────────────────────────────────────────────────
    // Fluid Motion Trail Rendering
    // ─────────────────────────────────────────────────────────────
    addTrailPoint(normX, normY, now) {
      if (!this.presViewport) return;
      const rect = this.presViewport.getBoundingClientRect();
      const px = normX * rect.width;
      const py = normY * rect.height;

      this.trailPoints.push({ x: px, y: py, t: now });
      if (this.trailPoints.length > this.maxTrailPoints) {
        this.trailPoints.shift();
      }
    }

    renderTrail(now) {
      if (!this.trailCtx || !this.trailCanvas) return;
      const ctx = this.trailCtx;
      const rect = this.presViewport ? this.presViewport.getBoundingClientRect() : { width: 800, height: 500 };

      // Prune expired points
      this.trailPoints = this.trailPoints.filter(p => now - p.t < this.trailDuration);

      ctx.clearRect(0, 0, rect.width, rect.height);
      if (this.trailPoints.length < 2) return;

      ctx.save();
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      for (let i = 1; i < this.trailPoints.length; i++) {
        const p0 = this.trailPoints[i - 1];
        const p1 = this.trailPoints[i];
        const age = now - p1.t;
        const life = Math.max(0, 1 - age / this.trailDuration);
        const alpha = life * 0.85;
        const width = Math.max(1, life * 7);

        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.lineWidth = width;

        // Glowing neon trail
        ctx.strokeStyle = `rgba(255, 23, 68, ${alpha})`;
        ctx.shadowColor = '#ff1744';
        ctx.shadowBlur = Math.floor(life * 12);
        ctx.stroke();

        // Core highlight beam
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.lineWidth = Math.max(0.5, width * 0.35);
        ctx.strokeStyle = `rgba(255, 255, 255, ${alpha * 0.95})`;
        ctx.shadowBlur = 0;
        ctx.stroke();
      }

      ctx.restore();
    }

    clearTrailCanvas() {
      if (!this.trailCtx || !this.trailCanvas) return;
      const rect = this.presViewport ? this.presViewport.getBoundingClientRect() : { width: 800, height: 500 };
      this.trailCtx.clearRect(0, 0, rect.width, rect.height);
    }

    // ─────────────────────────────────────────────────────────────
    // Precise Dwell Click with Bounding Box Mapping
    // ─────────────────────────────────────────────────────────────
    processDwellHitTesting(normX, normY, now) {
      if (!this.presViewport) return;
      if (now < this.dwellCooldownUntil) return;

      const rect = this.presViewport.getBoundingClientRect();
      const screenX = rect.left + normX * rect.width;
      const screenY = rect.top + normY * rect.height;

      // 1. Check element directly under pointer inside viewport
      let hitEl = document.elementFromPoint(screenX, screenY);
      let clickable = hitEl ? hitEl.closest('button, .slide-dot, .pres-hud-dot, .pres-hud-btn, .pres-nav-edge, a') : null;

      // 2. Precise Bounding Box Mapping: Check bottom control bar buttons
      // If laser is near bottom boundary of viewport (normY > 0.80), map to controls bar
      if (!clickable && normY > 0.82) {
        const bottomBarButtons = document.querySelectorAll(
          '.presentation-controls-bar button, .presentation-controls-bar .slide-dot'
        );
        for (const btn of bottomBarButtons) {
          const bRect = btn.getBoundingClientRect();
          // Test hit within element bounds expanded by generous touch margin
          const margin = 10;
          if (
            screenX >= bRect.left - margin &&
            screenX <= bRect.right + margin &&
            screenY >= bRect.top - margin &&
            screenY <= bRect.bottom + margin + 40
          ) {
            clickable = btn;
            break;
          }
        }
      }

      // 3. Process Dwell State Machine
      if (clickable) {
        if (clickable !== this.dwellTargetEl) {
          this.resetDwellTargetVisuals();
          this.dwellTargetEl = clickable;
          this.dwellStartTime = now;
          this.isDwelling = true;
          this.dwellTargetEl.classList.add('dwell-target-active');
          this.laserPointerEl?.classList.add('laser-dwell-active');
        }

        const elapsed = now - this.dwellStartTime;
        const dwellLimit = this.app?.state?.dwellMs || this.dwellDuration;
        const progress = Math.min(1.0, elapsed / dwellLimit);

        // Update Circular SVG Dwell Progress Ring
        // Circumference of r=18 is 2 * PI * 18 = 113.1
        if (this.dwellCircleEl) {
          const offset = 113.1 * (1.0 - progress);
          this.dwellCircleEl.style.strokeDashoffset = offset.toFixed(1);
        }

        if (this.dwellBadgeEl) {
          this.dwellBadgeEl.textContent = `${Math.round(progress * 100)}%`;
        }

        // Also update HUD dwell ring in bottom bar for global consistency
        const appDwellRing = document.getElementById('dwellRing');
        const appDwellLabel = document.getElementById('dwellLabel');
        if (appDwellRing) {
          appDwellRing.style.background = `conic-gradient(#1e8e3e ${progress * 360}deg, transparent 0deg)`;
        }
        if (appDwellLabel) {
          appDwellLabel.textContent = `Dwell: ${Math.round(progress * 100)}%`;
        }

        // Trigger Click when dwell completes
        if (progress >= 1.0) {
          this.executeDwellClick(this.dwellTargetEl);
        }
      } else {
        this.resetDwell();
      }
    }

    executeDwellClick(target) {
      if (!target) return;

      // Audio feedback
      this.app?.playPinchClick?.();

      // Visual click effect
      target.style.transform = 'scale(0.92)';
      setTimeout(() => {
        target.style.transform = '';
      }, 160);

      // Perform action
      target.click();

      // Toast feedback
      const label = target.textContent?.trim() || target.getAttribute('title') || 'Button';
      this.app?.showToast?.(`Dwell Activated: ${label}`);

      // Reset and lock out for cooldown
      this.dwellCooldownUntil = performance.now() + 650;
      this.resetDwell();
    }

    resetDwellTargetVisuals() {
      if (this.dwellTargetEl) {
        this.dwellTargetEl.classList.remove('dwell-target-active');
      }
      this.laserPointerEl?.classList.remove('laser-dwell-active');
      if (this.dwellCircleEl) {
        this.dwellCircleEl.style.strokeDashoffset = '113.1';
      }
      if (this.dwellBadgeEl) {
        this.dwellBadgeEl.textContent = '0%';
      }
    }

    resetDwell() {
      this.resetDwellTargetVisuals();
      this.dwellTargetEl = null;
      this.dwellStartTime = 0;
      this.isDwelling = false;

      const appDwellRing = document.getElementById('dwellRing');
      const appDwellLabel = document.getElementById('dwellLabel');
      if (appDwellRing) appDwellRing.style.background = 'transparent';
      if (appDwellLabel) appDwellLabel.textContent = 'Dwell: Inactive';
    }

    // ─────────────────────────────────────────────────────────────
    // Swipe Gestures: Velocity-Thresholded Horizontal Swipe
    // ─────────────────────────────────────────────────────────────
    detectSwipe(wrist, currentGesture, now) {
      if (!wrist) return;

      this.wristHistory.push({ x: wrist.x, y: wrist.y, t: now });
      if (this.wristHistory.length > 12) this.wristHistory.shift();

      if (now - this.lastSwipeTime < this.swipeCooldownMs) return;

      if (this.wristHistory.length >= 5) {
        const oldest = this.wristHistory[0];
        const newest = this.wristHistory[this.wristHistory.length - 1];
        const dt = (newest.t - oldest.t) / 1000;

        if (dt >= 0.06 && dt <= 0.40) {
          const dx = newest.x - oldest.x;
          const dy = newest.y - oldest.y;
          const velX = dx / dt;

          const thresh = parseFloat(this.app?.els?.rangeSwipeVel?.value) || this.swipeVelocityThreshold;

          // Horizontal swipe must be significantly stronger than vertical drift
          if (Math.abs(dx) > Math.abs(dy) * 1.35) {
            const isAllowedGesture =
              currentGesture === 'OPEN_PALM' ||
              currentGesture === 'POINTING_INDEX' ||
              currentGesture === 'UNKNOWN' ||
              !currentGesture;

            if (velX > thresh && isAllowedGesture) {
              this.lastSwipeTime = now;
              this.wristHistory = [];
              this.handleSwipe('SWIPE_RIGHT');
            } else if (velX < -thresh && isAllowedGesture) {
              this.lastSwipeTime = now;
              this.wristHistory = [];
              this.handleSwipe('SWIPE_LEFT');
            }
          }
        }
      }
    }

    handleSwipe(direction) {
      if (direction === 'SWIPE_RIGHT') {
        this.nextSlide();
        this.app?.playSlideChime?.(1);
        this.app?.showToast?.('👉 Next Slide (Swipe Right)');
        this.app?.showGestureHudBanner?.('👉 SWIPE RIGHT', 'Next Slide', '👉');
      } else if (direction === 'SWIPE_LEFT') {
        this.prevSlide();
        this.app?.playSlideChime?.(-1);
        this.app?.showToast?.('👈 Prev Slide (Swipe Left)');
        this.app?.showGestureHudBanner?.('👈 SWIPE LEFT', 'Previous Slide', '👈');
      }
    }

    // ─────────────────────────────────────────────────────────────
    // Fist Gesture: Instant Reset to Slide 1
    // ─────────────────────────────────────────────────────────────
    detectFistReset(now) {
      if (now - this.lastFistTime < this.fistCooldownMs) return;
      if (this.activeSlide === 1) return;

      this.lastFistTime = now;
      this.goToSlide(1);
      this.app?.playSlideChime?.(-1);
      this.app?.showToast?.('✊ Fist Gesture → Reset to Slide 1');
      this.app?.showGestureHudBanner?.('✊ FIST GESTURE', 'Reset to Slide 1', '✊');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 3. 3D HOLOGRAPHIC SPATIAL PORTAL ENGINE (THREE.JS CORE)
  // ─────────────────────────────────────────────────────────────
  const NEON_PALETTES = [
    {
      name: 'Quantum Cyan',
      core: 0x00f0ff,
      wire: 0xa8c7fa,
      emissive: 0x003344,
      particles: 0x00ffff,
      glowCss: '#00f0ff'
    },
    {
      name: 'Solar Amber',
      core: 0xf9ab00,
      wire: 0xffe082,
      emissive: 0x442800,
      particles: 0xffd54f,
      glowCss: '#f9ab00'
    },
    {
      name: 'Matrix Emerald',
      core: 0x00ff66,
      wire: 0x81c784,
      emissive: 0x003311,
      particles: 0xb9f6ca,
      glowCss: '#00ff66'
    },
    {
      name: 'Hyper Ruby',
      core: 0xff1744,
      wire: 0xef9a9a,
      emissive: 0x440011,
      particles: 0xff80ab,
      glowCss: '#ff1744'
    },
    {
      name: 'Cosmic Violet',
      core: 0x9d00ff,
      wire: 0xce93d8,
      emissive: 0x220044,
      particles: 0xe040fb,
      glowCss: '#9d00ff'
    },
    {
      name: 'Electric Plasma',
      core: 0xff007f,
      wire: 0xff80ab,
      emissive: 0x440022,
      particles: 0xff4081,
      glowCss: '#ff007f'
    }
  ];

  const SHAPE_NAMES = ['Icosahedron', 'TorusKnot', 'Dodecahedron', 'Octahedron', 'Sphere'];

  class HolographicSpatialPortal {
    constructor(visionApp) {
      this.app = visionApp || (typeof window !== 'undefined' ? window.VisionApp : null);
      this.hostEl = null;
      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.resizeObserver = null;

      // Meshes
      this.coreMesh = null;
      this.wireframeMesh = null;
      this.particleSystem = null;

      // Selection indices
      this.shapeIndex = 0; // 0..4
      this.paletteIndex = 0; // 0..5

      // Kinematic Lerp State
      this.currentScale = 1.0;
      this.targetScale = 1.0;
      this.currentRotX = 0;
      this.currentRotY = 0;
      this.currentRotZ = 0;
      this.targetRotX = 0;
      this.targetRotY = 0;
      this.targetRotZ = 0;

      // Zero-dimension safe flag
      this.isInitialized = false;
      this.lastFrameTime = performance.now();
    }

    init() {
      if (typeof document === 'undefined') return;
      if (typeof THREE === 'undefined') {
        console.warn('Three.js not yet loaded. Will retry upon script availability.');
        return;
      }

      this.hostEl = document.getElementById('spatial3dHost');
      if (!this.hostEl) return;

      // Clean host element
      this.hostEl.innerHTML = '';

      // Safe dimension check (handles zero-dimension load safely)
      const rect = this.hostEl.getBoundingClientRect();
      const width = Math.max(rect.width || this.hostEl.clientWidth || 800, 320);
      const height = Math.max(rect.height || this.hostEl.clientHeight || 500, 240);

      // Scene & Camera
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
      this.camera.position.set(0, 0, 4.5);

      // WebGL Renderer
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance'
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.hostEl.appendChild(this.renderer.domElement);

      // Futuristic Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
      this.scene.add(ambientLight);

      const dirLight1 = new THREE.DirectionalLight(0x00f0ff, 2.4);
      dirLight1.position.set(3, 4, 3);
      this.scene.add(dirLight1);

      const dirLight2 = new THREE.DirectionalLight(0xf9ab00, 1.6);
      dirLight2.position.set(-3, -3, 2);
      this.scene.add(dirLight2);

      const pointLight = new THREE.PointLight(0xffffff, 1.4, 10);
      pointLight.position.set(0, 0, 2.5);
      this.scene.add(pointLight);

      // Build Meshes & Starfield
      this.buildMeshes();
      this.buildParticleStarfield();

      // UI Controls
      this.bindControls();

      // Viewport Resize & Zero-Dimension Observers
      this.setupResizeHandling();

      this.isInitialized = true;
    }

    setupResizeHandling() {
      // 1. Window Resize
      window.addEventListener('resize', () => this.handleResize());

      // 2. ResizeObserver on container
      if (typeof ResizeObserver !== 'undefined' && this.hostEl) {
        this.resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            const cr = entry.contentRect;
            if (cr.width > 0 && cr.height > 0) {
              this.handleResize(cr.width, cr.height);
            }
          }
        });
        this.resizeObserver.observe(this.hostEl);
      }

      // 3. Tab switch re-check (in case tab was display:none on initial load)
      const tabBtn = document.getElementById('tabBtn-spatial3d');
      if (tabBtn) {
        tabBtn.addEventListener('click', () => {
          setTimeout(() => this.handleResize(), 50);
          setTimeout(() => this.handleResize(), 180);
        });
      }
    }

    handleResize(forcedW, forcedH) {
      if (!this.renderer || !this.camera || !this.hostEl) return;
      const w = Math.max(forcedW || this.hostEl.clientWidth || 800, 320);
      const h = Math.max(forcedH || this.hostEl.clientHeight || 500, 240);

      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }

    buildMeshes() {
      if (this.coreMesh) this.scene.remove(this.coreMesh);
      if (this.wireframeMesh) this.scene.remove(this.wireframeMesh);

      let coreGeom, wireGeom;

      switch (this.shapeIndex) {
        case 1: // TorusKnot
          coreGeom = new THREE.TorusKnotGeometry(0.72, 0.23, 100, 18);
          wireGeom = new THREE.TorusKnotGeometry(0.78, 0.25, 48, 8);
          break;
        case 2: // Dodecahedron
          coreGeom = new THREE.DodecahedronGeometry(1.1, 0);
          wireGeom = new THREE.DodecahedronGeometry(1.32, 0);
          break;
        case 3: // Octahedron
          coreGeom = new THREE.OctahedronGeometry(1.2, 0);
          wireGeom = new THREE.OctahedronGeometry(1.4, 0);
          break;
        case 4: // Sphere
          coreGeom = new THREE.SphereGeometry(1.05, 32, 24);
          wireGeom = new THREE.SphereGeometry(1.28, 16, 12);
          break;
        case 0: // Icosahedron (Default)
        default:
          coreGeom = new THREE.IcosahedronGeometry(1.1, 1);
          wireGeom = new THREE.IcosahedronGeometry(1.38, 0);
          break;
      }

      const palette = NEON_PALETTES[this.paletteIndex];

      // Shiny Holographic Core Material
      const coreMat = new THREE.MeshStandardMaterial({
        color: palette.core,
        emissive: palette.emissive,
        roughness: 0.12,
        metalness: 0.88
      });
      this.coreMesh = new THREE.Mesh(coreGeom, coreMat);
      this.scene.add(this.coreMesh);

      // Holographic Outer Wireframe Cage
      const wireMat = new THREE.MeshBasicMaterial({
        color: palette.wire,
        wireframe: true,
        transparent: true,
        opacity: 0.48
      });
      this.wireframeMesh = new THREE.Mesh(wireGeom, wireMat);
      this.scene.add(this.wireframeMesh);
    }

    buildParticleStarfield() {
      if (this.particleSystem) this.scene.remove(this.particleSystem);

      const partCount = 260;
      const geom = new THREE.BufferGeometry();
      const positions = new Float32Array(partCount * 3);

      for (let i = 0; i < partCount * 3; i += 3) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(Math.random() * 2 - 1);
        const r = 1.7 + Math.random() * 1.6;
        positions[i] = r * Math.sin(phi) * Math.cos(theta);
        positions[i + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i + 2] = r * Math.cos(phi);
      }

      geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

      const palette = NEON_PALETTES[this.paletteIndex];
      const mat = new THREE.PointsMaterial({
        color: palette.particles,
        size: 0.05,
        transparent: true,
        opacity: 0.85
      });

      this.particleSystem = new THREE.Points(geom, mat);
      this.scene.add(this.particleSystem);
    }

    bindControls() {
      const btnColor = document.getElementById('btnSpatialColor');
      const btnShape = document.getElementById('btnSpatialShape');
      const btnReset = document.getElementById('btnSpatialReset');

      if (btnColor) {
        btnColor.addEventListener('click', () => this.cyclePalette());
      }

      if (btnShape) {
        btnShape.addEventListener('click', () => this.cycleShape());
      }

      if (btnReset) {
        btnReset.addEventListener('click', () => this.resetSpatial());
      }
    }

    cycleShape() {
      this.shapeIndex = (this.shapeIndex + 1) % SHAPE_NAMES.length;
      this.buildMeshes();

      const name = SHAPE_NAMES[this.shapeIndex];
      const btn = document.getElementById('btnSpatialShape');
      if (btn) btn.textContent = `💠 Shape: ${name}`;

      this.app?.playPinchClick?.();
      this.app?.showToast?.(`Holographic Shape: ${name}`);
    }

    setShape(idx) {
      if (idx < 0 || idx >= SHAPE_NAMES.length) return;
      this.shapeIndex = idx;
      this.buildMeshes();
      const btn = document.getElementById('btnSpatialShape');
      if (btn) btn.textContent = `💠 Shape: ${SHAPE_NAMES[idx]}`;
    }

    cyclePalette() {
      this.paletteIndex = (this.paletteIndex + 1) % NEON_PALETTES.length;
      const p = NEON_PALETTES[this.paletteIndex];

      if (this.coreMesh?.material) {
        this.coreMesh.material.color.setHex(p.core);
        this.coreMesh.material.emissive.setHex(p.emissive);
      }
      if (this.wireframeMesh?.material) {
        this.wireframeMesh.material.color.setHex(p.wire);
      }
      if (this.particleSystem?.material) {
        this.particleSystem.material.color.setHex(p.particles);
      }

      const btn = document.getElementById('btnSpatialColor');
      if (btn) btn.textContent = `💎 Color: ${p.name}`;

      this.app?.playPinchClick?.();
      this.app?.showToast?.(`Neon Palette: ${p.name}`);
    }

    setPalette(idx) {
      if (idx < 0 || idx >= NEON_PALETTES.length) return;
      this.paletteIndex = idx;
      const p = NEON_PALETTES[idx];
      if (this.coreMesh?.material) {
        this.coreMesh.material.color.setHex(p.core);
        this.coreMesh.material.emissive.setHex(p.emissive);
      }
      if (this.wireframeMesh?.material) {
        this.wireframeMesh.material.color.setHex(p.wire);
      }
      if (this.particleSystem?.material) {
        this.particleSystem.material.color.setHex(p.particles);
      }
      const btn = document.getElementById('btnSpatialColor');
      if (btn) btn.textContent = `💎 Color: ${p.name}`;
    }

    resetSpatial() {
      this.currentScale = 1.0;
      this.targetScale = 1.0;
      this.currentRotX = 0;
      this.currentRotY = 0;
      this.currentRotZ = 0;

      if (this.coreMesh) {
        this.coreMesh.rotation.set(0, 0, 0);
        this.coreMesh.scale.set(1, 1, 1);
      }
      if (this.wireframeMesh) {
        this.wireframeMesh.rotation.set(0, 0, 0);
        this.wireframeMesh.scale.set(1, 1, 1);
      }

      this.app?.playSlideChime?.(1);
      this.app?.showToast?.('Centered 3D Spatial Core');
    }

    // ─────────────────────────────────────────────────────────────
    // Spatial Portal Frame Update
    // ─────────────────────────────────────────────────────────────
    update(state) {
      if (!this.isInitialized || !this.renderer || !this.scene || !this.camera || !this.coreMesh) {
        if (!this.isInitialized && typeof THREE !== 'undefined') {
          this.init();
        }
        return;
      }

      // Check tab visibility
      const isActiveTab = state ? state.activeTab === 'tab-spatial3d' : true;
      if (!isActiveTab) return;

      const now = performance.now();
      this.lastFrameTime = now;

      // Parallax rotation of outer wireframe cage & starfield
      if (this.wireframeMesh) {
        this.wireframeMesh.rotation.x -= 0.005;
        this.wireframeMesh.rotation.y += 0.008;
      }
      if (this.particleSystem) {
        this.particleSystem.rotation.y += 0.002;
      }

      const statsEl = document.getElementById('spatialStats');
      let statusText = '';

      // ── DUAL HAND SPATIAL KINEMATICS ──
      if (state?.multiHandLandmarks && state.multiHandLandmarks.length >= 2) {
        const h0 = state.multiHandLandmarks[0]; // Primary Hand (Pitch & Yaw)
        const h1 = state.multiHandLandmarks[1]; // Secondary Hand (Span Zoom & Pinch Roll)

        // 1. Dual-Hand Pitch & Yaw Rotation (Hand 0 wrist/palm)
        const targetRotY = (h0[0].x - 0.5) * 4.6;
        const targetRotX = (h0[0].y - 0.5) * 3.6;

        this.currentRotX += (targetRotX - this.currentRotX) * 0.12;
        this.currentRotY += (targetRotY - this.currentRotY) * 0.12;

        // 2. Two-Hand Span Zoom with Smooth Lerp Dampening
        const spanInter = Math.hypot(h0[0].x - h1[0].x, h0[0].y - h1[0].y);
        this.targetScale = Math.max(0.45, Math.min(3.4, spanInter * 4.4));
        this.currentScale += (this.targetScale - this.currentScale) * 0.10;

        // 3. Pinch Roll (Hand 1 Thumb to Index Distance)
        const isH1Pinch = Math.hypot(h1[4].x - h1[8].x, h1[4].y - h1[8].y) < 0.085;
        if (isH1Pinch) {
          this.currentRotZ += 0.085;
        }

        // Apply transforms
        this.coreMesh.rotation.x = this.currentRotX;
        this.coreMesh.rotation.y = this.currentRotY;
        this.coreMesh.rotation.z = this.currentRotZ;
        this.coreMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);

        if (this.wireframeMesh) {
          this.wireframeMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);
        }

        statusText = `Dual Hands Active • Span Zoom: ${this.currentScale.toFixed(2)}x • Pitch: ${(this.currentRotX * 57.3).toFixed(1)}° • Yaw: ${(this.currentRotY * 57.3).toFixed(1)}° • Roll: ${(this.currentRotZ * 57.3).toFixed(1)}° • ${SHAPE_NAMES[this.shapeIndex]}`;
      }
      // ── SINGLE HAND FALLBACK KINEMATICS ──
      else if (state?.landmarks && state.landmarks.length === 21 && state.handDetected) {
        const wrist = state.landmarks[0];
        const thumbTip = state.landmarks[4];
        const indexTip = state.landmarks[8];
        const pinkyTip = state.landmarks[20];

        // Pitch & Yaw from Hand Position
        const targetRotY = (wrist.x - 0.5) * 4.2;
        const targetRotX = (wrist.y - 0.5) * 3.2;

        this.currentRotX += (targetRotX - this.currentRotX) * 0.12;
        this.currentRotY += (targetRotY - this.currentRotY) * 0.12;

        // Single-Hand Thumb-to-Pinky Span Zoom with Lerp Dampening
        const span = Math.hypot(thumbTip.x - pinkyTip.x, thumbTip.y - pinkyTip.y);
        this.targetScale = Math.max(0.5, Math.min(2.8, span * 4.6));
        this.currentScale += (this.targetScale - this.currentScale) * 0.10;

        // Pinch Roll
        const isPinch = state.activeGesture === 'PINCH' || Math.hypot(thumbTip.x - indexTip.x, thumbTip.y - indexTip.y) < 0.075;
        if (isPinch) {
          this.currentRotZ += 0.075;
        }

        this.coreMesh.rotation.x = this.currentRotX;
        this.coreMesh.rotation.y = this.currentRotY;
        this.coreMesh.rotation.z = this.currentRotZ;
        this.coreMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);

        if (this.wireframeMesh) {
          this.wireframeMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);
        }

        statusText = `Single Hand: ${state.activeGesture || 'ACTIVE'} • Zoom: ${this.currentScale.toFixed(2)}x • Pitch: ${(this.currentRotX * 57.3).toFixed(1)}° • Yaw: ${(this.currentRotY * 57.3).toFixed(1)}° • Roll: ${(this.currentRotZ * 57.3).toFixed(1)}° • ${SHAPE_NAMES[this.shapeIndex]}`;
      }
      // ── IDLE / SIMULATION DRIFT ──
      else {
        this.currentRotX += 0.007;
        this.currentRotY += 0.011;
        this.currentScale += (1.0 - this.currentScale) * 0.04;

        this.coreMesh.rotation.x = this.currentRotX;
        this.coreMesh.rotation.y = this.currentRotY;
        this.coreMesh.rotation.z = this.currentRotZ;
        this.coreMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);

        if (this.wireframeMesh) {
          this.wireframeMesh.scale.set(this.currentScale, this.currentScale, this.currentScale);
        }

        statusText = `Holographic Core: Autonomous Drift • Zoom: 1.00x • Pitch: ${(this.currentRotX * 57.3).toFixed(1)}° • Yaw: ${(this.currentRotY * 57.3).toFixed(1)}° • ${SHAPE_NAMES[this.shapeIndex]} • ${NEON_PALETTES[this.paletteIndex].name}`;
      }

      if (statsEl) {
        statsEl.textContent = statusText;
      }

      // Render Three.js Scene
      this.renderer.render(this.scene, this.camera);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 4. ATTACH TO WINDOW.VISIONAPP & BOOTSTRAP
  // ─────────────────────────────────────────────────────────────
  let presController = null;
  let spatialPortal = null;
  let isAnimationLoopRunning = false;

  function initModule(visionApp) {
    const app = visionApp || (typeof window !== 'undefined' ? window.VisionApp : null);

    if (!presController) {
      presController = new TouchlessPresentationController(app);
      presController.init();
    }

    if (!spatialPortal) {
      spatialPortal = new HolographicSpatialPortal(app);
      spatialPortal.init();
    }

    // Start self-contained loop if not already driven by main app
    if (!isAnimationLoopRunning && typeof window !== 'undefined') {
      isAnimationLoopRunning = true;
      function tick() {
        const currentApp = window.VisionApp || app;
        const state = currentApp?.state;

        if (state) {
          if (state.activeTab === 'tab-presentation' && presController) {
            presController.update(state, state.landmarks, state.activeGesture);
          } else if (state.activeTab === 'tab-spatial3d' && spatialPortal) {
            spatialPortal.update(state);
          }
        }
        window.requestAnimationFrame(tick);
      }
      window.requestAnimationFrame(tick);
    }

    // Public Module API
    const api = {
      presentation: presController,
      spatial: spatialPortal,

      // Presentation API
      goToSlide: (n) => presController?.goToSlide(n),
      nextSlide: () => presController?.nextSlide(),
      prevSlide: () => presController?.prevSlide(),
      handleSwipe: (dir) => presController?.handleSwipe(dir),
      resetPresentation: () => presController?.goToSlide(1),
      updatePresentation: (state, points, gesture) => presController?.update(state, points, gesture),

      // 3D Spatial API
      cycleShape: () => spatialPortal?.cycleShape(),
      setShape: (idx) => spatialPortal?.setShape(idx),
      cyclePalette: () => spatialPortal?.cyclePalette(),
      setPalette: (idx) => spatialPortal?.setPalette(idx),
      resetSpatial: () => spatialPortal?.resetSpatial(),
      updateSpatial: (state) => spatialPortal?.update(state),

      // Query States
      getPresentationState: () => ({
        activeSlide: presController?.activeSlide || 1,
        totalSlides: presController?.totalSlides || 4,
        isDwelling: presController?.isDwelling || false
      }),
      getSpatialState: () => ({
        shape: SHAPE_NAMES[spatialPortal?.shapeIndex || 0],
        palette: NEON_PALETTES[spatialPortal?.paletteIndex || 0].name,
        scale: spatialPortal?.currentScale || 1.0,
        pitch: spatialPortal?.currentRotX || 0,
        yaw: spatialPortal?.currentRotY || 0,
        roll: spatialPortal?.currentRotZ || 0
      })
    };

    if (app) {
      app.tools = app.tools || {};
      app.tools.presentationSpatial = api;
    }

    return api;
  }

  // Automatic Lifecycle Bootstrap
  if (typeof window !== 'undefined') {
    window.VisionApp = window.VisionApp || {};
    window.VisionApp.tools = window.VisionApp.tools || {};

    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', () => {
        initModule(window.VisionApp);
      });
    } else {
      initModule(window.VisionApp);
    }
  }

  return {
    init: initModule,
    TouchlessPresentationController,
    HolographicSpatialPortal,
    NEON_PALETTES,
    SHAPE_NAMES
  };
});
