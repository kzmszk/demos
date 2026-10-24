import * as THREE from 'three';

// On foot. The street and the roofs as something to stand on: the 1 m footprint mask says where a building stands,
// the 4 m roof raster how high it is, the rubble mounds of the fallen floors and the abandoned cars add their own
// heights. Moving into something more than a step higher stops you (and is a wall you can climb); a roof edge stops
// you unless the drop is small. Everything here is in data axes (x east, y north, z up).

const STEP = 0.55, DROP = 3.2, R = 0.4;         // R: half the shoulders plus the eye's distance from a facade (the camera near plane)

export function makeWalker({ ground, roof, foot, rubble }) {
  // rubble mounds: a coarse grid of indices, a cone with a rounded top
  const G = 64, cells = new Map();
  for (let i = 0; i < rubble.length; i++) {
    const [x, y, , r] = rubble[i];
    for (let gx = Math.floor((x - r) / G); gx <= Math.floor((x + r) / G); gx++)
      for (let gy = Math.floor((y - r) / G); gy <= Math.floor((y + r) / G); gy++) { const k = gx * 100003 + gy; (cells.get(k) || cells.set(k, []).get(k)).push(i); }
  }
  const mound = (x, y) => {
    const l = cells.get(Math.floor(x / G) * 100003 + Math.floor(y / G)); if (!l) return -Infinity;
    let h = -Infinity;
    for (const i of l) {
      const [mx, my, zb, r, hg] = rubble[i]; const d = Math.hypot(x - mx, y - my) / r; if (d >= 1) continue;
      h = Math.max(h, zb + hg * (d < 0.55 ? 1 - 0.38 * (d / 0.55) ** 2 : 0.62 * (1 - (d - 0.55) / 0.45)));
    }
    return h;
  };
  // cars: oriented boxes (set later, the props load after the city)
  let cars = null; const CG = 16, carCells = new Map();
  function setCars(data, stride, type = null) {
    // half length / half width / roof height per car (from the props' own car types when given)
    const n = data.length / stride, dims = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const t = type?.(i), bus = data[i * stride + 6] > 0.5;
      dims[i * 3] = t?.L ? t.L / 2 : bus ? 5.4 : 2.0; dims[i * 3 + 1] = t?.W ? t.W / 2 : bus ? 1.2 : 0.82; dims[i * 3 + 2] = t?.roof || (bus ? 3.1 : 1.35);
    }
    cars = { data, stride, dims }; carCells.clear();
    for (let i = 0; i < data.length / stride; i++) {
      const o = i * stride, k = Math.floor(data[o] / CG) * 100003 + Math.floor(data[o + 1] / CG);
      for (const dx of [-1, 0, 1]) for (const dy of [-1, 0, 1]) { const kk = k + dx * 100003 + dy; (carCells.get(kk) || carCells.set(kk, []).get(kk)).push(i); }
    }
  }
  const car = (x, y) => {
    if (!cars) return -Infinity;
    const l = carCells.get(Math.floor(x / CG) * 100003 + Math.floor(y / CG)); if (!l) return -Infinity;
    const d = cars.data, s = cars.stride; let h = -Infinity;
    for (const i of l) {
      const o = i * s, c = Math.cos(d[o + 3]), sn = Math.sin(d[o + 3]), bus = d[o + 6] > 0.5;
      const ex = x - d[o], ey = y - d[o + 1], u = ex * c + ey * sn, v = -ex * sn + ey * c;
      const D = cars.dims, k = i * 3;
      if (Math.abs(u) < D[k] && Math.abs(v) < D[k + 1]) h = Math.max(h, d[o + 2] + 0.12 + (d[o + 5] > 0.5 && !bus ? 0.25 : D[k + 2]));
    }
    return h;
  };
  // tree trunks: circles that stop you (not something to climb or stand on)
  let trees = null; const treeCells = new Map();
  function setTrees(data, stride) {
    trees = { data, stride }; treeCells.clear();
    for (let i = 0; i < data.length / stride; i++) {
      const o = i * stride, k = Math.floor(data[o] / CG) * 100003 + Math.floor(data[o + 1] / CG);
      for (const dx of [-1, 0, 1]) for (const dy of [-1, 0, 1]) { const kk = k + dx * 100003 + dy; (treeCells.get(kk) || treeCells.set(kk, []).get(kk)).push(i); }
    }
  }
  const trunk = (x, y) => {
    if (!trees) return false;
    const l = treeCells.get(Math.floor(x / CG) * 100003 + Math.floor(y / CG)); if (!l) return false;
    const d = trees.data, s = trees.stride;
    for (const i of l) { const o = i * s, r = 0.38 * d[o + 3]; if ((x - d[o]) ** 2 + (y - d[o + 1]) ** 2 < r * r) return true; }
    return false;
  };
  // other boxes to stand on or bump into (the trains left on the tracks): [x, y, yaw, half length, half width, top z]
  const boxes = [], boxCells = new Map();
  function addBoxes(list) {
    for (const b of list) {
      const i = boxes.length; boxes.push(b);
      const r = Math.hypot(b[3], b[4]);
      for (let gx = Math.floor((b[0] - r) / CG); gx <= Math.floor((b[0] + r) / CG); gx++)
        for (let gy = Math.floor((b[1] - r) / CG); gy <= Math.floor((b[1] + r) / CG); gy++) { const k = gx * 100003 + gy; (boxCells.get(k) || boxCells.set(k, []).get(k)).push(i); }
    }
  }
  const box = (x, y) => {
    const l = boxCells.get(Math.floor(x / CG) * 100003 + Math.floor(y / CG)); if (!l) return -Infinity;
    let h = -Infinity;
    for (const i of l) { const [bx, by, a, hl, hw, top] = boxes[i], c = Math.cos(a), s = Math.sin(a), ex = x - bx, ey = y - by;
      if (Math.abs(ex * s + ey * c) < hl && Math.abs(ex * c - ey * s) < hw) h = Math.max(h, top); }
    return h;
  };
  // the highest roof cell around a solid metre (the 4 m raster can miss the edge of what the mask covers)
  const roofNear = (x, y) => { let t = roof.top(x, y); if (t > -Infinity) return t; for (const [dx, dy] of [[3, 0], [-3, 0], [0, 3], [0, -3]]) t = Math.max(t, roof.top(x + dx, y + dy)); return t; };
  // what you stand on at a point
  // the hand-built districts: their collision field is the whole truth inside them (hero.js)
  let field = null;
  function surface(x, y) {
    const g = ground(x, y);
    if (field) { const f = field(x, y); if (f !== null) return Math.max(g, f, box(x, y)); }
    let z = Math.max(g, mound(x, y), car(x, y), box(x, y));
    if (foot.solid(x, y)) { const t = roofNear(x, y); if (t > z) z = t; }
    return z;
  }
  // what you stand on: the highest surface under your feet (a small disc)
  function under(x, y) {
    let z = surface(x, y);
    for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + 0.4; z = Math.max(z, surface(x + Math.cos(a) * 0.25, y + Math.sin(a) * 0.25)); }
    return z;
  }
  // what is in the way of your shoulders at feet height z: how many points of a wider ring stand higher than a step
  function overlap(x, y, z) {
    let n = 0;
    for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4, px = x + Math.cos(a) * R, py = y + Math.sin(a) * R; if (surface(px, py) > z + STEP || trunk(px, py)) n++; }
    return n;
  }
  const out = { z: 0, wall: null };
  // try to move the feet (x, y at height z) by (dx, dy); returns the new position in `res` and whether it moved.
  // Starting half inside something (a landing next to a wall), any move that leaves less of it in the way is allowed.
  function tryMove(x, y, z, dx, dy, res, cur) {
    const nx = x + dx, ny = y + dy, nz = under(nx, ny);
    if (nz > z + STEP) { res.blocked = nz; return false; }                 // a wall (or a car) higher than a step
    if (nz < z - DROP) { res.edge = true; return false; }                  // a roof edge: stay up here
    const ov = overlap(nx, ny, Math.max(z, nz));
    if (ov > 0 && (cur === 0 || ov >= cur)) { res.blocked = z + STEP + 1; return false; }
    res.x = nx; res.y = ny; res.z = nz; return true;
  }
  return {
    surface, under, mound, car, setCars, setTrees, addBoxes, trunk, out, foot, setField(fn) { field = fn; },
    // the height of a wall right in front of you (within `reach` m along heading h), or null when none is climbable
    wallAhead(x, y, z, h, reach = 1.1) {
      const c = Math.sin(h), s = Math.cos(h);
      for (let d = 0.4; d <= reach; d += 0.35) {
        const t = surface(x + c * d, y + s * d);
        if (t > z + STEP) {
          // the top: walk the column up until there is a surface you could stand on beyond the face
          let top = t;
          for (let e = d + 0.5; e <= d + 4; e += 0.5) top = Math.max(top, surface(x + c * e, y + s * e));
          return { top, dist: d };
        }
      }
      return null;
    },
    // the nearest climbable wall in a fan around heading h (you rarely face a facade square on): { top, dist, h }
    wallNear(x, y, z, h, reach = 1.6) {
      let best = null;
      for (const o of [0, 0.3, -0.3, 0.6, -0.6, 0.9, -0.9]) {
        const w = this.wallAhead(x, y, z, h + o, reach - Math.abs(o) * 0.3);
        if (w && (!best || w.dist < best.dist - 0.1)) best = { ...w, h: h + o };
      }
      return best;
    },
    // a step of walking: slide along walls (try the move, then each axis)
    move(x, y, z, dx, dy) {
      const cur = overlap(x, y, z);
      const res = { x, y, z, blocked: null, edge: false };
      if (tryMove(x, y, z, dx, dy, res, cur)) return res;
      const r2 = { x, y, z, blocked: null, edge: false };
      if (Math.abs(dx) > 1e-4 && tryMove(x, y, z, dx, 0, r2, cur)) return { ...r2, blocked: res.blocked, edge: res.edge };
      const r3 = { x, y, z, blocked: null, edge: false };
      if (Math.abs(dy) > 1e-4 && tryMove(x, y, z, 0, dy, r3, cur)) return { ...r3, blocked: res.blocked, edge: res.edge };
      return res;
    },
    // open ground to land on: no building, car or mound within r metres
    open(x, y, r = 3) {
      if (foot.solid(x, y)) return false;
      for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; if (foot.solid(x + Math.cos(a) * r, y + Math.sin(a) * r)) return false; }
      return car(x, y) === -Infinity && mound(x, y) === -Infinity && box(x, y) === -Infinity;
    },
  };
}
