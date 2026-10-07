// KYOTO far field: the terrain out to +/-60 km, draped with the land-cover class raster (+/-24 km around the tile area), shaded per class
// with the viewer's season (G.season: 0 autumn, 1 winter) and light (G.sunDir, G.sunCol, G.irrGain, G.irrScale).
//
// Data (public/data/far, built by kyoto-assets/tools/far_build.py, see FAR_README.md):
//   far.json       extent of the raster, mesh/ground tables
//   far.bin        gzip of meshopt streams: pos (uint16x4 normalised), attr (uint8x4), idx (uint32), hgt_in / hgt_out (uint16 ground heights)
//   far_class.png  RGB, 4096 x 4096 over the extent; row 0 = NORTH edge, column 0 = WEST edge.
//                  R = class id, G = per-object variation (0..255, coarse levels), B = building height in metres (2 m steps)
//
// Orientation: the texture is loaded with flipY = false (row 0 of the image = v 0), so  u = (x - x0) / W,  v = (y1 - y) / W.
// Units: metres in the local frame (x east, y north, z up = height above T.P.).
import * as THREE from 'three/webgpu';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import {
  attribute, texture, uniformArray, vec2, vec3, vec4, float, mix, clamp, smoothstep, max, min, pow, dot, normalize, cross, length, abs, step, sqrt,
  positionWorld, cameraPosition, mx_noise_float, renderGroup,
} from 'three/tsl';
import { fetchBin, toGPU } from './tiles.js';

export const FAR_CLASSES = ['ground', 'roof_kawara', 'roof_flat', 'roof_metal', 'road', 'forest_evergreen', 'forest_deciduous', 'water', 'grass', 'farmland', 'railway', 'bare'];

// ---- palette: [r, g, b, a] per class.  AUTUMN: a = how much the per-object variation (G) modulates the albedo.  WINTER: a = snow cover (0 roads / water, 1 roofs / open ground)
const AUTUMN = [
  [0.18, 0.16, 0.14, 0.25],   // 0 open ground / urban unbuilt
  [0.11, 0.11, 0.115, 0.35],  // 1 kawara roof
  [0.35, 0.35, 0.34, 0.30],   // 2 flat / light roof
  [0.16, 0.19, 0.24, 0.30],   // 3 coloured metal roof (blue; brown for half of them, see tap())
  [0.08, 0.08, 0.08, 0.0],    // 4 road
  [0.04, 0.08, 0.03, 0.0],    // 5 evergreen forest (crown noise)
  [0.45, 0.10, 0.03, 0.0],    // 6 deciduous forest (red / orange / yellow in tap())
  [0.02, 0.03, 0.035, 0.0],   // 7 water
  [0.10, 0.14, 0.05, 0.25],   // 8 grass / park (yellowing in tap())
  [0.16, 0.12, 0.08, 0.40],   // 9 farmland / paddy
  [0.10, 0.09, 0.09, 0.0],    // 10 railway
  [0.32, 0.28, 0.22, 0.25],   // 11 bare / rock / sand
];
const WINTER = [
  [0.18, 0.16, 0.14, 1.0],
  [0.11, 0.11, 0.115, 1.0],
  [0.35, 0.35, 0.34, 1.0],
  [0.16, 0.19, 0.24, 1.0],
  [0.05, 0.05, 0.055, 0.0],   // wet dark asphalt
  [0.04, 0.08, 0.03, 0.62],   // conifer crowns shed part of the snow
  [0.12, 0.10, 0.09, 0.85],   // bare branches
  [0.02, 0.03, 0.035, 0.0],
  [0.10, 0.14, 0.05, 1.0],
  [0.16, 0.12, 0.08, 1.0],
  [0.07, 0.07, 0.075, 0.25],
  [0.32, 0.28, 0.22, 0.9],
];
const V4 = (rows) => rows.map((r) => new THREE.Vector4(...r));

// ---- ground heights (farGround)
let GROUND = null;
function bilin(a, nx, ny, fx, fy) {
  fx = Math.min(Math.max(fx, 0), nx - 1.001); fy = Math.min(Math.max(fy, 0), ny - 1.001);
  const i = Math.floor(fx), j = Math.floor(fy), ax = fx - i, ay = fy - j, k = j * nx + i;
  return (a[k] * (1 - ax) + a[k + 1] * ax) * (1 - ay) + (a[k + nx] * (1 - ax) + a[k + nx + 1] * ax) * ay;
}
/** height (m above T.P.) of the far terrain at x, y: DEM + roof relief (without the 3 m the mesh is sunk under the tiles), the local maximum within +/-60 m
 *  on a 120 m grid inside +/-24 km, 600 m grid out to +/-60 km, clamped to the nearest sample beyond.  0 until loadFar has finished. */
