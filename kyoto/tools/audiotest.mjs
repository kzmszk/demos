// audiotest.mjs — headless Chrome (NO GPU) runs public/audiotest.html's offline tests (window.AT.runAll), the WAVs they render are
// written to kyoto-assets/build/audio/, and this script analyses them: levels, the pitch of the piano's keys (FFT peak and
// autocorrelation), the tempo and onsets of the Aria, the bell's decay.
//   node audiotest.mjs [only,only,...]      only: pitch, grains, walk, water, bells, movements  (the Aria always)
//   node audiotest.mjs --analyse-only       re-analyse the WAVs and report.json already there
import fs from 'node:fs'; import os from 'node:os'; import path from 'node:path'; import http from 'node:http';
import { spawn } from 'node:child_process';
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../public');
const OUT = '/home/kazu/work/kyoto-assets/build/audio';
fs.mkdirSync(OUT, { recursive: true });
const args = process.argv.slice(2), analyseOnly = args.includes('--analyse-only'), only = args.filter((a) => !a.startsWith('--'))[0]?.split(',');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------------------------------------------------------------- the run */
let R;
if (analyseOnly) R = JSON.parse(fs.readFileSync(path.join(OUT, 'report.json'), 'utf8'));
else {
  const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.map': 'application/json' };
  const server = http.createServer((req, res) => {
    const u = new URL(req.url, 'http://x'), p = decodeURIComponent(u.pathname);
    if (req.method === 'POST' && p.startsWith('/__save/')) {
      const name = path.basename(p); const chunks = []; req.on('data', (c) => chunks.push(c)); req.on('end', () => { fs.writeFileSync(path.join(OUT, name), Buffer.concat(chunks)); res.writeHead(200).end('ok'); }); return;
    }
    if (p === '/favicon.ico') { res.writeHead(204).end(); return; }
    const f = path.join(ROOT, path.normalize(p === '/' ? '/audiotest.html' : p));
    if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404).end(); return; }
    res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'content-length': fs.statSync(f).size });
    fs.createReadStream(f).pipe(res);
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'kyo-audio-'));
  const chrome = spawn('google-chrome', ['--headless=new', '--disable-gpu', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--mute-audio',
    '--autoplay-policy=no-user-gesture-required', 'about:blank'], { stdio: 'ignore' });
  const pf = path.join(profile, 'DevToolsActivePort');
  for (let i = 0; i < 100 && !fs.existsSync(pf); i++) await sleep(100);
  const port = fs.readFileSync(pf, 'utf8').split('\n')[0];
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
  await new Promise((r, j) => ((ws.onopen = r), (ws.onerror = j)));
  let seq = 0; const pending = new Map(); const logs = [];
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
    else if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.type + ': ' + m.params.args.map((a) => a.value ?? a.description).join(' ').slice(0, 400));
    else if (m.method === 'Log.entryAdded') logs.push('LOG ' + m.params.entry.level + ': ' + m.params.entry.text.slice(0, 400));
    else if (m.method === 'Runtime.exceptionThrown') logs.push('EXC: ' + JSON.stringify(m.params.exceptionDetails).slice(0, 1200)); };
  const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
  const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) logs.push('EVAL EXC: ' + JSON.stringify(r.exceptionDetails).slice(0, 1500)); return r.result?.value; };
  await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable');
  await send('Page.navigate', { url: `${base}/audiotest.html` });
  for (let i = 0; i < 100; i++) { await sleep(100); if (await ev('!!window.AT')) break; }
  // a progress printer
  const prog = setInterval(async () => { try { const t = await ev(`document.getElementById('testst').textContent`); if (t) process.stdout.write('\r' + t.padEnd(40)); } catch (e) { /* */ } }, 700);
  const t0 = Date.now();
  if (args.includes('--ui')) {
    const U = await ev(`AT.ui().then((r) => JSON.stringify(r))`);
    console.log(U ? JSON.stringify(JSON.parse(U), null, 1) : 'no result'); console.log('console:', logs.filter((l) => !/now playing/.test(l)).slice(0, 20).join('\n') || 'no errors'); ws.close(); chrome.kill(); server.close(); process.exit(0);
  }
  if (args.includes('--live')) {      // the real-time engine, a few seconds, timings
    const L = await ev(`AT.live(${+(args.find((x) => x.startsWith('--secs='))?.slice(7)) || 16}).then((r) => JSON.stringify(r))`);
    console.log(L ? JSON.stringify(JSON.parse(L), null, 1).slice(0, 6000) : 'no result'); console.log('console:', logs.slice(0, 20).join('\n')); ws.close(); chrome.kill(); server.close(); process.exit(0);
  }
  const json = await ev(`AT.runAll(${only ? JSON.stringify(only) : 'undefined'}).then((r) => JSON.stringify(r))`);
  clearInterval(prog);
  console.log('\nruns took', ((Date.now() - t0) / 1000).toFixed(1), 's');
  if (!json) { console.log('no result'); console.log(logs.join('\n')); process.exit(1); }
  R = JSON.parse(json); fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(R));
  const bad = logs.filter((l) => /error|exc|reject|warn/i.test(l) && !/now playing/.test(l));
  console.log('console problems:', bad.length ? '\n' + bad.slice(0, 20).join('\n') : 'none');
  ws.close(); chrome.kill(); server.close();
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* */ }
}

