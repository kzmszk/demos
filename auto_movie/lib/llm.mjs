// LLM access through headless Claude Code (`claude -p`): no API key handling here, it uses the user's login.
// Every call is cached on disk by (prompt, system, model) so a re-run of the pipeline never pays twice.
import path from 'node:path';
import os from 'node:os';
import fs from 'node:fs';
import { run, sha1, ensureDir, exists, readJSON, writeJSON, writeText, log } from './util.mjs';

export const MODELS = {
  best: process.env.AUTO_MOVIE_MODEL_BEST || 'claude-opus-5-5',
  fast: process.env.AUTO_MOVIE_MODEL_FAST || 'claude-sonnet-5-5',
};

const CHILD_ENV_KEYS = ['HOME', 'PATH', 'LANG', 'LC_ALL', 'USER', 'TMPDIR', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'CLAUDE_CONFIG_DIR'];
const DEFAULT_SYSTEM =
  'You are a precise text-generation engine inside an automated video production pipeline. ' +
  'Follow the user instructions exactly, output only what is asked for (no preamble, no commentary), ' +
  'and never use tools.';

let mockHandler = null;
/** Tests / offline runs can replace the model with a function ({tag,prompt}) => text. */
export const setMockLLM = (fn) => { mockHandler = fn; };

/**
 * Ask Claude once. Returns { text, costUsd, seconds, model, cached }.
 * @param {object} o
 * @param {string} o.prompt
 * @param {string} [o.system]
 * @param {string} [o.model]   'best' | 'fast' | explicit model id
 * @param {string} o.tag       cache/log name, unique inside `dir`
 * @param {string} o.dir       run directory (logs go to <dir>/llm)
 */
export async function ask({ prompt, system = DEFAULT_SYSTEM, model = 'best', tag, dir, effort, timeoutMs = 30 * 60 * 1000, cache = true }) {
  const modelId = MODELS[model] || model;
  const llmDir = ensureDir(path.join(dir, 'llm'));
  const key = sha1([prompt, system, modelId]);
  const cacheFile = path.join(llmDir, `${tag}.json`);
  if (cache && exists(cacheFile)) {
    const c = readJSON(cacheFile);
    if (c.key === key) { log('llm', `${tag}: cached (${modelId})`); return { ...c, cached: true }; }
  }
  writeText(path.join(llmDir, `${tag}.prompt.md`), `<!-- model: ${modelId} -->\n<!-- system: ${system} -->\n\n${prompt}\n`);

  const t0 = Date.now();
  let res;
  if (mockHandler) {
    const text = await mockHandler({ tag, prompt, system, model: modelId });
    res = { text, costUsd: 0, seconds: 0, model: 'mock', key, cached: false };
  } else {
    const args = ['-p', '--model', modelId, '--tools', '', '--no-session-persistence', '--output-format', 'json', '--system-prompt', system];
    if (effort) args.push('--effort', effort);
    const env = Object.fromEntries(CHILD_ENV_KEYS.filter((k) => process.env[k] != null).map((k) => [k, process.env[k]]));
    const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'automovie-llm-'));
    log('llm', `${tag}: asking ${modelId} (${prompt.length} chars)…`);
    let r;
    try {
      r = await run('claude', args, { input: prompt, cwd, env, timeoutMs });
    } finally {
      fs.rmSync(cwd, { recursive: true, force: true });
    }
    let data;
    try { data = JSON.parse(r.stdout); } catch { throw new Error(`claude -p returned non-JSON (exit ${r.code}): ${(r.stdout + r.stderr).slice(0, 500)}`); }
    if (data.is_error || r.code !== 0) throw new Error(`claude -p failed for ${tag}: ${String(data.result ?? r.stderr).slice(0, 500)}`);
    res = {
      text: data.result ?? '',
      costUsd: data.total_cost_usd ?? null,
      seconds: Math.round((Date.now() - t0) / 1000),
      model: modelId,
      usage: data.usage,
      key,
      cached: false,
    };
    log('llm', `${tag}: done in ${res.seconds}s, $${(res.costUsd ?? 0).toFixed(2)}, ${res.text.length} chars`);
  }
  writeJSON(cacheFile, { key, text: res.text, costUsd: res.costUsd, seconds: res.seconds, model: res.model, usage: res.usage });
  return res;
}

