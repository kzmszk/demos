// Timeline compiler: script + measured voice durations → absolute schedule (scenes, lines, caption pages, cues).
// The audio decides the timing; visuals and music follow. Also fits the total to the requested length.
import { round, clamp } from './util.mjs';
import { makePages } from './tts/index.mjs';
import { mouthFromSegs, mouthFromAudio } from './visual/lipsync.mjs';

export const DEFAULT_CFG = {
  fps: 30,
  introSec: 4.4,        // title card + jingle
  sceneLeadIn: 0.5,     // silence at the start of a scene (transition + first draw)
  sceneHold: 0.5,       // after the last line of a scene
  gapSame: 0.2,         // between lines of the same speaker
  gapTurn: 0.34,        // when the speaker changes
  outroLeadIn: 0.45,
  outroTailMin: 3.8,    // credits hold
  outroTailMax: 9,
  captionMaxChars: 38,
  cueAnticipation: 0.1, // a visual lands slightly before the word
  minGapScale: 0.55, maxGapScale: 1.5,
};

/**
 * @param {object} o
 * @param {object} o.episode script JSON
 * @param {Record<string, any>} o.voice records from synthesizeLines (+ anchorTimes)
 * @param {number} o.targetSec requested total length
 * @param {number} [o.speed] global tempo factor applied to all voice (time-stretch); 1 = as synthesized
 */
export function compileTimeline({ episode, voice, targetSec, speed = 1, cfg: over = {} }) {
  const cfg = { ...DEFAULT_CFG, ...over };
  const dur = (id) => voice[id].duration / speed;
  const gapScale = over.gapScale ?? 1;
  const gap = (a, b) => (a.who === b.who ? cfg.gapSame : cfg.gapTurn) * gapScale;

  const scenes = [];
  let t = cfg.introSec;
  for (const sc of episode.scenes) {
    const start = t;
    let cur = start + cfg.sceneLeadIn;
    const lines = [];
    sc.lines.forEach((ln, i) => {
      const v = voice[ln.id];
      const d = dur(ln.id);
      const line = layoutLine(ln, v, cur, d, speed, cfg);
      lines.push(line);
      cur = line.end + (i + 1 < sc.lines.length ? gap(ln, sc.lines[i + 1]) : 0);
    });
    const end = cur + cfg.sceneHold * gapScale;
    scenes.push({ id: sc.id, type: sc.visual?.type, start: round(start), end: round(end), lines });
    t = end;
  }

  // outro: closing lines, then a credit hold that absorbs any slack up to the requested total
  const outro = { start: round(t), lines: [], end: 0 };
  let cur = t + cfg.outroLeadIn;
  const oLines = episode.outro?.lines || [];
  oLines.forEach((ln, i) => {
    const line = layoutLine(ln, voice[ln.id], cur, dur(ln.id), speed, cfg);
    outro.lines.push(line);
    cur = line.end + (i + 1 < oLines.length ? gap(ln, oLines[i + 1]) : 0);
  });
  const naturalEnd = cur + cfg.outroTailMin;
  // land exactly on the requested length (a hair under is fine: the credits hold absorbs it)
  const total = naturalEnd <= targetSec + 0.06 ? targetSec : naturalEnd;
  outro.end = round(total);
  outro.tail = round(total - cur);
  outro.linesEnd = round(cur);

  // cues: resolve "after <text>" anchors to absolute times
  const cues = [];
  for (const sc of episode.scenes) {
    const S = scenes.find((s) => s.id === sc.id);
    for (const cue of sc.cues || []) {
      const line = S.lines.find((l) => l.id === cue.line) || S.lines[0];
      let tt = line.start;
      if (cue.at === 'end') tt = line.end - 0.2;
      else if (cue.after != null && cue.after !== '') {
        const idx = line.text.indexOf(cue.after);
        const rel = idx >= 0 ? line.anchorTime(idx) : 0;
        tt = line.start + rel;
      }
      tt += cue.offset || 0;
      cues.push({ ...cue, scene: sc.id, t: round(clamp(tt - cfg.cueAnticipation, S.start + 0.15, S.end - 0.2)) });
    }
  }
  cues.sort((a, b) => a.t - b.t);

  const speechSec = scenes.reduce((s, sc) => s + sc.lines.reduce((x, l) => x + (l.end - l.start), 0), 0) + outro.lines.reduce((x, l) => x + (l.end - l.start), 0);
  const stats = {
    total: round(total), target: targetSec, natural: round(naturalEnd), speechSec: round(speechSec),
    lines: scenes.reduce((s, sc) => s + sc.lines.length, 0) + outro.lines.length,
    overrun: round(naturalEnd - targetSec),
  };
  // strip functions before serialising
  const clean = (l) => { const { anchorTime, ...rest } = l; return rest; };
  return {
    timeline: {
      fps: cfg.fps, duration: round(total), intro: { start: 0, end: cfg.introSec },
      scenes: scenes.map((s) => ({ ...s, lines: s.lines.map(clean) })),
      outro: { ...outro, lines: outro.lines.map(clean) }, cues,
    },
    stats, cfg,
  };
}

function layoutLine(ln, v, start, d, speed, cfg) {
  const pagesRaw = makePages(v.clauses.map((c) => ({ ...c })), cfg.captionMaxChars);
  const pages = pagesRaw.map((p, i) => {
    const t0 = p.first.t0 / speed;
    const next = pagesRaw[i + 1];
    const t1 = next ? next.first.t0 / speed : d;
    return { text: p.text.trim(), t0: round(t0), t1: round(t1) };
  });
  pages[0].t0 = 0;
  const mouth = v.segs ? mouthFromSegs(v.segs, { fps: cfg.fps, speed }) : (v.mouth || [[0, 1]]);
  const anchorMap = v.anchorTimes || {};
  const line = {
    id: ln.id, who: ln.who, text: ln.text, emotion: ln.emotion || 'normal',
    start: round(start), end: round(start + d), dur: round(d), pages, mouth,
    file: v.file,
    anchorTime(idx) {
      // exact when resolved by the TTS, else proportional to the text
      if (anchorMap[idx] != null) return anchorMap[idx] / speed;
      return (idx / Math.max(1, ln.text.length)) * d * 0.96;
    },
  };
  return line;
}

/** How much faster/slower (factor on speed) would make the natural length equal the target? */
export function speedForTarget({ episode, voice, targetSec, cfg: over = {} }) {
  const at1 = compileTimeline({ episode, voice, targetSec: 0, speed: 1, cfg: over });
  const cfg = at1.cfg;
  const fixed = at1.stats.natural - at1.stats.speechSec; // gaps, lead-ins, intro, tail min – not scaled by speed
  const avail = targetSec - fixed;
  const k = avail > 0 ? at1.stats.speechSec / avail : 9;
  return { k: round(k, 4), natural: at1.stats.natural, speechSec: at1.stats.speechSec, fixed: round(fixed) };
}
