// The fixed input script for the movement trace (proposal §4.0 comparison A).  Every op is replayed through real
// listeners (window keydown/keyup, canvas pointer*/wheel) and app-level actions (the Free button, F key, VAT.look /
// stopLoop), and the state is sampled after every op and every frame.
// Sections: K = keys only, D = drag (incl. both pitch-limit round trips), M = mixed (drag + keys while moving),
// W = wheel speed, S = mode switches (title → free → tour → free, look, stopLoop).  No T: vatican has no stick.
// Deliberately absent (accepted bug fixes, proposal §4.1): blur while keys are held, pointercancel, a second
// pointerId.  Keep the script deterministic: no time, no randomness.
const F60 = 1 / 60, F30 = 1 / 30, F144 = 1 / 144;
const k = (code) => ['keydown', code], ku = (code) => ['keyup', code];
const st = (n, dt = F60) => ['step', n, dt];
const pd = (x, y, o = {}) => ['pointerdown', x, y, o], pm = (x, y, o = {}) => ['pointermove', x, y, o], pu = (x, y, o = {}) => ['pointerup', x, y, o];

export const SCRIPT = [
  // title: the scripted camera owns the view; F does nothing in title (main.js:170)
  ['label', 'title'], st(10), k('KeyF'), ku('KeyF'), st(5),
  ['label', 'K'], ['free'], st(3),
  k('KeyW'), st(90), k('ShiftLeft'), st(30), ku('KeyW'), ku('ShiftLeft'), st(60, F30),
  k('ArrowUp'), k('ArrowRight'), st(40, F144), ku('ArrowUp'), ku('ArrowRight'),
  k('ArrowLeft'), k('KeyA'), k('ArrowDown'), st(30), ku('ArrowLeft'), ku('KeyA'), ku('ArrowDown'),
  k('KeyE'), st(20), k('Space'), k('KeyQ'), st(10), ku('KeyE'), ku('Space'), k('KeyC'), st(20), ku('KeyQ'), ku('KeyC'),
  k('KeyS'), k('KeyD'), k('ShiftRight'), st(20, 0.1), ku('KeyS'), ku('KeyD'), ku('ShiftRight'),
  k('KeyW'), k('KeyS'), st(10), ku('KeyW'), ku('KeyS'), st(40),
  ['label', 'D'],
  pd(400, 300, { pointerId: 1 }),
  ...Array.from({ length: 10 }, (_, i) => [pm(400 + 37 * (i + 1), 300 + 3 * (i + 1), { pointerId: 1 }), st(2)]).flat(),
  // down past the lower pitch limit and back (clamped per event)
  pm(770, 500, { pointerId: 1 }), pm(770, 700, { pointerId: 1 }), pm(770, 900, { pointerId: 1 }), pm(770, 1100, { pointerId: 1 }), st(2),
  pm(770, 950, { pointerId: 1 }), pm(770, 800, { pointerId: 1 }), pm(770, 650, { pointerId: 1 }), st(2),
  // up past the upper limit and back
  ...[350, 50, -250, -550, -850].map((y) => pm(760, y, { pointerId: 1 })), st(2),
  pm(760, -700, { pointerId: 1 }), pm(755, -500, { pointerId: 1 }), pm(740, -300, { pointerId: 1 }), st(2),
  pu(740, -300, { pointerId: 1 }), pm(900, 0, { pointerId: 1 }), st(5),
  // a touch drag (vatican uses the same coefficient for touch)
  pd(100, 100, { pointerId: 1, pointerType: 'touch' }), pm(60, 140, { pointerId: 1, pointerType: 'touch' }), pm(20, 150, { pointerId: 1, pointerType: 'touch' }),
  pu(20, 150, { pointerId: 1, pointerType: 'touch' }), st(5),
  ['label', 'M'],
  k('KeyW'), k('ShiftLeft'), pd(500, 400, { pointerId: 1 }),
  ...Array.from({ length: 24 }, (_, i) => [pm(500 - 11 * (i + 1), 400 - 7 * (i + 1) + (i % 3) * 5, { pointerId: 1 }), st(1, i % 2 ? F60 : F30)]).flat(),
  k('ArrowRight'), ...Array.from({ length: 12 }, (_, i) => [pm(236 + 9 * (i + 1), 232 + 40 * (i + 1), { pointerId: 1 }), st(1, F144)]).flat(),
  pu(344, 712, { pointerId: 1 }), ku('ArrowRight'), ku('ShiftLeft'), k('KeyE'), st(20), ku('KeyE'), ku('KeyW'), st(30),
  ['label', 'W'],
  k('KeyW'), ...Array.from({ length: 5 }, () => [['wheel', 100], st(3)]).flat(),
  ...Array.from({ length: 30 }, () => ['wheel', 120]), st(10),
  ...Array.from({ length: 45 }, () => ['wheel', -100]), st(10),
  ['wheel', 53], ['wheel', -1], ['wheel', 0], st(20), ku('KeyW'), st(20),
  ['label', 'S'],
  // F → tour: controls disabled, keys still collected, wheel still changes speed, drag ignored (origin kept)
  k('KeyF'), ku('KeyF'), st(10), k('KeyW'), ['wheel', 100], pd(300, 300, { pointerId: 1 }), pm(340, 320, { pointerId: 1 }), st(10),
  // F → free: syncFromCamera from the scripted pose; W still held; the drag resumes against its old origin
  k('KeyF'), ku('KeyF'), st(10), pm(360, 330, { pointerId: 1 }), st(10), pu(360, 330, { pointerId: 1 }), ku('KeyW'), st(20),
  ['look', [100, 50, 30], [0, 0, 20]], k('KeyD'), st(30), ku('KeyD'),
  ['stopLoop'], k('KeyW'), st(10), pd(0, 0, { pointerId: 1 }), pm(50, 50, { pointerId: 1 }), pu(50, 50, { pointerId: 1 }), st(5),
  ['look', [-50, 20, 60], [-200, 0, 10]], st(30), ku('KeyW'), st(60),
];
