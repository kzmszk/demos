"""Piazza San Marco: the small iconic details.

* the three flagpoles in front of the Basilica: Alessandro Leopardi's bronze bases (1505) on two-step Istrian
  plinths, the tall tapering masts with gilt finials and St Mark's red banners (gold lion patches) waving in
  a light breeze.  The row is derived from the Basilica's west front (basilica.FRONT_U / V_S / V_N through basilica.wf,
  so it follows the church's 3.5 deg turn): POLE_DIST = 6.9 m out from the front plane, POLE_SPACING = 14 m apart,
  the central pole on the main portal (piazza u ~ 30-31.5, v ~ 19.7 / 33.6 / 47.6);
* the white Istrian bands of the piazza paving: a calm grid aligned with the Procuratie Nuove (transverse bands every
  two arcade bays = 8.04 m, longitudinal bands 6.95 m apart) inside a double border 3 m inside the facades, clipped
  to the open piazza, clear of the Campanile / Loggetta (the grid keeps a hole of whole cells there) and of the
  flagpole plinths.  Strip pieces are <= 2 m long so place(max_edge=3) leaves them alone;
* the cast-iron three-lantern lamp posts: 6 along the Molo (6 m in front of the Doge's Palace south front, x = 55 ..
  140), 2 on the Loggetta terrace corners, 2 beside the two columns of the Piazzetta.

Everything is placed in world coordinates through the piazza frame (common.wf / pf).  API:
    build(mb, clip=None) -> dict     everything.  clip (shapely geometry in world xy, e.g. a tile box) restricts the
                                     output to the poles / lamps / paving pieces that stand inside it, so the piazza
                                     can be split over the 200 m tiles (see hero_entries)
    build_flagpoles(mb, clip=None), build_paving(mb, clip=None), build_lamps(mb, clip=None)    the three parts alone
    walk_areas() -> [(Polygon, None)]   plinths and lamp bases as blocked spots (world xy)
    hero_entries() -> [(anchor, fn)]    optional: ready-made entries for hero.HEROES, one per (part, tile)
    set_pole_sites(sites), osm_pole_stubs(world), OSM_POLE_SITES    explicit pole sites / the OSM-mapped pedestals
"""
import math
from functools import lru_cache
import numpy as np
from shapely import clip_by_rect, affinity
from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union
from vk import geom as G
from ..world import GROUND_Z, polys_of
from .common import wf, pf, PU, PV, place
from . import basilica as _basilica
from .procuratie import VECCHIE_LINE
from .campanile import frame_piazza
from .piazzetta import COL_MARCO, COL_TODARO, TORRE_LINE
from .ducale import SW as DUC_SW, SE as DUC_SE

ANG_U = math.atan2(PU[1], PU[0])          # world angle of the piazza u axis
ANG_V = math.atan2(PV[1], PV[0])


# ======================================================================================== helpers
def lathe_split(profile, seg, mat, sharp=38.0, center=(0, 0, 0)):
    """lathe whose smooth runs keep smooth shading while sharp profile corners (> `sharp` degrees) stay crisp
    (the profile is cut into separate lathes there, so no normals are averaged across the corner)."""
    out = G.Mesh()
    run = [profile[0]]
    for i in range(1, len(profile)):
        run.append(profile[i])
        if i < len(profile) - 1:
            a = np.subtract(profile[i], profile[i - 1]); b = np.subtract(profile[i + 1], profile[i])
            c = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
            if math.degrees(math.acos(max(-1.0, min(1.0, c)))) > sharp:
                out.merge(G.lathe(run, seg, mat=mat, center=center)); run = [profile[i]]
    if len(run) > 1: out.merge(G.lathe(run, seg, mat=mat, center=center))
    return out


def bead(r, z, h=0.05, d=0.035, seg=16, mat='bronze_gilt'):
    """small raised ring (bead) of height h and projection d on a surface of radius r at height z (embedded 4 cm)."""
    prof = [(r - 0.04, z - h / 2), (r + d, z - h * 0.2), (r + d, z + h * 0.2), (r - 0.04, z + h / 2)]
    return G.lathe(prof, seg, mat=mat)


def _interp(profile, z):
    p = np.asarray(profile, float)
    return float(np.interp(z, p[:, 1], p[:, 0]))


# ======================================================================================== 1. flagpoles
POLE_DIST = 6.9                            # m in front of the west front plane (the brief: u = 30.5 against the front at u = 37.4)
POLE_SPACING = 14.0                        # evenly spaced across the front, the central one on the main portal / nave axis
POLE_COUNT = 3
PLINTH_W = (2.6, 2.1)                      # the two Istrian steps (square)
PLINTH_H = 0.50
FLAG_L, FLAG_H = 3.2, 2.0
# per pole: wind direction (degrees off "toward -v"), wave phase, wave amplitude (m)
POLE_WIND = ((14.0, 0.0, 0.18), (7.0, 2.1, 0.15), (11.0, 4.0, 0.20))

