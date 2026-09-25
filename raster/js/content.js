/* RASTER — content. Samples: a fictional season at a fictional hall, in Japanese and English.
   A "doc" holds everything the viewer can edit; editions only decide the composition. */
(function (R) {
  'use strict';

  R.MOTIFS = ['zahl', 'drei', 'bogen', 'kreis', 'takt', 'senkrecht', 'diagonale'];
  R.MOTIF_INFO = {
    zahl: { name: '数字', gloss: '数字と、重ね刷りの赤い太陽' },
    drei: { name: '三つの文字', gloss: 'ひとつの言葉を漢字・かな・ラテン文字で' },
    bogen: { name: '弧', gloss: '同心の四分円弧' },
    kreis: { name: '円と月', gloss: '円盤、月、底辺に渡る言葉' },
    takt: { name: '拍子', gloss: '拍子記号と小節の棒' },
    senkrecht: { name: '縦', gloss: '帯を昇る言葉と網点の場' },
    diagonale: { name: '斜線', gloss: '回転した棒の帯' },
  };

  /* Which words each motif sets. */
  R.MOTIF_WORDS = {
    zahl: ['numeral', 'gloss'],
    drei: ['three'],
    bogen: ['word', 'gloss'],
    kreis: ['word', 'gloss'],
    takt: ['signature', 'gloss'],
    senkrecht: ['word', 'gloss'],
    diagonale: ['word', 'gloss'],
  };

  const DEFAULT_WORDS = { numeral: '7', three: ['光', 'ひかり', 'Light'], word: '響', gloss: '(resonance)', signature: '7/8' };
  const HALL = { ja: 'ラスター音楽堂 大ホール', en: 'Raster Hall, Main Auditorium' };
  const EVENING = { ja: '開演 19:00（開場 18:30）', en: 'Doors 6.30 pm, starts 7 pm' };

  const GROUPS = { '3/4': [1, 1, 1], '5/8': [3, 2], '7/8': [2, 2, 3], '6/8': [3, 3], '9/8': [2, 2, 2, 3], '5/4': [3, 2] };
  R.grouping = function (sig) {
    if (GROUPS[sig]) return GROUPS[sig];
    const n = +sig.split('/')[0];
    if (n <= 4) return Array(n).fill(1);
    const out = [];
    let left = n;
    while (left > 3) { out.push(2); left -= 2; }
    out.push(left);
    return out;
  };

  const SAMPLES = {
    zahl: (rng) => rng.pick([
      { words: { numeral: '7', gloss: '(seven nights)' }, ja: '打楽器のための七夜', en: 'Seven Nights for Percussion',
        bja: 'ひとつのアンサンブル、ひとつのホール、一週間。毎晩ただ一打から始まり、最後の残響がホールを去ったところで終わります。',
        ben: 'One ensemble, one hall, one week. Each night begins with a single stroke and ends when the last resonance has left the room.' },
      { words: { numeral: '12', gloss: '(twelve keys)' }, ja: '十二の前奏曲', en: 'Twelve Preludes',
        bja: '十二の調による十二の小品を、ひと晩で。曲間も客席の照明は落としません。出入りはいつでも自由です。',
        ben: 'Twelve short pieces in twelve keys, played in one evening. The house lights stay up between preludes; come and go as you like.' },
      { words: { numeral: '3', gloss: '(premieres)' }, ja: '三つの初演', en: 'Three Premieres',
        bja: 'このホールとその響きのために書かれた、室内オーケストラのための新作三曲。終演後、作曲家によるトークがあります。',
        ben: 'Three new works for chamber orchestra, written for this hall and its acoustics. The composers speak after the concert.' },
    ]),

    drei: (rng) => {
      const w = rng.pick([['光', 'ひかり', 'Light'], ['声', 'こえ', 'Voice'], ['水', 'みず', 'Water'], ['音', 'おと', 'Sound'], ['夜', 'よる', 'Night'], ['色', 'いろ', 'Colour']]);
      return {
        words: { three: w }, ja: 'ひとつの言葉、三つの文字', en: 'One Word, Three Scripts',
        venue: { ja: 'ラスター音楽堂 展示室1–3', en: 'Raster Hall, Galleries 1–3' },
        time: { ja: '10:00–18:00（月曜休館）', en: '10 am – 6 pm, closed Mondays' },
        bja: `漢字、ひらがな、ラテン文字。展覧会は「${w[0]}」という一語を三つの文字で書き分け、かたちが変わると言葉の手ざわりがどう変わるかをたどります。`,
        ben: `Kanji, hiragana and the Latin alphabet. The exhibition writes the word “${w[2].toLowerCase()}” in three scripts and follows how its feel changes with its shape.`,
      };
    },

    bogen: (rng) => rng.pick([
      { words: { word: '響', gloss: '(resonance)' }, ja: '交響曲全曲演奏会', en: 'The Complete Symphonies',
        bja: '九つの交響曲を作曲順に、四夜にわたって演奏します。各公演の前に、ホワイエで短い解説があります。',
        ben: 'All nine symphonies in the order they were written, across four evenings. A short introduction in the foyer before each concert.' },
      { words: { word: 'echo', gloss: '（こだま）' }, ja: '四隅の弦楽四重奏', en: 'Quartets in Four Corners',
        bja: '四つの弦楽四重奏団が、ホールの四隅で同時に演奏します。客席はその中央に。声部が空間で重なり合うのを聴いてください。',
        ben: 'Four string quartets play at once from the four corners of the hall. The audience sits between them and hears the voices overlap.' },
    ]),

    kreis: (rng) => rng.pick([
      { words: { word: '月蝕', gloss: '(eclipse)' }, ja: '月蝕のための音楽', en: 'Music for an Eclipse',
        venue: { ja: 'ラスター音楽堂 中庭（雨天時は大ホール）', en: 'Raster Hall courtyard (main hall if it rains)' },
        time: { ja: '開演 21:30', en: 'Starts 9.30 pm' },
        bja: '月蝕の始まりから終わりまで、ちょうどその長さだけ続く野外コンサート。最初の影から、最後の光まで。',
        ben: 'An open-air concert that lasts exactly as long as the eclipse itself: from the first shadow to the last light.' },
      { words: { word: 'ORBIT', gloss: '（軌道）' }, ja: '声のプラネタリウム', en: 'A Planetarium of Voices',
        venue: { ja: 'ラスター音楽堂 ドームホール', en: 'Raster Hall, Dome' },
        bja: '十二人の歌い手が、決められた軌道を描いて客席のまわりを巡ります。近づく者は大きく歌い、遠ざかる者は黙ります。',
        ben: 'Twelve singers circle the audience on fixed orbits. Whoever comes closer sings louder; whoever moves away falls silent.' },
      { words: { word: '満月', gloss: '(full moon)' }, ja: '満月の歌曲の夕べ', en: 'Songs for a Full Moon',
        venue: { ja: 'ラスター音楽堂 小ホール', en: 'Raster Hall, Small Auditorium' },
        bja: '満月の夜にだけ開かれる歌曲の夕べ。日程は季節ではなく、暦に従います。',
        ben: 'A song recital held only on nights of the full moon. The dates follow the calendar, not the season.' },
    ]),

    takt: (rng) => {
      const sig = rng.pick(['3/4', '5/8', '7/8', '6/8', '9/8', '5/4']);
      const [n, d] = sig.split('/');
      return {
        words: { signature: sig, gloss: `(${R.grouping(sig).join('+')})` }, ja: 'リズム工房', en: 'Rhythm Workshop',
        venue: { ja: 'ラスター音楽堂 リハーサル室', en: 'Raster Hall, Rehearsal Room' },
        time: { ja: '14:00–17:00', en: '2 – 5 pm' },
        bja: `${d}分の${n}拍子にとどまりたい人も、あえて外れたい人も歓迎する五日間の午後。経験は問いません。楽器はこちらで用意します。`,
        ben: `Five afternoons for anyone who wants to stay in ${sig} time, or fall out of it on purpose. No experience needed; instruments provided.`,
      };
    },

    senkrecht: (rng) => {
      const [word, gloss] = rng.pick([['高層', '(high-rise)'], ['塔', '(tower)'], ['階段', '(stairs)'], ['UPWARD', '（上へ）']]);
      return {
        words: { word, gloss }, ja: '建築連続講義 高さについて', en: 'Lectures on Building Tall',
        venue: { ja: 'ラスター音楽堂 講堂', en: 'Raster Hall, Lecture Theatre' },
        time: { ja: '毎週火曜 18:30', en: 'Tuesdays, 6.30 pm' }, free: true,
        bja: '階段、昇降路、荷重、そして上からの眺め。高さをつくることをめぐる六回の講義です。各回、講師との対話つき。',
        ben: 'Stairs, shafts, loads and the view from the top: six evenings on building upwards, each followed by a conversation with the speaker.',
      };
    },

    diagonale: (rng) => rng.pick([
      { words: { word: '舞', gloss: '(dance)' }, ja: '対角線のダンス', en: 'Dance on the Diagonal',
        bja: '十二人のダンサーが、ホールを対角線上だけで横切り続けるコレオグラフィー。上演時間約50分、休憩なし。',
        ben: 'A choreography for twelve dancers who cross the hall only ever on the diagonal. About 50 minutes, no interval.' },
      { words: { word: 'oblique', gloss: '（斜め）' }, ja: '斜めの音楽', en: 'Oblique Music',
        bja: 'ずれた入り、斜めの音程、解決しない旋律。ホール専属アンサンブルによる、逆目の作品集。',
        ben: 'Offset entries, slanted intervals, lines that never resolve: works against the grain, played by the house ensemble.' },
    ]),
  };

  const iso = (y, m, d) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

  function price(rng, free) {
    if (free) return { ja: '入場無料（予約不要）', en: 'Free admission' };
    const p = rng.pick([2500, 3000, 3500, 4000]);
    const f = (n) => n.toLocaleString('en-US');
    return { ja: `一般 ${f(p)}円／学生 ${f(p / 2)}円`, en: `¥${f(p)}, students ¥${f(p / 2)}` };
  }

  /* A complete, editable doc for one motif. Always consumes the same random draws. */
  R.sample = function (motif, rng) {
    const s = SAMPLES[motif](rng);
    const mo = rng.int(1, 12);
    const d1 = rng.int(1, 20);
    const span = rng.pick([0, 0, 2, 4, 6, 8]);
    return {
      kicker: { ja: 'ラスター音楽堂 主催', en: 'Presented by Raster Hall' },
      title: { ja: s.ja, en: s.en },
      body: { ja: s.bja, en: s.ben },
      dates: { start: iso(2027, mo, d1), end: span ? iso(2027, mo, d1 + span) : '' },
      time: s.time || EVENING,
      venue: s.venue || HALL,
      price: price(rng, s.free),
      words: Object.assign(JSON.parse(JSON.stringify(DEFAULT_WORDS)), s.words),
    };
  };

  /* ---------- dates, Japanese and English ---------- */
  const WD = ['日', '月', '火', '水', '木', '金', '土'];
  const MONTH_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function parse(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
    if (!m) return null;
    const d = new Date(+m[1], +m[2] - 1, +m[3]);
    return isNaN(d) ? null : { y: +m[1], m: +m[2], d: +m[3], wd: WD[d.getDay()] };
  }
  R.formatDates = function (dates) {
    const a = parse(dates.start);
    let b = parse(dates.end);
    if (!a) return { ja: '', en: '', short: '—' };
    if (b && b.y === a.y && b.m === a.m && b.d === a.d) b = null;
    const jaDay = (x, withYear, withMonth) => `${withYear ? x.y + '年' : ''}${withMonth ? x.m + '月' : ''}${x.d}日（${x.wd}）`;
    const enDay = (x, withMonth, withYear) => `${x.d}${withMonth ? ' ' + MONTH_EN[x.m - 1] : ''}${withYear ? ' ' + x.y : ''}`;
    if (!b) return { ja: jaDay(a, true, true), en: enDay(a, true, true), short: `${a.y}.${a.m}.${a.d}` };
    const sameY = a.y === b.y;
    const sameM = sameY && a.m === b.m;
    return {
      ja: `${jaDay(a, true, true)}–${jaDay(b, !sameY, !sameM)}`,
      en: sameM ? `${a.d}–${enDay(b, true, true)}` : `${enDay(a, true, !sameY)} – ${enDay(b, true, true)}`,
      short: sameY ? `${a.y}.${a.m}.${a.d}–${b.m}.${b.d}` : `${a.y}.${a.m}.${a.d}–${b.y}.${b.m}.${b.d}`,
    };
  };

  /* ---------- what the poster sets: the doc plus derived lines ---------- */
  const VALID = {
    numeral: (v) => typeof v === 'string' && v.trim().length > 0 && Array.from(v.trim()).length <= 4,
    three: (v) => Array.isArray(v) && v.length === 3 && v.every((w) => typeof w === 'string' && w.trim()),
    signature: (v) => /^\d{1,2}\/\d{1,2}$/.test((v || '').trim()) && +v.split('/')[0] > 0,
    word: (v) => typeof v === 'string' && v.trim().length > 0,
    gloss: (v) => typeof v === 'string',
  };
  R.validWord = (key, v) => VALID[key](v);

  R.programme = function (doc, sample, motif, rng, edition, edited) {
    const no = String(edition).padStart(4, '0');
    const words = {};
    for (const key of Object.keys(VALID)) {
      const v = doc.words && doc.words[key];
      const use = VALID[key](v) ? v : sample.words[key];
      words[key] = Array.isArray(use) ? use.map((w) => w.trim()) : use.trim();
    }
    const credit = `WELTFORMAT F4 · 895 × 1280 MM · 2色刷 赤・墨 · RASTER EDITION ${no}`;
    return Object.assign({}, doc, {
      no,
      words,
      date: R.formatDates(doc.dates || {}),
      panel: rng.chance(0.3),
      caption: edited ? credit : `${credit} · 架空のプログラムです — A FICTIONAL PROGRAMME`,
    });
  };
})((window.RASTER = window.RASTER || {}));
