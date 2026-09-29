// Mixdown: voice (sequential by construction – nothing can overlap), BGM ducked under speech, sound effects that
// follow the picture; then loudness-normalised with ffmpeg. All stems are written out so the QA stage can inspect them.
import path from 'node:path';
import fs from 'node:fs';
import { run, ensureDir, log, round, rng } from '../util.mjs';
import { readWav, writeWav, resample, makeBuffer, mixInto, toMono, db, fromDb } from './wav.mjs';
import { SFX, sfxForOp } from './sfx.mjs';
import { SR, place, newBus, biquad, rms } from './synth.mjs';

const FFMPEG = process.env.FFMPEG || 'ffmpeg';

/** Optional tempo change for a whole line (time-stretch, pitch preserved). */
async function tempo(file, k, out) {
  if (Math.abs(k - 1) < 0.002) return file;
  const parts = [];
  let r = k;
  while (r > 2) { parts.push(2); r /= 2; }
  while (r < 0.5) { parts.push(0.5); r /= 0.5; }
  parts.push(r);
  await run(FFMPEG, ['-y', '-loglevel', 'error', '-i', file, '-filter:a', parts.map((x) => `atempo=${x.toFixed(5)}`).join(','), '-ar', String(SR), out], { check: true });
  return out;
}

/** SFX plan from the timeline: scene changes and on-screen cues → [{t, name, gain, seed}] (sparse, ≥0.22 s apart). */
export function planSFX(timeline) {
  const ev = [];
  for (const sc of timeline.scenes) ev.push({ t: sc.start + 0.02, ...sfxForOp('scene') });
  ev.push({ t: timeline.outro.start + 0.02, ...sfxForOp('scene') });
  ev.push({ t: 0.2, name: 'ding', gain: 0.5 });
  for (const c of timeline.cues) {
    const s = sfxForOp(c.op, { long: true, dur: 0.6 });
    if (s) ev.push({ t: c.t + 0.04, ...s });
  }
  ev.sort((a, b) => a.t - b.t);
  const out = [];
  for (const e of ev) if (!out.length || e.t - out.at(-1).t >= 0.22) out.push(e);
  return out.map((e, i) => ({ ...e, seed: i + 1 }));
}

/** Smoothed voice-activity curve at `ctrl` Hz → Float32Array in 0..1. */
function activityCurve(lines, duration, ctrl = 200, pre = 0.12, post = 0.3, attack = 0.1, release = 0.55) {
  const n = Math.ceil(duration * ctrl), raw = new Float32Array(n);
  for (const l of lines) {
    const a = Math.max(0, Math.floor((l.start - pre) * ctrl)), b = Math.min(n, Math.ceil((l.end + post) * ctrl));
    for (let i = a; i < b; i++) raw[i] = 1;
  }
  const out = new Float32Array(n);
  const ka = Math.exp(-1 / (attack * ctrl)), kr = Math.exp(-1 / (release * ctrl));
  let y = 0;
  for (let i = 0; i < n; i++) { const k = raw[i] > y ? ka : kr; y = k * y + (1 - k) * raw[i]; out[i] = y; }
  return out;
}

