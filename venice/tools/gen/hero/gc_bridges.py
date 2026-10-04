"""The three modern crossings of the Grand Canal, hand-modelled like rialto.py.  The generic bridge generator (bridges.py)
only makes small stepped brick bridges; these are the other ways across the Canal Grande on foot.

  Ponte dell'Accademia      Miozzi's 1933 timber bridge as rebuilt in 1985: a long, gently stepped larch deck (approach flights
                            with Miozzi's 14 cm risers and 133 cm treads) over four laminated timber arch ribs with steel braces,
                            timber balustrades with a diagonal lattice, Istrian-stone abutments.  Walk line runs SW (Dorsoduro,
                            Campo della Carita) to NE (San Marco, Campo Santo Stefano side).
  Ponte degli Scalzi        Miozzi 1934: one segmental Istrian-stone arch, smooth spandrels, solid parapets with a string course
                            and coping, stairs of four-step flights with landings round a flat crown.  Walk line runs SE
                            (Santa Croce) to NW (the station).
  Ponte della Costituzione  Calatrava 2008: a very flat steel arch (main span 80.8 m, rise 4.8 m, 94 m long), a lens-shaped
                            deck (5.6 m wide at the ends, 9.4 m in the middle), red steel hull with transverse ribs, treads
                            alternating glass and Istrian stone, glass parapets under a bronze handrail.  Walk line runs from
                            Piazzale Roma (SW) to the station (NE).

Local frame (as in rialto.py): s along the walk line (0 = middle of the water crossing), t across (+ = left of s), z absolute
(water 0, street GROUND_Z).  Placement was measured from OSM and w.land (python -m gen.hero.gc_bridges prints it again):
  Accademia     axis from the foot of the Dorsoduro steps (OSM 171899882, -804.5/-296.0) to the San Marco end of 946641887
                (-766.8/-228.4); water s = 9.87..61.30 on it (51.4 m), middle s = 35.585.  The first building is 19 m from the water
                on the SW side (Campo della Carita), the NE side is open land for 30+ m.  The NE quay is square to the walk line, the
                SW quay runs 11 degrees askew across the deck, so the abutment faces and rib ends follow the measured edge (_ACC_EDGE).
  Scalzi        axis -1258.4/764.5 -> -1285.7/809.8 (OSM "Ponte degli Scalzi"); water s = 5.71..48.94 (43.2 m), middle 27.325.
  Costituzione  axis -1561.4/491.5 -> -1498.9/572.2 (OSM 171875667, 1138085966, 1098943156); water s = 21.23..83.35 (62.1 m),
                middle 52.29: the 80.8 m arch springs about 9.4 m inland on both banks, the fondamente run under it.
"""
import math
import bisect
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G
from ..world import GROUND_Z
from .common import place

GZ = GROUND_Z
ME = 2.4                       # longest face diagonal handed to the builder (place() subdivides anything longer than max_edge)


# ================================================================================================ placement
class Axis:
    """a walk line: C = middle of the water crossing, D = unit direction (s), N = left (t)."""
    def __init__(self, a0, a1, s_mid):
        a0 = np.array(a0, float); a1 = np.array(a1, float)
        self.D = (a1 - a0) / np.linalg.norm(a1 - a0)
        self.N = np.array([-self.D[1], self.D[0]])
        self.C = a0 + self.D * s_mid

    def xy(self, s, t=0.0):
        return self.C + self.D * s + self.N * t

    def frame(self):
        M = np.eye(4); M[:3, 0] = (self.D[0], self.D[1], 0); M[:3, 1] = (self.N[0], self.N[1], 0); M[:3, 3] = (self.C[0], self.C[1], 0)
        return M

    def rect(self, s0, s1, t0, t1):
        return Polygon([tuple(self.xy(s0, t0)), tuple(self.xy(s1, t0)), tuple(self.xy(s1, t1)), tuple(self.xy(s0, t1))])

    def ribbon(self, hw, half, margin, n=96):
        """polygon of a lens-shaped deck: half width hw(u) - margin along u = -half..half."""
        us = np.linspace(-half, half, n)
        L = [tuple(self.xy(u, hw(u) - margin)) for u in us]; R = [tuple(self.xy(u, -(hw(u) - margin))) for u in us[::-1]]
        return Polygon(L + R)


ACC = Axis((-804.5, -296.0), (-766.8, -228.4), 35.585)
SCA = Axis((-1258.4, 764.5), (-1285.7, 809.8), 27.325)
COS = Axis((-1561.4, 491.5), (-1498.9, 572.2), 52.29)


# ================================================================================================ small geometry kit
def _split(a, b, me):
    """(nu, nv) pieces for a quad with sides a, b so that no piece's diagonal exceeds me."""
    if a * a + b * b <= me * me: return 1, 1
    if b <= 0.5 * me: return max(1, math.ceil(a / math.sqrt(max(me * me - b * b, (0.3 * me) ** 2)))), 1
    if a <= 0.5 * me: return 1, max(1, math.ceil(b / math.sqrt(max(me * me - a * a, (0.3 * me) ** 2))))
    k = me / math.sqrt(2.0)
    return max(1, math.ceil(a / k)), max(1, math.ceil(b / k))


def quad(m, pts, want, mat, uv=None, smooth=False):
    """planar polygon (3 or 4 points) wound so that its normal agrees with `want`; uv(p) -> (u, v) in metres."""
    P = np.asarray(pts, float)
    n = np.cross(P[2] - P[0], P[3] - P[1]) if len(P) == 4 else np.cross(P[1] - P[0], P[2] - P[0])
    if np.linalg.norm(n) < 1e-9: return
    if np.dot(n, want) < 0: P = P[::-1]; n = -n
    n = n / np.linalg.norm(n)
    m.poly([tuple(p) for p in P], mat, smooth, None if uv is None else [uv(p, n) for p in P])


