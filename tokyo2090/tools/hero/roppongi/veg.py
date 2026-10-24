"""Vegetation: trees (zelkova / cherry / broadleaf / fig), vine curtains, roof growth, strangler roots, tufts.
Placement: the general scatter over the box (street trees along OSM roads, wild trees in lots), vines and growth
on every ruin (ctx['walls'], ctx['tops']), the tower tear anchors.  Garden and Keyakizaka call tree() directly."""
import math, json
import numpy as np
import lib
from lib import vnoise, norm

CELLS = {'zelkova': (0, 0, 1, 1), 'zelkova2': (1, 0, 1, 1), 'cherry': (2, 0, 1, 1), 'fig': (3, 0, 1, 1),
         'jungle': (0, 1, 1, 1), 'fern': (1, 1, 1, 1), 'reed': (2, 1, 1, 1), 'lily': (3, 1, 1, 1),
         'vine': (0, 2, 1, 2), 'vine2': (1, 2, 1, 2), 'ivy': (2, 2, 1, 1), 'grass': (3, 2, 1, 1),
         'shrub': (2, 3, 1, 1), 'bamboo': (3, 3, 1, 1)}


def cuv(name):
    cx, cy, w, h = CELLS[name]
    u0 = cx / 4 + 0.003; u1 = (cx + w) / 4 - 0.003
    v1 = 1 - cy / 4 - 0.003; v0 = 1 - (cy + h) / 4 + 0.003
    return u0, v0, u1, v1


def card(F, p, t1, t2, size, kind, nrm, ao=1.0, aspect=1.0):
    """quad centred at p spanned by unit vectors t1 (width) and t2 (height)"""
    u0, v0, u1, v1 = cuv(kind)
    hw = size / 2; hh = size * aspect / 2
    q = [p - t1 * hw - t2 * hh, p + t1 * hw - t2 * hh, p + t1 * hw + t2 * hh, p - t1 * hw + t2 * hh]
    c = (ao, ao, ao, 1.0)
    F.poly(q, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normals=[nrm] * 4, colors=[c] * 4)


def hang(F, top, out, width, length, kind='vine', ao=0.9, seed=0, sway=0.0):
    """vertical curtain hanging from `top` (3d), `out` = horizontal outward unit normal of the wall"""
    out = np.array([out[0], out[1], 0.0]); out = norm(out)
    t1 = np.array([-out[1], out[0], 0.0])
    u0, v0, u1, v1 = cuv(kind)
    seg = max(1, int(length / 7.0))
    rr = lib.rng(seed)
    z = top[2]
    p = np.array(top, float) + out * 0.25
    remaining = length
    while remaining > 0.5:
        L = min(remaining, rr.uniform(5.0, 8.0))
        a = p; b = p + np.array([0, 0, -L]) + out * rr.uniform(0.0, 0.5)
        q = [b - t1 * width / 2, b + t1 * width / 2, a + t1 * width / 2, a - t1 * width / 2]
        # the strip texture is 1:2; use the part matching the aspect
        frac = min(1.0, L / (width * 2.0))
        vv0 = v1 - (v1 - v0) * frac
        n = norm(out + np.array([0, 0, 0.25]))
        F.poly(q, [(u0, vv0), (u1, vv0), (u1, v1), (u0, v1)], normals=[n] * 4,
               colors=[(ao * 0.8,) * 3 + (1,)] * 2 + [(ao,) * 3 + (1,)] * 2)
        p = b + np.array([0, 0, 0.6])
        remaining -= max(L - 0.6, 0.6)
        width *= rr.uniform(0.7, 1.0)


CROWNS = []    # (x, y, z, R, Rz) of every tree crown (far LOD blobs)

SPECIES = {
    #          trunk_frac limbs  limb_ang(deg from vertical) crown_c  flat  leaf kinds         card
    'zelkova': (0.22, 6, (28, 48), 0.66, 0.62, ('zelkova', 'zelkova2'), 2.6),
    'cherry':  (0.26, 5, (50, 72), 0.62, 0.55, ('cherry',), 2.4),
    'broad':   (0.36, 4, (25, 45), 0.66, 0.85, ('jungle', 'shrub'), 2.6),
    'fig':     (0.30, 5, (35, 60), 0.68, 0.75, ('fig', 'jungle'), 2.8),
    'young':   (0.45, 3, (20, 40), 0.70, 0.9, ('shrub', 'zelkova2'), 1.6),
}


