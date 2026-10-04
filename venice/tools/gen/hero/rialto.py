"""Ponte di Rialto (Antonio da Ponte, 1588-91): a single Istrian-stone segmental arch (span 28.8 m, crown soffit
7.3 m above the water), 22.9 m wide, carrying three stepped walkways — the central one between two rows of
arcaded shops under lead roofs, two outer ones along the balustrades — meeting at the summit portico.

Placement from the OSM steps: central lane from (-222.5, 428.2) (San Marco side) to (-260.7, 460.2) (San Polo).
Local frame: s along the bridge (0 = summit, + toward San Polo), t across (+ = left of s), z absolute (water 0)."""
import math
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G, arch as A
from ..world import GROUND_Z

A0 = np.array([-222.5, 428.2]); A1 = np.array([-260.7, 460.2])
C = (A0 + A1) / 2
D = (A1 - A0) / np.linalg.norm(A1 - A0); N = np.array([-D[1], D[0]])
HW = 11.45                      # half width
SPAN = 28.8; ZCR = 7.32; ZSP = 0.6
TOP = 8.55                      # walkway at the summit
LAND = 3.9                      # half length of the summit landing
S_END = 25.0                    # where the ramps meet the rive
NST = 43
STONE = 'istrian'

def quad(m, pts, want, mat=STONE):
    """add a planar polygon whose normal agrees with `want`."""
    P = np.array(pts, float); n = np.cross(P[1] - P[0], P[2] - P[0])
    m.poly(pts if np.dot(n, want) >= 0 else pts[::-1], mat)

