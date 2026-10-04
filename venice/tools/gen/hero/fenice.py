"""Teatro La Fenice: the neoclassical front on Campo San Fantin (Selva, 1792: Corinthian pronaos with a terrace,
statues of Tragedy and Comedy in niches, the SOCIETAS MDCCXCII attic), the foyer and a corridor to the hall, and
the horseshoe auditorium: four tiers of boxes and the loggione, gilt parapets with painted panels (photo crops
from the hall itself), the royal box, the painted ceiling with its rosette and crystal chandelier, the gilded
proscenium with the red curtain, and the stalls.

Hall frame from the OSM parts: origin = centre of the proscenium line, s from the stage toward the back of the
hall, t to the left (facing the back), z absolute."""
import json, math, os
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import facade_frame, place, translate
from .basilica import statue

ART = json.load(open('/home/kazu/work/demos/venice/public/tex/art.json'))['items'] if os.path.exists('/home/kazu/work/demos/venice/public/tex/art.json') else {}
O = np.array([-447.1, -70.55]); X = np.array([0.906, 0.425]); X /= np.linalg.norm(X); Y = np.array([-X[1], X[0]])
R = 8.4; LS = 12.0; SBACK = LS + R                    # horseshoe: straight sides to s=LS, semicircle to s=LS+R
S0 = 0.8                                             # box fronts start just behind the proscenium
ZST = GROUND_Z + 0.35                                # stalls floor
TIERS = [ZST + 2.35 + 2.5 * k for k in range(5)]     # four box tiers + the loggione
ZC = TIERS[4] + 3.2                                  # ceiling
DEPTH = 2.3                                          # box depth behind the parapet
STONE = 'trim'

def T(s, t, z):
    p = O + X * s + Y * t; return (float(p[0]), float(p[1]), float(z))
def T2(s, t): p = O + X * s + Y * t; return (float(p[0]), float(p[1]))
def nst(ds, dt): v = X * ds + Y * dt; return (float(v[0]), float(v[1]), 0.0)

def quad(m, pts, want, mat, uv=None):
    P = np.array(pts, float); n = np.cross(P[1] - P[0], P[2] - P[0])
    if np.dot(n, want) >= 0: m.poly(pts, mat, uv=uv)
    else: m.poly(pts[::-1], mat, uv=uv[::-1] if uv else None)

def path(off=0.0, n_arc=40):
    """box-front line around the hall (left side forward, round the back, right side back), offset outward."""
    r = R + off; pts = []
    for s in np.linspace(S0, LS, 6): pts.append((s, r))
    for a in np.linspace(math.pi / 2, -math.pi / 2, n_arc + 1)[1:-1]: pts.append((LS + r * math.cos(a), r * math.sin(a)))
    for s in np.linspace(LS, S0, 6): pts.append((s, -r))
    out = []; acc = 0.0
    for i, p in enumerate(pts):
        if i: acc += math.dist(p, pts[i - 1])
        out.append((p[0], p[1], acc))
    return out

def outward(s, t):
    """unit outward direction (in s,t) of the horseshoe at a path point."""
    if s <= LS + 1e-6: return (0.0, 1.0 if t > 0 else -1.0)
    d = np.array([s - LS, t]); d /= np.linalg.norm(d); return (float(d[0]), float(d[1]))

# ------------------------------------------------------------------ the hall
def band(m, z0, z1, off, mat, face_in=True, art=None, period=4.6):
    """vertical band along the path at offset `off`, from z0 to z1; facing the hall (inward) or outward."""
    P = path(off)
    for i in range(len(P) - 1):
        (s0, t0, a0), (s1, t1, a1) = P[i], P[i + 1]
        o = outward((s0 + s1) / 2, (t0 + t1) / 2)
        want = nst(-o[0], -o[1]) if face_in else nst(o[0], o[1])
        pts = [T(s0, t0, z0), T(s1, t1, z0), T(s1, t1, z1), T(s0, t0, z1)]
        uv = [(a0 / period, 0.0), (a1 / period, 0.0), (a1 / period, 1.0), (a0 / period, 1.0)] if art else None
        quad(m, pts, want, mat, uv)

