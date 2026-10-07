"""Tree templates (procedural): a branching skeleton grown inside a species crown envelope, bark tubes, and leaf cards
from the leaf atlas (gen/leafatlas.py) at the twigs.  Two levels of detail per variant.

Wood vertex data:  P, N, UV (u around in metres, v along in metres), W (wind weight 0 trunk .. 1 twig)
Leaf vertex data:  P, N (spherised: away from the crown centre, blended with the card normal), UV (atlas), W (wind),
                   K (x = outerness 0..1, y = per-card random, z = height in crown 0..1, w = cell)"""
import math
import numpy as np

ATLAS_N = 4
# species: crown shape, size, branching, cards
SPECIES = {
    'momiji':   dict(H=(5.0, 8.0), crown='dome', R=0.62, zc=0.58, zr=0.42, zs=0.18, n1=(5, 7), el1=(25, 55), lvl=3, card=(0.65, 0.95), cells=(0,), ncards=750, r0=0.0136, deciduous=1),
    'ichou':    dict(H=(11.0, 17.0), crown='oval', R=0.28, zc=0.55, zr=0.48, zs=0.12, n1=(10, 14), el1=(40, 62), lvl=3, card=(0.9, 1.3), cells=(2,), ncards=950, r0=0.0155, deciduous=1),
    'sakura':   dict(H=(6.0, 9.5), crown='spread', R=0.7, zc=0.62, zr=0.34, zs=0.22, n1=(4, 6), el1=(15, 40), lvl=3, card=(0.8, 1.15), cells=(3,), ncards=650, r0=0.0186, deciduous=1),
    'keyaki':   dict(H=(13.0, 19.0), crown='vase', R=0.46, zc=0.62, zr=0.4, zs=0.2, n1=(6, 9), el1=(55, 75), lvl=3, card=(1.0, 1.5), cells=(13,), ncards=1000, r0=0.0174, deciduous=1),
    'matsu':    dict(H=(5.0, 10.0), crown='pads', R=0.45, zc=0.65, zr=0.35, zs=0.35, n1=(5, 8), el1=(-5, 25), lvl=2, card=(0.7, 1.1), cells=(4,), ncards=420, r0=0.0186, deciduous=0),
    'sugi':     dict(H=(18.0, 28.0), crown='cone', R=0.17, zc=0.6, zr=0.45, zs=0.3, n1=(22, 30), el1=(-15, 15), lvl=2, card=(1.1, 1.6), cells=(5,), ncards=800, r0=0.0136, deciduous=0),
    'hinoki':   dict(H=(14.0, 22.0), crown='cone', R=0.22, zc=0.6, zr=0.45, zs=0.25, n1=(18, 26), el1=(-10, 20), lvl=2, card=(1.0, 1.5), cells=(6,), ncards=700, r0=0.0136, deciduous=0),
    'kashi':    dict(H=(8.0, 14.0), crown='round', R=0.48, zc=0.62, zr=0.4, zs=0.2, n1=(6, 9), el1=(30, 60), lvl=3, card=(1.0, 1.5), cells=(1,), ncards=1000, r0=0.0174, deciduous=0),
    'yanagi':   dict(H=(7.0, 10.0), crown='weep', R=0.5, zc=0.6, zr=0.42, zs=0.3, n1=(6, 8), el1=(30, 60), lvl=2, card=(1.1, 1.6), cells=(7,), ncards=420, r0=0.0186, deciduous=1),
    'tsutsuji': dict(H=(0.8, 1.4), crown='mound', R=0.9, zc=0.5, zr=0.5, zs=0.0, n1=(5, 7), el1=(30, 70), lvl=2, card=(0.35, 0.5), cells=(10,), ncards=110, r0=0.0074, deciduous=0),
    'take':     dict(H=(9.0, 14.0), crown='bamboo', R=0.18, zc=0.75, zr=0.25, zs=0.55, n1=(1, 1), el1=(85, 89), lvl=1, card=(0.7, 1.0), cells=(8,), ncards=120, r0=0.0310, deciduous=0),
}
NAMES = list(SPECIES)

