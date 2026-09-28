// The little there is of an interface: a sound switch, and hints written in the same hand as the book.
import { writeText } from './layout.js';
import { PX, makeCanvas, planStroke, drawDabs } from './media.js';
import { hashStr } from './rng.js';

const HINTS = {
  open: 'タップしてひらく',
  turn: 'めくる →',
  draw: 'ここは、あなたのページ',
};

function handImage(text, size) {
  const ops = writeText(text, { x: 2, y: 2, size, medium: 'ink', tidy: 0.8, seed: hashStr(text) });
  const w = Math.ceil((ops.box.w + 6) * PX), h = Math.ceil((ops.box.h + 6) * PX);
  const c = makeCanvas(w, h);
  const g = c.getContext('2d');
  ops.forEach((op, i) => { const pl = planStroke({ ...op, w: op.w * 1.3 }, i * 31 + 7); drawDabs(g, { ...op, color: [242, 232, 212] }, pl, 0, pl.dabs.length / 5); });
  return c;
}

export function makeUI(live) {
  const ov = document.createElement('canvas');
  ov.setAttribute('aria-hidden', 'true');
  Object.assign(ov.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', pointerEvents: 'none' });
  document.body.appendChild(ov);
  const g = ov.getContext('2d');
  const imgs = {};
  let current = 'open', shownAt = 0, alpha = 0;
  // sound switch
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.setAttribute('aria-label', '音を消す');
  btn.setAttribute('aria-pressed', 'false');
  Object.assign(btn.style, { position: 'fixed', top: '14px', right: '14px', width: '44px', height: '44px', border: '0', borderRadius: '22px', background: 'rgba(20,16,12,0.35)', color: '#e8dcc6', cursor: 'pointer', padding: '10px' });
  const svgOn = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5c1.6 1.8 1.6 5.2 0 7"/><path d="M19 6c2.9 3.2 2.9 8.8 0 12"/></svg>';
  const svgOff = '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M17 9l5 6M22 9l-5 6"/></svg>';
  btn.innerHTML = svgOn;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const a = live.ensureAudio();
    if (!a) return;
    a.setMuted(!a.muted);
    btn.innerHTML = a.muted ? svgOff : svgOn;
    btn.setAttribute('aria-pressed', String(a.muted));
    btn.setAttribute('aria-label', a.muted ? '音を出す' : '音を消す');
  });
  btn.addEventListener('pointerdown', (e) => e.stopPropagation());
  document.body.appendChild(btn);
  const style = document.createElement('style');
  style.textContent = 'button:focus-visible{outline:2px solid #e8dcc6;outline-offset:3px}';
  document.head.appendChild(style);
  return {
    resize() {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      ov.width = Math.round(window.innerWidth * dpr); ov.height = Math.round(window.innerHeight * dpr);
    },
    hint(kind) { if (kind !== current) { current = kind; shownAt = live.t; } },
    draw(t) {
      g.clearRect(0, 0, ov.width, ov.height);
      const want = current && t - shownAt > (current === 'open' ? 1.2 : 1.6) ? 1 : 0;
      alpha += (want - alpha) * 0.06;
      if (!current || alpha < 0.01) return;
      const img = imgs[current] || (imgs[current] = handImage(HINTS[current], 5));
      // about 24 CSS px tall glyphs, whatever the screen
      const dpr = ov.width / window.innerWidth;
      const scale = (24 * dpr) / (5 * 7);
      const w = img.width * scale, h = img.height * scale;
      let x = (ov.width - w) / 2, y = ov.height * 0.86 - h / 2;
      if (current === 'turn') { x = ov.width * 0.78 - w / 2; y = ov.height * 0.9 - h / 2; }
      g.globalAlpha = alpha * (0.86 + 0.14 * Math.sin(t * 1.6));
      g.drawImage(img, x, y, w, h);
      g.globalAlpha = 1;
    },
  };
}