export async function mixdown({ timeline, voice, bgm, outDir, speed = 1, cast, targetLufs = -16, duckDb = 5, soloBoostDb = 4, bgmBelowVoiceDb = 10, sfxBelowVoiceDb = 14 }) {
  ensureDir(outDir);
  const dur = timeline.duration;
  const lines = [...timeline.scenes.flatMap((s) => s.lines), ...timeline.outro.lines];

  // ---- voice bus
  const vbus = makeBuffer(SR, dur + 1, 2);
  for (const ln of lines) {
    const rec = voice[ln.id];
    const f = await tempo(rec.file, speed, path.join(outDir, `tempo-${ln.id}.wav`));
    const a = resample(readWav(f), SR);
    mixInto(vbus, a, ln.start, 1, ln.who === 'host' ? -0.14 : 0.14);
  }
  writeWav(path.join(outDir, 'voice-raw.wav'), vbus);
  await run(FFMPEG, ['-y', '-loglevel', 'error', '-i', path.join(outDir, 'voice-raw.wav'), '-af',
    'highpass=f=90,equalizer=f=240:t=q:w=1:g=-1.5,equalizer=f=3200:t=q:w=1.1:g=2.5,acompressor=threshold=0.085:ratio=2.4:attack=6:release=140:makeup=2.2:knee=4,alimiter=limit=0.9:level=disabled',
    '-ar', String(SR), path.join(outDir, 'voice.wav')], { check: true });
  const V = readWav(path.join(outDir, 'voice.wav'));
  const nAll = Math.round(dur * SR);
  const vch = V.channels.map((c) => c.subarray(0, nAll));

  // reference level: RMS while someone speaks
  const act = activityCurve(lines, dur);
  let vs = 0, vn = 0;
  for (let i = 0; i < nAll; i += 8) { const a = act[Math.min(act.length - 1, Math.floor((i / SR) * 200))]; if (a > 0.9) { vs += vch[0][i] * vch[0][i] + vch[1][i] * vch[1][i]; vn += 2; } }
  const vRms = Math.sqrt(vs / Math.max(1, vn));

  // ---- BGM with ducking
  const bch = bgm.channels.map((c) => c.slice(0, nAll));
  const bRms = Math.max(1e-6, rms(bch));
  const bgmGain = (vRms * fromDb(-bgmBelowVoiceDb)) / bRms;
  for (let c = 0; c < 2; c++) {
    const arr = bch[c];
    for (let i = 0; i < arr.length; i++) {
      const a = act[Math.min(act.length - 1, Math.floor((i / SR) * 200))];
      arr[i] *= bgmGain * fromDb(-duckDb * a + soloBoostDb * (1 - a));
    }
  }

  // ---- SFX
  const sbus = newBus(dur + 1);
  const plan = planSFX(timeline);
  const r = rng('sfx-pan');
  for (const e of plan) {
    const gen = SFX[e.name];
    if (!gen) continue;
    place(sbus, gen(e.seed, SR, e.dur), Math.round(e.t * SR), e.gain, r.range(-0.25, 0.25));
  }
  // effects are sparse, so scale by peak: the loudest effect sits sfxBelowVoiceDb under the voice's peak
  const peakOf = (chs) => chs.reduce((m, c) => { let p = m; for (let i = 0; i < nAll && i < c.length; i++) { const a = Math.abs(c[i]); if (a > p) p = a; } return p; }, 0);
  const sfxGain = (peakOf(vch) * fromDb(-sfxBelowVoiceDb)) / Math.max(peakOf(sbus), 1e-6);
  for (const ch of sbus) for (let i = 0; i < ch.length; i++) ch[i] *= sfxGain;
  const sch = sbus.map((c) => c.slice(0, nAll));

  const stems = { voice: { rate: SR, channels: vch }, bgm: { rate: SR, channels: bch }, sfx: { rate: SR, channels: sch } };
  for (const [k, a] of Object.entries(stems)) writeWav(path.join(outDir, `stem-${k}.wav`), a);

  // ---- sum, then loudness normalisation (two-pass loudnorm)
  const sum = [new Float32Array(nAll), new Float32Array(nAll)];
  for (let c = 0; c < 2; c++) for (let i = 0; i < nAll; i++) sum[c][i] = vch[c][i] + bch[c][i] + sch[c][i];
  const prePath = path.join(outDir, 'master-pre.wav');
  writeWav(prePath, { rate: SR, channels: sum }, 32);
  const I = targetLufs, TP = -1.5, LRA = 9;
  const first = await run(FFMPEG, ['-hide_banner', '-nostats', '-i', prePath, '-af', `loudnorm=I=${I}:TP=${TP}:LRA=${LRA}:print_format=json`, '-f', 'null', '-']);
  const j = first.stderr.match(/\{[\s\S]*?\}/g)?.pop();
  const m = j ? JSON.parse(j) : null;
  const masterPath = path.join(outDir, 'master.wav');
  const lnorm = m
    ? `loudnorm=I=${I}:TP=${TP}:LRA=${LRA}:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`
    : `loudnorm=I=${I}:TP=${TP}:LRA=${LRA}`;
  await run(FFMPEG, ['-y', '-loglevel', 'error', '-i', prePath, '-af', `${lnorm},alimiter=limit=0.89:level=disabled`, '-ar', String(SR), '-c:a', 'pcm_s16le', masterPath], { check: true });
  fs.rmSync(prePath, { force: true });
  for (const ln of lines) fs.rmSync(path.join(outDir, `tempo-${ln.id}.wav`), { force: true });
  log('mix', `voice rms ${db(vRms).toFixed(1)} dB, bgm gain ${db(bgmGain).toFixed(1)} dB, ${plan.length} sfx; loudnorm input ${m?.input_i} LUFS → ${I}`);
  return { masterPath, plan, stats: { voiceRmsDb: round(db(vRms), 1), bgmGainDb: round(db(bgmGain), 1), sfx: plan.length, measured: m } };
}
