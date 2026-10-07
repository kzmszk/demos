// KYOTO — viewer entry.  three.js WebGPU renderer, z-up world (x east, y north, metres from Kyoto Station's central
// exit; z = height above T.P.).  An autumn evening and a snowy evening, on foot and in the air.
import * as THREE from 'three/webgpu';
import { pass, mrt, output, normalView, velocity, screenUV, builtinAOContext, packNormalToRGB, unpackRGBToNormal, sample, vec3, vec4, float, Fn,
  positionWorld, cameraPosition, length, normalize, dot, max, pow, exp, mix, clamp, smoothstep, uniform, vec2, output as outNode } from 'three/tsl';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { CSMShadowNode } from 'three/addons/csm/CSMShadowNode.js';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { traa } from 'three/addons/tsl/display/TRAANode.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { Tiles, perfLog, prefetch } from './tiles.js';
import { makeCityMaterial, makeGroundMaterial, makeWaterMaterial, makeLiteMaterial, SurfPool, G } from './kyomat.js';
import { Controls } from './controls.js';
import { Trees } from './trees.js';
import { MiniMap } from './minimap.js';
import { Snow } from './snow.js';
import { Statues } from './statues.js';
import { Weirs } from './weirs.js';
import { loadFar, farGround } from './far.js';
import { createAudio, renderOffline, wavBytes, beatTimes } from './audio.js';
import { UI, PLACES } from './ui.js';

THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const JA = location.hash !== '#en' && (location.hash === '#ja' || (navigator.language || '').startsWith('ja'));
const UAD = navigator.userAgentData;
const LOW = params.has('low') ? params.get('low') !== '0'
  : (UAD ? UAD.mobile || UAD.platform === 'Android' : /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))
    || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent))
    || (navigator.deviceMemory > 0 && navigator.deviceMemory <= 4);

for (let i = 0; i < 30 && navigator.gpu; i++) { if (await navigator.gpu.requestAdapter()) break; await new Promise((r) => setTimeout(r, 150)); }
const renderer = new THREE.WebGPURenderer({ canvas: $('c'), antialias: LOW, powerPreference: 'high-performance', forceWebGL: params.get('gl') === '1' });
await renderer.init();
if (!renderer.backend.isWebGPUBackend && params.get('gl') !== '1') {
  const m = document.createElement('div'); m.className = 'nogpu';
  m.innerHTML = JA
    ? '<b>京都</b><p>このデモには WebGPU が必要です。</p><p>Windows・macOS・Android の Chrome / Edge、または Safari 26 以降で開いてください。</p><p>Linux の Chrome では chrome://flags で「Unsafe WebGPU Support」を Enabled にして再起動すると使えます。</p>'
    : '<b>KYOTO</b><p>This demo needs WebGPU.</p><p>Open it in Chrome or Edge on Windows, macOS or Android, or in Safari 26 or later.</p><p>On Linux, enable “Unsafe WebGPU Support” in chrome://flags and relaunch Chrome.</p>';
  document.body.appendChild(m); document.querySelector('.title .prep')?.remove();
  throw new Error('WebGPU unavailable');
}
function gpuGone(why) {
  if (document.querySelector('.nogpu')) return;
  const m = document.createElement('div'); m.className = 'nogpu';
  m.innerHTML = (JA ? '<b>京都</b><p>GPU のメモリが足りなくなり、描画が止まりました。</p><p>ページを再読み込みしてください。</p><p>軽い表示でも開けます: アドレスの末尾に ?low=1</p>'
    : '<b>KYOTO</b><p>The GPU ran out of memory and stopped drawing.</p><p>Please reload the page.</p><p>A lighter version opens with ?low=1 at the end of the address.</p>') + `<p>(${String(why).replace(/[<>&]/g, '')})</p>`;
  document.body.appendChild(m);
}
{
  const dev = renderer.backend.device;
  dev.lost.then((i) => { if (i.reason !== 'destroyed') gpuGone(i.message || 'device lost'); });
  dev.addEventListener('uncapturederror', (e) => { if (typeof GPUOutOfMemoryError !== 'undefined' && e.error instanceof GPUOutOfMemoryError) gpuGone('out of memory'); });
}
const pixelRatio = () => +(params.get('pr') || 0) || Math.min(devicePixelRatio, LOW ? 1.5 : 2, Math.sqrt((LOW ? 1.1e6 : 3.7e6) / (innerWidth * innerHeight)));
renderer.setPixelRatio(pixelRatio());
const dyn = { k: 1, acc: 0, n: 0, good: 0, off: params.has('pr') || navigator.webdriver === true };
function dynRes(dt) {
  if (dyn.off || app.mode === 'title') return;
  dyn.acc += dt; dyn.n++;
  if (dyn.acc < 2.0) return;
  const ft = dyn.acc / dyn.n; dyn.acc = 0; dyn.n = 0;
  let k = dyn.k;
  if (ft > 1 / 25) { k = Math.max(0.55, k * 0.85); dyn.good = 0; }
  else if (ft < 1 / 50 && k < 1) { if (++dyn.good >= 2) { k = Math.min(1, k * 1.1); dyn.good = 0; } }
  if (Math.abs(k - dyn.k) > 1e-3) { dyn.k = k; renderer.setPixelRatio(pixelRatio() * k); }
}
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = params.get('tm') === 'agx' ? THREE.AgXToneMapping : THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const PIPE = { pending: 0, made: 0 };
if (params.get('async') !== '0') {
  const pipes = renderer._pipelines;
  const sink = { push(p) { PIPE.pending++; PIPE.made++; p.then(() => PIPE.pending--); } };
  pipes.updateForRender = (ro) => pipes.getForRender(ro, ro.scene === scene ? sink : null);
}
const camera = new THREE.PerspectiveCamera(58, innerWidth / innerHeight, 0.15, 30000);
camera.up.set(0, 0, 1);
const START = PLACES[0];
camera.position.set(START.at[0], START.at[1], 30); camera.lookAt(START.at[0] + Math.cos(START.yaw), START.at[1] + Math.sin(START.yaw), 30.1);

