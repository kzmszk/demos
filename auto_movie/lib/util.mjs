// Small shared helpers: filesystem, hashing, logging, process spawning, seeded randomness.
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const sha1 = (s) => createHash('sha1').update(typeof s === 'string' ? s : JSON.stringify(s)).digest('hex');
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const ensureDir = (d) => (fs.mkdirSync(d, { recursive: true }), d);
export const exists = (p) => fs.existsSync(p);
export const readText = (p) => fs.readFileSync(p, 'utf8');
export const writeText = (p, s) => (ensureDir(path.dirname(p)), fs.writeFileSync(p, s), p);
export const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
export const writeJSON = (p, o) => writeText(p, JSON.stringify(o, null, 2) + '\n');
export const round = (x, n = 3) => Math.round(x * 10 ** n) / 10 ** n;
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;

// ---- logging -------------------------------------------------------------------------------
let sink = null; // optional (line) => void, so the web UI can stream the same lines
export const setLogSink = (fn) => { sink = fn; };
const t0 = Date.now();
export function log(tag, ...msg) {
  const s = ((Date.now() - t0) / 1000).toFixed(1).padStart(6);
  const line = `[${s}s] ${tag.padEnd(9)} ${msg.join(' ')}`;
  console.log(line);
  if (sink) sink(line);
}

// ---- deterministic randomness --------------------------------------------------------------
export function rng(seed) {
  let a = typeof seed === 'number' ? seed >>> 0 : parseInt(sha1(String(seed)).slice(0, 8), 16);
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  next.range = (lo, hi) => lo + (hi - lo) * next();
  next.int = (lo, hi) => Math.floor(next.range(lo, hi + 1));
  next.pick = (arr) => arr[Math.floor(next() * arr.length)];
  next.chance = (p) => next() < p;
  next.gauss = () => {
    const u = Math.max(1e-9, next()), v = next();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  return next;
}

// ---- processes -----------------------------------------------------------------------------
/** Run a command, resolve {code, stdout, stderr}. Rejects only when it cannot be spawned (or code!==0 with check). */
export function run(cmd, args = [], opts = {}) {
  const { input, check = false, cwd, env, timeoutMs, onStdout, onStderr } = opts;
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { cwd, env: env ?? process.env, stdio: ['pipe', 'pipe', 'pipe'] });
    const out = [], err = [];
    let timer;
    if (timeoutMs) timer = setTimeout(() => p.kill('SIGKILL'), timeoutMs);
    p.stdout.on('data', (d) => { out.push(d); onStdout?.(d); });
    p.stderr.on('data', (d) => { err.push(d); onStderr?.(d); });
    p.on('error', (e) => { clearTimeout(timer); reject(e); });
    p.on('close', (code) => {
      clearTimeout(timer);
      const r = { code, stdout: Buffer.concat(out).toString('utf8'), stderr: Buffer.concat(err).toString('utf8') };
      if (check && code !== 0) reject(new Error(`${cmd} ${args.join(' ').slice(0, 200)} exited ${code}\n${r.stderr.slice(-1500)}`));
      else resolve(r);
    });
    if (input != null) p.stdin.end(input); else p.stdin.end();
  });
}

/** Run at most `limit` async tasks at once, keep order of results. */
export async function pool(limit, items, fn) {
  const results = new Array(items.length);
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      results[i] = await fn(items[i], i);
    }
  });
  await Promise.all(workers);
  return results;
}

export const fmtTime = (sec) => {
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return `${m}:${s.toFixed(1).padStart(4, '0')}`;
};

/** Escape for HTML text / attribute values. */
export const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
