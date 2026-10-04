// Tile streaming.  Every tile has a light far LOD ("lite": simplified roofs/ground/heroes + facade strips with
// procedural windows) that is always loaded, and a full version (static mesh, facades with two LODs, props)
// loaded near the camera.  Walk/water rasters come with the full tile.
import * as THREE from 'three/webgpu';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { buildFarFacades, FacadeBuilder, packAtlas, fillAtlas, chunkFacades } from './facade.js';

const NEAR_R = 150;          // tile gets its lightmap atlas (near facades possible)
const CHUNK_R = 75;          // a 50 m chunk of facades gets real openings, sills, shutters, balconies
const PROPS_R = 280;         // instanced props (poles, chimneys, boats) per tile
const FULL_R = 380;          // full tile
const FULL_DROP = 500;
const HERO_R = 260;          // hand-modelled heroes in full detail (else their simplified far LOD)

// frame-hitch diagnostics: phases slower than 8 ms are logged to window.__perf ([label, ms, t])
const PERF = (globalThis.__perf = globalThis.__perf || []);
export function perfLog(e) { PERF.push(e); if (PERF.length > 4000) PERF.splice(0, 1000); }   // bounded
export function timed(label, fn) { const t = performance.now(); const r = fn(); const dt = performance.now() - t; if (dt > 8) perfLog([label, Math.round(dt), Math.round(t)]); return r; }

function decodeStreams(bin, streams) {
  const src = new Uint8Array(bin); const S = {};
  for (const s of streams) {
    const part = src.subarray(s.off, s.off + s.len);
    if (s.kind === 'i') { const out = new Uint32Array(s.count); MeshoptDecoder.decodeIndexBuffer(new Uint8Array(out.buffer), s.count, 4, part); S[s.name] = out; }
    else { const out = new Uint8Array(s.count * s.stride); MeshoptDecoder.decodeVertexBuffer(out, s.count, s.stride, part); S[s.name] = out; }
  }
  return S;
}

