// Covers and endpapers: cloth over board, kraft endpapers, labels written in my hand.
import { PX, makeCanvas, planStroke, drawDabs, drawDots, toothCanvas } from './media.js';
import { writeText } from './layout.js';
import { Rng, noise2, hashStr } from './rng.js';

export const COVER_W = 153, COVER_H = 216;

function drawOps(g, ops, seed = 1) {
  ops.forEach((op, i) => {
    if (op.t === 'stroke') { const pl = planStroke(op, seed + i * 31); drawDabs(g, op, pl, 0, pl.dabs.length / 5); }
    else if (op.t === 'dots') drawDots(g, op, 0, op.pts.length / 2, seed + i);
  });
}

export function cloth(seed, rgb, W = COVER_W, H = COVER_H, wear = 1) {
  const c = makeCanvas(Math.round(W * PX), Math.round(H * PX));
  const g = c.getContext('2d', { willReadFrequently: true });
  const r = new Rng(seed);
  const w = c.width, h = c.height;
  g.fillStyle = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  g.fillRect(0, 0, w, h);
  // weave: fine warp and weft threads
  for (let y = 0; y < h; y += 2) { g.fillStyle = `rgba(255,255,255,${r.range(0.01, 0.045)})`; g.fillRect(0, y, w, 1); }
  for (let x = 0; x < w; x += 2) { g.fillStyle = `rgba(0,0,0,${r.range(0.02, 0.06)})`; g.fillRect(x, 0, 1, h); }
  // slubs in the thread
  for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(255,255,255,${r.range(0.02, 0.07)})`; g.fillRect(r.range(0, w), r.range(0, h), r.range(3, 14), 1); }
  // mottling
  const nz = noise2(seed + 5);
  const lw = 48, lh = 68, lc = makeCanvas(lw, lh), lg = lc.getContext('2d');
  const im = lg.createImageData(lw, lh);
  for (let y = 0; y < lh; y++) for (let x = 0; x < lw; x++) { const v = nz(x / 6, y / 6) * 0.7 + nz(x / 2, y / 2) * 0.3; const k = (y * lw + x) * 4; im.data[k] = im.data[k + 1] = im.data[k + 2] = 128 + (v - 0.5) * 60; im.data[k + 3] = 255; }
  lg.putImageData(im, 0, 0);
  g.save(); g.globalCompositeOperation = 'overlay'; g.globalAlpha = 0.35; g.drawImage(lc, 0, 0, w, h); g.restore();
  // wear: edges rubbed pale, corners bumped down to the board
  const edge = 5 * PX;
  const rub = (x0, y0, x1, y1, a) => { const gr = g.createLinearGradient(x0, y0, x1, y1); gr.addColorStop(0, `rgba(215,205,185,${a})`); gr.addColorStop(1, 'rgba(215,205,185,0)'); return gr; };
  g.fillStyle = rub(0, 0, 0, edge, 0.22 * wear); g.fillRect(0, 0, w, edge);
  g.fillStyle = rub(0, h, 0, h - edge, 0.25 * wear); g.fillRect(0, h - edge, w, edge);
  g.fillStyle = rub(w, 0, w - edge, 0, 0.28 * wear); g.fillRect(w - edge, 0, edge, h);
  for (const [cx, cy] of [[0, 0], [w, 0], [0, h], [w, h]]) {
    const gr = g.createRadialGradient(cx, cy, 0, cx, cy, 16 * PX);
    gr.addColorStop(0, `rgba(190,160,120,${0.55 * wear})`);
    gr.addColorStop(0.35, `rgba(200,180,150,${0.22 * wear})`);
    gr.addColorStop(1, 'rgba(200,180,150,0)');
    g.fillStyle = gr; g.fillRect(cx - 16 * PX, cy - 16 * PX, 32 * PX, 32 * PX);
  }
  // scuffs and a few scratches
  for (let i = 0; i < 24 * wear; i++) {
    const x = r.range(0, w), y = r.range(0, h), L = r.range(8, 60), a = r.range(-0.6, 0.6) + (r.chance(0.5) ? 0 : Math.PI / 2);
    g.strokeStyle = `rgba(230,220,200,${r.range(0.05, 0.16)})`;
    g.lineWidth = r.range(0.6, 1.8);
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
  }
  // where a hand holds it: slightly darker, a little polished
  const hg = g.createRadialGradient(w * 0.82, h * 0.55, 0, w * 0.82, h * 0.55, w * 0.45);
  hg.addColorStop(0, 'rgba(0,0,0,0.12)');
  hg.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = hg; g.fillRect(0, 0, w, h);
  return c;
}

export function kraft(seed, W = COVER_W, H = COVER_H) {
  const c = makeCanvas(Math.round(W * PX), Math.round(H * PX));
  const g = c.getContext('2d', { willReadFrequently: true });
  const r = new Rng(seed);
  g.fillStyle = 'rgb(205,178,138)';
  g.fillRect(0, 0, c.width, c.height);
  g.save(); g.globalAlpha = 0.25; g.fillStyle = g.createPattern(toothCanvas(), 'repeat'); g.fillRect(0, 0, c.width, c.height); g.restore();
  for (let i = 0; i < 1400; i++) {
    g.strokeStyle = r.chance(0.5) ? `rgba(120,85,45,${r.range(0.04, 0.12)})` : `rgba(240,220,190,${r.range(0.05, 0.15)})`;
    g.lineWidth = r.range(0.5, 1.2);
    const x = r.range(0, c.width), y = r.range(0, c.height), a = r.range(0, 6.3), L = r.range(4, 18);
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
  }
  // board edge shadow line where the endpaper folds into the spine
  return c;
}

function label(g, x, y, w, h, rot, seed) {
  const r = new Rng(seed);
  g.save();
  g.translate(x * PX, y * PX);
  g.rotate(rot);
  g.fillStyle = 'rgba(0,0,0,0.25)';
  g.fillRect(-w * PX / 2 + 3, -h * PX / 2 + 4, w * PX, h * PX);
  g.fillStyle = 'rgb(238,230,210)';
  g.fillRect(-w * PX / 2, -h * PX / 2, w * PX, h * PX);
  g.globalAlpha = 0.14; g.fillStyle = g.createPattern(toothCanvas(), 'repeat'); g.fillRect(-w * PX / 2, -h * PX / 2, w * PX, h * PX); g.globalAlpha = 1;
  // printed rule lines, a little faded
  g.strokeStyle = 'rgba(150,120,110,0.45)';
  g.lineWidth = 1.2;
  g.strokeRect(-w * PX / 2 + 2 * PX, -h * PX / 2 + 2 * PX, (w - 4) * PX, (h - 4) * PX);
  // corner lifted a bit, grime on it
  g.fillStyle = 'rgba(120,100,70,0.18)';
  g.beginPath(); g.moveTo(w * PX / 2, -h * PX / 2); g.lineTo(w * PX / 2 - 5 * PX, -h * PX / 2); g.lineTo(w * PX / 2, -h * PX / 2 + 5 * PX); g.fill();
  g.restore();
}

// text written straight onto a cover canvas (x, y in mm of that canvas)
function write(g, text, o) {
  const ops = writeText(text, { seed: hashStr(text), ...o });
  drawOps(g, ops, hashStr(text + 'd'));
}

export function frontOutside() {
  const c = cloth(71, [38, 56, 58]);
  const g = c.getContext('2d');
  label(g, 102, 44, 52, 26, -0.035, 7);
  g.save();
  g.translate(102 * PX, 44 * PX); g.rotate(-0.035); g.translate(-102 * PX, -44 * PX);
  write(g, 'Claude', { x: 81, y: 33, size: 8, medium: 'ink', tidy: 0.85 });
  write(g, 'sketchbook  no.1', { x: 81, y: 45, size: 4.2, medium: 'ink', tidy: 0.7 });
  g.restore();
  return c;
}

export function frontInside() {
  const c = kraft(72);
  const g = c.getContext('2d');
  write(g, 'Claude', { x: 26, y: 28, size: 9, medium: 'ink', tidy: 0.85 });
  write(g, 'スケッチブック no.1', { x: 26, y: 44, size: 5.2, medium: 'ink', tidy: 0.75 });
  write(g, '2026 秋 〜', { x: 26, y: 54, size: 4.6, medium: 'ink', tidy: 0.7 });
  write(g, '拾ったかたへ:\n読んでもかまいません。\n半分はまだ考えている途中です。', { x: 26, y: 150, size: 4.4, lh: 1.7, medium: 'ink', tidy: 0.65 });
  return c;
}

export function backInside() {
  const c = kraft(73);
  return c;
}

// the back cover: a label with the number of lines in this book
export function backOutside(total, reader) {
  const c = cloth(74, [38, 56, 58], COVER_W, COVER_H, 0.8);
  const g = c.getContext('2d');
  label(g, 76, 150, 74, 36, 0.02, 9);
  g.save();
  g.translate(76 * PX, 150 * PX); g.rotate(0.02); g.translate(-76 * PX, -150 * PX);
  write(g, 'この本の線', { x: 46, y: 136, size: 4.6, medium: 'ink', tidy: 0.75 });
  write(g, total.toLocaleString('en-US') + ' 本', { x: 48, y: 145.5, size: 8.2, medium: 'ink', tidy: 0.85 });
  if (reader > 0) write(g, '(うち ' + reader.toLocaleString('en-US') + ' 本は、あなたの線)', { x: 46, y: 158, size: 3.4, medium: 'ink', tidy: 0.7 });
  else write(g, '(最後のページは、まだ白い)', { x: 46, y: 158, size: 3.4, medium: 'ink', tidy: 0.7 });
  g.restore();
  return c;
}
