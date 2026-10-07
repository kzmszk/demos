"""嵐山 street fronts (長辻通, the riverside road, 中之島's tea houses): machiya._front's variant from the 東山 site
(sites/higashiyama_front.py, copied here so that site's later edits don't change ours) with 嵐山's additions: のぼり
banners on poles, more noren and red lanterns, tea-house fronts open to the plaza.  Open shop bays with goods
shelves and display tables, glazed shop doors, awnings, red-felt benches and parasols, standing and hanging signs,
pots.  Used through machiya.build by swapping machiya._front (see arashiyama_street.patched_front); fronts without
style['hy'] fall through to the original."""
import math
import numpy as np
from jk import prim
import sites.machiya as M

bars = M.bars; front_rect = M.front_rect; side_rect = M.side_rect; hbox = M.hbox; quad = M.quad; quads = M.quads
lattice = M.lattice; wall_holes = M.wall_holes

WHITE = (0.7, 0.68, 0.62)
def ptint(rgb, base=WHITE):
    return M.paint_tint(rgb, base=base)

GOODS = [(196, 60, 48), (226, 196, 120), (70, 96, 150), (232, 228, 214), (120, 150, 90), (180, 120, 70), (200, 110, 140), (90, 70, 60), (240, 200, 60), (60, 120, 120)]
AWNING = [(206, 188, 150), (226, 220, 200), (120, 84, 54), (44, 52, 84), (64, 80, 60), (150, 40, 34)]
FELT = (176, 22, 26)

def add_flat(B, P, I, mat, c0, tag='detail', **kw):
    """B.add with per-vertex tints and flat normals.  (jk.core.Builder.add re-indexes the vertices for flat shading but
    not a per-vertex c0 array, which then no longer matches; so expand the corners here and pass the normals.)"""
    P = np.asarray(P, float); I = np.asarray(I, np.int64).reshape(-1, 3); C = np.asarray(c0, np.uint8)
    idx = I.ravel()
    P2 = P[idx]; C2 = C[idx]
    fn = np.cross(P2[1::3] - P2[0::3], P2[2::3] - P2[0::3])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    N2 = np.repeat(fn, 3, axis=0)
    B.add(P2, np.arange(len(P2)).reshape(-1, 3), mat, N=N2, c0=C2, tag=tag, **kw)

# ------------------------------------------------------------------ small batched goods
def goods_row(B, u0, u1, v0, v1, z, rng, h=(0.08, 0.22), w=(0.1, 0.3), gap=0.03, tag='detail'):
    """a row of small boxes (packages, boxes of sweets, folded cloth) on a shelf: top + front + sides (no back, no bottom),
    each tinted by a goods colour (white_paint program: colour = tint)"""
    u = u0 + 0.02
    P = []; I = []; C = []
    while u < u1 - 0.06:
        ww = min(rng.uniform(*w), u1 - u - 0.02)
        if ww < 0.05: break
        hh = rng.uniform(*h); dd = min(v1 - v0, rng.uniform(0.12, 0.3))
        va = v0 + rng.uniform(0, max(0.0, (v1 - v0) - dd))
        a, b = u, u + ww
        k = len(P)
        P += [(a, va, z), (b, va, z), (b, va, z + hh), (a, va, z + hh), (a, va + dd, z + hh), (b, va + dd, z + hh), (a, va + dd, z), (b, va + dd, z)]
        I += [[k, k + 1, k + 2], [k, k + 2, k + 3],                 # front (facing -v)
              [k + 3, k + 2, k + 5], [k + 3, k + 5, k + 4],         # top
              [k + 6, k, k + 3], [k + 6, k + 3, k + 4],             # left
              [k + 1, k + 7, k + 5], [k + 1, k + 5, k + 2]]         # right
        col = GOODS[int(rng.integers(len(GOODS)))]
        C += [ptint(col)] * 8
        u = b + rng.uniform(0.0, gap * 3)
    if P:
        add_flat(B, P, I, 'white_paint', C, tag=tag)

def bowls(B, u0, u1, v, z, rng, r=0.07, tag='detail'):
    """a row of small bowls / cups (清水焼): short 6-sided cylinders, tinted"""
    n = max(1, int((u1 - u0) / (2 * r + 0.04)))
    us = np.linspace(u0 + r + 0.02, u1 - r - 0.02, n)
    P = []; I = []; C = []
    seg = 6
    for u in us:
        rr = r * rng.uniform(0.8, 1.15); hh = rr * rng.uniform(0.7, 1.3)
        k = len(P)
        for j in range(seg):
            t = 2 * math.pi * j / seg
            P.append((u + rr * 0.75 * math.cos(t), v + rr * 0.75 * math.sin(t), z)); P.append((u + rr * math.cos(t), v + rr * math.sin(t), z + hh))
        for j in range(seg):
            a0 = k + 2 * j; a1 = k + 2 * ((j + 1) % seg)
            I += [[a0, a1, a1 + 1], [a0, a1 + 1, a0 + 1]]
        # inside (top cap, dark-ish: same tint)
        c = k + 2 * seg; P.append((u, v, z + hh * 0.4))
        for j in range(seg):
            I.append([c, k + 2 * j + 1, k + 2 * ((j + 1) % seg) + 1])
        col = (232, 228, 214) if rng.random() < 0.4 else GOODS[int(rng.integers(len(GOODS)))]
        C += [ptint(col)] * (2 * seg + 1)
    add_flat(B, P, I, 'white_paint', C, tag=tag)

