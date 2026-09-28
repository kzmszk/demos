import { renderNote, SR } from '../src/audio/piano.js';
window.renderScale = function (notes, vel = 0.5, hold = 0.5, step0 = 0.55) {
  const t0 = performance.now();
  const step = step0 * SR;
  const tail = 4 * SR;
  const out = new Float32Array(Math.floor(notes.length * step + tail));
  notes.forEach((m, i) => {
    const b = renderNote(m, vel, hold, 1000 + i);
    const o = Math.floor(i * step);
    for (let k = 0; k < b.length && o + k < out.length; k++) out[o + k] += b[k];
  });
  let pk = 0; for (const x of out) pk = Math.max(pk, Math.abs(x));
  return { ms: performance.now() - t0, pk, data: Array.from(out) };
};
window.__ready = true;
