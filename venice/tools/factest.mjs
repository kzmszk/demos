globalThis.self = globalThis;
const { FacadeBuilder, outline } = await import('./web/facade.js');
import fs from 'node:fs';
const mats = JSON.parse(fs.readFileSync('/home/kazu/work/demos/venice/public/data/materials.json', 'utf8')).mats;
let bad = 0, total = 0;
for (const f of fs.readdirSync('/home/kazu/work/demos/venice/public/data/tiles').filter((x) => x.endsWith('.json') && x.startsWith('t_'))) {
  const meta = JSON.parse(fs.readFileSync('/home/kazu/work/demos/venice/public/data/tiles/' + f, 'utf8'));
  const atlas = { rects: meta.fac.map(() => [0, 0, 0]), slots: [0] };
  for (let i = 0; i < meta.fac.length; i++) {
    const fb = new FacadeBuilder(mats, atlas);
    const fc = meta.fac[i];
    fb.begin(fc, i);
    const L = fb.L, zb = fc[6], zt = fc[7];
    const holes = [];
    let holeArea = 0;
    for (const o of fc[23]) {
      const [t, u, z, w, h] = o;
      if (u - w / 2 < 0.05 || u + w / 2 > L - 0.05 || z < zb || z + h > zt - 0.1) continue;
      const pts = outline(t, u, z, w, h); holes.push(pts);
      let a = 0; for (let k = 0; k < pts.length; k++) { const p = pts[k], q = pts[(k + 1) % pts.length]; a += p[0] * q[1] - q[0] * p[1]; } holeArea += Math.abs(a) / 2;
    }
    const n0 = fb.g.idx.length;
    fb.planar([[0, zb], [L, zb], [L, zt], [0, zt]], holes, 0, fb.wallS);
    // area of produced triangles
    let A = 0; const I = fb.g.idx, P = fb.g.P;
    for (let k = n0; k < I.length; k += 3) {
      const a = I[k], b = I[k + 1], c = I[k + 2];
      const ax = P[a * 3], ay = P[a * 3 + 1], az = P[a * 3 + 2], bx = P[b * 3], by = P[b * 3 + 1], bz = P[b * 3 + 2], cx = P[c * 3], cy = P[c * 3 + 1], cz = P[c * 3 + 2];
      const ux = bx - ax, uy = by - ay, uz = bz - az, vx = cx - ax, vy = cy - ay, vz = cz - az;
      A += Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx) / 2;
    }
    const expect = L * (zt - zb) - holeArea;
    total++;
    if (Math.abs(A - expect) > 0.02 * expect + 0.05) { bad++; if (bad < 12) console.log(f, i, 'L', L.toFixed(2), 'h', (zt - zb).toFixed(1), 'holes', holes.length, 'area', A.toFixed(1), 'expect', expect.toFixed(1)); }
  }
}
console.log('bad', bad, 'of', total);
