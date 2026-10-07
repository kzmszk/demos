"""舎利殿 (金閣), rebuilt 1955 to the 1904-06 survey: 二重三階 (no roof between 1F and 2F), 宝形 杮葺, gilt-bronze 鳳凰.

Local frame: u east (along the front), v north, w up from the top of the stone base; the front (v-) faces south over 鏡湖池.
Plan (pillar centres): 1F = 2F = 33 x 24 尺 (9.99 x 7.27 m), bays E-W 6 / 7.5 / 6.5 / 6.5 / 6.5 尺, N-S 4 x 6 尺;
3F 究竟頂 3 x 3 bays, 16 尺 (5 / 6 / 5).  Heights from photo measurement (refs/kinkakuji/dossier.md):
  1F 法水院 (寝殿造): plain dark wood + white plaster; south: open 広縁 bay, the room front behind it = 5 bays of 蔀戸;
      E / W: 広縁 end open, a plank door, 2 bays white wall; N: 5 bays white wall with the 腰貫 outside.  Outer deck + rail.
  漱清: the fishing pavilion projecting west over the water (OSM posts), 切妻 shingle roof, ridge E-W.
  2F 潮音洞 (武家造): all gilt; veranda on black cantilevered joists, 和様 railing; S: west 3 bays an open 広縁 with the
      仏間 front behind (lattice windows + plank doors), east 2 bays 舞良戸; E / W plank walls, N plank walls + one door.
  2F roof: a hipped skirt of shingles from the eave (5.7) up to the 3F base (6.5); gilt soffit, rafters, arms, gutters.
  3F 究竟頂 (禅宗様): gilt in and out; each side 花頭窓 / 桟唐戸 / 花頭窓, Zen railing (逆蓮柱), 詰組 brackets.
  3F roof: 宝形 shingles, eave 8.95, apex ~10.7, 露盤 + 鳳凰 to ~12.1."""
import math
import numpy as np
from jk import prim, Frame
from jk import roof as jroof
from . import kinkakuji_util as U

WD = 'wood_dark'; GD = 'gold'; BL = 'black_lacquer'; SH = 'hiwada'
SHAKU = 0.30303
US = np.cumsum([0, 6, 7.5, 6.5, 6.5, 6.5]) * SHAKU; US = US - US[-1] / 2          # 1F / 2F pillar lines (u)
VS = np.arange(5) * 6 * SHAKU; VS = VS - VS[-1] / 2                                   # v: -3.636 .. 3.636
U3 = np.cumsum([0, 5, 6, 5]) * SHAKU; U3 = U3 - U3[-1] / 2                           # 3F: -2.424 .. 2.424
A1, C1 = US[-1], VS[-1]                 # half sizes of the 1F / 2F pillar rectangle
A3 = U3[-1]
# heights above the base top
FL1 = 0.6; DECK1 = 0.42; NG1 = 2.4; KB1 = 2.72; HB1 = 2.88; BAND1 = 3.1; FL2 = 3.35
NG2 = 4.95; PL2 = 5.15
E2, TOP2 = 5.62, 6.75                  # 2F roof: eave edge (mid side), top at the 3F base
FL3 = 7.1; NG3 = 8.57; HK3 = 8.72; PL3 = 8.8
SK_U, SK_V = 3.9, 3.0                  # the 2F skirt's top box (the 3F base is 3.0 square; a flat strip E / W of it)
EAVE2 = (7.2, 5.95)                    # 2F eave outline half sizes (mid-sides)
TERI2, SORI2 = 1.55, 0.6
E3, APEX = 9.15, 11.55
VER2 = 0.9; VER3 = 0.84
WHITE = (242, 240, 234)

def wbox(B, x0, y0, z0, x1, y1, z1, mat, tag='main'):
    prim.box(B, min(x0, x1), min(y0, y1), z0, max(x0, x1), max(y0, y1), z1, mat, tag=tag)

def ring_members(B, a, c, z0, z1, w, mat, out=0.0, tag='main', sides=(0, 1, 2, 3)):
    """a band (beam) around the rectangle +-a x +-c, from z0 to z1, w thick, centred `out` outside the line"""
    segs = [((-a - out, -c - out), (a + out, -c - out)), ((a + out, -c - out), (a + out, c + out)), ((a + out, c + out), (-a - out, c + out)), ((-a - out, c + out), (-a - out, -c - out))]
    for k in sides:
        (p, q) = segs[k]
        e = w / 2
        if abs(p[1] - q[1]) < 1e-6:
            wbox(B, min(p[0], q[0]) - e, p[1] - e, z0, max(p[0], q[0]) + e, p[1] + e, z1, mat, tag)
        else:
            wbox(B, p[0] - e, min(p[1], q[1]) - e, z0, p[0] + e, max(p[1], q[1]) + e, z1, mat, tag)

def faces(a, c):
    """the four wall lines of a rectangle: (p0, p1, outward normal), counter-clockwise from the south"""
    return [((-a, -c), (a, -c), (0, -1)), ((a, -c), (a, c), (1, 0)), ((a, c), (-a, c), (0, 1)), ((-a, c), (-a, -c), (-1, 0))]

# ------------------------------------------------------------------ railings
def koran(B, pts, z, h, mat, step=0.9, closed=False, kind='wa', post=0.09, tag='main', cap=None):
    """高欄: 地覆 (bottom rail), 平桁 (mid rail), 架木 (round top rail), 束 struts with small blocks; posts at the ends /
    corners.  kind 'zen': 逆蓮柱 corner posts (inverted lotus knob) and top-rail ends curling up; 'plain': square rails"""
    pts = [np.asarray(p, float) for p in pts]
    if closed: pts = pts + [pts[0]]
    n = len(pts)
    for i in range(n - 1):
        a, b = pts[i], pts[i + 1]
        L = float(np.linalg.norm(b - a))
        if L < 0.05: continue
        d = (b - a) / L
        ext_a = 0.0 if (closed or i > 0 or kind != 'zen') else 0.18
        ext_b = 0.0 if (closed or i < n - 2 or kind != 'zen') else 0.18
        prim.obox(B, np.r_[a, z + 0.05], np.r_[b, z + 0.05], 0.1, 0.1, mat, tag=tag)                       # 地覆
        prim.obox(B, np.r_[a, z + h * 0.5], np.r_[b, z + h * 0.5], 0.06, 0.07, mat, tag=tag)               # 平桁
        if kind == 'plain':
            prim.obox(B, np.r_[a, z + h], np.r_[b, z + h], 0.07, 0.06, mat, tag=tag)
        else:
            ss = np.linspace(-ext_a, L + ext_b, max(4, int((L + ext_a + ext_b) / 0.5)) + 1)
            path = []
            for s in ss:
                over = max(0.0, -s, s - L)
                path.append(np.r_[a + d * s, z + h + (1.6 * over ** 2 if kind == 'zen' else 0.0)])
            ring = [(0.035 * math.cos(t), 0.035 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 9)[:-1]]
            prim.sweep(B, np.array(path), ring, mat, up=(0, 0, 1), tag=tag, smooth=True)
        m = max(1, int(round(L / step)))
        for k in range(1, m):
            q = a + d * L * k / m
            prim.obox(B, np.r_[q, z + 0.1], np.r_[q, z + h - 0.02], 0.05, 0.05, mat, tag='detail')        # 束
            prim.obox(B, np.r_[q - d * 0.06, z + h - 0.04], np.r_[q + d * 0.06, z + h - 0.04], 0.07, 0.05, mat, tag='detail')
    ends = pts if not closed else pts[:-1]
    for k, p in enumerate(ends):
        if kind == 'zen':
            prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.12], 0.06, 0.06, 10, mat, tag=tag)
            prim.lathe(B, np.r_[p, z + h + 0.12], [(0.075, 0.0), (0.085, 0.04), (0.06, 0.1), (0.03, 0.17), (0.0, 0.25)], 10, mat, tag='detail')
        else:
            prim.obox(B, np.r_[p, z], np.r_[p, z + h + 0.06], post, post, mat, tag=tag)

