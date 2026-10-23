import * as THREE from 'three';
import { canvas, atlas, make } from '../detail-materials.js';
import { random } from '../materials.js';

// The Sala del Mexuar (x -34..-24, z -20.5..6.5, floor y = 0): the council hall of the Nasrid palaces,
// later a chapel. Modelled from Commons photographs (see public/textures/mexuar/credits.json):
//  - four slender marble columns carrying heavy dark architraves on big muqarnas stucco corbels,
//  - the raised timber lantern with its carved frieze, sloping coving and the sunburst ceiling
//    (radial planks round a carved central boss),
//  - painted lacería ceilings with rib lattices over the side aisles, a wooden carved fascia round the room,
//  - the wooden gallery with turned balusters over the entrance (south) end,
//  - the 16th-century cuerda-seca azulejo dado (rosettes / star tiles), carved stucco bands, Plus Ultra panels,
//  - herringbone brick floor.
const CX = -29, CZ = -7, W = 10, D = 27, T = .65, H = 6.8;
const X0 = CX - W / 2, X1 = CX + W / 2, Z0 = CZ - D / 2, Z1 = CZ + D / 2;
const IX0 = X0 + T / 2, IX1 = X1 - T / 2, IZ0 = Z0 + T / 2, IZ1 = Z1 - T / 2;
// vertical scheme
const Y_CAP = 3.55, Y_BEAM0 = 4.2, Y_BEAM1 = 4.8, Y_AISLE = 4.6, Y_FR1 = 5.7, Y_COVE0 = 5.9, Y_TOP = 6.4;
const COL = [[-31.5, -10], [-26.5, -10], [-31.5, -3], [-26.5, -3]];
const LX0 = -31.5, LX1 = -26.5, LZ0 = -10, LZ1 = -3; // lantern axes (column lines)

const img = async f => { const i = new Image(); i.src = `textures/mexuar/${f}.jpg`; await i.decode(); return i; };

