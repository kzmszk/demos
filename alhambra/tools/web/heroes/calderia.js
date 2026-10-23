import * as THREE from 'three';
import { terrainHeight } from '../navigation.js';
import { plant, ORANGE, SHRUB, PLANE } from '../trees.js';

// Calle Calderería Nueva and its lanes (box x -725..-555, z -115..45): the city generator leaves this block
// empty; every building, shop front and lane here is modelled by this module.
//  - footprints, levels and lanes: OpenStreetMap (ODbL) via public/textures/calderia/layout.json (tools in
//    work/calderia/prep.py: roof plans, party walls, street-facing edges); shops/bars: OSM POIs (same file)
//  - all textures are procedural canvases made at start-up (no photographs are shipped)

// ---------------------------------------------------------------- utilities
const rnd = seed => { let s = seed | 0; return () => { s = (Math.imul(1664525, s) + 1013904223) | 0; return (s >>> 0) / 4294967296; }; };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const hyp = Math.hypot;
const cv = (w, h = w) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d', { willReadFrequently: true })]; };
const hsl = (h, s, l, a = 1) => `hsla(${h},${s}%,${l}%,${a})`;
function speckle(g, w, h, seed, amount = 10, n = 60000) {
  const r = rnd(seed), img = g.getImageData(0, 0, w, h), d = img.data;
  for (let i = 0; i < n; i++) {
    const v = r() > .5 ? 255 : 0, a = r() * amount / 100, x0 = r() * w | 0, y0 = r() * h | 0, ww = 1 + r() * 3 | 0, hh = 1 + r() * 3 | 0;
    for (let y = y0; y < Math.min(h, y0 + hh); y++) for (let x = x0; x < Math.min(w, x0 + ww); x++) { const k = (y * w + x) * 4; d[k] += (v - d[k]) * a; d[k + 1] += (v - d[k + 1]) * a; d[k + 2] += (v - d[k + 2]) * a; }
  }
  g.putImageData(img, 0, 0);
}
// draw a feature at the 9 wrap offsets so that a tile has no seam
function wrap(g, S, fn, SY = S) { for (const dx of [-S, 0, S]) for (const dy of [-SY, 0, SY]) { g.save(); g.translate(dx, dy); fn(); g.restore(); } }
function tex(c, { srgb = true, repeat = 1 } = {}) {
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = 8; return t;
}

// ---------------------------------------------------------------- canvas textures
function texRender(seed = 11, base = '#ece6d9') {
  const S = 512, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = base; g.fillRect(0, 0, S, S);
  for (let i = 0; i < 46; i++) {
    const x = r() * S, y = r() * S, R = 30 + r() * 100, a = .02 + r() * .05, dark = r() < .62;
    wrap(g, S, () => { const gr = g.createRadialGradient(x, y, 0, x, y, R); gr.addColorStop(0, dark ? `rgba(105,90,65,${a})` : `rgba(255,255,255,${a})`); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(x - R, y - R, R * 2, R * 2); });
  }
  for (let i = 0; i < 46; i++) {
    const x = r() * S, y0 = r() * S, w = 1 + r() * 6, h = 70 + r() * 220, a = .03 + r() * .06;
    wrap(g, S, () => { const gr = g.createLinearGradient(0, y0, 0, y0 + h); gr.addColorStop(0, `rgba(80,68,50,${a})`); gr.addColorStop(1, 'rgba(80,68,50,0)'); g.fillStyle = gr; g.fillRect(x, y0, w, h); });
  }
  // trowel / patch marks
  for (let i = 0; i < 16; i++) { const x = r() * S, y = r() * S, w = 40 + r() * 90, h = 30 + r() * 70; wrap(g, S, () => { g.fillStyle = `rgba(${r() < .5 ? '255,250,235' : '120,105,80'},${.03 + r() * .04})`; g.beginPath(); g.ellipse(x, y, w, h, r() * 3, 0, 7); g.fill(); }); }
  speckle(g, S, S, seed + 1, 7, 70000);
  // hairline cracks
  g.lineWidth = 1;
  for (let i = 0; i < 7; i++) { let x = r() * S, y = r() * S; g.strokeStyle = 'rgba(60,50,38,.20)'; g.beginPath(); g.moveTo(x, y); for (let k = 0; k < 9; k++) { x += (r() - .5) * 26; y += 6 + r() * 20; g.lineTo(x, y); } g.stroke(); }
  return c;
}
function texStone(seed = 21, tone = [38, 22, 70]) {
  const S = 512, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = hsl(tone[0], tone[1], tone[2]); g.fillRect(0, 0, S, S);
  const rows = 8, rh = S / rows; // 0.3 m courses on a 2.4 m tile
  for (let j = 0; j < rows; j++) {
    let x = -r() * 100; const y = j * rh;
    while (x < S) {
      const w = 90 + r() * 120;
      g.fillStyle = hsl(tone[0] + (r() - .5) * 8, tone[1] + (r() - .5) * 10, tone[2] + (r() - .5) * 14, .85); g.fillRect(x + 2, y + 2, w - 3, rh - 3);
      const gr = g.createLinearGradient(0, y, 0, y + rh); gr.addColorStop(0, 'rgba(255,255,255,.10)'); gr.addColorStop(1, 'rgba(0,0,0,.10)'); g.fillStyle = gr; g.fillRect(x + 2, y + 2, w - 3, rh - 3);
      x += w;
    }
  }
  g.strokeStyle = 'rgba(70,58,44,.55)'; g.lineWidth = 2;
  for (let j = 0; j <= rows; j++) { g.beginPath(); g.moveTo(0, j * rh); g.lineTo(S, j * rh); g.stroke(); }
  speckle(g, S, S, seed + 2, 12, 80000);
  return c;
}
function texBrick(seed = 31, tone = [14, 38, 52]) {
  const S = 512, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = '#9d8e78'; g.fillRect(0, 0, S, S);
  const bw = 64, bh = 20;
  for (let j = 0; j * bh < S; j++) for (let i = -1; i * bw < S; i++) {
    const x = i * bw + (j % 2) * bw / 2, y = j * bh;
    g.fillStyle = hsl(tone[0] + (r() - .5) * 12, tone[1] + (r() - .5) * 14, tone[2] + (r() - .5) * 16); g.fillRect(x + 2, y + 2, bw - 3, bh - 3);
    g.fillStyle = `rgba(255,235,200,${r() * .12})`; g.fillRect(x + 2, y + 2, bw - 3, 3);
  }
  speckle(g, S, S, seed + 2, 12, 90000);
  return c;
}
function texTile(seed = 41) {
  const S = 512, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = '#5c3022'; g.fillRect(0, 0, S, S);
  const cw = S / 11, ch = S / 4; // 11 Arab-tile channels across 2 m, courses of 0.5 m
  for (let row = 0; row < 4; row++) for (let k = 0; k < 11; k++) {
    const x = k * cw, y = row * ch + (k % 2) * ch * .5, hue = 14 + r() * 10, l = 38 + r() * 20, sat = 40 + r() * 22;
    for (const yy of [y, y - S]) {
      const gr = g.createLinearGradient(x, 0, x + cw, 0); gr.addColorStop(0, hsl(hue, sat, l * .5)); gr.addColorStop(.42, hsl(hue, sat, l)); gr.addColorStop(.8, hsl(hue + 2, sat - 4, l * 1.15)); gr.addColorStop(1, hsl(hue, sat, l * .5));
      g.fillStyle = gr; g.fillRect(x + 1, yy + 1, cw - 2, ch - 1);
      g.fillStyle = 'rgba(25,12,8,.55)'; g.fillRect(x, yy + ch - 4, cw, 4);
    }
    if (r() < .3) { g.fillStyle = `rgba(${150 + r() * 50},${150 + r() * 40},${100},${.25 + r() * .3})`; g.beginPath(); g.arc(x + cw / 2, y + r() * ch, 3 + r() * 9, 0, 7); g.fill(); }
  }
  speckle(g, S, S, seed + 1, 9, 50000);
  return c;
}
function texWood(seed = 51) {
  const S = 256, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = '#6a4a30'; g.fillRect(0, 0, S, S);
  const pw = 32;
  for (let i = 0; i < S / pw; i++) {
    g.fillStyle = hsl(26 + (r() - .5) * 6, 38 + r() * 12, 26 + r() * 14); g.fillRect(i * pw + 1, 0, pw - 2, S);
    for (let k = 0; k < 14; k++) { g.strokeStyle = `rgba(25,14,6,${.08 + r() * .14})`; g.lineWidth = 1; const x = i * pw + 2 + r() * (pw - 4); g.beginPath(); g.moveTo(x, 0); g.bezierCurveTo(x + (r() - .5) * 6, S / 3, x + (r() - .5) * 6, S * 2 / 3, x + (r() - .5) * 3, S); g.stroke(); }
    g.fillStyle = 'rgba(0,0,0,.35)'; g.fillRect(i * pw, 0, 1.5, S);
  }
  speckle(g, S, S, seed + 1, 8, 12000);
  return c;
}
function texPebble(seed = 61, bands = true) {
  // 6 m (lateral, x) by 3 m (along the lane, y); t = 0 at x = 512. A white pebble band down the middle and bands near the walls.
  const W = 1024, H = 512, [c, g] = cv(W, H), r = rnd(seed), ppm = W / 6;
  g.fillStyle = '#1f1e1d'; g.fillRect(0, 0, W, H);
  const sp = 8.6;
  const inBand = x => { if (!bands) return .035; const t = (x - W / 2) / ppm, a = Math.abs(t); return a < .15 ? 1 : (a > 1.42 && a < 1.78) ? .8 : (a > 1.3 && a < 1.9) ? .28 : 0; };
  for (let j = -1; j * sp < H + sp; j++) for (let i = -1; i * sp < W + sp; i++) {
    const x = (i + .5 + (j % 2) * .5) * sp + (r() - .5) * 2.5, y = (j + .5) * sp + (r() - .5) * 2.5;
    const light = r() < inBand(x);
    const rx = sp * (.55 + r() * .2), ry = sp * (.4 + r() * .2), an = r() * Math.PI;
    let col;
    if (light) col = hsl(36 + r() * 12, 6 + r() * 14, 68 + r() * 22);
    else if (r() < .08) col = hsl(24 + r() * 10, 18 + r() * 14, 34 + r() * 14);
    else col = hsl(205 + r() * 50, 3 + r() * 9, 17 + r() * 20);
    const ox = x < sp ? W : x > W - sp ? -W : 0, oy = y < sp ? H : y > H - sp ? -H : 0;
    for (const [dx, dy] of [[0, 0], [ox, 0], [0, oy], [ox, oy]]) {
      if ((dx || dy) === 0 && (dx !== 0 || dy !== 0)) continue;
      if (dx === 0 && dy === 0 && false) continue;
      g.fillStyle = col; g.beginPath(); g.ellipse(x + dx, y + dy, rx, ry, an, 0, 7); g.fill();
      g.fillStyle = 'rgba(255,255,255,.10)'; g.beginPath(); g.ellipse(x + dx - rx * .2, y + dy - ry * .25, rx * .5, ry * .4, an, 0, 7); g.fill();
      if (!ox && !oy) break;
    }
  }
  speckle(g, W, H, seed + 3, 8, 90000);
  return c;
}
function texSett(seed = 71, tone = [215, 4, 44]) {
  const S = 512, [c, g] = cv(S), r = rnd(seed);
  g.fillStyle = '#2b2a28'; g.fillRect(0, 0, S, S);
  const sw = 27, sh = 54;
  for (let j = 0; j * sh < S; j++) for (let i = -1; i * sw < S; i++) {
    const x = i * sw + (j % 2) * sw / 2, y = j * sh + (i % 3) * 3;
    g.fillStyle = hsl(tone[0] + (r() - .5) * 40, tone[1] + r() * 10, tone[2] + (r() - .5) * 22); g.fillRect(x + 1.5, y + 1.5, sw - 3, sh - 3);
    g.fillStyle = 'rgba(255,255,255,.07)'; g.fillRect(x + 2, y + 2, sw - 4, 3);
  }
  speckle(g, S, S, seed + 1, 14, 90000);
  return c;
}
function texAsphalt(seed = 81) {
  const S = 256, [c, g] = cv(S); g.fillStyle = '#4a4b4c'; g.fillRect(0, 0, S, S); speckle(g, S, S, seed, 22, 60000); return c;
}
// merchandise atlas: 4 x 4 tiles of 256 px
function texGoods() {
  const S = 1024, T = 256, [c, g] = cv(S), r = rnd(91);
  const tile = (i, fn) => { g.save(); g.translate((i % 4) * T, Math.floor(i / 4) * T); g.beginPath(); g.rect(0, 0, T, T); g.clip(); fn(); g.restore(); };
  const fringe = (col = '#e8dcc0') => { g.strokeStyle = col; g.lineWidth = 1.5; for (let x = 4; x < T; x += 5) { g.beginPath(); g.moveTo(x, T - 14); g.lineTo(x + (r() - .5) * 3, T); g.stroke(); g.beginPath(); g.moveTo(x, 0); g.lineTo(x + (r() - .5) * 3, 14); g.stroke(); } };
  tile(0, () => { g.fillStyle = '#7a1c1c'; g.fillRect(0, 0, T, T); g.strokeStyle = '#d9b46a'; g.lineWidth = 6; g.strokeRect(14, 14, T - 28, T - 28); g.strokeStyle = '#1d2f55'; g.lineWidth = 8; g.strokeRect(30, 30, T - 60, T - 60); g.fillStyle = '#1d2f55'; g.beginPath(); g.moveTo(T / 2, 58); g.lineTo(T - 60, T / 2); g.lineTo(T / 2, T - 58); g.lineTo(60, T / 2); g.closePath(); g.fill(); g.fillStyle = '#d9b46a'; g.beginPath(); g.arc(T / 2, T / 2, 28, 0, 7); g.fill(); g.fillStyle = '#7a1c1c'; g.beginPath(); g.arc(T / 2, T / 2, 14, 0, 7); g.fill(); for (let k = 0; k < 40; k++) { g.fillStyle = `rgba(255,230,180,${r() * .18})`; g.fillRect(r() * T, r() * T, 12, 3); } fringe(); });
  tile(1, () => { g.fillStyle = '#c9b48a'; g.fillRect(0, 0, T, T); for (let y = 0; y < T; y += 32) for (let x = 0; x < T; x += 32) { g.fillStyle = (x + y) / 32 % 2 ? '#2b4a6e' : '#8c3d2b'; g.beginPath(); g.moveTo(x + 16, y + 2); g.lineTo(x + 30, y + 16); g.lineTo(x + 16, y + 30); g.lineTo(x + 2, y + 16); g.closePath(); g.fill(); } fringe(); });
  tile(2, () => { const cols = ['#b8452a', '#e8c070', '#2d5a52', '#e9e0cd', '#7b2e44', '#d98b2b']; let y = 0; while (y < T) { const h = 10 + r() * 30; g.fillStyle = cols[Math.floor(r() * cols.length)]; g.fillRect(0, y, T, h); y += h; } fringe(); });
  tile(3, () => { const cols = ['#d94a5c', '#f2a93b', '#3a6ea5', '#59a96a', '#8a4fa0', '#f3e9d2']; for (let x = 0; x < T; x += 28) { g.fillStyle = cols[Math.floor(x / 28) % cols.length]; g.fillRect(x, 0, 28, T); g.fillStyle = 'rgba(255,255,255,.18)'; g.fillRect(x + 6, 0, 3, T); } });
  tile(4, () => { for (let y = 0; y < T; y += 64) for (let x = 0; x < T; x += 64) { g.fillStyle = hsl(Math.floor(r() * 360), 55, 45); g.fillRect(x, y, 64, 64); g.strokeStyle = 'rgba(255,240,200,.75)'; g.lineWidth = 2; g.strokeRect(x + 5, y + 5, 54, 54); g.beginPath(); g.arc(x + 32, y + 32, 16, 0, 7); g.stroke(); for (let k = 0; k < 8; k++) { g.beginPath(); g.moveTo(x + 32, y + 32); g.lineTo(x + 32 + Math.cos(k * .785) * 24, y + 32 + Math.sin(k * .785) * 24); g.stroke(); } } });
  tile(5, () => { g.fillStyle = '#f0ece0'; g.fillRect(0, 0, T, T); g.fillStyle = '#244b8c'; for (let y = 0; y < T; y += 64) for (let x = 0; x < T; x += 64) { g.beginPath(); g.moveTo(x + 32, y + 6); g.lineTo(x + 58, y + 32); g.lineTo(x + 32, y + 58); g.lineTo(x + 6, y + 32); g.closePath(); g.fill(); g.fillStyle = '#f0ece0'; g.beginPath(); g.arc(x + 32, y + 32, 10, 0, 7); g.fill(); g.fillStyle = '#244b8c'; } });
  tile(6, () => { g.fillStyle = '#b5703a'; g.fillRect(0, 0, T, T); const gr = g.createLinearGradient(0, 0, T, T); gr.addColorStop(0, 'rgba(255,230,190,.25)'); gr.addColorStop(1, 'rgba(60,25,5,.3)'); g.fillStyle = gr; g.fillRect(0, 0, T, T); g.strokeStyle = 'rgba(60,30,10,.7)'; g.setLineDash([6, 5]); g.lineWidth = 2; g.strokeRect(12, 12, T - 24, T - 24); g.setLineDash([]); speckle(g, T, T, 5, 10, 8000); });
  tile(7, () => { g.fillStyle = '#3a2a22'; g.fillRect(0, 0, T, T); const gr = g.createLinearGradient(0, 0, T, T); gr.addColorStop(0, 'rgba(255,220,180,.18)'); gr.addColorStop(1, 'rgba(0,0,0,.3)'); g.fillStyle = gr; g.fillRect(0, 0, T, T); g.strokeStyle = 'rgba(200,170,120,.5)'; g.setLineDash([6, 5]); g.lineWidth = 2; g.strokeRect(12, 12, T - 24, T - 24); g.setLineDash([]); });
  tile(8, () => { g.fillStyle = '#2f5a3a'; g.fillRect(0, 0, T, T); for (let y = 0; y < T; y += 24) { g.strokeStyle = '#e0c070'; g.lineWidth = 2; g.beginPath(); for (let x = 0; x <= T; x += 8) g.lineTo(x, y + Math.sin(x * .1 + y) * 5); g.stroke(); } for (let k = 0; k < 20; k++) { g.fillStyle = ['#d94a5c', '#e8c070', '#e9e0cd'][k % 3]; g.beginPath(); g.arc(r() * T, r() * T, 6 + r() * 8, 0, 7); g.fill(); } fringe(); });
  tile(9, () => { for (let y = 0; y < T; y += 32) for (let x = 0; x < T; x += 32) { g.fillStyle = ['#e8421e', '#f2b020', '#2a9d8f', '#e04a8a', '#3a6ee8', '#f4e8c0'][Math.floor(r() * 6)]; g.fillRect(x + 1, y + 1, 30, 30); } g.strokeStyle = '#1a1512'; g.lineWidth = 3; for (let x = 0; x <= T; x += 32) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, T); g.stroke(); g.beginPath(); g.moveTo(0, x); g.lineTo(T, x); g.stroke(); } });
  tile(10, () => { g.fillStyle = '#17181b'; g.fillRect(0, 0, T, T); g.strokeStyle = '#ece6d6'; g.lineWidth = 2; for (let R = 14; R < 126; R += 14) { g.beginPath(); g.arc(T / 2, T / 2, R, 0, 7); g.stroke(); for (let k = 0; k < 16; k++) { const a = k * Math.PI / 8; g.beginPath(); g.arc(T / 2 + Math.cos(a) * R, T / 2 + Math.sin(a) * R, 4, 0, 7); g.stroke(); } } fringe('#ece6d6'); });
  tile(11, () => { for (let x = 0; x < T; x += 40) { g.fillStyle = x / 40 % 2 ? '#e7792b' : '#8a3a6e'; g.fillRect(x, 0, 40, T); g.fillStyle = 'rgba(255,255,255,.35)'; g.fillRect(x + 8, 0, 5, T); } fringe(); });
  tile(12, () => { const gr = g.createLinearGradient(0, 0, T, T); gr.addColorStop(0, '#e6c36a'); gr.addColorStop(.5, '#a8812e'); gr.addColorStop(1, '#d9b552'); g.fillStyle = gr; g.fillRect(0, 0, T, T); for (let k = 0; k < 400; k++) { g.fillStyle = `rgba(255,240,180,${r() * .3})`; g.beginPath(); g.arc(r() * T, r() * T, 2 + r() * 4, 0, 7); g.fill(); } });
  tile(13, () => { g.fillStyle = '#c8344a'; g.fillRect(0, 0, T, T); for (let k = 0; k < 60; k++) { g.fillStyle = ['#f2c0c8', '#f6d86a', '#2d6a4f', '#fff'][k % 4]; g.beginPath(); g.arc(r() * T, r() * T, 5 + r() * 8, 0, 7); g.fill(); } });
  tile(14, () => { g.fillStyle = '#1e3a78'; g.fillRect(0, 0, T, T); for (let y = 8; y < T; y += 24) { g.strokeStyle = '#e8e0cc'; g.lineWidth = 3; g.beginPath(); for (let x = 0; x < T; x += 4) g.lineTo(x, y + ((Math.floor(x / 16) % 2) ? 8 : 0)); g.stroke(); } fringe(); });
  tile(15, () => { g.fillStyle = '#ece3cd'; g.fillRect(0, 0, T, T); speckle(g, T, T, 12, 6, 6000); });
  return c;
}

