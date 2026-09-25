/* Kinetic Manifesto — scenes: cascade, prism, type. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const E = K.ease;
  const S = (K.scenes = K.scenes || {});

  /* ---------- 4. cascade: glyphs stand up from the floor like dominoes ---------- */
  S.cascade = {
    create(ctx) {
      let glyphs = [];
      function layout() {
        const b = ctx.box();
        const text = ctx.disp(ctx.scene.text);
        const font = K.fontFor(text);
        const fit = T.fit(text, font, b.w, b.h * 0.8, { maxLines: 3 });
        ctx.body.textContent = '';
        const el = K.h('div.k-block.k-cascade');
        el.style.fontSize = fit.size.toFixed(2) + 'px';
        glyphs = [];
        fit.lines.forEach((l) => {
          const gl = K.glyphLine(l, font);
          el.appendChild(gl.el);
          /* the floor is the ink bottom (below descenders and the ideographic em box) */
          const fl = gl.b + Math.max(0, K.meas.ink(l, font).desc);
          const floor = K.h('i.k-floor');
          floor.style.top = fl.toFixed(4) + 'em';
          floor.style.width = gl.w + 'em';
          gl.el.appendChild(floor);
          gl.glyphs.forEach((g) => {
            if (g.space) return;
            g.el.style.transformOrigin = `50% ${fl.toFixed(4)}em`;
            g.tick = K.h('i.k-tick');
            g.tick.style.left = (g.x + g.adv * 0.25).toFixed(4) + 'em';
            g.tick.style.width = (g.adv * 0.5).toFixed(4) + 'em';
            g.tick.style.top = (fl + 0.035).toFixed(4) + 'em';
            gl.el.appendChild(g.tick);
            glyphs.push(g);
          });
        });
        ctx.body.appendChild(el);
        const bh = el.offsetHeight;
        el.style.transform = `translate(${b.x}px, ${b.y + (b.h - bh) / 2}px)`;
        const n = Math.max(1, glyphs.length - 1);
        glyphs.forEach((g, i) => (g.start = 0.04 + 0.6 * (i / n)));
      }
      function update(p) {
        let up = 0;
        for (const g of glyphs) {
          const u = K.span(p, g.start, g.start + 0.3);
          const ang = 90 * (1 - E.spring(u));
          if (u >= 1) up++;
          g.el.style.transform = ang ? `rotateX(${ang.toFixed(2)}deg)` : '';
          g.el.style.opacity = (0.2 + 0.8 * Math.min(1, u * 2.2)).toFixed(3);
          g.tick.style.transform = `scaleX(${E.out3(K.span(u, 0.34, 0.7)).toFixed(3)})`;
        }
        ctx.read(`${K.pad(up)} / ${K.pad(glyphs.length)} STANDING`);
      }
      return { layout, update };
    },
  };

  /* ---------- 5. prism: a solid n-gon turning face by face ---------- */
  S.prism = {
    create(ctx) {
      let faces = [], prism, tilt, caption = [], n = 0, step = 0, apo = 0;
      const tl = { x: 0, y: 0 };
      function layout() {
        const b = ctx.box();
        const text = ctx.disp(ctx.scene.text);
        const font0 = K.fontFor(text);
        let words = T.rows(text, font0, 4);
        if (words.length < 2) words = [words[0] || '', ''];
        n = words.length;
        step = 360 / n;
        const capH = 34;
        const Wf = b.w;
        const Hf = Math.min(b.h * (b.h > b.w ? 0.4 : 0.5), Wf * (b.h > b.w ? 0.52 : 0.36));
        apo = n === 2 ? 0.5 : Hf / (2 * Math.tan(Math.PI / n));
        ctx.body.textContent = '';
        const wrap = K.h('div.k-prism-wrap');
        Object.assign(wrap.style, {
          left: b.x + 'px',
          top: b.y + (b.h - Hf - capH) / 2 + 'px',
          width: Wf + 'px',
          height: Hf + 'px',
          perspective: Hf * 6 + 'px',
        });
        tilt = K.h('div.k-prism-tilt');
        prism = K.h('div.k-prism');
        faces = words.map((w, i) => {
          const face = K.h('div.k-face' + (i % 2 ? '.is-accent' : ''));
          /* each next face waits underneath, so scrolling down rolls the prism upward */
          face.style.transform = `rotateX(${-i * step}deg) translateZ(${apo.toFixed(2)}px)`;
          const pad = Math.max(14, Hf * 0.12);
          if (w) {
            const f = K.fontFor(w);
            const m = K.meas.line(w, f);
            const size = Math.min((Wf - pad * 2) / m.w, (Hf * 0.7) / f.lh);
            const inner = K.h('div.k-block');
            inner.style.fontSize = size.toFixed(2) + 'px';
            inner.appendChild(K.glyphLine(w, f).el);
            inner.style.transform = `translate(${pad}px, ${(Hf - f.lh * size) / 2}px)`;
            face.appendChild(inner);
          }
          face.appendChild(K.h('span.k-face-no', { text: `${K.pad(i + 1)} / ${K.pad(n)}` }));
          const shade = K.h('i.k-shade');
          face.appendChild(shade);
          prism.appendChild(face);
          return { face, shade, i };
        });
        tilt.appendChild(prism);
        wrap.appendChild(tilt);
        const cap = K.h('p.k-prism-cap');
        cap.style.top = Hf * 1.12 + 22 + 'px';
        caption = words.map((w, i) => {
          const s = K.h('span', { text: w || '—' });
          cap.appendChild(s);
          if (i < n - 1) cap.appendChild(document.createTextNode(' / '));
          return s;
        });
        wrap.appendChild(cap);
        ctx.body.appendChild(wrap);
      }
      function update(p, dt) {
        const t = K.span(p, 0.05, 0.9);
        const u = t * (n - 1);
        const k = Math.min(Math.floor(u), n - 2);
        const f = u - k;
        const ang = step * (k + E.inOut3(K.span(f, 0.28, 0.92)));
        prism.style.transform = `translateZ(${(-apo).toFixed(2)}px) rotateX(${ang.toFixed(3)}deg)`;
        for (const fc of faces) {
          const rel = ((fc.i * step - ang) * Math.PI) / 180;
          fc.shade.style.opacity = K.clamp((1 - Math.cos(rel)) * 0.85, 0, 0.92).toFixed(3);
        }
        const active = Math.round(ang / step) % n;
        caption.forEach((s, i) => s.classList.toggle('is-on', i === active));
        /* pointer tilt, eased; keeps asking for frames until it settles */
        const P = ctx.pointer;
        const tx = P.fine ? P.nx * 7 : 0, ty = P.fine ? -P.ny * 5 : 0;
        const a = 1 - Math.exp(-(dt || 0.016) * 6);
        tl.x += (tx - tl.x) * a;
        tl.y += (ty - tl.y) * a;
        tilt.style.transform = `rotateY(${tl.x.toFixed(3)}deg) rotateX(${tl.y.toFixed(3)}deg)`;
        ctx.read(`FACE ${K.pad(active + 1)} / ${K.pad(n)} · ${Math.round(ang)}°`);
        return Math.abs(tx - tl.x) > 0.02 || Math.abs(ty - tl.y) > 0.02;
      }
      return { layout, update, live: true };
    },
  };

  /* ---------- 6. type: typed with a caret, a struck-out mistake, and IME conversion ---------- */
  const PUNCT = /[、。，．,.!！?？:：;；]/;
  function timeline(tokens) {
    const ev = [];
    let misLen = 0;
    const closeMistake = () => {
      if (!misLen) return;
      ev.push({ op: 'pause', w: 2.2 }, { op: 'strike', w: 2.6 }, { op: 'pause', w: 1.2 });
      for (let i = 0; i < misLen; i++) ev.push({ op: 'bs', w: 0.42 });
      ev.push({ op: 'pause', w: 1.2 });
      misLen = 0;
    };
    tokens.forEach((t) => {
      if (!t.mis) closeMistake();
      const into = t.mis ? 'm' : 'a';
      if (t.k === 'text') {
        for (const ch of T.graphemes(t.s)) {
          ev.push({ op: 'type', ch, into, w: /\s/.test(ch) ? 0.55 : 1 });
          if (t.mis) misLen++;
          if (PUNCT.test(ch)) ev.push({ op: 'pause', w: 1.3 });
        }
      } else {
        for (const ch of T.graphemes(t.reading)) ev.push({ op: 'comp', ch, w: 1 });
        ev.push({ op: 'conv', base: t.base, w: 1.7 }, { op: 'commit', into, w: 0.7 });
        if (t.mis) misLen += T.graphemes(t.base).length;
      }
    });
    closeMistake();
    /* snapshots: the state after each event */
    const st = { a: '', m: '', c: '', conv: false, strike: 0, keys: 0, dels: 0 };
    const snaps = [Object.assign({}, st)];
    for (const e of ev) {
      if (e.op === 'type') {
        st[e.into] += e.ch;
        st.keys++;
      } else if (e.op === 'comp') {
        st.c += e.ch;
        st.conv = false;
        st.keys++;
      } else if (e.op === 'conv') {
        st.c = e.base;
        st.conv = true;
        st.keys++;
      } else if (e.op === 'commit') {
        st[e.into] += st.c;
        st.c = '';
        st.conv = false;
        st.keys++;
      } else if (e.op === 'strike') {
        st.strike = 1;
      } else if (e.op === 'bs') {
        const g = T.graphemes(st.m);
        g.pop();
        st.m = g.join('');
        st.dels++;
        if (!st.m) st.strike = 0;
      }
      snaps.push(Object.assign({}, st));
    }
    let acc = 0;
    const ends = ev.map((e) => (acc += e.w));
    return { ev, snaps, ends, total: acc };
  }

  S.type = {
    create(ctx) {
      let tl = null, box, sA, sM, sC, caret, last = -2, idleTimer = 0;
      /* committed text is set as unbreakable phrase spans, so lines only wrap between phrases */
      function phrased(el, text) {
        if (el._text === text) return;
        el._text = text;
        el.textContent = '';
        for (const c of T.chunks(text)) el.appendChild(/^\s+$/.test(c) ? document.createTextNode(c) : K.h('span.k-ph', { text: c }));
      }
      function fill(el, s) {
        phrased(el.querySelector('.k-t-a'), s.a);
        const m = el.querySelector('.k-t-m');
        m.textContent = s.m;
        m.style.setProperty('--strike', s.strike);
        const c = el.querySelector('.k-t-c');
        c.textContent = s.c;
        c.className = 'k-t-c' + (s.conv ? ' is-conv' : s.c ? ' is-comp' : '');
      }
      function make(font) {
        return K.h(
          'p.k-typed.' + font.cls,
          { lang: T.hasJa(ctx.scene.text) ? 'ja' : 'en' },
          K.h('span.k-t-a'),
          K.h('span.k-t-m'),
          K.h('span.k-t-c'),
          K.h('span.k-caret')
        );
      }
      function layout() {
        const b = ctx.box();
        const parsed = T.parseTyping(ctx.disp(ctx.scene.text));
        tl = timeline(parsed.tokens);
        const final = tl.snaps[tl.snaps.length - 1];
        /* the longest intermediate state must fit as well as the final one */
        let peak = final;
        for (const s of tl.snaps) if ((s.a + s.m + s.c).length > (peak.a + peak.m + peak.c).length) peak = s;
        const font = K.fontFor(final.a || peak.a + peak.m);
        const W = b.w * 0.94, H = b.h * 0.9;
        const probe = make(font);
        probe.style.width = W + 'px';
        probe.style.lineHeight = font.lh;
        probe.classList.add('is-probe');
        ctx.body.textContent = '';
        ctx.body.appendChild(probe);
        const fits = (size) => {
          probe.style.fontSize = size + 'px';
          for (const s of [final, peak]) {
            fill(probe, s);
            if (probe.scrollHeight > H || probe.scrollWidth > W + 1) return false;
          }
          return true;
        };
        let lo = 10, hi = Math.min(b.h * 0.6, 420);
        for (let i = 0; i < 14; i++) {
          const mid = (lo + hi) / 2;
          if (fits(mid)) lo = mid;
          else hi = mid;
        }
        fill(probe, final);
        probe.style.fontSize = lo + 'px';
        const fh = probe.offsetHeight;
        probe.remove();
        box = make(font);
        Object.assign(box.style, {
          width: W + 'px',
          fontSize: lo.toFixed(2) + 'px',
          lineHeight: String(font.lh),
          transform: `translate(${b.x}px, ${b.y + Math.max(0, (b.h - fh) / 2)}px)`,
        });
        ctx.body.appendChild(box);
        last = -2;
      }
      function update(p) {
        if (!tl) return;
        const x = K.span(p, 0.03, 0.9) * tl.total;
        let i = 0;
        while (i < tl.ends.length && tl.ends[i] <= x) i++;
        /* i events are complete; a strike in progress draws partially */
        const s = Object.assign({}, tl.snaps[i]);
        const e = tl.ev[i];
        if (e && e.op === 'strike') {
          const st = i ? tl.ends[i - 1] : 0;
          s.strike = E.inOut2(K.clamp((x - st) / e.w));
        }
        const key = i + ':' + s.strike.toFixed(3);
        if (key !== last) {
          fill(box, s);
          last = key;
          box.classList.remove('is-idle');
          clearTimeout(idleTimer);
          idleTimer = setTimeout(() => box && box.classList.add('is-idle'), 520);
        }
        ctx.read(`KEYS ${K.pad(s.keys, 3)} · DEL ${K.pad(s.dels, 3)}`);
      }
      return { layout, update };
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