// ---------------------------------------------------------------- app state
const app = {
  mode: 'title', season: params.get('season') === 'winter' ? 'winter' : 'autumn', sound: false,
  bright: (() => { try { return Math.min(2.5, Math.max(0.5, +localStorage.getItem('kyo-bright') || 1)); } catch (e) { return 1; } })(),
  setBright(v) { this.bright = v; try { localStorage.setItem('kyo-bright', String(v)); } catch (e) { /* private mode */ } },
  begin(m) {
    if (LD.phase !== 'done') loadDone(false);
    this.started = true;
    if (!this.sound) this.toggleSound();          // the start click is the gesture that lets the sound begin
    const yaw = titleYaw(); this.goPlace(START); controls.yaw = yaw;
    if (m === 'fly') this.setMode('fly');
  },
  setMode(m) {
    if (m === 'walk' && this.mode !== 'walk') controls.pitch = 0;
    if (m === 'fly' && this.mode === 'walk') camera.position.z += 1.5;
    this.mode = m; controls.setMode(m); ui.refresh();
  },
  goPlace(p) {
    this.setMode(p.mode);
    if (p.at) {
      const z = p.z != null ? p.z : terrainZ(p.at[0], p.at[1]) + 1.6;
      camera.position.set(p.at[0], p.at[1], z); controls.yaw = p.yaw; controls.pitch = p.pitch != null ? p.pitch : 0.02;
    }
    controls.walkZ = null;
  },
  setSeason(s) { this.season = s; setSeason(s); ui.refresh(); },
  toggleSound() { this.sound = !this.sound; window.dispatchEvent(new CustomEvent('kyo-sound', { detail: this.sound })); ui.refresh(); },
};
const ui = new UI(app);

// ---------------------------------------------------------------- loading: the first view comes first
const SET = 'data/' + (params.get('set') || 'city');
const GATE = { x: START.at[0], y: START.at[1], full: 260, lite: 1600 };
const LD = { tex: new Map(), got: 0, want: 0, phase: 'data', work: 0, work0: 0, quiet: 0, shown: 0, tg: 0 };
function loadShow(force = false) {
  const now = performance.now(); if (!force && now - LD.shown < 60) return; LD.shown = now;
  let f = -1;
  if (LD.phase === 'data') {
    let a = LD.got, b = LD.want;
    for (const [l, t] of LD.tex.values()) { a += l; b += t; }
    if (LD.tex.size >= 4 && LD.want > 0) f = 0.9 * Math.min(1, a / b);
  } else f = LD.work0 ? 0.9 + 0.1 * (1 - LD.work / LD.work0) : 0.9;
  ui.prep(f, LD.phase === 'data' ? 'data' : 'gpu');
}
const texProg = (k) => (e) => { if (e && e.lengthComputable && e.total) { LD.tex.set(k, [e.loaded, e.total]); loadShow(); } };
const indexP = fetch(`${SET}/tiles.json`).then((r) => r.json()).then((j) => j.tiles);
const preP = indexP.then((index) => {
  const r = prefetch(SET, index, GATE.x, GATE.y, GATE.full, GATE.lite, (n) => { LD.got += n; loadShow(); });
  LD.want = r.bytes; loadShow(true); return r.pre;
});
loadShow(true);

