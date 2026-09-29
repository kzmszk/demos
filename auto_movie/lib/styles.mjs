import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readJSON } from './util.mjs';

export function loadStyles() {
  const dir = path.join(ROOT, 'styles');
  return Object.fromEntries(fs.readdirSync(dir).filter((f) => f.endsWith('.json')).map((f) => { const s = readJSON(path.join(dir, f)); return [s.id, s]; }));
}
export const loadSeries = (id = 'lifehack') => readJSON(path.join(ROOT, 'series', `${id}.json`));

/** Series cast reduced to what the style needs (monologue → host only). */
export function castFor(series, style) {
  const cast = { host: series.cast.host };
  if (style.speakers.includes('guest')) cast.guest = series.cast.guest;
  return cast;
}
