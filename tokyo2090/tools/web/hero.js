import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { fetchBin } from './data.js';

// The hand-built districts (Blender, tools/hero/): Shibuya crossing to 109, the Tocho, Roppongi Hills. Each comes in
// three levels — far (the silhouette, loaded at start), mid and near (loaded when you come close) — placed at its
// origin in the city frame (the glTF is +Y up, so Blender's x east / y north / z up lands on three's (x, z, -y)).
// Their collision proxy, rasterised from above at 0.5 m (field.bin, gen/hero_collide.py), is what the walker stands
// on inside the district. Data axes: x east, y north, z up.

const RANGE = { near: 420, mid: 1300 }, RANGE_LOW = { near: 0, mid: 650 };
// the district boxes in the city frame (gen/hero_src.py DISTRICTS)
const BOXES = { shibuya: [-235, -75, 75, 175], tocho: [-880, 3100, -645, 3440], roppongi: [2470, -140, 2830, 240] };

export async function makeHeroes(scene, { low, renderer, camera }) {
  let list = [];
  try { list = await (await fetch('data/heroes.json')).json(); } catch (e) { list = []; }
  // ?hero=<name>: preview a district straight from public/hero/<name>/ before gen.hero_collide has folded it in (no
  // collision field; the procedural city is cut away inside its box by the city shader)
  const preview = new URLSearchParams(location.search).get('hero');
  if (preview && BOXES[preview] && !list.some((d) => d.name === preview)) {
    let meta = {}; try { meta = await (await fetch(`hero/${preview}/hero.json`)).json(); } catch (e) { /* none yet */ }
    const b = BOXES[preview], files = {};
    for (const l of ['near', 'mid', 'far']) { try { files[l] = (await fetch(`hero/${preview}/${l}.glb`, { method: 'HEAD' })).ok; } catch (e) { files[l] = false; } }
    list.push({ name: preview, title: meta.title || preview, origin: meta.origin || [Math.round((b[0] + b[2]) / 20) * 10, Math.round((b[1] + b[3]) / 20) * 10], box: b, files, spawns: meta.spawns || [], labels: meta.labels || [], preview: true });
  }
  const loader = new GLTFLoader();
  const draco = new DRACOLoader(); draco.setDecoderPath('libs/draco/'); loader.setDRACOLoader(draco);
  const range = low ? RANGE_LOW : RANGE;
  const districts = [];
  for (const d of list) {
    const group = new THREE.Group(); group.name = 'hero:' + d.name; group.position.set(d.origin[0], 0, -d.origin[1]); scene.add(group);
    districts.push({ ...d, group, lods: {}, loading: {}, level: null, field: null });
  }
  // the materials the game wants: shadows both ways, decals offset onto the ground, foliage alpha-tested and two-sided
  function prepare(root) {
    const seen = new Set();
    root.traverse((o) => {
      if (!o.isMesh) return;
      // one material per mesh: a glTF material shared by an instanced and a plain mesh was not drawn at all (tocho's trees)
      if (Array.isArray(o.material)) o.material = o.material.map((m) => { if (seen.has(m)) return m.clone(); seen.add(m); return m; });
      else if (o.material) { if (seen.has(o.material)) o.material = o.material.clone(); else seen.add(o.material); }
      const name = (o.name || '') + ' ' + (o.parent?.name || '');
      o.castShadow = !/decal_/.test(name); o.receiveShadow = true;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        if (!m) continue;
        if (/decal_/.test(name)) { m.polygonOffset = true; m.polygonOffsetFactor = -2; m.polygonOffsetUnits = -4; }
        if (/foliage_/.test(name) || m.alphaTest > 0 || m.transparent) { m.side = THREE.DoubleSide; if (m.alphaTest === 0) m.alphaTest = 0.5; m.transparent = false; m.alphaToCoverage = !low; }
        if (/glass_/.test(name)) { m.roughness = Math.min(m.roughness, 0.15); }
        if (m.metalness > 0.4) m.metalness = 0.4;                         // no environment map: metal would read black
        m.envMapIntensity = 0;
        // three's Lambert term carries 1/π (albedo/π × light) and the city's shaders do not (albedo × light): the same
        // albedo would read about three times darker here than on the procedural buildings next door
        if (!m.userData.piScaled) { m.color.multiplyScalar(Math.PI); m.userData.piScaled = true; }
      }
    });
  }
  function load(d, level) {
    if (d.lods[level] || d.loading[level] || !d.files?.[level]) return;
    d.loading[level] = loader.loadAsync(`hero/${d.name}/${level}.glb`).then((g) => {
      prepare(g.scene); g.scene.visible = false; d.group.add(g.scene); d.lods[level] = g.scene;
      if (renderer?.compileAsync && camera) renderer.compileAsync(g.scene, camera).catch(() => {});
    }).catch((e) => console.warn('hero', d.name, level, e)).finally(() => { d.loading[level] = null; });
  }
  async function loadField(d) {
    if (d.field || d.fieldLoading) return; d.fieldLoading = true;
    try {
      const { head, buf, offset } = await fetchBin(`hero/${d.name}/field.bin`);
      d.field = { ...head, q: new Int16Array(buf.slice(offset, offset + head.w * head.h * 2)) };
    } catch (e) { console.warn('hero field', d.name, e); }
  }
  for (const d of districts) { load(d, 'far'); if (!d.preview) loadField(d); }
  const boxDist = (d, x, y) => Math.hypot(Math.max(d.box[0] - x, 0, x - d.box[2]), Math.max(d.box[1] - y, 0, y - d.box[3]));
  return {
    districts,
    ready(name) { const d = districts.find((d) => d.name === name); return !d || ((!!d.field || d.preview) && (!!d.lods.near || !!d.lods.mid || !d.files.near)); },
    get preview() { return districts.find((d) => d.preview) || null; },
    // a district's box contains (x, y): the procedural trees and cars stay out of it
    boxes: districts.map((d) => d.box),
    // the walker's surface inside a district: the field's height at (x, y), or null outside every field (and -Infinity where
    // the field has nothing but terrain)
    field(x, y) {
      for (const d of districts) {
        const f = d.field; if (!f) continue;
        const i = Math.floor((x - f.x0) / f.res), j = Math.floor((y - f.y0) / f.res);
        if (i < 0 || j < 0 || i >= f.w || j >= f.h) continue;
        const v = f.q[j * f.w + i]; return v === -32768 ? -Infinity : v / 10;
      }
      return null;
    },
    // the highest point of a district's field near (x, y) (for the labels of the towers it replaces)
    topNear(x, y, r = 30) {
      let top = -Infinity;
      for (const d of districts) {
        const f = d.field; if (!f) continue;
        for (let yy = y - r; yy <= y + r; yy += f.res * 2) for (let xx = x - r; xx <= x + r; xx += f.res * 2) {
          const i = Math.floor((xx - f.x0) / f.res), j = Math.floor((yy - f.y0) / f.res);
          if (i < 0 || j < 0 || i >= f.w || j >= f.h) continue; const v = f.q[j * f.w + i]; if (v !== -32768) top = Math.max(top, v / 10);
        }
      }
      return top;
    },
    // pick the level by the camera's distance to the box (with a little hysteresis), load what is missing
    update(cam) {
      const x = cam.x, y = -cam.z;
      for (const d of districts) {
        const dist = boxDist(d, x, y), h = d.level ? 60 : 0;
        let want = dist < range.near + (d.level === 'near' ? h : 0) ? 'near' : dist < range.mid + (d.level === 'mid' ? h : 0) ? 'mid' : 'far';
        if (want === 'near' && !d.files.near) want = 'mid';
        if (want === 'mid' && !d.files.mid) want = d.files.near && dist < range.mid ? 'near' : 'far';
        if (want !== 'far') { load(d, want); if (want === 'near') load(d, 'mid'); }
        if (dist < range.mid * 1.6) { if (want === 'far' && d.files.mid) load(d, 'mid'); }
        // show the wanted level if it is loaded, else the best one we have
        const order = want === 'near' ? ['near', 'mid', 'far'] : want === 'mid' ? ['mid', 'near', 'far'] : ['far', 'mid', 'near'];
        const show = order.find((l) => d.lods[l]);
        if (show !== d.level) { for (const l in d.lods) d.lods[l].visible = l === show; d.level = show; }
        // phones: free the near/mid levels again when far away
        if (low && dist > range.mid * 2.5) for (const l of ['near', 'mid']) if (d.lods[l]) { dispose(d.lods[l]); d.lods[l] = null; delete d.lods[l]; if (d.level === l) d.level = null; }
      }
    },
  };
}
function dispose(root) {
  root.parent?.remove(root);
  root.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); const ms = Array.isArray(o.material) ? o.material : [o.material]; for (const m of ms) { for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'alphaMap']) m[k]?.dispose(); m.dispose(); } } });
}
