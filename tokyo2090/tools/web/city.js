import * as THREE from 'three';
import { fetchBin } from './data.js';
import { shadowGLSL } from './light.js';

// The ruined city from tools/gen/city.py: one gzip file per 250 m tile holding a full mesh and a lite mesh.
// Tiles near the camera show the full mesh, far ones the lite boxes; facades, broken floors and overgrowth are
// drawn in the shader from the packed vertex attributes (no textures).

const vert = /* glsl */`
  attribute vec3 ap;      // uint16: cm, cm, 2 cm from the tile corner
  attribute vec3 an;      // int8 normal (x east, y north, z up)
  attribute vec4 ak;      // kind, seed, hcls, veg (uint8)
  attribute float ahb;    // uint16: 0.1 m above the building base
  attribute float al;     // uint8: landmark id (0 none)
  uniform vec3 origin;    // tile corner (x, y, z) in data axes
  varying vec3 vW; varying vec3 vN; varying vec4 vK; varying float vHb; varying float vL;
  void main(){
    vec3 d = vec3(ap.x * 0.01, ap.y * 0.01, ap.z * 0.02) + origin;
    vec3 w = vec3(d.x, d.z, -d.y);
    vW = w; vN = normalize(vec3(an.x, an.z, -an.y)); vK = ak; vHb = ahb * 0.1; vL = al;
    gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
  }`;

