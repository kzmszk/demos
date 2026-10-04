// City "uber" material (TSL): texture-array PBR layers + Venetian weathering (peeling plaster, rising damp,
// salt, algae at the tide line, Istrian-stone base courses, lichen on roofs, louvred shutters), baked
// irradiance as indirect diffuse (per vertex or from a facade lightmap atlas), sky reflections occluded by
// the bake, live sun with cascaded shadows.
import * as THREE from 'three/webgpu';
import {
  Fn, attribute, texture, uniform, uniformArray, vec2, vec3, vec4, float, int, mix, clamp, smoothstep, max, min, pow, dot, normalize, cross,
  positionWorld, positionViewDirection, normalView, tangentView, bitangentView, normalGeometry, uv, select, abs, sin, fract, floor, step,
  mx_noise_float, mx_fractal_noise_float, cameraWorldMatrix, renderGroup, pmremTexture, roughness as roughnessProp, materialEnvIntensity, transformNormalToView, vertexColor,
  cameraPosition, cameraViewMatrix,
} from 'three/tsl';

export const G = {
  night: uniform(0.0).setGroup(renderGroup),           // 0 day .. 1 night
  irrGain: uniform(Math.PI).setGroup(renderGroup),     // Cycles diffuse bake -> irradiance
  time: uniform(0.0).setGroup(renderGroup),
  winGlow: uniform(0.0).setGroup(renderGroup),         // lit windows at night
  lamp: uniform(6.0).setGroup(renderGroup),            // emission of lamp glass (matches the bake's emission strength)
  nightAmb: uniform(new THREE.Vector3(0.008, 0.0072, 0.0066)).setGroup(renderGroup),   // night: the glow of a lit city in the haze (lifts moonlit blacks)
  dbg: uniform(0).setGroup(renderGroup),               // 0 shaded, 1 albedo, 2 baked irradiance, 3 normal
};

const KIND = { wall: 0, ground: 1, roof: 2, stone: 3, wood: 4, metal: 5, glass: 6, water: 7, plain: 8, gold: 9, marble: 10, lozenge: 11, photo: 12, interior: 13, emissive: 14, mirror: 15, mosaic: 16, floor: 17 };

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
    const radiance = env.context(ctx).mul(materialEnvIntensity).mul(this.occNode);
    builder.context.radiance.addAssign(radiance);
  }
}

export class CityMaterial extends THREE.MeshPhysicalNodeMaterial {
  static get type() { return 'CityMaterial'; }
  constructor(opts) { super(); this.irrNode = opts.irrNode; this.occNode = opts.occNode; }
  setupLightMap() { return new THREE.IrradianceNode(this.irrNode); }
  setupEnvironment(builder) {
    const e = this.envNode || builder.environmentNode;
    return e ? new SpecEnvNode(e, this.occNode) : null;
  }
}

const rgbm = (c) => c.rgb.mul(c.a).mul(8.0);
const lum = (c) => dot(c, vec3(0.2126, 0.7152, 0.0722));
const s2l = (c) => pow(c, vec3(2.2));

