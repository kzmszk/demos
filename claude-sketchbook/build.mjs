#!/usr/bin/env node
// Bundle src/ (and three.js) into one self-contained HTML file: dist/index.html
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const dev = process.argv.includes('--dev');
const worker = await build({
  entryPoints: [path.join(here, 'src/audio/worker.js')],
  bundle: true, format: 'iife', minify: !dev, write: false, target: ['es2020'], logLevel: 'warning',
});
const res = await build({
  define: { __WORKER__: JSON.stringify(worker.outputFiles[0].text) },
  entryPoints: [path.join(here, 'src/main.js')],
  bundle: true,
  format: 'iife',
  minify: !dev,
  write: false,
  target: ['es2020'],
  legalComments: 'eof',
  logLevel: 'warning',
});
let js = res.outputFiles[0].text;
js = js.replace(/<\/script/gi, '<\\/script');
const html = fs.readFileSync(path.join(here, 'src/template.html'), 'utf8').replace('/*BUNDLE*/', () => js);
fs.mkdirSync(path.join(here, 'dist'), { recursive: true });
fs.writeFileSync(path.join(here, 'dist/index.html'), html);
console.log(`dist/index.html  ${(html.length / 1024).toFixed(0)} KB`);
