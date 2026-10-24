"""The ruined city: PLATEAU buildings (gen.plateau) -> sixty years of decay -> packed tiles for the viewer.
  python -m gen.city [N]      -> PUBLIC/data/city/<i>_<j>.bin (gzip), PUBLIC/data/city/index.json, ASSETS/build/roof.npz

Decay (deterministic per building id): tall towers lose their top at a jagged line (f of the height), the broken
floor becomes a 'cap' (rubble slab) surface; every building gets an overgrowth factor the shader turns into vines
and moss; windows and facades are drawn procedurally from the vertex attributes:
  pos uint16 x3 (cm from the tile corner; z in 2 cm above the tile base), nrm int8 x3, kind uint8 (0 wall 1 roof 2 cap),
  seed uint8, hcls uint8 (building height / 2 m), veg uint8, pad, hb uint16 (height above the building base, 0.1 m)
A 'lite' mesh (a box per building, or the mesh itself when it is as small) draws distant tiles."""
import os, sys, json, gzip, pickle, glob, struct, time, hashlib, math
import numpy as np
from PIL import Image, ImageDraw
from .frame import ASSETS, PUBLIC, X0, Y0, X1, Y1, TILE, NTX, NTY, tile_of, tile_bounds

OUT = os.path.join(PUBLIC, 'data', 'city')
ROOF_RES = 4.0

# landmarks: (id, x, y, radius) in the local frame; the tallest building near the point gets the id
LANDMARKS = [(1, 4066, -102, 90), (2, -802, 3342, 80), (3, -276, 3549, 60), (4, 2597, 106, 90), (5, 3588, 128, 90), (6, 150, -120, 70), (7, 294, -42, 60),
             (8, 232, 2762, 60), (9, -1236, 2592, 70)]     # tokyo tower, tocho, cocoon, mori, azabudai, scramble sq, hikarie, docomo, opera city

def tag_landmarks(bs):
    tag = {}
    for (lid, x, y, r) in LANDMARKS:
        near = [b for b in bs if abs(b['cx'] - x) < r and abs(b['cy'] - y) < r]
        if not near: continue
        best = max(near, key=lambda b: b['z1'] - b['z0'])
        tag[best['id']] = lid
    return tag

def seed_of(bid):
    return int(hashlib.md5(bid.encode()).hexdigest()[:8], 16)

def hash2(x, y):
    """cheap value noise on a 7 m grid for the jagged break line"""
    gx = np.floor(x / 7.0); gy = np.floor(y / 7.0)
    fx = x / 7.0 - gx; fy = y / 7.0 - gy
    def h(a, b):
        v = np.sin(a * 127.1 + b * 311.7) * 43758.5453
        return v - np.floor(v)
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    return (h(gx, gy) * (1 - fx) + h(gx + 1, gy) * fx) * (1 - fy) + (h(gx, gy + 1) * (1 - fx) + h(gx + 1, gy + 1) * fx) * fy

def clip_below(V, F, s):
    """keep the part of the mesh where the per-vertex scalar s <= 0 (Sutherland-Hodgman per triangle)."""
    sv = s[F]                                    # (m,3)
    inside = sv <= 0
    n_in = inside.sum(1)
    keep = F[n_in == 3]
    outV = [V]; outF = [keep]; base = len(V)
    newV = []; newF = []
    for f, si, ins in zip(F[(n_in > 0) & (n_in < 3)], sv[(n_in > 0) & (n_in < 3)], inside[(n_in > 0) & (n_in < 3)]):
        poly = []
        for k in range(3):
            a, b = k, (k + 1) % 3
            if ins[a]: poly.append(('v', f[a]))
            if ins[a] != ins[b]:
                t = si[a] / (si[a] - si[b])
                p = V[f[a]] + (V[f[b]] - V[f[a]]) * t
                poly.append(('n', len(newV))); newV.append(p)
        idx = [base + i if kind == 'n' else i for kind, i in poly]
        for k in range(1, len(idx) - 1): newF.append((idx[0], idx[k], idx[k + 1]))
    if newV:
        outV.append(np.asarray(newV, np.float32)); outF.append(np.asarray(newF, np.int32).reshape(-1, 3))
    return np.concatenate(outV), np.concatenate(outF)

