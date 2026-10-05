// startprobe.mjs — how a cold start behaves: headless Chrome (real GPU, fresh profile = cold shader caches) records
// every pipeline / shader module creation, main-thread long tasks and frame gaps from navigation on.
// node startprobe.mjs out.json "query" [steps.json]   steps: [{eval, wait}] run after VEN.ready (default: title 15 s)
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn } from 'node:child_process';
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../public');
const [out, query = '', stepsFile] = process.argv.slice(2);
const W = +(process.env.W || 1600), H = +(process.env.H || 900);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.bin': 'application/octet-stream', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.png': 'image/png', '.hdr': 'application/octet-stream', '.ktx2': 'image/ktx2', '.wasm': 'application/wasm', '.map': 'application/json' };
// optional bandwidth limit (bytes/s) so download time shows up like on a real connection
const BPS = +(process.env.BPS || 0);
let served = 0;
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, path.normalize(p));
  if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404).end(); return; }
  const size = fs.statSync(f).size; served += size;
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-length': size });
  if (!BPS) { fs.createReadStream(f).pipe(res); return; }
  const s = fs.createReadStream(f, { highWaterMark: 64 * 1024 });
  s.on('data', (c) => { s.pause(); res.write(c); setTimeout(() => s.resume(), (c.length / BPS) * 1000); });
  s.on('end', () => res.end());
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'ven-probe-'));
const env = { ...process.env, __GL_SHADER_DISK_CACHE: process.env.WARM ? '1' : '0' };
const chrome = spawn('google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--hide-scrollbars', '--mute-audio',
  `--window-size=${W},${H}`, '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-webgpu', '--enable-features=Vulkan', '--use-vulkan=native', '--ignore-gpu-blocklist', '--enable-gpu', 'about:blank'], { stdio: 'ignore', env });
