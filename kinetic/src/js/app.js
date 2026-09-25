/* Kinetic Manifesto — runtime: builds the page from content, maps scroll to scene
   progress, runs the frame loop, header, progress rail, keys, motion toggle. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const doc = document, html = doc.documentElement;

  const app = (K.app = {
    C: null,
    L: null,
    total: 0,
    statements: [],
    vh: 0,
    closingTop: 0,
    pointer: { x: 0, y: 0, t: 0, vx: 0, nx: 0, ny: 0, fine: false },
    state: { motion: true, dev: false, draft: false, editing: false },
  });

  let rootEl = null, vhProbe = null, hud = null, rail = null, railSegs = [];
  let intro = null, closing = null, insts = [], io = null, closeIO = null;
  let raf = 0, lastT = 0, current = -2, playAnim = 0, layoutTimer = 0, lastW = 0, lastVH = 0, pendingRise = false;
  const H = {}; /* header parts */
  const listeners = {};

  app.on = (ev, fn) => (listeners[ev] = listeners[ev] || []).push(fn);
  const emit = (ev, arg) => (listeners[ev] || []).forEach((fn) => fn(arg));

  app.margin = (W) => K.clamp(W * 0.055, 18, 96);
  app.canEdit = () => !!(app.state.dev || (app.C && app.C.options.editable));

  /* ---------- document-level state from content ---------- */
  function setMeta(name, content) {
    let m = doc.querySelector(`meta[name="${name}"]`);
    if (!m) {
      m = doc.createElement('meta');
      m.setAttribute('name', name);
      doc.head.appendChild(m);
    }
    m.setAttribute('content', content);
  }
  function applyDocument() {
    const C = app.C;
    html.lang = C.lang;
    doc.title = C.meta.title;
    setMeta('description', C.meta.description);
    setMeta('theme-color', C.palette.bg);
    const st = html.style;
    st.setProperty('--bg', C.palette.bg);
    st.setProperty('--fg', C.palette.fg);
    st.setProperty('--accent', C.palette.accent);
    st.setProperty('--f-lat', K.FONTS.lat.family);
    st.setProperty('--f-ja', K.FONTS.ja.family);
    st.setProperty('--f-mono', K.FONTS.mono);
    st.setProperty('--f-ui', K.FONTS.ui);
    const light = K.luminance(C.palette.bg) > 0.36;
    html.classList.toggle('k-light', light);
    st.colorScheme = light ? 'light' : 'dark';
  }

  /* ---------- header ---------- */
  function buildHud() {
    H.word = K.h('span.k-hud-word');
    H.mark = K.h('a.k-hud-mark', { href: '#k-top' }, K.h('i.k-sq', { 'aria-hidden': 'true' }), H.word);
    H.mark.addEventListener('click', (e) => {
      e.preventDefault();
      app.top();
    });
    H.sc = K.h('span.k-hud-sc');
    H.tc = K.h('span.k-hud-tc');
    H.draft = K.h('button.k-btn.k-hud-draft', { type: 'button', hidden: true, onclick: () => K.editor && K.editor.open() });
    H.motion = K.h('button.k-btn.k-hud-motion', { type: 'button', onclick: () => app.setMotion(!app.state.motion, true) });
    H.edit = K.h('button.k-btn.k-hud-edit', { type: 'button', onclick: () => K.editor && K.editor.toggle() });
    hud = K.h(
      'header.k-hud',
      null,
      H.mark,
      K.h('div.k-hud-mid', { 'aria-hidden': 'true' }, H.sc, H.tc),
      K.h('div.k-hud-actions', null, H.draft, H.motion, H.edit)
    );
    doc.body.insertBefore(hud, doc.body.firstChild);
  }
  function refreshHud() {
    const L = app.L;
    H.word.textContent = K.display(app.C.intro.word, app.C);
    H.mark.setAttribute('aria-label', app.C.meta.title);
    H.motion.textContent = app.state.motion ? L.motionOn : L.motionOff;
    H.motion.setAttribute('aria-pressed', String(app.state.motion));
    H.motion.setAttribute('title', L.motionAria + ' (M)');
    H.edit.textContent = L.edit;
    H.edit.hidden = !app.canEdit();
    H.edit.setAttribute('aria-pressed', String(app.state.editing));
    H.edit.setAttribute('title', L.edit + ' (E)');
    H.draft.textContent = L.draft;
    H.draft.hidden = !app.state.draft;
    H.draft.setAttribute('aria-label', L.draftAria);
  }
  app.setDraft = function (on) {
    app.state.draft = !!on;
    refreshHud();
  };
  app.setEditing = function (on) {
    app.state.editing = !!on;
    html.classList.toggle('k-editing', !!on);
    refreshHud();
  };

  /* ---------- rail ---------- */
  function buildRail() {
    if (rail) rail.remove();
    const ol = K.h('ol');
    railSegs = app.statements.map((s, i) => {
      const fill = K.h('i.k-rail-fill');
      const b = K.h(
        'button.k-rail-seg',
        { type: 'button', 'aria-label': app.L.jump(i + 1, s), onclick: () => app.jump(i, 'start') },
        K.h('span.k-rail-no', { 'aria-hidden': 'true', text: K.pad(i + 1) }),
        K.h('span.k-rail-track', { 'aria-hidden': 'true' }, fill),
        K.h('span.k-rail-tip', { 'aria-hidden': 'true', text: s })
      );
      ol.appendChild(K.h('li', null, b));
      return b;
    });
    rail = K.h('nav.k-rail', { 'aria-label': app.L.rail }, ol);
    doc.body.appendChild(rail);
  }

  /* ---------- scenes ---------- */
  function stageBox(stage) {
    const W = stage.clientWidth, Hh = stage.clientHeight;
    const m = app.margin(W);
    const top = Math.max(64, Hh * 0.11), bottom = Math.max(88, Hh * 0.14);
    return { W, H: Hh, m, x: m, y: top, w: W - 2 * m, h: Math.max(80, Hh - top - bottom) };
  }

  function makeScene(scene, i) {
    const info = scene.type === 'finale' ? K.FINALE : K.TYPES[scene.type];
    const n = i + 1;
    const sec = K.h('section.k-scene', { id: 'k-sc-' + n, 'data-type': scene.type, 'aria-labelledby': 'k-sc-h-' + n });
    sec.style.setProperty('--len', info.len);
    const stage = K.h('div.k-stage');
    const ghost = K.h('div.k-ghost', { 'aria-hidden': 'true', text: K.pad(n) });
    const body = K.h('div.k-body', { 'aria-hidden': 'true' });
    const read = K.h('span.k-ann-read');
    const tEl = K.h('span.k-ann-t', { text: 't = 0.000' });
    const ann = K.h(
      'div.k-ann',
      { 'aria-hidden': 'true' },
      K.h(
        'p.k-ann-l',
        null,
        K.h('span.k-ann-sc', { text: `SC. ${K.pad(n)} / ${K.pad(app.total)}` }),
        K.h('span.k-ann-code', { text: info.code }),
        scene.gloss ? K.h('span.k-ann-gloss', { text: scene.gloss }) : null
      ),
      K.h('p.k-ann-r', null, read, tEl)
    );
    stage.append(ghost, body, ann);
    sec.append(K.h('h2.k-sr', { id: 'k-sc-h-' + n, text: app.statements[i] }), stage);
    rootEl.appendChild(sec);
    const inst = { i, sec, stage, ghost, tEl, read, len: info.len, q: -1, drawn: -1, top: 0, h: 0, state: {}, finale: scene.type === 'finale' };
    const ctx = {
      C: app.C,
      scene,
      index: i,
      total: app.total,
      body,
      stage,
      state: inst.state,
      pointer: app.pointer,
      disp: (s) => K.display(s, app.C),
      rng: () => K.rng(K.hash(scene.type + '|' + scene.text + '|' + i)),
      box: () => stageBox(stage),
      read: (s) => {
        if (read.textContent !== s) read.textContent = s;
      },
    };
    inst.impl = K.scenes[scene.type].create(ctx);
    return inst;
  }

  function build() {
    rootEl.textContent = '';
    rootEl.classList.remove('k-fallback');
    insts = [];
    intro = K.intro.create(app);
    rootEl.appendChild(intro.el);
    const C = app.C;
    C.scenes.concat([{ type: 'finale', text: C.finale.text, gloss: C.finale.gloss }]).forEach((s, i) => insts.push(makeScene(s, i)));
    closing = K.closing.create(app);
    rootEl.appendChild(closing.el);
    buildRail();
    refreshHud();
    observe();
  }

  function measure() {
    const y = root.scrollY;
    for (const inst of insts) {
      inst.top = inst.sec.getBoundingClientRect().top + y;
      inst.h = inst.sec.offsetHeight;
    }
    app.closingTop = closing.el.getBoundingClientRect().top + y;
  }

  function layoutAll() {
    app.vh = vhProbe.clientHeight || root.innerHeight;
    lastW = rootEl.clientWidth;
    lastVH = app.vh;
    intro.layout();
    for (const inst of insts) {
      inst.impl.layout();
      inst.q = -1;
      inst.drawn = -1;
    }
    closing.layout();
    measure();
  }

  /* ---------- fades in static mode, closing-word rise in motion mode ---------- */
  function observe() {
    if (io) io.disconnect();
    if (closeIO) closeIO.disconnect();
    const hasIO = 'IntersectionObserver' in root;
    if (!app.state.motion && hasIO) {
      io = new IntersectionObserver(
        (es) =>
          es.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add('is-in');
              io.unobserve(e.target);
            }
          }),
        { threshold: 0.18 }
      );
      insts.forEach((inst) => io.observe(inst.stage));
    } else insts.forEach((inst) => inst.stage.classList.add('is-in'));
    if (hasIO) {
      closeIO = new IntersectionObserver((es) => es.forEach((e) => closing.el.classList.toggle('is-risen', e.isIntersecting)), { threshold: 0.25 });
      closeIO.observe(closing.el);
    } else closing.el.classList.add('is-risen');
  }

  /* ---------- frame loop ---------- */
  function wake() {
    if (!raf) raf = root.requestAnimationFrame(frame);
  }
  app.wake = wake;

  function frame(t) {
    raf = 0;
    const dt = lastT ? K.clamp((t - lastT) / 1000, 0.001, 0.05) : 0.016;
    lastT = t;
    const y = root.scrollY, vh = app.vh;
    const motion = app.state.motion;
    const k = 1 - Math.exp(-dt * 16);
    let busy = false;
    for (const inst of insts) {
      const span = Math.max(1, inst.h - vh);
      const target = motion ? K.clamp((y - inst.top) / span) : inst.finale ? 0 : 1;
      const near = y + vh > inst.top - vh * 0.3 && y < inst.top + inst.h + vh * 0.3;
      if (!near || inst.q < 0) inst.q = target;
      else {
        inst.q += (target - inst.q) * k;
        if (Math.abs(target - inst.q) < 0.0004) inst.q = target;
        else busy = true;
      }
      if (inst.q !== inst.drawn || (near && inst.impl.live)) {
        if (inst.impl.update(inst.q, dt) && near) busy = true;
        if (inst.q !== inst.drawn) {
          inst.drawn = inst.q;
          inst.tEl.textContent = 't = ' + inst.q.toFixed(3);
          inst.ghost.style.transform = motion ? `translateY(${((0.5 - inst.q) * vh * 0.16).toFixed(1)}px)` : '';
        }
      }
      if (railSegs[inst.i]) railSegs[inst.i].style.setProperty('--p', K.clamp((y - inst.top) / span).toFixed(3));
    }
    if (intro.update(dt, y, vh)) busy = true;
    if (pendingRise && y < 4) {
      pendingRise = false;
      intro.rise();
    }
    hudTick(y, vh);
    if (busy) wake();
    else lastT = 0;
  }

  function hudTick(y, vh) {
    H.tc.textContent = 'TC ' + K.timecode(y / Math.max(1, vh));
    let cur = -1;
    for (const inst of insts) if (y >= inst.top - vh * 0.5 && y < inst.top + inst.h - vh * 0.5) cur = inst.i;
    if (y >= app.closingTop - vh * 0.5) cur = insts.length;
    if (cur !== current) {
      current = cur;
      const shown = cur < 0 ? 0 : Math.min(cur + 1, app.total);
      H.sc.textContent = `SC. ${K.pad(shown)} / ${K.pad(app.total)}`;
      railSegs.forEach((s, i) => {
        s.classList.toggle('is-current', i === cur);
        if (i === cur) s.setAttribute('aria-current', 'step');
        else s.removeAttribute('aria-current');
      });
      emit('scene', cur);
    }
    const fin = insts[insts.length - 1];
    const onAccent = y + 30 >= app.closingTop || (fin && fin.state.full && y >= fin.top && y < fin.top + fin.h);
    html.classList.toggle('k-on-accent', !!onAccent);
  }

  /* ---------- navigation ---------- */
  function cancelPlay() {
    if (playAnim) root.cancelAnimationFrame(playAnim);
    playAnim = 0;
  }
  const smoothOK = () => app.state.motion && !K.prefersReducedMotion();

  app.position = function () {
    const y = root.scrollY, vh = app.vh;
    if (!insts.length || y < insts[0].top) return { i: -1, p: y / Math.max(1, vh) };
    for (const inst of insts) if (y < inst.top + inst.h) return { i: inst.i, p: K.clamp((y - inst.top) / Math.max(1, inst.h - vh)) };
    return { i: 'end', p: 0 };
  };
  app.seek = function (pos) {
    if (!pos) return;
    let y;
    if (pos.i === -1) y = pos.p * app.vh;
    else if (pos.i === 'end') y = app.closingTop;
    else {
      const inst = insts[Math.min(pos.i, insts.length - 1)];
      y = app.state.motion ? inst.top + pos.p * Math.max(1, inst.h - app.vh) : inst.top;
    }
    root.scrollTo({ top: y, behavior: 'auto' });
    insts.forEach((x) => (x.q = -1));
    wake();
  };
  app.jump = function (i, where, opts) {
    const inst = insts[i];
    if (!inst) return;
    cancelPlay();
    let y = inst.top;
    if (app.state.motion) y = where === 'end' ? inst.top + (inst.h - app.vh) * 0.985 : inst.top + 1;
    const smooth = !(opts && opts.instant) && smoothOK();
    root.scrollTo({ top: y, behavior: smooth ? 'smooth' : 'auto' });
    if (!smooth) insts.forEach((x) => (x.q = -1));
    wake();
  };
  /* scrub through one scene from start to end (editor preview) */
  app.play = function (i) {
    const inst = insts[i];
    if (!inst) return;
    if (!app.state.motion) return app.jump(i, 'end');
    cancelPlay();
    const y0 = inst.top + 1, y1 = inst.top + (inst.h - app.vh) * 0.99;
    root.scrollTo({ top: y0, behavior: 'auto' });
    insts.forEach((x) => (x.q = -1));
    const dur = 1150 * inst.len, t0 = performance.now();
    const step = (t) => {
      const u = Math.min(1, (t - t0) / dur);
      root.scrollTo({ top: y0 + (y1 - y0) * K.ease.inOut2(u), behavior: 'auto' });
      playAnim = u < 1 ? root.requestAnimationFrame(step) : 0;
    };
    playAnim = root.requestAnimationFrame(step);
  };
  app.top = function () {
    cancelPlay();
    pendingRise = true;
    root.scrollTo({ top: 0, behavior: smoothOK() ? 'smooth' : 'auto' });
    wake();
  };
  app.replay = app.top;

  app.setMotion = function (on, persist) {
    const pos = app.position();
    app.state.motion = !!on;
    if (persist) K.store.set('kinetic:motion', !!on);
    html.classList.toggle('k-static', !on);
    refreshHud();
    layoutAll();
    observe();
    app.seek(pos);
  };

  /* ---------- render ---------- */
  app.render = function (content, opts) {
    const keep = opts && opts.keep && insts.length ? app.position() : null;
    app.C = K.normalize(content);
    app.L = K.LABELS[app.C.lang];
    app.total = app.C.scenes.length + 1;
    app.statements = app.C.scenes.map((s) => T.plain(s)).concat([app.C.finale.text || app.C.intro.word]);
    current = -2;
    applyDocument();
    build();
    layoutAll();
    if (keep) app.seek(keep);
    wake();
    emit('render', app.C);
  };

  function relayout() {
    K.meas.clear();
    if (K.portal.clear) K.portal.clear();
    if (!app.C) return;
    const pos = app.position();
    layoutAll();
    app.seek(pos);
  }

  function setup() {
    rootEl = doc.getElementById('k-root');
    if (!rootEl) {
      rootEl = K.h('main', { id: 'k-root' });
      doc.body.appendChild(rootEl);
    }
    rootEl.id = 'k-root';
    vhProbe = K.h('div.k-vh-probe', { 'aria-hidden': 'true' });
    doc.body.appendChild(vhProbe);
    buildHud();

    root.addEventListener('scroll', wake, { passive: true });
    root.addEventListener(
      'pointermove',
      (e) => {
        const P = app.pointer, now = performance.now();
        if (P.t && now - P.t < 120) P.vx = K.lerp(P.vx, ((e.clientX - P.x) / Math.max(8, now - P.t)) * 1000, 0.5);
        P.x = e.clientX;
        P.y = e.clientY;
        P.t = now;
        P.nx = (e.clientX / root.innerWidth) * 2 - 1;
        P.ny = (e.clientY / root.innerHeight) * 2 - 1;
        P.fine = e.pointerType !== 'touch';
        wake();
      },
      { passive: true }
    );
    ['wheel', 'touchstart'].forEach((ev) => root.addEventListener(ev, cancelPlay, { passive: true }));
    const schedule = () => {
      clearTimeout(layoutTimer);
      layoutTimer = setTimeout(() => {
        if (!app.C) return;
        const w = rootEl.clientWidth, vh = vhProbe.clientHeight;
        if (w === lastW && Math.abs(vh - lastVH) < 2) {
          measure();
          wake();
          return;
        }
        const pos = app.position();
        layoutAll();
        app.seek(pos);
      }, 140);
    };
    root.addEventListener('resize', schedule);
    if ('ResizeObserver' in root) new ResizeObserver(schedule).observe(rootEl);
    if (doc.fonts) {
      if (doc.fonts.addEventListener) doc.fonts.addEventListener('loadingdone', relayout);
    }
    root.addEventListener('keydown', (e) => {
      if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      cancelPlay();
      if (/^[1-9]$/.test(e.key)) {
        const n = +e.key;
        if (n <= insts.length) {
          e.preventDefault();
          app.jump(n - 1, 'start');
        }
      } else if (e.key === '0') {
        e.preventDefault();
        app.top();
      } else if (e.key === 'm' || e.key === 'M') {
        app.setMotion(!app.state.motion, true);
      } else if ((e.key === 'e' || e.key === 'E') && app.canEdit() && K.editor) {
        e.preventDefault();
        K.editor.toggle();
      }
    });
  }

  /* ---------- start ---------- */
  app.start = function (raw, opts) {
    opts = opts || {};
    app.state.dev = !!opts.dev;
    app.source = K.normalize(raw);
    app.draftKey = 'kinetic:draft:' + (opts.key || location.pathname);
    const mp = K.store.get('kinetic:motion');
    app.state.motion = mp == null ? !K.prefersReducedMotion() : !!mp;
    html.classList.toggle('k-static', !app.state.motion);
    let content = app.source;
    const editable = app.state.dev || app.source.options.editable;
    const d = editable ? K.store.get(app.draftKey) : null;
    if (d && d.content) {
      content = d.content;
      app.state.draft = true;
    }
    setup();
    app.render(content);
    intro.rise(!app.state.motion || K.prefersReducedMotion());
    if (location.hash === '#edit' && app.canEdit() && K.editor) K.editor.open();
    html.classList.add('k-ready');
  };

  /* standalone pages carry their content inline */
  K.boot = function () {
    const node = doc.getElementById('k-content');
    if (!node) return false;
    let raw = {};
    try {
      raw = JSON.parse(node.textContent);
    } catch (e) {
      raw = {};
    }
    app.start(raw);
    return true;
  };
})(typeof window !== 'undefined' ? window : globalThis);
