"""風神 Fūjin and 雷神 Raijin (Kamakura, mid-13th c.) — traced from the temple's 2x photographs
(refs/sanjusangendo/official/fujinraijin/2x/img01.jpg 風神, img02.jpg 雷神, 1274x1542) with the Commons photographs
(refs/sanjusangendo/commons_fujinraijin: front three-quarter, from below, the Meiji full views of the cloud bases) for
depth.  Reference only.

Tracing: X = (CX - px) / K (statue's right = viewer's left), Z = (SOLE - py) / K + CZ, where SOLE is the cloud surface
under the figure in the photo and CZ the top of the cloud pedestal in the model.  像高 111.5 cm (風神), 100.0 cm (雷神)."""
import math
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from . import statues_wood as W
from .statues_sdf import (Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff, Displace, Tube, Loft,
                          Field, frame, rot, euler, nrm, fbm, Offset)
from .statues_body import L, A, Band, Sweep, spline
from .statues_narayana import head_surf, front_y, Proj

REF = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/fujinraijin/2x/img0{}.jpg'

class Tr:
    """photo px -> statue metres for one figure"""
    def __init__(self, K, CX, SOLE, CZ): self.K, self.CX, self.SOLE, self.CZ = K, CX, SOLE, CZ
    def __call__(self, px, py, y=0.0):
        return A((self.CX - px) / self.K, y, (self.SOLE - py) / self.K + self.CZ)

# ---------------------------------------------------------------------------------------------- heads
DEMON_BASE = [((0, -0.06, 0.1), (0.34, 0.4, 0.38)), ((0, 0.14, -0.08), (0.35, 0.29, 0.34)), ((0, 0.12, -0.3), (0.34, 0.26, 0.21)), ((0, 0.27, -0.43), (0.16, 0.11, 0.09))]

