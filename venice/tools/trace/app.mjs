// The movement glue of web/main.js, reduced to what touches controls, the camera and the gondola ride, in the same
// order: initial camera (main.js:96-101) → GondolaRide + Controls(camera, canvas, {tiles, ride}) (:267-268) → the R key
// (:296-298) → app.begin / setMode / goPlace / setRoute (:109-132) via ui.start and the mode bar (ui.js:82, :127-133) →
// titleCam (:336-343) → the frame step (:353-358) → the touch stick (:325-334) → VEN.mode / route / walkAt / place /
// look (:393-398) → film_page.js F.begin / F.shot / pose.  The ride is the real GondolaRide on a stand-in gondola (a
// bare Group whose pose() only updates its matrix, as Gondola.pose does last).  Keep this in step with main.js.
import { Group } from 'three';
import { GondolaRide } from '../web/gondola.js';
import { ROUTES } from './world.mjs';

export const PLACES = [
  { id: 'start', mode: 'walk', at: [5, 5], yaw: 0.33 },
  { id: 'bridge', mode: 'walk', at: [22, -36], yaw: Math.PI / 2 },
  { id: 'air', mode: 'fly', at: [50, 30], yaw: -2 },
];
const START = PLACES[0], EYE_Z = 1.1 + 1.62;

export function makeApp({ camera, tiles, win, createControls }) {
  camera.up.set(0, 0, 1);
  camera.position.set(START.at[0], START.at[1], EYE_Z); camera.lookAt(START.at[0] + Math.cos(START.yaw), START.at[1] + Math.sin(START.yaw), EYE_Z);
  const gondola = { group: new Group(), pose() { this.group.updateMatrixWorld(true); } };
  const ride = new GondolaRide({ add() {} }, gondola, tiles, ROUTES);
  let controls;
  const app = {
    mode: 'title', speed: 1, routeId: 'grand', rowing: false,
    begin(m) {
      if (m === 'boat') this.setRoute(this.routeId);
      else if (m === 'walk') { const yaw = titleYaw(); this.goPlace(START); controls.yaw = yaw; }
      else this.setMode('fly');
    },
    setMode(m) {
      if (m === 'walk' && this.mode !== 'walk') {
        if (this.mode === 'boat') { camera.position.set(ride.pos.x, ride.pos.y, 3); controls.yaw = ride.heading; }
        controls.pitch = 0;
      }
      if (m === 'fly' && this.mode === 'boat') { controls.syncFromCamera(); }
      this.mode = m; controls.setMode(m);
    },
    goPlace(p) {
      this.setMode(p.mode);
      if (p.at) { camera.position.set(p.at[0], p.at[1], 3); controls.yaw = p.yaw; controls.pitch = 0.02; }
      controls.walkZ = null;
    },
    setRoute(id) { this.routeId = id; ride.setRoute(id, 0); ride.speed = this.speed; this.rowing = false; this.setMode('boat'); },
    setSpeed(s) { this.speed = s; ride.speed = s; },
  };
  controls = createControls(ride);
  win.addEventListener('keydown', (e) => {
    if (e.code === 'KeyR' && app.mode === 'boat') { app.rowing = !app.rowing; ride.mode = app.rowing ? 'manual' : 'auto'; if (!app.rowing) ride.setRoute(app.routeId, ride.s); }
  });
  let swayT = 0;
  const titleYaw = () => START.yaw + 0.1 * Math.sin(swayT * 0.06);
  const titleCam = (dt) => {
    swayT += dt;
    const w = tiles.sample(START.at[0], START.at[1]), z = (w.z != null ? w.z + 1.62 : EYE_Z), yaw = titleYaw();
    camera.position.set(START.at[0], START.at[1], z);
    camera.lookAt(START.at[0] + Math.cos(yaw), START.at[1] + Math.sin(yaw), z + 0.02);
  };
  const start = (m) => app.begin(m);
  let pose = null;
  return {
    app, controls, ride,
    start,
    step(dt) {
      if (app.mode === 'title') titleCam(dt);
      ride.update(dt);
      if (pose) pose(dt); else if (app.mode !== 'title') { controls.update(dt); return true; }
      return false;
    },
    button(m) { app.setMode(m); },
    speedButton(s) { app.setSpeed(s); },
    stick(x, y) { const l = Math.hypot(x, y); if (l > 1) { x /= l; y /= l; } controls.move.x = x; controls.move.y = y; },
    stickEnd() { controls.move.x = controls.move.y = 0; },
    mode(m) { if (app.mode === 'title') start(m); else app.setMode(m); },
    route(name, s = 0, speed = 1) { if (app.mode === 'title') start('boat'); app.setRoute(name); ride.setRoute(name, s); ride.speed = speed; },
    walkAt(x, y, yaw = 0) { if (app.mode === 'title') start('walk'); app.setMode('walk'); camera.position.set(x, y, 3); controls.yaw = yaw; controls.pitch = 0; controls.walkZ = null; },
    place(id) { if (app.mode === 'title') start('walk'); app.goPlace(PLACES.find((p) => p.id === id)); },
    look(p, t) { if (app.mode === 'title') start('fly'); app.setMode('fly'); camera.position.set(...p); camera.lookAt(...t); controls.syncFromCamera(); },
    shotPitch(v) { controls.pitch = v; },
    // film_page.js: F.shot switches the mode, the controls go off and a pose function places the camera and writes vel
    film(kind) {
      if (kind === 'boat') { app.setRoute('grand'); ride.setRoute('grand', 10); ride.speed = 1; } else app.setMode(kind);
      controls.enabled = false;
      let t = 0;
      pose = kind === 'boat'
        ? () => { ride.seatPose(camera, 0.2, -0.1); controls.vel.set(0, 0, 0); }
        : (dt) => { t += dt; camera.position.set(12 + t, 12, 3); camera.lookAt(20, 12 + t, 2.5); controls.vel.set(1, 0, 0); };
    },
    filmEnd() { pose = null; controls.enabled = true; },
    disable() { controls.enabled = false; },
    enable() { controls.enabled = true; },
  };
}