/* ---------------------------------------------------------------- the analysis */
function readWav(file) {
  const b = fs.readFileSync(file), nc = b.readUInt16LE(22), rate = b.readUInt32LE(24), n = (b.length - 44) / (2 * nc), ch = Array.from({ length: nc }, () => new Float32Array(n));
  for (let i = 0, p = 44; i < n; i++) for (let c = 0; c < nc; c++, p += 2) ch[c][i] = b.readInt16LE(p) / 32768;
  return { rate, n, ch, mono: Float32Array.from({ length: n }, (_, i) => ch.reduce((s, c) => s + c[i], 0) / nc) };
}
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let len = 2; len <= n; len <<= 1) {
    const a = (-2 * Math.PI) / len, wr = Math.cos(a), wi = Math.sin(a);
    for (let i = 0; i < n; i += len) { let cr = 1, ci = 0; for (let k = 0; k < len / 2; k++) { const ur = re[i + k], ui = im[i + k], vr = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci, vi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr; re[i + k] = ur + vr; im[i + k] = ui + vi; re[i + k + len / 2] = ur - vr; im[i + k + len / 2] = ui - vi; const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t; } }
  }
}
const mag = (x, rate, f0, f1, N = 1 << 18) => {            // spectrum of a Hann-windowed segment; returns {freqs, mags} within [f0, f1]
  const re = new Float64Array(N), im = new Float64Array(N), n = Math.min(x.length, N);
  for (let i = 0; i < n; i++) re[i] = x[i] * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1)));
  fft(re, im); const df = rate / N, out = { f: [], m: [] };
  for (let k = Math.floor(f0 / df); k <= Math.ceil(f1 / df); k++) { out.f.push(k * df); out.m.push(Math.hypot(re[k], im[k])); }
  return out;
};
function peakIn(sp) { let bi = 0; for (let i = 1; i < sp.m.length - 1; i++) if (sp.m[i] > sp.m[bi]) bi = i; if (bi === 0 || bi === sp.m.length - 1) return sp.f[bi]; const a = Math.log(sp.m[bi - 1]), b = Math.log(sp.m[bi]), c = Math.log(sp.m[bi + 1]); return sp.f[bi] + ((a - c) / (2 * (a - 2 * b + c))) * (sp.f[1] - sp.f[0]); }
const cents = (f, ref) => 1200 * Math.log2(f / ref);
function autocorrPitch(x, rate, f0) {
  const lo = Math.floor(rate / (f0 * 1.06)), hi = Math.ceil(rate / (f0 / 1.06)), N = x.length - hi - 1; let best = -1, bl = lo; const r = {};
  const ac = (l) => { let s = 0, e1 = 0, e2 = 0; for (let i = 0; i < N; i++) { s += x[i] * x[i + l]; e1 += x[i] * x[i]; e2 += x[i + l] * x[i + l]; } return s / Math.sqrt(e1 * e2 + 1e-12); };
  for (let l = lo - 1; l <= hi + 1; l++) r[l] = ac(l);
  for (let l = lo; l <= hi; l++) if (r[l] > best) { best = r[l]; bl = l; }
  const a = r[bl - 1], b = r[bl], c = r[bl + 1], d = (a - c) / (2 * (a - 2 * b + c)); return { f: rate / (bl + d), r: best };
}
const hzOf = (m) => 440 * Math.pow(2, (m - 69) / 12);
const db = (x) => (20 * Math.log10(Math.max(x, 1e-9))).toFixed(1);
const pad = (s, n) => String(s).padEnd(n), lpad = (s, n) => String(s).padStart(n);

console.log('\n=== kit (the piano keys and every grain, rendered in a worker) ===');
console.log(JSON.stringify(R.kit));

