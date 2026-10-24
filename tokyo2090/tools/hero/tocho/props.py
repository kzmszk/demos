"""Abandoned vehicles, street furniture and office leftovers for the Tokyo Metropolitan Government district, 2090.

Pipeline (runs inside Blender 5.2, see the bottom of the file for the API):
  geometry   every model is plain python (Geo): faces with a semantic tag and explicit per-face UVs in metres
  layout     islands -> shelf packed into one rectangle per model -> rectangles packed into the 2048 atlas
  raster     the atlas is rasterised into position / normal / tag maps (a numpy 'shader' then paints from 3D position)
  paint      colour, normal (from a painted height field), roughness / metal, cavity occlusion
  bake       Cycles GPU AO of each model in isolation on a ground plane -> ORM red channel
"""
import bpy, bmesh, math, os, sys, json, subprocess, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from mathutils import Vector, Matrix
import common as C
import materials as M
import textures as T
import render

ATLAS = 2048
PAD = 7            # px kept around every island (>= bake margin)
GAP = 10           # px between model regions
FOLD = False         # mirror-fold the main car body (left = right in UV space): saves atlas but overlaps islands
DEV_ONLY = None    # development: restrict to these model names
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_SERIF = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
PY_TEXT = '/home/kazu/work/kyoto-assets/.venv/bin/python'

# face tags: what a surface is made of; the painters key on them
(PAINT, INT, TYRE, RIM, UNDER, TRIM, GLASS, CHROME, STEEL, CONC, GRAN, FAB, CARD, PLAS, SIGN, WOOD, PAPER, BARE,
 PAINT2, LAMP, SOIL) = range(21)

V3 = Vector


# =============================================================================================== geometry container
class Geo:
    def __init__(s, name, dens=80.0):
        s.name = name; s.dens = dens
        s.V = []; s.F = []; s.T = []; s.I = []; s.UV = []; s.isl = []
        s.boxes = []; s.info = {}
        s.rect = None          # (x, y, w, h) px in the atlas
        s.UVpx = None

    def island(s, m=1.0):
        s.isl.append({'m': m}); return len(s.isl) - 1

    def face(s, pts, uv, tag, isl):
        s.F.append([s._v(p) for p in pts]); s.T.append(tag); s.I.append(isl)
        s.UV.append([(float(a), float(b)) for a, b in uv])

    def facen(s, pts, tag, isl, n, uv=None):
        """face oriented so its normal points along n; planar uv unless given"""
        pts = [V3(p) for p in pts]
        if uv is None:
            uv = planar(pts)
            mn = (min(u[0] for u in uv), min(u[1] for u in uv)); uv = [(a - mn[0], b - mn[1]) for a, b in uv]
        if newell(pts).dot(V3(n)) < 0: pts = pts[::-1]; uv = uv[::-1]
        s.face(pts, uv, tag, isl)

    def _v(s, p):
        s.V.append((float(p[0]), float(p[1]), float(p[2]))); return len(s.V) - 1

    def tris(s):
        return sum(len(f) - 2 for f in s.F)


def frame_of(n):
    n = V3(n).normalized()
    if abs(n.z) > 0.9: u = V3((1, 0, 0))
    else: u = V3((0, 0, 1)).cross(n).normalized()
    return u, n.cross(u)


def newell(pts):
    n = V3((0, 0, 0))
    for i in range(len(pts)):
        a = V3(pts[i]); b = V3(pts[(i + 1) % len(pts)])
        n += V3(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    return n.normalized() if n.length > 1e-12 else V3((0, 0, 1))


def planar(pts, n=None, o=None, uv0=(0, 0)):
    n = newell(pts) if n is None else V3(n)
    u, v = frame_of(n)
    o = V3(pts[0]) if o is None else V3(o)
    return [((V3(p) - o).dot(u) + uv0[0], (V3(p) - o).dot(v) + uv0[1]) for p in pts]


def rotm(rot):
    if rot is None: return Matrix.Identity(3)
    if isinstance(rot, (int, float)): return Matrix.Rotation(rot, 3, 'Z')
    return rot


WMAX = 2.6      # metres: width at which the faces of one box wrap to a new row of its island


def box(g, c, sz, tag=PAINT, m=1.0, rot=None, faces='xXyYzZ', isl=None, tags=None):
    """axis box centred at c; faces keyed x X y Y z Z = +x -x +y -y +z -z.  Faces are laid out in rows in one island (long side along u)"""
    hx, hy, hz = sz[0] / 2, sz[1] / 2, sz[2] / 2
    sx, sy, szz = sz
    R = rotm(rot); c = V3(c)
    F = {
        'x': ([(hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz)], lambda p: (p[1] + hy, p[2] + hz), (sy, szz)),
        'X': ([(-hx, hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz)], lambda p: (-p[1] + hy, p[2] + hz), (sy, szz)),
        'y': ([(hx, hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz)], lambda p: (-p[0] + hx, p[2] + hz), (sx, szz)),
        'Y': ([(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)], lambda p: (p[0] + hx, p[2] + hz), (sx, szz)),
        'z': ([(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)], lambda p: (p[0] + hx, p[1] + hy), (sx, sy)),
        'Z': ([(-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz), (-hx, -hy, -hz)], lambda p: (p[0] + hx, -p[1] + hy), (sx, sy)),
    }
    if isl is None: isl = g.island(m)
    items = []
    for k in faces:
        pts, uvf, (fw, fh) = F[k]
        rotf = fw < fh
        items.append((max(fw, fh), min(fw, fh), k, rotf))
    items.sort(key=lambda t: -t[0])
    wmax = max(WMAX, items[0][0])
    x = y = rowh = 0.0; place = {}
    for (lw, lh, k, rotf) in items:
        if x + lw > wmax and x > 0:
            x = 0.0; y += rowh + 0.03; rowh = 0.0
        place[k] = (x, y); x += lw + 0.03; rowh = max(rowh, lh)
    for k in faces:
        pts, uvf, (fw, fh) = F[k]
        rotf = fw < fh
        ox, oy = place[k]
        uv = []
        for p in pts:
            u, v = uvf(p)
            if rotf: u, v = v, fw - u
            uv.append((u + ox, v + oy))
        t = tags.get(k, tag) if isinstance(tags, dict) else tag
        g.face([c + R @ V3(p) for p in pts], uv, t, isl)
    return isl


def bar(g, p0, p1, w, h, tag=PAINT, m=1.0, caps='both', up=(0, 0, 1)):
    """oriented box between two points, cross-section w (side) x h (up)"""
    p0 = V3(p0); p1 = V3(p1); a = p1 - p0; L = a.length
    an = a / L
    upv = V3(up)
    if abs(an.dot(upv)) > 0.97: upv = V3((1, 0, 0))
    s = upv.cross(an).normalized(); t = s.cross(an)       # x=s, y=an, z=t  (s x an = t ... checked below)
    Rm = Matrix(((s.x, an.x, t.x), (s.y, an.y, t.y), (s.z, an.z, t.z)))
    if Rm.determinant() < 0:
        t = -t; Rm = Matrix(((s.x, an.x, t.x), (s.y, an.y, t.y), (s.z, an.z, t.z)))
    faces = 'xXzZ' + ('y' if caps in ('both', 'end') else '') + ('Y' if caps in ('both', 'start') else '')
    return box(g, (p0 + p1) / 2, (w, L, h), tag, m, Rm, faces)


def cyl(g, p0, p1, r0, r1=None, n=8, tag=PAINT, m=1.0, caps='both', phase=0.0, isl=None, up=(0, 0, 1)):
    p0 = V3(p0); p1 = V3(p1); r1 = r0 if r1 is None else r1
    a = p1 - p0; L = a.length; an = a / L
    e1 = V3(up).cross(an)
    if e1.length < 1e-4: e1 = V3((1, 0, 0)).cross(an)
    e1.normalize(); e2 = an.cross(e1)
    circ = 2 * math.pi * (r0 + r1) / 2
    if isl is None: isl = g.island(m)
    R0 = [p0 + (e1 * math.cos(phase + 2 * math.pi * k / n) + e2 * math.sin(phase + 2 * math.pi * k / n)) * r0 for k in range(n + 1)]
    R1 = [p1 + (e1 * math.cos(phase + 2 * math.pi * k / n) + e2 * math.sin(phase + 2 * math.pi * k / n)) * r1 for k in range(n + 1)]
    for k in range(n):
        u0 = circ * k / n; u1 = circ * (k + 1) / n
        g.face([R0[k], R0[k + 1], R1[k + 1], R1[k]], [(u0, 0), (u1, 0), (u1, L), (u0, L)], tag, isl)
    rm = max(r0, r1)
    if caps in ('both', 'end') and r1 > 1e-5:
        cx = circ + 0.03 + rm
        pts = R1[:n]
        g.face(pts, [(cx + r1 * math.cos(phase + 2 * math.pi * k / n), rm + r1 * math.sin(phase + 2 * math.pi * k / n)) for k in range(n)], tag, isl)
    if caps in ('both', 'start') and r0 > 1e-5:
        cx = circ + 0.03 + rm
        pts = R0[:n][::-1]
        g.face(pts, [(cx + r0 * math.cos(phase + 2 * math.pi * k / n), 3 * rm + 0.03 + r0 * math.sin(phase + 2 * math.pi * k / n)) for k in range(n)][::-1], tag, isl)
    return isl


def plate(g, pts, off, tag=PAINT, m=1.0, tag_in=None):
    """thin slab: outer polygon (ccw seen from outside), inner copy shifted by off (pointing into the body)"""
    pts = [V3(p) for p in pts]; off = V3(off); n = newell(pts)
    isl = g.island(m)
    uv = planar(pts, n)
    mn = [min(u[0] for u in uv), min(u[1] for u in uv)]; mx = [max(u[0] for u in uv), max(u[1] for u in uv)]
    uv = [(a - mn[0], b - mn[1]) for a, b in uv]
    W = mx[0] - mn[0]; H = mx[1] - mn[1]
    g.face(pts, uv, tag, isl)
    inn = [p + off for p in pts][::-1]
    g.face(inn, [(a + W + 0.03, b) for a, b in uv][::-1], tag if tag_in is None else tag_in, isl)
    th = off.length; x = 0.0
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        l = (pts[j] - pts[i]).length
        g.face([pts[i], pts[i] + off, pts[j] + off, pts[j]], [(x, -th - 0.03), (x, -0.03), (x + l, -0.03), (x + l, -th - 0.03)][::1], tag, isl)
        x += l + 0.02
    return isl


def lathe(g, c, ax, prof, n=10, tags=None, m=1.0, phase=0.0, adj=None, up=(0, 0, 1)):
    """revolve profile [(r, t)] around axis ax through c; the ring order runs ccw seen from +ax.
    faces between consecutive profile points; radius 0 end points collapse to fans."""
    c = V3(c); an = V3(ax).normalized()
    e1 = V3(up).cross(an)
    if e1.length < 1e-4: e1 = V3((1, 0, 0)).cross(an)
    e1.normalize(); e2 = an.cross(e1)
    isl = g.island(m)

    def ring(r, t):
        out = []
        for k in range(n):
            th = phase + 2 * math.pi * k / n
            p = c + an * t + (e1 * math.cos(th) + e2 * math.sin(th)) * r
            out.append(adj(p) if adj else p)
        return out
    v0 = 0.0
    for i in range(len(prof) - 1):
        (ra, ta), (rb, tb) = prof[i], prof[i + 1]
        tag = tags[i] if tags else PAINT
        A = ring(ra, ta); B = ring(rb, tb)
        seg = math.hypot(rb - ra, tb - ta)
        circ = 2 * math.pi * max(ra, rb, 0.01)
        for k in range(n):
            k2 = (k + 1) % n
            u0 = circ * k / n; u1 = circ * (k + 1) / n
            if ra < 1e-6:
                g.face([A[k], B[k2], B[k]], [(0.5 * (u0 + u1), v0), (u1, v0 + seg), (u0, v0 + seg)], tag, isl)
            elif rb < 1e-6:
                g.face([A[k], A[k2], B[k]], [(u0, v0), (u1, v0), (0.5 * (u0 + u1), v0 + seg)], tag, isl)
            else:
                g.face([A[k], A[k2], B[k2], B[k]], [(u0, v0), (u1, v0), (u1, v0 + seg), (u0, v0 + seg)], tag, isl)
        v0 += seg + 0.03
    return isl


# =============================================================================================== layout
def _island_boxes(g):
    if 'ibox' in g.info: return g.info['ibox']
    bb = {}
    for f, i in zip(g.UV, g.I):
        b = bb.setdefault(i, [1e9, 1e9, -1e9, -1e9])
        for u, v in f:
            b[0] = min(b[0], u); b[1] = min(b[1], v); b[2] = max(b[2], u); b[3] = max(b[3], v)
    g.info['ibox'] = bb
    return bb


def _isl_wh(g, scale):
    """island pixel sizes at a density scale; islands are rotated by 90 degrees to landscape (w >= h)"""
    bb = _island_boxes(g)
    for i, b in bb.items():
        ppm = g.dens * scale * g.isl[i]['m']
        w = int(math.ceil((b[2] - b[0]) * ppm)) + 2 * PAD; h = int(math.ceil((b[3] - b[1]) * ppm)) + 2 * PAD
        g.isl[i]['ppm'] = ppm
        g.isl[i]['rot'] = h > w
        g.isl[i]['wh'] = (h, w) if h > w else (w, h)


def _pack_global(gs):
    """first-fit-decreasing shelf packing of every island of every model into the atlas; returns used height or None"""
    items = []
    for gi, g in enumerate(gs):
        for i in _island_boxes(g):
            w, h = g.isl[i]['wh']
            if w > ATLAS: return None
            items.append((h, w, gi, i))
    items.sort(key=lambda t: (-t[0], -t[1]))
    rows = []; y = 0
    for h, w, gi, i in items:
        isl = gs[gi].isl[i]
        for r in rows:
            if h <= r[1] and r[2] + w <= ATLAS:
                isl['pos'] = (r[2], r[0]); r[2] += w; break
        else:
            if y + h > ATLAS: return None
            rows.append([y, h, w]); isl['pos'] = (0, y); y += h
    return y


def layout(gs, log=print):
    """choose the largest global density scale at which every island of every model fits in the atlas.
    Islands are unique and non-overlapping; each model's painting context is the row range its islands occupy"""
    def trial(scale):
        for g in gs: _isl_wh(g, scale)
        return _pack_global(gs)
    lo, hi = 0.2, 2.0
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        if trial(mid) is not None: lo = mid
        else: hi = mid
    scale = lo
    used = trial(scale)
    for gi, g in enumerate(gs):
        g.mid = gi; g.scale = scale
        bb = _island_boxes(g); g.UVpx = []
        for f, i in zip(g.UV, g.I):
            b = bb[i]; px, py = g.isl[i]['pos']; ppm = g.isl[i]['ppm']; rot = g.isl[i]['rot']
            if rot: g.UVpx.append([(px + PAD + (v - b[1]) * ppm, py + PAD + (b[2] - u) * ppm) for u, v in f])
            else: g.UVpx.append([(px + PAD + (u - b[0]) * ppm, py + PAD + (v - b[1]) * ppm) for u, v in f])
        ys = [g.isl[i]['pos'][1] for i in bb]; ye = [g.isl[i]['pos'][1] + g.isl[i]['wh'][1] for i in bb]
        g.rect = (0, min(ys), ATLAS, max(ye) - min(ys))
    log('atlas scale %.3f, rows used %d / %d' % (scale, used, ATLAS))
    for g in gs:
        px = sum(g.isl[i]['wh'][0] * g.isl[i]['wh'][1] for i in _island_boxes(g))
        log('   %-18s %6.1f kpx (%4.1f%%)  %.0f px/m' % (g.name, px / 1000.0, 100.0 * px / ATLAS / ATLAS, g.dens * scale))
    return scale


# =============================================================================================== rasterise position maps
class Maps:
    def __init__(s):
        N = ATLAS
        s.msk = np.zeros((N, N), bool); s.P = np.zeros((N, N, 3), np.float32); s.N = np.zeros((N, N, 3), np.float32)
        s.tag = np.full((N, N), -1, np.int16); s.ppm = np.zeros((N, N), np.float32)
        s.fid = np.full((N, N), -1, np.int32); s.isl = np.full((N, N), -1, np.int16); s.mid = np.full((N, N), -1, np.int16)


def raster(gs, mp):
    for g in gs:
        for fi, f in enumerate(g.F):
            pts = np.array([g.V[i] for i in f], np.float64)
            nrm = np.array(newell(pts.tolist()))
            if g.isl[g.I[fi]].get('fold'):
                pts[:, 0] = np.abs(pts[:, 0]); nrm[0] = abs(nrm[0])
            uv = np.array(g.UVpx[fi])
            ppm = g.isl[g.I[fi]]['ppm']
            for k in range(1, len(f) - 1):
                a, b, c = uv[0], uv[k], uv[k + 1]
                x0 = max(int(math.floor(min(a[0], b[0], c[0]))) - 1, 0); x1 = min(int(math.ceil(max(a[0], b[0], c[0]))) + 1, ATLAS)
                y0 = max(int(math.floor(min(a[1], b[1], c[1]))) - 1, 0); y1 = min(int(math.ceil(max(a[1], b[1], c[1]))) + 1, ATLAS)
                if x1 <= x0 or y1 <= y0: continue
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) < 1e-9: continue
                xs = np.arange(x0, x1) + 0.5; ys = np.arange(y0, y1) + 0.5
                X, Y = np.meshgrid(xs, ys)
                l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
                l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
                l3 = 1 - l1 - l2
                e = -0.02
                ins = (l1 >= e) & (l2 >= e) & (l3 >= e)
                if not ins.any(): continue
                sl = (slice(y0, y1), slice(x0, x1))
                P = l1[..., None] * pts[0] + l2[..., None] * pts[k] + l3[..., None] * pts[k + 1]
                mp.P[sl][ins] = P[ins]; mp.N[sl][ins] = nrm; mp.msk[sl][ins] = True
                mp.tag[sl][ins] = g.T[fi]; mp.ppm[sl][ins] = ppm; mp.fid[sl][ins] = fi; mp.isl[sl][ins] = g.I[fi]; mp.mid[sl][ins] = g.mid


def dilate(mp, n=PAD - 1):
    arrs = [mp.P, mp.N, mp.tag, mp.ppm, mp.fid, mp.isl, mp.mid]
    for _ in range(n):
        new = np.zeros_like(mp.msk)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sm = np.roll(mp.msk, (dy, dx), (0, 1))
            take = sm & ~mp.msk & ~new
            if not take.any(): continue
            for a in arrs: a[take] = np.roll(a, (dy, dx), (0, 1))[take]
            new |= take
        mp.msk |= new


# =============================================================================================== noise / painting helpers
def _h3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761 & 0xffffffff)
    h = h & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    h = h ^ (h >> 16)
    return (h & 0xffff) / 65535.0


def vn3(p, f, seed=0):
    """value noise 0..1 on (k,3) positions; f = lattice frequency (1/m), scalar or 3-vector"""
    q = p.astype(np.float64) * np.asarray(f, np.float64)
    i = np.floor(q).astype(np.int64); t = q - i
    t = t * t * (3 - 2 * t)
    out = 0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                out = out + w * _h3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fb3(p, f, octv=3, seed=0, gain=0.5):
    out = 0; amp = 1.0; tot = 0.0
    for o in range(octv):
        out = out + amp * vn3(p, np.asarray(f) * 2 ** o, seed + 17 * o); tot += amp; amp *= gain
    return out / tot


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def L(c):
    return T.lin(np.asarray(c, float))


def mixc(a, b, t):
    t = np.asarray(t)
    if t.ndim == 1: t = t[:, None]
    return a * (1 - t) + b * t


def render_text(jobs):
    """jobs: [{'w','h','items':[{'t','size','x','y','anchor','font','fill','rot'}]}] -> list of float arrays (h, w), row 0 = bottom"""
    d = C.WORK + 'props_test/'
    os.makedirs(d, exist_ok=True)
    jp = d + 'textjobs.json'
    json.dump(jobs, open(jp, 'w'))
    script = d + 'textjobs.py'
    open(script, 'w').write(r'''
import sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
jobs = json.load(open(sys.argv[1]))
FONTS = {'bold': ('@BOLD@', 0), 'serif': ('@SERIF@', 0)}
for k, j in enumerate(jobs):
    im = Image.new('L', (j['w'], j['h']), 0)
    for it in j['items']:
        path, idx = FONTS[it.get('font', 'bold')]
        f = ImageFont.truetype(path, int(it['size']), index=idx)
        layer = Image.new('L', (j['w'], j['h']), 0)
        d = ImageDraw.Draw(layer)
        d.text((it['x'], it['y']), it['t'], font=f, fill=int(it.get('fill', 255)), anchor=it.get('anchor', 'mm'))
        if it.get('rot'): layer = layer.rotate(it['rot'], center=(it['x'], it['y']), resample=Image.BICUBIC)
        im = Image.fromarray(np.maximum(np.asarray(im), np.asarray(layer)))
    np.save(sys.argv[2] + '%d.npy' % k, np.asarray(im, np.float32)[::-1] / 255.0)
'''.replace('@BOLD@', FONT_BOLD).replace('@SERIF@', FONT_SERIF))
    subprocess.run([PY_TEXT, script, jp, d + 'text_'], check=True)
    return [np.load(d + 'text_%d.npy' % k) for k in range(len(jobs))]


# =============================================================================================== painting context
class Ctx:
    def __init__(s, g, mp):
        x, y, w, h = g.rect
        s.g = g; s.x, s.y, s.w, s.h = x, y, w, h
        sl = (slice(y, y + h), slice(x, x + w)); s.sl = sl
        s.msk = mp.msk[sl] & (mp.mid[sl] == g.mid); s.P = mp.P[sl].copy(); s.N = mp.N[sl].copy(); s.tag = mp.tag[sl].copy()
        s.ppm = mp.ppm[sl].copy(); s.fid = mp.fid[sl].copy(); s.isl = mp.isl[sl].copy()
        s.A = np.full((h, w, 3), 0.18, np.float32); s.H = np.zeros((h, w), np.float32); s.R = np.full((h, w), 0.85, np.float32); s.Mt = np.zeros((h, w), np.float32); s.O = np.ones((h, w), np.float32)
        s.info = g.info

    def sel(s, *tags):
        m = np.zeros(s.msk.shape, bool)
        for t in tags: m |= (s.tag == t)
        return m & s.msk

    def put(s, sel, A=None, R=None, Mt=None, H=None, O=None):
        if A is not None: s.A[sel] = A
        if R is not None: s.R[sel] = R
        if Mt is not None: s.Mt[sel] = Mt
        if H is not None: s.H[sel] = H
        if O is not None: s.O[sel] = O


