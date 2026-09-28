// A small authoring API for pages: everything appends ops in drawing order.
import { writeText } from '../layout.js';
import * as M from '../marks.js';
import { Rng } from '../rng.js';
import { washPath, blobPoly } from '../media.js';
import { glyphDef } from '../hand.js';

export const INK = [26, 28, 40];
export const RED = [192, 60, 52];
export const BLUE = [56, 90, 158];
export const GREEN = [70, 120, 80];
export const PAINT = {
  ultramarine: [72, 98, 176], indigo: [62, 70, 112], cerulean: [86, 150, 192], payne: [82, 92, 108],
  sienna: [176, 104, 62], ochre: [212, 168, 84], rose: [222, 126, 138], sap: [112, 142, 72],
  violet: [128, 102, 158], coffee: [150, 105, 60], gold: [232, 186, 96], peach: [240, 170, 130],
};

export function page(id, seed) {
  const rng = new Rng(seed ?? id);
  const ops = [];
  let pendingGap = 0;
  const push = (o) => {
    const arr = Array.isArray(o) ? o.flat(3) : [o];
    for (const op of arr) {
      if (!op) continue;
      if (pendingGap) { op.gap = (op.gap ?? 0.1) + pendingGap; pendingGap = 0; }
      ops.push(op);
    }
    return arr;
  };
  const api = {
    id, rng, ops,
    pause(s) { pendingGap += s; },
    text(str, o) { const r = writeText(str, { seed: rng.int(1, 1e9), ...o }); push(r); return r.box; },
    line(x1, y1, x2, y2, o = {}) { return push(M.line(x1, y1, x2, y2, o, rng.fork('l' + ops.length))); },
    path(pts, o = {}) { return push(M.path(pts, o, rng.fork('p' + ops.length))); },
    poly(pts, o = {}) { return push(M.polyline(pts, o, rng.fork('q' + ops.length))); },
    circle(x, y, r, o = {}) { return push(M.circle(x, y, r, o, rng.fork('c' + ops.length))); },
    ellipse(x, y, rx, ry, o = {}) { return push(M.ellipse(x, y, rx, ry, o, rng.fork('e' + ops.length))); },
    dot(x, y, o = {}) { return push(M.dot(x, y, o, rng.fork('d' + ops.length))); },
    arrow(x1, y1, x2, y2, o = {}) { return push(M.arrow(x1, y1, x2, y2, o, rng.fork('a' + ops.length))); },
    hatch(poly, ang, sp, o = {}) { return push(M.hatch(poly, ang, sp, o, rng.fork('h' + ops.length))); },
    rect(x, y, w, h, o = {}) { return push(M.rect(x, y, w, h, o, rng.fork('r' + ops.length))); },
    checkbox(x, y, s, o = {}) { return push(M.checkbox(x, y, s, o, rng.fork('b' + ops.length))); },
    scribble(x, y, w, h, o = {}) { return push(M.scribble(x, y, w, h, o, rng.fork('s' + ops.length))); },
    underline(x, y, w, o = {}) { return push(M.underline(x, y, w, o, rng.fork('u' + ops.length))); },
    stipple(pts, o = {}) { return push(M.stipple(pts, o, rng.fork('t' + ops.length))); },
    wash(poly, rgb, o = {}) {
      const r = rng.fork('w' + ops.length);
      const op = { t: 'wash', poly, rgb, a: o.a ?? 0.5, layers: o.layers, edge: o.edge, gran: o.gran, blooms: o.blooms ?? 1, soft: o.soft, clip: o.clip,
        path: o.path || washPath(poly, r, o.rows), brush: o.brush || 6, dur: o.dur ?? 2.4, gap: o.gap ?? 0.5, tool: 'brush', rgbTip: rgb, ghost: o.ghost ?? 1 };
      return push(op);
    },
    blob(cx, cy, rx, ry, rot = 0, n = 14) { return blobPoly(cx, cy, rx, ry, n, rng.fork('bp' + ops.length), rot); },
    erase(pts, o = {}) { return push({ t: 'erase', pts, r: o.r ?? 2.2, k: o.k ?? 0.2, dur: o.dur ?? 1.1, gap: o.gap ?? 0.35, tool: 'eraser' }); },
    smudge(pts, o = {}) { return push({ t: 'smudge', pts, r: o.r ?? 3.2, dur: o.dur ?? 0.7, gap: o.gap ?? 0.3, tool: 'finger' }); },
    tape(x, y, len, wid, rot = 0, o = {}) { return push({ t: 'tape', x, y, len, wid, rot, tint: o.tint, dur: o.dur ?? 0.9, gap: o.gap ?? 0.4, tool: 'hand' }); },
    stain(x, y, r, o = {}) { return push({ t: 'stain', x, y, r, seed: o.seed ?? rng.int(1, 999), k: o.k ?? 1, dur: 0.6, gap: o.gap ?? 0.2, tool: 'none' }); },
    dots(pts, o = {}) {
      const flat = new Float32Array(pts.length * 2);
      pts.forEach(([x, y], i) => { flat[i * 2] = x; flat[i * 2 + 1] = y; });
      return push({ t: 'dots', pts: flat, sizes: o.sizes, medium: o.medium || 'pencil', color: o.color, w: o.w || 0.45, a: o.a, dur: o.dur ?? pts.length * 0.03, gap: o.gap ?? 0.2, tool: o.tool || ((o.medium || 'pencil') === 'ink' ? 'pen' : 'pencil') });
    },
    raw(op) { return push(op); },
    // where a stroke of a glyph lands, for labelling big characters: glyph box (0..100) → page mm
    glyphPoint(x, y, gx, gy, size) { return [x + (gx / 100) * size, y + (gy / 100) * size]; },
    glyph: glyphDef,
  };
  return api;
}

// scrub path for an eraser across a box
export function scrubPath(x, y, w, h, passes, r) {
  const pts = [];
  const n = passes * 8;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const px = x + (Math.sin(t * Math.PI * passes) * 0.5 + 0.5) * w + r.sym(0.4);
    const py = y + t * h + r.sym(0.3);
    pts.push([px, py]);
  }
  return pts;
}