def demon_head(f, R, O, u, kind='fujin'):
    """the demon heads: a broad face, brows like ridges of muscle, bulging round crystal eyes, a wide nose with flared
    nostrils, the mouth open with fangs; Fūjin's upper lip juts like a bill; pointed ears"""
    P = lambda v: O + R @ (A(*v) * u)
    hs = lambda x, z: head_surf(x, z, DEMON_BASE)
    def Q(x, z, prot, ry): return (x, hs(x, z) + prot - ry, z)
    E = lambda c, r, k=None: Ellipsoid(P(c), A(*r) * u, R if k is None else R @ k)
    def Tq(pts, rad, prot): return Tube([P(Q(x, z, p, r)) for (x, z), r, p in zip(pts, rad, prot)], np.asarray(rad, float) * u)
    Lb = L['skin']
    for (c, r) in DEMON_BASE:
        f.add(E(c, r), Lb, 0.08 * u)
    for s in (1, -1):
        f.add(E(Q(s * 0.23, -0.03, 0.05, 0.07), (0.1, 0.07, 0.075)), Lb, 0.05 * u)             # cheekbones
        f.add(E(Q(s * 0.19, -0.16, 0.07, 0.07), (0.085, 0.07, 0.08)), Lb, 0.04 * u)            # bunched cheeks
        # brows: thick ridges sweeping up and out
        f.add(Tq([(s * 0.36, 0.14), (s * 0.27, 0.15), (s * 0.15, 0.12), (s * 0.05, 0.06)], (0.035, 0.05, 0.055, 0.045), (0.03, 0.08, 0.1, 0.08)), Lb, 0.03 * u)
        f.add(E(Q(s * 0.09, 0.19, 0.06, 0.04), (0.07, 0.04, 0.05), rot((0, 1, 0), -s * 0.5)), Lb, 0.03 * u)
        # eyes: big round bulging eyeballs with crystal irises, rimmed by heavy lids
        f.sub(E(Q(s * 0.16, 0.02, 0.12, 0.08), (0.11, 0.08, 0.08)), 0.02 * u)
        ey = hs(s * 0.16, 0.02)
        ec = P((s * 0.16, ey - 0.035, 0.02))
        f.add(Sphere(ec, 0.085 * u), L['eyew'], 0.004 * u)
        f.paint(Sphere(ec + R @ A(-s * 0.01, 0.075, 0.0) * u, 0.058 * u), L['eye'])
        f.add(Torus(ec + R @ A(0, 0.03, 0.005) * u, 0.083 * u, 0.018 * u, R @ frame(z=(0, 1, 0.15), x=(1, 0, 0))), Lb, 0.012 * u)
        # nasolabial bulges, jowls
        f.add(Tq([(s * 0.14, -0.13), (s * 0.21, -0.25)], (0.04, 0.035), (0.08, 0.05)), Lb, 0.03 * u)
        # pointed ears
        f.add(E((s * 0.37, -0.02, 0.0), (0.035, 0.11, 0.17), rot((0, 0, 1), s * 0.3) @ rot((0, 1, 0), -s * 0.4)), Lb, 0.02 * u)
        f.add(RCone(P((s * 0.4, -0.06, 0.1)), P((s * 0.55, -0.15, 0.26)), 0.04 * u, 0.008 * u), Lb, 0.02 * u)
        f.sub(E((s * 0.405, 0.0, 0.0), (0.02, 0.06, 0.1), rot((0, 1, 0), -s * 0.4)), 0.01 * u)
    # forehead knots and the furrow between the brows
    f.add(Tq([(0, 0.1), (0, 0.2), (0, 0.3)], (0.035, 0.035, 0.025), (0.06, 0.04, 0.02)), Lb, 0.03 * u)
    for zz in (0.24, 0.31):
        f.sub(Tq([(-0.2, zz - 0.02), (0, zz), (0.2, zz - 0.02)], (0.008, 0.01, 0.008), (0.035, 0.045, 0.035)), 0.008 * u)
    # nose: short, very broad, flared
    f.add(RCone(P(Q(0, 0.03, 0.07, 0.035)), P(Q(0, -0.12, 0.15, 0.05)), 0.035 * u, 0.05 * u), Lb, 0.03 * u)
    for s in (1, -1):
        f.add(E(Q(s * 0.085, -0.15, 0.12, 0.05), (0.06, 0.05, 0.05)), Lb, 0.03 * u)
        f.sub(E(Q(s * 0.055, -0.18, 0.15, 0.03), (0.03, 0.032, 0.016)), 0.006 * u)
    # mouth
    zm = -0.29
    my = hs(0, zm) + 0.06
    if kind == 'fujin':      # the upper lip juts forward like a bill over the open mouth
        f.add(E((0, my + 0.02, zm + 0.06), (0.16, 0.08, 0.045)), L['lip'], 0.03 * u)
        f.add(E((0, my + 0.0, zm - 0.085), (0.13, 0.06, 0.04)), L['lip'], 0.03 * u)
        f.sub(Box(P((0, my - 0.03, zm - 0.01)), A(0.12, 0.12, 0.045) * u, R, 0.035 * u), 0.012 * u, lab=L['mouth'])
    else:                    # Raijin: a wide open snarl, the corners pulled back
        f.add(E((0, my - 0.02, zm), (0.19, 0.08, 0.12)), Lb, 0.04 * u)
        f.sub(Box(P((0, my + 0.02, zm)), A(0.15, 0.12, 0.06) * u, R, 0.045 * u), 0.012 * u, lab=L['mouth'])
        f.add(Tube(spline([P((-0.17, my - 0.03, zm)), P((-0.09, my + 0.01, zm + 0.07)), P((0, my + 0.02, zm + 0.08)), P((0.09, my + 0.01, zm + 0.07)), P((0.17, my - 0.03, zm))], 14), np.full(14, 0.02) * u), L['lip'], 0.012 * u)
        f.add(Tube(spline([P((-0.17, my - 0.03, zm)), P((-0.09, my + 0.0, zm - 0.075)), P((0, my + 0.01, zm - 0.085)), P((0.09, my + 0.0, zm - 0.075)), P((0.17, my - 0.03, zm))], 14), np.full(14, 0.024) * u), L['lip'], 0.012 * u)
    mw = 0.11 if kind == 'fujin' else 0.14
    zt = zm + (0.025 if kind == 'fujin' else 0.035); zb = zm - (0.045 if kind == 'fujin' else 0.05)
    f.add(Box(P((0, my - 0.06, zt)), A(mw * 0.85, 0.02, 0.015) * u, R, 0.005 * u), L['teeth'], 0.003 * u)
    f.add(Box(P((0, my - 0.065, zb)), A(mw * 0.75, 0.02, 0.013) * u, R, 0.005 * u), L['teeth'], 0.003 * u)
    for s in (1, -1):        # fangs, up and down
        f.add(RCone(P((s * mw * 0.75, my - 0.05, zt + 0.01)), P((s * mw * 0.72, my - 0.04, zm - 0.04)), 0.02 * u, 0.004 * u), L['teeth'], 0.0)
        f.add(RCone(P((s * mw * 0.55, my - 0.055, zb - 0.01)), P((s * mw * 0.6, my - 0.045, zm + 0.04)), 0.018 * u, 0.004 * u), L['teeth'], 0.0)
    f.add(E((0, my - 0.17, zm - 0.02), (0.08, 0.1, 0.03)), L['mouth'], 0.02 * u)
    # chin
    f.add(E(Q(0, -0.44, 0.03, 0.06), (0.12, 0.06, 0.06)), Lb, 0.04 * u)

def fujin_hair(f, R, O, u, rng):
    """風神's hair: thick curling locks springing up and back from the crown, two small horns among them"""
    P = lambda v: O + R @ (A(*v) * u)
    f.add(Inter([Ellipsoid(P((0, -0.06, 0.12)), A(0.37, 0.43, 0.41) * u, R), Plane(P((0, 0.36, 0.3)), R @ nrm(A(0, 0.35, -0.9)))], 0.02 * u), L['hair'], 0.02 * u)
    for i in range(22):
        a = rng.uniform(-1.9, 1.9); e = rng.uniform(0.15, 1.15)
        c = P((0.43 * math.sin(a) * math.cos(e * 0.55), -0.05 + 0.33 * math.cos(a) * math.cos(e * 0.6) - 0.08, 0.15 + 0.4 * math.sin(e)))
        out = R @ nrm(A(math.sin(a), 0.4 * math.cos(a) - 0.3, 0.7 + 0.4 * e))
        side = nrm(np.cross(out, R[:, 2])) if abs(out @ R[:, 2]) < 0.95 else R[:, 0]
        r0 = rng.uniform(0.05, 0.08); dirn = 1 if rng.random() < 0.5 else -1
        pts = [c + out * r0 * 1.2 * t * u + (side * math.cos(dirn * t * 4.2) + out * math.sin(dirn * t * 4.2)) * r0 * (1 - 0.6 * t) * u for t in np.linspace(0, 1, 12)]
        f.add(Tube(pts, np.linspace(0.042, 0.016, 12) * u), L['hair'], 0.02 * u)
    for k in range(13):          # a row of curls along the hairline hides the edge of the hair mass
        a = -1.5 + 3.0 * k / 12
        c = P((0.38 * math.sin(a), -0.05 + 0.42 * math.cos(a), 0.3 + 0.05 * math.cos(a) - 0.12 * abs(math.sin(a))))
        out = R @ nrm(A(math.sin(a), math.cos(a), 0.3)); side = nrm(np.cross(out, R[:, 2]))
        dirn = 1 if k % 2 else -1
        pts = [c + (side * math.cos(dirn * t * 4.5) + R[:, 2] * math.sin(dirn * t * 4.5)) * 0.05 * (1 - 0.6 * t) * u + out * 0.02 * u for t in np.linspace(0, 1, 10)]
        f.add(Tube(pts, np.linspace(0.04, 0.015, 10) * u), L['hair'], 0.015 * u)
    for s in (1, -1):
        b = P((s * 0.17, 0.14, 0.42))
        f.add(Tube([b, b + R @ A(s * 0.06, 0.03, 0.14) * u, b + R @ A(s * 0.02, -0.02, 0.25) * u], A(0.055, 0.035, 0.008) * u), L['skin'], 0.03 * u)

