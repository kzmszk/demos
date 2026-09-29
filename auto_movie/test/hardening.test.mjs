// Videos can be made on request from a stranger's text. These tests pin down what stops that text from doing harm:
// the SVG allow-list, the escaping in the composition, the request cleaning, and the shape of the job result.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { ROOT, readJSON, jsonForScript } from '../lib/util.mjs';
import { sanitizeSVG } from '../lib/visual/svgsafe.mjs';
import { validateScript } from '../lib/schema.mjs';
import { cleanRequest, InputError, chaptersFrom, resultOf } from '../lib/job.mjs';
import { buildFromScript } from '../lib/pipeline.mjs';
import { loadStyles } from '../lib/styles.mjs';

const episode = readJSON(path.join(ROOT, 'examples/lifehack-001/script.json'));
const series = readJSON(path.join(ROOT, 'series/lifehack.json'));

/* ---------------- SVG ---------------- */
const wrap = (inner, root = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360">') => `${root}${inner}</svg>`;

test('every real drawing passes through the sanitizer unchanged in substance', () => {
  const dirs = [path.join(ROOT, 'examples/lifehack-001/illustrations')];
  const files = dirs.flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith('.svg')).map((f) => path.join(d, f)));
  assert.ok(files.length >= 3);
  for (const f of files) {
    const raw = fs.readFileSync(f, 'utf8');
    const { svg } = sanitizeSVG(raw);
    const body = raw.replace(/<!--[\s\S]*?-->/g, '');
    const count = (t, re) => (t.match(re) || []).length;
    assert.equal(count(svg, /<[A-Za-z]/g), count(body, /<[A-Za-z]/g), `${path.basename(f)}: elements kept`);
    assert.equal(count(svg, /\s[A-Za-z_:][\w:.-]*=/g), count(body, /\s[A-Za-z_:][\w:.-]*=/g), `${path.basename(f)}: attributes kept`);
  }
});

