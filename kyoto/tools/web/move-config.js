// Kyoto's movement settings for shared/move (no DOM, no three: a server could import this too).
// walk: on the walk map, eye 1.6 m, 1.5 m/s (Shift 4.2), gliding along walls; entering it limits the pitch to ±0.6.
// fly: 30 m/s (Shift ×4, wheel 2–600), forward follows the view, never closer than 2 m to the ground.
// W/S/↑/↓ forward/back, A/D strafe, ←/→ turn 1.5 rad/s, E/Space up, Q/C down, drag grabs the scene;
// the touch stick, ▲▼ and fast toggle via ui.js.
import { flyMode, rasterWalkMode, glideStep } from '../../../shared/move/index.js';

export const SPEED_RANGE = [2, 600];
export const MOVE = {
  mode: 'walk', speed: 30, speedRange: SPEED_RANGE,
  modes: {
    walk: rasterWalkMode({ strategy: glideStep({ radius: 0.12, up: 0.75, down: 1.2 }), eye: 1.6, speed: 1.5, runSpeed: 4.2,
      smooth: 8, follow: 10, searchRadius: 60, pitchOnEnter: 0.6 }),
    fly: flyMode({ fastMul: 4, smooth: 4, followPitch: true,
      clamp: (pos, vel, world) => { const gz = world.ground(pos.x, pos.y); if (pos.z < gz + 2.0) { pos.z = gz + 2.0; if (vel.z < 0) vel.z = 0; } } }),
  },
  input: {
    bindings: {
      forward: ['KeyW', 'ArrowUp'], back: ['KeyS', 'ArrowDown'], right: ['KeyD'], left: ['KeyA'],
      turnLeft: ['ArrowLeft'], turnRight: ['ArrowRight'], up: ['KeyE', 'Space'], down: ['KeyQ', 'KeyC'], fast: ['ShiftLeft', 'ShiftRight'],
    },
    turnRate: 1.5,
    drag: { mouse: 0.003, touch: 0.005, pitchLimit: 1.5 },
    wheel: { min: SPEED_RANGE[0], max: SPEED_RANGE[1], modes: ['fly'] },
  },
};
