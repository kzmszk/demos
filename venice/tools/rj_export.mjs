// Tiles as plain glb for rojibura (a 3D city for people and AIs, ~/work/rojibura docs/prd.md 3.8), which draws
// glTF with WebGL and has none of this viewer's shaders.  Per tile: the static mesh (ground, copings, bridges,
// heroes) and every facade in full detail (FacadeBuilder, as the viewer builds them within 75 m), in 50 m chunks
// (one mesh each, so three.js culls what is off screen or outside the shadow), coloured per vertex: material albedo (tinted materials times their tint) times an occlusion term from the day
// bake.  The sun is rojibura's own, so only the bake's darkening is kept, not its light.  Y up (x, z, -y), the
// Campanile at the origin as here; quantised and meshopt-compressed (three.js GLTFLoader + MeshoptDecoder).
//
//   node rj_export.mjs OUTDIR TILE [TILE ...]        e.g. node rj_export.mjs ../public/rj/2026-11-01 t_16_7 t_16_8
//
// Reads ../public/data/island (the packed tiles) and ../public/data/materials.json.  No props or textures yet.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { Document, NodeIO } from '@gltf-transform/core';
import { EXTMeshoptCompression, KHRMeshQuantization } from '@gltf-transform/extensions';
import { meshopt, quantize } from '@gltf-transform/functions';
import { MeshoptEncoder } from 'meshoptimizer';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { FacadeBuilder, LM, fillAtlas, packAtlas } from './web/facade.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ISLAND = join(HERE, '../public/data/island');
const MATS = JSON.parse(readFileSync(join(HERE, '../public/data/materials.json'), 'utf8'));
// tinted materials: their texture layer is neutral and the vertex tint (c0) gives the colour (citymat.js)
const TINTED = new Set(MATS.mats.filter((m) => m.layer >= 0 && MATS.layers[m.layer].neutral).map((m) => m.id));
const ALBEDO = MATS.mats.map((m) => m.albedo);
// day irradiance (RGBM, citymat.js rgbm) that counts as open sky: brighter keeps full colour, darker is occluded
const OPEN_SKY = 0.3, OCC_MIN = 0.3, OCC_POW = 0.7;

const s2l = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

function readBin(path) {
  const b = readFileSync(path);
  return b[0] === 0x1f && b[1] === 0x8b ? gunzipSync(b) : b;
}
function decodeStreams(bin, streams) {
  const src = new Uint8Array(bin.buffer, bin.byteOffset, bin.byteLength), S = {};
  for (const s of streams) {
    const part = src.subarray(s.off, s.off + s.len);
    if (s.kind === 'i') { const out = new Uint32Array(s.count); MeshoptDecoder.decodeIndexBuffer(new Uint8Array(out.buffer), s.count, 4, part); S[s.name] = out; }
    else { const out = new Uint8Array(s.count * s.stride); MeshoptDecoder.decodeVertexBuffer(out, s.count, s.stride, part); S[s.name] = out; }
  }
  return S;
}

// vertex colour (linear rgb) from c0 (tint), c1 (material id), the RGBM day irradiance and a geometric ao
function colour(c0, c1, k, irr, ir, ao) {
  const id = c1[k], a = ALBEDO[id] || ALBEDO[0];
  let r = a[0], g = a[1], b = a[2];
  if (TINTED.has(id)) {
    let tr = s2l(c0[k]), tg = s2l(c0[k + 1]), tb = s2l(c0[k + 2]);
    const l = lum(tr, tg, tb); tr += (l - tr) * 0.22; tg += (l - tg) * 0.22; tb += (l - tb) * 0.22;
    // the albedo of a tinted material is that of its neutral texture: scale the tint to it
    r *= tr / 0.62 * 0.9; g *= tg / 0.58 * 0.9; b *= tb / 0.52 * 0.9;
  }
  const m = irr[ir + 3] / 255 * 8;
  const e = lum(irr[ir] / 255 * m, irr[ir + 1] / 255 * m, irr[ir + 2] / 255 * m);
  const occ = Math.max(OCC_MIN, Math.min(1, (e / OPEN_SKY) ** OCC_POW)) * ao;
  return [Math.min(1, r * occ), Math.min(1, g * occ), Math.min(1, b * occ)];
}

class Out {
  constructor() { this.P = []; this.N = []; this.C = []; this.I = []; this.n = 0; }
  vertex(x, y, z, nx, ny, nz, c) {
    // the viewer's frame (x east, y north, z up) to glTF's (y up): (x, z, -y)
    this.P.push(x, z, -y); const l = Math.hypot(nx, ny, nz) || 1; this.N.push(nx / l, nz / l, -ny / l); this.C.push(...c);
    return this.n++;
  }
}

