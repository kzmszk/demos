// Debug sheets for the handwriting: skeleton (with stroke order) next to a written instance.
import { glyphDef, glyphStrokes } from '../src/hand.js';
import { Rng } from '../src/rng.js';

function drawStrokeSimple(ctx, st, scale, width, color) {
  ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const p = st.pts;
  for (let i = 1; i < p.length; i++) {
    ctx.lineWidth = Math.max(0.3, width * p[i][2]) * scale;
    ctx.beginPath(); ctx.moveTo(p[i - 1][0] * scale, p[i - 1][1] * scale); ctx.lineTo(p[i][0] * scale, p[i][1] * scale); ctx.stroke();
  }
}

window.renderSheet = function (chars, opts = {}) {
  const cols = opts.cols || 10, cell = opts.cell || 120, pad = 8;
  const rows = Math.ceil(chars.length / cols);
  const c = document.createElement('canvas');
  c.width = cols * cell * 2 + pad * 2; c.height = rows * cell + pad * 2;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#f7f3ea'; ctx.fillRect(0, 0, c.width, c.height);
  const errors = [];
  chars.forEach((ch, i) => {
    const gx = pad + (i % cols) * cell * 2, gy = pad + Math.floor(i / cols) * cell;
    ctx.strokeStyle = '#ddd'; ctx.lineWidth = 1; ctx.strokeRect(gx, gy, cell, cell); ctx.strokeRect(gx + cell, gy, cell, cell);
    ctx.strokeStyle = '#eee'; ctx.beginPath(); ctx.moveTo(gx + cell / 2, gy); ctx.lineTo(gx + cell / 2, gy + cell); ctx.moveTo(gx, gy + cell / 2); ctx.lineTo(gx + cell, gy + cell / 2); ctx.stroke();
    let g;
    try { g = glyphDef(ch); } catch (e) { errors.push(ch + ': ' + e.message); }
    if (!g) { ctx.fillStyle = '#c00'; ctx.font = '20px sans-serif'; ctx.fillText('? ' + ch, gx + 10, gy + 30); if (!errors.find(x => x.startsWith(ch))) errors.push(ch + ': missing'); return; }
    // skeleton
    const s = cell / 100;
    g.strokes.forEach((st, k) => {
      ctx.strokeStyle = `hsl(${(k * 47) % 360},70%,40%)`; ctx.lineWidth = 2; ctx.beginPath();
      st.pts.forEach((p, j) => (j ? ctx.lineTo(gx + p.x * s, gy + p.y * s) : ctx.moveTo(gx + p.x * s, gy + p.y * s)));
      ctx.stroke();
      const p0 = st.pts[0];
      ctx.fillStyle = '#d22'; ctx.font = '11px sans-serif'; ctx.fillText(String(k + 1), gx + p0.x * s - 9, gy + p0.y * s - 2);
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(gx + p0.x * s, gy + p0.y * s, 2, 0, 7); ctx.fill();
    });
    ctx.fillStyle = '#999'; ctx.font = '10px sans-serif'; ctx.fillText(ch + ' ' + g.strokes.length, gx + 3, gy + cell - 4);
    // handwriting instance, drawn at cell size (1 mm = 1 px * k)
    const r = new Rng('sheet' + ch + (opts.seed || 0));
    const size = 10; // mm
    const k = cell / size;
    const sts = glyphStrokes(ch, { x: 0, y: 0, size, rng: r, tidy: opts.tidy });
    ctx.save(); ctx.translate(gx + cell, gy);
    sts.forEach((st) => drawStrokeSimple(ctx, st, k, 0.55, '#333'));
    ctx.restore();
  });
  return { url: c.toDataURL('image/png'), errors };
};

window.renderText = function (lines, opts = {}) {
  const size = opts.size || 6, W = opts.width || 1400, H = opts.height || 900, k = opts.k || 6;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const ctx = c.getContext('2d'); ctx.fillStyle = '#f7f3ea'; ctx.fillRect(0, 0, W, H);
  const r = new Rng('text' + (opts.seed || 0));
  let y = 4;
  for (const line of lines) {
    let x = 4;
    for (const ch of line) {
      if (ch === ' ') { x += size * 0.4; continue; }
      const sts = glyphStrokes(ch, { x, y, size, rng: r, tidy: opts.tidy });
      sts.forEach((st) => drawStrokeSimple(ctx, st, k, 0.42, '#2d2d33'));
      x += size * (/[一-鿿]/.test(ch) ? 1.0 : /[、。]/.test(ch) ? 0.55 : 0.86);
    }
    y += size * 1.55;
  }
  return c.toDataURL('image/png');
};
window.__ready = true;
