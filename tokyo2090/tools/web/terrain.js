import * as THREE from 'three';
import { shadowGLSL } from './light.js';

// The ground: ring meshes from tools/gen/ground.py. Colour comes from the land-cover raster (what the ground was in
// the 2020s) reinterpreted sixty years later: asphalt cracked and grassed over, parks grown into forest, rails rusted.

const vert = /* glsl */`
  varying vec3 vW; varying vec3 vN;
  void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * w; }`;

const frag = /* glsl */`
  precision highp float;
  #include <packing>
  ${shadowGLSL}
  uniform sampler2D cover; uniform vec4 coverBox; // x0, y0(north), w, h in world metres (x east, y north)
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos; uniform float ringScale;
  varying vec3 vW; varying vec3 vN;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<4;k++){ v += a*noise(p); p = p*2.03 + 7.1; a *= 0.5; } return v; }
  void main(){
    vec2 xy = vec2(vW.x, -vW.z);
    vec2 uv = (xy - coverBox.xy) / coverBox.zw;
    vec4 cv = vec4(0.0); if(uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0) cv = texture2D(cover, uv);
    float n1 = fbm(xy * 0.08), n2 = fbm(xy * 0.011 + 3.0), n3 = noise(xy * 0.6);
    // the overgrown ground: summer grass and scrub, dry in patches
    vec3 grass = mix(vec3(0.20, 0.30, 0.10), vec3(0.42, 0.44, 0.18), n2);
    grass = mix(grass, vec3(0.13, 0.22, 0.08), n1 * 0.6);
    vec3 forest = mix(vec3(0.09, 0.17, 0.06), vec3(0.16, 0.25, 0.09), n1);
    vec3 asphalt = mix(vec3(0.21, 0.21, 0.20), vec3(0.30, 0.29, 0.27), n3);
    float cracks = smoothstep(0.45, 0.65, fbm(xy * 0.35 + 11.0));
    vec3 road = mix(asphalt, grass * 0.9, cracks * 0.75 + n2 * 0.2);
    vec3 rail = mix(vec3(0.34, 0.26, 0.19), grass, 0.55 + 0.3 * n1);
    vec3 water = mix(vec3(0.10, 0.17, 0.15), vec3(0.17, 0.26, 0.22), n1);
    vec3 col = mix(grass, forest, smoothstep(0.2, 0.9, cv.g));
    float roadW = smoothstep(0.15, 0.6, cv.r + 0.25 * (n3 - 0.5));           // soft, eaten edges
    col = mix(col, mix(road, asphalt * 0.8, smoothstep(0.65, 1.0, cv.r) * 0.3), roadW);
    col = mix(col, rail, smoothstep(0.3, 0.8, cv.a));
    col = mix(col, water, smoothstep(0.3, 0.7, cv.b));
    // far rings: a greener, hazier blanket
    col = mix(col, mix(vec3(0.18, 0.26, 0.11), vec3(0.3, 0.32, 0.2), n2), ringScale);
    vec3 N = normalize(vN);
    float dif = max(dot(N, sunDir), 0.0) * shadowAt(vW, N, sunDir);
    vec3 light = sunCol * dif + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9;
    vec3 rgb = col * light;
    float d = length(vW - camPos); float f = 1.0 - exp(-fogDen * d);
    rgb = mix(rgb, fogCol, f);
    gl_FragColor = vec4(rgb, 1.0);
  }`;

export function makeTerrainMaterial(uniforms) {
  return new THREE.ShaderMaterial({ uniforms, vertexShader: vert, fragmentShader: frag });
}

function ringGeometry(r, hole) {
  const nx = r.nx, ny = r.ny, pos = new Float32Array(nx * ny * 3), nor = new Float32Array(nx * ny * 3);
  const H = (c, w) => r.h[Math.min(ny - 1, Math.max(0, w)) * nx + Math.min(nx - 1, Math.max(0, c))];
  let k = 0;
  for (let w = 0; w < ny; w++) for (let c = 0; c < nx; c++, k++) {
    const x = r.x0 + c * r.s, y = r.y0 + w * r.s, z = r.h[w * nx + c];
    pos[k * 3] = x; pos[k * 3 + 1] = z; pos[k * 3 + 2] = -y;
    const dx = (H(c + 1, w) - H(c - 1, w)) / (2 * r.s), dy = (H(c, w + 1) - H(c, w - 1)) / (2 * r.s), l = Math.hypot(dx, 1, dy);
    nor[k * 3] = -dx / l; nor[k * 3 + 1] = 1 / l; nor[k * 3 + 2] = dy / l;
  }
  const idx = [];
  for (let w = 0; w < ny - 1; w++) for (let c = 0; c < nx - 1; c++) {
    if (hole) { const x = r.x0 + c * r.s, y = r.y0 + w * r.s; if (x >= hole[0] && x + r.s <= hole[2] && y >= hole[1] && y + r.s <= hole[3]) continue; }
    const a = w * nx + c, b = a + 1, cc = a + nx, d = cc + 1; idx.push(a, b, cc, b, d, cc);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setIndex(new THREE.Uint32BufferAttribute(idx, 1)); g.computeBoundingSphere();
  return g;
}

export function buildTerrain(rings, material) {
  const group = new THREE.Group();
  let hole = null;
  rings.forEach((r, i) => {
    const m = new THREE.ShaderMaterial({ uniforms: { ...material.uniforms, ringScale: { value: i === 0 ? 0 : i === 1 ? 0.6 : 1 } }, vertexShader: vert, fragmentShader: frag });
    const mesh = new THREE.Mesh(ringGeometry(r, hole), m); mesh.frustumCulled = false; mesh.renderOrder = -10 + i;
    group.add(mesh);
    hole = [r.x0, r.y0, r.x0 + (r.nx - 1) * r.s, r.y0 + (r.ny - 1) * r.s];
  });
  return group;
}
