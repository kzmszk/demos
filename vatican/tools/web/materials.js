// Uber material: MeshStandardMaterial whose albedo/roughness/metal come from the vertex stream
// `col` (sRGB albedo, a = roughness*127 + metal*128) and whose indirect diffuse is the baked
// per-vertex irradiance `irr` (Cycles units; x PI to match three's Lambert).  Sun direct light is
// realtime (CSM).  Detail textures (box-mapped in world space, z up) come from a texture array:
// R = albedo ratio, G,B = tangent-space normal xy.  Layer = texid.w*127 - 1.
import * as THREE from 'three';

export const shared = {
  time: { value: 0 },
  irrScale: { value: Math.PI }, detail: { value: null }, tiles: { value: [] }, nLayers: { value: 0 },
  detailStrength: { value: 1.0 }, debug: { value: 0 },
};

export async function loadDetail(base) {
  const meta = await (await fetch(`${base}/detail.json`)).json();
  const img = new Image(); img.src = `${base}/detail.jpg`; await img.decode();
  const S = meta.size, N = meta.layers.length;
  const c = document.createElement('canvas'); c.width = S; c.height = S * N;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  const data = g.getImageData(0, 0, S, S * N).data;
  const tex = new THREE.DataArrayTexture(new Uint8Array(data.buffer), S, S, N);
  tex.format = THREE.RGBAFormat; tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.LinearMipmapLinearFilter; tex.magFilter = THREE.LinearFilter; tex.generateMipmaps = true;
  tex.anisotropy = 8; tex.colorSpace = THREE.NoColorSpace; tex.needsUpdate = true;
  shared.detail.value = tex;
  const tiles = new Array(16).fill(1); meta.layers.forEach((l, i) => (tiles[i] = l.tile));
  shared.tiles.value = tiles; shared.nLayers.value = N;
}

function patch(shader) {
  Object.assign(shader.uniforms, { dbg: shared.debug, irrScale: shared.irrScale, detailTex: shared.detail, tiles: shared.tiles, nLayers: shared.nLayers, detailStrength: shared.detailStrength });
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', '#include <common>\nattribute vec4 irr;\nattribute vec4 col;\nattribute vec4 texid;\nvarying vec4 vIrr;\nvarying vec4 vCol;\nvarying vec3 vW;\nvarying vec3 vWN;\nflat varying int vTid;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvIrr = vec4(irr.rgb * irr.a * 8.0, 1.0); vCol = col; vW = (modelMatrix * vec4(position, 1.0)).xyz; vWN = normal; vTid = int(texid.w * 127.0 + 0.5) - 1;');
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <common>', `#include <common>
varying vec4 vIrr; varying vec4 vCol; varying vec3 vW; varying vec3 vWN; flat varying int vTid;
uniform int dbg; uniform float irrScale; uniform highp sampler2DArray detailTex; uniform float tiles[16]; uniform int nLayers; uniform float detailStrength;
vec3 s2l(vec3 c){ return mix(c/12.92, pow((c+0.055)/1.055, vec3(2.4)), step(0.04045, c)); }
vec3 detailSample; vec3 dT; vec3 dB; vec2 facadeUV;
void boxDetail(){
  detailSample = vec3(0.5, 0.5, 0.5); dT = vec3(1.0,0.0,0.0); dB = vec3(0.0,0.0,1.0);
  int layer = vTid == 11 ? 2 : vTid;
  if (layer < 0 || layer >= nLayers) return;
  vec3 n = normalize(vWN); vec3 a = abs(n); vec2 uv;
  if (a.z > a.x && a.z > a.y) { uv = vW.xy; dT = vec3(1.0,0.0,0.0); dB = vec3(0.0,1.0,0.0); }
  else if (a.x > a.y) { uv = vec2(vW.y * sign(n.x), vW.z); dT = vec3(0.0,sign(n.x),0.0); dB = vec3(0.0,0.0,1.0); }
  else { uv = vec2(-vW.x * sign(n.y), vW.z); dT = vec3(-sign(n.y),0.0,0.0); dB = vec3(0.0,0.0,1.0); }
  detailSample = texture(detailTex, vec3(uv / tiles[layer], float(layer))).rgb;
  facadeUV = uv;
}
/* Roman facade: window bays 3.4 m apart, floors 3.6 m; shutters, sills, a darker ground floor */
vec4 facadeWindow(vec2 uv, vec3 n) {
  if (abs(n.z) > 0.5) return vec4(0.0);
  float fx = fract(uv.x / 3.4), fy = fract((uv.y - 0.6) / 3.6);
  float floorIx = floor((uv.y - 0.6) / 3.6);
  if (uv.y < 4.2) return vec4(0.0);
  float h = fract(sin(dot(floor(vec2(uv.x / 3.4, floorIx)), vec2(12.9898, 78.233))) * 43758.5453);
  float wx = smoothstep(0.32, 0.335, fx) * (1.0 - smoothstep(0.665, 0.68, fx));
  float wy = smoothstep(0.22, 0.235, fy) * (1.0 - smoothstep(0.72, 0.735, fy));
  float win = wx * wy;
  float sill = smoothstep(0.30, 0.31, fx) * (1.0 - smoothstep(0.69, 0.70, fx)) * smoothstep(0.195, 0.2, fy) * (1.0 - smoothstep(0.22, 0.225, fy));
  float shut = (smoothstep(0.24, 0.25, fx) * (1.0 - smoothstep(0.32, 0.33, fx)) + smoothstep(0.67, 0.68, fx) * (1.0 - smoothstep(0.75, 0.76, fx))) * wy * step(0.45, h);
  return vec4(win, sill, shut, h);
}`)
    .replace('#include <color_fragment>', `#include <color_fragment>
boxDetail();
float ratio = mix(1.0, detailSample.r * 2.0, detailStrength);
diffuseColor.rgb *= s2l(vCol.rgb) * ratio;
float facadeGlass = 0.0;
if (vTid == 11) {
  vec4 w = facadeWindow(facadeUV, normalize(vWN));
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.86, 0.84, 0.78) * diffuseColor.rgb / max(0.2, dot(diffuseColor.rgb, vec3(0.33))) * 0.5, w.y);
  diffuseColor.rgb = mix(diffuseColor.rgb, mix(vec3(0.10, 0.16, 0.12), vec3(0.22, 0.17, 0.11), step(0.75, w.w)), w.z);
  diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.025, 0.03, 0.035), w.x);
  facadeGlass = w.x;
}`)
    .replace('#include <roughnessmap_fragment>', 'float aa = vCol.a * 255.0; float metalFlag = step(127.5, aa);\nfloat roughnessFactor = clamp(mix(mod(aa, 128.0) / 127.0 * mix(1.0, 1.25 - 0.5 * detailSample.r, detailStrength), 0.12, facadeGlass), 0.04, 1.0);')
    .replace('#include <metalnessmap_fragment>', 'float metalnessFactor = metalFlag;')
    .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
if (vTid >= 0 && vTid < nLayers) {
  vec2 nxy = (detailSample.gb * 2.0 - 1.0) * detailStrength;
  vec3 wn = normalize(normalize(vWN) + (dT * nxy.x + dB * nxy.y) * 0.9);
  normal = normalize((viewMatrix * vec4(wn, 0.0)).xyz);
}`)
    .replace('#include <dithering_fragment>', `#include <dithering_fragment>
if (dbg == 1) gl_FragColor = vec4(vIrr.rgb * 1.5, 1.0);
if (dbg == 2) gl_FragColor = vec4(normalize(vWN) * 0.5 + 0.5, 1.0);
if (dbg == 3) gl_FragColor = vec4(s2l(vCol.rgb), 1.0);`)
    .replace('#include <lights_fragment_maps>', `
#if defined( RE_IndirectDiffuse )
  irradiance += vIrr.rgb * irrScale * mix(1.0, clamp(0.55 + 0.9 * detailSample.r, 0.6, 1.4), detailStrength * 0.6);
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
  radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness ) * clamp(dot(vIrr.rgb, vec3(0.3,0.5,0.2)) * 1.2, 0.03, 1.0);
#endif
`);
}

