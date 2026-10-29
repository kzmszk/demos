// Movement trace (proposal §4.0, comparison A): drives web/controls.js and the gondola ride through real listeners
// with trace/script.mjs on the synthetic world (trace/world.mjs) and writes the sampled state sequence as JSON.
//   node trace/run.mjs [--orig] [--flip-drag] [out.json]     (default: web/controls.js → trace/out.json)
//   node trace/compare.mjs trace/golden.json trace/out.json
// --orig drives trace/controls.orig.js, a byte-for-byte copy of web/controls.js before the shared/move migration;
// trace/golden.json is recorded from it and kept as the reference.  When the controls are a shared/move Mover, the
// run also records the {dt, cmds, frame} log, sends it through JSON, replays it on the pure core (command/step) on a
// fresh world that follows the same script, and checks that the replay lands on the same positions (core modes only;
// the boat is a client-only mode and places the camera itself).  film_page.js writes controls.vel directly, outside
// the Command log, so the first tick after a film op takes vel from the live run.
import './three-hook.mjs';
import { writeFileSync } from 'node:fs';

// --flip-drag negates every pointer coordinate, so each drag delta changes sign (the decision ② expectation, §4.0)
const args = process.argv.slice(2), orig = args.includes('--orig'), flip = args.includes('--flip-drag') ? -1 : 1;
const { FakeTarget, FakeCamera, installWindow, event } = await import('./fake.mjs');
const { makeApp } = await import('./app.mjs');
const { makeWorld } = await import('./world.mjs');
const { SCRIPT } = await import('./script.mjs');
const { Controls } = await import(orig ? './controls.orig.js' : '../web/controls.js');

const out = args.find((a) => !a.startsWith('--')) || new URL(orig ? './golden.json' : './out.json', import.meta.url).pathname;
const win = installWindow(), canvas = new FakeTarget(), camera = new FakeCamera(), world = makeWorld();
const A = makeApp({ camera, tiles: world, win, createControls: (ride) => new Controls(camera, canvas, { tiles: world, ride }) });
const c = A.controls, ride = A.ride;
const boat = () => (c.clientModes ? c.clientModes.boat : { yaw: c.boatYaw, pitch: c.boatPitch });
const rec = typeof c.startRecording === 'function' ? c.startRecording() : null, ticks = [];

const samples = [];
let label = '', velWritten = false;
const v3 = (v) => [v.x, v.y, v.z];
const sample = (op) => samples.push({ n: samples.length, label, op, mode: A.app.mode, cmode: c.mode, enabled: c.enabled,
  pos: v3(camera.position), dir: v3(camera.dir), yaw: c.yaw, pitch: c.pitch, vel: v3(c.vel), speed: c.speed, walkZ: c.walkZ,
  boat: [boat().yaw, boat().pitch], ride: [ride.pos.x, ride.pos.y, ride.heading, ride.vel, ride.steer.thrust, ride.steer.turn, ride.duck], rmode: ride.mode });

for (const op of SCRIPT) {
  const [type, ...a] = op;
  if (type === 'label') { label = a[0]; continue; }
  if (type === 'step') {
    for (let i = 0; i < a[0]; i++) {
      const vel0 = v3(c.vel);
      if (A.step(a[1])) { ticks.push({ pos: v3(camera.position), gate: world.gate, late: world.late, vel0: velWritten ? vel0 : null }); velWritten = false; }
      sample(`step ${a[1].toPrecision(4)}`);
    }
    continue;
  }
  if (type === 'keydown' || type === 'keyup') win.dispatchEvent(event(type, { code: a[0], key: a[0] }));
  else if (type === 'blur') win.dispatchEvent(event('blur'));
  else if (type.startsWith('pointer')) {
    const [x, y, o] = a;
    canvas.dispatchEvent(event(type, { clientX: flip * x, clientY: flip * y, pointerId: 1, pointerType: 'mouse', button: 0, ...o }));
  } else if (type === 'wheel') canvas.dispatchEvent(event('wheel', { deltaY: a[0] }));
  else if (type === 'gate' || type === 'late') world[type] = a[0];
  else if (type === 'start') A.start(a[0]);
  else if (type === 'film') { A.film(...a); velWritten = true; }
  else if (typeof A[type] === 'function') A[type](...a);
  else throw new Error('unknown op ' + type);
  sample(op.map((x) => (typeof x === 'object' ? JSON.stringify(x) : x)).join(' '));
}

const impl = rec ? 'shared/move Mover' : 'hand-written Controls';
writeFileSync(out, JSON.stringify({ impl, ops: SCRIPT.length, samples }, null, 0).replace(/\},\{/g, '},\n{') + '\n');
console.log(`${impl}: ${samples.length} samples → ${out}`);

if (rec) {
  const { fromPlain, command, step } = await import('../../../shared/move/index.js');
  const log = JSON.parse(JSON.stringify(rec)), w2 = makeWorld(), cw = { sample: (x, y) => w2.sample(x, y) };
  if (log.ticks.length !== ticks.length) throw new Error(`replay: ${log.ticks.length} ticks recorded, ${ticks.length} updates run`);
  const s = fromPlain(log.initial);
  let worst = 0, n = 0;
  log.ticks.forEach((t, i) => {
    w2.gate = ticks[i].gate; w2.late = ticks[i].late;
    for (const cmd of t.cmds) command(s, cmd, cw, c.cfg);
    if (ticks[i].vel0) s.vel.set(...ticks[i].vel0);
    if (!c.cfg.modes[s.mode]) return;
    if (t.frame) step(s, t.frame, t.dt, cw, c.cfg);
    if (s.status === 'hold') return;
    n++;
    worst = Math.max(worst, ...[s.pos.x, s.pos.y, s.pos.z].map((v, j) => Math.abs(v - ticks[i].pos[j])));
  });
  console.log(`replay of ${log.ticks.length} ticks on the core (${n} compared): max |Δpos| = ${worst.toExponential(2)}`);
  if (!(worst <= 1e-6)) { console.error('replay does not match'); process.exitCode = 1; }
}
