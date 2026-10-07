// film_shots.mjs — the shot list of film.mjs (KYOTO).  bars: [from, to) of the Aria as the app plays it (the film plays bars
// 0-9, then the last four, 60-63, with the closing ritardando); kinds: walk (path on the ground, eye from the walk raster),
// fly (path + look-at path).  cap: the caption; title: the wordmark; tail: seconds held after the last bar (the final
// chord rings); winter: the snowy evening.
export const CUT = { a1: 10, b0: 60, b1: 64 };
const fwd = (x, y, yaw, d) => [x + Math.cos(yaw) * d, y + Math.sin(yaw) * d];
export const SHOTS = [
  { name: 'open', bars: [0, 2], kind: 'fly', ease: 'inout',
    path: [[700, 700, 300], [1150, 870, 235], [1520, 990, 185]], look: [[2420, 990, 70], [2420, 990, 70], [2420, 990, 70]],
    title: { in: 1.2, out: 7.6, sub: '紅葉と雪の夕暮れを、歩いて、空から。' } },
  { name: 'kiyomizu', bars: [2, 3], kind: 'walk', path: [[2433.6, 969.9], fwd(2433.6, 969.9, 2.72, 1.8)], yaw: 2.72, pitch: -0.05,
    cap: { ja: '清水寺', en: 'Kiyomizu-dera' } },
  { name: 'torii', bars: [3, 4], kind: 'walk', path: [fwd(1461.2, -2091.3, -0.71, 1.4), fwd(1461.2, -2091.3, -0.71, 7.8)], pitch: 0.03,
    cap: { ja: '伏見稲荷大社 千本鳥居', en: 'Fushimi Inari, the thousand torii' } },
  { name: 'hall', bars: [4, 5], kind: 'walk', path: [[1188.9, 258.0], [1189.2, 265.0]], yaw: [[0, 1.95], [1, 1.85]], pitch: 0.07, eye: 1.55, bright: 1.9,
    cap: { ja: '三十三間堂', en: 'Sanjūsangen-dō' } },
  { name: 'tofukuji', bars: [5, 6], kind: 'fly', path: [[1357.2, -946.3, 49.35], [1357.2, -946.0, 49.35]], yaw: [[0, 2.98], [1, 2.72]], pitch: -0.13,
    cap: { ja: '東福寺 通天橋', en: 'Tōfuku-ji, Tsūten-kyō' } },
  { name: 'toji', bars: [6, 7], kind: 'walk', path: [[-929.0, -596.5], [-930.0, -601.5]], lookAt: [[-920, -657, 41], [-920, -657, 43]],
    cap: { ja: '東寺 五重塔', en: 'Tō-ji, the five-storey pagoda' } },
  { name: 'yasaka', bars: [7, 8], kind: 'walk', path: [[1949.6, 1368.5], fwd(1949.6, 1368.5, 2.653, 6.0)], yaw: 2.653, pitch: 0.07,
    cap: { ja: '八坂の塔', en: 'The Yasaka Pagoda' } },
  { name: 'kamo', bars: [8, 9], kind: 'walk', path: [[1143.7, 3227.5], [1144.0, 3223.2]], yaw: [[0, -1.22], [1, -1.3]], pitch: -0.06,
    cap: { ja: '鴨川', en: 'The Kamo River' } },
  { name: 'eikando', bars: [9, 10], kind: 'walk', path: [[3277.7, 3125.4], [3277.5, 3128.6]], yaw: 1.633, pitch: 0.03,
    cap: { ja: '永観堂', en: 'Eikandō' } },
  { name: 'gion', bars: [60, 61], winter: true, kind: 'walk', path: [[1482.0, 1990.0], fwd(1482.0, 1990.0, -1.715, 6.0)], yaw: -1.715, pitch: 0.03,
    cap: { ja: '雪の祇園 花見小路', en: 'Gion in the snow' } },
  { name: 'kinkaku', bars: [61, 62], winter: true, kind: 'fly', path: [[-2745.4, 5914.4, 97.2], [-2749.7, 5922.0, 97.15]], look: [[-2768.3, 5955.3, 102.5], [-2768.3, 5955.3, 102.8]],
    cap: { ja: '雪の金閣寺', en: 'Kinkaku-ji in the snow' } },
  { name: 'bamboo', bars: [62, 63], kind: 'walk', path: [[-7790.0, 3532.3], fwd(-7790.0, 3532.3, -2.87, 7.0)], pitch: 0.1,
    cap: { ja: '嵐山 竹林の小径', en: 'Arashiyama, the bamboo grove' } },
  { name: 'end', bars: [63, 64], tail: 4.0, kind: 'fly', path: [[-6650, 2280, 330], [-6820, 2440, 300]], look: [[-7400, 3060, 60], [-7400, 3060, 60]],
    title: { in: 0.5, out: 99, fin: 1.4, blend: 'normal', url: 'demos.kazumasa.workers.dev/kyoto' }, black: [6.6, 9.2, 0, 1] },
];