def grid(m, p00, p10, p11, p01, want, mat, uv=None, me=ME):
    """quad p00-p10-p11-p01 cut into pieces whose diagonals stay within `me` (the builder would otherwise cut thin faces
    into many more triangles than they need)."""
    p00, p10, p11, p01 = (np.asarray(p, float) for p in (p00, p10, p11, p01))
    a = max(np.linalg.norm(p10 - p00), np.linalg.norm(p11 - p01)); b = max(np.linalg.norm(p01 - p00), np.linalg.norm(p11 - p10))
    nu, nv = _split(a, b, me)
    def P(x, y): return (1 - x) * (1 - y) * p00 + x * (1 - y) * p10 + x * y * p11 + (1 - x) * y * p01
    for i in range(nu):
        for j in range(nv):
            x0, x1, y0, y1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            quad(m, [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], want, mat, uv)


UV_DECK = lambda p, n=None: (p[1], p[0])       # planks run across the deck: texture u along t, v along s
UV_RISER = lambda p, n=None: (p[1], p[2])
UV_SIDE = lambda p, n=None: (p[0], p[2])       # boards along the bridge on the fascias


def UV_ALONG(p, n):
    """grain along s on timber bars (ribs, rails): side faces (s, z), end faces (t, z), the rest (s, t)."""
    if abs(n[1]) > 0.6: return (p[0], p[2])
    if abs(n[0]) > 0.6: return (p[1], p[2])
    return (p[0], p[1])

_HEXA = {'a': (0, 3, 2, 1), 'b': (4, 5, 6, 7), '0': (0, 1, 5, 4), '1': (1, 2, 6, 5), '2': (2, 3, 7, 6), '3': (3, 0, 4, 7)}


def hexa(m, P, mat, skip=(), uv=None):
    """convex hexahedron from 8 points (ring a = 0..3, ring b = 4..7), faces wound outward; skip: face keys to leave out."""
    P = np.asarray(P, float); c = P.mean(axis=0)
    for key, idx in _HEXA.items():
        if key in skip: continue
        Q = P[list(idx)]
        n = np.cross(Q[2] - Q[0], Q[3] - Q[1])
        if np.linalg.norm(n) < 1e-9: continue
        if np.dot(n, Q.mean(axis=0) - c) < 0: Q = Q[::-1]; n = -n
        n = n / np.linalg.norm(n)
        m.poly([tuple(p) for p in Q], mat, False, None if uv is None else [uv(p, n) for p in Q])


