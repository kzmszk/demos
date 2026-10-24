import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { loadTerrain, terrainSampler, loadRoof } from './data.js';
import { makeTerrainMaterial, buildTerrain } from './terrain.js';
import { makeCityMaterial, City } from './city.js';
import { makeFacadeAtlas, makeDetailTexture } from './facade.js';
import { Flight } from './flight.js';
import { makeSun } from './light.js';
import { makeBody } from './body.js';
import { makeSaki } from './saki.js';
import { loadProps, LOD } from './props.js';
import { makeStory } from './story.js';
import { makeClouds } from './clouds.js';
import { createAudio } from './music.js';
import { makeThermals } from './thermals.js';
import { makeAutopilot } from './hand.js';

const $ = (id) => document.getElementById(id);
const query = new URLSearchParams(location.search);
// phones: touch controls, a lighter profile (smaller shadow map, nearer detail, fewer trees)
const touch = matchMedia('(pointer: coarse)').matches || query.has('touch');
const low = query.get('q') === 'low' || (query.get('q') !== 'high' && touch);
document.body.classList.toggle('touch', touch);
if (low) { LOD.fullTrees = 500; LOD.hideTrees = 1700; LOD.hideCars = 900; }
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
let city, ground, roof, terrainGroup, body, saki, ring, props, story, clouds, thermals, autopilot, audio = null, muted = false, last = performance.now(), started = false, clock = 0;
const aim = { hit: null, ok: false };
const keys = new Set();
const T2090 = window.T2090 = { camera, scene, renderer, keys, ready: false, get flight() { return flight.current; }, get city() { return city; },
  info() { const f = flight.current; return { state: f.state, speed: +f.speed.toFixed(1), gamma: +f.gamma.toFixed(2), roll: +f.roll.toFixed(2), p: f.p.toArray().map((v) => +v.toFixed(0)), alt: +(f.p.y - ground(f.p.x, -f.p.z)).toFixed(0), up: +f.updraft.toFixed(2), aim: aim.ok, hand: f.hand, close: f.close, fps: +T2090.fps.toFixed(0), saki: saki?.state.pos.toArray().map((v) => +v.toFixed(0)), tris: renderer.info.render.triangles, calls: renderer.info.render.calls, tiles: city?.ready }; },
  key(code, down = true) { down ? keys.add(code) : keys.delete(code); },
  hand(on) { const f = flight.current; if (on) { f.hand = true; look.yaw = 0; } else f.hand = false; },
  close(on) { const f = flight.current; f.close = !!on; },
  tryLand,
  // dev / cover hooks: fly(x, y, z, heading) places the glider in the air in data axes; landAt(x, y) lands on that roof
  fly(x, y, z, heading = 0, speed = 18) { const f = flight.current; f.p.set(x, z, -y); f.heading = heading; f.gamma = -0.12; f.roll = 0; f.open = 1; f.state = 'glide'; f.stateTime = 5; f.launch = null; f.launchTop = -1e9;
    f.v.set(Math.sin(heading) * speed, -speed * 0.12, -Math.cos(heading) * speed); f.forward.set(Math.sin(heading), 0, -Math.cos(heading)); f.right.set(Math.cos(heading), 0, Math.sin(heading)); saki?.place(f.p.clone().addScaledVector(f.forward, 18)); },
  landAt(x, y) { const f = flight.current; const t = roof.top(x, y); if (t === -Infinity) return false; f.land(new THREE.Vector3(x, t, -y)); return true; },
  look(yaw, pitch) { look.yaw = yaw; look.pitch = pitch; },
  touch, get stick() { return stick; }, get tbtn() { return tbtn; },
  fps: 0 };

