// A deterministic stand-in for tiles.sample (0.5 m cells, {z, blocked, water, covered, surf}; z undefined where no
// tile is loaded) and for far.js farGround.  Layout (x, y in m; ground 10 m unless noted):
//   pillar     x 8–9, y 9.5–10.5 blocked                stairs  x 20–30, +0.3 m per m (to 12.7), plateau x 30–40 at 13
//   ledge      y ≥ 40 (x < 20) at 11: 1 m up is too high  wall    x 45–46 blocked except a 1 m gap at y 19.5–20.5
//   ramp       x 60–80, rising 0.08 per m               house   x −10…−5, y 0–5 blocked, roof 18
//   gate       x 2–4, y 2–4 blocked while world.gate (ground that turns blocked under the walker, as a tile can)
//   late       x 80–120 at 12, loaded only once world.late (before that: z undefined, 'hold')
// Everything else, and |y| beyond −20…60, is not loaded.
const C = 0.5;
export function makeWorld() {
  const W = { gate: false, late: false };
  W.sample = (x, y) => {
    const cx = Math.floor(x / C) * C + C / 2, cy = Math.floor(y / C) * C + C / 2;
    if (cy < -20 || cy >= 60 || cx < -20 || cx >= 120) return { z: undefined };
    if (cx >= 80) return W.late ? cell(12, false) : { z: undefined };
    if (cx >= -10 && cx < -5 && cy >= 0 && cy < 5) return cell(18, true);
    if (cx >= 8 && cx < 9 && cy >= 9.5 && cy < 10.5) return cell(10, true);
    if (cx >= 45 && cx < 46 && !(cy >= 19.5 && cy < 20.5)) return cell(10, true);
    if (W.gate && cx >= 2 && cx < 4 && cy >= 2 && cy < 4) return cell(10, true);
    if (cx >= 20 && cx < 30) return cell(10 + 0.3 * Math.floor(cx - 20), false);
    if (cx >= 30 && cx < 40) return cell(13, false);
    if (cx >= 60) return cell(10 + 0.08 * (cx - 60), false);
    if (cy >= 40 && cx < 20) return cell(11, false);
    return cell(10, false);
  };
  W.farGround = (x, y) => 5 + 0.02 * x + 0.01 * y;
  return W;
}
const cell = (z, blocked) => ({ z, blocked, water: false, covered: false, surf: 0 });
