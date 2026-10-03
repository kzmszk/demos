// pack.mjs — corner soup (from vb/bake.export) -> welded (irradiance averaged), chunked,
// meshopt-compressed zone.  usage: node pack.mjs <in-base> <out-dir> <zone> [cell=128] [--weld-mm=2]
// Vertex streams per chunk: pos f32x3 | nrm i8x4 (xyz, w = detail texture id) |
// irr f16x4 | col u8x4 (sRGB albedo, a = roughness*127 + metal*128) | uv f32x2 (art only)
import fs from 'fs'; import path from 'path';
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';
import { matInfo, drawClass } from './mats.mjs';
await MeshoptEncoder.ready; await MeshoptSimplifier.ready;
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const flags = Object.fromEntries(process.argv.slice(2).filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const [inBase, outDir, zone, cellS = '128'] = args;
const CELL = +cellS; const WELD = (+(flags['weld-mm'] ?? 2)) / 1000;
const SIMP = +(flags.simp ?? 0.02);          // absolute geometric error in metres (0 = off)
let simpIn = 0, simpOut = 0;
const header = JSON.parse(fs.readFileSync(inBase + '.json'));
const raw = fs.readFileSync(inBase + '.raw');
const f32 = (r) => new Float32Array(raw.buffer.slice(raw.byteOffset + r[0], raw.byteOffset + r[0] + r[1]));
const lin2srgb = (c) => Math.round(255 * (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055));
const toHalf = (() => {
  const f = new Float32Array(1), u = new Uint32Array(f.buffer);
  return (v) => { f[0] = v; const x = u[0]; const s = (x >>> 16) & 0x8000; const e = ((x >>> 23) & 0xff) - 112; const m = x & 0x7fffff;
    if (e <= 0) return s; if (e >= 31) return s | 0x7bff; return s | (e << 10) | Math.min(0x3ff, (m + 0x1000) >>> 13); };
})();

// gather triangles per (class, cell)
const buckets = new Map();
for (const g of header) {
  const P = f32(g.p), N = f32(g.n), C = f32(g.c), U = f32(g.u);
  const mi = matInfo(g.mat); const cls = drawClass(g.mat);
  const col = [lin2srgb(mi.albedo[0]), lin2srgb(mi.albedo[1]), lin2srgb(mi.albedo[2]), Math.round(mi.rough * 127) + (mi.metal ? 128 : 0)];
  for (let t = 0; t < g.count / 3; t++) {
    const i = t * 3;
    const cx = (P[i * 3] + P[i * 3 + 3] + P[i * 3 + 6]) / 3, cy = (P[i * 3 + 1] + P[i * 3 + 4] + P[i * 3 + 7]) / 3;
    const k = cls + '|' + Math.floor(cx / CELL) + ',' + Math.floor(cy / CELL);
    let b = buckets.get(k); if (!b) buckets.set(k, b = { cls, src: [] });
    b.src.push({ P, N, C, U, t, col, tex: mi.tex, lock: g.mat === 'statue_marble' });
  }
}
const chunks = []; const blobs = []; let off = 0;
const push = (buf) => { blobs.push(Buffer.from(buf.buffer, buf.byteOffset, buf.byteLength)); const r = [off, buf.byteLength]; off += buf.byteLength; return r; };
for (const [key, b] of buckets) {
  const hasUV = b.cls.startsWith('art:');
  const map = new Map(); const acc = []; const idx = new Uint32Array(b.src.length * 3); let w = 0;
  for (const s of b.src) for (let c = 0; c < 3; c++) {
    const i = s.t * 3 + c; const P = s.P, N = s.N;
    const nx = Math.round(N[i * 3] * 127), ny = Math.round(N[i * 3 + 1] * 127), nz = Math.round(N[i * 3 + 2] * 127);
    let k = `${Math.round(P[i * 3] / WELD)},${Math.round(P[i * 3 + 1] / WELD)},${Math.round(P[i * 3 + 2] / WELD)},${nx},${ny},${nz},${s.tex},${s.col[0]},${s.col[1]},${s.col[2]},${s.col[3]}`;
    if (hasUV) k += `,${s.U[i * 2].toFixed(4)},${s.U[i * 2 + 1].toFixed(4)}`;
    let v = map.get(k);
    if (v === undefined) {
      v = acc.length; map.set(k, v);
      acc.push({ p: [P[i * 3], P[i * 3 + 1], P[i * 3 + 2]], n: [nx, ny, nz], tex: s.tex, col: s.col, uv: hasUV ? [s.U[i * 2], s.U[i * 2 + 1]] : null, irr: [0, 0, 0, 0], k: 0, lock: s.lock });
    }
    const a = acc[v]; a.irr[0] += s.C[i * 4]; a.irr[1] += s.C[i * 4 + 1]; a.irr[2] += s.C[i * 4 + 2]; a.irr[3] += s.C[i * 4 + 3]; a.k++;
    idx[w++] = v;
  }
  // attribute-aware simplification: the bake densified flat surfaces; merge triangles back where neither the
  // shape (2 cm) nor the baked light (irradiance) nor the uv would change visibly; chunk borders are locked
  let ix = idx;
  if (SIMP > 0 && acc.length > 64) {
    const P3 = new Float32Array(acc.length * 3), AT = new Float32Array(acc.length * (hasUV ? 5 : 3));
    acc.forEach((a, v) => { P3.set(a.p, v * 3); const ir = [a.irr[0] / a.k, a.irr[1] / a.k, a.irr[2] / a.k];
      const st = hasUV ? 5 : 3; AT[v * st] = Math.sqrt(ir[0]); AT[v * st + 1] = Math.sqrt(ir[1]); AT[v * st + 2] = Math.sqrt(ir[2]); if (hasUV) { AT[v * st + 3] = a.uv[0]; AT[v * st + 4] = a.uv[1]; } });
    const w = hasUV ? [0.6, 0.6, 0.6, 2, 2] : [0.6, 0.6, 0.6];
    const lock = new Uint8Array(acc.length); let anyLock = false; acc.forEach((a, v) => { if (a.lock) { lock[v] = 1; anyLock = true; } });
    const [out] = MeshoptSimplifier.simplifyWithAttributes(idx, P3, 3, AT, hasUV ? 5 : 3, w, anyLock ? lock : null, 0, SIMP, ['LockBorder', 'ErrorAbsolute']);
    ix = out; simpIn += idx.length / 3; simpOut += out.length / 3;
  }
  const [remap, vc] = MeshoptEncoder.reorderMesh(ix, true, true);
  const pos = new Uint16Array(vc * 4), nrm = new Int8Array(vc * 4), irr = new Uint8Array(vc * 4), col = new Uint8Array(vc * 4), uv = hasUV ? new Float32Array(vc * 2) : null;
  const bmin = [1e9, 1e9, 1e9], bmax = [-1e9, -1e9, -1e9];
  for (const a of acc) for (let q = 0; q < 3; q++) { bmin[q] = Math.min(bmin[q], a.p[q]); bmax[q] = Math.max(bmax[q], a.p[q]); }
  const E = Math.max(1e-3, bmax[0] - bmin[0], bmax[1] - bmin[1], bmax[2] - bmin[2]);
  for (let v = 0; v < acc.length; v++) {
    const d = remap[v]; if (d === 0xffffffff) continue; const a = acc[v];
    for (let q = 0; q < 3; q++) { pos[d * 4 + q] = Math.round((a.p[q] - bmin[q]) / E * 65535); nrm[d * 4 + q] = a.n[q]; }
    nrm[d * 4 + 3] = a.tex;
    // RGBM, range 0..8
    const r = a.irr[0] / a.k, g = a.irr[1] / a.k, bl = a.irr[2] / a.k;
    const M = Math.min(1, Math.max(r, g, bl, 1e-6) / 8); const m8 = Math.max(1, Math.ceil(M * 255)); const mm = m8 / 255 * 8;
    irr[d * 4] = Math.round(Math.min(1, r / mm) * 255); irr[d * 4 + 1] = Math.round(Math.min(1, g / mm) * 255); irr[d * 4 + 2] = Math.round(Math.min(1, bl / mm) * 255); irr[d * 4 + 3] = m8;
    for (let q = 0; q < 4; q++) col[d * 4 + q] = a.col[q];
    if (uv) { uv[d * 2] = a.uv[0]; uv[d * 2 + 1] = a.uv[1]; }
  }
  const ch = { cls: b.cls, cell: key.split('|')[1], vc, ic: ix.length, bmin, bmax, E };
  ch.pos = push(MeshoptEncoder.encodeVertexBuffer(new Uint8Array(pos.buffer), vc, 8));
  ch.nrm = push(MeshoptEncoder.encodeVertexBuffer(new Uint8Array(nrm.buffer), vc, 4));
  ch.irr = push(MeshoptEncoder.encodeVertexBuffer(irr, vc, 4));
  ch.col = push(MeshoptEncoder.encodeVertexBuffer(col, vc, 4));
  if (uv) ch.uv = push(MeshoptEncoder.encodeVertexBuffer(new Uint8Array(uv.buffer), vc, 8));
  ch.idx = push(MeshoptEncoder.encodeIndexBuffer(new Uint8Array(ix.buffer, ix.byteOffset, ix.byteLength), ix.length, 4));
  chunks.push(ch);
}
fs.mkdirSync(outDir, { recursive: true });
// split into parts of at most 20 MiB (the host's per-file limit is 25 MiB); chunk offsets stay global
const all = Buffer.concat(blobs), PART = 20 * 1024 * 1024, parts = Math.max(1, Math.ceil(all.length / PART));
for (const f of fs.readdirSync(outDir)) if (f.startsWith(zone + '.') && f.endsWith('.bin')) fs.unlinkSync(path.join(outDir, f));
for (let i = 0; i < parts; i++) fs.writeFileSync(path.join(outDir, `${zone}.${i}.bin`), all.subarray(i * PART, Math.min(all.length, (i + 1) * PART)));
fs.writeFileSync(path.join(outDir, zone + '.json'), JSON.stringify({ zone, bytes: off, parts, chunks }));
const tv = chunks.reduce((a, c) => a + c.vc, 0), ti = chunks.reduce((a, c) => a + c.ic, 0);
console.log(`${zone}: ${chunks.length} chunks, ${tv} verts, ${ti / 3} tris, ${(off / 1e6).toFixed(2)} MB` + (simpIn ? `  (simplified ${simpIn} -> ${simpOut} tris)` : ''));