function grain(g, w, h, r, base, dark, light, n = 900) {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < n; i++) {
    const y = r() * h, x = r() * w, l = 20 + r() * w * .5;
    g.strokeStyle = r() < .5 ? dark : light; g.globalAlpha = .06 + r() * .16; g.lineWidth = .6 + r() * 1.8;
    g.beginPath(); g.moveTo(x, y); g.bezierCurveTo(x + l * .3, y + (r() - .5) * 4, x + l * .6, y + (r() - .5) * 4, x + l, y + (r() - .5) * 3); g.stroke();
  }
  g.globalAlpha = 1;
}
function star8(g, cx, cy, R, r = .72, rot = Math.PI / 8) {
  g.beginPath();
  for (let i = 0; i < 16; i++) { const a = rot + i * Math.PI / 8, q = i % 2 ? R * r : R; g[i ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * q, cy + Math.sin(a) * q); }
  g.closePath();
}
function woodCanvas(seed, base = '#3d2515', dark = '#1c0f08', light = '#7a4a28') {
  const c = canvas(512, 512), g = c.getContext('2d'), r = random(seed);
  grain(g, 512, 512, r, base, dark, light); return c;
}
function laceriaCanvas() { // painted lacería: gilt 8-point star, rust/blue pieces on dark walnut, 1 m per repeat
  const c = canvas(512, 512), g = c.getContext('2d'), r = random(31);
  grain(g, 512, 512, r, '#2b190b', '#120a04', '#5a3a1e', 700);
  const S = 512;
  // strapwork: octagon lines
  g.strokeStyle = '#6e4824'; g.lineWidth = 5; g.globalAlpha = .9;
  for (const [x, y] of [[0, 0], [S, 0], [0, S], [S, S], [S / 2, S / 2]]) { star8(g, x, y, S * .5, .62); g.stroke(); }
  g.globalAlpha = 1;
  // corner pieces: blue / rust
  const pieces = [[0, 0, '#1d2c52'], [S, 0, '#1d2c52'], [0, S, '#1d2c52'], [S, S, '#2f4a86']];
  for (const [x, y, col] of pieces) { g.fillStyle = col; star8(g, x, y, S * .21, .55); g.fill(); g.strokeStyle = '#7f6638'; g.lineWidth = 2; g.stroke(); }
  for (const [x, y] of [[S / 2, 0], [S / 2, S], [0, S / 2], [S, S / 2]]) { g.fillStyle = '#5c2a1c'; star8(g, x, y, S * .17, .5, 0); g.fill(); }
  // centre: big gilt star with rust heart
  g.fillStyle = '#8c6e3c'; star8(g, S / 2, S / 2, S * .30, .66); g.fill();
  g.fillStyle = '#5c2a1c'; star8(g, S / 2, S / 2, S * .19, .62); g.fill();
  g.fillStyle = '#1d2c52'; star8(g, S / 2, S / 2, S * .08, .6); g.fill();
  g.strokeStyle = '#2a170a'; g.lineWidth = 3; star8(g, S / 2, S / 2, S * .30, .66); g.stroke();
  // wear
  for (let i = 0; i < 1500; i++) { g.fillStyle = `rgba(20,10,4,${r() * .25})`; g.fillRect(r() * S, r() * S, 1 + r() * 3, 1 + r() * 3); }
  return c;
}
function floorCanvas() { // herringbone brick; lattice (1,1) and (4,0) in brick-width units, 4 units per repeat
  const c = canvas(512, 512), g = c.getContext('2d'), r = random(5), u = 128;
  g.fillStyle = '#7a6a5c'; g.fillRect(0, 0, 512, 512);
  const brick = (x, y, w, h) => {
    for (const ox of [-4, 0, 4]) for (const oy of [-4, 0, 4]) {
      const X = (x + ox) * u, Y = (y + oy) * u;
      if (X > 512 || Y > 512 || X + w * u < 0 || Y + h * u < 0) continue;
      g.fillStyle = `hsl(${18 + r() * 10} ${22 + r() * 12}% ${52 + r() * 14}%)`; g.fillRect(X + 2, Y + 2, w * u - 4, h * u - 4);
    }
  };
  for (let k = -6; k <= 6; k++) for (let m = -3; m <= 3; m++) {
    const sx = m * 4;
    brick(k + sx, k, 2, 1); brick(k + 2 + sx, k - 1, 1, 2);
  }
  for (let i = 0; i < 9000; i++) { g.fillStyle = `rgba(${r() < .5 ? '40,24,16' : '230,200,170'},${r() * .1})`; g.fillRect(r() * 512, r() * 512, 1 + r() * 2, 1 + r() * 2); }
  return c;
}
function plasterCanvas() {
  const c = canvas(512, 512), g = c.getContext('2d'), r = random(17);
  g.fillStyle = '#c9b08a'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 160; i++) { g.fillStyle = `rgba(${r() < .5 ? '120,90,55' : '240,225,195'},${.03 + r() * .06})`; g.beginPath(); g.ellipse(r() * 512, r() * 512, 20 + r() * 80, 10 + r() * 50, r() * 3, 0, 7); g.fill(); }
  for (let i = 0; i < 6000; i++) { g.fillStyle = `rgba(${r() < .5 ? '70,50,30' : '250,240,220'},${r() * .1})`; g.fillRect(r() * 512, r() * 512, 1 + r() * 2, 1 + r() * 2); }
  return c;
}
function marbleCanvas() {
  const c = canvas(256, 512), g = c.getContext('2d'), r = random(23);
  g.fillStyle = '#efe6d2'; g.fillRect(0, 0, 256, 512);
  for (let i = 0; i < 60; i++) { g.strokeStyle = `rgba(110,100,92,${.05 + r() * .18})`; g.lineWidth = .5 + r() * 1.5; g.beginPath(); let x = r() * 256, y = 0; g.moveTo(x, y); for (let k = 0; k < 12; k++) { x += (r() - .5) * 26; y += 44; g.lineTo(x, y); } g.stroke(); }
  return c;
}
function starTileCanvas() { // black / blue / green / white eight-point star tiles of the entrance end
  const c = canvas(256, 256), g = c.getContext('2d'), r = random(41);
  g.fillStyle = '#ecebe2'; g.fillRect(0, 0, 256, 256);
  const cols = ['#1d1c24', '#2c5aa8', '#2c8a6a', '#e9e7da'];
  for (let j = 0; j < 2; j++) for (let i = 0; i < 2; i++) {
    const x = 64 + i * 128, y = 64 + j * 128;
    g.fillStyle = cols[(i + j * 2 + (j ? 1 : 0)) % 4]; star8(g, x, y, 60, .6, 0); g.fill();
    g.strokeStyle = '#f4f2ea'; g.lineWidth = 3; g.stroke();
    g.fillStyle = (i + j) % 2 ? '#c49a2a' : '#2f6a9a'; g.save(); g.translate(x + 64, y); g.rotate(Math.PI / 4); g.fillRect(-12, -12, 24, 24); g.restore();
    g.save(); g.translate(x, y + 64); g.rotate(Math.PI / 4); g.fillRect(-12, -12, 24, 24); g.restore();
  }
  for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(255,255,255,${r() * .08})`; g.fillRect(r() * 256, r() * 256, 2, 2); }
  return c;
}
function plusUltraCanvas() { // the imperial-device tile panel: Pillars of Hercules and PLVS VLTRA on blue ground
  const c = canvas(256, 400), g = c.getContext('2d'), r = random(53);
  g.fillStyle = '#ece8da'; g.fillRect(0, 0, 256, 400);
  g.fillStyle = '#244f98'; g.fillRect(14, 14, 228, 372);
  g.strokeStyle = '#d6b055'; g.lineWidth = 3; g.strokeRect(26, 26, 204, 348);
  g.fillStyle = '#16264a'; g.fillRect(34, 34, 188, 332);
  for (let i = 0; i < 18; i++) { g.strokeStyle = '#d8d3c0'; g.lineWidth = 2; g.beginPath(); g.moveTo(40, 52 + i * 17); g.bezierCurveTo(90, 38 + i * 17, 150, 66 + i * 17, 216, 52 + i * 17); g.stroke(); }
  g.fillStyle = '#e8e2cc'; g.fillRect(104, 90, 48, 210); g.fillStyle = '#d6b055'; g.fillRect(96, 82, 64, 16); g.fillRect(96, 292, 64, 16);
  g.fillStyle = '#b8b09a'; g.fillRect(104, 90, 12, 210);
  g.fillStyle = '#e8e2cc'; g.beginPath(); g.moveTo(54, 140); g.bezierCurveTo(120, 120, 150, 190, 200, 170); g.lineTo(200, 190); g.bezierCurveTo(150, 215, 110, 150, 54, 165); g.fill();
  g.fillStyle = '#16264a'; g.font = 'bold 15px serif'; g.textAlign = 'center'; g.fillText('PLVS', 76, 156); g.fillText('VLTRA', 172, 188);
  g.fillStyle = '#d6b055'; g.beginPath(); g.arc(128, 330, 14, 0, 7); g.fill();
  for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(255,255,255,${r() * .07})`; g.fillRect(r() * 256, r() * 400, 2, 2); }
  return c;
}
function capitalCanvas() {
  const c = canvas(256, 256), g = c.getContext('2d'), r = random(61);
  g.fillStyle = '#b9955a'; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 8; i++) {
    const x = i * 32 + 16; g.fillStyle = i % 2 ? '#2f4f90' : '#e3dcc6';
    g.beginPath(); g.moveTo(x, 250); g.bezierCurveTo(x - 24, 170, x - 16, 90, x, 12); g.bezierCurveTo(x + 16, 90, x + 24, 170, x, 250); g.fill();
    g.strokeStyle = '#6a4a22'; g.lineWidth = 2; g.stroke();
  }
  for (let i = 0; i < 4000; i++) { g.fillStyle = `rgba(60,40,20,${r() * .12})`; g.fillRect(r() * 256, r() * 256, 2, 2); }
  return c;
}
function doorCanvas() {
  const c = canvas(256, 512), g = c.getContext('2d'), r = random(71);
  grain(g, 256, 512, r, '#4a2c18', '#20120a', '#8a5a32', 500);
  g.strokeStyle = '#1c0f08'; g.lineWidth = 4;
  for (let j = 0; j < 4; j++) for (let i = 0; i < 2; i++) { const x = 20 + i * 118, y = 22 + j * 122; g.strokeRect(x, y, 100, 106); star8(g, x + 50, y + 53, 40, .6); g.stroke(); g.fillStyle = '#b08a44'; star8(g, x + 50, y + 53, 14, .6); g.fill(); }
  return c;
}

