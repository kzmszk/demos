/* Kinetic Manifesto — content model: scene types, UI labels, palette presets,
   normalisation (defaults for every missing field) and the quality validator.
   DOM-free: the build script runs this in Node. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;

  /* scroll length of each scene, in stage heights beyond the stage itself */
  K.TYPES = {
    assemble: { code: 'ASSEMBLE', ja: '集合', en: 'Assemble', len: 2.2, limit: { ja: 18, en: 32 } },
    stretch: { code: 'STRETCH', ja: '伸長', en: 'Stretch', len: 2.2, limit: { ja: 5, en: 10 }, perLine: true },
    split: { code: 'SPLIT', ja: '切断', en: 'Split', len: 2.4, limit: { ja: 10, en: 16 }, insert: { ja: 16, en: 28 } },
    cascade: { code: 'CASCADE', ja: '連鎖', en: 'Cascade', len: 2.2, limit: { ja: 20, en: 36 } },
    prism: { code: 'PRISM', ja: '回転', en: 'Prism', len: 3.2, limit: { ja: 6, en: 12 }, perLine: true },
    type: { code: 'TYPE', ja: 'タイプ', en: 'Type', len: 3.0, limit: { ja: 30, en: 48 } },
  };
  K.FINALE = { code: 'ZOOM', ja: 'ズーム', en: 'Zoom', len: 2.8, limit: { ja: 10, en: 16 } };

  K.LABELS = {
    ja: {
      scroll: 'スクロールで再生',
      motionOn: 'モーション オン',
      motionOff: 'モーション オフ',
      motionAria: '動きの再生を切り替える',
      edit: '編集',
      draft: '下書き',
      draftAria: '下書きを表示中。クリックで編集パネルを開く',
      replay: '最初から再生',
      rail: 'シーン一覧',
      list: '宣言の一覧',
      jump: (n, s) => `シーン ${n} へ：${s}`,
      colophon: (n) => `${n} シーン · 3 色 · 画像 0 枚 · システムフォントで組版`,
      end: 'END',
    },
    en: {
      scroll: 'Scroll to play',
      motionOn: 'Motion on',
      motionOff: 'Motion off',
      motionAria: 'Toggle motion',
      edit: 'Edit',
      draft: 'Draft',
      draftAria: 'Showing a local draft. Click to open the editor',
      replay: 'Replay from the top',
      rail: 'Scenes',
      list: 'All statements',
      jump: (n, s) => `Scene ${n}: ${s}`,
      colophon: (n) => `${n} scenes · 3 colours · 0 images · set in system fonts`,
      end: 'END',
    },
  };

  /* curated three-colour palettes; each passes the validator's contrast rules */
  K.PRESETS = [
    { id: 'acid', ja: 'アシッド', en: 'Acid', bg: '#0a0a0a', fg: '#f1f1ec', accent: '#c6ff00' },
    { id: 'signal', ja: 'シグナル', en: 'Signal', bg: '#0b0b0b', fg: '#f3efe6', accent: '#ff4d1f' },
    { id: 'shu', ja: '朱', en: 'Vermilion', bg: '#ede7db', fg: '#151311', accent: '#c62d08' },
    { id: 'cobalt', ja: 'コバルト', en: 'Cobalt', bg: '#eeece6', fg: '#101010', accent: '#2437ff' },
    { id: 'pink', ja: 'ピンク', en: 'Pink', bg: '#101010', fg: '#f5f1ea', accent: '#ff6fb1' },
    { id: 'violet', ja: 'バイオレット', en: 'Violet', bg: '#0e0c16', fg: '#efeaf7', accent: '#a98bff' },
    { id: 'sky', ja: 'スカイ', en: 'Sky', bg: '#0b1220', fg: '#eef2f6', accent: '#5ee3ff' },
    { id: 'safety', ja: 'セーフティ', en: 'Safety', bg: '#111111', fg: '#f2f0ea', accent: '#ff9e1b' },
  ];

  const str = (v, d = '') => (typeof v === 'string' ? v : v == null ? d : String(v));
  const hex = (v, d) => (K.parseHex(v) ? '#' + K.parseHex(v).map((n) => n.toString(16).padStart(2, '0')).join('') : d);

  K.slugify = function (s) {
    const out = String(s || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48);
    return out || 'manifesto';
  };

  /* Fill every missing field. Unknown scene types become "assemble" (the validator reports them). */
  K.normalize = function (raw) {
    raw = raw && typeof raw === 'object' ? raw : {};
    const lang = raw.lang === 'en' ? 'en' : 'ja';
    const L = K.LABELS[lang];
    const meta = raw.meta || {}, pal = raw.palette || {}, intro = raw.intro || {}, fin = raw.finale || {}, opt = raw.options || {};
    const slate = intro.slate || {};
    const word = str(intro.word, 'MOVE').replace(/\s+/g, ' ').trim() || 'MOVE';
    const scenes = (Array.isArray(raw.scenes) ? raw.scenes : []).map((s) => {
      s = s || {};
      return {
        type: K.TYPES[s.type] ? s.type : 'assemble',
        text: str(s.text).replace(/\r\n?/g, '\n'),
        insert: str(s.insert),
        gloss: str(s.gloss),
      };
    });
    let portal = fin.portal;
    if (portal !== 'auto') portal = Number.isInteger(+portal) && +portal >= 0 ? +portal : 'auto';
    return {
      format: K.FORMAT,
      lang,
      meta: {
        title: str(meta.title, word),
        description: str(meta.description),
        slug: K.slugify(meta.slug || meta.title || word),
      },
      palette: {
        bg: hex(pal.bg, '#0a0a0a'),
        fg: hex(pal.fg, '#f1f1ec'),
        accent: hex(pal.accent, '#c6ff00'),
      },
      intro: {
        word,
        kicker: str(intro.kicker),
        sub: str(intro.sub),
        ticker: str(intro.ticker),
        slate: {
          prod: str(slate.prod, word),
          roll: str(slate.roll, 'A'),
          take: str(slate.take, '01'),
          date: str(slate.date),
          dir: str(slate.dir),
        },
      },
      scenes,
      finale: {
        text: str(fin.text),
        gloss: str(fin.gloss),
        portal,
        replay: str(fin.replay) || L.replay,
      },
      options: {
        uppercase: opt.uppercase !== false,
        editable: opt.editable !== false,
      },
    };
  };

  /* the string a scene actually displays (uppercase applied) */
  K.display = (s, content) => (content && content.options && content.options.uppercase ? String(s || '').toUpperCase() : String(s || ''));

  /* ---------- validator ---------- */
  /* issues: [{ level: 'error' | 'warn', path, msg: {ja, en} }] */
  K.validate = function (raw) {
    const c = K.normalize(raw);
    const issues = [];
    const add = (level, path, ja, en) => issues.push({ level, path, msg: { ja, en } });
    const limitOf = (lim, s) => (T.hasJa(s) ? lim.ja : lim.en);

    if (raw && raw.format && raw.format !== K.FORMAT) add('warn', 'format', `未知の形式「${raw.format}」です`, `Unknown format "${raw.format}"`);
    if (!c.meta.title.trim()) add('warn', 'meta.title', 'ページタイトルが空です', 'Page title is empty');
    if (!c.meta.description.trim()) add('warn', 'meta.description', '説明文（meta description）が空です', 'Meta description is empty');

    const pal = (raw && raw.palette) || {};
    ['bg', 'fg', 'accent'].forEach((k) => {
      if (pal[k] != null && !K.parseHex(pal[k])) add('error', 'palette.' + k, `色 ${k} が #rrggbb 形式ではありません`, `Colour ${k} is not #rrggbb`);
    });
    const cf = K.contrast(c.palette.fg, c.palette.bg);
    const ca = K.contrast(c.palette.accent, c.palette.bg);
    if (cf < 3) add('error', 'palette.fg', `文字色と地色のコントラストが ${cf.toFixed(1)}:1 しかありません（7:1 以上）`, `Type/ground contrast is only ${cf.toFixed(1)}:1 (needs 7:1)`);
    else if (cf < 7) add('warn', 'palette.fg', `文字色と地色のコントラスト ${cf.toFixed(1)}:1（推奨 7:1 以上）`, `Type/ground contrast ${cf.toFixed(1)}:1 (7:1 recommended)`);
    if (ca < 3) add('error', 'palette.accent', `アクセントと地色のコントラストが ${ca.toFixed(1)}:1 しかありません（4.5:1 以上）`, `Accent/ground contrast is only ${ca.toFixed(1)}:1 (needs 4.5:1)`);
    else if (ca < 4.5) add('warn', 'palette.accent', `アクセントと地色のコントラスト ${ca.toFixed(1)}:1（推奨 4.5:1 以上）`, `Accent/ground contrast ${ca.toFixed(1)}:1 (4.5:1 recommended)`);

    const w = c.intro.word;
    const wn = T.count(w);
    const wl = T.hasJa(w) ? [1, 4] : [2, 8];
    if (!raw || !raw.intro || !String(raw.intro.word || '').trim()) add('error', 'intro.word', 'タイトル語が空です', 'Title word is empty');
    else if (wn < wl[0] || wn > wl[1]) add('warn', 'intro.word', `タイトル語は ${wl[0]}〜${wl[1]} 字を推奨（いま ${wn} 字）`, `Title word: ${wl[0]}–${wl[1]} characters recommended (now ${wn})`);

    const rawScenes = (raw && Array.isArray(raw.scenes) && raw.scenes) || [];
    if (!rawScenes.length) add('error', 'scenes', 'シーンがありません', 'There are no scenes');
    const total = c.scenes.length + 1;
    if (total < 3 || total > 9) add('warn', 'scenes', `シーン数は 3〜9 を推奨（いま フィナーレ込みで ${total}）`, `3–9 scenes recommended (now ${total} with the finale)`);

    c.scenes.forEach((s, i) => {
      const p = 'scenes.' + i;
      const info = K.TYPES[s.type];
      const rs = rawScenes[i] || {};
      if (!K.TYPES[rs.type]) add('error', p + '.type', `不明な動き「${rs.type}」`, `Unknown motion type "${rs.type}"`);
      if (!s.text.trim()) {
        add('error', p + '.text', '本文が空です', 'Text is empty');
        return;
      }
      if (i > 0 && c.scenes[i - 1].type === s.type) add('warn', p + '.type', '直前のシーンと同じ動きです', 'Same motion as the previous scene');

      if (s.type === 'type') {
        const tp = T.parseTyping(s.text);
        if (tp.error === 'strike') add('error', p + '.text', '~~ が閉じていません', 'Unclosed ~~');
        if (tp.error === 'ruby') add('error', p + '.text', '{漢字|かな} の書き方が正しくありません', 'Malformed {base|reading}');
        if (tp.mistakes > 1) add('warn', p + '.text', '打ち間違い（~~…~~）は1か所を推奨', 'One ~~mistake~~ recommended');
        const n = T.count(tp.visible), lim = limitOf(info.limit, tp.visible);
        if (n > lim) add('warn', p + '.text', `${lim} 字以内を推奨（いま ${n} 字）`, `≤ ${lim} characters recommended (now ${n})`);
        return;
      }
      if (info.perLine) {
        const lines = T.explicitLines(s.text) || T.phrases(s.text);
        const lo = 2, hi = 4;
        const unit = s.type === 'prism' ? ['面', 'faces'] : ['行', 'lines'];
        if (lines.length < lo || lines.length > hi)
          add('warn', p + '.text', `${lo}〜${hi} ${unit[0]}を推奨（いま ${lines.length}）。改行で区切ります`, `${lo}–${hi} ${unit[1]} recommended (now ${lines.length}); separate with newlines`);
        lines.forEach((l, j) => {
          const n = T.count(l), lim = limitOf(info.limit, l);
          if (n > lim) add('warn', p + '.text', `${j + 1} ${unit[0]}目は ${lim} 字以内を推奨（いま ${n} 字）`, `Line ${j + 1}: ≤ ${lim} characters recommended (now ${n})`);
        });
        return;
      }
      const n = T.count(s.text), lim = limitOf(info.limit, s.text);
      if (n > lim) add('warn', p + '.text', `${lim} 字以内を推奨（いま ${n} 字）`, `≤ ${lim} characters recommended (now ${n})`);
      if (s.type === 'split') {
        if (!s.insert.trim()) add('warn', p + '.insert', '帯の文字が空です', 'Insert line is empty');
        else {
          const m = T.count(s.insert), l2 = limitOf(info.insert, s.insert);
          if (m > l2) add('warn', p + '.insert', `帯の文字は ${l2} 字以内を推奨（いま ${m} 字）`, `Insert: ≤ ${l2} characters recommended (now ${m})`);
        }
      }
    });

    const ft = c.finale.text;
    if (!ft.trim()) add('warn', 'finale.text', '締めの言葉が空です', 'Closing line is empty');
    else {
      const n = T.count(ft), lim = limitOf(K.FINALE.limit, ft);
      if (n > lim) add('warn', 'finale.text', `${lim} 字以内を推奨（いま ${n} 字）`, `≤ ${lim} characters recommended (now ${n})`);
    }
    if (c.finale.portal !== 'auto' && c.finale.portal >= T.graphemes(w.replace(/\s/g, '')).length)
      add('warn', 'finale.portal', 'ポータル文字の番号がタイトル語の文字数を超えています', 'Portal glyph index is beyond the title word');
    return issues;
  };
})(typeof window !== 'undefined' ? window : globalThis);