def weather(ctx, sel, base, seed=1, rust=0.5, moss=0.3, bleach=0.3, streak=0.4, leaf=0.0, zlow=0.0, zspan=1.0,
            rough=0.62, rust_cols=None, dirt=0.22, chip=1.0, pit=0.0012, patina=None, scab=1.0, fade=None):
    """sun-bleached, scabbed, rusted, mossy painted metal.  base: linear rgb.  Writes ctx.A/R/Mt/H on `sel`;
    returns (rust mask, moss mask) arrays on sel"""
    p = ctx.P[sel].astype(np.float64); n = ctx.N[sel].astype(np.float64)
    k = len(p)
    if k == 0: return None, None
    up = np.clip(n[:, 2], 0, 1); side = np.sqrt(np.clip(1 - up * up, 0, 1))
    big = fb3(p, 0.8, 3, seed); mid = fb3(p, 2.4, 4, seed + 5); fine = fb3(p, 22.0, 2, seed + 9); micro = vn3(p, 85.0, seed + 11)
    big = np.clip((big - 0.5) * 1.7 + 0.5, 0, 1); mid = np.clip((mid - 0.5) * 1.5 + 0.5, 0, 1)
    lowness = np.clip(1 - (p[:, 2] - zlow) / max(zspan, 1e-3), 0, 1) ** 1.5
    col = np.tile(np.asarray(base, float), (k, 1))
    lum = (col * np.array([0.3, 0.55, 0.15])).sum(1, keepdims=True)
    # chalking: sun-facing, upward surfaces fade towards a dusty pale version of the paint
    fd = np.asarray(0.75 if fade is None else fade)
    chalk = np.clip(bleach * (0.35 + 0.65 * up), 0, 1)
    col = mixc(col, np.repeat(lum, 3, 1) * 1.10 * np.array([1.0, 0.98, 0.92]) + 0.015, chalk * 0.55)
    col = col * (0.90 + 0.18 * mid)[:, None]
    # long vertical streaks (water runs) and dirt pooling low
    stk = 0.65 * vn3(p, np.array([14.0, 14.0, 1.5]), seed + 21) + 0.35 * vn3(p, np.array([5.0, 5.0, 0.8]), seed + 22)
    stk = sstep(0.50, 0.85, stk) * (0.35 + 0.65 * side)
    dirtc = L((0.26, 0.22, 0.17))
    col = mixc(col, col * 0.50 + dirtc * 0.30, np.clip(streak * stk * 0.8 + dirt * lowness * (0.3 + big), 0, 0.85))
    mil = sstep(0.56, 0.9, vn3(p, np.array([9.0, 9.0, 1.1]), seed + 23)) * (0.3 + 0.7 * side) * sstep(0.2, 0.7, fb3(p, 1.3, 2, seed + 24))
    col = mixc(col, col * 0.45 + L((0.06, 0.08, 0.05)) * 0.5, np.clip(mil * (0.25 + 0.5 * streak), 0, 0.6))
    # rust scabs: ragged blobs that start low, on seams (fine noise) and along the streaks
    score = 0.50 * big + 0.28 * mid + 0.20 * up + 0.50 * lowness + 0.30 * (stk - 0.3) * streak + scab * (0.13 * (fine - 0.5) + 0.06 * (micro - 0.5))
    thr = 1.00 - 0.60 * rust
    rm = sstep(thr - 0.03, thr + 0.03, score) * (1.0 if rust > 0 else 0.0)
    halo = sstep(thr - 0.10, thr - 0.02, score) * (1 - rm)          # lifting, chalky paint round a scab
    ring = rm * (1 - sstep(thr + 0.03, thr + 0.11, score))          # fresh orange rim of the scab
    if rust_cols is None:
        rust_cols = (L((0.17, 0.075, 0.04)), L((0.42, 0.20, 0.075)), L((0.30, 0.22, 0.15)))
    tone = sstep(0.30, 0.75, 0.55 * mid + 0.45 * fine)
    rc = mixc(rust_cols[0], rust_cols[1], tone)
    rc = mixc(rc, rust_cols[1] * 1.15, ring * 0.6)
    rc = mixc(rc, rust_cols[2], 0.40 * sstep(0.55, 0.8, micro) * np.ones(k))
    col = mixc(col, col * 0.80 + 0.06, halo * 0.8)
    col = mixc(col, rc, rm)
    # moss: only in the places water sits (low, flat, shaded creases), patchy
    mshape = 0.55 * fb3(p, 2.0, 3, seed + 31) + 0.30 * up + 0.30 * lowness + 0.10 * rm + 0.12 * (fine - 0.5)
    mm = sstep(0.84 - 0.55 * moss, 1.00 - 0.55 * moss, mshape) * sstep(0.35, 0.8, up) * (moss > 0)
    mcol = mixc(T.MOSS_D, T.MOSS, sstep(0.3, 0.8, fine))
    mcol = mixc(mcol, L((0.34, 0.40, 0.17)), 0.35 * micro)
    col = mixc(col, mcol * 0.62, mm * 0.85)
    # fallen leaves (litter) on horizontal faces: small flat brown/olive flakes
    if leaf > 0:
        lf = vn3(p, np.array([30.0, 30.0, 30.0]), seed + 41)
        lm = sstep(0.60, 0.66, lf) * sstep(0.45, 0.85, up) * sstep(0.35, 0.65, fb3(p, 1.6, 2, seed + 43) + leaf - 0.5)
        lc = mixc(L((0.36, 0.22, 0.085)), L((0.27, 0.26, 0.09)), sstep(0.3, 0.8, vn3(p, 55.0, seed + 47)))
        lc = lc * (0.8 + 0.4 * vn3(p, 140.0, seed + 49))[:, None]
        col = mixc(col, lc, lm * 0.95)
        mm = np.maximum(mm, lm)
    R = rough + 0.12 * (mid - 0.5) + 0.18 * chalk
    R = R * (1 - rm) + (0.90 + 0.06 * micro) * rm
    R = R * (1 - mm) + 0.97 * mm
    edgeb = rm * (1 - rm) * 4
    Mt = 0.02 * (1 - rm) + 0.06 * rm + 0.22 * np.clip(edgeb - 0.7, 0, 1) * (1 - mm)
    H = (-pit * rm * (0.4 + fine) + 0.0010 * ring - 0.0006 * edgeb + 0.004 * mm * (0.4 + micro)
         + 0.0005 * (micro - 0.5) - 0.0008 * halo)
    ctx.A[sel] = np.clip(col, 0, 1); ctx.R[sel] = np.clip(R, 0.05, 1); ctx.Mt[sel] = Mt; ctx.H[sel] = H
    return rm, mm


def spots(P, f, seed, thr):
    return sstep(thr, thr + 0.07, vn3(P, f, seed))


# =============================================================================================== mesh output
def make_object(g, col):
    """Blender object from a Geo (vertices welded, smooth with sharp edges by angle, UVs in atlas space)"""
    me = bpy.data.meshes.new(g.name)
    me.from_pydata(g.V, [], g.F)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    li = 0
    for fi, p in enumerate(me.polygons):
        for j, lo in enumerate(p.loop_indices):
            x, y = g.UVpx[fi][j]
            uvl.data[lo].uv = (x / ATLAS, y / ATLAS)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.faces.ensure_lookup_table()
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if a.normal.angle(b.normal, 0) > math.radians(36): e.smooth = False
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    me.materials.append(M.make('props'))
    ob = bpy.data.objects.new(g.name, me)
    col.objects.link(ob)
    ob['collide'] = [[float(v) for v in b] for b in g.boxes]
    ob['boxes'] = ob['collide']
    return ob


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# =============================================================================================== vehicles
def _ip(table, y):
    ys = [t[0] for t in table]
    return [float(np.interp(y, ys, [t[k] for t in table])) for k in range(1, len(table[0]))]


def _ring(S, y):
    """15 points p0..p14 (right wall up, over the top, left wall down) + u arc coordinates"""
    zb, ws = _ip(S['prof'], y)
    w = S['w'] * ws
    zu = S['zu']
    L2 = S['L'] / 2
    d = min(L2 - y, y + L2)
    zu += S.get('ramp', 0.16) * max(0.0, 1 - d / 0.4) ** 2
    for (yw, R, sag) in S['axles']:
        Ra = R + S.get('arch_gap', 0.10)
        dd = abs(y - yw)
        if dd < Ra:
            ztop = (R - sag) + R + 0.07
            zu = max(zu, S['zu'] + (ztop - S['zu']) * math.sqrt(1 - (dd / Ra) ** 2) ** 0.85)
    zu = min(zu, zb - 0.28)
    cr = S.get('crown', 0.03)
    z3 = min(max(zu + 0.22, zb - 0.17), zb - 0.06)
    Rt = [(0, zu), (w * 0.86, zu), (w * 0.975, zu + 0.09), (w, z3), (w - 0.06, zb),
          (w * 0.80, zb + 0.5 * cr), (w * 0.42, zb + 0.85 * cr), (0, zb + cr)]
    pts = [V3((x, y, z)) for x, z in Rt] + [V3((-x, y, z)) for x, z in Rt[6:0:-1]] + [V3((0, y, Rt[0][1]))]
    U = [0.0] * 15
    a = 0.0
    for j in range(6, -1, -1):
        a += (pts[j + 1] - pts[j]).length; U[j] = a
    a = 0.0
    for j in range(8, 15):
        a += (pts[j] - pts[j - 1]).length; U[j] = -a
    return {'y': y, 'P': pts, 'U': U, 'zb': zb, 'w': w}


def _stations(S):
    ys = set(t[0] for t in S['prof'])
    ys.add(S['cab'][0]); ys.add(S['cab'][1])
    for (yw, R, sag) in S['axles']:
        Ra = R + S.get('arch_gap', 0.10)
        for f in (-1.0, -0.82, -0.5, 0.0, 0.5, 0.82, 1.0):
            ys.add(yw + f * Ra)
    for yy in S.get('extra_y', []): ys.add(yy)
    ys = sorted(ys)
    out = [ys[0]]
    for y in ys[1:]:
        if y - out[-1] > 0.025: out.append(y)
    return out


def _f(u):
    return abs(u) if FOLD else u


def lower_body(g, S):
    """lofted lower body with wheel arches, open cabin tub and interior"""
    ys = _stations(S)
    rings = [_ring(S, y) for y in ys]
    isl = g.island(1.0); isl_u = g.island(0.3)
    if FOLD: g.isl[isl]['fold'] = True; g.isl[isl_u]['fold'] = True
    n = len(rings)
    V = [[0.0] * 15 for _ in range(n)]
    for i in range(1, n):
        for j in range(15):
            V[i][j] = V[i - 1][j] + (rings[i]['P'][j] - rings[i - 1]['P'][j]).length
    ycf, ycr = S['cab']          # cabin front / rear boundary (ycf > ycr)
    sill = {1: g.island(0.5), -1: g.island(0.5)}
    xi_off = 0.12
    doors = S.get('doors', [])   # [(y0, y1, side)]  side +1 right / -1 left: wall above the step is open
    for i in range(n - 1):
        A = rings[i]; B = rings[i + 1]
        ym = 0.5 * (A['y'] + B['y'])
        cab = ycr < ym < ycf
        for k in range(14):
            if cab and 4 <= k <= 9: continue
            if k in (2, 3, 10, 11) or k in (1, 12):
                skip = False
                for (d0, d1, sd) in doors:
                    if d0 < ym < d1 and ((sd > 0 and k in (2, 3)) or (sd < 0 and k in (10, 11))): skip = True
                if skip: continue
            pts = [A['P'][k], B['P'][k], B['P'][k + 1], A['P'][k + 1]]
            uv = [(_f(A['U'][k]), V[i][k]), (_f(B['U'][k]), V[i + 1][k]), (_f(B['U'][k + 1]), V[i + 1][k + 1]), (_f(A['U'][k + 1]), V[i][k + 1])]
            g.face(pts, uv, UNDER if k in (0, 13) else PAINT, isl_u if k in (0, 13) else isl)
        if cab:
            for sd in (1, -1):
                jo = 4 if sd > 0 else 10
                po0 = A['P'][jo]; po1 = B['P'][jo]
                xi0 = sd * (A['w'] - xi_off); xi1 = sd * (B['w'] - xi_off)
                pi0 = V3((xi0, A['y'], A['zb'])); pi1 = V3((xi1, B['y'], B['zb']))
                pts = [po0, po1, pi1, pi0] if sd > 0 else [po0, pi0, pi1, po1]
                g.face(pts, planar(pts, (0, 0, 1), (0, ycr, 0)), PAINT, sill[sd])
    # caps: rear (normal -y, ring order is ccw seen from behind) and front (reversed)
    P0 = rings[0]['P'][:14]; P1 = rings[-1]['P'][:14]
    pts = P0[0:5] + P0[10:14] if S.get('open_rear', False) else list(P0)
    g.face(pts, [(p.x, p.z) for p in pts], PAINT, g.island(1.0))
    pts = (P1[0:5] + P1[10:14] if S.get('open_front', False) else list(P1))[::-1]
    g.face(pts, [(-p.x, p.z) for p in pts], PAINT, g.island(1.0))
    # tub interior
    zf = S['floor']
    xi = S['w'] - xi_off
    iw = g.island(0.4)
    y0, y1 = ycr, ycf
    zbm = _ip(S['prof'], 0.5 * (ycr + ycf))[0]
    g.face([V3((xi, y1, zf)), V3((xi, y0, zf)), V3((xi, y0, zbm)), V3((xi, y1, zbm))], planar([V3((xi, y1, zf)), V3((xi, y0, zf)), V3((xi, y0, zbm)), V3((xi, y1, zbm))], (-1, 0, 0), (xi, y1, zf)), INT, iw)
    pl = [V3((-xi, y0, zf)), V3((-xi, y1, zf)), V3((-xi, y1, zbm)), V3((-xi, y0, zbm))]
    g.face(pl, planar(pl, (1, 0, 0), (-xi, y0, zf), (1.2, 0)), INT, iw)
    pf = [V3((-xi, y0, zf)), V3((xi, y0, zf)), V3((xi, y1, zf)), V3((-xi, y1, zf))]
    g.face(pf, planar(pf, (0, 0, 1), (-xi, y0, zf), (2.4, 0)), INT, iw)
    zbf = _ip(S['prof'], ycf)[0]; zbr = _ip(S['prof'], ycr)[0]
    pw = [V3((-xi, ycf, zf)), V3((xi, ycf, zf)), V3((xi, ycf, zbf)), V3((-xi, ycf, zbf))]
    g.face(pw, planar(pw, (0, -1, 0), (-xi, ycf, zf), (0, 1.2)), INT, iw)
    pw = [V3((xi, ycr, zf)), V3((-xi, ycr, zf)), V3((-xi, ycr, zbr)), V3((xi, ycr, zbr))]
    g.face(pw, planar(pw, (0, 1, 0), (xi, ycr, zf), (4.0, 1.2)), INT, iw)
    return rings


def roof_plate(g, stations, section, thick=0.04, tag=PAINT, m=1.0, wscale=None):
    """double skinned roof. stations: [(y, dz, ws)] rear->front; section: [(x, z)] left->right at ws=1"""
    io = g.island(m); ii = g.island(0.4)
    ns = len(stations); nk = len(section)
    def pt(i, k, d=0.0):
        y, dz, ws = stations[i]
        x, z = section[k]
        return V3((x * ws, y, z + dz - d))
    for i in range(ns - 1):
        for k in range(nk - 1):
            a = pt(i, k); b = pt(i, k + 1); c = pt(i + 1, k + 1); d = pt(i + 1, k)
            g.face([a, b, c, d], planar([a, b, c, d], (0, 0, 1), (0, stations[0][0], 0), (2.0, 0)), tag, io)
            a2 = pt(i, k, thick); b2 = pt(i, k + 1, thick); c2 = pt(i + 1, k + 1, thick); d2 = pt(i + 1, k, thick)
            g.face([a2, d2, c2, b2], planar([a2, d2, c2, b2], (0, 0, -1), (0, stations[0][0], 0), (0, 0)), INT, ii)
        # side edges
        for sd, kk in ((1, nk - 1), (-1, 0)):
            a = pt(i, kk); b = pt(i + 1, kk); a2 = pt(i, kk, thick); b2 = pt(i + 1, kk, thick)
            pts = [a2, b2, b, a] if sd > 0 else [a, b, b2, a2]
            g.face(pts, planar(pts, (sd, 0, 0), (0, 0, 0), (0, 0)), tag, ii)
    for (i, sd) in ((0, -1), (ns - 1, 1)):
        for k in range(nk - 1):
            a = pt(i, k); b = pt(i, k + 1); a2 = pt(i, k, thick); b2 = pt(i, k + 1, thick)
            pts = [b2, a2, a, b] if sd > 0 else [a2, b2, b, a]
            g.face(pts, planar(pts, (0, sd, 0), (0, 0, 0), (0, 0)), tag, ii)


def pillar(g, poly, S, thick=0.05, tag=PAINT, m=1.0):
    """poly: (y, z) pairs ccw seen from the right side (y to the right, z up); both sides are made"""
    zb = S['gh']['zb']; zt = S['gh']['zt']; wb = S['gh']['wb']; wr = S['gh']['wr']
    def xo(z): return wb + (wr - wb) * min(max((z - zb) / max(zt - zb, 1e-3), 0.0), 1.0)
    for sd in (1, -1):
        pts = [V3((sd * xo(z), y, z)) for (y, z) in poly]
        if sd < 0: pts = pts[::-1]
        plate(g, pts, (-sd * thick, 0, 0), tag, m)


def wheel(g, cx, cy, R, hw, side, sag, rim_r, n=10, phase=0.0, m=0.6):
    zax = R - sag
    c = V3((cx, cy, zax))
    s = 1 if side > 0 else -1
    prof = [(0, -hw * 0.9), (R, -hw * 0.6), (R, hw * 0.6), (R * 0.93, hw), (rim_r, hw * 0.85), (0, hw * 0.5)]
    tags = [UNDER, TYRE, TYRE, TYRE, RIM]

    def adj(p):
        dz = p.z - zax
        if dz < 0.0:
            f = zax / R
            dz = dz * f
            return V3((p.x, cy + (p.y - cy) * (1.0 + 1.6 * sag / R * min(1.0, -dz / R * 2)), max(zax + dz, 0.0)))
        return p
    ax = (s, 0, 0)
    lathe(g, c, ax, prof, n, tags, m, phase, adj, up=(0, 0, 1))
    g.info.setdefault('wheels', []).append((cx, cy, zax, R, s))


def seat(g, x, y, z0, wid=0.5, depth=0.5, back_h=0.55, face=1, tag=INT):
    """seat; face=+1 looks to +y"""
    box(g, (x, y, z0 + 0.09), (wid, depth, 0.18), tag, 0.35, faces='xXyYz')
    box(g, (x, y - face * (depth / 2 - 0.05), z0 + 0.18 + back_h / 2), (wid, 0.1, back_h), tag, 0.35, faces='xXyYz')
    return None


def mirror(g, x, y, z, sd):
    box(g, (x + sd * 0.07, y, z), (0.13, 0.05, 0.10), TRIM, 0.4, faces='xXyYzZ')
    box(g, (x + sd * 0.01, y, z - 0.03), (0.05, 0.04, 0.06), TRIM, 0.4, faces='yYz')


def car(name, S):
    g = Geo(name, S.get('dens', 90.0))
    g.info.update(S.get('info', {}))
    g.info['S'] = {k: v for k, v in S.items() if k not in ('dens',)}
    rings = lower_body(g, S)
    gh = S['gh']
    roof_plate(g, gh['roof_st'], gh['roof_sec'], 0.04)
    for (poly, th) in gh['pillars']:
        pillar(g, poly, S, th)
    # wheels
    for (yw, R, sag), hw, rim in zip(S['axles'], S['hw'], S['rim']):
        for sd in (1, -1):
            wheel(g, sd * (S['w'] - 0.14), yw, R, hw, sd, sag, rim, n=S.get('wn', 10), phase=0.31 + 0.5 * (yw > 0))
    for fn in S.get('extras', []): fn(g, S)
    for (c, r, d, dv) in S.get('dents', []):
        c = V3(c); dv = V3(dv)
        g.V = [tuple(V3(v) + dv * (d * math.exp(-((V3(v) - c).length / r) ** 2))) if (V3(v) - c).length < 2.2 * r else v for v in g.V]
    g.boxes = S.get('boxes', [])
    return g


# ------------------------------------------------------------------------------------------------ car specs
def _dash_and_seats(rows, dash, wheel_pos=None, rear_shelf=None):
    """interior furnishings: rows [(y, n_seats, width)], dash (ycf, depth, ztop)"""
    def fn(g, S):
        xi = S['w'] - 0.12 - 0.02
        zf = S['floor']
        ycf, dd, zt = dash
        box(g, (0, ycf - dd / 2, (zf + zt) / 2), (2 * xi, dd, zt - zf), INT, 0.35, faces='xXyz')
        for (y, nseat, wid) in rows:
            if nseat == 1:
                seat(g, 0, y, zf, wid, 0.5)
            else:
                span = 2 * xi - 0.1
                for k in range(nseat):
                    x = -span / 2 + span * (k + 0.5) / nseat
                    seat(g, x, y, zf, span / nseat - 0.05, 0.5)
        if wheel_pos:
            wx, wy, wz = wheel_pos
            cyl(g, (wx, wy, wz), (wx, wy - 0.035, wz + 0.016), 0.17, 0.17, 8, INT, 0.35, up=(0, 0, 1))
        if rear_shelf:
            y0, y1, z = rear_shelf
            pts = [V3((-xi, y0, z)), V3((xi, y0, z)), V3((xi, y1, z)), V3((-xi, y1, z))]
            g.face(pts, planar(pts, (0, 0, 1), (-xi, y0, z)), INT, g.island(0.35))
    return fn


def _mirrors(y, z):
    def fn(g, S):
        for sd in (1, -1): mirror(g, sd * (S['w'] - 0.01), y, z, sd)
    return fn


def _bumpers(zf=0.34, zr=0.36, hf=0.17, wf=0.94, wr=0.94, df=0.07, dr=0.07):
    def fn(g, S):
        L2 = S['L'] / 2; w = S['w']
        box(g, (0, L2 - 0.03, zf), (2 * w * wf, df * 2, hf), PAINT, 0.5, faces='xXyYz')
        box(g, (0, -L2 + 0.03, zr), (2 * w * wr, dr * 2, hf), PAINT, 0.5, faces='xXyYz')
    return fn


def _shards(front=None, rear=None):
    """a few triangles of glass still stuck in the screen frames. front/rear = (yb, zb, yt, zt, xb, xt)"""
    TR = [((-1, 0.0), (-0.55, 0.0), (-0.93, 0.38)), ((0.82, 0.0), (1.0, 0.0), (1.0, 0.26))]

    def fn(g, S):
        for pl, flip in ((front, False), (rear, True)):
            if pl is None: continue
            yb, zb, yt, zt, xb, xt = pl
            for ti, tri in enumerate(TR):
                if flip and ti % 2: continue
                pts = []
                for (u, v) in tri:
                    x = (xb + (xt - xb) * v) * u
                    pts.append(V3((x, yb + (yt - yb) * v, zb + (zt - zb) * v)))
                nrm = newell(pts)
                if (nrm.y < 0) != flip: pts = pts[::-1]
                isl = g.island(0.4)
                uv = planar(pts, nrm)
                g.face(pts, uv, GLASS, isl)
                g.face(pts[::-1], uv[::-1], GLASS, isl)
    return fn


def _roof_lamp(y, z, wd=0.52, ln=0.20, ht=0.17):
    def fn(g, S):
        box(g, (0, y, z + ht / 2), (wd, ln, ht), SIGN, 3.5, faces='yY')
        box(g, (0, y, z + ht / 2), (wd, ln, ht), SIGN, 0.8, faces='xXz')
        box(g, (0, y, z + 0.015), (wd * 0.7, ln * 0.8, 0.03), TRIM, 0.3, faces='xXyY')
        g.info['lamp'] = (y, z, wd, ln, ht)
    return fn


def _spec_common(S, zr, **kw):
    S.update(kw)
    return S


def sedan_spec(variant=0):
    zb = 0.95
    S = dict(L=4.7, w=0.875, zu=0.13, crown=0.03, floor=0.5,
             prof=[(-2.35, 0.80, 0.78), (-2.28, 0.89, 0.90), (-2.12, 0.96, 0.97), (-1.7, 0.99, 1.0), (-1.28, 0.99, 1.0),
                   (-0.9, 0.95, 1.0), (0.80, 0.95, 1.0), (1.25, 0.92, 1.0), (2.0, 0.86, 0.99), (2.28, 0.80, 0.93), (2.35, 0.76, 0.80)],
             cab=(0.80, -1.28), axles=[(1.35, 0.31, 0.08), (-1.35, 0.31, 0.08)], hw=[0.1, 0.1], rim=[0.19, 0.19], wn=12)
    zr = 1.43; zt = zr - 0.05
    S['gh'] = dict(zb=zb, zt=zt, wb=0.78, wr=0.69,
                   roof_st=[(-0.84, -0.07, 0.80), (-0.64, -0.014, 0.96), (-0.1, 0.0, 1.0), (0.06, -0.015, 0.95), (0.13, -0.07, 0.8)],
                   roof_sec=[(-0.69, zr - 0.05), (-0.42, zr - 0.006), (0.42, zr - 0.006), (0.69, zr - 0.05)],
                   pillars=[([(0.70, zb), (0.82, zb), (0.14, zt), (0.0, zt)], 0.09),
                            ([(-0.38, zb), (-0.24, zb), (-0.24, zt), (-0.38, zt)], 0.06),
                            ([(-1.28, zb), (-0.62, zb), (-0.62, zt), (-0.84, zt)], 0.07)])
    S['extras'] = [_dash_and_seats([(0.25, 2, 0.5), (-0.82, 3, 0.5)], (0.80, 0.42, 0.88), (0.38, 0.52, 0.99), (-1.28, -0.9, 0.9)),
                   _mirrors(0.62, 0.99), _bumpers(0.34, 0.36),
                   _shards((0.80, zb, 0.12, zt, 0.62, 0.52), (-1.28, zb, -0.84, zt, 0.6, 0.5))]
    S['boxes'] = [[0, 0.0, 0.5, 1.72, 4.6, 0.8], [0, -0.35, 1.2, 1.5, 1.7, 0.5]]
    S['dents'] = [[((0.1, 1.35, 0.95), 0.55, 0.05, (0, 0, -1)), ((0, -0.3, 1.43), 0.7, 0.035, (0, 0, -1)), ((0.86, -0.7, 0.65), 0.3, 0.045, (-1, 0, 0))],
                  [((-0.3, -1.7, 1.0), 0.5, 0.06, (0, 0, -1)), ((-0.87, 0.2, 0.7), 0.35, 0.05, (1, 0, 0)), ((0.3, 1.6, 0.9), 0.4, 0.03, (0, 0, -1))],
                  [((0, -0.2, 1.43), 0.9, 0.06, (0, 0, -1)), ((0.0, 2.3, 0.6), 0.35, 0.08, (0, -1, 0))]][variant % 3]
    S['info'] = dict(kind='sedan', doors=[(0.62, -0.30), (-0.30, -1.20)], cab_y=(0.80, -1.28), nose_zr=(0.3, 0.76), mould_z=0.56)
    return S


