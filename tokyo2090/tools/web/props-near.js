// Near level of detail for the props: what the walking player meets within ~140 m. Cars are lofted from a side
// profile (wheel arches, window openings, interior, tyres on rims) and trees are built from a buttressed trunk, a few
// main branches and several hundred alpha-tested leaf cards. This file holds the geometry generators and the
// shaders; props.js decides which records are near and fills the InstancedMeshes. Nothing here touches the scene.
// Local axes: x = nose of the car, y up, z = the car's right; trees stand on y = 0 with the crown about 10 m high.
import { shadowGLSL } from './light.js';

export const NEAR_BAND = 14;                 // metres over which the far and near levels dither into each other

const rngOf = (a) => () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

// ---------------------------------------------------------------------------------------------------- vector helpers
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const len = (a) => Math.hypot(a[0], a[1], a[2]);
const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const mix3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// Non-indexed mesh builder. exN floats of extra attributes per vertex. Every triangle's winding is flipped if needed so that
// its face normal agrees with the vertex normals (the materials are double sided and flip the normal on back faces).
function builder(exN) {
  const pos = [], nor = [], uv = [], ex = [];
  const vert = (p, n, t, e) => { pos.push(p[0], p[1], p[2]); nor.push(n[0], n[1], n[2]); uv.push(t[0], t[1]); for (let i = 0; i < exN; i++) ex.push(e[i]); };
  const tri = (p0, p1, p2, n0, n1, n2, t0, t1, t2, e0, e1, e2) => {
    const fn = cross(sub(p1, p0), sub(p2, p0));
    if (len(fn) < 1e-9) return;
    if (dot(fn, add(add(n0, n1), n2)) < 0) { [p1, p2] = [p2, p1]; [n1, n2] = [n2, n1]; [t1, t2] = [t2, t1]; [e1, e2] = [e2, e1]; }
    vert(p0, n0, t0, e0); vert(p1, n1, t1, e1); vert(p2, n2, t2, e2);
  };
  // quad with per-corner normals / uvs / extras (arrays of 4); corners go round the quad
  const quad = (P, N, T, E) => { tri(P[0], P[1], P[2], N[0], N[1], N[2], T[0], T[1], T[2], E[0], E[1], E[2]); tri(P[0], P[2], P[3], N[0], N[2], N[3], T[0], T[2], T[3], E[0], E[2], E[3]); };
  // flat quad whose normal points away from `hint`
  const flat = (P, T, e, hint) => {
    let n = norm(cross(sub(P[1], P[0]), sub(P[2], P[0])));
    const c = mul(add(add(P[0], P[1]), add(P[2], P[3])), 0.25);
    if (hint && dot(n, sub(c, hint)) < 0) n = mul(n, -1);
    quad(P, [n, n, n, n], T || [[0, 0], [1, 0], [1, 1], [0, 1]], [e, e, e, e]);
  };
  // axis-aligned box (centre c, size s), flat shaded; skip is a set of face names ('-x', '+y', ...)
  const box = (c, s, e, skip = '') => {
    const h = [s[0] / 2, s[1] / 2, s[2] / 2], F = [
      ['+x', [[1, -1, -1], [1, 1, -1], [1, 1, 1], [1, -1, 1]]], ['-x', [[-1, -1, 1], [-1, 1, 1], [-1, 1, -1], [-1, -1, -1]]],
      ['+y', [[-1, 1, -1], [-1, 1, 1], [1, 1, 1], [1, 1, -1]]], ['-y', [[-1, -1, 1], [-1, -1, -1], [1, -1, -1], [1, -1, 1]]],
      ['+z', [[-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]]], ['-z', [[1, -1, -1], [-1, -1, -1], [-1, 1, -1], [1, 1, -1]]]];
    for (const [name, q] of F) if (!skip.includes(name)) flat(q.map((v) => [c[0] + v[0] * h[0], c[1] + v[1] * h[1], c[2] + v[2] * h[2]]), null, e, c);
  };
  const finish = (THREE, names) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    names.forEach(([name, size], k) => { const a = new Float32Array(pos.length / 3 * size); let o = 0; for (let v = 0; v < pos.length / 3; v++) for (let q = 0; q < size; q++) a[o++] = ex[v * exN + names.slice(0, k).reduce((s, n) => s + n[1], 0) + q]; g.setAttribute(name, new THREE.BufferAttribute(a, size)); });
    g.computeBoundingSphere(); return g;
  };
  return { tri, quad, flat, box, finish, count: () => pos.length / 9 };
}

// A grid of points P[i][j] turned into smooth quads. o.closed: j wraps round; o.centre(i): a point inside row i (orients the normals
// outward); o.ex(i, j): extras of the quad (null skips it); o.uv(i, j): texture coordinates of a corner (j may equal nj for wrapping rings).
function grid(b, P, o) {
  const ni = P.length, nj = P[0].length, N = [];
  for (let i = 0; i < ni; i++) {
    N[i] = [];
    for (let j = 0; j < nj; j++) {
      const j0 = o.closed ? (j + nj - 1) % nj : Math.max(0, j - 1), j1 = o.closed ? (j + 1) % nj : Math.min(nj - 1, j + 1), i0 = Math.max(0, i - 1), i1 = Math.min(ni - 1, i + 1);
      let n = cross(sub(P[i1][j], P[i0][j]), sub(P[i][j1], P[i][j0]));
      const l = len(n); n = l < 1e-9 ? [0, 1, 0] : mul(n, 1 / l);
      if (dot(n, sub(P[i][j], o.centre(i))) < 0) n = mul(n, -1);
      N[i][j] = n;
    }
  }
  const jEnd = o.closed ? nj : nj - 1;
  for (let i = 0; i < ni - 1; i++) for (let j = 0; j < jEnd; j++) {
    const e = o.ex(i, j); if (!e) continue;
    const jn = (j + 1) % nj;
    b.quad([P[i][j], P[i + 1][j], P[i + 1][jn], P[i][jn]], [N[i][j], N[i + 1][j], N[i + 1][jn], N[i][jn]],
      [o.uv(i, j), o.uv(i + 1, j), o.uv(i + 1, j + 1), o.uv(i, j + 1)], [e, e, e, e]);
  }
}

// ---------------------------------------------------------------------------------------------------- cars
// Parts (aPart): 0 paint, 1 glass, 2 tyre, 3 rim, 4 interior, 5 underside / wheel well, 6 bumper plastic, 7 headlamp, 8 tail lamp, 9 (spare), 10 grille, 11 plate
// Types are real-world-ish 2020s Japanese dimensions in metres. hood = length of the bonnet ahead of the windscreen base,
// ws = how far the windscreen runs back, rt/rb = how far the roof / the rear-glass base stand in from the tail.
export const CAR_TYPES = [
  { name: 'kei',     L: 3.40, W: 1.475, ovF: 0.50, wb: 2.45, wr: 0.285, tw: 0.150, roof: 1.74, belt: 1.00, hood0: 0.82, hood: 0.55, ws: 0.42, rt: 0.22, rb: 0.10, deck: 1.00, zr: 0.86, win: 2, seats: 1 },
  { name: 'compact', L: 3.95, W: 1.695, ovF: 0.75, wb: 2.53, wr: 0.300, tw: 0.175, roof: 1.50, belt: 0.93, hood0: 0.72, hood: 1.00, ws: 0.72, rt: 0.55, rb: 0.12, deck: 0.93, zr: 0.74, win: 2, seats: 1 },
  { name: 'sedan',   L: 4.55, W: 1.745, ovF: 0.95, wb: 2.70, wr: 0.310, tw: 0.195, roof: 1.455, belt: 0.93, hood0: 0.70, hood: 1.05, ws: 0.78, rt: 1.45, rb: 1.15, deck: 0.96, zr: 0.72, win: 2, seats: 1 },
  { name: 'van',     L: 4.70, W: 1.695, ovF: 0.85, wb: 2.88, wr: 0.310, tw: 0.185, roof: 1.86, belt: 1.02, hood0: 0.82, hood: 0.85, ws: 0.55, rt: 0.17, rb: 0.10, deck: 1.02, zr: 0.88, win: 3, seats: 1 },
  { name: 'bus',     L: 10.8, W: 2.50, ovF: 2.70, wb: 5.45, wr: 0.500, tw: 0.270, roof: 3.00, belt: 1.00, hood0: 1.00, hood: 0.12, ws: 0.12, rt: 0.12, rb: 0.05, deck: 1.00, zr: 0.92, win: 6, seats: 0, gt: 2.45 },
];

