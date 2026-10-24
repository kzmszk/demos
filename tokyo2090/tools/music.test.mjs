// node tools/music.test.mjs  - checks the pure parts of web/music.js
import assert from 'node:assert/strict';
import {
  buildScore, noteToMidi, envelopePoints, makeImpulse, mulberry32, humanize,
  BPM, LOOP_GAP_S, ATTACK_S, RELEASE_S,
} from './web/music.js';

const s = buildScore();
assert.equal(BPM, 60);

// 1. bar count / duration
assert.equal(s.bars, 78, 'bar count');
assert.equal(s.beats, 234);
const totalS = s.beats * (60 / BPM);

// 2. every bar has a bass note on beat 1; chords on beats 2-3 (except the ending bars 37-39)
for (let b = 0; b < s.bars; b++) {
  const inBar = (n) => n[0] >= b * 3 && n[0] < b * 3 + 3;
  assert.ok(s.bass.some((n) => inBar(n) && n[0] === b * 3), `bar ${b + 1} lacks a bass note on beat 1`);
  assert.ok(s.chords.some(inBar), `bar ${b + 1} lacks a chord`);
}

// 3. pitch range and field sanity
for (const n of s.notes) {
  assert.ok(n[2] >= 36 && n[2] <= 96, `midi out of range: ${n}`);
  assert.ok(n[1] > 0 && n[0] >= 0 && n[0] + n[1] <= s.beats + 1e-9, `bad timing: ${n}`);
  assert.ok(n[3] > 0 && n[3] <= 1);
}
for (const c of s.chords) assert.ok(c[1] <= 3);

// 4. melody: opening theme, and no gap over 4 beats outside the 4-bar intros
const mel = [...s.melody].sort((a, b) => a[0] - b[0]);
const opening = mel.slice(0, 9).map((n) => n[2]);
assert.deepEqual(opening, [78, 81, 79, 78, 73, 71, 73, 74, 69], 'F#5 A5 G5 F#5 C#5 B4 C#5 D5 A4');
assert.equal(mel[0][0], 13, 'theme enters bar 5 beat 2');
const gaps = [];
for (let i = 1; i < mel.length; i++) {
  const gap = mel[i][0] - (mel[i - 1][0] + mel[i - 1][1]);
  if (gap > 4 + 1e-9) gaps.push({ afterBar: Math.floor(mel[i - 1][0] / 3) + 1, gap });
}
// the only long silences are the 4-bar intro of pass 2 (bars 40-43 in the 78-bar count)
assert.deepEqual(gaps.map((g) => g.afterBar), [39], 'unexpected melody gaps: ' + JSON.stringify(gaps));
console.log('melody gaps > 4 beats (intro of pass 2 only):', gaps);

// 5. final chord is D minor (second ending) and the first pass ends on D major
const lastBar = (s.bars - 1) * 3;
assert.deepEqual(s.chords.filter((n) => n[0] === lastBar).map((n) => n[2] % 12).sort((a, b) => a - b), [2, 5, 9]);
const firstEnd = 38 * 3;
assert.deepEqual(s.chords.filter((n) => n[0] === firstEnd).map((n) => n[2] % 12).sort((a, b) => a - b), [2, 6, 9]);

// 6. helpers
assert.equal(noteToMidi('C4'), 60);
assert.equal(noteToMidi('F#5'), 78);
const pts = envelopePoints(0.3, 2);
assert.equal(pts[0].t, 0);
assert.ok(Math.abs(pts[1].t - ATTACK_S) < 1e-12 && pts[1].v === 0.3);
assert.ok(Math.abs(pts[pts.length - 1].t - (2 + RELEASE_S)) < 1e-9);
for (let i = 2; i < pts.length; i++) assert.ok(pts[i].v <= pts[i - 1].v && pts[i].t > pts[i - 1].t, 'env must decay monotonically');
const r = mulberry32(1);
for (let i = 0; i < 1000; i++) {
  const h = humanize([0, 1, 60, 0.5], r);
  assert.ok(Math.abs(h.dt) <= 0.015 && Math.abs(h.vel - 0.5) <= 0.05 + 1e-12);
}
const ir = makeImpulse(8000, 2.5, mulberry32(3));
assert.equal(ir[0].length, 20000);
const rms = (a, i0, i1) => Math.sqrt(a.slice(i0, i1).reduce((x, y) => x + y * y, 0) / (i1 - i0));
assert.ok(rms(ir[0], 200, 2200) > 8 * rms(ir[0], 17000, 19000), 'impulse should decay');

const stat = (arr) => `${arr.length} notes`;
console.log(`bars: ${s.bars}  beats: ${s.beats}  duration: ${totalS} s at ${BPM} bpm (+${LOOP_GAP_S} s gap = ${totalS + LOOP_GAP_S} s loop)`);
console.log(`bass ${stat(s.bass)}, chords ${stat(s.chords)}, melody ${stat(s.melody)}, total ${stat(s.notes)}`);
console.log('pitch range:', Math.min(...s.notes.map((n) => n[2])), '-', Math.max(...s.notes.map((n) => n[2])));
console.log('ok');
