"""statues_body — a parametric, posable sculpted figure for the 三十三間堂 statues.

A Fig is a skeleton (proportions in head units, pose by frames + two-bone IK for arms and legs).  Its parts are
written into a statues_sdf.Field as labelled primitives: body (slender bodhisattva .. muscular guardian ..
gaunt ascetic), heads (serene / fierce / demon / bird / old), hair and topknots, clothing shells (skirts with
folds, long Tang sleeves, armour plates, belts), and hand fields (separate fine meshes, instanced at the wrists).

Statue frame: x = the statue's right, y = forward (it faces +y), z = up, metres, z = 0 at the soles."""
import math
import numpy as np
from . import statues_sdf as S
from .statues_sdf import (Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff,
                          Displace, Xf, Tube, Loft, Field, frame, rot, euler, nrm, smin, smax, vnoise, fbm)

F32 = np.float32
# ---------------------------------------------------------------------------------------------- labels (palette slots)
LABELS = ['none', 'skin', 'hair', 'eye', 'lip', 'robe', 'robe2', 'lining', 'scarf', 'armour', 'armour2', 'trim', 'jewel',
          'crown', 'base', 'base2', 'wood', 'metal', 'teeth', 'mouth', 'drum', 'bag', 'cloud', 'ped', 'petal', 'halo',
          'attr', 'worn', 'skin2', 'eyew', 'cap', 'beard', 'feather', 'snake', 'flame', 'shoe', 'belt', 'sash', 'ped2',
          'rod', 'glass', 'gold', 'dark', 'attr2', 'boss', 'nail', 'skin3', 'robe3', 'armour3', 'halo2', 'weapon', 'rock']
L = {n: i for i, n in enumerate(LABELS)}

def A(*v): return np.array(v, float)

