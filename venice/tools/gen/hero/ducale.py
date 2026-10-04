"""Palazzo Ducale (south front on the Molo, west front on the Piazzetta), the Porta della Carta, the Ponte della
Paglia and the Ponte dei Sospiri.

Facades from the OSM footprint corners: SW (77.3, -62.3), SE (148.4, -42.4), NW (56.7, 12.0).
Elevation (above the pavement): Gothic ground arcade (short columns, pointed arches) to 7.3 m; first-floor loggia
with twice as many ogee arches and a band of quatrefoils to 12.4 m; the upper wall in a lozenge pattern of white
Istrian and pink Verona stone with pointed windows and the balcony window, cornice at 23 m and the white merlons."""
import math
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import facade_frame, place, translate, compose
from .basilica import statue, crest_mesh, tabernacle

STONE = 'istrian'
SW = np.array([77.3, -62.3]); SE = np.array([148.4, -42.4]); NW = np.array([56.7, 12.0])
Z_ARC = 7.3; Z_LOG = 12.4; Z_COR = 23.0

def quad(m, pts, want, mat=STONE):
    P = np.array(pts, float); n = np.cross(P[1] - P[0], P[2] - P[0])
    m.poly(pts if np.dot(n, want) >= 0 else pts[::-1], mat)

def pointed(x0, w, zs, f=1.0, n=8, z0=0.0):
    """two-centred pointed arch opening (bottom-left x0, width w, springing zs); f = radius / span."""
    half = w / 2; cx = x0 + half; r = w * f; c = r - half
    amax = math.acos(c / r)
    right = [(cx - c + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, amax, n + 1)]
    left = [(2 * cx - x, z) for (x, z) in reversed(right[:-1])]
    return [(x0, z0), (x0 + w, z0)] + right + left

def ogee(x0, w, zs, rise, n=8, z0=0.0):
    """inflected (ogee) arch: convex near the springers, concave to a sharp apex."""
    half = w / 2; cx = x0 + half
    def bez(p0, p1, p2, p3, t):
        s = 1 - t
        return (s ** 3 * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t ** 3 * p3[0], s ** 3 * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t ** 3 * p3[1])
    P0 = (cx + half, zs); P1 = (cx + half, zs + 0.62 * rise); P2 = (cx + 0.04 * w, zs + 0.40 * rise); P3 = (cx, zs + rise)
    right = [bez(P0, P1, P2, P3, t) for t in np.linspace(0, 1, n + 1)]
    left = [(2 * cx - x, z) for (x, z) in reversed(right[:-1])]
    return [(x0, z0), (x0 + w, z0)] + right + left

def grow(outline, g):
    """offset a closed outline outward by g (polygon buffer, mitred)."""
    p = Polygon(outline).buffer(g, join_style=2, mitre_limit=3.0)
    return list(p.exterior.coords)[:-1]

def xs(pts, y0, y1, mat=STONE):
    """extrude a closed (x, z) section from y0 to y1 with outward-facing sides."""
    P = list(pts)
    if G.signed_area(P) > 0: P = P[::-1]
    return G.extrude_xsection(P, y1 - y0, mat, M=G.mat4((0, y0, 0)))

