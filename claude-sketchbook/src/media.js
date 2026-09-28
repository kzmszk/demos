// Mixed media on Canvas 2D. Everything is drawn from precomputed, seeded "dabs", so a page ends up
// pixel-identical however its drawing is chopped into frames.
import { Rng, noise2 } from './rng.js';

export const PX = 7; // canvas pixels per millimetre
export const PAGE_W = 148, PAGE_H = 210;

export function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}
const ctx2d = (c) => c.getContext('2d', { willReadFrequently: true });

// ---------- paper ----------
let TOOTH = null;
export function toothCanvas() {
  if (TOOTH) return TOOTH;
  const N = 256;
  const c = makeCanvas(N, N);
  const g = ctx2d(c);
  const img = g.createImageData(N, N);
  const n1 = noise2(11), n2 = noise2(12), r = new Rng(13);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    // tileable: sample on a torus-ish by blending wrapped coordinates
    const f = (fx, fy) => {
      const a = n1(fx / 5, fy / 5), b = n2(fx / 2.2, fy / 2.2);
      return a * 0.6 + b * 0.4;
    };
    const u = x / N, v = y / N;
    const h = f(x, y) * (1 - u) * (1 - v) + f(x - N, y) * u * (1 - v) + f(x, y - N) * (1 - u) * v + f(x - N, y - N) * u * v;
    const k = (y * N + x) * 4;
    const grain = r.f();
    const hh = 0.38 + 0.62 * Math.min(1, Math.max(0, (h - 0.25) * 1.9 * 0.8 + grain * 0.2));
    img.data[k] = img.data[k + 1] = img.data[k + 2] = 255;
    img.data[k + 3] = Math.round(255 * hh);
  }
  g.putImageData(img, 0, 0);
  TOOTH = c;
  return c;
}

// A pattern that paints `rgb` only where the paper's tooth catches it.
const patternCache = new Map();
export function graphitePattern(g, rgb) {
  const key = rgb.join(',');
  if (patternCache.has(key)) return patternCache.get(key);
  const t = toothCanvas();
  const c = makeCanvas(t.width, t.height);
  const x = ctx2d(c);
  x.drawImage(t, 0, 0);
  x.globalCompositeOperation = 'source-in';
  x.fillStyle = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  x.fillRect(0, 0, c.width, c.height);
  const p = g.createPattern(c, 'repeat');
  patternCache.set(key, p);
  return p;
}