# ---------------------------------------------------------------------------------------------- skeleton
def ik2(a, t, l1, l2, pole):
    """two-bone IK: root a, target t, bone lengths, pole direction -> (mid joint, end)"""
    a = np.asarray(a, float); t = np.asarray(t, float); pole = nrm(pole)
    d = t - a; L = np.linalg.norm(d)
    L = min(max(L, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    dn = nrm(d); t2 = a + dn * L
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L); y = math.sqrt(max(l1 * l1 - x * x, 0))
    p = pole - dn * (pole @ dn); p = nrm(p) if np.linalg.norm(p) > 1e-6 else nrm(np.cross(dn, [1, 0, 0]))
    return a + dn * x + p * y, t2

class Fig:
    """proportions (head units hh = chin to vertex) + pose -> joints and frames.
    kind: 'bodhi' (slender bodhisattva), 'deva' (calm deity), 'guard' (armoured guardian), 'nio' (muscular),
    'ascetic' (gaunt old man), 'female', 'demon' (Fujin / Raijin)"""
    def __init__(self, H, heads=6.2, kind='bodhi', **pose):
        self.kind = kind; self.H = H; hh = self.hh = H / heads
        self.musc = {'bodhi': 0.0, 'deva': 0.2, 'female': 0.0, 'guard': 0.6, 'nio': 1.0, 'ascetic': -0.6, 'demon': 0.9}.get(kind, 0.3)
        self.sw = hh * pose.get('sw', {'bodhi': 0.80, 'female': 0.7, 'deva': 0.76, 'guard': 0.98, 'nio': 1.08, 'ascetic': 0.78, 'demon': 1.05}[kind])
        self.pose = pose
        g = lambda k, d=(0, 0, 0): np.asarray(pose.get(k, d), float)
        # pelvis
        pz = pose.get('pelvis_z', H - 3.0 * hh)
        self.Rp = euler(*g('pelvis_rot'))
        self.Op = A(0, 0, pz) + np.r_[g('hip_shift', (0, 0))[:2], 0]
        self.W = self.Op + self.Rp @ A(0, 0.02 * hh, 0.48 * hh)
        self.Rw = self.Rp @ euler(*(g('chest_rot') * 0.5))
        self.Rc = self.Rp @ euler(*g('chest_rot'))
        self.Oc = self.W + self.Rw @ A(0, -0.02 * hh, 0.6 * hh)
        self.N = self.Oc + self.Rc @ A(0, -0.08 * hh, 0.72 * hh)
        self.Rh = self.Rc @ euler(*g('head_rot'))
        self.hs = pose.get('head_scale', 1.0); self.hhd = hh * self.hs          # head size (drawing) may exceed the body's head unit
        self.Oh = self.N + self.Rc @ A(0, 0.06 * hh, pose.get('neck', 0.2) * hh) + self.Rh @ A(0, 0.02 * hh, 0.55 * self.hhd)
        # arms
        l1, l2 = 1.28 * hh, 1.08 * hh
        self.arm = {}
        for s, nm in ((1, 'r'), (-1, 'l')):
            Sj = self.Oc + self.Rc @ A(s * self.sw, -0.1 * hh, 0.5 * hh)
            tgt = pose.get('hand_' + nm)
            pole = np.asarray(pose.get('elbow_' + nm, (s * 0.6, -1.0, -0.4)), float)
            if tgt is None: tgt = Sj + A(s * 0.25 * hh, 0.15 * hh, -2.25 * hh)
            E, Wr = ik2(Sj, tgt, l1, l2, pole)
            self.arm[nm] = dict(S=Sj, E=E, W=Wr, s=s)
        # legs
        self.leg = {}
        for s, nm in ((1, 'r'), (-1, 'l')):
            Hj = self.Op + self.Rp @ A(s * 0.40 * hh, 0.0, -0.22 * hh)
            # leg length: straight when the foot stands under the hip at ankle height (pose 'leg' scales it)
            ll = (self.Op[2] - 0.22 * hh - 0.28 * hh) * 1.004 * pose.get('leg', 1.0)
            if 'leg_len' in pose: ll = pose['leg_len'] * hh
            t1, t2 = 0.53 * ll, 0.47 * ll
            tgt = pose.get('foot_' + nm)
            if tgt is None: tgt = A(s * 0.36 * hh, 0.02 * hh, 0.30 * hh)
            pole = np.asarray(pose.get('knee_' + nm, (s * 0.1, 1.0, 0)), float)
            K, Ak = ik2(Hj, tgt, t1, t2, pole)
            self.leg[nm] = dict(H=Hj, K=K, A=Ak, s=s, foot_dir=np.asarray(pose.get('footdir_' + nm, (s * 0.15, 1, 0)), float))

    def hp(self, R, O, v):            # local (head units) -> world
        return O + R @ (np.asarray(v, float) * self.hh)

# ---------------------------------------------------------------------------------------------- body
def add_body(f, fig, skin='skin', bare_torso=True, k=None):
    hh = fig.hh; m = fig.musc; Lb = L[skin]
    kk = k if k is not None else 0.11 * hh
    Rc, Oc, Rp, Op, Rw = fig.Rc, fig.Oc, fig.Rp, fig.Op, fig.Rw
    c = lambda v: fig.hp(Rc, Oc, v); p = lambda v: fig.hp(Rp, Op, v); w = lambda v: fig.hp(Rw, fig.W, v)
    thin = 1.0 + 0.1 * min(m, 0)
    # torso
    f.add(Ellipsoid(c((0, 0.0, 0.05)), A(0.66 + 0.1 * m, 0.48 + 0.05 * m, 0.72) * hh * thin, Rc), Lb, kk)
    f.add(Ellipsoid(w((0, 0.05, 0.0)), A(0.55 + 0.06 * m, 0.42 + 0.06 * max(m, 0), 0.55) * hh * thin, Rw), Lb, kk)
    f.add(Ellipsoid(p((0, -0.02, 0.0)), A(0.66 + 0.06 * m, 0.45, 0.48) * hh, Rp), Lb, kk)
    for s in (1, -1):
        f.add(Ellipsoid(p((s * 0.27, -0.22, -0.12)), A(0.36, 0.3, 0.36) * hh, Rp), Lb, kk * 0.8)        # buttocks
        f.add(Ellipsoid(c((s * (0.5 + 0.08 * m), -0.12, 0.42)), A(0.36, 0.3, 0.2) * hh, Rc @ rot((0, 1, 0), s * 0.25)), Lb, kk)   # trapezius / shoulder top
    if m > 0.1:
        ks = 0.035 * hh if m > 0.5 else 0.05 * hh
        for s in (1, -1):
            # pectorals: a heavy plate with a crisp lower border
            f.add(Ellipsoid(c((s * 0.29, 0.32, 0.14)), A(0.33, 0.12 + 0.1 * m, 0.24) * hh, Rc @ rot((0, 1, 0), -s * 0.22) @ rot((1, 0, 0), 0.15)), Lb, ks)
            # abdominal blocks (three rows) and the obliques over the hips
            for zi, zz in enumerate((-0.02, -0.3, -0.58)):
                f.add(Ellipsoid(w((s * 0.125, 0.43 + 0.04 * m - 0.02 * zi, zz + 0.1)), A(0.115, 0.06 * m + 0.03, 0.115) * hh, Rw), Lb, ks * 0.8)
            f.add(Ellipsoid(w((s * 0.47, 0.18, -0.35)), A(0.16, 0.22, 0.3) * hh * (0.7 + 0.35 * m), Rw), Lb, 0.05 * hh)
            for i in range(3):                                                                                   # serratus
                f.add(Ellipsoid(c((s * 0.5, 0.26 - 0.03 * i, -0.18 - 0.13 * i)), A(0.07, 0.07, 0.05) * hh * (0.6 + 0.5 * m), Rc), Lb, 0.03 * hh)
            f.add(Capsule(c((s * 0.06, 0.38, 0.62)), c((s * 0.55, 0.12, 0.6)), 0.06 * hh), Lb, 0.05 * hh)        # clavicle
            f.add(Ellipsoid(c((s * 0.36, -0.25, 0.1)), A(0.3, 0.2, 0.42) * hh * (0.7 + 0.3 * m), Rc), Lb, 0.06 * hh)   # lats / back
        if m > 0.5:
            f.sub(Capsule(c((0, 0.5, 0.42)), c((0, 0.47, -0.05)), 0.028 * hh), 0.04 * hh)                      # sternum groove
            f.sub(Capsule(w((0, 0.52, 0.2)), w((0, 0.5, -0.65)), 0.02 * hh), 0.03 * hh)                         # linea alba
            for s in (1, -1):
                f.sub(Tube([c((s * 0.04, 0.47, -0.1)), c((s * 0.3, 0.42, -0.14)), c((s * 0.56, 0.24, -0.05))], A(0.02, 0.022, 0.016) * hh), 0.03 * hh)
        if fig.kind in ('nio', 'demon'):
            f.add(Ellipsoid(w((0, 0.32, -0.3)), A(0.42, 0.24, 0.4) * hh, Rw), Lb, 0.1 * hh)                # belly
            f.add(Sphere(w((0, 0.555, -0.42)), 0.025 * hh), Lb, 0.02 * hh) if False else None
    elif m < -0.3:
        # ribs of the ascetic: grooves
        for i in range(5):
            for s in (1, -1):
                a0 = c((s * 0.12, 0.42, 0.25 - 0.17 * i)); a1 = c((s * 0.55, 0.15, 0.05 - 0.2 * i))
                f.sub(Capsule(a0, a1, 0.035 * hh), 0.03 * hh)
        f.sub(Ellipsoid(w((0, 0.5, 0.2)), A(0.35, 0.12, 0.3) * hh, Rw), 0.1 * hh)   # hollow belly
    else:
        f.add(Ellipsoid(c((0, 0.2, 0.1)), A(0.55, 0.32, 0.3) * hh, Rc), Lb, 0.12 * hh)   # soft chest
        if fig.kind == 'female':
            for s in (1, -1): f.add(Sphere(c((s * 0.26, 0.38, 0.0)), 0.2 * hh), Lb, 0.12 * hh)
    # neck
    f.add(RCone(fig.N - Rc @ A(0, 0, 0.15 * hh), fig.Oh + fig.Rh @ A(0, -0.06 * hh, -0.25 * hh), (0.36 + 0.08 * m) * hh, 0.27 * hh), Lb, 0.12 * hh)
    if m > 0.5:
        for s in (1, -1):   # sternocleidomastoid
            f.add(Capsule(fig.Oh + fig.Rh @ A(s * 0.25 * hh, -0.05 * hh, -0.25 * hh), fig.N + Rc @ A(s * 0.08 * hh, 0.2 * hh, -0.05 * hh), 0.08 * hh), Lb, 0.06 * hh)
    # arms
    for nm, a in fig.arm.items():
        add_arm(f, fig, a, Lb)
    for nm, g in fig.leg.items():
        add_leg(f, fig, g, Lb)

def add_arm(f, fig, a, Lb, r_up=None, r_fore=None, deltoid=True):
    hh = fig.hh; m = fig.musc
    S_, E, Wr = a['S'], a['E'], a['W']
    slim = 0.88 if fig.kind in ('bodhi', 'female') else 1.0
    ru = r_up or (0.21 + 0.05 * m) * hh * slim; rf = r_fore or (0.17 + 0.04 * m) * hh * slim
    f.add(RCone(S_, E, ru, ru * 0.82), Lb, 0.08 * hh)
    f.add(RCone(E, Wr, rf, rf * 0.62), Lb, 0.06 * hh)
    if deltoid:
        ax = nrm(E - S_)
        f.add(Ellipsoid(S_ + (E - S_) * 0.18 + A(0, 0, 0.03 * hh), A(0.25 + 0.04 * m, 0.25 + 0.04 * m, 0.36 + 0.03 * m) * hh, frame(z=ax, x=(1, 0, 0) if abs(ax[0]) < 0.9 else (0, 1, 0))), Lb, (0.08 - 0.04 * max(m, 0)) * hh)
    if m > 0.2:
        ax = nrm(E - S_)
        R = frame(z=ax, x=np.cross(ax, [0, 1, 0]) if abs(ax[1]) < 0.9 else [1, 0, 0])
        f.add(Ellipsoid(S_ + (E - S_) * 0.55, A(0.16, 0.16, 0.4) * hh * (0.75 + 0.2 * m), R), Lb, 0.05 * hh)
        ax2 = nrm(Wr - E)
        R2 = frame(z=ax2, x=np.cross(ax2, [0, 0, 1]) if abs(ax2[2]) < 0.9 else [1, 0, 0])
        f.add(Ellipsoid(E + (Wr - E) * 0.28, A(0.16, 0.15, 0.35) * hh * (0.7 + 0.3 * m), R2), Lb, 0.06 * hh)

def add_leg(f, fig, g, Lb, foot=True):
    hh = fig.hh; m = fig.musc
    Hj, K, Ak = g['H'], g['K'], g['A']
    f.add(RCone(Hj, K, (0.33 + 0.05 * m) * hh, (0.21 + 0.02 * m) * hh), Lb, 0.12 * hh)
    f.add(RCone(K, Ak, (0.2 + 0.02 * m) * hh, 0.12 * hh), Lb, 0.06 * hh)
    ax = nrm(Ak - K)
    fd = nrm(g['foot_dir'] - ax * (g['foot_dir'] @ ax))
    f.add(Ellipsoid(K + (Ak - K) * 0.3 - fd * 0.06 * hh, A(0.17, 0.17, 0.42) * hh * (0.8 + 0.3 * max(m, 0)), frame(z=ax, y=fd)), Lb, 0.06 * hh)   # calf
    f.add(Sphere(K + fd * 0.05 * hh, 0.17 * hh), Lb, 0.06 * hh)    # knee cap
    if m > 0.2:
        ax1 = nrm(K - Hj)
        f.add(Ellipsoid(Hj + (K - Hj) * 0.55 + fd * 0.08 * hh, A(0.24, 0.22, 0.55) * hh, frame(z=ax1, y=fd)), Lb, 0.08 * hh)
    if foot: add_foot(f, fig, Ak, g['foot_dir'], Lb, g['s'])

def add_foot(f, fig, Ak, fdir, Lb, s, toes=True, scale=1.0):
    hh = fig.hh * scale
    fd = nrm(np.asarray(fdir, float) * A(1, 1, 0)); side = nrm(np.cross(fd, [0, 0, 1]))
    sole = Ak[2] - 0.26 * hh
    heel = A(Ak[0], Ak[1], sole + 0.1 * hh) - fd * 0.12 * hh
    toe = A(Ak[0], Ak[1], sole + 0.07 * hh) + fd * 0.78 * hh
    f.add(RCone(heel, Ak - fd * 0.02 * hh, 0.1 * hh, 0.13 * hh), Lb, 0.05 * hh)
    f.add(Ellipsoid((heel + toe) / 2 + A(0, 0, 0.03 * hh), A(0.23, 0.48, 0.12) * hh, frame(y=fd, z=(0, 0, 1))), Lb, 0.07 * hh)
    if toes:
        for i, (o, r, ln) in enumerate(((-0.13, 0.065, 0.12), (-0.03, 0.05, 0.11), (0.05, 0.045, 0.1), (0.12, 0.042, 0.08), (0.18, 0.04, 0.06))):
            b = toe + side * (-s) * o * hh * 1.0 - fd * 0.1 * hh + A(0, 0, -0.01 * hh)
            f.add(Capsule(b, b + fd * ln * hh * 1.2 - A(0, 0, 0.015 * hh), r * hh), Lb, 0.025 * hh)

# ---------------------------------------------------------------------------------------------- heads
class Band(S.Prim):
    """an elliptical band (crowns, belts, bracelets): frame M (columns), centre c, radii rx, ry, thickness t, half height hz"""
    def __init__(self, c, rx, ry, t, hz, M=None):
        self.c = np.asarray(c, F32); self.rx = rx; self.ry = ry; self.t = t; self.hz = hz; self.M = None if M is None else np.asarray(M, F32)
        e = np.array([rx + t, ry + t, hz + t], F32); e = e if self.M is None else np.abs(self.M) @ e
        self.lo = self.c - e; self.hi = self.c + e
    def d(self, P):
        q = P - self.c
        if self.M is not None: q = q @ self.M
        k0 = np.sqrt((q[:, 0] / self.rx) ** 2 + (q[:, 1] / self.ry) ** 2); k1 = np.sqrt((q[:, 0] / self.rx ** 2) ** 2 + (q[:, 1] / self.ry ** 2) ** 2)
        dxy = k0 * (k0 - 1) / np.maximum(k1, 1e-9)
        a = np.abs(dxy) - self.t; b = np.abs(q[:, 2]) - self.hz
        return np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0)

