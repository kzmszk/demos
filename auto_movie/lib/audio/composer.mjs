// Generative composer: turns the video's structure (sections with mood/energy) into a small piano-centred arrangement.
// Pure and seeded: the same input always gives the same score. Output is a list of note events per instrument.
import { rng, clamp } from '../util.mjs';

const MAJOR = [0, 2, 4, 5, 7, 9, 11];
const KEYS = { C: 0, 'D♭': 1, D: 2, 'E♭': 3, E: 4, F: 5, G: 7, A: 9, 'B♭': 10 };
const QUAL = {
  maj7: [0, 4, 7, 11], min7: [0, 3, 7, 10], dom7: [0, 4, 7, 10], sus7: [0, 5, 7, 10],
  maj9: [0, 4, 7, 11, 14], min9: [0, 3, 7, 10, 14], add9: [0, 4, 7, 14], dom9: [0, 4, 7, 10, 14],
};
// progressions as [scale-degree index of the root (0 = I), quality]
export const LOOPS = {
  warm: [[0, 'maj9'], [5, 'min7'], [3, 'maj7'], [4, 'dom7']],
  curious: [[5, 'min9'], [3, 'maj7'], [0, 'maj7'], [4, 'sus7']],
  focused: [[1, 'min9'], [4, 'dom9'], [0, 'maj9'], [5, 'min7']],
  playful: [[0, 'add9'], [3, 'add9'], [5, 'min7'], [4, 'sus7']],
  uplift: [[3, 'maj9'], [4, 'dom7'], [2, 'min7'], [5, 'min7']],
  resolve: [[1, 'min7'], [4, 'dom7'], [0, 'maj9'], [0, 'maj9']],
  calm: [[0, 'maj9'], [2, 'min7'], [3, 'maj9'], [0, 'maj7']],
};
export const MOODS = Object.keys(LOOPS);

const degreeToMidi = (keyPc, deg, oct) => 12 * (oct + 1) + keyPc + MAJOR[((deg % 7) + 7) % 7] + 12 * Math.floor(deg / 7);

function chordFrom(keyPc, [deg, q], oct = 3) {
  const rootPc = (keyPc + MAJOR[deg]) % 12;
  const iv = QUAL[q];
  return { deg, q, rootPc, iv, name: q, root: 12 * (oct + 1) + rootPc };
}

/** Voice-lead a chord's upper structure to sit close to the previous voicing. */
function voice(chord, prev) {
  const tones = chord.iv.filter((i) => i % 12 !== 0 || chord.iv.length < 4).map((i) => (chord.rootPc + i) % 12);
  const center = prev ? prev.reduce((a, b) => a + b, 0) / prev.length : 64;
  const picked = [];
  for (const pc of tones.slice(0, 4)) {
    let best = null;
    for (let m = 52; m <= 79; m++) if (m % 12 === pc) { const d = Math.abs(m - center); if (!best || d < best.d) best = { m, d }; }
    if (best) picked.push(best.m);
  }
  picked.sort((a, b) => a - b);
  // keep spacing sane
  for (let i = 1; i < picked.length; i++) if (picked[i] === picked[i - 1]) picked[i] += 12;
  return picked.sort((a, b) => a - b);
}

/** Section boundaries → bars. Returns per-bar { energy, mood, section, voiceLoad }. */
function barPlan({ sections, bars, barSec, voiceLoad }) {
  const plan = [];
  for (let b = 0; b < bars; b++) {
    const t = (b + 0.5) * barSec;
    const s = sections.find((x) => t >= x.t0 && t < x.t1) || sections.at(-1);
    plan.push({ bar: b, t0: b * barSec, mood: s.mood || 'warm', energy: clamp(s.energy ?? 0.4, 0, 1), label: s.label, voiceLoad: voiceLoad?.(b * barSec, (b + 1) * barSec) ?? 0.7 });
  }
  return plan;
}

/**
 * @param {object} o
 * @param {number} o.duration        video length in seconds
 * @param {{t0:number,t1:number,mood?:string,energy?:number,label?:string}[]} o.sections
 * @param {(a:number,b:number)=>number} [o.voiceLoad]  fraction of [a,b) covered by speech (0..1)
 */
