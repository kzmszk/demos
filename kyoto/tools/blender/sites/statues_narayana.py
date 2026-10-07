"""那羅延堅固 (Narayana-kengo, Niō a-gyō) — the precise figure, traced from the temple's 2x front photograph
(refs/sanjusangendo/official/nijuhachibushu/2x/img01.jpg, 928x1340; reference only).

Tracing: photo px -> statue metres with X = (445 - px) / 583 (statue's right = viewer's left), Z = (1182 - py) / 583
(z = 0 at the soles); depths (y) are judged from the shading and anatomy.  The body masses come from statues_body with
the joints set from the tracing; the carved relief (pectorals, abdomen, ribs, veins, tendons) is traced in 2D and
projected onto the front of the body field."""
import math
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from . import statues_wood as W
from .statues_sdf import (Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff, Displace, Tube, Loft,
                          Field, frame, rot, euler, nrm, fbm, Offset)
from .statues_body import L, A, Band, Sweep, spline

PHOTO2X = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/nijuhachibushu/2x/img01.jpg'
KPX, CX, SOLE = 583.0, 445.0, 1182.0

def ph(px, py, y=0.0):
    return A((CX - px) / KPX, y, (SOLE - py) / KPX)

def front_y(f, x, z, y0=0.45, y1=-0.3, iters=22):
    """the y of the body's front surface at (x, z): march back from y0 to the first inside point, then bisect"""
    ys = np.linspace(y0, y1, 120)
    P = np.stack([np.full(len(ys), x), ys, np.full(len(ys), z)], 1).astype(np.float32)
    d = f.eval(P)
    ins = np.nonzero(d < 0)[0]
    if len(ins) == 0: return None
    k = ins[0]
    if k == 0: return y0
    a, b = ys[k - 1], ys[k]
    for _ in range(iters):
        m = (a + b) / 2
        if f.eval(np.array([[x, m, z]], np.float32))[0] < 0: b = m
        else: a = m
    return (a + b) / 2

def Field_from(f):
    return f

class Proj:
    """projects traced photo points onto the front surface of a field (cached)"""
    def __init__(self, f): self.f = f; self.cache = {}
    def __call__(self, px, py, dy=0.0):
        key = (round(px, 1), round(py, 1))
        if key not in self.cache:
            p = ph(px, py); y = front_y(self.f, p[0], p[2])
            self.cache[key] = y if y is not None else 0.0
        p = ph(px, py); p[1] = self.cache[key] + dy
        return p

# ---------------------------------------------------------------------------------------------- head
BASE_HEAD = [((0, -0.05, 0.1), (0.355, 0.43, 0.43)), ((0, 0.13, -0.07), (0.315, 0.27, 0.34)), ((0, 0.12, -0.3), (0.3, 0.24, 0.2)), ((0, 0.3, -0.43), (0.15, 0.1, 0.09))]

def head_surf(x, z, base=BASE_HEAD):
    """front y of the base head masses at (x, z) (head units)"""
    best = -1.0
    for (c, r) in base:
        q = 1 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
        if q > 0: best = max(best, c[1] + r[1] * math.sqrt(q))
    return best