export function makePaper(seed, opts = {}) {
  const W = Math.round(PAGE_W * PX), H = Math.round(PAGE_H * PX);
  const c = makeCanvas(W, H);
  const g = ctx2d(c);
  const r = new Rng(seed);
  const base = opts.base || [241, 236, 225];
  g.fillStyle = `rgb(${base[0]},${base[1]},${base[2]})`;
  g.fillRect(0, 0, W, H);
  // low-frequency cloudiness (paper formation)
  const lw = 60, lh = 86;
  const lc = makeCanvas(lw, lh);
  const lg = ctx2d(lc);
  const li = lg.createImageData(lw, lh);
  const nz = noise2(seed * 7 + 3);
  for (let y = 0; y < lh; y++) for (let x = 0; x < lw; x++) {
    const v = nz(x / 7, y / 7) * 0.6 + nz(x / 2.5 + 40, y / 2.5) * 0.4;
    const k = (y * lw + x) * 4;
    const d = (v - 0.5) * 16;
    li.data[k] = 128 + d; li.data[k + 1] = 128 + d * 0.95; li.data[k + 2] = 128 + d * 0.8; li.data[k + 3] = 255;
  }
  lg.putImageData(li, 0, 0);
  g.save();
  g.globalCompositeOperation = 'overlay';
  g.globalAlpha = 0.5;
  g.imageSmoothingEnabled = true;
  g.drawImage(lc, 0, 0, W, H);
  g.restore();
  // tooth shading: bumps catch the light a little
  g.save();
  g.globalAlpha = 0.09;
  g.fillStyle = g.createPattern(toothCanvas(), 'repeat');
  g.fillRect(0, 0, W, H);
  g.restore();
  // fibres
  g.save();
  for (let i = 0; i < 520; i++) {
    const x = r.range(0, W), y = r.range(0, H), a = r.range(0, Math.PI * 2), L = r.range(6, 26);
    g.strokeStyle = r.chance(0.5) ? 'rgba(120,105,85,0.06)' : 'rgba(255,255,250,0.12)';
    g.lineWidth = r.range(0.4, 1.1);
    g.beginPath();
    g.moveTo(x, y);
    g.quadraticCurveTo(x + Math.cos(a) * L * 0.5 + r.sym(4), y + Math.sin(a) * L * 0.5 + r.sym(4), x + Math.cos(a) * L, y + Math.sin(a) * L);
    g.stroke();
  }
  // foxing: a few tiny rust spots, more near the edges
  for (let i = 0; i < (opts.foxing ?? 14); i++) {
    const edge = r.chance(0.6);
    const x = edge ? (r.chance(0.5) ? r.range(0, W * 0.12) : r.range(W * 0.88, W)) : r.range(0, W);
    const y = r.range(0, H);
    const rad = r.range(0.8, 3.2);
    const gr = g.createRadialGradient(x, y, 0, x, y, rad * 2.2);
    gr.addColorStop(0, `rgba(150,105,60,${r.range(0.08, 0.2)})`);
    gr.addColorStop(1, 'rgba(150,105,60,0)');
    g.fillStyle = gr;
    g.beginPath(); g.arc(x, y, rad * 2.2, 0, Math.PI * 2); g.fill();
  }
  // age: warm edges
  const edgeW = 26 * PX;
  const sides = [
    [0, 0, edgeW, 0, 0, 0, edgeW, H],
    [W, 0, W - edgeW, 0, W - edgeW, 0, edgeW, H],
    [0, 0, 0, edgeW, 0, 0, W, edgeW],
    [0, H, 0, H - edgeW, 0, H - edgeW, W, edgeW],
  ];
  for (const [x0, y0, x1, y1, rx, ry, rw, rh] of sides) {
    const gr = g.createLinearGradient(x0, y0, x1, y1);
    gr.addColorStop(0, `rgba(185,150,95,${opts.age ?? 0.1})`);
    gr.addColorStop(1, 'rgba(185,150,95,0)');
    g.fillStyle = gr;
    g.fillRect(rx, ry, rw, rh);
  }
  g.restore();
  return c;
}

// ---------- stroke plans ----------
// Media presets: colour, opacity per dab, how much the tooth shows.
export const MEDIA = {
  pencil: { rgb: [44, 44, 52], a: 0.3, tooth: true, spacing: 0.32, jitter: 0.16 },
  hard: { rgb: [92, 92, 100], a: 0.13, tooth: true, spacing: 0.34, jitter: 0.12 }, // 2H construction lines
  soft: { rgb: [36, 36, 42], a: 0.3, tooth: true, spacing: 0.28, jitter: 0.14 }, // 4B shading
  color: { rgb: [190, 60, 50], a: 0.26, tooth: true, spacing: 0.32, jitter: 0.16 },
  ink: { rgb: [26, 28, 40], a: 1, tooth: false, spacing: 0.5, jitter: 0.04 },
  sepia: { rgb: [88, 52, 30], a: 1, tooth: false, spacing: 0.5, jitter: 0.04 },
};