def decay(b, landmark=0):
    """returns (V, F, kind, zcut) for the building after sixty years: the top sheared off at a jagged line, or a
    corner wedge gone, with the floors inside exposed as slabs (kind 2)"""
    rng = np.random.default_rng(seed_of(b['id']))
    V = b['V'].copy(); F = b['F']; N = b['N']
    H = b['z1'] - b['z0']
    keep = N[:, 2] > -0.9
    F = F[keep]; N = N[keep]
    p = 0.6 if H > 80 else 0.48 if H > 45 else 0.3 if H > 25 else 0.14 if H > 12 else 0.04
    if landmark in (1, 3, 8): p = 0.0                    # the lattice towers stand
    if landmark == 2: p = 1.0                            # the north tower of the Tocho lost its crown (board 02)
    kind = np.where(N[:, 2] > 0.9, 1, 0).astype(np.uint8)
    roofF = F[kind == 1]
    zcut = None; mode = None
    if rng.random() < p and H > 8:
        mode = 'top' if (H < 25 or rng.random() < 0.6 or landmark in (2, 6)) else 'wedge'
    if mode == 'top':
        f = rng.uniform(0.3, 0.82) if H > 25 else rng.uniform(0.45, 0.85)
        if landmark == 6: f = 0.77                                  # Scramble Square: the start ledge of the game, ~190 m
        zcut = b['z0'] + f * H
        jag = (hash2(V[:, 0] + 1000 * rng.random(), V[:, 1]) - 0.5) * (6.0 if H > 45 else 3.0)
        s = V[:, 2] - (zcut + jag)
    elif mode == 'wedge':
        # a slanted plane through the upper part: everything above and outside it fell away
        P = V[:, :2]; cx, cy = P[:, 0].mean(), P[:, 1].mean()
        a = rng.uniform(0, 2 * np.pi); nx, ny = np.cos(a), np.sin(a)
        ext = max(3.0, 0.5 * max(np.ptp(P[:, 0]), np.ptp(P[:, 1])))
        z0 = b['z0'] + H * rng.uniform(0.35, 0.7); zcut = z0
        slope = rng.uniform(0.6, 1.6)                               # m of height per m toward the gone side
        d = (V[:, 0] - cx) * nx + (V[:, 1] - cy) * ny - ext * rng.uniform(-0.3, 0.3)
        jag = (hash2(V[:, 0] * 1.3 + 500 * rng.random(), V[:, 2] * 1.1) - 0.5) * 5.0
        # > 0 where the wedge is gone; on the gone side the cut may descend at most a third of the way to the ground,
        # so a wide building loses a corner, not its whole flank
        drop = np.minimum(d * slope, (z0 - b['z0']) * 0.35)
        s = (V[:, 2] - z0) + drop + jag
    if mode is not None:
        V2, F2 = clip_below(V, F, s)
        e1 = V2[F2[:, 1]] - V2[F2[:, 0]]; e2 = V2[F2[:, 2]] - V2[F2[:, 0]]
        N2 = np.cross(e1, e2); N2 /= np.maximum(np.linalg.norm(N2, axis=1), 1e-9)[:, None]
        kind2 = np.where(N2[:, 2] > 0.9, 1, 0).astype(np.uint8)
        # the floors inside: the roof outline copied down every storey into the broken region, as rubble-strewn slabs
        if len(roofF) and mode == 'top':
            # the broken floor at the break line (kind 2): what you land on, and what the collision raster sees
            used, inv = np.unique(roofF.ravel(), return_inverse=True)
            C = V[used].copy(); C[:, 2] = zcut + (hash2(C[:, 0] + 1000 * rng.random(), C[:, 1]) - 0.5) * 1.5 - 0.3
            Fc = inv.reshape(-1, 3).astype(np.int32) + len(V2)
            V2 = np.concatenate([V2, C.astype(np.float32)]); F2 = np.concatenate([F2, Fc]); kind2 = np.concatenate([kind2, np.full(len(Fc), 2, np.uint8)])
        if len(roofF) and H > 14 and mode == 'wedge':
            # the floors broke off with the walls: only stubs survive along the torn edge, a few metres into the gap
            used, inv = np.unique(roofF.ravel(), return_inverse=True)
            R = V[used]; Fr = inv.reshape(-1, 3).astype(np.int32)
            floorH = 3.4 if H > 20 else 2.9
            zs = np.arange(b['z0'] + floorH, b['z1'] - 0.5, floorH)[-14:]
            for zf in zs:
                if rng.random() < 0.4: continue                                   # that floor pancaked with the walls
                C = R.copy(); C[:, 2] = zf + (hash2(C[:, 0] + 77 * zf, C[:, 1]) - 0.5) * 0.3
                dc = (C[:, 0] - cx) * nx + (C[:, 1] - cy) * ny - ext * 0.0
                sc = (C[:, 2] - z0) + np.minimum(dc * slope, (z0 - b['z0']) * 0.35)
                reach = 1.5 + 5.0 * hash2(C[:, 0] * 0.7 + 31 * zf, C[:, 1] * 0.7) ** 2
                Cv, Cf = clip_below(C.astype(np.float32), Fr, sc - reach)        # inside the gap, within reach of the edge
                if len(Cf) == 0: continue
                off = len(V2); V2 = np.concatenate([V2, Cv]); F2 = np.concatenate([F2, Cf + off]); kind2 = np.concatenate([kind2, np.full(len(Cf), 6, np.uint8)])
        V, F, kind = V2, F2, kind2
    return V, F, kind, zcut

