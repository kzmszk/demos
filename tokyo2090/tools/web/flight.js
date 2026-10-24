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
    this.state = 'rest';            // rest (on foot: a roof or the street) | climb | fall | glide | landing | crash
    this.input = { pitch: 0, roll: 0, tuck: false, flare: false };
    this.restPos = new THREE.Vector3(); this.updraft = 0; this.speed = 0; this.gload = 1;
    this.time = 0; this.stateTime = 0; this.launch = null; this.target = null;
    this.hand = false; this.handT = 0; this.handBlend = 0;       // flying hand in hand with Saki (she steers)
    this.close = false; this.closeBlend = 0;                      // drawn in against him, face to face
    this.aoaVis = 0; this.flareVis = 0;                           // slow versions for the camera and the arms (the autopilot toggles the real ones)
    this.forward = new THREE.Vector3(0, 0, -1); this.right = new THREE.Vector3(1, 0, 0);
    // on foot
    this.walker = null; this.street = false; this.walked = false; this.feet = 0; this.eye = 0; this.vz = 0;
    this.wv = { x: 0, y: 0 }; this.walkSpeed = 0; this.walkHeading = 0; this.stride = 0; this.bob = 0; this.blocked = null;
    this.climbH = 0; this.climbTop = 0; this.hopV = 0; this.hopZ = 0;
    this.rollRate = 0; this.gRate = 0;                            // the body's attitude has momentum (see step)
  }
  dataXY() { return [this.p.x, -this.p.z]; }
  setWalker(w) { this.walker = w; }
  surfaceAt(x, y) { return this.walker ? this.walker.under(x, y) : Math.max(this.roof.top(x, y), this.ground(x, y)); }
  setHeading(h) { this.heading = h; this.forward.set(Math.sin(h), 0, -Math.cos(h)); this.right.set(Math.cos(h), 0, Math.sin(h)); }
  // stand at a point (a roof or the street): `slide` carries a little of the landing speed into the first steps
  placeOnFoot(x, y, heading, slide = null) {
    const z = this.surfaceAt(x, y);
    this.p.set(x, z + 1.65, -y); this.v.set(0, 0, 0); this.roll = 0; this.open = 0; this.gamma = 0; this.rollRate = 0; this.gRate = 0; this.setHeading(heading);
    this.state = 'rest'; this.stateTime = 0; this.restPos.copy(this.p); this.target = null; this.launch = null;
    this.feet = z; this.eye = z + 1.65; this.vz = 0; this.dropping = false; this.walked = false; this.walkHeading = heading; this.walkSpeed = 0; this.hopZ = 0; this.hopV = 0;
    this.street = this.onStreet(x, y, z); this.prevY = -Infinity;
    this.wv.x = slide ? slide.x : 0; this.wv.y = slide ? slide.y : 0;
  }
  placeOnRoof(x, y, heading) { this.placeOnFoot(x, y, heading); }
  // the street (or a car, a mound of rubble) rather than a building: no edge to jump from
  onStreet(x, y, z) { return this.walker ? !this.walker.foot.solid(x, y) || z - this.ground(x, y) < 1.5 : z - this.ground(x, y) < 4; }
  // a step on foot: (mx, my) is the wished direction in data axes (length 0..1), run doubles the pace and then some
  walk(dt, mx, my, run) {
    dt = Math.min(dt, 0.05);                         // (time and stateTime advance in step(), which runs first)
    const W = this.walker; if (!W) return;
    const [x, y] = this.dataXY();
    const pace = run ? 4.3 : 1.45, accel = Math.hypot(mx, my) > 0.01 ? 7 : 5;
    this.wv.x += (mx * pace - this.wv.x) * Math.min(1, dt * accel); this.wv.y += (my * pace - this.wv.y) * Math.min(1, dt * accel);
    const sp = Math.hypot(this.wv.x, this.wv.y);
    let nx = x, ny = y; this.blocked = null; this.edge = false;
    if (sp > 0.02) {
      const r = W.move(x, y, this.feet, this.wv.x * dt, this.wv.y * dt);
      nx = r.x; ny = r.y; this.blocked = r.blocked; this.edge = r.edge;
      const moved = Math.hypot(nx - x, ny - y);
      if (moved < sp * dt * 0.3) { this.wv.x *= 0.5; this.wv.y *= 0.5; }      // against a wall: do not keep pushing
      this.walkSpeed = moved / dt; this.stride += moved;
      if (moved > 0.002) { this.walked = true; this.walkHeading = Math.atan2(nx - x, ny - y); }
      if (r.z > this.feet) this.feet = r.z;                                  // up a step (the eye eases after it)
    } else this.walkSpeed = 0;
    // down: fall to what is under you
    const under = W.under(nx, ny);
    if (under < this.feet - 0.02) { this.vz -= 9.81 * dt; this.feet = Math.max(under, this.feet + this.vz * dt); } else { this.feet = under; this.vz = 0; }
    this.street = this.onStreet(nx, ny, this.feet);
    // a hop (Space on the street with nothing to climb)
    if (this.hopZ > 0 || this.hopV > 0) { this.hopV -= 9.81 * dt; this.hopZ = Math.max(0, this.hopZ + this.hopV * dt); if (this.hopZ === 0) this.hopV = 0; }
    // the eye: eases up steps, bobs with the stride
    const eyeWant = this.feet + 1.65; this.eye = eyeWant < this.eye ? eyeWant : this.eye + (eyeWant - this.eye) * Math.min(1, dt * 10);
    const stepLen = run ? 1.15 : 0.72;
    this.bob = this.walkSpeed > 0.2 ? -Math.abs(Math.sin(this.stride / stepLen * Math.PI)) * (run ? 0.07 : 0.035) : this.bob * 0.85;
    this.p.set(nx, this.eye + this.bob + this.hopZ, -ny);
    this.speed = this.walkSpeed;
    if (this.walkSpeed > 0.05 && this.hopZ === 0) this.restPos.set(nx, this.feet + 1.65, -ny);
  }
  hop() { if (this.state === 'rest' && this.hopZ === 0) this.hopV = 3.2; }
  // climbing: Space near a wall (or pushing into it). Up the face, faster as you go, onto whatever is on top
  climb(h) {
    if (this.state !== 'rest' || !this.walker) return false;
    const [x, y] = this.dataXY();
    const w = this.walker.wallNear(x, y, this.feet, h); if (!w) return false;
    h = w.h;
    const back = Math.max(0, w.dist - 0.3);
    this.p.x += Math.sin(h) * back; this.p.z -= Math.cos(h) * back;
    this.climbH = h; this.climbTop = w.top; this.setHeading(h);
    this.state = 'climb'; this.stateTime = 0; this.speed = 0; this.walked = true;
    return true;
  }
  climbStep(dt) {
    dt = Math.min(dt, 0.05);                         // (time and stateTime advance in step(), which runs first)
    const W = this.walker, h = this.climbH, c = Math.sin(h), s = Math.cos(h);
    const [x, y] = this.dataXY();
    const v = Math.min(11, 2.2 + this.stateTime * 1.8); this.speed = v;
    this.feet += v * dt; this.eye = this.feet + 1.65;
    // the face may step back (a setback, a broken edge): the top is whatever stands within a few metres ahead
    let top = -Infinity; for (let d = 0.6; d <= 4.5; d += 0.6) top = Math.max(top, W.surface(x + c * d, y + s * d));
    this.climbTop = top;
    this.p.y = this.eye + Math.sin(this.stateTime * 7) * 0.04;
    if (this.feet >= top + 0.15) {
      // over the top: step onto it, a little way in from the edge
      for (let d = 1.0; d <= 5; d += 0.5) { const t = W.under(x + c * d, y + s * d); if (Math.abs(t - top) < 1.5) { this.placeOnFoot(x + c * d, y + s * d, h); this.walked = true; this.climbed = true; return; } }
      this.placeOnFoot(x + c * 1.5, y + s * 1.5, h); this.walked = true; this.climbed = true;
    }
  }
  // push off the wall into the air, facing away from it
  kickOff() {
    if (this.state !== 'climb' || this.stateTime < 0.6) return;          // not on the same press that started the climb
    const h = this.climbH + Math.PI; this.setHeading(h);
    this.v.copy(this.forward).multiplyScalar(5.5); this.v.y = 2.5; this.gamma = 0.4;
    this.state = 'fall'; this.stateTime = 0; this.open = 0; this.launch = this.p.clone(); this.launchTop = this.climbTop;
  }
  jump(heading) {
    if (this.state !== 'rest' || this.street) return;
    if (heading === undefined) heading = this.heading;
    // you can only jump off an edge: of the directions near the one you face, take the first that clears this roof
    const [x, y] = this.dataXY(); const top = this.roof.top(x, y);
    const clear = (h) => { for (const d of [8, 16]) { const t = this.roof.top(x + Math.sin(h) * d, y + Math.cos(h) * d); if (t > top - 4) return false; } return true; };
    let best = null;
    for (let k = 0; k < 24 && best === null; k++) { const off = (k % 2 ? -1 : 1) * Math.ceil(k / 2) * (Math.PI / 12); if (clear(heading + off)) best = heading + off; }
    if (best !== null) heading = best;
    this.heading = heading; this.forward.set(Math.sin(heading), 0, -Math.cos(heading)); this.right.set(Math.cos(heading), 0, Math.sin(heading));
    this.v.copy(this.forward).multiplyScalar(5.0); this.v.y = 2.0; this.gamma = 0.4;
    this.state = 'fall'; this.stateTime = 0; this.open = 0; this.launch = this.p.clone(); this.launchTop = top; this.hopZ = 0;
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
    // down in the street the air is sheltered: the lift fades over the last 25 m above the ground (so you can come down)
    const shelter = clamp((z - this.ground(x, y) - 5) / 20, 0.12, 1);
    return Math.min(14.0, w * 1.6) * (below > -1e9 && z - below > 2 ? 1 : shelter);
  }
  // steer toward a roof point: used by the landing autopilot
  // the roof must lie below the glide line and roughly ahead; returns false when it cannot be reached
  // A street target (target.ground, picked by main.js with room around it) is reached differently: glide over to it
  // no lower than `safe` (the tops around it plus a margin), then come straight down on the open cape like a parachute.
  land(target) {
    if (this.state !== 'glide') return false;
    const d = target.clone().sub(this.p); const dh = Math.hypot(d.x, d.z);
    let dh2 = Math.atan2(d.x, -d.z) - this.heading; dh2 = Math.atan2(Math.sin(dh2), Math.cos(dh2));
    if (!target.ground && (d.y > -dh * 0.075 + 4 || d.y < -dh * 0.62 || Math.abs(dh2) > 1.9)) return false;     // too shallow, too steep, or behind
    this.target = target.clone(); this.targetGround = !!target.ground; this.safe = target.safe ?? target.y + 8; this.dropping = false;
    this.state = 'landing'; this.stateTime = 0; return true;
  }
  step(dt) {
    dt = Math.min(dt, 0.05); this.time += dt; this.stateTime += dt;
    if (this.hand && this.state !== 'glide') this.hand = false;
    this.handT = this.hand ? this.handT + dt : 0; this.handBlend += ((this.hand ? 1 : 0) - this.handBlend) * Math.min(1, dt * 3);
    if (!this.hand) this.close = false; this.closeBlend += ((this.close ? 1 : 0) - this.closeBlend) * Math.min(1, dt * 1.2);
    this.aoaVis += (this.aoa - this.aoaVis) * Math.min(1, dt * 1.2); this.flareVis += ((this.input.flare ? 1 : 0) - this.flareVis) * Math.min(1, dt * 1.5);
    if (this.state === 'rest' || this.state === 'climb') { this.updraft = 0; return; }
    if (this.state === 'crash') { this.updraft = 0; this.speed = 0; return; }           // down: nothing moves until the respawn
    let s = this.v.length(); this.speed = s;
    const [x, y] = this.dataXY();
    if (this.state === 'fall') {
      // the drop: ballistic until the cape is open and there is air to fly on
      this.open = Math.min(1, this.stateTime / 1.3);
      this.v.y -= G * dt; this.v.multiplyScalar(1 - 0.02 * this.open * dt); this.p.addScaledVector(this.v, dt);
      this.speed = this.v.length(); this.heading = Math.atan2(this.v.x, -this.v.z); this.gamma = Math.asin(clamp(this.v.y / Math.max(this.speed, 0.01), -1, 1));
      this.gRate = 0; this.rollRate = 0;
      if (this.open >= 1 && this.speed > 8) { this.state = 'glide'; this.stateTime = 0; }
      this.collide(); return;
    } else if (this.state !== 'crash') this.open = 1;
    // flight-path angle and heading from the velocity
    if (s > 0.5) { this.gamma = Math.asin(clamp(this.v.y / s, -1, 1)); this.heading = Math.atan2(this.v.x, -this.v.z); }
    // what the pilot asks for
    let gCmd = -0.115 + this.input.pitch * 0.36;                 // trimmed glide about 6.5 degrees down; stick to +/-20
    if (this.input.tuck) gCmd = Math.min(gCmd, -0.55);
    if (this.input.flare) gCmd = Math.max(gCmd, 0.06);
    let rollCmd = this.input.roll * 1.0;
    if (this.state === 'landing' && this.target && this.targetGround) {
      const d = _d.copy(this.target).sub(this.p); const dh = Math.hypot(d.x, d.z);
      if (dh < 13 || this.dropping) {
        // over it: down on the open cape, a few metres a second, drifting onto the spot
        this.dropping = true;
        // first over the spot (the tops around it were checked only that far out), then down: 12 m/s high up, 3.5 at the end
        const k = Math.min(6, dh * 1.0) / Math.max(dh, 1e-3), above = this.p.y - this.target.y;
        const sink = (3.5 + Math.min(9, Math.max(0, above - 4) * 0.15)) * (dh < 5 ? 1 : 0.35);
        this.v.x += (d.x * k - this.v.x) * Math.min(1, dt * 2); this.v.z += (d.z * k - this.v.z) * Math.min(1, dt * 2); this.v.y += (-sink - this.v.y) * Math.min(1, dt * 1.5);
        this.p.addScaledVector(this.v, dt);
        this.speed = this.v.length(); this.gamma = Math.asin(clamp(this.v.y / Math.max(this.speed, 0.01), -1, 1)); this.roll *= 1 - Math.min(1, dt * 1.5); this.rollRate = 0; this.gRate = 0;
        if (dh > 1) this.heading = Math.atan2(d.x, -d.z);
        this.input.flare = true; this.input.tuck = false; this.updraft = 0;
        this.forward.set(Math.sin(this.heading), 0, -Math.cos(this.heading)); this.right.set(Math.cos(this.heading), 0, Math.sin(this.heading));
        this.collide(); return;
      }
      // on the way: straight for it, sinking toward the safe height above it but not below
      let dh2 = Math.atan2(d.x, -d.z) - this.heading; dh2 = Math.atan2(Math.sin(dh2), Math.cos(dh2));
      rollCmd = clamp(dh2 * 2.0, -0.8, 0.8); this.input.tuck = false;
      // never steeper than the 1-in-8 line main.js checked clear of everything on the way
      gCmd = clamp(Math.atan2(this.safe - this.p.y, Math.max(dh - 8, 1)), -0.125, -0.03);
      this.input.flare = s > 16;
    } else if (this.state === 'landing' && this.target) {
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
      if (dh < 10 && Math.abs(d.y) < 8) { this.placeOnFoot(this.target.x, -this.target.z, this.heading, this.slideOf(0.35)); return; }
      if (d.y > 3 && dh > 10) { this.state = 'glide'; this.target = null; }          // slipped below the roof: back to the pilot
    }
    // the cape needs airspeed to steer; the stall: too slow and the nose drops
    const authority = clamp((s - 7) / 5, 0, 1) * this.open;          // full control from 12 m/s; the stall only below ~9
    if (s < 8 && this.open > 0.5) gCmd = Math.min(gCmd, -0.5);
    // A body under a cape, not a fighter: the bank and the pitch have momentum. The roll is a damped spring (it has to
    // start rolling and stop again, its rate and the change of its rate both capped), and the path's pitch rate eases
    // toward what the stick asks for, so every change of attitude swells in and settles instead of snapping.
    const rAcc = clamp(6.0 * (rollCmd - this.roll) - 4.2 * this.rollRate, -3.5, 3.5);
    this.rollRate = clamp(this.rollRate + rAcc * dt, -1.1, 1.1); this.roll += this.rollRate * dt;
    this.gRate += (clamp((gCmd - this.gamma) * 1.2, -0.6, 0.6) - this.gRate) * Math.min(1, dt * 2.4);
    // with authority the path follows the command; without it gravity turns the path down (the stall)
    const dg = this.gRate * authority + (-1.2 - this.gamma) * (1 - authority) * 1.2;
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
    this.collide();
  }
  collide() {
    const [nx, ny] = this.dataXY();
    const g = this.ground(nx, ny);
    // a wall counts only once you are well inside it: the lowest of the cells around you (4 m raster), so brushing past
    // a facade or the broken edge of a roof is not a crash
    const R = this.roof; const rt = Math.min(R.top(nx, ny), R.top(nx + 3, ny), R.top(nx - 3, ny), R.top(nx, ny + 3), R.top(nx, ny - 3));
    if (this.state === 'landing' && !this.targetGround && this.p.y < rt + 1.0 && this.target && this.p.distanceTo(this.target) < 25) { this.placeOnFoot(nx, ny, this.heading, this.slideOf(0.3)); return; }
    // the roof you left is never a wall: its jagged broken top (the raster is 4 m cells) would catch you on the way out
    const own = this.launch && this.p.distanceTo(this.launch) < 70 && Math.abs(rt - this.launchTop) < 6;
    // touching down: feet first and not falling hard (a glide sinks at 1-3 m/s) is a landing, on the street or on a
    // roof you come down onto from above; anything harder, or into a wall, is a crash
    // (falling off a roof the cape is still opening and brakes the last metres: a low roof is a drop to the street)
    const soft = this.v.y > (this.state === 'fall' ? -18 : -8.5);
    const floor = this.walker ? Math.max(g, this.walker.mound(nx, ny), this.walker.car(nx, ny)) : g;
    if (this.p.y < floor + 1.0 && !(this.walker && this.walker.foot && this.walker.foot.solid(nx, ny) && rt > g + 4)) {
      if (soft) { this.placeOnFoot(nx, ny, this.heading, this.slideOf(0.45)); this.touchdown = 'street'; return; }
      this.crashNow(g); return;
    }
    if (!own && rt > g + 4 && this.p.y < rt + 1.2 && this.prevY >= rt + 1.2 && soft) { this.placeOnFoot(nx, ny, this.heading, this.slideOf(0.3)); this.touchdown = 'roof'; return; }
    if (this.p.y < g + 0.6 || (!own && this.p.y < rt - 2.0)) { this.crashNow(g); return; }
    this.prevY = this.p.y;
  }
  crashNow(g) { this.state = 'crash'; this.stateTime = 0; this.crashPos = this.p.clone(); this.p.y = Math.max(this.p.y, g + 0.6); }
  // the horizontal speed you carry into the first steps after a landing (data axes, capped at a run)
  slideOf(k) { const x = this.v.x * k, y = -this.v.z * k, l = Math.hypot(x, y), m = Math.min(1, 4.5 / Math.max(l, 1e-6)); return { x: x * m, y: y * m }; }
}
