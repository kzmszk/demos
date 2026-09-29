// The gallery is static assets; this Worker only sees /api/* (assets.run_worker_first in wrangler.jsonc).
//
// /api/sketch — the sketchbook's try page ("おためし"). A visitor who knows the passphrase asks for an
// illustration; the request becomes an `illustration.svg` job on hermes-llm-jobs (service binding
// LLM_JOBS, app key in the LLM_JOBS_API_KEY secret), and a runner on the owner's PC draws it with Opus.
//   POST /api/sketch       {subject, passphrase, variant?} → {id, status}
//   GET  /api/sketch/:id   → {status: queued|drawing|done|failed, svg?, memo?}
// Secrets: SKETCH_PASSPHRASE, LLM_JOBS_API_KEY. Local dev may set SKETCH_MOCK=1 to fake the job service.
//
// /api/movie — auto_movie's "つくる". Same shape: a visitor with the passphrase asks for a video (a theme, 2 or 3 minutes, optional notes);
// it becomes a `video.generate` job (its own app key, MOVIE_JOBS_API_KEY, and daily allowance) and the owner's PC makes it in ten minutes or so.
//   POST /api/movie        {theme, minutes, notes?, passphrase, variant?} → {id, status}
//   GET  /api/movie/:id    → {status: queued|making|done|failed, movie?: {title, subtitle, seconds, chapters, video, poster, …}}
// Secrets: MOVIE_JOBS_API_KEY, MOVIE_PASSPHRASE (falls back to SKETCH_PASSPHRASE). Local dev may set MOVIE_MOCK=1.
//
// /media/movies/<id>/video.mp4 | poster.webp — the finished files, read from the R2 bucket bound as MEDIA (private, no public URL) with byte
// ranges, so the page can seek. Only those two file names under movies/<id>/ are served.

const JOBS = 'https://hermes-llm-jobs.kazumasa.workers.dev';
const STATUS = { pending: 'queued', running: 'drawing', completed: 'done', failed: 'failed' };

class ApiError extends Error {
  constructor(status, code) { super(code); this.status = status; this.code = code; }
}
const fail = (status, code) => { throw new ApiError(status, code); };
const reply = (value, status = 200) => new Response(JSON.stringify(value), {
  status,
  headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
});

