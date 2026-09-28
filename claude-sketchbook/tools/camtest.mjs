// node tools/camtest.mjs out.png t '{"t":[x,y,z],"dist":..,"elev":..,"azim":..,"roll":..,"fov":..}'
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const [out, t, ...shots] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1080 } });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto('file://' + path.join(here, '../dist/index.html') + '?video&size=1080' + (process.env.Q ? '&' + process.env.Q : ''));
await page.waitForFunction(() => window.__ready, null, { timeout: 120000 });
const cdp = await page.context().newCDPSession(page);
let k = 0;
for (const sh of shots) {
  await page.evaluate(([t, sh]) => { window.SKETCH.app.shotOverride = JSON.parse(sh); window.SKETCH.frame(+t); }, [t, sh]);
  const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(out.replace('.png', `_${k++}.png`), Buffer.from(shot.data, 'base64'));
}
await browser.close();
