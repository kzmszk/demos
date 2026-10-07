"""烏丸口 bus plaza: the forecourt in front of the Kyoto Station gate (granite paving, tactile guide lines, planters, rails),
the long bus canopies over bays A, B, C, JR and D (OSM shelters: standing-seam roofs on forked steel columns), bay posts,
the taxi rank in front of Hotel Granvia, kiosks and glass vaults, street lamps (lit in the evening) and trees."""
import math
import numpy as np
from jk import prim, arch
from . import station_util as U

Z = np.array([0.0, 0.0, 1.0])
ROOF_TINT = (206, 209, 213)

# OSM shelter outlines (site frame)
SHELTERS = {
    'A': dict(x0=-40.2, x1=17.1, y0=79.5, y1=86.4, axis='x', rows=2),
    'B': dict(x0=-42.8, x1=16.7, y0=93.5, y1=101.0, axis='x', rows=2),
    'C': dict(x0=-82.1, x1=34.3, y0=130.0, y1=142.5, axis='x', rows=3),
    'JR': dict(x0=-34.0, x1=12.0, y0=68.5, y1=72.9, axis='x', rows=1),
}
D_PATH = [(12.0, 71.0), (22.0, 71.1), (27.5, 72.0), (31.0, 74.2), (32.8, 77.5), (32.6, 85.0), (32.5, 130.0)]
BAY_POSTS = [('B1', -40.3, 99.1), ('B2', -25.6, 99.6), ('B3', -9.5, 99.9), ('A1', -37.8, 84.7), ('A2', -20.2, 85.3), ('A3', -4.1, 85.5),
             ('C1', -26.9, 142.3), ('C2', 2.5, 142.0), ('C3', 26.6, 143.2), ('C4', -31.8, 131.2), ('C5', -17.0, 131.3), ('C6', -0.1, 131.9),
             ('D1', 32.5, 87.9), ('D2', 32.4, 105.9), ('D3', 32.0, 120.9), ('JR1', -32.3, 71.3), ('JR2', -11.2, 71.8), ('JR3', 3.3, 72.3)]

def canopy_profile(w, z0=4.3, t=1.0):
    """closed cross-section (x across, y up) of a long bus canopy: flat soffit, rounded standing-seam top"""
    h = w / 2
    return [(-h, z0), (h, z0), (h + 0.05, z0 + 0.3), (h * 0.88, z0 + 0.7), (h * 0.55, z0 + 0.98), (0.0, z0 + 1.08), (-h * 0.55, z0 + 0.98), (-h * 0.88, z0 + 0.7), (-h - 0.05, z0 + 0.3)]

