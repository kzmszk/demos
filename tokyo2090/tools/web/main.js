import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { loadTerrain, terrainSampler, loadRoof, loadFoot } from './data.js';
import { makeWalker } from './walk.js';
import { makeTerrainMaterial, buildTerrain } from './terrain.js';
import { makeCityMaterial, City } from './city.js';
import { makeFacadeAtlas, makeDetailTexture } from './facade.js';
import { Flight } from './flight.js';
import { makeSun } from './light.js';
import { makeBody } from './body.js';
import { makeSaki } from './saki.js';
import { loadProps, LOD, CAR_STRIDE, TREE_STRIDE } from './props.js';
import { makeStory } from './story.js';
import { makeClouds } from './clouds.js';
import { createAudio } from './music.js';
import { makeThermals } from './thermals.js';
import { makeAutopilot } from './hand.js';
import { makeUndergrowth } from './undergrowth.js';
import { makeLabels } from './labels.js';
import { makeRails } from './rails.js';
import { makeHeroes } from './hero.js';

const $ = (id) => document.getElementById(id);
const query = new URLSearchParams(location.search);
// phones: touch controls, a lighter profile (smaller shadow map, nearer detail, fewer trees)
const touch = matchMedia('(pointer: coarse)').matches || query.has('touch');
const low = query.get('q') === 'low' || (query.get('q') !== 'high' && touch);
document.body.classList.toggle('touch', touch);
if (low) { LOD.fullTrees = 500; LOD.hideTrees = 1700; LOD.hideCars = 900; LOD.nearProps = 90; }
const renderer = new THREE.WebGLRenderer({ antialias: !low, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, low ? 1.25 : 1.5)); renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.prepend(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.25, 60000); scene.add(camera);
camera.rotation.order = 'YXZ';

// light: a low sun from the west-south-west, warm; haze toward the horizon
const sunDir = new THREE.Vector3(-0.76, 0.24, 0.40).normalize();
const sunRig = makeSun(scene, sunDir, low ? 2048 : 4096);
// the loaded models (Saki) use three's own materials: give them the same sun, sky and haze as the custom shaders
const hemi = new THREE.HemisphereLight(0xffffff, 0xffffff, 1.0); scene.add(hemi);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.BasicShadowMap; renderer.shadowMap.autoUpdate = true;
const shared = {
  sunDir: { value: sunDir }, sunCol: { value: new THREE.Color(1.48, 1.12, 0.80) }, skyCol: { value: new THREE.Color(0.46, 0.55, 0.70) },
  groundCol: { value: new THREE.Color(0.26, 0.28, 0.20) }, fogCol: { value: new THREE.Color(0.80, 0.72, 0.62) }, fogDen: { value: 0.00034 },
  camPos: { value: camera.position }, ...sunRig.uniforms,
};
sunRig.sun.color.copy(shared.sunCol.value); sunRig.sun.intensity = 1.0;
hemi.color.copy(shared.skyCol.value); hemi.groundColor.copy(shared.groundCol.value); hemi.intensity = 1.0;
scene.fog = new THREE.FogExp2(shared.fogCol.value.clone(), shared.fogDen.value);
// the sky box is drawn first with no depth test so the far plane can never clip it (it did at the top of the view)
const sky = new Sky(); sky.scale.setScalar(20000); sky.material.depthTest = false; sky.material.depthWrite = false; sky.renderOrder = -100; sky.frustumCulled = false; scene.add(sky);
{ const u = sky.material.uniforms; u.sunPosition.value.copy(sunDir); u.turbidity.value = 6; u.rayleigh.value = 1.8; u.mieCoefficient.value = 0.008; u.mieDirectionalG.value = 0.85; }

const flight = { current: null };
let ring2, labels, heroes, undergrowth, city, ground, roof, walker, terrainGroup, body, saki, ring, props, story, clouds, thermals, autopilot, audio = null, muted = false, last = performance.now(), started = false, clock = 0;
const aim = { hit: null, ok: false };
const keys = new Set();
const T2090 = window.T2090 = { camera, scene, renderer, keys, ready: false, get flight() { return flight.current; }, get city() { return city; },
  info() { const f = flight.current; return { state: f.state, street: f.street, feet: +f.feet.toFixed(1), wall: !!wallAhead, walked: f.walked, speed: +f.speed.toFixed(1), gamma: +f.gamma.toFixed(2), roll: +f.roll.toFixed(2), p: f.p.toArray().map((v) => +v.toFixed(0)), alt: +(f.p.y - ground(f.p.x, -f.p.z)).toFixed(0), up: +f.updraft.toFixed(2), aim: aim.ok, hand: f.hand, close: f.close, fps: +T2090.fps.toFixed(0), saki: saki?.state.pos.toArray().map((v) => +v.toFixed(0)), tris: renderer.info.render.triangles, calls: renderer.info.render.calls, tiles: city?.ready }; },
  key(code, down = true) { down ? keys.add(code) : keys.delete(code); },
  hand(on) { const f = flight.current; if (on) { f.hand = true; look.yaw = 0; } else f.hand = false; },
  close(on) { const f = flight.current; f.close = !!on; },
  tryLand,
  // dev / cover hooks: fly(x, y, z, heading) places the glider in the air in data axes; landAt(x, y) lands on that roof
  fly(x, y, z, heading = 0, speed = 18) { const f = flight.current; f.p.set(x, z, -y); f.heading = heading; f.gamma = -0.12; f.roll = 0; f.rollRate = 0; f.gRate = 0; f.open = 1; f.state = 'glide'; f.stateTime = 5; f.launch = null; f.launchTop = -1e9;
    f.v.set(Math.sin(heading) * speed, -speed * 0.12, -Math.cos(heading) * speed); f.forward.set(Math.sin(heading), 0, -Math.cos(heading)); f.right.set(Math.cos(heading), 0, Math.sin(heading)); saki?.place(f.p.clone().addScaledVector(f.forward, 18)); },
  landAt(x, y) { const f = flight.current; const t = roof.top(x, y); if (t === -Infinity) return false; f.land(new THREE.Vector3(x, t, -y)); return true; },
  look(yaw, pitch) { look.yaw = yaw; look.pitch = pitch; },
  primary: () => primary(), jumpTo: (...a) => jumpTo(...a), togglePlaces: (on) => togglePlaces(on),
  touch, get stick() { return stick; }, get tbtn() { return tbtn; },
  fps: 0 };

