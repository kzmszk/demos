import * as THREE from 'three';

// The player's own body as seen from his eyes: two bare forearms with leather wrist straps. He flies on wings now
// (on his back, out of sight), so there is no cape in the picture any more. Attached to the camera; the arms
// spread as the wings open, tilt with the bank and lift with the flare.

const vert = /* glsl */`
  uniform float time; uniform float flap; uniform float open;
  attribute float wave;          // 0 at the wrist, 1 along the free edge: how much the fabric may move
  varying vec3 vN; varying vec3 vC; varying float vW; varying vec2 vFold;
  void main(){
    vec3 p = position; vFold = vec2(p.x * 2.0 + p.z, p.z * 3.0);
    float w = wave * open;
    p.y += (sin(time * 9.0 + p.x * 6.0) * 0.5 + sin(time * 13.0 + p.z * 9.0)) * 0.035 * flap * w;
    p.x += sin(time * 7.0 + p.z * 5.0) * 0.02 * flap * w;
    vW = wave; vN = normalize(normalMatrix * normal); vC = color;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
  }`;
const frag = /* glsl */`
  precision highp float;
  uniform vec3 sunDirView; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  varying vec3 vN; varying vec3 vC; varying float vW; varying vec2 vFold;
  void main(){
    vec3 N = normalize(vN); if(!gl_FrontFacing) N = -N;
    // folds and sun-bleach along the fabric
    float fold = sin(vFold.x * 9.0 + sin(vFold.y * 5.0) * 2.0) * 0.5 + 0.5;
    vec3 base = mix(vC * 0.78, vC * 1.12, fold) ; base = mix(base, vec3(0.80, 0.52, 0.40), smoothstep(0.75, 1.0, vW) * 0.4);
    float dif = max(dot(N, sunDirView), 0.0);
    vec3 light = sunCol * dif * 0.9 + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 1.1;
    // thin cloth lets the sun through
    light += sunCol * max(dot(-N, sunDirView), 0.0) * 0.35 * step(0.01, vW);
    gl_FragColor = vec4(base * light, 1.0);
  }`;

function arm(side) {
  // forearm from just below the eye out to the hand, with a dark strap at the wrist
  const group = new THREE.Group();
  const skin = new THREE.Color(0.50, 0.33, 0.21), strap = new THREE.Color(0.20, 0.13, 0.08);
  const seg = (r0, r1, len, c) => {
    const g = new THREE.CylinderGeometry(r1, r0, len, 10, 1); const n = g.getAttribute('position').count; const col = new Float32Array(n * 3); const wave = new Float32Array(n);
    for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.setAttribute('wave', new THREE.BufferAttribute(wave, 1)); return g;
  };
  const fore = new THREE.Mesh(seg(0.040, 0.031, 0.62, skin)); fore.position.set(0, 0, -0.31); fore.rotation.x = Math.PI / 2;
  const band = new THREE.Mesh(seg(0.036, 0.036, 0.06, strap)); band.position.set(0, 0, -0.56); band.rotation.x = Math.PI / 2;
  const hand = new THREE.Mesh(seg(0.036, 0.024, 0.10, skin)); hand.position.set(0, 0, -0.66); hand.rotation.x = Math.PI / 2;
  group.add(fore, band, hand);
  return group;
}

export function makeBody(camera, shared) {
  const uniforms = { time: { value: 0 }, flap: { value: 0 }, open: { value: 0 }, sunDirView: { value: new THREE.Vector3() }, sunCol: shared.sunCol, skyCol: shared.skyCol, groundCol: shared.groundCol };
  const mat = new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag, vertexColors: true, side: THREE.DoubleSide });
  const root = new THREE.Group(); camera.add(root);
  const sides = [-1, 1].map((side) => {
    const pivot = new THREE.Group(); root.add(pivot);
    const a = arm(side); a.traverse((m) => { if (m.isMesh) m.material = mat; });
    pivot.add(a);
    return { side, pivot, arm: a };
  });
  const v = new THREE.Vector3();
  return {
    root,
    update(f, dt) {
      uniforms.time.value += dt;
      const flying = f.state !== 'rest';
      const open = flying ? f.open : 0;
      uniforms.open.value += (open - uniforms.open.value) * Math.min(1, dt * (flying ? 4 : 9));        // folds quickly once you stand
      uniforms.flap.value = Math.min(1, f.speed / 20) * (0.6 + 0.4 * Math.min(1, Math.abs(f.gload - 1))) * (1 - 0.7 * (f.handBlend || 0));
      uniforms.sunDirView.value.copy(shared.sunDir.value).transformDirection(camera.matrixWorldInverse);
      for (const s of sides) {
        const o = uniforms.open.value;
        // at rest the arms hang low and inward; open, they reach out to the sides, bank with the roll, rise in the flare
        // the hands sit just inside the frame corners; the forearms run in from below the eyes
        const hold = s.side < 0 ? (f.handBlend || 0) : 0;            // the left hand holds hers
        const spread = THREE.MathUtils.lerp(THREE.MathUtils.lerp(0.26, 0.46, o), 0.74, hold) * s.side;
        const lift = THREE.MathUtils.lerp(THREE.MathUtils.lerp(-0.62, -0.42, o) + (f.flareVis * 0.10 - f.aoaVis * 0.004) * (1 - (f.handBlend || 0)), -0.30, hold) + (flying ? Math.sin(uniforms.time.value * 2.1 + s.side) * 0.012 : 0);
        s.arm.position.set(spread, lift, THREE.MathUtils.lerp(0.12, -0.32, hold));
        s.arm.rotation.set(THREE.MathUtils.lerp(0.32 + (1 - o) * 0.35, 0.05, hold), -s.side * THREE.MathUtils.lerp(0.62 - o * 0.15, 1.25, hold), s.side * 0.1);
        s.pivot.rotation.z = -f.roll * 0.25 * (s.side > 0 ? 1 : 1);
        s.pivot.position.y = -f.roll * s.side * 0.06;
      }
    },
  };
}
