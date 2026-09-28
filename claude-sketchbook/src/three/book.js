// The book: two boards on hinges, five leaves that really bend, a cloth spine, an elastic band, a pen loop.
import * as THREE from 'three';

export const PW = 14.8, PH = 21.0;           // page (cm)
export const CW = 15.3, CH = 21.6, CT = 0.26; // cover boards
export const LT = 0.034, NL = 5;               // leaves
export const T = 2 * CT + NL * LT + 0.03;      // closed thickness
export const HY = T / 2;                       // hinge height
export const INSET = 0.3;                      // gap between spine line and board edge
const ROOT_Y = CT * 0.6;
const GUT = 1.9;
const NU = 44, NV = 22;

const smooth = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

export class Leaf {
  constructor(i, frontTex, backTex, opts = {}) {
    this.i = i;
    this.hR = CT + (NL - 1 - i) * LT + 0.014;
    this.hL = CT + i * LT + 0.014;
    this.rootX = (i - 2) * 0.004;
    this.rootY = ROOT_Y;
    this.p = -1;
    this.shift = opts.shift || 0; // the taped-back leaf sits a little crooked
    this.rot = opts.rot || 0;
    const nVert = (NU + 1) * (NV + 1);
    const pos = new Float32Array(nVert * 3);
    const uvF = new Float32Array(nVert * 2), uvB = new Float32Array(nVert * 2);
    for (let j = 0; j <= NV; j++) for (let k = 0; k <= NU; k++) {
      const n = j * (NU + 1) + k;
      uvF[n * 2] = k / NU; uvF[n * 2 + 1] = 1 - j / NV;
      uvB[n * 2] = 1 - k / NU; uvB[n * 2 + 1] = 1 - j / NV;
    }
    const idx = [];
    for (let j = 0; j < NV; j++) for (let k = 0; k < NU; k++) {
      const a = j * (NU + 1) + k, b = a + 1, c = a + NU + 1, d = c + 1;
      idx.push(a, c, b, c, d, b);
    }
    this.posAttr = new THREE.BufferAttribute(pos, 3);
    this.posAttr.setUsage(THREE.DynamicDrawUsage);
    this.geoF = new THREE.BufferGeometry();
    this.geoF.setAttribute('position', this.posAttr);
    this.geoF.setAttribute('uv', new THREE.BufferAttribute(uvF, 2));
    this.geoF.setIndex(idx);
    this.geoB = new THREE.BufferGeometry();
    this.geoB.setAttribute('position', this.posAttr);
    this.geoB.setAttribute('uv', new THREE.BufferAttribute(uvB, 2));
    this.geoB.setIndex(idx);
    const common = { roughness: 0.93, metalness: 0 };
    this.matF = new THREE.MeshStandardMaterial({ map: frontTex, side: THREE.FrontSide, ...common });
    this.matB = new THREE.MeshStandardMaterial({ map: backTex, side: THREE.BackSide, ...common });
    if (opts.alphaF) {
      this.matF.alphaMap = opts.alphaF; this.matF.alphaTest = 0.5;
      this.matB.alphaMap = opts.alphaB; this.matB.alphaTest = 0.5;
    }
    this.front = new THREE.Mesh(this.geoF, this.matF);
    this.back = new THREE.Mesh(this.geoB, this.matB);
    for (const m of [this.front, this.back]) { m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false; }
    this.group = new THREE.Group();
    this.group.add(this.front, this.back);
    this.set(0, 0.35, 0.2, 0);
  }
  // p: 0 on the right … 1 on the left. lead: how far the free edge runs ahead. corner: diagonal curl.
  set(p, lead = 0.35, corner = 0.2, flutter = 0) {
    const key = p.toFixed(5) + lead + corner + flutter.toFixed(4);
    if (key === this.key) return false;
    this.key = key;
    this.p = p;
    const pos = this.posAttr.array;
    const aR = (3 * (this.hR - this.rootY)) / GUT, aL = (3 * (this.hL - this.rootY)) / GUT;
    const s1 = Math.sin(Math.PI * Math.min(1, Math.max(0, p)));
    const ds = PW / NU;
    for (let j = 0; j <= NV; j++) {
      const vn = j / NV - 0.5;
      let x = this.rootX, y = this.rootY;
      let prevPhi = null;
      for (let k = 0; k <= NU; k++) {
        const s = k * ds, sn = s / PW;
        const gw = s < GUT ? (1 - s / GUT) ** 2 : 0;
        const phiR = aR * gw, phiL = Math.PI - aL * gw;
        let pe = p + lead * s1 * (sn - 0.28) + corner * s1 * sn * vn * 2 + flutter * s1 * Math.sin(sn * 5 + vn * 2);
        const m = smooth(pe);
        let phi = phiR + (phiL - phiR) * m;
        // paper sags a little in the air, most at the free edge
        phi -= 0.12 * s1 * sn * sn * Math.cos(phi);
        if (k > 0) {
          const ph = (phi + prevPhi) / 2;
          x += Math.cos(ph) * ds;
          y += Math.sin(ph) * ds;
        }
        prevPhi = phi;
        const n = (j * (NU + 1) + k) * 3;
        // taped back a little crooked: the free part is skewed in the page plane
        const zz = vn * PH + this.shift + this.rot * Math.max(0, s - 1.3);
        pos[n] = x; pos[n + 1] = y; pos[n + 2] = zz;
      }
    }
    this.posAttr.needsUpdate = true;
    this.geoF.computeVertexNormals();
    this.geoB.attributes.normal = this.geoF.attributes.normal;
    this.geoF.computeBoundingSphere();
    this.geoB.boundingSphere = this.geoF.boundingSphere;
    this.geoB.boundingBox = null;
    return true;
  }
  // page point (mm on the page image) → world position, for a leaf lying flat on either side
  pagePoint(side, xmm, ymm, out) {
    const u = side === 'front' ? xmm / 10 : PW - xmm / 10; // cm from the spine
    const vcm = ymm / 10 - PH / 2;
    const k = Math.min(NU - 1e-6, Math.max(0, (u / PW) * NU));
    const j = Math.min(NV - 1e-6, Math.max(0, ((vcm + PH / 2) / PH) * NV));
    const k0 = Math.floor(k), j0 = Math.floor(j), fk = k - k0, fj = j - j0;
    const P = this.posAttr.array;
    const at = (kk, jj, c) => P[(jj * (NU + 1) + kk) * 3 + c];
    for (let c = 0; c < 3; c++) {
      const a = at(k0, j0, c) * (1 - fk) + at(k0 + 1, j0, c) * fk;
      const b = at(k0, j0 + 1, c) * (1 - fk) + at(k0 + 1, j0 + 1, c) * fk;
      out.setComponent(c, a * (1 - fj) + b * fj);
    }
    return out;
  }
}

