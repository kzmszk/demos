// Camera modes:  fly (free: drag to look, WASD, E/Q up/down, Shift fast, wheel = speed),
// walk (WASD on the walk raster: calli, campi, bridges, porticoes; eye 1.62 m; Shift runs),
// boat (seated in the gondola: drag to look around; manual rowing with W/S and A/D when steering).
import * as THREE from 'three/webgpu';
const EYE = 1.62, R = 0.24;
export class Controls {
  constructor(camera, dom, o = {}) {
    this.camera = camera; this.dom = dom; this.tiles = o.tiles; this.ride = o.ride;
    this.yaw = 0; this.pitch = 0; this.vel = new THREE.Vector3(); this.keys = new Set(); this.speed = 12; this.enabled = true;
    this.mode = 'fly'; this.walkZ = null; this.bob = 0; this.boatYaw = 0; this.boatPitch = -0.05;
    this.move = { x: 0, y: 0 };            // touch joystick (-1..1)
    this.syncFromCamera();
    let drag = null;
    dom.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, id: e.pointerId }; dom.setPointerCapture(e.pointerId); });
    dom.addEventListener('pointerup', () => { drag = null; });
    dom.addEventListener('pointercancel', () => { drag = null; });
    dom.addEventListener('pointermove', (e) => {
      if (!drag || !this.enabled || e.pointerId !== drag.id) return;
      const k = e.pointerType === 'touch' ? 0.005 : 0.003;
      const dx = (e.clientX - drag.x) * k, dy = (e.clientY - drag.y) * k;
      if (this.mode === 'boat') { this.boatYaw = Math.max(-2.6, Math.min(2.6, this.boatYaw - dx)); this.boatPitch = Math.max(-1.0, Math.min(1.0, this.boatPitch - dy)); }
      else { this.yaw -= dx; this.pitch = Math.max(-1.5, Math.min(1.5, this.pitch - dy)); }
      drag.x = e.clientX; drag.y = e.clientY;
    });
    addEventListener('keydown', (e) => { if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) return; this.keys.add(e.code); });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    dom.addEventListener('wheel', (e) => { if (this.mode === 'fly') this.speed = Math.max(1, Math.min(300, this.speed * (e.deltaY > 0 ? 0.85 : 1.18))); e.preventDefault(); }, { passive: false });
  }
  syncFromCamera() {
    const d = new THREE.Vector3(); this.camera.getWorldDirection(d);
    this.yaw = Math.atan2(d.y, d.x); this.pitch = Math.asin(Math.max(-1, Math.min(1, d.z)));
  }
  setMode(m) {
    this.mode = m; this.vel.set(0, 0, 0);
    if (m === 'walk') { this.walkZ = null; this.pitch = Math.max(-0.5, Math.min(0.5, this.pitch)); }
    if (m === 'boat') { this.boatYaw = 0; this.boatPitch = -0.05; }
  }
  axes() {
    const k = this.keys; let f = 0, r = 0, u = 0;
    if (k.has('KeyW') || k.has('ArrowUp')) f += 1;
    if (k.has('KeyS') || k.has('ArrowDown')) f -= 1;
    if (k.has('KeyD')) r += 1;
    if (k.has('KeyA')) r -= 1;
    if (k.has('ArrowRight')) this.yaw -= 0.02;
    if (k.has('ArrowLeft')) this.yaw += 0.02;
    if (k.has('KeyE') || k.has('Space')) u += 1;
    if (k.has('KeyQ') || k.has('KeyC')) u -= 1;
    f += -this.move.y; r += this.move.x;
    return { f: Math.max(-1, Math.min(1, f)), r: Math.max(-1, Math.min(1, r)), u, fast: k.has('ShiftLeft') || k.has('ShiftRight') };
  }
  // walkable at (x, y) for someone standing at height z0? returns surface z or null
  surface(x, y) {
    const w = this.tiles.sample(x, y);
    return w.z;
  }
  free(x, y, z0) {
    for (const [ox, oy] of [[0, 0], [R, 0], [-R, 0], [0, R], [0, -R]]) {
      const z = this.surface(x + ox, y + oy);
      if (z === undefined) return false;               // tile not streamed yet
      if (z === null || Math.abs(z - z0) > 0.55) return false;
    }
    return true;
  }
  // nearest walkable point (spiral search) for entering walk mode
  findWalkable(x, y) {
    if (this.surface(x, y) === undefined) return null;       // wait until the raster under us is in
    for (let r = 0; r < 40; r += 0.5) for (let a = 0; a < 6.283; a += 0.35 / Math.max(1, r)) {
      const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r; const z = this.surface(px, py);
      if (z != null && this.free(px, py, z)) return [px, py, z];
    }
    return null;
  }
  update(dt) {
    if (!this.enabled) return;
    const cam = this.camera;
    if (this.mode === 'boat' && this.ride) {
      const a = this.axes();
      if (this.ride.mode === 'manual') { this.ride.steer.thrust = a.f; this.ride.steer.turn = -a.r; }
      this.ride.seatPose(cam, this.boatYaw, this.boatPitch);
      return;
    }
    const a = this.axes();
    const f = new THREE.Vector3(Math.cos(this.yaw), Math.sin(this.yaw), 0), r = new THREE.Vector3(Math.sin(this.yaw), -Math.cos(this.yaw), 0);
    if (this.mode === 'walk') {
      const p = cam.position;
      if (this.walkZ === null) {
        const w = this.findWalkable(p.x, p.y);
        if (!w) return;                                  // wait for the walk raster
        p.set(w[0], w[1], w[2] + EYE); this.walkZ = w[2];
      }
      const sp = a.fast ? 3.6 : 1.45;
      const want = f.clone().multiplyScalar(a.f).add(r.clone().multiplyScalar(a.r));
      if (want.lengthSq() > 1) want.normalize();
      want.multiplyScalar(sp);
      this.vel.lerp(want, 1 - Math.exp(-dt * 8));
      const dx = this.vel.x * dt, dy = this.vel.y * dt;
      const z0 = this.walkZ;
      if (this.free(p.x + dx, p.y + dy, z0)) { p.x += dx; p.y += dy; }
      else if (this.free(p.x + dx, p.y, z0)) { p.x += dx; this.vel.y = 0; }
      else if (this.free(p.x, p.y + dy, z0)) { p.y += dy; this.vel.x = 0; }
      else this.vel.set(0, 0, 0);
      const z = this.surface(p.x, p.y);
      if (z != null) this.walkZ += (z - this.walkZ) * Math.min(1, dt * 12);
      const v = Math.hypot(this.vel.x, this.vel.y);
      this.bob += dt * v * 1.15 * Math.PI;
      p.z = this.walkZ + EYE + Math.sin(this.bob * 2) * 0.012 * Math.min(1, v / 1.4);
    } else {
      const want = f.clone().multiplyScalar(a.f).add(r.clone().multiplyScalar(a.r)); want.z += a.u;
      want.multiplyScalar(this.speed * (a.fast ? 4 : 1));
      this.vel.lerp(want, 1 - Math.exp(-dt * 4));
      cam.position.addScaledVector(this.vel, dt);
    }
    const d = new THREE.Vector3(Math.cos(this.yaw) * Math.cos(this.pitch), Math.sin(this.yaw) * Math.cos(this.pitch), Math.sin(this.pitch));
    cam.up.set(0, 0, 1);
    cam.lookAt(cam.position.clone().add(d));
  }
}
