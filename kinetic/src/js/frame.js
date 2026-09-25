/* Kinetic Manifesto — the frame around the scenes: title card, finale zoom, closing page. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const E = K.ease;

  /* place the accent counter mask inside the portal glyph of a glyph line */
  function mountCounter(line, portal, accent) {
    if (!portal) return null;
    const g = line.glyphs[portal.index];
    if (!g) return null;
    if (portal.mode !== 'counter') {
      g.el.classList.add('is-accent');
      return null;
    }
    const src = K.portal.tint(portal, accent);
    const cv = K.h('canvas.k-counter');
    cv.width = src.width;
    cv.height = src.height;
    cv.getContext('2d').drawImage(src, 0, 0);
    Object.assign(cv.style, {
      left: portal.box.x.toFixed(4) + 'em',
      top: (line.b + portal.box.y).toFixed(4) + 'em',
      width: portal.box.w.toFixed(4) + 'em',
      height: portal.box.h.toFixed(4) + 'em',
      transformOrigin: `${(((portal.cx - portal.box.x) / portal.box.w) * 100).toFixed(2)}% ${(((portal.cy - portal.box.y) / portal.box.h) * 100).toFixed(2)}%`,
    });
    g.el.classList.add('has-counter');
    g.el.appendChild(cv);
    return cv;
  }

  /* ---------- title card ---------- */
  K.intro = {
    create(app) {
      const C = app.C, L = app.L;
      const el = K.h('section.k-intro', { id: 'k-top', 'aria-labelledby': 'k-title' });
      const grid = K.h('div.k-intro-grid', { 'aria-hidden': 'true' });
      const head = K.h(
        'div.k-intro-head',
        null,
        K.h('p.k-kicker', { text: C.intro.kicker }),
        K.h('p.k-cue', { 'aria-hidden': 'true' }, K.h('span', { text: L.scroll }), K.h('i.k-cue-arrow'))
      );
      const h1 = K.h('h1.k-sr', { id: 'k-title', text: C.meta.title });
      const wordWrap = K.h('div.k-word', { 'aria-hidden': 'true' });
      const skew = K.h('div.k-word-skew');
      wordWrap.appendChild(skew);
      const sl = C.intro.slate;
      const cell = (k, v) => K.h('div.k-slate-cell', null, K.h('dt', { text: k }), K.h('dd', { text: v || '—' }));
      const slate = K.h(
        'dl.k-slate',
        null,
        cell('PROD.', sl.prod),
        cell('ROLL', sl.roll),
        cell('SCENE', `00 / ${K.pad(app.total)}`),
        cell('TAKE', sl.take),
        cell('DATE', sl.date),
        cell('DIR.', sl.dir)
      );
      const foot = K.h('div.k-intro-foot', null, C.intro.sub ? K.h('p.k-sub', { text: C.intro.sub }) : K.h('p.k-sub'), slate);
      const tick = (C.intro.ticker || `${C.intro.word} — ${L.scroll}`).trim();
      const group = () => K.h('span.k-ticker-group', null, ...Array.from({ length: 4 }, () => K.h('span', { text: tick })));
      const ticker = K.h('div.k-ticker', { 'aria-hidden': 'true' }, K.h('div.k-ticker-track', null, group(), group()));
      el.append(grid, head, h1, wordWrap, foot, ticker);

      let line = null, counter = null, font = null;
      const sk = { v: 0, x: 0 };

      function layout() {
        const word = K.display(C.intro.word, C);
        font = K.fontFor(word);
        skew.textContent = '';
        const W = el.clientWidth;
        const m = app.margin(W);
        const avail = wordWrap.clientHeight;
        const fitRows = (rows) =>
          Math.min((W - m * 2) / Math.max.apply(null, rows.map((r) => K.meas.line(r, font).w)), (avail * 0.92) / (rows.length * font.lh));
        /* on tall screens a long word is stacked in two rows when that makes it much bigger */
        const gs = T.graphemes(word);
        let rows = [word];
        let size = fitRows(rows);
        if (gs.length >= 4 && !/\s/.test(word)) {
          const half = Math.ceil(gs.length / 2);
          const two = [gs.slice(0, half).join(''), gs.slice(half).join('')];
          const s2 = fitRows(two);
          if (s2 > size * 1.35) (rows = two), (size = s2);
        }
        const lines = rows.map((r) => K.glyphLine(r, font));
        let i = 0;
        lines.forEach((l) => {
          l.glyphs.forEach((g) => g.el.style.setProperty('--i', i++));
          skew.appendChild(l.el);
        });
        skew.style.setProperty('--n', i);
        line = lines[0];
        const portal = K.portal.pick(word, font, C.finale.portal);
        if (portal) {
          /* map the word-level glyph index onto its row */
          let idx = portal.index, r = 0;
          while (r < lines.length - 1 && idx >= lines[r].glyphs.length) idx -= lines[r++].glyphs.length;
          counter = mountCounter(lines[r], Object.assign({}, portal, { index: idx }), C.palette.accent);
        } else counter = null;
        skew.style.fontSize = size.toFixed(2) + 'px';
        const dur = Math.max(18, T.count(tick) * 4 * 0.32);
        ticker.style.setProperty('--dur', dur.toFixed(1) + 's');
      }
      /* letters rise one by one, then the counter pops in */
      function rise(instant) {
        el.classList.remove('is-risen');
        el.classList.toggle('is-instant', !!instant);
        void el.offsetWidth;
        requestAnimationFrame(() => el.classList.add('is-risen'));
      }
      /* pointer velocity skews the word; a spring brings it back */
      function update(dt, y, vh) {
        if (y > vh) return false;
        const target = K.clamp(-app.pointer.vx * 0.0045, -11, 11);
        app.pointer.vx *= Math.exp(-dt * 7);
        const k = 90, c = 13;
        const acc = k * (target - sk.x) - c * sk.v;
        sk.v += acc * dt;
        sk.x += sk.v * dt;
        skew.style.transform = Math.abs(sk.x) > 0.01 ? `skewX(${sk.x.toFixed(3)}deg)` : '';
        return Math.abs(sk.x) > 0.01 || Math.abs(sk.v) > 0.01 || Math.abs(app.pointer.vx) > 1;
      }
      return { el, layout, rise, update, get counter() { return counter; } };
    },
  };

  /* ---------- finale: zoom into the counter until it becomes the next page ---------- */
  K.scenes.finale = {
    create(ctx) {
      const C = ctx.C;
      const cv = K.h('canvas.k-zoom');
      let c2d = null, W = 0, H = 0, dpr = 1, font = null, glyphs = [], size = 0, x0 = 0, y0 = 0;
      let portal = null, C0 = { x: 0, y: 0 }, sEnd = 1, word = '';
      function layout() {
        ctx.body.textContent = '';
        ctx.body.appendChild(cv);
        const b = ctx.box();
        W = b.W;
        H = b.H;
        dpr = Math.min(2, root.devicePixelRatio || 1);
        cv.width = Math.round(W * dpr);
        cv.height = Math.round(H * dpr);
        c2d = cv.getContext('2d');
        word = K.display(C.intro.word, C);
        font = K.fontFor(word);
        const m = K.meas.line(word, font);
        glyphs = m.glyphs;
        size = Math.min(b.w / m.w, (b.h * 0.8) / font.lh);
        x0 = b.x + (b.w - m.w * size) / 2;
        y0 = b.y + (b.h - font.lh * size) / 2 + m.b * size;
        portal = K.portal.pick(word, font, C.finale.portal);
        if (portal) {
          const g = glyphs[portal.index];
          C0 = { x: x0 + (g.x + portal.cx) * size, y: y0 + portal.cy * size };
          sEnd = Math.max(2, (Math.hypot(W / 2, H / 2) / Math.max(0.5, portal.r * size)) * 1.3);
        } else {
          C0 = { x: W / 2, y: H / 2 };
          sEnd = 2;
        }
      }
      function draw(s, F, fade) {
        const c = c2d;
        const P = C.palette;
        c.setTransform(1, 0, 0, 1, 0, 0);
        c.fillStyle = P.bg;
        c.fillRect(0, 0, cv.width, cv.height);
        c.setTransform(dpr * s, 0, 0, dpr * s, dpr * (F.x - s * C0.x), dpr * (F.y - s * C0.y));
        if (portal && portal.mode === 'counter') {
          const g = glyphs[portal.index];
          const src = K.portal.tint(portal, P.accent);
          const gx = x0 + g.x * size;
          c.imageSmoothingEnabled = true;
          c.drawImage(src, gx + portal.box.x * size, y0 + portal.box.y * size, portal.box.w * size, portal.box.h * size);
        }
        c.font = `${font.weight} ${size}px ${font.family}`;
        if ('fontStretch' in c) c.fontStretch = font.stretch === 'condensed' ? 'condensed' : 'normal';
        c.textBaseline = 'alphabetic';
        glyphs.forEach((g, i) => {
          if (/^\s+$/.test(g.ch)) return;
          c.fillStyle = portal && portal.mode === 'ink' && i === portal.index ? P.accent : P.fg;
          c.fillText(g.ch, x0 + g.x * size, y0);
        });
        /* a small crosshair marks the zoom origin before the dive */
        if (fade > 0) {
          c.setTransform(dpr, 0, 0, dpr, 0, 0);
          c.globalAlpha = fade;
          c.strokeStyle = portal && portal.mode === 'counter' ? P.bg : P.fg;
          c.lineWidth = 1;
          c.beginPath();
          c.moveTo(F.x - 7, F.y);
          c.lineTo(F.x + 7, F.y);
          c.moveTo(F.x, F.y - 7);
          c.lineTo(F.x, F.y + 7);
          c.stroke();
          c.globalAlpha = 1;
        }
      }
      function update(p) {
        if (!c2d) return;
        const z = K.span(p, 0.12, 0.88);
        if (z >= 1) {
          c2d.setTransform(1, 0, 0, 1, 0, 0);
          c2d.fillStyle = C.palette.accent;
          c2d.fillRect(0, 0, cv.width, cv.height);
          ctx.state.full = true;
          ctx.stage.classList.add('is-full');
          ctx.read(`ZOOM ×${sEnd.toFixed(1)}`);
          return;
        }
        const s = Math.exp(Math.log(sEnd) * E.inOut3(z));
        const f = E.inOut3(K.span(z, 0, 0.55));
        const F = { x: K.lerp(C0.x, W / 2, f), y: K.lerp(C0.y, H / 2, f) };
        /* the accent owns the screen once the inscribed circle reaches the farthest corner */
        const far = Math.hypot(Math.max(F.x, W - F.x), Math.max(F.y, H - F.y));
        ctx.state.full = !!portal && portal.r * size * s >= far;
        ctx.stage.classList.toggle('is-full', ctx.state.full);
        const fade = z < 0.001 ? 0.9 * K.span(p, 0, 0.06) : 0.9 * (1 - K.span(z, 0, 0.2));
        draw(s, F, fade);
        const what = portal ? (portal.mode === 'counter' ? `COUNTER OF “${portal.ch}”` : `STROKE OF “${portal.ch}”`) : '';
        ctx.read(`${what} · ZOOM ×${s.toFixed(s < 10 ? 2 : 1)}`);
      }
      return { layout, update };
    },
  };

  /* ---------- closing page ---------- */
  K.closing = {
    create(app) {
      const C = app.C, L = app.L;
      const text = K.display(C.finale.text || C.intro.word, C);
      const el = K.h('section.k-closing', { id: 'k-end', 'aria-labelledby': 'k-end-h' });
      const top = K.h(
        'div.k-closing-top',
        { 'aria-hidden': 'true' },
        K.h('span', { text: `${L.end} · SC. ${K.pad(app.total)} / ${K.pad(app.total)}` }),
        K.h('span', { text: C.meta.title })
      );
      const h = K.h('h2.k-closing-word', { id: 'k-end-h' }, K.h('span.k-sr', { text: C.finale.text || C.intro.word }));
      const wordBox = K.h('span.k-closing-glyphs', { 'aria-hidden': 'true' });
      h.appendChild(wordBox);
      const gloss = C.finale.gloss ? K.h('p.k-closing-gloss', { text: C.finale.gloss }) : null;
      const list = K.h('ol.k-closing-list');
      app.statements.forEach((s, i) => {
        list.appendChild(
          K.h(
            'li',
            null,
            K.h(
              'button.k-closing-item',
              { type: 'button', 'aria-label': L.jump(i + 1, s), onclick: () => app.jump(i, 'start') },
              K.h('span.k-ci-no', { text: K.pad(i + 1) }),
              K.h('span.k-ci-text', { text: s }),
              K.h('span.k-ci-go', { 'aria-hidden': 'true', text: '↺' })
            )
          )
        );
      });
      const nav = K.h('nav.k-closing-nav', { 'aria-label': L.list }, list);
      const foot = K.h(
        'div.k-closing-foot',
        null,
        K.h('button.k-replay', { type: 'button', onclick: () => app.replay() }, K.h('span', { 'aria-hidden': 'true', text: '↑' }), K.h('span', { text: C.finale.replay })),
        K.h('p.k-colophon', { text: L.colophon(app.total) })
      );
      el.append(top, h, gloss, nav, foot);

      let line = null;
      function layout() {
        const font = K.fontFor(text);
        wordBox.textContent = '';
        line = K.glyphLine(text, font);
        line.glyphs.forEach((g, i) => g.el.style.setProperty('--i', i));
        wordBox.appendChild(line.el);
        const W = el.clientWidth, m = app.margin(W);
        const size = Math.min((W - 2 * m) / line.w, (app.vh * 0.34) / font.lh);
        wordBox.style.fontSize = size.toFixed(2) + 'px';
      }
      return { el, layout };
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