def shelf_wall(B, a, b, dd, z_top, rng, seed, light=True):
    """the back of an open shop bay at depth dd: dark board wall, 3 shelves with goods, a ceiling light"""
    front_rect(B, a, b, 0.0, z_top, dd, 'wall_board', facing=-1, c0=(70, 56, 42, 0))
    for zz in (0.55, 1.05, 1.55):
        if zz > z_top - 0.35: break
        hbox(B, a + 0.05, b - 0.05, dd - 0.38, dd, zz - 0.03, zz, 'wood_natural', tag='detail', faces='zZy')
        goods_row(B, a + 0.08, b - 0.08, dd - 0.36, dd - 0.02, zz, rng)

def display_table(B, a, b, v0, v1, z, rng, kind='boxes'):
    """見世台: a low wooden display table with goods (boxes or bowls)"""
    hbox(B, a, b, v0, v1, z - 0.05, z, 'wood_natural', tag='main', faces='yZxX')
    for (u, v) in ((a + 0.05, v0 + 0.05), (b - 0.05, v0 + 0.05)):
        bars(B, [(u, v, 0.0)], [(u, v, z - 0.05)], (1, 0, 0), 0.05, 0.05, 'wood_natural', tag='detail')
    front_rect(B, a, b, 0.05, z - 0.08, v0 + 0.02, 'wall_board', c0=(80, 64, 48, 0))
    if kind == 'bowls':
        for vv in np.arange(v0 + 0.12, v1 - 0.08, 0.2):
            bowls(B, a + 0.03, b - 0.03, vv, z, rng)
    else:
        goods_row(B, a + 0.03, b - 0.03, v0 + 0.04, v1 - 0.04, z, rng, h=(0.05, 0.16), w=(0.12, 0.35))

def open_bay(B, a, b, z_top, rng, seed, hy, info):
    """an open shop bay: stone floor, side cheeks, ceiling, back shelves, a display table at the front"""
    dd = hy.get('depth', 2.4)
    prim.polygon(B, [(a, 0.0), (b, 0.0), (b, dd), (a, dd)], 0.03, 'stone', tag='main')
    quad(B, (a, dd, z_top), (b, dd, z_top), (b, 0.0, z_top), (a, 0.0, z_top), 'eave_wood', tag='main', c1=(0, 2, 0, 0),
         uv=np.array([(a, dd), (b, dd), (b, 0), (a, 0)]))
    side_rect(B, 0.0, dd, 0.0, z_top, a, 'wall_plaster', facing=1, c0=(214, 200, 170, 0))
    side_rect(B, 0.0, dd, 0.0, z_top, b, 'wall_plaster', facing=-1, c0=(214, 200, 170, 0))
    shelf_wall(B, a, b, dd, z_top, rng, seed)
    if b - a > 0.9 and rng.random() < 0.8:
        display_table(B, a + 0.1, b - 0.1, 0.12, 0.85, 0.72, rng, kind=hy.get('goods', 'boxes'))
    # a ceiling light (emissive panel) — the shops glow in the evening
    cu = (a + b) / 2
    hbox(B, cu - 0.22, cu + 0.22, dd * 0.4 - 0.22, dd * 0.4 + 0.22, z_top - 0.05, z_top - 0.01, 'lamp', tag='detail', faces='z')
    info.setdefault('shop_lights', []).append((cu, dd * 0.4, z_top - 0.3))

def glass_bay(B, a, b, z_top, rng, hy):
    """glazed sliding doors (ガラス戸) in wooden frames with a paper-lit transom (欄間 障子)"""
    front_rect(B, a, b, 0.05, 0.3, -0.01, 'wood_dark')
    zg = min(2.05, z_top - 0.3)
    front_rect(B, a, b, 0.3, zg, 0.06, 'glass', tag='main')
    n = max(2, int(round((b - a) / 0.9)))
    mu = np.linspace(a, b, n + 1)
    bars(B, np.c_[mu, np.full(n + 1, 0.04), np.full(n + 1, 0.3)], np.c_[mu, np.full(n + 1, 0.04), np.full(n + 1, zg)], (1, 0, 0), 0.06, 0.05, 'wood_dark', tag='detail')
    bars(B, [(a, 0.04, zg), (a, 0.04, 0.3), (a, 0.03, 0.95)], [(b, 0.04, zg), (b, 0.04, 0.3), (b, 0.03, 0.95)], (0, 0, 1), (0.07, 0.07, 0.04), 0.05, 'wood_dark', tag='detail')
    # transom: lit shoji with a fine lattice
    if z_top - zg > 0.15:
        front_rect(B, a, b, zg, z_top, 0.05, 'lantern_paper', tag='main')
        lattice(B, a, b, zg + 0.02, z_top - 0.02, 0.0, pitch=0.12, sw=0.02, sd=0.02, back=None, rails=False, mid=False)
    # goods behind the glass are invisible (opaque glass): a display shelf in front of the glass instead
    if rng.random() < 0.5 and b - a > 1.0:
        hbox(B, a + 0.1, b - 0.1, -0.42, -0.05, 0.62, 0.66, 'wood_natural', tag='detail', faces='yZxX')
        bars(B, [(a + 0.15, -0.4, 0.0), (b - 0.15, -0.4, 0.0)], [(a + 0.15, -0.4, 0.62), (b - 0.15, -0.4, 0.62)], (1, 0, 0), 0.04, 0.04, 'wood_natural', tag='detail')
        if hy.get('goods') == 'bowls': bowls(B, a + 0.12, b - 0.12, -0.24, 0.66, rng)
        else: goods_row(B, a + 0.12, b - 0.12, -0.4, -0.08, 0.66, rng, h=(0.05, 0.14))
        return True
    return False