console.log('\n=== levels ===');
const aria = R.aria;
console.log('Aria, first 4 bars, whole chain (dBFS):  all', JSON.stringify(aria.stats), ' per bar:', aria.bars.map((s) => `${s.rms}/${s.peak}`).join('  '), '  (rms/peak)');
console.log('trim', aria.trim.toFixed(3), ' P', aria.P.toFixed(3), ' bpm', aria.bpm, ' movement length', aria.len.toFixed(1), 's');
for (const [k, v] of Object.entries(R.grains || {})) console.log('grain', pad(k, 8), 'peak', lpad(v.stats.peak, 6), 'rms', lpad(v.stats.rms, 6), ' per variant peak/rms:', v.peaks.map((s) => s.peak + '/' + s.rms).join('  '));
for (const [k, v] of Object.entries(R.walk || {})) console.log('walk ', pad(k, 14), 'peak', lpad(v.stats.peak, 6), 'rms', lpad(v.stats.rms, 6));
for (const [k, v] of Object.entries(R.water || {})) console.log('water', pad(k, 12), 'peak', lpad(v.stats.peak, 6), 'rms', lpad(v.stats.rms, 6));
for (const [k, v] of Object.entries(R.bells || {})) if (v.stats) console.log('bell ', pad(k, 12), 'peak', lpad(v.stats.peak, 6), 'rms', lpad(v.stats.rms, 6));
if (R.bells && R.bells.log) console.log('bell scheduler (420 s, three bells at 200/520/780 m): strikes', JSON.stringify(R.bells.log.map((s) => `${s.at}s d${s.dist} id${s.id}`)));
if (R.movements && R.movements.length) {
  console.log('\nmovement (16 s from the middle, music only): rms / peak dBFS, trim, P');
  console.log(R.movements.map((m) => `${pad(m.id, 13)} ${lpad(m.bpm, 6)}bpm  rms ${lpad(m.stats.rms, 6)}  peak ${lpad(m.stats.peak, 6)}  trim ${m.trim}  P ${m.P}`).join('\n'));
  const r = R.movements.map((m) => m.stats.rms), mean = r.reduce((a, b) => a + b, 0) / r.length;
  console.log('rms spread: min', Math.min(...r), 'max', Math.max(...r), 'mean', mean.toFixed(1));
}

if (R.transition) {
  console.log('\n=== the end of the Aria into Variation 1 ===');
  const tl = R.transition.timeline, w = R.transition.rmsPerQuarterSecond;
  console.log('timeline (audio clock s):', tl.map((t) => `movement ${t.mi}: ${t.t0.toFixed(2)} .. ${t.t1.toFixed(2)}`).join('  |  '), ' -> gap', (tl[1].t0 - tl[0].t1).toFixed(2), 's between the end of one and the first sound of the next');
  const quiet = w.map((x, i) => [i * 0.25, x]).filter(([t, x]) => t > tl[0].t1 - 1 && x < -60); console.log('quarter-seconds below -60 dBFS around the gap:', quiet.length ? `${quiet[0][0]} s .. ${quiet[quiet.length - 1][0] + 0.25} s` : 'none');
  console.log('label (nowPlaying) changes:', JSON.stringify(R.transition.nowPlaying), ' da capo wraps:', JSON.stringify(R.wrap && R.wrap.nowPlaying));
  console.log('piano in the wooden hall (Sanjusangendo) vs outdoors, aria 19 s:', JSON.stringify(R.hall.stats), 'vs', JSON.stringify(R.hall.outdoors));
}
if (R.pitch) {
  console.log('\n=== pitch of the keys (dry; FFT peak of the lowest strong partial, and autocorrelation) ===');
  const w = readWav(path.join(OUT, 'pitch.wav')), rate = w.rate; let worst = 0;
  for (const [t, m] of R.pitch.events) {
    const f0 = hzOf(m), i0 = Math.floor((t + 0.12) * rate), seg = w.mono.subarray(i0, i0 + Math.floor(1.0 * rate));
    // partial n=1, and for the weak bass also n=2, 3: report the first partial that stands above -40 dB of the strongest
    const sp = mag(seg, rate, f0 * 0.5, f0 * 4.5); const mx = Math.max(...sp.m);
    const parts = []; for (let n = 1; n <= 3; n++) { const s2 = mag(seg, rate, f0 * n * 0.97, f0 * n * 1.035 * (1 + 0.0004 * n * n)); const pk = Math.max(...s2.m); parts.push({ n, f: peakIn(s2), lvl: 20 * Math.log10(pk / mx) }); }
    const use = parts.find((p) => p.lvl > -25) || parts[0];
    const err = cents(use.f / use.n, f0), ac = autocorrPitch(w.mono.subarray(i0, i0 + Math.floor(0.4 * rate)), rate, f0);
    worst = Math.max(worst, Math.abs(err));
    console.log(`m${lpad(m, 3)} ${lpad(f0.toFixed(2), 8)} Hz  partial ${use.n}: ${lpad((use.f / use.n).toFixed(2), 8)} Hz  ${lpad(err.toFixed(1), 6)} cents   autocorr ${lpad(ac.f.toFixed(2), 8)} Hz ${lpad(cents(ac.f, f0).toFixed(1), 6)} cents (r ${ac.r.toFixed(2)})`);
  }
  console.log('worst FFT error', worst.toFixed(1), 'cents (a piano string is a little stiff: partials run slightly sharp)');
}

