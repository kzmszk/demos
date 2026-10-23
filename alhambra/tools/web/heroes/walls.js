import * as THREE from 'three';
import { terrainHeight, insidePolygon } from '../navigation.js';

// The enclosure of the Sabika hill: tapial curtain walls with lifts, battered rubble plinths, brick string
// courses, wall-walks and pyramid-capped merlons, with every named tower on its real OSM footprint.
// Geometry is lofted from cross-sections along the OSM perimeter (mitred at the bends) so that nothing is a
// plain box; the materials are procedural textures baked by work/gates/tex/*.py (public/textures/gates).

// ---------------------------------------------------------------- utilities
export const rnd = seed => { let s = seed | 0; return () => { s = (Math.imul(1664525, s) + 1013904223) | 0; return (s >>> 0) / 4294967296; }; };
export function vnoise(x, seed = 0) {
  const i = Math.floor(x), f = x - i, t = f * f * (3 - 2 * f);
  const h = k => { let n = Math.imul(i + k, 374761393) + Math.imul(seed | 0, 668265263); n = Math.imul(n ^ (n >>> 13), 1274126177); return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
  return h(0) * (1 - t) + h(1) * t;
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const hyp = Math.hypot;

// ---------------------------------------------------------------- materials
const IMG = {};
async function loadImg(file) {
  if (!IMG[file]) IMG[file] = (async () => { const i = new Image(); i.src = `textures/gates/${file}.jpg`; await i.decode(); return i; })();
  return IMG[file];
}
export async function texMat(M, name, file, w, h, { rough = .95, bump = .6, color = 0xffffff, vc = true, side = THREE.FrontSide } = {}) {
  const img = await loadImg(file);
  const map = new THREE.Texture(img); map.colorSpace = THREE.SRGBColorSpace; map.wrapS = map.wrapT = THREE.RepeatWrapping; map.anisotropy = 8; map.repeat.set(1 / w, 1 / h); map.needsUpdate = true;
  const m = new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, map, vertexColors: vc, side });
  if (bump) { const bm = new THREE.Texture(img); bm.colorSpace = THREE.NoColorSpace; bm.wrapS = bm.wrapT = THREE.RepeatWrapping; bm.anisotropy = 8; bm.repeat.copy(map.repeat); bm.needsUpdate = true; m.bumpMap = bm; m.bumpScale = bump; }
  m.name = name; m.userData = { scale: 1 }; M[name] = m; return m;
}
export function plainMat(M, name, color, rough = .95, { metal = 0, vc = true, side = THREE.FrontSide } = {}) {
  const m = new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal, vertexColors: vc, side });
  m.name = name; m.userData = { scale: 1 }; M[name] = m; return m;
}
export async function materials(M) {
  await Promise.all([
    texMat(M, 'walTapial', 'tapial-a', 6, 6, { bump: 1.6 }),
    texMat(M, 'walTapialB', 'tapial-b', 6, 6, { bump: 1.4 }),
    texMat(M, 'walTapialC', 'tapial-c', 6, 6, { bump: 1.6 }),
    texMat(M, 'walBrick', 'brick-a', 3.2, 3.2, { bump: 1.8 }),
    texMat(M, 'walBrickB', 'brick-b', 3.2, 3.2, { bump: 1.8 }),
    texMat(M, 'walAshlar', 'ashlar', 4, 4, { bump: 1.4 }),
    texMat(M, 'walAshlarGrey', 'ashlar-grey', 4, 4, { bump: 1.4 }),
    texMat(M, 'walRubble', 'rubble', 3.2, 3.2, { bump: 2.0 }),
    texMat(M, 'walCobble', 'cobble', 4, 4, { bump: 2.0, rough: .9 }),
    texMat(M, 'walGravel', 'gravel', 4, 4, { bump: 1.0, rough: 1 }),
    texMat(M, 'walLime', 'limewash', 2, 2, { bump: .5 }),
  ]);
  // overlay (patch) variants: pulled toward the camera in depth so thin decals never z-fight, at any distance
  for (const [name, src] of [['walPatchBrick', 'walBrick'], ['walPatchLime', 'walTapialB'], ['walPatchWash', 'walLime'], ['walPatchAshlar', 'walAshlar'], ['walPatchTapial', 'walTapialC']]) {
    const m = M[src].clone(); m.name = name; m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -4; M[name] = m;
  }
  for (const [name, src] of [['walFeatherBrick', 'walBrick'], ['walFeatherLime', 'walLime'], ['walFeatherTapial', 'walTapialC']]) {
    const m = M[src].clone(); m.name = name; m.transparent = true; m.depthWrite = false; m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -4; m.userData = { ...M[src].userData }; M[name] = m;
  }
  plainMat(M, 'walDark', 0x1a1410, 1);
  { const m = M.walDark.clone(); m.name = 'walDarkOver'; m.polygonOffset = true; m.polygonOffsetFactor = -3; m.polygonOffsetUnits = -6; M.walDarkOver = m; }
  plainMat(M, 'walTile', 0xb3623f, .85);
  plainMat(M, 'walWood', 0x6a4a2f, .8);
}

// ---------------------------------------------------------------- triangle soup (one per material)
export class Soup {
  constructor(rgba = false) { this.p = []; this.n = []; this.u = []; this.c = []; this.rgba = rgba; }
  get count() { return this.p.length / 9; }
  tri(A, B, C, uA, uB, uC, col = [1, 1, 1], want = null) { this.triC(A, B, C, uA, uB, uC, col, col, col, want); }
  triC(A, B, C, uA, uB, uC, cA, cB, cC, want = null) {
    let nx = (B[1] - A[1]) * (C[2] - A[2]) - (B[2] - A[2]) * (C[1] - A[1]);
    let ny = (B[2] - A[2]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[2] - A[2]);
    let nz = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0]);
    if (want && nx * want[0] + ny * want[1] + nz * want[2] < 0) { [B, C] = [C, B]; [uB, uC] = [uC, uB]; [cB, cC] = [cC, cB]; nx = -nx; ny = -ny; nz = -nz; }
    if (DEBUG && !(Number.isFinite(A[0] + A[1] + A[2] + B[0] + B[1] + B[2] + C[0] + C[1] + C[2]))) { if (!Soup.warned) { Soup.warned = 1; console.warn('NaN tri', JSON.stringify([A, B, C]), new Error().stack); } }
    const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
    for (const [P, U, col] of [[A, uA, cA], [B, uB, cB], [C, uC, cC]]) { this.p.push(P[0], P[1], P[2]); this.n.push(nx, ny, nz); this.u.push(U[0], U[1]); if (this.rgba) this.c.push(col[0], col[1], col[2], col[3] ?? 1); else this.c.push(col[0], col[1], col[2]); }
  }
  quad(A, B, C, D, uA, uB, uC, uD, col = [1, 1, 1], want = null) {
    // normal from the diagonal pair so the quad can be bent
    this.tri(A, B, C, uA, uB, uC, col, want); this.tri(A, C, D, uA, uC, uD, col, want);
  }
  // box-like faces helpers
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.u, 2));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.c, this.rgba ? 4 : 3));
    return g;
  }
}
const DEBUG = false;
export let LOW = false;
export const setLow = v => { LOW = !!v; };
export class Mesher {
  constructor() { this.m = new Map(); }
  s(name) { let s = this.m.get(name); if (!s) { s = new Soup(name.startsWith('walFeather')); this.m.set(name, s); } return s; }
  flush(b, pos = [0, 0, 0], rot = 0) {
    for (const [name, s] of this.m) { if (!s.count) continue; if (DEBUG) { const k = s.p.findIndex(v => !Number.isFinite(v)); if (k >= 0) console.warn('NaN in soup', name, k / 9 | 0, b.zone); } b.unique(s.geometry(), name, pos, rot); }
    this.m.clear();
  }
  get triangles() { let n = 0; for (const s of this.m.values()) n += s.count; return n; }
}

// ---------------------------------------------------------------- stations along a path (mitred)
// side = +1: the outward normal is on the left of the travel direction (-tz, tx); -1: on the right.
export function stations(path, { step = 3, closed = false, side = 1, uStart = 0, prev = null, next = null } = {}) {
  const n = path.length, E = closed ? n : n - 1, edges = [];
  const mkEdge = (a, c) => { const dx = c[0] - a[0], dz = c[1] - a[1], L = hyp(dx, dz) || 1e-6, tx = dx / L, tz = dz / L; return { a, c, L, tx, tz, nx: -tz * side, nz: tx * side }; };
  for (let i = 0; i < E; i++) edges.push(mkEdge(path[i], path[(i + 1) % n]));
  const pe = !closed && prev ? mkEdge(prev, path[0]) : null, ne = !closed && next ? mkEdge(path[n - 1], next) : null;
  const miter = (e0, e1) => {
    let mx = e0.nx + e1.nx, mz = e0.nz + e1.nz, l2 = mx * mx + mz * mz;
    if (l2 < 1e-4) return [e0.nx, e0.nz];
    const k = 2 / l2, vx = mx * k, vz = mz * k, vl = hyp(vx, vz);
    return vl > 3 ? [vx / vl * 3, vz / vl * 3] : [vx, vz];
  };
  const out = []; let u = uStart;
  for (let i = 0; i < E; i++) {
    const e = edges[i], pv = closed ? edges[(i + E - 1) % E] : (i > 0 ? edges[i - 1] : pe);
    const m = Math.max(1, Math.ceil(e.L / step));
    for (let k = 0; k < m; k++) {
      const t = k / m; let v;
      if (k === 0) v = pv ? miter(pv, e) : [e.nx, e.nz]; else v = [e.nx, e.nz];
      out.push({ x: lerp(e.a[0], e.c[0], t), z: lerp(e.a[1], e.c[1], t), mx: v[0], mz: v[1], u: u + e.L * t, tx: e.tx, tz: e.tz, nx: e.nx, nz: e.nz, edge: i });
    }
    u += e.L;
  }
  const last = edges[E - 1], c = last.c;
  const vEnd = closed ? miter(last, edges[0]) : (ne ? miter(last, ne) : [last.nx, last.nz]);
  out.push({ x: c[0], z: c[1], mx: vEnd[0], mz: vEnd[1], u, tx: last.tx, tz: last.tz, nx: last.nx, nz: last.nz, edge: E - 1 });
  if (closed) { const f = out[0]; out[out.length - 1] = { ...out[out.length - 1], x: f.x, z: f.z, mx: f.mx, mz: f.mz }; }
  out.length_ = u - uStart;
  return out;
}

