// VENEZIA — viewer entry.  three.js WebGPU renderer, z-up world (x east, y north, metres; water at z = 0).
import * as THREE from 'three/webgpu';
import { pass, mrt, output, normalView, velocity, screenUV, builtinAOContext, directionToColor, colorToDirection, sample, vec2, float } from 'three/tsl';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { CSMShadowNode } from 'three/addons/csm/CSMShadowNode.js';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { traa } from 'three/addons/tsl/display/TRAANode.js';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { Tiles, perfLog, prefetch } from './tiles.js';
import { makeCityMaterial, makeLiteMaterial, G } from './citymat.js';
import { LightmapPool } from './facade.js';
import { makeWater } from './water.js';
import { Controls } from './controls.js';
import { Props } from './props.js';
import { Gondola, GondolaRide } from './gondola.js';
import { UI, PLACES } from './ui.js';
import { createAudio, _scores } from './audio.js';
import { MiniMap } from './minimap.js';

THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const JA = location.hash !== '#en' && (location.hash === '#ja' || (navigator.language || '').startsWith('ja'));
// phones and tablets get a lighter page: an Android phone showed only a black screen (the full page held about 1.5 GB
// of JS memory and 0.9 GB on the GPU on a walk to the Rialto).  Less resolution, MSAA instead of the post chain, two
// smaller shadow cascades, a 1k sky, shorter streaming radii.  ?low=1 / ?low=0 force it either way.
const UAD = navigator.userAgentData;
const LOW = params.has('low') ? params.get('low') !== '0'
  : (UAD ? UAD.mobile || UAD.platform === 'Android' : /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))
    || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent))           // iPadOS says Macintosh
    || (navigator.deviceMemory > 0 && navigator.deviceMemory <= 4);                      // small machines too