async function init() {
  const [rings, roofData] = await Promise.all([loadTerrain('data/terrain.bin'), loadRoof('data/roof.bin')]);
  ground = terrainSampler(rings); roof = roofData;
  const cover = await new THREE.TextureLoader().loadAsync('data/cover.png');
  cover.magFilter = THREE.LinearFilter; cover.minFilter = THREE.LinearMipmapLinearFilter; cover.generateMipmaps = true; cover.flipY = false; cover.colorSpace = THREE.NoColorSpace;
  // cover.png row 0 is north (y = Y1); the shader samples uv.y from y0 up, so flipY=false + v = (y - y0)/h gives row = h - v
  const tm = makeTerrainMaterial({ ...shared, cover: { value: cover }, coverBox: { value: new THREE.Vector4(-2400, -2000, 7000, 6400) }, ringScale: { value: 0 } });
  terrainGroup = buildTerrain(rings, tm); scene.add(terrainGroup);
  for (const m of terrainGroup.children) for (const k of ['shadowMap', 'shadowMatrix', 'shadowSize']) m.material.uniforms[k] = sunRig.uniforms[k];
  const index = await (await fetch('data/city/index.json')).json();
  const facade = makeFacadeAtlas(); T2090.facade = facade;
  city = new City(scene, makeCityMaterial({ ...shared, atlas: { value: facade.albedo }, atlasMask: { value: facade.mask }, detail: { value: makeDetailTexture() } }), 'data/city', index);
  if (low) { city.fullRadius = 800; city.liteRadius = 6000; city.maxLoading = 1; city.maxSwaps = 1; }
  const f = new Flight(ground, roof); flight.current = f;
  // start on the roof of Shibuya Scramble Square, facing the crossing to the north-west
  const start = query.get('at') ? query.get('at').split(',').map(Number) : [116, -112];
  f.placeOnRoof(start[0], start[1], query.get('hd') ? Number(query.get('hd')) : -0.75);
  camera.position.copy(f.p); camera.rotation.set(-0.35, -f.heading, 0);
  body = makeBody(camera, shared); saki = makeSaki(scene, shared); saki.place(f.p.clone().addScaledVector(f.right, 2));
  ring = new THREE.Mesh(new THREE.RingGeometry(2.6, 3.4, 40), new THREE.MeshBasicMaterial({ color: 0xffd9b0, transparent: true, opacity: 0.85, side: THREE.DoubleSide, depthTest: false }));
  ring.rotation.x = -Math.PI / 2; ring.visible = false; ring.renderOrder = 5; scene.add(ring);
  T2090.ground = ground; T2090.roof = roof; T2090.saki = saki; T2090.aim = aim;
  clouds = makeClouds(scene, shared); thermals = makeThermals(scene, flight); autopilot = makeAutopilot(roof, ground);
  story = makeStory($('say')); T2090.story = story; saki.speaking = () => story.speaking; setTimeout(() => story.say('start'), 1500); setTimeout(() => story.say('edge'), 9000);
  loadProps(scene, { ground, roof, shared, THREE }).then((p) => { props = p; T2090.props = p; }).catch((e) => console.warn('props', e));
  for (let k = 0; k < 40; k++) { city.update(camera.position); await new Promise((r) => setTimeout(r, 60)); if (city.ready > 24) break; }
  $('loading').classList.add('hidden'); started = true; T2090.ready = true;
  if (!query.has('nointro') && !location.hash.includes('nointro')) { $('intro').classList.add('on'); document.body.classList.add('intro'); }
  requestAnimationFrame(loop);
}