export function compose({ duration, sections, seed = 1, key = 'F', bpm: bpmHint, voiceLoad, introSec = 4.5, outroSec = 9, title = '' }) {
  const r = rng(`music:${seed}:${title}`);
  const keyPc = KEYS[key] ?? 5;
  const wantBpm = bpmHint || 80 + Math.round(r.range(-4, 6));
  const bars = Math.max(8, Math.round((duration * wantBpm) / 240));
  const bpm = (bars * 240) / duration;                   // exact fit: bars × 4 beats = duration
  const beat = 60 / bpm, barSec = beat * 4, eighth = beat / 2;
  const plan = barPlan({ sections, bars, barSec, voiceLoad });

  const notes = { piano: [], ep: [], pad: [], bass: [], bell: [], kick: [], snare: [], shaker: [] };
  const swing = 0.1 + r.range(0, 0.06);
  const jitter = () => r.gauss() * 0.005;
  const at = (barIdx, eighthIdx) => barIdx * barSec + eighthIdx * eighth + (eighthIdx % 2 ? swing * eighth : 0);
  const add = (inst, t, midi, vel, dur, extra = {}) => notes[inst].push({ t: Math.max(0, t + jitter()), midi, vel: clamp(vel + r.range(-0.05, 0.05), 0.08, 1), dur, ...extra });

  // --- chord per bar (slower harmonic rhythm when the section is sparse), keeping the loop phase steady
  const chords = [];
  let prevV = null;
  const outroStartBar = Math.max(1, Math.floor((duration - outroSec + 1.2) / barSec));
  const finalBar = bars - Math.max(2, Math.round(5.2 / barSec)); // the final tonic starts here
  const introBars = Math.max(1, Math.round(introSec / barSec));
  let loopPos = 0;
  for (let b = 0; b < bars; b++) {
    const p = plan[b];
    let ch;
    if (b >= finalBar) ch = chordFrom(keyPc, [0, 'maj9']);
    else if (b === finalBar - 1) ch = chordFrom(keyPc, [4, 'dom7']);
    else if (b === finalBar - 2) ch = chordFrom(keyPc, [1, 'min7']);
    else {
      const loop = LOOPS[p.mood] || LOOPS.warm;
      const slow = p.energy < 0.28 ? 2 : 1;
      if (b > 0 && plan[b - 1].mood !== p.mood) loopPos = 0;
      ch = chordFrom(keyPc, loop[Math.floor(loopPos / slow) % loop.length]);
      loopPos++;
    }
    ch.voicing = voice(ch, prevV);
    prevV = ch.voicing;
    chords.push(ch);
  }

  // --- motif (scale degrees relative to key, octave-free) shared by the whole piece, with variations
  const motifLen = 6;
  const motifDeg = [];
  let d = r.pick([2, 4, 4, 5]);            // start on 3rd/5th/6th
  for (let i = 0; i < motifLen; i++) {
    motifDeg.push(d);
    d += r.pick([-2, -1, -1, 1, 1, 2, 0]) ;
    d = clamp(d, 0, 9);
  }
  const motifRhythm = r.pick([[1.5, 0.5, 1, 1, 2, 0], [1, 1, 1.5, 0.5, 1, 1], [0.5, 0.5, 1, 1.5, 1.5, 1], [2, 1, 1, 1.5, 0.5, 1]]);
  const chordPcs = (ch) => ch.iv.map((i) => (ch.rootPc + i) % 12);
  const snapToChord = (midi, ch) => {
    const pcs = chordPcs(ch);
    let best = midi, bd = 99;
    for (let m = midi - 2; m <= midi + 2; m++) { const pc = ((m % 12) + 12) % 12; if (pcs.includes(pc) && Math.abs(m - midi) < bd) { best = m; bd = Math.abs(m - midi); } }
    return best;
  };
  const inScale = (m) => MAJOR.includes((((m - keyPc) % 12) + 12) % 12);

  // --- render the plan bar by bar
  for (let b = 0; b < bars; b++) {
    const p = plan[b], ch = chords[b], v = ch.voicing, e = p.energy;
    const isFinal = b >= finalBar, inIntro = p.t0 + barSec * 0.5 < introSec;
    const busy = p.voiceLoad; // 0..1 how much of this bar is under speech
    const low = 36 + ch.rootPc;
    const bassLow = low > 45 ? low - 12 : low;            // 34..45: where the bass instrument lives
    const hasBass = e >= 0.32;
    const bassMidi = hasBass ? bassLow + 12 : bassLow;     // piano left hand: an octave above the bass, or alone
    const barDur = barSec;

    // pad: sustained chord (rooted at the bar where the chord changes)
    const chordChanged = b === 0 || chords[b - 1].rootPc !== ch.rootPc || chords[b - 1].q !== ch.q;
    if (chordChanged || b % 4 === 0) {
      let len = 1;
      while (b + len < bars && chords[b + len].rootPc === ch.rootPc && chords[b + len].q === ch.q && len < 4) len++;
      const padVel = 0.35 + 0.4 * e + (isFinal ? 0.15 : 0);
      [v[0], v[1], v[2]].forEach((m, i) => add('pad', p.t0 + i * 0.02, m - (i === 0 ? 12 : 0), padVel * (i === 2 ? 0.8 : 1), len * barSec + 0.4));
    }

    if (inIntro) continue;                                   // the intro is the jingle below (plus the pad)
    if (isFinal) {
      // the last tonic: rolled chord, a high bell, and nothing else
      if (b === finalBar) {
        v.forEach((m, i) => add('piano', p.t0 + i * 0.09, m - (i === 0 ? 12 : 0), 0.58 - i * 0.03, 8, { pedal: 1 }));
        add('piano', p.t0, bassLow + 12, 0.5, 9, { pedal: 1 });
        add('bell', p.t0 + 0.45, degreeToMidi(keyPc, 4, 5), 0.45, 3);
        add('bell', p.t0 + 0.75, degreeToMidi(keyPc, 7, 5), 0.4, 3);
      }
      continue;
    }

    // pattern by energy
    const dens = clamp(1 - busy * 0.45, 0.4, 1);
    if (e < 0.28) {
      // sparse: bass root, a rolled chord, one soft melodic answer
      add('piano', p.t0, bassMidi + 12, 0.5, barDur * 0.95, { pedal: 0.9 });
      v.forEach((m, i) => add('piano', p.t0 + 0.05 + i * 0.07, m, 0.4 + 0.05 * i, barDur * 0.9, { pedal: 0.9 }));
      if (b % 2 === 1 && busy < 0.85) {
        const md = motifDeg[(b >> 1) % motifLen];
        add('piano', p.t0 + beat * 2.5, snapToChord(degreeToMidi(keyPc, md, 4), ch), 0.42, beat * 1.4, { pedal: 0.7 });
      }
    } else {
      // flowing broken-chord figure on the eighth grid
      const fig = r.pick([[0, 2, 3, 2, 1, 2, 3, 2], [0, 1, 2, 3, 2, 1, 2, 1], [0, 2, 1, 3, 2, 3, 1, 2]]);
      const lo = v[0] - 12;
      add('piano', p.t0, bassMidi, 0.55 + 0.1 * e, beat * 1.9, { pedal: 0.6 });
      if (e > 0.4) add('piano', at(b, 4), bassMidi + (b % 2 ? 7 : 0), 0.45, beat * 1.4, { pedal: 0.6 });
      for (let i = 0; i < 8; i++) {
        if (r() > dens + 0.15 && i % 4 !== 0) continue;        // thin out under speech
        const idx = fig[i] % v.length;
        const m = idx === 0 && i > 0 ? lo + 12 : v[idx];
        const accent = i % 4 === 0 ? 0.1 : 0;
        add('piano', at(b, i), m + (i >= 6 ? 0 : 0), 0.34 + 0.22 * e + accent, eighth * 2.4, { pedal: 0.55 });
      }
      // melody: motif on even bars when the bar is not too busy; higher register
      if (busy < 0.92 || e > 0.55) {
        if (b % 2 === 0 || e > 0.7) {
          let t = 0;
          const phrase = (b >> 1) % 4;
          for (let i = 0; i < motifLen; i++) {
            const dur = motifRhythm[i];
            if (!dur) break;
            if (t >= 4) break;
            let deg = motifDeg[i] + (phrase === 1 ? -1 : phrase === 3 ? 1 : 0);
            let m = degreeToMidi(keyPc, deg, 4);
            if (t % 2 === 0) m = snapToChord(m, ch);        // chord tones on strong beats
            if (!inScale(m)) m += 1;
            if (r() < 0.86 * (0.55 + 0.45 * dens)) add(e > 0.62 && r() < 0.5 ? 'ep' : 'piano', p.t0 + t * beat, m + (e > 0.62 ? 0 : 0), 0.4 + 0.2 * e, dur * beat * 0.95, { pedal: 0.5 });
            t += dur;
          }
        }
      }
    }

    // bass line + soft percussion once the energy asks for it
    if (hasBass) {
      add('bass', p.t0, bassLow, 0.62, beat * 1.6);
      if (e >= 0.5) add('bass', at(b, 5), bassLow + 7 <= 47 ? bassLow + 7 : bassLow, 0.5, beat * 0.9);
    }
    if (e >= 0.45) {
      add('kick', p.t0, 0, 0.5 + 0.2 * e, 0.2);
      if (e >= 0.55) add('kick', at(b, 5), 0, 0.4, 0.2);
      add('snare', p.t0 + beat, 0, 0.36 + 0.2 * e, 0.2);
      add('snare', p.t0 + beat * 3, 0, 0.4 + 0.2 * e, 0.2);
      for (let i = 0; i < 8; i++) if (i % 2 === 1 || e > 0.7) add('shaker', at(b, i), 0, (i % 2 ? 0.5 : 0.3) + 0.15 * e, 0.1);
    }
    if (e >= 0.6 && busy < 0.9 && b % 2 === 1) {
      // electric-piano stabs on the off-beats
      v.slice(0, 3).forEach((m, i) => add('ep', at(b, 3) + i * 0.012, m + 12, 0.38, eighth * 1.6));
    }
    // sparkle at the top of each new section
    if (p.label && (b === 0 || plan[b - 1].label !== p.label) && !inIntro) {
      add('bell', p.t0 + 0.02, degreeToMidi(keyPc, 4 + (b % 3), 5), 0.4, 2.5);
    }
  }

  // --- intro jingle: a rising pentatonic figure (piano + bell) that lands on the first chord
  [0, 1, 2, 4, 5].forEach((dg, i) => {
    const m = degreeToMidi(keyPc, dg + 2, 4) + 12;
    add('piano', 0.25 + i * 0.32, m, 0.5 + i * 0.03, 1.4, { pedal: 0.8 });
    add('bell', 0.26 + i * 0.32, m + 12, 0.3, 2);
  });
  add('bell', 0.25 + 5 * 0.32, degreeToMidi(keyPc, 9, 5), 0.42, 3);
  add('piano', 0.25 + 5 * 0.32, chords[0].voicing[0], 0.5, 3, { pedal: 0.9 });
  add('piano', 0.25 + 5 * 0.32 + 0.06, chords[0].voicing[2], 0.44, 3, { pedal: 0.9 });

  const total = Object.values(notes).reduce((s, a) => s + a.length, 0);
  return {
    bpm: Math.round(bpm * 100) / 100, key, bars, beatSec: beat, barSec, duration,
    chords: chords.map((c, i) => ({ bar: i, t: i * barSec, root: c.rootPc, q: c.q, voicing: c.voicing })),
    plan: plan.map((p) => ({ bar: p.bar, t: p.t0, mood: p.mood, energy: p.energy, label: p.label, voiceLoad: Math.round(p.voiceLoad * 100) / 100 })),
    notes, stats: { notes: total, swing: Math.round(swing * 100) / 100 },
  };
}

