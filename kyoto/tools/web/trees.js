// Trees: species templates (bark tubes + leaf cards from a procedural atlas) drawn instanced in three levels of detail
// (full within ~70 m, light within ~260 m, a camera-facing impostor to ~1.2 km).  Instances come with the far-LOD tiles
// (position, scale, yaw, species, variant, baked light).  Autumn colours per species; winter: deciduous trees bare
// (the same cards show twigs) and snow on every upward surface.
import * as THREE from 'three/webgpu';
import {
  attribute, uniform, vec2, vec3, vec4, float, int, mix, clamp, smoothstep, max, min, pow, dot, normalize, cross, sin, cos, fract, floor, abs, select,
  positionLocal, positionWorld, normalLocal, normalView, uv, texture, frontFacing, cameraPosition, cameraViewMatrix, mx_noise_float, renderGroup, step, uniformArray, transformNormalToView,
} from 'three/tsl';
import { G, KyoMaterial, decIrr, dappled } from './kyomat.js';

export const TREE_R = { l0: 70, l1: 260, imp: 1250 };
const CAP = { l0: 1600, l1: 7000, imp: 60000 };
const TSH1 = new URLSearchParams(location.search).get('tsh1') === '1';     // debug: let the light trees cast shadows too

// per species: [autumn outer, autumn inner, autumn alt, evergreen?] linear colours; deciduous flag
const PAL = {
  momiji: [[0.62, 0.035, 0.02], [0.72, 0.20, 0.02], [0.70, 0.42, 0.04]],
  ichou: [[0.78, 0.55, 0.04], [0.70, 0.50, 0.06], [0.45, 0.42, 0.06]],
  sakura: [[0.55, 0.13, 0.04], [0.45, 0.22, 0.06], [0.50, 0.32, 0.08]],
  keyaki: [[0.45, 0.17, 0.05], [0.40, 0.24, 0.07], [0.30, 0.22, 0.07]],
  matsu: [[0.05, 0.10, 0.035], [0.04, 0.085, 0.03], [0.06, 0.11, 0.04]],
  sugi: [[0.05, 0.085, 0.03], [0.04, 0.07, 0.025], [0.07, 0.08, 0.03]],
  hinoki: [[0.05, 0.10, 0.04], [0.04, 0.08, 0.03], [0.05, 0.09, 0.035]],
  kashi: [[0.045, 0.09, 0.025], [0.035, 0.075, 0.02], [0.06, 0.10, 0.03]],
  yanagi: [[0.32, 0.38, 0.07], [0.25, 0.33, 0.06], [0.40, 0.40, 0.08]],
  tsutsuji: [[0.06, 0.11, 0.03], [0.30, 0.06, 0.03], [0.05, 0.09, 0.025]],
  take: [[0.16, 0.24, 0.05], [0.12, 0.20, 0.04], [0.18, 0.26, 0.06]],
};

function cellUV(uvn, cell, toCell) {
  // move an atlas uv from its cell to another (4 x 4 atlas)
  const dc = toCell.sub(cell);
  return uvn.add(vec2(fract(toCell.div(4.0)).sub(fract(cell.div(4.0))).mul(1.0), floor(toCell.div(4.0)).sub(floor(cell.div(4.0))).mul(0.25)));
}

