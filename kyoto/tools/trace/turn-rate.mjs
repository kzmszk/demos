// Decision ① check: hold ←/→ (with and without W) for the same simulated time at several frame rates, in walk and fly,
// through the real listeners, and print the yaw turned.  --orig runs trace/controls.orig.js (0.025 rad per frame).
//   node trace/turn-rate.mjs [--orig]
import './three-hook.mjs';
const orig = process.argv.includes('--orig');
const { FakeTarget, FakeCamera, installWindow, event } = await import('./fake.mjs');
const { makeApp } = await import('./app.mjs');
const { makeWorld } = await import('./world.mjs');
const { Controls } = await import(orig ? './controls.orig.js' : '../web/controls.js');

const win = installWindow();
const run = (mode, hz, keys, seconds) => {
  const canvas = new FakeTarget(), camera = new FakeCamera(), world = makeWorld();
  const A = makeApp({ camera, tiles: world, ground: world.farGround,
    createControls: () => new Controls(camera, canvas, { tiles: world, ground: world.farGround }) });
  A.start('walk'); A.walkAt(5, 5, 0.3); if (mode === 'fly') A.button('fly');
  for (let i = 0; i < 10; i++) A.step(1 / 60);
  const y0 = A.controls.yaw;
  for (const k of keys) win.dispatchEvent(event('keydown', { code: k, key: k }));
  for (let i = 0; i < Math.round(seconds * hz); i++) A.step(1 / hz);
  for (const k of keys) win.dispatchEvent(event('keyup', { code: k, key: k }));
  A.controls.dispose?.();
  return A.controls.yaw - y0;
};
console.log(orig ? 'controls.orig.js (before the migration)' : 'web/controls.js');
for (const mode of ['walk', 'fly'])
  for (const keys of [['ArrowLeft'], ['ArrowRight'], ['ArrowLeft', 'KeyW']]) {
    const r = [30, 60, 144].map((hz) => `${hz} Hz ${run(mode, hz, keys, 2).toFixed(9)}`);
    console.log(`  ${mode} ${keys.join('+')} for 2 s:  ${r.join('   ')}`);
  }
