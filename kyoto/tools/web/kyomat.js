// KYOTO materials (TSL).  One "city" program for buildings (walls with facade programs, roofs of smoked kawara,
// metal, copper, cypress bark, wood, paint), one "ground" program (the surface raster of each tile picks asphalt,
// pavers, setts, gravel, moss ...), water, and an unlit far-LOD program lit by the bake alone.
// Baked irradiance (sky + bounce) is the indirect diffuse; the evening sun is live (cascaded shadows) near the camera
// and comes from the bake's sun visibility far away.  G.season: 0 autumn, 1 winter (15 cm of snow).
import * as THREE from 'three/webgpu';
import {
  Fn, attribute, texture, uniform, uniformArray, vec2, vec3, vec4, float, int, ivec2, mix, clamp, smoothstep, max, min, pow, dot, normalize, cross,
  positionWorld, positionView, positionViewDirection, normalView, normalWorld, uv, select, abs, sin, cos, fract, floor, step, exp, sqrt, length,
  mx_noise_float, mx_fractal_noise_float, cameraWorldMatrix, cameraViewMatrix, cameraPosition, renderGroup, pmremTexture, roughness as roughnessProp,
  materialEnvIntensity, textureLoad, inverseSqrt, fwidth, uint, normalWorldGeometry, atan,
} from 'three/tsl';

// shadow lookups pushed off the surface by more with distance: the low evening sun grazes the walls, and the far
// cascades' texels are tens of centimetres (acne otherwise)
// foliage lets the low sun through in places: where the bake (buildings and terrain, no trees) saw the sun, a live
// shadow (most likely a tree's) is lifted to a dappled share; building and hill shadows stay full
export const FOLIAGE = uniform(0.45).setGroup(renderGroup);
export const dappled = (vis) => Fn(([s]) => max(s, smoothstep(0.8, 1.0, vis).mul(FOLIAGE)));
export const shadowOffset = () => positionWorld.add(normalWorldGeometry.mul(length(positionWorld.sub(cameraPosition)).mul(0.0035).add(0.04)));

// tile names count from the core's corner (X0, Y0); the western enclaves have negative i.  The surface lookup texture
// spans every built region from (LX0, LY0): NX x NY tiles (keep in step with gen/frame.py REGIONS)
export const TILE = { X0: -1200, Y0: -3200, S: 200, LX0: -8800, LY0: -3200, NX: 67, NY: 49 };
const LI = (i) => i + (TILE.X0 - TILE.LX0) / TILE.S, LJ = (j) => j + (TILE.Y0 - TILE.LY0) / TILE.S;

export const G = {
  season: uniform(0.0).setGroup(renderGroup),          // 0 autumn .. 1 winter
  irrGain: uniform(Math.PI).setGroup(renderGroup),     // Cycles diffuse bake -> irradiance
  irrScale: uniform(1.0).setGroup(renderGroup),
  time: uniform(0.0).setGroup(renderGroup),
  dusk: uniform(1.0).setGroup(renderGroup),            // lit windows / lanterns
  sunDir: uniform(new THREE.Vector3(0, 1, 0)).setGroup(renderGroup),
  sunCol: uniform(new THREE.Vector3(1, 0.8, 0.6)).setGroup(renderGroup),
  csmFar: uniform(450.0).setGroup(renderGroup),
  dbg: uniform(0).setGroup(renderGroup),
  spec: uniform(1.0).setGroup(renderGroup),
  skyHor: uniform(new THREE.Vector3(1, 1, 1)).setGroup(renderGroup),   // sky colours for the water's own reflection
  skySun: uniform(new THREE.Vector3(1, 1, 1)).setGroup(renderGroup),
  skyZen: uniform(new THREE.Vector3(0.5, 0.6, 0.9)).setGroup(renderGroup),
};

const KIND = { wall: 0, machiya: 1, kawara: 2, roofmetal: 3, roofflat: 4, copper: 5, hiwada: 6, ridge: 7, wood: 8, ground: 9, stone: 10, paint: 11,
  water: 12, metal: 13, glass: 14, emissive: 15, gold: 16, cloth: 17, floor: 18, snow: 19, hedge: 20 };
export const IRR_MAX = 4.0;

class SpecEnvNode extends THREE.LightingNode {
  static get type() { return 'SpecEnvNode'; }
  constructor(envNode, occNode) { super(); this.envNode = envNode; this.occNode = occNode; }
  setup(builder) {
    let env = this.envNode;
    if (env.isTextureNode) env = pmremTexture(env.value);
    let reflectVec = null;
    const ctx = {
      getUV: () => {
        if (reflectVec === null) {
          reflectVec = positionViewDirection.negate().reflect(normalView);
          reflectVec = pow(roughnessProp, 4).mix(reflectVec, normalView).normalize();
          reflectVec = reflectVec.transformDirection(cameraWorldMatrix);
        }
        return reflectVec;
      },
      getTextureLevel: () => roughnessProp,
    };
    builder.context.radiance.addAssign(env.context(ctx).mul(materialEnvIntensity).mul(this.occNode));
  }
}

export class KyoMaterial extends THREE.MeshPhysicalNodeMaterial {
  static get type() { return 'KyoMaterial'; }
  constructor(opts) { super(); this.irrNode = opts.irrNode; this.occNode = opts.occNode; this.pro = opts.pro || []; }
  setupDiffuseColor(builder) {
    for (const v of this.pro) builder.stack.addToStack(v);       // running values, once and in order (see V below)
    super.setupDiffuseColor(builder);
  }
  setupLightMap() { return new THREE.IrradianceNode(this.irrNode); }
  setupEnvironment(builder) {
    const e = this.envNode || builder.environmentNode;
    return e ? new SpecEnvNode(e, this.occNode) : null;
  }
}

const lum = (c) => dot(c, vec3(0.2126, 0.7152, 0.0722));
const s2l = (c) => pow(c, vec3(2.2));
const h21 = (p) => fract(sin(dot(p, vec2(127.1, 311.7))).mul(43758.5453));
const h11 = (x) => fract(sin(x.mul(91.345)).mul(47453.5453));
export const decIrr = (a) => a.rgb.mul(a.rgb).mul(IRR_MAX);

// tangent-space normal -> view space, frame from the uv derivatives (no tangent attribute needed)
function perturb(Nt, uvn) {
  const p = positionView, N = normalView;
  const dp1 = p.dFdx(), dp2 = p.dFdy(), du1 = uvn.dFdx(), du2 = uvn.dFdy();
  const dp2p = cross(dp2, N), dp1p = cross(N, dp1);
  const T = dp2p.mul(du1.x).add(dp1p.mul(du2.x)), B = dp2p.mul(du1.y).add(dp1p.mul(du2.y));
  const det = max(dot(T, T), dot(B, B));
  const im = inverseSqrt(max(det, float(1e-20)));
  const n = T.mul(im).mul(Nt.x).add(B.mul(im).mul(Nt.y)).add(N.mul(Nt.z));
  const l = length(n);
  // degenerate uv derivatives (or a NaN anywhere: comparisons fail) -> the geometric normal; a NaN would spread
  // through the AO and the temporal AA over the whole screen
  return select(det.greaterThan(1e-20).and(l.greaterThan(0.2)).and(l.lessThan(10.0)), n.div(l), N);
}