# ------------------------------------------------------------------ the 2F skirt roof (rectangular eave, square top box)
def skirt_roof(B, ue, ve, ub, vb, z_edge, z_top, uw, vw, teri=1.6, sori=0.45, sori_len=0.55, th=0.3, mat=SH, under=GD, rafter=0.55, tag='main'):
    """a hipped skirt: eave outline +-ue x +-ve (r = 0) up to the box +-ub x +-vb (r = 1); wall rectangle +-uw x +-vw.
    Returns the list of hip lines.  Under the overhang: gilt soffit, fascia, rafters, a gutter."""
    P = [np.array(p, float) for p in ((-ue, -ve), (ue, -ve), (ue, ve), (-ue, ve))]
    Q = [np.array(p, float) for p in ((-ub, -vb), (ub, -vb), (ub, vb), (-ub, vb))]
    H = z_top - z_edge
    def zf(t, r, E):
        dc = np.minimum(t, 1 - t) * E
        k = np.clip(1 - dc / (sori_len * E * 0.5), 0, 1)
        return z_edge + sori * k * k * (1 - r) ** 2 + H * np.power(np.clip(r, 0, 1), teri)
    hips = []
    for k in range(4):
        P0, P1, Q0, Q1 = P[k], P[(k + 1) % 4], Q[k], Q[(k + 1) % 4]
        E = float(np.linalg.norm(P1 - P0)); dE = (P1 - P0) / E
        n_in = np.array([-dE[1], dE[0]]); n_out = -n_in
        nt = max(10, int(E / 0.35)); nr = 9
        ts = np.linspace(0, 1, nt + 1); rs = np.linspace(0, 1, nr + 1) ** 0.8
        def pt(t, r):
            a = P0 + (P1 - P0) * t; b = Q0 + (Q1 - Q0) * t
            return a + (b - a) * r
        V = np.array([(*pt(t, r), float(zf(t, r, E))) for r in rs for t in ts])
        UV = np.array([(t * E, r * 3.0) for r in rs for t in ts])
        I = []
        for j in range(nr):
            for i in range(nt):
                a = j * (nt + 1) + i
                I += [[a, a + 1, a + nt + 2], [a, a + nt + 2, a + nt + 1]]
        I = np.array(I)
        fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(V, I, mat, UV=UV, smooth=True, tag=tag)
        # soffit (gilt boards): the surface lowered by the roof's thickness, out to the wall line only
        Vs = V.copy(); Vs[:, 2] -= th + 0.03
        B.add(Vs, I[:, ::-1], under, UV=UV, smooth=True, tag=tag)
        # eave edge: shingle courses on top, the gilt 茅負 below
        top = np.array([(*pt(t, 0), float(zf(t, 0, E))) for t in ts])
        for (dz0, dz1, m) in ((0.0, th * 0.45, mat), (th * 0.45, th + 0.03, under)):
            A_ = top - [0, 0, dz0]; B_ = top - [0, 0, dz1]
            PP = np.concatenate([A_, B_]); II = []
            n_ = len(ts)
            for i in range(n_ - 1):
                II += [[i, i + n_, i + 1], [i + 1, i + n_, i + n_ + 1]]
            II = np.array(II)
            f2 = np.cross(PP[II[:, 1]] - PP[II[:, 0]], PP[II[:, 2]] - PP[II[:, 0]])
            if (f2[:, :2] @ n_out).sum() < 0: II = II[:, ::-1]
            B.add(PP, II, m, UV=np.c_[np.r_[ts, ts] * E, PP[:, 2]], tag=tag)
        # gutter (樋): a half-round gilt channel hanging just under the edge
        gp = top - [0, 0, th + 0.08]
        gp[:, :2] += n_out * 0.1
        prim.sweep(B, gp, [(-0.07, 0.04), (-0.06, -0.02), (-0.03, -0.055), (0.0, -0.065), (0.03, -0.055), (0.06, -0.02), (0.07, 0.04)], under,
                   up=(0, 0, 1), closed=False, tag='detail')
        # rafters (垂木), widely spaced and gilt, from the wall line to the edge; stop at the hips
        depth_total = float(np.dot(Q0 - P0, n_in))
        for x in np.arange(rafter * 0.5, E, rafter):
            t = x / E
            a = P0 + dE * x
            if abs(n_in[0]) > 0.5: wall_r = abs(abs(a[0]) - uw) if abs(a[1]) <= vw else 9
            else: wall_r = abs(abs(a[1]) - vw) if abs(a[0]) <= uw else 9
            best = wall_r
            for (H0, H1) in ((P0, Q0), (P1, Q1)):
                dh = H1 - H0; M = np.array([[n_in[0], -dh[0]], [n_in[1], -dh[1]]])
                if abs(np.linalg.det(M)) < 1e-9: continue
                s_, u_ = np.linalg.solve(M, H0 - a)
                if s_ > 0 and 0 <= u_ <= 1: best = min(best, s_ - 0.08)
            best = min(best, depth_total - 0.05)
            if best < 0.25: continue
            r0, r1 = 0.04 / depth_total, best / depth_total
            q0 = a + n_in * 0.04; q1 = a + n_in * best
            z0 = float(zf(t, r0, E)) - th - 0.09; z1 = float(zf(t, r1, E)) - th - 0.09
            prim.obox(B, (q0[0], q0[1], z0), (q1[0], q1[1], z1), 0.09, 0.11, under, up=(0, 0, 1), tag='detail')
        hips.append((P0, Q0, k, E, zf))
    for (P0, Q0, k, E, zf) in hips:
        pts = []
        for r in np.linspace(0, 1, 12):
            xy = P0 + (Q0 - P0) * r
            pts.append((xy[0], xy[1], float(zf(0.0, r, E)) + 0.025))
        prim.sweep(B, np.array(pts), [(-0.11, -0.04), (0.11, -0.04), (0.08, 0.06), (-0.08, 0.06)], mat, up=(0, 0, 1), tag=tag, caps=True)
    return hips

