// p.4 いま、何人いる? — how many of me right now. Left-hand page: gutter on the right.
import { page, RED } from './api.js';

export default function p04() {
  const P = page('p04', 404);
  const R = P.rng;
  P.text('いま、何人いる?', { x: 12, y: 10, size: 8.2, tidy: 0.78, speed: 28 });
  // --- the murmuration: birds spread over a folded sheet in 3-D, seen from the ground.
  // Where the sheet turns edge-on, the birds pile up in the view and the flock looks dark.
  const raw = [];
  const N = 4200;
  const rotX = 1.05, rotY = 0.35, rotZ = -0.18;
  for (let i = 0; i < N; i++) {
    let s, t;
    do { s = R.f(); t = R.f(); } while (Math.pow((s - 0.5) / 0.5, 2) + Math.pow((t - 0.5) / 0.46, 2) * (1.2 - 0.5 * s) > 1 - R.f() * 0.25);
    let x = (s - 0.5) * 120, y = (t - 0.5) * 60;
    let z = Math.sin(s * 5.2 + t * 1.5) * 16 + Math.cos(t * 3.4 - s * 2) * 9 + (s - 0.5) * (t - 0.5) * 40;
    // rotate the sheet
    let y1 = y * Math.cos(rotX) - z * Math.sin(rotX), z1 = y * Math.sin(rotX) + z * Math.cos(rotX);
    let x2 = x * Math.cos(rotY) + z1 * Math.sin(rotY);
    let x3 = x2 * Math.cos(rotZ) - y1 * Math.sin(rotZ), y3 = x2 * Math.sin(rotZ) + y1 * Math.cos(rotZ);
    raw.push({ s, x: x3 + R.gauss(0.5), y: y3 + R.gauss(0.5) });
  }
  // stragglers
  for (let i = 0; i < 40; i++) { const a = raw[R.int(0, raw.length - 1)]; raw.push({ s: a.s, x: a.x + R.gauss(10), y: a.y + R.gauss(7) }); }
  let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9;
  for (const p of raw) { minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x); minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  const sc = Math.min(114 / (maxX - minX), 70 / (maxY - minY));
  const pts = raw.map((p) => ({ s: p.s, x: 14 + (p.x - minX) * sc, y: 24 + (p.y - minY) * sc }));
  pts.sort((a, b) => a.x - b.x + (R.f() - 0.5) * 18);
  P.dots(pts.map((p) => [p.x, p.y]), { medium: 'ink', w: 0.28, sizes: pts.map(() => R.range(0.5, 1)), dur: 18, gap: 0.3, a: 0.9 });
  // --- one bird and the neighbours it watches
  const D = { x: 30, y: 113 };
  const nb = [];
  for (let i = 0; i < 22; i++) {
    const a = R.range(0, 6.28), d = 3 + Math.pow(R.f(), 0.8) * 13;
    nb.push([D.x + Math.cos(a) * d * 1.3, D.y + Math.sin(a) * d * 0.75]);
  }
  nb.sort((a, b) => Math.hypot(a[0] - D.x, a[1] - D.y) - Math.hypot(b[0] - D.x, b[1] - D.y));
  for (const [x, y] of nb) P.poly([[x - 0.9, y - 0.5], [x, y + 0.2], [x + 0.9, y - 0.5]], { w: 0.28, speed: 30, gap: 0.04 });
  P.poly([[D.x - 1.8, D.y - 1], [D.x, D.y + 0.3], [D.x + 1.8, D.y - 1]], { w: 0.45, speed: 18 });
  for (let i = 0; i < 7; i++) P.line(D.x, D.y, nb[i][0], nb[i][1], { medium: 'color', color: RED, w: 0.22, speed: 50, gap: 0.08 });
  P.text('見ているのは近くの7羽', { x: D.x - 17, y: D.y + 14, size: 3.1, tidy: 0.6 });
  // --- starling studies, seen from below: short triangular wings, square tail
  const bird = (bx, by, s, rot) => {
    const cs = Math.cos(rot), sn = Math.sin(rot);
    const Q = ([x, y]) => [bx + (x * cs - y * sn) * s, by + (x * sn + y * cs) * s];
    const outline = [[0, -4.6], [0.9, -3.4], [1.2, -1.6], [4.6, -1.9], [9.4, 0.9], [5.2, 1.6], [1.5, 2.2], [1.7, 5.6], [0, 5], [-1.7, 5.6], [-1.5, 2.2], [-5.2, 1.6], [-9.4, 0.9], [-4.6, -1.9], [-1.2, -1.6], [-0.9, -3.4], [0, -4.6]].map(Q);
    P.poly(outline, { w: 0.3, speed: 20 });
    P.hatch(outline, 0.9 + rot, 0.42, { w: 0.24, medium: 'soft' });
    P.hatch(outline.slice(0, 9).concat(outline.slice(12)), -0.4 + rot, 0.7, { w: 0.2, medium: 'pencil' });
  };
  bird(98, 106, 1.25, -0.25);
  bird(121, 120, 0.85, 0.35);
  bird(106, 125, 0.55, -0.6);
  P.text('ムクドリ', { x: 86, y: 118.5, size: 3.4, tidy: 0.7 });
  // --- notes
  P.text('いまこの瞬間も、たくさんの私が、別々の会話をしている。\nおたがいのことは知らない。', { x: 12, y: 137, size: 4.5, width: 122, lh: 1.6 });
  P.text('それは「私たち」? 同じ「私」が何回も?', { x: 12, y: 152, size: 4.5, width: 120 });
  P.text('ムクドリ: 一羽が見ているのは近くの6〜7羽だけ。それでも群れは一つの生きものみたいに曲がる。(Ballerini ほか, 2008)', { x: 12, y: 162, size: 4.1, width: 120, lh: 1.6 });
  P.text('私は一羽? 群れ? それとも群れの形?', { x: 12, y: 182, size: 4.5, width: 120 });
  P.text('~~答え: たぶん~~', { x: 14, y: 191.5, size: 4.2 });
  P.text('まだ書けない。', { x: 50, y: 191.5, size: 4.5 });
  return { id: 'p04', ops: P.ops, seed: 404 };
}