function freeOnUpload(t) {
  t.onUpdate = () => {
    for (const m of t.mipmaps || []) if (m.data) m.data = new m.data.constructor(0);
    if (t.image && t.image.data && t.image.data.length) t.image.data = new t.image.data.constructor(0);
    t.onUpdate = null;
  };
}
// sky: equirect in Blender's convention; this rotation maps our z-up world to three's lookup
const SKY_ROT = new THREE.Euler().setFromRotationMatrix(new THREE.Matrix4().set(-1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1));
const ktx = new KTX2Loader().setTranscoderPath('basis/').detectSupport(renderer);
// files over the static host's size limit come in parts (tools/split_big.py, tex/split.json): fetched together, joined
const splitP = fetch('tex/split.json').then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
async function fetchParts(urls, k) {
  const rs = await Promise.all(urls.map((u) => fetch(u)));
  let loaded = 0, total = 0;
  for (const r of rs) { if (!r.ok) throw new Error(`${r.url}: ${r.status}`); total += +(r.headers.get('content-length') || 0); }
  const chunks = [];
  for (const r of rs) {
    const rd = r.body.getReader();
    for (;;) {
      const { done, value } = await rd.read(); if (done) break;
      chunks.push(value); loaded += value.length;
      if (total) texProg(k)({ lengthComputable: true, loaded: Math.min(loaded, total), total });
    }
  }
  const out = new Uint8Array(loaded); let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out.buffer;
}
const loadKTX = (u, k) => splitP.then((sp) => {
  const n = sp[u.split('/').pop()];
  if (!n) return new Promise((res, rej) => ktx.load(u, res, texProg(k), rej));
  return fetchParts(Array.from({ length: n }, (_, i) => `${u}.${i}`), k).then((buf) => new Promise((res, rej) => ktx.parse(buf, res, rej)));
});
const RES = params.get('tex') || (LOW ? '512' : '1024');
const texP = Promise.all([
  loadKTX(`tex/city_albedo_${RES}.ktx2`, 'alb'), loadKTX(`tex/city_normal_${RES}.ktx2`, 'nrm'), loadKTX(`tex/city_orm_${RES}.ktx2`, 'orm'),
  fetch('data/materials.json').then((r) => r.json()),
]);
// the horizon colours of a sky (for the haze): averaged from the HDR before it goes to the GPU
function skyHaze(tex, info) {
  const { width: W, height: H, data } = tex.image;
  const half = data instanceof Uint16Array, ch = data.length / (W * H);
  const px = (x, y) => { const k = (y * W + x) * ch; return half ? [0, 1, 2].map((i) => THREE.DataUtils.fromHalfFloat(data[k + i])) : [data[k], data[k + 1], data[k + 2]]; };
  const acc = (fn, y0 = 0.47, y1 = 0.5) => { const s = [0, 0, 0]; let n = 0; for (let y = Math.floor(H * y0); y < Math.floor(H * y1); y++) for (let x = 0; x < W; x += 4) { if (!fn(x)) continue; const c = px(x, y); s[0] += c[0]; s[1] += c[1]; s[2] += c[2]; n++; } return s.map((v) => v / Math.max(n, 1)); };
  // column of the sun: u = 0.5 + atan2(dir.x, dir.y) / 2pi in Blender's equirect (see sky_prep.py): find it by azimuth
  const az = info.sun_az * Math.PI / 180;
  const colAz = (x) => { const phi = ((x + 0.5) / W - 0.5) * 2 * Math.PI; return Math.atan2(-Math.cos(phi), Math.sin(phi)); };
  const near = (x) => Math.cos(colAz(x) - az) > 0.85, away = (x) => Math.cos(colAz(x) - az) < 0.2;
  return { sun: acc(near), away: acc(away), all: acc(() => true), zen: acc(() => true, 0.08, 0.3), sun2: acc(near, 0.42, 0.48), all2: acc(() => true, 0.42, 0.48) };
}
const SKIES = {};
async function loadSky(s) {
  if (SKIES[s]) return SKIES[s];
  const [tex, info] = await Promise.all([new HDRLoader().loadAsync(`tex/sky_${s}${LOW ? '' : ''}.hdr`, texProg('sky_' + s)), fetch(`tex/sky_${s}.json`).then((r) => r.json())]);
  const haze = skyHaze(tex, info);
  freeOnUpload(tex); tex.mapping = THREE.EquirectangularReflectionMapping;
  return (SKIES[s] = { tex, info, haze });
}
const sky0 = await loadSky(app.season);

