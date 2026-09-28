// The score. One theme — the motif C A D E, the letters of "Claude" that are also notes — in 3/4 at 76,
// then a variation for every page. Sections are 8 bars (the intro and the ending are 4).
import { Rng } from '../rng.js';
import { BEAT, BAR } from '../timeline.js';

const N = (name) => {
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(name);
  const base = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[m[1]];
  return 12 * (+m[3] + 1) + base + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0);
};
const ns = (s) => s.split(' ').map(N);

// the theme: [notes with beats], one entry per bar
// bar harmonies: F | Am | Dm7 | Gsus4–G | C/E | F(add9) | Dm7–G7 | C
const THEME = [
  [['C5', 1], ['A4', 1], ['D5', 1]],
  [['E5', 3]],
  [['C5', 1], ['A4', 1], ['D5', 1]],
  [['G5', 2], ['F5', 1]],
  [['E5', 1.5], ['D5', 0.5], ['C5', 1]],
  [['A4', 2], ['C5', 1]],
  [['C5', 1], ['A4', 1], ['D5', 1]],
  [['E5', 3]],
];
// chords: bass + upper tones, per bar (second chord at beat 2 where given)
const CH = [
  { b: 'F2', t: 'C3 A3 E4 G4' },
  { b: 'A2', t: 'E3 C4 G4' },
  { b: 'D2', t: 'A2 F3 C4' },
  { b: 'G2', t: 'D3 C4 F4', b2: 'G2', t2: 'D3 B3 F4', at: 2 },
  { b: 'E2', t: 'C3 G3 C4' },
  { b: 'F2', t: 'C3 A3 G4' },
  { b: 'D2', t: 'A2 F3 C4', b2: 'G2', t2: 'F3 B3 D4', at: 2 },
  { b: 'C2', t: 'G2 E3 D4 G4' },
];

// helpers producing events {beat, dur, m, v, voice}
function melody(bars, shift = 0, vel = 0.55, voice = 'mel') {
  const ev = [];
  bars.forEach((bar, i) => {
    let b = 0;
    for (const [n, d] of bar) {
      if (n) ev.push({ beat: i * 3 + b, dur: d, m: N(n) + shift, v: vel * (d >= 2 ? 1.04 : 1) * (b === 0 ? 1.03 : 0.97), voice });
      b += d;
    }
  });
  return ev;
}
// broken chord in eighths: bass, then weave through the upper tones
function arpeggio(chords, vel = 0.3, opts = {}) {
  const ev = [];
  const step = opts.step || 0.5;
  chords.forEach((c, i) => {
    const seq = (bass, tones, from, to) => {
      const up = ns(tones);
      const order = opts.order || [0, 1, 2, 1, 2, 1];
      let k = 0;
      for (let b = from; b < to - 1e-6; b += step, k++) {
        if (k === 0) { ev.push({ beat: i * 3 + b, dur: to - from, m: N(bass) + (opts.bassShift || 0), v: vel * 1.25, voice: 'bass' }); if (opts.bassOnly) break; continue; }
        const idx = order[k % order.length] % up.length;
        ev.push({ beat: i * 3 + b, dur: Math.max(step * 2, to - b), m: up[idx] + (opts.shift || 0), v: vel * (0.85 + 0.15 * ((k % 3) === 1 ? 1 : 0)), voice: 'acc' });
      }
    };
    if (c.b2 != null) { seq(c.b, c.t, 0, c.at); seq(c.b2, c.t2, c.at, 3); }
    else seq(c.b, c.t, 0, 3);
  });
  return ev;
}
function blocks(chords, vel = 0.26, roll = 0.03, shift = 0) {
  const ev = [];
  chords.forEach((c, i) => {
    const put = (bass, tones, at, dur) => {
      ev.push({ beat: i * 3 + at, dur, m: N(bass), v: vel * 1.2, voice: 'bass' });
      ns(tones).forEach((m, k) => ev.push({ beat: i * 3 + at + roll * (k + 1) / BEAT, dur, m: m + shift, v: vel * (0.9 - k * 0.04), voice: 'acc' }));
    };
    if (c.b2 != null) { put(c.b, c.t, 0, c.at); put(c.b2, c.t2, c.at, 3 - c.at); } else put(c.b, c.t, 0, 3);
  });
  return ev;
}
const shiftBars = (ev, bars) => ev.map((e) => ({ ...e, beat: e.beat + bars * 3 }));