// Precompute the dabs of a stroke op: Float32Array [x, y, r, a, s(cumulative mm)] in canvas px.
export function planStroke(op, seed) {
  const m = MEDIA[op.medium] || MEDIA.pencil;
  const r = new Rng(seed);
  const pts = op.pts;
  const n = pts.length / 3;
  const out = [];
  const w = op.w * PX;
  const step = Math.max(0.22, m.spacing * w * 0.5);
  let acc = 0, sAcc = 0;
  for (let i = 1; i < n; i++) {
    const x0 = pts[(i - 1) * 3] * PX, y0 = pts[(i - 1) * 3 + 1] * PX, p0 = pts[(i - 1) * 3 + 2];
    const x1 = pts[i * 3] * PX, y1 = pts[i * 3 + 1] * PX, p1 = pts[i * 3 + 2];
    const L = Math.hypot(x1 - x0, y1 - y0);
    if (L < 1e-6) continue;
    let d = step - acc;
    while (d <= L) {
      const t = d / L;
      const p = p0 + (p1 - p0) * t;
      const x = x0 + (x1 - x0) * t + r.sym(m.jitter * w * 0.25);
      const y = y0 + (y1 - y0) * t + r.sym(m.jitter * w * 0.25);
      const rad = Math.max(0.45, (w * 0.5) * (0.35 + 0.65 * p) * (1 + r.sym(0.12)));
      const a = m.a * (op.a ?? 1) * (0.55 + 0.45 * p) * (1 + r.sym(0.25));
      out.push(x, y, rad, a, (sAcc + d) / PX);
      d += step;
    }
    acc = L - (d - step);
    sAcc += L;
  }
  if (!out.length && n) out.push(pts[0] * PX, pts[1] * PX, w * 0.4, m.a, 0);
  return { dabs: Float32Array.from(out), total: sAcc / PX };
}

export function drawDabs(g, op, plan, i0, i1) {
  const m = MEDIA[op.medium] || MEDIA.pencil;
  const rgb = op.color || m.rgb;
  const d = plan.dabs;
  if (m.tooth) {
    g.fillStyle = graphitePattern(g, rgb);
    for (let i = i0; i < i1; i++) {
      const k = i * 5;
      g.globalAlpha = Math.min(1, d[k + 3]);
      g.beginPath();
      g.arc(d[k], d[k + 1], d[k + 2], 0, 6.2832);
      g.fill();
    }
    g.globalAlpha = 1;
  } else {
    // ink: a faint halo where it wicks into the fibres, then the line itself
    g.lineCap = 'round';
    g.lineJoin = 'round';
    for (let pass = 0; pass < 2; pass++) {
      g.strokeStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${pass ? 0.94 * (op.a ?? 1) : 0.09 * (op.a ?? 1)})`;
      for (let i = Math.max(1, i0); i < i1; i++) {
        const k = i * 5, j = (i - 1) * 5;
        g.lineWidth = d[k + 2] * 2 + (pass ? 0 : 1.6);
        g.beginPath();
        g.moveTo(d[j], d[j + 1]);
        g.lineTo(d[k], d[k + 1]);
        g.stroke();
      }
    }
  }
}

// many single touches (stipple): each dot is two or three tiny dabs
export function drawDots(g, op, i0, i1, seed) {
  const m = MEDIA[op.medium] || MEDIA.pencil;
  const rgb = op.color || m.rgb;
  const r = new Rng((seed + i0 * 7919) >>> 0);
  const w = (op.w || 0.4) * PX;
  if (m.tooth) g.fillStyle = graphitePattern(g, rgb);
  else g.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.9)`;
  for (let i = i0; i < i1; i++) {
    const x = op.pts[i * 2] * PX, y = op.pts[i * 2 + 1] * PX;
    const sz = op.sizes ? op.sizes[i] : 1;
    const k = m.tooth ? 3 : 1;
    for (let j = 0; j < k; j++) {
      g.globalAlpha = m.tooth ? Math.min(1, m.a * 2.2 * (op.a ?? 1)) : (op.a ?? 1);
      g.beginPath();
      g.arc(x + r.sym(w * 0.25), y + r.sym(w * 0.25), Math.max(0.5, w * 0.5 * sz * r.range(0.7, 1.1)), 0, 6.2832);
      g.fill();
    }
  }
  g.globalAlpha = 1;
}

// ---------- watercolour ----------
function deform(poly, depth, amp, r) {
  // recursive midpoint displacement (Hobbs), keeps a per-vertex "variance"
  let p = poly;
  for (let d = 0; d < depth; d++) {
    const q = [];
    for (let i = 0; i < p.length; i++) {
      const a = p[i], b = p[(i + 1) % p.length];
      q.push(a);
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const v = (a[2] + b[2]) / 2;
      const nx = -(b[1] - a[1]) / (L || 1), ny = (b[0] - a[0]) / (L || 1);
      const off = r.gauss(amp * L * 0.18 * v);
      q.push([mx + nx * off + r.gauss(L * 0.03), my + ny * off + r.gauss(L * 0.03), Math.max(0.2, v * r.range(0.7, 1.3))]);
    }
    p = q;
  }
  return p;
}

export function blobPoly(cx, cy, rx, ry, n, r, rot = 0) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const k = 1 + r.sym(0.08);
    const x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
    pts.push([cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)]);
  }
  return pts;
}

