// statue_pack.mjs — meshopt + gzip the staged statue meshes:  node statue_pack.mjs STAGE_DIR OUT_DIR
// one file per model and LOD (<id>_<lod>.bin: meshopt vertex stream then index stream, gzipped), statues.json with offsets
import fs from 'node:fs'; import path from 'node:path'; import zlib from 'node:zlib';
import { MeshoptEncoder } from 'meshoptimizer';
await MeshoptEncoder.ready;
const [stage, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const meta = JSON.parse(fs.readFileSync(path.join(stage, 'statues.json'), 'utf8'));
let raw = 0, packed = 0;
for (const m of meta.models) {
  for (const l of m.lods) {
    const v = new Uint8Array(fs.readFileSync(path.join(stage, l.name + '.v')));
    const i = new Uint32Array(new Uint8Array(fs.readFileSync(path.join(stage, l.name + '.i'))).buffer);
    const ev = MeshoptEncoder.encodeVertexBuffer(v, l.vcount, meta.stride);
    const ei = MeshoptEncoder.encodeIndexBuffer(new Uint8Array(i.buffer), l.icount, 4);
    const body = Buffer.concat([Buffer.from(ev), Buffer.from(ei)]);
    const gz = zlib.gzipSync(body, { level: 9 });
    fs.writeFileSync(path.join(out, l.name + '.bin'), gz);
    l.file = l.name + '.bin'; l.vlen = ev.length; l.ilen = ei.length;
    raw += v.length + i.byteLength; packed += gz.length;
  }
}
fs.writeFileSync(path.join(out, 'statues.json'), JSON.stringify(meta));
console.log(`statues: ${(raw / 1048576).toFixed(1)} MB raw -> ${(packed / 1048576).toFixed(1)} MB`);