# Leopardi's bronze base, plinth-top-relative (r, z): stepped foot, big lower belly, narrow waist, upper belly,
# abacus and a cone up to the mast collar.  3.0 m tall.
_PED = [
    (0.94, 0.00), (0.94, 0.10), (0.89, 0.13), (0.89, 0.20), (0.93, 0.24), (0.93, 0.30), (0.86, 0.35), (0.80, 0.40),     # foot
    (0.84, 0.50), (0.90, 0.66), (0.92, 0.84), (0.90, 1.00), (0.82, 1.14), (0.70, 1.24), (0.58, 1.32), (0.50, 1.40),     # lower belly
    (0.47, 1.50), (0.47, 1.62), (0.52, 1.72),                                                                          # waist
    (0.62, 1.84), (0.70, 1.98), (0.72, 2.12), (0.68, 2.26), (0.60, 2.36), (0.56, 2.44),                                  # upper belly
    (0.58, 2.50), (0.66, 2.53), (0.74, 2.58), (0.74, 2.70), (0.68, 2.74), (0.56, 2.78),                                  # abacus
    (0.42, 2.84), (0.32, 2.92), (0.27, 3.00),                                                                          # cone to the collar
]
# the mast: radius 0.17 -> 0.08 over 13.7 m (plinth-top-relative z)
_MAST = [(0.17, 3.0), (0.165, 4.5), (0.155, 6.5), (0.14, 8.8), (0.125, 11.2), (0.108, 13.6), (0.092, 15.4), (0.08, 16.7)]


def plinth():
    """two-step Istrian plinth, pavement-relative (0 .. 0.5)."""
    m = G.Mesh()
    side = ('+x', '-x', '+y', '-y', '+z')
    h1 = PLINTH_H / 2
    a = PLINTH_W[0] / 2; b = PLINTH_W[1] / 2
    m.merge(G.box(-a, -a, -0.08, a, a, h1, 'istrian', faces=side))
    m.merge(G.box(-b, -b, h1, b, b, PLINTH_H, 'istrian', faces=side))
    return m


def plaque(w, h):
    """relief panel in the local frame x = tangent, y = radial (outwards), z = up: bronze field, gilt frame, gilt rosette."""
    m = G.Mesh()
    f = ('+y', '+x', '-x', '+z', '-z')
    m.merge(G.box(-w / 2, -0.035, -h / 2, w / 2, 0.022, h / 2, 'bronze', faces=f))
    bw = 0.03
    for (x0, x1, z0, z1) in ((-w / 2, w / 2, h / 2 - bw, h / 2), (-w / 2, w / 2, -h / 2, -h / 2 + bw), (-w / 2, -w / 2 + bw, -h / 2, h / 2), (w / 2 - bw, w / 2, -h / 2, h / 2)):
        m.merge(G.box(x0, -0.035, z0, x1, 0.045, z1, 'bronze_gilt', faces=f))
    k = min(w, h) / 0.30
    m.merge(G.lathe([(0.075 * k, 0.0), (0.08 * k, 0.018), (0.045 * k, 0.05), (0.0, 0.062)], 8, mat='bronze_gilt').transformed(G.mat4((0, 0.022, 0), rx=-math.pi / 2)))
    return m


def pedestal():
    """Leopardi's bronze base (plinth-top-relative): lathe body, gilt rings, relief plaques on the two bellies."""
    m = G.Mesh()
    m.merge(lathe_split(_PED, 16, 'bronze'))
    for z in (0.33, 1.30, 1.56, 1.78, 2.40, 2.50, 2.72):                       # gilt mouldings at the transitions
        m.merge(bead(_interp(_PED, z), z, h=0.05, d=0.032))
    # relief plaques: a ring of eight on the lower belly (tritons), eight smaller on the upper (putti, garlands)
    for (z, w, h, n, a0) in ((0.80, 0.46, 0.40, 8, 0.0), (2.06, 0.30, 0.28, 8, math.pi / 8)):
        r = _interp(_PED, z)
        pl = plaque(w, h)
        for k in range(n):
            a = a0 + 2 * math.pi * k / n
            m.merge(pl.transformed(G.mat4((r * math.cos(a), r * math.sin(a), z), rz=a - math.pi / 2)))
    # mast collar
    m.merge(lathe_split([(0.25, 2.98), (0.25, 3.30), (0.21, 3.38), (0.175, 3.46)], 16, 'bronze'))
    m.merge(bead(0.25, 3.30, h=0.07, d=0.03))
    return m


