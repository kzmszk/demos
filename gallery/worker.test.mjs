// Offline tests of gallery/worker.js: the movie API (validation, the job it registers, how a finished job is shown) and the /media route
// (byte ranges, conditional requests, which keys are served). A fake job service and a fake R2 bucket stand in for Cloudflare.
//   node --test gallery/
import test from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.js';

const ORIGIN = 'https://demos.example';
const PASS = 'open-sesame';

/** A stand-in for the hermes-llm-jobs service binding: records calls, answers from a script. */
function jobsService(answer) {
  const calls = [];
  return {
    calls,
    async fetch(url, init) {
      calls.push({ url, method: init.method, auth: init.headers.Authorization, body: init.body ? JSON.parse(init.body) : undefined });
      const { status, body } = answer(calls.at(-1));
      return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
    },
  };
}

/** A stand-in for an R2 bucket holding one object; get() slices by the Range header the way R2 does. */
function bucket(files) {
  return {
    async head(key) { const f = files[key]; return f && { size: f.data.length, httpEtag: f.etag }; },
    async get(key, { range, onlyIf } = {}) {
      const f = files[key];
      if (!f) return null;
      const meta = { size: f.data.length, httpEtag: f.etag };
      if (onlyIf?.get('if-none-match') === f.etag) return meta;               // condition failed: metadata only, no body
      let [a, b] = [0, f.data.length - 1];
      const m = /^bytes=(\d*)-(\d*)$/.exec(range?.get('range') || '');
      if (m && (m[1] || m[2])) {
        if (!m[1]) a = Math.max(0, f.data.length - +m[2]);
        else { a = +m[1]; if (m[2]) b = Math.min(b, +m[2]); }
      }
      if (a >= f.data.length) { a = 0; b = f.data.length - 1; }                // R2 ignores what it cannot satisfy and answers with everything
      const slice = f.data.slice(a, b + 1);
      return { ...meta, body: new Response(slice).body, range: { offset: a, length: slice.length } };
    },
  };
}

const post = (path, body, headers = {}) => new Request(ORIGIN + path, { method: 'POST', headers: { Origin: ORIGIN, 'Content-Type': 'application/json', ...headers }, body: typeof body === 'string' ? body : JSON.stringify(body) });
const get = (path, headers = {}) => new Request(ORIGIN + path, { headers });
const env = (extra = {}) => ({ SKETCH_PASSPHRASE: PASS, MOVIE_JOBS_API_KEY: 'movie-key', LLM_JOBS_API_KEY: 'sketch-key', ASSETS: { fetch: async () => new Response('asset') }, ...extra });
const json = async (r) => ({ status: r.status, j: await r.json() });
const good = { theme: '朝の習慣を変える', minutes: 3, passphrase: PASS };

test('a request with the wrong passphrase, origin or shape is refused', async () => {
  const e = env({ LLM_JOBS: jobsService(() => { throw new Error('the job service must not be called'); }) });
  assert.deepEqual(await json(await worker.fetch(post('/api/movie', { ...good, passphrase: 'nope' }), e)), { status: 403, j: { error: 'passphrase' } });
  for (const [name, patch, error] of [['no theme', { theme: '' }, 'theme'], ['theme with <', { theme: 'a<b' }, 'theme'], ['long theme', { theme: 'あ'.repeat(61) }, 'theme'],
    ['minutes 5', { minutes: 5 }, 'minutes'], ['minutes text', { minutes: '3' }, 'minutes'], ['notes number', { notes: 5 }, 'notes'], ['notes long', { notes: 'あ'.repeat(1501) }, 'notes'], ['notes NUL', { notes: 'a\u0000b' }, 'notes']]) {
    assert.deepEqual(await json(await worker.fetch(post('/api/movie', { ...good, ...patch }), e)), { status: 400, j: { error } }, name);
  }
  assert.equal((await worker.fetch(new Request(ORIGIN + '/api/movie', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(good) }), e)).status, 403, 'no Origin header');
  assert.equal((await worker.fetch(post('/api/movie', good, { 'Content-Type': 'text/plain' }), e)).status, 415);
  assert.equal((await worker.fetch(post('/api/movie', 'x'.repeat(6001)), e)).status, 413);
  assert.equal((await worker.fetch(post('/api/movie', '{nope'), e)).status, 400);
});