let look = { yaw: -0.8, pitch: -0.5 }, pointer = false, camPitch = 0, adapted = false, hudT = 0, wasFlying = false;
function startAudio() { if (!audio && !query.has('silent')) { try { audio = createAudio(); audio.start(); audio.volume(muted ? 0 : 0.7); } catch (e) { console.warn('audio', e); } } }
function dismissIntro() { startAudio(); document.body.classList.remove('intro'); if ($('intro').classList.contains('on')) { $('intro').classList.remove('on'); return true; } return false; }
$('intro').addEventListener('click', dismissIntro); $('intro').addEventListener('touchend', (e) => { e.preventDefault(); dismissIntro(); }, { passive: false });
addEventListener('keydown', (e) => { if (e.code === 'KeyM') { muted = !muted; audio?.volume(muted ? 0 : 0.7); $('mute').textContent = muted ? '♪ off' : '♪ on'; } if (e.code === 'Space' && dismissIntro()) { e.preventDefault(); return; } keys.add(e.code); if (e.code === 'Space') { e.preventDefault(); const f = flight.current; if (f) { f.jump(f.heading - look.yaw); look.yaw = 0; } } if (e.code === 'KeyE') tryLand(); if (e.code === 'KeyH') toggleHand(); if (e.code === 'KeyJ') toggleClose(); });
function tryLand() {
  const f = flight.current; if (!f || f.state !== 'glide') return;
  const target = (aim.ok && aim.hit) ? aim.hit : pickRoof(f);
  if (target && f.land(target)) { f.hand = false; f.close = false; story.say('land', { every: 20000 }); }
  else story.say('noRoof', { every: 6000 });
}
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
// where the eyes point: the first roof along the view ray, if it is a roof a glider could reach
function updateAim(f) {
  aim.ok = false; aim.hit = null; ring.visible = false;
  if (f.state !== 'glide') return;
  const dir = new THREE.Vector3(); camera.getWorldDirection(dir);
  for (let t = 12; t < 700; t += 3) {
    const x = f.p.x + dir.x * t, y = f.p.y + dir.y * t, z = f.p.z + dir.z * t;
    const top = roof.top(x, -z); if (top === -Infinity) { if (y < ground(x, -z)) break; continue; }
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
renderer.domElement.addEventListener('pointerdown', (e) => { pointer = true; startAudio(); if (e.pointerType !== 'touch') renderer.domElement.requestPointerLock?.(); });
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
  $('tJump').addEventListener('pointerdown', (e) => { e.preventDefault(); startAudio(); const f = flight.current; if (f && f.state === 'rest') { f.jump(f.heading - look.yaw); look.yaw = 0; } });
  $('tLand').addEventListener('pointerdown', (e) => { e.preventDefault(); tryLand(); });
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

function readInput(f) {
  const pitch = (keys.has('KeyW') || keys.has('ArrowUp') ? -1 : 0) + (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
  const roll = (keys.has('KeyD') || keys.has('ArrowRight') ? 1 : 0) + (keys.has('KeyA') || keys.has('ArrowLeft') ? -1 : 0);
  const steer = f.state !== 'rest' && !f.hand && (document.pointerLockElement || (touch && !lookDrag && stick.id === null));
  f.input.pitch = THREE.MathUtils.clamp(pitch + stick.y + (steer ? -look.pitch * 1.4 : 0), -1, 1);
  f.input.roll = THREE.MathUtils.clamp(roll + stick.x + (steer ? -look.yaw * 1.2 : 0), -1, 1);
  f.input.tuck = keys.has('ShiftLeft') || keys.has('ShiftRight') || tbtn.tuck;
  f.input.flare = keys.has('KeyF') || tbtn.flare;
  // the mouse offsets spring back so the glider levels when the hand rests (a touch look-drag holds while the finger is down)
  if (f.state !== 'rest' && !lookDrag && !f.hand) { look.yaw *= Math.pow(0.02, 1 / 60); look.pitch += (-0.08 - look.pitch) * 0.04; }
  if (f.hand) look.yaw = THREE.MathUtils.clamp(look.yaw, -2.6, 2.2);
  if (touch) { $('tJump').classList.toggle('show', f.state === 'rest'); const lb = $('tLand'); lb.classList.toggle('show', f.state === 'glide'); lb.textContent = aim.ok ? '降りる ◎' : '降りる';
    const hb = $('tHand'); hb.classList.toggle('show', f.hand || sakiNear()); hb.textContent = f.hand ? 'はなす' : '手をつなぐ';
    const cb = $('tClose'); cb.classList.toggle('show', f.hand); cb.textContent = f.close ? 'はなれる' : '寄せる'; $('stick').style.opacity = f.hand ? 0.25 : 1; }
}

const hud = { alt: $('alt'), spd: $('spd'), state: $('state') };
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000); T2090.fps = T2090.fps * 0.95 + 0.05 / Math.max(1e-3, (now - last) / 1000); last = now; clock += dt;
  // adaptive quality: a phone that cannot hold 40 fps drops to a 1.0 pixel ratio and shorter tree distances (a steady
  // frame rate matters more than detail when you are looking at her from a metre away)
  if (clock > 8 && !adapted && T2090.fps < 40) { adapted = true; renderer.setPixelRatio(1); LOD.fullTrees = 350; LOD.hideTrees = 1200; LOD.hideCars = 600; if (city) city.fullRadius = 600; }
  const f = flight.current;
  readInput(f); if (f.hand) autopilot.step(f, dt); f.step(dt);
  if (f.state === 'crash' && f.stateTime > 1.0) { f.placeOnRoof(f.restPos.x, -f.restPos.z, f.heading); look.yaw = -0.8; look.pitch = -0.5; }
  if (f.state === 'rest' && wasFlying) { look.yaw = -0.8; look.pitch = -0.5; } wasFlying = f.state !== 'rest';
  // camera: in flight the eyes look along the velocity, tilted by the angle of attack and the bank
  if (f.state === 'rest') {
    camera.position.copy(f.p);
    camera.rotation.set(look.pitch, -f.heading + look.yaw, 0);
  } else {
    const pitchAng = Math.asin(THREE.MathUtils.clamp(f.v.length() > 1 ? f.v.y / f.v.length() : 0, -1, 1));
    camera.position.copy(f.p);
    const gaze = f.handBlend * (0.8 + 0.3 * f.closeBlend);             // toward her face at his left; look.yaw moves freely from there
    // holding hands, the eyes do not follow every dip of the glide: her position is fixed to the eye, so a nodding
    // camera read as her face shaking; the pitch is smoothed hard and she is placed in the same smoothed frame
    camPitch += (pitchAng - camPitch) * Math.min(1, dt * (f.hand ? 0.8 : 30));
    camera.rotation.set(camPitch * 0.85 - 0.08 + f.aoaVis * 0.012 + ((document.pointerLockElement || touch) ? look.pitch * 0.5 : 0) + gaze * 0.06 + f.closeBlend * 0.05, -f.heading + gaze + ((document.pointerLockElement || touch) ? look.yaw * (f.hand ? 1.0 : 0.4) : 0), -f.roll * 0.55 * (1 - f.handBlend));
    f.camPitch = camPitch;
  }
  camera.updateMatrixWorld();
  updateAim(f); body.update(f, dt); saki.update(f, dt, clock); props?.update(clock, camera.position); story.update(f, dt); clouds.update(clock, camera.position); thermals.update(dt, clock);
  city?.update(camera.position);
  shared.camPos.value = camera.position; sunRig.update(camera);
  renderer.render(scene, camera);
  if (audio) { audio.setFlying(f.state !== 'rest'); audio.setSpeed(f.speed); }
  hudT += dt; if (hudT < 0.2) { requestAnimationFrame(loop); return; } hudT = 0;        // the HUD text five times a second
  hud.alt.textContent = (f.p.y - ground(f.p.x, -f.p.z)).toFixed(0) + ' m';
  hud.spd.textContent = (f.speed * 3.6).toFixed(0) + ' km/h';
  hud.state.textContent = (f.hand ? (f.close ? 'サキと · J はなれる · H はなす' : 'サキと · J 寄せる · H はなす') : (sakiNear() ? 'H 手をつなぐ · ' : '') + (f.state === 'glide' ? (aim.ok ? 'E 着地 ◎ · ' : 'E 着地 · ') : '') + f.state);
  $('lift').firstElementChild.style.width = Math.min(100, f.updraft / 10 * 100) + '%';
  $('liftTxt').textContent = f.updraft > 1.5 ? '上昇気流 ↑' + f.updraft.toFixed(1) : '';
  requestAnimationFrame(loop);
}
init().catch((e) => { console.error(e); $('loading').textContent = 'failed: ' + e.message; });
