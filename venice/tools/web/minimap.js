// Minimap. The image is the walk raster itself (tools/map_build.py): calli, campi and bridge decks light, buildings
// dark, water blue, so it shows exactly where one can walk.  Small and north-up in the corner, centred on you; a click
// (or M) opens the whole island with the places named; a click, M or Esc closes it.
import { PLACES } from './ui.js';

const SPAN = 380;                // metres across the small map

export class MiniMap {
  constructor(root, getLang) {
    this.getLang = getLang;
    this.el = document.createElement('div'); this.el.className = 'map hidden';
    this.cv = document.createElement('canvas'); this.el.appendChild(this.cv); root.appendChild(this.el);
    this.g = this.cv.getContext('2d');
    this.big = false; this.t = 0; this.img = null; this.meta = null; this.on = false;
    this.el.addEventListener('pointerdown', (e) => e.stopPropagation());
    this.el.addEventListener('click', (e) => { e.stopPropagation(); this.toggle(); });
    addEventListener('keydown', (e) => {
      if (!this.on || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
      if (e.code === 'KeyM') this.toggle(); else if (e.code === 'Escape' && this.big) this.toggle();
    });
    Promise.all([
      fetch('tex/map.json').then((r) => r.json()),
      new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = 'tex/map.webp'; }),
    ]).then(([m, im]) => { this.meta = m; this.img = im; }).catch(() => { /* no map: the corner stays empty */ });
  }
  show(on) {
    if (on === this.on) return;
    this.on = on; this.el.classList.toggle('hidden', !on);
    if (!on && this.big) this.toggle();
  }
  toggle() { this.big = !this.big; this.el.classList.toggle('big', this.big); this.t = 0; }
  px(x, y) { const e = this.meta.extent, m = this.meta.mpp; return [(x - e[0]) / m, (e[3] - y) / m]; }   // world -> image px
  update(dt, x, y, yaw) {
    if (!this.img || !this.on) return;
    this.t -= dt; if (this.t > 0) return;
    this.t = this.big ? 1 / 15 : 1 / 30;
    const r = this.el.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
    const W = Math.max(1, Math.round(r.width * dpr)), H = Math.max(1, Math.round(r.height * dpr));
    if (this.cv.width !== W || this.cv.height !== H) { this.cv.width = W; this.cv.height = H; }
    const g = this.g, img = this.img;
    g.fillStyle = '#1a2734'; g.fillRect(0, 0, W, H);
    const [ix, iy] = this.px(x, y);
    // image px -> canvas px:  c = (p - o) * s
    let s, ox, oy;
    if (this.big) { s = Math.min(W / img.width, H / img.height); ox = (img.width - W / s) / 2; oy = (img.height - H / s) / 2; }
    else { const span = SPAN / this.meta.mpp; s = W / span; ox = ix - W / s / 2; oy = iy - H / s / 2; }
    // only the part of the image inside the canvas (a source rectangle off the image draws nothing in some browsers)
    const sx = Math.max(0, ox), sy = Math.max(0, oy), ex = Math.min(img.width, ox + W / s), ey = Math.min(img.height, oy + H / s);
    if (ex > sx && ey > sy) g.drawImage(img, sx, sy, ex - sx, ey - sy, (sx - ox) * s, (sy - oy) * s, (ex - sx) * s, (ey - sy) * s);
    if (this.big) {
      const lang = this.getLang(), fs = 11 * dpr, gap = 6 * dpr;
      g.font = `${fs}px "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Noto Sans JP", sans-serif`; g.textBaseline = 'middle';
      g.lineJoin = 'round';
      // San Marco's places sit a few pixels apart at this scale: each label takes the first side of its dot that
      // covers no other dot, no label placed before it and not you; inside views share their building's label
      const [yx, yy] = this.px(x, y), d = 4 * dpr;
      const hit = (a, b) => a[0] < b[0] + b[2] && b[0] < a[0] + a[2] && a[1] < b[1] + b[3] && b[1] < a[1] + a[3];
      const labs = PLACES.filter((p) => p.at && !p.id.includes('_')).map((p) => {
        const [qx, qy] = this.px(p.at[0], p.at[1]);
        return { cx: (qx - ox) * s, cy: (qy - oy) * s, text: (p.map || p)[lang] };
      });
      const used = [[(yx - ox) * s - 9 * dpr, (yy - oy) * s - 9 * dpr, 18 * dpr, 18 * dpr]];
      g.fillStyle = 'rgba(246,241,231,.9)';
      for (const l of labs) { g.beginPath(); g.arc(l.cx, l.cy, 2.5 * dpr, 0, 6.283); g.fill(); }
      for (const l of labs) {
        const { cx, cy, text } = l, w = g.measureText(text).width, h = fs * 1.3;
        const dots = labs.filter((o) => o !== l).map((o) => [o.cx - d, o.cy - d, 2 * d, 2 * d]);
        const sides = [[gap, 0], [-gap - w, 0], [gap, -h], [gap, h], [-gap - w, -h], [-gap - w, h], [gap, -2 * h], [gap, 2 * h]];
        let at = sides[0];
        for (const [dx, dy] of sides) {
          const r = [cx + dx, cy + dy - h / 2, w, h];
          if (!used.some((u) => hit(r, u)) && !dots.some((u) => hit(r, u))) { at = [dx, dy]; break; }
        }
        used.push([cx + at[0], cy + at[1] - h / 2, w, h]);
        const tx = cx + at[0], ty = cy + at[1];
        if (at[1]) { g.strokeStyle = 'rgba(246,241,231,.5)'; g.lineWidth = dpr; g.beginPath(); g.moveTo(cx, cy); g.lineTo(at[0] > 0 ? tx - 2 * dpr : tx + w + 2 * dpr, ty); g.stroke(); }
        g.lineWidth = 3 * dpr; g.strokeStyle = 'rgba(13,15,18,.8)'; g.strokeText(text, tx, ty); g.fillText(text, tx, ty);
      }
    }
    // you: the direction you face (north is up, so the screen angle is -yaw) and a dot
    const cx = (ix - ox) * s, cy = (iy - oy) * s, R = (this.big ? 7 : 6) * dpr;
    g.fillStyle = 'rgba(242,184,75,.30)'; g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, R * 5, -yaw - 0.5, -yaw + 0.5); g.closePath(); g.fill();
    g.fillStyle = '#f2b84b'; g.strokeStyle = '#0d0f12'; g.lineWidth = 2 * dpr; g.beginPath(); g.arc(cx, cy, R * 0.6, 0, 6.283); g.fill(); g.stroke();
  }
}
