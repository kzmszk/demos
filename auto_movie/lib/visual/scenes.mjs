// Scene renderers: script visual spec → static HTML/SVG for the stage + a JSON blob the browser runtime animates.
// Everything is laid out here in canvas pixels; the runtime only tweens (draw-on, pop, wipe), it never measures text.
import path from 'node:path';
import { readText, exists, esc } from '../util.mjs';
import { COLORS, STAGE } from './theme.mjs';
import { forEmbedding, designMemo, smoothPath, pencilLine, pencilRect, WOBBLE_DEFS, fmt } from './svgtools.mjs';

const SW = STAGE.w, SH = STAGE.h;
const INK = COLORS.ink, MARK = COLORS.marker, RED = COLORS.red;

/** Main entry: returns { html, data } for the stage content of a scene. */
export function renderStage(scene, ctx) {
  const v = scene.visual || {};
  switch (v.type) {
    case 'illustration': return illustration(scene, ctx);
    case 'chart': return v.kind === 'bar' ? barChart(scene) : v.kind === 'review-curve' ? reviewCurve(scene) : lineChart(scene);
    case 'steps': return steps(scene);
    case 'recap': return recap(scene);
    default: throw new Error(`unknown visual type "${v.type}" in scene ${scene.id}`);
  }
}

// monotone cubic (Fritsch–Carlson) interpolation through [[x,y],…]
function pchip(pts) {
  const n = pts.length, h = [], d = [], m = new Array(n);
  for (let i = 0; i < n - 1; i++) { h[i] = pts[i + 1][0] - pts[i][0]; d[i] = (pts[i + 1][1] - pts[i][1]) / h[i]; }
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (2 * d[i - 1] * d[i]) / (d[i - 1] + d[i]);
  return (x) => {
    let i = 0; while (i < n - 2 && x > pts[i + 1][0]) i++;
    const t = (x - pts[i][0]) / h[i], t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * pts[i][1] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * pts[i + 1][1] + (t3 - t2) * h[i] * m[i + 1];
  };
}
// Ebbinghaus' savings scores (days, retained): the measured shape of the forgetting curve
const EBBINGHAUS = [[0, 1], [0.0139, 0.582], [0.042, 0.442], [0.375, 0.358], [1, 0.337], [2, 0.278], [6, 0.254], [31, 0.211], [40, 0.2]];

// ------------------------------------------------------------------------------------------------
// Illustration
// ------------------------------------------------------------------------------------------------
function illustration(scene, ctx) {
  const file = path.join(ctx.runDir, 'illustrations', `${scene.id}.svg`);
  if (!exists(file)) throw new Error(`missing illustration ${file} (run the illustrate stage)`);
  const raw = readText(file);
  const svg = forEmbedding(raw, { prefix: `${scene.id}-` });
  const elements = (scene.visual.elements || []).map((e) => ({ id: e.id, dom: `${scene.id}-el-${e.id}`, idle: e.idle || null }));
  const callouts = (scene.cues || []).filter((c) => c.op === 'callout');
  const co = callouts.map((c, i) => `<div class="callout" id="${scene.id}-co${i}" data-target="${scene.id}-el-${esc(c.target)}" data-side="${esc(c.side || 'right')}"><u>${esc(c.text)}</u></div>`).join('');
  const html = `<div class="ill" id="${scene.id}-ill">${svg}</div>${co}<svg class="co-arrows" id="${scene.id}-arrows" viewBox="0 0 ${SW} ${SH}"></svg>`;
  return { html, data: { elements, deco: `${scene.id}-el-deco`, hero: scene.visual.hero || null, memo: designMemo(raw), viewBox: [640, 360] } };
}

// ------------------------------------------------------------------------------------------------
// Chart helpers
// ------------------------------------------------------------------------------------------------
const PLOT = { x0: 150, x1: 1090, yTop: 70, yBot: 548 }; // axes box in stage coords
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const yOf = (v, max) => PLOT.yBot - (v / max) * (PLOT.yBot - PLOT.yTop);
const tickStyle = 'position:absolute;font-size:26px;font-weight:500;color:rgba(61,61,61,.8);line-height:36px;white-space:nowrap;';

function axesSVG(id, { yMax = 100, unit = '%', ticks = [0, 25, 50, 75, 100], seed = 5 }) {
  const grid = ticks.filter((t) => t > 0).map((t, i) => `<path d="${pencilLine(PLOT.x0, yOf(t, yMax), PLOT.x1, yOf(t, yMax), seed + i, 1)}" stroke="${INK}" stroke-opacity=".16" stroke-width="1.6" stroke-dasharray="7 9" fill="none"/>`).join('');
  const labels = ticks.map((t) => `<div class="tick" style="${tickStyle}left:${PLOT.x0 - 100}px;top:${yOf(t, yMax) - 18}px;width:84px;text-align:right">${t}${unit}</div>`).join('');
  const axes = `<path d="${pencilLine(PLOT.x0, PLOT.yBot, PLOT.x1 + 10, PLOT.yBot, seed + 20, 1.6)}" stroke="${INK}" stroke-width="3.4" fill="none" stroke-linecap="round"/><path d="${pencilLine(PLOT.x0, PLOT.yBot + 6, PLOT.x0, PLOT.yTop - 14, seed + 21, 1.6)}" stroke="${INK}" stroke-width="3.4" fill="none" stroke-linecap="round"/>`;
  return { svg: `<g id="${id}-grid">${grid}</g><g id="${id}-axes">${axes}</g>`, labels: `<div id="${id}-ticks">${labels}</div>` };
}


