"""Ground decals (decal_ mesh, +0.04 m over ground.obj, subdivided <= 1 m): leaf litter, cracks with grass,
puddles, moss at wall feet, worn zebra crossings; and on the decks (flat).  Plus tufts on the decks (the game only
sows its small plants on its own terrain)."""
import math
import numpy as np
import lib, veg
from lib import norm

CELLS = {'litter': (0, 0), 'litter2': (1, 0), 'crack': (2, 0), 'puddle': (3, 0),
         'gravel': (0, 1), 'moss': (1, 1), 'zebra': (2, 1), 'lane': (3, 1),
         'roots': (0, 2), 'stain': (1, 2), 'petals': (2, 2), 'mud': (3, 2),
         'streak': (0, 3), 'scum': (1, 3), 'edge': (2, 3)}


def cuv(name, u, v):
    cx, cy = CELLS[name]
    return ((cx + 0.01 + 0.98 * u) / 4, 1 - (cy + 0.01 + 0.98 * (1 - v)) / 4)


def decal(D, c, sx, sy, rot, name, zf, flat=False, lift=0.04):
    ca, sa = math.cos(rot), math.sin(rot)
    nx = 1 if flat else max(1, int(math.ceil(sx / 1.0)))
    ny = 1 if flat else max(1, int(math.ceil(sy / 1.0)))
    def P(i, j):
        u, v = i / nx, j / ny
        lx, ly = (u - 0.5) * sx, (v - 0.5) * sy
        x = c[0] + lx * ca - ly * sa; y = c[1] + lx * sa + ly * ca
        return (x, y, zf(x, y) + lift), cuv(name, u, v)
    for j in range(ny):
        for i in range(nx):
            q = [P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)]
            D.poly([a for a, _ in q], [b for _, b in q])


def build(sc, col, ctx):
    G = ctx['ground']; occ = ctx['occ']; cov = ctx['cover']
    rr = lib.rng(4040)
    D = sc['decal_ground']
    gz = lambda x, y: G(x, y)
    n = 0
    for it in range(800 if not lib.mid() else 200):
        x = rr.uniform(lib.BOX[0], lib.BOX[2]); y = rr.uniform(lib.BOX[1], lib.BOX[3])
        o = occ.get(x, y)
        if o in (1, 2, 3, 4):
            continue
        c = cov(x, y)
        road = c[0] > 200
        r = rr.random()
        if road:
            name = 'crack' if r < 0.3 else ('puddle' if r < 0.36 else ('litter' if r < 0.75 else ('mud' if r < 0.85 else 'gravel')))
        else:
            name = 'litter' if r < 0.45 else ('litter2' if r < 0.7 else ('moss' if r < 0.85 else ('roots' if r < 0.93 else 'petals')))
        s = rr.uniform(2.5, 6.0)
        decal(D, (x, y), s, s * rr.uniform(0.6, 1.0), rr.uniform(0, 6.28), name, gz)
        n += 1
    # moss + stain at wall feet
    for (poly, ztop, zbase, bid) in ctx.get('walls', [])[:]:
        if ztop(poly[0][0], poly[0][1]) > 200:
            continue
        m = len(poly)
        for i in range(m):
            a = np.array(poly[i]); b = np.array(poly[(i + 1) % m]); L = float(np.linalg.norm(b - a))
            if L < 4 or rr.random() < (0.5 if not lib.mid() else 0.9):
                continue
            u = (b - a) / L; out = np.array([u[1], -u[0]])
            q = a + u * rr.uniform(0, L) + out * 1.0
            if occ.get(q[0], q[1]) in (1, 2):
                continue
            if abs(G(q[0], q[1]) - zbase) > 2.0:
                continue
            decal(D, q, rr.uniform(3, 6), 2.0, math.atan2(u[1], u[0]), rr.choice(['moss', 'moss', 'litter2']), gz)
    # weathering streaks running down the taller ruins from their tops
    for (poly, ztop, zbase, bid) in ctx.get('walls', []):
        m = len(poly)
        for i in range(m):
            a = np.array(poly[i]); b = np.array(poly[(i + 1) % m]); L = float(np.linalg.norm(b - a))
            if L < 4:
                continue
            u = (b - a) / L; out = np.array([u[1], -u[0]])
            k = rr.uniform(0, 6)
            while k < L - 2:
                w = rr.uniform(1.5, 5.0)
                p0 = a + u * k + out * 0.06; p1 = p0 + u * min(w, L - k)
                zt = min(ztop(p0[0], p0[1]), ztop(p1[0], p1[1])) - rr.uniform(0, 3)
                h = zt - zbase
                if h > 14 and rr.random() < (0.45 if not lib.mid() else 0.15):
                    Ls = min(h - 1, rr.uniform(8, 40))
                    D.poly([(p0[0], p0[1], zt - Ls), (p1[0], p1[1], zt - Ls), (p1[0], p1[1], zt), (p0[0], p0[1], zt)],
                           [cuv('streak', 0, 0), cuv('streak', 1, 0), cuv('streak', 1, 1), cuv('streak', 0, 1)])
                k += rr.uniform(4, 12)
    # zebra crossings
    for (c, d, L) in ctx.get('crossings', []):
        d = norm(np.array(d)); t = np.array([-d[1], d[0]])
        for k in range(int(L / 0.9)):
            p = np.array(c) + t * (k * 0.9 - L / 2)
            decal(D, p, 0.45, 3.2, math.atan2(d[1], d[0]) - math.pi / 2, 'zebra', gz)
    # Keyakizaka lane line (worn, dashed)
    line = ctx.get('keyaki_line', [])
    for i in range(len(line) - 1):
        a = np.array(line[i]); b = np.array(line[i + 1]); L = float(np.linalg.norm(b - a)); u = (b - a) / L
        k = 0.0
        while k < L:
            p = a + u * (k + 2.5)
            if lib.BOX[0] < p[0] < lib.BOX[2]:
                decal(D, p, 0.15, 5.0, math.atan2(u[1], u[0]) - math.pi / 2, 'lane', gz)
            k += 10.0
    # decks: litter, moss, cracks, and plants growing in the joints
    Dd = D
    deck = ctx.get('plaza_deck')
    PZ = lib.PLAZA_Z
    F = sc['foliage_plaza']
    if deck:
        xs = [p[0] for p in deck]; ys = [p[1] for p in deck]
        for it in range(1400 if not lib.mid() else 120):
            x = rr.uniform(min(xs), max(xs)); y = rr.uniform(min(ys), max(ys))
            if not lib.point_in_poly(x, y, deck) or occ.get(x, y) == 1:
                continue
            # skip inside the tower
            tc = ctx['tower_center']
            if math.hypot(x - tc[0], y - tc[1]) < ctx['tower_R'](math.atan2(y - tc[1], x - tc[0])) + 2:
                continue
            r = rr.random()
            if r < 0.55:
                name = rr.choice(['litter', 'litter2', 'moss', 'moss', 'roots', 'gravel', 'petals'])
                s = rr.uniform(2.5, 7)
                decal(Dd, (x, y), s, s * rr.uniform(0.6, 1), rr.uniform(0, 6.3), name, lambda a, b: PZ, flat=True)
            elif r < 0.85:
                veg.tuft(F, (x, y, PZ), rr.choice(['grass', 'grass', 'fern']), rr.uniform(0.5, 1.1), rr, n=2)
            else:
                veg.bush(F, (x, y, PZ), rr.uniform(0.5, 1.3), rr)
    ctx['n_decals'] = n