def taxi_spec(variant=0):
    S = sedan_spec()
    zb = 0.97; zr = 1.50; zt = zr - 0.05
    S['prof'] = [(-2.35, 0.84, 0.82), (-2.28, 0.94, 0.92), (-2.12, 1.0, 0.98), (-1.7, 1.02, 1.0), (-1.35, 1.02, 1.0),
                 (-0.9, 0.98, 1.0), (0.85, 0.98, 1.0), (1.25, 0.94, 1.0), (2.0, 0.88, 0.99), (2.28, 0.82, 0.93), (2.35, 0.78, 0.82)]
    S['cab'] = (0.85, -1.35)
    S['gh'] = dict(zb=zb, zt=zt, wb=0.80, wr=0.73,
                   roof_st=[(-1.00, -0.08, 0.82), (-0.82, -0.014, 0.97), (0.0, 0.0, 1.0), (0.2, -0.014, 0.96), (0.32, -0.08, 0.84)],
                   roof_sec=[(-0.73, zr - 0.05), (-0.45, zr - 0.006), (0.45, zr - 0.006), (0.73, zr - 0.05)],
                   pillars=[([(0.74, zb), (0.87, zb), (0.34, zt), (0.20, zt)], 0.09),
                            ([(-0.40, zb), (-0.26, zb), (-0.26, zt), (-0.40, zt)], 0.06),
                            ([(-1.35, zb), (-0.78, zb), (-0.80, zt), (-1.02, zt)], 0.07)])
    S['extras'] = [_dash_and_seats([(0.25, 2, 0.5), (-0.85, 3, 0.5)], (0.85, 0.42, 0.90), (0.38, 0.52, 1.01), (-1.35, -0.95, 0.9)),
                   _mirrors(0.66, 1.0), _bumpers(0.34, 0.36), _roof_lamp(-0.15, zr - 0.006),
                   _shards((0.85, zb, 0.32, zt, 0.64, 0.56), (-1.35, zb, -1.02, zt, 0.6, 0.52))]
    S['boxes'] = [[0, 0.0, 0.5, 1.72, 4.6, 0.85], [0, -0.2, 1.25, 1.55, 1.7, 0.55]]
    S['dents'] = [((0.3, 1.5, 0.9), 0.5, 0.04, (0, 0, -1)), ((0, -0.2, 1.5), 0.6, 0.03, (0, 0, -1)), ((-0.87, -0.8, 0.65), 0.3, 0.05, (1, 0, 0))]
    S['info'] = dict(kind='taxi', paint_hook=taxi_hook, doors=[(0.70, -0.30), (-0.30, -1.25)], cab_y=(0.85, -1.35), nose_zr=(0.3, 0.8), mould_z=0.56)
    return S


def kei_spec(variant=0):
    zb = 1.02; zr = 1.64; zt = zr - 0.05
    S = dict(L=3.4, w=0.74, zu=0.14, crown=0.02, floor=0.46,
             prof=[(-1.70, 0.86, 0.88), (-1.66, 0.97, 0.96), (-1.5, 1.02, 1.0), (-1.2, 1.02, 1.0), (0.78, 1.02, 1.0), (1.05, 0.93, 1.0),
                   (1.45, 0.86, 0.99), (1.62, 0.78, 0.94), (1.70, 0.70, 0.86)],
             cab=(0.78, -1.60), axles=[(1.17, 0.27, 0.07), (-1.10, 0.27, 0.07)], hw=[0.085, 0.085], rim=[0.165, 0.165], wn=12,
             ramp=0.12)
    S['gh'] = dict(zb=zb, zt=zt, wb=0.69, wr=0.64,
                   roof_st=[(-1.72, -0.15, 0.86), (-1.62, -0.03, 0.95), (-1.25, 0.0, 1.0), (0.30, 0.0, 1.0), (0.45, -0.03, 0.95), (0.54, -0.12, 0.86)],
                   roof_sec=[(-0.64, zr - 0.05), (-0.40, zr - 0.006), (0.40, zr - 0.006), (0.64, zr - 0.05)],
                   pillars=[([(0.70, zb), (0.80, zb), (0.56, zt), (0.44, zt)], 0.085),
                            ([(-0.18, zb), (-0.06, zb), (-0.06, zt), (-0.18, zt)], 0.055),
                            ([(-1.62, zb), (-1.18, zb), (-1.16, zt), (-1.62, zt)], 0.07)])
    S['extras'] = [_dash_and_seats([(0.20, 2, 0.45), (-0.78, 2, 0.45)], (0.78, 0.36, 0.92), (0.30, 0.46, 1.02)),
                   _mirrors(0.50, 1.04), _bumpers(0.34, 0.36, 0.15, 0.93, 0.93, 0.06, 0.06),
                   _shards((0.78, zb, 0.54, zt, 0.58, 0.54), (-1.62, zb, -1.70, zt, 0.58, 0.5))]
    S['boxes'] = [[0, 0.0, 0.5, 1.46, 3.3, 0.8], [0, -0.45, 1.3, 1.3, 1.9, 0.6]]
    S['dents'] = [((0.1, 1.3, 0.85), 0.4, 0.04, (0, 0, -1)), ((0, -0.5, 1.64), 0.6, 0.04, (0, 0, -1)), ((0.75, -0.3, 0.7), 0.3, 0.05, (-1, 0, 0))]
    S['info'] = dict(kind='kei', doors=[(0.64, -0.20), (-0.20, -0.95)], door_z0=0.33, cab_y=(0.78, -1.6), nose_zr=(0.3, 0.8), mould_z=0.60,
                     plate_col=(0.62, 0.50, 0.14))
    return S


def minivan_spec(variant=0):
    zb = 1.05; zr = 1.90; zt = zr - 0.06
    S = dict(L=4.7, w=0.85, zu=0.16, crown=0.025, floor=0.52,
             prof=[(-2.35, 0.86, 0.84), (-2.28, 0.98, 0.94), (-2.1, 1.05, 0.99), (-1.6, 1.07, 1.0), (-1.0, 1.05, 1.0), (1.45, 1.0, 1.0),
                   (1.75, 0.91, 1.0), (2.1, 0.82, 0.99), (2.30, 0.76, 0.93), (2.35, 0.72, 0.84)],
             cab=(1.45, -2.18), axles=[(1.45, 0.31, 0.08), (-1.40, 0.31, 0.08)], hw=[0.095, 0.095], rim=[0.185, 0.185], wn=12)
    S['gh'] = dict(zb=zb, zt=zt, wb=0.80, wr=0.74,
                   roof_st=[(-2.36, -0.24, 0.90), (-2.26, -0.05, 0.96), (-1.9, 0.0, 1.0), (0.65, 0.0, 1.0), (0.88, -0.04, 0.96), (1.0, -0.16, 0.86)],
                   roof_sec=[(-0.74, zr - 0.07), (-0.48, zr - 0.008), (0.48, zr - 0.008), (0.74, zr - 0.07)],
                   pillars=[([(1.38, zb), (1.50, zb), (0.98, zt), (0.80, zt)], 0.09),
                            ([(0.38, zb), (0.52, zb), (0.52, zt), (0.38, zt)], 0.06),
                            ([(-0.74, zb), (-0.62, zb), (-0.62, zt), (-0.74, zt)], 0.055),
                            ([(-2.18, zb), (-1.62, zb), (-1.70, zt), (-2.26, zt)], 0.08)])
    S['extras'] = [_dash_and_seats([(0.62, 2, 0.5), (-0.30, 2, 0.5), (-1.35, 3, 0.5)], (1.45, 0.5, 1.0), (0.80, 0.82, 1.1)),
                   _mirrors(1.12, 1.1), _bumpers(0.36, 0.38, 0.19, 0.93, 0.93, 0.07, 0.07),
                   _shards((1.45, zb, 0.98, zt, 0.7, 0.62), (-2.18, zb, -2.26, zt, 0.68, 0.62))]
    S['boxes'] = [[0, 0.0, 0.55, 1.68, 4.6, 0.9], [0, -0.35, 1.45, 1.55, 2.9, 0.9]]
    S['dents'] = [((0.0, 1.9, 0.85), 0.45, 0.05, (0, 0, -1)), ((0, -0.4, 1.9), 0.8, 0.05, (0, 0, -1)), ((-0.85, -0.9, 0.7), 0.4, 0.05, (1, 0, 0))]
    S['info'] = dict(kind='minivan', doors=[(1.32, 0.45), (0.38, -0.80)], door_z0=0.34, cab_y=(1.45, -2.18), nose_zr=(0.3, 0.84), mould_z=0.62)
    return S


# ------------------------------------------------------------------------------------------------ painters
class Flat:
    """flat (k,) views of a Ctx selection, with convenience blends"""
    def __init__(s, ctx, sel):
        s.ctx = ctx; s.sel = sel
        s.p = ctx.P[sel].astype(np.float64); s.n = ctx.N[sel].astype(np.float64)
        s.A = ctx.A[sel]; s.R = ctx.R[sel]; s.Mt = ctx.Mt[sel]; s.H = ctx.H[sel]
        s.x, s.y, s.z = s.p[:, 0], s.p[:, 1], s.p[:, 2]
        s.nx, s.ny, s.nz = s.n[:, 0], s.n[:, 1], s.n[:, 2]

    def blend(s, m, col=None, R=None, Mt=None, dH=0.0, setH=None):
        m = np.asarray(m, float)
        if col is not None: s.A = mixc(s.A, np.asarray(col, float) * np.ones((len(m), 3)), m)
        if R is not None: s.R = s.R * (1 - m) + R * m
        if Mt is not None: s.Mt = s.Mt * (1 - m) + Mt * m
        if setH is not None: s.H = s.H * (1 - m) + setH * m
        s.H = s.H + dH * m

    def commit(s):
        c = s.ctx; c.A[s.sel] = np.clip(s.A, 0, 1); c.R[s.sel] = s.R; c.Mt[s.sel] = s.Mt; c.H[s.sel] = s.H


def box_mask(F, x0, x1, y0, y1, z0, z1, soft=0.0):
    m = ((F.x >= x0) & (F.x <= x1) & (F.y >= y0) & (F.y <= y1) & (F.z >= z0) & (F.z <= z1))
    return m.astype(float)


def paint_interior(ctx, seed, moss=0.35):
    sel = ctx.sel(INT)
    if not sel.any(): return
    base = L((0.15, 0.13, 0.11))
    weather(ctx, sel, base, seed=seed + 3, rust=0.0, moss=moss, bleach=0.0, streak=0.2, leaf=0.45, dirt=0.3, rough=0.92)
    F = Flat(ctx, sel)
    fab = fb3(F.p, 9.0, 2, seed + 4)
    F.blend(sstep(0.4, 0.8, fab) * 0.5, L((0.22, 0.19, 0.15)))
    F.commit()


def paint_chrome(ctx, seed):
    sel = ctx.sel(CHROME)
    if sel.any():
        weather(ctx, sel, L((0.42, 0.42, 0.40)), seed=seed + 19, rust=0.65, moss=0.2, bleach=0.2, streak=0.4, dirt=0.35, rough=0.45)


def paint_rubber(ctx, seed):
    sel = ctx.sel(TYRE)
    if sel.any():
        rm, mm = weather(ctx, sel, L((0.045, 0.043, 0.040)), seed=seed + 7, rust=0.0, moss=0.5, bleach=0.5, streak=0.3, dirt=0.25, rough=0.88)
        F = Flat(ctx, sel)
        crack = sstep(0.55, 0.62, vn3(F.p, np.array([70.0, 70.0, 70.0]), seed + 8))
        F.blend(crack * 0.5, L((0.02, 0.02, 0.02)), dH=-0.0015)
        # perished grey bloom
        F.blend(sstep(0.5, 0.85, fb3(F.p, 5.0, 3, seed + 9)) * 0.5, L((0.13, 0.12, 0.105)))
        # tread blocks: rings of grooves around each wheel axis are drawn from the nearest wheel
        W = ctx.info.get('wheels', [])
        if W:
            best = np.full(len(F.y), 9.0); ang = np.zeros(len(F.y)); dist = np.zeros(len(F.y))
            for (cx, cy, cz, R, sd) in W:
                m = (F.x * sd > 0)
                dy = F.y - cy; dz = F.z - cz
                d = np.hypot(dy, dz)
                ok = m & (np.abs(F.y - cy) < R + 0.02) & (np.abs(F.x - cx) < 0.2)
                better = ok & (np.abs(d - R) < best)
                best = np.where(better, np.abs(d - R), best)
                ang = np.where(better, np.arctan2(dz, dy), ang)
            tread = (np.abs(F.nz) < 0.99) & (np.abs(F.nx) < 0.5)
            groove = (np.sin(ang * 22) > 0.55) & tread
            F.blend(groove.astype(float) * 0.5, L((0.02, 0.02, 0.02)), dH=-0.003)
        F.commit()
    sel = ctx.sel(RIM)
    if sel.any():
        rm, mm = weather(ctx, sel, L((0.20, 0.20, 0.19)), seed=seed + 12, rust=0.8, moss=0.15, bleach=0.1, streak=0.2, dirt=0.4, rough=0.7,
                         rust_cols=(L((0.15, 0.065, 0.035)), L((0.32, 0.15, 0.065)), L((0.26, 0.2, 0.14))))
        W = ctx.info.get('wheels', [])
        if W:
            F = Flat(ctx, sel)
            best = np.full(len(F.y), 9.0); rr = np.zeros(len(F.y)); ang = np.zeros(len(F.y))
            for (cx, cy, cz, R, sd) in W:
                ok = (F.x * sd > 0) & (np.abs(F.x - cx) < 0.2)
                d = np.hypot(F.y - cy, F.z - cz)
                better = ok & (d < best)
                best = np.where(better, d, best); rr = np.where(better, d, rr); ang = np.where(better, np.arctan2(F.z - cz, F.y - cy), ang)
            F.blend((rr < 0.05) * 0.8, L((0.34, 0.33, 0.30)), dH=0.004)
            for k in range(5):
                a = 2 * math.pi * k / 5
                bolt = np.hypot(rr * np.cos(ang) - 0.075 * math.cos(a), rr * np.sin(ang) - 0.075 * math.sin(a)) < 0.014
                F.blend(bolt * 1.0, L((0.03, 0.03, 0.03)), dH=-0.004)
            F.blend(((rr > 0.15) & (rr < 0.165)) * 0.6, L((0.05, 0.05, 0.05)))
            F.commit()
    sel = ctx.sel(UNDER)
    if sel.any():
        weather(ctx, sel, L((0.04, 0.032, 0.026)), seed=seed + 14, rust=0.7, moss=0.0, bleach=0.0, streak=0.0, dirt=0.3, rough=0.9)
    sel = ctx.sel(TRIM)
    if sel.any():
        weather(ctx, sel, L((0.07, 0.07, 0.065)), seed=seed + 16, rust=0.0, moss=0.35, bleach=0.7, streak=0.3, dirt=0.2, rough=0.8)


def _plate(F, x0, x1, z0, z1, col, seed):
    m = box_mask(F, x0, x1, -99, 99, z0, z1) if False else ((F.x >= x0) & (F.x <= x1) & (F.z >= z0) & (F.z <= z1)).astype(float)
    F.blend(m, col, R=0.55, dH=0.003)
    ch = sstep(0.55, 0.6, vn3(np.stack([F.x * 55, F.z * 90, F.x * 0], 1), 1.0, seed)) * (np.abs(((F.x - x0) / (x1 - x0) * 8) % 1 - 0.5) < 0.32)
    F.blend(m * ch * ((F.z > z0 + 0.04 * (z1 - z0)) & (F.z < z1 - 0.2 * (z1 - z0))) * 0.8, L((0.05, 0.05, 0.05)))
    edge = m * ((F.z < z0 + 0.012) | (F.z > z1 - 0.012) | (F.x < x0 + 0.012) | (F.x > x1 - 0.012))
    F.blend(edge, L((0.12, 0.12, 0.11)))


def paint_car(ctx):
    g = ctx.g; S = g.info['S']; pp = g.info['paint']; info = g.info
    L2 = S['L'] / 2; seed = pp['seed']
    sel = ctx.sel(PAINT)
    rm, mm = weather(ctx, sel, pp['base'], seed=seed, rust=pp['rust'], moss=pp['moss'], bleach=pp['bleach'], streak=0.55,
                     leaf=pp.get('leaf', 0.3), zlow=0.12, zspan=pp.get('zspan', 1.0), rough=0.6)
    F = Flat(ctx, sel)
    rust_c = L((0.34, 0.16, 0.075))
    sidew = (np.abs(F.nx) > 0.7)
    zb = S['gh']['zb']
    # door outlines
    for (d0, d1) in info.get('doors', []):
        zlo = info.get('door_z0', 0.30)
        for yy in (d0, d1):
            ln = sidew & (np.abs(F.y - yy) < 0.007) & (F.z > zlo) & (F.z < zb + 0.01)
            F.blend(ln.astype(float) * 0.9, L((0.02, 0.018, 0.015)), R=0.9, dH=-0.004)
        ln = sidew & (np.abs(F.z - zlo) < 0.007) & (F.y < d0) & (F.y > d1)
        F.blend(ln.astype(float) * 0.9, L((0.02, 0.018, 0.015)), R=0.9, dH=-0.004)
        hy = d1 + 0.09
        hd = sidew & (F.y > hy) & (F.y < hy + 0.15) & (F.z > zb - 0.13) & (F.z < zb - 0.09)
        F.blend(hd.astype(float), L((0.10, 0.095, 0.09)), R=0.5, Mt=0.15, dH=0.006)
    # body side moulding
    zm = info.get('mould_z', 0.56)
    ml = sidew & (np.abs(F.z - zm) < 0.016)
    F.blend(ml.astype(float) * 0.6, L((0.06, 0.06, 0.06)), dH=0.003)
    # front / rear faces
    zmin, zmax = info['nose_zr']; h = zmax - zmin
    kind = info.get('kind', 'sedan')
    fr = (F.ny > 0.7) & (F.y > L2 - 0.5)
    rr = (F.ny < -0.7) & (F.y < -L2 + 0.5)
    low = np.clip((zmin + 0.42 * h - F.z) / (0.06 * h + 1e-3), 0, 1)
    F.blend((fr | rr) * low * 0.85, L((0.075, 0.072, 0.068)), R=0.75)
    # headlamps: dark reflector bowls, glass long gone
    hl = fr & (np.abs(F.x) > S['w'] * 0.36) & (np.abs(F.x) < S['w'] * 0.80) & (F.z > zmin + 0.50 * h) & (F.z < zmin + 0.86 * h)
    hl = hl.astype(float)
    F.blend(hl, L((0.025, 0.027, 0.03)), R=0.35, Mt=0.2, dH=-0.02)
    bowl = hl * sstep(0.4, 0.9, fb3(F.p, 18.0, 2, seed + 61))
    F.blend(bowl * 0.5, L((0.16, 0.15, 0.13)), R=0.5)
    gr = fr & (np.abs(F.x) < S['w'] * 0.32) & (F.z > zmin + 0.44 * h) & (F.z < zmin + 0.80 * h)
    slat = (((F.z * 55) % 1) < 0.5)
    F.blend(gr * 0.9, L((0.04, 0.04, 0.04)), R=0.6, dH=-0.012)
    F.blend(gr * slat * 0.8, L((0.11, 0.10, 0.09)), R=0.6, dH=0.004)
    tl = rr & (np.abs(F.x) > S['w'] * 0.45) & (np.abs(F.x) < S['w'] * 0.92) & (F.z > zmin + 0.52 * h) & (F.z < zmin + 0.88 * h)
    F.blend(tl.astype(float), L((0.30, 0.055, 0.04)), R=0.4, dH=-0.01)
    F.blend(tl * sstep(0.5, 0.8, fb3(F.p, 14.0, 2, seed + 62)) * 0.7, L((0.12, 0.03, 0.03)))
    pc = info.get('plate_col', (0.60, 0.60, 0.55))
    for face in (fr, rr):
        sub = face
        pm = sub & (np.abs(F.x) < 0.17) & (F.z > zmin + 0.10 * h) & (F.z < zmin + 0.10 * h + 0.165)
        if pm.any():
            Fp = F
            m = pm.astype(float)
            F.blend(m, L(pc), R=0.55, dH=0.003)
            ch = sstep(0.52, 0.58, vn3(np.stack([F.x * 48, F.z * 85, F.x * 0 + (1 if face is fr else 2)], 1), 1.0, seed + 70))
            F.blend(m * ch * (np.abs(((F.x + 0.17) / 0.34 * 7) % 1 - 0.5) < 0.3) * ((F.z > zmin + 0.10 * h + 0.04) & (F.z < zmin + 0.10 * h + 0.13)) * 0.8, L((0.05, 0.05, 0.05)))
    F.commit()
    # roof lamp / extras left to the model hooks
    for tg in (SIGN, LAMP, PLAS, STEEL):
        _metal(tg, **TAGK[tg])(ctx, seed, {})
    paint_glass(ctx, seed, {})
    paint_chrome(ctx, seed)
    paint_interior(ctx, seed)
    paint_rubber(ctx, seed)
    if 'paint_hook' in info: info['paint_hook'](ctx, rm, mm)


PAINTERS = {}
BUILDERS = {}
REGIONS = {}
_G = None


def _car_builder(name, specf, paint, **kw):
    def b():
        S = specf(**kw)
        g = car(name, S)
        g.info['paint'] = paint
        return g
    return b


def taxi_hook(ctx, rm, mm):
    g = ctx.g
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    side = np.abs(F.nx) > 0.7
    k = np.floor(F.y / 0.065).astype(int) + np.floor((F.z - 0.60) / 0.065).astype(int)
    band = side & (F.z > 0.60) & (F.z < 0.73) & (F.y > -1.9) & (F.y < 1.2) & (k % 2 == 0)
    keep = 1.0 - 0.75 * (rm if rm is not None else 0)
    F.blend(band * keep * 0.95, L((0.07, 0.15, 0.36)), R=0.5)
    F.commit()
    sel = ctx.sel(SIGN)
    if sel.any():
        F = Flat(ctx, sel)
        y0, z0, wd, ln, ht = g.info['lamp']
        weather(ctx, sel, L((0.58, 0.55, 0.38)), seed=5, rust=0.0, moss=0.3, bleach=0.5, streak=0.5, dirt=0.5, rough=0.5)
        F = Flat(ctx, sel)
        fr = F.ny > 0.7; bk = F.ny < -0.7; sd = np.abs(F.nx) > 0.7
        cv = text_canvas(wd, ht, 300, [dict(t='TAXI', x=wd * 0.5, y=ht * 0.52, h=ht * 0.62, anchor='mm', font='bold')])
        cv2 = text_canvas(ln, ht, 300, [dict(t='空車', x=ln * 0.5, y=ht * 0.5, h=ht * 0.5, anchor='mm', font='bold')])
        wmk = np.clip(wear_mask(F, 5, 0.6), 0, 1)
        a = canvas_sample(F, fr, cv, 300, np.array([wd / 2, y0, z0]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]))
        a += canvas_sample(F, bk, cv, 300, np.array([-wd / 2, y0, z0]), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))
        F.blend(np.clip(a, 0, 1) * wmk, L((0.10, 0.10, 0.09)), R=0.6)
        F.commit()


def _reg_car(name, specf, paint, dens=64.0, painter=None):
    def b():
        S = specf(); S['dens'] = dens
        g = car(name, S); g.info['paint'] = paint
        return g
    BUILDERS[name] = b
    PAINTERS[name] = painter or paint_car