def tree(sc, col, p, kind, h, R, seed, zone='foliage_trees', density=1.0, collide=True, lean=0.0):
    if lib.cleared(p[0], p[1]):
        return None
    rr = lib.rng(seed)
    if lib.mid():
        density *= 0.33
    tf, nl, la, cc, flat, kinds, csize = SPECIES[kind]
    p = np.array(p, float)
    Bk = sc['bark']; F = sc[zone]
    r0 = max(0.07, 0.019 * h * (1.15 if kind in ('zelkova', 'cherry') else 1.0))
    lean_dir = rr.uniform(0, 2 * math.pi)
    lv = np.array([math.cos(lean_dir), math.sin(lean_dir), 0]) * (lean + rr.uniform(0, 0.08))
    th = h * tf
    trunk = [p + np.array([0, 0, -0.4]), p + np.array([0, 0, th * 0.35]) + lv * th * 0.35, p + np.array([0, 0, th]) + lv * th]
    rad = [r0 * 1.45, r0 * 1.05, r0 * 0.9]
    sides = 6 if h > 12 else (5 if h > 5 else 4)
    if lib.mid():
        sides = 4
        nl = min(nl, 4)
    lib.tube(Bk, trunk, rad, sides=sides, uv_v_scale=0.25, uv_u_scale=max(1.0, r0 * 4),
             rough=lambda i, k: 1.0 + 0.18 * (vnoise(i * 2.1, k * 1.7, seed) - 0.5) + (0.25 if i == 0 and k % 2 else 0))
    top = trunk[-1]
    crown_c = p + np.array([0, 0, h * cc]) + lv * h * 0.6
    Rz = R * flat
    CROWNS.append((float(crown_c[0]), float(crown_c[1]), float(crown_c[2]), float(R), float(Rz)))
    tips = []
    for i in range(nl):
        a = 2 * math.pi * i / nl + rr.uniform(-0.4, 0.4)
        ang = math.radians(rr.uniform(*la))
        L = (crown_c[2] - top[2]) / max(0.25, math.cos(ang)) * rr.uniform(0.9, 1.2)
        L = min(L, R * 1.1 / max(0.3, math.sin(ang)))
        d = np.array([math.cos(a) * math.sin(ang), math.sin(a) * math.sin(ang), math.cos(ang)])
        mid = top + d * L * 0.5 + np.array([0, 0, L * 0.08])
        end = top + d * L + np.array([0, 0, L * 0.15])
        if lib.mid():
            lib.tube(Bk, [top, end], [r0 * 0.5, r0 * 0.2], sides=3, uv_v_scale=0.3)
        else:
            lib.tube(Bk, [top, mid, end], [r0 * 0.6, r0 * 0.4, r0 * 0.18], sides=4 if h > 12 else 3, uv_v_scale=0.3)
        tips.append(end)
        if h > 12 and not lib.mid():
            for k in range(1):
                b0 = top + (end - top) * rr.uniform(0.4, 0.8)
                d2 = norm(d + np.array([rr.uniform(-0.6, 0.6), rr.uniform(-0.6, 0.6), 0.3]))
                e2 = b0 + d2 * L * 0.4
                lib.tube(Bk, [b0, e2], [r0 * 0.2, r0 * 0.07], sides=3, uv_v_scale=0.3)
                tips.append(e2)
    # crown cards: shell around tips + crown ellipsoid
    n_cards = int(density * (R * R * 1.5 + 6) * (1.0 if h > 6 else 0.7))
    n_cards = min(n_cards, 260)
    for i in range(n_cards):
        if i < len(tips) * 6 and tips:
            base = tips[i % len(tips)]
            q = base + np.array([rr.gauss(0, R * 0.3), rr.gauss(0, R * 0.3), rr.gauss(0, Rz * 0.25)])
        else:
            u = norm(np.array([rr.gauss(0, 1), rr.gauss(0, 1), abs(rr.gauss(0, 1)) * 0.9 - 0.15]))
            s = rr.uniform(0.6, 1.0) ** 0.5
            q = crown_c + np.array([u[0] * R * s, u[1] * R * s, u[2] * Rz * s])
        rel = q - crown_c
        rn = norm(np.array([rel[0] / R, rel[1] / R, rel[2] / max(Rz, 0.5)]))
        nrm = norm(rn + np.array([0, 0, 0.45]))
        size = csize * rr.uniform(0.75, 1.25) * (0.6 if h < 5 else 1.0) * min(1.0, 0.4 + R / 6)
        if rr.random() < 0.7:
            t1 = norm(np.cross(rn, np.array([0, 0, 1.0])) + np.array([rr.uniform(-.3, .3)] * 3))
            t2 = norm(np.cross(t1, rn))
            if rr.random() < 0.5:
                t1, t2 = t2, -t1
        else:
            t1 = norm(np.array([rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.3, 0.3)]))
            t2 = norm(np.cross(t1, norm(np.array([rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-1, 1)]))))
        depth = np.linalg.norm(rel / np.array([R, R, max(Rz, 0.5)]))
        ao = float(np.clip(0.42 + 0.5 * depth + 0.15 * (rel[2] / max(Rz, 0.5)), 0.35, 1.0))
        card(F, q, t1, t2, size, kinds[i % len(kinds)], nrm, ao)
    if collide:
        col.box((p[0], p[1], p[2] - 0.3), (max(0.6, r0 * 2.4), max(0.6, r0 * 2.4), 3.0))
    return crown_c


