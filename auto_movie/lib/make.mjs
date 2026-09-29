// `make`: theme + length + reference material → finished MP4. Every stage is resumable: artifacts live in the run directory
// and a stage is skipped when its output exists (use `force` to redo it). Progress goes to log() so the CLI and the UI share it.
import path from 'node:path';
import fs from 'node:fs';
import { ROOT, ensureDir, exists, readJSON, writeJSON, log, round, run } from './util.mjs';
import { loadSeries, loadStyles, castFor } from './styles.mjs';
import { collectSources } from './stages/sources.mjs';
import { makePlan, INTRO_SEC, OUTRO_SEC } from './stages/plan.mjs';
import { makeScript, reviseLength } from './stages/script.mjs';
import { illustrate } from './stages/illustrate.mjs';
import { countChars } from './schema.mjs';
import { linesOf, stageVoice, stageTimeline, stageMusic, stageMix, stageCompose, stageCheck, stageRender } from './pipeline.mjs';
import { runQA } from './qa.mjs';
import { makeWebCopy } from './publish.mjs';


const pad = (n, w = 2) => String(Math.floor(n)).padStart(w, '0');
const srtTime = (t) => `${pad(t / 3600)}:${pad((t % 3600) / 60)}:${pad(t % 60)},${pad(Math.round((t % 1) * 1000), 3)}`;
const mmss = (t) => `${Math.floor(t / 60)}:${pad(t % 60)}`;

/** Subtitles (.srt), chapter list and a description with the credits – handy when the video is published. */
function writePublishingExtras({ dir, timeline, episode, series, plan }) {
  const names = { host: series.cast.host.name, guest: series.cast.guest?.name };
  const lines = [...timeline.scenes.flatMap((sc) => sc.lines), ...timeline.outro.lines];
  let n = 0, srt = '';
  for (const ln of lines) {
    ln.pages.forEach((pg, k) => {
      const a = ln.start + pg.t0, b = k + 1 < ln.pages.length ? ln.start + ln.pages[k + 1].t0 : ln.end + 0.1;
      srt += `${++n}\n${srtTime(a)} --> ${srtTime(Math.max(a + 0.4, b - 0.02))}\n${names[ln.who] || ''}：${pg.text}\n\n`;
    });
  }
  fs.writeFileSync(path.join(dir, 'captions.srt'), srt);
  const chapters = [['イントロ', 0], ...timeline.scenes.map((sc) => [episode.scenes.find((x) => x.id === sc.id).headline, sc.start]), ['エンディング', timeline.outro.start]];
  const desc = `${series.name} No.${String(episode.episode || 1).padStart(3, '0')}　${episode.title}\n${episode.subtitle || ''}\n\n` +
    chapters.map(([t, s]) => `${mmss(s)} ${t}`).join('\n') +
    `\n\n【参考にした事実】\n${(plan?.facts || []).map((f) => `・${f.text}`).join('\n')}\n\n【クレジット】\n${series.credits.join('\n')}\nイラスト・BGM・映像：auto_movie（HyperFrames でレンダリング）\n`;
  fs.writeFileSync(path.join(dir, 'youtube-description.txt'), desc);
}

export const STAGES = ['sources', 'plan', 'script', 'illustrate', 'voice', 'audio', 'compose', 'check', 'render', 'qa'];

/**
 * @param {object} o
 * @param {string} o.theme
 * @param {number} [o.lengthSec=180]
 * @param {string[]} [o.sources]
 * @param {string} [o.style='auto']
 * @param {string} [o.series='lifehack']
 * @param {string} [o.provider='voicevox']   voicevox | gemini | mock
 * @param {string} [o.quality='looks']       draft | looks | delivery
 * @param {string} o.runDir
 * @param {string[]} [o.force]               stages to redo
 * @param {string} [o.out]                   final mp4 path
 */
