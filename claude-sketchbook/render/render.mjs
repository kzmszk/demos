#!/usr/bin/env node
// Render the film: build, soundtrack offline, frames stepped at a fixed timestep in headless Chromium,
// then ffmpeg. Every frame is a pure function of its time, so chunks can render in parallel.
//
//   node render/render.mjs                         full film → video/claude-sketchbook.mp4
//   node render/render.mjs --jobs 2 --fps 60 --size 1080 --crf 18 --out video/x.mp4
//   node render/render.mjs --from 20 --to 30       a slice (for checking)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const FPS = +arg('fps', 60), SIZE = +arg('size', 1080), JOBS = +arg('jobs', 2), CRF = arg('crf', '18');
const OUT = path.resolve(root, arg('out', 'video/claude-sketchbook.mp4'));
const WORK = path.resolve(root, arg('work', 'video/.work'));
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const GL = ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'];
fs.mkdirSync(WORK, { recursive: true });
fs.mkdirSync(path.dirname(OUT), { recursive: true });

if (!process.argv.includes('--no-build')) execFileSync(process.execPath, [path.join(root, 'build.mjs')], { stdio: 'inherit' });
const url = 'file://' + path.join(root, 'dist/index.html');

async function open(size) {
  const browser = await chromium.launch({ args: GL });
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('pageerror', e.message));
  await page.goto(url + '?video&size=' + size);
  await page.waitForFunction(() => window.__ready, null, { timeout: 180000 });
  return { browser, page };
}

// ---- soundtrack
const wav = path.join(WORK, 'soundtrack.wav');
let total;
{
  const { browser, page } = await open(256);
  total = await page.evaluate(() => window.SKETCH.total);
  if (!fs.existsSync(wav) || process.argv.includes('--audio')) {
    const t0 = Date.now();
    const info = await page.evaluate(() => window.SKETCH.renderAudio());
    const chunks = [];
    for (let i = 0; i < info.length; i += 4 << 20) chunks.push(Buffer.from(await page.evaluate(([i, s]) => window.SKETCH.wavChunk(i, s), [i, 4 << 20]), 'base64'));
    fs.writeFileSync(wav, Buffer.concat(chunks));
    console.log(`soundtrack: ${(Date.now() - t0) / 1000}s, ${(info.length / 1e6).toFixed(1)} MB`);
  }
  await browser.close();
}

// ---- frames
const from = +arg('from', 0), to = Math.min(total, +arg('to', total));
const f0 = Math.round(from * FPS), f1 = Math.round(to * FPS); // [f0, f1)
const per = Math.ceil((f1 - f0) / JOBS);
const chunks = [];
for (let j = 0; j < JOBS; j++) { const a = f0 + j * per, b = Math.min(f1, a + per); if (b > a) chunks.push({ j, a, b, file: path.join(WORK, `chunk${j}.mp4`) }); }
const started = Date.now();
await Promise.all(chunks.map(async (c) => {
  const { browser, page } = await open(SIZE);
  const cdp = await page.context().newCDPSession(page);
  await page.evaluate((t) => window.SKETCH.seek(t), c.a / FPS);
  const ff = spawn(FFMPEG, ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-pix_fmt', 'yuv420p', '-g', String(FPS * 2), '-bf', '2', '-tune', 'film',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', c.file], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let k = c.a; k < c.b; k++) {
    await page.evaluate((t) => window.SKETCH.frame(t), k / FPS);
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
    if (!ff.stdin.write(Buffer.from(shot.data, 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
    if ((k - c.a) % 300 === 0) {
      const done = k - c.a + 1, el = (Date.now() - started) / 1000;
      console.log(`chunk ${c.j}: frame ${k} (${done}/${c.b - c.a})  ${(el / done).toFixed(2)} s/frame  eta ${(((c.b - c.a - done) * el) / done / 60).toFixed(1)} min`);
    }
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
}));
console.log(`frames done in ${((Date.now() - started) / 60000).toFixed(1)} min`);

// ---- join and mux
const list = path.join(WORK, 'list.txt');
fs.writeFileSync(list, chunks.map((c) => `file '${c.file}'`).join('\n') + '\n');
execFileSync(FFMPEG, ['-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-ss', String(from), '-t', String(to - from), '-i', wav,
  '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', '-shortest', OUT], { stdio: 'inherit' });
console.log('wrote', OUT, (fs.statSync(OUT).size / 1e6).toFixed(1), 'MB');
