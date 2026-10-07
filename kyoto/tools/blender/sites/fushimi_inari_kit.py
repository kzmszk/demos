"""Fixed copies of jk.arch functions for 伏見稲荷大社 (the shared kit is not edited; reported to the lead).

kumimono: in jk.arch the 斗 on top of the arms are placed at c + [0, 0, t - z] where c already carries the
absolute height of the arm, so from the second tier on they float higher and higher (and poke through roofs);
here they sit on the arms (c + [0, 0, t - c.z]).  bracket_row: a row with only corner pillars now returns the
corner sets' top and reach."""
import math
import numpy as np
from jk import prim

def kumimono(B, x, y, z, out_dir, along, kind='demitsudo', s=1.0, mat='wood_dark', end_mat=None, tag='detail'):
    """a bracket set on a pillar top at (x, y, z): out_dir = unit vector (u, v) pointing out of the wall,
    along = unit vector along the wall.  kinds: 'funa' 舟肘木, 'hira' 平三斗, 'demitsudo' 出三斗, 'degumi' 出組,
    'futatesaki' 二手先, 'mitesaki' 三手先.  Returns the height of the top (where the purlin sits) and its outward reach."""
    o = np.array([out_dir[0], out_dir[1], 0.0]); a = np.array([along[0], along[1], 0.0])
    p = np.array([x, y, z])
    m = s * 0.26; mh = s * 0.17; hw = s * 0.15; hh = s * 0.17; arm = s * 0.55
    end_mat = end_mat or mat
    def masu(c, big=False):
        k = 1.5 if big else 1.0
        c = np.asarray(c, float)
        P = []
        # a block slightly wider at the top (斗): two rings
        for zz, sc in ((0.0, 0.8), (mh * k * 0.45, 0.8), (mh * k, 1.0)):
            for (du, dv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                P.append(c + a * du * m * k * 0.5 * sc + o * dv * m * k * 0.5 * sc + [0, 0, zz])
        P = np.array(P); I = []
        for r in range(2):
            for i in range(4):
                j = (i + 1) % 4; b0 = r * 4
                I += [[b0 + i, b0 + j, b0 + 4 + j], [b0 + i, b0 + 4 + j, b0 + 4 + i]]
        I += [[8, 9, 10], [8, 10, 11]]
        B.add(P, I, mat, tag=tag)
        return c[2] + mh * k
    def hijiki(c, d, L):
        c = np.asarray(c, float)
        prim.obox(B, c - d * L / 2 + [0, 0, hh / 2], c + d * L / 2 + [0, 0, hh / 2], hw, hh, mat, tag=tag)
        # rounded ends: a short lower chamfer block at each end
        for e in (-1, 1):
            q = c + d * e * (L / 2 - hw * 0.4)
            prim.obox(B, q + [0, 0, 0.0], q + [0, 0, hh * 0.45], hw * 1.02, hw * 0.8, mat, up=tuple(d), tag=tag)
        return c[2] + hh
    if kind == 'funa':
        prim.obox(B, p - a * arm + [0, 0, hh / 2], p + a * arm + [0, 0, hh / 2], hw * 1.2, hh, mat, tag=tag)
        return z + hh, 0.0
    top = masu(p, big=True)
    if kind == 'hira':
        t = hijiki(p + [0, 0, top - z], a, arm * 2)
        for e in (-1, 0, 1): masu(p + a * e * arm * 0.9 + [0, 0, t - z])
        return t + mh, 0.0
    steps = {'demitsudo': 1, 'degumi': 1, 'futatesaki': 2, 'mitesaki': 3}[kind]
    zc = top
    reach = 0.0
    for k in range(steps + (0 if kind == 'demitsudo' else 1)):
        c = p + o * reach + [0, 0, zc - z]
        t1 = hijiki(c, a, arm * 2)                          # along the wall
        t2 = hijiki(c + o * arm * 0.5, o, arm * 1.4)        # outward
        for e in (-1, 1): masu(c + a * e * arm * 0.9 + [0, 0, t1 - c[2]])
        masu(c + o * arm * 1.0 + [0, 0, t2 - c[2]])
        zc = max(t1, t2) + mh
        reach += arm
    if steps >= 2:   # 尾垂木: a sloping tail rafter through the set
        q0 = p - o * 0.8 + [0, 0, zc - z + 0.4]; q1 = p + o * (reach + 0.4) + [0, 0, zc - z - 0.35]
        prim.obox(B, q0, q1, hw * 1.2, hh * 1.3, mat, tag=tag)
        prim.obox(B, q1, q1 + (q1 - q0) / np.linalg.norm(q1 - q0) * 0.04, hw * 1.22, hh * 1.32, end_mat, tag=tag)
    return zc, reach

def bracket_row(B, L, D, z, kind, s=1.0, mat='wood_dark', end_mat=None, us=None, vs=None, purlin=True, tag='detail'):
    """bracket sets on every outer pillar of an L x D rectangle; returns (top height, reach)"""
    us = us if us is not None else np.array([-L / 2, L / 2]); vs = vs if vs is not None else np.array([-D / 2, D / 2])
    top = z; reach = 0.0
    pts = []
    for x in us[1:-1]: pts += [((x, -D / 2), (0, -1), (1, 0)), ((x, D / 2), (0, 1), (-1, 0))]     # corners get the diagonal sets below
    for y in vs[1:-1]: pts += [((-L / 2, y), (-1, 0), (0, 1)), ((L / 2, y), (1, 0), (0, -1))]
    for (pt, od, al) in pts:
        t, r = kumimono(B, pt[0], pt[1], z, od, al, kind, s, mat, end_mat, tag)
        top = max(top, t); reach = max(reach, r)
    # corner sets point diagonally
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = np.array([sx, sy]) / math.sqrt(2)
            t, r = kumimono(B, sx * L / 2, sy * D / 2, z, d, (-d[1], d[0]), kind, s, mat, end_mat, tag)
            top = max(top, t)
            if not pts: reach = max(reach, r / math.sqrt(2))      # (jk: a corner-only row returned top = z, reach = 0)
    if purlin:
        # 桁 / 丸桁 on top of the sets, at their outer reach
        a, c = L / 2 + reach, D / 2 + reach
        for (p0, p1) in (((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))):
            prim.obox(B, (p0[0], p0[1], top + 0.12), (p1[0], p1[1], top + 0.12), 0.24 * s, 0.24 * s, mat, tag='main')
    return top + 0.24 * s, reach
