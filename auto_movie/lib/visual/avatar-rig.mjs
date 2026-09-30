// Character rig: the SVG contract shared by the avatar prompt, the validator, the state sheet and the compositor.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readText } from '../util.mjs';

export const RIG = {
  eyes: ['eyes-open', 'eyes-blink', 'eyes-smile', 'eyes-wide'],
  brows: ['brows-normal', 'brows-up', 'brows-worry'],
  mouths: ['mouth-closed', 'mouth-a', 'mouth-i', 'mouth-o', 'mouth-smile', 'mouth-wow'],
  parts: ['body', 'mic', 'head-rig', 'hair-back', 'head', 'hair-front', 'headphones'],
  pivot: 'neck-pivot',
};
export const REQUIRED_IDS = [...RIG.parts, ...RIG.eyes, ...RIG.brows, ...RIG.mouths, RIG.pivot, 'art'];

const ALLOWED_COLORS = new Set(['#3d3d3d', '#fff176', '#d64545', '#fff', '#ffffff', 'none', 'currentcolor', 'transparent']);

/** Returns a list of problems (empty = usable). */
export function validateRigSVG(svg) {
  const problems = [];
  if (!/<svg[^>]*viewBox="0 0 300 380"/.test(svg)) problems.push('viewBox must be "0 0 300 380"');
  for (const id of REQUIRED_IDS) if (!new RegExp(`\\bid="${id}"`).test(svg)) problems.push(`missing id="${id}"`);
  if (/<text\b|<image\b|<script\b|<style\b|<foreignObject\b/.test(svg)) problems.push('forbidden element (text/image/script/style/foreignObject)');
  const colors = new Set([...svg.matchAll(/(?:fill|stroke|stop-color)="(#[0-9a-fA-F]{3,8}|[a-z]+)"/g)].map((m) => m[1].toLowerCase()));
  for (const c of colors) if (!ALLOWED_COLORS.has(c)) problems.push(`color outside palette: ${c}`);
  return problems;
}

export const avatarPath = (id) => path.join(ROOT, 'assets', 'cast', `${id}.svg`);
export const loadAvatar = (id) => readText(avatarPath(id));

/** Read the neck pivot (cx, cy) out of an avatar SVG. */
export function neckPivot(svg) {
  const m = svg.match(/<circle[^>]*id="neck-pivot"[^>]*>/);
  if (!m) return [150, 250];
  const cx = m[0].match(/cx="([\d.-]+)"/), cy = m[0].match(/cy="([\d.-]+)"/);
  return [cx ? +cx[1] : 150, cy ? +cy[1] : 250];
}

/**
 * Build an HTML contact sheet that shows the avatar in every rig state (eyes × mouths × brows samples),
 * to check by eye that the parts line up. Scoped CSS hides all state groups except the chosen ones.
 */
export function stateSheetHTML(svg, { title = '' } = {}) {
  const hide = (cls, keep) => {
    const all = [...RIG.eyes, ...RIG.brows, ...RIG.mouths];
    return all.filter((id) => !keep.includes(id)).map((id) => `.${cls} #${id}`).join(',') + '{display:none}';
  };
  const cells = [];
  const combos = [
    ['eyes-open', 'brows-normal', 'mouth-closed'],
    ['eyes-open', 'brows-normal', 'mouth-a'],
    ['eyes-open', 'brows-normal', 'mouth-i'],
    ['eyes-open', 'brows-normal', 'mouth-o'],
    ['eyes-smile', 'brows-normal', 'mouth-smile'],
    ['eyes-wide', 'brows-up', 'mouth-wow'],
    ['eyes-blink', 'brows-normal', 'mouth-closed'],
    ['eyes-open', 'brows-worry', 'mouth-i'],
  ];
  const css = combos.map((k, i) => hide(`c${i}`, k)).join('\n');
  combos.forEach((k, i) => cells.push(`<figure class="c${i}">${svg}<figcaption>${k.join(' · ')}</figcaption></figure>`));
  return `<!doctype html><meta charset="utf-8"><title>${title}</title>
<style>
body{margin:0;background:#fbf7ee;font:12px/1.4 sans-serif;color:#555}
main{display:grid;grid-template-columns:repeat(4,300px);gap:6px;padding:8px}
figure{margin:0}figure svg{width:300px;height:380px;display:block;background:#fbf7ee;outline:1px solid #e6dfcf}
figcaption{padding:2px 4px}
${css}
</style><main>${cells.join('')}</main>`;
}