export class Cover {
  constructor(which, texOut, texIn, clothColor) {
    this.which = which; // 'front' | 'back'
    const edge = new THREE.MeshStandardMaterial({ color: clothColor, roughness: 0.85 });
    const outM = new THREE.MeshStandardMaterial({ map: texOut, roughness: 0.82 });
    const inM = new THREE.MeshStandardMaterial({ map: texIn, roughness: 0.9 });
    const geo = new THREE.BoxGeometry(CW, CT, CH);
    // BoxGeometry material order: +x, -x, +y, -y, +z, -z
    const mats = which === 'front' ? [edge, edge, outM, inM, edge, edge] : [edge, edge, inM, outM, edge, edge];
    this.mesh = new THREE.Mesh(geo, mats);
    this.mesh.castShadow = true; this.mesh.receiveShadow = true;
    this.pivot = new THREE.Group();
    this.pivot.position.set(0, HY, 0);
    const cy = which === 'front' ? T - CT / 2 - HY : CT / 2 - HY;
    this.mesh.position.set(INSET + CW / 2, cy, 0);
    this.pivot.add(this.mesh);
    this.angle = 0;
    this.materials = { edge, outM, inM };
  }
  set(angle) { this.angle = angle; this.pivot.rotation.z = angle; }
  // the board's edge along the spine, in world space (outer surface)
  hingeEdge(out) {
    const y = this.which === 'front' ? T - HY : 0 - HY;
    const c = Math.cos(this.angle), s = Math.sin(this.angle);
    out.set(INSET * c - y * s, INSET * s + y * c + HY, 0);
    return out;
  }
}