def mast():
    """tapering wooden mast with bronze bands, a gilt truck, ball and spike (plinth-top-relative, tip at 17.5 = 18 m above the pavement)."""
    m = G.Mesh()
    m.merge(G.lathe(_MAST, 10, mat='wood_raw'))
    for z in (3.62, 14.3, 16.4):                                              # bronze bands (flag lashings at 14.3 / 16.4)
        m.merge(bead(_interp([(r, z) for r, z in _MAST], z) + 0.002, z, h=0.07, d=0.02, seg=10, mat='bronze'))
    m.merge(G.lathe([(0.08, 16.70), (0.12, 16.72), (0.17, 16.76), (0.17, 16.80), (0.12, 16.85), (0.07, 16.89), (0.05, 16.94), (0.05, 16.98)], 12, mat='bronze_gilt'))
    m.merge(G.lathe([(0.0, 16.97), (0.06, 16.99), (0.095, 17.04), (0.10, 17.10), (0.085, 17.16), (0.05, 17.20), (0.0, 17.21)], 10, mat='bronze_gilt'))
    m.merge(G.lathe([(0.03, 17.19), (0.012, 17.33), (0.0, 17.50)], 8, mat='bronze_gilt'))
    return m


def _lion():
    """the winged lion of St Mark as flat gold patches in banner coordinates (s along the fly, t up): a walking lion
    in profile facing the hoist, haloed head, raised wing, S-tail and the book under the paw, plus a gold fringe and
    thin gold borders."""
    c = (1.00, 1.36)
    halo = Point(*c).buffer(0.27, 6).difference(Point(*c).buffer(0.20, 6))
    head = unary_union([Point(*c).buffer(0.15, 5), Polygon([(0.80, 1.30), (0.90, 1.40), (0.90, 1.24)])])
    neck = Polygon([(1.08, 1.20), (1.30, 1.10), (1.36, 1.28), (1.14, 1.40)])
    body = Polygon([(1.28, 0.98), (1.34, 0.78), (1.62, 0.70), (2.00, 0.72), (2.34, 0.80), (2.46, 0.96), (2.36, 1.14), (1.96, 1.20), (1.54, 1.22), (1.34, 1.16)])
    wing = Polygon([(1.50, 1.16), (1.52, 1.46), (1.70, 1.70), (1.96, 1.84), (2.30, 1.86), (2.18, 1.66), (2.34, 1.62), (2.20, 1.44), (2.34, 1.36), (2.14, 1.22), (1.90, 1.18)])
    tail = Polygon([(2.42, 0.90), (2.60, 0.96), (2.68, 1.18), (2.62, 1.44), (2.50, 1.52), (2.46, 1.44), (2.54, 1.34), (2.54, 1.16), (2.40, 1.04)])
    legs = [Polygon([(1.30, 0.84), (1.48, 0.80), (1.46, 0.46), (1.28, 0.44)]), Polygon([(1.14, 0.88), (1.30, 0.84), (1.16, 0.62), (1.02, 0.68)]),
            Polygon([(2.08, 0.80), (2.28, 0.82), (2.34, 0.44), (2.16, 0.42)]), Polygon([(1.84, 0.74), (2.04, 0.74), (2.00, 0.44), (1.84, 0.42)])]
    book = Polygon([(0.80, 0.58), (1.06, 0.54), (1.12, 0.84), (0.86, 0.88)])
    fringe = Polygon([(FLAG_L - 0.08, 0.0), (FLAG_L, 0.0), (FLAG_L, FLAG_H), (FLAG_L - 0.08, FLAG_H)])
    edges = [Polygon([(0.0, 0.0), (FLAG_L, 0.0), (FLAG_L, 0.04), (0.0, 0.04)]), Polygon([(0.0, FLAG_H - 0.04), (FLAG_L, FLAG_H - 0.04), (FLAG_L, FLAG_H), (0.0, FLAG_H)])]
    return unary_union([halo, head, neck, body, wing, tail, book, fringe] + legs + edges)


def flag(r_mast, z_bottom, wind_deg, phase, amp, ns=20, nt=8):
    """St Mark's banner: a gently waving strip of quads, double-sided (two layers 1.2 cm apart, opposite windings),
    hoist on the mast (x = y = 0), flying toward -v turned by wind_deg.  Red 'velvet' with gold lion patches."""
    L, H = FLAG_L, FLAG_H
    a = math.radians(wind_deg) - math.pi / 2
    wd = np.array([math.cos(a), math.sin(a), 0.0]); nv = np.array([-wd[1], wd[0], 0.0])
    k = 2 * math.pi / 1.9

    def P(s, t):
        x = s / L
        d = amp * (0.12 + 0.88 * x ** 1.2) * (math.sin(k * s - phase + 0.9 * t) + 0.22 * math.sin(2.3 * k * s - 1.7 * phase + 0.4 * t))
        along = r_mast + 0.012 + s * (1.0 - 0.035 * x)
        sag = -0.16 * x * x * (0.75 + 0.25 * (1.0 - t / H))
        return np.array([wd[0] * along + nv[0] * d, wd[1] * along + nv[1] * d, z_bottom + t + sag])

    def N(s, t):
        e = 1e-3
        n = np.cross(P(s + e, t) - P(max(s - e, 0.0), t), P(s, t + e) - P(s, max(t - e, 0.0)))
        return n / np.linalg.norm(n)

    ss = np.linspace(0, L, ns + 1); tt = np.linspace(0, H, nt + 1)
    m = G.Mesh()
    for side, off in ((+1, 0.006), (-1, -0.006)):                              # front layer faces right of the flight direction
        o = m.add_v([P(s, t) + N(s, t) * off for t in tt for s in ss])
        for j in range(nt):
            for i in range(ns):
                q = o + j * (ns + 1) + i
                f = [q, q + 1, q + ns + 2, q + ns + 1]
                m.face(f if side > 0 else f[::-1], 'velvet', True)
    lion = _lion()
    for side, off in ((+1, 0.020), (-1, -0.020)):
        for j in range(nt):
            for i in range(ns):
                for q in polys_of(clip_by_rect(lion, ss[i], tt[j], ss[i + 1], tt[j + 1])):
                    if q.area < 1e-5: continue
                    cm = G.cap([list(q.exterior.coords)] + [list(h.coords) for h in q.interiors], 0.0, 'gold', True)
                    o = m.add_v([P(x, y) + N(x, y) * off for (x, y, _) in cm.V])
                    for f in cm.F: m.face([o + i2 for i2 in (f if side > 0 else f[::-1])], 'gold', True)
    return m


