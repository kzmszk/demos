// Instruments and effects, written from scratch (no samples): everything the BGM and the sound effects are made of.
// All voices render one note to a mono Float32Array; `place()` mixes it into a stereo bus.
import { rng, clamp } from '../util.mjs';

const TAU = Math.PI * 2;
export const midiToHz = (n) => 440 * 2 ** ((n - 69) / 12);
export const SR = 48000;

/** Mix a mono note into a stereo bus at sample offset with gain and pan (-1..1, equal power). */
export function place(bus, mono, offset, gain = 1, pan = 0) {
  const gl = gain * Math.cos(((pan + 1) * Math.PI) / 4) * Math.SQRT2 * 0.7071;
  const gr = gain * Math.sin(((pan + 1) * Math.PI) / 4) * Math.SQRT2 * 0.7071;
  const [L, R] = bus;
  const n = Math.min(mono.length, L.length - offset);
  for (let i = Math.max(0, -offset); i < n; i++) {
    L[offset + i] += mono[i] * gl;
    R[offset + i] += mono[i] * gr;
  }
}
/** Same for a stereo note. */
export function placeStereo(bus, l, r, offset, gain = 1) {
  const n = Math.min(l.length, bus[0].length - offset);
  for (let i = Math.max(0, -offset); i < n; i++) { bus[0][offset + i] += l[i] * gain; bus[1][offset + i] += r[i] * gain; }
}
export const newBus = (seconds, sr = SR) => [new Float32Array(Math.ceil(seconds * sr)), new Float32Array(Math.ceil(seconds * sr))];

// ---- damped-sinusoid bank (a resonator per partial: 2 multiplies per sample) ------------------
function addResonator(out, amp, freq, tau, phase, sr, maxLen) {
  const th = (TAU * freq) / sr;
  const r = Math.exp(-1 / (tau * sr));
  const c1 = 2 * r * Math.cos(th), c2 = -r * r;
  let y2 = amp * Math.sin(phase), y1 = amp * r * Math.sin(th + phase);
  const n = Math.min(out.length, maxLen);
  if (n > 0) out[0] += y2;
  if (n > 1) out[1] += y1;
  for (let i = 2; i < n; i++) {
    const y = c1 * y1 + c2 * y2;
    out[i] += y;
    y2 = y1; y1 = y;
  }
}

/**
 * Piano-like note: inharmonic partials, hammer position comb, felt-like high-frequency roll-off, two-stage decay with
 * a slightly detuned second "string" for natural beating. Deliberately soft and warm – it sits under a voice.
 */
export function pianoNote(midi, vel = 0.7, dur = 1, { sr = SR, pedal = 0.4, seed = midi, bright = 1 } = {}) {
  const r = rng(seed * 7919 + Math.round(vel * 100));
  const f0 = midiToHz(midi);
  const B = clamp(0.00008 * Math.exp(0.09 * (midi - 40)), 0.00003, 0.02);
  const tauF = clamp(14 * 2 ** (-(midi - 36) / 20), 1.5, 16) * (0.55 + 0.45 * pedal + 0.15);
  const rel = 0.09 + 0.9 * pedal * pedal; // release time constant after note-off
  const total = Math.min(tauF * 5.5, dur + rel * 6 + 0.05);
  const n = Math.max(64, Math.round(total * sr));
  const out = new Float32Array(n);
  const p = 0.85 + (1 - vel) * 0.9 + (1 - bright) * 0.7;
  const K = Math.min(28, Math.floor((0.42 * sr) / f0));
  const hammer = 0.13;
  for (let k = 1; k <= K; k++) {
    const fk = k * f0 * Math.sqrt(1 + B * k * k);
    if (fk > 9500) break;
    let a = 1 / k ** p;
    a *= Math.max(0.18, Math.abs(Math.sin(Math.PI * k * hammer)) * 1.4);
    a /= 1 + (fk / (2800 * bright + 900)) ** 2; // felt
    const tk = tauF / (1 + 0.5 * (k - 1) ** 0.9);
    const ph = r() * TAU;
    // fast + slow components; the slow one is detuned a little (second string)
    addResonator(out, a * 0.62, fk, tk * 0.32, ph, sr, n);
    addResonator(out, a * 0.38, fk * (1 + 0.00035 * (1 + r())), tk, ph + 1.3, sr, n);
  }
  // hammer thump: short lowpassed noise
  const thumpLen = Math.min(n, Math.round(0.014 * sr));
  let lp = 0;
  const lpC = Math.exp(-TAU * (900 + 2500 * vel) / sr);
  for (let i = 0; i < thumpLen; i++) {
    lp = lpC * lp + (1 - lpC) * (r() * 2 - 1);
    out[i] += lp * 0.5 * vel * Math.exp(-i / (0.004 * sr));
  }
  // amplitude shaping: attack ramp, note-off release
  const atk = Math.round(0.0025 * sr), off = Math.round(dur * sr);
  const g = 0.16 + 0.84 * vel ** 1.5;
  for (let i = 0; i < n; i++) {
    let e = i < atk ? i / atk : 1;
    if (i > off) e *= Math.exp(-(i - off) / (rel * sr));
    out[i] *= e * g * 0.11;
  }
  return out;
}

