// Renders a composer score to stereo audio: per-instrument buses, a shared reverb send, gentle saturation, fades.
import { rng, clamp } from '../util.mjs';
import {
  SR, place, placeStereo, newBus, pianoNote, epNote, padNote, bassNote, bellNote, kick, brushSnare, shaker,
  reverb, biquad, saturate, peak, rms,
} from './synth.mjs';

const sum = (a, b, g = 1) => { for (let c = 0; c < 2; c++) for (let i = 0; i < a[c].length; i++) a[c][i] += b[c][i] * g; };

/** @returns {{rate:number, channels:Float32Array[], stems?:object}} */
export function renderBGM(score, { sr = SR, keepStems = false, fadeOut = 2.4 } = {}) {
  const dur = score.duration + 0.5;
  const r = rng('bgm-pan');
  const B = { piano: newBus(dur), ep: newBus(dur), pad: newBus(dur), bass: newBus(dur), bell: newBus(dur), perc: newBus(dur) };
  const off = (t) => Math.round(t * sr);

  for (const n of score.notes.piano) place(B.piano, pianoNote(n.midi, n.vel, n.dur, { pedal: n.pedal ?? 0.5, seed: Math.round(n.t * 1000) + n.midi }), off(n.t), 1, clamp((n.midi - 62) / 46, -0.5, 0.5));
  for (const n of score.notes.ep) { const [l, rr] = epNote(n.midi, n.vel, n.dur, { seed: Math.round(n.t * 1000) + n.midi }); placeStereo(B.ep, l, rr, off(n.t), 1); }
  for (const n of score.notes.pad) { const [l, rr] = padNote(n.midi, n.vel, n.dur, { seed: n.midi }); placeStereo(B.pad, l, rr, off(n.t), 1); }
  for (const n of score.notes.bass) place(B.bass, bassNote(n.midi, n.vel, n.dur), off(n.t), 1, 0);
  for (const n of score.notes.bell) place(B.bell, bellNote(n.midi, n.vel, { tau: Math.min(2.6, n.dur) }), off(n.t), 1, r.range(-0.45, 0.45));
  score.notes.kick.forEach((n) => place(B.perc, kick(n.vel), off(n.t), 1, 0));
  score.notes.snare.forEach((n, i) => place(B.perc, brushSnare(n.vel, i), off(n.t), 0.9, 0.12));
  score.notes.shaker.forEach((n, i) => place(B.perc, shaker(n.vel, i), off(n.t), 0.7, -0.25));

  // tone shaping per bus
  for (const ch of B.piano) biquad(ch, 'hp', 58);
  for (const ch of B.ep) { biquad(ch, 'hp', 120); biquad(ch, 'lp', 5200); }
  for (const ch of B.pad) { biquad(ch, 'hp', 150); biquad(ch, 'lp', 3200); }
  for (const ch of B.bass) { biquad(ch, 'hp', 52); biquad(ch, 'lp', 520); }
  for (const ch of B.perc) biquad(ch, 'lp', 9000);
  for (const ch of B.bell) biquad(ch, 'hp', 300);

  const gains = { piano: 1.0, ep: 0.62, pad: 0.8, bass: 0.62, bell: 0.55, perc: 0.36 };
  const sends = { piano: 0.34, ep: 0.32, pad: 0.4, bass: 0, bell: 0.6, perc: 0.12 };
  const dry = newBus(dur), send = newBus(dur);
  for (const k of Object.keys(B)) { sum(dry, B[k], gains[k]); if (sends[k]) sum(send, B[k], gains[k] * sends[k]); }
  const wet = reverb(send, { rt60: 2.1, damp: 0.34, size: 1.15 });
  for (const ch of wet) biquad(ch, 'hp', 160); // keep the tail out of the low end
  const mix = newBus(dur);
  sum(mix, dry, 1); sum(mix, wet, 0.85);

  saturate(mix, 1.1);
  for (const ch of mix) {
    biquad(ch, 'hp', 55, 0.7);
    biquad(ch, 'peak', 2800, 0.8, -3.5); // leave room for the voice's presence band
  }

  // trim to duration with a fade in/out
  const n = Math.round(score.duration * sr);
  const out = mix.map((ch) => ch.slice(0, n));
  const fi = Math.round(0.04 * sr), fo = Math.round(fadeOut * sr);
  for (const ch of out) {
    for (let i = 0; i < fi; i++) ch[i] *= i / fi;
    for (let i = 0; i < fo; i++) { const x = i / fo; ch[n - 1 - i] *= 0.5 - 0.5 * Math.cos(Math.PI * x) ; }
  }
  const res = { rate: sr, channels: out };
  if (keepStems) res.stems = B;
  return res;
}

export const levelInfo = (audio) => ({ peak: peak(audio.channels), rms: rms(audio.channels) });
