// The statues of Sanjūsangen-dō: 1000 standing Kannon (three variants), the seated Kannon, the 28 attendants, Fujin and
// Raijin, drawn instanced in three levels of detail and loaded only near the hall.  Gilded wood glows softly in the
// light from the doors (the hall's bake), painted wood keeps its faded colours.
import * as THREE from 'three/webgpu';
import { attribute, uniform, uniformArray, vec2, vec3, vec4, float, mix, clamp, smoothstep, max, dot, normalize, sin, fract, select, abs, pow,
  positionLocal, positionWorld, normalLocal, transformNormalToView, mx_noise_float, renderGroup, cameraPosition, lights } from 'three/tsl';
import { G, KyoMaterial, decIrr } from './kyomat.js';
import { fetchBin } from './tiles.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const LOD_D = [9, 26, 400];          // metres: LOD0 within 9 m, LOD1 within 26 m, LOD2 beyond (to 400 m)
export const HALL = uniform(0.45).setGroup(renderGroup);      // the hall's light on the figures (scene-linear)

export class Statues {
  constructor(scene, { mats }) { this.scene = scene; this.mats = mats; this.groups = []; this.state = 'idle'; this.centre = null; this.t = 0; }
  async load(base) {
    this.state = 'loading';
    await MeshoptDecoder.ready;
    const meta = this.meta = await fetch(`${base}/statues/statues.json`).then((r) => r.json());
    this.base = `${base}/statues`; this.Q = 32767 / meta.q;          // snorm16 -> metres
    this.mat = this.makeMat();
    let cx = 0, cy = 0, n = 0;
    for (const m of meta.models) {
      for (const p of m.inst) { cx += p[0]; cy += p[1]; n++; }
      m.groups = m.lods.map(() => null);
    }
    this.centre = new THREE.Vector2(cx / n, cy / n);
    // the light levels first (whole hall), the full figures when one walks up to them
    await Promise.all(meta.models.flatMap((m) => m.lods.map((l, k) => (k > 0 ? this.loadLod(m, k) : null))));
    this.state = 'ready';
  }
  async loadLod(m, k) {
    if (m.groups[k] || (m.pending && m.pending[k])) return;
    (m.pending ||= {})[k] = true;
    const r = m.lods[k], st = this.meta.stride, nI = m.inst.length;
    const buf = new Uint8Array(await fetchBin(`${this.base}/${r.file}`));
    const vb = new Uint8Array(r.vcount * st), ib = new Uint32Array(r.icount);
    MeshoptDecoder.decodeVertexBuffer(vb, r.vcount, st, buf.subarray(0, r.vlen));
    MeshoptDecoder.decodeIndexBuffer(new Uint8Array(ib.buffer), r.icount, 4, buf.subarray(r.vlen, r.vlen + r.ilen));
    // separate plain arrays per attribute: several interleaved views over one ArrayBuffer made the GPU read c0 from the
    // normal's bytes (the wood came out pale)
    const n = r.vcount, P = new Int16Array(n * 4), Nn = new Int8Array(n * 4), C0 = new Uint8Array(n * 4), C1 = new Uint8Array(n * 4);
    const s16 = new Int16Array(vb.buffer), s8 = new Int8Array(vb.buffer);
    for (let k = 0; k < n; k++) {
      const o = k * st;
      for (let c = 0; c < 4; c++) { P[k * 4 + c] = s16[o / 2 + c]; Nn[k * 4 + c] = s8[o + 8 + c]; C0[k * 4 + c] = vb[o + 12 + c]; C1[k * 4 + c] = vb[o + 16 + c]; }
    }
    const g = new THREE.InstancedBufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(P, 4, true));
    g.setAttribute('normal', new THREE.BufferAttribute(Nn, 4, true));
    g.setAttribute('c0', new THREE.BufferAttribute(C0, 4, true));
    g.setAttribute('c1', new THREE.BufferAttribute(C1, 4, true));
    g.setIndex(new THREE.BufferAttribute(ib, 1));
    const a0 = new THREE.InstancedBufferAttribute(new Float32Array(nI * 4), 4), a1 = new THREE.InstancedBufferAttribute(new Uint8Array(nI * 4), 4, true);
    a0.setUsage(THREE.DynamicDrawUsage); a1.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('i0', a0); g.setAttribute('i1', a1); g.instanceCount = 0;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e7);
    const mesh = new THREE.Mesh(g, this.mat); mesh.frustumCulled = false; mesh.castShadow = false; mesh.receiveShadow = false; mesh.visible = false;
    this.scene.add(mesh);
    m.groups[k] = { g, mesh, a0, a1, n: 0 };
    this.t = 0;
  }
  makeMat() {
    const c0 = attribute('c0', 'vec4'), c1 = attribute('c1', 'vec4'), i0 = attribute('i0', 'vec4'), i1 = attribute('i1', 'vec4');
    const names = this.mats.map((m) => m.name);
    const ALB = uniformArray(this.mats.map((m) => new THREE.Vector4(...m.albedo, ['gold', 'metal'].indexOf(m.kind) + 1)), 'vec4').setGroup(renderGroup);
    const mid = c1.x.mul(255.0).add(0.5).toInt();
    const al = ALB.element(mid);
    const gold = abs(al.w.sub(1.0)).lessThan(0.5);
    const tinted = mid.equal(names.indexOf('cloth')).or(mid.equal(names.indexOf('wood_natural'))).or(mid.equal(names.indexOf('vermilion')));
    const tint = c0.rgb.mul(c0.rgb);
    const pL = positionLocal.mul(this.Q);                      // metres in the model frame
    const n1 = mx_noise_float(pL.mul(6.0)), n2 = mx_noise_float(pL.mul(30.0));
    // gilding: warm gold, rubbed through to dark lacquer on the high points and darkened in the folds
    // antique gilding: deep gold, worn through to the brown lacquer and wood in broad patches (the 1,000 are not new gold)
    const worn = smoothstep(0.15, 0.7, mx_noise_float(pL.mul(2.2).add(vec3(i0.x.mul(0.37), i0.y.mul(0.29), 0.0))).mul(0.5).add(0.5));
    const gcol = mix(mix(vec3(0.34, 0.22, 0.075), vec3(0.72, 0.51, 0.19), smoothstep(-0.4, 0.6, n1)), vec3(0.16, 0.09, 0.045), worn.mul(0.55))
      .mul(float(0.85).add(n2.mul(0.12)));
    // the tinted materials' albedo as constants: the uniform-array lookup returned the wrong entry here (the wood came out pale)
    const albOf = (n) => { const m = this.mats.find((x) => x.name === n); return vec3(...m.albedo); };
    const alT = select(mid.equal(names.indexOf('wood_natural')), albOf('wood_natural'), select(mid.equal(names.indexOf('cloth')), albOf('cloth'), albOf('vermilion')));
    // no nested select(): inside its isolated branch the vertex colour did not resolve (the wood came out pale) — blend with
    // 0/1 weights computed outside instead
    const wood = alT.mul(c0.rgb.mul(c0.rgb)).mul(2.2).toVar();
    const wT = tinted.and(c0.a.lessThan(0.5)).select(float(1.0), float(0.0)).toVar(), wG = gold.select(float(1.0), float(0.0)).toVar();
    const col = mix(mix(al.rgb, wood, wT), gcol, wG).mul(float(0.92).add(n2.mul(0.08))).toVar();
    const irr = decIrr(i1).mul(G.irrGain).mul(G.irrScale);
    // the environment map is the open sky: indoors the gilding would mirror it, so it only gets a trace of it
    const mat = new KyoMaterial({ irrNode: irr.mul(float(0.7).sub(wG.mul(0.45))), occNode: float(0.02) });
    // no sun: the figures are always under the hall's roof, and the shadow map let it through in patches (pale blotches)
    mat.lightsNode = lights([]);
    // yaw from the instance (radians, ccw from east; the model faces +y)
    const yaw = i0.w.sub(Math.PI / 2);
    const cs = yaw.cos(), sn = yaw.sin();
    const p = pL;
    mat.positionNode = vec3(p.x.mul(cs).sub(p.y.mul(sn)), p.x.mul(sn).add(p.y.mul(cs)), p.z).add(i0.xyz);
    const nl = normalLocal;
    const nW = normalize(vec3(nl.x.mul(cs).sub(nl.y.mul(sn)), nl.x.mul(sn).add(nl.y.mul(cs)), nl.z));
    mat.normalNode = transformNormalToView(nW);
    mat.colorNode = col;
    mat.metalnessNode = wG.mul(0.85);
    mat.roughnessNode = mix(float(0.75), float(0.38).add(n1.mul(0.1)), wG);
    // the soft glow of gilding in a dim hall (light from the doors scattered by the gold leaf)
    // and the hall's own light: daylight from the open doors on the aisle side (the way the figures face), warm from
    // the paper and the wood, a soft fill on every surface turned to it and a sheen on the gold
    const Ld = normalize(vec3(i0.w.cos(), i0.w.sin(), 0.45));
    const V = normalize(positionWorld.sub(cameraPosition));
    const Rv = V.sub(nW.mul(dot(V, nW).mul(2.0)));
    const warm = vec3(1.0, 0.8, 0.56).mul(HALL);
    const ndl = max(dot(nW, Ld), 0.0);
    const fill = ndl.mul(0.88).add(0.12);                  // a firm key from the doors: the carving reads as in the photographs
    const sheen = pow(max(dot(Rv, Ld), 0.0), 14.0);
    // gold: the form modelled by the light (dark away from the doors), bright only where the sheen catches
    // blended with the 0/1 weight, not select(): inside select()'s isolated branches the vertex colour resolved wrongly
    // and the wood came out pale in hard-edged patches
    const emG = gcol.mul(warm).mul(ndl.mul(0.3).add(0.05).add(sheen.mul(float(1.8).mul(float(1.0).sub(worn.mul(0.7))))));
    const emW = col.mul(warm).mul(fill.mul(0.75).add(sheen.mul(0.25)));
    mat.emissiveNode = mix(emW, emG, wG);
    return mat;
  }
  update(cam, dt) {
    if (this.state === 'idle' || !this.meta) return;
    const p = cam.position;
    const all = () => this.meta.models.flatMap((m) => m.groups.filter(Boolean));
    if (this.centre && Math.hypot(p.x - this.centre.x, p.y - this.centre.y) > 700) { for (const g of all()) g.mesh.visible = false; return; }
    this.t -= dt; if (this.t > 0) return; this.t = 0.2;
    for (const m of this.meta.models) {
      for (const g of m.groups) if (g) g.n = 0;
      for (let k = 0; k < m.inst.length; k++) {
        const s = m.inst[k], d = Math.hypot(s[0] - p.x, s[1] - p.y, s[2] - p.z);
        if (d > LOD_D[2]) continue;
        let lod = Math.min(m.groups.length - 1, d < LOD_D[0] ? 0 : d < LOD_D[1] ? 1 : 2);
        if (lod === 0 && !m.groups[0] && d < LOD_D[0] + 6) this.loadLod(m, 0).catch((e) => console.warn('statue', m.id, e));
        while (lod < m.groups.length - 1 && !m.groups[lod]) lod++;
        const g = m.groups[lod]; if (!g) continue;
        const j = g.n++;
        g.a0.array.set([s[0], s[1], s[2], s[3]], j * 4);
        g.a1.array.set(m.light[k], j * 4);
      }
      for (const g of m.groups) {
        if (!g) continue;
        g.g.instanceCount = g.n; g.mesh.visible = g.n > 0;
        if (g.n) for (const a of [g.a0, g.a1]) { a.clearUpdateRanges(); a.addUpdateRange(0, g.n * 4); a.needsUpdate = true; }
      }
    }
  }
}
