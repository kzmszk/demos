// The line chart's red note must not sit on a number: it goes up and to the right of its point, and somewhere else when that collides.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, readJSON } from '../lib/util.mjs';
import { renderStage, stampBox, stampTouches } from '../lib/visual/scenes.mjs';
import { STAGE } from '../lib/visual/theme.mjs';

const rects = (html, id) => {
  const co = html.match(new RegExp(`id="${id}-co0" style="left:([\\d.]+)px;top:([\\d.]+)px`));
  const text = html.match(new RegExp(`id="${id}-co0"[^>]*><u>([^<]*)</u>`))[1];
  const vals = [...html.matchAll(new RegExp(`id="${id}-val\\d+" style="[^"]*left:([\\d.]+)px;[^"]*top:([\\d.]+)px[^"]*">([^<]*)<`, 'g'))];
  return {
    note: { x: +co[1], y: +co[2], w: [...text].reduce((w, ch) => w + 38 * (/[\u2E80-\u9FFF\uFF00-\uFFEF]/.test(ch) ? 0.99 : 0.6), 0), h: 52 },   // full-width letters a whole em, digits a little over half
    labels: vals.map((m) => ({ x: +m[1], y: +m[2], w: 24 * [...m[3]].length, h: 46 })),
  };
};
const overlaps = (a, b) => Math.min(a.x + a.w, b.x + b.w) > Math.max(a.x, b.x) && Math.min(a.y + a.h, b.y + b.h) > Math.max(a.y, b.y);

test('a note never lands on a value label, wherever its point is', () => {
  const shapes = [[5, 50, 75, 90], [90, 60, 40, 20], [20, 90, 30, 85], [58, 44, 34, 25, 21], [10, 95, 100, 98]];
  for (const ys of shapes) {
    for (let index = 0; index < ys.length; index++) {
      const scene = { id: 's4', visual: { type: 'chart', kind: 'line', yMax: 100, unit: '%', points: ys.map((y, i) => ({ x: `${i + 1}日`, y })) }, cues: [{ op: 'chart.callout', index, text: '平均 約66日' }] };
      const { html } = renderStage(scene, {});
      const { note, labels } = rects(html, 's4');
      for (const l of labels) assert.ok(!overlaps(note, l), `${ys} @${index}: note ${JSON.stringify(note)} on label ${JSON.stringify(l)}`);
      assert.ok(note.x >= 8 && note.y >= 8 && note.x + note.w <= STAGE.w - 8, `${ys} @${index}: inside the stage`);
      const arrow = html.match(new RegExp(`id="s4-coa0" d="([^"]+)"`))[1];
      assert.ok(!/NaN|undefined|Infinity/.test(arrow), arrow);
      assert.ok(!/NaN|undefined|Infinity/.test(html.match(new RegExp(`id="s4-coh0" d="([^"]+)"`))[1]));
    }
  }
});

// The film published on the page (showcase/e001) was made by the first version of this renderer. Its charts must come out the same, so a film made
// again is the film people have seen. One number moved on purpose: the stamp of scene s3 was placed by its top edge (top:312px) and is now placed by its
// centre (top:390px, half its 156 px height lower), which is the very same place on the screen.
test('the published sample\'s charts are laid out exactly as before', () => {
  const ep = readJSON(path.join(ROOT, 'showcase/e001/script.json'));
  const golden = path.join(ROOT, 'test', 'scenes.golden.json');
  const now = Object.fromEntries(ep.scenes.filter((s) => s.visual.type !== 'illustration').map((s) => [s.id, renderStage(s, {})]));
  if (!fs.existsSync(golden)) fs.writeFileSync(golden, JSON.stringify(now));
  assert.deepEqual(now, JSON.parse(fs.readFileSync(golden, 'utf8')));
});

// The stamp as it is on the screen: its box (see .stamp in theme.mjs) tilted by 5° about its centre, as a cloud of points
const stampPoints = (text, fs, cx, cy) => {
  const w = [...text].length * fs * 0.96 + 0.6 * fs + 18, h = fs * 1.448 + 0.14 * fs + 18, a = (-5 * Math.PI) / 180, pts = [];
  for (let u = -w / 2; u <= w / 2; u += 4) for (let v = -h / 2; v <= h / 2; v += 4) pts.push([cx + u * Math.cos(a) - v * Math.sin(a), cy + u * Math.sin(a) + v * Math.cos(a)]);
  return pts;
};
const inside = ([x, y], r) => x > r.x && x < r.x + r.w && y > r.y && y < r.y + r.h;

