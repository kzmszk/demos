// The script contract between the LLM stages and the renderer, with a validator whose messages are written for the
// model to read (Japanese, concrete) so a failed attempt can be repaired automatically.
import { MOODS } from './audio/composer.mjs';

export const EMOTIONS = ['normal', 'happy', 'surprised', 'thinking', 'sad', 'emphatic'];
export const ICONS = ['calendar', 'book', 'star', 'check', 'bulb', 'clock', 'phone'];
export const IDLES = ['sway', 'float', 'pulse'];
export const SIDES = ['left', 'right', 'top', 'bottom'];

/** Which cue ops each visual (kind) understands. */
export const OPS = {
  illustration: ['draw', 'pop', 'drop', 'slide', 'fade', 'emph', 'callout'],
  'chart:line': ['chart.axes', 'chart.point', 'chart.callout', 'stamp'],
  'chart:review-curve': ['chart.axes', 'chart.line', 'chart.review', 'stamp'],
  'chart:bar': ['chart.axes', 'chart.bar'],
  steps: ['steps.reveal'],
  recap: ['recap.check'],
};
export const visualKey = (v) => (v.type === 'chart' ? `chart:${v.kind}` : v.type);

const isStr = (x, min = 1, max = 1e9) => typeof x === 'string' && x.trim().length >= min && x.length <= max;
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);

