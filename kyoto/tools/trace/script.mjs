// The fixed input script for the movement trace (proposal §4.0 comparison A).  Every op goes through real listeners
// (window keydown/keyup/blur, canvas pointer*/wheel) or the app-level paths of main.js/ui.js (app.mjs), and the state
// is sampled after every op and every frame.  The world is trace/world.mjs (synthetic, deterministic).
// Sections: title, K = keys (incl. ←/→ turning at 0.025 rad/frame at 60/30/144 Hz), T = stick / ▲▼ / fast toggle,
// D = drag (both pitch-limit round trips, mouse and touch), M = mixed, G = glide cases (pillar, stairs, ledge, wall
// gap, escape from a blocked cell, hold and landing, ramp), F = fly (pitch-following flight, the ground clamp on the
// walk map and on farGround, up/down, wheel), S = mode switches (buttons, walkAt, place, look, the film hand-off).
// Deliberately absent (accepted fixes, proposal §4.1): blur during a drag, pointercancel, a second pointerId, keys
// typed into a text field.
const F60 = 1 / 60, F30 = 1 / 30, F144 = 1 / 144;
const k = (code) => ['keydown', code], ku = (code) => ['keyup', code];
const st = (n, dt = F60) => ['step', n, dt];
const pd = (x, y, o = {}) => ['pointerdown', x, y, o], pm = (x, y, o = {}) => ['pointermove', x, y, o], pu = (x, y, o = {}) => ['pointerup', x, y, o];
const drag = (x0, y0, pts, o = {}, every = 0) => [pd(x0, y0, o), ...pts.flatMap(([x, y]) => (every ? [pm(x, y, o), st(every)] : [pm(x, y, o)])), pu(...pts[pts.length - 1], o)];

