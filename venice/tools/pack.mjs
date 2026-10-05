// pack.mjs — meshopt-encode staged tile streams:  node pack.mjs STAGE_DIR OUT_DIR
// Tile binaries are written gzip-compressed (the viewer inflates them with DecompressionStream): meshopt streams
// shrink by another ~40%, and the host does not compress application/octet-stream itself.
import fs from 'node:fs'; import path from 'node:path'; import zlib from 'node:zlib';
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';
await MeshoptEncoder.ready; await MeshoptSimplifier.ready;
const [stage, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const man = fs.existsSync(path.join(out, 'tiles.json')) ? JSON.parse(fs.readFileSync(path.join(out, 'tiles.json'), 'utf8')) : { tiles: {} };
let total = 0, liteTotal = 0;
// far LOD: simplify the roof/ground/hero groups, compact, quantise positions into one cube, meshopt-encode
function packLite(L, raw, file) {
  const view = (s) => { const b = raw.buffer.slice(raw.byteOffset + s.off, raw.byteOffset + s.off + s.len); return s.kind === 'i' ? new Uint32Array(b) : new Uint8Array(b); };
  const S = {}; for (const s of L.streams) S[s.name] = { s, d: view(s) };
  const meshes = {}; const mvs = {};
  for (const g of L.groups.filter((g) => g !== 'fac')) {
    const key = g === 'hero' ? 'h' : 'm';
    const mesh = meshes[key] || (meshes[key] = { pos: [], irr: [], irrn: [], c0: [], c1: [], idx: [] }); let mv = mvs[key] || 0;
    const pos = new Float32Array(S[g + ':pos'].d.buffer); let idx = S[g + ':idx'].d; const meta = S[g + ':idx'].s;
    const target = Math.max(3, Math.floor(idx.length * meta.ratio / 3) * 3);
    if (idx.length > 3) idx = g === 'hero' ? MeshoptSimplifier.simplifySloppy(idx, pos, 3, null, target, meta.err / MeshoptSimplifier.getScale(pos, 3))[0]
      : MeshoptSimplifier.simplify(idx, pos, 3, target, meta.err, ['ErrorAbsolute'])[0];
    const remap = new Int32Array(pos.length / 3).fill(-1); let n = 0;
    const out = new Uint32Array(idx.length);
    for (let i = 0; i < idx.length; i++) { const v = idx[i]; if (remap[v] < 0) remap[v] = n++; out[i] = remap[v] + mv; }
    const P = new Float32Array(n * 3), IR = new Uint8Array(n * 4), IRN = new Uint8Array(n * 4), C0 = new Uint8Array(n * 4), C1 = new Uint8Array(n * 4);
    const irr = S[g + ':irr'].d, irrn = S[g + ':irrn'] ? S[g + ':irrn'].d : null, c0 = S[g + ':c0'].d, c1 = S[g + ':c1'].d;
    for (let v = 0; v < remap.length; v++) { const r = remap[v]; if (r < 0) continue;
      P.set(pos.subarray(v * 3, v * 3 + 3), r * 3); IR.set(irr.subarray(v * 4, v * 4 + 4), r * 4); if (irrn) IRN.set(irrn.subarray(v * 4, v * 4 + 4), r * 4);
      C0.set(c0.subarray(v * 4, v * 4 + 4), r * 4); C1.set(c1.subarray(v * 4, v * 4 + 4), r * 4); }
    mesh.pos.push(P); mesh.irr.push(IR); mesh.irrn.push(IRN); mesh.c0.push(C0); mesh.c1.push(C1); mesh.idx.push(out); mv += n; mvs[key] = mv;
  }
  const cat = (arrs, T) => { const n = arrs.reduce((a, b) => a + b.length, 0); const o = new T(n); let k = 0; for (const a of arrs) { o.set(a, k); k += a.length; } return o; };
  const MP = meshes.m ? cat(meshes.m.pos, Float32Array) : new Float32Array(0);
  const HP = meshes.h ? cat(meshes.h.pos, Float32Array) : new Float32Array(0);
  const F = L.groups.includes('fac') ? { pos: new Float32Array(S['fac:pos'].d.buffer) } : null;
  // one quantisation cube for all meshes
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (const A of [MP, HP, F && F.pos]) if (A) for (let i = 0; i < A.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], A[i + k]); hi[k] = Math.max(hi[k], A[i + k]); }
  const ext = Math.max(1e-3, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
  const q = (A) => { const o = new Uint16Array(A.length / 3 * 4); for (let i = 0, j = 0; i < A.length; i += 3, j += 4) { for (let k = 0; k < 3; k++) o[j + k] = Math.round((A[i + k] - lo[k]) / ext * 65535); } return o; };
  const streams = []; const parts = []; let off = 0;
  const enc = (name, arr, stride, kind = 'v') => {
    const u8 = new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength); const count = kind === 'i' ? arr.length : u8.length / stride;
    const e = kind === 'i' ? MeshoptEncoder.encodeIndexBuffer(u8, count, 4) : MeshoptEncoder.encodeVertexBuffer(u8, count, stride);
    streams.push({ name, off, len: e.length, count, stride, kind }); parts.push(e); off += e.length;
  };
  for (const [k, P] of [['m', MP], ['h', HP]]) {
    if (!P.length) continue; const mesh = meshes[k];
    enc(k + ':pos', q(P), 8); enc(k + ':irr', cat(mesh.irr, Uint8Array), 4); enc(k + ':irrn', cat(mesh.irrn, Uint8Array), 4); enc(k + ':c0', cat(mesh.c0, Uint8Array), 4); enc(k + ':c1', cat(mesh.c1, Uint8Array), 4);
    enc(k + ':idx', cat(mesh.idx, Uint32Array), 4, 'i');
  }
  if (F) {
    enc('f:pos', q(F.pos), 8); enc('f:uv', new Float32Array(S['fac:uv'].d.buffer), 8); enc('f:c0', S['fac:c0'].d, 4); enc('f:c1', S['fac:c1'].d, 4);
    enc('f:irr', S['fac:irr'].d, 4); enc('f:irrn', S['fac:irrn'] ? S['fac:irrn'].d : new Uint8Array(S['fac:irr'].d.length), 4); enc('f:w0', new Float32Array(S['fac:w0'].d.buffer), 16); enc('f:w1', new Float32Array(S['fac:w1'].d.buffer), 16);
    enc('f:idx', S['fac:idx'].d, 4, 'i');
  }
  const bin = Buffer.concat(parts.map((p) => Buffer.from(p.buffer, p.byteOffset, p.length)));
  const gz = zlib.gzipSync(bin, { level: 9 });
  fs.writeFileSync(file, gz);
  return { qmin: lo, qext: ext, streams, bytes: gz.length };
}
for (const f of fs.readdirSync(stage).filter((f) => f.endsWith(".json") && f.startsWith("t_") && !f.endsWith(".lite.json"))) {
  const hdr = JSON.parse(fs.readFileSync(path.join(stage, f), 'utf8'));
  const raw = fs.readFileSync(path.join(stage, hdr.name + '.raw'));
  const parts = []; let off = 0; const streams = [];
  for (const s of hdr.streams) {
    const src = new Uint8Array(raw.buffer, raw.byteOffset + s.off, s.len);
    let enc;
    if (s.kind === 'i') enc = MeshoptEncoder.encodeIndexBuffer(new Uint8Array(src), s.count, 4);
    else enc = MeshoptEncoder.encodeVertexBuffer(new Uint8Array(src), s.count, s.stride);
    streams.push({ name: s.name, off, len: enc.length, count: s.count, stride: s.stride, kind: s.kind });
    parts.push(enc); off += enc.length;
  }
  const bin = Buffer.concat(parts.map((p) => Buffer.from(p.buffer, p.byteOffset, p.length)));
  const gz = zlib.gzipSync(bin, { level: 9 });
  fs.writeFileSync(path.join(out, hdr.name + '.bin'), gz);
  const meta = { name: hdr.name, tile: hdr.tile, bbox: hdr.bbox, qmin: hdr.qmin, qext: hdr.qext, nv: hdr.nv, ni: hdr.ni, hr: hdr.hr, streams, fac: hdr.fac, bytes: gz.length };
  fs.writeFileSync(path.join(out, hdr.name + '.json'), JSON.stringify(meta));
  man.tiles[hdr.name] = { tile: hdr.tile, bbox: hdr.bbox, bytes: gz.length };
  total += gz.length;
  const lj = path.join(stage, hdr.name + '.lite.json');
  if (fs.existsSync(lj)) { const lite = packLite(JSON.parse(fs.readFileSync(lj, 'utf8')), fs.readFileSync(path.join(stage, hdr.name + '.lite.raw')), path.join(out, hdr.name + '.lite.bin')); man.tiles[hdr.name].lite = lite; liteTotal += lite.bytes; }
  const wp = path.join(stage, hdr.name + '.walk.png');
  if (fs.existsSync(wp)) { fs.copyFileSync(wp, path.join(out, hdr.name + '.walk.png')); man.tiles[hdr.name].walk = 1; }
  console.log(hdr.name, (raw.length / 1024) | 0, 'KB raw ->', (bin.length / 1024) | 0, 'KB ->', (gz.length / 1024) | 0, 'KB gz');
}
fs.writeFileSync(path.join(out, 'tiles.json'), JSON.stringify(man));
console.log('total', (total / 1048576).toFixed(1), 'MB', 'lite', (liteTotal / 1048576).toFixed(2), 'MB');
// prop templates (if staged)
if (fs.existsSync(path.join(stage, 'props.tpl.json'))) {
  const hdr = JSON.parse(fs.readFileSync(path.join(stage, 'props.tpl.json'), 'utf8'));
  const raw = fs.readFileSync(path.join(stage, 'props.raw'));
  const parts = []; let off = 0;
  for (const rec of hdr.templates) {
    for (const s of rec.streams) {
      const src = new Uint8Array(raw.buffer, raw.byteOffset + s.off, s.len);
      const enc = s.kind === 'i' ? MeshoptEncoder.encodeIndexBuffer(new Uint8Array(src), s.count, 4) : MeshoptEncoder.encodeVertexBuffer(new Uint8Array(src), s.count, s.stride);
      s.off = off; s.len = enc.length; parts.push(enc); off += enc.length;
    }
  }
  fs.writeFileSync(path.join(out, 'props.bin'), Buffer.concat(parts.map((p) => Buffer.from(p.buffer, p.byteOffset, p.length))));
  fs.writeFileSync(path.join(out, 'props.json'), JSON.stringify(hdr));
  console.log('props templates', hdr.templates.length, (off / 1024) | 0, 'KB');
}
