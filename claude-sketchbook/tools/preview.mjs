// node tools/preview.mjs out.mp4 fps size [t0 t1] — quick low-res motion preview of the film (no audio)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const [out, fpsS = '10', sizeS = '540', t0S, t1S] = process.argv.slice(2);
const fps = +fpsS, size = +sizeS;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: size, height: size } });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto('file://' + path.join(here, '../dist/index.html') + '?video&size=' + size);
await page.waitForFunction(() => window.__ready, null, { timeout: 120000 });
const total = await page.evaluate(() => window.SKETCH.total);
const t0 = t0S ? +t0S : 0, t1 = t1S ? +t1S : total;
const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '26', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const cdp = await page.context().newCDPSession(page);
const n = Math.floor((t1 - t0) * fps);
const start = Date.now();
// pages must be advanced monotonically from 0, so step through the skipped part quickly
if (t0 > 0) await page.evaluate((t0) => { for (let t = 0; t < t0; t += 0.25) window.SKETCH.app.data.pages.forEach(() => {}); }, t0);
for (let i = 0; i <= n; i++) {
  const t = t0 + i / fps;
  await page.evaluate((t) => window.SKETCH.frame(t), t);
  const shot = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 90 });
  if (!ff.stdin.write(Buffer.from(shot.data, 'base64'))) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % 100 === 0) console.log(`${i}/${n}  t=${t.toFixed(2)}  ${((Date.now() - start) / (i + 1)).toFixed(0)} ms/frame`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log('done', out);
