// Planning stage: decide the style (or follow the requested one), choose/confirm the topic, pick the facts and lay out the scenes.
import path from 'node:path';
import { ROOT, readText, writeJSON, log } from '../util.mjs';
import { askJSON } from '../llm.mjs';
import { MOODS } from '../audio/composer.mjs';
import { loadStyles } from '../styles.mjs';

export const PLAN_VISUALS = ['illustration', 'chart-line', 'chart-bar', 'chart-review', 'steps', 'recap'];
export const INTRO_SEC = 4.4, OUTRO_SEC = 8.2;

export function validatePlan(plan, { styles, forcedStyle, bodySec }) {
  const p = [];
  if (!plan || typeof plan !== 'object') return ['JSONのオブジェクトではありません'];
  if (!styles[plan.style]) p.push(`style は ${Object.keys(styles).join(' | ')} のどれか`);
  if (forcedStyle && plan.style !== forcedStyle) p.push(`style は指定どおり "${forcedStyle}" にしてください`);
  if (typeof plan.title !== 'string' || plan.title.length < 2 || plan.title.length > 18) p.push('title は2〜18文字');
  if (typeof plan.subtitle !== 'string' || plan.subtitle.length < 2 || plan.subtitle.length > 36) p.push('subtitle は2〜36文字');
  if (!Array.isArray(plan.facts) || plan.facts.length > 8) p.push('facts は最大8個の配列');
  (plan.facts || []).forEach((f, i) => { if (!f?.id || typeof f.text !== 'string') p.push(`facts[${i}] は {id,text,source,confidence}`); });
  if (!Array.isArray(plan.scenes) || plan.scenes.length < 5 || plan.scenes.length > 10) return [...p, 'scenes は5〜10個'];
  let sum = 0, ill = 0;
  plan.scenes.forEach((s, i) => {
    if (s.id !== `s${i + 1}`) p.push(`scenes[${i}].id は "s${i + 1}"`);
    if (!PLAN_VISUALS.includes(s.visual)) p.push(`${s.id}: visual は ${PLAN_VISUALS.join(' | ')}`);
    if (s.visual === 'illustration') ill++;
    if (typeof s.seconds !== 'number' || s.seconds < 8 || s.seconds > 45) p.push(`${s.id}: seconds は8〜45`);
    sum += Number(s.seconds) || 0;
    if (!MOODS.includes(s.mood)) p.push(`${s.id}: mood は ${MOODS.join('|')}`);
    if (typeof s.energy !== 'number' || s.energy < 0 || s.energy > 1) p.push(`${s.id}: energy は 0〜1`);
    if (typeof s.headline !== 'string' || s.headline.length < 2 || s.headline.length > 22) p.push(`${s.id}: headline は2〜22文字`);
    if (i > 1 && plan.scenes[i - 1].visual === s.visual && plan.scenes[i - 2].visual === s.visual) p.push(`${s.id}: 同じ種類の画面が3つ続いています`);
  });
  if (ill > 4) p.push(`illustration が多すぎます（${ill}個。4個以内）`);
  if (plan.scenes.at(-1).visual !== 'recap') p.push('最後のシーンは recap にしてください');
  if (Math.abs(sum - bodySec) > bodySec * 0.08) p.push(`seconds の合計が ${sum} 秒です。本編 ${bodySec} 秒の±8%（${Math.round(bodySec * 0.92)}〜${Math.round(bodySec * 1.08)}）に収めてください`);
  return p;
}

export async function makePlan({ theme, lengthSec, styleId, series, sourcesText, runDir }) {
  const styles = loadStyles();
  const bodySec = Math.round(lengthSec - INTRO_SEC - OUTRO_SEC);
  const forced = styleId && styleId !== 'auto' ? styleId : null;
  if (forced && !styles[forced]) throw new Error(`unknown style "${forced}" (have: ${Object.keys(styles).join(', ')})`);
  const styleList = Object.values(styles).map((s) => `- ${s.id}（${s.name}）：${s.summary} 向いている題材：${s.bestFor}`).join('\n');
  const cast = Object.values(series.cast).map((c) => `${c.name}（${c.role}）`).join('、');
  const prompt = readText(path.join(ROOT, 'prompts', 'plan.md'))
    .replace('{{SERIES}}', series.name).replace('{{TAGLINE}}', series.tagline)
    .replace('{{THEME}}', theme).replace(/\{\{LENGTH_SEC\}\}/g, String(lengthSec)).replace(/\{\{BODY_SEC\}\}/g, String(bodySec))
    .replace('{{CAST}}', cast).replace('{{STYLES}}', styleList)
    .replace('{{STYLE_INSTRUCTION}}', forced ? `※ このスタイルは依頼者が「${forced}」に指定しています。style には必ず "${forced}" を入れてください。` : '※ スタイルは指定されていません。あなたが決めてください。')
    .replace('{{SOURCES}}', sourcesText);
  log('plan', forced ? `style fixed: ${forced}` : 'style: auto (the model decides)');
  const r = await askJSON({ prompt, tag: 'plan', dir: runDir, model: 'best', validate: (o) => validatePlan(o, { styles, forcedStyle: forced, bodySec }), repairs: 2 });
  writeJSON(path.join(runDir, 'plan.json'), r.data);
  log('plan', `style=${r.data.style} — ${r.data.styleReason || ''}`);
  return r.data;
}
