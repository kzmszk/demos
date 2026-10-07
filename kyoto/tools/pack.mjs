// pack.mjs — meshopt-encode staged tile streams, simplify the far LOD, gzip:  node pack.mjs STAGE_DIR OUT_DIR
import fs from 'node:fs'; import path from 'node:path'; import zlib from 'node:zlib';
import { MeshoptEncoder, MeshoptSimplifier } from 'meshoptimizer';
await MeshoptEncoder.ready; await MeshoptSimplifier.ready;
const [stage, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const manP = path.join(out, 'tiles.json');
const man = fs.existsSync(manP) ? JSON.parse(fs.readFileSync(manP, 'utf8')) : { tiles: {} };
let total = 0, liteTotal = 0;
const encode = (u8, count, stride, kind) => kind === 'i' ? MeshoptEncoder.encodeIndexBuffer(u8, count, 4) : MeshoptEncoder.encodeVertexBuffer(u8, count, stride);
function packLite(L, raw, file) {
  const view = (s) => { const b = raw.buffer.slice(raw.byteOffset + s.off, raw.byteOffset + s.off + s.len); return s.kind === 'i' ? new Uint32Array(b) : new Uint8Array(b); };
  const S = {}; for (const s of L.streams) S[s.name] = { s, d: view(s) };
  const parts = { pos: [], c0: [], c1: [], irr: [], idx: [] }; let mv = 0;
  for (const g of ['b', 'g', 'l', 'h']) {
    if (!S[g + ':pos']) continue;
    const pos = new Float32Array(S[g + ':pos'].d.buffer); let idx = S[g + ':idx'].d; const meta = S[g + ':idx'].s;
    const target = Math.max(3, Math.floor(idx.length * meta.ratio / 3) * 3);
    if (idx.length > 3 && meta.ratio < 1) idx = meta.sloppy ? MeshoptSimplifier.simplifySloppy(idx, pos, 3, null, target, meta.err / MeshoptSimplifier.getScale(pos, 3))[0] : MeshoptSimplifier.simplify(idx, pos, 3, target, meta.err, ['ErrorAbsolute'])[0];
    const remap = new Int32Array(pos.length / 3).fill(-1); let n = 0;
    const o = new Uint32Array(idx.length);
    for (let i = 0; i < idx.length; i++) { const v = idx[i]; if (remap[v] < 0) remap[v] = n++; o[i] = remap[v] + mv; }
    const P = new Float32Array(n * 3), C0 = new Uint8Array(n * 4), C1 = new Uint8Array(n * 4), IR = new Uint8Array(n * 4);
    for (let v = 0; v < remap.length; v++) { const r = remap[v]; if (r < 0) continue;
      P.set(pos.subarray(v * 3, v * 3 + 3), r * 3); C0.set(S[g + ':c0'].d.subarray(v * 4, v * 4 + 4), r * 4); C1.set(S[g + ':c1'].d.subarray(v * 4, v * 4 + 4), r * 4); IR.set(S[g + ':irr'].d.subarray(v * 4, v * 4 + 4), r * 4); }
    parts.pos.push(P); parts.c0.push(C0); parts.c1.push(C1); parts.irr.push(IR); parts.idx.push(o); mv += n;
  }
  const cat = (arrs, T) => { const n = arrs.reduce((a, b) => a + b.length, 0); const o = new T(n); let k = 0; for (const a of arrs) { o.set(a, k); k += a.length; } return o; };
  const P = cat(parts.pos, Float32Array);
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], P[i + k]); hi[k] = Math.max(hi[k], P[i + k]); }
  const ext = Math.max(1e-3, hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
  const Q = new Uint16Array(P.length / 3 * 4); for (let i = 0, j = 0; i < P.length; i += 3, j += 4) for (let k = 0; k < 3; k++) Q[j + k] = Math.round((P[i + k] - lo[k]) / ext * 65535);
  const streams = []; const bins = []; let off = 0;
  const enc = (name, arr, stride, kind = 'v') => { const u8 = new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength); const count = kind === 'i' ? arr.length : u8.length / stride;
    const e = encode(u8, count, stride, kind); streams.push({ name, off, len: e.length, count, stride, kind }); bins.push(e); off += e.length; };
  if (P.length) { enc('pos', Q, 8); enc('c0', cat(parts.c0, Uint8Array), 4); enc('c1', cat(parts.c1, Uint8Array), 4); enc('irr', cat(parts.irr, Uint8Array), 4); enc('idx', cat(parts.idx, Uint32Array), 4, 'i'); }
  if (S['t:pos']) { enc('tpos', new Float32Array(S['t:pos'].d.buffer), 16); enc('tq', S['t:q'].d, 4); enc('tirr', S['t:irr'].d, 4); }
  const gz = zlib.gzipSync(Buffer.concat(bins.map((p) => Buffer.from(p.buffer, p.byteOffset, p.length))), { level: 9 });
  fs.writeFileSync(file, gz);
  return { qmin: lo, qext: ext, streams, bytes: gz.length };
}
for (const f of fs.readdirSync(stage).filter((f) => f.startsWith('t_') && f.endsWith('.json') && !f.endsWith('.lite.json'))) {
  const hdr = JSON.parse(fs.readFileSync(path.join(stage, f), 'utf8'));
  const raw = fs.readFileSync(path.join(stage, hdr.name + '.raw'));
  const bins = []; let off = 0;
  for (const g of hdr.groups) for (const s of g.streams) {
    const e = encode(new Uint8Array(raw.buffer.slice(raw.byteOffset + s.off, raw.byteOffset + s.off + s.len)), s.count, s.stride, s.kind);
    s.off = off; s.len = e.length; bins.push(e); off += e.length;
  }
  const gz = zlib.gzipSync(Buffer.concat(bins.map((p) => Buffer.from(p.buffer, p.byteOffset, p.length))), { level: 9 });
  fs.writeFileSync(path.join(out, hdr.name + '.bin'), gz);
  const meta = { name: hdr.name, tile: hdr.tile, bbox: hdr.bbox, qmin: hdr.qmin, qext: hdr.qext, groups: hdr.groups, z: hdr.z, bytes: gz.length };
  fs.writeFileSync(path.join(out, hdr.name + '.json'), JSON.stringify(meta));
  const rec = man.tiles[hdr.name] = { tile: hdr.tile, bbox: hdr.bbox, z: hdr.z, bytes: gz.length };
  total += gz.length;
  const lj = path.join(stage, hdr.name + '.lite.json');
  if (fs.existsSync(lj)) { const lite = packLite(JSON.parse(fs.readFileSync(lj, 'utf8')), fs.readFileSync(path.join(stage, hdr.name + '.lite.raw')), path.join(out, hdr.name + '.lite.bin')); rec.lite = lite; liteTotal += lite.bytes; }
  for (const ext of ['walk', 'surf']) { const p = path.join(stage, `${hdr.name}.${ext}.png`); if (fs.existsSync(p)) { fs.copyFileSync(p, path.join(out, `${hdr.name}.${ext}.png`)); rec[ext] = 1; } }
  console.log(hdr.name, (raw.length / 1024) | 0, 'KB raw ->', (gz.length / 1024) | 0, 'KB gz', rec.lite ? ((rec.lite.bytes / 1024) | 0) + ' KB lite' : '');
}
fs.writeFileSync(manP, JSON.stringify(man));
console.log('total', (total / 1048576).toFixed(1), 'MB', 'lite', (liteTotal / 1048576).toFixed(2), 'MB');
