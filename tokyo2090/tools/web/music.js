// music.js - procedural audio for the Tokyo 2090 glider.
//
//   * Erik Satie, Gymnopedie No. 1 (1888, public domain), played on a synthesized
//     piano, about 60 bpm, 3/4, looped with a 3 s gap.
//   * a very quiet evening ambience: higurashi cicadas + a few bird chirps.
//   * while flying, one faint high-passed "breath" that follows the speed.
//
// Everything is generated at run time (no audio files, no dependencies).
//
//   const audio = createAudio();
//   audio.start();            // from a user gesture
//   audio.setFlying(true);    // false = resting on a roof (more cicadas)
//   audio.setSpeed(42);       // m/s, drives the faint breath and cicada thinning
//   audio.volume(0.7);        // 0..1 master (default 0.7)
//   audio.stop();             // 1 s fade-out, then the context is suspended
//
// The pure parts (score, envelope, impulse response, PRNG) are exported too, so
// they can be checked from node (see ../music.test.mjs). Nothing here touches
// Web Audio until start() is called.

// ---------------------------------------------------------------------------
// small pure helpers
// ---------------------------------------------------------------------------

export const BPM = 60;
export const SECONDS_PER_BEAT = 60 / BPM;
export const LOOP_GAP_S = 3;

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

export const midiToHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

const PITCH_CLASS = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };

/** 'F#5' -> 78, 'C4' -> 60. Accidentals are always explicit (no key signature). */
export function noteToMidi(name) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(name);
  if (!m) throw new Error('bad note name: ' + name);
  const acc = m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0;
  return 12 * (parseInt(m[3], 10) + 1) + PITCH_CLASS[m[1]] + acc;
}

/**
 * "F#5@1:2 A5" -> [{midi, beat, dur}]. Each token is NOTE[@beat[:duration]],
 * beat is counted from the start of the bar (0 = beat 1) and both default to
 * the supplied defaults.
 */
