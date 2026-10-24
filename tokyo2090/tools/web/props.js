// Props of the ruined city: abandoned cars along the old roads and the overgrown trees (parks, street trees, wild
// growth, trees rooted on flat roofs). Everything is placed once at load from a seeded PRNG and drawn as two
// InstancedMeshes with the same lighting and fog as terrain.js. Data axes: x east, y north, z up; three.js = (x, z, -y).

export const FRAME = { x0: -2400, x1: 4600, y0: -2000, y1: 4400 };
const CAR_CAP = 40000, TREE_CAP = 220000, PARK_CAP = 25000;
const CAR_L = 4.2, CAR_H = 1.45, FLIP_LIFT = 1.35;      // overturned cars rest on the cabin roof (spec said 0.6; see report)

// ---------------------------------------------------------------------------------------------------- random
export function mulberry32(a) {
  return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const inFrame = (x, y) => x >= FRAME.x0 && x < FRAME.x1 && y >= FRAME.y0 && y < FRAME.y1;
const pick = (rng, table) => { let s = rng() * table.reduce((a, e) => a + e[0], 0); for (const e of table) { s -= e[0]; if (s <= 0) return e[1]; } return table[0][1]; };

// roads worth driving or planting along: surface roads only (no bridges, tunnels or motorway ramps)
const surface = (r) => !r.bridge && r.layer >= 0 && r.hw !== 'motorway_link';

// ---------------------------------------------------------------------------------------------------- cars
// faded paint colours (linear albedo): [weight, [r, g, b]]
const PAINT = [[26, [0.55, 0.55, 0.52]], [22, [0.40, 0.41, 0.42]], [20, [0.07, 0.07, 0.075]], [16, [0.22, 0.22, 0.22]],
  [5, [0.36, 0.12, 0.09]], [5, [0.14, 0.19, 0.31]], [3, [0.40, 0.34, 0.20]], [3, [0.15, 0.26, 0.20]]];
const BUS_PAINT = [[3, [0.50, 0.50, 0.44]], [2, [0.20, 0.30, 0.22]], [2, [0.40, 0.18, 0.12]], [1, [0.45, 0.40, 0.18]]];

// Records of 11 numbers: x, y, z, heading, pitch, overturned, bus, r, g, b, (spare). Heading is the data-axes angle of the car's nose.
export const CAR_STRIDE = 11;
export function planCars(roads, ground, roof, seed = 2090) {
  const rng = mulberry32(seed), out = [];
  for (const rd of roads) {
    if (!surface(rd)) continue;
    const p = rd.xy, lanes = rd.w >= 6;
    let next = 6 + rng() * 16;                            // distance along the line to the next car
    for (let i = 0, run = 0; i < p.length - 1; i++) {
      const dx = p[i + 1][0] - p[i][0], dy = p[i + 1][1] - p[i][1], len = Math.hypot(dx, dy);
      if (len < 1e-6) continue;
      const ux = dx / len, uy = dy / len;
      while (run + len >= next) {
        const s = next - run;
        next += 6 + rng() * 16;
        // one car per step on a random lane; traffic keeps left (Japan): left lane drives forward, right lane back
        const side = lanes ? (rng() < 0.5 ? 1 : -1) : 0, off = side * rd.w / 4;
        const x = p[i][0] + ux * s - uy * off, y = p[i][1] + uy * s + ux * off;
        const r = rng(), a1 = rng(), a2 = rng(), flip = rng(), pa = rng(), pb = rng();   // fixed draw count keeps layouts stable
        if (!inFrame(x, y)) continue;
        let h = Math.atan2(uy, ux) + (side < 0 ? Math.PI : 0);
        if (a1 < 0.12) h += (a2 * 2 - 1) * 35 * Math.PI / 180;           // parked askew
        const bus = lanes && r < 0.05, hl = (bus ? 11 : CAR_L) * 0.4, c = Math.cos(h), sn = Math.sin(h);
        const g = ground(x, y), gf = ground(x + c * hl, y + sn * hl), gb = ground(x - c * hl, y - sn * hl);
        // skip anything under (or poking into) a building
        if (roof.top(x, y) > g + 1 || roof.top(x + c * hl, y + sn * hl) > gf + 1 || roof.top(x - c * hl, y - sn * hl) > gb + 1) continue;
        const flipped = !bus && flip < 0.03;
        const col = pick(rng, bus ? BUS_PAINT : PAINT), k = 0.85 + 0.3 * pa, t = 0.04 * (pb - 0.5);
        out.push(x, y, g - 0.12 + (flipped ? FLIP_LIFT : 0), h, Math.atan2(gf - gb, hl * 2), flipped ? 1 : 0, bus ? 1 : 0,
          col[0] * k + t, col[1] * k + t, col[2] * k + t, 0);
      }
      run += len;                                    // next is absolute along the whole line; run follows it
    }
  }
  // over the cap: drop cars uniformly at random (seeded) rather than truncating the last roads
  const n = out.length / CAR_STRIDE;
  if (n <= CAR_CAP) return Float32Array.from(out);
  const keep = [], r2 = mulberry32(seed + 1), pk = Math.min(1, CAR_CAP / n * 1.02);
  for (let i = 0; i < n; i++) if (r2() < pk) for (let j = 0; j < CAR_STRIDE; j++) keep.push(out[i * CAR_STRIDE + j]);
  return Float32Array.from(keep.slice(0, CAR_CAP * CAR_STRIDE));
}

// ---------------------------------------------------------------------------------------------------- trees
// Records of 8 numbers: x, y, z, scale, yaw, r, g, b.
export const TREE_STRIDE = 8;
const GREEN_DARK = [0.08, 0.16, 0.05], GREEN_YEL = [0.22, 0.30, 0.10], REDDISH = [0.35, 0.22, 0.08];
function treeColour(rng) {
  const t = rng(), k = 0.88 + 0.24 * rng(), red = rng() < 0.06 ? 0.4 + 0.6 * rng() : 0;
  return [0, 1, 2].map((i) => (GREEN_DARK[i] + (GREEN_YEL[i] - GREEN_DARK[i]) * t * t * (3 - 2 * t)) * (1 - red) * k + REDDISH[i] * red * k);
}

// polygon with a y-bucketed edge list so even-odd tests stay fast on rings with thousands of vertices
export function makePolygon(ring) {
  const B = 8, edges = new Map();
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, area = 0;
  for (let i = 0; i < ring.length; i++) {
    const [ax, ay] = ring[i], [bx, by] = ring[(i + 1) % ring.length];
    x0 = Math.min(x0, ax); x1 = Math.max(x1, ax); y0 = Math.min(y0, ay); y1 = Math.max(y1, ay); area += ax * by - bx * ay;
    for (let b = Math.floor(Math.min(ay, by) / B); b <= Math.floor(Math.max(ay, by) / B); b++) {
      if (!edges.has(b)) edges.set(b, []);
      edges.get(b).push(ax, ay, bx, by);
    }
  }
  const contains = (x, y) => {
    const e = edges.get(Math.floor(y / B)); if (!e) return false;
    let inside = false;
    for (let i = 0; i < e.length; i += 4) {
      const ax = e[i], ay = e[i + 1], bx = e[i + 2], by = e[i + 3];
      if ((ay > y) !== (by > y) && x < ax + (y - ay) * (bx - ax) / (by - ay)) inside = !inside;
    }
    return inside;
  };
  return { x0, y0, x1, y1, area: Math.abs(area) / 2, contains };
}

export function planTrees(green, roads, ground, roof, seed = 7) {
  const rng = mulberry32(seed);
  const rec = (x, y, z, s, col) => [x, y, z, s, rng() * Math.PI * 2, col[0], col[1], col[2]];
  const free = (x, y) => inFrame(x, y) && roof.top(x, y) === -Infinity;      // in the frame and not inside a building
  const counts = { parks: 0, osm: 0, street: 0, wild: 0, roof: 0 };
  const solid = [], parks = [];                                                // solid: never thinned; parks: thinned to fit the cap

  // (a) parks: one jittered-grid point per 55 m2 cell (blue-noise-like), kept inside the polygon
  const CELL = Math.sqrt(55);
  for (const park of green.parks) {
    const poly = makePolygon(park.xy);
    if (poly.area < 30) continue;
    const keepP = Math.min(1, PARK_CAP / (poly.area / 55));                    // thin huge polygons to the per-polygon cap
    for (let cy = poly.y0; cy < poly.y1; cy += CELL) for (let cx = poly.x0; cx < poly.x1; cx += CELL) {
      const x = cx + rng() * CELL, y = cy + rng() * CELL, k = rng();
      if (k > keepP || !poly.contains(x, y) || !free(x, y)) continue;
      parks.push(...rec(x, y, ground(x, y), 0.6 + rng(), treeColour(rng))); counts.parks++;
    }
  }
  // (b) every OSM tree
  for (const [x, y] of green.trees) if (free(x, y)) { solid.push(...rec(x, y, ground(x, y), 0.6 + rng(), treeColour(rng))); counts.osm++; }
  // (c) street trees on both sides of the wide roads
  for (const rd of roads) {
    if (rd.w < 8 || !surface(rd)) continue;
    const p = rd.xy;
    let next = 11 + rng() * 5;
    for (let i = 0, run = 0; i < p.length - 1; i++) {
      const dx = p[i + 1][0] - p[i][0], dy = p[i + 1][1] - p[i][1], len = Math.hypot(dx, dy);
      if (len < 1e-6) continue;
      const ux = dx / len, uy = dy / len;
      while (run + len >= next) {
        const s = next - run; next += 11 + rng() * 5;
        for (const side of [1, -1]) {
          const off = side * (rd.w / 2 + 1.5), x = p[i][0] + ux * s - uy * off, y = p[i][1] + uy * s + ux * off, keep = rng() < 0.55;
          if (keep && free(x, y)) { solid.push(...rec(x, y, ground(x, y), 0.6 + rng(), treeColour(rng))); counts.street++; }
        }
      }
      run += len;
    }
  }
  // (d) wild growth over the whole frame, wherever there is no building
  const W = FRAME.x1 - FRAME.x0, H = FRAME.y1 - FRAME.y0;
  for (let n = Math.round(W * H / 1800); n > 0; n--) {
    const x = FRAME.x0 + rng() * W, y = FRAME.y0 + rng() * H;
    if (roof.top(x, y) === -Infinity) { solid.push(...rec(x, y, ground(x, y), 0.6 + rng(), treeColour(rng))); counts.wild++; }
  }
  // (e) trees rooted on the buildings, Ta Prohm style: on flat roofs, on the broken tops (which are jagged, so the
  // level test is loose) and, biggest of all, on the edges where their roots can reach the walls
  for (let n = Math.round(W * H / 260); n > 0; n--) {
    const x = FRAME.x0 + rng() * W, y = FRAME.y0 + rng() * H, t = roof.top(x, y);
    if (!(t > ground(x, y) + 4)) continue;
    const nb = [[3, 0], [-3, 0], [0, 3], [0, -3]].map(([ox, oy]) => roof.top(x + ox, y + oy));
    const level = nb.every((v) => Math.abs(v - t) <= 2.0), edge = nb.some((v) => v < t - 6);
    if ((level || edge) && Math.hypot(x - 116, y + 112) > 16) {        // not on the player's own ledge
      const big = edge && rng() < 0.5;
      solid.push(...rec(x, y, t - (edge ? 0.4 : 0), big ? 1.0 + 0.7 * rng() : 0.5 + 0.6 * rng(), treeColour(rng))); counts.roof++;
    }
  }
  // total cap: thin the parks first (the biggest group) so the rarer kinds always survive
  const nSolid = solid.length / TREE_STRIDE, nPark = parks.length / TREE_STRIDE;
  let out = solid;
  if (nSolid + nPark <= TREE_CAP) out = solid.concat(parks);
  else {
    const pk = Math.max(0, TREE_CAP - nSolid) / nPark, r2 = mulberry32(seed + 1);
    for (let i = 0; i < nPark; i++) if (r2() < pk) for (let j = 0; j < TREE_STRIDE; j++) out.push(parks[i * TREE_STRIDE + j]);
    counts.parks = Math.round(counts.parks * pk);
  }
  return { data: Float32Array.from(out.slice(0, TREE_CAP * TREE_STRIDE)), counts };
}

// ---------------------------------------------------------------------------------------------------- geometry
// A small non-indexed mesh builder with flat normals. Parts: 0 paint, 1 glass, 2 tyre/dark (cars); shade (trees).
function builder(THREE) {
  const pos = [], nor = [], att = [];
  const tri = (a, b, c, v) => {
    const u = new THREE.Vector3().subVectors(b, a), w = new THREE.Vector3().subVectors(c, a), n = u.cross(w).normalize();
    for (const q of [a, b, c]) { pos.push(q.x, q.y, q.z); nor.push(n.x, n.y, n.z); att.push(v); }
  };
  const geometry = (name) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute(name, new THREE.Float32BufferAttribute(att, 1)); return g;
  };
  return { tri, geometry };
}

