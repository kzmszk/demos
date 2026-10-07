"""密迹金剛士 (Misshaku-kongoshi, Niō un-gyō) — the pair of 那羅延堅固, traced from the 2x front photograph
(refs/sanjusangendo/official/nijuhachibushu/2x/img28.jpg; reference only), built with the same kit as statues_narayana.

The mouth is shut (un-gyō); the right hand is raised, palm forward, beside the shoulder; the left fist presses on the
hip; the head turns to its left; the scarf loops over the head, crosses the belly and flutters at both sides."""
import math
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from . import statues_wood as W
from .statues_sdf import (Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff, Displace, Tube, Loft,
                          Field, frame, rot, euler, nrm, fbm, Offset)
from .statues_body import L, A, Band, Sweep, spline
from .statues_narayana import nio_head, grip_foot, Proj, front_y

PHOTO2X = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/nijuhachibushu/2x/img28.jpg'
KPX, CX, SOLE = 592.0, 445.0, 1170.0

def ph(px, py, y=0.0):
    return A((CX - px) / KPX, y, (SOLE - py) / KPX)

def topknot2(f, O, R, u):
    c = O + R @ (A(0, -0.06, 0.5) * u)
    d0 = c - ph(445, 168)
    def flutes(P):
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        return (-0.003 * np.cos(14 * th)).astype(np.float32)
    f.add(Displace(Ellipsoid(c + A(0, 0, 0.022), A(0.04, 0.036, 0.034)), flutes, 0.0035), L['hair'], 0.008)
    f.add(Torus(c + A(0, 0, 0.005), 0.036, 0.006, R), L['crown'], 0.003)
    for pts in ([(438, 160), (430, 140), (440, 118), (430, 98), (438, 80), (432, 66)],
                [(456, 160), (468, 140), (460, 118), (470, 98), (464, 80), (470, 66)]):
        P3 = [ph(px, py, -0.0004 * (165 - py)) + d0 for (px, py) in pts]
        pts_ = spline(P3, 30); n = len(pts_)
        f.add(Sweep(pts_, np.linspace(0.009, 0.004, n), 0.0028, [A(0, 1, 0.1)] * n), L['crown'], 0.002)

