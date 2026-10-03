import * as THREE from 'three';
import { CSM } from 'three/addons/csm/CSM.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';
import { getMaterial, loadDetail, shared } from './materials.js';
import { FlyControls } from './fly.js';
import { World, makeInteriors } from './world.js';
import { setRooms, ROOMS, B, S } from './frames.js';
import { buildTour, poseAt } from './tour.js';
import { AUDIO } from './audio.js';

THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
if (params.get('dbg')) shared.debug.value = { irr: 1, nrm: 2, alb: 3 }[params.get('dbg')] || 0;
let LANG = (location.hash === '#en' || params.get('lang') === 'en') ? 'en' : (navigator.language || '').startsWith('ja') || location.hash === '#ja' ? 'ja' : (location.hash ? 'ja' : 'ja');

// ---------------------------------------------------------------- renderer / scene
const canvas = $('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
const QUALITY = params.get('q') === 'low' ? 0.75 : 1;
renderer.setPixelRatio(Math.min(devicePixelRatio, 2) * QUALITY);
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.25, 80000);
camera.up.set(0, 0, 1);
camera.position.set(260, -360, 230); camera.lookAt(-280, -8.7, 60);

const SUN = { az: 120, el: 30, strength: 4.0 };
const az = THREE.MathUtils.degToRad(SUN.az), el = THREE.MathUtils.degToRad(SUN.el);
const sunDir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.cos(az) * Math.cos(el), Math.sin(el));
const csm = new CSM({ maxFar: 2500, cascades: 4, mode: 'practical', parent: scene, shadowMapSize: QUALITY < 1 ? 1024 : 2048,
  lightDirection: sunDir.clone().negate(), camera, lightIntensity: SUN.strength, lightMargin: 400 });
for (const l of csm.lights) { l.shadow.bias = -0.0002; l.shadow.normalBias = 0.05; l.color.setRGB(1.0, 0.96, 0.9); }
const SKYCOL = new THREE.Color().setRGB(0.55, 0.68, 0.85, THREE.LinearSRGBColorSpace);
scene.background = SKYCOL;
const fogExt = new THREE.FogExp2(new THREE.Color().setRGB(0.62, 0.70, 0.80, THREE.LinearSRGBColorSpace), 0.00016);
scene.fog = fogExt;
let skyTex = null;
new HDRLoader().load('tex/sky.hdr', (t) => {
  t.mapping = THREE.EquirectangularReflectionMapping; skyTex = t;
  scene.background = t; scene.environment = t;
  scene.backgroundRotation.set(Math.PI / 2, 0, 0); scene.environmentRotation.set(Math.PI / 2, 0, 0);
});
const mat = (n) => getMaterial(n, csm);
const controls = new FlyControls(camera, canvas); controls.enabled = false;

// ---------------------------------------------------------------- data
const loadText = $('load');
const progress = {};
const world = new World(scene, mat, (name, p) => {
  progress[name] = p;
  if (name === 'city' || name === 'core') {
    const v = ((progress.city || 0) * 19 + (progress.core || 0) * 38) / 57;
    loadText.textContent = v < 1 ? `${LANG === 'ja' ? '読み込み中' : 'Loading'} ${(v * 100) | 0}%` : '';
  }
});
let TOUR = null, ART = {}, POINTS = [];
const ready = (async () => {
  const [rooms, art] = await Promise.all([fetch('data/rooms.json').then((r) => r.json()), fetch('art/index.json').then((r) => r.json())]);
  setRooms(rooms); ART = art; world.interiors = makeInteriors();
  TOUR = buildTour(); AUDIO.init(TOUR);
  POINTS = artPoints();
  buildPlaces();
  await loadDetail('tex');
  await Promise.all([world.load('city'), world.load('core')]);
  loadText.textContent = '';
  $('go').disabled = false; $('free').disabled = false;
  world.update(camera.position);
  window.VAT.ready = true;
})();