// sun: live with cascaded shadows near the camera; far away the bake's visibility takes over (lite program)
const sun = new THREE.DirectionalLight(0xffffff, 1);
sun.castShadow = params.get('shadows') !== '0';
sun.shadow.mapSize.set(LOW ? 1024 : 2048, LOW ? 1024 : 2048);
sun.shadow.bias = -0.0003; sun.shadow.normalBias = 0.06;
const csm = new CSMShadowNode(sun, { cascades: LOW ? 2 : 4, maxFar: LOW ? 300 : 520, mode: 'practical', lightMargin: 400 });
csm.fade = true;
sun.shadow.shadowNode = csm;
scene.add(sun, sun.target);
G.csmFar.value = LOW ? 300 : 520;

// haze (aerial perspective): the horizon colour of the sky, warmer toward the sun, thicker low over the basin
const fogU = { near: uniform(new THREE.Color()), away: uniform(new THREE.Color()), dens: uniform(1 / +(params.get('fogd') || 14000)), sunH: uniform(new THREE.Vector3(1, 0, 0)) };
scene.fogNode = Fn(() => {
  const d = positionWorld.sub(cameraPosition), dist = length(d), dir = d.div(max(dist, 1e-3));
  const k = max(dot(normalize(vec3(dir.x, dir.y, 0.0).add(vec3(1e-5, 0, 0))), fogU.sunH), 0.0);
  const col = mix(fogU.away, fogU.near, pow(k, 3.0));
  const zMean = cameraPosition.z.add(positionWorld.z).mul(0.5);
  const hk = exp(zMean.sub(60.0).max(0.0).div(-900.0));
  const f = float(1.0).sub(exp(dist.mul(fogU.dens).mul(hk).negate())).mul(0.92);
  return vec4(mix(outNode.rgb, col, f), outNode.a);
})();

const EXP = { autumn: +(params.get('exp') || 0.4), winter: +(params.get('wexp') || 0.3) };
let expo = EXP[app.season];
function applySky(s, S) {
  scene.background = S.tex; scene.backgroundRotation.copy(SKY_ROT);
  scene.environment = S.tex; scene.environmentRotation.copy(SKY_ROT);
  const az = THREE.MathUtils.degToRad(S.info.sun_az), el = THREE.MathUtils.degToRad(Math.max(S.info.sun_el, 3.0));
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el));
  sun.position.copy(dir).multiplyScalar(3000); sun.target.position.set(0, 0, 0);
  // the evening sun: the HDR's own colour, a little less red than the hazy photo
  let E = S.info.sun_rgb.slice(); const Em = Math.max(...E);
  let c = E.map((v) => v / Em); c = [1, Math.max(c[1], 0.52), Math.max(c[2], 0.22)];
  const I = s === 'winter' ? 0.9 : Em * 0.9;
  sun.color.setRGB(c[0], c[1], c[2]); sun.intensity = I;
  G.sunDir.value.copy(dir); G.sunCol.value.set(c[0] * I, c[1] * I, c[2] * I);
  fogU.near.value.setRGB(...S.haze.sun.map((v) => v * 0.9)); fogU.away.value.setRGB(...S.haze.away.map((v) => v * 0.9));
  fogU.sunH.value.set(dir.x, dir.y, 0).normalize();
  G.skyHor.value.set(...S.haze.all2); G.skySun.value.set(...S.haze.sun2); G.skyZen.value.set(...S.haze.zen);
  G.season.value = s === 'winter' ? 1 : 0;
  // the bake holds the autumn sky; the snowy evening's sky is brighter and pinker
  G.irrScale.value = s === 'winter' ? 1.35 : 1.0;
}
applySky(app.season, sky0);
async function setSeason(s) { const S = await loadSky(s); applySky(s, S); }

