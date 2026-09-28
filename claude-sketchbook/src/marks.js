// Hand-drawn primitives. Each returns stroke ops (see layout.js for the op shape), in page mm.
import { Rng } from './rng.js';

const TAU = Math.PI * 2;

function opFrom(pts, o, len) {
  const medium = o.medium || 'pencil';
  const speed = o.speed || (medium === 'ink' ? 30 : 34);
  return {
    t: 'stroke', medium, color: o.color, w: o.w || (medium === 'ink' ? 0.3 : 0.42), a: o.a,
    pts: Float32Array.from(pts), len, dur: o.dur || 0.06 + len / speed, gap: o.gap != null ? o.gap : 0.14,
    tool: o.tool || (medium === 'ink' || medium === 'sepia' ? 'pen' : 'pencil'),
  };
}

function lenOf(p) {
  let L = 0;
  for (let i = 3; i < p.length; i += 3) L += Math.hypot(p[i] - p[i - 3], p[i + 1] - p[i - 2]);
  return L;
}

// pressure along t for a drawn line
function press(t, o) {
  const a = o.p0 ?? 0.55, taper = o.taper ?? 0.25;
  let p = a + (1 - a) * Math.min(1, t / 0.12);
  if (t > 1 - taper) p *= 0.35 + 0.65 * ((1 - t) / taper);
  return p * (o.p || 1);
}

// Sample a dense path through control points (Catmull–Rom), with a hand's wobble.
export function path(ctrl, o = {}, rng) {
  const r = rng || new Rng(o.seed || 1);
  const wob = o.wobble ?? 0.25;
  const pts = [];
  // dense sampling
  const dense = [];
  for (let k = 0; k < ctrl.length - 1; k++) {
    const p0 = ctrl[Math.max(0, k - 1)], p1 = ctrl[k], p2 = ctrl[k + 1], p3 = ctrl[Math.min(ctrl.length - 1, k + 2)];
    const L = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
    const n = Math.max(2, Math.ceil(L / 0.35));
    for (let i = k ? 1 : 0; i <= n; i++) {
      const t = i / n, t2 = t * t, t3 = t2 * t;
      const x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3);
      const y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3);
      dense.push([x, y]);
    }
  }
  // wobble: low-frequency perpendicular drift
  const ph1 = r.range(0, TAU), ph2 = r.range(0, TAU);
  const f1 = r.range(0.08, 0.16), f2 = r.range(0.25, 0.45);
  let s = 0;
  for (let i = 0; i < dense.length; i++) {
    if (i) s += Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]);
    const a = dense[Math.min(dense.length - 1, i + 1)], b = dense[Math.max(0, i - 1)];
    const L = Math.hypot(a[0] - b[0], a[1] - b[1]) || 1;
    const nx = -(a[1] - b[1]) / L, ny = (a[0] - b[0]) / L;
    const w = (Math.sin(s * f1 + ph1) * 0.7 + Math.sin(s * f2 + ph2) * 0.3) * wob;
    dense[i] = [dense[i][0] + nx * w, dense[i][1] + ny * w];
  }
  const total = dense.reduce((acc, p, i) => (i ? acc + Math.hypot(p[0] - dense[i - 1][0], p[1] - dense[i - 1][1]) : 0), 0);
  let acc = 0;
  for (let i = 0; i < dense.length; i++) {
    if (i) acc += Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]);
    pts.push(dense[i][0], dense[i][1], press(total ? acc / total : 0, o));
  }
  return opFrom(pts, o, total);
}

// a straight-ish line with a slight bow and overshoot
export function line(x1, y1, x2, y2, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x1 * 13 + y2 * 7));
  const L = Math.hypot(x2 - x1, y2 - y1) || 1;
  const nx = -(y2 - y1) / L, ny = (x2 - x1) / L;
  const bow = (o.bow ?? r.sym(0.012)) * L;
  const over = o.over ?? r.range(-0.01, 0.03);
  const ax = x1 - (x2 - x1) * over * 0.5, ay = y1 - (y2 - y1) * over * 0.5;
  const bx = x2 + (x2 - x1) * over, by = y2 + (y2 - y1) * over;
  const m = [(ax + bx) / 2 + nx * bow, (ay + by) / 2 + ny * bow];
  return path([[ax, ay], m, [bx, by]], { wobble: 0.12, ...o }, r);
}

