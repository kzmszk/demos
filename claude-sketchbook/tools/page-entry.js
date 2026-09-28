import { PAGE_BUILDERS } from '../src/pages/index.js';
import { PageRuntime } from '../src/runtime.js';
window.renderPage = function (id, frac = 1, scale = 1) {
  const t0 = performance.now();
  const def = PAGE_BUILDERS[id]();
  const t1 = performance.now();
  const rt = new PageRuntime(def);
  const t2 = performance.now();
  rt.advanceTo(rt.T * frac);
  const t3 = performance.now();
  const src = rt.display;
  const c = document.createElement('canvas');
  c.width = src.width * scale; c.height = src.height * scale;
  const g = c.getContext('2d');
  g.drawImage(src, 0, 0, c.width, c.height);
  // tool marker
  if (frac < 1) {
    const tl = rt.toolAt(rt.T * frac);
    g.fillStyle = 'rgba(255,0,0,0.6)'; g.beginPath(); g.arc(tl.x * 7 * scale, tl.y * 7 * scale, 6, 0, 7); g.fill();
  }
  return { url: c.toDataURL('image/png'), stats: { build: t1 - t0, paper: t2 - t1, draw: t3 - t2, ops: def.ops.length, strokes: rt.strokes, T: rt.T } };
};
window.__ready = true;