def misshaku():
    from .statues_build import Model
    ROCK_H, PLINTH = 0.16, 0.16
    m = Model('misshaku_kongoshi', '密迹金剛士', 'Misshaku-kongoshi (Nio, un-gyo)', budget=(80000, 16000, 2400), lift=ROCK_H + PLINTH, figure_h=1.68)
    m.pal = W.wood_palette(scarf=(0.072, 0.06, 0.048), crown=(0.075, 0.062, 0.048), robe=(0.06, 0.05, 0.044), robe3=(0.066, 0.055, 0.046),
                          eyew=(0.1, 0.088, 0.075), lip=(0.064, 0.05, 0.044), teeth=(0.12, 0.105, 0.09), gold='gold')
    m.shade = True
    m.weather = W.wood_c0fn(28, 1.0)
    m.back_bias = 0.7
    m.slot = dict(slot='attendants', slot_name='Misshaku-kongoshi', slot_pos='S12')
    m.photo = PHOTO2X
    m.check_views = ['q34', 'trace']
    m.trace = (KPX, CX, SOLE, 928, 1340)
    hh = 0.26
    fig = Bd.Fig(1.68, 6.4, 'nio')
    fig.musc = 0.55; fig.hh = hh; fig.hhd = hh; fig.hs = 1.0
    S_R, S_L = ph(328, 400, 0.0), ph(575, 395, -0.04)
    E_R, E_L = ph(268, 565, 0.05), ph(625, 545, -0.05)
    W_R = ph(245, 498, 0.14)
    W_L = ph(568, 650, 0.03)
    H_R, H_L = ph(385, 700, 0.0), ph(500, 700, 0.0)
    K_R, K_L = ph(300, 925, 0.07), ph(440, 935, 0.08)
    A_R, A_L = ph(278, 1118, 0.04), ph(432, 1120, 0.04)
    fig.Rc = frame(x=nrm(S_R - S_L), z=nrm(ph(450, 400) - ph(440, 650) + A(0, 0.03, 0)))
    fig.Oc = (S_R + S_L) / 2 - fig.Rc @ A(0, -0.1 * hh, 0.5 * hh)
    fig.N = fig.Oc + fig.Rc @ A(0, -0.08 * hh, 0.72 * hh)
    fig.Op = ph(442, 690, 0.0)
    fig.Rp = frame(x=nrm(H_R - H_L), z=(0, 0, 1))
    fig.W = ph(440, 570, 0.0)
    fig.Rw = frame(x=nrm(fig.Rp[:, 0] + fig.Rc[:, 0]), z=nrm(fig.Rc[:, 2] + A(0, 0, 1)))
    fig.Oh = ph(458, 262, 0.04)
    fig.Rh = rot((0, 0, 1), 0.4) @ rot((0, 1, 0), 0.08) @ rot((1, 0, 0), -0.04)
    fig.arm = {'r': dict(S=S_R, E=E_R, W=W_R, s=1), 'l': dict(S=S_L, E=E_L, W=W_L, s=-1)}
    fig.leg = {'r': dict(H=H_R, K=K_R, A=A_R, s=1, foot_dir=A(0.4, 1, 0)), 'l': dict(H=H_L, K=K_L, A=A_L, s=-1, foot_dir=A(-0.25, 1, 0))}
    O, R = fig.Oh, fig.Rh
    f = Field('body')
    arms, legs = fig.arm, fig.leg
    fig.arm = {}; fig.leg = {}
    Bd.add_body(f, fig, skin='skin')
    fig.arm, fig.leg = arms, legs
    Lb = L['skin']
    f.add(Ellipsoid(ph(450, 450, -0.04), A(0.19, 0.13, 0.17), fig.Rc), Lb, 0.06)
    f.add(Ellipsoid(ph(445, 560, -0.03), A(0.15, 0.115, 0.13), fig.Rw), Lb, 0.06)
    for nm, a in arms.items():
        Bd.add_arm(f, fig, a, Lb, r_up=0.05, r_fore=0.043)
    for (S_, E_) in ((S_R, E_R), (S_L, E_L)):
        ua = nrm(E_ - S_)
        f.add(Ellipsoid(S_ + ua * 0.05, A(0.065, 0.065, 0.085), frame(z=ua, x=(1, 0, 0) if abs(ua[0]) < 0.9 else (0, 1, 0))), Lb, 0.03)
        f.add(Ellipsoid(S_ + (E_ - S_) * 0.55 + A(0, 0.03, 0), A(0.045, 0.042, 0.09), frame(z=ua, x=(1, 0, 0) if abs(ua[0]) < 0.9 else (0, 1, 0))), Lb, 0.025)
    for (E_, W_) in ((E_R, W_R), (E_L, W_L)):
        fa = nrm(W_ - E_)
        f.add(Ellipsoid(E_ + (W_ - E_) * 0.28, A(0.042, 0.037, 0.085), frame(z=fa, x=(1, 0, 0) if abs(fa[0]) < 0.9 else (0, 1, 0))), Lb, 0.02)
    for nm, g in legs.items():
        Hj, K, Ak = g['H'], g['K'], g['A']; s = g['s']
        ax2 = nrm(Ak - K); fd = nrm(g['foot_dir'] * A(1, 1, 0))
        f.add(RCone(Hj, K, 0.085, 0.055), Lb, 0.05)
        f.add(RCone(K, Ak, 0.052, 0.03), Lb, 0.03)
        f.add(Ellipsoid(K + (Ak - K) * 0.3 - fd * 0.022, A(0.05, 0.05, 0.12), frame(z=ax2, y=fd)), Lb, 0.02)
        f.add(Capsule(K + ax2 * 0.04 + fd * 0.035, Ak + fd * 0.02 + A(0, 0, 0.03), 0.012), Lb, 0.015)
        f.add(Sphere(K + fd * 0.025, 0.033), Lb, 0.02)
        f.add(Capsule(Ak + A(0, 0, 0.03) - fd * 0.035, K + ax2 * 0.15 - fd * 0.035, 0.012), Lb, 0.012)
        grip_foot(f, Ak, g['foot_dir'], s)
        f.add(Ellipsoid((Hj + K) / 2 + A(0, 0.02, 0), A(0.09, 0.08, 0.16), frame(z=nrm(K - Hj), x=(1, 0, 0))), Lb, 0.04)
    f.add(RCone(fig.N - fig.Rc @ A(0, 0, 0.04), O + R @ A(0, -0.08, -0.3) * hh, 0.088, 0.072), Lb, 0.04)
    f.add(Capsule(ph(420, 380, -0.04), ph(335, 395, -0.02), 0.042), Lb, 0.04)
    f.add(Capsule(ph(480, 375, -0.05), ph(570, 390, -0.05), 0.045), Lb, 0.04)
    # carved relief traced from the photo (pectorals, abdomen, ribs, veins), projected onto the body
    pj = Proj(f)
    def bump(px, py, r, prot, k=0.01): f.add(Ellipsoid(pj(px, py, prot - r[1]), A(*r)), Lb, k)
    def groove(pts, r, depth, k=0.01): f.sub(Tube([pj(px, py, r - depth) for (px, py) in pts], np.full(len(pts), r)), k)
    bump(375, 440, (0.075, 0.04, 0.055), 0.016, 0.02); bump(505, 440, (0.072, 0.04, 0.055), 0.016, 0.02)
    groove([(325, 475), (365, 490), (410, 488), (438, 470)], 0.008, 0.008)
    groove([(455, 470), (490, 488), (530, 488), (565, 470)], 0.008, 0.008)
    groove([(442, 395), (444, 430), (446, 465), (448, 495)], 0.007, 0.008)
    bump(360, 470, (0.007, 0.006, 0.007), 0.004, 0.003); bump(522, 466, (0.007, 0.006, 0.007), 0.004, 0.003)
    for (py, cxp) in ((510, 445), (535, 446), (558, 448)):
        for s_ in (-1, 1): bump(cxp + s_ * 24, py, (0.028, 0.02, 0.016), 0.007, 0.008)
        groove([(cxp - 48, py + 11), (cxp, py + 13), (cxp + 48, py + 11)], 0.005, 0.005, 0.006)
    groove([(446, 495), (447, 525), (448, 555), (450, 580)], 0.006, 0.006, 0.008)
    bump(450, 590, (0.08, 0.04, 0.04), 0.01, 0.025)
    groove([(440, 500), (405, 512), (375, 532), (350, 552)], 0.006, 0.005)
    groove([(455, 500), (490, 512), (520, 532), (545, 552)], 0.006, 0.005)
    for (px, py) in ((340, 480), (344, 505), (548, 480), (552, 505)): bump(px, py, (0.022, 0.015, 0.014), 0.005, 0.006)
    for pts in ([(408, 370), (395, 385), (380, 400)], [(480, 370), (495, 385), (512, 395)], [(258, 530), (262, 560)], [(600, 560), (590, 600), (575, 630)]):
        f.add(Tube([pj(px, py, -0.002) for (px, py) in pts], np.full(len(pts), 0.004)), Lb, 0.004)     # veins
    m.field(f, 0.002, 30.0, lods=(0, 1))
    g = Field('head')
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.04), O + R @ A(0, -0.06 * hh, -0.25 * hh), 0.088, 0.075), Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), Lb, 0.0)
    nio_head(g, R, O, hh, mouth='closed')
    topknot2(g, O, R, hh)
    m.field(g, 0.0008, 26.0, lods=(0, 1))
    # drapery: rolled waist and knot, the skirt to the knees on the right and lower on the left, long fluttering flaps
    from .statues_kannon import Over
    d = Field('drape'); lr = L['robe']
    zb = (SOLE - 630) / KPX
    d.add(Band(ph(445, 630, -0.02), 0.18, 0.135, 0.022, 0.028, fig.Rp), L['robe3'], 0.015)
    d.add(Ellipsoid(ph(455, 650, 0.13), A(0.05, 0.035, 0.035)), L['robe3'], 0.02)
    def radial_folds(c, n, amp, z_top):
        c = np.asarray(c, np.float32)
        def fn(P):
            th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
            w = np.clip((z_top - P[:, 2]) / 0.25, 0.15, 1.0)
            return (-amp * w * (0.65 * np.cos(n * th + 6.0 * P[:, 2]) + 0.35 * np.cos(2.3 * n * th + 1.0))).astype(np.float32)
        return fn
    cxm = (CX - 440) / KPX
    rows = [(0.22, cxm + 0.04, -0.04, 0.27, 0.2), (0.42, cxm + 0.03, 0.0, 0.28, 0.205), (0.62, cxm + 0.0, 0.025, 0.25, 0.18), (0.8, cxm, 0.01, 0.2, 0.155), (zb + 0.01, cxm, -0.01, 0.178, 0.135)]
    def hem(th):
        bk = np.clip(-np.sin(th), 0, 1)
        return (0.42 + 0.05 * np.cos(th) - 0.2 * bk ** 1.5 + 0.03 * np.clip(np.sin(th), 0, 1) * np.cos(7 * th)).astype(np.float32)
    d.add(Over(rows, hem, radial_folds((cxm, 0.0), 9, 0.018, zb)), lr, 0.02)
    rows_o = [(0.78, cxm, 0.012, 0.215, 0.165), (0.88, cxm, 0.0, 0.195, 0.15), (zb + 0.012, cxm, -0.01, 0.19, 0.143)]
    def hem_o(th): return (0.82 + 0.025 * np.cos(4 * th + 0.5)).astype(np.float32)
    d.add(Over(rows_o, hem_o, radial_folds((cxm, 0.0), 8, 0.007, zb)), L['robe3'], 0.012)
    def plate_folds(n, amp):
        def fn(P): return (amp * np.sin((P[:, 0] * 0.8 + P[:, 2] * 0.6) * 2 * math.pi * n)[:, None] * np.array([0, 1, 0], np.float32)[None, :]).astype(np.float32)
        return fn
    # long flap at the statue's right (viewer's left) hanging to the shins, its end flicking out
    fl = spline([ph(330, 700, 0.06), ph(290, 820, 0.05), ph(250, 920, 0.03), ph(215, 1000, 0.02), ph(175, 1045, 0.04), ph(150, 1055, 0.07)], 40)
    d.add(S.Warp(Sweep(fl, np.interp(np.linspace(0, 1, 40), [0, 0.5, 1], [0.08, 0.07, 0.02]), 0.0045, [nrm(A(0.3, 1, 0.3))] * 40), plate_folds(9, 0.014), 0.014), lr, 0.012)
    # flaps at the statue's left (viewer's right), fluttering
    fr = spline([ph(545, 720, 0.04), ph(570, 830, 0.04), ph(590, 950, 0.03), ph(620, 1030, 0.03), ph(660, 1080, 0.06), ph(690, 1095, 0.08)], 40)
    d.add(S.Warp(Sweep(fr, np.interp(np.linspace(0, 1, 40), [0, 0.5, 1], [0.07, 0.065, 0.02]), 0.0045, [nrm(A(-0.4, 1, 0.3))] * 40), plate_folds(10, 0.012), 0.012), lr, 0.012)
    m.field(d, 0.002, 18.0, lods=(0, 1))
    bf = Field('rock'); rng = np.random.default_rng(128)
    W.rock(bf, rng, 0.82, 0.56, ROCK_H, pads=[(A_R[0] + 0.04, A_R[1] + 0.06, 0.0, 0.09), (A_L[0], A_L[1] + 0.05, 0.0, 0.09)], z_top=0.0, c=((CX - 440) / KPX, 0.0))
    m.field(bf, 0.004, 5.0, lods=(0, 1))
    f2 = Field('lod2')
    f2.add(Ellipsoid(ph(450, 470, -0.03), A(0.2, 0.15, 0.24), fig.Rc), Lb, 0.05)
    f2.add(Ellipsoid(O, A(0.13, 0.14, 0.15)), Lb, 0.05)
    for a in arms.values(): f2.add(Tube([a['S'], a['E'], a['W']], [0.06, 0.05, 0.04]), Lb, 0.03)
    for g_ in legs.values(): f2.add(Tube([g_['H'], g_['K'], g_['A']], [0.1, 0.07, 0.04]), Lb, 0.03)
    f2.add(Loft([(0.45, cxm, 0.02, 0.24, 0.17), (0.93, cxm, 0.0, 0.18, 0.14)]), lr, 0.03)
    f2.add(Box(A(cxm, 0, -ROCK_H / 2), A(0.41, 0.28, ROCK_H / 2), None, 0.03), L['rock'], 0.02)
    m.field(f2, 0.009, 30.0, lods=(2,))
    # hands: the right palm raised forward, fingers up; the left fist on the hip
    Bd.HAND_POSES['raise'] = ((0.05, 0.1, 0.06), (0.04, 0.08, 0.05), (0.08, 0.12, 0.08), (0.14, 0.2, 0.1), (0.35, 0.15, 0.15, 0.25), 0.1)
    fdir_R = nrm(ph(240, 440, 0.15) - W_R)
    xf_R = Bd.hand_xf(W_R, fdir_R, A(0.2, -1.0, 0.0), 1)
    fdir_L = nrm(W_L - E_L)
    xf_L = Bd.hand_xf(W_L, fdir_L, A(-1, 0.3, 0.0), -1)
    m.instance('hand_raise', lambda: (Bd.hand_field('raise', 0.2, musc=0.6, lab='skin'), 0.0013), 5.0, [xf_R])
    m.instance('hand_fist', lambda: (Bd.hand_field('fist', 0.2, musc=0.8, lab='skin'), 0.0013), 5.0, [xf_L])
    def xm_fn(q):
        xm = X.XM()
        X.octa_plinth(xm, ((CX - 440) / KPX, 0, -ROCK_H - PLINTH), 0.95 / 2 / math.cos(math.pi / 4), [(1.0, 0.0, PLINTH), (1.03, 0.0, 0.02)], 'base', sides=4, phase=math.pi / 4)
        if q > 0.15:
            n = 80 if q > 0.6 else 24
            loop = [(240, 620, 0.06), (205, 520, 0.02), (195, 420, -0.02), (215, 330, -0.06), (255, 260, -0.09), (320, 205, -0.11), (400, 180, -0.12),
                    (470, 185, -0.12), (540, 215, -0.1), (590, 270, -0.07), (610, 350, -0.03), (612, 440, 0.02), (600, 520, 0.07), (570, 585, 0.12),
                    (510, 600, 0.15), (440, 598, 0.16), (370, 590, 0.15), (300, 600, 0.11), (250, 640, 0.07), (215, 720, 0.04), (190, 820, 0.02),
                    (170, 920, 0.02), (150, 1000, 0.04), (120, 1040, 0.07)]
            pts0 = spline([ph(px, py, y) for (px, py, y) in loop], n)
            ups = []
            for k, p in enumerate(pts0):
                o = nrm(A(p[0] - fig.Oc[0], 0.0, p[2] - fig.Oc[2]))
                ups.append(nrm(A(0, 1.0, 0) + o * 0.25))
            tg = np.gradient(pts0, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
            side = np.cross(tg, np.array(ups)); side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-9)
            for off, wd, dy in ((-0.022, 0.02, -0.003), (0.0, 0.021, 0.003), (0.022, 0.02, -0.003)):
                X.ribbon(xm, pts0 + side * off + np.array(ups) * dy, wd, 0.0025, ups, 'scarf')
        return xm
    m.xm_fn = xm_fn
    m.face_z = O[2]
    m.closeups = [('face', m.lift + O[2] + 0.02, 0.75, -0.3)]
    return m
