"""Maman (Louise Bourgeois, 1999; bronze, marble eggs) at 66 Plaza: ~9.3 m tall, ~10 m across.
Eight long thin jointed legs rising from a small high body to knees ~9 m up, then plunging in long slightly bowed
shins to needle-pointed feet; abdomen with a ribbed cage of marble eggs beneath. Patina, a vine climbing a leg."""
import math
import numpy as np
import lib
from lib import vnoise, norm

POS = (6.8, 90.8)
FACE = math.radians(40.0)      # math angle the head points to (NE, toward the approach)


def build(sc, col, ctx):
    B = sc['bronze']
    rr = lib.rng(1999)
    z0 = lib.PLAZA_Z
    O = np.array([POS[0], POS[1], z0])
    ca, sa = math.cos(FACE), math.sin(FACE)
    def W(p):      # local (fwd, left, up) -> world
        return O + np.array([p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2]])
    body_z = 6.35
    # legs: (angle from forward deg, reach of the knee, knee height, foot reach)
    legs = [(24, 3.9, 9.25, 6.9), (64, 3.7, 9.05, 6.3), (114, 3.6, 8.85, 6.1), (154, 3.7, 8.7, 6.4)]
    leg_paths = []
    for side in (1, -1):
        for k, (ang, kr, kz, fr) in enumerate(legs):
            a = math.radians(ang * side + rr.uniform(-4, 4))
            d = np.array([math.cos(a), math.sin(a)])
            att = 0.55 if k < 2 else 0.5
            ctrl = [(att, body_z + 0.15),                       # coxa at the body
                    (att + 0.9, body_z + 1.6),                  # femur rising steeply
                    (kr - 0.4, kz - 0.15),
                    (kr, kz),                                   # knee (highest)
                    (kr + 0.55, kz - 0.6),
                    (kr + (fr - kr) * 0.52, kz * 0.56),         # tibia/metatarsus joint (slight kink)
                    (kr + (fr - kr) * 0.86, kz * 0.2),
                    (fr, 0.02)]                                 # needle foot
            pts = []
            for (r, z) in ctrl:
                pts.append(np.array([d[0] * r, d[1] * r, z]))
            path = lib.catmull(pts, 4 if not lib.mid() else 2)
            n = len(path)
            # radius profile: femur 0.17, knee knob 0.27, tibia 0.15 -> joint knob 0.16 -> tip 0.025
            rad = []
            for i in range(n):
                f = i / (n - 1)
                r = np.interp(f, [0, 0.12, 0.30, 0.38, 0.46, 0.62, 0.68, 0.74, 0.92, 1.0],
                                 [0.20, 0.17, 0.18, 0.28, 0.16, 0.14, 0.17, 0.12, 0.07, 0.02])
                rad.append(r)
            wpath = [W(p) for p in path]
            seed = k * 13 + (side > 0) * 7
            lib.tube(B, wpath, rad, sides=8 if not lib.mid() else 5, uv_u_scale=0.7, uv_v_scale=0.25,
                     rough=lambda i, j, s=seed: 1.0 + 0.16 * (vnoise(i * 1.7, j * 1.3, s) - 0.5) + 0.08 * math.sin(i * 2.3 + j))
            leg_paths.append(wpath)
            # knee knob (separate lumpy sphere)
            kn = W(pts[3])
            _blob(B, kn, 0.30, seed + 1, rr)
            jn = W(pts[5])
            _blob(B, jn, 0.19, seed + 2, rr)
    # thorax/head (front) and abdomen (back, larger), ribbed bronze
    _ellipsoid(B, W((0.55, 0, body_z + 0.15)), (0.85, 0.72, 0.5), FACE, 7, rr, bumps=0.08)
    _ellipsoid(B, W((-0.55, 0, body_z - 0.05)), (1.25, 1.05, 0.95), FACE, 8, rr, bumps=0.1)
    # egg sac: ribbed cage beneath the abdomen with marble eggs
    sac_c = W((-0.45, 0, body_z - 1.25))
    R = 0.85
    for m in range(10):
        a = 2 * math.pi * m / 10
        path = []
        for t in np.linspace(0.15, math.pi - 0.05, 9):
            path.append(sac_c + np.array([math.cos(a) * math.sin(t) * R, math.sin(a) * math.sin(t) * R, math.cos(t) * R * 1.05]))
        lib.tube(B, path, [0.05] * len(path), sides=4, uv_u_scale=0.2)
    for t in (1.6,):
        path = [sac_c + np.array([math.cos(a) * math.sin(t) * R, math.sin(a) * math.sin(t) * R, math.cos(t) * R * 1.05]) for a in np.linspace(0, 2 * math.pi, 13)]
        lib.tube(B, path, [0.04] * 13, sides=4, uv_u_scale=0.2)
    # eggs (marble: u in the 0.75..1 strip of the bronze atlas)
    for e in range(17):
        th = rr.uniform(1.2, 2.8); ph = rr.uniform(0, 2 * math.pi); rr_ = rr.uniform(0.25, 0.6)
        c = sac_c + np.array([math.cos(ph) * math.sin(th) * rr_, math.sin(ph) * math.sin(th) * rr_, math.cos(th) * rr_])
        _sphere(B, c, rr.uniform(0.13, 0.19), (0.76, 0.99), 5 if not lib.mid() else 3)
    # vine climbing a rear leg (woody stem + leaves): spiral up the back-left shin to the knee
    leg = leg_paths[3]
    stem = []
    nturn = 3.2
    for i in range(len(leg) - 1, len(leg) // 3, -1):
        f = (len(leg) - 1 - i) / (len(leg) - 1 - len(leg) // 3)
        p = leg[i]; q = leg[i - 1]
        t = norm(q - p); n1, n2 = lib.frame_from(t)
        a = f * nturn * 2 * math.pi
        stem.append(p + (math.cos(a) * n1 + math.sin(a) * n2) * 0.2)
    lib.tube(sc['bark'], stem, [0.05] * len(stem), sides=4, uv_v_scale=0.5)
    F = sc['foliage_maman']
    for i, p in enumerate(stem):
        for k in range(2):
            d = norm(np.array([rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(-0.6, 0.3)]))
            _card(F, p, d, 0.9 if i < len(stem) * 0.7 else 0.6, 'ivy', rr)
    # a few leaves tufted on the body (moss / seedling on the abdomen)
    for k in range(5):
        p = W((-0.55 + rr.uniform(-0.6, 0.6), rr.uniform(-0.5, 0.5), body_z + 0.75))
        _card(F, p, np.array([0, 0, 1.0]), 0.35, 'fern', rr, upright=True)
    ctx['labels'].append({'name': 'ママン', 'x': POS[0], 'y': POS[1], 'z': z0 + 11.5, 'kind': 'place'})
    ctx['maman'] = (POS[0], POS[1], z0)


def _sphere(b, c, r, urange=(0, 1), n=6):
    verts = []; uvs = []
    for i in range(n + 1):
        th = math.pi * i / n
        for j in range(n * 2 + 1):
            ph = 2 * math.pi * j / (n * 2)
            verts.append(c + r * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)]))
            uvs.append((urange[0] + (urange[1] - urange[0]) * j / (n * 2), i / n))
    faces = []
    w = n * 2 + 1
    for i in range(n):
        for j in range(n * 2):
            a = i * w + j
            faces.append([a, a + w, a + w + 1, a + 1])
    b.mesh(verts, faces, uvs)