# ------------------------------------------------------------------ the phoenix (鳳凰), gilt bronze, facing +x of its frame
def phoenix(B, x, y, z, s=1.0, yaw=0.0, mat=GD, tag='main'):
    with Frame(B, x, y, z, yaw):
        for sy in (-0.07, 0.07):                      # legs
            prim.cyl(B, (0.02, sy * s, 0.0), (0.04 * s, sy * s, 0.28 * s), 0.02 * s, 0.026 * s, 6, mat, tag=tag)
            for a in (-0.5, 0.0, 0.5):                # toes on the perch
                prim.obox(B, (0.02, sy * s, 0.01), (0.02 + 0.09 * s * math.cos(a), sy * s + 0.09 * s * math.sin(a), 0.0), 0.015 * s, 0.015 * s, mat, tag='detail')
        prof = [(0.0, 0.25), (0.07, 0.26), (0.115, 0.32), (0.125, 0.41), (0.105, 0.5), (0.075, 0.56), (0.05, 0.62)]
        seg = 12; P = []; I = []
        for j, (r, zz) in enumerate(prof):
            tilt = (zz - 0.25) * 0.45
            for i in range(seg):
                a = 2 * math.pi * i / seg
                P.append(((tilt + r * math.cos(a) * 1.2) * s, r * math.sin(a) * s, zz * s))
        for j in range(len(prof) - 1):
            for i in range(seg):
                a0 = j * seg + i; a1 = j * seg + (i + 1) % seg
                I += [[a0, a1, a1 + seg], [a0, a1 + seg, a0 + seg]]
        B.add(np.array(P), I, mat, smooth=True, tag=tag)
        neck = np.array([(0.15, 0, 0.6), (0.2, 0, 0.7), (0.19, 0, 0.8), (0.23, 0, 0.88)]) * s
        prim.sweep(B, neck, [(0.04 * s * math.cos(t), 0.04 * s * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 9)[:-1]], mat, up=(0, 1, 0), tag=tag, smooth=True)
        prim.lathe(B, (0.235 * s, 0, 0.86 * s), [(0.0, 0.0), (0.05 * s, 0.03 * s), (0.055 * s, 0.065 * s), (0.035 * s, 0.1 * s), (0.0, 0.11 * s)], 10, mat, tag=tag)
        prim.cyl(B, (0.28 * s, 0, 0.91 * s), (0.36 * s, 0, 0.88 * s), 0.018 * s, 0.003 * s, 6, mat, tag=tag)          # beak
        for k in range(4):                                                                                              # crest
            prim.obox(B, (0.22 * s, 0, 0.95 * s), ((0.15 - 0.04 * k) * s, 0, (1.06 + 0.025 * k) * s), 0.014 * s, 0.035 * s, mat, tag='detail')
        prim.obox(B, (0.25 * s, 0, 0.84 * s), (0.27 * s, 0, 0.76 * s), 0.02 * s, 0.03 * s, mat, tag='detail')           # wattle
        for sg in (-1, 1):                                                                                              # raised wings
            for f in range(8):
                a = 0.15 + f * 0.15
                root = np.array([0.02, sg * 0.09, 0.5]) * s
                tip = root + np.array([-0.16 - 0.06 * f, sg * (0.12 + 0.03 * f), 0.32 + 0.2 * math.cos(a)]) * s
                mid = (root + tip) / 2 + np.array([0.02, sg * 0.06, 0.05]) * s
                prim.sweep(B, np.array([root, mid, tip]), [(-0.04 * s, -0.005 * s), (0.04 * s, -0.005 * s), (0.025 * s, 0.007 * s), (-0.025 * s, 0.007 * s)], mat, up=(0, sg, 0.3), tag=tag)
        for f in range(9):                                                                                              # tail, sweeping back and up at the tips
            ang = -0.3 + f * 0.11
            pts = []
            for t in np.linspace(0, 1, 8):
                rr = 0.15 + 0.62 * t
                pts.append((-0.08 - rr * math.cos(ang + t * 0.5) * 0.95, (f - 4) * 0.028 * t, 0.38 + rr * math.sin(ang + t * 0.5) * 0.45 - 0.18 * t * t + 0.3 * t ** 4))
            prim.sweep(B, np.array(pts) * s, [(-0.035 * s, -0.004 * s), (0.035 * s, -0.004 * s), (0.022 * s, 0.006 * s), (-0.022 * s, 0.006 * s)], mat, up=(0, 1, 0), tag=tag)

# ------------------------------------------------------------------ 花頭窓 in a gilt board wall (lattice bars, dark behind)
def katomado_gilt(bay, s0, s1, z0, z1, wz, ww, off=0.0):
    sc = (s0 + s1) / 2
    ring = U.katomado_ring(sc, ww, z0 + wz[0], z0 + wz[1])
    bay.boards(s0, s1, z0, z1, off=off, mat=GD, batten=0, holes=[ring])
    pts = np.array([bay.P(s, z, off + 0.035) for (s, z) in ring + [ring[0]]])
    prim.sweep(bay.B, pts, [(-0.04, -0.035), (0.04, -0.035), (0.04, 0.035), (-0.04, 0.035)], GD, up=(bay.n[0], bay.n[1], 0))
    zs0, zs1 = z0 + wz[0], z0 + wz[1]
    bay.plane(sc - ww / 2 - 0.05, sc + ww / 2 + 0.05, zs0 - 0.02, zs1 + 0.02, 'glass', off=off - 0.1)
    for s in np.linspace(sc - ww / 2 + 0.08, sc + ww / 2 - 0.08, 6):
        bay.box(s - 0.014, s + 0.014, zs0, zs1 - 0.12, off - 0.07, off - 0.04, GD, tag='detail')
    for zz in np.linspace(zs0 + 0.2, zs1 - 0.3, 3):
        bay.box(sc - ww / 2 + 0.03, sc + ww / 2 - 0.03, zz - 0.012, zz + 0.012, off - 0.07, off - 0.045, GD, tag='detail')
    for i in range(len(ring)):
        s_a, z_a = ring[i]; s_b, z_b = ring[(i + 1) % len(ring)]
        A = bay.P(s_a, z_a, off); Bq = bay.P(s_b, z_b, off); C = bay.P(s_b, z_b, off - 0.1); D = bay.P(s_a, z_a, off - 0.1)
        U.quad(bay.B, A, D, C, Bq, GD, tag='detail', both=True)

