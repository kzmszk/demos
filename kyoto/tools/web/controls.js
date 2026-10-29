// Camera modes:  walk (WASD on the walk map: streets, steps, slopes, bridges; eye 1.6 m; Shift runs) and
// fly (free: drag to look, WASD, E/Q up/down, Shift fast, wheel = speed; never below the ground).
// A shared/move Mover with kyoto's settings (move-config.js); main.js, ui.js and film_page.js use it as before.
import * as THREE from 'three/webgpu';
import { Mover, zUpView } from '../../../shared/move/index.js';
import { MOVE } from './move-config.js';

export class Controls extends Mover {
  constructor(camera, dom, o = {}) {
    const dir = new THREE.Vector3(), tiles = o.tiles, ground = o.ground;
    super({ ...MOVE, dom, view: zUpView(camera, { readDir: (c) => c.getWorldDirection(dir) }), world: {
      sample: (x, y) => tiles.sample(x, y),
      // the walk map where loaded, else the coarse terrain
      ground: (x, y) => { const w = tiles.sample(x, y); return w.z !== undefined ? w.z : (ground ? ground(x, y) : -1e9); },
    } });
    this.camera = camera; this.dom = dom;
  }
}
