import * as THREE from 'three';

// The facade atlas: one bay × one storey of eight Tokyo building styles, drawn on a canvas at start-up, in three
// rows (upper storey, ground storey, shop-front ground storey). Two textures: the albedo, and a mask whose
// channels the shader reads — R glass (window area), G ambient darkening (reveals, under slabs), B metal / railing.
// Everything about decay (broken glass, stains, vines) is added in the shader on top of these clean drawings.

export const STYLES = [
  // name, bay width (m), storey height (m)
  { name: 'curtain', bay: 3.2, floor: 3.9 },
  { name: 'precast', bay: 3.4, floor: 3.7 },
  { name: 'mansion', bay: 3.6, floor: 3.0 },
  { name: 'tile', bay: 3.0, floor: 3.0 },
  { name: 'house', bay: 2.7, floor: 2.8 },
  { name: 'danchi', bay: 3.6, floor: 2.8 },
  { name: 'glass', bay: 3.0, floor: 4.0 },
  { name: 'darktile', bay: 3.2, floor: 3.4 },
];
export const CELL = 256, COLS = 8, ROWS = 3;

function rng(seed) { return () => ((seed = Math.imul(seed, 1664525) + 1013904223 | 0) >>> 0) / 4294967296; }

export function makeFacadeAtlas() {
  const W = CELL * COLS, H = CELL * ROWS;
  const alb = document.createElement('canvas'); alb.width = W; alb.height = H; const a = alb.getContext('2d');
  const msk = document.createElement('canvas'); msk.width = W; msk.height = H; const m = msk.getContext('2d');
  const r = rng(11);
  // metres -> pixels inside a cell: x from the left, y from the floor line (bottom)
  const px = (st, xm) => xm / st.bay * CELL, py = (st, ym) => CELL - ym / st.floor * CELL;
  const speckle = (g, x0, y0, w, h, n, amp0, dark = true) => { const amp = amp0 * 0.45; for (let i = 0; i < n; i++) { const v = r(); g.fillStyle = `rgba(${dark && v < 0.5 ? 0 : 255},${dark && v < 0.5 ? 0 : 255},${dark && v < 0.5 ? 0 : 255},${amp * r()})`; g.fillRect(x0 + r() * w, y0 + r() * h, 1 + r() * 2.5, 1 + r() * 2.5); } };
  const hline = (g, x0, y, w, c, t = 1) => { g.fillStyle = c; g.fillRect(x0, y, w, t); };
  // draws one window with its frame and reveal: albedo gets the frame and a dark sill shadow, the mask gets glass
  function window(st, ox, oy, x, y, w, h, frame, opts = {}) {
    const X = ox + px(st, x), Y = oy + py(st, y + h), Wd = px(st, w), Ht = h / st.floor * CELL;
    const reveal = opts.reveal ?? 4;
    a.fillStyle = 'rgba(0,0,0,0.35)'; a.fillRect(X - reveal, Y - reveal, Wd + reveal * 2, Ht + reveal * 2);          // reveal shadow
    a.fillStyle = frame; a.fillRect(X - 2, Y - 2, Wd + 4, Ht + 4);
    a.fillStyle = '#2a3034'; a.fillRect(X, Y, Wd, Ht);                                                                // glass base (replaced by the shader)
    m.fillStyle = 'rgb(255,0,0)'; m.fillRect(X, Y, Wd, Ht);
    m.fillStyle = 'rgba(0,160,0,0.9)'; m.fillRect(X - reveal, Y - reveal, Wd + reveal * 2, reveal); m.fillRect(X - reveal, Y - reveal, reveal, Ht + reveal * 2);   // AO on top / left reveal
    if (opts.mullions) { a.fillStyle = frame; for (let k = 1; k < opts.mullions; k++) a.fillRect(X + Wd * k / opts.mullions - 1, Y, 2, Ht); }
    if (opts.transom) { a.fillStyle = frame; a.fillRect(X, Y + Ht * opts.transom, Wd, 2); }
    if (opts.sash) { a.fillStyle = frame; a.fillRect(X + Wd / 2 - 1.5, Y, 3, Ht); a.fillStyle = 'rgba(255,255,255,0.18)'; a.fillRect(X, Y, Wd / 2, Ht); }
    a.fillStyle = 'rgba(0,0,0,0.25)'; a.fillRect(X - reveal, Y + Ht + 2, Wd + reveal * 2, 3);                       // sill shadow below
    if (opts.sill) { a.fillStyle = opts.sill; a.fillRect(X - reveal - 2, Y + Ht + 1, Wd + reveal * 2 + 4, 4); }
  }
  function balcony(st, ox, oy, x, w, h, kind) {
    // parapet slab across the bay with its shadow on the wall behind, a railing on top
    const X = ox + px(st, x), Wd = px(st, w), Y = oy + py(st, h), Ht = h / st.floor * CELL;
    a.fillStyle = 'rgba(0,0,0,0.42)'; a.fillRect(X, Y - 6, Wd, Ht + 6);                     // shade under the slab above / behind the parapet
    m.fillStyle = 'rgba(0,200,0,1)'; m.fillRect(X, Y - 6, Wd, 10);
    if (kind === 'concrete') { a.fillStyle = '#bfb9ae'; a.fillRect(X, Y, Wd, Ht * 0.55); speckle(a, X, Y, Wd, Ht * 0.55, 160, 0.08); a.fillStyle = 'rgba(0,0,0,0.3)'; a.fillRect(X, Y + Ht * 0.55, Wd, 3); }
    else { a.fillStyle = '#6a6b6a'; for (let k = 0; k < Wd; k += 7) a.fillRect(X + k, Y, 1.5, Ht * 0.55); a.fillRect(X, Y, Wd, 3); a.fillRect(X, Y + Ht * 0.55 - 3, Wd, 3); m.fillStyle = 'rgb(0,0,255)'; m.fillRect(X, Y, Wd, Ht * 0.55); }
    a.fillStyle = '#d8d3c9'; a.fillRect(X - 2, Y + Ht * 0.55, Wd + 4, 5);                    // the slab edge
    a.fillStyle = 'rgba(0,0,0,0.35)'; a.fillRect(X - 2, Y + Ht * 0.55 + 5, Wd + 4, 4);
  }
  function acUnit(st, ox, oy, x, y) { const X = ox + px(st, x), Y = oy + py(st, y + 0.6); a.fillStyle = '#cfcbc3'; a.fillRect(X, Y, px(st, 0.7), 0.6 / st.floor * CELL); a.fillStyle = 'rgba(0,0,0,0.3)'; a.fillRect(X, Y + 0.6 / st.floor * CELL - 3, px(st, 0.7), 3); a.fillStyle = '#9a9790'; a.beginPath(); a.arc(X + px(st, 0.3), Y + 0.3 / st.floor * CELL, px(st, 0.2), 0, 7); a.fill(); }
  function tiles(ox, oy, w, h, c1, c2, tw, th) { a.fillStyle = c2; a.fillRect(ox, oy, w, h); for (let y = 0; y < h; y += th) for (let x = ((y / th) % 2) * tw / 2; x < w; x += tw) { a.fillStyle = c1; a.globalAlpha = 0.5 + r() * 0.5; a.fillRect(ox + x, oy + y, tw - 0.7, th - 0.7); } a.globalAlpha = 1; }

  const styles = {
    curtain(ox, oy, row, st) {
      a.fillStyle = '#5c6267'; a.fillRect(ox, oy, CELL, CELL); speckle(a, ox, oy, CELL, CELL, 300, 0.06);
      // spandrel band (opaque panel) and a tall glass band split by mullions
      window(st, ox, oy, 0.08, 0.95, st.bay - 0.16, st.floor - 1.15, '#9a9ea0', { mullions: 2, reveal: 2 });
      a.fillStyle = '#4b5055'; a.fillRect(ox, oy + py(st, 0.9), CELL, py(st, 0) - py(st, 0.9)); hline(a, ox, oy + py(st, 0.9), CELL, '#aab0b2', 3);
      if (row === 1) { a.fillStyle = '#3a3f43'; a.fillRect(ox, oy, CELL, CELL); window(st, ox, oy, 0.1, 0.1, st.bay - 0.2, st.floor - 0.5, '#8b9093', { mullions: 2, reveal: 2 }); }
    },
    precast(ox, oy, row, st) {
      a.fillStyle = '#d3cdc2'; a.fillRect(ox, oy, CELL, CELL); speckle(a, ox, oy, CELL, CELL, 500, 0.08);
      hline(a, ox, oy + py(st, st.floor - 0.05), CELL, 'rgba(0,0,0,0.25)', 3); hline(a, ox, oy + py(st, 0.0) - 3, CELL, 'rgba(255,255,255,0.25)', 2);
      window(st, ox, oy, 0.45, 1.0, st.bay - 0.9, 1.7, '#4a4d50', { mullions: 3, transom: 0.3, sill: '#b5afa4' });
      if (row === 1) { window(st, ox, oy, 0.3, 0.1, st.bay - 0.6, st.floor - 0.6, '#45484b', { mullions: 2 }); }
    },
    mansion(ox, oy, row, st) {
      a.fillStyle = '#d9d2c4'; a.fillRect(ox, oy, CELL, CELL); tiles(ox, oy, CELL, CELL, '#d6cfc1', '#cbc4b6', 20, 9);
      window(st, ox, oy, 0.75, 1.3, st.bay - 1.5, 1.5, '#6d6a63', { sash: true });
      balcony(st, ox, oy, 0.1, st.bay - 0.2, 1.2, r() < 0.5 ? 'concrete' : 'rail');
      if (r() < 0.6) acUnit(st, ox, oy, st.bay - 0.95, 1.25);
      if (row === 1) { a.fillStyle = '#b9b2a4'; a.fillRect(ox, oy, CELL, CELL); tiles(ox, oy, CELL, CELL, '#b6ad9d', '#aba292', 20, 9); window(st, ox, oy, 0.6, 0.15, st.bay - 1.2, 2.2, '#3f4245', { mullions: 2 }); }
    },
    tile(ox, oy, row, st) {
      a.fillStyle = '#9a7c62'; a.fillRect(ox, oy, CELL, CELL); tiles(ox, oy, CELL, CELL, '#a68a70', '#977b63', 10, 20);
      window(st, ox, oy, 0.7, 1.0, st.bay - 1.4, 1.25, '#5a5147', { sash: true, sill: '#7b6655' });
      if (r() < 0.5) acUnit(st, ox, oy, 0.05, 0.9);
      if (row === 1) { window(st, ox, oy, 0.35, 0.1, st.bay - 0.7, 2.3, '#3c3a36', { mullions: 2 }); }
    },
    house(ox, oy, row, st) {
      // siding boards with a sash window
      a.fillStyle = '#e7e2d6'; a.fillRect(ox, oy, CELL, CELL); for (let y = 0; y < CELL; y += 11) { hline(a, ox, oy + y, CELL, 'rgba(0,0,0,0.12)', 1.5); hline(a, ox, oy + y + 2, CELL, 'rgba(255,255,255,0.3)', 1); }
      speckle(a, ox, oy, CELL, CELL, 200, 0.05);
      window(st, ox, oy, 0.7, 1.0, st.bay - 1.4, 1.1, '#f2eee6', { sash: true, sill: '#d8d2c6' });
      if (row === 1) { window(st, ox, oy, 0.5, 0.15, st.bay - 1.0, 2.0, '#ece7dd', { sash: true }); }
    },
    danchi(ox, oy, row, st) {
      a.fillStyle = '#c9c4b9'; a.fillRect(ox, oy, CELL, CELL); speckle(a, ox, oy, CELL, CELL, 600, 0.1);
      hline(a, ox, oy + py(st, st.floor - 0.02), CELL, 'rgba(0,0,0,0.3)', 4);
      window(st, ox, oy, 0.6, 1.25, st.bay - 1.2, 1.4, '#7a7f82', { sash: true });
      balcony(st, ox, oy, 0.0, st.bay, 1.15, 'rail');
      if (row === 1) { window(st, ox, oy, 0.5, 0.1, st.bay - 1.0, 2.0, '#6d7275', { sash: true }); }
    },
    glass(ox, oy, row, st) {
      a.fillStyle = '#3a4248'; a.fillRect(ox, oy, CELL, CELL);
      window(st, ox, oy, 0.03, 0.03, st.bay - 0.06, st.floor - 0.06, '#8d9599', { mullions: 2, transom: 0.72, reveal: 1 });
      if (row === 1) { window(st, ox, oy, 0.03, 0.03, st.bay - 0.06, st.floor - 0.06, '#8d9599', { mullions: 2, reveal: 1 }); }
    },
    darktile(ox, oy, row, st) {
      a.fillStyle = '#3f3a36'; a.fillRect(ox, oy, CELL, CELL); tiles(ox, oy, CELL, CELL, '#4a4540', '#403b36', 12, 24);
      window(st, ox, oy, 0.45, 0.95, st.bay - 0.9, 1.8, '#242628', { mullions: 2, transom: 0.25 });
      if (row === 1) { window(st, ox, oy, 0.15, 0.1, st.bay - 0.3, st.floor - 0.5, '#202224', { mullions: 2 }); }
    },
  };
  // the shop-front row: shutters, a sign box and an awning, shared by commercial ground floors
  function shop(ox, oy, st) {
    a.fillStyle = '#8c857b'; a.fillRect(ox, oy, CELL, CELL); speckle(a, ox, oy, CELL, CELL, 300, 0.08);
    const X = ox + px(st, 0.2), Wd = px(st, st.bay - 0.4), Y = oy + py(st, 2.6), Ht = 2.5 / st.floor * CELL;
    if (r() < 0.5) { a.fillStyle = '#9c9a94'; a.fillRect(X, Y, Wd, Ht); for (let y = 0; y < Ht; y += 6) hline(a, X, Y + y, Wd, 'rgba(0,0,0,0.28)', 2); m.fillStyle = 'rgb(0,0,255)'; m.fillRect(X, Y, Wd, Ht); }      // shutter
    else window(st, ox, oy, 0.2, 0.1, st.bay - 0.4, 2.5, '#3a3c3e', { mullions: 2, reveal: 2 });
    const sy = oy + py(st, st.floor - 0.05), sh = 0.65 / st.floor * CELL;
    a.fillStyle = ['#b9433a', '#2f6aa8', '#d8c15a', '#e9e2d2', '#3b7a4a'][Math.floor(r() * 5)]; a.fillRect(ox + 4, sy, CELL - 8, sh);              // sign box
    a.fillStyle = 'rgba(255,255,255,0.75)'; for (let k = 0; k < 4; k++) a.fillRect(ox + 20 + k * 52 + r() * 10, sy + sh * 0.3, 22 + r() * 14, sh * 0.42);   // faded lettering
    a.fillStyle = 'rgba(0,0,0,0.35)'; a.fillRect(ox + 4, sy + sh, CELL - 8, 5);
    m.fillStyle = 'rgba(0,120,0,1)'; m.fillRect(ox, sy + sh, CELL, 8);
  }
  for (let i = 0; i < COLS; i++) {
    const st = STYLES[i];
    styles[st.name](i * CELL, 0, 0, st);
    styles[st.name](i * CELL, CELL, 1, st);
    shop(i * CELL, CELL * 2, st);
  }
  const t = (c, srgb) => { const x = new THREE.CanvasTexture(c); x.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; x.wrapS = x.wrapT = THREE.ClampToEdgeWrapping; x.anisotropy = 8; x.generateMipmaps = true; x.minFilter = THREE.LinearMipmapLinearFilter; x.magFilter = THREE.LinearFilter; return x; };
  return { albedo: t(alb, true), mask: t(msk, false), canvas: alb, maskCanvas: msk };
}

