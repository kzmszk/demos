// A video made on request (a theme, a length and optional notes typed by a visitor): the same pipeline as `make`, with three differences.
//   1. The input is untrusted. It is cleaned here, the theme only ever goes into prompts (never treated as a path or URL), and the notes
//      are written to a file this code names, so "sources" can only be that file.
//   2. Only the light copy is kept (the render stays in the run directory and is removed after a success).
//   3. The outcome is a small JSON in exactly the shape the job broker accepts for `video.generate` (hermes-llm-jobs/worker.js).
// Used by `auto-movie job` (see bin/), which the PC-side runner starts.
import path from 'node:path';
import fs from 'node:fs';
import { ROOT, ensureDir, exists, readJSON, writeJSON, writeText, log, round } from './util.mjs';
import { make } from './make.mjs';
import { makeLightCopy, posterFrame, probe } from './media.mjs';
import { putObject } from './store.mjs';
import { qaSummary } from './publish.mjs';

export class InputError extends Error {
  constructor(field) { super(`invalid_input: ${field}`); this.code = 'invalid_input'; this.field = field; }
}

export const MINUTES = [2, 3];
export const ID_RE = /^[A-Za-z0-9-]{8,64}$/;

/** The request as the broker stored it → what the pipeline gets. Throws InputError. */
export function cleanRequest(p) {
  if (!p || typeof p !== 'object' || Array.isArray(p)) throw new InputError('payload');
  const theme = typeof p.theme === 'string' ? p.theme.normalize('NFKC').replace(/\s+/g, ' ').trim() : '';
  if (theme.length < 2 || theme.length > 60 || /[\u0000-\u001f\u007f<>{}`\\]/.test(theme)) throw new InputError('theme');
  if (!MINUTES.includes(p.minutes)) throw new InputError('minutes');
  let notes = '';
  if (p.notes != null) {
    if (typeof p.notes !== 'string') throw new InputError('notes');
    notes = p.notes.normalize('NFKC').replace(/\r\n?/g, '\n').replace(/[^\S\n]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
    if (notes.length > 1500 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(notes)) throw new InputError('notes');
  }
  return { theme, lengthSec: p.minutes * 60, notes };
}

const jstDate = () => new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Tokyo' }).replace(/-/g, '.');
const keys = (id) => ({ video: `movies/${id}/video.mp4`, poster: `movies/${id}/poster.webp` });

/** Chapters: the intro, every scene by its headline, the ending. */
export function chaptersFrom(episode, timeline) {
  const head = new Map(episode.scenes.map((s) => [s.id, s.headline]));
  return [
    { t: 0, title: 'イントロ' },
    ...timeline.scenes.map((sc) => ({ t: Math.floor(sc.start), title: head.get(sc.id) || sc.id })),
    { t: Math.floor(timeline.outro.start), title: 'エンディング' },
  ];
}

/** The shape the broker accepts (kept small: the broker stores it as JSON and the page reads it). */
export function resultOf({ id, episode, plan, info, chapters, bytes, qa }) {
  const k = keys(id);
  return {
    title: episode.title, subtitle: episode.subtitle, seconds: round(info.seconds, 1), width: info.width, height: info.height, style: plan.style,
    chapters, video: k.video, poster: k.poster, bytes,
    qa: qa && { status: qa.status, checks: qa.checks, passed: qa.passed, measuredSec: qa.measuredSec, overlaps: qa.overlaps, minGapSec: qa.minGapSec, lufs: qa.lufs },
  };
}

/**
 * @param {object} o
 * @param {string} o.id        the job id (also the run directory and the object key)
 * @param {object} o.request   { theme, minutes, notes? }
 * @param {boolean} [o.keep]   keep the heavy intermediates after a success
 */
export async function runJob({ id, request, keep = false }) {
  if (!ID_RE.test(id || '')) throw new InputError('id');
  const { theme, lengthSec, notes } = cleanRequest(request);
  const t0 = Date.now();
  const runDir = ensureDir(path.join(ROOT, 'runs', `job-${id}`));
  const sources = [];
  if (notes) { const f = path.join(runDir, 'notes.md'); writeText(f, notes + '\n'); sources.push(f); }

  const summary = await make({ theme, lengthSec, sources, style: 'auto', series: 'lifehack', provider: 'voicevox', quality: 'delivery', runDir, label: jstDate() });

  log('job', 'light copy + poster');
  const light = path.join(runDir, 'light.mp4'), poster = path.join(runDir, 'poster.webp');
  await makeLightCopy(summary.video, light);
  const info = await probe(light);
  await posterFrame(light, round(info.seconds / 4, 1), poster);

  const episode = readJSON(path.join(runDir, 'script.json')), plan = readJSON(path.join(runDir, 'plan.json')), timeline = readJSON(path.join(runDir, 'timeline.json'));
  const qaFile = path.join(runDir, 'qa', 'report.json');
  const result = resultOf({ id, episode, plan, info, chapters: chaptersFrom(episode, timeline), bytes: fs.statSync(light).size, qa: exists(qaFile) ? qaSummary(readJSON(qaFile)) : undefined });
  if (result.qa?.status === 'FAIL') throw new Error('qa_failed');

  const k = keys(id);
  await putObject(k.video, light, 'video/mp4');
  await putObject(k.poster, poster, 'image/webp');

  writeJSON(path.join(runDir, 'result.json'), { result, seconds: Math.round((Date.now() - t0) / 1000) });
  if (!keep) for (const d of ['video.mp4', 'light.mp4', 'poster.webp', 'project', 'audio', 'voice']) fs.rmSync(path.join(runDir, d), { recursive: true, force: true });
  return result;
}