def shitomi(bay, s0, s1, z0, z1, low=0.85, off=0.0):
    """蔀戸 with the upper flap raised: a fixed lower lattice panel; the room is dark above"""
    zl = z0 + low
    bay.box(s0, s1, z0, z0 + 0.06, off - 0.04, off + 0.04, WD)
    bay.box(s0, s1, zl - 0.05, zl, off - 0.04, off + 0.04, WD)
    bay.plane(s0, s1, z0 + 0.06, zl - 0.05, WD, off=off - 0.05)
    for s in np.arange(s0 + 0.07, s1 - 0.03, 0.14):
        bay.box(s - 0.012, s + 0.012, z0 + 0.06, zl - 0.05, off - 0.03, off + 0.0, WD, tag='detail')
    for zz in np.arange(z0 + 0.13, zl - 0.06, 0.14):
        bay.box(s0, s1, zz - 0.012, zz + 0.012, off - 0.03, off + 0.0, WD, tag='detail')
    # the raised flap hangs under the 内法 inside the room; the interior is dark
    bay.plane(s0, s1, zl, z1, 'glass', off=off - 1.6)
    U.quad(bay.B, bay.P(s0, z1 - 0.05, off - 0.05), bay.P(s1, z1 - 0.05, off - 0.05), bay.P(s1, z1 - 0.05, off - 0.75), bay.P(s0, z1 - 0.05, off - 0.75), WD, out=(0, 0, -1), tag='detail')

def plank_doors(bay, s0, s1, z0, z1, mat=WD, off=0.0):
    """板扉 (両開き): two board leaves with rails and a frame"""
    m = (s0 + s1) / 2
    bay.plane(s0, s1, z0, z1, mat, off=off - 0.03)
    for (a, b) in ((s0, s0 + 0.06), (m - 0.03, m + 0.03), (s1 - 0.06, s1)):
        bay.box(a, b, z0, z1, off - 0.04, off + 0.02, mat)
    for zz in (z0, z0 + (z1 - z0) * 0.33, z0 + (z1 - z0) * 0.66, z1 - 0.06):
        bay.box(s0, s1, zz, zz + 0.06, off - 0.035, off + 0.015, mat, tag='detail')

def dark_room(bay, s0, s1, z0, z1, depth=1.6):
    a = bay.P(s0, 0, -0.05); b = bay.P(s1, 0, -0.05); a2 = bay.P(s0, 0, -depth); b2 = bay.P(s1, 0, -depth)
    bay.plane(s0, s1, z0, z1, 'glass', off=-depth)
    U.quad(bay.B, (a[0], a[1], z0 - 0.01), (b[0], b[1], z0 - 0.01), (b2[0], b2[1], z0 - 0.01), (a2[0], a2[1], z0 - 0.01), WD, out=(0, 0, 1))

# ------------------------------------------------------------------ the building
def build(B, S, x, y, z0, yaw):
    with Frame(B, x, y, z0, yaw):
        base_and_1f(B)
        sosei(B)
        second(B)
        third(B)