const pf = path.join(profile, 'DevToolsActivePort');
for (let i = 0; i < 100 && !fs.existsSync(pf); i++) await sleep(100);
const port = fs.readFileSync(pf, 'utf8').split('\n')[0];
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
let seq = 0; const pending = new Map(); const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.type + ': ' + m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 300));
  else if (m.method === 'Runtime.exceptionThrown') logs.push('EXC: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 600)); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) logs.push('EVAL EXC: ' + JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result?.value; };
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.addScriptToEvaluateOnNewDocument', { source: `(() => {
  const L = window.__probe = { pipes: [], longs: [], gaps: [], marks: [] };
  const wrap = (proto, name, kind) => { const f = proto[name]; if (!f) return;
    proto[name] = function (...a) { const t = performance.now(); const r = f.apply(this, a); const e = { k: kind, t: Math.round(t), js: +(performance.now() - t).toFixed(1), n: (a[0] && a[0].label) || '' };
      if (kind === 'shader') { e.len = (a[0] && a[0].code || '').length; if (e.len > +(window.__BIG || 100000)) (L.big = L.big || []).push(a[0].code); }
      L.pipes.push(e); if (r && r.then) r.then(() => { e.done = Math.round(performance.now() - t); }, () => { e.err = 1; }); return r; }; };
  wrap(GPUDevice.prototype, 'createRenderPipeline', 'sync'); wrap(GPUDevice.prototype, 'createRenderPipelineAsync', 'async');
  wrap(GPUDevice.prototype, 'createComputePipeline', 'csync'); wrap(GPUDevice.prototype, 'createComputePipelineAsync', 'casync');
  wrap(GPUDevice.prototype, 'createShaderModule', 'shader');
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) L.longs.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({ type: 'longtask', buffered: true }); } catch (e) {}
  let last = performance.now(); const raf = () => { const n = performance.now(); if (n - last > 100) L.gaps.push([Math.round(last), Math.round(n - last)]); last = n; requestAnimationFrame(raf); }; requestAnimationFrame(raf);
})();` });
const tNav = Date.now();
await send('Page.navigate', { url: process.env.URL || `${base}/index.html?${query}` });
const mark = async (name) => ev(`(window.__probe && window.__probe.marks.push([${JSON.stringify(name)}, Math.round(performance.now())]), 1)`);
let readyAt = null, preparedAt = null; const tl = [];
const shotTimes = (process.env.SHOTS || '').split(',').filter(Boolean).map(Number).sort((a, b) => a - b);
// the loading line as the page shows it, until the first view is prepared (or the page is ready, for old builds)
for (;;) {
  await sleep(250);
  const r = await ev(`(() => { const q = (s) => (document.querySelector('.title ' + s) || {}).textContent || ''; return [!!(window.VEN && window.VEN.ready), !!(window.VEN && window.VEN.prepared), q('.ptxt'), q('.pstage'), !!document.querySelector('.title.ready')]; })()`);
  if (!r) continue;
  const t = Date.now() - tNav; if (!tl.length || tl[tl.length - 1][1] !== r[2]) tl.push([t, r[2], r[3]]);
  // page screenshots of the loading screen at the given times (ms): the HTML only (headless does not composite WebGPU)
  while (shotTimes.length && t >= shotTimes[0]) { const at = shotTimes.shift(); const sh = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(out.replace(/\.json$/, `-load${at}.png`), Buffer.from(sh.data, 'base64')); }
  if (r[0] && readyAt === null) readyAt = t;
  if (r[1] || r[4]) { preparedAt = t; break; }
  if (readyAt !== null && !process.env.WAITPREP) break;
  if (t > 240000) { console.log('timeout waiting for the first view'); break; }
}
await mark('ready');
if (process.env.TITLE_SHOT) {   // the title over the first view: the rendered frame laid under the HTML, then a page screenshot
  await ev('VEN.freeze()'); await sleep(1800);
  const sh = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(out.replace(/\.json$/, '-title.png'), Buffer.from(sh.data, 'base64'));
}
console.log('loading line:', tl.filter((e, i) => i % Math.max(1, Math.floor(tl.length / 14)) === 0 || i === tl.length - 1).map((e) => `${(e[0] / 1000).toFixed(1)}s ${e[1]}`).join(' | '));
console.log('VEN.ready at', readyAt, 'ms; first view prepared at', preparedAt, 'ms');
const steps = stepsFile ? JSON.parse(fs.readFileSync(stepsFile, 'utf8')) : [{ name: 'title', wait: 15000 }];
for (const s of steps) {
  await mark(s.name || 'step');
  if (s.profile) { await send('Profiler.enable'); await send('Profiler.setSamplingInterval', { interval: 2000 }); await send('Profiler.start'); }
  if (s.eval) await ev(s.eval);
  await sleep(s.wait ?? 10000);
  if (s.profile) {
    const { profile: pr } = await send('Profiler.stop');
    // self time per function (samples x interval), top 25
    const self = new Map(); const byId = new Map(pr.nodes.map((n) => [n.id, n]));
    const dt = pr.timeDeltas; const cnt = new Map();
    for (let i = 0; i < pr.samples.length; i++) cnt.set(pr.samples[i], (cnt.get(pr.samples[i]) || 0) + (dt[i] || 0));
    for (const [id, us] of cnt) { const n = byId.get(id); const k = `${n.callFrame.functionName || '(anon)'} ${n.callFrame.url.split('/').pop()}:${n.callFrame.lineNumber}:${n.callFrame.columnNumber}`; self.set(k, (self.get(k) || 0) + us); }
    console.log('PROFILE', s.name, [...self].sort((a, b) => b[1] - a[1]).slice(0, 25).map(([k, us]) => `${(us / 1000).toFixed(0)}ms ${k}`).join('\n  '));
    // the heaviest stacks: walk parents of the top self nodes
    const parent = new Map(); for (const n of pr.nodes) for (const c of n.children || []) parent.set(c, n.id);
    const top = [...cnt].sort((a, b) => b[1] - a[1]).slice(0, 4);
    for (const [id, us] of top) { const st = []; let x = id; while (x && st.length < 18) { const n = byId.get(x); st.push(`${n.callFrame.functionName || '(anon)'}:${n.callFrame.lineNumber}`); x = parent.get(x); } console.log('STACK', (us / 1000).toFixed(0) + 'ms', st.join(' < ')); }
  }
}
await mark('end');
const P = await ev('window.__probe');
const info = await ev('window.VEN && JSON.stringify(VEN.info())');
const perf = await ev('window.__perf'); const res = { readyAt, preparedAt, tl, served, info, perf, ...P };
fs.writeFileSync(out, JSON.stringify(res));
// summary
const k = (kind) => P.pipes.filter((e) => e.k === kind);
const sum = (a) => a.reduce((x, y) => x + y, 0);
console.log('ready after', readyAt, 'ms; served', (served / 1e6).toFixed(1), 'MB');
console.log('pipelines: sync', k('sync').length, 'async', k('async').length, 'compute', k('csync').length + k('casync').length, 'shader modules', k('shader').length);
console.log('long tasks', P.longs.length, 'total', sum(P.longs.map((l) => l[1])), 'ms; max', Math.max(0, ...P.longs.map((l) => l[1])), 'ms');
console.log('frame gaps >100ms', P.gaps.length, 'total', sum(P.gaps.map((g) => g[1])), 'ms; max', Math.max(0, ...P.gaps.map((g) => g[1])));
console.log('perf > 1 s', JSON.stringify((perf || []).filter((e) => e[1] > 1000)));
console.log('marks', JSON.stringify(P.marks));
console.log('biggest gaps', JSON.stringify(P.gaps.sort((a, b) => b[1] - a[1]).slice(0, 12)));
if (logs.length) console.log(logs.filter((l) => !/warning/.test(l)).slice(0, 20).join('\n'));
ws.close(); chrome.kill(); server.close();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
