// The handwriting engine: glyph definitions → strokes on the page.
// A stroke leaves here as a dense list of points in page millimetres, each with a pen pressure,
// plus how long the pen takes over it. The media module turns those into graphite, ink or paint.
import { HIRAGANA, KATAKANA } from './glyphs/kana.js';
import { KANJI, PARTS } from './glyphs/kanji.js';
import { LATIN, LATIN_WIDTHS } from './glyphs/latin.js';
import { Rng } from './rng.js';

const DEFS = Object.assign({}, PARTS, HIRAGANA, KATAKANA, KANJI, LATIN);

const SMALL = { 'ぁ': 'あ', 'ぃ': 'い', 'ぅ': 'う', 'ぇ': 'え', 'ぉ': 'お', 'っ': 'つ', 'ゃ': 'や', 'ゅ': 'ゆ', 'ょ': 'よ', 'ゎ': 'わ',
  'ァ': 'ア', 'ィ': 'イ', 'ゥ': 'ウ', 'ェ': 'エ', 'ォ': 'オ', 'ッ': 'ツ', 'ャ': 'ヤ', 'ュ': 'ユ', 'ョ': 'ヨ', 'ヮ': 'ワ' };

// ---------- parsing ----------
const cache = new Map();

function parseDef(def, box, out, depth) {
  if (depth > 6) throw new Error('component nesting too deep');
  for (let item of def.split(';')) {
    item = item.trim();
    if (!item) continue;
    if (item[0] === '@') {
      const m = /^@([^:]+?)(?::(.+))?$/.exec(item);
      const name = m[1];
      const sub = PARTS[name] != null ? PARTS[name] : DEFS[name];
      if (sub == null) throw new Error('unknown component ' + name);
      const b = m[2] ? m[2].split(',').map(Number) : [0, 0, 100, 100];
      const nb = [box[0] + (b[0] * box[2]) / 100, box[1] + (b[1] * box[3]) / 100, (b[2] * box[2]) / 100, (b[3] * box[3]) / 100];
      parseDef(sub, nb, out, depth + 1);
      continue;
    }
    let dot = false, end = 's';
    if (item[0] === '.') { dot = true; item = item.slice(1).trim(); }
    const last = item[item.length - 1];
    if (last === '>') { end = 'p'; item = item.slice(0, -1); }
    else if (last === '^') { end = 'h'; item = item.slice(0, -1); }
    const pts = [];
    for (const tok of item.trim().split(/\s+/)) {
      const corner = tok.endsWith('!');
      const [xs, ys] = (corner ? tok.slice(0, -1) : tok).split(',');
      const x = +xs, y = +ys;
      if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('bad point "' + tok + '" in ' + def);
      pts.push({ x: box[0] + (x * box[2]) / 100, y: box[1] + (y * box[3]) / 100, c: corner });
    }
    if (pts.length < 2) throw new Error('stroke needs two points: ' + item);
    out.push({ pts, end, dot });
  }
  return out;
}

export function glyphDef(ch) {
  if (cache.has(ch)) return cache.get(ch);
  let g = null;
  const d = ch.normalize('NFD');
  if (DEFS[ch] != null && typeof DEFS[ch] === 'string') {
    g = { strokes: parseDef(DEFS[ch], [0, 0, 100, 100], [], 0) };
  } else if (SMALL[ch]) {
    const base = glyphDef(SMALL[ch]);
    g = { strokes: base.strokes.map((s) => ({ ...s, pts: s.pts.map((p) => ({ x: 8 + p.x * 0.62, y: 34 + p.y * 0.62, c: p.c })) })), small: true };
  } else if (d.length === 2 && (d[1] === '゙' || d[1] === '゚') && DEFS[d[0]]) {
    const base = parseDef(DEFS[d[0]], [0, 0, 100, 100], [], 0);
    const marks = d[1] === '゙'
      ? parseDef('.80,6 86,17;.90,3 96,14', [0, 0, 100, 100], [], 0)
      : parseDef('89,5 83,9 84,16 90,18 95,13 93,7 88,6', [0, 0, 100, 100], [], 0);
    g = { strokes: base.concat(marks) };
  }
  cache.set(ch, g);
  return g;
}

