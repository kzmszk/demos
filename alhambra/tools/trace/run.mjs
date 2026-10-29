// Movement trace (proposal §4.0, comparison A): drives the movement glue of web/main.js through real listeners with
// trace/script.mjs on the stand-in palace (trace/world.mjs) and writes the sampled state sequence as JSON.
//   node trace/run.mjs [--orig] [out.json]      (default: app.mjs on web/controls.js → trace/out.json)
//   node trace/compare.mjs trace/golden.json trace/out.json
// --orig drives trace/app.orig.mjs, the glue as it was in main.js before the shared/move migration; golden.json is
// recorded from it.  Every sample holds the camera (position, quaternion, rotation order), yaw / pitch as main.js
// holds them, what the minimap last read, the orbit sphere, the touch stick and ▲▼, the tour flag, whether the event
// was default-prevented, canvas focus calls, and every nav.move(dx, dz) call made since the previous sample.
import { writeFileSync } from 'node:fs';
import { PerspectiveCamera } from 'three';
import { makeEnv, event } from './fake.mjs';
import { makeNav } from './world.mjs';
import { SCRIPT } from './script.mjs';

const args = process.argv.slice(2), orig = args.includes('--orig');
const { makeApp } = await import(orig ? './app.orig.mjs' : './app.mjs');
const out = args.find((a) => !a.startsWith('--')) || new URL(orig ? './golden.json' : './out.json', import.meta.url).pathname;

const env = makeEnv(), nav = makeNav(), camera = new PerspectiveCamera(63, 16 / 9, 0.08, 6500);
let moves = [];
const navMove = nav.move.bind(nav);
nav.move = (pos, dx, dz) => { if (pos === camera.position) moves.push([dx, dz]); return navMove(pos, dx, dz); };
const A = makeApp({ camera, nav, ...env });

const samples = [];
let label = '';
const sample = (op, prevented = null) => {
  const s = A.state();
  samples.push({ n: samples.length, label, op, mode: s.mode, tour: s.tour, place: s.place, order: camera.rotation.order,
    pos: camera.position.toArray(), quat: camera.quaternion.toArray(), yaw: s.yaw, pitch: s.pitch, map: s.map,
    orb: s.orb, stick: s.stick, alt: s.alt, prevented, focus: env.canvas.focused, moves });
  moves = [];
};

const targets = { canvas: env.canvas, joy: env.joy, rise: env.rise, descend: env.descend };
for (const op of SCRIPT) {
  const [type, ...a] = op;
  if (type === 'label') { label = a[0]; continue; }
  if (type === 'step') {
    for (let i = 0; i < a[0]; i++) { env.ms += a[1] * 1000; A.step(a[1]); sample(`step ${a[1].toPrecision(4)}`); }
    continue;
  }
  let e = null;
  if (type === 'keydown' || type === 'keyup') env.win.dispatchEvent(e = event(type, { key: a[0], ...a[1] }));
  else if (type === 'blur') env.win.dispatchEvent(e = event('blur'));
  else if (type === 'hidden') { env.doc.hidden = a[0]; env.doc.dispatchEvent(e = event('visibilitychange')); }
  else if (type.startsWith('pointer')) {
    const [x, y, o = {}] = a, { on = 'canvas', ...p } = o;
    targets[on].dispatchEvent(e = event(type, { clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', button: 0, ...p }));
  } else if (type === 'wheel') env.canvas.dispatchEvent(e = event('wheel', { deltaY: a[0] }));
  else if (type === 'dialog') env.dialogs[a[0]] = a[1];
  else if (typeof A[type] === 'function') A[type](...a);
  else throw new Error('unknown op ' + type);
  sample(op.map((x) => (typeof x === 'object' ? JSON.stringify(x) : x)).join(' '), e ? e.defaultPrevented : null);
}

const impl = orig ? 'main.js glue before shared/move' : 'shared/move Mover (web/controls.js)';
writeFileSync(out, JSON.stringify({ impl, ops: SCRIPT.length, samples }, null, 0).replace(/\},\{/g, '},\n{') + '\n');
console.log(`${impl}: ${samples.length} samples → ${out}`);