export async function materials(M) {
  const [dado, dadoB, stucco, band, inscr, muq] = await Promise.all(['mex-dado', 'mex-dado-border', 'mex-stucco', 'mex-lattice', 'mex-inscr', 'mex-muq'].map(img));
  const full = [0, 0, 1, 1];
  // cuerda-seca dado: one lattice period ~1.30 x 1.22 m (photograph rectified by tools: textures.py)
  make(M, 'mexDado', atlas(dado, full), 1.3, 1.22, { rough: .36, relief: .0012, ambient: .8 });
  make(M, 'mexDadoBorder', atlas(dadoB, full), 2.3, .14, { rough: .4, relief: .001, ambient: .8 });
  make(M, 'mexStarTile', starTileCanvas(), .9, .9, { rough: .38, relief: .001, ambient: .8 });
  make(M, 'mexStucco', atlas(stucco, full), .78, .78, { relief: .03, rough: .9, ambient: 1.0, color: 0xf2e6d2 });
  make(M, 'mexLattice', atlas(band, full), 5.4, .6, { relief: .02, rough: .9, ambient: 1.0, color: 0xf3e8d4 });
  make(M, 'mexInscr', atlas(inscr, full), 5.4, .26, { relief: .02, rough: .9, ambient: 1.0, color: 0xf5ecda });
  make(M, 'mexMuq', atlas(muq, full), .5, .5, { relief: .03, rough: .9, ambient: 1.0, color: 0xf3e6cf });
  make(M, 'mexMuqBlue', atlas(muq, full), .5, .5, { relief: .03, rough: .9, ambient: 1.0, color: 0x8c93b4 });
  make(M, 'mexPlaster', plasterCanvas(), 3, 3, { relief: .004, rough: .95, ambient: 1.0 });
  make(M, 'mexFloor', floorCanvas(), .6, .6, { relief: .006, rough: .85, ambient: 1.0 });
  make(M, 'mexMarble', marbleCanvas(), .6, 1.2, { relief: 0, rough: .35, ambient: 1.0 });
  make(M, 'mexCapital', capitalCanvas(), .5, .5, { relief: .006, rough: .7, ambient: 1.0 });
  make(M, 'mexWood', woodCanvas(3), 1.2, 1.2, { relief: .006, rough: .62, ambient: 1.0 });
  make(M, 'mexWoodWarm', woodCanvas(9, '#6a3f20', '#2e1a0c', '#a4693a'), 1.2, 1.2, { relief: .006, rough: .55, ambient: .95 });
  make(M, 'mexLaceria', laceriaCanvas(), 1, 1, { relief: .012, rough: .6, ambient: 1.0, color: 0xe0d0bc });
  make(M, 'mexFascia', laceriaCanvas(), .55, .55, { relief: .012, rough: .6, ambient: 1.0, color: 0xe0d0bc });
  make(M, 'mexDoor', doorCanvas(), 1.7, 2.5, { relief: .01, rough: .7, ambient: .8 });
  make(M, 'mexPlus', plusUltraCanvas(), 1, 1.56, { relief: .001, rough: .38, ambient: .8 });
  make(M, 'mexOuter', plasterCanvas(), 3, 3, { relief: .006, rough: .95, ambient: 1.0, color: 0xe8d3b6 });
  make(M, 'mexOuterTrim', plasterCanvas(), 3, 3, { relief: .006, rough: .95, ambient: 1.0, color: 0xf6ead4 });
  make(M, 'mexPlinth', plasterCanvas(), 3, 3, { relief: .01, rough: .98, ambient: 1.0, color: 0xa8957c });
  make(M, 'mexLime', plasterCanvas(), 3, 3, { relief: .004, rough: .95, ambient: 1.0, color: 0xf6f0e2 });
  // pierced window grille (celosía) used for the small windows of the oratory
  {
    const c = canvas(256, 256), g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256); g.fillStyle = '#fff';
    for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) { star8(g, 32 + i * 64, 32 + j * 64, 22, .62); g.fill(); g.fillRect(i * 64 + 60, j * 64 + 60, 8, 8); }
    const t2 = new THREE.CanvasTexture(c); t2.wrapS = t2.wrapT = THREE.RepeatWrapping; t2.repeat.set(1 / .5, 1 / .5);
    const m = new THREE.MeshStandardMaterial({ color: 0xfff6e0, roughness: .9, side: THREE.DoubleSide, alphaMap: t2, alphaTest: .5, emissive: 0xfff2d0, emissiveIntensity: .5 });
    m.name = 'mexGrille'; m.userData = { scale: 1, interiorAmbient: .9 }; M.mexGrille = m;
    const m2 = new THREE.MeshStandardMaterial({ color: 0xe9e0c8, roughness: .9, side: THREE.DoubleSide, emissive: 0xfff2d0, emissiveIntensity: .35 }); m2.name = 'mexGlow'; m2.userData = { scale: 1, interiorAmbient: .9 }; M.mexGlow = m2;
  }
  // the oratory is lit only by its windows: brighter clones of the wall materials
  for (const [src, k] of [['mexLime', 1.55], ['mexStucco', 1.7], ['mexLattice', 1.7], ['mexInscr', 1.7], ['mexFloor', 1.6], ['mexMuq', 1.5], ['mexPlaster', 1.4], ['mexMuqBlue', 2.7], ['mexLaceria', 1.7], ['mexFascia', 1.6], ['mexWood', 1.8]]) {
    const m = M[src].clone(); m.name = 'mexOr' + src.slice(3); m.userData = { ...M[src].userData }; m.color.multiplyScalar(k); M[m.name] = m;
  }
  // sunburst boards: vertex-coloured walnut / amber planks
  const sun = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .5, vertexColors: true, side: THREE.DoubleSide });
  sun.name = 'mexSun'; sun.emissive = new THREE.Color(0x3a1507); sun.emissiveIntensity = 1; sun.userData = { scale: 1, interiorAmbient: 1 };
  sun.map = M.mexWood.map.clone(); sun.map.repeat.set(1 / 1.2, 1 / 1.2); sun.map.needsUpdate = true; M.mexSun = sun;
  const gilt = new THREE.MeshStandardMaterial({ color: 0xc89a48, roughness: .38, metalness: .35, side: THREE.DoubleSide });
  gilt.name = 'mexGilt'; gilt.userData = { scale: 1, interiorAmbient: .95 }; M.mexGilt = gilt;
}