// ---------------------------------------------------------------- artwork cards
const EXTRA = {
  pieta: [{ ja: 'ピエタ', en: 'Pietà' }, 'Michelangelo', '1498–1499'],
  baldacchino: [{ ja: 'サン・ピエトロの天蓋', en: 'St Peter’s Baldachin' }, 'Gian Lorenzo Bernini', '1623–1634'],
  cathedra: [{ ja: '聖ペテロの司教座', en: 'Cathedra Petri' }, 'Gian Lorenzo Bernini', '1657–1666'],
  obelisk: [{ ja: 'ヴァチカンのオベリスク', en: 'Vatican Obelisk' }, 'Egypt; raised here by Domenico Fontana', '1586'],
  pigna: [{ ja: 'ピーニャ（松かさ）', en: 'The Pigna' }, 'Roman bronze', '1st–2nd century'],
  laocoon: [{ ja: 'ラオコーン群像', en: 'Laocoön and His Sons' }, 'Hagesandros, Athenodoros, Polydoros', 'c. 40–20 BC'],
  apollo: [{ ja: 'ベルヴェデーレのアポロン', en: 'Apollo Belvedere' }, 'Roman copy after Leochares', 'c. 120–140'],
  torso: [{ ja: 'ベルヴェデーレのトルソ', en: 'Belvedere Torso' }, 'Apollonios, son of Nestor', '1st century BC'],
  rotonda_basin: [{ ja: '斑岩の水盤', en: 'Porphyry basin' }, 'Roman', '1st century'],
  gallery_maps: [{ ja: '地図のギャラリー', en: 'Gallery of Maps' }, 'Ignazio Danti', '1580–1585'],
  momo: [{ ja: '二重螺旋階段', en: 'Momo Staircase' }, 'Giuseppe Momo', '1932'],
  creation_adam: [{ ja: 'アダムの創造', en: 'The Creation of Adam' }, 'Michelangelo', 'c. 1511'],
};
function artPoints() {
  const P = [];
  const add = (key, pos, zone, range = 30) => P.push({ key, pos: new THREE.Vector3(...pos), zone, range });
  for (const [name, r] of Object.entries(ROOMS)) for (const i of r.info || []) if (!/standin/.test(i.key)) add(i.key, i.pos, 'room_' + name, 16);
  add('pieta', B(107, 28.0, 3.4), 'basilica', 18); add('baldacchino', B(0, 0, 12), 'basilica', 45); add('cathedra', B(-67, 0, 15), 'basilica', 40);
  add('obelisk', [0, 0, 18], null, 70); add('pigna', [-222, 450.2, 9], null, 40);
  add('last_judgment', S(-20.1, 0, 10), 'sistine', 30); add('creation_adam', S(-2.4, 0, 20.5), 'sistine', 22); add('sistine_ceiling', S(6, 0, 20.7), 'sistine', 16);
  const N = ['baptism', 'temptations', 'calling', 'sermon', 'keys', 'last_supper'], So = ['moses_journey', 'moses_trials', 'red_sea', 'sinai', 'korah', 'moses_testament'];
  for (let b = 0; b < 6; b++) { const x = -20.115 + 6.705 * (b + 0.5); add(N[b], S(x, 6.7, 7.6), 'sistine', 11); add(So[b], S(x, -6.7, 7.6), 'sistine', 11); }
  return P;
}
const card = $('art'); let cardKey = null;
function updateCard() {
  if (!POINTS.length) return;
  const f = new THREE.Vector3(); camera.getWorldDirection(f);
  const zone = world.current ? world.current.zone : null;
  let best = null, bs = 0;
  for (const p of POINTS) {
    if (p.zone !== zone) continue;
    const d = p.pos.clone().sub(camera.position); const L = d.length(); if (L > p.range || L < 0.5) continue;
    const c = d.dot(f) / L; if (c < 0.86) continue;
    const sc = (c - 0.86) * 8 + (1 - L / p.range);
    if (sc > bs) { bs = sc; best = p; }
  }
  const key = best ? best.key : null;
  if (key === cardKey) return;
  cardKey = key;
  if (!key) { card.style.opacity = 0; return; }
  const a = ART[key], e = EXTRA[key];
  const title = e ? e[0][LANG] : a && a.title ? a.title[LANG] : null;
  if (!title) { card.style.opacity = 0; return; }
  card.querySelector('.t').textContent = title;
  card.querySelector('.a').textContent = e ? `${e[1]} · ${e[2]}` : `${a.artist || ''}${a.date ? ' · ' + a.date : ''}`;
  card.style.opacity = 1;
}

// ---------------------------------------------------------------- language
function applyLang() {
  document.documentElement.lang = LANG;
  for (const el of document.querySelectorAll('[data-ja]')) el.textContent = el.dataset[LANG];
  $('lang').textContent = $('b-lang').textContent = LANG === 'ja' ? 'EN' : '日本語';
  capKey = null; cardKey = null; buildPlaces();
}
const toggleLang = () => { LANG = LANG === 'ja' ? 'en' : 'ja'; history.replaceState(null, '', '#' + LANG); applyLang(); };
$('lang').onclick = toggleLang; $('b-lang').onclick = toggleLang;

