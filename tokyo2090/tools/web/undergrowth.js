import * as THREE from 'three';

// Undergrowth for walking: grass tufts, tall grass, broad-leaf weeds, ferns, taro leaves, shrubs and climbing vine
// clumps at the foot of walls, as alpha-tested cards drawn with procedural leaf shapes. Two draw calls (small
// plants: three crossed cards; big plants: five arching cards). The plants live on stable world grids (a hash of
// the cell decides everything, so they never shuffle) held in toroidal buffers: moving the camera re-fills only the
// cells that changed, a few per frame. A fine grid (2 m cells) near the player and a coarse one (5 m cells, bigger
// plants) out to ~60 m cross-fade into each other.
//
//   const ug = makeUndergrowth(scene, shared, { ground, roof, low });
//   ug.update(camera.position, dt, clock, onFoot);     // three.js world position; nothing runs while onFoot is false
//
// Data axes are x east, y north, z up; the three.js world is (x, z, -y).

const COVER_URL = 'data/cover.png';
const COVER = { x0: -2400, y1: 4400, res: 4 };

// ---------------------------------------------------------------------------------------------------------------
// cover.png without the canvas: a canvas premultiplies alpha and wipes R, G and B wherever A (rail) is 0, which is
// almost everywhere. So the PNG is decoded by hand (8-bit RGBA, any filter, no interlace).
export async function decodePNG(buf) {
  const u8 = new Uint8Array(buf), dv = new DataView(buf);
  let o = 8, w = 0, h = 0, depth = 0, ctype = 0, inter = 0; const idat = []; let total = 0;
  while (o + 8 <= u8.length) {
    const len = dv.getUint32(o), type = String.fromCharCode(u8[o + 4], u8[o + 5], u8[o + 6], u8[o + 7]);
    if (type === 'IHDR') { w = dv.getUint32(o + 8); h = dv.getUint32(o + 12); depth = u8[o + 16]; ctype = u8[o + 17]; inter = u8[o + 20]; }
    else if (type === 'IDAT') { idat.push(u8.subarray(o + 8, o + 8 + len)); total += len; }
    else if (type === 'IEND') break;
    o += 12 + len;
  }
  if (depth !== 8 || ctype !== 6 || inter !== 0) throw new Error('cover.png: unsupported PNG layout');
  const z = new Uint8Array(total); let p = 0; for (const c of idat) { z.set(c, p); p += c.length; }
  const raw = new Uint8Array(await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer());
  const stride = w * 4, out = new Uint8Array(h * stride);
  for (let y = 0; y < h; y++) {
    const f = raw[y * (stride + 1)], src = y * (stride + 1) + 1, dst = y * stride;
    for (let i = 0; i < stride; i++) {
      const x = raw[src + i], a = i >= 4 ? out[dst + i - 4] : 0, b = y > 0 ? out[dst - stride + i] : 0, c = i >= 4 && y > 0 ? out[dst - stride + i - 4] : 0;
      let v;
      if (f === 0) v = x; else if (f === 1) v = x + a; else if (f === 2) v = x + b; else if (f === 3) v = x + ((a + b) >> 1);
      else { const pp = a + b - c, pa = Math.abs(pp - a), pb = Math.abs(pp - b), pc = Math.abs(pp - c); v = x + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c); }
      out[dst + i] = v & 255;
    }
  }
  return { w, h, data: out };
}
export async function loadCover(url = COVER_URL) { const r = await fetch(url); if (!r.ok) throw new Error(url + ' ' + r.status); return decodePNG(await r.arrayBuffer()); }

// ---------------------------------------------------------------------------------------------------------------
// the same sine-free hashes as the terrain shader, so the road cracks the plants sprout from are the slab cracks
// the ground shader draws (see terrain.js: the `vor` call for the slabs)
const fract = (x) => x - Math.floor(x);
function h12(px, py) {
  let q0 = fract(px * 0.1031), q1 = fract(py * 0.1031), q2 = q0; const d = q0 * (q1 + 33.33) + q1 * (q2 + 33.33) + q2 * (q0 + 33.33);
  q0 += d; q1 += d; q2 += d; return fract((q0 + q1) * q2);
}
const _h = [0, 0];
function h22(px, py) {
  let q0 = fract(px * 0.1031), q1 = fract(py * 0.1030), q2 = fract(px * 0.0973); const d = q0 * (q1 + 33.33) + q1 * (q2 + 33.33) + q2 * (q0 + 33.33);
  q0 += d; q1 += d; q2 += d; _h[0] = fract((q0 + q1) * q2); _h[1] = fract((q0 + q2) * q1);
}
function vn(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y); let fx = x - ix, fy = y - iy; fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
  const a = h12(ix, iy), b = h12(ix + 1, iy), c = h12(ix, iy + 1), d = h12(ix + 1, iy + 1);
  return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy;
}
// distance (metres, approx.) from a point to the border of its ~2.9 m road slab
function slabEdge(x, y) {
  const wx = x + (vn(x * 0.8 + 5, y * 0.8 + 5) - 0.5) * 0.9, wy = y + (vn(x * 0.8 + 17, y * 0.8 + 17) - 0.5) * 0.9;
  const px = wx / 2.9, py = wy / 2.9, ix = Math.floor(px), iy = Math.floor(py), fx = px - ix, fy = py - iy;
  let f1 = 9, f2 = 9;
  for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) {
    h22(ix + i, iy + j); const rx = i + _h[0] * 0.86 + 0.07 - fx, ry = j + _h[1] * 0.86 + 0.07 - fy, d = rx * rx + ry * ry;
    if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) f2 = d;
  }
  return (Math.sqrt(f2) - Math.sqrt(f1)) * 1.45;
}
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// xorshift random numbers, seeded per slot from the cell: the same cell always grows the same plants
let S = 1;
function seed(ix, iy, j, salt) { S = (Math.imul(ix, 73856093) ^ Math.imul(iy, 19349663) ^ Math.imul(j + 1, 83492791) ^ Math.imul(salt + 1, 668265263)) | 0; if (S === 0) S = 1; rnd(); rnd(); }
function rnd() { S ^= S << 13; S ^= S >>> 17; S ^= S << 5; return (S >>> 0) / 4294967296; }