// ---------------------------------------------------------------- sign atlas (names from OSM, street plaques)
const SIGNS = new Map();      // key -> {w, h (px), draw, rect}
let signCanvas = null;
function defSign(key, w, h, draw) { if (!SIGNS.has(key)) SIGNS.set(key, { w, h, draw, rect: null }); }
const FONTS = ['"Palatino Linotype",Georgia,serif', 'Georgia,serif', '"Trebuchet MS",Verdana,sans-serif', '"Times New Roman",serif'];
function fitText(g, text, W, H, font, weight = 'bold', pad = 18) {
  let size = H * .62; for (let i = 0; i < 12; i++) { g.font = `${weight} ${size}px ${font}`; if (g.measureText(text).width <= W - pad * 2) break; size *= .88; } return size;
}
function signStyle(name, style) {
  const T = name.toUpperCase();
  return (g, w, h) => {
    const rr = rnd([...name].reduce((a, ch) => a * 31 + ch.charCodeAt(0), 7));
    if (style === 0) { // carved dark board, gold letters
      g.fillStyle = '#3a2416'; g.fillRect(0, 0, w, h); for (let k = 0; k < 60; k++) { g.strokeStyle = `rgba(0,0,0,${.1 + rr() * .2})`; g.beginPath(); g.moveTo(0, rr() * h); g.lineTo(w, rr() * h); g.stroke(); }
      g.strokeStyle = '#c9a24c'; g.lineWidth = 3; g.strokeRect(6, 6, w - 12, h - 12); g.fillStyle = '#e1b85a'; g.textAlign = 'center'; g.textBaseline = 'middle';
      fitText(g, T, w, h, FONTS[0]); g.fillText(T, w / 2, h / 2 + 2);
    } else if (style === 1) { // cream board, red letters
      g.fillStyle = '#efe6d0'; g.fillRect(0, 0, w, h); g.strokeStyle = '#8f2b22'; g.lineWidth = 4; g.strokeRect(5, 5, w - 10, h - 10); g.fillStyle = '#8f2b22'; g.textAlign = 'center'; g.textBaseline = 'middle';
      fitText(g, T, w, h, FONTS[1]); g.fillText(T, w / 2, h / 2 + 2);
    } else if (style === 2) { // teal board, white letters, arabesque dots
      g.fillStyle = '#1f5a5a'; g.fillRect(0, 0, w, h); g.fillStyle = '#d9b85a'; for (let x = 10; x < w; x += 18) { g.fillRect(x, 5, 6, 3); g.fillRect(x, h - 8, 6, 3); } g.fillStyle = '#f4ecd8'; g.textAlign = 'center'; g.textBaseline = 'middle';
      fitText(g, T, w, h, FONTS[2]); g.fillText(T, w / 2, h / 2 + 2);
    } else if (style === 3) { // dark green + gold script
      g.fillStyle = '#26382c'; g.fillRect(0, 0, w, h); g.strokeStyle = '#d6b45a'; g.lineWidth = 2; g.strokeRect(8, 8, w - 16, h - 16); g.fillStyle = '#e8c870'; g.textAlign = 'center'; g.textBaseline = 'middle';
      fitText(g, name, w, h, '"Brush Script MT","Segoe Script",cursive', 'italic'); g.fillText(name, w / 2, h / 2);
    } else { // maroon + cream
      g.fillStyle = '#6a2230'; g.fillRect(0, 0, w, h); g.fillStyle = '#f3e6c4'; g.textAlign = 'center'; g.textBaseline = 'middle';
      fitText(g, T, w, h, FONTS[3]); g.fillText(T, w / 2, h / 2 + 2); g.strokeStyle = '#d9b46a'; g.lineWidth = 2; g.strokeRect(5, 5, w - 10, h - 10);
    }
  };
}
function plaque(text) {
  return (g, w, h) => { // azulejo street plaque: white tile, blue border and lettering
    g.fillStyle = '#f2efe6'; g.fillRect(0, 0, w, h); g.strokeStyle = '#1d4a8c'; g.lineWidth = 6; g.strokeRect(5, 5, w - 10, h - 10); g.lineWidth = 2; g.strokeRect(14, 14, w - 28, h - 28);
    g.fillStyle = '#1d4a8c'; g.textAlign = 'center'; g.textBaseline = 'middle'; const lines = text.split('\n'); const fs = Math.min(h * .25, (w - 40) / Math.max(...lines.map(l => l.length)) * 1.7);
    g.font = `bold ${fs}px ${FONTS[0]}`; lines.forEach((l, i) => g.fillText(l, w / 2, h / 2 + (i - (lines.length - 1) / 2) * fs * 1.15));
  };
}
function chalk(lines) {
  return (g, w, h) => {
    g.fillStyle = '#25282a'; g.fillRect(0, 0, w, h); g.strokeStyle = '#6b5a45'; g.lineWidth = 8; g.strokeRect(4, 4, w - 8, h - 8);
    g.fillStyle = 'rgba(255,255,255,.05)'; for (let k = 0; k < 30; k++) g.fillRect(Math.random() * w, Math.random() * h, 30, 4);
    g.fillStyle = '#f3f0e6'; g.textAlign = 'center'; g.textBaseline = 'middle'; const fs = h / (lines.length + 1.4);
    lines.forEach((l, i) => { g.font = `${i ? '' : 'bold '}${fs * (i ? .8 : 1.05)}px "Comic Sans MS","Segoe Print",cursive`; g.fillText(l, w / 2, h * .16 + fs * (i + .6) * 1.15); });
  };
}
function packSigns() {
  const W = 2048, H = 2048, [c, g] = cv(W, H); g.fillStyle = '#7b6a55'; g.fillRect(0, 0, W, H);
  let x = 0, y = 0, rowH = 0;
  for (const s of SIGNS.values()) {
    if (x + s.w > W) { x = 0; y += rowH + 2; rowH = 0; }
    g.save(); g.translate(x, y); g.beginPath(); g.rect(0, 0, s.w, s.h); g.clip(); s.draw(g, s.w, s.h); g.restore();
    s.rect = [x / W, 1 - (y + s.h) / H, (x + s.w) / W, 1 - y / H]; x += s.w + 2; rowH = Math.max(rowH, s.h);
  }
  // a plain region for board backs: top-left pixel block is already covered; reserve the last 8x8 px
  g.fillStyle = '#5a4630'; g.fillRect(W - 16, H - 16, 16, 16);
  SIGNS.plain = [(W - 12) / W, 1 - (H - 4) / H];
  signCanvas = c;
}
const signRect = key => (SIGNS.get(key) || SIGNS.get('bazar0')).rect;

// ---------------------------------------------------------------- materials
export async function materials(M) {
  const tm = performance.now();
  LAY = await (await fetch('textures/calderia/layout.json')).json(); const tf = performance.now() - tm;
  const std = (name, o) => { const m = new THREE.MeshStandardMaterial({ roughness: .9, metalness: 0, vertexColors: true, ...o }); m.name = name; m.userData = { scale: 1 }; M[name] = m; return m; };
  const mapped = (name, canvas, { bump = 1.0, rough = .92, bumpCanvas = canvas, ...o } = {}) => { const m = std(name, { map: tex(canvas), roughness: rough, ...o }); if (bump) { m.bumpMap = tex(bumpCanvas, { srgb: false }); m.bumpScale = bump; } return m; };
  mapped('alcRender', texRender(), { bump: .9 });
  mapped('alcStone', texStone(), { bump: 1.4, rough: .88 });
  mapped('alcBrick', texBrick(), { bump: 1.5, rough: .9 });
  mapped('alcTile', texTile(), { bump: 1.6, rough: .85, side: THREE.DoubleSide });
  mapped('alcWood', texWood(), { bump: .6, rough: .8 });
  mapped('alcPebble', texPebble(), { bump: 1.8, rough: .82, vertexColors: true });
  mapped('alcPebbleFlat', texPebble(62, false), { bump: 1.8, rough: .82 });
  mapped('alcSett', texSett(), { bump: 1.4, rough: .85 });
  mapped('alcAsphalt', texAsphalt(), { bump: .5, rough: .95 });
  mapped('alcGoods', texGoods(), { bump: 0, rough: .85, side: THREE.DoubleSide });
  std('alcDetail', { roughness: .62, metalness: .1 });
  std('alcDetailDS', { roughness: .7, metalness: .05, side: THREE.DoubleSide });
  const gl = new THREE.MeshBasicMaterial({ vertexColors: true }); gl.name = 'alcGlow'; gl.userData = { scale: 1 }; M.alcGlow = gl;
  const gt = new THREE.MeshBasicMaterial({ vertexColors: true, map: M.alcGoods.map }); gt.name = 'alcGlowTex'; gt.userData = { scale: 1 }; M.alcGlowTex = gt;
  // narrow lanes: warm bounce light off the whitewash lifts the shade (the shared interior hook scales indirect light)
  for (const [n, k] of [['alcRender', 1.6], ['alcStone', 1.5], ['alcBrick', 1.5], ['alcWood', 1.4], ['alcDetail', 1.5], ['alcDetailDS', 1.5], ['alcGoods', 1.5], ['alcPebble', 1.4], ['alcPebbleFlat', 1.4], ['alcSett', 1.4], ['alcAsphalt', 1.3], ['alcTile', 1.2]]) M[n].userData.interiorAmbient = k;
  // signs
  const names = new Set();
  for (const p of LAY.pois) { const t = p.t; if (!t.name) continue; if (t.shop || /bar|cafe|restaurant|pub|fast_food|ice_cream|pharmacy/.test(t.amenity || '')) names.add(t.name); }
  let k = 0; for (const n of names) { defSign('n:' + n, 512, 112, signStyle(n, k++ % 5)); }
  for (const t of ['TETERÍA', 'BAZAR', 'ARTESANÍA', 'BAR', 'TAPAS', 'CAFETERÍA', 'ALQUILA', 'HOSTAL', 'SOUVENIRS', 'CERÁMICAS', 'ESPECIAS', 'PANADERÍA', 'FRUTAS', 'CARNICERÍA', 'TÉ · CAFÉ', 'LÁMPARAS', 'CUERO', 'JOYERÍA', 'ALFOMBRAS', 'HAMMAM']) defSign('t:' + t, 512, 112, signStyle(t, [0, 2, 1, 4, 3][t.length % 5]));
  defSign('bazar0', 512, 112, signStyle('BAZAR', 0));
  for (const w of LAY.ways) if (w.name) defSign('p:' + w.name, 256, 128, plaque(w.name.replace(/^(Calle|Cuesta|Callejón|Placeta|Plaza|Calleja|Callejuela) /, m => m.trim() + '\n').toUpperCase()));
  defSign('chalk0', 256, 320, chalk(['MENÚ DEL DÍA', 'Té moruno  2,5€', 'Tajine  9€', 'Cuscús  8€', 'Cerveza  2€']));
  defSign('chalk1', 256, 320, chalk(['TAPAS', 'Tinto de verano', 'Croquetas  4€', 'Jamón  9€', 'Tortilla  3€']));
  defSign('chalk2', 256, 320, chalk(['TETERÍA', 'Té a la menta', 'Pasteles árabes', 'Shisha', 'Zumos']));
  defSign('menu', 192, 256, (g, w, h) => { g.fillStyle = '#efe8d6'; g.fillRect(0, 0, w, h); g.fillStyle = '#7a2a22'; g.fillRect(8, 8, w - 16, 26); g.fillStyle = '#333'; for (let y = 50; y < h - 12; y += 16) g.fillRect(14, y, w * (.35 + Math.random() * .45), 5); });
  defSign('flag0', 128, 256, (g, w, h) => { g.fillStyle = '#f0e4c8'; g.fillRect(0, 0, w, h); g.strokeStyle = '#8f2b22'; g.lineWidth = 5; g.strokeRect(4, 4, w - 8, h - 8); g.fillStyle = '#8f2b22'; g.font = 'bold 56px Georgia,serif'; g.textAlign = 'center'; g.fillText('☕', w / 2, 90); g.font = 'bold 22px Georgia,serif'; g.fillText('TETERÍA', w / 2, 160); g.fillText('TÉ · CAFÉ', w / 2, 192); });
  defSign('flag1', 128, 256, (g, w, h) => { g.fillStyle = '#1f5a5a'; g.fillRect(0, 0, w, h); g.strokeStyle = '#e8c870'; g.lineWidth = 4; g.strokeRect(6, 6, w - 12, h - 12); g.fillStyle = '#e8c870'; g.font = 'bold 22px Georgia,serif'; g.textAlign = 'center'; g.fillText('RESTAURANTE', w / 2, 92); g.font = 'bold 54px Georgia,serif'; g.fillText('✦', w / 2, 160); g.font = 'bold 20px Georgia,serif'; g.fillText('HALAL', w / 2, 210); });
  defSign('flag2', 128, 256, (g, w, h) => { g.fillStyle = '#b3402c'; g.fillRect(0, 0, w, h); g.fillStyle = '#f6e9c8'; g.font = 'bold 26px Georgia,serif'; g.textAlign = 'center'; g.fillText('TAPAS', w / 2, 90); g.font = 'bold 56px Georgia,serif'; g.fillText('🍷', w / 2, 170); g.font = 'bold 20px Georgia,serif'; g.fillText('BAR', w / 2, 220); });
  packSigns();
  const sm = new THREE.MeshStandardMaterial({ map: tex(signCanvas), emissiveMap: null, roughness: .75, side: THREE.DoubleSide, vertexColors: true }); sm.name = 'alcSign'; sm.userData = { scale: 1 };
  sm.map.generateMipmaps = true; sm.emissive = new THREE.Color(0x553322); sm.emissiveMap = sm.map; sm.emissiveIntensity = .55; sm.userData.interiorAmbient = 1.4; M.alcSign = sm;
  console.log(`calderia materials: layout ${tf | 0} ms, textures ${(performance.now() - tm - tf) | 0} ms`);
}

// ---------------------------------------------------------------- mesh accumulation
let LAY = null;
class Geo {
  constructor() { this.p = []; this.n = []; this.u = []; this.c = []; this.i = []; this.count = 0; }
  v(P, N, U, C) { this.p.push(P[0], P[1], P[2]); this.n.push(N[0], N[1], N[2]); this.u.push(U[0], U[1]); this.c.push(C[0], C[1], C[2]); return this.count++; }
  get tris() { return this.i.length / 3; }
  geometry() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.u, 2)); g.setAttribute('color', new THREE.Float32BufferAttribute(this.c, 3));
    g.setIndex(this.count > 65535 ? new THREE.Uint32BufferAttribute(this.i, 1) : new THREE.Uint16BufferAttribute(this.i, 1)); return g;
  }
}
// quad (P0..P3 counter-clockwise seen from the front). hint: a world vector the normal should agree with.
const _a = [0, 0, 0], _b = [0, 0, 0];
function quadTo(geo, P, U, C, hint) {
  const ux = P[2][0] - P[0][0], uy = P[2][1] - P[0][1], uz = P[2][2] - P[0][2], vx = P[3][0] - P[1][0], vy = P[3][1] - P[1][1], vz = P[3][2] - P[1][2];
  let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
  const l = hyp(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
  let order = [0, 1, 2, 3];
  if (hint && nx * hint[0] + ny * hint[1] + nz * hint[2] < 0) { order = [0, 3, 2, 1]; nx = -nx; ny = -ny; nz = -nz; }
  const N = [nx, ny, nz], multi = C.length === 4 && Array.isArray(C[0]);
  const id = order.map(k => geo.v(P[k], N, U[k], multi ? C[k] : C));
  geo.i.push(id[0], id[1], id[2], id[0], id[2], id[3]);
}
function triTo(geo, P, U, C, hint) {
  const ux = P[1][0] - P[0][0], uy = P[1][1] - P[0][1], uz = P[1][2] - P[0][2], vx = P[2][0] - P[0][0], vy = P[2][1] - P[0][1], vz = P[2][2] - P[0][2];
  let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const l = hyp(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
  let order = [0, 1, 2];
  if (hint && nx * hint[0] + ny * hint[1] + nz * hint[2] < 0) { order = [0, 2, 1]; nx = -nx; ny = -ny; nz = -nz; }
  const N = [nx, ny, nz], multi = C.length === 3 && Array.isArray(C[0]);
  const id = order.map(k => geo.v(P[k], N, U[k], multi ? C[k] : C));
  geo.i.push(id[0], id[1], id[2]);
}
const GEOS = new Map();
// geometry is kept in four tiles (split at x = -640, z = 0, the Builder's 160 m cells) so that parts can be culled
function G(mat, x, z) { const key = mat + '|' + (x < -640 ? 0 : 1) + '|' + (z < 0 ? 0 : 1); let e = GEOS.get(key); if (!e) { e = { mat, geo: new Geo() }; GEOS.set(key, e); } return e.geo; }
const Q = (mat, P, U, C, hint) => quadTo(G(mat, P[0][0], P[0][2]), P, U, C, hint);
const T3 = (mat, P, U, C, hint) => triTo(G(mat, P[0][0], P[0][2]), P, U, C, hint);

// ---------------------------------------------------------------- rasters (0.25 m): buildings and paving
const R = .25, RX0 = -737, RZ0 = -127, RNX = Math.ceil((-543 - RX0) / R), RNZ = Math.ceil((57 - RZ0) / R);
let OCC = null, PH = null, COV = null, TOPR = null;
const ri = (x, z) => { const i = Math.floor((x - RX0) / R), j = Math.floor((z - RZ0) / R); return i < 0 || j < 0 || i >= RNX || j >= RNZ ? -1 : j * RNX + i; };
const occupied = (x, z) => { const k = ri(x, z); return k >= 0 && OCC[k] === 1; };
function fillPoly(ring, arr, val) {
  let zmin = 1e9, zmax = -1e9; for (const p of ring) { zmin = Math.min(zmin, p[1]); zmax = Math.max(zmax, p[1]); }
  const j0 = Math.max(0, Math.floor((zmin - RZ0) / R)), j1 = Math.min(RNZ - 1, Math.floor((zmax - RZ0) / R));
  for (let j = j0; j <= j1; j++) {
    const z = RZ0 + (j + .5) * R, xs = [];
    for (let a = 0, b = ring.length - 1; a < ring.length; b = a++) { const A = ring[a], B = ring[b]; if ((A[1] > z) !== (B[1] > z)) xs.push((B[0] - A[0]) * (z - A[1]) / (B[1] - A[1]) + A[0]); }
    xs.sort((p, q) => p - q);
    for (let k = 0; k + 1 < xs.length; k += 2) { const i0 = Math.max(0, Math.ceil((xs[k] - RX0) / R - .5)), i1 = Math.min(RNX - 1, Math.floor((xs[k + 1] - RX0) / R - .5)); for (let i = i0; i <= i1; i++) arr[j * RNX + i] = val; }
  }
}
function pavH(x, z) { const k = ri(x, z); const v = k >= 0 ? PH[k] : NaN; return Number.isNaN(v) ? terrainHeight(x, z) : v; }

// ---------------------------------------------------------------- lanes: ribbons with real steps
const EXCLUDE = new Set(['Plaza Nueva', 'Cuesta de Gomérez', 'Cuesta del Perro Alta', 'Cuesta de las Arremangadas', 'Calle Gran Vía de Colón', 'Calle Cementerio San José', 'Placeta de San José', 'Calle Hermosa', 'Calle Buen Rostro', 'Cuesta Beteta', 'Calle Abenamar', 'Calle Álamo del Marqués', 'Pasaje Diego de Siloé', 'Calle Lavadero Manchega', 'Calle Aguirre', 'Calle Rueda Bolas', 'Calle Valentín Barrecheguren', 'Placeta Sillería', 'Calle Joaquín Costa']);
const PRIORITY = ['Calle Calderería Nueva', 'Calle Calderería Vieja', 'Cuesta de Marañas', 'Callejón del Gato', 'Calle Hospital Corpus Christi', 'Calle Hospital Peregrinos', 'Calle Imprenta', 'Callejuela del Señor', 'Calle Correo Viejo', 'Cuesta de San Gregorio', 'Calle San Juan de los Reyes', 'Calle Pan', 'Calle Bodegoncillos', 'Calle Elvira', 'Calle Cetti Meriem', 'Calle Cárcel Baja', 'Calle Almireceros', 'Calle Cárcel Alta'];
function chaikin(pts, n = 2) { for (let it = 0; it < n; it++) { const o = [pts[0]]; for (let i = 0; i < pts.length - 1; i++) { const a = pts[i], b = pts[i + 1]; o.push([a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25], [a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75]); } o.push(pts[pts.length - 1]); pts = o; } return pts; }
function resample(pts, step) {
  const out = []; let carry = 0; out.push(pts[0].slice());
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i + 1], L = hyp(b[0] - a[0], b[1] - a[1]); let d = step - carry;
    while (d <= L) { out.push([a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L]); d += step; }
    carry = L - (d - step);
  }
  return out;
}
function surfaceClass(w) { const s = w.surface || ''; if (w.name === 'Calle Cárcel Baja' || s === 'asphalt') return 'alcAsphalt'; if (s === 'sett' || s === 'paving_stones') return 'alcSett'; return 'alcPebble'; }
const PAVE_STEP = .25, RISER = .17, STEP_RISE = .78, STEP_LIP = .13;
const LAMPS = []; // light pools registered by the lantern code
function buildLanes(b, stats) {
  const inReg = p => p[0] > -733 && p[0] < -547 && p[1] > -123 && p[1] < 53;
  const ways = LAY.ways.filter(w => w.name && !EXCLUDE.has(w.name) && ['steps', 'pedestrian', 'residential', 'secondary'].includes(w.hw) && w.pts.some(inReg));
  ways.sort((a, b) => { const pa = PRIORITY.indexOf(a.name), pb = PRIORITY.indexOf(b.name); return (pa < 0 ? 99 : pa) - (pb < 0 ? 99 : pb); });
  const lanes = [];
  for (const w of ways) {
    let pts = w.pts; if (pts.length < 2) continue;
    // closed pedestrian outlines (placetas) are areas, not lanes
    if (hyp(pts[0][0] - pts.at(-1)[0], pts[0][1] - pts.at(-1)[1]) < .5 && pts.length > 4) continue;
    pts = resample(chaikin(pts, 2), PAVE_STEP);
    const cls = surfaceClass(w), wide = cls !== 'alcPebble' || w.hw === 'secondary' ? 7 : 4.6;
    const n = pts.length; if (n < 3) continue;
    const S = []; // samples
    for (let i = 0; i < n; i++) {
      const a = pts[Math.max(0, i - 1)], c = pts[Math.min(n - 1, i + 1)]; let tx = c[0] - a[0], tz = c[1] - a[1]; const l = hyp(tx, tz) || 1; tx /= l; tz /= l;
      const nx = -tz, nz = tx, P = pts[i];
      if (!(P[0] > -745 && P[0] < -535 && P[1] > -135 && P[1] < 65)) { S.push(null); continue; }
      // the cadastre footprints and the OSM line do not agree to the metre: find the open gap nearest the line
      let ts = null, bd = 1e9; for (let t = -3.5; t <= 3.5; t += .1) if (!occupied(P[0] + nx * t, P[1] + nz * t) && Math.abs(t) < bd) { bd = Math.abs(t); ts = t; }
      if (ts === null) { S.push(null); continue; }
      let tl = ts, tr = ts; for (; tl > -wide - 1; tl -= .1) if (occupied(P[0] + nx * (tl - .1), P[1] + nz * (tl - .1))) break; for (; tr < wide + 1; tr += .1) if (occupied(P[0] + nx * (tr + .1), P[1] + nz * (tr + .1))) break;
      const hitL = occupied(P[0] + nx * (tl - .1), P[1] + nz * (tl - .1)), hitR = occupied(P[0] + nx * (tr + .1), P[1] + nz * (tr + .1)); const wl0 = tl - .05, wr0 = tr + .05;
      tl = Math.max(tl, ts - wide); tr = Math.min(tr, ts + wide); if (hitL && tl > ts - wide) tl -= .3; if (hitR && tr < ts + wide) tr += .3;
      if (tr - tl > 5.4) { S.push(null); continue; } // plazas and wide streets are laid by the ground grid
      S.push({ P, tx, tz, nx, nz, dl: -tl, dr: tr, tl, tr, wl: wl0, wr: wr0, hitL, hitR, s: i * PAVE_STEP });
    }
    lanes.push({ w, S, cls, id: lanes.length });
  }
  // widths: light median filter against jitter of facade recesses
  for (const L of lanes) {
    const S = L.S;
    L.tcs = S.map((s, i) => { if (!s) return 0; let a = 0, n = 0; for (let k = -8; k <= 8; k++) { const q = S[i + k]; if (q) { a += (q.tl + q.tr) / 2; n++; } } return a / n; });
    // height: highest ground across the lane, smoothed along it, then stepped
    const H = S.map((s, i) => { if (!s) return NaN; const tc = L.tcs[i]; let h = -1e9; for (let t = tc - .8; t <= tc + .81; t += .4) h = Math.max(h, terrainHeight(s.P[0] + s.nx * t, s.P[1] + s.nz * t)); return h; });
    const sm = H.map((h, i) => { if (Number.isNaN(h)) return NaN; let a = 0, wsum = 0; for (let k = -12; k <= 12; k++) { const v = H[i + k]; if (v === undefined || Number.isNaN(v)) continue; const w = Math.exp(-(k * k) / 72); a += v * w; wsum += w; } return a / wsum + .05; });
    L.h = sm; L.hq = []; L.sr = []; L.steep = [];
    for (let i = 0; i < S.length; i++) {
      if (!S[i]) { L.steep.push(false); L.hq.push(NaN); L.sr.push(0); continue; }
      let a = sm[Math.max(0, i - 6)], c = sm[Math.min(S.length - 1, i + 6)]; if (Number.isNaN(a)) a = sm[i]; if (Number.isNaN(c)) c = sm[i]; const slope = (c - a) / (12 * PAVE_STEP), st = Math.abs(slope) > .075;
      L.steep.push(st);
      // steep lanes: sloping cobbled treads with a low granite lip every metre or so of climb
      if (st) { const m = Math.floor(sm[i] / STEP_RISE), f = sm[i] / STEP_RISE - m; L.hq.push(m * STEP_RISE + f * (STEP_RISE - STEP_LIP)); L.sr.push(slope * (STEP_RISE - STEP_LIP) / STEP_RISE); }
      else { L.hq.push(sm[i]); L.sr.push(slope); }
    }
  }
  const col = (k, r = 1) => { const f = .94 + .1 * r; return [f, f * .98, f * .95]; };
  const stoneCol = [.78, .76, .72];
  for (const L of lanes) {
    const S = L.S, mat = L.cls, rr = rnd(S.length * 7 + (L.w.name || '').length), v0 = rr() * 3, half = PAVE_STEP / 2;
    const edges = i => { const s = S[i]; return [[s.P[0] + s.nx * s.tl, s.P[1] + s.nz * s.tl], [s.P[0] + s.nx * s.tr, s.P[1] + s.nz * s.tr]]; };
    const hA = i => L.hq[i] - L.sr[i] * half, hB = i => L.hq[i] + L.sr[i] * half;
    const emitted = [], mid = (A, B) => [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2];
    for (let i = 0; i < S.length; i++) {
      const s = S[i]; if (!s) { emitted.push(false); continue; }
      const k = ri(s.P[0] + s.nx * L.tcs[i], s.P[1] + s.nz * L.tcs[i]); if (k < 0 || (COV[k] >= 0 && COV[k] !== L.id)) { emitted.push(false); continue; }
      const p = S[i - 1], q = S[i + 1];
      if (!p || !q) { emitted.push(false); continue; }
      const [l0, r0] = edges(i - 1), [l1, r1] = edges(i), [l2, r2] = edges(i + 1);
      const La = mid(l0, l1), Ra = mid(r0, r1), Lb = mid(l1, l2), Rb = mid(r1, r2), ha = hA(i), hb = hB(i);
      const tcs = L.tcs[i], uL = (3 + s.tl - tcs) / 6, uR = (3 + s.tr - tcs) / 6, vA = v0 + (s.s - half) / 3, vB = vA + PAVE_STEP / 3;
      const tint = col(0, rr()), sc = mat === 'alcPebble' ? 1 : 1 / 2.4;
      const U = mat === 'alcPebble' ? [[uL, vA], [uR, vA], [uR, vB], [uL, vB]] : [[s.tl * sc, (s.s - half) * sc], [s.tr * sc, (s.s - half) * sc], [s.tr * sc, (s.s + half) * sc], [s.tl * sc, (s.s + half) * sc]];
      Q(mat, [[La[0], ha, La[1]], [Ra[0], ha, Ra[1]], [Rb[0], hb, Rb[1]], [Lb[0], hb, Lb[1]]], U, tint, [0, 1, 0]);
      // skirts so that nothing shows between the lane and the walls or the ground beyond
      const dk = 1.2;
      Q('alcStone', [[La[0], ha, La[1]], [Lb[0], hb, Lb[1]], [Lb[0], hb - dk, Lb[1]], [La[0], ha - dk, La[1]]], [[0, 0], [.25, 0], [.25, 1], [0, 1]], stoneCol, [-s.nx, 0, -s.nz]);
      Q('alcStone', [[Ra[0], ha, Ra[1]], [Rb[0], hb, Rb[1]], [Rb[0], hb - dk, Rb[1]], [Ra[0], ha - dk, Ra[1]]], [[0, 0], [.25, 0], [.25, 1], [0, 1]], stoneCol, [s.nx, 0, s.nz]);
      // ground registry: every 0.12 m across
      for (let t = s.tl; t <= s.tr; t += .15) for (let a = -.1; a <= .1; a += .1) { const x = s.P[0] + s.nx * t + s.tx * a, z = s.P[1] + s.nz * t + s.tz * a, kk = ri(x, z); if (kk >= 0 && (COV[kk] < 0 || COV[kk] === L.id)) { PH[kk] = (ha + hb) / 2; COV[kk] = L.id; } }
      emitted.push(true); stats.lane++;
      // riser between this cell and the next one (a low granite step)
      const j = i + 1, n2 = S[j];
      if (n2) {
        const h1 = hb, h2 = hA(j), d = h2 - h1;
        if (Math.abs(d) > .03) {
          const lo = Math.min(h1, h2), hi = Math.max(h1, h2), up = d > 0 ? 1 : -1, wdt = s.tr - s.tl;
          Q('alcStone', [[Lb[0], lo, Lb[1]], [Rb[0], lo, Rb[1]], [Rb[0], hi, Rb[1]], [Lb[0], hi, Lb[1]]], [[0, 0], [wdt / 2.4, 0], [wdt / 2.4, (hi - lo) / 2.4], [0, (hi - lo) / 2.4]], [.74, .72, .68], [-s.tx * up, 0, -s.tz * up]);
          // granite edging flush with the upper tread
          const w2 = .14, ox = s.tx * w2 * up, oz = s.tz * w2 * up;
          Q('alcStone', [[Lb[0], hi + .008, Lb[1]], [Rb[0], hi + .008, Rb[1]], [Rb[0] + ox, hi + .008 + (up > 0 ? L.sr[j] : L.sr[i]) * w2 * up, Rb[1] + oz], [Lb[0] + ox, hi + .008 + (up > 0 ? L.sr[j] : L.sr[i]) * w2 * up, Lb[1] + oz]], [[0, 0], [wdt / 2.4, 0], [wdt / 2.4, .2], [0, .2]], [.9, .88, .84], [0, 1, 0]);
          stats.risers++;
        }
      }
    }
    // navigation: runs of cells as ramps
    let run = null; const flush = () => { if (!run) return; const { i0, i1 } = run; const a = S[i0]; const len = (i1 - i0 + 1) * PAVE_STEP; let cx = 0, cz = 0, wd = 0, n = 0; for (let i = i0; i <= i1; i++) { const s = S[i]; cx += s.P[0] + s.nx * (s.tl + s.tr) / 2; cz += s.P[1] + s.nz * (s.tl + s.tr) / 2; wd = Math.max(wd, s.tr - s.tl); n++; } cx /= n; cz /= n; b.nav.ramp(cx, cz, wd + .2, len + .02, hA(i0), hB(i1), Math.atan2(a.tx, a.tz)); stats.navLane++; run = null; };
    for (let i = 0; i < S.length; i++) {
      if (!emitted[i]) { flush(); continue; }
      const s = S[i];
      if (run) { const a0 = S[run.i0], tot = Math.abs(a0.tx * s.tz - a0.tz * s.tx), jump = Math.abs(hA(i) - hB(i - 1)) > .03; if (tot > .15 || run.n >= 24 || jump || !emitted[i - 1]) flush(); }
      if (!run) run = { i0: i, i1: i, n: 1 }; else { run.i1 = i; run.n++; }
    }
    flush();
  }
  return lanes;
}

