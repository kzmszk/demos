// Tile streaming.  Every tile has a light far LOD ("lite": simplified roofs/ground/heroes + facade strips with
// procedural windows) that is always loaded, and a full version (static mesh, facades with two LODs, props)
// loaded near the camera.  Walk/water rasters come with the full tile.
import * as THREE from 'three/webgpu';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { buildFarFacades, FacadeBuilder, packAtlas, fillAtlas, chunkFacades } from './facade.js';

// streaming radii (m); a phone gets shorter ones (main.js)
export const RADII = {
  near: 150,                 // tile gets its lightmap atlas (near facades possible)
  chunk: 75,                 // a 50 m chunk of facades gets real openings, sills, shutters, balconies
  props: 280,                // props (poles, chimneys, boats) per tile
  full: 380,                 // full tile
  drop: 500,
  hero: 260,                 // hand-modelled heroes in full detail (else their simplified far LOD)
};

// CPU copies of geometry are let go once it is on the GPU: they were most of the page's memory (about 1 GB of typed
// arrays after a walk to the Rialto, more than a phone gives a tab).  Each mesh is uploaded as soon as it is built
// (three.js's WebGPU backend keeps one buffer per attribute and reads the array again only when the attribute's
// version changes, which never happens to these); the emptied arrays keep their type, which gives the vertex formats.
const bufs = (g) => { const b = Object.values(g.attributes).map((a) => (a.isInterleavedBufferAttribute ? a.data : a)); if (g.index) b.push(g.index); return [...new Set(b)]; };
export function toGPU(obj, backend) {
  if (!backend || !backend.createAttribute || !backend.createIndexAttribute) return;
  obj.traverse((o) => {
    if (!o.isMesh || !o.geometry) return;
    const g = o.geometry;
    for (const a of Object.values(g.attributes)) { const b = a.isInterleavedBufferAttribute ? a.data : a; if (b.array.length) { backend.createAttribute(a); b.array = new b.array.constructor(0); } }
    if (g.index && g.index.array.length) { backend.createIndexAttribute(g.index); g.index.array = new g.index.array.constructor(0); }
  });
}
// dispose() frees only the buffers three.js has drawn with; ones uploaded here and never drawn go too
function release(g, backend) {
  g.dispose();
  if (!backend || !backend.data) return;
  for (const b of bufs(g)) { const d = backend.data.get(b); if (d && d.buffer) { d.buffer.destroy(); backend.data.delete(b); } }
}

// frame-hitch diagnostics: phases slower than 8 ms are logged to window.__perf ([label, ms, t])
const PERF = (globalThis.__perf = globalThis.__perf || []);
export function perfLog(e) { PERF.push(e); if (PERF.length > 4000) PERF.splice(0, 1000); }   // bounded
export function timed(label, fn) { const t = performance.now(); const r = fn(); const dt = performance.now() - t; if (dt > 8) perfLog([label, Math.round(dt), Math.round(t)]); return r; }

