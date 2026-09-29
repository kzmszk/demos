// Automated QA of a finished run: is the length right, can voices ever overlap, is the mix sane, do captions cover the
// speech, does the picture keep changing, and where are the frames a human should look at. Writes qa/report.{json,md}.
import path from 'node:path';
import fs from 'node:fs';
import { run, ensureDir, readJSON, writeJSON, writeText, exists, log, round } from './util.mjs';
import { readWav, db } from './audio/wav.mjs';

const FFMPEG = process.env.FFMPEG || 'ffmpeg', FFPROBE = process.env.FFPROBE || 'ffprobe';
const S = { pass: 'pass', warn: 'warn', fail: 'fail' };

async function probe(video) {
  const r = await run(FFPROBE, ['-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', video], { check: true });
  const j = JSON.parse(r.stdout);
  const v = j.streams.find((s) => s.codec_type === 'video'), a = j.streams.find((s) => s.codec_type === 'audio');
  const [n, d] = (v?.r_frame_rate || '0/1').split('/').map(Number);
  return {
    duration: +j.format.duration, size: +j.format.size, bitrate: +j.format.bit_rate,
    video: v && { codec: v.codec_name, width: v.width, height: v.height, fps: d ? n / d : 0, frames: +v.nb_frames || null, duration: +v.duration },
    audio: a && { codec: a.codec_name, rate: +a.sample_rate, channels: a.channels, duration: +a.duration },
  };
}

async function loudness(video) {
  const r = await run(FFMPEG, ['-hide_banner', '-nostats', '-i', video, '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']);
  const t = r.stderr;
  const num = (re) => { const m = t.match(re); return m ? +m[1] : null; };
  return { integrated: num(/I:\s+(-?[\d.]+) LUFS/), lra: num(/LRA:\s+(-?[\d.]+) LU/), truePeak: num(/Peak:\s+(-?[\d.]+) dBFS/) };
}

async function silences(video, noise = -45, d = 0.8) {
  const r = await run(FFMPEG, ['-hide_banner', '-nostats', '-i', video, '-vn', '-af', `silencedetect=noise=${noise}dB:d=${d}`, '-f', 'null', '-']);
  const out = [];
  for (const m of r.stderr.matchAll(/silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+) \| silence_duration: ([\d.]+)/g)) out.push({ start: +m[1], end: +m[2], dur: +m[3] });
  return out;
}

async function freezes(video, d = 5) {
  const r = await run(FFMPEG, ['-hide_banner', '-nostats', '-i', video, '-an', '-vf', `freezedetect=n=0.0008:d=${d}`, '-f', 'null', '-']);
  const out = [];
  for (const m of r.stderr.matchAll(/freeze_start: ([\d.]+)[\s\S]*?freeze_duration: ([\d.]+)/g)) out.push({ start: +m[1], dur: +m[2] });
  return out;
}

/** RMS in dBFS per window (mono mix of a stem). */
function activity(stem, win = 0.02) {
  const n = Math.floor(stem.channels[0].length / (stem.rate * win)), step = Math.round(stem.rate * win);
  const out = new Float32Array(n);
  for (let w = 0; w < n; w++) {
    let s = 0;
    for (let i = w * step; i < (w + 1) * step; i++) { const v = (stem.channels[0][i] + stem.channels[stem.channels.length - 1][i]) / 2; s += v * v; }
    out[w] = db(Math.sqrt(s / step));
  }
  return { win, db: out };
}

