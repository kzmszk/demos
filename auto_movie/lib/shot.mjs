// Screenshot helper: headless Chrome via CLI (no extra dependencies).
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { run, ensureDir } from './util.mjs';

export const CHROME = process.env.CHROME_BIN || 'google-chrome';

/** Render an HTML file (or string) to a PNG. */
export async function screenshot(htmlOrPath, out, { width = 1280, height = 720, scale = 1, wait = 400 } = {}) {
  ensureDir(path.dirname(out));
  let file = htmlOrPath, tmp = null;
  if (!fs.existsSync(htmlOrPath) || htmlOrPath.includes('\n')) {
    tmp = path.join(os.tmpdir(), `automovie-shot-${process.pid}-${Date.now()}.html`);
    fs.writeFileSync(tmp, htmlOrPath);
    file = tmp;
  }
  const args = [
    '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
    `--window-size=${width},${height}`, `--force-device-scale-factor=${scale}`, `--virtual-time-budget=${wait * 5}`,
    `--screenshot=${path.resolve(out)}`, 'file://' + path.resolve(file),
  ];
  const r = await run(CHROME, args, { timeoutMs: 60000 });
  if (tmp) fs.rmSync(tmp, { force: true });
  if (!fs.existsSync(out)) throw new Error(`screenshot failed: ${r.stderr.slice(-400)}`);
  return out;
}
