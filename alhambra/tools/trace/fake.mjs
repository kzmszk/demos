// Fakes for driving the movement glue in node: EventTargets for window, document, the canvas and the touch controls,
// and DOM-like events.  The camera is a real three PerspectiveCamera (rotation order, lookAt and the quaternion are
// part of what is traced).
export class FakeTarget extends EventTarget {
  constructor(props = {}) { super(); this.focused = 0; this.style = {}; Object.assign(this, props); }
  setPointerCapture() {}
  releasePointerCapture() {}
  focus() { this.focused++; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 48, height: 48 }; }
  set onpointerdown(fn) { this.addEventListener('pointerdown', fn); }
}

// target can be given (e.g. { tagName: 'INPUT' }): dispatchEvent cannot set it, so it is an own property
export function event(type, props = {}) {
  const e = new Event(type, { cancelable: true });
  const { target, ...rest } = props;
  if (target) Object.defineProperty(e, 'target', { value: target });
  return Object.assign(e, rest);
}

export function makeEnv() {
  const win = new FakeTarget(), doc = new FakeTarget({ hidden: false });
  win.document = doc;
  const env = {
    win, doc, canvas: new FakeTarget(), joy: new FakeTarget({ firstElementChild: { style: {} } }),
    rise: new FakeTarget(), descend: new FakeTarget(),
    dialogs: { help: false, references: false }, ms: 0, now: () => env.ms,
  };
  return env;
}
