/* SOUND — a piano score that follows the tour (60 bpm, one movement per place), and the only natural
   sounds with a visible source: the two fountains in the square and the bells of St Peter's.
   The piano and the water are synthesised (ALOFT's string-physics piano, demos/aloft). */
import { synthKit } from './synthkit.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const BEAT = 1.0, BAR = 4 * BEAT;
const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const midi = (n) => { if (typeof n === 'number') return n; const m = /^([A-G])([#b]?)(-?\d)$/.exec(n); return 12 * (+m[3] + 1) + NOTE[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0); };
const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);
const notes = (s) => s.trim().split(/\s+/).map(midi);
const UPDN = [0, 1, 2, 3, 4, 3, 2, 1];

function compose(SEG) {
  const ev = [], peds = [];
  let base = 0, seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const at = (bar, beat = 0) => base + bar * BAR + beat * BEAT;
  const key = (t, m, v, d, lead = 0) => ev.push({ t: Math.max(0, t + lead + (rnd() - 0.5) * 0.014), m, v: clamp(v * (0.93 + 0.14 * rnd()), 0.04, 1), d: Math.max(0.08, d) });
  const pedal = (bar, bars, every = 4) => { for (let b = 0; b < bars * 4 - 1e-6; b += every) peds.push([at(bar, b) + 0.06, at(bar, b + every) - 0.03]); };
  const n = (bar, beat, nm, v, beats = 1) => key(at(bar, beat), midi(nm), v, beats * BEAT);
  const ch = (bar, beat, ns, v, beats = 4, roll = 0.02) => { const ms = notes(ns); ms.forEach((m, i) => key(at(bar, beat) + i * roll, m, v * (i === ms.length - 1 ? 1.06 : 0.84), beats * BEAT)); };
  const mel = (bar, str, v, o = {}) => {
    let b = o.beat || 0;
    for (const tok of str.replace(/\|/g, ' ').trim().split(/\s+/)) {
      const [nm, l] = tok.split(':'), len = +(l || 1);
      if (nm !== 'r') {
        const m = midi(nm) + 12 * (o.oct || 0), vv = v * (1 + 0.01 * (m - 74)) * (Math.abs(b % 4) < 1e-6 ? 1.05 : 1);
        key(at(bar, b), m, vv, len * BEAT * (o.leg ?? 1.02), -0.012);
        if (o.dbl) key(at(bar, b), m - 12, vv * 0.8, len * BEAT * (o.leg ?? 1.02), -0.005);
      }
      b += len;
    }
  };
  const fig = (bar, beat, beats, ns, step, v, o = {}) => {
    const ms = notes(ns), pat = o.pat || ms.map((_, i) => i);
    for (let k = 0, b = 0; b < beats - 1e-6; b += step, k++) {
      const acc = k % (o.group || 4) === 0 ? 1.1 : 0.95, vv = o.to !== undefined ? v + ((o.to - v) * b) / beats : v;
      key(at(bar, beat + b), ms[pat[k % pat.length]], vv * acc, (o.len ?? step * 1.5) * BEAT);
    }
  };
  const run = (bar, beat, ns, step, v0, v1) => { const ms = notes(ns); ms.forEach((m, i) => key(at(bar, beat) + i * step * BEAT, m, v0 + ((v1 - v0) * i) / Math.max(1, ms.length - 1), step * BEAT * 2.5)); };
  const go = (id) => { base = SEG[id]; };
  /* a bar of harmony: bass note, rolled chord, and an arpeggio figure over it */
  const harm = (bar, bass, chord, figN, v, o = {}) => {
    if (bass) n(bar, 0, bass, v * 1.05, o.bassLen || 4);
    if (chord) ch(bar, o.chordBeat || 0, chord, v * 0.8, o.chordLen || 4, o.roll || 0.03);
    if (figN) fig(bar, o.figBeat || 0, o.figBeats || 4, figN, o.step || 0.5, v * (o.figV || 0.8), { pat: o.pat || UPDN, len: o.len });
  };

  /* 1 — approach: D major, a hymn rising out of a low pedal */
  go('approach'); pedal(0, 9);
  n(0, 0, 'D1', 0.24, 8); fig(0, 0, 4, 'D2 A2 D3 E3 F#3', 0.5, 0.18, { pat: UPDN });
  [['D2', 'D2 A2 D3 E3 F#3'], ['F#1', 'F#2 A2 D3 E3 A3'], ['G1', 'G2 D3 F#3 A3 B3'], ['E1', 'E2 B2 D3 G3 B3'], ['G1', 'G2 D3 E3 G3 B3'], ['A1', 'A2 E3 G3 A3 C#4'], ['B1', 'B2 F#3 A3 B3 D4'], ['D2', 'D2 A2 D3 F#3 A3']]
    .forEach(([b, f], k) => harm(1 + k, b, null, f, 0.26 + 0.015 * k));
  mel(1, 'A4:2 D5:1 E5:1 | F#5:3 E5:1 | D5:1 E5:1 F#5:1 A5:1 | G5:2 F#5:2 | E5:2 D5:1 B4:1 | A4:3 r:1 | D5:2 C#5:1 B4:1 | A4:4', 0.38);

  /* 2 — the square: the answer, fuller, the melody in octaves; the bells ring in it */
  go('piazza'); pedal(0, 10);
  const PZ = [['D2', 'D3 F#3 A3', 'D2 A2 D3 F#3 A3'], ['C#2', 'C#3 E3 A3', 'C#2 A2 C#3 E3 A3'], ['B1', 'B2 D3 F#3', 'B1 F#2 B2 D3 F#3'], ['A1', 'A2 C#3 F#3', 'A1 E2 A2 C#3 F#3'],
    ['G1', 'G2 B2 D3', 'G1 D2 G2 B2 D3'], ['F#1', 'F#2 A2 D3', 'F#1 D2 A2 D3 F#3'], ['E1', 'E2 G2 B2', 'E2 B2 E3 G3 B3'], ['A1', 'A2 C#3 E3 G3', 'A1 E2 A2 C#3 G3'], ['D2', 'D3 F#3 A3', 'D2 A2 D3 F#3 A3'], ['D2', 'D3 G3 A3', 'D2 A2 D3 E3 A3']];
  PZ.forEach(([b, c, f], k) => harm(k, b, null, f, 0.36 + (k > 3 && k < 8 ? 0.06 : 0)));
  mel(0, 'F#5:2 A5:1 D6:1 | C#6:3 A5:1 | B5:2 A5:1 F#5:1 | A5:4 | G5:1 B5:1 D6:1 B5:1 | A5:3 F#5:1 | E5:1 G5:1 B5:1 G5:1 | A5:4 | D5:4', 0.5, { dbl: true });
  ch(9, 0, 'A4 D5 F#5', 0.3, 4);

  /* 3 — up the façade: G major, arpeggios climbing */
  go('facade'); pedal(0, 8);
  [['G1', 'G2 D3 G3 B3 D4 G4'], ['G1', 'G2 C3 E3 G3 C4 E4'], ['A1', 'A2 E3 G3 A3 C4 E4'], ['D2', 'D2 A2 D3 F#3 A3 D4'], ['E1', 'E2 B2 E3 G3 B3 E4'], ['C2', 'C2 G2 C3 E3 G3 C4'], ['A1', 'A2 E3 A3 C4 E4 A4'], ['D2', 'D2 A2 D3 F#3 A3 C4']]
    .forEach(([b, f], k) => harm(k, b, null, f, 0.38 + 0.02 * k, { pat: [0, 1, 2, 3, 4, 5, 4, 3], step: 0.5 }));
  mel(0, 'B4:2 D5:2 | E5:2 G5:2 | A5:3 G5:1 | F#5:4 | G5:2 B5:2 | E5:2 G5:2 | C6:3 B5:1 | A5:4', 0.48, { dbl: true });

  /* 4 — round the dome: B minor to D, broad rolled chords, the hymn in octaves */
  go('dome'); pedal(0, 9, 2);
  [['B1', 'B2 F#3 B3 D4'], ['G1', 'G2 D3 G3 B3'], ['A1', 'A2 D3 F#3 A3'], ['A1', 'A2 C#3 E3 A3'], ['B1', 'B2 D3 F#3 B3'], ['G1', 'G2 B2 D3 G3'], ['E1', 'E2 B2 D3 G3'], ['A1', 'A2 E3 G3 C#4'], ['D1', 'D2 A2 D3 F#3 A3']]
    .forEach(([b, c], k) => { n(k, 0, b, 0.5, 4); n(k, 0, midi(b) + 12, 0.42, 4); ch(k, 0, c, 0.4, 2); ch(k, 2, c, 0.34, 2); });
  mel(0, 'D5:2 F#5:1 B5:1 | B5:3 A5:1 | A5:2 F#5:1 D5:1 | E5:4 | F#5:2 D5:1 B4:1 | D5:2 B4:1 G4:1 | B4:2 E5:1 G5:1 | A5:3 C#5:1 | D5:4', 0.58, { dbl: true });
  run(8, 1, 'A5 D6 F#6 A6 D7', 0.5, 0.32, 0.22);

  /* 5 — inside: a lament at the Pietà (A minor), then a chorale that grows towards the Chair (C major) */
  go('nave'); pedal(0, 3, 2); pedal(3, 8, 2); pedal(11, 2);
  ch(0, 0, 'A1 E2 A2 C3 E3', 0.2, 4, 0.06); ch(1, 0, 'F1 C2 F2 A2 C3', 0.2, 4, 0.06); ch(2, 0, 'E1 B1 E2 G#2 B2', 0.22, 4, 0.06);
  mel(0, 'E5:2 C5:1 A4:1 | D5:2 C5:1 A4:1 | B4:4', 0.3);
  const CHO = [['C2', 'G3 C4 E4'], ['B1', 'G3 B3 D4'], ['A1', 'A3 C4 E4'], ['G1', 'G3 B3 E4'], ['F1', 'A3 C4 F4'], ['E1', 'G3 C4 E4'], ['D1', 'A3 C4 F4'], ['G1', 'G3 B3 D4']];
  CHO.forEach(([b, c], k) => { const v = 0.3 + 0.03 * k; n(3 + k, 0, b, v, 4); n(3 + k, 0, midi(b) + 12, v * 0.9, 4); ch(3 + k, 0, c, v, 2, 0.015); ch(3 + k, 2, c, v * 0.9, 2, 0.015); });
  mel(3, 'E5:2 D5:2 | D5:2 B4:2 | C5:2 E5:2 | G5:2 B4:2 | A5:2 F5:2 | G5:2 E5:2 | F5:2 D5:2 | D5:2 B4:2', 0.46, { dbl: true });
  n(11, 0, 'C1', 0.62, 8); n(11, 0, 'C2', 0.58, 8); ch(11, 0, 'G2 C3 E3 G3 C4 E4 G4 C5', 0.56, 8, 0.03);
  mel(11, 'C6:4', 0.5, { dbl: true });
  run(12, 0, 'E5 G5 C6 E6 G6 C7', 0.5, 0.3, 0.2);

  /* 6 — up into the dome: arpeggios rising through the keyboard to the lantern */
  go('cupola'); pedal(0, 7);
  [['C2 G2 C3 E3 G3 C4 E4 G4', 0.34], ['A1 E2 A2 C3 E3 A3 C4 E4', 0.36], ['F1 C2 F2 A2 C3 F3 A3 C4', 0.38], ['G1 D2 G2 B2 D3 G3 B3 D4', 0.4], ['C2 G2 C3 E3 G3 C4 E4 G4', 0.42], ['F2 C3 G3 A3 C4 G4 A4 C5', 0.36]]
    .forEach(([f, v], k) => { fig(k, 0, 4, f, 0.25, v, { pat: [0, 1, 2, 3, 4, 5, 6, 7], len: 0.6 }); n(k, 0, f.split(' ')[0], v * 1.1, 4); });
  mel(1, 'E5:4 | F5:2 A5:2 | B5:4 | C6:2 E6:2 | G6:4', 0.4);
  ch(6, 0, 'C4 G4 C5 E5 G5 C6 E6 G6', 0.3, 4, 0.05); n(6, 0, 'C7', 0.2, 4);

  /* 7 — over the gardens: G major, pastoral, lilting triplets */
  go('gardens'); pedal(0, 9);
  [['G1', 'G2 D3 G3 B3'], ['E1', 'E2 B2 E3 G3'], ['C2', 'C3 G3 C4 E4'], ['D2', 'D3 A3 D4 F#4'], ['G1', 'G2 D3 G3 B3'], ['B1', 'B2 F#3 B3 D4'], ['C2', 'C3 G3 C4 E4'], ['D2', 'D3 A3 C4 F#4'], ['G1', 'G2 D3 G3 B3']]
    .forEach(([b, f], k) => { n(k, 0, b, 0.32, 4); fig(k, 0, 4, f, 1 / 3, 0.24, { pat: [0, 1, 2, 3, 2, 1], group: 3, len: 0.7 }); });
  mel(0, 'D5:1.5 E5:0.5 D5:1 B4:1 | G4:2 B4:2 | C5:1.5 D5:0.5 E5:1 G5:1 | F#5:3 r:1 | D5:1.5 E5:0.5 D5:1 B4:1 | D5:2 F#5:2 | E5:1 G5:1 C6:1 B5:1 | A5:4 | G5:4', 0.4);

  /* 8 — the pine cone: a bright little fanfare */
  go('pigna'); pedal(0, 4);
  [['G1', 'G3 B3 D4'], ['C2', 'G3 C4 E4'], ['D2', 'F#3 A3 D4'], ['G1', 'G3 B3 D4']].forEach(([b, c], k) => { n(k, 0, b, 0.36, 4); ch(k, 0, c, 0.3, 1); ch(k, 2, c, 0.26, 1); });
  mel(0, 'G5:1 B5:1 D6:2 | E6:1 D6:1 C6:2 | B5:1 A5:1 F#5:2 | G5:4', 0.42, { leg: 0.8 });

  /* 9 — the spiral stair: sequences falling, turning, falling */
  go('momo'); pedal(0, 4, 2);
  [['E6 B5 G5 E5 B4 G4 E4 B3', 'E2'], ['E6 C6 G5 E5 C5 G4 E4 C4', 'C2'], ['E6 C6 A5 E5 C5 A4 E4 C4', 'A1'], ['D#6 B5 F#5 D#5 B4 F#4 D#4 B3', 'B1']]
    .forEach(([f, b], k) => { n(k, 0, b, 0.36, 4); fig(k, 0, 4, f, 0.25, 0.3, { len: 0.5 }); });

  /* 10 — the Octagonal Court: E minor for the Laocoön, then E major for the Apollo */
  go('ottagono'); pedal(0, 7);
  [['E1', 'E2 B2 E3 G3'], ['E1', 'E2 A2 C3 E3'], ['D#2', 'D#2 A2 B2 F#3'], ['G1', 'G2 B2 E3 G3'], ['C2', 'C2 G2 C3 E3'], ['E1', 'E2 A2 C#3 E3'], ['E1', 'E2 B2 E3 G#3']]
    .forEach(([b, f], k) => harm(k, b, null, f, 0.34 + (k === 2 ? 0.06 : 0)));
  mel(0, 'B4:1 E5:1 G5:1.5 F#5:0.5 | E5:2 C5:2 | B4:1 D#5:1 F#5:1 A5:1 | G5:4 | E5:2 G5:2 | C#5:2 E5:2 | G#5:4', 0.44, { dbl: true });

  /* 11 — Hall of the Muses: E major, quiet */
  go('muse'); pedal(0, 4);
  [['E1', 'E2 B2 E3 G#3'], ['C#2', 'C#2 G#2 C#3 E3'], ['A1', 'A2 E3 A3 C#4'], ['B1', 'B2 F#3 A3 D#4']].forEach(([b, f], k) => harm(k, b, null, f, 0.28));
  mel(0, 'G#5:2 B5:2 | E5:3 r:1 | C#6:2 A5:1 E5:1 | D#5:2 F#5:2', 0.36);

  /* 12 — the Round Hall: lifting to the oculus */
  go('rotonda'); pedal(0, 4);
  [['E1', 'E2 B2 E3 G#3 B3 E4'], ['A1', 'A2 E3 A3 C#4 E4 A4'], ['B1', 'B2 F#3 B3 D#4 F#4 B4'], ['E2', 'E3 B3 E4 G#4 B4 E5']].forEach(([b, f], k) => harm(k, b, null, f, 0.32, { pat: [0, 1, 2, 3, 4, 5, 4, 3] }));
  mel(0, 'B5:4 | C#6:4 | D#6:4 | E6:4', 0.34);

  /* 13 — Gallery of Maps: A major, walking */
  go('maps'); pedal(0, 8, 2);
  [['A1', 'A2 E3 A3'], ['G#1', 'G#2 E3 B3'], ['F#1', 'F#2 C#3 A3'], ['E1', 'E2 C#3 G#3'], ['D2', 'D3 A3 F#3'], ['C#2', 'C#3 A3 E3'], ['B1', 'B2 F#3 A3'], ['E2', 'E2 B2 D3 G#3']]
    .forEach(([b, f], k) => { fig(k, 0, 4, `${b} ${f}`, 0.5, 0.3, { pat: [0, 2, 1, 2, 0, 3, 1, 2], len: 0.6 }); });
  mel(0, 'C#5:1 E5:1 A5:1 G#5:1 | B5:2 E5:2 | A5:1 F#5:1 C#5:1 E5:1 | E5:2 G#4:2 | F#5:1 D5:1 A4:1 D5:1 | E5:2 C#5:2 | D5:1 F#5:1 A5:1 F#5:1 | G#5:2 E5:2', 0.42);

  /* 14–17 — the Raphael Rooms */
  go('costantino'); pedal(0, 3);
  [['D1', 'D2 A2 D3 F3'], ['Bb0', 'Bb1 F2 Bb2 D3'], ['A0', 'A1 E2 A2 C#3']].forEach(([b, c], k) => { n(k, 0, b, 0.5, 4); ch(k, 0, c, 0.42, 1, 0.01); ch(k, 1.5, c, 0.36, 0.5, 0.01); ch(k, 2, c, 0.4, 2, 0.01); });
  mel(0, 'D5:2 F5:1 A5:1 | D5:2 Bb4:2 | A4:1 C#5:1 E5:2', 0.5, { dbl: true });
  go('eliodoro'); pedal(0, 3);
  [['F1', 'F2 C3 F3 A3'], ['D1', 'D2 A2 D3 F3'], ['C2', 'C2 G2 C3 E3']].forEach(([b, f], k) => harm(k, b, null, f, 0.32));
  mel(0, 'A5:2 C6:2 | F5:2 D5:2 | E5:2 G5:2', 0.4);
  go('segnatura'); pedal(0, 6);
  [['Bb1', 'Bb2 F3 Bb3 D4'], ['A1', 'A2 F3 A3 C4'], ['G1', 'G2 D3 G3 Bb3'], ['Eb1', 'Eb2 Bb2 Eb3 G3'], ['F1', 'F2 D3 F3 Bb3'], ['F1', 'F2 C3 F3 A3']].forEach(([b, f], k) => harm(k, b, null, f, 0.36));
  mel(0, 'D5:2 F5:1 Bb5:1 | A5:3 F5:1 | G5:2 Bb5:1 D6:1 | C6:2 Bb5:1 G5:1 | F5:2 D5:1 Bb4:1 | C5:4', 0.48, { dbl: true });
  go('incendio'); pedal(0, 3, 2);
  [['D2', 'D3 F3 A3 D4 F4 A4'], ['D2', 'D3 G3 Bb3 D4 G4 Bb4'], ['A1', 'A2 C#3 E3 G3 A3 C#4']].forEach(([b, f], k) => { n(k, 0, b, 0.46, 4); fig(k, 0, 4, f, 0.25, 0.36, { pat: [0, 1, 2, 3, 4, 5, 4, 3], len: 0.4 }); });
  mel(0, 'A5:1 F5:1 D5:1 A5:1 | Bb5:2 G5:2 | C#6:2 A5:2', 0.48, { dbl: true });

  /* 18 — the Transfiguration: E minor turning to the dominant */
  go('pinacoteca'); pedal(0, 4);
  [['E1', 'E2 B2 E3 G3'], ['C2', 'C2 G2 C3 E3'], ['A1', 'A2 E3 A3 C4'], ['B1', 'B2 F#3 B3 D#4']].forEach(([b, f], k) => harm(k, b, null, f, 0.3));
  mel(0, 'B5:2 G5:2 | E6:2 G5:2 | C6:2 A5:1 E5:1 | F#5:4', 0.4);

  /* 19 — the Sistine Chapel: hushed; the ceiling opens (G); the touch of the fingers; the walls; the Last Judgment
     with the hymn at full strength in D */
  go('sistine'); pedal(0, 3); pedal(3, 4); pedal(7, 2); pedal(9, 3, 2); pedal(12, 6, 2);
  ch(0, 0, 'E2 B2 F#3 G3', 0.18, 4, 0.08); ch(1, 0, 'C2 G2 D3 E3', 0.18, 4, 0.08); ch(2, 0, 'D2 A2 C3 F#3', 0.2, 4, 0.08);
  mel(0, 'B5:4 | G5:4 | A5:4', 0.24);
  [['G1', 'G2 D3 G3 B3'], ['F#1', 'F#2 D3 A3 D4'], ['E1', 'E2 B2 E3 G3'], ['C2', 'C2 G2 C3 E3']].forEach(([b, f], k) => harm(3 + k, b, null, f, 0.32 + 0.02 * k));
  mel(3, 'D5:2 G5:2 | F#5:2 A5:2 | B5:2 E5:2 | E5:3 G5:1', 0.42, { dbl: true });
  n(7, 0, 'C2', 0.3, 8); ch(7, 0, 'G2 D3 E3 G3', 0.24, 8, 0.1);
  mel(7, 'D6:3 C6:0.5 B5:0.5 | A5:4', 0.34);
  n(7, 2.5, 'E7', 0.12, 3); n(8, 1, 'D7', 0.1, 3);
  [['C2', 'C2 G2 C3 E3 G3'], ['G1', 'G2 D3 G3 B3'], ['A1', 'A2 E3 A3 C4'], ['A1', 'A2 E3 G3 C#4']].forEach(([b, f], k) => harm(9 + k, b, null, f, 0.38 + 0.04 * k));
  mel(9, 'E5:1 G5:1 C6:1 B5:1 | B5:2 D5:2 | C5:1 E5:1 A5:1 G5:1 | A5:2 C#6:2', 0.46);
  const LJ = [['D1', 'D2 A2 D3 F#3 A3'], ['F#1', 'F#2 A2 D3 F#3 A3'], ['G1', 'G2 D3 F#3 B3 D4'], ['E1', 'E2 B2 D3 G3 B3'], ['A1', 'A2 E3 G3 C#4 E4'], ['D1', 'D2 A2 D3 F#3 A3']];
  LJ.forEach(([b, f], k) => { const v = 0.56 + (k === 4 ? 0.06 : 0); n(13 + k, 0, b, v, 4); n(13 + k, 0, midi(b) + 12, v * 0.95, 4); fig(13 + k, 0, 4, f, 0.5, v * 0.8, { pat: UPDN }); });
  mel(13, 'A4:2 D5:1 E5:1 | F#5:3 E5:1 | D5:1 E5:1 F#5:1 A5:1 | G5:2 F#5:2 | E5:2 D5:1 C#5:1 | D5:4', 0.74, { oct: 1, dbl: true });
  ch(17, 0, 'D4 F#4 A4 D5', 0.5, 4, 0.02);

  /* 20 — epilogue: the hymn once more, high and soft; the last chord rings out */
  go('finale'); pedal(0, 7);
  [['D2', 'D3 A3 D4 F#4'], ['B1', 'B2 F#3 B3 D4'], ['G1', 'G2 D3 G3 B3'], ['A1', 'A2 E3 A3 C#4'], ['D2', 'D3 A3 D4 F#4']].forEach(([b, f], k) => harm(k, b, null, f, 0.26));
  mel(0, 'A5:2 D6:1 E6:1 | F#6:3 E6:1 | D6:1 B5:1 G5:1 B5:1 | A5:4 | D6:4', 0.3);
  ch(5, 0, 'D1 A1 D2 A2 D3 F#3 A3 D4 F#4 A4', 0.44, 12, 0.03);
  run(5, 2, 'A4 D5 F#5 A5 D6 F#6 A6 D7', 0.375, 0.3, 0.16);
  peds.push([at(5) + 0.06, at(5) + 16]);

  peds.sort((a, b) => a[0] - b[0]);
  for (const e of ev) {
    const off = e.t + e.d;
    for (const [a, b] of peds) {
      if (a > off) break;
      if (off >= a && off < b) { if (e.t < a - 0.12 && off - a < 0.35) e.d = Math.max(0.08, a - 0.02 - e.t); else e.d = Math.max(e.d, b - e.t); break; }
    }
  }
  return ev.sort((a, b) => a.t - b.t);
}

/* bells: inharmonic church-bell partials (hum, prime, tierce, quint, nominal …) with long decays */
const BELL = [[0.5, 0.5, 9], [1.0, 0.65, 6], [1.183, 0.42, 4.5], [1.506, 0.2, 3.5], [2.0, 0.5, 3.2], [2.514, 0.16, 2.2], [2.662, 0.12, 2], [3.011, 0.12, 1.8], [4.166, 0.08, 1.2], [5.433, 0.05, 0.8]];

export const AUDIO = (() => {
  let ctx = null, master, musicBus, ambBus, revIn, epochBus = null, t0 = 0, running = false, cursor = 0, schedTimer = 0, events = [], active = {};
  const KEYS = {}, WATER = {}, KEYMAP = {}, MASTER = 0.8;
  let SEG = null, muted = false, held = false, inFree = false;
  function plan(evs) {
    let even = 0; for (const e of evs) if ((e.m - 21) % 2 === 0) even++;
    const par = even * 2 >= evs.length ? 0 : 1, need = {}, first = {};
    for (const e of evs) {
      const k = (e.m - 21) % 2 === par ? e.m : e.m - 1; KEYMAP[e.m] = k;
      const r = Math.pow(2, (e.m - k) / 12);
      need[k] = Math.max(need[k] || 0, Math.min(e.d + 1.2, 12) * r); if (first[k] === undefined) first[k] = e.t;
    }
    return Object.keys(need).map(Number).sort((a, b) => first[a] - first[b]).map((m) => ({ m, need: need[m] }));
  }
  const toBuffer = (r) => { const b = ctx.createBuffer(r.data.length, r.data[0].length, r.rate); r.data.forEach((d, c) => b.getChannelData(c).set(d)); return b; };
  function take(r) { if (r.kind) WATER[r.kind] = r; else KEYS[r.m] = r; }
  const keyBuf = (k) => { const s = KEYS[k]; if (!s) return null; if (!s.buf) s.buf = toBuffer(s); return s.buf; };
  const waterBuf = (k) => { const s = WATER[k]; if (!s) return null; if (!s.buf) s.buf = toBuffer(s); return s.buf; };
  function loadKit(jobs) {
    jobs = jobs.concat([{ water: 'fountain' }]);
    const fallback = (from) => { const K = synthKit(); let i = from; const step = () => { const t = performance.now(); while (i < jobs.length && performance.now() - t < 10) { const j = jobs[i++]; take(j.water ? K.water(j.water) : K.note(j.m, j.need)); } if (i < jobs.length) setTimeout(step, 0); }; step(); };
    try {
      const src = `const K = (${synthKit.toString()})();\nself.onmessage = (e) => { for (const j of e.data) { const r = j.water ? K.water(j.water) : K.note(j.m, j.need); self.postMessage(r, r.data.map((d) => d.buffer)); } };`;
      const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
      let got = 0; w.onmessage = (e) => { take(e.data); if (++got === jobs.length) w.terminate(); };
      w.onerror = (e) => { e.preventDefault && e.preventDefault(); w.terminate(); fallback(got); };
      w.postMessage(jobs);
    } catch (e) { fallback(0); }
  }
  function strike(e, at, off = 0) {
    const k = KEYMAP[e.m] ?? e.m, buf = keyBuf(k); if (!buf) return;
    const rate = Math.pow(2, (e.m - k) / 12), len = buf.duration / rate - off; if (len < 0.05) return;
    const src = ctx.createBufferSource(); src.buffer = buf; src.playbackRate.value = rate;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.5;
    const v2 = e.v * e.v; lp.frequency.value = Math.min(15000, hz(e.m) * (3 + 10 * v2) + 900 + 5000 * v2);
    const g = ctx.createGain(), amp = 0.05 + 0.95 * Math.pow(e.v, 1.6);
    if (off > 0) { g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(amp, at + 0.012); } else g.gain.setValueAtTime(amp, at);
    const p = ctx.createStereoPanner(); p.pan.value = clamp((e.m - 64) / 50, -0.55, 0.55);
    src.connect(lp); lp.connect(g); g.connect(p); p.connect(epochBus || musicBus);
    src.start(at, off * rate);
    const free = e.m >= 89, rest = e.d - off; let end;
    if (!free && rest < len) { const tau = 0.045 + 0.22 * clamp((72 - e.m) / 48, 0, 1), up = at + Math.max(0.03, rest); g.gain.setValueAtTime(amp, up); g.gain.setTargetAtTime(0, up, tau); end = up + tau * 7; src.stop(end); }
    else { end = at + len; src.stop(end); }
    const old = active[e.m];
    if (old && old.end > at && old.ep === epochBus) { try { old.g.gain.cancelScheduledValues(at); old.g.gain.setTargetAtTime(0, at, 0.03); old.src.stop(at + 0.25); } catch (x) { /* fine */ } }
    active[e.m] = { src, g, end, ep: epochBus };
  }
  function hall(sec) {
    const rate = ctx.sampleRate, n = Math.floor(rate * sec), b = ctx.createBuffer(2, n, rate), pre = Math.floor(0.02 * rate);
    for (let c = 0; c < 2; c++) { const d = b.getChannelData(c); let lp = 0;
      for (let i = pre; i < n; i++) { const t = (i - pre) / rate, k = 0.07 + 0.6 * Math.exp(-t * 2.0); lp += (Math.random() * 2 - 1 - lp) * k; d[i] = lp * Math.exp((-6.9 * t) / (sec * 0.85)) * Math.min(1, t / 0.008); } }
    return b;
  }
  function soundboard(sec) {
    const rate = ctx.sampleRate, n = Math.floor(rate * sec), b = ctx.createBuffer(2, n, rate);
    for (let c = 0; c < 2; c++) { const d = b.getChannelData(c);
      for (let k = 0; k < 260; k++) { const f = 70 * Math.pow(60, Math.random()), dec = 18 + f * 0.035, a = (Math.random() * 2 - 1) / Math.sqrt(1 + f / 600), w = (2 * Math.PI * f) / rate, ph = Math.random() * 6.28;
        for (let i = 0; i < n; i++) { const e = Math.exp((-dec * i) / rate); if (e < 1e-3) break; d[i] += a * e * Math.sin(w * i + ph); } } }
    return b;
  }
  function build() {
    ctx = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: 'playback' });
    master = ctx.createGain(); master.gain.value = muted ? 0 : MASTER;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 2.5; comp.attack.value = 0.02; comp.release.value = 0.3;
    const lim = ctx.createDynamicsCompressor(); lim.threshold.value = -2; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.002; lim.release.value = 0.12;
    master.connect(comp); comp.connect(lim); lim.connect(ctx.destination);
    const rev = ctx.createConvolver(); rev.buffer = hall(3.6); revIn = ctx.createGain(); revIn.gain.value = 0.5; revIn.connect(rev); rev.connect(master);
    musicBus = ctx.createGain(); musicBus.gain.value = 1;
    const body = ctx.createConvolver(); body.buffer = soundboard(0.09); const bodyG = ctx.createGain(); bodyG.gain.value = 0.55;
    musicBus.connect(master); musicBus.connect(body); body.connect(bodyG); bodyG.connect(master);
    const send = ctx.createGain(); send.gain.value = 0.46; musicBus.connect(send); send.connect(revIn);
    ambBus = ctx.createGain(); ambBus.gain.value = 1; ambBus.connect(master);
    newEpoch();
  }
  function newEpoch() {
    if (epochBus) { const old = epochBus; old.gain.setTargetAtTime(0, ctx.currentTime, 0.08); setTimeout(() => { try { old.disconnect(); } catch (e) { /* fine */ } }, 1500); }
    epochBus = ctx.createGain(); epochBus.gain.value = 1; epochBus.connect(musicBus);
  }
  function schedule(ahead = 0.45) {
    if (!running || !ctx || ctx.state !== 'running' || held || inFree) return;
    const now = ctx.currentTime - t0, horizon = now + ahead;
    while (cursor < events.length && events[cursor].t < horizon) {
      const e = events[cursor++], at = t0 + e.t;
      if (at < ctx.currentTime - 0.02) { const late = ctx.currentTime + 0.01 - at; if (late < e.d - 0.15) strike(e, ctx.currentTime + 0.01, late); continue; }
      strike(e, Math.max(at, ctx.currentTime));
    }
  }
  function seekTo(T) {
    newEpoch(); t0 = ctx.currentTime + 0.06 - T;
    let lo = 0, hi = events.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (events[m].t < T - 12) lo = m + 1; else hi = m; }
    for (cursor = lo; cursor < events.length && events[cursor].t < T; cursor++) { const e = events[cursor]; if (e.t + e.d > T + 0.25) strike(e, t0 + T, T - e.t); }
    bellsDone = new Set();
  }
  /* ---------- ambience: fountains (by distance) and the bells (a peal in the square, and at the end) ---------- */
  let fountain = null, bellsDone = new Set();
  function fountainLoop() {
    if (fountain || !WATER.fountain) return fountain;
    const s = ctx.createBufferSource(); s.buffer = waterBuf('fountain'); s.loop = true;
    const g = ctx.createGain(); g.gain.value = 0; const p = ctx.createStereoPanner();
    s.connect(g); g.connect(p); p.connect(ambBus); s.start();
    return (fountain = { s, g, p });
  }
  function bell(at, prime, v, pan) {
    const out = ctx.createStereoPanner(); out.pan.value = pan; out.connect(ambBus);
    const w = ctx.createGain(); w.gain.value = 0.35; out.connect(w); w.connect(revIn);
    for (const [r, a, dec] of BELL) {
      const o = ctx.createOscillator(); o.frequency.value = prime * r * (1 + (Math.random() - 0.5) * 0.002);
      const g = ctx.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(v * a * 0.18, at + 0.004); g.gain.exponentialRampToValueAtTime(1e-4, at + dec * 1.6);
      o.connect(g); g.connect(out); o.start(at); o.stop(at + dec * 1.6 + 0.1);
    }
    // the clapper's strike
    const n = ctx.createOscillator(); n.type = 'square'; n.frequency.value = prime * 7.1;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(v * 0.02, at); ng.gain.exponentialRampToValueAtTime(1e-4, at + 0.05); n.connect(ng); ng.connect(out); n.start(at); n.stop(at + 0.06);
  }
  const PEALS = { piazza: [[1.5, 9, 3.2]], finale: [[2, 6, 3.4]] };
  function bells(seg, lt, pos) {
    const P = PEALS[seg]; if (!P) return;
    for (const [start, count, gap] of P) for (let i = 0; i < count; i++) {
      const tt = start + i * gap, id = seg + ':' + i;
      if (bellsDone.has(id) || lt < tt - 0.3 || lt > tt + 0.5) continue;
      bellsDone.add(id);
      const d = Math.hypot(pos.x + 190, pos.y - 40, pos.z - 45), v = clamp(140 / Math.max(d, 40), 0.15, 1);
      const prime = i % 3 === 2 ? 220 : i % 2 ? 293.66 : 146.83;
      bell(ctx.currentTime + 0.03 + Math.max(0, tt - lt), prime, v, clamp((pos.y - 40) / -300, -0.5, 0.5));
    }
  }
  return {
    get muted() { return muted; },
    init(tour) {
      SEG = {}; for (const s of tour.segments) SEG[s.id] = s.t0;
      events = compose(SEG);
    },
    start() {
      try {
        if (!ctx) { build(); loadKit(plan(events)); }
        if (ctx.state === 'suspended') ctx.resume();
        running = true; clearInterval(schedTimer); schedTimer = setInterval(schedule, 40);
      } catch (e) { console.warn('audio unavailable', e); ctx = null; }
    },
    seek(T) { if (!ctx) return; if (T < 0) { inFree = true; newEpoch(); return; } inFree = false; held = false; seekTo(T); schedule(); },
    pause(p) { if (!ctx) return; p ? ctx.suspend() : ctx.resume(); },
    hold(h, T) { if (!ctx || h === held) return; held = h; if (h) newEpoch(); else if (!inFree) seekTo(T); },
    toggle() { muted = !muted; if (master) master.gain.setTargetAtTime(muted ? 0 : MASTER, ctx.currentTime, 0.1); },
    /* the tour clock follows the audio clock, smoothed */
    clock(now, T, dt) {
      if (!ctx || ctx.state !== 'running' || !running || held || inFree) return T + dt;
      let a = ctx.currentTime - t0;
      if (ctx.getOutputTimestamp) { const o = ctx.getOutputTimestamp(); if (o.contextTime && o.performanceTime) a = o.contextTime - t0 + (now - o.performanceTime) / 1000; }
      const pred = T + dt, err = a - pred;
      if (Math.abs(err) > 0.6) return a;
      return pred + clamp(err * 0.06, -0.004, 0.004);
    },
    tick(T, segId, lt) { if (!ctx) return; if (!inFree && !held) bells(segId, lt, this._pos || { x: 0, y: 0, z: 0 }); },
    listener(cam, zone) {
      if (!ctx) return;
      this._pos = cam.position;
      const f = fountainLoop(); if (!f) return;
      const p = cam.position;
      let g = 0, pan = 0;
      if (!zone) for (const fy of [60, -60]) { const d = Math.hypot(p.x, p.y - fy, p.z - 3); const gg = clamp(26 / Math.max(d, 6), 0, 1) ** 1.3 * 0.55; if (gg > g) { g = gg; pan = clamp((fy - p.y) / 60, -0.6, 0.6) * 0; } }
      f.g.gain.setTargetAtTime(g, ctx.currentTime, 0.3);
    },
    events: () => events,
    kit: () => ({ keys: Object.keys(KEYS).length, want: new Set(Object.values(KEYMAP)).size, water: Object.keys(WATER) }),
  };
})();