def add_head(f, R, O, hh, style='serene', ears='long', fierce=0.0, mouth='closed', age=0.0, k=None,
             skin='skin', eyes='crystal', urna=True, nose=1.0, brow=None, extra=None, jaw=1.0, beard=False):
    """a sculpted head in frame R (columns: right, forward, up), centre O (mid chin-vertex), size hh.
    style: serene (bodhisattva), deva (calm deity), female, fierce (guardian), demon (Fujin/Raijin), old (ascetic),
    oldwoman, bird (Karura)."""
    u = hh; Lb = L[skin]
    P = lambda v: O + R @ (np.asarray(v, float) * u)
    E = lambda c, r, rx=None: Ellipsoid(P(c), A(*r) * u, R if rx is None else R @ rx)
    fz = fierce; kk = 0.09 * u
    if style == 'bird':
        return add_bird_head(f, R, O, hh, skin)
    calm = style in ('serene', 'female', 'deva')
    wide = {'serene': 1.0, 'deva': 1.0, 'female': 0.9, 'fierce': 1.05, 'demon': 1.12, 'old': 0.88, 'oldwoman': 0.88}.get(style, 1.0)
    # skull and face masses
    f.add(E((0, -0.05, 0.08), (0.355, 0.43, 0.43)), Lb, kk)
    f.add(E((0, 0.14, 0.1), (0.3, 0.25, 0.25)), Lb, kk)
    f.add(E((0, 0.14, -0.12), (0.3 * wide, 0.26, 0.28)), Lb, kk)
    f.add(E((0, 0.1, -0.3), (0.27 * wide * jaw, 0.25, 0.19)), Lb, kk)
    f.add(E((0, 0.29, -0.42), (0.12, 0.08, 0.08 + 0.02 * fz)), Lb, 0.08 * u)                      # chin
    if calm and age < 0.5:
        f.add(E((0, 0.15, -0.47), (0.2, 0.15, 0.07)), Lb, 0.08 * u)                               # soft double chin
    for s in (1, -1):
        cr = 0.14 if calm else 0.12
        f.add(E((s * 0.19 * wide, 0.235, -0.14), (cr, 0.13, 0.15)), Lb, 0.1 * u)                  # cheeks
        if fz > 0.3:
            f.add(E((s * 0.19, 0.3, -0.1), (0.09, 0.07 * fz + 0.02, 0.07)), Lb, 0.05 * u)          # tensed cheek
            f.add(E((s * 0.2, 0.25, -0.3), (0.1, 0.08, 0.1)), Lb, 0.06 * u)                       # jowl
    if age > 0.5:
        for s in (1, -1):
            f.sub(E((s * 0.22, 0.36, -0.2), (0.07, 0.05, 0.1)), 0.06 * u)                         # hollow cheeks
            f.sub(E((s * 0.29, 0.14, 0.1), (0.05, 0.09, 0.08)), 0.05 * u)                         # temples
            f.add(E((s * 0.2, 0.3, -0.02), (0.08, 0.06, 0.04)), Lb, 0.03 * u)                     # cheekbones
    if not calm or fz > 0.3:
        for s in (1, -1):
            f.add(E((s * 0.235, 0.26, -0.02), (0.085, 0.07, 0.06), rot((0, 1, 0), -s * 0.4)), Lb, 0.04 * u)      # cheekbones
            if fz > 0.3:
                f.sub(Tube([P((s * 0.075, 0.45, -0.17)), P((s * 0.14, 0.42, -0.25)), P((s * 0.16, 0.38, -0.34))], A(0.01, 0.014, 0.01) * u), 0.012 * u)   # nasolabial
                f.add(Tube([P((s * 0.09, 0.43, -0.17)), P((s * 0.16, 0.395, -0.25))], A(0.03, 0.025) * u), Lb, 0.02 * u)
    # brows and eyes
    ex = 0.155
    for s in (1, -1):
        xs = s * ex
        if calm and fz < 0.3:
            f.add(Tube([P((s * 0.03, 0.415, 0.05)), P((s * 0.14, 0.4, 0.105)), P((s * 0.26, 0.335, 0.08)), P((s * 0.32, 0.24, 0.03))],
                       A(0.016, 0.02, 0.016, 0.01) * u), Lb, 0.05 * u)
            f.sub(E((xs, 0.41, 0.025), (0.12, 0.06, 0.055)), 0.06 * u)                            # socket under the brow
            f.add(E((xs, 0.305, -0.02), (0.1, 0.08, 0.05), rot((0, 1, 0), -s * 0.1)), Lb, 0.03 * u)   # lid bulge
            ang = rot((0, 1, 0), -s * 0.17)
            slit = Ellipsoid(P((xs + s * 0.005, 0.388, -0.03)), A(0.085, 0.03, 0.0075 if eyes == 'crystal' else 0.006) * u, R @ ang)
            f.sub(slit, 0.006 * u, lab=L['eye'] if eyes == 'crystal' else None)
            if eyes == 'crystal':
                f.add(Ellipsoid(P((xs + s * 0.005, 0.376, -0.032)), A(0.07, 0.02, 0.005) * u, R @ ang), L['eye'], 0.0)
            # upper lid edge: a fine ridge over the slit
            f.add(Ellipsoid(P((xs + s * 0.004, 0.383, -0.02)), A(0.088, 0.03, 0.009) * u, R @ ang), Lb, 0.008 * u)
        else:
            br = brow if brow is not None else fz
            er = 0.066 + 0.008 * fz + 0.01 * (style == 'demon')
            yb = 0.285 + 0.03 * fz + 0.025 * (style in ('old', 'oldwoman'))
            ec = P((xs, yb, -0.01))
            # socket, eyeball (whites), crystal iris
            f.sub(E((xs, 0.43, 0.0), (0.112, 0.075, 0.062 + 0.008 * fz)), 0.03 * u)
            f.add(Sphere(ec, er * u), L['eyew'], 0.006 * u)
            f.paint(Sphere(ec + R @ A(0, er * 0.96, -0.004) * u, er * (0.72 if style == 'demon' else (0.6 if style in ('old', 'oldwoman') else 0.84)) * u), L['eye'])
            # almond opening: a heavy arched upper lid and a thinner lower lid
            yl = yb + er * 0.62
            op = 0.012 * fz
            f.add(Tube([P((xs - s * 0.105, yl - 0.03, -0.004)), P((xs - s * 0.035, yl + 0.006, 0.058 + op)), P((xs + s * 0.05, yl - 0.004, 0.058 + op)),
                        P((xs + s * 0.115, yl - 0.05, 0.006))], A(0.016, 0.024, 0.023, 0.014) * u), Lb, 0.012 * u)
            f.add(Tube([P((xs - s * 0.1, yl - 0.03, -0.026)), P((xs, yl - 0.008, -0.07 - op * 0.5)), P((xs + s * 0.11, yl - 0.05, -0.024))],
                       A(0.01, 0.012, 0.009) * u), Lb, 0.01 * u)
            # brow: a fleshy ridge, inner end pulled down and in when angry
            f.add(Tube([P((s * 0.035, 0.43, 0.07 - 0.03 * br)), P((s * 0.13, 0.425, 0.115 + 0.01 * br)), P((s * 0.24, 0.385, 0.11)), P((s * 0.31, 0.3, 0.07))],
                       A(0.03, 0.04 + 0.012 * br, 0.035, 0.018) * u), Lb, 0.03 * u)
            if br > 0.4:
                f.add(Ellipsoid(P((s * 0.055, 0.425, 0.1)), A(0.05, 0.045, 0.06) * u), Lb, 0.03 * u)       # knotted brow
        if fz > 0.5:
            f.sub(Capsule(P((s * 0.022, 0.44, 0.05)), P((s * 0.032, 0.43, 0.16)), 0.011 * u), 0.012 * u)   # frown furrows
    if fz > 0.5:
        for zz in (0.21, 0.27):
            f.sub(Tube([P((-0.19, 0.35, zz - 0.02)), P((0, 0.4, zz + 0.01)), P((0.19, 0.35, zz - 0.02))], A(0.008, 0.011, 0.008) * u), 0.01 * u)
    if age > 0.5:
        for zz in (0.17, 0.22, 0.27):
            f.sub(Tube([P((-0.2, 0.34, zz)), P((0, 0.38, zz + 0.012)), P((0.2, 0.34, zz))], A(0.005, 0.008, 0.005) * u), 0.008 * u)
        for s in (1, -1):
            f.sub(Tube([P((s * 0.08, 0.45, -0.2)), P((s * 0.15, 0.41, -0.29)), P((s * 0.14, 0.38, -0.37))], A(0.007, 0.01, 0.007) * u), 0.01 * u)
            f.sub(Tube([P((s * 0.21, 0.36, -0.03)), P((s * 0.27, 0.3, -0.06)), P((s * 0.3, 0.24, -0.02))], A(0.005, 0.006, 0.004) * u), 0.006 * u)   # crow's feet
    # nose
    nw = 1.0 + 0.55 * fz
    if style == 'demon':
        f.add(RCone(P((0, 0.43, 0.04)), P((0, 0.52, -0.15)), 0.035 * u, 0.06 * u), Lb, 0.04 * u)
        for s in (1, -1):
            f.add(Sphere(P((s * 0.08, 0.45, -0.17)), 0.058 * u), Lb, 0.04 * u)
            f.sub(Ellipsoid(P((s * 0.05, 0.49, -0.205)), A(0.025, 0.03, 0.016) * u, R), 0.01 * u)
    else:
        nl = 0.475 + 0.01 * nose
        f.add(RCone(P((0, 0.418, 0.055)), P((0, nl, -0.165)), 0.021 * u, 0.033 * u * nw), Lb, 0.035 * u)
        f.add(Sphere(P((0, nl - 0.012, -0.172)), 0.038 * u * (1 + 0.2 * fz)), Lb, 0.02 * u)
        for s in (1, -1):
            f.add(Sphere(P((s * 0.05 * nw, 0.42, -0.188)), 0.035 * u * nw), Lb, 0.03 * u)
            f.sub(Ellipsoid(P((s * 0.032 * nw, 0.445, -0.213)), A(0.018, 0.022, 0.011) * u * nw, R), 0.008 * u)
    # mouth
    zm = -0.29
    if mouth == 'open':
        mw = 0.1 + 0.035 * fz + 0.02 * (style == 'demon')
        mh = 0.05 + 0.015 * fz + 0.025 * (style == 'demon')
        # the opening: a wide rounded slot, the upper lip drawn up in the middle (snarl)
        f.sub(Box(P((0, 0.42, zm)), A(mw, 0.12, mh) * u, R, mh * 0.8 * u), 0.012 * u, lab=L['mouth'])
        f.sub(Ellipsoid(P((0, 0.42, zm + mh * 0.6)), A(mw * 0.55, 0.12, mh * 0.55) * u, R), 0.01 * u, lab=L['mouth'])
        # lips: tubes round the slot
        up_l = [P((-mw - 0.012, 0.35, zm + 0.005)), P((-mw * 0.55, 0.385, zm + mh * 1.05)), P((0, 0.4, zm + mh * 1.4)), P((mw * 0.55, 0.385, zm + mh * 1.05)), P((mw + 0.012, 0.35, zm + 0.005))]
        lo_l = [P((-mw - 0.012, 0.35, zm + 0.005)), P((-mw * 0.5, 0.375, zm - mh * 1.08)), P((0, 0.385, zm - mh * 1.15)), P((mw * 0.5, 0.375, zm - mh * 1.08)), P((mw + 0.012, 0.35, zm + 0.005))]
        f.add(Tube(spline(up_l, 12), np.full(12, 0.02) * u), L['lip'], 0.015 * u)
        f.add(Tube(spline(lo_l, 12), np.full(12, 0.022) * u), L['lip'], 0.015 * u)
        # teeth: an upper row under the raised lip, a lower row
        f.add(Box(P((0, 0.375, zm + mh * 0.62)), A(mw * 0.82, 0.022, mh * 0.32) * u, R, 0.006 * u), L['teeth'], 0.003 * u)
        f.add(Box(P((0, 0.365, zm - mh * 0.66)), A(mw * 0.72, 0.022, mh * 0.28) * u, R, 0.006 * u), L['teeth'], 0.003 * u)
        for k_ in range(-3, 4):      # gaps between the teeth
            f.sub(Box(P((k_ * mw * 0.22, 0.4, zm + mh * 0.62)), A(0.004, 0.03, mh * 0.34) * u, R, 0.0), 0.0)
        for s in (1, -1):
            if style == 'demon' or fierce > 1.0:
                f.add(RCone(P((s * mw * 0.62, 0.37, zm + mh * 0.7)), P((s * mw * 0.6, 0.38, zm - mh * 0.3)), 0.016 * u, 0.004 * u), L['teeth'], 0.0)
            if style == 'demon':
                f.add(RCone(P((s * mw * 0.75, 0.36, zm - mh * 0.75)), P((s * mw * 0.82, 0.38, zm + mh * 0.5)), 0.017 * u, 0.004 * u), L['teeth'], 0.0)
        f.add(Ellipsoid(P((0, 0.28, zm - mh * 0.5)), A(0.07, 0.1, 0.03) * u, R), L['mouth'], 0.02 * u)       # tongue
    else:
        smile = {'serene': 0.008, 'female': 0.008, 'deva': 0.004, 'old': -0.012, 'oldwoman': -0.006}.get(style, -0.018 - 0.02 * fz)
        lw = 0.1 if calm else 0.11
        f.add(Ellipsoid(P((0, 0.37, zm + 0.02)), A(lw, 0.04, 0.026) * u, R), Lb, 0.02 * u)
        f.add(Ellipsoid(P((0, 0.355, zm - 0.025)), A(lw * 0.8, 0.04, 0.026) * u, R), Lb, 0.02 * u)
        f.paint(Ellipsoid(P((0, 0.4, zm + 0.016)), A(lw * 0.92, 0.04, 0.019) * u, R), L['lip'])
        f.paint(Ellipsoid(P((0, 0.39, zm - 0.022)), A(lw * 0.74, 0.04, 0.02) * u, R), L['lip'])
        f.sub(Tube([P((-lw - 0.006, 0.36, zm + smile)), P((-lw * 0.5, 0.41, zm - 0.002)), P((0, 0.425, zm + 0.002)), P((lw * 0.5, 0.41, zm - 0.002)), P((lw + 0.006, 0.36, zm + smile))],
                   A(0.003, 0.0045, 0.005, 0.0045, 0.003) * u), 0.005 * u)
        for s in (1, -1): f.sub(Sphere(P((s * (lw + 0.006), 0.35, zm + smile)), 0.011 * u), 0.012 * u)
        f.sub(Ellipsoid(P((0, 0.418, zm + 0.06)), A(0.017, 0.012, 0.025) * u, R), 0.01 * u)     # philtrum
        if mouth == 'clenched':
            f.add(Ellipsoid(P((0, 0.33, zm - 0.06)), A(0.12, 0.08, 0.05) * u, R), Lb, 0.03 * u)
    if beard:
        f.add(Tube([P((0, 0.3, -0.42)), P((0, 0.33, -0.6)), P((0.01, 0.32, -0.85)), P((0.02, 0.3, -1.0))], A(0.07, 0.06, 0.035, 0.008) * u), L['beard'], 0.04 * u)
        for s in (1, -1):
            f.add(Tube([P((s * 0.05, 0.42, -0.255)), P((s * 0.12, 0.4, -0.29)), P((s * 0.16, 0.37, -0.36))], A(0.016, 0.012, 0.004) * u), L['beard'], 0.008 * u)
    # ears
    for s in (1, -1):
        if ears == 'long':
            f.add(Ellipsoid(P((s * 0.355, 0.0, -0.03)), A(0.035, 0.09, 0.17) * u, R @ rot((1, 0, 0), -0.12) @ rot((0, 1, 0), -s * 0.2)), Lb, 0.02 * u)
            f.add(Ellipsoid(P((s * 0.35, 0.025, -0.29)), A(0.035, 0.055, 0.1) * u, R), Lb, 0.03 * u)
            f.sub(Ellipsoid(P((s * 0.392, 0.01, 0.0)), A(0.024, 0.055, 0.11) * u, R @ rot((0, 1, 0), -s * 0.2)), 0.012 * u)
            f.sub(Ellipsoid(P((s * 0.38, 0.025, -0.3)), A(0.03, 0.02, 0.05) * u, R), 0.01 * u)
        elif ears == 'pointed':
            f.add(Ellipsoid(P((s * 0.37, -0.02, 0.0)), A(0.03, 0.11, 0.16) * u, R @ rot((0, 1, 0), -s * 0.5) @ rot((1, 0, 0), -0.4)), Lb, 0.02 * u)
            f.add(RCone(P((s * 0.38, -0.05, 0.08)), P((s * 0.52, -0.12, 0.24)), 0.045 * u, 0.008 * u), Lb, 0.02 * u)
            f.sub(Ellipsoid(P((s * 0.4, 0.0, 0.0)), A(0.02, 0.06, 0.1) * u, R @ rot((0, 1, 0), -s * 0.5)), 0.01 * u)
        elif ears == 'normal':
            f.add(Ellipsoid(P((s * 0.355, -0.02, -0.04)), A(0.035, 0.09, 0.14) * u, R @ rot((0, 1, 0), -s * 0.25)), Lb, 0.02 * u)
            f.sub(Ellipsoid(P((s * 0.39, -0.0, -0.03)), A(0.022, 0.05, 0.08) * u, R @ rot((0, 1, 0), -s * 0.25)), 0.01 * u)
    if urna:
        f.add(Sphere(P((0, 0.41, 0.1)), 0.019 * u), L['eye'] if urna == 'crystal' else Lb, 0.004 * u)
    if extra: extra(f, P, u)