async function sha256(text) {
  const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)));
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}
async function sameSecret(given, expected) {
  if (typeof given !== 'string' || !expected) return false;
  const norm = (s) => s.normalize('NFKC').trim().toLowerCase();
  const [a, b] = await Promise.all([sha256(norm(given)), sha256(norm(expected))]);
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
async function allowed(limiter, key) {
  if (!limiter) return true;                 // no binding in some local setups
  const { success } = await limiter.limit({ key });
  return success;
}
function cleanSubject(raw) {
  if (typeof raw !== 'string') return null;
  const s = raw.normalize('NFKC').replace(/\s+/g, ' ').trim();
  if (!s || s.length > 60 || /[\u0000-\u001f\u007f<>{}`\\]/.test(s)) return null;
  return s;
}

async function jobs(env, key, path, body) {
  const r = await env.LLM_JOBS.fetch(JOBS + path, {
    method: body === undefined ? 'GET' : 'POST',
    redirect: 'manual',
    signal: AbortSignal.timeout(10000),
    headers: { Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  let data = null;
  try { data = await r.json(); } catch { /* keep null */ }
  return { status: r.status, data };
}

async function submit(request, env) {
  const url = new URL(request.url);
  if (request.headers.get('origin') !== url.origin) fail(403, 'origin');
  if (!request.headers.get('content-type')?.startsWith('application/json')) fail(415, 'json');
  const text = await request.text();
  if (text.length > 2048) fail(413, 'too_large');
  let body;
  try { body = JSON.parse(text); } catch { fail(400, 'json'); }
  const ip = request.headers.get('cf-connecting-ip') || 'local';

  if (!(await sameSecret(body?.passphrase, env.SKETCH_PASSPHRASE))) {
    if (!(await allowed(env.SKETCH_GUESS, ip))) fail(429, 'slow_down');
    fail(403, 'passphrase');
  }
  const subject = cleanSubject(body.subject);
  if (!subject) fail(400, 'subject');
  const variant = Number.isInteger(body.variant) ? Math.min(2, Math.max(0, body.variant)) : 0;
  if (!(await allowed(env.SKETCH_SUBMIT, ip))) fail(429, 'slow_down');

  if (env.SKETCH_MOCK === '1') return reply({ id: mockId(subject), status: 'queued' }, 201);

  // Same subject, same variant → same job, so a popular subject is drawn once.
  const idempotencyKey = 'sk1-' + (await sha256(subject + '|' + variant)).slice(0, 48);
  const r = await jobs(env, env.LLM_JOBS_API_KEY, '/api/jobs', { type: 'illustration.svg', version: 1, idempotencyKey, payload: { subject } });
  if (r.status === 429) fail(429, r.data?.error?.code === 'daily_limit' ? 'daily_limit' : 'slow_down');
  if (r.status !== 200 && r.status !== 201) fail(502, 'jobs_unavailable');
  return reply({ id: r.data.id, status: STATUS[r.data.status] || 'queued' }, r.status);
}

async function poll(request, env, id) {
  const ip = request.headers.get('cf-connecting-ip') || 'local';
  if (!(await allowed(env.SKETCH_POLL, ip))) fail(429, 'slow_down');
  if (env.SKETCH_MOCK === '1') return reply(mockPoll(id));
  const r = await jobs(env, env.LLM_JOBS_API_KEY, '/api/jobs/' + id);
  if (r.status === 404) fail(404, 'missing');
  if (r.status !== 200) fail(502, 'jobs_unavailable');
  const out = { status: STATUS[r.data.status] || 'queued' };
  if (out.status === 'done' && r.data.result?.svg) {
    out.svg = r.data.result.svg;
    if (r.data.result.memo) out.memo = r.data.result.memo;
  }
  return reply(out);
}

/* ---------- videos ---------- */
const MOVIE_STATUS = { pending: 'queued', running: 'making', completed: 'done', failed: 'failed' };
function cleanNotes(raw) {
  if (raw == null || raw === '') return '';
  if (typeof raw !== 'string') return null;
  const s = raw.normalize('NFKC').replace(/\r\n?/g, '\n').replace(/[^\S\n]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
  if (s.length > 1500 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(s)) return null;
  return s;
}
/** What the page needs from a finished job: the job's own numbers, and the two files as same-origin paths. */
const movieOf = (x) => ({
  title: x.title, subtitle: x.subtitle, seconds: x.seconds, width: x.width, height: x.height, style: x.style,
  chapters: x.chapters, bytes: x.bytes, qa: x.qa, video: '/media/' + x.video, poster: '/media/' + x.poster,
});

async function submitMovie(request, env) {
  const url = new URL(request.url);
  if (request.headers.get('origin') !== url.origin) fail(403, 'origin');
  if (!request.headers.get('content-type')?.startsWith('application/json')) fail(415, 'json');
  const text = await request.text();
  if (text.length > 6000) fail(413, 'too_large');
  let body;
  try { body = JSON.parse(text); } catch { fail(400, 'json'); }
  const ip = request.headers.get('cf-connecting-ip') || 'local';

  if (!(await sameSecret(body?.passphrase, env.MOVIE_PASSPHRASE || env.SKETCH_PASSPHRASE))) {
    if (!(await allowed(env.MOVIE_GUESS, ip))) fail(429, 'slow_down');
    fail(403, 'passphrase');
  }
  const theme = cleanSubject(body.theme);
  if (!theme) fail(400, 'theme');
  const minutes = body.minutes;
  if (minutes !== 2 && minutes !== 3) fail(400, 'minutes');
  const notes = cleanNotes(body.notes);
  if (notes === null) fail(400, 'notes');
  const variant = Number.isInteger(body.variant) ? Math.min(2, Math.max(0, body.variant)) : 0;
  if (!(await allowed(env.MOVIE_SUBMIT, ip))) fail(429, 'slow_down');

  if (env.MOVIE_MOCK === '1') return reply({ id: mockMovieId(theme), status: 'queued' }, 201);

  // Same theme, length, notes and variant → the same job, so a popular request is made once (and costs no more of the daily allowance).
  const idempotencyKey = 'mv1-' + (await sha256(JSON.stringify([theme, minutes, notes, variant]))).slice(0, 48);
  const r = await jobs(env, env.MOVIE_JOBS_API_KEY, '/api/jobs', { type: 'video.generate', version: 1, idempotencyKey, payload: notes ? { theme, minutes, notes } : { theme, minutes } });
  if (r.status === 429) fail(429, r.data?.error?.code === 'daily_limit' ? 'daily_limit' : 'slow_down');
  if (r.status !== 200 && r.status !== 201) fail(502, 'jobs_unavailable');
  return reply({ id: r.data.id, status: MOVIE_STATUS[r.data.status] || 'queued' }, r.status);
}

async function pollMovie(request, env, id) {
  const ip = request.headers.get('cf-connecting-ip') || 'local';
  if (!(await allowed(env.MOVIE_POLL, ip))) fail(429, 'slow_down');
  if (env.MOVIE_MOCK === '1') return reply(mockMoviePoll(id));
  const r = await jobs(env, env.MOVIE_JOBS_API_KEY, '/api/jobs/' + id);
  if (r.status === 404) fail(404, 'missing');
  if (r.status !== 200) fail(502, 'jobs_unavailable');
  const out = { status: MOVIE_STATUS[r.data.status] || 'queued' };
  if (out.status === 'done' && r.data.result?.video) out.movie = movieOf(r.data.result);
  return reply(out);
}

const MEDIA_KEY = /^movies\/[A-Za-z0-9][A-Za-z0-9-]{0,63}\/(video\.mp4|poster\.webp)$/;
const MEDIA_TYPE = { 'video.mp4': 'video/mp4', 'poster.webp': 'image/webp' };

/** The one range a client asked for ("bytes=a-b", "bytes=a-", "bytes=-n"), resolved against the size; null = send everything, 'bad' = unsatisfiable. */
function wantedRange(header, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(header || '');
  if (!m || (m[1] === '' && m[2] === '')) return null;
  if (m[1] === '') { const n = Math.min(+m[2], size); return n ? { offset: size - n, length: n } : 'bad'; }
  const offset = +m[1];
  if (offset >= size) return 'bad';
  const end = m[2] === '' ? size - 1 : Math.min(+m[2], size - 1);
  return end < offset ? 'bad' : { offset, length: end - offset + 1 };
}

async function media(request, env) {
  if (request.method !== 'GET' && request.method !== 'HEAD') fail(405, 'method');
  const url = new URL(request.url);
  let key;
  try { key = decodeURIComponent(url.pathname.slice('/media/'.length)); } catch { fail(404, 'not_found'); }
  if (!MEDIA_KEY.test(key) || !env.MEDIA) fail(404, 'not_found');
  const name = key.split('/').pop();
  const head = request.method === 'HEAD';
  const asked = request.headers.get('range');
  const single = /^bytes=\d*-\d*$/.test(asked || '');       // a list of ranges is not supported: it is answered with the whole file
  const obj = head ? await env.MEDIA.head(key) : await env.MEDIA.get(key, { range: single ? request.headers : undefined, onlyIf: request.headers });
  if (!obj) fail(404, 'not_found');
  const headers = new Headers({
    'Content-Type': MEDIA_TYPE[name], 'Accept-Ranges': 'bytes', ETag: obj.httpEtag, 'Cache-Control': 'public, max-age=86400',
    'X-Content-Type-Options': 'nosniff', 'Cross-Origin-Resource-Policy': 'same-origin',
  });
  if (url.searchParams.has('download')) headers.set('Content-Disposition', `attachment; filename="auto_movie-${key.split('/')[1]}.${name.split('.')[1]}"`);
  if (head) { headers.set('Content-Length', String(obj.size)); return new Response(null, { headers }); }
  if (!obj.body) return new Response(null, { status: request.headers.has('if-none-match') || request.headers.has('if-modified-since') ? 304 : 412, headers });
  const want = single ? wantedRange(asked, obj.size) : null;
  if (want === 'bad') {
    await obj.body.cancel();
    headers.set('Content-Range', `bytes */${obj.size}`);
    return new Response(null, { status: 416, headers });
  }
  if (want) {
    // Safari and Chrome both want a 206 with Content-Range for every range request, even one that spans the whole file
    headers.set('Content-Range', `bytes ${want.offset}-${want.offset + want.length - 1}/${obj.size}`);
    headers.set('Content-Length', String(want.length));
    return new Response(obj.body, { status: 206, headers });
  }
  headers.set('Content-Length', String(obj.size));
  return new Response(obj.body, { headers });
}

/* ---------- local dev only: a fake job service (SKETCH_MOCK=1 in .dev.vars) ---------- */
const MOCK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><defs><filter id="wob" x="-6%" y="-6%" width="112%" height="112%"><feTurbulence type="fractalNoise" baseFrequency="0.03 0.037" numOctaves="2" seed="2" result="n" /><feDisplacementMap in="SourceGraphic" in2="n" scale="2.8" xChannelSelector="R" yChannelSelector="G" /></filter></defs><g filter="url(#wob)" fill="none" stroke="#3d3d3d" stroke-linecap="round" stroke-linejoin="round"><path fill="#fff176" stroke="none" style="mix-blend-mode:multiply" d="M150 118 C196 92 262 106 276 160 C290 214 246 262 190 258 C134 254 104 206 116 164 C122 142 132 128 150 118 Z" /><path stroke-width="1.7" d="M138 176 C132 132 168 104 206 104 C246 104 274 134 270 176" /><path stroke-width="1.7" d="M140 172 C138 214 164 250 204 252 C244 254 270 222 268 176" /><path stroke-width="1.2" d="M178 186 l1 1 M232 184 l1 1" /><path stroke-width="1.2" d="M198 214 C204 218 212 218 218 213" /><path stroke-width="1.7" d="M150 250 C120 262 102 290 96 330 M258 250 C288 262 306 290 312 330" /><path stroke-width="1" stroke-opacity=".42" d="M300 90 l0 14 M293 97 l14 0" /><path stroke="#d64545" stroke-width="1.2" d="M160 206 l4 -5 M166 208 l4 -5 M236 205 l4 -5 M242 207 l4 -5" /></g></svg>';
function mockId(subject) {
  return 'mock-' + Date.now().toString(36) + '-' + [...subject].length;
}
function mockPoll(id) {
  const born = parseInt(String(id).split('-')[1] || '0', 36);
  const age = (Date.now() - born) / 1000;
  if (!born) return { status: 'failed' };
  if (age < 8) return { status: 'queued' };
  if (age < 16) return { status: 'drawing' };
  return { status: 'done', svg: MOCK_SVG, memo: '設計：（開発用のダミー）特徴／誇張と省略／場面／トリミング' };
}

function mockMovieId(theme) {
  return 'mock-' + Date.now().toString(36) + '-' + [...theme].length;
}
function mockMoviePoll(id) {
  const born = parseInt(String(id).split('-')[1] || '0', 36);
  const age = (Date.now() - born) / 1000;
  if (!born) return { status: 'failed' };
  if (age < 6) return { status: 'queued' };
  if (age < 20) return { status: 'making' };
  return { status: 'done', movie: {
    title: '開発用のダミー', subtitle: '本物の動画ではありません', seconds: 180, width: 1920, height: 1080, style: 'podcast-duo', bytes: 37977659,
    chapters: [{ t: 0, title: 'イントロ' }, { t: 4, title: '昨日覚えたのに、もう忘れた！？' }, { t: 21, title: '忘れるのは最初の1日が急' }, { t: 52, title: '間隔をあけると落ち方が緩やかに' }, { t: 172, title: 'エンディング' }],
    qa: { status: 'PASS', checks: 18, passed: 18, measuredSec: 180, overlaps: 0, minGapSec: 0.34, lufs: -16 },
    video: '/media/movies/lifehack-001/video.mp4', poster: '/media/movies/lifehack-001/poster.webp',
  } };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/media/')) {
      try { return await media(request, env); } catch (e) { if (e instanceof ApiError) return reply({ error: e.code }, e.status); throw e; }
    }
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    try {
      if (url.pathname === '/api/movie' && request.method === 'POST') return await submitMovie(request, env);
      const mv = url.pathname.match(/^\/api\/movie\/([A-Za-z0-9-]{1,80})$/);
      if (mv && request.method === 'GET') return await pollMovie(request, env, mv[1]);
      if (url.pathname === '/api/sketch' && request.method === 'POST') return await submit(request, env);
      const m = url.pathname.match(/^\/api\/sketch\/([A-Za-z0-9-]{1,80})$/);
      if (m && request.method === 'GET') return await poll(request, env, m[1]);
      fail(404, 'not_found');
    } catch (e) {
      if (e instanceof ApiError) return reply({ error: e.code }, e.status);
      console.error('sketch_api_error', e?.message);
      return reply({ error: 'internal' }, 500);
    }
  },
};
