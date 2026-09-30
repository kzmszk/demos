// Assembles the HyperFrames project (index.html + assets) from the script, the timeline and the audio.
import fs from 'node:fs';
import path from 'node:path';
import { ROOT, ensureDir, esc, round, writeText, writeJSON, jsonForScript } from '../util.mjs';
import { W, H, COLORS, STAGE, CAPTION, AVATAR, themeCSS } from './theme.mjs';
import { buildFonts } from './fonts.mjs';
import { renderStage } from './scenes.mjs';
import { avatarHTML, hiddenStateIds } from './avatars.mjs';
import { faceTracks } from './facetracks.mjs';
import { paperPNG } from './paper.mjs';

const walkStrings = (o, out = []) => {
  if (typeof o === 'string') out.push(o);
  else if (Array.isArray(o)) o.forEach((x) => walkStrings(x, out));
  else if (o && typeof o === 'object') Object.values(o).forEach((x) => walkStrings(x, out));
  return out;
};

/**
 * Split an episode title into 1–2 display lines: short titles stay on one line; otherwise break after 、 or at the most
 * balanced Japanese word boundary (never inside a word), preferring to break after a particle.
 */
export function splitTitle(title) {
  const t = title.trim();
  const m = t.match(/^(.+?[、,，。！？!?：:])(.+)$/);
  if (m && m[2].length >= 2) return [m[1], m[2]];
  if (t.length <= 9) return [t];
  const boundaries = new Set();
  let acc = 0;
  for (const w of new Intl.Segmenter('ja', { granularity: 'word' }).segment(t)) { acc += w.segment.length; boundaries.add(acc); }
  const numSym = (c) => /[0-9０-９%％〜~\-.,:/+]/.test(c);
  const startsWord = (c) => /[\u4e00-\u9fff\u30a0-\u30ffA-Za-z0-9]/.test(c);
  let best = null;
  for (const pos of boundaries) {
    if (pos <= 1 || pos >= t.length - 1) continue;
    if (/[、。！？」）]/.test(t[pos])) continue;
    if (numSym(t[pos - 1]) && numSym(t[pos])) continue;
    const afterParticle = /[はがをにでとのもへ]/.test(t[pos - 1]);
    if (!startsWord(t[pos])) continue;                 // only break before a kanji / katakana / alphanumeric word start
    const score = Math.abs(pos - (t.length - pos)) - (afterParticle ? 0.75 : 0);
    if (!best || score < best.score) best = { pos, score };
  }
  const cut = best ? best.pos : Math.ceil(t.length / 2);
  return [t.slice(0, cut), t.slice(cut)];
}

const t3 = (x) => (Math.round(x * 1000) / 1000).toString();

/**
 * Build <projectDir> for hyperframes. Returns { indexPath, data } where data is the runtime blob (AM).
 */