def tuft(F, p, kind='grass', size=0.9, rr=None, n=2, ao=0.85):
    if lib.cleared(p[0], p[1]):
        return
    rr = rr or lib.rng(int(p[0] * 13 + p[1] * 7))
    a0 = rr.uniform(0, math.pi)
    for k in range(n):
        a = a0 + math.pi * k / n
        t1 = np.array([math.cos(a), math.sin(a), 0.0]); t2 = np.array([0, 0, 1.0])
        card(F, np.array(p) + t2 * size * 0.5, t1, t2, size, kind, np.array([0, 0, 1.0]), ao)


def bush(F, p, R, rr, kinds=('shrub', 'jungle'), ao_lo=0.5):
    if lib.cleared(p[0], p[1]):
        return
    n = int(6 + R * R * 3)
    for i in range(n):
        u = norm(np.array([rr.gauss(0, 1), rr.gauss(0, 1), abs(rr.gauss(0, 1))]))
        q = np.array(p) + np.array([u[0] * R, u[1] * R, u[2] * R * 0.7]) * rr.uniform(0.3, 1.0)
        t1 = norm(np.cross(u, np.array([0, 0, 1.0])) + 1e-3); t2 = norm(np.cross(t1, u))
        card(F, q, t1, t2, R * rr.uniform(0.9, 1.4), kinds[i % len(kinds)], norm(u + np.array([0, 0, 0.5])),
             float(np.clip(ao_lo + 0.5 * u[2], 0.4, 1.0)))


def roots(sc, top, out, height, rr, n=6, spread=4.0):
    """strangler-fig roots pouring down a wall from `top` (3d) with outward normal `out`"""
    Bk = sc['bark']
    out = norm(np.array([out[0], out[1], 0.0])); t1 = np.array([-out[1], out[0], 0.0])
    for k in range(n):
        x = (k - (n - 1) / 2) / max(1, n - 1) * spread + rr.uniform(-0.4, 0.4)
        pts = []
        z = top[2] + 0.3
        p = np.array(top, float) + t1 * x * 0.3 + out * 0.3
        steps = max(3, int(height / 2.0))
        for s in range(steps + 1):
            f = s / steps
            lateral = t1 * (x * (0.3 + 0.7 * f) + math.sin(f * 7 + k) * 0.4)
            pts.append(np.array([top[0], top[1], top[2] + 0.3 - height * f]) + lateral + out * (0.25 + 0.15 * math.sin(f * 11 + k)))
        # foot spreading on the ground
        pts.append(pts[-1] + out * rr.uniform(0.8, 2.0) + np.array([0, 0, -0.3]))
        r = rr.uniform(0.10, 0.28)
        rad = [r * (1.0 - 0.4 * (i / len(pts))) for i in range(len(pts))]
        rad[-1] = r * 0.8; rad[-2] = r * 1.1
        lib.tube(Bk, pts, rad, sides=4, uv_v_scale=0.4)