function tables(mats, layers) {
  const P1 = [], AL = [];
  for (const m of mats) {
    const L = m.layer >= 0 ? layers[m.layer] : null;
    P1.push(new THREE.Vector4(Math.max(0, m.layer), L ? 1 / L.size : 1, KIND[m.kind] ?? 8, m.layer >= 0 ? 1 : 0));
    AL.push(new THREE.Vector4(...m.albedo, m.emit || 0));
  }
  return { p1: uniformArray(P1, 'vec4').setGroup(renderGroup), al: uniformArray(AL, 'vec4').setGroup(renderGroup) };
}

// ---------------------------------------------------------------------------------------------------------------
// buildings and structures
export function makeCityMaterial({ arrays, mats, layers }) {
  const { p1, al } = tables(mats, layers);
  const LY = Object.fromEntries(layers.map((l, i) => [l.name, i]));
  const c0 = attribute('c0', 'vec4'), c1 = attribute('c1', 'vec4'), irrA = attribute('irr', 'vec4');
  const mid = c1.x.mul(255.0).add(0.5).toInt();
  const q1 = p1.element(mid);
  const layer = q1.x.toInt(), kind = q1.z, hasTex = q1.w;
  const UV = uv();
  const wp = positionWorld;
  const pro = [];
  const V = (n) => { const v = n.toVar(); pro.push(v); return v; };
  const tA = (lay, c) => texture(arrays.albedo, c).depth(lay), tN = (lay, c) => texture(arrays.normal, c).depth(lay), tO = (lay, c) => texture(arrays.orm, c).depth(lay);
  const isK = (k) => abs(kind.sub(k)).lessThan(0.5);
  const flags = c1.w.mul(255.0).add(0.5).floor();
  const bit = (b) => fract(flags.div(b * 2)).greaterThanEqual(0.5);
  const seed = c1.z.mul(255.0).add(0.5).floor().div(255.0);     // exact per building: the sin hashes amplify interpolation noise
  const param = c1.y.mul(255.0).add(0.5).floor();

  // siding and most concrete walls: the smooth render layer, tinted (raw form-tie concrete only on some buildings)
  const MID = Object.fromEntries(mats.map((m) => [m.name, m.id]));
  const isSiding = mid.equal(int(MID.wall_siding));
  const smooth = isSiding.or(mid.equal(int(MID.wall_concrete)).and(h11(seed.mul(53.0)).lessThan(0.6)));
  const layerW = select(smooth, int(LY.plaster), layer);
  const st = UV.mul(q1.y);
  const A = V(tA(layerW, st)), O = V(tO(layerW, st));
  let Nt = V(tN(layerW, st).xyz.mul(2).sub(1));
  const albM = al.element(mid).rgb;
  const tint = V(s2l(c0.rgb));
  let col = V(select(hasTex.greaterThan(0.5), A.rgb, albM));
  // tintable layers (neutralised in tex_build) take the vertex colour; the rest keep their own colour
  col = V(mix(col, col.mul(tint).mul(1.25), A.a));
  // ceramic siding: shallow horizontal joints (lap boards or panel courses) and a vertical panel joint every 3.03 m
  const lapH = select(h11(seed.mul(29.0)).lessThan(0.5), float(0.2), float(0.455));
  const lap = fract(UV.y.div(lapH)).lessThan(float(0.018).div(lapH)).or(fract(UV.x.div(3.03)).lessThan(0.004));
  col = V(select(isSiding.and(lap), col.mul(0.72), col));
  let rough = V(mix(float(0.8), O.g, hasTex));
  let ao = V(mix(float(1.0), O.r, hasTex));
  let metal = V(float(0.0));
  let emit = V(vec3(0.0));
  const n1 = V(mx_fractal_noise_float(wp.mul(vec3(0.3, 0.3, 0.45)), int(3), float(2.0), float(0.5)));
  const n2 = V(mx_noise_float(wp.mul(vec3(1.9, 1.9, 2.3))));
  const u = UV.x, v = UV.y;
  const fh = max(c0.a.mul(25.5), float(2.4));            // floor height (m)

  // ---------- facade programs (walls)
  const isWall = isK(KIND.wall);
  const ws = param;
  const fl = floor(v.div(fh)), fv = v.sub(fl.mul(fh));    // floor index, height within the floor
  // house windows: a fixed column pitch per building, whole columns left blank, an aluminium sash around the glass
  const pitchH = select(h11(seed.mul(7.1)).lessThan(0.5), float(1.82), float(2.73));
  const ci = floor(u.div(pitchH)), cu = u.sub(ci.mul(pitchH)).sub(pitchH.mul(0.5));
  const colOn = h11(ci.add(seed.mul(131.0))).lessThan(0.62);
  const hw = h21(vec2(ci.add(seed.mul(131.0)), fl.add(seed.mul(17.0))));
  const wW = select(h11(ci.mul(3.1).add(seed)).lessThan(0.5), float(0.8), float(0.6));
  const inWinH = isWall.and(abs(ws.sub(1.0)).lessThan(0.5)).and(colOn).and(fv.greaterThan(0.9)).and(fv.lessThan(2.0)).and(v.greaterThan(0.5));
  const winH = inWinH.and(abs(cu).lessThan(wW.sub(0.04))).and(fv.greaterThan(0.94)).and(fv.lessThan(1.96));
  const sashH = inWinH.and(abs(cu).lessThan(wW)).and(winH.not());
  // office: ribbon windows with mullions every 1.6 m
  const winO = isWall.and(abs(ws.sub(2.0)).lessThan(0.5)).and(fv.greaterThan(0.85)).and(fv.lessThan(fh.sub(0.55))).and(v.greaterThan(fh.mul(0.98)));
  const mull = fract(u.div(1.6)).lessThan(0.06);
  // flats: balcony band (parapet panel 0..1.1, glass doors 1.1..2.3 behind), slab edges
  const flat = isWall.and(abs(ws.sub(3.0)).lessThan(0.5)).and(v.greaterThan(fh.mul(0.98)));
  const balPan = flat.and(fv.lessThan(1.1)).and(fract(u.div(3.6)).greaterThan(0.04));
  const balDoor = flat.and(fv.greaterThanEqual(1.1)).and(fv.lessThan(2.35)).and(fract(u.div(3.6)).greaterThan(0.08)).and(fract(u.div(3.6)).lessThan(0.92));
  const slab = isWall.and(ws.greaterThan(1.5)).and(ws.lessThan(3.5)).and(fv.lessThan(0.16)).and(v.greaterThan(1.0));
  // temple: posts every ~2 m, tie beams, lower boards
  const isTemple = isWall.and(abs(ws.sub(4.0)).lessThan(0.5));
  const post = fract(u.div(2.0)).lessThan(0.09);
  const beam = abs(v.sub(2.6)).lessThan(0.14).or(abs(v.sub(1.0)).lessThan(0.08)).or(v.lessThan(0.9));
  // shop fronts on the ground floor of street-facing walls
  const shop = isWall.and(bit(4)).and(v.lessThan(3.3)).and(v.greaterThan(-0.2));
  const shopGlass = shop.and(v.lessThan(2.6)).and(fract(u.div(2.4)).greaterThan(0.05));
  const sign = shop.and(v.greaterThanEqual(2.65)).and(v.lessThan(3.25));
  const signHue = h11(floor(u.div(5.0)).add(seed.mul(77.0)));
  const signCol = mix(mix(vec3(0.55, 0.08, 0.05), vec3(0.04, 0.12, 0.35), step(0.4, signHue)), vec3(0.75, 0.70, 0.62), step(0.75, signHue));
  const glassAny = winH.and(abs(cu).greaterThanEqual(0.02)).or(winO.and(mull.not())).or(balDoor).or(shopGlass);
  const frame = winO.and(mull).or(isTemple.and(post.or(beam)));
  const sash = sashH.or(winH.and(abs(cu).lessThan(0.02)));
  // dusk: a share of the windows lit warm
  const litW = bit(8).and(h21(vec2(ci.add(seed.mul(9.0)), fl.add(floor(u.div(1.6)).mul(0.37)))).lessThan(0.35));
  const glassCol = vec3(0.022, 0.025, 0.03).add(vec3(0.02, 0.022, 0.025).mul(hw));
  col = V(select(slab, vec3(0.55, 0.54, 0.52).mul(float(0.9).add(n2.mul(0.1))), col));
  col = V(select(balPan, mix(col, vec3(0.62, 0.62, 0.60), 0.5), col));
  col = V(select(frame, vec3(0.05, 0.04, 0.03), col));
  col = V(select(sash, vec3(0.42, 0.42, 0.41), col));
  col = V(select(glassAny, glassCol, col));
  col = V(select(sign, signCol, col));
  rough = V(select(glassAny, float(0.06), rough));
  metal = V(select(glassAny, float(0.0), metal));
  Nt = V(select(glassAny.or(sign), vec3(0.0, 0.0, 1.0), Nt));
  const shelf = step(0.82, fract(v.div(0.45))).mul(0.6).add(h21(vec2(floor(u.div(0.35)), floor(v.div(0.45))).add(seed)).mul(0.5)).add(smoothstep(2.6, 2.2, v).mul(0.3));
  const shopL = float(0.12).add(shelf.mul(0.35)).mul(float(0.6).add(hw.mul(0.6)));
  emit = V(emit.add(select(glassAny.and(litW.or(shopGlass)), vec3(1.0, 0.76, 0.52).mul(select(shopGlass, shopL, float(0.35).add(hw.mul(0.45)))).mul(G.dusk), vec3(0.0))));
  emit = V(emit.add(select(sign.and(h11(floor(u.div(5.0)).add(seed.mul(3.0))).lessThan(0.6)), signCol.mul(0.6).mul(G.dusk), vec3(0.0))));
  // weathering: rain streaks below sills and under eaves, splash dirt at the foot
  const streak = mx_noise_float(vec3(u.mul(1.3), v.mul(0.08), seed.mul(41.0))).mul(0.5).add(0.5);
  col = V(select(isWall.and(glassAny.not()), col.mul(float(0.92).add(n1.mul(0.1))).mul(float(1.0).sub(streak.mul(0.12))).mul(float(1.0).sub(smoothstep(0.6, 0.0, v).mul(0.25))), col));

  // ---------- machiya street front (u along the front, v height): bamboo 犬矢来 / stone base, 千本格子, doors with 暖簾, upper storey with 虫籠窓
  const isMach = isK(KIND.machiya);
  const woodC = tint;                                     // dark brown or 弁柄 red-brown
  const lat = fract(u.div(0.06));
  const fw = fwidth(u).div(0.06);                        // lattice period on screen: fade to the average when it gets small
  const slat = smoothstep(0.42, 0.42 + 0.08, lat).mul(smoothstep(0.98, 0.9, lat));
  const latM = mix(slat, float(0.6), smoothstep(0.12, 0.35, fw));
  const doorU = h11(seed.mul(13.0)).mul(4.0).add(1.0);
  const inDoor = abs(u.sub(doorU)).lessThan(0.9);
  const noren = isMach.and(inDoor).and(v.greaterThan(1.55)).and(v.lessThan(2.35)).and(h11(seed.mul(5.0)).lessThan(0.6));
  const norC = mix(mix(vec3(0.03, 0.05, 0.16), vec3(0.20, 0.05, 0.03), step(0.5, h11(seed.mul(23.0)))), vec3(0.6, 0.55, 0.45), step(0.85, h11(seed.mul(29.0))));
  const base = isMach.and(v.lessThan(0.48));
  const bamboo = base.and(h11(seed.mul(3.0)).lessThan(0.7));
  const bam = fract(u.div(0.035));
  const lattice = isMach.and(v.greaterThanEqual(0.48)).and(v.lessThan(2.55));
  const upper = isMach.and(v.greaterThanEqual(2.55));
  const uw = fract(u.div(3.4)).sub(0.5);                  // 虫籠窓 per 3.4 m bay
  const mushiko = upper.and(abs(uw).lessThan(0.17)).and(v.greaterThan(3.25)).and(v.lessThan(3.95));
  const mBar = fract(u.div(0.14)).lessThan(0.45);
  const plC = s2l(vec3(0.86, 0.83, 0.76)).mul(float(0.85).add(n2.mul(0.1)));
  const upperCol = mix(plC, mix(plC, s2l(vec3(0.62, 0.50, 0.36)), step(0.5, h11(seed.mul(41.0)))), 0.7);
  const behind = vec3(0.012, 0.010, 0.009);
  const PA = tA(int(LY.plaster), UV.mul(0.5));
  col = V(select(lattice, mix(behind, woodC.mul(float(0.75).add(lum(A.rgb).mul(0.9))), latM), col));
  col = V(select(bamboo, mix(vec3(0.17, 0.12, 0.06), vec3(0.30, 0.22, 0.11), smoothstep(0.1, 0.5, bam).mul(smoothstep(0.95, 0.6, bam))).mul(float(0.7).add(v.mul(0.8))), col));
  col = V(select(base.and(bamboo.not()), s2l(vec3(0.45, 0.44, 0.41)).mul(float(0.8).add(n2.mul(0.2))), col));
  col = V(select(upper, upperCol.mul(lum(PA.rgb).mul(1.6).add(0.3)), col));
  col = V(select(mushiko, mix(upperCol.mul(0.8), behind, mBar.select(0.0, 1.0)), col));
  col = V(select(noren, norC.mul(float(0.85).add(n2.mul(0.15))), col));
  Nt = V(select(lattice, normalize(vec3(sin(lat.mul(6.283)).mul(latM.mul(0.8)), 0.0, 1.0)), Nt));
  Nt = V(select(bamboo, normalize(vec3(sin(bam.mul(6.283)).mul(0.7), v.sub(0.24).mul(-2.0), 1.0)), Nt));
  Nt = V(select(upper.or(noren), vec3(0.0, 0.0, 1.0), Nt));
  rough = V(select(isMach, float(0.75), rough));
  ao = V(select(lattice, ao.mul(mix(float(0.55), float(1.0), latM)), ao));
  emit = V(emit.add(select(lattice.and(h11(seed.mul(61.0)).lessThan(0.45)), vec3(1.0, 0.7, 0.42).mul(float(1.0).sub(latM)).mul(0.25).mul(G.dusk), vec3(0.0))));

  // ---------- roofs: smoked kawara (桟瓦; 本瓦 for temples: param), u along the eave, v up the slope
  const isKaw = isK(KIND.kawara);
  const hon = mid.equal(int(mats.findIndex((m) => m.name === 'hongawara')));
  const pu = select(hon, float(0.30), float(0.29)), pv = select(hon, float(0.30), float(0.235));
  const tu = u.div(pu), tv = v.div(pv);
  const cx = fract(tu), cy = fract(tv);
  const tid = vec2(floor(tu), floor(tv));
  // sangawara profile: a broad pan and a narrow roll per tile; hongawara: round tile over two flat ones
  const prof = select(hon, smoothstep(0.62, 0.70, cx).mul(smoothstep(0.98, 0.9, cx)), sin(cx.mul(6.2832)).mul(0.5).add(0.5));
  const dprof = select(hon, smoothstep(0.62, 0.70, cx).sub(smoothstep(0.9, 0.98, cx)).mul(6.0), cos(cx.mul(6.2832)).mul(1.6));
  const fwk = fwidth(tu).add(fwidth(tv));
  const fade = smoothstep(0.35, 0.8, fwk);                 // far: average the relief away
  const lip = smoothstep(0.08, 0.0, cy);                   // each course's lower edge overlaps the next
  const tvar = h21(tid.add(seed.mul(57.0)));
  const kawC = vec3(0.085, 0.09, 0.10).mul(float(0.85).add(tvar.mul(0.28))).mul(float(0.93).add(prof.mul(0.12)));
  const lichen = smoothstep(0.35, 0.75, n1.add(n2.mul(0.3))).mul(0.4);
  col = V(select(isKaw, mix(mix(kawC.mul(float(1.0).sub(lip.mul(0.3))), vec3(0.12, 0.12, 0.10), lichen.mul(0.6)), vec3(0.09, 0.095, 0.10), fade.mul(0.7)), col));
  Nt = V(select(isKaw, normalize(vec3(dprof.mul(float(1.0).sub(fade)).mul(0.9), lip.mul(-1.3).mul(float(1.0).sub(fade)), 1.0)), Nt));
  rough = V(select(isKaw, mix(float(0.32), float(0.55), tvar.mul(0.5).add(lichen)), rough));
  ao = V(select(isKaw, mix(float(0.78).add(prof.mul(0.22)), float(0.92), fade).mul(float(1.0).sub(lip.mul(0.2))), ao));
  metal = V(select(isKaw, float(0.15), metal));            // ibushi silver sheen
  // ridge stacks (熨斗瓦): layered lines
  const isRidge = isK(KIND.ridge);
  const layr = fract(v.div(0.07));
  col = V(select(isRidge, vec3(0.10, 0.105, 0.11).mul(float(0.8).add(smoothstep(0.0, 0.25, layr).mul(0.35))), col));
  rough = V(select(isRidge, float(0.4), rough));
  metal = V(select(isRidge, float(0.15), metal));
  // coloured steel roofs with standing seams; flat roofs
  const isRM = isK(KIND.roofmetal);
  const seam = fract(u.div(0.455));
  col = V(select(isRM, tint.mul(float(0.85).add(n2.mul(0.08))).mul(float(1.0).sub(smoothstep(0.03, 0.0, seam).mul(0.4))), col));
  Nt = V(select(isRM, normalize(vec3(smoothstep(0.0, 0.04, seam).sub(smoothstep(0.96, 1.0, seam)).mul(0.6), 0.0, 1.0)), Nt));
  rough = V(select(isRM, float(0.45), rough));
  const isRF = isK(KIND.roofflat);
  col = V(select(isRF, tint.mul(0.6).mul(float(0.75).add(n1.mul(0.25))).mul(float(1.0).sub(step(fract(u.div(3.0)), 0.015).mul(0.2))), col));
  // copper (green patina), cypress bark (fine courses)
  const isCu = isK(KIND.copper);
  col = V(select(isCu, mix(vec3(0.10, 0.28, 0.22), vec3(0.20, 0.40, 0.33), n2.mul(0.5).add(0.5)).mul(float(1.0).sub(smoothstep(0.92, 1.0, fract(v.div(0.6))).mul(0.3))), col));
  rough = V(select(isCu, float(0.6), rough));
  const isHi = isK(KIND.hiwada);
  const hl = fract(v.div(0.012));
  col = V(select(isHi, vec3(0.085, 0.05, 0.032).mul(float(0.85).add(n2.mul(0.15))).mul(float(0.9).add(hl.mul(0.15))), col));
  rough = V(select(isHi, float(0.85), rough));
  // eave woodwork: fascia (param 1), soffit with exposed rafters (param 2)
  const isWood = isK(KIND.wood);
  const raft = isWood.and(param.equal(2.0)).and(fract(u.div(0.45)).lessThan(0.22));
  col = V(select(isWood, col.mul(0.8), col));
  col = V(select(raft, col.mul(0.55), col));
  ao = V(select(isWood.and(param.equal(2.0)), ao.mul(0.75), ao));
  // paints, metals, glass, gold, emissive
  const isPaint = isK(KIND.paint);
  col = V(select(isPaint, albM.mul(tint).mul(float(0.85).add(lum(A.rgb).mul(0.5))).mul(float(0.95).add(n2.mul(0.05))), col));
  // torii donor inscriptions: two columns of brush strokes (奉納 / the donor) in black ink on vermilion
  const insc = isPaint.and(param.equal(7.0));
  const iu = fract(u.mul(2.0)), iv = v.mul(9.0);
  const glyph = h21(vec2(floor(iu.mul(2.0)), floor(iv)).add(seed.mul(17.0)));
  const stroke = step(0.35, fract(iv)).mul(step(fract(iv), 0.9)).mul(step(0.18, fract(iu.mul(2.0))).mul(step(fract(iu.mul(2.0)), 0.82)))
    .mul(step(0.25, h21(vec2(floor(iu.mul(6.0)), floor(iv.mul(3.0))).add(glyph))));
  col = V(select(insc, mix(col, vec3(0.01, 0.01, 0.01), stroke.mul(0.92)), col));
  rough = V(select(isPaint, float(0.55), rough));
  const isMetal = isK(KIND.metal);
  col = V(select(isMetal, albM.mul(float(0.8).add(lum(A.rgb).mul(0.5))), col));
  metal = V(select(isMetal, float(0.6), metal)); rough = V(select(isMetal, float(0.45), rough));
  const isGlass = isK(KIND.glass);
  col = V(select(isGlass, vec3(0.015, 0.017, 0.02), col)); rough = V(select(isGlass, float(0.05), rough));
  const isGold = isK(KIND.gold);
  col = V(select(isGold, albM, col)); metal = V(select(isGold, float(1.0), metal)); rough = V(select(isGold, float(0.3).add(n2.mul(0.1)), rough));
  const isEm = isK(KIND.emissive);
  emit = V(emit.add(select(isEm, albM.mul(al.element(mid).w.mul(0.12)).mul(G.dusk), vec3(0.0))));
  col = V(select(isEm, albM.mul(0.5), col));
  const isCloth = isK(KIND.cloth);
  col = V(select(isCloth, tint.mul(float(0.85).add(n2.mul(0.15))), col)); rough = V(select(isCloth, float(0.95), rough));

  // ---------- hedges: a clipped leafy mass (small leaves, dark gaps), autumn: a few reddish tips
  const isHedge = isK(KIND.hedge);
  const hl1 = mx_noise_float(wp.mul(9.0)), hl2 = mx_noise_float(wp.mul(23.0));
  const hcol = vec3(0.035, 0.07, 0.022).mul(float(0.7).add(hl1.mul(0.35)).add(hl2.mul(0.25))).add(vec3(0.05, 0.0, 0.0).mul(smoothstep(0.55, 0.8, hl2)).mul(float(1.0).sub(G.season)));
  col = V(select(isHedge, hcol, col));
  Nt = V(select(isHedge, normalize(vec3(hl1.mul(0.9), hl2.mul(0.9), 1.0)), Nt));
  rough = V(select(isHedge, float(0.7), rough));
  ao = V(select(isHedge, ao.mul(float(0.6).add(hl2.mul(0.25)).add(0.15)), ao));

  // ---------- winter: snow on everything facing up (roofs carry it; steep faces shed it)
  const nW = normalWorld;
  const up = nW.z;
  const snowN = mx_fractal_noise_float(wp.mul(0.9), int(2), float(2.0), float(0.5));
  // under roofs, eaves and arcades (little sky in the bake) the floor stays dry
  const skyK = smoothstep(0.06, 0.22, lum(decIrr(irrA)));
  const snowK = V(smoothstep(0.42, 0.75, up.add(snowN.mul(0.12))).mul(G.season).mul(select(isWall.or(glassAny), float(0.0), float(1.0))).mul(skyK));
  const snowCol = vec3(0.80, 0.82, 0.86).mul(float(0.92).add(n2.mul(0.06)));
  col = V(mix(col, snowCol, snowK));
  rough = V(mix(rough, float(0.55), snowK));
  metal = V(mix(metal, float(0.0), snowK));
  Nt = V(normalize(mix(Nt, vec3(n2.mul(0.08), snowN.mul(0.08), 1.0), snowK)));
  ao = V(mix(ao, float(1.0), snowK.mul(0.7)));

  const irr = decIrr(irrA).mul(G.irrGain).mul(G.irrScale).mul(ao).mul(float(1.0).add(G.season.mul(0.25)));
  const occ = clamp(lum(decIrr(irrA)).div(0.5), 0.05, 1.0).pow(0.8);
  const mat = new KyoMaterial({ irrNode: irr, occNode: occ, pro });
  mat.receivedShadowPositionNode = shadowOffset();
  mat.receivedShadowNode = dappled(irrA.a);
  const dbgOn = G.dbg.greaterThan(0.5);
  mat.colorNode = select(dbgOn, vec3(0.0), col);
  mat.emissiveNode = select(dbgOn, select(G.dbg.lessThan(1.5), col, select(G.dbg.lessThan(2.5), irr.mul(0.3), vec3(irrA.a))), emit);
  mat.normalNode = perturb(Nt, select(isK(KIND.kawara).or(isK(KIND.machiya)).or(isK(KIND.roofmetal)), UV, st));
  mat.roughnessNode = clamp(rough, 0.09, 1.0);
  mat.metalnessNode = metal;
  mat.specularIntensityNode = select(dbgOn, float(0.0), float(0.6)).mul(G.spec);
  return mat;
}