export const SCRIPT = [
  ['label', 'title'], st(10), k('KeyW'), st(3), ku('KeyW'),
  ['start', 'walk'], st(3),
  ['label', 'K'],
  k('KeyW'), st(60), k('ShiftLeft'), st(30), ku('ShiftLeft'), st(20, F30),
  k('ArrowLeft'), st(40), st(20, F30), st(40, F144), ku('ArrowLeft'),
  k('ArrowRight'), st(30), ku('ArrowRight'), ku('KeyW'), st(30),
  k('KeyD'), st(30), k('KeyA'), st(10), ku('KeyD'), st(20), ku('KeyA'),
  k('KeyS'), k('ArrowDown'), st(20), ku('ArrowDown'), k('KeyW'), st(10), ku('KeyW'), ku('KeyS'), st(30),
  k('KeyW'), k('KeyD'), k('ShiftRight'), st(10, 0.1), ku('ShiftRight'), ku('KeyD'), k('ArrowUp'), st(20), ku('KeyW'), st(10), ku('ArrowUp'),
  k('KeyW'), st(10), ['blur'], st(20),
  // E/Q in walk: no effect on the walker
  k('KeyE'), k('KeyQ'), st(10), ku('KeyE'), ku('KeyQ'),
  ['label', 'T'],
  ['stick', 0.6, -0.8], st(40), ['stick', 1.5, 0.4], st(30), k('KeyW'), ['stick', -0.3, -0.9], st(20), ku('KeyW'), ['stickEnd'], st(20),
  ['fast'], ['stick', 0, -1], st(30), ['fast'], st(30), ['stickEnd'], st(30),
  ['vert', 1], st(5), ['vertOff', 1], st(5),
  ['label', 'D'],
  ...drag(400, 300, Array.from({ length: 10 }, (_, i) => [400 + 37 * (i + 1), 300 + 3 * (i + 1)]), { pointerId: 1 }, 2),
  // down past the lower limit (−1.5) and back, then up past the upper limit and back: clamped per event
  pd(500, 300, { pointerId: 1 }), ...[500, 700, 900, 1100].map((y) => pm(520, y, { pointerId: 1 })), st(2),
  ...[950, 800, 650].map((y) => pm(520, y, { pointerId: 1 })), st(2),
  ...[350, 50, -250, -550, -850].map((y) => pm(510, y, { pointerId: 1 })), st(2),
  pm(510, -700, { pointerId: 1 }), pm(505, -500, { pointerId: 1 }), pm(490, -300, { pointerId: 1 }), st(2),
  pu(490, -300, { pointerId: 1 }), pm(900, 0, { pointerId: 1 }), st(5),
  ...drag(100, 100, [[60, 140], [20, 150], [-40, 120]], { pointerId: 2, pointerType: 'touch' }), st(5),
  // the walk button while walking with pitch above 0.6 (setMode clamps it), then wheel in walk (ignored)
  ...drag(300, 300, [[300, 100], [300, -100]], { pointerId: 1 }), st(2), ['button', 'walk'], st(5),
  ['wheel', 100], ['wheel', -100], st(3),
  ['label', 'M'],
  k('KeyW'), k('ShiftLeft'), pd(500, 400, { pointerId: 1 }),
  ...Array.from({ length: 24 }, (_, i) => [pm(500 - 11 * (i + 1), 400 - 7 * (i + 1) + (i % 3) * 5, { pointerId: 1 }), st(1, i % 2 ? F60 : F30)]).flat(),
  k('ArrowRight'), ...Array.from({ length: 12 }, (_, i) => [pm(236 + 9 * (i + 1), 232 + 40 * (i + 1), { pointerId: 1 }), st(1, F144)]).flat(),
  pu(344, 712, { pointerId: 1 }), ku('ArrowRight'), ku('ShiftLeft'), ['stick', 0.5, 0], st(20), ['stickEnd'], ku('KeyW'), st(30),
  ['label', 'G'],
  // round the pillar
  ['walkAt', 5, 10.1, 0], k('KeyW'), st(240), ku('KeyW'), st(20),
  ['walkAt', 5, 9.7, 0.05], k('KeyW'), st(200), ku('KeyW'), st(20),
  // up the stairs at a run, turn about, down again
  ['walkAt', 17, 15, 0], k('KeyW'), k('ShiftLeft'), st(200), ku('ShiftLeft'), st(60), ku('KeyW'),
  k('ArrowLeft'), st(126), ku('ArrowLeft'), k('KeyW'), st(300), ku('KeyW'), st(30),
  // into the 1 m ledge head-on, then at a slant (slides along it)
  ['walkAt', 10, 38, Math.PI / 2], k('KeyW'), st(150), ku('KeyW'),
  ['walkAt', 10, 38.5, 1.2], k('KeyW'), st(150), ku('KeyW'), st(20),
  // down off the ledge
  ['walkAt', 10, 42, -Math.PI / 2], k('KeyW'), st(120), ku('KeyW'), st(20),
  // at the wall at a slant: side-steps to the 1 m gap and through
  ['walkAt', 43, 18.3, 0.25], k('KeyW'), st(300), ku('KeyW'), st(20),
  ['walkAt', 43, 22.5, -0.3], k('KeyW'), k('ShiftLeft'), st(200), ku('ShiftLeft'), ku('KeyW'), st(20),
  // the ground turns blocked under the walker: any move that keeps the height gets out
  ['walkAt', 3, 3, 0.7], st(5), ['gate', true], st(5), k('KeyW'), st(90), ku('KeyW'), st(20), ['gate', false],
  // a walkAt where nothing is loaded yet: 'hold' (turn keys still turn), then the tile arrives and the walker lands
  ['walkAt', 90, 10, 0], k('KeyW'), k('ArrowLeft'), st(20), ku('ArrowLeft'), ['late', true], st(60), ku('KeyW'), st(20),
  // the ramp and on to the late tile
  ['walkAt', 58, 30, 0], k('KeyW'), k('ShiftLeft'), st(360), ku('ShiftLeft'), ku('KeyW'), st(30),
  // a walkAt on the house roof (blocked): the spiral search lands beside it
  ['walkAt', -7, 2, 0], st(10), k('KeyS'), st(30), ku('KeyS'), st(10),
  ['label', 'F'],
  ['button', 'fly'], st(10), k('KeyW'), st(60),
  // dive: pitch down, the forward key follows the pitch, the ground clamp holds at +2 m
  ...drag(400, 300, [[400, 500], [400, 600]], { pointerId: 1 }), st(120), ku('KeyW'), st(20),
  k('KeyE'), st(30), k('Space'), k('KeyQ'), st(10), ku('KeyE'), ku('Space'), k('KeyC'), st(20), ku('KeyQ'), ku('KeyC'), st(10),
  ['vert', 1], st(20), k('KeyE'), st(10), ku('KeyE'), ['vertOff', 1], ['vert', -1], k('KeyQ'), st(400), ku('KeyQ'), ['vertOff', -1], st(10),
  ['fast'], k('KeyW'), st(30), ['fast'], k('ShiftLeft'), st(30), ku('ShiftLeft'), ku('KeyW'), st(30),
  // up again, look up, climb forward
  ...drag(400, 300, [[400, 0], [400, -200]], { pointerId: 1 }), k('KeyW'), st(60), ku('KeyW'), st(30),
  k('KeyW'), ...Array.from({ length: 5 }, () => [['wheel', 100], st(3)]).flat(),
  ...Array.from({ length: 30 }, () => ['wheel', 120]), st(10),
  ...Array.from({ length: 50 }, () => ['wheel', -100]), st(10),
  ['wheel', 53], ['wheel', -1], ['wheel', 0], st(20), ku('KeyW'), st(30),
  ...Array.from({ length: 12 }, () => ['wheel', 100]), st(5),
  // over ground that is not loaded: farGround clamps
  ['look', [10, 70, 30], [10, 90, 0]], k('KeyQ'), k('KeyW'), st(240), ku('KeyW'), ku('KeyQ'), st(20),
  ['look', [130, 10, 40], [140, 10, 0]], k('KeyW'), st(200), ku('KeyW'), st(20),
  ['stick', 0.7, -0.7], ['vert', -1], st(60), ['vertOff', -1], ['stickEnd'], st(30),
  ['label', 'S'],
  // fly → walk over unloaded ground: hold; then a place lands it
  ['look', [10, 70, 30], [10, 60, 25]], st(5), ['button', 'walk'], k('KeyW'), st(20), ku('KeyW'),
  ['place', 'stairs'], st(30), k('KeyW'), st(60), ku('KeyW'),
  ['place', 'air'], st(10), k('KeyW'), st(30), ku('KeyW'), st(10),
  ['place', 'start'], st(20), ['button', 'fly'], st(10), ['button', 'fly'], st(5), ['button', 'walk'], st(30),
  ['look', [20, 20, 25], [30, 25, 10]], k('KeyW'), st(30), ku('KeyW'),
  ['walkAt', 30, 5, 2.5], ...drag(0, 0, [[60, 30]], { pointerId: 1 }), st(30),
  // the film takes over: controls off, camera posed, vel written; keys and drag do nothing, the wheel still works
  ['film', [12, 12, 13], [20, 12, 12]], st(5), k('KeyW'), ...drag(0, 0, [[40, 40]], { pointerId: 1 }), st(10), ku('KeyW'),
  ['button', 'fly'], ['wheel', 100], ['wheel', 100], st(5),
];