// ---- output extraction -----------------------------------------------------------------------
export function extractJSON(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const candidates = [];
  if (fenced) candidates.push(fenced[1]);
  const a = text.indexOf('{'), b = text.lastIndexOf('}');
  if (a >= 0 && b > a) candidates.push(text.slice(a, b + 1));
  candidates.push(text);
  let lastErr;
  for (const c of candidates) {
    try { return JSON.parse(c.trim()); } catch (e) { lastErr = e; }
  }
  throw new Error(`no valid JSON in model output (${lastErr?.message}); head: ${text.slice(0, 200)}`);
}

export function extractSVG(text) {
  const m = text.match(/<svg\b[\s\S]*<\/svg>/);
  if (!m) throw new Error(`no <svg> in model output; head: ${text.slice(0, 200)}`);
  return m[0];
}

/** Ask for one SVG; `validate(svg) -> string[]` problems are sent back for repair like askJSON. */
export async function askSVG({ validate = () => [], repairs = 1, ...opts }) {
  let prompt = opts.prompt;
  for (let attempt = 0; attempt <= repairs; attempt++) {
    const tag = attempt === 0 ? opts.tag : `${opts.tag}.fix${attempt}`;
    const res = await ask({ ...opts, prompt, tag });
    let svg, problems;
    try {
      svg = extractSVG(res.text);
      problems = validate(svg);
    } catch (e) {
      problems = [String(e.message)];
    }
    if (!problems.length) return { svg, ...res, attempts: attempt + 1 };
    log('llm', `${opts.tag}: ${problems.length} problem(s) → repair round ${attempt + 1}: ${problems.slice(0, 4).join(' / ')}`);
    prompt =
      `${opts.prompt}\n\n----\n直前のあなたのSVGには次の問題がありました。すべて直した完全なSVGを、最初から1つだけ出力してください（説明文は不要）。\n` +
      problems.map((p) => `- ${p}`).join('\n') +
      `\n\n直前のSVG:\n${res.text.slice(0, 80000)}`;
  }
  throw new Error(`${opts.tag}: SVG still invalid after ${repairs} repair(s)`);
}

/**
 * Ask for JSON, validate with `validate(obj) -> string[] (problems)`, and if it fails send the problems back
 * (up to `repairs` times) so the model fixes its own output.
 */
export async function askJSON({ validate = () => [], repairs = 2, ...opts }) {
  let prompt = opts.prompt;
  let last;
  for (let attempt = 0; attempt <= repairs; attempt++) {
    const tag = attempt === 0 ? opts.tag : `${opts.tag}.fix${attempt}`;
    const res = await ask({ ...opts, prompt, tag });
    last = res;
    let obj, problems;
    try {
      obj = extractJSON(res.text);
      problems = validate(obj);
    } catch (e) {
      problems = [String(e.message)];
    }
    if (!problems.length) return { data: obj, ...res, attempts: attempt + 1 };
    log('llm', `${opts.tag}: ${problems.length} problem(s) → repair round ${attempt + 1}: ${problems.slice(0, 3).join(' / ')}`);
    prompt =
      `${opts.prompt}\n\n----\n直前のあなたの出力には次の問題がありました。すべて直した完全なJSONを、もう一度最初から出力してください（説明文は不要）。\n` +
      problems.map((p) => `- ${p}`).join('\n') +
      `\n\n直前の出力:\n${res.text.slice(0, 60000)}`;
  }
  throw new Error(`${opts.tag}: model output still invalid after ${repairs} repairs; last problems above. Raw saved in ${opts.dir}/llm`);
}