// the shape of a type: station heights and widths along x. Returns the helpers the builders share.
function carShape(s) {
  const hw = s.W / 2, xc = s.L / 2 - s.hood, xw = xc - s.ws, xre = -s.L / 2 + s.rt, xrb = -s.L / 2 + s.rb, xF = s.L / 2 - s.ovF, xR = xF - s.wb;
  const Ra = s.wr + 0.11, sill = s.name === 'bus' ? 0.36 : 0.29, yFloor = s.name === 'bus' ? 0.30 : 0.26;
  const topAt = (x) => {
    if (x >= xc) { const t = Math.min(1, (x - xc) / Math.max(0.05, s.L / 2 - xc)); return s.belt + (s.hood0 - s.belt) * t * t; }
    if (x >= xrb) return s.belt;
    const t = (xrb - x) / Math.max(0.05, xrb + s.L / 2); return s.deck + (s.deck - 0.07 - s.deck) * t * t;
  };
  const wAt = (x) => { const e = Math.min(s.L / 2 - Math.abs(x), 0.55) / 0.55; return hw * (0.84 + 0.16 * Math.sin(Math.max(0, e) * Math.PI / 2)); };
  const ybAt = (x) => {
    const e = Math.max(0, (Math.abs(x) - (s.L / 2 - 0.5)) / 0.5);
    let y = sill + 0.15 * e * e;
    for (const xw_ of [xF, xR]) { const dx = x - xw_; if (Math.abs(dx) < Ra) y = Math.max(y, s.wr + Math.sqrt(Ra * Ra - dx * dx)); }
    return y;
  };
  return { hw, xc, xw, xre, xrb, xF, xR, Ra, sill, yFloor, topAt, wAt, ybAt, zB: (x) => 0.86 * wAt(x), zRoof: s.zr * hw * 0.86 };
}