// ---------------------------------------------------------------- the rest of the ground (placetas, junctions)
function nearestSurface(x, z) {
  let best = 1e9, cls = 'alcPebbleFlat';
  for (const w of LAY.ways) { if (!w.name || EXCLUDE.has(w.name) && w.name !== 'Plaza Nueva') continue; const p = w.pts; for (let i = 0; i < p.length - 1; i++) { const A = p[i], B = p[i + 1], dx = B[0] - A[0], dz = B[1] - A[1], t = clamp(((x - A[0]) * dx + (z - A[1]) * dz) / (dx * dx + dz * dz || 1), 0, 1), d = hyp(A[0] + dx * t - x, A[1] + dz * t - z); if (d < best) { best = d; cls = surfaceClass(w) === 'alcPebble' ? 'alcPebbleFlat' : surfaceClass(w); } } }
  return best < 12 ? cls : 'alcPebbleFlat';
}
let REACH = null;
function floodReach() {
  REACH = new Uint8Array(RNX * RNZ); const q = []; const push = k => { if (k >= 0 && !OCC[k] && !REACH[k]) { REACH[k] = 1; q.push(k); } };
  for (const w of LAY.ways) { const p = w.pts; for (let i = 0; i < p.length - 1; i++) { const L = hyp(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]); for (let t = 0; t <= L; t += 1) { const x = p[i][0] + (p[i + 1][0] - p[i][0]) * t / L, z = p[i][1] + (p[i + 1][1] - p[i][1]) * t / L; for (let r = 0; r <= 3.5; r += .25) { let ok = false; for (let a = 0; a < 8 && !ok; a++) { const k = ri(x + Math.cos(a * .785) * r, z + Math.sin(a * .785) * r); if (k >= 0 && !OCC[k]) { push(k); ok = true; } } if (ok) break; } } } }
  while (q.length) { const k = q.pop(), i = k % RNX, j = (k / RNX) | 0; if (i > 0) push(k - 1); if (i < RNX - 1) push(k + 1); if (j > 0) push(k - RNX); if (j < RNZ - 1) push(k + RNX); }
}
let NHH = null, NHD = null;
function nearestRibbon() {
  // multi-source BFS from the ribbon-covered cells: height of the nearest paved lane and the distance to it
  NHH = new Float32Array(RNX * RNZ).fill(NaN); NHD = new Float32Array(RNX * RNZ).fill(99); const q = [];
  for (let k = 0; k < PH.length; k++) if (COV[k] >= 0) { NHH[k] = PH[k]; NHD[k] = 0; q.push(k); }
  let head = 0;
  while (head < q.length) { const k = q[head++], d = NHD[k]; if (d > 3.5) continue; const i = k % RNX, j = (k / RNX) | 0; for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const ii = i + di, jj = j + dj; if (ii < 0 || jj < 0 || ii >= RNX || jj >= RNZ) continue; const kk = jj * RNX + ii; if (OCC[kk] || NHD[kk] <= d + R) continue; NHD[kk] = d + R; NHH[kk] = NHH[k]; q.push(kk); } }
}
function buildGround(b, stats) {
  floodReach(); nearestRibbon();
  const C = .5, gx0 = -731, gz0 = -121, nx = Math.round((-549 - gx0) / C), nz = Math.round((51 - gz0) / C);
  const H = (x, z) => { const t = terrainHeight(x, z) + .03, k = ri(x, z); if (k < 0 || Number.isNaN(NHH[k])) return t; const d = NHD[k], w = clamp(1 - (d - .5) / 2.5, 0, 1); return lerp(t, NHH[k], w * w * (3 - 2 * w)); };
  const cell = new Array(nx * nz).fill(null);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const x = gx0 + (i + .5) * C, z = gz0 + (j + .5) * C;
    const occ4 = occupied(x - .12, z - .12) && occupied(x + .12, z - .12) && occupied(x - .12, z + .12) && occupied(x + .12, z + .12);
    if (occ4) continue; const k = ri(x, z); if (k >= 0 && COV[k] >= 0) continue;
    if (!(REACH[ri(x - .12, z - .12)] || REACH[ri(x + .12, z - .12)] || REACH[ri(x - .12, z + .12)] || REACH[ri(x + .12, z + .12)])) continue;
    const sx = (H(x + C, z) - H(x - C, z)) / (2 * C), sz = (H(x, z + C) - H(x, z - C)) / (2 * C), sl = hyp(sx, sz);
    if (sl > 9) { const q = Math.round(H(x, z) / RISER) * RISER; cell[j * nx + i] = { q, y: [q, q, q, q], plateau: true }; }
    else { const part = [[-.12, -.12], [.12, -.12], [-.12, .12], [.12, .12]].some(([a, bb]) => { const kk = ri(x + a, z + bb); return kk >= 0 && COV[kk] >= 0; }), off = part ? -.035 : 0; cell[j * nx + i] = { y: [H(x - C / 2, z - C / 2) + off, H(x + C / 2, z - C / 2) + off, H(x + C / 2, z + C / 2) + off, H(x - C / 2, z + C / 2) + off], plateau: false }; }
  }
  const at = (i, j) => (i < 0 || j < 0 || i >= nx || j >= nz) ? null : cell[j * nx + i];
  const rr = rnd(5);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const c = cell[j * nx + i]; if (!c) continue;
    const x0 = gx0 + i * C, z0 = gz0 + j * C, x1 = x0 + C, z1 = z0 + C, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
    const mat = nearestSurface(cx, cz), sc = mat === 'alcSett' || mat === 'alcAsphalt' ? 1 / 2.4 : 1, f = .86 + .16 * (vn(cx * .33 + cz * .21, 3) + vn(cz * .29 - cx * .17, 8)) * .5 + .08 * vn(cx * 1.7 + cz * .9, 4) + .03 * rr(), tint = [f, f * .985, f * .96];
    const P = [[x0, c.y[0], z0], [x1, c.y[1], z0], [x1, c.y[2], z1], [x0, c.y[3], z1]];
    const useMat = mat === 'alcPebbleFlat' ? 'alcPebbleFlat' : mat;
    const us = useMat === 'alcPebbleFlat' ? 1 / 6 : sc, vs = useMat === 'alcPebbleFlat' ? 1 / 3 : sc;
    Q(useMat, P, P.map(p => [p[0] * us, p[2] * vs]), tint, [0, 1, 0]);
    // registry for door levels
    for (let a = 0; a < 2; a++) for (let bb = 0; bb < 2; bb++) { const k = ri(x0 + (a + .5) * C / 2, z0 + (bb + .5) * C / 2); if (k >= 0 && Number.isNaN(PH[k])) PH[k] = (c.y[0] + c.y[1] + c.y[2] + c.y[3]) / 4; }
    stats.ground++; if (c.plateau) { stats.plat = (stats.plat || 0) + 1; }
    // risers / skirts toward the neighbours (east and south: each pair once; the others are covered by their own cell)
    const edgeH = (cc, side) => side === 'E' ? [cc.y[1], cc.y[2]] : side === 'W' ? [cc.y[0], cc.y[3]] : side === 'S' ? [cc.y[3], cc.y[2]] : [cc.y[0], cc.y[1]];
    for (const [di, dj, side, oside] of [[1, 0, 'E', 'W'], [0, 1, 'S', 'N']]) {
      const n = at(i + di, j + dj);
      const mine = edgeH(c, side);
      if (!n) { // boundary against a wall or the outside: a skirt
        continue;
      }
      const th = edgeH(n, oside);
      if (Math.abs(mine[0] - th[0]) > .008 || Math.abs(mine[1] - th[1]) > .008) {
        const e0 = side === 'E' ? [x1, z0] : [x0, z1], e1 = side === 'E' ? [x1, z1] : [x1, z1];
        // from first to second end of the shared edge (z0..z1 for E, x0..x1 for S)
        const A = side === 'E' ? [x1, z0] : [x0, z1], B = side === 'E' ? [x1, z1] : [x1, z1];
        const hi = [Math.max(mine[0], th[0]), Math.max(mine[1], th[1])], lo = [Math.min(mine[0], th[0]), Math.min(mine[1], th[1])];
        const low = mine[0] + mine[1] < th[0] + th[1] ? [di, dj] : [-di, -dj]; // direction toward the lower side
        Q('alcStone', [[A[0], lo[0], A[1]], [B[0], lo[1], B[1]], [B[0], hi[1], B[1]], [A[0], hi[0], A[1]]], [[0, 0], [C / 2.4, 0], [C / 2.4, .1], [0, .1]], [.72, .70, .66], [low[0], 0, low[1]]);
        stats.risers++;
      }
    }
    // outer border of the paved region: a short skirt
    for (const [di, dj, side] of [[1, 0, 'E'], [-1, 0, 'W'], [0, 1, 'S'], [0, -1, 'N']]) {
      const ii = i + di, jj = j + dj; if (ii >= 0 && jj >= 0 && ii < nx && jj < nz) continue;
      const A = side === 'E' ? [x1, z0] : side === 'W' ? [x0, z1] : side === 'S' ? [x1, z1] : [x0, z0], B = side === 'E' ? [x1, z1] : side === 'W' ? [x0, z0] : side === 'S' ? [x0, z1] : [x1, z0];
      const Hh = side === 'E' ? [c.y[1], c.y[2]] : side === 'W' ? [c.y[3], c.y[0]] : side === 'S' ? [c.y[2], c.y[3]] : [c.y[0], c.y[1]];
      Q('alcStone', [[A[0], Hh[0], A[1]], [B[0], Hh[1], B[1]], [B[0], Hh[1] - 1, B[1]], [A[0], Hh[0] - 1, A[1]]], [[0, 0], [C / 2.4, 0], [C / 2.4, .4], [0, .4]], [.7, .68, .64], [di, 0, dj]);
    }
  }
}

// ---------------------------------------------------------------- small cached models (local frame: x along the facade, y up, z outward)
const col = hex => { const c = new THREE.Color(hex); return [c.r, c.g, c.b]; };
const mulc = (c, k) => [c[0] * k, c[1] * k, c[2] * k];
const mixc = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
class Un {
  constructor() { this.g = new Geo(); this.d = new Geo(); }
  dq(P, c, U) { quadTo(this.d, P, U || [[0, 0], [1, 0], [1, 1], [0, 1]], c, null); }
  q(P, c, hint, U) { quadTo(this.g, P, U || [[0, 0], [1, 0], [1, 1], [0, 1]], c, hint); }
  tri(P, c, hint) { triTo(this.g, P, [[0, 0], [1, 0], [0, 1]], c, hint); }
  box(x0, x1, y0, y1, z0, z1, c, bottom = false, top = true) {
    const q = (P, h) => this.q(P, c, h);
    q([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], [0, 0, 1]);
    q([[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]], [0, 0, -1]);
    q([[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]], [1, 0, 0]);
    q([[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]], [-1, 0, 0]);
    if (top) q([[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]], [0, 1, 0]);
    if (bottom) q([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], [0, -1, 0]);
  }
  // vertical (optionally tapered) cylinder
  cyl(x, y, z, r0, r1, h, n, c, cap = true) {
    for (let i = 0; i < n; i++) {
      const a0 = i / n * Math.PI * 2, a1 = (i + 1) / n * Math.PI * 2, m = (a0 + a1) / 2;
      this.q([[x + Math.cos(a0) * r0, y, z + Math.sin(a0) * r0], [x + Math.cos(a1) * r0, y, z + Math.sin(a1) * r0], [x + Math.cos(a1) * r1, y + h, z + Math.sin(a1) * r1], [x + Math.cos(a0) * r1, y + h, z + Math.sin(a0) * r1]], c, [Math.cos(m), 0, Math.sin(m)]);
      if (cap && r1 > 0) this.tri([[x, y + h, z], [x + Math.cos(a0) * r1, y + h, z + Math.sin(a0) * r1], [x + Math.cos(a1) * r1, y + h, z + Math.sin(a1) * r1]], c, [0, 1, 0]);
    }
  }
  sph(x, y, z, rx, ry, rz, c, nl = 3, nn = 7) {
    const pt = (la, lo) => { const th = la / nl * Math.PI, ph = lo / nn * Math.PI * 2; return [x + Math.sin(th) * Math.cos(ph) * rx, y + Math.cos(th) * ry, z + Math.sin(th) * Math.sin(ph) * rz]; };
    for (let la = 0; la < nl; la++) for (let lo = 0; lo < nn; lo++) {
      const a = pt(la, lo), b = pt(la, lo + 1), cc = pt(la + 1, lo + 1), d = pt(la + 1, lo), hint = [(a[0] + b[0] + cc[0] + d[0]) / 4 - x, (a[1] + b[1] + cc[1] + d[1]) / 4 - y, (a[2] + b[2] + cc[2] + d[2]) / 4 - z];
      if (la === 0) this.tri([a, cc, d], c, hint); else if (la === nl - 1) this.tri([a, b, cc], c, hint); else this.q([a, b, cc, d], c, hint);
    }
  }
  geo() { const g = this.g.geometry(); g.ds = this.d.count ? this.d.geometry() : null; return g; }
}
const UC = new Map();
function unit(key, fn) { let g = UC.get(key); if (!g) { const u = new Un(); fn(u); g = u.geo(); g.ukey = key; UC.set(key, g); } return g; }
// place a cached model (and its double-sided thin parts)
const UST = {};
function addU(geo, mat, pos, rot) { const kk = (geo.ukey || '?').split('|')[0]; const t = (geo.index ? geo.index.count : geo.attributes.position.count) / 3 + (geo.ds ? geo.ds.index.count / 3 : 0); (UST[kk] = UST[kk] || [0, 0]); UST[kk][0] += t; UST[kk][1]++; BLD.add(geo, mat, pos, [1, 1, 1], rot); if (geo.ds) BLD.add(geo.ds, 'alcDetailDS', pos, [1, 1, 1], rot); STAT.props++; }