/** Rhodes-like electric piano (2-operator FM) with a stereo tremolo. Returns [L, R]. */
export function epNote(midi, vel = 0.7, dur = 1, { sr = SR, seed = midi, trem = 4.6, tremDepth = 0.14 } = {}) {
  const r = rng(seed * 104729);
  const f0 = midiToHz(midi);
  const tau = clamp(3.2 * 2 ** (-(midi - 48) / 18), 0.7, 4);
  const rel = 0.16;
  const total = Math.min(tau * 5, dur + rel * 6 + 0.05);
  const n = Math.max(64, Math.round(total * sr));
  const L = new Float32Array(n), R = new Float32Array(n);
  let pc = r() * TAU, pm = r() * TAU, pt = r() * TAU;
  const atk = Math.round(0.004 * sr), off = Math.round(dur * sr);
  const I0 = 0.9 + 2.0 * vel, ph0 = r() * TAU;
  let lp = 0;
  const lpC = Math.exp(-TAU * (2600 + 1800 * vel) / sr);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    const idx = I0 * Math.exp(-t / 0.55) + 0.22;
    pc += (TAU * f0) / sr; pm += (TAU * f0) / sr; pt += (TAU * f0 * 7.02) / sr;
    let y = Math.sin(pc + idx * Math.sin(pm));
    y += 0.09 * vel * Math.exp(-t / 0.07) * Math.sin(pt);
    let e = (i < atk ? i / atk : 1) * Math.exp(-t / tau);
    if (i > off) e *= Math.exp(-(i - off) / (rel * sr));
    lp = lpC * lp + (1 - lpC) * y * e;
    const lfo = Math.sin(TAU * trem * t + ph0) * tremDepth;
    L[i] = lp * (1 + lfo) * 0.24 * (0.25 + 0.75 * vel);
    R[i] = lp * (1 - lfo) * 0.24 * (0.25 + 0.75 * vel);
  }
  return [L, R];
}

/** Soft sustained pad: detuned band-limited saws, warm lowpass, slow attack/release. Returns [L, R]. */
export function padNote(midi, vel = 0.5, dur = 4, { sr = SR, seed = midi, cutoff = 850 } = {}) {
  const r = rng(seed * 31337);
  const f0 = midiToHz(midi);
  const atk = 0.9, rel = 1.4;
  const n = Math.round((dur + rel * 3) * sr);
  const L = new Float32Array(n), R = new Float32Array(n);
  const detunes = [-0.0055, 0.0004, 0.006];
  const H = 6;
  detunes.forEach((dt, v) => {
    const buf = v === 1 ? null : (v === 0 ? L : R);
    const f = f0 * (1 + dt);
    for (let h = 1; h <= H; h++) {
      const fh = f * h;
      if (fh > 4200) break;
      const th = (TAU * fh) / sr, a = 1 / h ** 1.1;
      let c = Math.cos(r() * TAU), s = Math.sin(r() * TAU);
      const nrm = Math.hypot(c, s); c /= nrm; s /= nrm;
      const cs = Math.cos(th), sn = Math.sin(th);
      for (let i = 0; i < n; i++) {
        const y = s * a;
        if (buf) buf[i] += y; else { L[i] += y * 0.6; R[i] += y * 0.6; }
        const nc = c * cs - s * sn; s = s * cs + c * sn; c = nc;
      }
    }
  });
  // one-pole cascade lowpass + envelope
  const aC = Math.exp(-TAU * cutoff / sr);
  let l1 = 0, l2 = 0, r1 = 0, r2 = 0;
  const off = Math.round(dur * sr);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let e = Math.min(1, t / atk); e = e * e * (3 - 2 * e);
    if (i > off) e *= Math.exp(-(i - off) / (rel * sr));
    l1 = aC * l1 + (1 - aC) * L[i]; l2 = aC * l2 + (1 - aC) * l1;
    r1 = aC * r1 + (1 - aC) * R[i]; r2 = aC * r2 + (1 - aC) * r1;
    L[i] = l2 * e * 0.075 * vel; R[i] = r2 * e * 0.075 * vel;
  }
  return [L, R];
}

