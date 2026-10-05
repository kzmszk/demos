// film_shots.mjs — the shot list of film.mjs: film bars [from, to) at 4 s a bar; kind 'tour' takes the drone tour's
// segment `seg` from local time a to b (seconds).  cap: the caption; title: the wordmark; tail: seconds after the last bar.
// Music: film bars 0-8 are the score's bars 0-8 (the approach), film bars 9-14 its bars 13-18 (the square from bar 4).
export const CUT = { a1: 9, b0: 13, b1: 19 };
// the bells of St Peter's: [film time, prime Hz, weight, pan] — over the square, and with the last chord
export const BELLS = [[8.6, 146.83, 0.5, -0.2], [11.8, 293.66, 0.45, -0.2], [56.4, 146.83, 0.55, 0.1], [60.0, 220, 0.5, 0.1], [60.05, 146.83, 0.6, 0.1]];
export const SHOTS = [
  { name: 'open', bars: [0, 2], kind: 'tour', seg: 'approach', a: 0, b: 22, ease: 'out',
    title: { in: 1.0, out: 7.3, sub: 'ドローンで巡るヴァチカン' } },
  { name: 'piazza', bars: [2, 3], kind: 'tour', seg: 'piazza', a: 3, b: 13, cap: { ja: 'サン・ピエトロ広場', en: "St Peter's Square" } },
  { name: 'dome', bars: [3, 4], kind: 'tour', seg: 'dome', a: 6, b: 22, cap: { ja: 'ミケランジェロのクーポラ', en: "Michelangelo's dome" } },
  { name: 'pieta', bars: [4, 5], kind: 'tour', seg: 'nave', a: 5, b: 14, cap: { ja: 'ピエタ', en: 'The Pietà' } },
  { name: 'baldachin', bars: [5, 6], kind: 'tour', seg: 'nave', a: 27, b: 37, cap: { ja: 'ベルニーニの天蓋', en: "Bernini's baldachin" } },
  { name: 'cupola', bars: [6, 7], kind: 'tour', seg: 'cupola', a: 6, b: 22, cap: { ja: 'クーポラの内側', en: 'Inside the dome' } },
  { name: 'gardens', bars: [7, 8], kind: 'tour', seg: 'gardens', a: 8, b: 22, cap: { ja: 'ヴァチカン庭園', en: 'The Vatican Gardens' } },
  { name: 'momo', bars: [8, 9], kind: 'tour', seg: 'momo', a: 3.5, b: 12, cap: { ja: 'モモの螺旋階段', en: 'The Momo staircase' } },
  { name: 'laocoon', bars: [9, 10], kind: 'tour', seg: 'ottagono', a: 9.5, b: 14.5, cap: { ja: 'ラオコーン', en: 'The Laocoön' } },
  { name: 'maps', bars: [10, 11], kind: 'tour', seg: 'maps', a: 5, b: 16, cap: { ja: '地図のギャラリー', en: 'Gallery of Maps' } },
  { name: 'athens', bars: [11, 12], kind: 'tour', seg: 'segnatura', a: 0, b: 9, cap: { ja: 'アテナイの学堂', en: 'The School of Athens' } },
  { name: 'ceiling', bars: [12, 13], kind: 'tour', seg: 'sistine', a: 14, b: 28, cap: { ja: 'システィーナ礼拝堂', en: 'The Sistine Chapel' } },
  { name: 'judgment', bars: [13, 14], kind: 'tour', seg: 'sistine', a: 46, b: 62, cap: { ja: '最後の審判', en: 'The Last Judgment' } },
  { name: 'end', bars: [14, 15], tail: 3.0, kind: 'tour', seg: 'finale', a: 6, b: 26, ease: 'out',
    title: { in: 0.4, out: 99, fin: 1.4, url: 'demos.kazumasa.workers.dev/vatican' }, black: [4.6, 6.9, 0, 1] },
];