def roof_furniture(b, V, F, kind, zcut, rng, landmark):
    """what stands on a Tokyo roof: hipped tile roofs on the houses, parapets, stair bulkheads, water tanks and air
    conditioners on everything taller. Returns (V2, F2, kind2) to append; kinds 3 parapet/bulkhead concrete,
    4 metal, 5 roof tiles."""
    from shapely.geometry import Polygon, MultiPoint, Point
    from shapely.ops import unary_union
    H = b['z1'] - b['z0']
    up = F[kind == 1]
    if landmark == 1: return None
    ztop = float(V[up][:, :, 2].max()) if len(up) else b['z1']
    top = up[V[up][:, :, 2].min(1) > ztop - 0.8] if len(up) else up
    outV = []; outF = []; outK = []
    def add(vs, fs, k):
        off = sum(len(v) for v in outV); outV.append(np.asarray(vs, np.float32)); outF.append(np.asarray(fs, np.int32) + off); outK.append(np.full(len(fs), k, np.uint8))
    def box(cx, cy, z0, w, d, h, ang, k):
        c, s_ = math.cos(ang), math.sin(ang)
        cs = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
        pts = [(cx + x * c - y * s_, cy + x * s_ + y * c) for x, y in cs]
        vs = [(x, y, z0) for x, y in pts] + [(x, y, z0 + h) for x, y in pts]
        fs = []
        for i in range(4):
            j = (i + 1) % 4; fs += [(i, j, j + 4), (i, j + 4, i + 4)]
        fs += [(4, 5, 6), (4, 6, 7)]
        add(vs, fs, k)
    if H < 11.0 and zcut is None:
        # a hipped roof of tiles over the footprint's rectangle, with eaves
        P = b['V'][:, :2]
        if len(P) > 300: P = P[rng.choice(len(P), 300, replace=False)]
        r = MultiPoint(P).minimum_rotated_rectangle
        if r.geom_type != 'Polygon': return None
        c = np.asarray(r.exterior.coords)[:4]
        e0 = c[1] - c[0]; e1 = c[2] - c[1]; l0 = np.linalg.norm(e0); l1 = np.linalg.norm(e1)
        if l0 < 2.5 or l1 < 2.5 or max(l0, l1) > 45.0 or r.area > 1200: return None     # a house, not a station or a hall
        if l0 < l1: c = np.roll(c, -1, 0); e0, e1 = e1, -e0; l0, l1 = l1, l0
        ax = e0 / l0; ay = e1 / l1; ov = 0.45
        q = [c[0] - ax * ov - ay * ov, c[1] + ax * ov - ay * ov, c[2] + ax * ov + ay * ov, c[3] - ax * ov + ay * ov]
        half = (l1 + 2 * ov) / 2; rise = half * math.tan(math.radians(27))
        inset = min(half, (l0 + 2 * ov) / 2 - 0.3)
        m0 = (q[0] + q[3]) / 2 + ax * inset; m1 = (q[1] + q[2]) / 2 - ax * inset
        zr = ztop - 0.15
        vs = [(q[0][0], q[0][1], zr), (q[1][0], q[1][1], zr), (q[2][0], q[2][1], zr), (q[3][0], q[3][1], zr), (m0[0], m0[1], zr + rise), (m1[0], m1[1], zr + rise)]
        fs = [(0, 1, 5), (0, 5, 4), (2, 3, 4), (2, 4, 5), (1, 2, 5), (3, 0, 4)]
        add(vs, fs, 5)
        # the underside of the eaves is never seen from the air: skip it
    elif H >= 11.0 and zcut is None:
        polys = []
        for t in top:
            tri = Polygon(V[t][:, :2])
            if tri.is_valid and tri.area > 0.05: polys.append(tri)
        if not polys: return None
        roof = unary_union(polys).buffer(0.02)
        parts = [g for g in (roof.geoms if hasattr(roof, 'geoms') else [roof]) if g.area > 12]
        for g in parts:
            ring = np.asarray(g.exterior.coords)
            # parapet: a 0.3 m thick wall along each edge
            for i in range(len(ring) - 1):
                p0, p1 = ring[i], ring[i + 1]; d = p1 - p0; L = np.linalg.norm(d)
                if L < 0.4: continue
                ang = math.atan2(d[1], d[0]); mid = (p0 + p1) / 2
                n = np.array([-d[1], d[0]]) / L
                box(mid[0] - n[0] * 0.15, mid[1] - n[1] * 0.15, ztop, L, 0.3, 0.85, ang, 3)
            inner = g.buffer(-2.2)
            if inner.is_empty or inner.area < 6: continue
            minx, miny, maxx, maxy = inner.bounds
            def spot(tries=12):
                for _ in range(tries):
                    x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                    if inner.contains(Point(x, y)): return x, y
                return None
            # stair bulkhead
            sp = spot()
            if sp and g.area > 60:
                box(sp[0], sp[1], ztop, 3.4, 2.8, 2.7 if H > 20 else 2.3, rng.uniform(0, math.pi), 3)
            # water tank: a squat cylinder on a frame
            if 12 < H < 75 and g.area > 80 and rng.random() < 0.55:
                sp = spot()
                if sp:
                    r_ = 1.3; n = 8; zt = ztop + 1.1
                    vs = [(sp[0] + r_ * math.cos(2 * math.pi * k / n), sp[1] + r_ * math.sin(2 * math.pi * k / n), zt) for k in range(n)]
                    vs += [(x, y, zt + 2.1) for (x, y, _) in vs] + [(sp[0], sp[1], zt + 2.1)]
                    fs = []
                    for k in range(n):
                        j = (k + 1) % n; fs += [(k, j, j + n), (k, j + n, k + n), (k + n, j + n, 2 * n)]
                    add(vs, fs, 4)
                    box(sp[0], sp[1], ztop, 2.4, 2.4, 1.1, 0.0, 4)
            # air conditioners and vents
            for _ in range(int(min(8, max(1, g.area / 120)))):
                sp = spot(6)
                if sp: box(sp[0], sp[1], ztop, rng.uniform(0.8, 1.3), 0.45, rng.uniform(0.7, 1.0), rng.uniform(0, math.pi), 4)
    if zcut is not None and H > 20:
        # the fallen floors: a mound of rubble at the foot of the tower, spilling out on one side
        P = b['V'][:, :2]; cx, cy = P[:, 0].mean(), P[:, 1].mean()
        ext = max(2.0, 0.5 * max(np.ptp(P[:, 0]), np.ptp(P[:, 1])))
        fallen = b['z1'] - zcut
        R = float(np.clip(fallen * 0.22 + ext * 0.35, 5.0, 26.0)); hgt = R * 0.32
        a = rng.uniform(0, 2 * math.pi); mx, my = cx + math.cos(a) * ext * 0.9, cy + math.sin(a) * ext * 0.9
        zb = b['z0'] - 0.3; n = 10
        vs = [(mx, my, zb + hgt)]
        for k in range(n):
            t = 2 * math.pi * k / n; rr = R * rng.uniform(0.7, 1.15)
            vs.append((mx + rr * math.cos(t), my + rr * math.sin(t), zb))
            vs.append((mx + rr * 0.55 * math.cos(t + 0.3), my + rr * 0.55 * math.sin(t + 0.3), zb + hgt * rng.uniform(0.45, 0.8)))
        fs = []
        for k in range(n):
            j = (k + 1) % n
            o, i = 1 + 2 * k, 2 + 2 * k; o2, i2 = 1 + 2 * j, 2 + 2 * j
            fs += [(o, o2, i2), (o, i2, i), (i, i2, 0)]
        add(vs, fs, 2)
    if not outV: return None
    return np.concatenate(outV), np.concatenate(outF), np.concatenate(outK)

