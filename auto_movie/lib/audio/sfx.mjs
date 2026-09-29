// Sound effects that follow what happens on screen. All synthesized, all quiet: they punctuate, they never lead.
import { rng } from '../util.mjs';
import { SR, bellNote, midiToHz } from './synth.mjs';

const TAU = Math.PI * 2;

/** State-variable bandpass sweeping from f0 to f1 (Hz) over the buffer. */
function sweptNoise(len, f0, f1, q, seed, sr) {
  const r = rng(seed);
  const out = new Float32Array(len);
  let low = 0, band = 0;
  for (let i = 0; i < len; i++) {
    const x = r() * 2 - 1;
    const f = f0 + (f1 - f0) * (i / len);
    const F = 2 * Math.sin((Math.PI * f) / sr);
    low += F * band;
    const high = x - low - band / q;
    band += F * high;
    out[i] = band;
  }
  return out;
}
const env = (len, a, curve, sr) => Float32Array.from({ length: len }, (_, i) => Math.min(1, i / (a * sr)) * Math.exp(-i / (curve * sr)));

export const SFX = {
  /** paper / page swish for scene changes */
  swish(seed = 1, sr = SR) {
    const len = Math.round(0.42 * sr);
    const n = sweptNoise(len, 700, 3800, 1.6, seed, sr), e = env(len, 0.05, 0.13, sr);
    return n.map((v, i) => v * e[i] * 0.55);
  },
  /** small pop for an element appearing */
  pop(seed = 1, sr = SR) {
    const len = Math.round(0.16 * sr), out = new Float32Array(len);
    let ph = 0;
    for (let i = 0; i < len; i++) {
      const t = i / sr, f = 380 + 480 * Math.min(1, t / 0.05);
      ph += (TAU * f) / sr;
      out[i] = Math.sin(ph) * Math.exp(-t / 0.045) * 0.5 * (i < 40 ? i / 40 : 1);
    }
    return out;
  },
  /** clean bell for a reveal */
  ding(seed = 1, sr = SR) {
    return bellNote(88, 0.7, { tau: 1.1, ratio: 2.76, index: 0.9, sr });
  },
  /** pair of rising chimes for "done / check" */
  chime(seed = 1, sr = SR) {
    const a = bellNote(83, 0.6, { tau: 0.9, sr }), b = bellNote(90, 0.6, { tau: 1.3, sr });
    const off = Math.round(0.11 * sr), out = new Float32Array(Math.max(a.length, b.length + off));
    a.forEach((v, i) => (out[i] += v)); b.forEach((v, i) => (out[i + off] += v));
    return out;
  },
  /** wood tick for a chart point / list item */
  tick(seed = 1, sr = SR) {
    const len = Math.round(0.09 * sr), out = new Float32Array(len);
    for (let i = 0; i < len; i++) {
      const t = i / sr;
      out[i] = (Math.sin(TAU * 1750 * t) + 0.5 * Math.sin(TAU * 3120 * t)) * Math.exp(-t / 0.012) * 0.32;
    }
    return out;
  },
  /** low soft thud for a stamped word */
  thud(seed = 1, sr = SR) {
    const r = rng(seed), len = Math.round(0.34 * sr), out = new Float32Array(len);
    let ph = 0, lp = 0;
    for (let i = 0; i < len; i++) {
      const t = i / sr, f = 52 + 60 * Math.exp(-t / 0.04);
      ph += (TAU * f) / sr;
      lp += 0.06 * ((r() * 2 - 1) - lp);
      out[i] = (Math.sin(ph) * Math.exp(-t / 0.1) + lp * 2.2 * Math.exp(-t / 0.03)) * 0.8;
    }
    return out;
  },
  /** pencil scribble: band-passed noise amplitude-modulated like strokes; `dur` seconds */
  scribble(seed = 1, sr = SR, dur = 0.45) {
    const r = rng(seed * 13);
    const len = Math.round(dur * sr);
    const n = sweptNoise(len, 2200, 3300, 2.2, seed, sr);
    const strokes = 3 + Math.floor(dur * 7);
    const out = new Float32Array(len);
    for (let i = 0; i < len; i++) {
      const x = i / len;
      const am = 0.5 + 0.5 * Math.sin(TAU * strokes * x + r() * 0.05) ** 2;
      const fade = Math.min(1, i / (0.03 * sr)) * Math.min(1, (len - i) / (0.06 * sr));
      out[i] = n[i] * am * fade * 0.5;
    }
    return out;
  },
  /** rising whoosh (counting up / build) */
  rise(seed = 1, sr = SR, dur = 0.9) {
    const len = Math.round(dur * sr);
    const n = sweptNoise(len, 300, 4200, 2.4, seed, sr);
    return n.map((v, i) => v * (i / len) ** 1.5 * Math.min(1, (len - i) / (0.05 * sr)) * 0.4);
  },
  /** three quick rising bell notes for a payoff */
  sparkle(seed = 1, sr = SR) {
    const notes = [86, 91, 95], step = Math.round(0.075 * sr);
    const parts = notes.map((m) => bellNote(m, 0.5, { tau: 0.7, sr }));
    const out = new Float32Array(step * 2 + parts[2].length);
    parts.forEach((p, k) => p.forEach((v, i) => (out[i + k * step] += v)));
    return out;
  },
};

/** Map a visual cue op to a sound effect (or null). Keep it sparse. */
export function sfxForOp(op, ctx = {}) {
  switch (op) {
    case 'scene': return { name: 'swish', gain: 0.55 };
    case 'draw': return ctx.long ? { name: 'scribble', gain: 0.35, dur: Math.min(0.9, ctx.dur || 0.5) } : null;
    case 'pop': case 'enter': return { name: 'pop', gain: 0.45 };
    case 'callout': return { name: 'pop', gain: 0.4 };
    case 'stamp': return { name: 'thud', gain: 0.6 };
    case 'chart.point': return { name: 'tick', gain: 0.5 };
    case 'chart.line': return { name: 'rise', gain: 0.32, dur: Math.min(1.6, ctx.dur || 1.2) };
    case 'steps.reveal': return { name: 'pop', gain: 0.45 };
    case 'check': return { name: 'chime', gain: 0.5 };
    case 'reveal': case 'title': return { name: 'ding', gain: 0.45 };
    case 'number': return { name: 'rise', gain: 0.28, dur: ctx.dur || 0.9 };
    case 'sparkle': return { name: 'sparkle', gain: 0.5 };
    default: return null;
  }
}

export { midiToHz };
