#!/usr/bin/env node
// Draw the illustration scenes of a script:  node tools/illustrate.mjs <script.json> <runDir> [--force] [--concurrency 3]
import { readJSON } from '../lib/util.mjs';
import { illustrate } from '../lib/stages/illustrate.mjs';
const [script, runDir, ...rest] = process.argv.slice(2);
const c = rest.includes('--concurrency') ? +rest[rest.indexOf('--concurrency') + 1] : 3;
await illustrate({ episode: readJSON(script), runDir, concurrency: c, force: rest.includes('--force') });