const PAL = {
  white: col(0xf3eee4), cream: col(0xf0e4c6), yellow: col(0xe8c978), ochre: col(0xdbab5c), salmon: col(0xdf9c84), terra: col(0xc6735a), grey: col(0xd2d0c7), green: col(0xc0cfb2), blue: col(0xb8cad6), orange: col(0xe3a463),
  wood: col(0x4a2f1c), woodL: col(0x7a5233), woodD: col(0x2c1b10), iron: col(0x1d1c1b), ironL: col(0x39373a), stone: col(0xcfc6b2), stoneD: col(0x9d9585), glass: col(0x14191d), black: col(0x0c0c0d),
  green2: col(0x2f4f38), greenS: col(0x3d5d3c), brown: col(0x5a3b26), white2: col(0xe9e5da), blue2: col(0x2b4d78), red: col(0x8a2a24), pot: col(0xb4623e), leaf: col(0x4c7a3a), leaf2: col(0x6c9440),
  warm: [1.35, .78, .36], warm2: [1.25, .62, .26], warmW: [1.3, 1.05, .7], dim: [.55, .30, .13],
};
const FLOWERS = [col(0xd9304a), col(0xe8743c), col(0xf0c8d0), col(0xc83c8c), col(0xf3e8d8), col(0xd8483a)];
const TINTS = [['white', 24], ['cream', 15], ['yellow', 16], ['ochre', 14], ['salmon', 10], ['terra', 6], ['grey', 3], ['green', 4], ['blue', 3], ['orange', 7]];
function pick(r, table) { let t = 0; for (const [, w] of table) t += w; let x = r() * t; for (const [k, w] of table) { x -= w; if (x <= 0) return k; } return table[0][0]; }
const bar4 = (u, x, z, y0, y1, c, t = .012) => { u.dq([[x - t, y0, z], [x + t, y0, z], [x + t, y1, z], [x - t, y1, z]], c); u.dq([[x, y0, z - t], [x, y0, z + t], [x, y1, z + t], [x, y1, z - t]], c); };

// ---- windows: opening spans x in [-w/2, w/2], y in [0, h]; z = 0 is the facade plane, the glass sits in the reveal
const RD = .26;
function uWindow(w, h, look, frameC, shutter, reja, mullion = true) {
  return unit(`win|${w}|${h}|${look}|${frameC}|${shutter}|${reja}|${mullion}`, u => {
    const fc = PAL[frameC] || PAL.white2, z0 = -RD + .05, zf = z0 + .06;
    const back = look === 0 ? PAL.glass : look === 1 ? col(0xcfc4a8) : look === 2 ? col(0xb08a6a) : look === 3 ? col(0x5b3d28) : col(0x88a0a8);
    u.q([[-w / 2, 0, z0], [w / 2, 0, z0], [w / 2, h, z0], [-w / 2, h, z0]], look === 0 ? [mulc(back, 2.4), mulc(back, 2.4), mulc(back, .5), mulc(back, .5)] : [mulc(back, 1), mulc(back, 1), mulc(back, .85), mulc(back, .85)], [0, 0, 1]);
    if (look === 3) for (let k = 0; k < 4; k++) u.q([[-w / 2, h * k / 4 + .03, z0 + .01], [w / 2, h * k / 4 + .03, z0 + .01], [w / 2, h * k / 4 + .06, z0 + .01], [-w / 2, h * k / 4 + .06, z0 + .01]], mulc(back, .6), [0, 0, 1]);
    const t = .06, fq = (x0, x1, y0, y1) => u.q([[x0, y0, zf], [x1, y0, zf], [x1, y1, zf], [x0, y1, zf]], fc, [0, 0, 1]);
    fq(-w / 2, -w / 2 + t, 0, h); fq(w / 2 - t, w / 2, 0, h); fq(-w / 2, w / 2, h - t, h); fq(-w / 2, w / 2, 0, t);
    if (mullion) { fq(-.02, .02, t, h - t); if (h > 1.2) fq(-w / 2 + t, w / 2 - t, h * .62, h * .62 + .035); }
    u.box(-w / 2 - .09, w / 2 + .09, -.07, 0, -RD, .12, PAL.stone, false, true); // sill
    if (shutter) {
      const sc = shutter === 1 ? PAL.green2 : shutter === 2 ? PAL.brown : PAL.white2;
      for (const sx of [-1, 1]) {
        const xa = sx > 0 ? w / 2 + .012 : -w / 2 - .012 - w / 2, xb = xa + w / 2;
        u.q([[xa, .02, .03], [xb, .02, .03], [xb, h - .02, .03], [xa, h - .02, .03]], sc, [0, 0, 1]);
        for (let k = 0; k < 3; k++) u.q([[xa + .03, .08 + (h - .2) * k / 3, .035], [xb - .03, .08 + (h - .2) * k / 3, .035], [xb - .03, .08 + (h - .2) * (k + .5) / 3, .035], [xa + .03, .08 + (h - .2) * (k + .5) / 3, .035]], mulc(sc, .66), [0, 0, 1]);
      }
    }
    if (reja) rejaBars(u, w, h, .12, reja);
  });
}
function uWinCheap(w, h, look, rj) {
  return unit(`wc|${w}|${h}|${look}|${rj}`, u => {
    const z0 = -RD + .05, back = look === 0 ? PAL.glass : look === 1 ? col(0xcfc4a8) : look === 2 ? col(0xb08a6a) : col(0x5b3d28), fc = PAL.white2, t = .07;
    u.q([[-w / 2, 0, z0], [w / 2, 0, z0], [w / 2, h, z0], [-w / 2, h, z0]], look === 0 ? [mulc(back, 2.2), mulc(back, 2.2), mulc(back, .6), mulc(back, .6)] : back, [0, 0, 1]);
    const fq = (x0, x1, y0, y1) => u.q([[x0, y0, z0 + .04], [x1, y0, z0 + .04], [x1, y1, z0 + .04], [x0, y1, z0 + .04]], fc, [0, 0, 1]);
    fq(-w / 2, -w / 2 + t, 0, h); fq(w / 2 - t, w / 2, 0, h); fq(-w / 2, w / 2, h - t, h); fq(-.02, .02, t, h - t);
    u.q([[-w / 2 - .06, -.02, .1], [w / 2 + .06, -.02, .1], [w / 2 + .06, -.02, -RD], [-w / 2 - .06, -.02, -RD]], PAL.stone, [0, 1, 0]);
    if (rj) for (let i = 0; i <= 3; i++) bar4(u, -w / 2 + w * i / 3, .09, -.02, h + .02, PAL.iron);
  });
}
function rejaBars(u, w, h, z, kind) {
  const c = PAL.iron, n = Math.max(3, Math.round(w / .14)), bow = kind === 2 ? .09 : 0;
  const rail = (y, th) => { u.q([[-w / 2 - .04, y, z + bow], [w / 2 + .04, y, z + bow], [w / 2 + .04, y + th, z + bow], [-w / 2 - .04, y + th, z + bow]], c, [0, 0, 1]); u.q([[-w / 2 - .04, y + th, z + bow], [w / 2 + .04, y + th, z + bow], [w / 2 + .04, y + th, z], [-w / 2 - .04, y + th, z]], c, [0, 1, 0]); };
  rail(-.04, .04); rail(h, .035); rail(h * .5, .022);
  for (let i = 0; i <= n; i++) bar4(u, -w / 2 + w * i / n, z + bow * (kind === 2 ? Math.sin(Math.PI * i / n) : 0), -.03, h + .03, c);
}
function uFlowerPot(kind) {
  return unit(`pot|${kind}`, u => {
    const fl = FLOWERS[kind % FLOWERS.length];
    u.cyl(0, 0, 0, .075, .1, .17, 5, PAL.pot, false); u.sph(0, .26, 0, .16, .11, .16, PAL.leaf, 1, 5);
    for (let i = 0; i < 3; i++) { const a = i * 2.4; u.sph(Math.cos(a) * .09, .34 + (i % 2) * .03, Math.sin(a) * .09, .045, .035, .045, fl, 1, 4); }
  });
}
function uBalcony(w, rail = 0) {
  return unit(`balc|${w}|${rail}`, u => {
    const bw = w + .5, d = .62, c = PAL.iron;
    u.box(-bw / 2, bw / 2, -.12, -.01, 0, d, PAL.stone, true);
    u.box(-bw / 2 - .02, bw / 2 + .02, -.14, -.12, 0, d + .02, mulc(PAL.stone, .85));
    for (const x of [-bw / 2 + .12, bw / 2 - .12]) u.box(x - .04, x + .04, -.34, -.12, 0, .3, PAL.stoneD);
    const hh = .98;
    const bars = (x0, z0, x1, z1) => { const n = Math.max(1, Math.round(hyp(x1 - x0, z1 - z0) / .16)); for (let i = 0; i <= n; i++) bar4(u, x0 + (x1 - x0) * i / n, z0 + (z1 - z0) * i / n, 0, hh, c); };
    bars(-bw / 2 + .02, d - .02, bw / 2 - .02, d - .02); bars(-bw / 2 + .02, .0, -bw / 2 + .02, d - .02); bars(bw / 2 - .02, 0, bw / 2 - .02, d - .02);
    u.box(-bw / 2, bw / 2, hh, hh + .035, d - .04, d, c); u.box(-bw / 2, -bw / 2 + .035, hh, hh + .035, 0, d, c); u.box(bw / 2 - .035, bw / 2, hh, hh + .035, 0, d, c);
    u.box(-bw / 2, bw / 2, .06, .085, d - .03, d - .005, c);
  });
}
function uDoorLeaf(w, h, variant) {
  return unit(`door|${w}|${h}|${variant}`, u => {
    const wood = variant === 0 ? PAL.wood : variant === 1 ? PAL.woodL : variant === 2 ? PAL.greenS : PAL.brown, z0 = -RD + .05, z1 = z0 + .06;
    u.box(-w / 2, w / 2, 0, h, z0, z1, wood);
    const pw = (w - .3) / 2, ph = (h - .55) / 2;
    for (const px of [-1, 1]) for (const py of [0, 1]) { const x0 = px < 0 ? -w / 2 + .1 : .05, y0 = .15 + py * (ph + .25); u.box(x0, x0 + pw, y0, y0 + ph, z1, z1 + .02, mulc(wood, .72)); }
    u.box(-.01, .01, 0, h, z1, z1 + .03, PAL.black);
    u.cyl(w / 2 - .12, h * .45, z1 + .02, .03, .03, .015, 6, col(0xb08d45));
    for (let k = 0; k < 8; k++) u.sph(-w / 2 + .1 + (w - .2) * (k % 4) / 3, .22 + Math.floor(k / 4) * (h - .5), z1 + .02, .018, .018, .012, PAL.iron, 1, 4);
  });
}
function uDoorSurround(w, h, kind) {
  return unit(`surr|${w}|${h}|${kind}`, u => {
    const s = kind === 0 ? PAL.stone : kind === 1 ? PAL.woodL : PAL.stoneD, t = .16;
    u.box(-w / 2 - t, -w / 2, -.06, h + t * .8, -RD, .07, s); u.box(w / 2, w / 2 + t, -.06, h + t * .8, -RD, .07, s); u.box(-w / 2 - t, w / 2 + t, h, h + t * .8, -RD, .07, s);
    u.box(-w / 2 - t - .05, w / 2 + t + .05, h + t * .8, h + t * .8 + .06, -RD, .11, s);
    u.box(-w / 2 - .02, w / 2 + .02, -.18, -.0, -RD + .1, .35, PAL.stoneD, true);
  });
}
function uLanternWall() {
  return unit('lw', u => {
    const c = PAL.iron;
    u.box(-.015, .015, 0, .55, 0, .02, c); u.box(-.012, .012, .5, .53, 0, .38, c);
    u.box(-.09, .09, .55, .6, .36, .54, c);
    u.box(-.075, .075, .26, .54, .38, .52, PAL.warmW); u.box(-.095, .095, .26, .29, .36, .54, c); u.box(-.095, .095, .5, .53, .36, .54, c);
  });
}
function uHangLantern(kind) {
  return unit(`hl|${kind}`, u => {
    const c = PAL.iron, n = 8, r0 = .26, r1 = .29, h = .85;
    const glow = kind === 0 ? [1.5, .95, .52] : [1.3, 1.05, .75];
    u.cyl(0, .12, 0, r0 * .96, r1 * .96, h - .2, n, glow, false);
    u.cyl(0, 0, 0, r0 * .5, r0 * .5, .12, n, c); u.cyl(0, .12, 0, r0, r0, .04, n, c);
    u.cyl(0, h - .08, 0, r1, r1, .05, n, c); u.cyl(0, h - .03, 0, r1 * .95, .05, .22, n, c, true);
    
    u.box(-.006, .006, h + .12, h + .6, -.006, .006, c);
  });
}

