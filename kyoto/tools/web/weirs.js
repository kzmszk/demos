// White water at the weirs across the Kamo, the Takano and the Ōi (落差工, 葛野大堰): a strip from each crest a few metres
// downstream, the foam carried along by the current and thinning out (data/weirs.json, tools/gen/weirs.py).
import * as THREE from 'three/webgpu';
import { uv, vec3, float, clamp, smoothstep, pow, mx_noise_float, attribute } from 'three/tsl';
import { G, KyoMaterial } from './kyomat.js';

export class Weirs {
  constructor(scene) { this.scene = scene; this.mesh = null; }
  async load(base) {
    const W = await fetch(`${base}/weirs.json`).then((r) => (r.ok ? r.json() : [])).catch(() => []);
    if (!W.length) return;
    const P = [], U = [], E = [], I = [];
    for (const w of W) {
      const [dx, dy] = w.dir, L = 6.0, up = 0.35;           // metres downstream of the crest, and above it
      const b0 = P.length / 3; let acc = 0;
      const len = w.pts.reduce((s_, p, k) => s_ + (k ? Math.hypot(p[0] - w.pts[k - 1][0], p[1] - w.pts[k - 1][1]) : 0), 0);
      w.pts.forEach(([x, y], k) => {
        if (k) acc += Math.hypot(x - w.pts[k - 1][0], y - w.pts[k - 1][1]);
        P.push(x - dx * up, y - dy * up, w.z + 0.035, x + dx * L, y + dy * L, w.z + 0.03);
        U.push(acc, 0, acc, 1); const e = Math.min(acc, len - acc); E.push(e, e);   // e: metres from the nearer bank
      });
      for (let k = 0; k < w.pts.length - 1; k++) { const a = b0 + k * 2; I.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(P.length).fill(0).map((_, i) => (i % 3 === 2 ? 1 : 0)), 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2));
    g.setAttribute('edge', new THREE.Float32BufferAttribute(E, 1));
    g.setIndex(I);
    const a = uv().x, d = uv().y, t = G.time;
    // churned at the crest, streaming away in tongues of foam
    const n1 = mx_noise_float(vec3(a.mul(1.1), d.mul(3.5).sub(t.mul(1.2)), 0.5)).mul(0.5).add(0.5);
    const n2 = mx_noise_float(vec3(a.mul(3.7), d.mul(9.0).sub(t.mul(2.3)), 3.1)).mul(0.5).add(0.5);
    const foam = n1.mul(0.6).add(n2.mul(0.4)).sub(d.mul(0.75)).add(smoothstep(0.22, 0.03, d).mul(0.3));   // churned at the crest
    const alpha = smoothstep(0.38, 0.62, foam).mul(pow(float(1.0).sub(d), 1.3)).mul(smoothstep(0.0, 0.04, d))
      .mul(smoothstep(0.0, 3.0, attribute('edge', 'float'))).mul(0.9);
    const mat = new KyoMaterial({ irrNode: vec3(1.5).mul(G.irrGain).mul(G.irrScale), occNode: float(0.0) });
    mat.colorNode = vec3(0.74, 0.77, 0.78).mul(float(0.7).add(n2.mul(0.35)));
    mat.opacityNode = clamp(alpha, 0.0, 1.0);
    mat.roughnessNode = float(0.85);
    mat.transparent = true; mat.depthWrite = false;
    this.mesh = new THREE.Mesh(g, mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 5;
    this.scene.add(this.mesh);
  }
}