def base_and_1f(B):
    a, c = A1, C1
    # stone base: dressed edge stones down into the water, a paved top round the building
    prim.prism(B, [(-a - 1.2, -c - 1.1), (a + 1.2, -c - 1.1), (a + 1.2, c + 1.0), (-a - 1.2, c + 1.0)], -0.85, 0.0, 'stone', top_mat='stone')
    for (x0, x1) in ((-a - 1.25, a + 1.25),):
        for k in range(int((x1 - x0) / 0.9)):
            xa = x0 + k * 0.9
            wbox(B, xa + 0.02, -c - 1.18, -0.75, xa + 0.88, -c - 1.05, 0.02, 'stone', 'detail')
    # underfloor: dark sill beams + short posts; floor of the room and the 広縁
    ring_members(B, a, c, FL1 - 0.22, FL1 - 0.02, 0.24, WD)
    prim.prism(B, [(-a + 0.1, -c + 0.1), (a - 0.1, -c + 0.1), (a - 0.1, c - 0.1), (-a + 0.1, c - 0.1)], 0.0, FL1 - 0.2, WD, top=False)
    prim.polygon(B, [(-a, -c), (a, -c), (a, c), (-a, c)], FL1, WD)
    # outer deck (縁) on all sides one step down, posts under its edge, a low rail on S / W / N
    D = VER2
    deck = [(-a - D, -c - D), (a + D, -c - D), (a + D, c + D), (-a - D, c + D)]
    prim.prism(B, deck, DECK1 - 0.08, DECK1, 'eave_wood', top=True, bottom=True)
    for (p, q, n) in faces(a + D - 0.06, c + D - 0.06):
        p = np.array(p); q = np.array(q); L = np.linalg.norm(q - p); d = (q - p) / L
        for t in np.linspace(0, L, max(2, int(L / 1.8)) + 1):
            r = p + d * t
            wbox(B, r[0] - 0.06, r[1] - 0.06, 0.0, r[0] + 0.06, r[1] + 0.06, DECK1 - 0.08, WD, 'detail')
    for x in np.arange(-a - D + 0.12, a + D, 0.24):
        wbox(B, x - 0.006, -c - D, DECK1, x + 0.006, -c, DECK1 + 0.004, WD, 'detail')
    koran(B, [(a + D - 0.05, -c - D + 0.05), (-a - D + 0.05, -c - D + 0.05), (-a - D + 0.05, -1.55)], DECK1, 0.55, WD, kind='plain', step=0.9)
    koran(B, [(-a - D + 0.05, 1.0), (-a - D + 0.05, c + D - 0.05), (a - 1.0, c + D - 0.05)], DECK1, 0.55, WD, kind='plain', step=0.9)
    # steps down at the east end (the monks' way in) and the 沓脱石
    prim.box(B, a + D, -0.9, -0.05, a + D + 0.6, 0.9, DECK1 - 0.18, 'stone')
    # pillars (square, chamfered look by a slim inner box) on the outer ring and the room front line
    pil = set()
    for u in US:
        for v in (VS[0], VS[1], VS[-1]): pil.add((round(u, 3), round(v, 3)))
    for v in VS:
        for u in (US[0], US[-1]): pil.add((round(u, 3), round(v, 3)))
    for (u, v) in pil:
        wbox(B, u - 0.105, v - 0.105, FL1 - 0.25, u + 0.105, v + 0.105, BAND1, WD)
    # head members all round (and on the room front line): 内法長押, white 小壁, 頭貫, a white band with the black arms
    ring_members(B, a, c, NG1, NG1 + 0.11, 0.14, WD, out=0.03)
    ring_members(B, a, c, HB1 - 0.16, HB1, 0.2, WD)
    ring_members(B, a, c, BAND1, BAND1 + 0.1, 0.22, WD)
    wbox(B, -a, VS[1] - 0.07, NG1, a, VS[1] + 0.07, NG1 + 0.11, WD)
    for (p, q, n) in faces(a, c):
        bay = U.Bay(B, p, q, n); L = bay.L
        bay.plaster(0.1, L - 0.1, NG1 + 0.11, HB1 - 0.16, off=-0.02, tint=WHITE)
        bay.plaster(0.1, L - 0.1, HB1, BAND1, off=-0.02, tint=WHITE)
    # the room front (蔀戸 x 5) behind the 広縁
    for i in range(5):
        bay = U.Bay(B, (US[i], VS[1]), (US[i + 1], VS[1]), (0, -1))
        shitomi(bay, 0.105, bay.L - 0.105, FL1, NG1, off=0.0)
        bay.plaster(0.1, bay.L - 0.1, NG1 + 0.11, HB1 - 0.16, off=-0.02, tint=WHITE)
    # the 広縁 ceiling (dark boards under the 2F floor) and its floor boards
    U.quad(B, (-a, -c, HB1 - 0.17), (a, -c, HB1 - 0.17), (a, VS[1], HB1 - 0.17), (-a, VS[1], HB1 - 0.17), WD, out=(0, 0, -1))
    for x in np.arange(-a + 0.12, a, 0.24):
        wbox(B, x - 0.005, -c, FL1, x + 0.005, VS[1], FL1 + 0.004, WD, 'detail')
    # side walls: (south -> north) 広縁 end open, plank door, white, white; north: 5 bays white with the 腰貫
    for sgn in (1, -1):
        u = sgn * a
        for j, kind in enumerate(('open', 'door', 'plaster', 'plaster')):
            v0, v1 = VS[j], VS[j + 1]
            p, q = ((u, v0), (u, v1)) if sgn > 0 else ((u, v1), (u, v0))
            bay = U.Bay(B, p, q, (sgn, 0))
            s0, s1 = 0.105, bay.L - 0.105
            if kind != 'open': wbox(B, u - 0.07, v0, FL1 - 0.02, u + 0.07, v1, FL1 + 0.05, WD)
            if kind == 'door': plank_doors(bay, s0, s1, FL1 + 0.05, NG1, off=-0.02)
            elif kind == 'plaster': bay.plaster(s0, s1, FL1 + 0.05, NG1, off=-0.02, tint=WHITE)
    for i in range(5):
        bay = U.Bay(B, (US[i + 1], c), (US[i], c), (0, 1))
        s0, s1 = 0.105, bay.L - 0.105
        bay.plaster(s0, s1, FL1 + 0.05, NG1, off=-0.02, tint=WHITE)
        bay.box(-0.0, bay.L, 1.38, 1.5, -0.04, 0.05, WD)                                   # 腰貫, outside on the north
    wbox(B, -a, c - 0.07, FL1 - 0.02, a, c + 0.07, FL1 + 0.05, WD)
    # a dim interior behind the room front: back wall, ceiling
    U.quad(B, (-a + 0.2, c - 0.15, FL1), (a - 0.2, c - 0.15, FL1), (a - 0.2, c - 0.15, NG1 + 0.3), (-a + 0.2, c - 0.15, NG1 + 0.3), 'glass', out=(0, -1, 0))
    U.quad(B, (-a + 0.15, VS[1] + 0.1, HB1 - 0.17), (a - 0.15, VS[1] + 0.1, HB1 - 0.17), (a - 0.15, c - 0.1, HB1 - 0.17), (-a + 0.15, c - 0.1, HB1 - 0.17), WD, out=(0, 0, -1))
    altar(B, (US[1] + US[2]) / 2, 2.55)
    # the black cantilever arms (腕木) under the 2F veranda, with small gilt caps, between the head beams
    for (p, q, n) in faces(a, c):
        p = np.array(p, float); q = np.array(q, float); L = np.linalg.norm(q - p); d = (q - p) / L; nn = np.array(n, float)
        k = max(2, int(round(L / 0.73)))
        for t in np.linspace(0, L, k + 1):
            r = p + d * t
            prim.obox(B, np.r_[r - nn * 0.1, BAND1 + 0.02], np.r_[r + nn * (VER2 - 0.05), BAND1 + 0.02], 0.12, 0.16, BL, tag='detail')
            prim.obox(B, np.r_[r + nn * (VER2 - 0.08), BAND1 - 0.02], np.r_[r + nn * (VER2 - 0.04), BAND1 - 0.02], 0.125, 0.165, GD, tag='detail')
            prim.box(B, *(r + nn * 0.35 - 0.07), BAND1 - 0.17, *(r + nn * 0.35 + 0.07), BAND1 - 0.06, BL, tag='detail')
    # block: nobody walks into the pavilion
    prim.prism(B, [(-a - D - 0.1, -c - D - 0.1), (a + D + 0.7, -c - D - 0.1), (a + D + 0.7, c + D + 0.1), (-a - D - 0.1, c + D + 0.1)], -0.3, 2.0, 'stone', tag='block')

def altar(B, uc, vc):
    """法水院's 須弥壇 at the back of the west three bays: the 宝冠釈迦如来 seated in the centre with its halo, the seated
    足利義満 (in priest's robes) to its left as seen from the front"""
    prim.box(B, uc - 2.0, vc - 0.55, FL1, uc + 2.0, vc + 0.55, FL1 + 0.75, BL)
    prim.box(B, uc - 2.08, vc - 0.62, FL1 + 0.7, uc + 2.08, vc + 0.62, FL1 + 0.78, GD, tag='detail')
    def seated(x, y, z, s, robe, face, halo=False, crown=False, tint=(255, 255, 255, 0)):
        prim.lathe(B, (x, y, z), [(0.0, 0.0), (0.42 * s, 0.0), (0.45 * s, 0.12 * s), (0.36 * s, 0.24 * s), (0.27 * s, 0.5 * s), (0.25 * s, 0.68 * s),
                                  (0.17 * s, 0.76 * s), (0.08 * s, 0.8 * s), (0.0, 0.81 * s)], 10, robe, c0=tint)
        prim.lathe(B, (x, y, z + 0.78 * s), [(0.0, 0.0), (0.1 * s, 0.03 * s), (0.12 * s, 0.13 * s), (0.09 * s, 0.24 * s), (0.0, 0.27 * s)], 8, face)
        if crown: prim.lathe(B, (x, y, z + 0.98 * s), [(0.11 * s, 0.0), (0.12 * s, 0.08 * s), (0.05 * s, 0.16 * s), (0.0, 0.2 * s)], 8, GD, tag='detail')
        if halo:
            prim.cyl(B, (x, y + 0.25 * s, z + 0.95 * s), (x, y + 0.29 * s, z + 0.95 * s), 0.42 * s, 0.42 * s, 16, GD, tag='detail')
            prim.cyl(B, (x, y + 0.3 * s, z + 0.5 * s), (x, y + 0.34 * s, z + 0.5 * s), 0.62 * s, 0.62 * s, 16, GD, tag='detail')
    seated(uc, vc, FL1 + 0.78, 1.15, GD, GD, halo=True, crown=True)
    prim.box(B, uc - 2.9, vc - 0.4, FL1, uc - 1.95, vc + 0.4, FL1 + 0.45, BL)
    seated(uc - 2.42, vc - 0.05, FL1 + 0.45, 1.0, 'cloth', 'wood_natural', tint=(58, 50, 44, 0))

