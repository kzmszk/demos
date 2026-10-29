// Compare two movement traces sample by sample (proposal §4.0: "match" = every compared quantity within 1e-6 m/rad
// at every sample; yaw and the orbit's theta modulo 2π; null must match null; the nav.move calls must be the same
// number with the same dx/dz).  Exit code 1 on any mismatch.
// The camera quaternion is compared at frame samples (after update(), what is rendered).  After a drag event the old
// handler had already turned the camera; the Mover turns it in the next update(), so event samples may differ there
// (counted and shown, not failed); yaw / pitch are compared at every sample.
//   node trace/compare.mjs trace/golden.json trace/out.json
import { readFileSync } from 'node:fs';
const TOL = 1e-6;
const [a, b] = process.argv.slice(2).map((f) => JSON.parse(readFileSync(f, 'utf8')));
const fail = (m) => { console.error(m); process.exit(1); };
if (a.samples.length !== b.samples.length) fail(`sample count differs: ${a.samples.length} vs ${b.samples.length}`);
const ang = (x, y) => { const d = (((x - y) % (2 * Math.PI)) + 3 * Math.PI) % (2 * Math.PI) - Math.PI; return Math.abs(d); };
const nz = (x, y, f = (u, v) => Math.abs(u - v)) => (x === null || y === null ? (x === y ? 0 : Infinity) : f(x, y));
const maxd = (u, v) => (u.length !== v.length ? Infinity : Math.max(0, ...u.map((x, j) => Math.abs(x - v[j]))));
// q and -q are the same rotation
const quat = (u, v) => Math.min(maxd(u, v), maxd(u, v.map((x) => -x)));
const worst = {}, at = {}, sections = {};
const note = (k, d, s) => { if (!(d <= (worst[k] ?? -1))) { worst[k] = d; at[k] = s.n; } };
let bad = 0, lag = 0, lagMax = 0;
for (let i = 0; i < a.samples.length; i++) {
  const x = a.samples[i], y = b.samples[i], frame = x.op.startsWith('step');
  if (x.op !== y.op || x.label !== y.label) fail(`sample ${i}: different ops (${x.op} / ${y.op})`);
  for (const k of ['mode', 'tour', 'place', 'order', 'prevented', 'focus']) {
    if (x[k] !== y[k]) { bad++; if (bad < 20) console.error(`sample ${i} (${x.label}: ${x.op}): ${k} ${x[k]} vs ${y[k]}`); }
  }
  const d = {
    pos: maxd(x.pos, y.pos), quat: frame ? quat(x.quat, y.quat) : 0, yaw: ang(x.yaw, y.yaw), pitch: Math.abs(x.pitch - y.pitch),
    map: nz(x.map, y.map, ang), orb: Math.max(maxd(x.orb.slice(0, 2), y.orb.slice(0, 2)), ang(x.orb[2], y.orb[2])),
    stick: maxd(x.stick, y.stick), alt: Math.abs(x.alt - y.alt),
    moves: x.moves.length !== y.moves.length ? Infinity : Math.max(0, ...x.moves.map((m, j) => maxd(m, y.moves[j]))),
  };
  for (const [k, v] of Object.entries(d)) {
    note(k, v, x);
    const s = (sections[x.label] ??= { n: 0, max: 0 }); s.max = Math.max(s.max, v);
    if (!(v <= TOL)) { bad++; if (bad < 20) console.error(`sample ${i} (${x.label}: ${x.op}): ${k} differs by ${v}`); }
  }
  sections[x.label].n++;
  if (!frame) { const q = quat(x.quat, y.quat); if (q > TOL) { lag++; lagMax = Math.max(lagMax, q); } }
}
const moves = a.samples.reduce((n, s) => n + s.moves.length, 0);
console.log(`${a.impl}  vs  ${b.impl}: ${a.samples.length} samples, ${moves} nav.move calls`);
for (const k of Object.keys(worst)) console.log(`  max |Δ${k}| = ${worst[k].toExponential(2)}  (sample ${at[k]})`);
for (const [l, s] of Object.entries(sections)) console.log(`  section ${l}: ${s.n} samples, max Δ ${s.max.toExponential(2)}`);
console.log(`  event samples with the camera turn still pending: ${lag} (max |Δquat| ${lagMax.toExponential(2)})`);
if (bad) fail(`${bad} values outside ${TOL}`);
console.log(`match (all within ${TOL})`);