def nio_head(f, R, O, u, mouth='open'):
    """the roaring Niō head, sculpted for 那羅延堅固 (head units u = chin..vertex; x right, y forward, z up).
    Every feature is placed by its protrusion over the base masses (head_surf), so it reads as carved relief:
    shaven dome, the fleshy ridge up the forehead between knotted brows dragged down to the nose, deep-set glaring
    crystal eyes, a broad nose with flared nostrils, deep nasolabial folds, bunched cheeks, the mouth open with the upper
    lip drawn up over the teeth, a thin curling moustache, a heavy chin"""
    P = lambda v: O + R @ (A(*v) * u)
    def Q(x, z, prot, ry):          # a feature centre: its front protrudes `prot` over the base surface
        return (x, head_surf(x, z) + prot - ry, z)
    E = lambda c, r, k=None: Ellipsoid(P(c), A(*r) * u, R if k is None else R @ k)
    def Tq(pts, rad, prot):         # tube through (x, z) points, each protruding by prot
        return Tube([P(Q(x, z, p, r)) for (x, z), r, p in zip(pts, rad, prot)], np.asarray(rad, float) * u)
    Lb = L['skin']; Lh = L['hair']
    for (c, r) in BASE_HEAD:
        f.add(E(c, r), Lb, 0.08 * u)
    for s in (1, -1):
        f.add(E(Q(s * 0.215, -0.04, 0.045, 0.07), (0.1, 0.07, 0.07)), Lb, 0.05 * u)          # cheekbones
        f.add(E(Q(s * 0.16, -0.14, 0.06, 0.06), (0.075, 0.06, 0.075)), Lb, 0.04 * u)         # bunched cheeks
        f.add(E(Q(s * 0.25, -0.3, 0.02, 0.07), (0.07, 0.07, 0.09)), Lb, 0.05 * u)            # jaw muscles
        # brows dragged down to the nose, knotted above their inner ends
        f.add(Tq([(s * 0.33, 0.06), (s * 0.25, 0.115), (s * 0.13, 0.1), (s * 0.045, 0.04)], (0.03, 0.05, 0.055, 0.04), (0.04, 0.08, 0.095, 0.075)), Lb, 0.03 * u)
        f.add(E(Q(s * 0.075, 0.15, 0.06, 0.04), (0.06, 0.04, 0.05), rot((0, 1, 0), -s * 0.4)), Lb, 0.03 * u)
        f.add(Tq([(s * 0.05, 0.19), (s * 0.13, 0.25), (s * 0.2, 0.3)], (0.03, 0.026, 0.018), (0.012, 0.006, 0.0)), Lb, 0.035 * u)
        f.sub(Tq([(s * 0.1, 0.17), (s * 0.19, 0.185), (s * 0.27, 0.155)], (0.007, 0.009, 0.007), (0.06, 0.05, 0.03)), 0.008 * u)
        # eyes: socket under the brow, the crystal eyeball, heavy lids leaving an almond slit
        f.sub(E(Q(s * 0.15, 0.0, 0.1, 0.07), (0.1, 0.07, 0.05)), 0.02 * u)
        ey = head_surf(s * 0.15, 0.0)
        ec = P((s * 0.15, ey - 0.055, 0.0))
        f.add(Sphere(ec, 0.072 * u), L['eyew'], 0.004 * u)
        f.paint(Sphere(ec + R @ A(-s * 0.012, 0.07, 0.004) * u, 0.04 * u), L['eye'])
        f.add(Tq([(s * 0.065, 0.006), (s * 0.115, 0.045), (s * 0.19, 0.046), (s * 0.245, 0.016)], (0.016, 0.02, 0.02, 0.014), (0.02, 0.03, 0.03, 0.015)), Lb, 0.008 * u)
        f.add(Tq([(s * 0.065, -0.016), (s * 0.13, -0.052), (s * 0.2, -0.046), (s * 0.245, -0.008)], (0.014, 0.017, 0.017, 0.012), (0.015, 0.025, 0.025, 0.012)), Lb, 0.01 * u)
        f.add(E(Q(s * 0.155, -0.08, 0.03, 0.03), (0.07, 0.03, 0.028)), Lb, 0.02 * u)        # bag under the eye
        # nasolabial grooves and the bulge beside them
        f.sub(Tq([(s * 0.1, -0.13), (s * 0.16, -0.22), (s * 0.18, -0.32)], (0.012, 0.015, 0.012), (0.08, 0.05, 0.03)), 0.012 * u)
        f.add(Tq([(s * 0.14, -0.14), (s * 0.195, -0.22)], (0.035, 0.03), (0.06, 0.04)), Lb, 0.025 * u)
        # ears
        f.add(E((s * 0.345, -0.0, -0.02), (0.035, 0.09, 0.15), rot((0, 0, 1), s * 0.12)), Lb, 0.025 * u)
        f.sub(E((s * 0.375, 0.01, -0.0), (0.02, 0.055, 0.09), rot((0, 0, 1), s * 0.12)), 0.01 * u)
        f.add(E((s * 0.345, 0.02, -0.16), (0.03, 0.045, 0.055)), Lb, 0.02 * u)
    # the vertical ridge up the forehead
    f.add(Tq([(0, 0.07), (0, 0.17), (0, 0.27), (0, 0.36)], (0.038, 0.04, 0.032, 0.02), (0.07, 0.04, 0.025, 0.008)), Lb, 0.035 * u)
    # nose: bridge, a broad tip, flared wings, open nostrils
    f.add(RCone(P(Q(0, 0.04, 0.06, 0.03)), P(Q(0, -0.12, 0.14, 0.042)), 0.03 * u, 0.042 * u), Lb, 0.03 * u)
    f.add(Sphere(P(Q(0, -0.135, 0.145, 0.05)), 0.05 * u), Lb, 0.02 * u)
    for s in (1, -1):
        f.add(E(Q(s * 0.072, -0.16, 0.095, 0.042), (0.05, 0.042, 0.042)), Lb, 0.035 * u)
        f.sub(E(Q(s * 0.045, -0.195, 0.13, 0.028), (0.026, 0.028, 0.014)), 0.006 * u)
    # muzzle, the open mouth with the upper lip drawn up, teeth, tongue
    f.add(E(Q(0, -0.27, 0.05, 0.11), (0.17, 0.11, 0.11)), Lb, 0.05 * u)
    my = head_surf(0, -0.27) + 0.05
    if mouth == 'open':
        zm = -0.278
        f.sub(Box(P((0, my, zm)), A(0.12, 0.12, 0.052) * u, R, 0.04 * u), 0.012 * u, lab=L['mouth'])
        f.sub(E((0, my, zm + 0.04), (0.075, 0.12, 0.03)), 0.01 * u, lab=L['mouth'])
        f.add(Tq([(-0.14, zm - 0.005), (-0.08, zm + 0.05), (0, zm + 0.068), (0.08, zm + 0.05), (0.14, zm - 0.005)], (0.014, 0.019, 0.02, 0.019, 0.014), (0.03, 0.05, 0.055, 0.05, 0.03)), L['lip'], 0.012 * u)
        f.add(Tq([(-0.14, zm - 0.005), (-0.075, zm - 0.06), (0, zm - 0.07), (0.075, zm - 0.06), (0.14, zm - 0.005)], (0.014, 0.024, 0.027, 0.024, 0.014), (0.03, 0.052, 0.058, 0.052, 0.03)), L['lip'], 0.012 * u)
        f.add(Box(P((0, my - 0.025, zm + 0.028)), A(0.1, 0.022, 0.02) * u, R, 0.006 * u), L['teeth'], 0.003 * u)
        f.add(Box(P((0, my - 0.03, zm - 0.035)), A(0.085, 0.022, 0.017) * u, R, 0.006 * u), L['teeth'], 0.003 * u)
        for k in range(-3, 4):
            f.sub(Box(P((k * 0.027, my - 0.01, zm + 0.028)), A(0.0035, 0.03, 0.022) * u, R, 0.0), 0.0)
            f.sub(Box(P((k * 0.025, my - 0.015, zm - 0.035)), A(0.003, 0.03, 0.019) * u, R, 0.0), 0.0)
        f.add(E((0, my - 0.14, zm - 0.02), (0.08, 0.1, 0.03)), L['mouth'], 0.02 * u)
    else:      # un-gyō: lips pressed shut, the corners pulled down
        f.add(Tq([(-0.13, -0.29), (-0.06, -0.27), (0, -0.265), (0.06, -0.27), (0.13, -0.29)], (0.014, 0.022, 0.024, 0.022, 0.014), (0.03, 0.05, 0.055, 0.05, 0.03)), L['lip'], 0.012 * u)
        f.add(Tq([(-0.12, -0.3), (-0.06, -0.31), (0, -0.312), (0.06, -0.31), (0.12, -0.3)], (0.014, 0.022, 0.024, 0.022, 0.014), (0.03, 0.045, 0.05, 0.045, 0.03)), L['lip'], 0.012 * u)
        f.sub(Tq([(-0.135, -0.3), (0, -0.289), (0.135, -0.3)], (0.004, 0.005, 0.004), (0.035, 0.065, 0.035)), 0.004 * u)
    # moustache: thin strands curling out over the mouth corners; a tuft under the lower lip
    for s in (1, -1):
        pts = [(s * 0.02, -0.205, 0.105), (s * 0.07, -0.215, 0.09), (s * 0.12, -0.24, 0.07), (s * 0.15, -0.27, 0.05), (s * 0.165, -0.25, 0.05), (s * 0.155, -0.235, 0.05)]
        f.add(Tube(spline([P(Q(x, z, p, 0.0)) for (x, z, p) in pts], 18), np.linspace(0.013, 0.006, 18) * u), Lh, 0.006 * u)
    f.add(E(Q(0, -0.395, 0.03, 0.02), (0.035, 0.02, 0.025)), Lh, 0.012 * u)