function chartShell(id, svgInner, htmlInner, extraDefs = '') {
  return `<svg id="${id}-svg" viewBox="0 0 ${SW} ${SH}" fill="none" stroke-linecap="round" stroke-linejoin="round"><defs>${WOBBLE_DEFS(`${id}-wob`, 3.4)}${extraDefs}</defs><g filter="url(#${id}-wob)">${svgInner}</g></svg>${htmlInner}`;
}

/**
 * Where the red note for a chart point goes. The usual place is up and to the right of the point; if that touches a number, a label or the curve,
 * a grid of other places around the point is searched for the one that touches nothing (nearest first). Returns the note's top-left corner and the
 * two path strings of its arrow (shaft and head).
 */
function placeCallout(p, text, avoid, curve) {
  const wide = /[\u2E80-\u9FFF\uFF00-\uFFEF\u3000-\u303F]/;                 // full-width letters take the whole em, digits and Latin about 0.62 of it
  const tw = Math.round([...String(text)].reduce((w, ch) => w + 38 * (wide.test(ch) ? 0.99 : 0.62), 0)) + 12, th = 56;
  const overlap = (a, b) => { const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y); return w > 0 && h > 0 ? w * h : 0; };
  // little squares along the curve, so a note does not lie across the line
  const line = [];
  for (let i = 0; i < curve.length - 1; i++) {
    const [x0, y0] = curve[i], [x1, y1] = curve[i + 1], n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 16));
    for (let k = 0; k <= n; k++) { const x = x0 + ((x1 - x0) * k) / n, y = y0 + ((y1 - y0) * k) / n; if (Math.hypot(x - p.px, y - p.py) > 34) line.push({ x: x - 7, y: y - 7, w: 14, h: 14 }); }
  }
  const score = (lx, ly, prefer) => {
    const rect = { x: lx - 8, y: ly - 4, w: tw + 16, h: th + 8 };
    const outside = lx < 8 || ly < 8 || lx + tw > SW + 40 || ly + th > SH - 8;        // the stage is narrower than the frame: a note may run a little past its right edge
    return (outside ? 1e7 : 0) + avoid.reduce((sum, r) => sum + overlap(rect, r), 0) + line.reduce((sum, r) => sum + (overlap(rect, r) ? 3000 : 0), 0)
      + overlap(rect, { x: p.px - 16, y: p.py - 16, w: 32, h: 32 }) * 4 + prefer;
  };
  const usual = { lx: Math.min(SW - 330, p.px + 70), ly: Math.max(20, p.py - 130) };
  let best = { ...usual, pen: score(usual.lx, usual.ly, 0), usual: true };
  if (best.pen > 0) {
    for (const dy of [-130, -96, -160, -64, -190, 60, 92, 124, -20, 16]) {
      for (const dx of [70, 0, -Math.round(tw / 2), 130, -tw - 30, 40, -tw - 90, 200]) {
        const lx = Math.round(Math.min(SW - tw - 12, Math.max(20, p.px + dx))), ly = Math.round(Math.min(SH - th - 12, Math.max(12, p.py + dy)));
        const pen = score(lx, ly, Math.hypot(lx + tw / 2 - p.px, ly + th / 2 - p.py) * 0.05);
        if (pen < best.pen) best = { lx, ly, pen };
      }
    }
  }
  const { lx, ly } = best;
  const rect = { x: lx - 8, y: ly - 4, w: tw + 16, h: th + 8 };
  if (best.usual) {   // the usual placement keeps its original arrow
    return { lx, ly, rect,
      arrow: `M${fmt(lx + 26)} ${fmt(ly + 56)} C${fmt(lx + 4)} ${fmt(ly + 100)} ${fmt(p.px + 60)} ${fmt(p.py - 28)} ${fmt(p.px + 16)} ${fmt(p.py - 14)}`,
      head: `M${fmt(p.px + 34)} ${fmt(p.py - 36)} L${fmt(p.px + 14)} ${fmt(p.py - 12)} L${fmt(p.px + 42)} ${fmt(p.py - 8)}` };
  }
  // anywhere else: a short curve from the note's nearest edge to just before the dot
  const clampX = Math.max(lx + 24, Math.min(lx + tw - 24, p.px));
  let sx, sy;
  if (ly + th < p.py - 24) { sx = clampX; sy = ly + th + 6; }             // the note is above the dot
  else if (ly > p.py + 24) { sx = clampX; sy = ly - 6; }                  // below
  else if (lx + tw < p.px) { sx = lx + tw + 6; sy = ly + th / 2; }        // to the left
  else { sx = lx - 6; sy = ly + th / 2; }                                 // to the right
  const dx = sx - p.px, dy = sy - p.py, len = Math.hypot(dx, dy) || 1;
  const ex = p.px + (dx / len) * 20, ey = p.py + (dy / len) * 20;         // stop short of the dot
  const bend = 24, cx = (sx + ex) / 2 + (-dy / len) * bend, cy = (sy + ey) / 2 + (dx / len) * bend;
  const tx = ex - cx, ty = ey - cy, tl = Math.hypot(tx, ty) || 1, ux = tx / tl, uy = ty / tl;
  const bx = ex - ux * 24, by = ey - uy * 24;
  return { lx, ly, rect, arrow: `M${fmt(sx)} ${fmt(sy)} Q${fmt(cx)} ${fmt(cy)} ${fmt(ex)} ${fmt(ey)}`,
    head: `M${fmt(bx - uy * 11)} ${fmt(by + ux * 11)} L${fmt(ex)} ${fmt(ey)} L${fmt(bx + uy * 11)} ${fmt(by - ux * 11)}` };
}

