// Overlay UI: title, mode bar (walk / gondola / fly), places, gondola routes and speed, day/night, sound, JA/EN.
const T = {
  ja: {
    title: 'VENEZIA', sub: 'ヴェネツィア本島を、歩いて、ゴンドラで。',
    walk: '歩く', boat: 'ゴンドラ', fly: '空から', places: '場所', route: 'コース', speed: '速さ', day: '昼', night: '夜', sound: '音', credits: 'クレジット', bright: '明るさ',
    help_walk: 'W A S D で歩く ・ ドラッグで見回す ・ Shift で走る',
    help_walk_t: '左下のスティックで歩く ・ ドラッグで見回す',
    help_fly_t: 'スティックで進む ・ ドラッグで向き',
    help_boat_t: 'ドラッグで見回す ・ コースと速さは下のバーで',
    help_boat: 'ドラッグで見回す ・ コースと速さは下のバーで ・ R で自分で漕ぐ',
    help_fly: 'W A S D・E Q で移動 ・ ドラッグで向き ・ ホイールで速度',
    help_row: 'W S で前後 ・ A D で舵 ・ R で自動に戻す',
    loading: '読み込み中',
    start: 'はじめる', prep: '準備中', prep_data: 'サン・マルコ広場とそのまわりを読み込んでいます', prep_gpu: '描画の準備をしています',
  },
  en: {
    title: 'VENEZIA', sub: 'Walk the island. Ride a gondola.',
    walk: 'Walk', boat: 'Gondola', fly: 'Fly', places: 'Places', route: 'Route', speed: 'Speed', day: 'Day', night: 'Night', sound: 'Sound', credits: 'Credits', bright: 'Brightness',
    help_walk: 'W A S D to walk · drag to look · Shift to run',
    help_walk_t: 'Stick (bottom left) to walk · drag to look',
    help_fly_t: 'Stick to move · drag to turn',
    help_boat_t: 'Drag to look around · route and speed in the bar',
    help_boat: 'Drag to look around · route and speed in the bar · R to row yourself',
    help_fly: 'W A S D · E Q to move · drag to turn · wheel for speed',
    help_row: 'W S forward/back · A D to steer · R for autopilot',
    loading: 'Loading',
    start: 'Start', prep: 'Preparing', prep_data: 'Loading Piazza San Marco and its surroundings', prep_gpu: 'Getting the graphics ready',
  },
};
// map: a shorter name for the minimap's labels
export const PLACES = [
  { id: 'piazza', ja: 'サン・マルコ広場', en: 'Piazza San Marco', mode: 'walk', at: [-28.0, 21.0], yaw: 0.33 },
  { id: 'florian', ja: 'カフェ・フローリアン（テラス）', en: 'Caffè Florian — terrace', mode: 'walk', at: [-44.0, -40.0], yaw: 2.1, map: { ja: 'カフェ・フローリアン', en: 'Caffè Florian' } },
  { id: 'florian_in', ja: 'カフェ・フローリアン（店内）', en: 'Caffè Florian — inside', mode: 'walk', at: [-58.42, -50.05], yaw: -1.2 },
  { id: 'basilica', ja: 'サン・マルコ寺院', en: "St Mark's Basilica", mode: 'walk', at: [20.0, 35.0], yaw: 0.33 },
  { id: 'piazzetta', ja: 'ピアツェッタとドゥカーレ宮殿', en: "Piazzetta & Doge's Palace", mode: 'walk', at: [58.0, -96.0], yaw: 1.3, map: { ja: 'ドゥカーレ宮殿', en: "Doge's Palace" } },
  { id: 'sospiri', ja: '嘆きの橋（藁の橋から）', en: 'Bridge of Sighs (from the Paglia)', mode: 'walk', at: [154.0, -45.0], yaw: 1.62, map: { ja: '嘆きの橋', en: 'Bridge of Sighs' } },
  { id: 'rialto', ja: 'リアルト橋', en: 'Rialto Bridge', mode: 'walk', at: [-238.0, 441.5], yaw: 2.45 },
  { id: 'accademia', ja: 'アカデミア橋（サルーテを望む）', en: 'Accademia Bridge, toward the Salute', mode: 'walk', at: [-787.2, -264.9], yaw: -0.24, map: { ja: 'アカデミア橋', en: 'Accademia Bridge' } },
  { id: 'fenice', ja: 'フェニーチェ劇場', en: 'La Fenice', mode: 'walk', at: [-383.5, -41.5], yaw: 2.906 },
  { id: 'fenice_in', ja: 'フェニーチェ劇場（客席）', en: 'La Fenice — the hall', mode: 'walk', at: [-430.3, -62.7], yaw: -2.703 },
  { id: 'calle', ja: '路地（カンナレージョ）', en: 'A calle in Cannaregio', mode: 'walk', at: [-560.0, 1100.0], yaw: 0, map: { ja: 'カンナレージョ', en: 'Cannaregio' } },
  { id: 'ferrovia', ja: 'サンタ・ルチア駅', en: 'Santa Lucia station', mode: 'walk', at: [-1375.3, 754.4], yaw: 2.47 },
];
export const ROUTES = [
  { id: 'grand', ja: '嘆きの橋からリアルト、フェニーチェへ', en: 'Bridge of Sighs, Rialto, La Fenice' },
  { id: 'sospiri', ja: '小運河から嘆きの橋へ', en: 'Small canals to the Bridge of Sighs' },
  { id: 'canalgrande', ja: '大運河（サルーテ〜リアルト）', en: 'Grand Canal: Salute to Rialto' },
];

