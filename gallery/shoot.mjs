#!/usr/bin/env node
/* DEMOS — cover shooter. Builds the site, serves site/ locally, drives headless Chrome over the
 * DevTools protocol and captures every frame listed in each demo.json "shots" into
 * gallery/covers/<folder>/NN.webp, then rebuilds so the covers ship with the site.
 *
 *   node gallery/shoot.mjs              every demo with shots
 *   node gallery/shoot.mjs raster …     only these folders
 *
 * A shot is { "path": "page.html#hash", "wait": ms after load, "eval": "js", "after": ms after eval }.
 * Needs Chrome/Chromium on PATH (or CHROME=/path/to/chrome). No npm dependencies. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'site');
const COVERS = path.join(ROOT, 'gallery', 'covers');
const W = 1440, H = 900, SCALE = 2 / 3; /* frames are 960×600 */
const only = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

execFileSync(process.execPath, [path.join(ROOT, 'gallery/build.mjs')], { stdio: 'inherit' });

/* ---------- tiny static server over site/ ---------- */
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  const file = path.join(OUT, path.normalize(p));
  if (!file.startsWith(OUT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end('not found');
    return;
  }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

/* ---------- headless Chrome ---------- */
const findChrome = () => {
  if (process.env.CHROME) return process.env.CHROME;
  for (const c of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    try {
      return execFileSync('which', [c]).toString().trim();
    } catch (e) {
      /* try the next name */
    }
  }
  const mac = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (fs.existsSync(mac)) return mac;
  throw new Error('Chrome not found (set CHROME=/path/to/chrome)');
};
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'demos-shoot-'));
const chrome = spawn(
  findChrome(),
  ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio', `--window-size=${W},${H}`, 'about:blank'],
  { stdio: 'ignore' }
);
const portFile = path.join(profile, 'DevToolsActivePort');
for (let i = 0; i < 100 && !fs.existsSync(portFile); i++) await sleep(100);
const port = fs.readFileSync(portFile, 'utf8').split('\n')[0];
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));

let seq = 0;
const pending = new Map(), waiters = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    if (m.error) rej(new Error(m.error.message));
    else res(m.result);
  } else if (m.method) {
    for (const w of waiters.slice()) if (w.method === m.method) waiters.splice(waiters.indexOf(w), 1), w.res(m.params);
  }
};
const send = (method, params = {}) =>
  new Promise((res, rej) => {
    const id = ++seq;
    pending.set(id, { res, rej });
    ws.send(JSON.stringify({ id, method, params }));
  });
const next = (method, ms = 20000) =>
  Promise.race([new Promise((res) => waiters.push({ method, res })), sleep(ms).then(() => null)]);

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });

/* ---------- shoot ---------- */
let failed = 0;
for (const slug of fs.readdirSync(ROOT).sort()) {
  const metaFile = path.join(ROOT, slug, 'demo.json');
  if (!fs.existsSync(metaFile) || (only.length && !only.includes(slug))) continue;
  const shots = JSON.parse(fs.readFileSync(metaFile, 'utf8')).shots || [];
  if (!shots.length) continue;
  const dir = path.join(COVERS, slug);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  for (const [i, s] of shots.entries()) {
    /* a query per shot forces a fresh document even when only the hash differs */
    const [p, h] = String(s.path || '').split('#');
    const url = `${base}/${slug}/${p}?shot=${i}${h ? '#' + h : ''}`;
    try {
      const loaded = next('Page.loadEventFired');
      await send('Page.navigate', { url });
      await loaded;
      await sleep(s.wait ?? 1800);
      if (s.eval) {
        await send('Runtime.evaluate', { expression: s.eval, awaitPromise: true });
        await sleep(s.after ?? 1100);
      }
      /* the clip is in document coordinates: capture where the page is scrolled to */
      const vp = (await send('Page.getLayoutMetrics')).cssVisualViewport;
      const clip = { x: vp.pageX, y: vp.pageY, width: W, height: H, scale: SCALE };
      const shot = await send('Page.captureScreenshot', { format: 'webp', quality: 82, clip });
      const file = path.join(dir, `${String(i + 1).padStart(2, '0')}.webp`);
      fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
      console.log(`  ${slug}/${path.basename(file)}  ${s.path}${s.eval ? '  + eval' : ''}`);
    } catch (e) {
      failed++;
      console.error(`✗ ${slug} #${i + 1}: ${e.message}`);
    }
    await send('Runtime.evaluate', { expression: 'try { localStorage.clear(); sessionStorage.clear() } catch (e) {}' }).catch(() => {});
  }
}

ws.close();
const exited = new Promise((r) => chrome.once('exit', r));
chrome.kill();
await Promise.race([exited, sleep(5000)]);
server.close();
try {
  fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
} catch (e) {
  console.warn(`! could not remove ${profile}`);
}
execFileSync(process.execPath, [path.join(ROOT, 'gallery/build.mjs'), '--skip-prebuild'], { stdio: 'inherit' });
process.exit(failed ? 1 : 0);
