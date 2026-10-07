"""千手観音: the 1000 standing statues (three variants) and the seated 中尊 of 三十三間堂."""
import math
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from .statues_sdf import Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Displace, Tube, Loft, Field, frame, rot, euler, nrm, fbm
from .statues_body import L, A, Band, Sweep, spline

GOLD_PAL = None

def gold_palette():
    from .statues_build import palette
    return palette(skin='gold', hair=('cloth', (34, 38, 52)), eye='gold', lip='gold', robe='gold', robe2='gold', lining='gold',
                   scarf='gold', jewel='gold', crown='gold', ped='gold', ped2=('black_lacquer', (0, 0, 0)), petal='gold', halo='gold',
                   attr='gold', attr2='gold', worn='black_lacquer', rod='gold', gold='gold', dark='black_lacquer', base='black_lacquer',
                   sash='gold', belt='gold', eyew='gold', teeth='gold', mouth='gold', glass='glass')

class Over(S.Prim):
    """an over-skirt / apron: a loft whose lower hem height depends on the angle around the axis: hem(theta) -> z"""
    def __init__(self, rows, hem, folds=None):
        self.lo_ = Loft(rows); self.hem = hem; self.folds = folds
        self.lo = self.lo_.lo - 0.02; self.hi = self.lo_.hi + 0.02
        self.c = np.array([np.mean(np.asarray(rows)[:, 1]), np.mean(np.asarray(rows)[:, 2])])
    def d(self, P):
        d = self.lo_.d(P)
        th = np.arctan2(P[:, 1] - self.c[1], P[:, 0] - self.c[0])
        if self.folds is not None: d = d + self.folds(P)
        return np.maximum(d, self.hem(th) - P[:, 2])

def noise_patches(lo, hi, scale, thr, seed):
    lo = np.asarray(lo, np.float32); hi = np.asarray(hi, np.float32)
    def f(P):
        return (fbm(P, scale, 3, seed) - thr).astype(np.float32) * -0.05
    return Fn(f, lo, hi)

