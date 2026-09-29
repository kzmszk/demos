// The publishing side: chapters, key frames, the QA numbers, and the contract between showcase/videos.json and the page.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { readJSON } from '../lib/util.mjs';
import { chaptersOf, keyTimes, qaSummary, SHOWCASE } from '../lib/publish.mjs';

test('chapters are read back from the description that make.mjs writes', () => {
  const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'am-')), 'youtube-description.txt');
  fs.writeFileSync(f, '今日のライフハック No.001　題\n副題\n\n0:00 イントロ\n0:04 昨日覚えたのに、もう忘れた！？\n1:17 復習は1日後・1週間後\n2:52 エンディング\n\n【クレジット】\nVOICEVOX:四国めたん\n');
  assert.deepEqual(chaptersOf(f), [{ t: 0, title: 'イントロ' }, { t: 4, title: '昨日覚えたのに、もう忘れた！？' }, { t: 77, title: '復習は1日後・1週間後' }, { t: 172, title: 'エンディング' }]);
  assert.deepEqual(chaptersOf(path.join(os.tmpdir(), 'no-such-file.txt')), []);
});

test('key frames: the title card, then just before every scene change', () => {
  const ch = [0, 4, 21, 52, 172].map((t, i) => ({ t, title: `c${i}` })); // intro, three scenes, ending
  assert.deepEqual(keyTimes(ch, 180, 10), [2.6, 20.5, 51.5, 171.5]);
  assert.equal(keyTimes(ch, 3, 10)[0], 1.5, 'the title card time never passes the middle of a very short video');
  const many = [0, ...Array.from({ length: 20 }, (_, i) => 4 + i * 8), 200].map((t, i) => ({ t, title: `c${i}` }));
  const picked = keyTimes(many, 210, 10);
  assert.equal(picked.length, 10);
  assert.equal(picked[0], 2.6);
  assert.deepEqual([...picked].sort((a, b) => a - b), picked, 'stays in order when thinned out');
});

test('the QA summary carries the numbers the page shows', () => {
  const report = {
    status: 'PASS', targetSec: 180, measuredSec: 180,
    checks: [
      { id: 'overlap', status: 'pass', detail: '49 行、最小の間隔 0.34 秒、重なり 0 件', data: { minGap: 0.339999, overlaps: 0 } },
      { id: 'loudness', status: 'pass', detail: '-16 LUFS', data: { integrated: -16, lra: 3.7, truePeak: -1.4 } },
      { id: 'bgm-balance', status: 'pass', detail: '声 -20.9 dB、BGM -38.4 dB、差 17.5 dB（14 dB 以上で声が埋もれない）' },
      { id: 'hf-check', status: 'pass', detail: '◇ 0 issues across 9 sample(s) / ◇ 59/59 text checks pass WCAG AA' },
      { id: 'freeze', status: 'warn', detail: '静止区間あり' },
    ],
  };
  assert.deepEqual(qaSummary(report), {
    status: 'PASS', checks: 5, passed: 4, targetSec: 180, measuredSec: 180, lines: 49, minGapSec: 0.34, overlaps: 0,
    lufs: -16, truePeakDb: -1.4, voiceOverMusicDb: 17.5, textContrast: { pass: 59, total: 59 },
  });
  assert.equal(qaSummary(null), undefined);
});

test('showcase/videos.json has everything the page reads, and the files it points at exist', () => {
  const db = readJSON(path.join(SHOWCASE, 'videos.json'));
  assert.ok(db.episodes.length > 0);
  const nos = db.episodes.map((e) => e.no);
  assert.deepEqual([...nos].sort((a, b) => b - a), nos, 'newest first');
  assert.equal(new Set(nos).size, nos.length, 'no duplicate episode numbers');
  for (const e of db.episodes) {
    assert.equal(e.id, String(e.no).padStart(3, '0'));
    assert.ok(e.title.ja && e.subtitle.ja && e.series.name.ja, 'Japanese texts are required; English is optional');
    assert.equal(e.titleLines.ja.join(''), e.title.ja, 'the big title is the title, split');
    if (e.titleLines.en) assert.equal(e.titleLines.en.join(' '), e.title.en);
    assert.ok(e.seconds > 0 && e.width > 0 && e.height > 0 && e.fps > 0);
    assert.ok(e.drive.stream && e.drive.master && e.drive.streamBytes > 0 && e.drive.masterBytes > 0);
    assert.equal(e.chapters[0].t, 0);
    assert.ok(e.chapters.every((c, i) => c.title && (i === 0 || c.t > e.chapters[i - 1].t) && c.t < e.seconds), 'chapters ascend and fit in the video');
    assert.ok(e.files.poster, 'a poster is required');
    for (const f of Object.values(e.files)) if (!/^https?:/.test(f)) assert.ok(fs.existsSync(path.join(SHOWCASE, f)), `${f} exists`);
  }
});
