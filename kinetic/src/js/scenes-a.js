/* Kinetic Manifesto — scenes: assemble, stretch, split.
   Every scene is create(ctx) → { layout(), update(p, dt) }. layout() rebuilds from
   measurements; update() only writes transforms/opacity/clip for progress p ∈ [0, 1]. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const E = K.ease;
  const S = (K.scenes = K.scenes || {});

  /* build a block of glyph lines at a font size; returns { el, lines } */
  function block(lines, font, size) {
    const el = K.h('div.k-block');
    el.style.fontSize = size.toFixed(2) + 'px';
    const out = lines.map((l) => {
      const gl = K.glyphLine(l, font);
      el.appendChild(gl.el);
      return gl;
    });
    return { el, lines: out };
  }

  /* ---------- 1. assemble: glyphs fly in from a seeded scatter ---------- */
  S.assemble = {
    create(ctx) {
      let glyphs = [];
      function layout() {
        const b = ctx.box();
        const text = ctx.disp(ctx.scene.text);
        const font = K.fontFor(text);
        const fit = T.fit(text, font, b.w, b.h * 0.9, { maxLines: 3 });
        ctx.body.textContent = '';
        const bl = block(fit.lines, font, fit.size);
        ctx.body.appendChild(bl.el);
        const bh = bl.el.offsetHeight;
        const bx = b.x, by = b.y + (b.h - bh) / 2;
        bl.el.style.transform = `translate(${bx}px, ${by}px)`;
        const rng = ctx.rng();
        glyphs = [];
        bl.lines.forEach((l) => l.glyphs.forEach((g) => !g.space && glyphs.push(g)));
        const rank = [];
        rng.shuffle(glyphs.map((_, i) => i)).forEach((gi, r) => (rank[gi] = r));
        const n = Math.max(1, glyphs.length - 1);
        glyphs.forEach((g, i) => {
          const el = g.el;
          const cx = el.offsetLeft + el.offsetWidth / 2, cy = el.offsetTop + el.offsetHeight / 2;
          const X = rng.range(0.06, 0.94) * b.W, Y = rng.range(0.16, 0.84) * b.H;
          g.dx = X - (bx + cx);
          g.dy = Y - (by + cy);
          g.rot = rng.sign() * rng.range(25, 200);
          g.sc = rng.range(0.35, 1.8);
          g.start = 0.03 + 0.42 * (rank[i] / n);
          /* registration cross at the glyph's destination */
          g.mark = K.h('i.k-reg');
          g.mark.style.left = cx + 'px';
          g.mark.style.top = cy + 'px';
          bl.el.appendChild(g.mark);
        });
      }
      function update(p) {
        let landed = 0;
        for (const g of glyphs) {
          const u = E.out4(K.span(p, g.start, g.start + 0.45));
          const k = 1 - u;
          if (u >= 1) landed++;
          g.el.style.transform = k
            ? `translate(${(g.dx * k).toFixed(1)}px, ${(g.dy * k).toFixed(1)}px) rotate(${(g.rot * k).toFixed(2)}deg) scale(${(1 + (g.sc - 1) * k).toFixed(3)})`
            : '';
          g.el.style.opacity = (0.24 + 0.76 * u).toFixed(3);
          g.mark.style.opacity = (k * 0.9).toFixed(3);
        }
        ctx.read(`${K.pad(landed)} / ${K.pad(glyphs.length)} GLYPHS`);
      }
      return { layout, update };
    },
  };

  /* ---------- 2. stretch: rows widen with scaleX until they form a justified block ---------- */
  S.stretch = {
    create(ctx) {
      let rows = [], rule = null, W = 0;
      function layout() {
        const b = ctx.box();
        const text = ctx.disp(ctx.scene.text);
        const font = K.fontFor(text);
        const lines = T.rows(text, font, 4);
        const gutter = Math.max(56, Math.min(84, b.W * 0.06));
        W = b.w - gutter;
        const nat = lines.map((l) => K.meas.line(l, font).w);
        /* the widest row starts at ~60% of the measure (75% on tall screens), so every row visibly stretches */
        const start = b.h > b.w ? 0.75 : 0.58;
        const size = Math.min((b.h * 0.92) / (lines.length * font.lh), (W * start) / Math.max.apply(null, nat));
        ctx.body.textContent = '';
        const bl = block(lines, font, size);
        ctx.body.appendChild(bl.el);
        const bh = bl.el.offsetHeight;
        const by = b.y + (b.h - bh) / 2;
        bl.el.style.transform = `translate(${b.x}px, ${by}px)`;
        rows = bl.lines.map((l, i) => {
          const s = W / (nat[i] * size);
          const read = K.h('span.k-readout', { text: '×1.00' });
          read.style.left = b.x + W + 14 + 'px';
          read.style.top = by + l.el.offsetTop + l.el.offsetHeight / 2 + 'px';
          ctx.body.appendChild(read);
          return { el: l.el, s, read, i };
        });
        rule = K.h('div.k-rule-v', null, K.h('span', { text: `MEASURE ${Math.round(W)}` }));
        rule.style.left = b.x + W + 'px';
        rule.style.top = by - 18 + 'px';
        rule.style.height = bh + 36 + 'px';
        ctx.body.appendChild(rule);
      }
      function update(p) {
        let done = 0;
        for (const r of rows) {
          const a = 0.06 + r.i * 0.08;
          const u = E.inOut3(K.span(p, a, a + 0.56));
          const s = 1 + (r.s - 1) * u;
          r.el.style.transform = `scaleX(${s.toFixed(4)})`;
          r.read.textContent = '×' + s.toFixed(2);
          r.read.classList.toggle('is-live', u > 0 && u < 1);
          if (u >= 1) done++;
        }
        const hit = rows.length && done === rows.length;
        if (rule) rule.classList.toggle('is-hit', hit);
        ctx.read(hit ? `JUSTIFIED · ${rows.length} ROWS` : `MEASURE ${Math.round(W)} PX`);
      }
      return { layout, update };
    },
  };

  /* ---------- 3. split: an accent blade cuts the line; the halves part around an insert band ---------- */
  S.split = {
    create(ctx) {
      let top, bot, band, bandText, blade, bladeLine, G = 0, W = 0, cutRatio = 0;
      function layout() {
        const b = ctx.box();
        W = b.W;
        const raw = ctx.scene.text.split('\n').map((l) => l.trim()).filter(Boolean);
        const text = ctx.disp(raw.join(T.joiner(ctx.scene.text)));
        const font = K.fontFor(text);
        const m = K.meas.line(text, font);
        const size = Math.min(b.w / m.w, (b.h * 0.3) / font.lh);
        const lineH = font.lh * size;
        const ink = K.meas.ink(text, font);
        const cut = (m.b - (ink.asc - ink.desc) / 2) * size;
        cutRatio = cut / lineH;
        G = K.clamp(size * 1.1, b.H * 0.17, b.H * 0.34);
        const y0 = b.y + (b.h - lineH) / 2;
        const cutY = y0 + cut;

        ctx.body.textContent = '';
        const half = (clip) => {
          const h = K.h('div.k-half');
          const bl = block([text], font, size);
          bl.el.style.transform = `translate(${b.x}px, ${y0}px)`;
          h.appendChild(bl.el);
          h.style.clipPath = clip;
          return h;
        };
        top = half(`inset(0 0 ${b.H - cutY}px 0)`);
        bot = half(`inset(${cutY}px 0 0 0)`);

        band = K.h('div.k-band');
        band.style.top = cutY - G / 2 + 'px';
        band.style.height = G + 'px';
        const ins = ctx.disp(ctx.scene.insert || '');
        if (ins.trim()) {
          const f2 = K.fontFor(ins);
          const m2 = K.meas.line(ins, f2);
          const s2 = Math.min((b.w * 0.96) / m2.w, (G * 0.64) / f2.lh);
          const bl2 = block([ins], f2, s2);
          bl2.el.style.transform = `translate(${b.x}px, ${(G - f2.lh * s2) / 2}px)`;
          bandText = K.h('div.k-band-text', null, bl2.el);
          band.appendChild(bandText);
        } else bandText = null;

        bladeLine = K.h('i.k-blade-line');
        blade = K.h('div.k-blade', null, bladeLine, K.h('span', { text: `CUT ${cutRatio.toFixed(3)}` }));
        blade.style.top = cutY - 1 + 'px';
        ctx.body.append(band, top, bot, blade);
      }
      function update(p) {
        const bl = E.inOut3(K.span(p, 0.04, 0.3));
        const o = E.inOut3(K.span(p, 0.3, 0.84));
        const g = o * G;
        const drift = o * W * 0.012;
        bladeLine.style.transform = `scaleX(${bl.toFixed(4)})`;
        blade.style.opacity = o > 0.02 ? '0' : bl > 0 ? '1' : '0';
        top.style.transform = `translate(${-drift}px, ${(-g / 2).toFixed(2)}px)`;
        bot.style.transform = `translate(${drift}px, ${(g / 2).toFixed(2)}px)`;
        const inset = ((G - g) / 2).toFixed(2);
        band.style.clipPath = `inset(${inset}px 0 ${inset}px 0)`;
        if (bandText) bandText.style.transform = `translateY(${((1 - o) * G * 0.22).toFixed(2)}px)`;
        ctx.read(o > 0 ? `GAP ${Math.round(g)} PX` : `CUT @ ${cutRatio.toFixed(3)}`);
      }
      return { layout, update };
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