export function polyline(points, o = {}, rng) {
  // a polyline drawn as separate strokes per segment when o.lift, else one stroke with corners
  const r = rng || new Rng(o.seed || 7);
  if (o.lift) return points.slice(1).map((p, i) => line(points[i][0], points[i][1], p[0], p[1], { ...o, gap: i ? 0.05 : o.gap }, r));
  // corners: sample each segment straight
  const pts = [];
  let total = 0;
  for (let i = 0; i < points.length - 1; i++) total += Math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1]);
  let acc = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const [x1, y1] = points[i], [x2, y2] = points[i + 1];
    const L = Math.hypot(x2 - x1, y2 - y1);
    const n = Math.max(2, Math.ceil(L / 0.4));
    for (let k = i ? 1 : 0; k <= n; k++) {
      const t = k / n;
      const w = Math.sin(t * Math.PI) * r.sym(0.1);
      pts.push(x1 + (x2 - x1) * t - (y2 - y1) / L * w, y1 + (y2 - y1) * t + (x2 - x1) / L * w, press((acc + L * t) / total, o));
    }
    acc += L;
  }
  return [opFrom(pts, o, total)];
}

// hand-drawn ellipse: starts somewhere, goes a little more than once round, ends open
export function ellipse(cx, cy, rx, ry, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(cx * 31 + cy * 17));
  const a0 = o.start ?? r.range(0, TAU);
  const turns = o.turns ?? r.range(1.02, 1.12);
  const rot = o.rot || 0;
  const n = Math.max(24, Math.round(Math.max(rx, ry) * 3 * turns));
  const pts = [];
  const e1 = r.sym(0.04), e2 = r.range(0, TAU);
  const dir = o.ccw ? -1 : 1;
  let total = 0, px, py;
  const raw = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = a0 + dir * t * turns * TAU;
    const k = 1 + e1 * Math.sin(a * 2 + e2) + (t > 0.85 ? (t - 0.85) * (o.spiral ?? 0.12) : 0);
    const x = Math.cos(a) * rx * k, y = Math.sin(a) * ry * k;
    const X = cx + x * Math.cos(rot) - y * Math.sin(rot), Y = cy + x * Math.sin(rot) + y * Math.cos(rot);
    if (i) total += Math.hypot(X - px, Y - py);
    px = X; py = Y;
    raw.push([X, Y]);
  }
  let acc = 0;
  for (let i = 0; i < raw.length; i++) {
    if (i) acc += Math.hypot(raw[i][0] - raw[i - 1][0], raw[i][1] - raw[i - 1][1]);
    pts.push(raw[i][0], raw[i][1], press(acc / total, o));
  }
  return opFrom(pts, o, total);
}

export function circle(cx, cy, rad, o = {}, rng) {
  return ellipse(cx, cy, rad, rad, o, rng);
}

export function dot(x, y, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x * 97 + y * 53));
  const s = o.size ?? 0.35;
  const a = r.range(0, TAU);
  const pts = [x, y, 0.8, x + Math.cos(a) * s, y + Math.sin(a) * s, 1];
  return { ...opFrom(pts, { ...o, dur: o.dur ?? 0.035, gap: o.gap ?? 0.03 }, s), dot: true };
}