def neck_folds(f, fig, n=2):
    """三道: grooves around the neck"""
    hh = fig.hh; R = fig.Rh; O = fig.Oh
    for i in range(n):
        z = -0.62 - 0.1 * i
        f.sub(Torus(O + R @ A(0, 0.02, z) * hh, 0.25 * hh, 0.008 * hh, R @ frame(z=(0, 0.25, 1), x=(1, 0, 0)), sx=1.0, sy=0.9), 0.008 * hh)

def add_hair(f, R, O, hh, kind='bodhi', lab='hair', crown=True, seed=0):
    """hair cap and topknot.  kind: bodhi (combed up, high topknot), bun (low topknot), flame (Raijin spikes),
    curls (Fujin), cap (cloth cap), short"""
    u = hh; P = lambda v: O + R @ (np.asarray(v, float) * u); Lh = L[lab]
    E = lambda c, r, rx=None: Ellipsoid(P(c), A(*r) * u, R if rx is None else R @ rx)
    # hair cap above a hairline plane (front at the forehead, back at the nape)
    hairline = Plane(P((0, 0.37, 0.2)), R @ nrm(A(0, 0.5, -0.72)))
    if kind in ('bodhi', 'bun', 'short', 'deva'):
        cap = Inter([E((0, -0.05, 0.095), (0.375, 0.445, 0.44)), hairline], 0.02 * u)
        f.add(cap, Lh, 0.01 * u)
        # locks over the ears to the back
        for s in (1, -1):
            f.add(Tube([P((s * 0.3, 0.2, 0.15)), P((s * 0.37, 0.08, 0.02)), P((s * 0.36, -0.12, -0.06)), P((s * 0.25, -0.3, -0.1))], A(0.05, 0.06, 0.06, 0.05) * u), Lh, 0.03 * u)
        if kind == 'bodhi':
            f.add(E((0, -0.04, 0.53), (0.17, 0.17, 0.14)), Lh, 0.06 * u)
            f.add(E((0, -0.04, 0.66), (0.14, 0.14, 0.13)), Lh, 0.04 * u)
            f.sub(Torus(P((0, -0.04, 0.6)), 0.15 * u, 0.012 * u), 0.01 * u)
            for s in (1, -1):    # hair falling behind the shoulders
                f.add(Tube([P((s * 0.3, -0.22, -0.1)), P((s * 0.36, -0.2, -0.45)), P((s * 0.46, -0.12, -0.75)), P((s * 0.55, -0.05, -0.95))], A(0.05, 0.045, 0.04, 0.03) * u), Lh, 0.04 * u)
        elif kind in ('bun', 'deva'):
            f.add(E((0, -0.08, 0.55), (0.15, 0.15, 0.17)), Lh, 0.06 * u)
            f.add(Band(P((0, -0.08, 0.5)), 0.155 * u, 0.155 * u, 0.012 * u, 0.025 * u, R), L['crown'], 0.0)
        # strands: shallow grooves combed toward the crown
        def strands(Q):
            q = (Q - O) @ R / u
            phi = np.arctan2(q[:, 0], q[:, 1] + 0.1)
            return 0.006 * u * np.sin(phi * 34)
        f.add(Displace(Inter([E((0, -0.05, 0.095), (0.37, 0.44, 0.435)), hairline]), strands, 0.007 * u), Lh, 0.0)
    elif kind == 'flame':
        f.add(Inter([E((0, -0.05, 0.1), (0.38, 0.45, 0.45)), hairline], 0.02 * u), Lh, 0.02 * u)
        rng = np.random.default_rng(seed)
        for i in range(13):
            a = -1.25 + 2.5 * i / 12 + rng.uniform(-0.06, 0.06)
            base = P((0.3 * math.sin(a), -0.05 + 0.25 * math.cos(a) * 0.5, 0.38))
            tip = P((0.75 * math.sin(a) * 1.1, -0.2 + 0.1 * rng.uniform(-1, 1), 1.15 + 0.25 * math.cos(a) + rng.uniform(-0.1, 0.1)))
            mid = (base + tip) / 2 + R @ A(0.08 * math.sin(a * 3), -0.08, 0) * u
            f.add(Tube([base, mid, tip], A(0.09, 0.05, 0.008) * u), Lh, 0.05 * u)
    elif kind == 'curls':
        f.add(Inter([E((0, -0.05, 0.1), (0.385, 0.45, 0.45)), hairline], 0.02 * u), Lh, 0.02 * u)
        rng = np.random.default_rng(seed)
        for i in range(16):
            a = rng.uniform(-1.6, 1.6); e = rng.uniform(0.25, 1.1)
            c = P((0.4 * math.sin(a) * math.cos(e * 0.6), -0.05 - 0.2 * math.cos(a) * 0.4, 0.2 + 0.32 * math.sin(e)))
            f.add(Torus(c, 0.07 * u, 0.04 * u, R @ rot((1, 0, 0), rng.uniform(0, 3)) @ rot((0, 1, 0), rng.uniform(0, 3))), Lh, 0.03 * u)
    elif kind == 'cap':
        f.add(Inter([E((0, -0.06, 0.12), (0.39, 0.46, 0.46)), Plane(P((0, 0.3, 0.17)), R @ nrm(A(0, 0.35, -1)))], 0.02 * u), L['cap'], 0.01 * u)
        f.add(Tube([P((0.02, -0.05, 0.5)), P((-0.05, 0.1, 0.62)), P((-0.12, 0.25, 0.55))], A(0.14, 0.1, 0.05) * u), L['cap'], 0.06 * u)
        for s in (1, -1):    # flaps over the ears to the shoulders
            f.add(Ellipsoid(P((s * 0.36, -0.12, -0.2)), A(0.06, 0.22, 0.4) * u, R @ rot((1, 0, 0), 0.2)), L['cap'], 0.05 * u)
        f.add(Ellipsoid(P((0, -0.35, -0.25)), A(0.32, 0.08, 0.4) * u, R @ rot((1, 0, 0), -0.2)), L['cap'], 0.06 * u)
    elif kind == 'hood':          # old woman's veil
        f.add(Inter([E((0, -0.06, 0.1), (0.4, 0.47, 0.46)), Plane(P((0, 0.33, 0.2)), R @ nrm(A(0, 0.4, -1)))], 0.03 * u), L['robe2'], 0.01 * u)
        f.add(Ellipsoid(P((0, -0.25, -0.35)), A(0.42, 0.3, 0.5) * u, R), L['robe2'], 0.1 * u)

