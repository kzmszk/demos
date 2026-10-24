import * as THREE from 'three';

// The cape glider as a point-mass glider: the pilot commands a flight-path angle (pitch input) and a bank (roll
// input); the path turns toward those at a rate the airspeed allows, speed follows gravity and drag along the
// path, and the air near tall walls rises. Everything in three.js world axes (y up). Speeds in m/s.

const G = 9.81, RHO = 1.2, MASS = 72, AREA = 2.6;
const clamp = THREE.MathUtils.clamp;
const _d = new THREE.Vector3();

export class Flight {
  constructor(ground, roof) {
    this.ground = ground;           // (x east, y north) -> terrain z
    this.roof = roof;               // roof raster
    this.p = new THREE.Vector3(); this.v = new THREE.Vector3();
    this.heading = 0; this.roll = 0; this.gamma = 0; this.aoa = 0; this.open = 0;
    this.state = 'rest';            // rest | fall | glide | landing | crash
    this.input = { pitch: 0, roll: 0, tuck: false, flare: false };
    this.restPos = new THREE.Vector3(); this.updraft = 0; this.speed = 0; this.gload = 1;
    this.time = 0; this.stateTime = 0; this.launch = null; this.target = null;
    this.hand = false; this.handT = 0; this.handBlend = 0;       // flying hand in hand with Saki (she steers)
    this.close = false; this.closeBlend = 0;                      // drawn in against him, face to face
    this.aoaVis = 0; this.flareVis = 0;                           // slow versions for the camera and the arms (the autopilot toggles the real ones)
    this.forward = new THREE.Vector3(0, 0, -1); this.right = new THREE.Vector3(1, 0, 0);
  }
  dataXY() { return [this.p.x, -this.p.z]; }
  surfaceAt(x, y) { return Math.max(this.roof.top(x, y), this.ground(x, y)); }
  placeOnRoof(x, y, heading) {
    const z = this.surfaceAt(x, y);
    this.p.set(x, z + 1.65, -y); this.v.set(0, 0, 0); this.heading = heading; this.roll = 0; this.open = 0; this.gamma = 0;
    this.state = 'rest'; this.stateTime = 0; this.restPos.copy(this.p); this.target = null;
    this.forward.set(Math.sin(heading), 0, -Math.cos(heading)); this.right.set(Math.cos(heading), 0, Math.sin(heading));
  }
  jump(heading) {
    if (this.state !== 'rest') return;
    if (heading === undefined) heading = this.heading;
    // you can only jump off an edge: of the directions near the one you face, take the first that clears this roof
    const [x, y] = this.dataXY(); const top = this.roof.top(x, y);
    const clear = (h) => { for (const d of [8, 16]) { const t = this.roof.top(x + Math.sin(h) * d, y + Math.cos(h) * d); if (t > top - 4) return false; } return true; };
    let best = null;
    for (let k = 0; k < 24 && best === null; k++) { const off = (k % 2 ? -1 : 1) * Math.ceil(k / 2) * (Math.PI / 12); if (clear(heading + off)) best = heading + off; }
    if (best !== null) heading = best;
    this.heading = heading; this.forward.set(Math.sin(heading), 0, -Math.cos(heading)); this.right.set(Math.cos(heading), 0, Math.sin(heading));
    this.v.copy(this.forward).multiplyScalar(5.0); this.v.y = 2.0; this.gamma = 0.4;
    this.state = 'fall'; this.stateTime = 0; this.open = 0; this.launch = this.p.clone(); this.launchTop = top;
  }
  // rising air: along the walls of tall buildings (ridge lift, which carries on some way above the top) and over the
  // sun-warmed roofs below. Generous on purpose: a glider that circles near a tower should climb at a few metres a second.
  windUp(x, y, z) {
    let w = 0;
    for (let k = 0; k < 12; k++) {
      const a = k * Math.PI / 6, c = Math.cos(a), s = Math.sin(a);
      for (const [r, gain] of [[18, 1.3], [40, 0.8], [75, 0.4]]) {
        const t = this.roof.top(x + c * r, y + s * r);
        if (t > z - 30) w += Math.min(1, (t - z + 30) / 70) * gain;
      }
    }
    const below = this.roof.top(x, y);
    if (below > -1e9 && z - below > 2 && z - below < 140) w += 3.2 * (1 - (z - below) / 140);
    return Math.min(14.0, w * 1.6);
  }
  // steer toward a roof point: used by the landing autopilot
  // the roof must lie below the glide line and roughly ahead; returns false when it cannot be reached
  land(target) {
    if (this.state !== 'glide') return false;
    const d = target.clone().sub(this.p); const dh = Math.hypot(d.x, d.z);
    let dh2 = Math.atan2(d.x, -d.z) - this.heading; dh2 = Math.atan2(Math.sin(dh2), Math.cos(dh2));
    if (d.y > -dh * 0.075 + 4 || d.y < -dh * 0.62 || Math.abs(dh2) > 1.9) return false;     // too shallow, too steep, or behind
    this.target = target.clone(); this.state = 'landing'; this.stateTime = 0; return true;
  }
  step(dt) {
    dt = Math.min(dt, 0.05); this.time += dt; this.stateTime += dt;
    if (this.hand && this.state !== 'glide') this.hand = false;
    this.handT = this.hand ? this.handT + dt : 0; this.handBlend += ((this.hand ? 1 : 0) - this.handBlend) * Math.min(1, dt * 3);
    if (!this.hand) this.close = false; this.closeBlend += ((this.close ? 1 : 0) - this.closeBlend) * Math.min(1, dt * 1.2);
    this.aoaVis += (this.aoa - this.aoaVis) * Math.min(1, dt * 1.2); this.flareVis += ((this.input.flare ? 1 : 0) - this.flareVis) * Math.min(1, dt * 1.5);
    if (this.state === 'rest') { this.updraft = 0; this.speed = 0; return; }
    if (this.state === 'crash') { this.updraft = 0; this.speed = 0; return; }           // down: nothing moves until the respawn
    let s = this.v.length(); this.speed = s;
    const [x, y] = this.dataXY();
    if (this.state === 'fall') {
      // the drop: ballistic until the cape is open and there is air to fly on
      this.open = Math.min(1, this.stateTime / 1.3);
      this.v.y -= G * dt; this.v.multiplyScalar(1 - 0.02 * this.open * dt); this.p.addScaledVector(this.v, dt);
      this.speed = this.v.length(); this.heading = Math.atan2(this.v.x, -this.v.z); this.gamma = Math.asin(clamp(this.v.y / Math.max(this.speed, 0.01), -1, 1));
      if (this.open >= 1 && this.speed > 8) { this.state = 'glide'; this.stateTime = 0; }
      return;
    } else if (this.state !== 'crash') this.open = 1;
    // flight-path angle and heading from the velocity
    if (s > 0.5) { this.gamma = Math.asin(clamp(this.v.y / s, -1, 1)); this.heading = Math.atan2(this.v.x, -this.v.z); }
    // what the pilot asks for
    let gCmd = -0.115 + this.input.pitch * 0.36;                 // trimmed glide about 6.5 degrees down; stick to +/-20
    if (this.input.tuck) gCmd = Math.min(gCmd, -0.55);
    if (this.input.flare) gCmd = Math.max(gCmd, 0.06);
    let rollCmd = this.input.roll * 1.0;
    if (this.state === 'landing' && this.target) {
      const d = _d.copy(this.target).sub(this.p); const dh = Math.hypot(d.x, d.z);
      let dh2 = Math.atan2(d.x, -d.z) - this.heading; dh2 = Math.atan2(Math.sin(dh2), Math.cos(dh2));
      const slope = d.y / Math.max(dh, 1);                                   // negative: the roof is below
      this.input.tuck = false;
      if (slope < -0.38 && dh > 14) {
        // far too high for a straight glide: a descending spiral, cape spread, until the roof comes into the glide line
        rollCmd = 0.6; gCmd = -0.34; this.input.flare = true;
      } else {
        rollCmd = clamp(dh2 * 2.0, -0.8, 0.8);
        gCmd = clamp(Math.atan2(d.y + 1.5, Math.max(dh, 1)), -0.42, -0.02);
        this.input.flare = s > 14 || dh < 45;                                 // slow, steady final
      }
      if (dh < 10 && Math.abs(d.y) < 8) { this.placeOnRoof(this.target.x, -this.target.z, this.heading); return; }
      if (d.y > 3 && dh > 10) { this.state = 'glide'; this.target = null; }          // slipped below the roof: back to the pilot
    }
    // the cape needs airspeed to steer; the stall: too slow and the nose drops
    const authority = clamp((s - 7) / 5, 0, 1) * this.open;          // full control from 12 m/s; the stall only below ~9
    if (s < 8 && this.open > 0.5) gCmd = Math.min(gCmd, -0.5);
    this.roll += (rollCmd - this.roll) * Math.min(1, dt * 3.5);
    // with authority the path follows the command; without it gravity turns the path down (the stall)
    const dg = clamp((gCmd - this.gamma) * 2.2, -1.0, 1.0) * authority + (-1.2 - this.gamma) * (1 - authority) * 1.2;
    const gammaNew = clamp(this.gamma + dg * dt, -1.4, 0.9);
    // coordinated turn at this bank, plus the gentle yaw of a hand on the cape at low speed
    const turn = authority * G * Math.tan(this.roll * 0.9) / Math.max(s, 8);
    this.heading += turn * dt;
    // speed along the path: gravity and drag; holding the path costs induced drag (the g-load), the tuck is slippery
    const q = 0.5 * RHO * s * s;
    this.gload = Math.cos(gammaNew) / Math.max(Math.cos(this.roll), 0.5) + dg * s / G;
    const cl = clamp(this.gload * MASS * G / Math.max(q * AREA, 1), -0.5, 1.6);
    const cd = (this.input.tuck ? 0.045 : 0.075) + 0.06 * cl * cl + (this.input.flare ? 0.5 : 0) + (1 - this.open) * 0.1;
    const accel = -G * Math.sin(gammaNew) - q * AREA * cd / MASS;
    s = Math.max(0, s + accel * dt);
    if (this.state === 'fall' && this.open < 1) s += 0;                          // the fall itself is just gravity
    this.gamma = gammaNew;
    this.v.set(Math.sin(this.heading) * Math.cos(this.gamma) * s, Math.sin(this.gamma) * s, -Math.cos(this.heading) * Math.cos(this.gamma) * s);
    // rising air carries the whole glider
    // the lift field is sampled on a 4 m raster, so it steps as you cross cells; smooth it over ~0.4 s
    const upRaw = this.open > 0.5 && this.state !== 'landing' ? this.windUp(x, y, this.p.y) : 0;     // on final she spills the lift
    this.updraft += (upRaw - this.updraft) * Math.min(1, dt * 2.5);
    this.p.addScaledVector(this.v, dt); this.p.y += this.updraft * dt;
    this.speed = s;
    this.forward.set(Math.sin(this.heading), 0, -Math.cos(this.heading)); this.right.set(Math.cos(this.heading), 0, Math.sin(this.heading));
    // the world
    const [nx, ny] = this.dataXY();
    const g = this.ground(nx, ny);
    // a wall counts only once you are well inside it: the lowest of the cells around you (4 m raster), so brushing past
    // a facade or the broken edge of a roof is not a crash
    const R = this.roof; const rt = Math.min(R.top(nx, ny), R.top(nx + 3, ny), R.top(nx - 3, ny), R.top(nx, ny + 3), R.top(nx, ny - 3));
    if (this.state === 'landing' && this.p.y < rt + 1.0 && this.target && this.p.distanceTo(this.target) < 25) { this.placeOnRoof(nx, ny, this.heading); return; }
    // the roof you left is never a wall: its jagged broken top (the raster is 4 m cells) would catch you on the way out
    const own = this.launch && this.p.distanceTo(this.launch) < 70 && Math.abs(rt - this.launchTop) < 6;
    if (this.p.y < g + 0.6 || (!own && this.p.y < rt - 2.0)) { this.state = 'crash'; this.stateTime = 0; this.crashPos = this.p.clone(); this.p.y = Math.max(this.p.y, g + 0.6); }
  }
}
