import * as THREE from 'three';
import { shadowGLSL } from './light.js';

// The ground: ring meshes from tools/gen/ground.py. Colour comes from the land-cover raster (what the ground was in
// the 2020s) reinterpreted sixty years later: asphalt cracked and grassed over, parks grown into forest, rails rusted.


// Close range (walking on the ground, 0-120 m): everything below `nearGround` is procedural and fades by the
// pixel footprint (FW, metres per pixel) so nothing shimmers: every feature is faded out when it gets smaller than
// ~a pixel and its mean is kept. Beyond `detR` metres the shader is exactly the old far look.
const vert = /* glsl */`
  varying vec3 vW; varying vec3 vN;
  void main(){ vec4 w = modelMatrix * vec4(position,1.0); vW = w.xyz; vN = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * w; }`;

const frag = /* glsl */`
  precision highp float;
  #include <packing>
  ${shadowGLSL}
  uniform sampler2D cover; uniform vec4 coverBox; // x0, y0(north), w, h in world metres (x east, y north)
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos; uniform float ringScale;
  uniform float detQ; uniform float detR;   // detail quality (1 full, 0 phone) and the radius it fades out by
  varying vec3 vW; varying vec3 vN;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<4;k++){ v += a*noise(p); p = p*2.03 + 7.1; a *= 0.5; } return v; }

  // ---- close-range detail helpers (sine-free hashes: stay clean at kilometre coordinates)
  float FW;                                                // metres per pixel on the ground (larger axis)
  float h12(vec2 p){ vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
  vec2 h22(vec2 p){ vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973)); q += dot(q, q.yzx + 33.33); return fract((q.xx + q.yz) * q.zy); }
  float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(h12(i), h12(i+vec2(1,0)), f.x), mix(h12(i+vec2(0,1)), h12(i+vec2(1,1)), f.x), f.y); }
  float fd(float size){ return 1.0 - smoothstep(0.4 * size, 1.3 * size, FW); }             // 1 while a feature of this size is resolved
  float dn(vec2 p, float size){ float f = fd(size); return f < 0.02 ? 0.0 : (vn(p / size) - 0.5) * 2.0 * f; }   // zero-mean noise, -1..1
  vec3 vor(vec2 p){                                         // F1, F2, cell id (jittered cells)
    vec2 ip = floor(p), fp = p - ip; float f1 = 9.0, f2 = 9.0, id = 0.0;
    for(int j = -1; j <= 1; j++) for(int i = -1; i <= 1; i++){
      vec2 g = vec2(float(i), float(j)); vec2 r = g + h22(ip + g) * 0.86 + 0.07 - fp; float d = dot(r, r);
      if(d < f1){ f2 = f1; f1 = d; id = h12(ip + g + 17.0); } else if(d < f2) f2 = d;
    }
    return vec3(sqrt(f1), sqrt(f2), id);
  }
  // one small thing per cell (leaf, pebble, flower): coverage 0..1, r = a random number for the colour
  float scatter(vec2 p, float cell, float size, float dens, float aniso, out float r){
    vec2 q = p / cell, ic = floor(q); vec2 h = h22(ic); r = h12(ic + 5.7);
    if(h.x > dens) return 0.0;
    vec2 d = (fract(q) - 0.5 - (h22(ic + 3.1) - 0.5) * 0.45) * cell;
    float a = r * 6.2832, ca = cos(a), sa = sin(a); d = vec2(ca * d.x + sa * d.y, -sa * d.x + ca * d.y); d.x *= aniso;
    float rad = size * (0.6 + 0.8 * h.y); float s = FW * 0.7 + rad * 0.12;
    return (1.0 - smoothstep(rad - s, rad + s, length(d))) * clamp(rad / (FW * 1.4), 0.0, 1.0);
  }
  vec2 coverUV(vec2 p){ vec2 uv = (p - coverBox.xy) / coverBox.zw;
  #ifdef COVER_FLIP
    uv.y = 1.0 - uv.y;
  #endif
    return uv; }
  float covR(vec2 p){ return textureLod(cover, coverUV(p), 0.0).r; }

  // The ground at 0-120 m. col comes in as the far colour and is replaced; hgt is a height in metres for bump shading,
  // tilt a per-slab lean of the normal, pud the share of standing water that mirrors the sky.
  void nearGround(inout vec3 col, vec2 xy, vec4 cv, float rr, float n1, float n2, out float hgt, out vec2 tilt, out float pud){
    hgt = 0.0; tilt = vec2(0.0); pud = 0.0;
    bool hi = detQ > 0.5;
    float aR = smoothstep(0.30, 0.50, rr);                              // asphalt
    float pv = smoothstep(0.12, 0.24, rr) * (1.0 - aR);                  // pavement: the skirt around a road
    float park = smoothstep(0.2, 0.9, cv.g) * (1.0 - aR);
    float wat = smoothstep(0.3, 0.7, cv.b), rail = smoothstep(0.3, 0.8, cv.a);
    float m1 = vn(xy * 0.9 + 13.0), m2 = vn(xy * 0.31 + 5.0);

    // ---- grass, scrub and forest floor
    vec3 gFresh = vec3(0.16, 0.29, 0.08), gDry = vec3(0.45, 0.41, 0.17), gDark = vec3(0.09, 0.17, 0.05);
    vec3 nat = mix(gFresh, gDry, smoothstep(0.4, 0.8, n2 * 0.7 + m2 * 0.4) * 0.75);
    nat = mix(nat, gDark, smoothstep(0.55, 0.2, m1) * 0.5);
    nat *= 1.0 + 0.30 * dn(xy + 7.0, 1.1) + 0.24 * dn(xy + 3.0, 0.32) + 0.2 * dn(xy * vec2(1.0, 1.3), 0.07);
    float thin = smoothstep(0.62, 0.30, vn(xy * 0.7 + 31.0));            // bare earth where the sward is thin
    nat = mix(nat, vec3(0.17, 0.12, 0.075) * (0.7 + 0.6 * m1), thin * 0.45);
    float lv, lc;
    vec3 flr = mix(vec3(0.085, 0.062, 0.04), vec3(0.16, 0.105, 0.055), vn(xy * 0.6 + 4.0));      // leaf litter
    float fern = smoothstep(0.5, 0.66, vn(xy * 0.75 + 21.0) + 0.2 * vn(xy * 3.0));
    flr = mix(flr, vec3(0.07, 0.165, 0.045) * (0.75 + 0.5 * vn(xy * 5.0)), fern * 0.8);
    float moss = smoothstep(0.58, 0.76, vn(xy * 1.4 + 40.0) + 0.25 * vn(xy * 6.0));
    flr = mix(flr, vec3(0.10, 0.22, 0.06), moss * 0.55);
    flr *= 1.0 + 0.45 * dn(xy + 1.0, 0.09) + 0.25 * dn(xy + 9.0, 0.5);
    vec3 base = mix(nat, flr, park);
    // flowers and clover in the open grass
    lv = scatter(xy + 3.0, 0.22, 0.013, 0.16, 1.0, lc);
    base = mix(base, lc < 0.5 ? vec3(0.62, 0.60, 0.5) : (lc < 0.8 ? vec3(0.62, 0.52, 0.12) : vec3(0.42, 0.28, 0.5)), lv * (1.0 - park) * 0.8);
    float litter = clamp(0.25 + 0.9 * (1.0 - m2) * (0.3 + park), 0.0, 1.0);   // how much fallen leaf cover here

    // ---- asphalt / pavement (the road structure, from the cover raster's own shape)
    vec3 road = vec3(0.2), pave = vec3(0.4);
    float kerb = 0.0, tact = 0.0;
    if(aR + pv > 0.02){
      float hh = 4.0;
      float r0 = covR(xy), rE = covR(xy + vec2(hh, 0.0)), rW = covR(xy - vec2(hh, 0.0)), rN = covR(xy + vec2(0.0, hh)), rS = covR(xy - vec2(0.0, hh));
      vec2 gr = vec2(rE - rW, rN - rS) / (2.0 * hh);
      float hxx = (rE + rW - 2.0 * r0) / (hh * hh), hyy = (rN + rS + -2.0 * r0) / (hh * hh), hxy = 0.0;
      if(hi){ hxy = (covR(xy + vec2(hh)) + covR(xy - vec2(hh)) - covR(xy + vec2(hh, -hh)) - covR(xy + vec2(-hh, hh))) / (4.0 * hh * hh); }
      float tr = hxx + hyy, dt = hxx * hyy - hxy * hxy, disc = sqrt(max(tr * tr * 0.25 - dt, 0.0)), l1 = tr * 0.5 - disc;   // l1: curvature across the road (negative on a ridge)
      vec2 nrm = vec2(hxy, l1 - hxx); nrm = dot(nrm, nrm) > 1e-12 ? normalize(nrm) : vec2(0.0, 1.0);
      vec2 dirH = vec2(-nrm.y, nrm.x);
      float gl = length(gr);
      vec2 dirG = gl > 1e-4 ? vec2(-gr.y, gr.x) / gl : dirH; if(dot(dirG, dirH) < 0.0) dirG = -dirG;
      vec2 dir = normalize(mix(dirH, dirG, smoothstep(0.015, 0.05, gl))); vec2 prp = vec2(-dir.y, dir.x);
      float ridge = smoothstep(0.004, 0.02, -l1);
      float sRidge = clamp(-dot(gr, nrm) / min(l1, -1e-4), -5.0, 5.0);   // metres across from the road's centre line
      float sd = (rr - 0.45) / (gl + 0.1);                                // metres from the kerb, positive on the road

      if(aR > 0.003){
      // asphalt
      float veg = clamp(0.05 + 0.6 * n2 + 0.45 * (1.0 - smoothstep(0.55, 1.0, rr)) + 0.5 * (m1 - 0.5), 0.0, 1.0);
      vec3 as0 = mix(vec3(0.215, 0.205, 0.19), vec3(0.36, 0.34, 0.31), vn(xy * 0.4 + 8.0));
      as0 *= 1.0 + 0.16 * dn(xy + 4.0, 7.0) + 0.1 * dn(xy + 2.0, 0.9);
      vec3 vs = vor((xy + (vec2(vn(xy * 0.8 + 5.0), vn(xy * 0.8 + 17.0)) - 0.5) * 0.9) / 2.9);                                           // the slabs
      float edge = (vs.y - vs.x) * 1.45;                                 // ~ metres to the slab's border
      float cw = mix(0.012, 0.11, veg * veg) * (0.5 + vs.z);
      float crack = 1.0 - smoothstep(cw, cw + max(1.1 * FW, 0.012), edge);
      tilt = (h22(vec2(vs.z * 91.0, 3.0)) - 0.5) * 0.09;
      vec3 slab = as0 * (1.0 + 0.2 * (vs.z - 0.5)) * (1.0 + 0.17 * dn(xy, 0.035) + 0.13 * dn(xy + 6.0, 0.11));   // aggregate
      float dmp = smoothstep(0.45, 0.72, vn(xy * 0.23 + 90.0)); slab *= 1.0 - 0.32 * dmp;                          // damp patches
      vec3 gcol = mix(vec3(0.13, 0.26, 0.065), vec3(0.30, 0.34, 0.12), vn(xy * 3.0)) * (0.8 + 0.4 * vn(xy * 17.0));
      float rim = (1.0 - smoothstep(0.0, 0.2 + 0.35 * veg, edge)) * veg;   // moss and grass creep along the slab borders
      slab = mix(slab, vec3(0.1, 0.21, 0.06) * (0.8 + 0.5 * vn(xy * 9.0)), rim * 0.5);
      vec3 as = mix(slab, mix(as0 * 0.35, gcol, 0.2 + 0.8 * veg), crack);
      hgt += -0.035 * crack + 0.008 * (vs.z - 0.5) - 0.004 * rim;
      if(hi && FW < 0.16){
        float rg = abs(vn(xy * 2.1 + vn(xy * 5.0) * 1.2) - 0.5) * 2.0;           // hairline cracks
        float fine = (1.0 - smoothstep(0.035, 0.035 + FW * 4.0, rg)) * (1.0 - smoothstep(0.04, 0.2, FW)) * (0.4 + 0.6 * veg);
        as = mix(as, as * 0.35 + gcol * 0.2 * veg, fine * 0.8); hgt -= 0.01 * fine;
      }
      float gp = smoothstep(0.52, 0.64, vn(xy * 0.55 + 50.0) * 0.7 + vn(xy * 2.9) * 0.3 + veg * 0.3 - 0.46);   // grass breaking through
      as = mix(as, nat * 0.95, gp * (0.4 + 0.6 * veg));
      // lane paint, faded to fragments
      float paint = 0.0;
      if(hi && ridge > 0.05 && FW < 0.6){
        float u = dot(xy, dir) / 7.0;
        float dash = smoothstep(0.0, 0.03, fract(u)) * (1.0 - smoothstep(0.42, 0.45, fract(u)));
        float line = 1.0 - smoothstep(0.07, 0.07 + FW * 1.3 + 0.03, abs(sRidge));
        float wear = smoothstep(0.38, 0.62, vn(vec2(u * 0.9, dot(xy, prp) * 0.5) * 2.3 + 6.0) + 0.3 * vn(xy * 4.0) * fd(0.25));
        paint = dash * line * wear * ridge * (1.0 - gp * 0.8) * (1.0 - crack * 0.5) * smoothstep(0.55, 0.8, rr);
        as = mix(as, vec3(0.52, 0.5, 0.44) * (0.85 + 0.3 * vn(xy * 25.0)), paint * 0.7);
      }
      float pr, pd = scatter(xy + 11.0, 1.1, 0.045, 0.13, 1.5, pr);       // spalled chips, scraps
      as = mix(as, pr < 0.4 ? vec3(0.33, 0.31, 0.28) : (pr < 0.7 ? vec3(0.34, 0.2, 0.13) : vec3(0.5, 0.5, 0.46)), pd * 0.75); hgt += 0.03 * pd;
      float pw = smoothstep(0.66, 0.72, vn(xy * 0.38 + 70.0) * 0.75 + vn(xy * 1.9) * 0.25) * (1.0 - gp) * (1.0 - crack) * 0.9;
      pud = pw;
      as *= 1.0 - 0.45 * pw;
      road = as;
      }

      if(pv > 0.003){
      // pavement of small square tiles, in the road's own direction
      vec2 pq = xy / 0.3; vec2 pc = floor(pq), pf = fract(pq);
      float th = h12(pc), th2 = h12(pc + 7.3);
      float gdist = min(min(pf.x, 1.0 - pf.x), min(pf.y, 1.0 - pf.y));
      float grout = 1.0 - smoothstep(0.035, 0.035 + max(FW / 0.3, 0.03), gdist);
      vec3 tile = mix(vec3(0.40, 0.38, 0.34), vec3(0.58, 0.54, 0.47), th) * (0.88 + 0.24 * vn(xy * 3.5 + 2.0));
      float mossy = smoothstep(0.4, 0.8, vn(xy * 0.5 + 33.0) + 0.5 * (n2 - 0.4)) ;
      tile = mix(tile, vec3(0.12, 0.23, 0.07) * (0.8 + 0.5 * th2), mossy * 0.4 * (0.3 + th2));
      float lost = step(0.945, th2);                                     // a tile gone: earth and weeds
      tile = mix(tile, nat * 0.7, lost);
      vec3 groutC = mix(vec3(0.26, 0.25, 0.22), vec3(0.13, 0.25, 0.07), clamp(0.2 + mossy, 0.0, 1.0) * 0.85) * (0.8 + 0.4 * th2);
      pave = mix(tile, groutC, mix(0.14, grout, 1.0 - smoothstep(0.1, 0.36, FW)) * (1.0 - lost));
      pave *= 1.0 + 0.45 * dn(xy + 8.0, 0.045) * 0.5;
      hgt += -0.012 * grout + 0.006 * (th - 0.5);
      // kerb and the faded yellow tactile strip
      float broken = smoothstep(0.25, 0.5, vn(xy * 0.7 + 3.0));
      kerb = (1.0 - smoothstep(0.075, 0.075 + FW * 1.2 + 0.02, abs(sd))) * broken * (1.0 - 0.6 * mossy);
      tact = (1.0 - smoothstep(0.14, 0.14 + FW * 1.2 + 0.02, abs(sd + 0.75))) * smoothstep(0.45, 0.7, vn(xy * 0.9 + 12.0)) * (1.0 - 0.5 * mossy);
      pave = mix(pave, vec3(0.5, 0.41, 0.14) * (0.75 + 0.35 * vn(xy * 22.0)), tact * 0.7);
      pave = mix(pave, vec3(0.5, 0.48, 0.43), kerb * 0.9);
      hgt += 0.04 * kerb;
      }
    }

    // ---- compose: earth, then pavement, then asphalt
    vec3 c = base;
    float pvw = pv * (1.0 - 0.3 * smoothstep(0.55, 0.75, vn(xy * 0.6 + 60.0)));   // the pavement is eaten by growth in places
    c = mix(c, pave, pvw);
    c = mix(c, road, aR);
    float built = clamp(aR + pvw, 0.0, 1.0);

    // fallen leaves and moss on everything
    if(fd(0.1) > (hi ? 0.02 : 0.3)){
      float lr, ll = scatter(xy, 0.15, 0.045, 0.55 * litter, 2.2, lr);
      vec3 lcol = lr < 0.3 ? vec3(0.27, 0.15, 0.06) : (lr < 0.6 ? vec3(0.34, 0.24, 0.08) : (lr < 0.85 ? vec3(0.19, 0.13, 0.05) : vec3(0.28, 0.29, 0.09)));
      c = mix(c, lcol * (0.8 + 0.4 * vn(xy * 37.0)), ll * 0.85 * (1.0 - 0.4 * built * (1.0 - litter)));
      hgt += 0.006 * ll;
    }
    // far-ish mean of the litter: a brown cast that stays when the leaves are too small to see
    c = mix(c, c * vec3(1.08, 0.96, 0.82), litter * 0.25 * (1.0 - fd(0.15)));
    // rails: ballast
    vec3 ball = mix(vec3(0.27, 0.26, 0.24), vec3(0.4, 0.37, 0.33), vn(xy * 0.8)) * (1.0 + 0.5 * dn(xy, 0.04));
    c = mix(c, mix(ball, nat * 0.8, 0.4 * smoothstep(0.4, 0.7, m1)), rail);
    col = mix(c, col, wat);
  }

  void main(){
    FW = max(max(fwidth(vW.x), fwidth(vW.z)), 1e-4);
    vec2 xy = vec2(vW.x, -vW.z);
    vec2 uv = coverUV(xy);
    vec4 cv = vec4(0.0); if(uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0) cv = texture2D(cover, uv);
    float n1 = fbm(xy * 0.08), n2 = fbm(xy * 0.011 + 3.0), n3 = noise(xy * 0.6);
    // the overgrown ground: summer grass and scrub, dry in patches
    vec3 grass = mix(vec3(0.20, 0.30, 0.10), vec3(0.42, 0.44, 0.18), n2);
    grass = mix(grass, vec3(0.13, 0.22, 0.08), n1 * 0.6);
    vec3 forest = mix(vec3(0.09, 0.17, 0.06), vec3(0.16, 0.25, 0.09), n1);
    vec3 asphalt = mix(vec3(0.21, 0.21, 0.20), vec3(0.30, 0.29, 0.27), n3);
    float cracks = smoothstep(0.45, 0.65, fbm(xy * 0.35 + 11.0));
    vec3 road = mix(asphalt, grass * 0.9, cracks * 0.75 + n2 * 0.2);
    vec3 rail = mix(vec3(0.34, 0.26, 0.19), grass, 0.55 + 0.3 * n1);
    vec3 water = mix(vec3(0.10, 0.17, 0.15), vec3(0.17, 0.26, 0.22), n1);
    vec3 col = mix(grass, forest, smoothstep(0.2, 0.9, cv.g));
    float rr = cv.r + 0.25 * (n3 - 0.5);
    float roadW = smoothstep(0.15, 0.6, rr);           // soft, eaten edges
    col = mix(col, mix(road, asphalt * 0.8, smoothstep(0.65, 1.0, cv.r) * 0.3), roadW);
    col = mix(col, rail, smoothstep(0.3, 0.8, cv.a));
    col = mix(col, water, smoothstep(0.3, 0.7, cv.b));
    // close range: cracked slabs, pavement tiles, litter, moss
    vec3 N = normalize(vN);
    float d = length(vW - camPos);
    float dw = (1.0 - smoothstep(detR * 0.4, detR, d)) * (1.0 - ringScale);
    float hgt = 0.0, pud = 0.0; vec2 tilt = vec2(0.0);
    if(dw > 0.003){
      vec3 cn = col; nearGround(cn, xy, cv, rr, n1, n2, hgt, tilt, pud); col = mix(col, cn, dw); pud *= dw;
    }
    float dhx = dFdx(hgt), dhy = dFdy(hgt);
    // far rings: a greener, hazier blanket
    col = mix(col, mix(vec3(0.18, 0.26, 0.11), vec3(0.3, 0.32, 0.2), n2), ringScale);
    vec3 Ng = N;
    if(dw > 0.003){
      N = normalize(N + vec3(tilt.x, 0.0, tilt.y) * dw);
      if(detQ > 0.5){                                  // bump from the height field (surface-gradient method)
        vec3 dpx = dFdx(vW), dpy = dFdy(vW), r1 = cross(dpy, N), r2 = cross(N, dpx); float det = dot(dpx, r1);
        vec3 gradv = sign(det) * (dhx * r1 + dhy * r2);
        N = normalize(abs(det) * N - 0.7 * dw * gradv);
      }
    }
    float dif = max(dot(N, sunDir), 0.0) * shadowAt(vW, Ng, sunDir);
    vec3 light = sunCol * dif + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9;
    vec3 rgb = col * light;
    float f = 1.0 - exp(-fogDen * d);
    if(pud > 0.004){                                    // standing water on the asphalt mirrors the sky
      vec3 V = normalize(camPos - vW); vec3 R = reflect(-V, vec3(0.0, 1.0, 0.0));
      float fr = 0.04 + 0.96 * pow(1.0 - clamp(V.y, 0.0, 1.0), 5.0);
      vec3 sk = mix(fogCol, skyCol * 1.5, smoothstep(0.0, 0.7, R.y));
      rgb = mix(rgb, sk * vec3(0.30, 0.34, 0.42), clamp(pud * (0.3 + 0.7 * fr), 0.0, 0.75));
    }
    rgb = mix(rgb, fogCol, f);
    gl_FragColor = vec4(rgb, 1.0);
  }`;