// ---------------------------------------------------------------- facades
const H0 = 3.6, HS = 3.0;
function vn(x, seed = 0) {
  const i = Math.floor(x), f = x - i, t = f * f * (3 - 2 * f);
  const h = k => { let n = Math.imul(i + k, 374761393) + Math.imul(seed | 0, 668265263); n = Math.imul(n ^ (n >>> 13), 1274126177); return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
  return h(0) * (1 - t) + h(1) * t;
}
function frameOf(e) {
  const [ax, az, bx, bz, , , nx, nz] = e; const tx = nz, tz = -nx; let sx = ax, sz = az, ex = bx, ez = bz;
  if ((bx - ax) * tx + (bz - az) * tz < 0) { sx = bx; sz = bz; ex = ax; ez = az; }
  return { x: sx, z: sz, tx, tz, nx, nz, len: hyp(ex - sx, ez - sz), rot: Math.atan2(nx, nz) };
}
let BLD = null;     // builder
const STAT = { lane: 0, navLane: 0, ground: 0, risers: 0, walls: 0, win: 0, shops: 0, props: 0 };
class Fac {
  constructor(B, e, simple) {
    Object.assign(this, frameOf(e)); this.B = B; this.e = e; this.simple = simple; this.pois = e.pois || [];
    const ns = Math.max(2, Math.ceil(this.len / .5) + 1); this.ns = ns; this.gr = [];
    for (let i = 0; i < ns; i++) { const u = this.len * i / (ns - 1); this.gr.push(pavH(this.x + this.tx * u + this.nx * .5, this.z + this.tz * u + this.nz * .5)); }
    this.n3 = [this.nx, 0, this.nz]; this.t3 = [this.tx, 0, this.tz];
  }
  P(u, y, w = 0) { return [this.x + this.tx * u + this.nx * w, y, this.z + this.tz * u + this.nz * w]; }
  g(u) { const f = clamp(u / this.len, 0, 1) * (this.ns - 1), i = Math.min(this.ns - 2, Math.floor(f)); return lerp(this.gr[i], this.gr[i + 1], f - i); }
  gmin(u0, u1) { let m = 1e9; for (let u = u0; u <= u1 + .01; u += .5) m = Math.min(m, this.g(Math.min(u, u1))); return m; }
  floor(s) { return s <= 0 ? this.B.Y0 : this.B.Y0 + H0 + HS * (s - 1); }
  shade(u, y) { const hh = y - this.g(u); return (.74 + .26 * clamp((hh + .3) / 1.7, 0, 1)) * (1 + .07 * (vn(u * .45 + this.B.k * 3.1, 5) - .5) + .03 * (vn(y * .8 + u * .2, 9) - .5)); }
  wc(u, y, k = 1) { return mulc(this.B.tint, this.shade(u, y) * k); }
  // front face of the wall between u0..u1, y0..y1 (split where the dirt gradient ends)
  wq(u0, u1, y0, y1, w = 0, mat = this.B.mat, k = 1) {
    if (y1 - y0 < .004 || u1 - u0 < .004) return;
    const piece = (a, b) => { const uo = this.B.uo; Q(mat, [this.P(u0, a, w), this.P(u1, a, w), this.P(u1, b, w), this.P(u0, b, w)], [[u0 / 3 + uo, a / 3], [u1 / 3 + uo, a / 3], [u1 / 3 + uo, b / 3], [u0 / 3 + uo, b / 3]], [this.wc(u0, a, k), this.wc(u1, a, k), this.wc(u1, b, k), this.wc(u0, b, k)], this.n3); STAT.walls++; };
    const gm = this.g((u0 + u1) / 2), yb = gm + 1.4;
    if (y0 < yb - .05 && y1 > yb + .05) { piece(y0, yb); piece(yb, y1); } else piece(y0, y1);
  }
  // coloured box on the facade (front, top, bottom, sides)
  fb(mat, u0, u1, y0, y1, w0, w1, c, sides = true) {
    const uo = this.B.uo, P = (u, y, w) => this.P(u, y, w), n = this.n3;
    const uv = (a, b) => [[a, b], [a + 1, b], [a + 1, b + 1], [a, b + 1]];
    Q(mat, [P(u0, y0, w1), P(u1, y0, w1), P(u1, y1, w1), P(u0, y1, w1)], [[u0 / 3, y0 / 3], [u1 / 3, y0 / 3], [u1 / 3, y1 / 3], [u0 / 3, y1 / 3]], c, n);
    Q(mat, [P(u0, y1, w1), P(u1, y1, w1), P(u1, y1, w0), P(u0, y1, w0)], [[u0 / 3, 0], [u1 / 3, 0], [u1 / 3, (w1 - w0) / 3], [u0 / 3, (w1 - w0) / 3]], c, [0, 1, 0]);
    Q(mat, [P(u0, y0, w1), P(u1, y0, w1), P(u1, y0, w0), P(u0, y0, w0)], [[u0 / 3, 0], [u1 / 3, 0], [u1 / 3, (w1 - w0) / 3], [u0 / 3, (w1 - w0) / 3]], mulc(c, .7), [0, -1, 0]);
    if (sides) {
      Q(mat, [P(u0, y0, w0), P(u0, y0, w1), P(u0, y1, w1), P(u0, y1, w0)], [[0, y0 / 3], [(w1 - w0) / 3, y0 / 3], [(w1 - w0) / 3, y1 / 3], [0, y1 / 3]], mulc(c, .85), [-this.tx, 0, -this.tz]);
      Q(mat, [P(u1, y0, w0), P(u1, y0, w1), P(u1, y1, w1), P(u1, y1, w0)], [[0, y0 / 3], [(w1 - w0) / 3, y0 / 3], [(w1 - w0) / 3, y1 / 3], [0, y1 / 3]], mulc(c, .85), [this.tx, 0, this.tz]);
    }
  }
  place(geo, mat, u, y, w = 0, rotAdd = 0) { const p = this.P(u, y, w); addU(geo, mat, p, this.rot + rotAdd); return p; }
  // inner faces of a rectangular or arched opening
  reveal(op) {
    const { u0, u1, y0, y1 } = op, c = mulc(this.B.tint, .78), P = (u, y, w) => this.P(u, y, w), mat = this.B.mat, uv = [[0, 0], [1, 0], [1, 1], [0, 1]];
    Q(mat, [P(u0, y0, 0), P(u0, y0, -RD), P(u0, op.top(u0), -RD), P(u0, op.top(u0), 0)], uv, c, this.t3);
    Q(mat, [P(u1, y0, 0), P(u1, y0, -RD), P(u1, op.top(u1), -RD), P(u1, op.top(u1), 0)], uv, c, [-this.tx, 0, -this.tz]);
    Q(mat, [P(u0, y0, 0), P(u1, y0, 0), P(u1, y0, -RD), P(u0, y0, -RD)], uv, mulc(c, 1.1), [0, 1, 0]);
    if (!op.arch) Q(mat, [P(u0, y1, 0), P(u1, y1, 0), P(u1, y1, -RD), P(u0, y1, -RD)], uv, mulc(c, .7), [0, -1, 0]);
    else {
      const n = op.arch.n, cx = (u0 + u1) / 2;
      for (let k = 0; k < n; k++) { const a = u0 + (u1 - u0) * k / n, b = u0 + (u1 - u0) * (k + 1) / n, ya = op.top(a), yb = op.top(b), um = (a + b) / 2; Q(mat, [P(a, ya, 0), P(b, yb, 0), P(b, yb, -RD), P(a, ya, -RD)], uv, mulc(c, .72), [(cx - um) * this.tx * .5, -1, (cx - um) * this.tz * .5]); }
    }
  }
}
function arcOp(u0, u1, y0, ys, kind = 0) {
  // round (kind 0) or slightly pointed-horseshoe style arch opening; springline ys
  const r = (u1 - u0) / 2, cx = (u0 + u1) / 2, n = 10;
  const top = u => { const d = clamp((u - cx) / r, -1, 1); return ys + Math.sqrt(Math.max(0, 1 - d * d)) * r * (kind ? 1.12 : 1); };
  return { u0, u1, y0, y1: ys + r * (kind ? 1.12 : 1), top, arch: { n, r, cx, ys } };
}
const rectOp = (u0, u1, y0, y1) => ({ u0, u1, y0, y1, top: () => y1, arch: null });

function emitStorey(F, s, ops) {
  const B = F.B, len = F.len, L = B.L;
  const ytop = s >= L - 1 ? B.top : F.floor(s + 1);
  const ybot = (u0, u1) => s === 0 ? F.gmin(u0, u1) - .35 : F.floor(s);
  ops = ops.filter(o => o.u1 > o.u0 + .05).sort((a, b) => a.u0 - b.u0);
  (F.rects = F.rects || []).push(...ops);
  let u = 0;
  for (const op of ops) {
    if (op.u0 > u + .001) F.wq(u, op.u0, ybot(u, op.u0), ytop);
    const yb = s === 0 ? F.gmin(op.u0, op.u1) - .35 : F.floor(s);
    if (op.y0 > yb + .02) F.wq(op.u0, op.u1, yb, op.y0);
    // above
    if (!op.arch) F.wq(op.u0, op.u1, op.y1, ytop);
    else { const n = op.arch.n; for (let k = 0; k < n; k++) { const a = op.u0 + (op.u1 - op.u0) * k / n, b = op.u0 + (op.u1 - op.u0) * (k + 1) / n; const ya = op.top(a), yb2 = op.top(b), uo = F.B.uo; Q(B.mat, [F.P(a, ya, 0), F.P(b, yb2, 0), F.P(b, ytop, 0), F.P(a, ytop, 0)], [[a / 3 + uo, ya / 3], [b / 3 + uo, yb2 / 3], [b / 3 + uo, ytop / 3], [a / 3 + uo, ytop / 3]], [F.wc(a, ya), F.wc(b, yb2), F.wc(b, ytop), F.wc(a, ytop)], F.n3); } }
    F.reveal(op);
    u = op.u1;
  }
  if (u < len - .001) F.wq(u, len, ybot(u, len), ytop);
}

// ---------------------------------------------------------------- composing a street facade, bay by bay
function roofH(B, x, z) {
  const r = B.roof; if (r.kind === 'flat') return 0;
  const dx = x - r.ctr[0], dz = z - r.ctr[1], s = dx * r.ax[0] + dz * r.ax[1], t = -dx * r.ax[1] + dz * r.ax[0], hw = r.W / 2;
  return Math.max(0, r.kind === 'hip' ? Math.min(hw - Math.abs(t), r.L / 2 - Math.abs(s)) : hw - Math.abs(t)) * r.tanp;
}
function gableFill(F) {
  const B = F.B; if (B.roof.kind === 'flat') return;
  const n = Math.max(1, Math.ceil(F.len / .4)), us = [], hs = [];
  for (let i = 0; i <= n; i++) { const u = F.len * i / n, p = F.P(u, 0, 0); us.push(u); hs.push(roofH(B, p[0], p[2])); }
  for (let i = 0; i < n; i++) {
    if (hs[i] < .03 && hs[i + 1] < .03) continue;
    const uo = B.uo, y = B.top;
    Q(B.mat, [F.P(us[i], y, 0), F.P(us[i + 1], y, 0), F.P(us[i + 1], y + hs[i + 1], 0), F.P(us[i], y + hs[i], 0)], [[us[i] / 3 + uo, y / 3], [us[i + 1] / 3 + uo, y / 3], [us[i + 1] / 3 + uo, (y + hs[i + 1]) / 3], [us[i] / 3 + uo, (y + hs[i]) / 3]], [F.wc(us[i], y), F.wc(us[i + 1], y), F.wc(us[i + 1], y + hs[i + 1]), F.wc(us[i], y + hs[i])], F.n3);
  }
}
const OV = .5;
function eaves(F) {
  const B = F.B, r = B.roof; if (r.kind === 'flat') return;
  // overhang only where the roof slopes away from this wall (the long sides)
  const mid = F.P(F.len / 2, 0, 0), h = roofH(B, mid[0], mid[2]); if (h > .15) return;
  const yS = B.top - OV * r.tanp - .13, wd = B.wood;
  Q('alcWood', [F.P(0, yS, 0), F.P(F.len, yS, 0), F.P(F.len, yS, OV), F.P(0, yS, OV)], [[0, 0], [F.len / 2, 0], [F.len / 2, .3], [0, .3]], mulc(wd, .8), [0, -1, 0]);
  Q('alcWood', [F.P(0, yS, OV), F.P(F.len, yS, OV), F.P(F.len, yS + .15, OV), F.P(0, yS + .15, OV)], [[0, 0], [F.len / 2, 0], [F.len / 2, .1], [0, .1]], wd, F.n3);
  // rafter ends under the soffit
  for (let u = .35; u < F.len - .2; u += .6) F.fb('alcWood', u - .035, u + .035, yS - .1, yS, .0, OV * .92, mulc(wd, .9), false);
}
function cornice(F, strong) {
  const B = F.B; if (B.roof.kind !== 'flat') return; // pitched roofs have their eaves
  const c = mulc(B.tint, 1.04);
  F.fb(B.mat, 0, F.len, B.top - .32, B.top - .06, .0, .13, c);
  F.fb(B.mat, 0, F.len, B.top - .06, B.top + .05, .0, .17, mulc(c, 1.05));
}
function plinth(F, ops, rr) {
  const B = F.B, h = B.plinthH; if (!h) return;
  const skip = ops.filter(o => o.nopl).map(o => [o.u0 - .15, o.u1 + .15]); let u = 0;
  const segs = []; for (const [a, b] of skip.sort((p, q) => p[0] - q[0])) { if (a > u) segs.push([u, Math.min(a, F.len)]); u = Math.max(u, b); } if (u < F.len) segs.push([u, F.len]);
  for (const [a, b] of segs) {
    const n = Math.max(1, Math.ceil((b - a) / 1.2));
    for (let i = 0; i < n; i++) {
      const u0 = a + (b - a) * i / n, u1 = a + (b - a) * (i + 1) / n, g0 = F.g(u0), g1 = F.g(u1), w = .04, c = mulc(B.plinthC, .96 + .08 * rr());
      Q('alcStone', [F.P(u0, g0 - .06, w), F.P(u1, g1 - .06, w), F.P(u1, g1 + h, w), F.P(u0, g0 + h, w)], [[u0 / 2.4, (g0) / 2.4], [u1 / 2.4, g1 / 2.4], [u1 / 2.4, (g1 + h) / 2.4], [u0 / 2.4, (g0 + h) / 2.4]], c, F.n3);
      Q('alcStone', [F.P(u0, g0 + h, w), F.P(u1, g1 + h, w), F.P(u1, g1 + h + .035, 0), F.P(u0, g0 + h + .035, 0)], [[0, 0], [.5, 0], [.5, .1], [0, .1]], mulc(c, 1.1), [0, 1, 0]);
    }
  }
}
// string course between storeys
function stringCourse(F, s) {
  const y = F.floor(s) - .08; F.fb(F.B.mat, 0, F.len, y - .08, y + .08, 0, .045, mulc(F.B.tint, 1.06), false);
}

const WIN_W = [.9, 1.0, 1.1], WIN_H = [1.5, 1.6, 1.7];
function windowOp(F, cx, y0, w, h) { return rectOp(cx - w / 2, cx + w / 2, y0, y0 + h); }
function placeWindow(F, op, rr, o = {}) {
  const w = op.u1 - op.u0, h = op.y1 - op.y0, cx = (op.u0 + op.u1) / 2;
  const look = o.look ?? (rr() < .62 ? 0 : rr() < .5 ? 1 : rr() < .6 ? 2 : 3), fc = o.frame ?? (rr() < .5 ? 'white2' : rr() < .6 ? 'brown' : rr() < .6 ? 'greenS' : 'iron');
  const shutter = LOW ? 0 : (o.shutter ?? (rr() < .28 ? 1 + Math.floor(rr() * 3) : 0)), reja = LOW ? 0 : (o.reja ?? 0);
  F.place(uWindow(+w.toFixed(2), +h.toFixed(2), look, fc, shutter, reja, rr() < .8), 'alcDetail', cx, op.y0, 0);
  if (o.lit) { const wq = w - .14, hq = h - .12; F.place(unit(`lit|${wq.toFixed(2)}|${hq.toFixed(2)}`, u => u.q([[-wq / 2, 0, 0], [wq / 2, 0, 0], [wq / 2, hq, 0], [-wq / 2, hq, 0]], [[1.35, .9, .5], [1.35, .9, .5], [.9, .55, .25], [.9, .55, .25]], [0, 0, 1])), 'alcGlow', cx, op.y0 + .05, -RD + .09); }
  if (!LOW && o.pot !== false && rr() < (o.potP ?? .18) && w > .8) F.place(uFlowerPot(Math.floor(rr() * 6)), 'alcDetail', cx + (rr() - .5) * .4, op.y0 + .0, .06);
  STAT.win++;
}
function placeBalcony(F, op, rr) {
  const w = op.u1 - op.u0, cx = (op.u0 + op.u1) / 2, h = op.y1 - op.y0;
  const look = rr() < .6 ? 0 : rr() < .6 ? 1 : 3, fc = rr() < .55 ? 'brown' : rr() < .5 ? 'white2' : 'greenS';
  F.place(uWindow(+w.toFixed(2), +h.toFixed(2), look, fc, rr() < .3 ? 1 + Math.floor(rr() * 3) : 0, 0, true), 'alcDetail', cx, op.y0, 0);
  const ww = +w.toFixed(2);
  F.place(uBalcony(ww), 'alcDetail', cx, op.y0, 0);
  const np = Math.floor(rr() * 4); for (let i = 0; i < np; i++) F.place(uFlowerPot(Math.floor(rr() * 6)), 'alcDetail', cx - w / 2 - .1 + (w + .2) * (i + .5) / np, op.y0 - .01, .5);
  STAT.win++;
}

function streetFacade(F, tw) {
  const B = F.B, len = F.len, L = B.L, rr = rnd((B.k * 2654435761 + Math.floor(F.x * 31) * 7 + Math.floor(F.z * 17)) | 0);
  F.rr = rr;
  const nb = Math.max(1, Math.round(len / 3.0)), bw = len / nb, E1 = F.floor(1);
  const bayPoi = new Array(nb).fill(null); for (const p of F.pois) { const k = clamp(Math.floor(p.u / bw), 0, nb - 1); if (!bayPoi[k]) bayPoi[k] = p; }
  const gops = [], types = [];
  // ground storey
  for (let k = 0; k < nb; k++) {
    const poi = bayPoi[k]; let type;
    if (poi) type = poi.kind;
    else if (bw < 1.8) type = rr() < .55 ? 'door' : 'win';
    else { const r = rr(), ps = .06 + .42 * tw, pb = .04 + .05 * tw, pt = .02 + .06 * tw, pd = .30; type = r < ps ? 'shop' : r < ps + pb ? 'bar' : r < ps + pb + pt ? 'tea' : r < ps + pb + pt + pd ? 'door' : 'win'; }
    types.push(type);
  }
  if (!types.some(t => t !== 'win')) { let k = Math.floor(rr() * nb); types[k] = bw > 1.5 ? 'door' : 'win'; }
  for (let k = 0; k < nb; k++) { const o = groundBay(F, k, (k + .5) * bw, bw, types[k], bayPoi[k], rr, tw, E1); for (const op of o) gops.push(op); }
  emitStorey(F, 0, gops);
  // upper storeys: windows and balconies aligned in columns
  const cols = [];
  for (let k = 0; k < nb; k++) cols.push(bw < 1.9 ? (rr() < .75 ? 'small' : 'blank') : rr() < .66 ? 'win' : rr() < .8 ? 'balc' : rr() < .6 ? 'win' : 'blank');
  if (nb >= 2 && !cols.includes('win') && !cols.includes('balc')) cols[Math.floor(rr() * nb)] = 'win';
  const wsel = Math.floor(rr() * 3), hsel = Math.floor(rr() * 3);
  for (let s = 1; s < L; s++) {
    const ops = [], fl = F.floor(s), top = s >= L - 1;
    for (let k = 0; k < nb; k++) {
      const cx = (k + .5) * bw; let c = cols[k];
      if (top && c === 'balc' && rr() < .5) c = 'win';
      if (c === 'blank') continue;
      if (c === 'small') { const op = windowOp(F, cx, fl + 1.0, .7, .9); ops.push(op); op.fn = () => placeWindow(F, op, rr, { reja: s === 1 ? 1 : 0, potP: .1 }); continue; }
      if (c === 'balc' && bw > 2.1) { const w = Math.min(bw - 1.0, 0.95 + .1 * wsel), op = rectOp(cx - w / 2, cx + w / 2, fl + .06, fl + 2.38); ops.push(op); op.fn = () => placeBalcony(F, op, rr); continue; }
      const w = Math.min(bw - .9, WIN_W[wsel]), h = top ? 1.45 : WIN_H[hsel], op = windowOp(F, cx, fl + .85 + (top ? .05 : 0), w, h); ops.push(op);
      op.fn = () => placeWindow(F, op, rr, { reja: (s === 1 && rr() < .35) ? (rr() < .3 ? 2 : 1) : 0, lit: rr() < .09 });
    }
    emitStorey(F, s, ops); for (const op of ops) op.fn && op.fn();
    if (s === 1 && rr() < .35) stringCourse(F, s);
  }
  plinth(F, gops, rr);
  cornice(F); eaves(F); gableFill(F); wallDecor(F, rr);
  // wall lamps and drain pipes
  if (len > 3 && rr() < .6) { const u = rr() < .5 ? .25 : len - .25, y = F.g(u) + 2.7; F.place(uLanternWall(), 'alcDetail', u, y, 0); F.place(uLanternWallGlass(), 'alcGlow', u, y, 0); LAMPS.push([...F.P(u, y + .4, .45), 1]); }
  if (rr() < .55) { const u = rr() < .5 ? .12 : len - .12, g = F.g(u); F.fb('alcDetail', u - .028, u + .028, g - .05, B.top - .1, .0, .065, PAL.ironL, false); }
}
function uLanternWallGlass() { return unit('lwg', u => u.box(-.075, .075, .27, .53, .385, .515, PAL.warmW, false, true)); }

// plain facades toward courtyards and back yards: fewer, simpler openings
function plainFacade(F) {
  const B = F.B, len = F.len, L = B.L, rr = rnd((B.k * 7919 + Math.floor(F.x * 13) + Math.floor(F.z * 11)) | 0);
  F.rr = rr;
  if (len < 1.4) { for (let s = 0; s < L; s++) emitStorey(F, s, []); cornice(F); eaves(F); gableFill(F); return; }
  const nb = Math.max(1, Math.round(len / 3.4)), bw = len / nb;
  for (let s = 0; s < L; s++) {
    const ops = [], fl = F.floor(s);
    for (let k = 0; k < nb; k++) {
      if (rr() < .38) continue; const cx = (k + .5) * bw, w = Math.min(bw - .9, .9);
      if (w < .5) continue; const y0 = s === 0 ? F.g(cx) + 1.1 : fl + .9, op = windowOp(F, cx, y0, w, 1.3); ops.push(op);
    }
    emitStorey(F, s, ops); for (const op of ops) { F.place(uWinCheap(+(op.u1 - op.u0).toFixed(2), +(op.y1 - op.y0).toFixed(2), rr() < .7 ? 0 : rr() < .5 ? 1 : 3, s === 0 ? 1 : 0), 'alcDetail', (op.u0 + op.u1) / 2, op.y0, 0); STAT.win++; }
  }
  cornice(F); eaves(F); gableFill(F);
}
function partyFacade(F, nbTop) {
  // wall above a lower neighbour: render with a few plain windows
  const B = F.B, len = F.len, y0 = Math.max(nbTop, F.gmin(0, len) - .3), y1 = B.top;
  if (y1 - y0 < .25) return;
  const rr = rnd((B.k * 31337 + Math.floor(F.x * 7) + Math.floor(F.z * 5)) | 0); F.rr = rr;
  // storeys that stand free above the neighbour
  const wins = [];
  if (len > 2.2) for (let s = 0; s < B.L; s++) {
    const fl = s === 0 ? F.g(len / 2) : F.floor(s); if (fl + 1.0 < y0 + .5) continue;
    const nb = Math.max(1, Math.round(len / 3.2)), bw = len / nb;
    for (let k = 0; k < nb; k++) { if (rr() < .3) continue; const cx = (k + .5) * bw, w = Math.min(bw - .9, .95); if (w < .5) continue; const yy = Math.max(fl + .9, y0 + .5); if (yy + 1.4 > (s >= B.L - 1 ? y1 - .2 : F.floor(s + 1) - .3)) continue; wins.push(windowOp(F, cx, yy, w, 1.35)); }
  }
  // wall around the windows (one strip per window, full height between them)
  wins.sort((a, b2) => a.u0 - b2.u0);
  const cuts = []; for (const w of wins) { if (cuts.length && w.u0 < cuts[cuts.length - 1].u1 + .05) continue; cuts.push(w); }
  let u = 0;
  for (const w of cuts) { F.wq(u, w.u0, y0, y1, 0, B.mat, .94); F.wq(w.u0, w.u1, y0, w.y0, 0, B.mat, .94); F.wq(w.u0, w.u1, w.y1, y1, 0, B.mat, .94); F.reveal(w); F.place(uWinCheap(+(w.u1 - w.u0).toFixed(2), +(w.y1 - w.y0).toFixed(2), rr() < .6 ? 0 : 1, 0), 'alcDetail', (w.u0 + w.u1) / 2, w.y0, 0); STAT.win++; u = w.u1; }
  F.wq(u, len, y0, y1, 0, B.mat, .94);
  gableFill(F);
  // a plain cornice on top
  cornice(F);
}

// ---------------------------------------------------------------- odds and ends on the walls
function nearestStreetName(x, z) { let best = 1e9, name = null; for (const w of LAY.ways) { if (!w.name) continue; for (let i = 0; i < w.pts.length - 1; i++) { const [d] = segDist(x, z, w.pts[i][0], w.pts[i][1], w.pts[i + 1][0], w.pts[i + 1][1]); if (d < best) { best = d; name = w.name; } } } return name; }
function uAC() { return unit('ac', u => { u.box(-.38, .38, 0, .52, 0, .3, col(0xd9d6cf)); u.q([[-.3, .06, .302], [.3, .06, .302], [.3, .3, .302], [-.3, .3, .302]], col(0x666a6c), [0, 0, 1]); u.cyl(.22, .18, .31, .12, .12, .02, 6, PAL.ironL, false); u.box(-.34, .34, -.04, 0, .02, .1, PAL.ironL, false, false); }); }
function uDish() { return unit('dish', u => { u.box(-.015, .015, .0, .12, 0, .22, PAL.ironL, false, false); u.cyl(0, .12, .32, .01, .3, .05, 8, col(0xe2e4e6), false); u.box(-.01, .01, .1, .14, .3, .46, PAL.iron, false, false); }); }
function uTilePanel() { return unit('tp', u => { const uv = tileUV(5, .1, .1, .8, .8); u.q([[-.22, 0, .03], [.22, 0, .03], [.22, .6, .03], [-.22, .6, .03]], [1, 1, 1], [0, 0, 1], uv); u.box(-.25, -.22, -.03, .63, .0, .05, PAL.woodL, false, true); u.box(.22, .25, -.03, .63, .0, .05, PAL.woodL, false, true); u.box(-.25, .25, .6, .63, .0, .05, PAL.woodL, false, true); u.box(-.25, .25, -.03, 0, .0, .05, PAL.woodL, false, true); }); }
function uMeter() { return unit('mt', u => { u.box(-.17, .17, 0, .4, 0, .12, col(0xb8b4aa)); u.box(-.15, .15, .22, .38, .12, .125, PAL.glass, false, false); }); }
function uWallPot(c) { return unit(`wp|${c}`, u => { const gl = c ? col(0x2a5a9a) : col(0xb4623e), fl = FLOWERS[c % FLOWERS.length]; u.box(-.012, .012, .0, .1, 0, .09, PAL.iron, false, false); u.cyl(0, .02, .13, .075, .1, .16, 6, gl, false); u.sph(0, .22, .13, .14, .1, .14, PAL.leaf, 1, 5); for (let i = 0; i < 3; i++) u.sph(-.07 + i * .07, .27, .13 + (i % 2) * .04, .04, .035, .04, fl, 1, 4); u.sph(0, .08, .13, .05, .22, .05, PAL.leaf2, 1, 4); }); }
function uVine(w, h, seed) { return unit(`vine|${w}|${h}|${seed}`, u => { const r = rnd(seed); const n = Math.round(w * h * 5); for (let i = 0; i < n; i++) { const x = (r() - .5) * w, y = r() * h * (.55 + .45 * r()), c = r() < .5 ? PAL.leaf : PAL.leaf2; u.sph(x, y, .06, .09 + r() * .06, .08 + r() * .05, .05, c, 1, 4); } for (let i = 0; i < n / 5; i++) u.sph((r() - .5) * w, r() * h, .1, .03, .03, .03, r() < .6 ? col(0xf3e8d8) : col(0xd9304a), 1, 4); }); }
function wallDecor(F, rr) {
  if (LOW) return;
  const B = F.B, len = F.len, L = B.L; if (len < 1.5) return;
  const free = (u0, u1, y0, y1) => !F.rects.some(o => o.u0 - .22 < u1 && o.u1 + .22 > u0 && o.y0 - .22 < y1 && o.y1 + .22 > y0);
  const find = (w, h, ya, yb) => { for (let k = 0; k < 10; k++) { const u = .3 + rr() * Math.max(0, len - .6 - w), y = ya + rr() * Math.max(0, yb - ya - h); if (free(u, u + w, y, y + h)) return [u + w / 2, y]; } return null; };
  const g = F.g(len / 2), mid = F.P(len / 2, 0, 0);
  // street-name plaque near a corner (azulejo)
  if (rr() < .55) { const nm = nearestStreetName(mid[0], mid[2]); if (nm && SIGNS.has('p:' + nm)) { const u = len > 3 ? (rr() < .5 ? .55 : len - .55) : len / 2, y = F.g(u) + 2.45; if (free(u - .3, u + .3, y, y + .3)) signOn(F, 'p:' + nm, u, y, .5, .035); } }
  if (L >= 2 && rr() < .22) { const p = find(.8, .55, F.floor(1) + .3, F.floor(2) - .3); if (p) F.place(uAC(), 'alcDetail', p[0], p[1], 0); }
  if (L >= 3 && rr() < .12) { const p = find(.6, .5, F.floor(2) + .8, B.top - .8); if (p) F.place(uDish(), 'alcDetail', p[0], p[1], 0); }
  if (rr() < .14) { const p = find(.5, .65, g + 1.6, F.floor(1) - .6); if (p) F.place(uTilePanel(), 'alcDetail', p[0], p[1], 0); }
  if (rr() < .35) { const p = find(.36, .4, g + 1.0, g + 1.9); if (p) F.place(uMeter(), 'alcDetail', p[0], p[1], 0); }
  if (rr() < .4 && len > 3) { // cables along the wall
    const y = F.floor(1) + 2.7 + rr() * .3, n = Math.max(2, Math.round(len / 1.5)); let prev = F.P(.2, y, .05);
    for (let k = 1; k <= n; k++) { const u = .2 + (len - .4) * k / n, yy = y - Math.sin(Math.PI * k / n) * .12; const q = F.P(u, yy, .05); BLD.line(prev, q, .005, 'alcDetail'); prev = q; }
  }
  // blue pots on the wall and a climbing vine
  if (L >= 2 && len > 2.6 && rr() < .18) { const n = 3 + Math.floor(rr() * 4), y = F.floor(1) + 1.9 + rr() * .3, ub = .5 + rr() * Math.max(0, len - n * .5 - 1), c = rr() < .6 ? 1 : 0; for (let k = 0; k < n; k++) { const u = ub + k * .5; if (u > len - .3) break; if (free(u - .15, u + .15, y, y + .3)) F.place(uWallPot(c + (k % 3 === 2 ? 2 : 0)), 'alcDetail', u, y, .0); } }
  if (rr() < .1) { const w = 1.0 + rr() * 1.2, h = 2.4 + rr() * 2.0, p = find(w, h, g + .1, g + 5.5); if (p) { F.place(uVine(+w.toFixed(1), +h.toFixed(1), Math.floor(rr() * 6)), 'alcDetail', p[0], g, 0); } }
}

// ---------------------------------------------------------------- ground storey: doors, barred windows, bazaars, tea houses, bars
const tileUV = (i, du = 0, dv = 0, sw = 1, sh = 1) => { const x = (i % 4) / 4, y = 1 - (Math.floor(i / 4) + 1) / 4; return [[x + du / 4, y + dv / 4], [x + (du + sw) / 4, y + dv / 4], [x + (du + sw) / 4, y + (dv + sh) / 4], [x + du / 4, y + (dv + sh) / 4]]; };
function interior(F, op, depth, rr, theme) {
  const { u0, u1, y0 } = op, yt = op.arch ? op.arch.ys + op.arch.r * 1.15 : op.y1, w = -depth, P = (u, y, ww) => F.P(u, y, ww), uv4 = [[0, 0], [1, 0], [1, 1], [0, 1]];
  const base = theme === 'bar' ? [.36, .2, .085] : theme === 'tea' ? [.34, .17, .07] : [.38, .24, .11];
  const top = yt + .35, H = top - y0;
  // dark warm room: floor, ceiling with beams, side walls with a vertical falloff
  Q('alcGlow', [P(u0, y0, 0), P(u1, y0, 0), P(u1, y0, w), P(u0, y0, w)], uv4, [mulc(base, .55), mulc(base, .55), mulc(base, .22), mulc(base, .22)], [0, 1, 0]);
  Q('alcGlow', [P(u0, top, 0), P(u1, top, 0), P(u1, top, w), P(u0, top, w)], uv4, [mulc(base, .6), mulc(base, .6), mulc(base, .3), mulc(base, .3)], [0, -1, 0]);
  const stiles = theme === 'bar' ? [6, 12, 7] : theme === 'tea' ? [9, 8, 0, 5] : [3, 14, 2, 11, 0, 1, 10, 13];
  for (const [u, sg] of [[u0, 1], [u1, -1]]) {
    const t = stiles[Math.floor(rr() * stiles.length)];
    Q('alcGlowTex', [P(u, y0, 0), P(u, y0, w), P(u, top, w), P(u, top, 0)], tileUV(t, rr() * .3, rr() * .3, .7, .7), [mulc(base, 1.0), mulc(base, .32), mulc(base, .4), mulc(base, 1.15)], [F.tx * sg, 0, F.tz * sg]);
  }
  // a rug on the floor
  { const rt = [0, 1, 10, 8][Math.floor(rr() * 4)], ru0 = u0 + .15, ru1 = u1 - .15; if (ru1 > ru0 + .3) Q('alcGlowTex', [P(ru0, y0 + .01, -.2), P(ru1, y0 + .01, -.2), P(ru1, y0 + .01, w * .8), P(ru0, y0 + .01, w * .8)], tileUV(rt, 0, 0, 1, 1), [mulc(base, 1.25), mulc(base, 1.25), mulc(base, .6), mulc(base, .6)], [0, 1, 0]); }
  for (let b = 1; b <= 2; b++) F.fb('alcDetail', u0, u1, top - .16, top, -b * depth / 3 - .06, -b * depth / 3 + .06, mulc(PAL.woodD, 1), false);
  // the back wall: shelves with merchandise
  const tiles = theme === 'bar' ? [12, 6, 12, 7] : theme === 'tea' ? [9, 8, 0, 14, 5] : [3, 14, 2, 11, 4, 1, 10, 13, 8, 0];
  const n = Math.max(1, Math.round((u1 - u0) / .8)), wi = (u1 - u0) / n;
  for (let i = 0; i < n; i++) { const t = tiles[Math.floor(rr() * tiles.length)]; Q('alcGlowTex', [P(u0 + wi * i, y0, w), P(u0 + wi * (i + 1), y0, w), P(u0 + wi * (i + 1), top, w), P(u0 + wi * i, top, w)], tileUV(t, rr() * .35, rr() * .35, .6, .6), mulc(base, 1.15), F.n3); }
  if (theme === 'bar') { // bottles on lit shelves
    for (let r = 0; r < 3; r++) { const y = y0 + 1.05 + r * .45; F.fb('alcDetail', u0 + .1, u1 - .1, y, y + .03, w, w + .22, PAL.woodL, false); for (let k = 0; k < Math.floor((u1 - u0 - .3) / .1); k++) { const c = [col(0x2a6a3a), col(0xb87a1a), col(0x6a2a2a), col(0x9ab0b8)][Math.floor(rr() * 4)]; F.fb('alcGlow', u0 + .15 + k * .1, u0 + .2 + k * .1, y + .03, y + .03 + .2 + rr() * .08, w + .06, w + .12, mulc(c, 1.2), false); } }
  }
  if (theme === 'tea') { // low benches with cushions along the side walls and a brass table
    const cs = [col(0xb8402e), col(0x2c5a8a), col(0xd8a22a), col(0x3a7a4a), col(0x8a3a6a)];
    for (const [u, sg] of [[u0 + .02, 1], [u1 - .02, -1]]) { const x0 = sg > 0 ? u : u - .4, x1 = sg > 0 ? u + .4 : u; F.fb('alcDetail', x0, x1, y0, y0 + .38, -depth * .85, -.35, PAL.woodL, false); for (let k = 0; k < 3; k++) F.fb('alcDetail', x0 + .02, x1 - .02, y0 + .38, y0 + .5, -depth * .85 + k * (depth * .85 - .35) / 3 + .03, -depth * .85 + (k + 1) * (depth * .85 - .35) / 3 - .03, cs[Math.floor(rr() * cs.length)], false); }
    addU(uTable(0), 'alcDetail', F.P((u0 + u1) / 2, y0, -depth * .5), 0);
  }
  // the counter / table silhouette and hanging lamps
  if (theme !== 'tea') F.fb('alcDetail', u0 + .05, u1 - .05, y0, y0 + .95, w + .85, w + 1.25, mulc(PAL.wood, .9));
  for (let k = 0; k < Math.max(1, Math.round((u1 - u0) / 1.2)); k++) { const uu = u0 + (u1 - u0) * (k + .5) / Math.max(1, Math.round((u1 - u0) / 1.2)); const p = F.P(uu, top - .5, -depth * .45); addU(unit('lamp', u => { u.sph(0, 0, 0, .12, .14, .12, [1.5, 1.05, .55], 3, 8); u.box(-.004, .004, .15, .5, -.004, .004, PAL.iron); }), 'alcGlow', p, 0); }
}
// timber frame around a rectangular shop opening
function shopFrame(F, op, c) {
  const { u0, u1, y0, y1 } = op, t = .1;
  F.fb('alcWood', u0 - t, u0, y0 - .02, y1 + t, -.02, .08, c); F.fb('alcWood', u1, u1 + t, y0 - .02, y1 + t, -.02, .08, c); F.fb('alcWood', u0 - t, u1 + t, y1, y1 + t, -.02, .1, c);
  F.fb('alcStone', u0 - t, u1 + t, y0 - .2, y0 - .02, -.0, .22, PAL.stoneD);
}
const AWN = [col(0xb04a3a), col(0x9a7a50), col(0x8a8a4a), col(0xe0a83a), col(0x3a6aa0), col(0x4a8a5a), col(0xc65a30), col(0xefe2bc)];
function awning(F, u0, u1, ytop, rr, proj = 1.15, drop = .5) {
  const stripe = rr() < .35, ci = Math.floor(rr() * AWN.length), c = stripe ? [1, 1, 1] : AWN[ci], tile = stripe ? (rr() < .5 ? 11 : 2) : 15;
  const yf = ytop - drop, P = (u, y, w) => F.P(u, y, w), uv = tileUV(tile, 0, 0, 1, 1);
  Q('alcGoods', [P(u0, ytop, 0), P(u1, ytop, 0), P(u1, yf, proj), P(u0, yf, proj)], uv, c, [0, 1, .4]);
  Q('alcGoods', [P(u0, yf, proj), P(u1, yf, proj), P(u1, yf - .24, proj + .03), P(u0, yf - .24, proj + .03)], uv, mulc(c, .92), F.n3);
  Q('alcGoods', [P(u0, ytop, 0), P(u0, yf, proj), P(u0, yf - .0, proj), P(u0, ytop - .02, 0)], uv, c, [-F.tx, 0, -F.tz]);
  return { yf, proj };
}
function signOn(F, key, u, y, wS, w = .04) {
  const r = signRect(key), asp = (r[3] - r[1]) * 2048 / ((r[2] - r[0]) * 2048), hS = wS * asp, P = (uu, yy, ww) => F.P(uu, yy, ww);
  Q('alcSign', [P(u - wS / 2, y, w), P(u + wS / 2, y, w), P(u + wS / 2, y + hS, w), P(u - wS / 2, y + hS, w)], [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]], [1, 1, 1], F.n3);
  F.fb('alcDetail', u - wS / 2 - .03, u + wS / 2 + .03, y - .03, y + hS + .03, 0, .03, PAL.woodD, false);
  return hS;
}
function flagSign(F, key, u, y, rr) {
  const r = signRect(key), rot = F.rot;
  const g = unit(`flag|${key}`, un => {
    const c = PAL.iron; un.box(-.012, .012, 0, .02, 0, .85, c); un.box(-.012, .012, -.02, 0, .0, .8, c); un.box(-.01, .01, -.5, 0, .72, .74, c);
    un.q([[0, -.9, .1], [0, -.9, .72], [0, -.05, .72], [0, -.05, .1]], [1, 1, 1], [1, 0, 0], [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]]);
    un.q([[0, -.9, .1], [0, -.9, .72], [0, -.05, .72], [0, -.05, .1]], [1, 1, 1], [-1, 0, 0], [[r[2], r[1]], [r[0], r[1]], [r[0], r[3]], [r[2], r[3]]]);
  });
  const p = F.P(u, y, 0); addU(g, 'alcSign', p, rot);
}
let SIGN_KEYS = [];
function groundBay(F, k, cx, bw, type, poi, rr, tw, E1) {
  const B = F.B, g = F.g(cx), ops = [], maxH = E1 - g - .45;
  if (type === 'win' || bw < 1.7 && type !== 'door') {
    const w = Math.min(bw - .9, 1.0 + (rr() < .3 ? .1 : 0)); if (w < .5) return ops;
    const op = windowOp(F, cx, g + 1.0 + rr() * .15, w, Math.min(1.4, maxH - 1.1)); if (op.y1 - op.y0 < .7) return ops; ops.push(op);
    placeWindow(F, op, rr, { reja: rr() < .35 ? 2 : 1, potP: .3 }); return ops;
  }
  if (type === 'door' || type === 'hotel') {
    const w = Math.min(bw - .8, 1.05 + .2 * rr()), h = Math.min(2.3, maxH), op = rectOp(cx - w / 2, cx + w / 2, g + .13, g + .13 + h); op.nopl = true; ops.push(op);
    const sk = Math.floor(rr() * 3), wv = Math.floor(rr() * 4);
    F.place(uDoorSurround(+w.toFixed(2), +h.toFixed(2), sk), 'alcDetail', cx, op.y0, 0); F.place(uDoorLeaf(+w.toFixed(2), +h.toFixed(2), wv), 'alcDetail', cx, op.y0, 0);
    if (rr() < .5) { F.place(uLanternWall(), 'alcDetail', cx + w / 2 + .45, op.y0 + 1.75, 0); F.place(uLanternWallGlass(), 'alcGlow', cx + w / 2 + .45, op.y0 + 1.75, 0); LAMPS.push([...F.P(cx + w / 2 + .45, op.y0 + 2.2, .45), .8]); }
    if (rr() < .5) F.place(uFlowerPot(Math.floor(rr() * 6)), 'alcDetail', cx - w / 2 - .4, g, .25);
    if (type === 'hotel' && poi) { flagSign(F, 'flag0', cx + w / 2 + .5, op.y1 + .9, rr); }
    return ops;
  }
  // shop-like fronts
  const theme = type === 'bar' ? 'bar' : type === 'tea' ? 'tea' : type === 'rest' ? 'tea' : 'bazaar';
  let w = Math.min(bw - .7, type === 'bar' ? 2.9 : type === 'shop' ? 2.1 + rr() * 1.2 : 1.35);
  w = Math.max(w, 1.3);
  const arched = type === 'tea' || type === 'rest', h = Math.min(arched ? 2.1 : 2.45, maxH);
  if (maxH < 1.9) return groundBay(F, k, cx, bw, 'door', null, rr, tw, E1);
  const y0 = g + .1; let op;
  if (arched) { op = arcOp(cx - w / 2, cx + w / 2, y0, y0 + h - w / 2, 0); } else op = rectOp(cx - w / 2, cx + w / 2, y0, y0 + h);
  op.nopl = true; ops.push(op); STAT.shops++;
  interior(F, op, 1.6 + rr(), rr, theme);
  if (!arched) shopFrame(F, op, rr() < .5 ? PAL.wood : PAL.woodL);
  else { // brick-and-stone ring and carved door leaves
    const r = w / 2, n = 10, ring = [];
    for (let i = 0; i <= n; i++) { const a = Math.PI * i / n, uu = op.arch.cx - Math.cos(a) * r, yy = op.arch.ys + Math.sin(a) * r * 1.0; ring.push([uu, yy, a]); }
    for (let i = 0; i < n; i++) { const [ua, ya] = ring[i], [ub, yb] = ring[i + 1]; const ra = r + .22, ca = Math.cos(ring[i][2]), sa = Math.sin(ring[i][2]), cb = Math.cos(ring[i + 1][2]), sb = Math.sin(ring[i + 1][2]); const outer = (c, s) => [op.arch.cx - c * ra, op.arch.ys + s * ra];
      const oa = outer(ca, sa), ob = outer(cb, sb), cc = (i % 2) ? col(0xcdb892) : col(0xa5754f);
      Q('alcBrick', [F.P(ua, ya, .0), F.P(ub, yb, .0), F.P(ob[0], ob[1], .0), F.P(oa[0], oa[1], .0)].map((p, ii) => ii < 2 ? F.P(ring[i + ii][0], ring[i + ii][1], .045) : F.P(ii === 2 ? ob[0] : oa[0], ii === 2 ? ob[1] : oa[1], .045)), [[0, 0], [.3, 0], [.3, .6], [0, .6]], cc, F.n3); }
    F.fb('alcStone', op.u0 - .22, op.u0, y0 - .1, op.arch.ys, -.0, .08, col(0xb9a78a), false); F.fb('alcStone', op.u1, op.u1 + .22, y0 - .1, op.arch.ys, -.0, .08, col(0xb9a78a), false);
    // wooden leaves (open) inside the arch, carved panels via the goods tile of dark timber
    const lw = (op.u1 - op.u0) / 2 - .02, hh = (op.arch.ys - y0) - .05;
    F.fb('alcWood', op.u0 + .01, op.u0 + .06, y0, y0 + hh, -RD + .02, -RD + .09, PAL.wood, false);
    F.fb('alcWood', op.u1 - .06, op.u1 - .01, y0, y0 + hh, -RD + .02, -RD + .09, PAL.wood, false);
    F.fb('alcStone', op.u0 - .22, op.u1 + .22, y0 - .2, y0 - .02, 0, .2, PAL.stoneD);
  }
  // awning + sign
  const ytop = (arched ? op.arch.ys + w / 2 * 1.15 : op.y1) + .38;
  const okAw = !arched && ytop + .1 < E1 + .2;
  let signY = ytop + .1;
  if (!arched) { const fr = laneFree(F, cx), proj = clamp(fr * .3, .5, 1.25); const aw = awning(F, op.u0 - .25, op.u1 + .25, Math.min(ytop - .05, E1 - .15), rr, proj, .5); signY = Math.min(ytop + .02, E1 - .02); }
  const names = poi && poi.name ? 'n:' + poi.name : null;
  const key = names && SIGNS.has(names) ? names : 't:' + (type === 'bar' ? ['BAR', 'TAPAS', 'CAFETERÍA'][Math.floor(rr() * 3)] : type === 'tea' ? 'TETERÍA' : ['BAZAR', 'ARTESANÍA', 'SOUVENIRS', 'CERÁMICAS', 'ESPECIAS', 'LÁMPARAS', 'CUERO', 'JOYERÍA', 'ALFOMBRAS'][Math.floor(rr() * 9)]);
  const sw = Math.min(bw - .3, 1.9);
  if (!arched) signOn(F, key, cx, Math.min(signY, E1 - .5), sw);
  else { signOn(F, key, cx, op.arch.ys + w / 2 * 1.15 + .5, Math.min(sw, 1.6)); flagSign(F, theme === 'tea' ? 'flag0' : 'flag1', op.u1 + .55, op.y1 + .45, rr); }
  shopProps(F, op, type, theme, rr, poi);
  return ops;
}