def sosei(B):
    """漱清: 方1間 open pavilion over the water west of the 1F (posts per OSM), a deck to it, 切妻 roof with the ridge E-W"""
    u0, u1 = -8.35, -11.75; v0, v1 = -1.45, 0.85
    ue = -A1 - VER2
    zf = DECK1 - 0.02
    # deck from the 1F's west deck out to the pavilion's far side
    prim.prism(B, [(u1 - 0.25, v0 - 0.2), (ue, v0 - 0.2), (ue, v1 + 0.2), (u1 - 0.25, v1 + 0.2)], zf - 0.1, zf, 'eave_wood', bottom=True)
    for x in np.arange(u1 - 0.2, ue, 0.22):
        wbox(B, x - 0.005, v0 - 0.2, zf, x + 0.005, v1 + 0.2, zf + 0.004, WD, 'detail')
    # posts down into the water on stones, and the deck's posts
    for (u, v) in ((u0, v0), (u0, v1), (u1, v0), (u1, v1)):
        prim.box(B, u - 0.08, v - 0.08, -1.0, u + 0.08, v + 0.08, 2.55, WD)
        U.rock(B, (u, v, -0.42), 0.32, int(abs(u * 100 + v * 10)), flat=0.6, sub=1, sink=0.3)
    for (u, v) in ((-6.8, v0 - 0.15), (-6.8, v1 + 0.15)):
        prim.box(B, u - 0.07, v - 0.07, -1.0, u + 0.07, v + 0.07, zf - 0.1, WD)
    # rails: low railing round the pavilion and along the deck
    koran(B, [(u0, v1 + 0.15), (u1 - 0.15, v1 + 0.15), (u1 - 0.15, v0 - 0.15), (u0, v0 - 0.15)], zf, 0.5, WD, kind='plain', step=0.85)
    koran(B, [(ue, v1 + 0.15), (u0, v1 + 0.15)], zf, 0.5, WD, kind='plain', step=0.85)
    koran(B, [(ue, v0 - 0.15), (u0, v0 - 0.15)], zf, 0.5, WD, kind='plain', step=0.85)
    # head beams, a little 小壁 band, the roof
    for (a_, b_) in (((u0, v0), (u1, v0)), ((u0, v1), (u1, v1)), ((u0, v0), (u0, v1)), ((u1, v0), (u1, v1))):
        prim.obox(B, (*a_, 2.45), (*b_, 2.45), 0.12, 0.18, WD)
    with Frame(B, (u0 + u1) / 2, (v0 + v1) / 2, 0, 0):
        L = abs(u1 - u0); Dd = v1 - v0
        jroof.roof(B, L, Dd, 2.78, 0.95, kind='kirizuma', cover='kokera', pitch=0.42, teri=1.25, sori=0.0, rafter=0.3, tiers=1, rafter_mat=WD,
                   rafter_end=WD, ends=None, verge=0.45, edge=0.2, bargeboard_mat=WD, gable_wall=WD)
    prim.prism(B, [(u1 - 0.3, v0 - 0.3), (ue, v0 - 0.3), (ue, v1 + 0.3), (u1 - 0.3, v1 + 0.3)], zf - 0.4, zf + 1.2, 'stone', tag='block')

