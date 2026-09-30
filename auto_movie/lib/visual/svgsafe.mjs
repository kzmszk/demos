// Allow-list sanitizer for SVG drawn by a model.
//
// The illustrations end up inline in a page that headless Chrome renders on this PC, and the theme that shapes them can come from a
// stranger (a video made on request). So a drawing is never trusted: it is tokenized strictly and REBUILT from an allow-list of
// elements and attributes with a pattern per attribute. Unknown elements are dropped together with everything inside them; malformed
// markup (DOCTYPE, CDATA, processing instructions, stray "<", unbalanced tags) rejects the whole drawing so the repair loop can ask again.
//
//   sanitizeSVG(text) → { svg, memo }   (memo = the first comment, the illustrator's design note, as plain text)
//   throws Error('svg: …') when the drawing cannot be made safe.
//
// The allow-list is what the illustration prompt asks for (paths, groups, one wobble filter, clip paths) plus the other basic shapes.

const ELEMENTS = new Set([
  'svg', 'g', 'defs', 'filter', 'feTurbulence', 'feDisplacementMap', 'clipPath', 'use',
  'path', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon',
]);

const NUM = '[-+]?(?:\\d+\\.?\\d*|\\.\\d+)(?:[eE][-+]?\\d+)?';
const LEN = new RegExp(`^${NUM}(?:%|px)?$`);
const NUMBER = new RegExp(`^${NUM}$`);
const NUMLIST = /^[\d\s.,eE+-]{0,20000}$/;
const ID = /^[A-Za-z][\w.-]{0,40}$/;
const PAINT = /^(?:none|currentColor|transparent|#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})$/;
const URL_REF = /^url\(#[A-Za-z][\w.-]{0,40}\)$/;
const TRANSFORM = /^(?:\s*(?:matrix|translate|scale|rotate|skewX|skewY)\s*\([\d\s.,eE+-]*\)\s*){0,12}$/;
const oneOf = (...words) => new RegExp(`^(?:${words.join('|')})$`);

const ATTRIBUTES = {
  viewBox: NUMLIST, id: ID, class: /^[A-Za-z][\w -]{0,40}$/,
  x: LEN, y: LEN, width: LEN, height: LEN, dx: LEN, dy: LEN, cx: LEN, cy: LEN, r: LEN, rx: LEN, ry: LEN, x1: LEN, y1: LEN, x2: LEN, y2: LEN,
  d: /^[MmLlHhVvCcSsQqTtAaZz\d\s.,eE+-]{0,20000}$/, points: NUMLIST, transform: TRANSFORM,
  opacity: NUMBER, 'fill-opacity': NUMBER, 'stroke-opacity': NUMBER, 'stroke-width': LEN, 'stroke-miterlimit': NUMBER, 'stroke-dashoffset': LEN,
  'stroke-dasharray': NUMLIST, pathLength: NUMBER, 'vector-effect': oneOf('non-scaling-stroke'),
  fill: PAINT, stroke: PAINT, 'fill-rule': oneOf('nonzero', 'evenodd'), 'clip-rule': oneOf('nonzero', 'evenodd'),
  'stroke-linecap': oneOf('butt', 'round', 'square'), 'stroke-linejoin': oneOf('miter', 'round', 'bevel'),
  filter: URL_REF, 'clip-path': URL_REF, href: /^#[A-Za-z][\w.-]{0,40}$/,
  style: /^\s*mix-blend-mode\s*:\s*multiply\s*;?\s*$/,
  // the wobble filter
  type: oneOf('fractalNoise', 'turbulence'), baseFrequency: NUMLIST, numOctaves: /^\d{1,2}$/, seed: NUMBER, stitchTiles: oneOf('stitch', 'noStitch'),
  result: ID, in: /^(?:SourceGraphic|SourceAlpha|[A-Za-z][\w.-]{0,40})$/, in2: /^(?:SourceGraphic|SourceAlpha|[A-Za-z][\w.-]{0,40})$/, scale: NUMBER,
  xChannelSelector: oneOf('R', 'G', 'B', 'A'), yChannelSelector: oneOf('R', 'G', 'B', 'A'),
  filterUnits: oneOf('userSpaceOnUse', 'objectBoundingBox'), primitiveUnits: oneOf('userSpaceOnUse', 'objectBoundingBox'), clipPathUnits: oneOf('userSpaceOnUse', 'objectBoundingBox'),
};
// `style` keeps one fixed value whatever the spelling
const CANONICAL = { style: 'mix-blend-mode:multiply' };

const TAG = /<(\/?)([A-Za-z][\w:.-]*)((?:\s+[A-Za-z_:][\w:.-]*\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)>/y;
const ATTR = /\s+([A-Za-z_:][\w:.-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
const MAX_TOKENS = 12000, MAX_DEPTH = 24, MAX_CHARS = 400000;

const bad = (why) => new Error(`svg: ${why}`);

function cleanAttrs(raw) {
  const out = [];
  const seen = new Set();
  for (const m of raw.matchAll(ATTR)) {
    let name = m[1];
    const value = (m[2] ?? m[3] ?? '').trim();
    if (name === 'xlink:href') name = 'href';
    const rule = ATTRIBUTES[name];
    if (!rule || seen.has(name) || value.length > 20000 || !rule.test(value)) continue;
    seen.add(name);
    out.push(`${name}="${CANONICAL[name] ?? value}"`);
  }
  return out;
}

export function sanitizeSVG(text) {
  if (typeof text !== 'string') throw bad('not a string');
  if (text.length > MAX_CHARS) throw bad('too large');
  const start = text.indexOf('<svg'), end = text.lastIndexOf('</svg>');
  if (start < 0 || end < start) throw bad('no <svg> element');
  let src = text.slice(start, end + 6);

  let memo = '';
  const first = src.match(/<!--([\s\S]*?)-->/);
  if (first) memo = first[1].replace(/[<>&"'\\-]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 600);
  src = src.replace(/<!--[\s\S]*?-->/g, '');
  if (/<!|<\?/.test(src)) throw bad('DOCTYPE, CDATA or processing instruction');

  const out = [];
  const open = [];          // names of the open elements (kept and skipped alike)
  let skip = 0;             // depth inside a dropped element
  let tokens = 0, pos = 0, sawRoot = false;
  while (pos < src.length) {
    const lt = src.indexOf('<', pos);
    if (lt < 0) break;      // trailing text: dropped
    // text between tags is dropped (no <text> in the allow-list)
    TAG.lastIndex = lt;
    const m = TAG.exec(src);
    if (!m) throw bad('malformed tag');
    pos = TAG.lastIndex;
    if (++tokens > MAX_TOKENS) throw bad('too many elements');
    const [, closing, name, rawAttrs, selfClose] = m;
    if (closing) {
      if (selfClose || rawAttrs.trim()) throw bad('malformed closing tag');
      if (open.pop() !== name) throw bad('unbalanced tags');
      if (skip) skip--; else out.push(`</${name}>`);
      continue;
    }
    if (sawRoot && !open.length) throw bad('content after the root element');
    if (open.length >= MAX_DEPTH) throw bad('nested too deeply');
    if (!selfClose) open.push(name);
    if (skip || !ELEMENTS.has(name)) { if (!selfClose) skip++; continue; }
    if (!sawRoot) {
      if (name !== 'svg' || out.length) throw bad('the first element must be <svg>');
      sawRoot = true;
      const attrs = cleanAttrs(rawAttrs).filter((a) => a.startsWith('viewBox='));
      if (!attrs.length) throw bad('the root needs a viewBox');
      out.push(`<svg xmlns="http://www.w3.org/2000/svg" ${attrs[0]}${selfClose ? '/' : ''}>`);
      continue;
    }
    const attrs = cleanAttrs(rawAttrs);
    out.push(`<${name}${attrs.length ? ' ' + attrs.join(' ') : ''}${selfClose ? '/' : ''}>`);
  }
  if (!sawRoot) throw bad('no <svg> root');
  if (open.length) throw bad('unclosed tags');
  return { svg: out.join(''), memo };
}
