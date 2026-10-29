// Drone-style free flight in a z-up world: drag to look, WASD/arrows to move, E/Q (Space/C) up/down,
// Shift = fast. Velocity is smoothed so it feels like a drone gliding.
import * as THREE from 'three';
export class FlyControls {
  constructor(camera, dom) {
    this.camera = camera; this.dom = dom;
    this.yaw = 0; this.pitch = 0; this.vel = new THREE.Vector3(); this.keys = new Set();
    this.speed = 25; this.enabled = true;
    this.syncFromCamera();
    let drag = null;
    dom.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY }; dom.setPointerCapture(e.pointerId); });
    dom.addEventListener('pointerup', () => { drag = null; });
    dom.addEventListener('pointermove', (e) => {
      if (!drag || !this.enabled) return;
      this.yaw -= (e.clientX - drag.x) * 0.0035; this.pitch -= (e.clientY - drag.y) * 0.0035;
      this.pitch = Math.max(-1.5, Math.min(1.5, this.pitch)); drag = { x: e.clientX, y: e.clientY };
    });
    addEventListener('keydown', (e) => this.keys.add(e.code));
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    dom.addEventListener('wheel', (e) => { this.speed = Math.max(2, Math.min(400, this.speed * (e.deltaY > 0 ? 0.85 : 1.18))); e.preventDefault(); }, { passive: false });
  }
  syncFromCamera() {
    const d = new THREE.Vector3(); this.camera.getWorldDirection(d);
    this.yaw = Math.atan2(d.y, d.x); this.pitch = Math.asin(Math.max(-1, Math.min(1, d.z)));
  }
  update(dt) {
    if (!this.enabled) return;
    const k = this.keys, f = new THREE.Vector3(Math.cos(this.yaw), Math.sin(this.yaw), 0), r = new THREE.Vector3(Math.sin(this.yaw), -Math.cos(this.yaw), 0);
    const want = new THREE.Vector3();
    if (k.has('KeyW') || k.has('ArrowUp')) want.add(f);
    if (k.has('KeyS') || k.has('ArrowDown')) want.sub(f);
    if (k.has('KeyD') || k.has('ArrowRight')) want.add(r);
    if (k.has('KeyA') || k.has('ArrowLeft')) want.sub(r);
    if (k.has('KeyE') || k.has('Space')) want.z += 1;
    if (k.has('KeyQ') || k.has('KeyC')) want.z -= 1;
    want.multiplyScalar(this.speed * (k.has('ShiftLeft') || k.has('ShiftRight') ? 4 : 1));
    this.vel.lerp(want, 1 - Math.exp(-dt * 3));
    this.camera.position.addScaledVector(this.vel, dt);
    const d = new THREE.Vector3(Math.cos(this.yaw) * Math.cos(this.pitch), Math.sin(this.yaw) * Math.cos(this.pitch), Math.sin(this.pitch));
    this.camera.lookAt(this.camera.position.clone().add(d));
  }
}