async function init() {
  const [rings, roofData, foot, rubble] = await Promise.all([loadTerrain('data/terrain.bin'), loadRoof('data/roof.bin'), loadFoot('data/foot.bin'), fetch('data/rubble.json').then((r) => r.json())]);
  ground = terrainSampler(rings); roof = roofData; walker = makeWalker({ ground, roof, foot, rubble }); T2090.walker = walker;
  const cover = await new THREE.TextureLoader().loadAsync('data/cover.png');
  cover.magFilter = THREE.LinearFilter; cover.minFilter = THREE.LinearMipmapLinearFilter; cover.generateMipmaps = true; cover.flipY = true; cover.colorSpace = THREE.NoColorSpace;
  // cover.png row 0 is north (y = Y1) and the shader samples v = (y - y0)/h from the south: flipY puts row 0 at v = 1
  // (it was false until 2026-10-24, which drew every road and park mirrored north-south)
  const tm = makeTerrainMaterial({ ...shared, cover: { value: cover }, coverBox: { value: new THREE.Vector4(-2400, -2000, 7000, 6400) }, ringScale: { value: 0 } });
  T2090.terrainMat = tm; terrainGroup = buildTerrain(rings, tm); scene.add(terrainGroup);
  for (const m of terrainGroup.children) for (const k of ['shadowMap', 'shadowMatrix', 'shadowSize']) m.material.uniforms[k] = sunRig.uniforms[k];
  const index = await (await fetch('data/city/index.json')).json();
  const facade = makeFacadeAtlas(); T2090.facade = facade;
  city = new City(scene, makeCityMaterial({ ...shared, atlas: { value: facade.albedo }, atlasMask: { value: facade.mask }, detail: { value: makeDetailTexture() } }), 'data/city', index);
  if (low) { city.fullRadius = 800; city.liteRadius = 6000; city.maxLoading = 1; city.maxSwaps = 1; }
  heroes = await makeHeroes(scene, { low, renderer, camera }); T2090.heroes = heroes; walker.setField(heroes.field);
  if (heroes.preview) city.material.uniforms.cutBox.value.set(...heroes.preview.box);
  const f = new Flight(ground, roof); flight.current = f; f.setWalker(walker);
  // start on the roof of Shibuya Scramble Square, facing the crossing to the north-west
  const start = query.get('at') ? query.get('at').split(',').map(Number) : [116, -112];
  f.placeOnRoof(start[0], start[1], query.get('hd') ? Number(query.get('hd')) : -0.75);
  camera.position.copy(f.p); camera.rotation.set(-0.35, -f.heading, 0);
  body = makeBody(camera, shared); saki = makeSaki(scene, shared); saki.walker = walker; saki.place(f.p.clone().addScaledVector(f.right, 2));
  ring = new THREE.Mesh(new THREE.RingGeometry(2.6, 3.4, 40), new THREE.MeshBasicMaterial({ color: 0xffd9b0, transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthTest: false }));
  ring.rotation.x = -Math.PI / 2; ring.visible = false; ring.renderOrder = 5; scene.add(ring);
  // the street ring (teal): where Shift+E / G would take you down
  ring2 = new THREE.Mesh(new THREE.RingGeometry(4.2, 5.2, 48), new THREE.MeshBasicMaterial({ color: 0x8fd8c8, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthTest: false }));
  ring2.rotation.x = -Math.PI / 2; ring2.visible = false; ring2.renderOrder = 5; scene.add(ring2);
  T2090.ground = ground; T2090.roof = roof; T2090.saki = saki; T2090.aim = aim;
  labels = makeLabels({ places: await (await fetch('data/places.json')).json(), ground, roof }); T2090.labels = labels;
  const rails = makeRails(scene, shared, { data: await (await fetch('data/rails.json')).json(), ground, walker }); T2090.rails = rails;
  labels.addLines(rails.labels, ground);
  for (const d of heroes.districts) labels.addLocal(d.labels, d.origin[0], d.origin[1]);
  undergrowth = makeUndergrowth(scene, shared, { ground, roof, low, exclude: heroes.boxes }); T2090.undergrowth = undergrowth;
  clouds = makeClouds(scene, shared); thermals = makeThermals(scene, flight); autopilot = makeAutopilot(roof, ground);
  story = makeStory($('say')); T2090.story = story; saki.speaking = () => story.speaking; setTimeout(() => story.say('start'), 1500); setTimeout(() => story.say('edge'), 9000);
  loadProps(scene, { ground, roof, shared, THREE, exclude: heroes.boxes }).then((p) => { props = p; T2090.props = p; if (p.carData) walker.setCars(p.carData, p.carStride || CAR_STRIDE, p.carType && p.carTypes ? (i) => p.carTypes[p.carType(i)] : null); if (p.treeData) walker.setTrees(p.treeData, p.treeStride || TREE_STRIDE); }).catch((e) => console.warn('props', e));
  for (let k = 0; k < 40; k++) { city.update(camera.position); await new Promise((r) => setTimeout(r, 60)); if (city.ready > 24) break; }
  $('loading').classList.add('hidden'); started = true; T2090.ready = true;
  if (!query.has('nointro') && !location.hash.includes('nointro')) { $('intro').classList.add('on'); document.body.classList.add('intro'); }
  requestAnimationFrame(loop);
}