/** The stamp (see .stamp in theme.mjs) at a font size, centred on (cx, cy): its box grown by a margin and tilted like the stamp is, as four corners. */
function stampCorners(text, fs, cx = 0, cy = 0, margin = 8) {
  const w = [...String(text)].length * fs * 0.96 + 0.6 * fs + 18 + 2 * margin, h = fs * 1.5 + 0.14 * fs + 18 + 2 * margin;
  const a = (-5 * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(([x, y]) => ({ x: cx + x * c - y * s, y: cy + x * s + y * c }));
}

/** The straight box that just holds a stamp (see stampCorners), for keeping it on the stage and for later stamps to keep off. */
export function stampBox(text, fs) {
  const q = stampCorners(text, fs), xs = q.map((p) => p.x), ys = q.map((p) => p.y);
  return { w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) };
}

/** Whether a stamp centred on (cx, cy) touches a straight box: a returned test, so a stamp's own numbers are worked out once for many boxes. */
export function stampTouches(text, fs, cx, cy) {
  const q = stampCorners(text, fs, cx, cy), xs = q.map((p) => p.x), ys = q.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const axes = [[0, 1], [1, 2]].map(([i, j]) => {
    const nx = q[j].y - q[i].y, ny = q[i].x - q[j].x, pr = q.map((p) => p.x * nx + p.y * ny);
    return { nx, ny, lo: Math.min(...pr), hi: Math.max(...pr) };
  });
  return (r) => {
    if (x1 <= r.x || x0 >= r.x + r.w || y1 <= r.y || y0 >= r.y + r.h) return false;
    for (const { nx, ny, lo, hi } of axes) {           // separating axis test along the stamp's own two directions
      const a = r.x * nx + r.y * ny, b = (r.x + r.w) * nx + r.y * ny, c = r.x * nx + (r.y + r.h) * ny, d = (r.x + r.w) * nx + (r.y + r.h) * ny;
      if (hi <= Math.min(a, b, c, d) || lo >= Math.max(a, b, c, d)) return false;
    }
    return true;
  };
}

/**
 * The stamp is a big red hanko over the chart. Its usual place (upper right) is empty when the curve falls, but on a rising curve it lies right on the
 * high points and their numbers. So: the largest size, from the usual 104 px down to 58 px, that has a spot touching no number, note or curve
 * (the spot nearest the usual one); if there is none, the usual place at the smallest size. Returns the centre and the font size.
 */
function placeStamp(text, avoid, curve, usual) {
  const line = [];
  for (let i = 0; i < curve.length - 1; i++) {
    const [x0, y0] = curve[i], [x1, y1] = curve[i + 1], n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 16));
    for (let k = 0; k <= n; k++) line.push({ x: x0 + ((x1 - x0) * k) / n - 7, y: y0 + ((y1 - y0) * k) / n - 7, w: 14, h: 14 });
  }
  const obstacles = [...avoid, ...line];
  const free = (cx, cy, fs) => { const touches = stampTouches(text, fs, cx, cy); return !obstacles.some(touches); };
  if (free(usual.x, usual.y, 104)) return { x: usual.x, y: usual.y, fs: 104 };
  for (const fs of [104, 88, 76, 66, 58]) {
    const b = stampBox(text, fs);
    let best = null;
    for (let cy = 84 + b.h / 2; cy <= SH - 20 - b.h / 2; cy += 16) {
      for (let cx = 12 + b.w / 2; cx <= SW - 12 - b.w / 2; cx += 16) {
        const d = Math.hypot(cx - usual.x, cy - usual.y);
        if ((!best || d < best.d) && free(cx, cy, fs)) best = { cx, cy, d };
      }
    }
    if (best) return { x: Math.round(best.cx), y: Math.round(best.cy), fs };
  }
  return { x: usual.x, y: usual.y, fs: 58 };
}

