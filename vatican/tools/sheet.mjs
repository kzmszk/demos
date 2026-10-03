// node sheet.mjs out.jpg cell cols file1 file2 ...  — labelled contact sheet
import sharp from 'sharp';
const [out, cellS, colsS, ...files] = process.argv.slice(2);
const cell = +cellS, cols = +colsS, rows = Math.ceil(files.length / cols);
const comps = [];
for (let i = 0; i < files.length; i++) {
  const buf = await sharp(files[i], { limitInputPixels: false }).resize(cell, cell, { fit: 'contain', background: '#fff' }).toBuffer();
  const label = Buffer.from(`<svg width="${cell}" height="22"><rect width="100%" height="100%" fill="#000"/><text x="4" y="16" font-size="15" fill="#ff0" font-family="sans-serif">${i}: ${files[i].split('/').pop().slice(0, 60).replace(/&/g,'&amp;').replace(/</g,'&lt;')}</text></svg>`);
  comps.push({ input: buf, left: (i % cols) * cell, top: Math.floor(i / cols) * (cell + 22) + 22 });
  comps.push({ input: label, left: (i % cols) * cell, top: Math.floor(i / cols) * (cell + 22) });
}
await sharp({ create: { width: cols * cell, height: rows * (cell + 22), channels: 3, background: '#888' } }).composite(comps).jpeg({ quality: 80 }).toFile(out);