let look = { yaw: -0.8, pitch: -0.5 }, pointer = false, camPitch = 0, adapted = false, hudT = 0, wasFlying = false;
function startAudio() { if (!audio && !query.has('silent')) { try { audio = createAudio(); audio.start(); audio.volume(muted ? 0 : 0.7); } catch (e) { console.warn('audio', e); } } }
function dismissIntro() { startAudio(); document.body.classList.remove('intro'); if ($('intro').classList.contains('on')) { $('intro').classList.remove('on'); return true; } return false; }
$('intro').addEventListener('click', dismissIntro); $('intro').addEventListener('touchend', (e) => { e.preventDefault(); dismissIntro(); }, { passive: false });
addEventListener('keydown', (e) => { if (e.code === 'KeyM') { muted = !muted; audio?.volume(muted ? 0 : 0.7); $('mute').textContent = muted ? '♪ off' : '♪ on'; } if (e.code === 'Space' && dismissIntro()) { e.preventDefault(); return; } keys.add(e.code); if (e.code === 'Space') { e.preventDefault(); if (!e.repeat) primary(); } if (e.code === 'KeyE') tryLand(e.shiftKey); if (e.code === 'KeyG') tryLand(true); if (e.code === 'KeyH') toggleHand(); if (e.code === 'KeyJ') toggleClose(); if (e.code === 'KeyL') labels.enabled = !labels.enabled; if (e.code === 'KeyP') togglePlaces(); if (e.code === 'Escape') togglePlaces(false); });
// Space / the big button: on foot, climb the wall you face, else jump off the roof's edge (or hop on the street);
// climbing, kick off the wall into the air
function primary() {
  const f = flight.current; if (!f) return;
  if (f.state === 'climb') { f.kickOff(); look.yaw = 0; look.pitch = -0.1; return; }
  if (f.state !== 'rest') return;
  const h = f.heading - look.yaw;
  if (f.climb(h)) { look.yaw = 0; look.pitch = Math.max(look.pitch, 0.35); return; }
  if (!f.street) { f.jump(h); look.yaw = 0; return; }
  f.hop();
}
// E: the roof you look at (or the nearest reachable one ahead); Shift+E or G: the street (the teal ring)
function tryLand(toStreet = false) {
  const f = flight.current; if (!f || f.state !== 'glide') return;
  if (toStreet) {
    const target = pickStreet(f);
    if (target && f.land(target)) { f.hand = false; f.close = false; story.say('landStreet', { every: 15000 }); }
    else story.say('noStreet', { every: 6000 });
    return;
  }
  const target = (aim.ok && aim.hit) ? aim.hit : pickRoof(f);
  if (target && f.land(target)) { f.hand = false; f.close = false; story.say('land', { every: 20000 }); }
  else story.say('noRoof', { every: 6000 });
}
// places: jump to the hand-built districts (their spawns, on foot) or back to the start
const START = { x: 116, y: -112, heading: -0.75 };
function buildPlaces() {
  const box = $('placesList'); box.innerHTML = '';
  const item = (label, sub, fn) => { const b = document.createElement('button'); b.innerHTML = label + (sub ? `<small>${sub}</small>` : ''); b.addEventListener('click', (e) => { e.stopPropagation(); togglePlaces(false); fn(); }); b.addEventListener('pointerdown', (e) => e.stopPropagation()); box.appendChild(b); };
  for (const d of heroes.districts) {
    const g = document.createElement('div'); g.className = 'grp'; g.textContent = d.title; box.appendChild(g);
    for (const sp of d.spawns) item(sp.name, '', () => jumpTo(d.origin[0] + sp.x, d.origin[1] + sp.y, sp.heading ?? 0, d.name));
  }
  if (!heroes.districts.length) { const n = document.createElement('div'); n.className = 'none'; n.textContent = '作り込み中の場所は、まだありません。'; box.appendChild(n); }
  const g = document.createElement('div'); g.className = 'grp'; g.textContent = 'はじまりの場所'; box.appendChild(g);
  item('渋谷スクランブルスクエアの屋上', 'サキと出会う崖', () => jumpTo(START.x, START.y, START.heading, null, true));
}
function togglePlaces(on) {
  const p = $('places'); const show = on ?? p.classList.contains('hidden');
  p.classList.toggle('hidden', !show);
  if (show) { buildPlaces(); if (document.pointerLockElement) document.exitPointerLock(); }
}
let jumping = false;
async function jumpTo(x, y, heading, district = null, roofStart = false) {
  const f = flight.current; if (!f || jumping) return; jumping = true;
  const fade = $('fade'); fade.textContent = ''; fade.classList.add('on');
  await new Promise((r) => setTimeout(r, 480));
  f.hand = false; f.close = false;
  f.placeOnFoot(x, y, heading); look.yaw = 0; look.pitch = roofStart ? -0.35 : -0.04; wasFlying = false;
  saki.place(f.p.clone().addScaledVector(f.right, 1.2).addScaledVector(f.forward, 2.0));
  // wait for the district (its field and its near level) and the city around the spot
  const t0 = performance.now();
  for (;;) {
    await new Promise((r) => setTimeout(r, 150));
    const ok = (!district || heroes.ready(district)) && city.ready >= 8;
    if (performance.now() - t0 > 1200) fade.textContent = '読み込んでいます';
    if (ok && performance.now() - t0 > 700) break;
    if (performance.now() - t0 > 15000) break;
  }
  f.placeOnFoot(x, y, heading);                     // again, now that the district's field is in
  saki.place(f.p.clone().addScaledVector(f.right, 1.2).addScaledVector(f.forward, 2.0));
  fade.classList.remove('on'); jumping = false;
  story.say(roofStart ? 'edge' : 'arrive', { every: 1000 });
}
$('placesBtn').addEventListener('click', (e) => { e.stopPropagation(); startAudio(); togglePlaces(); });
$('placesBtn').addEventListener('pointerdown', (e) => e.stopPropagation());
$('places').addEventListener('pointerdown', (e) => e.stopPropagation());
// her hand: within reach while gliding; the second press lets go
function sakiNear() { const f = flight.current; return f && f.state === 'glide' && saki && saki.state.pos.distanceTo(f.p) < 9; }
function toggleHand() { const f = flight.current; if (!f) return; if (f.hand) { f.hand = false; f.close = false; } else if (sakiNear()) { f.hand = true; look.yaw = 0; } }
function toggleClose() { const f = flight.current; if (f && f.hand) { f.close = !f.close; look.yaw = 0; look.pitch = -0.1; } }
// a roof to land on when none is in the eyes' line: the nearest flat roof ahead that the glide can reach
function pickRoof(f) {
  let best = null, bestD = 1e9;
  for (let off = -0.9; off <= 0.91; off += 0.15) for (let d = 30; d <= 320; d += 10) {
    const h = f.heading + off, x = f.p.x + Math.sin(h) * d, z = f.p.z - Math.cos(h) * d;
    const top = roof.top(x, -z); if (top === -Infinity) continue;
    const g = ground(x, -z); if (top - g < 11) continue;
    if (!(top < f.p.y - d * 0.075 + 4 && top > f.p.y - d * 0.62)) continue;
    if (![[4, 0], [-4, 0], [0, 4], [0, -4]].every(([dx, dy]) => Math.abs(roof.top(x + dx, -z + dy) - top) < 4)) continue;
    const slope = (top - f.p.y) / d;                                            // a comfortable glide is about -0.2
    const score = d + Math.abs(off) * 120 + Math.abs(slope + 0.2) * 500; if (score < bestD) { bestD = score; best = new THREE.Vector3(x, top, z); }
  }
  return best;
}
// The street to come down on (Shift+E / G): open ground with room around it (a crossing, a wide road, a park), the
// nearest one ahead of where you look, that the glide reaches staying above everything on the way and over it, so the last part is a
// straight descent on the open cape. Returns the point with .ground and .safe (the height to arrive over it at).
const _vd = new THREE.Vector3();
function pickStreet(f) {
  camera.getWorldDirection(_vd);
  const yaw = Math.atan2(_vd.x, -_vd.z);
  let best = null, bestS = 1e9;
  for (let off = -0.6; off <= 0.61; off += 0.1) for (let d = 25; d <= 420; d += 12) {
    const h = yaw + off, x = f.p.x + Math.sin(h) * d, y = -(f.p.z - Math.cos(h) * d);
    if (!walker.open(x, y, 6)) continue;
    const g = ground(x, y);
    // what stands around it: arrive above that, and be able to get there on the glide (about 1 in 8)
    let around = g; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; around = Math.max(around, walker.surface(x + Math.cos(a) * 14, y + Math.sin(a) * 14)); }
    const safe = Math.max(around + 5, g + 12), arrive = f.p.y - d * 0.13;
    if (arrive < safe) continue;
    let clear = true;
    for (let t = 0.1; t < 0.95 && clear; t += 0.1) { const px = f.p.x + (x - f.p.x) * t, py = -f.p.z + (y + f.p.z) * t; if (walker.surface(px, py) > Math.max(safe, f.p.y - d * t * 0.13) - 4) clear = false; }
    if (!clear) continue;
    const score = d + Math.abs(off) * 200;                         // the nearest open spot ahead: "down here"
    if (score < bestS) { bestS = score; best = new THREE.Vector3(x, g, -y); best.ground = true; best.safe = safe; }
  }
  return best;
}
const street = { t: 0, hit: null };
function updateStreet(f, dt) {
  street.t -= dt;
  if (f.state !== 'glide') { street.hit = null; ring2.visible = false; return; }
  if (street.t <= 0) { street.t = 0.2; street.hit = pickStreet(f); }
  ring2.visible = !!street.hit;
  if (street.hit) { ring2.position.set(street.hit.x, street.hit.y + 0.3, street.hit.z); ring2.scale.setScalar(Math.max(1, ring2.position.distanceTo(f.p) / 110) * (1 + Math.sin(clock * 3 + 1) * 0.06)); }
}
// open street ahead that the glide reaches in a straight line (no spiral down between the walls)
function pickGround(f) {
  let best = null, bestD = 1e9;
  for (let off = -0.8; off <= 0.81; off += 0.2) for (let d = 25; d <= 280; d += 8) {
    const h = f.heading + off, x = f.p.x + Math.sin(h) * d, z = f.p.z - Math.cos(h) * d, g = ground(x, -z);
    if (!(g < f.p.y - d * 0.075 + 4 && g > f.p.y - d * 0.38)) continue;
    if (!walker.open(x, -z, 3.5)) continue;
    let clear = true;
    for (let t = 0.1; t < 0.95 && clear; t += 0.1) { const px = f.p.x + (x - f.p.x) * t, pz = f.p.z + (z - f.p.z) * t, py = f.p.y + (g + 1.5 - f.p.y) * t; if (walker.surface(px, -pz) > py - 2.5) clear = false; }
    if (!clear) continue;
    const slope = (g - f.p.y) / d, score = d + Math.abs(off) * 120 + Math.abs(slope + 0.2) * 500;
    if (score < bestD) { bestD = score; best = new THREE.Vector3(x, g, z); best.ground = true; }
  }
  return best;
}
// where the eyes point: the first roof along the view ray, if it is a roof a glider could reach
function updateAim(f) {
  aim.ok = false; aim.hit = null; ring.visible = false;
  if (f.state !== 'glide') return;
  const dir = new THREE.Vector3(); camera.getWorldDirection(dir);
  for (let t = 12; t < 700; t += 3) {
    const x = f.p.x + dir.x * t, y = f.p.y + dir.y * t, z = f.p.z + dir.z * t;
    const top = roof.top(x, -z);
    if (top === -Infinity) { if (y < ground(x, -z)) break; continue; }
    if (y <= top) {
      const g = ground(x, -z); if (top - g < 11) break;          // houses have pitched roofs: no landing there
      const flat = [[4, 0], [-4, 0], [0, 4], [0, -4]].every(([dx, dy]) => Math.abs(roof.top(x + dx, -z + dy) - top) < 4);
      const dh = Math.hypot(x - f.p.x, z - f.p.z);
      aim.hit = new THREE.Vector3(x, top, z); aim.ok = flat && top < f.p.y - dh * 0.07 + 6 && top > f.p.y - dh * 0.6;
      ring.position.set(x, top + 0.4, z); ring.visible = true; ring.material.color.set(aim.ok ? 0xffd9b0 : 0x6a5a4a); ring.material.opacity = aim.ok ? 0.9 : 0.35;
      ring.scale.setScalar(1 + Math.sin(clock * 3) * 0.06);
      break;
    }
  }
}
addEventListener('keyup', (e) => keys.delete(e.code));
renderer.domElement.addEventListener('pointerdown', (e) => { pointer = true; startAudio(); if (e.pointerType !== 'touch') renderer.domElement.requestPointerLock?.()?.catch?.(() => {}); });
addEventListener('pointerup', () => { pointer = false; });
addEventListener('mousemove', (e) => { if (document.pointerLockElement !== renderer.domElement) return; if (flight.current?.hand && lookDrag) return; look.yaw -= e.movementX * 0.0022; look.pitch = THREE.MathUtils.clamp(look.pitch - e.movementY * 0.0022, -1.3, 1.1); });
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

