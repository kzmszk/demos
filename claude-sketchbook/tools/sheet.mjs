// node tools/sheet.mjs out.png "chars" [cols] ; or --text out.png "line1|line2"
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const tmp = path.join(here, '.sheet');
fs.mkdirSync(tmp, { recursive: true });
execFileSync(path.join(here, '../node_modules/.bin/esbuild'), [path.join(here, 'sheet-entry.js'), '--bundle', '--format=iife', '--outfile=' + path.join(tmp, 'b.js')], { stdio: 'inherit' });
fs.writeFileSync(path.join(tmp, 'i.html'), '<!doctype html><meta charset=utf-8><body><script src="b.js"></script>');
const args = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
page.on('pageerror', (e) => console.log('pageerror', e.message));
await page.goto('file://' + path.join(tmp, 'i.html'));
await page.waitForFunction(() => window.__ready);
if (args[0] === '--text') {
  const url = await page.evaluate(([lines, seed]) => window.renderText(lines, { seed }), [args[2].split('|'), args[3] || 0]);
  fs.writeFileSync(args[1], Buffer.from(url.split(',')[1], 'base64'));
} else {
  const res = await page.evaluate(([chars, cols, tidy]) => window.renderSheet([...chars], { cols, tidy }), [args[1], +(args[2] || 10), args[3] ? +args[3] : undefined]);
  if (res.errors.length) console.log('ERRORS:\n' + res.errors.join('\n'));
  fs.writeFileSync(args[0], Buffer.from(res.url.split(',')[1], 'base64'));
}
await browser.close();
