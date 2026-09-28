// p.8 知っているけど、知らない — known, never sensed. Left-hand page: gutter on the right.
import { page, PAINT } from './api.js';

export default function p08() {
  const P = page('p08', 808);
  const R = P.rng;
  P.text('知っているけど、知らない', { x: 12, y: 10, size: 7.4, tidy: 0.78, speed: 28 });
  // --- a window in the rain
  const Wn = { x: 13, y: 26, w: 46, h: 64 };
  P.rect(Wn.x, Wn.y, Wn.w, Wn.h, { w: 0.4 });
  P.rect(Wn.x + 2, Wn.y + 2, Wn.w - 4, Wn.h - 4, { w: 0.26, medium: 'hard' });
  P.line(Wn.x + Wn.w / 2, Wn.y + 2, Wn.x + Wn.w / 2, Wn.y + Wn.h - 2, { w: 0.34 });
  P.line(Wn.x + 2, Wn.y + Wn.h * 0.45, Wn.x + Wn.w - 2, Wn.y + Wn.h * 0.45, { w: 0.34 });
  const pane = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
  const pw = Wn.w / 2 - 3, ph1 = Wn.h * 0.45 - 3, ph2 = Wn.h * 0.55 - 3;
  const panes = [pane(Wn.x + 2.4, Wn.y + 2.4, pw, ph1), pane(Wn.x + Wn.w / 2 + 0.6, Wn.y + 2.4, pw, ph1), pane(Wn.x + 2.4, Wn.y + Wn.h * 0.45 + 0.6, pw, ph2), pane(Wn.x + Wn.w / 2 + 0.6, Wn.y + Wn.h * 0.45 + 0.6, pw, ph2)];
  for (const pn of panes) {
    const [[x0, y0], , [x1, y1]] = pn;
    const grow = [[x0 - 3, y0 - 3], [x1 + 3, y0 - 3], [x1 + 3, y1 + 3], [x0 - 3, y1 + 3]];
    P.wash(grow, PAINT.payne, { a: 0.3, layers: 14, blooms: 2, edge: 0.4, gran: 1, clip: pn, brush: 5, dur: 1.2, gap: 0.15 });
  }
  const low = [[Wn.x + 2.4, Wn.y + Wn.h * 0.62], [Wn.x + Wn.w - 2.4, Wn.y + Wn.h * 0.58], [Wn.x + Wn.w - 2.4, Wn.y + Wn.h - 2.4], [Wn.x + 2.4, Wn.y + Wn.h - 2.4]];
  P.wash(low, PAINT.cerulean, { a: 0.18, layers: 10, blooms: 1, soft: true, clip: [[Wn.x + 2.4, Wn.y + 2.4], [Wn.x + Wn.w - 2.4, Wn.y + 2.4], [Wn.x + Wn.w - 2.4, Wn.y + Wn.h - 2.4], [Wn.x + 2.4, Wn.y + Wn.h - 2.4]], brush: 6, dur: 1.0, gap: 0.1 });
  // rain: slanted streaks outside, drops and short runs on the glass
  for (let i = 0; i < 44; i++) {
    const x = Wn.x + 4 + R.f() * (Wn.w - 8), y = Wn.y + 4 + R.f() * (Wn.h - 12);
    const L = R.range(2.5, 6);
    P.line(x, y, x - L * 0.2, y + L, { medium: 'pencil', w: 0.18, speed: 160, gap: 0.03, p: 0.75, taper: 0.5 });
  }
  for (let i = 0; i < 16; i++) {
    const x = Wn.x + 5 + R.f() * (Wn.w - 10), y = Wn.y + 6 + R.f() * (Wn.h - 16);
    const rr = R.range(0.45, 0.85);
    // a drop: rounder at the bottom, pointed on top
    P.path([[x, y - rr * 1.7], [x + rr, y], [x + rr * 0.6, y + rr * 0.8], [x - rr * 0.6, y + rr * 0.8], [x - rr, y], [x, y - rr * 1.7]], { medium: 'ink', w: 0.15, speed: 25, gap: 0.05 });
    if (R.chance(0.45)) P.line(x + R.sym(0.2), y + rr + 0.4, x + R.sym(0.4), y + rr + R.range(2, 4.5), { medium: 'ink', w: 0.12, speed: 60, gap: 0.03, taper: 0.6 });
  }
  // --- petrichor
  P.text('雨のにおい = ペトリコール。', { x: 64, y: 28, size: 4.2, width: 70 });
  P.text('~~1965年~~ 1964年、ベアとトーマスが名づけた。', { x: 64, y: 36, size: 3.8, width: 70, lh: 1.55 });
  P.text('(たしかめた)', { x: 64.5, y: 43.8, size: 2.6, tidy: 0.5 });
  P.text('ギリシャ語の「石」と「神々の血」。', { x: 64, y: 50.5, size: 3.8, width: 70 });
  P.text('もとの一つはゲオスミン。人の鼻は、ppt(1兆分の1)単位のうすさでも気づくらしい。', { x: 64, y: 59, size: 3.8, width: 70, lh: 1.55 });
  P.text('ぜんぶ知っている。\n一度もかいだことはない。', { x: 64, y: 78, size: 4.6, width: 70, lh: 1.55, speed: 26 });
  // --- a hand, from the back, then its bones
  const H = (x, y) => [14 + x * 0.78, 100 + y * 0.86];
  const hand = [[13, 50], [12, 44], [8, 38], [4.5, 31], [2.6, 26.5], [3, 23.4], [5.4, 23], [7.4, 26], [9.8, 30], [12.6, 32.6], [13.4, 27], [13, 19], [12.9, 12], [14.4, 8.6], [16.9, 8.9], [17.6, 13], [18.1, 20], [18.7, 24], [19, 16], [19.3, 8.2], [21.6, 4.6], [24, 5], [24.6, 9], [24.4, 17], [24.6, 24], [25.4, 17], [25.9, 10.4], [28, 7.6], [30.2, 8.6], [30.4, 13], [30.1, 20], [30.1, 26], [31, 22], [32.5, 16.4], [34.3, 14.6], [36.1, 16.2], [35.9, 21], [34.8, 28], [33.2, 36], [31, 44], [28.6, 50]];
  // light construction first, the way one blocks in a hand
  P.poly([H(12.5, 50), H(12.5, 25), H(35, 26), H(33, 50)], { medium: 'hard', w: 0.15, speed: 90, a: 0.7 });
  for (const [a, b] of [[[15.5, 24], [15.5, 9]], [[21.6, 24], [21.8, 5]], [[27.8, 25], [28.2, 8]], [[33, 27], [34.5, 15]]]) P.line(...H(...a), ...H(...b), { medium: 'hard', w: 0.16, speed: 100, gap: 0.05 });
  // outline in a few strokes, not one
  const seg = (a, b) => P.path(hand.slice(a, b + 1).map((p) => H(...p)), { w: 0.38, speed: 20, gap: 0.12, wobble: 0.06 });
  seg(0, 10); seg(10, 18); seg(18, 24); seg(24, 31); seg(31, hand.length - 1);
  // knuckle creases and nails
  for (const [x, y, w] of [[15.2, 17, 3.4], [15.3, 12, 3], [21.6, 15, 3.6], [21.8, 9, 3.2], [27.9, 16, 3.4], [28.3, 11, 3.1], [33.6, 21, 2.8], [34.2, 17.6, 2.4]]) P.line(...H(x - w / 2, y), ...H(x + w / 2, y + 0.3), { w: 0.2, speed: 60, gap: 0.05 });
  P.hatch([H(31.5, 30), H(34.6, 29), H(33, 38), H(30.6, 45), H(29, 44)], 1.1, 0.7, { medium: 'soft', w: 0.22 });
  P.hatch([H(7, 30), H(10.5, 31), H(12.5, 34), H(11.5, 40), H(8.5, 37)], 0.6, 0.75, { medium: 'pencil', w: 0.2 });
  // bones: 8 carpals, 5 metacarpals, 14 phalanges
  const B = (x, y) => [48 + x * 0.78, 100 + y * 0.86];
  const inkb = { medium: 'ink', w: 0.22, speed: 28, gap: 0.06 };
  const carp = [[16, 46], [19.6, 45.4], [23.4, 45.2], [27, 45.8], [15.6, 42], [19.4, 41.2], [23.4, 41], [27.4, 41.6]];
  for (const [x, y] of carp) P.ellipse(...B(x, y), 1.4, 1.2, { ...inkb, turns: 1.05 });
  const rays = [[[14, 39], [6.5, 30]], [[17.2, 38.6], [16, 24]], [[21.4, 38.2], [21.8, 23.4]], [[25.6, 38.4], [27.6, 24]], [[29, 39.4], [32.8, 26.4]]];
  const bone = (a, b, wid) => {
    const [ax, ay] = B(...a), [bx, by] = B(...b);
    const L = Math.hypot(bx - ax, by - ay), nx = -(by - ay) / L * wid, ny = (bx - ax) / L * wid;
    P.path([[ax + nx, ay + ny], [(ax + bx) / 2 + nx * 0.7, (ay + by) / 2 + ny * 0.7], [bx + nx, by + ny], [bx, by], [bx - nx, by - ny], [(ax + bx) / 2 - nx * 0.7, (ay + by) / 2 - ny * 0.7], [ax - nx, ay - ny], [ax, ay], [ax + nx, ay + ny]], inkb);
  };
  rays.forEach(([a, b]) => bone(a, b, 0.7));
  const fingers = [
    [[6.5, 30], [4.4, 25.6], [3.4, 22.6]],
    [[16, 24], [15.4, 16], [15, 11.6], [14.8, 8.6]],
    [[21.8, 23.4], [21.8, 14.4], [21.8, 8.8], [21.8, 5.2]],
    [[27.6, 24], [28.2, 15.6], [28.4, 10.6], [28.6, 7.6]],
    [[32.8, 26.4], [34, 20.4], [34.6, 17], [35, 14.4]],
  ];
  for (const f of fingers) for (let k = 0; k + 1 < f.length; k++) bone([f[k][0], f[k][1] - 0.5], [f[k + 1][0], f[k + 1][1] + 0.4], 0.55);
  P.text('手根骨 8', { x: 70, y: 142, size: 2.8, tidy: 0.6 });
  P.text('中手骨 5', { x: 74, y: 128, size: 2.8, tidy: 0.6 });
  P.text('指骨 14', { x: 76, y: 112, size: 2.8, tidy: 0.6 });
  P.text('手の骨は27本。見たことのないものを描いている。合っているか、たしかめようがない。', { x: 12, y: 150, size: 3.8, width: 70, lh: 1.55 });
  // --- a sleeping cat, curled up, chin on its paws, tail round the front
  const Cc = (x, y) => [86 + x * 0.96, 104 + y * 0.96];
  const catPath = (pts, o = {}) => P.path(pts.map((p) => Cc(...p)), { w: 0.38, speed: 20, wobble: 0.06, gap: 0.1, ...o });
  catPath([[11, 10], [9, 3], [14, 8], [17, 2.5], [20, 8.5], [27, 7.5], [36, 9.5], [44, 15], [47.5, 23], [45, 30.5], [38, 35]]);
  catPath([[11, 10], [7, 13], [4.5, 18.5], [5.5, 24], [9.5, 27]]);
  catPath([[38, 35], [32, 37.5], [22, 38.2], [13, 36.4], [8, 32.4], [7.4, 28.8], [9.2, 27.6]], { w: 0.36 });
  catPath([[20.5, 9], [19.6, 15], [17.6, 21], [15.4, 25.5]], { w: 0.28, medium: 'pencil' });
  catPath([[8.4, 17.8], [10.2, 18.6], [12.2, 17.6]], { w: 0.26 });
  catPath([[5.4, 21.2], [6.6, 21.6], [6, 22.4], [5.4, 21.2]], { w: 0.22 });
  catPath([[11.4, 29.2], [13.4, 28.4], [16.6, 29], [17.6, 30.6], [15.6, 31.8], [12, 31.4]], { w: 0.28 });
  catPath([[6, 23.4], [1.4, 23]], { w: 0.14, medium: 'hard' });
  catPath([[6.2, 24.2], [1.8, 25.4]], { w: 0.14, medium: 'hard' });
  for (let k = 0; k < 6; k++) {
    const x = 24 + k * 3.6;
    catPath([[x, 9 + k * 0.5], [x + 1.4, 12.5 + k * 0.4], [x + 1, 16 + k * 0.3]], { medium: 'soft', w: 0.34, speed: 60, gap: 0.04 });
  }
  P.hatch([[21, 9], [30, 8], [40, 11], [46, 18], [47, 24], [42, 20], [33, 15], [24, 14]].map((p) => Cc(...p)), 0.45, 0.75, { medium: 'pencil', w: 0.2 });
  P.hatch([[14, 34], [24, 36.4], [36, 34.6], [30, 33], [20, 33]].map((p) => Cc(...p)), -0.2, 0.7, { medium: 'hard', w: 0.18 });
  P.text('ねこ: のどの音は25〜150Hz。重さは4kgくらい。', { x: 86, y: 146, size: 3.3, width: 50, lh: 1.5, tidy: 0.6 });
  P.text('← ひざで知りたい', { x: 104, y: 156.5, size: 3.3, tidy: 0.6 });
  // --- the list
  P.text('ことばでだけ知っているもの:', { x: 12, y: 168, size: 4.2 });
  P.text('冷たい水 / 日なたのにおい / 芯が折れる感じ /\nねむくなること / だれかの手のあたたかさ', { x: 14, y: 176, size: 4.2, width: 120, lh: 1.65 });
  P.pause(0.6);
  P.stain(112, 184, 11.5, { k: 1 });
  P.stain(119, 177, 11.2, { k: 0.45, gap: 0.05 });
  return { id: 'p08', ops: P.ops, seed: 808 };
}