// ---------------------------------------------------------------------------------------------------------------
// ground: the tile's surface raster (an array texture pool; a small lookup texture maps tiles to slots)
export class SurfPool {
  constructor(n = 48, size = 400) {
    this.n = n; this.size = size;
    this.tex = new THREE.DataArrayTexture(new Uint8Array(size * size * n), size, size, n);
    this.tex.format = THREE.RedFormat; this.tex.type = THREE.UnsignedByteType;
    this.tex.minFilter = this.tex.magFilter = THREE.NearestFilter; this.tex.generateMipmaps = false; this.tex.needsUpdate = true;
    this.look = new THREE.DataTexture(new Uint8Array(TILE.NX * TILE.NY), TILE.NX, TILE.NY, THREE.RedFormat, THREE.UnsignedByteType);
    this.look.minFilter = this.look.magFilter = THREE.NearestFilter; this.look.needsUpdate = true;
    this.free = [...Array(n).keys()]; this.of = new Map();
  }
  put(name, i, j, data) {
    if (this.of.has(name) || !this.free.length) return false;
    const s = this.free.shift(); this.of.set(name, { s, i, j });
    this.tex.image.data.set(data, s * this.size * this.size);
    this.tex.addLayerUpdate(s); this.tex.needsUpdate = true;
    this.look.image.data[LJ(j) * TILE.NX + LI(i)] = s + 1; this.look.needsUpdate = true;
    return true;
  }
  drop(name) {
    const e = this.of.get(name); if (!e) return;
    this.of.delete(name); this.free.push(e.s);
    this.look.image.data[LJ(e.j) * TILE.NX + LI(e.i)] = 0; this.look.needsUpdate = true;
  }
}

