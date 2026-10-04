/* SOUND — VENEZIA.
   Music: solo piano only, seven pieces that follow the scene (the string-physics piano of ALOFT / VATICANO,
   demos/aloft, demos/vatican). Natural sounds: only the ones with a visible cause — water against stone and hull, the
   oar, the listener's own footsteps, pigeons in the square, church bells — each a short granular event scattered in time.
   No noise beds, no drones. See createAudio() at the bottom for the API. */
import { synthKit } from './synthkit.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);

/* ====================================================================================================
   THE SCORE
   ==================================================================================================== */
const NOTE = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const pcOf = (s) => (NOTE[s[0]] + (s[1] === '#' ? 1 : s[1] === 'b' ? -1 : 0) + 12) % 12;
const midi = (n) => {
  if (typeof n === 'number') return n;
  const m = /^([A-G])([#b]?)(-?\d)$/.exec(n);
  if (!m) throw new Error('bad note ' + n);
  return 12 * (+m[3] + 1) + NOTE[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0);
};
const notes = (s) => s.trim().split(/\s+/).map(midi);

/* chord symbols: 'Am', 'E7', 'C/E', 'Dm7', 'Gsus4' … → pitch classes (root, third, fifth, …) and a bass */
const QUAL = {
  '': [0, 4, 7], m: [0, 3, 7], dim: [0, 3, 6], aug: [0, 4, 8], sus2: [0, 2, 7], sus4: [0, 5, 7], '5': [0, 7], '6': [0, 4, 7, 9], m6: [0, 3, 7, 9],
  '7': [0, 4, 7, 10], maj7: [0, 4, 7, 11], m7: [0, 3, 7, 10], dim7: [0, 3, 6, 9], m7b5: [0, 3, 6, 10], add9: [0, 4, 7, 14], madd9: [0, 3, 7, 14],
  '9': [0, 4, 7, 10, 14], m9: [0, 3, 7, 10, 14], maj9: [0, 4, 7, 11, 14],
};
const CHORDS = {};
function chordOf(sym) {
  let c = CHORDS[sym]; if (c) return c;
  const m = /^([A-G][#b]?)(maj7|maj9|m7b5|dim7|dim|aug|sus2|sus4|madd9|add9|m9|m7|m6|m|9|7|6|5|)(?:\/([A-G][#b]?))?$/.exec(sym);
  if (!m || !QUAL[m[2]]) throw new Error('chord? ' + sym);
  const root = pcOf(m[1]), tones = QUAL[m[2]];
  return (CHORDS[sym] = { sym, root, bass: m[3] ? pcOf(m[3]) : root, tones, pcs: tones.map((t) => (root + t) % 12) });
}
/* the pitch with pitch class p nearest to target, within [lo, hi] */
function near(p, target, lo, hi) {
  let best = null, bd = 1e9;
  for (let m = lo; m <= hi; m++) if (m % 12 === p) { const d = Math.abs(m - target); if (d < bd) { bd = d; best = m; } }
  return best;
}
function subsets(a, n) {
  if (n >= a.length) return [a.slice()];
  const out = [];
  (function rec(i, cur) { if (cur.length === n) { out.push(cur.slice()); return; } for (let k = i; k < a.length; k++) { cur.push(a[k]); rec(k + 1, cur); cur.pop(); } })(0, []);
  return out;
}
/* n chord tones inside [lo, hi] (the third is always kept), moving as little as possible from the previous voicing */
function voice(c, n, lo, hi, prev) {
  const must = c.tones.length > 2 && c.tones[1] !== 7 && c.tones[1] !== 5 && c.tones[1] !== 2 ? [c.pcs[1]] : [];
  let best = null, bc = 1e9;
  for (const s of subsets(c.pcs, n)) {
    if (!must.every((p) => s.includes(p))) continue;
    const opts = s.map((p) => { const o = []; for (let m = lo; m <= hi; m++) if (m % 12 === p) o.push(m); return o; });
    if (opts.some((o) => !o.length)) continue;
    (function rec(i, cur) {
      if (i === s.length) {
        const v = cur.slice().sort((a, b) => a - b);
        let cost = (v[v.length - 1] - v[0]) * 0.3;
        if (prev) for (let k = 0; k < v.length; k++) cost += Math.abs(v[k] - prev[Math.min(k, prev.length - 1)]);
        if (cost < bc) { bc = cost; best = v; }
        return;
      }
      for (const m of opts[i]) { if (cur.includes(m)) continue; cur.push(m); rec(i + 1, cur); cur.pop(); }
    })(0, []);
  }
  return best || s0(c, n, lo);
}
const s0 = (c, n, lo) => c.pcs.slice(0, n).map((p) => near(p, lo + 6, lo, lo + 24));
/* an open, harp-like voicing: the bass, then fifth, third, seventh (or root), ninth … each the nearest chord tone above the one
   before (a slash chord gets its root above the bass); never a second or less just above the bass */
function spread(c, base, n, hi) {
  const t = c.tones, bp = base % 12, own = bp === c.root;
  const stack = [0, 7, t[1], t.length > 3 ? t[3] % 12 : 0, t.length > 4 ? t[4] % 12 : 7, t[1] + 12, 12].map((x) => (c.root + x) % 12);
  const seq = (own ? stack.slice(1) : stack.filter((p) => p !== bp));
  const out = [base];
  for (let i = 0; i < n - 1; i++) {
    const pc = seq[i % seq.length]; let m = out[out.length - 1] + 1;
    while (m % 12 !== pc) m++;
    if (i === 0 && m - base < 5) m += 12;
    if (m > hi) m -= 12;
    out.push(m);
  }
  return out.sort((a, b) => a - b);
}

/* A score is written in beats (bar, beat); a tempo map turns beats into seconds at the end, so a phrase can
   breathe (slow(bar, factor, pause)) without touching the notes. Every key is humanised a little in time and weight. */
function Score(bpb, spb, seed = 7) {
  const ev = [], peds = [], harm = [], tf = {}, pause = {};
  let sd = seed, bars = 0;
  const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const S = { bpb, spb, ev, harm, peds, rnd, strong: [0], sub: [] };
  S.length = (n) => { bars = n; };
  S.slow = (bar, f, extra = 0) => { tf[bar] = f; if (extra) pause[bar] = extra; };
  S.at = (bar, beat = 0) => bar * bpb + beat;
  /* one key; b in beats from the start; v 0..1; db beats; lead seconds (melody a hair ahead of the beat) */
  S.key = (b, m, v, db, lead = 0, tag = 0) => { ev.push({ b, m: midi(m), v, db, lead, tag }); };
  S.n = (bar, beat, nm, v, db = 1, tag = 0) => S.key(bar * bpb + beat, nm, v, db, 0, tag);
  /* a chord rolled upward, its top voice a touch louder */
  S.ch = (bar, beat, names, v, db = 4, roll = 0.02, tag = 0) => { const ms = typeof names === 'string' ? notes(names) : names; ms.forEach((m, i) => S.key(bar * bpb + beat, m, v * (i === ms.length - 1 ? 1.06 : 0.84), db, i * roll, tag)); };
  /* a melody 'A4:2 D5:1 r:1 …' (durations in beats; r rests; x:1@1.2 scales the weight; 'x a grace note before x);
     o.oct moves it, o.dbl adds the octave below, o.up the octave above, o.v1 shapes a swell over the line */
  S.mel = (bar, str, v, o = {}) => {
    let b = bar * bpb + (o.beat || 0), grace = null;
    const toks = str.replace(/\|/g, ' ').trim().split(/\s+/), total = toks.reduce((a, t) => a + (t[0] === "'" ? 0 : +((t.split(':')[1] || '1').split('@')[0])), 0), b0 = b;
    for (const tok of toks) {
      if (tok[0] === "'") { grace = tok.slice(1); continue; }
      const [nm, rest] = tok.split(':'), [l, vm] = (rest || '1').split('@'), len = +l;
      if (nm !== 'r') {
        const m = midi(nm) + 12 * (o.oct || 0), pos = (b - Math.floor(b / bpb) * bpb);
        const acc = S.strong.some((p) => Math.abs(pos - p) < 1e-6) ? 1.06 : S.sub.some((p) => Math.abs(pos - p) < 1e-6) ? 1.03 : 1;
        let vv = v * (vm ? +vm : 1) * acc * (1 + 0.008 * (m - 74));
        if (o.v1 !== undefined) vv *= lerp(1, o.v1, (b - b0) / Math.max(1, total));
        const lead = o.lead ?? -0.012, db = len * (o.leg ?? 1.02);
        S.key(b, m, vv, db, lead, o.tag || 1);
        if (o.dbl) S.key(b, m - 12, vv * 0.78, db, lead + 0.006, 2);
        if (o.up) S.key(b, m + 12, vv * 0.5, db, lead + 0.004, 4);
        if (grace) { S.key(b, midi(grace) + 12 * (o.oct || 0), vv * 0.62, 0.35, lead - 0.085, 4); grace = null; }
      }
      b += len;
    }
  };
  /* the notes of ns in the order pat, one every `step` beats, over `beats` beats */
  S.fig = (bar, beat, beats, ns, step, v, o = {}) => {
    const ms = typeof ns === 'string' ? notes(ns) : ns, pat = o.pat || ms.map((_, i) => i);
    for (let k = 0, b = 0; b < beats - 1e-6; b += step, k++) {
      const acc = k % (o.group || 4) === 0 ? 1.1 : 0.95, vv = o.to !== undefined ? v + ((o.to - v) * b) / beats : v;
      S.key(bar * bpb + beat + b, ms[pat[k % pat.length]], vv * acc, (o.len ?? step * 1.5), 0, o.tag || 3);
    }
  };
  S.run = (bar, beat, ns, step, v0, v1, tag = 3) => { const ms = notes(ns); ms.forEach((m, i) => S.key(bar * bpb + beat + i * step, m, v0 + ((v1 - v0) * i) / Math.max(1, ms.length - 1), step * 2.5, 0, tag)); };
  /* harmony bookkeeping: the pedal follows it, and the checks read it */
  S.chord = (bar, beat, len, sym) => { chordOf(sym); harm.push({ b0: bar * bpb + beat, b1: bar * bpb + beat + len, sym }); };
  S.ped = (b0, b1) => { peds.push([b0, b1]); };
  S.pedBars = (bar, n, every = bpb) => { for (let b = 0; b < n * bpb - 1e-6; b += every) peds.push([bar * bpb + b, bar * bpb + Math.min(n * bpb, b + every)]); };
  /* pedal changes with the chords: down just after each change, up just before the next */
  S.autoPed = () => {
    const h = harm.slice().sort((a, b) => a.b0 - b.b0), out = [];
    const same = (a, b) => { const p = chordOf(a), q = chordOf(b); return p.root === q.root && p.bass === q.bass; };
    for (const x of h) { const last = out[out.length - 1]; if (last && same(last.sym, x.sym) && Math.abs(last.b1 - x.b0) < 1e-6) last.b1 = x.b1; else out.push({ b0: x.b0, b1: x.b1, sym: x.sym }); }
    for (const x of out) peds.push([x.b0, x.b1]);
  };
  /* phrase shape: every `period` bars from `from` to `to`, the middle bars a little quicker (breathe) and the middle of the
     phrase a little louder (arc); an explicit slow() is never overridden */
  const arcs = [], breaths = [];
  S.breathe = (from, to, period, depth) => { breaths.push([from, to, period, depth]); };
  S.arc = (from, to, period, depth) => { arcs.push([from * bpb, to * bpb, period * bpb, depth]); };
  S.finish = () => {
    for (const [from, to, per, d] of breaths) for (let b = from; b < to; b++) if (tf[b] === undefined) tf[b] = 1 - 0.5 * d * Math.cos((2 * Math.PI * ((b - from + 0.5) % per)) / per);
    for (const e of ev) for (const [a, z, per, d] of arcs) if (e.b >= a && e.b < z) e.v *= 1 + d * (Math.sin((Math.PI * ((e.b - a) % per)) / per) - 2 / Math.PI) * (e.tag === 1 ? 1 : 0.5);
    let maxB = bars * bpb; for (const e of ev) maxB = Math.max(maxB, e.b + e.db);
    const nb = Math.ceil(maxB / bpb) + 2, cum = [0];
    for (let i = 0; i < nb; i++) cum.push(cum[i] + (bpb * spb) / (tf[i] || 1) + (pause[i] || 0));
    const T = (b) => { const i = Math.max(0, Math.min(nb - 1, Math.floor(b / bpb + 1e-9))); return cum[i] + ((b - i * bpb) * spb) / (tf[i] || 1); };
    const out = ev.map((e) => ({ b: e.b, t: Math.max(0, T(e.b) + e.lead + (rnd() - 0.5) * 0.012), m: e.m, v: clamp(e.v * (0.93 + 0.14 * rnd()), 0.04, 1), d: Math.max(0.08, T(e.b + e.db) - T(e.b)), tag: e.tag }));
    const P = peds.map(([a, b]) => [T(a) + 0.06, T(b) - 0.03]).sort((a, b) => a[0] - b[0]);
    /* the pedal: a key let go while it is down keeps sounding until it comes up; a key from before a change that only
       overlaps it a moment is let go first, as a pianist does, so the new pedal does not catch it */
    for (const e of out) {
      const off = e.t + e.d;
      for (const [a, b] of P) {
        if (a > off) break;
        if (off >= a && off < b) { if (e.t < a - 0.12 && off - a < 0.35) e.d = Math.max(0.08, a - 0.02 - e.t); else e.d = Math.max(e.d, b - e.t); break; }
      }
    }
    out.sort((a, b) => a.t - b.t);
    const hs = harm.map((h) => ({ t0: T(h.b0), t1: T(h.b1), sym: h.sym })).sort((a, b) => a.t0 - b.t0);
    return { events: out, len: T(bars * bpb), harm: hs, bpb, spb, T };
  };
  return S;
}

/* ---------- 1  BARCAROLA — the gondola. 6/8, A minor, an eighth = 0.4 s so that a bar is exactly the gondolier's stroke
   (2.4 s); the left hand rocks (bass, two chord tones up | bass, the same two falling), the tune sings in long-short
   pairs and falls in thirds; a major-key episode in C climbs to a high singing line and comes back through E7. ---------- */
function compBarcarola(pass) {
  const S = Score(6, 0.4, 11 + pass * 5);
  S.strong = [0]; S.sub = [3];
  let pb = 45, pu = null;
  /* the rocking left hand for one bar: halves = the two half-bar chords */
  const rock = (bar, halves, v, o = {}) => {
    const c1 = chordOf(halves[0]), c2 = chordOf(halves[1]);
    S.chord(bar, 0, 3, halves[0]); S.chord(bar, 3, 3, halves[1]);
    const b1 = near(c1.bass, pb, 38, 52);
    let b2;
    if (halves[0] === halves[1]) {
      /* the same chord twice: the second bass is its fifth (or, over a slash bass, its root or fifth), nearest below */
      let best = null, bd = 1e9;
      for (const p of [c1.root, (c1.root + 7) % 12]) if (p !== c1.bass) { const m = near(p, b1 - 5, 36, 52), d = Math.abs(m - (b1 - 5)); if (d < bd) { bd = d; best = m; } }
      b2 = best ?? b1;
    } else b2 = near(c2.bass, b1, 38, 52);
    const u1 = voice(c1, o.n || 2, 55, 69, pu), u2 = halves[0] === halves[1] ? u1 : voice(c2, o.n || 2, 55, 69, u1);
    pb = b2; pu = u2;
    const b0 = bar * 6, k = (m, p, vv, d) => S.key(b0 + p, m, vv, d, 0, p % 3 === 0 ? 2 : 3);
    k(b1, 0, v * 1.08, 3); k(u1[0], 1, v * 0.7, 2); k(u1[u1.length - 1], 2, v * 0.64, 1);
    k(b2, 3, v * 0.92, 3); k(u2[u2.length - 1], 4, v * 0.7, 2); k(u2[0], 5, v * 0.62, 1);
    if (o.full) { const t = voice(c1, 3, 55, 72, u1); k(t[t.length - 1], 2, v * 0.55, 1); }
  };
  const bar = (i, hs, v, o) => rock(i, hs, v, o);
  const AM = ['Am', 'Am'];
  /* intro: the boat pushes off */
  bar(0, AM, 0.25); bar(1, ['Am', 'E7'], 0.27);
  S.mel(1, 'r:3 B4:1 C5:1 D5:1', 0.33);
  /* A — the tune, in Am (bars 2–9): down by thirds, up through C, the diminished fall to the dominant, home */
  const AH = [AM, ['Am7/G', 'Am7/G'], ['Dm/F', 'Dm/F'], ['E', 'E7'], AM, ['C', 'C'], ['Dm', 'E7'], AM];
  const AT = ['E5:3 D5:1 C5:1 B4:1', 'C5:3 A4:3', 'D5:3 F5:1 E5:1 D5:1', 'G#4:3 B4:3', 'E5:3 D5:1 C5:1 B4:1', 'C5:3 E5:3', 'F5:2 D5:1 B4:2 G#4:1', 'A4:6'];
  const ATL = ['C5:3 B4:1 A4:1 G4:1', 'A4:3 E4:3', 'A4:3 D5:1 C5:1 B4:1', 'E4:3 G#4:3', 'C5:3 B4:1 A4:1 G4:1', 'E4:3 G4:3', 'D5:2 B4:1 G#4:2 E4:1', 'E4:6'];
  const playA = (b0, v, how) => {
    AH.forEach((h, i) => bar(b0 + i, h, v * (0.9 + 0.012 * i), { full: how === 'oct' && i > 3 }));
    AT.forEach((t, i) => {
      if (how === 'oct') S.mel(b0 + i, t, v * 1.5, { up: true });
      else S.mel(b0 + i, t, v * 1.5);
      if (how === 'thirds') S.mel(b0 + i, ATL[i], v * 1.1, { lead: -0.004 });
    });
  };
  playA(2, 0.34, 'plain');
  /* A' — the same, an octave brighter */
  playA(10, 0.36, pass ? 'thirds' : 'oct');
  /* B — C major (bars 18–25): the lilt climbs to a high singing line; ii–V turns it back to A minor */
  const BH = [['C', 'C'], ['G', 'G'], ['Am', 'Am'], ['F', 'F'], ['C', 'C'], ['G/B', 'G/B'], ['Dm', 'E7'], AM];
  const BT = ['E5:3 G5:2 E5:1', 'D5:3 B4:2 D5:1', 'C5:3 E5:2 A5:1', 'A5:3 G5:2 F5:1', 'E5:3 G5:2 C6:1', 'D6:3 B5:2 G5:1', 'F5:2 D5:1 B4:2 G#4:1', 'A4:3 r:3'];
  const BTL = ['C5:3 E5:2 C5:1', 'B4:3 G4:2 B4:1', 'A4:3 C5:2 C5:1', 'F5:3 E5:2 D5:1', 'C5:3 E5:2 G5:1', 'B5:3 G5:2 D5:1', 'D5:2 B4:1 G#4:2 E4:1', 'E4:3 r:3'];
  const playB = (b0, v, how) => {
    BH.forEach((h, i) => bar(b0 + i, h, v * (0.92 + 0.01 * i), { full: i === 4 || i === 5 }));
    BT.forEach((t, i) => { S.mel(b0 + i, t, v * 1.45 * (i === 5 ? 1.08 : 1), how === 'oct' ? { up: true } : {}); if (how === 'thirds') S.mel(b0 + i, BTL[i], v * 1.05, { lead: -0.004 }); });
  };
  playB(18, 0.36, pass ? 'oct' : 'plain');
  /* A'' — the return, in thirds (a duet) */
  playA(26, 0.32, pass ? 'oct' : 'thirds');
  /* B' — the climb again, in thirds */
  playB(34, 0.37, pass ? 'plain' : 'thirds');
  /* the end: the first half of the tune and the cadence, then silence for the rocking to carry on */
  bar(42, AH[0], 0.3); bar(43, AH[1], 0.29); bar(44, AH[6], 0.29); bar(45, AM, 0.27);
  S.mel(42, AT[0], 0.44); S.mel(43, AT[1], 0.42); S.mel(44, AT[6], 0.4); S.mel(45, 'A4:6', 0.36, { dbl: true });
  S.mel(42, ATL[0], 0.3, { lead: -0.004 }); S.mel(43, ATL[1], 0.28, { lead: -0.004 }); S.mel(44, ATL[6], 0.28, { lead: -0.004 });
  S.length(46);
  /* the pedal changes with every half bar, so that a falling tune's passing notes do not pile up in it */
  for (let b = 0; b < 46; b++) for (let h = 0; h < 2; h++) S.ped(b * 6 + h * 3, b * 6 + h * 3 + 3);
  S.arc(2, 42, 4, 0.2);                         /* (the tempo is never bent: the bar is the oar's stroke) */
  return S.finish();
}

/* ---------- 2  PASSEGGIATA — a stroll in the morning. G major, 4/4, 80 to the quarter. A light stride in the left hand
   (bass, chord, bass, chord), a tune that keeps to the notes of the chord and lets them turn; an episode in D major that
   walks up the scale; a singing one in E minor that comes home through D7. ---------- */
function compPasseggiata(pass) {
  const S = Score(4, 0.75, 21 + pass * 3);
  S.strong = [0, 2]; S.sub = [1, 3];
  let pb = 43, pu = null;
  const stride = (bar, halves, v, o = {}) => {
    const b0 = bar * 4, same = halves[0] === halves[1];
    for (let h = 0; h < 2; h++) {
      const sym = halves[h], c = chordOf(sym); S.chord(bar, h * 2, 2, sym);
      let bass = near(c.bass, pb, 36, 52);
      if (same && h === 1) bass = near((c.bass + 7) % 12, pb - 5, 36, 52);
      pb = bass;
      const u = voice(c, 3, o.lo || 55, o.hi || 69, pu); pu = u;
      S.key(b0 + h * 2, bass, v * (h ? 0.9 : 1.05), 1.4, 0, 2);
      u.forEach((m, i) => S.key(b0 + h * 2 + 1, m, v * 0.6 * (i === u.length - 1 ? 1.06 : 0.9), 0.8, i * 0.006 + (h ? 0 : -0.01), 3));
      if (o.ping && h === 1) S.key(b0 + 3.5, u[u.length - 1] + 12, v * 0.38, 0.5, 0, 3);
    }
  };
  /* intro: a little rising arpeggio, and the walk begins */
  S.fig(0, 0, 4, 'G3 D4 G4 B4 D5 G5 B5 D6', 0.5, 0.24, { pat: [0, 1, 2, 3, 4, 5, 6, 7], len: 0.8 });
  S.ch(1, 0, 'G2 D3 G3 B3', 0.28, 3, 0.03); S.n(1, 0, 'G5', 0.3, 3); S.chord(0, 0, 4, 'G'); S.chord(1, 0, 4, 'G');
  /* A — the stroll (bars 2–9): I – vi7 – ii7 – V7 | I – IVmaj7 – ii7 V7 – I */
  const AH = [['G', 'G'], ['Em7', 'Em7'], ['Am7', 'Am7'], ['D7', 'D7'], ['G', 'G'], ['Cmaj7', 'Cmaj7'], ['Am7', 'D7'], ['G', 'G']];
  const AT = ['B4:1.5 D5:0.5 G5:2', 'G5:1.5 E5:0.5 B4:2', 'C5:1.5 E5:0.5 A5:2', 'A5:1.5 F#5:0.5 D5:1 C5:1', 'B4:1.5 D5:0.5 G5:1 B5:1', 'C6:1.5 B5:0.5 G5:2', 'A5:1 E5:1 F#5:1 A5:1', 'G5:3 r:1'];
  const ATo = ["B4:1.5 D5:0.5 'F#5 G5:2", "'A5 G5:1.5 E5:0.5 B4:2", "C5:1.5 E5:0.5 'G#5 A5:2", 'A5:1.5 F#5:0.5 D5:1 C5:1', "B4:1.5 D5:0.5 'F#5 G5:1 B5:1", "C6:1.5 B5:0.5 'A5 G5:2", 'A5:1 E5:1 F#5:1 A5:1', 'G5:3 r:1'];
  const playA = (b0, v, how) => {
    AH.forEach((h, i) => stride(b0 + i, h, v * (0.92 + 0.012 * i), { ping: how === 'orn' && i % 2 === 1 }));
    (how === 'orn' ? ATo : AT).forEach((t, i) => S.mel(b0 + i, t, v * 1.55, how === 'up' ? { up: true } : {}));
    S.slow(b0 + 7, 0.93);
  };
  playA(2, 0.3, 'plain');
  playA(10, 0.31, pass ? 'up' : 'orn');
  /* B — D major (bars 18–25): the scale walks up, falls back; a second time to the tonic */
  const BH = [['D', 'D'], ['D', 'A'], ['Bm', 'Bm'], ['A', 'A'], ['D', 'D'], ['G', 'G'], ['Em7', 'A7'], ['D', 'D']];
  const BT = ['A4:1 B4:0.5 C#5:0.5 D5:1 E5:1', 'F#5:1 E5:0.5 D5:0.5 C#5:2', 'B4:1 C#5:0.5 D5:0.5 F#5:1 D5:1', 'E5:1.5 C#5:0.5 A4:2', 'A4:1 B4:0.5 C#5:0.5 D5:1 E5:1', 'G5:1.5 F#5:0.5 E5:1 D5:1', 'E5:1 G5:1 C#5:1 E5:1', 'D5:3 r:1'];
  BH.forEach((h, i) => stride(18 + i, h, 0.3 * (0.93 + 0.01 * i), { lo: 52, hi: 66, ping: i % 2 === 0 }));
  BT.forEach((t, i) => S.mel(18 + i, t, 0.31 * 1.5, { v1: i === 7 ? 0.9 : 1 }));
  S.slow(25, 0.93);
  /* C — E minor (bars 26–33): sung, legato; it arrives on D7 */
  const CH = [['Em', 'Em'], ['B7', 'B7'], ['Em', 'Em'], ['Am', 'Am'], ['C', 'C'], ['Am7', 'Am7'], ['D7', 'D7'], ['D7', 'D7']];
  const CT = ['G5:2 B5:1 A5:0.5 G5:0.5', 'F#5:2 D#5:1 F#5:1', 'G5:1.5 F#5:0.5 E5:2', 'A5:2 C6:1 B5:1', 'C6:2 G5:1 E5:1', 'E5:2 C5:1 A4:1', 'A4:1 D5:1 F#5:1 A5:1', 'C6:2 A5:1 F#5:1'];
  CH.forEach((h, i) => stride(26 + i, h, 0.27 * (0.95 + 0.012 * i), { lo: 53, hi: 69 }));
  CT.forEach((t, i) => S.mel(26 + i, t, 0.3 * 1.5, { v1: i < 4 ? 1.1 : 1 }));
  S.slow(33, 0.9, 0.1);
  /* A again, softer, and the end: the first half, then a cadence on G */
  playA(34, 0.27, pass ? 'orn' : 'plain');
  [['G', 'G'], ['Em7', 'Em7'], ['Am7', 'D7'], ['G', 'G']].forEach((h, i) => stride(42 + i, h, 0.26 - 0.02 * i));
  ['B4:1.5 D5:0.5 G5:2', 'G5:1.5 E5:0.5 B4:2', 'C5:1 E5:1 F#5:1 A5:1', 'G5:4'].forEach((t, i) => S.mel(42 + i, t, 0.36 - 0.03 * i));
  S.n(45, 0, 'G2', 0.34, 4); S.ch(45, 0, 'D3 G3 B3 D4', 0.2, 4, 0.04); S.slow(44, 0.9); S.slow(45, 0.8);
  S.length(46);
  for (let b = 2; b < 46; b++) for (let h = 0; h < 2; h++) S.ped(b * 4 + h * 2, b * 4 + h * 2 + 2);
  S.breathe(2, 42, 4, 0.05); S.arc(2, 42, 4, 0.2);
  return S.finish();
}

/* ---------- 3  NOTTURNO — night. 12/8, E minor, an eighth = 0.4 s. A wide, rolling arpeggio in the left hand; the tune sings in
   long notes over a chromatic-feeling bass (E, D#, D, C); a turn into G major opens the middle; it ends on an E major chord. ---------- */
function compNotturno(pass) {
  const S = Score(12, 0.4, 41 + pass * 3);
  S.strong = [0, 6]; S.sub = [3, 9];
  let pb = 40;
  const roll = (bar, sym, v, o = {}) => {
    const c = chordOf(sym); S.chord(bar, 0, 12, sym);
    const bass = near(c.bass, pb, 36, 50); pb = bass;
    const t = spread(c, bass, 4, o.hi || 69), b0 = bar * 12;
    for (let h = 0; h < 2; h++) [0, 1, 2, 3, 2, 1].forEach((k, i) => S.key(b0 + h * 6 + i, t[k], v * (i === 0 ? (h ? 0.85 : 1.1) : 0.72), 2.2, 0, i === 0 ? 2 : 3));
  };
  /* intro: the left hand alone, then one high note */
  roll(0, 'Em', 0.17); roll(1, 'Em', 0.2); S.mel(1, 'r:6 B4:6', 0.28);
  const AH = ['Em', 'B7/D#', 'Em7/D', 'C', 'Am7', 'B7', 'Em', 'Em'];
  const AT = ["B4:6 E5:3 'F#5 G5:3", 'F#5:4 E5:1 D#5:1 B4:3 D#5:3', 'G5:3 F#5:1 E5:1 D5:1 B4:6', 'C5:6 E5:3 G5:3', "'B5 A5:6 G5:3 E5:3", 'D#5:3 F#5:3 A5:3 F#5:3', "'A5 G5:6 F#5:3 E5:3", 'E5:9 r:3'];
  const playA = (b0, v, how) => {
    AH.forEach((h, i) => roll(b0 + i, h, v * (0.9 + 0.015 * i)));
    AT.forEach((t, i) => S.mel(b0 + i, t, v * 1.9, how === 'up' ? { up: true } : how === 'orn' ? { up: i % 2 === 0 } : {}));
    S.slow(b0 + 7, 0.9, 0.35);
  };
  playA(2, 0.2, 'plain');
  /* B — G major (bars 10–17) */
  const BH = ['G', 'D/F#', 'Em', 'Bm', 'C', 'G/B', 'Am7', 'B7'];
  const BT = ['D5:3 G5:3 B5:2 A5:1 G5:3', 'A5:6 F#5:3 D5:3', 'G5:6 B5:3 E6:3', 'D6:3 B5:3 F#5:3 D5:3', 'E5:3 G5:3 C6:6', 'B5:3 A5:1 G5:2 D5:6', 'C5:3 E5:3 A5:3 G5:3', 'F#5:6 D#5:3 B4:3'];
  BH.forEach((h, i) => roll(10 + i, h, 0.21 * (0.92 + 0.02 * i)));
  BT.forEach((t, i) => S.mel(10 + i, t, 0.21 * 1.9 * (i === 2 ? 1.1 : 1), { v1: i === 2 ? 0.9 : 1 }));
  S.slow(17, 0.9, 0.3);
  /* A again, in octaves and softer, and the close: a last cadence ending on E major */
  playA(18, 0.19, pass ? 'orn' : 'up');
  ['Em', 'B7', 'Em', 'E'].forEach((h, i) => roll(26 + i, h, 0.16 - 0.015 * i));
  ['E5:6 G5:3 B5:3', 'D#5:6 F#5:6', 'B4:3 E5:3 G5:6', 'G#5:12'].forEach((t, i) => S.mel(26 + i, t, 0.3 - 0.03 * i));
  S.slow(28, 0.88); S.slow(29, 0.8);
  S.length(30);
  S.autoPed();
  S.breathe(2, 26, 4, 0.05); S.arc(2, 26, 4, 0.2);
  return S.finish();
}

/* ---------- 4  FLORIAN — the salon. A small café waltz in C major, 3/4, about 126 to the quarter: bass, chord, chord;
   a first strain that rises and falls in a long arch, a second in G with a dip to B7, a trio in F; the first returns. ---------- */
function compFlorian(pass) {
  const S = Score(3, 0.476, 51 + pass * 3);
  S.strong = [0]; S.sub = [];
  let pb = 43, pu = null;
  const waltz = (bar, sym, v, o = {}) => {
    const c = chordOf(sym), b0 = bar * 3, sec = o.second ? chordOf(o.second) : null;
    const bass = near(c.bass, pb, 36, 52); pb = bass;
    const u1 = voice(c, 3, o.lo || 57, o.hi || 70, pu), u2 = sec ? voice(sec, 3, o.lo || 57, o.hi || 70, u1) : u1; pu = u2;
    if (sec) { S.chord(bar, 0, 2, sym); S.chord(bar, 2, 1, o.second); } else S.chord(bar, 0, 3, sym);
    S.key(b0, bass, v * 1.05, 1.5, 0, 2);
    [[1, -0.012, 0.62, u1], [2, 0.004, 0.55, u2]].forEach(([beat, lead, k, u]) => u.forEach((m, i) => S.key(b0 + beat, m, v * k * (i === u.length - 1 ? 1.06 : 0.9), 0.8, lead + i * 0.005, 3)));
  };
  const wpair = (bar, a, b, v, o = {}) => waltz(bar, a, v, Object.assign({ second: b }, o));
  /* intro: four bars of the dominant, a little flourish, then in */
  [['G7', 0.2], ['G7', 0.22], ['G7', 0.24], ['G7', 0.26]].forEach(([h, v], i) => waltz(i, h, v));
  S.run(3, 0, 'D5 G5 B5 D6', 0.25, 0.3, 0.4); S.slow(3, 0.9);
  const AH = ['C', 'C', 'G7', 'G7', 'C', 'F', 'G7', 'C', 'C', 'A7', 'Dm', 'G7', 'C', 'Am', ['D7', 'G7'], 'C'];
  const AT = ['E5:2 G5:1', 'C6:2 B5:1', 'A5:2 G5:1', 'F5:2 D5:1', 'E5:2 G5:1', 'A5:2 F5:1', 'D5:2 B4:1', 'C5:3', 'E5:1 G5:1 C6:1', 'E6:2 C#6:1', 'D6:2 A5:1', 'B5:2 D6:1', 'E6:2 C6:1', 'A5:2 E5:1', 'F#5:1 A5:1 B5:1', 'C6:3'];
  const AT2 = ['E5:2 G5:1', 'C6:2 B5:1', 'A5:2 G5:1', "'G5 F5:2 D5:1", 'E5:2 G5:1', "A5:2 'G5 F5:1", 'D5:2 B4:1', 'C5:3', 'E5:1 G5:1 C6:1', 'E6:2 C#6:1', 'D6:2 A5:1', 'B5:2 D6:1', 'E6:2 C6:1', 'A5:2 E5:1', 'F#5:1 A5:1 B5:1', 'C6:3'];
  const playA = (b0, v, how) => {
    AH.forEach((h, i) => { if (Array.isArray(h)) wpair(b0 + i, h[0], h[1], v * (0.9 + 0.006 * i)); else waltz(b0 + i, h, v * (0.9 + 0.006 * i)); });
    const T = how === 'orn' ? AT2 : AT;
    T.forEach((t, i) => S.mel(b0 + i, t, v * 1.7, how === 'up' ? { up: true } : {}));
    S.slow(b0 + 7, 0.92); S.slow(b0 + 15, 0.88, 0.12);
  };
  playA(4, 0.28, 'plain');
  /* B — G major (bars 20–35): a singing strain, with a B7 in the middle */
  const BH = ['G', 'G', 'D7', 'D7', 'G', 'C', 'D7', 'G', 'G', 'B7', 'Em', 'A7', 'D7', 'G', ['C', 'D7'], 'G'];
  const BT = ['B4:3', 'G5:2 F#5:1', 'A5:2 F#5:1', 'C6:2 A5:1', 'B5:2 G5:1', 'E5:2 G5:1', 'F#5:2 A5:1', 'G5:3', 'D5:1 G5:1 B5:1', 'D#6:2 B5:1', 'E6:2 B5:1', 'C#6:2 E6:1', 'A5:2 F#5:1', 'B5:2 G5:1', 'E5:1 G5:1 A5:1', 'G5:3'];
  BH.forEach((h, i) => { if (Array.isArray(h)) wpair(20 + i, h[0], h[1], 0.27 * (0.92 + 0.006 * i)); else waltz(20 + i, h, 0.27 * (0.92 + 0.006 * i)); });
  BT.forEach((t, i) => S.mel(20 + i, t, 0.27 * 1.7, { v1: i < 7 ? 1.08 : 1 }));
  S.slow(27, 0.92); S.slow(35, 0.88, 0.1);
  /* A again, an octave higher */
  playA(36, 0.27, pass ? 'orn' : 'up');
  /* trio — F major (bars 52–67): staccato, graceful */
  const CH = ['F', 'F', 'C7', 'C7', 'F', 'Bb', 'C7', 'F', 'F', 'D7', 'Gm', 'C7', 'F', 'Dm', ['G7', 'C7'], 'F'];
  const CT = ['A5:1 C6:1 F6:1', 'E6:2 F6:1', 'G6:2 E6:1', 'Bb5:2 G5:1', 'A5:1 C6:1 F6:1', 'D6:2 Bb5:1', 'E6:1 G5:1 C6:1', 'A5:3', 'C6:2 A5:1', 'F#5:2 A5:1', 'Bb5:2 G5:1', 'E5:2 G5:1', 'A5:1 C6:1 F6:1', 'D6:2 A5:1', 'B5:1 D6:1 E6:1', 'F6:3'];
  CH.forEach((h, i) => { if (Array.isArray(h)) wpair(52 + i, h[0], h[1], 0.25 * (0.93 + 0.005 * i), { lo: 52, hi: 65 }); else waltz(52 + i, h, 0.25 * (0.93 + 0.005 * i), { lo: 52, hi: 65 }); });
  CT.forEach((t, i) => S.mel(52 + i, t, 0.25 * 1.75, { leg: 0.7, oct: i < 8 ? -1 : 0 }));
  S.slow(59, 0.92); S.slow(67, 0.88, 0.1);
  /* the first strain once more, and the coda */
  playA(68, 0.26, pass ? 'plain' : 'orn');
  ['C', 'F', 'G7', 'C'].forEach((h, i) => waltz(84 + i, h, 0.24 - 0.02 * i));
  ['G5:1 E5:1 C6:1', 'A5:2 F5:1', 'D5:2 B4:1', 'C5:3'].forEach((t, i) => S.mel(84 + i, t, 0.36 - 0.03 * i));
  S.ch(87, 0, 'C3 G3 C4 E4 G4', 0.2, 3, 0.03); S.slow(85, 0.9); S.slow(86, 0.82); S.slow(87, 0.7);
  S.length(88);
  S.autoPed();
  S.breathe(4, 84, 4, 0.04); S.arc(4, 84, 4, 0.16);
  return S.finish();
}

/* ---------- 5  FENICE — the theatre. F major, 4/4, 56 to the quarter. The left hand is a harp (eight to the bar); above it a
   long aria line with appoggiaturas and a turn, and a middle strain in D minor that climbs to the top of the voice. ---------- */
function compFenice(pass) {
  const S = Score(4, 1.0, 61 + pass * 3);
  S.strong = [0, 2]; S.sub = [1, 3];
  let pb = 41;
  const harp = (bar, sym, v, o = {}) => {
    const c = chordOf(sym); S.chord(bar, 0, 4, sym);
    const bass = near(c.bass, pb, 36, 48); pb = bass;
    const t = spread(c, bass, 5, o.hi || 72), b0 = bar * 4;
    [0, 1, 2, 3, 4, 3, 2, 1].forEach((k, i) => S.key(b0 + i * 0.5, t[k], v * (i === 0 ? 1.12 : i === 4 ? 0.95 : 0.78), 1.4, 0, i === 0 ? 2 : 3));
  };
  /* intro: the harp alone, a held top note */
  harp(0, 'F', 0.18); harp(1, 'C7', 0.2); S.n(1, 2, 'C6', 0.2, 2, 4);
  /* A (bars 2–9): the aria line over a harp — I, C/E, ii, ii7/C | IV, I6, ii7, V7 — and its answer (bars 10–18) */
  const AH = ['F', 'C/E', 'Dm', 'Dm7/C', 'Bb', 'F/A', 'Gm7', 'C7'];
  const AT = ['A4:1 C5:1 F5:2', 'G5:1.5 E5:0.5 C5:2', 'D5:2 F5:1 A5:1', 'G5:1.5 F5:0.5 E5:1 D5:1', 'D5:2 F5:1 Bb5:1', 'A5:1.5 G5:0.5 F5:2', 'Bb5:1 G5:1 D5:1 F5:1', 'E5:2 G5:1 Bb5:1'];
  const AH2 = ['F', 'F/A', 'Bb', 'Gm7', 'C7', 'F/A', 'Gm7', 'C7', 'F'];
  const AT2 = ["A5:1.5 C6:0.5 'G6 F6:2", 'E6:1 D6:1 C6:1 Bb5:1', "A5:1.5 Bb5:0.5 'E6 D6:2", 'D6:1 C6:1 Bb5:1 G5:1', 'E5:1 G5:1 Bb5:1 C6:1', 'A5:2 F5:1 C5:1', 'D5:1 E5:1 F5:1 G5:1', 'E5:2 D5:1 C5:1', "'G5 F5:4"];
  const playA1 = (b0, v, how) => {
    AH.forEach((h, i) => harp(b0 + i, h, v * (0.92 + 0.012 * i)));
    AT.forEach((t, i) => S.mel(b0 + i, t, v * 1.9, how === 'up' ? { up: true } : {}));
    S.slow(b0 + 7, 0.9, 0.1);
  };
  const playA2 = (b0, v, how) => {
    AH2.forEach((h, i) => harp(b0 + i, h, v * (0.95 + 0.01 * i)));
    AT2.forEach((t, i) => S.mel(b0 + i, t, v * 1.95 * (i === 2 ? 1.08 : 1), how === 'up' ? { up: true } : {}));
    S.slow(b0 + 8, 0.82, 0.25);
  };
  playA1(2, 0.22, 'plain'); playA2(10, 0.23, 'plain');
  /* B — D minor (bars 19–26): the middle strain climbs to the top of the voice */
  const BH = ['Dm', 'A7/C#', 'Dm', 'Gm', 'Bb', 'C7', 'F/A', 'A7'];
  const BT = ['D5:2 F5:1 A5:1', 'A5:2 G5:1 E5:1', 'F5:2 A5:1 D6:1', 'D6:1.5 C6:0.5 Bb5:1 G5:1', 'D6:2 F6:1 Bb5:1', 'G6:2 E6:1 C6:1', 'F6:2 A5:1 C6:1', 'E6:3 r:1'];
  BH.forEach((h, i) => harp(19 + i, h, 0.22 * (0.95 + 0.02 * i)));
  BT.forEach((t, i) => S.mel(19 + i, t, 0.22 * 2.0 * (i === 4 || i === 5 ? 1.1 : 1)));
  S.slow(26, 0.85, 0.2);
  /* A once more, brighter (bars 27–34), and the close */
  playA1(27, 0.23, pass ? 'plain' : 'up');
  ['F', 'Bb', 'C7', 'F'].forEach((h, i) => harp(35 + i, h, 0.2 - 0.02 * i));
  ['A5:2 C6:2', 'D6:2 Bb5:1 G5:1', 'G5:1.5 Bb5:0.5 A5:1 G5:1', "'G5 F5:4"].forEach((t, i) => S.mel(35 + i, t, 0.34 - 0.03 * i));
  S.slow(37, 0.85); S.slow(38, 0.7);
  S.ch(38, 0, 'F2 C3 F3 A3 C4 F4', 0.2, 4, 0.04);
  S.length(39);
  S.autoPed();
  S.breathe(2, 35, 4, 0.05); S.arc(2, 35, 4, 0.2);
  return S.finish();
}

/* ---------- 6  BASILICA — gold and dusk. D Dorian kept to its five quiet notes (D F G A C, so no two sustained notes can
   rub), wide open chords, a slow chant line on top; very long reverb. No metre to speak of: a beat is two seconds. ---------- */
function compBasilica(pass) {
  const S = Score(4, 2.0, 71 + pass * 3);
  S.strong = [0]; S.sub = [];
  const R = S.rnd;
  /* every 16 seconds a new chord, rolled very slowly; the pedal stays down through it */
  [['D2 A2 D3 A3 F4', 0.22], ['D2 A2 D3 G3 A3', 0.2], ['G2 D3 G3 A3 D4', 0.2], ['C2 G2 C3 D3 G3', 0.2],
    ['F2 C3 F3 G3 A3 C4', 0.2], ['D2 A2 D3 F3 A3', 0.2], ['A2 C3 D3 A3 C4', 0.2], ['G2 D3 A3 C4 D4', 0.2]]
    .forEach(([c, v], k) => { S.ch(k * 2, 0, c, v, 8, 0.22); S.ped(k * 8, k * 8 + 7.6); });
  /* the chant: a line of long notes in the pentatonic, each phrase falling back towards D; a rest of a few beats between phrases.
     The second time round the phrases come in another order (the last always ends on D). */
  const PH = ['A4:2 G4:1 F4:2 D4:3', 'F4:2 G4:2 A4:2 C5:2', 'A4:3 G4:1 F4:2 G4:2', 'C5:2 A4:2 G4:2 F4:2', 'D5:3 C5:1 A4:2 F4:2'], at = [1, 12, 23, 34, 45];
  (pass ? [2, 0, 4, 1, 3] : [0, 1, 2, 3, 4]).forEach((k, i) => S.mel(0, PH[k], 0.3, { beat: at[i], lead: -0.02, leg: 1.0 }));
  S.mel(0, 'A4:4 F4:2 D4:2', 0.3, { beat: 56, lead: -0.02, leg: 1.0 });
  /* the light through the windows: now and then a high note, far from everything */
  [['D6', 5], ['A6', 14], ['F6', 21], ['G6', 31], ['D7', 38], ['A6', 47], ['C7', 53], ['F6', 60]].forEach(([n, b]) => S.n(0, (b + (pass ? 3 : 0)) % 64, n, 0.1 + 0.05 * R(), 6, 4));
  S.length(16);
  return S.finish();
}

/* ---------- 7  TITLE — first light on the water. D major, 4/4, 60 to the quarter: a slow wave of arpeggio under a tune of long
   notes (I – vi – IV – V …), a minor turn in the middle, and the close that drops back to where it began. ---------- */
function compTitle(pass) {
  const S = Score(4, 1.0, 31 + pass * 7);
  S.strong = [0, 2]; S.sub = [];
  let pb = 40;
  const wave = (bar, sym, v, o = {}) => {
    const c = chordOf(sym), half = o.half === undefined ? -1 : o.half, b0 = bar * 4 + (half === 1 ? 2 : 0);
    S.chord(bar, half === 1 ? 2 : 0, half < 0 ? 4 : 2, sym);
    const bass = near(c.bass, pb, 36, 50); pb = bass;
    const t = spread(c, bass, 5, 77);
    (half < 0 ? [0, 1, 2, 3, 4, 3, 2, 1] : [0, 1, 2, 3]).forEach((k, i) => S.key(b0 + i * 0.5, t[k], v * (i === 0 ? 1.15 : i === 4 ? 0.95 : 0.72), 1.6, 0, i === 0 ? 2 : 3));
  };
  const hh = (bar, h, v) => { if (Array.isArray(h)) h.forEach((sym, k) => wave(bar, sym, v, { half: k })); else wave(bar, h, v); };
  /* intro (bars 0–3): the wave alone, quietly; a bell */
  ['Dmaj7', 'Dmaj7', 'Bm7', 'Gmaj7'].forEach((h, i) => wave(i, h, 0.15 + 0.02 * i));
  S.n(3, 2, 'A6', 0.16, 4, 4);
  const AH = ['Dmaj7', 'Bm7', 'Gmaj7', 'A6', 'Dmaj7', 'F#m7', 'Gmaj7', ['Asus4', 'A']];
  const AT = ['A4:1 D5:1 F#5:2', 'F#5:2 E5:1 D5:1', 'D5:2 B4:1 A4:1', 'C#5:4', 'A4:1 D5:1 F#5:1 A5:1', 'A5:2 F#5:1 E5:1', 'D5:2 E5:1 F#5:1', 'E5:2 C#5:2'];
  const playA = (b0, v, how) => { AH.forEach((h, i) => hh(b0 + i, h, v * (0.9 + 0.015 * i))); AT.forEach((t, i) => S.mel(b0 + i, t, v * 2.2, how === 'up' ? { up: true } : {})); };
  playA(4, 0.17, 'plain');
  playA(12, 0.19, pass ? 'plain' : 'up');
  /* B — B minor (bars 20–27): the line lifts to E6 */
  const BH = ['Bm', 'Gmaj7', 'D/F#', 'Em7', 'Bm', 'Gmaj7', 'A', ['Asus4', 'A']];
  const BT = ['B4:1 D5:1 F#5:2', 'B5:2 A5:1 G5:1', 'F#5:2 A5:1 D6:1', 'E6:3 D6:1', 'D6:2 B5:1 F#5:1', 'G5:2 B5:1 D6:1', 'C#6:2 A5:1 E5:1', 'E5:4'];
  BH.forEach((h, i) => hh(20 + i, h, 0.19 * (0.92 + 0.02 * i)));
  BT.forEach((t, i) => S.mel(20 + i, t, 0.19 * 2.2 * (i === 3 ? 1.1 : 1), { v1: i === 3 ? 0.92 : 1 }));
  /* A again, hushed; then the close */
  AH.slice(0, 4).forEach((h, i) => hh(28 + i, h, 0.15 + 0.003 * i)); AT.slice(0, 4).forEach((t, i) => S.mel(28 + i, t, 0.3));
  ['Gmaj7', 'D/F#', ['Asus4', 'A'], 'D'].forEach((h, i) => hh(32 + i, h, 0.15 - 0.02 * i));
  ['B4:2 D5:2', 'A4:2 D5:2', 'E5:2 C#5:2', 'D5:4'].forEach((t, i) => S.mel(32 + i, t, 0.3 - 0.03 * i));
  S.ch(35, 0, 'D2 A2 D3 F#3 A3 D4', 0.22, 4, 0.05);
  S.length(36);
  S.autoPed();
  S.breathe(4, 32, 4, 0.04); S.arc(4, 32, 4, 0.16);
  return S.finish();
}

/* ====================================================================================================
   THE PIECES — the table the engine plays from.  trim: weight; tone: brightness of the hammers; bells: the primes (MIDI)
   the distant bells ring on — chosen from the minor chords of the piece's own key, so a bell never fights the piano
   ==================================================================================================== */
const PIECE_DEFS = {
  title: { fn: compTitle, passes: 2, trim: 1.43, tone: 0.95, bells: [64, 66, 71] },
  passeggiata: { fn: compPasseggiata, passes: 2, trim: 1.1, tone: 1.05, bells: [64, 69, 71] },
  barcarola: { fn: compBarcarola, passes: 2, trim: 0.89, tone: 1.0, bells: [69, 74, 62], lock: 2.4 },
  notturno: { fn: compNotturno, passes: 2, trim: 1.46, tone: 0.9, bells: [64, 71, 76] },
  florian: { fn: compFlorian, passes: 2, trim: 1.06, tone: 1.0, bells: [62, 69, 74] },
  basilica: { fn: compBasilica, passes: 2, trim: 2.2, tone: 0.8, bells: [62, 64, 69] },
  fenice: { fn: compFenice, passes: 2, trim: 1.41, tone: 0.95, bells: [74, 69, 62] },
};
const PRIORITY = ['title', 'passeggiata', 'barcarola', 'notturno', 'florian', 'basilica', 'fenice'];
export function _scores() { const o = {}; for (const k in PIECE_DEFS) o[k] = Array.from({ length: PIECE_DEFS[k].passes }, (_, p) => PIECE_DEFS[k].fn(p)); return o; }
function composeAll() {
  const out = {};
  for (const name of PRIORITY) {
    const d = PIECE_DEFS[name]; if (!d) continue;
    out[name] = { name, trim: d.trim, tone: d.tone, bells: d.bells, lock: d.lock || 0, passes: Array.from({ length: d.passes }, (_, p) => d.fn(p)) };
  }
  return out;
}
/* every other key of the range the scores use is rendered once in a worker; the rest are the neighbour, pitched up a
   semitone. Returns the jobs, the key each note plays, and the keys each piece needs. */
function planKeys(pieces) {
  let even = 0, tot = 0;
  for (const p of pieces) for (const P of p.passes) for (const e of P.events) { tot++; if ((e.m - 21) % 2 === 0) even++; }
  const par = even * 2 >= tot ? 0 : 1, need = {}, first = {}, keymap = {};
  pieces.forEach((p, pi) => {
    p.keys = new Set();
    for (const P of p.passes) for (const e of P.events) {
      const k = (e.m - 21) % 2 === par ? e.m : e.m - 1; keymap[e.m] = k; p.keys.add(k);
      need[k] = Math.max(need[k] || 0, Math.min(e.d + 1.2, 12) * Math.pow(2, (e.m - k) / 12));
      const f = pi * 1e6 + e.t; if (first[k] === undefined || f < first[k]) first[k] = f;
    }
  });
  return { keymap, jobs: Object.keys(need).map(Number).sort((a, b) => first[a] - first[b]).map((m) => ({ m, need: need[m] })) };
}

/* ====================================================================================================
   THE ENGINE
   ==================================================================================================== */
const MASTER = 1.0;       /* master gain */
const AMB = 0.55;         /* the natural sounds, against the piano */
/* each kind of natural sound, weighed so that its peaks sit about 10 dB under the piano's (measured offline) */
const G = { water: 0.65, boat: 0.45, step: 2.0, bird: 0.42, bell: 0.4 };
const AHEAD = 1.5;        /* how far ahead notes are put on the audio clock (s): the page may sleep a moment */
const XFADE = 3.6;        /* crossfade between pieces (s) */
const HOLD = 4.0;         /* a context must hold this long before the music follows it (s) */
const CURVE_IN = new Float32Array(64), CURVE_OUT = new Float32Array(64);
for (let i = 0; i < 64; i++) { const u = i / 63; CURVE_IN[i] = Math.sin((u * Math.PI) / 2); CURVE_OUT[i] = Math.cos((u * Math.PI) / 2); }
const ROOMS = ['hall', 'basilica', 'florian', 'fenice'];
/* the rooms' impulse responses: noise that darkens as it dies (k: the one-pole opening, from k0 to k1 with time constant tauK) */
const ROOM_IR = {
  hall: { sec: 3.0, rt: 2.4, pre: 0.018, k0: 0.72, k1: 0.07, tauK: 0.5, build: 0.006, early: 10, spread: 0.075, hp: 90 },
  basilica: { sec: 9.0, rt: 7.2, pre: 0.035, k0: 0.34, k1: 0.03, tauK: 1.6, build: 0.09, early: 4, spread: 0.12, hp: 120 },
  florian: { sec: 1.3, rt: 0.9, pre: 0.006, k0: 0.85, k1: 0.14, tauK: 0.3, build: 0.003, early: 14, spread: 0.045, hp: 100 },
  fenice: { sec: 2.4, rt: 1.6, pre: 0.014, k0: 0.6, k1: 0.06, tauK: 0.6, build: 0.01, early: 12, spread: 0.09, hp: 100 },
};
/* where each kind of sound goes: [music send, ambience send, footstep send] to [hall, basilica, florian, fenice] */
const SEND = {
  out: { music: [0.46, 0, 0, 0], amb: [0.22, 0, 0, 0], self: [0.16, 0, 0, 0], dry: 1.0 },
  basilica: { music: [0, 0.95, 0, 0], amb: [0, 0.3, 0, 0], self: [0, 0.55, 0, 0], dry: 0.78 },
  florian: { music: [0, 0, 0.5, 0], amb: [0, 0, 0.2, 0], self: [0, 0, 0.1, 0], dry: 1.0 },
  fenice: { music: [0, 0, 0, 0.66], amb: [0, 0, 0, 0.22], self: [0, 0, 0, 0.12], dry: 0.92 },
};
/* a footstep is softer on carpet and boards than on the stone of the calli */
const FLOOR = { out: [1, 1], basilica: [0.95, 1.05], florian: [0.55, 0.7], fenice: [0.45, 0.6] };

/* createAudio() → { start(), setEnabled(on), update(dt, s), info() }

     start()         from a user gesture: makes the AudioContext, starts rendering the piano keys and grains in a worker, and fades
                     the sound in (the first piece begins as soon as its keys are ready). Safe to call again. Does not block.
     setEnabled(on)  mute / unmute with a fade of about a second (the context is suspended while muted: no CPU)
     update(dt, s)   every frame. It allocates nothing but the sound events themselves; notes are put on the audio clock ahead of time.
                     s = { mode: 'title'|'walk'|'boat'|'fly', interior: null|'florian'|'basilica'|'fenice', night: bool,
                           walkSpeed: m/s, boatPhase: 0..1 (one oar stroke = 2.4 s; the power stroke is heard as the phase passes 0.2),
                           boatSpeed: m/s, water: 0..1, piazza: 0..1, camZ: metres above the water }
     info()          what is playing and how far the kit has got (for a debug overlay)
   createAudio({ debug: true }) also returns the internals as ._dbg (a test drives them with an OfflineAudioContext). */
export function createAudio(opts = {}) {
  let ctx = null, started = false, enabled = null, timer = 0;
  let master, comp, lim, clip, music, tone, bodyG, out, outLP1, outLP2, outG, selfBus, room = {};
  const KEYS = {}, KEYMAP = {}, BANK = {}, LASTID = {};
  let PIECES = null, kitDone = 0, kitTotal = 0, sfxDone = 0;
  let cur = null, dying = [], pendingName = null, pendingT = 0, wantName = null;
  const live = () => !!ctx && (ctx.state === 'running' || !!opts.context);      /* (a test drives an offline context by hand) */
  /* the world, as the last update saw it */
  let mode = 'title', interior = null, night = false, gnd = 1, muf = 0, nightK = 0, roomKey = 'out', lastSlow = -1;
  let prevPhase = -1, stepPhase = 0.85, foot = 0, strokeAge = 99;
  let bellT = 50 + 60 * Math.random(), hourT = 300 + 120 * Math.random(), hourN = 0;
  const LAST = new Float64Array(64).fill(NaN), strokes = [];
  const num = (x, d = 0) => (typeof x === 'number' && Number.isFinite(x) ? x : d);

  /* ---------------------------------------------------------------- the kit: piano keys and grains */
  const toBuffer = (r) => { const b = ctx.createBuffer(r.data.length, r.data[0].length, r.rate); r.data.forEach((d, c) => b.getChannelData(c).set(d)); return b; };
  function take(r) {
    if (!ctx) return;
    if (r.kind) { (BANK[r.kind] || (BANK[r.kind] = []))[r.id] = { raw: r, buf: null }; sfxDone++; }
    else KEYS[r.m] = { raw: r, buf: null };
    kitDone++;
  }
  /* a rendered sound waits as raw samples until first used, then lives as an AudioBuffer only */
  const keyBuf = (k) => { const s = KEYS[k]; if (!s) return null; if (!s.buf) { s.buf = toBuffer(s.raw); s.raw = null; } return s.buf; };
  const bufOf = (kind, id) => { const bk = BANK[kind], s = bk && bk[id]; if (!s) return null; if (!s.buf) { s.buf = toBuffer(s.raw); s.raw = null; } return s.buf; };
  function pick(kind) {
    const bk = BANK[kind]; if (!bk) return -1;
    let n = 0; for (let i = 0; i < bk.length; i++) if (bk[i]) n++;
    if (!n) return -1;
    let id = Math.floor(Math.random() * bk.length), g = 0; while (!bk[id] && g++ < 64) id = (id + 1) % bk.length;
    if (id === LASTID[kind] && n > 1) { do id = (id + 1) % bk.length; while (!bk[id]); }
    return (LASTID[kind] = id);
  }
  function loadKit(jobs) {
    const K = synthKit(), run = (j) => (j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need));
    const fallback = (from) => { let i = from; const step = () => { const t = performance.now(); while (i < jobs.length && performance.now() - t < 10) take(run(jobs[i++])); if (i < jobs.length) setTimeout(step, 0); }; step(); };
    try {
      const src = `const K = (${synthKit.toString()})();\nself.onmessage = (e) => { for (const j of e.data) { const r = j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need); self.postMessage(r, r.data.map((d) => d.buffer)); } };`;
      const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
      let got = 0; w.onmessage = (e) => { take(e.data); if (++got === jobs.length) w.terminate(); };
      w.onerror = (e) => { if (e && e.preventDefault) e.preventDefault(); w.terminate(); fallback(got); };
      w.postMessage(jobs);
    } catch (e) { fallback(0); }
  }
  const pieceReady = (p) => { if (!p) return false; if (p.ok) return true; for (const k of p.keys) if (!KEYS[k]) return false; return (p.ok = true); };

  /* ---------------------------------------------------------------- the graph */
  function makeIR(o) {
    const rate = ctx.sampleRate, n = Math.floor(rate * o.sec), b = ctx.createBuffer(2, n, rate), pre = Math.floor(o.pre * rate), hk = 1 - Math.exp((-2 * Math.PI * o.hp) / rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c); let lp = 0, hz0 = 0;
      for (let i = pre; i < n; i++) {
        const t = (i - pre) / rate, k = o.k1 + (o.k0 - o.k1) * Math.exp(-t / o.tauK);
        lp += (Math.random() * 2 - 1 - lp) * k; hz0 += (lp - hz0) * hk;
        d[i] = (lp - hz0) * Math.exp((-6.908 * t) / o.rt) * Math.min(1, t / o.build);
      }
      for (let r = 0; r < o.early; r++) d[pre + Math.floor((0.002 + Math.random() * o.spread) * rate)] += (Math.random() < 0.5 ? -1 : 1) * (0.5 - (r / o.early) * 0.35);
    }
    return b;
  }
  /* the piano's own body: a short, dense ring of the soundboard and case under the dry strings */
  function soundboard(sec) {
    const rate = ctx.sampleRate, n = Math.floor(rate * sec), b = ctx.createBuffer(2, n, rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c);
      for (let k = 0; k < 260; k++) {
        const f = 70 * Math.pow(60, Math.random()), dec = 18 + f * 0.035, a = (Math.random() * 2 - 1) / Math.sqrt(1 + f / 600), w = (2 * Math.PI * f) / rate, ph = Math.random() * 6.28;
        for (let i = 0; i < n; i++) { const e = Math.exp((-dec * i) / rate); if (e < 1e-3) break; d[i] += a * e * Math.sin(w * i + ph); }
      }
    }
    return b;
  }
  function build() {
    const AC = opts.context ? function () { return opts.context; } : window.AudioContext || window.webkitAudioContext;
    ctx = new AC({ latencyHint: 'playback' });
    /* a phone call or a locked screen may suspend the context: come back when the page is touched or shown again */
    const wake = () => { if (ctx && enabled && ctx.state !== 'running' && !opts.context) { try { const r = ctx.resume(); if (r && r.catch) r.catch(() => {}); } catch (e) { /* fine */ } } };
    if (!opts.context && typeof document !== 'undefined') { document.addEventListener('visibilitychange', wake); addEventListener('pointerdown', wake, { passive: true }); addEventListener('keydown', wake, { passive: true }); }
    master = ctx.createGain(); master.gain.value = 0;
    comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 2.5; comp.attack.value = 0.02; comp.release.value = 0.3;
    lim = ctx.createDynamicsCompressor(); lim.threshold.value = -2; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.002; lim.release.value = 0.12;
    /* a last soft clip: linear to 0.85, then easing to 1.0, so that nothing can ever clip the output */
    clip = ctx.createWaveShaper(); const cv = new Float32Array(2049);
    for (let i = 0; i < cv.length; i++) { const x = (i / 1024 - 1), a = Math.abs(x), t = 0.85; cv[i] = Math.sign(x) * (a <= t ? a : t + (1 - t) * Math.tanh((a - t) / (1 - t))); }
    clip.curve = cv; clip.oversample = '2x';
    master.connect(comp); comp.connect(lim); lim.connect(clip); clip.connect(ctx.destination);
    /* the rooms: one convolver each, fed by sends from the piano, the outdoor sounds and the footsteps */
    ROOMS.forEach((r, i) => {
      /* a room is connected only while something is sent to it (a convolver fed by an automated zero-gain still costs the
         whole convolution); `on` / `off` track that */
      const inG = ctx.createGain(), conv = ctx.createConvolver(), ret = ctx.createGain();
      conv.connect(ret); ret.connect(master);
      room[r] = { inG, conv, ret, music: ctx.createGain(), amb: ctx.createGain(), self: ctx.createGain(), on: false, off: 0 };
      for (const k of ['music', 'amb', 'self']) { room[r][k].gain.value = 0; room[r][k].connect(inG); }
      if (!opts.noRooms) setTimeout(() => { if (ctx) room[r].conv.buffer = makeIR(ROOM_IR[r]); }, 30 + i * 70);
    });
    /* the piano: every piece plays into `music`; a touch of body, the dry signal, and the sends */
    music = ctx.createGain(); music.gain.value = 1;
    tone = ctx.createBiquadFilter(); tone.type = 'highshelf'; tone.frequency.value = 3000; tone.gain.value = 0;
    const body = ctx.createConvolver(); if (!opts.noBody) body.buffer = soundboard(0.09); bodyG = ctx.createGain(); bodyG.gain.value = 0.55;
    music.connect(tone); tone.connect(master); tone.connect(body); body.connect(bodyG); bodyG.connect(master);
    for (const r of ROOMS) tone.connect(room[r].music);
    /* the outdoors: water, oar, pigeons, bells → high-pass → (muffled indoors) → master */
    out = ctx.createGain(); out.gain.value = 1;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 140; hp.Q.value = 0.7;
    outLP1 = ctx.createBiquadFilter(); outLP1.type = 'lowpass'; outLP1.frequency.value = 16000; outLP1.Q.value = 0.6;
    outLP2 = ctx.createBiquadFilter(); outLP2.type = 'lowpass'; outLP2.frequency.value = 16000; outLP2.Q.value = 0.6;
    outG = ctx.createGain(); outG.gain.value = AMB;
    out.connect(hp); hp.connect(outLP1); outLP1.connect(outLP2); outLP2.connect(outG); outG.connect(master);
    for (const r of ROOMS) outG.connect(room[r].amb);
    /* the listener's own footsteps: in whatever room they stand in */
    selfBus = ctx.createGain(); selfBus.gain.value = AMB;
    const shp = ctx.createBiquadFilter(); shp.type = 'highpass'; shp.frequency.value = 150; shp.Q.value = 0.7;
    selfBus.connect(shp); shp.connect(master);
    for (const r of ROOMS) shp.connect(room[r].self);
  }
  function setT(p, i, v, tc) { if (Math.abs(v - LAST[i]) > 1e-3 * Math.max(1, Math.abs(v)) || !(LAST[i] === LAST[i])) { LAST[i] = v; p.setTargetAtTime(v, ctx.currentTime, tc); } }

  /* ---------------------------------------------------------------- playing a key */
  function strike(e, at, ep, off = 0) {
    const k = KEYMAP[e.m] ?? e.m, buf = keyBuf(k); if (!buf) return;
    const rate = Math.pow(2, (e.m - k) / 12), len = buf.duration / rate - off; if (len < 0.05) return;
    const src = ctx.createBufferSource(); src.buffer = buf; src.playbackRate.value = rate;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.5;
    const v2 = e.v * e.v; lp.frequency.value = Math.min(15000, (hz(e.m) * (3 + 10 * v2) + 900 + 5000 * v2) * ep.piece.tone);
    const g = ctx.createGain(), amp = (0.05 + 0.95 * Math.pow(e.v, 1.6)) * ep.piece.trim;
    if (off > 0) { g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(amp, at + 0.012); } else g.gain.setValueAtTime(amp, at);
    let last = g; src.connect(lp); lp.connect(g);
    if (ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp((e.m - 64) / 50, -0.55, 0.55); g.connect(p); last = p; }
    last.connect(ep.bus);
    src.start(at, off * rate);
    const free = e.m >= 89, rest = e.d - off; let end;
    if (!free && rest < len) { const tau = 0.045 + 0.22 * clamp((72 - e.m) / 48, 0, 1), up = at + Math.max(0.03, rest); g.gain.setValueAtTime(amp, up); g.gain.setTargetAtTime(0, up, tau); end = up + tau * 7; src.stop(end); }
    else { end = at + len; src.stop(end); }
    /* striking a key that is still sounding: the hammer stops the old vibration */
    const old = ep.active[e.m];
    if (old && old.end > at) { try { old.g.gain.cancelScheduledValues(at); old.g.gain.setTargetAtTime(0, at, 0.03); old.src.stop(at + 0.25); } catch (x) { /* fine */ } }
    ep.active[e.m] = { src, g, end };
    ep.voices.add(src); src.onended = () => { ep.voices.delete(src); try { src.disconnect(); lp.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
  }

  /* ---------------------------------------------------------------- the music: one epoch per piece, crossfaded */
  function newEpoch(piece, when) {
    const bus = ctx.createGain(); bus.gain.value = 0;
    const outg = ctx.createGain(); outg.gain.value = 1;
    bus.connect(outg); outg.connect(music);
    bus.gain.setValueCurveAtTime(CURVE_IN, when, XFADE);
    return { piece, name: piece.name, bus, outg, t0: when, pass: 0, events: piece.passes[0].events, cur: 0, active: {}, voices: new Set(), dead: false, until: 0 };
  }
  function endEpoch(ep, when) {
    if (ep.dead) return;
    ep.dead = true; ep.until = when + XFADE + 0.4;
    ep.outg.gain.setValueCurveAtTime(CURVE_OUT, when, XFADE);
    dying.push(ep);
  }
  function startPiece(name, when) {
    const p = PIECES[name]; if (!p) return;
    if (cur) endEpoch(cur, when);
    cur = newEpoch(p, when);
  }
  function tick() {
    if (!live()) return;
    const now = ctx.currentTime;
    for (let i = dying.length - 1; i >= 0; i--) {
      const ep = dying[i];
      if (now > ep.until) { for (const v of ep.voices) { try { v.stop(); } catch (x) { /* fine */ } } try { ep.bus.disconnect(); ep.outg.disconnect(); } catch (x) { /* fine */ } dying.splice(i, 1); }
    }
    const e = cur; if (!e || e.dead || !enabled || opts.noMusic) return;
    const horizon = now + AHEAD;
    for (let guard = 0; guard < 4000; guard++) {
      const ev = e.events[e.cur];
      if (!ev) { e.t0 += e.piece.passes[e.pass % e.piece.passes.length].len; e.pass++; e.events = e.piece.passes[e.pass % e.piece.passes.length].events; e.cur = 0; continue; }
      const at = e.t0 + ev.t; if (at > horizon) break;
      e.cur++;
      if (at < now - 0.03) continue;                                    /* the page slept: do not pile up late notes */
      strike(ev, Math.max(at, now + 0.004), e);
    }
  }
  /* a piece with a pulse of its own (the barcarola: one bar to a stroke of the oar) starts on a stroke */
  function startAt(name, now, phase) {
    const L = PIECES[name].lock;
    if (!L || mode !== 'boat' || phase < 0) return now + 0.15;
    const w = ((((0.2 - phase) % 1) + 1) % 1) * L;
    return now + (w < 0.15 ? w + L : w);
  }
  const pickPiece = (m, inside, ngt) => (inside && PIECES[inside] ? inside : m === 'title' ? 'title' : m === 'boat' ? 'barcarola' : ngt ? 'notturno' : 'passeggiata');

  /* ---------------------------------------------------------------- the natural sounds */
  function grain(kind, dest, at, gain, rate, pan) {
    const id = pick(kind); if (id < 0) return;
    const b = bufOf(kind, id); if (!b) return;
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = rate;
    const g = ctx.createGain(); g.gain.value = gain; src.connect(g);
    let last = g;
    if (pan && ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp(pan, -1, 1); g.connect(p); last = p; }
    last.connect(dest); src.start(at);
    src.onended = () => { try { src.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
  }
  const logn = (s) => Math.exp(s * (Math.random() + Math.random() + Math.random() - 1.5) * 0.8);   /* a gentle lognormal wobble */
  const sgn = () => (Math.random() < 0.5 ? -1 : 1);
  /* one stroke of a bronze bell on the primes of the current piece: distance darkens and quietens it */
  function bellStroke(at, prime, gain, pan, far) {
    const ref = prime < 59.5 ? 0 : prime < 68 ? 1 : 2, base = [55, 64, 72][ref];
    const b = bufOf('bell', ref); if (!b) return;
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = Math.pow(2, (prime - base) / 12);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3600 - 2300 * far; lp.Q.value = 0.5;
    const g = ctx.createGain(); g.gain.value = gain * G.bell * (1 - 0.45 * far); src.connect(lp); lp.connect(g);
    let last = g; if (ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp(pan, -1, 1); g.connect(p); last = p; }
    last.connect(out); src.start(at);
    src.onended = () => { try { src.disconnect(); lp.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
  }
  /* a toll now and then: a single slow bell, rounds of a few bells, or three-by-three; and the hour */
  function toll(now, kind) {
    const P = cur && cur.piece.bells ? cur.piece.bells : [69, 74, 62], pan = (Math.random() - 0.5) * 0.9, far = 0.55 + 0.4 * Math.random(), t0 = now + 0.1;
    if (kind === 'hour') { const n = 2 + (hourN++ % 4), deep = P[0] - 12; for (let i = 0; i < n; i++) bellStroke(t0 + i * (4.4 + 0.3 * Math.random()), deep, 0.95, pan * 0.5, far * 0.6); return; }
    const r = Math.random();
    if (r < 0.4) { const n = 4 + Math.floor(Math.random() * 4), pr = P[Math.floor(Math.random() * P.length)]; for (let i = 0; i < n; i++) bellStroke(t0 + i * (3.5 + 1.1 * Math.random()), pr, 0.8 * (1 - 0.05 * i), pan, far); }
    else if (r < 0.75) { const k = 3 + Math.floor(Math.random() * 2), set = P.slice().sort((a, b) => b - a).slice(0, k), rounds = 4 + Math.floor(Math.random() * 3), gap = 0.8 + 0.15 * Math.random(); for (let rd = 0; rd < rounds; rd++) set.forEach((pr, i) => bellStroke(t0 + (rd * set.length + i) * gap + (Math.random() - 0.5) * 0.08, pr, 0.55 * (1 - 0.06 * rd), pan + (i - 1) * 0.12, far)); }
    else { const pr = P[Math.floor(Math.random() * P.length)]; for (let gp = 0; gp < 3; gp++) for (let i = 0; i < 3; i++) bellStroke(t0 + gp * 9 + i * 1.7, pr, 0.75, pan, far); }
  }

  /* ---------------------------------------------------------------- the frame */
  function update(dt, s) {
    if (!ctx || !started || !PIECES || !s) return;
    dt = clamp(num(dt, 0.016), 0, 0.25);
    const now = ctx.currentTime;
    mode = s.mode === 'walk' || s.mode === 'boat' || s.mode === 'fly' || s.mode === 'title' ? s.mode : 'walk';
    interior = typeof s.interior === 'string' && SEND[s.interior] && PIECES[s.interior] ? s.interior : null; night = !!s.night;
    const camZ = num(s.camZ, 2), water = clamp(num(s.water), 0, 1), piazza = clamp(num(s.piazza), 0, 1), walk = clamp(num(s.walkSpeed), 0, 6), boatV = clamp(num(s.boatSpeed), 0, 8);
    const phase = num(s.boatPhase, -1);
    gnd = 1 - sstep(30, 100, camZ);
    if (!live() || !enabled) return;

    /* slow things, ten times a second: the room, the muffling, the night */
    if (now - lastSlow > 0.1) {
      lastSlow = now;
      const rk = interior || 'out', M = SEND[rk];
      roomKey = rk;
      muf += ((interior ? 1 : 0) - muf) * (1 - Math.exp(-0.1 / 0.6));
      nightK += ((night && !interior ? 1 : 0) - nightK) * (1 - Math.exp(-0.1 / 1.5));
      const f = 600 * Math.pow(16000 / 600, 1 - muf);
      setT(outLP1.frequency, 0, f, 0.06); setT(outLP2.frequency, 1, f, 0.06);
      setT(outG.gain, 2, AMB * lerp(1, 0.32, muf), 0.12);
      for (let i = 0; i < 4; i++) {
        const R = room[ROOMS[i]], want = M.music[i] + M.amb[i] + M.self[i] > 0;
        if (want) { R.off = 0; if (!R.on) { R.inG.connect(R.conv); R.on = true; } }
        else if (R.on) { if (!R.off) R.off = now; else if (now - R.off > 4.5) { try { R.inG.disconnect(R.conv); } catch (e) { /* fine */ } R.on = false; R.off = 0; } }
        setT(R.music.gain, 3 + i, M.music[i], 0.7); setT(R.amb.gain, 8 + i, M.amb[i], 0.7); setT(R.self.gain, 13 + i, M.self[i], 0.7);
      }
      setT(tone.gain, 18, -4 * nightK, 0.8); setT(music.gain, 19, M.dry * (1 - 0.1 * nightK), 0.8);
    }

    /* which piece: the context must hold for HOLD seconds before the music follows it (the first one starts at once) */
    const want = pickPiece(mode, interior, night); wantName = want;
    if (!cur) { if (pieceReady(PIECES[want])) startPiece(want, startAt(want, now, phase)); }
    else if (want !== cur.name) {
      if (pendingName !== want) { pendingName = want; pendingT = now; }
      else if (now - pendingT >= HOLD && pieceReady(PIECES[want])) { startPiece(want, startAt(want, now, phase)); pendingName = null; }
    } else pendingName = null;
    tick();
    if (opts.noAmb) return;

    const gn = gnd, titleK = mode === 'title' ? 0.55 : 1;
    /* the oar: dip + swirl at each power stroke (phase passes 0.2), a drip trail after it */
    let crossed = false;
    if (phase >= 0 && prevPhase >= 0) {
      let d = phase - prevPhase; if (d < -0.5) d += 1; else if (d > 0.5) d -= 1;
      if (d > 0 && d < 0.4 && ((((prevPhase - 0.2) % 1) + 1) % 1) + d >= 1) { crossed = true; strokeAge = (((((phase - 0.2) % 1) + 1) % 1)) * 2.4; }
    }
    prevPhase = phase;
    const sp = clamp(boatV / 2.0, 0, 1.5);
    if (crossed) {
      if (opts.debug) strokes.push([now - strokeAge, cur ? cur.t0 : -1, cur ? cur.name : '']);
      if (cur && !cur.dead && cur.piece.lock && mode === 'boat') {
        const bl = cur.piece.lock, tc = now - strokeAge; let err = (tc - cur.t0) % bl; if (err < 0) err += bl; if (err > bl / 2) err -= bl;
        cur.t0 += clamp(err * 0.3, -0.015, 0.015);
      }
      if (mode === 'boat' && boatV > 0.12 && gn > 0.05) {
        const g = (0.34 + 0.4 * Math.min(1, sp)) * gn * G.boat, at = now + 0.012, side = 0.28;
        grain('oar', out, at, g * logn(0.25), 0.96 + 0.08 * Math.random(), side);
        const nd = 5 + Math.floor(Math.random() * 4); let t = 0.62 + 0.1 * Math.random();
        for (let i = 0; i < nd; i++) { grain('drip', out, at + t, g * 0.42 * Math.pow(0.88, i) * logn(0.5), 0.85 + 0.35 * Math.random(), side + (Math.random() - 0.5) * 0.3); t += 0.055 + 0.028 * i + 0.05 * Math.random(); }
      }
    }
    /* water against stone and hull: scattered wavelets, drips and bubbles — only where there is water */
    const w = water * gn * titleK;
    if (w > 0.02) {
      const bt = mode === 'boat' ? 0.6 : 1;
      if (Math.random() < (0.12 + 0.55 * w) * bt * dt) grain('slap', out, now + 0.02 + 0.02 * Math.random(), G.water * 0.3 * w * logn(0.45), 0.9 + 0.25 * Math.random(), sgn() * (0.25 + 0.55 * Math.random()));
      if (Math.random() < (0.1 + 0.5 * w) * bt * dt) grain('lap', out, now + 0.02, G.water * 0.26 * w * logn(0.4), 0.92 + 0.2 * Math.random(), sgn() * (0.2 + 0.6 * Math.random()));
      if (Math.random() < (0.06 + 0.3 * w) * dt) grain('drip', out, now + 0.02, G.water * 0.2 * w * logn(0.5), 0.8 + 0.5 * Math.random(), sgn() * Math.random() * 0.7);
      if (Math.random() < (0.04 + 0.18 * w) * dt) grain('bubble', out, now + 0.02, G.water * 0.17 * w * logn(0.5), 0.85 + 0.4 * Math.random(), sgn() * Math.random() * 0.7);
      if (Math.random() < (0.015 + 0.06 * w) * dt) grain('splash', out, now + 0.02, G.water * 0.26 * w * logn(0.4), 0.9 + 0.2 * Math.random(), sgn() * (0.2 + 0.5 * Math.random()));
    }
    if (mode === 'boat' && gn > 0.02 && boatV > 0.05) {
      /* the hull: soft wavelets along the planks, more with speed */
      if (Math.random() < (0.35 + 1.7 * sp) * dt) grain('hull', out, now + 0.02, (0.2 + 0.16 * Math.min(1, sp)) * gn * G.boat * logn(0.4), 0.9 + 0.25 * Math.random(), sgn() * (0.15 + 0.45 * Math.random()));
    }
    /* the listener's own steps: about 1.8 a second at walking pace, quicker running */
    if (mode === 'walk' && walk > 0.12 && gn > 0.2) {
      const sps = walk < 1.7 ? walk / 0.77 : 2.2 + (walk - 1.7) * 0.5;
      stepPhase += sps * dt;
      for (let n = 0; stepPhase >= 1 && n < 2; n++) {
        stepPhase -= 1; foot ^= 1;
        const run = walk > 2.6, F = FLOOR[roomKey] || FLOOR.out;
        grain(run ? 'run' : 'walk', selfBus, now + 0.01, (run ? 0.17 : 0.13) * G.step * F[0] * logn(0.3), (foot ? 0.97 : 1.03) * (0.97 + 0.06 * Math.random()) * F[1], (foot ? 1 : -1) * 0.09);
      }
      if (stepPhase > 1) stepPhase = 0;
    } else stepPhase = Math.max(stepPhase, 0.85);
    /* pigeons in the square: an occasional coo, and a flutter when something startles them (running through them) */
    const pg = sstep(0.3, 0.8, piazza) * gn * (night ? 0.2 : 1);
    if (pg > 0.02 && !interior) {
      if (Math.random() < (0.1 + 0.2 * pg) * dt) { const pan = sgn() * (0.2 + 0.6 * Math.random()), rate = 0.92 + 0.2 * Math.random(); grain('coo', out, now + 0.03, G.bird * 0.34 * pg * logn(0.3), rate, pan); if (Math.random() < 0.3) grain('coo', out, now + 0.5 + 0.6 * Math.random(), G.bird * 0.26 * pg, rate * 1.07, -pan); }
      if (Math.random() < (0.012 + 0.03 * pg + (walk > 2.6 ? 0.2 : 0)) * dt) { const pan = sgn() * (0.3 + 0.5 * Math.random()); grain('wing', out, now + 0.03, G.bird * 0.3 * pg * logn(0.3), 0.95 + 0.1 * Math.random(), pan); if (Math.random() < 0.5) grain('wing', out, now + 0.25 + 0.3 * Math.random(), G.bird * 0.22 * pg, 1.0, -pan); }
    }
    /* the bells: a toll now and then, and a few strokes on the (virtual) hour */
    bellT -= dt; hourT -= dt;
    if (hourT <= 0) { hourT = 480; toll(now, 'hour'); if (bellT < 60) bellT = 60 + 30 * Math.random(); }
    else if (bellT <= 0) { bellT = 120 + 180 * Math.random(); if (hourT > 40) toll(now, 'toll'); else bellT = 60; }
  }

  /* ---------------------------------------------------------------- the public face */
  /* stop an automation where it is, without the jump that cancelScheduledValues would leave */
  function hold(p, t) { if (p.cancelAndHoldAtTime) p.cancelAndHoldAtTime(t); else { const v = p.value; p.cancelScheduledValues(t); p.setValueAtTime(v, t); } }
  function applyEnabled() {
    if (!ctx) return;
    const now = ctx.currentTime;
    if (enabled) { try { if (ctx.state === 'suspended') { const r = ctx.resume(); if (r && r.catch) r.catch(() => {}); } } catch (e) { /* fine */ } hold(master.gain, now); master.gain.setTargetAtTime(MASTER, now, 0.5); }
    else { hold(master.gain, now); master.gain.setTargetAtTime(0, now, 0.2); setTimeout(() => { if (!enabled && ctx && ctx.suspend) { try { ctx.suspend(); } catch (e) { /* fine */ } } }, 1400); }
  }
  async function start() {
    if (started) { if (enabled) applyEnabled(); return; }
    started = true; if (enabled === null) enabled = true;
    try { build(); } catch (e) { console.warn('audio unavailable', e); ctx = null; started = false; return; }
    try { if (!opts.context) await Promise.race([ctx.resume(), new Promise((r) => setTimeout(r, 400))]); } catch (e) { /* fine */ }
    applyEnabled();
    /* compose and start rendering after this call has returned, so the click that began it is not held up */
    setTimeout(() => {
      if (!ctx) return;
      try { PIECES = composeAll(); } catch (e) { console.warn('audio: the score failed', e); return; }
      const plan = planKeys(Object.values(PIECES)); Object.assign(KEYMAP, plan.keymap);
      /* the keys the opening piece needs first, then the grains, then the rest of the keyboard */
      const tk = PIECES.title ? PIECES.title.keys : new Set(), jobs = plan.jobs.filter((j) => tk.has(j.m));
      for (const k of Object.keys(COUNTS)) for (let i = 0; i < COUNTS[k]; i++) jobs.push({ sfx: k, id: i });
      jobs.push(...plan.jobs.filter((j) => !tk.has(j.m))); kitTotal = jobs.length;
      loadKit(jobs);
      if (!opts.context) timer = setInterval(tick, 80);
    }, 0);
  }
  function setEnabled(on) {
    enabled = !!on;
    if (started && ctx) applyEnabled(); else if (on && !started) start();
  }
  const COUNTS = synthKit().COUNTS;
  const api = {
    start, setEnabled, update,
    /* for debugging: what is playing and how far the kit has got */
    info: () => ({ started, enabled, state: ctx && ctx.state, piece: cur && cur.name, want: wantName, pass: cur && cur.pass, room: roomKey, kit: kitDone + '/' + kitTotal, sfx: sfxDone, gnd: +gnd.toFixed(2), muffle: +muf.toFixed(2) }),
  };
  if (opts.debug) api._dbg = { get ctx() { return ctx; }, get comp() { return comp; }, get lim() { return lim; }, get master() { return master; }, tick, strokes, get cur() { return cur; }, PIECES: () => PIECES, toll: (k) => toll(ctx.currentTime, k), strike, KEYS, BANK };
  return api;
}
