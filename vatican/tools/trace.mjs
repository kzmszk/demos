// trace the left silhouette of a dark engraving against paper: for each row in [y0,y1],
// first x (scanning from xs to the right) where a run of >= runLen dark pixels starts.
import sharp from 'sharp';
const [f, y0s, y1s, xs, xe, step = '8', thr = '110', runLen = '6'] = process.argv.slice(2);
const img = sharp(f, { limitInputPixels: false }).greyscale();
const { data, info } = await img.raw().toBuffer({ resolveWithObject: true });
const W = info.width;
const out = [];
for (let y = +y0s; y <= +y1s; y += +step) {
  let found = -1;
  for (let x = +xs; x < +xe; x++) {
    let ok = true;
    for (let k = 0; k < +runLen; k++) if (data[y * W + x + k] > +thr) { ok = false; break; }
    if (ok) { found = x; break; }
  }
  out.push([y, found]);
}
console.log(JSON.stringify(out));
