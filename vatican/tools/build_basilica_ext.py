"""St Peter's Basilica — exterior.  Local frame (site.B2W): u east along the axis (toward the facade),
v north, z above the basilica floor; origin = dome axis.  Dimensions from Fontana's Templum Vaticanum
(1694) plan/elevations and OSM, see notes inline.  Returns a Mesh in WORLD coordinates."""
import math, sys
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import *
from vb.arch import *
from vb import site

TRAV = 'travertine'; TRAV_D = 'travertine_dark'; LEAD = 'lead_dome'
# giant order (Michelangelo / Maderno) above the floor
ORD_H = 25.0        # base of pilasters to top of capitals
ENT_Z0, ENT_Z1 = 25.0, 32.0
ATTIC_Z1 = 44.0     # top of attic cornice
PIL_W, PIL_D = 2.6, 0.55
U_FAC = 133.6       # facade wall plane (columns ~1.9 m in front, at u ~135.5 as in OSM)
FAC_HALF = 57.35    # 114.69 / 2


def arc(cu, cv, r, a0, a1, n):
    return [(cu + r * math.cos(a0 + (a1 - a0) * i / n), cv + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def outline():
    """symmetric outline of Michelangelo's body + Maderno's nave (without the facade block), CCW."""
    N = []
    # west apse (centre u=-52.3, r=23): polygonal, 5 faces over the half circle
    N += arc(-52.3, 0.0, 23.0, math.pi, math.pi / 2, 5)[0:]          # from apex (v=0) round to v=+23
    N += [(-52.3, 52.2), (-35.5, 52.2), (-23.5, 54.5)]
    N += arc(0.0, 54.5, 23.5, math.pi, 0, 7)[1:]                       # north apse
    N += [(35.5, 52.2), (54.0, 52.2), (54.0, 47.4), (78.8, 47.4), (78.8, 38.0), (117.0, 38.0)]
    S = [(u, -v) for (u, v) in N[::-1]]
    ring = S[:-1] + N           # south half reversed + north half (apex shared)
    ring = [p for i, p in enumerate(ring) if i == 0 or math.dist(p, ring[i - 1]) > 0.01]
    return ccw(ring)


def seg_frame(A, B, z0=0.0):
    """arch-kit frame on the outside face of segment A->B of a CCW outline (x along, y into the wall)."""
    d = np.array([B[0] - A[0], B[1] - A[1], 0.0]); L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0], 0.0])      # outward (right of travel)
    return frame((A[0], A[1], z0), d, -n, (0, 0, 1)), L


def giant_wall(m, A, B, attic=True, windows=True, tiers=3, corner_pil=True):
    """Michelangelo's elevation on one straight outline segment: giant Corinthian pilasters,
    3 tiers of windows, entablature and attic.  Built in the segment frame then transformed."""
    F, L = seg_frame(A, B)
    if L < 1.0: return
    w = Mesh()
    nb = max(1, int(round(L / 9.5)))
    xs = [L * i / nb for i in range(nb + 1)]
    # base plinth
    w.merge(straight(plain_band(1.4, 0.35), 0, L, 0, 0, TRAV_D))
    for i, x in enumerate(xs):
        if not corner_pil and (i == 0 or i == nb): continue
        xx = min(max(x, PIL_W / 2), L - PIL_W / 2)
        if L < PIL_W * 1.2: break
        w.merge(pilaster(PIL_W, ORD_H, PIL_D, 'corinthian', TRAV).transformed(mat4((xx, 0, 0))))
    # windows per bay
    if windows:
        for i in range(nb):
            a, b = xs[i] + PIL_W / 2, xs[i + 1] - PIL_W / 2
            bw = b - a; cx = (a + b) / 2
            if bw < 3.2: continue
            ww = min(3.2, bw * 0.45)
            kind = 'tri' if i % 2 == 0 else 'seg'
            w.merge(aedicule(cx, 7.5, ww, 5.6, TRAV, kind, y=0.0))
            if tiers >= 2:
                w.merge(aedicule(cx, 17.0, ww * 0.85, 3.6, TRAV, 'flat', y=0.0))
            if attic and tiers >= 3:
                w.merge(aedicule(cx, 35.0, ww * 0.9, 4.2, TRAV, 'flat', y=0.0))
    # entablature (projects over the pilaster faces) + attic
    w.merge(straight(architrave_profile(ENT_Z1 * 0 + 2.1, 0.35), 0, L, ENT_Z0, -PIL_D, TRAV))
    w.merge(straight([(0, 0), (0.05, 0), (0.05, 2.1), (0, 2.1)], 0, L, ENT_Z0 + 2.1, -PIL_D, TRAV))
    w.merge(straight(cornice_profile(2.8, 1.9), 0, L, ENT_Z0 + 4.2, -PIL_D, TRAV))
    if attic:
        # attic pilaster strips aligned with the giant pilasters, then the attic cornice
        for i, x in enumerate(xs):
            xx = min(max(x, PIL_W / 2), L - PIL_W / 2)
            if L < PIL_W * 1.2: break
            w.merge(box(xx - PIL_W / 2, -0.35, ENT_Z1, xx + PIL_W / 2, 0, ATTIC_Z1 - 1.8, TRAV))
        w.merge(straight(cornice_profile(1.8, 1.0), 0, L, ATTIC_Z1 - 1.8, 0, TRAV))
    m.merge(w.transformed(F))


