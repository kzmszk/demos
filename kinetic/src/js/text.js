/* Kinetic Manifesto — text: font stacks, script detection, Japanese phrase breaking,
   typing markup, and (browser only) glyph-run measurement and line fitting.
   Pure-string helpers run in Node too (build-time validation). */
(function (root) {
  'use strict';
  const K = root.K;
  const T = (K.text = {});

  /* ---------- font stacks (system fonts only) ---------- */
  const LAT =
    '"HelveticaNeue-CondensedBlack", "Helvetica Neue Condensed Black", "Avenir Next Condensed", ' +
    '"Roboto Condensed", "sans-serif-condensed", "Arial Narrow", "Nimbus Sans Narrow", "Liberation Sans Narrow", ' +
    '"Bahnschrift Condensed", Impact, "DejaVu Sans Condensed"';
  const JA =
    '"Hiragino Sans", "Hiragino Kaku Gothic StdN", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", ' +
    '"Noto Sans JP", "Source Han Sans JP", "BIZ UDPGothic", "Yu Gothic", YuGothic, Meiryo';
  K.FONTS = {
    latStack: LAT,
    jaStack: JA,
    mono:
      'ui-monospace, "SFMono-Regular", "SF Mono", Menlo, Consolas, "Roboto Mono", "DejaVu Sans Mono", ' +
      '"Liberation Mono", "Noto Sans Mono CJK JP", monospace',
    ui: 'system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans CJK JP", "Yu Gothic UI", Meiryo, sans-serif',
    /* strings with no Japanese: condensed grotesque */
    lat: { cls: 'k-f-lat', family: `${LAT}, ${JA}, sans-serif`, weight: 900, stretch: 'condensed', lh: 0.9, track: -0.005 },
    /* strings with Japanese: heavy gothic first, its own Latin inside mixed lines */
    ja: { cls: 'k-f-ja', family: `${JA}, ${LAT}, sans-serif`, weight: 800, stretch: 'normal', lh: 1.1, track: 0 },
  };

  /* ---------- scripts ---------- */
  const RE_JA = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}　-〿！-｠]/u;
  const RE_HIRA = /^[\p{Script=Hiragana}ー]+$/u;
  /* may not start a line (closing brackets, punctuation, small kana, prolonged sound mark, iteration marks) */
  const RE_NO_START = /^[」』）)\]］｝}〉》】〕”’、。，．,.!！?？：:；;・…‥ー〜～ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ々ゝゞヽヾ]/u;
  /* may not end a line */
  const RE_NO_END = /[「『（(\[［｛{〈《【〔“‘]$/u;
  const RE_PUNCT_END = /[、。，．,.!！?？]$/u;
  /* hiragana words that attach to the previous word even when longer than three kana */
  const RE_AUX = /^(ではない|ではなく|だった|でした|ません|ましょう|なければ|ならない|られる|させる|ながら|ければ|だろう|でしょう|かもしれない|のです|のだ|ている|ていく|てくる|ていた)$/u;

  T.hasJa = (s) => RE_JA.test(s || '');

  let segG = null, segW = null;
  const Seg = typeof Intl !== 'undefined' && Intl.Segmenter;
  T.graphemes = function (s) {
    s = String(s || '');
    if (Seg) {
      segG = segG || new Intl.Segmenter(undefined, { granularity: 'grapheme' });
      return Array.from(segG.segment(s), (x) => x.segment);
    }
    return Array.from(s);
  };
  /* visible characters (spaces not counted) */
  T.count = (s) => T.graphemes(String(s || '').replace(/\s+/g, '')).length;

  /* fallback word split when Intl.Segmenter is missing: runs of the same script class */
  function classOf(ch) {
    if (/\s/.test(ch)) return 's';
    if (/\p{Script=Han}|[々〆ヶ]/u.test(ch)) return 'h';
    if (/\p{Script=Hiragana}/u.test(ch)) return 'r';
    if (/\p{Script=Katakana}|ー/u.test(ch)) return 'k';
    if (/[\p{L}\p{N}]/u.test(ch)) return 'l';
    return 'p';
  }
  function fallbackWords(s) {
    const out = [];
    let cur = '', cls = '';
    for (const ch of T.graphemes(s)) {
      const c = classOf(ch);
      if (cur && (c !== cls || c === 'p')) {
        out.push(cur);
        cur = '';
      }
      cur += ch;
      cls = c;
    }
    if (cur) out.push(cur);
    return out;
  }

  /* Split a statement into unbreakable phrases.
     Latin: words. Japanese: word segments merged into bunsetsu-like units. */
  T.phrases = function (s) {
    s = String(s || '').replace(/\s*\n\s*/g, ' ').trim();
    if (!s) return [];
    if (!T.hasJa(s)) return s.split(/\s+/);
    let words;
    if (Seg) {
      segW = segW || new Intl.Segmenter('ja', { granularity: 'word' });
      words = Array.from(segW.segment(s), (x) => x.segment);
    } else {
      words = fallbackWords(s);
    }
    const out = [];
    for (const w of words) {
      if (!out.length) {
        out.push(w);
        continue;
      }
      const prev = out[out.length - 1];
      let attach;
      if (/^\s+$/.test(w)) attach = true;
      else if (RE_NO_START.test(w)) attach = true;
      else if (RE_NO_END.test(prev)) attach = true;
      else if (RE_PUNCT_END.test(prev)) attach = false;
      else if (RE_HIRA.test(w) && (T.graphemes(w).length <= 3 || RE_AUX.test(w))) attach = true;
      else attach = false;
      if (attach) out[out.length - 1] = prev + w;
      else out.push(w);
    }
    return out.map((p) => p.trim()).filter(Boolean);
  };
  /* Like phrases(), but lossless: the chunks concatenate back to s exactly, with runs of
     whitespace as their own chunks. Used to keep phrases unbroken in wrapping text. */
  T.chunks = function (s) {
    s = String(s || '');
    const out = [];
    for (const part of s.split(/(\s+)/)) {
      if (!part) continue;
      if (/^\s+$/.test(part) || !T.hasJa(part)) out.push(part);
      else {
        let rest = part;
        for (const p of T.phrases(part)) {
          const at = rest.indexOf(p);
          if (at > 0) out.push(rest.slice(0, at));
          out.push(p);
          rest = rest.slice(at + p.length);
        }
        if (rest) out.push(rest);
      }
    }
    return out;
  };
  T.joiner = (s) => (T.hasJa(s) ? '' : ' ');
  T.explicitLines = (s) =>
    String(s || '').includes('\n') ? String(s).split('\n').map((l) => l.trim()).filter(Boolean) : null;

  /* ---------- typing markup: ~~mistake~~ and {漢字|かな} ---------- */
  T.parseTyping = function (src) {
    src = String(src || '');
    const tokens = [];
    let mis = false, i = 0, error = null, mistakes = 0;
    const pushText = (ch) => {
      const last = tokens[tokens.length - 1];
      if (last && last.k === 'text' && last.mis === mis) last.s += ch;
      else tokens.push({ k: 'text', s: ch, mis });
    };
    while (i < src.length) {
      if (src.startsWith('~~', i)) {
        mis = !mis;
        if (mis) mistakes++;
        i += 2;
        continue;
      }
      if (src[i] === '{') {
        const close = src.indexOf('}', i);
        const bar = src.indexOf('|', i);
        if (close < 0 || bar < 0 || bar > close) {
          error = error || 'ruby';
          pushText(src[i]);
          i++;
          continue;
        }
        const base = src.slice(i + 1, bar), reading = src.slice(bar + 1, close);
        if (!base || !reading) error = error || 'ruby';
        tokens.push({ k: 'ime', base, reading, mis });
        i = close + 1;
        continue;
      }
      pushText(src[i]);
      i++;
    }
    if (mis) error = error || 'strike';
    const visible = tokens
      .filter((t) => !t.mis)
      .map((t) => (t.k === 'ime' ? t.base : t.s))
      .join('');
    return { tokens, visible, mistakes, error };
  };

  /* plain reading text of any scene (for aria labels, lists, counts) */
  T.plain = function (scene) {
    if (!scene) return '';
    const s = scene.type === 'type' ? T.parseTyping(scene.text).visible : String(scene.text || '');
    const lines = s.split('\n').map((l) => l.trim()).filter(Boolean);
    const j = T.hasJa(s) ? '' : ' ';
    let out = lines.join(j);
    if (scene.type === 'split' && scene.insert) out += j + scene.insert.trim();
    return out;
  };

  /* ================= browser-only below ================= */

  K.fontFor = function (str) {
    const base = T.hasJa(str) ? K.FONTS.ja : K.FONTS.lat;
    const f = Object.assign({}, base);
    /* lower-case Latin needs room for descenders */
    if (!T.hasJa(str) && /[a-z]/.test(str)) f.lh = 1.0;
    return f;
  };

  /* ---------- measurement ---------- */
  const M = (K.meas = {});
  const cache = new Map();
  let host = null, ctx2d = null;

  M.clear = () => cache.clear();

  function ensureHost() {
    if (host && host.isConnected) return host;
    host = document.createElement('div');
    host.className = 'k-measure-host';
    host.setAttribute('aria-hidden', 'true');
    document.body.appendChild(host);
    return host;
  }

  /* Lay the string out as one real text run at 100px and read every grapheme's
     position from Range rects, so kerning, palt and punctuation trimming are kept.
     Returns em units: { w, b (baseline from line-box top), glyphs: [{ch, x, adv}] } */
  M.line = function (str, font) {
    const key = font.cls + '|' + font.lh + '|' + str;
    const hit = cache.get(key);
    if (hit) return hit;
    const el = document.createElement('span');
    el.className = 'k-measure ' + font.cls;
    el.style.lineHeight = String(font.lh);
    const tn = document.createTextNode(str);
    const probe = document.createElement('i');
    probe.className = 'k-probe';
    el.appendChild(tn);
    el.appendChild(probe);
    ensureHost().appendChild(el);
    const box = el.getBoundingClientRect();
    const pr = probe.getBoundingClientRect();
    const range = document.createRange();
    const glyphs = [];
    let off = 0;
    for (const ch of T.graphemes(str)) {
      range.setStart(tn, off);
      range.setEnd(tn, off + ch.length);
      const r = range.getBoundingClientRect();
      glyphs.push({ ch, x: (r.left - box.left) / 100, adv: 0 });
      off += ch.length;
    }
    const w = (pr.left - box.left) / 100;
    for (let i = 0; i < glyphs.length; i++) glyphs[i].adv = (i + 1 < glyphs.length ? glyphs[i + 1].x : w) - glyphs[i].x;
    const res = { w, b: (pr.top - box.top) / 100, h: box.height / 100, glyphs };
    el.remove();
    cache.set(key, res);
    return res;
  };

  M.ctx = function (font, px) {
    if (!ctx2d) ctx2d = document.createElement('canvas').getContext('2d');
    ctx2d.font = `${font.weight} ${px}px ${font.family}`;
    if ('fontStretch' in ctx2d) ctx2d.fontStretch = font.stretch === 'condensed' ? 'condensed' : 'normal';
    return ctx2d;
  };

  /* ink bounds of a string relative to its baseline, em units (asc up, desc down) */
  M.ink = function (str, font) {
    const key = 'ink|' + font.cls + '|' + str;
    const hit = cache.get(key);
    if (hit) return hit;
    const m = M.ctx(font, 100).measureText(str);
    const res = { asc: m.actualBoundingBoxAscent / 100, desc: m.actualBoundingBoxDescent / 100 };
    cache.set(key, res);
    return res;
  };

  /* ---------- line fitting ---------- */
  /* Split phrases into n lines minimising the widest line (exact widths, memoised). */
  function partition(phrases, n, font, j) {
    const P = phrases.length;
    const wOf = (a, b) => M.line(phrases.slice(a, b + 1).join(j), font).w;
    const best = [], cut = [];
    for (let k = 0; k < n; k++) {
      best.push(new Array(P).fill(Infinity));
      cut.push(new Array(P).fill(-1));
    }
    for (let e = 0; e < P; e++) best[0][e] = wOf(0, e);
    for (let k = 1; k < n; k++) {
      for (let e = k; e < P; e++) {
        for (let s = k; s <= e; s++) {
          const v = Math.max(best[k - 1][s - 1], wOf(s, e));
          if (v < best[k][e]) {
            best[k][e] = v;
            cut[k][e] = s;
          }
        }
      }
    }
    const lines = [];
    let e = P - 1;
    for (let k = n - 1; k >= 0; k--) {
      const s = k === 0 ? 0 : cut[k][e];
      lines.unshift(phrases.slice(s, e + 1).join(j));
      e = s - 1;
    }
    return { lines, w: best[n - 1][P - 1] };
  }
  T.partition = partition;

  /* Rows for scenes where every line is a unit (stretch rows, prism faces):
     hard lines if given, otherwise phrases merged into at most maxRows balanced rows. */
  T.rows = function (text, font, maxRows) {
    const explicit = T.explicitLines(text);
    if (explicit) return explicit.slice(0, maxRows);
    const ph = T.phrases(text);
    if (ph.length <= maxRows) return ph;
    return partition(ph, maxRows, font, T.joiner(text)).lines;
  };

  /* Choose line breaks and a font size for a block that must fit W×H (px).
     Newlines in the text are hard breaks; otherwise try 1..maxLines balanced lines. */
  T.fit = function (text, font, W, H, opts) {
    opts = opts || {};
    const maxLines = opts.maxLines || 3;
    const lh = font.lh;
    const explicit = T.explicitLines(text);
    if (explicit) {
      const ws = explicit.map((l) => M.line(l, font).w);
      const w = Math.max.apply(null, ws);
      return { lines: explicit, size: Math.min(W / w, H / (explicit.length * lh)), w };
    }
    const phrases = T.phrases(text);
    if (!phrases.length) return { lines: [''], size: 10, w: 1 };
    const j = T.joiner(text);
    let pick = null;
    for (let n = 1; n <= Math.min(maxLines, phrases.length); n++) {
      const p = partition(phrases, n, font, j);
      const size = Math.min(W / p.w, H / (n * lh));
      /* an extra line has to earn its place: +8% size */
      if (!pick || size > pick.size * 1.08) pick = { lines: p.lines, size, w: p.w };
    }
    return pick;
  };

  /* Build a line of inline-block glyphs with the measured advances. */
  K.glyphLine = function (str, font) {
    const m = M.line(str, font);
    const el = document.createElement('span');
    el.className = 'k-line ' + font.cls;
    el.style.lineHeight = String(font.lh);
    const glyphs = m.glyphs.map((g) => {
      const s = document.createElement('span');
      s.className = 'k-g';
      s.textContent = g.ch;
      s.style.width = g.adv.toFixed(4) + 'em';
      el.appendChild(s);
      return { el: s, ch: g.ch, x: g.x, adv: g.adv, space: /^\s+$/.test(g.ch) };
    });
    return { el, glyphs, w: m.w, b: m.b, h: m.h, str };
  };
})(typeof window !== 'undefined' ? window : globalThis);