/** Round plucked bass (sine + soft harmonics, saturated a little so it survives small speakers). */
export function bassNote(midi, vel = 0.7, dur = 0.5, { sr = SR } = {}) {
  const f0 = midiToHz(midi);
  const tau = 0.55 + dur * 0.35, rel = 0.09;
  const n = Math.round(Math.min(tau * 5, dur + rel * 6) * sr);
  const out = new Float32Array(n);
  const off = Math.round(dur * sr), atk = Math.round(0.006 * sr);
  for (let i = 0; i < n; i++) {
    const t = i / sr, ph = TAU * f0 * t;
    let y = Math.sin(ph) + 0.32 * Math.sin(2 * ph + 0.4) * Math.exp(-t / 0.35) + 0.1 * Math.sin(3 * ph) * Math.exp(-t / 0.18);
    y = Math.tanh(y * 1.6) / 1.6;
    let e = (i < atk ? i / atk : 1) * Math.exp(-t / tau);
    if (i > off) e *= Math.exp(-(i - off) / (rel * sr));
    out[i] = y * e * 0.32 * (0.35 + 0.65 * vel);
  }
  return out;
}

/** Bell / celesta sparkle (FM, inharmonic ratio). */
export function bellNote(midi, vel = 0.6, { sr = SR, tau = 1.6, ratio = 3.51, index = 1.6 } = {}) {
  const f0 = midiToHz(midi);
  const n = Math.round(tau * 5 * sr);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    const I = index * Math.exp(-t / 0.35);
    const y = Math.sin(TAU * f0 * t + I * Math.sin(TAU * f0 * ratio * t)) * Math.exp(-t / tau)
      + 0.25 * Math.sin(TAU * f0 * 2.0 * t) * Math.exp(-t / (tau * 0.5));
    out[i] = y * (i < 48 ? i / 48 : 1) * 0.16 * vel;
  }
  return out;
}

// ---- percussion (all soft: this is a bed, not a beat) ---------------------------------------
export function kick(vel = 0.7, { sr = SR } = {}) {
  const n = Math.round(0.32 * sr), out = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, f = 44 + 95 * Math.exp(-t / 0.028);
    ph += (TAU * f) / sr;
    out[i] = (Math.sin(ph) * Math.exp(-t / 0.11) + 0.15 * Math.exp(-t / 0.004) * Math.sin(ph * 6)) * 0.55 * vel;
  }
  return out;
}
export function brushSnare(vel = 0.6, seed = 1, { sr = SR } = {}) {
  const r = rng(seed * 977), n = Math.round(0.22 * sr), out = new Float32Array(n);
  let lp = 0, hp = 0, prev = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr, x = r() * 2 - 1;
    lp += 0.42 * (x - lp);            // ~ up to 5 kHz
    hp = 0.86 * (hp + lp - prev); prev = lp; // highpass ~ 1 kHz
    out[i] = (hp * Math.exp(-t / 0.07) * 0.6 + Math.sin(TAU * 185 * t) * Math.exp(-t / 0.035) * 0.25) * vel * 0.4;
  }
  return out;
}
export function shaker(vel = 0.5, seed = 1, { sr = SR } = {}) {
  const r = rng(seed * 4241), n = Math.round(0.09 * sr), out = new Float32Array(n);
  let hp = 0, prev = 0;
  for (let i = 0; i < n; i++) {
    const x = r() * 2 - 1;
    hp = 0.7 * (hp + x - prev); prev = x;
    const t = i / sr;
    out[i] = hp * Math.exp(-t / 0.028) * (i < 60 ? i / 60 : 1) * vel * 0.16;
  }
  return out;
}