export function carGeometry2(THREE, type) {
  const s = CAR_TYPES[type], S = carShape(s), b = builder(2), E = (part, id = 0) => [part, id];
  const { hw, xc, xw, xre, xrb, xF, xR, Ra, yFloor, topAt, wAt, ybAt, zB, zRoof } = S;
  const hint = [0, 0.9, 0];
  // ---- stations
  const xs = [s.L / 2, s.L / 2 - 0.04, s.L / 2 - 0.14, s.L / 2 - 0.3, xc, xrb, -s.L / 2 + 0.3, -s.L / 2 + 0.14, -s.L / 2 + 0.04, -s.L / 2];
  for (const xa of [xF, xR]) for (const f of [-1, -0.8, -0.5, -0.2, 0.2, 0.5, 0.8, 1]) xs.push(xa + f * Ra); xs.push(xF, xR);
  const nFill = Math.ceil(s.L / 0.9); for (let k = 1; k < nFill; k++) xs.push(s.L / 2 - s.L * k / nFill);
  xs.sort((p, q) => q - p);
  const X = xs.filter((x, i) => i === 0 || xs[i - 1] - x > 0.035);
  // ---- lower body: rows of 8 ring points (right half) per station
  const ring = X.map((x) => {
    const w = wAt(x), top = topAt(x), yb = ybAt(x), z = (zz) => zz * w;
    return [[x, yFloor, 0], [x, yFloor, z(0.80)], [x, yb, z(0.93)], [x, yb + Math.max(0.10, (top - yb) * 0.14), z(0.99)], [x, yb + (top - yb) * 0.58, z(1.0)],
      [x, top - 0.07, z(0.975)], [x, top - 0.02, z(0.86)], [x, top + 0.01, 0]];
  });
  const mirror = (p) => [p[0], p[1], -p[2]];
  const cabin = (i) => { const xm = (X[i] + X[i + 1]) / 2; return xm < xc && xm > xrb; };
  const centre = (i) => [X[i], (yFloor + topAt(X[i])) / 2, 0];
  // underside: left wall, floor, right wall (dark)
  grid(b, ring.map((r) => [mirror(r[2]), mirror(r[1]), r[0], r[1], r[2]]), { centre, ex: () => E(5), uv: (i, j) => [i, j] });
  // outer skin, both sides
  grid(b, ring.map((r) => [r[2], r[3], r[4], r[5], r[6]]), { centre, ex: () => E(0), uv: (i, j) => [X[Math.min(i, X.length - 1)], j] });
  grid(b, ring.map((r) => [mirror(r[2]), mirror(r[3]), mirror(r[4]), mirror(r[5]), mirror(r[6])]), { centre, ex: () => E(0), uv: (i, j) => [X[Math.min(i, X.length - 1)], j] });
  // bonnet and boot lid (the cabin is hollow: it has windows)
  grid(b, ring.map((r) => [mirror(r[6]), r[7], r[6]]), { centre, ex: (i) => (cabin(i) ? null : E(0)), uv: (i, j) => [X[Math.min(i, X.length - 1)], j] });
  // ---- front and rear faces with their lamps, grille, bumper, plate
  for (const end of [1, -1]) {
    const r = ring[end > 0 ? 0 : ring.length - 1], x0 = r[0][0], n = [end, 0, 0];
    const pts = [r[2], r[3], r[4], r[5], r[6], r[7], mirror(r[6]), mirror(r[5]), mirror(r[4]), mirror(r[3]), mirror(r[2])];
    const c = pts.reduce((a, p) => add(a, p), [0, 0, 0]).map((v) => v / pts.length);
    for (let k = 0; k < pts.length - 1; k++) b.tri(c, pts[k], pts[k + 1], n, n, n, [0.5, 0.5], [0, 0], [1, 1], E(0), E(0), E(0));
    const top = topAt(x0), w = wAt(x0), x1 = x0 + end * 0.006;
    const lamp = end > 0 ? 7 : 8, yl = top - (end > 0 ? 0.20 : 0.24), yh = top - 0.06;
    for (const sg of [1, -1]) b.flat([[x1, yl, sg * 0.52 * w], [x1, yl, sg * 0.90 * w], [x1, yh, sg * 0.90 * w], [x1, yh, sg * 0.52 * w]], null, E(lamp, sg > 0 ? 0 : 1), [x0 - end, 0.9, 0]);
    if (end > 0) b.flat([[x1, top - 0.30, -0.40 * w], [x1, top - 0.30, 0.40 * w], [x1, top - 0.13, 0.40 * w], [x1, top - 0.13, -0.40 * w]], null, E(10), [x0 - 1, 0.9, 0]);
    // bumper: a shallow box standing 6 cm proud, with the plate on it
    const by0 = 0.36, by1 = 0.60, bw = w * 0.97;
    b.box([x0 + end * 0.02, (by0 + by1) / 2, 0], [0.12, by1 - by0, bw * 2], E(6), end > 0 ? '-x' : '+x');
    const xp = x0 + end * 0.0815;
    b.flat([[xp, 0.40, -0.26], [xp, 0.40, 0.26], [xp, 0.52, 0.26], [xp, 0.52, -0.26]], [[0, 0], [1, 0], [1, 1], [0, 1]], E(11), [x0 - end, 0.5, 0]);
  }
  // ---- greenhouse: framed glass panels, roof, pillars
  const yb = (x) => topAt(x) - 0.02, pillar = s.name === 'bus' ? 0.05 : 0.07, nWin = s.win;
  const framed = (c, mu, mv, wins, id0, gap) => {
    const bil = (u, v) => add(add(mul(c[0], (1 - u) * (1 - v)), mul(c[1], u * (1 - v))), add(mul(c[2], u * v), mul(c[3], (1 - u) * v)));
    const Lu = (len(sub(c[1], c[0])) + len(sub(c[2], c[3]))) / 2, Lv = (len(sub(c[3], c[0])) + len(sub(c[2], c[1]))) / 2, a = mu / Lu, bb = mv / Lv, g = gap / Lu;
    const q = (u0, v0, u1, v1, e, T) => b.flat([bil(u0, v0), bil(u1, v0), bil(u1, v1), bil(u0, v1)], T, e, hint);
    q(0, 0, 1, bb, E(0)); q(1 - a, bb, 1, 1 - bb, E(0)); q(0, 1 - bb, 1, 1, E(0)); q(0, bb, a, 1 - bb, E(0));
    const w0 = a, w1 = 1 - a, wl = (w1 - w0 - g * (wins - 1)) / wins;
    for (let k = 0; k < wins; k++) {
      const u0 = w0 + k * (wl + g); q(u0, bb, u0 + wl, 1 - bb, E(1, id0 + k));
      if (k < wins - 1) q(u0 + wl, bb, u0 + wl + g, 1 - bb, E(0));
    }
  };
  const yTop = s.roof - 0.04, yG = s.gt ? s.gt : yTop;                  // glass reaches yG; on a bus a painted band runs above it to the roof
  const sideC = (sg) => [[xrb, yb(xrb), sg * zB(xrb)], [xc, yb(xc), sg * zB(xc)], [xw, yG, sg * zRoof], [xre, yG, sg * zRoof]];   // rear-bottom, front-bottom, front-top, rear-top
  framed([[xc, yb(xc), -zB(xc)], [xc, yb(xc), zB(xc)], [xw, yG, zRoof], [xw, yG, -zRoof]], 0.07, 0.07, 1, 0, 0);               // windscreen
  framed([[xrb, yb(xrb), zB(xrb)], [xrb, yb(xrb), -zB(xrb)], [xre, yG, -zRoof], [xre, yG, zRoof]], 0.07, 0.07, 1, 1, 0);        // rear glass
  if (s.gt) {
    for (const sg of [1, -1]) b.flat([[xw, yG, sg * zRoof], [xre, yG, sg * zRoof], [xre, yTop, sg * zRoof], [xw, yTop, sg * zRoof]], null, E(0), hint);
    for (const [x, sgn] of [[xw, 1], [xre, -1]]) b.flat([[x, yG, -zRoof], [x, yG, zRoof], [x, yTop, zRoof], [x, yTop, -zRoof]], null, E(0), [x - sgn, 0.9, 0]);
  }
  for (const sg of [1, -1]) { const c = sideC(sg); framed(sg > 0 ? [c[1], c[0], c[3], c[2]] : [c[0], c[1], c[2], c[3]], 0.10, 0.045, nWin, 2 + (sg > 0 ? 0 : nWin), pillar * 1.4); }
  // roof (crowned) with its gutter edges
  grid(b, [xw, xre].map((x) => [[x, yTop, -zRoof], [x, s.roof + 0.0, -zRoof * 0.8], [x, s.roof + 0.025, 0], [x, s.roof + 0.0, zRoof * 0.8], [x, yTop, zRoof]]),
    { centre: (i) => [i ? xre : xw, 0.9, 0], ex: () => E(0), uv: (i, j) => [i, j] });
  // ---- interior: floor is the underside; dash, seats, door cards
  const dash = xc - 0.30;
  b.box([dash, 0.62, 0], [0.50, 0.70, 2 * zB(xc) * 0.96], E(4));
  const seatH = s.name === 'van' ? 0.54 : 0.50, zs = [-0.40 * hw, 0.40 * hw], sw = 0.42 * hw;
  if (s.seats) {
    const rows = s.name === 'van' ? [dash - 0.85, dash - 1.65, xrb + 0.62] : [dash - 0.80, xrb + 0.62];
    for (const xr of rows) for (const z of zs) {
      b.box([xr, 0.44 + 0.04, z], [0.50, 0.30, sw], E(4)); b.box([xr - 0.30, 0.78, z], [0.12, 0.62, sw], E(4));
    }
  } else {
    for (let xr = xc - 2.4; xr > xrb + 0.5; xr -= 1.15) for (const z of [-0.62, 0.62]) b.box([xr, 0.62, z], [0.12, 0.78, 0.9], E(4));
  }
  // ---- wheels: a ten-sided tyre on a pressed-steel rim, standing in the arches
  const S12 = 12;
  [[xF, 1, 0], [xF, -1, 1], [xR, 1, 2], [xR, -1, 3]].forEach(([xa, sg, id]) => {
    const r = s.wr, hwid = s.tw / 2, z0 = sg * (0.93 * wAt(xa) - hwid + 0.015);
    const prof = [[r, -0.40], [r, 0], [r, 0.40], [r * 0.93, 0.50], [r * 0.64, 0.50]].map(([rad, k]) => [rad, k * s.tw * sg]);       // radius, z offset from the tyre centre
    const P = []; for (let k = 0; k < prof.length; k++) { P[k] = []; for (let j = 0; j < S12; j++) { const a = j / S12 * Math.PI * 2; P[k].push([xa + Math.cos(a) * prof[k][0], r + Math.sin(a) * prof[k][0], z0 + prof[k][1]]); } }
    grid(b, P, { closed: true, centre: () => [xa, r, z0], ex: () => E(2, id), uv: (i, j) => [j / S12 * 6, i / 4] });
    // rim face: a dished disc
    const hub = [xa, r, z0 + sg * hwid * 0.62];
    for (let j = 0; j < S12; j++) {
      const a0 = j / S12 * Math.PI * 2, a1 = (j + 1) / S12 * Math.PI * 2, q0 = [xa + Math.cos(a0) * r * 0.64, r + Math.sin(a0) * r * 0.64, z0 + sg * hwid * 1.0], q1 = [xa + Math.cos(a1) * r * 0.64, r + Math.sin(a1) * r * 0.64, z0 + sg * hwid * 1.0];
      const n = [0, 0, sg]; b.tri(hub, q0, q1, n, n, n, [j / S12, 0], [j / S12, 1], [(j + 1) / S12, 1], E(3, id), E(3, id), E(3, id));
    }
  });
  // ---- door mirrors
  for (const sg of [1, -1]) b.box([xc - 0.14, s.belt + 0.10, sg * (zB(xc) + 0.14)], [0.10, 0.12, 0.20], E(0), '');
  return b.finish(THREE, [['aPart', 1], ['aId', 1]]);
}