// One low-poly car (38 triangles): body, tapered cabin with glass sides, four hexagonal wheels. Nose is +x, origin at the tyres' base.
export function carGeometry(THREE) {
  const V = (x, y, z) => new THREE.Vector3(x, y, z), b = builder(THREE);
  // a box whose top ring may differ from the bottom ring; faces are wound outward by checking against the centre
  const solid = (bot, top, parts, skipBottom) => {
    const v = [...bot, ...top], c = v.reduce((s, p) => s.add(p), V(0, 0, 0)).multiplyScalar(1 / 8);
    const quad = (i, j, k, l, part) => {
      const n = new THREE.Vector3().subVectors(v[j], v[i]).cross(new THREE.Vector3().subVectors(v[k], v[i]));
      const o = n.dot(new THREE.Vector3().subVectors(v[i], c)) >= 0;
      if (o) { b.tri(v[i], v[j], v[k], part); b.tri(v[i], v[k], v[l], part); } else { b.tri(v[i], v[k], v[j], part); b.tri(v[i], v[l], v[k], part); }
    };
    if (!skipBottom) quad(0, 1, 2, 3, parts.bottom);
    quad(4, 5, 6, 7, parts.top);
    quad(0, 1, 5, 4, parts.side); quad(1, 2, 6, 5, parts.side); quad(2, 3, 7, 6, parts.side); quad(3, 0, 4, 7, parts.side);
  };
  const ring = (x0, x1, z0, z1, xt0, xt1, zt0, zt1, y0, y1) =>
    [[V(x0, y0, z0), V(x1, y0, z0), V(x1, y0, z1), V(x0, y0, z1)], [V(xt0, y1, zt0), V(xt1, y1, zt0), V(xt1, y1, zt1), V(xt0, y1, zt1)]];
  const body = ring(-2.1, 2.1, -0.875, 0.875, -2.1, 2.1, -0.875, 0.875, 0.28, 0.92);
  solid(body[0], body[1], { bottom: 2, top: 0, side: 0 }, false);
  const cab = ring(-1.3, 0.95, -0.8, 0.8, -1.0, 0.35, -0.7, 0.7, 0.92, CAR_H);
  solid(cab[0], cab[1], { bottom: 0, top: 0, side: 1 }, true);
  // wheels: hexagons on both flanks, standing just proud of the body so they show
  for (const sz of [1, -1]) for (const wx of [-1.3, 1.3]) {
    const r = 0.33, z = sz * 0.885, ring6 = [0, 1, 2, 3, 4, 5].map((k) => V(wx + Math.cos(k * Math.PI / 3) * r, r + Math.sin(k * Math.PI / 3) * r, z));
    const f = sz > 0 ? [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]] : [[0, 2, 1], [0, 3, 2], [0, 4, 3], [0, 5, 4]];
    for (const t of f) b.tri(ring6[t[0]], ring6[t[1]], ring6[t[2]], 2);
  }
  return b.geometry('aPart');
}

