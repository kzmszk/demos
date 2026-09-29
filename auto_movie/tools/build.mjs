#!/usr/bin/env node
// Build (and optionally render) a video from an existing script.json:
//   node tools/build.mjs <script.json> <runDir> [--target 180] [--provider voicevox|gemini|mock] [--render] [--quality draft|looks|delivery]
import path from 'node:path';
import fs from 'node:fs';
import { loadStyles } from '../lib/styles.mjs';
import { ROOT, readJSON, log } from '../lib/util.mjs';
import { buildFromScript, stageCheck, stageRender } from '../lib/pipeline.mjs';
const [script, runDir, ...rest] = process.argv.slice(2);
const opt = (k, d) => (rest.includes('--' + k) ? rest[rest.indexOf('--' + k) + 1] : d);
const series = readJSON(path.join(ROOT, 'series', `${opt('series', 'lifehack')}.json`));
// example scripts may ship their illustrations next to them
const exDir = path.join(path.dirname(path.resolve(script)), 'illustrations');
const dst = path.join(path.resolve(runDir), 'illustrations');
if (fs.existsSync(exDir) && !fs.existsSync(dst)) fs.cpSync(exDir, dst, { recursive: true });
const style = loadStyles()[opt('style', 'podcast-duo')];
const r = await buildFromScript({ episode: readJSON(script), series, runDir: path.resolve(runDir), targetSec: +opt('target', 180), provider: opt('provider', 'voicevox'), style });
log('build', JSON.stringify(r.stats), 'project:', r.project.indexPath);
if (rest.includes('--check') || rest.includes('--render')) {
  const c = await stageCheck({ runDir: path.resolve(runDir) });
  console.log(c.out.split('\n').slice(-40).join('\n'));
}
if (rest.includes('--render')) {
  const out = await stageRender({ runDir: path.resolve(runDir), quality: opt('quality', 'draft') });
  log('build', 'rendered', out);
}