export class Trees {
  constructor(scene, { atlas, atlasN, imp, arrays, layers }) {
    this.scene = scene; this.atlas = atlas; this.atlasN = atlasN; this.imp = imp; this.arrays = arrays; this.layers = layers;
    for (const t of [atlas, atlasN, imp]) { t.flipY = false; t.needsUpdate = true; }
    this.groups = []; this.tiles = new Map(); this.last = new THREE.Vector3(1e9, 0, 0); this.t = 0; this.enabled = true;
  }
  async init(base) {
    const [meta, bin] = await Promise.all([fetch(`${base}/trees.json`).then((r) => r.json()), fetch(`${base}/trees.bin`).then((r) => r.arrayBuffer())]);
    this.meta = meta;
    const names = meta.names;
    const spPal = (k) => names.map((n) => new THREE.Vector4(...PAL[n][k], 0));
    this.pal = [0, 1, 2].map((k) => uniformArray(spPal(k), 'vec4').setGroup(renderGroup));
    this.dec = uniformArray(names.map((n) => new THREE.Vector4(meta.templates.find((t) => t.species === n).deciduous, 0, 0, 0)), 'vec4').setGroup(renderGroup);
    this.impMeta = uniformArray(meta.imp.map((m) => new THREE.Vector4(m.cell[0], m.cell[1], m.half, m.h)), 'vec4').setGroup(renderGroup);
    this.matBark = this.makeBark(); this.matLeaf = this.makeLeaf(); this.matImp = this.makeImp();
    for (const t of meta.templates) for (const lod of [0, 1]) for (const part of ['wood', 'leaves']) {
      const r = t[part + lod]; if (!r) continue;
      const g = new THREE.InstancedBufferGeometry();
      const ib = new THREE.InterleavedBuffer(new Float32Array(bin, r.voff, r.vcount * 7), 7);
      const ib8 = new THREE.InterleavedBuffer(new Int8Array(bin, r.voff, r.vcount * 28), 28);
      const ibu = new THREE.InterleavedBuffer(new Uint8Array(bin, r.voff, r.vcount * 28), 28);
      g.setAttribute('position', new THREE.InterleavedBufferAttribute(ib, 3, 0));
      g.setAttribute('normal', new THREE.InterleavedBufferAttribute(ib8, 4, 12, true));
      g.setAttribute('uv', new THREE.InterleavedBufferAttribute(ib, 2, 4));
      g.setAttribute('ta', new THREE.InterleavedBufferAttribute(ibu, 4, 24, true));
      g.setIndex(new THREE.BufferAttribute(new Uint32Array(bin, r.ioff, r.icount), 1));
      this.groups.push(this.makeGroup(g, part === 'wood' ? this.matBark : this.matLeaf, t.si, t.var, lod, part, CAP['l' + lod]));
    }
    // impostors: one quad, all species
    const q = new THREE.InstancedBufferGeometry();
    q.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-0.5, 0, 0, 0.5, 0, 0, 0.5, 1, 0, -0.5, 1, 0]), 3));
    q.setAttribute('uv', new THREE.BufferAttribute(new Float32Array([0, 0, 1, 0, 1, 1, 0, 1]), 2));
    q.setIndex([0, 1, 2, 0, 2, 3]);
    this.impG = this.makeGroup(q, this.matImp, -1, -1, 2, 'imp', CAP.imp);
  }
  makeGroup(g, mat, si, v, lod, part, cap) {
    const a0 = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4); a0.setUsage(THREE.DynamicDrawUsage);
    const a1 = new THREE.InstancedBufferAttribute(new Float32Array(cap * 4), 4); a1.setUsage(THREE.DynamicDrawUsage);
    const a2 = new THREE.InstancedBufferAttribute(new Uint8Array(cap * 4), 4, true); a2.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('i0', a0); g.setAttribute('i1', a1); g.setAttribute('i2', a2);
    g.instanceCount = 0;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e7); g.boundingBox = new THREE.Box3(new THREE.Vector3(-1e7, -1e7, -1e7), new THREE.Vector3(1e7, 1e7, 1e7));
    const m = new THREE.Mesh(g, mat); m.frustumCulled = false; m.receiveShadow = part !== 'imp';
    // shadows from the full trees only (within ~70 m); the light ones (to 260 m) would be drawn into every cascade
    m.castShadow = lod === 0 || (lod === 1 && TSH1);
    this.scene.add(m);
    return { g, m, si, v, lod, part, cap, a0, a1, a2, n: 0 };
  }
  // instance transform: rotate by yaw, scale, sway with the wind
  inst(isImp = false) {
    const i0 = attribute('i0', 'vec4'), i1 = attribute('i1', 'vec4');
    return { i0, i1 };
  }
  pos(wind) {
    const i0 = attribute('i0', 'vec4'), i1 = attribute('i1', 'vec4');
    const p = positionLocal.mul(i0.w);
    const c = i1.x, s = i1.y;
    const r = vec3(p.x.mul(c).sub(p.y.mul(s)), p.x.mul(s).add(p.y.mul(c)), p.z);
    const ph = G.time.mul(1.3).add(i1.z.mul(6.283));
    const sway = vec3(sin(ph), cos(ph.mul(0.83)), 0.0).mul(wind.mul(0.06)).mul(p.z.div(10.0).min(1.5));
    return r.add(sway).add(i0.xyz);
  }
  nrm() {
    const i1 = attribute('i1', 'vec4');
    const n = normalLocal;
    return vec3(n.x.mul(i1.x).sub(n.y.mul(i1.y)), n.x.mul(i1.y).add(n.y.mul(i1.x)), n.z);
  }
  makeBark() {
    const ta = attribute('ta', 'vec4');
    const irrA = attribute('i2', 'vec4');
    const i1 = attribute('i1', 'vec4');
    const irr = decIrr(irrA).mul(G.irrGain).mul(G.irrScale).mul(float(0.75).add(ta.x.mul(0.25)));
    const mat = new KyoMaterial({ irrNode: irr, occNode: float(0.4) });
    mat.positionNode = this.pos(ta.x);
    mat.normalNode = transformNormalToView(this.nrm());
    mat.receivedShadowNode = dappled(irrA.a);
    const LY = Object.fromEntries(this.layers.map((l, i) => [l.name, i]));
    const sp = i1.w.add(0.5).toInt();          // an interpolated float: round, never truncate
    const names = this.meta.names;
    const lay = names.reduceRight((acc, n, k) => select(sp.equal(int(k)), int(n === 'sugi' || n === 'hinoki' ? LY.bark_cedar : n === 'sakura' || n === 'momiji' ? LY.bark_sakura : n === 'take' ? LY.bamboo : LY.wood_grey), acc), int(LY.wood_grey));
    const T = texture(this.arrays.albedo, uv().mul(vec2(0.9, 0.7))).depth(lay);
    const nW = this.nrm();
    const snow = smoothstep(0.25, 0.7, nW.z).mul(G.season);
    // the cedar and plank layers are dark (albedo ~0.06): lift them to a weathered bark's ~0.12
    const gain = select(lay.equal(int(LY.bark_sakura)), float(1.0), select(lay.equal(int(LY.bamboo)), float(0.9), float(1.9)));
    mat.colorNode = mix(T.rgb.mul(gain), vec3(0.8, 0.82, 0.86), snow);
    mat.roughnessNode = float(0.9);
    return mat;
  }
  // lv: a random value per leaf (atlas G): leaves of one tree differ a little, as they do
  // wild: 1 for a forest tree (may still be green); tended trees (precincts, parks, streets, banks) have all turned
  leafColor(sp, rnd, outer, hz, seed, isImp, lv, wild) {
    const tend = float(1.0).sub(wild);
    const p0 = this.pal[0].element(sp).rgb, p1 = this.pal[1].element(sp).rgb, p2 = this.pal[2].element(sp).rgb;
    const tv = fract(seed.mul(7.31));                    // per tree: how far its autumn has come
    let c = mix(p1, p0, smoothstep(0.35, 0.9, outer.add(hz.mul(0.3)).add(tv.mul(0.3)).sub(0.15)));
    c = mix(c, p2, smoothstep(0.5, 0.95, lv).mul(0.75).add(step(0.82, tv).mul(0.5)).min(1.0));
    // maples (from photographs of Eikandō, Tōfuku-ji, Acer palmatum in autumn): each tree stands at its own stage of
    // green -> yellow-green -> amber -> orange -> scarlet -> crimson; the sunlit outside and top lead, the shaded
    // inside lags a stage or two; leaf by leaf a little ahead or behind.  Some maples turn yellow instead.
    const ramp = (stops, P) => stops.slice(1).reduce((acc, [p, col], i) => mix(acc, vec3(...col), smoothstep(stops[i][0], p, P)), vec3(...stops[0][1]));
    const RED = [[0.0, [0.10, 0.17, 0.03]], [0.25, [0.42, 0.40, 0.04]], [0.42, [0.72, 0.42, 0.03]], [0.58, [0.80, 0.22, 0.02]],
      [0.74, [0.68, 0.06, 0.015]], [0.88, [0.52, 0.02, 0.012]], [1.0, [0.38, 0.012, 0.012]]];
    const YEL = [[0.0, [0.12, 0.20, 0.04]], [0.4, [0.45, 0.45, 0.05]], [0.7, [0.86, 0.48, 0.03]], [1.0, [0.84, 0.38, 0.022]]];
    const GIN = [[0.0, [0.15, 0.25, 0.04]], [0.5, [0.55, 0.55, 0.06]], [0.78, [0.92, 0.50, 0.02]], [1.0, [0.90, 0.43, 0.018]]];   // gold: under the evening light a plain yellow reads lime
    const t = fract(seed.mul(13.71)), k = smoothstep(0.25, 0.9, outer.add(hz.mul(0.3)).add(rnd.sub(0.5).mul(0.2)));
    const band = (a, b) => step(a, t).sub(step(b, t));
    const wY = band(0.79, 0.91);
    const Pt = band(-1.0, 0.36).mul(0.92).add(band(0.36, 0.61).mul(0.81)).add(band(0.61, 0.79).mul(0.62)).add(wY.mul(0.88)).add(band(0.91, 2.0).mul(mix(float(0.32), float(0.7), tend)));
    // tended maples: even the shaded inside has gone amber at least
    const P = max(clamp(Pt.sub(float(1.0).sub(k).mul(0.26)).add(lv.sub(0.5).mul(0.34)), 0.0, 1.0), tend.mul(0.44));
    const maple = mix(ramp(RED, P), ramp(YEL, max(P, tend.mul(0.7))), wY);
    // ginkgo: one gold, the trees a little apart (a few still yellow-green), hardly any variation inside one
    const Pg = clamp(mix(float(0.55), float(0.9), tend).add(fract(seed.mul(7.77)).mul(mix(float(0.45), float(0.1), tend))).sub(float(1.0).sub(k).mul(0.06)).add(lv.sub(0.5).mul(0.06)), 0.0, 1.0);
    const ginkgo = ramp(GIN, Pg);
    const isM = sp.equal(int(this.meta.names.indexOf('momiji'))).select(float(1.0), float(0.0));
    const isG = sp.equal(int(this.meta.names.indexOf('ichou'))).select(float(1.0), float(0.0));
    // tended azaleas: dōdan-tsutsuji, scarlet to crimson
    const isA = sp.equal(int(this.meta.names.indexOf('tsutsuji'))).select(float(1.0), float(0.0)).mul(tend);
    const azalea = ramp(RED, clamp(float(0.72).add(fract(seed.mul(3.3)).mul(0.2)).add(lv.sub(0.5).mul(0.2)), 0.0, 1.0));
    c = mix(mix(mix(c, maple, isM), ginkgo, isG), azalea, isA);
    // a few other broadleaves still green
    const green = vec3(0.07, 0.12, 0.03);
    c = mix(c, green, step(0.92, fract(seed.mul(3.71))).mul(this.dec.element(sp).x).mul(float(1.0).sub(isM).sub(isG)).mul(wild).mul(0.8));
    return c.mul(float(0.9).add(rnd.mul(0.2)));
  }
  makeLeaf() {
    const ta = attribute('ta', 'vec4');                 // outer, rnd, height, cell (x255)
    const i1 = attribute('i1', 'vec4'), i2 = attribute('i2', 'vec4');
    const sp = i1.w.add(0.5).toInt();          // an interpolated float: round, never truncate
    const dec = this.dec.element(sp).x;
    const cell = ta.w.mul(255.0).add(0.5).floor();
    const winterBare = G.season.mul(dec).greaterThan(0.5);
    // maples: one leaf shape per tree (イロハモミジ, オオモミジ, ハウチワカエデ: atlas cells 0, 12, 15)
    const isMs = sp.equal(int(this.meta.names.indexOf('momiji'))).select(float(1.0), float(0.0));
    const fm = fract(i1.z.mul(5.31));
    const mcell = step(0.6, fm).mul(12.0).add(step(0.85, fm).mul(3.0));
    const uvM = cellUV(uv(), cell, mix(cell, mcell, isMs));
    const uvn = select(winterBare, cellUV(uv(), cell, float(9.0)), uvM);
    const A = texture(this.atlas, uvn);
    const NM = texture(this.atlasN, uvn).xyz.mul(2).sub(1);
    const seed = i1.z;
    const wild = step(0.15, fract(i1.w));
    let col = this.leafColor(sp, ta.y, ta.x, ta.z, seed, false, A.g, wild).mul(A.r.mul(1.2).add(0.15));
    col = mix(col, vec3(0.09, 0.07, 0.05), A.b);                                      // twigs in the card
    col = select(winterBare, vec3(0.085, 0.07, 0.06).mul(A.r.add(0.4)), col);
    // snow: on the upper side of evergreen sprays and bare twigs
    const nW = normalize(this.nrm());
    const sn = smoothstep(0.1, 0.6, nW.z.add(mx_noise_float(positionWorld.mul(1.7)).mul(0.3))).mul(G.season);
    col = mix(col, vec3(0.78, 0.8, 0.84), sn.mul(select(winterBare, float(0.6), float(0.75))));
    // the sky's blue in the shade, mostly taken out for foliage (as the eye and a camera's white balance do): gold and
    // scarlet in the shade stayed olive and dull
    const irr0 = decIrr(i2).mul(G.irrGain).mul(G.irrScale).mul(float(0.45).add(ta.x.mul(0.55)));
    const irr = mix(irr0, vec3(dot(irr0, vec3(0.2126, 0.7152, 0.0722))).mul(vec3(1.04, 1.0, 0.92)), 0.7);
    const mat = new KyoMaterial({ irrNode: irr, occNode: float(0.3) });
    mat.positionNode = this.pos(float(1.0));
    // spherised card normals, flipped on the back face
    const nv = transformNormalToView(this.nrm());
    mat.normalNode = select(frontFacing, nv, nv.negate());
    mat.colorNode = col;
    mat.opacityNode = A.a;
    mat.alphaTest = 0.45;
    // look the shadow up a little toward the sun: the cards would otherwise shadow themselves (acne in fine stripes)
    mat.receivedShadowPositionNode = positionWorld.add(G.sunDir.mul(0.4));
    mat.receivedShadowNode = dappled(i2.a);
    mat.side = THREE.DoubleSide;
    mat.roughnessNode = float(0.75);
    mat.specularIntensityNode = float(0.3);
    // back-lit leaves glow in the low sun (translucency), stronger for thin deciduous leaves
    const V = normalize(positionWorld.sub(cameraPosition));
    const tr = pow(max(dot(V, G.sunDir), 0.0), 3.0).mul(i2.a).mul(select(winterBare, float(0.0), float(0.55).add(dec.mul(0.6))));
    mat.emissiveNode = col.mul(G.sunCol).mul(tr).mul(0.35);
    return mat;
  }
  makeImp() {
    const i0 = attribute('i0', 'vec4'), i1 = attribute('i1', 'vec4'), i2 = attribute('i2', 'vec4');
    const sp = i1.w.add(0.5).toInt();          // an interpolated float: round, never truncate
    const im = this.impMeta.element(sp);
    const dec = this.dec.element(sp).x;
    const winterBare = G.season.mul(dec).greaterThan(0.5);
    // cylindrical billboard: the quad's x axis across the view, z up
    const toCam = cameraPosition.xy.sub(i0.xy);
    const side = normalize(vec2(toCam.y.negate(), toCam.x).add(vec2(1e-4, 0.0)));
    const w = im.z.mul(2.0).mul(i0.w), h = im.w.mul(i0.w);
    const p = positionLocal;
    const wp = vec3(i0.x.add(side.x.mul(p.x).mul(w)), i0.y.add(side.y.mul(p.x).mul(w)), i0.z.add(p.y.mul(h)));
    const mat = new THREE.MeshBasicNodeMaterial();
    mat.positionNode = wp;
    const row = select(winterBare, im.y.add(2.0), im.y);
    const tuv = vec2(im.x.add(uv().x).div(8.0), row.add(float(1.0).sub(uv().y)).div(4.0));     // flipY off: v down from the top
    const T = texture(this.imp, tuv);
    const seed = i1.z;
    let col = this.leafColor(sp, fract(seed.mul(13.1)), T.g, uv().y, seed, true, T.g, step(0.15, fract(i1.w))).mul(T.r.mul(1.2).add(0.15));
    col = mix(col, vec3(0.09, 0.07, 0.05), T.b);
    col = select(winterBare, vec3(0.085, 0.07, 0.06).mul(T.r.add(0.5)), col);
    col = mix(col, vec3(0.78, 0.8, 0.84), G.season.mul(0.45).mul(smoothstep(0.2, 0.9, uv().y)).mul(float(1.0).sub(T.b)));
    // light: sky + bounce from the bake, the sun on the sunward half, glow when back-lit
    const irr0 = decIrr(i2).mul(G.irrGain).mul(G.irrScale).mul(0.75);
    const irr = mix(irr0, vec3(dot(irr0, vec3(0.2126, 0.7152, 0.0722))).mul(vec3(1.04, 1.0, 0.92)), 0.7);
    const toSun = dot(normalize(vec3(side.y.negate(), side.x, 0.0)), normalize(vec3(G.sunDir.x, G.sunDir.y, 0.0)));
    const sunK = float(0.35).add(uv().x.sub(0.5).mul(toSun).mul(-0.0)).add(0.25).mul(i2.a);
    const V = normalize(positionWorld.sub(cameraPosition));
    const tr = pow(max(dot(V, G.sunDir), 0.0), 3.0).mul(i2.a).mul(float(0.3).add(dec.mul(0.5)));
    mat.colorNode = col.mul(irr.add(G.sunCol.mul(sunK)).add(G.sunCol.mul(tr))).div(Math.PI);
    mat.opacityNode = T.a;
    mat.alphaTest = 0.4;
    return mat;
  }
  // tiles hand in their tree instances (from the far-LOD bin)
  addTile(name, S) {
    if (!S.tpos) return;
    const pos = new Float32Array(S.tpos.buffer), q = S.tq, ir = S.tirr;
    this.tiles.set(name, { pos, q, ir, n: pos.length / 4 });
    this.dirty = true;
  }
  dropTile(name) { if (this.tiles.delete(name)) this.dirty = true; }
  update(cam, dt) {
    if (!this.meta) return;
    this.t -= dt;
    const p = cam.position;
    if (!this.dirty && this.t > 0 && p.distanceToSquared(this.last) < 16) return;
    this.t = 0.25; this.dirty = false; this.last.copy(p);
    const R0 = TREE_R.l0 ** 2, R1 = TREE_R.l1 ** 2, RI = TREE_R.imp ** 2;
    const NV = 3;
    for (const g of this.groups) g.n = 0;
    this.impG.n = 0;
    const key = (si, v, lod) => (si * NV + v) * 2 + lod;
    if (!this.byKey) { this.byKey = new Map(); for (const g of this.groups) { const k = key(g.si, g.v, g.lod); if (!this.byKey.has(k)) this.byKey.set(k, []); this.byKey.get(k).push(g); } }
    const winter = G.season.value > 0.5;
    for (const T of this.tiles.values()) {
      const { pos, q, ir, n } = T;
      for (let i = 0; i < n; i++) {
        const x = pos[i * 4], y = pos[i * 4 + 1], z = pos[i * 4 + 2], s = pos[i * 4 + 3];
        const d2 = (x - p.x) ** 2 + (y - p.y) ** 2 + ((z - p.z) * 0.5) ** 2;
        if (d2 > RI) continue;
        // variant byte: bit 3 = a wild tree (forest); it travels to the shader as si + 0.3 (rounded away there)
        const si = q[i * 4], v = q[i * 4 + 1] & 7, wild = q[i * 4 + 1] >> 3, yaw = q[i * 4 + 2] / 255 * 6.2832, seed = q[i * 4 + 3] / 255;
        let list = null;
        if (d2 < R1) list = this.byKey.get(key(si, v % NV, d2 < R0 ? 0 : 1));
        const targets = list || [this.impG];
        for (const g of targets) {
          if (g.n >= g.cap) continue;
          const k = g.n++;
          g.a0.array[k * 4] = x; g.a0.array[k * 4 + 1] = y; g.a0.array[k * 4 + 2] = z; g.a0.array[k * 4 + 3] = s;
          g.a1.array[k * 4] = Math.cos(yaw); g.a1.array[k * 4 + 1] = Math.sin(yaw); g.a1.array[k * 4 + 2] = seed; g.a1.array[k * 4 + 3] = si + (wild ? 0.3 : 0);
          g.a2.array[k * 4] = ir[i * 4]; g.a2.array[k * 4 + 1] = ir[i * 4 + 1]; g.a2.array[k * 4 + 2] = ir[i * 4 + 2]; g.a2.array[k * 4 + 3] = ir[i * 4 + 3];
        }
      }
    }
    for (const g of [...this.groups, this.impG]) {
      g.g.instanceCount = g.n; g.m.visible = g.n > 0;
      if (g.n) for (const a of [g.a0, g.a1, g.a2]) { a.clearUpdateRanges(); a.addUpdateRange(0, g.n * 4); a.needsUpdate = true; }
    }
  }
  stats() { let n0 = 0, n1 = 0; for (const g of this.groups) { if (g.lod === 0 && g.part === 'leaves') n0 += g.n; if (g.lod === 1 && g.part === 'leaves') n1 += g.n; } return { l0: n0, l1: n1, imp: this.impG ? this.impG.n : 0 }; }
}
