/* RASTER — export: the sheet as SVG, or redrawn onto a canvas as a high-resolution PNG.
   The canvas path uses the page's loaded fonts, so Japanese sets exactly as on screen. */
(function (R) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';

  R.exportSVG = function (svg, W, H) {
    const c = svg.cloneNode(true);
    c.querySelectorAll('.grid-overlay').forEach((n) => n.remove());
    ['id', 'role', 'aria-labelledby'].forEach((a) => c.removeAttribute(a));
    c.setAttribute('xmlns', NS);
    c.setAttribute('width', W);
    c.setAttribute('height', H);
    const style = document.createElementNS(NS, 'style');
    style.textContent = `.ink{mix-blend-mode:${R.INK.blend}}`;
    c.insertBefore(style, c.firstChild);
    const xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(c);
    return new Blob([xml], { type: 'image/svg+xml' });
  };

  /* ---------- a small SVG-to-canvas painter for the elements the composer emits ---------- */
  function applyTransform(ctx, tf) {
    if (!tf) return;
    const re = /(translate|rotate)\(([^)]*)\)/g;
    let m;
    while ((m = re.exec(tf))) {
      const v = m[2].split(/[\s,]+/).filter(Boolean).map(Number);
      if (m[1] === 'translate') ctx.translate(v[0], v[1] || 0);
      else {
        const a = (v[0] * Math.PI) / 180;
        if (v.length === 3) { ctx.translate(v[1], v[2]); ctx.rotate(a); ctx.translate(-v[1], -v[2]); }
        else ctx.rotate(a);
      }
    }
  }

  function clipTo(ctx, svg, ref) {
    const id = /url\(#([^)]+)\)/.exec(ref);
    const cp = id && svg.querySelector(`[id="${id[1]}"]`);
    if (!cp) return;
    ctx.beginPath();
    cp.querySelectorAll('rect').forEach((r) => {
      ctx.rect(+r.getAttribute('x') || 0, +r.getAttribute('y') || 0, +r.getAttribute('width'), +r.getAttribute('height'));
    });
    ctx.clip();
  }

  const TURN = /[ー〜～—…「」『』（）【】〔〕〈〉《》()[\]]/;
  const COMMA = /[、。，．]/;

  function drawText(ctx, el, fill) {
    const st = el.style;
    const size = parseFloat(st.fontSize);
    const lsRaw = st.letterSpacing && st.letterSpacing !== 'normal' ? st.letterSpacing : '0';
    const ls = parseFloat(lsRaw) * (lsRaw.endsWith('em') ? size : 1);
    const x = +el.getAttribute('x') || 0;
    const y = +el.getAttribute('y') || 0;
    const str = el.textContent;
    ctx.font = `${st.fontWeight || 400} ${size}px ${st.fontFamily}`;
    ctx.fillStyle = fill;
    const spaced = 'letterSpacing' in ctx;
    if (!(st.writingMode || '').startsWith('vertical')) {
      if (spaced) ctx.letterSpacing = `${ls}px`;
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(str, x, y);
      return;
    }
    /* vertical-rl: glyphs centred on x, advancing down from y */
    if (spaced) ctx.letterSpacing = '0px';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    let yy = y;
    for (const ch of str) {
      const cjk = R.hasCJK(ch);
      const adv = cjk ? size : ctx.measureText(ch).width;
      const cy = yy + adv / 2;
      ctx.save();
      if (TURN.test(ch) || !cjk) { ctx.translate(x, cy); ctx.rotate(Math.PI / 2); ctx.fillText(ch, 0, 0); }
      else if (COMMA.test(ch)) ctx.fillText(ch, x + size * 0.6, cy - size * 0.6);
      else ctx.fillText(ch, x, cy);
      ctx.restore();
      yy += adv + ls;
    }
  }

  function paint(ctx, svg, el) {
    const tag = el.tagName;
    if (tag === 'title' || tag === 'defs' || tag === 'clipPath' || tag === 'style' || el.classList.contains('grid-overlay')) return;
    ctx.save();
    applyTransform(ctx, el.getAttribute('transform'));
    const cp = el.getAttribute('clip-path');
    if (cp) clipTo(ctx, svg, cp);
    ctx.globalCompositeOperation = el.classList.contains('ink') ? R.INK.blend : 'source-over';
    const fill = el.getAttribute('fill');
    const stroke = el.getAttribute('stroke');
    const shape = (p) => {
      if (fill && fill !== 'none') { ctx.fillStyle = fill; ctx.fill(p); }
      if (stroke && stroke !== 'none') {
        ctx.strokeStyle = stroke;
        ctx.lineWidth = +el.getAttribute('stroke-width') || 1;
        ctx.lineCap = el.getAttribute('stroke-linecap') || 'butt';
        ctx.stroke(p);
      }
    };
    const n = (a) => +el.getAttribute(a) || 0;
    if (tag === 'g') for (const ch of el.children) paint(ctx, svg, ch);
    else if (tag === 'rect') { const p = new Path2D(); p.rect(n('x'), n('y'), n('width'), n('height')); shape(p); }
    else if (tag === 'circle') { const p = new Path2D(); p.arc(n('cx'), n('cy'), n('r'), 0, Math.PI * 2); shape(p); }
    else if (tag === 'path') shape(new Path2D(el.getAttribute('d')));
    else if (tag === 'text') drawText(ctx, el, fill);
    ctx.restore();
  }

  R.exportPNG = function (svg, W, H) {
    const k = Math.max(2, Math.min(4, 3200 / Math.max(W, H)));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(W * k);
    canvas.height = Math.round(H * k);
    const ctx = canvas.getContext('2d');
    ctx.scale(k, k);
    for (const ch of svg.children) paint(ctx, svg, ch);
    return new Promise((resolve, reject) => canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('png'))), 'image/png'));
  };

  /* ---------- handing the file over ----------
     Inside a claude.ai viewer the page asks the `downloads` capability (the viewer confirms);
     opened as a plain page it downloads directly. null = this view cannot save: hide the controls. */
  let ns;
  R.downloads = function () {
    if (ns === undefined) {
      const c = window.claude;
      ns = c && typeof c.use === 'function' ? c.use('downloads').catch(() => null) : Promise.resolve(false);
    }
    return ns;
  };

  R.offer = async function (filename, blob) {
    const dl = await R.downloads();
    if (dl) return (await dl.save({ filename, data: blob })).status;
    if (dl === null) throw Object.assign(new Error('unavailable'), { code: 'unavailable' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    return 'saved';
  };
})((window.RASTER = window.RASTER || {}));
