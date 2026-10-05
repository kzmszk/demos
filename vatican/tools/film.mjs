// film.mjs — a one-minute film of VATICANO, cut on the bars of the tour's own score.
//   node film.mjs scout OUTDIR [shot,shot]    three stills per shot (start, middle, end) at 960x540
//   node film.mjs render OUTDIR [shot,shot]   every frame (1920x1080, 30 fps) as JPEG, then the sound (film_mix.py makes the mp4)
//   node film.mjs sound OUTDIR                only the sound (the shots traced without drawing)
//   node film.mjs info OUTDIR                 the tour's segments and key times
// Headless Chrome on the real GPU (as snap.mjs); the page steps the app frame by frame (film_page.js), so the motion is
// smooth whatever the machine.  Music: the score's first movements (the approach, bars 0-8, then the square from its
// bar 4), rendered offline by the app's own sound engine; the fountains and bells of the square on top.
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn, execFileSync } from 'node:child_process';
import { SHOTS, CUT, BELLS } from './film_shots.mjs';
const HERE = path.dirname(new URL(import.meta.url).pathname), ROOT = path.resolve(HERE, '../public');
const [MODE = 'scout', OUT = '/tmp/vaticano-film', ONLYS] = process.argv.slice(2);
const ONLY = ONLYS ? new Set(ONLYS.split(',')) : null;
const SCOUT = MODE === 'scout' || MODE === 'info' || MODE === 'probe' || MODE === 'seq', W = SCOUT ? 960 : 1920, H = SCOUT ? 540 : 1080, FPS = 30;
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
  else if (m.method === 'Runtime.consoleAPICalled' && (m.params.type === 'error' || m.params.type === 'warning')) console.log('console.' + m.params.type, m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 400));
  else if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') console.log('LOG', m.params.entry.text.slice(0, 300), m.params.entry.url || ''); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 1200)); return r.result.value; };
await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/index.html#ja` });
for (let t0 = Date.now(); !(await ev('!!(window.VAT && VAT.ready)').catch(() => false)); await sleep(300)) if (Date.now() - t0 > 120000) throw new Error('the page never got ready');
await ev(fs.readFileSync(path.join(HERE, 'film_page.js'), 'utf8'));
await ev(`FILM.begin({ fps: ${FPS} })`);

// ---------------------------------------------------------------- the timeline, on the score's bars (60 bpm: 4 s a bar)
// film bars 0..CUT.a1-1 are the score's bars from 0; then the score jumps from CUT.a1 to CUT.b0 (absolute bars)
const BAR = 4, t0 = 0;
const tl = (bar) => bar * BAR;                            // film time of a film bar line
let musicEnd = 0;
const plan = SHOTS.map((S) => {
  const a = tl(S.bars[0]), b = tl(S.bars[1]) + (S.tail || 0);
  return { ...S, start: a, dur: b - a, f0: Math.round(a * FPS), f1: Math.round(b * FPS) };
});
musicEnd = plan[plan.length - 1].start + plan[plan.length - 1].dur;
console.log('film', musicEnd.toFixed(2), 's,', plan.map((p) => `${p.name} ${p.start.toFixed(2)}+${p.dur.toFixed(2)}`).join(' | '));

