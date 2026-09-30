// Avatar markup: the cast SVGs made unique for the page, plus the yellow "halo" that marks whoever is speaking.
import { W, AVATAR } from './theme.mjs';
import { loadAvatar, RIG } from './avatar-rig.mjs';
import { forEmbedding } from './svgtools.mjs';
import { esc } from '../util.mjs';

export const DEFAULT_STATE = { eyes: 'eyes-open', brows: 'brows-normal', mouth: 'mouth-closed' };

/** ids of state groups that start hidden (everything except the defaults) */
export function hiddenStateIds(prefix) {
  const all = [...RIG.eyes, ...RIG.brows, ...RIG.mouths];
  const keep = new Set(Object.values(DEFAULT_STATE));
  return all.filter((id) => !keep.has(id)).map((id) => `${prefix}${id}`);
}

const HALO = `<svg viewBox="0 0 100 100" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible"><path d="M50 3 C74 2 97 22 96 48 C95 76 74 98 48 97 C22 96 3 74 4 49 C5 24 26 4 50 3 Z" fill="#fff176" style="mix-blend-mode:multiply"/></svg>`;

export function avatarHTML(member, side) {
  const prefix = `${member.id}-`;
  const svg = forEmbedding(loadAvatar(member.id), { prefix });
  const x = side === 'left' ? 24 : W - 24 - AVATAR.w;
  return `<div class="avatar" id="av-${side}" style="left:${x}px">
    <div class="halo" id="halo-${side}">${HALO}</div>
    <div class="avbody" id="avbody-${side}" style="position:absolute;inset:0">${svg}</div>
  </div>`;
}
