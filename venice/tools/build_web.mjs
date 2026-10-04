// build_web.mjs — bundle web/*.js into public/app.js (three.js included).  node build_web.mjs [--dev]
import * as esbuild from 'esbuild';
const dev = process.argv.includes('--dev');
await esbuild.build({ entryPoints: ['web/main.js'], bundle: true, format: 'esm', target: 'es2022', outfile: '../public/app.js', minify: !dev, sourcemap: dev, logLevel: 'info', legalComments: 'none' });