export function arrow(x1, y1, x2, y2, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x1 * 3 + y1 * 5 + x2));
  const ops = [];
  const bend = o.bend ?? 0.12;
  const L = Math.hypot(x2 - x1, y2 - y1);
  const nx = -(y2 - y1) / L, ny = (x2 - x1) / L;
  const m = [(x1 + x2) / 2 + nx * L * bend, (y1 + y2) / 2 + ny * L * bend];
  ops.push(path([[x1, y1], m, [x2, y2]], { wobble: 0.1, ...o }, r));
  // head from the tangent at the end
  const tx = x2 - m[0], ty = y2 - m[1], tl = Math.hypot(tx, ty) || 1;
  const ux = tx / tl, uy = ty / tl;
  const h = o.head ?? Math.min(3.2, L * 0.25);
  const a = 0.45;
  const lx = x2 - h * (ux * Math.cos(a) - uy * Math.sin(a)), ly = y2 - h * (uy * Math.cos(a) + ux * Math.sin(a));
  const rx = x2 - h * (ux * Math.cos(-a) - uy * Math.sin(-a)), ry = y2 - h * (uy * Math.cos(-a) + ux * Math.sin(-a));
  ops.push(...polyline([[lx, ly], [x2, y2], [rx, ry]], { ...o, gap: 0.06 }, r));
  return ops;
}

// parallel hatching clipped to a polygon (mm); angle in radians
export function hatch(poly, angle, spacing, o = {}, rng) {
  const r = rng || new Rng(o.seed || 3);
  const ops = [];
  const ca = Math.cos(angle), sa = Math.sin(angle);
  // rotate polygon so hatching is horizontal
  const rp = poly.map(([x, y]) => [x * ca + y * sa, -x * sa + y * ca]);
  let minY = 1e9, maxY = -1e9;
  for (const [, y] of rp) { minY = Math.min(minY, y); maxY = Math.max(maxY, y); }
  let flip = false;
  for (let y = minY + spacing * r.range(0.3, 0.7); y < maxY; y += spacing * r.range(0.85, 1.15)) {
    const xs = [];
    for (let i = 0; i < rp.length; i++) {
      const [x1, y1] = rp[i], [x2, y2] = rp[(i + 1) % rp.length];
      if ((y1 <= y && y2 > y) || (y2 <= y && y1 > y)) xs.push(x1 + ((y - y1) / (y2 - y1)) * (x2 - x1));
    }
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) {
      let a = xs[k] + r.range(0, spacing * 0.4), b = xs[k + 1] - r.range(0, spacing * 0.4);
      if (b - a < 0.3) continue;
      if (flip && o.zigzag) [a, b] = [b, a];
      const p1 = [a * ca - y * sa, a * sa + y * ca], p2 = [b * ca - (y + r.sym(0.2)) * sa, b * sa + (y + r.sym(0.2)) * ca];
      ops.push(line(p1[0], p1[1], p2[0], p2[1], { speed: 90, gap: 0.03, p0: 0.7, taper: 0.4, ...o }, r));
      flip = !flip;
    }
  }
  return ops;
}

export function rect(x, y, w, h, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x * 7 + y * 11));
  return [
    line(x, y, x + w, y, o, r),
    line(x + w, y, x + w, y + h, { ...o, gap: 0.05 }, r),
    line(x + w, y + h, x, y + h, { ...o, gap: 0.05 }, r),
    line(x, y + h, x, y, { ...o, gap: 0.05 }, r),
  ];
}

export function checkbox(x, y, s, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x * 3 + y * 17));
  return polyline([[x, y + r.sym(0.2)], [x + s, y], [x + s + r.sym(0.2), y + s], [x, y + s], [x + r.sym(0.2), y - 0.3]], { speed: 40, ...o }, r);
}

// scribbled-out patch (a real mistake, not a strike-through)
export function scribble(x, y, w, h, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x * 5 + y * 9));
  const pts = [];
  const n = Math.max(6, Math.round(w / 1.1));
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    pts.push([x + t * w + r.sym(0.4), y + (i % 2 ? h : 0) + r.sym(h * 0.15)]);
  }
  return path(pts, { speed: 120, p0: 0.9, taper: 0.1, wobble: 0.05, ...o }, r);
}

export function underline(x, y, w, o = {}, rng) {
  const r = rng || new Rng(o.seed || Math.round(x * 5 + y));
  return line(x, y, x + w, y + r.sym(0.4) - w * 0.012, { speed: 70, taper: 0.35, ...o }, r);
}

// stipple: an array of dots
export function stipple(points, o = {}, rng) {
  const r = rng || new Rng(o.seed || 5);
  return points.map(([x, y], i) => dot(x, y, { ...o, gap: o.gap ?? 0.02 }, r));
}
