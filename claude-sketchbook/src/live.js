// A person with a finger: tap to open, swipe or drag to turn, and draw on the last page.
import * as THREE from 'three';
import { App, SHOTS } from './app.js';
import { buildTimeline, BAR, smooth, clamp01 } from './timeline.js';
import { CT, CW, T, INSET, NL, LT, PW, PH } from './three/book.js';
import { LiveAudio } from './audio/live.js';
import { pageFoleyMap } from './audio/soundtrack.js';
import * as FX from './audio/sfx.js';
import { backOutside } from './covers.js';
import { makeUI } from './ui.js';
import { planStroke, drawDabs } from './media.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const KEY = (i) => ['p01', 'p02', 'p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09'][i];

export function startLive(canvas) {
  const app = new App(canvas, { mode: 'live', width: window.innerWidth, height: window.innerHeight });
  const live = new Live(app, canvas);
  window.SKETCH = { app, live };
  const m = /^#p(\d+)$/.exec(location.hash);
  if (m) live.jumpTo(Math.floor(+m[1] / 2), true);
}

class Live {
  constructor(app, canvas) {
    this.app = app;
    this.canvas = canvas;
    this.tl = buildTimeline(app.data.pages.slice(0, 9));
    this.reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.t = 0;
    this.last = performance.now();
    this.phase = 'closed';
    this.leaf = Array.from({ length: NL }, () => ({ p: 0, anim: null }));
    this.front = { p: 0, anim: null };
    this.back = { p: 0, anim: null };
    this.band = 0;
    this.drawQ = [];
    this.drawing = null;
    this.done = new Array(10).fill(false);
    this.done[9] = true;
    this.reader = 0;
    this.cam = null;
    this.ui = makeUI(this);
    this.bindInput();
    window.addEventListener('resize', () => this.resize());
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { if (this.audio) this.audio.ctx.suspend(); }
      else { this.lastTs = null; if (this.audio && !this.audio.muted) this.audio.ctx.resume(); }
    });
    this.resize();
    requestAnimationFrame((ts) => this.frame(ts));
  }
  resize() {
    this.app.resize(window.innerWidth, window.innerHeight);
    this.ui.resize();
  }
  get turned() { let k = 0; for (const l of this.leaf) if (l.p > 0.5) k++; return k; }
  get spread() { return this.front.p < 0.5 ? -1 : this.back.p > 0.5 ? 6 : this.turned; }

  // ---------- audio ----------
  ensureAudio() {
    if (!this.audio) {
      try { this.audio = new LiveAudio(); for (const k of ['intro', 'p01']) this.audio.prepare(k); } catch (e) { this.audio = null; }
    }
    if (this.audio) this.audio.resume();
    return this.audio;
  }
  sfx(seconds, fn) { if (this.audio) this.audio.foley(seconds, fn); }

  // ---------- actions ----------
  open() {
    if (this.phase !== 'closed') return;
    this.ensureAudio();
    this.phase = 'opening';
    this.openAt = this.t;
    if (this.audio) {
      this.audio.play('intro', { now: true, loop: false });
      this.sfx(1.2, (b) => FX.slide(b, 0.05, 0.7, 11));
      setTimeout(() => this.sfx(0.5, (b) => FX.snap(b, 0, 12)), 1570);
      setTimeout(() => this.sfx(3.2, (b) => FX.coverOpen(b, 0, 2.5, 13)), 2350);
      for (let i = 2; i < 6; i++) this.audio.prepare(KEY(i));
    }
    this.ui.hint(null);
  }
  arrive() {
    // pages on the spread that aren't drawn yet, left first
    const s = this.spread;
    const q = [];
    if (s >= 1 && s <= 5) q.push(2 * s - 1);
    if (s >= 0 && s <= 4) q.push(2 * s);
    this.drawQ = q.filter((i) => i < 9 && !this.done[i]);
    if (!this.drawing && this.drawQ.length) this.startDrawing(this.drawQ.shift());
    else if (!this.drawQ.length && this.audio) {
      if (s === 5) this.audio.play('end', { loop: false });
      else if (s >= 0 && s <= 4) this.audio.play(KEY(Math.min(8, 2 * s)));
    }
    if (s === 5) this.ui.hint('draw');
    else if (s === 0 && !this.everTurned) this.ui.hint('turn');
    else this.ui.hint(null);
    for (let i = 2 * Math.max(0, s); i < Math.min(9, 2 * s + 4); i++) if (this.audio) this.audio.prepare(KEY(i));
  }
  startDrawing(i) {
    const sec = this.tl.sec[i];
    const D = sec.d1 - sec.d0;
    const speed = this.reduced ? 3 : 1;
    this.drawing = { i, t0: this.t + 0.6, D: D / speed, warp: sec.warp, speed };
    if (this.audio) {
      this.audio.play(KEY(i));
      const page = this.app.data.pages[i];
      const warp = sec.warp;
      const at = this.audio.now + 0.6;
      this.drawing.foley = this.audio.foley(D / speed + 1.5, (b) => pageFoleyMap(b, (tau) => warp.inv(tau) / speed, page, sec.side, 'foley' + i), at);
    }
  }
  finishDrawing(stopSound) {
    const d = this.drawing;
    if (!d) return;
    this.app.data.pages[d.i].finishAll();
    this.done[d.i] = true;
    if (stopSound && this.audio) this.audio.stopFoley(d.foley);
    this.drawing = null;
    this.lastDrawEnd = this.t;
    this.lastDrawPage = d.i;
  }
  // turn forward (+1) or back (-1), animated
  turn(dir) {
    if (this.phase === 'closed') return this.open();
    if (this.phase !== 'open' || this.busy()) return;
    const k = this.turned;
    if (dir > 0) {
      if (this.back.p > 0.5) return;
      if (k >= NL) return this.closeBack(1);
      this.beginTurn(k, 1);
    } else {
      if (this.back.p > 0.5) return this.closeBack(0);
      if (k <= 0) return;
      this.beginTurn(k - 1, 0);
    }
  }
  busy() { return this.leaf.some((l) => l.anim) || this.back.anim || this.front.anim || this.drag; }
  beginTurn(l, to, from) {
    const leaf = this.leaf[l];
    if (to === 1 && this.drawing) this.finishDrawing(true);
    // pages about to be hidden should be complete
    if (to === 1) for (const i of [2 * l, 2 * l - 1]) if (i >= 0 && i < 9 && !this.done[i]) { this.app.data.pages[i].finishAll(); this.done[i] = true; }
    this.drawQ = [];
    const f = from ?? leaf.p;
    const dur = 1.35 * Math.abs(to - f) + 0.25;
    leaf.anim = { from: f, to, t0: this.t, dur };
    this.everTurned = this.everTurned || to === 1;
    if (this.audio) this.sfx(dur + 0.6, (b) => FX.pageTurn(b, 0, dur, 20 + l + Math.floor(this.t * 10)));
    this.ui.hint(null);
  }
  closeBack(to) {
    const f = this.back.p;
    this.back.anim = { from: f, to, t0: this.t, dur: 1.6 };
    if (to === 1) this.refreshLabel();
    if (this.audio) this.sfx(2.4, (b) => FX.coverOpen(b, 0, 1.6, 14));
    this.ui.hint(null);
  }
  refreshLabel() {
    const tex = this.app.coverTex.backOut;
    tex.image = backOutside(this.app.data.total + this.reader, this.reader);
    tex.needsUpdate = true;
  }

  // straight to a spread with everything before it drawn (for cover frames and deep links)
  jumpTo(s, drawCurrent = true) {
    this.phase = 'open';
    this.band = 1;
    this.front.p = 1; this.front.anim = null;
    this.back.p = s >= 6 ? 1 : 0; this.back.anim = null;
    const k = Math.min(NL, Math.max(0, s));
    this.leaf.forEach((l, i) => { l.p = i < k ? 1 : 0; l.anim = null; });
    if (this.drawing) this.finishDrawing(true);
    const upto = drawCurrent ? Math.min(9, 2 * k + 1) : Math.min(9, Math.max(0, 2 * k - 1));
    for (let i = 0; i < upto; i++) { this.app.data.pages[i].finishAll(); this.done[i] = true; }
    this.drawQ = [];
    if (s >= 6) this.refreshLabel();
    else this.arrive();
    this.cam = null;
  }

  // ---------- input ----------
  bindInput() {
    const c = this.canvas;
    c.addEventListener('pointerdown', (e) => this.down(e));
    c.addEventListener('pointermove', (e) => this.move(e));
    c.addEventListener('pointerup', (e) => this.up(e));
    c.addEventListener('pointercancel', (e) => this.up(e, true));
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    window.addEventListener('keydown', (e) => {
      if (['ArrowRight', 'PageDown', ' ', 'Enter'].includes(e.key)) { e.preventDefault(); this.ensureAudio(); this.turn(1); }
      else if (['ArrowLeft', 'PageUp', 'Backspace'].includes(e.key)) { e.preventDefault(); this.turn(-1); }
    });
    this.ray = new THREE.Raycaster();
  }
  ndc(e) { const r = this.canvas.getBoundingClientRect(); return new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); }
  // where the pointer lands on page 10 (mm), if it does
  hitBlank(e) {
    if (this.spread !== 5) return null;
    this.ray.setFromCamera(this.ndc(e), this.app.camera);
    const leaf = this.app.leaves[4];
    const hit = this.ray.intersectObject(leaf.back, false)[0];
    if (!hit || !hit.uv) return null;
    return { x: hit.uv.x * 148, y: (1 - hit.uv.y) * 210, point: hit.point };
  }
  // the screen x of the spine and a page's width in pixels (for drag distances)
  screenMetrics() {
    const cam = this.app.camera;
    const a = V(0, 0.3, 0).project(cam), b = V(PW, 0.3, 0).project(cam);
    const w = this.canvas.clientWidth;
    return { spine: ((a.x + 1) / 2) * w, page: Math.abs(b.x - a.x) / 2 * w };
  }
  down(e) {
    this.ensureAudio();
    this.canvas.setPointerCapture && this.canvas.setPointerCapture(e.pointerId);
    this.ptr = { x: e.clientX, y: e.clientY, t: this.t, id: e.pointerId, moved: 0 };
    if (this.phase !== 'open' || this.busy()) return;
    const hit = this.hitBlank(e);
    if (hit) {
      this.pen = { pts: [[hit.x, hit.y, this.pressure(e)]], last: [hit.x, hit.y], point: hit.point };
      this.pencilAt = hit;
      if (this.audio) this.audio.scratchStart();
      this.ui.hint(null);
      return;
    }
    const m = this.screenMetrics();
    const side = e.clientX > m.spine ? 'R' : 'L';
    const k = this.turned;
    if (side === 'R' && k < NL && this.back.p < 0.5) this.drag = { kind: 'leaf', l: k, from: 0, x0: e.clientX, m };
    else if (side === 'L' && k > 0 && this.back.p < 0.5) this.drag = { kind: 'leaf', l: k - 1, from: 1, x0: e.clientX, m };
    else if (side === 'R' && k === NL) this.drag = { kind: 'back', from: this.back.p, x0: e.clientX, m };
    else if (side === 'L' && this.back.p > 0.5) this.drag = { kind: 'back', from: 1, x0: e.clientX, m };
    if (this.drag) { this.drag.started = false; this.drag.y0 = e.clientY; }
  }
  pressure(e) { return e.pointerType === 'pen' && e.pressure > 0 ? 0.4 + e.pressure * 0.7 : 0.85; }
  move(e) {
    if (this.ptr && e.pointerId === this.ptr.id) this.ptr.moved = Math.max(this.ptr.moved, Math.hypot(e.clientX - this.ptr.x, e.clientY - this.ptr.y));
    if (this.pen) {
      const hit = this.hitBlank(e);
      if (!hit) return;
      const [lx, ly] = this.pen.last;
      const d = Math.hypot(hit.x - lx, hit.y - ly);
      if (d < 0.25) return;
      const p = this.pressure(e);
      const prev = this.pen.pts[this.pen.pts.length - 1];
      const op = { t: 'stroke', medium: 'pencil', w: 0.7, pts: Float32Array.from([prev[0], prev[1], prev[2], hit.x, hit.y, p]) };
      const pg = this.app.data.pages[9];
      const plan = planStroke(op, this.pen.pts.length * 7919 + this.reader);
      drawDabs(pg.g, op, plan, 0, plan.dabs.length / 5);
      pg.version++;
      this.pen.pts.push([hit.x, hit.y, p]);
      this.pen.last = [hit.x, hit.y];
      this.pencilAt = hit;
      const dt = Math.max(0.008, this.t - (this.pen.lt ?? this.t - 0.016));
      this.pen.lt = this.t;
      if (this.audio) this.audio.scratchLevel(Math.min(2.5, d / dt / 60));
      return;
    }
    const dg = this.drag;
    if (!dg) return;
    const dx = e.clientX - dg.x0;
    if (!dg.started && Math.abs(dx) < 8) return;
    dg.started = true;
    const span = Math.max(80, dg.m.page * 1.6);
    let p = dg.from === 0 || (dg.kind === 'back' && dg.from < 0.5) ? clamp01(-dx / span) : clamp01(1 - dx / span);
    dg.p = p;
    dg.corner = 0.15 + 0.5 * clamp01((e.clientY - dg.y0 + 120) / 240);
    if (dg.kind === 'leaf') { const leaf = this.leaf[dg.l]; leaf.p = p; leaf.corner = dg.corner; }
    else this.back.p = p;
    if (dg.kind === 'leaf' && dg.from === 0 && this.drawing) this.finishDrawing(true);
    const vx = e.movementX || 0;
    dg.v = (dg.v || 0) * 0.6 + vx * 0.4;
  }
  up(e, cancel) {
    if (this.pen) {
      if (this.pen.pts.length > 1) { this.reader++; }
      this.pen = null;
      if (this.audio) this.audio.scratchLevel(0);
      return;
    }
    const tap = this.ptr && this.ptr.moved < 10 && this.t - this.ptr.t < 0.45;
    const dg = this.drag;
    this.drag = null;
    if (this.phase === 'closed') { if (tap) this.open(); return; }
    if (dg && dg.started && !cancel) {
      const p = dg.p ?? dg.from;
      const fling = dg.v || 0;
      let to;
      if (dg.from === 0 || (dg.kind === 'back' && dg.from < 0.5)) to = p > 0.33 || fling < -6 ? 1 : 0;
      else to = p < 0.67 || fling > 6 ? 0 : 1;
      if (dg.kind === 'leaf') {
        if (to === 1 && dg.from === 0) { for (const i of [2 * dg.l, 2 * dg.l - 1]) if (i >= 0 && i < 9 && !this.done[i]) { this.app.data.pages[i].finishAll(); this.done[i] = true; } }
        const leaf = this.leaf[dg.l];
        leaf.anim = { from: p, to, t0: this.t, dur: 0.25 + 1.1 * Math.abs(to - p) };
        if (Math.abs(to - p) > 0.05 && this.audio) this.sfx(1.8, (b) => FX.pageTurn(b, 0, 0.25 + 1.1 * Math.abs(to - p), 40 + Math.floor(this.t * 7)));
        this.everTurned = this.everTurned || to === 1;
      } else {
        this.back.anim = { from: p, to, t0: this.t, dur: 0.3 + 1.2 * Math.abs(to - p) };
        if (to === 1) this.refreshLabel();
      }
      return;
    }
    if (tap) {
      const m = this.screenMetrics();
      this.turn(e.clientX > m.spine ? 1 : -1);
    }
  }

  // ---------- per frame ----------
  frame(ts) {
    if (this.lastTs == null) this.lastTs = ts;
    const dt = Math.max(0, Math.min(0.5, (ts - this.lastTs) / 1000));
    this.lastTs = ts;
    this.t += dt;
    this.update(dt);
    requestAnimationFrame((x) => this.frame(x));
  }
  update(dt) {
    const app = this.app, t = this.t;
    // opening sequence
    let pencilOut = this.phase === 'closed' ? 0 : 1;
    if (this.phase === 'opening') {
      const u = t - this.openAt;
      pencilOut = clamp01(u / 1.4);
      this.band = clamp01((u - 1.45) / 0.7);
      this.bandWob = u > 2.15 ? Math.exp(-(u - 2.15) * 6) * Math.sin((u - 2.15) * 26) * 0.35 : 0;
      const cu = clamp01((u - 2.35) / 2.5);
      this.front.p = 0.5 - 0.5 * Math.cos(Math.PI * cu);
      if (u > 4.9) { this.phase = 'open'; this.front.p = 1; this.arrive(); }
    }
    // animations
    const stepAnim = (o, onEnd) => {
      if (!o.anim) return;
      const a = o.anim, u = clamp01((t - a.t0) / a.dur);
      const e = a.to > a.from ? 1 - Math.pow(1 - smooth(u), 1.35) : smooth(u);
      o.p = a.from + (a.to - a.from) * e;
      if (u >= 1) { o.p = a.to; o.anim = null; o.landed = t; onEnd && onEnd(); }
    };
    this.leaf.forEach((l) => stepAnim(l, () => this.arrive()));
    stepAnim(this.back, () => { if (this.back.p < 0.5) this.arrive(); });
    // drawing
    const d = this.drawing;
    if (d) {
      const u = (t - d.t0) * d.speed;
      if (u >= 0) app.data.pages[d.i].advanceTo(d.warp.tau(Math.min(u, d.D * d.speed)));
      if (t - d.t0 >= d.D) {
        this.finishDrawing(false);
        if (this.drawQ.length) this.startDrawing(this.drawQ.shift());
        else if (this.spread === 5 && this.audio) this.audio.play('end', { loop: false });
      }
    }
    if (this.audio) this.audio.tick();
    // book
    app.band.set(this.band, this.bandWob || 0);
    app.front.set(Math.PI * this.front.p);
    app.back.set(Math.PI * this.back.p);
    this.leaf.forEach((l, i) => {
      const settle = l.landed && t - l.landed < 1.2 ? Math.exp(-(t - l.landed) * 4) * Math.sin((t - l.landed) * 18) * 0.05 : 0;
      app.leaves[i].set(l.p, 0.34, l.corner ?? 0.24, settle);
    });
    app.spine.update(app.front, app.back);
    this.poseTool(pencilOut);
    this.camera(dt);
    app.syncTextures();
    app.camera.updateMatrixWorld();
    app.updateLampView();
    app.renderer.render(app.scene, app.camera);
    this.ui.draw(t);
  }
  poseTool(pencilOut) {
    const app = this.app, tools = app.tools, t = this.t;
    const L = tools.pencil.userData.length;
    const bob = Math.sin(t * 1.3) * 0.25;
    const hover = { tip: V(19.5, 7.5 + bob, 9.5), axis: V(0.3, 0.85, 0.43).normalize() };
    if (this.phase === 'closed' || this.phase === 'opening') {
      const c0 = V(INSET + CW + 0.42, T - CT / 2 + 0.05, 0);
      const axis0 = V(0, 0, -1);
      const tip0 = c0.clone().addScaledVector(axis0, -L / 2 + 0.6);
      const slide = smooth(clamp01(pencilOut / 0.55));
      const tipS = tip0.clone().add(V(0, 0, 10.8 * slide));
      const lift = smooth(clamp01((pencilOut - 0.5) / 0.5));
      const tip = tipS.lerp(hover.tip, lift);
      tip.y += Math.sin(Math.PI * lift) * 4;
      tools.pose('pencil', tip, axis0.clone().lerp(hover.axis, lift).normalize());
      return;
    }
    const axisW = V(0.44, 0.7, 0.56).normalize();
    // the reader holds it
    if (this.spread === 5 && (this.pen || this.pencilAt)) {
      const hit = this.pencilAt;
      const tip = hit.point.clone().add(V(0, this.pen ? 0.02 : 0.6, 0));
      this.readerPose = this.readerPose ? this.readerPose.lerp(tip, 0.5) : tip;
      tools.pose('pencil', this.readerPose, axisW);
      return;
    }
    if (this.back.p > 0.5) {
      tools.pose('pencil', V(22, 0.36, 6), V(-0.3, 0, -0.95).normalize());
      return;
    }
    const d = this.drawing;
    if (d) {
      const pg = app.data.pages[d.i];
      const u = Math.max(0, (t - d.t0) * d.speed);
      const tl2 = pg.toolAt(d.warp.tau(Math.min(u, d.D * d.speed)));
      const p = app.pageWorld(d.i, tl2.x, tl2.y, V(0, 0, 0));
      let kind = tl2.tool, flip = 0, extra = 0;
      if (kind === 'eraser') { flip = 1; kind = 'pencil'; }
      if (kind === 'finger' || kind === 'hand' || kind === 'none') { kind = 'pencil'; extra = 5; }
      const tip = p.add(V(0, (tl2.lift || 0) / 10 + extra + 0.02, 0));
      const w = smooth(clamp01((t - (d.t0 - 1.0)) / 0.9));
      tools.pose(kind, hover.tip.clone().lerp(tip, w), hover.axis.clone().lerp(axisW, w).normalize(), flip * w, 0, tl2.op && tl2.op.rgbTip);
      return;
    }
    // resting between pages
    const since = this.lastDrawEnd != null ? t - this.lastDrawEnd : 99;
    const w = 1 - smooth(clamp01(since / 1.0));
    if (w > 0 && this.lastDrawPage != null) {
      const pg = app.data.pages[this.lastDrawPage];
      const e = pg.toolAt(pg.T);
      const p = app.pageWorld(this.lastDrawPage, e.x, e.y, V(0, 0, 0)).add(V(0, 1 + (1 - w) * 3, 0));
      tools.pose('pencil', hover.tip.clone().lerp(p, w), hover.axis.clone().lerp(axisW, w).normalize());
      return;
    }
    tools.pose('pencil', hover.tip, hover.axis);
  }
  // framing that fits the viewport's shape
  camera(dt) {
    const app = this.app;
    const aspect = app.W / app.H;
    const vf = (30 * Math.PI) / 180;
    const hf = 2 * Math.atan(Math.tan(vf / 2) * aspect);
    const fit = (w, h) => Math.max(h / (2 * Math.tan(vf / 2)), w / (2 * Math.tan(hf / 2))) * 1.06;
    let shot;
    const s = this.spread;
    if (this.phase === 'closed' || (this.phase === 'opening' && this.t - this.openAt < 1.0)) {
      const lampShot = aspect < 0.9 ? SHOTS.lampTall : SHOTS.lamp;
      const base = this.t < 2.6 && this.phase === 'closed' ? lampShot : SHOTS.closed;
      shot = { ...base, t: [...base.t], dist: base === SHOTS.closed ? fit(24, 30) : base.dist * (aspect < 0.9 ? Math.max(1, 0.62 / aspect) : Math.max(1, 1.2 / aspect)) };
    } else if (this.back.p > 0.5) {
      shot = { t: [-7.6, 0.6, 0.4], dist: fit(24, 30), elev: 62, azim: -3, roll: 0, fov: 30 };
    } else {
      const wide = aspect >= 1.25;
      let focus = 0; // -1 left page, +1 right page, 0 both
      if (this.drawing) focus = this.drawing.i % 2 ? -1 : 1;
      else if (s === 5) focus = -1;
      else if (s === 0) focus = 1;
      if (this.leaf.some((l) => l.anim) || this.drag) focus = 0;
      if (wide) shot = { t: [focus * 2.2, 0.3, 0.5], dist: fit(34, 24.5), elev: 66, azim: -1, roll: 0, fov: 30 };
      else if (focus === 0) shot = { t: [0, 0.3, 0.5], dist: fit(33, 24), elev: 66, azim: -1, roll: 0, fov: 30 };
      else shot = { t: [focus * 7.5, 0.3, 0.45], dist: fit(16.8, 23.5), elev: 73, azim: 0, roll: 0, fov: 30 };
    }
    // a critically damped follow
    if (!this.cam) this.cam = JSON.parse(JSON.stringify(shot));
    const k = 1 - Math.exp(-dt * (this.reduced ? 6 : 2.4));
    const c = this.cam;
    for (let i = 0; i < 3; i++) c.t[i] += (shot.t[i] - c.t[i]) * k;
    for (const key of ['dist', 'elev', 'azim', 'roll', 'fov']) c[key] += (shot[key] - c[key]) * k;
    this.app.setCamera(c, this.reduced ? 0 : this.t);
  }
}
