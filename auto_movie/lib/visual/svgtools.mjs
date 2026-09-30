// Small SVG string helpers (no DOM in Node): namespace ids, strip comments, paperize whites, smooth curves.
import { COLORS } from './theme.mjs';

/** Prefix every id (and its url(#…) / href="#…" references) so several SVGs can live in one page. */
export function prefixIds(svg, prefix) {
  const ids = [...svg.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]);
  let out = svg;
  for (const id of new Set(ids)) {
    const esc = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    out = out
      .replace(new RegExp(`\\bid="${esc}"`, 'g'), `id="${prefix}${id}"`)
      .replace(new RegExp(`url\\(#${esc}\\)`, 'g'), `url(#${prefix}${id})`)
      .replace(new RegExp(`(xlink:)?href="#${esc}"`, 'g'), (m, x) => `${x || ''}href="#${prefix}${id}"`);
  }
  return out;
}

export const stripComments = (svg) => svg.replace(/<!--[\s\S]*?-->/g, '');
export const designMemo = (svg) => (svg.match(/<!--([\s\S]*?)-->/) || [, ''])[1].trim();

/** Make the paper-white cut-outs match the page (the illustration's #fff would read as a brighter patch). */
export const paperize = (svg) => svg.replace(/(fill|stroke)="#(?:fff|ffffff)"/gi, `$1="${COLORS.paper}"`);

/** Remove the fixed size / xmlns noise so CSS can size the SVG. */
export function forEmbedding(svg, { prefix, extraAttrs = '' } = {}) {
  let s = stripComments(svg);
  s = paperize(s);
  s = s.replace(/<svg\b([^>]*)>/, (m, attrs) => {
    const vb = (attrs.match(/viewBox="[^"]+"/) || [''])[0];
    return `<svg xmlns="http://www.w3.org/2000/svg" ${vb} preserveAspectRatio="xMidYMid meet" ${extraAttrs}>`;
  });
  return prefix ? prefixIds(s, prefix) : s;
}

/** Catmull-Rom → cubic Bézier through points [[x,y],…]; returns an SVG path "d". */
export function smoothPath(pts, tension = 0.5) {
  if (pts.length < 2) return '';
  const d = [`M${f(pts[0][0])} ${f(pts[0][1])}`];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + ((p2[0] - p0[0]) * tension) / 3 * 1, p1[1] + ((p2[1] - p0[1]) * tension) / 3 * 1];
    const c2 = [p2[0] - ((p3[0] - p1[0]) * tension) / 3 * 1, p2[1] - ((p3[1] - p1[1]) * tension) / 3 * 1];
    d.push(`C${f(c1[0])} ${f(c1[1])} ${f(c2[0])} ${f(c2[1])} ${f(p2[0])} ${f(p2[1])}`);
  }
  return d.join(' ');
}
const f = (x) => Math.round(x * 10) / 10;
export const fmt = f;

/** A hand-drawn-looking line between two points: slight bow and overshoot, deterministic per seed. */
export function pencilLine(x1, y1, x2, y2, seed = 1, bow = 2.2) {
  const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len, ny = dx / len;
  const s = Math.sin(seed * 12.9898) * 43758.5453; const r = s - Math.floor(s) - 0.5;
  const ox = dx / len * 1.6, oy = dy / len * 1.6;
  const mx = (x1 + x2) / 2 + nx * bow * r * 2, my = (y1 + y2) / 2 + ny * bow * r * 2;
  return `M${f(x1 - ox * 0.4)} ${f(y1 - oy * 0.4)} Q${f(mx)} ${f(my)} ${f(x2 + ox)} ${f(y2 + oy)}`;
}

/** Wobbly closed rectangle path (pencil-drawn box). */
export function pencilRect(x, y, w, h, seed = 1, jit = 2.2) {
  const j = (k) => { const s = Math.sin((seed * 31 + k) * 78.233) * 43758.5453; return (s - Math.floor(s) - 0.5) * 2 * jit; };
  const p = [[x + j(1), y + j(2)], [x + w + j(3), y + j(4)], [x + w + j(5), y + h + j(6)], [x + j(7), y + h + j(8)]];
  return `M${f(p[0][0])} ${f(p[0][1])} L${f(p[1][0])} ${f(p[1][1])} L${f(p[2][0])} ${f(p[2][1])} L${f(p[3][0])} ${f(p[3][1])} L${f(p[0][0] + 1.5)} ${f(p[0][1] + 8)}`;
}

/** Shared filter defs giving vector shapes a pencil wobble (used by charts and icons). */
export const WOBBLE_DEFS = (id, scale = 3.2, freq = '0.022 0.028', seed = 3) =>
  `<filter id="${id}" x="-3%" y="-3%" width="106%" height="106%"><feTurbulence type="fractalNoise" baseFrequency="${freq}" numOctaves="2" seed="${seed}" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${scale}" xChannelSelector="R" yChannelSelector="G"/></filter>`;
