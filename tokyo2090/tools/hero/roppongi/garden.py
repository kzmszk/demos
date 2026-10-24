"""Mohri Garden: the Edo-period daimyo garden pond, now a jungle pond: water, shore stones, lily pads, reeds,
cherry trees grown wild and leaning over the water, stone lanterns, Othoniel's 'Kin no Kokoro' heart in the pond."""
import math
import numpy as np
import lib, veg
from lib import norm, vnoise


WATER_Z = 19.5     # the pond lies flat; the terrain's bumps inside it become little islands


def pond_poly():
    O = lib.osm()
    for w in O['water']:
        pl = w['polys'][0]['outer']
        xs = [p[0] for p in pl]
        if 50 < np.mean(xs) < 100:
            return [tuple(p) for p in pl[:-1]] if pl[0] == pl[-1] else [tuple(p) for p in pl]
    raise RuntimeError('pond not found')


def rock(b, c, r, rr, flat=0.6, n=6):
    """low-poly irregular boulder (half-buried)"""
    verts = []; faces = []
    rings = 3
    for i in range(rings + 1):
        th = (math.pi / 2) * i / rings
        for j in range(n):
            ph = 2 * math.pi * j / n + rr.uniform(-0.2, 0.2)
            k = rr.uniform(0.8, 1.2)
            verts.append(np.array(c) + np.array([math.cos(ph) * math.cos(th) * r * k, math.sin(ph) * math.cos(th) * r * k,
                                                 math.sin(th) * r * flat * k - r * 0.25]))
    top = len(verts); verts.append(np.array(c) + np.array([0, 0, r * flat * 0.95]))
    for i in range(rings):
        for j in range(n):
            a = i * n + j; b2 = i * n + (j + 1) % n
            faces.append([a, b2, b2 + n, a + n])
    for j in range(n):
        faces.append([rings * n + j, rings * n + (j + 1) % n, top])
    uv = [(v[0] / 2.0, v[1] / 2.0 + v[2] / 2.0) for v in verts]
    b.mesh(verts, faces, uv)


