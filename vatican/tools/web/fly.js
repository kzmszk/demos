// Free flight for the 'free' mode: a shared/move Mover with vatican's settings (move-config.js).
// main.js uses enabled / syncFromCamera() / update(dt), as with the old hand-written controls.
import * as THREE from 'three';
import { Mover, zUpView } from '../../../shared/move/index.js';
import { MOVE } from './move-config.js';

export class FlyControls extends Mover {
  constructor(camera, dom) {
    const dir = new THREE.Vector3();
    super({ ...MOVE, dom, view: zUpView(camera, { readDir: (c) => c.getWorldDirection(dir), setUp: false }) });
    this.camera = camera; this.dom = dom;
  }
}
