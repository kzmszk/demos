// Publishing: the finished video goes into a public Google Drive folder (through rclone) and is listed on the showcase page that the
// DEMOS gallery serves (auto_movie/demo.json → showcase/). Idempotent: run it again to refresh the pictures or the numbers.
import path from 'node:path';
import fs from 'node:fs';
import { ROOT, run, log, ensureDir, exists, readJSON, writeJSON, round } from './util.mjs';
import { loadSeries } from './styles.mjs';
import { splitTitle } from './visual/compose.mjs';

export const SHOWCASE = path.join(ROOT, 'showcase');
const COVERS = path.resolve(ROOT, '..', 'gallery', 'covers', path.basename(ROOT));
const CONFIG = path.join(ROOT, 'config', 'publish.json');
const pad3 = (n) => String(n).padStart(3, '0');
const ffmpeg = (args) => run('ffmpeg', ['-y', '-loglevel', 'error', ...args], { check: true });

/** An rclone remote whose root is confined to one public Drive folder. */
function driveRoot() {
  const c = readJSON(CONFIG);
  return `${process.env.AUTO_MOVIE_DRIVE_REMOTE || c.remote},root_folder_id=${process.env.AUTO_MOVIE_DRIVE_FOLDER || c.folderId}:`;
}
/** Direct, range-capable, CORS-open URL of a public Drive file – what the page's <video> plays. */
export const streamUrl = (id) => `https://drive.usercontent.google.com/download?id=${id}&export=download&confirm=t`;