const [albedo, normal, orm, mats] = await texP;
for (const t of [albedo, normal, orm]) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; freeOnUpload(t); }
albedo.colorSpace = THREE.SRGBColorSpace; normal.colorSpace = THREE.NoColorSpace; orm.colorSpace = THREE.NoColorSpace;
const arrays = { albedo, normal, orm };
G.dbg.value = { alb: 1, irr: 2, sun: 3 }[params.get('dbg')] || 0;
if (params.has('spec')) G.spec.value = +params.get('spec');
const pool = new SurfPool(LOW ? 32 : 56);
const matCity = makeCityMaterial({ arrays, mats: mats.mats, layers: mats.layers });
const matGround = makeGroundMaterial({ arrays, mats: mats.mats, layers: mats.layers, pool });
const matWater = makeWaterMaterial();
const matLite = makeLiteMaterial({ mats: mats.mats });
const texL = new THREE.TextureLoader();
const [leafA, leafN, impT] = await Promise.all(['tex/leaves.png', 'tex/leaves_nrm.png', 'tex/trees_imp.png'].map((u) => texL.loadAsync(u)));
leafA.colorSpace = THREE.NoColorSpace; leafN.colorSpace = THREE.NoColorSpace; impT.colorSpace = THREE.NoColorSpace;
for (const t of [leafA, leafN, impT]) { t.anisotropy = 4; t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; }
const trees = new Trees(scene, { atlas: leafA, atlasN: leafN, imp: impT, arrays, layers: mats.layers });
if (params.get('trees') !== '0') await trees.init('data');
const tiles = new Tiles(scene, { trees, base: SET, mats: mats.mats, matCity, matGround, matWater, matLite, pool, backend: renderer.backend, pre: await preP,
  radii: LOW ? { full: 280, drop: 360, lite: 1800, liteDrop: 2100 } : undefined });
await tiles.init(await indexP);
tiles.cap = GATE;
preP.then((pre) => Promise.allSettled([...pre.values()])).then(() => { if (LD.phase === 'data') { LD.phase = 'gpu'; LD.tg = performance.now(); loadShow(true); } });
function loadStep() {
  if (LD.phase !== 'gpu') return;
  LD.work = tiles.pending(camera.position) + PIPE.pending;
  LD.work0 = Math.max(LD.work0, LD.work);
  if (LD.work === 0) { if (++LD.quiet >= 10) loadDone(); } else LD.quiet = 0;
  if (performance.now() - LD.tg > 60000) loadDone();
  loadShow();
}
function loadDone(show = true) {
  LD.phase = 'done'; tiles.cap = null;
  if (show) { ui.prep(1, 'gpu'); ui.ready(); }
  window.KYO && (KYO.prepared = true);
}
function terrainZ(x, y) { const w = tiles.sample(x, y); return w.z !== undefined ? w.z : (farGround(x, y) || 30); }

// ---------------------------------------------------------------- post: GTAO on indirect light, TRAA, bloom, an evening grade
// split toning in scene-linear (before the tone curve): shadows cooler and a little deeper, lights warmer, a touch
// more colour, a soft vignette.  `expoU` keeps the split point where the eye sees it.
const GR = { expo: uniform(0.5), amt: uniform(params.has('grade') ? +params.get('grade') : 1.6) };
const grade = (c) => Fn(() => {
  const col = c.rgb, L = dot(col, vec3(0.2126, 0.7152, 0.0722)).mul(GR.expo);
  const hiK = smoothstep(0.08, 0.6, L);
  const tint = mix(vec3(0.90, 0.96, 1.10), vec3(1.10, 1.0, 0.86), hiK);
  let g = col.mul(mix(vec3(1.0), tint, GR.amt)).mul(mix(float(1.0), mix(float(0.86), float(1.0), hiK), GR.amt));
  const gl = dot(g, vec3(0.2126, 0.7152, 0.0722));
  g = mix(vec3(gl), g, mix(float(1.0), float(1.12), GR.amt));
  const d = screenUV.sub(0.5).mul(vec2(1.0, 0.75));
  const vig = float(1.0).sub(dot(d, d).mul(0.6).mul(GR.amt.min(1.0)));
  return vec4(g.mul(vig).max(vec3(0.0)), c.a);
})();
const pipeline = new THREE.RenderPipeline(renderer);
const usePost = params.has('post') ? params.get('post') !== '0' : !LOW;
if (usePost) {
  const prePass = pass(scene, camera);
  prePass.setMRT(mrt({ output: packNormalToRGB(normalView) }));
  prePass.transparent = false;
  const preNormal = sample((uv) => unpackRGBToNormal(prePass.getTextureNode().sample(uv)));
  const preDepth = prePass.getTextureNode('depth');
  const aoPass = ao(preDepth, preNormal, camera);
  aoPass.resolutionScale = 0.5;
  aoPass.distanceExponent.value = 1; aoPass.radius.value = 0.8; aoPass.scale.value = 1.0;
  aoPass.useTemporalFiltering = params.get('aa') !== '0';     // rotate the noise each frame so TRAA averages it away
  const scenePass = pass(scene, camera);
  if (params.get('ao') !== '0') scenePass.contextNode = builtinAOContext(aoPass.getTextureNode().sample(screenUV).r);
  scenePass.setMRT(mrt({ output, velocity }));
  // a low sun on glossy glass can exceed half-float range: an Inf would spread through bloom and TRAA (black screen)
  const col = scenePass.getTextureNode('output').min(vec4(2000.0)).max(vec4(0.0));
  const aa = params.get('aa') === '0' ? col : traa(col, scenePass.getTextureNode('depth'), scenePass.getTextureNode('velocity'), camera);
  const bl = bloom(aa, 0.06, 0.4, 4.0);
  pipeline.outputNode = grade(aa.add(bl));
} else {
  pipeline.outputNode = grade(pass(scene, camera));
}

