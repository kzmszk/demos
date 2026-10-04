// Facades: walls with openings, Istrian-stone frames, sills, shutters, glass, doors, balconies, cornices,
// string courses and downpipes, generated from the compact records written by tools/pack.py.
// Lighting comes from a per-tile lightmap atlas built from the baked facade grids (uv1).
import * as THREE from 'three/webgpu';
import { Geo } from './geo.js';

const F = { p0x: 0, p0y: 1, p1x: 2, p1y: 3, nx: 4, ny: 5, zb: 6, zt: 7, zg: 8, L: 9, u0: 10, cls: 11, mat: 12, tint: 13, dec: 14, sh: 15, st: 16, seed: 17, base: 18, bands: 19, cor: 20, g: 21, go: 22, open: 23 };
const T = { R: 1, A: 2, G: 3, S: 4, D: 5, DA: 6, WG: 7, P: 8, PA: 9, SH: 10, GR: 11 };
const ARCHED = new Set([T.A, T.DA, T.WG, T.PA]);
const GOTHIC = new Set([T.G, T.P]);
const WINDOWS = new Set([T.R, T.A, T.G, T.S, T.P, T.PA, T.GR]);

export function hash(a, b = 0, c = 0) {
  let h = (a * 374761393 + b * 668265263 + c * 2147483647) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

// ------------------------------------------------------------------ lightmap pool (shared array texture)
export const LM = 512;
export class LightmapPool {
  constructor(n = 40) {
    this.n = n; this.free = Array.from({ length: n }, (_, i) => i);
    const mk = () => {
      const t = new THREE.DataArrayTexture(new Uint8Array(LM * LM * 4 * n), LM, LM, n);
      t.format = THREE.RGBAFormat; t.type = THREE.UnsignedByteType; t.colorSpace = THREE.NoColorSpace;
      t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; t.needsUpdate = true;
      return t;
    };
    this.day = mk(); this.night = mk();
  }
  alloc(k) { return this.free.length >= k ? this.free.splice(0, k) : null; }
  release(slots) { for (const s of slots) this.free.push(s); }
  write(slots, pages, which) {
    const t = this[which];
    pages.forEach((data, i) => { t.image.data.set(data, slots[i] * LM * LM * 4); t.addLayerUpdate(slots[i]); });
    t.needsUpdate = true;
  }
}

// group facades into square chunks (by midpoint) for per-chunk detail switching
export function chunkFacades(meta, size = 50) {
  const bb = meta.bbox, fac = meta.fac, map = new Map();
  for (let i = 0; i < fac.length; i++) {
    const f = fac[i]; const mx = (f[F.p0x] + f[F.p1x]) / 2, my = (f[F.p0y] + f[F.p1y]) / 2;
    const cx = Math.max(0, Math.min(Math.floor((bb[2] - bb[0]) / size) - 1, Math.floor((mx - bb[0]) / size)));
    const cy = Math.max(0, Math.min(Math.floor((bb[3] - bb[1]) / size) - 1, Math.floor((my - bb[1]) / size)));
    const k = cy * 64 + cx;
    if (!map.has(k)) map.set(k, { list: [], bbox: [Infinity, Infinity, -Infinity, -Infinity] });
    const c = map.get(k); c.list.push(i);
    c.bbox[0] = Math.min(c.bbox[0], f[F.p0x], f[F.p1x]); c.bbox[1] = Math.min(c.bbox[1], f[F.p0y], f[F.p1y]);
    c.bbox[2] = Math.max(c.bbox[2], f[F.p0x], f[F.p1x]); c.bbox[3] = Math.max(c.bbox[3], f[F.p0y], f[F.p1y]);
  }
  return [...map.values()];
}

// shelf-pack the facade grids into LMxLM pages; returns {rects:[[page,x,y]], pages}
export function packAtlas(fac) {
  const rects = new Array(fac.length);
  const order = fac.map((f, i) => i).sort((a, b) => fac[b][F.g][1] - fac[a][F.g][1]);
  let page = 0, x = 0, y = 0, rowH = 0;
  for (const i of order) {
    const [nu, nz] = fac[i][F.g]; const w = Math.min(LM, nu + 2), h = Math.min(LM, nz + 2);
    if (x + w > LM) { x = 0; y += rowH; rowH = 0; }
    if (y + h > LM) { page++; x = 0; y = 0; rowH = 0; }
    rects[i] = [page, x, y]; x += w; rowH = Math.max(rowH, h);
  }
  return { rects, pages: page + 1 };
}

export function fillAtlas(fac, rects, npages, src) {
  const pages = Array.from({ length: npages }, () => new Uint8Array(LM * LM * 4));
  if (!src) return pages;
  for (let i = 0; i < fac.length; i++) {
    const [nu, nz] = fac[i][F.g]; const go = fac[i][F.go]; const [pg, rx, ry] = rects[i]; const data = pages[pg];
    for (let j = -1; j <= nz; j++) {
      const jj = Math.min(nz - 1, Math.max(0, j)); const yy = ry + 1 + j; if (yy < 0 || yy >= LM) continue;
      for (let k = -1; k <= nu; k++) {
        const kk = Math.min(nu - 1, Math.max(0, k)); const xx = rx + 1 + k; if (xx < 0 || xx >= LM) continue;
        const s = (go + jj * nu + kk) * 4, d = (yy * LM + xx) * 4;
        data[d] = src[s]; data[d + 1] = src[s + 1]; data[d + 2] = src[s + 2]; data[d + 3] = src[s + 3];
      }
    }
  }
  return pages;
}

// ------------------------------------------------------------------ shapes in facade space (u, z), CCW
function arcPts(cu, cz, r, a0, a1, k) {
  const out = [];
  for (let i = 0; i <= k; i++) { const a = a0 + (a1 - a0) * i / k; out.push([cu + Math.cos(a) * r, cz + Math.sin(a) * r]); }
  return out;
}
function bez(p0, p1, p2, p3, k) {
  const out = [];
  for (let i = 1; i <= k; i++) {
    const t = i / k, s = 1 - t;
    out.push([s * s * s * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t * t * t * p3[0], s * s * s * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t * t * t * p3[1]]);
  }
  return out;
}
// springing height (top of the straight jambs)
function spring(t, z, w, h) {
  if (ARCHED.has(t)) return z + h - w / 2;
  if (GOTHIC.has(t)) return z + h - 0.95 * w;
  return z + h;
}
export function outline(t, u, z, w, h, grow = 0) {
  const hw = w / 2 + grow, zz = z - (grow > 0 ? grow * 0.6 : 0);
  if (ARCHED.has(t)) {
    const zs = z + h - w / 2;
    return [[u - hw, zz], [u + hw, zz], ...arcPts(u, zs, hw, 0, Math.PI, 14)];
  }
  if (GOTHIC.has(t)) {
    const zs = z + h - 0.95 * w, apex = z + h + grow * 1.2;
    const right = bez([u + hw, zs], [u + hw, zs + 0.55 * w], [u + 0.02 * w, apex - 0.42 * w], [u, apex], 9);
    const left = bez([u, apex], [u - 0.02 * w, apex - 0.42 * w], [u - hw, zs + 0.55 * w], [u - hw, zs], 9);
    return [[u - hw, zz], [u + hw, zz], [u + hw, zs], ...right, ...left];
  }
  return [[u - hw, zz], [u + hw, zz], [u + hw, z + h + grow], [u - hw, z + h + grow]];
}

// ------------------------------------------------------------------ builder
export class FacadeBuilder {
  constructor(mats, atlas) {
    this.M = {}; for (const m of mats) this.M[m.name] = m.id;
    this.atlas = atlas;          // {rects, slots}  (null for the far LOD: vertex-lit from the grid)
    this.g = new Geo(1 << 16);
  }
  begin(f, fi) {
    const L = f[F.L];
    const dx = (f[F.p1x] - f[F.p0x]) / L, dy = (f[F.p1y] - f[F.p0y]) / L;
    this.f = f; this.fi = fi; this.L = L;
    this.ox = f[F.p0x]; this.oy = f[F.p0y]; this.dx = dx; this.dy = dy; this.nx = f[F.nx]; this.ny = f[F.ny];
    const [nu, nz, zs] = f[F.g]; this.nu = nu; this.nz = nz; this.zs = zs; this.zt = f[F.zt];
    if (this.atlas) { const [pg, rx, ry] = this.atlas.rects[fi]; this.rx = rx; this.ry = ry; this.layer = this.atlas.slots[pg]; }
    this.u0 = f[F.u0];
    const tint = f[F.tint], sh = f[F.sh];
    const seed = Math.round(f[F.seed] * 255);
    this.wallS = { n: [this.nx, this.ny, 0], t: [dx, dy, 0, 1], c0: [tint[0], tint[1], tint[2], Math.round(f[F.dec] * 255)], c1: [f[F.mat], 0, seed, 0], base: f[F.base] ?? -100, ao: 1 };
    this.stoneS = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.trim, 0, seed, 0], base: -100 };
    this.shutS = { ...this.wallS, c0: [sh[0], sh[1], sh[2], 0], c1: [this.M.wood_paint, 0, seed, 1] };
    this.doorS = { ...this.wallS, c0: [92, 62, 40, 0], c1: [this.M.wood_paint, 0, seed, 2] };
    this.glassS = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.glass, 0, seed, 0], base: -100 };
    this.glassLitS = { ...this.glassS, c1: [this.M.glass, 0, seed, 200] };
    this.ironS = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.metal, 0, seed, 0], base: -100 };
    this.darkS = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.dark, 0, seed, 0], base: -100 };
    this.woodS = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.wood_raw, 0, seed, 0], base: -100 };
  }
  // facade-local (u along, z up, w outward) -> world
  P(u, z, w) { return [this.ox + this.dx * u + this.nx * w, this.oy + this.dy * u + this.ny * w, z]; }
  lm(u, z) {
    const fu = Math.min(1, Math.max(0, u / this.L)); const fz = Math.min(1, Math.max(0, (z - this.zs) / Math.max(0.01, this.zt - this.zs)));
    return [(this.rx + 1 + fu * (this.nu - 1) + 0.5) / LM, (this.ry + 1 + fz * (this.nz - 1) + 0.5) / LM, this.layer];
  }
  // vertex at facade-local coords with explicit normal/tangent (world) and uv
  V(u, z, w, uvx, uvy, s, n, t, ao) {
    const p = this.P(u, z, w), l = this.lm(u, z);
    const st = (n || t || ao !== undefined) ? { ...s, n: n || s.n, t: t || s.t, ao: ao ?? s.ao } : s;
    return this.g.v(p[0], p[1], p[2], uvx, uvy, l[0], l[1], l[2], st);
  }
  // world dirs for facade-local axes
  get Dn() { return [this.nx, this.ny, 0]; }
  get Du() { return [this.dx, this.dy, 0]; }
  // planar polygon facing outward (+w) at depth w: pts [[u,z]...] CCW (seen from outside), holes optional
  planar(pts, holes, w, s, ao) {
    const contour = pts.map((p) => new THREE.Vector2(p[0], p[1]));
    const hs = (holes || []).map((h) => h.map((p) => new THREE.Vector2(p[0], p[1])));
    const tris = THREE.ShapeUtils.triangulateShape(contour, hs);
    const all = [...pts, ...(holes || []).flat()];
    const base = this.g.n;
    for (const p of all) this.V(p[0], p[1], w, this.u0 + p[0], p[1], s, null, null, ao);
    for (const t of tris) {
      const a = all[t[0]], b = all[t[1]], c = all[t[2]];
      const cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      if (cr >= 0) this.g.tri(base + t[0], base + t[1], base + t[2]); else this.g.tri(base + t[0], base + t[2], base + t[1]);
    }
  }
  // a strip of quads along a polyline (u,z) extruded between depths w0 (front) and w1 (back); normals point
  // to the left of the direction of travel (inward for a CCW hole outline -> faces the opening axis)
  extrude(pts, w0, w1, s, closed, ao0 = 1, ao1 = 1, flipN = false) {
    const n = pts.length; const segs = closed ? n : n - 1;
    let acc = 0;
    for (let i = 0; i < segs; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      const du = b[0] - a[0], dz = b[1] - a[1]; const len = Math.hypot(du, dz); if (len < 1e-4) continue;
      // in facade plane the left normal of (du,dz) is (-dz, du); for a CCW outline that points inward (into the hole)
      let nu = -dz / len, nzz = du / len; if (flipN) { nu = -nu; nzz = -nzz; }
      const nw = [this.dx * nu, this.dy * nu, nzz];
      const tw = [this.nx, this.ny, 0, 1];
      const v0 = this.V(a[0], a[1], w0, acc, w0, s, nw, tw, ao0), v1 = this.V(b[0], b[1], w0, acc + len, w0, s, nw, tw, ao0);
      const v2 = this.V(b[0], b[1], w1, acc + len, w1, s, nw, tw, ao1), v3 = this.V(a[0], a[1], w1, acc, w1, s, nw, tw, ao1);
      if (flipN) this.g.quad(v0, v3, v2, v1); else this.g.quad(v0, v1, v2, v3);
      acc += len;
    }
  }
  // axis-aligned box in facade space: u0..u1, z0..z1, w0..w1 (w outward); all 6 faces unless skip
  box(u0, u1, z0, z1, w0, w1, s, skip = '', ao = 1) {
    const Du = this.Du, Dn = this.Dn;
    const faces = [
      ['f', [[u0, z0, w1], [u1, z0, w1], [u1, z1, w1], [u0, z1, w1]], Dn, [...Du, 1]],
      ['b', [[u1, z0, w0], [u0, z0, w0], [u0, z1, w0], [u1, z1, w0]], Dn.map((v) => -v), [...Du.map((v) => -v), 1]],
      ['t', [[u0, z1, w1], [u1, z1, w1], [u1, z1, w0], [u0, z1, w0]], [0, 0, 1], [...Du, 1]],
      ['d', [[u0, z0, w0], [u1, z0, w0], [u1, z0, w1], [u0, z0, w1]], [0, 0, -1], [...Du, 1]],
      ['l', [[u0, z0, w0], [u0, z0, w1], [u0, z1, w1], [u0, z1, w0]], Du.map((v) => -v), [...Dn, 1]],
      ['r', [[u1, z0, w1], [u1, z0, w0], [u1, z1, w0], [u1, z1, w1]], Du, [...Dn.map((v) => -v), 1]],
    ];
    for (const [k, q, n, t] of faces) {
      if (skip.includes(k)) continue;
      const ids = q.map((p, i) => {
        const uvx = k === 'l' || k === 'r' ? p[2] : this.u0 + p[0];
        const uvy = k === 't' || k === 'd' ? p[2] : p[1];
        return this.V(p[0], p[1], p[2], uvx, uvy, s, n, t, ao);
      });
      this.g.quad(ids[0], ids[1], ids[2], ids[3]);
    }
  }
  // vertical cylinder (downpipe) at facade u, offset w
  pipe(u, w, z0, z1, r, s) {
    const k = 6; const base = this.g.n;
    for (let i = 0; i <= k; i++) {
      const a = i / k * Math.PI * 2; const cu = Math.cos(a) * r, cw = Math.sin(a) * r;
      const n = [this.dx * Math.cos(a) + this.nx * Math.sin(a), this.dy * Math.cos(a) + this.ny * Math.sin(a), 0];
      const t = [0, 0, 1, 1];
      this.V(u + cu, z0, w + cw, i / k * 0.3, z0, s, n, t); this.V(u + cu, z1, w + cw, i / k * 0.3, z1, s, n, t);
    }
    for (let i = 0; i < k; i++) { const a = base + i * 2; this.g.quad(a, a + 2, a + 3, a + 1); }
  }

  // ---------------------------------------------------------------- one facade
  facade(f, fi, near) {
    this.begin(f, fi);
    const L = this.L, zb = f[F.zb], zt = f[F.zt];
    const ops = near ? f[F.open] : [];
    const holes = [];
    for (const o of ops) {
      const [t, u, z, w, h] = o;
      if (u - w / 2 < 0.05 || u + w / 2 > L - 0.05 || z < zb || z + h > zt - 0.1) continue;
      holes.push(outline(t, u, z, w, h));
    }
    // wall (with holes when near)
    const wall = [[0, zb], [L, zb], [L, zt], [0, zt]];
    this.planar(wall, holes, 0, this.wallS);
    if (!near) { this.farOpenings(f); return; }
    for (const o of ops) this.opening(o, f);
    this.trims(f);
  }

  farOpenings(f) {
    for (const o of f[F.open]) {
      const [t, u, z, w, h, fl] = o;
      if (u - w / 2 < 0.05 || u + w / 2 > this.L - 0.05) continue;
      const sh = fl & 3; const pts = outline(t, u, z, w, h);
      const s = (WINDOWS.has(t) && (sh === 2)) ? this.shutS : (t === T.D || t === T.DA) ? this.doorS : this.glassS;
      this.planar(pts, null, 0.015, { ...s, ao: 0.8 });
    }
  }

  opening(o, f) {
    const [t, u, z, w, h, fl] = o;
    const isWin = WINDOWS.has(t), framed = (fl & 16) !== 0;
    const D = t === T.WG ? 0.55 : (t === T.D || t === T.DA || t === T.SH) ? 0.3 : 0.24;
    const fp = framed ? 0.035 : 0;
    const pts = outline(t, u, z, w, h);
    const zs = spring(t, z, w, h);
    // reveal (jambs + head + sill surface) — inward-facing quads from the wall face to the infill
    const revS = framed ? this.stoneS : this.wallS;
    this.extrude(pts, fp, -D, revS, true, 0.85, 0.45);
    // stone frame ring
    if (framed) {
      const fw = isWin ? 0.13 : 0.18;
      const outer = outline(t, u, z, w, h, fw);
      this.planar(outer, [pts], fp, this.stoneS, 0.95);
      this.extrude(outer, 0, fp, this.stoneS, true, 0.9, 0.9, true);
    }
    // sill
    if (isWin && t !== T.GR) this.box(u - w / 2 - 0.08, u + w / 2 + 0.08, z - 0.09, z, -0.02, 0.09, this.stoneS, 'b', 0.95);
    // infill (glass carries the 'lit at night' flag of the opening)
    const back = -D + 0.05;
    if (isWin) {
      this.planar(pts, null, back, (fl & 128) ? this.glassLitS : this.glassS, 0.6);
      // window frame bars: mullion + transom
      const bw = 0.05, bd = 0.04;
      this.box(u - w / 2, u + w / 2, z, z + bw, back, back + bd, this.woodS, 'b', 0.6);
      if (w > 0.6) this.box(u - bw / 2, u + bw / 2, z, zs, back, back + bd, this.woodS, 'b', 0.6);
      const tz = ARCHED.has(t) || GOTHIC.has(t) ? zs : z + (zs - z) * 0.72;
      this.box(u - w / 2, u + w / 2, tz - bw / 2, tz + bw / 2, back, back + bd, this.woodS, 'b', 0.6);
      this.box(u - w / 2, u - w / 2 + bw, z, zs, back, back + bd, this.woodS, 'b', 0.6);
      this.box(u + w / 2 - bw, u + w / 2, z, zs, back, back + bd, this.woodS, 'b', 0.6);
      // shutters (persiane)
      const sh = fl & 3;
      if (sh === 1 || sh === 3) {           // open: folded against the wall either side
        const hw = w / 2, zz0 = z, zz1 = zs;
        const left = sh === 1 || hash(this.fi, Math.round(u * 10)) < 0.5;
        if (left) this.box(u - w / 2 - hw - 0.02 - fp, u - w / 2 - 0.02 - fp, zz0, zz1, fp + 0.005, fp + 0.035, this.shutS, 'b', 0.95);
        this.box(u + w / 2 + 0.02 + fp, u + w / 2 + hw + 0.02 + fp, zz0, zz1, fp + 0.005, fp + 0.035, this.shutS, 'b', 0.95);
        if (sh === 3 && !left) this.box(u - w / 2, u, z, zs, -0.07, -0.04, this.shutS, 'b', 0.7);
      } else if (sh === 2) {                 // closed in the opening
        this.box(u - w / 2, u, z, zs, -0.08, -0.05, this.shutS, 'b', 0.75);
        this.box(u, u + w / 2, z, zs, -0.08, -0.05, this.shutS, 'b', 0.75);
      }
      if (t === T.GR) for (let k = 1; k * 0.12 < w; k++) this.box(u - w / 2 + k * 0.12 - 0.008, u - w / 2 + k * 0.12 + 0.008, z, zs, -0.06, -0.044, this.ironS, 'b', 0.7);
      // balconies
      const bal = (fl >> 2) & 3;
      if (bal === 1) this.ironBalcony(u, z, w, f);
      else if (bal === 2) { const m = (fl >> 8) & 15; this.stoneBalcony(u, z, w, m, f); }
      if (fl & 64) this.flowerBox(u, z, w);
    } else if (t === T.D || t === T.DA) {
      this.planar(pts, null, back, this.doorS, 0.55);
      if (t === T.DA) this.box(u - w / 2, u + w / 2, zs - 0.04, zs + 0.04, back, back + 0.05, this.woodS, 'b', 0.6);
      this.box(u - 0.02, u + 0.02, z, zs, back, back + 0.03, this.woodS, 'b', 0.55);
    } else if (t === T.SH) {
      this.planar(pts, null, back, this.glassS, 0.7);
      this.box(u - w / 2, u + w / 2, z, z + 0.45, back, back + 0.08, this.woodS, 'b', 0.6);
      this.box(u - w / 2, u + w / 2, z + h - 0.06, z + h, back, back + 0.06, this.woodS, 'b', 0.6);
    } else if (t === T.WG) {
      this.planar(pts, null, back, this.darkS, 0.3);
      // two stone steps down to the water inside the gate
      this.box(u - w / 2, u + w / 2, 0.1, 0.45, -D + 0.05, -D + 0.3, this.stoneS, 'b', 0.5);
      this.box(u - w / 2, u + w / 2, -0.3, 0.1, -D + 0.05, -0.02, this.stoneS, 'b', 0.5);
      // wooden gate leaves half open
      this.box(u - w / 2 + 0.02, u - 0.02, z, zs, -D + 0.06, -D + 0.1, this.woodS, 'b', 0.4);
    }
  }

  ironBalcony(u, z, w, f) {
    const u0 = u - w / 2 - 0.25, u1 = u + w / 2 + 0.25, d = 0.5;
    this.box(u0, u1, z - 0.14, z - 0.02, 0, d, this.stoneS, 'b', 0.9);
    const rz = z + 0.95;
    this.box(u0, u1, rz - 0.03, rz, d - 0.04, d, this.ironS, 'b');
    this.box(u0, u0 + 0.03, rz - 0.03, rz, 0, d, this.ironS, 'b'); this.box(u1 - 0.03, u1, rz - 0.03, rz, 0, d, this.ironS, 'b');
    for (let x = u0 + 0.02; x < u1; x += 0.11) this.box(x - 0.008, x + 0.008, z - 0.02, rz - 0.03, d - 0.03, d - 0.014, this.ironS, 'b');
    for (const x of [u0, u1]) for (let y = 0.1; y < d; y += 0.11) this.box(x - 0.008, x + 0.008, z - 0.02, rz - 0.03, y - 0.008, y + 0.008, this.ironS, 'b');
  }

  stoneBalcony(u, z, w, m, f) {
    const gap = 0.24; const W = m * w + (m - 1) * gap;
    const u0 = u - w / 2 - 0.3, u1 = u0 + W + 0.6, d = 0.55;
    this.box(u0, u1, z - 0.42, z - 0.25, 0, d, this.stoneS, 'b', 0.9);
    this.box(u0 - 0.02, u1 + 0.02, z + 0.68, z + 0.8, d - 0.16, d + 0.02, this.stoneS, 'b', 0.95);
    for (let x = u0 + 0.12; x < u1 - 0.05; x += 0.16) this.box(x - 0.045, x + 0.045, z - 0.25, z + 0.68, d - 0.12, d - 0.03, this.stoneS, 'b', 0.85);
    for (const x of [u0 + 0.04, u1 - 0.04]) this.box(x - 0.06, x + 0.06, z - 0.25, z + 0.68, 0, d, this.stoneS, 'b', 0.85);
  }

  flowerBox(u, z, w) {
    const s = { ...this.wallS, c0: [150, 70, 45, 0], c1: [this.M.wood_paint, 0, this.wallS.c1[2], 3] };
    this.box(u - w / 2 + 0.05, u + w / 2 - 0.05, z + 0.01, z + 0.17, 0.0, 0.16, s, 'b', 0.9);
    const leaf = { ...this.wallS, c0: [52, 96, 36, 0], c1: [this.M.wood_paint, 0, this.wallS.c1[2], 4] };
    this.box(u - w / 2 + 0.07, u + w / 2 - 0.07, z + 0.17, z + 0.33, 0.01, 0.17, leaf, 'b', 0.8);
    const red = { ...this.wallS, c0: [196, 38, 40, 0], c1: [this.M.wood_paint, 0, this.wallS.c1[2], 5] };
    for (let x = u - w / 2 + 0.14; x < u + w / 2 - 0.1; x += 0.13) this.box(x - 0.035, x + 0.035, z + 0.3, z + 0.37, 0.05 + 0.04 * hash(this.fi, x * 100), 0.12, red, 'b', 0.9);
  }

  trims(f) {
    const L = this.L, zt = f[F.zt], zg = f[F.zg];
    // cornice under the eave
    const S = this.stoneS;
    if (f[F.cor] === 1) {
      this.box(0, L, zt - 0.62, zt - 0.52, 0, 0.08, S, 'bl r', 0.9);
      this.box(0, L, zt - 0.52, zt - 0.40, 0, 0.16, S, 'bl r', 0.85);
      for (let x = 0.12; x < L - 0.1; x += 0.24) this.box(x - 0.06, x + 0.06, zt - 0.40, zt - 0.30, 0.0, 0.18, S, 'b', 0.8);
    } else {
      const brick = { ...this.wallS, c0: [255, 255, 255, 0], c1: [this.M.wall_brick, 0, this.wallS.c1[2], 0], base: -100 };
      this.box(0, L, zt - 0.42, zt - 0.34, 0, 0.06, brick, 'blr', 0.85);
      for (let x = 0.07; x < L - 0.05; x += 0.16) this.box(x - 0.05, x + 0.05, zt - 0.34, zt - 0.28, 0, 0.1, brick, 'b', 0.8);
    }
    for (const z of f[F.bands] || []) this.box(0, L, z - 0.07, z + 0.05, 0, 0.05, S, 'blr', 0.9);
    // downpipe at one end
    if (L > 5 && f[F.cls] !== 0) {
      const u = hash(this.fi, 3) < 0.5 ? 0.35 : L - 0.35;
      const pipe = { ...this.ironS, c0: [255, 255, 255, 0], c1: [this.M.metal, 0, this.wallS.c1[2], 1] };
      this.pipe(u, 0.11, Math.max(zg, 0.4), zt - 0.3, 0.05, pipe);
    }
  }
}