def build(sc, col, ctx):
    G = ctx['ground']; occ = ctx['occ']
    rr = lib.rng(1652)
    pond = lib.ccw(pond_poly())
    # view corridor from the garden spawn (92, 26) west over the pool towards the tower: no plants in it
    lib.CLEAR.append([(57.0, 23.0), (57.0, 31.0), (70.0, 34.0), (90.0, 36.0), (92.0, 22.0)])
    F = sc['foliage_garden']
    # ---------------- water surface: 1 m grid decal following the terrain + 0.04
    W = sc['decal_water']
    xs = [p[0] for p in pond]; ys = [p[1] for p in pond]
    x0, x1, y0, y1 = math.floor(min(xs)) - 1, math.ceil(max(xs)) + 1, math.floor(min(ys)) - 1, math.ceil(max(ys)) + 1
    X, Y = np.meshgrid(np.arange(x0, x1 + 1, 1.0), np.arange(y0, y1 + 1, 1.0))
    inside = lib.points_in_poly(X + 0.5, Y + 0.5, pond)
    zmin = min(G(p[0], p[1]) for p in pond)
    # the pool: the terrain's low ground connected to the pond, filled to WATER_Z (flood fill on a 0.5 m grid).
    # It is bounded by terrain on every side, so the shoreline is the terrain contour - no polygon edges.
    from collections import deque
    R_ = 0.5
    GX, GY = np.meshgrid(np.arange(20, 140, R_) + R_ / 2, np.arange(-10, 90, R_) + R_ / 2)
    gg = G(GX, GY)
    low = gg < WATER_Z
    seed_ = lib.points_in_poly(GX, GY, pond) & low
    seen = seed_.copy(); dq = deque(zip(*np.nonzero(seed_)))
    while dq:
        j, i = dq.popleft()
        for a, b in ((j + 1, i), (j - 1, i), (j, i + 1), (j, i - 1)):
            if 0 <= a < low.shape[0] and 0 <= b < low.shape[1] and low[a, b] and not seen[a, b]:
                seen[a, b] = True; dq.append((a, b))
    wet = seen.copy()                                    # one cell of margin (it lies under the terrain)
    wet[1:] |= seen[:-1]; wet[:-1] |= seen[1:]; wet[:, 1:] |= seen[:, :-1]; wet[:, :-1] |= seen[:, 1:]
    for j in range(wet.shape[0]):
        i = 0
        while i < wet.shape[1]:
            if not wet[j, i]:
                i += 1; continue
            i1 = i
            while i1 + 1 < wet.shape[1] and wet[j, i1 + 1]:
                i1 += 1
            xa, xb = GX[0, i] - R_ / 2, GX[0, i1] + R_ / 2; ya, yb = GY[j, 0] - R_ / 2, GY[j, 0] + R_ / 2
            W.poly([(xa, ya, WATER_Z), (xb, ya, WATER_Z), (xb, yb, WATER_Z), (xa, yb, WATER_Z)],
                   [(xa / 8, ya / 8), (xb / 8, ya / 8), (xb / 8, yb / 8), (xa / 8, yb / 8)])
            i = i1 + 1
    occ.fill_poly(pond, 4)
    # the terrain's bumps inside the pond: overgrown islands (reeds, shrubs, a stone, now and then a sapling)
    isl = [(X[j, i] + 0.5, Y[j, i] + 0.5) for j in range(X.shape[0]) for i in range(X.shape[1])
           if inside[j, i] and G(X[j, i] + 0.5, Y[j, i] + 0.5) > WATER_Z + 0.7]
    for k, (x, y) in enumerate(isl):
        z = G(x, y)
        r = rr.random()
        if r < 0.35:
            veg.bush(F, (x, y, z - 0.2), rr.uniform(0.8, 1.6), rr)
        elif r < 0.6:
            veg.tuft(F, (x, y, z - 0.1), 'reed', rr.uniform(1.4, 2.4), rr, n=2, ao=0.9)
        elif r < 0.64:
            rock(sc['top'], (x, y, z), rr.uniform(0.5, 1.0), rr)
        elif r < 0.66 and not lib.mid():
            veg.tree(sc, col, (x, y, z), 'young', rr.uniform(3, 6), 2.2, rr.randrange(1 << 30), 'foliage_garden', collide=False)
    # ---------------- a soft dark band where the water meets banks and islands, floating leaf/scum mats
    D = sc['decal_ground']
    from decals import cuv as dcuv
    def flat_decal(x, y, s, name, z):
        a = rr.uniform(0, 2 * math.pi); ca, sa = math.cos(a), math.sin(a)
        q = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        D.poly([(x + (u * ca - v * sa) * s / 2, y + (u * sa + v * ca) * s / 2, z) for u, v in q],
               [dcuv(name, (u + 1) / 2, (v + 1) / 2) for u, v in q])
    for gx in np.arange(x0, x1, 1.5):
        for gy in np.arange(y0, y1, 1.5):
            if not lib.point_in_poly(gx, gy, pond):
                continue
            g = G(gx, gy)
            if WATER_Z + 0.02 < g < WATER_Z + 0.4 and rr.random() < 0.6:
                import decals as _dc
                _dc.decal(D, (gx + rr.uniform(-0.5, 0.5), gy + rr.uniform(-0.5, 0.5)), rr.uniform(2.0, 3.2), rr.uniform(1.6, 2.6),
                          rr.uniform(0, 6.3), 'edge', G)
    for k in range(45 if not lib.mid() else 12):
        for _ in range(12):
            x = rr.uniform(min(xs), max(xs)); y = rr.uniform(min(ys), max(ys))
            if lib.point_in_poly(x, y, pond) and G(x, y) < WATER_Z - 0.1:
                flat_decal(x, y, rr.uniform(1.0, 3.0), 'scum', WATER_Z + 0.02)
                break
    # the game paints its own terrain as water wherever the land-cover raster says so: drape an opaque mossy cover
    # (1 m grid, +0.04 m) over that whole area; our pool (flat at WATER_Z) lies above it where the ground is low
    Cv = sc['decal_cover']
    cov_ = ctx['cover']
    for gx in np.arange(math.floor(x0) - 16, math.ceil(x1) + 16, 1.0):
        for gy in np.arange(math.floor(y0) - 16, math.ceil(y1) + 16, 1.0):
            near_b = any(cov_(gx + dx, gy + dy)[2] > 20 for dx in (-4.5, 0.5, 5.5) for dy in (-4.5, 0.5, 5.5))
            if not near_b:
                continue
            q = [(gx, gy), (gx + 1, gy), (gx + 1, gy + 1), (gx, gy + 1)]
            Cv.poly([(a, b, G(a, b) + 0.04) for a, b in q], [(a / 9.0, b / 9.0) for a, b in q])
    # with moss / mud / leaf litter so only our dark, still water reads as water
    import decals as _dc
    for gx in np.arange(x0 - 12, x1 + 12, 1.6):
        for gy in np.arange(y0 - 12, y1 + 12, 1.6):
            cx_, cy_ = gx + rr.uniform(-0.4, 0.4), gy + rr.uniform(-0.4, 0.4)
            if not (lib.point_in_poly(cx_, cy_, pond) or ctx['cover'](cx_, cy_)[2] > 100):
                continue
            if G(cx_, cy_) < WATER_Z + 0.05:
                continue
            _dc.decal(D, (cx_, cy_), rr.uniform(2.4, 3.2), rr.uniform(2.4, 3.2), rr.uniform(0, 6.3),
                      rr.choice(['moss', 'moss', 'mud', 'litter2']), G)
    # ---------------- shore: stones and reeds all round, lilies on the water
    ring = lib.resample_ring(pond, 1.3)
    ctr = np.array([np.mean(xs), np.mean(ys)])
    keep = 1.0 if not lib.mid() else 0.3
    for k, p in enumerate(ring):
        if rr.random() > keep:
            continue
        nxt = ring[(k + 1) % len(ring)]
        t = norm(nxt - p); out = np.array([t[1], -t[0]])
        q = p + out * rr.uniform(0.0, 0.6)
        z = G(q[0], q[1])
        if rr.random() < 0.45:
            rock(sc['top'], (q[0], q[1], z), rr.uniform(0.35, 0.9), rr)
        if rr.random() < 0.3 and np.hypot(p[0] - 55.5, p[1] - 27.0) > 14:
            r2 = p - out * rr.uniform(0.2, 1.5)
            for m in range(rr.randrange(2, 5)):
                s = r2 + np.array([rr.uniform(-0.6, 0.6), rr.uniform(-0.6, 0.6)])
                veg.tuft(F, (s[0], s[1], G(s[0], s[1]) - 0.1), 'reed', rr.uniform(1.4, 2.4), rr, n=2, ao=0.9)
    for k in range(70 if not lib.mid() else 20):
        for _ in range(10):
            x = rr.uniform(min(xs), max(xs)); y = rr.uniform(min(ys), max(ys))
            if lib.point_in_poly(x, y, pond):
                if G(x, y) > WATER_Z - 0.05:
                    continue
                z = WATER_Z + 0.03
                s = rr.uniform(1.2, 3.0)
                a = rr.uniform(0, math.pi)
                t1 = np.array([math.cos(a), math.sin(a), 0]); t2 = np.array([-math.sin(a), math.cos(a), 0])
                veg.card(F, np.array([x, y, z]), t1, t2, s, 'lily', np.array([0, 0, 1.0]), 0.95)
                break
    # ---------------- Kin no Kokoro (Othoniel 2014): a heart of big gold beads standing in the water
    hx, hy = 58.4, 37.7
    hz = G(hx, hy)
    beads = []
    for i in range(30):
        t = 2 * math.pi * i / 30
        x = 16 * math.sin(t) ** 3; z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        beads.append(np.array([hx + x * 0.09 * 0.6, hy + x * 0.09 * 0.8, hz + 2.1 + z * 0.09]))
    for c in beads[::(1 if not lib.mid() else 2)]:
        _bead(sc['signs'], c, 0.2 if not lib.mid() else 0.28)
    lib.tube(sc['metal'], [np.array([hx, hy, hz - 0.2]), np.array([hx, hy, hz + 0.85])], [0.06, 0.06], sides=4)
    # ---------------- stone lanterns and the guardian stone
    for (lx, ly) in ((47.0, 58.0), (86.0, 60.0), (100.0, 40.0), (66.0, 24.0)):
        z = G(lx, ly)
        _lantern(sc['conc'], (lx, ly, z), rr)
        col.box((lx, ly, z), (0.9, 0.9, 2.2))
        occ.fill_circle(lx, ly, 1.0, 5)
    rock(sc['top'], (111.3, 46.5, G(111.3, 46.5)), 1.4, rr, flat=1.1, n=7)
    col.box((111.3, 46.5, G(111.3, 46.5)), (2.2, 2.2, 1.4))
    # ---------------- trees: cherries around the pond (wild, leaning over the water) + big broadleaf behind
    cherries = [(46, 53), (53, 26), (62, 60), (72, 63), (80, 30), (90, 36), (100, 52), (98, 60), (70, 18), (44, 34),
                (108, 30), (84, 64), (115, 58), (40, 62)]
    for k, (x, y) in enumerate(cherries):
        x += rr.uniform(-2, 2); y += rr.uniform(-2, 2)
        if occ.get(x, y) not in (0,):
            continue
        h = rr.uniform(9, 13); R = rr.uniform(6, 8.5)
        lean = 0.15 if np.linalg.norm(np.array([x, y]) - ctr) < 25 else 0.0
        veg.tree(sc, col, (x, y, G(x, y)), 'cherry', h, R, 5000 + k, 'foliage_garden', lean=lean)
        occ.fill_circle(x, y, 3.0, 9)
    # the wooded island between the two lobes of the pond
    for k, (x, y) in enumerate(((81.0, 41.0), (77.0, 37.5), (87.5, 47.0), (70.5, 36.0))):
        veg.tree(sc, col, (x, y, G(x, y)), 'cherry', rr.uniform(8, 11), rr.uniform(5.5, 7.5), 5200 + k, 'foliage_garden', lean=0.12)
    for k, (x, y) in enumerate(((122, 70), (128, 48), (36, 72), (118, 28), (60, 76), (95, 74))):
        if occ.get(x, y) not in (0,):
            continue
        h = rr.uniform(15, 21)
        veg.tree(sc, col, (x, y, G(x, y)), rr.choice(['broad', 'zelkova']), h, h * 0.45, 5100 + k, 'foliage_garden')
        occ.fill_circle(x, y, 4.0, 9)
    # shrubs / azalea mounds (the garden's clipped azaleas, now big loose mounds)
    for k in range(60 if not lib.mid() else 15):
        x = rr.uniform(36, 130); y = rr.uniform(18, 80)
        if occ.get(x, y) != 0 or ctx['cover'](x, y)[1] < 100:
            continue
        veg.bush(F, (x, y, G(x, y)), rr.uniform(0.8, 2.0), rr)
    ctx['labels'].append({'name': '毛利庭園', 'x': 76.0, 'y': 44.0, 'z': 30.0, 'kind': 'place'})
    ctx['labels'].append({'name': 'テレビ朝日', 'x': 110.0, 'y': -30.0, 'z': 60.0, 'kind': 'building'})