def box_mesh(b, ztop):
    """the smallest rotated rectangle around the footprint, extruded z0..ztop (10 triangles, no bottom)"""
    from shapely.geometry import MultiPoint
    P = b['V'][:, :2]
    if len(P) > 400: P = P[np.random.default_rng(1).choice(len(P), 400, replace=False)]
    r = MultiPoint(P).minimum_rotated_rectangle
    if r.geom_type != 'Polygon': return None
    c = np.asarray(r.exterior.coords)[:4]
    z0 = b['z0']
    V = np.array([[x, y, z0] for x, y in c] + [[x, y, ztop] for x, y in c], np.float32)
    F = []; kind = []
    for k in range(4):
        a, bb = k, (k + 1) % 4
        F += [(a, bb, bb + 4), (a, bb + 4, a + 4)]; kind += [0, 0]
    F += [(4, 5, 6), (4, 6, 7)]; kind += [1, 1]
    F = np.asarray(F, np.int32)
    # orient outward: flip faces whose normal points toward the centre
    cx, cy = c[:, 0].mean(), c[:, 1].mean()
    for i in range(len(F)):
        e1 = V[F[i, 1]] - V[F[i, 0]]; e2 = V[F[i, 2]] - V[F[i, 0]]; n = np.cross(e1, e2)
        m = V[F[i]].mean(0)
        if kind[i] == 1:
            if n[2] < 0: F[i] = F[i, ::-1]
        elif np.dot(n[:2], m[:2] - [cx, cy]) < 0: F[i] = F[i, ::-1]
    return V, F, np.asarray(kind, np.uint8)