// headless Chrome sometimes needs a moment before an adapter is available
for (let i = 0; i < 30 && navigator.gpu; i++) { if (await navigator.gpu.requestAdapter()) break; await new Promise((r) => setTimeout(r, 150)); }
const renderer = new THREE.WebGPURenderer({ canvas: $('c'), antialias: LOW, powerPreference: 'high-performance', forceWebGL: params.get('gl') === '1' });
await renderer.init();
// without WebGPU three.js falls back to WebGL2, which cannot carry this city (frames take many seconds and the
// screen stays black) — say what is needed instead
if (!renderer.backend.isWebGPUBackend && params.get('gl') !== '1') {
  const m = document.createElement('div'); m.className = 'nogpu';
  m.innerHTML = JA
    ? '<b>VENEZIA</b><p>このデモには WebGPU が必要です。</p><p>Windows・macOS・Android の Chrome / Edge、または Safari 26 以降で開いてください。</p><p>Linux の Chrome では chrome://flags で「Unsafe WebGPU Support」と「Vulkan」を Enabled にして再起動すると使えます。</p>'
    : '<b>VENEZIA</b><p>This demo needs WebGPU.</p><p>Open it in Chrome or Edge on Windows, macOS or Android, or in Safari 26 or later.</p><p>On Linux, enable “Unsafe WebGPU Support” and “Vulkan” in chrome://flags and relaunch Chrome.</p>';
  document.body.appendChild(m); document.querySelector('.title .prep')?.remove();
  throw new Error('WebGPU unavailable');
}
// a GPU that runs out of memory (or resets) would leave the canvas black: say so instead
function gpuGone(why) {
  if (document.querySelector('.nogpu')) return;
  const m = document.createElement('div'); m.className = 'nogpu';
  const lite = LOW ? '' : (JA ? '<p>軽い表示でも開けます: アドレスの末尾に ?low=1</p>' : '<p>A lighter version opens with ?low=1 at the end of the address.</p>');
  m.innerHTML = (JA ? '<b>VENEZIA</b><p>GPU のメモリが足りなくなり、描画が止まりました。</p><p>ページを再読み込みしてください。</p>'
    : '<b>VENEZIA</b><p>The GPU ran out of memory and stopped drawing.</p><p>Please reload the page.</p>') + lite + `<p>(${String(why).replace(/[<>&]/g, '')})</p>`;
  document.body.appendChild(m);
}
if (renderer.backend.isWebGPUBackend) {
  const dev = renderer.backend.device;
  dev.lost.then((i) => { if (i.reason !== 'destroyed') gpuGone(i.message || 'device lost'); });
  dev.addEventListener('uncapturederror', (e) => { if (typeof GPUOutOfMemoryError !== 'undefined' && e.error instanceof GPUOutOfMemoryError) gpuGone('out of memory'); });
}
// drawing size capped near 3.7 megapixels (a Retina MacBook or a 4K monitor would otherwise draw 6-8 MP every frame);
// a phone draws at most 1.1 MP
const pixelRatio = () => +(params.get('pr') || 0) || Math.min(devicePixelRatio, LOW ? 1.5 : 2, Math.sqrt((LOW ? 1.1e6 : 3.7e6) / (innerWidth * innerHeight)));
renderer.setPixelRatio(pixelRatio());
// dynamic resolution: a slow GPU (a laptop) drops the drawing size step by step, and climbs back when there is room
const dyn = { k: 1, acc: 0, n: 0, good: 0, off: params.has('pr') || params.has('shot') || navigator.webdriver === true };
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
renderer.toneMapping = params.get('tm') === 'agx' ? THREE.AgXToneMapping : params.get('tm') === 'neutral' ? THREE.NeutralToneMapping : THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = +(params.get('exp') || 0.3);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
// the scene's render pipelines are made with createRenderPipelineAsync, and an object is drawn from the first frame its
// pipeline is ready.  Made the usual way, a pipeline compiles on the GPU process's main thread, and with a cold shader
// cache the city's took seconds each: the page's own thread waited behind them for up to half a minute ("Page
// Unresponsive").  Drawing done once (the sky's environment maps) or in the post passes stays as it was: skipped, a
// one-time draw would never happen.
const PIPE = { pending: 0, made: 0 };
if (renderer.backend.isWebGPUBackend && params.get('async') !== '0') {
  const pipes = renderer._pipelines;
  const sink = { push(p) { PIPE.pending++; PIPE.made++; p.then(() => PIPE.pending--); } };   // three resolves it either way
  pipes.updateForRender = (ro) => pipes.getForRender(ro, ro.scene === scene ? sink : null);   // a list: three goes async
}
const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 9000);
camera.up.set(0, 0, 1);
camera.layers.enable(1);
const START = PLACES[0];                         // the first view: walking in Piazza San Marco
const EYE_Z = 1.1 + 1.62;                        // ground + eye until the walk raster is in
camera.position.set(START.at[0], START.at[1], EYE_Z); camera.lookAt(START.at[0] + Math.cos(START.yaw), START.at[1] + Math.sin(START.yaw), EYE_Z);

// ---------------------------------------------------------------- app state + UI
const app = {
  mode: 'title', speed: 1, night: false, sound: false, routeId: 'grand', rowing: false,
  // brightness (screens differ: a MacBook shows the shade much darker than a desktop monitor); remembered
  bright: (() => { try { return Math.min(2.5, Math.max(0.5, +localStorage.getItem('ven-bright') || 1)); } catch (e) { return 1; } })(),
  setBright(v) { this.bright = v; try { localStorage.setItem('ven-bright', String(v)); } catch (e) { /* private mode */ } },
  begin(m) {
    if (LD.phase !== 'done') loadDone(false);      // started before the first view was ready (automation)
    this.started = true;
    if (m === 'boat') this.setRoute(this.routeId);
    else if (m === 'walk') { const yaw = titleYaw(); this.goPlace(START); controls.yaw = yaw; }   // on from the title's view
    else this.setMode('fly');
    if (!this.sound) this.toggleSound();          // the start click is the gesture that lets the sound begin
  },
  setMode(m) {
    if (m === 'walk' && this.mode !== 'walk') {
      // step off where the camera is (from the boat: onto the nearest fondamenta)
      if (this.mode === 'boat') { camera.position.set(ride.pos.x, ride.pos.y, 3); controls.yaw = ride.heading; }
      controls.pitch = 0;
    }
    if (m === 'fly' && this.mode === 'boat') { controls.syncFromCamera(); }
    this.mode = m; controls.setMode(m); ui.refresh();
  },
  goPlace(p) {
    this.setMode(p.mode);           // first: leaving the boat would otherwise put the camera back at the gondola
    if (p.at) { camera.position.set(p.at[0], p.at[1], 3); controls.yaw = p.yaw; controls.pitch = 0.02; }
    controls.walkZ = null;
  },
  setRoute(id) { this.routeId = id; ride.setRoute(id, 0); ride.speed = this.speed; this.rowing = false; this.setMode('boat'); },
  setSpeed(s) { this.speed = s; ride.speed = s; ui.refresh(); },
  toggleNight() { this.night = !this.night; setNight(this.night); ui.refresh(); },
  toggleSound() { this.sound = !this.sound; window.dispatchEvent(new CustomEvent('ven-sound', { detail: this.sound })); ui.refresh(); },
};
const ui = new UI(app);

