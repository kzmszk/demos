// Zone manager: exterior zones are always shown outside; each interior is shown (alone) while the camera is
// inside one of its volumes.  Interiors are loaded on demand.
import { loadZone } from './zones.js';
import { toB, toS, toR, ROOMS } from './frames.js';

const inBox = (p, b) => p[0] > b[0] && p[0] < b[1] && p[1] > b[2] && p[1] < b[3] && p[2] > b[4] && p[2] < b[5];

export function makeInteriors() {
  const list = [];
  // basilica: union of boxes in the basilica frame (u, v, z above the floor)
  // the eye opens up when rising into the dome (the drum windows light it less than the floor-level lamps)
  const domeExp = (P) => { const [u, v] = toB(P.x, P.y), z = P.z - 6; if (Math.abs(u) > 21 || Math.abs(v) > 21) return 0.62;
    const t = Math.min(1, Math.max(0, (z - 12) / 60)); return 0.62 + 0.4 * t * t * (3 - 2 * t); };
  list.push({ zone: 'basilica', exposure: domeExp, sun: false, bg: 0x0b0906,
    test: (P) => { const [u, v] = toB(P.x, P.y), z = P.z - 6; const p = [u, v, z];
      return [[20, 116, -31, 31, -1.5, 46], [-70, -20, -14, 14, -1.5, 46], [-14, 14, -70, 70, -1.5, 46], [-21, 21, -21, 21, -1.5, 119], [-7, 7, -7, 7, 118, 131]].some((b) => inBox(p, b)); } });
  list.push({ zone: 'sistine', exposure: 0.72, sun: false, bg: 0x0b0906,
    test: (P) => inBox(toS(P.x, P.y, P.z), [-20.3, 20.3, -6.8, 6.8, -0.6, 21.2]) });
  for (const name of Object.keys(ROOMS)) {
    const r = ROOMS[name], b = r.box;
    list.push({ zone: 'room_' + name, exposure: r.exposure, sun: name === 'ottagono', bg: ['ottagono', 'rotonda', 'momo'].includes(name) ? null : 0x0b0906,
      test: (P) => inBox(toR(r, P.x, P.y, P.z), [b.u0 - 0.2, b.u1 + 0.2, b.v0 - 0.2, b.v1 + 0.2, b.z0, b.z1 + (name === 'ottagono' ? 30 : 0)]) });
  }
  return list;
}

export class World {
  constructor(scene, getMaterial, onProgress) {
    this.scene = scene; this.getMaterial = getMaterial; this.onProgress = onProgress;
    this.groups = {}; this.loading = {}; this.exterior = ['city', 'core'];
    this.interiors = makeInteriors(); this.current = null;
  }
  load(name) {
    if (this.groups[name]) return Promise.resolve(this.groups[name]);
    if (this.loading[name]) return this.loading[name];
    this.loading[name] = loadZone(name, 'data', this.getMaterial, (p) => this.onProgress && this.onProgress(name, p)).then((g) => {
      g.visible = false; this.scene.add(g); g.updateMatrixWorld(true); this.groups[name] = g; return g;
    });
    return this.loading[name];
  }
  ready(name) { return !!this.groups[name]; }
  /** decide which zones are drawn for camera position P; returns the interior descriptor or null */
  update(P) {
    let cur = null;
    for (const I of this.interiors) if (this.groups[I.zone] && I.test(P)) { cur = I; break; }
    this.current = cur;
    for (const [name, g] of Object.entries(this.groups)) {
      g.visible = cur ? name === cur.zone : this.exterior.includes(name) || name === 'room_ottagono';
    }
    return cur;
  }
  /** which interior zone a position would need (for preloading) */
  zoneAt(P) { for (const I of this.interiors) if (I.test(P)) return I.zone; return null; }
}