def ring_floor(m, z, off0, off1, mat, up=True):
    """horizontal ring between two path offsets (box floors/ceilings, parapet tops)."""
    A_, B_ = path(off0), path(off1)
    for i in range(len(A_) - 1):
        pts = [T(A_[i][0], A_[i][1], z), T(A_[i + 1][0], A_[i + 1][1], z), T(B_[i + 1][0], B_[i + 1][1], z), T(B_[i][0], B_[i][1], z)]
        quad(m, pts, (0, 0, 1 if up else -1), mat)

def hall(arts):
    m = G.Mesh()
    # stalls floor: a rectangle up to the start of the curve + a fan for the semicircle
    quad(m, [T(0.0, -R, ZST), T(LS, -R, ZST), T(LS, R, ZST), T(0.0, R, ZST)], (0, 0, 1), 'parquet')
    for k in range(24):
        a0, a1 = -math.pi / 2 + math.pi * k / 24, -math.pi / 2 + math.pi * (k + 1) / 24
        quad(m, [T(LS, 0, ZST), T(LS + R * math.cos(a0), R * math.sin(a0), ZST), T(LS + R * math.cos(a1), R * math.sin(a1), ZST)], (0, 0, 1), 'parquet')
    # stall seats: rows of red velvet chairs, side aisles free
    for s in np.arange(4.2, 17.3, 0.95):
        half = min(5.6, (R - 1.6) if s < LS else math.sqrt(max(0.0, (R - 1.6) ** 2 - (s - LS) ** 2)))
        for t in np.arange(-half, half + 0.01, 0.56):
            seat = G.Mesh()
            seat.merge(G.box(-0.22, -0.24, 0.0, 0.22, 0.24, 0.44, 'velvet'))
            seat.merge(G.box(0.18, -0.24, 0.44, 0.28, 0.24, 0.98, 'velvet'))
            seat.merge(G.box(-0.24, -0.27, 0.0, 0.3, -0.24, 0.62, 'gilt')); seat.merge(G.box(-0.24, 0.24, 0.0, 0.3, 0.27, 0.62, 'gilt'))
            M = np.eye(4); M[:3, 0] = (X[0], X[1], 0); M[:3, 1] = (Y[0], Y[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = T(s, t, ZST)
            m.merge(seat.transformed(M))
    # tiers: parapets with painted panels, gilt rails, box openings with dividers, box interiors, lamps
    for k, zf in enumerate(TIERS):
        zp0, zp1 = zf - 0.35, zf + 1.02
        key = 'fen_par_a' if k % 2 == 0 else 'fen_par_b'
        pm = G.Mesh(); band(pm, zp0 + 0.12, zp1 - 0.1, 0.0, 'painting', art=True, period=4.6); arts.append((pm, key))
        band(m, zp1 - 0.1, zp1 + 0.06, -0.06, 'gilt')                      # gilt rail (front)
        ring_floor(m, zp1 + 0.06, -0.06, 0.25, 'velvet')                  # padded rail top
        band(m, zp0, zp0 + 0.12, -0.04, 'gilt')                            # bottom moulding
        ring_floor(m, zp0, -0.04, DEPTH, 'cream', up=False)                # soffit under the box floor
        ring_floor(m, zf, 0.25, DEPTH, 'parquet')                          # box floor
        top = (TIERS[k + 1] - 0.35) if k < 4 else ZC - 0.6
        ring_floor(m, top - 0.02, 0.0, DEPTH, 'cream', up=False)           # box ceiling
        band(m, zf, top, DEPTH, 'velvet')                                  # box back wall (red damask)
        # dividers between boxes: gilt pilaster faces on the front line + red partitions
        Pth = path(0.0); L = Pth[-1][2]; nb = max(8, int(L / (1.7 if k < 4 else 3.4)))
        for j in range(nb + 1):
            a = L * j / nb
            for q in range(len(Pth) - 1):
                if Pth[q][2] <= a <= Pth[q + 1][2]: break
            f = (a - Pth[q][2]) / max(1e-6, Pth[q + 1][2] - Pth[q][2])
            s = Pth[q][0] + (Pth[q + 1][0] - Pth[q][0]) * f; t = Pth[q][1] + (Pth[q + 1][1] - Pth[q][1]) * f
            o = outward(s, t); tg = (-o[1], o[0])
            w = 0.11
            c = [(s - tg[0] * w, t - tg[1] * w), (s + tg[0] * w, t + tg[1] * w)]
            # pilaster (front) and partition (to the back wall)
            for (z0, z1) in ((zp1 + 0.06, top),):
                quad(m, [T(c[0][0], c[0][1], z0), T(c[1][0], c[1][1], z0), T(c[1][0], c[1][1], z1), T(c[0][0], c[0][1], z1)], nst(-o[0], -o[1]), 'gilt')
                if k < 4:
                    back = [(c[0][0] + o[0] * DEPTH, c[0][1] + o[1] * DEPTH), (c[1][0] + o[0] * DEPTH, c[1][1] + o[1] * DEPTH)]
                    for side in (0, 1):
                        nrm = nst(tg[0] * (1 if side else -1), tg[1] * (1 if side else -1))
                        quad(m, [T(c[side][0], c[side][1], z0), T(back[side][0], back[side][1], z0), T(back[side][0], back[side][1], z1), T(c[side][0], c[side][1], z1)], nrm, 'velvet')
            # a pair of small lamps on each pilaster
            if j % 1 == 0 and k < 4:
                lz = zp1 + 0.55
                for d in (-0.12, 0.12):
                    px, py = s - o[0] * 0.12 + tg[0] * d, t - o[1] * 0.12 + tg[1] * d
                    m.merge(G.lathe([(0.0, 0), (0.05, 0.02), (0.06, 0.1), (0.035, 0.16), (0.0, 0.17)], 8, mat='lamp_glass').transformed(G.mat4(T(px, py, lz))))
    # ground level under the first tier: the stalls' back wall (cream) with a doorway at the centre back
    band(m, ZST, TIERS[0] - 0.35, 0.3, 'cream')
    # royal box: projecting gilt frame over tiers 1-2 at the back, red drapery, crown
    rb = SBACK + 0.0
    m.merge(_box_st(rb - 0.35, -2.2, TIERS[0] - 0.4, rb + 0.2, 2.2, TIERS[2] - 0.3, 'gilt'))
    m.merge(_box_st(rb - 0.3, -1.7, TIERS[0] + 1.0, rb - 0.15, 1.7, TIERS[2] - 0.7, 'velvet'))
    m.merge(G.lathe([(0.0, 0), (0.6, 0.1), (0.55, 0.5), (0.7, 0.9), (0.0, 1.2)], 10, mat='gilt').transformed(G.mat4(T(rb - 0.3, 0.0, TIERS[2] - 0.3))))
    # ceiling: cove from the loggione to the flat painted ceiling
    ring_floor(m, ZC - 0.6, 0.0, DEPTH, 'cream', up=False)
    Pi, Po = path(-0.9), path(0.0)
    for i in range(len(Pi) - 1):
        pts = [T(Po[i][0], Po[i][1], ZC - 0.6), T(Po[i + 1][0], Po[i + 1][1], ZC - 0.6), T(Pi[i + 1][0], Pi[i + 1][1], ZC), T(Pi[i][0], Pi[i][1], ZC)]
        o = outward(Pi[i][0], Pi[i][1])
        quad(m, pts, (-o[0] * X[0] - o[1] * Y[0], -o[0] * X[1] - o[1] * Y[1], -1.0), 'gilt')
    cm = G.Mesh()
    poly = G.ccw([(p[0], p[1]) for p in path(-0.9)] + [(S0, -(R - 0.9)), (0.4, -(R - 0.9)), (0.4, R - 0.9), (S0, R - 0.9)])
    for (a, b, c) in G.tess([poly]):
        pts = [T(poly[i][0], poly[i][1], ZC) for i in (a, b, c)]
        uv = [ceiling_uv(poly[i][0], poly[i][1]) for i in (a, b, c)]
        quad(cm, pts, (0, 0, -1), 'painting', uv)
    arts.append((cm, 'fen_ceiling'))
    # rosette and chandelier
    cs = 11.5
    m.merge(G.lathe([(0.0, 0.0), (1.6, 0.0), (1.4, -0.12), (0.6, -0.3), (0.0, -0.35)], 16, mat='gilt').transformed(G.mat4(T(cs, 0, ZC - 0.01))))
    m.merge(G.box(-0.03, -0.03, -3.0, 0.03, 0.03, 0.0, 'gilt').transformed(G.mat4(T(cs, 0, ZC))))
    zc0 = ZC - 4.6
    m.merge(G.lathe([(0.0, 0), (0.35, 0.1), (0.5, 0.7), (0.3, 1.4), (0.08, 1.7)], 12, mat='gilt').transformed(G.mat4(T(cs, 0, zc0))))
    for ring, (rr, zz, nbulb) in enumerate(((1.5, 0.35, 18), (1.05, 0.9, 12), (0.65, 1.4, 8))):
        for j in range(nbulb):
            a = 2 * math.pi * (j + 0.5 * ring) / nbulb
            bx, by = cs + rr * math.cos(a), rr * math.sin(a)
            m.merge(G.box(-0.015, -0.015, -0.02, 0.015, 0.015, 0.02, 'gilt').transformed(G.mat4(T(bx, by, zc0 + zz))))
            m.merge(G.lathe([(0.0, 0), (0.05, 0.02), (0.065, 0.1), (0.0, 0.16)], 8, mat='lamp_glass').transformed(G.mat4(T(bx, by, zc0 + zz))))
        # crystal swags: thin gilt rings
        for j in range(24):
            a0, a1 = 2 * math.pi * j / 24, 2 * math.pi * (j + 1) / 24
            p0, p1 = T(cs + rr * math.cos(a0), rr * math.sin(a0), zc0 + zz - 0.12), T(cs + rr * math.cos(a1), rr * math.sin(a1), zc0 + zz - 0.12)
            quad(m, [p0, p1, (p1[0], p1[1], p1[2] + 0.05), (p0[0], p0[1], p0[2] + 0.05)], (0, 0, 0.0001) if False else nst(math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2)), 'gilt')
    # proscenium: wall with the opening, gilded frame, valance and the closed red curtain
    zs = ZST + 1.2                                    # stage floor
    ow, oh = 6.3, 10.5
    outline = [(-(R + DEPTH), ZST), (R + DEPTH, ZST), (R + DEPTH, ZC), (-(R + DEPTH), ZC)]
    hole = [(-ow, zs), (ow, zs), (ow, zs + oh), (-ow, zs + oh)]
    loops = [G.ccw(outline), G.ccw(hole)[::-1]]; flat = loops[0] + loops[1]
    for (a, b, c) in G.tess(loops):
        quad(m, [T(0.0, flat[i][0], flat[i][1]) for i in (a, b, c)], nst(1, 0), 'cream')
    for (t0, t1, z0, z1) in ((ow, ow + 1.0, zs, zs + oh + 1.4), (-ow - 1.0, -ow, zs, zs + oh + 1.4), (-ow - 1.0, ow + 1.0, zs + oh, zs + oh + 1.4)):
        m.merge(_box_st(0.0, t0, z0, 0.35, t1, z1, 'gilt'))
    m.merge(G.lathe([(0.0, 0), (0.9, 0.1), (0.7, 0.8), (0.0, 1.1)], 10, mat='gilt').transformed(G.mat4(T(0.3, 0.0, zs + oh + 1.3))))
    # stage front and floor
    quad(m, [T(0.0, -ow, ZST), T(0.0, ow, ZST), T(0.0, ow, zs), T(0.0, -ow, zs)], nst(1, 0), 'walnut')
    quad(m, [T(-1.6, -ow, zs), T(0.0, -ow, zs), T(0.0, ow, zs), T(-1.6, ow, zs)], (0, 0, 1), 'parquet')
    # curtain: red velvet in folds, a valance with a gold fringe
    nf = 40
    for j in range(nf):
        ta, tb = -ow + 2 * ow * j / nf, -ow + 2 * ow * (j + 1) / nf
        da, db = -0.9 + 0.12 * math.sin(j * 1.9), -0.9 + 0.12 * math.sin((j + 1) * 1.9)
        quad(m, [T(da, ta, zs), T(db, tb, zs), T(db, tb, zs + oh), T(da, ta, zs + oh)], nst(1, 0), 'velvet')
    for j in range(nf):
        ta, tb = -ow + 2 * ow * j / nf, -ow + 2 * ow * (j + 1) / nf
        da, db = -0.45 + 0.08 * math.sin(j * 2.3), -0.45 + 0.08 * math.sin((j + 1) * 2.3)
        sag = lambda t: 1.6 + 0.45 * math.cos(math.pi * ((t + ow) / (2 * ow / 5.0) % 1.0) * 2) * 0.5
        quad(m, [T(da, ta, zs + oh - sag(ta)), T(db, tb, zs + oh - sag(tb)), T(db, tb, zs + oh), T(da, ta, zs + oh)], nst(1, 0), 'velvet')
        quad(m, [T(da + 0.02, ta, zs + oh - sag(ta) - 0.12), T(db + 0.02, tb, zs + oh - sag(tb) - 0.12), T(db + 0.02, tb, zs + oh - sag(tb)), T(da + 0.02, ta, zs + oh - sag(ta))], nst(1, 0), 'gilt')
    # the stage house behind the curtain (dark), so nothing outside shows round the curtain
    for (a, b, c, d, want) in (((-1.0, -9.0, ZST), (-12.0, -9.0, ZST), (-12.0, -9.0, ZC + 4), (-1.0, -9.0, ZC + 4), (0, 1)),
                               ((-1.0, 9.0, ZST), (-12.0, 9.0, ZST), (-12.0, 9.0, ZC + 4), (-1.0, 9.0, ZC + 4), (0, -1)),
                               ((-12.0, -9.0, ZST), (-12.0, 9.0, ZST), (-12.0, 9.0, ZC + 4), (-12.0, -9.0, ZC + 4), (1, 0))):
        quad(m, [T(*a), T(*b), T(*c), T(*d)], nst(*want), 'dark')
    quad(m, [T(-12.0, -9.0, ZC + 4), T(-1.0, -9.0, ZC + 4), T(-1.0, 9.0, ZC + 4), T(-12.0, 9.0, ZC + 4)], (0, 0, -1), 'dark')
    quad(m, [T(-12.0, -9.0, zs), T(-1.6, -9.0, zs), T(-1.6, 9.0, zs), T(-12.0, 9.0, zs)], (0, 0, 1), 'dark')
    # proscenium boxes (two each side, between the proscenium and the horseshoe)
    for sgn in (-1, 1):
        for k in range(4):
            zf = TIERS[k]
            m.merge(_box_st(0.35, sgn * (ow + 1.0) - (0 if sgn > 0 else 0), zf - 0.35, S0 + 0.05, sgn * (R + 0.0), zf + 1.02, 'gilt'))
    return m

def ceiling_uv(s, t):
    """planar mapping of the photograph of the ceiling (taken from the stalls looking up toward the back)."""
    x = 0.494 - (t / R) * 0.5
    y = 0.02 + (s - S0) / (11.5 - S0) * (0.425 - 0.02) if s < 11.5 else 0.425 + (s - 11.5) / (SBACK - 11.5) * (0.56 - 0.425)
    asp = ART['fen_ceiling']['aspect'] if 'fen_ceiling' in ART else 1.333
    return (min(1.0, max(0.0, x)), min(1.0, max(0.0, 1.0 - y * asp)))

def _box_st(s0, t0, z0, s1, t1, z1, mat):
    m = G.Mesh()
    sa, sb = min(s0, s1), max(s0, s1); ta, tb = min(t0, t1), max(t0, t1)
    P = [T(sa, ta, z0), T(sb, ta, z0), T(sb, tb, z0), T(sa, tb, z0), T(sa, ta, z1), T(sb, ta, z1), T(sb, tb, z1), T(sa, tb, z1)]
    o = m.add_v(P)
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        m.face([o + i for i in q], mat)
    return m

# ------------------------------------------------------------------ foyer + corridor
FAC_S = np.array([-395.0, -47.8]); FAC_N = np.array([-402.4, -27.9]); FAC_NORM = np.array([0.938, 0.349])
def fac_frame():
    return facade_frame(FAC_S, FAC_N, FAC_NORM)

def kitw(M, x, y, z=0.0):
    v = M @ np.array([x, y, z, 1.0]); return (float(v[0]), float(v[1]))

def foyer(M):
    """kit coords of the facade frame: x along the front (S->N), +y into the building."""
    m = G.Mesh()
    x0, x1, y0, y1, h = 3.0, 18.2, 0.6, 9.4, 6.4
    m.merge(G.box(x0, y0, -0.02, x1, y1, 0.0, 'basilica_floor', faces=('+z',)))
    m.merge(G.box(x0, y0, h, x1, y1, h + 0.02, 'cream', faces=('-z',)))
    for (a, b, c, d, want) in (((x0, y0), (x0, y1), None, None, (1, 0)), ((x1, y0), (x1, y1), None, None, (-1, 0))):
        quad(m, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], h), (a[0], a[1], h)], (want[0], want[1], 0), 'cream')
    # front wall (inside face) with the three doors; back wall with the doorway to the corridor
    for (yy, want, doors) in ((y0, (0, 1), (8.0, 10.6, 13.2)), (y1, (0, -1), (10.6,))):
        outline = [(x0, 0.0), (x1, 0.0), (x1, h), (x0, h)]
        holes = [[(dx - 0.8, 0.0), (dx + 0.8, 0.0), (dx + 0.8, 3.6), (dx - 0.8, 3.6)] for dx in doors]
        loops = [G.ccw(outline)] + [G.ccw(hh)[::-1] for hh in holes]; flat = [p for l in loops for p in l]
        for (a, b, c) in G.tess(loops):
            quad(m, [(flat[i][0], yy, flat[i][1]) for i in (a, b, c)], (want[0], want[1], 0), 'cream')
    m.merge(A.straight(A.cornice_profile(0.35, 0.3), x0, x1, h - 0.35, y1 - 0.01, 'gilt'))
    for x in (6.6, 14.6):
        for y in (3.4, 6.6):
            m.merge(A.column(0.55, h, order='ionic', mat='marble_white', seg=10).transformed(G.mat4((x, y, 0))))
    for x in (7.5, 13.7):
        m.merge(G.box(x - 0.02, 5.0 - 0.02, h - 1.4, x + 0.02, 5.0 + 0.02, h, 'gilt'))
        for j in range(8):
            a = 2 * math.pi * j / 8
            m.merge(G.lathe([(0.0, 0), (0.05, 0.02), (0.06, 0.1), (0.0, 0.15)], 8, mat='lamp_glass').transformed(G.mat4((x + 0.5 * math.cos(a), 5.0 + 0.5 * math.sin(a), h - 1.5))))
    return m