test('the stamp keeps off the numbers, the note and the curve, and shrinks when it must (the rising curve of a habit chart)', () => {
  const shapes = [[5, 50, 75, 90, 95], [95, 60, 40, 30, 21], [30, 30, 30, 30], [10, 40, 90, 95, 100]];
  for (const ys of shapes) {
    const scene = { id: 's4', visual: { type: 'chart', kind: 'line', yMax: 100, unit: '%', points: ys.map((y, i) => ({ x: `${i + 1}日`, y })) },
      cues: [{ op: 'chart.callout', index: ys.length - 2, text: '平均 約66日' }, { op: 'stamp', text: '休んでも大丈夫' }] };
    const { html } = renderStage(scene, {});
    const { note, labels } = rects(html, 's4');
    const m = html.match(/id="s4-stamp0" style="left:(\d+)px;top:(\d+)px;opacity:0;font-size:(\d+)px"/);
    const [cx, cy, fs] = [+m[1], +m[2], +m[3]];
    const b = stampBox('休んでも大丈夫', fs), pts = stampPoints('休んでも大丈夫', fs, cx, cy);
    assert.ok(fs >= 58 && fs <= 104, `${ys}: font ${fs}`);
    assert.ok(cx - b.w / 2 >= 0 && cx + b.w / 2 <= STAGE.w && cy - b.h / 2 >= 0 && cy + b.h / 2 <= STAGE.h, `${ys}: inside the stage`);
    for (const l of labels) assert.ok(!pts.some((q) => inside(q, l)), `${ys}: stamp on label ${JSON.stringify(l)}`);
    assert.ok(!pts.some((q) => inside(q, note)), `${ys}: stamp on the note`);
    // and not across the drawn curve: sample the polyline through the dots
    const dots = [...html.matchAll(/<circle cx="([\d.]+)" cy="([\d.]+)"/g)].map((d) => [+d[1], +d[2]]);
    for (let i = 0; i < dots.length - 1; i++) for (let t = 0; t <= 1; t += 0.05) {
      const x = dots[i][0] + (dots[i + 1][0] - dots[i][0]) * t, y = dots[i][1] + (dots[i + 1][1] - dots[i][1]) * t;
      assert.ok(!pts.some(([px, py]) => Math.hypot(px - x, py - y) < 5), `${ys}: the curve runs through the stamp at ${x | 0},${y | 0}`);
    }
  }
});

test('a stamp keeps its usual place, big and upper right, when the chart leaves it empty (a falling curve)', () => {
  const ys = [40, 20, 12, 8, 5];
  const scene = { id: 's2', visual: { type: 'chart', kind: 'line', yMax: 100, unit: '%', points: ys.map((y, i) => ({ x: `${i + 1}日後`, y })) }, cues: [{ op: 'stamp', text: '忘却曲線' }] };
  const { html } = renderStage(scene, {});
  assert.match(html, /id="s2-stamp0" style="left:835px;top:221px;opacity:0;font-size:104px"/);
});

test('stampTouches agrees with a brute-force look at the tilted stamp', () => {
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  let touching = 0;
  for (let n = 0; n < 400; n++) {
    const fs = [58, 76, 104][n % 3], [cx, cy] = [300 + rnd() * 500, 200 + rnd() * 300];
    const r = { x: cx - 450 + rnd() * 900, y: cy - 250 + rnd() * 500, w: 20 + rnd() * 160, h: 20 + rnd() * 120 };
    const got = stampTouches('休んでも', fs, cx, cy)(r);
    // the stamp with its margin, filled in with points a pixel apart
    const w = 4 * fs * 0.96 + 0.6 * fs + 18 + 16, h = fs * 1.5 + 0.14 * fs + 18 + 16, a = (-5 * Math.PI) / 180;
    let hit = 0;
    for (let u = -w / 2; u <= w / 2 && !hit; u += 1) for (let v = -h / 2; v <= h / 2; v += 1) if (inside([cx + u * Math.cos(a) - v * Math.sin(a), cy + u * Math.sin(a) + v * Math.cos(a)], r)) { hit = 1; break; }
    if (hit) assert.ok(got, `brute force finds a touch, the test does not: ${JSON.stringify({ fs, cx, cy, r })}`);
    if (got && !hit) { /* only ever by a sliver thinner than the point spacing */ }
    touching += got ? 1 : 0;
  }
  assert.ok(touching > 40 && touching < 360, `the sample covers both cases (${touching} of 400 touch)`);
});

test('the stamp animation leaves its centring to GSAP (a y tween must not reset the CSS translate)', () => {
  const src = fs.readFileSync(path.join(ROOT, 'lib/visual/runtime.js'), 'utf8');
  const body = src.slice(src.indexOf('function stampIn'), src.indexOf('function drawAxes'));
  assert.match(body, /gsap\.set\(el, \{[^}]*xPercent: -50[^}]*yPercent: -50/);
});
