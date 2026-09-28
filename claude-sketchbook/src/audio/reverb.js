// A small warm room, as an impulse response: early reflections, then a tail that darkens as it fades.
import { Rng } from '../rng.js';
export function makeIR(sr, seconds = 2.6, seed = 7) {
  const r = new Rng(seed);
  const n = Math.floor(seconds * sr);
  const L = new Float32Array(n), R = new Float32Array(n);
  const pre = Math.floor(0.011 * sr);
  // early reflections
  const taps = [[0.013, 0.5], [0.019, 0.38], [0.027, 0.33], [0.034, 0.27], [0.046, 0.22], [0.058, 0.17], [0.071, 0.13]];
  for (const [t, a] of taps) {
    const i = Math.floor(t * sr), j = Math.floor((t + r.range(0.001, 0.004)) * sr);
    L[i] += a * (r.chance(0.5) ? 1 : -1); R[j] += a * (r.chance(0.5) ? 1 : -1);
  }
  // late tail: noise, decaying, low-passed harder as it goes
  const rt60 = 1.7, tau = rt60 / 6.9;
  let lpL = 0, lpR = 0;
  for (let i = pre; i < n; i++) {
    const t = (i - pre) / sr;
    const fc = 1200 + 7500 * Math.exp(-t / 0.35);
    const k = 1 - Math.exp((-2 * Math.PI * fc) / sr);
    lpL += (r.f() * 2 - 1 - lpL) * k;
    lpR += (r.f() * 2 - 1 - lpR) * k;
    const env = Math.exp(-t / tau) * Math.min(1, t / 0.03) * 0.34;
    L[i] += lpL * env; R[i] += lpR * env;
  }
  return [L, R];
}
