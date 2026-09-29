// Illustration stage: one Opus call per illustrated scene (run a few at a time), validated and saved as SVG.
import path from 'node:path';
import { ROOT, readText, writeText, writeJSON, exists, ensureDir, log, pool } from '../util.mjs';
import { askSVG } from '../llm.mjs';

const ALLOWED = new Set(['#3d3d3d', '#fff176', '#d64545', '#fff', '#ffffff', 'none', 'currentcolor', 'transparent']);

export function elementIds(scene) {
  return (scene.visual.elements || []).map((e) => e.id);
}

/** Problems that would break the animation or the look. */
export function validateSceneSVG(svg, ids) {
  const p = [];
  if (!/<svg[^>]*viewBox="0 0 640 360"/.test(svg)) p.push('viewBox must be "0 0 640 360"');
  if (!/\bid="art"/.test(svg)) p.push('missing <g id="art">');
  for (const id of ids) if (!new RegExp(`\\bid="el-${id}"`).test(svg)) p.push(`missing <g id="el-${id}">`);
  if (!/\bid="el-deco"/.test(svg)) p.push('missing <g id="el-deco">');
  if (/<text\b|<image\b|<script\b|<style\b|<foreignObject\b/.test(svg)) p.push('forbidden element (text/image/script/style/foreignObject)');
  const colors = new Set([...svg.matchAll(/(?:fill|stroke|stop-color)="(#[0-9a-fA-F]{3,8}|[a-z]+)"/g)].map((m) => m[1].toLowerCase()));
  for (const c of colors) if (!ALLOWED.has(c)) p.push(`color outside the palette: ${c}`);
  if (/<g[^>]*id="el-[^"]*"[^>]*transform=/.test(svg)) p.push('el-* groups must not carry a transform');
  if (svg.length > 90000) p.push(`SVG too large (${svg.length} chars); simplify`);
  const washes = (svg.match(/class="wash"/g) || []).length;
  if (washes > 2) p.push('yellow wash (class="wash") should be used in one place only');
  return p;
}

function buildPrompt(scene, episode, styleGuide) {
  const tpl = readText(path.join(ROOT, 'prompts', 'illustration.md'));
  const v = scene.visual;
  const els = (v.elements || []).map((e) => `- id=${e.id}：${e.what}`).join('\n');
  const chars = (episode.characters || []).filter((c) => (v.elements || []).some((e) => e.character === c.id) || (v.brief || '').includes(c.name || c.id));
  const charBlock = chars.length ? `\n■ 登場人物の設定（ほかのシーンでも同じ人物として描く）\n${chars.map((c) => `- ${c.name || c.id}：${c.desc}`).join('\n')}\n` : '';
  return tpl
    .replace('{{BRIEF}}', v.brief)
    .replace('{{ELEMENTS}}', els)
    .replace('{{HERO}}', v.hero ? `el-${v.hero}` : '（要素のうちいちばん伝えたいもの）')
    .replace('{{CHARACTERS}}', charBlock)
    .replace('{{STYLE_GUIDE}}', styleGuide);
}

/** Draw every illustration scene of the episode into <runDir>/illustrations/<sceneId>.svg. */
export async function illustrate({ episode, runDir, concurrency = 3, force = false, model = 'best' }) {
  const styleGuide = readText(path.join(ROOT, 'prompts', 'style-guide.md'));
  const outDir = ensureDir(path.join(runDir, 'illustrations'));
  const scenes = episode.scenes.filter((s) => s.visual?.type === 'illustration');
  log('draw', `${scenes.length} illustration(s), ${concurrency} at a time`);
  const results = await pool(concurrency, scenes, async (sc) => {
    const out = path.join(outDir, `${sc.id}.svg`);
    if (exists(out) && !force) { log('draw', `${sc.id}: exists`); return { id: sc.id, cached: true }; }
    const ids = elementIds(sc);
    const prompt = buildPrompt(sc, episode, styleGuide);
    const r = await askSVG({ prompt, tag: `illust-${sc.id}`, dir: runDir, model, validate: (svg) => validateSceneSVG(svg, ids), repairs: 1 });
    writeText(out, r.svg + '\n');
    writeJSON(path.join(outDir, `${sc.id}.meta.json`), { model: r.model, costUsd: r.costUsd, seconds: r.seconds, attempts: r.attempts, bytes: r.svg.length });
    log('draw', `${sc.id}: ok (${r.svg.length} bytes, $${(r.costUsd ?? 0).toFixed(2)}, ${r.seconds}s)`);
    return { id: sc.id, costUsd: r.costUsd };
  });
  return results;
}