export class UI {
  constructor(app) {
    this.app = app;
    this.lang = window.__lang || ((location.hash === '#en' || (navigator.language || '').slice(0, 2) !== 'ja') && location.hash !== '#ja' ? 'en' : 'ja');
    if (location.hash === '#ja') this.lang = 'ja';
    window.__ui = this;
    this.build();
  }
  t(k) { return T[this.lang][k] || k; }
  el(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  build() {
    // the title (and its loading line) is in index.html, so it shows before the app has arrived
    let root = document.querySelector('.ui');
    if (!root) { root = this.el('div', 'ui'); document.body.appendChild(root); }
    this.root = root;
    let ti = root.querySelector('.title');
    if (!ti) {
      ti = this.el('div', 'title');
      ti.innerHTML = `<div class="word">VENEZIA</div><div class="sub"></div><div class="prep"><div class="pbar"><i></i></div><div class="ptxt"></div><div class="pstage"></div></div><div class="starts"></div><div class="lang"><button data-l="ja">JA</button><button data-l="en">EN</button></div>`;
      root.appendChild(ti);
    }
    this.title = ti;
    // one way in: walking in Piazza San Marco (the first view the page prepares); the bar switches modes later
    const sb = this.el('button', 'start'); sb.dataset.m = 'walk'; ti.querySelector('.starts').appendChild(sb);
    sb.onclick = () => this.start('walk');
    ti.querySelectorAll('.lang button').forEach((b) => (b.onclick = () => this.setLang(b.dataset.l)));
    // bar
    const bar = this.bar = this.el('div', 'bar hidden'); root.appendChild(bar);
    bar.innerHTML = `<div class="grp modes"></div><div class="grp"><select class="places"></select></div>
      <div class="grp boatonly"><select class="routes"></select><div class="speeds"></div></div>
      <div class="grp right"><label class="br"><span></span><input type="range" min="0.5" max="2.5" step="0.05"></label><button class="dn"></button><button class="snd"></button><button class="lg"></button><a class="cr" href="credits.html" target="_blank"></a></div>`;
    for (const m of ['walk', 'boat', 'fly']) { const b = this.el('button', 'mode'); b.dataset.m = m; b.onclick = () => this.app.setMode(m); bar.querySelector('.modes').appendChild(b); }
    bar.querySelector('.places').onchange = (e) => { const p = PLACES.find((x) => x.id === e.target.value); if (p) this.app.goPlace(p); e.target.value = ''; };
    bar.querySelector('.routes').onchange = (e) => this.app.setRoute(e.target.value);
    for (const s of [1, 2, 4]) { const b = this.el('button', 'spd', `×${s}`); b.dataset.s = s; b.onclick = () => this.app.setSpeed(s); bar.querySelector('.speeds').appendChild(b); }
    bar.querySelector('.dn').onclick = () => this.app.toggleNight();
    bar.querySelector('.snd').onclick = () => this.app.toggleSound();
    bar.querySelector('.lg').onclick = () => this.setLang(this.lang === 'ja' ? 'en' : 'ja');
    const br = bar.querySelector('.br input'); br.value = this.app.bright;
    br.oninput = () => this.app.setBright(+br.value);
    this.label = this.el('div', 'label'); root.appendChild(this.label);
    this.help = this.el('div', 'help'); root.appendChild(this.help);
    this.setLang(this.lang);
  }
  setLang(l) {
    this.lang = l; document.documentElement.lang = l;
    const ti = this.title;
    ti.querySelector('.sub').textContent = this.t('sub');
    ti.querySelectorAll('.start').forEach((b) => (b.textContent = this.t('start')));
    this.prep();
    ti.querySelectorAll('.lang button').forEach((b) => b.classList.toggle('on', b.dataset.l === l));
    this.bar.querySelectorAll('.mode').forEach((b) => (b.textContent = this.t(b.dataset.m)));
    const ps = this.bar.querySelector('.places');
    ps.innerHTML = `<option value="">${this.t('places')}</option>` + PLACES.map((p) => `<option value="${p.id}">${p[l]}</option>`).join('');
    const rs = this.bar.querySelector('.routes');
    rs.innerHTML = ROUTES.map((r) => `<option value="${r.id}">${r[l]}</option>`).join('');
    rs.value = this.app.routeId || 'grand';
    this.bar.querySelector('.lg').textContent = l === 'ja' ? 'EN' : 'JA';
    const cr = this.bar.querySelector('.cr'); cr.textContent = this.t('credits'); cr.href = 'credits.html#' + l;
    this.bar.querySelector('.br span').textContent = this.t('bright');
    this.refresh();
  }
  // loading line on the title: f = 0..1 (the bar), phase = 'data' | 'gpu'; f < 0 while the sizes are not known yet
  prep(f = this.pf, phase = this.pp) {
    this.pf = f; this.pp = phase;
    const P = this.title.querySelector('.prep'); if (!P || f === undefined) return;
    P.querySelector('.pbar i').style.transform = `scaleX(${Math.max(0, f)})`;
    P.querySelector('.ptxt').textContent = this.t('prep') + (f >= 0 ? `  ${Math.floor(f * 100)}%` : '');
    P.querySelector('.pstage').textContent = this.t('prep_' + phase);
  }
  // the first view is ready: the veil lifts off the Piazza and the start button replaces the loading line
  ready() {
    if (this.isReady) return; this.isReady = true;
    this.title.classList.add('ready');
    const v = document.getElementById('veil'); if (v) { v.classList.add('off'); setTimeout(() => v.remove(), 1600); }
  }
  start(m) {
    this.ready();
    this.title.classList.add('gone');
    setTimeout(() => this.title.remove(), 1200);
    this.bar.classList.remove('hidden');
    this.app.begin(m);
  }
  refresh() {
    const a = this.app;
    this.bar.querySelectorAll('.mode').forEach((b) => b.classList.toggle('on', b.dataset.m === a.mode));
    this.bar.querySelector('.boatonly').style.display = a.mode === 'boat' ? '' : 'none';
    this.bar.querySelectorAll('.spd').forEach((b) => b.classList.toggle('on', +b.dataset.s === a.speed));
    this.bar.querySelector('.dn').textContent = a.night ? this.t('day') : this.t('night');
    this.bar.querySelector('.snd').textContent = this.t('sound') + (a.sound ? ' ●' : ' ○');
    const hk = a.mode === 'boat' ? (a.rowing ? 'help_row' : 'help_boat') : 'help_' + a.mode;
    const tk = hk + '_t';                         // touch screens: the stick instead of keys
    this.help.textContent = a.mode === 'title' ? '' : this.t(matchMedia('(pointer: coarse)').matches && T[this.lang][tk] ? tk : hk);
    this.help.classList.remove('fade'); void this.help.offsetWidth; this.help.classList.add('fade');
  }
  setLabel(s) { if (this.label.textContent !== s) this.label.textContent = s; }
}