console.log('\n=== tempo and onsets of the Aria (first 4 bars) ===');
{
  const w = readWav(path.join(OUT, 'aria-4bars.wav')), rate = w.rate, ev = aria.events;
  // the audio's onset strength: the energy rise in 2-8 kHz and 150-1000 Hz bands, 10 ms hop
  const hop = Math.floor(0.005 * rate), win = 1024, env = [];
  for (let i = 0; i + win < w.n; i += hop) { const re = new Float64Array(win), im = new Float64Array(win); for (let k = 0; k < win; k++) re[k] = w.mono[i + k] * (0.5 - 0.5 * Math.cos((2 * Math.PI * k) / (win - 1))); fft(re, im); let e = 0; for (let k = 3; k < 160; k++) e += Math.hypot(re[k], im[k]); env.push(e); }
  const flux = env.map((e, i) => Math.max(0, Math.log(e + 1e-6) - Math.log((env[i - 1] ?? e) + 1e-6)));
  const bar = (b) => ev.filter((e) => Math.abs(e[4] - b) < 0.01);
  const downs = [0, 3, 6, 9, 12].map((b) => bar(b)).filter((a) => a.length).map((a) => a[0][0]);
  console.log('scheduled downbeats (s):', downs.map((x) => x.toFixed(3)).join(' '), ' -> bar lengths', downs.slice(1).map((x, i) => (x - downs[i]).toFixed(3)).join(' '), ' (nominal 4.500 at 40 bpm; the phrase shaping makes the 4th bar broader)');
  const secPerBeat = (downs[4] - downs[0]) / 12; console.log('4 bars = 12 beats in', (downs[4] - downs[0]).toFixed(3), 's  ->', (60 / secPerBeat).toFixed(2), 'bpm (nominal', aria.bpm + ')');
  // do the scheduled onsets show in the audio?
  let hit = 0, tot = 0; const offs = [];
  for (const e of ev) { if (e[0] > 22) continue; tot++; const c = Math.round(e[0] / 0.005); let best = 0, bj = c; for (let j = c - 8; j <= c + 8; j++) if (flux[j] > best) { best = flux[j]; bj = j; } if (best > 0.15) { hit++; offs.push((bj * 0.005 - e[0]) * 1000); } }
  offs.sort((a, b) => a - b);
  console.log(`scheduled notes with an onset within ±40 ms in the audio: ${hit}/${tot};  median offset ${offs[Math.floor(offs.length / 2)]?.toFixed(1)} ms`);
  const first = ev[0]; console.log('first note scheduled at', first[0].toFixed(3), 's, m', first[1]);
}

if (R.grains && R.grains.bell) {
  console.log('\n=== the bell (near, 60 m): spectrum peaks of the first 3 s and decay of its rms ===');
  const w = readWav(path.join(OUT, 'bell-near.wav')), rate = w.rate;
  const seg = w.mono.subarray(Math.floor(1 * rate), Math.floor(5 * rate)); const sp = mag(seg, rate, 40, 1500, 1 << 18);
  const pk = []; for (let i = 2; i < sp.m.length - 2; i++) if (sp.m[i] > sp.m[i - 1] && sp.m[i] > sp.m[i + 1] && sp.m[i] > sp.m[i - 2] && sp.m[i] > sp.m[i + 2]) pk.push([sp.f[i], sp.m[i]]);
  const mx = Math.max(...pk.map((p) => p[1])); pk.sort((a, b) => b[1] - a[1]);
  console.log('strongest partials (Hz, dB):', pk.filter((p) => p[1] > mx * 0.03).slice(0, 12).sort((a, b) => a[0] - b[0]).map((p) => `${p[0].toFixed(1)} ${(20 * Math.log10(p[1] / mx)).toFixed(0)}`).join('  |  '));
  const dec = [0.2, 1, 3, 6, 10, 15, 20, 25, 30, 35, 40].map((t) => { const i0 = Math.floor(t * rate); let e = 0; const n = Math.floor(0.5 * rate); for (let i = 0; i < n; i++) e += w.mono[i0 + i] ** 2; return `${t}s:${db(Math.sqrt(e / n))}`; });
  console.log('rms decay (dBFS):', dec.join('  '));
}
