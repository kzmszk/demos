/* SOUND — KYOTO.
   Music: Bach's Goldberg Variations (BWV 988), all thirty-two movements from the Aria through the thirty variations to the
   Aria da capo, played slowly on a solo piano and begun again when they end. The piano is the string-physics piano of ALOFT /
   VATICANO / VENEZIA (synthkit.js, unchanged), rendered once in a worker; the score is data/goldberg.json (CC BY-SA 4.0, see
   CREDITS). Natural sounds: only the ones with a visible cause — the listener's own footsteps on gravel, stone, boards, snow or
   asphalt, drops and bubbles of a stream, the wash of a weir, the many drops of a small waterfall, the great bronze bells of the
   temples a long way off, a distant crow — each a short granular event scattered in time. No noise beds, no drones.
   See createAudio() at the bottom for the API. */
import { synthKit } from './synthkit.js';

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);
const num = (x, d = 0) => (typeof x === 'number' && Number.isFinite(x) ? x : d);
const idNum = (id) => { if (typeof id === 'string') { let h = 0; for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) % 100003; return h; } return Math.abs(Math.floor(num(id, 0))); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ====================================================================================================
   THE SCORE — a movement is a list of notes in beats (quarter notes); a tempo map turns beats into seconds, and a pianist's
   shaping bends it a little: within a phrase of four bars the middle bars go on, the last eases; the end of a half is
   broader still, the last bar of a movement broadest (a ritardando). Every key is humanised a little in time; a chord is
   rolled from the bass up. The playing tempo is in the data (bpm).
   ==================================================================================================== */
const PPQ = 48;                     /* the resolution of the beat → seconds table */
function lcg(seed) { let s = seed % 2147483647; if (s <= 0) s += 2147483646; return () => (s = (s * 16807) % 2147483647) / 2147483647; }
function prepare(mv, idx) {
  const total = mv.total_beats, tm = mv.tempo_map && mv.tempo_map.length ? mv.tempo_map : [[0, mv.bpm]];
  /* the bars (a pick-up is not a bar of the phrase) → a slowness factor at the middle of each */
  const bb = Array.from(new Set(mv.bar_beats)).sort((a, b) => a - b), reg = [];
  bb.forEach((a, i) => { const z = i + 1 < bb.length ? bb[i + 1] : total; if (z - a >= 1) reg.push([a, z]); });
  const ctr = [], fac = [];
  reg.forEach(([a, z], i) => {
    let f = [1, 0.985, 0.985, 1.04][i % 4];
    if (i % 8 === 7) f *= 1.03;
    if (i % 16 === 15) f *= 1.05;
    if (i === reg.length - 1) f *= 1.22; else if (i === reg.length - 2) f *= 1.07;
    ctr.push((a + z) / 2); fac.push(f);
  });
  const n = Math.ceil(total * PPQ) + PPQ, cum = new Float64Array(n + 1);
  let seg = 0, ti = 0;
  for (let j = 0; j < n; j++) {
    const x = (j + 0.5) / PPQ;
    while (ti + 1 < tm.length && x >= tm[ti + 1][0]) ti++;
    while (seg + 1 < ctr.length && x > ctr[seg + 1]) seg++;
    let f;
    if (!ctr.length) f = 1; else if (x <= ctr[0]) f = fac[0]; else if (seg + 1 >= ctr.length) f = fac[fac.length - 1];
    else f = fac[seg] + (fac[seg + 1] - fac[seg]) * clamp((x - ctr[seg]) / (ctr[seg + 1] - ctr[seg]), 0, 1);
    cum[j + 1] = cum[j] + ((60 / tm[ti][1]) * f) / PPQ;
  }
  const T = (b) => { const x = Math.max(0, b) * PPQ, j = Math.min(n - 1, Math.floor(x)); return cum[j] + (cum[j + 1] - cum[j]) * (x - j); };
  const rng = lcg(7919 + idx * 131), N = mv.notes, ev = [];
  for (let i = 0; i < N.length;) {
    let j = i + 1; while (j < N.length && N[j][0] - N[i][0] < 0.004) j++;
    const grp = N.slice(i, j).sort((a, b) => a[2] - b[2]);
    grp.forEach(([t, d, m, vel], k) => {
      const t0 = T(t), roll = grp.length > 2 ? Math.min(0.018, k * 0.0045) : 0;
      ev.push({ b: t, t: Math.max(0, t0 + roll + (rng() - 0.5) * 0.008), m, v: clamp(((vel - 14) / 100) * (0.94 + 0.12 * rng()), 0.04, 1), d: Math.max(0.12, T(t + d) - t0) });
    });
    i = j;
  }
  ev.sort((a, b) => a.t - b.t);
  const len = T(total);
  /* the keys of the first half minute (to know when a movement can begin), and a rough loudness (the energy the notes put in per second) */
  const keys0 = new Set(); let E = 0;
  for (const e of ev) {
    if (e.t < 30) keys0.add(e.m);
    const amp = 0.05 + 0.95 * Math.pow(e.v, 1.6), tau = clamp(1.7 - 0.02 * (e.m - 60), 0.5, 2.6);
    E += amp * amp * Math.min(tau, e.d + 0.3);
  }
  const P = E / len;
  return { ev, len, T, keys0, P, trim: clamp(Math.pow(10, (LEVEL - (LEVEL_A + LEVEL_B * 10 * Math.log10(P))) / 20), 0.45, 1.5) };
}
/* every movement is brought to the same loudness: LEVEL is the rms (dBFS, over a quarter-minute of the finished mix) aimed at, and
   LEVEL_A + LEVEL_B * 10 log10(P) what a movement of loudness P (see above) gives at a trim of 1 (a fit to renderings of all
   thirty-two movements: it is within half a dB) */
const LEVEL = -20.5, LEVEL_A = -16.13, LEVEL_B = 1.55;

/* ====================================================================================================
   THE ENGINE
   ==================================================================================================== */
