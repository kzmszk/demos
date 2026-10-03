// detail texture atlas: layers stacked vertically, each 512x512 (R = luminance ratio x127.5, G,B = normal xy).
// Layer order must match mats.mjs TEX ids (id 1 = first layer).
import sharp from 'sharp'; import fs from 'fs';
const T = '/home/kazu/work/vatican-assets/textures/';
const LAYERS = [ // [id name, poly haven id or null (procedural), tile metres]
  ['travertine', 'large_sandstone_blocks_01', 3.2], ['marble', 'marble_01', 2.4], ['plaster', 'white_plaster_rough_01', 4.0],
  ['cobble', 'cobblestone_square', 2.0], ['tile', 'clay_roof_tiles_02', 2.6], ['lead', null, 1.2], ['brick', 'castle_brick_02_red', 2.2],
  ['granite', null, 1.0], ['grass', 'forest_leaves_02', 4.0], ['gravel', 'gravel_floor', 2.5],
];
const S = 512; const out = Buffer.alloc(S * S * LAYERS.length * 3);
for (const [li, [name, src]] of LAYERS.entries()) {
  const base = li * S * S * 3;
  if (!src) {
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const i = base + (y * S + x) * 3; let r = 127.5, nx = 128, ny = 128;
      if (name === 'lead') {          // standing seams every 1/3 of the tile, horizontal laps
        const sx = (x % (S / 3)) / (S / 3), sy = (y % (S / 2)) / (S / 2);
        const seam = Math.exp(-Math.pow((sx - 0.5) * 22, 2));
        r = 127.5 * (0.93 + 0.12 * seam - (sy < 0.03 ? 0.12 : 0) + 0.05 * Math.sin(x * 0.37 + y * 0.11));
        nx = 128 + Math.round(60 * Math.sign(0.5 - sx) * seam);
      } else {                         // granite speckle
        const h = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453; const n = h - Math.floor(h);
        r = 127.5 * (0.8 + 0.4 * n);
      }
      out[i] = Math.max(0, Math.min(255, r)); out[i + 1] = nx; out[i + 2] = ny;
    }
    continue;
  }
  const d = await sharp(T + `${src}_diff_1k.jpg`).resize(S, S).greyscale().raw().toBuffer();
  const n = await sharp(T + `${src}_nor_1k.jpg`).resize(S, S).removeAlpha().raw().toBuffer();
  let mean = 0; for (const v of d) mean += v; mean /= d.length;
  for (let p = 0; p < S * S; p++) {
    const i = base + p * 3;
    out[i] = Math.max(0, Math.min(255, Math.round(127.5 * d[p] / mean)));
    out[i + 1] = n[p * 3]; out[i + 2] = n[p * 3 + 1];
  }
}
fs.mkdirSync('../public/tex', { recursive: true });
await sharp(out, { raw: { width: S, height: S * LAYERS.length, channels: 3 } }).jpeg({ quality: 88 }).toFile('../public/tex/detail.jpg');
fs.writeFileSync('../public/tex/detail.json', JSON.stringify({ size: S, layers: LAYERS.map(([n, s, t]) => ({ name: n, tile: t, src: s })) }));
console.log('detail atlas', LAYERS.length, 'layers');
