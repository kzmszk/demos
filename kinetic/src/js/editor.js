/* Kinetic Manifesto — edit mode. A side panel of plain fields for every piece of copy,
   live preview, per-scene show/play, reorder/add/remove, palette presets with contrast
   checks, inline quality warnings, local draft autosave, and HTML/JSON export/import. */
(function (root) {
  'use strict';
  const K = root.K;
  const T = K.text;
  const doc = document;
  const app = K.app;
  const JA_UI = /^ja\b/i.test((root.navigator && root.navigator.language) || 'ja');
  const t = (ja, en) => (JA_UI ? ja : en);

  const HINTS = {
    assemble: t('散らばった文字が集まります。改行で行を固定、なければ文節で自動改行。', 'Scattered glyphs assemble. Newlines fix the breaks; otherwise lines are balanced automatically.'),
    stretch: t('1行＝1段。2〜4段、各段は短く。行ごとに横へ伸びて揃います。', 'One line per row, 2–4 short rows. Each row stretches to the measure.'),
    split: t('刃で切られる1行。下の「帯の文字」が切れ目から現れます。', 'The line that gets cut. The insert line appears in the gap.'),
    cascade: t('文字がドミノのように順に立ち上がります。', 'Glyphs stand up one after another like dominoes.'),
    prism: t('1行＝1面（2〜4面）。角柱が一面ずつ回ります。', 'One line per face (2–4). The prism turns face by face.'),
    type: t('~~消す語~~ で打ち間違い、{漢字|かんじ} でかな入力→変換。', '~~word~~ = typed-then-deleted mistake; {漢字|かんじ} = IME conversion.'),
  };
  const SAMPLE = {
    ja: {
      assemble: '新しい宣言を、ここに。',
      stretch: '短い\n言葉を\n並べる。',
      split: ['切られる言葉', '現れる言葉'],
      cascade: 'ひとつずつ、立ち上がる。',
      prism: '見る。\n回す。\n変わる。',
      type: '{書|か}いて、~~{消|け}す~~{直|なお}す。',
    },
    en: {
      assemble: 'Say it in pieces.',
      stretch: 'Make\nroom\nfor it.',
      split: ['Cut here', 'and look inside.'],
      cascade: 'One thing sets off the next.',
      prism: 'Turn\nit\nover.',
      type: 'Write it, ~~polish~~ mean it.',
    },
  };

  const ed = (K.editor = {});
  let panel = null, body = null, cardsBox = null, summary = null, status = null, fileIn = null;
  let C = null; /* working copy */
  let renderTimer = 0, saveTimer = 0, issues = [];

  /* ---------- paths ---------- */
  const getAt = (o, path) => path.split('.').reduce((a, k) => (a == null ? a : a[k]), o);
  const setAt = (o, path, v) => {
    const ks = path.split('.');
    const last = ks.pop();
    const tgt = ks.reduce((a, k) => a[k], o);
    tgt[last] = v;
  };

  /* ---------- small builders ---------- */
  function slot(path) {
    return K.h('div.k-ed-issues', { 'data-for': path, 'aria-live': 'polite' });
  }
  function field(label, path, opts) {
    opts = opts || {};
    const id = 'k-ed-' + path.replace(/\./g, '-');
    let input;
    if (opts.area) {
      input = K.h('textarea', { id, rows: opts.rows || 2, 'data-path': path, spellcheck: 'false' });
    } else if (opts.select) {
      input = K.h('select', { id, 'data-path': path }, ...opts.select.map(([v, l]) => K.h('option', { value: v, text: l })));
    } else {
      input = K.h('input', { id, type: 'text', 'data-path': path, spellcheck: 'false', autocomplete: 'off' });
    }
    if (opts.placeholder) input.setAttribute('placeholder', opts.placeholder);
    const wrap = K.h('div.k-ed-field' + (opts.cls ? '.' + opts.cls : ''), null, K.h('label', { for: id, text: label }), input);
    if (opts.hint) wrap.appendChild(K.h('p.k-ed-hint', { text: opts.hint }));
    wrap.appendChild(slot(path));
    return wrap;
  }
  function group(title, ...kids) {
    return K.h('section.k-ed-group', null, K.h('h3', { text: title }), ...kids);
  }
  function btn(label, onclick, cls, attrs) {
    return K.h('button.k-ed-btn' + (cls ? '.' + cls : ''), Object.assign({ type: 'button', onclick }, attrs || {}), label);
  }
  /* a destructive button that asks for a second press */
  function confirmBtn(label, sure, onconfirm, cls) {
    let armed = 0;
    const b = btn(label, () => {
      if (armed) {
        clearTimeout(armed);
        armed = 0;
        b.textContent = label;
        b.classList.remove('is-armed');
        onconfirm();
      } else {
        b.textContent = sure;
        b.classList.add('is-armed');
        armed = setTimeout(() => {
          armed = 0;
          b.textContent = label;
          b.classList.remove('is-armed');
        }, 3200);
      }
    }, cls);
    return b;
  }

  /* ---------- panel ---------- */
  function build() {
    const langSel = [
      ['ja', '日本語 (ja)'],
      ['en', 'English (en)'],
    ];
    status = K.h('p.k-ed-status', { role: 'status' });
    summary = K.h('p.k-ed-summary');
    const head = K.h(
      'header.k-ed-head',
      null,
      K.h('div', null, K.h('h2', { id: 'k-ed-title', text: t('編集', 'Edit') }), status),
      K.h(
        'div.k-ed-head-actions',
        null,
        btn(t('プレビュー', 'Preview'), () => panel.classList.add('is-peek'), 'k-ed-peek-btn'),
        btn('×', ed.close, 'k-ed-close', { 'aria-label': t('編集パネルを閉じる', 'Close the editor'), title: t('閉じる (E)', 'Close (E)') })
      )
    );

    const presets = K.h('div.k-ed-presets', { role: 'group', 'aria-label': t('配色プリセット', 'Palette presets') });
    K.PRESETS.forEach((p) => {
      const b = btn(
        [K.h('i', { style: { background: p.bg } }), K.h('i', { style: { background: p.fg } }), K.h('i', { style: { background: p.accent } })],
        () => {
          C.palette = { bg: p.bg, fg: p.fg, accent: p.accent };
          fillAll();
          changed();
        },
        'k-ed-swatch',
        { title: JA_UI ? p.ja : p.en, 'aria-label': JA_UI ? p.ja : p.en }
      );
      presets.appendChild(b);
    });
    const colour = (label, key) => {
      const path = 'palette.' + key;
      const pick = K.h('input', { type: 'color', 'data-color': path, 'aria-label': label });
      const hex = K.h('input', { type: 'text', 'data-path': path, spellcheck: 'false', maxlength: '7', 'aria-label': label + ' (hex)' });
      return K.h('div.k-ed-colour', null, K.h('span', { text: label }), pick, hex);
    };
    const contrast = K.h('p.k-ed-contrast');

    cardsBox = K.h('div.k-ed-cards');
    const addType = K.h(
      'select',
      { 'aria-label': t('追加するシーンの動き', 'Motion for the new scene') },
      ...Object.keys(K.TYPES).map((k) => K.h('option', { value: k, text: `${JA_UI ? K.TYPES[k].ja : K.TYPES[k].en} · ${k}` }))
    );
    const add = K.h(
      'div.k-ed-add',
      null,
      addType,
      btn(t('＋ シーンを追加', '+ Add scene'), () => {
        const type = addType.value;
        const sm = SAMPLE[C.lang][type];
        C.scenes.push({ type, text: Array.isArray(sm) ? sm[0] : sm, insert: Array.isArray(sm) ? sm[1] : '', gloss: '' });
        buildCards();
        changed();
        const i = C.scenes.length - 1;
        setTimeout(() => {
          const ta = cardsBox.querySelector(`[data-path="scenes.${i}.text"]`);
          if (ta) ta.focus();
        }, 300);
      })
    );

    const portalSel = K.h('select', { id: 'k-ed-portal', 'data-path': 'finale.portal' });

    fileIn = K.h('input', { type: 'file', accept: '.json,.html,.htm,application/json,text/html', hidden: true });
    fileIn.addEventListener('change', () => {
      const f = fileIn.files && fileIn.files[0];
      if (f) loadFile(f);
      fileIn.value = '';
    });

    body = K.h(
      'div.k-ed-body',
      null,
      summary,
      group(
        t('基本', 'Page'),
        field(t('言語', 'Language'), 'lang', { select: langSel, hint: t('組版ルールとボタン表記が切り替わります（本文は翻訳されません）', 'Switches typesetting rules and UI labels (copy is not translated)') }),
        field(t('ページタイトル <title>', 'Page title <title>'), 'meta.title'),
        field(t('説明文 (meta description)', 'Meta description'), 'meta.description', { area: true, rows: 2 }),
        field(t('ファイル名（半角英数）', 'File name (a–z, 0–9)'), 'meta.slug', { cls: 'is-mono' })
      ),
      group(t('配色（3色）', 'Palette (three colours)'), presets, colour(t('地', 'Ground'), 'bg'), colour(t('文字', 'Type'), 'fg'), colour(t('アクセント', 'Accent'), 'accent'), contrast, slot('palette.fg'), slot('palette.accent'), slot('palette.bg')),
      group(
        t('タイトルカード', 'Title card'),
        field(t('タイトル語（フィナーレでも使用）', 'Title word (also used by the finale)'), 'intro.word', { hint: t('O・D・0・回・口・間 など、閉じた空間（カウンター）を持つ字があると最後にその中へズームします', 'A glyph with a counter (O, D, 0, 回, 口, 間…) becomes the zoom portal in the finale') }),
        field(t('キッカー（語の上の小さな行）', 'Kicker (small line above)'), 'intro.kicker'),
        field(t('サブ（ひとこと紹介）', 'Sub (one-line introduction)'), 'intro.sub', { area: true, rows: 2 }),
        field(t('ティッカー（下の帯）', 'Ticker (accent band)'), 'intro.ticker'),
        K.h(
          'div.k-ed-row5',
          null,
          field('PROD.', 'intro.slate.prod', { cls: 'is-mono' }),
          field('ROLL', 'intro.slate.roll', { cls: 'is-mono' }),
          field('TAKE', 'intro.slate.take', { cls: 'is-mono' }),
          field('DATE', 'intro.slate.date', { cls: 'is-mono' }),
          field('DIR.', 'intro.slate.dir', { cls: 'is-mono' })
        )
      ),
      K.h('section.k-ed-group', null, K.h('h3', { text: t('シーン', 'Scenes') }), slot('scenes'), cardsBox, add),
      group(
        t('フィナーレと締め', 'Finale & closing'),
        K.h('div.k-ed-field', null, K.h('label', { for: 'k-ed-portal', text: t('ズームする文字（ポータル）', 'Zoom portal glyph') }), portalSel, slot('finale.portal')),
        field(t('締めの言葉', 'Closing line'), 'finale.text'),
        field(t('締めの注記（訳など）', 'Closing gloss (translation…)'), 'finale.gloss'),
        field(t('リプレイボタンの文言', 'Replay button label'), 'finale.replay')
      ),
      group(
        t('オプション', 'Options'),
        K.h('label.k-ed-check', null, K.h('input', { type: 'checkbox', 'data-bool': 'options.uppercase' }), t('欧文を大文字で組む', 'Set Latin in capitals')),
        K.h('label.k-ed-check', null, K.h('input', { type: 'checkbox', 'data-bool': 'options.editable' }), t('書き出したページでも編集ボタンを出す', 'Keep the Edit button in exported pages'))
      )
    );

    const foot = K.h(
      'footer.k-ed-foot',
      null,
      K.h(
        'div.k-ed-foot-row',
        null,
        btn(t('HTMLを保存', 'Save HTML'), exportHTML, 'is-primary'),
        btn(t('JSONを保存', 'Save JSON'), exportJSON),
        btn(t('読み込む', 'Load'), () => fileIn.click())
      ),
      K.h(
        'div.k-ed-foot-row',
        null,
        K.h('p.k-ed-note', { text: t('編集内容はこのブラウザに下書き保存されます。ファイルに反映するには「HTMLを保存」。JSON / HTML をここへドロップしても読み込めます。', 'Edits are kept as a draft in this browser. Use “Save HTML” to write a file. Drop a JSON or HTML file here to load it.') }),
        confirmBtn(t('下書きを破棄', 'Discard draft'), t('もう一度押すと破棄', 'Press again to discard'), revert, 'is-quiet')
      ),
      fileIn
    );

    panel = K.h('aside.k-ed', { 'aria-labelledby': 'k-ed-title', hidden: true }, head, body, foot);
    const back = btn(t('編集に戻る', 'Back to editor'), () => panel.classList.remove('is-peek'), 'k-ed-back');
    panel.appendChild(back);
    doc.body.appendChild(panel);

    /* input wiring */
    panel.addEventListener('input', (e) => {
      const el = e.target;
      if (el.dataset.path) {
        const path = el.dataset.path;
        let v = el.value;
        if (path === 'finale.portal') v = v === 'auto' ? 'auto' : +v;
        if (path.startsWith('palette.')) {
          if (!K.parseHex(v)) return;
          v = v.startsWith('#') ? v : '#' + v;
          const pick = panel.querySelector(`[data-color="${path}"]`);
          if (pick) pick.value = K.normalize({ palette: { bg: v } }).palette.bg;
        }
        setAt(C, path, v);
        if (path === 'lang') buildCards();
        if (path === 'intro.word') fillPortal();
        changed();
      } else if (el.dataset.color) {
        setAt(C, el.dataset.color, el.value);
        const hex = panel.querySelector(`[data-path="${el.dataset.color}"]`);
        if (hex) hex.value = el.value;
        changed();
      }
    });
    panel.addEventListener('change', (e) => {
      const el = e.target;
      if (el.dataset.bool) {
        setAt(C, el.dataset.bool, el.checked);
        changed(true);
      } else if (el.dataset.scenetype) {
        C.scenes[+el.dataset.scenetype].type = el.value;
        buildCards();
        changed(true);
      } else if (el.dataset.path === 'finale.portal' || el.dataset.path === 'lang') {
        changed(true);
      }
    });
    /* focusing a scene card shows that scene fully played */
    panel.addEventListener('focusin', (e) => {
      const card = e.target.closest && e.target.closest('.k-ed-card');
      if (!card) return;
      const i = +card.dataset.i;
      const pos = app.position();
      if (pos.i !== i) app.jump(i, 'end', { instant: true });
    });
    /* drop JSON / HTML files */
    panel.addEventListener('dragover', (e) => {
      e.preventDefault();
      panel.classList.add('is-drop');
    });
    panel.addEventListener('dragleave', (e) => {
      if (e.target === panel) panel.classList.remove('is-drop');
    });
    panel.addEventListener('drop', (e) => {
      e.preventDefault();
      panel.classList.remove('is-drop');
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) loadFile(f);
    });
    app.on('scene', (i) => {
      if (!cardsBox) return;
      cardsBox.querySelectorAll('.k-ed-card').forEach((c) => c.classList.toggle('is-current', +c.dataset.i === i));
    });
  }

  function buildCards() {
    cardsBox.textContent = '';
    const total = C.scenes.length + 1;
    C.scenes.forEach((s, i) => {
      const info = K.TYPES[s.type];
      const typeSel = K.h(
        'select',
        { 'data-scenetype': i, 'aria-label': t(`シーン ${i + 1} の動き`, `Motion of scene ${i + 1}`) },
        ...Object.keys(K.TYPES).map((k) => K.h('option', { value: k, text: `${JA_UI ? K.TYPES[k].ja : K.TYPES[k].en} · ${k}` }))
      );
      typeSel.value = s.type;
      const card = K.h(
        'article.k-ed-card',
        { 'data-i': i },
        K.h(
          'header',
          null,
          K.h('span.k-ed-no', { text: `SC. ${K.pad(i + 1)} / ${K.pad(total)}` }),
          typeSel,
          K.h(
            'span.k-ed-move',
            null,
            btn('↑', () => move(i, -1), 'is-icon', { 'aria-label': t('上へ', 'Move up'), disabled: i === 0 }),
            btn('↓', () => move(i, 1), 'is-icon', { 'aria-label': t('下へ', 'Move down'), disabled: i === C.scenes.length - 1 }),
            confirmBtn(t('削除', 'Delete'), t('削除する？', 'Sure?'), () => remove(i), 'is-quiet')
          )
        ),
        field(t('本文', 'Text'), `scenes.${i}.text`, { area: true, rows: s.type === 'stretch' || s.type === 'prism' ? 4 : 2, hint: HINTS[s.type] }),
        s.type === 'split' ? field(t('帯の文字', 'Insert line'), `scenes.${i}.insert`) : null,
        field(t('注記（訳・補足。小さく表示）', 'Gloss (small translation or note)'), `scenes.${i}.gloss`),
        K.h(
          'div.k-ed-card-foot',
          null,
          K.h('span.k-ed-count', { 'data-count': i }),
          btn(t('表示', 'Show'), () => app.jump(i, 'end', { instant: true }), 'is-small'),
          btn(t('▶ 再生', '▶ Play'), () => app.play(i), 'is-small')
        ),
        slot(`scenes.${i}`)
      );
      cardsBox.appendChild(card);
    });
    fillAll();
  }

  function move(i, d) {
    const j = i + d;
    if (j < 0 || j >= C.scenes.length) return;
    const s = C.scenes.splice(i, 1)[0];
    C.scenes.splice(j, 0, s);
    buildCards();
    changed(true);
    const b = cardsBox.querySelector(`.k-ed-card[data-i="${j}"] header select`);
    if (b) b.focus();
  }
  function remove(i) {
    C.scenes.splice(i, 1);
    buildCards();
    changed(true);
  }

  function fillPortal() {
    const sel = panel.querySelector('#k-ed-portal');
    if (!sel) return;
    const word = K.display(C.intro.word, C);
    const list = K.portal.survey(word, K.fontFor(word));
    sel.textContent = '';
    sel.appendChild(K.h('option', { value: 'auto', text: t('自動（いちばん大きなカウンター）', 'Auto (largest counter)') }));
    list.forEach((g, i) => sel.appendChild(K.h('option', { value: String(i), text: `${i + 1}: ${g.ch}${g.counter ? t('　◎ カウンターあり', '  ◎ has a counter') : t('　（線の中へ）', '  (into the stroke)')}` })));
    sel.value = String(C.finale.portal);
    if (sel.value !== String(C.finale.portal)) sel.value = 'auto';
  }

  function fillAll() {
    panel.querySelectorAll('[data-path]').forEach((el) => {
      const v = getAt(C, el.dataset.path);
      if (el.tagName === 'SELECT' && el.id === 'k-ed-portal') return;
      if (doc.activeElement !== el) el.value = v == null ? '' : String(v);
    });
    panel.querySelectorAll('[data-color]').forEach((el) => (el.value = getAt(C, el.dataset.color)));
    panel.querySelectorAll('[data-bool]').forEach((el) => (el.checked = !!getAt(C, el.dataset.bool)));
    fillPortal();
    validate();
  }

  /* ---------- validation display ---------- */
  function validate() {
    issues = K.validate(C);
    const L = JA_UI ? 'ja' : 'en';
    panel.querySelectorAll('.k-ed-issues').forEach((s) => (s.textContent = ''));
    const errs = issues.filter((x) => x.level === 'error').length;
    const warns = issues.length - errs;
    issues.forEach((x) => {
      let target = panel.querySelector(`.k-ed-issues[data-for="${x.path}"]`);
      if (!target) {
        const m = /^scenes\.(\d+)/.exec(x.path);
        target = m ? panel.querySelector(`.k-ed-issues[data-for="scenes.${m[1]}"]`) : null;
      }
      if (!target) target = panel.querySelector('.k-ed-issues[data-for="scenes"]');
      if (target) target.appendChild(K.h('p.k-ed-issue.is-' + x.level, { text: x.msg[L] }));
    });
    summary.textContent = errs || warns ? t(`エラー ${errs} · 注意 ${warns}`, `${errs} errors · ${warns} warnings`) : t('問題なし', 'No issues');
    summary.className = 'k-ed-summary' + (errs ? ' is-error' : warns ? ' is-warn' : ' is-ok');
    C.scenes.forEach((s, i) => {
      const el = panel.querySelector(`[data-count="${i}"]`);
      if (!el) return;
      const txt = s.type === 'type' ? T.parseTyping(s.text).visible : s.text;
      el.textContent = t(`${T.count(txt)} 字`, `${T.count(txt)} chars`);
    });
    const cf = K.contrast(C.palette.fg, C.palette.bg), ca = K.contrast(C.palette.accent, C.palette.bg);
    const c = panel.querySelector('.k-ed-contrast');
    if (c) c.textContent = t(`文字/地 ${cf.toFixed(1)}:1 · アクセント/地 ${ca.toFixed(1)}:1`, `type/ground ${cf.toFixed(1)}:1 · accent/ground ${ca.toFixed(1)}:1`);
  }

  /* ---------- change pipeline: validate now, render and save shortly after ---------- */
  function changed(now) {
    validate();
    clearTimeout(renderTimer);
    renderTimer = setTimeout(() => app.render(K.clone(C), { keep: true }), now ? 0 : 260);
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveDraft, 500);
  }
  function stamp() {
    const d = new Date();
    return `${K.pad(d.getHours())}:${K.pad(d.getMinutes())}`;
  }
  function saveDraft() {
    const ok = K.store.set(app.draftKey, { content: C, t: Date.now() });
    app.setDraft(true);
    status.textContent = ok ? t(`下書きを保存 ${stamp()}`, `Draft saved ${stamp()}`) : t('下書きを保存できません（ストレージ無効）', 'Cannot save a draft (storage blocked)');
  }
  function revert() {
    K.store.del(app.draftKey);
    C = K.clone(app.source);
    app.setDraft(false);
    buildCards();
    app.render(K.clone(C), { keep: true });
    status.textContent = t('元の内容に戻しました', 'Reverted to the original');
  }

  /* ---------- import / export ---------- */
  function loadFile(f) {
    const r = new FileReader();
    r.onload = () => {
      const text = String(r.result || '');
      let raw = null;
      try {
        if (/^\s*[{[]/.test(text)) raw = JSON.parse(text);
        else {
          const d = new DOMParser().parseFromString(text, 'text/html');
          const n = d.getElementById('k-content');
          if (n) raw = JSON.parse(n.textContent);
        }
      } catch (e) {
        raw = null;
      }
      if (!raw || typeof raw !== 'object') {
        status.textContent = t('読み込めませんでした（JSON か、このテンプレートの HTML を選んでください）', 'Could not load (choose a JSON file or an HTML page made with this template)');
        return;
      }
      C = K.normalize(raw);
      buildCards();
      changed(true);
      app.top();
      status.textContent = t(`「${f.name}」を読み込みました`, `Loaded “${f.name}”`);
    };
    r.readAsText(f);
  }
  function exportJSON() {
    K.exporter.download(`${C.meta.slug}.json`, JSON.stringify(K.normalize(C), null, 2) + '\n', 'application/json');
    status.textContent = t(`${C.meta.slug}.json を書き出しました`, `Saved ${C.meta.slug}.json`);
  }
  function exportHTML() {
    const errs = issues.filter((x) => x.level === 'error');
    if (errs.length) {
      status.textContent = t('エラーがあるため書き出せません（赤い項目を直してください）', 'Fix the errors (in red) before saving');
      return;
    }
    status.textContent = t('書き出し中…', 'Saving…');
    K.exporter
      .html(C)
      .then((html) => {
        K.exporter.download(`${C.meta.slug}.html`, html, 'text/html');
        status.textContent = t(`${C.meta.slug}.html を書き出しました`, `Saved ${C.meta.slug}.html`);
      })
      .catch(() => {
        status.textContent = t('書き出しに失敗しました（ローカルサーバー経由で開いてください）', 'Export failed (open the page through a local server)');
      });
  }

  /* ---------- open / close ---------- */
  ed.isOpen = () => !!(panel && !panel.hidden);
  ed.open = function () {
    if (!app.canEdit()) return;
    if (!panel) build();
    C = K.clone(app.C);
    buildCards();
    panel.hidden = false;
    panel.classList.remove('is-peek');
    app.setEditing(true);
    status.textContent = app.state.draft ? t('下書きを表示中', 'Showing your local draft') : t('入力するとすぐ反映されます', 'Changes apply as you type');
    const first = panel.querySelector('[data-path="intro.word"]');
    if (first) first.focus({ preventScroll: true });
  };
  ed.close = function () {
    if (!panel) return;
    panel.hidden = true;
    app.setEditing(false);
    if (app.state.editing === false && app.C) app.wake();
  };
  ed.toggle = () => (ed.isOpen() ? ed.close() : ed.open());
})(typeof window !== 'undefined' ? window : globalThis);