def topknot(f, O, R, u):
    """the fluted knot on the crown and the two flame-like ties rising from it (traced, anchored to the head)"""
    c = O + R @ (A(0, -0.06, 0.5) * u)
    d0 = c - ph(405, 182)
    def flutes(P):
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        return (-0.003 * np.cos(14 * th)).astype(np.float32)
    f.add(Displace(Ellipsoid(c + A(0, 0, 0.022), A(0.042, 0.038, 0.035)), flutes, 0.0035), L['hair'], 0.008)
    f.add(Torus(c + A(0, 0, 0.005), 0.038, 0.006, R), L['crown'], 0.003)
    for pts in ([(398, 168), (380, 150), (372, 126), (362, 108), (352, 96), (350, 82), (342, 76)],
                [(414, 168), (430, 148), (424, 124), (434, 104), (428, 88), (434, 74)]):
        P3 = [ph(px, py, -0.0004 * (170 - py)) + d0 for (px, py) in pts]
        pts_ = spline(P3, 30)
        n = len(pts_)
        f.add(Sweep(pts_, np.linspace(0.009, 0.004, n), 0.0028, [A(0, 1, 0.1)] * n), L['crown'], 0.002)

# ---------------------------------------------------------------------------------------------- feet
def grip_foot(f, ankle, fdir, s, u=1.0, toe_drop=0.03):
    """a bare foot gripping the rock: heel, arch, the ball, five toes clenched down over it; ankle bones, tendons"""
    fd = nrm(np.asarray(fdir, float) * A(1, 1, 0)); up = A(0, 0, 1); side = np.cross(fd, up)      # side = toward the little toe for s=+1? (right foot)
    a = np.asarray(ankle, float)
    sole = 0.0
    heel = A(a[0], a[1], sole + 0.035) - fd * 0.05
    ball = A(a[0], a[1], sole + 0.03) + fd * 0.14
    Lb = L['skin']
    f.add(RCone(a + A(0, 0, 0.03), heel, 0.034, 0.033), Lb, 0.015)
    f.add(Ellipsoid((heel + ball) / 2 + A(0, 0, 0.012), A(0.045, 0.11, 0.035), frame(y=fd, z=up)), Lb, 0.02)
    f.add(Ellipsoid(ball, A(0.052, 0.035, 0.028), frame(y=fd, z=up)), Lb, 0.015)
    for k in (1, -1):    # malleoli
        f.add(Sphere(a + side * k * 0.026 + A(0, 0, 0.005), 0.015), Lb, 0.008)
    # toes: big toe on the inner side (-side for the right foot)
    inner = -side * s
    for i, (o, r, ln) in enumerate(((0.032, 0.013, 0.05), (0.012, 0.0095, 0.04), (-0.006, 0.009, 0.036), (-0.022, 0.0085, 0.032), (-0.036, 0.008, 0.026))):
        b = ball + inner * o + fd * 0.02 - A(0, 0, 0.004)
        k1 = b + fd * ln * 0.55 + A(0, 0, 0.008)
        k2 = k1 + fd * ln * 0.35 - A(0, 0, toe_drop * 0.6)
        tip = k2 + fd * ln * 0.12 - A(0, 0, toe_drop * 0.5)
        f.add(Tube([b, k1, k2, tip], [r * 1.1, r, r * 0.95, r * 0.8]), Lb, 0.004)
        f.add(Sphere(k1, r * 1.05), Lb, 0.003)
    # tendons over the top of the foot
    for o in (0.03, 0.012, -0.006, -0.022):
        f.add(Capsule(a + fd * 0.02 + inner * o * 0.5 + A(0, 0, 0.012), ball + inner * o + A(0, 0, 0.016), 0.0028), Lb, 0.006)

