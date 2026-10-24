// Run: node props.test.mjs  — plans cars and trees from the real data files and checks the counts and invariants.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { loadTerrain, terrainSampler, loadRoof } from './web/data.js';
import { planCars, planTrees, carGeometry, treeGeometry, farTreeGeometry, chunkRecords, treeLod, LOD, makePolygon, CAR_STRIDE, TREE_STRIDE, FRAME } from './web/props.js';

const pub = path.join(path.dirname(fileURLToPath(import.meta.url)), '../public/');
globalThis.fetch = async (u) => new Response(fs.readFileSync(pub + u));   // data.js fetches relative URLs
const ok = (c, m) => { if (!c) { console.error('FAIL', m); process.exitCode = 1; } else console.log('ok  ', m); };

const ground = terrainSampler(await loadTerrain('data/terrain.bin')), roof = await loadRoof('data/roof.bin');
const roads = JSON.parse(fs.readFileSync(pub + 'data/roads.json')), green = JSON.parse(fs.readFileSync(pub + 'data/green.json'));

let t = Date.now();
const cars = planCars(roads, ground, roof), nc = cars.length / CAR_STRIDE;
console.log("cars", nc, "buses", cars.filter((_, i) => i % CAR_STRIDE === 6).reduce((a, b) => a + b, 0), "overturned", cars.filter((_, i) => i % CAR_STRIDE === 5).reduce((a, b) => a + b, 0), Date.now() - t, "ms");
ok(nc > 1000 && nc <= 40000, 'car count within cap');
ok(planCars(roads, ground, roof).every((v, i) => v === cars[i]), 'car layout is deterministic');
let bad = 0;
for (let i = 0; i < nc; i++) { const o = i * CAR_STRIDE; if (roof.top(cars[o], cars[o + 1]) > ground(cars[o], cars[o + 1]) + 1) bad++; if (cars[o] < FRAME.x0 || cars[o] >= FRAME.x1) bad++; }
ok(bad === 0, 'no car under a building or outside the frame');

t = Date.now();
const { data, counts } = planTrees(green, roads, ground, roof), nt = data.length / TREE_STRIDE;
console.log('trees', nt, counts, Date.now() - t, 'ms');
ok(nt > 1000 && nt <= 220000, 'tree count within cap');
ok(planTrees(green, roads, ground, roof).data.every((v, i) => v === data[i]), 'tree layout is deterministic');

const sq = makePolygon([[0, 0], [10, 0], [10, 10], [0, 10]]);
ok(sq.contains(5, 5) && !sq.contains(15, 5) && !sq.contains(5, -1) && sq.area === 100, 'polygon even-odd test');

const tris = (g) => g.attributes.position.count / 3;
const full = tris(treeGeometry(THREE)), far = tris(farTreeGeometry(THREE));
console.log('triangles: car', tris(carGeometry(THREE)), 'tree full', full, 'tree far', far);
ok(tris(carGeometry(THREE)) >= 30 && tris(carGeometry(THREE)) <= 60, 'car triangle budget');
ok(full <= 120 && far <= 24, 'tree LOD triangle budgets (full <= 120, far <= 24)');
// every car face normal should point away from the car's centre
const g = carGeometry(THREE), p = g.attributes.position, n = g.attributes.normal; let inward = 0;
for (let i = 0; i < p.count; i += 3) { const cx = (p.getX(i) + p.getX(i + 1) + p.getX(i + 2)) / 3, cy = (p.getY(i) + p.getY(i + 1) + p.getY(i + 2)) / 3 - 0.8, cz = (p.getZ(i) + p.getZ(i + 1) + p.getZ(i + 2)) / 3;
  if (cx * n.getX(i) + cy * n.getY(i) + cz * n.getZ(i) < 0) inward++; }
ok(inward === 0, 'car normals point outward');

// chunks: every record lands in exactly one 500 m cell
const tc = chunkRecords(data, TREE_STRIDE), cc = chunkRecords(cars, CAR_STRIDE);
ok([...tc.values()].reduce((a, v) => a + v.length, 0) === nt && [...cc.values()].reduce((a, v) => a + v.length, 0) === nc, 'chunking keeps every instance');
console.log('chunks: trees', tc.size, 'cars', cc.size);
// triangle load per frame (no frustum culling, i.e. a worst case) for a camera at (x, y) in data axes
function load(cx, cy) {
  const out = { full: 0, far: 0, cars: 0, fullTrees: 0, farTrees: 0 };
  for (const idx of tc.values()) {
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const i of idx) { const x = data[i * TREE_STRIDE], y = data[i * TREE_STRIDE + 1]; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2; let r = 0; for (const i of idx) r = Math.max(r, Math.hypot(data[i * TREE_STRIDE] - mx, data[i * TREE_STRIDE + 1] - my));
    const lod = treeLod(Math.hypot(mx - cx, my - cy), r + 20);
    if (lod === 0) { out.full += idx.length * full; out.fullTrees += idx.length; } else if (lod === 1) { out.far += idx.length * far; out.farTrees += idx.length; }
  }
  for (const idx of cc.values()) { const i = idx[0]; if (Math.hypot(cars[i * CAR_STRIDE] - cx, cars[i * CAR_STRIDE + 1] - cy) < LOD.hideCars) out.cars += idx.length * 38; }
  return out;
}
for (const [name, x, y] of [['Shibuya', 116, -112], ['Yoyogi park', -100, 1400], ['city centre of frame', 1100, 1100]]) {
  const l = load(x, y);
  console.log(name, '- trees full', l.fullTrees, '(' + (l.full / 1e6).toFixed(2) + 'M tris), far', l.farTrees, '(' + (l.far / 1e6).toFixed(2) + 'M tris), cars ~' + (l.cars / 1e6).toFixed(2) + 'M tris');
  if (name === 'Shibuya') ok(l.full + l.far < 2.5e6, 'Shibuya: tree triangles under 2.5M even before frustum culling');
}