// A tileable detail texture (world-space, 8 m period): R concrete grain, G stain blotches, B cracks, A leaf mask
export function makeDetailTexture() {
  const S = 512, c = document.createElement('canvas'); c.width = c.height = S; const g = c.getContext('2d');
  const r = rng(5);
  const img = g.createImageData(S, S); const d = img.data;
  // value noise, tileable by sampling on a torus
  const perm = new Uint8Array(512); for (let i = 0; i < 256; i++) perm[i] = i; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; } for (let i = 0; i < 256; i++) perm[i + 256] = perm[i];
  const h2 = (x, y) => perm[(perm[x & 255] + y) & 255] / 255;
  const vn = (x, y, p) => { const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi, sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy); const a0 = h2(xi % p, yi % p), b0 = h2((xi + 1) % p, yi % p), c0 = h2(xi % p, (yi + 1) % p), d0 = h2((xi + 1) % p, (yi + 1) % p); return (a0 + (b0 - a0) * sx) * (1 - sy) + (c0 + (d0 - c0) * sx) * sy; };
  const fbm = (x, y, oct, base) => { let v = 0, amp = 0.5, f = base; for (let k = 0; k < oct; k++) { v += amp * vn(x * f, y * f, f); amp *= 0.5; f *= 2; } return v; };
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const u = x / S, v = y / S, i = (y * S + x) * 4;
    const grain = fbm(u, v, 5, 8);
    const stain = fbm(u + 0.3, v + 0.7, 4, 2);
    // cracks: ridged noise
    const rd = 1 - Math.abs(fbm(u + 0.5, v + 0.1, 4, 4) * 2 - 1); const crack = Math.pow(Math.max(0, rd - 0.82) / 0.18, 1.5);
    // leaves: clusters of round blobs on a coarse mask
    const cluster = fbm(u + 0.8, v + 0.2, 3, 3);
    d[i] = grain * 255; d[i + 1] = stain * 255; d[i + 2] = Math.min(255, crack * 255); d[i + 3] = cluster * 255;
  }
  g.putImageData(img, 0, 0);
  // leaf blobs painted into alpha where the cluster is dense: stamp discs
  const leaf = document.createElement('canvas'); leaf.width = leaf.height = S; const lg = leaf.getContext('2d');
  lg.fillStyle = '#000'; lg.fillRect(0, 0, S, S);
  for (let k = 0; k < 3000; k++) {
    const x = r() * S, y = r() * S; const cl = d[((Math.floor(y) % S) * S + (Math.floor(x) % S)) * 4 + 3] / 255;
    if (r() > Math.pow(cl, 1.8) * 1.8) continue;
    const rad = 4 + r() * 6; lg.fillStyle = `rgba(255,255,255,${0.7 + r() * 0.3})`;
    for (const [dx, dy] of [[0, 0], [S, 0], [-S, 0], [0, S], [0, -S]]) { lg.beginPath(); lg.ellipse(x + dx, y + dy, rad, rad * 0.7, r() * 3, 0, 7); lg.fill(); }
  }
  const li = lg.getImageData(0, 0, S, S).data; for (let i = 0; i < S * S; i++) d[i * 4 + 3] = li[i * 4];
  const x = new THREE.DataTexture(new Uint8Array(d), S, S, THREE.RGBAFormat); x.colorSpace = THREE.NoColorSpace;
  x.wrapS = x.wrapT = THREE.RepeatWrapping; x.generateMipmaps = true; x.minFilter = THREE.LinearMipmapLinearFilter; x.magFilter = THREE.LinearFilter; x.anisotropy = 4; x.needsUpdate = true;
  return x;
}