// ---------------------------------------------------------------- merchandise and street furniture
const LANT_COL = [[.95, .3, .08], [.95, .65, .14], [.1, .5, .46], [.85, .12, .2], [.16, .28, .8], [1.0, .6, .22], [.12, .5, .16]];
function uSmallLantern(ci, size) {
  // a Moroccan lantern: six panels of coloured-glass mosaic (lit), iron cap and base are separate
  return unit(`sl|${ci}|${size}`, u => {
    const r = .075 * size, h = .2 * size, c = LANT_COL[ci % LANT_COL.length], n = 6, uv0 = tileUV(9, (ci % 3) * .25, .1, .5, .6);
    for (let i = 0; i < n; i++) {
      const a0 = i / n * Math.PI * 2, a1 = (i + 1) / n * Math.PI * 2, m = (a0 + a1) / 2;
      u.q([[Math.cos(a0) * r * .75, 0, Math.sin(a0) * r * .75], [Math.cos(a1) * r * .75, 0, Math.sin(a1) * r * .75], [Math.cos(a1) * r, h, Math.sin(a1) * r], [Math.cos(a0) * r, h, Math.sin(a0) * r]], mixc(c, [1, 1, 1], .35), [Math.cos(m), 0, Math.sin(m)], uv0);
    }
  });
}
function uSmallLanternFrame(ci, size) {
  return unit(`slf|${ci}|${size}`, u => { const r = .075 * size, h = .2 * size; u.cyl(0, h, 0, r * 1.1, .01, .07 * size, 5, PAL.iron, false); u.box(-.004, .004, h + .06 * size, h + .22 * size, -.004, .004, PAL.iron, false, false); });
}
function uRug(tile, w, h, rot) {
  return unit(`rug|${tile}|${w}|${h}`, u => { const uv = tileUV(tile); u.q([[-w / 2, -h, 0], [w / 2, -h, 0], [w / 2, 0, 0], [-w / 2, 0, 0]], [1, 1, 1], [0, 0, 1], uv); u.q([[-w / 2, -h, 0], [w / 2, -h, 0], [w / 2, 0, 0], [-w / 2, 0, 0]], [.8, .8, .8], [0, 0, -1], uv.map(p => p)); u.box(-w / 2 - .02, w / 2 + .02, .0, .03, -.02, .03, PAL.woodD); });
}
function uBagRow(n, ci) {
  return unit(`bag|${n}|${ci}`, u => {
    const cols = [col(0xb5703a), col(0x7a3b22), col(0x3a2a20), col(0xc9914a), col(0xa83a2e), col(0x3a6a7a), col(0xd1a23c), col(0x8a5a2a)], r = rnd(ci * 13 + n);
    u.box(-n * .16 - .1, n * .16 + .1, -.012, .012, -.012, .012, PAL.iron, false, false);
    for (let i = 0; i < n; i++) {
      const x = (i - (n - 1) / 2) * .3 + (r() - .5) * .04, kind = Math.floor(r() * 3), c = cols[Math.floor(r() * cols.length)];
      const bw = kind === 2 ? .2 : .24 + r() * .06, bh = kind === 2 ? .36 : .2 + r() * .08, bd = kind === 2 ? .12 : .08, top = -.15;
      u.q([[x - .003, top, 0], [x + .003, top, 0], [x + .003, 0, 0], [x - .003, 0, 0]], PAL.iron, [0, 0, 1]);
      u.box(x - bw / 2, x + bw / 2, top - bh, top, -bd / 2, bd / 2, c, true, true);
      u.box(x - bw / 2 - .005, x + bw / 2 + .005, top - bh * .5, top, bd / 2, bd / 2 + .012, mulc(c, .78), false, true); // flap
      u.box(x - .012, x + .012, top - bh * .55, top - bh * .4, bd / 2 + .012, bd / 2 + .02, col(0xc9a45a), false, false);
      u.box(x - bw * .38, x + bw * .38, top, top + .014, -bd * .3, bd * .3, mulc(c, .6), false, true);
    }
  });
}
function uBasket(ci) {
  return unit(`bk|${ci}`, u => { const c = ci % 2 ? col(0xa87a45) : col(0x8a5a30); u.cyl(0, 0, 0, .2, .26, .32, 8, c, false); const items = [col(0xd83a2e), col(0xe8b020), col(0x3a8a4a), col(0xb36a2a), col(0x7a2a5a)]; for (let i = 0; i < 6; i++) { const a = i * 1.1; u.sph(Math.cos(a) * .1, .32, Math.sin(a) * .1, .07, .05, .07, items[(i + ci) % items.length], 1, 5); } });
}
function uPotteryStand(ci) {
  return unit(`ps|${ci}`, u => { const cs = [col(0x2a5a9a), col(0xd9d0bc), col(0xb85a2a), col(0x3a7a5a), col(0xd7a62a)], c = PAL.woodL;
    u.box(-.45, .45, .42, .44, -.2, .2, c, false, true); u.box(-.45, .45, .84, .86, -.2, .2, c, false, true);
    for (const x of [-.42, .42]) for (const z of [-.18, .18]) u.box(x - .015, x + .015, 0, .84, z - .015, z + .015, c, false, false);
    for (let k = 0; k < 2; k++) for (let i = 0; i < 5; i++) u.sph(-.32 + i * .16, .44 + k * .42 + .06, (i % 2 ? .05 : -.05), .06, .06, .06, cs[(i + k + ci) % cs.length], 1, 5); });
}
function uTable(kind) {
  return unit(`tb|${kind}`, u => { const c = kind === 0 ? col(0x6a4a2a) : col(0x9a9a9a); u.cyl(0, .72, 0, .33, .33, .03, 10, c); u.cyl(0, 0, 0, .04, .04, .72, 5, PAL.iron); u.cyl(0, 0, 0, .22, .22, .02, 8, PAL.iron); u.cyl(.07, .75, .05, .035, .03, .09, 6, col(0xe8ecee)); });
}
function uChair(c) {
  return unit(`ch|${c}`, u => { const cc = [col(0x5a3a22), col(0x2c2c2e), col(0x8a2a24), col(0x3a5a3a)][c % 4]; u.box(-.2, .2, .44, .47, -.2, .2, cc); for (const [x, z] of [[-.18, -.18], [.18, -.18], [-.18, .18], [.18, .18]]) u.box(x - .015, x + .015, 0, .44, z - .015, z + .015, cc, false, false); u.box(-.2, .2, .47, .92, -.2, -.17, cc); });
}
function uChalk(key) { const r = signRect(key); return unit(`chalk|${key}`, u => { const w = .42, h = .64; u.q([[-w / 2, 0, .13], [w / 2, 0, .13], [w / 2, h, .0], [-w / 2, h, .0]], [1, 1, 1], [0, .3, 1], [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]]); u.q([[-w / 2, 0, -.13], [w / 2, 0, -.13], [w / 2, h, 0], [-w / 2, h, 0]], [1, 1, 1], [0, .3, -1], [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]]); u.box(-w / 2 - .01, -w / 2 + .01, 0, .03, -.14, .14, PAL.wood); u.box(w / 2 - .01, w / 2 + .01, 0, .03, -.14, .14, PAL.wood); }); }
function uCushionBench(ci) {
  return unit(`cb|${ci}`, u => { u.box(-.7, .7, 0, .4, 0, .38, PAL.woodL); const cs = [col(0xb8402e), col(0x2c5a8a), col(0xd8a22a), col(0x3a7a4a), col(0x8a3a6a)]; for (let i = 0; i < 4; i++) u.box(-.64 + i * .33, -.4 + i * .33, .4, .5, .03, .35, cs[(i + ci) % cs.length]); });
}
function uCat(ci) {
  return unit(`cat|${ci}`, u => { const c = [col(0x2a2624), col(0xc98a3a), col(0xb8b2a8), col(0x5a4a3a)][ci % 4]; u.sph(0, .13, 0, .1, .13, .16, c, 2, 6); u.sph(0, .27, .13, .075, .07, .07, c, 2, 6); u.tri([[-.06, .31, .13], [-.03, .38, .12], [-.01, .32, .13]], c, [0, 0, 1]); u.tri([[.06, .31, .13], [.03, .38, .12], [.01, .32, .13]], c, [0, 0, 1]); u.sph(.04, .04, -.2, .03, .03, .15, c, 1, 5); });
}
// hanging merchandise and furniture at a shop-like opening
function shopProps(F, op, type, theme, rr, poi) {
  const { u0, u1, y0 } = op, w = u1 - u0, cx = (u0 + u1) / 2, g = F.g(cx);
  const free = laneFree(F, cx); // metres of free ground in front of the facade
  if (theme === 'bazaar') {
    // rugs and cloth hanging on either side
    const tiles = [0, 1, 10, 8, 2, 13, 14, 4, 11];
    for (const side of [-1, 1]) {
      const room = side < 0 ? u0 : F.len - u1; if (room < .9 && rr() < .6) continue;
      const rw = (free < 2.6 ? .55 : .75) + rr() * .4, rh = 1.1 + rr() * .9, uu = side < 0 ? u0 - .08 - rw / 2 : u1 + .08 + rw / 2; if (uu - rw / 2 < .02 || uu + rw / 2 > F.len - .02) continue;
      F.place(uRug(tiles[Math.floor(rr() * tiles.length)], +rw.toFixed(2), +rh.toFixed(2)), 'alcGoods', uu, g + 2.55, .06);
    }
    if (!LOW && rr() < (free < 2.6 ? .25 : .75)) { const n = 3 + Math.floor(rr() * 3), ci = Math.floor(rr() * 8); const y = op.y1 - .1, ww = clamp(free * .16, .3, .55); F.place(uBagRow(n, ci), 'alcDetail', cx, y, ww); if (free > 2.6) F.place(uBagRow(n, ci + 1), 'alcDetail', cx, y - .5, ww); }
    // lanterns hanging from the awning
    const nl = LOW || free < 2.6 ? 2 : 3 + Math.floor(rr() * 3);
    for (let i = 0; i < nl; i++) { const ci = Math.floor(rr() * LANT_COL.length), sz = .65 + rr() * .45, uu = u0 + .1 + (w - .2) * (i + .5) / nl, y = op.y1 - .12 - (i % 3) * .26, ww = clamp(free * .12, .2, .45) + (i % 2) * .1; F.place(uSmallLantern(ci, +sz.toFixed(1)), 'alcGlowTex', uu, y - .2 * sz, ww); F.place(uSmallLanternFrame(ci, +sz.toFixed(1)), 'alcDetail', uu, y - .2 * sz, ww); }
    if (free > 2.6) { if (rr() < .7) F.place(uPotteryStand(Math.floor(rr() * 5)), 'alcDetail', u1 + .5 > F.len - .5 ? u0 - .6 : u1 + .55, g, .45); if (rr() < .8) F.place(uBasket(Math.floor(rr() * 4)), 'alcDetail', u0 + .35 + rr() * (w - .7), g + .1, .45 + rr() * .3); }
  } else if (theme === 'tea') {
    if (free > 2.2 && rr() < .7) F.place(uCushionBench(Math.floor(rr() * 5)), 'alcDetail', op.u1 + .9 > F.len ? op.u0 - .9 : op.u1 + .9, g, .02);
    for (const sx of [-1, 1]) { const uu = sx < 0 ? op.u0 - .4 : op.u1 + .4; if (uu < .3 || uu > F.len - .3) continue; const y = g + 2.3; F.place(uHangLanternFrame(0, .6), 'alcDetail', uu, y, .35); F.place(uHangLanternGlass(0, .6), 'alcGlow', uu, y, .35); LAMPS.push([...F.P(uu, y + .3, .35), 1]); }
    if (free > 2.8 && rr() < .6) { const uu = cx - w / 2 - .1; F.place(uTable(0), 'alcDetail', cx + (rr() - .5) * .6, g, 1.1); }
    if (rr() < .5) F.place(uChalk('chalk2'), 'alcSign', cx - w / 2 - .6 < .3 ? cx + w / 2 + .6 : cx - w / 2 - .6, g, .4, 0);
  } else if (theme === 'bar') {
    if (free > 2.3) { const nt = free > 3.6 ? 2 : 1; for (let i = 0; i < nt; i++) { const uu = cx + (i - (nt - 1) / 2) * 1.5, ww = .95 + (i % 2) * .15; F.place(uTable(rr() < .5 ? 0 : 1), 'alcDetail', uu, g, ww + .4); BLD.nav.box(...F.P(uu, 0, ww + .4).filter((_, i2) => i2 !== 1), .7, .7, g - 1, g + .9, 0); for (const [a, b] of [[-.5, .0], [.5, .1], [0, 1.0]]) F.place(uChair(Math.floor(rr() * 4)), 'alcDetail', uu + a, g, ww + .4 + b, (a > 0 ? -1 : 1) * 1.57 * (b < .5 ? 1 : 0) + (b > .5 ? Math.PI : 0)); } }
    if (rr() < .7) F.place(uChalk(rr() < .5 ? 'chalk0' : 'chalk1'), 'alcSign', cx + w / 2 + .5 > F.len - .3 ? cx - w / 2 - .5 : cx + w / 2 + .5, g, .5, 0);
    const y = op.y1 + .1; F.place(uHangLanternFrame(1, .5), 'alcDetail', u1 + .35 > F.len ? u0 - .35 : u1 + .35, g + 2.25, .3); F.place(uHangLanternGlass(1, .5), 'alcGlow', u1 + .35 > F.len ? u0 - .35 : u1 + .35, g + 2.25, .3);
  }
}
function uHangLanternFrame(kind, s) { return unit(`hlf|${kind}|${s}`, u => { const c = PAL.iron, n = 8, r0 = .26 * s, r1 = .29 * s, h = .85 * s; u.cyl(0, 0, 0, r0 * .5, r0 * .5, .12 * s, n, c); u.cyl(0, .12 * s, 0, r0, r0, .04 * s, n, c); u.cyl(0, h - .08 * s, 0, r1, r1, .05 * s, n, c); u.cyl(0, h - .03 * s, 0, r1 * .95, .05 * s, .22 * s, n, c, true); for (let i = 0; i < n; i++) { const a = (i + .5) / n * Math.PI * 2, cx = Math.cos(a) * (r0 + r1) / 2, cz = Math.sin(a) * (r0 + r1) / 2; u.box(cx - .008, cx + .008, .12 * s, h - .05 * s, cz - .008, cz + .008, c); } u.box(-.005, .005, h + .12 * s, h + .9, -.005, .005, c); }); }
function uHangLanternGlass(kind, s) { return unit(`hlg|${kind}|${s}`, u => { const n = 8, r0 = .26 * s, r1 = .29 * s, h = .85 * s; u.cyl(0, .13 * s, 0, r0 * .95, r1 * .95, h - .22 * s, n, kind === 0 ? [1.5, .95, .52] : [1.3, 1.05, .75], false); }); }
// free ground in front of a facade at u (metres until a building, max 8)
function laneFree(F, u) { const p = F.P(u, 0, 0); let d = .4; for (; d < 8; d += .3) if (occupied(p[0] + F.nx * d, p[2] + F.nz * d)) break; return d; }

