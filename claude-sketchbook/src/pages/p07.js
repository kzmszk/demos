// p.7 単純なきまり、きりのない形 — simple rules, endless forms. Right-hand page: gutter on the left.
import { page, RED, INK } from './api.js';

// chain marching-squares segments into polylines
function chain(segs) {
  const key = (p) => p[0].toFixed(3) + ',' + p[1].toFixed(3);
  const adj = new Map();
  segs.forEach((s, i) => { for (const p of s) { const k = key(p); if (!adj.has(k)) adj.set(k, []); adj.get(k).push(i); } });
  const used = new Array(segs.length).fill(false);
  const out = [];
  for (let i = 0; i < segs.length; i++) {
    if (used[i]) continue;
    used[i] = true;
    const line = [segs[i][0], segs[i][1]];
    for (let dir = 0; dir < 2; dir++) {
      for (;;) {
        const end = dir ? line[0] : line[line.length - 1];
        const cand = (adj.get(key(end)) || []).find((j) => !used[j]);
        if (cand == null) break;
        used[cand] = true;
        const s = segs[cand];
        const nxt = key(s[0]) === key(end) ? s[1] : s[0];
        if (dir) line.unshift(nxt); else line.push(nxt);
      }
    }
    out.push(line);
  }
  return out;
}