// Loft a cross-section profile along stations. profileFn(i, st) -> [{d, y, v?, col?}] (same length at every station).
// dir: 'out' | 'in' | 'up' | 'down' decides which way the faces point.
export function loft(soup, st, profileFn, { dir = 'out', uOff = 0, uScale = 1, vOff = 0, col = null } = {}) {
  const rows = st.map((s, i) => profileFn(i, s).map(p => ({ x: s.x + s.mx * p.d, y: p.y, z: s.z + s.mz * p.d, u: (s.u + uOff) * uScale, v: (p.v ?? p.y) + vOff, col: p.col || col || [1, 1, 1] })));
  for (let i = 0; i < st.length - 1; i++) {
    const r0 = rows[i], r1 = rows[i + 1], s = st[i];
    const want = dir === 'out' ? [s.nx, .25, s.nz] : dir === 'in' ? [-s.nx, .25, -s.nz] : dir === 'up' ? [0, 1, 0] : [0, -1, 0];
    for (let j = 0; j < r0.length - 1; j++) {
      const A = r0[j], B = r1[j], C = r1[j + 1], D = r0[j + 1];
      if (hyp(A.x - D.x, A.y - D.y, A.z - D.z) < 1e-5 && hyp(B.x - C.x, B.y - C.y, B.z - C.z) < 1e-5) continue; // degenerate
      soup.quad([A.x, A.y, A.z], [B.x, B.y, B.z], [C.x, C.y, C.z], [D.x, D.y, D.z], [A.u, A.v], [B.u, B.v], [C.u, C.v], [D.u, D.v], A.col, want);
    }
  }
}

// ---------------------------------------------------------------- small solids
// Axis-aligned-in-local-frame box with metre UVs. frame: {x,z,rot} world position/rotation (rot as Builder: about y).
export function boxSolid(soup, cx, cy, cz, w, h, d, rot = 0, col = [1, 1, 1], faces = 0b111111, uvScale = 1) {
  const c = Math.cos(rot), s = Math.sin(rot);
  const P = (x, y, z) => [cx + x * c + z * s, cy + y, cz - x * s + z * c];
  const hx = w / 2, hy = h / 2, hz = d / 2;
  const f = (a, b, cc, dd, uvw, uvh, bit) => { if (!(faces & bit)) return; soup.quad(a, b, cc, dd, [0, 0], [uvw * uvScale, 0], [uvw * uvScale, uvh * uvScale], [0, uvh * uvScale], col); };
  f(P(-hx, -hy, hz), P(hx, -hy, hz), P(hx, hy, hz), P(-hx, hy, hz), w, h, 1);     // +z
  f(P(hx, -hy, -hz), P(-hx, -hy, -hz), P(-hx, hy, -hz), P(hx, hy, -hz), w, h, 2);  // -z
  f(P(hx, -hy, hz), P(hx, -hy, -hz), P(hx, hy, -hz), P(hx, hy, hz), d, h, 4);      // +x
  f(P(-hx, -hy, -hz), P(-hx, -hy, hz), P(-hx, hy, hz), P(-hx, hy, -hz), d, h, 8);  // -x
  f(P(-hx, hy, hz), P(hx, hy, hz), P(hx, hy, -hz), P(-hx, hy, -hz), w, d, 16);     // top
  f(P(-hx, -hy, -hz), P(hx, -hy, -hz), P(hx, -hy, hz), P(-hx, -hy, hz), w, d, 32); // bottom
}
// Pyramid (square base) with metre UVs.
export function pyramid(soup, cx, y0, cz, w, d, h, rot = 0, col = [1, 1, 1], apexScale = 0) {
  const c = Math.cos(rot), s = Math.sin(rot), hx = w / 2, hz = d / 2, ax = hx * apexScale, az = hz * apexScale;
  const P = (x, y, z) => [cx + x * c + z * s, y0 + y, cz - x * s + z * c];
  const b = [P(-hx, 0, hz), P(hx, 0, hz), P(hx, 0, -hz), P(-hx, 0, -hz)], t = [P(-ax, h, az), P(ax, h, az), P(ax, h, -az), P(-ax, h, -az)];
  const sl = hyp(hx, h);
  for (let k = 0; k < 4; k++) {
    const k2 = (k + 1) % 4, len = hyp(b[k][0] - b[k2][0], b[k][2] - b[k2][2]);
    soup.quad(b[k], b[k2], t[k2], t[k], [0, 0], [len, 0], [len * .5 + (apexScale ? 0 : 0), sl], [0, sl], col);
  }
  if (apexScale) soup.quad(t[0], t[1], t[2], t[3], [0, 0], [1, 0], [1, 1], [0, 1], col);
}

// ---------------------------------------------------------------- local frames, faces with openings, arches
// A frame places a model built in (u right, y up, w outward) metres into the world: origin (x,z) at height y0, rotated by rot.
export class Frame {
  constructor(x, y0, z, rot) { this.x = x; this.y0 = y0; this.z = z; this.rot = rot; this.c = Math.cos(rot); this.s = Math.sin(rot); }
  // local (u, w) -> world [x, z]
  xz(u, w) { return [this.x + u * this.c + w * this.s, this.z - u * this.s + w * this.c]; }
  // local (u, y, w) -> world [x, y, z]
  p(u, y, w) { const [x, z] = this.xz(u, w); return [x, this.y0 + y, z]; }
  // local direction (du, dw) -> world direction
  d(du, dw) { return [du * this.c + dw * this.s, -du * this.s + dw * this.c]; }
  // frame whose origin is at local (u, w) and which is rotated by extra angle (e.g. to face another direction)
  at(u, y, w, extra = 0) { const [x, z] = this.xz(u, w); return new Frame(x, this.y0 + y, z, this.rot + extra); }
  // Builder.nav helpers (angle convention matches Builder.box)
  navBox(b, u, w, du, dw, y0, y1, extra = 0) { const [x, z] = this.xz(u, w); b.nav.box(x, z, du, dw, this.y0 + y0, this.y0 + y1, this.rot + extra); }
  navFloor(b, u, w, du, dw, y, extra = 0) { const [x, z] = this.xz(u, w); b.nav.floor(x, z, du, dw, this.y0 + y, this.rot + extra); }
  navRamp(b, u, w, du, dw, ya, yb, extra = 0) { const [x, z] = this.xz(u, w); b.nav.ramp(x, z, du, dw, this.y0 + ya, this.y0 + yb, this.rot + extra); }
}

// Horseshoe opening: jambs at +-a up to springY, then a circular arc (radius R > a) to apexY. R = (s^2 + a^2) / (2 s), s = apexY - springY.
export function horseshoe(a, springY, apexY, n = 40) {
  const s = apexY - springY, R = (s * s + a * a) / (2 * s), cy = apexY - R;
  const th0 = Math.atan2(springY - cy, a); // right spring angle (<=0)
  const arc = [];
  for (let i = 0; i <= n; i++) { const th = (Math.PI - th0) + (th0 - (Math.PI - th0)) * i / n; arc.push([R * Math.cos(th), cy + R * Math.sin(th), th]); }
  return { a, springY, apexY, R, cy, arc };
}
// outline of the opening from the floor (y = 0) on the left jamb over the arch to the right jamb, as [u, y, nu, ny] (outward normals from the opening)
export function openingPath(h, bottom = 0, offset = 0, n = 40) {
  const pts = [[-h.a - offset, bottom, -1, 0]];
  const arc = h.arc;
  for (let i = 0; i < arc.length; i++) { const [u, y, th] = arc[i]; pts.push([u + Math.cos(th) * offset, y + Math.sin(th) * offset, Math.cos(th), Math.sin(th)]); }
  pts.push([h.a + offset, bottom, 1, 0]);
  return pts;
}
// Triangulated flat face with holes in the (u, y) plane. contour/holes: [[u,y],...]. uvf(u,y) -> [tu,tv]. P(u,y)->[x,y,z] world.
export function polyFace(soup, contour, holes, P, uvf, col = [1, 1, 1], want = null) {
  const V = (arr) => arr.map(p => new THREE.Vector2(p[0], p[1]));
  const all = [...contour, ...holes.flat()];
  const tris = THREE.ShapeUtils.triangulateShape(V(contour), holes.map(V));
  for (const t of tris) {
    const A = all[t[0]], B = all[t[1]], C = all[t[2]];
    soup.tri(P(A[0], A[1]), P(B[0], B[1]), P(C[0], C[1]), uvf(A[0], A[1]), uvf(B[0], B[1]), uvf(C[0], C[1]), col, want);
  }
}
// Band between two offset curves of an opening path (front face in plane w = wz), e.g. an arch ring / alfiz frame.
// uvf(pt, index, side) -> [tu, tv]; facing = +1 faces +w (outward), -1 faces -w.
export function ringFace(soup, F, path, d0, d1, wz, uvf, col = [1, 1, 1], facing = 1) {
  const dw = F.d(0, facing), want = [dw[0], 0, dw[1]];
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i], c = path[i + 1];
    const A0 = [a[0] + a[2] * d0, a[1] + a[3] * d0], A1 = [a[0] + a[2] * d1, a[1] + a[3] * d1], C0 = [c[0] + c[2] * d0, c[1] + c[3] * d0], C1 = [c[0] + c[2] * d1, c[1] + c[3] * d1];
    soup.quad(F.p(A0[0], A0[1], wz), F.p(C0[0], C0[1], wz), F.p(C1[0], C1[1], wz), F.p(A1[0], A1[1], wz), uvf(A0, i, 0), uvf(C0, i + 1, 0), uvf(C1, i + 1, 1), uvf(A1, i, 1), col, want);
  }
}
// Soffit (tunnel surface) of an opening path, between planes w0 and w1, facing the opening centre. uvf(i, w) -> [tu, tv].
export function soffit(soup, F, path, offset, w0, w1, uvf, col = [1, 1, 1]) {
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i], c = path[i + 1];
    const ax = a[0] + a[2] * offset, ay = a[1] + a[3] * offset, cx = c[0] + c[2] * offset, cy = c[1] + c[3] * offset;
    const nu = -(a[2] + c[2]) / 2, ny = -(a[3] + c[3]) / 2, dd = F.d(nu, 0);
    soup.quad(F.p(ax, ay, w0), F.p(ax, ay, w1), F.p(cx, cy, w1), F.p(cx, cy, w0), uvf(i, w0), uvf(i, w1), uvf(i + 1, w1), uvf(i + 1, w0), col, [dd[0], ny, dd[1]]);
  }
}