def envelope(sp, H, z):
    """crown radius at height z (m)"""
    c = sp['crown']; R = sp['R'] * H; zc = sp['zc'] * H; zr = sp['zr'] * H; zs = sp['zs'] * H
    if z < zs * 0.9: return 0.0
    if c in ('dome', 'round', 'spread', 'mound', 'weep'):
        t = (z - zc) / max(zr, 1e-3)
        if abs(t) >= 1: return 0.0
        r = R * math.sqrt(1 - t * t)
        if c == 'dome' and t > 0.4: r *= 1 - (t - 0.4) * 0.6         # flatter top
        if c == 'spread' and t > 0.2: r *= 1 - (t - 0.2) * 0.5
        return r
    if c == 'oval':
        t = (z - zs) / max(H - zs, 1e-3)
        return R * (math.sin(math.pi * min(max(t, 0), 1)) ** 0.75) * (1.15 - 0.3 * t)
    if c == 'vase':
        t = (z - zs) / max(H - zs, 1e-3)
        if t >= 1: return 0.0
        return R * (min(1.0, t * 1.4) ** 0.7) * (1 - max(0, t - 0.8) / 0.2 * 0.7)
    if c == 'cone':
        t = (z - zs) / max(H - zs, 1e-3)
        if t >= 1 or t < 0: return 0.0
        return R * H * 0 + sp['R'] * H * (1 - t) ** 1.05 + 0.25
    if c == 'pads':
        t = (z - zs) / max(H - zs, 1e-3)
        if t >= 1 or t < 0: return 0.0
        return R * (0.6 + 0.4 * math.sin(t * math.pi)) * (1 - t * 0.5)
    if c == 'bamboo':
        t = (z - zs) / max(H - zs, 1e-3)
        if t >= 1 or t < 0: return 0.0
        return R * math.sin(math.pi * t)
    return 0.0