// ------------------------------------------------------------------------------------------------
// Line chart (points on a categorical x axis, smooth curve, "forgotten" area in marker yellow)
// ------------------------------------------------------------------------------------------------
function lineChart(scene) {
  const v = scene.visual, id = scene.id;
  const yMax = v.yMax || 100, unit = v.unit || '%';
  const start = v.noStart ? [] : [{ x: v.startLabel || '覚えた直後', y: v.startValue ?? 100, start: true }];
  const pts = [...start, ...v.points.map((p) => ({ ...p }))];
  const n = pts.length;
  const xa = PLOT.x0 + 70, xb = PLOT.x1 - 40;
  pts.forEach((p, i) => { p.px = xa + ((xb - xa) * i) / (n - 1); p.py = yOf(p.y, yMax); });
  const curve = smoothPath(pts.map((p) => [p.px, p.py]), 0.9);
  const top = yOf(yMax, yMax);
  const area = `${curve} L${fmt(pts.at(-1).px)} ${fmt(top)} L${fmt(pts[0].px)} ${fmt(top)} Z`;
  const ax = axesSVG(id, { yMax, unit });
  const off = start.length;

  const dots = pts.map((p, i) => {
    const hero = i - off === (v.highlight ?? -1);
    const cls = p.start ? 'start' : '';
    return `<g id="${id}-pt${i - off}" class="pt ${cls}"><circle cx="${fmt(p.px)}" cy="${fmt(p.py)}" r="${hero ? 11 : 8}" fill="${hero ? RED : INK}" stroke="none"/></g>`;
  }).join('');
  const clipId = `${id}-clip`;
  const clip = `<clipPath id="${clipId}"><rect id="${id}-clip-r" x="${PLOT.x0 - 20}" y="0" width="0" height="${SH}"/></clipPath>`;
  const svgInner = `${ax.svg}<path id="${id}-area" d="${area}" fill="${MARK}" fill-opacity=".72" stroke="none" clip-path="url(#${clipId})" style="mix-blend-mode:multiply"/>` +
    `<path id="${id}-curve" d="${curve}" stroke="${INK}" stroke-width="5" fill="none" pathLength="1"/>${dots}`;

  const xlabels = pts.map((p, i) => `<div class="xl" id="${id}-xl${i - off}" style="${tickStyle}left:${p.px - 90}px;top:${PLOT.yBot + 16}px;width:180px;text-align:center;font-size:28px;color:rgba(61,61,61,.9)">${esc(p.x)}</div>`).join('');
  const vals = pts.map((p, i) => {
    if (p.start) return '';
    return `<div class="val" id="${id}-val${i - off}" style="position:absolute;font-size:40px;font-weight:900;left:${p.px - 14}px;width:150px;text-align:left;top:${p.py - 64}px;opacity:0">${p.y}${unit}</div>`;
  }).join('');
  // callouts (red pencil note + arrow): up and to the right of the point, unless that collides with a value label (a point near the top of the
  // plot leaves no room above it), in which case the first free place among a few others is used
  const labelRects = pts.filter((p) => !p.start).map((p) => ({ x: p.px - 14, y: p.py - 64, w: 26 * (String(p.y).length + unit.length) + 8, h: 52 }));
  const fixedRects = [...pts.map((p) => ({ x: p.px - 90, y: PLOT.yBot + 16, w: 180, h: 40 })), { x: PLOT.x1 - 320, y: PLOT.yBot + 66, w: 340, h: 34 }, { x: PLOT.x0 - 6, y: 8, w: 420, h: 40 }];
  const cos = (scene.cues || []).filter((c) => c.op === 'chart.callout').map((c, k) => {
    const p = pts[(c.index ?? 0) + off];
    const place = placeCallout(p, c.text, [...labelRects, ...fixedRects], pts.map((q) => [q.px, q.py]));
    const { lx, ly } = place;
    return { rect: place.rect, html: `<div class="callout" id="${id}-co${k}" style="left:${lx}px;top:${ly}px;font-size:38px"><u>${esc(c.text)}</u></div>`,
      arrow: `<path id="${id}-coa${k}" d="${place.arrow}" stroke="${RED}" stroke-width="3.6" fill="none" pathLength="1"/><path id="${id}-coh${k}" d="${place.head}" stroke="${RED}" stroke-width="3.6" fill="none" pathLength="1"/>` };
  });
  const curveLine = pts.map((q) => [q.px, q.py]);
  const placed = cos.map((c) => c.rect);                       // notes already placed are obstacles for the stamps
  const stamp = (scene.cues || []).filter((c) => c.op === 'stamp').map((c, k) => {
    const where = placeStamp(c.text, [...labelRects, ...fixedRects, ...placed, { x: PLOT.x0 - 110, y: PLOT.yTop - 20, w: 110, h: PLOT.yBot - PLOT.yTop + 40 }, { x: PLOT.x0, y: SH - 44, w: 420, h: 44 }], curveLine, { x: Math.round(SW * 0.72), y: Math.round(SH * 0.34) });
    const b = stampBox(c.text, where.fs);
    placed.push({ x: where.x - b.w / 2, y: where.y - b.h / 2, w: b.w, h: b.h });
    return `<div class="stamp" id="${id}-stamp${k}" style="left:${where.x}px;top:${where.y}px;opacity:0;font-size:${where.fs}px">${esc(c.text)}</div>`;
  }).join('');
  const labels = `<div class="axlab" style="position:absolute;left:${PLOT.x0 - 6}px;top:8px;font-size:28px;font-weight:700;color:rgba(61,61,61,.8);white-space:nowrap" id="${id}-ylab">${esc(v.yLabel || '')}</div>` +
    `<div class="axlab" style="position:absolute;left:${PLOT.x1 - 320}px;top:${PLOT.yBot + 66}px;width:340px;text-align:right;font-size:24px;font-weight:500;color:rgba(61,61,61,.8);white-space:nowrap" id="${id}-xlab">${esc(v.xLabel || '')} →</div>` +
    (v.note ? `<div style="position:absolute;left:${PLOT.x0}px;top:${SH - 38}px;font-size:22px;font-weight:500;color:rgba(61,61,61,.8)" id="${id}-note">${esc(v.note)}</div>` : '');
  const tickHTML = ax.labels;
  const html = chartShell(id, svgInner + cos.map((c) => `<g id="${id}-coarrow${cos.indexOf(c)}" opacity="0">${c.arrow}</g>`).join(''), tickHTML + xlabels + vals + labels + cos.map((c) => c.html).join('') + stamp, clip);
  return {
    html,
    data: { kind: 'line', n: v.points.length, off, xs: pts.map((p) => fmt(p.px)), ys: pts.map((p) => fmt(p.py)), clipRect: `${id}-clip-r`, clipX: PLOT.x0 - 20, plot: PLOT, area: `${id}-area`, curve: `${id}-curve`, callouts: cos.length, stamps: (scene.cues || []).filter((c) => c.op === 'stamp').length, highlight: v.highlight ?? null },
  };
}

