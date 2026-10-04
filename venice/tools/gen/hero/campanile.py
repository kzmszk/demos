"""Campanile di San Marco (98.6 m) and Sansovino's Loggetta, in the piazza frame (campanile faces are
aligned with the piazza axes; OSM footprint ~12.4 m square centred near the origin)."""
import math
import numpy as np
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import place, translate, compose, wf, pf, PU, PV

STONE = 'trim'

def frame_piazza(cu, cv, rot=0.0):
    """kit frame at piazza (cu, cv): x along +u rotated by rot (radians, CCW), z up."""
    c, s = math.cos(rot), math.sin(rot)
    xu = PU * c + PV * s; yv = -PU * s + PV * c
    o = wf(cu, cv)
    M = np.eye(4); M[:3, 0] = (xu[0], xu[1], 0); M[:3, 1] = (yv[0], yv[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (o[0], o[1], GROUND_Z)
    return M

def face(m, side, width, z0, z1, depth_out=0.0):
    """helper: a kit Mesh built for a facade (x along, -y out) placed on one side of a square tower of half
    width hw centred at the origin.  side 0..3 = facing -v, +u, +v, -u."""
    pass

def campanile():
    m = G.Mesh()
    S = 12.4; hw = S / 2
    # plinth (Istrian stone, stepped)
    m.merge(G.box(-hw - 0.5, -hw - 0.5, -0.2, hw + 0.5, hw + 0.5, 0.45, STONE))
    m.merge(G.box(-hw - 0.25, -hw - 0.25, 0.45, hw + 0.25, hw + 0.25, 1.4, STONE))
    # brick shaft with pilaster strips (lesene) joining in round arches at the top
    z0, z1 = 1.4, 48.4
    m.merge(G.box(-hw, -hw, z0, hw, hw, z1, 'campanile_brick', faces=('-x', '+x', '-y', '+y')))
    nlp = 5; pw = 0.75; pd = 0.32
    for k in range(4):
        R = G.mat4((0, 0, 0), rz=k * math.pi / 2)
        sub = G.Mesh()
        for i in range(nlp):
            x = -hw + pw / 2 + (S - pw) * i / (nlp - 1)
            sub.merge(G.box(x - pw / 2, -hw - pd, z0, x + pw / 2, -hw, z1 - 2.6, 'campanile_brick', faces=('-y', '-x', '+x')))
        # arches between the pilasters at the top + a brick cornice
        for i in range(nlp - 1):
            xa = -hw + pw + (S - pw) * i / (nlp - 1); xb = -hw + (S - pw) * (i + 1) / (nlp - 1)
            r = (xb - xa) / 2; cx = (xa + xb) / 2; zs = z1 - 2.6 - 0.2
            pts = [(cx + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, math.pi, 10)]
            for j in range(len(pts) - 1):
                (xa1, za1), (xb1, zb1) = pts[j], pts[j + 1]
                sub.merge(G.box(min(xa1, xb1) - 0.02, -hw - pd, min(za1, zb1), max(xa1, xb1) + 0.02, -hw, max(za1, zb1) + 0.35, 'campanile_brick', faces=('-y', '-z')))
        sub.merge(G.box(-hw - pd - 0.1, -hw - pd - 0.15, z1 - 0.9, hw + pd + 0.1, -hw, z1, STONE))
        m.merge(sub.transformed(R))
    # belfry: Istrian stone loggia, four arches per side on columns, balustrade
    b0, b1 = 48.4, 59.0
    bw = hw + 0.2
    m.merge(G.box(-bw - 0.25, -bw - 0.25, b0, bw + 0.25, bw + 0.25, b0 + 0.55, STONE))
    for k in range(4):
        R = G.mat4((0, 0, 0), rz=k * math.pi / 2)
        sub = G.Mesh()
        n = 4; aw = (2 * bw - 0.8 * (n + 1)) / n
        for i in range(n + 1):
            x = -bw + 0.4 + (2 * bw - 0.8) * i / n
            sub.merge(G.box(x - 0.4, -bw, b0 + 0.55, x + 0.4, -bw + 0.6, b1 - 2.4, STONE))
            sub.merge(A.column(0.42, b1 - 2.4 - b0 - 0.55 - 0.2, order='corinthian', mat=STONE, seg=8, detail=0.1).transformed(G.mat4((x, -bw - 0.2, b0 + 0.55))))
        for i in range(n):
            xa = -bw + 0.8 + (2 * bw - 0.8) * i / n; xb = xa + aw
            r = (xb - xa) / 2; cx = (xa + xb) / 2; zs = b1 - 2.4 - r * 0.15
            sub.merge(A.arch_moulding(cx, zs, r, 0.3, 0.08, STONE, y=-bw, n=10))
            sub.merge(A.balustrade(xa + 0.05, xb - 0.05, b0 + 0.55, 1.0, 0.22, STONE, y=-bw + 0.05, bal_seg=6))
        sub.merge(G.box(-bw, -bw, b1 - 2.4, bw, -bw + 0.6, b1, STONE, faces=('-y', '+z', '-z')))
        m.merge(sub.transformed(R))
    # bell-chamber core (dark) + bells hint
    m.merge(G.box(-hw + 1.6, -hw + 1.6, b0 + 0.55, hw - 1.6, hw - 1.6, b1, 'dark'))
    m.merge(A.straight(A.cornice_profile(0.9, 0.6), -bw - 0.2, bw + 0.2, b1, -bw - 0.2, STONE).transformed(np.eye(4)))
    for k in range(4):
        R = G.mat4((0, 0, 0), rz=k * math.pi / 2)
        m.merge(A.straight(A.cornice_profile(0.9, 0.6), -bw - 0.2, bw + 0.2, b1, -bw, STONE).transformed(R))
    # attic (dado) with framed relief panels (lion / Venice as Justice), Istrian stone
    a0, a1 = 59.9, 69.6
    aw2 = hw - 0.3
    m.merge(G.box(-aw2, -aw2, a0, aw2, aw2, a1, STONE, faces=('-x', '+x', '-y', '+y')))
    for k in range(4):
        R = G.mat4((0, 0, 0), rz=k * math.pi / 2)
        sub = G.Mesh()
        sub.merge(G.box(-aw2 + 1.0, -aw2 - 0.12, a0 + 1.2, aw2 - 1.0, -aw2, a0 + 1.4, STONE))
        sub.merge(G.box(-aw2 + 1.0, -aw2 - 0.12, a1 - 1.4, aw2 - 1.0, -aw2, a1 - 1.2, STONE))
        sub.merge(G.box(-aw2 + 1.0, -aw2 - 0.12, a0 + 1.2, -aw2 + 1.2, -aw2, a1 - 1.2, STONE))
        sub.merge(G.box(aw2 - 1.2, -aw2 - 0.12, a0 + 1.2, aw2 - 1.0, -aw2, a1 - 1.2, STONE))
        sub.merge(G.box(-1.8, -aw2 - 0.25, a0 + 2.4, 1.8, -aw2, a1 - 2.6, 'relief'))          # relief panel
        m.merge(sub.transformed(R))
    m.merge(G.box(-aw2 - 0.4, -aw2 - 0.4, a1, aw2 + 0.4, aw2 + 0.4, a1 + 0.7, STONE))
    # spire: green copper pyramid with corner pinnacles
    s0, s1 = a1 + 0.7, 95.2
    sw = aw2 + 0.1
    tip = (0, 0, s1)
    base = [(-sw, -sw, s0), (sw, -sw, s0), (sw, sw, s0), (-sw, sw, s0)]
    for k in range(4):
        a, b = base[k], base[(k + 1) % 4]
        o = m.add_v([a, b, tip]); m.face([o, o + 1, o + 2], 'copper')
    for (sx, sy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        m.merge(G.lathe([(0.5, 0), (0.42, 1.5), (0.0, 3.4)], 8, mat='copper').transformed(G.mat4((sx * (sw - 0.3), sy * (sw - 0.3), s0))))
    # gilded archangel Gabriel (stylised: orb + figure + wings)
    m.merge(G.lathe([(0.0, 0), (0.35, 0.2), (0.4, 0.6), (0.2, 0.9), (0.12, 1.0)], 10, mat='gold').transformed(G.mat4((0, 0, s1 - 0.3))))
    m.merge(G.lathe([(0.25, 0), (0.32, 1.2), (0.18, 2.0), (0.14, 2.2), (0.18, 2.4), (0.0, 2.65)], 10, mat='gold').transformed(G.mat4((0, 0, s1 + 0.65))))
    m.merge(G.box(-0.05, -1.3, s1 + 1.8, 0.05, 1.3, s1 + 2.3, 'gold'))
    return m

def loggetta():
    """Sansovino's Loggetta against the campanile's east face: three arches between paired columns, attic,
    terrace with balustrade.  Local x along v (south->north), facade faces +u (east)."""
    m = G.Mesh()
    W = 15.2; H = 9.0
    # the kit faces -y; we build with x along the facade and rotate later
    m.merge(G.box(0, -6.4, -0.2, W, 0.0, 0.85, STONE))                                         # terrace podium
    m.merge(A.balustrade(0.2, W - 0.2, 0.85, 0.95, 0.24, STONE, y=-6.4, pier_every=2.6, bal_seg=6))
    m.merge(G.box(0, 0.0, 0.85, W, 3.8, H, 'marble_red', faces=('-y', '+z', '-x', '+x')))
    bays = 3; bw = W / bays
    for i in range(bays):
        xc = bw * (i + 0.5); aw = 2.2; zs = 0.85 + 4.4
        m.merge(G.box(xc - aw / 2, -0.02, 0.85, xc + aw / 2, 0.02, zs + aw / 2, 'dark'))
        m.merge(A.arch_moulding(xc, zs, aw / 2, 0.3, 0.1, 'marble_white', y=-0.05, n=12))
    for i in range(bays + 1):
        x = bw * i
        for dx in (-0.55, 0.55):
            xx = min(W - 0.4, max(0.4, x + dx))
            m.merge(A.column(0.5, 5.4, order='corinthian', mat='marble_verde', cap_mat='marble_white', seg=10, detail=0.4, pedestal=0.9).transformed(G.mat4((xx, -0.45, 0.85))))
        if 0 < i < bays:
            m.merge(A.niche(1.0, 2.6, 0.4, 'marble_white').transformed(G.mat4((x, -0.03, 2.3))))
    m.merge(A.entablature(0, W, 7.15, 1.1, 0.5, 'marble_white'))
    m.merge(G.box(0, 0.0, 8.25, W, 3.8, H + 1.2, 'marble_white', faces=('-y', '+z', '-x', '+x')))
    for i in range(bays):
        xc = bw * (i + 0.5)
        m.merge(G.box(xc - 1.6, -0.12, 8.5, xc + 1.6, 0.0, 9.9, 'relief'))
    m.merge(A.balustrade(0, W, H + 1.2, 0.8, 0.2, 'marble_white', y=0.0, bal_seg=6))
    return m

def build(mb):
    M = frame_piazza(0.0, 0.0)
    place(mb, campanile(), M)
    # loggetta along the east face (u = +6.2), facing +u: kit x along +v, -y = +u
    Ml = frame_piazza(10.0, -7.6, rot=math.pi / 2)
    place(mb, loggetta(), Ml)
    return dict(height=98.6)
