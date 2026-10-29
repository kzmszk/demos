// Venice's movement settings for shared/move (no DOM, no three: a server could import this too).
// fly (the first mode): 12 m/s (Shift ×4, wheel 1–300), level forward.  walk: on the walk raster, eye 1.62 m, 1.45 m/s
// (Shift 3.6), the strict five-point rule (radius 0.24 m, steps up to 0.55 m: bridge_check.py assumes these); entering
// it limits the pitch to ±0.5.  W/S/↑/↓ forward/back, A/D strafe, ←/→ turn 1.2 rad/s, E/Space up, Q/C down,
// drag grabs the scene (the boat's look-around too).
// The gondola (boat) is a client-only mode in controls.js.
import { flyMode, rasterWalkMode, strictStep } from '../../../shared/move/index.js';

export const SPEED_RANGE = [1, 300];
export const MOVE = {
  mode: 'fly', speed: 12, speedRange: SPEED_RANGE,
  modes: {
    walk: rasterWalkMode({ strategy: strictStep({ radius: 0.24, step: 0.55 }), eye: 1.62, speed: 1.45, runSpeed: 3.6,
      smooth: 8, follow: 12, searchRadius: 40, pitchOnEnter: 0.5 }),
    fly: flyMode({ fastMul: 4, smooth: 4 }),
  },
  input: {
    bindings: {
      forward: ['KeyW', 'ArrowUp'], back: ['KeyS', 'ArrowDown'], right: ['KeyD'], left: ['KeyA'],
      turnLeft: ['ArrowLeft'], turnRight: ['ArrowRight'], up: ['KeyE', 'Space'], down: ['KeyQ', 'KeyC'], fast: ['ShiftLeft', 'ShiftRight'],
    },
    turnRate: 1.2,
    drag: { mouse: 0.003, touch: 0.005, pitchLimit: 1.5 },
    wheel: { min: SPEED_RANGE[0], max: SPEED_RANGE[1], modes: ['fly'] },
  },
};