// Grass tufts, creepers and a sapling that have taken hold of a car. kinds: 0 leaf cards, 2 vine ribbons, 3 grass
export function carVinesGeometry(THREE, type, seed) {
  const s = CAR_TYPES[type], S = carShape(s), b = builder(5), rng = rngOf(seed + type * 31), { hw, xc, xw, xre, xrb, topAt, wAt, zB, zRoof } = S;
  const E = (kind, rnd, tone = rng()) => [kind, tone, 0.2, 0, rnd];
  const cardT = [[0, 0], [1, 0], [1, 1], [0, 1]];
  // grass tuft: two crossed upright quads at (x, y, z)
  const tuft = (x, y, z, w, h) => {
    const a = rng() * Math.PI, rnd = rng(), e = [3, rng(), 0.6, 0, rnd];
    for (const da of [0, Math.PI / 2]) {
      const dx = Math.cos(a + da) * w / 2, dz = Math.sin(a + da) * w / 2, n = norm([-dz, 0.3, dx]);
      b.quad([[x - dx, y, z - dz], [x + dx, y, z + dz], [x + dx, y + h, z + dz], [x - dx, y + h, z - dz]], [n, n, n, n], cardT, [e, e, e, e]);
    }
  };
  const nT = s.name === 'bus' ? 16 : 10;
  for (let k = 0; k < nT; k++) {                                                          // round the foot of the car
    const x = (rng() - 0.5) * (s.L - 0.4), side = rng() < 0.5 ? 1 : -1, z = side * (wAt(x) + 0.0 + rng() * 0.25);
    tuft(x, -0.05, z, 0.5 + rng() * 0.6, 0.4 + rng() * 0.55);
  }
  for (const [x, hgt] of [[(xc + s.L / 2) / 2, topAt((xc + s.L / 2) / 2)], [(xw + xre) / 2, s.roof], [(xrb - s.L / 2) / 2, topAt((xrb - s.L / 2) / 2)]]) {     // on the bonnet, roof and boot lid
    if (rng() < 0.75) tuft(x + (rng() - 0.5) * 0.4, hgt + 0.01, (rng() - 0.5) * hw * 0.8, 0.4 + rng() * 0.3, 0.25 + rng() * 0.3);
  }
  // creepers: ribbons that run up the side, over the greenhouse and across the roof
  const outline = (x) => {
    if (x <= xw && x >= xre) return [[wAt(x) * 0.99, 0.45], [wAt(x) * 0.975, topAt(x) - 0.07], [zB(x), topAt(x)], [zRoof, s.roof - 0.04], [zRoof * 0.8, s.roof], [0, s.roof + 0.025]];
    return [[wAt(x) * 0.99, 0.45], [wAt(x) * 0.975, topAt(x) - 0.07], [wAt(x) * 0.86, topAt(x)], [0, topAt(x) + 0.03]];
  };
  const nR = s.name === 'bus' ? 4 : 3;
  for (let k = 0; k < nR; k++) {
    const x0 = lerp(xre, xw, 0.15 + rng() * 0.7), sg = rng() < 0.5 ? 1 : -1, wid = 0.14 + rng() * 0.12, rnd = rng(), e = [2, rng(), 0.7, 0, rnd], pts = outline(x0);
    const start = 1 + Math.floor(rng() * 2), lift = 0.03;
    let acc = 0, prev = null;
    for (let i = start; i < pts.length; i++) {
      const p = pts[i], q = pts[i - 1], dz = p[0] - q[0], dy = p[1] - q[1], l = Math.hypot(dz, dy) || 1, nz = dy / l, ny = -dz / l;       // outward normal of the segment (right side)
      const sway = Math.sin(i * 1.7 + k) * 0.06;
      const a = [x0 + sway - wid, q[1] + ny * lift, sg * (q[0] + nz * lift)], a2 = [x0 + sway + wid, a[1], a[2]];
      const c = [x0 - sway - wid, p[1] + ny * lift, sg * (p[0] + nz * lift)], c2 = [x0 - sway + wid, c[1], c[2]];
      const n = norm([0.0, ny, sg * nz]);
      b.quad([a, a2, c2, c], [n, n, n, n], [[acc, 0], [acc, 1], [acc + l * 4, 1], [acc + l * 4, 0]], [e, e, e, e]);
      acc += l * 4;
    }
  }
  // a sapling grown through the bonnet / a broken window: crossed leaf cards round a point
  const sx = (xc + s.L / 2) / 2 - 0.1, sy = topAt(sx);
  for (let k = 0; k < 9; k++) {
    const a = rng() * Math.PI * 2, r = 0.05 + rng() * 0.22, c = [sx + Math.cos(a) * r, sy + 0.12 + rng() * 0.38, Math.sin(a) * r], sz = 0.22 + rng() * 0.2;
    const nn = norm([Math.cos(a) * 0.5, 0.9, Math.sin(a) * 0.5]), t1 = norm(cross(nn, [rng() - 0.5, rng() - 0.5, rng() - 0.5])), t2 = cross(nn, t1), e = [0, rng(), 0.8, 0, rng()];
    b.quad([sub(sub(c, mul(t1, sz)), mul(t2, sz)), sub(add(c, mul(t1, sz)), mul(t2, sz)), add(add(c, mul(t1, sz)), mul(t2, sz)), add(sub(c, mul(t1, sz)), mul(t2, sz))], [nn, nn, nn, nn], cardT, [e, e, e, e]);
  }
  return b.finish(THREE, [['aKind', 1], ['aTone', 1], ['aSway', 1], ['aDepth', 1], ['aRnd', 1]]);
}

