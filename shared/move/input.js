// Browser shell: keys, drag, wheel → InputFrame and Commands (proposal §3.2 InputOptions, §3.4).
// Keys are collected even while disabled; drag is ignored while disabled (and keeps its last point); the wheel
// changes the speed regardless of `enabled` unless wheel.modes limits it.
// Drag sign (owner decision ②, 2026-10-29): grab-the-scene, the same for every city — dragging right turns left
// (yaw grows), dragging down looks up.  It is a constant on purpose, not an option.
export const DRAG_SIGN = 1;

const NONE = [];
export const textField = (e) => {
  const t = e.target;
  return !!t && (t.isContentEditable === true || (typeof t.tagName === 'string' && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)));
};

export class Input {
  // hooks: { enabled(), mode(), speed(), setSpeed(v), look(dx, dy, e) → handled, wheel(e) → handled, userInput(kind) }
  // migration: { dragSign, turnPerFrame } — temporary, only so a migration commit keeps a city's old feel (§3.4)
  constructor({ win = globalThis, dom, options = {}, migration = null, hooks }) {
    const o = this.options = {
      keyField: 'code', bindings: {}, turnRate: 0, compose: 'clampEach', ignore: textField, resetOn: ['blur'],
      preventDefault: false, ...options,
      drag: { mouse: 0.003, touch: 0.005, pitchLimit: 1.5, button: null, ...options.drag },
      wheel: options.wheel === null ? null : { min: 1, max: 300, modes: ['fly'], down: 0.85, up: 1.18, ...options.wheel },
    };
    this.dragSign = migration && migration.dragSign != null ? migration.dragSign : DRAG_SIGN;
    this.turnPerFrame = migration && migration.turnPerFrame != null ? migration.turnPerFrame : null;
    this.hooks = hooks; this.win = win; this.dom = dom;
    this.keys = new Set(); this.yaw = 0; this.pitch = 0; this.drag = null;
    // written by the city's touch controls: the stick (x right, y down), ▲▼ (vert ±1), the fast toggle
    this.move = { x: 0, y: 0 }; this.vert = 0; this.fastLatch = false;
    const bound = new Set(Object.values(o.bindings).flat());
    const keyOf = (e) => (o.keyField === 'key' ? String(e.key).toLowerCase() : e.code);
    const L = this.listeners = [];
    const on = (t, type, fn, opt) => { t.addEventListener(type, fn, opt); L.push([t, type, fn, opt]); };
    on(win, 'keydown', (e) => {
      if (o.ignore && o.ignore(e)) return;
      const k = keyOf(e); this.keys.add(k);
      if (bound.has(k)) { if (o.preventDefault) e.preventDefault(); hooks.userInput && hooks.userInput('key'); }
    });
    // a key released over a text field still lifts: ignore only drops new input
    on(win, 'keyup', (e) => { this.keys.delete(keyOf(e)); });
    for (const r of o.resetOn) {
      if (r === 'blur') on(win, 'blur', () => this.reset());
      else if (r === 'hidden' && win.document) on(win.document, 'visibilitychange', () => { if (win.document.hidden) this.reset(); });
    }
    on(dom, 'pointerdown', (e) => {
      if (o.drag.button != null && e.button !== o.drag.button) return;
      if (this.drag && this.drag.id !== e.pointerId) return;
      this.drag = { id: e.pointerId, x: e.clientX, y: e.clientY };
      if (dom.setPointerCapture) dom.setPointerCapture(e.pointerId);
      hooks.userInput && hooks.userInput('pointerdown');
    });
    const end = (e) => { if (this.drag && this.drag.id === e.pointerId) this.drag = null; };
    on(dom, 'pointerup', end); on(dom, 'pointercancel', end);
    on(dom, 'pointermove', (e) => {
      const d = this.drag;
      if (!d || d.id !== e.pointerId || !hooks.enabled()) return;
      const k = e.pointerType === 'touch' ? o.drag.touch : o.drag.mouse, s = this.dragSign;
      const dx = s * (e.clientX - d.x) * k, dy = s * (e.clientY - d.y) * k;
      d.x = e.clientX; d.y = e.clientY;
      if (hooks.look && hooks.look(dx, dy, e)) return;
      // clamp per event, so a drag to the limit and back ends where it did before (§3.4 ②)
      const lim = o.drag.pitchLimit;
      this.yaw += dx; this.pitch = Math.max(-lim, Math.min(lim, this.pitch + dy));
    });
    on(dom, 'wheel', (e) => {
      if (hooks.wheel && hooks.wheel(e)) return;
      const w = o.wheel;
      if (!w) return;
      e.preventDefault();
      if (w.modes && !w.modes.includes(hooks.mode())) return;
      hooks.setSpeed(Math.max(w.min, Math.min(w.max, hooks.speed() * (e.deltaY > 0 ? w.down : w.up))));
    }, { passive: false });
  }

  any(name) { for (const k of this.options.bindings[name] || NONE) if (this.keys.has(k)) return 1; return 0; }

  // the InputFrame for one step; integrates the turn keys (rad/s, or per frame under migration.turnPerFrame)
  read(dt) {
    const a = (n) => this.any(n), turn = a('turnLeft') - a('turnRight');
    if (turn) this.yaw += turn * (this.turnPerFrame != null ? this.turnPerFrame : this.options.turnRate * dt);
    let f = a('forward') - a('back'), r = a('right') - a('left'), u = a('up') - a('down');
    f += -this.move.y; r += this.move.x; u += this.vert;
    if (this.options.compose === 'clampEach') { f = Math.max(-1, Math.min(1, f)); r = Math.max(-1, Math.min(1, r)); u = Math.max(-1, Math.min(1, u)); }
    return { f, r, u, fast: a('fast') === 1 || this.fastLatch, yaw: this.yaw, pitch: this.pitch };
  }

  reset() { this.keys.clear(); this.drag = null; }

  dispose() { for (const [t, type, fn, opt] of this.listeners) t.removeEventListener(type, fn, opt); this.listeners = []; }
}