// ---------------------------------------------------------------- loading
// The first view comes first.  Its bytes (sky, texture sets, the four tiles around the Piazza and the far view within
// 700 m) download together and fill the bar; then the shaders and the near detail it needs, while the veil still
// covers the canvas.  The start button shows when nothing is left to draw; the rest of the island streams in after.
const SET = 'data/' + (params.get('set') || 'island');
const GATE = { x: START.at[0], y: START.at[1], full: 100, lite: 700 };
const LD = { tex: new Map(), got: 0, want: 0, phase: 'data', work: 0, work0: 0, quiet: 0, shown: 0, tg: 0 };
function loadShow(force = false) {
  const now = performance.now(); if (!force && now - LD.shown < 60) return; LD.shown = now;
  let f = -1;                                     // sizes not known yet: the bar only sweeps
  if (LD.phase === 'data') {
    let a = LD.got, b = LD.want;
    for (const [l, t] of LD.tex.values()) { a += l; b += t; }
    if (LD.tex.size >= 5 && LD.want > 0) f = 0.9 * Math.min(1, a / b);
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

// texture data stays on the GPU only once uploaded (the KTX2 arrays and the skies: about 150 MB less in the tab)
function freeOnUpload(t) {
  t.onUpdate = () => {
    for (const m of t.mipmaps || []) if (m.data) m.data = new m.data.constructor(0);
    if (t.image && t.image.data && t.image.data.length) t.image.data = new t.image.data.constructor(0);
    t.onUpdate = null;
  };
}
// sky: equirect authored in Blender's convention; this rotation maps our z-up world to three's lookup
const SKY_ROT = new THREE.Euler().setFromRotationMatrix(new THREE.Matrix4().set(-1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1));
const SKY = LOW ? '_1k' : '';             // the environment maps three.js makes from the sky scale with it (2k: ~190 MB on the GPU)
// textures (started now, so everything downloads together)
const ktx = new KTX2Loader().setTranscoderPath('basis/').detectSupport(renderer);
const loadKTX = (u, k) => new Promise((res, rej) => ktx.load(u, res, texProg(k), rej));
const RES = params.get('tex') || (LOW ? '512' : '1024');        // a phone: the 512 sets (a quarter of the memory and download)
const texP = Promise.all([
  loadKTX(`tex/city_albedo_${RES}.ktx2`, 'alb'), loadKTX(`tex/city_normal_${RES}.ktx2`, 'nrm'), loadKTX(`tex/city_orm_${RES}.ktx2`, 'orm'),
  fetch('data/materials.json').then((r) => r.json()), new THREE.TextureLoader().loadAsync('tex/water_nrm.png'), loadKTX(RES === '512' ? 'tex/art_512.ktx2' : 'tex/art.ktx2', 'art'),
]);
const [skyTex, skyInfo] = await Promise.all([new HDRLoader().loadAsync(`tex/sky_day${SKY}.hdr`, texProg('sky')), fetch('tex/sky_day.json').then((r) => r.json())]);
freeOnUpload(skyTex);
skyTex.mapping = THREE.EquirectangularReflectionMapping;
scene.background = skyTex; scene.backgroundRotation.copy(SKY_ROT);
scene.environment = skyTex; scene.environmentRotation.copy(SKY_ROT);

// sun (direct light is live; the bake holds sky + bounce)
const az = THREE.MathUtils.degToRad(skyInfo.sun_az), el = THREE.MathUtils.degToRad(skyInfo.sun_el);
const sunDir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el));
const E = skyInfo.sun_rgb; const Emax = Math.max(...E);
const sun = new THREE.DirectionalLight(new THREE.Color(E[0] / Emax, E[1] / Emax, E[2] / Emax), Emax);
sun.position.copy(sunDir).multiplyScalar(2000); sun.target.position.set(0, 0, 0);
sun.castShadow = params.get('shadows') !== '0';
sun.shadow.mapSize.set(LOW ? 1024 : 2048, LOW ? 1024 : 2048);
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.08;
const csm = new CSMShadowNode(sun, { cascades: LOW ? 2 : 3, maxFar: LOW ? 250 : 400, mode: 'practical', lightMargin: 200 });
csm.fade = true;
sun.shadow.shadowNode = csm;
scene.add(sun, sun.target);