const frag = /* glsl */`
  precision highp float;
  #include <packing>
  ${shadowGLSL}
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos; uniform float lite;
  uniform sampler2D atlas; uniform sampler2D atlasMask; uniform sampler2D detail; uniform float dbg;
  varying vec3 vW; varying vec3 vN; varying vec4 vK; varying float vHb; varying float vL;
  const float COLS = 8.0, ROWS = 3.0;
  // bay width and storey height per style: curtain precast mansion tile house danchi glass darktile
  const float BAY[8] = float[8](3.2, 3.4, 3.6, 3.0, 2.7, 3.6, 3.0, 3.2);
  const float FLOOR[8] = float[8](3.9, 3.7, 3.0, 3.0, 2.8, 2.8, 4.0, 3.4);
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<3;k++){ v += a*noise(p); p = p*2.1 + 5.3; a *= 0.5; } return v; }
  void main(){
    vec3 N = normalize(vN);
    bool inside = !gl_FrontFacing; if(inside) N = -N;
    // the packed per-building values are integers: round them, or interpolation jitter re-rolls every hash per pixel
    float kind = vK.x > 5.5 ? 2.0 : vK.x, sid = floor(vK.y + 0.5), seed = sid / 255.0, H = floor(vK.z + 0.5) * 2.0, veg = floor(vK.w + 0.5) / 255.0;   // 6 = floor stub, drawn as a broken floor
    vec2 xy = vec2(vW.x, -vW.z);
    vec3 up = vec3(0.0, 1.0, 0.0);
    vec3 T = normalize(cross(up, N) + vec3(1e-4, 0.0, 0.0));
    float u = dot(vW, T), v = vHb;
    float s1 = hash(vec2(sid, 3.0)), s2 = hash(vec2(sid, 9.0)), s3 = hash(vec2(sid, 17.0));
    // which Tokyo building this is, from its height and seed
    int style; bool shopGround = false;
    if(H > 60.0){ style = s2 < 0.5 ? 0 : (s2 < 0.75 ? 6 : 1); shopGround = s3 < 0.5; }
    else if(H > 25.0){ style = s1 < 0.4 ? 2 : (s1 < 0.7 ? 1 : (s1 < 0.85 ? 7 : 3)); shopGround = s3 < 0.6; }
    else if(H > 11.0){ style = s1 < 0.45 ? 2 : (s1 < 0.7 ? 3 : (s1 < 0.85 ? 5 : 7)); shopGround = s3 < 0.5; }
    else { style = s1 < 0.7 ? 4 : 3; shopGround = s3 < 0.2; }
    float bay = BAY[style], floorH = FLOOR[style];
    bool house = style == 4, glassy = style == 0 || style == 6;
    // the world-space detail: grain, stains, cracks, leaves (8 m period)
    vec4 dtl = texture2D(detail, (kind < 0.5 ? vec2(u, v) : xy) / 8.0 + seed);
    vec4 dtl2 = texture2D(detail, (kind < 0.5 ? vec2(u, v) : xy) / 2.3 + seed * 3.0);
    vec3 col; float glass = 0.0, ao = 0.0, metal = 0.0, hole = 0.0;
    // facade cell in the atlas; derivatives of the unwrapped coordinates, taken outside any branch (undefined inside)
    vec2 cell = vec2(u / bay, v / floorH);
    vec2 dx = dFdx(cell) / vec2(COLS, ROWS), dy = dFdy(cell) / vec2(COLS, ROWS);
    if(kind < 0.5){
      float fl = floor(cell.y), fu = fract(cell.x), fv = fract(cell.y);
      float row = fl < 1.0 ? (shopGround ? 2.0 : 1.0) : 0.0;
      vec2 auv = vec2((float(style) + fu) / COLS, (ROWS - 1.0 - row + fv) / ROWS);
      vec4 A = textureGrad(atlas, auv, dx, dy);
      vec4 M = textureGrad(atlasMask, auv, dx, dy);
      // a wrapped atlas cannot be averaged across cells by mipmaps: when a cell covers only a few pixels (far away,
      // or a wall seen edge-on) blend toward the cell's mean, which is one texel at mip level 8 (8 x 3 texels)
      float pxPerCell = 1.0 / max(max(length(dFdx(cell)), length(dFdy(cell))), 1e-5);
      float fine = smoothstep(4.0, 14.0, pxPerCell);
      vec2 cuv = vec2((float(style) + 0.5) / COLS, (ROWS - 1.0 - row + 0.5) / ROWS);
      vec4 Am = textureLod(atlas, cuv, 8.0); Am.rgb = mix(Am.rgb, vec3(dot(Am.rgb, vec3(0.33))), 0.35) * 0.82;
      A = mix(Am, A, fine); M = mix(textureLod(atlasMask, cuv, 8.0), M, fine);
      // the same cell a little higher: is there a window whose sill drips on this spot?
      vec4 Mup = textureGrad(atlasMask, auv + vec2(0.0, 0.22 / ROWS), dx, dy);
      if(dbg > 0.5){
        vec3 o = dbg < 1.5 ? A.rgb : dbg < 2.5 ? M.rgb : dbg < 3.5 ? dtl.rgb : dbg < 4.5 ? dtl2.rgb : dbg < 5.5 ? vec3(length(dx) * 400.0, length(dy) * 400.0, 0.0) : dbg < 6.5 ? texture2D(atlas, auv).rgb : dbg < 7.5 ? vec3(fract(cell), 0.0) : dbg < 8.5 ? textureLod(atlas, auv, 5.0).rgb : dbg < 9.5 ? vec3(fine) : dbg < 10.5 ? vec3(fract(vW.x * 0.25), fract(vW.z * 0.25), fract(vW.y * 0.25)) : dbg < 11.5 ? N * 0.5 + 0.5 : vec3(fract(u * 0.3), fract(v * 0.3), 0.0);
        gl_FragColor = vec4(o, 1.0); return; }
      glass = M.r; ao = M.g; metal = M.b;
      col = A.rgb;
      // sixty years of weather on the wall itself: faded, grey-brown, sun-bleached on the sunny side
      col = mix(col, vec3(dot(col, vec3(0.33))), 0.2);
      col *= (0.95 + 0.15 * dtl.r) * mix(vec3(0.84, 0.86, 0.90), vec3(1.0, 0.97, 0.90), hash(vec2(sid, 29.0)));   // cool grey to sun-bleached, per building
      // breaches: sections of wall fallen away (more on tall, overgrown and sun-cracked buildings), with jagged edges
      float br = noise(vec2(u * 0.06, v * 0.035) + seed * 80.0) * 0.8 + noise(vec2(u * 0.3, v * 0.2) + seed * 3.0) * 0.2;
      float breachP = 0.62 - veg * 0.08 - smoothstep(10.0, 80.0, H) * 0.1 - smoothstep(0.0, 40.0, v) * 0.06;
      float breach = smoothstep(breachP, breachP + 0.04, br) * step(2.5, v);
      // the glass: per window, gone (dark room behind), dusty, or still catching the sky
      // broken panels come in patches (a fire, a storm side, the floors a tree fell through), not one by one
      float bayI = floor(cell.x);
      float gone = noise(vec2(bayI * (glassy ? 0.05 : 0.33), fl * (glassy ? 0.5 : 0.45)) + seed * 50.0) * (glassy ? 0.85 : 0.75) + hash(vec2(bayI * 7.7 + seed * 300.0, fl * 3.1)) * (glassy ? 0.15 : 0.25);
      float breakP = glassy ? 0.3 : 0.34; breakP += veg * 0.12 + smoothstep(0.0, 60.0, v) * 0.06;
      if(glass > 0.5){
        if(gone < breakP){
          // the room behind: near black, a slab line, dust
          vec3 room = (glassy ? vec3(0.09, 0.095, 0.10) : vec3(0.05, 0.047, 0.042)) * (0.6 + 0.8 * dtl2.r);
          room += vec3(0.05, 0.045, 0.04) * smoothstep(0.08, 0.0, abs(fv - 0.19));
          col = room; hole = 1.0;
        } else {
          float dusty = glassy ? 0.0 : step(0.78, hash(vec2(bayI, fl) + seed * 5.0));
          vec3 tint = glassy ? vec3(0.12, 0.17, 0.21) : vec3(0.14, 0.18, 0.20);
          vec3 sky = mix(groundCol, skyCol, 0.5 + 0.5 * N.y) * 1.25;
          col = mix(tint * 0.6 + sky * (glassy ? 0.12 : 0.35), vec3(0.36, 0.34, 0.30), dusty * (glassy ? 0.3 : 0.55));
          col *= 0.93 + 0.14 * hash(vec2(fl, bayI) + seed);
        }
      }
      // the landmarks: Tokyo Tower's lattice, the Tocho's granite grid, the Cocoon's white diagonal web, Docomo's clock tower brick
      float lm = floor(vL + 0.5);
      if(lm > 0.5){
        if(lm < 1.5){
          // Tokyo Tower: faded international orange and white bands, rusting; cross-braces as a diagonal lattice
          float band = step(0.5, fract(v / 28.0 + 0.25));
          vec3 paint = mix(vec3(0.72, 0.22, 0.08), vec3(0.78, 0.74, 0.68), band);
          float lat = max(smoothstep(0.42, 0.5, abs(fract((u + v * 0.9) / 7.0) - 0.5)), smoothstep(0.42, 0.5, abs(fract((u - v * 0.9) / 7.0) - 0.5)));
          float post = smoothstep(0.44, 0.5, abs(fract(u / 7.0) - 0.5));
          vec3 skyBehind = mix(groundCol, skyCol, 0.6) * 1.3;
          col = mix(skyBehind * 0.55, paint, max(lat, post));
          col = mix(col, vec3(0.30, 0.16, 0.09), smoothstep(0.4, 0.8, dtl.g) * 0.7);
          glass = 0.0; hole = 0.0; metal = 1.0; ao = 0.0;
        } else if(lm < 2.5){
          // Tocho: pale granite with the dark window grid of the real towers (two-tone checker in 3 m bays)
          float gx = fract(u / 3.0), gy = fract(v / 4.0);
          float dark = step(0.5, fract(floor(u / 3.0) * 0.5 + floor(v / 8.0) * 0.5)) * step(0.15, gx) * step(0.15, gy);
          col = mix(vec3(0.52, 0.50, 0.47), vec3(0.17, 0.18, 0.20), dark * 0.85);
          glass = dark; hole = 0.0; metal = 0.0;
        } else if(lm < 3.5 || lm > 7.5){
          // Cocoon (and the Docomo tower): a white diagonal web over dark glass
          float w1 = smoothstep(0.46, 0.5, abs(fract((u + v * 0.6) / 9.0) - 0.5)), w2 = smoothstep(0.46, 0.5, abs(fract((u - v * 0.6) / 9.0) - 0.5));
          vec3 dglass = vec3(0.10, 0.14, 0.18) + mix(groundCol, skyCol, 0.5) * 0.15;
          col = mix(dglass, vec3(0.82, 0.82, 0.80), max(w1, w2));
          if(lm > 7.5) col = mix(vec3(0.55, 0.42, 0.34), dglass, smoothstep(0.3, 0.7, fract(u / 6.0)) * 0.5);
          glass = 1.0 - max(w1, w2); hole = 0.0; metal = 0.0;
        }
      }
      if(breach > 0.5){
        float slab = smoothstep(0.1, 0.0, abs(fract(v / floorH) - 0.08));
        vec3 interior = vec3(0.07, 0.065, 0.06) * (0.5 + dtl2.r) + vec3(0.22, 0.20, 0.18) * slab;
        // rebar and torn edges around the opening
        float edge = smoothstep(breachP + 0.04, breachP + 0.065, br);
        col = mix(mix(vec3(0.26, 0.17, 0.10), vec3(0.24, 0.22, 0.20), dtl2.r), interior, edge);
        glass = 0.0; hole = 1.0; metal = 0.0; ao = 0.3;
      }
      // metal (railings, shutters, sign boxes) rusts
      float rust = smoothstep(0.35, 0.7, dtl.g + dtl2.b * 0.4);
      col = mix(col, mix(vec3(0.40, 0.22, 0.12), vec3(0.22, 0.12, 0.07), dtl2.r), metal * (0.45 + 0.5 * rust));
      // concrete spalls along cracks: the render falls off and shows darker aggregate and rust lines
      float spall = smoothstep(0.66, 0.86, dtl.g) * (1.0 - glass) * (1.0 - metal) * (house ? 0.4 : 1.0);
      vec3 inner = mix(vec3(0.46, 0.43, 0.39), vec3(0.34, 0.31, 0.28), dtl2.r);
      float rebar = smoothstep(0.8, 0.95, noise(vec2(u * 6.0, v * 0.3) + seed)) * spall;
      col = mix(col, inner, spall * 0.85); col = mix(col, vec3(0.45, 0.22, 0.10), rebar * 0.8);
      col = mix(col, vec3(0.30, 0.28, 0.26), dtl2.b * 0.22 * (1.0 - glass) * smoothstep(0.4, 0.7, dtl.g));   // fine cracks near the stains
      // black streaks running down from sills and from the top
      float runs = smoothstep(0.45, 0.9, noise(vec2(u * 1.6, v * 0.12) + seed * 10.0)) * (0.7 + 0.5 * smoothstep(H - 12.0, H, v));
      float fromSill = Mup.r * smoothstep(0.0, 0.5, fv) * (1.0 - glass);
      float streak = runs * (0.35 + 0.65 * fromSill) * (1.0 - glass) * smoothstep(0.0, 1.0, dtl.g * 1.6);
      col = mix(col, vec3(0.16, 0.15, 0.13), streak * 0.6);
      // grime at the base and a green-black mould on the shaded faces
      float grime = 1.0 - smoothstep(0.0, 9.0, v);
      col *= 1.0 - 0.38 * grime;
      float shade = clamp(-dot(N, sunDir) * 0.8 + 0.3, 0.0, 1.0);
      col = mix(col, vec3(0.13, 0.17, 0.10), shade * smoothstep(0.5, 0.85, dtl.g) * 0.3 * (1.0 - glass));
    } else if(kind > 4.5){
      // tiled hip roofs: dark grey, brown or blue-black tiles with the courses as faint lines, moss in the shade
      vec3 t0 = vec3(0.26, 0.25, 0.26), t1 = vec3(0.34, 0.24, 0.18), t2 = vec3(0.20, 0.22, 0.30), t3 = vec3(0.42, 0.40, 0.38);
      float pick = hash(vec2(sid, 41.0));
      col = pick < 0.4 ? t0 : pick < 0.65 ? t1 : pick < 0.85 ? t2 : t3;
      float course = smoothstep(0.85, 1.0, fract(v * 3.3)) * 0.25;
      col *= (0.9 + 0.2 * dtl.r) - course;
      col = mix(col, vec3(0.30, 0.26, 0.20), smoothstep(0.5, 0.85, dtl.g) * 0.5);
    } else if(kind > 3.5){
      // sheet metal: tanks, air conditioners, vents — galvanised grey gone to rust
      col = mix(vec3(0.55, 0.56, 0.55), vec3(0.62, 0.62, 0.60), dtl2.r);
      float rust = smoothstep(0.3, 0.75, dtl.g + dtl2.b * 0.3);
      col = mix(col, mix(vec3(0.42, 0.22, 0.11), vec3(0.24, 0.13, 0.07), dtl2.r), rust * 0.85);
    } else if(kind > 2.5){
      // parapets and bulkheads: the roof's concrete, streaked
      col = mix(vec3(0.60, 0.58, 0.54), vec3(0.70, 0.68, 0.63), dtl.r);
      col = mix(col, vec3(0.30, 0.28, 0.26), smoothstep(0.45, 0.85, dtl.g) * 0.55);
      col = mix(col, vec3(0.16, 0.15, 0.13), smoothstep(0.5, 0.9, noise(vec2(u * 1.6, v * 0.3) + seed * 10.0)) * 0.3);
    } else if(kind > 1.5){
      // the broken floor: slab dust, rubble, bent rebar
      col = mix(vec3(0.40, 0.38, 0.35), vec3(0.58, 0.55, 0.50), dtl.r);
      col = mix(col, vec3(0.30, 0.28, 0.26), smoothstep(0.5, 0.85, dtl2.g) * 0.7);
      col = mix(col, vec3(0.42, 0.24, 0.13), smoothstep(0.75, 0.95, dtl2.b + dtl.b * 0.5) * 0.8);
    } else {
      // roofs: grey membrane and gravel, water-stained, grass in the dust
      col = mix(vec3(0.48, 0.47, 0.44), vec3(0.62, 0.60, 0.55), dtl.r);
      if(house) col = mix(vec3(0.33, 0.30, 0.30), vec3(0.47, 0.42, 0.38), s3) * (0.8 + 0.4 * dtl2.r);
      col = mix(col, vec3(0.30, 0.29, 0.26), smoothstep(0.45, 0.8, dtl.g) * 0.6);
    }
    // roots of the trees above: pale grey-brown ropes that fork on the way down, thickest near the top and on the overgrown
    float rootN = 1.0 - abs(noise(vec2(u * 0.45 + v * 0.06, v * 0.05) + seed * 23.0) * 2.0 - 1.0);
    float rootN2 = 1.0 - abs(noise(vec2(u * 1.1 - v * 0.04, v * 0.09) + seed * 31.0) * 2.0 - 1.0);
    float fromTop = smoothstep(H - 45.0 - veg * 30.0, H - 3.0, v) * (kind < 0.5 ? 1.0 : 0.0);
    float roots = (smoothstep(0.78, 0.92, rootN) + smoothstep(0.84, 0.95, rootN2) * 0.7) * (0.25 + veg) * fromTop;
    roots += smoothstep(0.8, 0.93, rootN) * veg * 0.5 * (kind < 0.5 ? 1.0 : 0.0);          // and up from the ground
    vec3 rootCol = mix(vec3(0.42, 0.37, 0.30), vec3(0.28, 0.23, 0.17), dtl2.r);
    col = mix(col, rootCol, clamp(roots, 0.0, 1.0) * 0.9);
    // the plants: vines climb from the ground and spill from broken windows; moss settles on every flat surface
    // vines grow in a few thick ropes from the ground, fanning out as they climb; only the dense heart of a clump is solid
    float climb = veg * (1.0 - smoothstep(6.0, 16.0 + veg * 70.0, v)) + fromTop * veg * 0.6;
    float leaves = dtl.a;
    float rope = smoothstep(0.55, 0.8, noise(vec2(u * 0.35 + v * 0.05, v * 0.04) + seed * 40.0));
    float clump = smoothstep(0.5, 0.75, noise(vec2(u * 0.6, v * 0.5) + seed * 7.0));
    float vine = (kind < 0.5 ? 1.0 : 0.0) * leaves * smoothstep(0.1, 0.5, climb * (0.45 + rope + 0.7 * clump * rope));
    float spill = (kind < 0.5 ? 1.0 : 0.0) * hole * leaves * step(0.45, hash(vec2(floor(u / bay), floor(v / floorH)) + seed * 9.0) + veg * 0.6 - 0.3) * (1.0 - smoothstep(25.0, 70.0, v) * 0.6) * 0.95;
    float moss = (kind > 0.5 && kind < 2.5 ? 1.0 : 0.0) * smoothstep(0.25, 0.6, dtl.g) * (0.5 + 0.6 * veg) * (0.5 + 0.5 * dtl2.r) + (kind > 4.5 ? 0.5 * smoothstep(0.45, 0.8, dtl.g) * (0.3 + veg) : 0.0) + (kind > 2.5 && kind < 4.5 ? 0.4 * smoothstep(0.5, 0.8, dtl.g) * veg : 0.0);
    // a green film of moss and lichen on the walls of the damp side, and grass on every exposed slab
    float film = (kind < 0.5 ? 1.0 : 0.0) * smoothstep(0.3, 0.7, dtl.g * 0.6 + dtl2.g * 0.4) * (0.15 + 0.6 * veg) * (1.0 - glass) * (0.5 + 0.5 * clamp(-dot(N, sunDir) + 0.5, 0.0, 1.0));
    col = mix(col, vec3(0.20, 0.27, 0.12), film * 0.55);
    if(kind > 1.5 && kind < 2.5) moss = max(moss, smoothstep(0.3, 0.55, dtl.a + dtl.g * 0.5) * 0.8);
    vec3 leaf = mix(vec3(0.12, 0.22, 0.07), vec3(0.30, 0.38, 0.13), dtl2.r);
    float plant = clamp(vine + spill + moss, 0.0, 1.0);
    col = mix(col, leaf, plant * 0.95);
    if(inside){ col = mix(vec3(0.10, 0.09, 0.08), vec3(0.16, 0.18, 0.12), dtl.g * veg) * (0.5 + 0.7 * dtl2.r); }
    // light
    float dif = max(dot(N, sunDir), 0.0) * shadowAt(vW, N, sunDir);
    if(plant > 0.3) dif *= 0.85;
    if(inside) dif *= 0.35;
    vec3 amb = mix(groundCol, skyCol, N.y * 0.5 + 0.5) * (0.9 + 0.3 * smoothstep(0.0, 20.0, v)) * (1.0 - 0.6 * ao);
    vec3 light = sunCol * dif + amb;
    if(glass > 0.5 && hole < 0.5 && plant < 0.3){ vec3 V = normalize(camPos - vW); vec3 R = reflect(-sunDir, N); light += sunCol * pow(max(dot(R, V), 0.0), 60.0) * 0.8; }
    vec3 rgb = col * light;
    float d = length(vW - camPos); float f = 1.0 - exp(-fogDen * d);
    rgb = mix(rgb, fogCol, f);
    gl_FragColor = vec4(rgb, 1.0);
  }`;

