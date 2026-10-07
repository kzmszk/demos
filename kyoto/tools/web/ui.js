// Overlay UI: title, mode bar (walk / fly), places, season (autumn leaves / snow), sound, brightness, JA/EN.
const T = {
  ja: {
    sub: '秋の夕暮れ、雪の夕暮れ。歩いて、空から。', walk: '歩く', fly: '空から', places: '場所へ', autumn: '紅葉', winter: '雪', sound: '音', credits: 'クレジット', bright: '明るさ',
    help_walk: 'W A S D で歩く ・ ドラッグで見回す ・ Shift で走る',
    help_walk_t: '左下のスティックで歩く ・ ドラッグで見回す',
    more: '設定', up: '上昇', down: '下降', fast: '速く',
    help_fly: 'W A S D・E Q で移動 ・ ドラッグで向き ・ ホイールで速さ',
    help_fly_t: 'スティックで進む ・ ドラッグで向き ・ 右下の ▲▼ で上昇・下降',
    start: 'はじめる', prep: '準備中', prep_data: '京都駅とそのまわりを読み込んでいます', prep_gpu: '描画の準備をしています',
  },
  en: {
    sub: 'An autumn evening, a snowy evening. On foot and from the air.', walk: 'Walk', fly: 'Fly', places: 'Go to', autumn: 'Autumn', winter: 'Snow', sound: 'Sound', credits: 'Credits', bright: 'Brightness',
    help_walk: 'W A S D to walk · drag to look · Shift to run',
    help_walk_t: 'Stick (bottom left) to walk · drag to look',
    more: 'More', up: 'Up', down: 'Down', fast: 'Fast',
    help_fly: 'W A S D · E Q to move · drag to turn · wheel for speed',
    help_fly_t: 'Stick to move · drag to turn · ▲ ▼ (bottom right) to climb and descend',
    start: 'Start', prep: 'Preparing', prep_data: 'Loading Kyoto Station and its surroundings', prep_gpu: 'Getting the graphics ready',
  },
};
// at: [x, y] in the local frame (metres east / north of Kyoto Station's central exit); yaw: radians from east, ccw
export const PLACES = [
  { id: 'station', ja: '京都駅 烏丸口', en: 'Kyoto Station, Karasuma exit', mode: 'walk', at: [-58.0, 66.0], yaw: 0.905, pitch: 0.18 },
  { id: 'tower', ja: '京都タワーを見上げて', en: 'Kyoto Tower', mode: 'walk', at: [10.0, 110.0], yaw: 1.16, pitch: 0.5 },
  { id: 'toji', ja: '東寺 五重塔', en: 'Tō-ji, the five-storey pagoda', mode: 'walk', at: [-930.0, -600.0], yaw: -1.397, pitch: 0.25 },
  { id: 'toji_kujo', ja: '東寺（九条通から）', en: 'Tō-ji from Kujō-dōri', mode: 'walk', at: [-990.0, -709.4], yaw: 0.63, pitch: 0.12, map: { ja: '東寺', en: 'Tō-ji' } },
  { id: 'sanjusangendo', ja: '三十三間堂', en: 'Sanjūsangen-dō', mode: 'walk', at: [1215.0, 160.0], yaw: 2.0, pitch: 0.08 },
  { id: 'sanjusangendo_in', ja: '三十三間堂（堂内）', en: 'Sanjūsangen-dō — the hall', mode: 'walk', at: [1188.3, 205.0], yaw: 1.75, pitch: 0.04, map: { ja: '三十三間堂', en: 'Sanjūsangen-dō' } },
  { id: 'fushimi', ja: '伏見稲荷大社 楼門', en: 'Fushimi Inari Taisha', mode: 'walk', at: [1214.0, -2072.6], yaw: 0.03, pitch: 0.1 },
  { id: 'fushimi_torii', ja: '伏見稲荷 千本鳥居', en: 'Fushimi Inari — the thousand torii', mode: 'walk', at: [1461.0, -2091.6], yaw: -0.71, pitch: 0.02, map: { ja: '伏見稲荷大社', en: 'Fushimi Inari Taisha' } },
  { id: 'tofukuji', ja: '東福寺 通天橋（臥雲橋から）', en: 'Tōfuku-ji, Tsūten-kyō from Gaun-kyō', mode: 'walk', at: [1287.5, -925.8], yaw: -0.266, pitch: 0.07, map: { ja: '東福寺 臥雲橋', en: 'Tōfuku-ji, Gaun-kyō' } },
  { id: 'tofukuji_valley', ja: '東福寺 通天橋から洗玉澗', en: 'Tōfuku-ji, the maple valley from Tsūten-kyō', mode: 'walk', at: [1360.0, -944.4], yaw: 2.813, pitch: -0.12, map: { ja: '通天橋', en: 'Tsūten-kyō' } },
  { id: 'tofukuji_sanmon', ja: '東福寺 三門', en: 'Tōfuku-ji, the Sanmon', mode: 'walk', at: [1362.0, -1150.0], yaw: 1.435, pitch: 0.2, map: { ja: '東福寺', en: 'Tōfuku-ji' } },
  { id: 'kiyomizu', ja: '清水の舞台（奥の院から）', en: 'Kiyomizu-dera, the stage', mode: 'walk', at: [2432.6, 970.4], yaw: 2.72, pitch: -0.05 },
  { id: 'kiyomizu_gate', ja: '清水寺 仁王門', en: 'Kiyomizu-dera, the Niō gate', mode: 'walk', at: [2221.5, 1076.8], yaw: -0.43, pitch: 0.22, map: { ja: '清水寺', en: 'Kiyomizu-dera' } },
  { id: 'yasaka_pagoda', ja: '八坂通から八坂の塔', en: 'Yasaka-dōri and the Yasaka Pagoda', mode: 'walk', at: [1949.6, 1368.5], yaw: 2.653, pitch: 0.07 },
  { id: 'sannenzaka', ja: '産寧坂', en: 'Sannenzaka', mode: 'walk', at: [2021.9, 1187.3], yaw: -1.944, pitch: 0.2 },
  { id: 'ninenzaka', ja: '二年坂', en: 'Ninenzaka', mode: 'walk', at: [2010.0, 1433.6], yaw: -1.517, pitch: 0.07 },
  { id: 'ishibe', ja: '石塀小路', en: 'Ishibe-kōji', mode: 'walk', at: [1888.5, 1585.4], yaw: -1.305, pitch: 0.02 },
  { id: 'hanamikoji', ja: '祇園 花見小路', en: 'Gion, Hanamikōji', mode: 'walk', at: [1482.0, 1990.0], yaw: -1.715, pitch: 0.02 },
  { id: 'shirakawa', ja: '祇園 白川', en: 'Gion, Shirakawa', mode: 'walk', at: [1364.0, 2181.2], yaw: 0.057, pitch: -0.03 },
  { id: 'yasaka', ja: '八坂神社 西楼門', en: 'Yasaka Shrine', mode: 'walk', at: [1690.0, 1989.0], yaw: 0.06, pitch: 0.15 },
  { id: 'eikando', ja: '永観堂 放生池', en: 'Eikandō', mode: 'walk', at: [3277.6, 3126.6], yaw: 1.633, pitch: 0.02 },
  { id: 'ginkakuji', ja: '銀閣寺', en: 'Ginkaku-ji', mode: 'walk', at: [3610.3, 4511.3], yaw: 2.84, pitch: 0.02 },
  { id: 'kinkakuji', ja: '金閣寺', en: 'Kinkaku-ji', mode: 'walk', at: [-2738.4, 5901.8], yaw: 2.129, pitch: 0.06 },
  { id: 'arashiyama', ja: '嵐山 渡月橋', en: 'Arashiyama, Togetsukyō', mode: 'walk', at: [-7394.5, 3058.0], yaw: -1.62, pitch: 0.05 },
  { id: 'arashiyama_street', ja: '嵐山 長辻通', en: 'Arashiyama, Nagatsuji-dōri', mode: 'walk', at: [-7392.0, 3101.0], yaw: 1.824, pitch: 0.03, map: { ja: '長辻通', en: 'Nagatsuji-dōri' } },
  { id: 'bamboo', ja: '竹林の小径', en: 'The bamboo grove path', mode: 'walk', at: [-7790.0, 3532.3], yaw: -2.87, pitch: 0.1 },
  { id: 'nonomiya', ja: '野宮神社 黒木鳥居', en: 'Nonomiya Shrine, the black torii', mode: 'walk', at: [-7720.6, 3531.4], yaw: 1.749, pitch: 0.14, map: { ja: '野宮神社', en: 'Nonomiya Shrine' } },
  { id: 'tenryuji', ja: '天龍寺 曹源池庭園', en: 'Tenryū-ji, the Sōgen pond garden', mode: 'walk', at: [-7775.2, 3316.0], yaw: -2.826, pitch: 0.03, map: { ja: '天龍寺', en: 'Tenryū-ji' } },
  { id: 'jojakkoji', ja: '常寂光寺 仁王門', en: 'Jōjakkō-ji, the Niō gate', mode: 'walk', at: [-8160.0, 3753.6], yaw: 3.11, pitch: 0.19, map: { ja: '常寂光寺', en: 'Jōjakkō-ji' } },
  { id: 'air_arashiyama', ja: '嵐山の空から', en: 'Over Arashiyama', mode: 'fly', at: [-6600.0, 2200.0], z: 350, yaw: 2.356, pitch: -0.22 },
  { id: 'air', ja: '東山の空から', en: 'Over Higashiyama', mode: 'fly', at: [600.0, 300.0], z: 420, yaw: 0.6, pitch: -0.25 },
];