// ---------------------------------------------------------------- over the lanes: wires with bulbs, hung lanterns, laundry
const LANE_DECK = new Set(['Calle Calderería Nueva', 'Calle Calderería Vieja', 'Calle Elvira', 'Cuesta de Marañas', 'Calle Hospital Corpus Christi', 'Calle Hospital Peregrinos', 'Calle Imprenta', 'Calle Cetti Meriem', 'Callejuela del Señor', 'Calle Correo Viejo', 'Callejón del Gato', 'Calle Almireceros', 'Calle Pan']);
function uBulb() { return unit('bulb', u => u.sph(0, 0, 0, .055, .07, .055, [1.7, 1.15, .6], 1, 5)); }
// a covered passage ("pasadizo") joining the houses on both sides over a narrow lane
function uScooter(ci) { return unit(`sc|${ci}`, u => { const c = [col(0xb8342a), col(0x2a4a7a), col(0xd8d4c8), col(0x2c2c2e)][ci % 4]; for (const z of [-.45, .5]) u.cyl(0, .17, z, .17, .17, .09, 8, PAL.black, true); u.box(-.1, .1, .22, .5, -.5, .1, c, false, true); u.box(-.1, .1, .38, .5, .1, .55, c, false, true); u.box(-.11, .11, .5, .56, -.3, .15, PAL.black, false, true); u.box(-.012, .012, .5, 1.0, .46, .5, PAL.ironL, false, false); u.box(-.28, .28, .98, 1.02, .44, .52, PAL.ironL, false, false); u.box(-.1, .1, .9, .98, .4, .5, c, false, true); }); }
function bridgeOver(b, s, L, i, rr) {
  const nx = s.nx, nz = s.nz, tx = s.tx, tz = s.tz, wl = s.wl, wr = s.wr, gh = L.hq[i], half = (wr - wl) / 2, cc = (wl + wr) / 2, D = 2.6 + rr() * 1.4;
  const yb = gh + 4.35, rise = .75, ytop = gh + 7.1 + rr() * .6, tint = mulc(PAL[pick(rr, TINTS)], 1), n = 12;
  const pos = (c, t, y) => [s.P[0] + nx * (cc + c) + tx * t, y, s.P[1] + nz * (cc + c) + tz * t];
  const yArch = c => yb + rise * Math.sqrt(Math.max(0, 1 - (c / half) ** 2));
  for (const sgn of [-1, 1]) { // front and back faces
    for (let k = 0; k < n; k++) {
      const c0 = -half + 2 * half * k / n, c1 = -half + 2 * half * (k + 1) / n, y0 = yArch(c0), y1 = yArch(c1), t = sgn * D / 2;
      Q('alcRender', [pos(c0, t, y0), pos(c1, t, y1), pos(c1, t, ytop), pos(c0, t, ytop)], [[c0 / 3, y0 / 3], [c1 / 3, y1 / 3], [c1 / 3, ytop / 3], [c0 / 3, ytop / 3]], tint, [tx * sgn, 0, tz * sgn]);
      // soffit following the arch, with a cross beam now and then
      const t0 = -D / 2, t1 = D / 2;
      if (sgn > 0) Q('alcWood', [pos(c0, t0, y0), pos(c1, t0, y1), pos(c1, t1, y1), pos(c0, t1, y0)], [[0, c0], [0, c1], [1.5, c1], [1.5, c0]], [.8, .8, .8], [0, -1, 0]);
    }
    // a stone rim round the arch edge
    for (let k = 0; k < n; k++) { const c0 = -half + 2 * half * k / n, c1 = -half + 2 * half * (k + 1) / n, y0 = yArch(c0), y1 = yArch(c1), t = sgn * (D / 2 + .03); Q('alcStone', [pos(c0, t, y0 - .0), pos(c1, t, y1 - .0), pos(c1, t, y1 + .2), pos(c0, t, y0 + .2)], [[c0 / 2, 0], [c1 / 2, 0], [c1 / 2, .1], [c0 / 2, .1]], [.9, .88, .84], [tx * sgn, 0, tz * sgn]); }
    // a small window on each face
    const wy = ytop - 1.9, ww = .9; const wc = [pos(0, sgn * D / 2, wy)]; addU(uWinCheap(ww, 1.2, rr() < .6 ? 0 : 1, 1), 'alcDetail', [wc[0][0], wy, wc[0][2]], Math.atan2(tx * sgn, tz * sgn));
  }
  // roof: flat slab with a parapet (seen from above)
  Q('alcStone', [pos(-half - .2, -D / 2, ytop), pos(half + .2, -D / 2, ytop), pos(half + .2, D / 2, ytop), pos(-half - .2, D / 2, ytop)], [[0, 0], [1, 0], [1, 1], [0, 1]], [.55, .45, .38], [0, 1, 0]);
  return D;
}
function lanePass(b, lanes) {
  const rr = rnd(1234), topAt = (x, z) => { const k = ri(x, z); return k >= 0 && TOPR[k] > -1e8 ? TOPR[k] : null; };
  let spans = 0, lanterns = 0, bridges = 0; const bridged = [];
  for (const L of lanes) {
    if (!LANE_DECK.has(L.w.name) || L.w.name === 'Calle Elvira') continue; const S = L.S; let lastB = -99;
    for (let i = 8; i < S.length - 8; i++) {
      const s = S[i]; if (!s || i * PAVE_STEP < lastB + 45 || !s.hitL || !s.hitR) continue; const width = s.wr - s.wl; if (width < 2.2 || width > 3.7) continue;
      if (!(S[i - 4] && S[i + 4])) continue;
      const A = [s.P[0] + s.nx * (s.wl - .5), s.P[1] + s.nz * (s.wl - .5)], B2 = [s.P[0] + s.nx * (s.wr + .5), s.P[1] + s.nz * (s.wr + .5)], gh = L.hq[i], tA = topAt(A[0], A[1]), tB = topAt(B2[0], B2[1]);
      if (tA === null || tB === null || Math.min(tA, tB) < gh + 9.2) continue;
      if (rr() < .55 || bridges >= 6) continue;
      const D = bridgeOver(b, s, L, i, rr); bridged.push([s.P[0], s.P[1], D]); lastB = i * PAVE_STEP; bridges++;
    }
  }
  for (const L of lanes) {
    if (!LANE_DECK.has(L.w.name)) continue; const S = L.S; let next = 2 + rr() * 5;
    for (let i = 3; i < S.length - 3; i++) {
      const s = S[i]; if (!s || i * PAVE_STEP < next || !(S[i - 3] && S[i + 3])) continue;
      const width = s.wr - s.wl; if (width > 5.4 || width < 1.6 || !s.hitL || !s.hitR) continue;
      if (bridged.some(q => Math.hypot(q[0] - s.P[0], q[1] - s.P[1]) < q[2] / 2 + 3)) continue;
      next = i * PAVE_STEP + 9 + rr() * 9;
      const A = [s.P[0] + s.nx * (s.wl + .03), s.P[1] + s.nz * (s.wl + .03)], B = [s.P[0] + s.nx * (s.wr - .03), s.P[1] + s.nz * (s.wr - .03)];
      const gh = L.hq[i], tA = topAt(A[0] - s.nx * .6, A[1] - s.nz * .6), tB = topAt(B[0] + s.nx * .6, B[1] + s.nz * .6);
      if (tA === null || tB === null) continue;
      const y0 = Math.min(gh + 5.0 + rr() * 1.0, Math.min(tA, tB) - 1.0); if (y0 < gh + 3.9) continue;
      const sag = .18 + rr() * .22, n = 8, pts = [];
      for (let k = 0; k <= n; k++) { const t = k / n; pts.push([A[0] + (B[0] - A[0]) * t, y0 - sag * 4 * t * (1 - t) + (rr() < 0 ? 0 : 0), A[1] + (B[1] - A[1]) * t]); }
      for (let k = 0; k < n; k++) b.line(pts[k], pts[k + 1], .007, 'alcDetail');
      spans++;
      const kind = rr();
      if (LOW && kind < .5) { /* no bulbs on phones */ } else if (kind < .5) { // string of warm bulbs
        for (let k = 1; k < n; k++) { addU(uBulb(), 'alcGlow', [pts[k][0], pts[k][1] - .08, pts[k][2]], 0); }
        LAMPS.push([(A[0] + B[0]) / 2, y0, (A[1] + B[1]) / 2, .5]);
      } else if (kind < .78) { // a big hung lantern at mid-span
        const mx = (A[0] + B[0]) / 2, mz = (A[1] + B[1]) / 2, my = pts[n / 2][1] - 1.05;
        addU(uHangLanternFrame(0, 1), 'alcDetail', [mx, my, mz], Math.atan2(s.nx, s.nz)); addU(uHangLanternGlass(0, 1), 'alcGlow', [mx, my, mz], Math.atan2(s.nx, s.nz));
        b.line([mx, my + 1.0, mz], [mx, pts[n / 2][1], mz], .006, 'alcDetail'); LAMPS.push([mx, my + .4, mz, 1.3]); lanterns++;
      } else if (kind < .9 && !LOW) { // washing
        const tiles = [14, 11, 2, 13, 3, 15, 4];
        for (let k = 1; k < n; k++) if (rr() < .8) { const p = pts[k], w = .36 + rr() * .2, h = .45 + rr() * .5; const t = tiles[Math.floor(rr() * tiles.length)]; const dx = s.tx * w / 2, dz = s.tz * w / 2, ang = (rr() - .5) * .2; Q('alcGoods', [[p[0] - dx, p[1] - h, p[2] - dz], [p[0] + dx, p[1] - h, p[2] + dz], [p[0] + dx, p[1], p[2] + dz], [p[0] - dx, p[1], p[2] - dz]], tileUV(t, rr() * .6, rr() * .6, .3, .3), [1, 1, 1], null); }
      }
    }
  }
  // life in the lanes: scooters against the walls and cats on the steps
  const placeAt = (L, i, off, fn) => { const s = L.S[i]; if (!s || !s.hitL || !s.hitR) return false; const side = rr() < .5 ? 0 : 1, t = side ? s.wr - off : s.wl + off, x = s.P[0] + s.nx * t, z = s.P[1] + s.nz * t, y = pavH(x, z); fn(x, y, z, Math.atan2(s.nx * (side ? 1 : -1), s.nz * (side ? 1 : -1)), side); return true; };
  let scooters = 0, cats = 0;
  if (LOW) return { spans, lanterns, bridges, scooters, cats, at: [] };
  for (const L of lanes) { if (!LANE_DECK.has(L.w.name)) continue; const S = L.S;
    for (let i = 6; i < S.length - 6; i += 4) { const s = S[i]; if (!s) continue; const width = s.wr - s.wl; if (width < 2.8 || width > 5.4) continue;
      if (rr() < .012) placeAt(L, i, .55, (x, y, z, rot) => { addU(uScooter(Math.floor(rr() * 4)), 'alcDetail', [x, y, z], rot + Math.PI / 2); BLD.nav.box(x, z, .5, 1.2, y - 1, y + 1, -Math.atan2(s.tz, s.tx)); scooters++; });
      else if (rr() < .008) placeAt(L, i, .35 + rr() * 1.2, (x, y, z, rot) => { addU(uCat(Math.floor(rr() * 4)), 'alcDetail', [x, y, z], rr() * 6.28); cats++; }); } }
  return { spans, lanterns, bridges, scooters, cats, at: bridged.map(q => [Math.round(q[0]), Math.round(q[1])]) };
}

