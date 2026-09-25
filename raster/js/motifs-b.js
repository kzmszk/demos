/* RASTER — motifs II: 拍子, 縦, 斜線. */
(function (R) {
  'use strict';

  const INK = R.INK;
  const M = (R.motifs = R.motifs || {});
  const K = R.kit;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  /* 拍子 — the time signature set large above a staff rule; bars hang from it, one slot per beat,
     heavy on the first beat of each group (7/8 = 2+2+3). */
  M.takt = function ({ g, D, G, rng, P }) {
    const sig = P.words.signature;
    const num = +sig.split('/')[0];
    const groups = R.grouping(sig);
    const fit = R.fit(sig, D.w * (D.w < D.h ? 0.92 : 0.62), D.h * 0.5, 700, -0.04);
    const right = rng.chance(0.6);
    const sx = right ? D.x + D.w - fit.ink : D.x;
    R.setAt(g, sig, sx, D.y, fit, INK.black);
    const gx = right ? sx - G.g : sx + fit.ink + G.g;
    K.gloss(g, P.words.gloss, gx, D.y, G, right ? 'end' : 'start');

    const th = Math.max(2, G.g * 0.22);
    const ruleY = D.y + fit.height + G.g * 1.2;
    R.rect(D.x, ruleY, D.w, th, INK.black, g);
    const hr = clamp((ruleY - D.y) * 0.35, G.g, G.cw * 0.7);
    const hx = right ? D.x + hr : D.x + D.w - hr;
    R.shape('path', { d: `M${hx - hr} ${ruleY}A${hr} ${hr} 0 0 1 ${hx + hr} ${ruleY}Z` }, INK.red, g);

    const top = ruleY + th;
    const bottom = D.y + D.h;
    const slot = D.w / num;
    let beat = 0;
    groups.forEach((len, gi) => {
      for (let j = 0; j < len; j++, beat++) {
        const accent = j === 0;
        const w = Math.max(2, slot * (accent ? rng.pick([0.24, 0.34]) : rng.pick([0.03, 0.06, 0.12])));
        const x = D.x + beat * slot + (slot - w) * (accent ? 0 : rng.pick([0.3, 0.5, 0.7]));
        const h = (bottom - top) * (accent ? rng.pick([0.72, 1]) : rng.pick([0.18, 0.32, 0.5]));
        const stand = !accent && rng.chance(0.3);
        const ink = accent ? (gi === 0 ? INK.black : INK.red) : rng.chance(0.15) ? INK.red : INK.black;
        R.rect(x, stand ? bottom - h : top, w, h, ink, g);
      }
    });
  };

  /* Upright Japanese, centred in the strip and spread head to foot. */
  function tategaki(g, word, S, ink) {
    const chars = Array.from(word);
    const n = chars.length;
    const size = Math.min(S.w, S.h / n);
    const f = { wt: 700, size };
    const k = R.box('国', f);
    const mid = (k.top - k.bottom) / 2;
    const pitch = n > 1 ? (S.h - size) / (n - 1) : 0;
    const cx = S.x + S.w / 2;
    chars.forEach((ch, i) => {
      const cy = S.y + size / 2 + i * pitch;
      const t = R.text(g, ch, cx - R.textWidth(ch, f) / 2, cy + mid, f, ink);
      if (/[ー〜～—]/.test(ch)) t.setAttribute('transform', `rotate(90 ${cx.toFixed(1)} ${cy.toFixed(1)})`);
    });
  }

  /* 縦 — a word climbing a strip beside a halftone field that thickens toward it. */
  M.senkrecht = function ({ g, D, B, G, rng, P, defs }) {
    const word = P.words.word;
    const cjk = R.hasCJK(word);
    const n = Array.from(word).length;
    const picked = rng.pick([1, 2]);
    const sc = cjk ? clamp(Math.round(D.h / n / (G.cw + G.g)), 1, Math.floor(D.nc / 2)) : Math.max(1, Math.min(picked, Math.floor(D.nc / 3)));
    const stripLeft = rng.chance(0.5);
    const S = G.zone(stripLeft ? D.c0 : D.c0 + D.nc - sc, D.r0, sc, D.nr);
    const ink = rng.chance(0.35) ? INK.red : INK.black;
    if (cjk) tategaki(g, word, S, ink);
    else {
      const fit = R.fit(word, S.h, S.w, 700, K.ls(word));
      const t = R.text(g, word, -fit.left, 0, fit.f, ink);
      t.setAttribute('transform', `translate(${(S.x + fit.top).toFixed(1)} ${S.y + S.h}) rotate(-90)`);
    }

    const hair = Math.max(1.5, G.g * 0.12);
    const lx = stripLeft ? S.x + S.w + G.g / 2 : S.x - G.g / 2;
    R.rect(lx - hair / 2, B.y, hair, B.h, INK.red, g);

    const x1 = stripLeft ? S.x + S.w + G.g : B.x;
    const x2 = stripLeft ? B.x + B.w : S.x - G.g;
    const clip = R.el('clipPath', { id: 'rs-field' }, defs);
    R.el('rect', { x: x1, y: B.y, width: x2 - x1, height: B.h }, clip);
    const p = (G.cw + G.g) / rng.pick([4, 5]);
    const radial = rng.chance(0.5);
    const fy = rng.chance(0.5) ? B.y + B.h : B.y;
    const near = stripLeft ? x1 : x2;
    const span = Math.hypot(x2 - x1, B.h);
    const gamma = rng.pick([1.2, 1.8]);
    let d = '';
    for (let i = Math.floor((x1 - G.m) / p); G.m + (i + 0.5) * p <= x2; i++) {
      const x = G.m + (i + 0.5) * p;
      if (x < x1) continue;
      for (let j = Math.floor((B.y - G.m) / p); G.m + (j + 0.5) * p <= B.y + B.h; j++) {
        const y = G.m + (j + 0.5) * p;
        if (y < B.y) continue;
        const t = radial ? 1 - Math.hypot(x - near, y - fy) / span : 1 - Math.abs(x - near) / (x2 - x1);
        const r = p * 0.47 * Math.pow(clamp(t, 0, 1), gamma);
        if (r < 0.6) continue;
        d += `M${(x - r).toFixed(1)} ${y.toFixed(1)}a${r.toFixed(1)} ${r.toFixed(1)} 0 1 0 ${(2 * r).toFixed(1)} 0a${r.toFixed(1)} ${r.toFixed(1)} 0 1 0 ${(-2 * r).toFixed(1)} 0`;
      }
    }
    const field = R.el('g', { 'clip-path': 'url(#rs-field)' }, g);
    if (d) R.shape('path', { d }, INK.black, field);
    K.gloss(g, P.words.gloss, stripLeft ? x1 + G.g : x2 - G.g, D.y, G, stripLeft ? 'start' : 'end');
  };

  /* 斜線 — a stair of parallel bars at an angle, running off the sheet; the word rides the band. */
  M.diagonale = function ({ g, D, B, G, rng, P }) {
    const ang = rng.pick([-45, -30, 30, 45]);
    const t = (G.cw + G.g) * rng.pick([0.26, 0.36]);
    const gap = t * rng.pick([0.55, 0.9]);
    const n = rng.int(5, 8);
    const cx = G.x(D.c0 + Math.round(D.nc * rng.pick([0.35, 0.5]))) - G.g / 2;
    const cy = D.y + D.h * rng.pick([0.5, 0.62]);
    const L = Math.hypot(B.w, B.h);
    const step = t * rng.pick([1.2, 2, 3]);
    const red = rng.int(0, n - 1);
    const band = R.el('g', { transform: `translate(${cx.toFixed(1)} ${cy.toFixed(1)}) rotate(${ang})` }, g);
    const y0 = -((n - 1) * (t + gap)) / 2 - t / 2;
    for (let i = 0; i < n; i++) {
      const x0 = -L * 0.12 + i * step;
      R.rect(x0, y0 + i * (t + gap), L, t, i === red ? INK.red : INK.black, band);
    }
    const word = P.words.word;
    const fit = R.fit(word, Infinity, t * 2.6, 700, K.ls(word));
    const wx = -L * 0.12;
    const wy = y0 - gap - fit.height;
    R.setAt(band, word, wx, wy, fit, INK.black);
    if (P.words.gloss) {
      const f = { wt: 400, size: G.S * 1.55 };
      R.text(band, P.words.gloss, wx + fit.ink + G.g, wy + R.hang(P.words.gloss, f.size), f, INK.red);
    }
  };
})((window.RASTER = window.RASTER || {}));
