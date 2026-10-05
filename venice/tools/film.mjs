// film.mjs — a short film of the viewer, cut on the bars of its own title music.
//   node film.mjs scout OUTDIR [shot,shot]    three stills per shot (start, middle, end) at 960x540
//   node film.mjs render OUTDIR [shot,shot]   every frame (1920x1080, 30 fps) as JPEG, then the sound, then OUTDIR/venezia.mp4
// Headless Chrome on the real GPU (as snap.mjs); the page steps the app frame by frame (film_page.js), so the motion is
// smooth whatever the machine.  Music: the title piece, bars 0-11 (intro and theme) then 32-35 (the close), rendered
// offline by the app's own sound engine; the natural sounds are rendered offline from what each frame saw.
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn, execFileSync } from 'node:child_process';
import { SHOTS, CUT } from './film_shots.mjs';
const HERE = path.dirname(new URL(import.meta.url).pathname), ROOT = path.resolve(HERE, '../public');
const [MODE = 'scout', OUT = '/tmp/venezia-film', ONLYS] = process.argv.slice(2);
const ONLY = ONLYS ? new Set(ONLYS.split(',')) : null;
const SCOUT = MODE === 'scout' || MODE === 'eval', W = SCOUT ? 960 : 1920, H = SCOUT ? 540 : 1080, FPS = 30;
fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.bin': 'application/octet-stream', '.webp': 'image/webp', '.png': 'image/png', '.hdr': 'application/octet-stream', '.ktx2': 'image/ktx2', '.wasm': 'application/wasm' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, path.normalize(p));
  if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-length': fs.statSync(f).size });
  fs.createReadStream(f).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ven-film-'));
const chrome = spawn('google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--hide-scrollbars', '--mute-audio',
  `--window-size=${W},${H}`, '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-webgpu', '--enable-features=Vulkan', '--use-vulkan=native', '--ignore-gpu-blocklist', '--enable-gpu', 'about:blank'], { stdio: 'ignore' });
const pf = path.join(profile, 'DevToolsActivePort');
for (let i = 0; i < 100 && !fs.existsSync(pf); i++) await sleep(100);
const port = fs.readFileSync(pf, 'utf8').split('\n')[0];
const target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
let seq = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method === 'Runtime.exceptionThrown') console.log('EXC', JSON.stringify(m.params.exceptionDetails).slice(0, 800));
  else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') console.log('console.error', m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 400)); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 1200)); return r.result.value; };
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/index.html?pr=1#ja` });
for (let t0 = Date.now(); !(await ev('!!(window.VEN && VEN.prepared)').catch(() => false)); await sleep(300)) if (Date.now() - t0 > 120000) throw new Error('the page never got ready');
await ev(fs.readFileSync(path.join(HERE, 'film_page.js'), 'utf8'));
await ev(`FILM.begin({ fps: ${FPS} })`);

// ---------------------------------------------------------------- the timeline, on the music's bars
const { bars } = await ev('FILM.bars("title")');
const t0 = 0.15;                                          // the piece starts this far into the music render
const tl = (bar) => (bar <= CUT.a1 ? t0 + bars[bar] : t0 + bars[CUT.a1] + bars[bar] - bars[CUT.b0]);   // film time of a bar line
let musicEnd = 0;
const plan = SHOTS.map((S) => {
  const a = tl(S.bars[0]), b = tl(S.bars[1]) + (S.tail || 0);
  return { ...S, start: a, dur: b - a, f0: Math.round(a * FPS), f1: Math.round(b * FPS) };
});
musicEnd = plan[plan.length - 1].start + plan[plan.length - 1].dur;
console.log('film', musicEnd.toFixed(2), 's,', plan.map((p) => `${p.name} ${p.start.toFixed(2)}+${p.dur.toFixed(2)}`).join(' | '));

if (MODE === 'eval') {                       // node film.mjs eval OUT shot "expression": stream the shot's tiles, evaluate
  const S = plan.find((p) => p.name === ONLYS);
  await ev(`FILM.shot(${JSON.stringify(S)})`);
  console.log(JSON.stringify(await ev(process.argv[5])));
} else if (SCOUT) {
  for (const S of plan) {
    if (ONLY && !ONLY.has(S.name)) continue;
    const r = await ev(`FILM.shot(${JSON.stringify({ ...S, dur: S.dur })})`);
    for (const u of S.scout || [0, 0.5, 1]) {
      const b64 = await ev(`FILM.still(${u})`);
      fs.writeFileSync(path.join(OUT, `${S.name}-${Math.round(u * 100)}.jpg`), Buffer.from(b64, 'base64'));
    }
    console.log('scouted', S.name, JSON.stringify(r), JSON.stringify(await ev('VEN.info()')));
  }
} else {
  // ---------------------------------------------------------------- frames
  const T = Date.now();
  for (const S of plan) {
    if (ONLY && !ONLY.has(S.name)) continue;
    const r = await ev(`FILM.shot(${JSON.stringify({ ...S })})`);
    const n = S.f1 - S.f0;
    for (let i = 0; i < n; i++) {
      const b64 = await ev('FILM.next()');
      fs.writeFileSync(path.join(OUT, 'frames', `${String(S.f0 + i).padStart(5, '0')}.jpg`), Buffer.from(b64, 'base64'));
    }
    console.log('shot', S.name, n, 'frames', JSON.stringify(r), `${((Date.now() - T) / 1000).toFixed(0)}s`);
  }
  if (!ONLY) {
    // ---------------------------------------------------------------- sound: the natural sounds the frames heard, the music
    const save = async (what, o, file) => {
      const n = await ev(`FILM.sound('${what}', ${JSON.stringify(o)})`); let b = '';
      for (let i = 0; i < n; i++) b += await ev(`FILM.chunk(${i})`);
      fs.writeFileSync(path.join(OUT, file), Buffer.from(b, 'base64'));
    };
    await save('amb', { tail: 4 }, 'amb.wav');
    await save('music', { sec: t0 + bars[CUT.b1] + 10 }, 'music_full.wav');          // the whole piece; cut in film_mix.py
    fs.writeFileSync(path.join(OUT, 'cut.json'), JSON.stringify({ t0, a: t0 + bars[CUT.a1], b: t0 + bars[CUT.b0], end: musicEnd, bars }));
    console.log('sound rendered');
  }
}
ws.close(); chrome.kill(); server.close();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* fine */ }
process.exit(0);
