"""京都タワー (Yamada Mamoru, 1964): the 31 m Kyoto Tower Building (9 storeys, stepped ribbon floors, rounded corners,
roof terrace) and the 100 m monocoque steel tower: the ribbed glazed bowl on the roof, the white shaft with its concave
flare, the observation deck (red dish, glazed cabin, red cage of curved ribs) and the red-and-white mast.

Site frame: x east, y north (m from the station's central exit), z = T.P.  Heights below are above street level."""
import math
import numpy as np
from jk import prim
from . import station_util as U

TC = (48.3, 194.4)                          # tower axis (OSM node n1494857741)
OUTLINE = [(21.4, 168.8), (67.9, 168.9), (74.5, 175.3), (74.5, 213.0), (21.4, 212.9)]     # w120374257, CCW
RADII = [6.0, 3.0, 3.0, 6.5, 6.5]
ROOF_H = 30.8                               # OSM height of the Kyoto Tower Hotel building
N_FLOORS = 8
GROUND_H = 4.9
FLOOR_H = (ROOF_H - GROUND_H) / N_FLOORS

RED_LAMP = (1.0, 0.12, 0.08)

def tower_base(S):
    return float(min(S.ground(x, y) for (x, y) in OUTLINE + [TC]))

# ------------------------------------------------------------------------------------------------ the building
def build_building(B, S):
    zb = tower_base(S)
    top = U.round_outline(np.array(OUTLINE), RADII, seg=6)           # outline of the roof slab (widest)
    rng = np.random.default_rng(1964)
    out_prev = None
    rings = []
    for k in range(N_FLOORS + 1):
        inset = 0.28 * (N_FLOORS - k)
        rings.append(U.buffer_ring(top, -inset, 4) if inset > 0 else U.ccw(top))
    # ---- ground floor: colonnade and shop fronts
    g_out = rings[0]
    g_col = U.buffer_ring(top, -2.9, 4)
    g_back = U.buffer_ring(top, -5.6, 4)
    zg = zb
    # shop front glazing + lit signboard band
    n = len(g_back)
    a = g_back; b = np.roll(g_back, -1, axis=0)
    U.vquads(B, a, b, zb, zb + GROUND_H - 1.0, 'glass', zg=zg)
    U.vquads(B, a, b, zb + GROUND_H - 1.0, zb + GROUND_H - 0.1, 'wall_concrete', zg=zg, c0=(84, 78, 72, 0))
    # lit sign panels on the colonnade back wall (every ~6 m, alternating)
    P, Nn, T = U.ring_samples(g_back, 6.0)
    for i in range(0, len(P), 2):
        c = P[i] + Nn[i] * 0.05
        U.obox_batch(B, np.array([[*(c - T[i] * 1.6), zb + 3.0]]), np.array([[*(c + T[i] * 1.6), zb + 3.0]]), 0.7, 0.05, 'lamp', up=np.array([Nn[i][0], Nn[i][1], 0]), tag='main')
    # columns
    P, Nn, T = U.ring_samples(g_col, 6.2)
    for (x, y) in P:
        prim.cyl(B, (x, y, zb), (x, y, zb + GROUND_H), 0.34, 0.34, 10, 'wall_concrete', caps=(False, False), c0=(92, 86, 80, 0))
    U.box_batch(B, np.c_[P - 0.4, np.full(len(P), zb - 0.5)], np.c_[P + 0.4, np.full(len(P), zb + 3.5)], 'curb', tag='block')
    # ground floor ceiling (underside of slab 0) and floor
    U.flat(B, rings[0], zb + GROUND_H - 0.5, 'wall_concrete', up=False, holes=[g_back], c0=(72, 68, 64, 0))
    S.paint.append({'poly': [[float(x), float(y)] for (x, y) in U.buffer_ring(top, 3.5, 3)], 'surf': 'stone_slab'})
    # ---- the nine slabs and eight glazed bands
    for k in range(N_FLOORS + 1):
        zt = zb + GROUND_H + FLOOR_H * k                              # top of slab k (deck level)
        ring = rings[k]
        a = ring; b = np.roll(ring, -1, axis=0)
        U.vquads(B, a, b, zt - 1.05, zt, 'wall_concrete', zg=zb, c0=(74, 68, 62, 0))               # fascia
        inner = U.buffer_ring(ring, -0.95, 3)
        if inner is None: continue
        # balcony deck between the slab edge and the glass line (resample inner ring to the same count)
        inner_s = _resample_like(ring, 0.95)
        U.hquads(B, ring, inner_s, zt, 'wall_concrete', up=True, c0=(92, 86, 80, 0))
        U.hquads(B, ring, inner_s, zt - 1.05, 'wall_concrete', up=False, c0=(60, 56, 52, 0))
        if k == N_FLOORS: continue
        # glazing for floor k (between slab k and slab k+1), set 0.95 m behind the slab edge
        zt2 = zb + GROUND_H + FLOOR_H * (k + 1)
        zlo, zhi = zt + 0.08, zt2 - 1.05
        gl = inner_s
        Pm, Nm, Tm = U.ring_samples(gl, 1.9, phase=0.5 * (k % 2))
        m = len(Pm)
        a2 = Pm; b2 = np.roll(Pm, -1, axis=0)
        lit = rng.random(m) < 0.13
        if (~lit).any(): U.vquads(B, a2[~lit], b2[~lit], zlo, zhi, 'glass', zg=zb)
        if lit.any(): U.vquads(B, a2[lit] + _out(Nm[lit], 0.01), b2[lit] + _out(Nm[lit], 0.01), zlo + 0.3, zhi - 0.45, 'lamp', zg=zb)
        # mullions (red-brown), a mid transom, and the slender rail on the slab edge
        c = np.c_[Pm + Nm * 0.05, np.full(m, zlo)]
        U.obox_batch(B, c, c + np.array([0, 0, zhi - zlo]), 0.07, 0.10, 'bronze', up=np.c_[Nm, np.zeros(m)], tag='detail')
        zm = (zlo + zhi) / 2 + 0.25
        U.obox_batch(B, np.c_[Pm + Nm * 0.05, np.full(m, zm)], np.c_[b2 + Nm * 0.05, np.full(m, zm)], 0.05, 0.08, 'bronze', up=(0, 0, 1), tag='detail')
        # rail at the slab edge: top bar + posts
        Pr, Nr, Tr = U.ring_samples(ring, 2.0)
        r = len(Pr)
        rail_a = np.c_[ring - U.unit(_normals(ring)) * 0.08, np.full(len(ring), zt + 1.0)]
        rail_b = np.c_[np.roll(ring, -1, axis=0) - U.unit(_normals(np.roll(ring, -1, axis=0))) * 0.08, np.full(len(ring), zt + 1.0)]
        U.obox_batch(B, rail_a, rail_b, 0.05, 0.05, 'bronze', up=(0, 0, 1), tag='detail')
        c = np.c_[Pr - Nr * 0.08, np.full(r, zt)]
        U.obox_batch(B, c, c + np.array([0, 0, 1.0]), 0.04, 0.04, 'bronze', up=np.c_[Nr, np.zeros(r)], tag='detail')
    # ---- roof: parapet, deck, structures
    ring = rings[N_FLOORS]; zr = zb + ROOF_H
    par = U.buffer_ring(ring, -0.35, 3)
    U.wall_ring(B, par, zr, zr + 0.95, 'wall_concrete', zg=zb, c0=(84, 78, 72, 0))
    U.flat(B, par, zr + 0.95, 'wall_concrete', up=True, c0=(100, 96, 90, 0))
    U.flat(B, U.buffer_ring(par, -0.45, 3), zr + 0.02, 'roof_flat', up=True, c0=(150, 148, 142, 0))
    # white mesh fence on the parapet
    ps, pn, pt = U.ring_samples(par, 1.6)
    U.obox_batch(B, np.c_[par, np.full(len(par), zr + 2.0)], np.c_[np.roll(par, -1, axis=0), np.full(len(par), zr + 2.0)], 0.05, 0.05, 'white_paint', up=(0, 0, 1), tag='detail')
    c = np.c_[ps, np.full(len(ps), zr + 0.95)]
    U.obox_batch(B, c, c + np.array([0, 0, 1.05]), 0.04, 0.04, 'white_paint', up=np.c_[pn, np.zeros(len(ps))], tag='detail')
    _roof_structures(B, zr, zb)
    # ---- signs: white band on the south fascia of the 6th floor is left out (no glyphs); lit strips on the colonnade only
    B.lamp(TC[0] - 22, 170.5, zb + 3.5, 60, (1.0, 0.72, 0.45))
    B.lamp(TC[0] + 18, 170.5, zb + 3.5, 60, (1.0, 0.72, 0.45))
    return zb

