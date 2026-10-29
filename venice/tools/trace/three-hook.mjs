// Resolves 'three' and 'three/webgpu' to venice/tools/node_modules/three (npm ci first): the movement code and the
// gondola ride only use Vector3 / Matrix4 / Group, so the WebGPU entry is not needed in node.  'three/tsl' (imported by
// gondola.js for its materials, never called by the ride) resolves to an empty stand-in.
import { registerHooks } from 'node:module';
const tools = new URL('../package.json', import.meta.url).href;
const TSL = ['vec3', 'float', 'uniform', 'positionLocal', 'sin', 'step', 'fract', 'mix', 'color'];
const tsl = 'data:text/javascript,' + encodeURIComponent(TSL.map((n) => `export const ${n} = () => { throw new Error('tsl'); };`).join('\n'));
registerHooks({
  resolve(spec, ctx, next) {
    if (spec === 'three/tsl') return { url: tsl, shortCircuit: true };
    if (spec !== 'three' && spec !== 'three/webgpu') return next(spec, ctx);
    return next('three', { ...ctx, parentURL: tools });
  },
});