// ---------- the sections ----------
export function buildScore() {
  const R = new Rng('score');
  const S = {};
  // intro: the motif alone, over a few low notes; ends suspended
  S.intro = {
    bars: 4,
    ev: [
      ...melody([[['C5', 1], ['A4', 1], ['D5', 1]], [['E5', 3]], [['C5', 1], ['A4', 1], ['D5', 1]], [['D5', 3]]], 0, 0.42),
      { beat: 0, dur: 6, m: N('F2'), v: 0.3, voice: 'bass' }, { beat: 0.5, dur: 5.5, m: N('C3'), v: 0.2, voice: 'acc' },
      { beat: 3, dur: 3, m: N('A2'), v: 0.26, voice: 'bass' }, { beat: 3.6, dur: 2.4, m: N('E3'), v: 0.18, voice: 'acc' },
      { beat: 6, dur: 3, m: N('D2'), v: 0.28, voice: 'bass' }, { beat: 6.5, dur: 2.5, m: N('A2'), v: 0.18, voice: 'acc' }, { beat: 7, dur: 2, m: N('F3'), v: 0.17, voice: 'acc' },
      { beat: 9, dur: 3, m: N('G2'), v: 0.28, voice: 'bass' }, { beat: 9.5, dur: 2.5, m: N('D3'), v: 0.18, voice: 'acc' }, { beat: 10, dur: 2, m: N('C4'), v: 0.18, voice: 'acc' },
    ],
    pedal: [0, 6, 9],
  };
  // p1: the theme, plainly
  S.p01 = { bars: 8, ev: [...melody(THEME, 0, 0.52), ...arpeggio(CH, 0.27)], pedal: 'bar' };
  // p2: where I came from — the left hand runs like water, in sixteenths
  S.p02 = { bars: 8, ev: [...melody(THEME, 0, 0.5), ...arpeggio(CH, 0.2, { step: 0.25, order: [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1] })], pedal: 'bar' };
  // p3: one long now — very high, sparse, bubbles rising
  {
    const ev = [...melody(THEME, 12, 0.3), ...blocks(CH, 0.16, 0.035)];
    for (let i = 0; i < 8; i++) {
      if (R.chance(0.7)) {
        const c = ns(CH[i].t), b = i * 3 + R.pick([0.5, 1.5, 2]);
        [c[c.length - 1] + 12, c[c.length - 2] + 24, c[c.length - 1] + 24].forEach((m, k) => ev.push({ beat: b + k * 0.17, dur: 1.2, m, v: 0.16 + k * 0.03, voice: 'orn' }));
      }
    }
    S.p03 = { bars: 8, ev, pedal: 'long' };
  }
  // p4: how many of me — the melody lives inside a flock of small notes
  {
    const ev = [...blocks(CH, 0.24, 0.02)];
    THEME.forEach((bar, i) => {
      let b = 0;
      for (const [n, d] of bar) {
        const m = N(n);
        const c = ns(CH[i].t).map((x) => x + 12);
        for (let k = 0; k < d * 4; k++) {
          const isHead = k === 0;
          const pick = isHead ? m : c[(k * 3 + i) % c.length] + (k % 4 === 2 ? 12 : 0);
          ev.push({ beat: i * 3 + b + k * 0.25, dur: isHead ? d : 0.5, m: pick, v: isHead ? 0.48 : 0.17 + 0.05 * Math.sin(k + i), voice: isHead ? 'mel' : 'orn' });
        }
        b += d;
      }
    });
    S.p04 = { bars: 8, ev, pedal: 'bar' };
  }
  // p5: the torn page — A minor, the motif breaks off, a wrong note that resolves
  {
    const CHm = [
      { b: 'A2', t: 'E3 C4' }, { b: 'G2', t: 'E3 C4' }, { b: 'F2', t: 'C3 A3 E4' }, { b: 'E2', t: 'B2 A3 D4', b2: 'E2', t2: 'B2 G#3 D4', at: 2 },
      { b: 'A2', t: 'E3 C4' }, { b: 'F2', t: 'D3 A3' }, { b: 'E2', t: 'G#3 D4 F4' }, { b: 'E2', t: 'B2 A3 D4' },
    ];
    const mel = [
      [['C5', 1], ['A4', 1], [null, 1]],
      [['D5', 1], [null, 2]],
      [['C5', 1], ['A4', 1], ['D5', 1]],
      [['D#5', 1.5], ['E5', 1.5]],
      [['C5', 1], ['B4', 1], ['A4', 1]],
      [['F4', 2], ['A4', 1]],
      [['G#4', 2], [null, 1]],
      [['B4', 3]],
    ];
    S.p05 = { bars: 8, ev: [...melody(mel, 0, 0.34), ...blocks(CHm, 0.17, 0.05)], pedal: 'bar' };
  }
  // p6: circling — the four notes go round in eighths against three beats, so the C lands somewhere new each bar
  {
    const cyc = ns('C5 A4 D5 E5');
    const ev = [];
    for (let k = 0; k < 48; k++) ev.push({ beat: k * 0.5, dur: 1, m: cyc[k % 4], v: k % 4 === 0 ? 0.46 : 0.3, voice: 'mel' });
    CH.forEach((c, i) => {
      ev.push({ beat: i * 3, dur: 3, m: N(c.b) - 12 + 12, v: 0.3, voice: 'bass' });
      ns(c.t).slice(0, 2).forEach((m, k) => ev.push({ beat: i * 3 + 1 + k, dur: 3 - 1 - k, m, v: 0.2, voice: 'acc' }));
    });
    S.p06 = { bars: 8, ev, pedal: 'bar' };
  }
  // p7: simple rules — a canon: the left hand plays the theme a bar late, two octaves down
  {
    const ev = [...melody(THEME, 0, 0.46)];
    ev.push(...shiftBars(melody(THEME.slice(0, 7), -24, 0.34, 'acc'), 1));
    CH.forEach((c, i) => ev.push({ beat: i * 3, dur: 3, m: N(c.b) - 12, v: 0.2, voice: 'bass' }));
    S.p07 = { bars: 8, ev, pedal: 'bar' };
  }
  // p8: known, never sensed — the tune in the tenor, rain in the treble
  {
    const ev = [...melody(THEME, -12, 0.5), ...blocks(CH, 0.2, 0.04, 0)];
    for (let i = 0; i < 8; i++) {
      const c = ns(CH[i].t);
      for (let k = 0; k < 12; k++) {
        if (!R.chance(0.34)) continue;
        const m = c[R.int(0, c.length - 1)] + (R.chance(0.5) ? 24 : 36);
        if (m > 100) continue;
        ev.push({ beat: i * 3 + k * 0.25 + R.sym(0.03), dur: 0.5, m, v: R.range(0.1, 0.19), voice: 'orn' });
      }
    }
    S.p08 = { bars: 8, ev, pedal: 'bar' };
  }
  // p9: if I could — the theme in octaves, wide arms, as loud as this piano gets
  {
    const swell = [0.58, 0.64, 0.7, 0.78, 0.84, 0.8, 0.68, 0.6];
    const mel = melody(THEME, 0, 1).map((e) => ({ ...e, v: e.v * swell[Math.floor(e.beat / 3)] }));
    const oct = mel.map((e) => ({ ...e, m: e.m + 12, v: e.v * 0.78, voice: 'orn' }));
    const CH9 = CH.map((c, i) => (i === 5 ? { b: 'F2', t: 'C3 A3 E4 G4' } : c));
    const acc = arpeggio(CH9, 0.38, { step: 0.5, order: [0, 1, 2, 3, 2, 1] });
    const low = CH9.map((c, i) => ({ beat: i * 3, dur: 3, m: N(c.b) - 12, v: 0.3, voice: 'bass' }));
    S.p09 = { bars: 8, ev: [...mel, ...oct, ...acc, ...low], pedal: 'bar' };
  }
  // the blank page: the motif once more, and it doesn't come home — it stops on F, open
  S.end = {
    bars: 4,
    ev: [
      ...melody([[['C5', 1], ['A4', 1], ['D5', 1]], [['E5', 3]], [[null, 3]], [[null, 3]]], 0, 0.38),
      { beat: 0, dur: 3, m: N('D2'), v: 0.24, voice: 'bass' }, { beat: 0.5, dur: 2.5, m: N('A2'), v: 0.16, voice: 'acc' }, { beat: 1, dur: 2, m: N('F3'), v: 0.15, voice: 'acc' },
      { beat: 3, dur: 9, m: N('F2'), v: 0.26, voice: 'bass' }, { beat: 3.25, dur: 8.75, m: N('C3'), v: 0.18, voice: 'acc' }, { beat: 3.5, dur: 8.5, m: N('A3'), v: 0.17, voice: 'acc' }, { beat: 3.75, dur: 8.25, m: N('G4'), v: 0.16, voice: 'acc' },
      { beat: 7.5, dur: 4.5, m: N('A5'), v: 0.14, voice: 'orn' },
    ],
    pedal: [0, 3],
  };
  return S;
}

