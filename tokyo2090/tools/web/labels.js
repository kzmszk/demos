import * as THREE from 'three';

// Names on the city, so you know where you are. Landmark towers carry a small balloon over their (broken) tops that
// can be read from kilometres away; flat places (parks, shrines, stations, crossings) are named in letter-spaced text
// lying over them when you pass near. DOM labels over the canvas, positioned every frame, culled and de-cluttered
// five times a second. Data: data/places.json (gen/places.py), plus the hand-built districts' own labels.

const CSS = `
  #labels { position: fixed; inset: 0; pointer-events: none; overflow: hidden; z-index: 2; }
  #labels .pl { position: absolute; left: 0; top: 0; white-space: nowrap; will-change: transform, opacity; opacity: 0; transition: opacity .5s; }
  #labels .tw { transform-origin: 50% 100%; }
  #labels .tw .box { display: block; padding: 3px 9px 4px; border-radius: 3px; background: rgba(20,15,12,.58); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
    color: #f1e6d6; font-size: 12px; letter-spacing: .08em; line-height: 1.35; text-align: center; box-shadow: 0 1px 6px rgba(0,0,0,.25); }
  #labels .tw .box i { display: block; font-style: normal; font-size: 10px; letter-spacing: .12em; color: rgba(241,230,214,.6); }
  #labels .tw .stem { display: block; width: 1px; height: 22px; margin: 0 auto; background: linear-gradient(rgba(241,230,214,.7), rgba(241,230,214,0)); }
  #labels .tw.t2 .box { font-size: 11px; padding: 2px 7px 3px; }
  #labels .tw.hero .box { background: rgba(70,40,26,.55); }
  #labels .ar { transform-origin: 50% 50%; color: #f4ecdf; font-size: 15px; letter-spacing: .5em; font-weight: 300;
    text-shadow: 0 1px 2px rgba(0,0,0,.85), 0 0 12px rgba(0,0,0,.55); }
  #labels .ar small { display: block; text-align: center; font-size: 9px; letter-spacing: .3em; opacity: .65; margin-top: 2px; }
  #labels .ar.street { font-size: 13px; letter-spacing: .35em; }
  #labels .ln { color: #e9f0dc; font-size: 11px; letter-spacing: .3em; text-shadow: 0 1px 2px rgba(0,0,0,.85), 0 0 8px rgba(0,0,0,.5); }
  #labels .ln::before, #labels .ln::after { content: ''; display: inline-block; width: 14px; height: 1px; background: rgba(233,240,220,.6); vertical-align: middle; margin: 0 6px; }
  #labels .st { color: #f4ecdf; font-size: 12px; letter-spacing: .14em; padding: 1px 7px 2px 6px; border-left: 3px solid #8fa87a; background: rgba(20,15,12,.45);
    text-shadow: 0 1px 2px rgba(0,0,0,.7); }
  body.intro #labels, body.nolabels #labels { display: none; }
  body.touch #labels .tw .box { font-size: 11px; } body.touch #labels .ar { font-size: 13px; letter-spacing: .35em; }
`;

const KIND = { park: '公園', shrine: '', place: '', street: '', station: '' };