export const SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
  'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck', 'masa'];

export function makeGroundMaterial({ arrays, mats, layers, pool }) {
  const LY = Object.fromEntries(layers.map((l, i) => [l.name, i]));
  const SZ = Object.fromEntries(layers.map((l) => [l.name, 1 / l.size]));
  const S = Object.fromEntries(SURF.map((n, i) => [n, i]));
  const c1 = attribute('c1', 'vec4'), irrA = attribute('irr', 'vec4');
  const wp = positionWorld;
  const pro = [];
  const V = (n) => { const v = n.toVar(); pro.push(v); return v; };
  // surface id: the raster (jittered a little for soft borders), or the vertex (bridge decks)
  const rel = wp.xy.sub(vec2(TILE.X0, TILE.Y0)).div(TILE.S);
  const tij = floor(wp.xy.sub(vec2(TILE.LX0, TILE.LY0)).div(TILE.S));      // lookup texel
  const lk = textureLoad(pool.look, ivec2(clamp(tij.x, 0, TILE.NX - 1).toInt(), clamp(tij.y, 0, TILE.NY - 1).toInt())).r.mul(255.0).add(0.5).floor();
  const jit = vec2(mx_noise_float(wp.mul(0.9)), mx_noise_float(wp.mul(0.9).add(17.3))).mul(0.35 / TILE.S);
  const luv = fract(rel.add(jit));
  const lay0 = max(lk.sub(1.0), 0.0).toInt();
  const sidR0 = V(texture(pool.tex, vec2(luv.x, luv.y)).depth(lay0).r.mul(255.0).add(0.5).floor());
  // between natural surfaces (moss, gravel, sand, soil, forest ...) a wider, organic wander of the border: the raster's
  // half-metre steps and the hero gardens' triangles never show; roads and paving keep their crisp edges
  const NATS = ['soil', 'grass', 'moss', 'forest', 'riverbed', 'sand', 'gravel', 'farm'].map((n) => SURF.indexOf(n));
  const isNat = (x) => NATS.reduce((acc, id) => acc.or(abs(x.sub(id)).lessThan(0.5)), abs(x.sub(NATS[0])).lessThan(0.5));
  const jit2 = vec2(mx_noise_float(vec3(wp.xy.mul(0.42), 3.7)).mul(0.75).add(mx_noise_float(vec3(wp.xy.mul(1.6), 5.3)).mul(0.3)),
    mx_noise_float(vec3(wp.xy.mul(0.42), 9.1)).mul(0.75).add(mx_noise_float(vec3(wp.xy.mul(1.6), 1.9)).mul(0.3))).mul(1.0 / TILE.S);
  const luv2 = clamp(fract(rel).add(jit2), 0.5 / 400, 1.0 - 0.5 / 400);
  const sidR2 = V(texture(pool.tex, luv2).depth(lay0).r.mul(255.0).add(0.5).floor());
  const sidR = V(select(isNat(sidR0).and(isNat(sidR2)), sidR2, sidR0));
  const vs = c1.w.mul(255.0).add(0.5).floor();
  const midG = c1.x.mul(255.0).add(0.5).floor();
  const isSand = midG.equal(float(mats.findIndex((m) => m.name === 'sand_raked'))), isMossM = midG.equal(float(mats.findIndex((m) => m.name === 'moss_mound')));
  const sid = V(select(isSand, float(S.sand), select(isMossM, float(S.moss), select(vs.greaterThan(0.5), vs, select(lk.greaterThan(0.5), sidR, float(S.none))))));
  const is = (n) => abs(sid.sub(S[n])).lessThan(0.5);
  const n1 = V(mx_fractal_noise_float(wp.mul(0.18), int(3), float(2.0), float(0.5)));
  const n2 = V(mx_noise_float(wp.mul(2.1)));
  // texture layer and scale per surface (one sample set per pixel)
  const pick = (pairs, dflt) => pairs.reduceRight((acc, [n, val]) => select(is(n), float(val), acc), float(dflt));
  const lay = V(pick([['asphalt', LY.asphalt], ['asphalt_lane', LY.asphalt], ['sidewalk', LY.paving], ['stone_sett', LY.stone_sett], ['stone_slab', LY.stone_sett],
    ['gravel', LY.gravel], ['graves', LY.gravel], ['sand', LY.gravel], ['ballast', LY.gravel], ['soil', LY.soil], ['farm', LY.soil], ['grass', LY.grass], ['moss', LY.moss],
    ['forest', LY.forest], ['riverbed', LY.pebbles], ['concrete', LY.concrete], ['wood_deck', LY.wood_grey], ['tactile', LY.paving], ['masa', LY.gravel]], LY.concrete));
  const scl = V(pick([['asphalt', SZ.asphalt], ['asphalt_lane', SZ.asphalt], ['sidewalk', SZ.paving], ['stone_sett', SZ.stone_sett], ['stone_slab', SZ.stone_sett * 0.5],
    ['gravel', SZ.gravel], ['graves', SZ.gravel], ['sand', SZ.gravel * 2], ['ballast', SZ.gravel * 0.7], ['soil', SZ.soil], ['farm', SZ.soil], ['grass', SZ.grass], ['moss', SZ.moss],
    ['forest', SZ.forest], ['riverbed', SZ.pebbles], ['concrete', SZ.concrete * 0.5], ['wood_deck', SZ.wood_grey], ['tactile', SZ.paving], ['masa', SZ.gravel * 2.6]], SZ.concrete * 0.5));
  const st = wp.xy.mul(scl);
  const A = V(texture(arrays.albedo, st).depth(lay.toInt())), O = V(texture(arrays.orm, st).depth(lay.toInt()));
  let Nt = V(texture(arrays.normal, st).depth(lay.toInt()).xyz.mul(2).sub(1));
  let col = V(A.rgb);
  let rough = V(O.g); let ao = V(O.r);
  // tone per surface
  col = V(select(is('asphalt'), col.mul(0.75).mul(float(0.85).add(n1.mul(0.25))), col));
  col = V(select(is('asphalt_lane'), col.mul(0.95).mul(float(0.8).add(n1.mul(0.35))), col));
  col = V(select(is('concrete').or(is('none')), col.mul(vec3(0.85, 0.84, 0.82)).mul(float(0.75).add(n1.mul(0.35))), col));
  col = V(select(is('none'), mix(col, texture(arrays.albedo, wp.xy.mul(SZ.soil)).depth(int(LY.soil)).rgb, smoothstep(0.1, 0.5, n1).mul(0.7)), col));
  col = V(select(is('sand'), col.mul(1.3), col));
  // まさ土: the Kamo's riverside paths, fine beige decomposed granite, worn a little darker along the middle
  col = V(select(is('masa'), col.mul(vec3(1.12, 0.94, 0.72)).mul(float(0.95).add(n1.mul(0.12))), col));
  // raked sand: parallel ridges along the mesh uv (銀沙灘)
  const rk = fract(attribute('uv', 'vec2').y.div(0.12));
  col = V(select(isSand, vec3(0.62, 0.6, 0.56).mul(float(0.88).add(smoothstep(0.0, 0.5, rk).mul(smoothstep(1.0, 0.5, rk)).mul(0.22))), col));
  Nt = V(select(isSand, normalize(vec3(0.0, sin(rk.mul(6.283)).mul(0.6), 1.0)), Nt));
  col = V(select(is('ballast'), col.mul(0.6), col));
  col = V(select(is('farm'), col.mul(0.6), col));
  col = V(select(is('riverbed'), col.mul(0.45), col));
  col = V(select(is('tactile'), vec3(0.42, 0.32, 0.04).mul(float(0.85).add(n2.mul(0.1))), col));      // weathered yellow blocks
  rough = V(select(is('riverbed'), float(0.25), rough));
  // autumn: grass straw-coloured, fallen maple leaves on moss / gravel / soil / forest floor
  const autumn = float(1.0).sub(G.season);
  const leafy = is('moss').or(is('forest')).or(is('soil')).or(is('gravel')).or(is('grass')).or(is('none'));
  const leafM = smoothstep(0.15, 0.55, mx_fractal_noise_float(wp.mul(0.5), int(2), float(2.0), float(0.5)).add(n2.mul(0.15))).mul(leafy.select(1.0, 0.0)).mul(autumn);
  const LA = texture(arrays.albedo, wp.xy.mul(SZ.leaves)).depth(int(LY.leaves));
  const leafCol = LA.rgb.mul(vec3(1.25, 0.75, 0.5)).mul(float(0.9).add(n2.mul(0.2)));
  col = V(select(is('grass'), mix(col, col.mul(vec3(1.15, 0.95, 0.55)), autumn.mul(0.6)), col));
  col = V(mix(col, leafCol, leafM.mul(select(is('forest'), float(0.9), float(0.55)))));
  // winter: snow everywhere but on the carriageways (wet and dark there, slush along the edges)
  const road = is('asphalt').or(is('asphalt_lane'));
  const sn = mx_fractal_noise_float(wp.mul(0.35), int(3), float(2.0), float(0.5));
  const trod = smoothstep(0.1, 0.6, mx_noise_float(wp.mul(vec3(0.6, 0.6, 1.0))).add(n2.mul(0.2)));
  const snowK = V(G.season.mul(select(road, smoothstep(0.35, 0.75, sn).mul(0.5), select(is('sidewalk').or(is('stone_sett')).or(is('stone_slab')), float(1.0).sub(trod.mul(0.45)), float(1.0))))
    .mul(smoothstep(0.06, 0.22, lum(decIrr(irrA)))));                 // dry under arcades, gates and deep eaves
  const SA = texture(arrays.albedo, wp.xy.mul(SZ.snow)).depth(int(LY.snow));
  col = V(select(road, mix(col, col.mul(0.45), G.season), col));
  rough = V(select(road, mix(rough, float(0.12), G.season), rough));
  col = V(mix(col, SA.rgb.mul(1.05), snowK));
  rough = V(mix(rough, float(0.6), snowK));
  Nt = V(normalize(mix(Nt, vec3(0.0, 0.0, 1.0), snowK.mul(0.6))));

  const irr = decIrr(irrA).mul(G.irrGain).mul(G.irrScale).mul(ao).mul(float(1.0).add(G.season.mul(0.25)));
  const occ = clamp(lum(decIrr(irrA)).div(0.5), 0.05, 1.0).pow(0.8);
  const mat = new KyoMaterial({ irrNode: irr, occNode: occ, pro });
  mat.receivedShadowPositionNode = shadowOffset();
  mat.receivedShadowNode = dappled(irrA.a);
  const dbgOn = G.dbg.greaterThan(0.5);
  mat.colorNode = select(dbgOn, vec3(0.0), col);
  mat.emissiveNode = select(dbgOn, select(G.dbg.lessThan(1.5), col, select(G.dbg.lessThan(2.5), irr.mul(0.3), vec3(irrA.a))), vec3(0.0));
  mat.normalNode = perturb(Nt, st);
  mat.roughnessNode = clamp(rough, 0.09, 1.0);
  mat.specularIntensityNode = select(dbgOn, float(0.0), float(0.5)).mul(G.spec);
  return mat;
}