const touch = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
const query = typeof location !== 'undefined' ? new URLSearchParams(location.search) : new URLSearchParams();
const lowProfile = query.get('q') === 'low' || (query.get('q') !== 'high' && (touch || query.has('touch')));

// uniforms: the shared light / fog objects plus cover, coverBox and ringScale. `detQ` and `detR` default to the
// phone profile detected from the URL (?q=low / coarse pointer) and may be overridden in the passed uniforms.
export function makeTerrainMaterial(uniforms) {
  uniforms = { detQ: { value: lowProfile ? 0 : 1 }, detR: { value: lowProfile ? 80 : 130 }, ...uniforms };
  // cover.png row 0 is north. With flipY off, WebGL puts row 0 at v = 0, which is the SOUTH edge of coverBox, so a
  // texture that still has flipY = false would be mirrored north-south: undo that in the shader (flipY = true needs no fix).
  const defines = uniforms.cover?.value?.flipY === false ? { COVER_FLIP: 1 } : {};
  return new THREE.ShaderMaterial({ uniforms, defines, vertexShader: vert, fragmentShader: frag });
}

function ringGeometry(r, hole) {
  const nx = r.nx, ny = r.ny, pos = new Float32Array(nx * ny * 3), nor = new Float32Array(nx * ny * 3);
  const H = (c, w) => r.h[Math.min(ny - 1, Math.max(0, w)) * nx + Math.min(nx - 1, Math.max(0, c))];
  let k = 0;
  for (let w = 0; w < ny; w++) for (let c = 0; c < nx; c++, k++) {
    const x = r.x0 + c * r.s, y = r.y0 + w * r.s, z = r.h[w * nx + c];
    pos[k * 3] = x; pos[k * 3 + 1] = z; pos[k * 3 + 2] = -y;
    const dx = (H(c + 1, w) - H(c - 1, w)) / (2 * r.s), dy = (H(c, w + 1) - H(c, w - 1)) / (2 * r.s), l = Math.hypot(dx, 1, dy);
    nor[k * 3] = -dx / l; nor[k * 3 + 1] = 1 / l; nor[k * 3 + 2] = dy / l;
  }
  const idx = [];
  for (let w = 0; w < ny - 1; w++) for (let c = 0; c < nx - 1; c++) {
    if (hole) { const x = r.x0 + c * r.s, y = r.y0 + w * r.s; if (x >= hole[0] && x + r.s <= hole[2] && y >= hole[1] && y + r.s <= hole[3]) continue; }
    const a = w * nx + c, b = a + 1, cc = a + nx, d = cc + 1; idx.push(a, b, cc, b, d, cc);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setIndex(new THREE.Uint32BufferAttribute(idx, 1)); g.computeBoundingSphere();
  return g;
}

export function buildTerrain(rings, material) {
  const group = new THREE.Group();
  let hole = null;
  rings.forEach((r, i) => {
    const m = new THREE.ShaderMaterial({ uniforms: { ...material.uniforms, ringScale: { value: i === 0 ? 0 : i === 1 ? 0.6 : 1 } }, defines: material.defines, vertexShader: vert, fragmentShader: frag });
    const mesh = new THREE.Mesh(ringGeometry(r, hole), m); mesh.frustumCulled = false; mesh.renderOrder = -10 + i;
    group.add(mesh);
    hole = [r.x0, r.y0, r.x0 + (r.nx - 1) * r.s, r.y0 + (r.ny - 1) * r.s];
  });
  return group;
}