// ---------------------------------------------------------------------------------------------------- trees
// One tree layout (roots, trunk, branches, lobes) is built at two densities: tier 0 for the nearest few dozen, tier 1 (a third of
// the geometry, bigger cards) for the rest. aKind: 0 leaf card, 1 bark, 2 vine. aTone: colour variation, aDepth: 0 outer shell .. 1 deep inside,
// aSway: how much it moves, aRnd: card id (the vertex shader drops a share of the cards per tree, so crowns differ in fullness).
export function treeGeometry2(THREE, seed, tier) {
  const A = tier === 0, rng = rngOf(seed);
  const b = builder(5), cardT = [[0, 0], [1, 0], [1, 1], [0, 1]];
  const bark = (sway) => [1, 0, sway, 0, 0];
  const stream = (n) => { const r = rngOf(seed * 131 + n); return (a, c) => a + (c - a) * r(); };
  let R = stream(1);
  // ---- trunk: a leaning, gnarled column with a wide flared foot
  const lean = [R(-0.45, 0.45), R(-0.45, 0.45)], ph = rng() * 6.28, ph2 = rng() * 6.28;
  const trunkY = tier === 2 ? [-0.40, 1.0, 3.1, 5.1] : [-0.40, 0.25, 1.0, 2.0, 3.1, 4.2, 5.1], sides = [10, 7, 5][tier];
  const spine = (y) => { const k = Math.pow(Math.max(0, y) / 5.1, 1.6); return [lean[0] * k, y, lean[1] * k]; };
  const rad = (y) => (0.30 + 0.5 * Math.exp(-(y + 0.4) / 0.62)) * (1 - 0.34 * Math.max(0, y) / 5.1);
  const P = trunkY.map((y) => { const c = spine(y), r = rad(y); return Array.from({ length: sides }, (_, j) => { const a = j / sides * Math.PI * 2, g = 1 + 0.11 * Math.sin(3 * a + ph) + 0.07 * Math.sin(5 * a + ph2); return [c[0] + Math.cos(a) * r * g, y, c[2] + Math.sin(a) * r * g]; }); });
  grid(b, P, { closed: true, centre: (i) => spine(trunkY[i]), ex: (i) => bark(i > 4 ? 0.7 : 0.4), uv: (i, j) => [j / sides, trunkY[Math.min(i, trunkY.length - 1)] * 0.9] });
  R = stream(2);
  // ---- buttress roots: tall thin fins that start high on the trunk, spread out and dive under the ground
  const nRoots = [7, 5, 4][tier], rootSeg = [6, 4, 3][tier], rm = [6, 5, 4][tier];
  for (let k = 0; k < nRoots; k++) {
    const th = (k + R(-0.3, 0.3)) / nRoots * Math.PI * 2, D = R(1.9, 3.7), h0 = R(1.0, 1.65), curl = R(-0.5, 0.5), dirv = [Math.cos(th), 0, Math.sin(th)], tang = [-dirv[2], 0, dirv[0]];
    const rows = [];
    for (let i = 0; i <= rootSeg; i++) {
      const t = i / rootSeg, d = 0.22 + (D - 0.22) * Math.pow(t, 0.85), hv = 0.10 + h0 * Math.pow(1 - t, 2.5) * (1 + 0.16 * Math.sin(t * 11 + k * 2.1)), hh = 0.09 + 0.16 * (1 - t) * (1 - t);
      const c = add(add(mul(dirv, d), mul(tang, curl * Math.sin(t * 2.4) * t)), [0, hv - 0.22 - 0.40 * t * t * t, 0]);
      const row = []; for (let j = 0; j < rm; j++) { const a = j / rm * Math.PI * 2; row.push(add(add(c, mul(tang, Math.cos(a) * hh)), [0, Math.sin(a) * hv, 0])); }
      rows.push(row);
    }
    const cs = rows.map((r) => r.reduce((a, p) => add(a, p), [0, 0, 0]).map((v) => v / rm));
    grid(b, rows, { closed: true, centre: (i) => cs[i], ex: () => [1, 0, 0.1, 0, 0], uv: (i, j) => [j / rm * 0.5 + k * 0.13, i * D / rootSeg] });
  }
  R = stream(3);
  // ---- main branches, each ending in a lobe of foliage
  const nb = 5, lobes = [], bsides = [6, 5, 4][tier];
  for (let k = 0; k < nb; k++) {
    const th = (k + R(-0.25, 0.25)) / nb * Math.PI * 2 + 0.4, yb = R(3.3, 4.7), up = R(0.55, 1.0), Lb = R(2.6, 4.1), base = add(spine(yb), mul([Math.cos(th), 0, Math.sin(th)], rad(yb) * 0.7));
    const dir = norm([Math.cos(th) * Math.cos(up), Math.sin(up), Math.sin(th) * Math.cos(up)]), rows = [];
    for (let i = 0; i <= 3; i++) {
      const t = i / 3, c = add(add(base, mul(dir, Lb * t)), [0, 0.9 * t * t, 0]), r = 0.17 * (1 - 0.68 * t) + 0.03, ax = norm(cross(dir, [0, 1, 0])), ay = norm(cross(ax, dir));
      rows.push(Array.from({ length: bsides }, (_, j) => { const a = j / bsides * Math.PI * 2; return add(c, add(mul(ax, Math.cos(a) * r), mul(ay, Math.sin(a) * r))); }));
      if (i === 3) lobes.push({ c, r: R(2.1, 2.8) }); if (i === 2) lobes.push({ c, r: R(1.5, 2.1) });
    }
    const cs = rows.map((r) => r.reduce((a, p) => add(a, p), [0, 0, 0]).map((v) => v / bsides));
    grid(b, rows, { closed: true, centre: (i) => cs[i], ex: () => bark(0.9), uv: (i, j) => [j / bsides, i * Lb / 3] });
  }
  const top = add(spine(5.1), [R(-0.6, 0.6), 2.5, R(-0.6, 0.6)]); lobes.push({ c: top, r: R(2.5, 3.0) });
  lobes.push({ c: add(spine(4.6), [R(0.8, 1.6), 1.7, R(-1.2, 1.2)]), r: 2.1 }, { c: add(spine(4.6), [R(-1.6, -0.8), 1.5, R(-1.2, 1.2)]), r: 2.1 });
  // ---- leaf cards
  const cr = rngOf(seed * 7 + 5), CR = (a, c) => a + (c - a) * cr();
  const perLobe = [64, 21, 7][tier], size0 = [1.05, 1.8, 2.9][tier], size1 = [1.6, 2.5, 3.7][tier];
  for (const lb of lobes) for (let k = 0; k < perLobe; k++) {
    let d; do d = [CR(-1, 1), CR(-1, 1) * 0.8, CR(-1, 1)]; while (len(d) > 1 || len(d) < 0.15);
    const u = norm(d), rr = Math.pow(len(d), 0.45) * 0.95 + 0.05, p = add(lb.c, mul(u, lb.r * rr));
    if (p[1] < 3.2) { p[1] = 3.2 + (3.2 - p[1]) * 0.2; }
    const n = norm(add(mul(u, 1.0), [0, 0.28, 0])), rnd = cr(), sz = CR(size0, size1);
    const nc = norm(add(mul(u, 0.45), [CR(-0.9, 0.9), CR(-0.9, 0.9), CR(-0.9, 0.9)])), t1 = norm(cross(nc, [CR(-1, 1), CR(-1, 1), CR(-1, 1)])), t2 = cross(nc, t1);
    const gd = 1 - Math.min(1, len(sub(p, lb.c)) / lb.r), glob = 1 - Math.min(1, Math.hypot(p[0] / 4.4, (p[1] - 7.0) / 3.6, p[2] / 4.4));
    const depth = Math.min(1, 0.45 * gd + 0.75 * glob), e = [0, cr(), Math.min(1, (p[1] - 3) / 5), depth, rnd];
    const h = sz / 2, rot = cr() * 6.28, cs = Math.cos(rot), sn = Math.sin(rot), uk = sz / 1.3, T = cardT.map(([x, y]) => [(0.5 + (x - 0.5) * cs - (y - 0.5) * sn) * uk, (0.5 + (x - 0.5) * sn + (y - 0.5) * cs) * uk]);   // the uv grows with the card so a leaf is the same size at every level
    const Pq = [sub(sub(p, mul(t1, h)), mul(t2, h)), sub(add(p, mul(t1, h)), mul(t2, h)), add(add(p, mul(t1, h)), mul(t2, h)), add(sub(p, mul(t1, h)), mul(t2, h))];
    b.quad(Pq, [n, n, n, n], T, [e, e, e, e]);
  }
  // ---- creepers hanging from the lower crown
  R = stream(4);
  const nV = A ? 9 : 0;
  for (let k = 0; k < nV; k++) {
    const lb = lobes[Math.floor(R(0, 0.999) * lobes.length)], a = R(0, 6.28), p0 = add(lb.c, [Math.cos(a) * lb.r * 0.7, -lb.r * 0.5, Math.sin(a) * lb.r * 0.7]), Lv = R(2.0, 4.2), w = R(0.035, 0.06), e = [2, R(0, 1), 0.9, 0.3, R(0, 1)];
    const q = (t) => add(p0, [Math.sin(t * 3 + k) * 0.12, -Lv * t, Math.cos(t * 2 + k) * 0.12]);
    for (let i = 0; i < 3; i++) { const a0 = q(i / 3), a1 = q((i + 1) / 3), n = [Math.cos(a), 0.2, Math.sin(a)]; b.quad([sub(a0, [w, 0, 0]), add(a0, [w, 0, 0]), add(a1, [w, 0, 0]), sub(a1, [w, 0, 0])], [n, n, n, n], [[i, 0], [i, 1], [i + 1, 1], [i + 1, 0]].map(([x, y]) => [x * Lv * 1.3, y]), [e, e, e, e]); }
  }
  return b.finish(THREE, [['aKind', 1], ['aTone', 1], ['aSway', 1], ['aDepth', 1], ['aRnd', 1]]);
}