# ------------------------------------------------------------------ occupancy raster (1 m) over the box + margin
class Occ:
    X0, Y0, N = -190, -200, 400

    def __init__(self):
        self.m = np.zeros((self.N, self.N), np.uint8)

    def ij(self, x, y):
        return int(y - self.Y0), int(x - self.X0)

    def fill_poly(self, poly, v):
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        i0, j0 = self.ij(min(xs), min(ys)); i1, j1 = self.ij(max(xs), max(ys))
        i0 = max(i0, 0); j0 = max(j0, 0); i1 = min(i1 + 1, self.N - 1); j1 = min(j1 + 1, self.N - 1)
        if i1 <= i0 or j1 <= j0:
            return
        Y, X = np.mgrid[i0:i1 + 1, j0:j1 + 1]
        ins = lib.points_in_poly(X + self.X0 + 0.5, Y + self.Y0 + 0.5, poly)
        sub = self.m[i0:i1 + 1, j0:j1 + 1]
        sub[ins] = np.maximum(sub[ins], v)

    def fill_circle(self, x, y, r, v):
        i, j = self.ij(x, y); k = int(r) + 1
        for a in range(-k, k + 1):
            for b in range(-k, k + 1):
                if a * a + b * b <= r * r and 0 <= i + a < self.N and 0 <= j + b < self.N:
                    self.m[i + a, j + b] = max(self.m[i + a, j + b], v)

    def get(self, x, y):
        i, j = self.ij(x, y)
        if 0 <= i < self.N and 0 <= j < self.N:
            return int(self.m[i, j])
        return 255

    def free(self, x, y, r=1.0):
        for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            if self.get(x + dx, y + dy) != 0:
                return False
        return True


def cover():
    """cover.png as (h,w,4) uint8 + sampler (R road, G green, B water)"""
    import bpy
    im = bpy.data.images.load(lib.SRC + 'cover.png')
    w, h = im.size
    a = (np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1] * 255).astype(np.uint8)   # row 0 = north
    bpy.data.images.remove(im)
    def at(x, y):
        c = int((x + 300) / 4); r = int((310 - y) / 4)
        if 0 <= r < h and 0 <= c < w:
            return a[r, c]
        return np.zeros(4, np.uint8)
    return at