// textures
const [albedo, normal, orm, mats, waterN, art] = await texP;
art.colorSpace = THREE.SRGBColorSpace; art.anisotropy = 8; art.minFilter = THREE.LinearMipmapLinearFilter;
for (const t of [albedo, normal, orm]) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.minFilter = params.get('nomip') ? THREE.LinearFilter : THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; }
albedo.colorSpace = THREE.SRGBColorSpace; normal.colorSpace = THREE.NoColorSpace; orm.colorSpace = THREE.NoColorSpace;
for (const t of [albedo, normal, orm, art]) freeOnUpload(t);
const arrays = { albedo, normal, orm };
const pool = new LightmapPool(LOW ? 16 : 40);
G.dbg.value = { alb: 1, irr: 2, nrm: 3, raw: 4 }[params.get('dbg')] || 0;
const matStatic = makeCityMaterial({ arrays, mats: mats.mats, layers: mats.layers, lighting: 'vertex', hasNight: true, art });
const matNear = makeCityMaterial({ arrays, mats: mats.mats, layers: mats.layers, lighting: 'atlas', lmPool: pool, hasAux: true });

const water = params.get('refl') === '0' ? null : makeWater(scene, waterN, { reflScale: LOW ? 0.3 : 0.5 });

const matInst = makeCityMaterial({ arrays, mats: mats.mats, layers: mats.layers, lighting: 'inst' });
const matLite = makeLiteMaterial({ arrays, mats: mats.mats, layers: mats.layers });
const matLiteFac = makeLiteMaterial({ arrays, mats: mats.mats, layers: mats.layers, facade: true });
const props = new Props(matInst);
await props.init(SET);
const tiles = new Tiles(scene, { base: SET, mats: mats.mats, matStatic, matNear, matLite, matLiteFac, pool, props, backend: renderer.backend, pre: await preP,
  radii: LOW ? { near: 100, chunk: 50, props: 160, full: 260, drop: 340, hero: 200 } : undefined });
await tiles.init(await indexP);
tiles.cap = GATE; tiles.chunkMs = 12.0;          // nothing beyond the first view yet; near facades faster behind the veil
// the bytes are in when the textures are (awaited above) and the first view's tiles have arrived
preP.then((pre) => Promise.allSettled([...pre.values()])).then(() => { if (LD.phase === 'data') { LD.phase = 'gpu'; LD.tg = performance.now(); loadShow(true); } });
function loadStep() {
  if (LD.phase !== 'gpu') return;
  LD.work = tiles.pending(camera.position) + PIPE.pending;
  LD.work0 = Math.max(LD.work0, LD.work);
  if (LD.work === 0) { if (++LD.quiet >= 10) loadDone(); } else LD.quiet = 0;
  if (performance.now() - LD.tg > 60000) loadDone();          // never hold the start back for good
  loadShow();
}
function loadDone(show = true) {
  LD.phase = 'done'; tiles.cap = null; tiles.chunkMs = 4.0;
  if (show) { ui.prep(1, 'gpu'); ui.ready(); }
  window.VEN && (VEN.prepared = true);
}

