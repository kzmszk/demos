import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
const here = path.dirname(fileURLToPath(import.meta.url));
const own = createRequire(import.meta.url);
const shared = createRequire(path.resolve(here, '../../vatican/tools/package.json'));
function resolve(name) { try { return own.resolve(name); } catch { return shared.resolve(name); } }
const esbuild = await import(resolve('esbuild'));
const three = path.dirname(path.dirname(resolve('three')));
await esbuild.build({
  absWorkingDir: here, entryPoints: ['web/main.js'], outfile: '../public/app.js',
  bundle: true, format: 'esm', target: 'es2022', minify: !process.argv.includes('--dev'),
  sourcemap: process.argv.includes('--dev') ? 'inline' : false,
  alias: { 'three': path.join(three, 'build/three.module.js'), 'three/addons': path.join(three, 'examples/jsm') },
  logLevel: 'info',
});
fs.copyFileSync(path.join(three, 'LICENSE'), path.resolve(here, '../public/THREE-LICENSE.txt'));
const size = fs.statSync(path.resolve(here, '../public/app.js')).size;
if (size > 24 * 1024 * 1024) throw new Error('Cloudflare static asset limit exceeded');