def canopy(B, S, path, w, zg, posts_every=9.0, rows=1, tag_posts='main', name=''):
    """a canopy along a 2D path (list of points); returns the column positions"""
    path = np.array(path, float)
    # densify the path so curves follow
    pts = [path[0]]
    for a, b in zip(path[:-1], path[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 4.0))
        for k in range(1, n + 1): pts.append(a + (b - a) * k / n)
    pts = np.array(pts)
    z = S.ground(pts[:, 0], pts[:, 1]) + 0.12
    P3 = np.c_[pts, z]
    prim.sweep(B, P3, canopy_profile(w), 'roof_metal', up=(0, 0, 1), closed=True, tag='main', smooth=False, caps=True, c0=(*ROOF_TINT, 0), c1=(0, 0, 3, 0))
    # lit soffit strips (rows of lamps along the underside, on at dusk)
    Lc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    lp0 = []; lp1 = []
    for sv in np.arange(3.0, Lc[-1] - 1.0, 6.0):
        i = min(max(1, np.searchsorted(Lc, sv)), len(pts) - 1)
        t = U.unit(pts[i] - pts[i - 1]); nrm = np.array([-t[1], t[0]])
        offs_l = [0.0] if rows == 1 else list(np.linspace(-(w / 2 - 1.6), (w / 2 - 1.6), rows))
        for o in offs_l:
            c = pts[i] + nrm * o
            zz = float(S.ground(c[0], c[1])) + 0.12 + 4.27
            lp0.append((*(c - t * 0.7), zz)); lp1.append((*(c + t * 0.7), zz))
    if lp0:
        U.obox_batch(B, np.array(lp0), np.array(lp1), 0.28, 0.05, 'lamp', up=(0, 0, 1), tag='main')
    # columns: forked 'tree' columns along `rows` lines
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n = max(2, int(L[-1] / posts_every) + 1)
    s = np.linspace(2.5, L[-1] - 2.5, n)
    cols = []
    for sv in s:
        i = min(np.searchsorted(L, sv), len(pts) - 1)
        p = pts[i]; q = pts[min(i + 1, len(pts) - 1)] if i == 0 else pts[i - 1]
        t = U.unit(p - q) if np.linalg.norm(p - q) > 1e-6 else np.array([1.0, 0])
        nrm = np.array([-t[1], t[0]])
        offs = [0.0] if rows == 1 else list(np.linspace(-(w / 2 - 1.6), (w / 2 - 1.6), rows))
        for o in offs:
            cols.append(p + nrm * o)
    cols = np.array(cols)
    zc = S.ground(cols[:, 0], cols[:, 1])
    # trunks + two forks to the soffit
    p0 = np.c_[cols, zc]; p1 = np.c_[cols, zc + 3.4]
    U.obox_batch(B, p0, p1, 0.26, 0.26, 'metal_dark', up=(0, 1, 0), tag=tag_posts)
    for sgn in (-1, 1):
        p2 = np.c_[cols[:, 0] + sgn * 0.0, cols[:, 1], zc + 3.4]
        # forks in the across-direction approximated in world x/y by the first path direction
        d = np.zeros((len(cols), 2)); d[:, 1] = 1.0
        p3 = np.c_[cols + d * sgn * 1.5, zc + 4.25]
        U.obox_batch(B, p2, p3, 0.14, 0.14, 'metal_dark', up=(1, 0, 0), tag='detail')
    # base plates
    U.box_batch(B, np.c_[cols - 0.28, zc], np.c_[cols + 0.28, zc + 0.12], 'curb')
    # lights under the canopy
    for i in range(0, len(cols), max(1, len(cols) // 8)):
        B.lamp(cols[i][0], cols[i][1], zc[i] + 3.9, 45, (1.0, 0.92, 0.78))
    return cols

def platform_slab(B, S, x0, y0, x1, y1, h=0.15, tag='main'):
    z = float(S.ground((x0 + x1) / 2, (y0 + y1) / 2))
    U.box(B, x0, y0, z - 0.2, x1, y1, z + h, 'curb', c0=(255, 255, 255, 0))
    U.box(B, x0, y0, z + h - 0.01, x1, y1, z + h, 'curb', tag='walk', faces='Z', max_edge=1e6)

def lamp_post(B, x, y, z, h=9.0, arm=1.8, yaw=0.0, watts=140, double=False):
    prim.cyl(B, (x, y, z), (x, y, z + h), 0.13, 0.07, 8, 'metal_dark', tag='main')
    dirs = [yaw] + ([yaw + math.pi] if double else [])
    for a in dirs:
        dx, dy = math.cos(a), math.sin(a)
        U.obox_batch(B, np.array([[x, y, z + h - 0.15]]), np.array([[x + dx * arm, y + dy * arm, z + h + 0.15]]), 0.09, 0.09, 'metal_dark', up=(0, 0, 1), tag='detail')
        U.box(B, x + dx * arm - 0.35, y + dy * arm - 0.2, z + h + 0.05, x + dx * arm + 0.35, y + dy * arm + 0.2, z + h + 0.2, 'lamp', tag='detail', faces='z')
        B.lamp(x + dx * arm, y + dy * arm, z + h, watts, (1.0, 0.9, 0.72))

def taxi(B, x, y, z, yaw, body=(20, 20, 22)):
    from jk import Frame
    with Frame(B, x, y, z, yaw):
        U.box(B, -2.3, -0.85, 0.32, 2.3, 0.85, 0.98, 'cloth', c0=(*body, 0))
        U.box(B, -1.1, -0.78, 0.98, 1.0, 0.78, 1.52, 'glass')
        U.box(B, -1.0, -0.8, 1.52, 0.9, 0.8, 1.58, 'cloth', c0=(*body, 0))
        U.box(B, -0.25, -0.22, 1.58, 0.25, 0.22, 1.74, 'lantern_paper', tag='detail')
        for (dx, dy) in ((1.45, 0.75), (1.45, -0.75), (-1.45, 0.75), (-1.45, -0.75)):
            prim.cyl(B, (dx, dy - 0.1, 0.32), (dx, dy + 0.1, 0.32), 0.32, 0.32, 10, 'black_lacquer', caps=(True, True), tag='detail')

def bus(B, x, y, z, yaw, tint=(236, 238, 232), band=(30, 110, 60)):
    from jk import Frame
    with Frame(B, x, y, z, yaw):
        U.box(B, -5.2, -1.3, 0.45, 5.2, 1.3, 3.0, 'cloth', c0=(*tint, 0))
        U.box(B, -5.1, -1.32, 1.4, 5.1, 1.32, 2.5, 'glass', faces='yY')
        U.box(B, -5.15, -1.33, 0.9, 5.15, 1.33, 1.3, 'cloth', c0=(*band, 0), faces='yY')
        U.box(B, 5.18, -1.1, 1.2, 5.22, 1.1, 2.4, 'glass', faces='X')
        for dx in (-3.4, 3.4):
            for dy in (-1.2, 1.2):
                prim.cyl(B, (dx, dy - 0.15, 0.5), (dx, dy + 0.15, 0.5), 0.5, 0.5, 10, 'black_lacquer', tag='detail')

def barrel_vault(B, x0, y0, x1, y1, z, rise=3.6, along='x', mat_g='glass', ribs=2.4):
    """a translucent barrel vault (arched glass roof) with steel ribs, springing at z"""
    L = (x1 - x0) if along == 'x' else (y1 - y0)
    W = (y1 - y0) if along == 'x' else (x1 - x0)
    n = 10
    th = np.linspace(-math.pi / 2 + 0.25, math.pi / 2 - 0.25, n + 1)
    R = W / 2 / math.cos(0.25) if W / 2 > 0 else 1
    prof = np.array([(W / 2 * math.sin(t) / math.sin(math.pi / 2 - 0.25) , rise * math.cos(t) / math.cos(0.25) * 1.0) for t in th])
    # arch points in (across, up)
    cx = (x0 + x1) / 2; cy = (y0 + y1) / 2
    def P(a, h, s):
        if along == 'x': return (x0 + s, cy + a, z + h)
        return (cx + a, y0 + s, z + h)
    pts = []
    for s in (0.0, L):
        for (a, h) in prof: pts.append(P(a, h, s))
    # surface as grid
    m = len(prof)
    nn = max(2, int(L / ribs))
    ss = np.linspace(0, L, nn + 1)
    V = np.array([P(a, h, s) for s in ss for (a, h) in prof])
    I = []
    for i in range(nn):
        for j in range(m - 1):
            a = i * m + j
            I += [[a, a + 1, a + m + 1], [a, a + m + 1, a + m]]
    I = np.array(I)
    c = np.array([cx, cy, z - 4.0])
    I = U._fix_outward(V, I, c) if False else I
    # orient outward (up): flip where normal points down
    n_ = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
    I[n_[:, 2] < 0] = I[n_[:, 2] < 0][:, ::-1]
    B.add(V, I, mat_g, UV=V[:, :2], tag='main')
    # ribs
    for s in ss:
        arc = np.array([P(a, h + 0.08, s) for (a, h) in prof])
        U.obox_batch(B, arc[:-1], arc[1:], 0.12, 0.14, 'metal_grey', up=(0, 0, 1), tag='detail', ends=False)
    for (a, h) in prof[::3]:
        U.obox_batch(B, np.array([P(a, h + 0.08, 0)]), np.array([P(a, h + 0.08, L)]), 0.1, 0.12, 'metal_grey', up=(0, 0, 1), tag='detail', ends=False)

# ================================================================================================
def build_plaza(B, S, zst=None):
    rng = np.random.default_rng(1913)
    gz = lambda x, y: float(S.ground(x, y))
    cols_all = []
    # ---- canopies
    for name, s in SHELTERS.items():
        x0, x1, y0, y1 = s['x0'], s['x1'], s['y0'], s['y1']
        w = y1 - y0; zc = gz((x0 + x1) / 2, (y0 + y1) / 2)
        platform_slab(B, S, x0 - 0.3, y0 - 0.3, x1 + 0.3, y1 + 0.3)
        cols_all.append(canopy(B, S, [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], w, zc, posts_every=9.5, rows=s['rows'], name=name))
    cols_all.append(canopy(B, S, D_PATH, 4.6, 0, posts_every=9.0, rows=1, name='D'))
    # the columns stop walkers (invisible blockers)
    cc = np.vstack(cols_all)
    zc = S.ground(cc[:, 0], cc[:, 1])
    U.box_batch(B, np.c_[cc - 0.3, zc - 0.5], np.c_[cc + 0.3, zc + 3.5], 'curb', tag='block')
    # ---- bay posts with their plates
    for (nm, x, y) in BAY_POSTS:
        z = gz(x, y)
        prim.cyl(B, (x, y, z), (x, y, z + 2.7), 0.045, 0.045, 6, 'metal_dark', tag='detail')
        U.box(B, x - 0.28, y - 0.03, z + 2.1, x + 0.28, y + 0.03, z + 2.75, 'white_paint', c0=(235, 235, 235, 0), tag='detail')
        U.box(B, x - 0.28, y - 0.04, z + 2.6, x + 0.28, y + 0.04, z + 2.75, 'vermilion', tag='detail')
    # ---- forecourt (granite) + guide lines + planters + rails
    pave = [(-101.0, 60.0), (-62.0, 60.0), (-62.0, 66.0), (-101.0, 66.0)]
    S.paint.append({'poly': [(-103.0, 40.0), (-31.0, 40.0), (-31.0, 69.0), (-103.0, 69.0)], 'surf': 'stone_slab'})
    S.paint.append({'poly': [(-31.0, 36.0), (60.0, 36.0), (60.0, 56.0), (-31.0, 56.0)], 'surf': 'stone_slab'})
    S.paint.append({'poly': [(-31.0, 56.0), (60.0, 56.0), (60.0, 67.5), (-31.0, 67.5)], 'surf': 'stone_slab'})
    # tactile guide lines
    for pts in ([(-47.0, 56.0), (-47.0, 62.0), (-30.0, 66.5), (8.0, 66.5), (34.0, 66.5)], [(-46.2, 66.5), (-60.0, 66.5), (-84.0, 66.5)]):
        for a, b in zip(pts[:-1], pts[1:]):
            a = np.array(a); b = np.array(b); d = U.unit(b - a); n = np.array([-d[1], d[0]]) * 0.35
            S.paint.append({'poly': [tuple(a - n), tuple(b - n), tuple(b + n), tuple(a + n)], 'surf': 'tactile'})
    # concrete platforms under the canopies
    for name, s in SHELTERS.items():
        S.paint.append({'poly': [(s['x0'] - 0.3, s['y0'] - 0.3), (s['x1'] + 0.3, s['y0'] - 0.3), (s['x1'] + 0.3, s['y1'] + 0.3), (s['x0'] - 0.3, s['y1'] + 0.3)], 'surf': 'concrete'})
    # planters along the plaza edge (granite curb with clipped azalea)
    for x in (-96.0, -84.0, -26.0, -14.0, 14.0, 26.0, 38.0, 48.0):
        z = gz(x, 63.5)
        U.box(B, x, 62.5, z, x + 8.0, 65.0, z + 0.45, 'curb', c0=(255, 255, 255, 0))
        arch.hedge(B, [(x + 0.4, 63.75), (x + 7.6, 63.75)], z + 0.45, h=0.55, w=1.5, ground=None)
    # guard rail along the island's south edge and east edge (tubular)
    def rail(pts, z_off=0.0, step=2.4):
        pts = [np.array(p, float) for p in pts]
        for a, b in zip(pts[:-1], pts[1:]):
            L = np.linalg.norm(b - a)
            n = max(1, int(L / step))
            qs = [a + (b - a) * k / n for k in range(n + 1)]
            zs = [gz(*q) for q in qs]
            for q, z in zip(qs, zs):
                prim.cyl(B, (q[0], q[1], z), (q[0], q[1], z + 0.95), 0.035, 0.035, 5, 'metal_grey', caps=(False, True), tag='detail')
            for hz in (0.95, 0.5):
                P0 = np.array([[q0[0], q0[1], z0 + hz] for q0, z0 in zip(qs[:-1], zs[:-1])]); P1 = np.array([[q1[0], q1[1], z1 + hz] for q1, z1 in zip(qs[1:], zs[1:])])
                U.obox_batch(B, P0, P1, 0.06, 0.06, 'metal_grey', up=(0, 0, 1), tag='detail')
    rail([(-84.0, 67.6), (36.0, 67.6)])
    rail([(36.0, 67.6), (36.0, 100.0)])
    # ---- the kiosk / Porta entrance block in front of the station
    z = gz(-2, 57)
    U.box(B, -12.8, 49.0, z - 0.3, 8.4, 65.8, z + 9.0, 'wall_tile', c0=(196, 176, 148, 30), c1=(0, 0, 9, 0))
    U.box(B, -13.0, 48.8, z + 9.0, 8.6, 66.0, z + 9.4, 'wall_concrete', c0=(160, 158, 154, 0))
    for x in (-8.0, 1.0):
        U.box(B, x - 1.6, 65.75, z + 0.0, x + 1.6, 65.95, z + 3.0, 'glass', faces='Y')
    U.box(B, -4.0, 65.8, z + 4.0, 3.0, 65.96, z + 8.0, 'lamp', faces='Y', tag='main')
    for (x, y) in ((-22.0, 58.0), (-16.0, 59.0), (-22.0, 63.0), (-16.0, 63.0)):
        zz = gz(x, y)
        U.box(B, x - 1.5, y - 1.5, zz, x + 1.5, y + 1.5, zz + 1.1, 'curb', c0=(255, 255, 255, 0))
    # ---- glass vaults over the underground entrances
    barrel_vault(B, -80.0, 60.0, -65.0, 72.0, gz(-72, 66) + 0.4, rise=3.8, along='y')
    barrel_vault(B, 30.0, 47.0, 56.0, 58.0, gz(43, 52) + 0.4, rise=3.4, along='x')
    barrel_vault(B, -21.0, 70.5, -9.0, 76.5, gz(-15, 73) + 0.4, rise=2.2, along='x') if False else None
    # ---- the taxi rank in front of Hotel Granvia (south of its long canopy)
    S.paint.append({'poly': [(76.0, 63.0), (134.0, 63.0), (134.0, 80.0), (76.0, 80.0)], 'surf': 'asphalt'})
    for i in range(13):
        xx = 80.0 + i * 4.4
        a = np.array([xx, 64.0]); b = np.array([xx + 2.4, 76.0]); d = U.unit(b - a); n = np.array([-d[1], d[0]]) * 0.08
        S.paint.append({'poly': [tuple(a - n), tuple(b - n), tuple(b + n), tuple(a + n)], 'surf': 'concrete'})
    cols = [(0, 0, 0), (0, 0, 0), (236, 236, 232), (0, 0, 0), (30, 90, 60), (0, 0, 0), (200, 40, 40), (0, 0, 0), (236, 236, 232), (0, 0, 0), (0, 0, 0), (236, 236, 232)]
    for i in range(12):
        xx = 82.0 + i * 4.4
        taxi(B, xx + 1.4, 68.5 + 0.35 * (i % 3), gz(xx, 68), math.radians(-90 + 10), body=cols[i] if cols[i] != (0, 0, 0) else (22, 22, 26))
    # buses at the bays (a few)
    for (x, y, yaw, tint) in ((-30.0, 76.5, 0.0, (236, 238, 232)), (-8.0, 90.5, 0.0, (222, 232, 214)), (-24.0, 106.0, 0.0, (236, 238, 232)), (-34.0, 137.0, 0.0, (222, 232, 214)), (8.0, 136.0, 0.0, (236, 238, 232))):
        bus(B, x, y, gz(x, y), yaw, tint=tint)
    # ---- street lamps
    for x in np.arange(-92.0, 46.0, 22.0):
        lamp_post(B, x, 64.6, gz(x, 64.6), h=9.0, arm=1.6, yaw=math.pi / 2, double=False)
    for x in np.arange(-84.0, 40.0, 24.0):
        lamp_post(B, x, 146.2, gz(x, 146.2), h=9.5, arm=2.0, yaw=-math.pi / 2, double=False)
    for y in (84.0, 110.0, 126.0):
        lamp_post(B, 36.4, y, gz(36.4, y), h=9.0, arm=1.8, yaw=math.pi, double=False)
    # ---- trees
    otrees = np.array([t['xy'] for t in S.osm['trees']]) if S.osm['trees'] else np.zeros((0, 2))
    def tree(sp, x, y, sc=1.0):
        if len(otrees) and np.min(np.hypot(otrees[:, 0] - x, otrees[:, 1] - y)) < 5.0: return
        B.tree(sp, x, y, gz(x, y), sc * rng.uniform(0.9, 1.15), rng.uniform(0, 6.28))
    for x in (-18.0, -4.0, 14.0, 30.0, 46.0, 56.0):
        tree('keyaki', x, 62.8, 0.95)
    for x in (-98.0, -88.0, -76.0, -58.0, -42.0):
        tree('keyaki', x, 64.0, 1.0)
    for y in (80.0, 98.0, 116.0, 133.0):
        tree('kashi', 37.5, y, 0.9)
    for x in (-70.0, -52.0, -36.0, -20.0, -4.0, 12.0, 28.0):
        tree('keyaki', x, 148.0, 1.05)
    # ---- benches and bins under the canopies, one pair per bay post
    for (nm, x, y) in BAY_POSTS:
        z = gz(x, y)
        ax = 1.0 if nm[0] in 'ABC' or nm.startswith('JR') else 0.0
        dx, dy = (1.0, 0.0) if ax else (0.0, 1.0)
        bx, by = x + (2.2 * dx), y + (2.2 * dy)
        U.box(B, bx - 0.9 * (dx or 0.3), by - 0.9 * (dy or 0.3), z + 0.42, bx + 0.9 * (dx or 0.3), by + 0.9 * (dy or 0.3), z + 0.5, 'wood_natural', tag='detail')
        U.box(B, bx - 0.9 * (dx or 0.3), by - 0.9 * (dy or 0.3), z, bx - 0.8 * (dx or 0.3), by - 0.8 * (dy or 0.3) + 0.0, z + 0.42, 'metal_dark', tag='detail')
        prim.cyl(B, (bx + 1.4 * dx, by + 1.4 * dy, z), (bx + 1.4 * dx, by + 1.4 * dy, z + 0.85), 0.2, 0.2, 8, 'metal_grey', tag='detail')
    # ---- lit information boards on the forecourt (map boards)
    for (x, y, yaw) in ((-30.0, 57.0, math.pi / 2), (-64.0, 58.0, math.pi / 2), (18.0, 56.0, math.pi / 2)):
        z = gz(x, y)
        U.box(B, x - 1.1, y - 0.15, z, x + 1.1, y + 0.15, z + 2.3, 'metal_dark', tag='main')
        U.box(B, x - 0.95, y + 0.14, z + 0.3, x + 0.95, y + 0.17, z + 2.1, 'lamp', tag='main', faces='Y')
        B.lamp(x, y + 0.8, z + 1.4, 25, (1.0, 0.96, 0.85))
    # ---- around the Kyoto Tower building: hedge, planters, street trees
    zt = gz(48, 165)
    arch.hedge(B, [(24.0, 164.6), (47.0, 164.6)], zt, h=0.85, w=1.5)
    arch.hedge(B, [(50.0, 164.6), (70.0, 164.6)], zt, h=0.85, w=1.5)
    arch.hedge(B, [(77.4, 172.0), (77.4, 200.0)], gz(77.4, 185), h=0.8, w=1.4)
    for x in (27.0, 38.0, 59.0, 70.0):
        tree('keyaki', x, 163.0, 1.0)
    tree('kashi', 49.0, 163.5, 0.85)
    for y in (180.0, 196.0, 209.0):
        tree('keyaki', 79.5, y, 1.0)
    # plantings (azalea masses) in the island refuges
    for (x, y) in ((-22.0, 91.0), (14.0, 91.0), (-35.0, 118.0)):
        pass
    return cols_all

def blockers(B, S):
    def blk(x0, y0, x1, y1, z0=None, z1=None, tag='block'):
        zg = float(S.ground((x0 + x1) / 2, (y0 + y1) / 2))
        U.box(B, x0, y0, (zg - 1.0) if z0 is None else z0, x1, y1, (zg + 3.0) if z1 is None else z1, 'curb', tag=tag, max_edge=1e6)
    # the station body
    blk(-256.0, -29.0, -101.0, 27.0)
    blk(-101.0, -29.0, -62.0, 47.5)
    blk(-62.0, -29.0, -30.0, 44.0)
    blk(-30.0, -29.0, 58.0, 39.5)
    for x in (-32.0 + 18.0 * i for i in range(6)):
        blk(x - 1.7, 39.5, x + 1.7, 44.6)
    for (xa, xb) in ((-62.0, -56.0), (-38.0, -32.0)):
        blk(xa, 44.0, xb, 59.7)
    blk(-56.0, 44.0, -38.0, 46.0)
    blk(58.0, -29.0, 73.0, 50.2)
    blk(73.0, -29.0, 80.0, 51.0); blk(92.0, 44.0, 96.0, 51.0); blk(108.0, 44.0, 112.0, 51.0); blk(124.0, 36.0, 204.0, 51.0)
    for (xa, xb) in ((80.0, 92.0), (96.0, 108.0), (112.0, 124.0)): blk(xa, -29.0, xb, 44.0)
    blk(73.0, -29.0, 204.0, 36.0)
    blk(-271.0, -29.0, -256.0, 14.0)
    blk(-256.0, -29.0, 206.0, -22.0)
    # the Kyoto Tower building: back wall + columns
    blk(26.9, 174.3, 69.0, 207.6)
    # the plaza kiosk, vault bases and canopies' columns are handled by the generic walker; kiosk blocks:
    blk(-12.8, 49.0, 8.4, 65.8)