export async function make(o) {
  const t0 = Date.now();
  const { theme, lengthSec = 180, sources = [], style: styleId = 'auto', series: seriesId = 'lifehack', provider = 'voicevox', quality = 'looks', force = [], episodeNo = 1, concurrency = 3, keepScript = false, onStage } = o;
  const runDir = ensureDir(path.resolve(o.runDir));
  const series = loadSeries(seriesId), styles = loadStyles();
  const redo = (s) => force.includes(s) || force.includes('all');
  const stage = (name) => { log('stage', `▶ ${name}`); onStage?.(name); };
  writeJSON(path.join(runDir, 'input.json'), { theme, lengthSec, sources, style: styleId, series: seriesId, provider, quality, episodeNo });

  // 1. reference material
  stage('sources');
  const src = await collectSources(sources, { runDir });

  // 2. plan (style decision + outline)
  stage('plan');
  const planFile = path.join(runDir, 'plan.json');
  const plan = exists(planFile) && !redo('plan') ? readJSON(planFile) : await makePlan({ theme, lengthSec, styleId, series, sourcesText: src.text, runDir });
  const style = styles[plan.style];
  const cast = castFor(series, style);

  // 3. script
  stage('script');
  const scriptFile = path.join(runDir, 'script.json');
  let episode = exists(scriptFile) && !redo('script') ? readJSON(scriptFile) : (await makeScript({ plan, series, style, sourcesText: src.text, lengthSec, runDir })).episode;

  // 4. illustrations (in the background of the voice stage would save time, but keep it simple and robust)
  stage('illustrate');
  await illustrate({ episode, runDir, concurrency, force: redo('illustrate') });

  // 5. voice + fit. If the script cannot be fitted into the length by a modest tempo change, have the model rewrite it.
  stage('voice');
  const seriesForRun = { ...series, cast };
  let voice, fitted;
  for (let round_ = 1; round_ <= 3; round_++) {
    voice = await stageVoice({ episode, series: seriesForRun, runDir, provider });
    fitted = stageTimeline({ episode, voice, targetSec: lengthSec, runDir, speedRange: keepScript ? [0.8, 1.25] : [0.92, 1.09] });
    if (fitted.fit.ok || keepScript) { if (!fitted.fit.ok) log('fit', `--keep-script: script left as is (needs ×${fitted.fit.k}; used ×${fitted.speed}). ${fitted.fit.advice}`); break; }
    if (round_ === 3) { log('fit', `WARNING: could not fit after ${round_ - 1} rewrites — continuing at speed ×${fitted.fit.k}`); break; }
    const tooLong = fitted.fit.k > 1;
    const budgetDelta = Math.max(20, Math.round(Math.abs(fitted.fit.speechSec * (1 - 1 / fitted.fit.k)) * 6.65)); // seconds of speech to cut/add × chars per second
    log('fit', `script ${tooLong ? 'too long' : 'too short'} for ${lengthSec}s (×${fitted.fit.k}) → asking for a rewrite (${budgetDelta} chars)`);
    episode = await reviseLength({ episode, plan, series: seriesForRun, style, direction: tooLong ? 'shorter' : 'longer', deltaChars: budgetDelta, sourcesText: src.text, lengthSec, runDir, round: round_ });
    await illustrate({ episode, runDir, concurrency }); // element ids are unchanged, so this is a no-op unless a scene was added
  }
  const { timeline, speed } = fitted;

  // 6. audio: music composed for this timeline, mixed with the voice
  stage('audio');
  const music = stageMusic({ episode, timeline, series: seriesForRun, runDir, seed: `${seriesId}:${episodeNo}:${plan.title}`, style });
  const mix = await stageMix({ timeline, voice, bgm: music.audio, runDir, speed, series: seriesForRun });

  // 7. picture
  stage('compose');
  const project = await stageCompose({ episode, timeline, series: seriesForRun, runDir, audioFile: mix.masterPath, episodeNo, style });

  stage('check');
  const check = await stageCheck({ runDir });
  const fatal = /Runtime\s*\n\s*✗|✗ [a-z_]+:/.test(check.out);
  if (fatal) throw new Error(`hyperframes check found errors; see ${path.join(runDir, 'check.log')}`);

  stage('render');
  const video = path.join(runDir, 'video.mp4');
  await stageRender({ runDir, quality, out: video });

  stage('qa');
  const qa = await runQA({ runDir, video, targetSec: lengthSec, checkLog: check.out });

  let finalPath = null;
  if (o.out) {
    finalPath = path.resolve(o.out);
    ensureDir(path.dirname(finalPath));
    fs.copyFileSync(video, finalPath);
    // extras next to the video: the music on its own, the score, the QA report and pictures
    const extras = ensureDir(path.join(path.dirname(finalPath), path.basename(finalPath, path.extname(finalPath))));
    const copy = (src, name) => { if (exists(src)) fs.copyFileSync(src, path.join(extras, name)); };
    copy(path.join(runDir, 'audio', 'score.mid'), 'bgm-score.mid');
    copy(path.join(runDir, 'qa', 'report.md'), 'qa-report.md');
    copy(path.join(runDir, 'qa', 'report.json'), 'qa-report.json');
    copy(path.join(runDir, 'qa', 'contact-sheet.png'), 'contact-sheet.png');
    copy(path.join(runDir, 'qa', 'audio-overview.png'), 'audio-overview.png');
    copy(path.join(runDir, 'qa', 'readings.md'), 'readings.md');
    copy(path.join(runDir, 'script.json'), 'script.json');
    copy(path.join(runDir, 'plan.json'), 'plan.json');
    if (exists(path.join(runDir, 'audio', 'bgm.wav'))) await run('ffmpeg', ['-y', '-loglevel', 'error', '-i', path.join(runDir, 'audio', 'bgm.wav'), '-c:a', 'aac', '-b:a', '192k', path.join(extras, 'bgm.m4a')]);
    writePublishingExtras({ dir: extras, timeline, episode, series: seriesForRun, plan });
    // a light copy for sharing (about a quarter of the size of the master)
    await makeWebCopy(finalPath, finalPath.replace(/\.mp4$/, '.web.mp4'));
    log('done', `video → ${finalPath} (+ extras in ${extras})`);
  }
  const summary = { runDir, video, finalPath, style: plan.style, title: episode.title, lengthSec, measuredSec: qa.measuredSec, qa: qa.status, chars: countChars(episode), speed, seconds: round((Date.now() - t0) / 1000, 0) };
  writeJSON(path.join(runDir, 'summary.json'), summary);
  log('done', `QA ${qa.status}; ${summary.seconds}s total`);
  return summary;
}
