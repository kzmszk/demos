// Text → handwritten stroke ops. Mini-markup inside strings:
//   \n  new line          ^{..} superscript        _{..} subscript
//   ~~..~~ written, then crossed out (a mistake left in)
//   {{..}} written slower and a little bigger (emphasis)
import { glyphStrokes, advance, charClass, hasGlyph } from './hand.js';
import { Rng } from './rng.js';

const NO_LINE_START = '、。，．」』）)ー・…ぁぃぅぇぉっゃゅょァィゥェォッャュョ?!';

function tokenize(text) {
  // → array of {ch, sup, sub, strike (group id), emph}
  const out = [];
  let i = 0, strike = 0, emph = false, sgroup = 0;
  while (i < text.length) {
    if (text.startsWith('~~', i)) { if (strike) strike = 0; else strike = ++sgroup; i += 2; continue; }
    if (text.startsWith('{{', i)) { emph = true; i += 2; continue; }
    if (text.startsWith('}}', i)) { emph = false; i += 2; continue; }
    if ((text[i] === '^' || text[i] === '_') && text[i + 1] === '{') {
      const mode = text[i] === '^' ? 'sup' : 'sub';
      const end = text.indexOf('}', i + 2);
      for (const ch of text.slice(i + 2, end)) out.push({ ch, [mode]: true, strike, emph });
      i = end + 1;
      continue;
    }
    const cp = text.codePointAt(i);
    const ch = String.fromCodePoint(cp);
    out.push({ ch, strike, emph });
    i += ch.length;
  }
  return out;
}