// ---- geometry helpers ---------------------------------------------------------------------------------
function flat(pts, uvs, normal) { // triangles list (flat arrays)
  const g = new THREE.BufferGeometry();
  const n = []; for (let i = 0; i < pts.length / 3; i++) n.push(...normal);
  g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(n, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  return g;
}
function ceilingQuad(b, mat, x0, z0, x1, z1, y) {
  const p = [x0, y, z0, x1, y, z0, x1, y, z1, x0, y, z0, x1, y, z1, x0, y, z1];
  const uv = []; for (let i = 0; i < 18; i += 3) uv.push(p[i], p[i + 2]);
  b.unique(flat(p, uv, [0, -1, 0]), mat);
}
function archShape(w, spring, rise, top, margin) {
  const s = new THREE.Shape(), hw = w / 2 + margin;
  s.moveTo(-hw, spring); s.lineTo(-hw, top); s.lineTo(hw, top); s.lineTo(hw, spring); s.lineTo(w / 2, spring);
  for (let i = 0; i <= 48; i++) { const a = Math.PI * i / 48, rr = Math.sin(a * 9) ** 2 * .03; s.lineTo(Math.cos(a) * (w / 2 - rr), spring + Math.sin(a) ** .82 * rise - rr); }
  s.closePath(); return s;
}
function archPiece(w, spring, rise, top, depth, margin) {
  const g = new THREE.ExtrudeGeometry(archShape(w, spring, rise, top, margin), { depth, bevelEnabled: false, curveSegments: 12 });
  g.translate(0, 0, -depth / 2); g.clearGroups(); return g;
}

// sunburst: radial planks from the centre to the border of the rectangle, with raised ribs
function sunburst(cx, cz, hx, hz, y, n) {
  const ang = [], corners = [Math.atan2(hz, hx), Math.atan2(hz, -hx), Math.atan2(-hz, -hx), Math.atan2(-hz, hx)];
  for (let i = 0; i < n; i++) ang.push(i / n * Math.PI * 2 - Math.PI);
  for (const c of corners) ang.push(c);
  ang.sort((a, b) => a - b);
  const P = a => { const ca = Math.cos(a), sa = Math.sin(a); const t = Math.min(hx / Math.max(1e-6, Math.abs(ca)), hz / Math.max(1e-6, Math.abs(sa))); return [cx + ca * t, cz + sa * t]; };
  const pos = [], uv = [], col = [], r = random(77);
  const push = (x, yy, z, c) => { pos.push(x, yy, z); uv.push(x, z); col.push(c[0], c[1], c[2]); };
  const tints = [[.95, .55, .3], [.82, .45, .23], [.9, .5, .27], [.7, .36, .18], [1.0, .62, .34]];
  for (let k = 0; k < ang.length; k++) {
    const a = ang[k], bb = ang[(k + 1) % ang.length] + (k + 1 === ang.length ? Math.PI * 2 : 0);
    const c = tints[Math.floor(r() * tints.length)].map(v => v * (.85 + r() * .3));
    const A = P(a), B = P(bb);
    push(cx, y, cz, c); push(A[0], y, A[1], c); push(B[0], y, B[1], c);
  }
  // ribs
  const dark = [.34, .17, .08];
  for (let k = 0; k < n; k += 3) {
    const a = k / n * Math.PI * 2 - Math.PI, E = P(a), ca = Math.cos(a), sa = Math.sin(a), wd = .007;
    const r0 = .4, x0 = cx + ca * r0, z0 = cz + sa * r0, nx = -sa * wd, nz = ca * wd, yy = y - .012;
    for (const [px, pz] of [[x0 - nx, z0 - nz], [E[0] - nx, E[1] - nz], [E[0] + nx, E[1] + nz], [x0 - nx, z0 - nz], [E[0] + nx, E[1] + nz], [x0 + nx, z0 + nz]]) push(px, yy, pz, dark);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(pos.map((v, i) => i % 3 === 1 ? -1 : 0), 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  return g;
}
function boss(radius = .34, depth = .42) { // carved central rosette hanging from the sunburst
  const prof = [[0, -depth], [.05, -depth + .02], [.09, -depth + .1], [.07, -depth + .16], [.15, -depth + .2], [.2, -depth + .27], [.18, -depth + .31], [.27, -depth + .34], [.32, -depth + .39], [radius, -.04], [radius, 0]];
  const g = new THREE.LatheGeometry(prof.map(p => new THREE.Vector2(p[0], p[1])), 48);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), r = Math.hypot(x, z), a = Math.atan2(z, x), k = 1 + .11 * Math.cos(a * 16) * Math.min(1, r / .2); p.setX(i, x * k); p.setZ(i, z * k); }
  g.computeVertexNormals();
  const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, p.getX(i), p.getZ(i));
  return g;
}
function baluster() { // turned baluster, 0.8 m
  const prof = [[.0, 0], [.028, 0], [.03, .03], [.02, .06], [.04, .1], [.026, .2], [.034, .3], [.044, .38], [.034, .46], [.022, .52], [.036, .64], [.03, .7], [.02, .72], [.0, .72]];
  const g = new THREE.LatheGeometry(prof.map(p => new THREE.Vector2(p[0], p[1])), 8);
  const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * .3, uv.getY(i) * .7);
  return g;
}
function cell() { // one muqarnas cell: pointed-arch niche profile, extruded
  const s = new THREE.Shape(); s.moveTo(-.055, 0); s.lineTo(.055, 0); s.lineTo(.055, .075); s.quadraticCurveTo(.045, .125, 0, .15); s.quadraticCurveTo(-.045, .125, -.055, .075); s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: .08, bevelEnabled: true, bevelSize: .008, bevelThickness: .01, bevelSegments: 1, curveSegments: 5 });
  g.translate(0, 0, -.08); g.clearGroups(); return g;
}
function khatam(r, depth) { const s = new THREE.Shape(); for (let i = 0; i < 16; i++) { const a = Math.PI / 8 * i, q = i % 2 ? r * .7 : r; s[i ? 'lineTo' : 'moveTo'](Math.cos(a) * q, Math.sin(a) * q); } s.closePath(); const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false }); g.rotateX(Math.PI / 2); g.clearGroups(); return g; }