def flagpole(wind_deg, phase, amp):
    """one complete flagpole in its local frame (x = piazza u, y = piazza v, z = pavement-relative)."""
    m = plinth()
    up = G.mat4((0, 0, PLINTH_H))
    m.merge(pedestal().transformed(up))
    m.merge(mast().transformed(up))
    zt = 16.4 - FLAG_H                                                         # banner between the two lashings
    m.merge(flag(_interp([(r, z) for r, z in _MAST], zt + FLAG_H / 2), zt, wind_deg, phase, amp).transformed(up))
    return m


_POLE_OVERRIDE = None                      # [(u, v)] piazza coordinates, see set_pole_sites


def _front_uv():
    """the Basilica's west front in piazza (u, v), whatever frame basilica.py works in (it turned the church 3.5 deg off
    the piazza axis): (south end, north end, unit vector pointing from the front out into the piazza).  Falls back to the
    original plane u = 37.4, v = 10.2 .. 62.0 if basilica.py no longer offers FRONT_U / V_S / V_N / wf / PU."""
    try:
        B = _basilica
        s = np.array(pf(B.wf(B.FRONT_U, B.V_S))); n = np.array(pf(B.wf(B.FRONT_U, B.V_N)))
        out = -np.array([float(np.dot(B.PU, PU)), float(np.dot(B.PU, PV))])      # church -u, in piazza (u, v)
    except AttributeError:
        s, n, out = np.array([37.4, 10.2]), np.array([37.4, 62.0]), np.array([-1.0, 0.0])
    return s, n, out / np.linalg.norm(out)


def pole_sites():
    """[(world xy, rz)] of the flagpoles; the pole frame has x towards the Basilica, y along the front, so the plinths
    are square to the front (or to the piazza axes for the explicit sites of set_pole_sites)."""
    if _POLE_OVERRIDE is not None:
        return [(wf(u, v), ANG_U) for (u, v) in _POLE_OVERRIDE]
    s, n, out = _front_uv()
    d = (n - s) / np.linalg.norm(n - s)
    c = (s + n) / 2 + out * POLE_DIST
    w_in = -(PU * out[0] + PV * out[1])                                           # world direction towards the Basilica
    rz = math.atan2(w_in[1], w_in[0])
    return [(wf(*(c + d * (k - (POLE_COUNT - 1) / 2) * POLE_SPACING)), rz) for k in range(POLE_COUNT)]


# The OSM data maps the real pedestals as three tiny 'building=column' parts (0.4 m plinth + 0.6 m base) at these
# piazza (u, v): on the nave axis but about 25 m in front of the west front, i.e. ~18 m further out than POLE_DIST puts
# the poles.  They are generic buildings in the model right now.
OSM_POLE_SITES = ((10.6, 47.0), (12.3, 32.7), (14.0, 18.3))


def osm_pole_stubs(world, radius=3.0):
    """ids of the generic OSM 'column' parts at OSM_POLE_SITES; mark them hero (b.hero = True) to hide them when the
    hand-modelled flagpoles are used."""
    ws = [wf(u, v) for (u, v) in OSM_POLE_SITES]
    return [b.id for b in world.buildings if b.tags.get('building') == 'column'
            and any(math.hypot(b.poly.centroid.x - c[0], b.poly.centroid.y - c[1]) < radius for c in ws)]


def set_pole_sites(sites=None):
    """explicit flagpole sites [(u, v)] in the piazza frame (e.g. OSM_POLE_SITES), or None for the default row derived
    from the Basilica front (POLE_DIST / POLE_SPACING).  Clears the paving cache (the grid is centred on the central pole)."""
    global _POLE_OVERRIDE
    _POLE_OVERRIDE = None if sites is None else [(float(u), float(v)) for (u, v) in sites]
    paving.cache_clear()