def raijin_hair(f, R, O, u, rng):
    """雷神's hair: stiff flame-like spikes standing straight up and fanning out, a short horn in front"""
    P = lambda v: O + R @ (A(*v) * u)
    f.add(Inter([Ellipsoid(P((0, -0.06, 0.12)), A(0.37, 0.43, 0.41) * u, R), Plane(P((0, 0.36, 0.3)), R @ nrm(A(0, 0.35, -0.9)))], 0.02 * u), L['hair'], 0.02 * u)
    for row, (rr, zz, n, L0) in enumerate(((0.3, 0.35, 11, 0.62), (0.2, 0.45, 9, 0.78), (0.1, 0.5, 5, 0.85))):
        for i in range(n):
            a = -1.35 + 2.7 * (i + 0.5 * (row % 2)) / max(n - 1, 1)
            base = P((rr * math.sin(a) * 1.2, -0.05 + rr * math.cos(a) * 0.6 - 0.05 * row, zz))
            out = R @ nrm(A(math.sin(a) * 0.55, -0.12 - 0.08 * row, 1.0))
            ln = L0 * (1 - 0.25 * abs(math.sin(a))) * rng.uniform(0.9, 1.1)
            wig = R @ A(math.cos(a), -math.sin(a), 0) * 0.035
            pts = [base + (out * ln * t + wig * math.sin(t * 7 + i)) * u for t in np.linspace(0, 1, 9)]
            f.add(Sweep(pts, np.linspace(0.07, 0.006, 9) * u, 0.022 * u, [R @ A(math.cos(a), -math.sin(a), 0)] * 9), L['hair'], 0.02 * u)
    for k in range(15):
        a = -1.55 + 3.1 * k / 14
        c = P((0.37 * math.sin(a), -0.05 + 0.41 * math.cos(a), 0.3 + 0.05 * math.cos(a) - 0.12 * abs(math.sin(a))))
        out = R @ nrm(A(math.sin(a) * 0.6, math.cos(a) * 0.5, 1.0))
        f.add(Tube([c, c + out * 0.07 * u, c + out * 0.12 * u + R @ A(0.02 * math.sin(k), 0, 0) * u], A(0.04, 0.025, 0.006) * u), L['hair'], 0.015 * u)
    f.add(RCone(P((0, 0.25, 0.4)), P((0.0, 0.38, 0.62)), 0.045 * u, 0.008 * u), L['skin'], 0.03 * u)

