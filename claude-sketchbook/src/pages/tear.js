// The line where page 5 was torn out of the book (leaf coordinates: u from the spine, v down the page).
import { Rng } from '../rng.js';
export const TEAR = (() => {
  const r = new Rng('tear-p05');
  const pts = [];
  let u = 12.5;
  for (let v = -1; v <= 211; v += 0.9) {
    u += r.sym(0.55) + (12.8 - u) * 0.08;
    if (r.chance(0.04)) u += r.sym(1.6);
    pts.push([u, v, 0.25 + r.f() * 0.45]); // [u, v, gap width]
  }
  return pts;
})();