const MASTER = 1.0;       /* master gain */
const MUSIC = 1.2;        /* the piano, before the master */
const AMB = 0.55;         /* the natural sounds, against the piano */
/* each kind of natural sound, weighed so that its peaks (gain 1, one grain) sit about 10 dB under the piano's (measured offline) */
const G = { drip: 0.36, bubble: 0.36, trickle: 0.36, wash: 0.3, fall: 0.3, gravel: 0.42, stone: 0.45, wood: 0.42, snow: 0.42, asphalt: 0.45, soft: 0.45, leaves: 0.45, crow: 0.14, clap: 0.38, bell: 0.45 };
const AHEAD = 1.5;        /* how far ahead notes are put on the audio clock (s): the page may sleep a moment */
const GAP = 3.0;          /* the silence between two movements, from the last sound of one to the first of the next (s) */
const XFADE = 1.6;        /* the crossfade when a movement is chosen by hand (s) */
const CURVE_IN = new Float32Array(64), CURVE_OUT = new Float32Array(64);
for (let i = 0; i < 64; i++) { const u = i / 63; CURVE_IN[i] = Math.sin((u * Math.PI) / 2); CURVE_OUT[i] = Math.cos((u * Math.PI) / 2); }
const ROOMS = ['hall', 'wood'];
/* the rooms' impulse responses: noise that darkens as it dies (k: the one-pole opening, from k0 to k1 with time constant tauK) —
   a warm medium hall for the piano out of doors, and the large wooden hall of Sanjusangendo: drier and darker */
const ROOM_IR = {
  hall: { sec: 3.4, rt: 2.3, pre: 0.02, k0: 0.6, k1: 0.05, tauK: 0.55, build: 0.01, early: 10, spread: 0.08, hp: 90 },
  wood: { sec: 2.2, rt: 1.35, pre: 0.012, k0: 0.4, k1: 0.04, tauK: 0.35, build: 0.006, early: 16, spread: 0.11, hp: 110 },
};
/* where each kind of sound goes: [music send, ambience send, footstep send] to [hall, wood] */
const SEND = {
  out: { music: [0.42, 0], amb: [0.2, 0], self: [0.16, 0], dry: 1.0 },
  sanjusangendo: { music: [0, 0.5], amb: [0, 0.22], self: [0, 0.4], dry: 0.9 },
};
/* the ground under the walker → [grain, weight, pitch] (autumn; in winter all but cleared asphalt and the boards are snow) */
const SURF = {
  1: ['asphalt', 1, 1], 2: ['asphalt', 0.9, 1.04], 3: ['stone', 0.8, 1.05], 4: ['stone', 1, 1.1], 5: ['gravel', 1, 1], 6: ['soft', 1, 1], 7: ['soft', 0.65, 1.1],
  8: ['soft', 0.4, 0.95], 9: ['leaves', 0.9, 1], 10: ['gravel', 0.75, 0.88], 11: ['gravel', 1.15, 0.84], 12: ['stone', 0.85, 0.97], 13: ['gravel', 0.45, 0.78],
  14: ['gravel', 0.9, 1], 15: ['soft', 0.9, 0.95], 16: ['stone', 0.9, 1.08], 17: ['stone', 1, 0.92], 18: ['wood', 1, 1], 255: ['wood', 1.05, 0.95],
};
const NOSNOW = { 1: 1, 2: 1, 18: 1, 255: 1 };
const INTERIORS = { sanjusangendo: 1 };
const SPEED_OF_SOUND = 343;

/* createAudio(opts) → { start(), setEnabled(on), update(dt, s), info(), nowPlaying(), movements(), jump(id|index, {beat}), next(), prev(),
                         play(kind, o), bell(o), whenReady() }

     start()         from a user gesture: makes the AudioContext, loads the score, starts rendering the piano keys and grains in a worker,
                     and fades the sound in (the Aria begins as soon as its keys are ready). Safe to call again. Does not block.
     setEnabled(on)  mute / unmute with a fade of about a second (the context is suspended while muted: no CPU)
     update(dt, s)   every frame. It allocates nothing but the sound events themselves; notes are put on the audio clock ahead of time.
                     s = { mode: 'title'|'walk'|'fly', walkSpeed: m/s, surf: id of the ground under the walker (0 none, 1 asphalt,
                           2 asphalt_lane, 3 sidewalk, 4 stone_sett, 5 gravel, 6 soil, 7 grass, 8 moss, 9 forest, 10 riverbed, 11 ballast,
                           12 concrete, 13 sand, 14 graves, 15 farm, 16 tactile, 17 stone_slab, 18 wood_deck; 255 a wooden floor),
                           season: 0 autumn | 1 winter, water: 0..1 (water nearby), fall: 0..1 (a waterfall nearby), weir: 0..1 (optional;
                           default from water), bells: [{id, dist (m), az (rad, relative to the view: + to the right)}] (temple bells
                           within about 800 m), camZ: metres above the ground, interior: null | 'sanjusangendo' }
     nowPlaying()    { index, id, title, title_ja } of the movement being heard (it changes during the silence before the next one)
     movements()     [{ index, id, title, title_ja, sec }]
     jump(i, {beat}) crossfade to a movement (by index or id), from a beat of it; next() / prev() likewise
     play(kind, o)   one grain now (o: { gain, rate, pan, id, at (audio time), self (footstep bus) }); kinds: see synthkit.js
     bell(o)         one bronze bell now (o: { dist (m), az, id, delay (false: sound at once), gain })
     info()          what is playing and how far the kit has got (for a debug overlay)
   createAudio({ context, debug, kit, score, scoreUrl, noMusic, noAmb, noRooms, startMovement, startBeat, onMovement }):
     context  an OfflineAudioContext to render into (see renderOffline); debug: also returns ._dbg; kit: the rendered sounds of another
     instance (a test makes many); score: the parsed goldberg.json; scoreUrl: where to fetch it (default 'data/goldberg.json');
     startMovement / startBeat: where the music begins (default the Aria); onMovement(info): called when the movement heard changes. */