# ------------------------------------------------------------------ street accessories
def awning(B, u0, u1, z_top, depth, out, drop, tint):
    """日除け: a canvas awning from under the 庇 edge, sloping out, with a valance"""
    if u1 - u0 < 0.6: return
    vt = -depth + 0.05; vb = vt - out
    zt = z_top; zb = z_top - drop
    quad(B, (u0, vb, zb), (u1, vb, zb), (u1, vt, zt), (u0, vt, zt), 'cloth', tag='main', c0=(*tint, 0), uv=np.array([(u0, 0), (u1, 0), (u1, out), (u0, out)]))
    quad(B, (u0, vt, zt), (u1, vt, zt), (u1, vb, zb), (u0, vb, zb), 'cloth', tag='main', c0=(*tint, 0), uv=np.array([(u0, 0), (u1, 0), (u1, out), (u0, out)]))
    # valance with a scalloped hem: a strip of small triangles
    vh = 0.22
    front_rect(B, u0, u1, zb - vh, zb, vb, 'cloth', tag='detail', c0=(*tint, 0))
    front_rect(B, u0, u1, zb - vh, zb, vb + 0.005, 'cloth', tag='detail', facing=1, c0=(*tint, 0))
    n = max(2, int((u1 - u0) / 0.14))
    us = np.linspace(u0, u1, n + 1)
    P = []; I = []
    for i in range(n):
        k = len(P)
        P += [(us[i], vb, zb - vh), (us[i + 1], vb, zb - vh), ((us[i] + us[i + 1]) / 2, vb, zb - vh - 0.045)]
        I += [[k, k + 2, k + 1], [k, k + 1, k + 2]]
    B.add(np.array(P), np.array(I), 'cloth', tag='detail', c0=(*tint, 0))
    # side arms
    bars(B, [(u0 + 0.03, vt, zt), (u1 - 0.03, vt, zt)], [(u0 + 0.03, vb, zb), (u1 - 0.03, vb, zb)], (0, 0, 1), 0.025, 0.025, 'metal_dark', tag='detail')

def bench(B, u0, u1, v, rng, felt=FELT, parasol=False):
    """床几 with 緋毛氈: a low wooden bench, the red felt draped over the top and the front"""
    zt = 0.44; d = 0.6
    hbox(B, u0, u1, v - d / 2, v + d / 2, zt - 0.05, zt, 'wood_natural', tag='main', faces='zZyYxX')
    for (u, vv) in ((u0 + 0.06, v - d / 2 + 0.06), (u1 - 0.06, v - d / 2 + 0.06), (u0 + 0.06, v + d / 2 - 0.06), (u1 - 0.06, v + d / 2 - 0.06)):
        bars(B, [(u, vv, 0.0)], [(u, vv, zt - 0.05)], (1, 0, 0), 0.06, 0.06, 'wood_natural', tag='detail')
    # felt: top + front fall (cloth = its tint)
    quad(B, (u0 - 0.02, v - d / 2 - 0.02, zt + 0.006), (u1 + 0.02, v - d / 2 - 0.02, zt + 0.006), (u1 + 0.02, v + d / 2 + 0.02, zt + 0.006), (u0 - 0.02, v + d / 2 + 0.02, zt + 0.006),
         'cloth', tag='main', c0=(*felt, 0))
    front_rect(B, u0 - 0.02, u1 + 0.02, zt - 0.22, zt + 0.006, v - d / 2 - 0.021, 'cloth', tag='main', c0=(*felt, 0))
    prim.polygon(B, [(u0, v - d / 2), (u1, v - d / 2), (u1, v + d / 2), (u0, v + d / 2)], 0.05, 'stone', tag='block')
    if parasol:
        pu = u1 + 0.25; pv = v - 0.55
        bars(B, [(pu, pv, 0.0)], [(pu, pv, 2.45)], (1, 0, 0), 0.04, 0.04, 'wood_natural', tag='detail')
        prim.lathe(B, (pu, pv, 2.0), [(1.0, 0.0), (0.75, 0.15), (0.38, 0.3), (0.04, 0.4), (0.0, 0.42)], 12, 'vermilion', tag='main', smooth=True, c0=M.paint_tint(FELT))
        prim.lathe(B, (pu, pv, 2.0), [(0.0, 0.39), (0.04, 0.37), (0.38, 0.27), (0.75, 0.12), (1.0, -0.03)], 12, 'vermilion', tag='detail', smooth=True, c0=M.paint_tint((120, 16, 18)))

def stand_sign(B, u, v, rng, seed):
    """置き看板: a small standing board with brush strokes"""
    w = rng.uniform(0.32, 0.45); h = rng.uniform(0.9, 1.25)
    hbox(B, u - w / 2 - 0.03, u + w / 2 + 0.03, v - 0.02, v + 0.04, 0.05, h, 'wood_dark', tag='detail', faces='yYxXZ')
    quad(B, (u - w / 2, v - 0.025, 0.25), (u + w / 2, v - 0.025, 0.25), (u + w / 2, v - 0.025, h - 0.06), (u - w / 2, v - 0.025, h - 0.06), 'white_paint', tag='detail',
         uv=np.array([(0, 0), (w * 2.2, 0), (w * 2.2, h * 1.2), (0, h * 1.2)]), c1=(0, 7, (seed * 13) % 251, 0))
    hbox(B, u - w / 2, u + w / 2, v - 0.15, v + 0.2, 0.0, 0.05, 'wood_dark', tag='detail', faces='yZ')