def pack(V, F, kind, attrs, ox, oy, oz):
    """flat-shaded, welded on (position, normal); attrs = per-face (seed, hcls, veg, landmark) + per-vertex hb"""
    e1 = V[F[:, 1]] - V[F[:, 0]]; e2 = V[F[:, 2]] - V[F[:, 0]]
    N = np.cross(e1, e2); ln = np.linalg.norm(N, axis=1); ok = ln > 1e-7
    F = F[ok]; N = N[ok] / ln[ok][:, None]; kind = kind[ok]
    seed, hcls, veg, lm, z0 = (a[ok] for a in attrs)
    P = V[F].reshape(-1, 3)
    pq = np.stack([np.clip(np.round((P[:, 0] - ox) * 100), 0, 65535), np.clip(np.round((P[:, 1] - oy) * 100), 0, 65535),
                   np.clip(np.round((P[:, 2] - oz) * 50), 0, 65535)], 1).astype(np.uint16)
    nq = np.clip(np.round(np.repeat(N, 3, 0) * 127), -127, 127).astype(np.int8)
    hb = np.clip(np.round((P[:, 2] - np.repeat(z0, 3)) * 10), 0, 65535).astype(np.uint16)
    rec = np.zeros(len(P), dtype=[('p', np.uint16, 3), ('n', np.int8, 3), ('k', np.uint8), ('s', np.uint8), ('h', np.uint8), ('v', np.uint8), ('pad', np.uint8), ('hb', np.uint16)])
    rec['p'] = pq; rec['n'] = nq; rec['k'] = np.repeat(kind, 3); rec['s'] = np.repeat(seed, 3); rec['h'] = np.repeat(hcls, 3); rec['hb'] = hb; rec['v'] = np.repeat(veg, 3); rec['pad'] = np.repeat(lm, 3)
    u, idx = np.unique(rec, return_inverse=True)
    return u, idx.astype(np.uint32)