// Trees come in two levels of detail with the same silhouette and the same attributes. aShade < 0 marks bark; otherwise it is the lump's brightness.
function addTrunk(b, THREE, sides, r0, r1) {
  const V = (g, i) => new THREE.Vector3(g.attributes.position.getX(i), g.attributes.position.getY(i), g.attributes.position.getZ(i));
  const g = new THREE.CylinderGeometry(r1, r0, 4.4, sides, 1, true).translate(0, 2.2, 0), ix = g.index.array;   // open frustum, base radius r0
  for (let i = 0; i < ix.length; i += 3) b.tri(V(g, ix[i]), V(g, ix[i + 1]), V(g, ix[i + 2]), -1);
}

// Full tree (92 triangles): six-sided trunk (0.35 m at the base) and four jittered icosahedron lumps (detail 0).
export function treeGeometry(THREE, seed = 11) {
  const b = builder(THREE), V = (x, y, z) => new THREE.Vector3(x, y, z), rng = mulberry32(seed);
  addTrunk(b, THREE, 6, 0.35, 0.2);
  // canopy lumps: centre, radius
  const lumps = [[0, 6.3, 0, 3.7], [2.0, 5.5, 1.0, 2.8], [-1.8, 7.1, -1.1, 2.8], [0.4, 7.7, 1.6, 2.3]];
  for (const [cx, cy, cz, r] of lumps) {
    const ip = new THREE.IcosahedronGeometry(1, 0).attributes.position, shade = 0.85 + 0.25 * rng(), salt = rng() * 100, P = [];
    // jitter radially by a hash of the vertex position so shared corners move together (no cracks)
    for (let i = 0; i < ip.count; i++) {
      const x = ip.getX(i), y = ip.getY(i), z = ip.getZ(i);
      const h = Math.abs(Math.sin((Math.round(x * 997) * 12.9898 + Math.round(y * 997) * 78.233 + Math.round(z * 997) * 37.719 + salt) * 43758.5453)) % 1;
      const k = r * (0.8 + 0.4 * h);
      P.push(V(cx + x * k, cy + y * k * 0.8, cz + z * k));
    }
    for (let i = 0; i < P.length; i += 3) b.tri(P[i], P[i + 1], P[i + 2], shade);
  }
  return b.geometry('aShade');
}