// ------------------------------------------------------------------------------------------------
// Review curve: an illustrative model of memory with spaced reviews (labelled as an image, not data)
// ------------------------------------------------------------------------------------------------
function reviewCurve(scene) {
  const v = scene.visual, id = scene.id;
  const days = v.days || 40, reviews = v.reviews || [1, 7, 30];
  const xa = PLOT.x0 + 34, xb = PLOT.x1 - 10;
  const xOf = (t) => xa + Math.sqrt(t / days) * (xb - xa);
  const yV = (r) => yOf(r * 100, 100);
  const lambdas = [1.05, 0.075, 0.016, 0.004];
  const peaks = [1, 0.97, 0.97, 0.98];
  const decay = (k, t, r0) => peaks[k] * Math.exp(-lambdas[Math.min(k, lambdas.length - 1)] * (t - r0));
  // segments
  const bounds = [0, ...reviews, days];
  const segs = [];
  for (let k = 0; k < bounds.length - 1; k++) {
    const a = bounds[k], b = bounds[k + 1];
    const pts = [];
    const steps = k === 0 ? 46 : 60;
    for (let s = 0; s <= steps; s++) {
      // sample in sqrt space for an even look on the compressed axis
      const u0 = Math.sqrt(a), u1 = Math.sqrt(b), u = u0 + ((u1 - u0) * s) / steps, t = u * u;
      pts.push([xOf(t), yV(decay(k, t, a))]);
    }
    segs.push({ k, a, b, d: 'M' + pts.map((p) => `${fmt(p[0])} ${fmt(p[1])}`).join(' L'), end: pts.at(-1), start: pts[0] });
  }
  // baseline: no review (power-law like the real curve), dotted
  const base = [];
  const ebb = pchip(EBBINGHAUS.map(([t, r]) => [Math.sqrt(t), r]));
  for (let s = 0; s <= 120; s++) { const u = s / 120, t = u * u * days; base.push([xOf(t), yV(clamp01(ebb(Math.sqrt(Math.min(t, 40)))))]); }
  const baseD = 'M' + base.map((p) => `${fmt(p[0])} ${fmt(p[1])}`).join(' L');
  const ax = axesSVG(id, { yMax: 100, unit: '%', ticks: [0, 50, 100] });
  const segPaths = segs.map((s) => `<path id="${id}-seg${s.k}" d="${s.d}" stroke="${INK}" stroke-width="5" fill="none" pathLength="1"/>`).join('');
  const areas = segs.map((s) => `<path id="${id}-area${s.k}" d="${s.d} L${fmt(s.end[0])} ${fmt(PLOT.yBot)} L${fmt(s.start[0])} ${fmt(PLOT.yBot)} Z" fill="${MARK}" fill-opacity=".62" stroke="none" style="mix-blend-mode:multiply"/>`).join('');
  const jumps = reviews.map((r, i) => {
    const x = xOf(r), y0 = segs[i].end[1], y1 = yV(peaks[i + 1]);
    return `<path id="${id}-jump${i}" d="${pencilLine(x, y0, x, y1, 40 + i, 1)}" stroke="${RED}" stroke-width="4.2" fill="none" pathLength="1"/><path id="${id}-flag${i}" d="M${fmt(x)} ${fmt(y1)} l0 -34 M${fmt(x)} ${fmt(y1 - 34)} l30 10 l-30 10" stroke="${RED}" stroke-width="4" fill="none" pathLength="1" opacity="0"/>`;
  }).join('');
  const svgInner = `${ax.svg}<path id="${id}-base" d="${baseD}" stroke="${INK}" stroke-opacity=".4" stroke-width="4" stroke-dasharray="3 12" fill="none" pathLength="1"/>${areas}${segPaths}${jumps}`;
  const rlabels = reviews.map((r, i) => `<div class="rv" id="${id}-rv${i}" style="position:absolute;left:${xOf(r) - 90}px;top:${PLOT.yBot + 14}px;width:180px;text-align:center;font-size:30px;font-weight:900;color:${RED};opacity:0">${esc(v.reviewLabels?.[i] || `${r}日後`)}</div>`).join('');
  const tickHTML = ax.labels;
  const stamp = (scene.cues || []).filter((c) => c.op === 'stamp').map((c, k) => `<div class="stamp" id="${id}-stamp${k}" style="left:${Math.round(SW * 0.6)}px;top:${Math.round(SH * 0.6)}px;opacity:0;font-size:84px">${esc(c.text)}</div>`).join('');
  const legend = `<div style="position:absolute;left:${xOf(days * 0.7)}px;top:${yV(0.21) - 48}px;font-size:28px;font-weight:700;color:rgba(61,61,61,.8);white-space:nowrap;opacity:0" id="${id}-leg0">何もしないと…</div>` +
    `<div style="position:absolute;left:${PLOT.x0 - 6}px;top:8px;font-size:28px;font-weight:700;color:rgba(61,61,61,.8);white-space:nowrap" id="${id}-ylab">${esc(v.yLabel || '')}</div>` +
    `<div style="position:absolute;left:${PLOT.x1 - 330}px;top:${PLOT.yBot - 50}px;width:340px;text-align:right;font-size:24px;font-weight:500;color:rgba(61,61,61,.8)" id="${id}-xlab">${esc(v.xLabel || '')} →</div>` +
    (v.note ? `<div style="position:absolute;left:${PLOT.x0}px;top:${SH - 38}px;font-size:24px;font-weight:700;color:${RED}" id="${id}-note">${esc(v.note)}</div>` : '');
  const html = chartShell(id, svgInner, tickHTML + rlabels + legend + stamp);
  return { html, data: { kind: 'review', reviews, segs: segs.length, stamps: (scene.cues || []).filter((c) => c.op === 'stamp').length } };
}

