// Foley, synthesised: graphite on paper, a fineliner, a wet brush, an eraser, tape, a tearing page,
// leaves turning, the board landing, the elastic snapping, a pencil set down.
import { Rng } from '../rng.js';
import { SR } from './piano.js';

// state-variable filter (Zavalishin's TPT form: stable at any cutoff); run() returns the band-pass
class SVF {
  constructor(fc, q) { this.ic1 = 0; this.ic2 = 0; this.set(fc, q); }
  set(fc, q) {
    const g = Math.tan((Math.PI * Math.min(fc, SR * 0.49)) / SR);
    this.k = 1 / q;
    this.a1 = 1 / (1 + g * (g + this.k));
    this.a2 = g * this.a1;
    this.a3 = g * this.a2;
  }
  run(v0) {
    const v3 = v0 - this.ic2;
    const v1 = this.a1 * this.ic1 + this.a2 * v3;
    const v2 = this.ic2 + this.a2 * this.ic1 + this.a3 * v3;
    this.ic1 = 2 * v1 - this.ic1;
    this.ic2 = 2 * v2 - this.ic2;
    this.lp = v2;
    this.hp = v0 - this.k * v1 - v2;
    return v1;
  }
}

function add(buf, i0, samples, gain = 1, pan = 0) {
  const [L, R] = buf;
  const gl = gain * Math.cos(((pan + 1) * Math.PI) / 4) * 1.414, gr = gain * Math.sin(((pan + 1) * Math.PI) / 4) * 1.414;
  for (let i = 0; i < samples.length; i++) {
    const k = i0 + i;
    if (k < 0 || k >= L.length) continue;
    L[k] += samples[i] * gl; R[k] += samples[i] * gr;
  }
}

// graphite: scratchy band-limited noise plus the tick of paper tooth; ink: smoother and higher
export function scribble(buf, t0, dur, o, seed) {
  const r = new Rng(seed);
  const n = Math.max(8, Math.floor((dur + 0.012) * SR));
  const out = new Float32Array(n);
  const ink = o.medium === 'ink' || o.medium === 'sepia';
  const f1 = new SVF(ink ? 4600 : 3000 + r.range(-500, 600), ink ? 1.3 : 0.85);
  const f2 = new SVF(ink ? 7200 : 5600, 0.9);
  const body = new SVF(1100, 0.8);
  const soft = o.medium === 'soft' ? 0.65 : o.medium === 'hard' ? 1.2 : 1;
  const grainP = (ink ? 0.0012 : 0.006) * Math.min(3, o.speed || 1);
  const atk = Math.floor(0.004 * SR), rel = Math.floor(0.008 * SR);
  const tickN = Math.floor(0.003 * SR);
  for (let i = 0; i < n; i++) {
    let e = 1;
    if (i < atk) e = i / atk;
    if (i > n - rel) e = Math.max(0, (n - i) / rel);
    let x = r.f() * 2 - 1;
    if (r.f() < grainP) x += (r.f() * 2 - 1) * 5; // a grain of tooth, shaped by the same filters
    if (i < tickN) x += (r.f() * 2 - 1) * 6 * (1 - i / tickN) * (ink ? 0.4 : 1); // the point touching down
    const y = f1.run(x) * 0.8 + f2.run(x) * 0.22 * soft + body.run(x) * 0.18;
    out[i] = y * e;
  }
  add(buf, Math.floor(t0 * SR), out, (o.gain ?? 0.02) * (o.pressure ?? 1), o.pan ?? 0.2);
}

export function tick(buf, t0, gain, seed, pan = 0.2) {
  const r = new Rng(seed);
  const n = Math.floor(0.004 * SR);
  const out = new Float32Array(n);
  const f = new SVF(4200 + r.range(-800, 800), 1.2);
  for (let i = 0; i < n; i++) out[i] = f.run((r.f() * 2 - 1) * (1 - i / n)) * 1.6;
  add(buf, Math.floor(t0 * SR), out, gain, pan);
}