// Far tree (20 triangles): four-sided trunk and a six-sided double cone for the crown, covering the same volume.
export function farTreeGeometry(THREE) {
  const b = builder(THREE), V = (x, y, z) => new THREE.Vector3(x, y, z);
  addTrunk(b, THREE, 4, 0.4, 0.25);
  const top = V(0, 9.8, 0), bot = V(0, 4.8, 0), ring = [0, 1, 2, 3, 4, 5].map((k) => V(Math.cos(k * Math.PI / 3) * 4.2, 6.6, Math.sin(k * Math.PI / 3) * 4.2));
  for (let k = 0; k < 6; k++) { const p = ring[k], q = ring[(k + 1) % 6]; b.tri(top, q, p, 1); b.tri(bot, p, q, 1); }
  return b.geometry('aShade');
}

// level of detail by distance: 0 full tree, 1 far tree, -1 hidden (distance d to the chunk centre, radius r of its bounding sphere)
export const LOD = { fullTrees: 900, hideTrees: 2600, hideCars: 1500 };   // main.js lowers these on phones
export const treeLod = (d, r) => (d - r > LOD.hideTrees ? -1 : d < LOD.fullTrees ? 0 : 1);

// group record indices by 500 m cell of the data frame: Map cellKey -> [record index, ...]
export const CHUNK = 500;
export function chunkRecords(data, stride) {
  const cells = new Map(), nx = Math.ceil((FRAME.x1 - FRAME.x0) / CHUNK);
  for (let i = 0; i < data.length / stride; i++) {
    const key = Math.floor((data[i * stride + 1] - FRAME.y0) / CHUNK) * nx + Math.floor((data[i * stride] - FRAME.x0) / CHUNK);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(i);
  }
  return cells;
}

