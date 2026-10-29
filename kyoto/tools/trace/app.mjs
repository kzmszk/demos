// The movement glue of web/main.js and web/ui.js, reduced to what touches controls and the camera, in the same order:
//   initial camera (main.js:83-85) → Controls(camera, canvas, {tiles, ground}) (:323) → app.begin / setMode /
//   goPlace (:92-111) via ui.start (ui.js:149-154) and the mode buttons (ui.js:75) → titleCam (:383-388) → the frame
//   step (:408-409) → the touch stick (:328-336), ▲▼ and the fast toggle (ui.js:99-107) → KYO.walkAt / place / look
//   (:447-450).  Keep this in step with main.js: the trace is only meaningful while main.js drives controls this way.
export const PLACES = [
  { id: 'start', mode: 'walk', at: [5, 5], yaw: 0.3, pitch: 0.18 },
  { id: 'stairs', mode: 'walk', at: [18, 12], yaw: 0.1, pitch: 0.5 },
  { id: 'air', mode: 'fly', at: [50, 30], z: 80, yaw: -2, pitch: -0.4 },
];
const START = PLACES[0];

export function makeApp({ camera, tiles, ground, createControls }) {
  camera.up.set(0, 0, 1);
  camera.position.set(START.at[0], START.at[1], 30); camera.lookAt(START.at[0] + Math.cos(START.yaw), START.at[1] + Math.sin(START.yaw), 30.1);
  const terrainZ = (x, y) => { const w = tiles.sample(x, y); return w.z !== undefined ? w.z : (ground(x, y) || 30); };
  let swayT = 0;
  const titleYaw = () => START.yaw + 0.08 * Math.sin(swayT * 0.05);
  const titleCam = (dt) => {
    swayT += dt;
    const w = tiles.sample(START.at[0], START.at[1]), z = (w.z != null ? w.z + 1.6 : 30), yaw = titleYaw();
    camera.position.set(START.at[0], START.at[1], z);
    camera.lookAt(START.at[0] + Math.cos(yaw), START.at[1] + Math.sin(yaw), z + 0.22);
  };
  let controls;
  const app = {
    mode: 'title',
    begin(m) {
      const yaw = titleYaw(); this.goPlace(START); controls.yaw = yaw;
      if (m === 'fly') this.setMode('fly');
    },
    setMode(m) {
      if (m === 'walk' && this.mode !== 'walk') controls.pitch = 0;
      if (m === 'fly' && this.mode === 'walk') camera.position.z += 1.5;
      this.mode = m; controls.setMode(m);
    },
    goPlace(p) {
      this.setMode(p.mode);
      if (p.at) {
        const z = p.z != null ? p.z : terrainZ(p.at[0], p.at[1]) + 1.6;
        camera.position.set(p.at[0], p.at[1], z); controls.yaw = p.yaw; controls.pitch = p.pitch != null ? p.pitch : 0.02;
      }
      controls.walkZ = null;
    },
  };
  controls = createControls();
  const start = (m) => app.begin(m);
  return {
    app, controls,
    start,
    step(dt) { if (app.mode === 'title') titleCam(dt); if (app.mode !== 'title') controls.update(dt); },
    button(m) { app.setMode(m); },
    stick(x, y) { const l = Math.hypot(x, y); if (l > 1) { x /= l; y /= l; } controls.move.x = x; controls.move.y = y; },
    stickEnd() { controls.move.x = controls.move.y = 0; },
    vert(v) { controls.vert = v; },
    vertOff(v) { if (controls.vert === v) controls.vert = 0; },
    fastToggle() { controls.fastLatch = !controls.fastLatch; },
    walkAt(x, y, yaw = 0) { if (app.mode === 'title') start('walk'); app.setMode('walk'); camera.position.set(x, y, terrainZ(x, y) + 1.6); controls.yaw = yaw; controls.pitch = 0; controls.walkZ = null; },
    place(id) { if (app.mode === 'title') start('walk'); app.goPlace(PLACES.find((p) => p.id === id)); },
    look(p, t) { if (app.mode === 'title') start('fly'); app.setMode('fly'); camera.position.set(...p); camera.lookAt(...t); controls.syncFromCamera(); },
    // film_page.js F.begin / F.shot: controls switched off, the camera posed directly, vel written for the sound
    film(p, t) { app.setMode('walk'); controls.enabled = false; camera.position.set(...p); camera.lookAt(...t); controls.vel.set(0.5, 0.25, 0); },
  };
}
