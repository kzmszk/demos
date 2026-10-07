"""風神 Fujin and 雷神 Raijin (Kamakura, mid-13th c.): muscular demons crouching on swirling clouds; Fujin with the
wind bag arched over his head, Raijin with a hoop of eight drums.  Their clouds trail inward (Fujin stands at the
north end and his cloud trails to his right, Raijin at the south end, his trails to his left)."""
import math
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from .statues_sdf import Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Displace, Tube, Loft, Field, frame, rot, euler, nrm, fbm
from .statues_body import L, A, Band, Sweep, spline

def demon_palette(skin, hair, robe, scarf, extra=None):
    from .statues_build import palette
    p = palette(skin=skin, skin2=tuple(int(c * 0.8) for c in skin), hair=hair, eye=('glass', (0, 0, 0)), eyew=(178, 165, 132), lip=tuple(int(c * 0.85) for c in skin),
                teeth=(185, 172, 140), mouth=(105, 38, 28), robe=robe, robe2=tuple(int(c * 0.85) for c in robe), lining=(120, 60, 40),
                scarf=scarf, bag=(66, 62, 52), drum=(104, 78, 60), cloud=(62, 58, 54), rod='wood_dark', jewel='gold', trim='gold',
                belt=(70, 55, 40), feather=hair, nail=(60, 50, 40) if False else (60, 50, 40), wood='wood_dark', dark='wood_dark', gold='gold', attr='wood_dark')
    if extra: p.update(extra)
    return p

def claw_foot(f, Ak, fdir, hh, lab, s, sole_z=None):
    """a demon's foot with two clawed toes"""
    fd = nrm(np.asarray(fdir, float) * A(1, 1, 0.3)); up = A(0, 0, 1); side = nrm(np.cross(fd, up))
    sz = Ak[2] - 0.22 * hh if sole_z is None else sole_z
    heel = A(Ak[0], Ak[1], sz + 0.1 * hh) - fd * 0.12 * hh
    toe = A(Ak[0], Ak[1], sz + 0.08 * hh) + fd * 0.55 * hh
    f.add(RCone(heel, Ak, 0.12 * hh, 0.14 * hh), L[lab], 0.05 * hh)
    f.add(Ellipsoid((heel + toe) / 2 + A(0, 0, 0.02 * hh), A(0.26, 0.42, 0.13) * hh, frame(y=fd, z=up)), L[lab], 0.07 * hh)
    for o in (-0.1, 0.1):
        b = toe + side * o * hh
        tip = b + fd * 0.22 * hh - up * 0.06 * hh
        f.add(Capsule(b, tip, 0.075 * hh), L[lab], 0.04 * hh)
        f.add(RCone(tip, tip + fd * 0.08 * hh - up * 0.06 * hh, 0.045 * hh, 0.008 * hh), L['nail'] if 'nail' in L else L[lab], 0.01 * hh)

def cloud_base(f, c, size, tail, rng, lab='cloud', h=0.18):
    """湧雲: a swirling cloud platform with scroll curls, a tail trailing (and rising) toward `tail` (+1 / -1 in x)"""
    c = np.asarray(c, float)
    f.add(Ellipsoid(c + A(0, 0, h * 0.45), A(size * 0.55, size * 0.42, h * 0.55)), L[lab], 0.04)
    for i in range(14):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.2, 0.55) * size
        p = c + A(math.cos(a) * r, math.sin(a) * r * 0.75, h * rng.uniform(0.35, 0.8))
        f.add(Sphere(p, size * rng.uniform(0.09, 0.15)), L[lab], 0.05)
    # tail
    for i in range(7):
        t = (i + 1) / 7
        p = c + A(tail * (0.45 + 0.65 * t) * size, -0.15 * size * t, h * (0.5 + 0.9 * t * t))
        f.add(Sphere(p, size * (0.16 - 0.1 * t)), L[lab], 0.05)
    # scroll curls (渦) on the front and top
    for i in range(9):
        a = rng.uniform(-2.6, -0.5) if i < 6 else rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.3, 0.5) * size
        cc = c + A(math.cos(a) * r, math.sin(a) * r * 0.78 + (0.05 if i < 6 else 0), h * rng.uniform(0.55, 0.95))
        out = nrm(A(math.cos(a), math.sin(a), 0.5)); side = nrm(np.cross(out, A(0, 0, 1)))
        rad = size * rng.uniform(0.06, 0.09); dirn = 1 if rng.random() < 0.5 else -1
        pts = []
        for k in range(14):
            t = k / 13; ang = dirn * t * 4.2
            rr = rad * (1 - 0.7 * t)
            pts.append(cc + (side * math.cos(ang) + A(0, 0, 1) * math.sin(ang)) * rr + out * rad * 0.4)
        f.add(Tube(pts, np.linspace(0.028, 0.012, 14) * size / 0.9), L[lab], 0.015)