def build_flagpoles(mb, clip=None):
    n = 0
    for k, (p, rz) in enumerate(pole_sites()):
        if clip is not None and not clip.contains(Point(*p)): continue
        wind, phase, amp = POLE_WIND[k % len(POLE_WIND)]
        place(mb, flagpole(wind, phase, amp), G.mat4((p[0], p[1], GROUND_Z), rz=rz))
        n += 1
    return n


# ======================================================================================== 2. paving bands
BAND_W = 0.32                       # white Istrian band
BAND_DZ = 0.015                     # above the pavement
BAND_Z = GROUND_Z + BAND_DZ
BORDER_OFF = 3.0                    # outer border line: 3 m inside the facades
BORDER_GAP = 0.55                   # clear pavement between the two border bands
GRID_V = 6.95                       # longitudinal bands (about 6.5 m; chosen so that every flagpole stands mid-field)
MIN_PIECE = 3.0                     # shorter band runs (stubs against the Campanile, flagpoles) are dropped
NUOVE = ((-142.3, -23.0), (-5.7, -18.7))      # Procuratie Nuove facade line (u, v); 34 bays of 4.02 m
ALA_U = -142.2                                # Ala Napoleonica
# Campanile + Loggetta: the OSM footprints reach v = -11, the hero models u = 16.4 (terrace) and v = +7.6
KEEP_SOFT = (-8.3, -13.5, 19.5, 9.5)          # grid bands stop here
KEEP_HARD = (-7.2, -11.8, 18.6, 8.2)          # nothing at all inside
PLINTH_CLEAR = 1.3 + 0.45                     # plinth half-side + room for the band


def _square(c, rz, h):
    """square of half-side h centred on the world point c, turned by rz."""
    co, si = math.cos(rz), math.sin(rz)
    return Polygon([(c[0] + co * a - si * b, c[1] + si * a + co * b) for (a, b) in ((-h, -h), (h, -h), (h, h), (-h, h))])


def _piazza_uv():
    """the open piazza as a convex polygon in (u, v): Nuove line (S, extended to the Basilica), Ala Napoleonica (W),
    Vecchie line + Torre dell'Orologio (N) and the Basilica's west front (E, 3.5 deg off the piazza's v axis)."""
    (ua, va), (ub, vb) = NUOVE
    sn = (vb - va) / (ub - ua)
    (u0, v0), (u1, v1) = VECCHIE_LINE
    sv = (v1 - v0) / (u1 - u0)
    tu, tv = pf(TORRE_LINE[1])
    fs, fn, _ = _front_uv()
    ke = (fn[0] - fs[0]) / (fn[1] - fs[1])                                       # du / dv of the front line
    u = float(fn[0])
    for _ in range(8): u = float(fn[0] + ke * (va + sn * (u - ua) - fn[1]))      # front line (extended south) x Nuove line (extended east)
    return [(ALA_U, va + sn * (ALA_U - ua)), (u, va + sn * (u - ua)), (float(fn[0]), float(fn[1])), (tu, tv), (u1, v1), (ALA_U, v0 + sv * (ALA_U - u0))]


@lru_cache(maxsize=1)
def _grid():
    """grid frame (s along the Nuove facade, t into the piazza), affine matrices to and from the world."""
    O = wf(*NUOVE[0]); B = wf(*NUOVE[1])
    L = float(np.linalg.norm(B - O)); Es = (B - O) / L; Et = np.array([-Es[1], Es[0]])
    to_w = [Es[0], Et[0], Es[1], Et[1], O[0], O[1]]
    to_g = [Es[0], Es[1], Et[0], Et[1], -float(Es @ O), -float(Et @ O)]
    bay2 = 2 * L / int(round(L / 4.02))                                         # two arcade bays = 8.04 m
    return to_w, to_g, bay2


def _world_poly(uv):
    return Polygon([tuple(wf(u, v)) for (u, v) in uv])