// ---------------------------------------------------------------------------------------------------------------
// water: dark and glossy with small animated ripples.  The environment map has only sky, so near the horizon (where the
// banks, trees and houses would be) the reflection turns to a dark surround, more so where the bake saw little sky.
export function makeWaterMaterial() {
  const wp = positionWorld, t = G.time;
  const irrA = attribute('irr', 'vec4');
  const irr = decIrr(irrA).mul(G.irrGain);
  const open = clamp(lum(irr).sub(0.6).div(1.4), 0.0, 1.0);          // ~1 on the open river, low in a canal or a garden pond
  const still = attribute('c1', 'vec4').y.greaterThan(0.5);          // a garden pond (the heroes' water)
  const fq = select(still, float(2.8), float(1.0));                   // a pond only shivers in fine ripples, the river rolls
  const r1 = mx_noise_float(vec3(wp.xy.mul(fq.mul(0.9)).add(vec2(t.mul(0.35), t.mul(0.1))), t.mul(0.2)));
  const r2 = mx_noise_float(vec3(wp.xy.mul(fq.mul(2.7)).sub(vec2(t.mul(0.2), t.mul(0.5))), t.mul(0.4)));
  const amp = select(still, float(0.006), mix(float(0.025), float(0.09), open));
  const nx0 = r1.mul(0.10).add(r2.mul(0.05)).mul(amp.mul(10.0)), ny0 = mx_noise_float(vec3(wp.xy.mul(1.1).add(31.0), t.mul(0.3))).mul(amp);
  // running water (rivers, canals, streams: the flow of the nearest OSM waterway, packed in c0): ripples drawn out
  // along the current and carried downstream; two phases cross-fade so the pattern moves without stretching
  const fl = attribute('c0', 'vec4');
  const fsp = fl.z.mul(2.0).mul(step(0.5, fl.w)).mul(select(still, float(0.0), float(1.0)));     // m/s
  const fdir = normalize(fl.xy.mul(2.0).sub(1.0).add(vec2(1e-4, 0.0)));
  // world-aligned noise carried downstream (no rotated frame: the interpolated direction would swing a far-off origin
  // and fan the pattern out), drawn into streaks by averaging along the current
  const PH = 1.8, ph0 = fract(t.div(PH)), ph1 = fract(t.div(PH).add(0.5));
  const w0 = float(1.0).sub(abs(ph0.mul(2.0).sub(1.0))), w1 = float(1.0).sub(w0);
  const adv = fsp.mul(PH);
  const n2 = (q, z) => vec2(mx_noise_float(vec3(q, z)), mx_noise_float(vec3(q, z.add(9.0))));
  const streak = (q) => {
    const a = q.mul(0.9), b = q.mul(3.1), d1 = fdir.mul(0.55), d2 = fdir.mul(0.16);
    return n2(a.sub(d1), float(1.7)).add(n2(a, float(1.7))).add(n2(a.add(d1), float(1.7))).mul(0.33)
      .add(n2(b.sub(d2), float(4.2)).add(n2(b.add(d2), float(4.2))).mul(0.22));
  };
  const g = streak(wp.xy.sub(fdir.mul(ph0.mul(adv)))).mul(w0).add(streak(wp.xy.sub(fdir.mul(ph1.mul(adv))).add(vec2(17.3, 5.1))).mul(w1));
  const famp = clamp(fsp.mul(0.07), 0.0, 0.09);
  const flowing = smoothstep(0.04, 0.2, fsp);
  const nx = mix(nx0.mul(0.4), g.x.mul(famp), flowing);
  const ny = mix(ny0.mul(0.4), g.y.mul(famp), flowing);
  const mat = new KyoMaterial({ irrNode: irr.mul(0.45), occNode: float(0.0) });
  // nearly black to the sun: its shadows (the dappled trees) would draw the surface like paving; what lies under the
  // water (a shallow open river shows its pebbly bed, ponds and canals stay dark) is lit by the sky alone, below
  mat.colorNode = vec3(0.006, 0.008, 0.008);
  const nW = normalize(vec3(nx, ny, 1.0));
  mat.normalNode = transformDir(nW);
  mat.roughnessNode = select(still, float(0.03), mix(mix(float(0.04), float(0.08), open), float(0.045), flowing));  // a still pond mirrors the sun as a small glint, the river spreads it
  mat.metalnessNode = float(0.0);
  mat.specularIntensityNode = float(1.0);                  // the sun's glint stays physical
  const V = normalize(wp.sub(cameraPosition));
  const R = V.sub(nW.mul(dot(V, nW).mul(2.0)));
  const cosv = clamp(dot(V.negate(), nW), 0.0, 1.0);
  const fres = float(0.02).add(float(0.98).mul(pow(float(1.0).sub(cosv), 5.0)));
  const toSun = pow(max(dot(normalize(vec3(R.x, R.y, 0.0).add(vec3(1e-5, 0, 0))), normalize(vec3(G.sunDir.x, G.sunDir.y, 0.0))), 0.0), 4.0);
  const hor = mix(G.skyHor, G.skySun, toSun);
  const sky = mix(hor, G.skyZen, smoothstep(0.08, 0.7, R.z));
  // the banks: trees, walls and houses mirrored a little darker than they are, in masses round the horizon (the season's
  // foliage, or the snow on them)
  const ang = atan(R.y, R.x);
  const masses = mx_noise_float(vec3(ang.mul(7.0), wp.x.mul(0.013), wp.y.mul(0.013))).mul(0.5).add(0.5);
  const bankC = mix(vec3(0.42, 0.24, 0.13), vec3(0.62, 0.64, 0.68), G.season);
  const surround = irr.mul(0.045).mul(bankC).mul(masses.mul(0.9).add(0.35)).add(vec3(0.004, 0.004, 0.0035));
  const edge = select(still, float(0.3), mix(mix(float(0.42), float(0.16), open), float(0.2), flowing));   // how high the reflected banks reach (R.z)
  const refl = mix(surround, sky, smoothstep(edge.mul(0.45), edge, R.z.add(masses.sub(0.5).mul(0.08))));
  const bed = mix(vec3(0.016, 0.022, 0.019), vec3(0.075, 0.08, 0.065), select(still, float(0.0), open.mul(0.6))).mul(irr).div(Math.PI);
  mat.emissiveNode = refl.mul(fres).add(bed.mul(float(1.0).sub(fres)));
  return mat;
}
const transformDir = (n) => cameraViewMatrix.mul(vec4(n, 0.0)).xyz.normalize();