export class Tiles {
  constructor(scene, o) {
    Object.assign(this, o); this.scene = scene; this.tiles = new Map(); this.lites = new Map(); this.loading = 0; this.liteLoading = 0; this.nearBusy = false;
    this.walk = new Map();      // name -> {data: Uint8Array RGBA, size, bbox}
  }
  async init() {
    await MeshoptDecoder.ready;
    this.index = (await (await fetch(`${this.base}/tiles.json`)).json()).tiles;
  }
  dist(bb, p) {
    const dx = Math.max(bb[0] - p.x, 0, p.x - bb[2]), dy = Math.max(bb[1] - p.y, 0, p.y - bb[3]);
    return Math.hypot(dx, dy);
  }
  update(cam) {
    const p = cam.position;
    const all = Object.entries(this.index).map(([n, t]) => [n, t, this.dist(t.bbox, p)]).sort((a, b) => a[2] - b[2]);
    // full tiles near the camera (the walk raster needs the tile we stand on first)
    for (const [n, t, d] of all) {
      if (d < FULL_R && !this.tiles.has(n) && this.loading < 3) { this.tiles.set(n, { state: 'loading' }); this.loading++; this.load(n).catch((e) => console.error(n, e)).finally(() => this.loading--); }
    }
    // far LOD everywhere, nearest first
    for (const [n, t, d] of all) {
      if (!t.lite || this.lites.has(n) || this.liteLoading >= 6) continue;
      this.lites.set(n, { state: 'loading' }); this.liteLoading++;
      this.loadLite(n, t).catch((e) => console.error('lite', n, e)).finally(() => this.liteLoading--);
    }
    for (const [n, T] of this.tiles) {
      if (T.state === 'ready' && this.dist(T.meta.bbox, p) > FULL_DROP) this.drop(n, T);
    }
    // a tile shows its far LOD until the full version is in; heroes switch to full detail within HERO_R.
    // layers: 0 = everyone, 1 = main view (and shadows) only, 2 = water reflection only
    for (const [n, L] of this.lites) {
      if (!L.group) continue;
      const T = this.tiles.get(n); const full = !!(T && T.state === 'ready');
      L.base.visible = !full;
      const heroNear = full && T.hero && this.dist(T.meta.bbox, p) < HERO_R;
      if (T && T.hero) T.hero.visible = heroNear;
      if (L.hero) { L.hero.visible = true; L.hero.traverse((o) => o.layers.set(heroNear ? 2 : 0)); }
    }
    // near facades: tiles within NEAR_R own a lightmap atlas; chunks within CHUNK_R get detailed geometry.
    // A chunk is built a few facades per frame (~4 ms), so walking never stalls on it; one atlas per frame.
    if (this.job) timed('chunk-step', () => this.stepChunk(4.0));
    let budget = 1;
    for (const [n, t, d] of all) {
      const T = this.tiles.get(n);
      if (!T || T.state !== 'ready' || !T.chunks) continue;
      if (d < NEAR_R && !T.slots && budget > 0) { timed('atlas', () => this.makeAtlas(T)); budget--; }
      if (T.props) T.props.visible = d < PROPS_R;
      if (!T.slots) continue;
      for (const c of T.chunks) {
        const dc = this.dist(c.bbox, p);
        if (dc < CHUNK_R && !c.near && !this.job) this.job = { T, c, fb: new FacadeBuilder(this.mats, { rects: T.rects, slots: T.slots }), k: 0 };
        if (c.near) {
          const on = dc < CHUNK_R + 25;
          c.near.visible = on; c.far.visible = !on;
          if (dc > CHUNK_R + 80) this.dropChunk(T, c);
        }
      }
    }
    for (const T of this.tiles.values()) if (T.slots && this.dist(T.meta.bbox, p) > NEAR_R + 60) this.dropAtlas(T);
  }
  async loadLite(n, t) {
    const bin = await (await fetch(`${this.base}/${n}.lite.bin`)).arrayBuffer();
    const S = timed('lite:decode', () => decodeStreams(bin, t.lite.streams));
    const group = new THREE.Group(); group.name = n + ':lite';
    const base = new THREE.Group(), hero = new THREE.Group(); group.add(base, hero);
    const mk = (pre, mat, extra, into = base) => {
      if (!S[pre + 'pos']) return;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(S[pre + 'pos'].buffer), 4, true));
      g.setAttribute('irr', new THREE.BufferAttribute(S[pre + 'irr'], 4, true));
      g.setAttribute('irrn', new THREE.BufferAttribute(S[pre + 'irrn'] || new Uint8Array(S[pre + 'irr'].length), 4, true));
      g.setAttribute('c0', new THREE.BufferAttribute(S[pre + 'c0'], 4, true));
      g.setAttribute('c1', new THREE.BufferAttribute(S[pre + 'c1'], 4, true));
      if (extra) extra(g);
      g.setIndex(new THREE.BufferAttribute(S[pre + 'idx'], 1));
      g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 1, 1));
      g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
      const m = new THREE.Mesh(g, mat);
      m.position.set(...t.lite.qmin); m.scale.setScalar(t.lite.qext);
      m.castShadow = true; m.receiveShadow = true; m.matrixAutoUpdate = false; m.updateMatrix();
      into.add(m);
    };
    mk('m:', this.matLite);
    mk('h:', this.matLite, null, hero);
    mk('f:', this.matLiteFac, (g) => {
      g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(S['f:uv'].buffer), 2));
      g.setAttribute('w0', new THREE.BufferAttribute(new Float32Array(S['f:w0'].buffer), 4));
      g.setAttribute('w1', new THREE.BufferAttribute(new Float32Array(S['f:w1'].buffer), 4));
    });
    this.scene.add(group);
    this.lites.set(n, { state: 'ready', group, base, hero: S['h:pos'] ? hero : null });
  }
  async load(n) {
    const [meta, bin] = await Promise.all([fetch(`${this.base}/${n}.json`).then((r) => r.json()), fetch(`${this.base}/${n}.bin`).then((r) => r.arrayBuffer())]);
    const S = timed('full:decode', () => decodeStreams(bin, meta.streams));
    const tb = performance.now();
    const T = { name: n, meta, S, state: 'ready', group: new THREE.Group() };
    T.group.name = n;
    if (S.pos) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(S.pos.buffer), 4, true));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(S.nrm.buffer), 4, true));
      g.setAttribute('tangent', new THREE.BufferAttribute(new Int8Array(S.tan.buffer), 4, true));
      g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(S.uv.buffer), 2));
      g.setAttribute('c0', new THREE.BufferAttribute(S.c0, 4, true));
      g.setAttribute('c1', new THREE.BufferAttribute(S.c1, 4, true));
      g.setAttribute('irr', new THREE.BufferAttribute(S.irr, 4, true));
      g.setAttribute('irrn', new THREE.BufferAttribute(S.irrn || new Uint8Array(S.irr.length), 4, true));
      g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 1, 1));
      g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
      const mkMesh = (idx) => {
        const gg = idx === S.idx ? g : g.clone();
        gg.setIndex(new THREE.BufferAttribute(idx, 1));
        const m = new THREE.Mesh(gg, this.matStatic);
        m.position.set(...meta.qmin); m.scale.setScalar(Array.isArray(meta.qext) ? Math.max(...meta.qext) : meta.qext);
        m.castShadow = true; m.receiveShadow = true; m.matrixAutoUpdate = false; m.updateMatrix();
        T.group.add(m); return m;
      };
      if (meta.hr) {
        // hand-modelled heroes are a contiguous triangle range: their own mesh (main view only, switched by distance)
        const a = meta.hr[0] * 3, b = meta.hr[1] * 3;
        const baseIdx = new Uint32Array(S.idx.length - (b - a)); baseIdx.set(S.idx.subarray(0, a)); baseIdx.set(S.idx.subarray(b), a);
        T.mesh = mkMesh(baseIdx);
        T.hero = mkMesh(S.idx.slice(a, b)); T.hero.layers.set(1);
      } else T.mesh = mkMesh(S.idx);
    }
    if (performance.now() - tb > 8) perfLog(['full:geom', Math.round(performance.now() - tb), Math.round(tb)]);
    if (meta.fac && meta.fac.length) timed('full:farFacades', () => {
      // one mesh for all of the tile's coarse facades (draw calls and per-object uniforms add up over 25 tiles);
      // per-chunk coarse meshes exist only while the tile is near enough for detailed chunks to replace them
      T.farAll = new THREE.Mesh(buildFarFacades(meta, S.girr, S.girrn, this.mats, null), this.matStatic);
      T.farAll.castShadow = true; T.farAll.receiveShadow = true; T.group.add(T.farAll);
      T.chunks = chunkFacades(meta).map((c) => ({ ...c, far: null, near: null }));
    });
    if (this.props) { const pg = timed('full:props', () => this.props.build(S)); pg.traverse((o) => o.layers.set(1)); T.group.add(pg); T.props = pg; }
    if (this.index[n] && this.index[n].walk) this.loadWalk(n).catch((e) => console.error('walk', n, e));
    this.scene.add(T.group);
    this.tiles.set(n, T);
    this.onLoad && this.onLoad(T);
  }
  async loadWalk(n) {
    const blob = await (await fetch(`${this.base}/${n}.walk.png`)).blob();
    const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
    const c = new OffscreenCanvas(bmp.width, bmp.height); const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(bmp, 0, 0);
    const data = timed('walk:png', () => g.getImageData(0, 0, bmp.width, bmp.height).data);
    this.walk.set(n, { data, size: bmp.width, bbox: this.index[n].bbox });
  }
  drop(n, T) {
    if (T.slots) this.dropAtlas(T);
    this.scene.remove(T.group);
    T.group.traverse((o) => { if (o.isMesh && o.geometry) o.geometry.dispose(); });
    this.tiles.delete(n);
    this.walk.delete(n);
  }
  makeAtlas(T) {
    const fac = T.meta.fac;
    const { rects, pages } = packAtlas(fac);
    const slots = this.pool.alloc(pages);
    if (!slots) return;
    this.pool.write(slots, fillAtlas(fac, rects, pages, T.S.girr), 'day');
    this.pool.write(slots, fillAtlas(fac, rects, pages, T.S.girrn), 'night');
    T.slots = slots; T.rects = rects;
    // near: the merged coarse facades stay for the water reflection only; the main view gets them per chunk
    for (const c of T.chunks) {
      c.far = new THREE.Mesh(buildFarFacades(T.meta, T.S.girr, T.S.girrn, this.mats, c.list), this.matStatic);
      c.far.castShadow = true; c.far.receiveShadow = true; c.far.layers.set(1); T.group.add(c.far);
    }
    T.farAll.layers.set(2);
  }
  stepChunk(ms) {
    const J = this.job, fac = J.T.meta.fac, list = J.c.list, t0 = performance.now();
    while (J.k < list.length && performance.now() - t0 < ms) { J.fb.facade(fac[list[J.k]], list[J.k], true); J.k++; }
    if (J.k < list.length) return;
    const mesh = new THREE.Mesh(J.fb.g.build(true), this.matNear);
    mesh.castShadow = true; mesh.receiveShadow = true;
    mesh.layers.set(1);                           // main view only; the coarse facades still show in the water
    J.T.group.add(mesh); J.c.near = mesh; this.job = null;
  }
  dropChunk(T, c) {
    T.group.remove(c.near); c.near.geometry.dispose(); c.near = null; if (c.far) c.far.visible = true;
  }
  dropAtlas(T) {
    if (this.job && this.job.T === T) this.job = null;     // its atlas slots go away: abandon the half-built chunk
    for (const c of T.chunks) {
      if (c.near) this.dropChunk(T, c);
      if (c.far) { T.group.remove(c.far); c.far.geometry.dispose(); c.far = null; }
    }
    if (T.farAll) T.farAll.layers.set(0);
    this.pool.release(T.slots); T.slots = null; T.rects = null;
  }
  // walk raster lookup: {z, water} at world (x, y); z = null where blocked, undefined where no data yet
  sample(x, y) {
    const X0 = -3400, Y0 = -1600, TS = 200;
    const i = Math.floor((x - X0) / TS), j = Math.floor((y - Y0) / TS);
    const W = this.walk.get(`t_${i}_${j}`);
    if (!W) return { z: undefined, water: x !== x ? false : undefined };
    const bb = W.bbox, S = W.size;
    const px = Math.min(S - 1, Math.max(0, Math.floor((x - bb[0]) / (bb[2] - bb[0]) * S)));
    const py = Math.min(S - 1, Math.max(0, Math.floor((bb[3] - y) / (bb[3] - bb[1]) * S)));
    const k = (py * S + px) * 4; const c = W.data[k];
    return { z: c ? (c - 1) * 0.04 - 1.0 : null, water: W.data[k + 1] > 127 };
  }
  hasWalkTile(x, y) {
    const i = Math.floor((x + 3400) / 200), j = Math.floor((y + 1600) / 200);
    const n = `t_${i}_${j}`;
    return this.walk.has(n) || !(this.index[n] && this.index[n].walk);
  }
  breakdown(cam) {
    const out = {}; const add = (k, o) => { if (!o) return; let t = 0; o.traverse((x) => { if (x.isMesh && x.visible && x.layers.test(cam.layers)) t += (x.geometry.index ? x.geometry.index.count / 3 : 0) * (x.isInstancedMesh ? x.count : 1); }); out[k] = (out[k] || 0) + Math.round(t); };
    for (const T of this.tiles.values()) { if (T.state !== 'ready') continue; add('base', T.mesh); if (T.hero && T.hero.visible) add('hero', T.hero);
      if (T.farAll && T.farAll.layers.test(cam.layers)) add('far', T.farAll);
      for (const c of T.chunks || []) { if (c.far && c.far.visible) add('far', c.far); if (c.near && c.near.visible) add('near', c.near); } if (T.props && T.props.visible) add('props', T.props); }
    for (const L of this.lites.values()) { if (!L.group) continue; if (L.base.visible) add('lite', L.base); if (L.hero && L.hero.visible) add('liteHero', L.hero); }
    return out;
  }
  stats() {
    let tris = 0, near = 0, n = 0, lite = 0;
    for (const T of this.tiles.values()) {
      if (T.state !== 'ready') continue; n++;
      T.group.traverse((o) => { if (o.isMesh && o.visible) tris += o.geometry.index.count / 3; });
      if (T.slots) near++;
    }
    for (const L of this.lites.values()) if (L.group && L.group.visible) { lite++; L.group.traverse((o) => { if (o.isMesh) tris += o.geometry.index.count / 3; }); }
    return { tiles: n, lite, near, tris: Math.round(tris) };
  }
}
