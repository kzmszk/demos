// Alhambra's movement settings (no DOM, no three).  Keys by e.key, lower-cased: W/S/↑/↓ forward/back, A/D/←/→ strafe
// (no turn keys), E/Q up/down in fly, Shift ×2.4.  The axes are summed with the stick and ▲▼, not clamped (walk and
// fly normalise the horizontal pair).  Drag grabs the scene at .003 rad/px (mouse and touch, primary button), pitch
// ±1.48.  The wheel belongs to the modes (orbit zooms; walk and fly only keep the page from scrolling).
// Walking (Navigation), flying and the orbit are client-only modes in controls.js.
export const MOVE = {
  walkSpeed: 2.3, flySpeed: 17, fastMul: 2.4,
  flyBox: { x: [-2200, 1800], z: [-1800, 1700], aboveGround: 0.7, top: 850 },
  input: {
    keyField: 'key', compose: 'sum', preventDefault: true, resetOn: ['blur', 'hidden'],
    bindings: {
      forward: ['w', 'arrowup'], back: ['s', 'arrowdown'], right: ['d', 'arrowright'], left: ['a', 'arrowleft'],
      up: ['e'], down: ['q'], fast: ['shift'],
    },
    drag: { mouse: 0.003, touch: 0.003, pitchLimit: 1.48, button: 0 },
    wheel: null,
  },
};
