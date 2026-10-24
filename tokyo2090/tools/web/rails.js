import * as THREE from 'three';
import { shadowGLSL } from './light.js';

// The railways: every track above ground from OSM (data/rails.json, gen/rails.py) as a raised ballast bed with
// sleepers and two rusted rails, concrete viaduct decks and piers where the line is on a bridge, catenary masts along
// the electrified lines, and a few trains that stopped where they were in 2030. Seen from the air the lines are what
// makes the map readable (the Yamanote loop, the Chuo line, Odakyu...). Data axes: x east, y north, z up.

const common = /* glsl */`
  #include <packing>
  varying vec3 vW; varying vec3 vN;
  ${shadowGLSL}
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<4;k++){ v += a*noise(p); p = p*2.03 + 7.1; a *= 0.5; } return v; }
  vec3 shade(vec3 col, vec3 N, float ao){
    float dif = max(dot(N, sunDir), 0.0), dd = length(vW - camPos);
    if (dif > 0.0 && dd < 650.0) dif *= mix(shadowAt(vW, N, sunDir), 1.0, smoothstep(450.0, 650.0, dd));
    vec3 light = sunCol * dif + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9 * ao;
    float f = 1.0 - exp(-fogDen * dd);
    return mix(col * light, fogCol, f);
  }
  vec3 grass(vec2 p){ return mix(vec3(0.20, 0.25, 0.10), vec3(0.33, 0.36, 0.16), noise(p * 1.7)) * (0.75 + 0.4 * noise(p * 6.0)); }`;

const trackVert = /* glsl */`
  attribute vec2 aUV; attribute float aPart; varying vec2 vUV; varying float vPart; varying vec3 vW; varying vec3 vN;
  void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; vN = normal; vUV = aUV; vPart = aPart; gl_Position = projectionMatrix * viewMatrix * w; }`;
const trackFrag = /* glsl */`
  precision highp float; varying vec2 vUV; varying float vPart;
  ${common}
  void main(){
    vec3 N = normalize(vN); float u = vUV.x, s = vUV.y; vec2 xz = vW.xz; float ao = 1.0;
    float over = smoothstep(0.35, 0.75, fbm(xz * 0.08) * 0.7 + fbm(xz * 0.9) * 0.45);     // sixty years of weeds
    vec3 col;
    if (vPart < 0.5) {
      // ballast, sleepers every 0.6 m across the middle, rust stains under the rails
      vec3 stone = mix(vec3(0.30, 0.28, 0.26), vec3(0.44, 0.41, 0.37), noise(xz * 9.0)) * (0.8 + 0.35 * noise(xz * 31.0));
      float sl = step(abs(u), 1.05) * step(fract(s / 0.6), 0.36);
      vec3 sleeper = mix(vec3(0.50, 0.48, 0.44), vec3(0.38, 0.36, 0.33), noise(vec2(floor(s / 0.6), 3.0)));
      col = mix(stone, sleeper, sl);
      col = mix(col, vec3(0.30, 0.17, 0.09), smoothstep(0.22, 0.0, abs(abs(u) - 0.57)) * 0.55);
      col = mix(col, grass(xz), clamp(over * (abs(u) > 1.2 ? 1.0 : 0.8) + step(1.6, abs(u)) * 0.4, 0.0, 0.95));
      ao = 1.0 - 0.25 * smoothstep(0.6, 0.45, abs(abs(u) - 0.57) + 0.4) * sl;
    } else if (vPart < 2.5) {
      // the rails: rust, the running surface a little lighter where it was polished last
      col = mix(vec3(0.24, 0.13, 0.07), vec3(0.40, 0.22, 0.11), noise(vec2(s * 2.0, u * 9.0)));
      if (vPart < 1.5) col = mix(col, vec3(0.42, 0.33, 0.27), 0.35);
      col = mix(col, grass(xz), over * 0.45 * step(0.62, noise(vec2(s * 0.7, u))));
    } else {
      // concrete deck and piers: stains running down, moss on the top surfaces, vines from the ground up the piers
      col = mix(vec3(0.50, 0.48, 0.44), vec3(0.62, 0.60, 0.55), noise(xz * 0.7 + vW.y * 0.3)) * (0.82 + 0.25 * noise(vec2(xz.x + xz.y, vW.y * 4.0)));
      col *= 1.0 - 0.25 * smoothstep(0.5, 0.9, noise(vec2((xz.x + xz.y) * 2.0, vW.y * 0.15)));
      float moss = N.y > 0.6 ? 0.7 : smoothstep(0.55, 0.85, fbm(vec2(xz.x + xz.y, vW.y) * 0.4)) * 0.8;
      col = mix(col, grass(xz + vW.y), moss * smoothstep(0.3, 0.7, over + 0.25));
    }
    gl_FragColor = vec4(shade(col, N, ao), 1.0);
  }`;