// ------------------------------------------------------------------------------------------------
// Bar chart
// ------------------------------------------------------------------------------------------------
function barChart(scene) {
  const v = scene.visual, id = scene.id, yMax = v.yMax || 100, unit = v.unit || '%';
  const bars = v.bars, n = bars.length;
  const ax = axesSVG(id, { yMax, unit, ticks: [0, 25, 50, 75, 100], seed: 9 });
  const bw = Math.min(250, ((PLOT.x1 - PLOT.x0) / n) * 0.55);
  const slot = (PLOT.x1 - PLOT.x0) / n;
  const g = bars.map((b, i) => {
    const cx = PLOT.x0 + slot * (i + 0.5), x = cx - bw / 2, y = yOf(b.value, yMax), h = PLOT.yBot - y;
    const hatch = Array.from({ length: Math.ceil((bw + h) / 22) }, (_, k) => `M${fmt(x + k * 22)} ${fmt(PLOT.yBot)} l${fmt(h)} ${fmt(-h)}`).join(' ');
    const clip = `<clipPath id="${id}-bc${i}"><path d="M${fmt(x)} ${fmt(y)} H${fmt(x + bw)} V${fmt(PLOT.yBot)} H${fmt(x)} Z"/></clipPath>`;
    const fillEl = b.hero
      ? `<path d="M${fmt(x + 3)} ${fmt(y + 4)} H${fmt(x + bw - 2)} V${fmt(PLOT.yBot)} H${fmt(x + 4)} Z" fill="${MARK}" stroke="none" style="mix-blend-mode:multiply"/>`
      : `<g clip-path="url(#${id}-bc${i})"><path d="${hatch}" stroke="${INK}" stroke-opacity=".38" stroke-width="2" fill="none"/></g>`;
    return { defs: clip, svg: `<clipPath id="${id}-rv${i}"><rect id="${id}-rvr${i}" x="${fmt(x - 8)}" y="${fmt(PLOT.yBot)}" width="${fmt(bw + 16)}" height="0"/></clipPath><g id="${id}-bar${i}" clip-path="url(#${id}-rv${i})">${fillEl}<path d="${pencilRect(x, y, bw, h + 4, 50 + i, 2)}" stroke="${INK}" stroke-width="5" fill="none" pathLength="1"/></g>`, x, y, cx, h };
  });
  const svgInner = ax.svg + g.map((b) => b.svg).join('');
  const labels = bars.map((b, i) => `<div class="bl" id="${id}-bl${i}" style="position:absolute;left:${g[i].cx - 170}px;top:${PLOT.yBot + 18}px;width:340px;text-align:center;font-size:32px;font-weight:900">${esc(b.label)}</div>` +
    `<div class="bv" id="${id}-bv${i}" style="position:absolute;left:${g[i].cx - 120}px;top:${g[i].y - 84}px;width:240px;text-align:center;font-size:68px;font-weight:900;letter-spacing:-.03em;opacity:0;${b.hero ? `color:${RED}` : ''}">${b.value}${unit}</div>`).join('');
  const tickHTML = ax.labels;
  const extra = `<div style="position:absolute;left:${PLOT.x0 - 6}px;top:8px;font-size:28px;font-weight:700;color:rgba(61,61,61,.8);white-space:nowrap" id="${id}-ylab">${esc(v.yLabel || '')}</div>` +
    (v.note ? `<div style="position:absolute;left:${PLOT.x0}px;top:${SH - 38}px;font-size:22px;font-weight:500;color:rgba(61,61,61,.8)" id="${id}-note">${esc(v.note)}</div>` : '');
  return { html: chartShell(id, svgInner, tickHTML + labels + extra, g.map((b) => b.defs).join('')), data: { kind: 'bar', n, heights: g.map((b) => fmt(b.h + 6)), ys: g.map((b) => fmt(b.y)), baseline: PLOT.yBot, rects: g.map((_, i) => `${id}-rvr${i}`), xs: g.map((b) => fmt(b.x)) } };
}