export function makeCityMaterial({ arrays, mats, layers, lighting, lmPool, hasAux = false, hasNight = false, art = null }) {
  // per-material parameters
  const P1 = [], P2 = [], AL = [], P3 = [];
  for (const m of mats) {
    const L = m.layer >= 0 ? layers[m.layer] : null;
    const kind = KIND[m.kind] ?? 8;
    P3.push(new THREE.Vector4(...(m.emit || [0, 0]), 0, 0));
    P1.push(new THREE.Vector4(Math.max(0, m.layer), L ? 1 / L.size : 1, (m.name === 'wall_plaster' || m.name === 'wood_paint') ? 1 : 0, kind));
    const rough = { glass: 0.06, metal: 0.55, wood: 0.85, stone: 0.9, ground: 1.0, roof: 1.0, wall: 1.0, plain: 0.9 }[m.kind] ?? 1;
    P2.push(new THREE.Vector4(rough, m.kind === 'metal' ? 0.4 : 0, m.layer >= 0 ? 1 : 0, 0));
    if (m.kind === 'marble' || m.kind === 'gold') P2[P2.length - 1].z = m.layer >= 0 ? 1 : 0;
    AL.push(new THREE.Vector4(...m.albedo.map((v) => Math.pow(v, 1 / 1.0)), 1));
  }
  // material tables: the same for every draw -> render group (three.js puts uniforms in the per-object group by default,
  // which re-uploaded these ~1 KB arrays for each of ~170 draws x 6 passes every frame)
  const p1 = uniformArray(P1, 'vec4').setGroup(renderGroup), p2 = uniformArray(P2, 'vec4').setGroup(renderGroup), alU = uniformArray(AL, 'vec4').setGroup(renderGroup), p3 = uniformArray(P3, 'vec4').setGroup(renderGroup);
  const LY = Object.fromEntries(layers.map((l, i) => [l.name, i]));

  const c0 = attribute('c0', 'vec4'), c1 = attribute('c1', 'vec4');
  const mid = c1.x.mul(255.0).add(0.5).toInt();
  const q1 = p1.element(mid), q2 = p2.element(mid);
  const layer = q1.x.toInt(), kind = q1.w;
  const st = uv().mul(q1.y);
  const wp = positionWorld;

  const sampleA = (lay, coord) => texture(arrays.albedo, coord).depth(lay);
  const sampleN = (lay, coord) => texture(arrays.normal, coord).depth(lay);
  const sampleO = (lay, coord) => texture(arrays.orm, coord).depth(lay);

  // ---------------------------------------------------------------- surface (pure expressions)
  const surf = () => {
    const A = sampleA(layer, st), O = sampleO(layer, st);
    let Nt = sampleN(layer, st).xyz.mul(2).sub(1);
    const hasTex = q2.z;
    let col = mix(alU.element(mid).rgb, A.rgb, hasTex);
    const tint0 = s2l(c0.rgb);
    const tint = mix(tint0, vec3(lum(tint0)), 0.22);
    col = mix(col, col.mul(tint).mul(1.12), A.a.mul(q1.z));
    let rough = O.g.mul(q2.x);
    const metal = q2.y;
    let ao = mix(float(1.0), O.r, hasTex);
    const z = wp.z;
    const n1 = mx_fractal_noise_float(wp.mul(vec3(0.35, 0.35, 0.55)), int(3), float(2.0), float(0.5));
    const n2 = mx_noise_float(wp.mul(vec3(1.7, 1.7, 2.3)));
    // ---------- walls
    const isWall = kind.lessThan(0.5);
    const decay = c0.a;
    const baseZ = hasAux ? attribute('aux', 'vec2').x : float(-100.0);
    const inBase = isWall.and(z.lessThan(baseZ));
    const stoneUV = uv().mul(1.0 / 2.0);
    const SA = sampleA(int(LY.stone_rough), stoneUV), SN = sampleN(int(LY.stone_rough), stoneUV), SO = sampleO(int(LY.stone_rough), stoneUV);
    col = select(inBase, mix(SA.rgb, vec3(lum(SA.rgb)), 0.55).mul(1.08), col);
    Nt = select(inBase, SN.xyz.mul(2).sub(1), Nt);
    rough = select(inBase, SO.g, rough);
    // peeling plaster: brick shows through irregular patches ringed by the grey render coat; more of it low
    // on the wall and on decayed buildings
    const isPl = isWall.and(q1.z.greaterThan(0.5)).and(inBase.not());
    const zg = z.sub(1.1);
    const pf = n1.mul(0.75).add(n2.mul(0.25)).mul(0.5).add(0.5).add(float(1.0).sub(smoothstep(0.2, 3.5, zg)).mul(decay).mul(0.45)).sub(smoothstep(4.0, 12.0, zg).mul(0.12)).add(c1.z.mul(0.08));
    const pt = float(1.05).sub(decay.mul(0.5));
    const inner = smoothstep(pt.add(0.045), pt.add(0.065), pf).mul(isPl.select(1.0, 0.0));
    const ring = smoothstep(pt, pt.add(0.02), pf).mul(isPl.select(1.0, 0.0)).sub(inner).max(0.0);
    const edge = smoothstep(pt.sub(0.025), pt, pf).sub(smoothstep(pt, pt.add(0.005), pf)).max(0.0).mul(isPl.select(1.0, 0.0));
    const buv = uv().mul(1 / 1.5);
    const BA = sampleA(int(LY.brick_old), buv), BN = sampleN(int(LY.brick_old), buv), BO = sampleO(int(LY.brick_old), buv);
    const puv = uv().mul(1 / 2.0);
    const PN = sampleN(int(LY.plaster_peel), puv);
    const render = vec3(0.30, 0.285, 0.26).mul(float(0.85).add(n2.mul(0.2)));
    col = mix(col, render, ring);
    col = mix(col, BA.rgb.mul(0.92), inner);
    col = col.mul(float(1.0).sub(edge.mul(0.35)));
    Nt = mix(Nt, PN.xyz.mul(2).sub(1), ring);
    Nt = mix(Nt, BN.xyz.mul(2).sub(1), inner);
    rough = mix(rough, BO.g, inner);
    // tonal variation, vertical rain streaks, soot under the eaves, splash dirt at the foot
    const streak = mx_noise_float(vec3(uv().x.mul(1.6), z.mul(0.07), c1.z.mul(37.0))).mul(0.5).add(0.5);
    const streak2 = mx_noise_float(vec3(uv().x.mul(6.0), z.mul(0.25), c1.z.mul(11.0))).mul(0.5).add(0.5);
    const grime = streak.mul(0.6).add(streak2.mul(0.4)).mul(smoothstep(2.0, 10.0, zg)).mul(0.22);
    col = select(isWall, col.mul(float(0.9).add(n1.mul(0.12))).mul(float(1.0).sub(grime)).mul(float(1.0).sub(smoothstep(0.9, 0.0, zg).mul(0.18))), col);
    // rising damp + salt efflorescence + algae at the tide line (walls and canal walls)
    const wetK = isWall.or(kind.greaterThan(2.5).and(kind.lessThan(3.5)));
    const wetF = wetK.select(1.0, 0.0);
    const dampTop = float(1.1).add(float(0.75).add(n1.mul(0.55)).add(streak2.mul(0.35)).mul(float(0.6).add(decay)));
    const damp = smoothstep(dampTop, dampTop.sub(0.35), z).mul(wetF);
    const salt = smoothstep(0.10, 0.0, abs(z.sub(dampTop.sub(0.04)))).mul(smoothstep(0.2, 0.7, n2.add(0.2))).mul(wetF);
    col = mix(col, col.mul(vec3(0.58, 0.57, 0.52)), damp.mul(0.85));
    col = mix(col, vec3(0.52, 0.51, 0.48), salt.mul(0.4));
    rough = mix(rough, rough.mul(0.85), damp);
    // tide line: algae below ~0.4 m, a pale salt band above it up to ~1.1 m on walls in the water
    const tide = float(0.40).add(n2.mul(0.10));
    const algae = smoothstep(tide, tide.sub(0.10), z).mul(wetF);
    const tideBand = smoothstep(tide, tide.add(0.1), z).mul(smoothstep(1.15, 0.8, z)).mul(wetF);
    col = mix(col, col.mul(vec3(0.8, 0.82, 0.78)).add(vec3(0.03)), tideBand.mul(0.6));
    const auv = vec2(uv().x, z).mul(1 / 2.2);
    const AA = sampleA(int(LY.algae), auv);
    const acol = mix(AA.rgb.mul(vec3(0.42, 0.5, 0.33)), vec3(0.03, 0.036, 0.024), smoothstep(0.1, -0.35, z));
    col = mix(col, acol, algae);
    rough = mix(rough, float(0.28), algae.mul(smoothstep(0.3, 0.0, z)));
    // ---------- roofs: lichen and soot
    const isRoof = kind.greaterThan(1.5).and(kind.lessThan(2.5));
    const lich = smoothstep(0.25, 0.55, n1.add(n2.mul(0.3)));
    col = select(isRoof, mix(col.mul(float(0.85).add(n2.mul(0.15))), vec3(0.16, 0.15, 0.11), lich.mul(0.45)), col);
    // ---------- ground: big-scale dirt/wear variation
    const isGround = kind.greaterThan(0.5).and(kind.lessThan(1.5));
    const stain = smoothstep(0.2, 0.6, mx_noise_float(wp.mul(vec3(0.12, 0.12, 1.0))));
    const grime2 = smoothstep(-0.2, 0.8, mx_noise_float(wp.mul(vec3(0.45, 0.45, 1.0))));
    col = select(isGround, col.mul(float(0.72).add(n1.mul(0.24))).mul(float(1.0).sub(stain.mul(0.22))).mul(float(1.0).sub(grime2.mul(0.18))), col);
    // ---------- Istrian stone: whiten and add black crust where sheltered
    const isStone = kind.greaterThan(2.5).and(kind.lessThan(3.5));
    const scol = mix(col, vec3(lum(col)), 0.6).mul(1.18);
    col = select(isStone, mix(scol, scol.mul(0.45), smoothstep(0.35, 0.7, n2).mul(0.35)), col);
    // ---------- wood: louvred shutters (flag 1) via normal tweaks; flower boxes etc. flat colour
    const isWood = kind.greaterThan(3.5).and(kind.lessThan(4.5));
    const fl = c1.w.mul(255.0).add(0.5).floor();
    const slat = fract(z.div(0.065));
    const louv = isWood.and(fl.equal(1.0));
    Nt = select(louv, normalize(vec3(0.0, slat.sub(0.5).mul(1.6), 1.0)), Nt);
    ao = select(louv, ao.mul(smoothstep(0.0, 0.25, slat).mul(0.5).add(0.5)), ao);
    rough = select(isWood, max(rough, float(0.62)), rough);
    // flat-painted props: flower boxes/leaves/flowers (3-5), boat paint (8), canvas (10), lacquer (11)
    const plain = isWood.and(fl.greaterThan(2.5).and(fl.lessThan(5.5)).or(fl.equal(8.0)).or(fl.equal(10.0)).or(fl.equal(11.0)));
    const fine = mx_noise_float(wp.mul(9.0)).mul(0.06);
    col = select(plain, tint.mul(float(0.85).add(n2.mul(0.15)).add(fine)), col);
    rough = select(isWood.and(fl.equal(8.0)), float(0.42), rough);
    rough = select(isWood.and(fl.equal(10.0)), float(0.95), rough);
    rough = select(isWood.and(fl.equal(11.0)), float(0.16), rough);
    // spiral-striped mooring poles (6): instance colour over white paint
    if (lighting === 'inst') {
      const ic = s2l(attribute('icol', 'vec4').rgb);
      const stripe = step(0.5, fract(uv().x.div(0.69).add(uv().y.div(0.55))));
      const isStripe = isWood.and(fl.equal(6.0));
      col = select(isStripe, mix(vec3(0.62, 0.6, 0.56), ic, stripe).mul(float(0.85).add(n2.mul(0.15))), col);
      rough = select(isStripe, float(0.5), rough);
    }
    // ---------- glass: dark; metal: dark painted iron
    const isGlass = kind.greaterThan(5.5).and(kind.lessThan(6.5));
    col = select(isGlass, vec3(0.012, 0.014, 0.016), col);
    rough = select(isGlass, float(0.05), rough);
    const isMetal = kind.greaterThan(4.5).and(kind.lessThan(5.5));
    col = select(isMetal, vec3(0.035, 0.036, 0.034).add(col.mul(0.15)), col);
    let metal2 = metal;
    const gilt = isMetal.and(fl.equal(7.0)), steel = isMetal.and(fl.equal(12.0));
    col = select(gilt, vec3(0.95, 0.70, 0.32), select(steel, vec3(0.62, 0.62, 0.64), col));
    metal2 = select(gilt.or(steel), float(1.0), metal2);
    rough = select(gilt, float(0.3), select(steel, float(0.22), rough));
    // gilding and polished marbles (hero materials): albedo param tints the vein pattern of the stone layer
    const isGold = kind.greaterThan(8.5).and(kind.lessThan(9.5));
    const pat = smoothstep(0.1, 0.7, n2);                   // dark patina blotches on old gilding
    col = select(isGold, mix(alU.element(mid).rgb.mul(1.15).min(vec3(1.0)), vec3(0.13, 0.11, 0.06), pat.mul(0.55)), col);
    metal2 = select(isGold, float(1.0), metal2);
    rough = select(isGold, mix(float(0.32), float(0.6), pat), rough);
    const isMarble = kind.greaterThan(9.5).and(kind.lessThan(10.5));
    const veins = lum(A.rgb).div(0.36);
    col = select(isMarble, alU.element(mid).rgb.mul(veins.mul(0.6).add(0.45)).mul(float(0.92).add(n2.mul(0.08))), col);
    rough = select(isMarble, float(0.38), rough);
    // Palazzo Ducale: pink Verona marble lozenges in a lattice of white Istrian stone (small blocks = stone layer)
    const isLoz = kind.greaterThan(10.5).and(kind.lessThan(11.5));
    const lq = uv().div(vec2(1.3, 1.3));
    const dd = abs(fract(lq.x).sub(0.5)).add(abs(fract(lq.y.add(0.5)).sub(0.5)));
    const line = float(1.0).sub(smoothstep(0.025, 0.06, abs(dd.sub(0.5))));
    const blocks = lum(A.rgb).div(0.36).mul(0.25).add(0.75);
    const pink = vec3(0.70, 0.37, 0.30).mul(float(0.9).add(n2.mul(0.1))), white = vec3(0.74, 0.72, 0.67);
    col = select(isLoz, mix(pink, white, line).mul(blocks), col);
    rough = select(isLoz, float(0.7), rough);
    // interiors: albedo modulated by the texture's luminance, no weathering
    const isInt = kind.greaterThan(12.5).and(kind.lessThan(13.5));
    const alb0 = alU.element(mid).rgb;
    col = select(isInt, mix(alb0.mul(float(0.92).add(n2.mul(0.08))), alb0.mul(lum(A.rgb).div(0.32)), hasTex), col);
    rough = select(isInt, select(hasTex, O.g.mul(0.75), float(0.92)), rough);
    // paintings / mosaics (art array layer in c1.y), lamp glass, mirrors
    const isPhoto = kind.greaterThan(11.5).and(kind.lessThan(12.5));
    if (art) {
      const lay = c1.y.mul(255.0).add(0.5).toInt();
      col = select(isPhoto, texture(art, uv()).depth(lay).rgb, col);
    }
    rough = select(isPhoto, float(0.3), rough);
    const isEm = kind.greaterThan(13.5).and(kind.lessThan(14.5));
    col = select(isEm, alb0.mul(0.6), col);
    // gold mosaic: warm gold with tesserae (cells ~2.5 cm) that vary in tone and catch the light
    const isMos = kind.greaterThan(15.5).and(kind.lessThan(16.5));
    const wpm = wp.mul(12.0);
    const cell = floor(wpm.x.add(wpm.y.mul(0.37))).add(floor(wpm.z).mul(57.0)).add(floor(wpm.y).mul(13.0));
    const tess = fract(sin(cell.mul(12.9898)).mul(43758.5453));
    const blot = mx_noise_float(wp.mul(0.35)).mul(0.5).add(0.5);
    col = select(isMos, alb0.mul(float(0.88).add(tess.mul(0.24))).mul(float(0.9).add(blot.mul(0.2))), col);
    rough = select(isMos, float(0.35), rough);
    // opus sectile floor: 1.6 m panels with a white border, a red diamond and a green roundel, small checks
    const isFl = kind.greaterThan(16.5).and(kind.lessThan(17.5));
    const fq = wp.xy.div(1.6); const fc = fract(fq).sub(0.5); const fid = floor(fq);
    const fh = fract(sin(fid.x.mul(91.3).add(fid.y.mul(47.1))).mul(43758.5453));
    const dia = abs(fc.x).add(abs(fc.y));
    const rad = fc.length();
    const border = max(abs(fc.x), abs(fc.y)).greaterThan(0.44);
    const chk = fract(wp.x.mul(3.2)).lessThan(0.5).equal(fract(wp.y.mul(3.2)).lessThan(0.5));
    const fWhite = vec3(0.62, 0.6, 0.55), fRed = vec3(0.30, 0.06, 0.05), fGreen = vec3(0.07, 0.17, 0.11), fGrey = vec3(0.16, 0.16, 0.17), fOchre = vec3(0.55, 0.4, 0.18);
    const fcol = select(border, select(chk, fWhite, fGrey), select(dia.lessThan(0.38), select(rad.lessThan(0.17), select(fh.lessThan(0.5), fGreen, fOchre), fRed), select(chk, fWhite, vec3(0.42, 0.38, 0.33))));
    col = select(isFl, fcol.mul(float(0.8).add(lum(A.rgb).div(0.39).mul(0.2))), col);
    rough = select(isFl, float(0.3), rough);
    // old mirrors: the sky map is no picture of a café room, so they show a dull warm blur of the room's light
    const isMir = kind.greaterThan(14.5).and(kind.lessThan(15.5));
    col = select(isMir, vec3(0.34, 0.30, 0.24).mul(float(0.94).add(n2.mul(0.06))), col);
    metal2 = select(isMir, float(0.0), metal2);
    rough = select(isMir, float(0.4), rough);
    Nt = select(isPhoto.or(isEm).or(isMir).or(isMos).or(isLoz.not().and(isInt.and(hasTex.lessThan(0.5)))), vec3(0.0, 0.0, 1.0), Nt);
    const e3 = p3.element(mid);
    // night: lit windows (glass with the 'lit' flag) and lantern glass (flag 9) glow warm
    const flw = c1.w.mul(255.0).add(0.5).floor();
    const winLit = isGlass.and(flw.greaterThan(127.5));
    const lantern = isGlass.and(flw.equal(9.0));
    const wv = fract(sin(c1.z.mul(97.3).add(floor(uv().x.mul(0.7)).mul(13.1)).add(floor(wp.z.mul(0.3)).mul(7.7))).mul(43758.5453));
    const nightEm = select(winLit, vec3(1.0, 0.66, 0.36).mul(float(1.2).add(wv.mul(2.2))), select(lantern, vec3(1.0, 0.74, 0.44).mul(14.0), vec3(0.0)));
    return { col, Nt, rough, metal: metal2, ao, raw: A.rgb, emit: select(isEm, alb0.mul(mix(e3.x, e3.y, G.night)).mul(0.1), vec3(0.0)).add(nightEm.mul(G.night)) };
  };

  const S = surf();
  const lmc = attribute('lm', 'vec3');
  const irrDay = lighting === 'atlas' ? rgbm(texture(lmPool.day, lmc.xy).depth(lmc.z.add(0.5).toInt())) : lighting === 'inst' ? rgbm(attribute('iirr', 'vec4')) : rgbm(attribute('irr', 'vec4'));
  const irrNight = lighting === 'atlas' ? rgbm(texture(lmPool.night, lmc.xy).depth(lmc.z.add(0.5).toInt())) : lighting === 'inst' ? rgbm(attribute('iirrn', 'vec4')) : hasNight ? rgbm(attribute('irrn', 'vec4')) : irrDay.mul(0.0);
  const aoGeo = hasAux ? attribute('aux', 'vec2').y : float(1.0);
  const irr = mix(irrDay, irrNight.add(G.nightAmb), G.night).mul(G.irrGain).mul(aoGeo).mul(S.ao);
  // sky reflections are occluded by the bake; interiors (paintings, mirrors, gilt, velvet) reflect a dim warm room instead
  const kindI = p1.element(c1.x.mul(255.0).add(0.5).toInt()).w;
  const occ = clamp(lum(irrDay).div(0.32), 0.03, 1.0).pow(0.8).mul(aoGeo).mul(select(kindI.greaterThan(11.5).and(kindI.lessThan(17.5)), float(0.12), float(1.0)));

  const mat = new CityMaterial({ irrNode: irr, occNode: occ.mul(mix(float(1), float(0.15), G.night)) });
  mat.colorNode = S.col;
  // debug views: replace the lit result through emissive and black diffuse
  const dbgOn = G.dbg.greaterThan(0.5);
  mat.emissiveNode = select(dbgOn, select(G.dbg.lessThan(1.5), S.col, select(G.dbg.lessThan(2.5), irr.mul(0.25), select(G.dbg.lessThan(3.5), S.Nt.mul(0.5).add(0.5), S.raw))), S.emit);
  mat.colorNode = select(dbgOn, vec3(0.0), S.col);
  // tangent-space normal -> view space
  const tN = S.Nt;
  mat.normalNode = normalize(tangentView.mul(tN.x).add(bitangentView.mul(tN.y)).add(normalView.mul(tN.z)));
  mat.roughnessNode = clamp(S.rough, 0.04, 1.0);
  const specK = select(kind.lessThan(0.5), float(0.45), select(kind.lessThan(1.5), float(0.35), select(kind.lessThan(2.5), float(0.4), select(kind.lessThan(3.5), float(0.55), float(1.0)))));
  mat.specularIntensityNode = select(G.dbg.greaterThan(0.5), float(0.0), specK);
  mat.metalnessNode = S.metal;
  // lit windows at night
  const lit = c1.w.mul(255.0).add(0.5).floor().greaterThan(127.5);
  return mat;
}