// ---------------------------------------------------------------- small helpers
export const UP = [0, 1, 0];
export const wantOut = (F, f = 1) => { const d = F.d(0, f); return [d[0], 0, d[1]]; };
// irregular blob outline (patches of exposed brick, fallen render)
export function blob(cx, cy, rx, ry, seed, n = 16, rough = .35) {
  const r = rnd(seed), ph = r() * 6, pts = [];
  for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2, k = 1 + (vnoise(a * 2.2 + ph, seed) - .5) * rough * 2 + (r() - .5) * rough * .5; pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); }
  return pts;
}
export function patch(me, F, mat, cx, cy, rx, ry, wz, seed, col = [1, 1, 1], rough = .35) {
  if (LOW && seed % 3) return;
  const feather = { walPatchBrick: 'walFeatherBrick', walPatchLime: 'walFeatherLime', walPatchWash: 'walFeatherLime', walPatchTapial: 'walFeatherTapial' }[mat];
  if (!feather) { polyFace(me.s(mat), blob(cx, cy, rx, ry, seed, 16, rough), [], (u, y) => F.p(u, y, wz), (u, y) => [u, y], col, wantOut(F)); return; }
  const soup = me.s(feather), r = rnd(seed), ph = r() * 6, n = 18, want = wantOut(F), at = (a, k) => [cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k];
  const kr = i => 1 + (vnoise(i / n * 2.6 * Math.PI + ph, seed) - .5) * rough * 1.6;
  const rings = [[.0, 1], [.55, 1], [.8, .85], [1.05, 0]];
  for (let i = 0; i < n; i++) {
    const a0 = i / n * Math.PI * 2, a1 = (i + 1) / n * Math.PI * 2;
    for (let j = 0; j < rings.length - 1; j++) {
      const [k0, al0] = rings[j], [k1, al1] = rings[j + 1], p00 = at(a0, k0 * kr(i)), p01 = at(a1, k0 * kr(i + 1)), p10 = at(a0, k1 * kr(i)), p11 = at(a1, k1 * kr(i + 1));
      const C = (al) => [col[0], col[1], col[2], al * .94];
      const P = p => F.p(p[0], p[1], wz), U = p => [p[0], p[1]];
      if (j === 0) soup.triC(P(p00), P(p10), P(p11), U(p00), U(p10), U(p11), C(al0), C(al1), C(al1), want);
      else { soup.triC(P(p00), P(p10), P(p11), U(p00), U(p10), U(p11), C(al0), C(al1), C(al1), want); soup.triC(P(p00), P(p11), P(p01), U(p00), U(p11), U(p01), C(al0), C(al1), C(al0), want); }
    }
  }
}
// rectangle face in the (u, y) plane of a frame at depth wz
export function rectFace(soup, F, u0, y0, u1, y1, wz, uvf, col = [1, 1, 1], facing = 1) {
  polyFace(soup, [[u0, y0], [u1, y0], [u1, y1], [u0, y1]], [], (u, y) => F.p(u, y, wz), uvf || ((u, y) => [u, y]), col, wantOut(F, facing));
}
// axis-aligned (in the frame) box: centre u, bottom y, centre w; dims du x dy x dw; world rotation from the frame
export function fbox(soup, F, u, y, w, du, dy, dw, col = [1, 1, 1], faces = 0b111111, uv = 1) {
  const [x, , z] = F.p(u, 0, w); boxSolid(soup, x, F.y0 + y + dy / 2, z, du, dy, dw, F.rot, col, faces, uv);
}
// vertical rectangle between two local points, facing local direction (fu, fw)
export function wallQuad(soup, F, u0, w0, u1, w1, y0, y1, fu, fw, col = [1, 1, 1], uvs = 1) {
  const L = hyp(u1 - u0, w1 - w0), d = F.d(fu, fw);
  soup.quad(F.p(u0, y0, w0), F.p(u1, y0, w1), F.p(u1, y1, w1), F.p(u0, y1, w0), [0, y0 * uvs], [L * uvs, y0 * uvs], [L * uvs, y1 * uvs], [0, y1 * uvs], col, [d[0], 0, d[1]]);
}
export function floorQuad(soup, F, u0, w0, u1, w1, y, col = [1, 1, 1], uvs = 1, up = true) {
  soup.quad(F.p(u0, y, w0), F.p(u1, y, w0), F.p(u1, y, w1), F.p(u0, y, w1), [u0 * uvs, w0 * uvs], [u1 * uvs, w0 * uvs], [u1 * uvs, w1 * uvs], [u0 * uvs, w1 * uvs], col, up ? UP : [0, -1, 0]);
}
// brick saw-tooth frieze (ladrillos a sardinel): ridges every `period` metres
export function sawtooth(me, F, u0, u1, y0, y1, w0, depth, period, mat = 'walBrick') {
  const soup = me.s(mat), n = Math.max(1, Math.round((u1 - u0) / period)), p = (u1 - u0) / n;
  for (let i = 0; i < n; i++) {
    const a = u0 + i * p, m = a + p / 2, c = a + p, col = [.95 + (vnoise(i * .7, 3) - .5) * .12, .93, .9];
    soup.quad(F.p(a, y0, w0), F.p(m, y0, w0 + depth), F.p(m, y1, w0 + depth), F.p(a, y1, w0), [0, y0], [p / 2, y0], [p / 2, y1], [0, y1], col, wantOut(F));
    soup.quad(F.p(m, y0, w0 + depth), F.p(c, y0, w0), F.p(c, y1, w0), F.p(m, y1, w0 + depth), [p / 2, y0], [p, y0], [p, y1], [p / 2, y1], col, wantOut(F));
  }
  fbox(soup, F, (u0 + u1) / 2, y1, w0 + depth / 2 - .04, u1 - u0 + .2, .13, depth + .1, [.95, .9, .85], 0b111101);
}
// windows with a small horseshoe opening in an alfiz
export function windowAt(me, F, u, y0, w, h, wz, { twin = false } = {}) {
  const hh = horseshoe(w / 2, y0 + h * .55, y0 + h), path = openingPath(hh, y0).map(p => [p[0] + u, p[1]]);
  polyFace(me.s('walDarkOver'), path, [], (uu, y) => F.p(uu, y, wz + .02), (uu, y) => [uu, y], [1, 1, 1], wantOut(F));
  const hole = openingPath(hh, y0).map(p => [p[0] + u, p[1]]);
  const m = .26;
  polyFace(me.s('walPatchLime'), [[u - w / 2 - m, y0 - .12], [u + w / 2 + m, y0 - .12], [u + w / 2 + m, y0 + h + m], [u - w / 2 - m, y0 + h + m]], [hole], (uu, y) => F.p(uu, y, wz + .05), (uu, y) => [uu, y], [1.05, 1.02, .98], wantOut(F));
  fbox(me.s('walPatchLime'), F, u, y0 - .22, wz + .08, w + 2 * m + .08, .12, .22, [1, .98, .95], 0b111101);
}


// ---------------------------------------------------------------- tower data (real OSM footprints, local metres)
export const TOWERS = {
  picos: [[202.8, 14.2], [198.13, 8.36], [191.55, 13.63], [196.22, 19.47]],
  cadi: [[260.75, 61.07], [254.13, 67.3], [257.81, 71.21], [264.42, 64.98]],
  cautiva: [[298.0, 121.92], [310.08, 115.29], [306.17, 108.18], [294.09, 114.8]],
  infantas: [[343.08, 163.11], [338.24, 171.33], [336.23, 174.77], [344.74, 179.78], [346.33, 177.09], [351.61, 168.12]],
  cabo: [[404.24, 213.48], [406.44, 212.97], [411.52, 211.8], [415.35, 214.11], [415.79, 218.91], [411.52, 221.04], [409.31, 219.45], [407.54, 220.32]],
  agua: [[394.32, 261.78], [393.97, 270.39], [393.94, 271.03], [393.89, 272.44], [405.07, 272.91], [405.51, 262.24], [402.02, 262.09]],
  juanArce: [[358.24, 282.84], [361.64, 291.35], [367.44, 289.02], [364.01, 280.42], [363.8, 279.9], [363.62, 279.44], [357.81, 281.76], [358.03, 282.32]],
  baltasar: [[324.8, 288.09], [330.16, 288.37], [330.61, 280.07], [330.66, 279.41], [330.69, 278.81], [325.27, 278.52], [325.26, 279.16], [325.25, 279.78]],
  sieteSuelos: [[252.18, 303.47], [252.77, 306.98], [255.1, 309.7], [258.22, 311.06], [261.92, 311.45], [266.41, 311.45], [268.94, 309.89], [271.08, 307.37], [271.48, 303.08], [271.76, 276.18], [270.92, 276.13], [262.97, 275.61], [254.08, 275.07], [253.11, 275.02]],
  capitan: [[213.23, 264.47], [210.54, 271.09], [216.76, 273.82], [219.95, 267.21], [220.22, 266.69], [220.52, 266.12], [213.7, 263.28], [213.45, 263.94]],
  bruja: [[175.9, 247.02], [172.34, 252.77], [177.8, 256.15], [181.35, 250.38]],
  cabezas: [[129.5, 211.59], [113.4, 230.97], [117.44, 237.03], [123.56, 240.23], [140.77, 219.99], [131.9, 213.26]],
  abencerrajes: [[86.18, 179.72], [90.08, 174.44], [98.36, 181.65], [95.49, 184.96], [93.76, 186.94]],
  carros: [[30.18, 150.05], [31.79, 146.29], [33.71, 147.15], [34.85, 147.68], [40.14, 149.85], [38.52, 153.62], [34.46, 151.89], [32.03, 150.85]],
  barba: [[-10.71, 135.82], [-12.23, 138.97], [-22.4, 134.05], [-20.87, 130.9]],
  bibRambla: [[-29.09, 196.45], [-28.96, 183.99], [-21.12, 184.08], [-21.25, 196.52]],
  mohamed: [[-74.23, -24.96], [-85.93, -24.74], [-85.85, -31.5], [-85.89, -34.55], [-74.05, -33.24], [-74.25, -28.97]],
  rocas: [[-108.04, 95.28], [-114.91, 93.01], [-117.59, 101.07], [-110.4, 103.1]],
  bastion: [[-50.59, 137.49], [-54.97, 144.7], [-55.62, 147.54], [-55.57, 149.54], [-53.96, 152.58], [-50.72, 153.43], [-48.39, 153.25], [-46.35, 151.97], [-43.84, 148.98], [-42.29, 146.71], [-41.39, 144.87]],
  justicia: [[-62.16, 116.51], [-67.7, 129.74], [-54.83, 135.12], [-49.29, 121.88]],
};

// ---------------------------------------------------------------- shared helpers for ground and wall feet
// Ground overrides: other modules (gates.js: the esplanade terrace) register functions (x, z) -> height | null so that the
// walls stand on the built-up ground instead of the DEM below it.
const OVERRIDES = [];
export function registerGround(fn) { OVERRIDES.push(fn); }
export function gnd(x, z) { for (const f of OVERRIDES) { const h = f(x, z); if (h !== null && h !== undefined) return h; } return terrainHeight(x, z); }
export function groundAt(x, z, perimeter) {
  return insidePolygon(x, z, perimeter) ? 0 : gnd(x, z);
}
export const centroid = p => [p.reduce((s, v) => s + v[0], 0) / p.length, p.reduce((s, v) => s + v[1], 0) / p.length];
export function polyArea(p) { let a = 0; for (let i = 0; i < p.length; i++) { const q = p[(i + 1) % p.length]; a += p[i][0] * q[1] - q[0] * p[i][1]; } return a / 2; }
export function pointInPoly(x, z, poly, pad = 0) {
  if (!pad) return insidePolygon(x, z, poly);
  if (insidePolygon(x, z, poly)) return true;
  for (let i = 0; i < poly.length; i++) { const a = poly[i], c = poly[(i + 1) % poly.length]; if (distSeg(x, z, a, c) < pad) return true; }
  return false;
}
export function distSeg(x, z, a, c) {
  const dx = c[0] - a[0], dz = c[1] - a[1], l2 = dx * dx + dz * dz || 1e-9, t = clamp(((x - a[0]) * dx + (z - a[1]) * dz) / l2, 0, 1);
  return hyp(x - (a[0] + dx * t), z - (a[1] + dz * t));
}