const mastVert = /* glsl */`
  varying vec3 vW; varying vec3 vN; varying float vH;
  void main(){ mat4 M = modelMatrix * instanceMatrix; vec4 w = M * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(M) * normal); vH = position.y; gl_Position = projectionMatrix * viewMatrix * w; }`;
const mastFrag = /* glsl */`
  precision highp float; varying float vH;
  ${common}
  void main(){
    vec3 N = normalize(vN);
    vec3 col = mix(vec3(0.26, 0.15, 0.09), vec3(0.42, 0.30, 0.20), noise(vec2(vW.x + vW.z, vW.y * 3.0)));
    float vine = smoothstep(0.35, 0.65, noise(vec2((vW.x + vW.z) * 3.0, vW.y * 0.6)) + 0.55 - vH * 0.13);
    col = mix(col, grass(vW.xz + vW.y), vine);
    gl_FragColor = vec4(shade(col, N, 1.0), 1.0);
  }`;

const carVert = /* glsl */`
  attribute float aPart; varying float vPart; varying vec3 vL; varying vec3 vCol; varying vec3 vW; varying vec3 vN; varying float vSeed;
  void main(){ mat4 M = modelMatrix * instanceMatrix; vec4 w = M * vec4(position, 1.0); vW = w.xyz; vN = normalize(mat3(M) * normal);
    vL = position; vPart = aPart; vCol = instanceColor; vSeed = fract(M[3].x * 0.137 + M[3].z * 0.311); gl_Position = projectionMatrix * viewMatrix * w; }`;
const carFrag = /* glsl */`
  precision highp float; varying float vPart; varying vec3 vL; varying vec3 vCol; varying float vSeed;
  ${common}
  void main(){
    vec3 N = normalize(vN); float ao = 1.0; vec3 col;
    float y = vL.y, z = vL.z, side = step(1.3, abs(vL.x));
    if (vPart > 0.5) { col = mix(vec3(0.07, 0.05, 0.04), vec3(0.20, 0.10, 0.05), noise(vL.xz * 3.0 + vSeed * 9.0)); ao = 0.6; }
    else {
      // stainless body gone dull, grime streaks running down from the roof, a band in the line's colour
      col = mix(vec3(0.46, 0.47, 0.46), vec3(0.58, 0.58, 0.56), noise(vec2(z * 0.6, y * 0.3) + vSeed * 13.0));
      col *= 1.0 - 0.28 * smoothstep(0.45, 0.85, noise(vec2(z * 3.1 + vSeed * 7.0, y * 0.25)));
      if (side > 0.5) {
        // four doors a side; between them the bays of windows, each split by a pillar; a few panes broken
        float door = 0.0, dc = 0.0;
        for (int k = 0; k < 4; k++) { float c = -7.2 + 4.8 * float(k); if (abs(z - c) < 0.65) { door = 1.0; dc = c; } }
        float pane = floor((z + 9.75) / 1.6), pz = fract((z + 9.75) / 1.6);
        float win = step(1.3, y) * step(y, 2.12) * (1.0 - door) * step(abs(z), 9.15) * step(0.06, pz) * step(pz, 0.94);
        float dwin = door * step(1.38, y) * step(y, 2.05) * step(0.05, abs(z - dc)) * step(abs(z - dc), 0.55);
        float band = step(2.2, y) * step(y, 2.4) * (1.0 - door) + door * step(0.18, y) * step(y, 2.3) * step(0.58, abs(z - dc)) ;
        col = mix(col, vCol * 0.8, clamp(band, 0.0, 1.0));
        if (door > 0.5) col *= 0.8 + 0.2 * step(0.04, abs(z - dc));
        float glass = max(win, dwin);
        vec3 V = normalize(camPos - vW); float fr = pow(1.0 - abs(dot(V, N)), 3.0);
        float broken = step(0.7, hash(vec2(pane, vSeed * 17.0 + (vL.x > 0.0 ? 1.0 : 0.0))));
        vec3 gcol = mix(vec3(0.05, 0.06, 0.065), skyCol * 0.45, 0.25 + 0.6 * fr);
        if (broken > 0.5) gcol = vec3(0.025, 0.022, 0.02) + vec3(0.04, 0.05, 0.02) * noise(vL.zy * 4.0);
        col = mix(col, gcol, glass);
        ao *= 1.0 - 0.3 * glass;
      } else if (N.y > 0.5 || y > 2.9) {
        col = mix(vec3(0.36, 0.35, 0.33), grass(vW.xz), smoothstep(0.35, 0.7, fbm(vW.xz * 0.6 + vSeed * 5.0)));    // leaf litter and moss on the roof
      } else {
        col = mix(col, vec3(0.05), step(abs(vL.x), 0.5) * step(0.2, y) * step(y, 2.0));                     // the gangway door
      }
      // rust bleeding from the seams, vines climbing from the ballast
      col = mix(col, vec3(0.32, 0.17, 0.08), smoothstep(0.62, 0.8, noise(vec2(z * 1.7, y * 0.9) + vSeed * 3.0)) * 0.6);
      float vine = smoothstep(0.4, 0.7, noise(vec2(z * 0.9 + vSeed * 11.0, y * 0.5)) + 0.45 - y * 0.22);
      col = mix(col, grass(vW.xz + y), vine * 0.9);
    }
    gl_FragColor = vec4(shade(col, N, ao), 1.0);
  }`;

