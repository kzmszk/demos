/* auto_movie browser runtime: builds ONE paused GSAP timeline from window.AM (the compiled episode).
 * HyperFrames seeks it frame by frame, so every state is a pure function of time:
 * only tweens / tl.set (no callbacks, no clocks, no unseeded randomness, no infinite repeats).
 */
(function () {
  'use strict';
  var AM = window.AM;
  var tl = gsap.timeline({ paused: true });
  var byId = function (id) { return document.getElementById(id); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var clamp = function (x, a, b) { return Math.min(b, Math.max(a, x)); };
  var NS = 'http://www.w3.org/2000/svg';
  var EASE_OUT = 'power3.out';

  // ---------------------------------------------------------------------------------------------
  // helpers
  // ---------------------------------------------------------------------------------------------
  function fadeInOut(el, start, end, inD, outD) {
    tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: inD, ease: 'power1.out' }, start);
    if (outD) tl.to(el, { opacity: 0, duration: outD, ease: 'power1.in' }, end - outD);
  }

  /** Prepare stroke nodes of an SVG group for a pen-like draw-on; returns [{el, len, stroke, fill}] in document order. */
  function prepDraw(g) {
    var nodes = [];
    $$('path,line,polyline,polygon,circle,ellipse,rect', g).forEach(function (n) {
      if (n.closest('clipPath') || n.closest('defs')) return;
      var cs = getComputedStyle(n);
      var hasStroke = cs.stroke && cs.stroke !== 'none' && parseFloat(cs.strokeWidth) > 0;
      var hasFill = cs.fill && cs.fill !== 'none';
      var len = 0;
      if (hasStroke) { try { len = n.getTotalLength(); } catch (e) { len = 0; } }
      nodes.push({ el: n, len: len, stroke: hasStroke && len > 0, fill: hasFill, wash: n.classList.contains('wash') });
    });
    nodes.forEach(function (o) {
      var n = o.el;
      gsap.set(n, { opacity: 0 });
      if (o.stroke) {
        n.setAttribute('pathLength', '1');
        gsap.set(n, { strokeDasharray: '1 2', strokeDashoffset: 1 });
      }
    });
    return nodes;
  }

  /** Timeline entries drawing prepared nodes over `D` seconds starting at `T` (strokes in sequence, fills fading). */
  function drawNodes(nodes, T, D) {
    var total = nodes.reduce(function (s, o) { return s + (o.stroke ? o.len : 8); }, 0) || 1;
    var cum = 0;
    nodes.forEach(function (o) {
      var w = (o.stroke ? o.len : 8);
      var st = T + (cum / total) * D * 0.86;
      var du = Math.max(0.1, (w / total) * D * 0.92 + 0.05);
      cum += w;
      if (o.stroke) {
        tl.set(o.el, { opacity: 1 }, st);
        tl.fromTo(o.el, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: du, ease: 'none', immediateRender: true }, st);
      }
      if (o.fill && !o.stroke) {
        tl.fromTo(o.el, { opacity: 0 }, { opacity: 1, duration: Math.max(0.3, du), ease: 'power1.out', immediateRender: true }, o.wash ? T + D * 0.15 : st);
      } else if (o.fill && o.stroke) {
        // filled + stroked shapes: the stroke draws, the fill follows
        tl.set(o.el, { opacity: 1 }, st);
      }
    });
  }

  function totalLen(nodes) { return nodes.reduce(function (s, o) { return s + (o.stroke ? o.len : 0); }, 0); }
  function drawDur(nodes) { return clamp(0.8 + totalLen(nodes) / 1500, 0.9, 2.6); }

  /** Finite yoyo repeat count that fits into `span` seconds. */
  function reps(span, half) { return Math.max(0, Math.floor(span / half) - 1); }

  // ---------------------------------------------------------------------------------------------
  // global chrome: progress bar, rule, headline transitions
  // ---------------------------------------------------------------------------------------------
  tl.fromTo(byId('prog-i'), { scaleX: 0 }, { scaleX: 1, duration: Math.max(1, AM.progress.to - AM.progress.from), ease: 'none' }, AM.progress.from);
  tl.fromTo(byId('rule'), { scaleX: 0 }, { scaleX: 1, duration: 0.9, ease: 'power2.inOut' }, AM.intro.end - 0.5);
  tl.fromTo(byId('hud'), { opacity: 0 }, { opacity: 1, duration: 0.5 }, AM.intro.end - 0.4);

  // ---------------------------------------------------------------------------------------------
  // scenes
  // ---------------------------------------------------------------------------------------------
  var ANIM = {};

  ANIM.illustration = function (sc) {
    var S = sc.stage, ill = byId(sc.id + '-ill'), svg = ill.querySelector('svg');
    var dur = sc.end - sc.start;
    // element groups
    var els = S.elements.map(function (e) { return { id: e.id, idle: e.idle, g: byId(e.dom) }; }).filter(function (e) { return e.g; });
    var cueOf = {};
    sc.cues.forEach(function (c) { if (c.target && !cueOf[c.target] && ['draw', 'pop', 'drop', 'fade', 'slide'].indexOf(c.op) >= 0) cueOf[c.target] = c; });
    var autoN = els.filter(function (e) { return !cueOf[e.id]; }).length, autoI = 0;
    var lastT = sc.start;
    els.forEach(function (e) {
      var c = cueOf[e.id];
      var T = c ? c.t : sc.start + 0.55 + autoI++ * (0.5 * dur / Math.max(1, autoN));
      var op = c ? c.op : 'draw';
      var g = e.g;
      var done = T;
      if (op === 'draw') {
        var nodes = prepDraw(g), D = drawDur(nodes);
        drawNodes(nodes, T, D);
        done = T + D;
      } else {
        gsap.set(g, { opacity: 0, transformBox: 'fill-box', transformOrigin: '50% 50%' });
        var D2 = 0.55;
        if (op === 'pop') tl.fromTo(g, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: D2, ease: 'back.out(2)', immediateRender: true }, T);
        else if (op === 'drop') tl.fromTo(g, { opacity: 0, y: -90 }, { opacity: 1, y: 0, duration: 0.7, ease: 'bounce.out', immediateRender: true }, T);
        else if (op === 'slide') tl.fromTo(g, { opacity: 0, x: -120 }, { opacity: 1, x: 0, duration: 0.7, ease: EASE_OUT, immediateRender: true }, T);
        else tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.6, immediateRender: true }, T);
        done = T + D2;
      }
      lastT = Math.max(lastT, done);
      // idle motion (finite yoyo)
      if (e.idle) {
        gsap.set(g, { transformBox: 'fill-box', transformOrigin: e.idle === 'sway' ? '50% 100%' : '50% 50%' });
        var span = sc.end - done - 0.4;
        if (span > 1) {
          if (e.idle === 'sway') tl.fromTo(g, { rotation: -1.6 }, { rotation: 1.6, duration: 1.7, ease: 'sine.inOut', yoyo: true, repeat: reps(span, 1.7), immediateRender: false }, done);
          else if (e.idle === 'float') tl.fromTo(g, { y: 0 }, { y: -9, duration: 1.5, ease: 'sine.inOut', yoyo: true, repeat: reps(span, 1.5), immediateRender: false }, done);
          else if (e.idle === 'pulse') tl.fromTo(g, { scale: 1 }, { scale: 1.06, duration: 0.9, ease: 'sine.inOut', yoyo: true, repeat: reps(span, 0.9), immediateRender: false }, done);
        }
      }
    });
    // emphasis cues
    sc.cues.filter(function (c) { return c.op === 'emph' && c.target; }).forEach(function (c) {
      var g = byId(sc.id + '-el-' + c.target);
      if (!g) return;
      gsap.set(g, { transformBox: 'fill-box', transformOrigin: '50% 50%' });
      tl.to(g, { scale: 1.09, duration: 0.2, ease: 'power2.out', yoyo: true, repeat: 1 }, c.t);
    });
    // doodles last
    var deco = byId(S.deco);
    if (deco) { var dn = prepDraw(deco); drawNodes(dn, Math.max(lastT - 0.4, sc.start + 1), 1.4); }
    // slow camera push
    gsap.set(svg, { transformOrigin: '50% 50%' });
    tl.fromTo(svg, { scale: 1.0, x: 0 }, { scale: 1.045, x: -6, duration: dur, ease: 'none', immediateRender: true }, sc.start);
    // callouts
    sc.cues.filter(function (c) { return c.op === 'callout'; }).forEach(function (c, i) { placeCallout(sc, c, i); });
  };

  /** Callout: text near the target's bounding box + a hand-drawn arrow, revealed at cue time.
   *  The label goes to whichever side of the target is emptiest (least overlap with the other elements, inside the stage). */
  function placeCallout(sc, c, i) {
    var box = byId(sc.id + '-co' + i), tgt = byId(box.getAttribute('data-target')), side = box.getAttribute('data-side') || 'right';
    var svg = byId(sc.id + '-ill').querySelector('svg');
    if (!tgt) return;
    var vb = svg.viewBox.baseVal, S = AM.stage;
    var k = Math.min(S.w / vb.width, S.h / vb.height), offX = (S.w - vb.width * k) / 2, offY = (S.h - vb.height * k) / 2;
    var toStage = function (g) { var b = g.getBBox(); return { x: offX + b.x * k, y: offY + b.y * k, w: b.width * k, h: b.height * k }; };
    var T = toStage(tgt);
    var others = sc.stage.elements.map(function (e) { return byId(e.dom); }).filter(function (g) { return g && g !== tgt; }).map(toStage);
    var tw = box.offsetWidth || 260, th = box.offsetHeight || 40, cx = T.x + T.w / 2, cy = T.y + T.h / 2, gap = 56;
    var overlap = function (a, b) { var w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y); return w > 0 && h > 0 ? w * h : 0; };
    var make = function (sd) {
      var lx, ly, ax, ay, bx, by;
      if (sd === 'left') { lx = T.x - tw - gap; ly = cy - th / 2 - 24; ax = lx + tw + 6; ay = ly + th / 2; bx = T.x - 6; by = cy; }
      else if (sd === 'top') { lx = cx - tw / 2; ly = T.y - th - gap; ax = cx; ay = ly + th + 6; bx = cx; by = T.y - 6; }
      else if (sd === 'bottom') { lx = cx - tw / 2; ly = T.y + T.h + gap - 8; ax = cx; ay = ly - 6; bx = cx; by = T.y + T.h + 6; }
      else { lx = T.x + T.w + gap; ly = cy - th / 2 - 24; ax = lx - 6; ay = ly + th / 2; bx = T.x + T.w + 6; by = cy; }
      var rect = { x: lx, y: ly, w: tw, h: th };
      var pen = 0;
      if (lx < 8 || ly < 6 || lx + tw > S.w - 8 || ly + th > S.h - 6) pen += 1e6;              // outside the stage
      others.forEach(function (o) { pen += overlap({ x: lx - 8, y: ly - 8, w: tw + 16, h: th + 16 }, o) * 2; });
      pen += overlap(rect, T) * 3;
      return { side: sd, lx: clamp(lx, 8, S.w - tw - 8), ly: clamp(ly, 6, S.h - th - 6), ax: ax, ay: ay, bx: bx, by: by, pen: pen };
    };
    var opp = { left: 'right', right: 'left', top: 'bottom', bottom: 'top' };
    var order = [side, opp[side], 'top', 'bottom', 'left', 'right'].filter(function (v, idx, a) { return a.indexOf(v) === idx; });
    var best = null;
    order.forEach(function (sd, idx) { var m = make(sd); m.pen += idx * 40; if (!best || m.pen < best.pen) best = m; });
    var lx = best.lx, ly = best.ly, bx = best.bx, by = best.by;
    box.style.left = lx + 'px'; box.style.top = ly + 'px';
    var arrows = byId(sc.id + '-arrows');
    var horizontal = best.side === 'left' || best.side === 'right';
    var startX = horizontal ? (best.side === 'right' ? lx - 4 : lx + tw + 4) : lx + tw / 2, startY = horizontal ? ly + th / 2 : (best.side === 'bottom' ? ly - 4 : ly + th + 4);
    var mx = (startX + bx) / 2 + (horizontal ? 0 : 30), my = (startY + by) / 2 - 24;
    var path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M' + startX + ' ' + startY + ' Q' + mx + ' ' + my + ' ' + bx + ' ' + by);
    path.setAttribute('stroke', '#d64545'); path.setAttribute('stroke-width', '4'); path.setAttribute('fill', 'none'); path.setAttribute('stroke-linecap', 'round'); path.setAttribute('pathLength', '1');
    arrows.appendChild(path);
    var dx = bx - mx, dy = by - my, L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
    var head = document.createElementNS(NS, 'path');
    head.setAttribute('d', 'M' + (bx - dx * 20 - dy * 11) + ' ' + (by - dy * 20 + dx * 11) + ' L' + bx + ' ' + by + ' L' + (bx - dx * 20 + dy * 11) + ' ' + (by - dy * 20 - dx * 11));
    head.setAttribute('stroke', '#d64545'); head.setAttribute('stroke-width', '4'); head.setAttribute('fill', 'none'); head.setAttribute('stroke-linecap', 'round'); head.setAttribute('stroke-linejoin', 'round'); head.setAttribute('pathLength', '1');
    arrows.appendChild(head);
    var ul = box.querySelector('u');
    gsap.set([path, head], { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 });
    gsap.set(box, { opacity: 0 });
    tl.fromTo(box, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3, ease: EASE_OUT, immediateRender: true }, c.t);
    tl.set(path, { opacity: 1 }, c.t + 0.15);
    tl.fromTo(path, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.45, ease: 'power1.inOut', immediateRender: true }, c.t + 0.15);
    tl.set(head, { opacity: 1 }, c.t + 0.55);
    tl.fromTo(head, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.18, ease: 'none', immediateRender: true }, c.t + 0.55);
    if (ul) tl.fromTo(box, { '--ul': 0 }, { '--ul': 1, duration: 0.4, ease: 'power2.out', immediateRender: true }, c.t + 0.2);
    tl.to([box, path, head], { opacity: 0, duration: 0.3 }, Math.min(sc.end - 0.45, c.t + 5.5));
  }

  // ---- charts ----------------------------------------------------------------------------------
  function drawPath(el, T, D, ease) {
    el.setAttribute('pathLength', '1');
    gsap.set(el, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 });
    tl.set(el, { opacity: 1 }, T);
    tl.fromTo(el, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: D, ease: ease || 'power1.inOut', immediateRender: true }, T);
  }
  function popIn(el, T, D) {
    gsap.set(el, { opacity: 0, transformBox: 'fill-box', transformOrigin: '50% 50%' });
    tl.fromTo(el, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: D || 0.4, ease: 'back.out(2.4)', immediateRender: true }, T);
  }
  function textIn(el, T, D) {
    gsap.set(el, { opacity: 0 });
    tl.fromTo(el, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: D || 0.35, ease: EASE_OUT, immediateRender: true }, T);
  }
  function stampIn(el, T, sc) {
    // GSAP owns the transform from here on, so the centring (CSS translate(-50%,-50%)) is handed over too; otherwise the y tween below
    // resets it and the stamp hangs from its top edge, half its height below the point it was placed at
    gsap.set(el, { xPercent: -50, yPercent: -50, x: 0, y: 0, opacity: 0 });
    tl.fromTo(el, { opacity: 0, scale: 2.2, rotation: -14 }, { opacity: 1, scale: 1, rotation: -5, duration: 0.32, ease: 'power4.in', immediateRender: true }, T);
    tl.fromTo(el, { y: 0 }, { y: 6, duration: 0.06, yoyo: true, repeat: 1 }, T + 0.32);
    tl.to(el, { opacity: 0, duration: 0.4 }, Math.min(sc.end - 0.5, T + 4.5));
  }
  function drawAxes(sc, id, T) {
    var g = byId(id + '-axes');
    $$('path', g).forEach(function (p, i) { drawPath(p, T + i * 0.25, 0.7); });
    var grid = byId(id + '-grid');
    gsap.set(grid, { opacity: 0 });
    tl.to(grid, { opacity: 1, duration: 0.6 }, T + 0.4);
    var ticks = byId(id + '-ticks');
    gsap.set(ticks, { opacity: 0 });
    tl.to(ticks, { opacity: 1, duration: 0.5 }, T + 0.3);
    ['ylab', 'xlab', 'note'].forEach(function (k, i) { var e = byId(id + '-' + k); if (e) textIn(e, T + 0.4 + i * 0.15, 0.4); });
  }

  ANIM.line = function (sc) {
    var S = sc.stage, id = sc.id;
    var curve = byId(S.curve), area = byId(S.area), clip = byId(S.clipRect);
    var off = S.off, xs = S.xs, ys = S.ys;
    var clipX = S.clipX;
    // hide everything data-driven until revealed
    curve.setAttribute('pathLength', '1');
    gsap.set(curve, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 });
    // length at each point: sample the path once at build (geometry only)
    var L = curve.getTotalLength(), fr = [0];
    var samples = 400, pts = [];
    for (var i = 0; i <= samples; i++) pts.push(curve.getPointAtLength((L * i) / samples));
    for (var k = 1; k < xs.length; k++) {
      var best = 0, bd = 1e9;
      for (var j = 0; j <= samples; j++) { var d = Math.abs(pts[j].x - xs[k]) + Math.abs(pts[j].y - ys[k]) * 0.5; if (d < bd) { bd = d; best = j; } }
      fr.push(best / samples);
    }
    for (var q = 0; q < S.n + off; q++) { var pt = byId(id + '-pt' + (q - off)); if (pt) gsap.set(pt, { opacity: 0, transformBox: 'fill-box', transformOrigin: '50% 50%' }); }
    for (var q2 = 0; q2 < S.n + off; q2++) { var v = byId(id + '-val' + (q2 - off)); if (v) gsap.set(v, { opacity: 0 }); }
    for (var q3 = 0; q3 < S.n; q3++) { var xl = byId(id + '-xl' + q3); if (xl) gsap.set(xl, { opacity: 0 }); }
    var xl0 = byId(id + '-xl-1'); if (xl0) gsap.set(xl0, { opacity: 0 });
    gsap.set(clip, { attr: { width: 0 } });
    gsap.set(area, { opacity: 0 });
    var shown = 0, lastF = 0, lastX = clipX;
    var axesT = sc.cues.filter(function (c) { return c.op === 'chart.axes'; })[0];
    drawAxes(sc, id, axesT ? axesT.t : sc.start + 0.4);
    // the starting point ("just learned") appears with the axes
    var startT = (axesT ? axesT.t : sc.start + 0.4) + 0.9;
    if (off) { var sp = byId(id + '-pt-1'); if (sp) popIn(sp, startT, 0.4); var sx = byId(id + '-xl-1'); if (sx) textIn(sx, startT, 0.3); tl.set(curve, { opacity: 1 }, startT); }
    sc.cues.filter(function (c) { return c.op === 'chart.point'; }).forEach(function (c) {
      var i = c.index, q = i + off, T = c.t;
      var f1 = fr[q], f0 = lastF;
      if (f1 > f0) {
        var D = clamp(0.5 + (f1 - f0) * 2.2, 0.5, 1.4);
        tl.set(curve, { opacity: 1 }, T);
        tl.fromTo(curve, { strokeDashoffset: 1 - f0 }, { strokeDashoffset: 1 - f1, duration: D, ease: 'power1.inOut', immediateRender: false }, T);
        tl.fromTo(clip, { attr: { width: lastX - clipX } }, { attr: { width: +xs[q] - clipX + 10 }, duration: D, ease: 'power1.inOut', immediateRender: false }, T);
        tl.fromTo(area, { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: false }, T);
        lastF = f1; lastX = +xs[q] + 10;
        var pt = byId(id + '-pt' + i); if (pt) popIn(pt, T + D * 0.8, 0.4);
        var vv = byId(id + '-val' + i); if (vv) textIn(vv, T + D * 0.85, 0.35);
        var xx = byId(id + '-xl' + i); if (xx) textIn(xx, T + D * 0.3, 0.35);
      } else {
        var vv2 = byId(id + '-val' + i); if (vv2) textIn(vv2, T, 0.35);
      }
    });
    sc.cues.filter(function (c) { return c.op === 'chart.callout'; }).forEach(function (c, i) {
      var box = byId(id + '-co' + i), arr = byId(id + '-coarrow' + i);
      textIn(box, c.t, 0.35);
      tl.set(arr, { opacity: 1 }, c.t + 0.1);
      $$('path', arr).forEach(function (p, m) { p.setAttribute('pathLength', '1'); gsap.set(p, { strokeDasharray: '1 2', strokeDashoffset: 1 }); tl.fromTo(p, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: m ? 0.15 : 0.45, ease: 'power1.inOut', immediateRender: true }, c.t + 0.1 + (m ? 0.42 : 0)); });
      tl.to([box, arr], { opacity: 0, duration: 0.3 }, Math.min(sc.end - 0.5, c.t + 6));
      gsap.set(arr, { opacity: 0 });
    });
    sc.cues.filter(function (c) { return c.op === 'stamp'; }).forEach(function (c, i) { stampIn(byId(id + '-stamp' + i), c.t, sc); });
  };

  ANIM.review = function (sc) {
    var S = sc.stage, id = sc.id, n = S.reviews.length;
    var axesT = sc.cues.filter(function (c) { return c.op === 'chart.axes'; })[0];
    drawAxes(sc, id, axesT ? axesT.t : sc.start + 0.4);
    var base = byId(id + '-base'); base.setAttribute('pathLength', '1'); gsap.set(base, { strokeDasharray: '3 12', opacity: 0 });
    for (var k = 0; k <= n; k++) { var s = byId(id + '-seg' + k), a = byId(id + '-area' + k); if (s) { s.setAttribute('pathLength', '1'); gsap.set(s, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 }); } if (a) gsap.set(a, { opacity: 0 }); }
    for (var r = 0; r < n; r++) { var j = byId(id + '-jump' + r), fl = byId(id + '-flag' + r), lb = byId(id + '-rv' + r); if (j) { j.setAttribute('pathLength', '1'); gsap.set(j, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 }); } if (fl) { fl.setAttribute('pathLength', '1'); gsap.set(fl, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 }); } if (lb) gsap.set(lb, { opacity: 0 }); }
    var lg = byId(id + '-leg0'); if (lg) gsap.set(lg, { opacity: 0 });
    sc.cues.filter(function (c) { return c.op === 'chart.line'; }).forEach(function (c) {
      tl.set(base, { opacity: 1 }, c.t);
      tl.fromTo(base, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.6, ease: 'power1.inOut', immediateRender: true }, c.t);
      if (lg) textIn(lg, c.t + 1.1, 0.4);
    });
    sc.cues.filter(function (c) { return c.op === 'chart.review'; }).forEach(function (c) {
      var i = c.index, T = c.t;
      var seg = byId(id + '-seg' + i), area = byId(id + '-area' + i);
      var D = i === 0 ? 1.1 : 0.9;
      tl.set(seg, { opacity: 1 }, T);
      tl.fromTo(seg, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: D, ease: 'power1.inOut', immediateRender: true }, T);
      if (area) tl.fromTo(area, { opacity: 0 }, { opacity: 1, duration: D, immediateRender: true }, T);
      var jp = byId(id + '-jump' + i), fl = byId(id + '-flag' + i), lb = byId(id + '-rv' + i);
      tl.set(jp, { opacity: 1 }, T + D);
      tl.fromTo(jp, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.3, ease: 'power2.out', immediateRender: true }, T + D);
      tl.set(fl, { opacity: 1 }, T + D + 0.2);
      tl.fromTo(fl, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.3, immediateRender: true }, T + D + 0.2);
      textIn(lb, T + D * 0.6, 0.35);
      if (i === n - 1) { // the tail after the last review
        var tail = byId(id + '-seg' + n), ta = byId(id + '-area' + n);
        tl.set(tail, { opacity: 1 }, T + D + 0.35);
        tl.fromTo(tail, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.0, ease: 'power1.out', immediateRender: true }, T + D + 0.35);
        if (ta) tl.fromTo(ta, { opacity: 0 }, { opacity: 1, duration: 1.0, immediateRender: true }, T + D + 0.35);
      }
    });
    sc.cues.filter(function (c) { return c.op === 'stamp'; }).forEach(function (c, i) { stampIn(byId(id + '-stamp' + i), c.t, sc); });
  };

  ANIM.bar = function (sc) {
    var S = sc.stage, id = sc.id;
    var axesT = sc.cues.filter(function (c) { return c.op === 'chart.axes'; })[0];
    drawAxes(sc, id, axesT ? axesT.t : sc.start + 0.4);
    for (var i = 0; i < S.n; i++) {
      var rect = byId(S.rects[i]), bl = byId(id + '-bl' + i), bv = byId(id + '-bv' + i);
      gsap.set(rect, { attr: { y: S.baseline, height: 0 } }); gsap.set(bv, { opacity: 0 }); gsap.set(bl, { opacity: 0 });
      var line = byId(id + '-bar' + i).querySelector('path[pathLength], path:last-child');
      textIn(bl, sc.start + 0.9 + i * 0.15, 0.4);
    }
    sc.cues.filter(function (c) { return c.op === 'chart.bar'; }).forEach(function (c) {
      var i = c.index, rect = byId(S.rects[i]), h = +S.heights[i] + 24;
      tl.fromTo(rect, { attr: { y: S.baseline, height: 0 } }, { attr: { y: S.baseline - h, height: h + 4 }, duration: 0.9, ease: 'power3.out', immediateRender: false }, c.t);
      popIn(byId(id + '-bv' + i), c.t + 0.6, 0.45);
    });
  };

  ANIM.steps = function (sc) {
    var S = sc.stage, id = sc.id;
    for (var i = 0; i < S.n; i++) { var c = byId(id + '-c' + i); gsap.set(c, { opacity: 0 }); var cf = byId(id + '-cf' + i); cf.setAttribute('pathLength', '1'); gsap.set(cf, { strokeDasharray: '1 2', strokeDashoffset: 1 }); if (i) { var ar = byId(id + '-ar' + (i - 1)); ar.setAttribute('pathLength', '1'); gsap.set(ar, { strokeDasharray: '1 2', strokeDashoffset: 1, opacity: 0 }); } }
    sc.cues.filter(function (c) { return c.op === 'steps.reveal'; }).forEach(function (c) {
      var i = c.index, card = byId(id + '-c' + i), cf = byId(id + '-cf' + i);
      tl.fromTo(card, { opacity: 0, y: 40, rotation: -1.4 }, { opacity: 1, y: 0, rotation: 0, duration: 0.55, ease: 'back.out(1.6)', immediateRender: true }, c.t);
      tl.fromTo(cf, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.7, ease: 'power1.inOut', immediateRender: true }, c.t + 0.05);
      var mk = card.querySelector('.mk-l i'); if (mk) { gsap.set(mk, { scaleX: 0 }); tl.fromTo(mk, { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: 'power2.out', immediateRender: true }, c.t + 0.35); }
      if (i) { var ar = byId(id + '-ar' + (i - 1)); tl.set(ar, { opacity: 1 }, c.t - 0.05); tl.fromTo(ar, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.5, ease: 'power1.inOut', immediateRender: true }, c.t - 0.05); }
    });
  };

  ANIM.recap = function (sc) {
    var S = sc.stage, id = sc.id;
    for (var i = 0; i < S.n; i++) {
      var row = byId(id + '-r' + i), ck = byId(id + '-ck' + i), ul = byId(id + '-ul' + i), mk = row.querySelector('.rk');
      gsap.set(row, { opacity: 0 }); ck.setAttribute('pathLength', '1'); ul.setAttribute('pathLength', '1');
      gsap.set([ck, ul], { strokeDasharray: '1 2', strokeDashoffset: 1 });
    }
    sc.cues.filter(function (c) { return c.op === 'recap.check'; }).forEach(function (c) {
      var i = c.index, row = byId(id + '-r' + i), ck = byId(id + '-ck' + i), ul = byId(id + '-ul' + i), mk = row.querySelector('.rk');
      tl.fromTo(row, { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.45, ease: EASE_OUT, immediateRender: true }, c.t);
      tl.fromTo(ul, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.7, ease: 'power1.inOut', immediateRender: true }, c.t + 0.1);
      tl.fromTo(mk, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: 'power2.out', immediateRender: true }, c.t + 0.3);
      tl.fromTo(ck, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.4, ease: 'power2.out', immediateRender: true }, c.t + 0.45);
    });
  };

  AM.scenes.forEach(function (sc) {
    var inner = byId('in-' + sc.id), hl = byId('hl-' + sc.id);
    // scene in / out
    tl.fromTo(inner, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: 'power1.out', immediateRender: true }, sc.start);
    tl.to(inner, { opacity: 0, duration: 0.35, ease: 'power1.in' }, sc.end - 0.35);
    // headline: slides up, marker wipes in
    var span = hl.querySelector('span');
    tl.fromTo(hl, { y: 26, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: EASE_OUT, immediateRender: true }, sc.start + 0.1);
    tl.fromTo(span, { '--mk': 0 }, { '--mk': 1, duration: 0.5, ease: 'power2.out', immediateRender: true }, sc.start + 0.45);
    if (sc.type !== 'illustration') { // a barely-there drift keeps still diagrams alive (and video compression honest)
      var stg = byId('st-' + sc.id);
      gsap.set(stg, { transformOrigin: '50% 45%' });
      tl.fromTo(stg, { scale: 1, y: 0 }, { scale: 1.016, y: -3, duration: sc.end - sc.start, ease: 'none', immediateRender: true }, sc.start);
    }
    var kind = sc.stage.kind, type = sc.type;
    var fn = type === 'illustration' ? ANIM.illustration : type === 'chart' ? ANIM[kind] : ANIM[type];
    if (fn) fn(sc);
  });

  // ---------------------------------------------------------------------------------------------
  // captions
  // ---------------------------------------------------------------------------------------------
  AM.captions.forEach(function (c) {
    var el = byId(c.id), p = el.querySelector('p'), w = el.querySelector('.who');
    tl.fromTo(p, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.16, ease: 'power2.out', immediateRender: true }, c.s);
    tl.fromTo(w, { opacity: 0 }, { opacity: 1, duration: 0.16, immediateRender: true }, c.s);
  });

  // ---------------------------------------------------------------------------------------------
  // avatars: state tracks (tl.set), speaker halo, head bob, listener nods
  // ---------------------------------------------------------------------------------------------
  function applyTrack(prefix, tr, def) {
    var cur = def, els = {};
    var get = function (s) { return els[s] || (els[s] = byId(prefix + s)); };
    tr.forEach(function (e) {
      var t = e[0], s = e[1];
      if (s === cur) return;
      if (t <= 0) { gsap.set(get(cur), { opacity: 0 }); gsap.set(get(s), { opacity: 1 }); cur = s; return; }
      tl.set(get(cur), { opacity: 0 }, t);
      tl.set(get(s), { opacity: 1 }, t);
      cur = s;
    });
  }
  ['left', 'right'].forEach(function (side) {
    var f = AM.faces[side];
    if (!f) return;
    applyTrack(f.prefix, f.eyes, 'eyes-open');
    applyTrack(f.prefix, f.brows, 'brows-normal');
    applyTrack(f.prefix, f.mouth, 'mouth-closed');
    var av = byId('av-' + side), halo = byId('halo-' + side), body = byId('avbody-' + side);
    var rig = byId(f.prefix + 'head-rig'), pv = byId(f.prefix + 'neck-pivot');
    var px = pv ? +pv.getAttribute('cx') : 150, py = pv ? +pv.getAttribute('cy') : 250;
    gsap.set(rig, { svgOrigin: px + ' ' + py });
    // avatars slide in after the intro
    tl.fromTo(av, { y: 460, opacity: 1 }, { y: 0, duration: 0.8, ease: 'back.out(1.3)', immediateRender: true }, AM.intro.end - 0.55);
    // speaker spans (merge lines separated by short gaps)
    var mine = AM.lines.filter(function (l) { return l.who === f.who; });
    var spans = [];
    mine.forEach(function (l) { var last = spans[spans.length - 1]; if (last && l.start - last.end < 0.9) last.end = l.end; else spans.push({ start: l.start, end: l.end }); });
    gsap.set(halo, { opacity: 0, scale: 0.7 });
    spans.forEach(function (s) {
      tl.fromTo(halo, { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.28, ease: 'back.out(1.6)', immediateRender: false }, s.start - 0.05);
      tl.to(halo, { opacity: 0, scale: 0.85, duration: 0.3, ease: 'power1.in' }, s.end + 0.05);
    });
    // speaking bob (finite yoyo per line) and a nod for the listener
    mine.forEach(function (l) {
      var d = l.end - l.start;
      tl.fromTo(rig, { rotation: -0.8, y: 0 }, { rotation: 1.4, y: -2.2, duration: 0.42, ease: 'sine.inOut', yoyo: true, repeat: reps(d, 0.42), immediateRender: false }, l.start);
      tl.set(rig, { rotation: 0, y: 0 }, l.end + 0.02);
    });
    AM.lines.filter(function (l) { return l.who !== f.who && l.end - l.start > 1.2; }).forEach(function (l) {
      var t = l.start + Math.min(1.1, (l.end - l.start) * 0.4);
      tl.fromTo(rig, { rotation: 0, y: 0 }, { rotation: 2.4, y: 3, duration: 0.22, ease: 'sine.inOut', yoyo: true, repeat: 1, immediateRender: false }, t);
    });
    // gentle breathing of the whole body
    gsap.set(body, { transformOrigin: '50% 100%' });
    tl.fromTo(body, { scale: 1 }, { scale: 1.012, duration: 2.1, ease: 'sine.inOut', yoyo: true, repeat: reps(AM.duration - AM.intro.end, 2.1), immediateRender: false }, AM.intro.end);
  });

  // ---------------------------------------------------------------------------------------------
  // intro card
  // ---------------------------------------------------------------------------------------------
  var introEnd = AM.intro.end;
  var l1 = byId('in-l1'), l2 = byId('in-l2');
  tl.fromTo(byId('in-kick'), { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.5, ease: EASE_OUT, immediateRender: true }, 0.2);
  [l1, l2].forEach(function (l, i) {
    if (!l) return;
    tl.fromTo(l, { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.7, ease: 'power4.out', immediateRender: true }, 0.45 + i * 0.22);
    var mk = l.querySelector('.mk'); if (mk && getComputedStyle(mk).opacity !== '0') { tl.fromTo(mk, { scaleX: 0 }, { scaleX: 1, duration: 0.55, ease: 'power2.out', immediateRender: true }, 0.9 + i * 0.22); }
  });
  var mk2 = l2 && l2.querySelector('.mk'); if (mk2) { gsap.set(mk2, { opacity: 1 }); tl.fromTo(mk2, { scaleX: 0 }, { scaleX: 1, duration: 0.55, ease: 'power2.out', immediateRender: true }, 1.15); }
  tl.fromTo(byId('in-bar'), { scaleX: 0 }, { scaleX: 1, duration: 0.8, ease: 'power3.inOut', immediateRender: true }, 0.9);
  tl.fromTo(byId('in-sub'), { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.5, ease: EASE_OUT, immediateRender: true }, 1.35);
  tl.to(byId('intro'), { opacity: 0, duration: 0.35, ease: 'power1.in' }, introEnd - 0.05);

  // ---------------------------------------------------------------------------------------------
  // outro card
  // ---------------------------------------------------------------------------------------------
  var o = AM.outro;
  tl.fromTo(byId('o-stage'), { opacity: 0 }, { opacity: 1, duration: 0.5 }, o.start + 0.05);
  tl.fromTo(byId('o-kick'), { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.4, ease: EASE_OUT, immediateRender: true }, o.start + 0.3);
  tl.fromTo(byId('o-big').querySelector('span'), { opacity: 0, y: 50 }, { opacity: 1, y: 0, duration: 0.6, ease: 'power4.out', immediateRender: true }, o.start + 0.45);
  tl.fromTo(byId('o-big').querySelector('.mk'), { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: 'power2.out', immediateRender: true }, o.start + 0.85);
  tl.fromTo(byId('o-sub'), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.5, ease: EASE_OUT, immediateRender: true }, o.start + 1.1);
  tl.fromTo(byId('o-credits'), { opacity: 0 }, { opacity: 1, duration: 0.8 }, o.linesEnd + 0.15);

  window.__timelines = window.__timelines || {};
  window.__timelines['main'] = tl;
})();
