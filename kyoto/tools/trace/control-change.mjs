// Checks for the control-change commit (decisions ①②, proposal §4.0), on traces from run.mjs:
//   node trace/run.mjs --flip-drag /tmp/expect.json   (before the change: the drag expectation)
//   node trace/run.mjs /tmp/new.json; node trace/run.mjs --flip-drag /tmp/new-flip.json   (after it)
//   node trace/control-change.mjs trace/golden.json /tmp/expect.json /tmp/new.json /tmp/new-flip.json
import { readFileSync } from 'node:fs';
const L = (f) => JSON.parse(readFileSync(f, 'utf8')).samples;
const ang = (d) => ((((d) % (2 * Math.PI)) + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;
const TOL = 1e-6;
const diff = (x, y) => Math.max(...x.pos.map((v, j) => Math.abs(v - y.pos[j])), ...x.dir.map((v, j) => Math.abs(v - y.dir[j])),
  Math.abs(ang(x.yaw - y.yaw)), Math.abs(x.pitch - y.pitch), ...x.vel.map((v, j) => Math.abs(v - y.vel[j])),
  Math.abs(x.speed - y.speed), x.walkZ === null || y.walkZ === null ? (x.walkZ === y.walkZ ? 0 : Infinity) : Math.abs(x.walkZ - y.walkZ),
  x.mode === y.mode && x.cmode === y.cmode && x.enabled === y.enabled ? 0 : Infinity);

function sections(name, a, b) {
  console.log(`\n== ${name}`);
  const sec = {};
  a.forEach((x, i) => {
    const s = (sec[x.label] ??= { n: 0, bad: 0, max: 0, first: null });
    const d = diff(x, b[i]); s.n++; s.max = Math.max(s.max, d);
    if (!(d <= TOL)) { s.bad++; if (s.first === null) s.first = `${i} "${x.op}"`; }
  });
  for (const [l, s] of Object.entries(sec)) console.log(`  ${l}: ${s.n} samples, ${s.bad} differ, max Δ ${s.max.toExponential(2)}${s.first ? ', first at ' + s.first : ''}`);
}

// the yaw each step adds, compared step by step (so a pose carried over from earlier does not count)
function turnSteps(name, a, b) {
  console.log(`\n== per-step Δyaw, ${name}`);
  const groups = {};
  for (let i = 1; i < a.length; i++) {
    if (!a[i].op.startsWith('step')) continue;
    const da = ang(a[i].yaw - a[i - 1].yaw), db = ang(b[i].yaw - b[i - 1].yaw);
    const g = (groups[`${a[i].label} dt=${a[i].op.split(' ')[1]}`] ??= { steps: 0, turning: 0, same: 0, diff: 0, ex: null });
    g.steps++; if (da || db) g.turning++;
    if (Math.abs(da - db) <= 1e-9) g.same++; else { g.diff++; g.ex ??= `n=${i} ${da.toFixed(6)} vs ${db.toFixed(6)}`; }
  }
  for (const [k, g] of Object.entries(groups)) console.log(`  ${k}: ${g.steps} steps (${g.turning} turning), equal ${g.same}, differ ${g.diff}${g.ex ? ' (e.g. ' + g.ex + ')' : ''}`);
}

function yawOffset(name, a, b) {
  console.log(`\n== yaw offset (a − b) by section, ${name}`);
  const sec = {};
  a.forEach((x, i) => { const k = ang(x.yaw - b[i].yaw).toFixed(6); const s = (sec[x.label] ??= new Map()); s.set(k, (s.get(k) || 0) + 1); });
  for (const [l, m] of Object.entries(sec)) console.log(`  ${l}: ${[...m].map(([k, c]) => `${k}×${c}`).join(', ')}`);
}

// the sign of each pointermove's yaw/pitch change against the pointer delta
function dragDir(name, s) {
  const last = {}; let n = 0, still = 0, yw = 0, ya = 0, pw = 0, pa = 0, pc = 0;
  for (let i = 1; i < s.length; i++) {
    const p = s[i].op.split(' ');
    if (!p[0].startsWith('pointer')) continue;
    const x = +p[1], y = +p[2], id = (p[3] ? JSON.parse(p.slice(3).join(' ')) : {}).pointerId ?? 1;
    if (p[0] === 'pointerdown') { last[id] = [x, y]; continue; }
    if (p[0] !== 'pointermove' || !last[id]) continue;
    const dx = x - last[id][0], dy = y - last[id][1]; last[id] = [x, y];
    const dyaw = ang(s[i].yaw - s[i - 1].yaw), dp = s[i].pitch - s[i - 1].pitch;
    if (!dyaw && !dp) { still++; continue; }
    n++;
    if (dx) Math.sign(dyaw) === Math.sign(dx) ? yw++ : ya++;
    if (dy) { if (!dp) pc++; else Math.sign(dp) === Math.sign(dy) ? pw++ : pa++; }
  }
  console.log(`\n== drag direction, ${name}: ${n} drag events that turned the view (${still} did not: no drag held, or disabled)`);
  console.log(`  yaw with dx ${yw}, against ${ya};  pitch with dy ${pw}, against ${pa}, held at the limit ${pc}`);
}

const [gold, expD, nw, nwFlip] = process.argv.slice(2).map(L);
sections('turning only: new with the drag flipped back vs golden', nwFlip, gold);
turnSteps('new with the drag flipped back vs golden', nwFlip, gold);
yawOffset('new with the drag flipped back vs golden', nwFlip, gold);
sections('both: new vs the drag expectation', nw, expD);
turnSteps('new vs the drag expectation', nw, expD);
dragDir('golden', gold);
dragDir('new', nw);