// cloth spine joining the two boards' hinge edges
export class Spine {
  constructor(color) {
    this.NS = 10;
    const nv = (this.NS + 1) * 2;
    this.pos = new THREE.BufferAttribute(new Float32Array(nv * 3), 3);
    const idx = [];
    for (let i = 0; i < this.NS; i++) { const a = i * 2, b = a + 1, c = a + 2, d = a + 3; idx.push(a, b, c, b, d, c); }
    this.geo = new THREE.BufferGeometry();
    this.geo.setAttribute('position', this.pos);
    this.geo.setIndex(idx);
    this.mesh = new THREE.Mesh(this.geo, new THREE.MeshStandardMaterial({ color, roughness: 0.85, side: THREE.DoubleSide }));
    this.mesh.castShadow = true; this.mesh.receiveShadow = true; this.mesh.frustumCulled = false;
    this.a = new THREE.Vector3(); this.b = new THREE.Vector3();
  }
  update(front, back) {
    front.hingeEdge(this.a); back.hingeEdge(this.b);
    const mx = (this.a.x + this.b.x) / 2, my = (this.a.y + this.b.y) / 2;
    // bulge away from the body of the book (the average of the two boards)
    const fc = front.mesh.getWorldPosition(this.c0 || (this.c0 = new THREE.Vector3()));
    const bc = back.mesh.getWorldPosition(this.c1 || (this.c1 = new THREE.Vector3()));
    const bx = (fc.x + bc.x) / 2, by = (fc.y + bc.y) / 2;
    let nx = -(this.b.y - this.a.y), ny = this.b.x - this.a.x;
    const nl = Math.hypot(nx, ny) || 1;
    nx /= nl; ny /= nl;
    if (nx * (bx - mx) + ny * (by - my) > 0) { nx = -nx; ny = -ny; }
    const bulge = Math.max(0.05, Math.hypot(this.a.x - this.b.x, this.a.y - this.b.y) * 1.15);
    const cx = mx + nx * bulge, cy = Math.max(0.01, my + ny * bulge);
    const P = this.pos.array;
    for (let i = 0; i <= this.NS; i++) {
      const t = i / this.NS, u = 1 - t;
      const x = u * u * this.a.x + 2 * u * t * cx + t * t * this.b.x;
      const y = Math.max(0.005, u * u * this.a.y + 2 * u * t * cy + t * t * this.b.y);
      P.set([x, y, -CH / 2, x, y, CH / 2], i * 6);
    }
    this.pos.needsUpdate = true;
    this.geo.computeVertexNormals();
  }
}

