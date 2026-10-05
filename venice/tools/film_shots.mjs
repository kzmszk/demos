// film_shots.mjs — the shot list of film.mjs.  bars: [from, to) of the title piece (the film plays bars 0-11, then
// 32-35); kinds: walk (path on the ground, eye from the walk raster), fly (path + look-at path), boat (a route of the
// gondola ride).  cap: the caption; title: the wordmark; tail: seconds held after the last bar (the final chord rings).
export const CUT = { a1: 12, b0: 32, b1: 36 };
// St Mark's: the church's own frame (u along the nave, v north) turned 3.5 degrees from the piazza's
const wf = (u, v) => { const a = (-3.5 * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a), PU = [0.9426, 0.3338], PV = [-0.3338, 0.9426];
  // church frame -> piazza frame (rotation about the central dome at piazza (83.7, 29.7)) -> world
  const du = u - 83.7, dv = v - 29.7, pu = 83.7 + du * c - dv * s, pv = 29.7 + du * s + dv * c;
  return [pu * PU[0] + pv * PV[0], pu * PU[1] + pv * PV[1]]; };
const BAS_FRONT = [24.6, 43.0, 13];
export const SHOTS = [
  { name: 'open', bars: [0, 2], kind: 'fly', ease: 'inout',
    path: [[200, -640, 160], [125, -440, 100], [70, -280, 55]], look: [[20, -50, 15], [20, -45, 20], [20, -40, 25]],
    title: { in: 1.2, out: 7.4, sub: 'ヴェネツィア本島を、歩いて、ゴンドラで。' } },
  { name: 'piazza', bars: [2, 4], kind: 'walk', path: [[-66, 7], [-52, 12]], lookAt: [BAS_FRONT, BAS_FRONT],
    cap: { ja: 'サン・マルコ広場', en: 'Piazza San Marco' } },
  { name: 'basilica', bars: [4, 5], kind: 'walk', path: [wf(49, 29.7), wf(52.5, 29.7)],
    lookAt: [[...wf(72, 29.7), 4], [...wf(69, 29.7), 11], [...wf(68, 29.7), 17]],
    cap: { ja: 'サン・マルコ寺院', en: "St Mark's Basilica" } },
  { name: 'florian', bars: [5, 6], kind: 'walk', path: [[-58.42, -50.05], [-57.99, -51.17]], yaw: [[0, -1.38], [1, -1.02]], pitch: 0.0,
    cap: { ja: 'カフェ・フローリアン', en: 'Caffè Florian' } },
  { name: 'fenice', bars: [6, 7], kind: 'walk', path: [[-430.3, -62.7], [-432.11, -63.55]], yaw: -2.703, pitch: [[0, 0.02], [1, 0.12]],
    cap: { ja: 'フェニーチェ劇場', en: 'La Fenice' } },
  { name: 'calle', bars: [7, 8], kind: 'walk', path: [[-463, 1163.3], [-465.48, 1159.76], [-466.8, 1158.2]], bright: 1.15,
    cap: { ja: '路地を歩く', en: 'Through the calli' } },
  { name: 'bridge', bars: [8, 9], kind: 'walk', path: [[-478.6, 1119.0], [-480.6, 1115.7], [-482.4, 1113.4]], yaw: [[0, -2.215], [0.4, -2.1], [0.85, -1.15], [1, -1.1]],
    cap: { ja: '橋を渡る', en: 'Over the bridges' } },
  { name: 'canal', bars: [9, 10], kind: 'walk', path: [[-497.5, 1131], [-503.5, 1135.3]], yawOff: 0.3,
    cap: { ja: '運河沿いを歩く', en: 'Along the canals' } },
  { name: 'flyday', bars: [10, 11], kind: 'fly', path: [[-372, 322, 48], [-312, 368, 42]], look: [[-238, 441, 10], [-238, 441, 10]],
    cap: { ja: '空から', en: 'From above' } },
  { name: 'nightpiazza', bars: [11, 12], night: true, bright: 1.35, kind: 'walk', path: [[-20, 23.5], [-14.5, 25.5]], lookAt: [[24.6, 43.0, 11], [24.6, 43.0, 11]],
    cap: { ja: '夜のサン・マルコ広場', en: 'The Piazza by night' } },
  { name: 'gondola', bars: [32, 34], night: true, bright: 1.2, kind: 'boat', route: 'grand', s0: 24, speed: 1.0, yaw: 0, pitch: [[0, 0.08], [1, 0.2]],
    cap: { ja: '夜のゴンドラ', en: 'A gondola at night' } },
  { name: 'flynight', bars: [34, 35], night: true, bright: 1.4, kind: 'fly', path: [[260, -210, 40], [180, -150, 32]], look: [[40, -60, 15], [40, -60, 15]],
    cap: { ja: '夜の空から', en: 'The city at night' } },
  { name: 'end', bars: [35, 36], tail: 4.0, night: true, bright: 1.4, kind: 'fly', path: [[-120, -560, 170], [-100, -540, 166]], look: [[10, -20, 20], [10, -20, 20]],
    title: { in: 0.4, out: 99, fin: 1.4, blend: 'normal', url: 'demos.kazumasa.workers.dev/venice' }, black: [5.2, 7.6, 0, 1] },
];