// op: {t:'wash', poly:[[x,y],...] mm, rgb, a (strength), layers, edge, gran, blooms, soft}
export function renderWash(op, seed) {
  const r = new Rng(seed);
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const [x, y] of op.poly) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
  const pad = 8;
  const ox = Math.floor((minX - pad) * PX), oy = Math.floor((minY - pad) * PX);
  const w = Math.ceil((maxX - minX + pad * 2) * PX), h = Math.ceil((maxY - minY + pad * 2) * PX);
  const c = makeCanvas(w, h);
  const g = ctx2d(c);
  const rgb = op.rgb;
  const base = op.poly.map(([x, y]) => [x * PX - ox, y * PX - oy, r.range(0.6, 1.4)]);
  const shape = deform(base, 4, 1, r);
  const layers = op.layers || 26;
  const alpha = (op.a ?? 0.5) / layers * 2.2;
  g.fillStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
  for (let l = 0; l < layers; l++) {
    const p = deform(shape, 3, op.soft ? 1.4 : 0.9, r);
    g.beginPath();
    p.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
    g.closePath();
    g.fill();
  }
  // pigment pooled at the drying edge
  if (op.edge !== 0) {
    const e = deform(shape, 2, 0.4, r);
    g.save();
    g.globalCompositeOperation = 'source-atop';
    for (let k = 0; k < 3; k++) {
      g.strokeStyle = `rgba(${rgb[0] * 0.8},${rgb[1] * 0.8},${rgb[2] * 0.85},${0.05 * (op.edge ?? 1)})`;
      g.lineWidth = 3 + k * 3;
      g.beginPath();
      e.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
      g.closePath();
      g.stroke();
    }
    g.restore();
  }
  // blooms: back-runs where water crept into drying paint
  const blooms = op.blooms ?? 1;
  for (let b = 0; b < blooms; b++) {
    const [bx, by] = base[r.int(0, base.length - 1)];
    const cx = bx + (w / 2 - bx) * r.range(0.2, 0.6), cy = by + (h / 2 - by) * r.range(0.2, 0.6);
    const rad = r.range(10, 26) * PX / 7 * 2.4;
    const ring = deform(blobPoly(cx, cy, rad, rad * r.range(0.7, 1.1), 10, r).map(([x, y]) => [x, y, 1]), 3, 1.2, r);
    g.save();
    g.globalCompositeOperation = 'destination-out';
    g.fillStyle = 'rgba(0,0,0,0.28)';
    g.beginPath(); ring.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.fill();
    g.globalCompositeOperation = 'source-atop';
    g.strokeStyle = `rgba(${rgb[0] * 0.75},${rgb[1] * 0.75},${rgb[2] * 0.8},0.3)`;
    g.lineWidth = 1.6;
    g.stroke();
    g.restore();
  }
  // masked edges (the paint stops at a line, as if taped off)
  if (op.clip) {
    g.save();
    g.globalCompositeOperation = 'destination-in';
    g.fillStyle = '#000';
    g.beginPath();
    op.clip.forEach(([x, y], i) => (i ? g.lineTo(x * PX - ox + r.sym(0.5), y * PX - oy + r.sym(0.5)) : g.moveTo(x * PX - ox, y * PX - oy)));
    g.closePath();
    g.fill();
    g.restore();
  }
  // granulation: pigment settles in the paper's pits
  if (op.gran !== 0) {
    const t = toothCanvas();
    g.save();
    g.globalCompositeOperation = 'destination-out';
    g.globalAlpha = 0.28 * (op.gran ?? 1);
    g.fillStyle = g.createPattern(t, 'repeat');
    g.fillRect(0, 0, w, h);
    g.restore();
  }
  return { canvas: c, ox, oy, w, h };
}