def in_roof_hole(u, v):
    """areas where the interior rises above the roof terrace (arms' vaults, the crossing)"""
    if abs(v) < 15.5 and -52.0 < u < 116.5: return True
    if abs(u) < 15.5 and abs(v) < 52.0: return True
    R = 35.5
    if max(abs(u), abs(v), (abs(u) + abs(v)) / math.sqrt(2)) < R * math.cos(math.pi / 8): return True
    return False

def terrace(R, z, cell=1.0):
    """flat roof terrace over the outline, with holes where the interior spaces rise above it"""
    m = Mesh()
    xs = [p[0] for p in R]; ys = [p[1] for p in R]
    def pip(x, y):
        c = False
        for i in range(len(R)):
            x0, y0 = R[i]; x1, y1 = R[(i + 1) % len(R)]
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
        return c
    u = math.floor(min(xs)); 
    while u < max(xs):
        v = math.floor(min(ys))
        while v < max(ys):
            cu, cv = u + cell / 2, v + cell / 2
            if pip(cu, cv) and not in_roof_hole(cu, cv):
                o = m.add_v([(u, v, z), (u + cell, v, z), (u + cell, v + cell, z), (u, v + cell, z)])
                m.face([o, o + 1, o + 2, o + 3], 'roof_flat')
            v += cell
        u += cell
    return m

def body():
    m = Mesh()
    R = outline()
    m.merge(prism([R], -4.0, ATTIC_Z1, TRAV, top=False))
    m.merge(terrace(R, ATTIC_Z1))
    n = len(R)
    for i in range(n):
        A, B = R[i], R[(i + 1) % n]
        if A[0] > 116.5 and B[0] > 116.5: continue        # the facade block covers this edge
        giant_wall(m, A, B)
    return m


