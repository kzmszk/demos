#!/usr/bin/env node
// The film for the web: the same 1080×1080 at 60 fps, re-encoded from the master in two passes so it fits a size
// budget (by default 20 MiB, the most an artifact asset may be). The first pass only measures where the film is
// busy; the second spends the bits there, so quiet drawing gets little and page turns get more.
//
//   node render/web.mjs                        video/claude-sketchbook.mp4 → video/claude-sketchbook-web.mp4
//   node render/web.mjs --mib 20 --audio 128 --in video/x.mp4 --out video/y.mp4
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const IN = path.resolve(root, arg('in', 'video/claude-sketchbook.mp4'));
const OUT = path.resolve(root, arg('out', 'video/claude-sketchbook-web.mp4'));
const BUDGET = Math.floor(+arg('mib', 20) * 1024 * 1024); // bytes
const AUDIO = +arg('audio', 128); // kbps
const FFMPEG = process.env.FFMPEG || 'ffmpeg';

const run = (args) => {
  const r = spawnSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('ffmpeg failed: ' + args.join(' '));
};

if (!fs.existsSync(IN)) throw new Error(`${IN} not found: render the film first (node render/render.mjs)`);
const probe = spawnSync(FFMPEG, ['-hide_banner', '-i', IN], { encoding: 'utf8' }).stderr;
const m = /Duration: (\d+):(\d+):([\d.]+)/.exec(probe);
if (!m) throw new Error('could not read the duration of ' + IN);
const dur = +m[1] * 3600 + +m[2] * 60 + +m[3];

// what is left for the picture once the sound is paid for, less a margin for the container and the rate control
let kbps = Math.floor(((BUDGET * 8) / dur - AUDIO * 1000) * 0.94 / 1000);
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'web-'));
const log = path.join(tmp, 'x264');
const video = (pass) => ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'film', '-g', '120', '-b:v', kbps + 'k', '-pass', String(pass), '-passlogfile', log];
try {
  console.log(`${path.basename(IN)}: ${dur.toFixed(2)} s → ${kbps} kbps video + ${AUDIO} kbps audio`);
  run(['-i', IN, ...video(1), '-an', '-f', 'null', os.devNull]);
  for (let attempt = 0; ; attempt++) {
    run(['-i', IN, ...video(2), '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
      '-c:a', 'aac', '-b:a', AUDIO + 'k', '-movflags', '+faststart', OUT]);
    const size = fs.statSync(OUT).size;
    console.log(`wrote ${OUT} ${(size / 1048576).toFixed(2)} MiB`);
    if (size <= BUDGET) break;
    if (attempt === 2) throw new Error('still over budget after three tries');
    // the first pass's statistics hold for any target, so only the second pass runs again
    kbps = Math.floor(kbps * (BUDGET / size) * 0.98);
    console.log(`over budget; retrying at ${kbps} kbps`);
  }
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