const controls = new Controls(camera, renderer.domElement, { tiles, ground: farGround });
app.controls = controls;                         // the touch buttons (ui.js) climb, descend and speed up through it
// the basin and its hills out to the horizon (loaded once; drawn after the tiles so their pixels are rejected early)
const farP = params.get('far') === '0' ? Promise.resolve(null) : loadFar(scene, { G, base: 'data/far', backend: renderer.backend, renderOrder: 50 }).catch((e) => { console.warn('far', e); return null; });
// touch joystick
{
  const st = document.createElement('div'); st.className = 'stick'; st.innerHTML = '<i></i>'; document.querySelector('.ui').appendChild(st);
  const knob = st.querySelector('i'); let id = null;
  const set = (e) => { const r = st.getBoundingClientRect(); let x = (e.clientX - r.left - 55) / 45, y = (e.clientY - r.top - 55) / 45; const l = Math.hypot(x, y); if (l > 1) { x /= l; y /= l; }
    controls.move.x = x; controls.move.y = y; knob.style.transform = `translate(${x * 34}px, ${y * 34}px)`; };
  st.addEventListener('pointerdown', (e) => { id = e.pointerId; st.setPointerCapture(id); set(e); e.stopPropagation(); });
  st.addEventListener('pointermove', (e) => { if (e.pointerId === id) set(e); });
  const end = () => { id = null; controls.move.x = controls.move.y = 0; knob.style.transform = ''; };
  st.addEventListener('pointerup', end); st.addEventListener('pointercancel', end);
}
const minimap = new MiniMap(document.querySelector('.ui'), () => ui.lang);
// sound: the Goldberg Variations on a physical-model piano, footsteps by surface, water, temple bells (audio.js)
const audio = createAudio();
addEventListener('kyo-sound', (e) => { if (e.detail) audio.start(); audio.setEnabled(e.detail); });
const SOUNDS = await fetch('data/sounds.json').then((r) => r.json()).catch(() => ({ bells: [], falls: [], interiors: [] }));
const npEl = document.createElement('div'); npEl.className = 'np'; document.querySelector('.ui').appendChild(npEl);
const aud = { mode: 'title', walkSpeed: 0, surf: 0, season: 0, water: 0, fall: 0, bells: [], camZ: 2, interior: null };
let audT = 0, npT = 0;
function audState(dt) {
  const p = camera.position;
  aud.mode = app.mode; aud.season = app.season === 'winter' ? 1 : 0;
  aud.walkSpeed = app.mode === 'walk' ? Math.hypot(controls.vel.x, controls.vel.y) : 0;
  const w = tiles.sample(p.x, p.y);
  aud.surf = w.surf ?? 0; aud.camZ = w.z !== undefined ? p.z - w.z : 50;
  if ((audT -= dt) <= 0) {
    audT = 0.3;
    let n = 0; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; if (tiles.sample(p.x + Math.cos(a) * 6, p.y + Math.sin(a) * 6).water) n++; }
    aud.water = n / 8;
    let fd = 1e9; for (const f of SOUNDS.falls) fd = Math.min(fd, Math.hypot(f[0] - p.x, f[1] - p.y)); aud.fall = Math.max(0, 1 - fd / 40);
    camera.getWorldDirection(camDir); const yaw = Math.atan2(camDir.y, camDir.x);
    aud.bells = SOUNDS.bells.map((b, i) => ({ id: i, dist: Math.hypot(b[0] - p.x, b[1] - p.y, 0), az: Math.atan2(b[1] - p.y, b[0] - p.x) - yaw })).filter((b) => b.dist < 800)
      .sort((a, b) => a.dist - b.dist).slice(0, 3).map((b) => ({ ...b, az: -Math.atan2(Math.sin(b.az), Math.cos(b.az)) }));
    aud.interior = null;
    for (const r of SOUNDS.interiors) {
      const dx = p.x - r.c[0], dy = p.y - r.c[1], u = dx * r.axis[0] + dy * r.axis[1], v = -dx * r.axis[1] + dy * r.axis[0];
      if (Math.abs(u) < r.half[0] && Math.abs(v) < r.half[1] && aud.camZ < 6) aud.interior = r.id;
    }
  }
  audio.update(dt, aud);
  if ((npT -= dt) <= 0) {
    npT = 1;
    const np = app.sound && audio.nowPlaying ? audio.nowPlaying() : null;
    const t = np && np.index >= 0 ? (ui.lang === 'ja' ? `J.S.バッハ　ゴルトベルク変奏曲　${np.title_ja}` : `J. S. Bach — Goldberg Variations — ${np.title}`) : '';
    if (npEl.textContent !== t) npEl.textContent = t;
  }
}
const snow = new Snow(scene, LOW ? 3000 : 9000);
const statues = new Statues(scene, { mats: mats.mats });
// white water at the river weirs (small: loaded at once)
const weirs = new Weirs(scene); weirs.load('data').catch((e) => console.warn('weirs', e));
const STATUE_AT = [1185, 242];
const camDir = new THREE.Vector3();
// title camera: standing where the walk begins, looking about slowly once the view is ready
let swayT = 0;
const titleYaw = () => START.yaw + 0.08 * Math.sin(swayT * 0.05);
function titleCam(dt) {
  if (LD.phase === 'done') swayT += dt;
  const w = tiles.sample(START.at[0], START.at[1]), z = (w.z != null ? w.z + 1.6 : 30), yaw = titleYaw();
  camera.position.set(START.at[0], START.at[1], z);
  camera.lookAt(START.at[0] + Math.cos(yaw), START.at[1] + Math.sin(yaw), z + 0.22);
}

