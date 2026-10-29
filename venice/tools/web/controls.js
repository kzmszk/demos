// Camera modes:  fly (free: drag to look, WASD, E/Q up/down, Shift fast, wheel = speed),
// walk (WASD on the walk raster: calli, campi, bridges, porticoes; eye 1.62 m; Shift runs),
// boat (seated in the gondola: drag to look around; manual rowing with W/S and A/D when steering).
// A shared/move Mover with venice's settings (move-config.js); main.js and film_page.js use it as before.
import * as THREE from 'three/webgpu';
import { Mover, zUpView } from '../../../shared/move/index.js';
import { MOVE } from './move-config.js';

// client-only mode: the camera sits in the gondola (ride.seatPose); the look-around is relative to the bow
function boatMode(ride) {
  return {
    yaw: 0, pitch: -0.05,
    enter() { this.yaw = 0; this.pitch = -0.05; },
    look(dx, dy) { this.yaw = Math.max(-2.6, Math.min(2.6, this.yaw + dx)); this.pitch = Math.max(-1.0, Math.min(1.0, this.pitch + dy)); },
    update(mv, frame) {
      if (ride.mode === 'manual') { ride.steer.thrust = frame.f; ride.steer.turn = -frame.r; }
      ride.seatPose(mv.camera, this.yaw, this.pitch);
    },
  };
}

export class Controls extends Mover {
  constructor(camera, dom, o = {}) {
    const dir = new THREE.Vector3(), tiles = o.tiles;
    super({ ...MOVE, modes: { ...MOVE.modes, boat: boatMode(o.ride) }, dom,
      view: zUpView(camera, { readDir: (c) => c.getWorldDirection(dir) }), world: { sample: (x, y) => tiles.sample(x, y) } });
    this.camera = camera; this.dom = dom;
  }
}