_reg_car('car_sedan', sedan_spec, dict(base=L((0.62, 0.59, 0.50)), rust=0.55, moss=0.20, bleach=0.55, seed=11, leaf=0.5))
_reg_car('car_sedan_silver', lambda: sedan_spec(1), dict(base=L((0.46, 0.48, 0.49)), rust=0.5, moss=0.2, bleach=0.55, seed=12, leaf=0.5))
_reg_car('car_sedan_blue', lambda: sedan_spec(2), dict(base=L((0.07, 0.12, 0.26)), rust=0.55, moss=0.2, bleach=0.6, seed=13, leaf=0.5))
_reg_car('car_kei', kei_spec, dict(base=L((0.55, 0.62, 0.66)), rust=0.55, moss=0.2, bleach=0.5, seed=21, leaf=0.4))
_reg_car('car_minivan', minivan_spec, dict(base=L((0.56, 0.55, 0.50)), rust=0.55, moss=0.2, bleach=0.5, seed=31, leaf=0.4))
_reg_car('taxi', taxi_spec, dict(base=L((0.74, 0.62, 0.26)), rust=0.5, moss=0.2, bleach=0.5, seed=41, leaf=0.4))


# =============================================================================================== more primitives
def poly(g, pts, tag, m=1.0, double=False, isl=None, tag_back=None):
    """one flat polygon (ccw seen from the front); double = a reversed copy for the back"""
    pts = [V3(p) for p in pts]; n = newell(pts)
    uv = planar(pts, n)
    mn = (min(u[0] for u in uv), min(u[1] for u in uv)); mx = max(u[0] for u in uv)
    uv = [(a - mn[0], b - mn[1]) for a, b in uv]
    if isl is None: isl = g.island(m)
    g.face(pts, uv, tag, isl)
    if double:
        W = mx - mn[0] + 0.03
        g.face(pts[::-1], [(a + W, b) for a, b in uv][::-1], tag if tag_back is None else tag_back, isl)
    return isl


def extrude(g, poly2, axis, a0, a1, tag, m=1.0, tags=None, isl=None, ms=None):
    """prism: 2D polygon (p, q) extruded along an axis between a0 and a1.
    axis 'y': (p, q) = (x, z);  'x': (y, z);  'z': (x, y).  tags: dict cap0 / cap1 / side"""
    P = [(float(a), float(b)) for a, b in poly2]
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    if area < 0: P = P[::-1]

    def M(p, q, a):
        return V3((p, a, q)) if axis == 'y' else (V3((a, p, q)) if axis == 'x' else V3((p, q, a)))
    d = {'y': V3((0, 1, 0)), 'x': V3((1, 0, 0)), 'z': V3((0, 0, 1))}[axis]
    tg = {'cap0': tag, 'cap1': tag, 'side': tag}
    if tags: tg.update(tags)
    isls = {}
    if ms:
        for kk in ('cap0', 'cap1', 'side'): isls[kk] = g.island(ms.get(kk, m))
    else:
        if isl is None: isl = g.island(m)
        for kk in ('cap0', 'cap1', 'side'): isls[kk] = isl
    pm = min(p for p, q in P); qm = min(q for p, q in P)
    W = max(p for p, q in P) - pm
    for cap, a, sg in ((0, a0, -1), (1, a1, 1)):
        pts = [M(p, q, a) for p, q in P]
        uv = [(p - pm + (cap * (W + 0.03) if not ms else 0), q - qm) for p, q in P]
        if newell(pts).dot(d) * sg < 0: pts = pts[::-1]; uv = uv[::-1]
        g.face(pts, uv, tg['cap%d' % cap], isls['cap%d' % cap])
    x = 0.0; W3 = abs(a1 - a0)
    for i in range(len(P)):
        j = (i + 1) % len(P)
        (p0, q0), (p1, q1) = P[i], P[j]
        l = math.hypot(p1 - p0, q1 - q0)
        if l < 1e-6: continue
        quad = [M(p0, q0, a0), M(p1, q1, a0), M(p1, q1, a1), M(p0, q0, a1)]
        uvq = [(x, -0.03 - W3), (x + l, -0.03 - W3), (x + l, -0.03), (x, -0.03)]
        if newell(quad).dot(M(q1 - q0, -(p1 - p0), 0.0)) < 0: quad = quad[::-1]; uvq = uvq[::-1]
        g.face(quad, uvq, tg['side'], isls['side'])
        x += l + 0.02
    return isls['cap0']


def tube(g, pts, r, n=6, tag=STEEL, m=1.0, caps='both'):
    for i in range(len(pts) - 1):
        cap = 'none'
        if caps == 'both': cap = 'both' if len(pts) == 2 else ('start' if i == 0 else ('end' if i == len(pts) - 2 else 'none'))
        cyl(g, pts[i], pts[i + 1], r, r, n, tag, m, caps=cap)


def torus(g, c, ax, R, r, n=14, nt=5, tag=TYRE, m=1.0, phase=0.0, up=(0, 0, 1)):
    prof = [(R + r * math.cos(2 * math.pi * k / nt + math.pi / 2), r * math.sin(2 * math.pi * k / nt + math.pi / 2)) for k in range(nt + 1)]
    return lathe(g, c, ax, prof, n, [tag] * nt, m, phase, None, up)


def bb_box(g, margin=0.0):
    xs = [v[0] for v in g.V]; ys = [v[1] for v in g.V]; zs = [v[2] for v in g.V]
    return [(max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2,
            max(xs) - min(xs) + margin, max(ys) - min(ys) + margin, max(zs) - min(zs) + margin]


# =============================================================================================== text / canvases
def text_canvas(wm, hm, ppm, items):
    """render text items on a canvas of wm x hm metres at ppm px/m. item: dict(t, x, y (metres from the lower left), h (metres),
    anchor, font, fill, rot).  returns float array (H, W) row 0 = bottom"""
    W = int(math.ceil(wm * ppm)); H = int(math.ceil(hm * ppm))
    its = []
    for it in items:
        d = dict(it)
        d['x'] = it['x'] * ppm; d['y'] = H - it['y'] * ppm; d['size'] = max(4, int(it['h'] * ppm))
        its.append(d)
    return render_text([dict(w=W, h=H, items=its)])[0]


def canvas_sample(F, mask, cv, ppm, o, u, v):
    """sample canvas cv (row 0 bottom) at the plane coordinates of F.p points: returns float array (k,)"""
    o = np.asarray(o, float); u = np.asarray(u, float); v = np.asarray(v, float)
    d = F.p - o
    a = d @ u; b = d @ v
    H, W = cv.shape
    ix = np.floor(a * ppm).astype(int); iy = np.floor(b * ppm).astype(int)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H) & mask
    out = np.zeros(len(a))
    out[ok] = cv[iy[ok], ix[ok]]
    return out


def wear_mask(F, seed, amount=0.5, f=7.0):
    """1 = intact ink / paint, 0 = worn off"""
    return 1.0 - amount * sstep(0.45, 0.75, fb3(F.p, f, 3, seed)) - 0.25 * amount * vn3(F.p, 60.0, seed + 3)


# =============================================================================================== generic painters
def _metal(tag, **dflt):
    def fn(ctx, seed, kw):
        sel = ctx.sel(tag)
        if not sel.any(): return
        k = dict(dflt); k.update(kw.get(tag, {}))
        k.setdefault('seed', seed + 13 * tag)
        weather(ctx, sel, **k)
    return fn


STEEL_K = dict(base=L((0.58, 0.60, 0.58)), rust=0.38, moss=0.12, bleach=0.25, streak=0.5, dirt=0.3, rough=0.5)
TAGK = {
    STEEL: STEEL_K,
    BARE: dict(base=L((0.22, 0.10, 0.06)), rust=1.0, moss=0.08, bleach=0.0, streak=0.3, dirt=0.3, rough=0.85),
    CHROME: dict(base=L((0.50, 0.50, 0.47)), rust=0.55, moss=0.0, bleach=0.15, streak=0.4, dirt=0.3, rough=0.42),
    CONC: dict(base=L((0.50, 0.48, 0.43)), rust=0.0, moss=0.45, bleach=0.15, streak=0.7, dirt=0.5, rough=0.95, leaf=0.3),
    GRAN: dict(base=L((0.36, 0.35, 0.33)), rust=0.0, moss=0.30, bleach=0.1, streak=0.5, dirt=0.4, rough=0.75),
    PLAS: dict(base=L((0.52, 0.52, 0.48)), rust=0.0, moss=0.25, bleach=0.5, streak=0.5, dirt=0.4, rough=0.62),
    PAINT: dict(base=L((0.6, 0.6, 0.58)), rust=0.5, moss=0.2, bleach=0.5, streak=0.55, leaf=0.3, rough=0.6),
    PAINT2: dict(base=L((0.4, 0.4, 0.38)), rust=0.5, moss=0.2, bleach=0.4, streak=0.55, leaf=0.3, rough=0.6),
    SIGN: dict(base=L((0.5, 0.5, 0.5)), rust=0.3, moss=0.1, bleach=0.5, streak=0.5, dirt=0.3, rough=0.55),
    LAMP: dict(base=L((0.45, 0.30, 0.10)), rust=0.0, moss=0.2, bleach=0.4, streak=0.4, dirt=0.4, rough=0.4),
}


def paint_conc(ctx, seed, kw):
    for tag in (CONC, GRAN):
        sel = ctx.sel(tag)
        if not sel.any(): continue
        k = dict(TAGK[tag]); k.update(kw.get(tag, {})); k.setdefault('seed', seed + 17 * tag)
        weather(ctx, sel, **k)
        F = Flat(ctx, sel)
        grain = vn3(F.p, 320.0, seed + 2)
        F.blend(sstep(0.72, 0.9, grain) * 0.35, F.A * 0.45)
        F.blend(sstep(0.1, 0.25, grain) * (1 - sstep(0.25, 0.3, grain)) * 0.25, L((0.7, 0.68, 0.62)))
        cr = 1.0 - sstep(0.0, 0.010, np.abs(fb3(F.p, np.array([2.6, 2.6, 2.6]), 3, seed + 4) - 0.5))
        cr2 = 1.0 - sstep(0.0, 0.006, np.abs(fb3(F.p, np.array([7.0, 7.0, 7.0]), 3, seed + 5) - 0.5))
        F.blend(np.maximum(cr, cr2 * 0.6) * 0.65, L((0.06, 0.055, 0.05)), R=0.95, dH=-0.003)
        F.blend(sstep(0.55, 0.8, fb3(F.p, 5.0, 3, seed + 6)) * 0.25, L((0.28, 0.26, 0.22)))
        pit = sstep(0.8, 0.92, vn3(F.p, 90.0, seed + 8))
        F.blend(pit * 0.5, L((0.12, 0.11, 0.1)), dH=-0.002)
        F.commit()


def paint_wood(ctx, seed, kw):
    sel = ctx.sel(WOOD)
    if not sel.any(): return
    k = kw.get(WOOD, {})
    base = k.get('base', L((0.36, 0.30, 0.22)))
    weather(ctx, sel, base, seed=seed + 3, rust=0.0, moss=k.get('moss', 0.3), bleach=0.6, streak=0.4, dirt=0.35, leaf=k.get('leaf', 0.2), rough=0.9)
    F = Flat(ctx, sel)
    ax = k.get('axis', 1)
    fr = np.array([60.0, 60.0, 60.0]); fr[ax] = 4.0
    gr = fb3(F.p, fr, 3, seed + 7)
    F.blend(sstep(0.45, 0.7, gr) * 0.5, base * 0.55)
    F.blend(sstep(0.55, 0.8, vn3(F.p, fr * 1.6, seed + 8)) * 0.3, L((0.55, 0.52, 0.46)))
    F.H = F.H + 0.0015 * (gr - 0.5)
    F.commit()


def paint_fab(ctx, seed, kw):
    sel = ctx.sel(FAB)
    if not sel.any(): return
    k = kw.get(FAB, {})
    base = k.get('base', L((0.07, 0.085, 0.11)))
    weather(ctx, sel, base, seed=seed + 4, rust=0.0, moss=k.get('moss', 0.5), bleach=0.2, streak=0.3, dirt=0.4, leaf=0.4, rough=0.95)
    F = Flat(ctx, sel)
    wv = 0.5 + 0.5 * np.sin(F.x * 900) * np.sin(F.y * 900 + F.z * 900)
    F.blend(0.12 * wv, base * 1.8)
    F.blend(sstep(0.55, 0.8, fb3(F.p, 14.0, 2, seed + 6)) * 0.6, L((0.12, 0.11, 0.09)))
    F.commit()


def paint_card(ctx, seed, kw):
    sel = ctx.sel(CARD)
    if not sel.any(): return
    k = kw.get(CARD, {})
    base = k.get('base', L((0.52, 0.40, 0.27)))
    weather(ctx, sel, base, seed=seed + 5, rust=0.0, moss=k.get('moss', 0.45), bleach=0.3, streak=0.7, dirt=0.6, leaf=0.2, rough=0.95)
    F = Flat(ctx, sel)
    st = sstep(0.45, 0.75, fb3(F.p, 5.0, 3, seed + 6))
    F.blend(st * 0.55, base * 0.5)                           # water stains
    F.blend(sstep(0.62, 0.8, fb3(F.p, 3.0, 3, seed + 9)) * 0.55, L((0.20, 0.23, 0.12)))   # mildew
    corr = np.abs(((F.x + F.y) * 700) % 1 - 0.5) < 0.18      # corrugation hint
    F.blend(corr * 0.07, base * 0.7)
    F.commit()


def paint_paper(ctx, seed, kw):
    sel = ctx.sel(PAPER)
    if not sel.any(): return
    base = L((0.62, 0.58, 0.46))
    weather(ctx, sel, base, seed=seed + 6, rust=0.0, moss=0.3, bleach=0.2, streak=0.7, dirt=0.5, leaf=0.0, rough=0.9)
    F = Flat(ctx, sel)
    # rows of text-like grey marks
    ln = (((F.y + F.x * 0.0 + F.z) * 520) % 1 < 0.42) & (vn3(F.p, np.array([55.0, 55.0, 55.0]), seed + 3) > 0.28)
    F.blend(ln * 0.55 * wear_mask(F, seed + 5, 0.5), L((0.12, 0.12, 0.13)))
    F.blend(sstep(0.5, 0.8, fb3(F.p, 6.0, 3, seed + 9)) * 0.55, L((0.34, 0.26, 0.14)))
    F.commit()


def paint_soil(ctx, seed, kw):
    sel = ctx.sel(SOIL)
    if not sel.any(): return
    F = Flat(ctx, sel)
    n = fb3(F.p, 12.0, 3, seed + 2)
    soil = mixc(L((0.16, 0.12, 0.08)), L((0.25, 0.19, 0.12)), n)
    g1 = sstep(0.42, 0.62, fb3(F.p, 6.0, 3, seed + 3))
    F.A = mixc(soil, mixc(T.MOSS_D, T.MOSS, vn3(F.p, 40.0, seed + 4)), g1 * 0.9)
    F.R = np.full(len(F.x), 0.95); F.Mt = np.zeros(len(F.x)); F.H = 0.01 * n + 0.004 * vn3(F.p, 90.0, seed)
    F.commit()


def paint_glass(ctx, seed, kw):
    sel = ctx.sel(GLASS)
    if not sel.any(): return
    F = Flat(ctx, sel)
    base = L((0.07, 0.09, 0.10))
    F.A = np.tile(base, (len(F.x), 1)) * (0.8 + 0.5 * fb3(F.p, 7.0, 2, seed + 2))[:, None]
    cr = sstep(0.47, 0.5, vn3(F.p, np.array([14.0, 14.0, 14.0]), seed + 4)) * (1 - sstep(0.5, 0.53, vn3(F.p, np.array([14.0, 14.0, 14.0]), seed + 4)))
    F.A = mixc(F.A, L((0.5, 0.55, 0.55)), cr * 0.8)
    F.A = mixc(F.A, L((0.18, 0.2, 0.13)), 0.5 * sstep(0.6, 0.8, fb3(F.p, 9.0, 2, seed + 5)))
    F.R = 0.12 + 0.5 * sstep(0.6, 0.8, fb3(F.p, 9.0, 2, seed + 5)); F.Mt = np.zeros(len(F.x)); F.H = np.zeros(len(F.x))
    F.commit()


def paint_generic(ctx):
    g = ctx.g; pal = g.info.get('pal', {}); seed = g.info.get('seed', 7)
    for tag, k in TAGK.items():
        if tag in (CONC, GRAN): continue
        _metal(tag, **k)(ctx, seed, pal)
    paint_conc(ctx, seed, pal)
    paint_wood(ctx, seed, pal); paint_fab(ctx, seed, pal); paint_card(ctx, seed, pal); paint_paper(ctx, seed, pal); paint_glass(ctx, seed, pal); paint_soil(ctx, seed, pal)
    paint_interior(ctx, seed)
    paint_rubber(ctx, seed)
    if 'hook' in g.info: g.info['hook'](ctx)


def reg(name, builder, dens=80.0, painter=None):
    def b():
        g = builder(); g.dens = dens
        return g
    BUILDERS[name] = b
    PAINTERS[name] = painter or paint_generic


def convex(g, faces, tags, m=1.0, isl=None):
    """convex solid from explicit faces; every face oriented away from the centroid; one island, faces side by side"""
    allv = [V3(p) for f in faces for p in f]
    c = sum(allv, V3((0, 0, 0))) / len(allv)
    if isl is None: isl = g.island(m)
    ox = 0.0
    for f, t in zip(faces, tags if isinstance(tags, (list, tuple)) else [tags] * len(faces)):
        pts = [V3(p) for p in f]
        fc = sum(pts, V3((0, 0, 0))) / len(pts)
        if newell(pts).dot(fc - c) < 0: pts = pts[::-1]
        uv = planar(pts)
        mn = (min(u[0] for u in uv), min(u[1] for u in uv)); mx = max(u[0] for u in uv)
        g.face(pts, [(a - mn[0] + ox, b - mn[1]) for a, b in uv], t, isl)
        ox += mx - mn[0] + 0.03
    return isl


def panel_paint(F, m, o, u, v, W, H, ppm, items, bg=None, ink=(0.9, 0.9, 0.85), wear=0.5, seed=1, ink_R=0.5, raised=0.0006, fade=0.0):
    """text on a plane: F flat view, m bool mask, o origin, u/v plane axes (unit), W/H metres, items -> text_canvas"""
    cv = text_canvas(W, H, ppm, items)
    a = canvas_sample(F, m, cv, ppm, o, u, v)
    inkc = np.asarray(ink, float)
    w = np.clip(wear_mask(F, seed, wear), 0, 1) * (1 - fade)
    if bg is not None:
        F.blend(m.astype(float), bg)
    F.blend(a * w, inkc, R=ink_R, dH=raised)
    return a


# =============================================================================================== orientation QA
def check_orientation(ob, log=print):
    """ray test: outward normals shoot to an even number of hits; reports faces that start inside"""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    bad = 0; tot = 0
    for f in bm.faces:
        c = f.calc_center_median(); n = f.normal
        if f.calc_area() < 1e-5: continue
        o = c + n * 2e-4; hits = 0; d = n
        for _ in range(8):
            loc, nn, idx, dist = bvh.ray_cast(o, d)
            if loc is None: break
            hits += 1; o = loc + d * 1e-4
        tot += 1
        if hits % 2 == 1: bad += 1
    bm.free()
    return bad, tot


# =============================================================================================== street furniture
def b_bollard():
    g = Geo('bollard')
    lathe(g, (0, 0, 0), (0, 0, 1), [(0.075, 0.0), (0.075, 0.03), (0.055, 0.05), (0.055, 0.74), (0.05, 0.80), (0.0, 0.83)], 8,
          [STEEL, STEEL, STEEL, STEEL, STEEL], 1.0)
    g.boxes = [[0, 0, 0.4, 0.2, 0.2, 0.8]]
    g.info.update(seed=3, hook=hook_bollard)
    return g


def hook_bollard(ctx):
    sel = ctx.sel(STEEL); F = Flat(ctx, sel)
    band = (F.z > 0.52) & (F.z < 0.64)
    F.blend(band * 0.9, L((0.55, 0.12, 0.08)), R=0.45, Mt=0.1)
    band = (F.z > 0.36) & (F.z < 0.40)
    F.blend(band * 0.8, L((0.7, 0.7, 0.66)), R=0.4)
    F.commit()


def b_street_lamp():
    g = Geo('street_lamp')
    box(g, (0, 0, 0.02), (0.42, 0.42, 0.04), STEEL, 0.6, faces='xXyYz')
    lathe(g, (0, 0, 0.04), (0, 0, 1), [(0.16, 0.0), (0.16, 0.45), (0.115, 0.5), (0.085, 0.55), (0.062, 6.6), (0.055, 6.9)], 8,
          [STEEL] * 5, 1.0, phase=math.pi / 8)
    arm = [(0, 0, 6.75), (0.18, 0, 7.05), (0.65, 0, 7.30), (1.30, 0, 7.36), (1.85, 0, 7.30)]
    tube(g, arm, 0.042, 6, STEEL, 0.8)
    head = [(1.55, -0.16), (2.0, -0.18), (2.45, -0.10), (2.60, 0.0), (2.45, 0.10), (2.0, 0.18), (1.55, 0.16)]
    extrude(g, head, 'z', 7.20, 7.32, PAINT, 1.0)
    pts = [V3((1.62, -0.13, 7.195)), V3((2.38, -0.08, 7.195)), V3((2.38, 0.08, 7.195)), V3((1.62, 0.13, 7.195))]
    g.face(pts[::-1], planar(pts[::-1]), GLASS, g.island(0.5))
    g.boxes = [[0, 0, 0.6, 0.4, 0.4, 1.2]]
    g.info.update(seed=5, pal={PAINT: dict(base=L((0.34, 0.37, 0.33)), rust=0.45, moss=0.25, bleach=0.3),
                               STEEL: dict(base=L((0.55, 0.57, 0.54)), rust=0.6, moss=0.35, bleach=0.3, zlow=0.0, zspan=4.0, streak=0.7, dirt=0.5)})
    return g


def b_guard_rail():
    g = Geo('guard_rail')
    prof = [(0.0, 0.60), (0.0, 0.635), (0.045, 0.675), (0.045, 0.705), (0.0, 0.745), (0.0, 0.755), (0.045, 0.795), (0.045, 0.825), (0.0, 0.865), (0.0, 0.90)]
    prof = prof + [(y + 0.004, z) for y, z in prof[::-1]]
    extrude(g, prof, 'x', -2.0, 2.0, PAINT, 1.0)
    for x in (-1.9, 0.0, 1.9):
        cyl(g, (x, 0.12, 0.0), (x, 0.12, 0.95), 0.0575, 0.0575, 8, STEEL, 0.8, caps='end')
        box(g, (x, 0.07, 0.75), (0.10, 0.08, 0.20), STEEL, 0.5, faces='xXyz')
    box(g, (0.55, -0.012, 0.76), (0.12, 0.02, 0.08), PAINT2, 0.5, faces='Y')
    g.boxes = [[0, 0.08, 0.48, 4.0, 0.2, 0.96]]
    g.info.update(seed=9, pal={PAINT: dict(base=L((0.78, 0.78, 0.74)), rust=0.40, moss=0.15, bleach=0.5, streak=0.6, zlow=0.55, zspan=0.5),
                            STEEL: dict(base=L((0.62, 0.63, 0.60)), rust=0.35, moss=0.2, zlow=0.0, zspan=1.0)})
    return g