// ---- Standard MIDI file export (type 1, one track per instrument) --------------------------------
export function scoreToMidi(score) {
  const ppq = 480;
  const GM = { piano: 0, ep: 4, pad: 89, bass: 33, bell: 11 };
  const tracks = [];
  const vlq = (n) => { const b = [n & 0x7f]; while ((n >>= 7)) b.unshift((n & 0x7f) | 0x80); return b; };
  const tempo = Math.round(60000000 / score.bpm);
  tracks.push([0, 0xff, 0x51, 3, (tempo >> 16) & 255, (tempo >> 8) & 255, tempo & 255, 0, 0xff, 0x58, 4, 4, 2, 24, 8, 0, 0xff, 0x2f, 0]);
  let ch = 0;
  for (const [inst, arr] of Object.entries(score.notes)) {
    if (!arr.length) continue;
    const drum = ['kick', 'snare', 'shaker'].includes(inst);
    const channel = drum ? 9 : ch++ % 9;
    const ev = [];
    for (const n of arr) {
      const midi = drum ? { kick: 36, snare: 38, shaker: 70 }[inst] : n.midi;
      const on = Math.round((n.t / score.beatSec) * ppq), off = Math.round(((n.t + Math.min(n.dur, 8)) / score.beatSec) * ppq);
      ev.push([on, 0x90 | channel, midi, Math.round(n.vel * 110) + 10], [off, 0x80 | channel, midi, 0]);
    }
    ev.sort((a, b) => a[0] - b[0] || (a[1] & 0xf0) - (b[1] & 0xf0));
    const bytes = [0, 0xff, 0x03, inst.length, ...Buffer.from(inst)];
    if (!drum) bytes.push(0, 0xc0 | channel, GM[inst] ?? 0);
    let last = 0;
    for (const e of ev) { bytes.push(...vlq(e[0] - last), e[1], e[2], e[3]); last = e[0]; }
    bytes.push(0, 0xff, 0x2f, 0);
    tracks.push(bytes);
  }
  const head = Buffer.from([0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6, 0, 1, 0, tracks.length, (ppq >> 8) & 255, ppq & 255]);
  const chunks = tracks.map((t) => Buffer.concat([Buffer.from('MTrk'), Buffer.from([(t.length >>> 24) & 255, (t.length >>> 16) & 255, (t.length >>> 8) & 255, t.length & 255]), Buffer.from(t)]));
  return Buffer.concat([head, ...chunks]);
}
