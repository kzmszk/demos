#!/usr/bin/env node
/* DEMOS — site build.
 *
 * Every top-level folder with a demo.json becomes one work in the gallery:
 *   1. its "prebuild" command runs inside the folder (e.g. kinetic builds its dist/),
 *   2. its "serve" folder is copied to site/<folder>/ (demo.json, prompts/, README.md and dotfiles stay out),
 *      and HTML written for the Artifact skeleton (no doctype) gets a proper document wrapper,
 *   3. its cover frames from gallery/covers/<folder>/ are copied to site/_g/covers/<folder>/.
 * Then site/index.html (the gallery) and site/404.html are written.
 *
 *   node gallery/build.mjs                 full build
 *   node gallery/build.mjs --skip-prebuild don't run the demos' own builds
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const GAL = path.join(ROOT, 'gallery');
const OUT = path.join(ROOT, 'site');
const flags = new Set(process.argv.slice(2));

const NOT_DEMOS = new Set(['gallery', 'site', 'node_modules']);
const NEVER_COPY = new Set(['demo.json', 'prompts', 'README.md', 'node_modules', 'package.json', 'package-lock.json']);

const site = JSON.parse(fs.readFileSync(path.join(GAL, 'site.json'), 'utf8'));
const esc = (s) =>
  String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const pair = (v) => (typeof v === 'string' ? { en: v, ja: v } : { en: (v && v.en) || '', ja: (v && v.ja) || '' });
const dot = (d) => String(d || '').replace(/-/g, '.');

/* ---------- read the demos ---------- */
function readDemos() {
  return fs
    .readdirSync(ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory() && !d.name.startsWith('.') && !NOT_DEMOS.has(d.name))
    .map((d) => d.name)
    .filter((slug) => fs.existsSync(path.join(ROOT, slug, 'demo.json')))
    .map((slug) => {
      const m = JSON.parse(fs.readFileSync(path.join(ROOT, slug, 'demo.json'), 'utf8'));
      return {
        slug,
        no: m.no ? String(m.no) : '',
        title: pair(m.title || slug),
        subtitle: pair(m.subtitle || ''),
        summary: pair(m.summary || ''),
        date: m.date || '',
        tags: Array.isArray(m.tags) ? m.tags : [],
        lang: m.lang || site.lang || 'ja',
        prebuild: m.prebuild || '',
        serve: m.serve || '.',
        entry: m.entry || 'index.html',
        links: Array.isArray(m.links) ? m.links : [],
        shots: Array.isArray(m.shots) ? m.shots : [],
      };
    })
    .sort((a, b) => (b.date || '').localeCompare(a.date || '') || (b.no || '').localeCompare(a.no || '') || a.slug.localeCompare(b.slug));
}

/* ---------- copy ---------- */
const SKELETON = (lang) =>
  `<!DOCTYPE html>\n<html lang="${lang}">\n<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n`;

function copyTree(src, dst, lang) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    if (e.name.startsWith('.') || NEVER_COPY.has(e.name)) continue;
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) copyTree(s, d, lang);
    else if (e.name.endsWith('.html')) {
      const html = fs.readFileSync(s, 'utf8');
      /* pages written for the Artifact skeleton start without a doctype; give them one */
      fs.writeFileSync(d, /^\s*<!doctype/i.test(html) ? html : SKELETON(lang) + html);
    } else fs.copyFileSync(s, d);
  }
}

const hash = (buf) => crypto.createHash('sha256').update(buf).digest('hex').slice(0, 10);

