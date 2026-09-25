#!/usr/bin/env node
/* Kinetic Manifesto — build: content/*.json → dist/<slug>.html + dist/index.html
 *
 *   node build.mjs                       build every content/*.json
 *   node build.mjs content/a.json …      build some files
 *   --check    validate only, write nothing
 *   --lock     hide the Edit button in the output (options.editable = false)
 *   --force    build even when a file has errors
 *   --en       print messages in English
 *   --out=DIR  output directory (default: dist)
 *
 * The engine's assets are taken from index.html (every tag marked data-k-src, in order),
 * and the page is rendered by the same K.template the in-browser “Save HTML” uses. */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const flag = (f) => args.includes(f);
const outArg = args.find((a) => a.startsWith('--out='));
const outDir = path.resolve(here, outArg ? outArg.slice(6) : 'dist');
const lang = flag('--en') ? 'en' : 'ja';

let files = args.filter((a) => !a.startsWith('--'));
if (!files.length) {
  files = fs
    .readdirSync(path.join(here, 'content'))
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => path.join(here, 'content', f));
}

/* engine assets, in index.html order */
const index = fs.readFileSync(path.join(here, 'index.html'), 'utf8');
const css = [], js = [];
for (const [tag] of index.matchAll(/<(?:link|script)\b[^>]*\bdata-k-src\b[^>]*>/g)) {
  const src = /\b(?:href|src)="([^"]+)"/.exec(tag)[1];
  const text = fs.readFileSync(path.join(here, src), 'utf8').trim();
  if (tag.startsWith('<link')) css.push(text);
  else js.push(`/* ---- ${src} ---- */\n${text}`);
}
const cssText = css.join('\n');
const jsText = js.join('\n');

/* the DOM-free half of the engine: normalise, validate, template */
const sandbox = { console };
vm.createContext(sandbox);
for (const f of ['util.js', 'text.js', 'content.js', 'template.js']) {
  vm.runInContext(fs.readFileSync(path.join(here, 'src/js', f), 'utf8'), sandbox, { filename: f });
}
const K = sandbox.K;

const rel = (p) => path.relative(process.cwd(), p) || p;
let failed = 0, written = 0;
for (const file of files) {
  const abs = path.resolve(file);
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch (e) {
    console.error(`✗ ${rel(abs)}: ${e.message}`);
    failed++;
    continue;
  }
  const issues = K.validate(raw);
  const errors = issues.filter((i) => i.level === 'error');
  const mark = errors.length ? '✗' : issues.length ? '△' : '✓';
  console.log(`${mark} ${rel(abs)}`);
  for (const i of issues) console.log(`    ${i.level === 'error' ? 'error' : 'warn '}  ${i.path.padEnd(18)} ${i.msg[lang]}`);
  if (errors.length && !flag('--force')) {
    failed++;
    continue;
  }
  if (flag('--check')) continue;
  const c = K.normalize(raw);
  const html = K.template.page({ content: raw, css: cssText, js: jsText, lock: flag('--lock') });
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, `${c.meta.slug}.html`);
  fs.writeFileSync(out, html);
  written++;
  console.log(`    → ${rel(out)}  (${(Buffer.byteLength(html) / 1024).toFixed(1)} KB)`);
}

/* contact sheet of everything in the output folder */
if (!flag('--check') && fs.existsSync(outDir)) {
  const pages = fs
    .readdirSync(outDir)
    .filter((f) => f.endsWith('.html') && f !== 'index.html')
    .sort()
    .map((f) => {
      const src = fs.readFileSync(path.join(outDir, f), 'utf8');
      const m = /<script type="application\/json" id="k-content">\n([\s\S]*?)\n<\/script>/.exec(src);
      try {
        return { file: f, c: K.normalize(JSON.parse(m[1])) };
      } catch (e) {
        return null;
      }
    })
    .filter(Boolean);
  fs.writeFileSync(path.join(outDir, 'index.html'), gallery(pages));
}

console.log(failed ? `\n${failed} file(s) failed.` : `\n${written} page(s) written to ${rel(outDir)}/`);
process.exit(failed ? 1 : 0);

function gallery(pages) {
  const esc = K.escapeHTML;
  const lat = K.FONTS.lat.family.replace(/"/g, "'");
  const ja = K.FONTS.ja.family.replace(/"/g, "'");
  const mono = K.FONTS.mono.replace(/"/g, "'");
  const tiles = pages
    .map(({ file, c }) => {
      const P = c.palette;
      const word = c.options.uppercase ? c.intro.word.toUpperCase() : c.intro.word;
      const face = K.text.hasJa(word) ? 'ja' : 'lat';
      return `    <li>
      <a href="${esc(file)}" style="--bg:${P.bg};--fg:${P.fg};--ac:${P.accent}">
        <span class="w ${face}">${esc(word)}</span>
        <span class="meta"><i></i>${esc(c.lang.toUpperCase())} · ${K.pad(c.scenes.length + 1)} SC.</span>
        <span class="t">${esc(c.meta.title)}</span>
      </a>
    </li>`;
    })
    .join('\n');
  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kinetic Manifesto — ${pages.length} pages</title>
<meta name="description" content="Contact sheet of the pages built from the Kinetic Manifesto template.">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #0b0b0b; color: #ecece6; font: 13px/1.5 system-ui, sans-serif; }
  header { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding: 28px clamp(16px, 4vw, 48px) 18px; font: 11px/1.4 ${mono}; letter-spacing: .1em; text-transform: uppercase; }
  header b { font-size: 12px; letter-spacing: .14em; }
  ul { list-style: none; margin: 0; padding: 0 clamp(16px, 4vw, 48px) 48px; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 14px; }
  a { position: relative; display: flex; flex-direction: column; justify-content: flex-end; aspect-ratio: 4 / 5; padding: 16px; overflow: hidden; background: var(--bg); color: var(--fg); text-decoration: none; border-radius: 2px; transition: transform .35s cubic-bezier(.2,.8,.2,1); }
  a:hover { transform: translateY(-3px); }
  a:focus-visible { outline: 2px solid var(--ac); outline-offset: 3px; }
  .w { position: absolute; left: 12px; top: 6px; font-size: clamp(90px, 12vw, 150px); line-height: .9; white-space: nowrap; }
  .lat { font-family: ${lat}; font-weight: 900; font-stretch: condensed; }
  .ja { font-family: ${ja}; font-weight: 800; }
  .meta { display: flex; align-items: center; gap: 8px; font: 10px/1 ${mono}; letter-spacing: .12em; opacity: .8; }
  .meta i { width: 9px; height: 9px; background: var(--ac); }
  .t { margin-top: 8px; font-size: 14px; font-weight: 600; }
</style>
</head>
<body>
<header><b>Kinetic Manifesto</b><span>${pages.length} pages · built ${new Date().toISOString().slice(0, 10)}</span></header>
<ul>
${tiles}
</ul>
</body>
</html>
`;
}
