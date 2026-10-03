// Compose the inner-dome mosaic texture (4096 x 2048; u = 16 segments, v from the oculus (top) to the
// springing (bottom)) from crops of the CC0 photo "2025-03-10 St. Peter's Basilica Inside".
import sharp from 'sharp'; import fs from 'fs';
const SRC = '/home/kazu/work/vatican-assets/refs/photos/2025-03-10_St._Peter_s_Basilica_Inside.jpg';
const OUT = 'ref/sp_dome_src.jpg';
const TW = 4096, TH = 2048, SW = TW / 16;
const crop = (l, t, w, h, rot = 0) => sharp(SRC).extract({ left: l, top: t, width: w, height: h }).rotate(rot, { background: '#6b4a1c' });
const C = {
  cherubA: await crop(2846, 3050, 360, 340).toBuffer(),
  cherubB: await crop(3298, 2940, 330, 320).toBuffer(),
  angelA: await crop(2905, 3420, 270, 560).toBuffer(),
  angelB: await crop(3470, 3300, 300, 560, -14).toBuffer(),
  angelC: await crop(2300, 3330, 260, 560, 12).toBuffer(),
  medA: await crop(500, 1500, 416, 416).toBuffer(),
  medB: await crop(440, 2348, 420, 420).toBuffer(),
  medC: await crop(757, 3090, 420, 420).toBuffer(),
};
const svgBuf = (w, h, body) => Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">${body}</svg>`);
const star = (cx, cy, r) => { let p = ''; for (let i = 0; i < 16; i++) { const a = i * Math.PI / 8, rr = i % 2 ? r * 0.38 : r; p += `${cx + rr * Math.sin(a)},${cy - rr * Math.cos(a)} `; } return `<polygon points="${p}" fill="#d9a83c"/>`; };
// background: pale gilded field per gore, a wide cream rib (gold edged) on every gore boundary with a thin blue
// starred strip on each side of it, and the blue starred ring under the oculus
let bg = `<rect width="${TW}" height="${TH}" fill="#cdb684"/>`;
for (let s = 0; s <= 16; s++) {
  const x = s * SW;
  bg += `<rect x="${x - 24}" y="0" width="48" height="${TH}" fill="#e9e0c8"/>`;
  bg += `<rect x="${x - 26}" y="0" width="5" height="${TH}" fill="#c9a24e"/><rect x="${x + 21}" y="0" width="5" height="${TH}" fill="#c9a24e"/>`;
  bg += `<rect x="${x - 3}" y="0" width="6" height="${TH}" fill="#d7c08a"/>`;
  for (let y = 60; y < TH; y += 150) bg += `<circle cx="${x}" cy="${y}" r="9" fill="#d4a845"/>`;
  for (const sx of [x - 44, x + 28]) {
    bg += `<rect x="${sx}" y="0" width="16" height="${TH}" fill="#2c3d66"/>`;
    for (let y = 30; y < TH; y += 48) bg += star(sx + 8, y, 7);
  }
}
for (let s = 0; s < 16; s++) for (let y = 120; y < TH; y += 96) bg += `<rect x="${s * SW + 120}" y="${y}" width="16" height="16" transform="rotate(45 ${s * SW + 128} ${y + 8})" fill="#d8b866" opacity="0.6"/>`;
bg += `<rect width="${TW}" height="80" fill="#22345e"/>`;
for (let x = 20; x < TW; x += 52) bg += star(x, 40, 14);
const comps = [{ input: svgBuf(TW, TH, bg), left: 0, top: 0 }];
const frame = (w, h, round = false) => svgBuf(w, h, round
  ? `<circle cx="${w / 2}" cy="${h / 2}" r="${w / 2 - 5}" fill="none" stroke="#e8cf8a" stroke-width="10"/><circle cx="${w / 2}" cy="${h / 2}" r="${w / 2 - 14}" fill="none" stroke="#8a5a1e" stroke-width="4"/>`
  : `<rect x="4" y="4" width="${w - 8}" height="${h - 8}" fill="none" stroke="#e8cf8a" stroke-width="9"/><rect x="13" y="13" width="${w - 26}" height="${h - 26}" fill="none" stroke="#9a6a24" stroke-width="4"/>`);
const tiers = [
  { y: 92, h: 140, kind: 'cherub' }, { y: 250, h: 300, kind: 'angel' }, { y: 570, h: 180, kind: 'med' },
  { y: 770, h: 370, kind: 'angel' }, { y: 1160, h: 190, kind: 'med' }, { y: 1370, h: 640, kind: 'angel' },
];
for (let s = 0; s < 16; s++) {
  const x0 = s * SW + 50, w = SW - 100;
  for (const [ti, t] of tiers.entries()) {
    let key, ww = w, hh = t.h, round = false;
    if (t.kind === 'cherub') { key = s % 2 ? 'cherubA' : 'cherubB'; ww = Math.min(w, 170); }
    else if (t.kind === 'med') { key = ['medA', 'medB', 'medC'][(s + ti) % 3]; ww = hh = Math.min(w, t.h); round = true; }
    else key = ['angelA', 'angelB', 'angelC'][(s * 2 + ti) % 3];
    let img = sharp(C[key]).resize(ww - (round ? 0 : 20), hh - (round ? 0 : 20), { fit: 'cover' }).modulate({ brightness: 1.5, saturation: 0.82 });
    if (s % 2) img = img.flop();
    if (round) img = img.composite([{ input: svgBuf(ww, hh, `<circle cx="${ww / 2}" cy="${hh / 2}" r="${ww / 2 - 6}" fill="#fff"/>`), blend: 'dest-in' }]);
    const left = x0 + Math.round((w - ww) / 2);
    comps.push({ input: await img.png().toBuffer(), left: left + (round ? 0 : 10), top: t.y + (round ? 0 : 10) });
    if (t.kind !== 'cherub') comps.push({ input: frame(ww, hh, round), left, top: t.y });
  }
}
await sharp({ create: { width: TW, height: TH, channels: 3, background: '#7a5420' } }).composite(comps).modulate({ brightness: 1.08, saturation: 1.0 }).jpeg({ quality: 86 }).toFile(OUT);
await sharp(OUT).resize(1600).toFile(process.argv[2] || '/tmp/dome_small.jpg');
console.log('dome texture written');
