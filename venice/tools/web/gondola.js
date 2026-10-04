// The gondola: lofted asymmetric hull (black lacquer), ferro and risso, decks, floorboards, the armchair and
// cushions, brass seahorses, forcola and oar, and a gondolier who rows (and ducks under low bridges).
// GondolaRide moves it along a canal route (autopilot) or under the user's steering.
import * as THREE from 'three/webgpu';
import { vec3, float, uniform, positionLocal, sin, step, fract, mix, color } from 'three/tsl';

const L = 10.8, HL = L / 2;
const keelZ = (x) => -0.20 + 0.72 * Math.pow(Math.abs(x) / HL, 2.4) + (x > 0 ? 0.35 * Math.pow(x / HL, 6) : 0.12 * Math.pow(-x / HL, 6));
const gunZ = (x) => 0.38 + (x > 0 ? 0.88 * Math.pow(x / HL, 3.2) : 0.55 * Math.pow(-x / HL, 3.2));
const halfB = (x) => 0.70 * Math.pow(Math.max(0, 1 - Math.pow(Math.abs(x) / (HL + 0.02), 2)), 0.55);
const yC = (x) => -0.07 * (1 - Math.pow(x / HL, 2));        // the hull bends to starboard (single oar)

function hullGeometry() {
  const NX = 64, NS = 18;
  const xs = [];
  for (let i = 0; i <= NX; i++) { const t = i / NX; xs.push(-HL + L * (0.5 - 0.5 * Math.cos(Math.PI * t))); }
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= NX; i++) {
    const x = xs[i], zk = keelZ(x), zg = gunZ(x), hb = halfB(x), yc = yC(x);
    for (let j = 0; j <= NS; j++) {
      const th = -Math.PI / 2 + Math.PI * j / NS;          // -pi/2 = starboard gunwale, +pi/2 = port gunwale
      const s = Math.sin(th), c = Math.cos(th);
      const asym = s > 0 ? 1.04 : 0.96;
      const y = yc + hb * Math.sign(s) * Math.pow(Math.abs(s), 0.62) * asym;
      const z = zk + (zg - zk) * (1 - Math.pow(Math.abs(c), 0.75));
      pos.push(x, y, z); uv.push(x, j / NS);
    }
  }
  for (let i = 0; i < NX; i++) for (let j = 0; j < NS; j++) {
    const a = i * (NS + 1) + j, b = a + NS + 1;
    idx.push(a, a + 1, b + 1, a, b + 1, b);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// deck between the gunwales from x0 to x1 (flat-ish, slightly crowned)
function deckGeometry(x0, x1, lift = 0.0, crown = 0.03) {
  const N = 24, M = 6, pos = [], idx = [];
  for (let i = 0; i <= N; i++) {
    const x = x0 + (x1 - x0) * i / N, hb = halfB(x) * 0.985, zg = gunZ(x) + lift, yc = yC(x);
    for (let j = 0; j <= M; j++) { const t = -1 + 2 * j / M; pos.push(x, yc + hb * t, zg + crown * (1 - t * t)); }
  }
  for (let i = 0; i < N; i++) for (let j = 0; j < M; j++) { const a = i * (M + 1) + j, b = a + M + 1; idx.push(a, b, b + 1, a, b + 1, a + 1); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// the ferro: a steel comb at the bow (outline in x-z, extruded thin in y)
function ferroGeometry() {
  const P = [[0, 0], [0.10, 0], [0.13, 0.05]];
  for (let k = 0; k < 6; k++) { const z = 0.10 + k * 0.075; P.push([0.13, z], [0.31, z + 0.012], [0.31, z + 0.042], [0.13, z + 0.055]); }
  P.push([0.14, 0.58], [0.21, 0.665], [0.33, 0.735], [0.40, 0.795], [0.31, 0.83], [0.13, 0.80], [0.03, 0.70], [-0.02, 0.5], [-0.03, 0.2], [-0.03, 0.14], [-0.19, 0.12], [-0.19, 0.088], [-0.03, 0.06]);
  const shape = new THREE.Shape(P.map(([x, z]) => new THREE.Vector2(x + 0.16 * z, z)));
  const g = new THREE.ExtrudeGeometry(shape, { depth: 0.018, bevelEnabled: false, curveSegments: 4 });
  g.rotateX(Math.PI / 2); g.translate(0, 0.009, 0);         // shape x-y -> x-z, centred in y
  return g;
}

function tube(len, r, seg = 8) { const g = new THREE.CylinderGeometry(r, r, len, seg); g.rotateZ(Math.PI / 2); return g; }

export function makeDynMaterial(o) {
  const m = new THREE.MeshPhysicalNodeMaterial({ roughness: 0.6, metalness: 0, ...o });
  return m;
}

export class Gondola {
  constructor(env) {
    this.group = new THREE.Group(); this.group.name = 'gondola';
    this.env = env;
    const M = this.mats = {
      lacquer: makeDynMaterial({ color: 0x020202, roughness: 0.45, clearcoat: 0.35, clearcoatRoughness: 0.22 }),
      inner: makeDynMaterial({ color: 0x050403, roughness: 0.85, side: THREE.BackSide }),
      steel: makeDynMaterial({ color: 0xd8d8d8, metalness: 1.0, roughness: 0.18 }),
      brass: makeDynMaterial({ color: 0xd9a441, metalness: 1.0, roughness: 0.28 }),
      wood: makeDynMaterial({ color: 0x5a3a22, roughness: 0.7 }),
      floor: makeDynMaterial({ color: 0x1c130c, roughness: 0.8 }),
      velvet: makeDynMaterial({ color: 0x3a0306, roughness: 1.0 }),
      walnut: makeDynMaterial({ color: 0x4a2c18, roughness: 0.45 }),
      skin: makeDynMaterial({ color: 0xc58c6a, roughness: 0.6 }),
      cloth: makeDynMaterial({ color: 0x15151a, roughness: 0.9 }),
      straw: makeDynMaterial({ color: 0xd8c08a, roughness: 0.85 }),
      ribbon: makeDynMaterial({ color: 0x9a1018, roughness: 0.7 }),
    };
    // striped shirt (navy / white bands)
    const shirt = makeDynMaterial({ roughness: 0.85 });
    shirt.colorNode = mix(color(0xe8e6e0), color(0x1a2340), step(0.5, fract(positionLocal.y.mul(9.0))));
    M.shirt = shirt;
    const all = Object.values(M);
    for (const m of all) { m.envMap = env.tex; m.envMapRotation.copy(env.rot); m.envMapIntensity = 0.5; }
    const add = (g, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(g, m); o.position.set(x, y, z); o.castShadow = true; o.receiveShadow = true; this.group.add(o); return o; };
    const hull = hullGeometry();
    add(hull, M.lacquer); add(hull, M.inner);                      // glossy outside, matte black inside
    add(deckGeometry(2.35, HL - 0.05), M.lacquer);
    add(deckGeometry(-HL + 0.05, -3.05), M.lacquer);
    // cockpit floorboards and a red carpet runner
    const fl = new THREE.BoxGeometry(5.3, 1.0, 0.03); add(fl, M.floor, -0.35, yC(-0.35), 0.035);
    add(new THREE.BoxGeometry(4.4, 0.62, 0.012), M.velvet, -0.5, yC(-0.5), 0.056);
    // brass strip along both gunwales
    for (const sgn of [-1, 1]) {
      const pts = [];
      for (let i = 0; i <= 40; i++) { const x = -HL + 0.4 + (L - 0.8) * i / 40; pts.push(new THREE.Vector3(x, yC(x) + sgn * halfB(x) * (sgn > 0 ? 1.04 : 0.96), gunZ(x) + 0.012)); }
      add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 80, 0.013, 5, false), M.brass);
    }
    // bulkheads at the ends of the cockpit
    for (const x of [2.35, -3.05]) { const hb = halfB(x); const b = new THREE.BoxGeometry(0.03, hb * 1.9, gunZ(x) - keelZ(x) - 0.12); add(b, M.lacquer, x, yC(x), (gunZ(x) + keelZ(x) + 0.12) / 2); }
    // ferro (bow) and risso (stern)
    add(ferroGeometry(), M.steel, HL - 0.42, yC(HL - 0.4), gunZ(HL - 0.42) - 0.08);
    const ris = new THREE.TorusGeometry(0.09, 0.022, 6, 12, Math.PI * 1.4); ris.rotateX(Math.PI / 2);
    add(ris, M.steel, -HL + 0.06, yC(-HL), gunZ(-HL + 0.1) + 0.06);
    // armchair (poltrona) facing forward + cushions + brass seahorses
    const seatX = -1.75, fz = 0.05;
    add(new THREE.BoxGeometry(0.62, 0.66, 0.30), M.lacquer, seatX, -0.02, fz + 0.15);
    add(new THREE.BoxGeometry(0.58, 0.62, 0.10), M.velvet, seatX + 0.02, -0.02, fz + 0.35);
    add(new THREE.BoxGeometry(0.10, 0.66, 0.62), M.velvet, seatX - 0.30, -0.02, fz + 0.62);
    for (const s of [-1, 1]) {
      add(new THREE.BoxGeometry(0.58, 0.06, 0.24), M.velvet, seatX, -0.02 + s * 0.33, fz + 0.52);
      const horse = new THREE.LatheGeometry([0, 0.05, 0.07, 0.05, 0.035, 0.05, 0.03, 0].map((r, i) => new THREE.Vector2(r, i * 0.06)), 10);
      horse.rotateX(Math.PI / 2);
      add(horse, M.brass, seatX + 0.32, -0.02 + s * 0.40, fz + 0.30).rotation.set(0, 0, 0);
    }
    // a low bench facing aft and a stool, black lacquer with red cushions
    add(new THREE.BoxGeometry(0.42, 0.9, 0.16), M.lacquer, 0.55, yC(0.55), fz + 0.08);
    add(new THREE.BoxGeometry(0.40, 0.86, 0.07), M.velvet, 0.55, yC(0.55), fz + 0.19);
    add(new THREE.BoxGeometry(0.08, 0.9, 0.36), M.lacquer, 0.78, yC(0.78), fz + 0.34);
    add(new THREE.BoxGeometry(0.34, 0.34, 0.14), M.lacquer, -0.45, yC(-0.45) + 0.22, fz + 0.07);
    add(new THREE.BoxGeometry(0.32, 0.32, 0.06), M.velvet, -0.45, yC(-0.45) + 0.22, fz + 0.17);
    // forcola (walnut oarlock, starboard aft) and the oar
    this.forcola = new THREE.Vector3(-3.6, yC(-3.6) - halfB(-3.6) * 0.92, gunZ(-3.6));
    const fc = add(new THREE.BoxGeometry(0.16, 0.10, 0.78), M.walnut, this.forcola.x, this.forcola.y, this.forcola.z + 0.36);
    fc.rotation.z = 0.25;
    this.forcola.z += 0.72;
    // the oar rests in the forcola: handle ~1 m aft-up toward the gondolier, blade forward-down in the water
    const oarG = tube(4.25, 0.026); oarG.translate(4.25 / 2 - 1.05, 0, 0);
    const blade = new THREE.BoxGeometry(0.62, 0.02, 0.15); blade.translate(3.2 - 0.31, 0, 0);
    this.oar = new THREE.Group(); this.oar.position.copy(this.forcola);
    const oo = new THREE.Mesh(oarG, M.walnut); oo.castShadow = true; this.oar.add(oo);
    const bl = new THREE.Mesh(blade, M.walnut); bl.castShadow = true; this.oar.add(bl);
    this.group.add(this.oar);
    this.buildGondolier();
  }
  buildGondolier() {
    const M = this.mats;
    const G = this.gondolier = new THREE.Group();
    const stand = new THREE.Vector3(-4.85, yC(-4.85) + 0.05, gunZ(-4.85) + 0.02);
    G.position.copy(stand);
    const mk = (g, m) => { const o = new THREE.Mesh(g, m); o.castShadow = true; return o; };
    const cap = (r, h, m) => mk(new THREE.CapsuleGeometry(r, h, 4, 8), m);
    // hips pivot; legs below, torso above
    this.hips = new THREE.Group(); this.hips.position.set(0, 0, 0.92); G.add(this.hips);
    this.legs = [];
    for (const s of [-1, 1]) {
      const leg = cap(0.075, 0.78, M.cloth); leg.rotation.x = Math.PI / 2; leg.position.set(0.02 * s, s * 0.1, -0.46); this.hips.add(leg); this.legs.push(leg);
      const shoe = mk(new THREE.BoxGeometry(0.26, 0.10, 0.07), M.cloth); shoe.position.set(0.05, s * 0.1, -0.9); this.hips.add(shoe);
    }
    this.torso = new THREE.Group(); this.hips.add(this.torso);
    const chest = cap(0.17, 0.42, M.shirt); chest.rotation.x = Math.PI / 2; chest.scale.set(1, 0.75, 1); chest.position.z = 0.33; this.torso.add(chest);
    const head = mk(new THREE.SphereGeometry(0.105, 14, 10), M.skin); head.position.set(0.02, 0, 0.80); this.torso.add(head);
    const brim = mk(new THREE.CylinderGeometry(0.2, 0.2, 0.012, 20), M.straw); brim.rotation.x = Math.PI / 2; brim.position.set(0.02, 0, 0.88); this.torso.add(brim);
    const crown = mk(new THREE.CylinderGeometry(0.11, 0.115, 0.085, 18), M.straw); crown.rotation.x = Math.PI / 2; crown.position.set(0.02, 0, 0.93); this.torso.add(crown);
    const band = mk(new THREE.CylinderGeometry(0.117, 0.117, 0.03, 18), M.ribbon); band.rotation.x = Math.PI / 2; band.position.set(0.02, 0, 0.905); this.torso.add(band);
    // arms: upper + fore capsules, posed by 2-bone IK toward the oar handle
    this.arms = [];
    for (const s of [-1, 1]) {
      const sh = new THREE.Group(); sh.position.set(0.0, s * 0.2, 0.55); this.torso.add(sh);
      const up = cap(0.048, 0.26, M.shirt); const fo = cap(0.042, 0.24, M.skin);
      const upG = new THREE.Group(), foG = new THREE.Group();
      up.rotation.x = Math.PI / 2; up.position.z = -0.15; upG.add(up);
      fo.rotation.x = Math.PI / 2; fo.position.z = -0.14; foG.add(fo); foG.position.z = -0.30; upG.add(foG);
      sh.add(upG); this.arms.push({ sh, up: upG, fo: foG, side: s });
    }
    this.group.add(G);
  }
  // 2-bone IK: aim the upper arm so that the hand reaches `target` (gondola-local)
  solveArm(arm, target) {
    const a = 0.30, b = 0.30;
    const shW = new THREE.Vector3(); arm.sh.getWorldPosition(shW);
    const tW = target.clone().applyMatrix4(this.group.matrixWorld);
    const inv = new THREE.Matrix4().copy(arm.sh.matrixWorld).invert();
    const tl = tW.applyMatrix4(inv);                                  // target in shoulder space
    const d = Math.min(a + b - 1e-3, Math.max(0.05, tl.length()));
    const cosB = (a * a + b * b - d * d) / (2 * a * b);
    const elbow = Math.PI - Math.acos(Math.max(-1, Math.min(1, cosB)));
    const dir = tl.clone().normalize();
    // upper arm points along -z in its own frame; rotate -z onto dir, then lift by the shoulder angle
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, -1), dir);
    const cosA = (a * a + d * d - b * b) / (2 * a * d);
    const alpha = Math.acos(Math.max(-1, Math.min(1, cosA)));
    const side = new THREE.Vector3(0, 1, 0).applyQuaternion(q).normalize();
    const lift = new THREE.Quaternion().setFromAxisAngle(side, -alpha);
    arm.up.quaternion.copy(lift.multiply(q));
    arm.fo.quaternion.setFromAxisAngle(new THREE.Vector3(0, 1, 0), elbow);
  }
  // rowing pose: phase 0..1 (stroke then recovery); duck 0..1
  pose(phase, duck) {
    const w = phase * Math.PI * 2;
    const swing = Math.sin(w);                          // + = power stroke (handle forward), - = recovery
    const yaw = -0.30 + 0.20 * swing, pitch = 0.62 + 0.05 * Math.cos(w);
    this.oar.rotation.set(0, pitch, yaw, 'ZYX');
    this.torso.rotation.y = 0.22 + 0.16 * Math.max(0, swing) + 0.55 * duck;
    this.hips.position.z = 0.92 - 0.38 * duck;
    for (const l of this.legs) l.scale.set(1, 1 - 0.3 * duck, 1);
    this.group.updateMatrixWorld(true);
    // hands on the handle (aft of the forcola)
    const top = new THREE.Vector3(-1.0, 0, 0).applyEuler(this.oar.rotation).add(this.oar.position);
    const h1 = new THREE.Vector3(-0.58, 0, 0).applyEuler(this.oar.rotation).add(this.oar.position);
    this.solveArm(this.arms[0], top); this.solveArm(this.arms[1], h1);
  }
}

