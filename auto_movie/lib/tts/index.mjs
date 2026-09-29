// Voice stage: turns script lines into audio files + timing data, with a persistent cache.
// Providers: 'voicevox' (default, free/local), 'gemini' (paid, swap in at the end), 'mock' (offline tests).
import path from 'node:path';
import { ROOT, sha1, ensureDir, exists, readJSON, writeJSON, log, pool, round } from '../util.mjs';
import { readWav, writeWav } from '../audio/wav.mjs';
import * as voicevox from './voicevox.mjs';
import * as gemini from './gemini.mjs';
import * as mock from './mock.mjs';

export const PROVIDERS = { voicevox, gemini, mock };
const CACHE = path.join(ROOT, '.cache', 'tts');

/** Voice settings of one cast member for a provider. */
export function voiceOf(castMember, provider) {
  if (provider === 'mock') return { speaker: castMember.voice?.voicevox?.speaker ?? 0 };
  const v = castMember.voice?.[provider];
  if (!v) throw new Error(`cast "${castMember.id}" has no voice for provider "${provider}"`);
  return v;
}

/** Split into clauses at 、。！？ (punctuation stays with the preceding clause). Returns [{text, start}]. */
export function splitClauses(text) {
  const out = [];
  let start = 0;
  for (let i = 0; i < text.length; i++) {
    if ('、。！？!?，,'.includes(text[i])) {
      // swallow a run of punctuation / closing quotes
      let j = i + 1;
      while (j < text.length && '、。！？!?」』）)'.includes(text[j])) j++;
      out.push({ text: text.slice(start, j), start });
      start = j; i = j - 1;
    }
  }
  if (start < text.length) out.push({ text: text.slice(start), start });
  return out.filter((c) => c.text.trim());
}

/** Group clauses into caption pages that fit (max characters per page), never breaking inside a clause unless it is too long. */
export function makePages(clauses, maxChars = 40) {
  const pages = [];
  let cur = null;
  const push = () => { if (cur) pages.push(cur); cur = null; };
  for (const c of clauses) {
    const len = c.text.replace(/[、。！？!?]/g, '').length;
    if (cur && cur.len + len <= maxChars) { cur.text += c.text; cur.len += len; cur.end = c; continue; }
    push();
    cur = { text: c.text, len, first: c, end: c };
  }
  push();
  return pages;
}

/**
 * Synthesize all lines. `lines`: [{id, who, text, say?, emotion?}]. Returns records keyed by line id:
 * { id, who, file, duration, rate, segs, kana, clauses:[{text,t0,t1}] } with times relative to the line audio.
 */
export async function synthesizeLines({ lines, cast, provider = 'voicevox', outDir, concurrency = 3 }) {
  const P = PROVIDERS[provider];
  if (!P) throw new Error(`unknown TTS provider "${provider}"`);
  await P.ensureReady();
  ensureDir(outDir);
  const cacheDir = ensureDir(path.join(CACHE, provider));
  const byWho = Object.fromEntries(Object.entries(cast).map(([role, c]) => [role, c]));
  let hits = 0, made = 0;

  const results = await pool(provider === 'gemini' ? 2 : concurrency, lines, async (line) => {
    const member = byWho[line.who];
    if (!member) throw new Error(`line ${line.id}: unknown speaker "${line.who}"`);
    const v = voiceOf(member, provider);
    const emotion = line.emotion || 'normal';
    const model = provider === 'gemini' ? (process.env.AUTO_MOVIE_GEMINI_TTS_MODEL || 'gemini-3.8-flash-tts') : undefined;
    const key = sha1({ provider, model, text: line.text, say: line.say || null, emotion, v, ver: 3 });
    const wavPath = path.join(cacheDir, `${key}.wav`), metaPath = path.join(cacheDir, `${key}.json`);
    let meta;
    if (exists(wavPath) && exists(metaPath)) {
      meta = readJSON(metaPath); hits++;
    } else {
      const args = { text: line.text, say: line.say, emotion };
      const r = provider === 'voicevox' ? await voicevox.synth({ ...args, speaker: v.speaker, params: v.params })
        : provider === 'gemini' ? await gemini.synth({ ...args, voice: v.voice, style: v.style })
          : await mock.synth({ ...args, speaker: v.speaker });
      writeWav(wavPath, { rate: r.rate, channels: [r.samples] });
      // clause timing (for caption pages and cues)
      const clauses = splitClauses(line.text);
      const base = line.say || line.text;
      let offsets;
      if (line.say) {
        const sc = splitClauses(line.say);
        offsets = clauses.map((_, i) => sc[Math.min(i, sc.length - 1)].start);
      } else offsets = clauses.map((c) => c.start);
      let starts;
      if (provider === 'voicevox') starts = await voicevox.timesAtOffsets({ text: line.text, say: line.say, speaker: v.speaker, segs: r.segs, offsets });
      else if (r.segs && provider === 'mock') starts = offsets.map((o) => (o / Math.max(1, base.length)) * r.duration);
      else starts = offsets.map((o) => (o / Math.max(1, base.length)) * r.duration * 0.98);
      starts[0] = 0;
      meta = {
        rate: r.rate, duration: r.duration, segs: r.segs, kana: r.kana,
        clauses: clauses.map((c, i) => ({ text: c.text, start: c.start, t0: round(starts[i]), t1: round(i + 1 < clauses.length ? starts[i + 1] : r.duration) })),
      };
      writeJSON(metaPath, meta); made++;
    }
    const file = path.join(outDir, `${line.id}.wav`);
    const a = readWav(wavPath);
    writeWav(file, a);
    return { id: line.id, who: line.who, text: line.text, emotion, file, ...meta };
  });
  log('voice', `${provider}: ${results.length} lines (${made} synthesized, ${hits} cached), ${round(results.reduce((s, r) => s + r.duration, 0), 1)} s of speech`);
  return Object.fromEntries(results.map((r) => [r.id, r]));
}

/**
 * Word-level sync: for every cue that says "after <text>", find when that text starts being spoken.
 * Adds `anchorTimes: {charOffset: seconds}` to the matching record (VOICEVOX only; other providers fall back to
 * a proportional estimate in the timeline compiler).
 */
export async function resolveAnchors({ provider, cast, lines, records, cues }) {
  if (provider !== 'voicevox') return;
  const byLine = new Map();
  for (const cue of cues) {
    if (cue.after == null || cue.after === '') continue;
    const line = lines.find((l) => l.id === cue.line);
    if (!line) continue;
    const idx = line.text.indexOf(cue.after);
    if (idx < 0) continue;
    if (!byLine.has(line.id)) byLine.set(line.id, new Set());
    byLine.get(line.id).add(idx);
  }
  for (const [id, set] of byLine) {
    const line = lines.find((l) => l.id === id), rec = records[id];
    const member = cast[line.who];
    const offsets = [...set];
    const scaled = line.say ? offsets.map((o) => Math.round((o / line.text.length) * line.say.length)) : offsets;
    const times = await voicevox.timesAtOffsets({ text: line.text, say: line.say, speaker: voiceOf(member, provider).speaker, segs: rec.segs, offsets: scaled });
    rec.anchorTimes = Object.fromEntries(offsets.map((o, i) => [o, times[i]]));
  }
}