/** Speech-unfriendly things that make TTS stumble. Returned as advice, not always as hard errors. */
export function speechIssues(text) {
  const out = [];
  if (/[A-Za-z]{2,}/.test(text)) out.push('英字の単語が含まれています（読み上げが不安定）。カタカナか日本語にしてください');
  if (/[()（）「」『』\[\]{}<>*#_~`]/.test(text)) out.push('括弧・記号が含まれています（読み上げに不要）');
  if (/\d{1,3}(,\d{3})+/.test(text)) out.push('カンマ区切りの数字は避けてください（例：1000）');
  if (/[\n\r\t]/.test(text)) out.push('改行が含まれています');
  return out;
}

/**
 * @param {object} ep the script
 * @param {object} o
 * @param {string[]} o.speakers allowed values of `who`
 * @param {number} o.charBudget target number of spoken characters (all lines), ±tolerance
 * @param {number} [o.tolerance]
 * @param {number} [o.maxIllustrations]
 */
export function validateScript(ep, { speakers = ['host', 'guest'], charBudget, tolerance = 0.12, charRange, maxIllustrations = 5 } = {}) {
  const p = [];
  if (!ep || typeof ep !== 'object') return ['JSONのオブジェクトではありません'];
  if (!isStr(ep.title, 2, 30)) p.push('title は2〜30文字の文字列にしてください');
  if (!isStr(ep.subtitle, 2, 40)) p.push('subtitle は2〜40文字の文字列にしてください');
  if (!Array.isArray(ep.scenes) || ep.scenes.length < 3 || ep.scenes.length > 12) return [...p, 'scenes は3〜12個の配列にしてください'];
  if (!ep.outro || !Array.isArray(ep.outro.lines) || !ep.outro.lines.length || ep.outro.lines.length > 3) p.push('outro.lines は1〜3行の配列にしてください（締めのあいさつ）');

  const lineIds = new Set(), sceneIds = new Set(), lineById = new Map();
  let chars = 0, illustrations = 0;
  const addLine = (ln, where) => {
    if (!isStr(ln?.id, 1, 12) || lineIds.has(ln.id)) { p.push(`${where}: 行の id が空か重複しています (${ln?.id})`); return; }
    lineIds.add(ln.id); lineById.set(ln.id, ln);
    if (!speakers.includes(ln.who)) p.push(`${ln.id}: who は ${speakers.join(' か ')} にしてください`);
    if (!isStr(ln.text, 3, 80)) p.push(`${ln.id}: text は3〜80文字にしてください（長い発言は2行に分ける。目安は1行あたり60字以内）`);
    else {
      chars += ln.text.length;
      for (const m of speechIssues(ln.text)) p.push(`${ln.id}: ${m}`);
      if (!/[。！？!?…」]$/.test(ln.text.trim())) p.push(`${ln.id}: 文末は「。」「！」「？」で終えてください`);
    }
    if (ln.emotion != null && !EMOTIONS.includes(ln.emotion)) p.push(`${ln.id}: emotion は ${EMOTIONS.join('|')} のどれか`);
    if (ln.say != null && !isStr(ln.say, 2, 200)) p.push(`${ln.id}: say（読み仮名の上書き）は文字列にしてください`);
  };

  ep.scenes.forEach((sc, i) => {
    const w = `scene[${i}]`;
    if (!isStr(sc.id, 1, 8) || sceneIds.has(sc.id)) p.push(`${w}: id が空か重複しています`);
    sceneIds.add(sc.id);
    if (!MOODS.includes(sc.mood)) p.push(`${sc.id}: mood は ${MOODS.join('|')} のどれか`);
    if (!isNum(sc.energy) || sc.energy < 0 || sc.energy > 1) p.push(`${sc.id}: energy は 0〜1 の数`);
    if (!isStr(sc.headline, 2, 22)) p.push(`${sc.id}: headline は2〜22文字（画面に大きく出る見出し）`);
    if (!Array.isArray(sc.lines) || sc.lines.length < 2 || sc.lines.length > 12) p.push(`${sc.id}: lines は2〜12行`);
    (sc.lines || []).forEach((ln) => addLine(ln, sc.id));
    const v = sc.visual;
    if (!v || typeof v !== 'object') { p.push(`${sc.id}: visual がありません`); return; }
    const key = visualKey(v);
    if (!OPS[key]) { p.push(`${sc.id}: visual の種類が不正です (${v.type}/${v.kind})。illustration | chart(line|review-curve|bar) | steps | recap`); return; }
    const elIds = new Set();
    if (v.type === 'illustration') {
      illustrations++;
      if (!isStr(v.brief, 10, 400)) p.push(`${sc.id}: visual.brief は10〜400文字（何を描くか）`);
      if (!Array.isArray(v.elements) || v.elements.length < 2 || v.elements.length > 5) p.push(`${sc.id}: visual.elements は2〜5個`);
      (v.elements || []).forEach((e) => {
        if (!/^[a-z][a-z0-9-]{1,18}$/.test(e?.id || '')) p.push(`${sc.id}: element の id は英小文字・数字・ハイフンのみ (${e?.id})`);
        else if (elIds.has(e.id)) p.push(`${sc.id}: element id が重複 (${e.id})`);
        elIds.add(e?.id);
        if (!isStr(e?.what, 6, 200)) p.push(`${sc.id}/${e?.id}: what は6〜200文字（この要素の絵の説明）`);
        if (/^(mio|nono|host|guest)$/i.test(e?.id || '') || /ミオ|ノノ/.test(`${e?.what || ''}${v.brief || ''}`)) p.push(`${sc.id}: 出演者（ミオ・ノノ）は画面の両脇に常にいるので、挿絵には描かないでください。別の人物・モノ・図で表してください (${e?.id})`);
        if (e?.idle != null && !IDLES.includes(e.idle)) p.push(`${sc.id}/${e.id}: idle は ${IDLES.join('|')} か null`);
      });
      if (!v.hero || !elIds.has(v.hero)) p.push(`${sc.id}: visual.hero は elements のどれかの id`);
    } else if (v.type === 'chart' && v.kind === 'line') {
      if (!Array.isArray(v.points) || v.points.length < 3 || v.points.length > 6) p.push(`${sc.id}: points は3〜6個`);
      (v.points || []).forEach((pt, k) => { if (!isStr(pt?.x, 1, 8) || !isNum(pt?.y)) p.push(`${sc.id}: points[${k}] は {x:"ラベル(8字以内)", y:数値}`); });
      if (!isNum(v.yMax)) p.push(`${sc.id}: yMax（縦軸の最大値）が必要`);
    } else if (v.type === 'chart' && v.kind === 'bar') {
      if (!Array.isArray(v.bars) || v.bars.length < 2 || v.bars.length > 4) p.push(`${sc.id}: bars は2〜4個`);
      (v.bars || []).forEach((b, k) => { if (!isStr(b?.label, 1, 12) || !isNum(b?.value)) p.push(`${sc.id}: bars[${k}] は {label(12字以内), value}`); });
      if (!isNum(v.yMax)) p.push(`${sc.id}: yMax が必要`);
    } else if (v.type === 'chart' && v.kind === 'review-curve') {
      if (!Array.isArray(v.reviews) || v.reviews.length < 1 || v.reviews.length > 4 || v.reviews.some((r) => !isNum(r))) p.push(`${sc.id}: reviews は復習する日（数値）の配列 1〜4個`);
      else if (v.reviews.some((r, k) => r <= 0 || r >= (v.days || 40) || (k && r <= v.reviews[k - 1]))) p.push(`${sc.id}: reviews は昇順で、0より大きく days（既定40）より小さい日数にしてください`);
    } else if (v.type === 'steps') {
      if (!Array.isArray(v.items) || v.items.length < 2 || v.items.length > 4) p.push(`${sc.id}: steps.items は2〜4個`);
      (v.items || []).forEach((it, k) => {
        if (!isStr(it?.label, 1, 6)) p.push(`${sc.id}: items[${k}].label は6字以内`);
        if (!isStr(it?.sub, 2, 30)) p.push(`${sc.id}: items[${k}].sub は30字以内の説明`);
        if (it?.icon != null && !ICONS.includes(it.icon)) p.push(`${sc.id}: items[${k}].icon は ${ICONS.join('|')}`);
      });
    } else if (v.type === 'recap') {
      if (!Array.isArray(v.items) || v.items.length < 2 || v.items.length > 4) p.push(`${sc.id}: recap.items は2〜4個`);
      (v.items || []).forEach((it, k) => { if (!isStr(it?.text, 2, 20)) p.push(`${sc.id}: items[${k}].text は20字以内`); });
    }

    // cues
    const allowed = OPS[key];
    const need = new Set();
    if (v.type === 'illustration') (v.elements || []).forEach((e) => need.add(`el:${e.id}`));
    if (key === 'chart:line') (v.points || []).forEach((_, k) => need.add(`pt:${k}`));
    if (key === 'chart:bar') (v.bars || []).forEach((_, k) => need.add(`bar:${k}`));
    if (key === 'chart:review-curve') (v.reviews || []).forEach((_, k) => need.add(`rv:${k}`));
    if (v.type === 'steps' || v.type === 'recap') (v.items || []).forEach((_, k) => need.add(`it:${k}`));
    for (const cue of sc.cues || []) {
      const cw = `${sc.id} cue(${cue.op})`;
      if (!allowed.includes(cue.op)) { p.push(`${cw}: op が不正。この visual で使えるのは ${allowed.join(', ')}`); continue; }
      const ln = lineById.get(cue.line);
      if (!ln || !(sc.lines || []).includes(ln)) { p.push(`${cw}: line "${cue.line}" はこのシーンの行の id ではありません`); continue; }
      if (cue.at != null && !['start', 'end'].includes(cue.at)) p.push(`${cw}: at は start か end`);
      if (cue.after != null) {
        if (!isStr(cue.after, 1, 30) || !ln.text.includes(cue.after)) p.push(`${cw}: after "${cue.after}" が ${ln.id} の text に含まれていません（text のとおりに一部を抜き出す）`);
      } else if (cue.at == null) p.push(`${cw}: at か after のどちらかが必要`);
      if (v.type === 'illustration' && ['draw', 'pop', 'drop', 'slide', 'fade', 'emph', 'callout'].includes(cue.op)) {
        if (!elIds.has(cue.target)) p.push(`${cw}: target "${cue.target}" は elements の id ではありません`);
        else if (cue.op !== 'emph' && cue.op !== 'callout') need.delete(`el:${cue.target}`);
        if (cue.op === 'callout') {
          if (!isStr(cue.text, 1, 14)) p.push(`${cw}: callout.text は14字以内`);
          if (cue.side != null && !SIDES.includes(cue.side)) p.push(`${cw}: side は ${SIDES.join('|')}`);
        }
      }
      if (cue.op === 'chart.point') { if (!Number.isInteger(cue.index) || cue.index < 0 || cue.index >= (v.points || []).length) p.push(`${cw}: index が範囲外`); else need.delete(`pt:${cue.index}`); }
      if (cue.op === 'chart.callout') { if (!Number.isInteger(cue.index) || cue.index < 0 || cue.index >= (v.points || []).length) p.push(`${cw}: index が範囲外`); if (!isStr(cue.text, 1, 14)) p.push(`${cw}: text は14字以内`); }
      if (cue.op === 'chart.bar') { if (!Number.isInteger(cue.index) || cue.index < 0 || cue.index >= (v.bars || []).length) p.push(`${cw}: index が範囲外`); else need.delete(`bar:${cue.index}`); }
      if (cue.op === 'chart.review') { if (!Number.isInteger(cue.index) || cue.index < 0 || cue.index >= (v.reviews || []).length) p.push(`${cw}: index が範囲外`); else need.delete(`rv:${cue.index}`); }
      if (cue.op === 'steps.reveal' || cue.op === 'recap.check') { if (!Number.isInteger(cue.index) || cue.index < 0 || cue.index >= (v.items || []).length) p.push(`${cw}: index が範囲外`); else need.delete(`it:${cue.index}`); }
      if (cue.op === 'stamp' && !isStr(cue.text, 1, 8)) p.push(`${cw}: stamp.text は8字以内`);
    }
    // the picture must start to say something quickly: the first real reveal lands within the first two lines
    const firstReveal = (sc.cues || []).filter((c) => !['chart.axes', 'emph'].includes(c.op)).map((c) => (sc.lines || []).findIndex((l) => l.id === c.line)).filter((i) => i >= 0);
    if (firstReveal.length && Math.min(...firstReveal) > 1) p.push(`${sc.id}: 最初の要素・点・項目が出るのが遅すぎます（${Math.min(...firstReveal) + 1}行目）。画面が長く空のままになるので、最初の2行のうちに最初の cue（chart.point / chart.bar / steps.reveal / draw など）を置いてください。説明の順番を入れ替えて構いません`);
    if (need.size) p.push(`${sc.id}: 次の項目に対応する cue がありません → ${[...need].join(', ')}（すべての要素・点・項目を、読み上げに合わせて順に出すこと）`);
  });
  (ep.outro?.lines || []).forEach((ln) => addLine(ln, 'outro'));

  if (illustrations > maxIllustrations) p.push(`illustration のシーンが多すぎます（${illustrations}個。${maxIllustrations}個以内）`);
  if (charBudget) {
    const lo = charRange ? charRange[0] : Math.round(charBudget * (1 - tolerance)), hi = charRange ? charRange[1] : Math.round(charBudget * (1 + tolerance));
    if (chars < lo) p.push(`セリフの総文字数が少なすぎます（現在${chars}字。${charBudget}字前後、最低${lo}字。あと約${charBudget - chars}字足してください）`);
    if (chars > hi) p.push(`セリフの総文字数が多すぎます（現在${chars}字。${charBudget}字前後、最大${hi}字。約${chars - charBudget}字減らしてください）`);
  }
  return p;
}

export const countChars = (ep) => [...ep.scenes.flatMap((s) => s.lines), ...(ep.outro?.lines || [])].reduce((s, l) => s + l.text.length, 0);

/** Fill in harmless defaults so the renderer never trips over optional fields. */
export function normalizeScript(ep) {
  const out = JSON.parse(JSON.stringify(ep));
  for (const sc of out.scenes) {
    sc.cues = sc.cues || [];
    sc.energy = Math.min(1, Math.max(0, sc.energy ?? 0.45));
    for (const ln of sc.lines) { ln.text = ln.text.trim(); ln.emotion = ln.emotion || 'normal'; }
    if (sc.visual?.type === 'illustration') for (const e of sc.visual.elements) e.idle = e.idle || null;
    if (sc.visual?.type === 'steps') for (const it of sc.visual.items) it.icon = it.icon || 'star';
  }
  for (const ln of out.outro?.lines || []) { ln.text = ln.text.trim(); ln.emotion = ln.emotion || 'normal'; }
  return out;
}
