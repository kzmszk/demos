import * as THREE from 'three';

// Where the air rises you can see it: seeds, leaves and dust drift upward in slow spirals along the sunlit walls
// and over the hot roofs. A pool of point sprites is seeded each frame from a grid of updraft samples around the
// glider, so the columns appear wherever windUp() says there is lift.

const vert = /* glsl */`
  attribute float size; attribute float life; attribute vec3 tint;
  varying float vA; varying vec3 vT;
  void main(){
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float d = -mv.z;
    gl_PointSize = size * 1400.0 / max(d, 1.0);
    gl_PointSize = clamp(gl_PointSize, 3.0, 40.0);
    vA = smoothstep(0.0, 0.15, life) * smoothstep(1.0, 0.6, life) * smoothstep(900.0, 300.0, d);
    vT = tint;
    gl_Position = projectionMatrix * mv;
  }`;
const frag = /* glsl */`
  precision highp float;
  varying float vA; varying vec3 vT;
  void main(){
    vec2 c = gl_PointCoord - 0.5;
    float a = smoothstep(0.16, 0.03, abs(c.x)) * smoothstep(0.5, 0.2, abs(c.y)) * vA;
    gl_FragColor = vec4(vT, a * 0.95);
  }`;

export function makeThermals(scene, flight) {
  const N = 12000;
  const pos = new Float32Array(N * 3), vel = new Float32Array(N * 3), size = new Float32Array(N), life = new Float32Array(N), age = new Float32Array(N), tint = new Float32Array(N * 3), phase = new Float32Array(N);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('size', new THREE.BufferAttribute(size, 1));
  g.setAttribute('life', new THREE.BufferAttribute(life, 1).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('tint', new THREE.BufferAttribute(tint, 3));
  const mat = new THREE.ShaderMaterial({ vertexShader: vert, fragmentShader: frag, transparent: true, depthWrite: false, blending: THREE.NormalBlending });
  const pts = new THREE.Points(g, mat); pts.frustumCulled = false; pts.renderOrder = 3; scene.add(pts);
  let head = 0;
  const cols = [[1.3, 1.25, 1.05], [1.2, 1.1, 0.75], [0.75, 0.85, 0.40], [1.0, 0.8, 0.5]];
  // the sampling grid: 13 x 13 cells of 24 m around the glider, re-sampled a few rows per frame
  const G = 13, CELL = 24; const grid = new Float32Array(G * G); let row = 0;
  const cx0 = { x: 0, y: 0 };
  return {
    // active = false (on foot in the street, climbing): no new seeds; the ones in the air rise on and fade
    update(dt, time, active = true) {
      const f = flight.current; if (!f) return;
      const [px, py] = f.dataXY(); const z = f.p.y;
      const gx0 = Math.round(px / CELL) * CELL - (G - 1) / 2 * CELL, gy0 = Math.round(py / CELL) * CELL - (G - 1) / 2 * CELL;
      if (cx0.x !== gx0 || cx0.y !== gy0) { cx0.x = gx0; cx0.y = gy0; grid.fill(0); row = 0; }
      // sample two rows a frame, at the glider's height and 25 m below (the column is tall)
      for (let k = 0; k < 2; k++) {
        const j = row; row = (row + 1) % G;
        for (let i = 0; i < G; i++) { const x = gx0 + i * CELL, y = gy0 + j * CELL; grid[j * G + i] = Math.max(f.windUp(x, y, z), f.windUp(x, y, z - 30) * 0.9, f.windUp(x, y, z + 25) * 0.8); }
      }
      // spawn: cells with lift emit in proportion to it
      let budget = active ? Math.floor(700 * dt) : 0;
      for (let tries = 0; tries < 60 && budget > 0; tries++) {
        const i = Math.floor(Math.random() * G), j = Math.floor(Math.random() * G); const w = grid[j * G + i];
        if (w < 4.5) continue;
        const n = Math.min(budget, Math.ceil((w - 4.0) * 0.7)); budget -= n;
        for (let q = 0; q < n; q++) {
          const k = head; head = (head + 1) % N;
          const x = gx0 + i * CELL + (Math.random() - 0.5) * CELL * 1.2, y = gy0 + j * CELL + (Math.random() - 0.5) * CELL * 1.2;
          pos[k * 3] = x; pos[k * 3 + 1] = z - 75 + Math.random() * 115; pos[k * 3 + 2] = -y;
          vel[k * 3] = (Math.random() - 0.5) * 0.6; vel[k * 3 + 1] = 2.5 + w * 0.8 + Math.random() * 1.5; vel[k * 3 + 2] = (Math.random() - 0.5) * 0.6;
          size[k] = 0.6 + Math.random() * 0.9; age[k] = 0; life[k] = 0; phase[k] = Math.random() * 6.28;
          const c = cols[Math.floor(Math.random() * cols.length)]; tint[k * 3] = c[0]; tint[k * 3 + 1] = c[1]; tint[k * 3 + 2] = c[2];
        }
      }
      // move: rise, spiral a little, fade over 7 s
      for (let k = 0; k < N; k++) {
        if (life[k] >= 1) continue;
        age[k] += dt; life[k] = age[k] / 9.0;
        if (life[k] >= 1) { life[k] = 1; pos[k * 3 + 1] = -1e4; continue; }
        const sw = Math.sin(time * 1.7 + phase[k]) * 0.8, cw = Math.cos(time * 1.3 + phase[k]) * 0.8;
        pos[k * 3] += (vel[k * 3] + sw) * dt; pos[k * 3 + 1] += vel[k * 3 + 1] * dt; pos[k * 3 + 2] += (vel[k * 3 + 2] + cw) * dt;
      }
      g.attributes.position.needsUpdate = true; g.attributes.life.needsUpdate = true; g.attributes.size.needsUpdate = true; g.attributes.tint.needsUpdate = true;
    },
  };
}