export function buildNearFacades(meta, atlas, mats, material, list = null) {
  const fb = new FacadeBuilder(mats, atlas);
  const fac = meta.fac;
  for (const i of (list || fac.keys())) fb.facade(fac[i], i, true);
  const mesh = new THREE.Mesh(fb.g.build(true), material);
  mesh.castShadow = true; mesh.receiveShadow = true;
  return mesh;
}

// far LOD: the baked grid itself as a vertex-lit wall + flat window/door panels
export function buildFarFacades(meta, girr, girrn, mats, list = null) {
  const M = {}; for (const m of mats) M[m.name] = m.id;
  const fac = list ? list.map((i) => meta.fac[i]) : meta.fac;
  // the 1 m bake grid decimated to ~3 m (the lightmap atlas keeps full resolution for the near LOD)
  const pick = (n) => { const a = []; for (let i = 0; i < n - 1; i += 3) a.push(i); a.push(n - 1); return a; };
  let nv = 0, ni = 0;
  for (const f of fac) { const [nu, nz] = f[F.g]; const cu = pick(nu).length, cz = pick(nz).length; nv += cu * cz + 4 * f[F.open].length; ni += (cu - 1) * (cz - 1) * 6 + 6 * f[F.open].length; }
  const P = new Float32Array(nv * 3), N = new Int8Array(nv * 4), Tg = new Int8Array(nv * 4), U = new Float32Array(nv * 2), C0 = new Uint8Array(nv * 4), C1 = new Uint8Array(nv * 4), IR = new Uint8Array(nv * 4), IRN = new Uint8Array(nv * 4);
  const I = nv > 65535 ? new Uint32Array(ni) : new Uint16Array(ni);
  let v = 0, k = 0;
  const put = (x, y, z, u, w, nx, ny, dx, dy, c0, c1, gi) => {
    P[v * 3] = x; P[v * 3 + 1] = y; P[v * 3 + 2] = z; N[v * 4] = nx * 127; N[v * 4 + 1] = ny * 127; N[v * 4 + 3] = 127;
    Tg[v * 4] = dx * 127; Tg[v * 4 + 1] = dy * 127; Tg[v * 4 + 3] = 127; U[v * 2] = u; U[v * 2 + 1] = w;
    C0.set(c0, v * 4); C1.set(c1, v * 4);
    if (girr) { IR[v * 4] = girr[gi * 4]; IR[v * 4 + 1] = girr[gi * 4 + 1]; IR[v * 4 + 2] = girr[gi * 4 + 2]; IR[v * 4 + 3] = girr[gi * 4 + 3]; }
    if (girrn) { IRN[v * 4] = girrn[gi * 4]; IRN[v * 4 + 1] = girrn[gi * 4 + 1]; IRN[v * 4 + 2] = girrn[gi * 4 + 2]; IRN[v * 4 + 3] = girrn[gi * 4 + 3]; }
    return v++;
  };
  for (let fi = 0; fi < fac.length; fi++) {
    const f = fac[fi]; const [nu, nz, zs] = f[F.g]; const go = f[F.go]; const L = f[F.L];
    if (L < 0.05) continue;
    const dx = (f[F.p1x] - f[F.p0x]) / L, dy = (f[F.p1y] - f[F.p0y]) / L, nx = f[F.nx], ny = f[F.ny];
    const tint = f[F.tint]; const seed = Math.round(f[F.seed] * 255);
    const c0 = [tint[0], tint[1], tint[2], Math.round(f[F.dec] * 255)], c1 = [f[F.mat], 0, seed, 0];
    const zb = f[F.zb], zt = f[F.zt];
    const base = v;
    const cols = pick(nu), rows = pick(nz), cu = cols.length;
    for (const j of rows) {
      let z = zs + (zt - zs) * j / (nz - 1); if (j === 0) z = zb;
      for (const i of cols) {
        const u = L * i / (nu - 1);
        put(f[F.p0x] + dx * u, f[F.p0y] + dy * u, z, f[F.u0] + u, z, nx, ny, dx, dy, c0, c1, go + j * nu + i);
      }
    }
    for (let j = 0; j < rows.length - 1; j++) for (let i = 0; i < cu - 1; i++) {
      const a = base + j * cu + i; I[k++] = a; I[k++] = a + 1; I[k++] = a + cu + 1; I[k++] = a; I[k++] = a + cu + 1; I[k++] = a + cu;
    }
    for (const o of f[F.open]) {
      const [t, u, z, w, h, fl] = o;
      const isWin = WINDOWS.has(t), sh = fl & 3;
      const mat = (isWin && sh === 2) ? M.wood_paint : (t === T.D || t === T.DA) ? M.wood_paint : M.glass;
      const cc0 = mat === M.wood_paint ? (t === T.D || t === T.DA ? [92, 62, 40, 0] : [...f[F.sh], 0]) : [255, 255, 255, 0];
      const cc1 = [mat, 0, seed, ((fl & 128) && mat === M.glass) ? 200 : 0];
      const fu = Math.min(1, Math.max(0, u / L)), fz = Math.min(1, Math.max(0, (z + h / 2 - zs) / Math.max(0.01, zt - zs)));
      const gi = go + Math.round(fz * (nz - 1)) * nu + Math.round(fu * (nu - 1));
      const o2 = 0.02, u0 = u - w / 2, u1 = u + w / 2, z1 = z + h;
      const q = [[u0, z], [u1, z], [u1, z1], [u0, z1]].map(([uu, zz]) => put(f[F.p0x] + dx * uu + nx * o2, f[F.p0y] + dy * uu + ny * o2, zz, uu, zz, nx, ny, dx, dy, cc0, cc1, gi));
      I[k++] = q[0]; I[k++] = q[1]; I[k++] = q[2]; I[k++] = q[0]; I[k++] = q[2]; I[k++] = q[3];
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(P, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(N, 4, true));
  g.setAttribute('tangent', new THREE.BufferAttribute(Tg, 4, true));
  g.setAttribute('uv', new THREE.BufferAttribute(U, 2));
  g.setAttribute('c0', new THREE.BufferAttribute(C0, 4, true));
  g.setAttribute('c1', new THREE.BufferAttribute(C1, 4, true));
  g.setAttribute('irr', new THREE.BufferAttribute(IR, 4, true));
  g.setAttribute('irrn', new THREE.BufferAttribute(IRN, 4, true));
  g.setIndex(new THREE.BufferAttribute(I, 1));
  g.computeBoundingBox(); g.computeBoundingSphere();
  return g;
}