if (MODE === 'probe') {                      // node film.mjs probe OUT shot u: a still after a long wait, and the loader state
  const S = plan.find((p) => p.name === ONLYS), u = +(process.argv[5] || 0.5);
  await ev(`FILM.shot(${JSON.stringify(S)})`);
  for (let i = 0; i < 3; i++) { console.log('pending', JSON.stringify(await ev('FILM.pending()'))); await sleep(1500); }
  fs.writeFileSync(path.join(OUT, `${S.name}-probe.jpg`), Buffer.from(await ev(`FILM.still(${u})`), 'base64'));
  console.log('zone', JSON.stringify(await ev(`(() => { const W = VAT.world; return { current: W.current && W.current.zone, visible: Object.entries(W.groups).filter(([n, g]) => g.visible).map(([n]) => n), cam: VAT.camera.position.toArray().map((v) => +v.toFixed(2)), dir: VAT.camera.getWorldDirection(new VAT.THREE.Vector3()).toArray().map((v) => +v.toFixed(2)), meshes: (() => { let n = 0, v = 0; VAT.scene.traverse((o) => { if (o.isMesh) { n++; if (o.visible) v++; } }); return [n, v]; })() }; })()`)));
  console.log('pending after', JSON.stringify(await ev('FILM.pending()')), JSON.stringify(await ev('VAT.info()')));
} else if (MODE === 'seq') {                 // node film.mjs seq OUT shot: step through the shot, report each frame's state
  const S = plan.find((p) => p.name === ONLYS);
  await ev(`FILM.shot(${JSON.stringify(S)})`);
  const n = S.f1 - S.f0;
  for (let i = 0; i < n; i++) {
    await ev('FILM.next()');
    const st = await ev(`(() => { const W = VAT.world, c = VAT.camera; let vis = 0; VAT.scene.traverse((o) => { if (o.isMesh && o.visible) { let p = o.parent, ok = true; while (p) { if (!p.visible) ok = false; p = p.parent; } if (ok) vis++; } }); return { zone: W.current && W.current.zone, cam: c.position.toArray().map((v) => +v.toFixed(2)), nan: c.matrixWorld.elements.some((v) => !isFinite(v)), vis, calls: VAT.renderer.info.render.calls, tris: VAT.renderer.info.render.triangles }; })()`);
    if (i >= n - 12 || st.nan || st.calls < 5) console.log(i, JSON.stringify(st));
  }
} else if (MODE === 'info') {
  for (const s of await ev('FILM.segments()')) console.log(s.id.padEnd(12), 't0', s.t0, 'dur', s.dur, 'zone', s.zone, 'keys', s.keys.join(' '));
} else if (SCOUT) {
  for (const S of plan) {
    if (ONLY && !ONLY.has(S.name)) continue;
    const r = await ev(`FILM.shot(${JSON.stringify({ ...S, dur: S.dur })})`);
    for (const u of S.scout || [0, 0.5, 1]) {
      const b64 = await ev(`FILM.still(${u})`);
      fs.writeFileSync(path.join(OUT, `${S.name}-${Math.round(u * 100)}.jpg`), Buffer.from(b64, 'base64'));
    }
    console.log('scouted', S.name, JSON.stringify(r), JSON.stringify(await ev('VAT.info()')));
  }
} else {
  // ---------------------------------------------------------------- frames (MODE sound: only the camera, for the sound)
  const T = Date.now();
  for (const S of plan) {
    if (ONLY && !ONLY.has(S.name)) continue;
    const r = await ev(`FILM.shot(${JSON.stringify({ ...S })})`);
    const n = S.f1 - S.f0;
    if (MODE === 'sound') { await ev(`FILM.trace(${n})`); continue; }
    for (let i = 0; i < n; i++) {
      const b64 = await ev('FILM.next()');
      fs.writeFileSync(path.join(OUT, 'frames', `${String(S.f0 + i).padStart(5, '0')}.jpg`), Buffer.from(b64, 'base64'));
      if (process.env.DEBUG && i >= n - 4) console.log(i, JSON.stringify(await ev(`({ zone: VAT.world.current && VAT.world.current.zone, info: VAT.renderer.info.render, last: FILM.lastInfo })`)));
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
    await save('amb', { tail: 6, bells: BELLS }, 'amb.wav');
    await save('music', { sec: CUT.b1 * BAR + 10, from: 0, until: CUT.b1 * BAR }, 'music_full.wav');   // the score from 0 to the square's end; cut in film_mix.py
    fs.writeFileSync(path.join(OUT, 'cut.json'), JSON.stringify({ t0, a: CUT.a1 * BAR, b: CUT.b0 * BAR, end: musicEnd }));
    console.log('sound rendered');
  }
}
ws.close(); chrome.kill(); server.close();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* fine */ }
process.exit(0);
