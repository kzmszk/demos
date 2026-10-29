// Core: venice's passability strategy for raster walking.  world.sample(x, y) → { z }, z null where not walkable
// (buildings, water) and undefined where no data is loaded.  A stride is taken when the walker's centre and four edge
// points (radius) all stand on loaded ground within `step` of its feet; otherwise along x alone (vel.y = 0), along y
// alone (vel.x = 0), or not at all (vel = 0).  venice/tools/bridge_check.py checks the bridges with the same rule.
export function strictStep({ radius = 0.24, step = 0.55 } = {}) {
  return { kind: 'strict', radius, step };
}

function free(g, world, x, y, z0) {
  const R = g.radius;
  for (const [ox, oy] of [[0, 0], [R, 0], [-R, 0], [0, R], [0, -R]]) {
    const z = world.sample(x + ox, y + oy).z;
    if (z === undefined) return false;
    if (z === null || Math.abs(z - z0) > g.step) return false;
  }
  return true;
}

export const strict = {
  accept: (g, world, x, y, w) => w.z != null && free(g, world, x, y, w.z),
  move(g, world, p, vel, dx, dy, z0) {
    if (free(g, world, p.x + dx, p.y + dy, z0)) { p.x += dx; p.y += dy; }
    else if (free(g, world, p.x + dx, p.y, z0)) { p.x += dx; vel.y = 0; }
    else if (free(g, world, p.x, p.y + dy, z0)) { p.y += dy; vel.x = 0; }
    else vel.set(0, 0, 0);
  },
  ground: (g, world, x, y) => world.sample(x, y).z,
};