# ------------------------------------------------------------------- roofs over the body
def roofs():
    m = Mesh()
    z0 = ATTIC_Z1
    # four arms: barrel roofs from the crossing to the apse / facade (lead), width ~31 m
    hw = 15.5; rise = 8.0
    def barrel(u0, u1, axis='u', n=10):
        prof = [(hw * math.cos(math.pi * i / n), rise * math.sin(math.pi * i / n)) for i in range(n + 1)]
        g = Mesh()
        for i in range(n):
            (a0, h0), (a1, h1) = prof[i], prof[i + 1]
            if axis == 'u':
                g.face([g.add_v([(u0, a0, z0 + h0)]), g.add_v([(u0, a1, z0 + h1)]), g.add_v([(u1, a1, z0 + h1)]), g.add_v([(u1, a0, z0 + h0)])], 'lead', True)
            else:
                g.face([g.add_v([(a0, u1, z0 + h0)]), g.add_v([(a1, u1, z0 + h1)]), g.add_v([(a1, u0, z0 + h1)]), g.add_v([(a0, u0, z0 + h0)])], 'lead', True)
        # gable ends
        for uu in (u0, u1):
            pts = [(a, h) for (a, h) in prof]
            if axis == 'u':
                g.merge(fix_orient(cap([pts], 0, TRAV, True, frame((uu, 0, z0), (0, 1, 0), (0, 0, 1), (1, 0, 0))), (1 if uu == u1 else -1, 0, 0)))
            else:
                g.merge(fix_orient(cap([pts], 0, TRAV, True, frame((0, uu, z0), (1, 0, 0), (0, 0, 1), (0, 1, 0))), (0, 1 if uu == u1 else -1, 0)))
        return g
    m.merge(barrel(32.0, 116.5, 'u'))          # nave (Maderno)
    m.merge(barrel(-52.0, -32.0, 'u'))         # west arm
    m.merge(barrel(32.0, 52.0, 'v'))           # north arm
    m.merge(barrel(-52.0, -32.0, 'v'))         # south arm
    # half domes over the three apses
    for (cu, cv, a) in ((-52.3, 0, math.pi), (0, 54.5, math.pi / 2), (0, -54.5, -math.pi / 2)):
        prof = [(hw * math.cos(t), rise * 1.2 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 7)]
        hd = lathe(prof, 12, a0=a - math.pi / 2, a1=a + math.pi / 2, mat='lead', center=(cu, cv, z0))
        m.merge(hd)
    # octagonal mass under the drum ("masso ottangolare"), travertine, to z 59.2
    R = 35.5
    oct_ = [(R * math.cos(math.pi / 8 + k * math.pi / 4), R * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    m.merge(prism([oct_], z0 - 1, Z_B, TRAV, top=False))
    hole = [((R_BUTT + 2.0) * math.cos(2 * math.pi * k / 64), (R_BUTT + 2.0) * math.sin(2 * math.pi * k / 64)) for k in range(64)]
    m.merge(cap([oct_, hole], Z_B, 'roof_flat', True))
    for k in range(8):
        A, B = oct_[k], oct_[(k + 1) % 8]
        F, L = seg_frame(A, B, 0)
        g = Mesh()
        g.merge(straight(cornice_profile(1.4, 0.8), 0, L, Z_B - 1.4, 0, TRAV))
        for x in (2.0, L - 2.0):
            g.merge(box(x - 1.3, -0.3, z0, x + 1.3, 0, Z_B - 1.4, TRAV))
        g.merge(aedicule(L / 2, z0 + 2.0, 2.6, 3.6, TRAV, 'flat'))
        m.merge(g.transformed(F))
    return m


# ------------------------------------------------------------------- drum, dome, lantern
Z_B = 53.0            # top of the octagonal mass (photo/OSM calibrated, see notes)
Z_D = 56.8            # top of the circular zoccolone (D)
Z_F = 60.6            # top of the pedestal (F) = column bases
Z_DRUM = 75.0         # top of the drum entablature
Z_ATTIC = 81.3        # dome springing (I)
Z_LANT = 110.2        # lantern base (L)
Z_CROSS = 136.57
R_DRUM_WALL = 26.0    # drum wall outer face
R_BUTT = 30.0         # outer face of the buttress columns
# heights cross-checked: Ponte Sant'Angelo photo (telephoto) + OSM parts (drum 60, lantern 110, cross 136.5)


def dome_profile():
    """outer dome surface (r, z) from the traced engraving, springing at Z_ATTIC r=23.4 to the lantern ring."""
    pts = [(22.7, 87.6), (22.4, 89.8), (22.0, 92.0), (21.2, 94.2), (20.3, 96.5), (19.3, 98.7), (18.1, 100.9), (16.8, 103.2),
           (15.2, 105.4), (13.4, 107.6), (11.4, 109.9), (8.7, 112.1), (6.4, 113.7)]
    k = 25.6 / 22.7
    out = [(r * k, Z_ATTIC + (z - 87.6) * (Z_LANT - Z_ATTIC) / (113.7 - 87.6)) for (r, z) in pts]
    return out


def drum_dome():
    m = Mesh()
    # D: circular zoccolone (two steps) and F: pedestal ring
    m.merge(lathe([(R_BUTT + 3.2, Z_B - 0.2), (R_BUTT + 3.2, Z_B + 2.2), (R_BUTT + 2.4, Z_B + 2.6), (R_BUTT + 2.4, Z_D), (R_DRUM_WALL, Z_D)], 64, mat=TRAV, smooth=False))
    m.merge(lathe([(R_BUTT + 0.6, Z_D), (R_BUTT + 0.6, Z_F - 0.5), (R_BUTT + 1.0, Z_F - 0.2), (R_BUTT + 1.0, Z_F), (R_DRUM_WALL, Z_F)], 64, mat=TRAV, smooth=False))
    # drum wall (16 sides between buttresses), windows with alternating pediments
    NB = 16
    poly = [(R_DRUM_WALL * math.cos(2 * math.pi * k / NB), R_DRUM_WALL * math.sin(2 * math.pi * k / NB)) for k in range(NB)]
    for k in range(NB):
        a0 = 2 * math.pi * (k - 0.5) / NB; a1 = 2 * math.pi * (k + 0.5) / NB
        A = (R_DRUM_WALL * math.cos(a0) / math.cos(math.pi / NB), R_DRUM_WALL * math.sin(a0) / math.cos(math.pi / NB))
        B = (R_DRUM_WALL * math.cos(a1) / math.cos(math.pi / NB), R_DRUM_WALL * math.sin(a1) / math.cos(math.pi / NB))
        F, L = seg_frame(B, A, 0)   # ring is CCW; B->A runs clockwise -> outward is left... use A->B reversed handled below
        F, L = seg_frame(A, B, 0)
        g = Mesh()
        H = Z_DRUM - Z_F
        g.merge(wall(L, H, 2.5, TRAV, [opening_shape(3.2, 6.6, 'rect', x=L / 2 - 1.6, y=2.6)], back=False, sides=False).transformed(mat4((0, 0, Z_F))))
        g.merge(aedicule(L / 2, Z_F + 2.6, 3.2, 6.6, TRAV, 'tri' if k % 2 else 'seg', y=0))
        m.merge(g.transformed(F))
    # paired buttress columns + broken entablature over each buttress
    for k in range(NB):
        a = 2 * math.pi * (k + 0.5) / NB
        ca, sa = math.cos(a), math.sin(a)
        rad = np.array([ca, sa, 0.0]); tan = np.array([-sa, ca, 0.0])
        # buttress pier (radial wall) behind the columns
        c0 = rad * R_DRUM_WALL
        F = frame(tuple(c0 + np.array([0, 0, Z_F])), tan, -rad, (0, 0, 1))   # local x along tangent, y inward
        g = Mesh()
        HC = Z_DRUM - Z_F - 2.4
        g.merge(box(-1.6, -(R_BUTT - R_DRUM_WALL) + 1.0, 0, 1.6, 0.5, Z_DRUM - Z_F, TRAV))
        for s in (-1, 1):
            g.merge(column(1.85, HC, 'corinthian', TRAV).transformed(mat4((s * 1.65, -(R_BUTT - R_DRUM_WALL) + 1.0, 0))))
        # entablature block over the pair
        g.merge(box(-3.4, -(R_BUTT - R_DRUM_WALL) - 0.2, HC, 3.4, 0.5, HC + 1.2, TRAV))
        g.merge(straight(cornice_profile(1.2, 0.8), -3.4, 3.4, HC + 1.2, -(R_BUTT - R_DRUM_WALL) - 0.2, TRAV))
        m.merge(g.transformed(F))
    # continuous drum entablature on the wall
    m.merge(lathe([(R_DRUM_WALL + 0.3, Z_DRUM - 2.6), (R_DRUM_WALL + 0.8, Z_DRUM - 1.4), (R_DRUM_WALL + 0.8, Z_DRUM - 1.0),
                   (R_DRUM_WALL + 1.6, Z_DRUM - 0.4), (R_DRUM_WALL + 1.6, Z_DRUM), (R_DRUM_WALL, Z_DRUM)], 64, mat=TRAV, smooth=False))
    # attic (H) with festoon panels: plain cylinder + pilaster strips + cornice
    m.merge(lathe([(R_DRUM_WALL + 0.2, Z_DRUM), (R_DRUM_WALL + 0.2, Z_ATTIC - 1.2), (R_DRUM_WALL + 0.9, Z_ATTIC - 0.6), (R_DRUM_WALL + 0.9, Z_ATTIC), (25.4, Z_ATTIC)], 64, mat=TRAV, smooth=False))
    for k in range(NB):
        a = 2 * math.pi * (k + 0.5) / NB
        rad = np.array([math.cos(a), math.sin(a), 0.0]); tan = np.array([-math.sin(a), math.cos(a), 0.0])
        F = frame(tuple(rad * (R_DRUM_WALL + 0.2) + np.array([0, 0, Z_DRUM])), tan, -rad, (0, 0, 1))
        g = box(-1.6, -0.6, 0, 1.6, 0, Z_ATTIC - Z_DRUM - 1.2, TRAV)
        # candelabra-like finial standing above each buttress pair at attic level
        g.merge(lathe([(0.6, 0), (0.7, 0.4), (0.4, 1.0), (0.5, 1.8), (0.15, 2.6), (0, 2.8)], 10, mat=TRAV, center=(0, -2.6, Z_ATTIC - Z_DRUM - 1.2 + 0.0)))
        m.merge(g.transformed(F))
        # festoon panel between strips
        b = 2 * math.pi * k / NB
        rad2 = np.array([math.cos(b), math.sin(b), 0.0]); tan2 = np.array([-math.sin(b), math.cos(b), 0.0])
        F2 = frame(tuple(rad2 * (R_DRUM_WALL + 0.25) + np.array([0, 0, Z_DRUM + 1.0])), tan2, -rad2, (0, 0, 1))
        fest = Mesh()
        fest.merge(box(-3.0, -0.12, 0.0, 3.0, 0, 3.2, TRAV))
        pts = [(-2.6 + 5.2 * t, 0, 2.6 - 1.4 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 9)]
        fest.merge(sweep([(0.0, -0.22), (0.3, -0.15), (0.35, 0.0), (0.3, 0.15), (0.0, 0.22)], [(p[0], -0.12, p[2]) for p in pts], TRAV, up=(0, -1, 0)))
        m.merge(fest.transformed(F2))
    # dome shell: lead fields + 16 double ribs (travertine-edged, lead-covered) + 3 tiers of lucarnes
    prof = dome_profile()
    m.merge(lathe(prof, 96, mat=LEAD))
    for k in range(NB):
        a = 2 * math.pi * (k + 0.5) / NB
        ca, sa = math.cos(a), math.sin(a)
        path = [(r * ca, r * sa, z) for (r, z) in prof]
        m.merge(sweep_normal([(-1.25, -0.1), (-1.25, 0.55), (-0.85, 0.75), (0.85, 0.75), (1.25, 0.55), (1.25, -0.1)], path, (0, 0), 'lead_rib'))
        m.merge(sweep_normal([(-1.5, -0.05), (-1.5, 0.25), (-1.25, 0.25), (-1.25, -0.05)], path, (0, 0), TRAV))
        m.merge(sweep_normal([(1.25, -0.05), (1.25, 0.25), (1.5, 0.25), (1.5, -0.05)], path, (0, 0), TRAV))
    def profile_at(z):
        for i in range(len(prof) - 1):
            (r0, z0), (r1, z1) = prof[i], prof[i + 1]
            if z0 <= z <= z1: return r0 + (r1 - r0) * (z - z0) / (z1 - z0), math.atan2(z1 - z0, r0 - r1)
        return prof[-1][0], 1.0
    for tier, (zt, size, kind) in enumerate(((86.5, 1.35, 'ped'), (95.5, 1.1, 'hood'), (104.0, 0.85, 'oculus'))):
        r, slope = profile_at(zt)
        for k in range(NB):
            a = 2 * math.pi * k / NB
            rad = np.array([math.cos(a), math.sin(a), 0.0]); tan = np.array([-math.sin(a), math.cos(a), 0.0])
            base = rad * (r - 0.4) + np.array([0, 0, zt])
            F = frame(tuple(base), tan, -rad, (0, 0, 1))
            g = Mesh()
            if kind == 'oculus':
                g.merge(lathe([(0, 0), (size * 0.75, 0), (size * 0.75, 0.45), (size * 0.5, 0.55), (0, 0.55)], 12, mat=TRAV).transformed(frame((0, 0.2, size), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
                g.merge(lathe([(0, 0), (size * 0.48, 0), (0, 0.02)], 10, mat='glass').transformed(frame((0, -0.4, size), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
            else:
                d = 0.9 + size * 0.35
                g.merge(box(-size * 0.75, -d, 0, size * 0.75, 0.6, size * 1.5, LEAD))
                g.merge(box(-size * 0.62, -d - 0.02, 0.0, size * 0.62, -d + 0.15, size * 1.45, TRAV))
                g.merge(box(-size * 0.42, -d - 0.04, size * 0.25, size * 0.42, -d + 0.0, size * 1.2, 'glass'))
                if kind == 'ped':
                    g.merge(pediment_tri(-size * 0.95, size * 0.95, size * 1.5, size * 0.45, d + 0.6, 0.25, 0.3, TRAV, y=-d) if k % 2 else
                            pediment_seg(-size * 0.95, size * 0.95, size * 1.5, size * 0.4, 0.25, 0.3, TRAV, y=-d))
                    g.merge(box(-size * 0.95, -d, size * 1.5, size * 0.95, 0.6, size * 1.55, LEAD))
                else:
                    g.merge(box(-size * 0.9, -d - 0.2, size * 1.5, size * 0.9, 0.6, size * 1.7, LEAD))
            m.merge(g.transformed(F))
    m.merge(lantern())
    return m


def lantern():
    """lantern proportions from the Ponte Sant'Angelo photo: balcony r 8.3, 8 pairs of columns (6 m),
    attic with candelabra, steep ribbed spire, gilt ball, cross (top = Z_CROSS)."""
    m = Mesh(); z = Z_LANT
    m.merge(lathe([(8.3, z - 0.6), (8.3, z + 0.8), (0, z + 0.8)], 64, mat=TRAV))
    for k in range(64):
        a = 2 * math.pi * k / 64
        m.merge(box(8.0 * math.cos(a) - 0.04, 8.0 * math.sin(a) - 0.04, z + 0.8, 8.0 * math.cos(a) + 0.04, 8.0 * math.sin(a) + 0.04, z + 1.9, 'iron'))
    m.merge(lathe([(8.04, z + 1.85), (8.04, z + 1.95), (7.96, z + 1.95), (7.96, z + 1.85)], 64, mat='iron'))
    m.merge(lathe([(5.6, z + 0.8), (5.6, z + 8.2), (0, z + 8.2)], 32, mat=TRAV))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        rad = np.array([math.cos(a), math.sin(a), 0.0]); tan = np.array([-math.sin(a), math.cos(a), 0.0])
        F = frame(tuple(rad * 5.6 + np.array([0, 0, z + 0.8])), tan, -rad, (0, 0, 1))
        g = Mesh()
        g.merge(box(-1.4, -1.0, 0, 1.4, 0.2, 6.0, TRAV))                    # spur wall behind the pair
        for s_ in (-1, 1): g.merge(column(0.75, 6.0, 'corinthian', TRAV).transformed(mat4((s_ * 0.7, -1.35, 0))))
        g.merge(box(-1.6, -1.9, 6.0, 1.6, 0.2, 7.4, TRAV))
        g.merge(straight(cornice_profile(0.6, 0.4), -1.6, 1.6, 6.8, -1.9, TRAV))
        g.merge(lathe([(0.55, 0), (0.62, 0.35), (0.35, 0.9), (0.45, 1.7), (0.3, 2.3), (0.12, 3.0), (0, 3.2)], 10, mat=TRAV, center=(0, -1.2, 11.2 - 0.8)))
        m.merge(g.transformed(F))
        b2 = 2 * math.pi * k / 8
        rad2 = np.array([math.cos(b2), math.sin(b2), 0.0]); tan2 = np.array([-math.sin(b2), math.cos(b2), 0.0])
        F2 = frame(tuple(rad2 * 5.62 + np.array([0, 0, z + 1.6])), tan2, -rad2, (0, 0, 1))
        m.merge(box(-1.0, -0.02, 0, 1.0, 0.0, 4.6, 'glass').transformed(F2))
        m.merge(arch_moulding(0, 3.6, 1.0, 0.25, 0.15, TRAV, y=-0.03).transformed(F2))
    m.merge(lathe([(6.4, z + 7.8), (6.4, z + 8.6), (6.0, z + 8.6), (6.0, z + 11.2), (6.5, z + 11.6), (6.5, z + 12.0), (0, z + 12.0)], 32, mat=TRAV))
    cone = [(5.6, z + 12.0), (4.4, z + 13.6), (3.2, z + 15.6), (2.1, z + 17.6), (1.1, z + 19.6), (0.55, z + 20.6), (0, z + 20.7)]
    m.merge(lathe(cone, 32, mat=LEAD))
    for k in range(16):
        a = 2 * math.pi * k / 16
        path = [(r * math.cos(a), r * math.sin(a), zz) for (r, zz) in cone[:-1]]
        m.merge(sweep_normal([(-0.16, 0), (-0.16, 0.22), (0.16, 0.22), (0.16, 0)], path, (0, 0), TRAV))
    m.merge(lathe([(0.65, z + 20.6), (0.8, z + 20.9), (0.45, z + 21.2), (0.5, z + 21.6), (0, z + 21.65)], 16, mat='bronze'))
    m.merge(lathe([(1.2 * math.sin(t), z + 21.6 + 1.2 - 1.2 * math.cos(t)) for t in np.linspace(0.05, math.pi, 12)], 24, mat='gold'))
    m.merge(box(-0.18, -0.18, z + 24.0, 0.18, 0.18, Z_CROSS, 'gold'))
    m.merge(box(-0.85, -0.16, Z_CROSS - 1.3, 0.85, 0.16, Z_CROSS - 0.95, 'gold'))
    return m


# ------------------------------------------------------------------- minor domes
def minor_dome(cu, cv, z0=ATTIC_Z1, scale=1.0):
    """Della Porta/Vignola cupola: square base, drum with paired columns, ribbed lead dome, lantern."""
    m = Mesh(); s = scale
    m.merge(prism([[(-10.5 * s, -10.5 * s), (10.5 * s, -10.5 * s), (10.5 * s, 10.5 * s), (-10.5 * s, 10.5 * s)]], z0 - 1, z0 + 4.0 * s, TRAV))
    R = 8.2 * s; zd0 = z0 + 4.0 * s; zd1 = zd0 + 8.5 * s
    m.merge(lathe([(R, zd0), (R, zd1), (0, zd1)], 32, mat=TRAV, smooth=False))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        rad = np.array([math.cos(a), math.sin(a), 0.0]); tan = np.array([-math.sin(a), math.cos(a), 0.0])
        F = frame(tuple(rad * R + np.array([0, 0, zd0])), tan, -rad, (0, 0, 1))
        g = Mesh()
        for sgn in (-1, 1): g.merge(column(0.8 * s, 7.4 * s, 'corinthian', TRAV).transformed(mat4((sgn * 0.75 * s, -0.7 * s, 0))))
        g.merge(box(-1.6 * s, -1.4 * s, 7.4 * s, 1.6 * s, 0.2, zd1 - zd0, TRAV))
        m.merge(g.transformed(F))
        b = 2 * math.pi * k / 8
        rad2 = np.array([math.cos(b), math.sin(b), 0.0]); tan2 = np.array([-math.sin(b), math.cos(b), 0.0])
        F2 = frame(tuple(rad2 * R + np.array([0, 0, zd0])), tan2, -rad2, (0, 0, 1))
        g2 = Mesh()
        g2.merge(box(-1.1 * s, -0.02, 2.0 * s, 1.1 * s, 0.0, 5.6 * s, 'glass'))
        g2.merge(arch_moulding(0, 4.5 * s, 1.1 * s, 0.35 * s, 0.2 * s, TRAV, y=0))
        m.merge(g2.transformed(F2))
    m.merge(lathe([(R + 0.6 * s, zd1), (R + 0.6 * s, zd1 + 0.9 * s), (0, zd1 + 0.9 * s)], 32, mat=TRAV))
    zb = zd1 + 0.9 * s
    # raised (ogival) profile like the main dome
    prof = [(R * (1 - (t / (math.pi / 2)) ** 1.6 * 0.88), zb + 10.5 * s * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)]
    m.merge(lathe(prof, 48, mat=LEAD))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        m.merge(sweep_normal([(-0.4 * s, 0), (-0.4 * s, 0.3 * s), (0.4 * s, 0.3 * s), (0.4 * s, 0)], [(r * math.cos(a), r * math.sin(a), z) for (r, z) in prof], (0, 0), LEAD))
    zl = prof[-1][1]; rl = prof[-1][0]
    m.merge(lathe([(rl * 1.1, zl), (rl * 1.1, zl + 3.8 * s), (rl * 1.35, zl + 4.2 * s), (rl * 0.8, zl + 5.6 * s), (0.25, zl + 7.4 * s), (0, zl + 7.5 * s)], 16, mat=TRAV))
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        m.merge(box(rl * 1.12 * math.cos(a) - 0.25, rl * 1.12 * math.sin(a) - 0.25, zl, rl * 1.12 * math.cos(a) + 0.25, rl * 1.12 * math.sin(a) + 0.25, zl + 3.8 * s, TRAV))
    m.merge(lathe([(0.5 * s * math.sin(t), zl + 7.4 * s + 0.5 * s - 0.5 * s * math.cos(t)) for t in np.linspace(0.05, math.pi, 8)], 12, mat='bronze'))
    m.merge(box(-0.1, -0.1, zl + 8.3 * s, 0.1, 0.1, zl + 10.0 * s, 'iron'))
    m.merge(box(-0.55 * s, -0.08, zl + 9.2 * s, 0.55 * s, 0.08, zl + 9.45 * s, 'iron'))
    return m.transformed(mat4((cu, cv, 0)))


def chapel_dome(cu, cv, ru=5.5, rv=4.0, z0=ATTIC_Z1):
    """Maderno's small oval chapel domes along the nave."""
    m = Mesh()
    prof = [(1.0 * math.cos(t), 4.5 * math.sin(t)) for t in np.linspace(0, math.pi / 2 * 0.85, 7)]
    d = lathe(prof, 24, mat=LEAD)
    V = np.array(d.V); V[:, 0] *= ru; V[:, 1] *= rv; d.V = V.tolist()
    m.merge(lathe([(1.08, 0), (1.08, 2.0), (0, 2.0)], 24, mat=TRAV).transformed(mat4((0, 0, 0), s=(ru, rv, 1))))
    m.merge(d.transformed(mat4((0, 0, 2.0))))
    zl = 2.0 + prof[-1][1]
    m.merge(lathe([(1.0, zl), (0.9, zl + 2.0), (1.2, zl + 2.3), (0.2, zl + 3.2), (0, zl + 3.3)], 12, mat=TRAV))
    return m.transformed(mat4((cu, cv, z0 - 1.0)))


# ------------------------------------------------------------------- facade (Maderno)
def facade():
    """facade block in the arch frame: x along the facade (south -> north), y into the building, z up.
    Returns (mesh_in_facade_frame)."""
    m = Mesh()
    H_COL = ORD_H; D = 2.65
    cols = [5.5, 12.0, 17.0, 27.5]
    colY = -1.9
    # block behind: from the facade wall to the nave front (u 117)
    depth = U_FAC - 117.0
    m.merge(prism([[(-FAC_HALF, 0), (FAC_HALF, 0), (FAC_HALF, depth), (-FAC_HALF, depth)]], -4, ATTIC_Z1, TRAV, top=True))
    # (prism faces point outward; its front face at y=0 is the wall the columns stand before)
    # central frontispiece projects 1.2 m between |x| < 14.6
    m.merge(box(-14.6, -1.2, 0, 14.6, 0, ENT_Z0, TRAV))
    # openings: 5 doors at ground (C centre & sides, D minor) + loggia windows — drawn as recessed dark panels
    def recess(x0, x1, z0, z1, kind='rect', y0=-1.21):
        g = Mesh()
        w = x1 - x0; h = z1 - z0
        outline_ = opening_shape(w, h, kind, x=x0, y=z0)
        g.merge(fix_orient(cap([outline_], 0, 'glass', True, frame((0, y0 - 0.0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
        return g
    for xc, w, h, kind in ((0, 5.0, 11.5, 'rect'), (-22.25, 4.6, 10.5, 'rect'), (22.25, 4.6, 10.5, 'rect'), (-8.75, 3.0, 7.5, 'arch'), (8.75, 3.0, 7.5, 'arch')):
        yy = -1.21 if abs(xc) < 14.6 else -0.01
        m.merge(recess(xc - w / 2, xc + w / 2, 0.3, 0.3 + h, kind, yy))
        m.merge(aedicule(xc, 0.3, w, h, TRAV, 'flat' if kind == 'rect' else 'seg', y=yy, window=False, frame_w=0.7, proj=0.4))
    # upper level: loggia of blessings (centre) + balcony windows
    for xc, w in ((0, 4.6), (-8.75, 3.2), (8.75, 3.2), (-22.25, 4.2), (22.25, 4.2), (-31.2, 3.4), (31.2, 3.4)):
        yy = -1.21 if abs(xc) < 14.6 else -0.01
        m.merge(recess(xc - w / 2, xc + w / 2, 14.6, 14.6 + w * 1.9, 'arch', yy))
        m.merge(arch_moulding(xc, 14.6 + w * 1.9 - w / 2, w / 2, 0.55, 0.35, TRAV, y=yy))
        m.merge(pediment_seg(xc - w / 2 - 0.9, xc + w / 2 + 0.9, 14.6 + w * 1.9 + 0.6, 0.8, 0.45, 0.55, TRAV, y=yy))
        m.merge(balustrade(xc - w / 2 - 0.6, xc + w / 2 + 0.6, 13.4, 1.2, 0.6, TRAV, y=yy - 0.6))
        m.merge(box(xc - w / 2 - 0.8, yy - 0.75, 13.0, xc + w / 2 + 0.8, yy, 13.4, TRAV))
    # niches with statues (outer bays) and the end arches (passages) with windows above
    for s in (-1, 1):
        m.merge(niche(2.6, 6.0, 1.0, TRAV).transformed(mat4((s * 31.2, 0.0, 3.0))))
        xa = s * 45.0
        m.merge(recess(xa - 4.5, xa + 4.5, 0.0, 13.5, 'arch', -0.01))
        m.merge(arch_moulding(xa, 13.5 - 4.5, 4.5, 0.8, 0.4, TRAV, y=-0.01))
        m.merge(recess(xa - 1.7, xa + 1.7, 16.5, 22.5, 'rect', -0.01))
        m.merge(aedicule(xa, 16.5, 3.4, 6.0, TRAV, 'tri', y=-0.01, window=False))
    # giant columns (free-standing) and pilasters
    for s in (-1, 1):
        for x in cols:
            m.merge(column(D, H_COL, 'corinthian', TRAV).transformed(mat4((s * x, colY - (1.2 if x < 14.6 else 0), 0))))
        for x in (35.0, 39.5, 50.5, 55.9):
            m.merge(pilaster(PIL_W, H_COL, PIL_D, 'corinthian', TRAV).transformed(mat4((s * x, 0, 0))))
        for x in cols[2:]:
            m.merge(pilaster(PIL_W, H_COL, PIL_D, 'corinthian', TRAV).transformed(mat4((s * x, 0, 0))))
    # entablature: straight across the frontispiece, broken forward over the outer columns
    proj = 1.9
    ress = [(-14.6, 14.6, 1.2 + 2.0)]
    for s in (-1, 1):
        for x in cols[2:]:
            ress.append((s * x - D / 2 - 0.2, s * x + D / 2 + 0.2, 2.0 + 1.0))
    ress = sorted([(min(a, b), max(a, b), d) for (a, b, d) in ress])
    m.merge(broken_entablature([-FAC_HALF, FAC_HALF], ENT_Z0, ENT_Z1 - ENT_Z0, proj, TRAV, y=0.0, ressauts=ress))
    # pediment over the frontispiece
    m.merge(pediment_tri(-15.2, 15.2, ENT_Z1, 6.8, 3.0, 1.6, 2.0, TRAV, y=-3.2))
    # papal arms in the tympanum (simple cartouche)
    m.merge(lathe([(0, 0), (1.3, 0), (1.5, 0.3), (1.2, 0.5), (0, 0.5)], 16, mat=TRAV).transformed(frame((0, -3.0, ENT_Z1 + 2.8), (1, 0, 0), (0, 0, 1.4), (0, -1, 0))))
    # attic: windows, pilaster strips, cornice, balustrade with 13 statues on pedestals
    xs_attic = [-55.9, -50.5, -39.5, -35.0, -27.5, -17.0, -12.0, -5.5, 5.5, 12.0, 17.0, 27.5, 35.0, 39.5, 50.5, 55.9]
    for x in xs_attic:
        m.merge(box(x - 1.3, -0.45, ENT_Z1, x + 1.3, 0, ATTIC_Z1 - 1.6, TRAV))
    for i in range(len(xs_attic) - 1):
        a, b = xs_attic[i] + 1.3, xs_attic[i + 1] - 1.3
        if b - a < 3.0: continue
        xc = (a + b) / 2
        if abs(xc) < 14: continue      # pediment covers the centre
        m.merge(recess(xc - 1.4, xc + 1.4, ENT_Z1 + 3.2, ENT_Z1 + 6.4, 'rect', -0.01))
        m.merge(aedicule(xc, ENT_Z1 + 3.2, 2.8, 3.2, TRAV, 'tri' if (i % 3 == 1) else 'flat', y=-0.01, window=False))
    m.merge(straight(cornice_profile(1.6, 1.0), -FAC_HALF, FAC_HALF, ATTIC_Z1 - 1.6, 0, TRAV))
    m.merge(balustrade(-FAC_HALF, FAC_HALF, ATTIC_Z1, 1.6, 0.8, TRAV, y=0.1, pier_every=None))
    return m


def facade_statue_spots():
    """13 statue positions on the facade balustrade (facade frame x), Christ in the centre."""
    xs = [-27.5, -17.0, -12.0, -5.5, 5.5, 12.0, 17.0, 27.5, -35.0, 35.0, -39.5, 39.5]
    return [0.0] + xs


def build():
    W = Mesh()
    L = Mesh()
    L.merge(body())
    L.merge(roofs())
    L.merge(drum_dome())
    for (cu, cv) in ((36.5, 37.5), (-38.0, 38.0), (36.5, -37.5), (-38.0, -38.0)):
        L.merge(minor_dome(cu, cv))
    for cu in (88.0, 100.0, 111.0):
        for sv in (-1, 1):
            L.merge(chapel_dome(cu, sv * 31.0))
    Ff = frame((U_FAC, 0, 0), (0, 1, 0), (-1, 0, 0), (0, 0, 1))
    L.merge(facade().transformed(Ff))
    M = site.basilica_matrix()
    W.merge(L.transformed(M))
    return W


if __name__ == '__main__':
    import bpy
    from vb import bl
    out = sys.argv[sys.argv.index('--') + 1]
    bl.clear_scene()
    m = build()
    print('basilica', m.count())
    bl.to_object(m, 'basilica')
    bl.to_object(box(-700, -500, -0.05, 400, 500, 0, 'sampietrini'), 'ground')
    bl.setup_world()
    views = {'bridge': ((762, -40, 4), (-250, -6, 52), 167), 'dome': ((-235, -110, 105), (-321, -8, 98), 35), 'air': ((60, -300, 200), (-260, 0, 40), 30)}
    import json as _j, os as _o
    cf = '/tmp/claude-1000/-home-kazu-work-demos/1f48e580-beae-4176-8eee-fdee54a01026/scratchpad/camfit.json'
    if _o.path.exists(cf):
        c = _j.load(open(cf)); views['match'] = (tuple(c['cam']), tuple(c['target']), c['lens'])
    only = [a for a in sys.argv if a.startswith('view=')]
    if only: views = {k: v for k, v in views.items() if k in only[0][5:].split(',')}
    for k, (p, t, lens) in views.items():
        bl.camera(p, t, lens)
        bl.render(out + f'-{k}.jpg', 1600 if k == 'match' else 1400, 1067 if k == 'match' else 800, 32)