// eye adaptation: narrow streets (little open ground around) get more exposure, as eyes would
function openness(x, y) {
  let open = 0, n = 0;
  for (const r of [4, 10]) for (let k = 0; k < 12; k++) {
    const a = k / 12 * Math.PI * 2, w = tiles.sample(x + Math.cos(a) * r, y + Math.sin(a) * r);
    if (w.z === undefined) continue;
    n++; if (!w.blocked || w.water) open++;
  }
  return n ? open / n : 1;
}
let camOpen = 1, openT = 0, camCov = 0;

// ---------------------------------------------------------------- loop
const clock = new THREE.Clock();
let frames = 0, fpsT = 0, fps = 0;
// snap: the eye's adaptation arrives at once (a film's cut)
function step(dt, dtRaw = dt, pose = null, snap = false) {
  G.time.value += dt;
  if (app.mode === 'title') titleCam(dt);
  if (pose) pose(dt); else if (app.mode !== 'title') controls.update(dt);
  const tu = performance.now(); tiles.update(camera); trees.update(camera, dt); const tu2 = performance.now();
  snow.update(app.season === 'winter');
  if (statues.state === 'idle' && Math.hypot(camera.position.x - STATUE_AT[0], camera.position.y - STATUE_AT[1]) < 600) statues.load('data').catch((e) => { console.warn('statues', e); });
  statues.update(camera, dt);
  if (tu2 - tu > 8) perfLog(['tiles.update', Math.round(tu2 - tu), Math.round(tu)]);
  if (snap) openT = 0;
  if ((openT -= dt) <= 0) {
    openT = 0.25; const oc = app.mode === 'walk' ? openness(camera.position.x, camera.position.y) : 1; camOpen += (oc - camOpen) * (snap ? 1 : 0.35);
    // under a roof (a hall, a gate, a deep veranda): the eye opens up for the dimmer light
    const cv = app.mode === 'walk' && tiles.sample(camera.position.x, camera.position.y).covered ? 1 : 0; camCov += (cv - camCov) * (snap ? 1 : 0.3);
  }
  const expT = EXP[app.season] * (1 + 0.45 * (1 - camOpen)) * (1 + 1.4 * camCov);
  expo += (expT - expo) * (snap ? 1 : Math.min(1, dt * 1.5));
  renderer.toneMappingExposure = expo * app.bright; GR.expo.value = renderer.toneMappingExposure;
  audState(dt);
  minimap.show(app.mode !== 'title');
  if (app.mode !== 'title') { camera.getWorldDirection(camDir); minimap.update(dt, camera.position.x, camera.position.y, Math.atan2(camDir.y, camDir.x)); }
  dynRes(dtRaw);
}
function frame() {
  const dtRaw = clock.getDelta(), dt = Math.min(0.1, dtRaw);
  step(dt, dtRaw);
  const tr = performance.now(); pipeline.render(); const tr2 = performance.now();
  if (tr2 - tr > 12) perfLog(['render', Math.round(tr2 - tr), Math.round(tr)]);
  if (LD.phase !== 'done') loadStep();
  if (dtRaw > 0.05) perfLog(['FRAME', Math.round(dtRaw * 1000), Math.round(tr2)]);
  frames++; fpsT += dt; if (fpsT > 1) { fps = frames / fpsT; frames = 0; fpsT = 0; }
}
renderer.setAnimationLoop(frame);
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setPixelRatio(pixelRatio() * dyn.k); renderer.setSize(innerWidth, innerHeight); });