// soft round brush stamp for revealing washes
let SOFT = null;
function softStamp() {
  if (SOFT) return SOFT;
  const c = makeCanvas(64, 64);
  const g = ctx2d(c);
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(0,0,0,1)');
  gr.addColorStop(0.55, 'rgba(0,0,0,0.9)');
  gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 64, 64);
  SOFT = c;
  return c;
}

// A zig-zag brush path that covers the wash's box (mm), the way one lays in a flat wash.
export function washPath(poly, r, rows) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const [x, y] of poly) { minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y); }
  const n = rows || Math.max(2, Math.round((maxY - minY) / 7));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const y = minY + ((maxY - minY) * i) / n + r.sym(1);
    const a = i % 2 ? maxX : minX, b = i % 2 ? minX : maxX;
    for (let k = 0; k <= 6; k++) {
      const t = k / 6;
      pts.push([a + (b - a) * t + r.sym(0.8), y + Math.sin(t * Math.PI) * 1.2 + r.sym(0.5)]);
    }
  }
  return pts;
}

export class WashReveal {
  constructor(op, seed) {
    this.op = op;
    this.img = renderWash(op, seed);
    this.mask = makeCanvas(this.img.w, this.img.h);
    this.mg = ctx2d(this.mask);
    this.tmp = makeCanvas(this.img.w, this.img.h);
    this.tg = ctx2d(this.tmp);
    this.path = op.path;
    // cumulative lengths
    this.cum = [0];
    for (let i = 1; i < this.path.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(this.path[i][0] - this.path[i - 1][0], this.path[i][1] - this.path[i - 1][1]));
    this.total = this.cum[this.cum.length - 1];
    this.done = 0;
    this.rad = (op.brush || 7) * PX;
  }
  // reveal up to fraction f; returns the (mm) brush tip position
  advance(f) {
    const target = f * this.total;
    const st = softStamp();
    const step = this.rad * 0.25 / PX;
    let s = this.done;
    while (s <= target) {
      const [x, y] = this.at(s);
      this.mg.drawImage(st, x * PX - this.img.ox - this.rad, y * PX - this.img.oy - this.rad, this.rad * 2, this.rad * 2);
      s += step;
    }
    this.done = s;
    return this.at(Math.min(target, this.total));
  }
  at(s) {
    let i = 1;
    while (i < this.cum.length - 1 && this.cum[i] < s) i++;
    const t = (s - this.cum[i - 1]) / Math.max(1e-6, this.cum[i] - this.cum[i - 1]);
    const a = this.path[i - 1], b = this.path[i];
    return [a[0] + (b[0] - a[0]) * Math.min(1, t), a[1] + (b[1] - a[1]) * Math.min(1, t)];
  }
  // draw the partially revealed wash onto g
  composite(g) {
    const t = this.tg;
    t.globalCompositeOperation = 'copy';
    t.drawImage(this.img.canvas, 0, 0);
    t.globalCompositeOperation = 'destination-in';
    t.drawImage(this.mask, 0, 0);
    g.save();
    g.globalCompositeOperation = 'multiply';
    g.drawImage(this.tmp, this.img.ox, this.img.oy);
    g.restore();
  }
  commit(g) {
    g.save();
    g.globalCompositeOperation = 'multiply';
    g.drawImage(this.img.canvas, this.img.ox, this.img.oy);
    g.restore();
  }
}