def b_traffic_signal():
    g = Geo('traffic_signal')
    box(g, (0, 0, 0.02), (0.36, 0.36, 0.04), STEEL, 0.6, faces='xXyYz')
    lathe(g, (0, 0, 0.04), (0, 0, 1), [(0.14, 0.0), (0.14, 0.35), (0.105, 0.40), (0.1, 0.45), (0.072, 5.1), (0.066, 5.3)], 8, [STEEL] * 5, 1.0, phase=math.pi / 8)
    arm = [(0, 0, 4.85), (0.4, 0, 5.15), (1.5, 0, 5.40), (2.8, 0, 5.52), (4.0, 0, 5.50)]
    tube(g, arm, 0.055, 6, STEEL, 0.8)
    # three-lamp horizontal head hung under the arm (faces +y)
    cx, cz = 3.1, 5.12
    box(g, (cx, 0, cz), (1.06, 0.30, 0.34), PAINT, 1.0, faces='xXyYzZ')
    for dx in (-0.35, 0.0, 0.35):
        cyl(g, (cx + dx, 0.15, cz), (cx + dx, 0.155, cz), 0.125, 0.125, 8, LAMP, 0.8, caps='end')
        box(g, (cx + dx, 0.23, cz + 0.12), (0.26, 0.17, 0.02), PAINT, 0.4, faces='xXyz')
        for sd in (-1, 1): box(g, (cx + dx + sd * 0.13, 0.23, cz), (0.02, 0.17, 0.24), PAINT, 0.4, faces='yz')
    bar(g, (cx - 0.3, 0, cz + 0.17), (cx - 0.3, 0, 5.46), 0.03, 0.03, STEEL, 0.4)
    bar(g, (cx + 0.3, 0, cz + 0.17), (cx + 0.3, 0, 5.5), 0.03, 0.03, STEEL, 0.4)
    # pedestrian signal on the pole (faces +x) and push button
    box(g, (0.17, 0, 2.7), (0.1, 0.3, 0.32), PAINT, 1.0, faces='xXyYzZ')
    box(g, (0.215, 0, 2.7), (0.01, 0.26, 0.28), LAMP, 0.8, faces='x')
    box(g, (0.0, 0.14, 1.15), (0.1, 0.07, 0.17), PLAS, 0.5, faces='xXyYz')
    g.boxes = [[0, 0, 0.6, 0.4, 0.4, 1.2]]
    g.info.update(seed=15, pal={PAINT: dict(base=L((0.13, 0.21, 0.17)), rust=0.35, moss=0.3, bleach=0.35, streak=0.6),
                            STEEL: dict(base=L((0.48, 0.52, 0.48)), rust=0.6, moss=0.35, bleach=0.3, zlow=0.0, zspan=4.5, streak=0.7, dirt=0.5)}, hook=hook_signal)
    return g


def hook_signal(ctx):
    sel = ctx.sel(LAMP); F = Flat(ctx, sel)
    weather(ctx, sel, L((0.2, 0.2, 0.2)), seed=4, rust=0, moss=0.15, bleach=0.2, streak=0.4, dirt=0.4, rough=0.3)
    F = Flat(ctx, sel)
    head = F.nx < 0.5
    dx = F.x - 3.1
    cols = [(-0.35, L((0.08, 0.34, 0.30))), (0.0, L((0.50, 0.40, 0.08))), (0.35, L((0.42, 0.06, 0.05)))]
    for off, c in cols:
        r = np.hypot(F.x - 3.1 - off, F.z - 5.12)
        m = head & (r < 0.13)
        F.blend(m * 1.0, c * (0.55 + 0.5 * fb3(F.p, 25.0, 2, 4)[:, None] if False else 1.0), R=0.2)
        F.blend(m * sstep(0.5, 0.75, fb3(F.p, 18.0, 2, 8)) * 0.6, L((0.2, 0.2, 0.18)))
    # pedestrian lens: red figure over green figure on dark
    ped = F.nx > 0.5
    F.blend(ped * 1.0, L((0.05, 0.05, 0.05)), R=0.2)
    top = ped & (F.z > 2.7) & (np.abs(F.y) < 0.08) & (F.z < 2.82)
    bot = ped & (F.z < 2.7) & (np.abs(F.y) < 0.08) & (F.z > 2.58)
    F.blend(top * 0.8, L((0.40, 0.08, 0.06))); F.blend(bot * 0.8, L((0.08, 0.30, 0.24)))
    F.commit()


def b_bus_pole():
    g = Geo('bus_pole')
    lathe(g, (0, 0, 0), (0, 0, 1), [(0.22, 0.0), (0.22, 0.14), (0.20, 0.17), (0.07, 0.19), (0.036, 0.24), (0.034, 2.95)], 8,
          [CONC, CONC, CONC, STEEL, STEEL], 1.0)
    cz = 2.42; R = 0.31
    arc = [(-R * math.cos(a), cz + R * math.sin(a)) for a in np.linspace(0, math.pi, 9)]
    poly2 = [(R, 1.78), (R, cz)] + [(R * math.cos(a), cz + R * math.sin(a)) for a in np.linspace(0, math.pi, 9)][1:-1] + [(-R, cz), (-R, 1.78)]
    extrude(g, poly2, 'y', 0.04, 0.062, SIGN, 3.0, tags={'side': STEEL, 'cap0': STEEL}, ms={'cap0': 0.3, 'cap1': 3.0, 'side': 0.3})
    box(g, (0, 0.04, 1.48), (0.5, 0.012, 0.3), SIGN, 2.5, faces='y')
    box(g, (0, 0.04, 1.48), (0.5, 0.012, 0.3), STEEL, 0.3, faces='xXYzZ')
    g.boxes = [[0, 0, 0.6, 0.45, 0.45, 1.2]]
    g.info.update(seed=21, hook=hook_bus_pole, signf=dict(cz=cz, R=R))
    return g


def ginkgo(F, m, cx, cz, size, col):
    """a simple three-lobed leaf mark painted by distance (Tokyo's emblem feel)"""
    d = np.hypot(F.x - cx, F.z - cz)
    ang = np.arctan2(F.z - cz, F.x - cx)
    lobes = 0.55 + 0.45 * np.cos(3 * (ang - math.pi / 2))
    return m & (d < size * lobes)