// touch: a stick on the left (roll by x, pitch by y), a look-drag on the right half of the screen, and hold buttons
const stick = { x: 0, y: 0, id: null, cx: 0, cy: 0 }, tbtn = { tuck: false, flare: false };
let lookDrag = null;
function wireTouch() {
  const pad = $('stick'), knob = pad.firstElementChild, R = 44;
  pad.addEventListener('pointerdown', (e) => { stick.id = e.pointerId; stick.cx = e.clientX; stick.cy = e.clientY; pad.setPointerCapture(e.pointerId); startAudio(); e.preventDefault(); });
  pad.addEventListener('pointermove', (e) => { if (e.pointerId !== stick.id) return; const dx = e.clientX - stick.cx, dy = e.clientY - stick.cy; const l = Math.hypot(dx, dy), k = l > R ? R / l : 1;
    stick.x = THREE.MathUtils.clamp(dx * k / R, -1, 1); stick.y = THREE.MathUtils.clamp(dy * k / R, -1, 1); knob.style.transform = `translate(${dx * k}px, ${dy * k}px)`; });
  const release = (e) => { if (e.pointerId !== stick.id) return; stick.id = null; stick.x = stick.y = 0; knob.style.transform = ''; };
  pad.addEventListener('pointerup', release); pad.addEventListener('pointercancel', release);
  const hold = (id, key) => { const b = $(id); b.addEventListener('pointerdown', (e) => { tbtn[key] = true; b.classList.add('on'); b.setPointerCapture(e.pointerId); e.preventDefault(); });
    const off = () => { tbtn[key] = false; b.classList.remove('on'); }; b.addEventListener('pointerup', off); b.addEventListener('pointercancel', off); };
  hold('tTuck', 'tuck'); hold('tFlare', 'flare');
  $('tJump').addEventListener('pointerdown', (e) => { e.preventDefault(); startAudio(); primary(); });
  $('tLand').addEventListener('pointerdown', (e) => { e.preventDefault(); tryLand(false); });
  $('tLandG').addEventListener('pointerdown', (e) => { e.preventDefault(); tryLand(true); });
  $('tHand').addEventListener('pointerdown', (e) => { e.preventDefault(); toggleHand(); });
  $('tClose').addEventListener('pointerdown', (e) => { e.preventDefault(); toggleClose(); });
  $('tMute').addEventListener('pointerdown', (e) => { e.preventDefault(); muted = !muted; audio?.volume(muted ? 0 : 0.7); $('tMute').textContent = muted ? '♪ off' : '♪ on'; });
  // look by dragging anywhere else on the canvas (right half while flying, anywhere at rest)
  renderer.domElement.addEventListener('pointerdown', (e) => { if (e.pointerType !== 'touch' && !(flight.current?.hand)) return; lookDrag = { id: e.pointerId, x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener('pointermove', (e) => { if (!lookDrag || e.pointerId !== lookDrag.id) return; const dx = e.clientX - lookDrag.x, dy = e.clientY - lookDrag.y; lookDrag.x = e.clientX; lookDrag.y = e.clientY;
    look.yaw -= dx * 0.005; look.pitch = THREE.MathUtils.clamp(look.pitch - dy * 0.005, -1.3, 1.1); });
  const endDrag = (e) => { if (lookDrag && e.pointerId === lookDrag.id) lookDrag = null; };
  renderer.domElement.addEventListener('pointerup', endDrag); renderer.domElement.addEventListener('pointercancel', endDrag);
}
if (touch) wireTouch();
else {
  // desktop without pointer lock (e.g. after Esc): drag to look while holding hands
  renderer.domElement.addEventListener('pointermove', (e) => { if (!lookDrag || e.pointerId !== lookDrag.id) return; const dx = e.clientX - lookDrag.x, dy = e.clientY - lookDrag.y; lookDrag.x = e.clientX; lookDrag.y = e.clientY; look.yaw -= dx * 0.005; look.pitch = THREE.MathUtils.clamp(look.pitch - dy * 0.005, -1.3, 1.1); });
  const endDrag = (e) => { if (lookDrag && e.pointerId === lookDrag.id) lookDrag = null; };
  renderer.domElement.addEventListener('pointerup', endDrag); renderer.domElement.addEventListener('pointercancel', endDrag);
}
// no text selection, callouts or page gestures on a phone: every touch belongs to the game
for (const ev of ['selectstart', 'contextmenu']) document.addEventListener(ev, (e) => e.preventDefault());
document.addEventListener('touchmove', (e) => { if (e.cancelable) e.preventDefault(); }, { passive: false });
document.addEventListener('gesturestart', (e) => e.preventDefault());

// on foot: the keys (or the stick) move you relative to where you look; walking turns the body to the view
const walkIn = { x: 0, y: 0, run: false };
let wallAhead = null, mode = '', stepN = 0, pushT = 0;
function readWalk(f, dt = 1 / 60) {
  const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0) - stick.y;
  const side = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) - (keys.has('KeyA') || keys.has('ArrowLeft') ? 1 : 0) + stick.x;
  const yaw = f.heading - look.yaw, l = Math.hypot(fwd, side), k = l > 1 ? 1 / l : 1;
  walkIn.x = (Math.sin(yaw) * fwd + Math.cos(yaw) * side) * k; walkIn.y = (Math.cos(yaw) * fwd - Math.sin(yaw) * side) * k;
  walkIn.run = keys.has('ShiftLeft') || keys.has('ShiftRight') || Math.hypot(stick.x, stick.y) > 0.9;
  if (l > 0.05 && f.state === 'rest') { f.setHeading(yaw); look.yaw = 0; }
  const [x, y] = f.dataXY();
  wallAhead = f.state === 'rest' ? walker.wallNear(x, y, f.feet, f.heading - look.yaw) : null;
  f.wallNear = !!wallAhead && wallAhead.top - f.feet > 6;
  // pushing on into a wall for a moment starts the climb too (the hint says "in front of the wall, push")
  const into = f.state === 'rest' && wallAhead && f.blocked != null && wallAhead.top - f.feet > 1.2 && l > 0.5 && fwd > 0.3 && Math.abs(Math.sin((wallAhead.h - f.heading) / 2)) < 0.31;   // more or less head on, not sliding along it
  pushT = into ? pushT + dt : 0;
  if (pushT > 0.45) { pushT = 0; if (f.climb(f.heading)) { look.yaw = 0; look.pitch = Math.max(look.pitch, 0.35); } }
}
function readInput(f, dt = 1 / 60) {
  readWalk(f, dt);
  const pitch = (keys.has('KeyW') || keys.has('ArrowUp') ? -1 : 0) + (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
  const roll = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) + (keys.has('KeyA') || keys.has('ArrowLeft') ? -1 : 0);
  const foot = f.state === 'rest' || f.state === 'climb';
  const steer = !foot && !f.hand && (document.pointerLockElement || (touch && !lookDrag && stick.id === null));
  f.input.pitch = THREE.MathUtils.clamp(pitch + stick.y + (steer ? -look.pitch * 1.4 : 0), -1, 1);
  f.input.roll = THREE.MathUtils.clamp(roll + stick.x + (steer ? -look.yaw * 1.2 : 0), -1, 1);
  f.input.tuck = keys.has('ShiftLeft') || keys.has('ShiftRight') || tbtn.tuck;
  f.input.flare = keys.has('KeyF') || tbtn.flare;
  // the mouse offsets spring back so the glider levels when the hand rests (a touch look-drag holds while the finger is down)
  if (!foot && !lookDrag && !f.hand) { look.yaw *= Math.pow(0.02, 1 / 60); look.pitch += (-0.08 - look.pitch) * 0.04; }
  if (f.hand) look.yaw = THREE.MathUtils.clamp(look.yaw, -2.6, 2.2);
  if (touch) { const tj = $('tJump'); tj.classList.toggle('show', f.state === 'climb' || (f.state === 'rest' && (!!wallAhead || !f.street)));
    tj.textContent = f.state === 'climb' ? '蹴って飛ぶ' : wallAhead ? '登る' : '飛び降りる'; document.body.classList.toggle('onfoot', foot); const lb = $('tLand'); lb.classList.toggle('show', f.state === 'glide'); lb.textContent = aim.ok ? '屋上へ ◎' : '屋上へ';
    const lg = $('tLandG'); lg.classList.toggle('show', f.state === 'glide'); lg.textContent = street.hit ? '道へ ◎' : '道へ';
    const hb = $('tHand'); hb.classList.toggle('show', f.hand || sakiNear()); hb.textContent = f.hand ? 'はなす' : '手をつなぐ';
    const cb = $('tClose'); cb.classList.toggle('show', f.hand); cb.textContent = f.close ? 'はなれる' : '寄せる'; $('stick').style.opacity = f.hand ? 0.25 : 1; }
}

const hud = { alt: $('alt'), spd: $('spd'), state: $('state'), here: $('here') };
const K = (k, t) => `<kbd>${k}</kbd> ${t}`;
const HINTS = {
  fly: [K('W S', '下げ 上げ'), K('A D', '傾ける'), K('Shift', '絞る'), K('F', '広げる'), K('E', '見ている屋上に降りる'), K('Shift+E / G', '道に降りる（青緑の輪）'), K('H', 'サキと手をつなぐ'), K('J', '寄せる')].join('　'),
  roof: [K('W A S D', '歩く'), K('Shift', '走る'), K('Space', '飛び降りる / 壁を登る')].join('　'),
  street: [K('W A S D', '歩く'), K('Shift', '走る'), K('Space', '壁を登る（壁に向かって歩き続けても）')].join('　'),
  climb: [K('Space', '壁を蹴って飛ぶ')].join('　'),
};
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000); T2090.fps = T2090.fps * 0.95 + 0.05 / Math.max(1e-3, (now - last) / 1000); last = now; clock += dt;
  // adaptive quality: a phone that cannot hold 40 fps drops to a 1.0 pixel ratio and shorter tree distances (a steady
  // frame rate matters more than detail when you are looking at her from a metre away)
  if (clock > 8 && !adapted && T2090.fps < 40) { adapted = true; renderer.setPixelRatio(1); LOD.fullTrees = 350; LOD.hideTrees = 1200; LOD.hideCars = 600; LOD.nearProps = Math.min(LOD.nearProps, 60); if (undergrowth && T2090.terrainMat) T2090.terrainMat.uniforms.detQ.value = 0; if (city) city.fullRadius = 600; }
  const f = flight.current;
  readInput(f, dt); if (f.hand) autopilot.step(f, dt); f.step(dt);
  if (f.state === 'rest') f.walk(dt, walkIn.x, walkIn.y, walkIn.run); else if (f.state === 'climb') f.climbStep(dt);
  if (f.state === 'crash' && f.stateTime > 1.0) { f.placeOnFoot(f.restPos.x, -f.restPos.z, f.heading); wasFlying = true; }
  // just down: on a roof look half-right at her on the edge; in the street, ahead with her at your right
  if (f.state === 'rest' && wasFlying) { if (f.climbed) { f.climbed = false; look.yaw = 0; look.pitch = -0.15; } else if (f.street) { look.yaw = -0.35; look.pitch = -0.06; } else { look.yaw = -0.8; look.pitch = -0.5; } }
  wasFlying = f.state !== 'rest';
  // camera: in flight the eyes look along the velocity, tilted by the angle of attack and the bank
  if (f.state === 'rest' || f.state === 'climb') {
    camera.position.copy(f.p);
    camera.rotation.set(look.pitch, -f.heading + look.yaw, 0);
  } else {
    let pitchAng = Math.asin(THREE.MathUtils.clamp(f.v.length() > 1 ? f.v.y / f.v.length() : 0, -1, 1));
    if (f.dropping) pitchAng = Math.max(pitchAng, -0.6);              // coming down on the cape: look ahead and down, not at your feet
    camera.position.copy(f.p);
    const gaze = f.handBlend * (0.8 + 0.3 * f.closeBlend);             // toward her face at his left; look.yaw moves freely from there
    // holding hands, the eyes do not follow every dip of the glide: her position is fixed to the eye, so a nodding
    // camera read as her face shaking; the pitch is smoothed hard and she is placed in the same smoothed frame
    camPitch += (pitchAng - camPitch) * Math.min(1, dt * (f.hand ? 0.8 : 5));
    camera.rotation.set(camPitch * 0.85 - 0.08 + f.aoaVis * 0.012 + ((document.pointerLockElement || touch) ? look.pitch * 0.5 : 0) + gaze * 0.06 + f.closeBlend * 0.05, -f.heading + gaze + ((document.pointerLockElement || touch) ? look.yaw * (f.hand ? 1.0 : 0.4) : 0), -f.roll * 0.55 * (1 - f.handBlend));
    f.camPitch = camPitch;
  }
  camera.updateMatrixWorld();
  updateAim(f); updateStreet(f, dt); body.update(f, dt); saki.update(f, dt, clock); props?.update(clock, camera.position); story.update(f, dt); clouds.update(clock, camera.position); thermals.update(dt, clock, !(f.state === 'climb' || (f.state === 'rest' && f.street)));
  undergrowth.update(camera.position, dt, clock, f.p.y - ground(f.p.x, -f.p.z) < 40);
  city?.update(camera.position); heroes.update(camera.position);
  shared.camPos.value = camera.position; sunRig.update(camera, (f.state === 'rest' || f.state === 'climb') && f.feet - ground(f.p.x, -f.p.z) < 30 ? 'near' : 'far');
  renderer.render(scene, camera);
  labels.update(camera, dt);
  // footsteps: one per stride half (the walker counts the distance)
  if (f.state === 'rest' && f.walkSpeed > 0.3 && f.hopZ === 0) { const len = f.walkSpeed > 2.5 ? 1.15 : 0.72; const n = Math.floor(f.stride / len); if (n !== stepN) { stepN = n; audio?.step(f.walkSpeed > 2.5); } }
  if (audio) { audio.setFlying(f.state !== 'rest' && f.state !== 'climb'); audio.setSpeed(f.state === 'rest' || f.state === 'climb' ? 0 : f.speed); }
  hudT += dt; if (hudT < 0.2) { requestAnimationFrame(loop); return; } hudT = 0;        // the HUD text five times a second
  hud.alt.textContent = (f.p.y - ground(f.p.x, -f.p.z)).toFixed(0) + ' m';
  hud.spd.textContent = (f.speed * 3.6).toFixed(0) + ' km/h';
  hud.here.textContent = labels.here;
  // a train left on the line, close by on foot
  if (f.state === 'rest' && f.street) { const [px, py] = f.dataXY(); if (T2090.rails.carPos.some(([x, y]) => Math.abs(x - px) < 25 && Math.abs(y - py) < 25)) story.say('train', { every: 90000 }); }
  const m = f.state === 'climb' ? 'climb' : f.state === 'rest' ? (f.street ? 'street' : 'roof') : 'fly';
  if (m !== mode) { mode = m; $('keys').innerHTML = HINTS[m]; }
  if (m !== 'fly') { hud.state.textContent = m === 'climb' ? '登っている · Space 蹴って飛ぶ' : (wallAhead ? 'Space 登る · ' : m === 'roof' ? 'Space 飛び降りる · ' : '') + (f.walkSpeed > 2.5 ? '走る' : f.walkSpeed > 0.2 ? '歩く' : m === 'street' ? '街' : '屋上'); }
  else hud.state.textContent = (f.hand ? (f.close ? 'サキと · J はなれる · H はなす' : 'サキと · J 寄せる · H はなす') : (sakiNear() ? 'H 手をつなぐ · ' : '') + (f.state === 'glide' ? (aim.ok ? 'E 屋上 ◎ · ' : 'E 屋上 · ') + (street.hit ? 'G 道 ◎ · ' : 'G 道 · ') : '') + f.state);
  $('lift').firstElementChild.style.width = Math.min(100, f.updraft / 10 * 100) + '%';
  $('liftTxt').textContent = f.updraft > 1.5 ? '上昇気流 ↑' + f.updraft.toFixed(1) : '';
  requestAnimationFrame(loop);
}
init().catch((e) => { console.error(e); $('loading').textContent = 'failed: ' + e.message; });