// the elastic closure: a ribbon whose centre line slides from "round the book" to "on the desk"
export class Band {
  constructor() {
    this.N = 64;
    this.W = 0.62;
    this.x = INSET + CW - 2.4;
    const nv = this.N * 2;
    this.pos = new THREE.BufferAttribute(new Float32Array(nv * 3), 3);
    const idx = [];
    for (let i = 0; i < this.N - 1; i++) { const a = i * 2, b = a + 1, c = a + 2, d = a + 3; idx.push(a, c, b, b, c, d); }
    this.geo = new THREE.BufferGeometry();
    this.geo.setAttribute('position', this.pos);
    this.geo.setIndex(idx);
    this.mesh = new THREE.Mesh(this.geo, new THREE.MeshStandardMaterial({ color: 0x151517, roughness: 0.55, side: THREE.DoubleSide }));
    this.mesh.castShadow = true; this.mesh.receiveShadow = true; this.mesh.frustumCulled = false;
    this.closed = this.resample(this.closedPath());
    this.open = this.resample(this.openPath());
    this.cur = this.closed.map((p) => p.clone());
    this.set(0);
  }
  closedPath() {
    const x = this.x, e = 0.03, z0 = -CH / 2 - e, z1 = CH / 2 + e;
    const pts = [];
    pts.push(new THREE.Vector3(x, CT * 0.5, z0));
    for (let i = 0; i <= 4; i++) { const a = (i / 4) * Math.PI * 0.5; pts.push(new THREE.Vector3(x, CT * 0.5 + Math.sin(a) * (T - CT * 0.5 + e), z0 - Math.cos(a) * 0.02)); }
    for (let i = 1; i < 12; i++) pts.push(new THREE.Vector3(x, T + e + Math.sin((i / 12) * Math.PI) * 0.03, z0 + ((z1 - z0) * i) / 12));
    for (let i = 4; i >= 0; i--) { const a = (i / 4) * Math.PI * 0.5; pts.push(new THREE.Vector3(x, CT * 0.5 + Math.sin(a) * (T - CT * 0.5 + e), z1 + Math.cos(a) * 0.02)); }
    return pts;
  }
  openPath() {
    const x = this.x, z0 = -CH / 2 - 0.03, z1 = CH / 2 + 0.03;
    const pts = [];
    pts.push(new THREE.Vector3(x, CT * 0.5, z0));
    pts.push(new THREE.Vector3(x + 1.2, 0.12, z0 - 0.4));
    pts.push(new THREE.Vector3(x + 3.2, 0.04, z0 + 1.6));
    pts.push(new THREE.Vector3(x + 4.4, 0.04, -3));
    pts.push(new THREE.Vector3(x + 4.7, 0.04, 2.5));
    pts.push(new THREE.Vector3(x + 3.6, 0.04, z1 - 1.8));
    pts.push(new THREE.Vector3(x + 1.2, 0.12, z1 + 0.4));
    pts.push(new THREE.Vector3(x, CT * 0.5, z1));
    return pts;
  }
  resample(pts) {
    const curve = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
    return curve.getSpacedPoints(this.N - 1);
  }
  // t: 0 closed … 1 released; wob: a little elastic overshoot
  set(t, wob = 0) {
    const P = this.pos.array;
    for (let i = 0; i < this.N; i++) {
      const a = this.closed[i], b = this.open[i];
      const f = i / (this.N - 1);
      // the part over the cover leaves first, the ends follow
      const lag = Math.sin(f * Math.PI);
      const tt = Math.min(1, Math.max(0, t * (1 + lag * 0.5) - lag * 0.05));
      const e = tt * tt * (3 - 2 * tt);
      const c = this.cur[i];
      c.lerpVectors(a, b, e);
      // lift while sliding over the board edge
      c.y += Math.sin(Math.PI * e) * 0.9 * lag;
      c.x += Math.sin(Math.PI * e) * 0.6 * lag + wob * lag;
    }
    for (let i = 0; i < this.N; i++) {
      const c = this.cur[i];
      const p0 = this.cur[Math.max(0, i - 1)], p1 = this.cur[Math.min(this.N - 1, i + 1)];
      const tx = p1.x - p0.x, ty = p1.y - p0.y, tz = p1.z - p0.z;
      // width direction: across the path, lying flat when the band is horizontal
      let wx = tz, wz = -tx, wy = 0;
      let L = Math.hypot(wx, wz);
      if (L < 1e-4) { wx = 1; wz = 0; L = 1; }
      wx /= L; wz /= L;
      if (Math.abs(ty) > Math.hypot(tx, tz) * 2) { wx = 1; wz = 0; }
      const h = this.W / 2;
      P.set([c.x - wx * h, c.y + wy, c.z - wz * h, c.x + wx * h, c.y + wy, c.z + wz * h], i * 6);
    }
    this.pos.needsUpdate = true;
    this.geo.computeVertexNormals();
  }
}

// a loop of elastic on the front board's fore-edge that holds the pencil
export function penLoop() {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0x151517, roughness: 0.55, side: THREE.DoubleSide });
  const loop = new THREE.Mesh(new THREE.CylinderGeometry(0.47, 0.47, 1.9, 24, 1, true), mat);
  loop.rotation.x = Math.PI / 2;
  const tab = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.05, 1.9), mat);
  tab.position.set(-0.55, 0.28, 0);
  g.add(loop, tab);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return g;
}
