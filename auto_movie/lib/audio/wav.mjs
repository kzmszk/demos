// Minimal WAV I/O and buffer helpers. Audio inside the pipeline is { rate, channels: [Float32Array, …] }.
import fs from 'node:fs';

export function parseWav(buf) {
  if (buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') throw new Error('not a WAV file');
  let pos = 12, fmt = null, data = null;
  while (pos + 8 <= buf.length) {
    const id = buf.toString('ascii', pos, pos + 4);
    let size = buf.readUInt32LE(pos + 4);
    const body = pos + 8;
    if (id === 'fmt ') {
      fmt = {
        format: buf.readUInt16LE(body), channels: buf.readUInt16LE(body + 2), rate: buf.readUInt32LE(body + 4),
        bits: buf.readUInt16LE(body + 14),
      };
    } else if (id === 'data') {
      if (body + size > buf.length) size = buf.length - body; // streamed WAVs may claim 0xFFFFFFFF
      data = buf.subarray(body, body + size);
      break;
    }
    pos = body + size + (size & 1);
  }
  if (!fmt || !data) throw new Error('WAV missing fmt/data');
  const { channels, bits, format } = fmt;
  const frames = Math.floor(data.length / (channels * (bits / 8)));
  const out = Array.from({ length: channels }, () => new Float32Array(frames));
  for (let i = 0; i < frames; i++) {
    for (let c = 0; c < channels; c++) {
      const o = (i * channels + c) * (bits / 8);
      let v;
      if (format === 3 && bits === 32) v = data.readFloatLE(o);
      else if (bits === 16) v = data.readInt16LE(o) / 32768;
      else if (bits === 24) v = data.readIntLE(o, 3) / 8388608;
      else if (bits === 32) v = data.readInt32LE(o) / 2147483648;
      else throw new Error(`unsupported WAV format ${format}/${bits}`);
      out[c][i] = v;
    }
  }
  return { rate: fmt.rate, channels: out };
}

export const readWav = (p) => parseWav(fs.readFileSync(p));

/** Encode to 16-bit PCM WAV (or 32-bit float when bits=32). */
export function encodeWav({ rate, channels }, bits = 16) {
  const n = channels[0].length, nc = channels.length, bytes = bits / 8;
  const dataSize = n * nc * bytes;
  const buf = Buffer.alloc(44 + dataSize);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + dataSize, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(bits === 32 ? 3 : 1, 20);
  buf.writeUInt16LE(nc, 22); buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * nc * bytes, 28);
  buf.writeUInt16LE(nc * bytes, 32); buf.writeUInt16LE(bits, 34);
  buf.write('data', 36); buf.writeUInt32LE(dataSize, 40);
  let o = 44;
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < nc; c++) {
      const x = channels[c][i];
      if (bits === 32) { buf.writeFloatLE(x, o); o += 4; }
      else { const s = Math.max(-1, Math.min(1, x)); buf.writeInt16LE(Math.round(s < 0 ? s * 32768 : s * 32767), o); o += 2; }
    }
  }
  return buf;
}

export const writeWav = (p, audio, bits = 16) => fs.writeFileSync(p, encodeWav(audio, bits));
export const durationOf = (a) => a.channels[0].length / a.rate;
export const makeBuffer = (rate, seconds, nch = 2) => ({ rate, channels: Array.from({ length: nch }, () => new Float32Array(Math.ceil(seconds * rate))) });
export const toMono = (a) => {
  if (a.channels.length === 1) return a.channels[0];
  const n = a.channels[0].length, out = new Float32Array(n), k = 1 / a.channels.length;
  for (const ch of a.channels) for (let i = 0; i < n; i++) out[i] += ch[i] * k;
  return out;
};

/** Linear-interpolating resampler (good enough for 24 kHz speech → 48 kHz; music is rendered at target rate). */
export function resample(a, newRate) {
  if (a.rate === newRate) return a;
  const ratio = a.rate / newRate;
  const n = Math.floor(a.channels[0].length / ratio);
  const channels = a.channels.map((src) => {
    const dst = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = i * ratio, i0 = Math.floor(x), f = x - i0;
      const s0 = src[i0], s1 = src[Math.min(i0 + 1, src.length - 1)];
      dst[i] = s0 + (s1 - s0) * f;
    }
    return dst;
  });
  return { rate: newRate, channels };
}

/** Add `src` into `dst` starting at time `t` seconds with gain (mono src → all dst channels, or matching channels). */
export function mixInto(dst, src, t, gain = 1, pan = 0) {
  const off = Math.round(t * dst.rate);
  const nSrc = src.channels[0].length;
  for (let c = 0; c < dst.channels.length; c++) {
    const s = src.channels[Math.min(c, src.channels.length - 1)];
    // equal-power pan for mono sources
    const g = src.channels.length === 1 && dst.channels.length === 2 ? gain * (c === 0 ? Math.cos((pan + 1) * Math.PI / 4) : Math.sin((pan + 1) * Math.PI / 4)) * Math.SQRT2 : gain;
    const d = dst.channels[c];
    const end = Math.min(nSrc, d.length - off);
    for (let i = Math.max(0, -off); i < end; i++) d[off + i] += s[i] * g;
  }
}

/** RMS envelope in windows of `hop` seconds (mono). Returns Float32Array of linear RMS per window. */
export function rmsEnvelope(mono, rate, hop) {
  const step = Math.max(1, Math.round(rate * hop));
  const n = Math.ceil(mono.length / step);
  const out = new Float32Array(n);
  for (let w = 0; w < n; w++) {
    let s = 0, c = 0;
    const end = Math.min(mono.length, (w + 1) * step);
    for (let i = w * step; i < end; i++) { s += mono[i] * mono[i]; c++; }
    out[w] = c ? Math.sqrt(s / c) : 0;
  }
  return out;
}

export const db = (x) => 20 * Math.log10(Math.max(1e-9, x));
export const fromDb = (d) => 10 ** (d / 20);