export function farGround(x, y) {
  const G = GROUND; if (!G) return 0;
  const a = G.inner, b = G.outer;
  const fx = (x - a.o[0]) / a.res, fy = (y - a.o[1]) / a.res;
  const use = fx >= -0.05 && fy >= -0.05 && fx <= a.nx - 0.95 && fy <= a.ny - 0.95;       // (the mesh edge is quantised to ~2 m)
  const h = use ? bilin(a.d, a.nx, a.ny, fx, fy) : bilin(b.d, b.nx, b.ny, (x - b.o[0]) / b.res, (y - b.o[1]) / b.res);
  return G.z0 + h * G.step;
}

function decodeStreams(bin, streams) {
  const src = new Uint8Array(bin); const S = {};
  for (const s of streams) {
    const part = src.subarray(s.off, s.off + s.len);
    if (s.kind === 'i') { const out = new Uint32Array(s.count); MeshoptDecoder.decodeIndexBuffer(new Uint8Array(out.buffer), s.count, 4, part); S[s.name] = out; }
    else { const out = new Uint8Array(s.count * s.stride); MeshoptDecoder.decodeVertexBuffer(out, s.count, s.stride, part); S[s.name] = out; }
  }
  return S;
}

/** Build the far material (exported for tests).  meta = far.json, ras = the class texture. */
export function makeFarMaterial({ G, meta, ras, derivNormals = false }) {
  const [ex0, ey0, ex1, ey1] = meta.extent, SZ = ex1 - ex0, HALF = SZ / 2;
  const cx = (ex0 + ex1) / 2, cy = (ey0 + ey1) / 2;
  const lutA = uniformArray(V4(AUTUMN), 'vec4').setGroup(renderGroup), lutW = uniformArray(V4(WINTER), 'vec4').setGroup(renderGroup);
  const wp = positionWorld;
  const SNOW = vec3(0.80, 0.82, 0.86);
  const SKY = vec3(0.55, 0.62, 0.78).mul(1.9);                        // evening sky colour (irradiance of an unoccluded flat surface = SKY * irrGain * irrScale)

  // ---- per-fragment (shared) terms: footprint, noise at tree-crown and stand scales, both faded out when a pixel covers too much ground
  const fpm = length(wp.dFdx()).add(length(wp.dFdy()));                 // metres per pixel
  const a1 = float(1.0).sub(smoothstep(5.0, 18.0, fpm)), a2 = float(1.0).sub(smoothstep(30.0, 120.0, fpm));
  const nA = mx_noise_float(vec3(wp.xy.mul(0.11), 0.37)), nB = mx_noise_float(vec3(wp.xy.mul(0.27), 1.13)), nC = mx_noise_float(vec3(wp.xy.mul(0.0222), 1.7));
  const cr = smoothstep(0.15, 0.85, nA.mul(0.6).add(nB.mul(0.35)).add(0.5));
  const crown = mix(float(1.0), mix(float(0.4), float(1.3), cr), a1).toVar();       // dark gaps between the crowns
  const mott = nC.mul(a2).toVar();                                                   // stand-scale mottling, +/-0.7

  // ---- normal: smooth normal of the bare terrain from the mesh (attr.zw), or the screen-space derivative normal (opts.derivNormals)
  const at = attribute('attr', 'vec4');
  let nW;
  if (derivNormals) {
    const cr3 = cross(wp.dFdx(), wp.dFdy()); const l = length(cr3);
    nW = normalize(cr3.div(max(l, 1e-9))); nW = nW.mul(nW.z.lessThan(0.0).select(-1.0, 1.0));
  } else {
    const nxy = at.zw.mul(2.0).sub(1.0);
    nW = vec3(nxy.x, nxy.y, sqrt(max(float(1.0).sub(dot(nxy, nxy)), 0.0)));
  }
  const nz = clamp(nW.z, 0.0, 1.0);
  const steep = float(1.0).sub(smoothstep(0.78, 0.90, nz));                          // slopes beyond ~35 deg keep less snow
  const snowSlope = float(1.0).sub(steep.mul(0.55));
  const season = G.season;

  // ---- one raster sample -> shaded albedo (rgb) and water weight (a)
  const tap = (uvT) => {
    const t = texture(ras, uvT);
    const c = t.r.mul(255.0).add(0.5).floor(), g = t.g;
    const ci = c.toInt();
    const A = lutA.element(ci), W = lutW.element(ci);
    const inR = (lo, hi) => step(lo, c).mul(step(c, hi));
    const isForest = inR(4.5, 6.5), isDec = inR(5.5, 6.5), isWater = inR(6.5, 7.5), isGrass = inR(7.5, 8.5), isMetal = inR(2.5, 3.5);
    let base = mix(A.rgb, W.rgb, season);
    // metal roofs: blue or brown by g
    base = mix(base, vec3(0.22, 0.15, 0.11), isMetal.mul(step(0.5, g)));
    // grass yellows in autumn
    const hay = clamp(float(0.5).add(mott.mul(1.1)).add(g.sub(0.5).mul(0.6)), 0.0, 1.0).mul(0.8);
    base = mix(base, mix(base, vec3(0.22, 0.19, 0.07), hay), isGrass.mul(float(1.0).sub(season)));
    // deciduous in autumn: red / orange / yellow by g and the stand-scale noise
    const hp = clamp(float(0.5).add(g.sub(0.5).mul(0.7)).add(mott.mul(0.55)), 0.0, 1.0);
    // mostly the yellow-brown of the oaks (コナラ), red maples in a few stands, yellow here and there; a share of evergreens inside
    const dec = mix(mix(vec3(0.36, 0.07, 0.03), vec3(0.27, 0.18, 0.06), smoothstep(0.18, 0.32, hp)), vec3(0.40, 0.31, 0.06), smoothstep(0.7, 0.85, hp));
    base = mix(base, mix(dec, vec3(0.045, 0.08, 0.03), 0.3), isDec.mul(float(1.0).sub(season)));
    // variation: per object (G) for everything with a variation amplitude, tree crowns for forests
    const v = mix(float(1.0).add(A.a.mul(g.sub(0.5)).mul(0.9)), crown.mul(float(0.7).add(g.mul(0.6))), isForest);
    let col = base.mul(v);
    // snow
    const sn = season.mul(W.a).mul(snowSlope);
    const tone = mix(float(0.92).add(g.mul(0.08)), float(0.55).add(crown.mul(0.45)), isForest);
    col = mix(col, SNOW.mul(tone), sn);
    return vec4(col, isWater);
  };

  const uv0 = vec2(wp.x.sub(ex0).div(SZ), float(ey1).sub(wp.y).div(SZ));
  const dux = uv0.dFdx().mul(0.3), duy = uv0.dFdy().mul(0.3);
  const T = tap(uv0.add(dux).add(duy)).add(tap(uv0.add(dux).sub(duy))).add(tap(uv0.sub(dux).add(duy))).add(tap(uv0.sub(dux).sub(duy))).mul(0.25).toVar();

  // ---- outside the raster (the horizon ring): forest on the heights, grey-brown low, sea at 0 m; blended in over the last 1.5 km of the raster
  const dInf = max(abs(wp.x.sub(cx)), abs(wp.y.sub(cy)));
  const outW = smoothstep(HALF - 1500.0, HALF - 100.0, dInf);
  const hill = smoothstep(60.0, 170.0, wp.z);
  const fdec = smoothstep(0.35, 0.65, float(0.5).add(mott.mul(0.8)));
  const forestA = mix(vec3(0.04, 0.075, 0.03), vec3(0.26, 0.17, 0.06), fdec.mul(0.45)).mul(mix(float(1.0), crown, 0.6));
  const forestW = mix(vec3(0.05, 0.07, 0.04), vec3(0.12, 0.10, 0.09), fdec.mul(0.4));
  const lowA = vec3(0.14, 0.13, 0.115), lowW = lowA;
  let fb = mix(mix(lowA, forestA, hill), mix(lowW, forestW, hill), season);
  fb = mix(fb, SNOW.mul(0.95), season.mul(0.85).mul(snowSlope));
  const sea = float(1.0).sub(smoothstep(0.8, 2.0, wp.z));
  fb = mix(fb, vec3(0.02, 0.03, 0.035), sea);
  const alb = mix(T.rgb, fb, outW);
  const waterW = mix(T.a, sea, outW);

  // ---- light: albedo * (sky * skyVis + sun * max(n.l, 0) * sunVis) / PI;  attr.x = sky visibility, attr.y = sun visibility (0..1, soft edge)
  const k = float(0.5).add(nz.mul(0.5));
  const irr = SKY.mul(at.x).mul(k).mul(G.irrGain).mul(G.irrScale);
  const sun = G.sunCol.mul(max(dot(nW, G.sunDir), 0.0)).mul(at.y);
  let col = alb.mul(irr.add(sun)).div(Math.PI);
  // water: a little sky reflection (Schlick)
  const V = normalize(cameraPosition.sub(wp));
  const fres = mix(float(0.03), float(1.0), pow(float(1.0).sub(clamp(dot(V, nW), 0.0, 1.0)), 5.0));
  col = mix(col, SKY.mul(G.irrScale).mul(0.8), fres.mul(waterW));

  const mat = new THREE.MeshBasicNodeMaterial();
  mat.colorNode = col;
  mat.name = 'kyoto-far';
  return mat;
}