// ---------------------------------------------------------------- the masonry skin (shared by curtain walls and towers)
const LIFT = 6 / 7; // m: height of one rammed-earth lift (matches the baked texture)
const TONE = (st, o, rand) => {
  const rr = rnd((o.seed | 0) * 313 + 17), tint = [1 + (rr() - .5) * .10, 1 + (rr() - .5) * .06, 1 + (rr() - .5) * .14], gl = .9 + rr() * .16;
  return (i, y) => {
    const s = st[i], t = gl * (.93 + .09 * vnoise(s.u / 9 + y * .05, o.seed) + .08 * vnoise(s.u / 31 + 7, o.seed + 11) + (rand() - .5) * .02) * (1 - .12 * clamp(1 - (y + 6) / 10, 0, 1) * 0);
    return [t * tint[0], t * tint[1] * (.98 + .03 * vnoise(s.u / 5, o.seed + 3)), t * tint[2] * (.97 + .05 * vnoise(s.u / 7, o.seed + 5))];
  };
};

// Outer face of a wall/tower along stations: rubble plinth with a ledge, stacked tapial lifts, corbelled brick string course.
// o: H (offset of the face at the top), bw (batter), topAt(i), plinthH, mats{body,plinth}, seed. info[i] = {foot, ground}.
// Returns dEdge(i): the outer offset of the crown edge.
export function skin(me, st, info, o, tone) {
  const H = o.H, bwF = typeof o.bw === 'function' ? o.bw : () => o.bw, topAt = o.topAt, seed = o.seed;
  const outerD = (i, y) => H + bwF(i) * (topAt(i) - y);
  const plinthTop = i => clamp(info[i].ground + (o.plinthH ?? 2.6), info[i].foot + 3, topAt(i) - 2.4);
  let maxPl = 3; for (let i = 0; i < st.length; i++) maxPl = Math.max(maxPl, plinthTop(i) - info[i].foot);
  const nPl = clamp(Math.ceil(maxPl / 1.8), 2, 26);
  loft(me.s(o.mats.plinth), st, (i, s) => {
    const yp = plinthTop(i), yb = info[i].foot, bp = typeof o.plinthBatter === 'function' ? o.plinthBatter(i) : (o.plinthBatter ?? .20), d0 = outerD(i, yp) + .22, pts = [];
    for (let k = 0; k <= nPl; k++) { const y = lerp(yb, yp, k / nPl); pts.push({ d: d0 + bp * (yp - y) + (vnoise(s.u / 5 + k * 2.7, seed + 70 + k) - .5) * .12, y, v: y, col: tone(i, y).map(c => c * (.84 + .16 * k / nPl)) }); }
    return pts;
  }, { dir: 'out' });
  loft(me.s(o.mats.plinth), st, (i) => { const yp = plinthTop(i), d0 = outerD(i, yp); return [{ d: d0 + .22, y: yp, v: 0, col: [1, .96, .9] }, { d: d0, y: yp, v: .22, col: [1, .96, .9] }]; }, { dir: 'up' });
  // lifts: joints at absolute multiples of one tapial lift so that the formwork lines stay horizontal while the wall follows the slope
  let kMin = 1e9, kMax = -1e9; for (let i = 0; i < st.length; i++) { kMin = Math.min(kMin, Math.floor(plinthTop(i) / LIFT)); kMax = Math.max(kMax, Math.ceil((topAt(i) - .75) / LIFT)); }
  loft(me.s(o.mats.body), st, (i, s) => {
    const yp = plinthTop(i), yt = topAt(i) - .75, pts = [];
    for (let k = kMin; k <= kMax; k++) {
      const y = clamp(k * LIFT, yp, yt), jit = (vnoise(s.u / 7 + k * 5.3, seed + k) - .5) * .03;
      pts.push({ d: outerD(i, y) + jit, y, v: y, col: tone(i, y) });
    }
    return pts;
  }, { dir: 'out' });
  const brick = o.mats.course || 'walBrick';
  loft(me.s(brick), st, (i) => {
    const yt = topAt(i), d = outerD(i, yt - .75);
    return [{ d, y: yt - .75, v: 0, col: [.95, .92, .9] }, { d: d + .10, y: yt - .66, v: .1 }, { d: d + .10, y: yt - .36, v: .4 }, { d: d + .16, y: yt - .30, v: .46 }, { d: d + .16, y: yt - .02, v: .74 }];
  }, { dir: 'out' });
  loft(me.s(brick), st, (i) => { const yt = topAt(i), d = outerD(i, yt - .75); return [{ d: d + .10, y: yt - .66, v: 0 }, { d: d, y: yt - .66, v: .1 }]; }, { dir: 'down' });
  return i => outerD(i, topAt(i) - .75) + .16;
}
// foot / ground of every station: the face is sampled at its battered foot
export function footInfo(st, o) {
  const H = o.H, bwF = typeof o.bw === 'function' ? o.bw : () => o.bw, g = o.ground || gnd;
  const info = st.map((s, i) => {
    const top = o.topAt(i), bw = bwF(i);
    let yb0 = g(s.x + s.mx * (H + 1), s.z + s.mz * (H + 1));
    for (let it = 0; it < 2; it++) {
      const dFoot = H + bw * (top - yb0) + .5;
      yb0 = Math.min(g(s.x + s.mx * dFoot, s.z + s.mz * dFoot), g(s.x + s.mx * (dFoot + 2.5), s.z + s.mz * (dFoot + 2.5)));
    }
    const g2 = g(s.x + s.mx * (H + 2.5), s.z + s.mz * (H + 2.5));
    return { foot: Math.min(yb0, 0) - 1.4, ground: Math.max(yb0, g2) };
  });
  for (let k = 0; k < 2; k++) for (let i = 1; i < info.length - 1; i++) info[i].foot = Math.min(info[i].foot, (info[i - 1].foot + info[i].foot * 2 + info[i + 1].foot) / 4);
  return info;
}

// Rubble spur (espolón) leaning against the outer face of a tall wall: tapering in plan and section.
function spur(me, st, info, i, outerD, topAt, o) {
  if (LOW) return false;
  const a = st[i], c = st[i + 1]; if (!c || a.edge !== c.edge) return false;
  const mx = (a.x + c.x) / 2, mz = (a.z + c.z) / 2, nx = a.nx, nz = a.nz, tx = a.tx, tz = a.tz, k = .5;
  const yb = Math.min(info[i].foot, info[i + 1].foot), yt = topAt(i) - 1.4, hw0 = o.hw ?? .85, hw1 = hw0 * .72, p0 = o.p0 ?? 1.5, p1 = .38, n = 6, soup = me.s(o.mat || 'walRubble'), cap = me.s('walAshlarGrey');
  const f = y => outerD(i, y) * .5 + outerD(i + 1, y) * .5;
  const P = (off, u, y) => [mx + nx * off + tx * u, y, mz + nz * off + tz * u];
  const rows = []; for (let r = 0; r <= n; r++) { const y = lerp(yb, yt, r / n), t = r / n, p = lerp(p0, p1, Math.pow(t, .8)), hw = lerp(hw0, hw1, t); rows.push({ y, off: f(y) + p, off0: f(y) - .05, hw }); }
  const col = [.95, .92, .88];
  for (let r = 0; r < n; r++) {
    const A = rows[r], B = rows[r + 1];
    soup.quad(P(A.off, -A.hw, A.y), P(A.off, A.hw, A.y), P(B.off, B.hw, B.y), P(B.off, -B.hw, B.y), [0, A.y], [A.hw * 2, A.y], [B.hw * 2, B.y], [0, B.y], col, [nx, .3, nz]);
    for (const s of [-1, 1]) soup.quad(P(A.off0, s * A.hw, A.y), P(A.off, s * A.hw, A.y), P(B.off, s * B.hw, B.y), P(B.off0, s * B.hw, B.y), [0, A.y], [A.off - A.off0, A.y], [B.off - B.off0, B.y], [0, B.y], col, [tx * s, 0, tz * s]);
  }
  const T = rows[n]; cap.quad(P(T.off, -T.hw - .08, T.y), P(T.off, T.hw + .08, T.y), P(T.off0, T.hw + .08, T.y), P(T.off0, -T.hw - .08, T.y), [0, 0], [1, 0], [1, 1], [0, 1], [1, .97, .93], [0, 1, 0]);
  cap.quad(P(T.off, -T.hw - .08, T.y), P(T.off, T.hw + .08, T.y), P(T.off, T.hw + .08, T.y + .22), P(T.off, -T.hw - .08, T.y + .22), [0, 0], [1, 0], [1, .2], [0, .2], [1, .97, .93], [nx, 0, nz]);
  return true;
}