// ------------------------------------------------------------------------------------------------
// Steps (2–4 cards with an icon, a big label and one line of explanation)
// ------------------------------------------------------------------------------------------------
const ICONS = {
  calendar: '<path d="M14 26 Q13 24 16 24 L84 23 Q87 24 87 27 L86 82 Q86 86 82 86 L18 87 Q14 87 14 83 Z" /><path d="M14 42 L87 41" /><path d="M32 14 L32 30 M68 14 L68 30"/><path d="M30 58 l8 0 M46 58 l8 0 M62 58 l8 0 M30 72 l8 0 M46 72 l8 0"/>',
  book: '<path d="M50 30 C38 22 22 23 10 28 L11 78 C23 73 38 73 50 80 C62 73 77 73 89 78 L90 28 C78 23 62 22 50 30 Z"/><path d="M50 30 L50 80"/><path d="M20 40 C28 38 36 39 43 42 M20 52 C28 50 36 51 43 54 M57 42 C64 39 72 38 80 40 M57 54 C64 51 72 50 80 52"/>',
  star: '<path d="M50 12 L61 38 L89 41 L67 59 L74 87 L50 72 L26 87 L33 59 L11 41 L39 38 Z"/>',
  check: '<path d="M14 54 L38 78 L88 22"/>',
  bulb: '<path d="M50 12 C29 12 22 30 30 45 C36 56 38 60 38 68 L62 68 C62 60 64 56 70 45 C78 30 71 12 50 12 Z"/><path d="M40 78 L60 78 M43 88 L57 88"/><path d="M50 2 L50 6 M14 22 L18 25 M86 22 L82 25" />',
  clock: '<path d="M50 10 C72 9 90 27 90 50 C90 73 72 91 50 90 C27 91 10 72 10 50 C10 28 28 10 50 10 Z"/><path d="M50 28 L50 52 L66 62"/>',
  phone: '<path d="M30 10 L70 10 Q76 10 76 16 L76 84 Q76 90 70 90 L30 90 Q24 90 24 84 L24 16 Q24 10 30 10 Z"/><path d="M42 80 L58 80"/>',
};
function steps(scene) {
  const v = scene.visual, id = scene.id, items = v.items, n = items.length;
  const gap = 56, cw = Math.min(360, Math.floor((SW - gap * (n - 1) - 40) / n)), ch = 440;
  const x0 = Math.round((SW - (cw * n + gap * (n - 1))) / 2), y0 = 70;
  const cards = items.map((it, i) => {
    const x = x0 + i * (cw + gap);
    const icon = ICONS[it.icon] || ICONS.star;
    return `<div class="card-step" id="${id}-c${i}" style="position:absolute;left:${x}px;top:${y0}px;width:${cw}px;height:${ch}px;opacity:0">
      <svg viewBox="0 0 ${cw} ${ch}" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" fill="none" stroke-linecap="round" stroke-linejoin="round"><defs>${WOBBLE_DEFS(`${id}-w${i}`, 3, '0.02 0.026', 3 + i)}</defs>
        <g filter="url(#${id}-w${i})"><path id="${id}-cf${i}" d="${pencilRect(6, 6, cw - 12, ch - 12, 70 + i, 3)}" stroke="${INK}" stroke-width="4" pathLength="1"/>
        <path d="M${cw / 2 - 74} 236 h148" stroke="none"/>
        <g transform="translate(${cw / 2 - 52} 44) scale(1.04)" stroke="${INK}" stroke-width="3.2"><ellipse cx="50" cy="52" rx="42" ry="40" fill="${MARK}" stroke="none" style="mix-blend-mode:multiply"/>${icon}</g></g></svg>
      <div style="position:absolute;left:0;right:0;top:172px;text-align:center;font-size:${[88, 88, 88, 80, 66, 52, 44][Math.min(6, it.label.length)]}px;font-weight:900;letter-spacing:-.04em;line-height:1.1"><span class="mk-l" style="position:relative;display:inline-block;padding:0 .14em;isolation:isolate"><i style="position:absolute;left:0;right:0;bottom:.06em;height:.38em;background:${MARK};z-index:-1;mix-blend-mode:multiply;transform-origin:0 50%;transform:rotate(-.6deg)"></i>${esc(it.label)}</span></div>
      <div style="position:absolute;left:28px;right:28px;top:272px;text-align:center;font-size:32px;font-weight:500;line-height:1.5;text-wrap:balance">${esc(it.sub || '')}</div>
    </div>`;
  }).join('');
  const arrows = items.slice(1).map((_, i) => {
    const xa = x0 + (i + 1) * cw + i * gap + 10, xb = xa + gap - 20, y = y0 + ch / 2;
    return `<path id="${id}-ar${i}" d="M${xa} ${y} Q${(xa + xb) / 2} ${y - 10} ${xb} ${y + 2} M${xb - 16} ${y - 14} L${xb + 2} ${y + 2} L${xb - 16} ${y + 16}" stroke="${RED}" stroke-width="4.5" fill="none" pathLength="1"/>`;
  }).join('');
  const html = `<svg viewBox="0 0 ${SW} ${SH}" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" fill="none" stroke-linecap="round">${arrows}</svg>${cards}`;
  return { html, data: { kind: 'steps', n } };
}