export function makeRails(scene, shared, { data, ground, walker }) {
  const group = new THREE.Group(); group.name = 'rails'; scene.add(group);
  const uni = { ...shared };
  const trackMat = new THREE.ShaderMaterial({ uniforms: uni, vertexShader: trackVert, fragmentShader: trackFrag, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2, side: THREE.DoubleSide });
  const CH = 600, chunks = new Map();
  const chunk = (x, y) => { const k = Math.floor(x / CH) + ',' + Math.floor(y / CH); let c = chunks.get(k); if (!c) chunks.set(k, c = { P: [], N: [], UV: [], part: [], I: [] }); return c; };
  // push a quad strip section: a list of cross-section corners [u, dz] at two stations a, b
  function quad(c, A, B, C, D, n, uvA, uvB, uvC, uvD, part) {
    const base = c.P.length / 3;
    for (const [p, uv] of [[A, uvA], [B, uvB], [C, uvC], [D, uvD]]) { c.P.push(p[0], p[2], -p[1]); c.N.push(n[0], n[2], -n[1]); c.UV.push(uv[0], uv[1]); c.part.push(part); }
    c.I.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const tracks = [], masts = [], mastGrid = new Set();
  for (const t of data.tracks) {
    const p = t.p, n = p.length / 3; if (n < 2) continue;
    const X = new Float64Array(n), Y = new Float64Array(n), Z = new Float64Array(n), B = new Uint8Array(n), S = new Float64Array(n);
    for (let i = 0; i < n; i++) { X[i] = p[i * 3]; Y[i] = p[i * 3 + 1]; const bz = p[i * 3 + 2]; B[i] = bz > -900 ? 1 : 0; Z[i] = B[i] ? bz : ground(X[i], Y[i]); if (i) S[i] = S[i - 1] + Math.hypot(X[i] - X[i - 1], Y[i] - Y[i - 1]); }
    tracks.push({ X, Y, Z, S, n, l: t.l });
    // across direction at each station (left of travel)
    const LX = new Float64Array(n), LY = new Float64Array(n);
    for (let i = 0; i < n; i++) { const a = Math.max(0, i - 1), b = Math.min(n - 1, i + 1); let dx = X[b] - X[a], dy = Y[b] - Y[a]; const l = Math.hypot(dx, dy) || 1; LX[i] = -dy / l; LY[i] = dx / l; }
    const at = (i, u, dz) => [X[i] + LX[i] * u, Y[i] + LY[i] * u, Z[i] + dz];
    const mono = t.k === 2;
    for (let i = 0; i < n - 1; i++) {
      const j = i + 1, c = chunk((X[i] + X[j]) / 2, (Y[i] + Y[j]) / 2), s0 = S[i], s1 = S[j];
      const tx = X[j] - X[i], ty = Y[j] - Y[i], tl = Math.hypot(tx, ty) || 1;
      const nl = [-ty / tl * 0.0, 0, 1];
      if (!mono) {
        // ballast: shoulders and top (the edges sit 3 cm proud of the ground so they never sink into it)
        const sec = [[-2.2, 0.03], [-1.45, 0.28], [1.45, 0.28], [2.2, 0.03]];
        for (let k = 0; k < 3; k++) {
          const [u0, z0] = sec[k], [u1, z1] = sec[k + 1];
          const du = u1 - u0, dz = z1 - z0, l = Math.hypot(du, dz); const nn = [LX[i] * -dz / l, LY[i] * -dz / l, du / l];
          quad(c, at(i, u0, z0), at(j, u0, z0), at(j, u1, z1), at(i, u1, z1), nn, [u0, s0], [u0, s1], [u1, s1], [u1, s0], 0);
        }
        // the rails: head (top) and both faces, 15 cm above the sleepers
        for (const r of [-0.57, 0.57]) {
          quad(c, at(i, r - 0.03, 0.43), at(j, r - 0.03, 0.43), at(j, r + 0.03, 0.43), at(i, r + 0.03, 0.43), nl, [r, s0], [r, s1], [r, s1], [r, s0], 1);
          for (const sd of [-1, 1]) {
            const u = r + sd * 0.03, nn = [LX[i] * sd, LY[i] * sd, 0];
            if (sd > 0) quad(c, at(i, u, 0.29), at(j, u, 0.29), at(j, u, 0.43), at(i, u, 0.43), nn, [u, s0], [u, s1], [u, s1], [u, s0], 2);
            else quad(c, at(i, u, 0.43), at(j, u, 0.43), at(j, u, 0.29), at(i, u, 0.29), nn, [u, s0], [u, s1], [u, s1], [u, s0], 2);
          }
        }
      }
      // a bridge: the deck under the ballast, its sides and parapets, a pier every ~16 m
      if (B[i] && B[j]) {
        const w = mono ? 0.45 : 2.6, top = mono ? 0.4 : 0.0, bot = mono ? -1.2 : -1.1;
        for (const sd of [-1, 1]) {
          const nn = [LX[i] * sd, LY[i] * sd, 0];
          if (sd > 0) quad(c, at(i, w, bot), at(j, w, bot), at(j, w, top + (mono ? 0 : 0.9)), at(i, w, top + (mono ? 0 : 0.9)), nn, [w, s0], [w, s1], [w, s1], [w, s0], 3);
          else quad(c, at(i, -w, top + (mono ? 0 : 0.9)), at(j, -w, top + (mono ? 0 : 0.9)), at(j, -w, bot), at(i, -w, bot), nn, [-w, s0], [-w, s1], [-w, s1], [-w, s0], 3);
        }
        quad(c, at(i, -w, bot), at(j, -w, bot), at(j, w, bot), at(i, w, bot), [0, 0, -1], [0, s0], [0, s1], [0, s1], [0, s0], 3);
        if (mono) quad(c, at(i, -w, top), at(j, -w, top), at(j, w, top), at(i, w, top), [0, 0, 1], [0, s0], [0, s1], [0, s1], [0, s0], 3);
        else for (const sd of [-1, 1]) { const u = sd * 2.6, ui = sd * 2.4;
          quad(c, at(i, ui, 0.9), at(j, ui, 0.9), at(j, u, 0.9), at(i, u, 0.9), [0, 0, 1], [u, s0], [u, s1], [u, s1], [u, s0], 3); }
        for (let sp = Math.ceil(s0 / 16) * 16; sp < s1; sp += 16) {
          const f = (sp - s0) / (s1 - s0), px = X[i] + tx * f, py = Y[i] + ty * f, pz = Z[i] + (Z[j] - Z[i]) * f + bot, g = ground(px, py);
          if (pz - g < 1.0) continue;
          const ax = tx / tl, ay = ty / tl, hw = mono ? 0.5 : 1.6, hd = 0.6;
          const cs = [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd]].map(([a, b]) => [px + LX[i] * a + ax * b, py + LY[i] * a + ay * b]);
          for (let k = 0; k < 4; k++) { const [a0, b0] = cs[k], [a1, b1] = cs[(k + 1) % 4]; const ex = a1 - a0, ey = b1 - b0, el = Math.hypot(ex, ey);
            quad(c, [a0, b0, g - 0.5], [a1, b1, g - 0.5], [a1, b1, pz], [a0, b0, pz], [ey / el, -ex / el, 0], [0, g], [1, g], [1, pz], [0, pz], 4); }
        }
      }
      // catenary masts every 50 m on the electrified lines, one per corridor where tracks run side by side
      if (t.e && !mono) for (let sp = Math.ceil(s0 / 50) * 50; sp < s1; sp += 50) {
        const f = (sp - s0) / (s1 - s0), mx = X[i] + tx * f + LX[i] * 2.5, my = Y[i] + ty * f + LY[i] * 2.5, mz = (B[i] ? Z[i] + (Z[j] - Z[i]) * f : ground(mx, my));
        const gk = Math.round(mx / 7) + ',' + Math.round(my / 7); if (mastGrid.has(gk)) continue;
        for (const dx of [-1, 0, 1]) for (const dy of [-1, 0, 1]) mastGrid.add((Math.round(mx / 7) + dx) + ',' + (Math.round(my / 7) + dy));
        masts.push([mx, my, mz, Math.atan2(-LY[i], -LX[i])]);
      }
    }
  }
  // platforms: the OSM outline raised to 1.1 m over the rails beside it (to the deck of an elevated station)
  for (const ring of data.platforms || []) {
    const n = ring.length / 2; if (n < 3) continue;
    let cx = 0, cy = 0; for (let k = 0; k < n; k++) { cx += ring[k * 2]; cy += ring[k * 2 + 1]; } cx /= n; cy /= n;
    let gmin = Infinity; for (let k = 0; k < n; k++) gmin = Math.min(gmin, ground(ring[k * 2], ring[k * 2 + 1]));
    let rz = -Infinity, rd = 1e9;
    for (const t of tracks) for (let i = 0; i < t.n; i += 1) { const d = Math.abs(t.X[i] - cx) + Math.abs(t.Y[i] - cy); if (d < 60) { const e = minDistToRing(t.X[i], t.Y[i], ring); if (e < 6 && e < rd + 2) { if (e < rd) rd = e; rz = Math.max(rz, t.Z[i]); } } }
    const top = (rz > -Infinity ? rz : gmin) + 1.1, c = chunk(cx, cy);
    // walls
    for (let k = 0; k < n; k++) {
      const a = [ring[k * 2], ring[k * 2 + 1]], b = [ring[((k + 1) % n) * 2], ring[((k + 1) % n) * 2 + 1]];
      const ex = b[0] - a[0], ey = b[1] - a[1], el = Math.hypot(ex, ey) || 1, nn = [ey / el, -ex / el, 0];
      const ga = Math.min(gmin, ground(a[0], a[1])) - 0.3, gb = Math.min(gmin, ground(b[0], b[1])) - 0.3;
      quad(c, [a[0], a[1], ga], [b[0], b[1], gb], [b[0], b[1], top], [a[0], a[1], top], nn, [0, ga], [el, gb], [el, top], [0, top], 3);
    }
    // the top: a fan of triangles (platform outlines are simple, nearly convex strips)
    const shape = new THREE.Shape(); for (let k = 0; k < n; k++) (k ? shape.lineTo : shape.moveTo).call(shape, ring[k * 2], ring[k * 2 + 1]);
    const sg = new THREE.ShapeGeometry(shape), sp = sg.attributes.position.array, si = sg.index.array, base = c.P.length / 3;
    for (let k = 0; k < sp.length; k += 3) { c.P.push(sp[k], top, -sp[k + 1]); c.N.push(0, 1, 0); c.UV.push(0, 0); c.part.push(3); }
    for (let k = 0; k < si.length; k += 3) c.I.push(base + si[k], base + si[k + 2], base + si[k + 1]);
  }
  for (const c of chunks.values()) {
    if (!c.I.length) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(c.P, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(c.N, 3));
    g.setAttribute('aUV', new THREE.Float32BufferAttribute(c.UV, 2)); g.setAttribute('aPart', new THREE.Float32BufferAttribute(c.part, 1));
    g.setIndex(c.P.length / 3 > 65535 ? new THREE.Uint32BufferAttribute(c.I, 1) : new THREE.Uint16BufferAttribute(c.I, 1)); g.computeBoundingSphere();
    const m = new THREE.Mesh(g, trackMat); m.receiveShadow = true; group.add(m);
  }
  // masts: an H-section post with a cantilever arm over the track, leaning after sixty years; a few have fallen
  const mg = (() => {
    const parts = [];
    const post = new THREE.BoxGeometry(0.28, 8.2, 0.28); post.translate(0, 4.1, 0); parts.push(post);
    const arm = new THREE.BoxGeometry(3.4, 0.14, 0.14); arm.translate(1.6, 7.1, 0); parts.push(arm);
    const brace = new THREE.BoxGeometry(2.4, 0.08, 0.08); brace.rotateZ(0.42); brace.translate(1.1, 7.6, 0); parts.push(brace);
    return mergeGeoms(parts);
  })();
  const mastMat = new THREE.ShaderMaterial({ uniforms: uni, vertexShader: mastVert, fragmentShader: mastFrag });
  const mi = new THREE.InstancedMesh(mg, mastMat, masts.length); mi.castShadow = true; mi.receiveShadow = true;
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(0, 0, 0, 'YXZ'), sc = new THREE.Vector3(1, 1, 1), pos = new THREE.Vector3();
  masts.forEach(([x, y, z, a], k) => {
    const r = hash1(k * 7.31), fallen = r < 0.04;
    // local +X (the arm) points across the track: the yaw turns +X to the track side
    e.set(fallen ? 0 : (hash1(k * 3.1) - 0.5) * 0.12, a, fallen ? 1.45 : (hash1(k * 5.7) - 0.5) * 0.14);
    q.setFromEuler(e); pos.set(x, z - 0.2, -y); m4.compose(pos, q, sc); mi.setMatrixAt(k, m4);
  });
  mi.computeBoundingSphere(); group.add(mi);
  // trains: cars 20 m long on their track, some derailed a little; you can stand on their roofs
  const carGeo = makeCarGeometry();
  const carMat = new THREE.ShaderMaterial({ uniforms: uni, vertexShader: carVert, fragmentShader: carFrag, side: THREE.DoubleSide });
  const cars = [];
  data.trains.forEach(([li, ti, s0, nc], k) => {
    const tr = tracks[ti]; if (!tr) return;
    for (let c = 0; c < nc; c++) {
      const sc0 = s0 + c * 20.5 + 10.0, a = along(tr, sc0 - 8), b = along(tr, sc0 + 8), m = along(tr, sc0);
      const yaw = Math.atan2(b[0] - a[0], b[1] - a[1]), pitch = Math.atan2(b[2] - a[2], 16);
      const d = hash1(k * 31 + c * 7.7), derail = d < 0.12 ? 1 : 0;
      cars.push({ x: m[0] + (derail ? Math.cos(yaw) * 0.9 : 0), y: m[1] - (derail ? Math.sin(yaw) * 0.9 : 0), z: m[2] + 0.45, yaw: yaw + (derail ? (d - 0.06) * 2.5 : (d - 0.5) * 0.01), pitch, roll: derail ? 0.1 + d : (hash1(c + k * 3.3) - 0.5) * 0.04, col: data.lines[li]?.[1] || '#888888' });
    }
  });
  const ci = new THREE.InstancedMesh(carGeo, carMat, Math.max(1, cars.length)); ci.count = cars.length; ci.castShadow = true; ci.receiveShadow = true;
  const col = new THREE.Color(), boxes = [];
  cars.forEach((c, k) => {
    e.set(c.pitch, -c.yaw, c.roll); q.setFromEuler(e); pos.set(c.x, c.z, -c.y); m4.compose(pos, q, sc); ci.setMatrixAt(k, m4);
    col.set(c.col).convertSRGBToLinear(); ci.setColorAt(k, col);
    boxes.push([c.x, c.y, c.yaw, 9.8, 1.45, c.z + 3.95]);
  });
  if (ci.instanceColor) ci.instanceColor.needsUpdate = true; ci.computeBoundingSphere(); group.add(ci);
  walker?.addBoxes(boxes);
  return { group, tracks, masts: masts.length, cars: cars.length, carPos: cars.map((c) => [c.x, c.y]), chunks: chunks.size, labels: data.labels.map(([li, x, y]) => [data.lines[li][0], x, y]) };
}