def _ellipsoid(b, c, r, rot, n, rr, bumps=0.08):
    ca, sa = math.cos(rot), math.sin(rot)
    verts = []; uvs = []
    for i in range(n + 1):
        th = math.pi * i / n
        for j in range(2 * n + 1):
            ph = 2 * math.pi * j / (2 * n)
            k = 1 + bumps * (vnoise(i * 1.9, j * 1.3, 77) - 0.5) + 0.05 * math.sin(i * 3.1)
            x = r[0] * math.sin(th) * math.cos(ph) * k; y = r[1] * math.sin(th) * math.sin(ph) * k; z = r[2] * math.cos(th) * k
            verts.append(c + np.array([x * ca - y * sa, x * sa + y * ca, z]))
            uvs.append((j / (2 * n) * 0.7, i / n))
    faces = []
    w = 2 * n + 1
    for i in range(n):
        for j in range(2 * n):
            a = i * w + j
            faces.append([a, a + w, a + w + 1, a + 1])
    b.mesh(verts, faces, uvs)


def _blob(b, c, r, seed, rr):
    _ellipsoid(b, c, (r * 1.15, r, r * 0.9), rr.uniform(0, 6.28), 5, rr, bumps=0.25)


LEAF_UV = None


def leaf_uv(name):
    import importlib.util, os
    cells = {'zelkova': (0, 0, 1, 1), 'zelkova2': (1, 0, 1, 1), 'cherry': (2, 0, 1, 1), 'fig': (3, 0, 1, 1),
             'jungle': (0, 1, 1, 1), 'fern': (1, 1, 1, 1), 'reed': (2, 1, 1, 1), 'lily': (3, 1, 1, 1),
             'vine': (0, 2, 1, 2), 'vine2': (1, 2, 1, 2), 'ivy': (2, 2, 1, 1), 'grass': (3, 2, 1, 1),
             'shrub': (2, 3, 1, 1), 'bamboo': (3, 3, 1, 1)}
    cx, cy, w, h = cells[name]
    u0 = cx / 4 + 0.004; u1 = (cx + w) / 4 - 0.004
    v1 = 1 - cy / 4 - 0.004; v0 = 1 - (cy + h) / 4 + 0.004
    return u0, v0, u1, v1


def _card(b, p, d, size, kind, rr, upright=False):
    u0, v0, u1, v1 = leaf_uv(kind)
    if upright:
        a = rr.uniform(0, math.pi)
        t = np.array([math.cos(a), math.sin(a), 0.0])
        up = np.array([0, 0, 1.0])
        q = [p - t * size / 2, p + t * size / 2, p + t * size / 2 + up * size, p - t * size / 2 + up * size]
    else:
        n1, n2 = lib.frame_from(d)
        q = [p + (-n1 - n2) * size / 2, p + (n1 - n2) * size / 2, p + (n1 + n2) * size / 2, p + (-n1 + n2) * size / 2]
    nn = norm(d) if not upright else np.array([0, 0, 1.0])
    b.poly(q, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normals=[nn] * 4, colors=[(0.8, 0.8, 0.8, 1)] * 4)