// ---------------------------------------------------------------- post: GTAO on indirect light, TRAA, bloom
const pipeline = new THREE.RenderPipeline(renderer);
const usePost = params.has('post') ? params.get('post') !== '0' : !LOW;     // a phone: MSAA, no post chain
if (usePost) {
  const prePass = pass(scene, camera);
  prePass.setMRT(mrt({ output: directionToColor(normalView) }));
  prePass.transparent = false;
  const preNormal = sample((uv) => colorToDirection(prePass.getTextureNode().sample(uv)));
  const preDepth = prePass.getTextureNode('depth');
  const aoPass = ao(preDepth, preNormal, camera);
  aoPass.resolutionScale = 0.5;
  aoPass.distanceExponent.value = 1; aoPass.radius.value = 0.6; aoPass.scale.value = 1.0;
  const scenePass = pass(scene, camera);
  scenePass.contextNode = builtinAOContext(aoPass.getTextureNode().sample(screenUV).r);
  scenePass.setMRT(mrt({ output, velocity }));
  const col = scenePass.getTextureNode('output');
  const aa = traa(col, scenePass.getTextureNode('depth'), scenePass.getTextureNode('velocity'), camera);
  const bl = bloom(aa, 0.05, 0.3, 6.0);
  pipeline.outputNode = aa.add(bl);
} else {
  pipeline.outputNode = pass(scene, camera);
}