// ---------------------------------------------------------------------------------------------------------------
// geometry: unit cards. position = (across, along, card angle or index); uv = (across + 0.5, along)
function cardsA() {          // three crossed upright cards (grass, weeds, vines)
  const pos = [], uv = [], idx = [];
  for (let k = 0; k < 3; k++) {
    const a = k * Math.PI / 3, b = pos.length / 3;
    for (const [x, y] of [[-0.5, 0], [0.5, 0], [-0.5, 1], [0.5, 1]]) { pos.push(x, y, a); uv.push(x + 0.5, y); }
    idx.push(b, b + 1, b + 2, b + 1, b + 3, b + 2);
  }
  return mk(pos, uv, idx);
}
function cardsB() {          // five fronds, three rows each (so they can arch)
  const pos = [], uv = [], idx = [];
  for (let k = 0; k < 5; k++) {
    const b = pos.length / 3;
    for (const y of [0, 0.5, 1]) for (const x of [-0.5, 0.5]) { pos.push(x, y, k); uv.push(x + 0.5, y); }
    for (let r = 0; r < 2; r++) { const q = b + r * 2; idx.push(q, q + 1, q + 2, q + 1, q + 3, q + 2); }
  }
  return mk(pos, uv, idx);
}
function mk(pos, uv, idx) {
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  return g;
}

