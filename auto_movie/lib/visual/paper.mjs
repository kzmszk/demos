// A tileable paper-grain PNG generated in pure JS (no image libraries): fine noise plus a few short fibres.
import zlib from 'node:zlib';
import { rng } from '../util.mjs';

function crc32(buf) {
  if (typeof zlib.crc32 === 'function') return zlib.crc32(buf) >>> 0;
  let c, crc = 0xffffffff;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
const chunk = (type, data) => {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
};

export function encodePNG(width, height, rgb) {
  const raw = Buffer.alloc((width * 3 + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (width * 3 + 1)] = 0;
    rgb.copy(raw, y * (width * 3 + 1) + 1, y * width * 3, (y + 1) * width * 3);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

export function paperPNG(size = 512, seed = 'paper') {
  const r = rng(seed);
  const px = new Float32Array(size * size).fill(0.965);
  for (let i = 0; i < px.length; i++) px[i] += r.gauss() * 0.012;
  // soft blotches (low frequency) for a slightly uneven sheet
  for (let b = 0; b < 40; b++) {
    const cx = r.int(0, size - 1), cy = r.int(0, size - 1), rad = r.range(30, 90), amp = r.range(-0.012, 0.012);
    for (let dy = -rad; dy <= rad; dy++) for (let dx = -rad; dx <= rad; dx++) {
      const d = Math.hypot(dx, dy); if (d > rad) continue;
      const x = (cx + dx + size) % size, y = (cy + dy + size) % size;
      px[y * size + x] += amp * (1 - d / rad) ** 2;
    }
  }
  // fibres
  for (let f = 0; f < 260; f++) {
    let x = r.range(0, size), y = r.range(0, size), a = r.range(0, Math.PI * 2);
    const len = r.range(6, 26), tone = -r.range(0.02, 0.05);
    for (let s = 0; s < len; s++) {
      a += r.range(-0.25, 0.25); x += Math.cos(a); y += Math.sin(a);
      px[(((Math.round(y) % size) + size) % size) * size + (((Math.round(x) % size) + size) % size)] += tone;
    }
  }
  const rgb = Buffer.alloc(size * size * 3);
  for (let i = 0; i < px.length; i++) {
    const v = Math.max(0, Math.min(1, px[i]));
    rgb[i * 3] = Math.round(v * 255); rgb[i * 3 + 1] = Math.round(v * 250); rgb[i * 3 + 2] = Math.round(v * 240);
  }
  return encodePNG(size, size, rgb);
}
