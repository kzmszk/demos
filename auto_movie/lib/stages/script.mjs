// Script stage: dialogue + on-screen direction as JSON, validated against the schema and repaired by the model if needed.
import path from 'node:path';
import { ROOT, readText, writeJSON, log } from '../util.mjs';
import { askJSON } from '../llm.mjs';
import { validateScript, normalizeScript, countChars, visualKey } from '../schema.mjs';
import { castFor } from '../styles.mjs';

const CPS = 6.65;              // spoken characters per second (VOICEVOX at the series' speed, pauses excluded)
const LINE_AVG = 21;           // average characters per line (LLM scripts use short lines → more pauses)
const FIXED_SEC = 4.4 + 3.8;   // intro + credits hold

/** How many spoken characters make the video exactly `lengthSec` long with `scenes` scenes. */
export function charBudget(lengthSec, scenes) {
  const c = (lengthSec - FIXED_SEC - 1.0 * scenes) / (1 / CPS + 0.3 / LINE_AVG);
  return Math.round(c / 10) * 10;
}

const PLAN_TO_VISUAL = { illustration: 'illustration', 'chart-line': 'chart:line', 'chart-bar': 'chart:bar', 'chart-review': 'chart:review-curve', steps: 'steps', recap: 'recap' };

function crossCheck(ep, plan) {
  const p = [];
  if (ep.scenes.length !== plan.scenes.length) p.push(`シーン数が企画（${plan.scenes.length}個）と違います（${ep.scenes.length}個）`);
  plan.scenes.forEach((ps, i) => {
    const s = ep.scenes[i];
    if (!s) return;
    if (s.id !== ps.id) p.push(`scenes[${i}].id は企画どおり "${ps.id}" にしてください`);
    if (s.visual && visualKey(s.visual) !== PLAN_TO_VISUAL[ps.visual]) p.push(`${ps.id}: visual は企画どおり ${ps.visual} にしてください`);
  });
  return p;
}

function castBlock(cast) {
  return Object.entries(cast).map(([role, c]) => `- ${role}（who に書く値）＝ ${c.name}（${c.role}）\n  口調・性格：${c.speech}`).join('\n');
}

export async function makeScript({ plan, series, style, sourcesText, lengthSec, runDir, maxIllustrations = 4 }) {
  const cast = castFor(series, style);
  const budget = charBudget(lengthSec, plan.scenes.length);
  const lo = Math.round(budget * 0.88), hi = Math.round(budget * 1.04); // long scripts need speeding up (unnatural); short ones only stretch the credits
  const prompt = readText(path.join(ROOT, 'prompts', 'script.md'))
    .replace('{{PLAN}}', JSON.stringify(plan, null, 1))
    .replace('{{SOURCES}}', sourcesText)
    .replace('{{CAST}}', castBlock(cast))
    .replace('{{STYLE_NAME}}', style.name).replace('{{STYLE_GUIDE}}', style.scriptGuide)
    .replace(/\{\{CHAR_BUDGET\}\}/g, String(budget)).replace('{{CHAR_LO}}', String(lo)).replace('{{CHAR_HI}}', String(hi))
    .replace(/\{\{LENGTH_SEC\}\}/g, String(lengthSec))
    .replace('{{TITLE}}', plan.title).replace('{{SUBTITLE}}', plan.subtitle)
    .replace('{{WHO}}', style.speakers.join(' / '));
  log('script', `target ${budget} chars (${lo}–${hi}) for ${lengthSec}s, ${plan.scenes.length} scenes`);
  const validate = (o) => [...validateScript(o, { speakers: style.speakers, charBudget: budget, charRange: [lo, hi], maxIllustrations }), ...crossCheck(o, plan)];
  const r = await askJSON({ prompt, tag: 'script', dir: runDir, model: 'best', validate, repairs: 3 });
  const ep = normalizeScript(r.data);
  if (!ep.characters?.length) ep.characters = plan.characters || [];
  ep.style = plan.style;
  writeJSON(path.join(runDir, 'script.json'), ep);
  log('script', `${ep.scenes.length} scenes, ${countChars(ep)} chars (budget ${budget})`);
  return { episode: ep, budget };
}

/** Ask the model to lengthen/shorten an existing script by about `deltaChars` while keeping its structure and cues. */
export async function reviseLength({ episode, plan, series, style, direction, deltaChars, sourcesText, lengthSec, runDir, round = 1 }) {
  const budget = charBudget(lengthSec, episode.scenes.length);
  const prompt = `次の動画台本（JSON）の長さを調整してください。セリフの総文字数は今 ${countChars(episode)} 字ですが、${budget} 字前後（${Math.round(budget * 0.92)}〜${Math.round(budget * 1.02)}字）にしたいのです。` +
    `${direction === 'shorter' ? `約${deltaChars}字減らして` : `約${deltaChars}字ぶん、内容を足して`}ください。\n` +
    `- シーン構成・visual・要素・cues の意味は変えない（セリフを変えたら、cue の after は新しい text に含まれる語句に直す）。\n` +
    `- ${direction === 'shorter' ? '重複した説明や言い回しを削る。数字や要点は残す' : '聞き役の質問、たとえ話、具体例を足す。新しい事実は参考資料にあるものだけ'}。\n` +
    `- 口調と文体（出演者の口調）はそのまま。行の id は変えず、足す場合は新しい id を付ける。\n\n■ 参考資料\n${sourcesText}\n\n■ 現在の台本\n${JSON.stringify(episode)}\n\nJSONだけを出力してください。`;
  const validate = (o) => [...validateScript(o, { speakers: style.speakers, charBudget: budget, charRange: [Math.round(budget * 0.92), Math.round(budget * 1.02)], maxIllustrations: 4 }), ...crossCheck(o, plan)];
  const r = await askJSON({ prompt, tag: `revise-${round}`, dir: runDir, model: 'best', validate, repairs: 2 });
  const ep = normalizeScript(r.data);
  ep.characters = episode.characters; ep.style = episode.style;
  writeJSON(path.join(runDir, 'script.json'), ep);
  log('script', `revised (${direction}): ${countChars(ep)} chars`);
  return ep;
}