export function build(b, ctx) {
  b.zone = 'mexuar';
  const off = b.offset;
  const WALLS = {
    S: { axis: 'x', f: Z1, inward: -1, u0: X0 - T / 2, u1: X1 + T / 2, open: [[CX, 2.7, 1.4]] },
    N: { axis: 'x', f: Z0, inward: 1, u0: X0 - T / 2, u1: X1 + T / 2, open: [[CX, 2.3, 1.2]] },
    W: { axis: 'z', f: X0, inward: 1, u0: Z0, u1: Z1, open: [] },
    E: { axis: 'z', f: X1, inward: -1, u0: Z0, u1: Z1, open: [[CZ, 3, 1.56]] },
  };
  const fi = w => w.f + w.inward * T / 2;
  const segs = (w, a = w.u0, c = w.u1) => {
    let list = [[a, c]];
    for (const [uc, ow] of w.open) {
      const o0 = uc - ow / 2, o1 = uc + ow / 2, nl = [];
      for (const [p, q] of list) { if (o1 <= p || o0 >= q) nl.push([p, q]); else { if (o0 > p) nl.push([p, o0]); if (o1 < q) nl.push([o1, q]); } }
      list = nl;
    }
    return list;
  };
  // slab t0..t1 measured into the room from the inner face, along u0..u1, y..y+h
  const slab = (w, u0, u1, y, h, t0, t1, mat, block = false) => {
    const fc = fi(w) + w.inward * (t0 + t1) / 2, uc = (u0 + u1) / 2;
    if (w.axis === 'x') b.box(uc, y, fc, u1 - u0, h, t1 - t0, mat, 0, block);
    else b.box(fc, y, uc, u1 - u0, h, t1 - t0, mat, Math.PI / 2, block);
  };
  const layer = (w, y, h, t0, t1, mat, from, to) => { for (const [p, q] of segs(w, from ?? w.u0 + T / 2, to ?? w.u1 - T / 2)) slab(w, p, q, y, h, t0, t1, mat); };
  const full = (w, y, h, t0, t1, mat, from, to) => slab(w, from ?? w.u0 + T / 2, to ?? w.u1 - T / 2, y, h, t0, t1, mat);

  // ---- floor
  b.floor(CX, CZ, W, D, 0, 'mexFloor');

  // ---- shell with the three passages
  for (const k of ['S', 'N', 'W', 'E']) {
    const w = WALLS[k];
    for (const [p, q] of segs(w)) {
      const uc = (p + q) / 2;
      if (w.axis === 'x') b.box(uc, 0, w.f, q - p, H, T, 'mexPlaster', 0, true); else b.box(w.f, 0, uc, q - p, H, T, 'mexPlaster', Math.PI / 2, true);
    }
    for (const [uc, ow, rise] of w.open) {
      const spring = 2.25, top = Math.min(H, spring + rise + .5);
      const rot = w.axis === 'x' ? 0 : Math.PI / 2, pos = w.axis === 'x' ? [uc, 0, w.f] : [w.f, 0, uc];
      b.unique(archPiece(ow, spring, rise, H, T, 0), 'mexPlaster', pos, rot);
      b.unique(archPiece(ow, spring, rise, top, T + .08, .42), 'mexStucco', pos, rot);
      // jamb reveals (stucco-faced cheeks) so the passage reads as thick
      const [jx, jz] = w.axis === 'x' ? [1, 0] : [0, 1];
      void jx; void jz;
    }
  }

  // ---- dado: field tiles + borders + inscription cornice, then plain plaster, carved lattice frieze, wooden fascia
  for (const k of ['S', 'N', 'W', 'E']) {
    const w = WALLS[k];
    const starPart = (k === 'S' || k === 'N');
    const from = w.u0 + T / 2, to = w.u1 - T / 2;
    if (starPart) {
      layer(w, .12, 1.28, 0, .03, 'mexStarTile');
    } else {
      // rosette dado over the long walls; the entrance end (z>0) uses the star tiles
      const zc = 0;
      for (const [p, q] of segs(w, from, to)) {
        const a = Math.max(p, from), c = Math.min(q, to);
        if (c <= zc) slab(w, a, c, .14, 1.22, 0, .03, 'mexDado');
        else if (a >= zc) slab(w, a, c, .12, 1.28, 0, .03, 'mexStarTile');
        else { slab(w, a, zc, .14, 1.22, 0, .03, 'mexDado'); slab(w, zc, c, .12, 1.28, 0, .03, 'mexStarTile'); }
      }
      layer(w, 0, .14, 0, .03, 'mexDadoBorder'); layer(w, 1.36, .14, 0, .03, 'mexDadoBorder');
    }
    if (starPart) { layer(w, 0, .12, 0, .03, 'mexDadoBorder'); layer(w, 1.4, .1, 0, .03, 'mexDadoBorder'); }
    layer(w, 1.5, .26, 0, .045, 'mexInscr');
    layer(w, 3.4, .6, 0, .05, 'mexLattice');
    layer(w, 4.0, .08, 0, .11, 'mexWoodWarm');
    full(w, Y_BEAM0 - .05, .46, 0, .13, 'mexFascia');
    full(w, Y_AISLE, .1, 0, .24, 'mexWood');
  }

  // ---- west facade (outside): battered plinth, string course, pilasters, framed shuttered windows, eaves
  {
    const w = WALLS.W, ZA = Z0 + .2, ZB = Z1 - .2, o = -T;
    slab(w, ZA, ZB, 0, H, o - .035, o, 'mexOuter');
    slab(w, ZA, ZB, 0, .55, o - .12, o - .035, 'mexPlinth'); slab(w, ZA, ZB, .55, .08, o - .16, o - .035, 'mexOuterTrim');
    slab(w, ZA, ZB, 4.55, .12, o - .2, o - .035, 'mexOuterTrim'); slab(w, ZA, ZB, 4.67, .08, o - .14, o - .035, 'mexPlinth');
    slab(w, ZA, ZB, H - .38, .14, o - .3, o - .035, 'mexOuterTrim'); slab(w, ZA, ZB, H - .24, .24, o - .22, o - .035, 'mexPlinth');
    for (const u of [Z0 + .3, -14, -7, 0, Z1 - .3]) slab(w, u - .22, u + .22, .63, H - 1.1, o - .12, o - .035, 'mexOuterTrim');
    for (const u of [-17.2, -10.4, -3.6, 3.2]) {
      slab(w, u - .52, u + .52, 3.0, 1.55, o - .09, o - .035, 'mexPlinth');
      slab(w, u - .38, u + .38, 3.12, 1.3, o - .125, o - .09, 'mexOrFascia');
      slab(w, u - .34, u + .34, 3.16, 1.22, o - .15, o - .125, 'mexDoor');
    }
    for (const u of [-14.4, -7, -0.2]) { // low shuttered windows with stucco frames
      slab(w, u - .45, u + .45, 1.35, 1.1, o - .08, o - .035, 'mexPlinth'); slab(w, u - .35, u + .35, 1.43, .94, o - .11, o - .08, 'mexDoor');
    }
  }

  // ---- Plus Ultra tile panels, shuttered windows
  for (const [k, uc] of [['W', -14], ['W', 1.2], ['E', -14], ['E', 1.2]]) slab(WALLS[k], uc - .5, uc + .5, .45, 1.6, .03, .06, 'mexPlus');
  for (const s of [-1, 1]) slab(WALLS.N, CX + s * 2.6 - .85, CX + s * 2.6 + .85, 0, 2.5, 0, .06, 'mexDoor');
  for (const uc of [-17, -4.5]) slab(WALLS.W, uc - .5, uc + .5, 2.1, 1.1, .0, .07, 'mexDoor');

  // ---- carved blind arches (stucco niches) between the dado frieze and the lattice frieze
  const niche = (w, uc, ww, y0) => {
    const rot = w.axis === 'x' ? 0 : Math.PI / 2, fc = fi(w) + w.inward * .02, spring = y0 + .6, rise = ww * .5;
    const place = (g, mat, d) => { const pos = w.axis === 'x' ? [uc, y0 - 1.0, fc + w.inward * d / 2] : [fc + w.inward * d / 2, y0 - 1.0, uc]; b.unique(g, mat, pos, rot); };
    const mk = (hw, sp, r, d) => { const s = new THREE.Shape(); s.moveTo(-hw, sp - .6); s.lineTo(-hw, sp); for (let i = 0; i <= 40; i++) { const a = Math.PI - Math.PI * i / 40; s.lineTo(Math.cos(a) * hw, sp + Math.sin(a) ** .85 * r); } s.lineTo(hw, sp - .6); s.closePath(); const g = new THREE.ExtrudeGeometry(s, { depth: d, bevelEnabled: false, curveSegments: 6 }); g.clearGroups(); return g; };
    void place;
    const frame = mk(ww / 2 + .13, spring, rise + .13, .045), inner = mk(ww / 2, spring, rise, .07);
    const base = w.axis === 'x' ? [uc, y0 - 1.0 - 1.0 + 1.0, 0] : null; void base;
    const add = (g, mat, d) => { const pos = w.axis === 'x' ? [uc, 0, fi(w) + w.inward * (d)] : [fi(w) + w.inward * d, 0, uc]; const r2 = w.axis === 'x' ? (w.inward > 0 ? 0 : Math.PI) : (w.inward > 0 ? Math.PI / 2 : -Math.PI / 2); b.unique(g, mat, pos, r2); };
    add(frame, 'mexLattice', .0); add(inner, 'mexStucco', .0);
  };
  for (const [k, uc] of [['W', -17.5], ['W', -11], ['W', -3], ['W', 3.5], ['E', -17.5], ['E', -12.2], ['E', -1.8], ['E', 3.5]]) niche(WALLS[k], uc, 1.3, 1.85);

  // ---- columns: marble shaft with Attic base, painted capital, abacus
  const cap = cell();
  for (const [x, z] of COL) {
    b.cylinder(x, 0, z, .3, .06, 'mexMarble'); b.cylinder(x, .06, z, .26, .1, 'mexMarble'); b.cylinder(x, .16, z, .22, .06, 'mexMarble');
    b.cylinder(x, .22, z, .165, Y_CAP - .22 - .5, 'mexMarble', .135, 20);
    b.cylinder(x, Y_CAP - .3, z, .18, .06, 'mexMarble'); b.cylinder(x, Y_CAP - .24, z, .15, .05, 'mexGilt');
    b.cylinder(x, Y_CAP - .19, z, .145, .19, 'mexCapital', .27, 16); // bell
    b.box(x, Y_CAP, z, .62, .14, .62, 'mexCapital');
    b.nav.box(x + off[0], z + off[2], .5, .5, off[1], off[1] + Y_BEAM0);
    // stucco corbel: six tiers of muqarnas cells, alternate tiers turned 45 degrees, widening upward under the architrave
    for (let t = 0; t < 7; t++) {
      const th = 0, hh = .30 + .12 * t, y = Y_CAP + .13 + t * .095, n = Math.max(3, Math.round(2 * hh / .12));
      b.box(x, y, z, 2 * hh - .06, .12, 2 * hh - .06, 'mexMuqBlue', th);
      for (let k = 0; k < 4; k++) {
        const ph = th + k * Math.PI / 2, sx = Math.sin(ph), cz = Math.cos(ph), tx = cz, tz = -sx;
        for (let i = 0; i < n; i++) {
          const u = -hh + (i + .5) * (2 * hh / n), sc = [1.1, 1.25 + (t % 3) * .08, 1.1];
          b.add(cap, 'mexMuq', [x + sx * hh + tx * u, y, z + cz * hh + tz * u], sc, ph);
        }
      }
    }
  }

  // ---- architraves (dark carved timber) and the lantern frieze
  for (const z of [LZ0, LZ1]) { b.box((LX0 + LX1) / 2, Y_BEAM0, z, LX1 - LX0 + .9, Y_BEAM1 - Y_BEAM0, .5, 'mexWood'); for (const s of [-1, 1]) b.box((LX0 + LX1) / 2, Y_BEAM0 + .12, z + s * .255, LX1 - LX0 + .9, .03, .02, 'mexGilt'); b.box((LX0 + LX1) / 2, Y_BEAM0 - .02, z, LX1 - LX0 + .9, .06, .6, 'mexWoodWarm'); }
  for (const x of [LX0, LX1]) { b.box(x, Y_BEAM0, (LZ0 + LZ1) / 2, .5, Y_BEAM1 - Y_BEAM0, LZ1 - LZ0 + .9, 'mexWood'); for (const s of [-1, 1]) b.box(x + s * .255, Y_BEAM0 + .12, (LZ0 + LZ1) / 2, .02, .03, LZ1 - LZ0 + .9, 'mexGilt'); b.box(x, Y_BEAM0 - .02, (LZ0 + LZ1) / 2, .6, .06, LZ1 - LZ0 + .9, 'mexWoodWarm'); }
  // stucco-faced architraves between the corbels (outer faces towards the aisles)
  for (const z of [LZ0, LZ1]) b.box((LX0 + LX1) / 2, Y_BEAM0, z + (z === LZ0 ? -1 : 1) * .262, 2.9, .6, .025, 'mexLattice');
  for (const x of [LX0, LX1]) b.box(x + (x === LX0 ? -1 : 1) * .262, Y_BEAM0, (LZ0 + LZ1) / 2, .025, .6, 4.9, 'mexLattice');
  // frieze walls of the lantern: inscription + lattice, on both faces; cornice above
  const frz = (x, z, w, d, rot) => { // centre, size along local x (w) and thickness d
    b.box(x, Y_BEAM1, z, w, Y_FR1 - Y_BEAM1, d, 'mexPlaster', rot);
    for (const s of [-1, 1]) {
      const dx = rot ? s * (d / 2 + .012) : 0, dz = rot ? 0 : s * (d / 2 + .012);
      b.box(x + dx, Y_BEAM1 + .02, z + dz, w - .1, .26, .025, 'mexInscr', rot);
      b.box(x + dx, Y_BEAM1 + .3, z + dz, w - .1, .6, .025, 'mexLattice', rot);
    }
    b.box(x, Y_FR1, z, w + .16, .14, d + .22, 'mexWood', rot);
    b.box(x, Y_FR1 + .14, z, w + .06, .05, d + .12, 'mexWoodWarm', rot);
  };
  const LL = LX1 - LX0 + .5, LD = LZ1 - LZ0 + .5;
  frz((LX0 + LX1) / 2, LZ0, LL, .42, 0); frz((LX0 + LX1) / 2, LZ1, LL, .42, 0);
  frz(LX0, (LZ0 + LZ1) / 2, LD, .42, Math.PI / 2); frz(LX1, (LZ0 + LZ1) / 2, LD, .42, Math.PI / 2);

  // ---- lantern ceiling: coving boards + sunburst
  const ix0 = LX0 + .21, ix1 = LX1 - .21, iz0 = LZ0 + .21, iz1 = LZ1 - .21, jx0 = ix0 + .55, jx1 = ix1 - .55, jz0 = iz0 + .55, jz1 = iz1 - .55;
  const cove = (ax, az, bx, bz, cx2, cz2, dx2, dz2, ya, yb) => {
    const p = [ax, ya, az, bx, ya, bz, cx2, yb, cz2, ax, ya, az, cx2, yb, cz2, dx2, yb, dz2], uv = [];
    for (let i = 0; i < 18; i += 3) uv.push(p[i] + p[i + 1] * .2, p[i + 2]);
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.computeVertexNormals(); b.unique(g, 'mexWoodWarm');
  };
  const yc0 = Y_COVE0 + .0, yc1 = Y_TOP;
  cove(ix0, iz0, ix1, iz0, jx1, jz0, jx0, jz0, yc0, yc1); cove(ix0, iz1, ix1, iz1, jx1, jz1, jx0, jz1, yc0, yc1);
  cove(ix0, iz0, ix0, iz1, jx0, jz1, jx0, jz0, yc0, yc1); cove(ix1, iz0, ix1, iz1, jx1, jz1, jx1, jz0, yc0, yc1);
  // vertical inner faces of the lantern frieze are the painted plaster above; boards under the cornice
  const smx = (jx0 + jx1) / 2, smz = (jz0 + jz1) / 2;
  b.unique(sunburst(smx, smz, (jx1 - jx0) / 2, (jz1 - jz0) / 2, Y_TOP, 96), 'mexSun');
  b.unique(boss(), 'mexWoodWarm', [smx, Y_TOP, smz]);
  b.unique(boss(.2, .3), 'mexGilt', [smx, Y_TOP - .03, smz]);
  // gilt battens round the border of the sunburst
  for (const [x, z, w, d] of [[smx, jz0, jx1 - jx0 + .06, .06], [smx, jz1, jx1 - jx0 + .06, .06], [jx0, smz, .06, jz1 - jz0], [jx1, smz, .06, jz1 - jz0]]) b.box(x, Y_TOP - .06, z, w, .06, d, 'mexGilt');

  // ---- aisle ceilings (painted lacería with rib lattice) and cross beams
  const rects = [[IX0, IZ0, LX0 - .25, IZ1], [LX1 + .25, IZ0, IX1, IZ1], [LX0 - .25, IZ0, LX1 + .25, LZ0 - .25], [LX0 - .25, LZ1 + .25, LX1 + .25, IZ1]];
  for (const [a, c, d, e] of rects) {
    ceilingQuad(b, 'mexLaceria', a, c, d, e, Y_AISLE);
    for (let x = Math.ceil(a); x <= d; x++) if (x > a + .1 && x < d - .1) b.box(x, Y_AISLE - .09, (c + e) / 2, .07, .09, e - c, 'mexWood');
    for (let z = Math.ceil(c); z <= e; z++) if (z > c + .1 && z < e - .1) b.box((a + d) / 2, Y_AISLE - .09, z, d - a, .09, .07, 'mexWood');
  }
  for (const z of [LZ0, LZ1]) { b.box((IX0 + LX0 - .25) / 2, Y_BEAM0 + .1, z, LX0 - .25 - IX0, .5, .34, 'mexWood'); b.box((IX1 + LX1 + .25) / 2, Y_BEAM0 + .1, z, IX1 - LX1 - .25, .5, .34, 'mexWood'); }
  for (const x of [LX0, LX1]) { b.box(x, Y_BEAM0 + .1, (IZ0 + LZ0 - .25) / 2, .34, .5, LZ0 - .25 - IZ0, 'mexWood'); b.box(x, Y_BEAM0 + .1, (IZ1 + LZ1 + .25) / 2, .34, .5, IZ1 - LZ1 - .25, 'mexWood'); }
  // carved canes (brackets) where the cross beams meet the walls
  for (const z of [LZ0, LZ1]) for (const [x, s] of [[IX0, 1], [IX1, -1]]) for (let i = 0; i < 3; i++) b.box(x + s * (.08 + i * .06), Y_BEAM0 - .1 - (2 - i) * .0 + i * .0 - .18 + i * .1, z, .16 - i * .02, .16, .3 - i * .04, 'mexWoodWarm');

  // ---- gallery over the entrance (south) end: carved fascia, deck, turned balusters, posts
  const gz0 = 3.7, gz1 = IZ1, gy = 3.35;
  b.box(CX, gy - .55, gz0, W - T, .55, .22, 'mexFascia');
  b.box(CX, gy - .62, gz0, W - T, .07, .3, 'mexGilt');
  b.box(CX, gy - .12, (gz0 + gz1) / 2, W - T, .12, gz1 - gz0, 'mexWood');
  b.box(CX, gy, (gz0 + gz1) / 2, W - T, .03, gz1 - gz0, 'mexWoodWarm');
  const bal = baluster();
  for (let x = IX0 + .1; x < IX1 - .05; x += .14) b.add(bal, 'mexWoodWarm', [x, gy + .03, gz0 + .06], [1, 1.0, 1], 0);
  b.box(CX, gy + .75, gz0 + .06, W - T, .09, .13, 'mexGilt'); b.box(CX, gy + .03, gz0 + .06, W - T, .05, .13, 'mexGilt');
  for (const x of [CX - 3.2, CX + 3.2]) {
    b.cylinder(x, 0.0, gz0 + .06, .09, gy - .55, 'mexMarble', .075, 12);
    b.cylinder(x, gy - .62, gz0 + .06, .12, .08, 'mexCapital', .16, 12);
    b.cylinder(x, gy + .03, gz0 + .06, .06, Y_AISLE - gy - .03, 'mexMarble', .06, 10);
    b.nav.box(x + off[0], gz0 + .06 + off[2], .2, .2, off[1], off[1] + gy);
  }
  // gallery back wall: carved lattice panel
  slab(WALLS.S, IX0, IX1, gy + .1, 1.0, 0, .04, 'mexStucco');

  oratory(b, off, slab, layer, full, fi, segs, WALLS);

  // ---- roof over the hall (lantern rises above the aisle ceiling)
  b.roof(CX, CZ, W + 1, D + 1, H + .2, 2);
}

