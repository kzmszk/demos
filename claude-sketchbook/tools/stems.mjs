// node tools/stems.mjs outdir — dry piano and dry foley, separately
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const out = process.argv[2];
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 256, height: 256 } });
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto('file://' + path.join(here, '../dist/index.html') + '?video&size=256');
await page.waitForFunction(() => window.__ready, null, { timeout: 120000 });
const info = await page.evaluate(() => window.SKETCH.renderStems());
for (const name of ['piano', 'foley']) {
  const chunks = [];
  for (let i = 0; i < info[name]; i += 4 << 20) chunks.push(Buffer.from(await page.evaluate(([n, i, s]) => window.SKETCH.stemChunk(n, i, s), [name, i, 4 << 20]), 'base64'));
  fs.writeFileSync(path.join(out, name + '.wav'), Buffer.concat(chunks));
}
await browser.close();
