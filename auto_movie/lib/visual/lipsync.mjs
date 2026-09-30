// Mouth / eye tracks for the avatars, derived from the voice timing (mora timeline) or, for providers without
// timing (Gemini), from the audio's loudness envelope. Output is a compact list of [time, state] transitions.
import { rng, round } from '../util.mjs';
import { rmsEnvelope } from '../audio/wav.mjs';

// 0 closed · 1 a · 2 i(e) · 3 o(u)
const VOWEL_SHAPE = { a: 1, i: 2, e: 2, o: 3, u: 3, I: 0, U: 0, N: 0, cl: 0, pau: 0 };
const CLOSED_CONS = new Set(['m', 'b', 'p', 'my', 'by', 'py']);

/** Mora segments → transitions [[t, shape]] (relative to the line start), min hold 2 frames. */
export function mouthFromSegs(segs, { fps = 30, speed = 1 } = {}) {
  const minHold = 2 / fps;
  const raw = [];
  for (const s of segs) {
    const t0 = s.t0 / speed, tv = s.tv / speed, t1 = s.t1 / speed;
    if (s.kind === 'pause') { raw.push([t0, 0]); continue; }
    if (s.cons && CLOSED_CONS.has(s.cons) && tv - t0 > 0.02) raw.push([t0, 0]);
    raw.push([s.cons && CLOSED_CONS.has(s.cons) ? tv : t0, VOWEL_SHAPE[s.vowel] ?? 1]);
  }
  return simplify(raw, minHold);
}

/** Loudness envelope → transitions (fallback for providers without timing). */
export function mouthFromAudio(mono, rate, { fps = 30 } = {}) {
  const env = rmsEnvelope(mono, rate, 1 / fps);
  const max = Math.max(1e-6, ...env);
  const raw = [];
  let shape = 0;
  for (let i = 0; i < env.length; i++) {
    const v = env[i] / max;
    const up = v > 0.55 ? 1 : v > 0.32 ? 2 : v > 0.14 ? 3 : 0;
    // small hysteresis: only close when clearly quiet
    if (up === 0 && v > 0.08 && shape !== 0) continue;
    if (up !== shape) { raw.push([i / fps, up]); shape = up; }
  }
  return simplify(raw, 2 / fps);
}

function simplify(raw, minHold) {
  const out = [];
  for (const [t, s] of raw) {
    if (out.length && out.at(-1)[1] === s) continue;
    if (out.length && t - out.at(-1)[0] < minHold) { out.at(-1)[1] = s; continue; } // too short: replace previous
    out.push([round(t), s]);
  }
  // merge again after replacements
  return out.filter((e, i) => i === 0 || e[1] !== out[i - 1][1]);
}

/** Blinks: random-ish but seeded; returns [[start, end], …] over [0, duration]. */
export function blinkTimes(duration, seed) {
  const r = rng(`blink:${seed}`);
  const out = [];
  let t = r.range(1.2, 3);
  while (t < duration - 0.3) {
    out.push([round(t), round(t + 0.13)]);
    if (r.chance(0.18)) out.push([round(t + 0.32), round(t + 0.45)]); // double blink
    t += r.range(2.4, 5.6);
  }
  return out;
}

/** Emotion → face state for the speaker while a line plays. */
export const FACE = {
  normal: { eyes: 'eyes-open', brows: 'brows-normal', rest: 'mouth-closed' },
  happy: { eyes: 'eyes-smile', brows: 'brows-normal', rest: 'mouth-smile' },
  surprised: { eyes: 'eyes-wide', brows: 'brows-up', rest: 'mouth-closed' },
  thinking: { eyes: 'eyes-open', brows: 'brows-worry', rest: 'mouth-closed' },
  sad: { eyes: 'eyes-open', brows: 'brows-worry', rest: 'mouth-closed' },
  emphatic: { eyes: 'eyes-open', brows: 'brows-up', rest: 'mouth-closed' },
};