// gondola on a canal route (always afloat; the boat mode seats the camera in it)
const canals = await fetch('data/canals.json').then((r) => r.json());
const gondola = new Gondola({ tex: skyTex, rot: SKY_ROT });
const ride = new GondolaRide(scene, gondola, tiles, canals.routes);
const controls = new Controls(camera, renderer.domElement, { tiles, ride });
// sky visibility around the gondola (its materials are lit by the sky probe, not by the bake)
function openness(x, y) {
  let open = 0, n = 0;
  for (const r of [5, 12]) for (let k = 0; k < 12; k++) {
    const a = k / 12 * Math.PI * 2; const w = tiles.sample(x + Math.cos(a) * r, y + Math.sin(a) * r);
    n++; if (w.water || w.z != null || w.z === undefined) open++;
  }
  return open / n;
}
let openK = 0.5, camOpen = 1;
// interiors: eye adaptation (exposure) and a label while inside
const interiors = (await fetch('data/interiors.json').then((r) => r.json()).catch(() => ({ interiors: [] }))).interiors;
function inPoly(P, x, y) { let c = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) { const a = P[i], b = P[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
const EXP = { day: +(params.get('exp') || 0.3), night: +(params.get('nexp') || 1.6) }; EXP.out = EXP.day;
let expo = EXP.out;

// night: night sky + environment, the sun off (moonlight is in the night bake), brighter eye
let nightTex = null;
async function setNight(on) {
  if (on && !nightTex) { nightTex = await new HDRLoader().loadAsync(`tex/sky_night${SKY}.hdr`); nightTex.mapping = THREE.EquirectangularReflectionMapping; freeOnUpload(nightTex); }
  G.night.value = on ? 1 : 0;
  const t = on ? nightTex : skyTex;
  scene.background = t; scene.environment = t;
  for (const m of Object.values(gondola.mats)) { m.envMap = t; m.needsUpdate = true; }
  sun.intensity = on ? 0 : Emax;
  EXP.out = on ? EXP.night : EXP.day;
}
addEventListener('keydown', (e) => {
  if (e.code === 'KeyR' && app.mode === 'boat') { app.rowing = !app.rowing; ride.mode = app.rowing ? 'manual' : 'auto'; if (!app.rowing) ride.setRoute(app.routeId, ride.s); ui.refresh(); }
});
const minimap = new MiniMap(document.querySelector('.ui'), () => ui.lang);
const camDir = new THREE.Vector3();
// sound: solo piano that follows the scene, and only the natural sounds whose cause you can see (audio.js)
const audio = createAudio();
const aud = { mode: 'title', interior: null, night: false, walkSpeed: 0, boatPhase: 0, boatSpeed: 0, water: 0, piazza: 0, camZ: 0 };
addEventListener('ven-sound', (e) => { if (e.detail) audio.start(); audio.setEnabled(e.detail); });
const PZU = [Math.sin(70.5 * Math.PI / 180), Math.cos(70.5 * Math.PI / 180)];
let waterT = 0;
function audState(dt, inside) {
  const p = camera.position;
  aud.mode = app.mode; aud.interior = inside ? inside.id : null; aud.night = app.night; aud.camZ = p.z;
  aud.walkSpeed = app.mode === 'walk' ? Math.hypot(controls.vel.x, controls.vel.y) : 0;
  aud.boatPhase = (ride.t / 2.4) % 1;
  aud.boatSpeed = app.mode === 'boat' ? Math.max(0, ride.vel) : 0;
  // how much water is within a few metres (the boat is on it); a few raster lookups, four times a second
  if ((waterT -= dt) <= 0) {
    waterT = 0.25;
    if (app.mode === 'boat') aud.water = 1;
    else { let n = 0; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; if (tiles.sample(p.x + Math.cos(a) * 5, p.y + Math.sin(a) * 5).water) n++; } aud.water = n / 8; }
  }
  // Piazza San Marco (piazza frame: u -140..35 between the Napoleonica and the Basilica, v -20..35), soft 20 m edge
  const pu = p.x * PZU[0] + p.y * PZU[1], pv = -p.x * PZU[1] + p.y * PZU[0];
  aud.piazza = Math.max(0, 1 - Math.hypot(Math.max(-140 - pu, 0, pu - 35), Math.max(-20 - pv, 0, pv - 35)) / 20);
  audio.update(dt, aud);
}
// touch joystick (walk / fly / rowing)
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
// title camera: standing where the walk begins, looking about slowly once the view is ready
let swayT = 0;
const titleYaw = () => START.yaw + 0.1 * Math.sin(swayT * 0.06);
function titleCam(dt) {
  if (LD.phase === 'done') swayT += dt;
  const w = tiles.sample(START.at[0], START.at[1]), z = (w.z != null ? w.z + 1.62 : EYE_Z), yaw = titleYaw();
  camera.position.set(START.at[0], START.at[1], z);
  camera.lookAt(START.at[0] + Math.cos(yaw), START.at[1] + Math.sin(yaw), z + 0.02);
}

// ---------------------------------------------------------------- loop
const clock = new THREE.Clock();
let frames = 0, fpsT = 0, fps = 0;
// everything a frame does but drawing.  pose (tools/film.mjs) places the camera instead of the controls; snap lets the
// eye adaptation arrive at once (a cut in a film)
function step(dt, dtRaw = dt, pose = null, snap = false) {
  const k = (rate) => (snap ? 1 : Math.min(1, dt * rate));
  G.time.value += dt;
  if (app.mode === 'title') titleCam(dt);
  ride.update(dt);
  const o = openness(ride.pos.x, ride.pos.y); openK += (o - openK) * k(2);
  const ei = 0.10 + 0.55 * Math.pow(openK, 2.0);
  for (const m of Object.values(gondola.mats)) m.envMapIntensity = ei;
  if (pose) pose(dt); else if (app.mode !== 'title') controls.update(dt);
  const tu = performance.now(); tiles.update(camera); const tu2 = performance.now();
  if (tu2 - tu > 8) perfLog(['tiles.update', Math.round(tu2 - tu), Math.round(tu)]);
  const inside = interiors.find((z) => camera.position.z < z.zmax && inPoly(z.poly, camera.position.x, camera.position.y));
  // eye adaptation outdoors: narrow shaded calli (little open ground around) get up to a third more exposure
  if (app.mode !== 'fly') { const oc = openness(camera.position.x, camera.position.y); camOpen += (oc - camOpen) * k(1.2); } else camOpen += (1 - camOpen) * k(1);
  const lift = (G.night.value > 0.5 ? 0.15 : 0.35) * (1 - camOpen);
  const expT = inside ? inside.exposure * (G.night.value > 0.5 ? 1.3 : 1.0) : EXP.out * (1 + lift);
  expo += (expT - expo) * k(1.5);
  renderer.toneMappingExposure = expo * app.bright;
  if (app.mode === 'boat') ui.setLabel(ride.nameAt(ride.s));
  else ui.setLabel(inside ? inside[ui.lang] : '');
  audState(dt, inside);
  minimap.show(app.mode !== 'title');
  if (app.mode !== 'title') { camera.getWorldDirection(camDir); minimap.update(dt, camera.position.x, camera.position.y, Math.atan2(camDir.y, camDir.x)); }
  dynRes(dtRaw);
}
function frame() {
  const dtRaw = clock.getDelta(), dt = Math.min(0.1, dtRaw);
  step(dt, dtRaw);
  const tr = performance.now(); (window.VEN ? VEN.pipeline : pipeline).render(); const tr2 = performance.now();
  if (tr2 - tr > 12) perfLog(['render', Math.round(tr2 - tr), Math.round(tr)]);
  if (LD.phase !== 'done') loadStep();
  if (dtRaw > 0.05) perfLog(['FRAME', Math.round(dtRaw * 1000), Math.round(tr2)]);
  frames++; fpsT += dt; if (fpsT > 1) { fps = frames / fpsT; frames = 0; fpsT = 0; }
}
renderer.setAnimationLoop(frame);
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setPixelRatio(pixelRatio() * dyn.k); renderer.setSize(innerWidth, innerHeight); });

