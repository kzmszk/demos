// shared/move — walking / flying shared by the city demos (docs/movement-unification-proposal.md).
// Core (node / Worker safe): state, step/command, flyMode, rasterWalkMode + glideStep / strictStep.  Browser shell: Input, views, Mover,
// TouchControls (the phone's stick and ▲▼).
// Imported by relative path from each city's tools/web (esbuild bundles it); never imports three.
export { MOVE_SCHEMA, createState, toPlain, fromPlain } from './state.js';
export { step, command } from './step.js';
export { Vec3, AXES } from './vec.js';
export { flyMode } from './fly.js';
export { rasterWalkMode } from './raster-walk.js';
export { glideStep } from './walk-glide.js';
export { strictStep } from './walk-strict.js';
export { Input, DRAG_SIGN, textField } from './input.js';
export { zUpView, alhambraView } from './view.js';
export { Mover } from './mover.js';
export { TouchControls } from './touch.js';
