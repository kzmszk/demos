/* RASTER — the machine: edition controls, copy editor, inversion, print passes, live resize. */
(function (R) {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const svg = $('#poster');
  const stage = $('#stage');
  const input = $('#edition');
  const form = $('#copy');
  const editor = $('#editor');
  const motifSelect = $('#motif');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const scratch = document.createElementNS('http://www.w3.org/2000/svg', 'svg');

  const KEY_DOC = 'raster.doc.v3';
  const KEY_INV = 'raster.inverted';
  const store = {
    get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
    set(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage refused */ } },
  };

  let edition = 417;
  let userDoc = store.get(KEY_DOC);
  let inverted = store.get(KEY_INV) === true;
  let current = null;
  let seq = 0;
  let timers = [];
  let editTimer = 0;

  const pad = (n) => String(n).padStart(4, '0');
  const wrapEd = (n) => ((n % 10000) + 10000) % 10000;
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const size = () => ({ W: Math.max(240, Math.round(stage.clientWidth)), H: Math.max(240, Math.round(stage.clientHeight)) });

  function readHash() {
    const m = /^#(\d{1,4})$/.exec(location.hash);
    return m ? +m[1] : null;
  }

  /* ---------- Japanese glyphs load per subset; make sure the ones in use are in before setting ---------- */
  const WEIGHTS = ['400', '700'];
  function glyphsReady(text) {
    if (!R.hasCJK(text)) return true;
    try { return WEIGHTS.every((w) => document.fonts.check(`${w} 16px "${R.JP_FAMILY}"`, text)); } catch (e) { return true; }
  }
  function loadGlyphs(text) {
    const loads = WEIGHTS.map((w) => document.fonts.load(`${w} 16px "${R.JP_FAMILY}"`, text).catch(() => null));
    return Promise.race([Promise.all(loads), new Promise((r) => setTimeout(r, 2500))]);
  }

  function printPasses() {
    timers.forEach(clearTimeout);
    timers = [
      setTimeout(() => stage.classList.replace('pass-0', 'pass-1'), 300),
      setTimeout(() => stage.classList.replace('pass-1', 'pass-2'), 680),
      setTimeout(() => stage.classList.remove('pass-2'), 1150),
    ];
  }

  async function render(animate) {
    const my = ++seq;
    const { W, H } = size();
    R.compose(scratch, edition, W, H, userDoc);
    const text = scratch.textContent;
    if (!glyphsReady(text)) {
      await loadGlyphs(text);
      if (my !== seq) return;
      R.measureFonts();
    }
    const run = animate && !reduce.matches;
    if (run) {
      timers.forEach(clearTimeout);
      stage.classList.remove('pass-1', 'pass-2');
      stage.classList.add('pass-0');
    }
    current = R.compose(svg, edition, W, H, userDoc);
    if (document.activeElement !== input) input.value = pad(edition);
    motifSelect.value = current.motif;
    try { history.replaceState(null, '', '#' + pad(edition)); } catch (e) { /* sandboxed frames may refuse */ }
    syncEditor();
    if (run) printPasses();
  }

  /* ---------- copy editor ---------- */
  const WORD_FIELDS = {
    numeral: [['words.numeral', '数字（4文字まで）']],
    three: [['words.three.0', '1段目（漢字）'], ['words.three.1', '2段目（かな）'], ['words.three.2', '3段目（ラテン文字）']],
    word: [['words.word', '大きな言葉（和文は縦組・欧文は回転）']],
    gloss: [['words.gloss', '添え書き（赤、括弧つきがおすすめ）']],
    signature: [['words.signature', '拍子（例 7/8）']],
  };
  const getPath = (o, p) => p.split('.').reduce((a, k) => (a == null ? a : a[k]), o);
  function setPath(o, p, v) {
    const ks = p.split('.');
    const last = ks.pop();
    const t = ks.reduce((a, k, i) => (a[k] = a[k] != null ? a[k] : /^\d+$/.test(ks[i + 1] || last) ? [] : {}), o);
    t[last] = v;
  }

  let fieldsMotif = null;
  function buildMotifFields(motif) {
    if (fieldsMotif === motif) return;
    fieldsMotif = motif;
    const box = $('#motif-fields');
    box.textContent = '';
    $('#motif-words legend').textContent = `図像の文字 — ${R.MOTIF_INFO[motif].name}`;
    for (const key of R.MOTIF_WORDS[motif]) {
      for (const [path, label] of WORD_FIELDS[key]) {
        const l = document.createElement('label');
        l.className = 'stack';
        const s = document.createElement('span');
        s.textContent = motif !== 'senkrecht' && key === 'word' ? '大きな言葉' : label;
        const i = document.createElement('input');
        i.id = 'f-' + path.replace(/\./g, '-');
        i.dataset.path = path;
        i.dataset.key = key;
        l.append(s, i);
        box.appendChild(l);
      }
    }
    const hint = document.createElement('p');
    hint.className = 'hint';
    hint.id = 'motif-hint';
    hint.hidden = true;
    hint.textContent = '形式が合わないため、サンプルの文字で組んでいます。';
    box.appendChild(hint);
  }

  function syncEditor() {
    buildMotifFields(current.motif);
    form.querySelectorAll('[data-path]').forEach((el) => {
      if (el !== document.activeElement) {
        const v = getPath(current.doc, el.dataset.path);
        el.value = v == null ? '' : v;
      }
    });
    let anyBad = false;
    $('#motif-fields').querySelectorAll('input').forEach((el) => {
      const key = el.dataset.key;
      const bad = !R.validWord(key, getPath(current.doc, 'words.' + key));
      el.setAttribute('aria-invalid', String(bad));
      anyBad = anyBad || bad;
    });
    $('#motif-hint').hidden = !anyBad;
    $('#editor-status').textContent = userDoc
      ? 'あなたの内容を表示中。どのエディションにも同じ内容が組まれ、奥付から「架空のプログラム」の表記が外れます。'
      : 'サンプルを表示中。入力すると、どのエディションにも同じ内容が組まれます。';
    $('#editor-reset').disabled = !userDoc;
  }

  function setEditor(open) {
    editor.hidden = !open;
    $('#edit').setAttribute('aria-pressed', String(open));
    if (!open && editor.contains(document.activeElement)) $('#edit').focus();
  }

  function setInvert(on) {
    inverted = on;
    R.setInverted(on);
    document.documentElement.classList.toggle('inverted', on);
    store.set(KEY_INV, on);
    $('#invert').setAttribute('aria-pressed', String(on));
    if (current) render(false);
  }

  /* ---------- export ---------- */
  let statusTimer = 0;
  function notify(msg) {
    const el = $('#status');
    el.textContent = msg;
    el.classList.add('on');
    clearTimeout(statusTimer);
    statusTimer = setTimeout(() => el.classList.remove('on'), 2600);
  }

  async function save(kind) {
    if (!current || $('#export').hidden) return;
    const btns = [$('#save-png'), $('#save-svg')];
    btns.forEach((b) => (b.disabled = true));
    const { W, H } = current.G;
    const name = `raster-${pad(edition)}${inverted ? '-inverted' : ''}.${kind}`;
    try {
      const blob = kind === 'png' ? await R.exportPNG(svg, W, H) : R.exportSVG(svg, W, H);
      const status = await R.offer(name, blob);
      notify(status === 'delivered' ? `${name} を渡しました` : `${name} を保存しました`);
    } catch (e) {
      const code = e && e.code;
      if (code === 'declined') notify('保存を取り消しました');
      else if (code === 'rate_limited') notify('保存の確認がすでに開いています');
      else if (code === 'unavailable' || code === 'not_granted') { notify('この表示では保存できません'); $('#export').hidden = true; }
      else notify('書き出しに失敗しました。もう一度お試しください');
    } finally {
      btns.forEach((b) => (b.disabled = false));
    }
  }

  function toggleGrid() {
    const on = !stage.classList.contains('show-grid');
    stage.classList.toggle('show-grid', on);
    $('#grid').setAttribute('aria-pressed', String(on));
  }

  /* ---------- navigation ---------- */
  function go(n) {
    edition = wrapEd(n);
    render(true);
  }
  const random = () => go(Math.floor(Math.random() * 10000));

  function nextWith(motif) {
    for (let i = 1; i <= 10000; i++) {
      const n = wrapEd(edition + i);
      if (R.motifOf(n) === motif) return go(n);
    }
  }

  function commitInput() {
    const v = parseInt(input.value.replace(/\D/g, ''), 10);
    if (Number.isFinite(v)) go(v);
    else input.value = pad(edition);
  }

  function wire() {
    for (const key of R.MOTIFS) {
      const o = document.createElement('option');
      o.value = key;
      o.textContent = R.MOTIF_INFO[key].name;
      motifSelect.appendChild(o);
    }
    motifSelect.addEventListener('change', () => nextWith(motifSelect.value));
    stage.addEventListener('click', random);
    $('#prev').addEventListener('click', () => go(edition - 1));
    $('#next').addEventListener('click', () => go(edition + 1));
    $('#grid').addEventListener('click', toggleGrid);
    $('#save-png').addEventListener('click', () => save('png'));
    $('#save-svg').addEventListener('click', () => save('svg'));
    R.downloads().then((dl) => { $('#export').hidden = dl === null; });
    $('#invert').addEventListener('click', () => setInvert(!inverted));
    $('#edit').addEventListener('click', () => setEditor(editor.hidden));
    $('#editor-close').addEventListener('click', () => setEditor(false));
    $('#editor-reset').addEventListener('click', () => {
      userDoc = null;
      store.set(KEY_DOC, null);
      render(false);
    });

    form.addEventListener('submit', (e) => e.preventDefault());
    form.addEventListener('input', (e) => {
      const el = e.target.closest('[data-path]');
      if (!el || !current) return;
      if (!userDoc) userDoc = clone(current.doc);
      setPath(userDoc, el.dataset.path, el.value);
      store.set(KEY_DOC, userDoc);
      clearTimeout(editTimer);
      editTimer = setTimeout(() => render(false), 160);
    });

    input.addEventListener('input', () => { input.value = input.value.replace(/\D/g, '').slice(0, 4); });
    input.addEventListener('change', commitInput);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); commitInput(); input.select(); } });
    input.addEventListener('focus', () => input.select());

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !editor.hidden) { setEditor(false); return; }
      if (e.target.closest('input, textarea, select') || e.metaKey || e.ctrlKey || e.altKey || e.isComposing) return;
      if ((e.key === ' ' || e.key === 'Enter') && e.target.closest('button')) return;
      const k = e.key.toLowerCase();
      if (e.key === 'ArrowLeft') go(edition - 1);
      else if (e.key === 'ArrowRight') go(edition + 1);
      else if (e.key === ' ') random();
      else if (k === 'r') random();
      else if (k === 'g') toggleGrid();
      else if (k === 'i') setInvert(!inverted);
      else if (k === 'e') setEditor(editor.hidden);
      else if (k === 'p') save('png');
      else return;
      e.preventDefault();
    });

    window.addEventListener('hashchange', () => {
      const h = readHash();
      if (h != null && h !== edition) go(h);
    });

    let resizeTimer = 0;
    let last = '';
    new ResizeObserver(() => {
      const { W, H } = size();
      const key = W + 'x' + H;
      if (key === last) return;
      last = key;
      clearTimeout(resizeTimer);
      if (current) resizeTimer = setTimeout(() => render(false), 80);
    }).observe(stage);

    let fontTimer = 0;
    document.fonts.addEventListener('loadingdone', () => {
      clearTimeout(fontTimer);
      fontTimer = setTimeout(() => { R.measureFonts(); render(false); }, 60);
    });
  }

  async function boot() {
    wire();
    setInvert(inverted);
    await Promise.race([
      Promise.all(['400', '700'].map((w) => document.fonts.load(`${w} 16px ${R.FONT}`, 'Aa国ひ').catch(() => null))),
      new Promise((r) => setTimeout(r, 2500)),
    ]);
    R.measureFonts();
    const h = readHash();
    edition = h != null ? h : 417;
    await render(false);
  }

  boot();
})(window.RASTER);
