// Gemini TTS (paid, "serious" voices) – meant to replace VOICEVOX once the video is finished.
// Needs GEMINI_API_KEY (or GOOGLE_API_KEY). Model: AUTO_MOVIE_GEMINI_TTS_MODEL (default gemini-3.8-flash-tts).
// The Interactions API is tried first (current docs); if the model/endpoint is rejected we fall back to the older
// generateContent shape used by the *-preview-tts models.
import { parseWav } from '../audio/wav.mjs';
import { log } from '../util.mjs';

const MODEL = () => process.env.AUTO_MOVIE_GEMINI_TTS_MODEL || 'gemini-3.8-flash-tts';
const KEY = () => process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
const HOST = 'https://generativelanguage.googleapis.com/v1beta';

export const available = () => Boolean(KEY());
export async function ensureReady() {
  if (!KEY()) throw new Error('Gemini TTS needs GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment');
}

async function post(path, body) {
  const res = await fetch(`${HOST}${path}`, {
    method: 'POST',
    headers: { 'x-goog-api-key': KEY(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  });
  const text = await res.text();
  if (!res.ok) { const e = new Error(`Gemini ${path} → ${res.status} ${text.slice(0, 300)}`); e.status = res.status; throw e; }
  return JSON.parse(text);
}

function pcm16ToFloat(buf) {
  const n = Math.floor(buf.length / 2), out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = buf.readInt16LE(i * 2) / 32768;
  return out;
}

function findAudio(obj) {
  // walk the response and return the last {data, mime_type|mimeType} that looks like audio
  let found = null;
  (function walk(o) {
    if (!o || typeof o !== 'object') return;
    if (typeof o.data === 'string' && o.data.length > 100 && (o.type === 'audio' || /audio/.test(o.mime_type || o.mimeType || ''))) found = o;
    for (const v of Object.values(o)) walk(v);
  })(obj);
  return found;
}

function decode(audioObj) {
  const buf = Buffer.from(audioObj.data, 'base64');
  const mime = audioObj.mime_type || audioObj.mimeType || '';
  if (buf.toString('ascii', 0, 4) === 'RIFF') {
    const w = parseWav(buf);
    return { samples: w.channels[0], rate: w.rate };
  }
  const m = mime.match(/rate=(\d+)/);
  return { samples: pcm16ToFloat(buf), rate: m ? +m[1] : 24000 }; // raw L16 PCM
}

export async function synth({ text, say, voice, style }) {
  await ensureReady();
  const content = say || text;
  let audio;
  try {
    const res = await post('/interactions', {
      model: MODEL(),
      input: [{ type: 'user_input', content: [{ type: 'text', text: content, annotations: style ? [{ type: 'speech_metadata', style }] : [] }] }],
      response_format: { type: 'audio' },
      generation_config: { speech_config: [{ voice }] },
    });
    audio = findAudio(res);
  } catch (e) {
    if (![400, 404].includes(e.status)) throw e;
    log('gemini', `interactions API rejected (${e.status}) – trying generateContent`);
    const model = process.env.AUTO_MOVIE_GEMINI_TTS_FALLBACK || 'gemini-2.5-flash-preview-tts';
    const res = await post(`/models/${model}:generateContent`, {
      contents: [{ parts: [{ text: style ? `${style}。次の台詞を読んでください：${content}` : content }] }],
      generationConfig: { responseModalities: ['AUDIO'], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } } } },
    });
    audio = findAudio(res);
  }
  if (!audio) throw new Error('Gemini TTS: no audio in the response');
  const { samples, rate } = decode(audio);
  return { samples, rate, duration: samples.length / rate, segs: null, kana: null, speechText: content };
}