def build_tile(args):
    (i, j), bl, tags = args
    x0, y0, x1, y1 = tile_bounds(i, j)
    oz = min(b['z0'] for b in bl) - 2.0
    full = dict(V=[], F=[], k=[], s=[], h=[], v=[], l=[], z0=[]); lite = dict(V=[], F=[], k=[], s=[], h=[], v=[], l=[], z0=[])
    roofs = []            # (polygon xy list, z) for the roof raster
    nfull = 0; nlite = 0
    for b in bl:
        rng = np.random.default_rng(seed_of(b['id']) ^ 0x5bd1e995)
        V, F, kind, zcut = decay(b, tags.get(b['id'], 0))
        if len(F) == 0: continue
        H = b['z1'] - b['z0']
        extra = roof_furniture(b, V, F, kind, zcut, rng, tags.get(b['id'], 0))
        if extra is not None:
            Ve, Fe, Ke = extra
            Vfull, Ffull, Kfull = np.concatenate([V, Ve]), np.concatenate([F, Fe + len(V)]), np.concatenate([kind, Ke])
        else:
            Vfull, Ffull, Kfull = V, F, kind
        veg = int(np.clip(rng.normal(0.55 if H < 30 else 0.35, 0.22), 0, 1) * 255)
        sd = seed_of(b['id']) & 255; hc = int(min(255, H / 2)); lm = tags.get(b['id'], 0)
        for d, (Vd, Fd, kd) in ((full, (Vfull, Ffull, Kfull)), (lite, (V, F, kind) if len(F) <= 24 else (box_mesh(b, zcut if zcut else b['z1']) or (V, F, kind)))):
            off = sum(len(v) for v in d['V'])
            d['V'].append(Vd); d['F'].append(Fd + off); d['k'].append(kd)
            n = len(Fd); d['s'].append(np.full(n, sd, np.uint8)); d['h'].append(np.full(n, hc, np.uint8)); d['v'].append(np.full(n, veg, np.uint8)); d['l'].append(np.full(n, lm, np.uint8)); d['z0'].append(np.full(n, b['z0'], np.float32))
        up = F[(kind == 1) | (kind == 2)]          # roofs and broken-floor caps carry the glider; stubs in a wedge gap (6) do not
        for t in up: roofs.append((V[t][:, :2], float(V[t][:, 2].mean())))
        nfull += len(F)
    out = {}
    for name, d in (('full', full), ('lite', lite)):
        V = np.concatenate(d['V']); F = np.concatenate(d['F']); k = np.concatenate(d['k'])
        u, idx = pack(V, F, k, (np.concatenate(d['s']), np.concatenate(d['h']), np.concatenate(d['v']), np.concatenate(d['l']), np.concatenate(d['z0'])), x0, y0, oz)
        out[name] = (u, idx)
    head = dict(i=i, j=j, ox=x0, oy=y0, oz=oz, full=dict(nv=len(out['full'][0]), ni=len(out['full'][1])), lite=dict(nv=len(out['lite'][0]), ni=len(out['lite'][1])), n=len(bl))
    hb = json.dumps(head).encode()
    body = b''.join([struct.pack('<I', len(hb)), hb] + [out[n][0].tobytes() + out[n][1].tobytes() for n in ('full', 'lite')])
    os.makedirs(OUT, exist_ok=True)
    with gzip.open(os.path.join(OUT, f'{i}_{j}.bin'), 'wb', compresslevel=6) as f: f.write(body)
    return head, roofs

