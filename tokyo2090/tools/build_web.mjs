import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import * as esbuild from 'esbuild';
const here = path.dirname(fileURLToPath(import.meta.url));
const three = path.join(here, 'node_modules/three');
await esbuild.build({
  absWorkingDir: here, entryPoints: ['web/main.js'], outfile: '../public/app.js',
  bundle: true, format: 'esm', target: 'es2022', minify: !process.argv.includes('--dev'),
  sourcemap: process.argv.includes('--dev') ? 'inline' : false,
  alias: { 'three': path.join(three, 'build/three.module.js'), 'three/addons': path.join(three, 'examples/jsm') },
  logLevel: 'info',
});
fs.copyFileSync(path.join(three, 'LICENSE'), path.resolve(here, '../public/THREE-LICENSE.txt'));