// ---------------------------------------------------------------------------------------------------- shaders
// The near and far levels share an instance-origin distance test: the far shaders (props.js) drop an instance when it is
// nearer than nearR.xz - nearR.yw and dither it out in the band up to nearR.xz; the near shaders do the opposite with the
// same screen-door pattern, so each pixel is drawn by exactly one of the two.
const head = /* glsl */`
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos; uniform vec4 nearR; uniform float time;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<3;k++){ v += a*noise(p); p = p*2.03 + 7.1; a *= 0.5; } return v; }
  float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }`;

const finish = /* glsl */`
  vec3 fogIt(vec3 rgb){ float d = length(vW - camPos); return mix(rgb, fogCol, 1.0 - exp(-fogDen * d)); }`;

const carVertN = /* glsl */`
  ${head}
  attribute float aPart; attribute float aId;
  varying vec3 vW; varying vec3 vN; varying vec3 vCol; varying vec3 vLoc; varying vec2 vUv; varying float vPart; varying float vId; varying float vFar; varying vec4 vInst;
  void main(){
    mat4 M = modelMatrix * instanceMatrix;
    vec3 org = M[3].xyz;
    vFar = clamp((distance(org, camPos) - (nearR.x - nearR.y)) / nearR.y, 0.0, 1.0);
    if (vFar >= 1.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    vInst = vec4(hash(org.xz * 0.37), hash(org.xz * 0.71 + 3.1), hash(org.zx * 0.53 + 9.7), hash(org.xz * 1.13 + 5.3));
    vec3 p = position;
    if (aPart > 1.5 && aPart < 3.5) {                       // tyres and rims: about half the wheels are flat
      float h = hash(org.xz * 0.9 + aId * 3.7);
      if (h < 0.5) { float f = 0.70 + 0.24 * h * 2.0; p.z += sign(p.z) * 0.10 * (1.0 - f) * (1.0 - clamp(p.y / 0.6, 0.0, 1.0)); p.y *= f; }
    }
    vec4 w = M * vec4(p, 1.0);
    vW = w.xyz; vN = normalize(mat3(M) * normal); vCol = instanceColor; vLoc = position; vUv = uv; vPart = aPart; vId = aId;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;

const carFragN = /* glsl */`
  precision highp float;
  #include <packing>
  ${head}
  ${shadowGLSL}
  varying vec3 vW; varying vec3 vN; varying vec3 vCol; varying vec3 vLoc; varying vec2 vUv; varying float vPart; varying float vId; varying float vFar; varying vec4 vInst;
  ${finish}
  void main(){
    if (vFar > 0.0 && ign(gl_FragCoord.xy) < vFar) discard;
    bool back = !gl_FrontFacing;
    vec3 N = normalize(vN); if (back) N = -N;
    vec3 V = normalize(camPos - vW);
    float part = vPart, up = clamp(N.y, 0.0, 1.0), seed = vInst.x * 100.0;
    vec3 col = vec3(0.05); float spec = 0.0, ao = 1.0;
    if (part < 0.5) {                                                      // ---- paint
      if (back) { col = vec3(0.04, 0.036, 0.032); ao = 0.45; }
      else {
        col = vCol;
        float lum = dot(col, vec3(0.34));
        col = mix(col, vec3(lum) * 1.15 + 0.03, (0.25 + 0.4 * vInst.w) * (0.3 + 0.7 * up));          // sun-bleached clear coat
        col *= 0.78 + 0.34 * fbm(vLoc.xz * 2.5 + seed);                                               // grime
        float rustAmt = 0.25 + 0.6 * vInst.y;
        float low = smoothstep(0.65, 0.30, vLoc.y);
        float streak = noise(vec2(vLoc.x * 5.0 + seed, vLoc.y * 1.2 + vLoc.z * 2.0));
        vec2 bp = vec2(vLoc.x * 3.5 + vLoc.z * 2.0, vLoc.y * 3.0) + seed * 1.7;
        float blot = fbm(bp + 2.2 * vec2(noise(bp * 1.7), noise(bp * 1.7 + 5.0)));
        float rv = blot * 0.65 + low * 0.6 + 0.2 * streak;
        float rust = smoothstep(0.9 - rustAmt * 0.7, 1.05 - rustAmt * 0.7, rv);
        float stain = smoothstep(0.55 - rustAmt * 0.6, 0.95 - rustAmt * 0.6, rv + 0.25 * streak);
        vec3 rc = mix(vec3(0.26, 0.10, 0.045), vec3(0.50, 0.25, 0.10), noise(vLoc.xz * 30.0 + vLoc.y * 20.0));
        col = mix(col, rc * 0.8 + col * 0.2, stain * 0.45);
        col = mix(col, rc, rust * 0.9);
        col = mix(col, vec3(0.30, 0.26, 0.20), up * 0.16);                                            // dust
        col = mix(col, vec3(0.12, 0.09, 0.06), smoothstep(0.45, 0.22, vLoc.y) * 0.55);               // road mud on the lower panels
        float moss = smoothstep(0.55, 0.95, N.y) * (0.35 + 0.65 * vInst.z) * smoothstep(0.30, 0.70, fbm(vW.xz * 2.2 + 3.0));
        col = mix(col, vec3(0.11, 0.19, 0.045) * (0.7 + 0.7 * noise(vW.xz * 14.0)), moss * 0.85);
        col = mix(col, vec3(0.24, 0.13, 0.05), smoothstep(0.55, 0.95, N.y) * step(0.74, noise(vW.xz * 11.0 + 5.0)) * 0.7);   // leaf litter
        spec = pow(max(dot(N, normalize(V + sunDir)), 0.0), 60.0) * 0.12 * (1.0 - rust) * (1.0 - moss);
        ao = mix(0.55, 1.0, smoothstep(0.1, 0.6, vLoc.y));
      }
    } else if (part < 1.5) {                                               // ---- glass
      float st = fract(vInst.w * 7.31 + vId * 0.618 + vInst.x * 3.0), crack = 0.0;
      if (st < 0.26) discard;                                              // pane gone: look into the cabin
      if (st < 0.50) {                                                     // shattered: a star of cracks round an impact, shards missing
        vec2 c0 = vec2(0.25 + 0.5 * hash(vec2(vId, vInst.x * 9.0)), 0.3 + 0.4 * hash(vec2(vInst.y * 9.0, vId))), p = (vUv - c0) * vec2(1.0, 0.7);
        float r = length(p), ang = atan(p.y, p.x) / 6.2832 * 11.0 + 0.35 * noise(p * 9.0 + vId);
        float rad = abs(fract(ang) - 0.5) * r * 0.57, ring = abs(fract(r * 6.0 + 0.4 * noise(p * 12.0)) - 0.5) * 0.17;
        crack = max(smoothstep(0.012, 0.0, rad), smoothstep(0.008, 0.0, ring) * step(r, 0.55));
        if (fbm(vUv * 5.0 + vId * 5.0) > 0.60 || (r < 0.07 + 0.08 * hash(vec2(vId, 4.0)) && st < 0.4)) discard;
      }
      float gr = fbm(vUv * vec2(6.0, 4.0) + vId * 3.0);
      col = vec3(0.012, 0.02, 0.022) + skyCol * (0.07 + 0.55 * pow(1.0 - max(dot(N, V), 0.0), 3.0));
      col = mix(col, vec3(0.07, 0.11, 0.05), smoothstep(0.4, 0.0, vUv.y) * gr * 0.9);
      col += vec3(0.05, 0.05, 0.045) * smoothstep(0.4, 0.8, gr) + vec3(0.5) * crack * 0.45;
      spec = pow(max(dot(reflect(-V, N), sunDir), 0.0), 30.0) * 0.4;
    } else if (part < 2.5) {                                               // ---- tyre
      col = vec3(0.028, 0.028, 0.03) + 0.04 * noise(vUv * vec2(10.0, 8.0));
      col = mix(col, vec3(0.20, 0.17, 0.12), 0.3 * noise(vW.xz * 5.0) * (0.3 + 0.7 * up));
      ao = mix(0.45, 1.0, smoothstep(0.0, 0.4, vLoc.y));
    } else if (part < 3.5) {                                               // ---- rim: pressed steel, rusted, five slots
      col = mix(vec3(0.30, 0.29, 0.27), vec3(0.36, 0.16, 0.07), smoothstep(0.25, 0.8, fbm(vUv * vec2(8.0, 4.0)) + 0.3 * noise(vW.xz * 6.0)));
      if (vUv.y > 0.42 && vUv.y < 0.9 && sin(vUv.x * 6.2832 * 5.0) > 0.35) col = vec3(0.012);
      col *= 0.55 + 0.7 * smoothstep(0.0, 0.3, vUv.y); ao = 0.8;
    } else if (part < 4.5) {                                               // ---- interior: mouldy cloth and plastic
      col = mix(vec3(0.075, 0.068, 0.058), vec3(0.04, 0.065, 0.03), noise(vW.xz * 8.0 + vW.y * 3.0) * smoothstep(0.3, 0.9, fbm(vW.xz * 3.0)));
      ao = 0.38;
    } else if (part < 5.5) {                                               // ---- underside, wheel wells
      col = vec3(0.028, 0.022, 0.016) + 0.04 * noise(vLoc.xz * 10.0); ao = 0.3;
    } else if (part < 6.5) {                                               // ---- bumper plastic, bleached and dusty
      col = mix(vec3(0.05, 0.05, 0.055), vec3(0.20, 0.19, 0.17), vInst.w * 0.5 + 0.2 * noise(vW.xz * 20.0));
      col = mix(col, vec3(0.11, 0.18, 0.05), smoothstep(0.6, 0.95, N.y) * 0.5 * noise(vW.xz * 4.0)); ao = mix(0.6, 1.0, smoothstep(0.2, 0.6, vLoc.y));
    } else if (part < 7.5) {                                               // ---- headlamp: yellowed lens, some cracked
      col = mix(vec3(0.07, 0.08, 0.09), vec3(0.18, 0.15, 0.07), 0.5 * noise(vUv * 6.0));
      if (hash(vec2(vInst.x * 50.0, vId)) < 0.3) col = vec3(0.01);
      spec = pow(max(dot(reflect(-V, N), sunDir), 0.0), 20.0) * 0.25;
    } else if (part < 8.5) {                                               // ---- tail lamp: faded red
      col = vec3(0.27, 0.035, 0.03) * (0.6 + 0.6 * noise(vUv * 8.0)); if (hash(vec2(vInst.y * 50.0, vId)) < 0.3) col = vec3(0.015);
    } else if (part < 10.5) {                                              // ---- grille
      col = mix(vec3(0.02), vec3(0.10, 0.10, 0.10), step(0.5, fract(vUv.y * 6.0)));
    } else {                                                               // ---- number plate
      col = vec3(0.40, 0.40, 0.36);
      col = mix(col, vec3(0.04, 0.07, 0.04), step(0.5, fract(vUv.x * 14.0)) * step(0.3, vUv.y) * step(vUv.y, 0.72) * 0.7);
      col = mix(col, vec3(0.3, 0.15, 0.07), smoothstep(0.4, 0.8, fbm(vUv * 7.0)) * 0.7);
    }
    float dif = max(dot(N, sunDir), 0.0), shd = 1.0;
    if (dif > 0.0) shd = shadowAt(vW, N, sunDir);
    vec3 amb = mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9;
    vec3 rgb = col * (sunCol * dif * shd + amb) * ao + sunCol * spec * shd;
    gl_FragColor = vec4(fogIt(rgb), 1.0);
  }`;

// foliage: tree leaf cards / bark / hanging creepers, and the grass, creepers and saplings on the cars (CAR). aKind: 0 leaf card, 1 bark, 2 vine, 3 grass
const folVert = /* glsl */`
  ${head}
  attribute float aKind; attribute float aTone; attribute float aSway; attribute float aDepth; attribute float aRnd;
  varying vec3 vW; varying vec3 vN; varying vec3 vCol; varying vec3 vLoc; varying vec2 vUv; varying vec4 vA; varying float vFar; varying float vSeed;
  void main(){
    mat4 M = modelMatrix * instanceMatrix;
    vec3 org = M[3].xyz;
  #ifdef CAR
    vFar = clamp((distance(org, camPos) - (nearR.x - nearR.y)) / nearR.y, 0.0, 1.0);
  #else
    vFar = clamp((distance(org, camPos) - (nearR.z - nearR.w)) / nearR.w, 0.0, 1.0);
  #endif
    if (vFar >= 1.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    float sd = hash(org.xz * 0.137), sd2 = hash(org.zx * 0.311 + 7.0);
    vSeed = sd;
  #ifdef CAR
    if (aRnd > 0.30 + 0.70 * sd2) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }          // how overgrown this car is
  #else
    if (aKind < 0.5 && aRnd > 0.58 + 0.42 * sd2) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }   // how full this crown is
  #endif
    vec3 p = position;
  #ifndef CAR
    if (p.y > 2.5) p.y = 2.5 + (p.y - 2.5) * (0.9 + 0.24 * sd);                                  // every tree its own height
  #endif
    vec4 w = M * vec4(p, 1.0);
  #ifndef CAR
    float s = length(M[0].xyz), wgt = smoothstep(2.5, 6.5, position.y), ph = time * 1.3 + w.x * 0.3;
    w.x += sin(ph) * 0.15 * s * wgt; w.z += sin(ph * 0.8 + 1.7) * 0.1 * s * wgt;                  // the same slow wave as the far trees
    float fl = (aKind < 0.5 ? 0.05 : (aKind > 1.5 ? 0.12 : 0.0)) * s * aSway;
    w.xyz += vec3(sin(time * 2.3 + aRnd * 60.0 + w.z), sin(time * 2.9 + aRnd * 47.0) * 0.5, cos(time * 2.1 + aRnd * 53.0 + w.x)) * fl;
  #else
    w.xyz += vec3(sin(time * 2.0 + aRnd * 60.0 + w.z), 0.0, cos(time * 1.7 + aRnd * 50.0 + w.x)) * 0.025 * aSway * (aKind > 2.5 ? 2.0 : 1.0) * (position.y > 0.1 ? 1.0 : 0.0);
  #endif
    vW = w.xyz; vN = normalize(mat3(M) * normal);
  #if defined(USE_INSTANCING_COLOR) && !defined(CAR)
    vCol = instanceColor;
  #else
    vCol = vec3(0.17, 0.27, 0.07) * (0.85 + 0.3 * sd);
  #endif
    vLoc = position; vUv = uv; vA = vec4(aTone, aDepth, aKind, aRnd);
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;