// ---------------------------------------------------------------- the curtain wall
// One run of curtain wall. o: top (y of the wall-walk), thick (half thickness at the top), mats, merlons, seed, side
function curtainRun(me, ctx, pts, o) {
  const st = stations(pts, { step: 3.2, side: o.side, uStart: o.uStart || 0, prev: o.prev, next: o.next });
  const H = o.thick, bw = o.batterFn ? (i => o.batterFn(st[i])) : (o.batter ?? .055), rand = rnd(o.seed * 977 + 13);
  const topAt = i => (o.topFn ? o.topFn(st[i]) : o.top);
  const info = footInfo(st, { H, bw, topAt });
  const tone = TONE(st, o, rand);
  const bwF_ = typeof bw === 'function' ? bw : () => bw, outerD_ = i => (y => H + bwF_(i) * (topAt(i) - y));
  const dEdge = skin(me, st, info, { H, bw, topAt, seed: o.seed, plinthH: o.plinthH, plinthBatter: o.batterFn ? (i => (o.batterFn(st[i]) < .03 ? .04 : .2)) : undefined, mats: { body: o.mats.body, plinth: o.mats.plinth } }, tone);
  // rubble spurs on the tall stretches: one every ~17-26 m where the wall stands more than 12 m above the slope
  { const rs = rnd(o.seed * 211 + 5); let acc = 6 + rs() * 8, last = 0; for (let i = 0; i < st.length - 1; i++) { acc -= hyp(st[i + 1].x - st[i].x, st[i + 1].z - st[i].z); if (acc < 0 && topAt(i) - info[i].ground > 12 && st[i + 1].edge === st[i].edge) { if (spur(me, st, info, i, (j, y) => outerD_(j)(y), topAt, { hw: .75 + rs() * .3, p0: 1.2 + rs() * .5 })) acc = 17 + rs() * 9; } } }
  const parapetOut = -H + .38;
  // crown: walk pavement, parapet
  loft(me.s('walBrickB'), st, (i) => [{ d: dEdge(i), y: topAt(i), v: 0 }, { d: parapetOut, y: topAt(i), v: dEdge(i) - parapetOut }], { dir: 'up', col: [.9, .88, .86] });
  let kIn = 2; for (let i = 0; i < st.length; i++) kIn = Math.max(kIn, Math.ceil((topAt(i) + 1.3) / LIFT) + 1);
  loft(me.s(o.mats.inner), st, (i, s) => {
    const yt = topAt(i) + 1.0, pts = [];
    for (let k = -1; k <= kIn; k++) {
      const y = clamp(k * LIFT, -.3, yt), d = -(H + .015 * (topAt(i) - y)) + (vnoise(s.u / 6 + k * 3.1, o.seed + 40 + k) - .5) * .03;
      pts.push({ d, y, v: y, col: tone(i, y).map(c => c * (.92 + .1 * clamp(y / 8, 0, 1))) });
    }
    return pts;
  }, { dir: 'in' });
  loft(me.s('walLime'), st, (i) => [{ d: parapetOut, y: topAt(i), v: 0 }, { d: parapetOut, y: topAt(i) + 1.0, v: 1.0 }], { dir: 'out', col: [1, .98, .96] });
  loft(me.s('walLime'), st, (i) => [{ d: parapetOut, y: topAt(i) + 1.0, v: 0 }, { d: -H, y: topAt(i) + 1.0, v: .4 }], { dir: 'up', col: [1.02, 1, .98] });
  if (o.merlons) merlons(me, st, dEdge, topAt, o);
  // inner face: arrow loops with rendered frames every 9-15 m, and now and then a postern door (not walkable: a rendering detail)
  if (!o.noInner) {
    const rs = rnd(o.seed * 419 + 3); let acc = 4 + rs() * 7, doorAcc = 28 + rs() * 40;
    for (let i = 0; i < st.length - 1; i++) {
      const a = st[i], c = st[i + 1], L = hyp(c.x - a.x, c.z - a.z); acc -= L; doorAcc -= L;
      if (a.edge !== c.edge || (acc >= 0 && doorAcc >= 0)) continue;
      const top = topAt(i), x = (a.x + c.x) / 2 - a.nx * (H + .015 * (top - 1) + .015), z = (a.z + c.z) / 2 - a.nz * (H + .015 * (top - 1) + .015), G = new Frame(x, 0, z, Math.atan2(-a.nx, -a.nz));
      if (doorAcc < 0 && top > 3.6) { doorAt(me, G, 0, 0, 1.1, 2.25, 0); doorAcc = 38 + rs() * 50; acc = 5 + rs() * 5; }
      else { windowAt(me, G, 0, Math.max(1.6, top - 3.3), .26, 1.05, 0); acc = 9 + rs() * 8; if (doorAcc < 0) doorAcc = 20; }
    }
  }
  // Paseo de las Torres: a compacted-gravel walk with a cobbled kerb along the inner foot of the north wall
  if (o.paseo) {
    const sub = st.filter(s => s.x > 154 && s.x < 190 && s.z < 20 && s.z > 5), bis = [];
    for (let i = 0; i < sub.length - 1; i++) if (sub[i + 1].edge === sub[i].edge || true) bis.push(sub[i]);
    if (sub.length > 1) {
      const idx = i => i;
      loft(me.s('walGravel'), sub, () => [{ d: -(H + 1.7), y: .03, v: 0 }, { d: -(H + 4.9), y: .03, v: 3.2 }], { dir: 'up', col: [1, .97, .93] });
      loft(me.s('walCobble'), sub, () => [{ d: -(H + 1.7), y: .035, v: 0 }, { d: -(H + 2.1), y: .035, v: .4 }], { dir: 'up', col: [.9, .88, .85] });
      loft(me.s('walCobble'), sub, () => [{ d: -(H + 4.5), y: .035, v: 0 }, { d: -(H + 4.9), y: .035, v: .4 }], { dir: 'up', col: [.9, .88, .85] });
    }
  }
  for (let i = 0; i < st.length - 1; i++) {
    const a = st[i], c = st[i + 1], dx = c.x - a.x, dz = c.z - a.z, L = hyp(dx, dz);
    if (L < .05) continue; const rot = -Math.atan2(dz, dx);
    ctx.b.nav.box((a.x + c.x) / 2, (a.z + c.z) / 2, L + 1.2, 2 * H + .4, -60, topAt(i), rot);
  }
  return { st, info };
}

// ---------------------------------------------------------------- towers from OSM footprints
export function outwardSign(poly) {
  const a = poly[0], c = poly[1], tx = c[0] - a[0], tz = c[1] - a[1], l = hyp(tx, tz), nx = -tz / l, nz = tx / l, mx = (a[0] + c[0]) / 2, mz = (a[1] + c[1]) / 2;
  return insidePolygon(mx + nx * .3, mz + nz * .3, poly) ? -1 : 1;
}
// Frame of polygon edge i seen from outside: origin at fraction `at` of the edge, u to the right, w outward.
export function edgeFrame(poly, i, sign, y0 = 0, at = .5) {
  const a = poly[i], c = poly[(i + 1) % poly.length], dx = c[0] - a[0], dz = c[1] - a[1], L = hyp(dx, dz) || 1e-6, tx = dx / L, tz = dz / L;
  const nx = -tz * sign, nz = tx * sign;
  return { F: new Frame(a[0] + dx * at, y0, a[1] + dz * at, Math.atan2(nx, nz)), L, at, sign, nx, nz, a, c };
}
// minimal-area rectangle of a polygon: {cx, cz, w, d, rot} (rot as Builder boxes)
export function minRect(poly) {
  let best = null;
  for (let k = 0; k < poly.length; k++) {
    const a = poly[k], c = poly[(k + 1) % poly.length], ang = Math.atan2(c[1] - a[1], c[0] - a[0]), ca = Math.cos(-ang), sa = Math.sin(-ang);
    const us = poly.map(q => q[0] * ca - q[1] * sa), vs = poly.map(q => q[0] * sa + q[1] * ca);
    const u0 = Math.min(...us), u1 = Math.max(...us), v0 = Math.min(...vs), v1 = Math.max(...vs), area = (u1 - u0) * (v1 - v0);
    if (!best || area < best.area) { const mu = (u0 + u1) / 2, mv = (v0 + v1) / 2; best = { area, cx: mu * Math.cos(ang) - mv * Math.sin(ang), cz: mu * Math.sin(ang) + mv * Math.cos(ang), w: u1 - u0, d: v1 - v0, rot: -ang }; }
  }
  return best;
}
// A solid tower on a footprint. o: top (world y of the platform), bw, mats, seed, crown ('merlons'|'picos'|'coping'|'flat'), plinthH, ground (fn), block (nav)
export function prismTower(me, ctx, poly, o) {
  const sign = outwardSign(poly), st = stations(poly, { step: o.step || 2.6, closed: true, side: sign });
  const rand = rnd(o.seed * 53 + 9), bw = o.bw ?? .035, H = 0, topAt = () => o.top;
  const info = footInfo(st, { H, bw, topAt, ground: o.ground });
  const tone = TONE(st, o, rand);
  const bwF_ = typeof bw === 'function' ? bw : () => bw, outerD_ = i => (y => H + bwF_(i) * (topAt(i) - y));
  const dEdge = skin(me, st, info, { H, bw, topAt, seed: o.seed, plinthH: o.plinthH, plinthBatter: o.plinthBatter, mats: { body: o.mats.body, plinth: o.mats.plinth, course: o.mats.course } }, tone);
  const crown = o.crown || 'merlons', ring = { merlons: .85, picos: .6, coping: 1.15, flat: .55 }[crown], pTop = o.top + ring, pm = o.mats.parapet || 'walLime';
  loft(me.s(pm), st, i => [{ d: dEdge(i), y: o.top, v: 0 }, { d: dEdge(i), y: pTop, v: ring }], { dir: 'out', col: [1, .97, .94] });
  const th = crown === 'merlons' || crown === 'picos' ? .55 : .5;
  if (crown === 'coping' || crown === 'flat') {
    // brick coping slab with a small overhang
    loft(me.s('walBrickB'), st, i => [{ d: dEdge(i) + .1, y: pTop, v: 0 }, { d: dEdge(i) + .1, y: pTop + .13, v: .13 }], { dir: 'out', col: [.95, .9, .86] });
    loft(me.s('walBrickB'), st, i => [{ d: dEdge(i) + .1, y: pTop + .13, v: 0 }, { d: dEdge(i) - th - .08, y: pTop + .13, v: th + .18 }], { dir: 'up', col: [1, .95, .9] });
    loft(me.s(pm), st, i => [{ d: dEdge(i) - th - .08, y: pTop + .13, v: .13 }, { d: dEdge(i) - th - .08, y: pTop, v: 0 }, { d: dEdge(i) - th - .08, y: o.top, v: ring }], { dir: 'in', col: [.97, .95, .92] });
  } else {
    loft(me.s(pm), st, i => [{ d: dEdge(i), y: pTop, v: 0 }, { d: dEdge(i) - th, y: pTop, v: th }], { dir: 'up', col: [1.02, 1, .98] });
    loft(me.s(pm), st, i => [{ d: dEdge(i) - th, y: pTop, v: ring }, { d: dEdge(i) - th, y: o.top, v: 0 }], { dir: 'in', col: [.97, .95, .92] });
  }
  polyFace(me.s('walBrickB'), poly.map(p => [p[0], p[1]]), [], (x, z) => [x, o.top, z], (x, z) => [x, z], [.85, .83, .8], [0, 1, 0]);
  if (crown === 'merlons') merlons(me, st, i => dEdge(i), () => pTop, { ...o, merlonH: o.merlonH || 1.1, capH: o.capH || .45, mats: { merlon: 'walLime', cap: 'walLime' } });
  if (crown === 'picos') merlons(me, st, i => dEdge(i), () => pTop, { ...o, merlonH: 1.55, capH: 1.15, merlonPitch: 1.3, merlonW: .72, mats: { merlon: 'walLime', cap: 'walLime' } });
  if (o.block !== false) { const r = minRect(poly); ctx.b.nav.box(r.cx, r.cz, r.w, r.d, -60, o.top + 1, r.rot); }
  return { st, info, sign, dEdge, pTop };
}

