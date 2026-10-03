// bundle tools/web -> public/app.js (three + addons included)
import * as esbuild from '/home/kazu/work/demos/node_modules/esbuild/lib/main.js';
const dev = process.argv.includes('--dev');
await esbuild.build({
  entryPoints: ['web/main.js'], bundle: true, format: 'esm', outfile: '../public/app.js',
  minify: !dev, sourcemap: dev ? 'inline' : false, target: 'es2022',
  alias: { 'three/addons': './node_modules/three/examples/jsm' }, logLevel: 'info',
});