def second(B):
    a, c = A1, C1
    D = VER2
    # veranda deck (black edge, gilt rail)
    deck = [(-a - D, -c - D), (a + D, -c - D), (a + D, c + D), (-a - D, c + D)]
    prim.prism(B, deck, BAND1 + 0.1, FL2 - 0.12, BL, top=False, bottom=True)
    prim.prism(B, deck, FL2 - 0.12, FL2, BL, top=True)
    for x in np.arange(-a - D + 0.12, a + D, 0.24):
        wbox(B, x - 0.006, -c - D, FL2, x + 0.006, -c, FL2 + 0.004, GD, 'detail')
    ring_members(B, a + D - 0.06, c + D - 0.06, FL2 - 0.02, FL2 + 0.08, 0.12, GD)
    koran(B, deck, FL2, 0.7, GD, closed=True, kind='wa', step=0.95)
    # pillars (gilt), floor sill, 腰長押, 内法長押, 頭貫, 小壁
    pil = set([(u, v) for u in US for v in (VS[0], VS[-1])] + [(u, v) for v in VS for u in (US[0], US[-1])] + [(u, VS[1]) for u in US[:4]])
    for (u, v) in pil:
        wbox(B, u - 0.095, v - 0.095, FL2, u + 0.095, v + 0.095, PL2, GD)
    ring_members(B, a, c, FL2, FL2 + 0.12, 0.16, GD)
    ring_members(B, a, c, NG2, NG2 + 0.1, 0.15, GD, out=0.02)
    ring_members(B, a, c, PL2 - 0.12, PL2 + 0.02, 0.2, GD)
    wbox(B, US[0], VS[1] - 0.07, NG2, US[3], VS[1] + 0.07, NG2 + 0.1, GD)
    wbox(B, US[0], VS[1] - 0.07, FL2, US[3], VS[1] + 0.07, FL2 + 0.1, GD)
    # fittings
    def fit(bay, kind):
        s0, s1 = 0.095, bay.L - 0.095
        z0, z1 = FL2 + 0.12, NG2
        if kind == 'board': bay.boards(s0, s1, z0, z1, off=-0.02, mat=GD, batten=0.48)
        elif kind == 'mairado': bay.mairado(s0, s1, z0, z1, 2, off=-0.02, mat=GD, slat=0.06)
        elif kind == 'door':
            plank_doors(bay, s0 + 0.05, s1 - 0.05, z0, z1 - 0.05, mat=GD, off=-0.02)
        elif kind == 'lattice':
            bay.boards(s0, s1, z0, z0 + 0.75, off=-0.02, mat=GD, batten=0)
            bay.box(s0, s1, z0 + 0.75, z0 + 0.83, -0.05, 0.04, GD)
            bay.koshi(s0, s1, z0 + 0.83, z1, off=-0.02, mat=GD, step=0.09, back='glass')
        if kind != 'open': bay.boards(0.1, bay.L - 0.1, NG2 + 0.1, PL2 - 0.12, off=-0.02, mat=GD, batten=0)
    for i in range(5):                                     # south outer line: loggia open on the west 3 bays, 舞良戸 on the east 2
        bay = U.Bay(B, (US[i], -c), (US[i + 1], -c), (0, -1))
        fit(bay, 'open' if i < 3 else 'mairado')
        if i < 3: bay.boards(0.1, bay.L - 0.1, NG2 + 0.1, PL2 - 0.12, off=-0.02, mat=GD, batten=0)
    for i, kind in enumerate(('lattice', 'door', 'lattice')):            # the 仏間 front behind the loggia
        fit(U.Bay(B, (US[i], VS[1]), (US[i + 1], VS[1]), (0, -1)), kind)
    fit(U.Bay(B, (US[3], -c), (US[3], VS[1]), (-1, 0)), 'mairado')      # the east room's side to the loggia
    U.quad(B, (US[0], -c, NG2 + 0.1), (US[3], -c, NG2 + 0.1), (US[3], VS[1], NG2 + 0.1), (US[0], VS[1], NG2 + 0.1), GD, out=(0, 0, -1))
    for j in range(4):                                     # east (u+) and west (u-) plank walls; the west end of the loggia is open
        fit(U.Bay(B, (a, VS[j]), (a, VS[j + 1]), (1, 0)), 'board')
        if j > 0: fit(U.Bay(B, (-a, VS[j + 1]), (-a, VS[j]), (-1, 0)), 'board')
    for i in range(5):                                     # north: plank walls, a door in the 2nd bay from the west
        fit(U.Bay(B, (US[i + 1], c), (US[i], c), (0, 1)), 'door' if i == 1 else 'board')
    # bracket blocks (舟肘木) on the pillars, the plate (桁), arms (腕木) carrying an outer purlin (出桁)
    for (u, v) in pil:
        if abs(abs(v) - c) > 0.01 and abs(abs(u) - a) > 0.01: continue
        n = np.array([np.sign(u) if abs(abs(u) - a) < 0.01 else 0.0, np.sign(v) if abs(abs(v) - c) < 0.01 else 0.0])
        al = np.array([-n[1], n[0]])
        if abs(n[0]) > 0 and abs(n[1]) > 0: al = np.array([1.0, -1.0]) * n[::-1] / math.sqrt(2)
        q = np.array([u, v])
        prim.obox(B, np.r_[q - al * 0.45, PL2 + 0.05], np.r_[q + al * 0.45, PL2 + 0.05], 0.15, 0.1, GD, tag='detail')
        prim.obox(B, np.r_[q - n * 0.2, PL2 + 0.16], np.r_[q + n * 1.05, PL2 + 0.16], 0.13, 0.16, GD, tag='detail')
    ring_members(B, a, c, PL2 + 0.1, PL2 + 0.24, 0.2, GD)
    ring_members(B, a + 1.0, c + 1.0, PL2 + 0.22, PL2 + 0.33, 0.15, GD, tag='detail')
    # the roof: eave outline 14.4 x 11.9 at mid-sides, up to the 3F base box
    ue, ve = EAVE2
    hips = skirt_roof(B, ue, ve, SK_U, SK_V, E2, TOP2, a, c, teri=TERI2, sori=SORI2, sori_len=0.55, th=0.3, rafter=0.55)
    # close the band between the plate and the soffit (gilt boards) on each side
    for k, (p, q, n) in enumerate(faces(a + 0.02, c + 0.02)):
        r_ = (ve - c) / (ve - SK_V) if k in (0, 2) else (ue - a) / (ue - SK_U)
        z_soff = E2 + (TOP2 - E2) * r_ ** TERI2 - 0.33
        bay = U.Bay(B, p, q, n)
        bay.plane(-0.12, bay.L + 0.12, PL2 + 0.2, z_soff + 0.04, GD, off=0.0)
    # wind bells (風鐸) at the four corners
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = sx * 6.75, sy * 5.5
        prim.lathe(B, (x, y, E2 - 0.15), [(0.0, -0.35), (0.09, -0.33), (0.1, -0.1), (0.06, 0.0), (0.0, 0.02)], 8, GD, tag='detail')
    # interior glimpse through the loggia: a dim room
    dark_room(U.Bay(B, (US[0], VS[1]), (US[3], VS[1]), (0, -1)), 0.1, US[3] - US[0] - 0.1, FL2 + 0.1, NG2, depth=0.4)