def _out(Nm, d):
    return Nm * d

def _normals(ring):
    """outward normals at ring vertices (CCW): average of the two adjacent edge normals"""
    ring = np.asarray(ring, float)
    t = np.roll(ring, -1, axis=0) - ring
    t = t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    n = np.stack([t[:, 1], -t[:, 0]], 1)
    return n + np.roll(n, 1, axis=0)

def _resample_like(ring, inset):
    """inner ring with the same vertex count as `ring` (vertex-normal inset: exact enough for ~1 m)"""
    n = U.unit(_normals(ring))
    return np.asarray(ring, float) - n * inset

def _roof_structures(B, zr, zb):
    # plant rooms in white-grey panels, with louvre strips
    def room(x0, y0, x1, y1, h, tint=(206, 206, 200)):
        U.box(B, x0, y0, zr, x1, y1, zr + h, 'wall_plaster', c0=(*tint, 30), c1=(0, 0, 3, 0))
        U.box(B, x0 - 0.1, y0 - 0.1, zr + h, x1 + 0.1, y1 + 0.1, zr + h + 0.18, 'wall_concrete', c0=(120, 120, 118, 0))
        for zz in np.arange(zr + 1.0, zr + h - 0.6, 0.45):
            U.box(B, x0 + 0.5, y0 - 0.04, zz, x1 - 0.5, y0, zz + 0.12, 'metal_grey', tag='detail')
    room(22.8, 199.0, 38.5, 210.5, 5.4)
    room(30.0, 190.0, 40.0, 199.0, 3.2)
    room(60.5, 197.0, 72.5, 210.5, 4.2)
    room(43.0, 207.0, 56.0, 212.0, 6.2, tint=(150, 152, 156))
    room(24.0, 175.0, 31.0, 181.0, 2.9)
    # cowl vents on the east roof
    for (x, y, r) in ((66.5, 203.0, 1.5), (69.8, 205.5, 1.3)):
        U.lathe_uv(B, (x, y, zr + 4.2), [(0.5, 0.0), (r, 0.5), (r * 1.05, 1.6), (r * 0.7, 2.2)], seg=14, mat='metal_grey', uvs=1.0)
    # antenna masts on the west block
    for (x, y, h) in ((26.0, 205.0, 11.0), (28.5, 207.5, 8.5), (35.0, 209.0, 14.0), (39.0, 195.0, 7.0), (70.0, 209.0, 9.0)):
        z0 = zr + (5.4 if x < 38.6 and y > 199 else 3.2)
        prim.cyl(B, (x, y, z0), (x, y, z0 + h), 0.05, 0.03, 5, 'metal_grey', tag='detail')
    # the glazed arcade around the foot of the bowl: a low glass ring with ribs and a flat roof
    cx, cy = TC
    ro, ri = 16.6, 14.6
    t = np.linspace(0, 2 * math.pi, 49)[:-1]
    ring_o = np.stack([cx + ro * np.cos(t), cy + ro * np.sin(t)], 1)
    ring_i = np.stack([cx + ri * np.cos(t), cy + ri * np.sin(t)], 1)
    U.vquads(B, ring_o, np.roll(ring_o, -1, axis=0), zr, zr + 2.7, 'glass', zg=zb)
    U.hquads(B, ring_o, ring_i, zr + 2.7, 'white_paint', up=True)
    U.hquads(B, ring_o, ring_i, zr + 2.7, 'white_paint', up=False)
    c = np.c_[ring_o, np.full(len(ring_o), zr)]
    nn = np.c_[np.cos(t), np.sin(t), np.zeros(len(t))]
    U.obox_batch(B, c, c + np.array([0, 0, 2.7]), 0.08, 0.1, 'white_paint', up=nn, tag='detail')
    U.obox_batch(B, np.c_[ring_o, np.full(48, zr + 1.1)], np.c_[np.roll(ring_o, -1, axis=0), np.full(48, zr + 1.1)], 0.05, 0.06, 'white_paint', up=(0, 0, 1), tag='detail')
    # flag poles in front of the bowl
    for dx in (-5.0, 0.0, 5.0):
        prim.cyl(B, (cx + dx, cy - 19.5, zr), (cx + dx, cy - 19.5, zr + 8.5), 0.06, 0.04, 5, 'metal_grey', tag='detail')
    B.lamp(cx - 12, cy - 16, zr + 3.0, 40, (1.0, 0.9, 0.7))
    B.lamp(cx + 12, cy - 16, zr + 3.0, 40, (1.0, 0.9, 0.7))

