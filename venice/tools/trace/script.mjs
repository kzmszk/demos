// The fixed input script for the movement trace (proposal §4.0 comparison A).  Every op goes through real listeners
// (window keydown/keyup/blur, canvas pointer*/wheel) or the app-level paths of main.js / film_page.js (app.mjs), and
// the state is sampled after every op and every frame.  The world is trace/world.mjs (synthetic, deterministic).
// Sections: title, K = keys (incl. ←/→ turning at 0.02 rad/frame at 60/30/144 Hz), T = touch stick, D = drag (both
// pitch-limit round trips, mouse and touch), M = mixed, W = strict walking (pillar head-on and at a slant, a building
// corner, 0.5 m step up, 0.6 m and 1 m too high, the wall, over the bridge and off its sides, the canal edge, ground
// turning blocked underfoot, hold and landing, ramp, spiral searches), F = fly (keys, drag, wheel to both limits),
// B = gondola (mode bar and route starts, look-around drag to both limits, turn keys, R rowing with keys and stick, the
// bank, back to autopilot, stepping off to walk and to fly), S = places, look, the film hand-off.
// Deliberately absent (accepted fixes, proposal §4.1): blur during a drag, pointercancel, a second pointerId, keys
// typed into a text field; also ← and → held together (the old code turned by −0.02 then +0.02).
const F60 = 1 / 60, F30 = 1 / 30, F144 = 1 / 144;
const k = (code) => ['keydown', code], ku = (code) => ['keyup', code];
const st = (n, dt = F60) => ['step', n, dt];
const pd = (x, y, o = {}) => ['pointerdown', x, y, o], pm = (x, y, o = {}) => ['pointermove', x, y, o], pu = (x, y, o = {}) => ['pointerup', x, y, o];
const drag = (x0, y0, pts, o = {}, every = 0) => [pd(x0, y0, o), ...pts.flatMap(([x, y]) => (every ? [pm(x, y, o), st(every)] : [pm(x, y, o)])), pu(...pts[pts.length - 1], o)];
// both look limits, there and back: down then up past the pitch limit, then far right and far left (the boat's ±2.6)
const roundTrips = [
  pd(500, 300), ...[500, 700, 900, 1100].map((y) => pm(520, y)), st(2),
  ...[950, 800, 650].map((y) => pm(520, y)), st(2),
  ...[350, 50, -250, -550, -850].map((y) => pm(510, y)), st(2),
  pm(510, -700), pm(505, -500), pm(490, -300), st(2),
  ...[900, 1300, 1700].map((x) => pm(x, -300)), st(2), ...[1500, 1200].map((x) => pm(x, -300)), st(2),
  ...[600, 0, -600, -1100].map((x) => pm(x, -300)), st(2), ...[-900, -500].map((x) => pm(x, -300)), st(2),
  pu(-500, -300), pm(900, 0), st(5),
];

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
  ['stick', 0, -1], k('ShiftLeft'), st(30), ku('ShiftLeft'), ['stickEnd'], st(30),
  ['label', 'D'],
  ...drag(400, 300, Array.from({ length: 10 }, (_, i) => [400 + 37 * (i + 1), 300 + 3 * (i + 1)]), {}, 2),
  ...roundTrips,
  ...drag(100, 100, [[60, 140], [20, 150], [-40, 120]], { pointerId: 2, pointerType: 'touch' }), st(5),
  // the walk button while walking with pitch above 0.5 (setMode clamps it), then wheel in walk (ignored)
  ...drag(300, 300, [[300, 100], [300, -100]]), st(2), ['button', 'walk'], st(5),
  ['wheel', 100], ['wheel', -100], st(3),
  ['label', 'M'],
  k('KeyW'), k('ShiftLeft'), pd(500, 400),
  ...Array.from({ length: 24 }, (_, i) => [pm(500 - 11 * (i + 1), 400 - 7 * (i + 1) + (i % 3) * 5), st(1, i % 2 ? F60 : F30)]).flat(),
  k('ArrowRight'), ...Array.from({ length: 12 }, (_, i) => [pm(236 + 9 * (i + 1), 232 + 40 * (i + 1)), st(1, F144)]).flat(),
  pu(344, 712), ku('ArrowRight'), ku('ShiftLeft'), ['stick', 0.5, 0], st(20), ['stickEnd'], ku('KeyW'), st(30),
  ['label', 'W'],
  // the pillar head-on (stops, vel 0 on x), then at a slant (slides along it)
  ['walkAt', 5, 10, 0], k('KeyW'), st(200), ku('KeyW'), st(20),
  ['walkAt', 5, 9.7, 0.3], k('KeyW'), st(200), ku('KeyW'), st(20),
  // into the house's corner
  ['walkAt', -13, -3, 0.75], k('KeyW'), k('ShiftLeft'), st(150), ku('ShiftLeft'), ku('KeyW'), st(20),
  // up the 0.5 m step, then north into the 0.6 m one, then back down
  ['walkAt', 25, 5, 0], k('KeyW'), st(300), ku('KeyW'), k('ArrowLeft'), st(78), ku('ArrowLeft'), k('KeyW'), st(300), ku('KeyW'),
  k('KeyS'), st(60), k('KeyA'), st(200), ku('KeyA'), ku('KeyS'), st(20),
  // into the 1 m ledge head-on, then at a slant
  ['walkAt', 10, 38, Math.PI / 2], k('KeyW'), st(150), ku('KeyW'),
  ['walkAt', 10, 38.5, 1.2], k('KeyW'), st(150), ku('KeyW'), st(20),
  // along the wall at a slant, to the gap and through
  ['walkAt', 43, 18.3, 0.25], k('KeyW'), st(300), ku('KeyW'), st(20),
  ['walkAt', 43, 22.5, -0.3], k('KeyW'), k('ShiftLeft'), st(200), ku('ShiftLeft'), ku('KeyW'), st(20),
  // over the bridge at a run, off its side towards the canal, then down the far end
  ['place', 'bridge'], st(10), k('KeyW'), k('ShiftLeft'), st(130), ku('ShiftLeft'), ku('KeyW'),
  k('KeyD'), st(120), ku('KeyD'), k('KeyA'), st(60), ku('KeyA'), k('KeyW'), st(300), ku('KeyW'), st(20),
  // the canal edge, head-on and at a slant
  ['walkAt', 0, -17, -Math.PI / 2], k('KeyW'), st(120), ku('KeyW'),
  ['walkAt', 0, -17, -1.3], k('KeyW'), st(200), ku('KeyW'), st(20),
  // the ground turns blocked under the walker: stuck
  ['walkAt', 3, 3, 0.7], st(5), ['gate', true], st(5), k('KeyW'), st(90), ku('KeyW'), st(20), ['gate', false], k('KeyW'), st(30), ku('KeyW'),
  // a walkAt where nothing is loaded yet: 'hold' (turn keys still turn), then the tile arrives and the walker lands
  ['walkAt', 90, 10, 0], k('KeyW'), k('ArrowLeft'), st(20), ku('ArrowLeft'), ['late', true], st(60), ku('KeyW'), st(20),
  // up the ramp to the late tile's 0.8 m drop
  ['walkAt', 58, 35, 0], k('KeyW'), k('ShiftLeft'), st(400), ku('ShiftLeft'), ku('KeyW'), st(30),
  // walkAt on the house and in the canal: the spiral search lands beside them
  ['walkAt', -7, 2, 0], st(10), k('KeyS'), st(30), ku('KeyS'), st(10),
  ['walkAt', 5, -25, 1], st(10), k('KeyW'), st(30), ku('KeyW'), st(10),
  ['label', 'F'],
  ['button', 'fly'], st(10), k('KeyW'), st(60),
  ...drag(400, 300, [[400, 500], [400, 600]]), st(120), ku('KeyW'), st(20),
  k('KeyE'), st(30), k('Space'), k('KeyQ'), st(10), ku('KeyE'), ku('Space'), k('KeyC'), st(20), ku('KeyQ'), ku('KeyC'), st(10),
  k('KeyW'), k('KeyD'), st(30), k('ShiftLeft'), st(30), ku('ShiftLeft'), ku('KeyD'), ku('KeyW'), st(30),
  ['stick', 0.7, -0.7], k('KeyE'), st(60), ku('KeyE'), ['stickEnd'], st(30),
  k('ArrowRight'), k('KeyW'), st(40), ku('ArrowRight'), st(20, F30), ku('KeyW'), st(10),
  ...drag(400, 300, [[400, 0], [400, -200]]), k('KeyW'), st(60), ku('KeyW'), st(30),
  k('KeyW'), ...Array.from({ length: 5 }, () => [['wheel', 100], st(3)]).flat(),
  ...Array.from({ length: 30 }, () => ['wheel', -120]), st(10),
  ...Array.from({ length: 50 }, () => ['wheel', 100]), st(10),
  ['wheel', 53], ['wheel', -1], ['wheel', 0], st(20), ku('KeyW'), st(30),
  ...Array.from({ length: 6 }, () => ['wheel', -100]), st(5),
  ['label', 'B'],
  // a route start from fly: seated on the autopilot; look around to both limits; wheel ignored
  ['route', 'grand', 5, 1], st(60), ...roundTrips, ['wheel', 100], st(5),
  ...drag(100, 100, [[60, 140], [20, 150], [-40, 120]], { pointerId: 2, pointerType: 'touch' }), st(5),
  // keys on the autopilot: W/S do nothing to the boat; ←/→ still turn yaw (unseen in the boat)
  k('KeyW'), k('ArrowLeft'), st(30), ku('ArrowLeft'), k('ArrowRight'), st(10, F30), ku('ArrowRight'), ku('KeyW'), st(10),
  ['speedButton', 2], st(120), ['speedButton', 1],
  // R: rowing.  Forward, steer with D and A, the stick, into the bank (bounces), astern, back to the autopilot
  k('KeyR'), ku('KeyR'), k('KeyW'), st(200), k('KeyD'), st(60), ku('KeyD'), k('KeyA'), st(120), ku('KeyA'), st(60), ku('KeyW'),
  ['stick', 0.8, -0.6], st(120), ['stick', -1, 0], st(200), ['stickEnd'], st(30),
  k('KeyW'), k('KeyA'), st(400), ku('KeyA'), st(200), ku('KeyW'), k('KeyS'), st(120), ku('KeyS'), st(20),
  ...drag(300, 300, [[350, 320], [420, 330]]), st(10),
  k('KeyR'), ku('KeyR'), st(60),
  // stepping off onto the fondamenta (spiral search from the water), walk on
  ['button', 'walk'], st(20), k('KeyW'), st(60), ku('KeyW'), st(10),
  // the mode bar's boat (no new route: the ride is where the autopilot took it)
  ['button', 'boat'], st(30), ['button', 'walk'], st(20),
  // a route start over the walker, under the bridge (the gondolier ducks), then off to fly from the seat
  ['route', 'back', 40, 1.5], st(30), ...drag(200, 200, [[260, 180]]), st(500),
  ['button', 'fly'], st(10), k('KeyW'), st(30), ku('KeyW'), st(10),
  ['mode', 'boat'], st(30), ['button', 'boat'], st(10), ['button', 'walk'], st(30),
  ['label', 'S'],
  ['place', 'start'], st(20), ['place', 'air'], st(10), k('KeyW'), st(30), ku('KeyW'), st(10),
  ['look', [20, 20, 25], [30, 25, 10]], k('KeyW'), st(30), ku('KeyW'),
  ['walkAt', 30, 5, 2.5], ...drag(0, 0, [[60, 30]]), st(30), ['shotPitch', 0.35], st(10),
  // the film takes over: controls off, the pose function moves the camera; keys and drag do nothing, the wheel still
  // works in fly
  ['film', 'walk'], st(5), k('KeyW'), ...drag(0, 0, [[40, 40]]), st(10), ku('KeyW'), ['filmEnd'], st(10),
  ['film', 'fly'], st(5), ['wheel', 100], ['wheel', 100], st(5), ['filmEnd'], k('KeyW'), st(10), ku('KeyW'),
  ['film', 'boat'], st(10), ['filmEnd'], st(10), ['button', 'fly'], st(10),
  // disabled without a pose (film_page between shots): nothing moves, keys are still collected
  ['disable'], k('KeyW'), k('ArrowLeft'), st(10), ...drag(0, 0, [[30, 30]]), ['enable'], st(10), ku('ArrowLeft'), ku('KeyW'),
  ['button', 'walk'], st(30),
];