def add_bird_head(f, R, O, hh, skin='skin'):
    """迦楼羅 Karura: bird head with a hooked beak, round eyes, crest"""
    u = hh; P = lambda v: O + R @ (np.asarray(v, float) * u); Lb = L[skin]
    f.add(Ellipsoid(P((0, -0.05, 0.05)), A(0.36, 0.44, 0.42) * u, R), Lb, 0.08 * u)
    f.add(Ellipsoid(P((0, 0.18, -0.08)), A(0.25, 0.25, 0.25) * u, R), Lb, 0.08 * u)
    beak = Tube([P((0, 0.25, -0.02)), P((0, 0.5, -0.05)), P((0, 0.68, -0.15)), P((0, 0.7, -0.26))], A(0.16, 0.1, 0.05, 0.015) * u)
    f.add(beak, L['lip'], 0.04 * u)
    f.add(Tube([P((0, 0.25, -0.2)), P((0, 0.45, -0.2)), P((0, 0.56, -0.24))], A(0.12, 0.07, 0.02) * u), L['lip'], 0.03 * u)
    f.sub(Tube([P((-0.2, 0.42, -0.165)), P((0, 0.6, -0.17)), P((0.2, 0.42, -0.165))], A(0.012, 0.012, 0.012) * u), 0.01 * u)
    for s in (1, -1):
        ec = P((s * 0.19, 0.27, 0.07))
        f.add(Sphere(ec, 0.075 * u), L['eyew'], 0.01 * u)
        f.paint(Sphere(ec + R @ A(s * 0.03, 0.06, 0) * u, 0.05 * u), L['eye'])
        f.add(Torus(ec, 0.075 * u, 0.018 * u, R @ frame(z=(s * 0.5, 1, 0.1), x=(1, 0, 0))), Lb, 0.015 * u)
        f.add(Ellipsoid(P((s * 0.18, 0.28, 0.17)), A(0.11, 0.07, 0.04) * u, R @ rot((0, 1, 0), s * 0.4)), Lb, 0.04 * u)
    # crest feathers
    for i in range(5):
        a = -0.5 + i * 0.25
        f.add(Tube([P((0.0 + 0.15 * a, -0.05, 0.4)), P((0.25 * a, -0.1, 0.62)), P((0.35 * a, -0.25, 0.78))], A(0.07, 0.05, 0.01) * u), L['feather'], 0.04 * u)