# ---------------------------------------------------------------------------------------------- pedestal
def cloud_column(f, rng, cz, tail, tr, tail_pts, lab='cloud', w=0.62, d=0.5):
    """the carved cloud pedestal of the photographs: a gnarled, striated column flaring up into a churning mass of
    scrolling cloud curls that overhangs it, and a flame-like cloud tail rising at the back"""
    seed = int(rng.integers(0, 999))
    def strata(P):
        Q = P * np.array([1.0, 1.0, 0.35], np.float32)
        ridge = 1.0 - np.abs(fbm(Q, 0.06, 3, seed + 4))
        return (0.025 * fbm(P * np.array([1, 1, 0.5], np.float32), 0.12, 3, seed) + 0.016 * ridge ** 3).astype(np.float32)
    zt = cz - 0.2
    col = Union([RCone(A(0.0, 0.0, 0.0), A(0.03, -0.01, zt * 0.6), w * 0.4, w * 0.3), RCone(A(0.03, -0.01, zt * 0.6), A(0.0, 0.0, zt), w * 0.3, w * 0.52),
                 Ellipsoid(A(0.06, -0.04, zt * 0.4), A(w * 0.36, d * 0.34, zt * 0.3)), Ellipsoid(A(-0.08, 0.04, zt * 0.25), A(w * 0.3, d * 0.3, zt * 0.25)),
                 Ellipsoid(A(0.0, 0.0, 0.06), A(w * 0.55, d * 0.5, 0.08))], 0.12)
    for i in range(5):          # buttress ribs running up into the cloud cap
        a = 2 * math.pi * (i + rng.uniform(-0.2, 0.2)) / 5
        b0 = A(math.cos(a) * w * 0.42, math.sin(a) * d * 0.4, 0.05); b1 = A(math.cos(a) * w * 0.3, math.sin(a) * d * 0.3, zt * 0.55)
        b2 = A(math.cos(a + 0.3) * w * 0.5, math.sin(a + 0.3) * d * 0.48, zt * 0.95)
        f.add(Tube([b0, b1, b2], [0.06, 0.04, 0.05]), L[lab], 0.06)
    f.add(Displace(col, strata, 0.045), L[lab], 0.0)
    for i in range(6):          # hollows and root-like ribs on the column
        a = rng.uniform(0, 2 * math.pi); z = rng.uniform(0.1, zt - 0.1)
        p = A(math.cos(a) * w * 0.48, math.sin(a) * d * 0.45, z)
        f.sub(Ellipsoid(p, A(0.05, 0.05, rng.uniform(0.06, 0.14)), rot((0, 0, 1), a)), 0.02)
        q = A(math.cos(a + 0.4) * w * 0.47, math.sin(a + 0.4) * d * 0.44, z)
        f.add(Capsule(q - A(0, 0, 0.12), q + A(0, 0, 0.12), 0.03), L[lab], 0.04)
    # the cloud mass: a churning cap of low lumps carrying scroll rosettes round its rim and over its top
    f.add(Ellipsoid(A(0.0, 0.0, cz - 0.09), A(w * 0.62, d * 0.62, 0.1)), L[lab], 0.06)
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.15, 0.4)
        p = A(math.cos(a) * r * w / 0.62, math.sin(a) * r * 0.8 * d / 0.5, cz - rng.uniform(0.04, 0.16))
        f.add(Ellipsoid(p, A(rng.uniform(0.06, 0.09), rng.uniform(0.05, 0.08), rng.uniform(0.035, 0.06))), L[lab], 0.04)
    def rosette(c, out, rad, dirn, turns=1.6):
        out = nrm(out); side = nrm(np.cross(out, A(0, 0, 1))) if abs(out[2]) < 0.95 else A(1, 0, 0); upv = np.cross(side, out)
        n = 22
        pts = [c + (side * math.cos(dirn * t * turns * 2 * math.pi) + upv * math.sin(dirn * t * turns * 2 * math.pi)) * rad * (1 - 0.82 * t) + out * rad * 0.25 * (1 - t) for t in np.linspace(0, 1, n)]
        f.add(Tube(pts, np.linspace(0.34, 0.12, n) * rad), L[lab], 0.15 * rad)
        f.add(Ellipsoid(c - out * rad * 0.35, A(rad, rad, rad * 0.55), frame(z=out, x=side)), L[lab], 0.3 * rad)
    for i in range(26):
        a = 2 * math.pi * (i + rng.uniform(-0.25, 0.25)) / 26
        rim = 0.47 if i % 2 else 0.4
        z = cz - rng.uniform(0.04, 0.2)
        c = A(math.cos(a) * rim * w / 0.62, math.sin(a) * rim * 0.85 * d / 0.5, z)
        rosette(c, A(math.cos(a), math.sin(a), rng.uniform(0.0, 0.7)), rng.uniform(0.045, 0.075), 1 if rng.random() < 0.5 else -1)
    for i in range(7):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.08, 0.28)
        c = A(math.cos(a) * r * w / 0.62, math.sin(a) * r * 0.8 * d / 0.5, cz - 0.02)
        rosette(c, A(math.cos(a) * 0.3, math.sin(a) * 0.3, 1.0), rng.uniform(0.04, 0.06), 1 if rng.random() < 0.5 else -1)
    # the tail: a flame-like plume rising at the back
    pts = spline([tr(px, py, y) for (px, py, y) in tail_pts], 24)
    n = len(pts)
    rad = np.interp(np.linspace(0, 1, n), [0, 0.3, 0.8, 1.0], [0.07, 0.05, 0.025, 0.008])
    f.add(Tube(pts, rad), L[lab], 0.03)
    for k in range(3, n - 4, 4):        # flame licks off the plume
        p = pts[k]; d_ = nrm(pts[k + 1] - pts[k - 1]); side = nrm(np.cross(d_, A(0, 1, 0)))
        f.add(Tube([p, p + side * tail * 0.06 + d_ * 0.04, p + side * tail * 0.09 + d_ * 0.12], [rad[k] * 0.6, rad[k] * 0.4, 0.004]), L[lab], 0.015)

def claw_foot2(f, ankle, fdir, u, lab, toes_down=0.0):
    """a demon's foot: heel, a long sole, two big clawed toes gripping"""
    fd = nrm(np.asarray(fdir, float)); up = A(0, 0, 1) if abs(fd[2]) < 0.9 else A(0, 1, 0)
    up = nrm(up - fd * (up @ fd)); side = np.cross(fd, up)
    a = np.asarray(ankle, float)
    heel = a - up * 0.05 * u / 0.24 - fd * 0.04
    ball = a - up * 0.055 + fd * 0.12
    f.add(RCone(a, heel, 0.035, 0.032), L[lab], 0.015)
    f.add(Ellipsoid((heel + ball) / 2, A(0.05, 0.1, 0.035), frame(y=fd, z=up)), L[lab], 0.02)
    for o in (-0.025, 0.025):
        b = ball + side * o
        k1 = b + fd * 0.045 + up * 0.008
        tip = k1 + fd * 0.03 - up * (0.03 + toes_down)
        f.add(Tube([b, k1, tip], [0.022, 0.02, 0.016]), L[lab], 0.008)
        f.add(RCone(tip, tip + fd * 0.02 - up * 0.025, 0.012, 0.002), L['nail'], 0.004)