// ------------------------------------------------------------------------------------------------ ride
export class GondolaRide {
  constructor(scene, gondola, tiles, routes) {
    this.scene = scene; this.g = gondola; this.tiles = tiles; this.routes = routes;
    scene.add(gondola.group);
    this.s = 0; this.speed = 1.0; this.t = 0; this.duck = 0; this.mode = 'auto';
    this.pos = new THREE.Vector3(); this.heading = 0; this.vel = 0; this.yawRate = 0;
    this.steer = { thrust: 0, turn: 0 };
    this.setRoute(Object.keys(routes)[0]);
  }
  setRoute(name, s = 0) {
    const r = this.routes[name]; this.routeName = name;
    this.P = r.pts; this.len = r.length;
    // cumulative arc length
    this.cum = [0]; for (let i = 1; i < this.P.length; i++) this.cum.push(this.cum[i - 1] + Math.hypot(this.P[i][0] - this.P[i - 1][0], this.P[i][1] - this.P[i - 1][1]));
    this.s = s; this.mode = 'auto';
    const p = this.at(s); this.pos.set(p[0], p[1], 0); this.heading = this.dirAt(s);
  }
  at(s) {
    const c = this.cum, P = this.P; s = Math.max(0, Math.min(c[c.length - 1], s));
    let lo = 0, hi = c.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (c[m] <= s) lo = m; else hi = m; }
    const t = (s - c[lo]) / Math.max(1e-6, c[hi] - c[lo]);
    return [P[lo][0] + (P[hi][0] - P[lo][0]) * t, P[lo][1] + (P[hi][1] - P[lo][1]) * t];
  }
  dirAt(s) { const a = this.at(s - 2), b = this.at(s + 4); return Math.atan2(b[1] - a[1], b[0] - a[0]); }
  nameAt(s) { const n = this.routes[this.routeName].names; let cur = ''; for (const [d, nm] of n) if (d <= s) cur = nm; return cur; }
  water(x, y) { const w = this.tiles.sample(x, y); return w.water === undefined ? true : w.water; }
  update(dt) {
    const g = this.g;
    this.t += dt;
    const period = 2.4;
    const phase = (this.t / period) % 1;
    const surge = 1 + 0.18 * Math.sin(phase * Math.PI * 2 - 0.6);
    if (this.mode === 'auto') {
      const v = 1.5 * this.speed * surge;
      this.s = Math.min(this.len, this.s + v * dt);
      const p = this.at(this.s);
      this.pos.set(p[0], p[1], 0);
      let h = this.dirAt(this.s); let dh = h - this.heading; dh = Math.atan2(Math.sin(dh), Math.cos(dh));
      this.heading += dh * Math.min(1, dt * 2.5);
      this.vel = v;
    } else {
      // manual: thrust and turn, with drag; bow/stern stay in water
      this.vel += (this.steer.thrust * 1.1 - this.vel * 0.35) * dt;
      this.yawRate += (this.steer.turn * 0.45 - this.yawRate * 1.5) * dt;
      const nh = this.heading + this.yawRate * dt;
      const np = this.pos.clone().add(new THREE.Vector3(Math.cos(nh), Math.sin(nh), 0).multiplyScalar(this.vel * surge * dt));
      const ok = [5.0, 0, -5.0].every((d) => [-0.6, 0.6].every((o) => this.water(np.x + Math.cos(nh) * d - Math.sin(nh) * o, np.y + Math.sin(nh) * d + Math.cos(nh) * o)));
      if (ok) { this.pos.copy(np); this.heading = nh; } else { this.vel *= -0.2; this.yawRate *= 0.5; }
    }
    // duck under bridges: deck above the gondolier's head
    const sx = this.pos.x + Math.cos(this.heading) * -4.85, sy = this.pos.y + Math.sin(this.heading) * -4.85;
    let low = false;
    for (const d of [0, 1.2, 2.4]) {
      const w = this.tiles.sample(sx + Math.cos(this.heading) * d, sy + Math.sin(this.heading) * d);
      if (w.z != null && w.water && w.z < 3.4) low = true;
    }
    this.duck += ((low ? 1 : 0) - this.duck) * Math.min(1, dt * 3);
    // gentle motion: heave, roll with the stroke, pitch
    const roll = 0.012 * Math.sin(phase * Math.PI * 2) + 0.004 * Math.sin(this.t * 0.7);
    const pitch = 0.004 * Math.sin(this.t * 0.9 + 1.0);
    g.group.position.set(this.pos.x, this.pos.y, 0.015 * Math.sin(this.t * 1.3));
    g.group.rotation.set(roll, pitch, this.heading, 'ZYX');
    g.pose(phase, this.duck);
  }
  // seat camera: passenger in the armchair; yaw/pitch relative to the boat
  seatPose(cam, yaw, pitch) {
    const m = this.g.group.matrixWorld;
    const eye = new THREE.Vector3(-1.62, -0.02, 1.08).applyMatrix4(m);
    cam.position.copy(eye);
    const h = this.heading + yaw;
    const d = new THREE.Vector3(Math.cos(h) * Math.cos(pitch), Math.sin(h) * Math.cos(pitch), Math.sin(pitch));
    cam.up.set(0, 0, 1); cam.lookAt(eye.clone().add(d));
  }
}