// pyramid-capped merlons: 0.62 thick, 0.8 wide, 1.2 high + cap, one every 1.5 m along the outer edge
function merlons(me, st, dEdge, topAt, o) {
  const soup = me.s(o.mats.merlon || 'walLime'), cap = me.s(o.mats.cap || 'walLime'), rand = rnd(o.seed * 31 + 7);
  const pitch = o.merlonPitch || 1.5, w = o.merlonW || .8, th = .62, hgt = o.merlonH || 1.2;
  const P = st.map((s, i) => ({ x: s.x + s.mx * (dEdge(i) - th / 2), z: s.z + s.mz * (dEdge(i) - th / 2), y: topAt(i), nx: s.nx, nz: s.nz }));
  let carry = pitch * .5;
  for (let i = 0; i < P.length - 1; i++) {
    const a = P[i], c = P[i + 1], dx = c.x - a.x, dz = c.z - a.z, L = hyp(dx, dz); if (L < 1e-4) continue;
    const rot = -Math.atan2(dz, dx); let t = carry;
    while (t < L) {
      const f = t / L, x = a.x + dx * f, z = a.z + dz * f, y = a.y + (c.y - a.y) * f, roll = rand();
      const damaged = !o.noDamage && roll < .07, hh = damaged ? hgt * (.35 + rand() * .35) : hgt + (rand() - .5) * .14;
      const col = [.97 + (rand() - .5) * .08, .95 + (rand() - .5) * .08, .93 + (rand() - .5) * .08];
      if (!(roll > .965 && !o.noDamage)) {                      // a few merlons are simply gone
        boxSolid(soup, x, y + hh / 2, z, w, hh, th, rot, col, damaged ? 0b011111 : 0b001111);
        if (!damaged) { pyramid(cap, x, y + hh, z, w + .1, th + .1, (o.capH || .46) + (rand() - .5) * .08, rot, [1, .97, .93]);
          if (!LOW && !o.noSlit && roll > .55 && roll < .8) { const ox = a.nx * (th / 2 + .012), oz = a.nz * (th / 2 + .012), tx = dx / L * .05, tz = dz / L * .05; me.s('walDarkOver').quad([x + ox - tx, y + hh * .3, z + oz - tz], [x + ox + tx, y + hh * .3, z + oz + tz], [x + ox + tx, y + hh * .78, z + oz + tz], [x + ox - tx, y + hh * .78, z + oz - tz], [0, 0], [1, 0], [1, 1], [0, 1], [1, 1, 1], [a.nx, 0, a.nz]); } }
      }
      t += pitch;
    }
    carry = t - L;
  }
}

// ---------------------------------------------------------------- the named towers
// Each entry: platform height above the plateau (world y), crown style, body / plinth materials, features.
const SPECS = {
  picos: { top: 12.6, crown: 'picos', seed: 31, mats: ['walTapialC', 'walRubble'], door: 'inner', slits: 2, twin: 0, patches: 1 },
  cadi: { top: 10.8, crown: 'merlons', seed: 32, mats: ['walTapial', 'walRubble'], door: 'inner', slits: 3, twin: 0 },
  cautiva: { top: 12.8, crown: 'coping', seed: 33, mats: ['walTapialB', 'walAshlarGrey'], door: 'inner', slits: 3, twin: 1, brickBase: 1.6 },
  infantas: { top: 13.6, crown: 'coping', seed: 34, mats: ['walTapialB', 'walRubble'], door: 'inner', slits: 2, twin: 2, turret: true },
  cabo: { top: 5.4, crown: 'flat', seed: 35, mats: ['walRubble', 'walRubble'], kind: 'bastion', plinthH: 5 },
  agua: { top: 17.0, crown: 'flat', seed: 36, mats: ['walTapialB', 'walBrick'], door: 'inner', slits: 3, twin: 0, brickBase: 7, aqueduct: true },
  juanArce: { top: 9.4, crown: 'coping', seed: 37, mats: ['walTapialC', 'walRubble'], slits: 2 },
  baltasar: { top: 9.0, crown: 'coping', seed: 38, mats: ['walTapial', 'walAshlarGrey'], door: 'inner', slits: 2, twin: 1 },
  sieteSuelos: { top: 17.0, crown: 'flat', seed: 39, mats: ['walTapialB', 'walBrick'], kind: 'siete', plinthH: 6, brickBase: 5 },
  capitan: { top: 12.0, crown: 'merlons', seed: 40, mats: ['walTapialC', 'walRubble'], slits: 3, twin: 1 },
  bruja: { top: 10.6, crown: 'merlons', seed: 41, mats: ['walTapial', 'walAshlarGrey'], door: 'inner', slits: 2 },
  cabezas: { top: 11.6, crown: 'flat', seed: 42, mats: ['walTapialB', 'walRubble'], kind: 'bastion', slits: 4, plinthH: 5 },
  abencerrajes: { top: 11.0, crown: 'merlons', seed: 43, mats: ['walTapialC', 'walRubble'], door: 'inner', slits: 2, twin: 1 },
  carros: { top: 9.8, crown: 'merlons', seed: 44, mats: ['walTapial', 'walAshlarGrey'], slits: 2 },
  barba: { top: 9.4, crown: 'merlons', seed: 45, mats: ['walTapialB', 'walRubble'], slits: 2, twin: 1 },
  bibRambla: { kind: 'gatehouse', seed: 46, mats: ['walAshlar', 'walRubble'] },
  mohamed: { top: 11.4, crown: 'merlons', seed: 47, mats: ['walTapial', 'walAshlarGrey'], door: 'inner', slits: 2, twin: 1 },
  rocas: { top: 8.4, crown: 'coping', seed: 48, mats: ['walTapialC', 'walRubble'], slits: 2 },
};
export function doorAt(me, F, u, y0, w, h, wz, mat = 'walWood') {
  const hh = horseshoe(w / 2, y0 + h * .68, y0 + h), path = openingPath(hh, y0).map(p => [p[0] + u, p[1]]), m = .24;
  polyFace(me.s(mat), path, [], (uu, y) => F.p(uu, y, wz + .02), (uu, y) => [uu * .5, y * .5], [.9, .85, .8], wantOut(F));
  polyFace(me.s('walPatchAshlar'), [[u - w / 2 - m, y0 - .1], [u + w / 2 + m, y0 - .1], [u + w / 2 + m, y0 + h + m], [u - w / 2 - m, y0 + h + m]], [path], (uu, y) => F.p(uu, y, wz + .05), (uu, y) => [uu, y], [1, .97, .93], wantOut(F));
}
// ajimez: two small horseshoe lights divided by a marble columnette, in a rendered frame
export function twinWindow(me, F, u, y0, wz, w = 1.05, h = 1.25) {
  const half = w / 2, lw = (w - .1) / 2;
  const frame = [[u - half - .26, y0 - .14], [u + half + .26, y0 - .14], [u + half + .26, y0 + h + .3], [u - half - .26, y0 + h + .3]];
  const holes = [-1, 1].map(sg => openingPath(horseshoe(lw / 2, y0 + h * .55, y0 + h), y0).map(p => [p[0] + u + sg * (lw / 2 + .05), p[1]]));
  polyFace(me.s('walDarkOver'), holes[0], [], (uu, y) => F.p(uu, y, wz + .02), (uu, y) => [uu, y], [1, 1, 1], wantOut(F));
  polyFace(me.s('walDarkOver'), holes[1], [], (uu, y) => F.p(uu, y, wz + .02), (uu, y) => [uu, y], [1, 1, 1], wantOut(F));
  polyFace(me.s('walPatchLime'), frame, holes, (uu, y) => F.p(uu, y, wz + .05), (uu, y) => [uu, y], [1.06, 1.03, .98], wantOut(F));
  fbox(me.s('gatMarble'), F, u, y0, wz + .09, .09, h * .6, .09, [1, 1, 1], 0b111111);
  fbox(me.s('walPatchLime'), F, u, y0 - .24, wz + .1, w + .6, .1, .24, [1, .98, .95], 0b111101);
}
export function turretRoof(me, cx, y0, cz, w, h, rot, mat = 'walTile') {
  // glazed-tile pyramid: eaves slightly proud, ridge cap
  pyramid(me.s(mat), cx, y0, cz, w, w, h, rot, [1, .97, .94]);
  boxSolid(me.s('walWood'), cx, y0 - .08, cz, w + .12, .16, w + .12, rot, [.8, .72, .64], 0b111101);
}

function towerFeatures(me, ctx, poly, spec, res) {
  const { sign } = res, top = spec.top, bw = .035, rand = rnd(spec.seed * 7 + 1);
  const per = ctx.perimeter, n = poly.length, out = { edges: [] };
  for (let i = 0; i < n; i++) {
    const fr = edgeFrame(poly, i, sign, 0, .5);
    if (fr.L < 2.0) continue;
    const mx = fr.a[0] + (fr.c[0] - fr.a[0]) / 2, mz = fr.a[1] + (fr.c[1] - fr.a[1]) / 2;
    const px = mx + fr.nx * 2.2, pz = mz + fr.nz * 2.2, inside = insidePolygon(px, pz, per), g = gnd(px, pz);
    out.edges.push({ i, fr, outer: !inside, ground: inside ? 0 : g, L: fr.L });
  }
  const edges = out.edges, wz = y => .05 + bw * (top - y);
  const outer = edges.filter(e => e.outer).sort((a, c) => c.L - a.L), inner = edges.filter(e => !e.outer).sort((a, c) => c.L - a.L);
  const gy = e => Math.max(e.ground, 0 * 1);                      // height where people stand beside this face
  for (const e of edges) {
    const F = e.fr.F, g = e.outer ? e.ground : 0, h0 = top - g;
    // fallen render: patches of the brick / rubble core
    for (let j = 0; j < Math.round(e.L / 3.4) + 1; j++) patch(me, F, rand() < .65 ? 'walPatchBrick' : 'walPatchLime', lerp(-e.L / 2 + 1, e.L / 2 - 1, rand()), lerp(g + h0 * .3, top - 1.5, rand()), .5 + rand() * 1.2, .4 + rand() * .9, wz(top * .5) + .01, spec.seed * 100 + j + e.i * 7, [1.02, 1, .98]);
    // stone string course under the parapet
    rectFace(me.s('walPatchAshlar'), F, -e.L / 2 + .25, top - 1.5, e.L / 2 - .25, top - 1.32, wz(top - 1.4) + .02, (u, yy) => [u, yy], [1, .98, .95]);
    // exposed brick footing on the faces beside the walls (tower plinth in brick)
    if (spec.brickBase) polyFace(me.s('walPatchBrick'), [[-e.L / 2 + .15, g + 2.9], [-e.L / 2 + .15 + e.L * .35, g + spec.brickBase + 1.1], [e.L / 2 - .6, g + spec.brickBase + .3], [e.L / 2 - .15, g + 2.9]], [], (u, yy) => F.p(u, yy, wz(g + 5) + .02), (u, yy) => [u, yy], [1.02, 1, .98], wantOut(F));
  }
  const place = (arr, k, fn) => { const e = arr[k]; if (e) fn(e, e.fr.F, e.ground, wz); };
  // slits (arrow loops) and twin windows on the outer faces; door on an inner face
  const slitY = e => Math.max(e.ground, 0) + (top - Math.max(e.ground, 0)) * .55;
  for (let k = 0; k < (spec.slits || 0); k++) { const e = outer[k % Math.max(1, outer.length)] || edges[0]; if (!e) break; const F = e.fr.F, u = lerp(-e.L * .3, e.L * .3, ((k * .618) % 1)), y = slitY(e) + (k % 2 ? -1.6 : .6); windowAt(me, F, u, y, .3, 1.15, wz(y)); }
  for (let k = 0; k < (spec.twin || 0); k++) { const e = outer[k % Math.max(1, outer.length)] || edges[0]; if (!e) break; const F = e.fr.F, y = top - 4.9 - k * 3.4; if (y < Math.max(e.ground, 0) + 3) continue; twinWindow(me, F, k ? e.L * .18 : -e.L * .12, y, wz(y)); }
  if (spec.door === 'inner') { const e = inner[0] || outer[outer.length - 1]; if (e) doorAt(me, e.fr.F, 0, 0, 1.15, 2.35, wz(1)); }
  return out;
}

