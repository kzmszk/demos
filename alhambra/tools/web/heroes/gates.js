import * as THREE from 'three';
import { terrainHeight, insidePolygon } from '../navigation.js';
import { plant, CYPRESS, SHRUB, ORANGE, PLANE } from '../trees.js';
import { Soup, Mesher, Frame, rnd, vnoise, texMat, plainMat, boxSolid, pyramid, polyFace, ringFace, soffit, horseshoe, openingPath, stations, loft, TOWERS, centroid, groundAt, gnd, registerGround, prismTower, skin, footInfo, outwardSign, edgeFrame, minRect, merlonRow, setLow, UP, wantOut, blob, patch, rectFace, fbox, wallQuad, floorQuad, sawtooth, windowAt } from './walls.js';

// Puerta de la Justicia (1348) with its esplanade, barbican bastion and the Pilar de Carlos V; the Puerta del Vino and the
// Plaza de los Aljibes. Everything is built in a local frame (u right, y up, w outward from the gate front) and placed by Frame.
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const hyp = Math.hypot;

// ---------------------------------------------------------------- materials
async function decal(M, name, file, w, h, { rough = .9, bump = 0, color = 0xffffff, emissive = 0, side = THREE.FrontSide } = {}) {
  const m = await texMat(M, name, file, w, h, { rough, bump, color, vc: false, side });
  m.map.wrapS = m.map.wrapT = THREE.ClampToEdgeWrapping; m.map.repeat.set(1 / w, 1 / h);
  if (m.bumpMap) { m.bumpMap.wrapS = m.bumpMap.wrapT = THREE.ClampToEdgeWrapping; }
  if (emissive) { m.emissive = new THREE.Color(0xffffff); m.emissiveMap = m.map; m.emissiveIntensity = emissive; }
  return m;
}
// ---------------------------------------------------------------- the esplanade terrace in front of the gate (built-up ground)
const TERRACE = [[-54.83, 135.12], [-49.29, 121.88], [-20.87, 130.9], [-22.4, 134.05], [-12.23, 138.97], [-6.0, 148.5], [-13.0, 163.5], [-26.5, 157.5], [-41.39, 144.87], [-50.59, 137.49]];
const JW = [Math.sin(1.1737), Math.cos(1.1737)], JU = [Math.cos(1.1737), -Math.sin(1.1737)];
const localW = (x, z) => (x - -52.06) * JW[0] + (z - 128.5) * JW[1];
const terraceH = (x, z) => -11.5 - .03 * Math.max(0, localW(x, z));
function inTerrace(x, z, pad = 0) { return insidePolygon(x, z, TERRACE) || (pad > 0 && TERRACE.some((a, i) => { const c = TERRACE[(i + 1) % TERRACE.length], dx = c[0] - a[0], dz = c[1] - a[1], l2 = dx * dx + dz * dz, t = clamp(((x - a[0]) * dx + (z - a[1]) * dz) / l2, 0, 1); return hyp(x - a[0] - dx * t, z - a[1] - dz * t) < pad; })); }

export async function materials(M) {
  registerGround((x, z) => (inTerrace(x, z) ? terraceH(x, z) : null));
  await decal(M, 'gatPorch', 'justicia-porch', 5.222, 9.5, { rough: .85, emissive: .10 });
  await decal(M, 'gatHandMat', 'justicia-hand', 1, 1, { rough: .7, bump: .6 });
  await decal(M, 'gatVinoEast', 'vino-east', 7.943, 10.287, { rough: .9 });
  await decal(M, 'gatPilar', 'pilar-front', 14.8, 6.35, { rough: .88 });
  plainMat(M, 'gatMarble', 0xd9cfbb, .7);
  plainMat(M, 'walWaterDark', 0x3f5b57, .15, { metal: .1 });
  plainMat(M, 'gatLime', 0xe9dfcc, .95);
  plainMat(M, 'gatBeam', 0x7a5a3c, .85, { vc: false });
  plainMat(M, 'gatIron', 0x2b2926, .5, { metal: .6 });
  plainMat(M, 'gatWoodDoor', 0x4a3524, .8);
}

// ---------------------------------------------------------------- shared constants
const J = { x: -52.06, z: 128.5, rot: 1.1737, F: -11.5, W: 14.35, D: 13.9, top: 19.4 };
let PER = null;

