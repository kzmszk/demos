/* RASTER — motifs I: 数字, 三つの文字, 弧, 円と月.
   Each motif draws into the display zone D and may run off the sheet edges inside the bleed box B.
   Display type is Helvetica Bold, tracked tight, and placed by its ink so it sits on the grid. */
(function (R) {
  'use strict';

  const INK = R.INK;
  const M = (R.motifs = R.motifs || {});

  /* ---------- shared kit ---------- */
  const K = (R.kit = {});
  K.ls = (s) => (R.hasCJK(s) ? -0.02 : -0.045);
  /* The edge of the display that meets the small type; big things anchor there and spill away from it. */
  K.anchor = (plan) => (plan.kind === 'column' || plan.at === 'bottom' ? 'bottom' : 'top');
  /* Small red parenthetical, hung from y by its cap or kanji face. align: 'start' | 'end'. */
  K.gloss = function (g, text, x, y, G, align) {
    if (!text) return;
    const f = { wt: 400, size: G.S * 1.55 };
    const w = R.textWidth(text, f);
    R.text(g, text, align === 'end' ? x - w : x, y + R.hang(text, f.size), f, INK.red);
    return { w, h: R.hang(text, f.size) + f.size * 0.25 };
  };
  K.tag = function (g, text, x, y, G) {
    const f = { wt: 700, size: Math.max(8, G.S * 0.78), ls: 0.1 };
    R.text(g, text, x, y + R.hang(text, f.size), f, INK.red);
  };
  const snapCol = (G, x) => G.x(Math.round((x - G.m) / (G.cw + G.g)));

  /* 数字 — a numeral as tall as the zone or taller, cropped by the sheet; the red sun overprints it. */
  M.zahl = function ({ g, D, G, rng, P, plan }) {
    const n = P.words.numeral;
    const k = rng.pick([1, 1.2, 1.45]);
    const ls = K.ls(n);
    let fit = R.fit(n, Infinity, D.h * k, 700, ls);
    const maxW = D.w * (k > 1 ? 1.1 : 1);
    if (fit.ink > maxW) fit = R.fit(n, maxW * (fit.width / fit.ink), Infinity, 700, ls);
    const flushRight = rng.chance(0.3);
    const at = K.anchor(plan);
    const x = flushRight ? D.x + D.w - fit.ink : D.x - (k > 1.3 ? G.cw * 0.6 : 0);
    const y = at === 'bottom' ? D.y + D.h - fit.height : D.y;

    const r = Math.min(D.h * rng.pick([0.28, 0.34, 0.4]), D.w * 0.45);
    const cx = snapCol(G, flushRight ? D.x + D.w * rng.pick([0.25, 0.4]) : D.x + D.w * rng.pick([0.6, 0.72]));
    const cy = D.y + D.h * rng.pick([0.36, 0.5, 0.62]);
    const lines = rng.chance(0.5);
    const dot = rng.chance(0.5);

    R.setAt(g, n, x, y, fit, INK.black);
    R.disc(cx, cy, r, INK.red, g);
    R.line('circle', { cx, cy, r: r * 0.62 }, INK.red, Math.max(2, G.g * 0.28), g);
    if (dot) R.disc(cx, cy, Math.max(3, G.g * 0.35), INK.black, g);
    const gx = G.x(D.c0 + D.nc - 2);
    let gy = at === 'bottom' ? D.y : D.y + D.h - G.S * 3;
    if (lines) {
      const top = at === 'bottom' ? D.y : D.y + D.h - G.g * 3;
      for (let i = 0; i < 6; i++) R.rect(gx, top + i * G.g * 0.55, G.w(2), Math.max(1, G.g * 0.1), INK.black, g);
      if (at === 'bottom') gy = top + G.g * 3.8;
      else gy = top - G.S * 2.4;
    }
    K.gloss(g, P.words.gloss, gx, gy, G);
  };

  /* 三つの文字 — one word stacked in kanji, kana and Latin, with a row of growing dots. */
  M.drei = function ({ g, D, G, rng, P, plan }) {
    const words = P.words.three;
    const tagW = G.w(1) + G.g;
    const one = words.map((w) => ({ w1: R.textWidth(w, { wt: 700, ls: K.ls(w), size: 1 }), b: R.box(w, { wt: 700, size: 1 }) }));
    const gapK = 0.1;
    const hSum = one.reduce((s, o) => s + o.b.height, 0) + 2 * gapK;
    const dotsRoom = rng.chance(0.6);
    const availH = D.h * (dotsRoom ? 0.8 : 1);
    const size = Math.min(availH / hSum, ...one.map((o) => (D.w - tagW) / o.w1));
    const red = rng.pick([0, 1]);
    const at = K.anchor(plan);
    const stackH = hSum * size;
    let y = at === 'top' ? D.y : D.y + (dotsRoom ? 0 : D.h - stackH);
    const labels = ['漢字 KANJI', 'かな KANA', 'LATIN'];
    words.forEach((w, i) => {
      const fit = R.fit(w, Infinity, one[i].b.height * size, 700, K.ls(w));
      R.setAt(g, w, D.x, y, fit, i === red ? INK.red : INK.black);
      K.tag(g, labels[i], G.x(D.c0 + D.nc - 1), y, G);
      y += fit.height + gapK * size;
    });
    if (!dotsRoom) return;
    const free = at === 'top' ? { y0: y, y1: D.y + D.h } : { y0: y, y1: D.y + D.h };
    const count = Math.max(6, Math.min(12, D.nc));
    const rMax = Math.min((free.y1 - free.y0) * 0.42, D.w / count / 2.2);
    if (rMax < G.g * 0.4) return;
    const cy = free.y1 - rMax;
    for (let i = 0; i < count; i++) {
      const t = (i + 1) / count;
      const cx = D.x + rMax + (i * (D.w - 2 * rMax)) / (count - 1);
      R.disc(cx, cy, Math.max(1.5, rMax * t * t), i === count - 1 ? INK.red : INK.black, g);
    }
  };

  /* 弧 — clean concentric quarter arcs from a corner on the rule, the word in the opposite corner. */
  M.bogen = function ({ g, D, G, rng, P, plan }) {
    const at = K.anchor(plan);
    const left = rng.chance(0.5);
    const ox = left ? D.x : D.x + D.w;
    const oy = at === 'bottom' ? D.y + D.h : D.y;
    const sx = left ? 1 : -1;
    const sy = at === 'bottom' ? -1 : 1;
    const sweep = sx * sy > 0 ? 1 : 0;
    const sw = (G.cw + G.g) * rng.pick([0.16, 0.22, 0.28]);
    const step = sw * rng.pick([1.9, 2.3]);
    const q = step * rng.pick([1, 1.4]);
    const Rmax = Math.min(D.h * rng.pick([0.95, 1.15]), D.w * 0.8);
    const arcs = [];
    for (let r = q + step * 0.75; r < Rmax; r += step) arcs.push(r);
    const redAt = rng.int(1, Math.max(1, arcs.length - 3));
    const quarter = (r) => `M${ox + sx * r} ${oy}A${r} ${r} 0 0 ${sweep} ${ox} ${oy + sy * r}`;
    R.shape('path', { d: `M${ox} ${oy}L${ox + sx * q} ${oy}A${q} ${q} 0 0 ${sweep} ${ox} ${oy + sy * q}Z` }, INK.red, g);
    arcs.forEach((r, i) => {
      const red = i === redAt || i === redAt + 1;
      R.line('path', { d: quarter(r), 'stroke-linecap': 'butt' }, red ? INK.red : INK.black, sw, g);
    });

    /* the word takes the far corner */
    const word = P.words.word;
    const fit = R.fit(word, D.w * 0.5, D.h * 0.3, 700, K.ls(word));
    const wx = left ? D.x + D.w - fit.ink : D.x;
    const wy = at === 'bottom' ? D.y : D.y + D.h - fit.height;
    R.setAt(g, word, wx, wy, fit, INK.black);
    const gy = at === 'bottom' ? wy + fit.height + G.S * 0.9 : wy - G.S * 2.6;
    K.gloss(g, P.words.gloss, left ? wx + fit.ink : wx, gy, G, left ? 'end' : 'start');
  };

  /* 円と月 — a red disc with an overprinted ring, a black moon and a red bar, the word across the base. */
  M.kreis = function ({ g, D, G, rng, P }) {
    const word = P.words.word;
    const fit = R.fit(word, D.w, D.h * 0.42, 700, K.ls(word));
    const Rb = Math.min(D.h * rng.pick([0.44, 0.5, 0.58]), D.w * 0.62);
    const right = rng.chance(0.7);
    const cx = snapCol(G, D.x + D.w * (right ? rng.pick([0.62, 0.7]) : rng.pick([0.3, 0.38])));
    const cy = D.y + D.h * rng.pick([0.4, 0.48]);
    const rm = Rb * rng.pick([0.28, 0.34]);
    const a = ((right ? 225 : 315) * Math.PI) / 180;
    const mx = cx + Math.cos(a) * Rb * 0.92;
    const my = cy + Math.sin(a) * Rb * 0.92;
    const barW = Math.max(3, G.g * 0.32);

    R.disc(cx, cy, Rb, INK.red, g);
    R.line('circle', { cx, cy, r: Rb * 0.45 }, INK.red, Math.max(2, G.g * 0.25), g);
    R.disc(mx, my, rm, INK.black, g);
    R.rect(mx - rm * 0.55, my - rm * 0.75, barW, rm * 0.75 + D.h * 0.42, INK.red, g);
    R.setAt(g, word, D.x, D.y + D.h - fit.height, fit, INK.black);
    /* red on red would vanish: the gloss takes the top corner away from the disc */
    K.gloss(g, P.words.gloss, right ? D.x : D.x + D.w, D.y, G, right ? 'start' : 'end');
  };
})((window.RASTER = window.RASTER || {}));
