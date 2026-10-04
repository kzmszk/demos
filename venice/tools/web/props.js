// Instanced props (mooring poles, bricole, lanterns, chimneys, wellheads, moored boats) per tile.
import * as THREE from 'three/webgpu';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

export class Props {
  constructor(material) { this.material = material; this.tpl = []; }
  async init(base) {
    await MeshoptDecoder.ready;
    const [hdr, bin] = await Promise.all([fetch(`${base}/props.json`).then((r) => r.json()), fetch(`${base}/props.bin`).then((r) => r.arrayBuffer())]);
    const src = new Uint8Array(bin);
    for (const rec of hdr.templates) {
      const S = {};
      for (const s of rec.streams) {
        const part = src.subarray(s.off, s.off + s.len);
        if (s.kind === 'i') { const o = new Uint32Array(s.count); MeshoptDecoder.decodeIndexBuffer(new Uint8Array(o.buffer), s.count, 4, part); S[s.name] = o; }
        else { const o = new Uint8Array(s.count * s.stride); MeshoptDecoder.decodeVertexBuffer(o, s.count, s.stride, part); S[s.name] = o; }
      }
      const attrs = {
        position: new THREE.BufferAttribute(new Float32Array(S.pos.buffer), 3),
        normal: new THREE.BufferAttribute(new Int8Array(S.nrm.buffer), 4, true),
        tangent: new THREE.BufferAttribute(new Int8Array(S.tan.buffer), 4, true),
        uv: new THREE.BufferAttribute(new Float32Array(S.uv.buffer), 2),
        c0: new THREE.BufferAttribute(S.c0, 4, true),
        c1: new THREE.BufferAttribute(S.c1, 4, true),
      };
      const box = new THREE.Box3().setFromBufferAttribute(attrs.position);
      this.tpl.push({ name: rec.name, attrs, index: new THREE.BufferAttribute(S.idx, 1), box });
    }
  }
  // one static mesh per tile: every instance baked into world space.  (three.js gives each InstancedMesh its own
  // uniquely named instance-matrix buffer in the shader, so instancing compiled new pipelines for every tile —
  // seconds of stall while walking — and re-uploaded the matrices every frame; baked props share one pipeline.)
  build(S) {
    const group = new THREE.Group(); group.name = 'props';
    if (!S.ipos || !this.tpl.length) return group;
    const pos = new Float32Array(S.ipos.buffer), sct = S.isct, col = S.icol, irr = S.iirr, irrn = S.iirrn;
    const n = pos.length / 4;
    let nv = 0, ni = 0;
    for (let i = 0; i < n; i++) { const T = this.tpl[sct[i * 4 + 3]]; if (T) { nv += T.attrs.position.count; ni += T.index.count; } }
    if (!nv) return group;
    const P = new Float32Array(nv * 3), N = new Int8Array(nv * 4), Tn = new Int8Array(nv * 4), UV = new Float32Array(nv * 2);
    const C0 = new Uint8Array(nv * 4), C1 = new Uint8Array(nv * 4), D = new Uint8Array(nv * 12), I = new Uint32Array(ni);
    let v0 = 0, i0 = 0;
    const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < n; i++) {
      const T = this.tpl[sct[i * 4 + 3]]; if (!T) continue;
      const tp = T.attrs.position.array, tn = T.attrs.normal.array, tt = T.attrs.tangent.array, tu = T.attrs.uv.array, t0 = T.attrs.c0.array, t1 = T.attrs.c1.array, ti = T.index.array;
      const k = T.attrs.position.count;
      const ox = pos[i * 4], oy = pos[i * 4 + 1], oz = pos[i * 4 + 2], yaw = pos[i * 4 + 3];
      const c = Math.cos(yaw), s_ = Math.sin(yaw);
      const sx = sct[i * 4] / 100, sy = sct[i * 4 + 1] / 100, sz = sct[i * 4 + 2] / 100;
      for (let q = 0; q < k; q++) {
        const x = tp[q * 3] * sx, y = tp[q * 3 + 1] * sy, z = tp[q * 3 + 2] * sz;
        const wx = ox + c * x - s_ * y, wy = oy + s_ * x + c * y, wz = oz + z;
        const o = (v0 + q) * 3; P[o] = wx; P[o + 1] = wy; P[o + 2] = wz;
        if (wx < lo[0]) lo[0] = wx; if (wy < lo[1]) lo[1] = wy; if (wz < lo[2]) lo[2] = wz;
        if (wx > hi[0]) hi[0] = wx; if (wy > hi[1]) hi[1] = wy; if (wz > hi[2]) hi[2] = wz;
        // normal: inverse scale, then the yaw; tangent: scale, then the yaw (w = handedness kept)
        let nx = tn[q * 4] / sx, ny = tn[q * 4 + 1] / sy, nz = tn[q * 4 + 2] / sz; let l = Math.hypot(nx, ny, nz) || 1;
        nx /= l; ny /= l; nz /= l;
        const a = (v0 + q) * 4;
        N[a] = Math.round((c * nx - s_ * ny) * 127); N[a + 1] = Math.round((s_ * nx + c * ny) * 127); N[a + 2] = Math.round(nz * 127); N[a + 3] = 0;
        let ux = tt[q * 4] * sx, uy = tt[q * 4 + 1] * sy, uz = tt[q * 4 + 2] * sz; l = Math.hypot(ux, uy, uz) || 1;
        ux /= l; uy /= l; uz /= l;
        Tn[a] = Math.round((c * ux - s_ * uy) * 127); Tn[a + 1] = Math.round((s_ * ux + c * uy) * 127); Tn[a + 2] = Math.round(uz * 127); Tn[a + 3] = tt[q * 4 + 3];
      }
      UV.set(tu, v0 * 2); C0.set(t0, v0 * 4); C1.set(t1, v0 * 4);
      // per-instance baked light and colour, repeated on every vertex (one interleaved buffer: 8 vertex buffers max)
      for (let q = 0; q < k; q++) {
        const b = (v0 + q) * 12;
        D[b] = irr[i * 4]; D[b + 1] = irr[i * 4 + 1]; D[b + 2] = irr[i * 4 + 2]; D[b + 3] = irr[i * 4 + 3];
        if (irrn) { D[b + 4] = irrn[i * 4]; D[b + 5] = irrn[i * 4 + 1]; D[b + 6] = irrn[i * 4 + 2]; D[b + 7] = irrn[i * 4 + 3]; }
        D[b + 8] = col[i * 4]; D[b + 9] = col[i * 4 + 1]; D[b + 10] = col[i * 4 + 2]; D[b + 11] = col[i * 4 + 3];
      }
      for (let q = 0; q < ti.length; q++) I[i0 + q] = ti[q] + v0;
      v0 += k; i0 += ti.length;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(P, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(N, 4, true));
    g.setAttribute('tangent', new THREE.BufferAttribute(Tn, 4, true));
    g.setAttribute('uv', new THREE.BufferAttribute(UV, 2));
    g.setAttribute('c0', new THREE.BufferAttribute(C0, 4, true));
    g.setAttribute('c1', new THREE.BufferAttribute(C1, 4, true));
    const ib = new THREE.InterleavedBuffer(D, 12);
    g.setAttribute('iirr', new THREE.InterleavedBufferAttribute(ib, 4, 0, true));
    g.setAttribute('iirrn', new THREE.InterleavedBufferAttribute(ib, 4, 4, true));
    g.setAttribute('icol', new THREE.InterleavedBufferAttribute(ib, 4, 8, true));
    g.setIndex(new THREE.BufferAttribute(I, 1));
    g.boundingBox = new THREE.Box3(new THREE.Vector3(...lo), new THREE.Vector3(...hi));
    g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
    const mesh = new THREE.Mesh(g, this.material);
    mesh.castShadow = true; mesh.receiveShadow = true; mesh.matrixAutoUpdate = false;
    group.add(mesh);
    return group;
  }
}
