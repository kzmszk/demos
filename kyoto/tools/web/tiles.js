// Tile streaming.  The far LOD ("lite": simplified buildings + terrain, lit by the bake) loads by distance; the full
// tile (buildings 'b', ground 'g', water 'w' — one draw each) near the camera, with its surface raster (into the
// ground program's pool) and its walk map.
import * as THREE from 'three/webgpu';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { TILE } from './kyomat.js';

export const RADII = { full: 420, drop: 520, lite: 2600, liteDrop: 2900 };

// CPU copies go once the GPU has them (see the Venice notes: three.js keeps every array otherwise)
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
function release(g, backend) {
  g.dispose();
  if (!backend || !backend.data) return;
  for (const b of bufs(g)) { const d = backend.data.get(b); if (d && d.buffer) { d.buffer.destroy(); backend.data.delete(b); } }
}

const PERF = (globalThis.__perf = globalThis.__perf || []);
export function perfLog(e) { PERF.push(e); if (PERF.length > 4000) PERF.splice(0, 1000); }
export function timed(label, fn) { const t = performance.now(); const r = fn(); const dt = performance.now() - t; if (dt > 8) perfLog([label, Math.round(dt), Math.round(t)]); return r; }

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

export function prefetch(base, index, x, y, full, lite, onBytes) {
  const pre = new Map(); let bytes = 0;
  for (const [n, t] of Object.entries(index)) {
    const d = tileDist(t.bbox, x, y);
    if (d < full) {
      pre.set(`${base}/${n}.json`, fetchJSON(`${base}/${n}.json`));
      pre.set(`${base}/${n}.bin`, fetchBin(`${base}/${n}.bin`, onBytes)); bytes += t.bytes || 0;
      if (t.walk) pre.set(`${base}/${n}.walk.png`, fetchBlob(`${base}/${n}.walk.png`));
      if (t.surf) pre.set(`${base}/${n}.surf.png`, fetchBlob(`${base}/${n}.surf.png`));
    }
    if (t.lite && d < lite) { pre.set(`${base}/${n}.lite.bin`, fetchBin(`${base}/${n}.lite.bin`, onBytes)); bytes += t.lite.bytes || 0; }
  }
  for (const v of pre.values()) v.catch(() => {});
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
async function pngData(blob) {
  const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  const c = new OffscreenCanvas(bmp.width, bmp.height); const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(bmp, 0, 0);
  return { w: bmp.width, h: bmp.height, rgba: g.getImageData(0, 0, bmp.width, bmp.height).data };
}

export class Tiles {
  constructor(scene, o) {
    Object.assign(this, o); this.scene = scene; this.tiles = new Map(); this.lites = new Map(); this.loading = 0; this.liteLoading = 0;
    this.R = { ...RADII, ...(o.radii || {}) };
    this.pre = o.pre || new Map();
    this.cap = null;
    this.walk = new Map();
    this.onLoad = null;
  }
  async init(index) { await MeshoptDecoder.ready; this.index = index; }
  dist(bb, p) { return tileDist(bb, p.x, p.y); }
  take(url, get) { const p = this.pre.get(url); if (p) { this.pre.delete(url); return p; } return get(url); }
  update(cam) {
    const p = cam.position, cap = this.cap;
    const all = Object.entries(this.index).map(([n, t]) => [n, t, this.dist(t.bbox, p)]).sort((a, b) => a[2] - b[2]);
    const capD = (t) => (cap ? tileDist(t.bbox, cap.x, cap.y) : 0);
    for (const [n, t, d] of all) {
      if (cap && capD(t) >= cap.full) continue;
      if (d < this.R.full && !this.tiles.has(n) && this.loading < 3) { this.tiles.set(n, { state: 'loading' }); this.loading++; this.load(n).catch((e) => { console.error(n, e); }).finally(() => this.loading--); }
    }
    for (const [n, t, d] of all) {
      if (!t.lite || this.lites.has(n) || this.liteLoading >= 6 || d > this.R.lite || (cap && capD(t) >= cap.lite)) continue;
      this.lites.set(n, { state: 'loading' }); this.liteLoading++;
      this.loadLite(n, t).catch((e) => console.error('lite', n, e)).finally(() => this.liteLoading--);
    }
    for (const [n, T] of this.tiles) if (T.state === 'ready' && this.dist(T.meta.bbox, p) > this.R.drop) this.drop(n, T);
    for (const [n, L] of this.lites) {
      if (L.state !== 'ready') continue;
      if (this.dist(this.index[n].bbox, p) > this.R.liteDrop) { this.scene.remove(L.group); L.group.traverse((o) => { if (o.isMesh) release(o.geometry, this.backend); }); this.lites.delete(n); if (this.trees) this.trees.dropTile(n); continue; }
      const T = this.tiles.get(n); L.group.visible = !(T && T.state === 'ready');
    }
  }
  pending(p) {
    let n = this.loading + this.liteLoading;
    const cap = this.cap;
    if (cap) for (const [name, t] of Object.entries(this.index)) {
      const d = tileDist(t.bbox, cap.x, cap.y);
      if (d < cap.full && !this.tiles.has(name)) n++;
      if (t.lite && d < cap.lite && !this.lites.has(name)) n++;
    }
    for (const T of this.tiles.values()) if (T.state !== 'ready') n++;
    return n;
  }
  async loadLite(n, t) {
    const bin = await this.take(`${this.base}/${n}.lite.bin`, (u) => fetchBin(u));
    const S = timed('lite:decode', () => decodeStreams(bin, t.lite.streams));
    const group = new THREE.Group(); group.name = n + ':lite';
    if (S.pos) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(S.pos.buffer), 4, true));
      g.setAttribute('c0', new THREE.BufferAttribute(S.c0, 4, true));
      g.setAttribute('c1', new THREE.BufferAttribute(S.c1, 4, true));
      g.setAttribute('irr', new THREE.BufferAttribute(S.irr, 4, true));
      g.setIndex(new THREE.BufferAttribute(S.idx, 1));
      g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 1, 1));
      g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
      const m = new THREE.Mesh(g, this.matLite);
      m.position.set(...t.lite.qmin); m.scale.setScalar(t.lite.qext);
      m.castShadow = true; m.receiveShadow = false; m.matrixAutoUpdate = false; m.updateMatrix();
      group.add(m);
    }
    this.scene.add(group); toGPU(group, this.backend);
    if (this.trees) this.trees.addTile(n, S);
    this.lites.set(n, { state: 'ready', group });
  }
  async load(n) {
    const t = this.index[n];
    const [meta, bin] = await Promise.all([this.take(`${this.base}/${n}.json`, fetchJSON), this.take(`${this.base}/${n}.bin`, (u) => fetchBin(u))]);
    const T = { name: n, meta, state: 'ready', group: new THREE.Group() };
    T.group.name = n;
    let off = 0;
    const mats = { b: this.matCity, g: this.matGround, w: this.matWater };
    for (const gr of meta.groups) {
      const S = timed('full:decode', () => decodeStreams(bin, gr.streams));
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(S.pos.buffer), 4, true));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int8Array(S.nrm.buffer), 4, true));
      g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(S.uv.buffer), 2));
      g.setAttribute('c0', new THREE.BufferAttribute(S.c0, 4, true));
      g.setAttribute('c1', new THREE.BufferAttribute(S.c1, 4, true));
      g.setAttribute('irr', new THREE.BufferAttribute(S.irr, 4, true));
      g.setIndex(new THREE.BufferAttribute(S.idx, 1));
      g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 1, 1));
      g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
      const m = new THREE.Mesh(g, mats[gr.name]);
      m.position.set(...meta.qmin); m.scale.setScalar(meta.qext);
      m.castShadow = gr.name !== 'w'; m.receiveShadow = true; m.matrixAutoUpdate = false; m.updateMatrix();
      T.group.add(m);
    }
    if (t.walk) this.loadWalk(n).catch((e) => console.error('walk', n, e));
    if (t.surf && this.pool) this.loadSurf(n, t).catch((e) => console.error('surf', n, e));
    this.scene.add(T.group); toGPU(T.group, this.backend);
    this.tiles.set(n, T);
    this.onLoad && this.onLoad(T);
  }
  async loadSurf(n, t) {
    const { w, rgba } = await pngData(await this.take(`${this.base}/${n}.surf.png`, fetchBlob));
    const d = new Uint8Array(w * w);
    // the PNG's row 0 is north; the pool's row 0 is the tile's south edge (texture v = 0)
    for (let y = 0; y < w; y++) for (let x = 0; x < w; x++) d[(w - 1 - y) * w + x] = rgba[(y * w + x) * 4];
    if (this.tiles.has(n)) this.pool.put(n, t.tile[0], t.tile[1], d);
  }
  async loadWalk(n) {
    const { w, rgba } = await pngData(await this.take(`${this.base}/${n}.walk.png`, fetchBlob));
    const d = new Uint8Array(w * w * 3);
    for (let i = 0, j = 0; i < rgba.length; i += 4, j += 3) { d[j] = rgba[i]; d[j + 1] = rgba[i + 1]; d[j + 2] = rgba[i + 2]; }
    this.walk.set(n, { data: d, size: w, bbox: this.index[n].bbox });
  }
  drop(n, T) {
    this.scene.remove(T.group);
    T.group.traverse((o) => { if (o.isMesh && o.geometry) release(o.geometry, this.backend); });
    this.tiles.delete(n); this.walk.delete(n);
    if (this.pool) this.pool.drop(n);
  }
  // walk map lookup at world (x, y): {z, blocked, water, surf}; z undefined where the tile is not in yet
  sample(x, y) {
    const i = Math.floor((x - TILE.X0) / TILE.S), j = Math.floor((y - TILE.Y0) / TILE.S);
    const W = this.walk.get(`t_${i}_${j}`);
    if (!W) return { z: undefined };
    const bb = W.bbox, S = W.size;
    const px = Math.min(S - 1, Math.max(0, Math.floor((x - bb[0]) / (bb[2] - bb[0]) * S)));
    const py = Math.min(S - 1, Math.max(0, Math.floor((bb[3] - y) / (bb[3] - bb[1]) * S)));
    const k = (py * S + px) * 3, b = W.data[k + 2];
    return { z: (W.data[k] * 256 + W.data[k + 1]) / 100 - 20, blocked: b >= 128, water: (b & 64) !== 0, covered: (b & 32) !== 0, surf: b & 31 };
  }
  stats() {
    let tris = 0, n = 0, lite = 0;
    for (const T of this.tiles.values()) { if (T.state !== 'ready') continue; n++; T.group.traverse((o) => { if (o.isMesh && o.visible) tris += o.geometry.index.count / 3; }); }
    for (const L of this.lites.values()) if (L.group && L.group.visible) { lite++; L.group.traverse((o) => { if (o.isMesh) tris += o.geometry.index.count / 3; }); }
    return { tiles: n, lite, tris: Math.round(tris) };
  }
}