test('a good request becomes one video.generate job under the movie app key', async () => {
  const jobs = jobsService(() => ({ status: 201, body: { id: 'job-1', status: 'pending' } }));
  const e = env({ LLM_JOBS: jobs });
  const r = await json(await worker.fetch(post('/api/movie', { ...good, theme: '  朝の習慣を変える ', notes: ' 数字は\r\n\r\n\r\n出典つき ' }), e));
  assert.deepEqual(r, { status: 201, j: { id: 'job-1', status: 'queued' } });
  const c = jobs.calls[0];
  assert.equal(c.url, 'https://hermes-llm-jobs.kazumasa.workers.dev/api/jobs');
  assert.equal(c.auth, 'Bearer movie-key', 'its own app key, not the sketchbook\'s');
  assert.deepEqual(c.body.payload, { theme: '朝の習慣を変える', minutes: 3, notes: '数字は\n\n出典つき' });
  assert.equal(c.body.type, 'video.generate');
  assert.match(c.body.idempotencyKey, /^mv1-[0-9a-f]{48}$/);

  // the same request is the same job; another variant or length is another one
  await worker.fetch(post('/api/movie', { ...good, theme: '朝の習慣を変える', notes: '数字は\n\n出典つき' }), e);
  await worker.fetch(post('/api/movie', { ...good, variant: 1 }), e);
  await worker.fetch(post('/api/movie', { ...good, minutes: 2 }), e);
  const keys = jobs.calls.map((x) => x.body.idempotencyKey);
  assert.equal(keys[0], keys[1]);
  assert.equal(new Set(keys).size, 3);
  assert.equal(jobs.calls[2].body.payload.notes, undefined, 'no notes key when there are none');
});

test('the passphrase falls back to the sketchbook\'s unless a movie passphrase is set', async () => {
  const jobs = jobsService(() => ({ status: 201, body: { id: 'j', status: 'pending' } }));
  assert.equal((await worker.fetch(post('/api/movie', good), env({ LLM_JOBS: jobs }))).status, 201);
  const own = env({ LLM_JOBS: jobs, MOVIE_PASSPHRASE: 'movie-only' });
  assert.equal((await worker.fetch(post('/api/movie', good), own)).status, 403);
  assert.equal((await worker.fetch(post('/api/movie', { ...good, passphrase: 'MOVIE-only ' }), own)).status, 201, 'compared without case and edge spaces, like the sketchbook');
});

test('the daily allowance and an unreachable service are reported as such', async () => {
  const limited = env({ LLM_JOBS: jobsService(() => ({ status: 429, body: { error: { code: 'daily_limit' } } })) });
  assert.deepEqual(await json(await worker.fetch(post('/api/movie', good), limited)), { status: 429, j: { error: 'daily_limit' } });
  const down = env({ LLM_JOBS: jobsService(() => ({ status: 500, body: {} })) });
  assert.deepEqual(await json(await worker.fetch(post('/api/movie', good), down)), { status: 502, j: { error: 'jobs_unavailable' } });
  const slow = env({ LLM_JOBS: jobsService(() => ({ status: 429, body: { error: { code: 'rate_limited' } } })) });
  assert.deepEqual(await json(await worker.fetch(post('/api/movie', good), slow)), { status: 429, j: { error: 'slow_down' } });
});

test('polling shows the state, and only the known fields of a finished film, with its files as same-origin paths', async () => {
  const result = { title: '題', subtitle: '副', seconds: 119.6, width: 1920, height: 1080, style: 'podcast-duo', bytes: 25e6,
    chapters: [{ t: 0, title: 'イントロ' }, { t: 4, title: '本編' }], video: 'movies/job-1/video.mp4', poster: 'movies/job-1/poster.webp',
    qa: { status: 'PASS', checks: 18, passed: 18 }, model: 'secret model label', promptVersion: 'v', leaked: 'x' };
  for (const [state, want] of [['pending', 'queued'], ['running', 'making'], ['failed', 'failed']]) {
    const e = env({ LLM_JOBS: jobsService(() => ({ status: 200, body: { id: 'job-1', status: state, result: null } })) });
    assert.deepEqual(await json(await worker.fetch(get('/api/movie/job-1'), e)), { status: 200, j: { status: want } });
  }
  const jobs = jobsService(() => ({ status: 200, body: { id: 'job-1', status: 'completed', result } }));
  const done = await json(await worker.fetch(get('/api/movie/job-1'), env({ LLM_JOBS: jobs })));
  assert.equal(jobs.calls[0].url, 'https://hermes-llm-jobs.kazumasa.workers.dev/api/jobs/job-1');
  assert.equal(jobs.calls[0].auth, 'Bearer movie-key');
  assert.equal(done.j.status, 'done');
  assert.equal(done.j.movie.video, '/media/movies/job-1/video.mp4');
  assert.equal(done.j.movie.poster, '/media/movies/job-1/poster.webp');
  assert.deepEqual(Object.keys(done.j.movie).sort(), ['bytes', 'chapters', 'height', 'poster', 'qa', 'seconds', 'style', 'subtitle', 'title', 'video', 'width']);
  const missing = env({ LLM_JOBS: jobsService(() => ({ status: 404, body: {} })) });
  assert.deepEqual(await json(await worker.fetch(get('/api/movie/nope'), missing)), { status: 404, j: { error: 'missing' } });
  assert.equal((await worker.fetch(get('/api/movie/a%2F..%2Fb'), env())).status, 404, 'ids are plain');
});

