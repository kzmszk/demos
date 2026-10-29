// Resolves 'three' and 'three/webgpu' to kyoto/tools/node_modules/three (npm ci first): the movement code only uses
// Vector3, so the WebGPU entry is not needed in node (proposal §4.0 A2: alias three/webgpu → three).
import { registerHooks } from 'node:module';
const tools = new URL('../package.json', import.meta.url).href;
registerHooks({
  resolve(spec, ctx, next) {
    if (spec !== 'three' && spec !== 'three/webgpu') return next(spec, ctx);
    return next('three', { ...ctx, parentURL: tools });
  },
});