const cache = new Map();
const texLoader = new THREE.TextureLoader();
const REPEAT = /drapery|band|pilaster|upper|floor|momo_rail|rotonda_dome/;
export function getMaterial(cls, csm) {
  if (cache.has(cls)) return cache.get(cls);
  let m;
  if (cls.startsWith('art:')) {
    const key = cls.slice(4);
    const t = texLoader.load(`art/${key}.webp`);
    t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    t.wrapS = t.wrapT = REPEAT.test(key) ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
    m = new THREE.MeshStandardMaterial({ map: t, roughness: 0.88, metalness: 0 });
    if (/rail/.test(key)) { m.alphaTest = 0.5; m.side = THREE.DoubleSide; }     // see-through grille
  } else if (cls === 'gloria') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color().setRGB(3.2, 2.3, 0.9, THREE.LinearSRGBColorSpace) });
    cache.set(cls, m); return m;
  } else if (cls === 'glass_pane') {
    m = new THREE.MeshStandardMaterial({ color: 0x0a0c0e, roughness: 0.04, metalness: 0, transparent: true, opacity: 0.12, depthWrite: false });
    cache.set(cls, m); return m;
  } else if (cls === 'water_fall') {
    // falling sheets of water: streaks around the fountain's axis that run downwards (the two fountains of the square)
    m = new THREE.MeshBasicMaterial({ color: 0xe8f0f4, transparent: true, depthWrite: false, side: THREE.DoubleSide });
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uTime = shared.time;
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWp;').replace('#include <begin_vertex>', '#include <begin_vertex>\nvWp = (modelMatrix * vec4(position, 1.0)).xyz;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWp; uniform float uTime;\nfloat h1(float x){ return fract(sin(x * 127.1) * 43758.5453); }')
        .replace('#include <color_fragment>', `#include <color_fragment>
          float cy = vWp.y > 0.0 ? 60.0 : -60.0;
          float ang = atan(vWp.y - cy, vWp.x) * 38.0;
          float col = floor(ang), f = fract(ang);
          float streak = smoothstep(0.0, 0.25, f) * (1.0 - smoothstep(0.55, 0.9, f)) * (0.55 + 0.45 * h1(col));
          float fall = fract(vWp.z * 0.9 + uTime * (1.6 + 0.6 * h1(col + 3.0)) + h1(col + 7.0));
          float a = streak * (0.35 + 0.65 * smoothstep(0.0, 0.5, fall) * (1.0 - smoothstep(0.7, 1.0, fall)));
          diffuseColor.a *= clamp(a * 0.85 + 0.08, 0.0, 0.9);`);
    };
    cache.set(cls, m); return m;
  } else {
    m = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, metalness: 0 });
  }
  m.name = cls;
  if (csm) {
    csm.setupMaterial(m);
    const f = m.onBeforeCompile;
    m.onBeforeCompile = (sh, r) => { f(sh, r); patch(sh); };
  } else m.onBeforeCompile = patch;
  m.customProgramCacheKey = () => 'uber2' + (m.transparent ? 't' : '') + (m.map ? 'm' : '');
  cache.set(cls, m);
  return m;
}