// ---------------------------------------------------------------------------------------------------------
// Far LOD ("lite") material: vertex-lit, flat normals from screen derivatives, texture coordinates from world
// position (walls: along the wall / height; roofs and ground: plan), procedural window grid on facade strips.
export function makeLiteMaterial({ arrays, mats, layers, facade = false }) {
  const P1 = [], AL = [];
  for (const m of mats) {
    const L = m.layer >= 0 ? layers[m.layer] : null;
    P1.push(new THREE.Vector4(Math.max(0, m.layer), L ? 1 / L.size : 1, (m.name === 'wall_plaster' || m.name === 'wood_paint') ? 1 : 0, KIND[m.kind] ?? 8));
    AL.push(new THREE.Vector4(...m.albedo, m.layer >= 0 ? 1 : 0));
  }
  const p1 = uniformArray(P1, 'vec4').setGroup(renderGroup), alU = uniformArray(AL, 'vec4').setGroup(renderGroup);
  const c0 = attribute('c0', 'vec4'), c1 = attribute('c1', 'vec4');
  const mid = c1.x.mul(255.0).add(0.5).toInt();
  const q1 = p1.element(mid), al = alU.element(mid);
  const kind = q1.w;
  const wp = positionWorld;
  let nW = normalize(cross(wp.dFdx(), wp.dFdy()));
  nW = select(dot(nW, cameraPosition.sub(wp)).lessThan(0.0), nW.negate(), nW);
  const horiz = abs(nW.z).greaterThan(0.6);
  const tdir = normalize(vec2(nW.y.negate(), nW.x).add(vec2(1e-5, 0.0)));
  const uvA = facade ? attribute('uv', 'vec2') : null;
  const UV = facade ? uvA : select(horiz, wp.xy, vec2(dot(wp.xy, tdir), wp.z));
  const st = UV.mul(q1.y);
  const A = texture(arrays.albedo, st).depth(q1.x.toInt());
  let col = mix(al.rgb, A.rgb, al.w);
  const tint0 = s2l(c0.rgb);
  col = mix(col, col.mul(mix(tint0, vec3(lum(tint0)), 0.22)).mul(1.12), A.a.mul(q1.z));
  const n2 = mx_noise_float(wp.mul(0.11));
  let rough = float(0.92);
  // stone whitening, marble / metal / gold kinds as in the city material
  const isStone = kind.greaterThan(2.5).and(kind.lessThan(3.5));
  col = select(isStone, mix(col, vec3(lum(col)), 0.6).mul(1.18), col);
  const isMarble = kind.greaterThan(9.5).and(kind.lessThan(10.5));
  col = select(isMarble, al.rgb.mul(lum(A.rgb).div(0.36).mul(0.6).add(0.45)), col);
  const isGold = kind.greaterThan(8.5).and(kind.lessThan(9.5));
  col = select(isGold, vec3(0.95, 0.70, 0.32), col);
  const isGround = kind.greaterThan(0.5).and(kind.lessThan(1.5));
  col = select(isGround, col.mul(0.78), col);
  col = col.mul(float(0.92).add(n2.mul(0.08)));
  let metal = select(isGold, float(1.0), float(0.0));
  rough = select(isGold, float(0.3), select(isMarble, float(0.4), rough));
  if (facade) {
    // regular window grid from the facade's upper-floor openings: w0 = (u first, pitch, columns, width), w1 = (z first sill, floor height, rows, height)
    const w0 = attribute('w0', 'vec4'), w1 = attribute('w1', 'vec4');
    const u = uvA.x, z = uvA.y;
    const ci = floor(u.sub(w0.x).div(w0.y).add(0.5));
    const du = u.sub(w0.x.add(ci.mul(w0.y)));
    const ri = floor(z.sub(w1.x).div(w1.y));
    const dz = z.sub(w1.x.add(ri.mul(w1.y)));
    const inC = ci.greaterThanEqual(0.0).and(ci.lessThan(w0.z));
    const inR = ri.greaterThanEqual(0.0).and(ri.lessThan(w1.z));
    const win = inC.and(inR).and(abs(du).lessThan(w0.w.mul(0.5))).and(dz.greaterThan(0.0)).and(dz.lessThan(w1.w));
    const frame = inC.and(inR).and(abs(du).lessThan(w0.w.mul(0.5).add(0.13))).and(dz.greaterThan(-0.12)).and(dz.lessThan(w1.w.add(0.1))).and(win.not());
    const hsh = fract(sin(ci.mul(12.9898).add(ri.mul(78.233)).add(c1.z.mul(311.7))).mul(43758.5453));
    const shut = hsh.lessThan(0.38);
    const glass = vec3(0.012, 0.014, 0.017);
    const shutCol = vec3(0.09, 0.15, 0.11).mul(float(0.8).add(hsh.mul(0.5)));
    col = select(frame, vec3(0.55, 0.53, 0.49), col);
    col = select(win, select(shut, shutCol, glass), col);
    rough = select(win.and(shut.not()), float(0.08), rough);
  }
  const irrD = rgbm(attribute('irr', 'vec4')), irrN = rgbm(attribute('irrn', 'vec4'));
  const irr = mix(irrD, irrN.add(G.nightAmb), G.night).mul(G.irrGain);
  const occ = clamp(lum(irrD).div(0.32), 0.03, 1.0).pow(0.8);
  const mat = new CityMaterial({ irrNode: irr, occNode: occ.mul(mix(float(1), float(0.15), G.night)) });
  mat.colorNode = col;
  mat.normalNode = cameraViewMatrix.mul(vec4(nW, 0.0)).xyz.normalize();
  mat.roughnessNode = rough;
  mat.metalnessNode = metal;
  mat.specularIntensityNode = select(kind.lessThan(2.5), float(0.4), float(0.8));
  return mat;
}