// ---------------------------------------------------------------------------------------------------------------
// far LOD: unlit program; sky + bounce from the bake, the sun from the bake's visibility, flat normals
export function makeLiteMaterial({ mats }) {
  const AL = mats.map((m) => new THREE.Vector4(...m.albedo, KIND[m.kind] ?? 8));
  const al = uniformArray(AL, 'vec4').setGroup(renderGroup);
  const c0 = attribute('c0', 'vec4'), c1 = attribute('c1', 'vec4'), irrA = attribute('irr', 'vec4');
  const mid = c1.x.mul(255.0).add(0.5).toInt();
  const a = al.element(mid);
  const k = a.w;
  const wp = positionWorld;
  const cr = cross(wp.dFdx(), wp.dFdy()), crl = length(cr);
  let nW = select(crl.greaterThan(1e-12), cr.div(crl), vec3(0.0, 0.0, 1.0));
  nW = select(dot(nW, cameraPosition.sub(wp)).lessThan(0.0), nW.negate(), nW);
  const tinted = abs(k.sub(KIND.wall)).lessThan(0.5).or(abs(k.sub(KIND.machiya)).lessThan(0.5)).or(abs(k.sub(KIND.roofmetal)).lessThan(0.5)).or(abs(k.sub(KIND.ground)).lessThan(0.5));
  let col = select(tinted, s2l(c0.rgb).mul(select(abs(k.sub(KIND.ground)).lessThan(0.5), float(1.0), float(0.8))), a.rgb);
  col = col.mul(float(0.9).add(mx_noise_float(wp.mul(0.13)).mul(0.1)));
  // forest ground beyond the tree impostors: the canopy seen from afar (stands of oak yellow-brown, maple red,
  // evergreens dark green; bare grey-brown twigs under snow in winter), as on the distant hills (far.js)
  const sidL = c1.w.mul(255.0).add(0.5).floor();
  const isForest = abs(k.sub(KIND.ground)).lessThan(0.5).and(abs(sidL.sub(SURF.indexOf('forest'))).lessThan(0.5));
  const mott = mx_noise_float(vec3(wp.xy.mul(0.018), 3.1)), crown = mx_noise_float(vec3(wp.xy.mul(0.22), 7.7)).mul(0.5).add(0.5);
  const hp = clamp(float(0.5).add(mott.mul(0.9)), 0.0, 1.0);
  const decC = mix(mix(vec3(0.30, 0.06, 0.025), vec3(0.22, 0.14, 0.05), smoothstep(0.18, 0.32, hp)), vec3(0.32, 0.24, 0.05), smoothstep(0.72, 0.86, hp));
  const everg = smoothstep(0.2, 0.5, mx_noise_float(vec3(wp.xy.mul(0.011), 1.3)).mul(0.5).add(0.5));
  const canA = mix(decC, vec3(0.035, 0.06, 0.025), everg.mul(0.75));
  const canW = mix(vec3(0.085, 0.07, 0.06), vec3(0.03, 0.05, 0.025), everg.mul(0.8));
  const canopy = mix(canA, canW, G.season).mul(float(0.6).add(crown.mul(0.7)));
  col = select(isForest, canopy, col);
  const snow = smoothstep(0.45, 0.8, nW.z).mul(G.season).mul(select(abs(k.sub(KIND.ground)).lessThan(0.5).and(c1.y.greaterThan(0.5 / 255)), float(0.5), float(1.0)))
    .mul(select(isForest, float(0.45).mul(crown), float(1.0)));
  col = mix(col, vec3(0.8, 0.82, 0.86), snow);
  const irr = decIrr(irrA).mul(G.irrGain).mul(G.irrScale);
  const sun = G.sunCol.mul(max(dot(nW, G.sunDir), 0.0)).mul(irrA.a);
  const mat = new THREE.MeshBasicNodeMaterial();
  // water far away: the river bed through shallow water, the sky mirrored at a glancing view
  const isWater = abs(k.sub(KIND.water)).lessThan(0.5);
  const V = normalize(wp.sub(cameraPosition));
  const fres = float(0.02).add(float(0.98).mul(pow(float(1.0).sub(clamp(V.z.negate(), 0.0, 1.0)), 5.0)));
  const skyR = mix(G.skyHor, G.skyZen, smoothstep(0.05, 0.6, V.z.negate()));
  const waterC = vec3(0.10, 0.11, 0.09).mul(irr.add(sun)).div(Math.PI).add(skyR.mul(fres).mul(0.8));
  mat.colorNode = select(isWater, mix(waterC, vec3(0.8, 0.82, 0.86).mul(irr).div(Math.PI), G.season.mul(0.0)), col.mul(irr.add(sun)).div(Math.PI));
  return mat;
}