export class UI {
  constructor(app) {
    this.app = app;
    this.lang = window.__lang || ((location.hash === '#en' || (navigator.language || '').slice(0, 2) !== 'ja') && location.hash !== '#ja' ? 'en' : 'ja');
    if (location.hash === '#ja') this.lang = 'ja';
    this.build();
  }
  t(k) { return T[this.lang][k] || k; }
  el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  build() {
    const root = this.root = document.querySelector('.ui');
    const ti = this.title = root.querySelector('.title');
    const sb = this.el('button', 'start'); ti.querySelector('.starts').appendChild(sb);
    sb.onclick = () => this.start('walk');
    ti.querySelectorAll('.lang button').forEach((b) => (b.onclick = () => this.setLang(b.dataset.l)));
    const bar = this.bar = this.el('div', 'bar hidden'); root.appendChild(bar);
    bar.innerHTML = `<div class="grp modes"></div><div class="grp"><select class="places"></select></div><div class="grp seasons"></div>
      <div class="grp right"><label class="br"><span></span><input type="range" min="0.5" max="2.5" step="0.05"></label><button class="snd"></button><button class="lg"></button><a class="cr" href="credits.html" target="_blank"></a></div>`;
    for (const m of ['walk', 'fly']) { const b = this.el('button', 'mode'); b.dataset.m = m; b.onclick = () => this.app.setMode(m); bar.querySelector('.modes').appendChild(b); }
    for (const s of ['autumn', 'winter']) { const b = this.el('button', 'season'); b.dataset.s = s; b.onclick = () => this.app.setSeason(s); bar.querySelector('.seasons').appendChild(b); }
    // a control keeps the keyboard focus after use (WASD went to the place menu or the slider): give it back to the view
    bar.addEventListener('change', (e) => { if (e.target.blur) e.target.blur(); });
    bar.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) b.blur(); });
    bar.querySelector('.places').onchange = (e) => { const p = PLACES.find((x) => x.id === e.target.value); if (p) this.app.goPlace(p); e.target.value = ''; e.target.blur(); };
    bar.querySelector('.snd').onclick = () => this.app.toggleSound();
    bar.querySelector('.lg').onclick = () => this.setLang(this.lang === 'ja' ? 'en' : 'ja');
    const br = bar.querySelector('.br input'); br.value = this.app.bright;
    br.oninput = () => this.app.setBright(+br.value);
    // phones and tablets: one short row (mode, places, ⋯); the rest in a small sheet above it, so nothing lands under
    // the thumbs; in the air, ▲ ▼ to climb and descend and a fast toggle, bottom right
    this.touch = matchMedia('(pointer: coarse)').matches;
    if (this.touch) {
      root.classList.add('touch');
      const more = this.el('button', 'more'); bar.insertBefore(more, bar.querySelector('.seasons'));
      const sheet = this.sheet = this.el('div', 'sheet'); root.appendChild(sheet);
      sheet.appendChild(bar.querySelector('.seasons')); sheet.appendChild(bar.querySelector('.right'));
      more.onclick = () => sheet.classList.toggle('open');
      sheet.addEventListener('click', (e) => { if (e.target.closest('button') && !e.target.closest('.br')) setTimeout(() => sheet.classList.remove('open'), 150); });
      sheet.addEventListener('pointerdown', (e) => e.stopPropagation());
      const vb = this.el('div', 'vbtns'); root.appendChild(vb);
      const hold = (cls, v) => {
        const b = this.el('button', cls); vb.appendChild(b);
        const on = (e) => { e.preventDefault(); e.stopPropagation(); try { b.setPointerCapture(e.pointerId); } catch (_) { /* no capture */ } b.classList.add('on'); this.app.controls.vert = v; };
        const off = () => { b.classList.remove('on'); if (this.app.controls.vert === v) this.app.controls.vert = 0; };
        b.addEventListener('pointerdown', on); b.addEventListener('pointerup', off); b.addEventListener('pointercancel', off);
        return b;
      };
      hold('up', 1); hold('down', -1);
      const fb = this.el('button', 'fast'); vb.appendChild(fb);
      fb.addEventListener('pointerdown', (e) => e.stopPropagation());
      fb.onclick = () => { const c = this.app.controls; c.fastLatch = !c.fastLatch; fb.classList.toggle('on', c.fastLatch); };
    }
    this.label = this.el('div', 'label'); root.appendChild(this.label);
    this.help = this.el('div', 'help'); root.appendChild(this.help);
    this.setLang(this.lang);
  }
  setLang(l) {
    this.lang = l; document.documentElement.lang = l; window.__lang = l;
    const ti = this.title;
    if (ti) {
      ti.querySelector('.sub').textContent = this.t('sub');
      ti.querySelectorAll('.start').forEach((b) => (b.textContent = this.t('start')));
      ti.querySelectorAll('.lang button').forEach((b) => b.classList.toggle('on', b.dataset.l === l));
      this.prep();
    }
    this.bar.querySelectorAll('.mode').forEach((b) => (b.textContent = this.t(b.dataset.m)));
    this.root.querySelectorAll('.season').forEach((b) => (b.textContent = this.t(b.dataset.s)));
    const ps = this.bar.querySelector('.places');
    ps.innerHTML = `<option value="">${this.t('places')}</option>` + PLACES.map((p) => `<option value="${p.id}">${p[l]}</option>`).join('');
    this.root.querySelector('.lg').textContent = l === 'ja' ? 'EN' : 'JA';
    const cr = this.root.querySelector('.cr'); cr.textContent = this.t('credits'); cr.href = 'credits.html#' + l;
    this.root.querySelector('.br span').textContent = this.t('bright');
    if (this.touch) {
      this.bar.querySelector('.more').textContent = this.t('more') + ' ⋯';
      const vb = this.root.querySelector('.vbtns');
      vb.querySelector('.up').textContent = '▲'; vb.querySelector('.down').textContent = '▼'; vb.querySelector('.fast').textContent = this.t('fast');
      vb.querySelector('.up').setAttribute('aria-label', this.t('up')); vb.querySelector('.down').setAttribute('aria-label', this.t('down'));
    }
    this.refresh();
  }
  prep(f = this.pf, phase = this.pp) {
    this.pf = f; this.pp = phase;
    const P = this.title && this.title.querySelector('.prep'); if (!P || f === undefined) return;
    P.querySelector('.pbar i').style.transform = `scaleX(${Math.max(0, f)})`;
    P.querySelector('.ptxt').textContent = this.t('prep') + (f >= 0 ? `  ${Math.floor(f * 100)}%` : '');
    P.querySelector('.pstage').textContent = this.t('prep_' + phase);
  }
  ready() {
    if (this.isReady) return; this.isReady = true;
    this.title && this.title.classList.add('ready');
    const v = document.getElementById('veil'); if (v) { v.classList.add('off'); setTimeout(() => v.remove(), 1600); }
  }
  start(m) {
    this.ready();
    if (this.title) { const t = this.title; t.classList.add('gone'); setTimeout(() => t.remove(), 1200); this.title = null; }
    this.bar.classList.remove('hidden');
    this.app.begin(m);
  }
  refresh() {
    const a = this.app;
    this.bar.querySelectorAll('.mode').forEach((b) => b.classList.toggle('on', b.dataset.m === a.mode));
    this.root.querySelectorAll('.season').forEach((b) => b.classList.toggle('on', b.dataset.s === a.season));
    this.root.classList.toggle('flying', a.mode === 'fly');
    this.root.querySelector('.snd').textContent = this.t('sound') + (a.sound ? ' ●' : ' ○');
    const hk = 'help_' + a.mode, tk = hk + '_t';
    this.help.textContent = a.mode === 'title' ? '' : this.t(matchMedia('(pointer: coarse)').matches && T[this.lang][tk] ? tk : hk);
    this.help.classList.remove('fade'); void this.help.offsetWidth; this.help.classList.add('fade');
  }
  setLabel(s) { if (this.label.textContent !== s) this.label.textContent = s; }
}
