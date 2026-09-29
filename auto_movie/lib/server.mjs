// Local web UI backend (no dependencies). Jobs are child processes running the same `make` pipeline as the CLI,
// so the UI and the command line always behave identically. Bound to 127.0.0.1 only.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { ROOT, ensureDir, readJSON, writeJSON, writeText, exists, sha1 } from './util.mjs';
import { loadStyles, loadSeries } from './styles.mjs';
import * as voicevox from './tts/voicevox.mjs';
import * as gemini from './tts/gemini.mjs';

const RUNS = path.join(ROOT, 'runs');
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.wav': 'audio/wav', '.md': 'text/markdown; charset=utf-8', '.log': 'text/plain; charset=utf-8' };
const jobs = new Map(); // id → { proc, log: string[], stage, state, listeners:Set }

const json = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(obj)); };
const body = (req) => new Promise((resolve, reject) => { const c = []; req.on('data', (d) => c.push(d)); req.on('end', () => { try { resolve(JSON.parse(Buffer.concat(c).toString('utf8') || '{}')); } catch (e) { reject(e); } }); });

function sendFile(req, res, file) {
  if (!exists(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end('not found'); }
  const st = fs.statSync(file), type = MIME[path.extname(file)] || 'application/octet-stream';
  const range = req.headers.range;
  if (range) {
    const m = range.match(/bytes=(\d*)-(\d*)/);
    const start = m[1] ? +m[1] : 0, end = m[2] ? Math.min(+m[2], st.size - 1) : st.size - 1;
    res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${start}-${end}/${st.size}`, 'Accept-Ranges': 'bytes', 'Content-Length': end - start + 1 });
    return fs.createReadStream(file, { start, end }).pipe(res);
  }
  res.writeHead(200, { 'Content-Type': type, 'Content-Length': st.size, 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-cache' });
  fs.createReadStream(file).pipe(res);
}

function jobInfo(id) {
  const dir = path.join(RUNS, id);
  const j = jobs.get(id);
  const inp = exists(path.join(dir, 'input.json')) ? readJSON(path.join(dir, 'input.json')) : {};
  const summary = exists(path.join(dir, 'summary.json')) ? readJSON(path.join(dir, 'summary.json')) : null;
  const plan = exists(path.join(dir, 'plan.json')) ? readJSON(path.join(dir, 'plan.json')) : null;
  const qa = exists(path.join(dir, 'qa', 'report.json')) ? readJSON(path.join(dir, 'qa', 'report.json')) : null;
  const logFile = path.join(dir, 'make.log');
  const logAge = exists(logFile) ? Date.now() - fs.statSync(logFile).mtimeMs : Infinity;
  const tail = exists(logFile) ? fs.readFileSync(logFile, 'utf8').split('\n') : [];
  const lastStage = [...tail].reverse().map((l) => l.match(/stage\s+▶ (\w+)/)).find(Boolean)?.[1] || null;
  const external = !j && !summary && logAge < 120000; // started from the command line and still writing its log
  const state = j ? j.state : summary ? 'done' : external ? 'running' : exists(path.join(dir, 'video.mp4')) ? 'done' : 'stopped';
  return { id, state, stage: j?.stage || (external ? lastStage : null), external, input: inp, title: plan?.title || summary?.title || null, style: plan?.style || null, summary, qa: qa && { status: qa.status, checks: qa.checks.map(({ id, label, status, detail }) => ({ id, label, status, detail })) }, hasVideo: exists(path.join(dir, 'video.mp4')), mtime: fs.statSync(dir).mtimeMs };
}

function startJob(spec) {
  const id = spec.runId;
  const dir = ensureDir(path.join(RUNS, id));
  const inputs = ensureDir(path.join(dir, 'inputs'));
  const sources = [];
  (spec.sources || []).forEach((s, i) => {
    if (s.url) sources.push(s.url);
    else if (s.text && s.text.trim()) { const f = path.join(inputs, `${String(i + 1).padStart(2, '0')}-${(s.name || 'source').replace(/[^\w.\-぀-ヿ一-鿿]/g, '_')}.md`); writeText(f, s.text); sources.push(f); }
  });
  const args = [path.join(ROOT, 'bin', 'auto-movie.mjs'), 'make', '--theme', spec.theme, '--seconds', String(Math.round(spec.lengthSec)), '--run', id, '--style', spec.style || 'auto', '--tts', spec.tts || 'voicevox', '--quality', spec.quality || 'looks', '--series', spec.series || 'lifehack'];
  if (sources.length) args.push('--sources', ...sources);
  if (spec.force) args.push('--force', spec.force);
  // own process group, so that cancelling also stops the claude / ffmpeg / chrome children
  const proc = spawn(process.execPath, args, { cwd: ROOT, env: process.env, detached: true });
  const job = { proc, log: [], stage: 'starting', state: 'running', listeners: new Set() };
  jobs.set(id, job);
  const push = (chunk) => {
    for (const line of chunk.toString().split('\n')) {
      if (!line.trim()) continue;
      const clean = line.replace(/\x1b\[[0-9;]*m/g, '');
      job.log.push(clean); if (job.log.length > 2000) job.log.shift();
      const m = clean.match(/stage\s+▶ (\w+)/); if (m) job.stage = m[1];
      for (const l of job.listeners) l({ line: clean, stage: job.stage });
    }
  };
  proc.stdout.on('data', push); proc.stderr.on('data', push);
  proc.on('close', (code) => {
    job.state = code === 0 ? 'done' : 'failed'; job.stage = code === 0 ? 'done' : job.stage;
    for (const l of job.listeners) l({ line: `— finished (exit ${code})`, stage: job.stage, end: true, state: job.state });
    fs.appendFileSync(path.join(dir, 'make.log'), job.log.join('\n') + '\n');
  });
  return id;
}

export async function startApp({ port = 8420 } = {}) {
  ensureDir(RUNS);
  const uiDir = path.join(ROOT, 'ui');
  const server = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://x');
      const p = decodeURIComponent(url.pathname);
      if (p === '/' || p === '/index.html') return sendFile(req, res, path.join(uiDir, 'index.html'));
      if (p.startsWith('/ui/')) return sendFile(req, res, path.join(uiDir, p.slice(4)));
      if (p === '/api/config') {
        const order = ['podcast-duo', 'monologue', 'entertainment'];
        const styles = Object.values(loadStyles()).sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)).map(({ id, name, summary }) => ({ id, name, summary }));
        const series = loadSeries('lifehack');
        return json(res, 200, { styles, series: { id: series.id, name: series.name, tagline: series.tagline, cast: Object.values(series.cast).map((c) => ({ name: c.name, role: c.role })) }, tts: { voicevox: await voicevox.isUp(), gemini: gemini.available() } });
      }
      if (p === '/api/voicevox/start' && req.method === 'POST') { voicevox.ensureReady().catch(() => {}); return json(res, 200, { ok: true }); }
      if (p === '/api/jobs' && req.method === 'GET') {
        const ids = exists(RUNS) ? fs.readdirSync(RUNS).filter((d) => exists(path.join(RUNS, d, 'input.json'))) : [];
        return json(res, 200, ids.map(jobInfo).sort((a, b) => b.mtime - a.mtime));
      }
      if (p === '/api/jobs' && req.method === 'POST') {
        const spec = await body(req);
        if (!spec.theme || !String(spec.theme).trim()) return json(res, 400, { error: 'テーマを入力してください' });
        spec.lengthSec = Math.max(30, Math.min(600, +spec.lengthSec || 180));
        spec.runId = `${new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')}-${sha1(spec.theme).slice(0, 4)}`;
        startJob(spec);
        return json(res, 200, { id: spec.runId });
      }
      let m = p.match(/^\/api\/jobs\/([\w-]+)$/);
      if (m) { const info = jobInfo(m[1]); const j = jobs.get(m[1]); return json(res, 200, { ...info, log: j ? j.log.slice(-200) : (exists(path.join(RUNS, m[1], 'make.log')) ? fs.readFileSync(path.join(RUNS, m[1], 'make.log'), 'utf8').split('\n').slice(-200) : []) }); }
      m = p.match(/^\/api\/jobs\/([\w-]+)\/events$/);
      if (m) {
        const j = jobs.get(m[1]);
        res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
        if (!j) { res.write(`data: ${JSON.stringify({ end: true, line: '' })}\n\n`); return res.end(); }
        for (const line of j.log.slice(-100)) res.write(`data: ${JSON.stringify({ line, stage: j.stage })}\n\n`);
        const l = (ev) => res.write(`data: ${JSON.stringify(ev)}\n\n`);
        j.listeners.add(l); req.on('close', () => j.listeners.delete(l));
        if (j.state !== 'running') { res.write(`data: ${JSON.stringify({ line: '— finished', end: true, state: j.state })}\n\n`); }
        return;
      }
      m = p.match(/^\/api\/jobs\/([\w-]+)\/cancel$/);
      if (m && req.method === 'POST') { const j = jobs.get(m[1]); if (j) { try { process.kill(-j.proc.pid, 'SIGTERM'); } catch { j.proc.kill('SIGTERM'); } } return json(res, 200, { ok: true }); }
      m = p.match(/^\/runs\/([\w-]+)\/(.+)$/);
      if (m) {
        const f = path.normalize(path.join(RUNS, m[1], m[2]));
        if (!f.startsWith(path.join(RUNS, m[1]))) { res.writeHead(403); return res.end(); }
        return sendFile(req, res, f);
      }
      res.writeHead(404); res.end('not found');
    } catch (e) { json(res, 500, { error: e.message }); }
  });
  await new Promise((r) => server.listen(port, '127.0.0.1', r));
  console.log(`auto_movie UI → http://127.0.0.1:${port}/`);
  return server;
}