// tile binaries are gzip files (pack.mjs): fetched with their bytes counted as they arrive (the loading bar), then
// inflated by the browser.  Plain meshopt data (an older pack) starts with 0xa0/0xe0 and is used as it is.
export async function fetchBin(url, onBytes) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  let buf;
  if (onBytes && r.body) {
    const rd = r.body.getReader(), parts = []; let n = 0;
    for (;;) { const { done, value } = await rd.read(); if (done) break; parts.push(value); n += value.length; onBytes(value.length); }
    buf = new Uint8Array(n); let o = 0; for (const q of parts) { buf.set(q, o); o += q.length; }
  } else buf = new Uint8Array(await r.arrayBuffer());
  if (buf[0] === 0x1f && buf[1] === 0x8b) return new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  return buf.buffer;
}
const fetchJSON = (url) => fetch(url).then((r) => { if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); });
const fetchBlob = (url) => fetch(url).then((r) => { if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.blob(); });
const tileDist = (bb, x, y) => Math.hypot(Math.max(bb[0] - x, 0, x - bb[2]), Math.max(bb[1] - y, 0, y - bb[3]));
// the first view's tiles, fetched while the textures still load: full tiles within `full` m of (x, y), far LOD within
// `lite` m.  Returns the promises by URL (handed to Tiles, which takes them instead of fetching again) and the bytes.
export function prefetch(base, index, x, y, full, lite, onBytes) {
  const pre = new Map(); let bytes = 0;
  for (const [n, t] of Object.entries(index)) {
    const d = tileDist(t.bbox, x, y);
    if (d < full) {
      pre.set(`${base}/${n}.json`, fetchJSON(`${base}/${n}.json`));
      pre.set(`${base}/${n}.bin`, fetchBin(`${base}/${n}.bin`, onBytes)); bytes += t.bytes || 0;
      if (t.walk) pre.set(`${base}/${n}.walk.png`, fetchBlob(`${base}/${n}.walk.png`));
    }
    if (t.lite && d < lite) { pre.set(`${base}/${n}.lite.bin`, fetchBin(`${base}/${n}.lite.bin`, onBytes)); bytes += t.lite.bytes || 0; }
  }
  for (const v of pre.values()) v.catch(() => {});              // a failure surfaces where the tile is loaded
  return { pre, bytes };
}

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
    this.R = { ...RADII, ...(o.radii || {}) };
    this.pre = o.pre || new Map();        // prefetched files by URL (see prefetch)
    this.cap = null;                      // {x, y, full, lite}: while the first view loads, nothing beyond it (main.js)
    this.chunkMs = 4.0;                   // time per frame for detailed facades (more while the loading screen is up)
    this.walk = new Map();      // name -> {data: Uint8Array of (height code, water) pairs, size, bbox}
  }
  async init(index) {
    await MeshoptDecoder.ready;
    this.index = index || (await (await fetch(`${this.base}/tiles.json`)).json()).tiles;
  }
  dist(bb, p) {
    const dx = Math.max(bb[0] - p.x, 0, p.x - bb[2]), dy = Math.max(bb[1] - p.y, 0, p.y - bb[3]);
    return Math.hypot(dx, dy);
  }
  // a prefetched file if there is one (used once), else a fetch
  take(url, get) { const p = this.pre.get(url); if (p) { this.pre.delete(url); return p; } return get(url); }
  update(cam) {
    const p = cam.position, cap = this.cap;
    const all = Object.entries(this.index).map(([n, t]) => [n, t, this.dist(t.bbox, p)]).sort((a, b) => a[2] - b[2]);
    const capD = (t) => (cap ? tileDist(t.bbox, cap.x, cap.y) : 0);
    // full tiles near the camera (the walk raster needs the tile we stand on first)
    for (const [n, t, d] of all) {
      if (cap && capD(t) >= cap.full) continue;
      if (d < this.R.full && !this.tiles.has(n) && this.loading < 3) { this.tiles.set(n, { state: 'loading' }); this.loading++; this.load(n).catch((e) => console.error(n, e)).finally(() => this.loading--); }
    }
    // far LOD everywhere, nearest first
    for (const [n, t, d] of all) {
      if (!t.lite || this.lites.has(n) || this.liteLoading >= 6 || (cap && capD(t) >= cap.lite)) continue;
      this.lites.set(n, { state: 'loading' }); this.liteLoading++;
      this.loadLite(n, t).catch((e) => console.error('lite', n, e)).finally(() => this.liteLoading--);
    }
    for (const [n, T] of this.tiles) {
      if (T.state === 'ready' && this.dist(T.meta.bbox, p) > this.R.drop) this.drop(n, T);
    }
    // a tile shows its far LOD until the full version is in; heroes switch to full detail within R.hero.
    // layers: 0 = everyone, 1 = main view (and shadows) only, 2 = water reflection only
    for (const [n, L] of this.lites) {
      if (!L.group) continue;
      const T = this.tiles.get(n); const full = !!(T && T.state === 'ready');
      L.base.visible = !full;
      const heroNear = full && T.hero && this.dist(T.meta.bbox, p) < this.R.hero;
      if (T && T.hero) T.hero.visible = heroNear;
      if (L.hero) { L.hero.visible = true; L.hero.traverse((o) => o.layers.set(heroNear ? 2 : 0)); }
    }
    // near facades: tiles within R.near own a lightmap atlas; chunks within R.chunk get detailed geometry.
    // A chunk is built a few facades per frame (~4 ms), so walking never stalls on it; one atlas per frame.
    if (this.job) timed('chunk-step', () => this.stepChunk(this.chunkMs));
    let budget = 1, propsBudget = 1;
    for (const [n, t, d] of all) {
      const T = this.tiles.get(n);
      if (!T || T.state !== 'ready' || !T.chunks) continue;
      if (d < this.R.near && !T.slots && budget > 0) { timed('atlas', () => this.makeAtlas(T)); budget--; }
      if (this.props && !T.props && d < this.R.props && propsBudget-- > 0) {
        const pg = T.props = timed('props', () => this.props.build(T.SP)); pg.traverse((o) => o.layers.set(1)); T.group.add(pg); toGPU(pg, this.backend);
      } else if (T.props && d > this.R.props + 60) { T.group.remove(T.props); T.props.traverse((o) => { if (o.isMesh) release(o.geometry, this.backend); }); T.props = null; }
      if (T.props) T.props.visible = d < this.R.props;
      if (!T.slots) continue;
      for (const c of T.chunks) {
        const dc = this.dist(c.bbox, p);
        if (dc < this.R.chunk && !c.near && !this.job) this.job = { T, c, fb: new FacadeBuilder(this.mats, { rects: T.rects, slots: T.slots }), k: 0 };
        if (c.near) {
          const on = dc < this.R.chunk + 25;
          c.near.visible = on; c.far.visible = !on;
          if (dc > this.R.chunk + 80) this.dropChunk(T, c);
        }
      }
    }
    for (const T of this.tiles.values()) if (T.slots && this.dist(T.meta.bbox, p) > this.R.near + 60) this.dropAtlas(T);
  }
  // work still to do for the view at p: tiles in flight, near tiles without their lightmap atlas, props or detailed
  // facades (the loading screen stays up until this is 0)
  pending(p) {
    let n = this.loading + this.liteLoading + (this.job ? 1 : 0);
    const cap = this.cap;
    if (cap) for (const [name, t] of Object.entries(this.index)) {        // the first view's tiles not even started
      const d = tileDist(t.bbox, cap.x, cap.y);
      if (d < cap.full && !this.tiles.has(name)) n++;
      if (t.lite && d < cap.lite && !this.lites.has(name)) n++;
    }
    for (const T of this.tiles.values()) {
      if (T.state !== 'ready') { n++; continue; }
      const d = this.dist(T.meta.bbox, p);
      if (this.index[T.name] && this.index[T.name].walk && !this.walk.has(T.name)) n++;
      if (!T.chunks) continue;
      if (d < this.R.near && !T.slots && !this.poolFull) n++;
      if (this.props && d < this.R.props && !T.props) n++;
      if (T.slots) for (const c of T.chunks) if (!c.near && this.dist(c.bbox, p) < this.R.chunk) n++;
    }
    return n;
  }
  async loadLite(n, t) {
    const bin = await this.take(`${this.base}/${n}.lite.bin`, (u) => fetchBin(u));
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
    this.scene.add(group); toGPU(group, this.backend);
    this.lites.set(n, { state: 'ready', group, base, hero: S['h:pos'] ? hero : null });
  }
  async load(n) {
    const [meta, bin] = await Promise.all([this.take(`${this.base}/${n}.json`, fetchJSON), this.take(`${this.base}/${n}.bin`, (u) => fetchBin(u))]);
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
        let gg = g;
        if (idx !== S.idx) {         // the hero split: same vertices, own index (a clone would copy them, CPU and GPU)
          gg = new THREE.BufferGeometry();
          for (const k in g.attributes) gg.setAttribute(k, g.attributes[k]);
          gg.boundingBox = g.boundingBox; gg.boundingSphere = g.boundingSphere;
        }
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
    if (this.index[n] && this.index[n].walk) this.loadWalk(n).catch((e) => console.error('walk', n, e));
    // kept: the facade light for atlases made later, the prop instances for props made when the tile comes near
    T.S = { girr: S.girr, girrn: S.girrn }; T.SP = { ipos: S.ipos, isct: S.isct, icol: S.icol, iirr: S.iirr, iirrn: S.iirrn };
    this.scene.add(T.group); toGPU(T.group, this.backend);
    this.tiles.set(n, T);
    this.onLoad && this.onLoad(T);
  }
  async loadWalk(n) {
    const blob = await this.take(`${this.base}/${n}.walk.png`, fetchBlob);
    const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
    const c = new OffscreenCanvas(bmp.width, bmp.height); const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(bmp, 0, 0);
    const data = timed('walk:png', () => {
      const rgba = g.getImageData(0, 0, bmp.width, bmp.height).data; const d = new Uint8Array(rgba.length / 2);
      for (let i = 0, j = 0; i < rgba.length; i += 4, j += 2) { d[j] = rgba[i]; d[j + 1] = rgba[i + 1]; }
      return d;
    });
    this.walk.set(n, { data, size: bmp.width, bbox: this.index[n].bbox });
  }
  drop(n, T) {
    if (T.slots) this.dropAtlas(T);
    this.scene.remove(T.group);
    const gs = new Set(); T.group.traverse((o) => { if (o.isMesh && o.geometry) gs.add(o.geometry); });
    for (const g of gs) release(g, this.backend);
    this.tiles.delete(n);
    this.walk.delete(n);
  }
  makeAtlas(T) {
    const fac = T.meta.fac;
    const { rects, pages } = packAtlas(fac);
    const slots = this.pool.alloc(pages);
    this.poolFull = !slots;
    if (!slots) return;
    this.pool.write(slots, fillAtlas(fac, rects, pages, T.S.girr), 'day');
    this.pool.write(slots, fillAtlas(fac, rects, pages, T.S.girrn), 'night');
    T.slots = slots; T.rects = rects;
    // near: the merged coarse facades stay for the water reflection only; the main view gets them per chunk
    for (const c of T.chunks) {
      c.far = new THREE.Mesh(buildFarFacades(T.meta, T.S.girr, T.S.girrn, this.mats, c.list), this.matStatic);
      c.far.castShadow = true; c.far.receiveShadow = true; c.far.layers.set(1); T.group.add(c.far); toGPU(c.far, this.backend);
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
    J.T.group.add(mesh); J.c.near = mesh; this.job = null; toGPU(mesh, this.backend);
  }
  dropChunk(T, c) {
    T.group.remove(c.near); release(c.near.geometry, this.backend); c.near = null; if (c.far) c.far.visible = true;
  }
  dropAtlas(T) {
    if (this.job && this.job.T === T) this.job = null;     // its atlas slots go away: abandon the half-built chunk
    for (const c of T.chunks) {
      if (c.near) this.dropChunk(T, c);
      if (c.far) { T.group.remove(c.far); release(c.far.geometry, this.backend); c.far = null; }
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
    const k = (py * S + px) * 2; const c = W.data[k];
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
