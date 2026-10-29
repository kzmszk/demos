// Vatican's movement settings for shared/move (no DOM, no three: a server could import this too).
// Drone-style free flight in a z-up world: drag to look, WASD/arrows to move (←/→ strafe), E/Q (Space/C)
// up/down, Shift ×4, wheel 2–400 in any mode.  Velocity is smoothed so it feels like a drone gliding.
import { flyMode } from '../../../shared/move/index.js';

export const SPEED_RANGE = [2, 400];
export const MOVE = {
  mode: 'fly', speed: 25, speedRange: SPEED_RANGE,
  modes: { fly: flyMode({ fastMul: 4, smooth: 3 }) },
  input: {
    bindings: {
      forward: ['KeyW', 'ArrowUp'], back: ['KeyS', 'ArrowDown'], right: ['KeyD', 'ArrowRight'], left: ['KeyA', 'ArrowLeft'],
      up: ['KeyE', 'Space'], down: ['KeyQ', 'KeyC'], fast: ['ShiftLeft', 'ShiftRight'],
    },
    drag: { mouse: 0.0035, touch: 0.0035, pitchLimit: 1.5 },
    wheel: { min: SPEED_RANGE[0], max: SPEED_RANGE[1], modes: null },
  },
};
