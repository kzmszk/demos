// Reference material: files, URLs or literal text → one digest for the prompts (and a copy in the run directory).
import path from 'node:path';
import fs from 'node:fs';
import { writeText, log } from '../util.mjs';

const MAX_EACH = 14000, MAX_ALL = 28000;

function htmlToText(html) {
  return html
    .replace(/<(script|style|noscript|svg|nav|footer|header|form)[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<br\s*\/?>|<\/(p|div|li|h[1-6]|tr)>/gi, '\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/[ \t　]+/g, ' ').replace(/\n\s*\n+/g, '\n\n').trim();
}

/** @param {string[]} inputs paths, http(s) URLs or literal text */
export async function collectSources(inputs = [], { runDir } = {}) {
  const parts = [];
  for (const raw of inputs) {
    const item = String(raw).trim();
    if (!item) continue;
    let name, text;
    if (/^https?:\/\//i.test(item)) {
      name = item;
      try {
        const res = await fetch(item, { headers: { 'User-Agent': 'auto-movie/0.1 (+research)' }, signal: AbortSignal.timeout(20000) });
        const body = await res.text();
        text = /html/i.test(res.headers.get('content-type') || '') ? htmlToText(body) : body;
      } catch (e) { log('sources', `could not fetch ${item}: ${e.message}`); continue; }
    } else if (fs.existsSync(item)) {
      name = path.basename(item);
      text = fs.readFileSync(item, 'utf8');
    } else { name = '(inline)'; text = item; }
    parts.push({ name, text: text.length > MAX_EACH ? text.slice(0, MAX_EACH) + '\n…（以下省略）' : text });
  }
  let out = parts.map((p, i) => `【資料${i + 1}：${p.name}】\n${p.text.trim()}`).join('\n\n');
  if (out.length > MAX_ALL) out = out.slice(0, MAX_ALL) + '\n…（以下省略）';
  if (!out) out = '（参考資料は与えられていません。一般に確かな知識だけを使い、数字は控えめに）';
  if (runDir) writeText(path.join(runDir, 'sources.md'), out + '\n');
  return { text: out, files: parts.map((p) => ({ name: p.name, chars: p.text.length })) };
}