// ---- effects --------------------------------------------------------------------------------
/** RBJ biquad on a Float32Array (in place). type: lp|hp|bp|peak|lowshelf|highshelf */
export function biquad(x, type, freq, q = 0.707, gainDb = 0, sr = SR) {
  const w0 = (TAU * freq) / sr, cs = Math.cos(w0), sn = Math.sin(w0), alpha = sn / (2 * q);
  const A = 10 ** (gainDb / 40);
  let b0, b1, b2, a0, a1, a2;
  switch (type) {
    case 'lp': b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha; break;
    case 'hp': b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha; break;
    case 'bp': b0 = alpha; b1 = 0; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha; break;
    case 'peak': b0 = 1 + alpha * A; b1 = -2 * cs; b2 = 1 - alpha * A; a0 = 1 + alpha / A; a1 = -2 * cs; a2 = 1 - alpha / A; break;
    case 'highshelf': {
      const s = 2 * Math.sqrt(A) * alpha;
      b0 = A * ((A + 1) + (A - 1) * cs + s); b1 = -2 * A * ((A - 1) + (A + 1) * cs); b2 = A * ((A + 1) + (A - 1) * cs - s);
      a0 = (A + 1) - (A - 1) * cs + s; a1 = 2 * ((A - 1) - (A + 1) * cs); a2 = (A + 1) - (A - 1) * cs - s; break;
    }
    case 'lowshelf': {
      const s = 2 * Math.sqrt(A) * alpha;
      b0 = A * ((A + 1) - (A - 1) * cs + s); b1 = 2 * A * ((A - 1) - (A + 1) * cs); b2 = A * ((A + 1) - (A - 1) * cs - s);
      a0 = (A + 1) + (A - 1) * cs + s; a1 = -2 * ((A - 1) + (A + 1) * cs); a2 = (A + 1) + (A - 1) * cs - s; break;
    }
    default: throw new Error(`biquad type ${type}`);
  }
  b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const v = x[i];
    const y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = v; y2 = y1; y1 = y;
    x[i] = y;
  }
  return x;
}

/**
 * Feedback-delay-network reverb (8 lines, Hadamard mixing, damped). Input: stereo bus. Output: wet stereo.
 * rt60 in seconds; the returned wet signal is to be mixed with the dry bus by the caller.
 */
export function reverb(bus, { rt60 = 1.9, damp = 0.32, predelay = 0.018, sr = SR, size = 1 } = {}) {
  const base = [1117, 1289, 1481, 1697, 1877, 2113, 2381, 2657];
  const lens = base.map((d) => Math.round((d * size * sr) / 44100));
  const bufs = lens.map((l) => new Float32Array(l));
  const idx = new Int32Array(8);
  const g = lens.map((l) => 10 ** ((-3 * l) / (sr * rt60)));
  const lpState = new Float64Array(8);
  const n = bus[0].length;
  const wetL = new Float32Array(n), wetR = new Float32Array(n);
  const pd = Math.round(predelay * sr);
  const inGain = 0.42;
  const outL = [1, 0, 1, 0, 1, 0, 1, 0], outR = [0, 1, 0, 1, 0, 1, 0, 1];
  const v = new Float64Array(8);
  for (let i = 0; i < n; i++) {
    const src = i >= pd ? (bus[0][i - pd] + bus[1][i - pd]) * 0.5 : 0;
    for (let k = 0; k < 8; k++) v[k] = bufs[k][idx[k]];
    // fast Walsh–Hadamard (8) and normalise
    for (let h = 1; h < 8; h <<= 1) {
      for (let a = 0; a < 8; a += h << 1) {
        for (let b = a; b < a + h; b++) { const x = v[b], y = v[b + h]; v[b] = x + y; v[b + h] = x - y; }
      }
    }
    let l = 0, r = 0;
    for (let k = 0; k < 8; k++) {
      let s = v[k] * 0.35355339; // 1/sqrt(8)
      lpState[k] = lpState[k] * damp + s * (1 - damp);
      s = lpState[k] * g[k];
      bufs[k][idx[k]] = s + src * inGain * (k & 1 ? -1 : 1);
      if (++idx[k] >= lens[k]) idx[k] = 0;
      l += outL[k] ? bufs[k][idx[k]] : 0;
      r += outR[k] ? bufs[k][idx[k]] : 0;
    }
    wetL[i] = l * 0.5; wetR[i] = r * 0.5;
  }
  return [wetL, wetR];
}

/** Gentle tape-ish saturation (tanh) with makeup. */
export function saturate(bus, drive = 1.4) {
  const k = 1 / Math.tanh(drive);
  for (const ch of bus) for (let i = 0; i < ch.length; i++) ch[i] = Math.tanh(ch[i] * drive) * k / drive;
  return bus;
}

/** Peak of a stereo bus. */
export const peak = (bus) => bus.reduce((m, ch) => { let p = m; for (let i = 0; i < ch.length; i++) { const a = Math.abs(ch[i]); if (a > p) p = a; } return p; }, 0);
export const rms = (bus, a = 0, b = bus[0].length) => {
  let s = 0, c = 0;
  for (const ch of bus) for (let i = a; i < b; i++) { s += ch[i] * ch[i]; c++; }
  return Math.sqrt(s / Math.max(1, c));
};
