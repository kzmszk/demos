/* The sound test page (public/audiotest.html): play the music from any movement, every grain, walk on every ground, hear a bell
   at a distance — and the offline tests that tools/audiotest.mjs drives in headless Chrome (window.AT.runAll()).
   Bundle: cd tools && npx esbuild web/audiotest.js --bundle --format=esm --outfile=../public/audiotest.js */
import { createAudio, renderOffline, wavBytes } from './audio.js';
import { synthKit } from './synthkit.js';

const COUNTS = synthKit().COUNTS;
const $ = (id) => document.getElementById(id);
const SURF = { 0: 'none', 1: 'asphalt', 2: 'asphalt lane', 3: 'sidewalk', 4: 'stone sett', 5: 'gravel', 6: 'soil', 7: 'grass', 8: 'moss', 9: 'forest', 10: 'riverbed', 11: 'ballast', 12: 'concrete', 13: 'sand', 14: 'graves', 15: 'farm', 16: 'tactile', 17: 'stone slab', 18: 'wood deck', 255: 'wooden floor' };
const logEl = $('log');
const log = (...a) => { const s = a.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join(' '); console.log(s); if (logEl) { logEl.textContent += s + '\n'; logEl.scrollTop = logEl.scrollHeight; } };
window.addEventListener('error', (e) => log('ERROR', e.message, e.filename + ':' + e.lineno));
window.addEventListener('unhandledrejection', (e) => log('REJECTED', String(e.reason && e.reason.stack || e.reason)));

const A = createAudio({ debug: true, onMovement: (m) => { $('now').textContent = `${m.title_ja}  —  ${m.title}`; log('now playing:', m.index, m.id, m.title); } });
const W = { mode: 'walk', walkSpeed: 0, surf: 5, season: 0, water: 0, fall: 0, weir: 0, camZ: 2, interior: null, bells: [] };