def frame():
    M = np.eye(4); M[:3, 0] = (D[0], D[1], 0); M[:3, 1] = (N[0], N[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (C[0], C[1], 0)
    return M

def zwalk(s):
    """walking surface height along the bridge (continuous ramp through the step noses)."""
    a = abs(s)
    if a <= LAND: return TOP
    if a >= S_END: return GROUND_Z
    return GROUND_Z + (TOP - GROUND_Z) * (S_END - a) / (S_END - LAND)

R_ARCH = ((SPAN / 2) ** 2 + (ZCR - ZSP) ** 2) / (2 * (ZCR - ZSP)); ZC_ARCH = ZCR - R_ARCH
def zarch(s): return ZC_ARCH + math.sqrt(max(0.0, R_ARCH ** 2 - s ** 2))

def steps(m, t0, t1, n, top, s_land, s_end, mat_tread='portico_floor'):
    """two flights of n steps (both ramps) between t0..t1 rising from GROUND_Z at |s|=s_end to `top` at s_land."""
    rise = (top - GROUND_Z) / n; tread = (s_end - s_land) / n
    for side in (-1, 1):
        for k in range(n):
            s_a = side * (s_end - k * tread); s_b = side * (s_end - (k + 1) * tread)
            lo, hi = min(s_a, s_b), max(s_a, s_b)
            z1 = GROUND_Z + rise * (k + 1)
            m.merge(G.box(lo, t0, z1 - 0.3, hi, t1, z1, mat_tread, faces=('+z',)))
            # riser (Istrian stone nosing) facing outward along the ramp
            sr = s_a
            if side > 0: m.merge(G.box(sr - 0.06, t0, z1 - rise, sr, t1, z1, STONE, faces=('+x', '+z')))
            else: m.merge(G.box(sr, t0, z1 - rise, sr + 0.06, t1, z1, STONE, faces=('-x', '+z')))
    m.merge(G.box(-s_land, t0, top - 0.3, s_land, t1, top, mat_tread, faces=('+z',)))

def arch_barrel():
    m = G.Mesh()
    K = 28
    ss = np.linspace(-SPAN / 2, SPAN / 2, K + 1)
    for i in range(K):
        s0, s1 = ss[i], ss[i + 1]; za, zb = zarch(s0), zarch(s1)
        q = [(s0, -HW, za), (s1, -HW, zb), (s1, HW, zb), (s0, HW, za)]
        sm, zm = (s0 + s1) / 2, (za + zb) / 2
        quad(m, q, (-sm, 0, ZC_ARCH - zm))               # soffit faces the arch centre (down)
    # abutment walls at the springing (down into the water)
    for sgn in (-1, 1):
        s = sgn * SPAN / 2
        m.merge(G.box(min(s, s + sgn * 0.01), -HW, -1.5, max(s, s + sgn * 0.01), HW, ZSP, STONE))
    return m

def spandrel(side):
    """face of the bridge on one side (t = side*HW): from the arch extrados up to the parapet base."""
    m = G.Mesh()
    t = side * HW
    K = 36
    top = []
    for s in np.linspace(-S_END - 2.0, S_END + 2.0, K):
        top.append((s, zwalk(max(-S_END, min(S_END, s))) - 0.05))
    bottom = [(-S_END - 2.0, GROUND_Z - 0.2), (-SPAN / 2, GROUND_Z - 0.2), (-SPAN / 2, ZSP)] + \
             [(s, zarch(s)) for s in np.linspace(-SPAN / 2, SPAN / 2, 30)[1:-1]] + [(SPAN / 2, ZSP), (SPAN / 2, GROUND_Z - 0.2), (S_END + 2.0, GROUND_Z - 0.2)]
    outline = bottom + top[::-1]
    if side > 0:
        m.merge(A.fix_orient(G.cap([outline], 0, STONE, True, G.frame((0, t, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))), (0, 1, 0)))
    else:
        m.merge(A.fix_orient(G.cap([outline], 0, STONE, True, G.frame((0, t, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    # archivolt (projecting ring) and keystone
    ring = 0.9
    pts_in = [(s, zarch(s)) for s in np.linspace(-SPAN / 2, SPAN / 2, 31)]
    for i in range(30):
        (s0, z0), (s1, z1) = pts_in[i], pts_in[i + 1]
        # outward offset along the radius
        def off(s, z, r):
            dx, dz = s - 0.0, z - ZC_ARCH; L = math.hypot(dx, dz)
            return (s + dx / L * r, z + dz / L * r)
        o0 = off(s0, z0, ring); o1 = off(s1, z1, ring)
        y0, y1 = (t, t + side * 0.18)
        quad(m, [(s0, y1, z0), (s1, y1, z1), (o1[0], y1, o1[1]), (o0[0], y1, o0[1])], (0, side, 0))
        quad(m, [(s0, y0, z0), (s1, y0, z1), (s1, y1, z1), (s0, y1, z0)], (-(s0 + s1) / 2, 0, ZC_ARCH - (z0 + z1) / 2))
    m.merge(G.box(-0.55, min(t, t + side * 0.3), ZCR - 0.2, 0.55, max(t, t + side * 0.3), ZCR + 1.4, STONE))
    # relief roundels on the spandrels (Annunciation / patron saints)
    for s in (-9.5, 9.5):
        z = (zarch(s) + zwalk(s)) / 2 - 0.4
        m.merge(G.box(s - 1.3, min(t, t + side * 0.22), z - 1.1, s + 1.3, max(t, t + side * 0.22), z + 1.1, 'relief'))
    # cornice under the balustrade, following the ramps
    for s0, s1 in zip(np.linspace(-S_END, S_END, 41)[:-1], np.linspace(-S_END, S_END, 41)[1:]):
        za, zb = zwalk(s0), zwalk(s1)
        y0, y1 = (t, t + side * 0.35)
        lo, hi = min(y0, y1), max(y0, y1)
        m.merge(_slab(s0, s1, za - 0.5, zb - 0.5, lo, hi, 0.45))
    return m

def _slab(s0, s1, za, zb, y0, y1, h):
    """sloped box between s0..s1 whose bottom runs from za to zb, height h, t from y0 to y1."""
    m = G.Mesh()
    P = [(s0, y0, za), (s1, y0, zb), (s1, y1, zb), (s0, y1, za), (s0, y0, za + h), (s1, y0, zb + h), (s1, y1, zb + h), (s0, y1, za + h)]
    o = m.add_v(P)
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        m.face([o + i for i in q], STONE)
    return m

def balustrade(side):
    """outer balustrade following the ramps: sloped rails on balusters, piers every few metres."""
    m = G.Mesh()
    t = side * (HW - 0.15)
    xs = np.linspace(-S_END, S_END, 25)
    for s0, s1 in zip(xs[:-1], xs[1:]):
        za, zb = zwalk(s0), zwalk(s1)
        m.merge(_slab(s0, s1, za + 0.95, zb + 0.95, t - 0.16, t + 0.16, 0.14))     # rail
        m.merge(_slab(s0, s1, za - 0.02, zb - 0.02, t - 0.14, t + 0.14, 0.12))     # plinth
        L = s1 - s0; n = max(1, int(L / 0.32))
        for k in range(n):
            s = s0 + (k + 0.5) * L / n; z = zwalk(s) + 0.1
            m.merge(A.baluster(0.82, 0.075, STONE, seg=6).transformed(G.mat4((s, t, z))))
        m.merge(G.box(s0 - 0.2, t - 0.2, za - 0.02, s0 + 0.2, t + 0.2, za + 1.15, STONE))
    return m

def shop_row(side):
    """arcaded shops between the central and the outer walkway, stepping down the ramps; lead roofs."""
    m = G.Mesh()
    t0, t1 = (3.1, 8.3) if side > 0 else (-8.3, -3.1)
    tin, tout = (t0, t1) if side > 0 else (t1, t0)        # tin faces the central walkway
    nb = 6
    for sgn in (-1, 1):
        edges = np.linspace(LAND + 0.6, S_END - 3.0, nb + 1)
        for k in range(nb):
            sa, sb = sgn * edges[k], sgn * edges[k + 1]
            lo, hi = min(sa, sb), max(sa, sb)
            zf = zwalk(sgn * (edges[k] + edges[k + 1]) / 2) - 0.1        # floor of this shop
            H = 4.3
            # walls: the shop as a box with an arched opening on the central side, blind arch outside
            m.merge(G.box(lo, t0, zf - 2.5, hi, t1, zf + H, 'portico_wall', faces=('-z',)))
            for (tt, face) in ((tin, -1), (tout, 1)):
                w = hi - lo; aw = w - 0.9; zs = zf + 2.6
                op = G.opening_shape(aw, zs + aw / 2 - zf, 'arch', n=10, x=0.45, y=0.0)
                wl = G.wall(w, H, 0.25, STONE, openings=[op], back=False, sides=False)
                n_out = (0, -side, 0) if tt == tin else (0, side, 0)
                m.merge(wl.transformed(_facing(lo, hi, tt, zf, n_out)))
                # infill: shop front (dark wood shutters) or blind panel
                infill = 'shop_wood' if tt == tin else STONE
                p2 = [(lo + 0.45 + p[0], p[1]) for p in op]
                m.merge(A.fix_orient(G.cap([p2], 0, infill, True, G.frame((0, tt - n_out[1] * 0.18, zf), (1, 0, 0), (0, 0, 1), (0, n_out[1], 0))), n_out))
                m.merge(A.arch_moulding(w / 2, zs - zf, aw / 2, 0.18, 0.06, STONE, n=10).transformed(_facing(lo, hi, tt, zf, n_out)))
            # pilasters at bay ends + cornice
            for s in (lo, hi):
                for tt in (t0, t1):
                    m.merge(G.box(s - 0.22, tt - 0.25, zf, s + 0.22, tt + 0.25, zf + H, STONE))
            m.merge(G.box(lo - 0.1, t0 - 0.35, zf + H, hi + 0.1, t1 + 0.35, zf + H + 0.35, STONE))
            # lead roof: low ridge along s
            rz = zf + H + 0.35; tc = (t0 + t1) / 2
            for (a, b) in ((t0 - 0.35, tc), (tc, t1 + 0.35)):
                za_, zb_ = (rz + 1.3 if a == tc else rz), (rz + 1.3 if b == tc else rz)
                quad(m, [(lo - 0.1, a, za_), (hi + 0.1, a, za_), (hi + 0.1, b, zb_), (lo - 0.1, b, zb_)], (0, 0, 1), 'lead')
            # end walls of each stepped block (above the lower neighbour)
            for s in (lo, hi):
                m.merge(G.box(s - 0.12, t0 - 0.35, zf + H, s + 0.12, t1 + 0.35, zf + H + 1.6, 'lead'))
    return m

def _facing(s0, s1, t, z, n_out):
    """kit frame (facade faces local -y, x along the facade over [0, s1-s0]) on the plane t, facing n_out (+-t)."""
    if n_out[1] < 0: return G.frame((s0, t, z), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    return G.frame((s1, t, z), (-1, 0, 0), (0, -1, 0), (0, 0, 1))

def portico():
    """summit portico: a large arch over the central walkway on each face, pediments, lead roof."""
    m = G.Mesh()
    z0 = TOP - 0.05; H = 11.0
    for sgn in (-1, 1):
        s = sgn * LAND
        w = 6.6; aw = 4.4
        op = G.opening_shape(aw, 7.2, 'arch', n=14, x=(w - aw) / 2, y=0.0)
        wl = G.wall(w, H, 0.6, STONE, openings=[op], back=True, sides=True)
        # kit frame: local x across the bridge (t), local -y faces outward along s
        F = np.eye(4)
        F[:3, 0] = (0, sgn, 0); F[:3, 1] = (-sgn, 0, 0); F[:3, 2] = (0, 0, 1); F[:3, 3] = (s + sgn * 0.6, -sgn * w / 2, z0)
        m.merge(wl.transformed(F))
        m.merge(A.arch_moulding(w / 2, 7.2 - aw / 2, aw / 2, 0.3, 0.1, STONE, n=14).transformed(F))
        m.merge(A.pediment_tri(-0.3, w + 0.3, H, 2.2, 0.6, 0.35, 0.5, STONE).transformed(F))
        for x in (0.45, w - 0.45):
            m.merge(G.box(x - 0.3, -0.18, 0.0, x + 0.3, 0.0, H - 0.6, STONE).transformed(F))
        m.merge(A.straight(A.cornice_profile(0.5, 0.35), -0.2, w + 0.2, H - 0.6, 0.0, STONE).transformed(F))
    # vault over the summit + lead gable roof
    m.merge(G.box(-LAND, -3.3, TOP + H - 0.4, LAND, 3.3, TOP + H, STONE))
    for sgn in (-1, 1):
        quad(m, [(-LAND - 0.7, sgn * 3.6, TOP + H), (LAND + 0.7, sgn * 3.6, TOP + H), (LAND + 0.7, 0.0, TOP + H + 2.2), (-LAND - 0.7, 0.0, TOP + H + 2.2)], (0, sgn, 1), 'lead')
    return m

def build_mesh():
    m = G.Mesh()
    m.merge(arch_barrel())
    for side in (-1, 1):
        m.merge(spandrel(side)); m.merge(balustrade(side)); m.merge(shop_row(side))
    # walkways: central between the shop rows, outer ones along the balustrades
    steps(m, -3.1, 3.1, NST, TOP, LAND, S_END)
    for side in (-1, 1):
        t0, t1 = (8.3, HW - 0.35) if side > 0 else (-HW + 0.35, -8.3)
        steps(m, t0, t1, NST - 1, TOP - 0.15, LAND, S_END)
    # bridge body under the walkways (closes the volume above the arch)
    m.merge(portico())
    return m

def build(mb):
    from .common import place
    place(mb, build_mesh(), frame())
    return dict(height=TOP + 13.0)

def walk_areas():
    """walkways with their ramp heights; shops and parapets blocked."""
    out = []
    def poly(s0, s1, t0, t1):
        P = [C + D * s0 + N * t0, C + D * s1 + N * t0, C + D * s1 + N * t1, C + D * s0 + N * t1]
        return Polygon(P)
    prof = {'a': C.tolist(), 'd': D.tolist(), 'prof': [(-S_END - 1.0, GROUND_Z), (-S_END, GROUND_Z), (-LAND, TOP), (LAND, TOP), (S_END, GROUND_Z), (S_END + 1.0, GROUND_Z)]}
    out.append((poly(-S_END - 0.5, S_END + 0.5, -HW, HW), None))                  # block the whole deck first
    for (t0, t1) in ((-3.0, 3.0), (8.4, HW - 0.4), (-HW + 0.4, -8.4)):
        out.append((poly(-S_END - 0.5, S_END + 0.5, t0, t1), prof))
    return out
