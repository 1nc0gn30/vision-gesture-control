/**
 * Vision Studio - Spatial Audio & Hip-Hop Loop Studio Engine
 * tool-spatial-audio.js
 *
 * Provides a 41-sound spatial synthesizer and loop workstation:
 * - 8 Continuous Hip-Hop, Lo-Fi, Trap, and Drill Beat Loops (BPM synced metronome)
 * - 12 Hip-Hop Synth & Bass Instruments (808 Sub, G-Funk Lead, Cowbell, Rhodes, Brass, Acid 303)
 * - 12 Expressive Vocal Chops & Turntable Scratches (Formant synthesized "Yeah!", "Yo!", "Check It!", "Drop That!")
 * - 9 Sacred Solfeggio Theremin Tones (174Hz to 963Hz)
 * - Spatial Hand Position modulation (Right Hand X=Pitch/Scale, Y=Filter Cutoff; Left Hand Y=Volume, X=Stereo Pan)
 * - Gesture Triggers: Peace=Vocal Chop, Rock=808 Bass, ThumbsUp=Scratch, ThumbsDown=Sub Drop,
 *                     Shaka=Lo-Fi Rhodes, Pinch=Trap Hat Roll, Fist=Mute/Choke, Palm=Sustain
 * - Zero cross-tool state carryover.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    const exports = factory();
    if (root.VisionApp) {
      if (!root.VisionApp.tools) root.VisionApp.tools = {};
      root.VisionApp.tools.spatialAudio = exports;
    }
    root.SpatialAudioTool = exports;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ── SOUND LIBRARY PRESETS (41 TOTAL SOUNDS) ──────────────────────────────────

  const LOOPS = [
    {
      id: 'loop_boombap',
      name: 'Boom-Bap 90s NYC',
      category: 'loop',
      icon: '🥁',
      bpm: 92,
      bars: 2,
      desc: 'Dusty vinyl kick, punchy snare, swung hi-hats',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 1, 0,  0, 1, 0, 0,  0, 0, 0, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0],
        perc:  [0, 0, 0, 1,  0, 0, 0, 0,  0, 0, 0, 1,  0, 0, 1, 0]
      }
    },
    {
      id: 'loop_trap808',
      name: 'Atlanta 808 Trap',
      category: 'loop',
      icon: '🔥',
      bpm: 140,
      bars: 2,
      desc: 'Rolling 808 sub, rapid triplet hats, crisp clap',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 0, 0,  0, 0, 1, 0,  0, 0, 0, 0],
        sub:   [1, 0, 0, 0,  0, 0, 0, 0,  0, 0, 1, 0,  0, 0, 1, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1],
        openHat: [0, 0, 1, 0, 0, 0, 1, 0,  0, 0, 1, 0,  0, 0, 1, 0]
      }
    },
    {
      id: 'loop_lofi',
      name: 'Lo-Fi Chillhop Coffee',
      category: 'loop',
      icon: '☕',
      bpm: 84,
      bars: 2,
      desc: 'Muted warm kick, brushed snare, vinyl flutter',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 0, 0,  0, 1, 0, 0,  0, 0, 0, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [1, 0, 1, 0,  0, 1, 0, 1,  1, 0, 1, 0,  0, 1, 0, 1],
        chord: [1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0]
      }
    },
    {
      id: 'loop_phonk',
      name: 'Memphis Phonk Drift',
      category: 'loop',
      icon: '🏎️',
      bpm: 132,
      bars: 2,
      desc: 'Distorted 808 cowbell drive, gritty tape saturation',
      pattern: {
        kick:    [1, 0, 0, 0,  1, 0, 0, 0,  1, 0, 0, 0,  1, 0, 0, 0],
        snare:   [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        cowbell: [1, 0, 1, 0,  0, 1, 0, 1,  1, 1, 0, 1,  0, 1, 1, 0],
        hat:     [1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1,  1, 1, 1, 1]
      }
    },
    {
      id: 'loop_gfunk',
      name: 'West Coast G-Funk',
      category: 'loop',
      icon: '🌴',
      bpm: 96,
      bars: 2,
      desc: 'Laid back bounce, finger snaps, G-funk sine glide',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 1, 0,  0, 0, 1, 0,  0, 0, 0, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0,  1, 0, 1, 0],
        perc:  [0, 0, 0, 0,  1, 0, 0, 1,  0, 0, 0, 0,  1, 0, 1, 0]
      }
    },
    {
      id: 'loop_drill',
      name: 'UK Drill Stutter',
      category: 'loop',
      icon: '⚔️',
      bpm: 144,
      bars: 2,
      desc: 'Syncopated off-grid sliding sub, delayed ghost claps',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 0, 1,  0, 0, 1, 0,  0, 0, 0, 0],
        snare: [0, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 1, 0],
        hat:   [1, 0, 1, 1,  0, 1, 1, 0,  1, 1, 0, 1,  1, 0, 1, 1]
      }
    },
    {
      id: 'loop_neosoul',
      name: 'Neo-Soul Dilla Swing',
      category: 'loop',
      icon: '✨',
      bpm: 88,
      bars: 2,
      desc: 'Humanized unquantized pocket, organic rimshots',
      pattern: {
        kick:  [1, 0, 0, 0,  0, 0, 0, 1,  0, 1, 0, 0,  0, 0, 1, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [1, 0, 1, 1,  1, 0, 1, 0,  1, 0, 1, 1,  1, 0, 1, 0]
      }
    },
    {
      id: 'loop_darksynth',
      name: 'Cyber Darksynth Drive',
      category: 'loop',
      icon: '⚡',
      bpm: 118,
      bars: 2,
      desc: 'Four-on-the-floor synthwave bass pulse and electro snare',
      pattern: {
        kick:  [1, 0, 0, 0,  1, 0, 0, 0,  1, 0, 0, 0,  1, 0, 0, 0],
        snare: [0, 0, 0, 0,  1, 0, 0, 0,  0, 0, 0, 0,  1, 0, 0, 0],
        hat:   [0, 0, 1, 0,  0, 0, 1, 0,  0, 0, 1, 0,  0, 0, 1, 0]
      }
    }
  ];

  const SYNTHS = [
    { id: 'synth_808slide', name: 'Deep 808 Sub Slide', icon: '🔊', baseFreq: 46.25, type: 'sub' },
    { id: 'synth_gfunk', name: 'G-Funk Saw Whistle', icon: '🪈', baseFreq: 1174.66, type: 'lead' },
    { id: 'synth_cowbell', name: 'Memphis Cowbell 808', icon: '🔔', baseFreq: 800, type: 'perc' },
    { id: 'synth_rhodes', name: 'Lo-Fi Rhodes Pad', icon: '🎹', baseFreq: 261.63, type: 'chord' },
    { id: 'synth_brass', name: 'Detroit Brass Horns', icon: '🎺', baseFreq: 130.81, type: 'brass' },
    { id: 'synth_bell', name: 'Pluck Bell Melodic', icon: '💎', baseFreq: 587.33, type: 'pluck' },
    { id: 'synth_303', name: 'Acid 303 Resonant Slide', icon: '🧬', baseFreq: 65.41, type: 'acid' },
    { id: 'synth_cloudpad', name: 'Ambient Cloud Pad', icon: '☁️', baseFreq: 220.00, type: 'pad' },
    { id: 'synth_pentatonic', name: 'Minor Pentatonic Chord', icon: '🎼', baseFreq: 196.00, type: 'chord' },
    { id: 'synth_slapbass', name: 'Slap Funk Bass', icon: '🎸', baseFreq: 82.41, type: 'bass' },
    { id: 'synth_future', name: 'Future Bass Chime', icon: '🛸', baseFreq: 392.00, type: 'chord' },
    { id: 'synth_cyberarp', name: 'Cyber 16th Arp', icon: '⚡', baseFreq: 440.00, type: 'arp' }
  ];

  const VOCALS = [
    { id: 'vox_yeah', name: 'Chant: "YEAH!"', icon: '🎤', text: 'YEAH!', formants: [800, 1200, 2500], pitch: 240 },
    { id: 'vox_yo', name: 'Chant: "YO!"', icon: '🗣️', text: 'YO!', formants: [450, 900, 2400], pitch: 190 },
    { id: 'vox_checkit', name: 'Hook: "CHECK IT!"', icon: '💥', text: 'CHECK IT!', formants: [600, 1800, 2800], pitch: 260 },
    { id: 'vox_drop', name: 'Drop: "DROP THAT!"', icon: '💣', text: 'DROP THAT!', formants: [350, 1100, 2200], pitch: 160 },
    { id: 'vox_uh', name: 'Accent: "UH!"', icon: '👊', text: 'UH!', formants: [500, 1000, 2300], pitch: 180 },
    { id: 'vox_fresh', name: 'Cue: "FRESH!"', icon: '💿', text: 'FRESH!', formants: [700, 1900, 3100], pitch: 300 },
    { id: 'vox_aahh', name: 'Vocal: "Aahh" Choir', icon: '🕊️', text: 'AAHH', formants: [750, 1150, 2400], pitch: 220 },
    { id: 'vox_oohh', name: 'Vocal: "Oohh" Sub', icon: '🌌', text: 'OOHH', formants: [380, 800, 2100], pitch: 140 },
    { id: 'vox_talkbox', name: 'Talkbox Funk Vowel', icon: '🤖', text: 'WAH-WAH', formants: [650, 1300, 2600], pitch: 210 },
    { id: 'vox_beatbox', name: 'Beatbox "Pshh-Ktk"', icon: '💨', text: 'PSHH!', formants: [900, 2400, 4200], pitch: 120 },
    { id: 'vox_siren', name: 'Trap Siren Vox', icon: '🚨', text: 'WHEEE-OOO', formants: [1100, 2200, 3500], pitch: 580 },
    { id: 'vox_scratch', name: 'Rewind Scratch Vox', icon: '🎛️', text: 'CH-CH-WHEW', formants: [1200, 2600, 3800], pitch: 420 }
  ];

  const SOLFEGGIO_TONES = [
    { freq: 174, name: '174 Hz (Foundation)' },
    { freq: 285, name: '285 Hz (Cognition)' },
    { freq: 396, name: '396 Hz (Liberation)' },
    { freq: 417, name: '417 Hz (Facilitation)' },
    { freq: 528, name: '528 Hz (Transformation / Miracles)' },
    { freq: 639, name: '639 Hz (Connection)' },
    { freq: 741, name: '741 Hz (Awakening)' },
    { freq: 852, name: '852 Hz (Intuition)' },
    { freq: 963, name: '963 Hz (Crown Consensus)' }
  ];

  // Minor Pentatonic Note Frequencies (C4, Eb4, F4, G4, Bb4, C5, Eb5, F5)
  const PENTATONIC_SCALE = [
    261.63, 311.13, 349.23, 392.00, 466.16, 523.25, 622.25, 698.46
  ];

  // ── ENGINE STATE ────────────────────────────────────────────────────────────

  const audioState = {
    isInitialized: false,
    activeLoops: new Set(),         // Set of active loop IDs
    loopStep: 0,                   // 0 to 15
    loopIntervalId: null,
    tempoBpm: 92,
    masterVolume: 0.85,
    filterCutoff: 3800,
    filterResonance: 3.5,
    stereoPan: 0.0,
    spatialDepth: 0.5,
    activeVoice: null,
    lastGestureTriggerTime: 0,
    activeSoundCard: null,         // { text, icon, color, timestamp }
    waveformBuffer: new Uint8Array(128),
    recentNotes: []
  };

  let audioCtx = null;
  let masterGain = null;
  let masterFilter = null;
  let masterPan = null;
  let masterAnalyser = null;

  // ── AUDIO GRAPH INITIALIZATION ──────────────────────────────────────────────

  function getAudioCtx() {
    if (audioCtx) return audioCtx;
    if (typeof window !== 'undefined' && window.VisionApp && typeof window.VisionApp.ensureAudioContext === 'function') {
      window.VisionApp.ensureAudioContext();
      audioCtx = window.VisionApp.getAudioContext ? window.VisionApp.getAudioContext() : null;
    }
    if (!audioCtx && typeof window !== 'undefined') {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) audioCtx = new AudioContextClass();
    }
    return audioCtx;
  }

  function initAudioGraph() {
    const ctx = getAudioCtx();
    if (!ctx) return false;
    if (masterGain) return true;

    try {
      masterGain = ctx.createGain();
      masterFilter = ctx.createBiquadFilter();
      masterFilter.type = 'lowpass';
      masterFilter.frequency.setValueAtTime(audioState.filterCutoff, ctx.currentTime);
      masterFilter.Q.setValueAtTime(audioState.filterResonance, ctx.currentTime);

      if (ctx.createStereoPanner) {
        masterPan = ctx.createStereoPanner();
        masterPan.pan.setValueAtTime(audioState.stereoPan, ctx.currentTime);
      }

      masterAnalyser = ctx.createAnalyser();
      masterAnalyser.fftSize = 256;

      masterGain.gain.setValueAtTime(audioState.masterVolume, ctx.currentTime);

      // Connect graph: Inputs -> MasterFilter -> MasterPan -> MasterGain -> Analyser -> Destination
      if (masterPan) {
        masterFilter.connect(masterPan);
        masterPan.connect(masterGain);
      } else {
        masterFilter.connect(masterGain);
      }

      masterGain.connect(masterAnalyser);
      masterAnalyser.connect(ctx.destination);

      audioState.isInitialized = true;
      return true;
    } catch (e) {
      console.warn("Spatial Audio graph initialization warning:", e);
      return false;
    }
  }

  // ── SOUND SYNTHESIS ENGINES ─────────────────────────────────────────────────

  /**
   * Generates a noise buffer for snares, hats, and scratches
   */
  function createNoiseBuffer(ctx, duration = 0.5) {
    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  }

  /**
   * Synthesize an authentic 808 Sub Kick
   */
  function triggerKick(t, is808Sub = false) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    const startFreq = is808Sub ? 120 : 150;
    const endFreq = is808Sub ? 38 : 48;
    const duration = is808Sub ? 0.42 : 0.22;

    osc.frequency.setValueAtTime(startFreq, now);
    osc.frequency.exponentialRampToValueAtTime(endFreq, now + duration * 0.4);

    gain.gain.setValueAtTime(0.85, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

    // Punch transient click
    const clickOsc = ctx.createOscillator();
    const clickGain = ctx.createGain();
    clickOsc.type = 'triangle';
    clickOsc.frequency.setValueAtTime(320, now);
    clickOsc.frequency.exponentialRampToValueAtTime(40, now + 0.025);
    clickGain.gain.setValueAtTime(0.5, now);
    clickGain.gain.exponentialRampToValueAtTime(0.001, now + 0.025);
    clickOsc.connect(clickGain);
    clickGain.connect(masterFilter);
    clickOsc.start(now);
    clickOsc.stop(now + 0.03);

    osc.connect(gain);
    gain.connect(masterFilter);
    osc.start(now);
    osc.stop(now + duration);
  }

  /**
   * Synthesize a crisp Hip-Hop Snare / Clap
   */
  function triggerSnare(t) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    // Body tone
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(185, now);
    osc.frequency.exponentialRampToValueAtTime(80, now + 0.08);
    gain.gain.setValueAtTime(0.4, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
    osc.connect(gain);
    gain.connect(masterFilter);
    osc.start(now);
    osc.stop(now + 0.13);

    // Noise snap
    const noise = ctx.createBufferSource();
    noise.buffer = createNoiseBuffer(ctx, 0.25);
    const noiseFilter = ctx.createBiquadFilter();
    noiseFilter.type = 'highpass';
    noiseFilter.frequency.setValueAtTime(1000, now);
    const noiseGain = ctx.createGain();
    noiseGain.gain.setValueAtTime(0.65, now);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

    noise.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(masterFilter);
    noise.start(now);
    noise.stop(now + 0.23);
  }

  /**
   * Synthesize a metallic Trap Hi-Hat
   */
  function triggerHat(t, isOpen = false) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const noise = ctx.createBufferSource();
    noise.buffer = createNoiseBuffer(ctx, isOpen ? 0.35 : 0.08);

    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(7500, now);
    filter.Q.setValueAtTime(3.5, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(isOpen ? 0.45 : 0.35, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + (isOpen ? 0.32 : 0.06));

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(masterFilter);
    noise.start(now);
    noise.stop(now + (isOpen ? 0.34 : 0.07));
  }

  /**
   * Synthesize a Memphis 808 Cowbell
   */
  function triggerCowbell(t, freq = 800) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const filter = ctx.createBiquadFilter();
    const gain = ctx.createGain();

    osc1.type = 'square';
    osc2.type = 'square';
    osc1.frequency.setValueAtTime(freq, now);
    osc2.frequency.setValueAtTime(freq * 1.5, now);

    filter.type = 'bandpass';
    filter.frequency.setValueAtTime(freq * 1.25, now);
    filter.Q.setValueAtTime(6.0, now);

    gain.gain.setValueAtTime(0.55, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc1.connect(filter);
    osc2.connect(filter);
    filter.connect(gain);
    gain.connect(masterFilter);

    osc1.start(now);
    osc2.start(now);
    osc1.stop(now + 0.36);
    osc2.stop(now + 0.36);
  }

  /**
   * Synthesize human vocal formant vowels ("Yeah!", "Yo!", "Check It!")
   */
  function triggerVocalSample(vocalPreset, t) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const p = vocalPreset || VOCALS[0];
    const pitch = p.pitch || 220;
    const formants = p.formants || [800, 1200, 2500];

    // Dual pulse-saw glottal source
    const glottal = ctx.createOscillator();
    glottal.type = 'sawtooth';
    glottal.frequency.setValueAtTime(pitch * 1.15, now);
    glottal.frequency.exponentialRampToValueAtTime(pitch * 0.85, now + 0.28);

    const voiceGain = ctx.createGain();
    voiceGain.gain.setValueAtTime(0.65, now);
    voiceGain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

    // 3 Formant bandpass filters in parallel (simulating vocal tract resonances)
    formants.forEach(fmtFreq => {
      const bq = ctx.createBiquadFilter();
      bq.type = 'bandpass';
      bq.frequency.setValueAtTime(fmtFreq, now);
      bq.Q.setValueAtTime(5.5, now);
      glottal.connect(bq);
      bq.connect(voiceGain);
    });

    voiceGain.connect(masterFilter);
    glottal.start(now);
    glottal.stop(now + 0.33);

    flashSoundCard(p.text || p.name, p.icon || '🎤', '#38bdf8');
  }

  /**
   * Synthesize Hip-Hop Synths & Basses
   */
  function triggerSynthSound(synthPreset, freqOverride, t) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const s = synthPreset || SYNTHS[0];
    const baseF = freqOverride || s.baseFreq || 130.81;

    if (s.type === 'sub') {
      // 808 Deep Sub Slide
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(baseF * 1.5, now);
      osc.frequency.exponentialRampToValueAtTime(baseF * 0.85, now + 0.45);
      gain.gain.setValueAtTime(0.85, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
      osc.connect(gain);
      gain.connect(masterFilter);
      osc.start(now);
      osc.stop(now + 0.56);
    } else if (s.type === 'lead') {
      // G-Funk Saw Whistle
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(baseF, now);
      gain.gain.setValueAtTime(0.35, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      osc.connect(gain);
      gain.connect(masterFilter);
      osc.start(now);
      osc.stop(now + 0.42);
    } else if (s.type === 'chord') {
      // Lo-Fi Rhodes / Chords: 3-note triad
      [1.0, 1.25, 1.5].forEach(multiplier => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(baseF * multiplier, now);
        gain.gain.setValueAtTime(0.22, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
        osc.connect(gain);
        gain.connect(masterFilter);
        osc.start(now);
        osc.stop(now + 0.62);
      });
    } else if (s.type === 'brass') {
      // Detroit Brass Horns
      [1.0, 1.01, 0.5].forEach(detuneMult => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(baseF * detuneMult, now);
        gain.gain.setValueAtTime(0.28, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
        osc.connect(gain);
        gain.connect(masterFilter);
        osc.start(now);
        osc.stop(now + 0.4);
      });
    } else {
      // Default melodics (pluck/bell)
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(baseF, now);
      gain.gain.setValueAtTime(0.4, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
      osc.connect(gain);
      gain.connect(masterFilter);
      osc.start(now);
      osc.stop(now + 0.32);
    }

    flashSoundCard(s.name, s.icon || '🎹', '#f59e0b');
  }

  /**
   * Turntable Vinyl Scratch & Rewind Effect
   */
  function triggerTurntableScratch(t) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = t || ctx.currentTime;

    const noise = ctx.createBufferSource();
    noise.buffer = createNoiseBuffer(ctx, 0.35);

    const bq = ctx.createBiquadFilter();
    bq.type = 'bandpass';
    bq.frequency.setValueAtTime(2400, now);
    bq.frequency.exponentialRampToValueAtTime(450, now + 0.18);
    bq.frequency.exponentialRampToValueAtTime(1800, now + 0.32);
    bq.Q.setValueAtTime(8.0, now);

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.7, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.34);

    noise.connect(bq);
    bq.connect(gain);
    gain.connect(masterFilter);
    noise.start(now);
    noise.stop(now + 0.35);

    flashSoundCard('TURNTABLE SCRATCH', '💿', '#ec4899');
  }

  // ── LOOP METRONOME SCHEDULER ────────────────────────────────────────────────

  function startLoopScheduler() {
    if (audioState.loopIntervalId) return;
    const stepMs = Math.round((60000 / audioState.tempoBpm) / 4); // 16th note steps

    audioState.loopIntervalId = setInterval(() => {
      if (audioState.activeLoops.size === 0) return;
      const ctx = getAudioCtx();
      if (!ctx) return;
      const t = ctx.currentTime;
      const step = audioState.loopStep;

      audioState.activeLoops.forEach(loopId => {
        const loop = LOOPS.find(l => l.id === loopId);
        if (!loop || !loop.pattern) return;

        if (loop.pattern.kick && loop.pattern.kick[step]) triggerKick(t, false);
        if (loop.pattern.sub && loop.pattern.sub[step]) triggerKick(t, true);
        if (loop.pattern.snare && loop.pattern.snare[step]) triggerSnare(t);
        if (loop.pattern.hat && loop.pattern.hat[step]) triggerHat(t, false);
        if (loop.pattern.openHat && loop.pattern.openHat[step]) triggerHat(t, true);
        if (loop.pattern.cowbell && loop.pattern.cowbell[step]) triggerCowbell(t, 800);
        if (loop.pattern.chord && loop.pattern.chord[step]) triggerSynthSound(SYNTHS[3], 261.63, t);
      });

      audioState.loopStep = (audioState.loopStep + 1) % 16;
    }, stepMs);
    if (audioState.loopIntervalId && typeof audioState.loopIntervalId.unref === 'function') {
      audioState.loopIntervalId.unref();
    }
  }

  function stopLoopScheduler() {
    if (audioState.loopIntervalId) {
      clearInterval(audioState.loopIntervalId);
      audioState.loopIntervalId = null;
    }
    audioState.loopStep = 0;
  }

  function toggleLoop(loopId) {
    let nowActive = false;
    if (audioState.activeLoops.has(loopId)) {
      audioState.activeLoops.delete(loopId);
      if (audioState.activeLoops.size === 0) {
        stopLoopScheduler();
      }
      flashSoundCard(`STOPPED: ${loopId}`, '⏸️', '#94a3b8');
      nowActive = false;
    } else {
      const loop = LOOPS.find(l => l.id === loopId);
      if (loop) {
        audioState.tempoBpm = loop.bpm || audioState.tempoBpm;
      }
      audioState.activeLoops.add(loopId);
      startLoopScheduler();
      flashSoundCard(`LOOPING: ${loop ? loop.name : loopId}`, '🔁', '#10b981');
      nowActive = true;
    }
    return nowActive;
  }

  function stopAll() {
    audioState.activeLoops.clear();
    stopLoopScheduler();
    const ctx = getAudioCtx();
    if (masterGain && ctx) {
      try {
        masterGain.gain.setValueAtTime(0.0001, ctx.currentTime);
        const timer = setTimeout(() => {
          if (masterGain && ctx) masterGain.gain.setValueAtTime(audioState.masterVolume, ctx.currentTime);
        }, 120);
        if (timer && typeof timer.unref === 'function') timer.unref();
      } catch (e) {}
    }
  }

  // ── VISUAL CARD POPUP ───────────────────────────────────────────────────────

  function flashSoundCard(text, icon = '🎵', color = '#00f0ff') {
    audioState.activeSoundCard = {
      text,
      icon,
      color,
      timestamp: performance.now()
    };
  }

  // ── SPATIAL HAND TRACKING INTEGRATION ───────────────────────────────────────

  /**
   * Process hands for spatial audio modulation and gesture triggering
   */
  function processHands(h0, h1, g0, g1) {
    const ctx = getAudioCtx();
    if (!ctx || !initAudioGraph()) return;
    const now = performance.now();

    // 1. Right Hand X-Axis: Pitch / Pentatonic Note Selection
    //    Right Hand Y-Axis: Filter Cutoff & Vertical Tap Trigger
    if (h0) {
      const normX = Math.max(0, Math.min(1.0, h0[8].x));
      const normY = Math.max(0, Math.min(1.0, h0[8].y));

      // Cutoff: 200 Hz (muffled bottom) to 12,000 Hz (bright open top)
      audioState.filterCutoff = Math.round(12000 - normY * 11700);
      if (masterFilter) {
        masterFilter.frequency.setTargetAtTime(audioState.filterCutoff, ctx.currentTime, 0.05);
      }

      // Map X-position to Pentatonic Scale
      const noteIdx = Math.floor(normX * PENTATONIC_SCALE.length);
      const noteFreq = PENTATONIC_SCALE[Math.min(PENTATONIC_SCALE.length - 1, noteIdx)];

      // 2. Left Hand Y-Axis: Volume
      //    Left Hand X-Axis: Stereo Panning
      if (h1) {
        const h1NormY = Math.max(0, Math.min(1.0, h1[8].y));
        const h1NormX = Math.max(0, Math.min(1.0, h1[8].x));

        audioState.masterVolume = +(Math.max(0.05, Math.min(1.0, 1.0 - h1NormY))).toFixed(2);
        if (masterGain) {
          masterGain.gain.setTargetAtTime(audioState.masterVolume, ctx.currentTime, 0.05);
        }

        // Stereo pan: -0.9 (left) to +0.9 (right)
        audioState.stereoPan = +((h1NormX - 0.5) * 1.8).toFixed(2);
        if (masterPan && masterPan.pan) {
          masterPan.pan.setTargetAtTime(audioState.stereoPan, ctx.currentTime, 0.05);
        }
      }

      // 3. Gesture Triggers (with 450ms cooldown)
      const activeG = (g0 && g0 !== 'UNKNOWN' && g0 !== 'NONE') ? g0 : (g1 && g1 !== 'UNKNOWN' && g1 !== 'NONE' ? g1 : null);
      if (activeG && (now - audioState.lastGestureTriggerTime > 450)) {
        if (activeG === 'VICTORY_PEACE') {
          // ✌️ Peace: Vocal Chop
          audioState.lastGestureTriggerTime = now;
          const randomVox = VOCALS[Math.floor(Math.random() * 6)];
          triggerVocalSample(randomVox);
        } else if (activeG === 'ROCK_ON') {
          // 🤘 Rock On: 808 Sub Slide / Detroit Horn
          audioState.lastGestureTriggerTime = now;
          triggerSynthSound(SYNTHS[0], 46.25);
        } else if (activeG === 'THUMBS_UP') {
          // 👍 Thumbs Up: Turntable Scratch
          audioState.lastGestureTriggerTime = now;
          triggerTurntableScratch();
        } else if (activeG === 'THUMBS_DOWN') {
          // 👎 Thumbs Down: Sub Drop / Impact
          audioState.lastGestureTriggerTime = now;
          triggerKick(ctx.currentTime, true);
          flashSoundCard('808 SUB IMPACT', '💣', '#ef4444');
        } else if (activeG === 'SHAKA') {
          // 🤙 Shaka: Lo-Fi Rhodes / Cloud Pad
          audioState.lastGestureTriggerTime = now;
          triggerSynthSound(SYNTHS[3], noteFreq);
        } else if (activeG === 'PINCH') {
          // 👌 Pinch: Trap Hi-Hat Roll
          audioState.lastGestureTriggerTime = now;
          [0, 0.05, 0.1, 0.15].forEach(dt => triggerHat(ctx.currentTime + dt, false));
          flashSoundCard('TRAP HAT ROLL', '⚡', '#10b981');
        } else if (activeG === 'FIST') {
          // ✊ Fist: Choke / Mute All
          audioState.lastGestureTriggerTime = now;
          stopAll();
          flashSoundCard('CHOKE / MUTE ALL', '✊', '#64748b');
        }
      }
    }
  }

  // ── PLAYGROUND STAGE RENDERER (OSCILLOSCOPE, PADS, METERS) ──────────────────

  /**
   * Renders the complete Spatial Audio & Loop Studio on #playgroundCanvas
   */
  function renderStage(ctx, w, h, now) {
    if (!ctx) return;

    // Retrieve live audio waveform
    if (masterAnalyser) {
      masterAnalyser.getByteTimeDomainData(audioState.waveformBuffer);
    }

    ctx.save();

    // 1. Neon Oscilloscope Background Field
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.45)';
    ctx.lineWidth = 2.5;
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 12;

    ctx.beginPath();
    const sliceWidth = w / audioState.waveformBuffer.length;
    let ox = 0;
    for (let i = 0; i < audioState.waveformBuffer.length; i++) {
      const v = audioState.waveformBuffer[i] / 128.0;
      const oy = (v * h) * 0.45 + h * 0.25;
      if (i === 0) ctx.moveTo(ox, oy);
      else ctx.lineTo(ox, oy);
      ox += sliceWidth;
    }
    ctx.stroke();
    ctx.restore();

    // 2. Loop Deck Channel Bar (Top of Stage)
    ctx.save();
    const barH = 54;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
    ctx.fillRect(10, 10, w - 20, barH);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.strokeRect(10, 10, w - 20, barH);

    // Title & BPM badge
    ctx.font = 'bold 11px monospace';
    ctx.fillStyle = '#38bdf8';
    ctx.fillText(`SPATIAL BEAT STUDIO • ${audioState.tempoBpm} BPM`, 22, 28);

    // 8 Loop Channel Chips
    const chipW = (w - 60) / 8;
    LOOPS.forEach((loop, idx) => {
      const cx = 22 + idx * chipW;
      const cy = 34;
      const isActive = audioState.activeLoops.has(loop.id);

      ctx.save();
      ctx.beginPath();
      ctx.roundRect(cx, cy, chipW - 6, 24, 4);
      ctx.fillStyle = isActive ? 'rgba(16, 185, 129, 0.35)' : 'rgba(255, 255, 255, 0.05)';
      ctx.fill();
      ctx.strokeStyle = isActive ? '#10b981' : 'rgba(255, 255, 255, 0.12)';
      ctx.lineWidth = isActive ? 2 : 1;
      ctx.stroke();

      ctx.font = '10px monospace';
      ctx.fillStyle = isActive ? '#ffffff' : '#94a3b8';
      ctx.fillText(`${loop.icon} ${loop.name.slice(0, 8)}`, cx + 6, cy + 16);
      ctx.restore();
    });
    ctx.restore();

    // 3. Floating Spatial Sound Triggers & Sound Matrix (Bottom of Stage)
    ctx.save();
    const matrixY = h - 90;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
    ctx.fillRect(10, matrixY, w - 20, 80);
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
    ctx.strokeRect(10, matrixY, w - 20, 80);

    ctx.font = '10px monospace';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('🖐️ GESTURE TRIGGERS:  ✌️ Peace: Vocal Chop  •  🤘 Rock: 808 Bass  •  👍 Thumb: Scratch  •  👌 Pinch: Hat Roll  •  ✊ Fist: Mute', 22, matrixY + 22);

    // Readout Meters: Cutoff, Volume, Pan
    ctx.fillStyle = '#38bdf8';
    ctx.fillText(`FILTER CUTOFF: ${audioState.filterCutoff} Hz`, 22, matrixY + 48);
    ctx.fillStyle = '#f59e0b';
    ctx.fillText(`MASTER VOL: ${Math.round(audioState.masterVolume * 100)}%`, 220, matrixY + 48);
    ctx.fillStyle = '#a855f7';
    ctx.fillText(`STEREO PAN: ${audioState.stereoPan > 0 ? '+' : ''}${audioState.stereoPan}`, 380, matrixY + 48);
    ctx.restore();

    // 4. Floating Animated Hit Notification Card
    if (audioState.activeSoundCard) {
      const card = audioState.activeSoundCard;
      const elapsed = now - card.timestamp;
      if (elapsed < 1400) {
        const alpha = Math.max(0, 1.0 - elapsed / 1400);
        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.translate(w * 0.5, h * 0.52 - (elapsed * 0.04));

        ctx.fillStyle = 'rgba(10, 15, 26, 0.94)';
        ctx.strokeStyle = card.color || '#00f0ff';
        ctx.lineWidth = 2.5;
        ctx.shadowColor = card.color || '#00f0ff';
        ctx.shadowBlur = 18;

        ctx.beginPath();
        ctx.roundRect(-140, -25, 280, 50, 10);
        ctx.fill();
        ctx.stroke();

        ctx.font = '22px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(card.icon, -105, 8);

        ctx.font = 'bold 13px monospace';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'left';
        ctx.fillText(card.text, -80, 6);

        ctx.restore();
      } else {
        audioState.activeSoundCard = null;
      }
    }

    // 5. Active Loop Beat Indicator Dots (Step 0 to 15)
    if (audioState.activeLoops.size > 0) {
      ctx.save();
      const dotStartY = 68;
      const dotSpacing = (w - 40) / 16;
      for (let s = 0; s < 16; s++) {
        const dx = 20 + s * dotSpacing;
        const isCurrent = (s === audioState.loopStep);
        ctx.beginPath();
        ctx.arc(dx, dotStartY, isCurrent ? 5 : 2.5, 0, Math.PI * 2);
        ctx.fillStyle = isCurrent ? '#10b981' : 'rgba(255, 255, 255, 0.2)';
        ctx.fill();
        if (isCurrent) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }
      }
      ctx.restore();
    }
  }

  function handleCanvasClick(px, py, w, h) {
    if (!w) w = 800;
    if (!h) h = 520;

    // 1. Loop chips click (top bar: y ~ 28-64)
    if (py >= 28 && py <= 64) {
      const chipW = (w - 60) / 8;
      const idx = Math.floor((px - 22) / chipW);
      if (idx >= 0 && idx < LOOPS.length) {
        toggleLoop(LOOPS[idx].id);
        return true;
      }
    }

    // 2. Main visualizer field click: trigger pitch / synth
    if (py > 64 && py < h - 90) {
      const normX = Math.max(0, Math.min(1, px / w));
      const normY = Math.max(0, Math.min(1, py / h));
      setHandModulation(normX, 1.0 - normY, normX * 2.0 - 1.0);
      const synthIdx = Math.floor(normX * SYNTHS.length) % SYNTHS.length;
      triggerSynthSound(SYNTHS[synthIdx]);
      return true;
    }

    // 3. Gesture trigger bar click (bottom: py >= h - 90)
    if (py >= h - 90) {
      const sectW = (w - 20) / 5;
      const sectIdx = Math.floor((px - 10) / sectW);
      if (sectIdx === 0) triggerVocalSample(VOCALS[Math.floor(Math.random() * VOCALS.length)]);
      else if (sectIdx === 1) triggerSynthSound(SYNTHS[0]); // 808
      else if (sectIdx === 2) triggerTurntableScratch();
      else if (sectIdx === 3) triggerHat();
      else if (sectIdx === 4) stopAll();
      return true;
    }
    return false;
  }

  // ── PUBLIC API EXPORTS ──────────────────────────────────────────────────────

  return {
    name: 'spatialAudio',
    LOOPS,
    SYNTHS,
    VOCALS,
    SOLFEGGIO_TONES,
    state: audioState,
    getAudioCtx,
    initAudioGraph,
    triggerKick,
    triggerSnare,
    triggerHat,
    triggerCowbell,
    triggerVocalSample,
    triggerSynthSound,
    triggerTurntableScratch,
    toggleLoop,
    startLoopScheduler,
    stopLoopScheduler,
    stopAll,
    processHands,
    renderStage,
    flashSoundCard,
    handleCanvasClick
  };
});