/** The light copy used for streaming and sharing (about a quarter of the master's size). */
export const makeWebCopy = (src, dst) => ffmpeg(['-i', src, '-c:v', 'libx264', '-preset', 'slow', '-crf', '22', '-tune', 'animation', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', '-c:a', 'copy', dst]);

async function upload(file, root) {
  const name = path.basename(file), bytes = fs.statSync(file).size;
  const find = async () => JSON.parse((await run('rclone', ['lsjson', root, '--files-only'], { check: true })).stdout).find((f) => f.Name === name);
  let f = await find();
  if (f && f.Size === bytes) log('publish', `${name}: already on Drive`);
  else {
    log('publish', `uploading ${name} (${round(bytes / 1e6, 1)} MB)`);
    await run('rclone', ['copyto', file, root + name], { check: true });
    f = await find();
    if (!f) throw new Error(`${name} did not appear in the Drive folder`);
  }
  return { id: f.ID, bytes };
}

/** Can anyone (no login) stream it? */
async function isPublic(id) {
  try {
    const r = await fetch(streamUrl(id), { headers: { Range: 'bytes=0-15' } });
    await r.body?.cancel();
    return (r.status === 206 || r.status === 200) && /video/.test(r.headers.get('content-type') || '');
  } catch { return false; }
}

async function probe(file) {
  const j = JSON.parse((await run('ffprobe', ['-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', file], { check: true })).stdout);
  const v = j.streams.find((s) => s.codec_type === 'video');
  const [n, d] = v.r_frame_rate.split('/').map(Number);
  return { seconds: round(+j.format.duration, 3), width: v.width, height: v.height, fps: round(n / (d || 1), 2) };
}

/** Chapters as written into youtube-description.txt ("m:ss title"). */
export function chaptersOf(file) {
  if (!exists(file)) return [];
  return fs.readFileSync(file, 'utf8').split('\n').map((l) => l.match(/^(\d+):(\d\d)\s+(.+)$/)).filter(Boolean).map((m) => ({ t: +m[1] * 60 + +m[2], title: m[3].trim() }));
}

/** The numbers worth showing, taken from the QA report. */
export function qaSummary(report) {
  if (!report) return undefined;
  const c = Object.fromEntries(report.checks.map((x) => [x.id, x]));
  const first = (x, re) => { const m = (x?.detail || '').match(re); return m ? +m[1] : undefined; };
  const hf = (c['hf-check']?.detail || '').match(/(\d+)\/(\d+) text checks/);
  return {
    status: report.status, checks: report.checks.length, passed: report.checks.filter((x) => x.status === 'pass').length,
    targetSec: report.targetSec, measuredSec: report.measuredSec,
    lines: first(c.overlap, /^(\d+) 行/), minGapSec: c.overlap?.data?.minGap != null ? round(c.overlap.data.minGap, 2) : undefined, overlaps: c.overlap?.data?.overlaps,
    lufs: c.loudness?.data?.integrated, truePeakDb: c.loudness?.data?.truePeak, voiceOverMusicDb: first(c['bgm-balance'], /差 ([\d.]+) dB/),
    textContrast: hf ? { pass: +hf[1], total: +hf[2] } : undefined,
  };
}

function llmCost(runDir) {
  const d = path.join(runDir, 'llm');
  if (!exists(d)) return undefined;
  const sum = fs.readdirSync(d).filter((f) => f.endsWith('.json')).reduce((s, f) => s + (readJSON(path.join(d, f)).costUsd || 0), 0);
  return sum ? round(sum, 2) : undefined;
}

/** The title card, then the end of every scene (when all of its drawing has appeared). */
export function keyTimes(chapters, seconds, max) {
  let times = [Math.min(2.6, seconds / 2), ...chapters.slice(1, -1).map((_, i) => chapters[i + 2].t - 0.5)];
  if (times.length > max) times = Array.from({ length: max }, (_, k) => times[Math.round((k * (times.length - 1)) / (max - 1))]);
  return times;
}

/** Cover frames for the DEMOS gallery card (16:10 like the other works; the 16:9 picture sits on paper-coloured matte). */
async function makeCovers(video, times) {
  ensureDir(COVERS);
  for (const f of fs.readdirSync(COVERS)) if (/^\d\d\.webp$/.test(f)) fs.rmSync(path.join(COVERS, f));
  for (const [i, t] of times.entries()) {
    await ffmpeg(['-ss', String(t), '-i', video, '-frames:v', '1', '-vf', 'pad=iw:iw*10/16:0:(oh-ih)/2:color=0xfbf7ee,scale=960:600:flags=lanczos', '-c:v', 'libwebp', '-quality', '82', path.join(COVERS, `${String(i + 1).padStart(2, '0')}.webp`)]);
  }
  log('publish', `${times.length} gallery cover frames → ${path.relative(ROOT, COVERS)}`);
}

/** One picture of the whole film: those key frames, three across, on paper. */
async function makeStoryboard(video, times, out) {
  const tmp = ensureDir(path.join(path.dirname(out), '.sb'));
  for (const [i, t] of times.entries()) {
    await ffmpeg(['-ss', String(t), '-i', video, '-frames:v', '1', '-vf', 'scale=640:360:flags=lanczos,drawbox=0:0:iw:ih:color=0x3d3d3d@0.28:t=1', path.join(tmp, `f${String(i).padStart(3, '0')}.png`)]);
  }
  await ffmpeg(['-framerate', '1', '-i', path.join(tmp, 'f%03d.png'), '-vf', `tile=3x${Math.ceil(times.length / 3)}:padding=12:margin=0:color=0xfbf7ee,scale=1800:-1:flags=lanczos`, '-frames:v', '1', '-c:v', 'libwebp', '-quality', '82', out]);
  fs.rmSync(tmp, { recursive: true, force: true });
}

/**
 * @param {object} o
 * @param {string} o.video          master mp4 written by `make --out` (its extras folder and .web.mp4 sit next to it)
 * @param {number} [o.no=1]         episode number
 * @param {string} [o.runId]        run folder under runs/ (for the QA report and LLM cost)
 * @param {string} [o.titleEn]      English title; "|" marks a line break
 * @param {string} [o.subtitleEn]
 * @param {number} [o.posterAt]     second of the poster frame (default: a quarter of the way in)
 * @param {boolean} [o.covers]      also (re)make the gallery card's cover frames
 * @param {boolean} [o.upload=true] false: reuse the Drive IDs already in videos.json
 * @param {string} [o.date]
 */
export async function publish(o) {
  const master = path.resolve(o.video);
  if (!exists(master)) throw new Error(`video not found: ${master}`);
  const base = master.replace(/\.mp4$/i, ''), web = `${base}.web.mp4`;
  const from = (name) => path.join(base, name); // extras written next to the video by make.mjs
  for (const f of ['script.json', 'youtube-description.txt']) if (!exists(from(f))) throw new Error(`missing ${from(f)} — was this video made with "make --out"?`);
  if (!exists(web)) { log('publish', 'making the light copy'); await makeWebCopy(master, web); }

  const no = o.no ?? 1, id = pad3(no), dir = ensureDir(path.join(SHOWCASE, `e${id}`));
  const dbFile = path.join(SHOWCASE, 'videos.json');
  const db = exists(dbFile) ? readJSON(dbFile) : { episodes: [] };
  const before = db.episodes.find((e) => e.no === no);

  const script = readJSON(from('script.json')), plan = exists(from('plan.json')) ? readJSON(from('plan.json')) : {};
  const series = loadSeries(o.series || 'lifehack');
  const info = await probe(master);
  const chapters = chaptersOf(from('youtube-description.txt'));
  const runDir = o.runId ? path.join(ROOT, 'runs', o.runId) : null;
  const qaFile = runDir && exists(path.join(runDir, 'qa', 'report.json')) ? path.join(runDir, 'qa', 'report.json') : exists(from('qa-report.json')) ? from('qa-report.json') : null;

  // 1. the files: master for download, light copy for streaming
  let drive = before?.drive;
  if (o.upload !== false) {
    const root = driveRoot();
    const [m, w] = [await upload(master, root), await upload(web, root)];
    drive = { stream: w.id, master: m.id, streamBytes: w.bytes, masterBytes: m.bytes };
    if (!(await isPublic(w.id))) log('publish', `WARNING: ${web} cannot be streamed anonymously – is the Drive folder shared with "anyone with the link"?`);
  } else if (!drive) throw new Error('--no-upload needs an existing entry in showcase/videos.json');

  // 2. pictures and small files for the page
  const poster = o.posterAt ?? round(info.seconds / 4, 1);
  await ffmpeg(['-ss', String(poster), '-i', master, '-frames:v', '1', '-vf', 'scale=1280:720:flags=lanczos', '-c:v', 'libwebp', '-quality', '86', path.join(dir, 'poster.webp')]);
  const files = { poster: `e${id}/poster.webp`, ...(before?.files?.video ? { video: before.files.video } : {}) };
  await makeStoryboard(master, keyTimes(chapters, info.seconds, 12), path.join(dir, 'storyboard.webp'));
  files.storyboard = `e${id}/storyboard.webp`;
  if (exists(from('audio-overview.png'))) {
    await ffmpeg(['-i', from('audio-overview.png'), '-vf', 'scale=1800:-1:flags=lanczos', '-c:v', 'libwebp', '-quality', '80', path.join(dir, 'audio.webp')]);
    files.audio = `e${id}/audio.webp`;
  }
  for (const [key, src, out] of [['captions', 'captions.srt', 'captions.srt'], ['score', 'bgm-score.mid', 'bgm-score.mid'], ['script', 'script.json', 'script.json']]) {
    if (!exists(from(src))) continue;
    fs.copyFileSync(from(src), path.join(dir, out));
    files[key] = `e${id}/${out}`;
  }

  // 3. the entry
  const titleJa = script.title, enLines = (o.titleEn || '').split('|').map((s) => s.trim()).filter(Boolean);
  const entry = {
    no, id, date: o.date || before?.date || new Date().toLocaleDateString('sv-SE'),
    series: { id: series.id, name: { ja: series.name, en: series.nameEn || series.name } },
    title: { ja: titleJa, en: enLines.length ? enLines.join(' ') : before?.title?.en },
    titleLines: { ja: splitTitle(titleJa), en: enLines.length ? enLines : before?.titleLines?.en },
    subtitle: { ja: script.subtitle || '', en: o.subtitleEn || before?.subtitle?.en },
    style: plan.style || script.style, ...info, posterAt: poster,
    drive, chapters, files, facts: (plan.facts || []).map((f) => f.text),
    qa: (qaFile ? qaSummary(readJSON(qaFile)) : undefined) ?? before?.qa,
    build: { llmUsd: (runDir && llmCost(runDir)) ?? before?.build?.llmUsd, minutes: o.buildMinutes ?? before?.build?.minutes },
  };
  db.episodes = [...db.episodes.filter((e) => e.no !== no), JSON.parse(JSON.stringify(entry))].sort((a, b) => b.no - a.no);
  writeJSON(dbFile, db);
  log('publish', `showcase/videos.json: episode ${id} "${titleJa}" (${info.seconds}s)`);

  if (o.covers) await makeCovers(master, keyTimes(chapters, info.seconds, 10));
  return entry;
}
