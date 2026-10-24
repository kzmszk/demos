#!/usr/bin/env node
// Generate the image boards with Codex (its image generation tool), N at a time.
//   node tokyo2090/tools/boards.mjs            # all boards that have no png yet
//   node tokyo2090/tools/boards.mjs 03 07      # only these ids (prefix match), overwrite
//   PAR=3 node tokyo2090/tools/boards.mjs      # parallelism (default 4)
import { spawn } from 'node:child_process';
import { readFileSync, existsSync, mkdirSync, writeFileSync, renameSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const boardsDir = join(root, 'boards');
const spec = JSON.parse(readFileSync(join(boardsDir, 'boards.json'), 'utf8'));
const only = process.argv.slice(2);
const PAR = Number(process.env.PAR || 4);
const DRY = !!process.env.DRY;

const jobs = spec.boards.filter((b) => {
  if (only.length) return only.some((o) => b.id.startsWith(o));
  return !existsSync(join(boardsDir, b.id + '.png'));
});
if (!jobs.length) { console.log('nothing to do'); process.exit(0); }

function prompt(b) {
  const out = join(boardsDir, b.id + '.png');
  const size = b.aspect === 'landscape' ? '1536x1024 (landscape)' : b.aspect === 'portrait' ? '1024x1536 (portrait)' : '1024x1024';
  return `You are generating ONE image board for a game. Use your image generation tool exactly once, with size ${size} if the tool supports it (otherwise the closest landscape size). Do not edit, upscale or resize the result. Copy the generated PNG to ${out} (overwrite). Do not write any other file. Finally print exactly: DONE ${out}

IMAGE PROMPT (pass it to the image tool as written, you may prepend nothing):
${spec.style}

SHOT: ${b.prompt}`;
}

function run(b) {
  return new Promise((done) => {
    const out = join(boardsDir, b.id + '.png');
    const log = join(boardsDir, '.log', b.id + '.txt');
    mkdirSync(dirname(log), { recursive: true });
    writeFileSync(join(boardsDir, '.log', b.id + '.prompt.txt'), prompt(b));
    if (DRY) { console.log('dry', b.id); return done(); }
    const t0 = Date.now();
    const p = spawn('codex', ['exec', '-s', 'workspace-write', '--skip-git-repo-check', '-c', 'model_reasoning_effort=low', '-'],
      { cwd: boardsDir, stdio: ['pipe', 'pipe', 'pipe'] });
    let buf = '';
    p.stdout.on('data', (d) => { buf += d; });
    p.stderr.on('data', (d) => { buf += d; });
    p.stdin.end(prompt(b));
    const timer = setTimeout(() => { buf += '\nTIMEOUT\n'; p.kill('SIGKILL'); }, 15 * 60 * 1000);
    p.on('close', (code) => {
      clearTimeout(timer);
      writeFileSync(log, buf);
      const ok = existsSync(out) && buf.includes('DONE ');
      console.log(`${ok ? 'ok  ' : 'FAIL'} ${b.id}  ${((Date.now() - t0) / 1000).toFixed(0)}s  exit ${code}`);
      done();
    });
  });
}

let i = 0;
async function worker() { while (i < jobs.length) await run(jobs[i++]); }
await Promise.all(Array.from({ length: Math.min(PAR, jobs.length) }, worker));
