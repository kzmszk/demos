// Offline stand-in voice for tests and quick layout checks: syllable-rate vowel buzz with formants.
// It has the same interface as the real providers (samples/rate/duration/segs) so the whole pipeline can run without any service.
import { rng } from '../util.mjs';

export const ensureReady = async () => {};
const VOWELS = { a: [800, 1200], i: [300, 2300], u: [350, 1300], e: [500, 1900], o: [500, 900] };
const KEYS = Object.keys(VOWELS);

export async function synth({ text, say, speaker = 0, emotion = 'normal' }) {
  const t = String(say || text).replace(/[、。！？!?\s]/g, '');
  const rate = 24000;
  const r = rng(`${t}:${speaker}`);
  const base = 150 + (speaker % 5) * 22 + (emotion === 'surprised' ? 25 : 0);
  const segs = [];
  const chunks = [];
  let time = 0.03;
  for (const ch of String(say || text)) {
    if (/[、。！？!?]/.test(ch)) { segs.push({ kind: 'pause', text: ch, vowel: 'pau', t0: time, tv: time, t1: time + 0.2 }); time += 0.2; continue; }
    if (/\s/.test(ch)) continue;
    const v = KEYS[Math.floor(r() * KEYS.length)];
    const d = 0.11 + r() * 0.03;
    segs.push({ kind: 'mora', text: ch, vowel: v, cons: null, t0: time, tv: time, t1: time + d });
    chunks.push({ t0: time, t1: time + d, v, f0: base * (1 + 0.15 * Math.sin(time * 3)) });
    time += d;
  }
  time += 0.07;
  const n = Math.round(time * rate), out = new Float32Array(n);
  for (const c of chunks) {
    const [f1, f2] = VOWELS[c.v];
    const a = Math.floor(c.t0 * rate), b = Math.min(n, Math.floor(c.t1 * rate));
    for (let i = a; i < b; i++) {
      const tt = i / rate, env = Math.sin((Math.PI * (i - a)) / (b - a)) ** 0.7;
      let s = 0;
      for (let h = 1; h <= 12; h++) {
        const f = c.f0 * h;
        const g = Math.exp(-((f - f1) ** 2) / 2e5) + 0.6 * Math.exp(-((f - f2) ** 2) / 4e5) + 0.05;
        s += (g / h) * Math.sin(2 * Math.PI * f * tt);
      }
      out[i] += 0.16 * env * s;
    }
  }
  return { samples: out, rate, duration: n / rate, segs, kana: null, speechText: t };
}