// ---------------------------------------------------------------------------------------------------------------
const vert = /* glsl */`
  #include <packing>
  attribute vec4 iA;   // base position (three.js world) and width in metres
  attribute vec4 iB;   // yaw, kind (-1 = empty), random, height in metres
  attribute vec4 iC;   // distance bands: fade in from .x to .y, fade out from .z to .w
  attribute vec4 iD;   // lean direction (x, z), thinning rank, spare
  uniform vec3 camPos; uniform float time; uniform float fade; uniform float bendB;
  uniform sampler2D shadowMap; uniform mat4 shadowMatrix; uniform vec2 shadowSize; uniform vec3 sunDir;
  uniform vec3 skyCol; uniform vec3 groundCol;
  uniform float isB;
  varying vec2 vUv; varying vec3 vN; varying float vKind; varying float vRnd; varying float vVis; varying float vShadow; varying vec3 vW; varying float vAlong;
  varying vec3 vTint;
  float hs(float x){ x = fract(x * 0.1031); x *= x + 33.33; x *= x + x; return fract(x); }
  float shadowTap(vec3 w){
    vec4 sc = shadowMatrix * vec4(w + vec3(0.0, 0.6, 0.0), 1.0); sc.xyz /= sc.w;
    if(sc.x <= 0.001 || sc.x >= 0.999 || sc.y <= 0.001 || sc.y >= 0.999 || sc.z >= 1.0) return 1.0;
    float bias = 0.0027, s = 0.0; vec2 t = 1.0 / shadowSize;
    for(int i = 0; i < 4; i++){
      vec2 o = (vec2(float(i & 1), float(i >> 1)) - 0.5) * 2.0 * t;
      s += sc.z - bias > unpackRGBAToDepth(texture2D(shadowMap, sc.xy + o)) ? 0.0 : 1.0;
    }
    return s * 0.25;
  }
  void main(){
    float kind = iB.y;
    if(kind < -0.5){ gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    float rnd = iB.z;
    vec3 base = iA.xyz;
    float d = length(base.xz - camPos.xz);
    float vis = fade * smoothstep(iC.x, iC.y, d) * (1.0 - smoothstep(iC.z, iC.w, d));
    // thin out with distance: the rank is this plant's place in the order of survival
    float keep = mix(1.0, 0.45, smoothstep(8.0, 55.0, d));
    float sc = clamp((keep - iD.z) * 6.0 + 0.5, 0.0, 1.0); if(kind > 3.5 && kind < 4.5) sc = 1.0;
    float w = iA.w * sc, h = iB.w * sc;
    float cy = cos(iB.x), sy = sin(iB.x);
    float across = position.x, along = position.y;
    vec3 loc, nrm;
    float amp, stiff;
    if(isB < 0.5){
      float a = position.z;
      loc = vec3(across * cos(a), along, across * sin(a)); nrm = vec3(-sin(a), 0.0, cos(a));
      loc.xz *= w; loc.y *= h;
      amp = kind < 0.5 ? 0.20 : (kind < 1.5 ? 0.10 : (kind < 2.5 ? 0.12 : 0.025)); stiff = along * along;
      if(kind > 3.5) stiff = along * along * 0.4;
    } else {
      float k = position.z, a = k * 1.2566 + (hs(rnd * 91.0 + k) - 0.5) * 0.9;
      float len = 0.7 + 0.5 * hs(rnd * 37.0 + k * 3.1);
      float th0 = kind < 3.5 ? 0.35 + 0.5 * hs(rnd * 53.0 + k) : (kind < 5.5 ? 0.25 + 0.55 * hs(rnd * 17.0 + k) : 0.2 + 0.17 * k);
      float droop = kind < 3.5 ? 0.9 : (kind < 5.5 ? 0.7 : 0.25);
      float L = h * (kind < 5.5 ? len : (0.8 + 0.3 * hs(rnd * 5.0 + k))); float t = along;
      float rad = L * (sin(th0) * t + 0.55 * droop * t * t), up = L * (cos(th0) * t - 0.45 * droop * t * t);
      vec3 dir = vec3(cos(a), 0.0, sin(a)), tt = vec3(-sin(a), 0.0, cos(a));
      float ww = w * (kind < 5.5 ? (kind < 3.5 ? 0.5 : 0.8) : 1.0);
      loc = dir * rad + vec3(0.0, up, 0.0) + tt * across * ww;
      vec3 T = dir * L * (sin(th0) + 1.1 * droop * t) + vec3(0.0, L * (cos(th0) - 0.9 * droop * t), 0.0);
      nrm = normalize(cross(tt, T));
      amp = kind < 3.5 ? 0.07 : (kind < 5.5 ? 0.06 : 0.03); stiff = along * along;
    }
    vec3 wp = vec3(loc.x * cy + loc.z * sy, loc.y, -loc.x * sy + loc.z * cy) + base;
    nrm = vec3(nrm.x * cy + nrm.z * sy, nrm.y, -nrm.x * sy + nrm.z * cy);
    if(isB < 0.5 && kind > 3.5) wp.xz += iD.xy * along * along * 0.4;      // a vine leans into its wall
    // wind: a slow gust field plus a faster flutter, each plant on its own phase
    float ph = rnd * 6.2832;
    float gust = sin(time * 0.9 + (base.x * 0.7 + base.z * 0.5) * 0.12) * 0.55 + sin(time * 0.37 + base.x * 0.05) * 0.45;
    float fl = sin(time * 3.1 + ph + base.x * 0.9) * 0.5 + sin(time * 4.7 + ph * 1.7 + base.z * 0.8) * 0.5;
    float sway = (gust * 0.8 + 0.25 + fl * 0.25) * amp * (isB < 0.5 ? h : h * 0.8) * stiff;
    wp.x += sway * 0.8; wp.z += sway * 0.6;
    vW = wp; vUv = uv; vN = nrm; vKind = kind; vRnd = rnd; vVis = vis; vAlong = along;
    vShadow = shadowTap(wp);
    // colour of this plant: fresh, yellow-green, straw, or dark
    float r2 = hs(rnd * 11.3 + 2.0), r3 = hs(rnd * 7.7 + 5.0);
    vec3 fresh = vec3(0.17, 0.36, 0.07), yel = vec3(0.40, 0.46, 0.10), straw = vec3(0.62, 0.52, 0.24), dark = vec3(0.09, 0.22, 0.06);
    vec3 tint;
    if(kind < 0.5 || (kind > 1.5 && kind < 2.5)){
      tint = mix(fresh, yel, smoothstep(0.2, 0.7, r2)); tint = mix(tint, straw, smoothstep(0.62, 0.9, r3) * 0.85); tint = mix(tint, dark, smoothstep(0.85, 1.0, r2) * 0.6);
    } else if(kind < 1.5){ tint = mix(vec3(0.13, 0.28, 0.07), vec3(0.22, 0.36, 0.09), r2); tint = mix(tint, vec3(0.30, 0.2, 0.08), step(0.93, r3) * 0.6); }
    else if(kind < 3.5){ tint = mix(vec3(0.10, 0.30, 0.07), vec3(0.20, 0.42, 0.10), r2); tint = mix(tint, straw * 0.6, step(0.9, r3) * 0.5); }
    else if(kind < 4.5){ tint = mix(vec3(0.11, 0.28, 0.07), vec3(0.20, 0.37, 0.09), r2); }
    else if(kind < 5.5){ tint = mix(vec3(0.07, 0.27, 0.09), vec3(0.13, 0.37, 0.12), r2); }
    else { tint = mix(vec3(0.10, 0.24, 0.06), vec3(0.22, 0.34, 0.08), r2); tint = mix(tint, vec3(0.34, 0.3, 0.08), step(0.88, r3) * 0.6); }
    vTint = tint;
    gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
  }`;

