/* auto_movie — the page: a request slip that makes a film on the owner's PC (through /api/movie), the film when it is done, and a sample.
   Everything bilingual is written twice, <span lang="ja"> and <span lang="en">; <html lang> picks one (#en). */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* Japanese has no spaces: keep each phrase (up to ・ 、 。) in one piece so a line never breaks inside "1か月後" or "はみ出し" */
  const ph = (t) => (String(t ?? '').match(/[^・、，。！？!?]+[・、，。！？!?」）』]*|[・、，。！？!?]+/g) || []).map((x) => `<span class="ph">${esc(x)}</span>`).join('');
  const two = (o) => `<span lang="ja">${ph(o.ja)}</span><span lang="en">${esc(o.en || o.ja)}</span>`;
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  const clock = (ms) => { const s = Math.max(0, Math.floor(ms / 1000)); return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; };
  const mb = (b) => `${Math.round(b / 1e6)} MB`;
  const STYLE = { 'podcast-duo': { ja: '二人ポッドキャスト', en: 'two-voice podcast' }, monologue: { ja: 'モノローグ', en: 'monologue' }, entertainment: { ja: 'エンタメ', en: 'entertainment' } };
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- language: #en ---------- */
  const PLACEHOLDER = {
    ja: { theme: '例：三日坊主をやめる工夫', notes: '数字や出典など、動画に入れたいことがあれば。なければ、一般に確かなことだけで組み立てます。' },
    en: { theme: 'e.g. 三日坊主をやめる工夫 (best written in Japanese)', notes: 'Numbers or sources you want in the film. Left empty, only well-established facts are used.' },
  };
  const setLang = (l, push) => {
    document.documentElement.lang = l;
    $$('.lang button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.l === l)));
    const ph_ = PLACEHOLDER[l] || PLACEHOLDER.ja;                       // placeholders cannot be switched by CSS
    if ($('#theme')) { $('#theme').placeholder = ph_.theme; $('#notes').placeholder = ph_.notes; }
    if (push) history.replaceState(null, '', location.pathname + location.search + (l === 'en' ? '#en' : ''));
    fitTitles();
  };
  $$('.lang button').forEach((b) => b.addEventListener('click', () => setLang(b.dataset.l, true)));
  addEventListener('hashchange', () => setLang(/#en\b/.test(location.hash) ? 'en' : 'ja'));

  /* ---------- big titles: as large as their column allows ---------- */
  function fitTitles() {
    $$('.hero').forEach((hero) => {
      const box = $('.titles', hero);
      const h = box && [...box.querySelectorAll('.title')].find((x) => getComputedStyle(x).display !== 'none');
      if (!h) return;
      h.style.setProperty('--fs', '100px');
      const widest = Math.max(1, ...[...h.querySelectorAll('.ln')].map((l) => l.getBoundingClientRect().width));
      h.style.setProperty('--fs', `${Math.max(26, Math.min(+hero.dataset.max || 170, (100 * box.getBoundingClientRect().width) / widest * 0.985))}px`);
    });
  }
  addEventListener('resize', fitTitles);
  document.fonts?.ready.then(fitTitles);

  /* a two-line title for the big type, broken at a word boundary near the middle (same rules as auto_movie's title card) */
  function splitTitle(title) {
    const t = String(title).trim();
    const m = t.match(/^(.+?[、,，。！？!?：:])(.+)$/);
    if (m && m[2].length >= 2) return [m[1], m[2]];
    if (t.length <= 9) return [t];
    const bounds = new Set();
    let acc = 0;
    for (const w of new Intl.Segmenter('ja', { granularity: 'word' }).segment(t)) { acc += w.segment.length; bounds.add(acc); }
    const numSym = (c) => /[0-9０-９%％〜~\-.,:/+]/.test(c);
    let best = null;
    for (const pos of bounds) {
      if (pos <= 1 || pos >= t.length - 1 || /[、。！？」）]/.test(t[pos]) || (numSym(t[pos - 1]) && numSym(t[pos])) || !/[一-鿿゠-ヿA-Za-z0-9]/.test(t[pos])) continue;
      const score = Math.abs(pos - (t.length - pos)) - (/[はがをにでとのもへ]/.test(t[pos - 1]) ? 0.75 : 0);
      if (!best || score < best.score) best = { pos, score };
    }
    const cut = best ? best.pos : Math.ceil(t.length / 2);
    return [t.slice(0, cut), t.slice(cut)];
  }

  /* ================= an episode: title, player, chapters (the sample and a made film share this) ================= */
  const sec = (i, label, body, cls = '') => `<section class="sec ${cls}"><h2><span class="i">${i}</span>${two(label)}</h2><div class="body">${body}</div></section>`;

  function heroHTML(ep, { tag = 'h2', max = 130, kicker }) {
    const lines = (l) => ep.titleLines?.[l] || ep.titleLines?.ja || splitTitle(ep.title[l] || ep.title.ja);
    return `<section class="hero ep-hero" data-max="${max}">
      <div class="titles">${['ja', 'en'].map((l) => `<${tag} class="title" lang="${l}" aria-label="${esc(ep.title[l] || ep.title.ja)}">${lines(l).map((t) => `<span class="ln"><span>${esc(t)}</span></span>`).join('')}</${tag}>`).join('')}</div>
      <aside>
        <p class="kicker">${kicker}</p>
        <p class="sub">${two(ep.subtitle)}</p>
        <p class="meta">${ep.width}×${ep.height} · ${two(STYLE[ep.style] || { ja: ep.style, en: ep.style })}<br>${two({ ja: '音声は日本語です', en: 'Narrated in Japanese' })}</p>
      </aside>
    </section>`;
  }

  function chaptersHTML(ep, index) {
    const row = (c) => `<span class="t">${mmss(c.t)}</span><span class="name"><span>${esc(c.title)}</span></span>`;
    return sec(index, { ja: 'チャプター', en: 'Chapters' }, `
      <div class="tochead"><span>${two({ ja: 'クリックでその場面から再生', en: 'Click to play from a scene' })}</span></div>
      <div class="prog" aria-hidden="true"><i class="progbar"></i>${ep.chapters.slice(1).map((c) => `<b style="left:${((c.t / ep.seconds) * 100).toFixed(3)}%"></b>`).join('')}</div>
      <ol class="toc">${ep.chapters.map((c, i) => `<li data-i="${i}"><button type="button" data-t="${c.t}">${row(c)}</button></li>`).join('')}</ol>`);
  }

  function episodeHTML(ep, o) {
    return `${heroHTML(ep, o)}<div class="rule"></div><div class="band"><div class="stage"></div></div><p class="note" hidden></p>${chaptersHTML(ep, o.index || '01')}`;
  }

  /* the player: the poster and a play button; a click loads the <video> (which streams from /media with byte ranges, so chapters can seek) */
  function mountEpisode(root, ep) {
    const stage = $('.stage', root), note = $('.note', root), bar = $('.progbar', root), items = $$('.toc li', root);
    const src = ep.files.video, poster = ep.files.poster;
    let video = null;
    stage.innerHTML = `<img class="poster" src="${esc(poster)}" alt="" width="1280" height="720" decoding="async"><button class="playbtn" type="button"><span class="sr">${two({ ja: '再生', en: 'Play' })}</span></button><span class="len">${mmss(ep.seconds)}</span>`;
    const tick = () => {
      const t = video?.currentTime || 0;
      bar.style.width = `${Math.min(100, (t / ep.seconds) * 100)}%`;
      let cur = 0;
      ep.chapters.forEach((c, i) => { if (t + 0.05 >= c.t) cur = i; });
      items.forEach((li, i) => li.classList.toggle('on', video ? i === cur : false));
    };
    const start = (t = 0) => {
      if (video) { video.currentTime = t; video.play().catch(() => {}); return; }
      video = document.createElement('video');
      video.controls = true; video.playsInline = true; video.preload = 'auto'; video.poster = poster;
      video.setAttribute('aria-label', ep.title.ja);
      video.addEventListener('loadedmetadata', () => { if (t) video.currentTime = t; }, { once: true });
      video.addEventListener('timeupdate', tick);
      video.addEventListener('seeked', tick);
      video.addEventListener('error', () => {
        note.hidden = false;
        note.innerHTML = `${two({ ja: 'この動画を再生できませんでした。', en: 'The film could not be played.' })} <a href="${esc(src)}?download=1">${two({ ja: 'ダウンロードして見る', en: 'Download it instead' })}</a>`;
      });
      video.src = src;
      stage.replaceChildren(video);
      video.play().catch(() => {});
    };
    $('.playbtn', stage).addEventListener('click', () => start(0));
    $('.toc', root).addEventListener('click', (e) => {
      const b = e.target.closest('button[data-t]');
      if (!b) return;
      start(+b.dataset.t);
      stage.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'nearest' });
    });
    return { start, stage };
  }

  /* ================= the sample: what a finished film looks like, with its numbers ================= */
  function sampleHTML(ep) {
    const q = ep.qa, F = ep.files;
    let checks = '';
    if (q) {
      const f = [];
      f.push({ n: (q.measuredSec ?? ep.seconds).toFixed(3), u: { ja: '秒', en: 's' }, l: { ja: `指定の ${mmss(q.targetSec)} ちょうど。映像と音声も同じ長さ。`, en: `Exactly the ${mmss(q.targetSec)} that was asked for — picture and sound the same length.` } });
      if (q.overlaps != null) f.push({ n: String(q.overlaps), u: { ja: '件', en: '' }, l: { ja: `声の重なり。${q.lines} 行のうち、いちばん近い二つでも ${q.minGapSec} 秒あく。`, en: `Overlapping voices. Of ${q.lines} lines, even the closest pair is ${q.minGapSec} s apart.` } });
      if (q.textContrast) f.push({ n: `${q.textContrast.pass}/${q.textContrast.total}`, u: { ja: '', en: '' }, l: { ja: '画面の文字が WCAG AA のコントラストに合格。はみ出し・重なりも 0 件。', en: 'On-screen text passes WCAG AA contrast, with no overflow or overlaps.' } });
      if (q.lufs != null) f.push({ n: q.lufs.toFixed(1), u: { ja: 'LUFS', en: 'LUFS' }, l: { ja: `音量をそろえ、声は BGM より ${q.voiceOverMusicDb ?? '—'} dB 大きい。`, en: `Loudness levelled; the voices sit ${q.voiceOverMusicDb ?? '—'} dB above the music.` } });
      checks = sec('02', { ja: '検証', en: 'Checks' }, `
        <div class="figs">${f.map((x) => `<div class="fig"><p class="n">${esc(x.n)}${x.u.ja || x.u.en ? `<small>${two(x.u)}</small>` : ''}</p><p class="l">${two(x.l)}</p></div>`).join('')}</div>
        <p class="verdict"><b>${q.passed}/${q.checks} ${two({ ja: '項目 合格', en: 'checks passed' })}</b><span>${two({ ja: '書き出したあと、自動で検査しています（長さ・声の重なり・音量・字幕・静止画面・場面ごとの初めの絵）。', en: 'Checked automatically after rendering — length, overlaps, loudness, captions, frozen frames, time to first visual.' })}</span></p>`);
    }

    const steps = [
      ['企画', 'Plan', 'スタイルを決め、事実を整理し、シーンに割る', 'Picks the style, sorts out the facts, splits the scenes'],
      ['台本', 'Script', 'セリフと画面の演出を JSON で書き、検証して差し戻す', 'Lines and on-screen cues as JSON — validated, and sent back if flawed'],
      ['絵', 'Draw', 'シーンごとに SVG の挿絵を描き、一本ずつ描き足す', 'One SVG illustration per scene, drawn in stroke by stroke'],
      ['声', 'Voice', 'VOICEVOX で 1 行ずつ合成し、口の形まで取る', 'VOICEVOX speaks every line; mouth shapes follow the phonemes'],
      ['尺合わせ', 'Fit', '実測の声の長さで話速を調整。合わなければ台本を書き直す', 'Tempo is tuned to the measured voices; the script is rewritten if it will not fit'],
      ['音', 'Score', 'ピアノ中心の BGM をコードで作曲・演奏し、声の下で下げる', 'Piano-led music composed and played in code, ducked under the voices'],
      ['画面', 'Compose', 'すべてを HyperFrames の 1 本のタイムラインに組む', 'Everything becomes one HyperFrames timeline'],
      ['書き出し', 'Render', '1 フレームずつ描いて MP4 にする', 'Rendered frame by frame into an MP4'],
      ['検査', 'Check', '尺・重なり・音量・字幕・静止を自動で調べる', 'Length, overlaps, loudness, captions and freezes are checked'],
    ];
    const how = sec('03', { ja: 'つくりかた', en: 'How it is made' }, `
      <p class="lead">${two({ ja: 'テーマ、長さ、参考資料を渡すと、ここまでを自動で行います。上の「つくる」を押すと、あなたのテーマでも同じ流れが動きます。', en: 'Give it a theme, a length and some reference material and it does all of this by itself. The request slip above sets the same steps going for your theme.' })}</p>
      <ol class="steps" style="margin-top:clamp(20px,3vw,40px)">${steps.map((s, i) => `<li><span class="k">${String(i + 1).padStart(2, '0')}</span><h3>${two({ ja: s[0], en: s[1] })}<em>${esc(s[1])}</em></h3><p>${two({ ja: s[2], en: s[3] })}</p></li>`).join('')}</ol>
      ${ep.build && (ep.build.minutes || ep.build.llmUsd) ? `<p class="verdict"><b>${two({ ja: 'このサンプルの実績', en: 'This sample' })}</b><span>${ep.build.minutes ? two({ ja: `テーマから書き出しまで約 ${ep.build.minutes} 分`, en: `about ${ep.build.minutes} minutes from theme to render` }) : ''}${ep.build.minutes && ep.build.llmUsd ? ' · ' : ''}${ep.build.llmUsd ? two({ ja: `LLM の費用は約 $${ep.build.llmUsd.toFixed(2)}`, en: `LLM cost about $${ep.build.llmUsd.toFixed(2)}` }) : ''}</span></p>` : ''}`);

    const plates = (F.storyboard || F.audio) ? sec('04', { ja: '絵コンテと音', en: 'Storyboard & sound' }, `
      ${F.storyboard ? `<figure class="plate"><a href="${esc(F.storyboard)}" target="_blank" rel="noopener"><img src="${esc(F.storyboard)}" alt="" width="1800" loading="lazy" decoding="async"></a><figcaption>${two({ ja: '絵コンテ。タイトルと、場面ごとの描き終わったときの絵。', en: 'Storyboard — the title card and each scene as it looks once its drawing is complete.' })}</figcaption></figure>` : ''}
      ${F.audio ? `<figure class="plate"><a href="${esc(F.audio)}" target="_blank" rel="noopener"><img src="${esc(F.audio)}" alt="" width="1800" loading="lazy" decoding="async"></a><figcaption>${two({ ja: '音のようす。上の段は誰がいつ話したか（黒がミオ、赤がノノ）。重なりはなく、声・BGM・効果音の音量が場面ごとに動いていきます。', en: 'The sound — who speaks when (black: Mio, red: Nono) with no overlaps, and how voice, music and effects move scene by scene.' })}</figcaption></figure>` : ''}`) : '';

    const facts = ep.facts?.length ? sec('05', { ja: '根拠', en: 'Facts' }, `
      <ul class="facts">${ep.facts.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>
      <p>${two({ ja: '数字や固有名詞は、渡した参考資料にあるものだけを使うよう指示し、資料にない断定は避けています。', en: 'Numbers and names come only from the reference material that was supplied; claims beyond it are avoided.' })}</p>`) : '';

    const rows = [
      [{ ja: '動画', en: 'Video' }, `${ep.width}×${ep.height} · H.264 · AAC`, mb(ep.bytes), `${F.video}?download=1`, '↓'],
      F.captions && [{ ja: '字幕', en: 'Subtitles' }, 'SRT', '.srt', F.captions, '↓'],
      F.score && [{ ja: '楽譜', en: 'Score' }, `${two({ ja: 'BGM の演奏データ', en: 'the music as played' })} · MIDI`, '.mid', F.score, '↓'],
      F.script && [{ ja: '台本', en: 'Script' }, `${two({ ja: 'セリフと演出', en: 'lines and cues' })} · JSON`, '.json', F.script, '↓'],
    ].filter(Boolean);
    const files = sec('06', { ja: 'ファイル', en: 'Files' }, `<div class="files">${rows.map(([l, m, size, h, arrow]) => `<a href="${esc(h)}" download><b>${two(l)}</b><span>${m}</span><i>${esc(size)} ${arrow}</i></a>`).join('')}</div>`);

    const credits = sec('07', { ja: 'クレジット', en: 'Credits' }, `
      <div class="credits"><dl>
        <dt>${two({ ja: '声', en: 'VOICES' })}</dt><dd>VOICEVOX:四国めたん / VOICEVOX:ずんだもん　<a href="https://voicevox.hiroshiba.jp/" target="_blank" rel="noopener">voicevox.hiroshiba.jp</a></dd>
        <dt>${two({ ja: '絵', en: 'ART' })}</dt><dd>${two({ ja: 'Claude Opus 5.5 が SVG で描いた挿絵と、この作品のために描き下ろしたキャスト（公式の立ち絵ではありません）', en: 'Illustrations drawn as SVG by Claude Opus 5.5, and cast portraits drawn for this piece (not the official character art)' })}</dd>
        <dt>${two({ ja: '音楽', en: 'MUSIC' })}</dt><dd>${two({ ja: 'サンプルを使わず、コードで作曲・演奏したピアノ中心の BGM と効果音', en: 'Piano-led music and sound effects composed and played in code, with no samples' })}</dd>
        <dt>${two({ ja: '映像', en: 'PICTURE' })}</dt><dd><a href="https://github.com/heygen-com/hyperframes" target="_blank" rel="noopener">HyperFrames</a> ${two({ ja: 'で HTML から書き出し。フォントは Noto Sans CJK JP（SIL OFL）', en: 'renders HTML to video. Font: Noto Sans CJK JP (SIL OFL)' })}</dd>
      </dl></div>`);

    const kicker = `<span>${two(ep.series.name)}</span><span class="no">No.${esc(ep.id)} · ${mmss(ep.seconds)}</span>`;
    return `<div class="sample-head"><span>Sample</span><span>${two({ ja: 'サンプル — できあがりの例', en: 'a sample of what comes out' })}</span></div>
      <div class="ep" id="sampleEp">${episodeHTML(ep, { tag: 'h2', max: 120, kicker })}</div>${checks}${how}${plates}${facts}${files}${credits}`;
  }

  fetch('videos.json').then((r) => r.json()).then((db) => {
    const ep = db.episodes[0];
    if (!ep) return;
    $('#sample').innerHTML = sampleHTML(ep);
    mountEpisode($('#sampleEp'), ep);
    setLang(/#en\b/.test(location.hash) ? 'en' : 'ja');
    window.AUTO_MOVIE = { ...(window.AUTO_MOVIE || {}), sample: ep };
  }).catch((e) => { $('#sample').innerHTML = `<p style="margin:3em var(--gut)">videos.json: ${esc(e.message)}</p>`; });

  /* ================= the request slip ================= */
  const form = $('#req'), themeEl = $('#theme'), notesEl = $('#notes'), passEl = $('#pass'), goBtn = $('#go'), statusEl = $('#status');
  const workEl = $('#work'), clockEl = $('#clock'), workTitle = $('#workTitle'), madeEl = $('#made');
  const KEY = 'auto-movie-job-v1';
  const store = {
    get() { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; } },
    set(v) { try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY); } catch { /* storage blocked */ } },
  };
  const ERR = {
    passphrase: { ja: '合言葉がちがうようです。', en: 'That passphrase is not right.' },
    theme: { ja: 'テーマは2〜60文字。記号の < > { } ` \\ は使えません。', en: 'The theme must be 2–60 characters, without < > { } ` \\.' },
    minutes: { ja: '長さを選んでください。', en: 'Please pick a length.' },
    notes: { ja: '事実のメモは1,500文字までです。', en: 'The facts can be up to 1,500 characters.' },
    too_large: { ja: '内容が長すぎます。', en: 'That is too long.' },
    slow_down: { ja: '少し間をおいてから、もう一度どうぞ。', en: 'Please wait a moment and try again.' },
    daily_limit: { ja: '今日の受付は終わりました（1日3本まで）。また明日どうぞ。', en: 'Today\'s requests are used up (three a day). Please come back tomorrow.' },
    jobs_unavailable: { ja: 'いまは受付につながりません。しばらくしてから、もう一度どうぞ。', en: 'The request desk is unreachable right now. Please try again later.' },
    offline: { ja: 'ここでは受付を使えません。公開しているページから試してください。', en: 'Requests are not available here. Please use the published page.' },
  };
  let job = null, timer = 0, ticker = 0, busy = false;

  const say = (pair, kind = '') => { statusEl.innerHTML = pair ? two(pair) : ''; statusEl.dataset.kind = kind; };
  const beforeHours = () => +new Intl.DateTimeFormat('en-GB', { hour: 'numeric', hourCycle: 'h23', timeZone: 'Asia/Tokyo' }).format(new Date()) < 8;
  function setBusy(on) {
    busy = on;
    goBtn.disabled = on;
    workEl.hidden = !on;
    form.classList.toggle('busy', on);
    clearInterval(ticker);
    if (on) { const paint = () => { clockEl.textContent = clock(Date.now() - job.at); }; paint(); ticker = setInterval(paint, 1000); }
  }
  const counters = () => { $('#themeCount').textContent = `${[...themeEl.value].length} / 60`; $('#notesCount').textContent = `${[...notesEl.value].length} / 1500`; };
  themeEl.addEventListener('input', counters);
  notesEl.addEventListener('input', counters);
  $('#chips').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { themeEl.value = b.textContent; counters(); passEl.focus(); } });

  function sayWorking(waiting) {
    const p = waiting ? { ja: `順番を待っています。${beforeHours() ? '受付時間の前なので、朝8時から順につくります。' : ''}`, en: `Waiting in line.${beforeHours() ? ' It is before opening hours, so it starts at 8 a.m. JST.' : ''}` }
      : { ja: 'いま、つくっています。', en: 'Making it now.' };
    workTitle.innerHTML = two(p);
    say({ ja: '受け付けました。このページを閉じても大丈夫です。', en: 'Received. You can close this page.' });
  }

  /* the film is done: the big title, the player, the chapters, and ways to keep it */
  function showMade(m, id) {
    const ep = {
      id, title: { ja: m.title }, subtitle: { ja: m.subtitle }, seconds: m.seconds, width: m.width, height: m.height, style: m.style,
      chapters: m.chapters, files: { video: m.video, poster: m.poster }, bytes: m.bytes,
    };
    const url = `${location.origin}${location.pathname}?v=${encodeURIComponent(id)}`;
    const kicker = `<span>${two({ ja: 'できあがり', en: 'Your film' })}</span><span class="no">${mmss(m.seconds)}</span>`;
    madeEl.innerHTML = `<div class="made-head"><span>Made</span><span>${two({ ja: 'あなたのテーマでつくった動画', en: 'the film made from your theme' })}</span></div>
      <div class="ep" id="madeEp">${episodeHTML(ep, { tag: 'h2', max: 150, kicker })}</div>
      <p class="share"><button type="button" id="copyUrl">${two({ ja: 'この動画の URL をコピー', en: 'Copy this film\'s link' })}</button><a href="${esc(m.video)}?download=1" download>${two({ ja: `ダウンロード（${mb(m.bytes)}）`, en: `Download (${mb(m.bytes)})` })}</a><button type="button" id="another">${two({ ja: '別のテーマでつくる', en: 'Make another' })}</button>${m.qa ? `<span>${m.qa.passed}/${m.qa.checks} ${two({ ja: '項目 自動検査に合格', en: 'automatic checks passed' })}</span>` : ''}</p>`;
    madeEl.hidden = false;
    const mounted = mountEpisode($('#madeEp'), ep);
    setLang(document.documentElement.lang);
    document.title = `${m.title} — auto_movie`;
    history.replaceState(null, '', `?v=${encodeURIComponent(id)}${/#en\b/.test(location.hash) ? '#en' : ''}`);
    $('#copyUrl').addEventListener('click', async (e) => {
      try { await navigator.clipboard.writeText(url); e.target.textContent = document.documentElement.lang === 'en' ? 'Copied' : 'コピーしました'; } catch { prompt('URL', url); }
    });
    $('#another').addEventListener('click', () => { form.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'center' }); themeEl.focus({ preventScroll: true }); });
    madeEl.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });
    window.AUTO_MOVIE = { ...(window.AUTO_MOVIE || {}), made: mounted };
  }

  async function poll(first) {
    clearTimeout(timer);
    if (!job || (document.hidden && !first)) return;      // a background tab stops polling until it is visible again
    if (Date.now() - job.at > 60 * 60 * 1000) { setBusy(false); say({ ja: '時間がかかっています。しばらくしてから、このページを開き直してください。', en: 'This is taking a while. Please open the page again later.' }, 'err'); return; }
    let r, data = {};
    try { r = await fetch('/api/movie/' + encodeURIComponent(job.id), { cache: 'no-store' }); data = await r.json().catch(() => ({})); }
    catch { timer = setTimeout(poll, 15000); return; }
    if (r.status === 404) { setBusy(false); job = null; store.set(null); say({ ja: '受付が見つかりませんでした。もう一度どうぞ。', en: 'That request could not be found. Please try again.' }, 'err'); return; }
    if (!r.ok) { timer = setTimeout(poll, 15000); return; }
    if (data.status === 'done' && data.movie) { setBusy(false); say(null); showMade(data.movie, job.id); return; }
    if (data.status === 'failed') { setBusy(false); failed(); return; }
    if (!busy) setBusy(true);
    sayWorking(data.status !== 'making');
    timer = setTimeout(poll, 8000);
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden && busy) poll(); });

  function failed() {
    statusEl.dataset.kind = 'err';
    const more = (job.variant || 0) < 2;
    statusEl.innerHTML = `${two({ ja: 'うまくつくれませんでした。テーマを変えるか、もう一度どうぞ。', en: 'It did not work out. Change the theme, or try once more.' })}${more ? ` <button type="button" id="again">${two({ ja: '同じテーマでもう一度', en: 'Try this theme again' })}</button>` : ''}`;
    $('#again')?.addEventListener('click', () => { if (!passEl.value) { say(ERR.passphrase, 'err'); passEl.focus(); return; } send({ theme: job.theme, minutes: job.minutes, notes: job.notes, variant: (job.variant || 0) + 1 }); });
  }

  async function send({ theme, minutes, notes, variant = 0 }) {
    job = { id: '', theme, minutes, notes, variant, at: Date.now() };
    setBusy(true);   // the clock starts at once; the id arrives with the answer
    workEl.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'nearest' });
    workTitle.innerHTML = two({ ja: '受け付けています…', en: 'Sending…' });
    say(null);
    let r, data = {};
    try {
      r = await fetch('/api/movie', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme, minutes, notes, passphrase: passEl.value, variant }) });
      data = await r.json().catch(() => ({}));
    } catch { setBusy(false); job = null; say(ERR.offline, 'err'); return; }
    if (!r.ok) {
      setBusy(false); job = null;
      say(ERR[data.error] || ([404, 405, 501].includes(r.status) ? ERR.offline : ERR.jobs_unavailable), 'err');
      if (data.error === 'passphrase') passEl.select();
      return;
    }
    job.id = data.id;
    store.set(job);
    madeEl.hidden = true; madeEl.innerHTML = '';
    poll(true);
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (busy) return;
    const theme = themeEl.value.replace(/\s+/g, ' ').trim();
    if (!theme) { say({ ja: 'テーマを書いてください。', en: 'Please write a theme.' }, 'err'); themeEl.focus(); return; }
    if (!passEl.value) { say({ ja: '合言葉を入れてください。', en: 'Please enter the passphrase.' }, 'err'); passEl.focus(); return; }
    send({ theme, minutes: +form.elements.minutes.value, notes: notesEl.value.trim(), variant: 0 });
  });

  /* pick up where the visitor left off (a film stays retrievable for a day), or open a shared link (?v=…) */
  const shared = new URLSearchParams(location.search).get('v');
  const saved = store.get();
  if (shared && /^[A-Za-z0-9-]{1,80}$/.test(shared)) {
    job = { id: shared, theme: '', minutes: 3, at: Date.now() };
    setBusy(true); workTitle.innerHTML = two({ ja: '確かめています…', en: 'Checking…' });
    poll(true);
  } else if (saved && saved.id && Date.now() - saved.at < 24 * 3600 * 1000) {
    job = saved;
    themeEl.value = saved.theme || '';
    counters();
    setBusy(true); workTitle.innerHTML = two({ ja: '前回の受付を確かめています…', en: 'Checking your last request…' });
    poll(true);
  }
  counters();
  setLang(/#en\b/.test(location.hash) ? 'en' : 'ja');
})();