export function parseTokens(str, defBeat, defDur) {
  const out = [];
  for (const tok of str.split(/\s+/).filter(Boolean)) {
    const m = /^([A-G][#b]?-?\d)(?:@(\d+(?:\.\d+)?)(?::(\d+(?:\.\d+)?))?)?$/.exec(tok);
    if (!m) throw new Error('bad token: ' + tok);
    out.push({
      midi: noteToMidi(m[1]),
      beat: m[2] === undefined ? defBeat : parseFloat(m[2]),
      dur: m[3] === undefined ? defDur : parseFloat(m[3]),
    });
  }
  return out;
}

// ---------------------------------------------------------------------------
// The score: Gymnopedie No. 1, D major, 3/4, 78 bars
// ---------------------------------------------------------------------------
//
// Form (one pass = 39 bars, the whole piece is played twice = 78 bars):
//   bars  1- 4  intro: Gmaj7 / Dmaj7 / Gmaj7 / Dmaj7
//   bars  5- 8  the theme  (rest, F#5 A5 | G5 F#5 C#5 | B4 C#5 D5 | A4)
//   bars  9-12  the same two chords under a long F#4
//   bars 13-16  the theme again
//   bars 17-24  middle part: C#5, F#5, long E4, then A4 B4 C5 / E5 D5 B4 / D5 C5 B4
//   bars 25-31  D pedal, long D5, E5 F5 G5 / A5 C5 D5 / E5 D5 B4 / D5 ...
//   bars 32-39  first ending (to D major)  -> repeat from bar 1
//                second ending (to D minor) on the second pass
//
// Each bar is [bass, chord, melody] in the NOTE@beat:dur mini-notation of
// parseTokens(). Defaults: bass @0:3 (whole bar, held by the pedal), chord @1:2
// (beats 2 and 3), melody @0:1. Source: transcribed from the score by way of a
// single-line ABC reduction; see the comments in the report for what was
// reconstructed.

const G7 = ['G2', 'B3 D4 F#4'];
const D7 = ['D2', 'A3 C#4 F#4'];

const THEME = [
  [...G7, 'F#5@1 A5@2'],
  [...D7, 'G5@0 F#5@1 C#5@2'],
  [...G7, 'B4@0 C#5@1 D5@2'],
  [...D7, 'A4@0:3'],
];

const PART_A = [
  // 1-4 intro
  [...G7, ''], [...D7, ''], [...G7, ''], [...D7, ''],
  // 5-8 theme
  ...THEME,
  // 9-12 long F#4
  [...G7, 'F#4@0:12'], [...D7, ''], [...G7, ''], [...D7, ''],
  // 13-16 theme again
  ...THEME,
  // 17-24
  ['F#2', 'A3 C#4 F#4', 'C#5@0:3'],
  ['B2', 'B3 D4 F#4', 'F#5@0:3'],
  ['E2', 'G3 B3', 'E4@0:9'],
  ['E2', 'B3 D4 G4', ''],
  ['D2', 'F3 A3 D4', ''],
  ['A2', 'A3 C4 E4', 'A4@0 B4@1 C5@2'],
  ['D2', 'G3 B3 E4', 'E5@0 D5@1 B4@2'],
  ['D2', 'G3 B3 E4', 'D5@0 C5@1 B4@2'],
  // 25-31 (D pedal)
  ['D2', 'C3 E3 A3', 'D5@0:5'],
  ['D2', 'C3 E3 A3', 'D5@2'],
  ['D2', 'A3 C4 F4', 'E5@0 F5@1 G5@2'],
  ['D2', 'A3 C4 E4', 'A5@0 C5@1 D5@2'],
  ['D2', 'G3 B3 E4', 'E5@0 D5@1 B4@2'],
  ['D2', 'C3 E3 A3', 'D5@0:5'],
  ['D2', 'C3 F#3 A3', 'D5@2'],
];

// bars 32-39, first ending (resolves to D major, then repeats)
const ENDING_1 = [
  ['E2', 'B3 E4 G4', 'G5@0:3'],
  ['F#2', 'A3 C#4 F#4', 'F#5@0:3'],
  ['B2', 'B3 D4 F#4', 'B4@0 A4@1 B4@2'],
  ['E2', 'C#4 E4 A4', 'C#5@0 D5@1 E5@2'],
  ['E2', 'A3 C#4 F#4', 'C#5@0 D5@1 E5@2'],
  ['E2@0:1 B2@1:1 E3@2:1', 'A3@1:1 D4@1:1 B3@2:1 D4@2:1 G4@2:1', 'F#4@0:3'],
  ['A2', 'C4@0:3 E4@0:3 A4@0:3', 'C5@0:3'],
  ['D2@0:3 A2@0:3 D3@0:3', 'D4@0:3 F#4@0:3 A4@0:3', 'D5@0:3'],
];

// bars 32-39, second ending (darker, closes on D minor)
const ENDING_2 = [
  ['E2', 'B3 E4 G4', 'G5@0:3'],
  ['E2', 'A3 D4 F4', 'F5@0:3'],
  ['E2', 'A3 C4 F4', 'B4@0 C5@1 F5@2'],
  ['E2', 'A3 C4 E4', 'E5@0 D5@1 C5@2'],
  ['E2', 'A3 C4 F4', 'E5@0 D5@1 C5@2'],
  ['E2@0:1 B2@1:1 E3@2:1', 'A3@1:1 D4@1:1 B3@2:1 D4@2:1 G4@2:1', 'F4@0:3'],
  ['A2@0:3 G3@0:3', 'C4@0:3 E4@0:3 A4@0:3', 'C5@0:3'],
  ['D2@0:3 A2@0:3 D3@0:3', 'D4@0:3 F4@0:3 A4@0:3', 'D5@0:3'],
];

export const VEL_MELODY = 0.5;
export const VEL_CHORD = 0.3;
export const VEL_BASS = 0.4;

/**
 * Builds the whole 78-bar score. Notes are [startBeat, durationBeats, midi, velocity].
 * Returns { bass, chords, melody, notes (all, sorted), bars, beats, barList }.
 */
export function buildScore() {
  const bars = [...PART_A, ...ENDING_1, ...PART_A, ...ENDING_2];
  const bass = [], chords = [], melody = [];
  bars.forEach((bar, i) => {
    const b0 = i * 3;
    for (const n of parseTokens(bar[0], 0, 3)) bass.push([b0 + n.beat, n.dur, n.midi, VEL_BASS]);
    for (const n of parseTokens(bar[1], 1, 2)) chords.push([b0 + n.beat, n.dur, n.midi, VEL_CHORD]);
    for (const n of parseTokens(bar[2], 0, 1)) melody.push([b0 + n.beat, n.dur, n.midi, VEL_MELODY]);
  });
  const byStart = (a, b) => a[0] - b[0] || a[2] - b[2];
  const notes = [...bass, ...chords, ...melody].sort(byStart);
  return { bass, chords, melody, notes, bars: bars.length, beats: bars.length * 3, barList: bars };
}

/** Seeded humanisation: +-15 ms and +-0.05 velocity. Returns { dt (s), vel }. */
export function humanize(note, rng) {
  const dt = (rng() * 2 - 1) * 0.015;
  const vel = clamp(note[3] + (rng() * 2 - 1) * 0.05, 0.05, 1);
  return { dt, vel };
}

// ---------------------------------------------------------------------------
// piano envelope + reverb impulse (pure, testable)
// ---------------------------------------------------------------------------

export const ATTACK_S = 0.005;
export const RELEASE_S = 0.6;
export const TAIL_END_S = 7.5; // slow piano-like decay continues until here
export const MAX_VOICE_AGE_S = 8;

/**
 * Gain envelope as a list of points {t, v, lin}: 5 ms linear attack to `peak`,
 * exponential decay to the sustain level over `decay` s (~1.5), a slower
 * exponential fade, and at `hold` s a release of RELEASE_S down to silence. The
 * value at note-off is read from the pre-release curve so the release starts
 * from where the note actually is.
 */
export function envelopePoints(peak, hold, decay = 1.5) {
  const FLOOR = 0.0001;
  const sus = peak * 0.4;
  const curve = [
    [0, FLOOR],
    [ATTACK_S, peak],
    [ATTACK_S + decay, sus],
    [TAIL_END_S, peak * 0.07],
  ];
  const valueAt = (t) => {
    if (t <= 0) return FLOOR;
    if (t < ATTACK_S) return FLOOR + (peak - FLOOR) * (t / ATTACK_S);
    for (let i = 1; i < curve.length - 1; i++) {
      const [t0, v0] = curve[i];
      const [t1, v1] = curve[i + 1];
      if (t <= t1) return v0 * Math.pow(v1 / v0, (t - t0) / (t1 - t0));
    }
    return curve[curve.length - 1][1];
  };
  const pts = [{ t: 0, v: FLOOR, lin: true }];
  const h = Math.max(hold, ATTACK_S * 2);
  for (let i = 1; i < curve.length; i++) {
    if (curve[i][0] >= h) break;
    pts.push({ t: curve[i][0], v: curve[i][1], lin: i === 1 });
  }
  pts.push({ t: h, v: valueAt(h), lin: h < ATTACK_S + 1e-9 });
  pts.push({ t: h + RELEASE_S, v: FLOOR, lin: false });
  return pts;
}

/** Stereo exponentially-decaying noise impulse (RT60 = seconds), slightly darkening. */
export function makeImpulse(sampleRate, seconds, rng) {
  const n = Math.floor(sampleRate * seconds);
  const pre = Math.floor(sampleRate * 0.012);
  const fade = Math.floor(sampleRate * 0.008);
  const chans = [new Float32Array(n), new Float32Array(n)];
  for (const d of chans) {
    let lp = 0;
    for (let i = pre; i < n; i++) {
      const t = (i - pre) / sampleRate;
      const env = Math.exp((-6.9 * t) / seconds) * Math.min(1, (i - pre) / fade);
      const a = 0.12 + 0.6 * Math.exp(-t * 1.4); // one-pole lowpass opening -> closing
      lp += ((rng() * 2 - 1) - lp) * a;
      d[i] = lp * env;
    }
  }
  return chans;
}

// ---------------------------------------------------------------------------
// the audio engine
// ---------------------------------------------------------------------------

const LOOKAHEAD_S = 2.0;
const PUMP_MS = 250;
const MAX_VOICES = 48;
const MAX_HOLD_S = 6; // long tied notes die away on their own, no organ drones
const PIANO_PEAK = 0.5;
const REVERB_MIX = 0.28;
const REVERB_S = 2.5;
const CICADA_SLOTS = 5;
const CICADA_PEAK = 0.008;
const BIRD_PEAK = 0.02;
const BREATH_MAX = 0.004; // on ~0.25 rms noise: about 25 dB under the piano at top speed

// piano partials: sine fundamental (as a detuned pair), triangle +1 octave at -12 dB,
// sine 12th at -22 dB
const PARTIALS = [
  { type: 'sine', mult: 1, gain: 0.55, detune: -2.5 },
  { type: 'sine', mult: 1, gain: 0.45, detune: 2.5 },
  { type: 'triangle', mult: 2, gain: Math.pow(10, -12 / 20), detune: 1 },
  { type: 'sine', mult: 3, gain: Math.pow(10, -22 / 20), detune: -1.5 },
];
const PARTIAL_NORM = 1 / PARTIALS.reduce((s, p) => s + p.gain, 0);

/**
 * opts (all optional, mostly for tests):
 *   context : an existing (Offline)AudioContext to use
 *   manual  : no timers; drive the scheduler yourself with api._pump(untilSeconds)
 *   layers  : { music, cicada, birds, breath } booleans (default all true)
 */
export function createAudio(opts = {}) {
  const layers = Object.assign({ music: true, cicada: true, birds: true, breath: true }, opts.layers);
  const score = buildScore();
  const humRng = mulberry32(0x7a1ce090);

  let ctx = null;
  let master, comp, pianoBus, dryGain, convolver, wetGain, ambBus, ambSend;
  let cicadaBus, birdBus, breathGain;
  let noiseSrc = null;
  let running = false;
  let flying = false;
  let stepBuf = null, stepSide = 1;
  let speed = 0;
  let vol = 0.7;
  let pumpTimer = null;
  let stopTimer = null;
  let loopStart = 0;
  let noteIdx = 0;
  let cicadaNext = [];
  let birdNext = 0;
  const voices = new Set();

  // ---- graph -------------------------------------------------------------

  function build() {
    if (opts.context) {
      ctx = opts.context;
    } else {
      const AC = globalThis.AudioContext || globalThis.webkitAudioContext;
      if (!AC) throw new Error('Web Audio is not available');
      ctx = new AC({ latencyHint: 'playback' });
    }
    const sr = ctx.sampleRate;

    master = ctx.createGain();
    master.gain.value = 0;
    comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18;
    comp.knee.value = 24;
    comp.ratio.value = 3;
    comp.attack.value = 0.012;
    comp.release.value = 0.35;
    comp.connect(master);
    master.connect(ctx.destination);

    // piano -> dry + reverb -> compressor
    pianoBus = ctx.createGain();
    dryGain = ctx.createGain();
    dryGain.gain.value = 1 - REVERB_MIX;
    wetGain = ctx.createGain();
    wetGain.gain.value = REVERB_MIX;
    convolver = ctx.createConvolver();
    const ir = makeImpulse(sr, REVERB_S, mulberry32(0x51a71e));
    const buf = ctx.createBuffer(2, ir[0].length, sr);
    buf.getChannelData(0).set(ir[0]);
    buf.getChannelData(1).set(ir[1]);
    convolver.buffer = buf;
    pianoBus.connect(dryGain);
    dryGain.connect(comp);
    pianoBus.connect(convolver);
    convolver.connect(wetGain);
    wetGain.connect(comp);

    // ambience: straight to master (so the piano compressor never pumps it),
    // with a small send into the same reverb
    ambBus = ctx.createGain();
    ambBus.gain.value = 1;
    ambBus.connect(master);
    ambSend = ctx.createGain();
    ambSend.gain.value = 0.25;
    ambBus.connect(ambSend);
    ambSend.connect(convolver);

    cicadaBus = ctx.createGain();
    cicadaBus.gain.value = cicadaDensity();
    cicadaBus.connect(ambBus);
    birdBus = ctx.createGain();
    birdBus.gain.value = 1;
    birdBus.connect(ambBus);

    // faint breath: looped white noise -> high-pass -> soft low-pass -> gain (0 at rest)
    const nLen = sr * 2;
    const nBuf = ctx.createBuffer(1, nLen, sr);
    const nd = nBuf.getChannelData(0);
    const nr = mulberry32(0xb4ea7);
    for (let i = 0; i < nLen; i++) nd[i] = nr() * 2 - 1;
    // crossfade the loop seam so it never ticks
    const xf = Math.floor(sr * 0.05);
    for (let i = 0; i < xf; i++) {
      const w = i / xf;
      nd[i] = nd[i] * w + nd[nLen - xf + i] * (1 - w);
    }
    stepBuf = nBuf;
    noiseSrc = ctx.createBufferSource();
    noiseSrc.buffer = nBuf;
    noiseSrc.loop = true;
    noiseSrc.loopEnd = (nLen - xf) / sr;
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 3200;
    hp.Q.value = 0.5;
    const lpn = ctx.createBiquadFilter();
    lpn.type = 'lowpass';
    lpn.frequency.value = 9000;
    lpn.Q.value = 0.4;
    breathGain = ctx.createGain();
    breathGain.gain.value = 0;
    noiseSrc.connect(hp);
    hp.connect(lpn);
    lpn.connect(breathGain);
    breathGain.connect(ambBus);
    if (layers.breath) noiseSrc.start();
  }

  function panned(p) {
    if (ctx.createStereoPanner) {
      const n = ctx.createStereoPanner();
      n.pan.value = p;
      return n;
    }
    return ctx.createGain();
  }

  // ---- piano -------------------------------------------------------------

  function killVoice(v, now) {
    if (v.dead) return;
    v.dead = true;
    try {
      v.env.gain.cancelScheduledValues(now);
      v.env.gain.setTargetAtTime(0, now, 0.03);
      for (const o of v.oscs) o.stop(now + 0.2);
    } catch (e) { /* already stopped */ }
  }

  function playNote(t, durS, midi, vel) {
    const f = midiToHz(midi);
    const hold = clamp(durS, 0.25, MAX_HOLD_S);
    const peak = PIANO_PEAK * Math.pow(vel, 1.15);
    const decay = 1.5 * clamp(Math.pow(440 / f, 0.2), 0.7, 1.3);
    const stopAt = t + hold + RELEASE_S + 0.1;

    const mix = ctx.createGain();
    mix.gain.value = PARTIAL_NORM;
    const oscs = [];
    for (const p of PARTIALS) {
      const o = ctx.createOscillator();
      o.type = p.type;
      o.frequency.value = f * p.mult;
      o.detune.value = p.detune;
      const g = ctx.createGain();
      g.gain.value = p.gain;
      o.connect(g);
      g.connect(mix);
      o.start(t);
      o.stop(stopAt);
      oscs.push(o);
    }

    // brightness: opens with velocity, closes as the note decays
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.Q.value = 0.5;
    const c0 = clamp(f * (4 + 18 * vel), 700, 10000);
    const c1 = Math.max(c0 * 0.3, 300);
    lp.frequency.setValueAtTime(c0, t);
    lp.frequency.exponentialRampToValueAtTime(c1, t + 2.5);

    const env = ctx.createGain();
    const pts = envelopePoints(peak, hold, decay);
    env.gain.setValueAtTime(pts[0].v, t);
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].lin) env.gain.linearRampToValueAtTime(pts[i].v, t + pts[i].t);
      else env.gain.exponentialRampToValueAtTime(pts[i].v, t + pts[i].t);
    }
    env.gain.setValueAtTime(0, t + pts[pts.length - 1].t + 0.001);

    mix.connect(lp);
    lp.connect(env);
    env.connect(pianoBus);

    const v = { t0: t, oscs, env, dead: false };
    voices.add(v);
    oscs[0].onended = () => {
      voices.delete(v);
      try { mix.disconnect(); lp.disconnect(); env.disconnect(); } catch (e) { /* ignore */ }
    };
    if (voices.size > MAX_VOICES) {
      let oldest = null;
      for (const x of voices) if (!x.dead && (!oldest || x.t0 < oldest.t0)) oldest = x;
      if (oldest && oldest !== v) killVoice(oldest, ctx.currentTime);
    }
  }

  function scheduleMusic(until) {
    const now = ctx.currentTime;
    const notes = score.notes;
    for (;;) {
      if (noteIdx >= notes.length) {
        loopStart += score.beats * SECONDS_PER_BEAT + LOOP_GAP_S;
        noteIdx = 0;
      }
      const n = notes[noteIdx];
      const t = loopStart + n[0] * SECONDS_PER_BEAT;
      if (t > until) break;
      noteIdx++;
      const h = humanize(n, humRng);
      const at = Math.max(t + h.dt, now);
      if (t < now - 0.1) continue; // we were suspended / throttled; do not burst
      playNote(at, n[1] * SECONDS_PER_BEAT, n[2], h.vel);
    }
  }

  // ---- ambience ----------------------------------------------------------

  // 1 at rest; thins out quickly with speed while flying, nearly gone when fast
  function cicadaDensity() {
    if (!flying) return 1;
    const k = clamp(speed / 35, 0, 1);
    return Math.max(0.03, 0.45 * (1 - k) * (1 - k));
  }

  function breathTarget() {
    if (!flying) return 0;
    return BREATH_MAX * Math.pow(clamp((speed - 4) / 40, 0, 1), 1.4);
  }

  function updateAmbience() {
    if (!ctx) return;
    const now = ctx.currentTime;
    cicadaBus.gain.setTargetAtTime(cicadaDensity(), now, 0.9);
    breathGain.gain.setTargetAtTime(layers.breath ? breathTarget() : 0, now, 0.5);
  }

  // one higurashi call: a ~4.5 kHz tone that rises and falls, 45 Hz AM buzz,
  // plus a slow 6 Hz "ka-na-ka-na" swell
  function cicadaCall(t) {
    const dur = 3 + Math.random() * 3;
    const f0 = 4200 + Math.random() * 700;
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(f0 * 0.97, t);
    osc.frequency.linearRampToValueAtTime(f0 * 1.05, t + dur * 0.4);
    osc.frequency.linearRampToValueAtTime(f0 * 0.96, t + dur);

    const am = ctx.createGain();
    am.gain.value = 0.5;
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 45 + (Math.random() - 0.5) * 6;
    const depth = ctx.createGain();
    depth.gain.value = 0.5;
    lfo.connect(depth);
    depth.connect(am.gain);

    const peak = CICADA_PEAK * (0.7 + Math.random() * 0.6);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(peak, t + 0.6);
    env.gain.setValueAtTime(peak, t + dur - 1.0);
    env.gain.linearRampToValueAtTime(0, t + dur);
    const swell = ctx.createOscillator();
    swell.frequency.value = 5.5 + Math.random() * 1.5;
    const swellDepth = ctx.createGain();
    swellDepth.gain.value = peak * 0.3;
    swell.connect(swellDepth);
    swellDepth.connect(env.gain);

    const pan = panned((Math.random() * 2 - 1) * 0.85);
    osc.connect(am);
    am.connect(env);
    env.connect(pan);
    pan.connect(cicadaBus);
    for (const o of [osc, lfo, swell]) {
      o.start(t);
      o.stop(t + dur + 0.05);
    }
    osc.onended = () => {
      try { am.disconnect(); env.disconnect(); pan.disconnect(); depth.disconnect(); swellDepth.disconnect(); } catch (e) { /* ignore */ }
    };
    return dur;
  }

  function birdGroup(t0) {
    const n = 2 + Math.floor(Math.random() * 3);
    const pan = panned((Math.random() * 2 - 1) * 0.8);
    pan.connect(birdBus);
    const quiet = flying ? 0.5 + 0.5 * (1 - clamp(speed / 40, 0, 1)) : 1;
    let t = t0;
    const rising = Math.random() < 0.5;
    const base = 2200 + Math.random() * 1500;
    for (let i = 0; i < n; i++) {
      const d = 0.06 + Math.random() * 0.06;
      const f1 = clamp(base * (0.9 + Math.random() * 0.25), 2000, 3600);
      const f2 = clamp(rising ? f1 * (1.2 + Math.random() * 0.25) : f1 * (0.72 + Math.random() * 0.1), 2000, 4000);
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(f1, t);
      o.frequency.exponentialRampToValueAtTime(f2, t + d);
      const g = ctx.createGain();
      const pk = BIRD_PEAK * quiet * (0.8 + Math.random() * 0.4);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(pk, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.02);
      o.connect(g);
      g.connect(pan);
      o.start(t);
      o.stop(t + d + 0.05);
      o.onended = () => { try { g.disconnect(); } catch (e) { /* ignore */ } };
      t += d + 0.09 + Math.random() * 0.1;
    }
  }

  function scheduleAmbience(until) {
    const now = ctx.currentTime;
    if (layers.cicada) {
      const dens = cicadaDensity();
      for (let i = 0; i < CICADA_SLOTS; i++) {
        while (cicadaNext[i] < until) {
          const t = Math.max(cicadaNext[i], now);
          if (Math.random() < dens) {
            const d = cicadaCall(t);
            cicadaNext[i] = t + d + 1.5 + Math.random() * 7;
          } else {
            cicadaNext[i] = t + 1.5 + Math.random() * 2.5;
          }
        }
      }
    }
    if (layers.birds) {
      while (birdNext < until) {
        const t = Math.max(birdNext, now);
        birdGroup(t);
        birdNext = t + 6 + Math.random() * 14;
      }
    }
  }

  // ---- scheduler ---------------------------------------------------------

  function pumpUntil(until) {
    const now = ctx.currentTime;
    for (const v of voices) if (!v.dead && now - v.t0 > MAX_VOICE_AGE_S) killVoice(v, now);
    if (layers.music) scheduleMusic(until);
    scheduleAmbience(until);
  }

  function pump() {
    if (running) pumpUntil(ctx.currentTime + LOOKAHEAD_S);
  }

  // ---- public API --------------------------------------------------------

  function start() {
    if (!ctx) build();
    if (stopTimer) {
      clearTimeout(stopTimer);
      stopTimer = null;
    }
    const isOffline = typeof ctx.startRendering === 'function';
    const resumed = !isOffline && ctx.state !== 'running' ? ctx.resume() : null;
    if (resumed && resumed.catch) resumed.catch(() => {});
    if (running) return resumed;
    running = true;

    const now = ctx.currentTime;
    for (const v of voices) killVoice(v, now);
    loopStart = now + 0.5;
    noteIdx = 0;
    cicadaNext = [];
    for (let i = 0; i < CICADA_SLOTS; i++) cicadaNext.push(now + 0.5 + Math.random() * 5);
    birdNext = now + 3 + Math.random() * 6;

    master.gain.cancelScheduledValues(now);
    master.gain.setValueAtTime(0, now);
    master.gain.linearRampToValueAtTime(vol, now + 0.8);
    updateAmbience();

    if (!opts.manual) {
      pump();
      pumpTimer = setInterval(pump, PUMP_MS);
    }
    return resumed;
  }

  function stop() {
    if (!ctx || !running) return;
    running = false;
    if (pumpTimer) {
      clearInterval(pumpTimer);
      pumpTimer = null;
    }
    const now = ctx.currentTime;
    master.gain.cancelScheduledValues(now);
    master.gain.setValueAtTime(master.gain.value, now);
    master.gain.linearRampToValueAtTime(0, now + 1);
    if (opts.manual) return;
    stopTimer = setTimeout(() => {
      stopTimer = null;
      const t = ctx.currentTime;
      for (const v of voices) killVoice(v, t);
      if (ctx.state === 'running') ctx.suspend().catch(() => {});
    }, 1050);
  }

  function setFlying(b) {
    flying = !!b;
    updateAmbience();
  }

  function setSpeed(mps) {
    speed = Number.isFinite(mps) ? Math.max(0, mps) : 0;
    updateAmbience();
  }

  // a footstep on grit and leaf litter: a short burst of the noise through a band-pass, over a soft low thump
  function step(run = false) {
    if (!ctx || !running || !stepBuf) return;
    const t = ctx.currentTime + 0.005, dur = run ? 0.07 : 0.1, amp = (run ? 0.16 : 0.11) * (0.8 + Math.random() * 0.4);
    stepSide = -stepSide;
    const src = ctx.createBufferSource(); src.buffer = stepBuf;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1100 + Math.random() * 900; bp.Q.value = 0.9;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 170; lp.Q.value = 0.7;
    const g = ctx.createGain(), gl = ctx.createGain();
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(amp, t + 0.006); g.gain.exponentialRampToValueAtTime(0.0005, t + dur);
    gl.gain.setValueAtTime(0, t); gl.gain.linearRampToValueAtTime(amp * 2.2, t + 0.01); gl.gain.exponentialRampToValueAtTime(0.0005, t + dur * 1.4);
    const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    src.connect(bp); bp.connect(g); src.connect(lp); lp.connect(gl);
    const out = pan || ambBus; if (pan) { pan.pan.value = stepSide * 0.15; pan.connect(ambBus); }
    g.connect(out); gl.connect(out);
    src.start(t, Math.random() * 1.5, dur * 1.6); src.stop(t + dur * 1.6);
  }

  function volume(v) {
    if (v === undefined) return vol;
    vol = clamp(+v || 0, 0, 1);
    if (ctx && running) {
      const now = ctx.currentTime;
      master.gain.cancelScheduledValues(now);
      master.gain.setTargetAtTime(vol, now, 0.05);
    }
    return vol;
  }

  return {
    start,
    stop,
    setFlying,
    setSpeed,
    step,
    volume,
    // test hooks
    _pump: (until) => pumpUntil(until),
    _ctx: () => ctx,
    _score: score,
  };
}