const frag = /* glsl */`
  precision highp float;
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol; uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos;
  varying vec2 vUv; varying vec3 vN; varying float vKind; varying float vRnd; varying float vVis; varying float vShadow; varying vec3 vW; varying float vAlong; varying vec3 vTint;
  float hh(float x){ x = fract(x * 0.1031); x *= x + 33.33; x *= x + x; return fract(x); }
  vec2 hh2(vec2 p){ vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973)); q += dot(q, q.yzx + 33.33); return fract((q.xx + q.yz) * q.zy); }
  float cov(float sd, float w){ return clamp(sd / max(w, 1e-5) + 0.5, 0.0, 1.0); }   // coverage from a signed distance (positive inside) and the pixel width

  // every shape returns (coverage, shade 0..1)
  vec2 grass(vec2 uv, float seed, float tall){
    float a = 0.0, sh = 0.5, fw = fwidth(uv.x) + 1e-4;
    int nb = tall > 0.5 ? 5 : 8;
    for(int i = 0; i < 8; i++){
      if(i >= nb) break;
      float fi = float(i); vec3 r = vec3(hh(fi * 3.7 + seed), hh(fi * 5.9 + seed * 2.0), hh(fi * 8.3 + seed * 3.0));
      float x0 = 0.1 + 0.8 * (fi + r.x) / float(nb);
      float hgt = tall > 0.5 ? 0.7 + 0.3 * r.y : 0.4 + 0.6 * r.y;
      float y = uv.y / hgt; if(y >= 1.0) continue;
      float lean = (r.z - 0.5) * (tall > 0.5 ? 0.25 : 0.6);
      float cx = x0 + lean * y * y;
      float hw = (tall > 0.5 ? 0.028 : 0.05) * (1.0 - pow(y, 0.8)) * (0.7 + 0.5 * r.x);
      float c = cov(hw - abs(uv.x - cx), fw);
      if(c > a){ a = c; sh = 0.2 + 0.55 * y + 0.25 * r.z; }
    }
    return vec2(a, sh);
  }
  vec2 weed(vec2 uv, float seed){
    float a = 0.0, sh = 0.5, fw = fwidth(uv.x) + 1e-4;
    for(int i = 0; i < 4; i++){
      float fi = float(i); float ang = (fi - 1.5) * 0.62 + (hh(fi * 4.1 + seed) - 0.5) * 0.4;
      vec2 dir = vec2(sin(ang), cos(ang)); float len = 0.62 + 0.35 * hh(fi * 9.1 + seed * 2.0);
      vec2 p = uv - vec2(0.5, 0.0); float al = dot(p, dir) / len, ac = dot(p, vec2(dir.y, -dir.x));
      float hw = 0.2 * len * pow(max(sin(3.14159 * clamp((al - 0.12) / 0.88, 0.0, 1.0)), 0.0), 0.7);
      float c = cov(min(hw - abs(ac), min(al - 0.1, 1.0 - al) * 0.5), fw * 1.2);
      float stem = cov(0.008 - abs(ac), fw) * step(al, 0.3) * step(0.0, al);
      c = max(c, stem);
      if(c > a){ a = c; sh = 0.3 + 0.5 * al + 0.15 * abs(ac) / (hw + 0.02); }
    }
    return vec2(a, sh);
  }
  vec2 fern(vec2 uv){
    float t = uv.y, lx = abs(uv.x - 0.5) * 2.0, fx = fwidth(lx) + 1e-4;
    float L = (1.0 - pow(t, 1.6)) * smoothstep(0.04, 0.24, t);
    float u = (t - lx * 0.28) * 17.0, ph = fract(u), fu = fwidth(u) + 1e-4;
    float wp = 0.78 - 0.5 * lx / max(L, 0.06);
    float leaf = min(cov(L - lx, fx), cov(wp - ph, fu * 1.2));
    float rach = cov(0.014 - abs(uv.x - 0.5), fwidth(uv.x) + 1e-4) * step(t, 0.99);
    return vec2(max(leaf, rach), leaf > rach ? 0.25 + 0.5 * lx + 0.2 * hh(floor(u) * 1.7 + floor(lx * 5.0)) : 0.1);
  }
  vec2 taro(vec2 uv){
    float v = (uv.y - 0.3) / 0.7, ax = abs(uv.x - 0.5), fw = fwidth(uv.x) + 1e-4;
    float vv = clamp(v, 0.0, 1.0);
    float W = 0.5 * pow(max(sin(3.14159 * pow(vv, 0.72)), 0.0), 0.75);
    float notch = (1.0 - smoothstep(0.0, 0.25, vv)) * 0.12;
    float sd = min(W - ax, ax - notch); sd = min(sd, min(v, 1.0 - v) * 0.4);
    float blade = cov(sd, fw * 1.3);
    float pet = cov(0.017 - ax, fw) * step(uv.y, 0.36);
    float vein = 1.0 - smoothstep(0.0, 0.07, abs(fract(v * 5.0 - ax * 3.2) - 0.5) * 2.0 - 0.85);
    float rib = 1.0 - smoothstep(0.0, 0.03, ax);
    float shade = 0.4 + 0.25 * (ax / max(W, 0.05)) + 0.35 * max(vein * 0.6, rib);
    return vec2(max(blade, pet), blade > pet ? shade : 0.35);
  }
  vec2 shrub(vec2 uv, float seed){
    float a = 0.0, sh = 0.4, fw = fwidth(uv.x) * 6.0 + 1e-4;
    for(int ly = 0; ly < 2; ly++){
      vec2 g = uv * vec2(5.0, 6.0) + vec2(0.5, 0.5) * float(ly) + vec2(seed * 3.0, 0.0);
      vec2 ic = floor(g), f = fract(g) - 0.5; vec2 jt = hh2(ic + seed) - 0.5; vec2 d = f - jt * 0.35;
      float ang = hh(dot(ic, vec2(7.1, 3.3)) + seed + float(ly) * 9.0) * 6.2832; float ca = cos(ang), sa = sin(ang);
      d = vec2(ca * d.x + sa * d.y, -sa * d.x + ca * d.y) / vec2(0.5, 0.26);
      vec2 cuv = (ic + 0.5 + jt * 0.35 - 0.5 * float(ly) - vec2(seed * 3.0, 0.0)) / vec2(5.0, 6.0);
      float env = 1.0 - length((cuv - vec2(0.5, 0.45)) / vec2(0.52, 0.55));
      float c = cov(1.0 - length(d), fwidth(length(d)) + 1e-4) * step(0.02, env);
      if(c > a){ a = c; sh = 0.2 + 0.6 * hh(dot(ic, vec2(1.3, 5.1)) + float(ly) * 3.0 + seed) + 0.25 * uv.y; }
    }
    return vec2(a, sh);
  }
  vec2 vine(vec2 uv, float seed){
    float a = 0.0, sh = 0.4, fw = fwidth(uv.x) + 1e-4;
    float rows = 13.0;
    for(int i = 0; i < 5; i++){
      float fi = float(i), r = hh(seed * 7.0 + fi * 3.1);
      float x0 = 0.12 + 0.76 * (fi + r * 0.7) / 5.0;
      float cx = x0 + 0.05 * sin(uv.y * 6.0 + r * 40.0) + (r - 0.5) * 0.1 * uv.y;
      float st = cov((0.012 - 0.006 * uv.y) - abs(uv.x - cx), fw) * step(uv.y, 0.55 + 0.45 * hh(seed + fi));
      float c = st; float lsh = 0.1;
      float rid0 = floor(uv.y * rows);
      for(int dr = -1; dr <= 1; dr++){          // the leaves of this row and its neighbours (a leaf crosses row borders)
        float rid = rid0 + float(dr);
        float side = mod(rid + fi, 2.0) * 2.0 - 1.0, lr = hh(rid * 1.7 + fi * 9.3 + seed);
        float yy = (rid + 0.5) / rows;
        float ls = (0.075 - 0.03 * yy) * (0.8 + 0.5 * lr);
        float lcx = x0 + 0.05 * sin(yy * 6.0 + r * 40.0) + (r - 0.5) * 0.1 * yy + side * ls * 0.9;
        float ang = side * (0.5 + 0.5 * lr);                               // leaves point up and out
        vec2 dd = uv - vec2(lcx, yy + 0.01 * lr); dd = vec2(cos(ang) * dd.x - sin(ang) * dd.y, sin(ang) * dd.x + cos(ang) * dd.y);
        dd /= vec2(ls * 1.0, ls * 0.62); float lg = length(dd);
        float lf = cov(1.0 - lg, fwidth(lg) + 1e-4) * step(lr, 0.95 - 0.5 * yy) * step(0.0, rid);
        if(lf > c){ c = lf; lsh = 0.35 + 0.5 * lr; }
      }
      if(c > a){ a = c; sh = lsh; }
    }
    vec2 m = shrub(vec2(uv.x, uv.y * 2.6), seed);
    float mc = m.x * step(uv.y, 0.38);
    if(mc > a){ a = mc; sh = m.y; }
    return vec2(a, sh);
  }

  void main(){
    // dithered fade in / out (no blending, so the order of drawing never matters)
    float ign = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715))));
    if(vVis < ign) discard;
    int k = int(vKind + 0.5);
    float seed = vRnd * 31.7;
    vec2 s;
    if(k == 0) s = grass(vUv, seed, 0.0);
    else if(k == 1) s = weed(vUv, seed);
    else if(k == 2) s = grass(vUv, seed, 1.0);
    else if(k == 3) s = fern(vUv);
    else if(k == 4) s = vine(vUv, seed);
    else if(k == 5) s = taro(vUv);
    else s = shrub(vUv, seed);
    if(s.x < 0.5) discard;
    float sh = s.y;
    // colour: the plant's tint, lighter at the tips / faces, darker deep in
    vec3 alb = vTint * (0.5 + 0.85 * sh);
    if(k == 0 || k == 2) alb = mix(alb, alb * vec3(1.25, 1.2, 0.8), smoothstep(0.55, 1.0, vUv.y) * 0.6);
    vec3 N = normalize(vN); if(!gl_FrontFacing) N = -N;
    float ndl = dot(N, sunDir);
    float dif = 0.5 * max(ndl, 0.0) + 0.38 * max(-ndl, 0.0) + 0.22 * sunDir.y;      // leaves are thin: the sun comes through
    float ao = mix(0.5, 1.0, smoothstep(0.0, 0.5, vAlong));
    if(k == 4) ao = mix(0.7, 1.0, smoothstep(0.0, 0.3, vAlong));
    vec3 light = sunCol * dif * vShadow + mix(groundCol, skyCol, 0.55) * 0.95;
    vec3 rgb = alb * light * ao;
    float d = length(vW - camPos); rgb = mix(rgb, fogCol, 1.0 - exp(-fogDen * d));
    gl_FragColor = vec4(rgb, 1.0);
  }`;

