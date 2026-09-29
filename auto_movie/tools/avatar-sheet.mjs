#!/usr/bin/env node
// Render every rig state of a cast member to a PNG contact sheet: node tools/avatar-sheet.mjs mio [out.png]
import path from 'node:path';
import { ROOT, ensureDir } from '../lib/util.mjs';
import { loadAvatar, stateSheetHTML, validateRigSVG } from '../lib/visual/avatar-rig.mjs';
import { screenshot } from '../lib/shot.mjs';

const id = process.argv[2] || 'mio';
const out = process.argv[3] || path.join(ROOT, '.cache', 'avatars', `${id}-sheet.png`);
ensureDir(path.dirname(out));
const svg = loadAvatar(id);
const problems = validateRigSVG(svg);
if (problems.length) console.log('validation problems:', problems);
await screenshot(stateSheetHTML(svg, { title: id }), out, { width: 1240, height: 800 });
console.log('wrote', out);
