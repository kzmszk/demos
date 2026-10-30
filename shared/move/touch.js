// Browser shell: the phone's movement controls, the same in every city.  A stick bottom left (walk, fly, rowing), and
// ▲▼ bottom right in the modes that fly.  Pushing the stick out past its ring runs (the fast key), so there is no
// extra button for it.  They write the Mover's touch inputs (move, vert, fastLatch) and show only on touch screens.
//
//   const touch = new TouchControls(controls, { root: uiElement, altitude: ['fly'], labels: { up: '上昇', down: '下降' } });
//   touch.setMode(app.mode);                      // whenever the mode changes ('title' / a tour hides everything)
//
// Placement and colour come from CSS variables on the root (or any ancestor), so each city keeps its look:
//   --tc-bottom   distance from the bottom of the screen (above the city's bar)      default 66px + safe area
//   --tc-line / --tc-pad / --tc-knob / --tc-bg / --tc-ink / --tc-on        ring, inside the ring, knob, button fill, glyph, pressed
const CSS = `
.tc { position: fixed; inset: auto 0 0 0; height: 0; pointer-events: none; z-index: 2; }
.tc[hidden] { display: none; }
.tc-stick { position: absolute; left: 20px; bottom: var(--tc-bottom, calc(66px + env(safe-area-inset-bottom))); width: 110px; height: 110px;
  border-radius: 50%; border: 1px solid var(--tc-line, rgba(246, 241, 231, .28)); background: var(--tc-pad, rgba(13, 15, 18, .16));
  pointer-events: auto; touch-action: none; }
.tc-stick i { position: absolute; left: 39px; top: 39px; width: 32px; height: 32px; border-radius: 50%; background: var(--tc-knob, rgba(246, 241, 231, .4));
  transition: background .15s, box-shadow .15s; }
.tc-stick.run i { background: var(--tc-ink, #f6f1e7); box-shadow: 0 0 0 6px var(--tc-on, rgba(246, 241, 231, .2)); }
.tc-alt { position: absolute; right: 18px; bottom: var(--tc-bottom, calc(66px + env(safe-area-inset-bottom))); display: flex; flex-direction: column; gap: 14px;
  pointer-events: auto; }
.tc-alt[hidden] { display: none; }
.tc-alt button { width: 56px; height: 56px; border-radius: 50%; border: 1px solid var(--tc-line, rgba(246, 241, 231, .28)); background: var(--tc-bg, rgba(13, 15, 18, .35));
  color: var(--tc-ink, #f6f1e7); font: 18px/1 system-ui, sans-serif; padding: 0; touch-action: none; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none; }
.tc-alt button.on { background: var(--tc-on, rgba(246, 241, 231, .28)); }
/* a phone on its side: little height, so a smaller stick and ▲▼ side by side */
@media (max-height: 500px) {
  .tc-stick { width: 92px; height: 92px; left: max(16px, env(safe-area-inset-left)); }
  .tc-stick i { left: 30px; top: 30px; }
  .tc-alt { flex-direction: row; right: max(16px, env(safe-area-inset-right)); gap: 12px; }
  .tc-alt button { width: 50px; height: 50px; }
}`;

const RANGE = 45;          // px from the centre for a full push (110 px ring)
const RUN = 1.3;           // a finger this far out (× RANGE), past the ring, runs
const KNOB = 34;           // how far the knob follows (px)

export class TouchControls {
  constructor(mover, { root = document.body, altitude = ['fly'], stick = null, labels = {}, onInput = null, force = false } = {}) {
    this.mover = mover; this.altitude = altitude; this.stickModes = stick; this.onInput = onInput;
    this.on = force || matchMedia('(pointer: coarse)').matches;
    if (!document.getElementById('tc-css')) { const s = document.createElement('style'); s.id = 'tc-css'; s.textContent = CSS; document.head.appendChild(s); }
    const el = this.el = document.createElement('div'); el.className = 'tc'; el.hidden = true;
    el.innerHTML = '<div class="tc-stick"><i></i></div><div class="tc-alt" hidden><button class="tc-up">▲</button><button class="tc-down">▼</button></div>';
    root.appendChild(el);
    this.stick = el.querySelector('.tc-stick'); this.alt = el.querySelector('.tc-alt');
    this.setLabels(labels);
    const knob = this.stick.querySelector('i');
    let id = null;
    const set = (e) => {
      const r = this.stick.getBoundingClientRect(), k = r.width / 110;
      let x = (e.clientX - r.left - r.width / 2) / (RANGE * k), y = (e.clientY - r.top - r.height / 2) / (RANGE * k);
      const l = Math.hypot(x, y), run = l > RUN;
      if (l > 1) { x /= l; y /= l; }
      mover.move.x = x; mover.move.y = y; mover.fastLatch = run;
      this.stick.classList.toggle('run', run);
      knob.style.transform = `translate(${x * KNOB * k}px, ${y * KNOB * k}px)`;
    };
    const end = () => { id = null; mover.move.x = mover.move.y = 0; mover.fastLatch = false; this.stick.classList.remove('run'); knob.style.transform = ''; };
    this.stick.addEventListener('pointerdown', (e) => {
      e.preventDefault(); e.stopPropagation(); id = e.pointerId;
      try { this.stick.setPointerCapture(id); } catch (_) { /* no capture */ }
      if (this.onInput) this.onInput('stick');
      set(e);
    });
    this.stick.addEventListener('pointermove', (e) => { if (e.pointerId === id) set(e); });
    for (const t of ['pointerup', 'pointercancel', 'lostpointercapture']) this.stick.addEventListener(t, (e) => { if (e.pointerId === id) end(); });
    const hold = (b, v) => {
      const off = () => { b.classList.remove('on'); if (mover.vert === v) mover.vert = 0; };
      b.addEventListener('pointerdown', (e) => {
        e.preventDefault(); e.stopPropagation();
        try { b.setPointerCapture(e.pointerId); } catch (_) { /* no capture */ }
        if (this.onInput) this.onInput('altitude');
        b.classList.add('on'); mover.vert = v;
      });
      for (const t of ['pointerup', 'pointercancel', 'lostpointercapture']) b.addEventListener(t, off);
      b.addEventListener('contextmenu', (e) => e.preventDefault());
    };
    hold(el.querySelector('.tc-up'), 1); hold(el.querySelector('.tc-down'), -1);
    this.release = () => { end(); mover.vert = 0; el.querySelectorAll('.tc-alt button').forEach((b) => b.classList.remove('on')); };
    addEventListener('blur', this.release);
    document.addEventListener('visibilitychange', () => { if (document.hidden) this.release(); });
  }
  setLabels({ up, down } = {}) {
    if (up) this.el.querySelector('.tc-up').setAttribute('aria-label', up);
    if (down) this.el.querySelector('.tc-down').setAttribute('aria-label', down);
  }
  // shows what the mode moves with; null / 'title' / any mode with neither hides the lot
  setMode(mode) {
    const stick = !!mode && (this.stickModes ? this.stickModes.includes(mode) : mode !== 'title');
    const alt = !!mode && this.altitude.includes(mode);
    if (!alt && this.mover.vert) this.release();
    this.alt.hidden = !alt;
    this.stick.style.display = stick ? '' : 'none';
    this.el.hidden = !this.on || (!stick && !alt);
  }
}