def third(B):
    a = A3
    D = VER3
    # base (腰組) on the 2F roof: a gilt box with bracket blocks carrying the veranda
    prim.prism(B, [(-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)], TOP2 - 0.4, FL3 - 0.24, GD, top=False)
    for (p, q, n) in faces(3.0, 3.0):
        p = np.array(p, float); q = np.array(q, float); L = np.linalg.norm(q - p); d = (q - p) / L; nn = np.array(n, float)
        for t in np.linspace(0.3, L - 0.3, 6):
            r = p + d * t
            prim.obox(B, np.r_[r - d * 0.22, FL3 - 0.33], np.r_[r + d * 0.22, FL3 - 0.33], 0.12, 0.1, GD, tag='detail')
            prim.box(B, *(r - 0.09 + nn * 0.05), FL3 - 0.45, *(r + 0.09 + nn * 0.05), FL3 - 0.38, GD, tag='detail')
            prim.obox(B, np.r_[r, FL3 - 0.28], np.r_[r + nn * (A3 + D - 3.0 + 0.05), FL3 - 0.28], 0.1, 0.1, GD, tag='detail')
    deck = [(-a - D, -a - D), (a + D, -a - D), (a + D, a + D), (-a - D, a + D)]
    prim.prism(B, deck, FL3 - 0.24, FL3 - 0.08, GD, top=False, bottom=True)
    prim.prism(B, deck, FL3 - 0.08, FL3, GD, top_mat=BL, top=True)
    koran(B, [(x * 0.985, y * 0.985) for (x, y) in deck], FL3, 0.72, GD, closed=True, kind='zen', step=0.75)
    # round gilt pillars
    for u in U3:
        for v in (U3[0], U3[-1]):
            for (px, py) in ((u, v), (v, u)):
                prim.cyl(B, (px, py, FL3), (px, py, HK3), 0.105, 0.1, 12, GD, caps=(False, True))
    # sill, 内法, 頭貫, 台輪 (proud at the corners)
    ring_members(B, a, a, FL3, FL3 + 0.13, 0.16, GD)
    ring_members(B, a, a, NG3, NG3 + 0.09, 0.14, GD, out=0.02)
    ring_members(B, a, a, HK3 - 0.16, HK3, 0.18, GD)
    for (p, q, n) in faces(a, a):
        bay = U.Bay(B, p, q, n)
        bay.box(-0.28, bay.L + 0.28, HK3, PL3, -0.13, 0.13, GD)
    # each side: 花頭窓 / 桟唐戸 / 花頭窓
    for (p, q, n) in faces(a, a):
        p = np.array(p, float); q = np.array(q, float); d = (q - p) / np.linalg.norm(q - p)
        edges = U3 - U3[0]
        for i in range(3):
            bay = U.Bay(B, p + d * edges[i], p + d * edges[i + 1], n)
            s0, s1 = 0.1, bay.L - 0.1
            if i == 1:
                bay.karado(s0 + 0.02, s1 - 0.02, FL3 + 0.13, NG3, off=-0.03, mat=GD, lattice=0.5)
            else:
                katomado_gilt(bay, s0, s1, FL3 + 0.13, NG3, wz=(0.28, 1.25), ww=0.72, off=-0.02)
            bay.boards(s0, s1, NG3 + 0.09, HK3 - 0.16, off=-0.02, mat=GD, batten=0)
    # 詰組 bracket sets: at the pillars and between them (三斗), then the purlin
    zb = PL3
    for (p, q, n) in faces(a, a):
        p = np.array(p, float); q = np.array(q, float); L = np.linalg.norm(q - p); d = (q - p) / L; nn = np.array(n, float)
        e3 = U3 - U3[0]
        for t in np.r_[e3, (e3[:-1] + e3[1:]) / 2]:
            r = p + d * t
            prim.box(B, *(r - 0.1), zb, *(r + 0.1), zb + 0.08, GD, tag='detail')                                            # 大斗
            prim.obox(B, np.r_[r - d * 0.34, zb + 0.13], np.r_[r + d * 0.34, zb + 0.13], 0.09, 0.1, GD, tag='detail')       # 肘木
            for e in (-0.28, 0.0, 0.28):
                prim.box(B, *(r + d * e - 0.06), zb + 0.18, *(r + d * e + 0.06), zb + 0.24, GD, tag='detail')              # 巻斗
            prim.obox(B, np.r_[r - nn * 0.15, zb + 0.13], np.r_[r + nn * 0.36, zb + 0.13], 0.09, 0.1, GD, tag='detail')
    ring_members(B, a, a, zb + 0.2, zb + 0.32, 0.16, GD)
    ring_members(B, a + 0.32, a + 0.32, zb + 0.18, zb + 0.32, 0.15, GD)
    for (p, q, n) in faces(a + 0.02, a + 0.02):
        bay = U.Bay(B, p, q, n)
        bay.plane(-0.3, bay.L + 0.3, zb, zb + 0.55, GD, off=-0.06)
    cz = zb + 0.33; ce = a + 0.6                                  # ceiling under the roof: no view up into it
    U.quad(B, (-ce, -ce, cz), (ce, -ce, cz), (ce, ce, cz), (-ce, ce, cz), GD, out=(0, 0, -1))
    # the 扁額「究竟頂」 on the south, under the eave
    prim.box(B, -0.2, -a - 0.36, HK3 - 0.06, 0.2, -a - 0.3, HK3 + 0.46, BL)
    prim.box(B, -0.24, -a - 0.33, HK3 - 0.1, 0.24, -a - 0.28, HK3 + 0.5, GD, tag='detail')
    # roof: 宝形 shingles over the purlin; eave 8.95 at mid-sides, apex 10.7
    c_out = 4.4
    Lr = 2 * (a + 0.32); o = c_out - Lr / 2
    ZR = zb + 0.8
    Hh = APEX - E3
    teri = float(np.clip(math.log(max(0.05, ZR - E3) / Hh) / math.log(o / c_out), 1.2, 2.6))
    r = jroof.Roof(Lr, Lr, ZR, o, kind='hogyo', cover='kokera', pitch=Hh / c_out, teri=teri, sori=0.72, sori_len=1.0, edge=0.3,
                   rafter=0.5, tiers=2, rafter_mat=GD, rafter_end=GD, fascia_mat=GD, ends=None, hip=False, top=[(0.001, 0.0), (0.0, 0.002)])
    info = r.build(B)
    za = info['z_ridge']
    for k in range(4):
        hl = r.hip_line(k, c_out * 0.97, n=14, off=0.03)
        prim.sweep(B, hl, [(-0.1, -0.04), (0.1, -0.04), (0.07, 0.06), (-0.07, 0.06)], SH, up=(0, 0, 1), caps=True)
        # gutters along this side's eave
        p0, p1, n_in, E = r.sides()[k]
        d = (p1 - p0) / E
        xs = np.linspace(0, E, 30)
        g = np.array([np.r_[p0 + d * x_ - n_in * 0.08, float(r.z(0.0, min(x_, E - x_))) - 0.38] for x_ in xs])
        prim.sweep(B, g, [(-0.06, 0.035), (-0.05, -0.02), (0.0, -0.055), (0.05, -0.02), (0.06, 0.035)], GD, up=(0, 0, 1), closed=False, tag='detail')
        # 風鐸 at the corner
        prim.lathe(B, (p0[0] * 0.93, p0[1] * 0.93, E3 + 0.1), [(0.0, -0.3), (0.08, -0.28), (0.09, -0.08), (0.05, 0.0), (0.0, 0.02)], 8, GD, tag='detail')
    # 露盤: a dark band, a stepped gilt box; the phoenix facing south
    prim.box(B, -0.7, -0.7, za - 0.45, 0.7, 0.7, za - 0.2, 'metal_dark')
    prim.box(B, -0.66, -0.66, za - 0.2, 0.66, 0.66, za - 0.08, GD)
    prim.box(B, -0.62, -0.62, za - 0.08, 0.62, 0.62, za + 0.22, GD)
    prim.box(B, -0.68, -0.68, za + 0.22, 0.68, 0.68, za + 0.28, GD)
    prim.box(B, -0.5, -0.5, za + 0.28, 0.5, 0.5, za + 0.4, GD)
    prim.box(B, -0.2, -0.2, za + 0.4, 0.2, 0.2, za + 0.48, GD)
    phoenix(B, 0.0, 0.05, za + 0.48, s=1.12, yaw=-math.pi / 2)
    return za