# ---------------------------------------------------------------------------------------------- standing Kannon
def kannon_standing(variant='a'):
    from .statues_build import Model
    v = {'a': 0, 'b': 1, 'c': 2}[variant]
    rng = np.random.default_rng(11 + v * 7)
    m = Model(f'kannon_standing_{variant}', '千手観音立像', f'Standing Thousand-armed Kannon (variant {variant.upper()})',
              budget=(58000, 11600, 1800), lift=0.38, figure_h=1.66)
    m.pal = gold_palette()
    m.slot = dict(slot='kannon_standing', note='one of three variants for each of the 1000 (and kannon_rear_1001)')
    H = 1.43; heads = 6.1
    hh = H / heads
    head_rot = [(0.06, 0, 0), (0.1, 0.0, 0.03), (0.05, 0.0, -0.025)][v]
    fig = Bd.Fig(H, heads, 'bodhi', head_rot=head_rot, pelvis_rot=(0, 0, [0, 0.0, 0.0][v]),
                 hip_shift=[(0, 0), (0.006, 0), (-0.004, 0)][v],
                 hand_r=(0.032, 0.17, 0.985), hand_l=(-0.032, 0.17, 0.985), elbow_r=(1.0, -0.2, -0.9), elbow_l=(-1.0, -0.2, -0.9),
                 foot_r=(0.075, 0.03, 0.06), foot_l=(-0.075, 0.03, 0.06), footdir_r=(0.12, 1, 0), footdir_l=(-0.12, 1, 0))
    # ------------------------------------------------ body field
    f = Field('body')
    Bd.add_body(f, fig, skin='skin')
    # bowl arms (宝鉢手) from just behind the shoulders
    bowl_w = {}
    for nm, a in fig.arm.items():
        s = a['s']
        S0 = a['S'] + A(-s * 0.01, -0.035, -0.03)
        W = A(s * 0.055, 0.155, 0.735)
        E, W = Bd.ik2(S0, W, 1.28 * hh, 1.08 * hh, (s * 0.7, -0.3, -1))
        Bd.add_arm(f, fig, dict(S=S0, E=E, W=W, s=s), L['skin'], deltoid=False)
        bowl_w[nm] = (E, W)
        f.add(Torus(W + nrm(W - E) * 0.004, 0.026, 0.006, frame(z=nrm(W - E), x=(0, 0, 1))), L['jewel'], 0.003)
    for nm, a in fig.arm.items():   # bracelets + armlets on the prayer arms
        ax = nrm(a['W'] - a['E'])
        f.add(Torus(a['W'] + ax * 0.004, 0.027, 0.006, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.003)
        ax2 = nrm(a['E'] - a['S'])
        f.add(Torus(a['S'] + (a['E'] - a['S']) * 0.4, 0.05, 0.007, frame(z=ax2, x=(0, 1, 0) if abs(ax2[1]) < 0.9 else (1, 0, 0))), L['jewel'], 0.004)
    # side arms: two fans of 19
    side = []           # (s, root, elbow, wrist, pose, attr)
    poses = ['pinch', 'grip', 'cup', 'pinch', 'open', 'grip', 'mudra']
    attrs_all = ['jewel', 'wheel', 'disc', 'lotus', 'vase', 'sword', 'vajra', 'rosary', 'bell', 'skull', 'branch', 'conch',
                 'buddha', 'axe', 'arrow', 'bow', 'sutra', 'cloud', 'disc', 'jewel', 'rod', 'lotus', 'vase', 'wheel', 'trident',
                 'vajra', 'disc', 'bell', 'jewel', 'sword', 'lotus', 'rod', 'conch', 'rosary', 'branch', 'vase', 'disc', 'buddha']
    order = rng.permutation(len(attrs_all))
    k = 0
    for s in (1, -1):
        Hc = A(s * 0.15, -0.035, 1.03)
        R0 = A(s * 0.12, -0.085, 1.07)
        n = 19
        for i in range(n):
            layer = i % 3
            th = math.radians(14 + 140 * i / (n - 1) + rng.uniform(-4, 4) + (v - 1) * 3)
            rx, rz = 0.30 + 0.02 * (layer == 0) - 0.02 * (layer == 2), 0.29
            y = [0.035, -0.03, -0.09][layer]
            W = Hc + A(s * math.sin(th) * rx, y, math.cos(th) * rz) + rng.uniform(-0.01, 0.01, 3)
            root = R0 + A(0, -0.015 * layer, -0.1 * (i / n))
            E, W = Bd.ik2(root, W, 0.175, 0.16, (s * 0.25, -0.5, -1))
            pose = poses[(i + v) % len(poses)]
            att = attrs_all[order[k % len(order)]]; k += 1
            side.append((s, root, E, W, pose, att, th))
            f.add(RCone(root, E, 0.026, 0.021), L['skin'], 0.012)
            f.add(RCone(E, W, 0.02, 0.0145), L['skin'], 0.008)
            ax = nrm(W - E)
            f.add(Torus(W + ax * 0.003, 0.0165, 0.004, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.002)
        # the bundle of upper arms behind the shoulder
        f.add(Ellipsoid(A(s * 0.13, -0.09, 1.0), A(0.075, 0.06, 0.15)), L['skin'], 0.03)
    # skirt (裙) with folds, the folded-over top, an apron, the 天衣 swags are explicit ribbons
    hem_z = 0.008
    rows = [(hem_z, 0, 0.025, 0.165, 0.14), (0.05, 0, 0.018, 0.152, 0.122), (0.25, 0, 0.005, 0.142, 0.112), (0.45, 0, 0.0, 0.152, 0.118),
            (0.62, 0, -0.008, 0.172, 0.13), (0.72, 0, -0.012, 0.18, 0.135), (0.8, 0, -0.008, 0.172, 0.128)]
    def skfold(P):
        th = np.arctan2(P[:, 1], P[:, 0]); z = P[:, 2]
        front = np.clip(np.sin(th), 0, 1)
        w = np.clip((0.78 - z) / 0.6, 0, 1) ** 0.6
        return (-0.0055 * w * np.cos(13 * th + 2.0 * np.sin(z * 6)) - 0.0035 * w * front * np.cos(29 * th + z * 4)).astype(np.float32)
    f.add(Displace(Loft(rows), skfold, 0.009), L['robe'], 0.006)
    # feet poke out of the hem: hem lifted in front
    f.sub(Ellipsoid(A(0, 0.16, 0.0), A(0.13, 0.06, 0.05)), 0.02)
    f.add(Band(A(0, -0.008, 0.775), 0.178, 0.131, 0.007, 0.026), L['robe2'], 0.004)
    def apron_hem(th):
        return (0.52 + 0.17 * (1 - np.clip(np.sin(th), 0, 1)) ** 1.5 - 0.0).astype(np.float32)
    def apfold(P):
        th = np.arctan2(P[:, 1], P[:, 0]); z = P[:, 2]
        return (-0.004 * np.cos(9 * th + 1.0) * np.clip((0.79 - z) / 0.25, 0, 1)).astype(np.float32)
    f.add(Over([(0.48, 0, 0.0, 0.168, 0.128), (0.62, 0, -0.006, 0.185, 0.14), (0.72, 0, -0.01, 0.191, 0.145), (0.79, 0, -0.008, 0.182, 0.136)], apron_hem, apfold), L['robe2'], 0.004)
    # 条帛: a sash from the left shoulder across the chest to the right hip and round the back
    sash = spline([(-0.15, -0.02, 1.13), (-0.09, 0.105, 1.07), (0.0, 0.13, 0.97), (0.1, 0.11, 0.87), (0.15, 0.0, 0.83), (0.11, -0.11, 0.86), (0.0, -0.13, 0.95), (-0.1, -0.12, 1.07), (-0.15, -0.02, 1.13)], 26)
    ups = [nrm(p - A(0, -0.01, p[2])) for p in sash]
    f.add(Sweep(sash, 0.03, 0.005, ups), L['sash'], 0.004)
    # gilding worn through to the lacquer: patches on the skirt
    f.paint(Inter([noise_patches((-0.25, -0.2, 0), (0.25, 0.25, 0.8), 0.07, 0.36 + 0.04 * v, 5 + v), Offset_(Loft(rows), 0.012)]), L['worn'])
    m.field(f, 0.0028, 19.0, lods=(0, 1))
    # ------------------------------------------------ head field (fine)
    g = Field('head')
    R = fig.Rh; O = fig.Oh
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.15 * hh), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.27 * hh, 0.25 * hh),
                 Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), L['skin'], 0.0)
    Bd.add_head(g, R, O, hh, style='serene', ears='long', eyes='carved', urna=True,
                nose=[1.0, 0.6, 1.3][v], jaw=[1.0, 1.04, 0.97][v])
    Bd.add_hair(g, R, O, hh, 'bodhi')
    Bd.neck_folds(g, fig, 2)
    # crown band (宝冠台) + side ornaments
    P_ = lambda vv: O + R @ (A(*vv) * hh)
    g.add(Band(P_((0, -0.05, 0.25)), 0.366 * hh, 0.426 * hh, 0.016 * hh, 0.03 * hh, R @ rot((1, 0, 0), -0.08)), L['crown'], 0.004 * hh)
    for s in (1, -1):    # side rosettes of the crown + the bows of the crown ribbons
        g.add(Ellipsoid(P_((s * 0.37, 0.02, 0.26)), A(0.025, 0.075, 0.075) * hh, R), L['crown'], 0.008 * hh)
        g.add(Ellipsoid(P_((s * 0.36, -0.12, 0.22)), A(0.03, 0.05, 0.03) * hh, R), L['crown'], 0.008 * hh)
    g.add(Ellipsoid(P_((0, 0.385, 0.29)), A(0.055, 0.02, 0.06) * hh, R), L['crown'], 0.006 * hh)
    m.field(g, 0.0011, 17.0, lods=(0, 1))
    # ------------------------------------------------ LOD2: one coarse field (body, head mass, the two arm fans as plates)
    f2 = Field('lod2')
    Bd.add_body(f2, fig, skin='skin')
    f2.add(Loft(rows), L['robe'], 0.01)
    f2.add(Ellipsoid(O + R @ A(0, -0.04, 0.12) * hh, A(0.42, 0.48, 0.62) * hh, R), L['hair'], 0.03)
    for s_ in (1, -1):
        Rf = frame(x=(s_, 0, 0), y=(0, 1, 0))
        f2.add(Ellipsoid(A(s_ * 0.27, -0.03, 1.02), A(0.17, 0.05, 0.27), rot((0, 1, 0), s_ * 0.25)), L['skin'], 0.04)
    f2.add(Ellipsoid(A(0, 0.165, 0.75), A(0.09, 0.05, 0.035)), L['skin'], 0.01)
    m.field(f2, 0.006, 30.0, lods=(2,))
    # ------------------------------------------------ the eleven heads (十一面) + 頂上仏面: instanced
    def mini(kind):
        def mk():
            u = 0.205 * hh; mf = Field('mini_' + kind)
            Rm = np.eye(3); Om = A(0, 0, 0)
            mf.add(RCone(A(0, -0.08, -0.85) * u, A(0, -0.05, -0.3) * u, 0.32 * u, 0.26 * u), L['skin'], 0.1 * u)
            if kind == 'calm':
                Bd.add_head(mf, Rm, Om, u, style='serene', ears='long', eyes='carved', urna=False)
                Bd.add_hair(mf, Rm, Om, u, 'bun')
            elif kind == 'angry':
                Bd.add_head(mf, Rm, Om, u, style='fierce', fierce=1.0, ears='normal', eyes='carved', urna=False, mouth='closed')
                Bd.add_hair(mf, Rm, Om, u, 'bun')
            elif kind == 'fang':
                Bd.add_head(mf, Rm, Om, u, style='fierce', fierce=0.8, ears='normal', eyes='carved', urna=False, mouth='open')
                Bd.add_hair(mf, Rm, Om, u, 'bun')
            else:   # buddha: ushnisha
                Bd.add_head(mf, Rm, Om, u, style='serene', ears='long', eyes='carved', urna=True)
                mf.add(Ellipsoid(A(0, -0.03, 0.12) * u, A(0.37, 0.44, 0.42) * u), L['hair'], 0.02 * u)
                mf.add(Ellipsoid(A(0, -0.04, 0.5) * u, A(0.24, 0.24, 0.2) * u), L['hair'], 0.1 * u)
            return mf, 0.00045
        return mk
    top = O + R @ A(0, -0.04, 0.5) * hh
    ring = []
    for i in range(10):
        a = math.pi / 2 + 2 * math.pi * i / 10       # 0 = front
        kind = 'calm' if i in (0, 1, 9) else ('fang' if i in (2, 3, 4) else ('angry' if i in (6, 7, 8) else 'fang'))
        if i == 5: kind = 'angry'
        rr = 0.27 * hh
        p = top + R @ A(rr * math.cos(a), rr * math.sin(a) * 1.05, -0.04 * hh + 0.02 * hh * (i % 2))
        Rf = R @ frame(y=(math.cos(a), math.sin(a), 0.15), z=(0, 0, 1))
        ring.append((kind, Rf, p))
    tier2 = []
    for (kind, Rf, p) in ring: tier2.append((kind, Rf, p))
    for kind in ('calm', 'angry', 'fang'):
        xfs = [(Rf * 1.0, p) for (kk, Rf, p) in tier2 if kk == kind]
        m.instance('mini_' + kind, mini(kind), 0.36, xfs, maxlod=1)
    bud_p = top + R @ A(0, 0.02, 0.36) * hh
    m.instance('mini_buddha', mini('buddha'), 0.4, [(R * 1.12, bud_p)], maxlod=1)
    # ------------------------------------------------ hands (instanced)
    Lh = 0.71 * hh; Ls = 0.47 * hh
    def hand(pose, Lh_, br=None):
        return lambda: (Bd.hand_field(pose, Lh_, lab='skin'), Lh_ / 115)
    xf_pr = []
    for nm, a in fig.arm.items():
        s = a['s']
        fd = nrm(A(0, 0.32, 1)); back = A(s, 0.0, 0)
        xf_pr.append(Bd.hand_xf(a['W'], fd, back, s))
    m.instance('hand_prayer', hand('prayer', Lh), 0.85, xf_pr)
    xf_bw = []
    for nm, (E, W) in bowl_w.items():
        s = 1 if nm == 'r' else -1
        fd = nrm(A(-s, 0.35, -0.05)); back = A(0, 0.0, -1)
        R_, t_ = Bd.hand_xf(W, fd, back, s)
        if s < 0: t_ = t_ + A(0, 0, -0.012)
        xf_bw.append((R_, t_))
    m.instance('hand_cup', hand('cup', Lh), 0.85, xf_bw)
    side_xf = {}
    for (s, root, E, W, pose, att, th) in side:
        ax = nrm(W - E)
        fd = nrm(ax + A(0, 0.25, 0.55))
        back = A(s * 0.35, -1, -0.1)
        side_xf.setdefault(pose, []).append(Bd.hand_xf(W, fd, back, s))
    for pose, xfs in side_xf.items():
        m.instance('hand_s_' + pose, hand(pose, Ls), 0.19, xfs, maxlod=1)
    # ------------------------------------------------ explicit parts
    halo_c = O + A(0, -0.135, 0.02)
    def xm_fn(q):
        xm = X.XM()
        # pedestal (figure coords: the soles at z = 0, the pedestal bottom at -lift)
        z0 = -m.lift
        X.octa_plinth(xm, (0, 0, z0), 0.3, [(1.0, 0.0, 0.05), (0.95, 0.05, 0.075), (0.9, 0.075, 0.12), (0.84, 0.12, 0.145)], 'ped2', 'ped', phase=math.pi / 8)
        if q > 0.3:
            X.kaeribana(xm, (0, 0, z0 + 0.145), 0.25, 0.06, 16 if q > 0.6 else 10, 'petal', q)
        else:
            X.lathe(xm, (0, 0, z0 + 0.145), [(0.24, 0), (0.22, 0.04), (0.14, 0.06), (0, 0.06)], 8, 'petal')
        X.lathe(xm, (0, 0, z0 + 0.205), [(0.0, 0.0), (0.11, 0.0), (0.1, 0.035), (0.15, 0.05), (0.17, 0.07), (0.15, 0.085), (0.0, 0.085)], 16 if q > 0.5 else 8, 'ped')
        if q > 0.3:
            X.lotus_seat(xm, (0, 0, -0.095), 0.2, 0.095, 3 if q > 0.6 else 2, 13 if q > 0.6 else 9, 'petal', q)
        else:
            X.lathe(xm, (0, 0, -0.095), [(0.1, 0), (0.2, 0.06), (0.21, 0.095), (0, 0.095)], 8, 'petal')
        X.disc(xm, (0, 0, -0.002), (0, 0, 1), 0.165, 'ped', seg=24 if q > 0.5 else 8)
        # halo post + head disc + ring + rods
        X.tube(xm, [A(0, -0.16, z0 + 0.15), A(0, -0.16, halo_c[2] - 0.05), halo_c + A(0, -0.02, 0)], 0.012, 6 if q > 0.5 else 4, 'rod')
        nr = 34 if q > 0.3 else 18
        X.sunburst(xm, halo_c, np.eye(3), nr, 0.12, 0.6, 0.0032 if q > 0.3 else 0.006, 'halo', q, ring_r=0.42 if q > 0.2 else None,
                   disc_r=0.165, seed=v, up_long=1.42, knob=q > 0.5)
        # long staffs held by the lowest side arms on each side: 錫杖 (right) and 戟 (left)
        for s, top_kind in ((1, 'ring'), (-1, 'halberd')):
            low = [a for a in side if a[0] == s][-3]
            W = low[3]
            base = A(s * 0.255, 0.14, z0 + 0.145); topp = A(s * 0.25, 0.15, 1.36)
            X.tube(xm, [base, topp], 0.0045 if q > 0.3 else 0.007, 5 if q > 0.5 else 3, 'rod')
            if q > 0.3:
                if top_kind == 'ring':
                    th_ = np.linspace(0, 2 * math.pi, 17)
                    X.tube(xm, [topp + A(0.045 * math.sin(t), 0, 0.06 + 0.06 * math.cos(t)) for t in th_], 0.004, 4, 'rod', caps=False)
                    X.tube(xm, [topp, topp + A(0, 0, 0.16)], [0.006, 0.002], 4, 'rod')
                else:
                    X.tube(xm, [topp, topp + A(0, 0, 0.12)], [0.008, 0.001], 4, 'rod')
                    for e in (-1, 1):
                        X.tube(xm, [topp, topp + A(e * 0.04, 0, 0.02), topp + A(e * 0.045, 0, 0.08)], [0.005, 0.004, 0.001], 4, 'rod', caps=False)
        # 天衣: scarf over the shoulders, two U swags across the front, ends hanging at the sides
        if q > 0.2:
            for s, zs, end in ((-1, 0.585, 1), (1, 0.43, -1)):
                pts = spline([(s * 0.13, -0.08, 1.15), (s * 0.205, -0.03, 1.08), (s * 0.215, 0.02, 0.93), (s * 0.195, 0.07, 0.76),
                              (s * 0.13, 0.135, zs + 0.06), (0, 0.155, zs), (-s * 0.13, 0.14, zs + 0.06), (-s * 0.18, 0.09, zs + 0.2), (-s * 0.175, 0.05, 0.78)],
                             40 if q > 0.6 else 16)
                ups = [nrm(A(p[0], p[1] + 0.02, 0)) for p in pts]
                X.ribbon(xm, pts, 0.02, 0.0035, ups, 'scarf')
                hang = spline([(s * 0.19, 0.04, 0.82), (s * 0.235, 0.06, 0.6), (s * 0.24, 0.06, 0.3), (s * 0.235, 0.07, 0.05)], 16 if q > 0.6 else 6)
                X.ribbon(xm, hang, 0.022, 0.004, [nrm(A(s, 0.3, 0))] * len(hang), 'scarf')
            # crown ribbons (冠繒) falling from the crown sides behind the shoulders
            for s in (1, -1):
                c0 = O + R @ A(s * 0.4, -0.05, 0.28) * hh
                pts = spline([c0, c0 + A(s * 0.02, -0.02, -0.12), c0 + A(s * 0.06, -0.03, -0.3), c0 + A(s * 0.09, -0.02, -0.48)], 14 if q > 0.6 else 5)
                X.ribbon(xm, pts, [0.012, 0.014, 0.016, 0.012] if False else 0.013, 0.003, [A(s, 0.2, 0)] * len(pts), 'scarf')
            # necklace (胸飾) with pendants, and a jewel string on the skirt
            neck = spline([(-0.12, 0.03, 1.1), (-0.06, 0.115, 1.06), (0, 0.13, 1.045), (0.06, 0.115, 1.06), (0.12, 0.03, 1.1)], 20)
            X.beads(xm, neck, 0.007, 'jewel', q)
            for xx in (-0.05, 0.0, 0.05):
                p0 = A(xx, 0.125 + 0.005 * (xx == 0), 1.05 - 0.01 * (xx == 0))
                X.tube(xm, [p0, p0 + A(0, 0.01, -0.06)], [0.005, 0.009], 5, 'jewel')
            for s in (1, -1):
                X.beads(xm, spline([(s * 0.06, 0.1, 0.83), (s * 0.09, 0.15, 0.6), (s * 0.04, 0.17, 0.5), (0, 0.175, 0.47)], 16), 0.006, 'jewel', q)
        # attributes in the side hands
        if q > 0.5:
            for (s, root, E, W, pose, att, th) in side:
                ax = nrm(W - E)
                fd = nrm(ax + A(0, 0.25, 0.55)); back = A(s * 0.35, -1, -0.1)
                Rh_, t_ = Bd.hand_xf(W, fd, back, s)
                grip = {'grip': (0.5, 0.0, -0.1), 'pinch': (0.62, 0.1, -0.12), 'cup': (0.35, 0, -0.15), 'open': (0.35, 0, -0.15), 'mudra': (0.55, 0.1, -0.12)}[pose]
                tt = t_ + Rh_ @ (A(*grip) * Ls)
                X.attribute(xm, att, Rh_, tt, 0.075, 'attr', q)
            # the bowl (宝鉢) on the lower hands
            X.attribute(xm, 'bowl', frame(x=(0, 1, 0), z=(0, 0, -1)), A(0, 0.165, 0.745), 0.13, 'attr', q)
        return xm
    m.xm_fn = xm_fn
    m.closeups = [('face', m.lift + O[2] + 0.03, 0.75, 0.3), ('lower', m.lift + 0.45, 1.6, 0.5), ('mid', m.lift + 1.0, 1.1, -0.4)]
    return m

