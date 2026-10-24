// film_shots.mjs — the shot list of film.mjs. bars [from, to) on the score's bars (Gymnopédie No. 1, 3/4 at 60 bpm:
// 3 s a bar), so every cut falls on a downbeat. Places in data axes (x east, y north, z up, T.P. metres); headings
// 0 = north, clockwise. kinds (film_page.js):
//   pan    stand at (x, y) on whatever is there, turn the eyes by `sweep` from heading h (look pitch p), the eyes
//          `lift` m above you (a drone's view over the roof garden)
//   ground stand and drift from a to b (data x, y), heading h0 -> h1, pitch p0 -> p1
//   glide  fly from (x, y, z) along heading h at `speed`, climbing `climb` m/s on the lift, a slow sway of the bank
//   arc    on foot, eyes `eye` m up, arcing round c at radius r0 -> r1 from angle a0 to a1, facing it (eyes on zl
//          above its ground, plus tilt)
//   orbit  circle the point c at radius r from angle a0 (radians, from east, counter-clockwise = a left turn), rising
//          z0 -> z1, the eyes turned `inward` toward the middle
// cap: the place (ja, en), from `in` to `out` s; say: a line of Saki's (the game's own), from `in` to `out` s;
// title: the wordmark; tail: seconds after the last bar; black: [t0, t1, a0, a1] a fade.
export const BAR = 3;
export const SHOTS = [
  { name: 'scramble', bars: [0, 5], kind: 'pan', x: 15, y: -11, h: 0, sweep: -2 * Math.PI, p: 0.19, ease: 'inout',
    title: { in: 0.8, out: 6.6, sub: '渋谷 · 新宿 · 六本木 — 滑空する廃都' },
    cap: { ja: '渋谷スクランブル交差点', en: 'Shibuya Crossing', in: 8.2, out: 14.6 },
    say: { text: 'この交差点、いまは木しか渡らない。', in: 9.4, out: 13.8 } },
  { name: 'tochoAir', bars: [5, 7], kind: 'glide', x: -655, y: 3215, z: 262, h: -0.5, speed: 15, climb: 0, sway: 0.08, look: [0.9, -0.12],
    cap: { ja: '新宿 東京都庁', en: 'Tokyo Metropolitan Government Building', in: 0.5, out: 5.8 },
    say: { text: '都庁。てっぺん、なくなっちゃったね。', in: 1.0, out: 5.6 } },
  { name: 'tochoGround', bars: [7, 9], kind: 'ground', a: [-688, 3348], b: [-692, 3347.4], h0: -1.72, h1: -1.66, p0: 0.12, p1: 0.62, ease: 'inout',
    cap: { ja: '都民広場', en: "Citizens' Plaza", in: 0.6, out: 5.8 } },
  { name: 'maman', bars: [9, 12], kind: 'arc', c: [2656.8, 140.8], r0: 14, r1: 9.5, a0: 0.55, a1: 1.95, eye: 1.4, zl: 6.2, tilt: 0.04, ease: 'inout',
    cap: { ja: '六本木ヒルズ 66プラザ　ママン', en: 'Maman, 66 Plaza, Roppongi Hills', in: 0.8, out: 8.6 },
    say: { text: 'ママン。ずっと、ここで卵を守ってる。', in: 2.2, out: 7.4 } },
  { name: 'spiral', bars: [12, 16], kind: 'orbit', c: [2604, 100], r: 92, a0: -1.9, speed: 16, z0: 168, z1: 286, inward: 0.72, bank: 0.42, pitch: -0.1, thermals: true,
    cap: { ja: '森タワーの上昇気流', en: 'Riding the lift off Mori Tower', in: 0.6, out: 6.2 },
    say: { text: 'この壁、あったかい。ここで回って、上がろう。', in: 1.4, out: 6.4 } },
  { name: 'float', bars: [16, 21], tail: 3.0, kind: 'glide', x: 40, y: 160, z: 215, h: -0.23, speed: 11, climb: 0.6, sway: 0.12, look: [0.0, -0.2],
    cap: { ja: '渋谷から新宿へ', en: 'Shibuya to Shinjuku', in: 0.6, out: 5.6 },
    say: { text: 'ね。街がぜんぶ、わたしたちのもの。', in: 2.0, out: 6.6 },
    title: { in: 9.6, out: 99, fin: 1.4, url: 'demos.polynous.io/tokyo2090' }, black: [15.4, 17.8, 0, 1] },
];
