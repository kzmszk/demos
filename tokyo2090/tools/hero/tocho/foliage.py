"""Vegetation: the leaf atlas (alpha-clipped cards), tree / shrub models, hanging vine curtains, wall ivy, fig roots.

Leaf atlas 'leaf' (2048, RGBA; material M_leaf, MASK, double sided). Regions (px, rows from the bottom):
  CLUSTER[k]  4 leaf-cluster cards 512 x 512       x 0..1024,  y 1024..2048
  VINE[k]     4 hanging vine strips 256 x 1024     x 1024..2048, y 1024..2048
  FERN        512 x 512  x 0..512,   y 512..1024
  GRASS       512 x 512  x 512..1024, y 512..1024
  IVY         512 x 512  x 0..512,   y 0..512      (dense flat ivy, opaque-ish)
  LITTER      512 x 512  x 512..1024, y 0..512      (dead leaves / twigs)
  BARK        512 x 1024 x 1024..1536, y 0..1024   (opaque, tiles vertically: 2 m around x 4 m long)
  BARK2       512 x 1024 x 1536..2048, y 0..1024   (fig root bark, smooth grey)
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import common as C
import materials as M
import textures as T

N = 2048
CLUSTER = [(0, 1536, 512, 512), (512, 1536, 512, 512), (0, 1024, 512, 512), (512, 1024, 512, 512)]
VINE = [(1024 + 256 * k, 1024, 256, 1024) for k in range(4)]
FERN = (0, 512, 512, 512)
GRASS = (512, 512, 512, 512)
IVY = (0, 0, 512, 512)
LITTER = (512, 0, 512, 512)
BARK = (1024, 0, 512, 1024)
BARK2 = (1536, 0, 512, 1024)


def uvr(reg, u, v, inset=3):
    x, y, w, h = reg
    return ((x + inset + u * (w - 2 * inset)) / N, (y + inset + v * (h - 2 * inset)) / N)


# ============================================================================================== painting
class Canvas:
    def __init__(self):
        self.C = np.zeros((N, N, 3)); self.A = np.zeros((N, N)); self.O = np.ones((N, N)); self.R = np.full((N, N), 0.7)

    def leaf(self, cx, cy, ang, L, W, col, shade=1.0, rib=True, curl=0.0, region=None, kind='ovate'):
        """one leaf: tip at angle ang from (cx, cy) base, length L, width W px"""
        r = int(L + W + 2)
        x0, x1 = int(cx - r), int(cx + r + 1); y0, y1 = int(cy - r), int(cy + r + 1)
        if region:
            rx, ry, rw, rh = region
            x0 = max(x0, rx); y0 = max(y0, ry); x1 = min(x1, rx + rw); y1 = min(y1, ry + rh)
        if x1 <= x0 or y1 <= y0: return
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(float)
        dx, dy = xs - cx, ys - cy
        ca, sa = math.cos(ang), math.sin(ang)
        u = (dx * ca + dy * sa) / L; v = (-dx * sa + dy * ca) / W
        v = v - curl * u * u
        if kind == 'ovate':
            prof = np.sin(np.clip(u, 0, 1) * math.pi) ** 0.75 * (1 - 0.35 * np.clip(u, 0, 1))
        elif kind == 'lance':
            prof = np.sin(np.clip(u, 0, 1) * math.pi) ** 1.2
        else:  # heart (ivy / fig-like)
            prof = np.sin(np.clip(u, 0, 1) * math.pi) ** 0.6 * (1.1 - 0.5 * np.clip(u, 0, 1))
        m = (u >= 0) & (u <= 1) & (np.abs(v) <= prof * 0.5)
        if not m.any(): return
        # shading: lighter toward one side (light from above-ish), darker at base, midrib line
        s = shade * (0.82 + 0.25 * u - 0.18 * np.sign(v) * (np.abs(v) / (prof * 0.5 + 1e-6)) * 0.6)
        c = np.array(col)[None, None, :] * s[..., None]
        if rib:
            ribm = np.abs(v) < 0.045
            c = np.where(ribm[..., None], c * 0.78, c)
        sub = (slice(y0, y1), slice(x0, x1))
        self.C[sub] = np.where(m[..., None], c, self.C[sub])
        self.A[sub] = np.where(m, 1.0, self.A[sub])
        self.O[sub] = np.where(m, np.clip(shade, 0.3, 1.0), self.O[sub])


GREENS = [T.lin(c) for c in [(0.36, 0.50, 0.16), (0.28, 0.42, 0.12), (0.44, 0.54, 0.18), (0.24, 0.36, 0.11), (0.50, 0.58, 0.22)]]
YELLOW = T.lin((0.55, 0.50, 0.20)); BROWN = T.lin((0.45, 0.32, 0.16))


def paint_cluster(cv, reg, seed, leafL, leafW, n, kind='ovate', palette=GREENS, yellow=0.06):
    R = random.Random(seed)
    x, y, w, h = reg
    cx, cy = x + w / 2, y + h / 2
    # twigs first
    for k in range(9):
        a = R.uniform(0, 2 * math.pi); L = R.uniform(0.25, 0.45) * w
        for t in np.linspace(0, 1, 40):
            px, py = cx + math.cos(a) * L * t, cy + math.sin(a) * L * t
            rr = 2.2 * (1 - t) + 0.8
            cv.leaf(px - rr, py, 0, 2 * rr, 2 * rr, T.lin((0.22, 0.17, 0.12)), 0.7, rib=False, region=reg)
    order = []
    lobes = [(cx + R.uniform(-0.2, 0.2) * w, cy + R.uniform(-0.2, 0.2) * h, R.uniform(0.18, 0.28) * w) for _ in range(5)]
    for i in range(n):
        # leaves in a few overlapping lobes -> an irregular outline that fills the card
        lx, ly, lr = lobes[i % len(lobes)]
        rad_l = (R.random() ** 0.55) * lr
        a = R.uniform(0, 2 * math.pi)
        px, py = lx + math.cos(a) * rad_l, ly + math.sin(a) * rad_l
        rad = math.hypot(px - cx, py - cy)
        if rad > 0.46 * w: continue
        order.append((rad, px, py, math.atan2(py - cy, px - cx)))
    order.sort(key=lambda t: t[0])      # centre first, outer leaves on top
    for rad, px, py, a in order:
        col = palette[R.randrange(len(palette))]
        if R.random() < yellow: col = YELLOW if R.random() < 0.6 else BROWN
        col = np.array(col) * R.uniform(0.85, 1.15)
        ang = a + R.uniform(-0.9, 0.9)
        L = leafL * R.uniform(0.75, 1.25); W = leafW * R.uniform(0.8, 1.2)
        shade = 0.55 + 0.45 * (rad / (0.46 * w)) + R.uniform(-0.08, 0.08)
        cv.leaf(px, py, ang, L, W, col, shade, curl=R.uniform(-0.2, 0.2), region=reg, kind=kind)


def paint_vine(cv, reg, seed):
    R = random.Random(seed)
    x, y, w, h = reg
    for s in range(R.randint(5, 7)):
        x0 = x + R.uniform(0.15, 0.85) * w
        ph = R.uniform(0, 6.28); amp = R.uniform(6, 22); fq = R.uniform(1.5, 4)
        ys = np.arange(y + h - 2, y + 2, -2)
        endy = y + R.uniform(0.0, 0.35) * h
        for yy in ys:
            if yy < endy: break
            t = (y + h - yy) / h
            xx = x0 + math.sin(t * fq * 6.28 + ph) * amp
            cv.leaf(xx - 1.5, yy, 0, 3, 3, T.lin((0.22, 0.20, 0.12)), 0.7, rib=False, region=reg)
            if R.random() < 0.7:
                side = R.choice((-1, 1))
                col = np.array(GREENS[R.randrange(5)]) * R.uniform(0.8, 1.2)
                if R.random() < 0.05: col = YELLOW
                L = R.uniform(16, 30)
                cv.leaf(xx, yy, -math.pi / 2 + side * R.uniform(0.3, 1.3), L, L * 0.75, col, R.uniform(0.6, 1.0), region=reg, kind='heart')


def paint_fern(cv, reg, seed):
    R = random.Random(seed)
    x, y, w, h = reg
    cx, cy = x + w / 2, y + 30
    for f in range(9):
        a = math.pi / 2 + R.uniform(-1.1, 1.1)
        L = R.uniform(0.6, 0.9) * h
        for t in np.linspace(0.02, 1, 60):
            bend = 0.6 * t * t * (1 if a > math.pi / 2 else -1)
            aa = a + bend
            px = cx + math.cos(a) * L * t + (math.cos(aa) - math.cos(a)) * L * t * 0.5
            py = cy + math.sin(a) * L * t - 0.25 * L * t * t
            cv.leaf(px - 1.5, py, 0, 3, 3, T.lin((0.20, 0.28, 0.09)), 0.8, rib=False, region=reg)
            pl = 26 * (1 - t) ** 0.7 + 4
            col = np.array(GREENS[R.randrange(5)]) * (0.9 + 0.2 * t)
            for side in (-1, 1):
                cv.leaf(px, py, aa + side * 1.25, pl, pl * 0.32, col, 0.65 + 0.35 * t, rib=False, region=reg, kind='lance')


def paint_grass(cv, reg, seed):
    R = random.Random(seed)
    x, y, w, h = reg
    for b in range(170):
        bx = x + w / 2 + R.gauss(0, w * 0.13)
        L = R.uniform(0.35, 0.95) * h
        ang = math.pi / 2 + R.uniform(-0.45, 0.45)
        col = np.array(GREENS[R.randrange(5)]) * R.uniform(0.8, 1.2)
        if R.random() < 0.18: col = T.lin((0.52, 0.48, 0.28))
        cv.leaf(bx, y + 3, ang, L, R.uniform(7, 12), col, R.uniform(0.7, 1.0), rib=False, curl=R.uniform(-0.25, 0.25), region=reg, kind='lance')


def paint_ivy(cv, reg, seed):
    R = random.Random(seed)
    x, y, w, h = reg
    for i in range(3200):
        px = x + R.random() * w; py = y + R.random() * h
        d = math.hypot((px - x - w / 2) / (w / 2), (py - y - h / 2) / (h / 2))
        if d > 0.55 + 0.4 * math.sin(math.atan2(py - y - h / 2, px - x - w / 2) * 3 + seed) * 0.5 + R.random() * 0.35: continue
        col = np.array(GREENS[R.randrange(5)]) * R.uniform(0.7, 1.15)
        L = R.uniform(14, 24)
        cv.leaf(px, py, R.uniform(0, 6.28), L, L * 0.85, col, R.uniform(0.55, 1.0), region=reg, kind='heart')


def paint_litter(cv, reg, seed):
    R = random.Random(seed)
    x, y, w, h = reg
    for i in range(1400):
        px = x + R.random() * w; py = y + R.random() * h
        col = [YELLOW, BROWN, T.lin((0.35, 0.22, 0.10)), T.lin((0.42, 0.38, 0.22)), GREENS[3]][R.randrange(5)]
        L = R.uniform(10, 22)
        cv.leaf(px, py, R.uniform(0, 6.28), L, L * 0.5, np.array(col) * R.uniform(0.7, 1.1), R.uniform(0.6, 1.0), region=reg)


def paint_bark(cv, reg, seed, smooth=False):
    x, y, w, h = reg
    f = T.fbm(h, w, 4, 5, seed, aspect=4.0 if not smooth else 1.0)
    g = T.white(h, w, seed + 1)
    if smooth:
        base = T.mix(T.lin((0.46, 0.43, 0.37)), T.lin((0.30, 0.28, 0.24)), f)
        lent = (T.fbm(h, w, 40, 2, seed + 2, aspect=0.3) > 0.68)
        base = base * np.where(lent[..., None], 0.8, 1.0)
    else:
        fis = (T.fbm(h, w, 3, 3, seed + 3, aspect=8.0) > 0.55)
        base = T.mix(T.lin((0.33, 0.28, 0.22)), T.lin((0.18, 0.15, 0.12)), f)
        base = base * np.where(fis[..., None], 0.6, 1.0)
    moss = np.clip((T.fbm(h, w, 3, 4, seed + 4) - 0.55) * 3, 0, 1)
    base = T.mix(base, T.MOSS_D, moss * 0.6) * (0.9 + 0.2 * g[..., None])
    cv.C[y:y + h, x:x + w] = base; cv.A[y:y + h, x:x + w] = 1; cv.R[y:y + h, x:x + w] = 0.85
    cv.O[y:y + h, x:x + w] = 1


def build_textures(log=print):
    cv = Canvas()
    paint_cluster(cv, CLUSTER[0], 1, 30, 15, 1500, 'ovate')                         # zelkova-ish small leaves
    paint_cluster(cv, CLUSTER[1], 2, 58, 30, 520, 'ovate', yellow=0.04)             # fig: big glossy leaves
    paint_cluster(cv, CLUSTER[2], 3, 36, 12, 1300, 'lance', palette=GREENS[:2] + GREENS[3:4])
    paint_cluster(cv, CLUSTER[3], 4, 26, 18, 1400, 'heart', palette=GREENS[2:], yellow=0.1)
    for k, r in enumerate(VINE): paint_vine(cv, r, 10 + k)
    paint_fern(cv, FERN, 20); paint_grass(cv, GRASS, 21); paint_ivy(cv, IVY, 22); paint_litter(cv, LITTER, 23)
    paint_bark(cv, BARK, 24); paint_bark(cv, BARK2, 25, smooth=True)
    # bleed colour under transparent pixels (mip edges stay green, not black)
    Cb = cv.C.copy()
    for r in (2, 6, 16):
        bl = T.blur(cv.C * cv.A[..., None], r); ab = T.blur(cv.A, r)
        fill = bl / np.maximum(ab[..., None], 1e-4)
        Cb = np.where((cv.A < 0.5)[..., None] & (ab > 0.01)[..., None] & (Cb.sum(-1, keepdims=True) == 0), fill, Cb)
    Cb = np.where((Cb.sum(-1, keepdims=True) == 0), T.lin((0.22, 0.30, 0.12)), Cb)
    T.save_png('leaf_col', T.srgb(Cb), cv.A)
    rough = np.where(np.arange(N)[None, :] < 1024, cv.R, 0.85) * np.ones((N, N))
    rough[1536:2048, 512:1024] = 0.45       # fig leaves glossy
    T.save_png('leaf_orm', np.dstack([cv.O, rough, np.zeros((N, N))]))
    for n in ('leaf_col', 'leaf_orm'):
        im = bpy.data.images.get(n)
        if im: im.reload()
    log('leaf atlas done')


# ============================================================================================== geometry helpers
def tube(mb, pts, radii, reg=BARK, sides=6, tile=(2.0, 4.0), mat=0, cap=True, uoff=0.0):
    """tapered tube along pts; UVs into a vertically tiling bark region, split every tile length"""
    n = len(pts)
    if n < 2: return
    frames = []
    prev_s = None
    for i in range(n):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        if prev_s is None:
            up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
            s = d.cross(up).normalized()
        else:
            s = (prev_s - d * prev_s.dot(d)).normalized()
        t = d.cross(s).normalized()
        frames.append((s, t)); prev_s = s
    rings = []
    for i in range(n):
        s, t = frames[i]
        rings.append([pts[i] + (s * math.cos(a) + t * math.sin(a)) * radii[i] for a in
                      [2 * math.pi * k / sides for k in range(sides)]])
    acc = [0.0]
    for i in range(1, n): acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    circ = 2 * math.pi * max(radii)
    us = 1
    for i in range(n - 1):
        v0 = acc[i] / tile[1]; v1 = acc[i + 1] / tile[1]
        base = math.floor(v0)
        if v1 - base > 1.0: v1 = base + 1.0     # clamp (segments shorter than a tile anyway)
        for k in range(sides):
            k2 = (k + 1) % sides
            u0 = k / sides * us; u1 = (k + 1) / sides * us
            ub = math.floor(u0 + 1e-6); u0 -= ub; u1 -= ub
            uv = [uvr(reg, u0, v0 - base), uvr(reg, u1, v0 - base), uvr(reg, u1, v1 - base), uvr(reg, u0, v1 - base)]
            mb.poly([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], mat, 0, uv)
    if cap:
        mb.poly(rings[-1], mat, 0, [uvr(reg, 0.5 + 0.4 * math.cos(2 * math.pi * k / sides), 0.5 + 0.4 * math.sin(2 * math.pi * k / sides)) for k in range(sides)])


def card(mb, c, xa, ya, reg, w, h, mat=0, anchor='centre'):
    """a quad centred at c (or hanging from its top) spanned by unit axes xa, ya"""
    xa = Vector(xa).normalized() * w / 2; ya = Vector(ya).normalized()
    if anchor == 'top':
        p = [c - xa - ya * h, c + xa - ya * h, c + xa, c - xa]
    elif anchor == 'bottom':
        p = [c - xa, c + xa, c + xa + ya * h, c - xa + ya * h]
    else:
        yh = ya * h / 2
        p = [c - xa - yh, c + xa - yh, c + xa + yh, c - xa + yh]
    uv = [uvr(reg, 0, 0), uvr(reg, 1, 0), uvr(reg, 1, 1), uvr(reg, 0, 1)]
    return mb.poly(p, mat, 0, uv)


# ============================================================================================== trees
SPECIES = {
    'zelkova': dict(h=16.0, cr=7.5, tr=0.45, nc=100, cs=(3.2, 4.6), reg=[0, 3], nb=6, vase=True),
    'street': dict(h=11.0, cr=5.0, tr=0.30, nc=62, cs=(2.6, 3.6), reg=[0, 2], nb=5, vase=True),
    'young': dict(h=6.5, cr=2.6, tr=0.13, nc=24, cs=(1.6, 2.4), reg=[3, 0], nb=3, vase=False),
    'fig': dict(h=10.0, cr=7.0, tr=0.6, nc=110, cs=(3.0, 4.2), reg=[1, 3], nb=7, vase=False, fig=True),
    'roof': dict(h=5.5, cr=3.0, tr=0.16, nc=30, cs=(1.8, 2.6), reg=[3, 1], nb=4, vase=False),
    'shrub': dict(h=1.8, cr=1.3, tr=0.05, nc=10, cs=(1.3, 1.8), reg=[3, 0], nb=0, vase=False),
}


def tree(name, seed=0, lo=False):
    """returns an MB with trunk/branches (bark) and leaf cards, pivot at the trunk base, plus per-vertex
    custom normals (spherical around the crown) for the cards"""
    sp = SPECIES[name]
    R = random.Random(hash((name, seed)) & 0xffff)
    mb = C.MB()
    H, cr, tr = sp['h'], sp['cr'], sp['tr']
    crown_c = Vector((0, 0, H * 0.66 if name != 'shrub' else 0.9))
    crh = (H - crown_c.z) * 0.95 if name != 'shrub' else 0.8
    tips = []
    # trunk
    lean = Vector((R.uniform(-0.08, 0.08), R.uniform(-0.08, 0.08), 1)).normalized()
    tl = H * (0.42 if sp.get('vase') else 0.55)
    if name == 'shrub': tl = 0.3
    trunk = [Vector((0, 0, -0.3)) + lean * tl * t + Vector((math.sin(t * 3 + seed) * 0.15, math.cos(t * 2.3) * 0.15, 0)) * t for t in np.linspace(0, 1, 6)]
    rad = [tr * (1.25 - 0.45 * t) for t in np.linspace(0, 1, 6)]
    rad[0] = tr * 1.6
    if tl > 0.5: tube(mb, trunk if not lo else trunk[::2], rad if not lo else rad[::2], sides=(6 if tr > 0.2 else 4) if not lo else 4)
    top = trunk[-1]
    # buttress roots for big trees
    if tr > 0.3 and not lo:
        for k in range(4 if not sp.get('fig') else 7):
            a = 2 * math.pi * k / 5 + R.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0))
            pts = [Vector((0, 0, 1.2)) + d * tr * 0.5, d * (tr + 0.6) + Vector((0, 0, 0.35)), d * (tr + 1.6 + R.uniform(0, 1.2)) + Vector((0, 0, -0.1))]
            tube(mb, pts, [tr * 0.45, tr * 0.3, tr * 0.12], reg=BARK2 if sp.get('fig') else BARK, sides=4)
    # main branches
    for b in range(sp['nb']):
        a = 2 * math.pi * b / max(1, sp['nb']) + R.uniform(-0.4, 0.4)
        el = R.uniform(0.75, 1.15) if sp.get('vase') else R.uniform(0.3, 0.8)
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)))
        L = (H - tl) * R.uniform(0.75, 1.0) if sp.get('vase') else cr * R.uniform(0.8, 1.1)
        p0 = top - lean * R.uniform(0, tl * 0.25)
        pts = [p0]
        for t in np.linspace(0.33, 1, 3):
            q = p0 + d * L * t + Vector((0, 0, -0.15 * L * t * t if not sp.get('vase') else 0.0))
            q += Vector((R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3), R.uniform(-0.2, 0.2)))
            pts.append(q)
        if lo: pts = pts[:3]
        tube(mb, pts, [tr * 0.6, tr * 0.38, tr * 0.2, tr * 0.08][:len(pts)], sides=5 if not lo else 3, cap=False)
        tips += pts[1:]
        # sub-branches
        for s in range(0 if lo else 1):
            q = pts[2 + s]; a2 = a + R.uniform(-1.0, 1.0)
            d2 = Vector((math.cos(a2), math.sin(a2), R.uniform(0.1, 0.8))).normalized()
            q2 = q + d2 * L * 0.4
            tube(mb, [q, q.lerp(q2, 0.5) + Vector((0, 0, 0.2)), q2], [tr * 0.18, tr * 0.11, tr * 0.05], sides=3, cap=False)
            tips.append(q2)
    if sp.get('fig') and not lo:
        # aerial roots hanging from the branches
        for k in range(10):
            q = R.choice(tips)
            if q.z < 2.5: continue
            pts = [q, Vector((q.x * 0.9, q.y * 0.9, q.z * 0.5)), Vector((q.x * 0.85 + R.uniform(-0.3, 0.3), q.y * 0.85, -0.2))]
            tube(mb, pts, [0.05, 0.06, 0.09], reg=BARK2, sides=4, cap=False)
    if not tips: tips = [top]
    leaf_start = len(mb.F)
    # leaf clusters: crossed cards around the tips and filling the crown ellipsoid
    centres = []
    for i in range(sp['nc']):
        if i < len(tips) * 2:
            c = tips[i % len(tips)] + Vector((R.uniform(-0.8, 0.8), R.uniform(-0.8, 0.8), R.uniform(-0.3, 0.6)))
        else:
            u = Vector((R.gauss(0, 1), R.gauss(0, 1), R.gauss(0, 1))).normalized() * (R.random() ** 0.3)
            # lumpy crown: radius modulated by direction
            lump = 1 + 0.25 * math.sin(math.atan2(u.y, u.x) * 3 + seed) * math.cos(u.z * 4)
            c = crown_c + Vector((u.x * cr * lump, u.y * cr * lump, u.z * crh))
        if name == 'shrub': c = Vector((R.uniform(-0.6, 0.6), R.uniform(-0.6, 0.6), R.uniform(0.4, 1.3)))
        centres.append(c)
    for c in centres:
        reg = CLUSTER[R.choice(sp['reg'])]
        s = R.uniform(*sp['cs'])
        a = R.uniform(0, math.pi)
        x1 = Vector((math.cos(a), math.sin(a), 0)); y1 = Vector((0, 0, 1)).lerp(Vector((-math.sin(a), math.cos(a), 0)), R.uniform(0.0, 0.5))
        card(mb, c, x1, y1, reg, s, s)
        x2 = Vector((-math.sin(a), math.cos(a), 0)); y2 = Vector((0, 0, 1)).lerp(x1, R.uniform(0.0, 0.5))
        card(mb, c, x2, y2, reg, s, s)
        # a near-horizontal card on top for the view from the air
        x3 = Vector((math.cos(a + 0.7), math.sin(a + 0.7), R.uniform(-0.2, 0.2)))
        card(mb, c + Vector((0, 0, 0.2)), x3, x3.cross(Vector((0, 0, 1))).cross(x3) * -1 if False else Vector((-x3.y, x3.x, 0.25)), reg, s * 1.05, s * 1.05)
    mb.leaf_from = leaf_start
    mb.crown_c = crown_c
    return mb


def mb_object(mb, name, mat, col, crown_normals=True):
    ob = mb.build(name, [mat], col)
    me = ob.data
    if crown_normals and hasattr(mb, 'leaf_from'):
        # bend card normals outward from the crown centre (soft volumetric shading), bark keeps its own
        cc = mb.crown_c
        me.update()
        normals = []
        for p in me.polygons:
            for li in p.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                if p.index >= mb.leaf_from:
                    n = (v - cc); n.z = n.z * 0.7 + 0.35 * n.length
                    normals.append(n.normalized())
                else:
                    normals.append(p.normal.copy())
        me.normals_split_custom_set(normals)
    return ob


def tree_models(col, log=print):
    """one mesh per species: objects 'foliage_<species>' (pivot at the base)"""
    mat = M.make('leaf')
    out = {}
    for name in SPECIES:
        for v in range(2 if name in ('zelkova', 'street', 'young', 'roof') else 1):
            for lo in (False, True):
                sp = SPECIES[name]
                keep = sp['nc']
                if lo: sp['nc'] = max(5, keep // 5); sp['cs'] = (sp['cs'][0] * 1.6, sp['cs'][1] * 1.6)
                mb = tree(name, v, lo)
                if lo: sp['nc'] = keep; sp['cs'] = (sp['cs'][0] / 1.6, sp['cs'][1] / 1.6)
                nm = 'foliage_%s%d' % (name, v) + ('_lo' if lo else '')
                # one material per instanced mesh: the game does not draw a material shared between meshes
                mt = mat.copy(); mt.name = 'M_leaf_' + nm.replace('foliage_', '')
                ob = mb_object(mb, nm, mt, col)
                ob.data.name = nm
                out[nm] = ob
                log('tree', nm, len(ob.data.polygons), 'faces')
    # ground plants
    for nm, reg, s, n in (('foliage_fern', FERN, 1.3, 5), ('foliage_grass', GRASS, 1.4, 4)):
        mb = C.MB(); R = random.Random(len(nm))
        for k in range(n):
            a = math.pi * k / n + R.uniform(-0.2, 0.2)
            x1 = Vector((math.cos(a), math.sin(a), 0))
            c = Vector((R.uniform(-0.2, 0.2), R.uniform(-0.2, 0.2), -0.05))
            card(mb, c, x1, Vector((R.uniform(-0.3, 0.3), R.uniform(-0.3, 0.3), 1)), reg, s, s * 0.95, anchor='bottom')
        mt = mat.copy(); mt.name = 'M_leaf_' + nm.replace('foliage_', '')
        ob = mb.build(nm, [mt], col); ob.data.name = nm; out[nm] = ob
    return out


# ============================================================================================== walls
def hang_vines(mb, a, b, out, rng, length=(3, 12), spacing=1.1, z_min=None):
    """curtains hanging from the edge a->b (a ledge or a roof edge), 0.15 m in front of the wall (normal 'out')"""
    a = Vector(a); b = Vector(b); out = Vector(out).normalized()
    L = (b - a).length
    n = max(1, int(L / spacing))
    tang = (b - a).normalized()
    for i in range(n):
        if rng.random() < 0.25: continue
        t = (i + rng.random()) / n
        p = a.lerp(b, t) + out * (0.12 + rng.random() * 0.3)
        ln = rng.uniform(*length)
        if z_min is not None: ln = min(ln, p.z - z_min - 0.3)
        if ln < 0.8: continue
        w = rng.uniform(0.9, 1.6)
        reg = VINE[rng.randrange(4)]
        # the strip texture is 256 x 1024 = 1 x 4 aspect: one tile per 4 widths of length, stack tiles
        seg = w * 4
        z = p.z; k = 0
        while ln > 0.3 and k < 6:
            h = min(seg, ln)
            x, y, ww, hh = reg
            # map from the top of the strip downward (partial last tile)
            frac = h / seg
            c0 = p.copy(); c0.z = z
            xa = tang * w / 2
            q = [c0 - xa - Vector((0, 0, h)), c0 + xa - Vector((0, 0, h)), c0 + xa, c0 - xa]
            # slight outward bulge at the bottom
            q[0] += out * 0.15 * k; q[1] += out * 0.15 * k
            uv = [uvr(reg, 0, 1 - frac), uvr(reg, 1, 1 - frac), uvr(reg, 1, 1), uvr(reg, 0, 1)]
            mb.poly(q, 0, 0, uv)
            z -= h; ln -= h; k += 1


def ivy_patch(mb, p0, tang, out, w, h, rng):
    """a patch of flat ivy on a wall: overlapping square cards slightly off the wall"""
    tang = Vector(tang).normalized(); out = Vector(out).normalized(); up = Vector((0, 0, 1))
    nx = max(1, int(w / 2.2)); ny = max(1, int(h / 2.2))
    for i in range(nx):
        for j in range(ny):
            if rng.random() < 0.15: continue
            c = Vector(p0) + tang * (i + 0.5 + rng.uniform(-0.3, 0.3)) * w / nx + up * (j + 0.5 + rng.uniform(-0.3, 0.3)) * h / ny + out * (0.06 + 0.05 * rng.random())
            s = rng.uniform(2.2, 3.2)
            ang = rng.uniform(-0.5, 0.5)
            xa = tang * math.cos(ang) + up * math.sin(ang); ya = -tang * math.sin(ang) + up * math.cos(ang)
            card(mb, c, xa, ya, IVY if rng.random() < 0.7 else CLUSTER[3], s, s)


def root_curtain(mb, top, out, rng, n=9, length=(8, 25), spread=3.0, z_min=None):
    """strangler-fig roots pouring down a wall from a ledge at 'top': braided tubes hugging the wall"""
    top = Vector(top); out = Vector(out).normalized()
    tang = Vector((0, 0, 1)).cross(out).normalized()
    for k in range(n):
        x = rng.uniform(-spread, spread)
        L = rng.uniform(*length)
        if z_min is not None: L = min(L, top.z - z_min)
        if L < 1: continue
        pts = []; rad = []
        steps = max(3, int(L / 2.5))
        r0 = rng.uniform(0.14, 0.38)
        ph = rng.uniform(0, 6.28); amp = rng.uniform(0.4, 1.4)
        steps = max(4, int(L / 1.5))
        for i in range(steps + 1):
            t = i / steps
            p = top + tang * (x * (0.4 + 0.6 * t) + math.sin(t * 4.5 + ph) * amp * t) + out * (r0 * 0.8 + 0.04 * math.sin(t * 9 + k)) - Vector((0, 0, L * t))
            if i == 0: p += out * (r0 + 0.25) + Vector((0, 0, 0.3))
            pts.append(p); rad.append(r0 * (1 - 0.6 * t) + 0.03)
        tube(mb, pts, rad, reg=BARK2, sides=4, tile=(1.0, 3.0), cap=False)
        # feeder roots branching sideways
        if rng.random() < 0.6 and len(pts) > 3:
            i = rng.randrange(1, len(pts) - 2)
            q = pts[i]; d = tang * rng.choice((-1, 1)) * rng.uniform(1, 3)
            tube(mb, [q, q + d * 0.5 - Vector((0, 0, 0.8)), q + d - Vector((0, 0, 2.5))], [rad[i] * 0.5, rad[i] * 0.35, 0.02], reg=BARK2, sides=3, tile=(1.0, 3.0), cap=False)
