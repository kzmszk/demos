// Geometry accumulator for generated city parts (facades, props). Compact attribute formats:
//   position f32x3 (world), normal snorm8x4, tangent snorm8x4 (w = handedness), uv f32x2 (metres),
//   lm f32x3 (lightmap page uv + layer), c0 unorm8x4 (tint rgb, decay), c1 unorm8x4 (mat, dirt, seed, flags), aux f32x2 (baseZ, ao)
import * as THREE from 'three/webgpu';

export class Geo {
  constructor(cap = 4096) {
    this.n = 0; this.cap = 0; this.ni = 0; this.idx = new Uint32Array(cap * 2); this._grow(cap);
  }
  _grow(c) {
    const old = this.cap ? this : null;
    const P = new Float32Array(c * 3), N = new Int8Array(c * 4), T = new Int8Array(c * 4), U = new Float32Array(c * 2), U2 = new Float32Array(c * 3),
      C0 = new Uint8Array(c * 4), C1 = new Uint8Array(c * 4), AX = new Float32Array(c * 2);
    if (old) { P.set(this.P); N.set(this.N); T.set(this.T); U.set(this.U); U2.set(this.U2); C0.set(this.C0); C1.set(this.C1); AX.set(this.AX); }
    Object.assign(this, { P, N, T, U, U2, C0, C1, AX, cap: c });
  }
  // add one vertex; s = state {n:[x,y,z], t:[x,y,z,w], c0:[r,g,b,a], c1:[m,d,s,f], base, ao}
  v(x, y, z, u, w, u2x, u2y, lay, s) {
    if (this.n >= this.cap) this._grow(this.cap * 2);
    const i = this.n++;
    this.P[i * 3] = x; this.P[i * 3 + 1] = y; this.P[i * 3 + 2] = z;
    const n = s.n, t = s.t;
    this.N[i * 4] = n[0] * 127; this.N[i * 4 + 1] = n[1] * 127; this.N[i * 4 + 2] = n[2] * 127; this.N[i * 4 + 3] = 127;
    this.T[i * 4] = t[0] * 127; this.T[i * 4 + 1] = t[1] * 127; this.T[i * 4 + 2] = t[2] * 127; this.T[i * 4 + 3] = (t[3] < 0 ? -127 : 127);
    this.U[i * 2] = u; this.U[i * 2 + 1] = w; this.U2[i * 3] = u2x; this.U2[i * 3 + 1] = u2y; this.U2[i * 3 + 2] = lay;
    const c0 = s.c0, c1 = s.c1;
    this.C0[i * 4] = c0[0]; this.C0[i * 4 + 1] = c0[1]; this.C0[i * 4 + 2] = c0[2]; this.C0[i * 4 + 3] = c0[3];
    this.C1[i * 4] = c1[0]; this.C1[i * 4 + 1] = c1[1]; this.C1[i * 4 + 2] = c1[2]; this.C1[i * 4 + 3] = c1[3];
    this.AX[i * 2] = s.base ?? -100; this.AX[i * 2 + 1] = s.ao ?? 1;
    return i;
  }
  _idx(k) { if (this.ni + k > this.idx.length) { const o = this.idx; this.idx = new Uint32Array(o.length * 2); this.idx.set(o); } }
  tri(a, b, c) { this._idx(3); const I = this.idx, i = this.ni; I[i] = a; I[i + 1] = b; I[i + 2] = c; this.ni += 3; }
  quad(a, b, c, d) { this._idx(6); const I = this.idx, i = this.ni; I[i] = a; I[i + 1] = b; I[i + 2] = c; I[i + 3] = a; I[i + 4] = c; I[i + 5] = d; this.ni += 6; }
  build() {
    const g = new THREE.BufferGeometry(), n = this.n;
    // big builds: views, not copies (copying a big facade chunk cost tens of ms in one frame); small builds: copies,
    // so a mostly empty 3.6 MB builder is not kept alive behind a small mesh.  The builder is not reused afterwards.
    const cut = n * 2 > this.cap ? (A, k) => A.subarray(0, n * k) : (A, k) => A.slice(0, n * k);
    g.setAttribute('position', new THREE.BufferAttribute(cut(this.P, 3), 3));
    g.setAttribute('normal', new THREE.BufferAttribute(cut(this.N, 4), 4, true));
    g.setAttribute('tangent', new THREE.BufferAttribute(cut(this.T, 4), 4, true));
    g.setAttribute('uv', new THREE.BufferAttribute(cut(this.U, 2), 2));
    g.setAttribute('lm', new THREE.BufferAttribute(cut(this.U2, 3), 3));
    g.setAttribute('c0', new THREE.BufferAttribute(cut(this.C0, 4), 4, true));
    g.setAttribute('c1', new THREE.BufferAttribute(cut(this.C1, 4), 4, true));
    g.setAttribute('aux', new THREE.BufferAttribute(cut(this.AX, 2), 2));
    const I = this.idx.subarray(0, this.ni);
    g.setIndex(n > 65535 ? new THREE.BufferAttribute(I, 1) : new THREE.BufferAttribute(Uint16Array.from(I), 1));
    g.computeBoundingBox(); g.computeBoundingSphere();
    return g;
  }
}