// ---------------------------------------------------------------- the Puerta de la Justicia
function justiciaTower(b, ctx) {
  const F = new Frame(J.x, J.F, J.z, J.rot), me = new Mesher();
  const halfW = J.W / 2, D = J.D, top = J.top, tt = top + 1.1;
  b.zone = 'justice';
  const hs = horseshoe(2.6, 5.86, 10.2), door = horseshoe(1.29, 3.03, 4.32);
  const out = wantOut(F);
  // ---- front face (w = 0): tapial with the arch opening cut out
  const hole = openingPath(hs, 0).map(p => [p[0], p[1]]);
  polyFace(me.s('walTapial'), [[-halfW, -.8], [halfW, -.8], [halfW, tt], [-halfW, tt]], [hole], (u, y) => F.p(u, y, 0), (u, y) => [u, y], [1, .97, .94], out);
  // ashlar veneer on the lower front (both sides of the opening) and corner quoins
  for (const s of [-1, 1]) {
    const u0 = s < 0 ? -halfW : hs.a, u1 = s < 0 ? -hs.a : halfW;
    polyFace(me.s('walPatchAshlar'), [[u0, -.8], [u1, -.8], [u1, 5.4], [u0, 5.4]], [], (u, y) => F.p(u, y, .04), (u, y) => [u, y], [1, .96, .9], out);
    for (let k = 0; k < 9; k++) { const y = 5.4 + k * .9, long = k % 2 ? .95 : 1.7, uc = s * (halfW - long / 2 + .02); fbox(me.s('walAshlar'), F, uc, y, .06, long, .88, .12, [.98 - k * .004, .95, .9], 0b011111, 1); }
  }
  // brick alfiz panel around the arch, lime-rendered, with the brick voussoir ring
  const panel = [[-3.75, -.8], [3.75, -.8], [3.75, 13.0], [-3.75, 13.0]];
  polyFace(me.s('walPatchLime'), panel, [hole], (u, y) => F.p(u, y, .10), (u, y) => [u, y], [1.02, .99, .95], out);
  for (const [u0, y0, u1, y1] of [[-3.75, -.8, -3.65, 13], [3.65, -.8, 3.75, 13]]) fbox(me.s('walPatchLime'), F, (u0 + u1) / 2, y0, .05, u1 - u0 + .05, y1 - y0, .10, [.95, .92, .88], 0b111101);
  const ring = openingPath(hs, 0), cum = [0]; for (let i = 1; i < ring.length; i++) cum.push(cum[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
  ringFace(me.s('walBrick'), F, ring, 0, .85, .15, (pt, i, side) => [side ? .85 : 0, cum[i]], [1, .96, .92]);
  ringFace(me.s('walBrickB'), F, ring, .85, 1.0, .12, (pt, i, side) => [side ? 1 : .85, cum[i]], [.92, .88, .84]);
  // hand on the keystone
  rectFace(me.s('gatHandMat'), F, -.28, 10.85, .28, 11.9, .19, (u, y) => [(u + .28) / .56, (y - 10.85) / 1.05], [1, 1, 1]);
  // saw-tooth frieze above the panel, windows and slits, fallen-render patches
  sawtooth(me, F, -4.15, 4.15, 13.0, 13.75, .08, .22, .30);
  windowAt(me, F, -5.15, 11.7, .62, 1.5, .0);
  windowAt(me, F, 5.2, 11.2, .62, 1.5, .0);
  rectFace(me.s('walDarkOver'), F, 5.95 - .09, 15.2, 5.95 + .09, 16.4, .03);
  rectFace(me.s('walDarkOver'), F, -2.3 - .09, 16.6, -2.3 + .09, 17.7, .03);
  const prand = rnd(401);
  for (let i = 0; i < 9; i++) patch(me, F, 'walPatchBrick', lerp(-6.5, 6.5, prand()), lerp(13.8, 19.2, prand()), .7 + prand() * 1.5, .5 + prand() * 1.2, .035, 500 + i, [1, 1, 1]);
  for (let i = 0; i < 6; i++) patch(me, F, 'walPatchLime', lerp(-6.5, 6.5, prand()), lerp(6, 16, prand()), .5 + prand() * 1.2, .4 + prand() * 1.0, .03, 600 + i, [1.02, 1, .97]);
  // brick crown of the tower (the top 3 m are brick between tapial lifts)
  polyFace(me.s('walPatchBrick'), [[-halfW, 17.0], [-5, 17.5], [-2, 17.1], [1.5, 17.6], [4.5, 17.2], [halfW, 17.7], [halfW, tt], [-halfW, tt]], [], (u, y) => F.p(u, y, .045), (u, y) => [u, y], [1, 1, 1], out);

  // ---- the great horseshoe porch: soffit, floor, back wall with the decal
  const wBack = -2.4, wDoor = -4.7;
  const cumP = [0]; for (let i = 1; i < ring.length; i++) cumP.push(cumP[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
  for (let i = 0; i < ring.length - 1; i++) {
    const jamb = i === 0 || i === ring.length - 2;
    soffit(me.s(jamb ? 'walAshlar' : 'walBrick'), F, [ring[i], ring[i + 1]], 0, 0, wBack, jamb ? (k, w) => [-w, ring[i + k][1]] : (k, w) => [cumP[i + k], -w], [.9, .88, .86]);
  }
  floorQuad(me.s('walCobble'), F, -2.6, wBack, 2.6, 0, 0, [.95, .93, .9], .5);
  // back wall: the decal (photograph of the real second door and the tiled lunette), with the door opening cut out
  const porchOutline = openingPath(hs, -.3).map(p => [p[0], p[1]]);
  const doorHole = openingPath(door, 0).map(p => [p[0], p[1]]);
  polyFace(me.s('gatPorch'), porchOutline, [doorHole], (u, y) => F.p(u, y, wBack), (u, y) => [u + 2.611, Math.max(0, y)], [1, 1, 1], wantOut(F));
  // second brick arch framing the lunette, projecting a little from the back wall
  { const lun = [], n = 28, a = 2.35, y0 = 6.62, rise = 2.5; for (let i = 0; i <= n; i++) { const t = Math.PI * (1 - i / n), cu = Math.cos(t) * a, cy = y0 + Math.sin(t) * rise, nx = Math.cos(t) / a * 1, ny = Math.sin(t) / rise; const l = hyp(nx, ny); lun.push([cu, cy, nx / l, ny / l]); }
    const cl = [0]; for (let i = 1; i < lun.length; i++) cl.push(cl[i - 1] + hyp(lun[i][0] - lun[i - 1][0], lun[i][1] - lun[i - 1][1]));
    ringFace(me.s('walBrick'), F, lun, 0, .34, wBack + .12, (pt, i, side) => [side ? .34 : 0, cl[i]], [.95, .9, .85]);
    for (let i = 0; i < lun.length - 1; i++) soffit(me.s('walBrick'), F, [lun[i], lun[i + 1]], 0, wBack + .12, wBack, (k, w) => [cl[i + k], -w], [.8, .76, .72]);
  }
  // ---- door passage (2.3 m deep) with its slightly rising floor
  const cumD = [0]; for (let i = 1; i < doorHole.length + 1; i++) { const p = openingPath(door, 0); cumD.push(cumD[i - 1] + (i < p.length ? hyp(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) : 0)); }
  const dp = openingPath(door, 0);
  for (let i = 0; i < dp.length - 1; i++) { const jamb = i === 0 || i === dp.length - 2; soffit(me.s(jamb ? 'walAshlarGrey' : 'walTapialB'), F, [dp[i], dp[i + 1]], 0, wBack, wDoor, jamb ? (k, w) => [-w, dp[i + k][1]] : (k, w) => [cumD[i + k], -w], [.85, .82, .8]); }
  me.s('gatMarble').quad(F.p(-1.29, 0, wBack), F.p(1.29, 0, wBack), F.p(1.29, .5, wDoor), F.p(-1.29, .5, wDoor), [0, 0], [2.58, 0], [2.58, 2.3], [0, 2.3], [.9, .88, .85], UP);

  // ---- the other three faces, standing on the real ground (variable foot), then the parapet and the top
  const dirs = [['left', -halfW, -D / 2, -Math.PI / 2], ['right', halfW, -D / 2, Math.PI / 2], ['back', 0, -D, Math.PI]];
  for (const [name, fu, fw, extra] of dirs) {
    const G = F.at(fu, 0, fw, extra), L = name === 'back' ? J.W : D, n = Math.ceil(L), rr = rnd(name.length * 91 + 7);
    const north = name === 'right';
    const foots = [], plTop = [], us = [];
    for (let k = 0; k <= n; k++) {
      const u = -L / 2 + L * k / n, [x, z] = G.xz(u, 1.0), gw = groundAt(x, z, PER), gl = gw - F.y0;
      us.push(u); foots.push(gl - .9 - (north ? 0 : .6)); plTop.push(north ? gl + .25 : clamp(gl + 4.6 + (vnoise(u * .4, 5) - .5) * 1.2, gl + 2.5, tt - 4));
    }
    const outG = wantOut(G);
    const lower = [...us.map((u, k) => [u, foots[k]]), ...us.map((u, k) => [u, plTop[k]]).reverse()];
    polyFace(me.s(north ? 'walTapialC' : 'walAshlarGrey'), lower, [], (u, y) => G.p(u, y, 0), (u, y) => [u + rr() * 0 + 3.3, y], [.95, .93, .9], outG);
    // upper tapial
    const upper = [...us.map((u, k) => [u, plTop[k]]), [L / 2, tt], [-L / 2, tt]];
    let holes = [];
    if (north) { const ex = horseshoe(.85, 11.5 + 1.55, 11.5 + 2.7); const uc = -(-9.95 + D / 2); holes = [openingPath(ex, 11.499).map(p => [p[0] + uc, p[1]])]; }
    polyFace(me.s(north ? 'walTapialB' : 'walTapial'), upper, holes, (u, y) => G.p(u, y, 0), (u, y) => [u + (name === 'back' ? 5 : 11), y], [1, .97, .94], outG);
    // ledge on the plinth line
    for (let k = 0; k < n; k++) if (!north) { const a = [us[k], plTop[k]], c = [us[k + 1], plTop[k + 1]]; me.s('walAshlarGrey').quad(G.p(a[0], a[1], .0), G.p(c[0], c[1], .0), G.p(c[0], c[1], .22), G.p(a[0], a[1], .22), [0, 0], [1, 0], [1, .22], [0, .22], [1, .97, .93], UP); }
    // brick crown, patches, a window or two
    const bc = [[-L / 2, top - 3.2 + rr() * .6]]; for (let k = 1; k < 6; k++) bc.push([-L / 2 + L * k / 6, top - 3.4 + rr() * 1.4]); bc.push([L / 2, top - 3.0 + rr() * .6], [L / 2, tt], [-L / 2, tt]);
    polyFace(me.s('walPatchBrick'), bc, [], (u, y) => G.p(u, y, .045), (u, y) => [u, y], [1.02, 1, .98], outG);
    for (let i = 0; i < 5; i++) patch(me, G, i % 2 ? 'walPatchBrick' : 'walPatchLime', lerp(-L / 2 + 1.5, L / 2 - 1.5, rr()), lerp(plTop[0] + 1.5, top - 3.5, rr()), .7 + rr() * 1.4, .5 + rr() * 1.1, .035, 700 + i + name.length * 10, [1.02, 1, .98]);
    // stepped brick cornice with a row of modillions under the parapet (the real tower carries one on every face)
    { const cs = me.s('walBrickB'), n2 = Math.round(L / .85);
      fbox(cs, G, 0, top - 1.62, .09, L, .16, .18, [.98, .92, .86], 0b111101); fbox(cs, G, 0, top - 1.46, .17, L, .16, .34, [1, .94, .88], 0b111101); fbox(cs, G, 0, top - 1.3, .27, L, .3, .54, [1, .95, .9], 0b111101);
      for (let k = 0; k < n2; k++) fbox(cs, G, -L / 2 + (k + .5) * L / n2, top - 1.95, .13, .32, .34, .26, [.92, .86, .8], 0b111101); }
    if (name === 'back') windowAt(me, G, 2.8, 12.5, .62, 1.5, 0);
    if (name === 'left') { windowAt(me, G, 1.5, 12.8, .62, 1.5, 0); windowAt(me, G, -3.8, 11.3, .62, 1.5, 0); }
    if (north) { sawtooth(me, G, -D / 2 + 1.2, -D / 2 + 5.6, 8.2, 8.65, .06, .16, .26); windowAt(me, G, 3.2, 9.9, .55, 1.3, 0); }
  }
  // brick parapet: inner faces and cap, platform
  { const t = .45, segs = [[-halfW, 0, halfW, 0, 0, -1], [halfW, 0, halfW, -D, -1, 0], [halfW, -D, -halfW, -D, 0, 1], [-halfW, -D, -halfW, 0, 1, 0]];
    for (const [ua, wa, ue, we, fu, fw] of segs) {
      const ua2 = ua + fu * t, wa2 = wa + fw * t, ue2 = ue + fu * t, we2 = we + fw * t;
      wallQuad(me.s('walTapialB'), F, ua2, wa2, ue2, we2, top, tt, fu, fw, [.95, .93, .9]);
      me.s('walBrickB').quad(F.p(ua, tt, wa), F.p(ue, tt, we), F.p(ue2, tt, we2), F.p(ua2, tt, wa2), [0, 0], [1, 0], [1, .45], [0, .45], [.95, .9, .85], UP);
    }
    polyFace(me.s('walBrickB'), [[-halfW + t, -t], [halfW - t, -t], [halfW - t, -D + t], [-halfW + t, -D + t]], [], (u, w) => F.p(u, top, w), (u, w) => [u, w], [.85, .83, .8], UP);
    // crenellation: pyramid-capped merlons on all four sides of the parapet (the real gate has them)
    const q = [[-halfW + .31, -.31], [halfW - .31, -.31], [halfW - .31, -D + .31], [-halfW + .31, -D + .31]];
    for (let k = 0; k < 4; k++) merlonRow(me, F, q[k], q[(k + 1) % 4], F.y0 + tt, { pitch: 1.55, seed: 90 + k, h: 1.25, capH: .5 });
  }

  // ---- the bent passage: porch ramp -> vestibule -> flight A (west) -> landing -> flight B (east, long) -> exit door in the north face
  const S = -F.y0;                                     // local height of the plateau (y = 0 in the world)
  const wallM = me.s('walLime'), vaultM = me.s('walLime'), pcol = [.96, .93, .88], vcol = [.9, .86, .8];
  const yDoor = .9, yA = 3.7, WA = [-4.7, -7.5], WB = [-8.3, -11.6], uA0 = -1.4, uA1 = -5.9, uB0 = -6.1, uB1 = 6.4, wDoorExit = -9.95;
  const slopeA = (yA - yDoor) / (uA0 - uA1), slopeB = (S - yA) / (uB1 - uB0);
  // generic vault along u: floor profile fy(u), section of width between w0..w1
  const spring = 2.0, crown = 3.25;
  function vaultAlongU(ua, ub, w0, w1, fy, mat, col, skipEnds = false) {
    const sec = (u) => { const y = fy(u), pts = [[w0, y], [w0, y + spring]]; const hw = (w1 - w0) / 2, wc = (w0 + w1) / 2; for (let i = 1; i < 10; i++) { const a = Math.PI * i / 10, w = wc - Math.cos(a) * hw; pts.push([w, y + spring + (crown - spring) * Math.sin(a)]); } pts.push([w1, y + spring], [w1, y]); return pts.map(p => F.p(u, p[1], p[0])); };
    const A = sec(ua), B = sec(ub), cen = F.p((ua + ub) / 2, fy((ua + ub) / 2) + 1.2, (w0 + w1) / 2);
    for (let k = 0; k < A.length - 1; k++) {
      const q = [A[k], B[k], B[k + 1], A[k + 1]], cx = (q[0][0] + q[2][0]) / 2, cy = (q[0][1] + q[2][1]) / 2, cz = (q[0][2] + q[2][2]) / 2, want = [cen[0] - cx, cen[1] - cy, cen[2] - cz];
      mat.quad(q[0], q[1], q[2], q[3], [0, k * .5], [Math.abs(ub - ua), k * .5], [Math.abs(ub - ua), k * .5 + .5], [0, k * .5 + .5], col, want);
    }
  }
  const fyA = u => u > uA0 ? yDoor : u > uA1 ? yDoor + (uA0 - u) * slopeA : yA;
  const fyB = u => u < uB0 ? yA : u < uB1 ? yA + (u - uB0) * slopeB : S;
  // ---- vestibule + flight A (u from 2.1 to -5.9, w -4.7..-7.5)
  vaultAlongU(2.1, -6.9, WA[1], WA[0], fyA, vaultM, vcol);
  // ---- landing across both halls (u -6.9..-5.9) joins A to B: a cross vault along w
  { const u0 = -6.9, u1 = -5.9, y = yA, wc = (WA[0] + WB[1]) / 2; const sec = (w) => { const pts = [[u0, y], [u0, y + spring]]; const hw = (u1 - u0) / 2, uc = (u0 + u1) / 2; for (let i = 1; i < 8; i++) { const a = Math.PI * i / 8; pts.push([uc - Math.cos(a) * hw, y + spring + (crown - spring) * Math.sin(a)]); } pts.push([u1, y + spring], [u1, y]); return pts.map(p => F.p(p[0], p[1], w)); };
    const A = sec(WA[0]), B = sec(WB[1]), cen = F.p((u0 + u1) / 2, y + 1.2, wc);
    for (let k = 0; k < A.length - 1; k++) { const q = [A[k], B[k], B[k + 1], A[k + 1]], cx = (q[0][0] + q[2][0]) / 2, cy = (q[0][1] + q[2][1]) / 2, cz = (q[0][2] + q[2][2]) / 2; vaultM.quad(q[0], q[1], q[2], q[3], [0, 0], [1, 0], [1, 1], [0, 1], vcol, [cen[0] - cx, cen[1] - cy, cen[2] - cz]); } }
  // ---- flight B (u from -6.9 to 7.18)
  vaultAlongU(-6.9, 7.18, WB[1], WB[0], fyB, vaultM, vcol);
  // end wall of A at the near door wall, dividing wall between A and B (both full height), end wall of B
  const wallProfile = (u0, u1, fy, w, faceW, hole, uvo = 0) => polyFace(wallM, [[u0, fy(u0)], [u1, fy(u1)], [u1, fy(u1) + spring], [u0, fy(u0) + spring]], hole ? [hole] : [], (u, y) => F.p(u, y, w), (u, y) => [u + uvo, y], pcol, wantOut(F, faceW));
  // near wall of the vestibule (w = -4.7), with the door passage opening. y runs over the vault lunette too
  { const prof = []; const us = [2.1]; for (let u = 2.1; u >= -6.9; u -= .5) us.push(u); us.push(-6.9); const top = u => fyA(u) + spring + (crown - spring) * 0.0;
    const door = openingPath(horseshoe(1.29, yDoor + 2.1, yDoor + 3.15), yDoor).map(p => [p[0], p[1]]);
    const outline = [...us.map(u => [u, fyA(u)]), ...[...us].reverse().map(u => [u, fyA(u) + spring + .0])];
    polyFace(wallM, outline, [door], (u, y) => F.p(u, y, WA[0]), (u, y) => [u, y], pcol, wantOut(F, -1)); }
  // divider between the two flights (both faces), from u = -5.9 to the north end
  for (const [w, f] of [[WA[1], 1], [WB[0], -1]]) { const us = []; for (let u = -5.9; u < 7.18; u += .6) us.push(u); us.push(7.18); const top = u => { const y = Math.max(fyA(u), fyB(u)); return y + spring; };
    const o1 = f === 1 ? [...us.map(u => [u, fyA(u)]), ...[...us].reverse().map(u => [u, fyA(u) + spring])] : [...us.map(u => [u, fyB(u)]), ...[...us].reverse().map(u => [u, fyB(u) + spring])];
    polyFace(wallM, o1, [], (u, y) => F.p(u, y, w), (u, y) => [u, y], pcol, wantOut(F, f)); }
  // timber beams under the crown every 1.2 m in the flights (read as the carpentry of the real vestibule)
  for (let u = 1.5; u > -6.5; u -= 1.2) fbox(me.s('gatBeam'), F, u, fyA(u) + crown - .2, (WA[0] + WA[1]) / 2, .1, .12, WA[0] - WA[1] - .1, [1, 1, 1], 0b111101);
  for (let u = -5.5; u < 6.5; u += 1.2) fbox(me.s('gatBeam'), F, u, fyB(u) + crown - .2, (WB[0] + WB[1]) / 2, .1, .12, WB[0] - WB[1] - .1, [1, 1, 1], 0b111101);
  // ---- floors: door-passage ramp is a box wedge; landings; steps
  floorQuad(me.s('walCobble'), F, -1.29, -4.7, 1.29, 0, 0, [.95, .93, .9], .5);       // porch handled earlier (flat); passage ramp below
  { const N = 16, tread = 4.7 / N; for (let k = 0; k < N; k++) { const y = yDoor * (1 - (k + .5) / N); fbox(me.s('walCobble'), F, 0, y - .35, -(k + .5) * tread, 2.58, .35, tread, [.95, .93, .9], 0b010000); } }
  floorQuad(me.s('walAshlarGrey'), F, uA0, WA[0], 2.1, WA[1], yDoor, [.9, .88, .85], .5);
  { const N = Math.round((uA0 - uA1) / .3), tread = (uA0 - uA1) / N, rise = (yA - yDoor) / N;
    for (let k = 0; k < N; k++) fbox(me.s('walAshlar'), F, uA0 - (k + .5) * tread, yDoor + rise * (k + 1) - .35, (WA[0] + WA[1]) / 2, tread, .35, WA[0] - WA[1], [.9 + (k % 3) * .02, .88, .85], 0b010100); }
  floorQuad(me.s('walAshlarGrey'), F, -6.9, WB[1], -5.9, WA[0], yA, [.88, .86, .83], .5);
  { const N = Math.round((uB1 - uB0) / .3), tread = (uB1 - uB0) / N, rise = (S - yA) / N;
    for (let k = 0; k < N; k++) fbox(me.s('walAshlar'), F, uB0 + (k + .5) * tread, yA + rise * (k + 1) - .35, (WB[0] + WB[1]) / 2, tread, .35, WB[0] - WB[1], [.9 + (k % 3) * .02, .88, .85], 0b011000); }
  // ---- west end wall of the landing and the east end wall of B with the exit door
  wallQuad(wallM, F, -6.9, WA[0], -6.9, WB[1], yA, yA + crown, 1, 0, pcol);
  const exitH = horseshoe(.85, S + 1.55, S + 2.7);
  { const G2 = F.at(halfW, 0, wDoorExit, Math.PI / 2);   // outward = +u
    const ep = openingPath(exitH, S), ce = [0]; for (let i = 1; i < ep.length; i++) ce.push(ce[i - 1] + hyp(ep[i][0] - ep[i - 1][0], ep[i][1] - ep[i - 1][1]));
    for (let i = 0; i < ep.length - 1; i++) soffit(me.s(i === 0 || i === ep.length - 2 ? 'walAshlarGrey' : 'walBrick'), G2, [ep[i], ep[i + 1]], 0, 0, -.8, (k, w) => [ce[i + k], w], [.85, .82, .78]);
    ringFace(me.s('walPatchLime'), G2, ep, 0, .32, .07, (pt, i, side) => [side ? .32 : 0, i * .3], [1, .97, .93]);
    // timber door leaves, ajar, in the exit
    me.s('walAshlarGrey').quad(G2.p(-.85, S, 0), G2.p(.85, S, 0), G2.p(.85, S, -.8), G2.p(-.85, S, -.8), [0, 0], [1.7, 0], [1.7, .8], [0, .8], [.9, .88, .85], UP);
    // closed end of flight B behind the soffit (the wall the stairs run into)
    const hole = openingPath(exitH, S).map(p => [p[0], p[1]]);
    polyFace(wallM, [[-1.6, fyB(6.4)], [1.6, fyB(6.4)], [1.6, S + crown], [-1.6, S + crown]], [hole], (u, y) => G2.p(u, y, -.8), (u, y) => [u, y], pcol, [-1, 0, 0].map((v, i) => v * 0 + [G2.d(0, -1)[0], 0, G2.d(0, -1)[1]][i])); }
  // ---- navigation: floors, ramps and the solid tower mass (everything outside the passage legs)
  F.navRamp(b, 0, -2.35, 2.58, 4.7, yDoor, 0);                                    // porch + door passage: y 0 at w=0 .. .9 at w=-4.7
  F.navFloor(b, (uA0 + 2.1) / 2, (WA[0] + WA[1]) / 2, 2.1 - uA0, WA[0] - WA[1], yDoor);
  F.navRamp(b, (uA0 + uA1) / 2, (WA[0] + WA[1]) / 2, WA[0] - WA[1], uA0 - uA1, yA, yDoor, Math.PI / 2);   // v' runs along +u: y at -d (u small) = yA .. yDoor at u large
  F.navFloor(b, -6.4, (WA[0] + WB[1]) / 2, 1.0, WA[0] - WB[1], yA);
  F.navRamp(b, (uB0 + uB1) / 2, (WB[0] + WB[1]) / 2, WB[0] - WB[1], uB1 - uB0, yA, S, Math.PI / 2);
  F.navFloor(b, (uB1 + halfW) / 2 + .35, wDoorExit, halfW - uB1 + .8, 1.7, S);
  { const legs = [[-2.6, 2.6, -2.4, 0], [-1.29, 1.29, -4.7, -2.4], [-6.9, 2.1, WA[1], WA[0]], [-6.9, -5.9, WB[1], WA[0]], [-6.9, 7.2, WB[1], WB[0]], [uB1 - .1, halfW + .2, wDoorExit - .85, wDoorExit + .85]];
    const us = [-halfW, halfW], ws = [-D, 0]; for (const l of legs) { us.push(l[0], l[1]); ws.push(l[2], l[3]); }
    const U = [...new Set(us.filter(v => v >= -halfW && v <= halfW))].sort((a, c) => a - c), W = [...new Set(ws.filter(v => v >= -D && v <= 0))].sort((a, c) => a - c);
    for (let i = 0; i < U.length - 1; i++) for (let j = 0; j < W.length - 1; j++) {
      const uc = (U[i] + U[i + 1]) / 2, wc = (W[j] + W[j + 1]) / 2;
      if (legs.some(l => uc > l[0] && uc < l[1] && wc > l[2] && wc < l[3])) continue;
      F.navBox(b, uc, wc, U[i + 1] - U[i], W[j + 1] - W[j], -60, 40);
    } }
  me.flush(b, [0, 0, 0], 0);
}

// ---------------------------------------------------------------- esplanade: terrace, retaining walls, bastion, Pilar de Carlos V
function parapetWall(me, st, topAt, dEdge, o) {
  const t = o.thick, soup = me.s(o.mat);
  loft(soup, st, i => [{ d: dEdge(i), y: topAt(i), v: 0 }, { d: dEdge(i), y: topAt(i) + o.h, v: o.h }], { dir: 'out', col: o.col || [1, .97, .94] });
  loft(me.s(o.cap || o.mat), st, i => [{ d: dEdge(i), y: topAt(i) + o.h, v: 0 }, { d: dEdge(i) - t, y: topAt(i) + o.h, v: t }], { dir: 'up', col: [1.05, 1.02, .98] });
  loft(soup, st, i => [{ d: dEdge(i) - t, y: topAt(i) + o.h, v: o.h }, { d: dEdge(i) - t, y: topAt(i), v: 0 }], { dir: 'in', col: [.95, .93, .9] });
}
function terraceWall(me, ctx, pts, seed, { h = 1.0, mat = 'walAshlarGrey' } = {}) {
  const [a, c] = pts, tx = c[0] - a[0], tz = c[1] - a[1], l = hyp(tx, tz), mx = (a[0] + c[0]) / 2, mz = (a[1] + c[1]) / 2;
  const side = inTerrace(mx - tz / l * .8, mz + tx / l * .8) ? -1 : 1;   // outward = away from the terrace
  const st = stations(pts, { step: 2.5, side }), rand = rnd(seed);
  const topAt = i => terraceH(st[i].x, st[i].z) + .02, H = .6, bw = .10;
  const info = footInfo(st, { H, bw, topAt, ground: (x, z) => (inTerrace(x, z) ? 1e3 : gnd(x, z)) });
  const tone = (i, y) => { const t = .92 + .12 * vnoise(st[i].u / 6 + y * .1, seed); return [t, t * .99, t * .97]; };
  const dEdge = skin(me, st, info, { H, bw, topAt, seed, plinthH: 3.5, plinthBatter: .12, mats: { body: mat, plinth: 'walRubble', course: 'walAshlar' } }, tone);
  parapetWall(me, st, topAt, dEdge, { thick: .5, h: h, mat: 'walAshlarGrey', cap: 'walAshlar' });
  for (let i = 0; i < st.length - 1; i++) { const p = st[i], q = st[i + 1], dx = q.x - p.x, dz = q.z - p.z, L = hyp(dx, dz); if (L > .05) ctx.b.nav.box((p.x + q.x) / 2, (p.z + q.z) / 2, L + .8, 1.8, -60, topAt(i) + h, -Math.atan2(dz, dx)); }
}
function esplanade(b, ctx) {
  const F = new Frame(J.x, J.F, J.z, J.rot), me = new Mesher();
  b.zone = 'justice';
  // cobbled floor (empedrado granadino) with stone bands
  polyFace(me.s('walCobble'), TERRACE.map(p => [p[0], p[1]]), [], (x, z) => [x, terraceH(x, z), z], (x, z) => [x, z], [.95, .93, .9], UP);
  const L2 = TERRACE.map(([x, z]) => [(x - J.x) * JU[0] + (z - J.z) * JU[1], localW(x, z)]);
  const inT = (u, w) => insidePolygon(u, w, L2);
  const band = (u0, w0, u1, w1, wd) => { const n = Math.ceil(hyp(u1 - u0, w1 - w0) / 1.0); for (let k = 0; k < n; k++) { const a = k / n, c = (k + 1) / n, pa = [lerp(u0, u1, a), lerp(w0, w1, a)], pc = [lerp(u0, u1, c), lerp(w0, w1, c)], mid = [(pa[0] + pc[0]) / 2, (pa[1] + pc[1]) / 2]; const dx = pc[0] - pa[0], dw = pc[1] - pa[1], l = hyp(dx, dw), nx = -dw / l * wd / 2, nw = dx / l * wd / 2;
    if (![[mid[0] + nx * 2, mid[1] + nw * 2], [mid[0] - nx * 2, mid[1] - nw * 2], mid].every(p => inT(p[0], p[1]))) continue;
    const P = (u, w) => { const [x, z] = F.xz(u, w); return [x, terraceH(x, z) + .015, z]; };
    me.s('walPatchAshlar').quad(P(pa[0] - nx, pa[1] - nw), P(pc[0] - nx, pc[1] - nw), P(pc[0] + nx, pc[1] + nw), P(pa[0] + nx, pa[1] + nw), [0, 0], [l, 0], [l, wd], [0, wd], [1, .98, .94], UP); } };
  for (const u of [-5, 0, 5]) band(u, 1, u, 48, .34);
  for (let w = 7; w < 46; w += 8) band(-12, w, 9, w, .3);
  for (let k = -3; k <= 3; k++) { band(k * 3 - 1.5, 3, k * 3 + 1.5, 6, .22); band(k * 3 + 1.5, 3, k * 3 - 1.5, 6, .22); }
  // navigation: strips of ramp that follow the terrace slope, kept inside the outline
  for (let w = 0; w < 50; w += 2) {
    const wm = w + 1, xs = [];
    for (let i = 0; i < L2.length; i++) { const a = L2[i], c = L2[(i + 1) % L2.length]; if ((a[1] > wm) !== (c[1] > wm)) xs.push(a[0] + (wm - a[1]) / (c[1] - a[1]) * (c[0] - a[0])); }
    xs.sort((p, q) => p - q);
    for (let k = 0; k + 1 < xs.length; k += 2) { const u0 = xs[k] + .25, u1 = xs[k + 1] - .25; if (u1 - u0 < .6) continue; F.navRamp(b, (u0 + u1) / 2, w + 1, u1 - u0, 2, -.03 * w, -.03 * (w + 2)); }
  }
  // retaining walls and parapets along the open edges
  terraceWall(me, ctx, [TERRACE[4], TERRACE[5]], 11); terraceWall(me, ctx, [TERRACE[5], TERRACE[6]], 12); terraceWall(me, ctx, [TERRACE[6], TERRACE[7]], 13); terraceWall(me, ctx, [TERRACE[7], TERRACE[8]], 14);
  // the barbican bastion on the south-west side of the forecourt
  { const bs = TOWERS.bastion, topW = terraceH(-46, 141) + 10.2;
    prismTower(me, ctx, bs, { top: topW, bw: .04, seed: 21, plinthH: 3.2, parapet: .8, merlons: false, ground: gnd, mats: { body: 'walTapialC', plinth: 'walRubble', course: 'walBrick', parapet: 'walTapialB' } }); }
  me.flush(b, [0, 0, 0], 0);
}

// ---------------------------------------------------------------- Pilar de Carlos V (Pedro Machuca, 1545): a Renaissance wall fountain against the curtain wall
// The frontal photograph (Chabe01, CC BY-SA 4.0) is mapped on the wall panel (14.8 x 6.35 m at 130 px/m); cornice, basin and side
// returns are real solids so the fountain has depth.
function pilar(b, ctx) {
  const me = new Mesher(), D0 = [-49.29, 121.88], dir = [.9531, .3025], nrm = [-.3025, .9531], sAlong = 17.5, WALL = 1.95;
  const px = D0[0] + dir[0] * sAlong + nrm[0] * WALL, pz = D0[1] + dir[1] * sAlong + nrm[1] * WALL;
  const P = new Frame(px, terraceH(px, pz), pz, Math.atan2(nrm[0], nrm[1]));
  b.zone = 'justice';
  const U0 = -7.58, U1 = 7.22, HP = 6.35, PXM = 130, base = (u, y) => [u - U0, y];
  const sand = me.s('walAshlar'), grey = me.s('walAshlarGrey');
  // the panel (decal) with a stone top cornice and side returns
  polyFace(me.s('gatPilar'), [[U0, 0], [U1, 0], [U1, HP], [U0, HP]], [], (u, y) => P.p(u, y, 0), base, [1, 1, 1], wantOut(P));
  fbox(sand, P, (U0 + U1) / 2, 0, -.75, U1 - U0, HP, 1.5, [1.02, .98, .92], 0b011100);
  fbox(sand, P, (U0 + U1) / 2, HP - .38, .22, U1 - U0 + .5, .38, .46, [1.04, 1, .94], 0b111101);
  fbox(sand, P, (U0 + U1) / 2, HP - .05, .3, U1 - U0 + .6, .1, .6, [1.06, 1.02, .96], 0b111101);
  // the basin: decal front (the lower strip of the photograph), grey stone lip and trough, returns
  const bw = 5.88, y1 = 1.0, depth = 1.05;
  polyFace(me.s('gatPilar'), [[-bw, 0], [bw, 0], [bw, y1 + .12], [-bw, y1 + .12]], [], (u, y) => P.p(u, y, depth), base, [.98, .98, .98], wantOut(P));
  fbox(grey, P, 0, y1 + .12, depth / 2 + .05, bw * 2 + .1, .1, depth + .2, [.95, .97, 1], 0b111101);
  for (const sgn of [-1, 1]) fbox(grey, P, sgn * bw, 0, depth / 2, .02, y1 + .12, depth, [.9, .92, .95], sgn < 0 ? 0b001000 : 0b000100);
  me.s('walWaterDark').quad(P.p(-bw + .1, y1 - .1, .1), P.p(bw - .1, y1 - .1, .1), P.p(bw - .1, y1 - .1, depth - .1), P.p(-bw + .1, y1 - .1, depth - .1), [0, 0], [1, 0], [1, 1], [0, 1], [1, 1, 1], UP);
  // the central pediment stands a little proud of the wall
  { const n = 28, cx = 0, cy = 4.14, R = 1.5, pts = []; for (let i = 0; i <= n; i++) { const t = Math.PI * (1 - i / n); pts.push([cx + Math.cos(t) * R, cy - .02 + Math.sin(t) * R]); }
    const soup = me.s('gatPilar');
    polyFace(soup, [...pts, [cx - R, cy - .02]], [], (u, y) => P.p(u, y, .2), base, [1.02, 1.02, 1.02], wantOut(P));
    for (let i = 0; i < n; i++) { const a = pts[i], c = pts[i + 1]; me.s('gatMarble').quad(P.p(a[0], a[1], 0), P.p(c[0], c[1], 0), P.p(c[0], c[1], .2), P.p(a[0], a[1], .2), [0, 0], [.2, 0], [.2, .2], [0, .2], [1, .98, .94], [(a[0] + c[0]) / 2 * 0 + (a[0] + c[0]) / 2 / R * P.d(1, 0)[0], (a[1] + c[1]) / 2 > cy ? 1 : 0, (a[0] + c[0]) / 2 / R * P.d(1, 0)[1]]); } }
  me.flush(b, [0, 0, 0], 0);
  for (const u of [-3.1, -.08, 3.1]) { const [x, , z] = P.p(u, 0, .45); b.jet(x, P.y0 + 1.75, z, nrm[0] * .5, nrm[1] * .5, .1); }
  P.navBox(b, 0, 1.0, U1 - U0, 2.2, -60, 8);
  // cypresses behind the wall, inside the enclosure
  for (let i = 0; i < 4; i++) plant(-34 + i * 1.8, 0, 120.8 + i * .55, CYPRESS, 11.5 + i * .6);
}

// ---------------------------------------------------------------- Puerta del Vino (c. 1348): free-standing gate between the Plaza de los Aljibes and the medina
const V = { x: -88.76, z: 68.29, rot: 1.3374, D: 7.5, W: 8.3, H: 10.29 };
function hipRoof(me, F, u0, u1, w0, w1, yE, rise, ridgeU, mat = 'roof') {
  // eave rectangle (u0..u1, w0..w1) at height yE; ridge along u from -ridgeU..ridgeU at the mid w
  const wm = (w0 + w1) / 2, yR = yE + rise, soup = me.s(mat), col = [1, .97, .94], sl = hyp(w1 - w0, rise * 2) / 2;
  const A = F.p(u0, yE, w1), B = F.p(u1, yE, w1), C = F.p(u1, yE, w0), D = F.p(u0, yE, w0), R0 = F.p(-ridgeU, yR, wm), R1 = F.p(ridgeU, yR, wm);
  const uv = (u, w) => [u * .55, w * .55];
  soup.quad(A, B, R1, R0, [0, 0], [u1 - u0, 0], [ridgeU * 2 + (u1 - u0) / 2 - ridgeU, sl], [0, sl], col, UP);
  soup.quad(C, D, R0, R1, [0, 0], [u1 - u0, 0], [(u1 - u0) / 2 + ridgeU, sl], [(u1 - u0) / 2 - ridgeU, sl], col, UP);
  soup.tri(D, A, R0, [0, 0], [w1 - w0, 0], [(w1 - w0) / 2, sl], col, UP);
  soup.tri(B, C, R1, [0, 0], [w1 - w0, 0], [(w1 - w0) / 2, sl], col, UP);
  // fascia + corbel row
  for (const [a, c, fu, fw] of [[[u0, w1], [u1, w1], 0, 1], [[u1, w0], [u0, w0], 0, -1]]) { wallQuad(me.s('walWood'), F, a[0], a[1], c[0], c[1], yE - .22, yE + .05, fu, fw, [.9, .85, .8]); }
  for (const [a, c, fu, fw] of [[[u1, w1], [u1, w0], 1, 0], [[u0, w0], [u0, w1], -1, 0]]) { wallQuad(me.s('walWood'), F, a[0], a[1], c[0], c[1], yE - .22, yE + .05, fu, fw, [.9, .85, .8]); }
}
function puertaDelVino(b, ctx) {
  const F = new Frame(V.x, 0, V.z, V.rot), me = new Mesher(), H = V.H, D = V.D, hw = 4.15;
  b.zone = 'vino';
  const hsE = horseshoe(1.72, 2.73, 5.41), hsW = hsE;
  // ---- east (inner, tiled) façade: the photograph as a decal, the opening cut out
  polyFace(me.s('gatVinoEast'), [[-hw, -.5], [hw, -.5], [hw, H], [-hw, H]], [openingPath(hsE, 0).map(p => [p[0], p[1]])], (u, y) => F.p(u, y, 0), (u, y) => [u + 4.0, Math.max(0, y)], [1, 1, 1], wantOut(F));
  // ---- west (outer, plain stucco) façade
  { const G = F.at(0, 0, -D, Math.PI), out = wantOut(G), hole = openingPath(hsW, 0).map(p => [p[0], p[1]]);
    polyFace(me.s('walRubble'), [[-hw, -.5], [hw, -.5], [hw, H], [-hw, H]], [hole], (u, y) => G.p(u, y, 0), (u, y) => [u + 1.5, y], [1.05, .98, .9], out);
    polyFace(me.s('walPatchBrick'), [[-hw, 4.2], [hw, 4.2], [hw, H], [-hw, H]], [], (u, y) => G.p(u, y, .03), (u, y) => [u, y], [1.12, 1.02, .88], out);
    // stucco alfiz with brick voussoirs, saw-tooth band, inscription band and the twin window
    polyFace(me.s('fineStucco'), [[-2.75, -.5], [2.75, -.5], [2.75, 7.0], [-2.75, 7.0]], [hole], (u, y) => G.p(u, y, .08), (u, y) => [u, y], [.95, .78, .55], out);
    const ring = openingPath(hsW, 0), cr = [0]; for (let i = 1; i < ring.length; i++) cr.push(cr[i - 1] + hyp(ring[i][0] - ring[i - 1][0], ring[i][1] - ring[i - 1][1]));
    ringFace(me.s('walBrickB'), G, ring, 0, .62, .12, (pt, i, sd) => [sd ? .62 : 0, cr[i]], [1.1, 1, .85]);
    sawtooth(me, G, -3.1, 3.1, 7.0, 7.8, .06, .18, .3, 'walBrickB');
    rectFace(me.s('frieze'), G, -3.0, 7.95, 3.0, 8.55, .1, (u, y) => [u * .45, y], [.95, .82, .62]);
    for (const uu of [-1.8, -.6, .6, 1.8]) rectFace(me.s('walPatchLime'), G, uu - .22, 8.1, uu + .22, 8.4, .12, (u, y) => [u, y], [.9, .85, .78]);
    windowAt(me, G, -.56, 8.9, .62, 1.55, .1); windowAt(me, G, .56, 8.9, .62, 1.55, .1);
    rectFace(me.s('fineStucco'), G, -2.0, 8.7, 2.0, 10.4, .06, (u, y) => [u, y], [.95, .78, .55]);
    rectFace(me.s('walWood'), G, 3.0, 7.6, 3.9, 8.9, .08, (u, y) => [u * .6, y * .6], [1, .9, .8]);
  }
  // north and south faces: rubble and brick masonry
  for (const [fu, name] of [[-hw, 'n'], [hw, 's']]) {
    const G = F.at(fu, 0, -D / 2, fu < 0 ? -Math.PI / 2 : Math.PI / 2), out = wantOut(G);
    polyFace(me.s('walRubble'), [[-D / 2, -.5], [D / 2, -.5], [D / 2, H], [-D / 2, H]], [], (u, y) => G.p(u, y, 0), (u, y) => [u + (name === 'n' ? 3 : 0), y], [1.04, .97, .9], out);
    polyFace(me.s('walPatchBrick'), [[-D / 2, 5.5], [D / 2, 5.0], [D / 2, H], [-D / 2, H]], [], (u, y) => G.p(u, y, .03), (u, y) => [u, y], [1.1, 1.02, .9], out);
    windowAt(me, G, name === 'n' ? -1.4 : 1.2, 7.2, .4, 1.1, .05);
  }
  // ---- the passage: stone jambs, brick vault, two inner arches, cobbled floor
  const pc = [0]; { const p = openingPath(hsE, 0); for (let i = 1; i < p.length; i++) pc.push(pc[i - 1] + hyp(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1])); }
  { const p = openingPath(hsE, 0);
    for (let i = 0; i < p.length - 1; i++) { const jamb = i === 0 || i === p.length - 2; soffit(me.s(jamb ? 'walAshlar' : 'walBrick'), F, [p[i], p[i + 1]], 0, 0, -D, jamb ? (k, w) => [-w, p[i + k][1]] : (k, w) => [pc[i + k], -w], [.85, .8, .74]); } }
  for (const w of [-2.4, -5.1]) { const ip = openingPath(horseshoe(1.5, 2.6, 4.7), 0), ic = [0]; for (let i = 1; i < ip.length; i++) ic.push(ic[i - 1] + hyp(ip[i][0] - ip[i - 1][0], ip[i][1] - ip[i - 1][1])); ringFace(me.s('walBrick'), F, ip, 0, .5, w, (pt, i, sd) => [sd ? .5 : 0, ic[i]], [.9, .85, .8]); ringFace(me.s('walBrick'), F, ip, 0, .5, w, (pt, i, sd) => [sd ? .5 : 0, ic[i]], [.9, .85, .8], -1); }
  floorQuad(me.s('walCobble'), F, -1.72, -D, 1.72, 0, 0, [.95, .93, .9], .5);
  // ---- hipped roof with timber corbels
  hipRoof(me, F, -hw - .85, hw + .85, -D - .85, .85, H, 2.6, 1.6);
  for (let u = -hw - .6; u <= hw + .6; u += .55) for (const [w, nm] of [[.85 - .4, 1], [-D - .45, -1]]) fbox(me.s('walWood'), F, u, H - .55, w, .16, .22, .9, [.9, .85, .8], 0b111101);
  // ---- nav: passage floor and solid walls
  F.navFloor(b, 0, -D / 2, 3.4, D + .2, 0);
  F.navBox(b, -(hw + 1.75) / 2, -D / 2, hw - 1.75, D, -60, 40); F.navBox(b, (hw + 1.75) / 2, -D / 2, hw - 1.75, D, -60, 40);
  // cobbled aprons both sides (empedrado), over the flat platform
  const apron = (G, w0, w1, uw) => polyFace(me.s('walCobble'), [[-uw, w0], [uw, w0], [uw, w1], [-uw, w1]], [], (u, w) => G.p(u, .02, w), (u, w) => [u, w], [.96, .94, .9], UP);
  apron(F, 0, 9, 6.0); apron(F, -D - 9, -D, 6.0);
  me.flush(b, [0, 0, 0], 0);
}

// ---------------------------------------------------------------- Plaza de los Aljibes, the cistern kiosk and the lane from the Justicia gate
const TOWERS_K = [[-113.6, 16.22], [-113.8, 18.62], [-112.25, 20.47], [-109.85, 20.68], [-107.99, 19.12], [-107.79, 16.72], [-109.34, 14.87], [-111.74, 14.67]];
const PLAZA = [[-119.9, 43.0], [-105.6, 49.3], [-105.3, 57.7], [-100.9, 58.4], [-98.8, 58.6], [-95.9, -3.7], [-115.4, -4.3], [-116.1, 9.2], [-122.6, 8.8], [-122.8, 12.7], [-124.2, 35.0]];
const LANE = [[-58.6, 117.4], [-56.0, 112.6], [-59.5, 107.5], [-70, 103.5], [-77.5, 99.5], [-79.5, 88], [-84, 77], [-88.5, 71.5]];
function plaza(b, ctx) {
  const me = new Mesher(); b.zone = 'aljibes';
  // compacted gravel with a stone-paved edge and the two cistern lids
  polyFace(me.s('walGravel'), PLAZA, [], (x, z) => [x, .018, z], (x, z) => [x * .7, z * .7], [1.05, .98, .92], UP);
  const inner = PLAZA.map(p => { const c = centroid(PLAZA); return [p[0] + (c[0] - p[0]) * .025, p[1] + (c[1] - p[1]) * .012]; });
  b.nav.floor(-107, 36, 42, 63, 0);
  for (const [x, z, w, d, rot] of [[-112, 43, 3.6, 2.2, .1], [-110.5, 29, 3.0, 3.0, .6]]) {
    boxSolid(me.s('walAshlarGrey'), x, .17, z, w, .34, d, rot, [1, .98, .94], 0b011111); boxSolid(me.s('walAshlar'), x, .42, z, w - .6, .16, d - .6, rot, [1, .98, .94], 0b011111);
  }
  // Los Aljibes kiosk: an octagonal whitewashed stall with a tiled cone roof
  { const k = TOWERS_K, c = centroid(k), n = k.length;
    for (let i = 0; i < n; i++) {
      const a = k[i], d = k[(i + 1) % n], len = hyp(d[0] - a[0], d[1] - a[1]), nx = -(d[1] - a[1]) / len, nz = (d[0] - a[0]) / len, flip = ((c[0] - a[0]) * nx + (c[1] - a[1]) * nz) > 0 ? -1 : 1;
      const want = [nx * flip, 0, nz * flip], soup = me.s('gatLime');
      soup.quad([a[0], .02, a[1]], [d[0], .02, d[1]], [d[0], 3.1, d[1]], [a[0], 3.1, a[1]], [0, 0], [len, 0], [len, 3.1], [0, 3.1], [.97, .95, .92], want);
      if (i % 2 === 0) { const mx = (a[0] + d[0]) / 2 + want[0] * .03, mz = (a[1] + d[1]) / 2 + want[2] * .03, tx = (d[0] - a[0]) / len, tz = (d[1] - a[1]) / len; me.s('walDarkOver').quad([mx - tx * .8, 1.05, mz - tz * .8], [mx + tx * .8, 1.05, mz + tz * .8], [mx + tx * .8, 2.3, mz + tz * .8], [mx - tx * .8, 2.3, mz - tz * .8], [0, 0], [1, 0], [1, 1], [0, 1], [1, 1, 1], want); }
      const top = [c[0] + (a[0] - c[0]) * 1.12, c[1] + (a[1] - c[1]) * 1.12], top2 = [c[0] + (d[0] - c[0]) * 1.12, c[1] + (d[1] - c[1]) * 1.12];
      me.s('roof').tri([top[0], 3.0, top[1]], [top2[0], 3.0, top2[1]], [c[0], 4.9, c[1]], [0, 0], [len * 1.1, 0], [len * .55, 2.2], [1, 1, 1], UP);
    }
    b.nav.box(c[0], c[1], 6.2, 6.2, -1, 4, .0);
    me.flush(b, [0, 0, 0], 0);
  }
  // trees of the plaza and the lane along the south side
  const pr = rnd(88);
  for (let i = 0; i < 9; i++) { const t = pr(), z = lerp(2, 52, t), x = lerp(-99, -101, pr()) + (i % 2 ? 0 : -2); plant(x, 0, z, PLANE, 9 + pr() * 5); }
  for (let i = 0; i < 5; i++) plant(-120 + pr() * 2, 0, lerp(14, 40, i / 4), PLANE, 8 + pr() * 4);
  plant(-92.5, 0, 56, CYPRESS, 10); plant(-92, 0, 50, CYPRESS, 9);
  // ---- the lane from the gate exit (platform level) to the Puerta del Vino: gravel strips + walkable floor
  b.zone = 'aljibes';
  for (let i = 0; i < LANE.length - 1; i++) {
    const a = LANE[i], c = LANE[i + 1], dx = c[0] - a[0], dz = c[1] - a[1], L = hyp(dx, dz), nx = -dz / L * 2.6, nz = dx / L * 2.6;
    me.s('walGravel').quad([a[0] - nx, .02, a[1] - nz], [c[0] - nx, .02, c[1] - nz], [c[0] + nx, .02, c[1] + nz], [a[0] + nx, .02, a[1] + nz], [a[0] * .7, a[1] * .7], [c[0] * .7, c[1] * .7], [c[0] * .7 + 1, c[1] * .7], [a[0] * .7 + 1, a[1] * .7], [1.05, .98, .92], UP);
    b.nav.floor((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, 5.6, L + 3, 0, Math.atan2(dx, dz) * 1 - 0);
  }
  // exit apron in front of the north door
  me.s('walCobble').quad([-62.5, .03, 119.6], [-54.5, .03, 122.2], [-52.5, .03, 113.4], [-61, .03, 111], [-62.5, 119.6], [-54.5, 122.2], [-52.5, 113.4], [-61, 111], [.95, .93, .9], UP);
  b.nav.floor(-57.6, 116.6, 9, 9, 0);
  me.flush(b, [0, 0, 0], 0);
}

// ---------------------------------------------------------------- build
export function build(b, ctx) {
  PER = ctx.perimeter;
  setLow(ctx.low);
  justiciaTower(b, ctx);
  esplanade(b, ctx);
  pilar(b, ctx);
  puertaDelVino(b, ctx);
  plaza(b, ctx);
}