// ------------------------------------------------------------------------------------------------
// Recap (checklist)
// ------------------------------------------------------------------------------------------------
function recap(scene) {
  const v = scene.visual, id = scene.id, items = v.items;
  const rowH = 150, y0 = Math.round((SH - items.length * rowH) / 2) - 10;
  const rows = items.map((it, i) => {
    const y = y0 + i * rowH;
    return `<div class="rc" id="${id}-r${i}" style="position:absolute;left:0;top:${y}px;width:${SW}px;height:${rowH}px;opacity:0">
      <svg viewBox="0 0 ${SW} ${rowH}" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" fill="none" stroke-linecap="round" stroke-linejoin="round"><defs>${WOBBLE_DEFS(`${id}-rw${i}`, 3, '0.02 0.026', 8 + i)}</defs><g filter="url(#${id}-rw${i})">
        <path d="${pencilRect(74, 30, 78, 78, 90 + i, 2.5)}" stroke="${INK}" stroke-width="4.5"/>
        <path id="${id}-ck${i}" d="M84 72 L108 98 L162 32" stroke="${RED}" stroke-width="10" pathLength="1"/>
        <path id="${id}-ul${i}" d="${pencilLine(200, rowH - 26, SW - 100, rowH - 22, 100 + i, 2)}" stroke="${INK}" stroke-opacity=".3" stroke-width="2.4" pathLength="1"/></g></svg>
      <div style="position:absolute;left:210px;top:16px;font-size:66px;font-weight:900;letter-spacing:-.03em;line-height:1.2;white-space:nowrap"><span style="position:relative;display:inline-block;padding:0 .12em;isolation:isolate"><i class="rk" style="position:absolute;left:0;right:0;bottom:.06em;height:.4em;background:${MARK};z-index:-1;mix-blend-mode:multiply;transform-origin:0 50%;transform:scaleX(0) rotate(-.5deg)"></i>${esc(it.text)}</span></div></div>`;
  }).join('');
  return { html: rows, data: { kind: 'recap', n: items.length } };
}
