/**
 * Vision Studio - Gesture FX Studio & Touchless Macropad Modular Extension Engine
 * File: public/js/tool-gesturefx.js
 * 
 * Hyperfocused on tab-gesturefx:
 * - Kinetic Particle Spellcasting: Fireball, Cryo Frost, Tesla Arc Lightning, Grav Repulsor, Chrono Time Echoes
 * - Posture Triggering: Open palm charging, index finger aiming/casting, two-hand shockwave bursts
 * - DJ Audio Filter Engine: Real-time BiquadFilterNode Low-Pass Filter sweep mapped to hand height (200 Hz - 12,000 Hz)
 *   and Resonance (Q) mapped to horizontal span (0.5 - 15.0 Q), live audio synthesis & frequency analyzer bar
 * - Touchless Macropad: Fingertip collision detection against onscreen macro pads (Bullet Time, Spell select, Canvas clear)
 *   with hover glow, dwell circles, and Web Audio trigger sound
 * - Decoupled from all other tools, presentation controllers, and filter lenses
 */

(function(window) {
  'use strict';

  // =========================================================================
  // CONSTANTS & SPELL METADATA
  // =========================================================================
  const SPELL_METADATA = {
    fireball: {
      key: 'fireball',
      name: 'Pyrokinesis: Solar Fireball',
      color: '#ff5500',
      glowColor: '#ffaa00',
      cost: 0.15,
      icon: '🔥',
      hint: 'Thrust open palm or aim index finger to cast Solar Fireball.'
    },
    cryo: {
      key: 'cryo',
      name: 'Cryokinesis: Frost Freeze',
      color: '#00f0ff',
      glowColor: '#a5f3fc',
      cost: 0.18,
      icon: '❄️',
      hint: 'Spread palm wide to unleash cryogenic sub-zero frost blast.'
    },
    lightning: {
      key: 'lightning',
      name: 'Electrokinesis: Tesla Arc',
      color: '#a855f7',
      glowColor: '#38bdf8',
      cost: 0.20,
      icon: '⚡',
      hint: 'Point index finger to aim and discharge Tesla arc lightning bolts.'
    },
    repulsor: {
      key: 'repulsor',
      name: 'Gravitokinesis: Grav Repulsor',
      color: '#ec4899',
      glowColor: '#9333ea',
      cost: 0.25,
      icon: '🌌',
      hint: 'Thrust both open palms forward to trigger a dual grav shockwave.'
    },
    chrono_echoes: {
      key: 'chrono_echoes',
      name: 'Chronokinesis: Time Echoes',
      color: '#fbbf24',
      glowColor: '#f59e0b',
      cost: 0.22,
      icon: '⏱️',
      hint: 'Hold fist or move hand steadily to cast temporal time echoes.'
    },
    bullet_time: {
      key: 'bullet_time',
      name: 'Matrix Chrono Dilation',
      color: '#22c55e',
      glowColor: '#4ade80',
      cost: 0.10,
      icon: '⏱️',
      hint: 'Engage matrix bullet time slow-motion dilation.'
    },
    optical_particles: {
      key: 'optical_particles',
      name: 'Cosmic Fluid Particle Wave',
      color: '#38bdf8',
      glowColor: '#60a5fa',
      cost: 0.05,
      icon: '🌊',
      hint: 'Fluid particle wave reacting to spatial hand velocity.'
    }
  };

  // Map legacy / alternative spell keys
  const SPELL_KEY_ALIASES = {
    fire: 'fireball',
    ice: 'cryo',
    ice_freeze: 'cryo',
    frost: 'cryo',
    tesla: 'lightning',
    tesla_storm: 'lightning',
    gravity: 'repulsor',
    shockwave: 'repulsor',
    chrono: 'chrono_echoes',
    echoes: 'chrono_echoes'
  };

  function normalizeSpellKey(key) {
    if (!key) return 'fireball';
    const lower = String(key).toLowerCase();
    return SPELL_KEY_ALIASES[lower] || lower;
  }

  // =========================================================================
  // GESTURE FX STUDIO CONTROLLER STATE
  // =========================================================================
  const fxState = {
    initialized: false,
    active: true,
    activeSpell: 'fireball',
    mana: 1.0,
    bulletTimeFactor: 1.0,
    spells: [],
    particles: [],
    temporalEchoes: [], // Historical hand poses for Chrono Time Echoes
    lastSpellCastTime: 0,
    lastMacroTriggerTime: 0,
    lastShockwaveTime: 0,
    eventCount: 0,

    // Posture state tracking
    charging: {
      active: false,
      handIndex: 0,
      progress: 0.0,
      x: 0,
      y: 0,
      chargeDuration: 0,
      lastUpdateTime: 0
    },
    aiming: {
      active: false,
      handIndex: 0,
      originX: 0,
      originY: 0,
      targetX: 0,
      targetY: 0,
      angle: 0,
      lockDuration: 0,
      lastCastTime: 0
    },
    twoHandShockwave: {
      active: false,
      lastTrigger: 0,
      cooldown: 800 // ms
    },

    // Touchless Macropad state
    macropad: {
      hoveredKey: null,
      hoverStartTime: 0,
      dwellProgress: 0.0,
      dwellDuration: 360, // ms to trigger dwell action
      lastTriggeredKey: null,
      lastTriggerTime: 0
    },

    // DJ Audio Synthesizer Engine
    djAudio: {
      enabled: false,
      audioCtx: null,
      osc1: null,
      osc2: null,
      oscSub: null,
      noiseNode: null,
      biquadFilter: null,
      gainNode: null,
      analyser: null,
      freqData: null,
      cutoff: 3200, // 200 Hz - 12000 Hz
      resonance: 4.2, // 0.5 Q - 15.0 Q
      isSynthesizing: false
    }
  };

  // Cached DOM Elements
  let domEls = {};

  function queryDomElements() {
    domEls = {
      stage: document.getElementById('gestureFxStage'),
      canvas: document.getElementById('gestureFxCanvas'),
      macropad: document.getElementById('spatialMacropad'),
      macroButtons: document.querySelectorAll('.macro-btn'),
      spellChips: document.querySelectorAll('#spellSelectorStrip .filter-chip'),
      spellBadge: document.getElementById('fxSpellBadge'),
      spellName: document.getElementById('fxSpellName'),
      powerBadge: document.getElementById('fxGesturePowerBadge'),
      powerText: document.getElementById('fxPowerText'),
      djCutoffVal: document.getElementById('djCutoffVal'),
      djResonanceVal: document.getElementById('djResonanceVal'),
      djMeterBar: document.getElementById('djMeterBar'),
      fxLogBox: document.getElementById('fxLogBox'),
      fxEventCount: document.getElementById('fxEventCount'),
      fxLiveBadge: document.getElementById('fxLiveBadge'),
      btnCastTrigger: document.getElementById('btnCastSpellTrigger'),
      btnClearStage: document.getElementById('btnClearFxStage'),
      webcamVideo: document.getElementById('webcamVideo')
    };
  }

  // =========================================================================
  // LOGGING & TOAST HELPERS
  // =========================================================================
  function logEvent(htmlMessage) {
    fxState.eventCount++;
    if (domEls.fxEventCount) {
      domEls.fxEventCount.textContent = `${fxState.eventCount} event${fxState.eventCount === 1 ? '' : 's'}`;
    }
    if (domEls.fxLogBox) {
      const timeStr = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const line = document.createElement('div');
      line.style.marginBottom = '3px';
      line.innerHTML = `<span style="color:#71717a;">[${timeStr}]</span> ${htmlMessage}`;
      domEls.fxLogBox.appendChild(line);
      while (domEls.fxLogBox.childNodes.length > 50) {
        domEls.fxLogBox.removeChild(domEls.fxLogBox.firstChild);
      }
      domEls.fxLogBox.scrollTop = domEls.fxLogBox.scrollHeight;
    }
  }

  function showNotification(msg) {
    if (window.VisionApp && typeof window.VisionApp.showToast === 'function') {
      window.VisionApp.showToast(msg);
    }
  }

  // =========================================================================
  // WEB AUDIO & DJ FILTER ENGINE
  // =========================================================================
  function getOrCreateAudioContext() {
    if (fxState.djAudio.audioCtx && fxState.djAudio.audioCtx.state !== 'closed') {
      return fxState.djAudio.audioCtx;
    }
    if (window.VisionApp && typeof window.VisionApp.getAudioContext === 'function') {
      const appCtx = window.VisionApp.getAudioContext();
      if (appCtx && appCtx.state !== 'closed') {
        fxState.djAudio.audioCtx = appCtx;
        return appCtx;
      }
    }
    const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    if (AudioCtxClass) {
      try {
        fxState.djAudio.audioCtx = new AudioCtxClass();
      } catch (e) {
        console.warn('[GestureFX] Web Audio Context initialization failed:', e);
      }
    }
    return fxState.djAudio.audioCtx;
  }

  /**
   * Initializes the DJ Audio Synthesizer:
   * Multi-oscillator harmonic chord pad + pink noise routed through
   * a Web Audio BiquadFilterNode (Low-Pass) and AnalyserNode.
   */
  function initDjAudioSynthesizer() {
    const ctx = getOrCreateAudioContext();
    if (!ctx) return;
    if (fxState.djAudio.isSynthesizing) return;

    try {
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }

      // 1. Create Biquad Low-Pass Filter
      const biquad = ctx.createBiquadFilter();
      biquad.type = 'lowpass';
      biquad.frequency.setValueAtTime(fxState.djAudio.cutoff, ctx.currentTime);
      biquad.Q.setValueAtTime(fxState.djAudio.resonance, ctx.currentTime);
      fxState.djAudio.biquadFilter = biquad;

      // 2. Create Master Gain Node
      const masterGain = ctx.createGain();
      masterGain.gain.setValueAtTime(0.001, ctx.currentTime); // Start silent, ramp up
      fxState.djAudio.gainNode = masterGain;

      // 3. Create Frequency Analyser Node
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.82;
      fxState.djAudio.analyser = analyser;
      fxState.djAudio.freqData = new Uint8Array(analyser.frequencyBinCount);

      // Connect: Filter -> Gain -> Analyser -> Destination
      biquad.connect(masterGain);
      masterGain.connect(analyser);
      analyser.connect(ctx.destination);

      // 4. Create Harmonic Oscillators (Am7 Cyber Synth Chord: A2 110Hz, C3 130.81Hz, E3 164.81Hz, G3 196Hz)
      const notes = [110, 130.81, 164.81, 196];
      const oscTypes = ['sawtooth', 'triangle', 'sawtooth', 'sine'];

      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        osc.type = oscTypes[idx % oscTypes.length];
        osc.frequency.setValueAtTime(freq, ctx.currentTime);
        // Subtle detune for lush analog chorus
        osc.detune.setValueAtTime((idx - 1.5) * 7.5, ctx.currentTime);

        const oscGain = ctx.createGain();
        oscGain.gain.setValueAtTime(0.08 / notes.length, ctx.currentTime);

        osc.connect(oscGain);
        oscGain.connect(biquad);
        osc.start();
      });

      // 5. Create Subtle Pink/Filtered Noise for Air Texture
      const bufferSize = ctx.sampleRate * 2;
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      let b0 = 0, b1 = 0, b2 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.96900 * b2 + white * 0.1538520;
        output[i] = (b0 + b1 + b2 + white * 0.1) * 0.05;
      }
      const whiteNoise = ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;
      whiteNoise.loop = true;
      const noiseGain = ctx.createGain();
      noiseGain.gain.setValueAtTime(0.02, ctx.currentTime);
      whiteNoise.connect(noiseGain);
      noiseGain.connect(biquad);
      whiteNoise.start();

      fxState.djAudio.isSynthesizing = true;
      fxState.djAudio.enabled = true;

      // Smooth fade in
      masterGain.gain.setTargetAtTime(0.18, ctx.currentTime, 0.25);
      logEvent(`🎛️ <strong>Live DJ Audio Synthesizer</strong> engaged [BiquadFilter: Low-Pass]`);
    } catch (e) {
      console.warn('[GestureFX] Error starting DJ synthesizer:', e);
    }
  }

  function stopDjAudioSynthesizer() {
    if (!fxState.djAudio.isSynthesizing || !fxState.djAudio.gainNode || !fxState.djAudio.audioCtx) return;
    try {
      const ctx = fxState.djAudio.audioCtx;
      fxState.djAudio.gainNode.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.15);
      fxState.djAudio.enabled = false;
    } catch (e) {}
  }

  function toggleDjAudio() {
    if (!fxState.djAudio.isSynthesizing || !fxState.djAudio.enabled) {
      initDjAudioSynthesizer();
      if (fxState.djAudio.gainNode && fxState.djAudio.audioCtx) {
        fxState.djAudio.gainNode.gain.setTargetAtTime(0.18, fxState.djAudio.audioCtx.currentTime, 0.1);
        fxState.djAudio.enabled = true;
      }
      showNotification('DJ Audio Synth Enabled');
    } else {
      stopDjAudioSynthesizer();
      showNotification('DJ Audio Synth Muted');
    }
  }

  /**
   * Real-time update of DJ Filter Cutoff (Y) and Resonance (X)
   * Y-axis mapped to: 200 Hz - 12,000 Hz (inverted so higher hand = higher cutoff)
   * X-axis mapped to: 0.5 Q - 15.0 Q (horizontal spread/span)
   */
  function updateDjFilter(h0, h1) {
    if (!h0) return;
    const ctx = fxState.djAudio.audioCtx;

    // Y position (landmark 8 tip or landmark 0 wrist)
    const yVal = Math.max(0.02, Math.min(0.98, h0[8] ? h0[8].y : 0.5));
    // Invert Y so hand raised high = higher cutoff frequency (open filter)
    const targetCutoff = Math.round(200 + Math.pow(1.0 - yVal, 1.8) * 11800);
    fxState.djAudio.cutoff = Math.max(200, Math.min(12000, targetCutoff));

    // X position or dual hand span
    let xVal = 0.5;
    if (h1 && h0) {
      const span = Math.abs((h1[8] ? h1[8].x : 0.7) - (h0[8] ? h0[8].x : 0.3));
      xVal = Math.max(0.05, Math.min(0.95, span));
    } else if (h0[8]) {
      xVal = Math.max(0.05, Math.min(0.95, h0[8].x));
    }
    const targetQ = +(0.5 + xVal * 14.5).toFixed(1);
    fxState.djAudio.resonance = Math.max(0.5, Math.min(15.0, targetQ));

    // Update Web Audio BiquadFilter parameters smoothly without clicks
    if (fxState.djAudio.biquadFilter && ctx && ctx.state === 'running') {
      try {
        fxState.djAudio.biquadFilter.frequency.setTargetAtTime(fxState.djAudio.cutoff, ctx.currentTime, 0.04);
        fxState.djAudio.biquadFilter.Q.setTargetAtTime(fxState.djAudio.resonance, ctx.currentTime, 0.04);
      } catch (e) {}
    }

    // Update DOM UI elements
    if (domEls.djCutoffVal) {
      domEls.djCutoffVal.textContent = `${fxState.djAudio.cutoff.toLocaleString()} Hz`;
    }
    if (domEls.djResonanceVal) {
      domEls.djResonanceVal.textContent = `${fxState.djAudio.resonance} Q`;
    }
    if (domEls.djMeterBar) {
      const pct = Math.round(((fxState.djAudio.cutoff - 200) / 11800) * 100);
      domEls.djMeterBar.style.width = `${pct}%`;
    }

    // Sync back to VisionApp state if available
    if (window.VisionApp && window.VisionApp.state && window.VisionApp.state.gestureFx) {
      window.VisionApp.state.gestureFx.djCutoff = fxState.djAudio.cutoff;
      window.VisionApp.state.gestureFx.djResonance = fxState.djAudio.resonance;
    }
  }

  // =========================================================================
  // SYNTHESIZED SFX GENERATOR
  // =========================================================================
  function playSound(type) {
    const ctx = getOrCreateAudioContext();
    if (!ctx) return;
    try {
      if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      const t = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      if (type === 'fireball') {
        // Whoosh + explosive rumble
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(420, t);
        osc.frequency.exponentialRampToValueAtTime(70, t + 0.35);
        gain.gain.setValueAtTime(0.24, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.38);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.40);
      } else if (type === 'cryo') {
        // High crystalline ice freeze chime
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1480, t);
        osc.frequency.setValueAtTime(1960, t + 0.08);
        osc.frequency.setValueAtTime(2620, t + 0.16);
        gain.gain.setValueAtTime(0.18, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.32);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.34);
      } else if (type === 'lightning') {
        // Electrical arc crackle
        osc.type = 'square';
        osc.frequency.setValueAtTime(880, t);
        osc.frequency.setValueAtTime(1760, t + 0.04);
        osc.frequency.setValueAtTime(330, t + 0.09);
        osc.frequency.setValueAtTime(1320, t + 0.14);
        gain.gain.setValueAtTime(0.20, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.24);
      } else if (type === 'repulsor') {
        // Deep sub-bass grav pulse drop
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(160, t);
        osc.frequency.exponentialRampToValueAtTime(32, t + 0.42);
        gain.gain.setValueAtTime(0.35, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.46);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.48);
      } else if (type === 'chrono_echoes' || type === 'bullet_time') {
        // Slow-mo pitch bend / time echo sweep
        osc.type = 'sine';
        osc.frequency.setValueAtTime(520, t);
        osc.frequency.exponentialRampToValueAtTime(180, t + 0.45);
        gain.gain.setValueAtTime(0.22, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.48);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.50);
      } else if (type === 'click' || type === 'macro') {
        // Snappy tactile macro click
        osc.type = 'sine';
        osc.frequency.setValueAtTime(950, t);
        osc.frequency.exponentialRampToValueAtTime(280, t + 0.04);
        gain.gain.setValueAtTime(0.18, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.06);
      } else if (type === 'hover') {
        // Gentle micro tick
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(1200, t);
        gain.gain.setValueAtTime(0.04, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.02);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.025);
      }
    } catch (e) {}
  }

  // =========================================================================
  // KINETIC PARTICLE SPELLCASTING EMITTERS
  // =========================================================================

  /**
   * Casts a kinetic spell from origin (ox, oy) towards target (tx, ty)
   */
  function castSpell(spellName, originX, originY, targetX, targetY) {
    const rawKey = normalizeSpellKey(spellName || fxState.activeSpell);
    const meta = SPELL_METADATA[rawKey] || SPELL_METADATA.fireball;
    const now = performance.now();

    // Prevent spam
    if (now - fxState.lastSpellCastTime < 180) return;
    fxState.lastSpellCastTime = now;

    const canvas = domEls.canvas || (window.VisionApp && window.VisionApp.els && window.VisionApp.els.gestureFxCanvas);
    const w = canvas ? canvas.width : 800;
    const h = canvas ? canvas.height : 520;

    const ox = originX !== undefined ? originX : w * 0.5;
    const oy = originY !== undefined ? originY : h * 0.8;
    const tx = targetX !== undefined ? targetX : w * 0.5 + (Math.random() - 0.5) * 140;
    const ty = targetY !== undefined ? targetY : h * 0.25 + (Math.random() - 0.5) * 100;

    const spellInstance = {
      type: rawKey,
      meta,
      x: ox,
      y: oy,
      originX: ox,
      originY: oy,
      targetX: tx,
      targetY: ty,
      progress: 0,
      color: meta.color,
      glowColor: meta.glowColor,
      createdAt: now,
      exploded: false
    };

    fxState.spells.push(spellInstance);
    fxState.mana = Math.max(0.05, fxState.mana - meta.cost);
    playSound(rawKey);

    logEvent(`Cast <strong>${meta.name}</strong> [Mana: ${Math.round(fxState.mana * 100)}%]`);

    // Initial cast burst
    spawnCastBurst(ox, oy, meta);

    // Sync to VisionApp if present
    if (window.VisionApp && window.VisionApp.state && window.VisionApp.state.gestureFx) {
      window.VisionApp.state.gestureFx.mana = fxState.mana;
    }
  }

  function spawnCastBurst(x, y, meta) {
    const count = meta.key === 'repulsor' ? 42 : 24;
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2 + Math.random() * 6;
      fxState.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1.0,
        decay: 0.02 + Math.random() * 0.03,
        color: Math.random() < 0.6 ? meta.color : meta.glowColor,
        size: 3 + Math.random() * 5,
        type: meta.key
      });
    }
  }

  function spawnExplosion(x, y, type) {
    const count = type === 'fireball' ? 52 : (type === 'repulsor' ? 64 : 36);
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2.5 + Math.random() * 9.5;
      let pColor = '#ffffff';
      if (type === 'fireball') {
        pColor = Math.random() < 0.4 ? '#ffffff' : (Math.random() < 0.7 ? '#ffe600' : '#ff3300');
      } else if (type === 'cryo') {
        pColor = Math.random() < 0.5 ? '#ffffff' : (Math.random() < 0.8 ? '#00f0ff' : '#a5f3fc');
      } else if (type === 'lightning') {
        pColor = Math.random() < 0.5 ? '#00f0ff' : '#c084fc';
      } else if (type === 'repulsor') {
        pColor = Math.random() < 0.5 ? '#ec4899' : '#9333ea';
      } else if (type === 'chrono_echoes') {
        pColor = Math.random() < 0.5 ? '#fbbf24' : '#38bdf8';
      }

      fxState.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: 1.0,
        decay: 0.02 + Math.random() * 0.03,
        color: pColor,
        size: 3.5 + Math.random() * 6.5,
        type: 'explosion'
      });
    }

    // Repulse active particles away from explosion center
    if (type === 'repulsor') {
      const radius = 260;
      fxState.particles.forEach(p => {
        const dx = p.x - x;
        const dy = p.y - y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > 1 && dist < radius) {
          const force = ((radius - dist) / radius) * 14;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
        }
      });
    }
  }

  // =========================================================================
  // POSTURE TRIGGERING: CHARGING, AIMING & TWO-HAND BURSTS
  // =========================================================================

  /**
   * Evaluates hand postures and triggers kinetic particle spellcasting:
   * 1. OPEN_PALM: Elemental charge orb gathers into palm center
   * 2. POINTING_INDEX: Holographic aim ray & lock-on reticle with auto-discharge
   * 3. TWO-HAND SPREAD/PUSH: Dual palm grav repulsor shockwave burst
   */
  function evaluateHandPostures(h0, h1, g0, g1, w, h, now) {
    if (!h0) {
      fxState.charging.active = false;
      fxState.aiming.active = false;
      return;
    }

    const tip0X = (h0[8] ? h0[8].x : 0.5) * w;
    const tip0Y = (h0[8] ? h0[8].y : 0.5) * h;
    const wrist0X = (h0[0] ? h0[0].x : 0.5) * w;
    const wrist0Y = (h0[0] ? h0[0].y : 0.8) * h;
    const palm0X = (h0[0] && h0[9]) ? ((h0[0].x + h0[9].x) * 0.5) * w : wrist0X;
    const palm0Y = (h0[0] && h0[9]) ? ((h0[0].y + h0[9].y) * 0.5) * h : wrist0Y;

    // -----------------------------------------------------------------------
    // 1. OPEN PALM CHARGING: Inward elemental gathering aura
    // -----------------------------------------------------------------------
    if (g0 === 'OPEN_PALM') {
      fxState.charging.active = true;
      fxState.charging.x = palm0X;
      fxState.charging.y = palm0Y;
      fxState.charging.progress = Math.min(1.0, fxState.charging.progress + 0.025 * fxState.bulletTimeFactor);

      // Mana accelerated recovery during charging
      fxState.mana = Math.min(1.0, fxState.mana + 0.003 * fxState.bulletTimeFactor);

      // Spawn inward-flowing gathering particles
      const activeMeta = SPELL_METADATA[fxState.activeSpell] || SPELL_METADATA.fireball;
      const gatherRadius = 45 + (1.0 - fxState.charging.progress) * 35;
      for (let i = 0; i < 3; i++) {
        const theta = Math.random() * Math.PI * 2;
        const px = palm0X + Math.cos(theta) * gatherRadius;
        const py = palm0Y + Math.sin(theta) * gatherRadius;
        fxState.particles.push({
          x: px,
          y: py,
          vx: (palm0X - px) * 0.12,
          vy: (palm0Y - py) * 0.12,
          life: 0.9,
          decay: 0.05,
          color: Math.random() < 0.6 ? activeMeta.color : activeMeta.glowColor,
          size: 2.5 + Math.random() * 3,
          type: 'charging'
        });
      }

      // Auto-cast when charged if pushed upwards or on periodic release
      if (fxState.charging.progress >= 1.0 && Math.random() < 0.08) {
        castSpell(fxState.activeSpell, palm0X, palm0Y, palm0X + (Math.random() - 0.5) * 80, palm0Y - 180);
        fxState.charging.progress = 0.3; // Reset partial
      }
    } else {
      // If was charging and transitioned away with charge > 0.6, unleash burst!
      if (fxState.charging.active && fxState.charging.progress > 0.6) {
        castSpell(fxState.activeSpell, fxState.charging.x, fxState.charging.y, fxState.charging.x, fxState.charging.y - 200);
      }
      fxState.charging.active = false;
      fxState.charging.progress = 0.0;
    }

    // -----------------------------------------------------------------------
    // 2. INDEX FINGER AIMING & CASTING: Targeting reticle & precision bolts
    // -----------------------------------------------------------------------
    if (g0 === 'POINTING_INDEX') {
      fxState.aiming.active = true;
      fxState.aiming.originX = tip0X;
      fxState.aiming.originY = tip0Y;

      // Calculate vector from joint 5 (Index MCP) to joint 8 (Index Tip)
      let dx = 0;
      let dy = -1;
      if (h0[5] && h0[8]) {
        dx = (h0[8].x - h0[5].x) * w;
        dy = (h0[8].y - h0[5].y) * h;
        const mag = Math.sqrt(dx * dx + dy * dy);
        if (mag > 0.001) {
          dx /= mag;
          dy /= mag;
        }
      }

      const rayDistance = 340;
      fxState.aiming.targetX = tip0X + dx * rayDistance;
      fxState.aiming.targetY = tip0Y + dy * rayDistance;
      fxState.aiming.angle = Math.atan2(dy, dx);

      // Periodic precision discharge while aiming
      if (now - fxState.aiming.lastCastTime > 320) {
        if (fxState.activeSpell === 'lightning') {
          castSpell('lightning', tip0X, tip0Y, fxState.aiming.targetX + (Math.random() - 0.5) * 40, fxState.aiming.targetY + (Math.random() - 0.5) * 40);
        } else if (fxState.activeSpell === 'fireball' && Math.random() < 0.45) {
          castSpell('fireball', tip0X, tip0Y, fxState.aiming.targetX, fxState.aiming.targetY);
        } else if (fxState.activeSpell === 'cryo' && Math.random() < 0.4) {
          castSpell('cryo', tip0X, tip0Y, fxState.aiming.targetX, fxState.aiming.targetY);
        }
        fxState.aiming.lastCastTime = now;
      }
    } else {
      fxState.aiming.active = false;
    }

    // -----------------------------------------------------------------------
    // 3. TWO-HAND SHOCKWAVE BURSTS: Dual open palms trigger grav repulsor
    // -----------------------------------------------------------------------
    if (h0 && h1 && (g0 === 'OPEN_PALM' || g0 === 'DETECTING') && (g1 === 'OPEN_PALM' || g1 === 'DETECTING')) {
      const tip1X = (h1[8] ? h1[8].x : 0.7) * w;
      const tip1Y = (h1[8] ? h1[8].y : 0.5) * h;
      const wrist1X = (h1[0] ? h1[0].x : 0.7) * w;
      const wrist1Y = (h1[0] ? h1[0].y : 0.8) * h;

      const midX = (wrist0X + wrist1X) * 0.5;
      const midY = (wrist0Y + wrist1Y) * 0.5;
      const handDist = Math.hypot(wrist1X - wrist0X, wrist1Y - wrist0Y);

      // If hands are within good shockwave distance and cooldown elapsed
      if (now - fxState.lastShockwaveTime > fxState.twoHandShockwave.cooldown) {
        if (g0 === 'OPEN_PALM' && g1 === 'OPEN_PALM' && handDist > 100) {
          castSpell('repulsor', midX, midY, midX, midY);
          fxState.lastShockwaveTime = now;
          logEvent(`🌌 <strong>Dual Hand Grav Shockwave Burst</strong> triggered!`);
        }
      }
    }

    // -----------------------------------------------------------------------
    // 4. CHRONO TIME ECHOES: Record spatial motion history
    // -----------------------------------------------------------------------
    if (fxState.activeSpell === 'chrono_echoes' || fxState.bulletTimeFactor < 0.6) {
      if (now % 3 === 0 && h0) {
        fxState.temporalEchoes.push({
          time: now,
          landmarks: h0.map(pt => ({ x: pt.x * w, y: pt.y * h })),
          alpha: 0.75,
          color: '#fbbf24'
        });
        if (fxState.temporalEchoes.length > 20) {
          fxState.temporalEchoes.shift();
        }
      }
    }
  }

  // =========================================================================
  // TOUCHLESS MACROPAD COLLISION DETECTION
  // =========================================================================
  function checkTouchlessMacropad(tipX, tipY, gesture, now, stageRect, w, h) {
    if (!domEls.macroButtons || !domEls.macroButtons.length || !stageRect) return;

    let isAnyHovered = false;

    domEls.macroButtons.forEach(btn => {
      const btnRect = btn.getBoundingClientRect();
      const bx1 = (btnRect.left - stageRect.left) * (w / stageRect.width);
      const by1 = (btnRect.top - stageRect.top) * (h / stageRect.height);
      const bx2 = (btnRect.right - stageRect.left) * (w / stageRect.width);
      const by2 = (btnRect.bottom - stageRect.top) * (h / stageRect.height);

      const isInside = (tipX >= bx1 && tipX <= bx2 && tipY >= by1 && tipY <= by2);

      if (isInside) {
        isAnyHovered = true;
        btn.classList.add('active-macro');

        // New button entered
        if (fxState.macropad.hoveredKey !== btn.dataset.macro) {
          fxState.macropad.hoveredKey = btn.dataset.macro;
          fxState.macropad.hoverStartTime = now;
          fxState.macropad.dwellProgress = 0.0;
          playSound('hover');
        } else {
          // Accumulate dwell progress
          const elapsed = now - fxState.macropad.hoverStartTime;
          fxState.macropad.dwellProgress = Math.min(1.0, elapsed / fxState.macropad.dwellDuration);
        }

        // Trigger condition: Pinch gesture OR Dwell time completed
        const isPinchTrigger = (gesture === 'PINCH');
        const isDwellTrigger = (fxState.macropad.dwellProgress >= 1.0);

        if (isPinchTrigger || isDwellTrigger) {
          if (now - fxState.macropad.lastTriggerTime > 400) {
            executeMacroAction(btn.dataset.macro);
            fxState.macropad.lastTriggerTime = now;
            fxState.macropad.dwellProgress = 0.0; // Reset after trigger
            fxState.macropad.hoverStartTime = now;
          }
        }
      } else {
        btn.classList.remove('active-macro');
      }
    });

    if (!isAnyHovered) {
      fxState.macropad.hoveredKey = null;
      fxState.macropad.dwellProgress = 0.0;
    }
  }

  /**
   * Executes a touchless macro action (Bullet Time, Spell select, Snapshot, Reset)
   */
  function executeMacroAction(macroKey) {
    const now = performance.now();
    if (now - fxState.lastMacroTriggerTime < 280) return;
    fxState.lastMacroTriggerTime = now;
    playSound('macro');

    switch (macroKey) {
      case 'snapshot':
        captureCanvasSnapshot();
        logEvent(`Macro: 📸 <strong>Captured High-Res Canvas Snapshot</strong>`);
        showNotification('Snapshot exported from Gesture Studio');
        break;

      case 'next_filter':
        if (window.VisionApp && typeof window.VisionApp.cycleFilter === 'function') {
          window.VisionApp.cycleFilter(1);
          logEvent(`Macro: 🎨 Cycled Shader Filter`);
        }
        break;

      case 'fireball':
        selectSpell('fireball');
        castSpell('fireball');
        break;

      case 'ice_freeze':
      case 'cryo':
        selectSpell('cryo');
        castSpell('cryo');
        break;

      case 'tesla_storm':
      case 'lightning':
        selectSpell('lightning');
        castSpell('lightning');
        break;

      case 'bullet_time':
        fxState.bulletTimeFactor = fxState.bulletTimeFactor < 0.6 ? 1.0 : 0.25;
        if (window.VisionApp && window.VisionApp.state && window.VisionApp.state.gestureFx) {
          window.VisionApp.state.gestureFx.bulletTimeFactor = fxState.bulletTimeFactor;
        }
        const btStatus = fxState.bulletTimeFactor < 0.6 ? 'Engaged (0.25x)' : 'Disengaged (1.0x)';
        playSound('chrono_echoes');
        logEvent(`Macro: ⏱️ <strong>Chrono Bullet Time</strong> ${btStatus}`);
        showNotification(`Bullet Time ${btStatus}`);
        break;

      case 'toggle_sfx':
        toggleDjAudio();
        logEvent(`Macro: 🔊 Toggled DJ Synthesizer Audio (${fxState.djAudio.enabled ? 'ON' : 'OFF'})`);
        break;

      case 'reset_all':
      case 'clear_stage':
        clearStage();
        logEvent(`Macro: 🔄 <strong>Reset Stage & Recharged Mana</strong>`);
        showNotification('Gesture Stage & Mana Reset');
        break;

      default:
        logEvent(`Macro: Unknown action [${macroKey}]`);
        break;
    }
  }

  function selectSpell(spellKey) {
    const normalized = normalizeSpellKey(spellKey);
    const meta = SPELL_METADATA[normalized];
    if (!meta) return;

    fxState.activeSpell = normalized;
    if (window.VisionApp && window.VisionApp.state && window.VisionApp.state.gestureFx) {
      window.VisionApp.state.gestureFx.activeSpell = normalized;
    }

    // Update UI chips
    if (domEls.spellChips) {
      domEls.spellChips.forEach(chip => {
        chip.classList.toggle('active-chip', chip.dataset.spell === normalized);
      });
    }
    if (domEls.spellName) {
      domEls.spellName.textContent = meta.name;
    }
    if (domEls.spellBadge) {
      domEls.spellBadge.style.borderColor = meta.color;
    }
  }

  function clearStage() {
    fxState.spells = [];
    fxState.particles = [];
    fxState.temporalEchoes = [];
    fxState.mana = 1.0;
    fxState.bulletTimeFactor = 1.0;
    fxState.charging.progress = 0.0;
    fxState.charging.active = false;

    if (window.VisionApp && window.VisionApp.state && window.VisionApp.state.gestureFx) {
      window.VisionApp.state.gestureFx.spells = [];
      window.VisionApp.state.gestureFx.particles = [];
      window.VisionApp.state.gestureFx.mana = 1.0;
      window.VisionApp.state.gestureFx.bulletTimeFactor = 1.0;
    }
  }

  function captureCanvasSnapshot() {
    const canvas = domEls.canvas || (window.VisionApp && window.VisionApp.els && window.VisionApp.els.gestureFxCanvas);
    if (!canvas) return;
    try {
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `gesturefx_snapshot_${Date.now()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      console.warn('[GestureFX] Snapshot export failed:', e);
    }
  }

  // =========================================================================
  // STAGE SCENE RENDERING ENGINE
  // =========================================================================

  /**
   * Main render loop for tab-gesturefx
   * Called on every animation frame when tab-gesturefx is active.
   */
  function renderScene(ctx, w, h, now) {
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);

    const dt = (16 / 1000) * fxState.bulletTimeFactor;

    // Passive mana recharge
    fxState.mana = Math.min(1.0, fxState.mana + 0.0018 * fxState.bulletTimeFactor);
    if (domEls.powerText) {
      const manaPct = Math.round(fxState.mana * 100);
      domEls.powerText.textContent = `Mana: ${manaPct}% • ${manaPct > 20 ? 'Cast Ready' : 'Recharging...'}`;
    }

    // -----------------------------------------------------------------------
    // 1. BACKDROP: Mirrored Webcam Feed or Cyber Matrix Spatial Grid
    // -----------------------------------------------------------------------
    const appState = (window.VisionApp && window.VisionApp.state) || {};
    const webcamVideo = domEls.webcamVideo || (window.VisionApp && window.VisionApp.els && window.VisionApp.els.webcamVideo);

    if (appState.isWebcamActive && webcamVideo && webcamVideo.readyState >= 2) {
      ctx.save();
      ctx.scale(-1, 1);
      ctx.drawImage(webcamVideo, -w, 0, w, h);
      ctx.restore();
    } else {
      // Cosmic Cyber Matrix gradient
      const bgGrad = ctx.createRadialGradient(w * 0.5, h * 0.5, 40, w * 0.5, h * 0.5, Math.max(w, h));
      bgGrad.addColorStop(0, '#0f172a');
      bgGrad.addColorStop(0.5, '#090d16');
      bgGrad.addColorStop(1, '#020408');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Neon perspective cyber grid floor
      ctx.save();
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.07)';
      ctx.lineWidth = 1;
      for (let x = 0; x <= w; x += 48) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 0; y <= h; y += 48) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }
      ctx.restore();
    }

    // -----------------------------------------------------------------------
    // 2. HAND POSITIONS, DJ FILTER & TOUCHLESS MACROPAD COLLISION
    // -----------------------------------------------------------------------
    const h0 = (appState.multiHandLandmarks && appState.multiHandLandmarks[0]) || (appState.landmarks && appState.landmarks.length ? appState.landmarks : null);
    const h1 = (appState.multiHandLandmarks && appState.multiHandLandmarks[1]) || null;
    const g0 = (appState.handGestures && appState.handGestures[0]) || appState.activeGesture || 'DETECTING';
    const g1 = (appState.handGestures && appState.handGestures[1]) || 'DETECTING';

    // Real-time DJ Low-Pass filter sweep tracking
    if (h0) {
      updateDjFilter(h0, h1);
    }

    // Touchless Macropad Check
    if (h0 && domEls.stage) {
      const tip0X = (h0[8] ? h0[8].x : 0.5) * w;
      const tip0Y = (h0[8] ? h0[8].y : 0.5) * h;
      const stageRect = domEls.stage.getBoundingClientRect();
      checkTouchlessMacropad(tip0X, tip0Y, g0, now, stageRect, w, h);
    }

    // Evaluate Hand Postures for Automated Kinetic Casting
    evaluateHandPostures(h0, h1, g0, g1, w, h, now);

    // -----------------------------------------------------------------------
    // 3. RENDER TEMPORAL CHRONO ECHOES (Ghost Wireframes & Timelines)
    // -----------------------------------------------------------------------
    if (fxState.temporalEchoes.length > 0) {
      ctx.save();
      const boneConnections = (window.VisionApp && window.VisionApp.BONE_CONNECTIONS) || [
        [0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8],
        [5, 9], [9, 10], [10, 11], [11, 12], [9, 13], [13, 14], [14, 15],
        [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]
      ];

      fxState.temporalEchoes.forEach((echo, idx) => {
        const ratio = (idx + 1) / fxState.temporalEchoes.length;
        ctx.strokeStyle = `rgba(251, 191, 36, ${ratio * 0.35})`;
        ctx.lineWidth = 1.5;

        boneConnections.forEach(([i, j]) => {
          if (echo.landmarks[i] && echo.landmarks[j]) {
            ctx.beginPath();
            ctx.moveTo(echo.landmarks[i].x, echo.landmarks[i].y);
            ctx.lineTo(echo.landmarks[j].x, echo.landmarks[j].y);
            ctx.stroke();
          }
        });
      });
      ctx.restore();
    }

    // -----------------------------------------------------------------------
    // 4. RENDER CHARGING ELEMENTAL ORB (OPEN_PALM POSTURE)
    // -----------------------------------------------------------------------
    if (fxState.charging.active) {
      ctx.save();
      const cx = fxState.charging.x;
      const cy = fxState.charging.y;
      const prog = fxState.charging.progress;
      const activeMeta = SPELL_METADATA[fxState.activeSpell] || SPELL_METADATA.fireball;

      // Glowing pulsating charge orb
      const orbRadius = 14 + prog * 24 + Math.sin(now * 0.015) * 4;
      const orbGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, orbRadius);
      orbGrad.addColorStop(0, '#ffffff');
      orbGrad.addColorStop(0.3, activeMeta.glowColor);
      orbGrad.addColorStop(0.8, activeMeta.color);
      orbGrad.addColorStop(1, 'rgba(0,0,0,0)');

      ctx.fillStyle = orbGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, orbRadius, 0, Math.PI * 2);
      ctx.fill();

      // Rotating runic charge ring
      ctx.strokeStyle = activeMeta.glowColor;
      ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.arc(cx, cy, orbRadius + 8, now * 0.003, now * 0.003 + Math.PI * 2 * prog);
      ctx.stroke();

      ctx.restore();
    }

    // -----------------------------------------------------------------------
    // 5. RENDER HOLOGRAPHIC AIMING RAY & RETICLE (POINTING_INDEX POSTURE)
    // -----------------------------------------------------------------------
    if (fxState.aiming.active) {
      ctx.save();
      const ox = fxState.aiming.originX;
      const oy = fxState.aiming.originY;
      const tx = fxState.aiming.targetX;
      const ty = fxState.aiming.targetY;
      const activeMeta = SPELL_METADATA[fxState.activeSpell] || SPELL_METADATA.lightning;

      // Laser Targeting Beam
      ctx.strokeStyle = activeMeta.color;
      ctx.lineWidth = 1.8;
      ctx.setLineDash([8, 4]);
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(tx, ty);
      ctx.stroke();

      // Lock-On Aim Reticle
      ctx.setLineDash([]);
      ctx.strokeStyle = activeMeta.glowColor;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(tx, ty, 16, 0, Math.PI * 2);
      ctx.stroke();

      // Crosshairs
      ctx.beginPath();
      ctx.moveTo(tx - 22, ty); ctx.lineTo(tx - 10, ty);
      ctx.moveTo(tx + 10, ty); ctx.lineTo(tx + 22, ty);
      ctx.moveTo(tx, ty - 22); ctx.lineTo(tx, ty - 10);
      ctx.moveTo(tx, ty + 10); ctx.lineTo(tx, ty + 22);
      ctx.stroke();

      // Aim Target Coordinates HUD Readout
      ctx.fillStyle = activeMeta.glowColor;
      ctx.font = '10px monospace';
      ctx.fillText(`AIM LOCK: [${Math.round(tx)}, ${Math.round(ty)}]`, tx + 20, ty - 12);

      ctx.restore();
    }

    // -----------------------------------------------------------------------
    // 6. RENDER ACTIVE KINETIC SPELLS
    // -----------------------------------------------------------------------
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';

    fxState.spells = fxState.spells.filter(spell => {
      spell.progress += 0.038 * fxState.bulletTimeFactor;

      // FIREBALL
      if (spell.type === 'fireball') {
        const curX = spell.originX + (spell.targetX - spell.originX) * Math.min(1.0, spell.progress);
        const curY = spell.originY + (spell.targetY - spell.originY) * Math.min(1.0, spell.progress) - Math.sin(spell.progress * Math.PI) * 44;

        const rad = ctx.createRadialGradient(curX, curY, 2, curX, curY, 30);
        rad.addColorStop(0, '#ffffff');
        rad.addColorStop(0.25, '#ffea00');
        rad.addColorStop(0.65, '#ff5500');
        rad.addColorStop(1, 'rgba(255, 30, 0, 0)');
        ctx.fillStyle = rad;
        ctx.beginPath();
        ctx.arc(curX, curY, 30, 0, Math.PI * 2);
        ctx.fill();

        // Trail smoke/spark particles
        for (let i = 0; i < 4; i++) {
          fxState.particles.push({
            x: curX + (Math.random() - 0.5) * 14,
            y: curY + (Math.random() - 0.5) * 14,
            vx: (Math.random() - 0.5) * 3 - (spell.targetX - spell.originX) * 0.015,
            vy: (Math.random() - 0.5) * 3 + 2,
            life: 1.0,
            decay: 0.04 + Math.random() * 0.04,
            color: Math.random() < 0.5 ? '#ffea00' : '#ff3300',
            size: 4 + Math.random() * 6,
            type: 'fireball'
          });
        }

        // Explosion on impact
        if (spell.progress >= 1.0 && !spell.exploded) {
          spell.exploded = true;
          spawnExplosion(curX, curY, 'fireball');
        }
      }

      // CRYO FROST
      else if (spell.type === 'cryo') {
        const curR = spell.progress * 240;
        ctx.save();
        ctx.strokeStyle = '#00f0ff';
        ctx.lineWidth = 3.5 * (1.0 - spell.progress);
        ctx.shadowColor = '#00f0ff';
        ctx.shadowBlur = 18;
        ctx.beginPath();
        ctx.arc(spell.originX, spell.originY, curR, 0, Math.PI * 2);
        ctx.stroke();

        // 6-Fold Snowflake Crystal Fractal Spines
        for (let a = 0; a < 6; a++) {
          const theta = (a / 6) * Math.PI * 2 + now * 0.0012;
          const ex = spell.originX + Math.cos(theta) * curR;
          const ey = spell.originY + Math.sin(theta) * curR;
          ctx.beginPath();
          ctx.moveTo(spell.originX, spell.originY);
          ctx.lineTo(ex, ey);
          ctx.stroke();

          // Sub-spines
          const subR = curR * 0.6;
          const mx = spell.originX + Math.cos(theta) * subR;
          const my = spell.originY + Math.sin(theta) * subR;
          ctx.beginPath();
          ctx.moveTo(mx, my);
          ctx.lineTo(mx + Math.cos(theta + 0.6) * (curR * 0.25), my + Math.sin(theta + 0.6) * (curR * 0.25));
          ctx.moveTo(mx, my);
          ctx.lineTo(mx + Math.cos(theta - 0.6) * (curR * 0.25), my + Math.sin(theta - 0.6) * (curR * 0.25));
          ctx.stroke();
        }
        ctx.restore();

        // Ice mist particles
        if (Math.random() < 0.6) {
          const ang = Math.random() * Math.PI * 2;
          fxState.particles.push({
            x: spell.originX + Math.cos(ang) * curR,
            y: spell.originY + Math.sin(ang) * curR,
            vx: Math.cos(ang) * 1.6,
            vy: Math.sin(ang) * 1.6,
            life: 1.0,
            decay: 0.032,
            color: '#e0f7fa',
            size: 3 + Math.random() * 4,
            type: 'cryo'
          });
        }
      }

      // TESLA ARC LIGHTNING
      else if (spell.type === 'lightning') {
        ctx.save();
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.95)';
        ctx.lineWidth = 4.2 * (1.0 - spell.progress);
        ctx.shadowColor = '#a855f7';
        ctx.shadowBlur = 22;

        let lx = spell.originX;
        let ly = spell.originY;
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        const segments = 14;
        for (let s = 1; s <= segments; s++) {
          const t = s / segments;
          const nlx = spell.originX + (spell.targetX - spell.originX) * t + (Math.random() - 0.5) * 55;
          const nly = spell.originY + (spell.targetY - spell.originY) * t + (Math.random() - 0.5) * 55;
          ctx.lineTo(nlx, nly);

          // Secondary branching fork arc
          if (s % 4 === 0 && Math.random() < 0.6) {
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(nlx, nly);
            ctx.lineTo(nlx + (Math.random() - 0.5) * 60, nly + (Math.random() - 0.5) * 60);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(nlx, nly);
          }

          lx = nlx;
          ly = nly;
        }
        ctx.stroke();

        // White hot inner core
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.8 * (1.0 - spell.progress);
        ctx.stroke();
        ctx.restore();
      }

      // GRAV REPULSOR
      else if (spell.type === 'repulsor') {
        const r1 = spell.progress * 280;
        ctx.save();
        ctx.strokeStyle = `rgba(168, 85, 247, ${1.0 - spell.progress})`;
        ctx.lineWidth = 5.5 * (1.0 - spell.progress);
        ctx.shadowColor = '#9333ea';
        ctx.shadowBlur = 26;
        ctx.beginPath();
        ctx.arc(spell.originX, spell.originY, r1, 0, Math.PI * 2);
        ctx.stroke();

        ctx.strokeStyle = `rgba(236, 72, 153, ${1.0 - spell.progress})`;
        ctx.lineWidth = 2.8;
        ctx.beginPath();
        ctx.arc(spell.originX, spell.originY, r1 * 0.68, 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();

        // Repulse particles along the shockwave
        if (spell.progress > 0.05 && spell.progress < 0.8) {
          fxState.particles.forEach(p => {
            const dx = p.x - spell.originX;
            const dy = p.y - spell.originY;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (Math.abs(dist - r1) < 35 && dist > 1) {
              p.vx += (dx / dist) * 6.5;
              p.vy += (dy / dist) * 6.5;
            }
          });
        }
      }

      // CHRONO TIME ECHOES
      else if (spell.type === 'chrono_echoes') {
        const rEcho = spell.progress * 220;
        ctx.save();
        ctx.strokeStyle = `rgba(251, 191, 36, ${1.0 - spell.progress})`;
        ctx.lineWidth = 3 * (1.0 - spell.progress);
        ctx.shadowColor = '#f59e0b';
        ctx.shadowBlur = 20;
        ctx.beginPath();
        ctx.arc(spell.originX, spell.originY, rEcho, 0, Math.PI * 2);
        ctx.stroke();

        // Clock ticks radiating outwards
        for (let i = 0; i < 12; i++) {
          const theta = (i / 12) * Math.PI * 2;
          const x1 = spell.originX + Math.cos(theta) * (rEcho - 12);
          const y1 = spell.originY + Math.sin(theta) * (rEcho - 12);
          const x2 = spell.originX + Math.cos(theta) * rEcho;
          const y2 = spell.originY + Math.sin(theta) * rEcho;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
        ctx.restore();
      }

      return spell.progress < 1.0;
    });

    // -----------------------------------------------------------------------
    // 7. PARTICLES UPDATE & DRAW
    // -----------------------------------------------------------------------
    fxState.particles = fxState.particles.filter(p => {
      p.life -= p.decay * fxState.bulletTimeFactor;
      p.x += p.vx * fxState.bulletTimeFactor;
      p.y += p.vy * fxState.bulletTimeFactor;

      if (p.type === 'fireball' || p.type === 'explosion') {
        p.vy -= 0.05 * fxState.bulletTimeFactor; // Thermal buoyancy
      } else if (p.type === 'ambient') {
        p.vx += (Math.random() - 0.5) * 0.2;
        p.vy += (Math.random() - 0.5) * 0.2;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
        if (p.life <= 0) p.life = 1.0;
      }

      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, p.life);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
      ctx.fill();

      return p.life > 0;
    });

    ctx.globalAlpha = 1.0;
    ctx.globalCompositeOperation = 'source-over';
    ctx.restore();

    // -----------------------------------------------------------------------
    // 8. RENDER SKELETONS & ELEMENTAL HAND AURAS
    // -----------------------------------------------------------------------
    if (appState.showSkeleton !== false && window.VisionApp && typeof window.VisionApp.renderMultiHandSkeletons === 'function') {
      window.VisionApp.renderMultiHandSkeletons(ctx, w, h);
    }

    // -----------------------------------------------------------------------
    // 9. RENDER DJ FREQUENCY ANALYZER SPECTRUM HUD
    // -----------------------------------------------------------------------
    drawDjVisualizerOverlay(ctx, w, h);

    // -----------------------------------------------------------------------
    // 10. RENDER MACROPAD DWELL PROGRESS RING (IF DWELLING)
    // -----------------------------------------------------------------------
    if (fxState.macropad.hoveredKey && fxState.macropad.dwellProgress > 0 && h0) {
      const tip0X = (h0[8] ? h0[8].x : 0.5) * w;
      const tip0Y = (h0[8] ? h0[8].y : 0.5) * h;
      ctx.save();
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(tip0X, tip0Y, 18, -Math.PI * 0.5, -Math.PI * 0.5 + Math.PI * 2 * fxState.macropad.dwellProgress);
      ctx.stroke();

      ctx.fillStyle = 'rgba(0, 240, 255, 0.25)';
      ctx.beginPath();
      ctx.arc(tip0X, tip0Y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // -----------------------------------------------------------------------
    // 11. BULLET TIME CHRONO DILATION HUD OVERLAY
    // -----------------------------------------------------------------------
    if (fxState.bulletTimeFactor < 0.6) {
      ctx.save();
      ctx.strokeStyle = 'rgba(34, 197, 94, 0.45)';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 6]);
      ctx.strokeRect(12, 12, w - 24, h - 24);
      ctx.fillStyle = 'rgba(34, 197, 94, 0.9)';
      ctx.font = '11px monospace';
      ctx.fillText(`⏱️ CHRONO DILATION: ${(fxState.bulletTimeFactor).toFixed(2)}x [MATRIX BULLET TIME ACTIVE]`, 24, 34);
      ctx.restore();
    }
  }

  /**
   * Renders the live DJ Frequency Analyzer Spectrum Bars on the stage
   */
  function drawDjVisualizerOverlay(ctx, w, h) {
    if (!fxState.djAudio.analyser || !fxState.djAudio.freqData) return;
    try {
      fxState.djAudio.analyser.getByteFrequencyData(fxState.djAudio.freqData);

      const barWidth = 3;
      const barGap = 2;
      const numBars = 32;
      const totalWidth = numBars * (barWidth + barGap);
      const startX = 16;
      const startY = h - 20;

      ctx.save();
      ctx.fillStyle = 'rgba(11, 15, 20, 0.65)';
      ctx.fillRect(startX - 6, startY - 42, totalWidth + 12, 48);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.strokeRect(startX - 6, startY - 42, totalWidth + 12, 48);

      for (let i = 0; i < numBars; i++) {
        const val = fxState.djAudio.freqData[i] || 0;
        const barHeight = Math.max(2, (val / 255) * 36);
        const bx = startX + i * (barWidth + barGap);
        const by = startY - barHeight;

        // Gradient color from cyan to orange/purple based on frequency
        const hue = 180 + (i / numBars) * 120;
        ctx.fillStyle = `hsl(${hue}, 100%, 60%)`;
        ctx.fillRect(bx, by, barWidth, barHeight);
      }

      // DJ Filter Cutoff Marker line
      const cutoffPct = (fxState.djAudio.cutoff - 200) / 11800;
      const markerX = startX + cutoffPct * totalWidth;
      ctx.strokeStyle = '#f9ab00';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(markerX, startY - 42);
      ctx.lineTo(markerX, startY);
      ctx.stroke();

      ctx.fillStyle = '#a8c7fa';
      ctx.font = '8px monospace';
      ctx.fillText(`LPF: ${fxState.djAudio.cutoff}Hz | Q: ${fxState.djAudio.resonance}`, startX, startY - 46);

      ctx.restore();
    } catch (e) {}
  }

  // =========================================================================
  // INITIALIZATION & EVENT WIRING
  // =========================================================================
  function init() {
    if (fxState.initialized) return;
    queryDomElements();

    // Pre-populate fluid wave ambient particles
    for (let i = 0; i < 140; i++) {
      fxState.particles.push({
        x: Math.random() * 800,
        y: Math.random() * 520,
        vx: (Math.random() - 0.5) * 1.8,
        vy: (Math.random() - 0.5) * 1.8,
        life: 1.0,
        decay: 0.003 + Math.random() * 0.004,
        color: '#38bdf8',
        size: 2.2 + Math.random() * 2.8,
        type: 'ambient'
      });
    }

    // Bind Spell Selector Chips
    if (domEls.spellChips) {
      domEls.spellChips.forEach(chip => {
        chip.addEventListener('click', () => {
          const spellKey = chip.dataset.spell;
          selectSpell(spellKey);
          playSound('click');
          logEvent(`Selected spell: <strong>${SPELL_METADATA[normalizeSpellKey(spellKey)]?.name || spellKey}</strong>`);
        });
      });
    }

    // Bind Touchless Macro Buttons (Mouse / Touch click fallback)
    if (domEls.macroButtons) {
      domEls.macroButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          executeMacroAction(btn.dataset.macro);
        });
      });
    }

    // Bind Cast Trigger Button
    if (domEls.btnCastTrigger) {
      domEls.btnCastTrigger.addEventListener('click', () => {
        castSpell(fxState.activeSpell);
      });
    }

    // Bind Clear Button
    if (domEls.btnClearStage) {
      domEls.btnClearStage.addEventListener('click', () => {
        clearStage();
        logEvent('Cleared all active spells and particle waves.');
        showNotification('Cleared Gesture FX Stage');
      });
    }

    // Bind Canvas Click / Tap fallback
    if (domEls.canvas) {
      domEls.canvas.addEventListener('mousedown', (e) => {
        const rect = domEls.canvas.getBoundingClientRect();
        const px = (e.clientX - rect.left) * (domEls.canvas.width / rect.width);
        const py = (e.clientY - rect.top) * (domEls.canvas.height / rect.height);
        castSpell(fxState.activeSpell, domEls.canvas.width * 0.5, domEls.canvas.height * 0.9, px, py);
      });
    }

    // Bind DJ Meter Click to toggle DJ Audio
    if (domEls.djMeterBar && domEls.djMeterBar.parentElement) {
      domEls.djMeterBar.parentElement.style.cursor = 'pointer';
      domEls.djMeterBar.parentElement.title = 'Click to toggle live DJ Audio Synthesizer';
      domEls.djMeterBar.parentElement.addEventListener('click', () => {
        toggleDjAudio();
      });
    }

    fxState.initialized = true;
    logEvent(`[Ready] ⚡ <strong>Kinetic Gesture FX Studio & DJ Synthesizer</strong> initialized.`);
  }

  // =========================================================================
  // PUBLIC TOOL INTERFACE
  // =========================================================================
  const gestureFxTool = {
    id: 'tool-gesturefx',
    name: 'Gesture FX Studio & Touchless Macropad',
    version: '1.0.0',
    init,
    renderScene,
    castSpell,
    executeMacroAction,
    selectSpell,
    clearStage,
    updateDjFilter,
    toggleDjAudio,
    startDjAudio: initDjAudioSynthesizer,
    stopDjAudio: stopDjAudioSynthesizer,
    getState: () => fxState,
    getSpellMetadata: () => SPELL_METADATA
  };

  // Expose globally on window for HTML button onclicks
  window.castSpell = castSpell;
  window.executeMacroAction = executeMacroAction;
  window.selectSpell = selectSpell;
  window.VisionGestureFx = gestureFxTool;

  // Attach to window.VisionApp if available
  function attachToVisionApp() {
    if (window.VisionApp) {
      if (!window.VisionApp.tools) {
        window.VisionApp.tools = {};
      }
      window.VisionApp.tools.gestureFx = gestureFxTool;
      window.VisionApp.tools['gesturefx'] = gestureFxTool;
      window.VisionApp.tools['tool-gesturefx'] = gestureFxTool;

      // Sync state if already exists
      if (window.VisionApp.state && window.VisionApp.state.gestureFx) {
        window.VisionApp.state.gestureFx.toolInstance = gestureFxTool;
      }
    }
  }

  // Attempt attachment immediately
  attachToVisionApp();

  // Listen for DOM load or script completion
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      attachToVisionApp();
      init();
    });
  } else {
    setTimeout(() => {
      attachToVisionApp();
      init();
    }, 0);
  }

})(typeof window !== 'undefined' ? window : this);