def beam3(m, a, b, w, h, mat, skip=(), up0=(0, 0, 1.0), uv=None):
    """straight bar a -> b of section w (horizontal across) x h; faces: a/b caps, 0 = underside, 1 = +side, 2 = top, 3 = -side."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; L = np.linalg.norm(d)
    if L < 1e-6: return
    d = d / L; u0 = np.array(up0, float)
    if abs(np.dot(d, u0)) > 0.95: u0 = np.array([1.0, 0, 0])
    side = np.cross(u0, d); side /= np.linalg.norm(side); up = np.cross(d, side)
    def ring(p): return [p - side * w / 2 - up * h / 2, p + side * w / 2 - up * h / 2, p + side * w / 2 + up * h / 2, p - side * w / 2 + up * h / 2]
    hexa(m, ring(a) + ring(b), mat, skip, uv)


def loft(m, rings, mat, closed=False, smooth=False, outward=None, uv=None):
    """faces between consecutive rings (lists of 3D points of equal length); each quad wound away from `outward(centre, i)`
    (default: the middle of the two rings).  Smooth lofts share their ring vertices so the builder can average normals."""
    rings = [np.asarray(r, float) for r in rings]
    n = len(rings[0]); nseg = n if closed else n - 1
    ids = [m.add_v(r) for r in rings]
    for i in range(len(rings) - 1):
        mid = (rings[i].mean(axis=0) + rings[i + 1].mean(axis=0)) / 2
        for j in range(nseg):
            j2 = (j + 1) % n
            q = [ids[i] + j, ids[i] + j2, ids[i + 1] + j2, ids[i + 1] + j]
            P = np.array([m.V[k] for k in q])
            nrm = np.cross(P[2] - P[0], P[3] - P[1]); c = P.mean(axis=0)
            ref = outward(c, i) if outward is not None else c - mid
            if np.dot(nrm, ref) < 0: q = q[::-1]; nrm = -nrm
            nrm = nrm / max(np.linalg.norm(nrm), 1e-12)
            m.face(q, mat, smooth, None if uv is None else [uv(m.V[k], nrm) for k in q])


def rect_sweep(m, path, w, h, mat, caps=True, uv=None):
    """square-section bar (w across, h high) along a 3D polyline."""
    P = [np.asarray(p, float) for p in path]
    rings = []; ds = []
    for i, p in enumerate(P):
        d = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; d /= np.linalg.norm(d); ds.append(d)
        side = np.cross((0, 0, 1.0), d); side /= np.linalg.norm(side); up = np.cross(d, side)
        rings.append([p - side * w / 2 - up * h / 2, p + side * w / 2 - up * h / 2, p + side * w / 2 + up * h / 2, p - side * w / 2 + up * h / 2])
    loft(m, rings, mat, closed=True, uv=uv)
    if caps:
        quad(m, rings[0], -ds[0], mat, uv); quad(m, rings[-1], ds[-1], mat, uv)


def wall_between(m, A, B, want, mat, uv=None, me=ME):
    """vertical face strip between polylines A (bottom) and B (top): one gridded quad per interval."""
    for i in range(len(A) - 1):
        grid(m, A[i], A[i + 1], B[i + 1], B[i], want, mat, uv, me)


def _samples(lo, hi, step, extra=()):
    n = max(1, int(math.ceil((hi - lo) / step)))
    return sorted(set([round(x, 6) for x in np.linspace(lo, hi, n + 1)] + [round(float(e), 6) for e in extra if lo - 1e-9 <= e <= hi + 1e-9]))


# ================================================================================================ steps
def add_treads(m, treads, hwf, mat_top, mat_riser=None, uv_top=None, uv_riser=None, me=ME):
    """treads: [(s0, s1, z)] contiguous and ascending in s; hwf(s) = half width there.  Tread tops and the risers between
    neighbouring treads (and down to the street at both ends); the higher tread owns the riser.  No side faces."""
    mat_riser = mat_riser or mat_top
    n = len(treads)
    for k, (sa, sb, z) in enumerate(treads):
        grid(m, (sa, -hwf(sa), z), (sb, -hwf(sb), z), (sb, hwf(sb), z), (sa, hwf(sa), z), (0, 0, 1.0), mat_top(k), uv_top, me)
        zp = GZ if k == 0 else treads[k - 1][2]
        if abs(z - zp) > 1e-6:
            hi_k = k if z > zp else k - 1
            w_ = hwf(sa); zl, zh = min(z, zp), max(z, zp)
            grid(m, (sa, -w_, zl), (sa, w_, zl), (sa, w_, zh), (sa, -w_, zh), (-1.0, 0, 0) if z > zp else (1.0, 0, 0), mat_riser(hi_k), uv_riser, me)
    sa, sb, z = treads[-1]
    if z - GZ > 1e-6:
        w_ = hwf(sb)
        grid(m, (sb, -w_, GZ), (sb, w_, GZ), (sb, w_, z), (sb, -w_, z), (1.0, 0, 0), mat_riser(n - 1), uv_riser, me)


def tread_z(treads, u):
    starts = [t[0] for t in treads]
    k = max(0, min(len(treads) - 1, bisect.bisect_right(starts, u) - 1))
    return treads[k][2]


def walk_profile(treads, ext=1.0):
    """[(s, z)] through the middle of every riser (never more than half a riser off a tread), at GROUND_Z `ext` m beyond the ends."""
    pts = [(treads[0][0] - ext, GZ), (treads[0][0], (GZ + treads[0][2]) / 2)]
    for k in range(1, len(treads)):
        if abs(treads[k][2] - treads[k - 1][2]) > 1e-6: pts.append((treads[k][0], (treads[k][2] + treads[k - 1][2]) / 2))
    pts.append((treads[-1][1], (GZ + treads[-1][2]) / 2)); pts.append((treads[-1][1] + ext, GZ))
    return [(round(float(s), 3), round(float(z), 3)) for s, z in pts]


def _mirror(half):
    """half = treads for u >= 0 from the crown outwards, first one (0, b, z) is the platform -> full symmetric list ascending in s."""
    left = [(-ub, -ua, z) for (ua, ub, z) in half[1:]][::-1]
    mid = [(-half[0][1], half[0][1], half[0][2])]
    return left + mid + list(half[1:])


# ================================================================================================ PONTE DELL'ACCADEMIA
ACC_HW = 3.2                   # half width over the fascias (OSM maps the deck 5.4 m between its edges)
ACC_A = 25.75                  # half clear span on the centre line: the abutment faces stand on the quay edges (water crossing 51.4 m)
ACC_ZCR = 7.5                  # walking surface at the crown
ACC_ZSP, ACC_ZCRS = 1.0, 7.0   # soffit of the ribs at the springing and at the crown (rise 6 m)
ACC_RAP, ACC_TAP, ACC_NAP = 0.14, 1.33, 9      # approach flights: riser, tread, steps
ACC_ZAB = GZ + ACC_NAP * ACC_RAP               # deck level on the abutments, 2.36
ACC_NARCH = 37                 # steps from the abutment up to the crown platform
ACC_SAG = ACC_ZCR - ACC_ZAB
ACC_RD = (ACC_A ** 2 + ACC_SAG ** 2) / (2 * ACC_SAG)                               # the deck is a circle over the span
ACC_RA = (ACC_A ** 2 + (ACC_ZCRS - ACC_ZSP) ** 2) / (2 * (ACC_ZCRS - ACC_ZSP))     # and the rib soffit another
ACC_UEND = ACC_A + ACC_NAP * ACC_TAP           # foot of the stairs
ACC_RIBS = (-2.7, -0.95, 0.95, 2.7); ACC_RW = 0.5
ACC_UNDER = 0.30               # deck thickness (planks + joists) under the walking surface
ACC_FASC = 0.45                # fascia depth
# quay edge across the deck, measured on w.land: (t, u) with u from the middle of the crossing.  The NE bank is square to the
# walk line, the SW bank (Campo della Carita) runs 11 degrees askew over the first 4.5 m, so the abutment faces follow it.
_ACC_EDGE = {-1: ((-3.6, -26.55), (-2.0, -26.18), (-0.8, -25.90), (0.8, -25.52), (2.0, -25.38), (3.6, -25.21)),
             1: ((-3.6, 25.67), (0.0, 25.71), (3.6, 25.75))}


def acc_face(sg, t):
    """u of the abutment face at lateral position t on the sg (-1 = SW, +1 = NE) bank, 4 cm inside the land."""
    pts = _ACC_EDGE[sg]
    return float(np.interp(t, [q[0] for q in pts], [q[1] for q in pts])) + sg * 0.04


def acc_zd(u):
    a = abs(u)
    if a <= ACC_A: return ACC_ZCR - ACC_RD + math.sqrt(ACC_RD ** 2 - a * a)
    return max(GZ, ACC_ZAB - (a - ACC_A) * ACC_RAP / ACC_TAP)


def acc_zs(u): return ACC_ZCRS - (ACC_RA - math.sqrt(ACC_RA ** 2 - u * u))
def acc_dep(u): return 0.40 + 0.35 * (u / ACC_A) ** 2


def _acc_treads():
    n = ACC_NARCH; ra = ACC_SAG / n; zc = ACC_ZCR - ACC_RD
    def u_of(z): return math.sqrt(max(0.0, ACC_RD ** 2 - (z - zc) ** 2))
    b = {k: u_of(ACC_ZAB + (k - 0.5) * ra) for k in range(1, n + 1)}       # riser between step k-1 and step k
    half = [(0.0, b[n], ACC_ZCR)]
    for k in range(n - 1, 0, -1): half.append((b[k + 1], b[k], ACC_ZAB + k * ra))
    half.append((b[1], ACC_A + ACC_TAP, ACC_ZAB))                           # abutment landing
    for j in range(1, ACC_NAP): half.append((ACC_A + j * ACC_TAP, ACC_A + (j + 1) * ACC_TAP, ACC_ZAB - j * ACC_RAP))
    return _mirror(half)


ACC_TREADS = _acc_treads()


def _acc_deck(m):
    add_treads(m, ACC_TREADS, lambda s: ACC_HW, lambda k: 'wood_raw', lambda k: 'shop_wood', UV_DECK, UV_RISER)
    # fascias: one board-wide strip per tread, from the underside up to the tread
    for side in (-1, 1):
        for (sa, sb, z) in ACC_TREADS:
            zb = lambda u: max(GZ - 0.05, acc_zd(u) - ACC_FASC)
            grid(m, (sa, side * ACC_HW, zb(sa)), (sb, side * ACC_HW, zb(sb)), (sb, side * ACC_HW, z), (sa, side * ACC_HW, z), (0, side, 0.0), 'shop_wood', UV_SIDE)
    # the underside of the planking between the abutments (ends follow the quay-side faces)
    w = ACC_HW - 0.04; tb = np.linspace(-w, w, 5); N = 52
    for ta, tb_ in zip(tb[:-1], tb[1:]):
        def col(i, t): return acc_face(-1, t) + (acc_face(1, t) - acc_face(-1, t)) * i / N
        for i in range(N):
            P = [(col(i, ta), ta), (col(i + 1, ta), ta), (col(i + 1, tb_), tb_), (col(i, tb_), tb_)]
            grid(m, *[(u, t, acc_zd(u) - ACC_UNDER) for (u, t) in P], (0, 0, -1.0), 'wood_raw', UV_DECK)


def _acc_ribs(m, steel):
    for tr in ACC_RIBS:
        u0, u1 = acc_face(-1, tr), acc_face(1, tr)
        us = list(np.linspace(u0, u1, 53))
        rings = [[(u, tr - ACC_RW / 2, acc_zs(u)), (u, tr + ACC_RW / 2, acc_zs(u)), (u, tr + ACC_RW / 2, acc_zs(u) + acc_dep(u)), (u, tr - ACC_RW / 2, acc_zs(u) + acc_dep(u))] for u in us]
        loft(m, rings, 'wood_raw', closed=True, uv=UV_ALONG)
        quad(m, rings[0], (-1.0, 0, 0), 'wood_raw', UV_ALONG); quad(m, rings[-1], (1.0, 0, 0), 'wood_raw', UV_ALONG)
        for sg, u in ((-1, u0), (1, u1)):                                  # steel shoes where the ribs bear on the stone
            ui = u - sg * 0.8
            hexa(steel, [(u, tr - 0.3, acc_zs(u) - 0.18), (u, tr + 0.3, acc_zs(u) - 0.18), (u, tr + 0.3, acc_zs(u) + acc_dep(u) + 0.12), (u, tr - 0.3, acc_zs(u) + acc_dep(u) + 0.12),
                          (ui, tr - 0.3, acc_zs(ui) - 0.18), (ui, tr + 0.3, acc_zs(ui) - 0.18),
                          (ui, tr + 0.3, acc_zs(ui) + acc_dep(ui) + 0.12), (ui, tr - 0.3, acc_zs(ui) + acc_dep(ui) + 0.12)], 'metal', skip=('a',))
    # panel points: timber struts across and steel X braces in the plane of the ribs' middle
    pts = np.linspace(-ACC_A + 1.5, ACC_A - 1.5, 17)
    zm = lambda u: acc_zs(u) + acc_dep(u) * 0.5
    for k, u in enumerate(pts):
        for ta, tb in zip(ACC_RIBS[:-1], ACC_RIBS[1:]):
            a = (u, ta + ACC_RW / 2, zm(u)); b = (u, tb - ACC_RW / 2, zm(u))
            beam3(m, a, b, 0.14, 0.2, 'wood_raw', skip=('a', 'b'))
            if k + 1 < len(pts):
                u2 = pts[k + 1]
                beam3(steel, (u, ta + ACC_RW / 2, zm(u)), (u2, tb - ACC_RW / 2, zm(u2)), 0.05, 0.05, 'metal')
                beam3(steel, (u, tb - ACC_RW / 2, zm(u)), (u2, ta + ACC_RW / 2, zm(u2)), 0.05, 0.05, 'metal')
    # short steel posts where the deck stands off the ribs (towards the abutments)
    for u in np.linspace(-ACC_A + 2.0, ACC_A - 2.0, 25):
        gap = (acc_zd(u) - ACC_UNDER) - (acc_zs(u) + acc_dep(u))
        if gap > 0.06:
            for tr in ACC_RIBS:
                beam3(steel, (u, tr, acc_zs(u) + acc_dep(u) - 0.05), (u, tr, acc_zd(u) - ACC_UNDER + 0.02), 0.12, 0.2, 'metal', skip=('a', 'b'))


def _acc_abutments(m):
    wb = ACC_HW + 0.3
    for sg in (-1, 1):
        ts = [-wb, -2.0, -0.8, 0.8, 2.0, wb]
        poly = [(acc_face(sg, t), t) for t in ts] + [(sg * (ACC_A + 2.5), wb), (sg * (ACC_A + 2.5), -wb)]
        m.merge(G.prism([poly], -1.6, ACC_ZAB - ACC_UNDER, 'istrian', top=False))
        m.merge(G.prism([poly], ACC_ZAB - ACC_UNDER, ACC_ZAB - ACC_UNDER + 0.1, 'bridge_stone', top=True))        # cut-stone cap course


def _acc_balustrade(m):
    HB = 1.08                                   # rail centre above the smooth deck line
    zr = lambda u: acc_zd(u) + HB
    us = _samples(-ACC_UEND, ACC_UEND, 1.2, extra=[-ACC_A, ACC_A, -ACC_TREADS[len(ACC_TREADS) // 2][1], ACC_TREADS[len(ACC_TREADS) // 2][1]])
    npan = 31; pitch = 2 * (ACC_UEND - 0.12) / npan
    posts = [-ACC_UEND + 0.12 + i * pitch for i in range(npan + 1)]
    for side in (-1, 1):
        t = side * (ACC_HW - 0.10)
        rect_sweep(m, [(u, t, zr(u)) for u in us], 0.17, 0.09, 'shop_wood', uv=UV_ALONG)                    # top rail
        rect_sweep(m, [(u, t, acc_zd(u) + 0.16) for u in us], 0.10, 0.08, 'shop_wood', uv=UV_ALONG)          # bottom rail
        for u in posts:
            zb = tread_z(ACC_TREADS, u) - 0.04
            m.merge(G.box(u - 0.06, t - 0.06, zb, u + 0.06, t + 0.06, zr(u) - 0.045, 'shop_wood'))
        for u in (-ACC_UEND + 0.12, ACC_UEND - 0.12):                                            # newels at the feet
            m.merge(G.box(u - 0.10, t - 0.10, GZ - 0.05, u + 0.10, t + 0.10, GZ + 1.42, 'shop_wood'))
            m.merge(G.box(u - 0.14, t - 0.14, GZ + 1.42, u + 0.14, t + 0.14, GZ + 1.50, 'shop_wood'))
        # diagonal lattice (two families of slats, 3 cm apart so they never share a plane)
        zl0, zl1 = 0.205, 1.035; hl = zl1 - zl0; pitch_l = 0.28
        for ua, ub in zip(posts[:-1], posts[1:]):
            w = ub - ua; za, zb_ = acc_zd(ua), acc_zd(ub)
            zbase = lambda x: za + (zb_ - za) * x / w
            x_lo, x_hi = 0.06, w - 0.06
            for fam in (0, 1):
                tt = t + (0.016 if fam == 0 else -0.016)
                n = int(math.ceil((w + hl) / pitch_l)) + 1
                for k in range(n):
                    x0 = -hl + k * pitch_l
                    if fam == 0: xa, xb = max(x_lo, x0), min(x_hi, x0 + hl); ya, yb = zl0 + (xa - x0), zl0 + (xb - x0)
                    else: xa, xb = max(x_lo, x0), min(x_hi, x0 + hl); ya, yb = zl1 - (xa - x0), zl1 - (xb - x0)
                    if xb - xa < 0.12: continue
                    beam3(m, (ua + xa, tt, zbase(xa) + ya), (ua + xb, tt, zbase(xb) + yb), 0.03, 0.05, 'wood_raw', skip=('a', 'b'))


def build_accademia(mb):
    main = G.Mesh(); steel = G.Mesh()
    _acc_deck(main); _acc_ribs(main, steel); _acc_abutments(main); _acc_balustrade(main)
    M = ACC.frame()
    place(mb, main, M, max_edge=ME * 1.02)
    place(mb, steel, M, c1=(0, 0, 0, 12), max_edge=ME * 1.02)         # flag 12: bright steel
    return dict(height=ACC_ZCR + 1.2)


# ================================================================================================ PONTE DEGLI SCALZI
SCA_HW = 3.6                   # half width (OSM polygon 7.2 m)
SCA_PT = 0.46                  # parapet thickness
SCA_A = 21.6                   # half span: the arch springs on the quay edges (water crossing 43.2 m)
SCA_ZSP, SCA_ZCR = 0.5, 6.8    # soffit at the springing and at the crown
SCA_ZTOP = 7.65                # flat crown walkway (crown soffit + 0.8 m ring + paving)
SCA_PLAT = 5.85                # half length of the crown platform
SCA_NFL, SCA_RUN, SCA_LAND = 11, 20.6, 0.85    # flights per side, plan length of the stairs per side, landing length
SCA_R = (SCA_ZTOP - GZ) / (4 * SCA_NFL)                              # riser 14.9 cm
SCA_TT = (SCA_RUN - (SCA_NFL - 1) * SCA_LAND) / (3 * SCA_NFL)        # tread 36.7 cm
SCA_UEND = SCA_PLAT + SCA_RUN
SCA_RA = (SCA_A ** 2 + (SCA_ZCR - SCA_ZSP) ** 2) / (2 * (SCA_ZCR - SCA_ZSP))
SCA_PAR = 1.0                  # parapet height above the pitch line
SCA_FLARE = 1.5                # each parapet swings out this far over the last stretch of the stairs (OSM maps a round, ~12 m wide foot)
SCA_FL = SCA_UEND - SCA_A


def sca_hw(u):
    """outer half width: 3.6 m, flaring on the land beyond the springings (quadratic, 32 degrees at the foot)."""
    x = max(0.0, abs(u) - SCA_A) / SCA_FL
    return SCA_HW + SCA_FLARE * x * x


def sca_zr(u):
    a = abs(u)
    if a <= SCA_PLAT: return SCA_ZTOP
    return GZ + (SCA_ZTOP - GZ) * max(0.0, SCA_UEND - a) / SCA_RUN


def sca_zs(u): return SCA_ZCR - (SCA_RA - math.sqrt(SCA_RA ** 2 - u * u))


def _sca_treads():
    half = [(0.0, SCA_PLAT, SCA_ZTOP)]
    u = SCA_PLAT; z = SCA_ZTOP
    for f in range(SCA_NFL):
        for j in range(3):
            z -= SCA_R; half.append((u, u + SCA_TT, z)); u += SCA_TT
        z -= SCA_R
        if f < SCA_NFL - 1:
            half.append((u, u + SCA_LAND, z)); u += SCA_LAND
    return _mirror(half)


SCA_TREADS = _sca_treads()


def _rbox(m, cu, ct, z0, z1, hx, hy, ang, mat):
    """box (no bottom) centred on (cu, ct) in plan, half size hx along the direction `ang` and hy across it."""
    c, s_ = math.cos(ang), math.sin(ang)
    q = [(cu + c * dx - s_ * dy, ct + s_ * dx + c * dy) for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
    hexa(m, [(x, y, z0) for x, y in q] + [(x, y, z1) for x, y in q], mat, skip=('a',))


def _sca_stone(m):
    hw = sca_hw
    hin = lambda u: sca_hw(u) - SCA_PT
    add_treads(m, SCA_TREADS, hin, lambda k: 'istrian')
    # soffit of the arch
    us = _samples(-SCA_A, SCA_A, 1.1)
    for u0, u1 in zip(us[:-1], us[1:]):
        grid(m, (u0, -SCA_HW, sca_zs(u0)), (u1, -SCA_HW, sca_zs(u1)), (u1, SCA_HW, sca_zs(u1)), (u0, SCA_HW, sca_zs(u0)), (0, 0, -1.0), 'istrian')
    for sg in (-1, 1):                                                      # abutment faces on the quay edges
        grid(m, (sg * SCA_A, -SCA_HW, -1.2), (sg * SCA_A, SCA_HW, -1.2), (sg * SCA_A, SCA_HW, SCA_ZSP), (sg * SCA_A, -SCA_HW, SCA_ZSP), (-sg * 1.0, 0, 0), 'istrian')
    us = _samples(-SCA_UEND, SCA_UEND, 1.2, extra=[-SCA_A, SCA_A, -SCA_PLAT, SCA_PLAT])
    zrp = lambda u: sca_zr(u) + SCA_PAR
    for side in (-1, 1):
        for u0, u1 in zip(us[:-1], us[1:]):
            t0, t1 = side * hw(u0), side * hw(u1)
            # smooth outer face from the arch (or the street) up to the parapet top
            if abs(0.5 * (u0 + u1)) < SCA_A: b0, b1 = sca_zs(u0), sca_zs(u1)
            else: b0 = b1 = GZ - 0.15
            grid(m, (u0, t0, b0), (u1, t1, b1), (u1, t1, zrp(u1)), (u0, t0, zrp(u0)), (0, side, 0.0), 'istrian')
            # inner face of the parapet down to below the treads
            i0, i1 = side * hin(u0), side * hin(u1)
            grid(m, (u0, i0, sca_zr(u0) - 0.45), (u1, i1, sca_zr(u1) - 0.45), (u1, i1, zrp(u1)), (u0, i0, zrp(u0)), (0, -side, 0.0), 'istrian')
            # string course under the parapet (projects 12 cm) and the coping on top (projects 8 cm both ways)
            o0, o1 = side * (hw(u0) + 0.12), side * (hw(u1) + 0.12)
            hexa(m, [(u0, t0, sca_zr(u0) - 0.30), (u0, o0, sca_zr(u0) - 0.30), (u0, o0, sca_zr(u0) - 0.02), (u0, t0, sca_zr(u0) - 0.02),
                     (u1, t1, sca_zr(u1) - 0.30), (u1, o1, sca_zr(u1) - 0.30), (u1, o1, sca_zr(u1) - 0.02), (u1, t1, sca_zr(u1) - 0.02)], 'istrian', skip=('a', 'b', '3'))
            a0, a1 = side * (hin(u0) - 0.08), side * (hin(u1) - 0.08); c0, c1 = side * (hw(u0) + 0.08), side * (hw(u1) + 0.08)
            hexa(m, [(u0, a0, zrp(u0)), (u0, c0, zrp(u0)), (u0, c0, zrp(u0) + 0.15), (u0, a0, zrp(u0) + 0.15),
                     (u1, a1, zrp(u1)), (u1, c1, zrp(u1)), (u1, c1, zrp(u1) + 0.15), (u1, a1, zrp(u1) + 0.15)], 'istrian', skip=('a', 'b'))
        # ring (archivolt) round the arch, slightly proud of the smooth spandrel
        t = side * SCA_HW
        zc = SCA_ZCR - SCA_RA
        ring_us = _samples(-SCA_A, SCA_A, 1.0)
        def rad(u, r):
            z = sca_zs(u); k = (SCA_RA + r) / SCA_RA
            return (u * k, zc + (z - zc) * k)
        for u0, u1 in zip(ring_us[:-1], ring_us[1:]):
            i0, i1 = rad(u0, 0.0), rad(u1, 0.0); o0, o1 = rad(u0, 0.45), rad(u1, 0.45)
            hexa(m, [(i0[0], t, i0[1]), (i0[0], t + side * 0.08, i0[1]), (o0[0], t + side * 0.08, o0[1]), (o0[0], t, o0[1]),
                     (i1[0], t, i1[1]), (i1[0], t + side * 0.08, i1[1]), (o1[0], t + side * 0.08, o1[1]), (o1[0], t, o1[1])], 'istrian', skip=('a', 'b', '3'))
        # piers closing the parapets at the feet, turned to the flare
        for sg in (-1, 1):
            u = sg * (SCA_UEND - 0.32); h = 0.05
            ang = math.atan2(side * (hw(u + h) - hw(u - h)), 2 * h)
            d = np.array([math.cos(ang), math.sin(ang)]); n = np.array([-d[1], d[0]])
            if n[1] * side > 0: n = -n                                      # inward
            c = np.array([u, side * hw(u)]) + n * 0.40
            _rbox(m, c[0], c[1], GZ - 0.15, GZ + 1.45, 0.40, 0.40, ang, 'istrian')
            _rbox(m, c[0], c[1], GZ + 1.45, GZ + 1.60, 0.47, 0.47, ang, 'istrian')


def build_scalzi(mb):
    m = G.Mesh()
    _sca_stone(m)
    place(mb, m, SCA.frame(), max_edge=ME * 1.02)
    return dict(height=SCA_ZTOP + SCA_PAR + 0.15)


# ================================================================================================ PONTE DELLA COSTITUZIONE
COS_HALF, COS_A = 47.0, 40.4                 # half length (94 m), half of the 80.8 m arch
COS_ZCR, COS_ZAB = 8.1, 3.3                  # walking surface at the crown / on the abutments (rise 4.8 m)
COS_HM, COS_HE = 4.69, 2.79                  # half width in the middle (9.38) and at the ends (5.58)
COS_RP = (COS_HALF ** 2 + (COS_HM - COS_HE) ** 2) / (2 * (COS_HM - COS_HE))      # the deck edges are arcs in plan
COS_SAG = COS_ZCR - COS_ZAB
COS_RD = (COS_A ** 2 + COS_SAG ** 2) / (2 * COS_SAG)                             # the deck follows a circle (R ~ 172 m)
COS_EB = 0.28                                # edge beam width
COS_G = 0.75                                 # depth of the hull below the edge beams in the middle
COS_RED = (186, 62, 42, 0)                   # painted steel (tint of wall_plaster)
COS_PAR = 1.05                               # glass height above the edge beam top


def cos_h(u):
    a = min(abs(u), COS_HALF)
    return COS_HM - (COS_RP - math.sqrt(COS_RP ** 2 - a * a))


def cos_zd(u):
    a = abs(u)
    if a <= COS_A: return COS_ZCR - COS_RD + math.sqrt(COS_RD ** 2 - a * a)
    return max(GZ, COS_ZAB - (a - COS_A) / (COS_HALF - COS_A) * (COS_ZAB - GZ))


def _cos_treads():
    n = 35; ra = COS_SAG / n; zc = COS_ZCR - COS_RD
    def u_of(z): return math.sqrt(max(0.0, COS_RD ** 2 - (z - zc) ** 2))
    b = {k: u_of(COS_ZAB + (k - 0.5) * ra) for k in range(1, n + 1)}
    half = [(0.0, b[n], COS_ZCR)]
    for k in range(n - 1, 0, -1): half.append((b[k + 1], b[k], COS_ZAB + k * ra))
    half.append((b[1], COS_A, COS_ZAB))
    tl = (COS_HALF - COS_A) / 15; re = (COS_ZAB - GZ) / 16
    for j in range(1, 16): half.append((COS_A + (j - 1) * tl, COS_A + j * tl, COS_ZAB - j * re))
    full = _mirror(half)
    out = []                                                  # treads longer than 1.4 m become flush panels of equal length
    for (sa, sb, z) in full:
        k = max(1, int(math.ceil((sb - sa) / 1.4)))
        for i in range(k): out.append((sa + (sb - sa) * i / k, sa + (sb - sa) * (i + 1) / k, z))
    return out


COS_TREADS = _cos_treads()


def _cos_red(red):
    # ---- hull: an elliptical keel under the whole span, smooth-shaded
    us = _samples(-COS_A, COS_A, 2.0)
    M_ = 14
    phis = np.linspace(-math.pi / 2, math.pi / 2, M_ + 1)
    def sec(u, off=0.0):
        h = cos_h(u) - COS_EB * 0.5; zc = cos_zd(u) - 0.30
        pts = []
        for ph in phis:
            x, y = h * math.sin(ph), -COS_G * math.cos(ph)
            if off:                                    # offset along the ellipse normal
                nx, ny = math.sin(ph) / h, -math.cos(ph) / COS_G; l = math.hypot(nx, ny); x += off * nx / l; y += off * ny / l
            pts.append((u, x, zc + y))
        return pts
    rings = [sec(u) for u in us]
    loft(red, rings, 'wall_plaster', smooth=True, outward=lambda c, i: np.array(c) - np.array([c[0], 0.0, cos_zd(c[0]) + 1.0]))
    # ---- the box girder: a keel along the lowest line of the hull, wider towards the abutments
    def spine(u):
        w = 0.6 + 0.25 * (u / COS_A) ** 2; zt = cos_zd(u) - 0.30 - COS_G + 0.02; zb = zt - 0.36
        return [(u, -w, zt), (u, w, zt), (u, w, zb + 0.14), (u, w - 0.14, zb), (u, -w + 0.14, zb), (u, -w, zb + 0.14)]
    loft(red, [spine(u) for u in us], 'wall_plaster', closed=True)
    quad(red, spine(us[0]), (-1.0, 0, 0), 'wall_plaster'); quad(red, spine(us[-1]), (1.0, 0, 0), 'wall_plaster')
    # ---- transverse ribs (fins) under the hull, 2.5 m apart
    for u in np.linspace(-COS_A + 1.3, COS_A - 1.3, 33):
        a, b = sec(u - 0.035), sec(u + 0.035); a2, b2 = sec(u - 0.035, 0.20), sec(u + 0.035, 0.20)
        for j in range(M_):
            quad(red, [a2[j], a2[j + 1], b2[j + 1], b2[j]], (0, 0, -1.0), 'wall_plaster')
            quad(red, [a[j], a[j + 1], a2[j + 1], a2[j]], (-1.0, 0, 0), 'wall_plaster')
            quad(red, [b[j], b[j + 1], b2[j + 1], b2[j]], (1.0, 0, 0), 'wall_plaster')
        for (p, q) in ((0, 0), (M_, M_)):                  # close the fin where it meets the edge beam
            quad(red, [a[p], a2[p], b2[p], b[p]], (0, 1.0 if p else -1.0, 0), 'wall_plaster')
    # ---- edge beams (the side arches) over the whole length, tops 0.10 above the deck line
    es = _samples(-COS_HALF, COS_HALF, 1.5, extra=[-COS_A, COS_A])
    for side in (-1, 1):
        rings = [[(u, side * (cos_h(u) - COS_EB), cos_zd(u) - 0.30), (u, side * cos_h(u), cos_zd(u) - 0.30), (u, side * cos_h(u), cos_zd(u) + 0.10), (u, side * (cos_h(u) - COS_EB), cos_zd(u) + 0.10)] for u in es]
        loft(red, rings, 'wall_plaster', closed=True)
        quad(red, rings[0], (-1.0, 0, 0), 'wall_plaster'); quad(red, rings[-1], (1.0, 0, 0), 'wall_plaster')


def _cos_stone(m):
    # abutments under the end stairs: stone cheeks along the edges and the inner face under the hull
    es = _samples(COS_A, COS_HALF, 1.4)
    for sg in (-1, 1):
        us = [sg * u for u in es][::1 if sg > 0 else -1]
        for side in (-1, 1):
            A_ = [(u, side * cos_h(u), GZ - 0.1) for u in us]; B_ = [(u, side * cos_h(u), cos_zd(u) - 0.30) for u in us]
            wall_between(m, A_, B_, (0, side, 0.0), 'istrian')
        u = sg * COS_A; w = cos_h(u) - COS_EB
        grid(m, (u, -w, GZ - 0.1), (u, w, GZ - 0.1), (u, w, cos_zd(u) - 0.30), (u, -w, cos_zd(u) - 0.30), (-sg * 1.0, 0, 0), 'istrian')


def _cos_deck(m):
    hwt = lambda s: cos_h(s) - COS_EB
    add_treads(m, COS_TREADS, hwt, lambda k: 'istrian' if k % 2 == 0 else 'glass')


def _cos_parapets(m, bronze):
    es = _samples(-COS_HALF, COS_HALF, 1.5, extra=[-COS_A, COS_A])
    for side in (-1, 1):
        tc = lambda u: side * (cos_h(u) - COS_EB * 0.5)
        for u0, u1 in zip(es[:-1], es[1:]):
            ua, ub = u0 + 0.018, u1 - 0.018
            za, zb = cos_zd(ua) + 0.10, cos_zd(ub) + 0.10
            pa = np.array([ua, tc(ua), za]); pb = np.array([ub, tc(ub), zb])
            d = pb - pa; nrm = np.cross(d, (0, 0, 1.0)); nrm = nrm / np.linalg.norm(nrm) * 0.015
            hexa(m, [pa - nrm, pb - nrm, pb - nrm + (0, 0, COS_PAR), pa - nrm + (0, 0, COS_PAR), pa + nrm, pb + nrm, pb + nrm + (0, 0, COS_PAR), pa + nrm + (0, 0, COS_PAR)], 'glass', skip=('0',))
        rect_sweep(bronze, [(u, tc(u), cos_zd(u) + 0.10 + COS_PAR + 0.035) for u in es], 0.10, 0.07, 'bronze_gilt')


def build_costituzione(mb):
    main = G.Mesh(); red = G.Mesh(); bronze = G.Mesh()
    _cos_deck(main); _cos_stone(main); _cos_red(red); _cos_parapets(main, bronze)
    M = COS.frame()
    place(mb, main, M, max_edge=ME * 1.02)
    place(mb, red, M, c0=COS_RED, max_edge=ME * 1.02)
    place(mb, bronze, M, max_edge=ME * 1.02)
    return dict(height=COS_ZCR + 0.10 + COS_PAR + 0.07)


# ================================================================================================ exports
# Registration in gen/hero/__init__.py: import this module; EXCLUDE_BRIDGES += gc_bridges.EXCLUDE; in setup()
#   HEROES.append((gc_bridges.ANCHORS['accademia'], lambda mb, inst: gc_bridges.build_accademia(mb)))   (same for scalzi, costituzione)
# and walk_areas() += gc_bridges.walk_areas().  Each bridge is built by the tile holding its ANCHOR; footprints reach into
# the neighbour tile for the Accademia (t_12_6) and the Scalzi (t_10_12), whose walk rasters pick them up from walk_areas().
ANCHORS = {'accademia': (float(ACC.C[0]), float(ACC.C[1])), 'scalzi': (float(SCA.C[0]), float(SCA.C[1])), 'costituzione': (float(COS.C[0]), float(COS.C[1]))}
# one circle per bridge round the middle of its water crossing, where the generic generator would put its chord midpoint
# (the next generic bridges are 42.7 m, 52.8 m and 42.0 m away)
EXCLUDE = [(ANCHORS['accademia'][0], ANCHORS['accademia'][1], 34.0), (ANCHORS['scalzi'][0], ANCHORS['scalzi'][1], 40.0),
           (ANCHORS['costituzione'][0], ANCHORS['costituzione'][1], 34.0)]


def _prof(ax, treads):
    return {'a': [float(ax.C[0]), float(ax.C[1])], 'd': [float(ax.D[0]), float(ax.D[1])], 'prof': walk_profile(treads)}


def walk_areas():
    """[(polygon, z)]: each bridge's footprint blocked first, then the deck between the parapets as a ramp along s."""
    out = []
    e = 0.5
    # Accademia
    out.append((ACC.rect(ACC_TREADS[0][0] - e, ACC_TREADS[-1][1] + e, -ACC_HW - 0.4, ACC_HW + 0.4), None))
    out.append((ACC.rect(ACC_TREADS[0][0] - e, ACC_TREADS[-1][1] + e, -ACC_HW + 0.22, ACC_HW - 0.22), _prof(ACC, ACC_TREADS)))
    # Scalzi
    out.append((SCA.ribbon(sca_hw, SCA_UEND + e, -0.2), None))
    out.append((SCA.ribbon(sca_hw, SCA_UEND + e, SCA_PT + 0.1), _prof(SCA, SCA_TREADS)))
    # Costituzione: lens-shaped deck
    out.append((COS.ribbon(cos_h, COS_HALF + e, -0.3), None))
    out.append((COS.ribbon(cos_h, COS_HALF + e, COS_EB + 0.12), _prof(COS, COS_TREADS)))
    return out