// ---------------------------------------------------------------- modes
let mode = 'title', tourT = 0, playing = false, fade = 1, fadeHold = 0;
const cap = $('cap'); let capKey = null;
function setMode(m) {
  mode = m;
  $('title').style.opacity = m === 'title' ? 1 : 0; $('title').style.pointerEvents = m === 'title' ? 'auto' : 'none';
  $('bar').style.opacity = m === 'title' ? 0 : 1; $('bar').style.pointerEvents = m === 'title' ? 'none' : 'auto';
  $('help').style.display = m === 'free' ? 'block' : 'none';
  controls.enabled = m === 'free'; if (m === 'free') controls.syncFromCamera();
  $('b-tour').classList.toggle('on', m === 'tour'); $('b-free').classList.toggle('on', m === 'free');
  if (m !== 'tour') { cap.style.opacity = 0; capKey = null; }
  $('prog').style.display = m === 'tour' ? 'block' : 'none';
}
function startTour(at = 0) { tourT = at; playing = true; setMode('tour'); AUDIO.start(); AUDIO.seek(tourT); }
$('go').onclick = () => { ready.then(() => startTour(0)); };
$('free').onclick = () => { ready.then(() => { setMode('free'); fade = 0; AUDIO.start(); }); };
$('b-tour').onclick = () => { if (mode === 'tour') return; const s = segAt(tourT); startTour(s ? s.t0 : 0); };
$('b-free').onclick = () => { playing = false; setMode('free'); AUDIO.seek(-1); };
$('b-sound').onclick = () => { AUDIO.toggle(); $('b-sound').classList.toggle('on', !AUDIO.muted); };
$('b-credits').onclick = () => { $('credits').style.display = 'block'; loadCredits(); };
$('credits-x').onclick = () => { $('credits').style.display = 'none'; };
$('b-places').onclick = () => { const p = $('places'); p.style.display = p.style.display === 'block' ? 'none' : 'block'; };
function buildPlaces() {
  if (!TOUR) return;
  const el = $('places'); el.innerHTML = '';
  TOUR.segments.forEach((s, i) => {
    if (s.final) return;
    const b = document.createElement('button');
    b.innerHTML = `<span class="n">${String(i + 1).padStart(2, '0')}</span>${s.name[LANG]}`;
    b.onclick = () => { el.style.display = 'none'; world.load(s.zone || 'core'); startTour(s.t0); fade = 1; };
    el.appendChild(b);
  });
}
addEventListener('keydown', (e) => {
  if (e.code === 'KeyF' && mode !== 'title') (mode === 'free' ? $('b-tour') : $('b-free')).click();
  if (e.code === 'KeyM') $('b-sound').click();
  if (e.code === 'Escape') { $('credits').style.display = 'none'; $('places').style.display = 'none'; }
  if (mode === 'tour' && e.code === 'ArrowRight') { const s = segAt(tourT); const n = TOUR.segments[TOUR.segments.indexOf(s) + 1]; if (n) { tourT = n.t0; AUDIO.seek(tourT); fade = 1; } }
  if (mode === 'tour' && e.code === 'ArrowLeft') { const s = segAt(tourT); tourT = Math.max(0, (tourT - s.t0 < 2 && TOUR.segments.indexOf(s) > 0) ? TOUR.segments[TOUR.segments.indexOf(s) - 1].t0 : s.t0); AUDIO.seek(tourT); fade = 1; }
  if (mode === 'tour' && e.code === 'Space') { playing = !playing; AUDIO.pause(!playing); e.preventDefault(); }
});
canvas.addEventListener('pointerdown', () => { if (mode === 'tour') { /* a drag during the tour hands over to free flight */ } });

const segAt = (t) => { if (!TOUR) return null; let s = TOUR.segments[0]; for (const x of TOUR.segments) if (x.t0 <= t) s = x; return s; };

function updateTour(dt) {
  const s = segAt(tourT); if (!s) return;
  const i = TOUR.segments.indexOf(s), next = TOUR.segments[i + 1];
  // preload this and the next two segments' zones
  for (const k of [i, i + 1, i + 2]) { const z = TOUR.segments[k] && TOUR.segments[k].zone; if (z) world.load(z); }
  const need = s.zone && !world.ready(s.zone);
  AUDIO.hold(!!need, tourT);
  if (playing && !need) tourT = AUDIO.clock(performance.now(), tourT, dt);
  if (tourT >= TOUR.total) { playing = false; tourT = 0; setMode('title'); AUDIO.seek(-1); fade = 1; titleT = 0; return; }
  const lt = tourT - s.t0;
  const pose = poseAt(s, Math.min(lt, s.dur));
  camera.position.set(...pose.p); camera.lookAt(...pose.l);
  // fades at cuts
  let f = 0;
  if (s.cut) f = Math.max(f, 1 - lt / 1.1);
  if (next && next.cut) f = Math.max(f, 1 - (s.dur - lt) / 1.1);
  if (s.final) f = Math.max(f, 1 - (s.dur - lt) / 3.0);
  if (need) f = 1;
  fade = Math.max(0, Math.min(1, f));
  // caption
  let c = null; for (const k of s.caps || []) if (k[0] <= lt) c = k;
  const show = c && lt < s.dur - 1.6 ? c : null;
  const key = show ? s.id + ':' + show[0] + ':' + LANG : null;
  if (key !== capKey) {
    capKey = key;
    if (!show) cap.style.opacity = 0;
    else {
      const txt = LANG === 'ja' ? show[1] : show[2];
      cap.style.opacity = 0;
      setTimeout(() => { cap.querySelector('.h').textContent = txt.h; cap.querySelector('.p').textContent = txt.p; cap.style.opacity = 1; }, 450);
    }
  }
  $('where').textContent = s.name[LANG];
  $('prog').style.width = (tourT / TOUR.total * 100).toFixed(2) + '%';
  AUDIO.tick(tourT, s.id, lt);
}

