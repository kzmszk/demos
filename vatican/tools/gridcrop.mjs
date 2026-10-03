// node gridcrop.mjs in out x y w h outW gridStep  — crop with labelled grid in SOURCE pixel coords
import sharp from 'sharp';
const [f, out, x, y, w, h, outW, gs] = process.argv.slice(2).map((v, i) => i < 2 ? v : +v);
const sc = outW / w, oh = Math.round(h * sc);
let svg = `<svg width="${outW}" height="${oh}">`;
for (let gx = Math.ceil(x / gs) * gs; gx < x + w; gx += gs) {
  const X = (gx - x) * sc; svg += `<line x1="${X}" y1="0" x2="${X}" y2="${oh}" stroke="red" stroke-width="1" opacity="0.6"/><text x="${X + 2}" y="12" font-size="11" fill="red">${gx}</text>`;
}
for (let gy = Math.ceil(y / gs) * gs; gy < y + h; gy += gs) {
  const Y = (gy - y) * sc; svg += `<line x1="0" y1="${Y}" x2="${outW}" y2="${Y}" stroke="blue" stroke-width="1" opacity="0.6"/><text x="2" y="${Y - 2}" font-size="11" fill="blue">${gy}</text>`;
}
svg += '</svg>';
await sharp(f, { limitInputPixels: false }).extract({ left: x, top: y, width: w, height: h }).resize(outW).composite([{ input: Buffer.from(svg) }]).jpeg({ quality: 85 }).toFile(out);