/* ------------------------------------------------------------------ the page */
for (const [id, name] of Object.entries(SURF)) { const o = document.createElement('option'); o.value = id; o.textContent = `${id} ${name}`; if (+id === 5) o.selected = true; $('surf').appendChild(o); }
for (const kind of Object.keys(COUNTS)) {
  const b = document.createElement('button'); b.textContent = kind + (COUNTS[kind] > 1 ? ` ×${COUNTS[kind]}` : '');
  b.onclick = async () => { await begin(); if (kind === 'bell') A.bell({ dist: +$('bdist').value, az: +$('baz').value, id: Math.floor(Math.random() * 3), delay: $('belldelay').checked }); else A.play(kind, { self: ['gravel', 'stone', 'wood', 'snow', 'asphalt', 'soft', 'leaves'].includes(kind) }); };
  $('grains').appendChild(b);
}
let began = false;
async function begin() { if (began) return; began = true; await A.start(); }
$('start').onclick = async () => { await begin(); log('started', A.info()); fillMovements(); };
$('mute').onclick = () => { const on = $('mute').classList.toggle('on'); A.setEnabled(!on); $('mute').textContent = on ? 'Unmute' : 'Mute'; };
$('next').onclick = () => A.next(); $('prev').onclick = () => A.prev();
$('jump').onclick = async () => { await begin(); A.jump(+$('mv').value, { beat: +$('beat').value || 0 }); };
function fillMovements() {
  const ms = A.movements(); if (!ms.length) { setTimeout(fillMovements, 200); return; }
  if ($('mv').options.length) return;
  for (const m of ms) { const o = document.createElement('option'); o.value = m.index; o.textContent = `${m.index}  ${m.title_ja}  (${Math.floor(m.sec / 60)}:${String(Math.round(m.sec % 60)).padStart(2, '0')})`; $('mv').appendChild(o); }
}
const bind = (id, fn) => { const el = $(id), f = () => fn(el); el.addEventListener('input', f); el.addEventListener('change', f); f(); };
bind('mode', (e) => (W.mode = e.value)); bind('speed', (e) => { W.walkSpeed = +e.value; $('speedv').textContent = e.value; });
bind('surf', (e) => (W.surf = +e.value)); bind('season', (e) => (W.season = +e.value)); bind('interior', (e) => (W.interior = e.value || null));
bind('water', (e) => (W.water = +e.value)); bind('weir', (e) => (W.weir = +e.value)); bind('fall', (e) => (W.fall = +e.value));
bind('camz', (e) => { W.camZ = +e.value; $('camzv').textContent = e.value; });
const bellList = () => { W.bells = $('bellson').checked ? [{ id: 11, dist: +$('bdist').value, az: +$('baz').value }, { id: 12, dist: 650, az: -2 }] : []; $('bdistv').textContent = $('bdist').value; };
bind('bellson', bellList); bind('bdist', bellList); bind('baz', bellList);
$('bellnow').onclick = async () => { await begin(); A.bell({ dist: +$('bdist').value, az: +$('baz').value, id: Math.floor(Math.random() * 3), delay: $('belldelay').checked }); };
let last = performance.now(), nextInfo = 0;
function frame(t) {
  const dt = (t - last) / 1000; last = t;
  if (began) { A.update(dt, W); if (t > nextInfo) { nextInfo = t + 500; $('info').textContent = JSON.stringify(A.info()); } }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

/* ------------------------------------------------------------------ the offline tests */
const db = (x) => +(20 * Math.log10(Math.max(x, 1e-9))).toFixed(1);
function stats(buf, t0 = 0, t1 = buf.duration) {
  let pk = 0, e = 0, n = 0;
  for (let c = 0; c < buf.numberOfChannels; c++) { const d = buf.getChannelData(c), i0 = Math.floor(t0 * buf.sampleRate), i1 = Math.min(d.length, Math.floor(t1 * buf.sampleRate)); for (let i = i0; i < i1; i++) { const x = d[i]; if (Math.abs(x) > pk) pk = Math.abs(x); e += x * x; n++; } }
  return { peak: db(pk), rms: db(Math.sqrt(e / Math.max(1, n))) };
}
async function save(name, buf) { try { const r = await fetch('/__save/' + name, { method: 'POST', body: wavBytes(buf) }); return r.ok; } catch (e) { return false; } }
const STEP_KINDS = ['gravel', 'stone', 'wood', 'snow', 'asphalt', 'soft', 'leaves'];
const AT = window.AT = { A, createAudio, renderOffline, wavBytes, stats, COUNTS };

AT.runAll = async function (only) {
  const R = { kit: null, aria: null, pitch: null, grains: {}, walk: {}, water: {}, bells: {}, movements: [] };
  const want = (k) => !only || only.includes(k);
  let kit = null;
  const out = (txt) => { $('testst').textContent = txt; log(txt); };
  /* the Aria's first four bars, with the whole engine (a first context also renders the kit: timings) */
  out('aria …');
  const t0 = performance.now();
  const a = await renderOffline({ movement: 'aria', sec: 24, amb: false }); kit = a.A.kit;
  R.kit = Object.assign({ wallMs: Math.round(performance.now() - t0) }, a.A.info());
  const cur = a.A._dbg.cur;
  R.aria = { saved: await save('aria-4bars.wav', a.buffer), t0: cur.t0, bpm: cur.mv.bpm, trim: cur.trim, P: cur.p.P, len: cur.p.len, stats: stats(a.buffer),
    events: cur.p.ev.filter((e) => e.t < 20).map((e) => [+(cur.t0 + e.t).toFixed(4), e.m, +e.v.toFixed(3), +e.d.toFixed(3), +e.b.toFixed(3)]),
    bars: [0, 1, 2, 3, 4].map((i) => stats(a.buffer, 0.15 + i * 4.5, Math.min(24, 0.15 + (i + 1) * 4.5))) };
  /* the pitch of the keys: a chromatic-ish ladder through the whole range, dry */
  if (want('pitch')) {
    out('pitch …');
    const ps = [31, 33, 36, 41, 45, 48, 52, 55, 60, 64, 67, 69, 72, 76, 79, 84, 86];
    const score = { movements: [{ id: 'pitchtest', title: 'pitch test', title_ja: 'pitch', meter: [4, 4], bpm: 60, total_beats: ps.length * 2 + 2, bar_beats: [0, 4, 8, 12, 16, 20, 24, 28, 32], notes: ps.map((m, i) => [i * 2, 1.6, m, 70]) }] };
    let pev = null;
    const p = await renderOffline({ score, sec: ps.length * 2 + 3, amb: false, rooms: false, kit, onFrame: (A2, t) => { if (t === 1) { const c = A2._dbg.cur; pev = c.p.ev.map((e) => [+(c.t0 + e.t).toFixed(4), e.m]); } } });
    R.pitch = { saved: await save('pitch.wav', p.buffer), stats: stats(p.buffer), events: pev };
  }
  /* each grain through the whole chain: three variants, a gap apart */
  if (want('grains')) for (const kind of Object.keys(COUNTS)) {
    out('grain ' + kind + ' …');
    const long = kind === 'bell' ? 44 : kind === 'fall' ? 4 : 1.6, n = kind === 'bell' ? 1 : 3, sec = n * long + 0.5;
    const g = await renderOffline({ sec, music: false, kit, settle: 150, onFrame: (A2, t) => { if (t === 0) for (let i = 0; i < n; i++) A2.play(kind, { id: i, at: 0.1 + i * long, self: STEP_KINDS.includes(kind) }); } });
    R.grains[kind] = { saved: await save('grain-' + kind + '.wav', g.buffer), stats: stats(g.buffer, 0, sec), peaks: [...Array(n).keys()].map((i) => stats(g.buffer, 0.1 + i * long, 0.1 + (i + 1) * long)) };
  }
  /* walking on every ground, 1.4 m/s, six seconds (and in snow, and in the hall) */
  if (want('walk')) {
    const surfs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 255, 0];
    const cases = surfs.map((s) => ['walk-' + s, { surf: s, season: 0 }]).concat([['walk-snow-5', { surf: 5, season: 1 }], ['walk-snow-9', { surf: 9, season: 1 }], ['walk-snow-1', { surf: 1, season: 1 }], ['walk-snow-18', { surf: 18, season: 1 }], ['walk-hall', { surf: 255, season: 0, interior: 'sanjusangendo' }], ['run-5', { surf: 5, season: 0, speed: 3.6 }]]);
    for (const [name, c] of cases) {
      out(name + ' …');
      const g = await renderOffline({ sec: 6, music: false, kit, settle: 150, step: 1 / 60, state: { mode: 'walk', walkSpeed: c.speed || 1.4, surf: c.surf, season: c.season, interior: c.interior || null, camZ: 2 } });
      R.walk[name] = { saved: ['walk-1', 'walk-4', 'walk-5', 'walk-6', 'walk-9', 'walk-17', 'walk-18', 'walk-255', 'walk-snow-5', 'walk-snow-1', 'walk-hall', 'run-5'].includes(name) ? await save(name + '.wav', g.buffer) : false, stats: stats(g.buffer, 0.2, 6) };
    }
  }
  /* water: a stream, a weir, a waterfall near and far, with and without the piano */
  if (want('water')) {
    for (const [name, st, sec] of [['stream', { water: 1 }, 14], ['weir', { weir: 1 }, 12], ['fall-1', { fall: 1 }, 12], ['fall-0.35', { fall: 0.35 }, 10], ['fall-hall', { fall: 1, interior: 'sanjusangendo' }, 8]]) {
      out(name + ' …');
      const g = await renderOffline({ sec, music: false, kit, settle: 150, step: 0.1, state: Object.assign({ mode: 'walk', walkSpeed: 0, camZ: 2 }, st) });
      R.water[name] = { saved: await save('water-' + name + '.wav', g.buffer), stats: stats(g.buffer, 1, sec) };
    }
    out('fall + piano …');
    const g = await renderOffline({ sec: 20, kit, settle: 150, state: { mode: 'walk', walkSpeed: 0, camZ: 2, fall: 1, water: 1 } });
    R.water.piano_fall = { saved: await save('water-piano-fall.wav', g.buffer), stats: stats(g.buffer, 2, 20) };
  }
  /* bells: three sizes at three distances; and a stretch of the scheduler with two bells in range */
  if (want('bells')) {
    for (const [name, dist, id] of [['near', 60, 0], ['mid', 300, 1], ['far', 800, 2]]) {
      out('bell ' + name + ' …');
      const g = await renderOffline({ sec: 46, music: false, kit, settle: 150, onFrame: (A2, t) => { if (t === 0) A2.bell({ dist, az: 0.8, id, delay: false }); } });
      R.bells[name] = { saved: await save('bell-' + name + '.wav', g.buffer), stats: stats(g.buffer, 0, 46) };
    }
    out('bell scheduler …');
    const g = await renderOffline({ sec: 420, music: false, kit, settle: 150, step: 0.5, state: { mode: 'walk', walkSpeed: 0, camZ: 2, bells: [{ id: 3, dist: 200, az: 0.3 }, { id: 4, dist: 520, az: -1.9 }, { id: 5, dist: 780, az: 2.5 }] }, onFrame: (A2, t) => { if (t >= 419) R.bells.log = A2._dbg.strikes.slice(); } });
    R.bells.scheduler = { stats: stats(g.buffer) };
  }
  /* the end of the Aria into the first variation (the silence between; the label), and the piano in the wooden hall */
  if (want('transition')) {
    out('transition …');
    const names = []; let tl = null;
    const g = await renderOffline({ movement: 'aria', beat: 186, sec: 30, amb: false, kit, onFrame: (A2, t) => { const np = A2.nowPlaying(); if (!names.length || names[names.length - 1][1] !== np.id) names.push([t, np.id]); if (t === 29) tl = A2._dbg.timeline.slice(); } });
    const win = []; for (let i = 0; i < 30 * 4; i++) win.push(stats(g.buffer, i * 0.25, (i + 1) * 0.25).rms);
    R.transition = { saved: await save('transition.wav', g.buffer), nowPlaying: names, timeline: tl, rmsPerQuarterSecond: win };
    out('da capo wraps to the Aria …');
    const nm2 = []; const w2 = await renderOffline({ movement: 'aria_da_capo', beat: 186, sec: 22, amb: false, kit, onFrame: (A2, t) => { const np = A2.nowPlaying(); if (!nm2.length || nm2[nm2.length - 1][1] !== np.id) nm2.push([t, np.id]); } });
    R.wrap = { nowPlaying: nm2, stats: stats(w2.buffer) };
    out('hall …');
    const h = await renderOffline({ movement: 'aria', sec: 20, amb: false, kit, state: { mode: 'walk', interior: 'sanjusangendo' } });
    R.hall = { saved: await save('aria-hall.wav', h.buffer), stats: stats(h.buffer, 1, 20) };
    const o2 = await renderOffline({ movement: 'aria', sec: 20, amb: false, kit });
    R.hall.outdoors = stats(o2.buffer, 1, 20);
  }
  /* every movement: sixteen seconds from about the middle, for the level */
  if (want('movements')) {
    const ms = a.A.movements();
    for (const m of ms) {
      out('movement ' + m.id + ' …');
      const mv = a.A._dbg.MOV[m.index], bars = mv.bar_beats, beat = bars[Math.floor(bars.length * 0.4)] || 0;
      const g = await renderOffline({ movement: m.index, beat, sec: 18, amb: false, kit, settle: 250 });
      const p = g.A._dbg.prep(m.index);
      R.movements.push({ id: m.id, bpm: mv.bpm, beat, trim: +p.trim.toFixed(3), P: +p.P.toFixed(3), stats: stats(g.buffer, 1, 18), saved: ['var28', 'var25', 'var22', 'var05'].includes(m.id) ? await save('mv-' + m.id + '.wav', g.buffer) : false });
    }
  }
  out('done');
  return R;
};
/* the live engine in this (headless) page: how long until the first note, how long the main thread was ever held, does the clock run */
AT.live = async (secs = 16) => {
  const L = createAudio({ debug: true }), sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const st = { mode: 'walk', walkSpeed: 1.4, surf: 5, season: 0, water: 0.6, fall: 0.3, camZ: 2, bells: [{ id: 1, dist: 250, az: 0.5 }] };
  const t0 = performance.now(); await L.start(); const tStart = performance.now() - t0;
  let lastT = performance.now(), maxGap = 0, frames = 0; const iv = setInterval(() => { const n = performance.now(); maxGap = Math.max(maxGap, n - lastT); lastT = n; frames++; L.update(0.016, st); }, 16);
  const log2 = [];
  for (let i = 0; i < secs * 2; i++) {
    await sleep(500);
    if (i === 20) L.jump('var25');
    if (i === 24) L.next();
    if (i % 4 === 3) log2.push({ t: (i + 1) / 2, ctx: +(L._dbg.ctx.currentTime).toFixed(2), state: L._dbg.ctx.state, info: L.info(), now: L.nowPlaying().id });
  }
  clearInterval(iv);
  const ctx = L._dbg.ctx, n = L._dbg.cur;
  return { startCallMs: Math.round(tStart), sampleRate: ctx.sampleRate, baseLatency: ctx.baseLatency, state: ctx.state, ctxTime: ctx.currentTime, wall: (performance.now() - t0) / 1000, maxGapMs: Math.round(maxGap), frames, log: log2, timeline: L._dbg.timeline };
};
/* the page's own controls, clicked by a script (headless): start, the list of movements, a jump, a grain, the sliders */
AT.ui = async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms)), o = {};
  $('start').click(); await sleep(2500);
  o.movements = $('mv').options.length; o.now1 = $('now').textContent; o.info = $('info').textContent;
  $('mv').value = '5'; $('jump').click(); await sleep(2000); o.now2 = $('now').textContent;
  for (const b of document.querySelectorAll('#grains button')) b.click();
  $('speed').value = '1.5'; $('speed').dispatchEvent(new Event('input')); $('surf').value = '17'; $('surf').dispatchEvent(new Event('change'));
  $('season').value = '1'; $('season').dispatchEvent(new Event('change')); $('fall').value = '0.8'; $('fall').dispatchEvent(new Event('input'));
  $('bellson').checked = true; $('bellson').dispatchEvent(new Event('change')); $('interior').value = 'sanjusangendo'; $('interior').dispatchEvent(new Event('change'));
  $('mute').click(); await sleep(500); o.muted = A.info().enabled; $('mute').click(); await sleep(1500);
  o.world = JSON.stringify(W); o.after = A.info(); o.log = $('log').textContent.split('\n').slice(-6);
  return o;
};
log('audiotest ready');
