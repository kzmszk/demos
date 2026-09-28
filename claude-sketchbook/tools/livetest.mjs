// node tools/livetest.mjs outdir W H — drive the interactive book like a person would
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const [out, W = '1440', H = '900', touch] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const ctx = await browser.newContext({ viewport: { width: +W, height: +H }, deviceScaleFactor: 1, hasTouch: !!touch, isMobile: !!touch });
const page = await ctx.newPage();
const errs = [];
page.on('pageerror', (e) => { errs.push(e.message); console.log('pageerror', e.message); });
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console', m.type(), m.text().slice(0, 200)); });
await page.goto('file://' + path.join(here, '../dist/index.html'));
await page.waitForFunction(() => window.SKETCH && window.SKETCH.live, null, { timeout: 60000 });
const snap = async (name) => { await page.screenshot({ path: path.join(out, name + '.png') }); console.log('shot', name); };
const wait = (ms) => page.waitForTimeout(ms);
await wait(1500); await snap('01-closed');
await wait(2000); await snap('02-closed-later');
await page.mouse.click(+W / 2, +H / 2);
await wait(2600); await snap('03-opening');
await wait(4000); await snap('04-p1-drawing');
await wait(9000); await snap('05-p1-more');
await page.keyboard.press('ArrowRight');
await wait(900); await snap('06-turning');
await wait(3000); await snap('07-p2');
// drag the right page over by hand
const m = await page.evaluate(() => window.SKETCH.live.screenMetrics());
await page.mouse.move(m.spine + m.page * 0.9, +H * 0.6);
await page.mouse.down();
for (let i = 1; i <= 12; i++) { await page.mouse.move(m.spine + m.page * 0.9 - i * m.page * 0.06, +H * 0.6 - i * 2); await wait(30); }
await snap('08-drag-mid');
for (let i = 13; i <= 26; i++) { await page.mouse.move(m.spine + m.page * 0.9 - i * m.page * 0.06, +H * 0.6 - i * 2); await wait(30); }
await page.mouse.up();
await wait(2500); await snap('09-after-drag');
// jump ahead: turn to the last spread
while ((await page.evaluate(() => window.SKETCH.live.spread)) < 5) { await page.keyboard.press('ArrowRight'); await wait(2200); }
await wait(1500); await snap('10-last-spread');
// draw on the blank page
const pts = await page.evaluate(() => {
  const L = window.SKETCH.live, app = L.app;
  const THREE = null;
  const out = [];
  for (const [x, y] of [[40, 60], [60, 80], [80, 70], [100, 110], [70, 140], [50, 120]]) {
    const v = app.leaves[4].pagePoint('back', x, y, new app.camera.position.constructor());
    v.project(app.camera);
    out.push([(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]);
  }
  return out;
});
await page.mouse.move(pts[0][0], pts[0][1]);
await page.mouse.down();
for (let i = 1; i < pts.length; i++) {
  const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
  for (let k = 1; k <= 10; k++) { await page.mouse.move(x0 + (x1 - x0) * k / 10, y0 + (y1 - y0) * k / 10); await wait(16); }
}
await page.mouse.up();
await wait(800); await snap('11-drawn');
await page.keyboard.press('ArrowRight');
await wait(2600); await snap('12-back-cover');
console.log('errors:', errs.length, 'reader strokes', await page.evaluate(() => window.SKETCH.live.reader));
await browser.close();