def Offset_(p, r): return S.Offset(p, r)

# ---------------------------------------------------------------------------------------------- seated 中尊
def add_foot_up(f, Ak, toe_dir, hh, lab, s):
    """a foot lying on the opposite thigh, sole up (結跏趺坐)"""
    td = nrm(toe_dir); up = A(0, 0, 1); side = nrm(np.cross(td, up))
    heel = Ak - td * 0.12 * hh
    toe = Ak + td * 0.75 * hh
    f.add(Ellipsoid((heel + toe) / 2 + A(0, 0, -0.02 * hh), A(0.5, 0.24, 0.13) * hh, frame(x=td, z=up)), lab, 0.07 * hh)
    f.add(RCone(heel, Ak, 0.12 * hh, 0.14 * hh), lab, 0.05 * hh)
    for i, (o, r, ln) in enumerate(((-0.13, 0.065, 0.12), (-0.03, 0.05, 0.11), (0.05, 0.045, 0.1), (0.12, 0.042, 0.08), (0.18, 0.04, 0.06))):
        b = toe + side * s * o * hh - td * 0.1 * hh + up * 0.01 * hh
        f.add(Capsule(b, b + td * ln * hh * 1.2, r * hh), lab, 0.025 * hh)

def kannon_seated():
    from .statues_build import Model
    from . import statues_relief as RL
    rng = np.random.default_rng(1254)
    m = Model('kannon_seated', '千手観音坐像 (中尊)', 'Seated Thousand-armed Kannon (central image, Tankei 1254)',
              budget=(248000, 49000, 7400), lift=2.0, figure_h=3.35)
    m.pal = gold_palette()
    m.slot = dict(slot='kannon_seated')
    m.pal[L['eye']] = ('glass', (255, 255, 255, 0))
    hh = 0.78; H = 6.1 * hh
    pz = 0.38 * hh
    fig = Bd.Fig(H, 6.1, 'bodhi', pelvis_z=pz, leg_len=2.62, head_rot=(0.1, 0, 0),
                 hand_r=(0.03, 0.57, 1.15), hand_l=(-0.03, 0.57, 1.15), elbow_r=(1.0, -0.2, -0.9), elbow_l=(-1.0, -0.2, -0.9),
                 foot_r=A(-0.5, 0.78, 0.47) * hh, foot_l=A(0.45, 0.95, 0.2) * hh, knee_r=(1, 0.35, -0.45), knee_l=(-1, 0.35, -0.45))
    O = fig.Oh; R = fig.Rh
    f = Field('body')
    # torso, neck, prayer arms (legs handled here: no standing feet)
    hhh = hh
    Rc, Oc = fig.Rc, fig.Oc
    Bd.add_body(f, fig, skin='skin') if False else None
    # body without the default legs/feet
    fig_legs = fig.leg; fig.leg = {}
    Bd.add_body(f, fig, skin='skin')
    fig.leg = fig_legs
    for nm, g in fig.leg.items():
        Bd.add_leg(f, fig, g, L['skin'], foot=False)
    rfoot = fig.leg['r']['A']
    add_foot_up(f, rfoot, nrm(A(-0.9, 0.25, 0.05)), hh, L['skin'], 1)
    # robe over the crossed legs: lap mass + shin tubes + radial folds
    def lapfold(P):
        th = np.arctan2(P[:, 1] - 0.2 * hh, P[:, 0]); r = np.sqrt(P[:, 0] ** 2 + (P[:, 1] - 0.2 * hh) ** 2)
        return (-0.012 * np.cos(17 * th + 3 * r) * np.clip(r / (1.6 * hh), 0, 1) - 0.006 * np.cos(31 * th)).astype(np.float32)
    lap = Union([Ellipsoid(A(0, 0.42, 0.33) * hh, A(1.82, 0.82, 0.33) * hh),
                 Tube([fig.leg['r']['H'], fig.leg['r']['K'], fig.leg['r']['A'] + A(0.1, 0.05, 0) * hh], A(0.46, 0.4, 0.3) * hh),
                 Tube([fig.leg['l']['H'], fig.leg['l']['K'], fig.leg['l']['A'] - A(0.1, -0.05, 0) * hh], A(0.46, 0.4, 0.3) * hh),
                 Ellipsoid(A(0, -0.05, 0.3) * hh, A(0.8, 0.55, 0.42) * hh)], 0.25 * hh)
    f.add(Displace(lap, lapfold, 0.02), L['robe'], 0.04 * hh)
    f.add(Band(A(0, -0.02, 0.7) * hh + A(0, 0, pz * 0.0), 0.72 * hh, 0.56 * hh, 0.02 * hh, 0.07 * hh), L['robe2'], 0.01 * hh)
    # bowl arms: hands in the lap
    bowl_w = {}
    for nm, a in fig.arm.items():
        s = a['s']
        S0 = a['S'] + A(-s * 0.04, -0.15, -0.12) * hh
        W = A(s * 0.2, 0.62, 0.62) * hh
        E, W = Bd.ik2(S0, W, 1.28 * hh, 1.08 * hh, (s * 0.8, -0.2, -1))
        Bd.add_arm(f, fig, dict(S=S0, E=E, W=W, s=s), L['skin'], deltoid=False)
        bowl_w[nm] = (E, W)
        f.add(Torus(W + nrm(W - E) * 0.02 * hh, 0.115 * hh, 0.025 * hh, frame(z=nrm(W - E), x=(0, 0, 1))), L['jewel'], 0.01 * hh)
    for nm, a in fig.arm.items():
        ax = nrm(a['W'] - a['E'])
        f.add(Torus(a['W'] + ax * 0.02 * hh, 0.118 * hh, 0.026 * hh, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.01 * hh)
        ax2 = nrm(a['E'] - a['S'])
        f.add(Torus(a['S'] + (a['E'] - a['S']) * 0.4, 0.21 * hh, 0.03 * hh, frame(z=ax2, x=(0, 1, 0) if abs(ax2[1]) < 0.9 else (1, 0, 0))), L['jewel'], 0.015 * hh)
    # 38 side arms in a great oval fan, 3 layers deep, + 2 arms raising a small Buddha over the head, + 2 holding the long staffs
    side = []
    poses = ['pinch', 'grip', 'cup', 'open', 'pinch', 'grip', 'mudra']
    attrs_all = ['jewel', 'wheel', 'disc', 'lotus', 'vase', 'sword', 'vajra', 'rosary', 'bell', 'skull', 'branch', 'conch',
                 'axe', 'arrow', 'bow', 'sutra', 'cloud', 'disc', 'jewel', 'rod', 'lotus', 'vase', 'wheel', 'trident',
                 'vajra', 'disc', 'bell', 'jewel', 'sword', 'lotus', 'rod', 'conch', 'rosary', 'branch', 'vase', 'disc', 'buddha', 'jewel']
    order = rng.permutation(len(attrs_all)); k = 0
    shz = fig.arm['r']['S'][2]
    for s in (1, -1):
        R0 = A(s * 0.42, -0.42, -0.05) * hh + A(0, 0, shz)
        Hc = A(s * 0.3 * hh, -0.25 * hh, Oc[2] + 0.3 * hh)
        n = 18
        for i in range(n):
            layer = i % 3
            th = math.radians(16 + 150 * i / (n - 1) + rng.uniform(-3, 3))
            rx, rz = (1.95 + 0.08 * (layer == 0) - 0.12 * (layer == 2)) * hh, 1.65 * hh
            y = [0.12, -0.12, -0.36][layer] * hh
            W = Hc + A(s * math.sin(th) * rx, y, math.cos(th) * rz) + rng.uniform(-0.02, 0.02, 3)
            root = R0 + A(0, -0.06 * layer, -0.35 * (i / n)) * hh
            E, W = Bd.ik2(root, W, 1.12 * hh, 1.02 * hh, (s * 0.3, -0.6, -1))
            pose = poses[(i + layer) % len(poses)]
            att = attrs_all[order[k % len(order)]]; k += 1
            side.append((s, root, E, W, pose, att))
        # two more near the top reaching over the head (頂上化仏手)
        root = R0 + A(-s * 0.1, 0.05, 0.1) * hh
        W = A(s * 0.16 * hh, -0.05 * hh, O[2] + 0.95 * hh)
        E, W = Bd.ik2(root, W, 0.95 * hh, 0.88 * hh, (s * 1, -0.3, -0.2))
        side.append((s, root, E, W, 'cup_over', None))
        # staff holders (front)
        root = R0 + A(0, 0.12, -0.25) * hh
        W = A(s * 0.95 * hh, 0.55 * hh, Oc[2] - 0.1 * hh)
        E, W = Bd.ik2(root, W, 0.95 * hh, 0.88 * hh, (s * 1, -0.2, -0.8))
        side.append((s, root, E, W, 'grip_staff', None))
        f.add(Ellipsoid(A(s * 0.42, -0.45, -0.3) * hh + A(0, 0, shz), A(0.32, 0.3, 0.6) * hh), L['skin'], 0.1 * hh)
    for (s, root, E, W, pose, att) in side:
        f.add(RCone(root, E, 0.105 * hh, 0.085 * hh), L['skin'], 0.04 * hh)
        f.add(RCone(E, W, 0.08 * hh, 0.058 * hh), L['skin'], 0.03 * hh)
        ax = nrm(W - E)
        f.add(Torus(W + ax * 0.012 * hh, 0.066 * hh, 0.016 * hh, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.006 * hh)
    # sash across the chest
    sc = hh / 0.234
    sash = spline([A(-0.15, -0.02, 1.13), A(-0.09, 0.105, 1.07), A(0.0, 0.13, 0.97), A(0.1, 0.11, 0.87), A(0.15, 0.0, 0.83),
                   A(0.11, -0.11, 0.86), A(0.0, -0.13, 0.95), A(-0.1, -0.12, 1.07), A(-0.15, -0.02, 1.13)], 30)
    sash = [(p - A(0, 0, 0.98)) * sc * A(1, 1.03, 1) + A(0, 0, Oc[2]) for p in sash]
    f.add(Sweep(sash, 0.03 * sc, 0.005 * sc, [nrm(p - A(0, -0.01 * sc, p[2])) for p in sash]), L['sash'], 0.004 * sc)
    m.field(f, 0.0062, 80.0, lods=(0, 1))
    # ------------------------------------------------ head (crystal eyes)
    g = Field('head')
    g.add(Inter([RCone(fig.N - Rc @ A(0, 0, 0.15 * hh), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.27 * hh, 0.25 * hh),
                 Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), L['skin'], 0.0)
    Bd.add_head(g, R, O, hh, style='serene', ears='long', eyes='crystal', urna='crystal', nose=0.8)
    Bd.add_hair(g, R, O, hh, 'bodhi')
    Bd.neck_folds(g, fig, 3)
    P_ = lambda vv: O + R @ (A(*vv) * hh)
    g.add(Band(P_((0, -0.05, 0.25)), 0.366 * hh, 0.426 * hh, 0.016 * hh, 0.03 * hh, R @ rot((1, 0, 0), -0.08)), L['crown'], 0.004 * hh)
    for s in (1, -1):
        g.add(Ellipsoid(P_((s * 0.37, 0.02, 0.26)), A(0.025, 0.075, 0.075) * hh, R), L['crown'], 0.008 * hh)
        g.add(Ellipsoid(P_((s * 0.36, -0.12, 0.22)), A(0.03, 0.05, 0.03) * hh, R), L['crown'], 0.008 * hh)
    g.add(Ellipsoid(P_((0, 0.385, 0.29)), A(0.055, 0.02, 0.06) * hh, R), L['crown'], 0.006 * hh)
    m.field(g, 0.0026, 30.0, lods=(0, 1))
    # LOD2 field
    f2 = Field('lod2')
    fig.leg = {}; Bd.add_body(f2, fig, skin='skin'); fig.leg = fig_legs
    f2.add(lap, L['robe'], 0.05)
    f2.add(Ellipsoid(O + R @ A(0, -0.04, 0.12) * hh, A(0.42, 0.48, 0.62) * hh, R), L['hair'], 0.05)
    for s_ in (1, -1):
        f2.add(Ellipsoid(A(s_ * 1.05 * hh, -0.25 * hh, Oc[2] + 0.25 * hh), A(1.0, 0.3, 1.45) * hh, rot((0, 1, 0), s_ * 0.2)), L['skin'], 0.1)
    m.field(f2, 0.016, 30.0, lods=(2,))
    # ------------------------------------------------ eleven heads
    def mini(kind):
        def mk():
            u = 0.2 * hh; mf = Field('mini_' + kind)
            Rm = np.eye(3); Om = A(0, 0, 0)
            mf.add(RCone(A(0, -0.08, -0.85) * u, A(0, -0.05, -0.3) * u, 0.32 * u, 0.26 * u), L['skin'], 0.1 * u)
            if kind == 'buddha':
                Bd.add_head(mf, Rm, Om, u, style='serene', ears='long', eyes='carved', urna=True)
                mf.add(Ellipsoid(A(0, -0.03, 0.12) * u, A(0.37, 0.44, 0.42) * u), L['hair'], 0.02 * u)
                mf.add(Ellipsoid(A(0, -0.04, 0.5) * u, A(0.24, 0.24, 0.2) * u), L['hair'], 0.1 * u)
            else:
                Bd.add_head(mf, Rm, Om, u, style='serene' if kind == 'calm' else 'fierce', fierce=0.0 if kind == 'calm' else 1.0,
                            ears='long' if kind == 'calm' else 'normal', eyes='carved', urna=False, mouth='open' if kind == 'fang' else 'closed')
                Bd.add_hair(mf, Rm, Om, u, 'bun')
            return mf, 0.0011
        return mk
    top = O + R @ A(0, -0.04, 0.5) * hh
    for kind, idxs in (('calm', (0, 1, 9)), ('fang', (2, 3, 4)), ('angry', (5, 6, 7, 8))):
        xfs = []
        for i in idxs:
            a = math.pi / 2 + 2 * math.pi * i / 10; rr = 0.27 * hh
            p = top + R @ A(rr * math.cos(a), rr * math.sin(a) * 1.05, -0.04 * hh + 0.02 * hh * (i % 2))
            xfs.append((R @ frame(y=(math.cos(a), math.sin(a), 0.15), z=(0, 0, 1)), p))
        m.instance('mini_' + kind, mini(kind), 1.0, xfs, maxlod=1)
    m.instance('mini_buddha', mini('buddha'), 1.2, [(R * 1.12, top + R @ A(0, 0.02, 0.36) * hh)], maxlod=1)
    # ------------------------------------------------ hands
    Lh = 0.71 * hh; Ls = 0.42 * hh
    def hand(pose, Lh_):
        return lambda: (Bd.hand_field(pose, Lh_, lab='skin'), Lh_ / 120)
    xf_pr = [Bd.hand_xf(a['W'], nrm(A(0, 0.32, 1)), A(a['s'], 0, 0), a['s']) for nm, a in fig.arm.items()]
    m.instance('hand_prayer', hand('prayer', Lh), 2.4, xf_pr)
    xf_bw = []
    for nm, (E, W) in bowl_w.items():
        s = 1 if nm == 'r' else -1
        R_, t_ = Bd.hand_xf(W, nrm(A(-s, 0.35, -0.05)), A(0, 0.0, -1), s)
        if s < 0: t_ = t_ + A(0, 0, -0.04 * hh)
        xf_bw.append((R_, t_))
    m.instance('hand_cup', hand('cup', Lh), 2.4, xf_bw)
    side_xf = {}; side_frames = []
    for (s, root, E, W, pose, att) in side:
        ax = nrm(W - E)
        if pose == 'cup_over':
            fd = nrm(A(-s, 0, 0.6)); back = A(0, 0.2, -1); pose_ = 'cup'
        elif pose == 'grip_staff':
            fd = nrm(A(-s, 0.4, 0.0)); back = A(s * 0.2, -0.3, 1); pose_ = 'grip'
        else:
            fd = nrm(ax + A(0, 0.25, 0.55)); back = A(s * 0.35, -1, -0.1); pose_ = pose
        xf = Bd.hand_xf(W, fd, back, s)
        side_xf.setdefault(pose_, []).append(xf); side_frames.append((xf, pose, att, s))
    for pose, xfs in side_xf.items():
        m.instance('hand_s_' + pose, hand(pose, Ls), 0.7, xfs, maxlod=1)
    # ------------------------------------------------ halo (舟形光背): openwork of scrolls, rings and flames
    hx0, hx1, hz0, hz1 = -1.78, 1.78, -0.15, 5.15
    px = 0.0065
    def half_w(z):
        t = np.clip((z - hz0) / (hz1 - hz0), 0, 1)
        lowp = 1.58 + 0.14 * np.clip(t / 0.4, 0, 1)
        u_ = np.clip((t - 0.4) / 0.6, 0, 1)
        upp = 1.72 * np.sqrt(np.clip(1 - u_ ** 2, 0, 1)) * (1 - u_) ** 0.25
        return np.where(t < 0.4, lowp, upp)
    cv = RL.Canvas(hx0 - 0.2, hz0, hx1 + 0.2, hz1 + 0.25, px)
    zs = np.linspace(hz0, hz1, 120)
    outline = [(half_w(z) - 0.035, z) for z in zs] + [(0, hz1 - 0.02)]
    cv.stroke(outline, 0.032); cv.stroke([(-x, z) for (x, z) in outline], 0.032)
    inner = [(half_w(z) - 0.17, z) for z in zs if half_w(z) > 0.25]
    cv.stroke(inner, 0.016); cv.stroke([(-x, z) for (x, z) in inner], 0.016)
    hc = (0.0, O[2] + 0.05); bc = (0.0, Oc[2] - 0.05)
    for rr_, w_ in ((0.78, 0.035), (0.66, 0.016)):
        th = np.linspace(0, 2 * math.pi, 160); cv.stroke([(hc[0] + rr_ * math.cos(t), hc[1] + rr_ * math.sin(t)) for t in th], w_)
    th = np.linspace(-0.05, math.pi + 0.05, 160)
    cv.stroke([(bc[0] + 1.32 * math.cos(t), bc[1] + 1.32 * math.sin(t) * 0.9) for t in th], 0.03)
    for i in range(24):    # beads between the head rings
        a = 2 * math.pi * i / 24
        c_ = (hc[0] + 0.72 * math.cos(a), hc[1] + 0.72 * math.sin(a))
        cv.stroke([(c_[0] + 0.022 * math.cos(t), c_[1] + 0.022 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 10)], 0.012)
    for i in range(20):    # rays in the head halo
        a = 2 * math.pi * i / 20
        cv.stroke([(hc[0] + 0.4 * math.cos(a), hc[1] + 0.4 * math.sin(a)), (hc[0] + 0.64 * math.cos(a), hc[1] + 0.64 * math.sin(a))], 0.012)
    # scroll tendrils (宝相華唐草) on a jittered grid
    seeds = []
    sp = 0.215
    for zz in np.arange(hz0 + 0.2, hz1 - 0.15, sp * 0.87):
        for xx in np.arange(-1.7, 1.71, sp):
            p = np.array([xx + (sp / 2 if int(round((zz - hz0) / (sp * 0.87))) % 2 else 0) + rng.uniform(-0.05, 0.05), zz + rng.uniform(-0.05, 0.05)])
            if abs(p[0]) < half_w(p[1]) - 0.2: seeds.append(p)
    RL.tendril_field(cv, seeds, rng, w=0.019, r=0.105, links=2)
    # flames along the rim
    s_out = np.linspace(0.05, 0.98, 30)
    for side_s in (1, -1):
        for t in s_out:
            z = hz0 + t * (hz1 - hz0); x = half_w(z)
            if x < 0.05: continue
            d = np.array([side_s, 0.6 + 0.6 * t]); d /= np.linalg.norm(d)
            pts = [np.array([side_s * x, z]) + d * 0.2 * u + np.array([0, 0.06 * u * u]) for u in np.linspace(0, 1, 6)]
            cv.stroke(pts, np.linspace(0.04, 0.004, 6))
    top_flame = [np.array([0.0, hz1 - 0.05]) + np.array([0.03 * math.sin(u * 4), 0.28 * u]) for u in np.linspace(0, 1, 8)]
    cv.stroke(top_flame, np.linspace(0.06, 0.004, 8))
    cv.clip(lambda X_, Z_: (np.abs(X_) <= half_w(Z_) + 0.25) & (Z_ <= hz1 + 0.3))
    D2 = cv.sdf()
    hy0 = -0.62 * hh - 0.3
    halo = RL.Relief(D2, cv.x0, cv.z0, px, hy0, 0.026, r=0.009, bend=0.06, tilt=0.0, zbend=-0.008, zc=hc[1])
    hf = Field('halo'); hf.add(halo, L['halo'], 0.0)
    m.field(hf, 0.0085, 62.0, lods=(0, 1))
    hf2 = Field('halo2')
    def boat2(P):
        z = P[:, 2]; w = half_w(z)
        dxz = np.maximum(np.abs(P[:, 0]) - w, np.maximum(hz0 - z, z - hz1))
        yc = hy0 + 0.06 * P[:, 0] ** 2
        return np.maximum(dxz, np.abs(P[:, 1] - yc) - 0.03).astype(np.float32)
    hf2.add(Fn(boat2, (hx0, hy0 - 0.1, hz0), (hx1, hy0 + 0.35, hz1)), L['halo'], 0.0)
    m.field(hf2, 0.03, 12.0, lods=(2,))
    def halo_y(x, z): return hy0 + 0.06 * x * x - 0.008 * (z - hc[1]) ** 2
    # 33 small figures (三十三応現身) on the halo
    fig_pos = []
    for i in range(33):
        t = (i + 0.5) / 33
        a = math.pi * (0.04 + 0.92 * t)                       # around the rim, from right-bottom over the top to left
        z = hz0 + 0.35 + (hz1 - hz0 - 0.9) * (0.5 + 0.5 * math.sin(a - math.pi / 2)) * 0.98
        x_ = (half_w(z) - 0.32) * math.cos(a) * -1
        sc_ = 0.75 + 0.25 * rng.random()
        fig_pos.append((x_, z, sc_))
    def small_fig():
        u = 0.07; mf = Field('small_fig')
        mf.add(Ellipsoid(A(0, 0, 0.0), A(1.0, 0.7, 0.6) * u), L['robe'], 0.0)                     # cloud seat / lap
        mf.add(Ellipsoid(A(0, 0.0, 0.85) * u, A(0.75, 0.5, 1.2) * u), L['robe'], 0.3 * u)          # body
        mf.add(Sphere(A(0, 0.05, 2.25) * u, 0.42 * u), L['skin'], 0.2 * u)                       # head
        mf.add(Ellipsoid(A(0, 0.02, 2.7) * u, A(0.22, 0.22, 0.3) * u), L['hair'], 0.1 * u)
        mf.add(Ellipsoid(A(0, 0.38, 1.25) * u, A(0.3, 0.2, 0.25) * u), L['skin'], 0.12 * u)       # hands
        mf.add(Cyl(A(0, -0.35, 2.0) * u, A(0, -0.25, 2.0) * u, 1.0 * u, 0.04 * u), L['halo'], 0.0)
        for e in (-1, 1):
            mf.add(Ellipsoid(A(e * 0.9, 0.05, -0.1) * u, A(0.6, 0.45, 0.35) * u), L['robe'], 0.15 * u)
        return mf, 0.003
    xfs = []
    for (x_, z, sc_) in fig_pos:
        xfs.append((np.eye(3) * sc_, A(x_, halo_y(x_, z) + 0.06, z)))
    m.instance('small_fig', small_fig, 0.5, xfs, maxlod=1)
    # ------------------------------------------------ explicit parts
    def xm_fn(q):
        xm = X.XM()
        z0 = -m.lift
        X.octa_plinth(xm, (0, 0, z0), 1.95, [(1.0, 0.0, 0.12), (0.96, 0.12, 0.2), (0.92, 0.2, 0.32)], 'ped2', 'ped', phase=math.pi / 8)
        if q > 0.3: X.kaeribana(xm, (0, 0, z0 + 0.32), 1.6, 0.22, 24 if q > 0.6 else 16, 'petal', q)
        else: X.lathe(xm, (0, 0, z0 + 0.32), [(1.6, 0), (1.5, 0.12), (0.9, 0.22), (0, 0.22)], 8, 'petal')
        X.octa_plinth(xm, (0, 0, z0 + 0.54), 1.08, [(1.0, 0.0, 0.1)], 'ped2', phase=math.pi / 8)
        X.lathe(xm, (0, 0, z0 + 0.64), [(0.0, 0.0), (1.0, 0.0), (1.42, 0.05), (1.5, 0.12), (1.42, 0.15), (0.0, 0.15)], 32 if q > 0.5 else 12, 'ped', ngon=False)
        X.lathe(xm, (0, 0, z0 + 0.79), [(0.0, 0.0), (0.95, 0.0), (1.05, 0.1), (1.0, 0.22), (0.85, 0.28), (0.0, 0.28)], 32 if q > 0.5 else 12, 'ped')
        if q > 0.3:
            X.lotus_seat(xm, (0, 0, -0.95), 1.62, 0.95, 5 if q > 0.6 else 3, 22 if q > 0.6 else 14, 'petal', q, flare=1.0)
        else:
            X.lathe(xm, (0, 0, -0.95), [(0.9, 0), (1.6, 0.5), (1.7, 0.95), (0, 0.95)], 10, 'petal')
        X.disc(xm, (0, 0, -0.01), (0, 0, 1), 1.45, 'ped', seg=48 if q > 0.5 else 12)
        # halo stays: two posts behind
        for e in (-1, 1):
            X.tube(xm, [A(e * 0.5, hy0 + 0.08, -0.4), A(e * 0.5, hy0 + 0.08, 2.2)], 0.035, 8 if q > 0.5 else 4, 'rod')
        # long staffs held at chest height
        for (xf, pose, att, s) in side_frames:
            if pose != 'grip_staff': continue
            R_, t_ = xf
            c = t_ + R_ @ (A(0.5, 0.0, -0.1) * Ls)
            d = nrm(A(-s * 0.05, -0.12, 1))
            X.tube(xm, [c - d * 1.05, c + d * 1.45], 0.022, 8 if q > 0.5 else 4, 'rod')
            tp = c + d * 1.45
            if q > 0.3:
                if s > 0:
                    th_ = np.linspace(0, 2 * math.pi, 21)
                    X.tube(xm, [tp + A(0.16 * math.sin(t), 0, 0.2 + 0.2 * math.cos(t)) for t in th_], 0.014, 5, 'rod', caps=False)
                    X.tube(xm, [tp, tp + A(0, 0, 0.5)], [0.025, 0.006], 5, 'rod')
                else:
                    X.tube(xm, [tp, tp + A(0, 0, 0.42)], [0.03, 0.003], 5, 'rod')
                    for e in (-1, 1):
                        X.tube(xm, [tp, tp + A(e * 0.14, 0, 0.06), tp + A(e * 0.15, 0, 0.28)], [0.018, 0.014, 0.003], 5, 'rod', caps=False)
        if q > 0.2:
            # 天衣 over the shoulders, falling past the elbows into the lap
            for s in (1, -1):
                sh = fig.arm['r' if s > 0 else 'l']['S']
                pts = spline([sh + A(-s * 0.15, -0.12, 0.1) * hh, sh + A(s * 0.15, 0.0, 0.05) * hh, sh + A(s * 0.32, 0.15, -0.5) * hh,
                              sh + A(s * 0.45, 0.4, -1.2) * hh, A(s * 0.95, 0.75, 0.48) * hh, A(s * 1.3, 0.85, 0.32) * hh, A(s * 1.55, 0.95, 0.15) * hh], 36 if q > 0.6 else 14)
                X.ribbon(xm, pts, 0.075 * hh / 0.234 * 0.234 * 0.33, 0.012, [nrm(A(p[0], p[1] + 0.3, 0.2)) for p in pts], 'scarf')
            neck = spline([A(-0.12, 0.03, 1.1), A(-0.06, 0.115, 1.06), A(0, 0.13, 1.045), A(0.06, 0.115, 1.06), A(0.12, 0.03, 1.1)], 24)
            neck = [(p - A(0, 0, 0.98)) * sc * A(1, 1.03, 1) + A(0, 0, Oc[2]) for p in neck]
            X.beads(xm, neck, 0.007 * sc, 'jewel', q)
            for xx in (-0.05, 0.0, 0.05):
                p0 = (A(xx, 0.125 + 0.005 * (xx == 0), 1.05 - 0.01 * (xx == 0)) - A(0, 0, 0.98)) * sc + A(0, 0, Oc[2])
                X.tube(xm, [p0, p0 + A(0, 0.01, -0.07) * sc], [0.005 * sc, 0.009 * sc], 6, 'jewel')
            # crown ribbons
            for s in (1, -1):
                c0 = O + R @ A(s * 0.4, -0.05, 0.28) * hh
                pts = spline([c0, c0 + A(s * 0.02, -0.02, -0.12) * sc, c0 + A(s * 0.06, -0.03, -0.3) * sc, c0 + A(s * 0.09, -0.02, -0.48) * sc], 14 if q > 0.6 else 5)
                X.ribbon(xm, pts, 0.013 * sc, 0.003 * sc, [A(s, 0.2, 0)] * len(pts), 'scarf')
        if q > 0.5:
            for (xf, pose, att, s) in side_frames:
                R_, t_ = xf
                if att is None:
                    if pose == 'cup_over' and s > 0:
                        X.attribute(xm, 'buddha', frame(x=(1, 0, 0), z=(0, 0, -1)), t_ + R_ @ (A(0.35, 0, -0.15) * Ls) + A(-0.16 * hh, 0, 0.0), 0.36, 'attr', q)
                    continue
                grip = {'grip': (0.5, 0.0, -0.1), 'pinch': (0.62, 0.1, -0.12), 'cup': (0.35, 0, -0.15), 'open': (0.35, 0, -0.15), 'mudra': (0.55, 0.1, -0.12)}[pose]
                X.attribute(xm, att, R_, t_ + R_ @ (A(*grip) * Ls), 0.075 * Ls / (0.47 * 0.234), 'attr', q)
            X.attribute(xm, 'bowl', frame(x=(0, 1, 0), z=(0, 0, -1)), A(0, 0.66, 0.66) * hh, 0.13 * sc, 'attr', q)
        return xm
    m.xm_fn = xm_fn
    m.closeups = [('face', m.lift + O[2] + 0.05, 2.2, 0.15), ('whole', m.lift + 2.4, 9.0, 0.3), ('lap', m.lift + 0.6, 4.0, 0.4)]
    return m
