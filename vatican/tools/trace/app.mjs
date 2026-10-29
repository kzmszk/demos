// The movement glue of web/main.js, reduced to what touches controls and the camera, in the same order:
//   initial camera (main.js:29) → controls built and disabled (:48) → setMode (:139-148) → the F key (:169-170,
//   via the b-tour / b-free buttons :149, :153) → setMode('title') (:261) → the frame step (:233-238) →
//   VAT.stopLoop / VAT.look (:275-276).
// Title and tour place the camera themselves (updateTitle / updateTour → poseAt); a fixed path stands in for them.
// Keep this in step with main.js: the trace is only meaningful while main.js drives controls this way.
export function makeApp({ win, camera, createControls }) {
  camera.position.set(260, -360, 230); camera.lookAt(-280, -8.7, 60);
  const controls = createControls(); controls.enabled = false;
  let mode = 'title', clock = 0;
  const setMode = (m) => { mode = m; controls.enabled = m === 'free'; if (m === 'free') controls.syncFromCamera(); };
  win.addEventListener('keydown', (e) => { if (e.code === 'KeyF' && mode !== 'title') setMode(mode === 'free' ? 'tour' : 'free'); });
  setMode('title');
  const scripted = (dt) => {
    clock += dt; const a = clock * 0.2;
    camera.position.set(260 * Math.cos(a), -360 + 40 * Math.sin(a), 230 - 30 * a);
    camera.lookAt(-280, -8.7 + 20 * Math.sin(a), 60);
  };
  return {
    controls,
    get mode() { return mode; },
    setMode,
    step(dt) { if (mode === 'free') controls.update(dt); else scripted(dt); },
    stopLoop() { setMode('free'); controls.enabled = false; },
    look(p, t) { setMode('free'); camera.position.set(...p); camera.lookAt(...t); controls.syncFromCamera(); },
  };
}