def cloud_pedestal(f, rng, cz, tail):
    """the tall carved cloud pedestal of the photographs: a weathered column flaring upward into a dense mass of cloud
    scrolls that overhangs it, and a flame-like cloud tail rising at the back on the inner side"""
    from . import statues_wood as W
    seed = int(rng.integers(0, 999))
    def strata(P):
        Q = P * np.array([1.0, 1.0, 2.5], np.float32)
        return (0.025 * fbm(Q, 0.13, 3, seed) + 0.012 * (1 - np.abs(fbm(Q, 0.06, 2, seed + 4))) ** 3).astype(np.float32)
    col = Union([RCone(A(0, 0, 0.0), A(0, 0, cz - 0.25), 0.3, 0.38), Ellipsoid(A(0.05, -0.02, cz * 0.35), A(0.36, 0.32, cz * 0.35)),
                 Ellipsoid(A(-0.08, 0.04, cz * 0.7), A(0.4, 0.34, cz * 0.3))], 0.12)
    f.add(Displace(col, strata, 0.04), L['cloud'], 0.0)
    for i in range(16):                 # the cloud mass on top, overhanging the column
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.1, 0.5)
        p = A(math.cos(a) * r, math.sin(a) * r * 0.85, cz - rng.uniform(0.04, 0.18))
        f.add(Ellipsoid(p, A(rng.uniform(0.1, 0.17), rng.uniform(0.09, 0.14), rng.uniform(0.07, 0.11))), L['cloud'], 0.05)
    for i in range(16):                 # scroll curls (渦) all round the rim and on the front
        a = rng.uniform(-math.pi, math.pi); r = rng.uniform(0.38, 0.55)
        cc = A(math.cos(a) * r, math.sin(a) * r * 0.85, cz - rng.uniform(0.02, 0.2))
        out = nrm(A(math.cos(a), math.sin(a), 0.3)); side = nrm(np.cross(out, A(0, 0, 1)))
        rad = rng.uniform(0.045, 0.075); dirn = 1 if rng.random() < 0.5 else -1
        pts = [cc + (side * math.cos(dirn * t * 4.4) + A(0, 0, 1) * math.sin(dirn * t * 4.4)) * rad * (1 - 0.7 * t) + out * rad * 0.5 for t in np.linspace(0, 1, 14)]
        f.add(Tube(pts, np.linspace(0.03, 0.012, 14)), L['cloud'], 0.012)
    # the tail: a flame-like plume rising at the back, curling over at the top
    base = A(tail * 0.4, -0.22, cz - 0.2)
    path = [base + A(tail * (0.04 * t + 0.07 * math.sin(t * 3.0)), -0.05 * t, 0.62 * t) for t in np.linspace(0, 1, 9)]
    path += [path[-1] + A(-tail * 0.06 * math.sin(a), -0.01, 0.06 * math.cos(a) - 0.02) for a in np.linspace(0.6, 3.0, 5)]
    rad = np.r_[np.linspace(0.08, 0.035, 9), np.linspace(0.03, 0.012, 5)]
    f.add(Tube(path, rad), L['cloud'], 0.03)
    for k in range(4):        # flame licks off the plume
        p = path[2 + 2 * k]
        f.add(Tube([p, p + A(tail * 0.07, -0.02, 0.06), p + A(tail * 0.1, -0.02, 0.14)], A(0.03, 0.018, 0.004)), L['cloud'], 0.015)