def hook_bus_pole(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    front = (F.ny < -0.5) | (F.ny > 0.5)
    green = L((0.05, 0.42, 0.26)); white = L((0.62, 0.62, 0.56))
    cz = 2.42; R = 0.31
    # round-top plate (front y=+0.062): green header, white body
    pl = F.y > 0.05
    head = pl & (F.z > cz - 0.02)
    body = pl & ~head
    F.blend(head * 1.0, green, R=0.6); F.blend(body * 1.0, white, R=0.6)
    items = [dict(t='都営バス', x=0.62, y=0.56, h=0.115, anchor='mm', font='bold', fill=255),
             dict(t='TOEI BUS', x=0.62, y=0.44, h=0.045, anchor='mm', font='bold', fill=255)]
    o = np.array([0.31, 0.0, 1.78]); u = np.array([-1.0, 0, 0]); v = np.array([0, 0, 1.0])
    panel_paint(F, pl & head, o, u, v, 0.62, 0.95, 240, items, None, ink=(0.80, 0.82, 0.74), seed=3)
    items2 = [dict(t='都庁前', x=0.31, y=0.37, h=0.14, anchor='mm', font='bold', fill=255),
              dict(t='Tocho-mae', x=0.31, y=0.22, h=0.05, anchor='mm', font='bold', fill=255),
              dict(t='新宿駅西口 ↑', x=0.31, y=0.10, h=0.06, anchor='mm', font='bold', fill=255)]
    panel_paint(F, pl & body, o, u, v, 0.62, 0.95, 240, items2, None, ink=(0.08, 0.1, 0.09), seed=5)
    # ginkgo mark on the header
    gm = ginkgo(F, pl & head, 0.0, cz + 0.12, 0.055, None)
    F.blend(gm * 0.9, L((0.72, 0.78, 0.60)))
    # route plate (below)
    rp = (F.y > 0.04) & (F.z < 1.7) & (F.ny > 0.5) & (F.z > 1.3)
    F.blend(rp * 1.0, L((0.52, 0.52, 0.48)), R=0.6)
    rows = [dict(t='宿75', x=0.12, y=0.22, h=0.075, anchor='mm', font='bold', fill=255),
            dict(t='都03', x=0.30, y=0.22, h=0.075, anchor='mm', font='bold', fill=255),
            dict(t='橋86', x=0.48, y=0.22, h=0.075, anchor='mm', font='bold', fill=255),
            dict(t='新宿駅西口 → 渋谷駅', x=0.30, y=0.07, h=0.045, anchor='mm', font='bold', fill=255)]
    panel_paint(F, rp, np.array([0.25, 0, 1.33]), u, v, 0.5, 0.3, 240, rows, None, ink=(0.06, 0.20, 0.12), seed=9)
    # dust / grime over everything, rust speckle on the plate edges
    F.blend(0.35 * sstep(0.45, 0.8, fb3(F.p, 5.0, 3, 14)), L((0.30, 0.27, 0.20)))
    edge = (np.abs(np.abs(F.x) - 0.31) < 0.012) & (F.z < cz)
    F.blend(edge * 0.6, L((0.36, 0.17, 0.08)))
    F.commit()


def b_sign_blue():
    g = Geo('sign_blue')
    for x in (-0.72, 0.72):
        cyl(g, (x, 0, 0), (x, 0, 3.35), 0.035, 0.035, 8, STEEL, 0.8, caps='end')
    box(g, (0, 0.04, 2.95), (1.96, 0.03, 0.98), SIGN, 5.0, faces='y')
    box(g, (0, 0.04, 2.95), (1.96, 0.03, 0.98), STEEL, 0.4, faces='xXYzZ')
    for x in (-0.72, 0.72):
        for z in (2.62, 3.28):
            box(g, (x, 0.02, z), (0.1, 0.05, 0.05), STEEL, 0.5, faces='yz')
    box(g, (0, 0, 0.02), (0.3, 0.3, 0.04), CONC, 0.3, faces='z')
    g.boxes = [[0, 0, 0.6, 0.35, 0.3, 1.2]]
    g.info.update(seed=25, pal={STEEL: dict(base=L((0.5, 0.52, 0.5)), rust=0.5, moss=0.2, bleach=0.3)}, hook=hook_sign_blue)
    return g


def hook_sign_blue(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    fr = F.ny > 0.7
    blue = L((0.04, 0.24, 0.46))
    o = np.array([0.98, 0, 2.46]); u = np.array([-1.0, 0, 0]); v = np.array([0, 0, 1.0])
    items = [dict(t='都庁前', x=0.28, y=0.76, h=0.19, anchor='lm', font='bold'), dict(t='Tocho-mae', x=0.30, y=0.62, h=0.07, anchor='lm', font='bold'),
             dict(t='→', x=1.72, y=0.72, h=0.30, anchor='mm', font='bold'),
             dict(t='新宿駅', x=0.28, y=0.46, h=0.19, anchor='lm', font='bold'), dict(t='Shinjuku Sta.', x=0.30, y=0.33, h=0.07, anchor='lm', font='bold'),
             dict(t='↑', x=1.72, y=0.44, h=0.30, anchor='mm', font='bold'),
             dict(t='中野', x=0.28, y=0.18, h=0.15, anchor='lm', font='bold'), dict(t='Nakano', x=1.05, y=0.17, h=0.07, anchor='lm', font='bold'),
             dict(t='←', x=1.72, y=0.16, h=0.26, anchor='mm', font='bold'),
             dict(t='20', x=0.10, y=0.78, h=0.10, anchor='mm', font='bold')]
    cv = text_canvas(1.96, 0.98, 360, items)
    a = canvas_sample(F, fr & (np.abs(F.x) < 0.98) & (F.z > 2.46) & (F.z < 3.44), cv, 360, o, u, v)
    wn = np.clip(wear_mask(F, 31, 0.8), 0, 1)
    bd = (np.abs(np.abs(F.x) - 0.95) < 0.025) | (np.abs(F.z - 2.95) > 0.455)
    F.blend(fr * 1.0, blue, R=0.45)
    F.blend(fr * bd * 0.85 * wn, L((0.8, 0.82, 0.78)), R=0.4)
    F.blend(a * wn, L((0.82, 0.84, 0.80)), R=0.4)
    # faded and flaking: pale chalk bloom, grey primer, rust at the bottom edge and bolt holes
    F.blend(fr * sstep(0.5, 0.75, fb3(F.p, 3.0, 3, 77)) * 0.45, L((0.30, 0.38, 0.40)))
    F.blend(fr * sstep(0.7, 0.8, fb3(F.p, 9.0, 3, 78)) * 0.8, L((0.34, 0.15, 0.08)))
    F.blend(fr * sstep(0.52, 0.8, fb3(F.p, 2.0, 3, 79)) * (F.z < 2.85) * 0.5, L((0.15, 0.2, 0.1)))
    F.commit()


def b_sign_tocho():
    g = Geo('sign_tocho')
    A = 1.7; y0 = 0.28; y1 = -0.28
    v = lambda x, y, z: (x, y, z)
    faces = [[v(-A, y0, 0), v(A, y0, 0), v(A, y0, 0.42), v(-A, y0, 0.42)],                 # low front face
             [v(-A, y0, 0.42), v(A, y0, 0.42), v(A, y1, 0.86), v(-A, y1, 0.86)],            # sloped lettering face
             [v(-A, y1, 0), v(-A, y1, 0.86), v(A, y1, 0.86), v(A, y1, 0)],                  # back
             [v(-A, y0, 0), v(-A, y0, 0.42), v(-A, y1, 0.86), v(-A, y1, 0)],
             [v(A, y0, 0), v(A, y1, 0), v(A, y1, 0.86), v(A, y0, 0.42)],
             [v(-A, y0, 0), v(-A, y1, 0), v(A, y1, 0), v(A, y0, 0)]]
    convex(g, faces[:1] + faces[2:5], GRAN, 1.0)
    g.facen(faces[1], SIGN, g.island(3.0), (0, 0.56, 0.44))
    g.facen(faces[5], GRAN, g.island(0.3), (0, 0, -1))
    g.boxes = [[0, 0, 0.43, 3.4, 0.56, 0.86]]
    g.info.update(seed=27, hook=hook_sign_tocho)
    return g


def hook_sign_tocho(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    A = 1.7
    sl = math.hypot(0.56, 0.44)
    u = np.array([-1.0, 0, 0]); v = np.array([0, -0.56 / sl, 0.44 / sl])
    o = np.array([A, 0.28, 0.42])
    F.blend(np.ones(len(F.x)), L((0.05, 0.055, 0.06)), R=0.35)
    items = [dict(t='東京都庁', x=1.7, y=0.52, h=0.34, anchor='mm', font='serif'),
             dict(t='東京都議会議事堂', x=1.7, y=0.24, h=0.16, anchor='mm', font='serif'),
             dict(t='TOKYO METROPOLITAN GOVERNMENT BUILDING', x=1.7, y=0.07, h=0.05, anchor='mm', font='bold')]
    panel_paint(F, np.ones(len(F.x), bool), o, u, v, 3.4, sl, 200, items, None, ink=(0.62, 0.60, 0.52), wear=0.6, seed=2, ink_R=0.4, raised=0.0015)
    F.blend(sstep(0.5, 0.8, fb3(F.p, 4.0, 3, 5)) * 0.5, L((0.2, 0.22, 0.14)), R=0.9)          # moss / dust creeping on the polished face
    F.blend(sstep(0.62, 0.8, fb3(F.p, 14.0, 2, 6)) * 0.5, L((0.3, 0.27, 0.2)), R=0.9)
    F.commit()


def b_sign_fallen_panel():
    g = Geo('sign_fallen_panel')
    W, H = 2.2, 1.1
    t = math.radians(5.0)
    p = [V3((-W / 2, -H / 2, 0.08)), V3((W / 2, -H / 2, 0.06)), V3((W / 2, H / 2, 0.14)), V3((-W / 2, H / 2, 0.16))]
    isl = g.island(4.0)
    uv = [(0, 0), (W, 0), (W, H), (0, H)]
    g.face(p, uv, SIGN, isl)
    g.face(p[::-1], uv[::-1], STEEL, g.island(0.3))
    for (x, y) in ((0.9, 0.0), (-0.9, 0.2)):
        box(g, (x, y, 0.045), (0.08, 0.3, 0.07), STEEL, 0.4, faces='xXyYz')
    g.boxes = [[0, 0, 0.08, 2.2, 1.1, 0.16]]
    g.info.update(seed=29, hook=hook_sign_fallen)
    return g


def hook_sign_fallen(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    W, H = 2.2, 1.1
    up = F.nz > 0.5
    o = np.array([-W / 2, -H / 2, 0.0]); u = np.array([1.0, 0, 0]); v = np.array([0, 1.0, 0])
    blue = L((0.05, 0.26, 0.45))
    items = [dict(t='都庁通り', x=0.4, y=0.78, h=0.22, anchor='lm', font='bold'), dict(t='Tocho-dori', x=0.42, y=0.60, h=0.08, anchor='lm', font='bold'),
             dict(t='新宿中央公園', x=0.4, y=0.36, h=0.17, anchor='lm', font='bold'), dict(t='Shinjuku Central Park', x=0.42, y=0.20, h=0.07, anchor='lm', font='bold'),
             dict(t='→', x=1.82, y=0.55, h=0.40, anchor='mm', font='bold')]
    cv = text_canvas(W, H, 300, items)
    a = canvas_sample(F, up, cv, 300, o, u, v)
    wn = np.clip(wear_mask(F, 41, 0.9), 0, 1)
    F.blend(up * 1.0, blue, R=0.5)
    bd = (np.abs(np.abs(F.x) - 1.07) < 0.025) | (np.abs(np.abs(F.y) - 0.53) < 0.025)
    F.blend(up * bd * 0.8 * wn, L((0.75, 0.78, 0.72)))
    F.blend(a * wn, L((0.8, 0.82, 0.76)))
    F.blend(up * sstep(0.45, 0.72, fb3(F.p, 2.5, 3, 7)) * 0.7, L((0.2, 0.3, 0.12)), R=0.95)       # moss and silt
    F.blend(up * sstep(0.62, 0.78, fb3(F.p, 6.0, 3, 8)) * 0.6, L((0.35, 0.28, 0.17)), R=0.95)
    F.blend(up * sstep(0.72, 0.8, fb3(F.p, 7.0, 3, 9)) * 0.7, L((0.32, 0.14, 0.07)), R=0.9)
    F.commit()


def b_vending(name, variant):
    g = Geo(name)
    W, D, H = 0.78, 0.70, 1.83
    hx, hy = W / 2, D / 2
    body = (0.6, 0.12, 0.10) if variant == 0 else (0.10, 0.22, 0.45)
    box(g, (0, 0, H / 2), (W, D, H), PAINT, 1.0, faces='xXYzZ')
    wx0, wx1, wz0, wz1 = -0.34, 0.12, 0.60, 1.62
    zs = [0.0, wz0, wz1, H]; xs = [-hx, wx0, wx1, hx]
    isl = g.island(1.4)
    # front face with a window opening: 8 quads around the opening
    for i in range(3):
        for j in range(3):
            if i == 1 and j == 1: continue
            pts = [V3((xs[i], hy, zs[j])), V3((xs[i + 1], hy, zs[j])), V3((xs[i + 1], hy, zs[j + 1])), V3((xs[i], hy, zs[j + 1]))]
            g.facen(pts, PAINT, isl, (0, 1, 0), uv=[(p.x + hx, p.z) for p in pts])
    dp = 0.07
    g.facen([(wx0, hy - dp, wz0), (wx1, hy - dp, wz0), (wx1, hy - dp, wz1), (wx0, hy - dp, wz1)], INT, g.island(2.0), (0, 1, 0))
    iw = g.island(0.8)
    g.facen([(wx0, hy, wz0), (wx0, hy - dp, wz0), (wx1, hy - dp, wz0), (wx1, hy, wz0)], INT, iw, (0, 0, 1), uv=[(0, 0), (0.07, 0), (0.07, 0.46), (0, 0.46)])
    g.facen([(wx0, hy, wz1), (wx1, hy, wz1), (wx1, hy - dp, wz1), (wx0, hy - dp, wz1)], INT, iw, (0, 0, -1), uv=[(0.1, 0), (0.1, 0.46), (0.17, 0.46), (0.17, 0)])
    g.facen([(wx0, hy, wz0), (wx0, hy, wz1), (wx0, hy - dp, wz1), (wx0, hy - dp, wz0)], INT, iw, (1, 0, 0), uv=[(0.2, 0), (0.2, 1.0), (0.27, 1.0), (0.27, 0)])
    g.facen([(wx1, hy, wz0), (wx1, hy - dp, wz0), (wx1, hy - dp, wz1), (wx1, hy, wz1)], INT, iw, (-1, 0, 0), uv=[(0.3, 0), (0.37, 0), (0.37, 1.0), (0.3, 1.0)])
    box(g, (0, 0, 0.04), (W + 0.04, D + 0.04, 0.08), STEEL, 0.4, faces='xXyYz')
    box(g, (0, 0, H + 0.02), (W + 0.04, D + 0.04, 0.04), PAINT, 0.5, faces='xXyYz')
    g.boxes = [[0, 0, H / 2, W, D, H]]
    g.info.update(seed=31 + variant, variant=variant, pal={PAINT: dict(base=L(body), rust=0.35, moss=0.2, bleach=0.55, streak=0.7, zlow=0.0, zspan=1.4)},
                  hook=hook_vending)
    return g


def hook_vending(ctx):
    g = ctx.g; var = g.info['variant']
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    fr = (F.ny > 0.7) & (F.y > 0.34)
    # top header panel (was lit): pale faded colour with the drink slogan
    hd = fr & (F.z > 1.62)
    sl = fr & (F.x > 0.12)
    F.blend(hd * 1.0, L((0.62, 0.58, 0.5)) if var == 0 else L((0.52, 0.6, 0.66)), R=0.5)
    items = [dict(t='つめた〜い', x=0.25, y=0.14, h=0.085, anchor='mm', font='bold'), dict(t='あたたか〜い', x=0.56, y=0.14, h=0.085, anchor='mm', font='bold')]
    panel_paint(F, hd, np.array([0.39, 0, 1.62]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.78, 0.21, 200, items, None,
                ink=(0.55, 0.12, 0.1) if var == 0 else (0.1, 0.2, 0.5), seed=3)
    # control column: coin slot, buttons, return slot, outlet flap
    F.blend(sl * 1.0, L((0.15, 0.15, 0.14)) if var == 0 else L((0.75, 0.75, 0.72)), R=0.5)
    for k in range(6):
        zc = 1.50 - 0.10 * k
        for xc in (0.20, 0.30):
            btn = sl & (np.abs(F.z - zc) < 0.032) & (np.abs(F.x - xc) < 0.035)
            F.blend(btn * 1.0, L((0.55, 0.52, 0.45)), R=0.4, dH=0.003)
    F.blend(sl * (np.abs(F.z - 0.82) < 0.04) * (np.abs(F.x - 0.25) < 0.08), L((0.02, 0.02, 0.02)))
    flap = fr & (F.z < 0.36) & (F.z > 0.12) & (F.x < 0.2) & (F.x > -0.30)
    F.blend(flap * 1.0, L((0.03, 0.03, 0.03)), R=0.5, dH=-0.004)
    F.commit()
    sel = ctx.sel(INT); F = Flat(ctx, sel)
    win = F.ny > 0.7
    # rows of dummy cans on shelves
    pal = [L((0.55, 0.1, 0.08)), L((0.12, 0.22, 0.5)), L((0.55, 0.5, 0.45)), L((0.12, 0.4, 0.2)), L((0.6, 0.42, 0.1)), L((0.4, 0.15, 0.4))]
    zlo = 0.60; row = np.floor((F.z - zlo) / 0.17); rz = (F.z - zlo) - row * 0.17
    col = np.floor((F.x + 0.34) / 0.052); rx = (F.x + 0.34) - col * 0.052
    h = (_h3(col.astype(np.int64) + 40, row.astype(np.int64) + 90, np.zeros(len(col), np.int64), 17 + var) * 5.99).astype(int)
    can = win & (rz > 0.035) & (rz < 0.155) & (rx > 0.004) & (rx < 0.048)
    cc = np.array(pal)[h]
    shade = 0.65 + 0.5 * np.sin(rx / 0.052 * math.pi)
    F.blend(win * 1.0, L((0.04, 0.04, 0.045)), R=0.4)
    gone = _h3(col.astype(np.int64) + 5, row.astype(np.int64) + 5, np.zeros(len(col), np.int64), 33) < 0.30
    F.blend(can * (~gone) * 1.0, cc * shade[:, None] * 0.7, R=0.35, Mt=0.2)
    F.blend(win * (rz < 0.03) * 1.0, L((0.5, 0.5, 0.48)), R=0.4)         # shelf lip
    F.blend(win * sstep(0.45, 0.75, fb3(F.p, 8.0, 3, 61)) * 0.55, L((0.20, 0.22, 0.13)), R=0.9)     # dust, mould
    F.commit()


def b_bench():
    g = Geo('bench')
    for k, y in enumerate((-0.06, 0.02, 0.10, 0.18)):
        if k == 2: continue
        box(g, (0, y, 0.44), (1.8, 0.075, 0.04), WOOD, 0.9, faces='xXyYzZ')
    for k in range(3):
        z = 0.58 + 0.12 * k
        box(g, (0, -0.26 - 0.03 * k, z), (1.8, 0.04, 0.085), WOOD, 0.9, rot=None, faces='xXyYzZ')
    for sx in (-0.82, 0.82):
        bar(g, (sx, 0.20, 0.0), (sx, 0.20, 0.44), 0.06, 0.05, STEEL, 0.4)
        bar(g, (sx, -0.12, 0.0), (sx, -0.12, 0.44), 0.06, 0.05, STEEL, 0.4)
        bar(g, (sx, -0.12, 0.44), (sx, -0.34, 0.86), 0.06, 0.05, STEEL, 0.4)
        bar(g, (sx, -0.12, 0.40), (sx, 0.20, 0.40), 0.06, 0.05, STEEL, 0.4)
    g.boxes = [[0, -0.08, 0.35, 1.84, 0.6, 0.7]]
    g.info.update(seed=33, pal={WOOD: dict(axis=0), STEEL: dict(base=L((0.28, 0.30, 0.27)), rust=0.55, moss=0.25, bleach=0.2)})
    return g


def b_trash_bin():
    g = Geo('trash_bin')
    box(g, (0, 0, 0.42), (0.46, 0.46, 0.84), PAINT, 1.0, faces='xXYZ')
    box(g, (0, 0, 0.42), (0.46, 0.46, 0.84), PAINT, 2.6, faces='y')
    # lid with a slot opening on the front (+y)
    extrude(g, [(-0.25, 0.84), (0.25, 0.84), (0.25, 0.92), (0.15, 0.98), (-0.15, 0.98), (-0.25, 0.92)], 'y', -0.25, 0.25, PAINT, 1.0)
    box(g, (0, 0.235, 0.7), (0.3, 0.02, 0.1), INT, 0.5, faces='y')
    box(g, (0, 0, 0.02), (0.5, 0.5, 0.04), STEEL, 0.4, faces='xXyYz')
    g.boxes = [[0, 0, 0.5, 0.5, 0.5, 1.0]]
    g.info.update(seed=35, pal={PAINT: dict(base=L((0.18, 0.28, 0.22)), rust=0.55, moss=0.3, bleach=0.4, zlow=0.0, zspan=1.0)}, hook=hook_bin)
    return g


def hook_bin(ctx):
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    fr = (F.ny > 0.7) & (F.y > 0.2) & (F.z < 0.84)
    items = [dict(t='燃えるごみ', x=0.23, y=0.16, h=0.075, anchor='mm', font='bold'), dict(t='Burnable', x=0.23, y=0.07, h=0.04, anchor='mm', font='bold')]
    panel_paint(F, fr, np.array([0.23, 0, 0.3]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.46, 0.26, 260, items, None, ink=(0.78, 0.78, 0.7), seed=4)
    F.commit()


def b_planter_box():
    g = Geo('planter_box')
    W, D, H, t = 1.2, 0.5, 0.5, 0.07
    box(g, (0, D / 2 - t / 2, H / 2), (W, t, H), CONC, 1.0, faces='xXyYzZ')
    box(g, (0, -D / 2 + t / 2, H / 2), (W, t, H), CONC, 1.0, faces='xXyYzZ')
    box(g, (W / 2 - t / 2, 0, H / 2), (t, D - 2 * t, H), CONC, 1.0, faces='xyYz')
    box(g, (-W / 2 + t / 2, 0, H / 2), (t, D - 2 * t, H), CONC, 1.0, faces='XyYz')
    pts = [V3((-W / 2 + t, -D / 2 + t, 0.40)), V3((W / 2 - t, -D / 2 + t, 0.40)), V3((W / 2 - t, D / 2 - t, 0.40)), V3((-W / 2 + t, D / 2 - t, 0.40))]
    g.face(pts, planar(pts, (0, 0, 1)), SOIL, g.island(1.0))
    g.boxes = [[0, 0, 0.25, 1.2, 0.5, 0.5]]
    g.info.update(seed=37)
    return g


def b_phone_booth():
    g = Geo('phone_booth')
    W = 0.9; Hh = 2.3
    box(g, (0, 0, 0.07), (W, W, 0.14), CONC, 0.6, faces='xXyYz')
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar(g, (sx * 0.43, sy * 0.43, 0.14), (sx * 0.43, sy * 0.43, 2.2), 0.05, 0.05, PAINT, 0.7)
    box(g, (0, 0, 2.27), (W + 0.06, W + 0.06, 0.12), PAINT, 1.0, faces='xXyYzZ')
    box(g, (0, 0.455, 2.27), (0.7, 0.02, 0.1), SIGN, 3.0, faces='y')
    for z in (0.5, 1.1, 1.7):                                  # mid rails
        for (a, b) in (((-0.43, 0.43), (0.43, 0.43)), ((-0.43, -0.43), (0.43, -0.43)), ((-0.43, -0.43), (-0.43, 0.43)), ((0.43, -0.43), (0.43, 0.43))):
            if z == 1.1 and a[1] == b[1] == 0.43: continue
            bar(g, (a[0], a[1], z), (b[0], b[1], z), 0.03, 0.04, PAINT, 0.5)
    # shelf and the telephone on the back wall
    box(g, (0, -0.30, 0.95), (0.56, 0.2, 0.04), PAINT, 0.5, faces='xXyYzZ')
    box(g, (0, -0.35, 1.28), (0.30, 0.14, 0.50), PAINT2, 1.0, faces='xXyYz')
    box(g, (0.0, -0.265, 1.40), (0.12, 0.03, 0.14), INT, 0.5, faces='y')
    cyl(g, (-0.09, -0.255, 1.30), (0.09, -0.255, 1.30), 0.018, 0.018, 6, PAINT2, 0.3, caps='both')
    # glass: shards left in the corners of the frames
    for (pts) in ([(-0.43, 0.43, 0.5), (-0.43, 0.43, 1.1), (-0.12, 0.43, 0.5)], [(0.43, -0.43, 1.7), (0.43, 0.0, 1.7), (0.43, -0.43, 1.3)],
                  [(-0.43, -0.43, 0.5), (-0.43, 0.0, 0.5), (-0.43, -0.43, 0.9)], [(0.2, -0.43, 1.7), (0.43, -0.43, 1.7), (0.43, -0.43, 1.45)]):
        pp = [V3(p) for p in pts]
        isl = g.island(0.4); uv = planar(pp)
        g.face(pp, uv, GLASS, isl); g.face(pp[::-1], uv[::-1], GLASS, isl)
    g.boxes = [[0, 0, 1.15, 0.92, 0.92, 2.3]]
    g.info.update(seed=39, pal={PAINT: dict(base=L((0.30, 0.42, 0.34)), rust=0.45, moss=0.3, bleach=0.5, zlow=0.0, zspan=2.0),
                                PAINT2: dict(base=L((0.22, 0.4, 0.25)), rust=0.35, moss=0.25, bleach=0.4)}, hook=hook_phone)
    return g


def hook_phone(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    F.blend(np.ones(len(F.x)), L((0.12, 0.38, 0.25)), R=0.5)
    items = [dict(t='公衆電話', x=0.35, y=0.05, h=0.075, anchor='mm', font='bold')]
    panel_paint(F, np.ones(len(F.x), bool), np.array([0.35, 0.455, 2.22]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.7, 0.1, 300, items, None, ink=(0.8, 0.82, 0.76), seed=6)
    F.blend(sstep(0.5, 0.8, fb3(F.p, 7.0, 2, 5)) * 0.5, L((0.2, 0.22, 0.16)))
    F.commit()


def b_bus_shelter():
    g = Geo('bus_shelter')
    L2 = 6.0; D = 1.6
    # thin flat roof with a deeper front fascia
    box(g, (0, 0, 2.5), (L2, D, 0.09), PAINT, 1.2, faces='xXyYzZ')
    box(g, (0, D / 2 - 0.02, 2.46), (L2, 0.04, 0.2), PAINT, 1.0, faces='xXyYzZ')
    yb = -0.70                                                    # back wall line
    posts_x = [-2.95, -1.5, 0.0, 1.5, 2.95]
    for x in posts_x:
        cyl(g, (x, yb, 0.0), (x, yb, 2.45), 0.045, 0.045, 6, STEEL, 0.8, caps='end')
    for x in (-2.95, 0.0, 2.95):
        cyl(g, (x, 0.68, 0.0), (x, 0.68, 2.45), 0.05, 0.05, 6, STEEL, 0.8, caps='end')
    # back wall frames (glass gone): rails
    for z in (0.35, 1.05, 2.40):
        bar(g, (-2.95, yb, z), (2.95, yb, z), 0.04, 0.06, STEEL, 0.5)
    for x in posts_x:
        pass
    # shards still in the frame corners
    shard = [[(-2.9, yb, 0.4), (-2.3, yb, 0.4), (-2.9, yb, 1.0)], [(-1.45, yb, 2.35), (-0.85, yb, 2.35), (-1.45, yb, 1.6)],
             [(1.55, yb, 0.4), (2.05, yb, 0.4), (1.55, yb, 0.85)], [(2.4, yb, 2.35), (2.9, yb, 2.35), (2.9, yb, 1.8)],
             [(0.05, yb, 0.4), (0.4, yb, 0.4), (0.05, yb, 0.7)]]
    for pts in shard:
        pp = [V3(p) for p in pts]; n = newell(pp)
        if n.y < 0: pp = pp[::-1]
        isl = g.island(0.4); uv = planar(pp)
        g.face(pp, uv, GLASS, isl); g.face(pp[::-1], uv[::-1], GLASS, isl)
    # end panels (side screens) as frames with one big shard
    for sx in (-1, 1):
        x = sx * 2.97
        for z in (0.35, 2.40):
            bar(g, (x, yb, z), (x, 0.68, z), 0.04, 0.06, STEEL, 0.5)
        bar(g, (x, 0.0, 0.35), (x, 0.0, 2.4), 0.04, 0.04, STEEL, 0.5)
        pp = [V3(p) for p in ((x, 0.1, 0.4), (x, 0.65, 0.4), (x, 0.65, 0.9))]
        if (newell(pp).x > 0) != (sx > 0): pp = pp[::-1]
        isl = g.island(0.4); uv = planar(pp)
        g.face(pp, uv, GLASS, isl); g.face(pp[::-1], uv[::-1], GLASS, isl)
    # bench against the back wall (-x half of the shelter)
    for k, y in enumerate((-0.52, -0.40, -0.28)):
        box(g, (-1.2, y, 0.46), (2.6, 0.1, 0.04), WOOD, 0.7, faces='xXyYzZ')
    for x in (-2.4, -1.2, 0.0):
        bar(g, (x, -0.52, 0.0), (x, -0.52, 0.44), 0.05, 0.05, STEEL, 0.3)
        bar(g, (x, -0.28, 0.0), (x, -0.28, 0.44), 0.05, 0.05, STEEL, 0.3)
    # timetable board and stop sign panel on the back wall; a lit-advert box hanging off the end
    box(g, (1.2, yb + 0.04, 1.45), (0.78, 0.04, 1.1), SIGN, 3.0, faces='y')
    box(g, (2.35, yb + 0.04, 1.35), (0.55, 0.04, 0.75), SIGN, 2.0, faces='y')
    box(g, (1.2, yb + 0.04, 1.45), (0.78, 0.04, 1.1), STEEL, 0.3, faces='xXYzZ')
    box(g, (2.35, yb + 0.04, 1.35), (0.55, 0.04, 0.75), STEEL, 0.3, faces='xXYzZ')
    g.boxes = [[0, yb + 0.1, 1.2, 6.0, 0.35, 2.4]]
    g.info.update(seed=41, pal={PAINT: dict(base=L((0.62, 0.64, 0.6)), rust=0.4, moss=0.35, bleach=0.45, leaf=0.5, zlow=2.3, zspan=0.4),
                                STEEL: dict(base=L((0.5, 0.54, 0.5)), rust=0.45, moss=0.3, bleach=0.3)}, hook=hook_shelter)
    return g


def hook_shelter(ctx):
    sel = ctx.sel(SIGN); F = Flat(ctx, sel)
    yb = -0.70
    # timetable board (x 0.81..1.59, z 0.9..2.0): white plate with a grid of numbers
    tt = (np.abs(F.x - 1.2) < 0.4) & (F.z > 0.88) & (F.z < 2.02)
    fr = F.ny > 0.7
    F.blend((tt & fr) * 1.0, L((0.55, 0.55, 0.5)), R=0.6)
    items = [dict(t='都庁前', x=0.39, y=1.02, h=0.09, anchor='mm', font='bold'), dict(t='時刻表', x=0.39, y=0.90, h=0.06, anchor='mm', font='bold')]
    for k in range(9):
        items.append(dict(t='%d 00 15 30 45' % (6 + k), x=0.39, y=0.76 - k * 0.075, h=0.05, anchor='mm', font='bold'))
    panel_paint(F, tt & fr, np.array([1.59, yb, 0.9]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.78, 1.12, 240, items, None, ink=(0.08, 0.1, 0.1), seed=7)
    hd = tt & fr & (F.z > 1.88)
    F.blend(hd * 1.0, L((0.05, 0.42, 0.26)), R=0.6)
    panel_paint(F, hd, np.array([1.59, yb, 0.9]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.78, 1.12, 240,
                [dict(t='都営バス', x=0.39, y=1.0, h=0.1, anchor='mm', font='bold')], None, ink=(0.82, 0.84, 0.78), seed=8)
    ad = (np.abs(F.x - 2.35) < 0.3) & (F.z > 0.95) & (F.z < 1.75) & fr
    F.blend(ad * 1.0, L((0.45, 0.5, 0.52)), R=0.6)
    panel_paint(F, ad, np.array([2.65, yb, 0.95]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 0.6, 0.8, 240,
                [dict(t='都庁前', x=0.3, y=0.55, h=0.16, anchor='mm', font='bold'), dict(t='Tocho-mae', x=0.3, y=0.38, h=0.06, anchor='mm', font='bold')],
                None, ink=(0.1, 0.25, 0.18), seed=9)
    F.blend(sstep(0.45, 0.78, fb3(F.p, 5.0, 3, 5)) * 0.5, L((0.3, 0.26, 0.2)))
    F.commit()


reg('bollard', b_bollard, 160.0)
reg('street_lamp', b_street_lamp, 70.0)
reg('guard_rail', b_guard_rail, 90.0)
reg('traffic_signal', b_traffic_signal, 80.0)
reg('bus_pole', b_bus_pole, 90.0)
reg('sign_blue', b_sign_blue, 70.0)
reg('sign_tocho', b_sign_tocho, 70.0)
reg('sign_fallen_panel', b_sign_fallen_panel, 60.0)
reg('vending_machine', lambda: b_vending('vending_machine', 0), 100.0)
reg('vending_machine_b', lambda: b_vending('vending_machine_b', 1), 100.0)
reg('bench', b_bench, 100.0)
reg('trash_bin', b_trash_bin, 100.0)
reg('planter_box', b_planter_box, 90.0)
reg('phone_booth', b_phone_booth, 90.0)
reg('bus_shelter', b_bus_shelter, 60.0)


# =============================================================================================== office leftovers
def b_office_desk():
    g = Geo('office_desk')
    W, D, Hh = 1.4, 0.7, 0.72
    box(g, (0, 0, Hh - 0.015), (W, D, 0.03), PLAS, 1.0, faces='xXyYzZ')
    px = -W / 2 + 0.21                                      # left pedestal with three drawers
    box(g, (px, 0.0, 0.35), (0.40, D - 0.06, 0.66), PAINT, 1.0, faces='xXyYz')
    for k in range(3):
        z = 0.12 + 0.2 * k
        dz = 0.0
        if k == 1: dz = 0.0
        box(g, (px, D / 2 - 0.03 + 0.012 + (0.16 if k == 1 else 0.0), z + 0.095), (0.37, 0.025, 0.175), PAINT, 0.8, faces='xXyYzZ')
        box(g, (px, D / 2 + 0.012 + (0.16 if k == 1 else 0.0), z + 0.15), (0.10, 0.03, 0.02), CHROME, 0.3, faces='xXyz')
    box(g, (px, 0.30 + 0.16 - 0.15, 0.31), (0.34, 0.30, 0.14), INT, 0.6, faces='xXYz')   # the drawer pulled open
    box(g, (W / 2 - 0.02, 0, 0.35), (0.03, D - 0.06, 0.68), PAINT, 1.0, faces='xXyYz')   # right end panel
    box(g, (0.1, -D / 2 + 0.05, 0.43), (W - 0.45, 0.02, 0.4), PAINT, 1.0, faces='xXyYz')  # modesty panel
    g.boxes = [[0, 0, 0.36, 1.4, 0.7, 0.72]]
    g.info.update(seed=51, pal={PAINT: dict(base=L((0.42, 0.44, 0.42)), rust=0.5, moss=0.2, bleach=0.4, zlow=0.0, zspan=0.8),
                                PLAS: dict(base=L((0.46, 0.42, 0.33)), rust=0.0, moss=0.3, bleach=0.4)}, hook=hook_drawers)
    return g


def hook_drawers(ctx):
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    # drawer seams on faces that look +y
    fr = F.ny > 0.7
    for k in range(3):
        z = 0.12 + 0.2 * k
        for zz in (z, z + 0.19):
            F.blend((fr * (np.abs(F.z - zz) < 0.0035)) * 0.8, L((0.03, 0.03, 0.03)), dH=-0.003)
    F.commit()


def b_office_chair():
    g = Geo('office_chair')
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        c, s_ = math.cos(a), math.sin(a)
        bar(g, (0, 0, 0.10), (0.32 * c, 0.32 * s_, 0.07), 0.045, 0.03, STEEL, 0.4, caps='both')
        cyl(g, (0.34 * c, 0.34 * s_, 0.0), (0.34 * c, 0.34 * s_, 0.055), 0.028, 0.028, 6, TYRE, 0.3, caps='end')
    cyl(g, (0, 0, 0.09), (0, 0, 0.42), 0.028, 0.028, 6, STEEL, 0.4, caps='end')
    box(g, (0, 0.0, 0.46), (0.50, 0.47, 0.09), FAB, 1.0, faces='xXyYzZ')
    # backrest on a post, leaning back
    bar(g, (0, -0.20, 0.46), (0, -0.28, 0.72), 0.05, 0.03, STEEL, 0.4, caps='both')
    box(g, (0, -0.30, 0.86), (0.46, 0.07, 0.46), FAB, 1.0, rot=None, faces='xXyYzZ')
    for sx in (-1, 1):
        bar(g, (sx * 0.26, -0.05, 0.50), (sx * 0.26, -0.16, 0.68), 0.025, 0.025, STEEL, 0.3, caps='both')
        box(g, (sx * 0.26, 0.04, 0.68), (0.06, 0.26, 0.03), PLAS, 0.4, faces='xXyYz')
    g.boxes = [[0, 0, 0.45, 0.62, 0.62, 0.9]]
    g.info.update(seed=53, pal={FAB: dict(base=L((0.07, 0.09, 0.12))), STEEL: dict(base=L((0.2, 0.2, 0.2)), rust=0.6, moss=0.2, bleach=0.1),
                                PLAS: dict(base=L((0.08, 0.08, 0.08)), moss=0.3, bleach=0.2)})
    return g


def b_filing_cabinet():
    g = Geo('filing_cabinet')
    W, D, Hh = 0.45, 0.62, 1.32
    box(g, (0, 0, Hh / 2), (W, D, Hh), PAINT, 1.0, faces='xXyYz')
    for k in range(4):
        z0 = 0.06 + 0.32 * k
        out = 0.0 if k != 2 else 0.22
        box(g, (0, D / 2 + out, z0 + 0.14), (W - 0.03, 0.02, 0.29), PAINT, 0.8, faces='xXyzZ')
        box(g, (0, D / 2 + out + 0.025, z0 + 0.22), (0.14, 0.04, 0.025), CHROME, 0.3, faces='xXyz')
        if k == 2:
            box(g, (0, D / 2 + out / 2 - 0.02, z0 + 0.05), (W - 0.06, out, 0.1), INT, 0.5, faces='xXz')
    g.boxes = [[0, 0.05, Hh / 2, W, D + 0.2, Hh]]
    g.info.update(seed=55, pal={PAINT: dict(base=L((0.40, 0.45, 0.40)), rust=0.55, moss=0.25, bleach=0.4, zlow=0.0, zspan=1.4)}, hook=hook_cabinet)
    return g


def hook_cabinet(ctx):
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    fr = F.ny > 0.7
    for k in range(4):
        z0 = 0.06 + 0.32 * k
        lab = fr & (np.abs(F.x) < 0.1) & (F.z > z0 + 0.255) & (F.z < z0 + 0.285)
    F.commit()


def b_doc_boxes():
    g = Geo('doc_boxes')
    labels = []
    specs = [((-0.38, -0.2, 0.13), (0.40, 0.33, 0.26), 0.0), ((0.04, -0.2, 0.13), (0.40, 0.33, 0.26), 0.07),
             ((-0.22, -0.2, 0.39), (0.40, 0.33, 0.26), -0.12), ((0.35, 0.15, 0.13), (0.40, 0.33, 0.26), 1.2)]
    for k, (c, sz, rz) in enumerate(specs):
        box(g, c, sz, CARD, 1.2, rot=rz, faces='xXyYzZ')
        # lid band and a hand hole on the end face
        box(g, (c[0], c[1], c[2] + sz[2] / 2 - 0.045), (sz[0] + 0.01, sz[1] + 0.01, 0.07), CARD, 1.0, rot=rz, faces='xXyY')
        R = Matrix.Rotation(rz, 3, 'Z')
        hp = V3(c) + R @ V3((0, sz[1] / 2 + 0.006, -0.02))
        box(g, hp, (0.12, 0.012, 0.035), INT, 0.4, rot=rz, faces='y')
        labels.append((tuple(V3(c) + R @ V3((0.0, sz[1] / 2 + 0.008, 0.05))), rz))
    g.info['labels'] = labels
    g.boxes = [[-0.1, -0.1, 0.26, 0.9, 0.5, 0.52]]
    g.info.update(seed=57, hook=hook_docs)
    return g


def hook_docs(ctx):
    g = ctx.g
    sel = ctx.sel(CARD); F = Flat(ctx, sel)
    txt = ['総務局', '文書保存箱', '令和41年度', '保存期間 10年']
    for k, (c, rz) in enumerate(g.info['labels']):
        R = Matrix.Rotation(rz, 3, 'Z')
        u = np.array(R @ V3((-1, 0, 0))); v = np.array([0, 0, 1.0]); n = np.array(R @ V3((0, 1, 0)))
        o = np.array(V3(c) + V3((0.14 * math.cos(rz), 0.14 * math.sin(rz), 0)) - V3((0, 0, 0.06)))
        near = (np.abs((F.p - np.array(c)) @ v) < 0.1) & (np.abs((F.p - np.array(c)) @ u) < 0.15) & (F.n @ n > 0.9) & (np.abs((F.p - np.array(c)) @ n) < 0.02)
        F.blend(near * 1.0, L((0.62, 0.6, 0.5)), R=0.8)
        items = [dict(t=txt[k % 4], x=0.14, y=0.085, h=0.045, anchor='mm', font='bold'), dict(t='第%d号' % (k + 3), x=0.14, y=0.035, h=0.03, anchor='mm', font='bold')]
        panel_paint(F, near, o, u, v, 0.28, 0.12, 400, items, None, ink=(0.1, 0.1, 0.1), seed=k + 3)
    F.commit()


def b_binders():
    g = Geo('binders')
    cols = [(0.12, 0.2, 0.42), (0.1, 0.32, 0.18), (0.45, 0.08, 0.08), (0.1, 0.1, 0.1), (0.3, 0.3, 0.32), (0.45, 0.33, 0.1)]
    g.info['cols'] = cols
    z = 0.0
    for k in range(4):
        box(g, (0.01 * k, 0.0, z + 0.027), (0.31, 0.28, 0.055), PLAS, 1.0, rot=0.13 * (k - 1.5), faces='xXyYzZ')
        z += 0.055
    # two standing against the stack: leaning boxes made with a pivot matrix
    for k in range(2):
        Rm = Matrix.Rotation(-0.22 - 0.04 * k, 3, 'Y')
        box(g, (0.34 + 0.06 * k, 0.02, 0.15), (0.05, 0.28, 0.31), PLAS, 1.0, rot=Rm, faces='xXyYzZ')
    g.boxes = [[0.15, 0, 0.12, 0.7, 0.32, 0.25]]
    g.info.update(seed=59, hook=hook_binders)
    return g


def hook_binders(ctx):
    g = ctx.g
    sel = ctx.sel(PLAS); F = Flat(ctx, sel)
    cols = g.info['cols']
    idx = np.floor(np.abs(F.z) / 0.055).astype(int)
    for k in range(len(cols)):
        pass
    h = (_h3((F.x * 40).astype(np.int64) // 8, (F.z * 20).astype(np.int64), np.zeros(len(F.x), np.int64), 5) * 5.99).astype(int)
    zone = np.floor(F.z / 0.055).astype(int).clip(0, 3)
    cc = np.array(cols)[(zone + (F.x > 0.28) * 4) % 6]
    F.blend(np.ones(len(F.x)), L(cc) * 0.9, R=0.55)
    F.blend(sstep(0.45, 0.72, fb3(F.p, 6.0, 3, 5)) * 0.55, L((0.3, 0.28, 0.2)), R=0.9)
    F.blend(sstep(0.62, 0.8, fb3(F.p, 4.0, 3, 8)) * 0.5, L((0.2, 0.25, 0.12)), R=0.95)
    sp = (F.ny > 0.7) & (np.abs(F.x) < 0.2) & (F.z % 0.055 > 0.012) & (F.z % 0.055 < 0.043) & (F.z < 0.22)
    F.blend(sp * 0.9, L((0.62, 0.6, 0.52)), R=0.8)
    F.commit()


def b_briefcase():
    g = Geo('briefcase')
    W, H, T = 0.44, 0.31, 0.12
    r = 0.04
    pts = [(-W / 2 + r, 0), (W / 2 - r, 0), (W / 2, r), (W / 2, H - r), (W / 2 - r, H), (-W / 2 + r, H), (-W / 2, H - r), (-W / 2, r)]
    extrude(g, pts, 'y', -T / 2, T / 2, FAB, 1.2)
    for sx in (-0.15, 0.15):
        box(g, (sx, T / 2 + 0.006, H - 0.04), (0.05, 0.012, 0.03), CHROME, 0.2, faces='yzxX')
    tube(g, [(-0.07, 0, H), (-0.07, 0, H + 0.05), (0.07, 0, H + 0.05), (0.07, 0, H)], 0.012, 5, PAINT2, 0.3, caps='both')
    g.boxes = [[0, 0, 0.16, 0.44, 0.12, 0.34]]
    g.info.update(seed=61, pal={FAB: dict(base=L((0.10, 0.065, 0.04)), moss=0.35), PAINT2: dict(base=L((0.07, 0.05, 0.04)), rust=0.0, moss=0.2)})
    return g


def b_umbrella():
    g = Geo('umbrella')
    n = 8
    prof = [(0.0, 0.34), (0.22, 0.285), (0.42, 0.18), (0.56, 0.02)]
    # canopy: custom gores so a couple can be torn away
    ring = lambda r, t, k: V3((r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n), t))
    isl = g.island(1.2); isl2 = g.island(0.6)
    gone = {2, 3}
    for i in range(len(prof) - 1):
        (ra, ta), (rb, tb) = prof[i], prof[i + 1]
        for k in range(n):
            if k in gone and i >= 1: continue
            k2 = (k + 1) % n
            if ra < 1e-6:
                pts = [ring(ra, ta, k), ring(rb, tb, k), ring(rb, tb, k2)]
            else:
                pts = [ring(ra, ta, k), ring(rb, tb, k), ring(rb, tb, k2), ring(ra, ta, k2)]
            nn = newell(pts)
            if nn.z < 0: pts = pts[::-1]
            uv = planar(pts); mn = (min(u[0] for u in uv), min(u[1] for u in uv))
            uvq = [(a - mn[0] + k * 0.15, b - mn[1] + i * 0.3) for a, b in uv]
            g.face(pts, uvq, FAB, isl)
            g.face(pts[::-1], [(a, b + 0.01) for a, b in uvq][::-1], FAB, isl2)
    for k in range(n):                                   # ribs
        a = ring(0.0, 0.335, k); b = ring(0.55, 0.03, k)
        bar(g, a, b, 0.008, 0.008, STEEL, 0.3, caps='none')
    cyl(g, (0, 0, -0.55), (0, 0, 0.36), 0.009, 0.009, 6, STEEL, 0.3, caps='both')
    tube(g, [(0, 0, -0.55), (0.0, 0.0, -0.60), (0.04, 0, -0.64), (0.09, 0, -0.62), (0.10, 0, -0.57)], 0.014, 6, PAINT2, 0.4, caps='both')
    # lay it on its side: axis +z -> mostly +x, resting on the canopy rim and the handle
    Rm = Matrix.Rotation(math.radians(-80), 3, 'Y') @ Matrix.Rotation(0.4, 3, 'Z')
    g.V = [tuple(Rm @ V3(v)) for v in g.V]
    zmin = min(v[2] for v in g.V)
    cx = 0.5 * (min(v[0] for v in g.V) + max(v[0] for v in g.V)); cy = 0.5 * (min(v[1] for v in g.V) + max(v[1] for v in g.V))
    g.V = [(v[0] - cx, v[1] - cy, v[2] - zmin) for v in g.V]
    g.info.update(seed=63, pal={FAB: dict(base=L((0.06, 0.08, 0.16)), moss=0.4), STEEL: dict(base=L((0.25, 0.25, 0.24)), rust=0.7, moss=0.1, bleach=0.1),
                                PAINT2: dict(base=L((0.05, 0.04, 0.04)), rust=0.0, moss=0.2)})
    return g


def b_pc_monitor():
    g = Geo('pc_monitor')
    box(g, (0, 0, 0.30), (0.56, 0.035, 0.34), PLAS, 1.0, faces='xXYzZ')
    pts = [V3((0.26, 0.0175, 0.14)), V3((-0.26, 0.0175, 0.14)), V3((-0.26, 0.0175, 0.45)), V3((0.26, 0.0175, 0.45))]
    g.facen(pts, GLASS, g.island(1.2), (0, 1, 0))
    box(g, (0, -0.03, 0.30), (0.4, 0.03, 0.2), PLAS, 0.6, faces='xXyYz')
    box(g, (0, -0.04, 0.13), (0.07, 0.04, 0.2), PLAS, 0.5, faces='xXyYz')
    box(g, (0, -0.02, 0.01), (0.26, 0.2, 0.025), PLAS, 0.8, faces='xXyYzZ')
    g.boxes = [[0, 0, 0.23, 0.56, 0.25, 0.46]]
    g.info.update(seed=65, pal={PLAS: dict(base=L((0.07, 0.07, 0.075)), moss=0.3, bleach=0.5)})
    return g


reg('office_desk', b_office_desk, 100.0)
reg('office_chair', b_office_chair, 100.0)
reg('filing_cabinet', b_filing_cabinet, 100.0)
reg('doc_boxes', b_doc_boxes, 130.0)
reg('binders', b_binders, 130.0)
reg('briefcase', b_briefcase, 120.0)
reg('umbrella', b_umbrella, 100.0)
reg('pc_monitor', b_pc_monitor, 110.0)


# =============================================================================================== bus, truck, bicycle, scooter
def two_tone(ctx, sel, A, B, maskfn, **kw):
    """weather the same selection with two base colours, pick per pixel (same rust pattern)"""
    p = ctx.P[sel].astype(np.float64)
    m = maskfn(p, ctx.N[sel].astype(np.float64)).astype(float)
    weather(ctx, sel, A, **kw)
    A1, R1, M1, H1 = ctx.A[sel].copy(), ctx.R[sel].copy(), ctx.Mt[sel].copy(), ctx.H[sel].copy()
    weather(ctx, sel, B, **kw)
    mm = m[:, None]
    ctx.A[sel] = A1 * (1 - mm) + ctx.A[sel] * mm
    ctx.R[sel] = R1 * (1 - m) + ctx.R[sel] * m
    ctx.Mt[sel] = M1 * (1 - m) + ctx.Mt[sel] * m
    ctx.H[sel] = H1 * (1 - m) + ctx.H[sel] * m


def arch_skirt(y0, y1, arches, z0=0.40, z1=1.15, R=0.62, zc=0.50):
    pts = [(y1, z1), (y0, z1), (y0, z0)]
    for yc in sorted(arches):
        if yc - R > y0 and yc + R < y1:
            pts.append((yc - R, z0))
            for a in np.linspace(math.pi, 0, 9): pts.append((yc + R * math.cos(a), zc + R * math.sin(a)))
            pts.append((yc + R, z0))
    pts.append((y1, z0))
    return pts


def b_bus():
    g = Geo('bus')
    hw = 1.25; L2 = 5.25
    axf, axr = 2.85, -2.35
    box(g, (0, 0, 0.60), (2.4, 10.3, 0.40), UNDER, 0.25, faces='xXyYZ')
    box(g, (0, 0, 0.60), (2.4, 10.3, 0.40), INT, 0.4, faces='z')
    doorsL = [(3.5, 4.8), (-1.0, 0.4)]
    # skirts (lower side panels with wheel arches); doors open on the left (-x)
    def sk(y0, y1, sd):
        poly2 = arch_skirt(y0, y1, [axf, axr])
        if sd > 0: extrude(g, poly2, 'x', 1.20, 1.25, PAINT, 1.0, tags={'cap0': INT}, ms={'cap0': 0.3, 'cap1': 1.0, 'side': 0.3})
        else: extrude(g, poly2, 'x', -1.25, -1.20, PAINT, 1.0, tags={'cap1': INT}, ms={'cap1': 0.3, 'cap0': 1.0, 'side': 0.3})
    sk(-5.2, 5.2, 1)
    sk(-5.2, -1.0, -1); sk(0.4, 3.5, -1); sk(4.8, 5.2, -1)
    # window pillars and sill rails
    ys = [-5.0, -3.9, -2.8, -1.7, -0.6, 0.5, 1.6, 2.7, 3.8, 4.9]
    for sd in (1, -1):
        for y in ys:
            if sd < 0 and any(a - 0.05 < y < b + 0.05 for a, b in doorsL): continue
            box(g, (sd * 1.225, y, 1.68), (0.07, 0.11, 1.06), PAINT2, 0.5, faces='xXyY')
        segs = [(-5.2, 5.2)] if sd > 0 else [(-5.2, -1.0), (0.4, 3.5), (4.8, 5.2)]
        for a, b in segs:
            box(g, (sd * 1.225, (a + b) / 2, 1.17), (0.07, b - a, 0.06), PAINT2, 0.5, faces='xXz')
    # door frames on the left
    for a, b in doorsL:
        for y in (a, b):
            box(g, (-1.225, y, 1.3), (0.07, 0.08, 1.8), PAINT2, 0.5, faces='xXyY')
    # upper hull (roof rail band + roof)
    hull = [(-1.25, 2.2), (1.25, 2.2), (1.25, 2.55), (1.19, 2.85), (0.92, 2.97), (-0.92, 2.97), (-1.19, 2.85), (-1.25, 2.55)]
    extrude(g, hull, 'y', -L2, L2, PAINT, 1.0, ms={'cap0': 1.0, 'cap1': 1.0, 'side': 1.0})
    box(g, (0, -0.8, 3.03), (1.7, 2.6, 0.12), PAINT2, 0.8, faces='xXyYz')           # roof air conditioner
    box(g, (0, 2.6, 3.0), (0.8, 0.8, 0.07), PAINT2, 0.5, faces='xXyYz')
    # front fascia and screen pillars
    box(g, (0, 5.0, 0.775), (2.5, 0.5, 0.75), PAINT, 1.0, faces='xXyz')
    box(g, (0, 5.3, 0.52), (2.4, 0.14, 0.22), PAINT2, 0.6, faces='xXyYz')
    for x in (-1.2, 0, 1.2):
        box(g, (x, 5.2, 1.68), (0.09, 0.07, 1.06), PAINT2, 0.5, faces='xXyY')
    # rear
    box(g, (0, -4.95, 0.9), (2.5, 0.6, 1.0), PAINT, 1.0, faces='xXYz')
    for x in (-1.2, 0, 1.2):
        box(g, (x, -5.2, 1.8), (0.09, 0.07, 0.8), PAINT2, 0.5, faces='xXyY')
    for sd in (1, -1):
        bar(g, (sd * 1.26, 5.0, 1.85), (sd * 1.38, 5.15, 1.95), 0.03, 0.03, PAINT2, 0.3)
        box(g, (sd * 1.40, 5.15, 1.85), (0.05, 0.2, 0.42), PAINT2, 0.5, faces='xXyYzZ')
    # driver's area
    box(g, (0, 4.72, 1.4), (2.3, 0.45, 0.5), INT, 0.5, faces='xXyz')
    cyl(g, (0.72, 4.5, 1.55), (0.72, 4.41, 1.68), 0.2, 0.2, 8, INT, 0.3, caps='both')
    seat(g, 0.72, 3.95, 0.8, 0.5, 0.5, 0.7, 1, FAB)
    # passenger seats
    for y in (-4.3, -3.5, -2.7, -1.9, -1.1, -0.3, 0.5):
        seat(g, 0.72, y, 0.8, 0.9, 0.46, 0.6, 1, FAB)
    for y in (-4.3, -3.5, -2.7, -1.9, 1.1, 1.9):
        seat(g, -0.9, y, 0.8, 0.42, 0.46, 0.6, 1, FAB)
    for (x, y) in ((0.3, -3.0), (0.3, -0.6), (-0.35, 0.0), (-0.3, 4.1), (0.3, 3.0), (0.3, 4.6)):
        cyl(g, (x, y, 0.8), (x, y, 2.2), 0.02, 0.02, 5, STEEL, 0.3, caps='none')
    # wheels (rear pair is a dual-wheel pair, drawn as one wide tyre)
    for sd in (1, -1):
        wheel(g, sd * 1.12, axf, 0.5, 0.14, sd, 0.06, 0.3, n=12, phase=0.2)
        wheel(g, sd * 1.10, axr, 0.5, 0.22, sd, 0.06, 0.3, n=12, phase=0.4)
    g.boxes = [[0, 0, 1.55, 2.5, 10.5, 3.1]]
    g.info.update(seed=71, hook=hook_bus, pal={
        PAINT: dict(base=L((0.62, 0.64, 0.60)), rust=0.3, moss=0.25, bleach=0.5, streak=0.6, leaf=0.4, zlow=0.4, zspan=2.6),
        PAINT2: dict(base=L((0.15, 0.16, 0.15)), rust=0.35, moss=0.3, bleach=0.3),
        FAB: dict(base=L((0.10, 0.14, 0.16)), moss=0.6)})
    return g


def hook_bus(ctx):
    g = ctx.g
    sel = ctx.sel(PAINT)
    green = L((0.10, 0.45, 0.27)); white = L((0.66, 0.67, 0.62))
    def mk(p, n):
        band = (p[:, 2] < 1.14) | ((p[:, 2] > 2.28) & (p[:, 2] < 2.50) & (np.abs(n[:, 0]) > 0.5))
        return band
    two_tone(ctx, sel, white, green, mk, seed=71, rust=0.3, moss=0.25, bleach=0.5, streak=0.6, leaf=0.4, zlow=0.4, zspan=2.6, rough=0.6)
    F = Flat(ctx, sel)
    right = (F.nx > 0.7); left = (F.nx < -0.7); front = (F.ny > 0.7) & (F.y > 5.2); rear = (F.ny < -0.7) & (F.y < -5.2)
    # side lettering on the green skirt (right side reads rear -> front)
    its = [dict(t='都営バス', x=3.6, y=0.30, h=0.26, anchor='lm', font='bold'), dict(t='TOEI BUS', x=5.4, y=0.30, h=0.13, anchor='lm', font='bold')]
    cvR = text_canvas(10.4, 0.75, 70, its)
    a = canvas_sample(F, right & (F.z < 1.14), cvR, 70, np.array([-5.2, 0, 0.4]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0]))
    F.blend(a * wear_mask(F, 7, 0.7), L((0.78, 0.8, 0.74)), R=0.6)
    cvL = text_canvas(10.4, 0.75, 70, its)
    a = canvas_sample(F, left & (F.z < 1.14), cvL, 70, np.array([5.2, 0, 0.4]), np.array([0, -1.0, 0]), np.array([0, 0, 1.0]))
    F.blend(a * wear_mask(F, 8, 0.7), L((0.78, 0.8, 0.74)), R=0.6)
    # destination board (front) and rear number board
    ds = front & (F.z > 2.3) & (F.z < 2.9) & (np.abs(F.x) < 0.95)
    F.blend(ds * 1.0, L((0.025, 0.028, 0.03)), R=0.35)
    panel_paint(F, ds, np.array([0.95, 5.25, 2.3]), np.array([-1.0, 0, 0]), np.array([0, 0, 1.0]), 1.9, 0.6, 160,
                [dict(t='宿75 新宿駅西口', x=0.95, y=0.34, h=0.20, anchor='mm', font='bold'), dict(t='都庁前 経由', x=0.95, y=0.13, h=0.11, anchor='mm', font='bold')],
                None, ink=(0.55, 0.32, 0.06), wear=0.7, seed=4)
    # headlamps and bumper-line dark, front plate
    zl = (F.z > 0.75) & (F.z < 1.0)
    for sd in (-1, 1):
        hl = front & zl & (np.abs(F.x - sd * 0.95) < 0.24)
        F.blend(hl * 1.0, L((0.04, 0.045, 0.05)), R=0.3)
        F.blend(hl * sstep(0.5, 0.85, fb3(F.p, 14.0, 2, 3)) * 0.4, L((0.3, 0.3, 0.26)))
    tl = rear & (F.z > 0.85) & (F.z < 1.1) & (np.abs(np.abs(F.x) - 0.95) < 0.2)
    F.blend(tl * 1.0, L((0.32, 0.05, 0.04)), R=0.4)
    gr = rear & (F.z > 0.5) & (F.z < 0.82) & (np.abs(F.x) < 0.7)
    F.blend(gr * (((F.z * 40) % 1) < 0.5) * 0.9, L((0.03, 0.03, 0.03)))
    F.blend(front & (np.abs(F.x) < 0.2) & (F.z > 0.55) & (F.z < 0.7), L((0.55, 0.55, 0.5)), R=0.5)
    # interior ceiling and wall faces seen through the windows
    ce = (F.nz < -0.7) & (F.z < 2.3) & (F.z > 2.1)
    F.blend(ce * 1.0, L((0.30, 0.30, 0.27)), R=0.9)
    F.blend(ce * sstep(0.45, 0.75, fb3(F.p, 4.0, 3, 9)) * 0.6, L((0.16, 0.2, 0.11)), R=0.95)
    F.commit()


def b_truck_small():
    g = Geo('truck_small')
    cw = 0.845
    # chassis rails and cross members
    for sd in (-1, 1):
        box(g, (sd * 0.5, -0.1, 0.52), (0.1, 4.5, 0.16), UNDER, 0.3, faces='xXyYzZ')
    box(g, (0, -1.9, 0.52), (1.2, 0.1, 0.12), UNDER, 0.2, faces='yYz')
    # cab tub, roof, pillars (cab-over, glass gone)
    box(g, (0, 1.62, 0.87), (1.69, 1.45, 0.5), PAINT, 1.0, faces='xXyYzZ')
    box(g, (0, 0.95, 1.55), (1.69, 0.05, 0.9), PAINT, 1.0, faces='xXyYz')           # rear wall of the cab
    box(g, (0, 1.62, 2.0), (1.72, 1.52, 0.06), PAINT, 1.0, faces='xXyYzZ')
    for sx in (-1, 1):
        bar(g, (sx * 0.82, 2.33, 1.12), (sx * 0.80, 2.22, 1.97), 0.07, 0.07, PAINT2, 0.5, caps='both')
        bar(g, (sx * 0.82, 0.98, 1.12), (sx * 0.82, 1.0, 1.97), 0.08, 0.08, PAINT2, 0.5, caps='both')
        bar(g, (sx * 0.84, 1.58, 1.12), (sx * 0.84, 1.58, 1.97), 0.06, 0.06, PAINT2, 0.5, caps='both')
        box(g, (sx * 0.86, 1.6, 1.12), (0.04, 1.4, 0.05), TRIM, 0.4, faces='xXz')
        bar(g, (sx * 0.9, 2.1, 1.55), (sx * 1.04, 2.17, 1.62), 0.03, 0.03, PAINT2, 0.3)
        box(g, (sx * 1.06, 2.17, 1.62), (0.05, 0.12, 0.38), PAINT2, 0.5, faces='xXyYzZ')
    box(g, (0, 2.33, 0.58), (1.72, 0.14, 0.2), PAINT2, 0.5, faces='xXyYz')           # bumper
    box(g, (0, 1.9, 1.20), (1.5, 0.3, 0.38), INT, 0.5, faces='xXyz')                  # dash
    seat(g, -0.38, 1.45, 1.12, 0.62, 0.5, 0.7, 1, FAB)
    seat(g, 0.38, 1.45, 1.12, 0.62, 0.5, 0.7, 1, FAB)
    cyl(g, (0.38, 1.88, 1.42), (0.38, 1.80, 1.52), 0.18, 0.18, 8, INT, 0.3, caps='both')
    # flatbed with drop sides
    box(g, (0, -0.93, 0.86), (1.7, 2.88, 0.1), WOOD, 1.0, faces='xXYzZ')
    box(g, (0, 0.52, 0.86), (1.7, 0.06, 0.1), WOOD, 0.5, faces='xXyz')
    for sx in (-1, 1):
        box(g, (sx * 0.84, -0.93, 1.08), (0.05, 2.88, 0.34), PAINT, 0.9, faces='xXyYz')
    box(g, (0, -2.35, 1.08), (1.7, 0.05, 0.34), PAINT, 0.9, faces='yYz')
    box(g, (0, 0.55, 1.28), (1.7, 0.06, 0.6), PAINT, 0.9, faces='xXyYz')               # headboard
    # wheels
    for sd in (1, -1):
        wheel(g, sd * 0.78, 1.55, 0.36, 0.1, sd, 0.05, 0.2, n=12, phase=0.1)
        wheel(g, sd * 0.78, -1.3, 0.36, 0.17, sd, 0.05, 0.2, n=12, phase=0.3)
    g.boxes = [[0, 1.55, 1.0, 1.72, 1.6, 2.0], [0, -1.0, 0.5, 1.72, 3.0, 1.1]]
    g.info.update(seed=73, hook=hook_truck, pal={
        PAINT: dict(base=L((0.66, 0.66, 0.62)), rust=0.5, moss=0.25, bleach=0.5, streak=0.6, leaf=0.4, zlow=0.4, zspan=1.6),
        PAINT2: dict(base=L((0.12, 0.13, 0.12)), rust=0.4, moss=0.3, bleach=0.3), FAB: dict(base=L((0.09, 0.10, 0.12)), moss=0.5),
        WOOD: dict(base=L((0.30, 0.25, 0.18)), axis=1, moss=0.5, leaf=0.5)})
    return g


def hook_truck(ctx):
    sel = ctx.sel(PAINT); F = Flat(ctx, sel)
    fr = (F.ny > 0.7) & (F.y > 2.3)
    F.blend(fr * (F.z < 1.12) * 0.5, L((0.06, 0.06, 0.06)), R=0.7)
    for sd in (-1, 1):
        hl = fr & (F.z > 0.7) & (F.z < 0.98) & (np.abs(F.x - sd * 0.58) < 0.18)
        F.blend(hl * 1.0, L((0.04, 0.045, 0.05)), R=0.3)
    gr = fr & (np.abs(F.x) < 0.28) & (F.z > 0.7) & (F.z < 1.0)
    F.blend(gr * (((F.z * 45) % 1) < 0.5), L((0.04, 0.04, 0.04)))
    # corrugation ribs on the drop sides
    side = (np.abs(F.nx) > 0.7) & (F.y < 0.5) & (F.z > 0.9)
    F.blend(side * (np.abs(((F.y * 5.0) % 1) - 0.5) < 0.06) * 0.35, L((0.08, 0.08, 0.08)), dH=-0.004)
    F.commit()


def fender(g, cy, cz, R, hw, a0, a1, n=7, tag=PAINT):
    """curved mudguard over a wheel (axis x), strip of width 2*hw at radius R from angle a0..a1 (rad from +y axis through +z)"""
    isl = g.island(0.5)
    for k in range(n):
        t0 = a0 + (a1 - a0) * k / n; t1 = a0 + (a1 - a0) * (k + 1) / n
        P = lambda t, x: V3((x, cy + R * math.cos(t), cz + R * math.sin(t)))
        pts = [P(t0, -hw), P(t0, hw), P(t1, hw), P(t1, -hw)]
        uv = [(0, 0.04 * k), (hw * 2, 0.04 * k), (hw * 2, 0.04 * (k + 1)), (0, 0.04 * (k + 1))]
        g.face(pts, uv, tag, isl); g.face(pts[::-1], [(a, b) for a, b in uv][::-1], tag, isl)


def b_bicycle():
    g = Geo('bicycle')
    R = 0.34; sag = 0.0
    zax = R - sag
    yf, yr = 0.55, -0.52
    for y in (yf, yr):
        torus(g, (0, y, zax), (1, 0, 0), R - 0.025, 0.025, 12, 4, TYRE, 0.5)
        cyl(g, (-0.05, y, zax), (0.05, y, zax), 0.025, 0.025, 6, STEEL, 0.3, caps='both')
        for k in range(3):
            a = math.pi * k / 3
            p0 = V3((0, y + (R - 0.05) * math.cos(a), zax + (R - 0.05) * math.sin(a))); p1 = V3((0, y - (R - 0.05) * math.cos(a), zax - (R - 0.05) * math.sin(a)))
            pts = [p0 + V3((0.004, 0, 0)), p1 + V3((0.004, 0, 0)), p1 - V3((0.004, 0, 0)), p0 - V3((0.004, 0, 0))]
            isl = g.island(0.2); g.face(pts, [(0, 0), (0.6, 0), (0.6, 0.01), (0, 0.01)], STEEL, isl); g.face(pts[::-1], [(0.7, 0), (0.7, 0.01), (1.3, 0.01), (1.3, 0)][::-1], STEEL, isl)
    fender(g, yf, zax, R + 0.03, 0.03, 0.2, 2.2)
    fender(g, yr, zax, R + 0.03, 0.03, 0.9, 2.95)
    head = V3((0, 0.44, 0.92)); bb = V3((0, 0.02, 0.31)); seatp = V3((0, -0.20, 0.90)); stay = V3((0, yr, zax))
    for sd in (-1, 1):
        tube(g, [V3((sd * 0.04, yf, zax)), V3((sd * 0.04, 0.50, 0.62)), V3((sd * 0.03, 0.46, 0.93))], 0.012, 5, PAINT, 0.5, 'none')
    tube(g, [head + V3((0, -0.02, -0.08)), V3((0, 0.18, 0.55)), bb], 0.02, 6, PAINT, 0.6, 'none')
    tube(g, [bb, seatp], 0.018, 6, PAINT, 0.6, 'none')
    tube(g, [bb, V3((0, -0.30, 0.31)), stay], 0.014, 5, PAINT, 0.5, 'none')
    tube(g, [seatp, V3((0, -0.40, 0.55)), stay], 0.012, 5, PAINT, 0.4, 'none')
    tube(g, [head, V3((0, 0.40, 1.04)), V3((0.2, 0.34, 1.07)), V3((0.38, 0.28, 1.04))], 0.011, 5, STEEL, 0.4, 'none')
    tube(g, [V3((0, 0.40, 1.04)), V3((-0.2, 0.34, 1.07)), V3((-0.38, 0.28, 1.04))], 0.011, 5, STEEL, 0.4, 'none')
    box(g, (0, -0.22, 0.95), (0.18, 0.26, 0.05), PLAS, 0.5, faces='xXyYzZ')
    box(g, (0, -0.55, 0.64), (0.2, 0.32, 0.015), STEEL, 0.4, faces='zZ')
    box(g, (0.05, -0.2, 0.31), (0.03, 0.5, 0.12), PAINT, 0.4, faces='xXz')               # chain guard
    for sd in (-1, 1): box(g, (sd * 0.14, 0.02, 0.31 + sd * 0.0), (0.08, 0.025, 0.02), STEEL, 0.2, faces='zY') if False else None
    # front basket
    bx, by, bz = 0, 0.64, 0.82
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar(g, (sx * 0.17, by + sy * 0.12, bz), (sx * 0.19, by + sy * 0.13, bz + 0.2), 0.012, 0.012, STEEL, 0.3, caps='none')
    for z, dx in ((bz, 0.17), (bz + 0.2, 0.19)):
        for (a, b) in (((-dx, by - 0.12), (dx, by - 0.12)), ((-dx, by + 0.12), (dx, by + 0.12)), ((-dx, by - 0.12), (-dx, by + 0.12)), ((dx, by - 0.12), (dx, by + 0.12))):
            bar(g, (a[0], a[1], z), (b[0], b[1], z), 0.012, 0.012, STEEL, 0.3, caps='none')
    for x in (-0.07, 0.07):
        bar(g, (x, by - 0.12, bz), (x, by + 0.12, bz), 0.01, 0.01, STEEL, 0.2, caps='none')
    # pedals, kickstand
    box(g, (0.16, 0.02, 0.24), (0.1, 0.07, 0.025), PLAS, 0.3, faces='xXyYzZ')
    box(g, (-0.16, 0.02, 0.38), (0.1, 0.07, 0.025), PLAS, 0.3, faces='xXyYzZ')
    bar(g, (0, -0.4, 0.31), (0.05, -0.44, 0.0), 0.015, 0.015, STEEL, 0.3, caps='none')
    box(g, (0, 0.52, 0.99), (0.07, 0.05, 0.08), STEEL, 0.3, faces='xXyYz')
    g.boxes = [[0, 0.02, 0.5, 0.45, 1.5, 1.0]]
    g.info.update(seed=75, pal={PAINT: dict(base=L((0.40, 0.55, 0.52)), rust=0.55, moss=0.3, bleach=0.5, zlow=0.0, zspan=1.0),
                                STEEL: dict(base=L((0.45, 0.46, 0.44)), rust=0.7, moss=0.15, bleach=0.2),
                                PLAS: dict(base=L((0.07, 0.07, 0.07)), moss=0.2, bleach=0.5)})
    return g


def b_scooter():
    g = Geo('scooter')
    R = 0.21; sag = 0.0
    zax = R - sag
    yf, yr = 0.62, -0.50
    for sd in (1, -1):
        pass
    for y in (yf, yr):
        torus(g, (0, y, zax), (1, 0, 0), R - 0.05, 0.05, 12, 5, TYRE, 0.6)
        cyl(g, (-0.05, y, zax), (0.06, y, zax), 0.09, 0.09, 8, RIM, 0.4, caps='both')
    # body in side profile (y, z), extruded over the width: floor + rear body + seat base
    rear = [(-0.72, 0.36), (-0.80, 0.55), (-0.64, 0.72), (-0.12, 0.74), (-0.02, 0.50), (-0.02, 0.32)]
    extrude(g, rear, 'x', -0.16, 0.16, PAINT, 1.0)
    extrude(g, [(-0.02, 0.26), (0.46, 0.26), (0.46, 0.34), (-0.02, 0.34)], 'x', -0.21, 0.21, PAINT, 0.8)
    leg = [(0.40, 0.28), (0.52, 0.30), (0.60, 0.95), (0.52, 0.98), (0.42, 0.55)]
    extrude(g, leg, 'x', -0.16, 0.16, PAINT, 1.0)
    box(g, (0, -0.30, 0.78), (0.30, 0.58, 0.09), PLAS, 0.8, faces='xXyYzZ')            # seat
    box(g, (0, -0.78, 0.60), (0.2, 0.06, 0.1), LAMP, 0.4, faces='Y')                    # tail lamp
    box(g, (0, -0.35, 0.42), (0.14, 0.4, 0.2), PAINT2, 0.6, faces='xXzZ')               # engine casing, left
    box(g, (0.17, -0.55, 0.3), (0.1, 0.5, 0.2), PAINT2, 0.6, faces='xXyYz')
    for sd in (-1, 1):
        tube(g, [V3((sd * 0.06, yf, zax)), V3((sd * 0.06, 0.66, 0.6)), V3((sd * 0.05, 0.62, 0.95))], 0.014, 5, STEEL, 0.4, 'none')
        tube(g, [V3((sd * 0.05, 0.60, 1.0)), V3((sd * 0.3, 0.56, 1.05))], 0.012, 5, STEEL, 0.3, 'none')
        bar(g, (sd * 0.3, 0.56, 1.05), (sd * 0.36, 0.5, 1.28), 0.01, 0.01, STEEL, 0.3)
    box(g, (0, 0.58, 1.0), (0.46, 0.2, 0.16), PAINT, 0.8, faces='xXyYzZ')
    box(g, (0, 0.70, 0.98), (0.2, 0.08, 0.14), LAMP, 0.5, faces='yxXz')
    fender(g, yf, zax, R + 0.03, 0.06, 0.1, 2.0, 5)
    box(g, (0, -0.74, 0.40), (0.24, 0.22, 0.1), PAINT, 0.4, faces='xXYz')
    g.boxes = [[0, 0, 0.5, 0.45, 1.6, 1.0]]
    g.info.update(seed=77, pal={PAINT: dict(base=L((0.62, 0.20, 0.16)), rust=0.55, moss=0.3, bleach=0.55, zlow=0.0, zspan=1.0),
                                PAINT2: dict(base=L((0.16, 0.16, 0.15)), rust=0.5, moss=0.3, bleach=0.2),
                                STEEL: dict(base=L((0.4, 0.4, 0.38)), rust=0.7, moss=0.15, bleach=0.2),
                                PLAS: dict(base=L((0.05, 0.05, 0.05)), moss=0.45, bleach=0.5),
                                LAMP: dict(base=L((0.45, 0.2, 0.1)), moss=0.2, bleach=0.4)})
    return g


reg('bus', b_bus, 46.0)
reg('truck_small', b_truck_small, 56.0)
reg('bicycle', b_bicycle, 110.0)
reg('scooter', b_scooter, 100.0)


# =============================================================================================== pipeline
def _geos():
    global _G
    if _G is None:
        names = DEV_ONLY or list(BUILDERS)
        gs = [BUILDERS[n]() for n in names]
        layout(gs)
        for g in gs:
            x, y, w, h = g.rect
            REGIONS[g.name] = (x / ATLAS, y / ATLAS, (x + w) / ATLAS, (y + h) / ATLAS)
        _G = {g.name: g for g in gs}
    return _G


def normal_map(H, ppm, k=1.0):
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5 * ppm * k
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5 * ppm * k
    n = np.dstack([-dx, -dy, np.ones_like(H)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def bake_ao(gs, samples=384, dist=3.0, log=print):
    """Cycles GPU AO of every model alone on a ground plane, baked into the atlas layout. returns (ATLAS, ATLAS) float"""
    sc = bpy.context.scene
    old = (sc.render.engine, sc.cycles.samples, sc.cycles.device, sc.cycles.use_denoising, sc.world)
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    sc.cycles.device = 'GPU'; sc.cycles.samples = samples
    w = bpy.data.worlds.new('props_ao_world'); sc.world = w
    w.light_settings.distance = dist
    w.use_nodes = True
    # build one object carrying every model on a grid of cells so they never see each other
    Vs = []; Fs = []; UVs = []
    cols = 6; sp = 24.0
    for k, g in enumerate(gs):
        ox = (k % cols) * sp; oy = (k // cols) * sp
        base = len(Vs)
        Vs += [(v[0] + ox, v[1] + oy, v[2]) for v in g.V]
        Fs += [[i + base for i in f] for f in g.F]
        UVs += [[(x / ATLAS, y / ATLAS) for x, y in f] for f in g.UVpx]
    me = bpy.data.meshes.new('props_ao_mesh'); me.from_pydata(Vs, [], Fs); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for fi, p in enumerate(me.polygons):
        for j, lo in enumerate(p.loop_indices): uvl.data[lo].uv = UVs[fi][j]
    ob = bpy.data.objects.new('props_ao_obj', me)
    sc.collection.objects.link(ob)
    img = bpy.data.images.new('props_ao_bake', ATLAS, ATLAS, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    mat = bpy.data.materials.new('props_ao_mat'); mat.use_nodes = True
    nt = mat.node_tree
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; nt.nodes.active = tn
    me.materials.append(mat)
    # ground
    gm = bpy.data.meshes.new('props_ao_ground')
    ext = 400.0
    gm.from_pydata([(-ext, -ext, 0), (ext * 2, -ext, 0), (ext * 2, ext * 2, 0), (-ext, ext * 2, 0)], [], [[0, 1, 2, 3]])
    gob = bpy.data.objects.new('props_ao_ground', gm); sc.collection.objects.link(gob)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO', margin=PAD - 1, margin_type='EXTEND', use_clear=True)
    px = np.empty(ATLAS * ATLAS * 4, np.float32)
    img.pixels.foreach_get(px)
    ao = px.reshape(ATLAS, ATLAS, 4)[..., 0].copy()
    for o in (ob, gob): bpy.data.objects.remove(o, do_unlink=True)
    for m_ in (me, gm): bpy.data.meshes.remove(m_)
    bpy.data.materials.remove(mat); bpy.data.images.remove(img)
    sc.world = old[4]; bpy.data.worlds.remove(w)
    sc.render.engine, sc.cycles.samples, sc.cycles.device, sc.cycles.use_denoising = old[:4]
    return ao


def build_textures(bake=True, log=print):
    gs = list(_geos().values())
    N = ATLAS
    mp = Maps()
    raster(gs, mp); dilate(mp)
    COL = np.full((N, N, 3), 0.30); NRM = np.zeros((N, N, 3)) + (0.5, 0.5, 1.0); ORM = np.zeros((N, N, 3)) + (1.0, 0.85, 0.0)
    for g in gs:
        ctx = Ctx(g, mp)
        PAINTERS[g.name](ctx)
        H = ctx.H
        mb = ctx.msk
        if mb.any():
            pp = ctx.P[mb].astype(np.float64)
            H[mb] += (0.0014 * (fb3(pp, 60.0, 2, 3) - 0.5) + 0.0006 * (vn3(pp, 210.0, 5) - 0.5)).astype(np.float32)
        cav = np.clip(T.blur(H, 2) - H, -0.01, 0.01) * 80.0           # + in dents
        O = ctx.O * np.clip(1 - 0.5 * np.clip(cav, 0, 1), 0, 1)
        m = ctx.msk
        nm = normal_map(H, ctx.ppm, 1.0)
        sl = ctx.sl
        COL[sl][m] = T.srgb(ctx.A[m]); NRM[sl][m] = nm[m]
        ORM[sl][m] = np.stack([O[m], ctx.R[m], ctx.Mt[m]], 1)
        # keep the cavity for the bake multiply
        g.info['cav'] = O; g.info['msk'] = m
    if bake:
        ao = bake_ao(gs)
        ao = np.clip(ao, 0, 1)
        for g in gs:
            x, y, w, h = g.rect
            sl = (slice(y, y + h), slice(x, x + w))
            m = g.info['msk']
            ORM[sl][..., 0] = np.where(m, ao[sl] * g.info['cav'], ORM[sl][..., 0])
    T.save_png('props_col', COL)
    T.save_png('props_nrm', NRM)
    T.save_png('props_orm', ORM)
    for n in ('props_col', 'props_nrm', 'props_orm'):
        path = C.TEX + n + '.png'
        im = bpy.data.images.get(n)
        if im is None:
            im = bpy.data.images.load(path); im.name = n
        else:
            im.source = 'FILE'; im.filepath = path; im.reload()
        im.colorspace_settings.name = 'sRGB' if n == 'props_col' else 'Non-Color'


def models():
    gs = _geos()
    col = bpy.data.collections.get('props_lib')
    if col is None:
        col = bpy.data.collections.new('props_lib'); bpy.context.scene.collection.children.link(col)
    out = {}
    for name, g in gs.items():
        old = bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old, do_unlink=True)
        out[name] = make_object(g, col)
    col.hide_render = True
    lc = bpy.context.view_layer.layer_collection.children.get('props_lib')
    if lc: lc.hide_viewport = True
    return out


# =============================================================================================== preview / test
PREVIEW = C.WORK + 'props_preview/'


def _ground_plane(size=200.0, col=(0.20, 0.19, 0.17)):
    me = bpy.data.meshes.new('pv_ground')
    me.from_pydata([(-size, -size, -0.01), (size, -size, -0.01), (size, size, -0.01), (-size, size, -0.01)], [], [[0, 1, 2, 3]])
    ob = bpy.data.objects.new('pv_ground', me); bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new('pv_ground'); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = col + (1,); bs.inputs['Roughness'].default_value = 0.95
    me.materials.append(m)
    return ob


def _place(ob, x, y, rot=0.0, scene_col=None):
    ob2 = ob.copy()
    (scene_col or bpy.context.scene.collection).objects.link(ob2)
    ob2.location = (x, y, 0); ob2.rotation_euler = (0, 0, rot)
    return ob2


def _dims(o):
    return max(o.dimensions.x, o.dimensions.y, o.dimensions.z)


def shoot_model(ms, name, tag, yaw_deg=35.0, elev_deg=14.0, dist=None, lens=40, res=(1100, 700), look_z=None, shift=(0, 0)):
    """render one model alone at the origin; yaw rotates the model; camera on -y looking +y"""
    o = ms[name]; sc = bpy.context.scene
    c = _place(o, 0, 0, math.radians(yaw_deg), sc.collection)
    d = dist or _dims(o) * 1.6 + 1.0
    lz = look_z if look_z is not None else o.dimensions.z * 0.42
    el = math.radians(elev_deg)
    pos = (shift[0], -d * math.cos(el), lz + d * math.sin(el))
    render.shot(PREVIEW + 'm_%s_%s.png' % (name, tag), pos, (shift[0], 0, lz), lens, res)
    bpy.data.objects.remove(c, do_unlink=True)


def tile(ms, name, path, yaw_deg=215.0, elev_deg=16.0, res=(560, 560), fit=1.0, lens=50):
    """one model, framed on its bounding sphere"""
    o = ms[name]; sc = bpy.context.scene
    c = _place(o, 0, 0, math.radians(yaw_deg), sc.collection)
    bpy.context.view_layer.update()
    pts = [c.matrix_world @ V3(p) for p in [(bx, by, bz) for bx in (c.bound_box[0][0], c.bound_box[6][0]) for by in (c.bound_box[0][1], c.bound_box[6][1]) for bz in (c.bound_box[0][2], c.bound_box[6][2])]]
    ctr = sum(pts, V3((0, 0, 0))) / 8
    r = max((p - ctr).length for p in pts)
    d = r * 1.12 / math.sin(math.atan(18.0 / lens)) * fit
    el = math.radians(elev_deg)
    pos = (ctr.x, ctr.y - d * math.cos(el), ctr.z + d * math.sin(el))
    render.shot(path, pos, ctr, lens, res)
    bpy.data.objects.remove(c, do_unlink=True)


def compose(paths, labels, out, cols=4, cell=(560, 560)):
    code = (
        "import sys, json\nfrom PIL import Image, ImageDraw, ImageFont\n"
        "paths, labels, out, cols, cw, ch = json.loads(sys.argv[1])\n"
        "rows = (len(paths) + cols - 1) // cols\n"
        "im = Image.new('RGB', (cols * cw, rows * ch), (40, 40, 40))\n"
        "f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 20)\n"
        "d = ImageDraw.Draw(im)\n"
        "for k, (p, l) in enumerate(zip(paths, labels)):\n"
        "    t = Image.open(p).convert('RGB').resize((cw, ch))\n"
        "    x, y = (k % cols) * cw, (k // cols) * ch\n"
        "    im.paste(t, (x, y)); d.text((x + 8, y + 6), l, font=f, fill=(255, 255, 255))\n"
        "im.save(out)\n")
    subprocess.run([PY_TEXT, '-c', code, json.dumps([paths, labels, out, cols, cell[0], cell[1]])], check=True)


GROUPS = {
    'a_shelter': ['bus_shelter', 'bus_pole', 'vending_machine', 'vending_machine_b'],
    'b_roadside': ['traffic_signal', 'street_lamp', 'guard_rail', 'bollard', 'sign_blue'],
    'd_office': ['office_desk', 'office_chair', 'filing_cabinet', 'doc_boxes', 'binders', 'briefcase', 'umbrella', 'pc_monitor'],
    'c_plaza': ['sign_tocho', 'sign_fallen_panel', 'bench', 'trash_bin', 'phone_booth', 'planter_box'],
    'vehicles': ['car_sedan', 'car_sedan_silver', 'car_sedan_blue', 'car_kei', 'car_minivan', 'taxi'],
    'bus': ['bus', 'truck_small', 'bicycle', 'scooter'],
    'office': ['office_desk', 'office_chair', 'filing_cabinet', 'doc_boxes', 'binders', 'briefcase', 'umbrella', 'pc_monitor'],
}


LINEUPS = {
    'lineup_vehicles': ['car_sedan', 'car_sedan_silver', 'taxi', 'car_minivan', 'bus', 'car_sedan_blue', 'car_kei', 'truck_small', 'bicycle', 'scooter'],
    'lineup_street': ['bus_shelter', 'bus_pole', 'vending_machine', 'vending_machine_b', 'phone_booth', 'bench', 'trash_bin', 'planter_box', 'bollard',
                      'guard_rail', 'sign_blue', 'traffic_signal', 'street_lamp', 'sign_tocho', 'sign_fallen_panel'],
    'lineup_office': ['office_desk', 'office_chair', 'filing_cabinet', 'doc_boxes', 'binders', 'briefcase', 'umbrella', 'pc_monitor'],
}


def lineup(ms, names, path, yaw=160.0, per_row=5, res=(1700, 800), lens=28, elev=14.0, dist=1.0):
    """models laid out in rows on the ground plane (front rows nearest the camera), seen from a low three-quarter height"""
    sc = bpy.context.scene
    rows = [names[i:i + per_row] for i in range(0, len(names), per_row)]
    objs = []; y = 0.0; wmax = 0.0
    for r in rows:
        w = sum(max(ms[n].dimensions.x, ms[n].dimensions.y) + 1.4 for n in r)
        d = max(max(ms[n].dimensions.x, ms[n].dimensions.y) for n in r) + 1.2
        x = -w / 2
        for n in r:
            ww = max(ms[n].dimensions.x, ms[n].dimensions.y) + 1.4
            objs.append(_place(ms[n], x + ww / 2, y, math.radians(yaw), sc.collection)); x += ww
        y += d; wmax = max(wmax, w)
    cy = (y - 1.0) / 2
    D = max(wmax * 0.75, y * 1.1, 7.0) * dist
    el = math.radians(elev)
    render.shot(path, (0, -D * math.cos(el) + cy * 0.0, 1.6 + D * math.sin(el)), (0, cy * 0.8, 0.8), lens, res)
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)


def test(argv=()):
    C.reset()
    log = print
    import time
    t0 = time.time()
    build_textures(bake='nobake' not in argv, log=log)
    ms = models()
    log('textures+models %.1fs' % (time.time() - t0))
    for n, o in ms.items():
        bad, tot = check_orientation(o)
        zs = [v.co.z for v in o.data.vertices]; xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]
        log('%-18s tris %4d  dims %s  zmin %.3f  x[%.2f,%.2f] y[%.2f,%.2f]  boxes %d  flipped %d/%d' % (n, tri_count(o), tuple(round(v, 2) for v in o.dimensions), min(zs), min(xs), max(xs), min(ys), max(ys), len(o['collide']), bad, tot))
    os.makedirs(PREVIEW, exist_ok=True)
    render.setup(samples=40, res=(1600, 700))
    _ground_plane()
    only = [a for a in argv if a in ms]
    views = [a for a in argv if a.startswith('v=')]
    if only:
        for n in only:
            if views:
                for vi, v in enumerate(views):
                    p = [float(t) for t in v[2:].split(':')]
                    shoot_model(ms, n, 'v%d' % vi, p[0], p[1], p[2] if len(p) > 2 and p[2] > 0 else None, look_z=p[3] if len(p) > 3 else None, lens=p[4] if len(p) > 4 else 40)
            else:
                shoot_model(ms, n, 'f34', 215); shoot_model(ms, n, 'r34', 35); shoot_model(ms, n, 'side', 90, elev_deg=5)
        return ms
    os.makedirs(PREVIEW + 'tiles/', exist_ok=True)
    if 'nolineup' not in argv:
        for ln, nm in LINEUPS.items():
            lineup(ms, [n for n in nm if n in ms], PREVIEW + ln + '.png', per_row=(5 if 'vehicles' in ln else 6 if 'street' in ln else 4))
    for gname, names in GROUPS.items():
        names = [n for n in names if n in ms]
        if not names: continue
        paths = []; labels = []
        for n in names:
            p = PREVIEW + 'tiles/%s.png' % n
            if 'notiles' not in argv: tile(ms, n, p)
            paths.append(p); labels.append('%s  %d tris' % (n, tri_count(ms[n])))
        compose(paths, labels, PREVIEW + 'sheet_%s.png' % gname, cols=min(4, len(paths)) if len(paths) < 5 else 4)
    return ms


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if argv and argv[0] == 'test':
        test(argv[1:])
