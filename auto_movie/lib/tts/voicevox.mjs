// VOICEVOX engine client (free, local). The engine runs in Docker (voicevox/voicevox_engine:cpu-latest).
// Besides the waveform we keep the mora timeline: it drives lip-sync, caption pages and word-level cues.
import { run, sleep, log } from '../util.mjs';
import { parseWav } from '../audio/wav.mjs';

const BASE = process.env.VOICEVOX_URL || 'http://127.0.0.1:50021';
const CONTAINER = 'automovie-voicevox';
const IMAGE = 'voicevox/voicevox_engine:cpu-latest';

async function api(path, { method = 'POST', query, body, raw = false } = {}) {
  const url = new URL(BASE + path);
  for (const [k, v] of Object.entries(query || {})) url.searchParams.set(k, String(v));
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`VOICEVOX ${path} → ${res.status} ${(await res.text()).slice(0, 200)}`);
  return raw ? Buffer.from(await res.arrayBuffer()) : res.json();
}

export async function isUp() {
  try {
    const r = await fetch(BASE + '/version', { signal: AbortSignal.timeout(1500) });
    return r.ok;
  } catch { return false; }
}

/** Make sure an engine answers on :50021 – start (or create) the Docker container when needed. */
export async function ensureReady() {
  if (await isUp()) return;
  log('voicevox', 'engine not running – starting Docker container', CONTAINER);
  const start = await run('docker', ['start', CONTAINER]);
  if (start.code !== 0) {
    const created = await run('docker', ['run', '-d', '--name', CONTAINER, '-p', '127.0.0.1:50021:50021', IMAGE]);
    if (created.code !== 0) throw new Error(`cannot start VOICEVOX (docker): ${created.stderr.slice(0, 300)}\nPull the image first: docker pull ${IMAGE}`);
  }
  for (let i = 0; i < 90; i++) {
    if (await isUp()) { log('voicevox', 'engine is up'); return; }
    await sleep(1000);
  }
  throw new Error('VOICEVOX engine did not become ready in 90 s');
}

export const audioQuery = (text, speaker) => api('/audio_query', { query: { text, speaker } });

/** Text normalisation for speech: keeps what the engine reads well, drops decoration. */
export function speechText(text) {
  return String(text)
    .replace(/[「」『』（）()［］\[\]{}<>*_`#]/g, '')
    .replace(/…+|\.{3,}|・{2,}/g, '、')
    .replace(/[〜～]/g, 'ー')
    .replace(/\s+/g, '')
    .replace(/、{2,}/g, '、')
    .trim();
}

const EMOTION = {
  normal: {},
  happy: { intonationScale: +0.15, pitchScale: +0.02 },
  surprised: { intonationScale: +0.25, pitchScale: +0.04, speedScale: +0.02 },
  thinking: { speedScale: -0.06, pitchScale: -0.02, intonationScale: -0.05 },
  sad: { speedScale: -0.07, pitchScale: -0.03, intonationScale: -0.1 },
  emphatic: { intonationScale: +0.2, volumeScale: +0.1 },
};

/**
 * Build the mora timeline (seconds from the start of the WAV) out of an audio_query.
 * VOICEVOX divides lengths by speedScale at synthesis; pre/post lengths and pauses are calibrated against the
 * real duration so small differences between engine versions do not accumulate.
 */
export function moraTimeline(q, actualDur) {
  const speed = q.speedScale || 1;
  const segs = [];
  let t = (q.prePhonemeLength || 0) / speed;
  for (const ap of q.accent_phrases) {
    for (const m of ap.moras) {
      const c = (m.consonant_length || 0) / speed, v = m.vowel_length / speed;
      segs.push({ kind: 'mora', text: m.text, vowel: m.vowel, cons: m.consonant || null, t0: t, tv: t + c, t1: t + c + v });
      t += c + v;
    }
    if (ap.pause_mora) {
      const base = q.pauseLength != null ? q.pauseLength : ap.pause_mora.vowel_length * (q.pauseLengthScale ?? 1);
      const pl = base / speed;
      segs.push({ kind: 'pause', text: ap.pause_mora.text, vowel: 'pau', t0: t, tv: t, t1: t + pl });
      t += pl;
    }
  }
  t += (q.postPhonemeLength || 0) / speed;
  const k = t > 0 ? actualDur / t : 1;
  for (const s of segs) { s.t0 *= k; s.tv *= k; s.t1 *= k; }
  return segs;
}

/** Trim leading/trailing silence (keeping a little air) and shift the timeline. */
function trimSilence(mono, rate, segs, { lead = 0.03, tail = 0.07, thresh = 0.004 } = {}) {
  let a = 0, b = mono.length - 1;
  while (a < b && Math.abs(mono[a]) < thresh) a++;
  while (b > a && Math.abs(mono[b]) < thresh) b--;
  const start = Math.max(0, a - Math.round(lead * rate));
  const end = Math.min(mono.length, b + 1 + Math.round(tail * rate));
  const shift = start / rate;
  const samples = mono.slice(start, end);
  const out = segs.map((s) => ({ ...s, t0: Math.max(0, s.t0 - shift), tv: Math.max(0, s.tv - shift), t1: Math.max(0, s.t1 - shift) }));
  return { samples, segs: out };
}

/**
 * Synthesize one utterance.
 * @returns {{samples: Float32Array, rate: number, duration: number, segs: object[], kana: string}}
 */
export async function synth({ text, say, speaker, params = {}, emotion = 'normal' }) {
  const t = speechText(say || text);
  const q = await audioQuery(t, speaker);
  const emo = EMOTION[emotion] || {};
  const merged = { ...params };
  for (const [k, v] of Object.entries(emo)) merged[k] = (merged[k] ?? (k === 'volumeScale' || k === 'speedScale' || k === 'intonationScale' ? 1 : 0)) + v;
  Object.assign(q, { prePhonemeLength: 0.05, postPhonemeLength: 0.08, outputSamplingRate: 24000, outputStereo: false }, merged);
  const wavBuf = await api('/synthesis', { query: { speaker }, body: q, raw: true });
  const wav = parseWav(wavBuf);
  const mono = wav.channels[0];
  const full = mono.length / wav.rate;
  const segs = moraTimeline(q, full);
  const trimmed = trimSilence(mono, wav.rate, segs);
  return { samples: trimmed.samples, rate: wav.rate, duration: trimmed.samples.length / wav.rate, segs: trimmed.segs, kana: q.kana, speechText: t };
}

/**
 * Time (seconds from the start of the audio) at which the text at each character offset begins to be spoken.
 * Uses audio_query on the prefix to count how many moras precede the offset.
 * @param {number[]} offsets character offsets into (say || text)
 */
export async function timesAtOffsets({ text, say, speaker, segs, offsets }) {
  const base = say || text;
  const moras = segs.filter((s) => s.kind === 'mora');
  const out = [];
  for (const idx of offsets) {
    const prefix = idx <= 0 ? '' : speechText(base.slice(0, idx));
    if (!prefix) { out.push(moras[0]?.t0 ?? 0); continue; }
    const q = await audioQuery(prefix, speaker);
    const n = q.accent_phrases.reduce((s, ap) => s + ap.moras.length, 0);
    const m = moras[Math.min(n, moras.length - 1)];
    out.push(m ? m.t0 : segs.at(-1)?.t1 ?? 0);
  }
  return out;
}

export async function listSpeakers() {
  return api('/speakers', { method: 'GET' });
}