def corridor_line():
    M, L, fl = fac_frame()
    a = kitw(M, 10.6, 9.4); b = T2(SBACK + DEPTH + 0.6, 0.0)
    return np.array(a), np.array(b)

def corridor():
    a, b = corridor_line(); d = b - a; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    m = G.Mesh(); w = 1.5; h = 4.2; z0 = GROUND_Z
    P = lambda s, t, z: (float(a[0] + d[0] * s + n[0] * t), float(a[1] + d[1] * s + n[1] * t), z)
    quad(m, [P(0, -w, z0), P(L, -w, z0), P(L, w, z0), P(0, w, z0)], (0, 0, 1), 'parquet')
    quad(m, [P(0, -w, z0 + h), P(L, -w, z0 + h), P(L, w, z0 + h), P(0, w, z0 + h)], (0, 0, -1), 'cream')
    for sgn in (-1, 1):
        quad(m, [P(0, sgn * w, z0), P(L, sgn * w, z0), P(L, sgn * w, z0 + h), P(0, sgn * w, z0 + h)], (-n[0] * sgn, -n[1] * sgn, 0), 'cream')
        quad(m, [P(0, sgn * w * 0.99, z0), P(L, sgn * w * 0.99, z0), P(L, sgn * w * 0.99, z0 + 1.0), P(0, sgn * w * 0.99, z0 + 1.0)], (-n[0] * sgn, -n[1] * sgn, 0), 'walnut')
    for s in np.arange(3.0, L - 1.0, 5.0):
        c = P(s, 0, z0 + h - 0.05)
        m.merge(G.lathe([(0.0, 0), (0.18, 0.0), (0.22, -0.12), (0.0, -0.2)], 10, mat='lamp_glass').transformed(G.mat4(c)))
    return m