def pot(B, u, v, rng, big=False):
    """a potted plant: a glazed pot and a clipped shrub"""
    r = rng.uniform(0.16, 0.24) * (1.5 if big else 1.0); h = r * 1.3
    prim.cyl(B, (u, v, 0.0), (u, v, h), r * 0.8, r, 8, 'white_paint', caps=(False, True), tag='detail', c0=ptint((70, 60, 54) if rng.random() < 0.6 else (60, 80, 100)))
    sz = r * rng.uniform(1.4, 2.2)
    blob(B, (u, v, h + sz * 0.4), sz, rng)

_ICO = None
def blob(B, c, size, rng, mat='hedge', tag='detail', flat=0.85, **kw):
    """a low-poly clipped shrub / crown: a jittered icosahedron (20 triangles)"""
    global _ICO
    if _ICO is None:
        t = (1 + 5 ** 0.5) / 2
        V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
        _ICO = (V, F)
    V, F = _ICO
    P = V * (1 + rng.uniform(-0.12, 0.12, (len(V), 1))) * [size / 2, size / 2, size / 2 * flat] + np.asarray(c, float)
    B.add(P, F, mat, tag=tag, smooth=True, **kw)

def red_chochin(B, u, v, z_top, r=0.15, h=0.42, lit=False):
    """a red paper lantern (赤提灯): vermilion body, black caps (lit ones get a lamp)"""
    z = z_top - h - 0.06
    prim.lathe(B, (u, v, z), [(r * 0.7, 0.0), (r * 0.95, h * 0.18), (r, h * 0.5), (r * 0.95, h * 0.82), (r * 0.7, h)], 8, 'vermilion', tag='main', c0=M.paint_tint((200, 34, 26)))
    prim.cyl(B, (u, v, z - 0.03), (u, v, z + 0.01), r * 0.72, r * 0.72, 8, 'black_lacquer', tag='detail')
    prim.cyl(B, (u, v, z + h - 0.01), (u, v, z + h + 0.03), r * 0.72, r * 0.72, 8, 'black_lacquer', tag='detail')
    if lit: B.lamp(u, v, z + h / 2, 4.0, (1.0, 0.35, 0.18))

BANNER = [(200, 40, 34), (230, 220, 200), (40, 60, 120), (90, 140, 70), (230, 180, 60), (130, 40, 90)]
def nobori(B, u, v, rng, tint=None):
    """のぼり: a tall narrow cloth banner on a pole with a cross bar, the shops' flags along the street"""
    tint = tint or BANNER[int(rng.integers(len(BANNER)))]
    h = rng.uniform(2.6, 3.1); w = 0.45
    bars(B, [(u, v, 0.0)], [(u, v, h + 0.15)], (1, 0, 0), 0.035, 0.035, 'metal_grey', tag='detail')
    bars(B, [(u, v, h)], [(u + w + 0.05, v, h)], (0, 0, 1), 0.025, 0.025, 'metal_grey', tag='detail')
    P = np.array([(u + 0.03, v, h - 1.9), (u + w, v, h - 1.9), (u + w, v, h - 0.02), (u + 0.03, v, h - 0.02)])
    B.add(P, [[0, 1, 2], [0, 2, 3]], 'cloth', tag='detail', c0=(*tint, 0))
    B.add(P, [[0, 2, 1], [0, 3, 2]], 'cloth', tag='detail', c0=(*tint, 0))
    # the white lettering stripe (paint, inscription program)
    Q = P + [0.0, -0.005, 0.0]; Q[:, 0] = np.clip(Q[:, 0], u + 0.12, u + w - 0.09)
    B.add(Q, [[0, 1, 2], [0, 2, 3]], 'white_paint', tag='detail', UV=np.array([(0, 0), (0.25, 0), (0.25, 2.0), (0, 2.0)]), c1=(0, 7, int(rng.integers(251)), 0))
    prim.cyl(B, (u, v, 0.0), (u, v, 0.12), 0.12, 0.1, 6, 'stone', tag='detail')

# ------------------------------------------------------------------ the front (copy of machiya._front, extended)
def _bays(W):
    nb = max(1, int(round(W / 1.85)))
    return nb, np.linspace(0.0, W, nb + 1)

