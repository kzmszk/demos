// Japanese web fonts without downloads: take Noto Sans CJK JP from the system (.ttc), cut the first face (the JP one) out
// of the collection and subset it to exactly the characters the video uses → a few hundred KB of WOFF2 per weight.
import fs from 'node:fs';
import path from 'node:path';
import subsetFont from 'subset-font';
import { ensureDir, sha1, ROOT } from '../util.mjs';

const DIRS = ['/usr/share/fonts/opentype/noto', '/usr/share/fonts/noto-cjk', '/usr/share/fonts/truetype/noto', '/usr/local/share/fonts'];
export const WEIGHTS = { 400: 'Regular', 500: 'Medium', 700: 'Bold', 900: 'Black' };

function findFont(weightName) {
  for (const d of DIRS) {
    for (const f of [`NotoSansCJK-${weightName}.ttc`, `NotoSansCJKjp-${weightName}.otf`]) {
      const p = path.join(d, f);
      if (fs.existsSync(p)) return p;
    }
  }
  throw new Error(`Noto Sans CJK ${weightName} not found on this machine (install fonts-noto-cjk)`);
}

/** Extract face `index` of a TrueType/OpenType collection as a standalone sfnt. */
export function extractFromTTC(buf, index = 0) {
  if (buf.toString('ascii', 0, 4) !== 'ttcf') return buf;
  const num = buf.readUInt32BE(8);
  if (index >= num) throw new Error('face index out of range');
  const off = buf.readUInt32BE(12 + index * 4);
  const numTables = buf.readUInt16BE(off + 4);
  const recs = [];
  for (let i = 0; i < numTables; i++) {
    const r = off + 12 + i * 16;
    recs.push({ tag: buf.subarray(r, r + 4), sum: buf.readUInt32BE(r + 4), offset: buf.readUInt32BE(r + 8), length: buf.readUInt32BE(r + 12) });
  }
  const headerLen = 12 + numTables * 16;
  let pos = (headerLen + 3) & ~3;
  const out = [Buffer.alloc(headerLen)];
  buf.copy(out[0], 0, off, off + 12);
  const placed = [];
  for (const r of recs) {
    placed.push(pos);
    const padded = (r.length + 3) & ~3;
    const b = Buffer.alloc(padded);
    buf.copy(b, 0, r.offset, r.offset + r.length);
    out.push(b);
    pos += padded;
  }
  recs.forEach((r, i) => {
    const w = 12 + i * 16;
    r.tag.copy(out[0], w);
    out[0].writeUInt32BE(r.sum, w + 4);
    out[0].writeUInt32BE(placed[i], w + 8);
    out[0].writeUInt32BE(r.length, w + 12);
  });
  // first block must be padded to 4 bytes
  const head = Buffer.alloc((headerLen + 3) & ~3);
  out[0].copy(head);
  return Buffer.concat([head, ...out.slice(1)]);
}

const COMMON = ' 　0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.,:;!?%()[]{}<>+-–—=×÷/\\|&@#*_~^"\'`、。，．・：；！？％（）「」『』【】〔〕〈〉《》…‥ー〜～→←↑↓↔✓✔✕✖▶●○◎■□▲△▼▽★☆♪♬※＊＋－＝／＜＞＆＃＠';
const HIRAGANA = Array.from({ length: 0x3097 - 0x3041 }, (_, i) => String.fromCharCode(0x3041 + i)).join('');
const KATAKANA = Array.from({ length: 0x30ff - 0x30a1 }, (_, i) => String.fromCharCode(0x30a1 + i)).join('');

/**
 * Build WOFF2 subsets for the given weights. Returns { css, files } where files are written into `outDir`.
 * `fontFamily` is the CSS family name to declare.
 */
export async function buildFonts({ text, outDir, weights = [500, 700, 900], family = 'AM Sans', urlPrefix = 'fonts/' }) {
  ensureDir(outDir);
  const chars = [...new Set([...(COMMON + HIRAGANA + KATAKANA + text)])].join('');
  const cacheDir = ensureDir(path.join(ROOT, '.cache', 'fonts'));
  const files = [];
  const faces = [];
  for (const w of weights) {
    const src = findFont(WEIGHTS[w]);
    const key = sha1([src, chars]).slice(0, 12);
    const cached = path.join(cacheDir, `${w}-${key}.woff2`);
    if (!fs.existsSync(cached)) {
      const sfnt = extractFromTTC(fs.readFileSync(src), 0);
      const woff2 = await subsetFont(sfnt, chars, { targetFormat: 'woff2' });
      fs.writeFileSync(cached, woff2);
    }
    const name = `am-sans-${w}.woff2`;
    fs.copyFileSync(cached, path.join(outDir, name));
    files.push(name);
    faces.push(`@font-face{font-family:"${family}";font-weight:${w};font-style:normal;font-display:block;src:url("${urlPrefix}${name}") format("woff2");}`);
  }
  return { css: faces.join('\n'), files, family, chars: chars.length };
}