def knot_scarf(f, xm_fn_list, fig, lab='scarf'):
    """the scarf knotted at the chest (both demons): an SDF knot; ribbons are explicit"""
    hh = fig.hh; Rc, Oc = fig.Rc, fig.Oc
    k = Oc + Rc @ A(0, 0.62, 0.35) * hh
    f.add(Ellipsoid(k, A(0.12, 0.08, 0.09) * hh, Rc), L[lab], 0.02 * hh)
    for s in (1, -1):
        f.add(Tube([k, k + Rc @ A(s * 0.25, 0.05, -0.25) * hh, k + Rc @ A(s * 0.3, 0.1, -0.55) * hh], A(0.07, 0.06, 0.03) * hh), L[lab], 0.02 * hh)
    return k

def demon(kind):
    from .statues_build import Model
    rng = np.random.default_rng(7 if kind == 'fujin' else 8)
    if kind == 'fujin':
        m = Model('fujin', '風神', 'Fujin, god of wind', budget=(80000, 16000, 2400), lift=0.0, figure_h=1.115)
        m.slot = dict(slot='fujin')
        m.photo = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/fujinraijin/img01.jpg'
        hh = 0.29; H = 5.3 * hh
        cz = 0.92        # top of the cloud pedestal
        fig = Bd.Fig(H, 5.3, 'demon', head_scale=1.22, neck=0.04, pelvis_z=cz + 0.46, leg_len=2.45, pelvis_rot=(0.12, 0.08, -0.3), chest_rot=(0.3, -0.06, 0.25),
                     head_rot=(0.05, 0.05, 0.42),
                     hand_r=(0.08, 0.22, cz + 0.88), elbow_r=(1, -0.3, -0.6), hand_l=(-0.42, 0.18, cz + 0.52), elbow_l=(-1, -0.4, 0.2),
                     foot_l=(-0.3, 0.3, cz + 0.07), knee_l=(-0.4, 1, 0.9), foot_r=(0.24, -0.42, cz + 0.1), knee_r=(0.25, 0.3, -1),
                     footdir_l=(-0.2, 1, 0), footdir_r=(0.3, -0.2, -0.8))
        fingers = 4; tail = 1
    else:
        m = Model('raijin', '雷神', 'Raijin, god of thunder', budget=(80000, 16000, 2400), lift=0.0, figure_h=1.0)
        m.slot = dict(slot='raijin')
        m.photo = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/fujinraijin/img02.jpg'
        hh = 0.27; H = 5.3 * hh
        cz = 0.85
        fig = Bd.Fig(H, 5.3, 'demon', head_scale=1.22, neck=0.04, pelvis_z=cz + 0.47, leg_len=2.45, pelvis_rot=(0.15, -0.05, 0.25), chest_rot=(0.2, 0.08, -0.12),
                     head_rot=(0.1, -0.05, 0.42),
                     hand_r=(0.42, 0.02, cz + 1.32), elbow_r=(1, -0.1, -0.7), hand_l=(-0.12, 0.3, cz + 0.8), elbow_l=(-1, -0.2, -0.6),
                     foot_r=(0.3, 0.3, cz + 0.07), knee_r=(0.35, 1, 0.5), foot_l=(-0.28, -0.42, cz + 0.1), knee_l=(-0.3, 0.2, -1),
                     footdir_r=(0.2, 1, 0), footdir_l=(-0.3, -0.2, -0.8))
        fingers = 3; tail = -1
    from . import statues_wood as W
    m.pal = W.wood_palette(skin=(0.06, 0.052, 0.046), hair=(0.035, 0.03, 0.028), robe=(0.055, 0.047, 0.042), robe2=(0.058, 0.05, 0.044),
                           scarf=(0.06, 0.05, 0.044), bag=(0.058, 0.05, 0.045), drum=(0.07, 0.058, 0.048), cloud=W.ROCK, rod=(0.04, 0.034, 0.03),
                           lip=(0.07, 0.05, 0.044), mouth=(0.05, 0.03, 0.026), teeth=(0.14, 0.12, 0.1), belt=(0.045, 0.04, 0.036))
    m.shade = True
    m.weather = W.wood_c0fn(7 if kind == 'fujin' else 8, 1.0)
    O, R = fig.Oh, fig.Rh
    f = Field('body')
    legs = fig.leg; fig.leg = {}
    Bd.add_body(f, fig, skin='skin')
    fig.leg = legs
    for nm, g in fig.leg.items():
        Bd.add_leg(f, fig, g, L['skin'], foot=False)
        fd = g['foot_dir']
        if nm == ('l' if kind == 'fujin' else 'r'):
            claw_foot(f, g['A'], fd, hh, 'skin', g['s'], sole_z=cz)
        else:   # kneeling leg: toes bent on the cloud behind
            claw_foot(f, g['A'], nrm(A(0, -1, -0.6)), hh * 0.95, 'skin', g['s'], sole_z=g['A'][2] - 0.25 * hh)
    # ribs and veins: a few ridges on the flanks
    for s in (1, -1):
        for i in range(3):
            f.add(Capsule(fig.Oc + fig.Rc @ A(s * 0.48, 0.25 - 0.05 * i, -0.15 - 0.18 * i) * hh, fig.Oc + fig.Rc @ A(s * 0.62, -0.05, -0.05 - 0.18 * i) * hh, 0.04 * hh), L['skin'], 0.04 * hh)
    # skirt (裙) round the hips, blown out, a belt, the knotted scarf
    Op = fig.Op
    def hem(th):
        return (Op[2] - 0.6 * hh + 0.12 * hh * np.cos(2 * th + 0.5) + 0.06 * hh * np.cos(5 * th)).astype(np.float32)
    def sk_fold(P):
        th = np.arctan2(P[:, 1] - Op[1], P[:, 0] - Op[0])
        return (-0.012 * np.cos(9 * th + 2.0 * P[:, 2] / hh)).astype(np.float32)
    from .statues_kannon import Over
    rows = [(Op[2] - 0.95 * hh, Op[0], Op[1], 0.95 * hh, 0.72 * hh), (Op[2] - 0.5 * hh, Op[0], Op[1], 0.82 * hh, 0.62 * hh),
            (Op[2] - 0.1 * hh, Op[0], Op[1] + 0.02, 0.7 * hh, 0.52 * hh), (Op[2] + 0.28 * hh, Op[0], Op[1] + 0.03, 0.62 * hh, 0.48 * hh)]
    f.add(Over(rows, hem, sk_fold), L['robe'], 0.02 * hh)
    f.add(Band(Op + A(0, 0.03, 0.22 * hh), 0.64 * hh, 0.5 * hh, 0.05 * hh, 0.07 * hh, fig.Rp), L['belt'], 0.01 * hh)
    knot = knot_scarf(f, None, fig)
    # head
    g = Field('head')
    hb = hh; hh = fig.hhd
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.15 * hb), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.36 * hb, 0.3 * hh),
                 Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), L['skin'], 0.0)
    Bd.add_head(g, R, O, hh, style='demon', fierce=1.0, mouth='open', ears='pointed', urna=False)
    if kind == 'fujin':
        Bd.add_hair(g, R, O, hh, 'curls', seed=3)
        for s in (1, -1):    # two small horns among the curls
            b = O + R @ A(s * 0.2, 0.1, 0.42) * hh
            g.add(Tube([b, b + R @ A(s * 0.08, 0.02, 0.18) * hh, b + R @ A(s * 0.04, -0.04, 0.3) * hh], A(0.07, 0.045, 0.01) * hh), L['skin'], 0.03 * hh)
        # the duck-bill-like pursed lips: a heavier upper lip
        g.add(Ellipsoid(O + R @ A(0, 0.4, -0.2) * hh, A(0.14, 0.06, 0.04) * hh, R), L['lip'], 0.02 * hh)
    else:
        Bd.add_hair(g, R, O, hh, 'flame', seed=5)
    m.field(g, 0.0011, 26.0, lods=(0, 1))
    hh = hb
    # wind bag / drum hoop as SDF + hands
    if kind == 'fujin':
        a_r = fig.arm['r']['W']; a_l = fig.arm['l']['W']
        e_r = a_r + nrm(a_r - fig.arm['r']['E']) * 0.09 * hh * 3
        e_l = a_l + nrm(a_l - fig.arm['l']['E']) * 0.09 * hh * 3
        bag = [e_r, e_r + A(0.05, -0.12, 0.14), A(0.22, -0.3, O[2] + 0.1), A(0.12, -0.38, O[2] + 0.45 * hh + 0.22),
               A(-0.25, -0.36, O[2] + 0.4 * hh + 0.14), A(-0.52, -0.22, O[2] - 0.05), e_l + A(-0.06, -0.04, 0.22), e_l]
        bp = spline(bag, 30)
        rad = 0.045 + 0.1 * np.sin(np.linspace(0, math.pi, len(bp))) ** 0.6
        rad[:2] = 0.035; rad[-2:] = 0.035
        def wrinkle(P): return (0.008 * fbm(P, 0.07, 2, 9)).astype(np.float32)
        f.add(Displace(Tube(bp, rad), wrinkle, 0.009), L['bag'], 0.01)
        for e in (e_r, e_l):
            f.add(Torus(e, 0.04, 0.012, frame(z=(0, 0, 1), x=(1, 0, 0))), L['rod'], 0.004)
    m.field(f, 0.0026, 44.0, lods=(0, 1))
    cf = Field('cloud')
    cloud_pedestal(cf, rng, cz, tail)
    cf.inter(Plane(A(0, 0, 0.0), A(0, 0, -1)))          # flat underside on the origin plane
    m.field(cf, 0.0045, 14.0, lods=(0, 1))
    # LOD2: one field
    f2 = Field('lod2')
    fig.leg = legs; Bd.add_body(f2, fig, skin='skin')
    f2.add(Ellipsoid(O + R @ A(0, 0, 0.05) * hh, A(0.45, 0.5, 0.55) * hh, R), L['skin'], 0.05)
    f2.add(Box(A(0.0, 0, cz * 0.5), A(0.36, 0.3, cz * 0.5), None, 0.08), L['cloud'], 0.05)
    f2.add(Ellipsoid(A(0.02 * tail, 0, cz - 0.05), A(0.55, 0.42, 0.14)), L['cloud'], 0.05)
    f2.add(Capsule(A(tail * 0.4, -0.2, cz - 0.1), A(tail * 0.55, -0.25, cz + 0.6), 0.08), L['cloud'], 0.05)
    if kind == 'fujin': f2.add(Tube(bp, rad), L['bag'], 0.02)
    f2.inter(Plane(A(0, 0, 0.0), A(0, 0, -1)))
    m.field(f2, 0.01, 30.0, lods=(2,))
    # hands
    xfs = []
    for nm, a in fig.arm.items():
        s = a['s']; ax = nrm(a['W'] - a['E'])
        back = nrm(np.cross(ax, A(0, 0, 1)) * s) if abs(ax[2]) < 0.9 else A(s, 0, 0)
        xfs.append(Bd.hand_xf(a['W'], ax, back, s))
    m.instance('hand_claw', lambda: (Bd.hand_field('grip', 0.68 * hh, musc=1.0, fingers=fingers, claws=True, lab='skin'), 0.68 * hh / 110), 3.0, xfs)
    # explicit: scarf ribbons, drum hoop + drums, drumsticks
    def xm_fn(q):
        xm = X.XM()
        if q > 0.2:
            for s in (1, -1):
                sh = fig.arm['r' if s > 0 else 'l']['S']
                pts = spline([knot + A(s * 0.03, 0, 0.02), sh + A(-s * 0.05, 0.05, 0.1), sh + A(0, -0.12, 0.08), sh + A(s * 0.15, -0.3, -0.05),
                              sh + A(s * 0.3, -0.42, -0.25), sh + A(s * 0.45, -0.38, -0.45)], 24 if q > 0.6 else 10)
                X.ribbon(xm, pts, 0.045, 0.006, [nrm(A(s * 0.4, 0.2, 1))] * len(pts), 'scarf')
            # skirt ends flying back
            for s in (1, -1):
                b = fig.Op + A(s * 0.12, 0.05, -0.1)
                pts = spline([b, b + A(s * 0.12, -0.15, -0.08), b + A(s * 0.25, -0.35, 0.0), b + A(s * 0.38, -0.5, 0.1)], 18 if q > 0.6 else 8)
                X.ribbon(xm, pts, np.linspace(0.07, 0.02, len(pts)), 0.006, [nrm(A(0, 0.3, 1))] * len(pts), 'robe2')
        if kind == 'raijin':
            # the hoop of eight drums (連鼓) behind the shoulders
            c = fig.Oc + A(0.0, -0.3, 0.08)
            Rr = 0.62
            th = np.linspace(0, 2 * math.pi, 61 if q > 0.5 else 25)
            tilt = rot((0, 1, 0), 0.12) @ rot((1, 0, 0), 0.25)
            ring = [c + tilt @ A(Rr * math.cos(t), 0, Rr * math.sin(t) * 1.08) for t in th]
            X.tube(xm, ring, 0.011, 6 if q > 0.5 else 4, 'rod', caps=False)
            for i in range(8):
                t = math.pi / 2 + 2 * math.pi * (i + 0.5) / 8
                p = c + tilt @ A(Rr * math.cos(t), 0, Rr * math.sin(t) * 1.08)
                tang = nrm(tilt @ A(-math.sin(t), 0, math.cos(t) * 1.08))
                ax = nrm(tilt @ A(0, 1, 0) + tang * (0.6 if i in (1, 6) else 0.0))
                seg = 16 if q > 0.5 else 8
                Rm = frame(z=ax, x=tang)
                prof = [(0.0, -0.045), (0.085, -0.045), (0.1, -0.03), (0.1, 0.03), (0.085, 0.045), (0.0, 0.045)]
                P = [];
                for (r_, z_) in prof:
                    for k in range(seg):
                        a = 2 * math.pi * k / seg
                        P.append(p + Rm @ A(r_ * math.cos(a), r_ * math.sin(a), z_))
                xm.add(P, X.grid_tris(seg, len(prof) - 1, wrap_u=True), 'drum')
            # drumsticks (桴) with ball ends
            for nm, a in fig.arm.items():
                W = a['W']; ax = nrm(W - a['E'])
                fist = W + ax * 0.08
                d = nrm(np.cross(ax, A(0, 1, 0.3)))
                X.tube(xm, [fist - d * 0.06, fist + d * 0.2], 0.012, 6 if q > 0.5 else 4, 'rod')
                X.lathe(xm, fist + d * 0.22, [(0, -0.03), (0.03, -0.02), (0.035, 0.0), (0.03, 0.02), (0, 0.035)], 8 if q > 0.5 else 5, 'rod')
        return xm
    m.xm_fn = xm_fn
    m.closeups = [('face', O[2] + 0.02, 0.8, 0.25), ('front', 0.6, 2.6, 0.0)]
    return m

def fujin(): return demon('fujin')
def raijin(): return demon('raijin')
