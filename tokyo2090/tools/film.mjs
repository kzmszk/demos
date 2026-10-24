// film.mjs — a one-minute film of TOKYO 2090, cut on the bars of the game's own Gymnopédie.
//   node tools/film.mjs scout OUTDIR [shot,shot]    three stills per shot (start, middle, end) at 960x540
//   node tools/film.mjs render OUTDIR [shot,shot]   every frame (1920x1080, 30 fps) as JPEG, then the sound
//   node tools/film.mjs sound OUTDIR                only the sound
// then: python3 tools/film_mix.py OUTDIR  ->  OUTDIR/tokyo2090.mp4
// Headless Chrome on the real GPU (as snap.mjs); the page steps the game frame by frame (film_page.js), so the motion
// is smooth whatever the machine.
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn } from 'node:child_process';
import { SHOTS, BAR } from './film_shots.mjs';
const HERE = path.dirname(new URL(import.meta.url).pathname), ROOT = path.resolve(HERE, '../public');
const [MODE = 'scout', OUT = '/tmp/tokyo2090-film', ONLYS] = process.argv.slice(2);
const ONLY = ONLYS ? new Set(ONLYS.split(',')) : null;
const SCOUT = MODE === 'scout', W = SCOUT ? 960 : 1920, H = SCOUT ? 540 : 1080, FPS = 30;
fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.bin': 'application/octet-stream', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.glb': 'model/gltf-binary', '.wasm': 'application/wasm' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, path.normalize(p));
  if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-length': fs.statSync(f).size });
  fs.createReadStream(f).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 't2090-film-'));
const chrome = spawn('google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--hide-scrollbars', '--mute-audio',
  `--window-size=${W},${H}`, '--autoplay-policy=no-user-gesture-required', '--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist', '--enable-gpu', 'about:blank'], { stdio: 'ignore' });
const pf = path.join(profile, 'DevToolsActivePort');
for (let i = 0; i < 100 && !fs.existsSync(pf); i++) await sleep(100);
const port = fs.readFileSync(pf, 'utf8').split('\n')[0];
const target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
let seq = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method === 'Runtime.exceptionThrown') console.log('EXC', JSON.stringify(m.params.exceptionDetails).slice(0, 800));
  else if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'warning')) console.log('console.' + m.params.type, m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 400)); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 1200)); return r.result.value; };
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/index.html?nointro&silent` });
for (let t0 = Date.now(); !(await ev('!!(window.T2090 && T2090.ready)').catch(() => false)); await sleep(300)) if (Date.now() - t0 > 180000) throw new Error('the page never got ready');
await ev(fs.readFileSync(path.join(HERE, 'film_page.js'), 'utf8'));
console.log('begin', JSON.stringify(await ev(`FILM.begin({ fps: ${FPS} })`)));

const plan = SHOTS.map((S) => {
  const a = S.bars[0] * BAR, b = S.bars[1] * BAR + (S.tail || 0);
  return { ...S, start: a, dur: b - a, f0: Math.round(a * FPS), f1: Math.round(b * FPS) };
});
const end = plan[plan.length - 1].start + plan[plan.length - 1].dur;
console.log('film', end.toFixed(2), 's,', plan.map((p) => `${p.name} ${p.start}+${p.dur}`).join(' | '));

if (SCOUT) {
  for (const S of plan) {
    if (ONLY && !ONLY.has(S.name)) continue;
    const r = await ev(`FILM.shot(${JSON.stringify(S)})`);
    for (const u of S.scout || [0, 0.5, 1]) fs.writeFileSync(path.join(OUT, `${S.name}-${Math.round(u * 100)}.jpg`), Buffer.from(await ev(`FILM.still(${u})`), 'base64'));
    console.log('scouted', S.name, JSON.stringify(r), JSON.stringify(await ev('T2090.info()')));
  }
} else {
  if (MODE === 'render') {
    const T0 = Date.now();
    for (const S of plan) {
      if (ONLY && !ONLY.has(S.name)) continue;
      const r = await ev(`FILM.shot(${JSON.stringify(S)})`);
      for (let i = 0; i < S.f1 - S.f0; i++) fs.writeFileSync(path.join(OUT, 'frames', `${String(S.f0 + i).padStart(5, '0')}.jpg`), Buffer.from(await ev('FILM.next()'), 'base64'));
      console.log('shot', S.name, S.f1 - S.f0, 'frames', JSON.stringify(r), `${((Date.now() - T0) / 1000).toFixed(0)}s`);
    }
  }
  if (!ONLY) {
    const save = async (what, sec, file) => {
      const n = await ev(`FILM.sound('${what}', ${sec})`); let b = '';
      for (let i = 0; i < n; i++) b += await ev(`FILM.chunk(${i})`);
      fs.writeFileSync(path.join(OUT, file), Buffer.from(b, 'base64'));
    };
    await save('music', end + 9, 'music.wav');
    await save('amb', end + 2, 'amb.wav');
    // the score's bar 0 begins 0.5 s into the render (music.js loopStart); ground shots hear the cicadas
    fs.writeFileSync(path.join(OUT, 'cut.json'), JSON.stringify({ musicOffset: 0.5, end, fps: FPS, shots: plan.map((p) => ({ name: p.name, start: p.start, dur: p.dur, ground: p.kind === 'pan' || p.kind === 'ground' })) }));
    console.log('sound rendered');
  }
}
ws.close(); chrome.kill(); server.close();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* fine */ }
process.exit(0);