/* ---------- build ---------- */
const demos = readDemos();
if (!flags.has('--skip-prebuild')) {
  for (const d of demos) {
    if (!d.prebuild) continue;
    console.log(`· ${d.slug}: ${d.prebuild}`);
    execSync(d.prebuild, { cwd: path.join(ROOT, d.slug), stdio: ['ignore', 'ignore', 'inherit'] });
  }
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(path.join(OUT, '_g'), { recursive: true });

for (const d of demos) {
  const src = path.join(ROOT, d.slug, d.serve);
  if (!fs.existsSync(src)) throw new Error(`${d.slug}: serve folder "${d.serve}" not found`);
  copyTree(src, path.join(OUT, d.slug), d.lang);
  if (!fs.existsSync(path.join(OUT, d.slug, d.entry))) console.warn(`! ${d.slug}: entry "${d.entry}" is missing`);
  const coverDir = path.join(GAL, 'covers', d.slug);
  d.frames = fs.existsSync(coverDir)
    ? fs
        .readdirSync(coverDir)
        .filter((f) => /\.(webp|png|jpe?g)$/i.test(f))
        .sort()
        .map((f) => {
          const buf = fs.readFileSync(path.join(coverDir, f));
          fs.mkdirSync(path.join(OUT, '_g/covers', d.slug), { recursive: true });
          fs.writeFileSync(path.join(OUT, '_g/covers', d.slug, f), buf);
          return `_g/covers/${d.slug}/${f}?v=${hash(buf)}`;
        })
    : [];
  console.log(`✓ ${d.slug.padEnd(12)} ${String(d.frames.length).padStart(2)} frames → site/${d.slug}/`);
}

const asset = (name) => {
  const buf = fs.readFileSync(path.join(GAL, 'src', name));
  fs.writeFileSync(path.join(OUT, '_g', name), buf);
  return `_g/${name}?v=${hash(buf)}`;
};
const css = asset('gallery.css');
const js = asset('gallery.js');

const latest = demos.map((d) => d.date).filter(Boolean).sort().pop() || '';
fs.writeFileSync(path.join(OUT, 'index.html'), page(demos));
fs.writeFileSync(path.join(OUT, '404.html'), notFound());
console.log(`\n${demos.length} works → site/index.html`);

/* ---------- templates ---------- */
function head(title, description, prefix) {
  const p = prefix || '';
  return `<!DOCTYPE html>
<html lang="${esc(site.lang || 'ja')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<meta name="theme-color" content="#e8e8e5" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f0f0e" media="(prefers-color-scheme: dark)">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(description)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230e0e0d'/%3E%3Crect x='19' y='19' width='8' height='8' fill='%23e1261c'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap">
<link rel="stylesheet" href="${p}${css}">
</head>`;
}

function card(d, i) {
  const href = `${d.slug}/${d.entry === 'index.html' ? '' : d.entry}`;
  const name = d.title.en || d.title.ja;
  const cover = d.frames.length
    ? `<a class="cover" href="${esc(href)}" data-frames="${esc(JSON.stringify(d.frames))}" aria-label="${esc(name)} を開く">
        <span class="frames"><img src="${esc(d.frames[0])}" alt="" width="960" height="600"${i < 2 ? ' fetchpriority="high"' : ' loading="lazy"'} decoding="async"></span>
        ${d.frames.length > 1 ? `<span class="scrub" aria-hidden="true">${d.frames.map((_, k) => `<i${k ? '' : ' class="is-on"'}></i>`).join('')}</span>` : ''}
      </a>`
    : `<a class="cover is-type" href="${esc(href)}" aria-label="${esc(name)} を開く"><span>${esc(name)}</span></a>`;
  const links = d.links.length
    ? `<ul class="links">${d.links.map((l) => `<li><a href="${esc(`${d.slug}/${l.href}`)}">${esc(l.label)}</a></li>`).join('')}</ul>`
    : `<ul class="links"><li><a href="${esc(href)}">開く <span aria-hidden="true">↗</span></a></li></ul>`;
  return `
    <article class="work" id="${esc(d.slug)}">
      <p class="work-head"><span class="no">${d.no ? `No. ${esc(d.no)}` : esc(d.slug)}</span><time datetime="${esc(d.date)}">${esc(dot(d.date))}</time></p>
      ${cover}
      <h2 class="work-title"><a href="${esc(href)}">${esc(name)}</a></h2>
      <p class="work-sub"><span lang="ja">${esc(d.subtitle.ja)}</span><span lang="en">${esc(d.subtitle.en)}</span></p>
      <p class="work-sum" lang="ja">${esc(d.summary.ja)}</p>
      <p class="work-sum-en" lang="en">${esc(d.summary.en)}</p>
      <div class="work-foot">
        <ul class="tags">${d.tags.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>
        ${links}
      </div>
    </article>`;
}

function page(list) {
  const n = String(list.length).padStart(2, '0');
  return `${head(site.name, site.description)}
<body>
<header class="mast">
  <p class="topline"><span>Index of web experiments</span><span>${n} works · updated ${esc(dot(latest))}</span></p>
  <h1 class="wordmark"><span>${esc(site.name)}</span></h1>
  <div class="rule" aria-hidden="true"></div>
  <div class="intro">
    <p class="tagline"><span lang="ja">${esc(site.tagline.ja)}</span><span lang="en">${esc(site.tagline.en)}</span></p>
    <dl class="stats">
      <div><dt>Works</dt><dd>${n}</dd></div>
      <div><dt>Updated</dt><dd>${esc(dot(latest))}</dd></div>
    </dl>
  </div>
</header>
<main class="works">${list.map(card).join('')}
</main>
<footer class="colophon">
  <span>${esc(site.name)} — ${n} works</span>
  <span>Each work is a single page · served by Cloudflare Workers</span>
</footer>
<script src="${js}" defer></script>
</body>
</html>
`;
}

function notFound() {
  return `${head(`${site.name} — 404`, 'Page not found.', '/')}
<body class="is-404">
<header class="mast">
  <p class="topline"><span>Index of web experiments</span><span>404</span></p>
  <h1 class="wordmark"><span>404</span></h1>
  <div class="rule" aria-hidden="true"></div>
  <div class="intro">
    <p class="tagline"><span lang="ja">このページは見つかりません。</span><span lang="en">Nothing lives at this address.</span></p>
    <p class="back"><a href="/">← ${esc(site.name)}</a></p>
  </div>
</header>
<script src="/${js}" defer></script>
</body>
</html>
`;
}
