#!/usr/bin/env node
// Draw the series cast with Opus (one call per character) and save assets/cast/<id>.svg.
//   node tools/gen-avatars.mjs [series=lifehack] [--only mio] [--force]
import path from 'node:path';
import { ROOT, readJSON, readText, writeText, ensureDir, exists, log, pool } from '../lib/util.mjs';
import { askSVG } from '../lib/llm.mjs';
import { validateRigSVG, avatarPath } from '../lib/visual/avatar-rig.mjs';

const args = process.argv.slice(2);
const seriesId = args.find((a) => !a.startsWith('--')) || 'lifehack';
const only = args.includes('--only') ? args[args.indexOf('--only') + 1] : null;
const force = args.includes('--force');
const series = readJSON(path.join(ROOT, 'series', `${seriesId}.json`));
const styleGuide = readText(path.join(ROOT, 'prompts', 'style-guide.md'));
const tpl = readText(path.join(ROOT, 'prompts', 'avatar.md'));
const dir = ensureDir(path.join(ROOT, '.cache', 'avatars'));

const members = Object.values(series.cast).filter((c) => !only || c.id === only);
await pool(2, members, async (c) => {
  const out = avatarPath(c.id);
  if (exists(out) && !force) return log('avatar', `${c.id}: exists (use --force)`);
  const facing = c.side === 'left' ? '右' : '左';
  const prompt = tpl
    .replace('{{CHARACTER}}', `名前：${c.name}（${c.role}）\n${c.look}`)
    .replace('{{SIDE}}', c.side === 'left' ? '左端' : '右端')
    .replace('{{FACING}}', `${facing}向き`)
    .replace('{{STYLE_GUIDE}}', styleGuide);
  const r = await askSVG({ prompt, tag: `avatar-${c.id}`, dir, model: 'best', validate: validateRigSVG, repairs: 1 });
  writeText(out, r.svg + '\n');
  log('avatar', `${c.id}: saved ${out} (${r.svg.length} bytes, $${(r.costUsd ?? 0).toFixed(2)}, ${r.seconds}s)`);
});
