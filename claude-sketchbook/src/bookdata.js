// All the paper in the book, as canvases that draw themselves.
import { PAGE_BUILDERS } from './pages/index.js';
import { PageRuntime } from './runtime.js';
import { PX, PAGE_W, PAGE_H, makeCanvas } from './media.js';
import { frontOutside, frontInside, backInside, backOutside } from './covers.js';
import { TEAR } from './pages/tear.js';

export function buildBookData() {
  const ids = ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09'];
  const defs = ids.map((id) => PAGE_BUILDERS[id]());
  defs.push({ id: 'p10', ops: [], seed: 1010 });
  const pages = defs.map((d) => new PageRuntime(d));
  // watercolour soaks through: when a wash dries, a faint mirror of it appears on the other side of the leaf
  for (let l = 0; l < 5; l++) {
    const f = pages[l * 2], b = pages[l * 2 + 1];
    for (const [src, dst] of [[f, b], [b, f]]) {
      for (const op of src.def.ops) {
        if (op.t !== 'wash') continue;
        op.onDone = (wash) => {
          const g = dst.g;
          g.save();
          g.globalCompositeOperation = 'multiply';
          g.globalAlpha = 0.085 * (op.ghost ?? 1);
          g.filter = 'blur(2.5px) saturate(0.7)';
          g.translate(dst.W, 0);
          g.scale(-1, 1);
          g.drawImage(wash.img.canvas, wash.img.ox, wash.img.oy);
          g.restore();
          dst.version++;
        };
      }
    }
  }
  // the torn leaf: a mask that opens along the tear as it happens (x = distance from the spine)
  const W = Math.round(PAGE_W * PX), H = Math.round(PAGE_H * PX);
  const alphaF = makeCanvas(W, H), alphaB = makeCanvas(W, H);
  for (const c of [alphaF, alphaB]) { const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, W, H); }
  const tear = { alphaF, alphaB, version: 0 };
  pages[4].onTear = (op, i0, i1) => {
    for (const [c, mirror] of [[alphaF, false], [alphaB, true]]) {
      const g = c.getContext('2d');
      g.strokeStyle = '#000';
      g.lineCap = 'round';
      for (let i = Math.max(1, i0); i < i1; i++) {
        const [u0, v0, w0] = TEAR[i - 1], [u1, v1] = TEAR[i];
        g.lineWidth = w0 * PX;
        const x0 = mirror ? W - u0 * PX : u0 * PX, x1 = mirror ? W - u1 * PX : u1 * PX;
        g.beginPath(); g.moveTo(x0, v0 * PX); g.lineTo(x1, v1 * PX); g.stroke();
      }
    }
    tear.version++;
  };
  const total = pages.reduce((n, p) => n + p.strokes, 0);
  const covers = { frontOut: frontOutside(), frontIn: frontInside(), backIn: backInside(), backOut: backOutside(total, 0) };
  return { pages, covers, tear, total };
}
