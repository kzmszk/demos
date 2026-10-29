// The fixed input script for the movement trace (proposal §4.0 comparison A).  Every op goes through real listeners
// (window keydown/keyup/blur, document visibilitychange, canvas pointer*/wheel, the #joystick / #rise / #descend
// elements) or the app-level paths of main.js (setMode, go, startTour, pauseInput, ALH.look / move / filmFrame), and
// the state is sampled after every op and every frame.  The world is trace/world.mjs.
// Sections: init (the load sequence, then walking before any drag), K = keys (60/30/144 Hz and the 0.05 s cap; ←/→
// strafe, alhambra has no turn keys), I = ignored and released input (dialogs, a text field, blur, hidden, unbound
// keys), T = touch stick and ▲▼, D = drag (mouse and touch, both pitch-limit round trips, a non-primary button, drags
// pending when setMode / go run before the next frame), W = walking into the stand-in palace, F = fly (keys, ▲▼,
// clamps), O = orbit (drag incl. the phi limits, wheel to both radius limits, the stick leaving it), R = guided tour
// (the whole minute, and stopped by each kind of input), S = ALH.look / move / filmFrame, M = mixed.
// Deliberately absent (accepted differences, see the migration commit): a second pointerId during a drag, a pointerup
// / pointercancel / lostpointercapture from another pointer, and visibilitychange during a drag.
const F60 = 1 / 60, F30 = 1 / 30, F144 = 1 / 144, CAP = 0.05;
const k = (key, o) => ['keydown', key, o], ku = (key, o) => ['keyup', key, o];
const st = (n, dt = F60) => ['step', n, dt];
const pd = (x, y, o = {}) => ['pointerdown', x, y, o], pm = (x, y, o = {}) => ['pointermove', x, y, o], pu = (x, y, o = {}) => ['pointerup', x, y, o];
const drag = (x0, y0, pts, o = {}, every = 0) => [pd(x0, y0, o), ...pts.flatMap(([x, y]) => (every ? [pm(x, y, o), st(every)] : [pm(x, y, o)])), pu(...pts[pts.length - 1], o)];
const joy = (x, y) => ['pointermove', x, y, { on: 'joy', pointerId: 7, pointerType: 'touch' }];
// pitch to both limits and back (±1.48 at .003/px), then far right and far left
const roundTrips = [
  pd(500, 300), ...[500, 700, 900, 1100].map((y) => pm(520, y)), st(2),
  ...[950, 800, 650].map((y) => pm(520, y)), st(2),
  ...[350, 50, -250, -550, -850].map((y) => pm(510, y)), st(2),
  pm(510, -700), pm(505, -500), pm(490, -300), st(2),
  ...[900, 1300, 1700].map((x) => pm(x, -300)), st(2), ...[1500, 1200].map((x) => pm(x, -300)), st(2),
  ...[600, 0, -600, -1100].map((x) => pm(x, -300)), st(2), pu(-1100, -300), st(2),
];