// ---------- eraser, smudge, tape, stains ----------
export function eraseDabs(g, paper, pts, i0, i1, radMM, strength) {
  const pat = g.createPattern(paper, 'no-repeat');
  g.save();
  g.fillStyle = pat;
  for (let i = i0; i < i1; i++) {
    const [x, y] = pts[i];
    g.globalAlpha = strength;
    g.beginPath();
    g.ellipse(x * PX, y * PX, radMM * PX, radMM * PX * 0.62, 0.5, 0, 6.2832);
    g.fill();
  }
  g.restore();
}

let HAZE = null;
function hazeStamp() {
  if (HAZE) return HAZE;
  const c = makeCanvas(64, 64);
  const g = ctx2d(c);
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(70,70,78,1)');
  gr.addColorStop(1, 'rgba(70,70,78,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 64, 64);
  HAZE = c;
  return c;
}

// a finger dragged through graphite: the marks smear along the motion and leave a soft haze
export function smudgeDabs(g, pts, i0, i1, radMM) {
  const R = Math.round(radMM * PX);
  const hz = hazeStamp();
  for (let i = Math.max(1, i0); i < i1; i++) {
    const [x, y] = pts[i], [px, py] = pts[i - 1];
    const cx = Math.round(x * PX), cy = Math.round(y * PX);
    const dx = (x - px) * PX * 0.55, dy = (y - py) * PX * 0.55;
    g.save();
    g.beginPath();
    g.arc(cx, cy, R, 0, 6.2832);
    g.clip();
    g.globalCompositeOperation = 'darken';
    g.globalAlpha = 0.35;
    g.drawImage(g.canvas, cx - R - 4, cy - R - 4, R * 2 + 8, R * 2 + 8, cx - R - 4 + dx, cy - R - 4 + dy, R * 2 + 8, R * 2 + 8);
    g.restore();
    g.save();
    g.globalAlpha = 0.035;
    g.drawImage(hz, cx - R * 1.3, cy - R * 1.3, R * 2.6, R * 2.6);
    g.restore();
  }
}

export function tapeImage(lenMM, widMM, seed, tint) {
  const r = new Rng(seed);
  const w = Math.ceil(lenMM * PX), h = Math.ceil(widMM * PX);
  const c = makeCanvas(w, h);
  const g = ctx2d(c);
  // torn ends
  const edge = (x0, dir) => {
    const pts = [];
    for (let y = 0; y <= h; y += 3) pts.push([x0 + dir * r.range(0, 5) , y]);
    return pts;
  };
  const L = edge(0, 1), R = edge(w, -1);
  g.beginPath();
  g.moveTo(L[0][0], 0);
  for (const p of L) g.lineTo(p[0], p[1]);
  for (const p of R.reverse()) g.lineTo(p[0], p[1]);
  g.closePath();
  const tc = tint || [232, 220, 186];
  g.fillStyle = `rgba(${tc[0]},${tc[1]},${tc[2]},0.62)`;
  g.fill();
  g.save();
  g.clip();
  // crepe texture: fine stripes across the width
  for (let x = 0; x < w; x += 2) {
    g.fillStyle = `rgba(255,255,255,${r.range(0, 0.06)})`;
    g.fillRect(x, 0, 1, h);
  }
  for (let i = 0; i < 90; i++) {
    g.fillStyle = `rgba(120,100,60,${r.range(0.01, 0.05)})`;
    g.fillRect(r.range(0, w), r.range(0, h), r.range(2, 12), r.range(1, 2));
  }
  // sheen along one edge, dirt along the other
  const gr = g.createLinearGradient(0, 0, 0, h);
  gr.addColorStop(0, 'rgba(255,255,245,0.18)');
  gr.addColorStop(0.2, 'rgba(255,255,245,0)');
  gr.addColorStop(0.85, 'rgba(90,70,40,0)');
  gr.addColorStop(1, 'rgba(90,70,40,0.12)');
  g.fillStyle = gr;
  g.fillRect(0, 0, w, h);
  g.restore();
  return c;
}

// A torn edge along a path of [x, y] (mm) on the page: the gap's shadow, the paper core, loose fibres.
export function drawTear(g, path, i0, i1, seed, side) {
  const r = new Rng(seed + i0 * 131);
  g.save();
  g.lineCap = 'round';
  for (let i = Math.max(1, i0); i < i1; i++) {
    const [x0, y0] = path[i - 1], [x1, y1] = path[i];
    const X0 = x0 * PX, Y0 = y0 * PX, X1 = x1 * PX, Y1 = y1 * PX;
    // shadow in the gap
    g.strokeStyle = 'rgba(52,40,26,0.5)';
    g.lineWidth = 1.3;
    g.beginPath(); g.moveTo(X0, Y0); g.lineTo(X1, Y1); g.stroke();
    // the torn sheet's edge: rough white core on the far side of the gap
    const s = side || 1;
    g.strokeStyle = 'rgba(255,253,246,0.85)';
    g.lineWidth = r.range(1.6, 3.2);
    g.beginPath(); g.moveTo(X0 + s * 1.6, Y0); g.lineTo(X1 + s * (1.4 + r.range(0, 1.2)), Y1); g.stroke();
    g.strokeStyle = 'rgba(120,100,70,0.16)';
    g.lineWidth = 1;
    g.beginPath(); g.moveTo(X0 + s * 3.4, Y0); g.lineTo(X1 + s * (3.2 + r.range(0, 1.4)), Y1); g.stroke();
    // fibres bridging the gap
    if (r.chance(0.5)) {
      g.strokeStyle = 'rgba(250,246,236,0.7)';
      g.lineWidth = 0.6;
      const fx = X0 + r.range(-1, 1), fy = Y0 + r.range(0, Y1 - Y0);
      g.beginPath(); g.moveTo(fx - s * 2.5, fy); g.lineTo(fx + s * r.range(1, 3), fy + r.sym(2)); g.stroke();
    }
  }
  g.restore();
}

export function drawStain(g, cx, cy, rad, seed, strength = 1) {
  const r = new Rng(seed);
  g.save();
  g.globalCompositeOperation = 'multiply';
  const n = 90;
  // faint body
  const gr = g.createRadialGradient(cx * PX, cy * PX, rad * PX * 0.2, cx * PX, cy * PX, rad * PX);
  gr.addColorStop(0, `rgba(212,172,120,${0.1 * strength})`);
  gr.addColorStop(0.9, `rgba(196,150,96,${0.16 * strength})`);
  gr.addColorStop(1, 'rgba(200,160,110,0)');
  g.fillStyle = gr;
  g.beginPath(); g.arc(cx * PX, cy * PX, rad * PX, 0, Math.PI * 2); g.fill();
  // the ring: coffee dries at the rim; break it in two places
  const gapA = r.range(0, Math.PI * 2), gapL = r.range(0.4, 1.1);
  for (let pass = 0; pass < 3; pass++) {
    g.strokeStyle = `rgba(140,90,45,${(0.34 - pass * 0.09) * strength})`;
    g.lineWidth = (0.35 + pass * 0.5) * PX;
    g.beginPath();
    let started = false;
    for (let i = 0; i <= n; i++) {
      const a = (i / n) * Math.PI * 2;
      const inGap = ((a - gapA + Math.PI * 4) % (Math.PI * 2)) < gapL;
      const rr = rad * (1 + Math.sin(a * 3 + seed) * 0.012 + Math.sin(a * 7) * 0.006) + pass * 0.15;
      const x = cx * PX + Math.cos(a) * rr * PX, y = cy * PX + Math.sin(a) * rr * PX;
      if (inGap) { started = false; continue; }
      if (!started) { g.moveTo(x, y); started = true; } else g.lineTo(x, y);
    }
    g.stroke();
  }
  g.restore();
}