// title backdrop: a slow orbit high over the square
let titleT = 0;
function updateTitle(dt) {
  titleT += dt;
  const a = -0.9 + titleT * 0.012, r = 420;
  camera.position.set(-160 + r * Math.cos(a), -8.7 + r * Math.sin(a), 190);
  camera.lookAt(-200, -8.7, 40);
  fade = Math.max(0, fade - dt * 0.6 * (world.ready('core') ? 1 : 0));
}

// ---------------------------------------------------------------- frame loop
let exposure = 1, last = performance.now(), sunOn = 1;
addEventListener('resize', () => { renderer.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); csm.updateFrustums(); });
function frame(t) {
  const dt = Math.min(0.1, (t - last) / 1000); last = t; shared.time.value = t / 1000;
  if (mode === 'title') updateTitle(dt);
  else if (mode === 'tour') updateTour(dt);
  else { controls.update(dt); fade = Math.max(0, fade - dt * 1.5); }
  camera.updateMatrixWorld();
  const I = world.update(camera.position);
  const tExp = I ? (typeof I.exposure === 'function' ? I.exposure(camera.position) : I.exposure) : 1;
  exposure += (tExp - exposure) * (1 - Math.exp(-dt * 3));
  renderer.toneMappingExposure = exposure;
  const wantSun = !I || I.sun ? 1 : 0;
  sunOn += (wantSun - sunOn) * Math.min(1, dt * 8);
  for (const l of csm.lights) l.intensity = SUN.strength * sunOn;
  scene.fog = I ? null : fogExt;
  if (I && I.bg != null) { scene.background = new THREE.Color(I.bg); } else scene.background = skyTex || SKYCOL;
  $('fade').style.opacity = fade.toFixed(3);
  csm.update();
  if (mode !== 'title') updateCard(); else card.style.opacity = 0;
  renderer.render(scene, camera);
  AUDIO.listener(camera, I ? I.zone : null);
  requestAnimationFrame(frame);
}
applyLang(); setMode('title');
$('go').disabled = true; $('free').disabled = true;
requestAnimationFrame(frame);

// ---------------------------------------------------------------- credits (loaded on demand)
let creditsLoaded = false;
function loadCredits() {
  if (creditsLoaded) return; creditsLoaded = true;
  fetch('credits.html').then((r) => r.text()).then((h) => { $('credits-body').innerHTML = h; });
}

// ---------------------------------------------------------------- debug / automation hooks
window.VAT = { THREE, scene, camera, renderer, world, ready: false, audio: AUDIO,
  look(px, py, pz, tx, ty, tz) { setMode('free'); fade = 0; camera.position.set(px, py, pz); camera.lookAt(tx, ty, tz); controls.syncFromCamera(); },
  async at(t) { await ready; const s = segAt(t); if (s.zone) await world.load(s.zone); startTour(t); playing = false; updateTour(0); fade = 0; $('fade').style.opacity = 0; return s.id; },
  async play(t) { await ready; startTour(t); },
  get tour() { return TOUR; }, get t() { return tourT; },
  fps(ms = 3000) { return new Promise((res) => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < ms) requestAnimationFrame(f); else res(+(n * 1000 / (performance.now() - t0)).toFixed(1)); }; requestAnimationFrame(f); }); },
  stats() { const i = renderer.info; return { calls: i.render.calls, tris: i.render.triangles, geoms: i.memory.geometries, tex: i.memory.textures }; },
  info() { return { mode, t: tourT, zone: world.current && world.current.zone, pos: camera.position.toArray().map((v) => +v.toFixed(2)) }; },
};
if (params.get('zones')) ready.then(() => Promise.all(params.get('zones').split(',').map((z) => world.load(z))));