# ================================================================================================ measurement
def check(world=None):
    """re-measure the placements against w.land and the building footprints, and the walk profiles against the treads
    (needs the world cache)."""
    from shapely.geometry import LineString, Point
    from shapely.ops import unary_union
    if world is None:
        from ..world import load
        world = load()
    bl = unary_union([b.poly for b in world.buildings])
    wa = walk_areas()
    for k, (name, ax, treads) in enumerate((('accademia', ACC, ACC_TREADS), ('scalzi', SCA, SCA_TREADS), ('costituzione', COS, COS_TREADS))):
        s0, s1 = treads[0][0], treads[-1][1]
        wat = LineString([tuple(ax.xy(s0 - 60)), tuple(ax.xy(s1 + 60))]).difference(world.land)
        segs = [(round(float(np.dot(np.array(g.coords[0]) - ax.C, ax.D)), 2), round(float(np.dot(np.array(g.coords[-1]) - ax.C, ax.D)), 2)) for g in (list(wat.geoms) if hasattr(wat, 'geoms') else [wat])]
        prof = np.array(wa[2 * k + 1][1]['prof']); ss = np.arange(s0, s1, 0.02)
        err = np.abs(np.interp(ss, prof[:, 0], prof[:, 1]) - np.array([tread_z(treads, s + 1e-9) for s in ss])).max()
        ends = [Point(*ax.xy(s, t)) for s in (prof[0, 0], prof[-1, 0]) for t in (-1.5, 0.0, 1.5)]
        free = all(world.land.contains(p) and not bl.contains(p) for p in ends)
        print(f'{name}: deck s = {s0:.2f}..{s1:.2f}, water on the centre line {segs} (s from the middle of the crossing); walk profile within {err:.3f} m of the treads; '
              f'profile ends 1 m beyond the feet on free land: {free}')
        for (poly, z), label in zip(wa[2 * k:2 * k + 2], ('footprint', 'lane')):
            print(f'    {label:9s} area {poly.area:6.1f} m2, in buildings {poly.intersection(bl).area:.2f}, over water {poly.difference(world.land).area:.1f}')


if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    check()