/** Load the far field into the scene.  opts: G (the shared uniforms from kyomat.js), base (default 'data/far'), backend (renderer.backend, to drop the CPU copies once uploaded),
 *  derivNormals (use screen-space derivative normals instead of the smooth normals shipped in the mesh), renderOrder (default -100; a large positive value draws
 *  it after the opaque tiles so that early-z skips the pixels they cover).  Resolves { mesh, meta, texture, farGround, dispose }. */
export async function loadFar(scene, { G, base = 'data/far', backend = null, derivNormals = false, renderOrder = -100 } = {}) {
  await MeshoptDecoder.ready;
  const getJSON = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); });
  const getBlob = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.blob(); });
  const [meta, bin, blob] = await Promise.all([getJSON(`${base}/far.json`), fetchBin(`${base}/far.bin`), getBlob(`${base}/far_class.png`)]);
  const S = decodeStreams(bin, meta.mesh.streams);
  // class raster: raw RGBA values, no colour management, nearest filtering, no mipmaps (the shader averages a few taps over the pixel footprint itself)
  const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none', imageOrientation: 'none' });
  const ras = new THREE.Texture(bmp);
  ras.colorSpace = THREE.NoColorSpace; ras.flipY = false; ras.generateMipmaps = false;
  ras.minFilter = THREE.NearestFilter; ras.magFilter = THREE.NearestFilter; ras.wrapS = ras.wrapT = THREE.ClampToEdgeWrapping;
  ras.onUpdate = () => { ras.onUpdate = null; try { bmp.close(); } catch (e) { /* already closed */ } };   // the GPU has it now
  ras.needsUpdate = true;
  // ground heights
  const sd = (n) => { const s = meta.mesh.streams.find((q) => q.name === n); return new Uint16Array(S[n].buffer, 0, s.n); };
  const gm = meta.ground;
  GROUND = { inner: { ...gm.inner, d: sd(gm.inner.stream) }, outer: { ...gm.outer, d: sd(gm.outer.stream) }, z0: gm.z0, step: gm.step };
  // mesh
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Uint16Array(S.pos.buffer), 4, true));
  g.setAttribute('attr', new THREE.BufferAttribute(S.attr, 4, true));
  g.setIndex(new THREE.BufferAttribute(S.idx, 1));
  g.boundingBox = new THREE.Box3(new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 1, 1));
  g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
  const mat = makeFarMaterial({ G, meta, ras, derivNormals });
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = 'far';
  mesh.position.set(...meta.mesh.qmin); mesh.scale.set(...meta.mesh.qext);        // per-axis extents: x, y 120 km, z ~1.4 km
  mesh.frustumCulled = false; mesh.castShadow = false; mesh.receiveShadow = false; mesh.renderOrder = renderOrder;
  mesh.matrixAutoUpdate = false; mesh.updateMatrix();
  scene.add(mesh);
  toGPU(mesh, backend);
  return {
    mesh, meta, texture: ras, farGround, material: mat,
    dispose() { scene.remove(mesh); g.dispose(); mat.dispose(); ras.dispose(); GROUND = null; },
  };
}