# ---------------------------------------------------------------------------------------------- figure builder
def demon_figure(kind):
    from .statues_build import Model
    rng = np.random.default_rng(7 if kind == 'fujin' else 8)
    if kind == 'fujin':
        tr = Tr(759.0, 680.0, 1010.0, 0.92)
        m = Model('fujin', '風神', 'Fujin, god of wind', budget=(150000, 30000, 4500), lift=0.0, figure_h=1.115)
        skin = (0.052, 0.055, 0.048)             # dark olive: the green of the paint is only a trace now
    else:
        tr = Tr(735.0, 650.0, 985.0, 0.85)
        m = Model('raijin', '雷神', 'Raijin, god of thunder', budget=(150000, 30000, 4500), lift=0.0, figure_h=1.0)
        skin = (0.06, 0.058, 0.054)
    m.slot = dict(slot=kind)
    m.photo = REF.format(1 if kind == 'fujin' else 2)
    m.pal = W.wood_palette(skin=skin, hair=(0.035, 0.03, 0.028), robe=(0.055, 0.047, 0.042), robe2=(0.06, 0.05, 0.044), robe3=(0.065, 0.054, 0.046),
                           scarf=(0.062, 0.052, 0.045), bag=(0.06, 0.056, 0.05), drum=(0.085, 0.07, 0.056), cloud=W.ROCK, rod=(0.045, 0.04, 0.035),
                           lip=(0.062, 0.055, 0.048), mouth=(0.04, 0.028, 0.024), teeth=(0.13, 0.115, 0.095), eyew=(0.095, 0.085, 0.07),
                           belt=(0.045, 0.04, 0.036), gold='gold', attr=(0.07, 0.06, 0.05), nail=(0.04, 0.035, 0.03))
    m.shade = True
    m.weather = W.wood_c0fn(7 if kind == 'fujin' else 8, 1.0)
    m.back_bias = 0.5
    m.check_views = ['q34', 'low', 'trace']
    m.trace = (tr.K, tr.CX, tr.SOLE, 1274, 1542)
    m.trace_z0 = tr.CZ
    m.dais_above_floor = 0.35
    cz = tr.CZ
    if kind == 'fujin':
        hh = 0.235
        S_R, S_L = tr(573, 455, 0.03), tr(764, 436, -0.06)
        E_R, E_L = tr(391, 468, -0.05), tr(855, 500, -0.12)
        fist_R = tr(545, 423, 0.17); hand_L = tr(891, 573, 0.03)
        H_R, H_L = tr(620, 725, -0.03), tr(700, 718, -0.02)
        K_R, K_L = tr(503, 925, 0.12), tr(773, 756, 0.3)
        A_R, A_L = tr(530, 958, -0.2), tr(785, 979, 0.22)
        foot_R, foot_L = A(0.1, -1.0, -0.6), A(-0.2, 1.0, 0.0)
        Oh = tr(700, 322, 0.05); Rh = rot((0, 0, 1), -0.35) @ rot((0, 1, 0), 0.08) @ rot((1, 0, 0), -0.32)
        Op = tr(660, 722, -0.05); Wc = tr(664, 620, 0.02)
        zc = nrm(A(0.02, 0.38, 1.0))
    else:
        hh = 0.215
        S_R, S_L = tr(470, 455, -0.02), tr(692, 471, -0.04)
        E_R, E_L = tr(334, 418, -0.08), tr(903, 545, -0.06)
        fist_R = tr(387, 285, 0.0); hand_L = tr(766, 539, 0.16)
        H_R, H_L = tr(590, 800, 0.0), tr(700, 800, -0.02)
        K_R, K_L = tr(460, 800, 0.28), tr(790, 932, 0.2)
        A_R, A_L = tr(520, 960, 0.15), tr(760, 945, -0.12)
        foot_R, foot_L = A(0.4, 1.0, 0.0), A(-0.1, -1.0, -0.5)
        Oh = tr(597, 470, 0.05); Rh = rot((0, 0, 1), -0.4) @ rot((0, 1, 0), 0.12) @ rot((1, 0, 0), -0.18)
        Op = tr(640, 800, -0.05); Wc = tr(650, 720, 0.02)
        zc = nrm(A(0.05, 0.3, 1.0))
    fdir_R = nrm(fist_R - E_R); W_R = fist_R - fdir_R * 0.05
    fdir_L = nrm(hand_L - E_L); W_L = hand_L - fdir_L * 0.05
    fig = Bd.Fig(1.6, 6.0, 'demon')
    fig.musc = 0.9; fig.hh = hh; fig.hhd = hh; fig.hs = 1.0
    fig.Rc = frame(x=nrm(S_R - S_L), z=zc)
    fig.Oc = (S_R + S_L) / 2 - fig.Rc @ A(0, -0.1 * hh, 0.5 * hh)
    fig.N = fig.Oc + fig.Rc @ A(0, -0.08 * hh, 0.6 * hh)
    fig.Op = Op; fig.Rp = frame(x=nrm(H_R - H_L), z=(0, 0, 1))
    fig.W = Wc; fig.Rw = frame(x=nrm(fig.Rp[:, 0] + fig.Rc[:, 0]), z=nrm(zc + A(0, 0, 1)))
    fig.Oh = Oh; fig.Rh = Rh
    arms = {'r': dict(S=S_R, E=E_R, W=W_R, s=1), 'l': dict(S=S_L, E=E_L, W=W_L, s=-1)}
    legs = {'r': dict(H=H_R, K=K_R, A=A_R, s=1, foot_dir=foot_R), 'l': dict(H=H_L, K=K_L, A=A_L, s=-1, foot_dir=foot_L)}
    fig.arm = {}; fig.leg = {}
    f = Field('body')
    Bd.add_body(f, fig, skin='skin')
    fig.arm, fig.leg = arms, legs
    Lb = L['skin']
    O, R = Oh, Rh
    # torso masses: a barrel chest, a big muscular belly (the lumpy abdomen of the photos)
    f.add(Ellipsoid(fig.Oc + fig.Rc @ A(0, 0.02, 0.0), A(0.17, 0.12, 0.15), fig.Rc), Lb, 0.05)
    f.add(Ellipsoid(fig.W + fig.Rw @ A(0, 0.03, 0.0), A(0.14, 0.12, 0.12), fig.Rw), Lb, 0.05)
    for a in arms.values():
        Bd.add_arm(f, fig, a, Lb, r_up=0.048, r_fore=0.042)
        ax = nrm(a['E'] - a['S'])
        f.add(Ellipsoid(a['S'] + (a['E'] - a['S']) * 0.5, A(0.05, 0.05, 0.1), frame(z=ax, x=(0, 1, 0) if abs(ax[1]) < 0.9 else (1, 0, 0))), Lb, 0.025)
        fa = nrm(a['W'] - a['E'])
        f.add(Ellipsoid(a['E'] + (a['W'] - a['E']) * 0.3, A(0.045, 0.04, 0.085), frame(z=fa, x=(0, 0, 1) if abs(fa[2]) < 0.9 else (1, 0, 0))), Lb, 0.02)
        f.add(Torus(a['W'] - fa * 0.02, 0.04, 0.008, frame(z=fa, x=(0, 0, 1) if abs(fa[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.004)     # bracelet
    for nm, g in legs.items():
        Hj, K, Ak = g['H'], g['K'], g['A']
        f.add(RCone(Hj, K, 0.085, 0.055), Lb, 0.05)
        f.add(RCone(K, Ak, 0.055, 0.032), Lb, 0.03)
        ax2 = nrm(Ak - K)
        f.add(Ellipsoid(K + (Ak - K) * 0.3 + np.cross(ax2, (1, 0, 0)) * 0.015, A(0.05, 0.05, 0.1), frame(z=ax2, x=(1, 0, 0))), Lb, 0.02)
        f.add(Sphere(K, 0.05), Lb, 0.02)
        claw_foot2(f, Ak, g['foot_dir'], hh, 'skin', toes_down=0.01 if np.asarray(g['foot_dir'])[2] < -0.3 else 0.0)
    # neck: short and thick
    f.add(RCone(fig.N - fig.Rc @ A(0, 0, 0.03), O + R @ A(0, -0.08, -0.3) * hh, 0.08, 0.07), Lb, 0.04)
    # relief: pectorals, the lumpy abdomen, serratus, ribs (projected onto the front)
    pj = Proj(f)
    def bump(c3, r, prot, k=0.01):
        y = front_y(f, c3[0], c3[2]) or c3[1]
        f.add(Ellipsoid(A(c3[0], y + prot - r[1], c3[2]), A(*r)), Lb, k)
    Rc, Oc, Rw = fig.Rc, fig.Oc, fig.Rw
    for s in (1, -1):
        bump(Oc + Rc @ A(s * 0.075, 0.1, 0.03), (0.07, 0.04, 0.05), 0.016, 0.02)
        for i in range(3):
            bump(fig.W + Rw @ A(s * 0.04, 0.1, 0.07 - 0.055 * i), (0.035, 0.03, 0.025), 0.008, 0.016)
        for i in range(3):
            bump(Oc + Rc @ A(s * 0.13, 0.06, -0.05 - 0.035 * i), (0.022, 0.02, 0.015), 0.006, 0.006)
    m.field(f, 0.0016, 46.0, lods=(0, 1))
    # ---- head (finest)
    g = Field('head')
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.03), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.08, 0.072), Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), Lb, 0.0)
    demon_head(g, R, O, hh, kind)
    (fujin_hair if kind == 'fujin' else raijin_hair)(g, R, O, hh, rng)
    m.field(g, 0.0007, 36.0, lods=(0, 1))
    # ---- drapery: short skirt with a belt, the scarf knotted at the chest
    from .statues_kannon import Over
    d = Field('drape')
    zb = Op[2] + 0.06
    knees = [K_R, K_L]
    hem_z = max(min(K_R[2], K_L[2]) + 0.06, Op[2] - 0.2)
    rows = [(hem_z - 0.02, Op[0], Op[1] + 0.03, 0.2, 0.17), (Op[2] - 0.05, Op[0], Op[1] + 0.01, 0.17, 0.14), (zb, Op[0], Op[1], 0.15, 0.12)]
    def hem(th): return (hem_z + 0.03 * np.cos(5 * th + 0.4) - 0.04 * np.clip(-np.sin(th), 0, 1)).astype(np.float32)
    def sk(P):
        th = np.arctan2(P[:, 1] - Op[1], P[:, 0] - Op[0])
        return (-0.01 * np.cos(9 * th + 8 * P[:, 2])).astype(np.float32)
    d.add(Over(rows, hem, sk), L['robe'], 0.02)
    d.add(Band(A(Op[0], Op[1], zb), 0.155, 0.125, 0.02, 0.022, fig.Rp), L['belt'], 0.01)
    for nm, g_ in legs.items():         # the skirt over each thigh to above the knee
        tube = Tube([g_['H'] + A(0, 0, 0.04), g_['H'] + (g_['K'] - g_['H']) * 0.6], [0.1, 0.085])
        d.add(Displace(tube, sk, 0.01), L['robe'], 0.02)
    # the scarf: over both shoulders, crossing and knotted on the breastbone, the ends hanging (kept clear of the face)
    knot = Oc + Rc @ A(0, 0.16, -0.01)
    d.add(Ellipsoid(knot, A(0.032, 0.022, 0.026), Rc), L['scarf'], 0.01)
    for s in (1, -1):
        sh = S_R if s > 0 else S_L
        d.add(Sweep(spline([knot, knot + Rc @ A(s * 0.06, 0.0, 0.04), sh + Rc @ A(-s * 0.03, 0.05, -0.0), sh + Rc @ A(s * 0.02, -0.06, 0.01)], 10),
                    np.full(10, 0.02), 0.005, [Rc @ nrm(A(0, 1, 0.3))] * 10), L['scarf'], 0.008)
        d.add(Tube([knot, knot + Rc @ A(s * 0.05, 0.01, -0.05), knot + Rc @ A(s * 0.06, 0.02, -0.11)], [0.018, 0.015, 0.01]), L['scarf'], 0.01)
    m.field(d, 0.0016, 18.0, lods=(0, 1))
    # ---- the wind bag / the drums (SDF, fine)
    if kind == 'fujin':
        bf = Field('bag')
        bag = [(470, 528, 0.13), (520, 475, 0.16), (545, 423, 0.18), (500, 360, 0.12), (445, 280, 0.05), (432, 205, -0.02), (480, 156, -0.08), (573, 139, -0.13),
               (680, 153, -0.16), (790, 206, -0.13), (875, 300, -0.08), (918, 420, -0.03), (918, 520, 0.0), (891, 573, 0.03), (900, 640, 0.06), (910, 700, 0.08)]
        pts = spline([tr(px, py, y) for (px, py, y) in bag], 70)
        tt = np.linspace(0, 1, len(pts))
        rad = np.interp(tt, [0.0, 0.06, 0.13, 0.25, 0.5, 0.75, 0.85, 0.89, 0.95, 1.0], [0.06, 0.06, 0.035, 0.085, 0.092, 0.08, 0.06, 0.03, 0.045, 0.03])
        def wrinkles(P):
            return (0.004 * fbm(P, 0.12, 2, 9) + 0.0035 * np.sin(fbm(P * np.array([1, 1, 2.5], np.float32), 0.2, 2, 3) * 18)).astype(np.float32)
        bf.add(Displace(Tube(pts, rad), wrinkles, 0.008), L['bag'], 0.0)
        nb = len(pts) - 1
        for k in (int(0.13 * nb), int(0.89 * nb)):      # the ties at the necks
            dd = nrm(pts[min(k + 1, nb)] - pts[k - 1])
            bf.add(Torus(pts[k], rad[k] + 0.006, 0.008, frame(z=dd, x=np.cross(dd, (0, 1, 0)) if abs(dd[1]) < 0.9 else (1, 0, 0))), L['rod'], 0.004)
        for k in range(6):          # the gathered cloth at the lower end, flaring out
            a = 2 * math.pi * k / 6
            e = pts[-1]; dd = nrm(pts[-1] - pts[-3])
            o = nrm(np.cross(dd, A(math.cos(a), math.sin(a), 0)))
            bf.add(Sweep([e - dd * 0.02, e + dd * 0.03 + o * 0.03, e + dd * 0.06 + o * 0.05], A(0.018, 0.02, 0.012), 0.004, [np.cross(dd, o)] * 3), L['bag'], 0.006)
        m.field(bf, 0.0016, 22.0, lods=(0, 1))
    else:
        df = Field('drums')
        cring = tr(650, 429, -0.16)
        rr = 0.444
        tilt = math.acos(min(1.0, (284 / 735) / rr))
        Rr = rot((1, 0, 0), -tilt) @ frame(x=(1, 0, 0), y=(0, 0, -1))      # ring plane: x right, ring 'up' tilted back
        def ring_pt(a): return cring + Rr @ A(rr * math.cos(a), rr * math.sin(a), 0)
        th = np.linspace(0, 2 * math.pi, 97)
        df.add(Tube([ring_pt(a) for a in th], np.full(97, 0.009)), L['rod'], 0.0)
        drums = [(508, 155), (734, 145), (908, 287), (976, 513), (887, 713), (445, 687), (339, 539), (324, 308)]
        for (px, py) in drums:
            p = tr(px, py)
            a = math.atan2(-(py - 429) / (284 / 735) / 735 * (284 / 735) / (284 / 735), (650 - px) / 735 / rr) if False else math.atan2((429 - py) / 284.0, (650 - px) / 326.0)
            c = ring_pt(a)
            tang = nrm(ring_pt(a + 0.01) - ring_pt(a - 0.01))
            ax = nrm(Rr @ A(0, 0, 1) * -1.0 + tang * 0.15)            # the drum faces forward, a little turned
            if ax[1] < 0: ax = -ax
            Rd = frame(z=ax, x=tang)
            d0 = c - ax * 0.022; d1 = c + ax * 0.022
            df.add(Cyl(d0, d1, 0.076, 0.012), L['drum'], 0.0)
            df.add(Torus(d1 - ax * 0.002, 0.07, 0.006, Rd), L['rod'], 0.002)          # the rims
            df.add(Torus(d0 + ax * 0.002, 0.07, 0.006, Rd), L['rod'], 0.002)
            df.add(Capsule(c - nrm(c - cring) * 0.05, c - nrm(c - cring) * 0.085, 0.007), L['rod'], 0.004)
        m.field(df, 0.0015, 22.0, lods=(0, 1))
    # ---- cloud pedestal
    cf = Field('cloud')
    if kind == 'fujin':
        tail_pts = [(360, 1000, -0.22), (300, 900, -0.25), (240, 820, -0.25), (200, 760, -0.22), (190, 700, -0.2), (210, 660, -0.2)]
        cloud_column(cf, rng, cz, 1, tr, tail_pts, w=0.7, d=0.55)
    else:
        tail_pts = [(900, 990, -0.25), (960, 900, -0.28), (1000, 820, -0.28), (1020, 750, -0.26), (1000, 700, -0.24), (970, 690, -0.24)]
        cloud_column(cf, rng, cz, -1, tr, tail_pts, w=0.68, d=0.55)
    cf.inter(Plane(A(0, 0, 0.0), A(0, 0, -1)))
    m.field(cf, 0.004, 22.0, lods=(0, 1))
    # ---- LOD2
    f2 = Field('lod2')
    f2.add(Ellipsoid(fig.Oc, A(0.18, 0.14, 0.2), fig.Rc), Lb, 0.04)
    f2.add(Ellipsoid(O, A(0.12, 0.13, 0.14)), L['hair'], 0.04)
    for a in arms.values(): f2.add(Tube([a['S'], a['E'], a['W']], [0.055, 0.048, 0.04]), Lb, 0.03)
    for g_ in legs.values(): f2.add(Tube([g_['H'], g_['K'], g_['A']], [0.09, 0.06, 0.04]), Lb, 0.03)
    f2.add(Box(A(0, 0, cz * 0.5), A(0.33, 0.27, cz * 0.5), None, 0.08), L['cloud'], 0.05)
    f2.add(Ellipsoid(A(0, 0, cz - 0.06), A(0.45, 0.36, 0.13)), L['cloud'], 0.05)
    if kind == 'fujin':
        f2.add(Tube(pts[::6], rad[::6]), L['bag'], 0.02)
    else:
        f2.add(Torus(cring, rr, 0.06, Rr), L['drum'], 0.0)
    m.field(f2, 0.01, 30.0, lods=(2,))
    # ---- hands: Fūjin four fingers, Raijin three, clawed
    nf = 4 if kind == 'fujin' else 3
    hxf = []
    for nm, a in arms.items():
        s = a['s']; fd = nrm(a['W'] - a['E'])
        back = nrm(np.cross(fd, A(0, 0, 1)) * s + A(0, -0.3, 0.3)) if abs(fd[2]) < 0.9 else A(s, 0, 0)
        hxf.append(Bd.hand_xf(a['W'], fd, back, s))
    m.instance('hand_claw', lambda: (Bd.hand_field('grip', 0.17, musc=1.0, fingers=nf, claws=True, lab='skin'), 0.001), 6.0, hxf)
    # ---- explicit: the scarf ends whipping in the wind; Raijin's drumsticks
    def xm_fn(q):
        xm = X.XM()
        n = 40 if q > 0.6 else 14
        if q > 0.15:
            if kind == 'fujin':
                ends = [[(600, 640, 0.1), (520, 660, 0.12), (440, 680, 0.1), (390, 700, 0.06), (360, 730, 0.02)],
                        [(760, 640, 0.06), (830, 680, 0.03), (880, 720, 0.0), (930, 760, -0.03)]]
            else:
                ends = [[(560, 660, 0.08), (480, 700, 0.06), (420, 740, 0.03), (380, 780, 0.0)],
                        [(740, 640, 0.06), (820, 700, 0.03), (880, 760, -0.02), (930, 800, -0.06)]]
            for e in ends:
                pts = spline([tr(px, py, y) for (px, py, y) in e], n)
                ups = [nrm(A(0.3 * math.sin(k * 0.3), 1.0, 0.6)) for k in range(len(pts))]
                X.ribbon(xm, pts, np.linspace(0.03, 0.022, len(pts)), 0.004, ups, 'scarf')
        if kind == 'raijin':
            for (W_, tip, back_) in ((W_R + fdir_R * 0.06, tr(366, 222, 0.02), 0.08), (W_L + fdir_L * 0.06, tr(720, 470, 0.25), 0.07)):
                dd = nrm(tip - W_)
                X.tube(xm, [W_ - dd * back_, tip], 0.011, 8 if q > 0.5 else 4, 'rod')
                X.lathe(xm, tip, [(0, -0.025), (0.022, -0.012), (0.026, 0.005), (0.02, 0.02), (0, 0.028)], 10 if q > 0.5 else 5, 'rod')
        return xm
    m.xm_fn = xm_fn
    m.face_z = O[2]
    m.closeups = [('face', O[2] + 0.02, 0.8, 0.25)]
    return m

def fujin(): return demon_figure('fujin')
def raijin(): return demon_figure('raijin')
