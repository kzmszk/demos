// The production pipeline from a finished script to an MP4. Each stage writes its artifacts under <runDir> and can be
// re-run on its own; TTS results are cached globally, so changing only the picture (or the music) is cheap.
import path from 'node:path';
import fs from 'node:fs';
import { ROOT, run, ensureDir, readJSON, writeJSON, writeText, exists, log, round, clamp, rng } from './util.mjs';
import { synthesizeLines, resolveAnchors } from './tts/index.mjs';
import { compileTimeline, DEFAULT_CFG } from './timeline.mjs';
import { compose, scoreToMidi } from './audio/composer.mjs';
import { renderBGM } from './audio/bgm.mjs';
import { writeWav } from './audio/wav.mjs';
import { mixdown } from './audio/mixer.mjs';
import { buildProject } from './visual/compose.mjs';

const HF = path.join(ROOT, 'node_modules', '.bin', 'hyperframes');
const HF_ENV = { ...process.env, HYPERFRAMES_NO_TELEMETRY: '1', DO_NOT_TRACK: '1' };

export const linesOf = (episode) => [...episode.scenes.flatMap((s) => s.lines), ...(episode.outro?.lines || [])];
export const cuesOf = (episode) => episode.scenes.flatMap((s) => (s.cues || []).map((c) => ({ ...c, scene: s.id })));

// ---- fit: choose a global speed factor so that speech + gaps + credits equal the requested length ------------
export function fitSpeed({ episode, voice, targetSec, cfg = {} }) {
  const c = { ...DEFAULT_CFG, ...cfg };
  const base = compileTimeline({ episode, voice, targetSec: 0, speed: 1, cfg });
  const speech = base.stats.speechSec;
  const fixedNoTail = base.stats.natural - c.outroTailMin - speech;
  const need = (tail) => speech / (targetSec - 0.03 - fixedNoTail - tail);
  const kLow = need(c.outroTailMin), kHigh = need(c.outroTailMax);
  let k = 1, why = 'natural length fits (credits absorb the slack)';
  if (kLow > 1) { k = kLow; why = 'speeding up to fit'; } else if (kHigh < 1) { k = kHigh; why = 'slowing down to fill'; }
  const ok = k >= 0.92 && k <= 1.09;
  return { k: round(k, 4), ok, why, natural: base.stats.natural, speechSec: speech, kRange: [round(kLow, 3), round(kHigh, 3)],
    advice: ok ? null : k > 1.09 ? `台本が長すぎます（あと約${Math.round((speech - speech / 1.1) * 6.6)}文字ほど減らす）` : `台本が短すぎます（あと約${Math.round((speech / 0.92 - speech) * 6.6)}文字ほど足す）` };
}

// ---- stages ----------------------------------------------------------------------------------------------
export async function stageVoice({ episode, series, runDir, provider }) {
  const lines = linesOf(episode);
  const voice = await synthesizeLines({ lines, cast: series.cast, provider, outDir: path.join(runDir, 'voice') });
  await resolveAnchors({ provider, cast: series.cast, lines, records: voice, cues: cuesOf(episode) });
  writeJSON(path.join(runDir, 'voice.json'), Object.fromEntries(Object.entries(voice).map(([k, v]) => [k, { ...v, segs: undefined }])));
  return voice;
}

export function stageTimeline({ episode, voice, targetSec, runDir, cfg, speedRange = [0.92, 1.09] }) {
  const fit = fitSpeed({ episode, voice, targetSec, cfg });
  // when the script is not to be rewritten (a voice swap), accept whatever tempo change is needed within a wider range
  const speed = Math.min(speedRange[1], Math.max(speedRange[0], fit.k));
  log('fit', `speed ×${fit.k}${speed !== fit.k ? ` → limited to ×${speed}` : ''} (${fit.why}); natural ${fit.natural}s of ${targetSec}s`);
  const { timeline, stats } = compileTimeline({ episode, voice, targetSec, speed, cfg });
  writeJSON(path.join(runDir, 'timeline.json'), { ...timeline, speed });
  writeJSON(path.join(runDir, 'fit.json'), { ...fit, usedSpeed: speed, stats });
  return { timeline, speed, fit, stats };
}

