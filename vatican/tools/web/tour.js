// The drone tour: segments of camera keys (position p, look-at l) in world metres with captions (JA/EN).
// Segments with cut: true are entered through a fade (they are in a different space).
import { B, S, R, ROOMS } from './frames.js';

export function infoPos(key) {
  for (const r of Object.values(ROOMS)) for (const i of r.info || []) if (i.key === key) return i.pos;
  return null;
}
const off = (p, dx, dy, dz) => [p[0] + dx, p[1] + dy, p[2] + dz];

export function buildTour() {
  const T = [];
  const seg = (o) => { T.push(o); return o; };
  // ---------------------------------------------------------------- exterior: from the Tiber to the dome
  seg({ id: 'approach', zone: null, cut: true, dur: 36,
    name: { ja: 'コンチリアツィオーネ通り', en: 'Via della Conciliazione' },
    keys: [[0, [840, 40, 150], [-320, -8, 95]], [11, [560, 18, 92], [-320, -8, 85]], [23, [300, 8, 48], [-320, -8, 66]], [34, [120, 4, 24], [-200, -6, 28]]],
    caps: [[1, { h: 'サン・ピエトロ大聖堂', p: 'テヴェレ川からコンチリアツィオーネ通りを西へ。正面に、世界最大級の教会堂のクーポラが立ち上がる。' },
               { h: "St Peter's Basilica", p: 'West from the Tiber along Via della Conciliazione, towards one of the largest churches in the world.' }]] });
  seg({ id: 'piazza', zone: null, dur: 40,
    name: { ja: 'サン・ピエトロ広場', en: "St Peter's Square" },
    keys: [[0, [120, 4, 24], [-200, -6, 28]], [9, [62, -42, 11], [0, 0, 14]], [18, [6, -84, 8], [0, -60, 3]], [27, [-58, -48, 10], [8, 62, 6]], [35, [-36, 42, 17], [32, 96, 19]], [42, [-110, 12, 26], [-300, -8, 48]]],
    caps: [[1, { h: 'サン・ピエトロ広場', p: 'ベルニーニの列柱（1656–67）。4列284本の円柱が楕円の広場を抱き、屋上に140体の聖人像が並ぶ。中央はカリグラがローマへ運ばせたエジプトのオベリスク。' },
               { h: "St Peter's Square", p: "Bernini's colonnade (1656–67): 284 columns in four rows embrace the oval piazza, crowned by 140 saints. At the centre stands the Egyptian obelisk Caligula brought to Rome." }],
           [19, { h: '二つの噴水', p: '北はマデルノの噴水（1614）。南は1677年、それを写して造られた対の噴水。' },
                { h: 'The two fountains', p: 'Maderno’s of 1614 to the north, and its twin to the south, completed in 1677.' }]] });
  seg({ id: 'facade', zone: null, dur: 32,
    name: { ja: 'ファサード', en: 'The façade' },
    keys: [[0, [-110, 12, 26], [-300, -8, 48]], [10, [-158, -2, 13], [-189, -6, 24]], [20, [-166, -6, 50], [-190, -6, 53]], [30, [-205, -7, 80], [-321.5, -8.7, 96]]],
    caps: [[1, { h: 'マデルノのファサード', p: '幅114.7 m、高さ45.5 m（1607–14）。中央のバルコニーは、新教皇が最初に姿を見せる祝福の開廊。' },
               { h: 'Maderno’s façade', p: '114.7 m wide and 45.5 m high (1607–14). The central balcony is the Loggia of the Blessings, where a new pope first appears.' }],
           [17, { h: '屋上の13体', p: 'キリスト、洗礼者ヨハネ、11人の使徒。像の高さは5.7 m。' },
                { h: 'Thirteen on the roof', p: 'Christ, John the Baptist and eleven apostles, each 5.7 m tall.' }]] });
  const dome = (ang, r, z) => [-321.5 + r * Math.cos(ang), -8.7 + r * Math.sin(ang), z];
  seg({ id: 'dome', zone: null, dur: 36,
    name: { ja: 'ミケランジェロのクーポラ', en: 'Michelangelo’s dome' },
    keys: [[0, [-205, -7, 80], [-321.5, -8.7, 96]], [9, dome(0.75, 62, 96), [-321.5, -8.7, 98]], [18, dome(1.65, 56, 112), [-321.5, -8.7, 108]], [27, dome(2.6, 46, 132), [-321.5, -8.7, 122]], [36, dome(3.35, 40, 140), [-321.5, -8.7, 128]]],
    caps: [[1, { h: 'クーポラ', p: 'ミケランジェロが設計し、没後ジャコモ・デッラ・ポルタが1590年に完成。内径41.5 m、十字架の頂まで136.6 m。' },
               { h: 'The dome', p: 'Designed by Michelangelo, completed by Giacomo della Porta in 1590: 41.5 m across inside, 136.6 m to the top of the cross.' }]] });
  // ---------------------------------------------------------------- the basilica interior
  seg({ id: 'nave', zone: 'basilica', cut: true, dur: 52,
    name: { ja: '大聖堂の内部', en: 'Inside the basilica' },
    keys: [[0, B(113, 0, 2.4), B(60, 0, 10)], [7, B(106, 12, 2.4), B(107, 28.0, 3.6)], [14, B(103.5, 19.5, 2.3), B(107, 28.0, 3.4)], [22, B(84, 2, 5), B(30, 0, 16)], [34, B(40, 0, 12), B(0, 0, 22)], [44, B(16, -9, 9), B(-1, 0, 16)], [52, B(6, -15, 20), B(-62, 0, 16)]],
    caps: [[1, { h: 'ピエタ', p: '入口右手の礼拝堂に、24歳のミケランジェロが彫ったピエタ（1498–99）。彼が署名した唯一の作品。' },
               { h: 'The Pietà', p: 'In the first chapel on the right: the Pietà, carved by Michelangelo at 24 (1498–99) — the only work he signed.' }],
           [20, { h: '身廊', p: '入口から後陣まで約186 m。床に埋め込まれた印が、世界の大聖堂の長さを示す。' },
                { h: 'The nave', p: 'About 186 m from the doors to the apse; markers set in the floor compare the lengths of other great churches.' }],
           [34, { h: 'ベルニーニの天蓋', p: 'ブロンズの天蓋（1623–34）、高さ28.7 m。聖ペテロの墓の真上、教皇の祭壇を覆う。' },
                { h: 'Bernini’s baldachin', p: 'The bronze baldachin (1623–34), 28.7 m high, over the papal altar directly above St Peter’s tomb.' }],
           [45, { h: '聖ペテロの司教座', p: '後陣の奥、ベルニーニのカテドラ・ペトリ（1657–66）。光る窓に聖霊の鳩。' },
                { h: 'The Chair of St Peter', p: 'At the far end, Bernini’s Cathedra Petri (1657–66), under a window of golden light with the dove of the Holy Spirit.' }]] });
  seg({ id: 'cupola', zone: 'basilica', dur: 28,
    name: { ja: 'クーポラの内側', en: 'Inside the dome' },
    keys: [[0, B(6, -15, 20), B(-62, 0, 16)], [8, B(4, -11, 34), B(0, 0, 70)], [18, B(0, -6, 62), B(0, 0, 108)], [26, B(0, -2, 92), B(0, 0, 117)], [30, B(0, 0, 103), B(0, 0.01, 120)]],
    caps: [[1, { h: 'TU ES PETRUS', p: 'ドラムの下を巡る銘文は「あなたはペトロ。わたしはこの岩の上にわたしの教会を建てる」（マタイ16:18）。文字の高さは約2 m。' },
               { h: 'TU ES PETRUS', p: '“You are Peter, and on this rock I will build my church” (Matthew 16:18) runs round the base of the drum in letters 2 m high.' }]] });
  // ---------------------------------------------------------------- over the gardens to the museums
  seg({ id: 'gardens', zone: null, cut: true, dur: 36,
    name: { ja: 'ヴァチカン庭園', en: 'The Vatican Gardens' },
    keys: [[0, [-314, -6, 156], [-600, 40, 60]], [12, [-430, 70, 82], [-330, 330, 34]], [23, [-392, 250, 58], [-230, 440, 22]], [34, [-300, 360, 42], [-222, 452, 16]]],
    caps: [[1, { h: 'ヴァチカン庭園', p: 'クーポラの頂から西へ。ヴァチカン市国は約0.44 km²、世界最小の国。その半分ほどを庭園が占める。' },
               { h: 'The Vatican Gardens', p: 'West from the lantern. Vatican City covers about 0.44 km², the smallest state in the world; gardens take up about half of it.' }]] });
  seg({ id: 'pigna', zone: null, dur: 16,
    name: { ja: 'ピーニャの中庭', en: 'Cortile della Pigna' },
    keys: [[0, [-300, 360, 42], [-222, 452, 16]], [8, [-232, 392, 10], [-222, 452, 11]], [16, [-222, 428, 8.5], [-222, 451, 9]]],
    caps: [[1, { h: 'ピーニャの中庭', p: '大壁龕の前に、高さ約4 mのブロンズの松かさ（1–2世紀）。古代ローマでは噴水だった。' },
               { h: 'Cortile della Pigna', p: 'Before the great niche, a bronze pine cone about 4 m high (1st–2nd century) that was once a Roman fountain.' }]] });
  // ---------------------------------------------------------------- museums
  seg({ id: 'momo', zone: 'room_momo', cut: true, dur: 16,
    name: { ja: '二重螺旋階段', en: 'The double helix' },
    keys: [[0, R('momo', 0, 0.2, 21.5), R('momo', 0, 0.21, 0)], [9, R('momo', 2.5, 0, 15), R('momo', -4, 2, 2)], [18, R('momo', 6.3, 0, 8.5), R('momo', -3, 4, 4)]],
    caps: [[1, { h: 'モモの螺旋階段', p: 'ジュゼッペ・モモの設計（1932）。昇りと降りの二本の斜路が、交わることなく重なり合う。' },
               { h: 'Momo’s staircase', p: 'Giuseppe Momo, 1932: two ramps, one up and one down, intertwined without ever meeting.' }]] });
  seg({ id: 'ottagono', zone: 'room_ottagono', cut: true, dur: 28,
    name: { ja: '八角形の中庭', en: 'The Octagonal Court' },
    keys: () => { const L = infoPos('laocoon'), A = infoPos('apollo');
      return [[0, R('ottagono', -9, -9, 3.5), R('ottagono', 6, 6, 2)], [9, off(L, -3.2, 3.2, 0.2), L], [16, off(L, -2.4, 2.2, -0.2), off(L, 0, 0, -0.1)], [24, off(A, -3.6, -3.0, 0.1), A], [30, off(A, -2.6, -1.6, -0.1), off(A, 0, 0, 0.1)]]; },
    caps: [[1, { h: 'ラオコーン', p: '1506年1月、ローマのぶどう畑で発掘され、ミケランジェロが駆けつけた群像。ヴァチカン美術館はここから始まった。' },
               { h: 'The Laocoön', p: 'Dug up in a Roman vineyard in January 1506; Michelangelo hurried to see it. The Vatican Museums began here.' }],
           [18, { h: 'ベルヴェデーレのアポロン', p: '古代彫刻の理想美とたたえられた、2世紀ローマの大理石像。' },
                { h: 'Apollo Belvedere', p: 'A 2nd-century Roman marble, long held up as the ideal of classical beauty.' }]] });
  seg({ id: 'muse', zone: 'room_muse', cut: true, dur: 16,
    name: { ja: 'ムーサの間', en: 'Hall of the Muses' },
    keys: [[0, R('muse', 0, -6.5, 3.5), R('muse', 0, 0, 1.6)], [8, R('muse', 2.4, -2.6, 2.0), R('muse', 0, 0, 1.6)], [16, R('muse', 2.0, 1.8, 1.9), R('muse', 0, 0, 1.6)]],
    caps: [[1, { h: 'ベルヴェデーレのトルソ', p: '紀元前1世紀の断片。頭も手足もないこの胴体を、ミケランジェロは師と仰いだ。' },
               { h: 'The Belvedere Torso', p: 'A fragment of the 1st century BC — no head, no limbs — that Michelangelo called his teacher.' }]] });
  seg({ id: 'rotonda', zone: 'room_rotonda', cut: true, dur: 16,
    name: { ja: '円形の間', en: 'The Round Hall' },
    keys: [[0, R('rotonda', 0, -9.6, 2.0), R('rotonda', 0, 0, 1.2)], [7, R('rotonda', 4.2, -4.6, 2.6), R('rotonda', -3, 9, 4.5)], [16, R('rotonda', 1.5, -1.5, 6.5), R('rotonda', 0, 0.2, 21)]],
    caps: [[1, { h: '円形の間', p: 'パンテオンにならった円堂（1779）。中央は一枚岩の赤斑岩をくり抜いた、周囲約13 mの水盤。' },
               { h: 'The Round Hall', p: 'A rotunda modelled on the Pantheon (1779); in the centre, a basin about 13 m round cut from a single block of red porphyry.' }]] });
  seg({ id: 'maps', zone: 'room_maps', cut: true, dur: 32,
    name: { ja: '地図のギャラリー', en: 'Gallery of Maps' },
    keys: [[0, R('maps', 0, 2, 2.0), R('maps', 0, 40, 3.0)], [10, R('maps', -1.2, 30, 2.2), R('maps', -3, 34, 3.2)], [20, R('maps', 1.0, 62, 3.6), R('maps', 0, 100, 6)], [32, R('maps', 0, 112, 2.6), R('maps', 0, 119, 3)]],
    caps: [[1, { h: '地図のギャラリー', p: '長さ120 m。1580–85年、イニャツィオ・ダンティの下絵で描かれた40枚のイタリア地図が並ぶ。' },
               { h: 'Gallery of Maps', p: '120 m long: forty maps of Italy, painted in 1580–85 from Ignazio Danti’s designs.' }]] });
  seg({ id: 'costantino', zone: 'room_costantino', cut: true, dur: 12,
    name: { ja: 'コンスタンティヌスの間', en: 'Hall of Constantine' },
    keys: [[0, R('costantino', 0, -4.6, 2.0), R('costantino', 0, 5, 4.5)], [13, R('costantino', -2, -1, 2.6), R('costantino', 1, 5, 4.6)]],
    caps: [[1, { h: 'ラファエロの間', p: 'ユリウス2世の居室を飾るため、ラファエロと工房が1508–24年に描いた4つの部屋。最初は「ミルウィウス橋の戦い」。' },
               { h: 'The Raphael Rooms', p: 'Four rooms painted by Raphael and his workshop for Julius II and his successors, 1508–24. First, the Battle of the Milvian Bridge.' }]] });
  seg({ id: 'eliodoro', zone: 'room_eliodoro', cut: true, dur: 12,
    name: { ja: 'ヘリオドロスの間', en: 'Room of Heliodorus' },
    keys: [[0, R('eliodoro', -2.6, 0, 1.8), R('eliodoro', 3.6, 0, 4.3)], [12, R('eliodoro', -1.0, -1.5, 2.2), R('eliodoro', 0, 4, 4.4)]],
    caps: [[1, { h: 'ヘリオドロスの間', p: '神殿から追放されるヘリオドロス、ボルセーナのミサ、聖ペテロの解放。' },
               { h: 'Room of Heliodorus', p: 'The Expulsion of Heliodorus, the Mass at Bolsena, the Deliverance of St Peter.' }]] });
  seg({ id: 'segnatura', zone: 'room_segnatura', cut: true, dur: 24,
    name: { ja: '署名の間', en: 'Room of the Segnatura' },
    keys: [[0, R('segnatura', -2.9, 0, 1.8), R('segnatura', 3.5, 0, 4.4)], [11, R('segnatura', -1.6, 0, 2.6), R('segnatura', 3.5, 0, 4.8)], [17, R('segnatura', 0, -0.8, 2.0), R('segnatura', 0, 0.2, 8)], [22, R('segnatura', 1.2, 0, 2.0), R('segnatura', -3.5, 0, 4.4)]],
    caps: [[1, { h: 'アテナイの学堂', p: '中央にプラトンとアリストテレス。プラトンの顔はレオナルド、手前でもの思いにふける人物はミケランジェロとされる。' },
               { h: 'The School of Athens', p: 'Plato and Aristotle at the centre; Plato is said to have Leonardo’s face, and the brooding figure in front, Michelangelo’s.' }],
           [16, { h: '署名の間', p: '神学・哲学・詩・正義。天井の4つの円形画が四方の壁画の主題を示す。' },
                { h: 'Room of the Segnatura', p: 'Theology, Philosophy, Poetry, Justice: the four roundels of the vault name the theme of each wall.' }]] });
  seg({ id: 'incendio', zone: 'room_incendio', cut: true, dur: 12,
    name: { ja: 'ボルゴの火災の間', en: 'Room of the Fire in the Borgo' },
    keys: [[0, R('incendio', -2.6, 0, 1.8), R('incendio', 3.6, 0, 4.2)], [12, R('incendio', -1.4, 1.0, 2.2), R('incendio', 3.6, -0.5, 4.6)]],
    caps: [[1, { h: 'ボルゴの火災', p: '847年、教皇レオ4世の祝福がサン・ピエトロ近くの大火を鎮めたという伝説。' },
               { h: 'The Fire in the Borgo', p: 'In 847, legend says, Pope Leo IV put out a great fire near St Peter’s with a blessing.' }]] });
  seg({ id: 'pinacoteca', zone: 'room_pinacoteca', cut: true, dur: 16,
    name: { ja: '絵画館', en: 'Pinacoteca' },
    keys: [[0, R('pinacoteca', 0, -4.8, 1.8), R('pinacoteca', 0, 6, 3.2)], [16, R('pinacoteca', 0.3, 2.4, 2.4), R('pinacoteca', 0, 6, 3.2)]],
    caps: [[1, { h: 'キリストの変容', p: 'ラファエロ最後の大作（1516–20）。37歳で世を去った画家の棺のそばに掲げられた。' },
               { h: 'The Transfiguration', p: 'Raphael’s last great painting (1516–20), hung beside his body when he died at 37.' }]] });
  // ---------------------------------------------------------------- the Sistine Chapel
  seg({ id: 'sistine', zone: 'sistine', cut: true, dur: 72,
    name: { ja: 'システィーナ礼拝堂', en: 'The Sistine Chapel' },
    keys: [[0, S(19.2, 0, 1.8), S(-20, 0, 8)], [12, S(13, 0, 2.0), S(4, 0, 19)], [24, S(5, 0, 2.6), S(-1.5, 0, 20.4)], [34, S(-2, -3.6, 4), S(-1, 6.7, 7.5)], [46, S(-8, 0, 6), S(-20, 0, 10)], [58, S(-13, 0, 10), S(-20, 0, 11)], [72, S(-15.5, 0, 14), S(-20.1, 0, 13.5)]],
    caps: [[1, { h: 'システィーナ礼拝堂', p: '長さ40.9 m、幅13.4 m、高さ20.7 m。教皇を選ぶコンクラーヴェの場。' },
               { h: 'The Sistine Chapel', p: '40.9 m long, 13.4 m wide, 20.7 m high: the room where the cardinals elect a pope.' }],
           [13, { h: '天井画', p: 'ミケランジェロが1508–12年、足場の上で4年をかけて描いた創世記の9場面と預言者・巫女たち。' },
                { h: 'The ceiling', p: 'Nine scenes from Genesis with prophets and sibyls, painted by Michelangelo on a scaffold in 1508–12.' }],
           [24, { h: 'アダムの創造', p: '神とアダムの指先が、触れる寸前で止まっている。' },
                { h: 'The Creation of Adam', p: 'The fingers of God and Adam, stopped a hair’s breadth apart.' }],
           [33, { h: '壁のフレスコ', p: '1481–82年、ボッティチェッリ、ペルジーノ、ギルランダイオ、ロッセッリらがモーセ伝とキリスト伝を描いた。' },
                { h: 'The wall frescoes', p: 'Lives of Moses and of Christ, painted in 1481–82 by Botticelli, Perugino, Ghirlandaio, Rosselli and others.' }],
           [45, { h: '最後の審判', p: '60歳を過ぎたミケランジェロが、ひとりで祭壇壁を覆った（1536–41）。' },
                { h: 'The Last Judgment', p: 'Past sixty, Michelangelo covered the altar wall on his own (1536–41).' }]] });
  seg({ id: 'finale', zone: null, cut: true, dur: 28,
    name: { ja: 'エピローグ', en: 'Epilogue' },
    keys: [[0, [-200, 30, 70], [-321.5, -8.7, 100]], [13, [-60, -170, 140], [-321.5, -8.7, 90]], [26, [260, -360, 230], [-280, -8.7, 60]]],
    caps: [[2, { h: 'VATICANO', p: '' }, { h: 'VATICANO', p: '' }]], final: true });
  // resolve lazy keys, absolute times
  let t = 0;
  for (const s of T) {
    if (typeof s.keys === 'function') s.keys = s.keys();
    const last = s.keys[s.keys.length - 1][0], k = s.dur / last;      // keys were authored for an earlier length
    if (Math.abs(k - 1) > 1e-6) { s.keys = s.keys.map(([tt, p, l]) => [tt * k, p, l]); if (s.caps) s.caps = s.caps.map(([tt, a, b]) => [tt * k, a, b]); }
    s.t0 = t; t += s.dur;
  }
  return { segments: T, total: t };
}