export async function buildProject({ episode, timeline, series, runDir, projectDir, audioFile, episodeNo = 1, label, style = { avatars: 2 } }) {
  ensureDir(projectDir);
  const assets = ensureDir(path.join(projectDir, 'assets'));
  const dur = timeline.duration;
  const cast = series.cast;
  const hasGuest = (style.avatars ?? 2) > 1;
  const sides = hasGuest ? { host: cast.host, guest: cast.guest } : { host: cast.host };

  // ---- assets: gsap, paper grain, fonts, audio
  fs.copyFileSync(path.join(ROOT, 'node_modules', 'gsap', 'dist', 'gsap.min.js'), path.join(assets, 'gsap.min.js'));
  fs.copyFileSync(path.join(ROOT, 'lib', 'visual', 'runtime.js'), path.join(assets, 'runtime.js'));
  fs.writeFileSync(path.join(assets, 'paper.png'), paperPNG(512, `paper:${series.id}`));
  if (audioFile) fs.copyFileSync(audioFile, path.join(assets, 'master.wav'));
  const texts = walkStrings([episode, series.name, series.tagline, series.credits, ...Object.values(cast).map((c) => [c.name, c.role])]).join('') + '0123456789/:%';
  const fonts = await buildFonts({ text: texts, outDir: path.join(assets, 'fonts'), urlPrefix: 'assets/fonts/' });

  // ---- scenes
  const ctx = { runDir };
  const sceneData = [];
  let sceneHTML = '', hudCounters = '';
  const total = timeline.scenes.length;
  timeline.scenes.forEach((tsc, idx) => {
    const esc_ = episode.scenes.find((s) => s.id === tsc.id);
    const cues = timeline.cues.filter((c) => c.scene === tsc.id);
    const scene = { ...esc_, cues: esc_.cues || [] };
    const { html, data } = renderStage(scene, ctx);
    const d = round(tsc.end - tsc.start);
    sceneHTML += `<section class="clip scene" id="sc-${tsc.id}" data-start="${t3(tsc.start)}" data-duration="${t3(d)}" data-track-index="1"><div class="inner" id="in-${tsc.id}">` +
      `<div class="headline" id="hl-${tsc.id}"><span>${esc(esc_.headline || '')}</span></div><div class="stage" id="st-${tsc.id}">${html}</div></div></section>\n`;
    hudCounters += `<div class="clip hudsc" id="hsc-${tsc.id}" data-start="${t3(tsc.start)}" data-duration="${t3(d)}" data-track-index="2">${String(idx + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}</div>\n`;
    sceneData.push({ id: tsc.id, type: esc_.visual.type, start: tsc.start, end: tsc.end, headline: esc_.headline, stage: data, cues });
  });

  // ---- captions
  const allLines = [...timeline.scenes.flatMap((s) => s.lines), ...timeline.outro.lines];
  let capHTML = '';
  const capData = [];
  for (const ln of allLines) {
    ln.pages.forEach((pg, k) => {
      const s = ln.start + pg.t0, e = k + 1 < ln.pages.length ? ln.start + ln.pages[k + 1].t0 : ln.end + 0.12;
      const who = ln.who === 'guest' && hasGuest ? cast.guest : cast.host;
      capHTML += `<div class="clip cap ${ln.who}" id="cap-${ln.id}-${k}" data-start="${t3(s)}" data-duration="${t3(e - s)}" data-track-index="5"><div class="who">${esc(who.name)}</div><p>${esc(pg.text).replace(/\*\*(.+?)\*\*/g, '<mark>$1</mark>')}</p></div>\n`;
      capData.push({ id: `cap-${ln.id}-${k}`, s: round(s), e: round(e) });
    });
  }

  // ---- avatars + face tracks
  const linesHost = allLines.filter((l) => l.who === 'host'), linesGuest = allLines.filter((l) => l.who === 'guest');
  const faces = {
    left: { member: sides.host, who: 'host', tracks: faceTracks({ mine: linesHost, theirs: linesGuest, duration: dur, seed: `${series.id}:host` }) },
  };
  if (hasGuest) faces.right = { member: sides.guest, who: 'guest', tracks: faceTracks({ mine: linesGuest, theirs: linesHost, duration: dur, seed: `${series.id}:guest` }) };
  const avatarsHTML = avatarHTML(sides.host, 'left') + (hasGuest ? avatarHTML(sides.guest, 'right') : '');
  const hiddenCSS = Object.values(sides).flatMap((m) => hiddenStateIds(`${m.id}-`)).map((id) => `#${id}`).join(',') + '{opacity:0}';

  // ---- intro / outro cards
  const [t1, t2] = splitTitle(episode.title);
  const longest = Math.max(t1.length, (t2 || '').length);
  const bigPx = Math.max(96, Math.min(214, Math.floor(1560 / Math.max(3, longest))));
  const no = String(episodeNo).padStart(3, '0');
  const tag = label || `No.${no}`;                       // e.g. "No.001", or a date for videos made on request
  const introHTML = `<section class="clip card" id="intro" data-start="0" data-duration="${t3(timeline.intro.end + 0.35)}" data-track-index="8">
    <div class="kicker" id="in-kick"><b>${esc(series.name)}</b>　${esc(tag)}</div>
    <div class="big" id="in-big" data-layout-allow-overlap style="font-size:${bigPx}px;top:${Math.round(H * 0.5 - bigPx * (t2 ? 1.05 : 0.6))}px"><span class="ln" id="in-l1" data-layout-allow-overlap><i class="mk" style="opacity:${t2 ? 0 : 1}"></i>${esc(t1)}</span>${t2 ? `<br><span class="ln" id="in-l2" data-layout-allow-overlap><i class="mk"></i>${esc(t2)}</span>` : ''}</div>
    <div class="bar" id="in-bar" style="top:${Math.round(H * 0.5 + bigPx * (t2 ? 1.25 : 0.55))}px"></div>
    <div class="sub" id="in-sub" style="top:${Math.round(H * 0.5 + bigPx * (t2 ? 1.25 : 0.55)) + 34}px">${esc(episode.subtitle || series.tagline || '')}</div>
  </section>\n`;
  const outroStart = timeline.outro.start;
  const outroHTML = `<section class="clip card outro" id="outro" data-start="${t3(outroStart)}" data-duration="${t3(dur - outroStart)}" data-track-index="8" style="background:transparent" data-layout-allow-overlap>
    <div class="ostage" id="o-stage" style="position:absolute;left:${STAGE.x}px;top:${HEADLINE_Y()}px;width:${STAGE.w}px;height:${STAGE.y + STAGE.h - HEADLINE_Y()}px">
      <div class="kicker" id="o-kick" style="left:6px;top:96px"><b>${esc(series.name)}</b>　${esc(tag)}</div>
      <div class="big" id="o-big" style="left:0;top:190px;font-size:190px"><span><i class="mk"></i>また次回。</span></div>
      <div class="sub" id="o-sub" style="left:6px;top:470px;font-size:44px;color:${COLORS.ink}">${esc(episode.subtitle || '')}</div>
    </div>
    <div class="credits" id="o-credits" style="left:${CAPTION.x}px;right:auto;width:${CAPTION.w}px;bottom:auto;top:${CAPTION.y + 10}px;opacity:0">
      <div>${series.credits.map((c) => `<b>${esc(c)}</b>`).join('　／　')}</div>
      <div>イラスト・BGM・映像：auto_movie（HyperFrames でレンダリング）</div></div>
  </section>\n`;

  // ---- HUD
  const hud = `<div class="hud" id="hud"><div><b>${esc(series.name)}</b><span class="no">${esc(tag)}</span></div><div style="display:flex;align-items:center"><span style="display:inline-block;width:110px"></span><div class="prog" id="prog"><i id="prog-i"></i></div></div></div><div class="rule" id="rule"></div>`;
  const ticks = timeline.scenes.map((s) => `<s style="left:${round(((s.start - timeline.scenes[0].start) / (timeline.outro.linesEnd - timeline.scenes[0].start)) * 100)}%"></s>`).join('');

  // ---- runtime data
  const AM = {
    fps: timeline.fps, duration: dur, intro: timeline.intro, outro: timeline.outro,
    scenes: sceneData,
    lines: allLines.map((l) => ({ id: l.id, who: l.who, start: l.start, end: l.end, emotion: l.emotion })),
    faces: Object.fromEntries(Object.entries(faces).map(([side, f]) => [side, { prefix: `${f.member.id}-`, who: f.who, ...f.tracks }])),
    progress: { from: timeline.scenes[0].start, to: timeline.outro.linesEnd },
    stage: STAGE, captions: capData,
  };

  const html = `<!doctype html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=${W}, height=${H}">
<title>${esc(series.name)} ${esc(tag)} ${esc(episode.title)}</title>
<style>
${fonts.css}
${themeCSS()}
${hiddenCSS}
.hudsc{right:${60 + 340 + 4}px;top:${44 + 4}px;font-size:22px;font-weight:500;letter-spacing:.18em;color:${COLORS.inkSoft};white-space:nowrap;text-align:right;width:160px;line-height:44px}
.tick{}
</style>
<script src="assets/gsap.min.js"></script>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="${W}" data-height="${H}" data-duration="${t3(dur)}">
<div class="paper"></div><div class="grain"></div>
${hud}
${hudCounters}
${sceneHTML}
${avatarsHTML}
${capHTML}
${introHTML}
${outroHTML}
${audioFile ? `<audio id="master" src="assets/master.wav" data-start="0" data-duration="${t3(dur)}" data-track-index="10" data-volume="1"></audio>` : ''}
</div>
<script>window.AM = ${jsonForScript(AM)};document.getElementById('prog').insertAdjacentHTML('beforeend', ${jsonForScript(ticks)});</script>
<script>
${fs.readFileSync(path.join(ROOT, 'lib', 'visual', 'runtime.js'), 'utf8')}
</script>
</body>
</html>
`;
  const indexPath = writeText(path.join(projectDir, 'index.html'), html);
  writeJSON(path.join(projectDir, 'hyperframes.json'), { $schema: 'https://hyperframes.heygen.com/schema/hyperframes.json', registry: 'https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry', paths: { blocks: 'compositions', components: 'compositions/components', assets: 'assets' }, media: { autoProxy: true } });
  writeJSON(path.join(projectDir, 'meta.json'), { id: 'auto-movie', name: episode.title, createdAt: new Date(0).toISOString() });
  writeJSON(path.join(projectDir, 'am-data.json'), AM);
  return { indexPath, data: AM, fonts };
}

function HEADLINE_Y() { return 96; }
