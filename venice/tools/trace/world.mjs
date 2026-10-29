// A deterministic stand-in for tiles.sample (0.5 m cells, {z, water}; z null where not walkable — buildings, water —,
// undefined where no tile is loaded) and the canal routes.  Layout (x, y in m; ground 1.1 m unless noted):
//   canal   y −30…−20 (x < 80), water; the routes run along it      bridge  x 20–24 over it, y −34…−16, +0.15 m per 0.5 m
//   pillar  x 8–9, y 9.5–10.5 (building)                             house   x −10…−5, y 0–5 (building)
//   step    x 30–40, y 0–10 at 1.6 (0.5 m up: walkable)              high    x 30–40, y 10–20 at 2.2 (0.6 m up: not)
//   ledge   y ≥ 40 (x < 20) at 2.1 (1 m up: not)                     wall    x 45–46 except a 1 m gap at y 19.5–20.5
//   ramp    x 60–80, y 30–40, rising 0.05 per m                      gate    x 2–4, y 2–4: a building while world.gate
//   late    x ≥ 80 at 1.3, loaded only once world.late
// Everything beyond x −40…120, y −40…60 is not loaded.
const C = 0.5;
export function makeWorld() {
  const W = { gate: false, late: false };
  W.sample = (x, y) => {
    const cx = Math.floor(x / C) * C + C / 2, cy = Math.floor(y / C) * C + C / 2;
    if (cy < -40 || cy >= 60 || cx < -40 || cx >= 120) return { z: undefined, water: undefined };
    if (cx >= 80) return W.late ? land(1.3) : { z: undefined, water: undefined };
    const canal = cy >= -30 && cy < -20;
    if (cx >= 20 && cx < 24 && cy >= -34 && cy < -16) {
      const k = Math.floor((9 - Math.abs(cy + 25)) / C);
      return { z: 1.1 + 0.15 * Math.max(0, Math.min(14, k)), water: canal };
    }
    if (canal) return { z: null, water: true };
    if (cx >= 8 && cx < 9 && cy >= 9.5 && cy < 10.5) return wall();
    if (cx >= -10 && cx < -5 && cy >= 0 && cy < 5) return wall();
    if (cx >= 45 && cx < 46 && !(cy >= 19.5 && cy < 20.5)) return wall();
    if (W.gate && cx >= 2 && cx < 4 && cy >= 2 && cy < 4) return wall();
    if (cx >= 30 && cx < 40 && cy >= 0 && cy < 10) return land(1.6);
    if (cx >= 30 && cx < 40 && cy >= 10 && cy < 20) return land(2.2);
    if (cx >= 60 && cy >= 30 && cy < 40) return land(1.1 + 0.05 * (cx - 60));
    if (cy >= 40 && cx < 20) return land(2.1);
    return land(1.1);
  };
  return W;
}
const land = (z) => ({ z, water: false });
const wall = () => ({ z: null, water: false });

const route = (pts, names) => {
  let length = 0;
  for (let i = 1; i < pts.length; i++) length += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return { pts, length, names };
};
export const ROUTES = {
  grand: route([[-35, -25], [10, -25], [40, -24], [75, -25]], [[0, 'Canal'], [50, 'Bridge']]),
  back: route([[75, -25], [40, -26], [-35, -25]], [[0, 'Back']]),
};
