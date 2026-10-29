// Resolves 'three' for the movement trace: vatican/tools/node_modules/three when it is installed, otherwise the
// Vector3 stand-in in three-shim.mjs.  Only web/fly.js and its pre-migration copy trace/fly.orig.js import three
// (shared/move does not), so 'three' is always resolved as if imported from vatican/tools.
import { registerHooks } from 'node:module';
const tools = new URL('../package.json', import.meta.url).href;
const shim = new URL('./three-shim.mjs', import.meta.url).href;
registerHooks({
  resolve(spec, ctx, next) {
    if (spec !== 'three') return next(spec, ctx);
    try { return next(spec, { ...ctx, parentURL: tools }); } catch { return { url: shim, shortCircuit: true }; }
  },
});