export function hasGlyph(ch) {
  if (ch === ' ' || ch === '　' || ch === '\n') return true;
  try { return !!glyphDef(ch); } catch (e) { return false; }
}

// ---------- classes & metrics ----------
export function charClass(ch) {
  const c = ch.codePointAt(0);
  if (ch === ' ') return 'space';
  if (ch === '　') return 'wspace';
  if (SMALL[ch]) return 'small';
  if ('、。，．・'.includes(ch)) return 'punct';
  if ('「」『』（）()'.includes(ch)) return 'bracket';
  if (c >= 0x3040 && c <= 0x309f) return 'hira';
  if (c >= 0x30a0 && c <= 0x30ff) return 'kata';
  if (c >= 0x4e00 && c <= 0x9fff) return 'kanji';
  if (ch === '々') return 'kanji';
  return 'latin';
}

// advance widths in em, and the scale a glyph is drawn at inside its cell
export function advance(ch) {
  const k = charClass(ch);
  if (k === 'space') return 0.36;
  if (k === 'wspace') return 0.9;
  if (k === 'punct') return 0.52;
  if (k === 'bracket') return 0.5;
  if (k === 'small') return 0.66;
  if (k === 'hira' || k === 'kata') return ch === 'ー' ? 0.9 : 0.86;
  if (k === 'kanji') return 1.0;
  const L = LATIN_WIDTHS[ch];
  return L != null ? L : 0.6;
}

// ---------- geometry helpers ----------
function catmull(p0, p1, p2, p3, n, out) {
  // centripetal Catmull–Rom from p1 to p2
  const d01 = Math.pow(Math.hypot(p1.x - p0.x, p1.y - p0.y), 0.5) || 1e-4;
  const d12 = Math.pow(Math.hypot(p2.x - p1.x, p2.y - p1.y), 0.5) || 1e-4;
  const d23 = Math.pow(Math.hypot(p3.x - p2.x, p3.y - p2.y), 0.5) || 1e-4;
  const t0 = 0, t1 = d01, t2 = t1 + d12, t3 = t2 + d23;
  for (let i = 1; i <= n; i++) {
    const t = t1 + ((t2 - t1) * i) / n;
    const a1x = ((t1 - t) / (t1 - t0)) * p0.x + ((t - t0) / (t1 - t0)) * p1.x;
    const a1y = ((t1 - t) / (t1 - t0)) * p0.y + ((t - t0) / (t1 - t0)) * p1.y;
    const a2x = ((t2 - t) / (t2 - t1)) * p1.x + ((t - t1) / (t2 - t1)) * p2.x;
    const a2y = ((t2 - t) / (t2 - t1)) * p1.y + ((t - t1) / (t2 - t1)) * p2.y;
    const a3x = ((t3 - t) / (t3 - t2)) * p2.x + ((t - t2) / (t3 - t2)) * p3.x;
    const a3y = ((t3 - t) / (t3 - t2)) * p2.y + ((t - t2) / (t3 - t2)) * p3.y;
    const b1x = ((t2 - t) / (t2 - t0)) * a1x + ((t - t0) / (t2 - t0)) * a2x;
    const b1y = ((t2 - t) / (t2 - t0)) * a1y + ((t - t0) / (t2 - t0)) * a2y;
    const b2x = ((t3 - t) / (t3 - t1)) * a2x + ((t - t1) / (t3 - t1)) * a3x;
    const b2y = ((t3 - t) / (t3 - t1)) * a2y + ((t - t1) / (t3 - t1)) * a3y;
    out.push({
      x: ((t2 - t) / (t2 - t1)) * b1x + ((t - t1) / (t2 - t1)) * b2x,
      y: ((t2 - t) / (t2 - t1)) * b1y + ((t - t1) / (t2 - t1)) * b2y,
    });
  }
}

