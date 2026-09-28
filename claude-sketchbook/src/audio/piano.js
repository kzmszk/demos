// A felt piano, from first principles: stiff strings (inharmonic partials), two or three strings per note
// tuned a hair apart (beating), a felt-covered hammer (dark, soft onset), double decay, dampers, and the
// small mechanical noises you hear when the microphone is close. Pure JS, deterministic.
import { Rng } from '../rng.js';

export const SR = 48000;

const midiHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

// stretch tuning: bass a little flat, treble a little sharp (cents)
const stretch = (m) => (m < 60 ? -0.035 * Math.pow(60 - m, 1.4) : 0.028 * Math.pow(m - 60, 1.45));

// one note, not damped by anything but its own decay until `damp` seconds (key and pedal both up)
// returns { l, r } Float32Arrays at SR
export function renderNote(m, vel, damp, seed, opts = {}) {
  const r = new Rng(seed >>> 0);
  const f0 = midiHz(m) * Math.pow(2, stretch(m) / 1200);
  const B = 0.00009 * Math.exp(0.056 * (m - 21));
  const v = Math.min(1, Math.max(0.05, vel));
  // how long the note rings on its own (fundamental, -60 dB)
  const T60 = Math.min(24, Math.max(1.6, 17 * Math.pow(2, -(m - 36) / 13.5)));
  const hasDamper = m < 89;
  const tDamp = hasDamper ? Math.max(0.02, damp) : 1e9;
  const tauDamp = 0.045 + 0.28 * Math.pow(Math.max(0, (72 - m) / 51), 1.5);
  const len = Math.min(T60 * 1.05, tDamp + tauDamp * 7 + 0.05, opts.maxLen || 14);
  const N = Math.ceil(len * SR);
  const out = new Float32Array(N);
  const strings = m < 30 ? 1 : m < 41 ? 2 : 3;
  const det = [0, 0.55 + r.range(-0.15, 0.2), -0.45 + r.range(-0.2, 0.15)];
  // felt: a strong low-pass that opens a little with velocity
  const fc = 600 + 2300 * Math.pow(v, 1.6);
  const tilt = 1.05 + (1 - v) * 0.75;
  const beta = 1 / 8.3; // hammer strike point
  const attack = 0.0026 + (1 - v) * 0.0045; // felt makes the onset soft
  const atkN = Math.max(8, Math.floor(attack * SR));
  let peak = 0;
  for (let n = 1; n <= 48; n++) {
    const fn = n * f0 * Math.sqrt(1 + B * n * n);
    if (fn > 11000) break;
    let a = Math.abs(Math.sin(Math.PI * n * beta)) + 0.04;
    a *= 1 / Math.pow(n, tilt);
    a *= 1 / (1 + Math.pow(fn / fc, 3));
    // soundboard / body: a broad warm bump and a little presence
    const oct = Math.log2(fn / 180);
    a *= 1 + 0.45 * Math.exp(-oct * oct / 0.5) + 0.18 * Math.exp(-Math.pow(Math.log2(fn / 1100), 2) / 0.3);
    if (a < 0.0007) continue;
    const tauN = (T60 / 6.9) / (1 + 0.14 * (n - 1) + Math.pow(fn / 2600, 1.6));
    const tauP = tauN * 0.42, tauA = tauN * 1.9, wP = 0.62;
    for (let s = 0; s < strings; s++) {
      const cents = det[s] * (1 + n * 0.012);
      const f = fn * Math.pow(2, cents / 1200);
      const w = (2 * Math.PI * f) / SR;
      const cr = Math.cos(w), sr = Math.sin(w);
      let c = Math.cos(r.range(0, 6.283)), sn = Math.sin(r.range(0, 6.283));
      const nrm = Math.hypot(c, sn); c /= nrm; sn /= nrm;
      const amp = a / strings * (s === 0 ? 1.1 : 0.95);
      let eP = amp * wP, eA = amp * (1 - wP);
      const kP = Math.exp(-1 / (tauP * SR)), kA = Math.exp(-1 / (tauA * SR));
      const dampStart = Math.floor(tDamp * SR);
      const kD = Math.exp(-1 / (tauDamp * SR));
      let d = 1;
      for (let i = 0; i < N; i++) {
        const env = eP + eA;
        if (env * d < 1e-6 && i > atkN) break;
        const atk = i < atkN ? (i / atkN) * (i / atkN) * (3 - 2 * (i / atkN)) : 1;
        out[i] += sn * env * d * atk;
        const nc = c * cr - sn * sr;
        sn = c * sr + sn * cr;
        c = nc;
        eP *= kP; eA *= kA;
        if (i >= dampStart) d *= kD;
      }
    }
  }
  // the hammer's felt thud and the key's knock, scaled by how hard it was played
  const thudN = Math.floor(0.05 * SR);
  let lp = 0, lp2 = 0;
  const kf = 1 - Math.exp(-2 * Math.PI * (500 + 900 * v) / SR);
  const knock = 70 + 50 * r.f();
  for (let i = 0; i < thudN && i < N; i++) {
    const t = i / SR;
    const e = Math.exp(-t / 0.009) * (1 - Math.exp(-t / 0.0008));
    const x = (r.f() * 2 - 1);
    lp += (x - lp) * kf; lp2 += (lp - lp2) * kf;
    out[i] += lp2 * e * 0.05 * v;
    out[i] += Math.sin(2 * Math.PI * knock * t) * Math.exp(-t / 0.02) * 0.018 * v;
  }
  // normalise the partial sum roughly by register so loudness follows velocity, not pitch
  const gain = (0.2 + 0.8 * Math.pow(v, 1.7)) * (0.52 + 0.004 * (m - 21));
  for (let i = 0; i < N; i++) out[i] *= gain;
  // dampers settling: a tiny soft brush of felt
  if (hasDamper && tDamp < len) {
    const i0 = Math.floor(tDamp * SR), dn = Math.floor(0.06 * SR);
    let l = 0;
    for (let i = 0; i < dn && i0 + i < N; i++) {
      l += ((r.f() * 2 - 1) - l) * 0.08;
      out[i0 + i] += l * 0.004 * Math.sin((Math.PI * i) / dn);
    }
  }
  return out;
}

// mechanical: the key going down (a soft click before the tone) — mixed separately and quietly
export function keyClick(seed, vel) {
  const r = new Rng(seed);
  const N = Math.floor(0.025 * SR);
  const out = new Float32Array(N);
  let hp = 0, prev = 0;
  for (let i = 0; i < N; i++) {
    const x = r.f() * 2 - 1;
    hp = 0.9 * (hp + x - prev); prev = x;
    out[i] = hp * Math.exp(-i / (0.003 * SR)) * 0.02 * vel;
  }
  return out;
}

export { midiHz };