function exportTile(name) {
  const meta = JSON.parse(readFileSync(join(ISLAND, `${name}.json`), 'utf8'));
  const S = decodeStreams(readBin(join(ISLAND, `${name}.bin`)), meta.streams);
  const out = new Out();
  // static mesh: positions uint16 in a cube (qmin + v / 65535 * qext), normals snorm8
  if (S.pos) {
    const pos = new Uint16Array(S.pos.buffer), nrm = new Int8Array(S.nrm.buffer);
    const q = Array.isArray(meta.qext) ? Math.max(...meta.qext) : meta.qext, [ox, oy, oz] = meta.qmin;
    const n = pos.length / 4, base = out.n;
    for (let i = 0; i < n; i++) {
      out.vertex(ox + pos[i * 4] / 65535 * q, oy + pos[i * 4 + 1] / 65535 * q, oz + pos[i * 4 + 2] / 65535 * q,
        nrm[i * 4] / 127, nrm[i * 4 + 1] / 127, nrm[i * 4 + 2] / 127, colour(S.c0, S.c1, i * 4 + 0, S.irr, i * 4, 1));
    }
    for (const v of S.idx) out.I.push(base + v);
  }
  // facades in full detail, lit from the baked facade grids through the same atlas the viewer makes
  if (meta.fac && meta.fac.length) {
    const { rects, pages } = packAtlas(meta.fac);
    const atlas = fillAtlas(meta.fac, rects, pages, S.girr);
    const fb = new FacadeBuilder(MATS.mats, { rects, slots: atlas.map((_, i) => i) });
    for (let i = 0; i < meta.fac.length; i++) fb.facade(meta.fac[i], i, true);
    const g = fb.g, base = out.n, irr = new Uint8Array(4);
    for (let i = 0; i < g.n; i++) {
      const page = atlas[Math.round(g.U2[i * 3 + 2])];
      const px = Math.min(LM - 1, Math.max(0, Math.floor(g.U2[i * 3] * LM))), py = Math.min(LM - 1, Math.max(0, Math.floor(g.U2[i * 3 + 1] * LM)));
      irr.set(page.subarray((py * LM + px) * 4, (py * LM + px) * 4 + 4));
      out.vertex(g.P[i * 3], g.P[i * 3 + 1], g.P[i * 3 + 2], g.N[i * 4] / 127, g.N[i * 4 + 1] / 127, g.N[i * 4 + 2] / 127,
        colour(g.C0, g.C1, i * 4, irr, 0, g.AX[i * 2 + 1]));
    }
    for (let k = 0; k < g.ni; k++) out.I.push(base + g.idx[k]);
  }
  return out;
}

// triangles by the CHUNK m cell of their centroid (glTF's x, -z), each cell with its own vertices
const CHUNK = 50;
function chunks(out) {
  const cells = new Map();
  for (let t = 0; t < out.I.length; t += 3) {
    const a = out.I[t] * 3, b = out.I[t + 1] * 3, c = out.I[t + 2] * 3;
    const cx = (out.P[a] + out.P[b] + out.P[c]) / 3, cz = (out.P[a + 2] + out.P[b + 2] + out.P[c + 2]) / 3;
    const key = `${Math.floor(cx / CHUNK)}_${Math.floor(-cz / CHUNK)}`;
    let cell = cells.get(key);
    if (!cell) cells.set(key, (cell = { map: new Map(), P: [], N: [], C: [], I: [] }));
    for (const v of [out.I[t], out.I[t + 1], out.I[t + 2]]) {
      let k = cell.map.get(v);
      if (k === undefined) {
        k = cell.map.size; cell.map.set(v, k);
        cell.P.push(out.P[v * 3], out.P[v * 3 + 1], out.P[v * 3 + 2]); cell.N.push(out.N[v * 3], out.N[v * 3 + 1], out.N[v * 3 + 2]); cell.C.push(out.C[v * 3], out.C[v * 3 + 1], out.C[v * 3 + 2]);
      }
      cell.I.push(k);
    }
  }
  return cells;
}

async function write(path, name, out) {
  const doc = new Document();
  const buffer = doc.createBuffer();
  const acc = (type, array) => doc.createAccessor().setType(type).setArray(array).setBuffer(buffer);
  const material = doc.createMaterial('venice').setBaseColorFactor([1, 1, 1, 1]).setRoughnessFactor(0.92).setMetallicFactor(0);
  const scene = doc.createScene(name);
  for (const [key, cell] of chunks(out)) {
    const prim = doc.createPrimitive()
      .setAttribute('POSITION', acc('VEC3', new Float32Array(cell.P)))
      .setAttribute('NORMAL', acc('VEC3', new Float32Array(cell.N)))
      .setAttribute('COLOR_0', acc('VEC3', new Float32Array(cell.C)))
      .setIndices(acc('SCALAR', new Uint32Array(cell.I)))
      .setMaterial(material);
    scene.addChild(doc.createNode(`${name}_${key}`).setMesh(doc.createMesh(`${name}_${key}`).addPrimitive(prim)));
  }
  await MeshoptEncoder.ready;
  await doc.transform(quantize({ quantizePosition: 16, quantizeNormal: 8, quantizeColor: 8 }), meshopt({ encoder: MeshoptEncoder, level: 'medium' }));
  const io = new NodeIO().registerExtensions([EXTMeshoptCompression, KHRMeshQuantization]).registerDependencies({ 'meshopt.encoder': MeshoptEncoder });
  const glb = await io.writeBinary(doc);
  writeFileSync(path, glb);
  return glb.byteLength;
}

const [outDir, ...tiles] = process.argv.slice(2);
if (!outDir || !tiles.length) { console.error('usage: node rj_export.mjs OUTDIR TILE [TILE ...]'); process.exit(2); }
await MeshoptDecoder.ready;
mkdirSync(outDir, { recursive: true });
for (const t of tiles) {
  const t0 = performance.now();
  const out = exportTile(t);
  const bytes = await write(join(outDir, `${t}.glb`), t, out);
  console.log(`${t}.glb: ${out.n} vertices, ${out.I.length / 3} triangles, ${(bytes / 1048576).toFixed(1)} MB, ${Math.round(performance.now() - t0)} ms`);
}