const depthVert = /* glsl */`
  attribute vec3 ap; uniform vec3 origin;
  void main(){ vec3 d = vec3(ap.x * 0.01, ap.y * 0.01, ap.z * 0.02) + origin; gl_Position = projectionMatrix * viewMatrix * vec4(d.x, d.z, -d.y, 1.0); }`;
const depthFrag = /* glsl */`
  #include <packing>
  void main(){ gl_FragColor = packDepthToRGBA(gl_FragCoord.z); }`;
export function makeCityDepthMaterial() { return new THREE.ShaderMaterial({ uniforms: { origin: { value: new THREE.Vector3() } }, vertexShader: depthVert, fragmentShader: depthFrag }); }

export function makeCityMaterial(uniforms) {
  return new THREE.ShaderMaterial({ uniforms: { ...uniforms, dbg: { value: 0 }, origin: { value: new THREE.Vector3() }, lite: { value: 0 } }, vertexShader: vert, fragmentShader: frag, side: THREE.DoubleSide });
}

function geometryFrom(buf, offset, nv, ni) {
  const STRIDE = 16;
  const bytes = new Uint8Array(buf, offset, nv * STRIDE);
  const ib = new THREE.InterleavedBuffer(new Uint16Array(bytes.slice().buffer), STRIDE / 2);
  const ib8 = new THREE.InterleavedBuffer(new Uint8Array(ib.array.buffer), STRIDE);
  const ib8s = new THREE.InterleavedBuffer(new Int8Array(ib.array.buffer), STRIDE);
  const g = new THREE.BufferGeometry();
  g.setAttribute('ap', new THREE.InterleavedBufferAttribute(ib, 3, 0, false));
  g.setAttribute('an', new THREE.InterleavedBufferAttribute(ib8s, 3, 6, false));
  g.setAttribute('ak', new THREE.InterleavedBufferAttribute(ib8, 4, 9, false));
  g.setAttribute('ahb', new THREE.InterleavedBufferAttribute(ib, 1, 7, false));
  g.setAttribute('al', new THREE.InterleavedBufferAttribute(ib8, 1, 13, false));
  const idx = new Uint32Array(buf.slice(offset + nv * STRIDE, offset + nv * STRIDE + ni * 4));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}