export const SCRIPT = [
  ['label', 'init'], ['init'], st(5),
  // the load sequence leaves the camera rolled (main.js sets rotation.order after a lookAt in XYZ); walk in it
  k('w'), st(30), ku('w'), k('d'), st(10), ku('d'), st(3),
  ['label', 'K'],
  k('w'), st(60), k('Shift'), st(30), ku('Shift'), st(20, F30), st(30, F144), st(10, CAP),
  k('W', { shiftKey: true }), k('Shift'), st(10), ku('Shift'), ku('W'), st(5),
  k('ArrowLeft'), st(20), ku('ArrowLeft'), k('ArrowRight'), st(20), ku('ArrowRight'), ku('w'), st(10),
  k('d'), st(20), k('a'), st(10), ku('d'), st(20), ku('a'),
  k('s'), k('ArrowDown'), st(20), ku('ArrowDown'), k('ArrowUp'), st(10), ku('ArrowUp'), ku('s'), st(10),
  k('w'), k('d'), k('Shift'), st(10, CAP), ku('Shift'), ku('d'), k('ArrowUp'), st(20), ku('w'), st(10), ku('ArrowUp'),
  k('e'), k('q'), st(10), ku('e'), ku('q'), st(2),
  ['label', 'I'],
  k('w'), st(10), ['blur'], st(10),
  k('a'), st(10), ['hidden', true], st(5), ['hidden', false], st(5),
  k('x'), k('m'), k('Escape'), k('w', { repeat: true }), st(10), ku('w'), ku('x'), ku('m'), st(5),
  ['dialog', 'help', true], k('w'), st(10), ['dialog', 'help', false], st(5),
  k('d'), ['dialog', 'references', true], ku('d'), st(5), k('s'), st(5), ['dialog', 'references', false], st(5),
  k('a', { target: { tagName: 'INPUT' } }), k('s', { target: { tagName: 'TEXTAREA' } }), st(5),
  k('w'), ku('w', { target: { tagName: 'SELECT' } }), st(5),
  k('d'), st(10), ['pauseInput'], st(10),
  ['label', 'T'],
  ['pointerdown', 24, 0, { on: 'joy', pointerId: 7, pointerType: 'touch' }], st(30),
  joy(48, 24), st(20), joy(60, 60), st(20), k('w'), joy(30, 10), st(20), ku('w'), joy(24, 24), st(5),
  joy(10, 0), k('Shift'), st(20), ku('Shift'),
  ['pointerup', 10, 0, { on: 'joy', pointerId: 7, pointerType: 'touch' }], st(10),
  ['pointerdown', 40, 30, { on: 'joy', pointerId: 7, pointerType: 'touch' }], st(10), ['blur'], st(5),
  ['pointerdown', 0, 0, { on: 'rise', pointerId: 8, pointerType: 'touch' }], st(10), ['pointerup', 0, 0, { on: 'rise', pointerId: 8 }],
  ['label', 'D'],
  ...drag(400, 300, Array.from({ length: 10 }, (_, i) => [400 + 37 * (i + 1), 300 + 3 * (i + 1)]), {}, 2),
  ...roundTrips,
  ...drag(100, 100, [[60, 140], [20, 150], [-40, 120]], { pointerId: 2, pointerType: 'touch' }), st(5),
  pd(300, 300, { button: 2 }), pm(500, 400, { button: 2 }), st(3), pu(500, 400, { button: 2 }),
  pm(600, 600), st(2),
  // several drag events between two frames
  pd(200, 200), pm(230, 210), pm(260, 190), pm(250, 260), st(1), pm(240, 240), pm(200, 250), st(1), pu(200, 250), st(2),
  // a drag still pending when setMode / go run (main.js's handlers run between pointermove and the next frame)
  pd(300, 300), pm(340, 320), ['setMode', 'walk'], st(2), pm(380, 330), ['setMode', 'fly'], st(5), pm(420, 310), ['setMode', 'walk'], st(5), pu(420, 310),
  pd(300, 300), pm(360, 330), ['go', 'lions'], st(2), pm(400, 350), st(2), pu(400, 350), st(2),
  ['label', 'W'],
  ['go', 'lions'],
  // south-west onto the low step, east into the too-high step, back through the doorway in the wall at z=17
  ...drag(0, 0, [[-300, 0]]), k('w'), st(60), ku('w'), ...drag(0, 0, [[-524, 0]]), k('w'), st(90), ku('w'),
  ['look', 28, 1.65, 25, 28, 1.65, 10], ['setMode', 'walk'], k('w'), st(150), ku('w'), k('d'), st(40), k('w'), st(40), ku('w'), ku('d'),
  // the pillar head-on and at a slant, then up the ramp onto the terrace and off its far end
  ['look', 31, 1.65, 26, 31, 1.65, 0], ['setMode', 'walk'], k('w'), st(120), ku('w'),
  ['look', 30.7, 1.65, 26, 31, 1.65, 0], ['setMode', 'walk'], k('w'), st(120), ku('w'),
  ['look', 28, 1.65, 28, 28, 1.65, 40], ['setMode', 'walk'], k('w'), k('Shift'), st(200), ku('Shift'), st(60), ku('w'),
  k('s'), st(60), ku('s'), st(2),
  ['label', 'F'],
  ['setMode', 'fly'], k('e'), st(60), ku('e'), k('w'), k('Shift'), st(60), ku('Shift'), k('q'), st(200), ku('q'), ku('w'), st(5),
  ['pointerdown', 0, 0, { on: 'rise', pointerId: 8, pointerType: 'touch' }], st(30), ['pointerup', 0, 0, { on: 'rise', pointerId: 8 }],
  ['pointerdown', 0, 0, { on: 'descend', pointerId: 9, pointerType: 'touch' }], st(120), k('e'), st(10), ku('e'), ['pointercancel', 0, 0, { on: 'descend', pointerId: 9 }], st(5),
  ...drag(500, 500, [[560, 480], [620, 470]], {}, 3), k('w'), st(30), ku('w'),
  ['wheel', 100], ['wheel', -100], st(3),
  ['look', 1790, 849, 0, 1800, 849, 0], k('d'), k('e'), st(30), ku('d'), ku('e'), k('a'), st(10), ku('a'),
  ['look', -2195, 30, 1695, -2300, 30, 1800], k('w'), st(20), ku('w'),
  // into walk from 6 m+ above the floor (back to the place) and from just above it (dropped onto the floor)
  ['look', 60, 60, 60, 70, 55, 60], ['setMode', 'walk'], st(5),
  ['look', 60, 9, 60, 70, 8, 60], ['setMode', 'walk'], st(5), k('w'), st(30), ku('w'),
  ['look', 28, 3, 25, 40, 2, 25], ['setMode', 'walk'], st(5),
  ['label', 'O'],
  ['setMode', 'orbit'], st(10),
  ...drag(500, 400, Array.from({ length: 8 }, (_, i) => [500 - 40 * (i + 1), 400 + 25 * (i + 1)]), {}, 1),
  pd(500, 400), ...[600, 800, 1000].map((y) => pm(500, y)), st(2), ...[700, 300, -100, -500].map((y) => pm(500, y)), st(2), pm(500, -300), pu(500, -300), st(2),
  ...Array.from({ length: 12 }, () => ['wheel', 300]), st(2), ...Array.from({ length: 20 }, () => ['wheel', -400]), st(2), ['wheel', 150], st(2),
  k('w'), st(10), ku('w'), ['pointerdown', 30, 10, { on: 'joy', pointerId: 7, pointerType: 'touch' }], st(20), ['pointerup', 30, 10, { on: 'joy', pointerId: 7 }], st(5),
  ['go', 'overview'], ['setMode', 'fly'], st(5), ['setMode', 'orbit'], ['setMode', 'walk'], st(5),
  ['label', 'R'],
  ['go', 'lions'], ['startTour'], ...Array.from({ length: 61 }, () => st(30, F30)), st(5),
  ['go', 'sisters'], ['startTour'], st(100), k('w'), st(10), ku('w'),
  ['startTour'], st(50), pd(10, 10), st(5), pu(10, 10),
  ['startTour'], st(50), pd(10, 10, { button: 1 }), st(5), ['pointerdown', 24, 24, { on: 'joy', pointerId: 7 }], st(5), ['pointerup', 24, 24, { on: 'joy', pointerId: 7 }],
  ['startTour'], st(50), ['pointerdown', 0, 0, { on: 'rise', pointerId: 8 }], st(5), ['pointerup', 0, 0, { on: 'rise', pointerId: 8 }],
  ['go', 'justice'], ['startTour'], st(20), ['wheel', 100], st(1), ['stopTour'], ['go', 'overview'], ['startTour'], st(20), ['wheel', 100], st(5),
  ['startTour'], st(20), k('Escape'), st(5), ['startTour'], st(20), ['pauseInput'], st(5), ['startTour'], st(10), ['setMode', 'fly'], st(5),
  ['label', 'S'],
  ['look', 10, 40, 10, 60, 0, -20], st(5), ['move', 1, 2], st(3), ['go', 'myrtles'], ['move', 0.5, -3], st(3),
  ['filmFrame', 'lions', 0.3], ['filmFrame', 'lions', 0.8], ['filmFrame', 'overview', 0.5], ['filmFrame', 'vela', 0.2], st(5),
  ['go', 'lions'], ...drag(0, 0, [[30, -20]]), ['filmFrame', 'lions', 0.5], st(2),
  ['label', 'M'],
  ['go', 'lions'], k('w'), k('Shift'), pd(500, 400),
  ...Array.from({ length: 24 }, (_, i) => [pm(500 - 11 * (i + 1), 400 - 7 * (i + 1) + (i % 3) * 5), st(1, i % 2 ? F60 : F30)]).flat(),
  ['pointerdown', 40, 20, { on: 'joy', pointerId: 7, pointerType: 'touch' }],
  ...Array.from({ length: 12 }, (_, i) => [pm(236 + 9 * (i + 1), 232 + 20 * (i + 1)), st(1, F144)]).flat(),
  pu(344, 472), ku('Shift'), ['pointerup', 40, 20, { on: 'joy', pointerId: 7 }], st(20), ku('w'), st(10),
  ['setMode', 'fly'], k('w'), pd(0, 0), ...Array.from({ length: 10 }, (_, i) => [pm(-15 * (i + 1), 10 * (i + 1)), st(1)]).flat(), pu(-150, 100), ku('w'), st(5),
];
