// Face tracks for one avatar: eyes / brows / mouth as [[time, stateId]] transitions, from the speaker's lines,
// the partner's reactions and seeded blinks. The browser runtime turns each transition into a tl.set().
import { round } from '../util.mjs';
import { FACE, blinkTimes } from './lipsync.mjs';

const MOUTH_BY_SHAPE = ['mouth-closed', 'mouth-a', 'mouth-i', 'mouth-o'];

/** Sweep prioritized intervals into transitions (highest priority wins; ties → later start). */
function sweep(intervals, base, until) {
  const cuts = new Set([0, until]);
  for (const iv of intervals) { cuts.add(iv.t0); cuts.add(iv.t1); }
  const ts = [...cuts].sort((a, b) => a - b);
  const out = [];
  let cur = null;
  for (let i = 0; i < ts.length - 1; i++) {
    const mid = (ts[i] + ts[i + 1]) / 2;
    let best = null;
    for (const iv of intervals) if (iv.t0 <= mid && mid < iv.t1 && (!best || iv.prio > best.prio || (iv.prio === best.prio && iv.t0 >= best.t0))) best = iv;
    const id = best ? best.id : base;
    if (id !== cur) { out.push([round(ts[i]), id]); cur = id; }
  }
  return out;
}

/**
 * @param {object} o
 * @param {object[]} o.mine   this avatar's lines (absolute times, with .mouth relative transitions)
 * @param {object[]} o.theirs the partner's lines
 */
export function faceTracks({ mine, theirs, duration, seed }) {
  const eyes = [], brows = [], mouth = [];
  for (const ln of mine) {
    const f = FACE[ln.emotion] || FACE.normal;
    if (f.eyes !== 'eyes-open') {
      const len = ln.emotion === 'surprised' ? 0.9 : ln.emotion === 'happy' ? Math.min(ln.end - ln.start, 1.6) : 0;
      if (len) eyes.push({ t0: ln.start, t1: ln.start + len, id: f.eyes, prio: 3 });
    }
    if (f.brows !== 'brows-normal') brows.push({ t0: ln.start, t1: ln.end, id: f.brows, prio: 3 });
    // mouth: shapes while speaking, resting shape (smile for happy) around it
    const rest = f.rest;
    mouth.push({ t0: ln.start, t1: ln.end + 0.05, id: rest, prio: 1 });
    const tr = ln.mouth || [];
    tr.forEach(([t, shape], i) => {
      const t0 = ln.start + t, t1 = i + 1 < tr.length ? ln.start + tr[i + 1][0] : ln.end;
      const id = shape === 0 ? rest : MOUTH_BY_SHAPE[shape];
      mouth.push({ t0, t1, id, prio: 2 });
    });
  }
  // reactions while the partner talks
  for (const ln of theirs) {
    if (ln.emotion === 'happy') {
      mouth.push({ t0: ln.start + 0.4, t1: Math.min(ln.end + 0.3, ln.start + 3), id: 'mouth-smile', prio: 1 });
      eyes.push({ t0: ln.start + 0.5, t1: Math.min(ln.end, ln.start + 2), id: 'eyes-smile', prio: 2 });
    } else if (ln.emotion === 'surprised') {
      eyes.push({ t0: ln.start + 0.3, t1: ln.start + 1.1, id: 'eyes-wide', prio: 2 });
      brows.push({ t0: ln.start + 0.3, t1: ln.start + 1.4, id: 'brows-up', prio: 2 });
    } else if (ln.emotion === 'thinking') {
      brows.push({ t0: ln.start + 0.3, t1: ln.end, id: 'brows-worry', prio: 2 });
    }
  }
  // blinks only when the eyes are plain open
  const eyeTr = sweep(eyes, 'eyes-open', duration);
  const openAt = (t) => { let id = 'eyes-open'; for (const [tt, s] of eyeTr) if (tt <= t) id = s; else break; return id === 'eyes-open'; };
  for (const [a, b] of blinkTimes(duration, seed)) if (openAt(a) && openAt(b)) eyes.push({ t0: a, t1: b, id: 'eyes-blink', prio: 9 });
  return {
    eyes: sweep(eyes, 'eyes-open', duration),
    brows: sweep(brows, 'brows-normal', duration),
    mouth: sweep(mouth, 'mouth-closed', duration),
  };
}