# ------------------------------------------------------------------------------------------------ the tower
BOWL = [(5.4, 0.0), (6.0, 0.9), (7.0, 2.5), (8.5, 4.7), (10.0, 7.1), (11.5, 9.7), (12.7, 12.4), (13.4, 14.8), (13.6, 15.9)]   # r, h above the roof
SHAFT_D = [(46.8, 11.8), (50.0, 10.5), (54.0, 9.6), (60.0, 8.7), (70.0, 7.8), (80.0, 7.1), (90.0, 6.5), (97.2, 6.2)]          # z above street, diameter

def build_tower(B, S, zb):
    cx, cy = TC
    zr = zb + ROOF_H
    UVS = 0.03
    # ---- the bowl: dark glazing between copper-brown ribs
    prof = U.smooth_profile(BOWL, 24)
    prof = [(r, zr + h) for (r, h) in prof]
    U.lathe_uv(B, (cx, cy, 0.0), prof, seg=72, mat='glass', uvs=0.5)
    nrib = 60
    th = np.arange(nrib) * 2 * math.pi / nrib
    p0 = []; p1 = []; ups = []
    for t in th:
        for j in range(len(prof) - 1):
            (r0, z0), (r1, z1) = prof[j], prof[j + 1]
            p0.append((cx + (r0 + 0.07) * math.cos(t), cy + (r0 + 0.07) * math.sin(t), z0))
            p1.append((cx + (r1 + 0.07) * math.cos(t), cy + (r1 + 0.07) * math.sin(t), z1))
            ups.append((math.cos(t), math.sin(t), 0.0))
    U.obox_batch(B, np.array(p0), np.array(p1), 0.17, 0.2, 'bronze', up=np.array(ups), ends=False, tag='main')
    # horizontal bands at a few heights
    for hh in (4.2, 8.2, 12.0):
        r = float(np.interp(hh, [p[1] - zr for p in prof], [p[0] for p in prof])) + 0.1
        pts = np.array([[cx + r * math.cos(a), cy + r * math.sin(a), zr + hh] for a in np.linspace(0, 2 * math.pi, 49)])
        U.polyline_tube(B, pts, 0.1, 'bronze', seg=4, tag='detail', caps=False)
    # rim fascia and the cap the shaft stands on
    rr = [(13.3, zr + 14.7), (13.9, zr + 15.1), (13.95, zr + 16.0), (13.5, zr + 16.1), (3.0, zr + 16.1)]
    U.lathe_uv(B, (cx, cy, 0.0), rr, seg=72, mat='white_paint', uvs=UVS)
    # lit panes in the bowl (interior lighting) -- a few per band between the ribs
    rngb = np.random.default_rng(31)
    bands = [(2, 5), (6, 9), (10, 13), (14, 17)]
    for i in range(nrib):
        a0, a1 = th[i], th[i] + 2 * math.pi / nrib
        for (j0, j1) in bands:
            if rngb.random() < 0.3:
                (r0, z0_), (r1, z1_) = prof[j0], prof[min(j1, len(prof) - 1)]
                q = []
                for (rr_, zz_, aa_) in ((r0, z0_, a0 + 0.02), (r0, z0_, a1 - 0.02), (r1, z1_, a1 - 0.02), (r1, z1_, a0 + 0.02)):
                    q.append((cx + (rr_ + 0.06) * math.cos(aa_), cy + (rr_ + 0.06) * math.sin(aa_), zz_))
                B.add(np.array(q), [[0, 1, 2], [0, 2, 3]], 'lamp', UV=np.array([[0, 0], [1, 0], [1, 1], [0, 1]]), tag='main')
    # floodlights at the foot of the shaft (the tower is lit white at night)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        B.lamp(cx + 12.0 * math.cos(a), cy + 12.0 * math.sin(a), zr + 17.2, 380, (1.0, 0.96, 0.88))
    # plinth where the bowl meets the roof
    prim.cyl(B, (cx, cy, zr), (cx, cy, zr + 0.5), 5.8, 5.6, 36, 'wall_concrete', c0=(110, 106, 100, 0), caps=(False, True))
    # ---- the shaft (concave flare, white steel plates)
    zs = np.array([p[0] for p in SHAFT_D]); ds = np.array([p[1] for p in SHAFT_D])
    z = np.linspace(46.8, 114.2, 56)
    d = np.interp(z, np.r_[zs, 114.2], np.r_[ds, 5.9])
    # smooth the flare with a monotone curve: d(z) = d_top + (d_bot - d_top) * ((z_top - z)/(z_top - z_bot))^p blended
    t = (97.2 - np.minimum(z, 97.2)) / (97.2 - 46.8)
    d = np.where(z < 97.2, 6.2 + 5.6 * (t ** 1.9) * 0.62 + 5.6 * 0.38 * (t ** 6.0), 6.2 - (z - 97.2) * 0.02)
    prof = [(dd / 2, zb + zz) for dd, zz in zip(d, z)]
    U.lathe_uv(B, (cx, cy, 0.0), prof, seg=40, mat='white_paint', uvs=UVS)
    # steel-plate seams: a ring every ~4.5 m (a very slight step), read as horizontal lines
    for zz in np.arange(50.0, 96.0, 4.6):
        dd = float(np.interp(zz, z, d)) / 2 + 0.03
        pts = np.array([[cx + dd * math.cos(a), cy + dd * math.sin(a), zb + zz] for a in np.linspace(0, 2 * math.pi, 41)])
        U.polyline_tube(B, pts, 0.035, 'white_paint', seg=4, tag='detail', caps=False)
    # ---- the observation deck
    _deck(B, zb, cx, cy)
    # ---- mast
    z0 = zb + 114.2
    r_sh = 2.95
    U.lathe_uv(B, (cx, cy, 0.0), [(r_sh, z0), (r_sh, z0 + 0.1), (3.4, z0 + 0.15), (3.4, z0 + 1.0), (2.2, z0 + 1.25)], seg=24, mat='vermilion', uvs=UVS)
    s = 1.3
    zm = z0 + 1.25
    # square mast: red lower part, white upper part
    U.box(B, cx - s, cy - s, zm, cx + s, cy + s, zm + 3.4, 'vermilion', faces='xXyY')
    U.box(B, cx - s, cy - s, zm + 3.4, cx + s, cy + s, zm + 9.2, 'white_paint', faces='xXyY')
    U.box(B, cx - s * 0.85, cy - s * 0.85, zm + 9.2, cx + s * 0.85, cy + s * 0.85, zm + 10.2, 'vermilion')
    U.box(B, cx - s, cy - s, zm + 3.4, cx + s, cy + s, zm + 3.55, 'metal_grey', faces='Zz')
    # whip antenna with red / white bands
    za = zm + 10.2
    top = zb + 131.0
    n = 5
    for i in range(n):
        za0 = za + (top - za) * i / n; za1 = za + (top - za) * (i + 1) / n
        prim.cyl(B, (cx, cy, za0), (cx, cy, za1), 0.14 - 0.016 * i, 0.14 - 0.016 * (i + 1), 6, 'vermilion' if i % 2 == 0 else 'white_paint', tag='main')
    # aircraft warning lamps (red) -- emissive spheres plus bake lamps
    for (zz, rr_, nn) in ((zb + 125.4, 0.9, 1), (zb + 119.0, 1.5, 4), (zb + 109.1, 9.5, 6), (zb + 114.6, 3.5, 4)):
        for i in range(nn):
            a = 2 * math.pi * i / max(nn, 1) + 0.4
            x = cx + (rr_ * math.cos(a) if nn > 1 else 0.0); y = cy + (rr_ * math.sin(a) if nn > 1 else 0.0)
            U.lathe_uv(B, (x, y, zz), [(0.0, -0.18), (0.22, -0.05), (0.26, 0.1), (0.15, 0.24), (0.0, 0.3)], seg=8, mat='lantern_paper', uvs=1.0, tag='detail')
            B.lamp(x, y, zz + 0.1, 12 if zz > zb + 120 else 6, RED_LAMP)
    B.lamp(cx, cy, zb + 130.8, 18, RED_LAMP)