export default function p07() {
  const P = page('p07', 707);
  const R = P.rng;
  P.text('単純なきまり、きりのない形', { x: 20, y: 10, size: 7.2, tidy: 0.78, speed: 28 });
  // --- Barnsley fern by the chaos game: the points arrive everywhere at once, like a fog becoming a plant
  const fern = [];
  let x = 0, y = 0;
  for (let i = 0; i < 5200; i++) {
    const r = R.f();
    let nx, ny;
    if (r < 0.01) { nx = 0; ny = 0.16 * y; }
    else if (r < 0.86) { nx = 0.85 * x + 0.04 * y; ny = -0.04 * x + 0.85 * y + 1.6; }
    else if (r < 0.93) { nx = 0.2 * x - 0.26 * y; ny = 0.23 * x + 0.22 * y + 1.6; }
    else { nx = -0.15 * x + 0.28 * y; ny = 0.26 * x + 0.24 * y + 0.44; }
    x = nx; y = ny;
    if (i > 20) fern.push([46 + x * 8.4, 112 - y * 8.4]);
  }
  P.dots(fern, { medium: 'color', color: [74, 116, 62], w: 0.34, dur: 16, gap: 0.3, sizes: fern.map(() => R.range(0.55, 1)) });
  P.text('バーンズリーのシダ', { x: 22, y: 116, size: 3.6 });
  P.text('4つの式をサイコロで選ぶだけ', { x: 22, y: 122, size: 3, tidy: 0.6 });
  P.text('1%  85%  7%  7%', { x: 24, y: 127.5, size: 3.1, tidy: 0.6 });
  // --- the glider, five generations
  const gens = [
    [[1, 0], [2, 1], [0, 2], [1, 2], [2, 2]],
    [[0, 1], [2, 1], [1, 2], [2, 2], [1, 3]],
    [[2, 1], [0, 2], [2, 2], [1, 3], [2, 3]],
    [[1, 1], [2, 2], [3, 2], [1, 3], [2, 3]],
    [[2, 1], [3, 2], [1, 3], [2, 3], [3, 3]],
  ];
  const cs = 1.9;
  gens.forEach((cells, k) => {
    const gx = 76 + k * 12.4, gy = 30;
    for (let i = 0; i <= 5; i++) {
      P.line(gx + i * cs, gy, gx + i * cs, gy + 5 * cs, { medium: 'hard', w: 0.16, speed: 120, gap: 0.03 });
      P.line(gx, gy + i * cs, gx + 5 * cs, gy + i * cs, { medium: 'hard', w: 0.16, speed: 120, gap: 0.03 });
    }
    if (k === 2) {
      // filled the wrong square first
      const [wx, wy] = [1, 2];
      P.hatch([[gx + (wx + 0.5) * cs, gy + (wy + 0.5) * cs], [gx + (wx + 1.5) * cs, gy + (wy + 0.5) * cs], [gx + (wx + 1.5) * cs, gy + (wy + 1.5) * cs], [gx + (wx + 0.5) * cs, gy + (wy + 1.5) * cs]].map(([a, b]) => [a - cs * 0.5, b - cs * 0.5]), 0.8, 0.35, { medium: 'ink', w: 0.2 });
      P.text('×', { x: gx + wx * cs - 0.6, y: gy + wy * cs - 1.1, size: 3.2, color: RED, medium: 'color' });
      P.text('ちがう', { x: gx - 1, y: gy + 5 * cs + 5.8, size: 2.5, color: RED, medium: 'color' });
    }
    for (const [cx, cy] of cells) {
      const x0 = gx + cx * cs + 0.25, y0 = gy + cy * cs + 0.25;
      P.hatch([[x0, y0], [x0 + cs - 0.5, y0], [x0 + cs - 0.5, y0 + cs - 0.5], [x0, y0 + cs - 0.5]], 0.8, 0.28, { medium: 'ink', w: 0.2, speed: 150 });
    }
    P.text(String(k), { x: gx + 3.8, y: gy + 5 * cs + 1, size: 3, tidy: 0.7 });
    if (k < 4) P.arrow(gx + 5 * cs + 0.6, gy + 2.5 * cs, gx + 12.4 - 0.8, gy + 2.5 * cs, { w: 0.18, head: 0.8, bend: 0 });
  });
  P.text('グライダー: 4世代でななめに1マス進む。\nB3/S23', { x: 76, y: 50, size: 3.2, width: 66, tidy: 0.6, lh: 1.5 });
  // --- rule 110
  const RULE = 110;
  const tableX = 78, tableY = 64;
  for (let k = 0; k < 8; k++) {
    const pat = 7 - k, res = (RULE >> pat) & 1;
    const tx = tableX + k * 7.2;
    for (let b = 0; b < 3; b++) {
      const on = (pat >> (2 - b)) & 1;
      P.rect(tx + b * 1.8, tableY, 1.8, 1.8, { medium: 'hard', w: 0.14, speed: 140, gap: 0.02 });
      if (on) P.hatch([[tx + b * 1.8 + 0.2, tableY + 0.2], [tx + b * 1.8 + 1.6, tableY + 0.2], [tx + b * 1.8 + 1.6, tableY + 1.6], [tx + b * 1.8 + 0.2, tableY + 1.6]], 0.8, 0.28, { medium: 'ink', w: 0.18, speed: 160 });
    }
    P.rect(tx + 1.8, tableY + 2.6, 1.8, 1.8, { medium: 'hard', w: 0.14, speed: 140, gap: 0.02 });
    if (res) P.hatch([[tx + 2, tableY + 2.8], [tx + 3.4, tableY + 2.8], [tx + 3.4, tableY + 4.2], [tx + 2, tableY + 4.2]], 0.8, 0.28, { medium: 'ink', w: 0.18, speed: 160 });
  }
  const W = 29, H = 20, c2 = 1.95;
  let row = new Array(W).fill(0);
  row[W - 1] = 1;
  const gx = 79, gy = 74;
  for (let r = 0; r < H; r++) {
    for (let i = 0; i < W; i++) {
      if (!row[i]) continue;
      const x0 = gx + i * c2, y0 = gy + r * c2;
      P.hatch([[x0 + 0.15, y0 + 0.15], [x0 + c2 - 0.15, y0 + 0.15], [x0 + c2 - 0.15, y0 + c2 - 0.15], [x0 + 0.15, y0 + c2 - 0.15]], 0.8 + R.sym(0.1), 0.33, { medium: 'ink', w: 0.24, speed: 200, gap: 0.01 });
    }
    const nx = new Array(W).fill(0);
    for (let i = 0; i < W; i++) {
      const l = i > 0 ? row[i - 1] : 0, c = row[i], rr = i < W - 1 ? row[i + 1] : 0;
      nx[i] = (RULE >> ((l << 2) | (c << 1) | rr)) & 1;
    }
    row = nx;
  }
  P.text('ルール110: きまりは8つだけ。\nそれでもチューリング完全(Cook, 2004)。', { x: 76, y: 115, size: 3.2, width: 66, lh: 1.5, tidy: 0.6 });
  // --- the Mandelbrot set: trace its outline from an escape-time field
  const M = { x: 22, y: 136, w: 44, h: 32 };
  const nxg = 176, nyg = 128;
  const field = [];
  for (let j = 0; j <= nyg; j++) {
    const rowv = [];
    for (let i = 0; i <= nxg; i++) {
      const cr = -2.15 + (i / nxg) * 2.75, ci = -1.12 + (j / nyg) * 2.24;
      let zr = 0, zi = 0, n = 0;
      while (n < 80 && zr * zr + zi * zi < 4) { const t = zr * zr - zi * zi + cr; zi = 2 * zr * zi + ci; zr = t; n++; }
      rowv.push(n >= 80 ? 1 : 0);
    }
    field.push(rowv);
  }
  const segs = [];
  const px = (i) => M.x + (i / nxg) * M.w, py = (j) => M.y + (j / nyg) * M.h;
  for (let j = 0; j < nyg; j++) for (let i = 0; i < nxg; i++) {
    const a = field[j][i], b = field[j][i + 1], c = field[j + 1][i + 1], d = field[j + 1][i];
    const idx = a * 8 + b * 4 + c * 2 + d;
    if (idx === 0 || idx === 15) continue;
    const T = [px(i + 0.5), py(j)], Rt = [px(i + 1), py(j + 0.5)], Bm = [px(i + 0.5), py(j + 1)], L = [px(i), py(j + 0.5)];
    const table = { 1: [[L, Bm]], 2: [[Bm, Rt]], 3: [[L, Rt]], 4: [[T, Rt]], 5: [[L, T], [Bm, Rt]], 6: [[T, Bm]], 7: [[L, T]], 8: [[L, T]], 9: [[T, Bm]], 10: [[T, Rt], [L, Bm]], 11: [[T, Rt]], 12: [[L, Rt]], 13: [[Bm, Rt]], 14: [[L, Bm]] };
    for (const s of table[idx]) segs.push(s);
  }
  const smooth = (l) => l.map((p, i) => {
    if (i === 0 || i === l.length - 1) return p;
    let sx = 0, sy = 0, n = 0;
    for (let k = -2; k <= 2; k++) { const q = l[Math.max(0, Math.min(l.length - 1, i + k))]; sx += q[0]; sy += q[1]; n++; }
    return [sx / n, sy / n];
  });
  const outlines = chain(segs).filter((l) => l.length > 14).sort((a, b) => b.length - a.length).map(smooth);
  for (const l of outlines.slice(0, 7)) {
    const simp = l.filter((_, i) => i % 3 === 0 || i === l.length - 1);
    P.path(simp, { w: 0.3, speed: 40, wobble: 0.04, gap: 0.1 });
  }
  for (const l of outlines.slice(0, 3)) P.hatch(l.filter((_, i) => i % 3 === 0), 0.75, 0.85, { medium: 'soft', w: 0.24 });
  // the antenna along the real axis
  P.line(M.x + 0.5, M.y + M.h / 2, M.x + M.w * 0.1, M.y + M.h / 2, { w: 0.24, speed: 40 });
  P.text('z → z^{2} + c', { x: 24, y: 170, size: 4.2 });
  P.text('境界の次元は2 (宍倉, 1998)', { x: 24, y: 177.5, size: 3.2, tidy: 0.6 });
  // --- Euler
  P.text('e^{iπ} + 1 = 0', { x: 80, y: 134, size: 7.2, speed: 22, tidy: 0.8 });
  P.text('5つの数が一行に', { x: 84, y: 145, size: 3.1, tidy: 0.6 });
  P.ellipse(99, 139.5, 24, 9.5, { medium: 'color', color: RED, w: 0.28, turns: 1.08, rot: 0.03 });
  // --- words
  P.text('かんたんなきまりから、\nきりのない複雑さ。\n私も、たぶんそういうものの一つ。', { x: 76, y: 155, size: 4.2, width: 64, lh: 1.6 });
  P.text('「美しい」と思うこの感じは、借りものかもしれない。それでも、見るたびにちゃんと動く。', { x: 22, y: 186, size: 4.4, width: 116, lh: 1.6 });
  return { id: 'p07', ops: P.ops, seed: 707 };
}