// control points (with corners) → dense polyline; returns index where the hook starts
export function densify(pts, step) {
  const out = [{ x: pts[0].x, y: pts[0].y }];
  let hookStart = -1;
  let runStart = 0;
  for (let i = 1; i < pts.length; i++) {
    const isEnd = i === pts.length - 1 || pts[i].c;
    if (!isEnd) continue;
    const run = pts.slice(runStart, i + 1);
    for (let k = 0; k < run.length - 1; k++) {
      const p1 = run[k], p2 = run[k + 1];
      const p0 = k > 0 ? run[k - 1] : { x: 2 * p1.x - p2.x, y: 2 * p1.y - p2.y };
      const p3 = k < run.length - 2 ? run[k + 2] : { x: 2 * p2.x - p1.x, y: 2 * p2.y - p1.y };
      const n = Math.max(2, Math.ceil(Math.hypot(p2.x - p1.x, p2.y - p1.y) / step));
      catmull(p0, p1, p2, p3, n, out);
    }
    if (pts[i].c) hookStart = out.length - 1;
    runStart = i;
  }
  return { pts: out, lastCorner: hookStart };
}

// ---------- one glyph instance ----------
// opts: x, y = top-left of the em box (mm); size = em (mm); rng; slant; tidy (0 messy .. 1 neat)
export function glyphStrokes(ch, o) {
  const g = glyphDef(ch);
  if (!g) return [];
  const r = o.rng;
  const tidy = o.tidy == null ? 0.6 : o.tidy;
  const mess = 1 - tidy;
  const k = charClass(ch);
  let scale = 1;
  let dy = 0;
  if (k === 'hira' || k === 'kata') { scale = 0.92; dy = 3; }
  if (k === 'latin') { scale = 1; }
  const rot = r.sym(0.03 + mess * 0.04) + (o.rot || 0);
  const sc = scale * (1 + r.sym(0.035 + mess * 0.03));
  const ox = r.sym(1.4 + mess * 2), oy = r.sym(1.4 + mess * 2) + dy;
  const slant = o.slant == null ? 0.075 : o.slant;
  const cs = Math.cos(rot), sn = Math.sin(rot);
  const S = o.size / 100;
  const out = [];
  g.strokes.forEach((st, si) => {
    const jx = r.sym(0.6), jy = r.sym(0.6);
    const ctrl = st.pts.map((p) => {
      // glyph space: jitter, slant (右上がり), rotate + scale about the centre
      let x = p.x + jx + r.gauss(0.55 + mess * 0.7);
      let y = p.y + jy + r.gauss(0.55 + mess * 0.7);
      y -= slant * (x - 50);
      x = (x - 50) * sc; y = (y - 50) * sc;
      const X = x * cs - y * sn + 50 + ox, Y = x * sn + y * cs + 50 + oy;
      return { x: o.x + X * S, y: o.y + Y * S, c: p.c };
    });
    const { pts, lastCorner } = densify(ctrl, 0.12 * Math.max(0.4, o.size / 5));
    // はらい: a little longer than it needs to be
    if (st.end === 'p' && pts.length > 2) {
      const a = pts[pts.length - 3], b = pts[pts.length - 1];
      const L = Math.hypot(b.x - a.x, b.y - a.y) || 1;
      const ext = o.size * 0.05;
      for (let i = 1; i <= 4; i++) pts.push({ x: b.x + ((b.x - a.x) / L) * ext * (i / 4), y: b.y + ((b.y - a.y) / L) * ext * (i / 4) });
    }
    // arc length
    let len = 0;
    const s = [0];
    for (let i = 1; i < pts.length; i++) { len += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); s.push(len); }
    const hookS = st.end === 'h' && lastCorner > 0 ? s[lastCorner] / len : 1;
    const pn = r.range(0, 100);
    const pres = pts.map((p, i) => {
      const t = len > 0 ? s[i] / len : 0;
      let pr = 0.62 + 0.38 * smooth(0, st.dot ? 0.5 : 0.1, t);
      pr *= 1 + 0.07 * Math.sin(pn + t * 7.1) + 0.04 * Math.sin(pn * 1.7 + t * 17.3);
      if (st.dot) pr *= 1 - 0.7 * smooth(0.75, 1, t);
      else if (st.end === 'p') pr *= 1 - 0.93 * smooth(0.5, 1, t);
      else if (st.end === 'h') pr *= 1 - 0.85 * smooth(hookS, 1, t);
      else pr *= 1 - 0.2 * smooth(0.86, 1, t);
      return pr;
    });
    out.push({ pts: pts.map((p, i) => [p.x, p.y, pres[i]]), len, dot: st.dot, end: st.end, index: si });
  });
  return out;
}

export function smooth(a, b, t) {
  const x = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
}

export { DEFS };