def _deck(B, zb, cx, cy):
    UVS = 0.03
    z0 = zb + 97.2
    # red dish under the cabin (radial ribs read through the shader's paint; add ribs as geometry)
    dish = [(3.1, z0 - 0.2), (4.2, z0 + 0.0), (5.8, z0 + 0.6), (7.2, z0 + 1.5), (8.3, z0 + 2.6), (8.95, z0 + 3.7)]
    dish = U.smooth_profile(dish, 20)
    U.lathe_uv(B, (cx, cy, 0.0), [tuple(p) for p in dish], seg=60, mat='vermilion', uvs=UVS)
    nr = 48
    p0 = []; p1 = []; up = []
    for i in range(nr):
        a = 2 * math.pi * i / nr
        for j in range(0, len(dish) - 1, 2):
            (r0, zz0), (r1, zz1) = dish[j], dish[min(j + 2, len(dish) - 1)]
            p0.append((cx + (r0 - 0.04) * math.cos(a), cy + (r0 - 0.04) * math.sin(a), zz0 - 0.05))
            p1.append((cx + (r1 - 0.04) * math.cos(a), cy + (r1 - 0.04) * math.sin(a), zz1 - 0.05))
            up.append((math.cos(a), math.sin(a), -0.6))
    U.obox_batch(B, np.array(p0), np.array(p1), 0.08, 0.12, 'vermilion', up=np.array(up), tag='detail')
    # cabin: lower glazed band (alternating lit panes), ledge, upper glazed band, roof
    nseg = 40
    def cone(r0, zc0, r1, zc1, a):
        return None
    ang = np.linspace(0, 2 * math.pi, nseg + 1)
    rng = np.random.default_rng(97)
    rA0, zA0 = 8.95, z0 + 3.7
    rA1, zA1 = 9.45, z0 + 7.3
    for i in range(nseg):
        a0, a1 = ang[i], ang[i + 1]
        P = np.array([[cx + rA0 * math.cos(a0), cy + rA0 * math.sin(a0), zA0], [cx + rA0 * math.cos(a1), cy + rA0 * math.sin(a1), zA0],
                      [cx + rA1 * math.cos(a1), cy + rA1 * math.sin(a1), zA1], [cx + rA1 * math.cos(a0), cy + rA1 * math.sin(a0), zA1]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'glass', UV=np.array([[0, 0], [1, 0], [1, 1], [0, 1]]), tag='main')
        if rng.random() < 0.55:        # lit strip (interior lights seen through the glass)
            t0, t1 = 0.28, 0.5
            L0, L1, U1, U0 = P[0], P[1], P[2], P[3]
            Q = np.array([L0 + (U0 - L0) * t0, L1 + (U1 - L1) * t0, L1 + (U1 - L1) * t1, L0 + (U0 - L0) * t1])
            nrm = np.array([math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0.0]) * 0.03
            B.add(Q + nrm, [[0, 1, 2], [0, 2, 3]], 'lamp', UV=np.array([[0, 0], [1, 0], [1, 1], [0, 1]]), tag='main')
    # mullions
    mm = 80
    a = np.linspace(0, 2 * math.pi, mm, endpoint=False)
    p0 = np.stack([cx + (rA0 + 0.05) * np.cos(a), cy + (rA0 + 0.05) * np.sin(a), np.full(mm, zA0)], 1)
    p1 = np.stack([cx + (rA1 + 0.05) * np.cos(a), cy + (rA1 + 0.05) * np.sin(a), np.full(mm, zA1)], 1)
    U.obox_batch(B, p0, p1, 0.06, 0.08, 'metal_dark', up=np.stack([np.cos(a), np.sin(a), np.zeros(mm)], 1), tag='detail')
    # ledge / underside of the upper deck (cream), upper band, roof
    ledge = [(9.45, zA1), (10.35, zA1 + 0.1), (10.4, zA1 + 0.55), (9.5, zA1 + 0.62)]
    U.lathe_uv(B, (cx, cy, 0.0), ledge, seg=60, mat='white_paint', uvs=UVS)
    zB0 = zA1 + 0.62; zB1 = zB0 + 2.1
    U.lathe_uv(B, (cx, cy, 0.0), [(9.5, zB0), (9.3, zB1)], seg=60, mat='glass', uvs=0.5)
    a = np.linspace(0, 2 * math.pi, 60, endpoint=False)
    p0 = np.stack([cx + 9.55 * np.cos(a), cy + 9.55 * np.sin(a), np.full(60, zB0)], 1)
    p1 = np.stack([cx + 9.35 * np.cos(a), cy + 9.35 * np.sin(a), np.full(60, zB1)], 1)
    U.obox_batch(B, p0, p1, 0.06, 0.08, 'metal_dark', up=np.stack([np.cos(a), np.sin(a), np.zeros(60)], 1), tag='detail')
    roof = [(9.3, zB1), (9.9, zB1 + 0.05), (9.95, zB1 + 0.9), (9.2, zB1 + 1.0), (3.0, zB1 + 1.0)]
    U.lathe_uv(B, (cx, cy, 0.0), roof, seg=60, mat='vermilion', uvs=UVS)
    # the cage: two families of ribs leaning against each other, plus two rings
    pr = U.smooth_profile([(8.6, z0 + 2.9), (9.6, z0 + 4.0), (10.1, z0 + 5.8), (10.15, z0 + 7.4), (9.85, z0 + 9.2), (9.2, z0 + 10.6)], 14)
    nrb = 20
    for fam, twist in ((0, 0.16), (1, -0.16)):
        p0 = []; p1 = []; up = []
        for i in range(nrb):
            a0 = 2 * math.pi * i / nrb
            pts = []
            for k, (r, zz) in enumerate(pr):
                f = k / (len(pr) - 1)
                a = a0 + twist * f
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a), zz, a))
            for k in range(len(pts) - 1):
                p0.append(pts[k][:3]); p1.append(pts[k + 1][:3]); up.append((math.cos(pts[k][3]), math.sin(pts[k][3]), 0))
        U.obox_batch(B, np.array(p0), np.array(p1), 0.17, 0.2, 'vermilion', up=np.array(up), tag='main', ends=False)
    for (rr, zz) in ((10.15, z0 + 6.4), (9.3, z0 + 10.3), (8.8, z0 + 3.0)):
        pts = np.array([[cx + rr * math.cos(a), cy + rr * math.sin(a), zz] for a in np.linspace(0, 2 * math.pi, 61)])
        U.polyline_tube(B, pts, 0.1, 'vermilion', seg=6, tag='main', caps=False)