export function createAudio(opts = {}) {
  let ctx = null, started = false, enabled = null, timer = 0, MOV = null;
  let master, comp, lim, clip, music, tone, bodyG, out, outLP1, outLP2, outG, selfBus, fallBus, fallG, fallLP, room = {};
  const KIT = opts.kit || { KEYS: {}, BANK: {}, done: 0, total: 0, sfx: 0, cpu: 0 };
  const KEYS = KIT.KEYS, BANK = KIT.BANK, LASTID = {}, PREP = {};
  let queue = [], allJobs = [], inflight = 0, worker = null, fallbackOn = false, t0Start = 0, tFirst = 0, tKit = 0;
  let cur = null, dying = [], timeline = [], want = { mi: opts.startMovement ?? 0, beat: opts.startBeat || 0, fade: 0 }, lastNow = -1, lastIdx = -1;
  const live = () => !!ctx && (ctx.state === 'running' || !!opts.context);      /* (a test drives an offline context by hand) */
  /* the world, as the last update saw it */
  let mode = 'title', interior = null, gnd = 1, muf = 0, interiorK = 0, roomKey = 'out', lastSlow = -1;
  let stepPhase = 0.85, foot = 0, fallNext = 0, clock = 0, crowT = 80 + 140 * Math.random(), lastBell = -99;
  const LAST = new Float64Array(64).fill(NaN), bells = new Map(), strikes = [];

  /* ---------------------------------------------------------------- the kit: piano keys and grains */
  const toBuffer = (r) => { const b = ctx.createBuffer(r.data.length, r.data[0].length, r.rate); r.data.forEach((d, c) => b.getChannelData(c).set(d)); return b; };
  function take(r) {
    if (r.kind) { (BANK[r.kind] || (BANK[r.kind] = []))[r.id] = { raw: r, buf: null }; KIT.sfx++; }
    else KEYS[r.m] = { raw: r, buf: null };
    KIT.done++; KIT.cpu += r.ms || 0; if (KIT.done >= KIT.total) tKit = performance.now() - t0Start;
  }
  /* a rendered sound waits as raw samples until first used, then lives as an AudioBuffer only */
  const keyBuf = (k) => { const s = KEYS[k]; if (!s) return null; if (!s.buf) { s.buf = toBuffer(s.raw); s.raw = null; } return s.buf; };
  const bufOf = (kind, id) => { const bk = BANK[kind], s = bk && bk[id]; if (!s) return null; if (!s.buf) { s.buf = toBuffer(s.raw); s.raw = null; } return s.buf; };
  function pick(kind) {
    const bk = BANK[kind]; if (!bk) return -1;
    let n = 0; for (let i = 0; i < bk.length; i++) if (bk[i]) n++;
    if (!n) return -1;
    let id = Math.floor(Math.random() * bk.length), g = 0; while (!bk[id] && g++ < 64) id = (id + 1) % bk.length;
    if (id === LASTID[kind] && n > 1) { do id = (id + 1) % bk.length; while (!bk[id]); }
    return (LASTID[kind] = id);
  }
  /* the jobs go to the worker a few at a time, so that what a movement needs next can be moved to the front of the queue */
  const runJob = (K, j) => (j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need));
  function pump() {
    while (worker && inflight < 2 && queue.length) { inflight++; worker.postMessage(queue.splice(0, 3)); }
  }
  function mainThread() {
    fallbackOn = true; const K = synthKit();
    queue = allJobs.filter((j) => (j.sfx ? !(BANK[j.sfx] && BANK[j.sfx][j.id]) : !KEYS[j.m]));
    const step = () => { const t = performance.now(); while (queue.length && performance.now() - t < 10) { const j = queue.shift(), t1 = performance.now(), r = runJob(K, j); r.ms = performance.now() - t1; take(r); } if (queue.length) setTimeout(step, 0); };
    step();
  }
  function loadKit(jobs) {
    queue = jobs.slice(); allJobs = jobs.slice(); KIT.total += jobs.length;
    if (!jobs.length) { tKit = 0; return; }
    try {
      const src = `const K = (${synthKit.toString()})();\nself.onmessage = (e) => { const J = e.data; J.forEach((j, i) => { const t = performance.now(), r = j.sfx ? K.sfx(j.sfx, j.id) : K.note(j.m, j.need); r.ms = performance.now() - t; r.last = i === J.length - 1; self.postMessage(r, r.data.map((d) => d.buffer)); }); };`;
      const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
      w.onmessage = (e) => { take(e.data); if (e.data.last) { inflight--; pump(); } if (KIT.done >= KIT.total) w.terminate(); };
      w.onerror = (e) => { if (e && e.preventDefault) e.preventDefault(); try { w.terminate(); } catch (x) { /* fine */ } worker = null; inflight = 0; mainThread(); };
      worker = w; pump();
    } catch (e) { worker = null; mainThread(); }
  }
  /* what a movement needs first: move those keys to the front of the queue */
  function prioritize(keys) {
    const f = [], r = [];
    for (const j of queue) (!j.sfx && keys.has(j.m) ? f : r).push(j);
    if (f.length) queue = f.concat(r);
    pump();
  }
  const ready = (keys) => { for (const k of keys) if (!KEYS[k]) return false; return true; };

  /* the movements: what to play, and the keys and grains to make. Keys: every pitch of the work, each rendered as it sounds (no
     neighbour pitched up), longest-needed length from the data; the Aria's first, in the order it uses them. */
  function setup(score) {
    MOV = score.movements;
    if (typeof want.mi === 'string') { const k = MOV.findIndex((m) => m.id === want.mi); want.mi = k < 0 ? 0 : k; }
    MOV.forEach((m, i) => { m.index = i; m.sec = (() => { const tm = m.tempo_map && m.tempo_map.length ? m.tempo_map : [[0, m.bpm]]; let s = 0; for (let k = 0; k < tm.length; k++) { const b1 = k + 1 < tm.length ? tm[k + 1][0] : m.total_beats; s += ((b1 - tm[k][0]) * 60) / tm[k][1]; } return s; })(); });
    const need = {}, first = {}, mi0 = clamp(Math.floor(num(want.mi)), 0, MOV.length - 1);
    MOV.forEach((m, mi) => {
      const spb = 60 / Math.min(...(m.tempo_map || [[0, m.bpm]]).map((x) => x[1]));
      for (const [t, d, p] of m.notes) {
        need[p] = Math.max(need[p] || 0, Math.min(d * spb * 1.35 + 1.2, 12));
        if (mi === mi0 && (first[p] === undefined || t < first[p])) first[p] = t;
      }
    });
    const pitches = Object.keys(need).map(Number), kj = (p) => ({ m: p, need: need[p] });
    const k1 = pitches.filter((p) => first[p] !== undefined).sort((a, b) => first[a] - first[b]).map(kj), k2 = pitches.filter((p) => first[p] === undefined).sort((a, b) => a - b).map(kj);
    const sj = (kinds) => { const o = []; for (const k of kinds) for (let i = 0; i < COUNTS[k]; i++) if (!(BANK[k] && BANK[k][i])) o.push({ sfx: k, id: i }); return o; };
    const jobs = [...k1, ...sj(['stone', 'gravel', 'wood', 'snow', 'asphalt', 'soft', 'leaves']), ...k2, ...sj(['drip', 'bubble', 'trickle', 'bell', 'crow', 'wash', 'fall', 'clap'])].filter((j) => j.sfx || !KEYS[j.m]);
    loadKit(jobs);
  }
  const prep = (mi) => PREP[mi] || (PREP[mi] = prepare(MOV[mi], mi));
  function trimPrep(keep) { const ks = Object.keys(PREP); if (ks.length > 4) for (const k of ks) if (!keep.includes(+k)) delete PREP[k]; }

  /* ---------------------------------------------------------------- the graph */
  function makeIR(o) {
    const rate = ctx.sampleRate, n = Math.floor(rate * o.sec), b = ctx.createBuffer(2, n, rate), pre = Math.floor(o.pre * rate), hk = 1 - Math.exp((-2 * Math.PI * o.hp) / rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c); let lp = 0, hz0 = 0;
      for (let i = pre; i < n; i++) {
        const t = (i - pre) / rate, k = o.k1 + (o.k0 - o.k1) * Math.exp(-t / o.tauK);
        lp += (Math.random() * 2 - 1 - lp) * k; hz0 += (lp - hz0) * hk;
        d[i] = (lp - hz0) * Math.exp((-6.908 * t) / o.rt) * Math.min(1, t / o.build);
      }
      for (let r = 0; r < o.early; r++) d[pre + Math.floor((0.002 + Math.random() * o.spread) * rate)] += (Math.random() < 0.5 ? -1 : 1) * (0.5 - (r / o.early) * 0.35);
    }
    return b;
  }
  /* the piano's own body: a short, dense ring of the soundboard and case under the dry strings */
  function soundboard(sec) {
    const rate = ctx.sampleRate, n = Math.floor(rate * sec), b = ctx.createBuffer(2, n, rate);
    for (let c = 0; c < 2; c++) {
      const d = b.getChannelData(c);
      for (let k = 0; k < 260; k++) {
        const f = 70 * Math.pow(60, Math.random()), dec = 18 + f * 0.035, a = (Math.random() * 2 - 1) / Math.sqrt(1 + f / 600), w = (2 * Math.PI * f) / rate, ph = Math.random() * 6.28;
        for (let i = 0; i < n; i++) { const e = Math.exp((-dec * i) / rate); if (e < 1e-3) break; d[i] += a * e * Math.sin(w * i + ph); }
      }
    }
    return b;
  }
  function build() {
    const AC = opts.context ? function () { return opts.context; } : window.AudioContext || window.webkitAudioContext;
    ctx = new AC({ latencyHint: 'playback' });
    /* a phone call or a locked screen may suspend the context: come back when the page is touched or shown again */
    const wake = () => { if (ctx && enabled && ctx.state !== 'running' && !opts.context) { try { const r = ctx.resume(); if (r && r.catch) r.catch(() => {}); } catch (e) { /* fine */ } } };
    if (!opts.context && typeof document !== 'undefined') { document.addEventListener('visibilitychange', wake); addEventListener('pointerdown', wake, { passive: true }); addEventListener('keydown', wake, { passive: true }); }
    master = ctx.createGain(); master.gain.value = 0;
    comp = ctx.createDynamicsCompressor(); comp.threshold.value = -16; comp.ratio.value = 2.5; comp.attack.value = 0.02; comp.release.value = 0.3;
    lim = ctx.createDynamicsCompressor(); lim.threshold.value = -2; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.002; lim.release.value = 0.12;
    /* a last soft clip: linear to 0.85, then easing to 1.0, so that nothing can ever clip the output */
    clip = ctx.createWaveShaper(); const cv = new Float32Array(2049);
    for (let i = 0; i < cv.length; i++) { const x = (i / 1024 - 1), a = Math.abs(x), t = 0.85; cv[i] = Math.sign(x) * (a <= t ? a : t + (1 - t) * Math.tanh((a - t) / (1 - t))); }
    clip.curve = cv; clip.oversample = '2x';
    master.connect(comp); comp.connect(lim); lim.connect(clip); clip.connect(ctx.destination);
    /* the rooms: one convolver each, fed by sends from the piano, the outdoor sounds and the footsteps */
    ROOMS.forEach((r, i) => {
      /* a room is connected only while something is sent to it (a convolver fed by an automated zero-gain still costs the
         whole convolution); `on` / `off` track that */
      const inG = ctx.createGain(), conv = ctx.createConvolver(), ret = ctx.createGain();
      conv.connect(ret); ret.connect(master);
      room[r] = { inG, conv, ret, music: ctx.createGain(), amb: ctx.createGain(), self: ctx.createGain(), on: false, off: 0 };
      for (const k of ['music', 'amb', 'self']) { room[r][k].gain.value = 0; room[r][k].connect(inG); }
      if (!opts.noRooms) setTimeout(() => { if (ctx) room[r].conv.buffer = makeIR(ROOM_IR[r]); }, 30 + i * 70);
    });
    /* the piano: every movement plays into `music`; a little less top, a touch of body, the dry signal, and the sends */
    music = ctx.createGain(); music.gain.value = MUSIC;
    tone = ctx.createBiquadFilter(); tone.type = 'highshelf'; tone.frequency.value = 3000; tone.gain.value = -2;
    const body = ctx.createConvolver(); if (!opts.noBody) body.buffer = soundboard(0.09); bodyG = ctx.createGain(); bodyG.gain.value = 0.55;
    music.connect(tone); tone.connect(master); tone.connect(body); body.connect(bodyG); bodyG.connect(master);
    for (const r of ROOMS) tone.connect(room[r].music);
    /* the outdoors: water, bells, birds → high-pass → (muffled indoors) → master */
    out = ctx.createGain(); out.gain.value = 1;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 40; hp.Q.value = 0.7;
    outLP1 = ctx.createBiquadFilter(); outLP1.type = 'lowpass'; outLP1.frequency.value = 16000; outLP1.Q.value = 0.6;
    outLP2 = ctx.createBiquadFilter(); outLP2.type = 'lowpass'; outLP2.frequency.value = 16000; outLP2.Q.value = 0.6;
    outG = ctx.createGain(); outG.gain.value = AMB;
    out.connect(hp); hp.connect(outLP1); outLP1.connect(outLP2); outLP2.connect(outG); outG.connect(master);
    for (const r of ROOMS) outG.connect(room[r].amb);
    /* the waterfall: its grains overlap into one steady fall; its level and brightness follow how near it is */
    fallG = ctx.createGain(); fallG.gain.value = 0; fallLP = ctx.createBiquadFilter(); fallLP.type = 'lowpass'; fallLP.frequency.value = 2500; fallLP.Q.value = 0.5;
    fallBus = ctx.createGain(); fallBus.connect(fallLP); fallLP.connect(fallG); fallG.connect(out);
    /* the listener's own footsteps: in whatever room they stand in */
    selfBus = ctx.createGain(); selfBus.gain.value = AMB;
    const shp = ctx.createBiquadFilter(); shp.type = 'highpass'; shp.frequency.value = 60; shp.Q.value = 0.7;
    selfBus.connect(shp); shp.connect(master);
    for (const r of ROOMS) shp.connect(room[r].self);
  }
  function setT(p, i, v, tc) { if (Math.abs(v - LAST[i]) > 1e-3 * Math.max(1, Math.abs(v)) || !(LAST[i] === LAST[i])) { LAST[i] = v; p.setTargetAtTime(v, ctx.currentTime, tc); } }

  /* ---------------------------------------------------------------- playing a key */
  /* the key to play pitch m with: its own, or (while the kit is still being made) the nearest one, pitched */
  function keyFor(m) {
    if (KEYS[m]) return [m, 1];
    for (const d of [-1, 1, -2, 2]) if (KEYS[m + d]) return [m + d, Math.pow(2, -d / 12)];
    return null;
  }
  function strike(e, at, ep) {
    const kf = keyFor(e.m); if (!kf) return;
    const buf = keyBuf(kf[0]); if (!buf) return;
    const rate = kf[1], len = buf.duration / rate; if (len < 0.05) return;
    const src = ctx.createBufferSource(); src.buffer = buf; src.playbackRate.value = rate;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.5;
    const v2 = e.v * e.v; lp.frequency.value = Math.min(15000, (hz(e.m) * (3 + 10 * v2) + 900 + 5000 * v2) * ep.tone);
    const g = ctx.createGain(), amp = (0.05 + 0.95 * Math.pow(e.v, 1.6)) * ep.trim;
    g.gain.setValueAtTime(amp, at);
    let last = g; src.connect(lp); lp.connect(g);
    if (ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp((e.m - 62) / 70, -0.4, 0.4); g.connect(p); last = p; }
    last.connect(ep.bus);
    src.start(at);
    /* the damper comes down when the key is let go (slower in the bass, as the felt takes the long strings) */
    let end;
    if (e.d < len) { const tau = 0.06 + 0.24 * clamp((72 - e.m) / 48, 0, 1), up = at + e.d; g.gain.setValueAtTime(amp, up); g.gain.setTargetAtTime(0, up, tau); end = up + tau * 7; src.stop(end); }
    else { end = at + len; src.stop(end); }
    /* striking a key that is still sounding: the hammer stops the old vibration */
    const old = ep.active[e.m];
    if (old && old.end > at) { try { old.g.gain.cancelScheduledValues(at); old.g.gain.setTargetAtTime(0, at, 0.03); old.src.stop(at + 0.25); } catch (x) { /* fine */ } }
    ep.active[e.m] = { src, g, end };
    ep.voices.add(src); src.onended = () => { ep.voices.delete(src); try { src.disconnect(); lp.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
  }

  /* ---------------------------------------------------------------- the music: one epoch per movement */
  function newEpoch(mi, when, fadeIn, beat) {
    const p = prep(mi), mv = MOV[mi], bus = ctx.createGain(), outg = ctx.createGain();
    if (fadeIn) { bus.gain.value = 0; bus.gain.setValueCurveAtTime(CURVE_IN, when, fadeIn); } else bus.gain.value = 1;
    outg.gain.value = 1; bus.connect(outg); outg.connect(music);
    const off = beat > 0 ? p.T(beat) : 0; let c0 = 0; while (c0 < p.ev.length && p.ev[c0].t < off - 0.001) c0++;
    const ep = { mi, mv, p, bus, outg, t0: when, off, cur: c0, active: {}, voices: new Set(), dead: false, until: 0, tone: 0.95, trim: p.trim };
    timeline.push({ mi, t0: when - off, t1: when - off + p.len });
    if (timeline.length > 8) timeline.shift();
    trimPrep([mi, (mi + 1) % MOV.length]);
    return ep;
  }
  /* a movement ends: its last chord rings on in the room until it has died, then its voices are let go */
  function retire(ep, until) { ep.until = until; dying.push(ep); }
  function endEpoch(ep, when, fade) {
    if (ep.dead) return;
    ep.dead = true; ep.until = when + fade + 0.4;
    ep.outg.gain.setValueCurveAtTime(CURVE_OUT, when, fade);
    dying.push(ep);
  }
  function tick() {
    if (!live() || !MOV) return;
    const now = ctx.currentTime;
    for (let i = dying.length - 1; i >= 0; i--) {
      const ep = dying[i];
      if (now > ep.until) { for (const v of ep.voices) { try { v.stop(); } catch (x) { /* fine */ } } try { ep.bus.disconnect(); ep.outg.disconnect(); } catch (x) { /* fine */ } dying.splice(i, 1); }
    }
    if (!enabled || opts.noMusic) return;
    /* a movement asked for (the first one, or a jump): as soon as its first half minute of keys is there */
    if (want) {
      const p = prep(want.mi);
      if (ready(p.keys0)) {
        const when = now + (cur ? 0.25 : 0.15);
        if (cur) endEpoch(cur, when, XFADE);
        cur = newEpoch(want.mi, when, cur ? XFADE * 0.5 : 0, want.beat || 0); want = null; if (!tFirst) tFirst = performance.now() - t0Start;
      } else prioritize(p.keys0);
    }
    const horizon = now + AHEAD;
    for (let guard = 0; cur && guard < 6000; guard++) {
      const e = cur, ev = e.p.ev[e.cur];
      if (!ev) {
        /* the movement has been given to the clock: the next one follows its last sound by a few seconds (or waits for its keys) */
        const ni = (e.mi + 1) % MOV.length, np = prep(ni);
        if (!ready(np.keys0)) { prioritize(np.keys0); break; }
        const endT = e.t0 - e.off + e.p.len + GAP;
        retire(e, endT + 8); cur = newEpoch(ni, endT, 0, 0);
        continue;
      }
      const at = e.t0 + ev.t - e.off; if (at > horizon) break;
      e.cur++;
      if (at < now - 0.03) continue;                                    /* the page slept: do not pile up late notes */
      strike(ev, Math.max(at, now + 0.004), e);
    }
  }
  /* the movement being heard: it changes as the silence before the next one begins */
  function heard(now) {
    let r = null;
    for (const t of timeline) if (t.t0 - 2.5 <= now) r = t;
    return r ? MOV[r.mi] : null;
  }

  /* ---------------------------------------------------------------- the natural sounds */
  function grain(kind, dest, at, gain, rate, pan, id, fc) {
    if (id === undefined || id === null) id = pick(kind);
    if (id < 0) return false;
    const b = bufOf(kind, id); if (!b) return false;
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = rate;
    const g = ctx.createGain(); g.gain.value = gain;
    let lp = null; if (fc) { lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = fc; lp.Q.value = 0.5; src.connect(lp); lp.connect(g); } else src.connect(g);
    let last = g;
    if (pan && ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp(pan, -1, 1); g.connect(p); last = p; }
    last.connect(dest); src.start(at);
    src.onended = () => { try { src.disconnect(); if (lp) lp.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
    return true;
  }
  const logn = (s) => Math.exp(s * (Math.random() + Math.random() + Math.random() - 1.5) * 0.8);   /* a gentle lognormal wobble */
  const sgn = () => (Math.random() < 0.5 ? -1 : 1);
  /* one stroke of a temple bell, a long way off: it arrives dist / 343 s late, darker and softer the farther it is; it comes
     from the side it is on. The three bells (large to small) are told apart by the id. */
  function bellStrike(o = {}) {
    const dist = clamp(num(o.dist, 300), 5, 3000), az = num(o.az, 0), idn = idNum(o.id), id = idn % 3;
    const b = bufOf('bell', id); if (!b) return false;
    const at = (ctx.currentTime || 0) + 0.03 + (o.delay === false ? 0 : dist / SPEED_OF_SOUND) + num(o.later);
    const src = ctx.createBufferSource(); src.buffer = b; src.playbackRate.value = 1 + 0.004 * (((idn * 7) % 5) - 2);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 0.5;
    lp.frequency.value = clamp(15000 * Math.exp(-dist / 330), 900, 15000) * (0.78 + 0.22 * Math.cos(az));
    const g = ctx.createGain(); g.gain.value = (o.gain ?? 1) * G.bell * Math.pow(clamp(70 / (dist + 30), 0.05, 1.2), 0.6); src.connect(lp); lp.connect(g);
    let last = g; if (ctx.createStereoPanner) { const p = ctx.createStereoPanner(); p.pan.value = clamp(Math.sin(az) * 0.85, -1, 1); g.connect(p); last = p; }
    last.connect(out); src.start(at);
    if (opts.debug) strikes.push({ at: +at.toFixed(2), dist, id, az, gain: g.gain.value });
    src.onended = () => { try { src.disconnect(); lp.disconnect(); g.disconnect(); if (last !== g) last.disconnect(); } catch (x) { /* fine */ } };
    return at;
  }
  /* each bell within hearing is struck now and then: the nearest every 70-150 s, the others less often (a farther bell and a
     later one in the order wait longer); a strike is sometimes followed by a second or third, twenty-odd seconds apart */
  function bellsUpdate(list, k) {
    if (!Array.isArray(list)) return;
    const sorted = list.filter((b) => b && typeof b === 'object').slice().sort((a, b) => num(a.dist, 1e9) - num(b.dist, 1e9));
    sorted.forEach((b, rank) => {
      const id = b.id ?? rank; let st = bells.get(id);
      if (!st) { st = { next: clock + 6 + 40 * Math.random(), n: 0, seen: clock }; bells.set(id, st); }
      st.seen = clock;
      if (clock < st.next) return;
      if (clock - lastBell < 14) { st.next = clock + 6 + 10 * Math.random(); return; }       /* not two at once */
      lastBell = clock;
      const dist = num(b.dist, 300), strikes = Math.random() < 0.22 ? 2 + (Math.random() < 0.4 ? 1 : 0) : 1;
      let later = 0;
      for (let i = 0; i < strikes; i++) { bellStrike({ dist, az: b.az, id, gain: (1 - 0.1 * i) * k, later }); later += 20 + 8 * Math.random(); }
      st.next = clock + (70 + 80 * Math.random()) * (1 + 0.6 * rank) * (1 + dist / 2400) + later;
    });
    if (bells.size > 16) for (const [id, st] of bells) if (clock - st.seen > 300) bells.delete(id);
  }

  /* ---------------------------------------------------------------- the frame */
  function update(dt, s) {
    if (!ctx || !started || !MOV || !s) return;
    dt = clamp(num(dt, 0.016), 0, 0.25); clock += dt;
    const now = ctx.currentTime;
    mode = s.mode === 'walk' || s.mode === 'fly' || s.mode === 'title' ? s.mode : 'walk';
    interior = typeof s.interior === 'string' && INTERIORS[s.interior] ? s.interior : null;
    const camZ = num(s.camZ, 2), walk = clamp(num(s.walkSpeed), 0, 8), season = s.season === 1 ? 1 : 0, surf = num(s.surf, 0);
    const water = clamp(num(s.water), 0, 1), fall = clamp(num(s.fall), 0, 1), weir = s.weir === undefined ? clamp((water - 0.55) / 0.45, 0, 1) * 0.7 : clamp(num(s.weir), 0, 1);
    gnd = 1 - sstep(30, 100, camZ);
    if (!live() || !enabled) return;

    /* slow things, ten times a second: the room, the muffling */
    if (now - lastSlow > 0.1) {
      lastSlow = now;
      const rk = interior || 'out', M = SEND[rk];
      roomKey = rk;
      muf += ((interior ? 1 : 0) - muf) * (1 - Math.exp(-0.1 / 0.6));
      interiorK = muf;
      const f = 600 * Math.pow(16000 / 600, 1 - muf);
      setT(outLP1.frequency, 0, f, 0.06); setT(outLP2.frequency, 1, f, 0.06);
      setT(outG.gain, 2, AMB * lerp(1, 0.32, muf), 0.12);
      for (let i = 0; i < ROOMS.length; i++) {
        const R = room[ROOMS[i]], wantRoom = M.music[i] + M.amb[i] + M.self[i] > 0;
        if (wantRoom) { R.off = 0; if (!R.on) { R.inG.connect(R.conv); R.on = true; } }
        else if (R.on) { if (!R.off) R.off = now; else if (now - R.off > 4.5) { try { R.inG.disconnect(R.conv); } catch (e) { /* fine */ } R.on = false; R.off = 0; } }
        setT(R.music.gain, 3 + i, M.music[i], 0.7); setT(R.amb.gain, 8 + i, M.amb[i], 0.7); setT(R.self.gain, 13 + i, M.self[i], 0.7);
      }
      setT(tone.gain, 18, -2 - 3 * interiorK, 0.8); setT(music.gain, 19, MUSIC * M.dry, 0.8);
    }
    tick();
    /* a new movement for the page's label */
    if (opts.onMovement) { const h = heard(now); if (h && h.index !== lastIdx) { lastIdx = h.index; try { opts.onMovement({ index: h.index, id: h.id, title: h.title, title_ja: h.title_ja }); } catch (e) { /* the page's affair */ } } }
    if (opts.noAmb) return;

    const gn = gnd, titleK = mode === 'title' ? 0.55 : 1;
    /* water: a stream's drops, gurgles and bubbles; the wash of a weir — only where there is water */
    const w = water * gn * titleK;
    if (w > 0.02) {
      if (Math.random() < (0.2 + 0.9 * w) * dt) grain('trickle', out, now + 0.02, G.trickle * 0.8 * w * logn(0.45), 0.9 + 0.25 * Math.random(), sgn() * (0.2 + 0.55 * Math.random()));
      if (Math.random() < (0.15 + 0.75 * w) * dt) grain('drip', out, now + 0.02, G.drip * 0.8 * w * logn(0.5), 0.8 + 0.5 * Math.random(), sgn() * Math.random() * 0.7);
      if (Math.random() < (0.05 + 0.3 * w) * dt) grain('bubble', out, now + 0.02, G.bubble * 0.7 * w * logn(0.5), 0.85 + 0.4 * Math.random(), sgn() * Math.random() * 0.7);
    }
    const wk = weir * gn * titleK;
    if (wk > 0.05 && Math.random() < (0.12 + 0.3 * wk) * dt) grain('wash', out, now + 0.02, G.wash * wk * logn(0.35), 0.92 + 0.16 * Math.random(), 0);
    /* a small waterfall: many drops, steadily (its grains overlap by their fades); its level follows how near it is */
    const fk = fall * gn * titleK;
    if (fk > 0.02) {
      if (fallNext < now) fallNext = now + 0.03;
      while (fallNext < now + 0.7) { grain('fall', fallBus, fallNext, 1, 0.98 + 0.04 * Math.random(), 0); fallNext += 2.7; }
    } else if (fallNext > 0 && fallNext < now) fallNext = 0;
    setT(fallG.gain, 20, G.fall * Math.pow(fk, 1.2), 0.25); setT(fallLP.frequency, 21, 1800 + 8500 * fk, 0.25);

    /* the listener's own steps: about 1.8 a second at walking pace, quicker running; the ground decides the sound */
    if (mode === 'walk' && walk > 0.12 && gn > 0.2) {
      const sps = walk < 1.7 ? walk / 0.77 : 2.2 + (walk - 1.7) * 0.5;
      stepPhase += sps * dt;
      for (let n = 0; stepPhase >= 1 && n < 2; n++) {
        stepPhase -= 1; foot ^= 1;
        let sf = interior ? SURF[255] : SURF[surf] || ['stone', 0.7, 1];
        if (season === 1 && !interior && !NOSNOW[surf]) sf = ['snow', 0.9, 1];
        const run = walk > 2.6, gw = (0.8 + 0.2 * Math.min(1, walk / 1.6)) * (run ? 1.3 : 1);
        grain(sf[0], selfBus, now + 0.01, G[sf[0]] * sf[1] * gw * logn(0.3), (foot ? 0.97 : 1.03) * (0.97 + 0.06 * Math.random()) * sf[2] * (run ? 1.08 : 1), (foot ? 1 : -1) * 0.09);
      }
      if (stepPhase > 1) stepPhase = 0;
    } else stepPhase = Math.max(stepPhase, 0.85);

    /* a crow, now and then, far off */
    crowT -= dt;
    if (crowT <= 0) { crowT = 150 + 250 * Math.random(); if (!interior && gn > 0.2 && mode !== 'title') grain('crow', out, now + 0.05, G.crow * gn * logn(0.3), 0.92 + 0.16 * Math.random(), sgn() * (0.3 + 0.5 * Math.random()), null, 2800); }

    /* the bells of the temples within hearing */
    bellsUpdate(s.bells, lerp(0.55, 1, gn));
  }

  /* ---------------------------------------------------------------- the public face */
  /* stop an automation where it is, without the jump that cancelScheduledValues would leave */
  function hold(p, t) { if (p.cancelAndHoldAtTime) p.cancelAndHoldAtTime(t); else { const v = p.value; p.cancelScheduledValues(t); p.setValueAtTime(v, t); } }
  function applyEnabled() {
    if (!ctx) return;
    const now = ctx.currentTime;
    if (opts.context) { master.gain.value = enabled ? MASTER : 0; return; }
    if (enabled) { try { if (ctx.state === 'suspended') { const r = ctx.resume(); if (r && r.catch) r.catch(() => {}); } } catch (e) { /* fine */ } hold(master.gain, now); master.gain.setTargetAtTime(MASTER, now, 0.5); }
    else { hold(master.gain, now); master.gain.setTargetAtTime(0, now, 0.2); setTimeout(() => { if (!enabled && ctx && ctx.suspend) { try { ctx.suspend(); } catch (e) { /* fine */ } } }, 1400); }
  }
  async function start() {
    if (started) { if (enabled) applyEnabled(); return; }
    started = true; if (enabled === null) enabled = true;
    try { build(); } catch (e) { console.warn('audio unavailable', e); ctx = null; started = false; return; }
    t0Start = performance.now();
    try { if (!opts.context) await Promise.race([ctx.resume(), new Promise((r) => setTimeout(r, 400))]); } catch (e) { /* fine */ }
    applyEnabled();
    /* load the score and start rendering after this call has returned, so the click that began it is not held up */
    await new Promise((r) => setTimeout(r, 0));
    if (!ctx) return;
    try {
      const score = opts.score || (await (await fetch(opts.scoreUrl || 'data/goldberg.json')).json());
      setup(score);
    } catch (e) { console.warn('audio: the score failed', e); return; }
    if (!opts.context) timer = setInterval(tick, 80);
  }
  function setEnabled(on) {
    enabled = !!on;
    if (started && ctx) applyEnabled(); else if (on && !started) start();
  }
  function jump(i, o = {}) {
    if (!MOV) { want = { mi: typeof i === 'string' ? i : num(i), beat: num(o.beat), fade: 0 }; return false; }
    const mi = typeof i === 'string' ? MOV.findIndex((m) => m.id === i) : clamp(Math.floor(num(i)), 0, MOV.length - 1);
    if (mi < 0) return false;
    want = { mi, beat: num(o.beat), fade: XFADE }; return true;
  }
  const curIndex = () => { const h = ctx && heard(ctx.currentTime); return h ? h.index : cur ? cur.mi : want ? want.mi : 0; };
  const COUNTS = synthKit().COUNTS;
  const api = {
    start, setEnabled, update, jump,
    next: () => jump((curIndex() + 1) % (MOV ? MOV.length : 32)),
    prev: () => jump((curIndex() + (MOV ? MOV.length : 32) - 1) % (MOV ? MOV.length : 32)),
    movements: () => (MOV || []).map((m) => ({ index: m.index, id: m.id, title: m.title, title_ja: m.title_ja, sec: +m.sec.toFixed(1) })),
    nowPlaying: () => { const h = ctx && MOV ? heard(ctx.currentTime) : null; return h ? { index: h.index, id: h.id, title: h.title, title_ja: h.title_ja } : { index: -1, id: '', title: '', title_ja: '' }; },
    play: (kind, o = {}) => { if (!ctx || !COUNTS[kind]) return false; if (kind === 'bell') return !!bellStrike(Object.assign({ delay: false }, o)); return grain(kind, o.self ? selfBus : out, o.at ?? ctx.currentTime + 0.02, (o.gain ?? 1) * G[kind], o.rate ?? 1, o.pan ?? 0, o.id); },
    bell: (o = {}) => !!ctx && !!bellStrike(o),
    whenReady: () => new Promise((res) => { const chk = () => { if (MOV && KIT.done >= KIT.total) res(KIT); else setTimeout(chk, 40); }; chk(); }),
    kit: KIT,
    /* for debugging: what is playing and how far the kit has got */
    info: () => ({
      started, enabled, state: ctx && ctx.state, movement: cur && cur.mv.id, index: cur && cur.mi, want: want && want.mi, room: roomKey, kit: KIT.done + '/' + KIT.total, sfx: KIT.sfx,
      worker: fallbackOn ? 'main thread' : worker ? 'worker' : 'done', kitMs: tKit ? Math.round(tKit) : null, firstNoteMs: tFirst ? Math.round(tFirst) : null, cpuMs: Math.round(KIT.cpu), gnd: +gnd.toFixed(2), muffle: +muf.toFixed(2),
    }),
  };
  if (opts.debug) api._dbg = { get ctx() { return ctx; }, get comp() { return comp; }, get lim() { return lim; }, get master() { return master; }, get out() { return out; }, tick, prep, get cur() { return cur; }, get MOV() { return MOV; }, KIT, KEYS, BANK, strike, bellStrike, timeline, G, SURF, strikes, bells };
  return api;
}

/* ====================================================================================================
   OFFLINE — the whole engine into an OfflineAudioContext (a test; a promotional film's sound)
   ==================================================================================================== */
/* renderOffline({ sec, rate, movement, beat, music, amb, state: s | (t) => s, step, score, kit, settle, onFrame(A, t) }) → { buffer, A }
   The engine is driven as the page drives it: update(step, state(t)) every `step` seconds (0.25; 1/60 for footsteps). */
export async function renderOffline(o = {}) {
  const rate = o.rate || 48000, sec = o.sec || 20, step = o.step || 0.25, oac = new OfflineAudioContext(2, Math.ceil(sec * rate), rate);
  const A = createAudio({ context: oac, debug: true, score: o.score, kit: o.kit, noMusic: o.music === false, noAmb: o.amb === false, startMovement: o.movement ?? 0, startBeat: o.beat || 0, noRooms: o.rooms === false, scoreUrl: o.scoreUrl });
  await A.start(); await A.whenReady(); await sleep(o.settle ?? 600);     /* (the rooms' impulse responses are made a moment after start) */
  for (let i = 0; i * step < sec; i++) { const t = i * step; oac.suspend(t).then(() => { A.update(step, typeof o.state === 'function' ? o.state(t) : o.state || { mode: 'walk' }); if (o.onFrame) o.onFrame(A, t); oac.resume(); }); }
  const buffer = await oac.startRendering();
  return { buffer, A };
}
/* the seconds at a beat of a movement as the pianist plays it (the phrasing included): for cutting a film on the bars */
export function beatTimes(mv, idx = 0) { const p = prepare(mv, idx); return { T: p.T, len: p.len }; }
/* a 16-bit PCM WAV of an AudioBuffer */
export function wavBytes(buf) {
  const n = buf.length, nc = buf.numberOfChannels, ch = []; for (let c = 0; c < nc; c++) ch.push(buf.getChannelData(c));
  const dv = new DataView(new ArrayBuffer(44 + n * nc * 2)), str = (p, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(p + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); dv.setUint32(4, 36 + n * nc * 2, true); str(8, 'WAVEfmt '); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, nc, true);
  dv.setUint32(24, buf.sampleRate, true); dv.setUint32(28, buf.sampleRate * nc * 2, true); dv.setUint16(32, nc * 2, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, n * nc * 2, true);
  for (let i = 0, p = 44; i < n; i++) for (let c = 0; c < nc; c++, p += 2) dv.setInt16(p, clamp(Math.round(ch[c][i] * 32767), -32768, 32767), true);
  return new Uint8Array(dv.buffer);
}