def frame_ring(outline, g, y, mat=STONE, depth=0.12):
    """a projecting stone frame around an opening outline on the wall face y (facing -y)."""
    m = G.Mesh()
    outer = grow(outline, g)
    F = G.frame((0, y - depth, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    m.merge(A.fix_orient(G.cap([outer, outline], 0, mat, True, F), (0, -1, 0)))
    # outer edge band (faces outward)
    L = G.ccw(outer); n = len(L)
    for i in range(n):
        a, b = L[i], L[(i + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]; ln = math.hypot(dx, dz)
        if ln < 1e-6: continue
        quad(m, [(a[0], y, a[1]), (b[0], y, b[1]), (b[0], y - depth, b[1]), (a[0], y - depth, a[1])], (dz / ln, 0, -dx / ln), mat)
    return m

def panel(outline, y, mat):
    return A.fix_orient(G.cap([outline], 0, mat, True, G.frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0))

# ------------------------------------------------------------------ bays
def arcade_bay(W):
    """ground storey bay: column at x=0, pointed arch, spandrel wall to the loggia floor, portico behind."""
    m = G.Mesh()
    d = 0.78; aw = W - 0.95; zs = 3.85
    op = pointed(W / 2 - aw / 2, aw, zs, f=0.85, n=8)
    m.merge(G.wall(W, Z_ARC, 0.7, STONE, openings=[op], back=True, sides=False))
    m.merge(A.column(d, zs + 0.1, order='corinthian', mat=STONE, seg=10, base=False, detail=0.1).transformed(G.mat4((0, -0.05, 0))))
    m.merge(_arch_band(op, 0.24, 0.0, 0.1))
    # portico: floor, beamed ceiling, back wall with doors
    D = 5.0
    m.merge(G.box(0, 0.7, -0.05, W, D, 0.0, 'portico_floor', faces=('+z',)))
    m.merge(G.box(0, 0.7, Z_ARC - 0.75, W, D, Z_ARC - 0.6, 'wood_raw', faces=('-z',)))
    for x in (W * 0.25, W * 0.75):
        m.merge(G.box(x - 0.12, 0.7, Z_ARC - 1.0, x + 0.12, D, Z_ARC - 0.75, 'wood_raw', faces=('-z', '-x', '+x')))
    door = [(W / 2 - 0.8, 0.0), (W / 2 + 0.8, 0.0), (W / 2 + 0.8, 3.0), (W / 2 - 0.8, 3.0)]
    m.merge(G.wall(W, Z_ARC - 0.6, 0.3, 'portico_wall', openings=[door], back=False, sides=False).transformed(G.mat4((0, D, 0))))
    m.merge(panel(door, D + 0.15, 'shop_wood'))
    return m

def _arch_band(op, g, y, proj):
    """projecting band around the curved part of an arch opening (from springer to springer)."""
    m = G.Mesh()
    inner = op[2:]                          # springer-right ... apex ... springer-left
    out = []
    cx = (op[0][0] + op[1][0]) / 2
    for (x, z) in inner:
        # push outward from the arch's centroid region
        dx, dz = x - cx, z - inner[0][1] + 0.3
        ln = math.hypot(dx, dz) or 1
        out.append((x + dx / ln * g, z + dz / ln * g))
    for i in range(len(inner) - 1):
        a, b, c, d = inner[i], inner[i + 1], out[i + 1], out[i]
        quad(m, [(a[0], y - proj, a[1]), (b[0], y - proj, b[1]), (c[0], y - proj, c[1]), (d[0], y - proj, d[1])], (0, -1, 0))
        quad(m, [(d[0], y, d[1]), (c[0], y, c[1]), (c[0], y - proj, c[1]), (d[0], y - proj, d[1])], (d[0] - cx, 0, d[1] - inner[0][1]))
    return m

def loggia_bay(W2):
    """first-floor loggia bay: slender column at x=0, ogee arch, quatrefoil roundel over the column."""
    m = G.Mesh()
    zf = Z_ARC; zs = zf + 2.75; aw = W2 - 0.42
    op = ogee(W2 / 2 - aw / 2, aw, zs - zf, 1.05, n=8)
    # wall from the loggia floor to the top of the quatrefoil band, with the arch opening and a roundel
    rz = Z_LOG - zf - 0.78; rr = 0.5
    ring = G.opening_shape(2 * rr, 2 * rr, 'circle', n=10, x=-rr, y=rz - rr)
    ring2 = G.opening_shape(2 * rr, 2 * rr, 'circle', n=10, x=W2 - rr, y=rz - rr)
    wl = G.wall(W2, Z_LOG - zf, 0.45, STONE, openings=[op], back=True, sides=False)
    m.merge(wl.transformed(G.mat4((0, 0, zf))))
    m.merge(A.column(0.34, zs - zf, order='corinthian', mat=STONE, seg=8, base=True, detail=0.1).transformed(G.mat4((0, -0.02, zf))))
    m.merge(_arch_band([(x, z + zf) for (x, z) in op], 0.12, 0.0, 0.07))
    # quatrefoil roundel (stone disc with four lobes cut through, dark behind) centred over the column
    disc = G.opening_shape(1.0, 1.0, 'circle', n=12, x=-0.5, y=zf + rz - 0.5)
    lobes = [G.opening_shape(0.34, 0.34, 'circle', n=6, x=-0.17 + dx, y=zf + rz - 0.17 + dz) for (dx, dz) in ((0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2))]
    m.merge(A.fix_orient(G.cap([disc] + lobes, 0, STONE, True, G.frame((0, -0.06, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    for lb in lobes: m.merge(panel(lb, 0.1, 'dark'))
    # balustrade between the columns (pierced: small balusters)
    m.merge(A.balustrade(0.2, W2 - 0.2, zf, 0.95, 0.2, STONE, y=-0.08, bal_seg=6))
    # loggia floor, ceiling, back wall
    D = 4.5
    m.merge(G.box(0, 0.45, zf - 0.05, W2, D, zf, 'portico_floor', faces=('+z',)))
    m.merge(G.box(0, 0.45, Z_LOG - 0.3, W2, D, Z_LOG - 0.15, 'wood_raw', faces=('-z',)))
    m.merge(G.wall(W2, Z_LOG - zf - 0.3, 0.3, 'portico_wall', back=False, sides=False).transformed(G.mat4((0, D, zf))))
    return m

def upper_wall(L, windows, balcony_x=None):
    """lozenge-pattern wall from Z_LOG to Z_COR with pointed windows (x positions), cornice and merlons."""
    m = G.Mesh()
    H = Z_COR - Z_LOG
    ops = []
    for (x, zs, w, h) in windows:
        ops.append([(px, pz) for (px, pz) in pointed(x - w / 2, w, h - w * 0.75, f=0.8, n=8, z0=0.0)])
        ops[-1] = [(px, pz + zs - Z_LOG) for (px, pz) in ops[-1]]
    wl = G.wall(L, H, 0.6, 'ducale_wall', openings=ops, back=False, sides=False, reveal_mat=STONE)
    m.merge(wl.transformed(G.mat4((0, 0, Z_LOG))))
    for k, (x, zs, w, h) in enumerate(windows):
        o = [(px, pz + Z_LOG) for (px, pz) in ops[k]]
        m.merge(frame_ring(o, 0.22, 0.0))
        m.merge(panel(o, 0.45, 'glass'))
        # mullion + a small balcony with balusters
        m.merge(G.box(x - 0.06, 0.25, zs, x + 0.06, 0.4, zs + h - w * 0.75, STONE))
        m.merge(G.box(x - w / 2 - 0.35, -0.75, zs - 0.18, x + w / 2 + 0.35, 0.0, zs, STONE))
        m.merge(A.balustrade(x - w / 2 - 0.3, x + w / 2 + 0.3, zs, 0.9, 0.16, STONE, y=-0.72, bal_seg=6))
    # small round windows high up
    for (x, zs, w, h) in windows:
        oc = G.opening_shape(0.9, 0.9, 'circle', n=8, x=x - 0.45, y=Z_COR - 2.6)
        m.merge(frame_ring(oc, 0.12, 0.0)); m.merge(panel(oc, -0.01, 'dark'))
    # cornice + merlons
    m.merge(A.straight(A.cornice_profile(0.7, 0.55), -0.4, L + 0.4, Z_COR - 0.7, 0.0, STONE))
    merlon = [(-0.45, 0), (0.45, 0), (0.45, 0.62), (0.28, 0.78), (0.34, 1.08), (0.12, 1.24), (0.0, 1.78), (-0.12, 1.24), (-0.34, 1.08), (-0.28, 0.78), (-0.45, 0.62)]
    n = int(L / 1.62)
    for k in range(n + 1):
        x = L * k / n
        m.merge(xs([(x + px, Z_COR + pz) for (px, pz) in merlon], -0.05, 0.25))
    # balcony window (1404): pinnacled frame and a statue of Justice above
    if balcony_x is not None:
        x = balcony_x; w = 2.9; zs = 14.0; h = 6.6
        for sx in (-1, 1):
            m.merge(G.box(x + sx * (w / 2 + 0.7) - 0.35, -0.9, zs - 1.2, x + sx * (w / 2 + 0.7) + 0.35, 0.0, zs + h + 1.5, STONE))
            m.merge(G.lathe([(0.42, 0), (0.3, 0.8), (0.0, 2.6)], 4, mat=STONE, center=(x + sx * (w / 2 + 0.7), -0.45, zs + h + 1.5)))
            m.merge(statue(1.7).transformed(G.mat4((x + sx * (w / 2 + 0.7), -1.1, zs + 1.0))))
        m.merge(crest_mesh(x, zs + h - 0.6, w / 2 + 0.6, 2.4, y=-0.3))
        m.merge(statue(2.2).transformed(G.mat4((x, -0.6, zs + h + 2.0))))
        m.merge(G.box(x - w / 2 - 1.2, -1.2, zs - 0.4, x + w / 2 + 1.2, 0.0, zs, STONE))
        m.merge(A.balustrade(x - w / 2 - 1.1, x + w / 2 + 1.1, zs, 1.0, 0.18, STONE, y=-1.15, bal_seg=6))
    return m

def facade(a, b, n_out, nbays, windows, balcony=None, corner_pinnacles=(True, True)):
    M, L, flipped = facade_frame(a, b, n_out)
    W = L / nbays; W2 = W / 2
    m = G.Mesh()
    bay = arcade_bay(W); lb = loggia_bay(W2)
    for i in range(nbays): m.merge(bay.transformed(translate(i * W)))
    m.merge(A.column(0.78, 3.95, order='corinthian', mat=STONE, seg=10, base=False, detail=0.1).transformed(G.mat4((L, -0.05, 0))))
    for i in range(2 * nbays): m.merge(lb.transformed(translate(i * W2)))
    m.merge(A.column(0.34, 2.75, order='corinthian', mat=STONE, seg=8, detail=0.1).transformed(G.mat4((L, -0.02, Z_ARC))))
    # string course between loggia and upper wall
    m.merge(A.straight(A.string_course(0.3, 0.18), 0, L, Z_LOG - 0.3, 0.0, STONE))
    m.merge(upper_wall(L, [(f * L, zs, w, h) for (f, zs, w, h) in windows], balcony * L if balcony is not None else None))
    # corner pinnacles (gugliette) and corner sculpture groups at the loggia level
    for k, x in enumerate((0.0, L)):
        if not corner_pinnacles[k]: continue
        m.merge(G.box(x - 0.55, -0.55, Z_COR, x + 0.55, 0.55, Z_COR + 2.2, STONE))
        m.merge(G.lathe([(0.62, 0), (0.45, 1.0), (0.0, 3.4)], 8, mat=STONE, center=(x, 0.0, Z_COR + 2.2)))
        m.merge(statue(2.1).transformed(G.mat4((x, -0.6, Z_ARC + 0.2))))
    return M, flipped, m

def porta_della_carta():
    """the gate between the palace and the basilica (Bartolomeo Bon, 1438-42), kit frame, 9.4 m wide."""
    m = G.Mesh(); W = 9.4
    op = pointed(W / 2 - 2.1, 4.2, 5.4, f=0.75, n=10)
    m.merge(G.wall(W, 12.5, 1.2, STONE, openings=[op], back=True, sides=True, top=True))
    m.merge(_arch_band(op, 0.35, 0.0, 0.18))
    for x in (0.8, W - 0.8):
        m.merge(G.box(x - 0.8, -0.6, 0, x + 0.8, 0.0, 13.0, STONE))
        for z in (3.0, 7.4):
            m.merge(A.niche(0.9, 2.2, 0.35, STONE).transformed(G.mat4((x, -0.62, z))))
            m.merge(statue(1.8).transformed(G.mat4((x, -0.75, z + 0.1))))
        m.merge(G.lathe([(0.8, 0), (0.55, 1.0), (0.0, 4.2)], 4, mat=STONE, center=(x, -0.3, 13.0)))
    # Doge Foscari before the lion, tracery window, crest and Justice
    m.merge(G.box(W / 2 - 2.0, -0.35, 7.6, W / 2 + 2.0, 0.0, 9.4, 'relief'))
    win = pointed(W / 2 - 1.8, 3.6, 10.6, f=0.8, n=8, z0=9.6)
    m.merge(panel(win, 0.3, 'glass_lattice')); m.merge(frame_ring(win, 0.2, 0.0))
    m.merge(crest_mesh(W / 2, 12.6, 2.6, 3.0, y=-0.2))
    m.merge(statue(2.3).transformed(G.mat4((W / 2, -0.4, 16.2))))
    return m

# ------------------------------------------------------------------ Ponte dei Sospiri
SOS_A = np.array([139.0, -1.6]); SOS_B = np.array([148.1, 0.8])
def sospiri():
    """enclosed bridge (Antonio Contin, 1600-03), local x along the bridge (palace -> prisons), y across."""
    m = G.Mesh()
    L = float(np.linalg.norm(SOS_B - SOS_A)); hw = 2.1
    zsp, zcr = 5.0, 6.7                                   # arch springing at the walls, crown soffit
    R = ((L / 2) ** 2 + (zcr - zsp) ** 2) / (2 * (zcr - zsp)); zc = zcr - R
    za = lambda x: zc + math.sqrt(max(0.0, R * R - (x - L / 2) ** 2))
    xa = np.linspace(0, L, 17)
    for x0, x1 in zip(xa[:-1], xa[1:]):
        quad(m, [(x0, -hw, za(x0)), (x1, -hw, za(x1)), (x1, hw, za(x1)), (x0, hw, za(x0))], (L / 2 - (x0 + x1) / 2, 0, zc - za((x0 + x1) / 2)))
    ztop = 11.2
    for side in (-1, 1):
        y = side * hw
        out = [(0, ztop)] + [(0, zsp)] + [(x, za(x)) for x in xa[1:-1]] + [(L, zsp), (L, ztop)]
        quad_cap = G.cap([out], 0, STONE, True, G.frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, side, 0)))
        m.merge(A.fix_orient(quad_cap, (0, side, 0)))
        # rusticated pilasters at the ends, archivolt with mascarons, windows with stone grilles
        for x in (0.45, L - 0.45):
            m.merge(G.box(x - 0.45, y - (0.25 if side < 0 else 0), zsp - 0.3, x + 0.45, y + (0.25 if side > 0 else 0), ztop, STONE))
        phi = math.asin(min(1.0, (L / 2) / R))
        for k in range(9):
            th = math.pi / 2 + phi - 2 * phi * (k + 0.5) / 9
            x = L / 2 + (R + 0.25) * math.cos(th); z = zc + (R + 0.25) * math.sin(th)
            m.merge(G.box(x - 0.24, y - (0.18 if side < 0 else 0), z - 0.28, x + 0.24, y + (0.18 if side > 0 else 0), z + 0.32, 'relief' if k == 4 else STONE))
        for xw in (L * 0.33, L * 0.67):
            w0, w1, z0, z1 = xw - 0.5, xw + 0.5, 8.3, 9.5
            m.merge(G.box(w0 - 0.18, y - (0.12 if side < 0 else 0), z0 - 0.18, w1 + 0.18, y + (0.12 if side > 0 else 0), z1 + 0.18, STONE))
            quad(m, [(w0, y + side * 0.02, z0), (w1, y + side * 0.02, z0), (w1, y + side * 0.02, z1), (w0, y + side * 0.02, z1)], (0, side, 0), 'dark')
            for k in range(1, 5):
                xx = w0 + k * 0.2
                m.merge(G.box(xx - 0.02, y + side * 0.05 - 0.02, z0, xx + 0.02, y + side * 0.05 + 0.02, z1, 'metal'))
            for k in range(1, 6):
                zz = z0 + k * 0.2
                m.merge(G.box(w0, y + side * 0.05 - 0.02, zz - 0.02, w1, y + side * 0.05 + 0.02, zz + 0.02, 'metal'))
        # frieze + cornice, curved crowning with volutes and the arms in the middle
        m.merge(G.box(-0.2, y - (0.3 if side < 0 else -0.0), ztop - 0.5, L + 0.2, y + (0.3 if side > 0 else 0.0), ztop, STONE))
        crown = [(0.3, ztop)] + [(L / 2 + (L / 2 - 0.3) * math.cos(a), ztop + 1.5 * math.sin(a)) for a in np.linspace(0, math.pi, 13)][::-1] + [(L - 0.3, ztop)]
        m.merge(xs(crown, y - 0.35 if side < 0 else y, y if side < 0 else y + 0.35))
        m.merge(G.box(L / 2 - 0.55, y - (0.45 if side < 0 else -0.1), ztop + 0.4, L / 2 + 0.55, y + (0.45 if side > 0 else -0.1), ztop + 1.7, 'relief'))
        for x in (0.6, L - 0.6):
            m.merge(G.lathe([(0.0, 0), (0.32, 0.1), (0.36, 0.35), (0.2, 0.55), (0.0, 0.6)], 8, mat=STONE, center=(x, y, ztop + 0.05)))
    # roof (lead) over the passage
    m.merge(G.box(0, -hw, ztop - 0.02, L, hw, ztop + 0.6, 'lead', faces=('+z',)))
    return m, L

def sospiri_frame():
    d = (SOS_B - SOS_A) / np.linalg.norm(SOS_B - SOS_A); n = np.array([-d[1], d[0]])
    M = np.eye(4); M[:3, 0] = (d[0], d[1], 0); M[:3, 1] = (n[0], n[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (SOS_A[0], SOS_A[1], 0)
    return M

# ------------------------------------------------------------------ Ponte della Paglia
PAG_D = np.array([0.962, 0.272]); PAG_N = np.array([-PAG_D[1], PAG_D[0]]); PAG_C = np.array([154.4, -45.8])
PAG = dict(s0=-17.5, s1=16.8, a0=-5.6, a1=6.2, t0=-5.2, t1=4.6, top=2.75, land=2.0)

def paglia_z(s):
    p = PAG; c = (p['a0'] + p['a1']) / 2
    a = abs(s - c); half = (p['s1'] - p['s0']) / 2
    if a <= p['land']: return p['top']
    e = half
    if a >= e: return GROUND_Z
    return GROUND_Z + (p['top'] - GROUND_Z) * (e - a) / (e - p['land'])

def paglia():
    p = PAG; m = G.Mesh()
    c = (p['a0'] + p['a1']) / 2; span = p['a1'] - p['a0']
    zsp, zcr = 0.4, 2.1
    R = ((span / 2) ** 2 + (zcr - zsp) ** 2) / (2 * (zcr - zsp)); zc = zcr - R
    za = lambda s: zc + math.sqrt(max(0.0, R * R - (s - c) ** 2))
    ss = np.linspace(p['a0'], p['a1'], 17)
    for s0, s1 in zip(ss[:-1], ss[1:]):
        quad(m, [(s0, p['t0'], za(s0)), (s1, p['t0'], za(s1)), (s1, p['t1'], za(s1)), (s0, p['t1'], za(s0))], (c - (s0 + s1) / 2, 0, zc - za((s0 + s1) / 2)))
    # side faces with archivolt, deck steps (stone), balustrades
    sv = np.linspace(p['s0'], p['s1'], 40)
    for t, side in ((p['t0'], -1), (p['t1'], 1)):
        top = [(s, paglia_z(s) - 0.02) for s in sv]
        bottom = [(p['s0'], GROUND_Z - 0.3), (p['a0'], GROUND_Z - 0.3), (p['a0'], zsp)] + [(s, za(s)) for s in ss[1:-1]] + [(p['a1'], zsp), (p['a1'], GROUND_Z - 0.3), (p['s1'], GROUND_Z - 0.3)]
        m.merge(A.fix_orient(G.cap([bottom + top[::-1]], 0, STONE, True, G.frame((0, t, 0), (1, 0, 0), (0, 0, 1), (0, side, 0))), (0, side, 0)))
        for s0, s1 in zip(sv[:-1], sv[1:]):
            z0, z1 = paglia_z(s0), paglia_z(s1)
            # rail on balusters
            ty = t - side * 0.15
            m.merge(_slab(s0, s1, z0 + 0.92, z1 + 0.92, ty - 0.15, ty + 0.15, 0.14))
            m.merge(_slab(s0, s1, z0 - 0.02, z1 - 0.02, ty - 0.13, ty + 0.13, 0.12))
            sm = (s0 + s1) / 2
            m.merge(A.baluster(0.8, 0.07, STONE, seg=6).transformed(G.mat4((sm, ty, paglia_z(sm) + 0.1))))
        for s in np.linspace(p['s0'], p['s1'], 9):
            ty = t - side * 0.15
            m.merge(G.box(s - 0.2, ty - 0.18, paglia_z(s) - 0.02, s + 0.2, ty + 0.18, paglia_z(s) + 1.12, STONE))
    # walking surface: stepped stone treads
    n = 10; e = (p['s1'] - p['s0']) / 2
    for sgn in (-1, 1):
        for k in range(n):
            a0 = e - k * (e - p['land']) / n; a1 = e - (k + 1) * (e - p['land']) / n
            s_a, s_b = c + sgn * a0, c + sgn * a1
            z = GROUND_Z + (p['top'] - GROUND_Z) * (k + 1) / n
            lo, hi = min(s_a, s_b), max(s_a, s_b)
            m.merge(G.box(lo, p['t0'] + 0.3, z - 0.25, hi, p['t1'] - 0.3, z, 'bridge_stone', faces=('+z', '+x' if sgn > 0 else '-x')))
    m.merge(G.box(c - p['land'], p['t0'] + 0.3, p['top'] - 0.25, c + p['land'], p['t1'] - 0.3, p['top'], 'bridge_stone', faces=('+z',)))
    return m

def _slab(s0, s1, za, zb, y0, y1, h, mat=STONE):
    m = G.Mesh()
    P = [(s0, y0, za), (s1, y0, zb), (s1, y1, zb), (s0, y1, za), (s0, y0, za + h), (s1, y0, zb + h), (s1, y1, zb + h), (s0, y1, za + h)]
    o = m.add_v(P)
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        m.face([o + i for i in q], mat)
    return m

def paglia_frame():
    M = np.eye(4); M[:3, 0] = (PAG_D[0], PAG_D[1], 0); M[:3, 1] = (PAG_N[0], PAG_N[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (PAG_C[0], PAG_C[1], 0)
    return M

# ------------------------------------------------------------------ build + walk
def south_line(): return SW, SE, np.array([0.272, -0.962])

def build(mb):
    a, b, n = south_line()
    # windows (fraction along, sill z, width, height): two low ones toward the east, five high, balcony between
    win_s = [(0.07, 13.9, 2.4, 5.6), (0.20, 13.9, 2.4, 5.6), (0.33, 13.9, 2.4, 5.6), (0.66, 13.9, 2.4, 5.6), (0.79, 12.9, 2.4, 5.6), (0.92, 12.9, 2.4, 5.6)]
    M, fl, m = facade(a, b, n, 17, win_s, balcony=0.5)
    place(mb, m, M)
    a, b = SW, NW
    d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])     # left of SW->NW = west (the Piazzetta)
    win_w = [(0.08, 13.9, 2.4, 5.6), (0.21, 13.9, 2.4, 5.6), (0.34, 13.9, 2.4, 5.6), (0.66, 13.9, 2.4, 5.6), (0.79, 13.9, 2.4, 5.6), (0.92, 13.9, 2.4, 5.6)]
    M, fl, m = facade(a, b, n, 18, win_w, balcony=0.5, corner_pinnacles=(False, False))
    place(mb, m, M)
    # Porta della Carta between the palace's NW corner and the basilica's treasury
    pa, pb = NW, np.array([59.9, 20.8]); dd = (pb - pa) / np.linalg.norm(pb - pa)
    M, L, fl = facade_frame(pa, pb, np.array([-dd[1], dd[0]]))
    place(mb, porta_della_carta(), M)
    sm, L = sospiri(); place(mb, sm, sospiri_frame())
    place(mb, paglia(), paglia_frame())
    return dict(height=Z_COR + 1.8)

def portico_walk(a, b, n_out, depth, nb, arch_w, pier_d, z=GROUND_Z):
    a = np.asarray(a, float); b = np.asarray(b, float); n = np.asarray(n_out, float); n /= np.linalg.norm(n)
    d = b - a; L = np.linalg.norm(d); d /= L
    out = [(Polygon([a + n * 0.05, b + n * 0.05, b - n * (depth - 0.25), a - n * (depth - 0.25)]), z)]
    W = L / nb
    for i in range(nb + 1):
        c = a + d * (i * W); hw = (W - arch_w) / 2
        out.append((Polygon([c - d * hw + n * 0.45, c + d * hw + n * 0.45, c + d * hw - n * pier_d, c - d * hw - n * pier_d]), None))
    return out

def walk_areas():
    out = []
    a, b, n = south_line()
    out += portico_walk(a, b, n, 5.0, 17, 4.34 - 0.95, 0.7)
    d = (NW - SW) / np.linalg.norm(NW - SW)
    out += portico_walk(SW, NW, np.array([-d[1], d[0]]), 5.0, 18, 4.28 - 0.95, 0.7)
    # Ponte della Paglia deck (ramped)
    p = PAG; c = (p['a0'] + p['a1']) / 2
    poly = Polygon([PAG_C + PAG_D * p['s0'] + PAG_N * (p['t0'] + 0.35), PAG_C + PAG_D * p['s1'] + PAG_N * (p['t0'] + 0.35),
                    PAG_C + PAG_D * p['s1'] + PAG_N * (p['t1'] - 0.35), PAG_C + PAG_D * p['s0'] + PAG_N * (p['t1'] - 0.35)])
    e = (p['s1'] - p['s0']) / 2
    prof = {'a': PAG_C.tolist(), 'd': PAG_D.tolist(), 'prof': [(c - e - 1, GROUND_Z), (c - e, GROUND_Z), (c - p['land'], p['top']), (c + p['land'], p['top']), (c + e, GROUND_Z), (c + e + 1, GROUND_Z)]}
    out.append((poly, prof))
    return out