const folFrag = /* glsl */`
  precision highp float;
  #include <packing>
  ${head}
  ${shadowGLSL}
  varying vec3 vW; varying vec3 vN; varying vec3 vCol; varying vec3 vLoc; varying vec2 vUv; varying vec4 vA; varying float vFar; varying float vSeed;
  ${finish}
  // a card of 3 x 3 pointed leaves, each with its own angle, size and tint; returns coverage, shading along the leaf, a per-leaf random, midrib
  float leaves(vec2 uv, out float sh, out float hv, out float rib){
    vec2 p = uv * 2.5 + vec2(vSeed * 17.0), id = floor(p), f = fract(p) - 0.5;
    float h1 = hash(id + 1.3), h2 = hash(id + 7.7), h3 = hash(id + 3.1);
    f -= (vec2(h2, h3) - 0.5) * 0.16;
    float ang = h1 * 6.2832, a = dot(f, vec2(cos(ang), sin(ang))), b = dot(f, vec2(-sin(ang), cos(ang)));
    float L = 0.31 + 0.07 * h3, t = a / L, w = 0.18 * (1.0 - t * t) * (1.0 + 0.5 * t);
    hv = h1; sh = clamp(t * 0.5 + 0.5, 0.0, 1.0); rib = smoothstep(0.025, 0.0, abs(b)) * step(abs(t), 0.9);
    return (abs(t) < 1.0 && abs(b) < w) ? 1.0 : 0.0;
  }
  float grassBlades(vec2 uv, out float sh, out float hv, out float rib){
    float cov = 0.0; hv = 0.5; sh = 0.0; rib = 0.0;
    for (int l = 0; l < 2; l++) {
      float N = l == 0 ? 8.0 : 5.0, x = uv.x * N + vSeed * 9.0 + float(l) * 3.7 + (l == 0 ? 0.0 : 0.37), cell = floor(x), f = fract(x) - 0.5;
      float jit = (hash(vec2(cell, 11.0 + float(l))) - 0.5) * 0.5;
      float h = (l == 0 ? 0.55 : 0.35) + 0.45 * hash(vec2(cell, vSeed + float(l))), lean = (hash(vec2(cell, 3.0 + vSeed)) - 0.5) * 0.9;
      float w = 0.16 * (1.0 - 0.9 * uv.y / h);
      if (uv.y < h && abs(f - jit - lean * uv.y) < w) { cov = 1.0; hv = hash(vec2(cell, 9.0 + float(l))); sh = clamp(uv.y / h, 0.0, 1.0); }
    }
    return cov;
  }
  // a creeper: a thin stem with pointed leaves standing out to alternate sides
  float vineLeaves(vec2 uv, out float sh, out float hv, out float rib){
    float cell = floor(uv.x), f = fract(uv.x), stem = step(abs(uv.y - 0.5), 0.04), leaf = 0.0;
    hv = hash(vec2(cell, 5.0)); sh = 0.5; rib = stem;
    for (int s = 0; s < 2; s++) {
      float side = s == 0 ? 1.0 : -1.0, h = hash(vec2(cell, float(s) + vSeed * 3.0));
      float t = (uv.y - 0.5) * side / (0.30 + 0.16 * h);
      if (t > 0.05 && t < 1.0) {
        float w = 0.30 * sin(3.14159 * t) * (1.0 - 0.3 * t);
        if (abs(f - (0.2 + 0.6 * h) - (t - 0.4) * side * 0.35) < w) { leaf = 1.0; hv = h; sh = clamp(t, 0.0, 1.0); rib = 0.0; }
      }
    }
    return max(stem, leaf);
  }
  void main(){
    if (vFar > 0.0 && ign(gl_FragCoord.xy) < vFar) discard;
    float kind = vA.z, depth = vA.y, tone = vA.x;
    vec3 N = normalize(vN), V = normalize(camPos - vW);
    vec3 col; float ao = 1.0, trans = 0.0, wrapK = 0.0;
    if (kind > 0.5 && kind < 1.5) {                                        // ---- bark
      float ridge = noise(vec2(vUv.x * 28.0 + vSeed * 9.0, vUv.y * 0.9)), ridge2 = noise(vec2(vUv.x * 70.0, vUv.y * 2.2));
      col = mix(vec3(0.08, 0.06, 0.047), vec3(0.34, 0.26, 0.19), smoothstep(0.35, 0.65, ridge)) * (0.75 + 0.5 * ridge2);
      float moss = (smoothstep(0.4, 1.0, N.y) * 0.9 + smoothstep(2.4, 0.2, vLoc.y) * 0.45) * smoothstep(0.30, 0.65, fbm(vW.xz * 3.0 + vLoc.y * 1.3));
      col = mix(col, vec3(0.07, 0.14, 0.035) * (0.7 + 0.8 * ridge2), moss * 0.85);
      col = mix(col, vec3(0.30, 0.31, 0.25), smoothstep(0.58, 0.70, fbm(vW.xz * 5.0 + vW.y * 4.0 + 3.0)) * 0.5);     // lichen
      ao = mix(0.5, 1.0, smoothstep(-0.3, 1.4, vLoc.y));
      wrapK = 0.15;
    } else {                                                               // ---- leaves, grass, creeper
      float sh, hv, rib, cover;
      if (kind < 0.5) cover = leaves(vUv, sh, hv, rib); else if (kind > 2.5) cover = grassBlades(vUv, sh, hv, rib); else cover = vineLeaves(vUv, sh, hv, rib);
      if (cover < 0.5) discard;
      col = vCol * mix(0.8, 1.75, hv);
      col = mix(col, col * vec3(2.0, 1.55, 0.4), smoothstep(0.55, 1.0, tone) * 0.55);                          // new growth, turning leaves
      if (hv < 0.02) col = vec3(0.26, 0.16, 0.06) * (0.6 + hv * 20.0);                                        // a few dead leaves
      if (kind > 2.5) { col = mix(vec3(0.12, 0.17, 0.05), vec3(0.45, 0.42, 0.18), sh * (0.4 + 0.6 * tone)) ; }
      col *= mix(0.78, 1.16, sh) * (1.0 - 0.35 * rib) * (1.0 + 0.45 * (1.0 - depth));
      ao = mix(1.0, 0.14, depth * depth);
      wrapK = 0.45;
      trans = pow(clamp(dot(-V, sunDir), 0.0, 1.0), 2.0) * (1.0 - 0.75 * depth);
    }
    float nl = dot(N, sunDir), wrap = clamp((nl + wrapK) / (1.0 + wrapK), 0.0, 1.0), shd = 1.0;
    if (wrap > 0.0 || trans > 0.0) shd = shadowAt(vW, N, sunDir);
    vec3 amb = mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9;
    float sunAo = mix(1.0, 0.12, depth * depth);
    vec3 rgb = col * (sunCol * wrap * wrap * shd * (kind > 0.5 && kind < 1.5 ? ao : sunAo) + sunCol * vec3(1.0, 0.95, 0.45) * trans * 0.75 * shd + amb * ao);
    gl_FragColor = vec4(fogIt(rgb), 1.0);
  }`;

export function nearMaterials(THREE, uniforms) {
  const car = new THREE.ShaderMaterial({ uniforms, vertexShader: carVertN, fragmentShader: carFragN, side: THREE.DoubleSide });
  const tree = new THREE.ShaderMaterial({ uniforms, vertexShader: folVert, fragmentShader: folFrag, side: THREE.DoubleSide });
  const carFol = new THREE.ShaderMaterial({ uniforms, vertexShader: folVert, fragmentShader: folFrag, side: THREE.DoubleSide, defines: { CAR: 1 } });
  return { car, tree, carFol };
}
export { head as nearHead };