def build(sc, col, ctx):
    G = ctx['ground']; occ = ctx['occ']; cov = ctx['cover']
    rr = lib.rng(777)
    O = lib.osm()
    n_trees = 0
    # ---------------- street trees along roads (offset to both kerbs), wild trees in lots
    for r in O['roads']:
        if r['tunnel'] or r['bridge'] or r['hw'] in ('motorway', 'steps', 'footway', 'path', 'service', 'pedestrian'):
            continue
        if r['name'] == 'けやき坂':
            continue                                    # keyaki.py plants Keyakizaka
        w = (r['width'] or 6.0)
        line = r['line']
        for i in range(len(line) - 1):
            a = np.array(line[i]); b = np.array(line[i + 1]); L = float(np.linalg.norm(b - a))
            if L < 1:
                continue
            u = (b - a) / L; nrm = np.array([-u[1], u[0]])
            k = 0.0
            while k < L:
                k += rr.uniform(10, 16)
                if k >= L:
                    break
                for s in (-1, 1):
                    if rr.random() < 0.3:
                        continue
                    q = a + u * k + nrm * s * (w / 2 + rr.uniform(1.2, 2.5))
                    if not (lib.BOX[0] < q[0] < lib.BOX[2] and lib.BOX[1] < q[1] < lib.BOX[3]):
                        continue
                    if not occ.free(q[0], q[1], 2.0):
                        continue
                    z = G(q[0], q[1])
                    h = rr.uniform(11, 19); R = h * rr.uniform(0.35, 0.5)
                    tree(sc, col, (q[0], q[1], z), rr.choice(['zelkova', 'broad', 'broad']), h, R, rr.randrange(1 << 30), 'foliage_streets')
                    occ.fill_circle(q[0], q[1], 3.0, 9)
                    n_trees += 1
    # wild trees in lots and green areas (not on roads)
    for it in range(1900):
        x = rr.uniform(lib.BOX[0], lib.BOX[2]); y = rr.uniform(lib.BOX[1], lib.BOX[3])
        c = cov(x, y)
        green = c[1] > 100
        if c[0] > 100 or c[2] > 100:
            continue
        if not occ.free(x, y, 3.0 if not green else 2.0):
            continue
        if rr.random() > (0.5 if green else 0.12):
            continue
        z = G(x, y)
        big = rr.random() < (0.5 if green else 0.3)
        h = rr.uniform(10, 20) if big else rr.uniform(4, 9)
        R = h * rr.uniform(0.35, 0.55)
        tree(sc, col, (x, y, z), rr.choice(['broad', 'fig', 'zelkova', 'young'] if big else ['young', 'broad']), h, R,
             rr.randrange(1 << 30), 'foliage_lots')
        occ.fill_circle(x, y, max(3.0, R * 0.6), 9)
        n_trees += 1
        # undergrowth around
        for k in range(rr.randrange(1, 4) if not lib.mid() else 0):
            q = np.array([x + rr.uniform(-4, 4), y + rr.uniform(-4, 4)])
            bush(sc['foliage_lots'], (q[0], q[1], G(q[0], q[1])), rr.uniform(0.6, 1.4), rr)
    ctx['n_trees'] = n_trees
    # ---------------- growth on ruins: roof shrubs & trees, vine curtains from tops, roots
    tops = ctx.get('tops', [])
    for (region, z, bid) in tops:
        area = abs(lib.poly_area([tuple(p) for p in region]))
        if area < 6:
            continue
        zone = 'foliage_high' if z > 70 else 'foliage_roofs'
        xs = [p[0] for p in region]; ys = [p[1] for p in region]
        n_b = int(area / (70 if not lib.mid() else 250)) + 1
        n_t = int(area / 260)
        for k in range(min(n_b, 40)):
            for _ in range(8):
                x = rr.uniform(min(xs), max(xs)); y = rr.uniform(min(ys), max(ys))
                if lib.point_in_poly(x, y, region):
                    bush(sc[zone], (x, y, z), rr.uniform(0.7, 1.8), rr)
                    break
        for k in range(min(n_t, 6)):
            for _ in range(8):
                x = rr.uniform(min(xs), max(xs)); y = rr.uniform(min(ys), max(ys))
                if lib.point_in_poly(x, y, region):
                    h = rr.uniform(3.5, 9.0)
                    tree(sc, col, (x, y, z), rr.choice(['young', 'fig', 'broad']), h, h * 0.5, rr.randrange(1 << 30), zone,
                         density=0.8, collide=False)
                    break
    walls = ctx.get('walls', [])
    for (poly, ztop_fn, zbase, bid) in walls:
        n = len(poly)
        for i in range(n):
            a = np.array(poly[i]); b = np.array(poly[(i + 1) % n])
            L = float(np.linalg.norm(b - a))
            if L < 3:
                continue
            u = (b - a) / L; out = np.array([u[1], -u[0]])
            k = rr.uniform(0, 4)
            while k < L - 1:
                q = a + u * k
                zt = ztop_fn(q[0], q[1])
                hgt = zt - zbase
                if hgt > 3 and rr.random() < (0.45 if not lib.mid() else 0.2):
                    length = min(hgt - 0.5, rr.uniform(0.15, 0.75) * hgt)
                    zone = 'foliage_high' if zt > 70 else 'foliage_roofs'
                    hang(sc[zone], (q[0], q[1], zt + 0.3), out, rr.uniform(1.6, 3.8), length,
                         rr.choice(['vine', 'vine2']), 0.95, rr.randrange(1 << 30))
                k += rr.uniform(3.0, 9.0)
            # strangler roots on some low/mid walls facing the street
            if 6 < (ztop_fn(*((a + b) / 2)) - zbase) < 45 and L > 6 and rr.random() < (0.035 if not lib.mid() else 0.0):
                m = (a + b) / 2
                zt = ztop_fn(m[0], m[1])
                roots(sc, (m[0], m[1], zt), out, zt - zbase + 0.3, rr, n=rr.randrange(4, 9), spread=min(L * 0.6, 7))
                tree(sc, col, (m[0] - out[0] * 1.5, m[1] - out[1] * 1.5, zt), 'fig', rr.uniform(6, 11), rr.uniform(4, 6),
                     rr.randrange(1 << 30), 'foliage_high' if zt > 70 else 'foliage_roofs', collide=False)
    # tower tear: vines spill from exposed slab edges, small trees on slabs
    for (x, y, z, nx, ny) in ctx.get('vine_anchors', []):
        if rr.random() < (0.75 if not lib.mid() else 0.3):
            hang(sc['foliage_high'], (x, y, z + 0.2), (nx, ny), rr.uniform(2.5, 5.0), rr.uniform(6, 26),
                 rr.choice(['vine', 'vine2']), 1.0, rr.randrange(1 << 30))
        if rr.random() < 0.4:
            q = np.array([x, y]) - np.array([nx, ny]) * rr.uniform(2, 6)
            tree(sc, col, (q[0], q[1], z), rr.choice(['young', 'fig']), rr.uniform(3, 7), rr.uniform(2, 3.5),
                 rr.randrange(1 << 30), 'foliage_high', collide=False)