# ---------------------------------------------------------------------------------------------- hands
HAND_POSES = {
    #          index (mcp, pip, dip)  middle            ring              little            thumb (cmc_abd, mcp, ip, rot)   spread
    'open':    ((0.08, 0.12, 0.08), (0.08, 0.14, 0.1), (0.12, 0.18, 0.1), (0.18, 0.24, 0.12), (0.45, 0.15, 0.15, 0.3), 0.12),
    'relaxed': ((0.35, 0.45, 0.3), (0.45, 0.55, 0.35), (0.55, 0.65, 0.4), (0.65, 0.75, 0.45), (0.5, 0.3, 0.3, 0.6), 0.08),
    'grip':    ((1.25, 1.55, 0.9), (1.35, 1.6, 0.9), (1.45, 1.6, 0.9), (1.55, 1.6, 0.9), (0.9, 0.5, 0.6, 1.2), 0.0),
    'fist':    ((1.55, 1.9, 1.1), (1.6, 1.95, 1.1), (1.65, 1.95, 1.1), (1.7, 1.95, 1.1), (1.0, 0.7, 0.7, 1.3), 0.0),
    'prayer':  ((0.05, 0.08, 0.05), (0.05, 0.08, 0.05), (0.05, 0.08, 0.05), (0.06, 0.1, 0.05), (0.12, 0.1, 0.1, 0.1), 0.0),
    'pinch':   ((0.75, 0.9, 0.5), (0.95, 1.2, 0.7), (1.15, 1.35, 0.8), (1.3, 1.45, 0.8), (0.95, 0.35, 0.4, 1.0), 0.03),
    'mudra':   ((0.6, 0.95, 0.6), (0.15, 0.2, 0.1), (0.12, 0.18, 0.1), (0.2, 0.2, 0.1), (0.9, 0.3, 0.4, 1.0), 0.1),
    'cup':     ((0.25, 0.3, 0.2), (0.25, 0.3, 0.2), (0.3, 0.35, 0.2), (0.35, 0.4, 0.2), (0.4, 0.2, 0.2, 0.4), 0.02),
    'claw':    ((0.7, 1.0, 0.7), (0.7, 1.05, 0.7), (0.75, 1.05, 0.7), (0.8, 1.1, 0.7), (0.7, 0.5, 0.6, 0.9), 0.25),
    'spread':  ((0.15, 0.2, 0.15), (0.15, 0.2, 0.15), (0.18, 0.25, 0.15), (0.25, 0.3, 0.15), (0.9, 0.15, 0.1, 0.4), 0.3),
    'point':   ((0.05, 0.1, 0.05), (1.4, 1.7, 1.0), (1.5, 1.7, 1.0), (1.6, 1.7, 1.0), (0.9, 0.5, 0.6, 1.2), 0.05),
}