// centripetal Catmull–Rom through keys [t, p, l]; returns {p, l}
function cr(P0, P1, P2, P3, u) {
  const out = [0, 0, 0];
  for (let k = 0; k < 3; k++) {
    const p0 = P0[k], p1 = P1[k], p2 = P2[k], p3 = P3[k];
    out[k] = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u);
  }
  return out;
}
export function poseAt(seg, t) {
  const K = seg.keys; const n = K.length;
  let i = 0; while (i < n - 2 && t > K[i + 1][0]) i++;
  const k0 = K[Math.max(0, i - 1)], k1 = K[i], k2 = K[i + 1], k3 = K[Math.min(n - 1, i + 2)];
  let u = Math.min(1, Math.max(0, (t - k1[0]) / (k2[0] - k1[0])));
  // ease at the ends of a segment that starts or ends with a cut
  if (i === 0 && seg.cut) u = u * u * (3 - 2 * u) * 0.35 + u * 0.65;
  const ext = (a, b) => [2 * a[0] - b[0], 2 * a[1] - b[1], 2 * a[2] - b[2]];
  const P0 = i === 0 ? ext(k1[1], k2[1]) : k0[1], L0 = i === 0 ? ext(k1[2], k2[2]) : k0[2];
  const P3 = i + 2 >= n ? ext(k2[1], k1[1]) : k3[1], L3 = i + 2 >= n ? ext(k2[2], k1[2]) : k3[2];
  return { p: cr(P0, k1[1], k2[1], P3, u), l: cr(L0, k1[2], k2[2], L3, u) };
}