export function makeLabels({ places, ground, roof }) {
  const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  const root = document.createElement('div'); root.id = 'labels'; document.body.appendChild(root);
  const items = [];
  const add = (it) => {
    const el = document.createElement('div');
    if (it.type === 'tower') {
      el.className = 'pl tw' + (it.tier === 2 ? ' t2' : '') + (it.hero ? ' hero' : '');
      el.innerHTML = `<span class="box">${it.name}<i></i></span><span class="stem"></span>`;
      it.dist = el.querySelector('i');
    } else if (it.type === 'station') { el.className = 'pl st'; el.textContent = it.name; }
    else if (it.kind === 'line') { el.className = 'pl ln'; el.textContent = it.name; }
    else { el.className = 'pl ar' + (it.kind === 'street' ? ' street' : ''); el.textContent = it.name; }
    root.appendChild(el); it.el = el; it.w = 0; it.h = 0; it.on = false; it.op = 0; it.sx = 0; it.sy = 0; it.vis = false;
    items.push(it); return it;
  };
  for (const [name, en, x, y, z, tier] of places.towers) add({ type: 'tower', name, en, x, y, z: z + 4, tier, pri: tier === 1 ? 3 : 2 });
  for (const [name, en, kind, x, y, z, r, outline] of places.areas) {
    add({ type: kind === 'station' ? 'station' : 'area', kind, name, en, x, y, z: z + (kind === 'station' ? 14 : 3), r, poly: outline && outline.length > 2 ? outline : null, pri: kind === 'station' ? 1.5 : 1 });
  }
  const v = new THREE.Vector3();
  let t = 0, enabled = true;
  // distance from (x, y) to a place: 0 inside its outline, else to its edge (or to its centre minus its radius)
  function areaDist(it, x, y) {
    if (!it.poly) return Math.max(0, Math.hypot(x - it.x, y - it.y) - it.r);
    const p = it.poly; let inside = false, best = 1e9;
    for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
      const [xi, yi] = p[i], [xj, yj] = p[j];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
      const dx = xj - xi, dy = yj - yi, l2 = dx * dx + dy * dy || 1, u = Math.max(0, Math.min(1, ((x - xi) * dx + (y - yi) * dy) / l2));
      best = Math.min(best, Math.hypot(x - xi - u * dx, y - yi - u * dy));
    }
    return inside ? 0 : best;
  }
  // a tower behind a nearer building reads dimmer (the label is still useful: it tells you which way to fly)
  function occluded(cam, it) {
    const cx = cam.x, cy = -cam.z, cz = cam.y, dx = it.x - cx, dy = it.y - cy, dz = it.z - 6 - cz, d = Math.hypot(dx, dy);
    const n = Math.min(40, Math.max(6, Math.floor(d / 40)));
    for (let k = 1; k < n; k++) {
      const s = k / n, x = cx + dx * s, y = cy + dy * s, z = cz + dz * s;
      if (Math.hypot(x - it.x, y - it.y) < 45) break;
      const top = roof.top(x, y); if (top > z || ground(x, y) > z) return Math.hypot(x - cx, y - cy);
    }
    return 0;
  }
  let here = '';
  return {
    root, items,
    get here() { return here; },
    set enabled(on) { enabled = on; document.body.classList.toggle('nolabels', !on); },
    get enabled() { return enabled; },
    // the hand-built districts name their own pieces (QFRONT, ハチ公像, ママン...): seen only when you are close
    addLocal(list, ox, oy) {
      for (const l of list) {
        const x = ox + l.x, y = oy + l.y;
        // the same name as a city-wide tower: that tower's balloon moves to where the district puts it
        const tw = items.find((i) => i.type === 'tower' && !i.local && (i.name === l.name || (l.name.startsWith(i.name) && Math.hypot(i.x - x, i.y - y) < 80)));
        if (l.kind === 'place' && items.some((i) => i.type === 'area' && i.name === l.name)) continue;
        if (tw) { tw.x = x; tw.y = y; if (l.z != null) tw.z = l.z + 4; continue; }
        if (l.kind === 'place') add({ type: 'area', kind: 'place', name: l.name, x, y, z: (l.z ?? ground(x, y)) + 2, r: 25, poly: null, pri: 1.2, local: true });
        else add({ type: 'tower', name: l.name, x, y, z: l.z ?? ground(x, y) + 20, tier: 3, hero: true, pri: 2.5, local: true });
      }
    },
    // the railway lines, named along the track
    addLines(list, ground) { for (const [name, x, y] of list) add({ type: 'area', kind: 'line', name, x, y, z: ground(x, y) + 2, r: 0, poly: null, pri: 0.8 }); },
    // replace a tower's anchor (a hand-built district knows where its broken top really is)
    setTop(name, x, y, z) { const it = items.find((i) => i.name === name); if (it) { it.x = x; it.y = y; it.z = z + 4; } },
    update(camera, dt) {
      t -= dt;
      const W = innerWidth, H = innerHeight, cam = camera.position;
      const cx = cam.x, cy = -cam.z, alt = cam.y - ground(cx, cy);
      if (t <= 0 && enabled) {
        t = 0.2;
        // which labels are wanted, from distance and height
        let hereD = 1e9; here = '';
        for (const it of items) {
          const dh = Math.hypot(it.x - cx, it.y - cy); it.dh = dh;
          let want = 0;
          if (it.type === 'tower') {
            if (it.local) want = dh < 420 && dh > 12 ? 1 - smooth(260, 420, dh) : 0;
            else {
              const far = it.tier === 1 ? 7500 : 3200;
              want = (1 - smooth(far * 0.6, far, dh)) * smooth(90, 220, Math.hypot(dh, it.z - cam.y));
            }
            // on foot (or low) the far towers only clutter the street: the nearer big ones, and only when in sight
            if (want > 0 && !it.local && alt < 30 && (it.tier === 2 ? dh > 1500 : dh > 4000)) want = 0;
            // behind something: hidden when that something is close (a label pinned on a near facade reads wrong), dimmed when far
            if (want > 0 && !it.local) { const o = occluded(cam, it); if (o) want *= alt < 30 || o < 450 ? 0 : 0.45; }
          } else {
            const d = areaDist(it, cx, cy);
            const reach = it.local ? 160 : it.kind === 'line' ? Math.min(600, 160 + Math.max(0, alt) * 1.2) : Math.min(1100, (it.type === 'station' ? 380 : 320) + Math.max(0, alt) * 1.6 + it.r * 0.3);
            want = 1 - smooth(reach * 0.6, reach, d);
            if (it.type !== 'station' && !it.local && d < 1 && it.r > 60) want = Math.max(want, 0.75);
            if (want > 0 && alt < 30 && dh > 60 && occluded(cam, it)) want = 0;
            if (d < hereD && d < 40 && !it.local && it.kind !== 'line') { hereD = d; here = it.name; }
          }
          it.want = want;
        }
        // project, then hide the lower-priority ones that would overlap a label already placed
        const placed = [];
        const order = items.filter((it) => it.want > 0.02).sort((a, b) => b.pri - a.pri || a.dh - b.dh);
        for (const it of items) it.vis = false;
        for (const it of order) {
          v.set(it.x, it.z, -it.y).project(camera);
          if (v.z > 1 || v.x < -1.2 || v.x > 1.2 || v.y < -1.2 || v.y > 1.2) continue;
          if (!it.w) { const r = it.el.getBoundingClientRect(); it.w = r.width || 80; it.h = r.height || 24; }
          const sx = (v.x * 0.5 + 0.5) * W, sy = (-v.y * 0.5 + 0.5) * H;
          const box = it.type === 'tower' ? [sx - it.w / 2, sy - it.h, sx + it.w / 2, sy] : [sx - it.w / 2, sy - it.h / 2, sx + it.w / 2, sy + it.h / 2];
          if (placed.some((b) => box[0] < b[2] + 6 && box[2] + 6 > b[0] && box[1] < b[3] + 4 && box[3] + 4 > b[1])) continue;
          placed.push(box); it.vis = true;
        }
        for (const it of items) {
          const op = it.vis ? Math.min(1, it.want * 1.3) : 0;
          if (Math.abs(op - it.op) > 0.02) { it.op = op; it.el.style.opacity = op.toFixed(2); }
          if (it.type === 'tower' && it.vis && !it.local) {
            const d = Math.hypot(it.x - cx, it.y - cy);
            it.dist.textContent = d > 950 ? (d / 1000).toFixed(1) + ' km' : Math.round(d / 10) * 10 + ' m';
          }
        }
      }
      if (!enabled) return;
      // every frame: follow the screen
      for (const it of items) {
        if (it.op <= 0 && !it.vis) continue;
        v.set(it.x, it.z, -it.y).project(camera);
        if (v.z > 1) { it.el.style.opacity = '0'; it.op = 0; continue; }
        const sx = (v.x * 0.5 + 0.5) * W, sy = (-v.y * 0.5 + 0.5) * H;
        if (it.type === 'tower') it.el.style.transform = `translate(${(sx - it.w / 2).toFixed(1)}px, ${(sy - it.h).toFixed(1)}px)`;
        else it.el.style.transform = `translate(${(sx - it.w / 2).toFixed(1)}px, ${(sy - it.h / 2).toFixed(1)}px)`;
      }
    },
  };
}
function smooth(a, b, x) { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); }