// ---------------------------------------------------------------- the church of San Gregorio Bético (Placeta de San Gregorio)
function uOculus(r) {
  return unit(`ocu|${r}`, u => {
    const n = 12, c = PAL.stone;
    for (let i = 0; i < n; i++) {
      const a0 = i / n * Math.PI * 2, a1 = (i + 1) / n * Math.PI * 2;
      u.q([[Math.cos(a0) * r, Math.sin(a0) * r, 0.02], [Math.cos(a1) * r, Math.sin(a1) * r, 0.02], [Math.cos(a1) * r * 1.35, Math.sin(a1) * r * 1.35, 0.04], [Math.cos(a0) * r * 1.35, Math.sin(a0) * r * 1.35, 0.04]], c, [0, 0, 1]);
      u.tri([[0, 0, -.1], [Math.cos(a0) * r, Math.sin(a0) * r, -.1], [Math.cos(a1) * r, Math.sin(a1) * r, -.1]], i % 2 ? [.05, .06, .08] : [.08, .09, .11], [0, 0, 1]);
    }
  });
}
function churchFront(F, rr) {
  const B = F.B, len = F.len, cx = len / 2, g0 = F.g(cx), top = B.top, w = 2.3, st = col(0xcdbb99), stD = col(0xb09c78);
  const op = arcOp(cx - w / 2, cx + w / 2, g0 + .12, g0 + 2.95, 0); op.nopl = true;
  emitStorey(F, 0, [op]); F.rects = [op];
  // dark nave beyond the doors, closed carved doors
  const P = (u, y, ww) => F.P(u, y, ww);
  Q('alcDetail', [P(op.u0, op.y0, -RD - .1), P(op.u1, op.y0, -RD - .1), P(op.u1, op.y1 + .2, -RD - .1), P(op.u0, op.y1 + .2, -RD - .1)], [[0, 0], [1, 0], [1, 1], [0, 1]], [.05, .035, .03], F.n3);
  F.place(uDoorLeaf(+(w - .1).toFixed(2), 2.8, 0), 'alcDetail', cx, op.y0, 0.02);
  // stone portal: pilasters, entablature, pediment, niche
  const pw = .55, ya = g0 - .1, yb = op.y1 + .25;
  for (const sgn of [-1, 1]) {
    const u0 = sgn < 0 ? cx - w / 2 - pw : cx + w / 2, u1 = u0 + pw;
    F.fb('alcStone', u0, u1, ya, yb, -.0, .2, st); F.fb('alcStone', u0 - .08, u1 + .08, ya, ya + .5, -.0, .26, stD); F.fb('alcStone', u0 - .1, u1 + .1, yb - .2, yb, -.0, .28, stD);
    F.fb('alcStone', sgn < 0 ? u0 - .5 : u1 + .1, sgn < 0 ? u0 - .1 : u1 + .5, ya, yb + .35, 0, .12, mulc(st, .95));
  }
  F.fb('alcStone', cx - w / 2 - pw - .65, cx + w / 2 + pw + .65, yb, yb + .35, 0, .34, stD);          // entablature
  F.fb('alcStone', cx - w / 2 - pw - .75, cx + w / 2 + pw + .75, yb + .35, yb + .5, 0, .42, mulc(stD, 1.05));
  // upper register: framed niche with a lamp, pediment above
  const ny = yb + 1.0; F.fb('alcStone', cx - .7, cx + .7, ny, ny + 1.9, 0, .12, st);
  Q('alcDetail', [P(cx - .45, ny + .2, .13), P(cx + .45, ny + .2, .13), P(cx + .45, ny + 1.6, .13), P(cx - .45, ny + 1.6, .13)], [[0, 0], [1, 0], [1, 1], [0, 1]], [.07, .05, .04], F.n3);
  F.fb('alcStone', cx - .5, cx + .5, ny + 1.6, ny + 1.75, .12, .26, stD);
  F.place(uOculus(.42), 'alcDetail', cx, Math.min(top - 1.6, ny + 3.3), .0);
  // pilaster strips and quoins at the corners
  for (const [u0, u1] of [[0, .7], [len - .7, len]]) {
    F.fb('alcStone', u0, u1, g0 - .3, top, 0, .1, st, false);
    for (let y = g0 + .3; y < top - .5; y += .62) F.fb('alcStone', u0, u1 + (u1 === len ? 0 : .12) - (u0 === 0 ? 0 : .12), y, y + .3, 0, .18, stD, false);
  }
  F.fb('alcStone', 0, len, g0 - .1, g0 + .9, 0, .12, stD);            // plinth
  F.fb('alcStone', 0, len, top - .45, top - .1, 0, .3, stD);          // cornice
  gableFill(F); eaves(F);
  // the bell gable above the pediment
  const mid = F.P(cx, 0, 0), rh = roofH(B, mid[0], mid[2]), by = top + rh, bw = 2.5;
  F.fb('alcStone', cx - bw / 2, cx + bw / 2, by - .2, by + 2.4, -.1, .55, st);
  for (const sgn of [-.5, .5]) { const u = cx + sgn * bw * .45; Q('alcDetail', [P(u - .32, by + .55, .46), P(u + .32, by + .55, .46), P(u + .32, by + 1.7, .46), P(u - .32, by + 1.7, .46)], [[0, 0], [1, 0], [1, 1], [0, 1]], [.05, .04, .035], F.n3); addU(unit('bell', un => { un.sph(0, 0, 0, .17, .2, .17, col(0x9c7a3a), 2, 7); }), 'alcDetail', F.P(u, by + .95, .3), 0); }
  F.fb('alcStone', cx - bw / 2 - .15, cx + bw / 2 + .15, by + 2.4, by + 2.6, -.15, .7, stD);
  for (const sgn of [-1, 1]) F.fb('alcStone', cx + sgn * (bw / 2 + .05) - .1, cx + sgn * (bw / 2 + .05) + .1, by + 2.6, by + 3.1, 0, .2, stD);
  F.fb('alcStone', cx - .08, cx + .08, by + 2.6, by + 3.4, .1, .28, stD); F.fb('alcStone', cx - .3, cx + .3, by + 3.0, by + 3.12, .1, .28, stD); // cross
  // lamps either side of the doors
  for (const sgn of [-1, 1]) { const u = cx + sgn * (w / 2 + pw + 1.3); addU(uLanternWall(), 'alcDetail', F.P(u, g0 + 2.6, .1), F.rot); addU(uLanternWallGlass(), 'alcGlow', F.P(u, g0 + 2.6, .1), F.rot); LAMPS.push([...F.P(u, g0 + 3.0, .5), 1]); }
}
function churchSide(F, rr) {
  const B = F.B, len = F.len, g = F.g(len / 2), st = col(0xcdbb99), stD = col(0xb09c78);
  const nb = Math.max(1, Math.round(len / 4.5)), bw = len / nb, ops = [];
  for (let k = 0; k < nb; k++) { const cx = (k + .5) * bw, op = arcOp(cx - .38, cx + .38, F.floor(0) + 4.4, F.floor(0) + 5.15, 0); ops.push(op); }
  emitStorey(F, 0, ops);
  for (const op of ops) { const cx = (op.u0 + op.u1) / 2; Q('alcDetail', [F.P(op.u0, op.y0, -RD + .05), F.P(op.u1, op.y0, -RD + .05), F.P(op.u1, op.y1, -RD + .05), F.P(op.u0, op.y1, -RD + .05)], [[0, 0], [1, 0], [1, 1], [0, 1]], [.07, .08, .1], F.n3); }
  for (let k = 0; k <= nb; k++) { const u = k * bw; F.fb('alcStone', Math.max(0, u - .3), Math.min(len, u + .3), F.gmin(Math.max(0, u - .3), Math.min(len, u + .3)) - .3, B.top - .2, 0, .5, stD, true); } // buttresses
  F.fb('alcStone', 0, len, g - .1, g + .9, 0, .15, stD); F.fb('alcStone', 0, len, B.top - .45, B.top - .1, 0, .3, stD);
  gableFill(F); eaves(F);
}

// ---------------------------------------------------------------- roofs and whole buildings
function buildRoof(B, rr) {
  const r = B.roof, tris = r.tris, mat = r.kind === 'flat' ? 'alcStone' : 'alcTile', top = B.top;
  const tint = r.kind === 'flat' ? mulc(col(0x9a8a78), .8 + .3 * rr()) : mulc(col(0xd8a58a), .75 + .4 * rr());
  for (let i = 0; i < tris.length; i += 3) {
    const a = tris[i], b = tris[i + 1], c = tris[i + 2];
    const y = h => r.kind === 'flat' ? top - .45 : top + h, P = [[a[0], y(a[2]), a[1]], [b[0], y(b[2]), b[1]], [c[0], y(c[2]), c[1]]];
    let U;
    if (r.kind === 'flat') U = P.map(p => [p[0] / 2.4, p[2] / 2.4]);
    else {
      // direction of steepest descent -> channels run down the slope
      const ux = P[1][0] - P[0][0], uy = P[1][1] - P[0][1], uz = P[1][2] - P[0][2], vx = P[2][0] - P[0][0], vy = P[2][1] - P[0][1], vz = P[2][2] - P[0][2];
      let nx = uy * vz - uz * vy, nz = ux * vy - uy * vx; const l = hyp(nx, nz) || 1; nx /= l; nz /= l; // horizontal normal
      const s = hyp(nx, nz) < .05 ? [1, 0] : [nx, nz];
      U = P.map(p => [(-s[1] * p[0] + s[0] * p[2]) / 2 + B.uo, (s[0] * p[0] + s[1] * p[2]) / (2 * Math.cos(Math.atan(r.tanp)))]);
    }
    T3(mat, P, U, tint, [0, 1, 0]);
  }
  if (r.kind !== 'flat') {
    for (const [x0, z0, x1, z1, h] of r.ridge) { // ridge cap
      const L = hyp(x1 - x0, z1 - z0); if (L < .3) continue; const ang = Math.atan2(x1 - x0, z1 - z0);
      const g = unit(`ridge|${L.toFixed(1)}`, u => { u.box(-.17, .17, 0, .17, -L / 2, L / 2, col(0xa8553a)); });
      addU(g, 'alcDetail', [(x0 + x1) / 2, top + h - .02, (z0 + z1) / 2], ang);
    }
    // a chimney now and then
    if (rr() < .4 && r.ridge.length) { const [x0, z0, x1, z1, h] = r.ridge[0], t = .25 + rr() * .5, x = x0 + (x1 - x0) * t, z = z0 + (z1 - z0) * t; const ch = unit('chim', u => { u.box(-.3, .3, -.4, 1.1, -.3, .3, col(0xc9b9a0)); u.box(-.38, .38, 1.1, 1.2, -.38, .38, col(0x8a7a68)); }); addU(ch, 'alcDetail', [x, top + h, z], r.ax ? Math.atan2(r.ax[0], r.ax[1]) : 0); }
  }
}
function roofTop(B, rr) {
  const r = B.roof, tris = r.tris; if (r.kind !== 'flat' || tris.length < 3 || LOW) return;
  const tri = []; for (let i = 0; i < tris.length; i += 3) { const a = tris[i], b = tris[i + 1], c = tris[i + 2], ar = Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2; if (ar > 5) tri.push([ar, (a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3]); }
  if (!tri.length) return; const y = B.top - .45;
  const spot = () => { const t = tri[Math.floor(rr() * tri.length)]; return [t[1] + (rr() - .5) * 1.0, t[2] + (rr() - .5) * 1.0]; };
  if (rr() < .3) { const [x, z] = spot(); addU(unit('tank', u => { u.cyl(0, .5, 0, .5, .5, 1.1, 8, col(0xd6d2c8)); for (const [a, c] of [[-.3, -.3], [.3, -.3], [-.3, .3], [.3, .3]]) u.box(a - .03, a + .03, 0, .5, c - .03, c + .03, PAL.iron, false, false); }), 'alcDetail', [x, y, z], rr() * 6); }
  if (rr() < .28 && B.L >= 2) { const [x, z] = spot(), ang = rr() * 3; addU(unit('cabin', u => { u.box(-1, 1, 0, 2.3, -.8, .8, col(0xe6e0d0)); u.box(-1.1, 1.1, 2.3, 2.45, -.9, .9, col(0x8a7a68)); u.box(-.4, .4, 0, 1.9, .8, .83, PAL.wood, false, false); }), 'alcDetail', [x, y, z], ang); }
  if (rr() < .26) { const [x, z] = spot(), ang = rr() * 3.14, c = Math.cos(ang), sn = Math.sin(ang), L = 2 + rr() * 1.5; b_line([x - c * L / 2, y + 1.7, z + sn * L / 2], [x + c * L / 2, y + 1.7, z - sn * L / 2]); const tiles = [14, 11, 2, 13, 3, 15, 4]; for (let k = 0; k < 5; k++) { const f = (k + .5) / 5, px = x + c * L * (f - .5), pz = z - sn * L * (f - .5), w = .34, h = .5 + rr() * .3, dx = c * w / 2, dz = -sn * w / 2, t = tiles[Math.floor(rr() * tiles.length)]; Q('alcGoods', [[px - dx, y + 1.7 - h, pz - dz], [px + dx, y + 1.7 - h, pz + dz], [px + dx, y + 1.7, pz + dz], [px - dx, y + 1.7, pz - dz]], tileUV(t, rr() * .6, rr() * .6, .3, .3), [1, 1, 1], null); } for (const e of [-1, 1]) BLD.box(x + c * e * L / 2 - .03, y, z - sn * e * L / 2 - .03, .06, 1.7, .06, 'alcDetail'); }
  if (rr() < .3) { const [x, z] = spot(); for (let k = 0; k < 3; k++) addU(uFlowerPot(Math.floor(rr() * 6)), 'alcDetail', [x + k * .35, y, z + (k % 2) * .2], 0); }
}
const b_line = (a, c) => BLD.line(a, c, .006, 'alcDetail');
function poiKind(t) {
  const am = t.amenity || '', cu = t.cuisine || '', nm = (t.name || '').toLowerCase();
  if (am === 'place_of_worship' || t.tourism === 'artwork') return null;
  if (t.tourism === 'hotel' || t.tourism === 'hostel' || t.tourism === 'guest_house') return 'hotel';
  if (/teter|tea ?house|teahouse|tea/.test(nm) || /tea/.test(cu)) return 'tea';
  if (am === 'pub' || am === 'bar' || am === 'nightclub' || am === 'music_venue') return 'bar';
  if (am === 'restaurant' || am === 'fast_food') return /arab|moroccan|lebanese|indian|kebab|pizza|halal/.test(cu + nm) ? 'rest' : 'bar';
  if (am === 'cafe' || am === 'ice_cream') return 'bar';
  if (t.shop || am === 'pharmacy' || am === 'bank') return t.shop ? 'shop' : 'door';
  return null;
}
function segDist(px, pz, ax, az, bx, bz) { const dx = bx - ax, dz = bz - az, t = clamp(((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz || 1), 0, 1); return [hyp(ax + dx * t - px, az + dz * t - pz), t]; }
function assignPois(blds) {
  const edges = []; for (const B of blds) B.edges.forEach((e, i) => { if (e[4] === 0 && hyp(e[2] - e[0], e[3] - e[1]) > 1.2) edges.push({ B, e }); });
  const claimed = new Map(); let n = 0;
  for (const p of LAY.pois) {
    const kind = poiKind(p.t); if (!kind) continue; if (p.x < -727 || p.x > -553 || p.z < -118 || p.z > 48) continue;
    let best = null;
    for (const { B, e } of edges) { const [d, t] = segDist(p.x, p.z, e[0], e[1], e[2], e[3]); const inside = pointIn(B.ring, p.x, p.z); const score = d + (inside ? 0 : 6); if (!best || score < best.score) best = { score, B, e, t, d }; }
    if (!best || best.score > 14) continue;
    const key = best.B.k + ':' + best.e[0] + ':' + best.e[1]; const F = frameOf(best.e);
    const u = ((best.e[0] - F.x) * F.tx + (best.e[1] - F.z) * F.tz) + 0; // edge start in facade coordinates (0 or len)
    const pu = (p.x - F.x) * F.tx + (p.z - F.z) * F.tz;
    (best.e.pois = best.e.pois || []).push({ u: clamp(pu, .3, F.len - .3), kind, name: p.t.name }); n++;
  }
  return n;
}
function pointIn(ring, x, z) { let inside = false; for (let a = 0, b = ring.length - 1; a < ring.length; b = a++) { const A = ring[a], Bp = ring[b]; if ((A[1] > z) !== (Bp[1] > z) && x < (Bp[0] - A[0]) * (z - A[1]) / (Bp[1] - A[1]) + A[0]) inside = !inside; } return inside; }

function buildBuildings(b) {
  const blds = LAY.buildings, byK = new Map(blds.map(B => [B.k, B])), occK = new Map(LAY.occ.map(o => [o.k, o]));
  const tourist = (x, z) => { // closeness to the tea-house lanes
    let d = 1e9; for (const w of LAY.ways) { if (w.name !== 'Calle Calderería Nueva' && w.name !== 'Calle Calderería Vieja' && w.name !== 'Calle Elvira' && w.name !== 'Cuesta de Marañas' && w.name !== 'Calle Hospital Corpus Christi') continue; for (let i = 0; i < w.pts.length - 1; i++) d = Math.min(d, segDist(x, z, w.pts[i][0], w.pts[i][1], w.pts[i + 1][0], w.pts[i + 1][1])[0]); }
    return clamp(1 - (d - 8) / 40, 0, 1);
  };
  // levels and tops
  for (const B of blds) {
    const rr = rnd(B.k * 48271 + 11); B.rr0 = rr;
    B.L = Math.max(1, Math.round(B.L));
    const hs = []; for (const e of B.edges) if (e[4] !== 2) { const mx = (e[0] + e[2]) / 2 + e[6] * .6, mz = (e[1] + e[3]) / 2 + e[7] * .6; hs.push(pavH(mx, mz)); }
    if (!hs.length) for (const p of B.ring) hs.push(terrainHeight(p[0], p[1]));
    hs.sort((a, c) => a - c); B.Y0 = hs[Math.floor(hs.length * .5)] + .08;
    if (B.k === 35) B.L = 1; B.h = B.k === 35 ? 8.6 : H0 + HS * (B.L - 1) + .5; B.top = B.Y0 + B.h; fillPoly(B.ring, TOPR, B.top);
    const tn = pick(rr, TINTS); B.tint = mulc(PAL[tn], .96 + .06 * rr());
    const mm = rr(); B.mat = B.kind === 'church' || B.kind === 'public' ? 'alcStone' : mm < .06 ? 'alcBrick' : 'alcRender';
    if (B.mat === 'alcBrick') B.tint = mulc(col(0xd8b99a), .95 + .1 * rr()); if (B.mat === 'alcStone') B.tint = mulc(col(0xfff2d6), .97 + .08 * rr());
    B.uo = rr() * 5; B.wood = PAL.woodL; B.plinthH = rr() < .72 ? .55 + rr() * .45 : 0; B.plinthC = rr() < .5 ? col(0xb3a98f) : rr() < .5 ? col(0x9c9a94) : col(0xc9bba0);
  }
  const npoi = assignPois(blds);
  const topOf = k => { const B = byK.get(k); if (B) return B.top; const o = occK.get(k); if (!o) return -1e9; let y = 0; for (const p of o.ring) y += terrainHeight(p[0], p[1]); return y / o.ring.length + o.h; };
  for (const B of blds) {
    const rr = B.rr0;
    for (const e of B.edges) {
      const len = hyp(e[2] - e[0], e[3] - e[1]); if (len < .1) continue;
      if (e[4] === 2) { const nbTop = Math.max(...e[5].map(topOf), -1e9); if (nbTop < B.top - .25) partyFacade(new Fac(B, e, true), nbTop); continue; }
      const F = new Fac(B, e, e[4] !== 0);
      if (B.k === 35 && e[4] === 0) { if (len > 11 && len < 14) churchFront(F, rr); else churchSide(F, rr); }
      else if (e[4] === 0) streetFacade(F, tourist((e[0] + e[2]) / 2, (e[1] + e[3]) / 2)); else plainFacade(F);
      // collision: a wall slab just inside the footprint edge
      if (len > .25) b.nav.box((e[0] + e[2]) / 2 - e[6] * .25, (e[1] + e[3]) / 2 - e[7] * .25, len + .1, .5, B.Y0 - 40, B.top + 1, -Math.atan2(e[3] - e[1], e[2] - e[0]));
    }
    buildRoof(B, rr); roofTop(B, rr);
    // roof of a courtyard hole: nothing (open)
  }
  return npoi;
}

// light pools: warm patches under the registered lamps, baked into the paving's vertex colours
function lightPools() {
  for (const { mat, geo } of GEOS.values()) {
    if (!/^alc(Pebble|PebbleFlat|Sett|Asphalt)$/.test(mat)) continue;
    const p = geo.p, c = geo.c;
    for (let i = 0; i < geo.count; i++) {
      const x = p[i * 3], y = p[i * 3 + 1], z = p[i * 3 + 2]; let add = 0;
      for (const l of LAMPS) { const dx = x - l[0], dz = z - l[2], d2 = dx * dx + dz * dz + Math.max(0, l[1] - y) ** 2 * .25; if (d2 < 22) add += (1 - d2 / 22) ** 2 * (l[3] ?? 1) * .5; }
      if (add > 0) { c[i * 3] *= 1 + add * .9; c[i * 3 + 1] *= 1 + add * .55; c[i * 3 + 2] *= 1 + add * .22; }
    }
  }
}

let LOW = false;
// ---------------------------------------------------------------- entry points
export function build(b, ctx) {
  b.zone = 'calderia'; BLD = b; LOW = !!ctx.low; const t0 = performance.now();
  GEOS.clear(); LAMPS.length = 0;
  OCC = new Uint8Array(RNX * RNZ); PH = new Float32Array(RNX * RNZ).fill(NaN); COV = new Int16Array(RNX * RNZ).fill(-1);
  for (const o of LAY.occ) fillPoly(o.ring, OCC, 1);
  const lanes = buildLanes(b, STAT); window.CALD = { dbg: (x, z) => { const k = ri(x, z); return [k, OCC[k], PH[k], COV[k]]; }, lanes: lanes.map(L => ({ name: L.w.name, pts: L.S.map((s, i) => s ? [+(s.P[0] + s.nx * L.tcs[i]).toFixed(2), +(s.P[1] + s.nz * L.tcs[i]).toFixed(2), +(s.tr - s.tl).toFixed(1)] : null).filter(Boolean) })) }; const t1 = performance.now();
  buildGround(b, STAT); const t2 = performance.now();
  TOPR = new Float32Array(RNX * RNZ).fill(-1e9);
  for (const o of LAY.occ) { if (!o.inbox) fillPoly(o.ring, TOPR, (() => { let y = 0; for (const q of o.ring) y += terrainHeight(q[0], q[1]); return y / o.ring.length + o.h; })()); }
  const npoi = buildBuildings(b); const lp = lanePass(b, lanes); STAT.lp = JSON.stringify(lp); const t3 = performance.now();
  // trees in the Placeta de San Gregorio and a few shrubs
  for (const [x, z, sp, h] of [[-597, -95, ORANGE, 4.6], [-591.5, -101, ORANGE, 5.2], [-600, -100, SHRUB, 2.2]]) { if (!occupied(x, z)) plant(x, terrainHeight(x, z), z, sp, h); }
  lightPools();
  let tris = 0; for (const { mat, geo } of GEOS.values()) { tris += geo.tris; b.unique(geo.geometry(), mat, [0, 0, 0], 0); geo.p = geo.n = geo.u = geo.c = geo.i = null; }
  GEOS.clear();
  console.log(`calderia: ${tris} unique tris, ${LAY.buildings.length} buildings, ${npoi} POIs, lanes ${(t1 - t0) | 0}ms ground ${(t2 - t1) | 0}ms buildings ${(t3 - t2) | 0}ms`, JSON.stringify(STAT));
}
