import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Saki, who always flies with you. The rigged model from tools/blender/saki.py (models/saki.glb, actions fly / sit /
// stand) is lit by the scene's own sun and hemisphere lights; until it has loaded, or if it is missing, a stand-in of
// primitives flies in her place. She holds a loose formation ahead of the player, swaps sides now and then, and sits
// beside him on the edge when he rests.

const vert = /* glsl */`
  uniform float time; uniform float flap;
  attribute float wave;
  varying vec3 vN; varying vec3 vC; varying vec3 vW; varying float vWave;
  void main(){
    vec3 p = position;
    p.y += (sin(time * 8.0 + p.x * 4.0) + 0.5 * sin(time * 12.5 + p.z * 7.0)) * 0.06 * wave * flap;
    p.z += sin(time * 6.0 + p.x * 3.0) * 0.04 * wave * flap;
    vec4 w = modelMatrix * vec4(p, 1.0); vW = w.xyz;
    vN = normalize(mat3(modelMatrix) * normal); vC = color; vWave = wave;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const frag = /* glsl */`
  precision highp float;
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol; uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos;
  varying vec3 vN; varying vec3 vC; varying vec3 vW; varying float vWave;
  void main(){
    vec3 N = normalize(vN); if(!gl_FrontFacing) N = -N;
    float dif = max(dot(N, sunDir), 0.0);
    vec3 light = sunCol * dif + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 1.0;
    light += sunCol * max(dot(-N, sunDir), 0.0) * 0.4 * step(0.01, vWave);
    vec3 rgb = vC * light;
    float d = length(vW - camPos); rgb = mix(rgb, fogCol, 1.0 - exp(-fogDen * d));
    gl_FragColor = vec4(rgb, 1.0);
  }`;

function colored(g, c, wave = 0) {
  const n = g.getAttribute('position').count; const col = new Float32Array(n * 3); const wv = new Float32Array(n).fill(wave);
  for (let i = 0; i < n; i++) { col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.setAttribute('wave', new THREE.BufferAttribute(wv, 1)); return g;
}

function capeWing(side) {
  const g = new THREE.PlaneGeometry(1, 1, 8, 6);
  const pos = g.getAttribute('position'); const n = pos.count; const wave = new Float32Array(n); const col = new Float32Array(n * 3);
  const c0 = new THREE.Color(0.82, 0.25, 0.13), c1 = new THREE.Color(0.60, 0.16, 0.08);
  for (let i = 0; i < n; i++) {
    const u = pos.getX(i) + 0.5, v = pos.getY(i) + 0.5;
    const x = side * u * (0.95 - v * 0.65), z = -0.05 + v * 1.05 + u * 0.15, y = -0.06 - v * 0.05 + Math.sin(u * Math.PI) * 0.06 * v;
    pos.setXYZ(i, x, y, z); wave[i] = Math.pow(u, 1.3) * (0.3 + 0.7 * v);
    const c = c0.clone().lerp(c1, (Math.sin(u * 11.0 + v * 3.0) * 0.5 + 0.5) * 0.5);
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  g.setAttribute('wave', new THREE.BufferAttribute(wave, 1)); g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.computeVertexNormals();
  return g;
}

// the stand-in: capsules and cylinders in the prone pose, facing -z
function standIn(uniforms) {
  const mat = new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag, vertexColors: true, side: THREE.DoubleSide });
  const skin = new THREE.Color(0.60, 0.40, 0.26), hair = new THREE.Color(0.05, 0.04, 0.04), top = new THREE.Color(0.74, 0.70, 0.60), wrap = new THREE.Color(0.42, 0.36, 0.26), leather = new THREE.Color(0.25, 0.16, 0.10);
  const g = new THREE.Group(); const M = (geo) => new THREE.Mesh(geo, mat);
  const torso = M(colored(new THREE.CapsuleGeometry(0.16, 0.42, 4, 10), top)); torso.rotation.x = Math.PI / 2;
  const belly = M(colored(new THREE.CapsuleGeometry(0.15, 0.1, 4, 10), skin)); belly.rotation.x = Math.PI / 2; belly.position.z = 0.25;
  const hips = M(colored(new THREE.CapsuleGeometry(0.17, 0.16, 4, 10), wrap)); hips.rotation.x = Math.PI / 2; hips.position.z = 0.46;
  const head = M(colored(new THREE.SphereGeometry(0.12, 12, 10), skin)); head.position.set(0, 0.05, -0.36);
  const hairCap = M(colored(new THREE.SphereGeometry(0.128, 12, 10, 0, Math.PI * 2, 0, Math.PI * 0.62), hair)); hairCap.position.set(0, 0.06, -0.35); hairCap.rotation.x = -0.5;
  g.add(torso, belly, hips, head, hairCap);
  for (const side of [-1, 1]) {
    const arm = M(colored(new THREE.CylinderGeometry(0.035, 0.045, 0.62, 8), skin)); arm.rotation.z = side * Math.PI / 2; arm.position.set(side * 0.44, 0.02, -0.08);
    const rod = M(colored(new THREE.CylinderGeometry(0.012, 0.012, 1.0, 6), leather)); rod.rotation.z = Math.PI / 2; rod.position.set(side * 0.55, -0.02, -0.07);
    const leg = M(colored(new THREE.CylinderGeometry(0.055, 0.075, 0.78, 8), skin)); leg.rotation.x = Math.PI / 2; leg.position.set(side * 0.1, -0.02, 0.95);
    const wing = M(capeWing(side)); wing.position.set(side * 0.12, 0.0, -0.03);
    g.add(arm, rod, leg, wing);
  }
  g.rotation.y = Math.PI;      // built head toward -z already; the stand-in's own frame has the head at -z, so face -z
  return g;
}

export function makeSaki(scene, shared) {
  const uniforms = { time: { value: 0 }, flap: { value: 0 }, sunDir: shared.sunDir, sunCol: shared.sunCol, skyCol: shared.skyCol, groundCol: shared.groundCol, fogCol: shared.fogCol, fogDen: shared.fogDen, camPos: shared.camPos };
  const root = new THREE.Group(); const body = new THREE.Group(); body.rotation.order = 'YXZ'; root.add(body); scene.add(root);
  let stand = standIn(uniforms); body.add(stand);
  // the model
  let model = null, mixer = null, actions = {}, current = null, headBone = null, neckBone = null, headTurn = 0, hairBones = [], glanceT = 12, armR = null, foreR = null, overridden = [];
  const clean = new Map();
  const qP = new THREE.Quaternion(), vAx = new THREE.Vector3();
  // rotate a bone about a world axis (the quaternion is local to the parent, so bring the axis into parent space)
  const swing = (bone, worldAxis, ang) => { if (!bone || !bone.parent) return; bone.parent.getWorldQuaternion(qP).invert(); vAx.copy(worldAxis).applyQuaternion(qP).normalize(); qTurn.setFromAxisAngle(vAx, ang); bone.quaternion.premultiply(qTurn); };
  let speaking = () => false;
  const axisX = new THREE.Vector3(1, 0, 0);
  const qTurn = new THREE.Quaternion(), axisY = new THREE.Vector3(0, 1, 0), axisZ = new THREE.Vector3(0, 0, 1);
  new GLTFLoader().load('models/saki.glb', (gltf) => {
    model = gltf.scene; model.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = false; o.frustumCulled = false; if (o.material) { o.material.side = THREE.DoubleSide;
      // glossy black hair: the glb ships it matte
      if (/hair/i.test(o.material.name)) { o.material.roughness = 0.42; o.material.metalness = 0.0; if (o.material.color) o.material.color.multiplyScalar(0.8); } } } });
    // GLTFLoader strips the dots from node names ('upperarm.R' -> 'upperarmR', 'hair.001' -> 'hair001')
    const bone = (n) => model.getObjectByName(n) || model.getObjectByName(n.replace(/\./g, ''));
    headBone = bone('head'); neckBone = bone('neck');
    hairBones = ['hair.001', 'hair.002', 'hair.003', 'hair.004'].map(bone).filter(Boolean);
    armR = bone('upperarm.R'); foreR = bone('forearm.R');
    overridden = [headBone, neckBone, armR, foreR, ...hairBones].filter(Boolean);
    mixer = new THREE.AnimationMixer(model);
    for (const clip of gltf.animations) { const a = mixer.clipAction(clip); a.setLoop(THREE.LoopRepeat); actions[clip.name] = a; }
    body.remove(stand); body.add(model); play('fly', 0);
    console.log('saki model', gltf.animations.map((c) => c.name), Object.keys(actions));
  }, undefined, (e) => console.warn('saki model missing, keeping the stand-in', e?.message || e));
  function play(name, fade = 0.5) {
    const a = actions[name]; if (!a || a === current) return;
    a.reset().fadeIn(fade).play(); if (current) current.fadeOut(fade); current = a;
  }
  const state = { pos: new THREE.Vector3(), vel: new THREE.Vector3(), side: 1, sideT: 0, phase: Math.random() * 10 };
  const tmp = new THREE.Vector3(), target = new THREE.Vector3(), vFwd = new THREE.Vector3();
  let ARM_SWING = 0.75; window.__armSwing = (v) => { ARM_SWING = v; };
  const lerpAngle = (a, b, t) => a + Math.atan2(Math.sin(b - a), Math.cos(b - a)) * t;
  return {
    root, state, get model() { return model; },
    set speaking(fn) { speaking = fn; },
    place(p) { state.pos.copy(p); state.vel.set(0, 0, 0); root.position.copy(p); },
    update(f, dt, time) {
      uniforms.time.value = time;
      // hand in hand the clip almost stands still: its arm flex and body wave were the 1 Hz shake he saw in her face
      if (current) current.timeScale = f.hand ? 0.12 : 1;
      // the mixer only rewrites a bone when the clip value changes; with the clip nearly frozen it often does not,
      // and an override multiplied onto the bone would then accumulate frame after frame (the arm spun, the head
      // flapped). So: restore the clip's own value first, let the mixer write, remember the clean value, then override.
      for (const [b, qc] of clean) b.quaternion.copy(qc);
      mixer?.update(dt);
      for (const b of overridden) { if (!b) continue; let qc = clean.get(b); if (!qc) { qc = new THREE.Quaternion(); clean.set(b, qc); } qc.copy(b.quaternion); }
      if (f.state === 'rest') {
        // sitting beside him on the edge, a little ahead so he sees her when he looks right
        // on the edge beside him, a little ahead so she is in the picture when he looks half-right
        target.copy(f.p).addScaledVector(f.right, 1.35).addScaledVector(f.forward, 1.0); target.y = f.p.y - 1.65 + (model ? 0.0 : 0.62);
        // the moment he lands she is already there beside him (no fly-in from wherever the formation left her)
        if (!state.wasRest) state.pos.copy(target); else state.pos.lerp(target, Math.min(1, dt * 3));
        state.vel.set(0, 0, 0);
        const yaw = f.heading - 0.55;             // beside him, turned a little his way (her left); the sit animation turns her head further
        if (model) { play('sit'); body.rotation.set(0, lerpAngle(body.rotation.y, -yaw, Math.min(1, dt * 4)), 0); }
        else { body.rotation.set(1.45, yaw, 0); }
        uniforms.flap.value = 0.05;
      } else if (f.hand) {
        // hand in hand: she flies at his left, her right hand in his left, and turns her face to him
        // locked to him once she has slid into place: any lag here reads as her image shaking
        const c = f.closeBlend;                                             // 0 hand in hand, 1 drawn in, face to face
        // the model's origin is at her hips and her head is ~0.75 m ahead of it: place her so her face is beside his
        target.copy(f.p).addScaledVector(f.right, -THREE.MathUtils.lerp(1.35, 0.62, c)).addScaledVector(f.forward, THREE.MathUtils.lerp(0.0, -0.45, c)); target.y -= THREE.MathUtils.lerp(0.38, 0.06, c);
        if (f.handT < 1.2) state.pos.lerp(target, Math.min(1, dt * 2.5)); else state.pos.copy(target);
        state.vel.copy(f.v);
        // no bank on either of them while they hold hands: the two roll axes differ by the gaze, and the difference shook her image
        body.rotation.set((f.camPitch ?? f.gamma) * 0.8, model ? -f.heading : f.heading, (model ? -1 : 1) * c * 0.3);
        if (model) play('fly');
        uniforms.flap.value = Math.min(1, f.speed / 18);
      } else {
        state.sideT += dt; if (state.sideT > 18 + 10 * Math.sin(state.phase)) { state.sideT = 0; state.side *= -1; }
        const ahead = 7.5 + 2.5 * Math.sin(time * 0.17 + state.phase), side = state.side * (3.2 + 1.2 * Math.sin(time * 0.23)), up = 0.2 + 1.2 * Math.sin(time * 0.31 + 1.0);
        target.copy(f.p).addScaledVector(f.forward, ahead).addScaledVector(f.right, side); target.y += up;
        tmp.copy(target).sub(state.pos); const d = tmp.length();
        // she keeps his speed and closes on the slot at a cape's pace (the old cap of 4 + 0.9 d left her trailing behind him)
        const want = tmp.multiplyScalar(Math.min(1, 1 / Math.max(d, 1e-3)) * Math.max(3, f.speed + THREE.MathUtils.clamp(d * 0.9 - 2, -5, 9)));
        state.vel.lerp(want, Math.min(1, dt * 1.6));
        state.pos.addScaledVector(state.vel, dt);
        const v = state.vel; const sp = v.length();
        if (sp > 0.5) {
          const heading = Math.atan2(v.x, -v.z), pitch = Math.asin(THREE.MathUtils.clamp(v.y / sp, -1, 1));
          const latAcc = (want.x - v.x) * Math.cos(heading) + (want.z - v.z) * Math.sin(heading);
          body.rotation.set(pitch * 0.8, model ? -heading : heading, THREE.MathUtils.clamp(latAcc * 0.08, -0.9, 0.9) * (model ? -1 : 1));
        }
        if (model) play('fly');
        uniforms.flap.value = Math.min(1, sp / 18);
      }
      root.position.copy(state.pos); state.wasRest = f.state === 'rest';
      // the head: after the animation, twist it toward him when they hold hands (her right), back when they let go
      // she looks ahead; she turns to him when she speaks, when they are drawn close, and for a glance now and then
      glanceT -= dt; if (glanceT < -2.5) glanceT = 14 + Math.random() * 16;
      const wantTurn = f.hand && (f.close || speaking() || glanceT < 0) ? 1 : 0;
      headTurn += (wantTurn - headTurn) * Math.min(1, dt * (wantTurn ? 2.5 : 1.5));
      // hand in hand: her right arm comes down and back toward his hand (beside and below his eyes) instead of
      // pointing at the camera; her forearm follows
      if (f.handBlend > 0.01 && armR) {
        root.updateMatrixWorld(true);
        const fwd = vFwd.set(Math.sin(f.heading), 0, -Math.cos(f.heading));          // her flight direction (world)
        swing(armR, fwd, f.handBlend * ARM_SWING);
        swing(foreR, fwd, f.handBlend * ARM_SWING * 0.3);
        root.updateMatrixWorld(true);
      }
      // the ponytail (if the model has one): a wave travelling down the chain, stronger with speed, on top of the clip
      if (hairBones.length) {
        const sp = f.state === 'rest' ? 0 : Math.min(1, f.speed / 20) * (f.hand ? 0.35 : 1);
        hairBones.forEach((b, i) => {
          const ph = time * (3.5 + sp * 3) - i * 0.9;
          qTurn.setFromAxisAngle(axisX, Math.sin(ph) * (0.04 + 0.08 * sp) * (0.5 + i * 0.3)); b.quaternion.multiply(qTurn);
          qTurn.setFromAxisAngle(axisZ, Math.sin(ph * 0.7 + 1.3) * (0.03 + 0.05 * sp)); b.quaternion.multiply(qTurn);
        });
      }
      if (headBone && headTurn > 0.01) {
        const c = f.closeBlend;
        qTurn.setFromAxisAngle(axisY, -(0.95 + 0.35 * c) * headTurn); headBone.quaternion.multiply(qTurn);
        qTurn.setFromAxisAngle(axisZ, (0.25 + 0.2 * c) * headTurn); headBone.quaternion.multiply(qTurn);
        if (neckBone) { qTurn.setFromAxisAngle(axisY, -(0.35 + 0.2 * c) * headTurn); neckBone.quaternion.multiply(qTurn); }
      }
    },
    get headTurn() { return headTurn; },
  };
}