def _rect_uv(r):
    u0, v0, u1, v1 = r
    return _world_poly([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _ring_strip(poly):
    return LineString(list(poly.exterior.coords)).buffer(BAND_W / 2, cap_style=2, join_style=2, mitre_limit=6.0)


def _slice(g, h, off=0.37):
    """cut polygons (grid frame) into pieces of at most h x h along the grid axes (cuts at (i + off) * h)."""
    out = []
    for p in polys_of(g):
        x0, y0, x1, y1 = p.bounds
        for i in range(math.floor(x0 / h - off), math.ceil(x1 / h - off) + 1):
            for q in polys_of(clip_by_rect(p, (i + off) * h, y0 - 1, (i + 1 + off) * h, y1 + 1)):
                qx0, qy0, qx1, qy1 = q.bounds
                j0 = math.floor(qy0 / h - off); j1 = math.ceil(qy1 / h - off)
                if j1 - j0 <= 1: out.append(q); continue
                for j in range(j0, j1 + 1):
                    out.extend(polys_of(clip_by_rect(q, qx0 - 1, (j + off) * h, qx1 + 1, (j + 1 + off) * h)))
    return [q for q in out if q.area > 2e-4]


@lru_cache(maxsize=1)
def paving():
    """-> dict(pieces=[world-xy polygons, each <= ~2 m long], length=total band length, lines=(nlong, ntrans), ...)

    The bands are laid out in a grid frame (s along the Procuratie Nuove, t into the piazza): transverse bands every
    two arcade bays, longitudinal bands 6.95 m apart (centred on the central flagpole), a double border 3 m inside the
    facades.  Runs are clipped to the open piazza and to the keep-out zones; every run that ends at a keep-out is
    pulled back to the nearest crossing, so the Campanile / Loggetta stand in a hole made of whole grid cells."""
    to_w, to_g, bay2 = _grid()
    g = lambda geom: affinity.affine_transform(geom, to_g)
    w = lambda geom: affinity.affine_transform(geom, to_w)
    P0 = g(_world_poly(_piazza_uv()))
    ring_out = P0.buffer(-BORDER_OFF, join_style=2)
    ring_in = P0.buffer(-(BORDER_OFF + BAND_W + BORDER_GAP), join_style=2)
    soft = g(_rect_uv(KEEP_SOFT)); hard = g(_rect_uv(KEEP_HARD))
    sites = pole_sites()
    plinths = [g(_square(c, rz, PLINTH_CLEAR)) for (c, rz) in sites]
    obstacles_hard = unary_union([hard] + plinths)
    free = ring_in.difference(unary_union([soft] + plinths))
    edge = ring_in.exterior
    # transverse lines: not closer than 3.5 m to the west / 3 m to the east border (a narrow wedge of cell looks busy);
    # the inset corners of the P0 edges SW-NW (west) and SE-NE (east) give the border's extreme s
    corners = [min(list(ring_in.exterior.coords)[:-1], key=lambda c, q=q: (c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2) for q in list(P0.exterior.coords)[:-1]]
    s_lo = max(corners[0][0], corners[5][0]) + 3.5; s_hi = min(corners[1][0], corners[2][0]) - 3.0
    smin, tmin, smax, tmax = ring_in.bounds
    tc = g(Point(*sites[len(sites) // 2][0])).y                              # the grid is centred on the central flagpole
    t0 = tc + GRID_V / 2
    S_pos = [k * bay2 for k in range(1, 80) if s_lo <= k * bay2 <= s_hi]
    T_pos = [t0 + j * GRID_V for j in range(-40, 41) if tmin + 2.0 <= t0 + j * GRID_V < tmax]
    Tr = {}; Lg = {}                              # {line position: [[from, to], ...]} runs along the other axis
    for S in S_pos:
        runs = [sorted((c[1] for c in (seg.coords[0], seg.coords[-1]))) for seg in polys_of_lines(LineString([(S, tmin - 5), (S, tmax + 5)]).intersection(free))]
        Tr[S] = [r for r in runs if r[1] - r[0] >= MIN_PIECE]
    for T in T_pos:
        runs = [sorted((c[0] for c in (seg.coords[0], seg.coords[-1]))) for seg in polys_of_lines(LineString([(smin - 5, T), (smax + 5, T)]).intersection(free))]
        Lg[T] = [r for r in runs if r[1] - r[0] >= MIN_PIECE]
    cover = lambda D, pos, x: any(a - 1e-6 <= x <= b + 1e-6 for a, b in D.get(pos, []))
    at_edge = lambda s, t: edge.distance(Point(s, t)) < 1e-4
    for _ in range(8):                            # pull every free end back to the nearest crossing (ends on the border stay)
        changed = False
        for D, O, pt in ((Lg, Tr, lambda pos, x: (x, pos)), (Tr, Lg, lambda pos, x: (pos, x))):
            for pos, runs in D.items():
                out = []
                for a, b in runs:
                    cands = [q for q in sorted(O) if a - 1e-6 <= q <= b + 1e-6 and cover(O, q, pos)]
                    a2 = a if at_edge(*pt(pos, a)) else (cands[0] if cands else None)
                    b2 = b if at_edge(*pt(pos, b)) else (cands[-1] if cands else None)
                    if a2 is None or b2 is None or b2 - a2 < MIN_PIECE: changed = True; continue
                    changed |= abs(a2 - a) > 1e-6 or abs(b2 - b) > 1e-6
                    out.append([a2, b2])
                D[pos] = out
        if not changed: break
    lines = [LineString([(S, a), (S, b)]) for S, runs in Tr.items() for a, b in runs] + [LineString([(a, T), (b, T)]) for T, runs in Lg.items() for a, b in runs]
    grid = unary_union([ln.buffer(BAND_W / 2, cap_style=2) for ln in lines])
    border = unary_union([_ring_strip(ring_out), _ring_strip(ring_in)])
    bands = unary_union([border, grid]).difference(obstacles_hard)
    pieces = [w(p) for p in _slice(bands, 2.0)]
    return dict(pieces=pieces, length=sum(ln.length for ln in lines) + ring_out.exterior.length + ring_in.exterior.length,
                lines=(sum(len(r) for r in Lg.values()), sum(len(r) for r in Tr.values())), polygon=w(P0), border=(w(ring_out), w(ring_in)),
                keep=w(soft), grid_lines=[w(ln) for ln in lines])


def polys_of_lines(g):
    if g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    return [x for part in getattr(g, 'geoms', []) for x in polys_of_lines(part)]


def paving_mesh(clip=None):
    """upward-facing quads/triangles at BAND_Z ('trim'); degenerate slivers are dropped."""
    m = G.Mesh()
    n = 0
    for p in paving()['pieces']:
        if clip is not None and not clip.contains(p.representative_point()): continue
        cm = G.cap([list(p.exterior.coords)] + [list(r.coords) for r in p.interiors], BAND_Z, 'trim', True)
        V = cm.V; ok = []
        for f in cm.F:
            a, b, c = V[f[0]], V[f[1]], V[f[2]]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 2e-6: ok.append(f)
        if not ok: continue
        o = m.add_v(V)
        for f in ok: m.face([o + i for i in f], 'trim')
        n += 1
    return m, n


def build_paving(mb, clip=None):
    m, n = paving_mesh(clip)
    if n: place(mb, m, np.eye(4), max_edge=3.0)
    return n


# ======================================================================================== 3. lamp posts
MOLO_OFF = 6.0                                    # the Molo line: 6 m in front of the Doge's Palace south front
MOLO_X = tuple(55.0 + 17.0 * i for i in range(6))  # x = 55 ... 140


def lantern(k=1.0):
    """six-sided glass lantern, 0.62 m tall at k = 1: cast-iron tray, emissive-at-night panes, corner bars, bell cap, finial."""
    m = G.Mesh()
    m.merge(G.lathe([(0.0, 0.0), (0.08, 0.0), (0.17, 0.055), (0.185, 0.085), (0.185, 0.10), (0.0, 0.10)], 6, mat='cast_iron', smooth=False))
    m.merge(G.lathe([(0.145, 0.10), (0.155, 0.44)], 6, mat='street_glass', smooth=False))
    m.merge(G.lathe([(0.0, 0.44), (0.185, 0.44), (0.185, 0.465), (0.12, 0.53), (0.05, 0.60), (0.045, 0.61)], 6, mat='cast_iron', smooth=False))
    m.merge(G.lathe([(0.0, 0.60), (0.035, 0.615), (0.05, 0.64), (0.035, 0.665), (0.0, 0.68)], 6, mat='cast_iron', smooth=False))
    for i in range(6):
        a = math.pi / 3 * i
        x, y = 0.152 * math.cos(a), 0.152 * math.sin(a)
        m.merge(G.box(x - 0.011, y - 0.011, 0.10, x + 0.011, y + 0.011, 0.445, 'cast_iron', faces=('+x', '-x', '+y', '-y')))
    return m.transformed(G.mat4(s=k)) if k != 1.0 else m


_ARM = [(0.05, 0, 3.00), (0.20, 0, 2.97), (0.36, 0, 3.00), (0.50, 0, 3.10), (0.60, 0, 3.24), (0.64, 0, 3.40)]
_SQ = [(-0.0225, -0.0225), (0.0225, -0.0225), (0.0225, 0.0225), (-0.0225, 0.0225), (-0.0225, -0.0225)]


def lamp_post():
    """4.5 m cast-iron Venetian lamp post: stepped foot, vase pedestal, tapering shaft with collars, a bracket with two
    scrolled arms (lanterns at their ends) and the third lantern on top.  Arms run along local x; z = 0 at the base."""
    m = G.Mesh()
    side = ('+x', '-x', '+y', '-y', '+z')
    seg = 14
    m.merge(G.box(-0.26, -0.26, -0.05, 0.26, 0.26, 0.14, 'cast_iron', faces=side))
    m.merge(G.box(-0.20, -0.20, 0.14, 0.20, 0.20, 0.24, 'cast_iron', faces=side))
    ped = [(0.17, 0.24), (0.19, 0.28), (0.18, 0.33), (0.15, 0.38), (0.125, 0.46), (0.125, 0.54), (0.15, 0.62), (0.175, 0.70), (0.18, 0.76), (0.165, 0.84), (0.13, 0.90), (0.10, 0.95)]
    m.merge(lathe_split(ped, seg, 'cast_iron'))
    shaft = [(0.10, 0.95), (0.085, 1.05), (0.080, 2.0), (0.074, 2.9), (0.070, 3.05)]
    m.merge(G.lathe(shaft, seg, mat='cast_iron'))
    for z, r in ((1.05, 0.086), (1.55, 0.082), (2.45, 0.077)):
        m.merge(bead(r, z, h=0.05, d=0.03, seg=seg, mat='cast_iron'))
    m.merge(lathe_split([(0.07, 3.00), (0.12, 3.04), (0.13, 3.10), (0.09, 3.16), (0.06, 3.24), (0.055, 3.30), (0.055, 3.78)], seg, 'cast_iron'))
    for sgn in (1, -1):                                                             # the two scrolled arms
        path = [(sgn * x, y, z) for (x, y, z) in _ARM]
        m.merge(G.sweep(_SQ, path, 'cast_iron', caps=False))
        m.merge(lantern().transformed(G.mat4((sgn * 0.64, 0, 3.40))))
    m.merge(lantern(1.2).transformed(G.mat4((0, 0, 3.78))))                          # top lantern: 3.78 .. 4.52
    return m


def lamp_sites():
    """[(x, y, z_base, rz, tag)]: 6 on the Molo line, 2 on the Loggetta terrace corners, 2 by the columns."""
    out = []
    d = (DUC_SE - DUC_SW) / np.linalg.norm(DUC_SE - DUC_SW); n = np.array([d[1], -d[0]])     # n: toward the water
    rz = math.atan2(d[1], d[0])
    base = DUC_SW + n * MOLO_OFF
    for x in MOLO_X:
        p = base + d * ((x - base[0]) / d[0])
        out.append((float(p[0]), float(p[1]), GROUND_Z, rz, 'molo'))
    Ml = frame_piazza(10.0, -7.6, math.pi / 2)                                       # the Loggetta kit frame (campanile.build)
    for x in (0.8, 14.4):                                                            # inside the corner piers of the terrace balustrade
        p = Ml @ np.array([x, -5.7, 0.85, 1.0])
        out.append((float(p[0]), float(p[1]), float(p[2]), ANG_V, 'loggetta'))
    c = (COL_MARCO - COL_TODARO) / np.linalg.norm(COL_MARCO - COL_TODARO); nc = np.array([c[1], -c[0]])
    rc = math.atan2(c[1], c[0])
    for col, sg in ((COL_MARCO, 1.0), (COL_TODARO, -1.0)):                           # on the lagoon side, flanking the gap between the columns
        p = col + nc * 6.0 + c * (3.0 * sg)
        out.append((float(p[0]), float(p[1]), GROUND_Z, rc, 'columns'))
    return out


def build_lamps(mb, clip=None):
    post = lamp_post()
    n = 0
    for (x, y, z, rz, tag) in lamp_sites():
        if clip is not None and not clip.contains(Point(x, y)): continue
        place(mb, post, G.mat4((x, y, z), rz=rz)); n += 1
    return n


# ======================================================================================== API
def build(mb, clip=None):
    nf = build_flagpoles(mb, clip)
    nb = build_paving(mb, clip)
    nl = build_lamps(mb, clip)
    pv = paving()
    return dict(flagpoles=nf, bands=nb, band_length=round(pv['length']), band_lines=pv['lines'], lamps=nl)


def walk_areas():
    """blocked spots: the flagpole plinths (2.8 m squares, piazza-aligned) and the lamp-post bases (0.6 m squares)."""
    out = []
    for c, rz in pole_sites():
        out.append((_square(c, rz, 1.4), None))
    for (x, y, z, rz, tag) in lamp_sites():
        c, s = math.cos(rz), math.sin(rz)
        out.append((Polygon([(x + c * a - s * b, y + s * a + c * b) for (a, b) in ((-0.3, -0.3), (0.3, -0.3), (0.3, 0.3), (-0.3, 0.3))]), None))
    return out


# the 200 m tile grid of build_tiles.py (hero builders run for the tile that holds their anchor)
TILE, TILE_X0, TILE_Y0 = 200.0, -3400.0, -1600.0


def _tile_of(x, y):
    return int((x - TILE_X0) // TILE), int((y - TILE_Y0) // TILE)


def _tile_box(i, j):
    return sbox(TILE_X0 + i * TILE, TILE_Y0 + j * TILE, TILE_X0 + (i + 1) * TILE, TILE_Y0 + (j + 1) * TILE)


def hero_entries():
    """[(anchor world xy, fn(mb, inst) -> dict)] for hero.HEROES, one entry per (part, tile): the poles, the lamps and
    the paving pieces each go into the tile they stand in.  Anchors lie inside their tile."""
    out = []
    groups = {}
    for p, rz in pole_sites(): groups.setdefault(('flagpoles', _tile_of(*p)), []).append((float(p[0]), float(p[1])))
    for (x, y, z, rz, tag) in lamp_sites(): groups.setdefault(('lamps', _tile_of(x, y)), []).append((x, y))
    for piece in paving()['pieces']:
        c = piece.representative_point(); groups.setdefault(('paving', _tile_of(c.x, c.y)), []).append((c.x, c.y))
    fns = dict(flagpoles=build_flagpoles, paving=build_paving, lamps=build_lamps)
    for (part, (i, j)), pts in sorted(groups.items()):
        R = _tile_box(i, j)
        out.append((pts[0], lambda mb, inst, R=R, f=fns[part], part=part: {part: f(mb, R)}))
    return out
