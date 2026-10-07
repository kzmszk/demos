// Camera modes:  walk (WASD on the walk map: streets, steps, slopes, bridges; eye 1.6 m; Shift runs) and
// fly (free: drag to look, WASD, E/Q up/down, Shift fast, wheel = speed; never below the ground).
import * as THREE from 'three/webgpu';
// R: the walker's radius (kept small: the walk map's cells are 0.5 m and a narrow aisle must stay passable);
// UP / DOWN: the highest step up and the deepest step down taken in one stride
const EYE = 1.6, R = 0.12, UP = 0.75, DOWN = 1.2;
export class Controls {
  constructor(camera, dom, o = {}) {
    this.camera = camera; this.dom = dom; this.tiles = o.tiles; this.ground = o.ground;
    this.yaw = 0; this.pitch = 0; this.vel = new THREE.Vector3(); this.keys = new Set(); this.speed = 30; this.enabled = true;
    this.mode = 'walk'; this.walkZ = null; this.bob = 0;
    this.move = { x: 0, y: 0 };
    this.vert = 0; this.fastLatch = false;          // touch: ▲ ▼ held (climb / descend), the fast toggle
    this.syncFromCamera();
    let drag = null;
    dom.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, id: e.pointerId }; dom.setPointerCapture(e.pointerId); });
    dom.addEventListener('pointerup', () => { drag = null; });
    dom.addEventListener('pointercancel', () => { drag = null; });
    dom.addEventListener('pointermove', (e) => {
      if (!drag || !this.enabled || e.pointerId !== drag.id) return;
      const k = e.pointerType === 'touch' ? 0.005 : 0.003;
      this.yaw -= (e.clientX - drag.x) * k; this.pitch = Math.max(-1.5, Math.min(1.5, this.pitch - (e.clientY - drag.y) * k));
      drag.x = e.clientX; drag.y = e.clientY;
    });
    addEventListener('keydown', (e) => { if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) return; this.keys.add(e.code); });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    dom.addEventListener('wheel', (e) => { if (this.mode === 'fly') this.speed = Math.max(2, Math.min(600, this.speed * (e.deltaY > 0 ? 0.85 : 1.18))); e.preventDefault(); }, { passive: false });
  }
  syncFromCamera() {
    const d = new THREE.Vector3(); this.camera.getWorldDirection(d);
    this.yaw = Math.atan2(d.y, d.x); this.pitch = Math.asin(Math.max(-1, Math.min(1, d.z)));
  }
  setMode(m) {
    this.mode = m; this.vel.set(0, 0, 0);
    if (m === 'walk') { this.walkZ = null; this.pitch = Math.max(-0.6, Math.min(0.6, this.pitch)); }
  }
  axes() {
    const k = this.keys; let f = 0, r = 0, u = 0;
    if (k.has('KeyW') || k.has('ArrowUp')) f += 1;
    if (k.has('KeyS') || k.has('ArrowDown')) f -= 1;
    if (k.has('KeyD')) r += 1;
    if (k.has('KeyA')) r -= 1;
    if (k.has('ArrowRight')) this.yaw -= 0.025;
    if (k.has('ArrowLeft')) this.yaw += 0.025;
    if (k.has('KeyE') || k.has('Space')) u += 1;
    if (k.has('KeyQ') || k.has('KeyC')) u -= 1;
    f += -this.move.y; r += this.move.x; u = Math.max(-1, Math.min(1, u + this.vert));
    return { f: Math.max(-1, Math.min(1, f)), r: Math.max(-1, Math.min(1, r)), u, fast: k.has('ShiftLeft') || k.has('ShiftRight') || this.fastLatch };
  }
  // ground under a walker standing at z0: the walk map's height, or null where blocked / too high a step
  at(x, y, z0, through = false) {
    const w = this.tiles.sample(x, y);
    if (w.z === undefined) return undefined;
    if ((w.blocked && !through) || w.z - z0 > UP || z0 - w.z > DOWN) return null;
    return w.z;
  }
  free(x, y, z0, through = false) { return this.cost(x, y, z0, through) === 0; }
  // how many of the walker's edge points stand on blocked ground (Infinity: its centre does)
  cost(x, y, z0, through = false) {
    let n = 0;
    for (const [ox, oy] of [[0, 0], [R, 0], [-R, 0], [0, R], [0, -R]]) {
      if (this.at(x + ox, y + oy, z0, through) == null) { if (!ox && !oy) return Infinity; n++; }
    }
    return n;
  }
  // a stride is fine when it ends on open ground; pressed to a wall, any stride but one toward a blocked side (the
  // walker slides along it or turns away instead of freezing)
  can(x0, y0, x, y, z0, through) {
    const c = this.cost(x, y, z0, through);
    if (c === 0) return true;
    if (c === Infinity) return false;
    for (const [ox, oy] of [[R, 0], [-R, 0], [0, R], [0, -R]]) {
      if (this.at(x + ox, y + oy, z0, through) == null && (x - x0) * ox + (y - y0) * oy > 0) return false;
    }
    return true;
  }
  findWalkable(x, y) {
    if (this.tiles.sample(x, y).z === undefined) return null;
    for (let r = 0; r < 60; r += 0.5) for (let a = 0; a < 6.283; a += 0.35 / Math.max(1, r)) {
      const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r; const w = this.tiles.sample(px, py);
      if (w.z != null && !w.blocked && this.free(px, py, w.z)) return [px, py, w.z];
    }
    return null;
  }
  update(dt) {
    if (!this.enabled) return;
    const cam = this.camera, a = this.axes();
    const f = new THREE.Vector3(Math.cos(this.yaw), Math.sin(this.yaw), 0), r = new THREE.Vector3(Math.sin(this.yaw), -Math.cos(this.yaw), 0);
    if (this.mode === 'walk') {
      const p = cam.position;
      if (this.walkZ === null) {
        const w = this.findWalkable(p.x, p.y);
        if (!w) return;
        p.set(w[0], w[1], w[2] + EYE); this.walkZ = w[2];
      }
      const sp = a.fast ? 4.2 : 1.5;
      const want = f.clone().multiplyScalar(a.f).add(r.clone().multiplyScalar(a.r));
      if (want.lengthSq() > 1) want.normalize();
      want.multiplyScalar(sp);
      this.vel.lerp(want, 1 - Math.exp(-dt * 8));
      const dx = this.vel.x * dt, dy = this.vel.y * dt, z0 = this.walkZ;
      // standing in a blocked cell (after a jump, at a raster edge): any move that keeps the height is allowed out
      const thr = this.cost(p.x, p.y, z0) === Infinity;
      if (this.can(p.x, p.y, p.x + dx, p.y + dy, z0, thr)) { p.x += dx; p.y += dy; }
      else {
        // glide: the stride turned up to 70 degrees either way (round a pillar or a corner), then along x or y alone
        const L = Math.hypot(dx, dy); let moved = false;
        for (const t of [0.35, -0.35, 0.7, -0.7, 1.2, -1.2]) {
          const c = Math.cos(t), s = Math.sin(t), ex = (dx * c - dy * s) * Math.cos(t), ey = (dx * s + dy * c) * Math.cos(t);
          if (L > 1e-6 && this.can(p.x, p.y, p.x + ex, p.y + ey, z0, thr)) { p.x += ex; p.y += ey; moved = true; break; }
        }
        if (!moved && L > 1e-6) {
          // side-step toward the nearer opening just ahead (the walk map's 0.5 m cells make stairs of a slanting rail)
          const fx = dx / L, fy = dy / L, sx = -fy, sy = fx;
          let side = 0;
          for (const k of [0.2, 0.4, 0.7, 1.0]) {
            if (this.free(p.x + fx * 0.3 + sx * k, p.y + fy * 0.3 + sy * k, z0, thr)) { side = 1; break; }
            if (this.free(p.x + fx * 0.3 - sx * k, p.y + fy * 0.3 - sy * k, z0, thr)) { side = -1; break; }
          }
          const ex = sx * side * L, ey = sy * side * L;
          if (side && this.can(p.x, p.y, p.x + ex, p.y + ey, z0, thr)) { p.x += ex; p.y += ey; moved = true; }
        }
        if (!moved) {
          if (this.can(p.x, p.y, p.x + dx, p.y, z0, thr)) { p.x += dx; this.vel.y = 0; }
          else if (this.can(p.x, p.y, p.x, p.y + dy, z0, thr)) { p.y += dy; this.vel.x = 0; }
          else this.vel.multiplyScalar(0.5);
        }
      }
      const z = this.at(p.x, p.y, this.walkZ, true);
      if (z != null) this.walkZ += (z - this.walkZ) * Math.min(1, dt * 10);
      const v = Math.hypot(this.vel.x, this.vel.y);
      this.bob += dt * v * 1.15 * Math.PI;
      p.z = this.walkZ + EYE + Math.sin(this.bob * 2) * 0.012 * Math.min(1, v / 1.4);
    } else {
      const want = f.clone().multiplyScalar(a.f * Math.cos(this.pitch)).add(r.clone().multiplyScalar(a.r)); want.z += a.u + a.f * Math.sin(this.pitch);
      want.multiplyScalar(this.speed * (a.fast ? 4 : 1));
      this.vel.lerp(want, 1 - Math.exp(-dt * 4));
      cam.position.addScaledVector(this.vel, dt);
      // stay above the ground (walk map where loaded, else the coarse terrain)
      const w = this.tiles.sample(cam.position.x, cam.position.y);
      const gz = w.z !== undefined ? w.z : (this.ground ? this.ground(cam.position.x, cam.position.y) : -1e9);
      if (cam.position.z < gz + 2.0) { cam.position.z = gz + 2.0; if (this.vel.z < 0) this.vel.z = 0; }
    }
    const d = new THREE.Vector3(Math.cos(this.yaw) * Math.cos(this.pitch), Math.sin(this.yaw) * Math.cos(this.pitch), Math.sin(this.pitch));
    cam.up.set(0, 0, 1);
    cam.lookAt(cam.position.clone().add(d));
  }
}