def main(nproc=8):
    from multiprocessing import Pool
    bs = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'cache', 'plateau', '*.pkl'))): bs += pickle.load(open(f, 'rb'))
    tags = tag_landmarks(bs)
    from .hero_ids import excluded
    ex = excluded()
    tiles = {}
    for b in bs:
        if b['id'] in ex: continue                     # rebuilt by hand in a hero district (tools/hero/)
        i, j = tile_of(b['cx'], b['cy'])
        if 0 <= i < NTX and 0 <= j < NTY: tiles.setdefault((i, j), []).append(b)
    print(len(bs), 'buildings in', len(tiles), 'tiles;', len(ex), 'left to the hero districts; landmarks', sorted(tags.values()), flush=True)
    for f in glob.glob(os.path.join(OUT, '*.bin')): os.remove(f)
    heads = []; t0 = time.time()
    W = int((X1 - X0) / ROOF_RES); Hh = int((Y1 - Y0) / ROOF_RES)
    allroofs = []
    with Pool(nproc) as pool:
        for k, (head, roofs) in enumerate(pool.imap_unordered(build_tile, [(key, bl, tags) for key, bl in sorted(tiles.items())], chunksize=4)):
            heads.append(head)
            allroofs += [(z, poly) for poly, z in roofs if np.ptp(poly[:, 0]) > 1.5 or np.ptp(poly[:, 1]) > 1.5]
            if k % 50 == 0: print(k, 'tiles', round(time.time() - t0), 's', flush=True)
    # the roof raster: the highest surface wins, so draw the roofs from the lowest up
    im = Image.new('F', (W, Hh), -1000.0); dr = ImageDraw.Draw(im)
    allroofs.sort(key=lambda r: r[0])
    for z, poly in allroofs:
        dr.polygon([((x - X0) / ROOF_RES, (y - Y0) / ROOF_RES) for x, y in poly], fill=float(z))
    roof = np.asarray(im, np.float32)
    print('roof raster', roof.shape, 'covered', float((roof > -999).mean()), flush=True)
    np.savez_compressed(os.path.join(ASSETS, 'build', 'roof.npz'), roof=roof, x0=X0, y0=Y0, res=ROOF_RES)
    json.dump(dict(tile=TILE, x0=X0, y0=Y0, ntx=NTX, nty=NTY, tiles=sorted(heads, key=lambda h: (h['i'], h['j']))), open(os.path.join(OUT, 'index.json'), 'w'))
    tot = sum(h['full']['ni'] for h in heads) // 3; totl = sum(h['lite']['ni'] for h in heads) // 3
    size = sum(os.path.getsize(f) for f in glob.glob(os.path.join(OUT, '*.bin')))
    print('full tris', tot, 'lite tris', totl, 'bytes', size, round(time.time() - t0), 's')

if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
