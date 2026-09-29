// Fast, offline tests of the deterministic core (no LLM, no VOICEVOX, no browser).
import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { ROOT, readJSON } from '../lib/util.mjs';
import { validateScript, countChars, speechIssues } from '../lib/schema.mjs';
import { splitClauses, makePages, synthesizeLines } from '../lib/tts/index.mjs';
import { compileTimeline } from '../lib/timeline.mjs';
import { compose } from '../lib/audio/composer.mjs';
import { mouthFromSegs } from '../lib/visual/lipsync.mjs';
import { fitSpeed, linesOf } from '../lib/pipeline.mjs';
import { charBudget } from '../lib/stages/script.mjs';

const episode = readJSON(path.join(ROOT, 'examples/lifehack-001/script.json'));
const series = readJSON(path.join(ROOT, 'series/lifehack.json'));

test('the baseline script satisfies the schema', () => {
  const problems = validateScript(episode, { charBudget: 1010, tolerance: 0.15 });
  assert.deepEqual(problems, []);
});

test('the validator explains what is wrong', () => {
  const bad = JSON.parse(JSON.stringify(episode));
  bad.scenes[0].cues[0].target = 'nope';
  bad.scenes[1].cues = bad.scenes[1].cues.filter((c) => c.op !== 'chart.axes' && !(c.op === 'chart.point' && c.index === 3));
  bad.scenes[0].lines[0].text = 'Hello world';
  const p = validateScript(bad, {});
  assert.ok(p.some((m) => /target "nope"/.test(m)), p.join('\n'));
  assert.ok(p.some((m) => /pt:3/.test(m)), 'missing chart point cue is reported');
  assert.ok(p.some((m) => /英字/.test(m)));
});

test('clauses split at punctuation and pages respect the size limit', () => {
  const c = splitClauses('こんにちは、今日のライフハックです。覚えたはずなのに、次の日にはもう忘れている。');
  assert.equal(c.length, 4);
  const pages = makePages(c, 20);
  assert.ok(pages.every((p) => p.len <= 20));
  assert.equal(pages.map((p) => p.text).join(''), 'こんにちは、今日のライフハックです。覚えたはずなのに、次の日にはもう忘れている。');
});

test('speech issues are flagged', () => {
  assert.ok(speechIssues('これはAPIです。').length);
  assert.deepEqual(speechIssues('これは普通の文です。'), []);
});

async function mockVoice() {
  const lines = linesOf(episode);
  const out = await synthesizeLines({ lines, cast: series.cast, provider: 'mock', outDir: path.join(ROOT, '.cache', 'test-voice') });
  return { lines, out };
}

test('timeline lands on the requested length, voices never overlap, cues stay inside their scene', async () => {
  const { out } = await mockVoice();
  const fit = fitSpeed({ episode, voice: out, targetSec: 180 });
  const { timeline, stats } = compileTimeline({ episode, voice: out, targetSec: 180, speed: Math.min(1.14, Math.max(0.9, fit.k)) });
  assert.ok(Math.abs(timeline.duration - 180) < 1.2 || fit.ok === false, `duration ${timeline.duration}`);
  const lines = [...timeline.scenes.flatMap((s) => s.lines), ...timeline.outro.lines].sort((a, b) => a.start - b.start);
  for (let i = 1; i < lines.length; i++) assert.ok(lines[i].start >= lines[i - 1].end + 0.05, `${lines[i - 1].id} overlaps ${lines[i].id}`);
  for (const c of timeline.cues) {
    const s = timeline.scenes.find((x) => x.id === c.scene);
    assert.ok(c.t >= s.start && c.t <= s.end, `cue ${c.op} at ${c.t} outside ${s.id}`);
  }
  assert.ok(stats.lines === lines.length);
});

test('music is deterministic and fits the video exactly', () => {
  const sections = [{ t0: 0, t1: 4.4, label: 'intro', mood: 'warm', energy: 0.2 }, { t0: 4.4, t1: 100, label: 'a', mood: 'curious', energy: 0.4 }, { t0: 100, t1: 180, label: 'outro', mood: 'resolve', energy: 0.25 }];
  const a = compose({ duration: 180, sections, seed: 'x', key: 'F' }), b = compose({ duration: 180, sections, seed: 'x', key: 'F' });
  assert.deepEqual(a.notes.piano.slice(0, 40), b.notes.piano.slice(0, 40));
  assert.ok(Math.abs(a.bars * a.barSec - 180) < 1e-6);
  assert.ok(a.notes.piano.every((n) => n.midi >= 30 && n.midi <= 100 && n.t >= 0 && n.t < 180));
  const c = compose({ duration: 180, sections, seed: 'y', key: 'F' });
  assert.notDeepEqual(a.notes.piano.slice(0, 40), c.notes.piano.slice(0, 40));
});

test('lip-sync turns mora timing into a small set of mouth shapes', () => {
  const segs = [{ kind: 'mora', vowel: 'a', cons: 'k', t0: 0, tv: 0.03, t1: 0.12 }, { kind: 'mora', vowel: 'i', cons: null, t0: 0.12, tv: 0.12, t1: 0.2 }, { kind: 'pause', vowel: 'pau', t0: 0.2, tv: 0.2, t1: 0.4 }, { kind: 'mora', vowel: 'o', cons: 'm', t0: 0.4, tv: 0.45, t1: 0.6 }];
  const tr = mouthFromSegs(segs);
  assert.ok(tr.every(([t, s]) => t >= 0 && s >= 0 && s <= 3));
  assert.deepEqual(tr.map((x) => x[1]), [1, 2, 0, 3]); // a → i → (pause + bilabial m: closed) → o
});

test('character budget for 3 minutes is about a thousand characters', () => {
  const b = charBudget(180, 8);
  assert.ok(b > 900 && b < 1080, String(b));
  assert.ok(countChars(episode) > 900 && countChars(episode) < 1150);
});
