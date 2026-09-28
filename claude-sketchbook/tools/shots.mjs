// node tools/shots.mjs outdir t1 t2 ... — render film frames at the given times (non-decreasing)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const [out, ...ts] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const size = +(process.env.SIZE || 1080);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: size, height: size } });
page.on('pageerror', (e) => console.log('pageerror', e.message));
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console', m.type(), m.text().slice(0, 300)); });
const t0 = Date.now();
await page.goto('file://' + path.join(here, '../dist/index.html') + '?video&size=' + size);
await page.waitForFunction(() => window.__ready, null, { timeout: 120000 });
console.log('loaded in', Date.now() - t0, 'ms; total', await page.evaluate(() => window.SKETCH.total), 'strokes', await page.evaluate(() => window.SKETCH.strokes));
const cdp = await page.context().newCDPSession(page);
for (const t of ts.map(Number)) {
  const a = Date.now();
  // walk up to t in 1/30 s steps so drawing and the cover progress the way they would in the film
  await page.evaluate(async (t) => {
    const S = window.SKETCH;
    S._t = S._t || 0;
    while (S._t + 1 / 15 < t) { S._t += 1 / 15; S.app.data.pages.forEach((p, i) => {}); }
    S._t = t;
    S.frame(t);
  }, t);
  const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(out, `t${String(t).padStart(6, '0')}.png`), Buffer.from(shot.data, 'base64'));
  console.log('t', t, Date.now() - a, 'ms');
}
await browser.close();