def hand_field(pose='open', Lh=0.15, musc=0.0, fingers=5, claws=False, lab='skin', name='hand', bracelet=None, seg_sep=True, nails=True):
    """a right hand in its local frame: wrist at the origin, fingers along +x, back of the hand +z, thumb +y.
    Mirror y for a left hand.  fingers 5 (human), 4 (Fujin), 3 (Raijin)."""
    f = Field(name); u = Lh; Lb = L[lab]
    fp = HAND_POSES[pose]
    pw = 0.45 * u; th = (0.13 + 0.03 * musc) * u
    # palm: rounded box + thenar
    f.add(Box(A(0.24 * u, 0, 0), A(0.23 * u, 0.2 * u, th / 2), None, th * 0.45), Lb, 0.0)
    f.add(Ellipsoid(A(0.12 * u, 0.12 * u, -0.03 * u), A(0.15, 0.08, 0.07) * u), Lb, 0.04 * u)
    f.add(Ellipsoid(A(0.15 * u, -0.13 * u, -0.02 * u), A(0.15, 0.06, 0.055) * u), Lb, 0.04 * u)
    f.add(RCone(A(-0.25 * u, 0, 0), A(0.04 * u, 0, 0), 0.15 * u, 0.13 * u), Lb, 0.06 * u)       # wrist
    if pose == 'cup' or pose == 'prayer':
        f.sub(Ellipsoid(A(0.25 * u, 0, -0.12 * u), A(0.17, 0.13, 0.07) * u), 0.04 * u) if pose == 'cup' else None
    if fingers == 5:
        defs = [(0.17, 0.5, 0.048), (0.05, 0.55, 0.05), (-0.07, 0.52, 0.047), (-0.17, 0.42, 0.042)]
        curls = fp[:4]
    elif fingers == 4:
        defs = [(0.15, 0.5, 0.06), (0.02, 0.55, 0.062), (-0.12, 0.48, 0.058)]; curls = fp[:3]
    else:
        defs = [(0.12, 0.52, 0.068), (-0.08, 0.5, 0.065)]; curls = (fp[0], fp[2])
    spread = fp[5]
    for i, ((yy, ln, r), cu) in enumerate(zip(defs, curls)):
        r = r * u * (1 + 0.15 * musc); ln = ln * u
        sp = spread * (yy / 0.17) * (1 if fingers == 5 else 1.3)
        d = A(math.cos(sp), math.sin(sp), 0); up = A(0, 0, 1)
        p = A(0.46 * u, yy * u, 0.005 * u)
        pts = [p - d * 0.06 * u, p]; ang = 0.0
        for seg, frac in enumerate((0.45, 0.3, 0.25)):
            ang += cu[seg]
            dd = d * math.cos(ang) - up * math.sin(ang)
            p = p + dd * ln * frac; pts.append(p)
        rad = [r * 1.12, r * 1.0, r * 0.9, r * 0.84, r * (0.7 if claws else 0.78)]
        f.add(Tube(pts, rad), Lb, 0.007 * u if seg_sep else 0.02 * u)
        f.add(Sphere(pts[1] + up * r * 0.25, r * 1.05), Lb, 0.012 * u)        # knuckle
        for j in (2, 3):                                                       # finger joints
            f.add(Sphere(pts[j], rad[j] * 1.07), Lb, 0.004 * u)
        f.sub(Ellipsoid(pts[-1] + (pts[-1] - pts[-2]) * 0.1 + up * r * 0.55, A(r * 0.55, r * 0.7, r * 0.18), frame(z=up, x=nrm(pts[-1] - pts[-2]))), 0.003 * u) if nails else None
        if claws:
            dd = pts[-1] - pts[-2]; dd = nrm(dd)
            f.add(RCone(pts[-1], pts[-1] + dd * 0.09 * u - up * 0.03 * u, r * 0.75, 0.004 * u), L['nail'] if 'nail' in L else Lb, 0.01 * u)
    # thumb
    ab, m1, m2, rr = fp[4]
    b0 = A(0.06 * u, 0.15 * u, -0.02 * u)
    dth = nrm(A(math.cos(0.75 - 0.35 * ab), math.sin(0.75 - 0.35 * ab), -0.25 - 0.55 * rr))
    nrot = nrm(np.cross(dth, A(0, 0, 1)))
    p1 = b0 + dth * 0.2 * u
    d2 = rot(nrot, -m1) @ dth if True else dth
    d2 = nrm(d2 - A(0, 0.4 * ab, 0.3 * rr) * 0.5)
    p2 = p1 + d2 * 0.17 * u
    d3 = nrm(rot(nrot, -m2) @ d2)
    p3 = p2 + d3 * 0.14 * u
    tr = 0.058 * u * (1 + 0.15 * musc) * (1.15 if fingers < 5 else 1.0)
    f.add(Tube([b0, p1, p2, p3], [tr * 1.4, tr * 1.1, tr, tr * 0.82]), Lb, 0.04 * u)
    if claws:
        f.add(RCone(p3, p3 + d3 * 0.08 * u, tr * 0.7, 0.004 * u), Lb, 0.01 * u)
    if bracelet:
        f.add(Torus(A(-0.06 * u, 0, 0), 0.155 * u, 0.025 * u, frame(z=(1, 0, 0), x=(0, 1, 0))), L[bracelet], 0.005 * u)
    return f