// ---------------------------------------------------------------- debug / automation hooks
const KYO = window.KYO = {
  dyn, low: LOW, pipes: PIPE, minimap, snow, statues, audio, aud, load: LD, step, G, csm, sun, fogU, EXP,
  stopLoop() { renderer.setAnimationLoop(null); },
  ready: false, camera, scene, tiles, renderer, pipeline, controls, app, ui,
  mode(m) { if (app.mode === 'title') ui.start(m); else app.setMode(m); },
  walkAt(x, y, yaw = 0) { if (app.mode === 'title') ui.start('walk'); app.setMode('walk'); camera.position.set(x, y, terrainZ(x, y) + 1.6); controls.yaw = yaw; controls.pitch = 0; controls.walkZ = null; },
  place(id) { if (app.mode === 'title') ui.start('walk'); app.goPlace(PLACES.find((p) => p.id === id)); },
  season(s) { app.season = s; return setSeason(s).then(() => ui.refresh()); },
  look(px, py, pz, tx, ty, tz) { if (app.mode === 'title') ui.start('fly'); app.setMode('fly'); camera.position.set(px, py, pz); camera.lookAt(tx, ty, tz); controls.syncFromCamera(); },
  info() { return { fps: Math.round(fps), ...tiles.stats(), trees: trees.stats(), cam: camera.position.toArray().map((v) => +v.toFixed(1)) }; },
  trees,
  // a promotional film (tools/film.mjs): the sound engine offline, and the bar lines of a movement
  renderOffline, wavBytes,
  async barTimes(mi = 0, n = 80) {
    const sc = await fetch('data/goldberg.json').then((r) => r.json()), mv = sc.movements[mi], { T, len } = beatTimes(mv, mi);
    const bpb = mv.meter[0] * 4 / mv.meter[1], out = []; for (let b = 0; b <= n; b++) out.push(T(b * bpb)); return { bars: out, len, bpb };
  },
  async capture(type = 'image/jpeg') { return (await KYO.frameCanvas()).toDataURL(type, 0.9).split(',')[1]; },
  async freeze() {
    document.getElementById('veil')?.remove();
    const c = await KYO.frameCanvas(), d = renderer.domElement;
    c.style.cssText = `position:fixed;left:0;top:0;width:${d.clientWidth}px;height:${d.clientHeight}px;z-index:1;pointer-events:none`;
    document.body.appendChild(c); return true;
  },
  async frameCanvas() {
    const w = renderer.domElement.width, h = renderer.domElement.height;
    if (!KYO._rt || KYO._rt.width !== w || KYO._rt.height !== h) KYO._rt = new THREE.RenderTarget(w, h, { type: THREE.UnsignedByteType, colorSpace: THREE.SRGBColorSpace });
    for (let k = 0; k < 100; k++) {
      renderer.setRenderTarget(KYO._rt); pipeline.render(); renderer.setRenderTarget(null);
      if (PIPE.pending === 0) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    const px = await renderer.readRenderTargetPixelsAsync(KYO._rt, 0, 0, w, h);
    const c2 = document.createElement('canvas'); c2.width = w; c2.height = h; const g = c2.getContext('2d');
    const img = g.createImageData(w, h);
    const row = w * 4, padded = Math.ceil(row / 256) * 256;
    const stride = px.length >= padded * (h - 1) + row && padded !== row ? padded : row;
    if (stride === row) img.data.set(px.subarray(0, row * h));
    else for (let y = 0; y < h; y++) img.data.set(px.subarray(y * stride, y * stride + row), y * row);
    g.putImageData(img, 0, 0);
    return c2;
  },
  async settle(ms = 1500) {
    const t0 = performance.now();
    while (performance.now() - t0 < 30000) {
      tiles.update(camera);
      const pending = [...tiles.tiles.values()].some((t) => t.state === 'loading') || tiles.loading > 0 || tiles.liteLoading > 0 || PIPE.pending > 0;
      if (!pending && performance.now() - t0 > ms) break;
      await new Promise((r) => setTimeout(r, 100));
    }
  },
};
KYO.ready = true;
KYO.THREE = THREE;
