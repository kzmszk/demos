/* Kinetic Manifesto — portal: find the counter (enclosed white space) of any glyph.
   The glyph is rasterised offscreen, the outside is flood-filled from the border, the
   remaining enclosed components are labelled, and a two-pass chamfer distance transform
   gives each component's largest inscribed circle. The biggest circle is the portal:
   its centre is the zoom origin, its radius sets the zoom needed to cover the viewport,
   and the (slightly dilated) component becomes the accent mask under the glyph. */
(function (root) {
  'use strict';
  const K = root.K;
  const P = (K.portal = {});
  const cache = new Map();
  const RASTER = 320; /* px per em for the analysis */

  function chamfer(W, H, inside) {
    const N = W * H, d = new Float32Array(N), BIG = 1e9, D1 = 1, D2 = Math.SQRT2;
    for (let i = 0; i < N; i++) d[i] = inside(i) ? BIG : 0;
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const i = y * W + x;
        if (!d[i]) continue;
        let v = d[i];
        if (x > 0) v = Math.min(v, d[i - 1] + D1);
        if (y > 0) {
          v = Math.min(v, d[i - W] + D1);
          if (x > 0) v = Math.min(v, d[i - W - 1] + D2);
          if (x < W - 1) v = Math.min(v, d[i - W + 1] + D2);
        }
        d[i] = v;
      }
    }
    for (let y = H - 1; y >= 0; y--) {
      for (let x = W - 1; x >= 0; x--) {
        const i = y * W + x;
        if (!d[i]) continue;
        let v = d[i];
        if (x < W - 1) v = Math.min(v, d[i + 1] + D1);
        if (y < H - 1) {
          v = Math.min(v, d[i + W] + D1);
          if (x < W - 1) v = Math.min(v, d[i + W + 1] + D2);
          if (x > 0) v = Math.min(v, d[i + W - 1] + D2);
        }
        d[i] = v;
      }
    }
    return d;
  }

  /* Analyse one grapheme. All results are in em, relative to the pen origin on the baseline. */
  P.analyze = function (ch, font) {
    const key = font.cls + '|' + ch;
    if (cache.has(key)) return cache.get(key);
    const S = RASTER;
    const m = K.meas.ctx(font, S).measureText(ch);
    const L = Math.ceil(m.actualBoundingBoxLeft), R = Math.ceil(m.actualBoundingBoxRight);
    const A = Math.ceil(m.actualBoundingBoxAscent), D = Math.ceil(m.actualBoundingBoxDescent);
    const pad = 4;
    const W = Math.max(8, L + R + pad * 2), H = Math.max(8, A + D + pad * 2);
    const cv = document.createElement('canvas');
    cv.width = W;
    cv.height = H;
    const c = cv.getContext('2d', { willReadFrequently: true });
    c.font = `${font.weight} ${S}px ${font.family}`;
    if ('fontStretch' in c) c.fontStretch = font.stretch === 'condensed' ? 'condensed' : 'normal';
    c.textBaseline = 'alphabetic';
    c.fillStyle = '#000';
    const ox = pad + L, oy = pad + A;
    c.fillText(ch, ox, oy);
    const px = c.getImageData(0, 0, W, H).data;
    const N = W * H;
    /* 1 = ink, 2 = outside, 3+ = enclosed components, 0 = unvisited */
    const lab = new Int32Array(N);
    for (let i = 0; i < N; i++) lab[i] = px[i * 4 + 3] > 100 ? 1 : 0;
    const stack = new Int32Array(N);
    const fill = (seed, v) => {
      let sp = 0, area = 0;
      stack[sp++] = seed;
      lab[seed] = v;
      while (sp) {
        const p = stack[--sp];
        area++;
        const x = p % W;
        if (x > 0 && lab[p - 1] === 0) (lab[p - 1] = v), (stack[sp++] = p - 1);
        if (x < W - 1 && lab[p + 1] === 0) (lab[p + 1] = v), (stack[sp++] = p + 1);
        if (p >= W && lab[p - W] === 0) (lab[p - W] = v), (stack[sp++] = p - W);
        if (p < N - W && lab[p + W] === 0) (lab[p + W] = v), (stack[sp++] = p + W);
      }
      return area;
    };
    for (let x = 0; x < W; x++) {
      if (lab[x] === 0) fill(x, 2);
      if (lab[N - W + x] === 0) fill(N - W + x, 2);
    }
    for (let y = 0; y < H; y++) {
      if (lab[y * W] === 0) fill(y * W, 2);
      if (lab[y * W + W - 1] === 0) fill(y * W + W - 1, 2);
    }
    let next = 3;
    for (let i = 0; i < N; i++) if (lab[i] === 0) fill(i, next++);

    let res = null;
    if (next > 3) {
      const d = chamfer(W, H, (i) => lab[i] >= 3);
      let best = -1, bi = -1;
      for (let i = 0; i < N; i++) if (lab[i] >= 3 && d[i] > best) (best = d[i]), (bi = i);
      if (best >= 3) {
        const comp = lab[bi];
        /* mask: the component grown by 2px, so its soft edge always hides under the stroke */
        const mask = document.createElement('canvas');
        mask.width = W;
        mask.height = H;
        const mc = mask.getContext('2d');
        const img = mc.createImageData(W, H);
        const R2 = 2;
        for (let y = 0; y < H; y++) {
          for (let x = 0; x < W; x++) {
            if (lab[y * W + x] !== comp) continue;
            for (let dy = -R2; dy <= R2; dy++) {
              const yy = y + dy;
              if (yy < 0 || yy >= H) continue;
              for (let dx = -R2; dx <= R2; dx++) {
                const xx = x + dx;
                if (xx < 0 || xx >= W) continue;
                img.data[(yy * W + xx) * 4 + 3] = 255;
              }
            }
          }
        }
        mc.putImageData(img, 0, 0);
        res = {
          mode: 'counter',
          r: best / S,
          cx: ((bi % W) + 0.5 - ox) / S,
          cy: (((bi / W) | 0) + 0.5 - oy) / S,
          mask,
          box: { x: -ox / S, y: -oy / S, w: W / S, h: H / S },
        };
      }
    }
    if (!res) {
      /* no enclosed counter: the portal is the thickest point of the stroke itself */
      const d = chamfer(W, H, (i) => lab[i] === 1);
      let best = -1, bi = -1;
      for (let i = 0; i < N; i++) if (lab[i] === 1 && d[i] > best) (best = d[i]), (bi = i);
      res = bi < 0 ? null : { mode: 'ink', r: best / S, cx: ((bi % W) + 0.5 - ox) / S, cy: (((bi / W) | 0) + 0.5 - oy) / S, mask: null, box: null };
    }
    cache.set(key, res);
    return res;
  };

  /* Choose the portal glyph of a word. forced = glyph index among non-space glyphs, or 'auto'. */
  P.pick = function (word, font, forced) {
    const gs = K.text.graphemes(word);
    const cands = [];
    gs.forEach((ch, gi) => {
      if (/^\s+$/.test(ch)) return;
      cands.push({ gi, ch, a: P.analyze(ch, font) });
    });
    if (!cands.length) return null;
    if (forced !== 'auto' && cands[forced]) {
      const c = cands[forced];
      return c.a ? Object.assign({ index: c.gi, ch: c.ch }, c.a) : null;
    }
    let best = null;
    for (const c of cands) if (c.a && c.a.mode === 'counter' && (!best || c.a.r > best.a.r)) best = c;
    if (!best) for (const c of cands) if (c.a && (!best || c.a.r > best.a.r)) best = c;
    return best ? Object.assign({ index: best.gi, ch: best.ch }, best.a) : null;
  };

  /* which glyphs of a word have counters (for the editor's picker) */
  P.survey = function (word, font) {
    return K.text
      .graphemes(word)
      .filter((ch) => !/^\s+$/.test(ch))
      .map((ch) => {
        const a = P.analyze(ch, font);
        return { ch, counter: !!(a && a.mode === 'counter'), r: a ? a.r : 0 };
      });
  };

  /* the white mask tinted with a colour (cached per colour) */
  P.tint = function (a, color) {
    if (!a || !a.mask) return null;
    a.tints = a.tints || {};
    if (a.tints[color]) return a.tints[color];
    const cv = document.createElement('canvas');
    cv.width = a.mask.width;
    cv.height = a.mask.height;
    const c = cv.getContext('2d');
    c.drawImage(a.mask, 0, 0);
    c.globalCompositeOperation = 'source-in';
    c.fillStyle = color;
    c.fillRect(0, 0, cv.width, cv.height);
    a.tints[color] = cv;
    return cv;
  };

  P.clear = () => cache.clear();
})(typeof window !== 'undefined' ? window : globalThis);