function buildTowers(b, ctx, me) {
  for (const [id, spec] of Object.entries(SPECS)) {
    const poly = TOWERS[id]; if (!poly) continue;
    b.zone = 'tower-' + Math.floor(centroid(poly)[0] / 140) + '-' + Math.floor(centroid(poly)[1] / 140);
    if (spec.kind === 'gatehouse') { bibRambla(b, ctx, me, poly, spec); me.flush(b); continue; }
    const m = spec.mats;
    const res = prismTower(me, ctx, poly, { top: spec.top, seed: spec.seed, bw: spec.kind === 'bastion' ? .06 : spec.kind === 'siete' ? .028 : .035, plinthH: spec.plinthH || 3.2, crown: spec.crown, mats: { body: m[0], plinth: m[1], course: 'walBrick', parapet: 'walLime' } });
    const feat = towerFeatures(me, ctx, poly, spec, res);
    if (spec.turret) { const r = minRect(poly), rot = r.rot, yb = spec.top + 1.15; boxSolid(me.s('walLime'), r.cx, yb + 1.45, r.cz, 3.4, 2.9, 3.4, rot, [1, .97, .93], 0b001111); turretRoof(me, r.cx, yb + 2.9, r.cz, 4.3, 2.0, rot);
      for (let k = 0; k < 4; k++) { const F = new Frame(r.cx, yb, r.cz, rot + k * Math.PI / 2); windowAt(me, F, 0, .8, .5, 1.3, 1.72); } }
    if (spec.kind === 'siete') sieteSuelos(me, ctx, poly, spec, res, feat);
    if (spec.aqueduct) aqueduct(b, ctx, me, poly, spec, res, feat);
    me.flush(b);
  }
}
// Torre de los Siete Suelos: the gate between the bastions: ashlar-framed horseshoe arch with alfiz and voussoirs, recess behind
function sieteSuelos(me, ctx, poly, spec, res, feat) {
  const e = [...feat.edges].filter(q => q.outer).sort((p, q) => (q.fr.F.z - p.fr.F.z))[0]; if (!e) return;
  const F = e.fr.F; let g = -99; for (const d of [5, 8, 11, 14]) { const [px, pz] = F.xz(0, d); g = Math.max(g, gnd(px, pz)); } g = Math.min(0, g);
  const wz = .06 + .028 * (spec.top - g), hs = horseshoe(1.7, 3.15, 5.4);
  const hole = openingPath(hs, g).map(p => [p[0] + 0, p[1] + 0]);
  const gy = g;
  const pts = openingPath(hs, 0).map(p => [p[0], p[1] + gy]);
  polyFace(me.s('walPatchAshlar'), [[-3.2, gy], [3.2, gy], [3.2, gy + 8.6], [-3.2, gy + 8.6]], [pts], (u, y) => F.p(u, y, wz + .02), (u, y) => [u, y], [1.06, 1.04, 1], wantOut(F));
  const ring = openingPath(hs, 0).map(p => [p[0], p[1] + gy, p[2], p[3]]), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
  ringFace(me.s('walPatchAshlar'), F, ring, 0, .55, wz + .1, (pt, i, sd) => [sd ? .55 : 0, cr[i]], [1.1, 1.08, 1.02]);
  ringFace(me.s('walBrickB'), F, ring, .55, .8, wz + .08, (pt, i, sd) => [sd ? .25 : 0, cr[i]], [1, .95, .9]);
  // recess: soffit and a dark back wall with the inner door (the gate passage turns inside)
  for (let i = 0; i < ring.length - 1; i++) soffit(me.s('walBrick'), F, [ring[i], ring[i + 1]], 0, wz, -3.2, (k, w) => [cr[i + k], -w], [.8, .76, .72]);
  polyFace(me.s('walDarkOver'), ring, [], (u, y) => F.p(u, y, -3.2), (u, y) => [u, y], [1, 1, 1], wantOut(F));
  floorQuad(me.s('walCobble'), F, -1.7, -3.2, 1.7, wz, g + .02, [.9, .88, .84], .5);
  rectFace(me.s('walPatchAshlar'), F, -3.2, gy + 8.6, 3.2, gy + 8.85, wz + .12, (u, y) => [u, y], [1.1, 1.08, 1.02]);
}
// Torre del Agua: the Acequia Real crosses on a single stone arch beside the tower (a short aqueduct bridge with parapet)
function aqueduct(b, ctx, me, poly, spec, res, feat) {
  const e = feat.edges.filter(q => q.outer)[0] || feat.edges[0]; if (!e) return;
  const F = e.fr.F, g = e.ground, y0 = Math.max(g, -1), span = 6.2, w0 = .0, len = 14;
  const wz = .05 + .035 * (spec.top - 6);
  const ring = []; const n = 28, R = span / 2; for (let i = 0; i <= n; i++) { const t = Math.PI * (1 - i / n); ring.push([Math.cos(t) * R, Math.sin(t) * (R * .95), Math.cos(t) / 1, Math.sin(t) / 1]); }
  const base = y0 + 3.0;
  // pier and spandrel faces (stone), arch ring in brick, channel on top
  const uc = e.L / 2 + R + 1.6;
  const fr = new Frame(...F.xz(uc, 0).slice(0, 1), 0, ...F.xz(uc, 0).slice(1, 2), F.rot);
  fr.y0 = 0;
  const stone = me.s('walAshlarGrey'), arch = me.s('walBrick');
  const G = new Frame(F.xz(uc, 0)[0], 0, F.xz(uc, 0)[1], F.rot);
  polyFace(stone, [[-R - 1.6, base - 3.2], [R + 1.6, base - 3.2], [R + 1.6, base + 3.4], [-R - 1.6, base + 3.4]], [ring.map(p => [p[0], base + p[1] - 3.0])], (u, y) => G.p(u, y, .1), (u, y) => [u, y], [.95, .92, .88], wantOut(G));
  const rg = ring.map(p => [p[0], base + p[1] - 3.0, p[2], p[3]]), cl = [0]; for (let i = 1; i < rg.length; i++) cl.push(cl[i - 1] + hyp(rg[i][0] - rg[i - 1][0], rg[i][1] - rg[i - 1][1]));
  ringFace(arch, G, rg, 0, .6, .14, (pt, i, sd) => [sd ? .6 : 0, cl[i]], [1, .94, .88]);
  for (let i = 0; i < rg.length - 1; i++) soffit(arch, G, [rg[i], rg[i + 1]], 0, .14, -3.4, (k, w) => [cl[i + k], -w], [.8, .74, .68]);
  boxSolid(stone, G.p(0, 0, -1.6)[0], base + 3.55, G.p(0, 0, -1.6)[2], R * 2 + 3.4, .3, 3.4, F.rot, [1, .97, .93], 0b011111);
  b.nav.box(...(() => { const p = G.xz(0, -1.6); return [p[0], p[1], R * 2 + 3.4, 3.6, -60, base + 4]; })(), F.rot);
}
function bibRambla(b, ctx, me, poly, spec) {
  const r = minRect(poly), F = new Frame(r.cx, 0, r.cz, r.rot), W = r.w, D = r.d, g = gnd(r.cx, r.cz), hw = W / 2, hd = D / 2, top = g + 6.4;
  // the long axis is the one carrying the passage (arch on both short faces)
  const along = W >= D ? 'u' : 'w';
  const Fr = along === 'u' ? new Frame(r.cx, g, r.cz, r.rot + Math.PI / 2) : new Frame(r.cx, g, r.cz, r.rot), Wd = along === 'u' ? D : W, Ln = along === 'u' ? W : D;
  // Fr: u across the passage, w along it (faces the arch at w = +Ln/2 .. -Ln/2)
  const hs = horseshoe(1.35, 2.5, 4.4);
  for (const [f, sign] of [[Fr.at(0, 0, Ln / 2, 0), 1], [Fr.at(0, 0, -Ln / 2, Math.PI), -1]]) {
    const hole = openingPath(hs, 0).map(p => [p[0], p[1]]);
    polyFace(me.s('walAshlar'), [[-Wd / 2, -4], [Wd / 2, -4], [Wd / 2, 6.4], [-Wd / 2, 6.4]], [hole], (u, y) => f.p(u, y, 0), (u, y) => [u, y], [1, .98, .94], wantOut(f));
    const ring = openingPath(hs, 0), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
    ringFace(me.s('walBrick'), f, ring, 0, .5, .06, (pt, i, sd) => [sd ? .5 : 0, cr[i]], [1, .94, .88]);
    ringFace(me.s('walPatchAshlar'), f, ring, .5, .75, .08, (pt, i, sd) => [sd ? .25 : 0, cr[i]], [1.1, 1.08, 1.02]);
  }
  { const ring = openingPath(hs, 0), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
    const f = Fr.at(0, 0, Ln / 2, 0); for (let i = 0; i < ring.length - 1; i++) soffit(me.s('walBrick'), f, [ring[i], ring[i + 1]], 0, 0, -Ln, (k, w) => [cr[i + k], -w], [.85, .8, .75]); }
  // side faces (the long ones) and the walkable top with brick parapet
  for (const [fu, sg] of [[-Wd / 2, -1], [Wd / 2, 1]]) { const G = Fr.at(fu, 0, 0, sg > 0 ? Math.PI / 2 : -Math.PI / 2); polyFace(me.s('walRubble'), [[-Ln / 2, -4], [Ln / 2, -4], [Ln / 2, 6.4], [-Ln / 2, 6.4]], [], (u, y) => G.p(u, y, 0), (u, y) => [u, y], [1, .96, .9], wantOut(G)); }
  polyFace(me.s('walBrickB'), [[-Wd / 2, -Ln / 2], [Wd / 2, -Ln / 2], [Wd / 2, Ln / 2], [-Wd / 2, Ln / 2]], [], (u, w) => Fr.p(u, 6.4, w), (u, w) => [u, w], [.85, .8, .76], UP);
  floorQuad(me.s('walCobble'), Fr, -1.35, -Ln / 2, 1.35, Ln / 2, .03, [.9, .88, .84], .5);
  // nav: passage floor, solid sides
  Fr.navFloor(b, 0, 0, 2.7, Ln + 1, 0);
  Fr.navBox(b, -(Wd / 2 + 1.35) / 2, 0, Wd / 2 - 1.35, Ln, -60, 30); Fr.navBox(b, (Wd / 2 + 1.35) / 2, 0, Wd / 2 - 1.35, Ln, -60, 30);
}

