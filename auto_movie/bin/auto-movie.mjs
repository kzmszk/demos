#!/usr/bin/env node
// auto-movie CLI
//   auto-movie make --theme "…" [--length 3] [--sources a.md b.md] [--style auto|podcast-duo|monologue|entertainment]
//                   [--tts voicevox|gemini|mock] [--quality draft|looks|delivery] [--run <id>] [--out output/x.mp4] [--force plan,script,…]
//   auto-movie build <script.json> --run <id>       (script → video, skipping the LLM stages)
//   auto-movie voicevox [start|status|stop]         manage the local VOICEVOX engine (Docker)
//   auto-movie qa <runDir> [--target 180]           re-run the automated QA on a rendered run
//   auto-movie app [--port 8420]                    local web UI
import path from 'node:path';
import fs from 'node:fs';
import { ROOT, run, log, readJSON, ensureDir, exists } from '../lib/util.mjs';

const [cmd, ...rest] = process.argv.slice(2);
const flags = {}, pos = [];
for (let i = 0; i < rest.length; i++) {
  if (rest[i].startsWith('--')) {
    const k = rest[i].slice(2);
    const vals = [];
    while (i + 1 < rest.length && !rest[i + 1].startsWith('--')) vals.push(rest[++i]);
    flags[k] = vals.length === 0 ? true : vals.length === 1 ? vals[0] : vals;
  } else pos.push(rest[i]);
}
const arr = (v) => (v == null || v === true ? [] : Array.isArray(v) ? v : [v]);
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9぀-ヿ一-鿿]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'run';

async function main() {
  if (cmd === 'make') {
    const { make } = await import('../lib/make.mjs');
    if (!flags.theme) throw new Error('--theme is required');
    const lengthSec = flags.seconds ? +flags.seconds : Math.round((flags.length ? +flags.length : 3) * 60);
    const runId = flags.run || `${slug(String(flags.theme))}-${new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '')}`;
    const s = await make({
      theme: String(flags.theme), lengthSec, sources: arr(flags.sources), style: flags.style || 'auto', series: flags.series || 'lifehack',
      provider: flags.tts || 'voicevox', quality: flags.quality || 'looks', runDir: path.join(ROOT, 'runs', runId), force: String(flags.force || '').split(',').filter(Boolean),
      out: flags.out, episodeNo: flags.no ? +flags.no : 1,
    });
    console.log(JSON.stringify(s, null, 2));
  } else if (cmd === 'build') {
    const { buildFromScript, stageCheck, stageRender } = await import('../lib/pipeline.mjs');
    const { runQA } = await import('../lib/qa.mjs');
    const { loadSeries } = await import('../lib/styles.mjs');
    const script = pos[0];
    if (!script) throw new Error('usage: build <script.json> --run <id>');
    const runDir = path.join(ROOT, 'runs', String(flags.run || slug(path.basename(path.dirname(path.resolve(script))))));
    const lengthSec = flags.seconds ? +flags.seconds : Math.round((flags.length ? +flags.length : 3) * 60);
    const r = await buildFromScript({ episode: readJSON(script), series: loadSeries(flags.series || 'lifehack'), runDir, targetSec: lengthSec, provider: flags.tts || 'voicevox' });
    log('build', JSON.stringify(r.stats));
    if (flags.render) {
      const c = await stageCheck({ runDir });
      const video = await stageRender({ runDir, quality: flags.quality || 'looks' });
      const qa = await runQA({ runDir, video, targetSec: lengthSec, checkLog: c.out });
      if (flags.out) { ensureDir(path.dirname(path.resolve(flags.out))); fs.copyFileSync(video, path.resolve(flags.out)); }
      console.log(`QA: ${qa.status}`);
    }
  } else if (cmd === 'voicevox') {
    const vv = await import('../lib/tts/voicevox.mjs');
    const sub = pos[0] || 'status';
    if (sub === 'start') { await vv.ensureReady(); console.log('VOICEVOX engine is up'); }
    else if (sub === 'stop') { await run('docker', ['stop', 'automovie-voicevox']); console.log('stopped'); }
    else console.log((await vv.isUp()) ? 'VOICEVOX engine is up' : 'VOICEVOX engine is not running');
  } else if (cmd === 'qa') {
    const { runQA } = await import('../lib/qa.mjs');
    const runDir = path.resolve(pos[0] || '');
    const inp = exists(path.join(runDir, 'input.json')) ? readJSON(path.join(runDir, 'input.json')) : {};
    const target = flags.target ? +flags.target : inp.lengthSec || 180;
    const rep = await runQA({ runDir, video: path.join(runDir, 'video.mp4'), targetSec: target, checkLog: exists(path.join(runDir, 'check.log')) ? fs.readFileSync(path.join(runDir, 'check.log'), 'utf8') : '' });
    console.log(`QA: ${rep.status}  → ${path.join(runDir, 'qa', 'report.md')}`);
  } else if (cmd === 'app') {
    const { startApp } = await import('../lib/server.mjs');
    await startApp({ port: flags.port ? +flags.port : 8420 });
  } else {
    console.log(fs.readFileSync(new URL(import.meta.url), 'utf8').split('\n').slice(1, 12).filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
  }
}
main().catch((e) => { console.error('\nerror:', e.message); process.exit(1); });