// ---------------------------------------------------------------- debug / automation hooks
const VEN = window.VEN = {
  audio, dyn, minimap, low: LOW, pipes: PIPE, load: LD, aud, step, createAudio, scores: _scores,
  // a film (tools/film.mjs) drives the frames itself
  stopLoop() { renderer.setAnimationLoop(null); },
  ready: false, camera, scene, tiles, renderer, G, pipeline, tex: arrays, ride, controls, gondola, app, ui,
  mode(m) { if (app.mode === 'title') ui.start(m); else app.setMode(m); },
  route(name, s = 0, speed = 1) { if (app.mode === 'title') ui.start('boat'); app.setRoute(name); ride.setRoute(name, s); ride.speed = speed; },
  walkAt(x, y, yaw = 0) { if (app.mode === 'title') ui.start('walk'); app.setMode('walk'); camera.position.set(x, y, 3); controls.yaw = yaw; controls.pitch = 0; controls.walkZ = null; },
  place(id) { if (app.mode === 'title') ui.start('walk'); app.goPlace(PLACES.find((p) => p.id === id)); },
  night(on = true) { app.night = on; return setNight(on).then(() => ui.refresh()); },
  look(px, py, pz, tx, ty, tz) { if (app.mode === 'title') { ui.start('fly'); } app.setMode('fly'); camera.position.set(px, py, pz); camera.lookAt(tx, ty, tz); controls.syncFromCamera(); },
  info() { return { fps: Math.round(fps), ...tiles.stats(), cam: camera.position.toArray().map((v) => +v.toFixed(1)) }; },
  // headless Chrome does not composite WebGPU canvases: render once into a target and read it back
  async capture(type = 'image/jpeg') { return (await VEN.frameCanvas()).toDataURL(type, 0.9).split(',')[1]; },
  // gallery covers: a headless WebGPU canvas screenshots blank, so lay the rendered frame over it (under the UI)
  async freeze() {
    document.getElementById('veil')?.remove();
    const c = await VEN.frameCanvas(), d = renderer.domElement;
    c.style.cssText = `position:fixed;left:0;top:0;width:${d.clientWidth}px;height:${d.clientHeight}px;z-index:1;pointer-events:none`;
    document.body.appendChild(c); return true;
  },
  async frameCanvas() {
    const w = renderer.domElement.width, h = renderer.domElement.height;
    if (!VEN._rt || VEN._rt.width !== w || VEN._rt.height !== h) VEN._rt = new THREE.RenderTarget(w, h, { type: THREE.UnsignedByteType, colorSpace: THREE.SRGBColorSpace });
    // drawing into a target of its own needs pipelines of its own: draw again once they are made (async, see above)
    for (let k = 0; k < 100; k++) {
      renderer.setRenderTarget(VEN._rt); pipeline.render(); renderer.setRenderTarget(null);
      if (PIPE.pending === 0) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    const px = await renderer.readRenderTargetPixelsAsync(VEN._rt, 0, 0, w, h);
    const c2 = document.createElement('canvas'); c2.width = w; c2.height = h; const g = c2.getContext('2d');
    const img = g.createImageData(w, h);
    // WebGPU pads each read-back row to 256 bytes: copy row by row when the width leaves padding
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
VEN.ready = true;
VEN.THREE = THREE;