test('the sanitizer rebuilds the drawing: scripts, handlers, external references and odd markup are gone', () => {
  const attacks = [
    wrap('<script>alert(1)</script><path d="M0 0L10 10"/>'),
    wrap('<path d="M0 0" onload="alert(1)" onclick="x()"/>'),
    wrap('<image href="http://evil.example/x.png"/><path d="M0 0"/>'),
    wrap('<foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><iframe src="javascript:alert(1)"></iframe></body></foreignObject><path d="M0 0"/>'),
    wrap('<a href="javascript:alert(1)"><path d="M0 0"/></a>'),
    wrap('<path d="M0 0" fill="url(http://evil.example/p)" stroke="javascript:alert(1)" style="background:url(http://evil.example)"/>'),
    wrap('<use href="http://evil.example/x.svg#a"/><use xlink:href="data:image/svg+xml;base64,AAAA"/>'),
    wrap('<defs><filter id="f"><feImage href="http://evil.example/x.png"/></filter></defs><path d="M0 0" filter="url(http://evil.example/f)"/>'),
    wrap('<set attributeName="href" to="javascript:alert(1)"/><animate attributeName="href" values="javascript:alert(1)"/><path d="M0 0"/>'),
    wrap('<style>path{background:url(http://evil.example)}</style><path d="M0 0" class="x"/>'),
    wrap('<text>hello</text><path d="M0 0"/>'),
  ];
  for (const a of attacks) {
    const { svg } = sanitizeSVG(a);
    const inner = svg.replace(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/, '<svg');   // the one namespace URL we write ourselves
    assert.doesNotMatch(inner, /<script|<image|<foreignObject|<iframe|<a[\s>]|<style|<set|<animate|<feImage|<text|javascript:|data:|http:|https:|onload|onclick|url\((?!#)/i, svg);
    assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" viewBox="0 0 640 360">/);
  }
  // an unknown element takes everything inside it along
  assert.doesNotMatch(sanitizeSVG(wrap('<switch><path id="kept-not" d="M0 0"/></switch><path id="kept" d="M1 1"/>')).svg, /kept-not/);
  assert.match(sanitizeSVG(wrap('<switch><path id="a" d="M0 0"/></switch><path id="kept" d="M1 1"/>')).svg, /id="kept"/);
});

test('malformed or unsafe documents are rejected, not repaired', () => {
  const bad = [
    'no svg here',
    '<svg viewBox="0 0 1 1"><path d="M0 0"></svg>',                            // unbalanced
    '<svg viewBox="0 0 1 1"><![CDATA[x]]></svg>',
    '<?xml version="1.0"?><svg viewBox="0 0 1 1"><!DOCTYPE x></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0" fill=red/></svg>',                 // unquoted attribute
    '<svg viewBox="0 0 1 1"></svg><svg viewBox="0 0 1 1"></svg>',             // two roots
    '<svg><path d="M0 0"/></svg>',                                            // no viewBox
    '<svg viewBox="0 0 1 1"><path d="M0 0" < /></svg>',
  ];
  for (const b of bad) assert.throws(() => sanitizeSVG(b), /^Error: svg:/, b);
  assert.throws(() => sanitizeSVG('<svg viewBox="0 0 1 1">' + '<g>'.repeat(40) + '</g>'.repeat(40) + '</svg>'), /deeply/);
});

test('the design memo is kept as plain text', () => {
  const { memo, svg } = sanitizeSVG('<svg viewBox="0 0 640 360"><!-- 設計：<script>alert(1)</script> 顔／誇張 --><path d="M0 0"/></svg>');
  assert.doesNotMatch(memo, /[<>]/);
  assert.match(memo, /設計/);
  assert.doesNotMatch(svg, /<!--/);
});

/* ---------------- request ---------------- */
test('a request is cleaned before it reaches the pipeline', () => {
  assert.deepEqual(cleanRequest({ theme: '  三日坊主を　やめる工夫 ', minutes: 3 }), { theme: '三日坊主を やめる工夫', lengthSec: 180, notes: '' });
  assert.equal(cleanRequest({ theme: '朝の習慣', minutes: 2, notes: ' 数字は\r\n\r\n\r\n\r\n出典つき ' }).notes, '数字は\n\n出典つき');
  for (const bad of [null, [], {}, { theme: 'a', minutes: 3 }, { theme: 'x'.repeat(61), minutes: 3 }, { theme: '<script>', minutes: 3 }, { theme: 'ok theme', minutes: 5 },
    { theme: 'ok theme', minutes: '3' }, { theme: 'ok theme', minutes: 3, notes: 5 }, { theme: 'ok theme', minutes: 3, notes: 'x'.repeat(1501) }, { theme: 'ok theme', minutes: 3, notes: 'a\u0000b' }]) {
    assert.throws(() => cleanRequest(bad), InputError, JSON.stringify(bad));
  }
  // paths and URLs are only ever text: the theme never reaches the sources stage, the notes go through a file this code names
  assert.equal(cleanRequest({ theme: '/etc/passwd', minutes: 2 }).theme, '/etc/passwd');
});

test('a job result has the small, fixed shape the broker validates', () => {
  const plan = { style: 'podcast-duo' };
  const timeline = { scenes: [{ id: 's1', start: 4.4 }, { id: 's2', start: 21.9 }], outro: { start: 172.3 } };
  const ep = { title: 'たいとる', subtitle: 'さぶ', scenes: [{ id: 's1', headline: '一つめ' }, { id: 's2', headline: '二つめ' }] };
  const chapters = chaptersFrom(ep, timeline);
  assert.deepEqual(chapters, [{ t: 0, title: 'イントロ' }, { t: 4, title: '一つめ' }, { t: 21, title: '二つめ' }, { t: 172, title: 'エンディング' }]);
  const r = resultOf({ id: 'abcd1234-ef', episode: ep, plan, info: { seconds: 179.96, width: 1920, height: 1080 }, chapters, bytes: 38000000, qa: { status: 'PASS', checks: 18, passed: 18, measuredSec: 180, overlaps: 0, minGapSec: 0.34, lufs: -16, extra: 'x' } });
  assert.equal(r.video, 'movies/abcd1234-ef/video.mp4');
  assert.equal(r.poster, 'movies/abcd1234-ef/poster.webp');
  assert.equal(r.seconds, 180);
  assert.equal('extra' in r.qa, false);
  assert.ok(JSON.stringify(r).length < 4000);
});

/* ---------------- the composition ---------------- */
test('script ids that would reach HTML attributes and selectors must be plain', () => {
  const bad = structuredClone(episode);
  bad.scenes[0].id = 'a" onload="x';
  bad.scenes[1].lines[0].id = 's2 l1';
  const p = validateScript(bad, {});
  assert.ok(p.some((m) => /scene\[0\].*id/.test(m)), p.join('\n'));
  assert.ok(p.some((m) => /行の id/.test(m)), p.join('\n'));
});

test('JSON put into an inline script cannot close it', () => {
  const s = jsonForScript({ memo: '</script><script>alert(1)</script>', sep: 'a b' });
  assert.ok(!s.includes('<'), s);
  assert.ok(!s.includes(' '));
  assert.equal(JSON.parse(s).memo, '</script><script>alert(1)</script>');
});

test('hostile text in a script cannot escape the composition HTML', async () => {
  const evil = '</script><img src=x onerror=alert(1)>';
  const ep = structuredClone(episode);
  ep.title += evil; ep.subtitle += evil;
  for (const sc of ep.scenes) {
    sc.headline += evil;
    for (const ln of sc.lines) ln.text += evil;
    for (const c of sc.cues || []) if (typeof c.text === 'string') c.text += evil;
    const v = sc.visual;
    for (const pt of v.points || []) pt.x += evil;
    for (const b of v.bars || []) b.label += evil;
    for (const it of v.items || []) { if (it.label) it.label += evil; if (it.sub) it.sub += evil; if (it.text) it.text += evil; }
  }
  for (const ln of ep.outro.lines) ln.text += evil;
  const runDir = fs.mkdtempSync(path.join(os.tmpdir(), 'am-harden-'));
  fs.cpSync(path.join(ROOT, 'examples/lifehack-001/illustrations'), path.join(runDir, 'illustrations'), { recursive: true });
  const r = await buildFromScript({ episode: ep, series, runDir, targetSec: 180, provider: 'mock', style: loadStyles()['podcast-duo'] });
  const html = fs.readFileSync(r.project.indexPath, 'utf8');
  assert.ok(!html.includes('<img src=x'), 'no raw injected element');
  assert.ok(html.includes('&lt;img src=x'), 'the text is there, escaped');
  const opens = (html.match(/<script\b/g) || []).length, closes = (html.match(/<\/script>/g) || []).length;
  assert.equal(closes, opens, 'no injected </script>');
  fs.rmSync(runDir, { recursive: true, force: true });
});