# ---------------------------------------------------------------------------------------------- the build
def narayana():
    from .statues_build import Model
    ROCK_H, PLINTH = 0.16, 0.16
    m = Model('narayana_kengo', '那羅延堅固', 'Narayana-kengo (Nio, a-gyo)', budget=(150000, 30000, 4500), lift=ROCK_H + PLINTH, figure_h=1.67)
    m.pal = W.wood_palette(scarf=(0.072, 0.06, 0.048), crown=(0.075, 0.062, 0.048), robe=(0.06, 0.05, 0.044), robe3=(0.066, 0.055, 0.046),
                          eyew=(0.1, 0.088, 0.075), lip=(0.064, 0.05, 0.044), teeth=(0.12, 0.105, 0.09))
    m.shade = True
    m.weather = W.wood_c0fn(17, 1.0)
    m.back_bias = 0.7
    m.slot = dict(slot='attendants', slot_name='Narayana-kengo', slot_pos='N1')
    m.photo = PHOTO2X
    m.check_views = ['q34', 'q34l', 'trace']
    m.trace = (KPX, CX, SOLE, 928, 1340)
    hh = 0.26
    fig = Bd.Fig(1.67, 6.4, 'nio')
    fig.musc = 0.55; fig.hh = hh; fig.hhd = hh; fig.hs = 1.0
    # ---- joints from the tracing (photo px, depth judged)
    S_R, S_L = ph(343, 432, 0.03), ph(582, 348, -0.06)
    E_R, E_L = ph(300, 585, 0.02), ph(675, 245, -0.15)
    W_R = ph(275, 727, 0.06)
    fist = ph(550, 265, 0.1)
    fdir_L = nrm(fist - E_L); W_L = fist - fdir_L * 0.06
    H_R, H_L = ph(440, 668, 0.015), ph(558, 660, -0.02)
    K_R, K_L = ph(385, 892, 0.07), ph(555, 862, 0.1)
    A_R, A_L = ph(346, 1110, 0.1), ph(566, 1100, -0.02)
    xS = nrm(S_R - S_L)
    zc = nrm(ph(468, 390) - ph(500, 665))
    fig.Rc = frame(x=xS, z=zc)
    fig.Oc = (S_R + S_L) / 2 - fig.Rc @ A(0, -0.1 * hh, 0.5 * hh)
    fig.N = fig.Oc + fig.Rc @ A(0, -0.08 * hh, 0.72 * hh)
    fig.Op = ph(500, 662, 0.0)
    fig.Rp = frame(x=nrm(H_R - H_L), z=(0, 0, 1))
    fig.W = ph(495, 560, 0.0)
    fig.Rw = frame(x=nrm(fig.Rp[:, 0] + fig.Rc[:, 0]), z=nrm(fig.Rc[:, 2] + A(0, 0, 1)))
    fig.Oh = ph(437, 287, 0.04)
    fig.Rh = rot((0, 0, 1), -0.32) @ rot((0, 1, 0), -0.06) @ rot((1, 0, 0), -0.1)
    fig.arm = {'r': dict(S=S_R, E=E_R, W=W_R, s=1), 'l': dict(S=S_L, E=E_L, W=W_L, s=-1)}
    fig.leg = {'r': dict(H=H_R, K=K_R, A=A_R, s=1, foot_dir=A(0.55, 0.85, 0)), 'l': dict(H=H_L, K=K_L, A=A_L, s=-1, foot_dir=A(-0.15, 1, 0))}
    O, R = fig.Oh, fig.Rh
    # ---- body masses
    f = Field('body')
    arms, legs = fig.arm, fig.leg
    fig.arm = {}; fig.leg = {}
    Bd.add_body(f, fig, skin='skin')
    fig.arm, fig.leg = arms, legs
    Lb = L['skin']
    # chest / back masses to the traced silhouette (the body leans and twists to its right)
    f.add(Ellipsoid(ph(470, 455, -0.04), A(0.19, 0.13, 0.17), fig.Rc), Lb, 0.06)
    f.add(Ellipsoid(ph(492, 545, -0.03), A(0.15, 0.115, 0.12), fig.Rw), Lb, 0.06)
    # arms: muscular, with the traced radii
    for nm, a in arms.items():
        Bd.add_arm(f, fig, a, Lb, r_up=0.05, r_fore=0.043)
    # deltoids, biceps, triceps, forearm masses
    f.add(Ellipsoid(ph(325, 450, 0.02), A(0.06, 0.065, 0.085), frame(z=nrm(E_R - S_R), x=(1, 0, 0))), Lb, 0.03)
    f.add(Ellipsoid(S_R + (E_R - S_R) * 0.55 + A(0, 0.03, 0), A(0.045, 0.04, 0.09), frame(z=nrm(E_R - S_R), x=(1, 0, 0))), Lb, 0.025)
    f.add(Ellipsoid(S_R + (E_R - S_R) * 0.5 + A(0.01, -0.035, 0), A(0.042, 0.04, 0.1), frame(z=nrm(E_R - S_R), x=(1, 0, 0))), Lb, 0.025)
    f.add(Ellipsoid(E_R + (W_R - E_R) * 0.25 + A(0.012, 0.012, 0), A(0.04, 0.035, 0.09), frame(z=nrm(W_R - E_R), x=(1, 0, 0))), Lb, 0.02)
    f.add(Ellipsoid(ph(600, 322, -0.05), A(0.07, 0.07, 0.07), fig.Rc), Lb, 0.03)
    ua = nrm(E_L - S_L)
    f.add(Ellipsoid(S_L + (E_L - S_L) * 0.5 + A(0, 0.0, 0.035), A(0.05, 0.05, 0.11), frame(z=ua, x=(0, 1, 0))), Lb, 0.025)
    f.add(Ellipsoid(S_L + (E_L - S_L) * 0.5 + A(0, 0.0, -0.03), A(0.045, 0.045, 0.11), frame(z=ua, x=(0, 1, 0))), Lb, 0.025)
    fa = nrm(W_L - E_L)
    f.add(Ellipsoid(E_L + (W_L - E_L) * 0.3 + A(0, 0, 0.015), A(0.045, 0.04, 0.09), frame(z=fa, x=(0, 0, 1))), Lb, 0.02)
    # legs
    for nm, g in legs.items():
        Hj, K, Ak = g['H'], g['K'], g['A']; s = g['s']
        ax1 = nrm(K - Hj); ax2 = nrm(Ak - K); fd = nrm(g['foot_dir'] * A(1, 1, 0))
        f.add(RCone(Hj, K, 0.085, 0.055), Lb, 0.05)
        f.add(RCone(K, Ak, 0.052, 0.03), Lb, 0.03)
        f.add(Ellipsoid(K + (Ak - K) * 0.3 - fd * 0.022 + np.cross(ax2, (0, 0, 1)) * 0.0, A(0.05, 0.05, 0.12), frame(z=ax2, y=fd)), Lb, 0.02)     # calf
        f.add(Ellipsoid(K + (Ak - K) * 0.32 - fd * 0.018 - np.cross(fd, (0, 0, 1)) * s * 0.018, A(0.04, 0.04, 0.1), frame(z=ax2, y=fd)), Lb, 0.015)
        f.add(Capsule(K + ax2 * 0.04 + fd * 0.035, Ak + fd * 0.02 + A(0, 0, 0.03), 0.012), Lb, 0.015)      # shin ridge
        f.add(Sphere(K + fd * 0.025, 0.033), Lb, 0.02)                                                      # knee cap
        f.add(Capsule(Ak + A(0, 0, 0.03) - fd * 0.035, K + ax2 * 0.15 - fd * 0.035, 0.012), Lb, 0.012)      # Achilles
        grip_foot(f, Ak, g['foot_dir'], s)
    f.add(Ellipsoid((H_R + K_R) / 2 + A(0, 0.02, 0), A(0.09, 0.08, 0.16), frame(z=nrm(K_R - H_R), x=(1, 0, 0))), Lb, 0.04)    # thighs under the skirt
    f.add(Ellipsoid((H_L + K_L) / 2 + A(0, 0.02, 0), A(0.09, 0.08, 0.16), frame(z=nrm(K_L - H_L), x=(1, 0, 0))), Lb, 0.04)
    # neck: thick, the sternocleidomastoids, the trapezius slopes
    f.add(RCone(fig.N - fig.Rc @ A(0, 0, 0.04), O + R @ A(0, -0.08, -0.3) * hh, 0.085, 0.07), Lb, 0.04)
    f.add(Capsule(O + R @ A(0.25, 0.0, -0.32) * hh, ph(460, 392, 0.08), 0.022), Lb, 0.02)
    f.add(Capsule(O + R @ A(-0.25, -0.02, -0.32) * hh, ph(478, 392, 0.08), 0.022), Lb, 0.02)
    f.add(Capsule(ph(420, 380, -0.04), ph(350, 410, -0.02), 0.04), Lb, 0.04)
    f.add(Capsule(ph(505, 360, -0.06), ph(580, 335, -0.06), 0.045), Lb, 0.04)
    m_body = f
    # ---- relief traced from the photo, projected onto the front of the body
    pj = Proj(f)
    rel = []
    def bump(px, py, r, prot, k=0.01): rel.append(('a', Ellipsoid(pj(px, py, prot - r[1]), A(*r)), k))
    def groove(pts, r, depth, k=0.01): rel.append(('s', Tube([pj(px, py, r - depth) for (px, py) in pts], np.full(len(pts), r)), k))
    # pectorals: heavy plates with a hard lower edge, the deep sternal groove
    bump(402, 450, (0.075, 0.04, 0.055), 0.016, 0.02); bump(422, 474, (0.05, 0.03, 0.03), 0.012, 0.012)
    bump(535, 428, (0.07, 0.04, 0.05), 0.014, 0.02); bump(556, 447, (0.04, 0.025, 0.03), 0.01, 0.01)
    groove([(362, 482), (395, 495), (440, 495), (468, 488)], 0.008, 0.008)
    groove([(488, 477), (520, 475), (555, 463), (588, 441)], 0.008, 0.008)
    groove([(470, 400), (474, 430), (478, 460), (480, 490)], 0.007, 0.008)
    bump(411, 476, (0.007, 0.006, 0.007), 0.004, 0.003); bump(561, 419, (0.007, 0.006, 0.007), 0.004, 0.003)
    groove([(455, 398), (410, 403), (362, 413)], 0.005, 0.004, 0.008); groove([(482, 392), (530, 376), (578, 354)], 0.005, 0.004, 0.008)
    # the abdomen: three rows of blocks, the linea alba, the lower belly
    for (py, cxp) in ((507, 478), (527, 484), (546, 490)):
        for s_ in (-1, 1):
            bump(cxp + s_ * 22, py, (0.027, 0.02, 0.015), 0.007, 0.008)
        groove([(cxp - 45, py + 10), (cxp, py + 12), (cxp + 45, py + 10)], 0.005, 0.005, 0.006)
    groove([(478, 496), (484, 520), (490, 545), (500, 568)], 0.006, 0.006, 0.008)
    bump(514, 584, (0.08, 0.04, 0.045), 0.012, 0.025)
    groove([(506, 602), (507, 604)], 0.006, 0.006, 0.002)
    # ribcage edge, serratus fingers, obliques, the iliac V
    groove([(470, 500), (440, 512), (410, 530), (385, 550)], 0.006, 0.005)
    groove([(490, 494), (525, 505), (555, 525), (575, 545)], 0.006, 0.005)
    for (px, py) in ((588, 470), (594, 494), (598, 518), (372, 505), (376, 527)):
        bump(px, py, (0.022, 0.015, 0.014), 0.005, 0.006)
    bump(412, 585, (0.04, 0.03, 0.05), 0.01, 0.02); bump(590, 575, (0.04, 0.03, 0.05), 0.01, 0.02)
    groove([(420, 600), (445, 625), (470, 645)], 0.007, 0.006); groove([(595, 598), (570, 622), (545, 642)], 0.007, 0.006)
    # veins on the hanging arm
    for pts in ([(290, 625), (282, 660), (276, 700), (278, 725)], [(270, 650), (266, 690), (268, 720)], [(318, 520), (312, 555), (305, 580)]):
        rel.append(('a', Tube([pj(px, py, -0.002) for (px, py) in pts], np.full(len(pts), 0.0045)), 0.004))
    for kd, p, k in rel:
        if kd == 'a': f.add(p, Lb, k)
        else: f.sub(p, k)
    m.field(f, 0.0017, 44.0, lods=(0, 1))
    # ---- head (finest)
    g = Field('head')
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.04), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.085, 0.075), Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), Lb, 0.0)
    nio_head(g, R, O, hh)
    topknot(g, O, R, hh)
    m.field(g, 0.0007, 36.0, lods=(0, 1))
    # ---- drapery: sash, skirt, the windblown flaps
    from .statues_kannon import Over
    d = Field('drape')
    lr = L['robe']
    zb = (SOLE - 632) / KPX
    d.add(Band(ph(508, 632, -0.02), 0.178, 0.135, 0.022, 0.028, fig.Rp), L['robe3'], 0.015)        # rolled waist
    d.add(Ellipsoid(ph(478, 648, 0.13), A(0.055, 0.035, 0.035)), L['robe3'], 0.02)                  # the knot
    for s_, x0 in ((1, 466), (-1, 498)):
        d.add(Sweep(spline([ph(x0, 650, 0.135), ph(x0 - s_ * 10, 690, 0.14), ph(x0 - s_ * 5, 720, 0.13)], 10), np.full(10, 0.03), 0.008, [A(0, 1, 0)] * 10), L['robe3'], 0.01)
    def radial_folds(c, n, amp, z_top, front=0.6):
        c = np.asarray(c, np.float32)
        def fn(P):
            th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
            w = np.clip((z_top - P[:, 2]) / 0.25, 0.15, 1.0)
            fw = (1 - front) + front * np.clip(np.sin(th) * 0.5 + 0.6, 0, 1)
            return (-amp * w * fw * (0.65 * np.cos(n * th + 6.0 * P[:, 2]) + 0.35 * np.cos(2.3 * n * th + 1.0))).astype(np.float32)
        return fn
    # the wrapped skirt: round the hips, widening over the spread legs; short in front, the back billowing low between the legs
    rows = [(0.22, -0.04, -0.06, 0.29, 0.21), (0.42, -0.04, -0.0, 0.3, 0.215), (0.62, -0.06, 0.025, 0.26, 0.19), (0.8, -0.085, 0.01, 0.2, 0.155), (zb + 0.01, -0.1, -0.01, 0.175, 0.135)]
    def hem(th):
        fr = np.clip(np.sin(th), 0, 1); bk = np.clip(-np.sin(th), 0, 1)
        return (0.46 + 0.02 * np.cos(th) - 0.22 * bk ** 1.5 + 0.03 * fr * np.cos(7 * th + 0.5) + 0.012 * np.cos(11 * th)).astype(np.float32)
    d.add(Over(rows, hem, radial_folds((-0.06, 0.0), 9, 0.018, zb, 0.92)), lr, 0.02)
    # folds blown diagonally from the knot down toward the statue's right
    for (x0, y0, x1, y1, r) in ((470, 680, 395, 860, 0.012), (490, 690, 425, 890, 0.011), (455, 700, 360, 830, 0.01), (515, 700, 470, 900, 0.01), (540, 690, 560, 900, 0.009), (575, 680, 610, 880, 0.009)):
        a0 = ph(x0, y0); a1 = ph(x1, y1)
        y_a = front_y(Field_from(d), a0[0], a0[2]) or 0.15; y_b = front_y(Field_from(d), a1[0], a1[2]) or 0.15
        d.add(Tube([A(a0[0], y_a - r * 0.4, a0[2]), (A(a0[0], y_a, a0[2]) + A(a1[0], y_b, a1[2])) / 2 + A(0, 0.004, 0), A(a1[0], y_b - r * 0.4, a1[2])], [r * 0.6, r, r * 0.8]), lr, 0.02)
    # the overfold hanging over the sash
    rows_o = [(0.79, -0.09, 0.012, 0.215, 0.165), (0.88, -0.095, 0.0, 0.195, 0.15), (zb + 0.012, -0.1, -0.01, 0.188, 0.143)]
    def hem_o(th): return (0.83 + 0.025 * np.cos(4 * th + 0.5) - 0.03 * np.clip(np.sin(th + 0.3), 0, 1)).astype(np.float32)
    d.add(Over(rows_o, hem_o, radial_folds((-0.09, 0.0), 8, 0.007, zb, 0.3)), L['robe3'], 0.012)
    # the windblown flap to the statue's right (viewer's left): a sheet from the right thigh sweeping out low to its tip
    fl = spline([ph(392, 800, 0.1), ph(355, 880, 0.1), ph(310, 950, 0.08), ph(250, 1005, 0.06), ph(195, 1045, 0.06), ph(154, 1068, 0.09)], 48)
    ws = np.interp(np.linspace(0, 1, 48), [0, 0.3, 0.6, 0.85, 1.0], [0.08, 0.1, 0.075, 0.045, 0.015])
    ups = [nrm(A(0.35 * math.sin(k * 0.22), 1.0, 0.25 + 0.6 * k / 47)) for k in range(48)]
    def plate_folds(n, amp, axis=(0, 1, 0)):
        ax = np.asarray(axis, np.float32)
        def fn(P): return (amp * np.sin((P[:, 0] * 0.8 + P[:, 2] * 0.6) * 2 * math.pi * n)[:, None] * ax[None, :]).astype(np.float32)
        return fn
    d.add(S.Warp(Sweep(fl, ws, 0.0045, ups), plate_folds(9, 0.018), 0.018), lr, 0.012)
    fl2 = spline([ph(360, 880, 0.02), ph(290, 975, 0.0), ph(220, 1035, -0.01), ph(170, 1068, 0.02)], 30)
    d.add(S.Warp(Sweep(fl2, np.linspace(0.06, 0.02, 30), 0.004, [nrm(A(0, 1, 0.5))] * 30), plate_folds(12, 0.01), 0.01), lr, 0.01)
    # the statue's left side: the skirt's outer edge hanging in folds
    sl = spline([ph(610, 660, 0.03), ph(625, 760, 0.01), ph(632, 860, 0.0), ph(635, 930, 0.01)], 24)
    d.add(S.Warp(Sweep(sl, np.linspace(0.05, 0.075, 24), 0.005, [nrm(A(-0.8, 0.6, 0))] * 24), plate_folds(12, 0.01, (-0.8, 0.6, 0)), 0.01), lr, 0.015)
    m.field(d, 0.0016, 30.0, lods=(0, 1))
    # ---- rock and LOD2
    bf = Field('rock')
    rng = np.random.default_rng(101)
    W.rock(bf, rng, 0.85, 0.56, ROCK_H, pads=[(A_R[0] + 0.05, A_R[1] + 0.06, 0.0, 0.09), (A_L[0], A_L[1] + 0.05, 0.0, 0.09)], z_top=0.0, c=(0.037, 0.0))
    bf.add(Ellipsoid(A(0.42, 0.02, -0.06), A(0.08, 0.12, 0.05)), L['rock'], 0.04)
    m.field(bf, 0.004, 6.0, lods=(0, 1))
    f2 = Field('lod2')
    f2.add(Ellipsoid(ph(475, 470, -0.03), A(0.2, 0.15, 0.24), fig.Rc), Lb, 0.05)
    f2.add(Ellipsoid(O, A(0.13, 0.14, 0.15)), Lb, 0.05)
    for nm, a in arms.items():
        f2.add(Tube([a['S'], a['E'], a['W']], [0.06, 0.05, 0.04]), Lb, 0.03)
    for nm, g_ in legs.items():
        f2.add(Tube([g_['H'], g_['K'], g_['A'], g_['A'] + nrm(g_['foot_dir'] * A(1, 1, 0)) * 0.15 - A(0, 0, 0.09)], [0.1, 0.07, 0.04, 0.03]), Lb, 0.03)
    f2.add(Loft([(0.45, -0.05, 0.02, 0.24, 0.17), (0.93, -0.1, 0.0, 0.18, 0.14)]), lr, 0.03)
    f2.add(Box(A(0.037, 0, -ROCK_H / 2), A(0.42, 0.28, ROCK_H / 2), None, 0.03), L['rock'], 0.02)
    m.field(f2, 0.009, 30.0, lods=(2,))
    # ---- hands
    fdir_R = nrm(ph(329, 791, 0.12) - W_R)
    xf_R = Bd.hand_xf(W_R, fdir_R, A(0.25, 0.9, 0.3), 1)
    gax = A(0, 0, -1)
    x_ = nrm(fdir_L - gax * (fdir_L @ gax))
    xf_L = Bd.hand_xf(W_L, x_, np.cross(x_, gax * -1), -1)
    Bd.HAND_POSES['hang'] = ((0.22, 0.32, 0.22), (0.26, 0.36, 0.24), (0.32, 0.42, 0.28), (0.38, 0.48, 0.3), (0.55, 0.2, 0.2, 0.5), 0.07)
    Lh = 0.2
    m.instance('hand_hang', lambda: (Bd.hand_field('hang', Lh, musc=0.6, lab='skin'), 0.0011), 6.0, [xf_R])
    m.instance('hand_fist', lambda: (Bd.hand_field('fist', Lh, musc=0.8, lab='skin'), 0.0011), 6.0, [xf_L])
    # ---- explicit: plinth, the scarf (天衣)
    def xm_fn(q):
        xm = X.XM()
        X.octa_plinth(xm, (0.006, 0, -ROCK_H - PLINTH), 0.97 / 2 / math.cos(math.pi / 4), [(1.0, 0.0, PLINTH), (1.03, 0.0, 0.02)], 'base', sides=4, phase=math.pi / 4)
        n = 90 if q > 0.6 else (36 if q > 0.3 else 14)
        if q > 0.15:
            arc = [(610, 450, 0.06), (615, 350, 0.03), (612, 250, -0.02), (600, 178, -0.06), (560, 154, -0.09), (490, 153, -0.1), (430, 172, -0.09),
                   (395, 200, -0.06), (365, 250, -0.02), (338, 310, 0.03), (325, 380, 0.07), (332, 430, 0.1), (355, 480, 0.13), (375, 540, 0.14), (392, 600, 0.15), (405, 635, 0.15)]
            pts0 = spline([ph(px, py, y) for (px, py, y) in arc], n)
            ups = [nrm(A(0.7 * max(0, k / (len(pts0) - 1) - 0.55) * 2.0, 1.0, 0.25 * (1 - k / (len(pts0) - 1)))) for k in range(len(pts0))]
            tg = np.gradient(pts0, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
            side = np.cross(tg, np.array(ups)); side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-9)
            for off, wd, dy in ((-0.027, 0.022, -0.004), (0.0, 0.022, 0.003), (0.027, 0.022, -0.004)):
                X.ribbon(xm, pts0 + side * off + np.array(ups) * dy, wd, 0.0025, ups, 'scarf')
            down = [(608, 440, 0.06), (612, 520, 0.07), (610, 600, 0.09), (606, 650, 0.1), (620, 720, 0.07), (630, 800, 0.04), (640, 880, 0.02),
                    (650, 950, 0.02), (670, 1000, 0.04), (700, 1030, 0.06), (717, 1042, 0.09)]
            pts0 = spline([ph(px, py, y) for (px, py, y) in down], n)
            ups = [nrm(A(-0.5, 1.0, 0.1 * math.sin(k * 0.2))) for k in range(len(pts0))]
            tg = np.gradient(pts0, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
            side = np.cross(tg, np.array(ups)); side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-9)
            for off, wd, dy in ((-0.014, 0.02, 0.0), (0.014, 0.02, 0.004)):
                X.ribbon(xm, pts0 + side * off + np.array(ups) * dy, wd, 0.0025, ups, 'scarf')
        return xm
    m.xm_fn = xm_fn
    m.face_z = O[2]
    m.closeups = [('face', m.lift + O[2] + 0.02, 0.75, 0.3)]
    return m
