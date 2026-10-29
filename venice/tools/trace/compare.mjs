// Compare two movement traces sample by sample (proposal §4.0: "match" = every compared quantity within 1e-6 m/rad
// at every sample; yaw and the boat's heading compared modulo 2π; walkZ null must match null).  Exit code 1 on any
// mismatch.
//   node trace/compare.mjs trace/golden.json trace/out.json
import { readFileSync } from 'node:fs';
const TOL = 1e-6;
const [a, b] = process.argv.slice(2).map((f) => JSON.parse(readFileSync(f, 'utf8')));
const fail = (m) => { console.error(m); process.exit(1); };
if (a.samples.length !== b.samples.length) fail(`sample count differs: ${a.samples.length} vs ${b.samples.length}`);
const ang = (x, y) => { const d = (((x - y) % (2 * Math.PI)) + 3 * Math.PI) % (2 * Math.PI) - Math.PI; return Math.abs(d); };
const nz = (x, y) => (x === null || y === null ? (x === y ? 0 : Infinity) : Math.abs(x - y));
const maxd = (u, v) => Math.max(...u.map((x, j) => Math.abs(x - v[j])));
const worst = {}, at = {}, sections = {};
const note = (k, d, s) => { if (!(d <= (worst[k] ?? -1))) { worst[k] = d; at[k] = s.n; } };
let bad = 0;
for (let i = 0; i < a.samples.length; i++) {
  const x = a.samples[i], y = b.samples[i];
  if (x.op !== y.op || x.label !== y.label) fail(`sample ${i}: different ops (${x.op} / ${y.op})`);
  if (x.mode !== y.mode || x.cmode !== y.cmode || x.enabled !== y.enabled || x.rmode !== y.rmode) {
    bad++; console.error(`sample ${i} (${x.op}): mode/cmode/enabled/ride ${x.mode}/${x.cmode}/${x.enabled}/${x.rmode} vs ${y.mode}/${y.cmode}/${y.enabled}/${y.rmode}`);
  }
  const d = {
    pos: maxd(x.pos, y.pos), dir: maxd(x.dir, y.dir),
    yaw: ang(x.yaw, y.yaw), pitch: Math.abs(x.pitch - y.pitch),
    vel: maxd(x.vel, y.vel), speed: Math.abs(x.speed - y.speed), walkZ: nz(x.walkZ, y.walkZ),
    boat: maxd(x.boat, y.boat),
    ride: Math.max(maxd(x.ride.slice(0, 2), y.ride.slice(0, 2)), ang(x.ride[2], y.ride[2]), maxd(x.ride.slice(3), y.ride.slice(3))),
  };
  for (const [k, v] of Object.entries(d)) {
    note(k, v, x);
    const s = (sections[x.label] ??= { n: 0, max: 0 }); s.max = Math.max(s.max, v);
    if (!(v <= TOL)) { bad++; if (bad < 20) console.error(`sample ${i} (${x.label}: ${x.op}): ${k} differs by ${v}`); }
  }
  sections[x.label].n++;
}
console.log(`${a.impl}  vs  ${b.impl}: ${a.samples.length} samples`);
for (const k of Object.keys(worst)) console.log(`  max |Δ${k}| = ${worst[k].toExponential(2)}  (sample ${at[k]})`);
for (const [l, s] of Object.entries(sections)) console.log(`  section ${l}: ${s.n} samples, max Δ ${s.max.toExponential(2)}`);
if (bad) fail(`${bad} values outside ${TOL}`);
console.log(`match (all within ${TOL})`);