// a point along a track at arc length s: [x, y, z]
function along(t, s) {
  s = Math.max(0, Math.min(t.S[t.n - 1], s));
  let i = 0; while (i < t.n - 2 && t.S[i + 1] < s) i++;
  const f = (s - t.S[i]) / Math.max(1e-6, t.S[i + 1] - t.S[i]);
  return [t.X[i] + (t.X[i + 1] - t.X[i]) * f, t.Y[i] + (t.Y[i + 1] - t.Y[i]) * f, t.Z[i] + (t.Z[i + 1] - t.Z[i]) * f];
}
function minDistToRing(x, y, r) {
  let best = 1e9; const n = r.length / 2;
  for (let k = 0; k < n; k++) { const ax = r[k * 2], ay = r[k * 2 + 1], bx = r[((k + 1) % n) * 2], by = r[((k + 1) % n) * 2 + 1], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy || 1;
    const u = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / l2)); best = Math.min(best, Math.hypot(x - ax - u * dx, y - ay - u * dy)); }
  return best;
}
function hash1(x) { const s = Math.sin(x * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
function mergeGeoms(list) {
  const P = [], N = [], I = []; let base = 0;
  for (const g of list) { const gi = g.toNonIndexed(); const p = gi.attributes.position.array, n = gi.attributes.normal.array;
    for (let k = 0; k < p.length; k++) { P.push(p[k]); N.push(n[k]); } for (let k = 0; k < p.length / 3; k++) I.push(base + k); base += p.length / 3; }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); g.setIndex(I); return g;
}
// one car: local x across (±1.475), y up from the rail head, z along (±9.75); the body from 0.95 to 4.0 m with a rounded
// roof edge, two bogies and the underfloor boxes. aPart 0 = body, 1 = running gear
function makeCarGeometry() {
  const P = [], N = [], A = [], I = [];
  const W = 1.475, L = 9.75, y0 = 0.95, y1 = 3.6, y2 = 4.0, r = 0.35;
  const sec = [[W, y0], [W, y1], [W - r * 0.5, y1 + (y2 - y1) * 0.75], [W - r, y2], [-(W - r), y2], [-(W - r * 0.5), y1 + (y2 - y1) * 0.75], [-W, y1], [-W, y0]];
  const push = (p, n, a) => { P.push(...p); N.push(...n); A.push(a); return P.length / 3 - 1; };
  for (let k = 0; k < sec.length - 1; k++) {
    const [x0, h0] = sec[k], [x1, h1] = sec[k + 1], dx = x1 - x0, dh = h1 - h0, l = Math.hypot(dx, dh), n = [dh / l, -dx / l, 0];
    const a = push([x0, h0, -L], n, 0), b = push([x0, h0, L], n, 0), c = push([x1, h1, L], n, 0), d = push([x1, h1, -L], n, 0);
    I.push(a, c, b, a, d, c);
  }
  for (const sd of [-1, 1]) {        // the two ends
    const c0 = push([0, (y0 + y2) / 2, sd * L], [0, 0, sd], 0), ring = sec.map(([x, h]) => push([x, h, sd * L], [0, 0, sd], 0));
    for (let k = 0; k < ring.length; k++) { const a = ring[k], b = ring[(k + 1) % ring.length]; if (sd > 0) I.push(c0, a, b); else I.push(c0, b, a); }
  }
  const box = (cx, cy, cz, hx, hy, hz) => {
    const g = new THREE.BoxGeometry(hx * 2, hy * 2, hz * 2).toNonIndexed(); const p = g.attributes.position.array, n = g.attributes.normal.array;
    for (let k = 0; k < p.length; k += 3) { const v = push([p[k] + cx, p[k + 1] + cy, p[k + 2] + cz], [n[k], n[k + 1], n[k + 2]], 1); I.push(v); }
  };
  box(0, 0.5, -6.9, 1.2, 0.42, 1.4); box(0, 0.5, 6.9, 1.2, 0.42, 1.4); box(0, 0.75, 0, 1.05, 0.22, 4.2);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); g.setAttribute('aPart', new THREE.Float32BufferAttribute(A, 1)); g.setIndex(I);
  return g;
}
