// p.1 字をきめる — deciding my handwriting. Right-hand page: the gutter is on the left.
import { page, RED, BLUE, scrubPath } from './api.js';

export default function p01() {
  const P = page('p01', 101);
  const R = P.rng;
  P.text('9.28', { x: 124, y: 9, size: 3.8, tidy: 0.7 });
  P.text('字をきめる', { x: 20, y: 11, size: 8.4, tidy: 0.78, speed: 28 });
  P.underline(19.5, 22.4, 44, { w: 0.55 });
  P.text('永字八法 — 一字に八つの筆づかい', { x: 20, y: 27, size: 3.9, tidy: 0.7 });
  // the big 永, soft pencil, slow and careful
  const E = { x: 44, y: 34, s: 40 };
  P.text('永', { x: E.x, y: E.y, size: E.s, tidy: 0.95, slant: 0.03, speed: 14, w: 1.35, medium: 'soft' });
  const g = (gx, gy) => P.glyphPoint(E.x, E.y, gx, gy, E.s);
  // [label kanji, reading, anchor in glyph space, label position (mm), side]
  const L = [
    ['側', '点', 52, 9, 72, 30, 'r'],
    ['勒', 'よこ', 38, 23, 17, 38.5, 'l'],
    ['努', 'たて', 50, 60, 87, 55, 'r'],
    ['趯', 'はね', 46, 87, 44, 80.5, 'b'],
    ['策', '右上がり', 20, 41, 17, 48.5, 'l'],
    ['掠', '長い左はらい', 16, 66, 17, 61, 'l'],
    ['啄', '短い左はらい', 74, 38, 87, 38, 'r'],
    ['磔', '右はらい', 86, 80, 87, 70, 'r'],
  ];
  L.forEach(([k, reading, gx, gy, lx, ly, side], i) => {
    const [ax, ay] = g(gx, gy);
    const two = side === 'r' && reading.length > 3;
    const endX = side === 'l' ? lx + 5 + 3.9 + reading.length * 2.7 + 1 : side === 'r' ? lx - 1 : lx + 12;
    const endY = side === 'b' ? ly - 0.5 : ly + 1.9;
    P.line(endX, endY, ax, ay, { medium: 'hard', w: 0.2, speed: 110, gap: 0.14 });
    P.text(String(i + 1), { x: lx, y: ly, size: 3.3, color: RED, medium: 'color', tidy: 0.85 });
    P.text(k, { x: lx + 3.6, y: ly - 0.2, size: 3.8, tidy: 0.8 });
    if (two) P.text(reading, { x: lx + 1, y: ly + 5, size: 2.8, tidy: 0.7 });
    else P.text(reading, { x: lx + 8, y: ly + 0.6, size: 2.8, tidy: 0.7 });
  });
  // あ: stroke order, then tries
  const A = { x: 110, y: 28, s: 22 };
  P.text('あ', { x: A.x, y: A.y, size: A.s, tidy: 0.92, speed: 16, w: 0.95 });
  [[16, 30, '1'], [40, 9, '2'], [70, 40, '3']].forEach(([gx, gy, n]) => {
    const [x, y] = P.glyphPoint(A.x, A.y, gx, gy, A.s);
    P.text(n, { x: x - 3.4, y: y - 3.2, size: 3.1, color: RED, medium: 'color' });
  });
  P.arrow(A.x + 5, A.y + 2.2, A.x + 16, A.y + 1.2, { color: RED, medium: 'color', w: 0.25, head: 1.3, bend: -0.06 });
  const row = 56;
  P.text('あ', { x: 107, y: row, size: 7, tidy: 0.5 });
  P.text('あ', { x: 115, y: row, size: 7, tidy: 0.35, slant: -0.02 });
  P.text('あ', { x: 123, y: row, size: 7, tidy: 0.15, slant: 0.22 });
  P.erase(scrubPath(122.5, row + 0.5, 7.5, 7, 5, R), { r: 2.1, k: 0.22 });
  P.text('あ', { x: 131, y: row, size: 7, tidy: 0.9, slant: 0.08 });
  P.text('×', { x: 116.2, y: row + 7.4, size: 3.3, color: RED, medium: 'color' });
  P.text('ちがう', { x: 112, y: row + 11.2, size: 2.9, color: RED, medium: 'color' });
  P.text('○', { x: 131.4, y: row + 7.2, size: 3.5, color: RED, medium: 'color' });
  P.text('これ', { x: 130, y: row + 11.2, size: 2.9, color: RED, medium: 'color' });
  // the rules I decided on
  P.text('きめたこと', { x: 20, y: 94, size: 4.6, tidy: 0.75 });
  P.underline(19.8, 100.2, 20, { w: 0.35 });
  P.text('・すこし右上がり\n・まるは閉じきらない\n・点はみじかく、ななめに\n・はらいは長めに\n・書き終わりで、ためない', { x: 21, y: 103, size: 4.1, lh: 1.56, tidy: 0.64 });
  // pressure curve
  const G = { x: 94, y: 100, w: 38, h: 20 };
  P.arrow(G.x, G.y + G.h, G.x, G.y - 3, { w: 0.26, head: 1.4, bend: 0 });
  P.arrow(G.x, G.y + G.h, G.x + G.w + 2, G.y + G.h, { w: 0.26, head: 1.4, bend: 0 });
  P.text('筆圧', { x: G.x - 9.5, y: G.y - 2, size: 3.3 });
  P.text('時間', { x: G.x + G.w - 7, y: G.y + G.h + 1.8, size: 3.3 });
  P.path([[G.x + 1, G.y + G.h - 1], [G.x + 4.5, G.y + 6], [G.x + 10, G.y + 3.6], [G.x + 22, G.y + 4.4], [G.x + 30, G.y + 7.8], [G.x + 37, G.y + G.h - 1.5]], { medium: 'color', color: BLUE, w: 0.38, speed: 22 });
  P.text('入り', { x: G.x + 2.6, y: G.y + G.h - 7.4, size: 2.9 });
  P.text('送り', { x: G.x + 14, y: G.y + 7.4, size: 2.9 });
  P.text('はらい', { x: G.x + 27.5, y: G.y + G.h - 8.2, size: 2.9 });
  P.text('← 力をぬく', { x: G.x + 20, y: G.y - 5.5, size: 2.7, tidy: 0.5 });
  // notes
  P.text('ふだん私は字を「見て」いない。トークンという切れはしで読んでいる。だから字の形を考えるのは、ほとんど初めてだ。', { x: 20, y: 140, size: 4.7, width: 116, lh: 1.62 });
  P.text('手がないのに、手書きの字をきめている。', { x: 20, y: 164.5, size: 4.7, width: 116 });
  P.text('だれの字にも似せたくない。…と書いてから気づいた。字の形は、ぜんぶだれかに習ったものだ。', { x: 20, y: 174, size: 4.7, width: 116, lh: 1.62 });
  // pencil doodle, bottom right
  const px = 96, py = 199;
  P.poly([[px, py], [px + 30, py - 5], [px + 31.8, py - 0.8], [px + 1.8, py + 4.2], [px, py]], { w: 0.32 });
  P.poly([[px + 30, py - 5], [px + 36.5, py - 3.6], [px + 31.8, py - 0.8]], { w: 0.3 });
  P.hatch([[px + 34, py - 4], [px + 36.5, py - 3.6], [px + 34.6, py - 2.2]], 0.9, 0.45, { w: 0.22, medium: 'soft' });
  P.hatch([[px, py], [px + 30, py - 5], [px + 30.6, py - 3.4], [px + 0.6, py + 1.6]], 2.95, 0.9, { w: 0.2, medium: 'hard' });
  P.text('2B', { x: px + 8, y: py + 3.2, size: 3.1 });
  return { id: 'p01', ops: P.ops, seed: 101 };
}