async function contactSheet(video, times, outDir, name, { cols = 5, w = 640 } = {}) {
  ensureDir(outDir);
  const tmp = ensureDir(path.join(outDir, `.${name}`));
  for (let i = 0; i < times.length; i++) {
    await run(FFMPEG, ['-y', '-loglevel', 'error', '-ss', String(times[i]), '-i', video, '-frames:v', '1', '-vf', `scale=${w}:-1`, path.join(tmp, `f${String(i).padStart(3, '0')}.png`)], { check: true });
  }
  const rows = Math.ceil(times.length / cols);
  const out = path.join(outDir, `${name}.png`);
  await run(FFMPEG, ['-y', '-loglevel', 'error', '-framerate', '1', '-i', path.join(tmp, 'f%03d.png'), '-vf', `tile=${cols}x${rows}:padding=6:color=#c9c2b4`, '-frames:v', '1', out], { check: true });
  fs.rmSync(tmp, { recursive: true, force: true });
  return out;
}

export async function runQA({ runDir, video, targetSec, checkLog }) {
  const qaDir = ensureDir(path.join(runDir, 'qa'));
  const timeline = readJSON(path.join(runDir, 'timeline.json'));
  const am = exists(path.join(runDir, 'project', 'am-data.json')) ? readJSON(path.join(runDir, 'project', 'am-data.json')) : null;
  const checks = [];
  const add = (id, label, status, detail, data) => { checks.push({ id, label, status, detail, data }); log('qa', `${status.toUpperCase().padEnd(4)} ${label}: ${detail}`); };

  // ---- 1. container / length
  const pr = await probe(video);
  const dErr = pr.duration - targetSec;
  add('length', `動画の長さ（指定 ${targetSec} 秒）`, Math.abs(dErr) <= 0.25 ? S.pass : Math.abs(dErr) <= 1 ? S.warn : S.fail, `${round(pr.duration, 2)} 秒（差 ${dErr >= 0 ? '+' : ''}${round(dErr, 2)} 秒）`, pr);
  add('format', '映像・音声の形式', pr.video?.width === 1920 && pr.video?.height === 1080 && Math.abs(pr.video.fps - 30) < 0.01 && pr.audio ? S.pass : S.fail,
    `${pr.video?.width}×${pr.video?.height} ${round(pr.video?.fps, 2)}fps ${pr.video?.codec} / 音声 ${pr.audio?.codec} ${pr.audio?.rate}Hz ${pr.audio?.channels}ch`);
  add('av-length', '映像と音声の長さの一致', Math.abs((pr.video?.duration || 0) - (pr.audio?.duration || 0)) <= 0.1 ? S.pass : S.warn, `映像 ${round(pr.video?.duration, 2)} 秒 / 音声 ${round(pr.audio?.duration, 2)} 秒`);

  // ---- 2. voice schedule: can two voices overlap?
  const lines = [...timeline.scenes.flatMap((s) => s.lines), ...timeline.outro.lines].sort((a, b) => a.start - b.start);
  let minGap = 1e9, overlaps = 0, sameRun = 1, maxSame = 1;
  for (let i = 1; i < lines.length; i++) {
    const g = lines[i].start - lines[i - 1].end;
    minGap = Math.min(minGap, g);
    if (g < 0.05) overlaps++;
    sameRun = lines[i].who === lines[i - 1].who ? sameRun + 1 : 1; maxSame = Math.max(maxSame, sameRun);
  }
  const speech = lines.reduce((s, l) => s + (l.end - l.start), 0);
  add('overlap', '声の重なり（台本上のスケジュール）', overlaps === 0 ? S.pass : S.fail, `${lines.length} 行、最小の間隔 ${round(minGap, 2)} 秒、重なり ${overlaps} 件`, { minGap, overlaps });
  add('turns', '掛け合いのテンポ', maxSame <= 3 ? S.pass : S.warn, `同じ人が続けて話す最長 ${maxSame} 行、発話時間 ${round(speech, 1)} 秒（全体の ${round((speech / targetSec) * 100, 0)}%）`);

  // ---- 3. audio, from the stems and from the rendered file
  const ld = await loudness(video);
  add('loudness', 'ラウドネス（目標 -16 LUFS）', Math.abs(ld.integrated + 16) <= 1.2 ? S.pass : S.warn, `${ld.integrated} LUFS、LRA ${ld.lra} LU、トゥルーピーク ${ld.truePeak} dBFS`, ld);
  add('peak', '音の割れ（ピーク）', ld.truePeak <= -1 ? S.pass : ld.truePeak <= 0 ? S.warn : S.fail, `最大 ${ld.truePeak} dBFS`);
  const sil = await silences(video);
  const badSil = sil.filter((s) => s.dur >= 1.0 && s.start < pr.duration - 1);
  add('silence', '無音の区間', badSil.length === 0 ? S.pass : S.warn, badSil.length ? badSil.map((s) => `${round(s.start, 1)}s から ${round(s.dur, 1)} 秒`).join(', ') : '1 秒以上の無音なし', sil);

  const stemPath = (n) => path.join(runDir, 'audio', `stem-${n}.wav`);
  if (exists(stemPath('voice')) && exists(stemPath('bgm'))) {
    const V = readWav(stemPath('voice')), B = readWav(stemPath('bgm'));
    const Sx = exists(stemPath('sfx')) ? readWav(stemPath('sfx')) : null;
    const av = activity(V), ab = activity(B), as = Sx ? activity(Sx) : null;
    const w = av.win;
    const inLine = (t) => lines.some((l) => t >= l.start - 0.15 && t <= l.end + 0.15);
    let stray = 0, sv = 0, sb = 0, ss = 0, nsp = 0, silentInLine = 0, nInLine = 0;
    for (let i = 0; i < av.db.length; i++) {
      const t = i * w;
      const active = av.db[i] > -52;
      const inside = lines.some((l) => t >= l.start && t < l.end);
      if (active && !inLine(t)) stray += w;
      if (inside) {
        nInLine++;
        if (!active) silentInLine++;
        if (active) { nsp++; sv += 10 ** (av.db[i] / 10); sb += 10 ** (ab.db[Math.min(i, ab.db.length - 1)] / 10); if (as) ss += 10 ** (as.db[Math.min(i, as.db.length - 1)] / 10); }
      }
    }
    const vdb = 10 * Math.log10(sv / Math.max(1, nsp)), bdb = 10 * Math.log10(sb / Math.max(1, nsp)), sdb = as ? 10 * Math.log10(ss / Math.max(1, nsp)) : -99;
    add('stray-voice', '予定外の声（スケジュール外の発話）', stray < 0.05 ? S.pass : S.fail, `${round(stray, 2)} 秒`);
    add('bgm-balance', '声とBGMの音量差（発話中）', vdb - bdb >= 14 ? S.pass : vdb - bdb >= 10 ? S.warn : S.fail, `声 ${round(vdb, 1)} dB、BGM ${round(bdb, 1)} dB、差 ${round(vdb - bdb, 1)} dB（14 dB 以上で声が埋もれない）`);
    add('sfx-balance', '声と効果音の音量差（発話中）', vdb - sdb >= 12 ? S.pass : S.warn, `効果音 ${round(sdb, 1)} dB、差 ${round(vdb - sdb, 1)} dB`);
  }

  // ---- 4. captions cover the speech
  if (am) {
    const caps = am.captions.slice().sort((a, b) => a.s - b.s);
    let uncovered = 0, tooLong = 0;
    for (const l of lines) {
      const mine = caps.filter((c) => c.e > l.start && c.s < l.end);
      let t = l.start;
      for (const c of mine) { if (c.s > t + 0.15) uncovered += c.s - t; t = Math.max(t, c.e); }
      if (l.end > t + 0.15) uncovered += l.end - t;
    }
    add('captions', '字幕が発話を覆っているか', uncovered < 0.3 ? S.pass : S.warn, `字幕のない発話時間 ${round(uncovered, 2)} 秒 / ページ数 ${caps.length}`);
    const long = lines.flatMap((l) => l.pages).filter((p) => p.text.replace(/[、。！？]/g, '').length > 40);
    tooLong = long.length;
    add('caption-size', '字幕1枚の文字数（40字以内）', tooLong === 0 ? S.pass : S.warn, tooLong ? `${tooLong} 枚が長い` : 'すべて収まっている');
  }

  // ---- 5. the picture keeps moving; scenes are neither rushed nor stuck
  const fr = await freezes(video, 6);
  add('freeze', '画面が止まっていないか（6秒以上の静止）', fr.filter((f) => f.start < pr.duration - 10).length === 0 ? S.pass : S.warn, fr.length ? fr.map((f) => `${round(f.start, 1)}s から ${round(f.dur, 1)} 秒`).join(', ') : '静止区間なし');
  const sd = timeline.scenes.map((s) => ({ id: s.id, type: s.type, dur: round(s.end - s.start, 1) }));
  const badScenes = sd.filter((s) => s.dur > 40 || s.dur < 8);
  add('scenes', 'シーンの長さ（8〜40 秒）', badScenes.length === 0 ? S.pass : S.warn, sd.map((s) => `${s.id}:${s.dur}s`).join(' '), sd);

  // ---- 6. sync of visual cues to speech
  const exact = timeline.cues.filter((c) => c.after != null && c.after !== '').length;
  add('cues', '画面の演出キュー', S.pass, `${timeline.cues.length} 個（語句に同期 ${exact}、行頭/行末 ${timeline.cues.length - exact}）`);

  // ---- 7. HyperFrames' own audit
  if (checkLog) {
    const errs = (checkLog.match(/(\d+) error\(s\)/g) || []);
    const layout = /Layout\s*\n\s*(.*)/.exec(checkLog)?.[1] || '';
    const contrast = /Contrast\s*\n\s*(.*)/.exec(checkLog)?.[1] || '';
    add('hf-check', 'HyperFrames の検査（レイアウト・コントラスト）', /✗/.test(checkLog) ? S.warn : S.pass, `${layout.replace(/\s+/g, ' ').trim()} / ${contrast.replace(/\s+/g, ' ').trim()}`);
  }

  // ---- contact sheets for a human
  const times = [2.5];
  for (const sc of timeline.scenes) { const d = sc.end - sc.start; times.push(round(sc.start + Math.min(2.5, d * 0.3)), round(sc.start + d * 0.62), round(sc.end - 0.8)); }
  times.push(round(timeline.outro.start + 1.5), round(Math.min(pr.duration - 0.3, timeline.duration - 1.0)));
  const sheet = await contactSheet(video, times.filter((t) => t < pr.duration), qaDir, 'contact-sheet', { cols: 5, w: 640 });

  // readings (for pronunciation review)
  if (exists(path.join(runDir, 'voice.json'))) {
    const vj = readJSON(path.join(runDir, 'voice.json'));
    writeText(path.join(qaDir, 'readings.md'), '# 読み上げ（VOICEVOX が解釈した読み）\n\n' + lines.map((l) => `- **${l.id}** ${l.text}\n  - ${vj[l.id]?.kana ?? ''}`).join('\n') + '\n');
  }

  const status = checks.some((c) => c.status === S.fail) ? 'FAIL' : checks.some((c) => c.status === S.warn) ? 'WARN' : 'PASS';
  const report = { status, video, targetSec, measuredSec: round(pr.duration, 3), checks, contactSheet: sheet };
  writeJSON(path.join(qaDir, 'report.json'), report);
  const icon = { pass: '✅', warn: '⚠️', fail: '❌' };
  writeText(path.join(qaDir, 'report.md'), `# 自動QAレポート：${status}\n\n動画：${video}\n\n| 結果 | 項目 | 内容 |\n|---|---|---|\n${checks.map((c) => `| ${icon[c.status]} | ${c.label} | ${c.detail} |`).join('\n')}\n\nコンタクトシート：${sheet}\n`);
  return report;
}