// ---- the Oratorio del Mexuar: small prayer room north of the hall, twin-arched windows over the Darro valley,
// carved stucco walls, the mihrab niche in the east wall and a lacería ceiling.
function oratory(b, off, slab, layer, full, fi, segs, WALLS) {
  const OX = -29, OWd = 6.6, OZ0 = -27.2, OZ1 = Z0, OH = 5.0, OC = 4.25;
  const OXW = OX - OWd / 2, OXE = OX + OWd / 2, OCZ = (OZ0 + OZ1) / 2, OD = OZ1 - OZ0;
  const bays = [OX - 1.5, OX + 1.5], wins = [];
  for (const cb of bays) for (const s of [-1, 1]) wins.push(cb + s * .36);
  const ww = .5, sill = .95, spring = 2.15, rise = .5;
  const ON = { axis: 'x', f: OZ0, inward: 1, u0: OXW - T / 2, u1: OXE + T / 2, open: wins.map(u => [u, ww, rise]) };
  const OS = { axis: 'x', f: OZ1, inward: -1, u0: OXW - T / 2, u1: OXE + T / 2, open: [[CX, 2.3, 1.2]] };
  const OW = { axis: 'z', f: OXW, inward: 1, u0: OZ0, u1: OZ1, open: [] };
  const OE = { axis: 'z', f: OXE, inward: -1, u0: OZ0, u1: OZ1, open: [[(OZ0 + OZ1) / 2, 1.0, .62]] };
  const IXW = OXW + T / 2, IXE = OXE - T / 2;
  b.floor(OX, OCZ, OWd, OD, 0, 'mexOrFloor');
  // shell: south wall is the hall's north wall (already built); west, east, north here
  b.box(OW.f, 0, OCZ, OD + T, OH, T, 'mexOrPlaster', Math.PI / 2, true);
  // north wall with two twin-arched windows
  {
    const cuts = wins.map(u => [u - ww / 2, u + ww / 2]);
    let a = ON.u0; const parts = [];
    for (const [c0, c1] of cuts) { parts.push([a, c0]); a = c1; } parts.push([a, ON.u1]);
    for (const [p, q] of parts) if (q - p > .01) b.box((p + q) / 2, 0, OZ0, q - p, OH, T, 'mexOrPlaster', 0, true);
    for (const u of wins) {
      b.box(u, 0, OZ0, ww, sill, T, 'mexOrPlaster', 0, true);
      b.unique(archPiece(ww, spring, rise, OH, T, 0), 'mexOrPlaster', [u, 0, OZ0], 0);
      b.unique(archPiece(ww, spring, rise, spring + rise + .3, T + .08, .2), 'mexOrStucco', [u, 0, OZ0], 0);
    }
    for (const cb of bays) { b.cylinder(cb, sill, OZ0, .05, spring - sill + .08, 'mexMarble', .04, 10); b.box(cb, spring + .06, OZ0, .17, .09, T + .02, 'mexCapital'); b.box(cb, sill - .06, OZ0, .5, .06, T + .08, 'mexMarble'); }
    // sills
    for (const u of wins) b.box(u, sill - .04, OZ0 + .05, ww + .12, .05, T + .12, 'mexMarble');
  }
  // mihrab: niche cut into the east wall (horseshoe arch, muqarnas ring, stucco surround)
  {
    const nw = 1.0, sp = 1.5, rs = .62, c0 = OCZ - nw / 2, c1 = OCZ + nw / 2;
    b.box(OE.f, 0, (OZ0 - T / 2 + c0) / 2, c0 - (OZ0 - T / 2), OH, T, 'mexOrPlaster', Math.PI / 2, true);
    b.box(OE.f, 0, (OZ1 + T / 2 + c1) / 2, OZ1 + T / 2 - c1, OH, T, 'mexOrPlaster', Math.PI / 2, true);
    b.box(OE.f + T / 2 - .05, 0, OCZ, nw, OH, .1, 'mexOrPlaster', Math.PI / 2, true);
    const pos = [OE.f, 0, OCZ], rot = Math.PI / 2;
    b.unique(archPiece(nw, sp, rs, OH, T, 0), 'mexOrPlaster', pos, rot);
    b.unique(archPiece(nw, sp, rs, sp + rs + .42, T + .1, .42), 'mexOrStucco', pos, rot);
    b.unique(archPiece(nw, sp, rs, sp + rs + .2, T + .14, .16), 'mexOrMuq', pos, rot);
    b.box(OE.f + T / 2 - .105, 0, OCZ, nw, sp + rs, .01, 'mexOrMuqBlue', Math.PI / 2);
    const cc = cell();
    for (let i = 0; i < 7; i++) for (let r2 = 0; r2 < 3; r2++) { const a = (i / 6 - .5) * (nw - .3 - r2 * .2); b.add(cc, 'mexOrMuq', [OE.f + T / 2 - .12 - .0, sp + rs * .35 + r2 * .17 + Math.cos(a * 2.2) * .02, OCZ + a], [1, 1, 1], -Math.PI / 2); }
  }
  // inner finishes
  for (const u of wins) { slab(ON, u - ww / 2 - .06, u + ww / 2 + .06, 0, sill, 0, .02, 'mexOrLime'); slab(ON, u - ww / 2 - .2, u + ww / 2 + .2, 2.95, .66, 0, .035, 'mexOrStucco'); }
  for (const w of [ON, OW, OE]) {
    layer(w, 0, 1.35, 0, .02, 'mexOrLime', w.u0 + T / 2, w.u1 - T / 2);
    layer(w, 1.35, .26, 0, .04, 'mexOrInscr', w.u0 + T / 2, w.u1 - T / 2);
    layer(w, 1.61, 2.0, 0, .035, 'mexOrStucco', w.u0 + T / 2, w.u1 - T / 2);
    layer(w, 3.61, .6, 0, .05, 'mexOrLattice', w.u0 + T / 2, w.u1 - T / 2);
    full(w, OC - .5, .5, 0, .12, 'mexOrFascia', w.u0 + T / 2, w.u1 - T / 2);
    full(w, OC, .1, 0, .22, 'mexOrWood', w.u0 + T / 2, w.u1 - T / 2);
  }
  slab(OE, OCZ - .95, OCZ + .95, 2.6, 1.0, 0, .035, 'mexOrStucco');
  // south wall (hall's north wall) interior face
  for (const [p, q] of segs(OS, IXW, IXE)) {
    slab(OS, p, q, 0, 1.35, 0, .02, 'mexOrLime'); slab(OS, p, q, 1.35, .26, 0, .04, 'mexOrInscr'); slab(OS, p, q, 1.61, 2.0, 0, .035, 'mexOrStucco'); slab(OS, p, q, 3.61, .6, 0, .05, 'mexOrLattice');
  }
  slab(OS, IXW, IXE, OC - .5, .5, 0, .12, 'mexOrFascia'); slab(OS, IXW, IXE, OC, .1, 0, .22, 'mexOrWood');
  // blind lattice windows (celosía) above the twin windows, glowing
  for (const u of [OX - 2.25, OX - .75 - .0, OX + .75, OX + 2.25].slice(0, 4)) {
    b.box(u, 3.0, OZ0 + T / 2 + .045, .42, .62, .02, 'mexGlow'); b.box(u, 3.0, OZ0 + T / 2 + .062, .42, .62, .01, 'mexGrille');
  }
  // lacería ceiling with ribs and cross beams
  ceilingQuad(b, 'mexOrLaceria', IXW, OZ0 + T / 2, IXE, OZ1 - T / 2, OC);
  for (let x = Math.ceil(IXW); x <= IXE; x++) b.box(x, OC - .09, OCZ, .07, .09, OD - T, 'mexOrWood');
  for (let z = Math.ceil(OZ0 + T / 2); z <= OZ1 - T / 2; z++) b.box(OX, OC - .09, z, OWd - T, .09, .07, 'mexOrWood');
  for (const z of [OZ0 + 2.0, OZ0 + 4.2]) b.box(OX, OC - .35, z, OWd - T, .35, .28, 'mexOrWood');
  b.roof(OX, OCZ, OWd + 1.1, OD + 1.1, OH + .15, 1.4);
}
