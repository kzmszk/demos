/* RASTER — composition: where the display sits, small type hung from the grid, the rule, the imprint.
   Three plans:
   - band:   small type runs across the sheet above or below a black rule;
   - column: it stands in a column beside the display (3 of 12 columns, or a 2-of-6 rail on a phone);
   - tate:   the Japanese title stands upright down the right edge, the rest in a band. */
(function (R) {
  'use strict';

  const INK = R.INK;

  R.motifOf = (edition) => R.MOTIFS[Math.floor(R.rng(edition).next() * R.MOTIFS.length)];

  function choosePlan(rng) {
    const kind = rng.pick(['band', 'band', 'column', 'tate']);
    const sub = rng.pick([0, 0, 1]);
    if (kind === 'column') return { kind, side: sub ? 'left' : 'right' };
    return { kind, at: sub ? 'top' : 'bottom' };
  }

  /* Split `cols` columns into tracks for the band. */
  function bandTracks(G, cols) {
    if (G.landscape) {
      const base = Math.floor(cols / 4);
      const extra = cols - base * 4;
      const w = [0, 1, 2, 3].map((i) => base + (i < extra ? 1 : 0));
      const at = w.map((_, i) => w.slice(0, i).reduce((a, b) => a + b, 0));
      return [
        { c0: at[0], nc: w[0], top: ['headline'], foot: ['mark'] },
        { c0: at[1], nc: w[1], top: ['date'], foot: ['info'] },
        { c0: at[2], nc: w[2], top: ['bodyJa'], foot: [] },
        { c0: at[3], nc: w[3], top: ['bodyEn'], foot: [] },
      ];
    }
    const a = Math.ceil(cols / 2);
    return [
      { c0: 0, nc: a, top: ['headline', 'bodyJa'], foot: ['mark'] },
      { c0: a, nc: cols - a, top: ['date', 'bodyEn'], foot: ['info'] },
    ];
  }

  const filled = (s) => typeof s === 'string' && s.trim().length > 0;

  function block(name, w, G, S, P) {
    const L = S * 1.6;
    const small = { wt: 400, size: S };
    const runs = (texts, f, extra) => texts.filter(filled).map((t, i) => Object.assign({ lines: R.wrap(t, f, w), f, gap: i ? S * 0.9 : 0 }, extra));
    switch (name) {
      case 'headline':
        return R.flow([
          ...runs([P.tate ? '' : P.title.ja], { wt: 700, size: L }, { lead: 1.3 }),
          ...runs([P.title.en], { wt: 400, size: L }, { lead: 1.14, gap: L * 0.2 }),
        ]);
      case 'date': {
        const ko = P.panel;
        const pad = ko ? Math.round(G.g * 0.7) : 0;
        const inner = w - 2 * pad;
        const ink = ko ? INK.white : INK.red;
        const big = { wt: 700, size: L };
        const fl = R.flow([
          { lines: [P.date.ja, P.time.ja].filter(filled).flatMap((t) => R.wrap(t, big, inner)), f: big, lead: 1.3, fill: ink },
          { lines: R.wrap([P.date.en, P.time.en].filter(filled).join(', '), small, inner), f: small, lead: 1.3, gap: S * 0.5, fill: ink },
        ]);
        if (!ko) return fl;
        const h = fl.h + 2 * pad;
        return { h, draw(p, x, top) { R.rect(x, top, w, h, INK.red, p); fl.draw(p, x + pad, top + pad); } };
      }
      case 'bodyJa':
      case 'bodyEn': {
        const txt = name === 'bodyJa' ? P.body.ja : P.body.en;
        if (!filled(txt)) return { h: 0, draw() {} };
        const hair = Math.max(1, S * 0.09);
        const fl = R.flow(runs([txt], small));
        const off = S * 0.85;
        return { h: fl.h + off, draw(p, x, top) { R.rect(x, top, w, hair, INK.black, p); fl.draw(p, x, top + off); } };
      }
      case 'info': {
        const f = { wt: 700, size: Math.max(8, S * 0.78), ls: 0.1 };
        const ja = [P.kicker.ja, P.venue.ja, P.price.ja].filter(filled).join(' · ');
        const en = [P.venue.en, P.price.en].filter(filled).join(' · ').toUpperCase();
        return R.flow(runs([ja, en], f, { lead: 1.55 }).map((r, i) => Object.assign(r, { gap: i ? f.size * 0.3 : 0 })));
      }
      case 'mark':
        return R.flow([{ lines: ['No. ' + P.no], f: { wt: 700, size: L * 1.2 }, lead: 1 }]);
    }
  }

  /* Top blocks hang from row lines; foot blocks stack up from the zone's bottom edge. */
  function planTrack(tr, T, G, S, P) {
    const x = G.x(tr.c0);
    const w = G.w(tr.nc);
    const lines = [];
    for (let r = 0; r < T.nr; r++) lines.push(G.y(T.r0 + r));
    const bottom = T.y + T.h;
    const placed = [];
    let cursor = T.y;
    for (const name of tr.top) {
      const b = block(name, w, G, S, P);
      if (!b.h) continue;
      const top = lines.find((l) => l >= cursor - 0.01);
      if (top == null) return { ok: false };
      placed.push([b, top]);
      cursor = top + b.h + S * 1.2;
    }
    const foot = tr.foot.map((n) => block(n, w, G, S, P)).filter((b) => b.h);
    const gap = S * 1.1;
    let y = bottom - foot.reduce((s, b) => s + b.h, 0) - gap * Math.max(0, foot.length - 1);
    if (y < cursor - S * 0.2) return { ok: false };
    for (const b of foot) { placed.push([b, y]); y += b.h + gap; }
    return { ok: true, draw: (parent) => placed.forEach(([b, top]) => b.draw(parent, x, top)) };
  }

  /* The title set upright: as large as a column allows, broken into at most two vertical lines. */
  function tateTitle(G, title) {
    if (!R.hasCJK(title || '')) return null;
    const Ht = G.H - 2 * G.m;
    let f;
    let lines;
    for (let s = G.cw * 0.92; ; s *= 0.93) {
      f = { wt: 700, size: s, ls: 0.04, vertical: true };
      lines = R.wrap(title.trim(), f, Ht);
      if (lines.length <= 2 || s < G.S * 1.8) break;
    }
    return { f, lines: lines.slice(0, 2) };
  }

  function layoutText(G, plan, P, cols) {
    const rail = G.landscape ? 3 : 2;
    const railC0 = plan.side === 'left' ? 0 : G.C - rail;
    const trs = plan.kind === 'column'
      ? [{ c0: railC0, nc: rail, top: ['headline', 'date'], foot: ['bodyJa', 'bodyEn', 'info', 'mark'] }]
      : bandTracks(G, cols);
    const minRows = plan.kind === 'column' ? G.rows : G.landscape ? 2 : 3;
    const maxRows = plan.kind === 'column' ? G.rows : Math.max(minRows, Math.floor(G.rows * 0.55));
    const zoneFor = (n) => {
      if (plan.kind === 'column') return G.zone(railC0, 0, rail, G.rows);
      return plan.at === 'bottom' ? G.zone(0, G.rows - n, cols, n) : G.zone(0, 0, cols, n);
    };
    for (const s of [1, 0.92, 0.85, 0.78, 0.72, 0.66, 0.6]) {
      for (let n = minRows; n <= maxRows; n++) {
        const T = zoneFor(n);
        const plans = trs.map((tr) => planTrack(tr, T, G, G.S * s, P));
        if (plans.every((p) => p.ok)) return { T, plans, scale: s, rail };
      }
    }
    return { T: zoneFor(maxRows), plans: [], scale: 0, rail };
  }

  function displayZone(G, plan, T, cols, rail) {
    if (plan.kind === 'column') return plan.side === 'left' ? G.zone(rail, 0, G.C - rail, G.rows) : G.zone(0, 0, G.C - rail, G.rows);
    return plan.at === 'bottom' ? G.zone(0, 0, cols, G.rows - T.nr) : G.zone(0, T.nr, cols, G.rows - T.nr);
  }

  /* The display bleeds off every sheet edge it touches, except the margin holding the imprint. */
  function bleed(D, G, capSide) {
    const x0 = D.c0 === 0 && capSide !== 'left' ? 0 : D.x;
    const x1 = D.c0 + D.nc === G.C && capSide !== 'right' ? G.W : D.x + D.w;
    const y0 = D.r0 === 0 ? 0 : D.y;
    const y1 = D.r0 + D.nr === G.rows ? G.H : D.y + D.h;
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }

  /* The imprint climbs a margin or the gutter beside the column, in red. */
  function imprint(parent, G, x, text) {
    const f = { wt: 700, size: Math.max(7, G.S * 0.62), ls: 0.14 };
    const avail = G.H - 2 * G.m;
    const w = R.textWidth(text, f);
    if (w > avail) f.size *= avail / w;
    const t = R.text(parent, text, 0, 0, f, INK.red);
    t.setAttribute('transform', `translate(${(x + R.cap(f.size) / 2).toFixed(1)} ${G.H - G.m}) rotate(-90)`);
  }

  function gridOverlay(parent, G) {
    const g = R.el('g', { class: 'grid-overlay', fill: 'none', stroke: INK.red, 'stroke-width': 1, 'aria-hidden': 'true' }, parent);
    for (let c = 0; c < G.C; c++) {
      for (let r = 0; r < G.rows; r++) {
        R.el('rect', { x: G.x(c) + 0.5, y: G.y(r) + 0.5, width: G.cw - 1, height: G.rh - 1 }, g);
      }
    }
  }

  /* doc: the viewer's own content, or null to set this edition's sample. */
  R.compose = function (svg, edition, W, H, doc) {
    const G = R.grid(W, H);
    const rng = R.rng(edition);
    const motif = R.MOTIFS[Math.floor(rng.next() * R.MOTIFS.length)];
    let plan = choosePlan(rng);
    const sidePick = rng.pick(['left', 'right']);
    /* Content draws from its own stream, so the same edition reads the same at any sheet size. */
    const crng = R.rng(edition + 10007);
    const sample = R.sample(motif, crng);
    const P = R.programme(doc || sample, sample, motif, crng, edition, !!doc);

    const tate = plan.kind === 'tate' ? tateTitle(G, P.title.ja) : null;
    if (plan.kind === 'tate' && !tate) plan = { kind: 'band', at: plan.at };
    P.tate = !!tate;
    const nt = tate ? tate.lines.length : 0;
    const cols = G.C - nt;
    const capSide = plan.kind === 'column' ? null : tate ? 'left' : sidePick;

    const text = layoutText(G, plan, P, cols);
    const T = text.T;
    const D = displayZone(G, plan, T, cols, text.rail);
    const B = bleed(D, G, capSide);

    svg.textContent = '';
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const title = R.el('title', { id: 'poster-title' }, svg);
    title.textContent = `ポスター No. ${P.no}：${P.title.ja || P.title.en}、${P.date.short}（${R.MOTIF_INFO[motif].name}）`;
    const defs = R.el('defs', {}, svg);
    const clip = R.el('clipPath', { id: 'rs-bleed' }, defs);
    R.el('rect', { x: B.x, y: B.y, width: B.w, height: B.h }, clip);
    R.el('rect', { width: W, height: H, fill: INK.paper }, svg);

    const art = R.el('g', { class: 'art' }, svg);
    R.motifs[motif]({ g: R.el('g', { 'clip-path': 'url(#rs-bleed)' }, art), D, B, G, rng, P, defs, plan });

    const type = R.el('g', { class: 'type' }, art);
    if (plan.kind !== 'column') {
      const y = plan.at === 'bottom' ? T.y - G.g / 2 : T.y + T.h + G.g / 2;
      const th = Math.max(2, G.g * 0.2);
      R.rect(G.m, y - th / 2, tate ? G.w(cols) : G.W - 2 * G.m, th, INK.black, type);
    }
    text.plans.forEach((p) => p.draw(type));

    if (tate) {
      tate.lines.forEach((line, i) => {
        const c = G.C - 1 - i;
        R.text(type, line, G.x(c) + G.cw / 2, G.m, tate.f, INK.black);
      });
    }

    const ix = plan.kind === 'column'
      ? (plan.side === 'left' ? G.x(text.rail) - G.g / 2 : G.x(G.C - text.rail) - G.g / 2)
      : (capSide === 'left' ? G.m / 2 : G.W - G.m / 2);
    imprint(art, G, ix, P.caption);
    gridOverlay(svg, G);
    return { G, motif, plan, D, T, P, scale: text.scale, doc: doc || sample };
  };
})((window.RASTER = window.RASTER || {}));
