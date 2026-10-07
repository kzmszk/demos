// snap.mjs — headless Chrome (real GPU, WebGPU) screenshots of the viewer.
// node snap.mjs out.jpg "query" [shots.json]   shots: [{name, eval, wait}] evaluated after KYO.ready
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn } from 'node:child_process';
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../public');
const [out, query = '', shotsFile] = process.argv.slice(2);
const W = +(process.env.W || 1600), H = +(process.env.H || 900);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.bin': 'application/octet-stream', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.png': 'image/png', '.hdr': 'application/octet-stream', '.ktx2x': '', '.ktx2': 'image/ktx2', '.wasm': 'application/wasm', '.map': 'application/json' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
  const f = path.join(ROOT, path.normalize(p));
  if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404).end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-length': fs.statSync(f).size });
  fs.createReadStream(f).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'kyo-snap-'));
const chrome = spawn('google-chrome', ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--hide-scrollbars', '--mute-audio',
  `--window-size=${W},${H}`, '--autoplay-policy=no-user-gesture-required', '--enable-unsafe-webgpu', '--enable-features=Vulkan', '--use-vulkan=native', '--ignore-gpu-blocklist', '--enable-gpu', 'about:blank'], { stdio: 'ignore' });
const pf = path.join(profile, 'DevToolsActivePort');
for (let i = 0; i < 100 && !fs.existsSync(pf); i++) await sleep(100);
const port = fs.readFileSync(pf, 'utf8').split('\n')[0];
const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
let seq = 0; const pending = new Map(); const logs = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.type + ': ' + m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 600));
  else if (m.method === 'Log.entryAdded') logs.push('LOG ' + m.params.entry.level + ': ' + m.params.entry.text.slice(0, 600));
  else if (m.method === 'Runtime.exceptionThrown') logs.push('EXC: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 1200)); };
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) logs.push('EVAL EXC: ' + JSON.stringify(r.exceptionDetails).slice(0, 600)); return r.result?.value; };
await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `${base}/index.html?${query}` });
if (process.env.PROBE) { await sleep(1500); console.log('PROBE', JSON.stringify(await ev(`(async()=>{const o={has:!!navigator.gpu, secure:isSecureContext}; try{const a=await navigator.gpu.requestAdapter({powerPreference:'high-performance'}); o.adapter=!!a; if(a){o.feat=[...a.features]; const d=await a.requestDevice(); o.device=!!d;}}catch(e){o.err=String(e)} return o})()`))); }
const t0 = Date.now();
for (;;) { await sleep(300); const r = await ev('window.KYO && window.KYO.ready'); if (r) break; if (Date.now() - t0 > 90000) { console.log('timeout waiting for ready'); break; } }
console.log('ready after', Date.now() - t0, 'ms');
const shots = shotsFile ? JSON.parse(fs.readFileSync(shotsFile, 'utf8')) : [{ name: '' }];
for (const s of shots) {
  if (s.eval) await ev(s.eval);
  await ev(`KYO.settle(${s.settle ?? 1200})`);
  await sleep(s.wait ?? 1500);
  const data = await ev('KYO.capture()');
  const file = s.name ? out.replace(/\.jpg$/, `-${s.name}.jpg`) : out;
  if (data) fs.writeFileSync(file, Buffer.from(data, 'base64')); else console.log('capture failed');
  if (process.env.UI_SHOT) {   // page screenshot (HTML overlay; the WebGPU canvas itself is not composited headless)
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(file.replace(/\.jpg$/, '-ui.png'), Buffer.from(r.data, 'base64'));
  }
  console.log('saved', file, JSON.stringify(await ev('JSON.stringify(KYO.info())')));
}
if (logs.length) console.log(logs.slice(0, 40).join('\n'));
ws.close(); chrome.kill(); server.close();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