export class City {
  constructor(scene, material, base, index) {
    this.scene = scene; this.material = material; this.base = base; this.index = index;
    this.tiles = new Map(); this.loading = 0;
    for (const t of index.tiles) this.tiles.set(t.i + '_' + t.j, { head: t, state: 0, full: null, lite: null, mesh: null });
    this.fullRadius = 1400; this.liteRadius = 9000; this.maxLoading = 6; this.maxSwaps = 4;   // LOD swaps per frame (each uploads a mesh)
  }
  tileCenter(t) { return new THREE.Vector3(t.ox + 125, t.oz + 20, -(t.oy + 125)); }
  async load(key) {
    const t = this.tiles.get(key); if (!t || t.state) return;
    t.state = 1; this.loading++;
    try {
      const { head, buf, offset } = await fetchBin(`${this.base}/${t.head.i}_${t.head.j}.bin`);
      const full = geometryFrom(buf, offset, head.full.nv, head.full.ni);
      const lite = geometryFrom(buf, offset + head.full.nv * 16 + head.full.ni * 4, head.lite.nv, head.lite.ni);
      const sphere = new THREE.Sphere(this.tileCenter(t.head), 320);
      full.boundingSphere = sphere; lite.boundingSphere = sphere.clone();
      // every tile shares the world uniforms by reference and owns only its origin
      const m = new THREE.ShaderMaterial({ uniforms: { ...this.material.uniforms, origin: { value: new THREE.Vector3(head.ox, head.oy, head.oz) }, lite: { value: 0 } }, vertexShader: vert, fragmentShader: frag, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(lite, m); mesh.frustumCulled = true; mesh.castShadow = true;
      mesh.customDepthMaterial = makeCityDepthMaterial(); mesh.customDepthMaterial.uniforms.origin.value.copy(m.uniforms.origin.value);
      t.full = full; t.lite = lite; t.mesh = mesh; t.state = 2; this.scene.add(mesh);
    } catch (e) { console.warn('tile', key, e); t.state = 3; }
    this.loading--;
  }
  update(cam) {
    // choose by distance: nearest unloaded tiles first, full mesh within fullRadius
    const want = []; let swaps = 0;
    for (const [key, t] of this.tiles) {
      const c = this.tileCenter(t.head); const d = Math.hypot(c.x - cam.x, c.z - cam.z);
      if (t.state === 0 && d < this.liteRadius) want.push([d, key]);
      if (t.state === 2) { const full = d < this.fullRadius; const g = full ? t.full : t.lite; if (t.mesh.geometry !== g && swaps < this.maxSwaps) { t.mesh.geometry = g; swaps++; } }
    }
    want.sort((a, b) => a[0] - b[0]);
    for (const [, key] of want) { if (this.loading >= this.maxLoading) break; this.load(key); }
  }
  get ready() { let n = 0; for (const t of this.tiles.values()) if (t.state >= 2) n++; return n; }
}