class Tube:
    def __init__(self):
        self.P = []; self.N = []; self.UV = []; self.W = []; self.I = []
    def add(self, pts, radii, sides, wind):
        """a tube along pts (k,3) with radii (k,)"""
        pts = np.asarray(pts, float); k = len(pts)
        if k < 2: return
        base = len(self.P)
        # parallel-transport frames
        T = np.gradient(pts, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        up = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.95 else np.array([1.0, 0, 0])
        Nn = np.cross(T[0], up); Nn /= np.linalg.norm(Nn)
        acc = 0.0
        for i in range(k):
            if i > 0:
                acc += np.linalg.norm(pts[i] - pts[i - 1])
                v = np.cross(T[i - 1], T[i]); s = np.linalg.norm(v)
                if s > 1e-6:
                    v /= s; ang = math.asin(min(1.0, s))
                    Nn = Nn * math.cos(ang) + np.cross(v, Nn) * math.sin(ang) + v * (v @ Nn) * (1 - math.cos(ang))
                Nn -= T[i] * (Nn @ T[i]); Nn /= max(np.linalg.norm(Nn), 1e-9)
            B = np.cross(T[i], Nn)
            for j in range(sides + 1):
                a = 2 * math.pi * j / sides
                d = Nn * math.cos(a) + B * math.sin(a)
                self.P.append(pts[i] + d * radii[i]); self.N.append(d); self.UV.append((a * radii[i] * 1.0 + 0.0, acc)); self.W.append(wind[i])
        for i in range(k - 1):
            for j in range(sides):
                a = base + i * (sides + 1) + j; b = a + 1; c = a + sides + 1; d = c + 1
                self.I += [(a, b, c), (b, d, c)]          # outward (CCW seen from outside)
    def arrays(self):
        return dict(P=np.array(self.P, np.float32), N=np.array(self.N, np.float32), UV=np.array(self.UV, np.float32), W=np.array(self.W, np.float32), I=np.array(self.I, np.uint32))

def make(species, seed, lod=0):
    sp = SPECIES[species]; r = np.random.default_rng(seed)
    H = r.uniform(*sp['H'])
    tube = Tube()
    cards = []                                   # (centre, up, normal, size, cell, depth)
    sides = (7, 5, 4, 3) if lod == 0 else (5, 4, 3, 3)
    crown_c = np.array([0, 0, sp['zc'] * H])
    # ---- trunk
    zs = sp['zs'] * H
    lean = r.normal(0, 0.03, 2)
    nseg = 10
    if sp['crown'] == 'bamboo':
        # a clump of culms: several thin straight stems, each with leaf fans near the top
        for c in range(r.integers(5, 9)):
            off = r.normal(0, 0.35, 2); h = H * r.uniform(0.75, 1.0); bend = r.normal(0, 0.06, 2)
            pts = [np.array([off[0] + bend[0] * (t ** 2) * h, off[1] + bend[1] * (t ** 2) * h, t * h]) for t in np.linspace(0, 1, 8)]
            tube.add(pts, np.linspace(0.045, 0.02, 8), 5 if lod == 0 else 3, np.linspace(0, 1, 8))
            for t in np.linspace(0.5, 1.0, 7 if lod == 0 else 3):
                p = pts[0] + (pts[-1] - pts[0]) * t
                for k in range(2):
                    a = r.uniform(0, 2 * math.pi); d = np.array([math.cos(a), math.sin(a), 0.3]); d /= np.linalg.norm(d)
                    cards.append((p + d * 0.35, d * 0.5 + np.array([0, 0, 0.5]), np.array([-d[1], d[0], 0.0]), r.uniform(*sp['card']), sp['cells'][0], 2))
        return finish(sp, tube, cards, H, crown_c, r, lod)
    if sp['crown'] == 'mound':
        trunk_top = np.array([0, 0, 0.1])
    else:
        top = H * (0.97 if sp['crown'] in ('cone', 'oval') else max(0.45, sp['zs'] + 0.25))
        pts = [np.array([lean[0] * t * H + r.normal(0, 0.02 * H) * (0 < t < 1) * 0.3, lean[1] * t * H, t * top]) for t in np.linspace(0, 1, nseg)]
        rad = [sp['r0'] * H * (1.0 - 0.75 * t) * (1.25 if t < 0.05 else 1.0) for t in np.linspace(0, 1, nseg)]
        tube.add(pts, rad, sides[0], np.linspace(0, 0.3, nseg))
        trunk_top = pts[-1]
        trunk = (pts, rad)
    # ---- main branches inside the envelope
    n1 = r.integers(sp['n1'][0], sp['n1'][1] + 1)
    if sp['crown'] in ('cone',):
        n1 = int(n1 * (1.0 if lod == 0 else 0.6))
    ga = r.uniform(0, 2 * math.pi)
    def branch(p0, d, length, depth, rad0):
        k = max(3, int(length / (0.6 if depth == 1 else 0.4)) + 1)
        pts = [p0]; dd = d.copy()
        for i in range(1, k):
            # curve: gravitropism per species (droop for conifers/weeping, up for vase)
            g = {'cone': -0.06, 'weep': -0.18, 'pads': -0.03, 'vase': 0.05, 'oval': 0.03}.get(sp['crown'], 0.0)
            dd = dd + np.array([0, 0, g]) + r.normal(0, 0.08, 3); dd /= np.linalg.norm(dd)
            pts.append(pts[-1] + dd * length / (k - 1))
        rad = np.linspace(rad0, rad0 * 0.25, k)
        if depth <= (2 if lod == 0 else 1) or sp['crown'] in ('cone',):
            tube.add(pts, rad, sides[min(depth, 3)], np.linspace(0.3 + 0.2 * depth, 0.5 + 0.25 * depth, k))
        # children
        if depth < sp['lvl']:
            nc = r.integers(2, 5) if depth == 1 else r.integers(2, 4)
            for c in range(nc):
                t = r.uniform(0.35, 0.95)
                i = min(k - 2, int(t * (k - 1))); p = pts[i] + (pts[i + 1] - pts[i]) * (t * (k - 1) - i)
                side = np.cross(dd, [0, 0, 1.0]); side = side / max(np.linalg.norm(side), 1e-6) if np.linalg.norm(side) > 1e-6 else np.array([1.0, 0, 0])
                a = r.uniform(-1, 1) * 1.2
                nd = dd * math.cos(0.7) + (side * math.cos(a) + np.cross(side, dd) * math.sin(a)) * math.sin(0.7)
                nd /= np.linalg.norm(nd)
                L2 = min(length * r.uniform(0.4, 0.65), room(p, nd) * 0.9)
                if L2 > 0.25: branch(p, nd, L2, depth + 1, rad0 * 0.55)
        # leaves at the outer part of the last branches
        if depth >= sp['lvl'] - 1:
            nl = max(1, int(length / 0.45))
            for i in range(nl):
                t = r.uniform(0.35, 1.0)
                j = min(k - 2, int(t * (k - 1))); p = pts[j] + (pts[j + 1] - pts[j]) * (t * (k - 1) - j)
                cards.append((p, dd.copy(), None, r.uniform(*sp['card']), sp['cells'][r.integers(len(sp['cells']))], depth))
    def room(p, d):
        """distance from p along d to the crown envelope"""
        s = 0.0
        for _ in range(60):
            s += 0.25; q = p + d * s
            if math.hypot(q[0], q[1]) > envelope(sp, H, q[2]) + 0.15 or q[2] > H or q[2] < 0.2: return s
        return s
    if sp['crown'] == 'mound':
        for b in range(n1):
            a = ga + b * 2.39996; el = math.radians(r.uniform(*sp['el1']))
            d = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)])
            branch(trunk_top, d, max(0.3, room(trunk_top, d)), 1, 0.015)
    else:
        pts, rad = trunk
        top = pts[-1][2]
        for b in range(n1):
            if sp['crown'] in ('cone', 'pads'):
                t = (b + 0.5) / n1
                z = zs + (top * 0.98 - zs) * t
            else:
                z = zs + (top - zs) * r.uniform(0.0, 0.85) ** 0.8
            i = min(nseg - 2, int(z / top * (nseg - 1))); p = pts[i] + (pts[i + 1] - pts[i]) * (z / top * (nseg - 1) - i)
            a = ga + b * 2.39996 + r.normal(0, 0.25); el = math.radians(r.uniform(*sp['el1']))
            d = np.array([math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el)])
            L = room(p, d)
            if sp['crown'] == 'weep': L = max(L, 1.5)
            if L > 0.4: branch(p, d, L, 1, rad[i] * 0.6)
        # a leader top tuft for conifers / ginkgo
        if sp['crown'] in ('cone', 'oval'):
            for k in range(6):
                cards.append((pts[-1] + np.array([r.normal(0, 0.3), r.normal(0, 0.3), -k * 0.3]), np.array([0, 0, 1.0]), None, r.uniform(*sp['card']), sp['cells'][0], 3))
    return finish(sp, tube, cards, H, crown_c, r, lod)

