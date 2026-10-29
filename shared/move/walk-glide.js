// Core: kyoto's passability strategy for raster walking.  world.sample(x, y) → { z, blocked }, z undefined where no
// data is loaded.  A stride is fine when it ends on open ground; pressed to a wall, any stride but one toward a blocked
// side; otherwise the stride is turned (glide), side-stepped toward a nearby opening, tried along x or y alone, or
// halved.  Standing in a blocked cell, any move that keeps the height is allowed out (`through`).
export function glideStep({ radius = 0.12, up = 0.75, down = 1.2 } = {}) {
  return { kind: 'glide', radius, up, down };
}

// ground under a walker standing at z0: the height, null where blocked / too high a step, undefined where not loaded
function at(g, world, x, y, z0, through = false) {
  const w = world.sample(x, y);
  if (w.z === undefined) return undefined;
  if ((w.blocked && !through) || w.z - z0 > g.up || z0 - w.z > g.down) return null;
  return w.z;
}
// how many of the walker's edge points stand on blocked ground (Infinity: its centre does)
function cost(g, world, x, y, z0, through = false) {
  const R = g.radius;
  let n = 0;
  for (const [ox, oy] of [[0, 0], [R, 0], [-R, 0], [0, R], [0, -R]]) {
    if (at(g, world, x + ox, y + oy, z0, through) == null) { if (!ox && !oy) return Infinity; n++; }
  }
  return n;
}
const free = (g, world, x, y, z0, through = false) => cost(g, world, x, y, z0, through) === 0;
function can(g, world, x0, y0, x, y, z0, through) {
  const c = cost(g, world, x, y, z0, through), R = g.radius;
  if (c === 0) return true;
  if (c === Infinity) return false;
  for (const [ox, oy] of [[R, 0], [-R, 0], [0, R], [0, -R]]) {
    if (at(g, world, x + ox, y + oy, z0, through) == null && (x - x0) * ox + (y - y0) * oy > 0) return false;
  }
  return true;
}

export const glide = {
  accept: (g, world, x, y, w) => w.z != null && !w.blocked && free(g, world, x, y, w.z),
  // moves p by (dx, dy) or what the walls leave of it; may change vel
  move(g, world, p, vel, dx, dy, z0) {
    const thr = cost(g, world, p.x, p.y, z0) === Infinity;
    if (can(g, world, p.x, p.y, p.x + dx, p.y + dy, z0, thr)) { p.x += dx; p.y += dy; return; }
    const L = Math.hypot(dx, dy); let moved = false;
    for (const t of [0.35, -0.35, 0.7, -0.7, 1.2, -1.2]) {
      const c = Math.cos(t), s = Math.sin(t), ex = (dx * c - dy * s) * Math.cos(t), ey = (dx * s + dy * c) * Math.cos(t);
      if (L > 1e-6 && can(g, world, p.x, p.y, p.x + ex, p.y + ey, z0, thr)) { p.x += ex; p.y += ey; moved = true; break; }
    }
    if (!moved && L > 1e-6) {
      // the walk map's 0.5 m cells make stairs of a slanting rail
      const fx = dx / L, fy = dy / L, sx = -fy, sy = fx;
      let side = 0;
      for (const k of [0.2, 0.4, 0.7, 1.0]) {
        if (free(g, world, p.x + fx * 0.3 + sx * k, p.y + fy * 0.3 + sy * k, z0, thr)) { side = 1; break; }
        if (free(g, world, p.x + fx * 0.3 - sx * k, p.y + fy * 0.3 - sy * k, z0, thr)) { side = -1; break; }
      }
      const ex = sx * side * L, ey = sy * side * L;
      if (side && can(g, world, p.x, p.y, p.x + ex, p.y + ey, z0, thr)) { p.x += ex; p.y += ey; moved = true; }
    }
    if (!moved) {
      if (can(g, world, p.x, p.y, p.x + dx, p.y, z0, thr)) { p.x += dx; vel.y = 0; }
      else if (can(g, world, p.x, p.y, p.x, p.y + dy, z0, thr)) { p.y += dy; vel.x = 0; }
      else { vel.x *= 0.5; vel.y *= 0.5; vel.z *= 0.5; }
    }
  },
  // the height the eye follows
  ground: (g, world, x, y, z0) => at(g, world, x, y, z0, true),
};