def _bead(b, c, r):
    n = 4 if not lib.mid() else 3
    verts = []; uvs = []
    for i in range(n + 1):
        th = math.pi * i / n
        for j in range(n * 2 + 1):
            ph = 2 * math.pi * j / (n * 2)
            verts.append(c + r * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)]))
            uvs.append((0.512 + 0.045 * j / (n * 2), 0.135 + 0.1 * i / n))     # the faded gold of a sign panel
    faces = []
    w = n * 2 + 1
    for i in range(n):
        for j in range(n * 2):
            a = i * w + j
            faces.append([a, a + w, a + w + 1, a + 1])
    b.mesh(verts, faces, uvs)


def _lantern(b, p, rr):
    x, y, z = p
    rot = rr.uniform(0, 1.5)
    lib.box(b, (x, y, z), (0.9, 0.9, 0.3), rot, 0.5)
    lib.box(b, (x, y, z + 0.3), (0.35, 0.35, 0.9), rot, 0.5)
    lib.box(b, (x, y, z + 1.2), (0.75, 0.75, 0.25), rot, 0.5)
    lib.box(b, (x, y, z + 1.45), (0.55, 0.55, 0.45), rot, 0.5)
    lib.box(b, (x, y, z + 1.9), (1.0, 1.0, 0.18), rot, 0.5)
    lib.box(b, (x, y, z + 2.08), (0.5, 0.5, 0.2), rot, 0.5)