// brush: a soft wet swish
export function brush(buf, t0, dur, seed, gain = 0.016) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(1500, 0.7), g = new SVF(700, 1.2);
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const am = 0.55 + 0.45 * Math.sin(i / SR * 2 * Math.PI * (3.2 + r.range(0, 0.02)));
    const env = Math.sin(Math.PI * Math.min(1, t * 1.05)) ** 0.6;
    const x = r.f() * 2 - 1;
    out[i] = (f.run(x) * 0.7 + g.run(x) * 0.5) * am * env;
  }
  add(buf, Math.floor(t0 * SR), out, gain, 0.15);
}

// eraser: rubber scrubbing back and forth
export function eraser(buf, t0, dur, seed, gain = 0.03) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(1300, 1.1), lo = new SVF(260, 1.5);
  const rate = 9 + r.range(-1, 1.5);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const stroke = Math.abs(Math.sin(Math.PI * rate * t));
    const env = Math.min(1, t / 0.03) * Math.min(1, (dur - t) / 0.05);
    const x = r.f() * 2 - 1;
    out[i] = (f.run(x) + lo.run(x) * 0.6 + (r.f() < 0.002 ? (r.f() * 2 - 1) : 0)) * stroke * env;
  }
  add(buf, Math.floor(t0 * SR), out, gain, 0.2);
}

export function smudge(buf, t0, dur, seed, gain = 0.012) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(650, 0.8);
  for (let i = 0; i < n; i++) out[i] = f.run(r.f() * 2 - 1) * Math.sin(Math.PI * i / n);
  add(buf, Math.floor(t0 * SR), out, gain, 0.1);
}

// masking tape pulled off the roll, then pressed down
export function tape(buf, t0, dur, seed, gain = 0.03) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(2600, 0.9);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const rate = 70 + 60 * Math.sin(Math.PI * t);
    ph += rate / SR;
    const crack = (ph % 1) < 0.18 ? 1 : 0.25;
    const env = t < 0.7 ? Math.min(1, t / 0.05) : Math.max(0, 1 - (t - 0.7) / 0.08);
    out[i] = f.run(r.f() * 2 - 1) * crack * env;
  }
  // press: a soft thump near the end
  const i0 = Math.floor(n * 0.82);
  for (let i = 0; i < 0.06 * SR && i0 + i < n; i++) out[i0 + i] += Math.sin(2 * Math.PI * 110 * i / SR) * Math.exp(-i / (0.012 * SR)) * 0.7;
  add(buf, Math.floor(t0 * SR), out, gain, -0.1);
}

// a page torn along the spine: fibres snapping in bursts
export function tear(buf, t0, dur, seed, gain = 0.05) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(2200, 0.8), h = new SVF(5200, 1);
  let burst = 0;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    if (r.f() < 0.0022) burst = r.range(0.4, 1);
    burst *= 0.9985;
    const env = Math.min(1, t / 0.08) * (t > 0.85 ? Math.max(0, (1 - t) / 0.15) : 1);
    const x = r.f() * 2 - 1;
    const crackle = r.f() < 0.02 ? (r.f() * 2 - 1) * 2 : 0;
    out[i] = (f.run(x) * (0.35 + burst) + h.run(crackle) * 0.6) * env;
  }
  add(buf, Math.floor(t0 * SR), out, gain, 0);
}

// a leaf going over: lift crinkle, air, flutter, landing
export function pageTurn(buf, t0, dur, seed, gain = 0.065) {
  const r = new Rng(seed);
  const n = Math.floor((dur + 0.4) * SR);
  const out = new Float32Array(n);
  const air = new SVF(900, 0.6), crinkle = new SVF(3800, 1.3);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const u = t / dur;
    const lift = Math.exp(-t / 0.06) * (t < 0.2 ? 1 : 0);
    const whoosh = u < 1 ? Math.sin(Math.PI * u) ** 1.5 : 0;
    const flutter = 0.7 + 0.3 * Math.sin(2 * Math.PI * (18 + 6 * u) * t);
    const x = r.f() * 2 - 1;
    let y = air.run(x) * whoosh * flutter * 0.9 + crinkle.run(x) * (lift * 1.2 + whoosh * 0.12);
    // landing: paper slap and a soft body thump
    const tl = t - dur * 0.93;
    if (tl > 0) y += (x * 0.5 * Math.exp(-tl / 0.018) + Math.sin(2 * Math.PI * 95 * tl) * Math.exp(-tl / 0.03) * 0.8) * 0.9;
    out[i] = y;
  }
  add(buf, Math.floor(t0 * SR), out, gain, -0.25);
}