def finish(sp, tube, cards, H, crown_c, r, lod):
    want = sp['ncards'] if lod == 0 else max(12, sp['ncards'] // 5)
    # twig cards keep the branch structure readable; the rest fill the crown's outer shell (a full silhouette)
    ntw = min(len(cards), int(want * 0.35))
    if len(cards) > ntw:
        idx = r.choice(len(cards), ntw, replace=False); cards = [cards[i] for i in idx]
    if sp['crown'] not in ('bamboo',):
        zs = sp['zs'] * H
        tips = np.array([c[0] for c in cards]) if cards else np.zeros((0, 3))
        tries = 0
        while len(cards) < want and tries < want * 30:
            tries += 1
            z = r.uniform(zs, H)
            R = envelope(sp, H, z)
            if R < 0.2: continue
            if sp['crown'] == 'pads' and len(tips):
                # pine: flat pads around the branch ends
                c0 = tips[r.integers(len(tips))]
                p = c0 + np.array([r.normal(0, 0.55), r.normal(0, 0.55), r.normal(0, 0.12)])
                cards.append((p, np.array([0, 0, 1.0]), None, r.uniform(*sp['card']), sp['cells'][0], 3)); continue
            a = r.uniform(0, 2 * math.pi); rr = R * r.uniform(0.55, 1.0) ** 0.5
            p = np.array([math.cos(a) * rr, math.sin(a) * rr, z])
            d = np.array([math.cos(a), math.sin(a), 0.6]); d /= np.linalg.norm(d)
            cards.append((p, d, None, r.uniform(*sp['card']), sp['cells'][r.integers(len(sp['cells']))], 3))
    scale = 1.0 if lod == 0 else 1.7
    P = []; N = []; UV = []; W = []; K = []; I = []
    rmax = max(1e-3, max((math.hypot(c[0][0], c[0][1]) for c in cards), default=1.0))
    for (p, d, nrm, size, cell, depth) in cards:
        size *= scale
        out = p - crown_c; ol = np.linalg.norm(out); out = out / ol if ol > 1e-6 else np.array([0, 0, 1.0])
        if sp['crown'] == 'weep':
            up = np.array([0, 0, -1.0]); n = out.copy(); n[2] = 0; n /= max(np.linalg.norm(n), 1e-6)
        else:
            up = d * 0.6 + out * 0.4 + np.array([0, 0, 0.2]); up /= np.linalg.norm(up)
            n = out - up * (out @ up)
            n = n / np.linalg.norm(n) if np.linalg.norm(n) > 1e-3 else np.cross(up, [1.0, 0, 0])
            n = n + r.normal(0, 0.35, 3); n -= up * (n @ up); n /= max(np.linalg.norm(n), 1e-6)
        side = np.cross(up, n)
        # the atlas cluster grows from the bottom centre of its cell: put that point at the twig
        base = p - up * size * 0.05
        q = [base - side * size / 2, base + side * size / 2, base + side * size / 2 + up * size, base - side * size / 2 + up * size]
        if sp['crown'] == 'weep':      # hanging strands: the top of the cell at the twig
            q = [p - side * size / 2 + up * size, p + side * size / 2 + up * size, p + side * size / 2, p - side * size / 2]
        cu, cv = cell % ATLAS_N, cell // ATLAS_N
        uvs = [(cu + 0.02, cv + 0.98), (cu + 0.98, cv + 0.98), (cu + 0.98, cv + 0.02), (cu + 0.02, cv + 0.02)]
        uvs = [(u / ATLAS_N, v / ATLAS_N) for (u, v) in uvs]
        sph = np.array(out)
        nn = n * 0.45 + sph * 0.55; nn /= np.linalg.norm(nn)
        b0 = len(P)
        hz = min(1.0, max(0.0, (p[2] - sp['zs'] * H) / max(H * (1 - sp['zs']), 1e-3)))
        rnd = r.random()
        outer = min(1.0, ol / max(rmax, 1e-3))
        for k in range(4):
            P.append(q[k]); N.append(nn); UV.append(uvs[k]); W.append(0.7 + 0.3 * min(1.0, depth / 3)); K.append((outer, rnd, hz, cell))
        I += [(b0, b0 + 1, b0 + 2), (b0, b0 + 2, b0 + 3)]
    leaves = dict(P=np.array(P, np.float32).reshape(-1, 3), N=np.array(N, np.float32).reshape(-1, 3), UV=np.array(UV, np.float32).reshape(-1, 2),
                  W=np.array(W, np.float32), K=np.array(K, np.float32).reshape(-1, 4), I=np.array(I, np.uint32).reshape(-1, 3))
    return dict(H=H, wood=tube.arrays(), leaves=leaves)

if __name__ == '__main__':
    import sys
    for n in NAMES:
        t = make(n, 1)
        print(n, round(t['H'], 1), 'wood', len(t['wood']['I']), 'tris; leaves', len(t['leaves']['I']), 'tris')