// ---------------------------------------------------------------------------------------------------------------
// plant counts per grid cell, and the two grids
const PROFILE = {
  high: [
    { cell: 2, G: 26, Ka: 10, Kb: 2, size: 1.0, fin: [-1, -0.5, 15, 24] },
    { cell: 5, G: 24, Ka: 8, Kb: 1, size: 1.5, fin: [14, 25, 48, 58] },
  ],
  low: [
    { cell: 2, G: 18, Ka: 8, Kb: 1, size: 1.0, fin: [-1, -0.5, 11, 17] },
    { cell: 5, G: 16, Ka: 5, Kb: 1, size: 1.5, fin: [10, 18, 32, 38] },
  ],
};

export function makeUndergrowth(scene, shared, ctx) {
  const { ground, roof, low } = ctx;
  // the hand-built districts (hero.js) bring their own vines and shrubs, and their cars and rubble are in the roof raster:
  // only the small grass there (wall-foot vines grew as big dark cards against buses and cars)
  const boxes = ctx.exclude || [];
  const inHero = (x, y) => boxes.some((b) => x > b[0] && x < b[2] && y > b[1] && y < b[3]);
  const cfg = PROFILE[low ? 'low' : 'high'].map((g) => ({ ...g }));
  let offA = 0, offB = 0;
  for (const g of cfg) { g.offA = offA; g.offB = offB; g.nCells = g.G * g.G; offA += g.nCells * g.Ka; offB += g.nCells * g.Kb; g.cx = -1e9; g.cy = -1e9; }
  const NA = offA, NB = offB;
  const group = new THREE.Group(); group.visible = false; group.name = 'undergrowth';

  const uniforms = {
    ...shared,    // sunDir, sunCol, skyCol, groundCol, fogCol, fogDen, camPos, shadowMap, shadowMatrix, shadowSize: by reference
    time: { value: 0 }, fade: { value: 0 }, bendB: { value: 0 },
  };
  function layer(geo, n, isB) {
    const iA = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4), iB = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4);
    const iC = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4), iD = new THREE.InstancedBufferAttribute(new Float32Array(n * 4), 4);
    for (const a of [iA, iB, iC, iD]) a.setUsage(THREE.DynamicDrawUsage);
    for (let i = 0; i < n; i++) iB.array[i * 4 + 1] = -1;
    geo.setAttribute('iA', iA); geo.setAttribute('iB', iB); geo.setAttribute('iC', iC); geo.setAttribute('iD', iD); geo.instanceCount = n;
    const mat = new THREE.ShaderMaterial({ uniforms: { ...uniforms, isB: { value: isB ? 1 : 0 } }, vertexShader: vert, fragmentShader: frag, side: THREE.DoubleSide, alphaToCoverage: true });
    const mesh = new THREE.Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = -5;
    group.add(mesh);
    return { mesh, iA, iB, iC, iD, lo: Infinity, hi: -1 };
  }
  const A = layer(cardsA(), NA, false), B = layer(cardsB(), NB, true);
  // the distance bands never change per slot: write them once
  for (const g of cfg) {
    for (const [L, off, K] of [[A, g.offA, g.Ka], [B, g.offB, g.Kb]]) for (let i = 0; i < g.nCells * K; i++) { const o = (off + i) * 4; L.iC.array.set(g.fin, o); }
  }
  scene.add(group);

  // cover raster
  let cover = null; loadCover().then((c) => { cover = c; }).catch((e) => { console.warn('undergrowth: no cover', e); cover = { w: 1, h: 1, data: new Uint8Array(4) }; });
  let cR = 0, cG = 0, cB = 0, cA = 0;
  function sampleCover(x, y) {
    const c = Math.floor((x - COVER.x0) / COVER.res), r = Math.floor((COVER.y1 - y) / COVER.res);
    if (c < 0 || r < 0 || c >= cover.w || r >= cover.h) { cR = cG = cB = cA = 0; return; }
    const i = (r * cover.w + c) * 4, d = cover.data; cR = d[i] / 255; cG = d[i + 1] / 255; cB = d[i + 2] / 255; cA = d[i + 3] / 255;
  }
  const solid = (x, y, gz) => roof.top(x, y) > gz + 1.0;
  const RING = [[1, 0], [0.707, 0.707], [0, 1], [-0.707, 0.707], [-1, 0], [-0.707, -0.707], [0, -1], [0.707, -0.707]];
  let wallNx = 0, wallNy = 0;
  // is there a building within r metres? (also leaves the direction towards it in wallN)
  function buildingWithin(x, y, gz, r) {
    let sx = 0, sy = 0, n = 0;
    for (const [dx, dy] of RING) if (solid(x + dx * r, y + dy * r, gz)) { sx += dx; sy += dy; n++; }
    if (!n) return false;
    const l = Math.hypot(sx, sy); if (l < 0.01) { wallNx = RING[0][0]; wallNy = RING[0][1]; } else { wallNx = sx / l; wallNy = sy / l; }
    return true;
  }

  // fill one cell's slots in grid g
  function buildCell(g, slot, ix, iy) {
    const cell = g.cell, x0 = ix * cell, y0 = iy * cell;
    const sz = g.size;
    for (let j = 0; j < g.Ka; j++) {
      const idx = g.offA + slot * g.Ka + j, o = idx * 4, ia = A.iA.array, ib = A.iB.array, id = A.iD.array;
      seed(ix, iy, j, 1);
      const x = x0 + rnd() * cell, y = y0 + rnd() * cell, rk = rnd(), kr = rnd(), r1 = rnd(), r2 = rnd(), r3 = rnd();
      ib[o + 1] = -1; ia[o + 3] = 0;
      sampleCover(x, y);
      if (cB > 0.5) continue;
      const gz = ground(x, y);
      if (solid(x, y, gz)) continue;
      let vine = false;
      const hero = inHero(x, y);
      if (!hero && j < (cell < 3 ? 2 : 1) && r3 < 0.7 && !buildingWithin(x, y, gz, 1.6) && buildingWithin(x, y, gz, 3.4)) vine = true;
      else if (buildingWithin(x, y, gz, 1.5)) continue;
      const R = cR, aR = sstep(0.30, 0.50, R), pv = sstep(0.12, 0.24, R) * (1 - aR), park = sstep(0.2, 0.9, cG);
      let dens;
      const clump = 0.2 + 1.5 * Math.pow(vn(x / 6 + 3.1, y / 6 + 7.7), 1.4);
      const land = (0.5 + 0.5 * park) * clump;
      if (aR > 0.01) { const e = slabEdge(x, y); dens = land * (1 - aR - pv) + pv * 0.12 + aR * (e < 0.3 ? 0.55 : 0.03); }
      else dens = land * (1 - pv) + pv * (0.1 + (R < 0.3 ? 0.25 : 0));
      if (cA > 0.3) dens = Math.max(dens, 0.45);
      if (vine) dens = 0.9; else if (rk > dens) continue;
      let kind, w, h;
      if (vine) {
        kind = 4; w = 1.5 + 0.8 * r1; h = 1.9 + 1.1 * r2;
        const lx = wallNx, lz = -wallNy;   // towards the wall, in three.js axes
        id[o] = lx; id[o + 1] = lz;
        ib[o] = Math.atan2(wallNx, -wallNy);
      } else {
        const paved = aR + pv > 0.4;
        if (kr < (paved ? 0.3 : 0.12)) { kind = 1; w = 0.4 + 0.3 * r1; h = 0.28 + 0.14 * r2; }
        else if (kr < (paved ? 0.34 : 0.12 + 0.1 * (1 - park) + 0.06)) { kind = 2; w = 0.45 + 0.2 * r1; h = 0.8 + 0.5 * r2; }
        else { kind = 0; w = 0.45 + 0.35 * r1; h = 0.3 + 0.3 * r2; }
        id[o] = 0; id[o + 1] = 0; ib[o] = r3 * 6.2832;
      }
      ia[o] = x; ia[o + 1] = gz - 0.02; ia[o + 2] = -y; ia[o + 3] = w * (vine ? 1 : sz);
      ib[o + 1] = kind; ib[o + 2] = r1 * 0.5 + r2 * 0.5; ib[o + 3] = h * (vine ? 1 : (kind === 0 ? sz : 1 + (sz - 1) * 0.5));
      id[o + 2] = Math.min(1, rk / Math.max(0.05, Math.min(1, dens)));
    }
    for (let j = 0; j < g.Kb; j++) {
      const idx = g.offB + slot * g.Kb + j, o = idx * 4, ia = B.iA.array, ib = B.iB.array, id = B.iD.array;
      seed(ix, iy, j, 2);
      const x = x0 + rnd() * cell, y = y0 + rnd() * cell, rk = rnd(), kr = rnd(), r1 = rnd(), r2 = rnd();
      ib[o + 1] = -1; ia[o + 3] = 0;
      sampleCover(x, y);
      if (cB > 0.5 || cR > 0.45) { if (!(cR > 0.45 && cR < 0.9 && rk < 0.04)) continue; }
      const gz = ground(x, y);
      if (solid(x, y, gz) || buildingWithin(x, y, gz, 2.6) || inHero(x, y)) continue;
      const park = sstep(0.2, 0.9, cG), pv = sstep(0.12, 0.3, cR);
      const clump = 0.15 + 1.6 * Math.pow(vn(x / 9 + 11.3, y / 9 + 2.2), 1.5);
      const dens = (0.4 + 0.6 * park) * clump * (1 - pv * 0.8);
      if (rk > dens) continue;
      let kind, w, h;
      if (park > 0.5) kind = kr < 0.45 ? 3 : kr < 0.72 ? 5 : 6; else kind = kr < 0.3 ? 3 : kr < 0.55 ? 5 : 6;
      if (kind === 3) { h = 0.65 + 0.5 * r1; w = h * 0.9; }
      else if (kind === 5) { h = 0.55 + 0.6 * r1; w = h * 0.8; }
      else { h = 0.9 + 0.9 * r1; w = h * (0.9 + 0.3 * r2); }
      ia[o] = x; ia[o + 1] = gz - 0.02; ia[o + 2] = -y; ia[o + 3] = w * (1 + (g.size - 1) * 0.5);
      ib[o] = r2 * 6.2832; ib[o + 1] = kind; ib[o + 2] = r1 * 0.5 + r2 * 0.5; ib[o + 3] = h * (1 + (g.size - 1) * 0.5);
      id[o] = 0; id[o + 1] = 0; id[o + 2] = Math.min(1, rk / Math.max(0.05, Math.min(1, dens)));
    }
    // remember the dirty range of each buffer
    const a0 = g.offA + slot * g.Ka, a1 = a0 + g.Ka - 1, b0 = g.offB + slot * g.Kb, b1 = b0 + g.Kb - 1;
    if (a0 < A.lo) A.lo = a0; if (a1 > A.hi) A.hi = a1; if (b0 < B.lo) B.lo = b0; if (b1 > B.hi) B.hi = b1;
  }

  // the toroidal window of each grid: slot (sx, sy) holds the one cell of the window that maps onto it
  for (const g of cfg) {
    g.curX = new Int32Array(g.nCells).fill(-2147483000); g.curY = new Int32Array(g.nCells).fill(-2147483000);
    g.pS = new Int32Array(g.nCells); g.pX = new Int32Array(g.nCells); g.pY = new Int32Array(g.nCells); g.nPend = 0;
  }
  const mod = (a, n) => ((a % n) + n) % n;
  function gridUpdate(g, cam, budget) {
    const cx = Math.floor(cam.x / g.cell), cy = Math.floor(-cam.z / g.cell);
    if (cx !== g.cx || cy !== g.cy) {
      g.cx = cx; g.cy = cy; g.nPend = 0;
      const bx = cx - (g.G >> 1), by = cy - (g.G >> 1);
      for (let sy = 0; sy < g.G; sy++) for (let sx = 0; sx < g.G; sx++) {
        const ix = bx + mod(sx - bx, g.G), iy = by + mod(sy - by, g.G), s = sy * g.G + sx;
        if (g.curX[s] !== ix || g.curY[s] !== iy) { const n = g.nPend++; g.pS[n] = s; g.pX[n] = ix; g.pY[n] = iy; }
      }
    }
    // closest first, a few per frame
    for (; g.nPend > 0 && budget > 0; budget--) {
      let best = 0, bd = Infinity;
      for (let i = 0; i < g.nPend; i++) { const dx = g.pX[i] + 0.5 - cam.x / g.cell, dy = g.pY[i] + 0.5 + cam.z / g.cell, d = dx * dx + dy * dy; if (d < bd) { bd = d; best = i; } }
      const s = g.pS[best], ix = g.pX[best], iy = g.pY[best];
      const n = --g.nPend; g.pS[best] = g.pS[n]; g.pX[best] = g.pX[n]; g.pY[best] = g.pY[n];
      buildCell(g, s, ix, iy); g.curX[s] = ix; g.curY[s] = iy;
    }
  }
  function flush(L) {
    if (L.hi < 0) return;
    for (const a of [L.iA, L.iB, L.iD]) { a.addUpdateRange(L.lo * 4, (L.hi - L.lo + 1) * 4); a.needsUpdate = true; }
    L.lo = Infinity; L.hi = -1;
  }

  let fade = 0, was = false, budget = low ? 16 : 30;
  const stats = { cells: 0, pending: 0, ms: 0, tris: 0 };
  stats.tris = NA * 6 + NB * 20;
  return {
    group, stats,
    // camPos: three.js world position of the eye. dt seconds, time seconds (wind), active: the player is on foot near the ground
    update(camPos, dt, time, active) {
      if (active) fade = Math.min(1, fade + dt / 0.5); else fade = Math.max(0, fade - dt / 0.5);
      if (fade <= 0) { if (group.visible) group.visible = false; was = false; return; }
      if (!cover) return;
      const t0 = performance.now();
      group.visible = true;
      uniforms.time.value = time; uniforms.fade.value = fade * fade * (3 - 2 * fade);
      if (!was) { was = true; for (const g of cfg) g.cx = -1e9; }     // the player may have moved far while it was off
      let pend = 0;
      for (const g of cfg) { gridUpdate(g, camPos, budget); pend += g.nPend; }
      flush(A); flush(B);
      stats.pending = pend; stats.ms = performance.now() - t0;
    },
  };
}
