// Fakes for driving the movement code in node: an EventTarget for window and the canvas, DOM-like events, and a
// camera that keeps a position and a view direction (lookAt / getWorldDirection, z-up).  The old and the new
// implementation get the same fakes, so the trace compares the movement code and not three's matrix math.
import { Vector3 } from 'three';

export class FakeTarget extends EventTarget {
  setPointerCapture() {}
  releasePointerCapture() {}
}

export function installWindow() {
  const win = new FakeTarget();
  globalThis.addEventListener = win.addEventListener.bind(win);
  globalThis.removeEventListener = win.removeEventListener.bind(win);
  return win;
}

export function event(type, props = {}) {
  const e = new Event(type, { cancelable: true });
  return Object.assign(e, props);
}

export class FakeCamera {
  constructor() { this.position = new Vector3(); this.up = new Vector3(0, 0, 1); this.dir = { x: 1, y: 0, z: 0 }; }
  lookAt(x, y, z) {
    if (typeof x === 'object') ({ x, y, z } = x);
    const p = this.position, dx = x - p.x, dy = y - p.y, dz = z - p.z, l = Math.sqrt(dx * dx + dy * dy + dz * dz);
    this.dir = { x: dx / l, y: dy / l, z: dz / l };
  }
  getWorldDirection(target) { return target.set(this.dir.x, this.dir.y, this.dir.z); }
}