test('the sketchbook API still uses its own key and answers as before', async () => {
  const jobs = jobsService(() => ({ status: 201, body: { id: 's1', status: 'pending' } }));
  const r = await json(await worker.fetch(post('/api/sketch', { subject: '縁側の柴犬', passphrase: PASS }), env({ LLM_JOBS: jobs })));
  assert.deepEqual(r, { status: 201, j: { id: 's1', status: 'queued' } });
  assert.equal(jobs.calls[0].auth, 'Bearer sketch-key');
  assert.equal(jobs.calls[0].body.type, 'illustration.svg');
});

/* ---------------- /media ---------------- */
const DATA = new Uint8Array(1000).map((_, i) => i % 251);
const files = { 'movies/job-1/video.mp4': { data: DATA, etag: '"abc"' }, 'movies/job-1/poster.webp': { data: DATA.slice(0, 100), etag: '"def"' } };
const media = (path, headers, method = 'GET') => worker.fetch(new Request(ORIGIN + path, { method, headers }), env({ MEDIA: bucket(files) }));

test('/media answers whole reads with 200 and every valid single range with 206', async () => {
  let r = await media('/media/movies/job-1/video.mp4');
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('content-type'), 'video/mp4');
  assert.equal(r.headers.get('accept-ranges'), 'bytes');
  assert.equal(r.headers.get('content-length'), '1000');
  assert.equal(r.headers.get('cross-origin-resource-policy'), 'same-origin');
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), DATA);

  for (const [range, from, to] of [['bytes=0-99', 0, 99], ['bytes=100-', 100, 999], ['bytes=-50', 950, 999], ['bytes=0-', 0, 999], ['bytes=990-5000', 990, 999], ['bytes=0-1', 0, 1]]) {
    r = await media('/media/movies/job-1/video.mp4', { Range: range });
    assert.equal(r.status, 206, range);
    assert.equal(r.headers.get('content-range'), `bytes ${from}-${to}/1000`, range);
    assert.equal(r.headers.get('content-length'), String(to - from + 1), range);
    assert.deepEqual(new Uint8Array(await r.arrayBuffer()), DATA.slice(from, to + 1), range);
  }
});

test('/media refuses what it cannot satisfy and ignores what it does not support', async () => {
  for (const range of ['bytes=5000-', 'bytes=5-2']) {
    const r = await media('/media/movies/job-1/video.mp4', { Range: range });
    assert.equal(r.status, 416, range);
    assert.equal(r.headers.get('content-range'), 'bytes */1000');
  }
  for (const range of ['bytes=0-10,20-30', 'bytes=-', 'lines=1-2', 'junk']) {
    const r = await media('/media/movies/job-1/video.mp4', { Range: range });
    assert.equal(r.status, 200, range);
    assert.equal(r.headers.get('content-length'), '1000');
  }
});

test('/media supports HEAD, conditional requests and downloads', async () => {
  let r = await media('/media/movies/job-1/video.mp4', {}, 'HEAD');
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('content-length'), '1000');
  assert.equal(await r.text(), '');
  r = await media('/media/movies/job-1/video.mp4', { 'If-None-Match': '"abc"' });
  assert.equal(r.status, 304);
  r = await media('/media/movies/job-1/video.mp4?download=1');
  assert.equal(r.headers.get('content-disposition'), 'attachment; filename="auto_movie-job-1.mp4"');
  r = await media('/media/movies/job-1/poster.webp');
  assert.equal(r.headers.get('content-type'), 'image/webp');
});

test('/media serves only movies/<id>/video.mp4 and poster.webp', async () => {
  for (const p of ['/media/movies/job-1/other.mp4', '/media/movies/job-1/video.mp4/x', '/media/movies/../etc/passwd', '/media/movies%2Fjob-1%2F..%2Fjob-1%2Fvideo.mp4', '/media/movies/nothing/video.mp4', '/media/', '/media/movies/job-1/', '/media/other/job-1/video.mp4', '/media/%E0%A4%A']) {
    assert.equal((await media(p)).status, 404, p);
  }
  assert.equal((await media('/media/movies/job-1/video.mp4', {}, 'POST')).status, 405);
  assert.equal((await worker.fetch(get('/media/movies/job-1/video.mp4'), env())).status, 404, 'no bucket bound');
});

test('everything else is a static asset', async () => {
  const r = await worker.fetch(get('/auto_movie/'), env());
  assert.equal(await r.text(), 'asset');
});