// ---------------------------------------------------------------------------------------------------- shaders
// shared: noise, then lighting and fog exactly as terrain.js
const vary = /* glsl */`
  varying vec3 vW; varying vec3 vN; varying vec3 vCol;
  float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }`;
const common = /* glsl */`
  ${vary}
  uniform vec3 sunDir; uniform vec3 sunCol; uniform vec3 skyCol; uniform vec3 groundCol;
  uniform vec3 fogCol; uniform float fogDen; uniform vec3 camPos;
  float noise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float v = 0.0, a = 0.5; for(int k=0;k<3;k++){ v += a*noise(p); p = p*2.03 + 7.1; a *= 0.5; } return v; }
  vec3 shade(vec3 col, vec3 N){
    float dif = max(dot(N, sunDir), 0.0);
    vec3 light = sunCol * dif + mix(groundCol, skyCol, N.y * 0.5 + 0.5) * 0.9;
    vec3 rgb = col * light;
    float d = length(vW - camPos); float f = 1.0 - exp(-fogDen * d);
    return mix(rgb, fogCol, f);
  }`;
// (instanceMatrix and instanceColor are declared by three for ShaderMaterial on an InstancedMesh, so they are not redeclared here)

const carVert = /* glsl */`
  ${vary}
  attribute float aPart; varying float vPart; varying float vRust;
  void main(){
    mat4 M = modelMatrix * instanceMatrix;
    vec4 w = M * vec4(position, 1.0);
    // inverse-transpose normal for a rotation times a (bus) stretch
    vec3 s2 = vec3(dot(M[0].xyz, M[0].xyz), dot(M[1].xyz, M[1].xyz), dot(M[2].xyz, M[2].xyz));
    vW = w.xyz; vN = normalize(mat3(M) * (normal / s2)); vCol = instanceColor; vPart = aPart;
    vRust = 0.2 + 0.4 * hash(M[3].xz * 0.37);      // how much of this car has rusted (0.2-0.6 of its surface)
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const carFrag = /* glsl */`
  precision highp float; varying float vPart; varying float vRust;
  ${common}
  void main(){
    vec3 N = normalize(vN), col;
    if(vPart > 1.5) col = vec3(0.035);                                                     // tyres, underside
    else if(vPart > 0.5) col = mix(vec3(0.035, 0.045, 0.05), vec3(0.10, 0.12, 0.12), noise(vW.xz * 3.0));   // dull, grimy glass
    else {
      col = vCol;
      // rust blooms from noise in world space; the threshold follows the car's own rust amount
      float t = mix(0.53, 0.41, (vRust - 0.2) / 0.4);
      float rust = smoothstep(t - 0.07, t + 0.07, fbm(vW.xz * 0.9 + vW.y * 2.3));
      col = mix(col, mix(vec3(0.27, 0.12, 0.06), vec3(0.46, 0.25, 0.11), noise(vW.xz * 7.0 + vW.y * 5.0)), rust * 0.85);
      // dust and moss settle on upward faces
      col = mix(col, vec3(0.20, 0.27, 0.10), smoothstep(0.6, 0.95, N.y) * 0.45 * noise(vW.xz * 1.3));
    }
    gl_FragColor = vec4(shade(col, N), 1.0);
  }`;

const treeVert = /* glsl */`
  ${vary}
  attribute float aShade; uniform float time; varying float vShade; varying float vLy;
  void main(){
    mat4 M = modelMatrix * instanceMatrix;
    vec4 w = M * vec4(position, 1.0);
    // sway: the canopy (local y > 2.5) leans in a slow wave travelling across the city; the weight ramps up from the trunk
    float s = length(M[0].xyz), wgt = smoothstep(2.5, 6.5, position.y), ph = time * 1.3 + w.x * 0.3;
    w.x += sin(ph) * 0.15 * s * wgt; w.z += sin(ph * 0.8 + 1.7) * 0.1 * s * wgt;
    vW = w.xyz; vN = normalize(mat3(M) * normal); vCol = instanceColor; vShade = aShade; vLy = position.y;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;
const treeFrag = /* glsl */`
  precision highp float; varying float vShade; varying float vLy;
  ${common}
  void main(){
    vec3 N = normalize(vN), col;
    if(vShade < 0.0) col = vec3(0.19, 0.14, 0.10) * (0.8 + 0.4 * noise(vW.xz * 4.0 + vW.y * 2.0));   // bark
    else {
      // leaf clumps: darker low inside the crown, speckled by world-space noise
      float g = 0.62 + 0.55 * smoothstep(3.5, 10.0, vLy);
      col = vCol * vShade * g * (0.82 + 0.36 * noise(vW.xz * 2.1 + vW.y * 1.7));
    }
    gl_FragColor = vec4(shade(col, N), 1.0);
  }`;

// ---------------------------------------------------------------------------------------------------- build
// One InstancedMesh for the records `idx` (matrices written by fill), with a bounding sphere so it can be frustum culled.
// pos(i) gives the three.js position of record i; the sphere covers every instance plus 20 m (tree crowns, bus length).
function chunkMesh(THREE, geo, material, data, stride, idx, pos, fill) {
  const n = idx.length, mesh = new THREE.InstancedMesh(geo, material, n), m = mesh.instanceMatrix.array, c = new Float32Array(n * 3);
  const lo = new THREE.Vector3(Infinity, Infinity, Infinity), hi = new THREE.Vector3(-Infinity, -Infinity, -Infinity), v = new THREE.Vector3();
  idx.forEach((r, k) => { fill(data, r * stride, m, c, k); pos(data, r * stride, v); lo.min(v); hi.max(v); });
  const centre = lo.clone().add(hi).multiplyScalar(0.5);
  let rad = 0; for (const r of idx) { pos(data, r * stride, v); rad = Math.max(rad, v.distanceTo(centre)); }
  mesh.instanceColor = new THREE.InstancedBufferAttribute(c, 3);
  mesh.instanceMatrix.needsUpdate = true; mesh.matrixAutoUpdate = false;
  mesh.boundingSphere = new THREE.Sphere(centre, rad + 20); mesh.frustumCulled = true;
  return mesh;
}

export async function loadProps(scene, ctx) {
  const { ground, roof, shared, THREE } = ctx;
  const [roads, green] = await Promise.all([fetch('data/roads.json').then((r) => r.json()), fetch('data/green.json').then((r) => r.json())]);
  const uniforms = { ...shared, time: { value: 0 } };            // same uniform objects as the city, plus our own clock
  const carMat = new THREE.ShaderMaterial({ uniforms, vertexShader: carVert, fragmentShader: carFrag });
  const treeMat = new THREE.ShaderMaterial({ uniforms, vertexShader: treeVert, fragmentShader: treeFrag });

  // cars: instance matrix = T * Ry(heading) * Rz(pitch) * Rx(roll) * S, composed through a quaternion ('YZX' Euler order)
  const cd = planCars(roads, ground, roof), nCars = cd.length / CAR_STRIDE;
  const pos = new THREE.Vector3(), quat = new THREE.Quaternion(), scl = new THREE.Vector3(), eul = new THREE.Euler(0, 0, 0, 'YZX'), mat = new THREE.Matrix4();
  const carGeo = carGeometry(THREE), carsGroup = new THREE.Group(); carsGroup.name = 'abandonedCars';
  const carChunks = [];
  for (const idx of chunkRecords(cd, CAR_STRIDE).values()) {
    const mesh = chunkMesh(THREE, carGeo, carMat, cd, CAR_STRIDE, idx, (d, o, v) => v.set(d[o], d[o + 2], -d[o + 1]), (d, o, m, c, k) => {
      pos.set(d[o], d[o + 2], -d[o + 1]);
      eul.set(d[o + 5] > 0.5 ? Math.PI : 0, d[o + 3], d[o + 4]);       // data heading h is a yaw of h about +y; pitch lifts the nose (+x)
      quat.setFromEuler(eul); d[o + 6] > 0.5 ? scl.set(11 / CAR_L, 3.2 / CAR_H, 2.5 / 1.75) : scl.set(1, 1, 1);
      mat.compose(pos, quat, scl).toArray(m, k * 16);
      c[k * 3] = d[o + 7]; c[k * 3 + 1] = d[o + 8]; c[k * 3 + 2] = d[o + 9];
    });
    mesh.name = 'carChunk'; carsGroup.add(mesh); carChunks.push(mesh);
  }
  scene.add(carsGroup);

  // trees: uniform scale and a yaw, so the matrix is written directly. Each chunk has a full and a far mesh sharing one set of instance attributes.
  const { data: td, counts: treeCounts } = planTrees(green, roads, ground, roof), nTrees = td.length / TREE_STRIDE;
  const fullGeo = treeGeometry(THREE), farGeo = farTreeGeometry(THREE), treesGroup = new THREE.Group(); treesGroup.name = 'overgrownTrees';
  const treeChunks = [];
  for (const idx of chunkRecords(td, TREE_STRIDE).values()) {
    const full = chunkMesh(THREE, fullGeo, treeMat, td, TREE_STRIDE, idx, (d, o, v) => v.set(d[o], d[o + 2], -d[o + 1]), (d, o, m, c, k) => {
      const s = d[o + 3], cs = Math.cos(d[o + 4]) * s, sn = Math.sin(d[o + 4]) * s, q = k * 16;
      m[q] = cs; m[q + 2] = -sn; m[q + 5] = s; m[q + 8] = sn; m[q + 10] = cs; m[q + 12] = d[o]; m[q + 13] = d[o + 2]; m[q + 14] = -d[o + 1]; m[q + 15] = 1;
      c[k * 3] = d[o + 5]; c[k * 3 + 1] = d[o + 6]; c[k * 3 + 2] = d[o + 7];
    });
    const far = new THREE.InstancedMesh(farGeo, treeMat, idx.length);
    far.instanceMatrix = full.instanceMatrix; far.instanceColor = full.instanceColor;       // same attribute objects: uploaded once
    far.boundingSphere = full.boundingSphere; far.frustumCulled = true; far.matrixAutoUpdate = false;
    full.name = 'treeChunkFull'; far.name = 'treeChunkFar'; treesGroup.add(full, far); treeChunks.push({ full, far, sphere: full.boundingSphere });
  }
  scene.add(treesGroup);

  // per frame: the clock, then hide chunks by distance and pick each tree chunk's level of detail from the camera (three.js world coordinates)
  const update = (t, cam) => {
    uniforms.time.value = t;
    if (!cam) return;
    for (const m of carChunks) m.visible = m.boundingSphere.center.distanceTo(cam) - m.boundingSphere.radius <= LOD.hideCars;
    for (const c of treeChunks) {
      const lod = treeLod(c.sphere.center.distanceTo(cam), c.sphere.radius);
      c.full.visible = lod === 0; c.far.visible = lod === 1;
    }
  };
  for (const m of carsGroup.children.concat(treesGroup.children)) m.visible = false;       // hidden until the first update() knows where the camera is
  return { update, trees: treesGroup, cars: carsGroup, counts: { cars: nCars, trees: nTrees, carChunks: carChunks.length, treeChunks: treeChunks.length, ...treeCounts } };
}