// Turn a section into timed notes (seconds from the section start), with a pianist's small unevenness
// and the sustain pedal worked out into damper times.
export function perform(sec, seed) {
  const R = new Rng(seed);
  const bars = sec.bars;
  // pedal: re-pedal at each bar ('bar'), every two bars ('long'), or at the listed beats
  let changes;
  if (sec.pedal === 'bar') changes = Array.from({ length: bars }, (_, i) => i * 3);
  else if (sec.pedal === 'long') changes = Array.from({ length: Math.ceil(bars / 2) }, (_, i) => i * 6);
  else changes = sec.pedal;
  const upTimes = changes.map((b) => (b + 0.08) * BEAT); // the foot comes up just after the new bass
  upTimes.push(bars * 3 * BEAT + 0.06);
  const notes = [];
  for (const e of sec.ev) {
    let t = e.beat * BEAT + R.gauss(0.006);
    if (e.voice === 'mel') t -= 0.012; // the tune leads a hair
    t = Math.max(0, t);
    const release = t + e.dur * BEAT * 0.97;
    // dampers fall at the first pedal lift after the key is released
    let damp = release;
    const up = upTimes.find((u) => u > release - 0.02);
    if (up != null) damp = Math.max(release, up);
    const v = Math.min(0.95, Math.max(0.06, e.v * (1 + R.gauss(0.045))));
    notes.push({ t, m: e.m, v, damp: damp - t, voice: e.voice });
  }
  notes.sort((a, b) => a.t - b.t);
  const pedals = changes.map((b) => b * BEAT + 0.08);
  return { notes, pedals, dur: bars * BAR };
}