def hand_xf(wrist, fdir, back, side):
    """placement (R, t) for a hand mesh: wrist position, finger direction, back-of-hand direction; side +1 right, -1 left"""
    x = nrm(fdir); z = nrm(np.asarray(back, float) - x * (np.asarray(back, float) @ x)); y = np.cross(z, x)
    R = np.stack([x, y * side, z], 1)
    return R, np.asarray(wrist, float)

# ---------------------------------------------------------------------------------------------- clothing
def fold_fn(c, n, amp, z0, z1, phase=0.0, axis=2, taper=True, seed=0, wobble=0.0):
    """vertical folds around an axis through c: displacement amp*cos(n*theta + wobble(z)) between z0 and z1"""
    c = np.asarray(c, F32)
    def f(P):
        q = P - c; th = np.arctan2(q[:, 1], q[:, 0]); z = P[:, 2]
        w = np.clip((z - z0) / max(z1 - z0, 1e-6), 0, 1)
        env = np.sin(np.clip(1 - w, 0, 1) * math.pi * 0.5) ** 0.7 if taper else 1.0
        ph = phase + wobble * np.sin(z * 9.0 + seed)
        return -amp * env * (np.cos(n * th + ph) * 0.7 + 0.3 * np.cos(2 * n * th + 1.3 * ph + 0.5))
    return f

def skirt(f, rows, lab='robe', folds=None, k=0.0, hem=None):
    """a loft from the waist down with folds; rows: (z, cx, cy, rx, ry) bottom->top"""
    lo = Loft(rows)
    if folds:
        c = (np.mean([r[1] for r in rows]), np.mean([r[2] for r in rows]), 0)
        fn = fold_fn(c, *folds) if not callable(folds) else folds
        lo = Displace(lo, fn, folds[1] * 1.0 if not callable(folds) else 0.02)
    f.add(lo, L[lab], k)
    return lo

class Sweep(S.Prim):
    """a flat ribbon / plate swept along a polyline: half width w(t), half thickness t(t), up vectors per point."""
    def __init__(self, pts, w, t, ups):
        self.pts = np.asarray(pts, F32); n = len(pts)
        def fit(v):
            v = np.atleast_1d(np.asarray(v, F32))
            if len(v) == n: return v.copy()
            if len(v) == 1: return np.full(n, v[0], F32)
            return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(v)), v).astype(F32)
        self.w = fit(w); self.t = fit(t)
        self.ups = np.asarray(ups, F32) if np.ndim(ups) == 2 else np.tile(np.asarray(ups, F32), (n, 1))
        m = float(self.w.max() + self.t.max())
        self.lo = self.pts.min(0) - m; self.hi = self.pts.max(0) + m
    def d(self, P):
        best = np.full(len(P), 1e3, F32)
        for i in range(len(self.pts) - 1):
            a = self.pts[i]; b = self.pts[i + 1]; ab = b - a; l2 = float(ab @ ab) + 1e-12
            tt = np.clip(((P - a) @ ab) / l2, 0, 1)
            c = a + tt[:, None] * ab
            up = self.ups[i] * (1 - tt[:, None]) + self.ups[i + 1] * tt[:, None]
            dirv = ab / math.sqrt(l2)
            up = up - dirv * (up @ dirv)[:, None]; up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
            side = np.cross(dirv[None, :], up)
            q = P - c
            qu = (q * up).sum(1); qs = np.abs((q * side).sum(1)); qa = q @ dirv      # qa != 0 only beyond the segment ends
            w = self.w[i] * (1 - tt) + self.w[i + 1] * tt; th = self.t[i] * (1 - tt) + self.t[i + 1] * tt
            a1 = np.maximum(qs - (w - th), 0)
            dd = np.sqrt(a1 * a1 + qu * qu + qa * qa) - th          # distance to a flat strip inflated by th
            best = np.minimum(best, dd)
        return best

def spline(ctrl, n=24):
    """Catmull-Rom through control points"""
    c = np.asarray(ctrl, float)
    if len(c) < 3: return np.linspace(c[0], c[-1], n)
    P = np.vstack([2 * c[0] - c[1], c, 2 * c[-1] - c[-2]])
    out = []
    segs = len(c) - 1
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        m = max(2, n // segs)
        for t in np.linspace(0, 1, m, endpoint=(i == segs - 1)):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)
