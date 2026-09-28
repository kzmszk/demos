// A page that draws itself: ops laid out on a "natural" clock, drawn incrementally up to any time τ.
import { PX, PAGE_W, PAGE_H, makeCanvas, makePaper, planStroke, drawDabs, drawDots, WashReveal, eraseDabs, smudgeDabs, tapeImage, drawStain, drawTear } from './media.js';
import { hashStr } from './rng.js';

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const easeStroke = (f) => f * 0.45 + 0.55 * (0.5 - 0.5 * Math.cos(Math.PI * f));

export class PageRuntime {
  constructor(def) {
    this.def = def;
    this.id = def.id;
    this.W = Math.round(PAGE_W * PX);
    this.H = Math.round(PAGE_H * PX);
    this.paper = makePaper(def.seed ?? hashStr(def.id), def.paper || {});
    this.canvas = makeCanvas(this.W, this.H);
    this.g = this.canvas.getContext('2d', { willReadFrequently: true });
    this.disp = null;
    this.reset();
    let t = def.lead ?? 0.4;
    for (const op of def.ops) {
      t += op.gap ?? 0.1;
      op.start = t;
      t += Math.max(0.001, op.dur ?? 0.1);
      op.end = t;
    }
    this.T = t + 0.3;
    this.strokes = def.ops.reduce((n, o) => n + (o.t === 'dots' ? o.pts.length / 2 : o.t === 'stroke' || o.t === 'wash' || o.t === 'erase' || o.t === 'smudge' ? 1 : 0), 0);
    this.version = 0;
  }
  reset() {
    this.g.globalCompositeOperation = 'source-over';
    this.g.globalAlpha = 1;
    this.g.drawImage(this.paper, 0, 0);
    if (this.def.under) this.def.under(this.g, this);
    this.cursor = 0;
    this.state = null; // progress of the op under the cursor
    this.overlay = null;
    this.tau = 0;
    this.version = (this.version || 0) + 1;
  }
  get done() { return this.cursor >= this.def.ops.length; }
  // Draw everything that happened up to natural time tau (monotonic; call reset() to go back).
  advanceTo(tau) {
    if (tau < this.tau) return false;
    this.tau = tau;
    const ops = this.def.ops;
    let changed = false;
    while (this.cursor < ops.length && ops[this.cursor].start <= tau) {
      const op = ops[this.cursor];
      const f = clamp01((tau - op.start) / (op.end - op.start));
      changed = this.drawOp(op, f) || changed;
      if (f >= 1) {
        this.finish(op);
        this.cursor++;
        this.state = null;
      } else break;
    }
    if (changed) this.version++;
    return changed;
  }
  finishAll() { return this.advanceTo(1e9); }
  drawOp(op, f) {
    const g = this.g;
    if (!this.state) this.state = { i: 0, op };
    const st = this.state;
    switch (op.t) {
      case 'stroke': {
        if (!st.plan) st.plan = planStroke(op, hashStr(this.id) ^ (op.start * 1000) | 0);
        const target = easeStroke(f) * st.plan.total;
        const d = st.plan.dabs;
        let j = st.i;
        const n = d.length / 5;
        while (j < n && d[j * 5 + 4] <= target + 1e-6) j++;
        if (f >= 1) j = n;
        if (j > st.i) { drawDabs(g, op, st.plan, st.i, j); st.i = j; return true; }
        return false;
      }
      case 'wash': {
        if (!st.wash) { st.wash = new WashReveal(op, hashStr(this.id + op.start)); this.overlay = st.wash; }
        st.tip = st.wash.advance(clamp01(f * 1.02));
        return true;
      }
      case 'erase':
      case 'smudge': {
        const pts = op.pts;
        const j = Math.min(pts.length, Math.floor(f * pts.length + (f >= 1 ? 1 : 0)));
        if (j > st.i) {
          if (op.t === 'erase') eraseDabs(g, this.paper, pts, st.i, j, op.r || 2.4, op.k || 0.22);
          else smudgeDabs(g, pts, st.i, j, op.r || 3);
          st.i = j;
          return true;
        }
        return false;
      }
      case 'tape': {
        if (!st.img) { st.img = tapeImage(op.len, op.wid, hashStr(this.id + 'tape' + op.start), op.tint); this.overlay = { composite: (gg) => this.tapeDraw(gg, op, st.img, st.f), commit: (gg) => this.tapeDraw(gg, op, st.img, 1) }; }
        st.f = f;
        return true;
      }
      case 'stain': {
        if (!st.drawn && f >= 1) { drawStain(g, op.x, op.y, op.r, op.seed || 1, op.k || 1); st.drawn = true; return true; }
        if (!st.drawn) { this.overlay = { composite: (gg) => { gg.save(); gg.globalAlpha = f; drawStain(gg, op.x, op.y, op.r, op.seed || 1, op.k || 1); gg.restore(); }, commit: () => {} }; return true; }
        return false;
      }
      case 'dots': {
        const n = op.pts.length / 2;
        const j = f >= 1 ? n : Math.floor(f * n);
        if (j > st.i) { drawDots(g, op, st.i, j, hashStr(this.id) ^ (op.start * 977)); st.i = j; return true; }
        return false;
      }
      case 'tear': {
        const n = op.path.length;
        const j = f >= 1 ? n : Math.floor(f * n);
        if (j > st.i) {
          drawTear(g, op.path, st.i, j, 77, op.side);
          if (this.onTear) this.onTear(op, st.i, j);
          st.i = j;
          return true;
        }
        return false;
      }
      case 'paint': { // arbitrary deterministic canvas painter, drawn once at the end (e.g. ghosts)
        if (f >= 1 && !st.drawn) { op.draw(g, this); st.drawn = true; return true; }
        return false;
      }
      default:
        return false;
    }
  }
  tapeDraw(g, op, img, f) {
    g.save();
    g.translate(op.x * PX, op.y * PX);
    g.rotate(op.rot || 0);
    const w = img.width * clamp01(f);
    if (w > 1) {
      // shadow line under the tape edge
      g.fillStyle = 'rgba(60,45,20,0.08)';
      g.fillRect(-img.width / 2, img.height / 2 - 1, w, 2.5);
      g.drawImage(img, 0, 0, w, img.height, -img.width / 2, -img.height / 2, w, img.height);
    }
    g.restore();
  }
  finish(op) {
    const st = this.state;
    if (op.t === 'wash' && st && st.wash) { st.wash.commit(this.g); this.overlay = null; if (op.onDone) op.onDone(st.wash); }
    if (op.t === 'tape' && st && st.img) { this.tapeDraw(this.g, op, st.img, 1); this.overlay = null; }
    if (op.t === 'stain') this.overlay = null;
  }
  // The canvas to show (the committed one, or a composite with the op in progress).
  get display() {
    if (!this.overlay) return this.canvas;
    if (!this.disp) { this.disp = makeCanvas(this.W, this.H); this.dg = this.disp.getContext('2d'); }
    this.dg.globalCompositeOperation = 'copy';
    this.dg.drawImage(this.canvas, 0, 0);
    this.dg.globalCompositeOperation = 'source-over';
    this.overlay.composite(this.dg);
    return this.disp;
  }
  // Where the drawing tool is at natural time tau: {x, y (mm), lift (mm), tool, op}
  toolAt(tau) {
    const ops = this.def.ops;
    if (!ops.length) return { x: PAGE_W * 0.7, y: PAGE_H * 0.8, lift: 40, tool: 'pencil', idle: true };
    // binary search the op whose [prev.end, end) contains tau
    let lo = 0, hi = ops.length - 1;
    while (lo < hi) { const m = (lo + hi) >> 1; if (ops[m].end < tau) lo = m + 1; else hi = m; }
    const op = ops[lo];
    if (tau >= op.start && tau <= op.end) {
      const f = clamp01((tau - op.start) / (op.end - op.start));
      const p = this.opPoint(op, f);
      return { x: p[0], y: p[1], lift: 0, tool: op.tool || 'pencil', op, pressure: p[2] ?? 1 };
    }
    // in the gap before op
    const prev = lo > 0 ? ops[lo - 1] : null;
    if (!prev) {
      const s = this.opPoint(op, 0);
      const u = clamp01((tau - 0) / Math.max(0.01, op.start));
      return { x: s[0] + 30 * (1 - u), y: s[1] + 40 * (1 - u), lift: 2 + 30 * (1 - u) * (1 - u), tool: op.tool || 'pencil', op };
    }
    if (tau > op.end) {
      const e = this.opPoint(op, 1);
      const u = clamp01((tau - op.end) / 1.2);
      return { x: e[0] + 25 * u, y: e[1] + 30 * u, lift: 1 + 34 * u * u, tool: op.tool || 'pencil', idle: u >= 1 };
    }
    const a = this.opPoint(prev, 1), b = this.opPoint(op, 0);
    const u = clamp01((tau - prev.end) / Math.max(1e-3, op.start - prev.end));
    const e = u * u * (3 - 2 * u);
    const dist = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const lift = Math.sin(Math.PI * e) * Math.min(7, 0.8 + dist * 0.25) + 0.3;
    const sameTool = (prev.tool || 'pencil') === (op.tool || 'pencil');
    return { x: a[0] + (b[0] - a[0]) * e, y: a[1] + (b[1] - a[1]) * e, lift: sameTool ? lift : lift + 30 * Math.sin(Math.PI * u), tool: u < 0.5 ? prev.tool || 'pencil' : op.tool || 'pencil', swap: !sameTool ? u : null, op };
  }
  opPoint(op, f) {
    if (op.t === 'stroke') {
      if (!op._cum) {
        const p = op.pts, n = p.length / 3, c = new Float32Array(n);
        for (let i = 1; i < n; i++) c[i] = c[i - 1] + Math.hypot(p[i * 3] - p[i * 3 - 3], p[i * 3 + 1] - p[i * 3 - 2]);
        op._cum = c;
      }
      const c = op._cum, p = op.pts, n = c.length;
      const s = easeStroke(f) * c[n - 1];
      let lo = 0, hi = n - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (c[m] < s) lo = m + 1; else hi = m; }
      const i = Math.max(1, lo);
      const t = clamp01((s - c[i - 1]) / Math.max(1e-6, c[i] - c[i - 1]));
      return [p[i * 3 - 3] + (p[i * 3] - p[i * 3 - 3]) * t, p[i * 3 - 2] + (p[i * 3 + 1] - p[i * 3 - 2]) * t, p[i * 3 + 2]];
    }
    if (op.t === 'wash') {
      const P = op.path;
      if (!op._cum) { const c = [0]; for (let i = 1; i < P.length; i++) c.push(c[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1])); op._cum = c; }
      const c = op._cum, s = clamp01(f) * c[c.length - 1];
      let i = 1;
      while (i < c.length - 1 && c[i] < s) i++;
      const t = clamp01((s - c[i - 1]) / Math.max(1e-6, c[i] - c[i - 1]));
      return [P[i - 1][0] + (P[i][0] - P[i - 1][0]) * t, P[i - 1][1] + (P[i][1] - P[i - 1][1]) * t, 1];
    }
    if (op.t === 'dots') {
      const n = op.pts.length / 2, i = Math.min(n - 1, Math.floor(clamp01(f) * n));
      return [op.pts[i * 2], op.pts[i * 2 + 1], 1];
    }
    if (op.t === 'tear') {
      const P = op.path, i = Math.min(P.length - 1, Math.floor(clamp01(f) * (P.length - 1)));
      return [P[i][0], P[i][1], 1];
    }
    if (op.t === 'erase' || op.t === 'smudge') {
      const P = op.pts, i = Math.min(P.length - 1, Math.floor(f * (P.length - 1)));
      return [P[i][0], P[i][1], 1];
    }
    if (op.t === 'tape') {
      const L = op.len * clamp01(f) - op.len / 2;
      return [op.x + Math.cos(op.rot || 0) * L, op.y + Math.sin(op.rot || 0) * L, 1];
    }
    return [op.x ?? PAGE_W / 2, op.y ?? PAGE_H / 2, 1];
  }
}
