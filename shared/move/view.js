// Browser shell: state ⇄ camera adapters.  The only code that touches the camera; three is never imported, the
// camera is used through position.set / lookAt / up.set, and the city supplies readDir(camera) → {x, y, z}
// (camera.getWorldDirection into its own THREE.Vector3).
import { AXES } from './vec.js';

// venice / kyoto / vatican: z-up, lookAt.  setUp=false keeps vatican's camera.up untouched, as before.
export function zUpView(camera, { readDir, setUp = true }) {
  const ax = AXES.zUp;
  return {
    axes: 'zUp', forward: ax.forward, right: ax.right, up: ax.up,
    readPos() { const p = camera.position; return { x: p.x, y: p.y, z: p.z }; },
    read() {
      const d = readDir(camera);
      return { pos: this.readPos(), yaw: Math.atan2(d.y, d.x), pitch: Math.asin(Math.max(-1, Math.min(1, d.z))) };
    },
    apply(s) {
      const p = s.pos, cp = Math.cos(s.pitch);
      if (setUp) camera.up.set(0, 0, 1);
      camera.position.set(p.x, p.y, p.z);
      camera.lookAt(p.x + Math.cos(s.yaw) * cp, p.y + Math.sin(s.yaw) * cp, p.z + Math.sin(s.pitch));
    },
  };
}

// alhambra: y-up, camera.rotation (pitch, yaw, 0, 'YXZ').  read() takes the angles as they stand and does not set
// rotation.order: alhambra's orientation() does, at the moments it always did.
export function alhambraView(camera) {
  return {
    axes: 'alhambra',
    readPos() { const p = camera.position; return { x: p.x, y: p.y, z: p.z }; },
    read() { return { pos: this.readPos(), yaw: camera.rotation.y, pitch: camera.rotation.x }; },
    apply(s) { camera.position.set(s.pos.x, s.pos.y, s.pos.z); camera.rotation.set(s.pitch, s.yaw, 0, 'YXZ'); },
  };
}