// the board swinging open: the spine creaks (stick-slip), then the cover lands on the desk
export function coverOpen(buf, t0, dur, seed, gain = 0.07) {
  const r = new Rng(seed);
  const n = Math.floor((dur + 0.5) * SR);
  const out = new Float32Array(n);
  const res = new SVF(420, 6), res2 = new SVF(1100, 4), air = new SVF(500, 0.7);
  let next = 0;
  for (let i = 0; i < n; i++) {
    const t = i / SR, u = t / dur;
    let imp = 0;
    if (u < 0.55 && i >= next) { imp = r.range(0.3, 1) * (1 - u / 0.55); next = i + Math.floor(SR / r.range(28, 60)); }
    const x = r.f() * 2 - 1;
    let y = res.run(imp * 4) * 0.5 + res2.run(imp * 3) * 0.2 + air.run(x) * (u < 1 ? Math.sin(Math.PI * u) * 0.35 : 0);
    const tl = t - dur * 0.97;
    if (tl > 0) y += (Math.sin(2 * Math.PI * 70 * tl) * Math.exp(-tl / 0.05) * 1.4 + x * Math.exp(-tl / 0.012) * 0.6);
    out[i] = y;
  }
  add(buf, Math.floor(t0 * SR), out, gain, -0.3);
}

// the elastic band let go: a snap and a slap against the board
export function snap(buf, t0, seed, gain = 0.06) {
  const r = new Rng(seed);
  const n = Math.floor(0.25 * SR);
  const out = new Float32Array(n);
  const f = new SVF(1800, 1.5);
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    const x = r.f() * 2 - 1;
    out[i] = f.run(x) * Math.exp(-t / 0.006) * 1.4 + Math.sin(2 * Math.PI * (160 - 60 * t) * t) * Math.exp(-t / 0.05) * 0.7 + Math.sin(2 * Math.PI * 85 * t) * Math.exp(-(t - 0.045) / 0.03) * (t > 0.045 ? 0.8 : 0);
  }
  add(buf, Math.floor(t0 * SR), out, gain, 0.35);
}

// the pencil sliding out of its loop
export function slide(buf, t0, dur, seed, gain = 0.02) {
  const r = new Rng(seed);
  const n = Math.floor(dur * SR);
  const out = new Float32Array(n);
  const f = new SVF(1900, 0.9);
  for (let i = 0; i < n; i++) { const u = i / n; out[i] = f.run(r.f() * 2 - 1) * Math.sin(Math.PI * u) * (0.6 + 0.4 * Math.sin(u * 40)); }
  add(buf, Math.floor(t0 * SR), out, gain, 0.4);
}

// wood on paper: a pencil set down, a little roll
export function setDown(buf, t0, seed, gain = 0.05) {
  const r = new Rng(seed);
  for (const [dt, a] of [[0, 1], [0.09, 0.45], [0.16, 0.22]]) {
    const n = Math.floor(0.05 * SR);
    const out = new Float32Array(n);
    const f = new SVF(1400 + r.range(-200, 300), 8);
    for (let i = 0; i < n; i++) out[i] = f.run(i < 30 ? (r.f() * 2 - 1) : 0) * 2 + Math.sin(2 * Math.PI * 220 * i / SR) * Math.exp(-i / (0.006 * SR)) * 0.4;
    add(buf, Math.floor((t0 + dt) * SR), out, gain * a, -0.2);
  }
}

export { add };