// opts: x, y (mm, top-left of first line), size (mm), lh (line height, em), width (wrap, mm),
//       rot (radians, whole block), tidy, slant, medium, color, w (line width mm), speed (mm/s),
//       seed, vertical (true → top-to-bottom columns, right to left), indent (em, first line)
export function writeText(text, o) {
  const rng = new Rng(o.seed != null ? o.seed : text);
  const size = o.size || 5;
  const lh = (o.lh || 1.62) * size;
  const toks = tokenize(text);
  const placed = []; // {ch, x, y, s} in block space (before rotation)
  let line = 0, x = (o.indent || 0) * size;
  let lineDrift = 0;
  const maxW = o.width || 1e9;
  const lines = [[]];
  // --- horizontal layout with wrapping
  if (!o.vertical) {
    for (let k = 0; k < toks.length; k++) {
      const t = toks[k];
      if (t.ch === '\n') { line++; x = 0; lines.push([]); continue; }
      const s = size * (t.sup || t.sub ? 0.58 : 1) * (t.emph ? 1.12 : 1);
      const adv = advance(t.ch) * s * (1 + rng.sym(0.04)) * (o.track || 1);
      if (x + adv > maxW && x > 0 && !NO_LINE_START.includes(t.ch) && t.ch !== ' ') { line++; x = 0; lines.push([]); }
      if (x === 0 && t.ch === ' ') continue;
      const yOff = t.sup ? -size * 0.22 : t.sub ? size * 0.5 : 0;
      lines[lines.length - 1].push({ ...t, x, y: line * lh + yOff + (s < size ? 0 : 0), s, line });
      x += adv;
    }
  } else {
    // vertical: columns from right to left, x is the column's right edge offset (negative)
    let col = 0, y = 0;
    for (const t of toks) {
      if (t.ch === '\n') { col++; y = 0; lines.push([]); continue; }
      const s = size;
      const adv = (t.ch === 'ー' || '、。'.includes(t.ch) ? 0.8 : charClass(t.ch) === 'kanji' ? 1.0 : 0.9) * s;
      if (y + adv > maxW && y > 0 && !NO_LINE_START.includes(t.ch)) { col++; y = 0; lines.push([]); }
      lines[lines.length - 1].push({ ...t, x: -col * lh, y, s, line: col, vert: true });
      y += adv;
    }
  }
  // --- per-line drift (baseline wobble, gentle rise to the right)
  const ops = [];
  const cs = Math.cos(o.rot || 0), sn = Math.sin(o.rot || 0);
  const medium = o.medium || 'pencil';
  const color = o.color;
  const width = o.w || (medium === 'ink' ? 0.3 : 0.5) * Math.max(0.72, Math.min(1.6, Math.pow(size / 5, 0.7)));
  const speed = o.speed || 38;
  let first = true;
  const strikeGroups = new Map();
  lines.forEach((ln, li) => {
    const rise = (o.rise != null ? o.rise : -0.012) + rng.sym(0.008);
    const drift = rng.sym(0.25);
    ln.forEach((g, gi) => {
      if (g.ch === ' ' || g.ch === '　') return;
      let gx = g.x, gy = g.y;
      if (!g.vert) gy += drift + rise * g.x + Math.sin(g.x * 0.13 + li) * 0.15;
      let ch = g.ch;
      let rot = 0;
      if (g.vert) {
        if (ch === 'ー' || ch === '〜' || ch === '…' || ch === '(' || ch === ')') rot = Math.PI / 2;
        gx += -size; // column cell to the left of the column edge
        if ('、。'.includes(ch)) { gx += size * 0.55; gy -= size * 0.5; }
      }
      if (!hasGlyph(ch)) { console.warn('no glyph', ch); return; }
      const bx = gx, by = gy;
      const strokes = glyphStrokes(ch, { x: 0, y: 0, size: g.s, rng: rng.fork(li * 1000 + gi), tidy: o.tidy, slant: o.slant, rot });
      for (let si = 0; si < strokes.length; si++) {
        const st = strokes[si];
        const pts = new Float32Array(st.pts.length * 3);
        for (let i = 0; i < st.pts.length; i++) {
          const px = st.pts[i][0] + bx, py = st.pts[i][1] + by;
          pts[i * 3] = o.x + px * cs - py * sn;
          pts[i * 3 + 1] = o.y + px * sn + py * cs;
          pts[i * 3 + 2] = st.pts[i][2];
        }
        const emph = g.emph ? 1.35 : 1;
        const dur = (0.05 + st.len / speed) * emph * (st.dot ? 0.8 : 1);
        const gap = first ? 0.2 : si === 0 ? (gi === 0 ? 0.42 : 0.12 + rng.range(0, 0.08)) : 0.06 + rng.range(0, 0.05);
        first = false;
        ops.push({ t: 'stroke', medium, color, w: width * (g.s < size ? 0.8 : 1), pts, len: st.len, dur, gap, tool: medium === 'ink' ? 'pen' : 'pencil', ch: si === 0 ? ch : undefined });
      }
      if (g.strike) {
        if (!strikeGroups.has(g.strike)) strikeGroups.set(g.strike, []);
        strikeGroups.get(g.strike).push({ x: bx, y: by, s: g.s, adv: advance(ch) * g.s, line: g.line });
      }
    });
  });
  // --- cross-outs, after the words they cancel (two quick strokes, a bit angry)
  for (const [, cells] of strikeGroups) {
    const byLine = new Map();
    for (const c of cells) { if (!byLine.has(c.line)) byLine.set(c.line, []); byLine.get(c.line).push(c); }
    for (const [, cs2] of byLine) {
      const x0 = cs2[0].x - 0.6, x1 = cs2[cs2.length - 1].x + cs2[cs2.length - 1].adv + 0.4;
      const yc = cs2[0].y + size * 0.52;
      for (let k = 0; k < 2; k++) {
        const pts = [];
        const n = 18;
        const yA = yc + rng.sym(0.6) + (k ? size * 0.12 : -size * 0.08), yB = yc + rng.sym(0.6) + (k ? -size * 0.06 : size * 0.1);
        for (let i = 0; i <= n; i++) {
          const t = i / n;
          const px = x0 + (x1 - x0) * t, py = yA + (yB - yA) * t + Math.sin(t * 9 + k) * 0.25;
          pts.push(o.x + px * cs - py * sn, o.y + px * sn + py * cs, 0.85 + 0.15 * Math.sin(t * 3.1));
        }
        const len = Math.hypot(x1 - x0, yB - yA);
        ops.push({ t: 'stroke', medium, color, w: width * 1.1, pts: Float32Array.from(pts), len, dur: 0.05 + len / 90, gap: k ? 0.08 : 0.3, tool: medium === 'ink' ? 'pen' : 'pencil' });
      }
    }
  }
  // bounding box (block space → page)
  let maxX = 0, maxY = 0;
  for (const ln of lines) for (const g of ln) { maxX = Math.max(maxX, g.x + g.s); maxY = Math.max(maxY, g.y + g.s); }
  ops.box = { w: maxX, h: maxY, lines: lines.length };
  return ops;
}

// Measure without drawing (for layout decisions).
export function measure(text, size, width) {
  const ops = writeText(text, { x: 0, y: 0, size, width, seed: 1 });
  return ops.box;
}
