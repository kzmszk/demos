// The film's soundtrack, rendered offline: the score laid on the timeline, every mark on every page given
// its sound at the moment it is made, then the room, mixed in an OfflineAudioContext.
import { SR, renderNote } from './piano.js';
import { buildScore, perform } from './score.js';
import { makeIR } from './reverb.js';
import * as FX from './sfx.js';
import { globalAt } from '../timeline.js';
import { Rng } from '../rng.js';

const SECTIONS = ['intro', 'p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'end'];

export function sectionStarts(tl) {
  return [0, ...tl.sec.map((s) => s.s0), tl.end.s0];
}

// piano notes mixed into [L, R] starting at time t0 (seconds)
export function mixSection(buf, perf, t0, seed, gain = 1) {
  const [L, R] = buf;
  perf.notes.forEach((nt, k) => {
    const s = renderNote(nt.m, nt.v, nt.damp, seed * 131 + k * 7 + nt.m);
    const pan = Math.max(-0.22, Math.min(0.26, (nt.m - 64) / 80));
    const gl = Math.cos(((pan + 1) * Math.PI) / 4) * 1.414 * gain, gr = Math.sin(((pan + 1) * Math.PI) / 4) * 1.414 * gain;
    const i0 = Math.floor((t0 + nt.t) * SR);
    const d = Math.floor(Math.abs(pan) * 0.0004 * SR); // a hair of width
    for (let i = 0; i < s.length; i++) {
      const a = i0 + i;
      if (a >= L.length) break;
      L[a + (pan > 0 ? d : 0)] += s[i] * gl;
      R[a + (pan < 0 ? d : 0)] += s[i] * gr;
    }
  });
  // the sustain pedal's soft thump
  const r = new Rng(seed);
  for (const p of perf.pedals) {
    const i0 = Math.floor((t0 + p) * SR);
    for (let i = 0; i < 0.08 * SR; i++) {
      const t = i / SR;
      const v = Math.sin(2 * Math.PI * 48 * t) * Math.exp(-t / 0.025) * 0.006 + (r.f() * 2 - 1) * Math.exp(-t / 0.01) * 0.0015;
      if (i0 + i < L.length) { L[i0 + i] += v; R[i0 + i] += v; }
    }
  }
}

// sounds for everything drawn on a page; map(tau) gives the time (s) in `buf` at which natural time tau happens
export function pageFoleyMap(buf, map, page, side, seed) {
  const r = new Rng(seed);
  const panOf = (x) => (side === 'L' ? -0.45 : 0.05) + (x / 148) * 0.4;
  for (const op of page.def.ops) {
    const g0 = map(op.start), g1 = map(op.end);
    const dur = Math.max(0.006, g1 - g0);
    const x = op.t === 'stroke' ? op.pts[0] : op.x ?? 74;
    switch (op.t) {
      case 'stroke': {
        const speed = op.len / Math.max(0.01, dur);
        const pr = op.pts[2 * 3 + 2] ?? 1;
        FX.scribble(buf, g0, dur, { medium: op.medium, speed: Math.min(3, speed / 60), pressure: 0.6 + 0.4 * pr, gain: op.medium === 'ink' ? 0.011 : op.medium === 'hard' ? 0.009 : 0.016, pan: panOf(x) }, r.int(1, 1e9));
        break;
      }
      case 'dots': {
        const n = op.pts.length / 2;
        const step = Math.max(1, Math.floor(n / 900));
        for (let k = 0; k < n; k += step) FX.tick(buf, map(op.start + ((op.end - op.start) * k) / n), op.medium === 'ink' ? 0.006 : 0.008, r.int(1, 1e9), panOf(op.pts[k * 2]));
        break;
      }
      case 'wash': FX.brush(buf, g0, Math.max(0.15, dur), r.int(1, 1e9)); break;
      case 'erase': FX.eraser(buf, g0, Math.max(0.2, dur), r.int(1, 1e9)); break;
      case 'smudge': FX.smudge(buf, g0, Math.max(0.2, dur), r.int(1, 1e9)); break;
      case 'tape': FX.tape(buf, g0, Math.max(0.35, dur), r.int(1, 1e9)); break;
      case 'tear': FX.tear(buf, g0, Math.max(0.6, dur), r.int(1, 1e9)); break;
      default: break;
    }
  }
}

export function pageFoley(buf, tl, i, page, side) {
  pageFoleyMap(buf, (tau) => globalAt(tl, i, tau), page, side, 'foley' + i);
}

// equal energy in both channels (the bass sits a little left of centre, as it does at a piano)
export function balance([L, R]) {
  let a = 0, b = 0;
  for (let i = 0; i < L.length; i++) { a += L[i] * L[i]; b += R[i] * R[i]; }
  if (!a || !b) return;
  const m = Math.sqrt((a + b) / 2);
  const ga = m / Math.sqrt(a), gb = m / Math.sqrt(b);
  for (let i = 0; i < L.length; i++) { L[i] *= ga; R[i] *= gb; }
}

// the room itself: a very low bed of pinkish air, so silence isn't digital
export function roomTone(buf, seed) {
  const r = new Rng(seed);
  const [L, R] = buf;
  let b0 = 0, b1 = 0, b2 = 0, c0 = 0, c1 = 0, c2 = 0;
  for (let i = 0; i < L.length; i++) {
    const w = r.f() * 2 - 1, v = r.f() * 2 - 1;
    b0 = 0.997 * b0 + w * 0.029591; b1 = 0.985 * b1 + w * 0.032534; b2 = 0.95 * b2 + w * 0.048056;
    c0 = 0.997 * c0 + v * 0.029591; c1 = 0.985 * c1 + v * 0.032534; c2 = 0.95 * c2 + v * 0.048056;
    L[i] += (b0 + b1 + b2) * 0.0009; R[i] += (c0 + c1 + c2) * 0.0009;
  }
}

export function filmFoley(buf, tl) {
  const ev = tl.ev;
  FX.slide(buf, ev.pencilOut[0] + 0.05, (ev.pencilOut[1] - ev.pencilOut[0]) * 0.5, 11);
  FX.snap(buf, ev.band[0] + 0.12, 12);
  FX.coverOpen(buf, ev.cover[0], ev.cover[1] - ev.cover[0], 13);
  for (let l = 0; l < 5; l++) {
    const turn = l < 4 ? tl.sec[l * 2 + 1].turn : tl.end.turn;
    FX.pageTurn(buf, turn[0], turn[1] - turn[0], 20 + l);
  }
  FX.setDown(buf, tl.end.turn[1] + 0.4 + 2.2 * 0.92, 30);
}

// everything, through the room → { L, R } Float32Arrays
export const MIX_GAIN = 0.55;

export async function renderSoundtrack(tl, pages, onProgress, opts = {}) {
  const total = tl.total;
  const n = Math.ceil(total * SR);
  const piano = [new Float32Array(n), new Float32Array(n)];
  const foley = [new Float32Array(n), new Float32Array(n)];
  const score = buildScore();
  const starts = sectionStarts(tl);
  SECTIONS.forEach((key, k) => {
    const perf = perform(score[key], 1000 + k);
    mixSection(piano, perf, starts[k], 50 + k);
    if (onProgress) onProgress(k / SECTIONS.length);
  });
  balance(piano);
  for (let i = 0; i < 9; i++) pageFoley(foley, tl, i, pages[i], tl.sec[i].side);
  filmFoley(foley, tl);
  if (opts.stems) return { piano, foley };
  // the room
  const ctx = new OfflineAudioContext(2, n, SR);
  const mk = (pair) => { const b = ctx.createBuffer(2, n, SR); b.copyToChannel(pair[0], 0); b.copyToChannel(pair[1], 1); return b; };
  const ir = makeIR(SR);
  const irb = ctx.createBuffer(2, ir[0].length, SR); irb.copyToChannel(ir[0], 0); irb.copyToChannel(ir[1], 1);
  const conv = ctx.createConvolver(); conv.normalize = false; conv.buffer = irb;
  const master = ctx.createGain(); master.gain.value = 1;
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -12; comp.knee.value = 10; comp.ratio.value = 1.7; comp.attack.value = 0.025; comp.release.value = 0.4;
  master.connect(comp); comp.connect(ctx.destination);
  const src = (buf, dry, wet, lowpass) => {
    const s = ctx.createBufferSource(); s.buffer = buf;
    let head = s;
    if (lowpass) { const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = lowpass; f.Q.value = 0.6; s.connect(f); head = f; }
    const d = ctx.createGain(); d.gain.value = dry; head.connect(d); d.connect(master);
    const w = ctx.createGain(); w.gain.value = wet; head.connect(w); w.connect(conv);
    s.start(0);
  };
  roomTone(foley, 77);
  src(mk(piano), 1, 0.42);
  src(mk(foley), 1.8, 0.12, 8500);
  const room = ctx.createGain(); room.gain.value = 1; conv.connect(room); room.connect(master);
  const out = await ctx.startRendering();
  const L = out.getChannelData(0), R = out.getChannelData(1);
  // fade the last second, then peak-normalise to -1 dBFS
  const fadeN = Math.floor(1.2 * SR);
  for (let i = 0; i < fadeN; i++) { const g = 1 - i / fadeN; L[n - fadeN + i] *= g * g; R[n - fadeN + i] *= g * g; }
  let pk = 0;
  for (let i = 0; i < n; i++) pk = Math.max(pk, Math.abs(L[i]), Math.abs(R[i]));
  const g = 0.891 / Math.max(1e-6, pk);
  for (let i = 0; i < n; i++) { L[i] *= g; R[i] *= g; }
  return { L, R, peak: pk };
}

export function wav16(L, R) {
  const n = L.length;
  const buf = new ArrayBuffer(44 + n * 4);
  const v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 4, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true); v.setUint32(24, SR, true); v.setUint32(28, SR * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true);
  w(36, 'data'); v.setUint32(40, n * 4, true);
  // TPDF dither, deterministic
  let s = 12345;
  const rnd = () => { s = (s * 1103515245 + 12345) >>> 0; return s / 4294967296; };
  for (let i = 0; i < n; i++) {
    const l = Math.round(Math.max(-1, Math.min(1, L[i])) * 32767 + (rnd() - rnd()));
    const r = Math.round(Math.max(-1, Math.min(1, R[i])) * 32767 + (rnd() - rnd()));
    v.setInt16(44 + i * 4, Math.max(-32768, Math.min(32767, l)), true);
    v.setInt16(46 + i * 4, Math.max(-32768, Math.min(32767, r)), true);
  }
  return new Uint8Array(buf);
}