def front(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info):
    hy = s.get('hy') or {}
    kind = s['kind']
    shop = hy.get('shop')
    nb, ed = _bays(W)
    pw = 0.12
    z1 = s['z1'] if s['z1'] else 2.72 + rng.uniform(-0.12, 0.15)
    if kind == 'hiraya': z1 = min(z1, z_wp - 0.25)
    door = int(rng.integers(nb)) if nb > 2 else (0 if rng.random() < 0.5 else nb - 1)
    if s['door'] is not None: door = s['door'] if s['door'] >= 0 else -99
    types = []
    for i in range(nb):
        if shop == 'open': types.append('open')
        elif shop == 'glass': types.append('door' if i == door else 'glass')
        elif shop == 'mixed':
            if i == door: types.append('open')
            else: types.append('open' if rng.random() < 0.45 else ('glass' if rng.random() < 0.6 else 'lattice'))
        elif i == door: types.append('door')
        elif s['front1'] == 'redwall': types.append('red')
        elif kind == 'shop': types.append('shop')
        elif s['degoshi'] and rng.random() < 0.7 and s['lattice'] != 'none': types.append('degoshi')
        elif s['lattice'] == 'none' or rng.random() < 0.12: types.append('wall')
        else: types.append('lattice')
    pitch = 0.046 if s['lattice'] == 'senbon' else 0.09
    sw = 0.026 if s['lattice'] == 'senbon' else 0.055
    hbox(B, 0, W, -0.22, 0.02, -0.25, 0.06, 'stone', tag='main')
    bars(B, np.c_[ed, np.full(nb + 1, -0.02), np.zeros(nb + 1)], np.c_[ed, np.full(nb + 1, -0.02), np.full(nb + 1, z1)], (1, 0, 0), pw, 0.14, wmat, tag='main', caps=True, **wtint)
    bars(B, [(0, -0.03, z1 - 0.1)], [(W, -0.03, z1 - 0.1)], (0, 0, 1), 0.2, 0.12, wmat, tag='main', **wtint)
    hz = 2.42
    iy = []
    iykind = 'plank' if s['inuyarai'] == 'plank' else 'slope' if s['inuyarai'] == 'slope' else 'bamboo'
    open_spans = []
    for i, t in enumerate(types):
        a = ed[i] + pw / 2; b = ed[i + 1] - pw / 2
        if b - a < 0.3: continue
        if t == 'open':
            zt = min(hz + 0.15, z1 - 0.2)
            front_rect(B, a, b, zt, z1 - 0.2, 0.02, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            open_bay(B, a, b, zt, rng, seed, hy, info)
            open_spans.append((a, b))
            if i == door:
                if s['noren']: M.noren(B, a + 0.05, b - 0.05, zt - 0.02, 0.62, -0.04, s['noren'])
                info['door'] = (a, b)
            continue
        if t == 'glass':
            front_rect(B, a, b, hz, z1 - 0.2, 0.02, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            glass_bay(B, a, b, hz, rng, hy)
            continue
        if t == 'red':
            sk = s['skirt']
            front_rect(B, a, b, 0.05, sk, -0.01, 'wall_board', c0=(40, 33, 28, 0))
            front_rect(B, a, b, sk, z1 - 0.2, 0.025, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
            continue
        front_rect(B, a, b, hz, z1 - 0.2, 0.02, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
        if t == 'door':
            dw = min(b - a, 1.7); da = a + (b - a - dw) / 2 if b - a > 2.2 else a; db = da + dw
            zd = 1.98
            if da > a + 0.05: front_rect(B, a, da, 0.05, hz, 0.02, 'wall_board', c0=(70, 58, 46, 0))
            if db < b - 0.05: front_rect(B, db, b, 0.05, hz, 0.02, 'wall_board', c0=(70, 58, 46, 0))
            front_rect(B, da, db, zd, hz, 0.0, 'wall_board', c0=(60, 48, 38, 0))
            rd = 0.38
            side_rect(B, 0.0, rd, 0.0, zd, da, 'wood_dark', facing=1); side_rect(B, 0.0, rd, 0.0, zd, db, 'wood_dark', facing=-1)
            hbox(B, da, db, 0.0, rd, zd - 0.01, zd + 0.06, 'wood_dark', tag='detail')
            prim.polygon(B, [(da, -0.02), (db, -0.02), (db, rd), (da, rd)], 0.06, 'stone', tag='main')
            if shop and rng.random() < 0.6:
                # a shop entrance: glazed door with the lit shoji above
                front_rect(B, da + 0.04, db - 0.04, 0.08, zd - 0.06, rd - 0.04, 'glass')
                bars(B, [((da + db) / 2, rd - 0.06, 0.08)], [((da + db) / 2, rd - 0.06, zd - 0.06)], (1, 0, 0), 0.05, 0.04, 'wood_dark', tag='detail')
            else:
                lattice(B, da + 0.04, db - 0.04, 0.55, zd - 0.06, rd - 0.03, pitch=0.07, sw=0.022, sd=0.03, mat='wood_dark', back='black_lacquer', back_dv=0.05, mid=False)
                front_rect(B, da + 0.04, db - 0.04, 0.08, 0.55, rd - 0.04, 'wood_dark')
            hbox(B, da + 0.1, db - 0.1, -0.5, -0.06, 0.0, 0.1, 'stone', tag='detail')
            if s['noren']:
                M.noren(B, da + 0.02, db - 0.02, zd - 0.02, 0.85 if rng.random() < 0.6 else 1.35, 0.06, s['noren'])
            if s['nameboard']:
                nu = da - 0.18 if da - a > 0.3 else (db + 0.18 if b - db > 0.3 else da + 0.15)
                M.nameboard(B, min(max(nu, a + 0.12), b - 0.12), 1.45, 1.95, 0.0, seed=seed)
            info['door'] = (da, db)
        elif t == 'shop':
            front_rect(B, a, b, 0.05, 0.45, -0.01, 'wood_dark')
            front_rect(B, a, b, 0.45, 2.3, 0.08, 'glass', tag='main')
            nm = max(1, int((b - a) / 0.9))
            mu = np.linspace(a, b, nm + 1)
            bars(B, np.c_[mu, np.full(nm + 1, 0.06), np.full(nm + 1, 0.45)], np.c_[mu, np.full(nm + 1, 0.06), np.full(nm + 1, 2.3)], (1, 0, 0), 0.05, 0.05, 'wood_dark', tag='detail')
            bars(B, [(a, 0.06, 2.3), (a, 0.06, 0.45)], [(b, 0.06, 2.3), (b, 0.06, 0.45)], (0, 0, 1), 0.07, 0.06, 'wood_dark', tag='detail')
            front_rect(B, a, b, 2.3, hz, 0.0, 'wall_board', c0=(60, 48, 38, 0))
        elif t == 'wall':
            front_rect(B, a, b, 0.05, 0.9, -0.01, 'wall_board', c0=(64, 52, 42, 0))
            wall_holes(B, a, b, 0.9, hz, 0.0, [], 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
        elif t == 'lattice':
            front_rect(B, a, b, 0.05, 0.46, -0.01, 'wall_board', c0=(64, 52, 42, 0))
            lattice(B, a, b, 0.46, hz, -0.03, pitch=pitch, sw=sw, mat=wmat, c0=wtint.get('c0', (255, 255, 255, 0)))
            if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
        else:   # 出格子
            dv = -0.42; zt = 2.22
            front_rect(B, a, b, 0.2, 0.46, dv - 0.01, 'wall_board', c0=(64, 52, 42, 0))
            hbox(B, a, b, dv - 0.02, 0.0, 0.42, 0.47, wmat, tag='main', **wtint)
            hbox(B, a - 0.03, b + 0.03, dv - 0.06, 0.0, zt, zt + 0.05, wmat, tag='main', **wtint)
            lattice(B, a, b, 0.47, zt, dv, pitch=pitch, sw=sw, mat=wmat, back='black_lacquer', back_dv=-dv - 0.02, c0=wtint.get('c0', (255, 255, 255, 0)))
            for (u, f) in ((a + 0.015, -1), (b - 0.015, 1)):
                M.side_lattice(B, dv + 0.02, -0.02, 0.47, zt, u, mat=wmat, c0=wtint.get('c0', (255, 255, 255, 0)))
            side_rect(B, dv, 0.0, 0.2, 0.47, a, 'wall_board', facing=-1, c0=(64, 52, 42, 0)); side_rect(B, dv, 0.0, 0.2, 0.47, b, 'wall_board', facing=1, c0=(64, 52, 42, 0))
            front_rect(B, a, b, zt + 0.05, hz, 0.0, 'wall_plaster', c0=(*wall_t, 0))
            if s['komayose']: M.komayose(B, a - pw / 2, b + pw / 2, v=dv - 0.4, h=0.95)
    runs = []
    for (a, b) in sorted(iy):
        if runs and a - runs[-1][1] < 0.25: runs[-1] = (runs[-1][0], b)
        else: runs.append((a, b))
    ih = (1.05 if iykind != 'bamboo' else 0.92) + rng.uniform(-0.04, 0.06)
    for (a, b) in runs:
        M.inuyarai(B, a + 0.02, b - 0.02, h=ih, out=0.45 if iykind == 'bamboo' else 0.75, kind=iykind)
    # the 庇
    zh = z1 + 0.1
    depth = 0.95 if kind != 'shop' else 1.25
    if hy.get('hisashi_depth'): depth = hy['hisashi_depth']
    if s['hisashi'] and kind not in ('hiraya',):
        zh = z1 + 0.12 + (rng.uniform(-0.05, 0.05) if not s['z1'] else 0.0)
        zw = M.hisashi(B, -0.02, W + 0.02, zh, depth=depth, pitch=0.36, v=-0.02, brackets=ed[1:-1] if nb > 1 else [W / 2], manju=rng.random() < 0.5)
        if s['chochin'] and 'door' in info:
            da, db = info['door']
            uu = da - 0.25 if da > 0.5 else db + 0.25
            M.chochin(B, uu, -0.45, zh - 0.18, lamp=s['lamps'])
            info['lamps'].append(uu)
        upper0 = zw + 0.05
    else:
        upper0 = z1 + 0.1
    # ---------------- shop accessories (in the street, at the foot of the front; on the lane's own level)
    lzf = hy.get('lz') if hy else None
    xf = B.xf
    def gz(u, v):
        if lzf is None or xf is None: return 0.0
        p = xf @ np.array([u, v, 0.0, 1.0])
        return float(lzf(p[0], p[1]) - p[2])
    def level(u0, u1, v0, v1):
        zs = [gz(u, v) for u in (u0, u1) for v in (v0, v1)]
        return min(zs), max(zs)
    if hy:
        if hy.get('awning') is not None and s['hisashi'] and kind != 'hiraya':
            ua = 0.15; ub = W - 0.15
            if hy.get('awning_part'): ub = min(ub, ua + max(1.2, W * rng.uniform(0.4, 0.7)))
            awning(B, ua, ub, zh - 0.22, depth, rng.uniform(0.5, 0.8), rng.uniform(0.45, 0.65), hy['awning'])
        if hy.get('lanterns'):
            n = int(hy['lanterns'])
            us = np.linspace(0.5, W - 0.5, n) if n > 1 else [W * rng.uniform(0.2, 0.8)]
            red = hy.get('red_lanterns', True)
            for k, u in enumerate(us):
                if red: red_chochin(B, u, -depth + 0.25, zh - 0.12, lit=(k == 0))
                else: M.chochin(B, u, -depth + 0.25, zh - 0.12, r=0.15, h=0.4, lamp=(k == 0))
        if hy.get('bench'):
            bw = min(1.8, W * 0.45)
            ua = rng.uniform(0.3, max(0.31, W - bw - 0.4))
            lo, hi = level(ua, ua + bw + (0.3 if hy.get('parasol') else 0.0), -1.4, -0.4)
            if hi - lo < 0.12 and lo > -0.9:
                from jk.core import Frame
                with Frame(B, 0.0, 0.0, hi, 0.0):
                    bench(B, ua, ua + bw, -0.75, rng, parasol=hy.get('parasol', False))
        if hy.get('sign') and W > 2.4:
            u = rng.uniform(0.4, W - 0.4)
            lo, hi = level(u - 0.2, u + 0.2, -0.7, -0.4)
            if hi - lo < 0.12:
                from jk.core import Frame
                with Frame(B, 0.0, 0.0, hi, 0.0):
                    stand_sign(B, u, -0.55, rng, seed)
        for k in range(int(hy.get('pots', 0))):
            u = rng.uniform(0.25, W - 0.25)
            lo, hi = level(u - 0.15, u + 0.15, -0.55, -0.3)
            if hi - lo < 0.15:
                from jk.core import Frame
                with Frame(B, 0.0, 0.0, hi if hi > -0.2 else max(hi, -0.25), 0.0):
                    pot(B, u, -0.42, rng)
        for k in range(int(hy.get('banners', 0))):
            u = 0.3 + (W - 0.6) * (k + 0.5) / max(1, int(hy['banners']))
            lo, hi = level(u - 0.2, u + 0.2, -1.4, -1.0)
            if hi - lo < 0.15:
                from jk.core import Frame
                with Frame(B, 0.0, 0.0, hi, 0.0):
                    nobori(B, u, -1.25, rng, hy.get('banner_tint'))
        if hy.get('table') and W > 3.0:
            # goods on a low stall out in front (陶器 / 菓子)
            ta = rng.uniform(0.3, W - 2.0); tb = ta + rng.uniform(1.2, 1.8)
            lo, hi = level(ta, tb, -1.05, -0.4)
            if hi - lo < 0.12 and lo > -0.9:
                from jk.core import Frame
                with Frame(B, 0.0, 0.0, hi, 0.0):
                    display_table(B, ta, tb, -1.05, -0.4, 0.68, rng, kind=hy.get('goods', 'boxes'))
                    prim.polygon(B, [(ta, -1.05), (tb, -1.05), (tb, -0.4), (ta, -0.4)], 0.05, 'stone', tag='block')
        if info.get('shop_lights') and rng.random() < 0.4:
            cu, cv, cz = info['shop_lights'][len(info['shop_lights']) // 2]
            B.lamp(cu, cv, cz, 14.0, (1.0, 0.8, 0.55))
    if kind == 'hiraya':
        front_rect(B, 0, W, z1, z_wp, 0.0, 'wall_plaster', c0=(*wall_t, 0))
        return zh
    # ---------------- upper storeys (as machiya._front)
    floors = []
    if kind == 'tsushi':
        floors.append(('tsushi', upper0, z_wp))
    elif kind == 'sangai':
        zm = upper0 + (z_wp - upper0) * 0.5
        floors += [('ochaya', upper0, zm), ('third', zm, z_wp)]
    elif kind == 'shop' and z_wp > 8.0:
        zm = upper0 + (z_wp - upper0) * 0.5
        floors += [('shop2', upper0, zm), ('third', zm, z_wp)]
    else:
        floors.append(('ochaya' if kind != 'shop' else 'shop2', upper0, z_wp))
    nb2 = max(1, int(round(W / 1.95)))
    pu = np.linspace(0.0, W, nb2 + 1)
    bars(B, np.c_[pu, np.full(nb2 + 1, 0.0), np.full(nb2 + 1, upper0 - 0.3)], np.c_[pu, np.full(nb2 + 1, 0.0), np.full(nb2 + 1, z_wp)], (1, 0, 0), 0.12, 0.12, 'wood_dark', tag='main', caps=True)
    if s['upper'] == 'itagoshi':
        floors = [('itagoshi', upper0, z_wp)]
    for (ft, za, zb) in floors:
        if ft == 'itagoshi':
            vz = -0.32
            front_rect(B, 0.0, W, za - 0.3, zb, 0.06, 'wall_plaster', c0=(*wall_t, 0))
            front_rect(B, 0.05, W - 0.05, za + 0.1, zb - 0.25, vz + 0.12, 'black_lacquer')
            n = max(2, int(W / 0.2))
            bu = np.linspace(0.08, W - 0.08, n)
            bars(B, np.c_[bu, np.full(n, vz), np.full(n, za)], np.c_[bu, np.full(n, vz), np.full(n, zb - 0.2)], (1, 0, 0), 0.12, 0.03, 'wood_dark', tag='detail', hide=(0, 1, 0))
            continue
        if ft == 'tsushi':
            nw = 1 if W < 4.5 else 2 if W < 8 else 3
            holes = []
            for k in range(nw):
                cu = W * (k + 0.5) / nw; ww = min(0.95, W / nw - 0.6); h0 = za + 0.35; h1 = min(zb - 0.3, h0 + 0.62)
                if ww > 0.4 and h1 - h0 > 0.3: holes.append((cu - ww / 2, cu + ww / 2, h0, h1))
            wall_holes(B, 0.0, W, za - 0.3, zb, 0.06, holes, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            for (ha, hb, h0, h1) in holes:
                front_rect(B, ha, hb, h0, h1, 0.16, 'black_lacquer')
                for (aa, bb, cc, dd) in ((ha, hb, h0 - 0.06, h0), (ha, hb, h1, h1 + 0.06)):
                    hbox(B, aa - 0.06, bb + 0.06, 0.0, 0.16, cc, dd, 'wall_plaster', tag='detail', c0=(*wall_t, 0), faces='yzZ')
                side_rect(B, 0.06, 0.16, h0, h1, ha, 'wall_plaster', facing=1, c0=(*wall_t, 0)); side_rect(B, 0.06, 0.16, h0, h1, hb, 'wall_plaster', facing=-1, c0=(*wall_t, 0))
                nbars = max(4, int((hb - ha) / 0.1))
                bu = np.linspace(ha + 0.05, hb - 0.05, nbars)
                bars(B, np.c_[bu, np.full(nbars, 0.1), np.full(nbars, h0)], np.c_[bu, np.full(nbars, 0.1), np.full(nbars, h1)], (1, 0, 0), 0.045, 0.06, 'wall_plaster', tag='detail', c0=(*wall_t, 0))
        elif ft in ('ochaya', 'third', 'shop2'):
            for i in range(nb2):
                a = pu[i] + 0.06; b = pu[i + 1] - 0.06
                wz0 = za + (0.35 if ft != 'third' else 0.5); wz1 = zb - 0.38
                if wz1 - wz0 < 0.5: wz1 = zb - 0.1
                front_rect(B, a, b, za - 0.3, wz0, 0.04, 'wall_board' if ft != 'shop2' else 'wall_plaster', c0=(70, 58, 46, 0) if ft != 'shop2' else (*wall_t, 0))
                front_rect(B, a, b, wz1, zb, 0.04, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
                glazed = ft == 'shop2' or rng.random() < 0.3
                lit = hy and rng.random() < 0.3
                front_rect(B, a, b, wz0, wz1, 0.1, 'lantern_paper' if lit else ('glass' if glazed else 'wall_plaster'), c0=(238, 232, 214, 0) if not glazed else (255, 255, 255, 0))
                bars(B, [(a, 0.06, wz0), (a, 0.06, wz1)], [(b, 0.06, wz0), (b, 0.06, wz1)], (0, 0, 1), 0.06, 0.06, 'wood_dark', tag='detail')
                if ft == 'shop2' or (rng.random() < 0.5 and not s['sudare']):
                    lattice(B, a, b, wz0, wz1, 0.0, pitch=0.06, sw=0.02, sd=0.03, back=None, rails=False, mid=False)
                else:
                    nm = max(2, int((b - a) / 0.45))
                    mu = np.linspace(a, b, nm + 1)[1:-1]
                    bars(B, np.c_[mu, np.full(len(mu), 0.07), np.full(len(mu), wz0)], np.c_[mu, np.full(len(mu), 0.07), np.full(len(mu), wz1)], (1, 0, 0), 0.025, 0.03, 'wood_dark', tag='detail')
                    zz = np.linspace(wz0, wz1, 4)[1:-1]
                    bars(B, np.c_[np.full(len(zz), a), np.full(len(zz), 0.075), zz], np.c_[np.full(len(zz), b), np.full(len(zz), 0.075), zz], (0, 0, 1), 0.02, 0.025, 'wood_dark', tag='detail')
                if s['sudare'] and ft != 'shop2':
                    down = rng.uniform(0.55, 1.0)
                    M.sudare(B, a + 0.02, b - 0.02, zb - 0.12, zb - 0.12 - (zb - 0.12 - za - 0.25) * down, -0.12)
            if ft == 'ochaya' and s['railing']:
                M.board_railing(B, 0.12, W - 0.12, -0.58, za + 0.02, h=0.82, returns=0.5)
            if ft == 'third':
                bars(B, [(0, -0.03, za)], [(W, -0.03, za)], (0, 0, 1), 0.18, 0.1, 'wood_dark', tag='main', caps=True)
                if rng.random() < 0.6: M.board_railing(B, 0.12, W - 0.12, -0.35, za + 0.05, h=0.75, returns=0.3)
    # signs: a board on the 庇 (shops) and a hanging sign
    if kind == 'shop' or hy.get('kanban'):
        sw_ = min(W - 0.6, 3.6)
        if sw_ > 0.8:
            su = (W - sw_) / 2
            hbox(B, su, su + sw_, -0.2, -0.12, upper0 + 0.02, upper0 + 0.62, 'wood_dark', tag='main')
            quad(B, (su + 0.05, -0.205, upper0 + 0.07), (su + sw_ - 0.05, -0.205, upper0 + 0.07), (su + sw_ - 0.05, -0.205, upper0 + 0.57), (su + 0.05, -0.205, upper0 + 0.57),
                 s['sign'] or ('white_paint' if rng.random() < 0.5 else 'wood_natural'), tag='main', uv=np.array([(0, 0), (sw_ * 1.6, 0), (sw_ * 1.6, 0.8), (0, 0.8)]), c1=(0, 7, int(seed) % 251, 0))
    if kind == 'shop' or hy.get('hanging_sign'):
        if rng.random() < 0.7:
            uu = 0.35 if rng.random() < 0.5 else W - 0.35
            hbox(B, uu - 0.03, uu + 0.03, -0.95, -0.02, upper0 + 2.1, upper0 + 2.16, 'metal_dark', tag='detail')
            hbox(B, uu - 0.03, uu + 0.03, -0.92, -0.18, upper0 + 0.35, upper0 + 2.1, 'wood_dark', tag='detail')
            for f in (-1, 1):
                P = np.array([(uu + f * 0.035, -0.9, upper0 + 0.4), (uu + f * 0.035, -0.2, upper0 + 0.4), (uu + f * 0.035, -0.2, upper0 + 2.05), (uu + f * 0.035, -0.9, upper0 + 2.05)])
                I = [[0, 1, 2], [0, 2, 3]] if f > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'white_paint', UV=np.array([(0, 0), (1.0, 0), (1.0, 2.2), (0, 2.2)]), tag='detail', c1=(0, 7, (int(seed) * 7) % 251, 0))
    if rng.random() < 0.7:
        uu = W - 0.18 if rng.random() < 0.5 else 0.18
        prim.cyl(B, (uu, -o + 0.05, z_edge - 0.2), (uu, -0.12, z_edge - 0.55), 0.035, 0.035, 6, 'bronze', tag='detail')
        prim.cyl(B, (uu, -0.12, z_edge - 0.55), (uu, -0.12, upper0 - 0.1), 0.035, 0.035, 6, 'bronze', tag='detail')
    return zh