// A row of pyramid-capped merlons along a segment given in a Frame's (u, w) plane at world height y.
export function merlonRow(me, F, a, c, y, o = {}) {
  const pitch = o.pitch || 1.5, w = o.w || .8, th = o.th || .62, h = o.h || 1.2, capH = o.capH || .46, rand = rnd((o.seed || 1) * 17 + 3);
  const body = me.s(o.mat || 'walLime'), cap = me.s(o.capMat || o.mat || 'walLime');
  const p0 = F.xz(a[0], a[1]), p1 = F.xz(c[0], c[1]), dx = p1[0] - p0[0], dz = p1[1] - p0[1], L = hyp(dx, dz), n = Math.max(1, Math.round((L - w) / pitch)), rot = -Math.atan2(dz, dx);
  for (let i = 0; i <= n; i++) {
    const t = n ? i / n : .5, x = p0[0] + dx * (w / 2 / L) + (dx * (1 - w / L)) * t, z = p0[1] + dz * (w / 2 / L) + (dz * (1 - w / L)) * t, hh = h + (rand() - .5) * .1;
    const col = [.97 + (rand() - .5) * .08, .95 + (rand() - .5) * .08, .93 + (rand() - .5) * .08];
    boxSolid(body, x, y + hh / 2, z, w, hh, th, rot, col, 0b001111);
    pyramid(cap, x, y + hh, z, w + .1, th + .1, capH + (rand() - .5) * .08, rot, [1, .97, .93]);
  }
}

// Height of the wall-walk above the plateau: low beside the gate (where the Explanada is only ~12 m below), growing to the east.
function wallTop(x, z, seed) {
  const d = hyp(x + 55, z - 123), k = clamp((d - 20) / 90, 0, 1);
  return 2.5 + k * 4.4 + (vnoise(x / 23 + z / 31, 7) - .5) * 1.1 + (vnoise(x / 6 - z / 5, 12) - .5) * .12;
}

// ---------------------------------------------------------------- perimeter processing
function excluded(mx, mz) {
  return mx < -130 || (mx > -67 && mx < 150 && mz < 35) || hyp(mx + 55, mz - 123) < 18 || hyp(mx - 370, mz - 180) < 13;
}

// The eastern visitor gate: the wall opens in a horseshoe-arched passage (the route to the Generalife steps passes through it).
function eastGate(b, ctx, me, gx, gz, tx, tz, side) {
  const nx = -tz * side, nz = tx * side, F = new Frame(gx, 0, gz, Math.atan2(nx, nz)), H = 1.05, halfL = 4.4;
  const top = wallTop(gx, gz), tt = top + 1.0, hs = horseshoe(2.2, 3.7, 6.0);
  b.zone = 'wall-gate';
  const hole = openingPath(hs, 0).map(p => [p[0], p[1]]);
  const batter = .055 * 0;
  for (const [w, f, G] of [[H, 1, F.at(0, 0, H, 0)], [-H, -1, F.at(0, 0, -H, Math.PI)]]) {
    polyFace(me.s('walTapialB'), [[-halfL, -1], [halfL, -1], [halfL, tt], [-halfL, tt]], [hole], (u, y) => G.p(u, y, 0), (u, y) => [u + 3, y], [1, .97, .94], wantOut(G));
    polyFace(me.s('walPatchAshlar'), [[-halfL, -1], [-2.2, -1], [-2.2, 3.7], [-halfL, 3.7]], [], (u, y) => G.p(u, y, .04), (u, y) => [u, y], [1, .97, .93], wantOut(G));
    polyFace(me.s('walPatchAshlar'), [[2.2, -1], [halfL, -1], [halfL, 3.7], [2.2, 3.7]], [], (u, y) => G.p(u, y, .04), (u, y) => [u, y], [1, .97, .93], wantOut(G));
    const ring = openingPath(hs, 0), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
    ringFace(me.s('walBrick'), G, ring, 0, .6, .07, (pt, i, sd) => [sd ? .6 : 0, cr[i]], [1, .94, .88]);
    ringFace(me.s('walPatchLime'), G, ring, .6, .85, .06, (pt, i, sd) => [sd ? .25 : 0, cr[i]], [1.05, 1.02, .98]);
    sawtooth(me, G, -2.6, 2.6, top - 2.4, top - 1.8, .06, .16, .3, 'walBrickB');
  }
  const ring = openingPath(hs, 0), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
  for (let i = 0; i < ring.length - 1; i++) { const jamb = i === 0 || i === ring.length - 2; soffit(me.s(jamb ? 'walAshlarGrey' : 'walBrick'), F, [ring[i], ring[i + 1]], 0, -H, H, jamb ? (k, w) => [w, ring[i + k][1]] : (k, w) => [cr[i + k], w], [.85, .8, .75]); }
  floorQuad(me.s('walCobble'), F, -2.2, -H, 2.2, H, .03, [.95, .93, .9], .5);
  polyFace(me.s('walBrickB'), [[-halfL, -H], [halfL, -H], [halfL, H], [-halfL, H]], [], (u, w) => F.p(u, top, w), (u, w) => [u, w], [.85, .82, .78], UP);
  // parapet, merlons on both faces
  for (const [w, f] of [[H - .31, 1], [-H + .31, -1]]) { merlonRow(me, F, [-halfL + .4, w], [halfL - .4, w], top, { pitch: 1.5, seed: 77 + f, h: 1.15 }); }
  for (const f of [1, -1]) { const w = f * (H - .02); wallQuad(me.s('walLime'), F, -halfL, w, halfL, w, top, top + .3, f ? 0 : 0, f, [1, .97, .94]); }
  // navigation: the two solid wing walls beside the opening; the opening itself is clear
  for (const sg of [-1, 1]) F.navBox(b, sg * (2.2 + halfL) / 2, 0, halfL - 2.2, 2 * H + .3, -60, top);
  F.navFloor(b, 0, 0, 4.4, 2 * H + 1, 0);
}

export function build(b, ctx) {
  setLow(ctx.low);
  b.zone = 'walls';
  ctx.b = b;
  let per = ctx.perimeter.map(p => p.slice());
  let gate = null;
  for (let i = 0; i < per.length && !gate; i++) { const a = per[i], c = per[(i + 1) % per.length], dx = c[0] - a[0], dz = c[1] - a[1], L = hyp(dx, dz), t = ((396 - a[0]) * dx + (208 - a[1]) * dz) / (L * L), gx = a[0] + dx * t, gz = a[1] + dz * t; if (L > 9 && t > 0 && t < 1 && hyp(gx - 396, gz - 208) < 2) { gate = { i, gx, gz, tx: dx / L, tz: dz / L }; per.splice(i + 1, 0, [gx - gate.tx * 4.4, gz - gate.tz * 4.4], [gx + gate.tx * 4.4, gz + gate.tz * 4.4]); } }
  const n = per.length;
  let sideSign = 1;
  { const a = per[40], c = per[41], tx = c[0] - a[0], tz = c[1] - a[1], l = hyp(tx, tz); const nx = -tz / l, nz = tx / l; const mx = (a[0] + c[0]) / 2, mz = (a[1] + c[1]) / 2; sideSign = insidePolygon(mx + nx * 1.5, mz + nz * 1.5, per) ? -1 : 1; }
  // segments that run along a tower footprint are replaced by the tower itself; the wall stops at the tower corner
  const towerPolys = Object.entries(TOWERS).filter(([k]) => k !== 'justicia' && k !== 'bastion').map(([k, p]) => p);
  const onTower = (x, z) => towerPolys.some(p => pointInPoly(x, z, p, .5));
  const fix = p => (hyp(p[0] + 48.08, p[1] - 118.7) < .1 ? [-49.29, 121.88] : p);   // the OSM jog beside the Justicia tower
  const segOk = i => { const a = per[i], c = per[(i + 1) % n], mx = (a[0] + c[0]) / 2, mz = (a[1] + c[1]) / 2; return !(gate && i === gate.i + 1) && !excluded(mx, mz) && hyp(c[0] - a[0], c[1] - a[1]) > .4 && !onTower(mx, mz); };
  let start = 0; for (let i = 0; i < n; i++) if (!segOk(i)) { start = (i + 1) % n; break; }
  const runs = []; let cur = null;
  for (let k = 0; k < n; k++) {
    const i = (start + k) % n, j = (i + 1) % n;
    if (!segOk(i)) { if (cur && cur.length > 1) runs.push(cur); cur = null; continue; }
    if (!cur) cur = [fix(per[i])];
    cur.push(fix(per[j]));
  }
  if (cur && cur.length > 1) runs.push(cur);
  const clean = r => { const o = [r[0]]; for (let i = 1; i < r.length; i++) { const p = o[o.length - 1]; if (hyp(r[i][0] - p[0], r[i][1] - p[1]) > .6) o.push(r[i]); } return o; };
  const me = new Mesher();
  let rIdx = 0;
  const variants = ['walTapial', 'walTapialB', 'walTapialC'], pl = ['walRubble', 'walAshlarGrey', 'walRubble'];
  for (const r0 of runs) {
    const r = clean(r0); if (r.length < 2) continue;
    const parts = []; let acc = [r[0]], len = 0, startIdx = 0;
    for (let i = 1; i < r.length; i++) { acc.push(r[i]); len += hyp(r[i][0] - r[i - 1][0], r[i][1] - r[i - 1][1]); if (len > 100 && i < r.length - 1) { parts.push({ pts: acc, prev: r[startIdx - 1] || null, next: r[i + 1] }); acc = [r[i]]; len = 0; startIdx = i; } }
    parts.push({ pts: acc, prev: r[startIdx - 1] || null, next: null });
    for (const { pts, prev, next } of parts) {
      if (pts.length < 2) continue;
      const seed = (rIdx++) + 1, rr = rnd(seed * 101 + 5), mid = pts[Math.floor(pts.length / 2)];
      b.zone = 'wall-' + Math.floor(mid[0] / 100) + '-' + Math.floor(mid[1] / 100);
      const vi = Math.floor(rr() * 3);
      curtainRun(me, ctx, pts, { side: sideSign, prev, next, top: 6.6, topFn: s => wallTop(s.x, s.z, seed), thick: 1.05, batterFn: s => (hyp(s.x + 38, s.z - 128) < 42 ? .015 : .055), seed, merlons: true, paseo: pts.some(p => p[0] > 154 && p[0] < 190 && p[1] < 20), mats: { body: variants[vi], inner: variants[(vi + 1) % 3], plinth: pl[vi], merlon: 'walLime', cap: 'walLime' } });
      me.flush(b);
    }
  }
  if (gate) { eastGate(b, ctx, me, gate.gx, gate.gz, gate.tx, gate.tz, sideSign); me.flush(b); }
  buildTowers(b, ctx, me);
}