# ------------------------------------------------------------------ the front on Campo San Fantin
def front():
    """kit: x along the facade from the south end, facade faces -y, z from the campo."""
    m = G.Mesh(); W = float(np.linalg.norm(FAC_N - FAC_S)); H = 18.7
    ops = []
    for x in (2.8, W - 2.8):
        ops.append([(x - 0.75, 1.2), (x + 0.75, 1.2), (x + 0.75, 3.7), (x - 0.75, 3.7)])          # ground windows
        ops.append([(x - 0.75, 9.6), (x + 0.75, 9.6), (x + 0.75, 12.4), (x - 0.75, 12.4)])        # piano nobile
        ops.append([(x - 0.5, 15.2), (x + 0.5, 15.2), (x + 0.5, 16.2), (x - 0.5, 16.2)])          # attic
    for dx in (8.0, 10.6, 13.2): ops.append([(dx - 0.8, 0.0), (dx + 0.8, 0.0), (dx + 0.8, 3.6), (dx - 0.8, 3.6)])
    ops.append([(W / 2 - 0.95, 8.4), (W / 2 + 0.95, 8.4), (W / 2 + 0.95, 12.0), (W / 2 - 0.95, 12.0)])
    m.merge(G.wall(W, H, 0.6, STONE, openings=ops, back=False, sides=True, top=True))
    for o in ops:
        xs = [p[0] for p in o]; zs = [p[1] for p in o]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        m.merge(G.box(x0 - 0.15, -0.1, z0 - 0.12, x1 + 0.15, 0.0, z0, STONE)); m.merge(G.box(x0 - 0.15, -0.1, z1, x1 + 0.15, 0.0, z1 + 0.15, STONE))
        m.merge(G.box(x0 - 0.15, -0.1, z0, x0, 0.0, z1, STONE)); m.merge(G.box(x1, -0.1, z0, x1 + 0.15, 0.0, z1, STONE))
        door = z0 < 0.5
        if not (door and abs((x0 + x1) / 2 - 10.6) < 0.1):
            m.merge(A.fix_orient(G.cap([o], 0, 'glass' if not door else 'shop_wood', True, G.frame((0, 0.35, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    for x in (2.8, W - 2.8):
        m.merge(A.pediment_tri(x - 1.05, x + 1.05, 12.55, 0.7, 0.3, 0.12, 0.22, STONE, y=-0.12))
    # rusticated ground storey bands, string courses, main cornice
    for z in (4.6, 8.1, 14.6):
        m.merge(A.straight(A.string_course(0.3, 0.14), -0.1, W + 0.1, z, 0.0, STONE))
    m.merge(A.straight(A.cornice_profile(0.8, 0.6), -0.3, W + 0.3, H - 0.8, 0.0, STONE))
    # pronaos: four Corinthian columns carrying the terrace
    for x in (6.9, 9.3, 11.9, 14.3):
        m.merge(A.column(0.74, 7.2, order='corinthian', mat=STONE, seg=12, detail=0.3).transformed(G.mat4((x, -2.4, 0.0))))
        m.merge(G.box(x - 0.42, -0.6, 0.0, x + 0.42, 0.0, 7.2, STONE))
    m.merge(G.box(6.2, -3.0, 7.2, 15.0, 0.0, 8.05, STONE))
    m.merge(A.balustrade(6.2, 15.0, 8.05, 1.0, 0.24, STONE, y=-3.0, bal_seg=6))
    m.merge(G.box(6.2, -3.0, -0.05, 15.0, 0.0, 0.08, STONE))
    # niches with Tragedy and Comedy, the phoenix over the door, the inscription and the two masks
    for x in (8.1, 13.1):
        m.merge(A.niche(1.1, 2.9, 0.4, STONE).transformed(G.mat4((x, 0.0, 8.7))))
        m.merge(statue(2.2, STONE).transformed(G.mat4((x, 0.18, 8.75))))
    m.merge(G.box(9.0, -0.12, 15.2, 12.2, 0.0, 16.4, 'relief'))
    for x in (7.6, 13.6):
        m.merge(G.lathe([(0.0, 0), (0.42, 0.0), (0.45, 0.06), (0.0, 0.08)], 14, mat='relief').transformed(G.mat4((x, -0.02, 15.8), rx=-math.pi / 2)))
    m.merge(G.box(10.1, 0.3, 3.7, 11.1, 0.4, 4.5, 'gilt'))
    # lamp posts flanking the entrance
    for x in (4.9, 16.3):
        m.merge(G.box(x - 0.06, -1.3, 0.0, x + 0.06, -1.18, 3.4, 'metal'))
        m.merge(G.lathe([(0.0, 0), (0.16, 0.05), (0.2, 0.45), (0.12, 0.6), (0.0, 0.7)], 8, mat='lamp_glass').transformed(G.mat4((x, -1.24, 3.4))))
    return m

def build_front(mb):
    M, L, fl = fac_frame()
    place(mb, front(), M)
    place(mb, foyer(M), M, max_edge=1.0)
    place(mb, corridor(), np.eye(4), max_edge=1.0)
    return dict(height=19.0)

def build_hall(mb):
    arts = []
    m = hall(arts)
    place(mb, m, np.eye(4), max_edge=1.2)
    for (pm, key) in arts:
        if key in ART: place(mb, pm, np.eye(4), c1=(ART[key]['layer'], 0, 0, 0), max_edge=1.2)
    return dict(hall=True)

def walk_areas():
    out = []
    M, L, fl = fac_frame()
    poly = lambda pts: Polygon([kitw(M, x, y) for (x, y) in pts])
    out.append((poly([(6.4, -3.2), (15.0, -3.2), (15.0, 0.9), (6.4, 0.9)]), GROUND_Z))          # pronaos
    out.append((poly([(3.4, 0.0), (17.8, 0.0), (17.8, 9.0), (3.4, 9.0)]), GROUND_Z))            # foyer
    for x in (6.6, 14.6):
        for y in (3.4, 6.6): out.append((poly([(x - 0.45, y - 0.45), (x + 0.45, y - 0.45), (x + 0.45, y + 0.45), (x - 0.45, y + 0.45)]), None))
    for x in (6.9, 9.3, 11.9, 14.3): out.append((poly([(x - 0.45, -2.85), (x + 0.45, -2.85), (x + 0.45, -1.95), (x - 0.45, -1.95)]), None))
    a, b = corridor_line(); d = b - a; Lc = np.linalg.norm(d); d /= Lc; n = np.array([-d[1], d[0]])
    out.append((Polygon([a - d * 0.6 - n * 1.2, b + d * 1.5 - n * 1.2, b + d * 1.5 + n * 1.2, a - d * 0.6 + n * 1.2]), GROUND_Z + 0.1))
    # the hall: front strip, side aisles and the back of the stalls (rows blocked)
    hp = [T2(p[0], p[1]) for p in path(-0.35)] + [T2(S0, -(R - 0.35)), T2(0.4, -(R - 0.35)), T2(0.4, R - 0.35), T2(S0, R - 0.35)]
    out.append((Polygon(hp), ZST))
    for s in np.arange(4.2, 17.3, 0.95):
        half = min(5.6, (R - 1.6) if s < LS else math.sqrt(max(0.0, (R - 1.6) ** 2 - (s - LS) ** 2)))
        out.append((Polygon([T2(s - 0.3, -half - 0.3), T2(s + 0.35, -half - 0.3), T2(s + 0.35, half + 0.3), T2(s - 0.3, half + 0.3)]), None))
    return out

def interior_zone():
    hp = [T2(p[0], p[1]) for p in path(DEPTH)] + [T2(S0, -(R + DEPTH)), T2(-1.0, -(R + DEPTH)), T2(-1.0, R + DEPTH), T2(S0, R + DEPTH)]
    return [list(map(lambda v: round(v, 2), p)) for p in hp]

def foyer_zone():
    M, L, fl = fac_frame()
    a, b = corridor_line()
    pts = [kitw(M, 3.0, 0.4), kitw(M, 18.2, 0.4), kitw(M, 18.2, 9.6), tuple(b), kitw(M, 3.0, 9.6)]
    return [list(map(lambda v: round(v, 2), p)) for p in pts]