export function stageMusic({ episode, timeline, series, runDir, seed, style }) {
  const lineSpans = [...timeline.scenes.flatMap((s) => s.lines), ...timeline.outro.lines];
  const voiceLoad = (a, b) => {
    let cov = 0;
    for (const l of lineSpans) cov += Math.max(0, Math.min(b, l.end + 0.2) - Math.max(a, l.start - 0.1));
    return clamp(cov / (b - a), 0, 1);
  };
  // the style sets the feel of the music: tempo range and how lively the arrangement is
  const [bpmLo, bpmHi] = style?.music?.bpm || [78, 88];
  const bias = style?.music?.energyBias || 0;
  const bpmHint = bpmLo + (bpmHi - bpmLo) * rng(`bpm:${seed}`)();
  const sections = [
    { t0: 0, t1: timeline.intro.end, label: 'intro', mood: 'warm', energy: 0.2 },
    ...timeline.scenes.map((s) => {
      const e = episode.scenes.find((x) => x.id === s.id);
      return { t0: s.start, t1: s.end, label: s.id, mood: e.mood || 'warm', energy: clamp((e.energy ?? 0.45) + bias, 0, 1) };
    }),
    { t0: timeline.outro.start, t1: timeline.duration, label: 'outro', mood: 'resolve', energy: 0.22 },
  ];
  const score = compose({ duration: timeline.duration, sections, seed: seed ?? series.id, key: series.music?.key || 'F', bpm: bpmHint, voiceLoad, introSec: timeline.intro.end, outroSec: timeline.duration - timeline.outro.start, title: episode.title });
  const dir = ensureDir(path.join(runDir, 'audio'));
  writeJSON(path.join(dir, 'score.json'), { ...score, notes: undefined, noteCounts: Object.fromEntries(Object.entries(score.notes).map(([k, v]) => [k, v.length])) });
  fs.writeFileSync(path.join(dir, 'score.mid'), scoreToMidi(score));
  const audio = renderBGM(score);
  writeWav(path.join(dir, 'bgm.wav'), audio);
  log('music', `${score.bpm} bpm, ${score.bars} bars in ${score.key}, ${score.stats.notes} notes`);
  return { score, audio };
}

export async function stageMix({ timeline, voice, bgm, runDir, speed, series }) {
  const dir = ensureDir(path.join(runDir, 'audio'));
  const r = await mixdown({ timeline, voice, bgm, outDir: dir, speed, cast: series.cast });
  writeJSON(path.join(dir, 'mix.json'), { plan: r.plan, stats: r.stats });
  return r;
}

export async function stageCompose({ episode, timeline, series, runDir, audioFile, episodeNo, style, label }) {
  const projectDir = path.join(runDir, 'project');
  fs.rmSync(path.join(projectDir, 'assets'), { recursive: true, force: true });
  return buildProject({ episode, timeline, series, runDir, projectDir, audioFile, episodeNo, style, label });
}

/** Run a hyperframes CLI command in the project directory. */
export function hyperframes(args, { cwd, onLine } = {}) {
  return run(HF, args, { cwd, env: HF_ENV, onStdout: (d) => onLine?.(d.toString()), onStderr: (d) => onLine?.(d.toString()) });
}

export async function stageCheck({ runDir }) {
  const projectDir = path.join(runDir, 'project');
  const r = await hyperframes(['check'], { cwd: projectDir });
  const out = (r.stdout + r.stderr).replace(/\x1b\[[0-9;]*m/g, '');
  writeText(path.join(runDir, 'check.log'), out);
  return { code: r.code, out };
}

export async function stageRender({ runDir, quality = 'looks', out, fps = 30, workers }) {
  const projectDir = path.join(runDir, 'project');
  const output = out || path.join(runDir, 'video.mp4');
  const args = ['render', '--quality', quality, '--output', output, '--fps', String(fps)];
  if (workers) args.push('--workers', String(workers));
  let last = 0;
  const r = await hyperframes(args, { cwd: projectDir, onLine: (s) => { const m = s.match(/(\d+)%/); if (m && +m[1] >= last + 10) { last = +m[1]; log('render', `${m[1]}%`); } } });
  writeText(path.join(runDir, 'render.log'), (r.stdout + r.stderr).replace(/\x1b\[[0-9;]*m/g, ''));
  if (r.code !== 0 || !exists(output)) throw new Error(`hyperframes render failed (exit ${r.code}); see ${path.join(runDir, 'render.log')}`);
  return output;
}

/** Everything after the script exists: voice → timeline → music → mix → project. */
export async function buildFromScript({ episode, series, runDir, targetSec = 180, provider = 'voicevox', episodeNo = 1, seed, cfg, style }) {
  ensureDir(runDir);
  writeJSON(path.join(runDir, 'script.json'), episode);
  const voice = await stageVoice({ episode, series, runDir, provider });
  const { timeline, speed, fit, stats } = stageTimeline({ episode, voice, targetSec, runDir, cfg });
  if (!fit.ok) log('fit', `WARNING: ${fit.advice}`);
  const music = stageMusic({ episode, timeline, series, runDir, seed, style });
  const mix = await stageMix({ timeline, voice, bgm: music.audio, runDir, speed, series });
  const project = await stageCompose({ episode, timeline, series, runDir, audioFile: mix.masterPath, episodeNo, style });
  return { voice, timeline, speed, fit, stats, music, mix, project };
}
