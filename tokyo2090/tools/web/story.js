// What Saki says, in your head. Lines fade in at the top of the view and fade out again; each trigger fires once
// (or on a cooldown) from the state of the flight and the places you pass.

const LINES = {
  start: ['……起きてる？　今日も風がいいよ。', 'ほら、来て。ここから飛ぶの、好きでしょ。'],
  edge: ['怖くないよ。マントは、わたしが見てる。'],
  jump: ['いいよ、そのまま。', '落ちて、落ちて――ほら、ひらいた。'],
  firstGlide: ['ね。街がぜんぶ、わたしたちのもの。'],
  updraft: ['この壁、あったかい。ここで回って、上がろう。', '風、来てる。広げて、ゆっくり回って。'],
  low: ['低いよ。壁にそって、上がろう。'],
  fast: ['はやい……！　もっと。'],
  tocho: ['都庁。てっぺん、なくなっちゃったね。', 'むかしは、ここに千人くらい働いてたんだって。'],
  tower: ['東京タワー。赤かったんだよ、ぜんぶ。'],
  roppongi: ['六本木。森タワーに森が生えてる。'],
  shinjuku: ['新宿。ガラスの谷。'],
  shibuya: ['スクランブル。いちばん人がいた場所。', 'この交差点、いまは木しか渡らない。'],
  yoyogi: ['代々木の森。ここは、前から森だった。'],
  land: ['ここ、降りよう。', 'つかれた？　ちょっと休も。', 'あの屋上。ついてきて。'],
  noRoof: ['ここからじゃ届かない。もう少し、上から。', 'そっちは屋上がないよ。'],
  rest: ['……静かだね。', 'ねえ。わたしたち、どこまで行けるのかな。', '夕方の光、好き。', '十八のまま、ずっとこのまま。'],
  crash: ['……大丈夫？　もう一回。', 'いたそう。今度はもっと上を飛ぼ。'],
  handOn: ['……手、あったかい。', 'いいよ。わたしが飛ぶから、見てて。'],
  hand: ['こっち見て。', 'ずっと、こうしてたいね。', '風、気持ちいい。', '落ちないよ。わたしがいる。', '……なに。顔、見すぎ。', 'あの屋上まで、いっしょに。'],
  handOff: ['……もう、はなすの？', 'また、つなごうね。'],
  closeOn: ['……ちか、い。', 'ん……。', '……目、閉じて。'],
  close: ['……あったかい。', 'きこえる？　心臓。', 'このまま、落ちてもいいかも。', '……ばか。'],
  far: ['遠くまで来たね。帰れる？　帰れるよ。'],
};

const PLACES = [
  { id: 'tocho', x: -802, y: 3342, r: 260 },
  { id: 'tower', x: 4066, y: -102, r: 320 },
  { id: 'roppongi', x: 2597, y: 106, r: 300 },
  { id: 'shinjuku', x: -276, y: 3549, r: 450 },
  { id: 'shibuya', x: 0, y: 0, r: 220 },
  { id: 'yoyogi', x: -700, y: 1300, r: 380 },
];

export function makeStory(el) {
  const fired = new Map(); let shown = null, hideAt = 0, queue = [];
  const pick = (k) => { const a = LINES[k]; const i = (fired.get(k) || 0) % a.length; fired.set(k, (fired.get(k) || 0) + 1); return a[i]; };
  function say(key, { every = Infinity, chance = 1 } = {}) {
    const n = fired.get(key) || 0; const last = fired.get(key + '@') || -1e9;
    if (n > 0 && performance.now() - last < every) return;
    if (Math.random() > chance) return;
    fired.set(key + '@', performance.now());
    queue.push(pick(key));
  }
  let flightTime = 0, wasState = 'rest', restTime = 0, upTime = 0, wasHand = false, handTime = 0, wasClose = false, closeTime = 0;
  return {
    say,
    get speaking() { return shown !== null; },
    update(f, dt) {
      // triggers
      if (f.state !== wasState) {
        if (f.state === 'fall') say('jump', { every: 40000 });
        if (f.state === 'glide' && wasState === 'fall') { if (!fired.get('firstGlide')) say('firstGlide'); }
        if (f.state === 'crash') say('crash', { every: 15000 });
        if (f.state === 'landing') say('land', { every: 30000 });
        if (f.state === 'rest') restTime = 0;
        wasState = f.state;
      }
      if (f.hand !== wasHand) { say(f.hand ? 'handOn' : 'handOff', { every: 8000 }); wasHand = f.hand; handTime = 0; }
      if (f.close !== wasClose) { if (f.close) say('closeOn', { every: 6000 }); wasClose = f.close; closeTime = 0; }
      if (f.close) { closeTime += dt; if (closeTime > 8) { say('close', { every: 10000 }); closeTime = 0; } }
      else if (f.hand) { handTime += dt; if (handTime > 9) { say('hand', { every: 12000 }); handTime = 0; } }
      if (f.state === 'rest') { restTime += dt; if (restTime > 14) { say('rest', { every: 45000 }); restTime = 0; } }
      if (f.state === 'glide') {
        flightTime += dt;
        if (f.updraft > 3.5) { upTime += dt; if (upTime > 1.5) { say('updraft', { every: 45000 }); upTime = -30; } } else upTime = Math.max(0, upTime);
        if (f.speed > 32) say('fast', { every: 90000 });
        const [x, y] = [f.p.x, -f.p.z];
        for (const p of PLACES) if (Math.hypot(x - p.x, y - p.y) < p.r) say(p.id, { every: 240000 });
        if (f.p.y - f.ground(x, y) < 25 && f.speed > 5) say('low', { every: 60000 });
        if (Math.hypot(x, y) > 3800) say('far', { every: 300000 });
      }
      // display
      const now = performance.now();
      if (shown && now > hideAt) { el.classList.remove('on'); shown = null; hideAt = now + 1500; }
      if (!shown && queue.length && now > hideAt) { shown = queue.shift(); el.textContent = shown; el.classList.add('on'); hideAt = now + 4200 + shown.length * 90; }
    },
  };
}
