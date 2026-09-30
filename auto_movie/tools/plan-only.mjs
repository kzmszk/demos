#!/usr/bin/env node
// Run only the planning stage to see which style the model picks:
//   node tools/plan-only.mjs "テーマ" [--seconds 180] [--sources file.md …]
import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';
import { ROOT } from '../lib/util.mjs';
import { loadSeries } from '../lib/styles.mjs';
import { collectSources } from '../lib/stages/sources.mjs';
import { makePlan } from '../lib/stages/plan.mjs';
const args = process.argv.slice(2);
const theme = args[0];
const seconds = args.includes('--seconds') ? +args[args.indexOf('--seconds') + 1] : 180;
const srcs = args.includes('--sources') ? args.slice(args.indexOf('--sources') + 1).filter((a) => !a.startsWith('--')) : [];
const runDir = fs.mkdtempSync(path.join(os.tmpdir(), 'automovie-plan-'));
const src = await collectSources(srcs, { runDir });
const plan = await makePlan({ theme, lengthSec: seconds, styleId: 'auto', series: loadSeries('lifehack'), sourcesText: src.text, runDir });
console.log(JSON.stringify({ theme, style: plan.style, reason: plan.styleReason, title: plan.title, scenes: plan.scenes.map((s) => `${s.id}:${s.visual}:${s.seconds}s`).join(' ') }, null, 2));
