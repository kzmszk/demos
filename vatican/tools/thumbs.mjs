// node thumbs.mjs <dir> <outdir> [maxPx]  — downscaled JPEG copies for viewing
import sharp from 'sharp'; import fs from 'fs'; import path from 'path';
const [dir, out, max = '1600'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
for (const f of fs.readdirSync(dir)) {
  if (!/\.(jpe?g|png|tif|webp)$/i.test(f)) continue;
  const dst = path.join(out, f.replace(/\.[^.]+$/, '.jpg'));
  if (fs.existsSync(dst)) continue;
  try { await sharp(path.join(dir, f), { limitInputPixels: false }).resize(+max, +max, { fit: 'inside' }).jpeg({ quality: 82 }).toFile(dst); }
  catch (e) { console.log('fail', f, e.message); }
}
