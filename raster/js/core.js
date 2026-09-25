/* RASTER — core: seeded random, the live modular grid, SVG and type helpers.
   The sheet is the viewport: geometry is in CSS pixels and recomputed on resize.
   Latin is set in the Helvetica family; Japanese falls through to Hiragino or Noto Sans JP. */
(function (R) {
  'use strict';

  const PALETTE = {
    normal: { paper: '#f2efe8', red: '#e30613', black: '#111111', white: '#ffffff', blend: 'multiply' },
    /* Inverted: black ground, paper-coloured ink; knock-outs show the ground; inks add light. */
    inverted: { paper: '#111111', red: '#e30613', black: '#f2efe8', white: '#111111', blend: 'screen' },
  };
  R.INK = Object.assign({}, PALETTE.normal);
  R.setInverted = (on) => Object.assign(R.INK, on ? PALETTE.inverted : PALETTE.normal);

  R.JP_FAMILY = 'Noto Sans JP';
  R.FONT = "'Helvetica Neue', Helvetica, Arial, 'Nimbus Sans', 'Liberation Sans', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif";

  const CJK = '\\u2E80-\\u2FFF\\u3000-\\u30FF\\u3400-\\u4DBF\\u4E00-\\u9FFF\\uF900-\\uFAFF\\uFF00-\\uFFEF';
  const CJK_RE = new RegExp(`[${CJK}]`);
  R.hasCJK = (s) => CJK_RE.test(s);

  /* ---------- seeded random (mulberry32), seeded by the edition number ---------- */
  R.rng = function (seed) {
    let a = (Math.imul(seed + 1, 2654435761) ^ 0x9e3779b9) >>> 0;
    const next = function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    return {
      next,
      range: (lo, hi) => lo + (hi - lo) * next(),
      int: (lo, hi) => lo + Math.floor(next() * (hi - lo + 1)),
      pick: (arr) => arr[Math.floor(next() * arr.length)],
      chance: (p) => next() < p,
    };
  };

  /* ---------- the grid: 12 columns landscape, 6 portrait; rows keep modules nearly square ---------- */
  R.grid = function (W, H) {
    const landscape = W >= H;
    const C = landscape ? 12 : 6;
    const short = Math.min(W, H);
    const m = Math.round(Math.max(16, short * 0.04));
    const g = Math.round(Math.max(8, short * 0.018));
    const cw = (W - 2 * m - (C - 1) * g) / C;
    const rows = Math.max(4, Math.round((H - 2 * m + g) / (cw + g)));
    const rh = (H - 2 * m - (rows - 1) * g) / rows;
    const G = { W, H, C, rows, m, g, cw, rh, landscape };
    G.x = (c) => m + c * (cw + g);
    G.y = (r) => m + r * (rh + g);
    G.w = (n) => n * cw + (n - 1) * g;
    G.h = (n) => n * rh + (n - 1) * g;
    G.zone = (c0, r0, nc, nr) => ({ c0, r0, nc, nr, x: G.x(c0), y: G.y(r0), w: G.w(nc), h: G.h(nr) });
    /* small type scale, tied to the column */
    G.S = Math.max(9, Math.min(15, cw * 0.12));
    return G;
  };

  /* ---------- SVG ---------- */
  const NS = 'http://www.w3.org/2000/svg';
  R.el = function (tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  /* Print passes: red (and knock-outs) go down first, black last. Inks overprint; knock-outs do not. */
  R.pass = (c) => (c === R.INK.black ? '2' : '1');
  const cls = (c) => (c === R.INK.white ? 'ko' : 'ink');
  R.shape = function (tag, attrs, fill, parent) {
    return R.el(tag, Object.assign({ fill, 'data-pass': R.pass(fill), class: cls(fill) }, attrs), parent);
  };
  R.line = function (tag, attrs, stroke, width, parent) {
    return R.el(tag, Object.assign({ fill: 'none', stroke, 'stroke-width': width, 'data-pass': R.pass(stroke), class: 'ink' }, attrs), parent);
  };
  R.rect = (x, y, w, h, fill, parent) => R.shape('rect', { x, y, width: w, height: h }, fill, parent);
  R.disc = (cx, cy, r, fill, parent) => R.shape('circle', { cx, cy, r }, fill, parent);

  /* ---------- type ---------- */
  R.fontStyle = (f) =>
    `font-family:${R.FONT};font-weight:${f.wt || 400};font-size:${f.size}px` + (f.ls ? `;letter-spacing:${f.ls}em` : '') +
    (f.vertical ? ';writing-mode:vertical-rl;text-orientation:mixed' : '');

  R.text = function (parent, str, x, baseline, f, fill) {
    const t = R.shape('text', { x, y: baseline, style: R.fontStyle(f) }, fill, parent);
    t.textContent = str;
    return t;
  };

  let probe = null;
  const widths = new Map();
  const boxes = new Map();
  function probeText() {
    if (!probe) {
      const svg = R.el('svg', { width: 0, height: 0, 'aria-hidden': 'true', style: 'position:absolute;left:-9999px;top:0;overflow:hidden' });
      document.body.appendChild(svg);
      probe = R.el('text', { x: 0, y: 0 }, svg);
    }
    return probe;
  }
  /* Advance width, measured by the same SVG text engine that renders the poster; tracking in em. */
  R.textWidth = function (str, f) {
    const key = `${f.wt || 400}|${str}`;
    let w = widths.get(key);
    if (w == null) {
      const t = probeText();
      t.setAttribute('style', R.fontStyle({ wt: f.wt, size: 100 })); /* vertical lines measure the same advance */
      t.textContent = str;
      w = t.getComputedTextLength() / 100;
      widths.set(key, w);
    }
    const n = Array.from(str).length;
    return f.size * (w + (f.ls || 0) * Math.max(0, n - 1));
  };

  let ctx = null;
  /* Ink box of a string: top above the baseline, bottom below it, left side bearing. */
  R.box = function (str, f) {
    const key = `${f.wt || 400}|${str}`;
    let b = boxes.get(key);
    if (!b) {
      try {
        ctx = ctx || document.createElement('canvas').getContext('2d');
        ctx.font = `${f.wt || 400} 100px ${R.FONT}`;
        const m = ctx.measureText(str);
        b = { top: m.actualBoundingBoxAscent / 100, bottom: Math.max(0, m.actualBoundingBoxDescent / 100), left: -m.actualBoundingBoxLeft / 100, right: m.actualBoundingBoxRight / 100 };
      } catch (e) {
        b = null;
      }
      if (!b || !(b.top > 0)) b = { top: 0.72, bottom: 0, left: 0, right: 0.6 * Array.from(str).length };
      boxes.set(key, b);
    }
    return { top: b.top * f.size, bottom: b.bottom * f.size, left: b.left * f.size, right: b.right * f.size, height: (b.top + b.bottom) * f.size };
  };

  let capRatio = 0.72;
  let kanjiTop = 0.86;
  R.measureFonts = function () {
    widths.clear();
    boxes.clear();
    const c = R.box('H', { wt: 700, size: 1 }).top;
    if (c > 0.55 && c < 0.85) capRatio = c;
    const k = R.box('国', { wt: 700, size: 1 }).top;
    if (k > 0.6 && k < 1) kanjiTop = k;
  };
  R.cap = (size) => size * capRatio;
  /* Small type hangs from a grid line by its cap height, or by the kanji face when the line is Japanese. */
  R.hang = (line, size) => size * (R.hasCJK(line) ? kanjiTop : capRatio);

  /* Display type: the largest size at which `str` fits maxW × maxH (advance width × ink height). */
  R.fit = function (str, maxW, maxH, wt, ls) {
    const one = { wt, ls, size: 1 };
    const w1 = R.textWidth(str, one);
    const h1 = R.box(str, one).height;
    const size = Math.min(maxW / w1, maxH / h1);
    const f = { wt, ls, size };
    const b = R.box(str, f);
    /* canvas measures without tracking; move the ink's right edge by the tracking between glyphs */
    b.right += (ls || 0) * size * Math.max(0, Array.from(str).length - 1);
    return Object.assign({ f, width: w1 * size, ink: b.right - b.left }, b);
  };
  /* Set display type with its ink box's top-left at (x, y). */
  R.setAt = function (parent, str, x, y, fit, fill) {
    return R.text(parent, str, x - fit.left, y + fit.top, fit.f, fill);
  };

  /* ---------- line breaking: Latin on spaces, Japanese between characters, with kinsoku ---------- */
  const OPEN = '「『（〔［｛〈《【“‘(\\[';
  const CLOSE = '、。，．・：；？！ー…」』）〕］｝〉》】”’ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ々〻';
  const TOKEN = new RegExp(`[${OPEN}]*(?:[^\\s${CJK}]+|\\s+|[${CJK}])[${CLOSE}]*`, 'gu');
  const SPACE = /^\s+$/;

  R.wrap = function (str, f, maxW) {
    const lines = [];
    for (const para of String(str).split('\n')) {
      const tokens = para.match(TOKEN) || [];
      let line = '';
      for (const tk of tokens) {
        if (!line && SPACE.test(tk)) continue;
        const t = line + tk;
        if (line && R.textWidth(t.trimEnd(), f) > maxW) {
          lines.push(line.trimEnd());
          line = SPACE.test(tk) ? '' : tk;
        } else line = t;
      }
      lines.push(line.trimEnd());
    }
    return lines;
  };

  /* Stack runs of lines; the first line hangs from y = 0. Japanese runs get a looser lead. */
  R.flow = function (runs) {
    const items = [];
    let base = null;
    for (const run of runs) {
      const lead = run.lead || (R.hasCJK(run.lines.join('')) ? 1.6 : 1.3);
      run.lines.forEach((line, i) => {
        if (base === null) base = R.hang(line, run.f.size);
        else base += run.f.size * lead + (i === 0 ? run.gap || 0 : 0);
        items.push({ line, base, f: run.f, fill: run.fill || R.INK.black });
      });
    }
    const last = items[items.length - 1];
    return {
      items,
      h: last ? last.base + last.f.size * 0.24 : 0,
      draw(parent, x, top) {
        for (const it of items) if (it.line) R.text(parent, it.line, x, top + it.base, it.f, it.fill);
      },
    };
  };
})((window.RASTER = window.RASTER || {}));
