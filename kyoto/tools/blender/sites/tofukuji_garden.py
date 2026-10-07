"""東福寺 本坊庭園 「八相の庭」 (重森三玲, 1939; 名勝 2014) round the 方丈:
  南庭  rough-sea raked sand (whirlpools round the stones, long waves elsewhere) with four stone groups — 瀛洲, 蓬莱,
        壺梁 and 方丈 (the islands of the immortals; OSM artwork nodes give their places) — and the 五山 moss mounds in the
        west corner;
  西庭  井田市松: clipped サツキ squares and raked-sand squares in a large checkerboard with cut-stone kerbs, moss to the south;
  北庭  小市松: square paving stones (from the 恩賜門 approach) and moss in a fine checkerboard that dissolves eastward,
        round azaleas along the valley side;
  東庭  北斗七星: seven 東司 pillar bases in the Big Dipper on a cloud-shaped band of raked sand in moss, a hedge behind.
Gardens are raised a few cm over the court with a stone kerb; visitors stay on the 方丈 verandas (gardens block).
World coordinates; layouts in the 方丈 frame (u east, v north)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
import mapbox_earcut as earcut
from jk import prim, arch
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK
from sites import tofukuji_halls as HL

ZGARD = 49.98
SMOOTH_V = 0.06          # sand_raked with constant uv.y = smoothed sand

def loc():
    return L.Loc(HL.HOJO_C[0], HL.HOJO_C[1], L.ROT)

def lpoly(world_ring):
    lc = loc()
    return Polygon([lc.l(x, y) for (x, y) in world_ring]).buffer(0)

# ------------------------------------------------------------------ surfaces
def flat_poly(B, poly, z, mat, uvfn=None, tag='main', c1=(0, 0, 0, 0)):
    polys = poly.geoms if hasattr(poly, 'geoms') else [poly]
    for p in polys:
        if p.is_empty or p.area < 0.02 or p.geom_type != 'Polygon': continue
        rings = [np.array(p.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in p.interiors]
        V = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
        if len(I) == 0: continue
        P = np.c_[V, np.full(len(V), z)]
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
        UV = uvfn(V) if uvfn else V.copy()
        B.add(P, I, mat, UV=UV, tag=tag, c1=c1)

def rings_mesh(B, cx, cy, r0, r1, z, clip, done, seg=48, nr=10):
    """concentric raked rings (uv.y = radius) round (cx, cy) from r0 to r1, triangles inside `clip` and outside `done`"""
    P = []; UV = []
    rs = np.linspace(r0, r1, nr + 1)
    for r in rs:
        for i in range(seg + 1):
            t = 2 * math.pi * i / seg
            P.append((cx + r * math.cos(t), cy + r * math.sin(t), z)); UV.append((t * r, r))
    P = np.array(P); UV = np.array(UV); I = []
    for j in range(nr):
        for i in range(seg):
            a = j * (seg + 1) + i
            I += [[a, a + 1, a + seg + 2], [a, a + seg + 2, a + seg + 1]]
    I = np.array(I)
    C = P[I].mean(1)
    keep = shapely.contains_xy(clip, C[:, 0], C[:, 1])
    if done is not None and not done.is_empty: keep &= ~shapely.contains_xy(done, C[:, 0], C[:, 1])
    I = I[keep]
    if len(I) == 0: return
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
    B.add(P, I, 'sand_raked', UV=UV)

def kerb(B, poly, z, h=0.16, w=0.22, zb=None):
    """cut-stone edging round a garden"""
    ring = np.array(poly.exterior.coords)
    zb = z - 0.35 if zb is None else zb
    for a, b in zip(ring[:-1], ring[1:]):
        prim.obox(B, (a[0], a[1], zb + (z + 0.05 - zb) / 2), (b[0], b[1], zb + (z + 0.05 - zb) / 2), w, z + 0.05 - zb, 'curb')

def gstone(B, x, y, zg, w, h, seed, shape='stand', aniso=(1.0, 1.0), yaw=None, mat='stone', tilt=0.05):
    """a garden stone with footprint radius w and visible height h above zg"""
    sz = 0.58 * h
    L.stone(B, (x, y, zg + h - sz), w, seed, mat=mat, flat=sz / w, sub=2, sink=0.0, aniso=aniso, tilt=tilt, yaw=yaw, shape=shape)

def lying(B, x, y, zg, length, w, h, yaw, seed, mat='stone'):
    """a long recumbent stone"""
    sz = 0.62 * h
    L.stone(B, (x, y, zg + h - sz), length / 2, seed, mat=mat, flat=sz / (length / 2), sub=2, sink=0.0, aniso=(1.0, (w / 2) / (length / 2) / 0.87), yaw=yaw, shape='round', tilt=0.02)

def mound(B, cx, cy, rx, ry, h, z, seed, seg=24):
    rng = np.random.default_rng(seed)
    rings = [(1.0, 0.0), (0.92, 0.3), (0.75, 0.62), (0.5, 0.86), (0.25, 0.97), (0.0, 1.0)]
    ph = rng.uniform(0, 6.28, 3)
    P = []
    for (r, t) in rings:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            k = 1 + 0.1 * math.sin(2 * a + ph[0]) + 0.06 * math.sin(3 * a + ph[1])
            P.append((cx + rx * r * k * math.cos(a), cy + ry * r * k * math.sin(a), z - 0.05 + h * t))
    I = []
    for j in range(len(rings) - 1):
        for i in range(seg):
            a0 = j * seg + i; a1 = j * seg + (i + 1) % seg
            I += [[a0, a1, a1 + seg], [a0, a1 + seg, a0 + seg]]
    P = np.array(P); I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
    B.add(P, I, 'moss_mound', smooth=True)

# ====================================================================== 南庭
def south(B, S):
    lc = loc()
    gp = lpoly(L.osm_poly(S, 'landuse', 775460459))
    # the garden runs from the veranda's rain gutter to the south wall
    a, c, w = HL.HOJO_L / 2, HL.HOJO_D / 2, HL.HOJO_VER
    vN = -c - w - 0.55
    x0, y0, x1, y1 = gp.bounds
    sand = box(x0, y1 - 13.0, x1, vN).intersection(gp.buffer(0.4, join_style=2)).buffer(0)
    sand = sand.difference(box(x0 - 1, vN - 0.01, x1 + 1, vN + 5))
    z = ZGARD
    groups = {}
    for nm, wid in (('eishu', '瀛洲'), ('horai', '蓬莱'), ('koryo', '壺梁'), ('hojo', '方丈'), ('gozan', '五山')):
        for p in S.osm['points']:
            if p['tags'].get('name') == wid and p['tags'].get('tourism') == 'artwork':
                groups[nm] = np.array(lc.l(*p['xy']))
    # stone groups (local offsets from the OSM artwork nodes); heights from the photos (Shigemori, Zairon)
    E = groups.get('eishu', np.array([13.3, -19.0])); Hr = groups.get('horai', np.array([6.8, -18.6]))
    Kr = groups.get('koryo', np.array([-0.6, -18.6])); Hj = groups.get('hojo', np.array([-13.4, -18.6]))
    G5 = groups.get('gozan', np.array([-22.2, -17.3]))
    stones = []
    # 瀛洲: tall jagged stones and a long lying stone
    stones += [('s', E + (-0.9, 1.4), 0.62, 2.55, 11), ('s', E + (0.1, 2.0), 0.5, 1.9, 12), ('s', E + (1.2, 1.2), 0.55, 2.2, 13), ('s', E + (1.9, 2.3), 0.45, 1.5, 14),
               ('l', E + (-0.4, -0.3), 4.2, 0.85, 0.75, 0.25, 15), ('s', E + (1.4, -0.6), 0.45, 1.25, 16), ('r', E + (-2.4, 0.6), 0.45, 0.55, 17), ('r', E + (2.7, 0.2), 0.38, 0.45, 18)]
    # 蓬莱: the long recumbent stone, two tall stones beside it
    stones += [('l', Hr + (0.0, 0.0), 5.2, 1.0, 0.85, -0.18, 21), ('s', Hr + (-1.8, 0.9), 0.55, 1.95, 22), ('s', Hr + (1.4, 1.0), 0.5, 1.55, 23),
               ('r', Hr + (2.6, -0.3), 0.42, 0.6, 24), ('r', Hr + (-3.0, -0.5), 0.35, 0.4, 25)]
    # 壺梁
    stones += [('s', Kr + (0.2, 0.5), 0.5, 1.7, 31), ('l', Kr + (-0.8, -0.4), 2.8, 0.8, 0.6, 0.1, 32), ('r', Kr + (1.3, -0.2), 0.4, 0.55, 33)]
    # 方丈
    stones += [('s', Hj + (0.0, 0.3), 0.45, 1.45, 41), ('r', Hj + (0.9, -0.3), 0.42, 0.6, 42), ('r', Hj + (-0.8, -0.2), 0.32, 0.35, 43)]
    # rings round the groups, long waves elsewhere
    circles = [(E + (0.4, 0.8), 4.4), (Hr + (0.0, 0.3), 4.6), (Kr + (0.0, 0.0), 3.4), (Hj + (0.0, 0.0), 2.8), (np.array([-6.5, -15.2]), 2.2), (np.array([10.0, -14.0]), 1.9)]
    done = Polygon()
    for (cxy, r) in circles:
        rings_mesh(B, cxy[0], cxy[1], 0.3, r, z, sand, done, seg=56, nr=max(6, int(r / 0.3)))
        done = done.union(Point(*cxy).buffer(r, 32))
    rest = sand.difference(done).buffer(0)
    # long waves: lines along u with a slow swell (uv.y = v + wave(u))
    flat_poly(B, rest, z, 'sand_raked', uvfn=lambda V: np.c_[V[:, 0], V[:, 1] + 0.35 * np.sin(V[:, 0] * 0.42)])
    kerb(B, sand, z)
    zs = z
    for st in stones:
        if st[0] == 's': gstone(B, st[1][0], st[1][1], zs, st[2], st[3], st[4] + 100)
        elif st[0] == 'r': gstone(B, st[1][0], st[1][1], zs, st[2], st[3], st[4] + 100, shape='round')
        else: lying(B, st[1][0], st[1][1], zs, st[2], st[3], st[4], st[5], st[6] + 100)
    # 五山: five moss mounds in the west corner (a pine on the largest)
    for (du, dv, rx, ry, h, sd) in ((0.0, 0.0, 2.9, 2.2, 1.15, 1), (3.0, -2.6, 2.3, 1.8, 0.9, 2), (-2.6, -2.9, 2.0, 1.7, 0.8, 3), (4.2, 0.9, 1.7, 1.4, 0.6, 4), (-0.6, 2.8, 1.5, 1.3, 0.55, 5)):
        mound(B, G5[0] + du, G5[1] + dv, rx, ry, h, z, 50 + sd)
    B.tree('matsu', G5[0] - 0.3, G5[1] + 0.2, z + 1.0, 0.42, 0.7)
    # blocker over the garden
    K.block_poly(B, list(np.array(sand.buffer(-0.2).exterior.coords)[:-1]))
    return sand

# ====================================================================== 西庭
def west(B, S):
    gp = lpoly(L.osm_poly(S, 'landuse', 775460457))
    x0, y0, x1, y1 = gp.bounds
    a, c, w = HL.HOJO_L / 2, HL.HOJO_D / 2, HL.HOJO_VER
    xr = min(x1, -a - w - 0.5)
    g = box(x0 + 0.2, y0 + 0.2, xr, y1 - 0.2)
    z = ZGARD
    cell = (xr - x0 - 0.2) / 3.0
    nrow = int((y1 - y0 - 0.4) / cell)
    yb = y1 - 0.2 - nrow * cell
    # moss in the south part with a wavy edge
    edge = [(x0 - 1, yb + 2.2 * cell)]
    for t in np.linspace(0, 1, 16):
        edge.append((x0 + (xr - x0) * t, yb + cell * (2.0 + 0.55 * math.sin(t * 5.0 + 0.7))))
    edge += [(xr + 1, yb + 2.2 * cell), (xr + 1, y0 - 1), (x0 - 1, y0 - 1)]
    moss = g.intersection(Polygon(edge).buffer(0))
    flat_poly(B, moss, z + 0.03, 'moss_mound')
    rest = g.difference(moss)
    flat_poly(B, rest, z, 'sand_raked', uvfn=lambda V: np.c_[V[:, 1], V[:, 0] * 1.0])
    # checkerboard: サツキ squares (clipped boxes) / sand squares with kerbs
    for j in range(nrow):
        for i in range(3):
            cx = x0 + 0.2 + (i + 0.5) * cell; cy = yb + (j + 0.5) * cell
            sq = box(cx - cell / 2, cy - cell / 2, cx + cell / 2, cy + cell / 2)
            if sq.intersection(moss).area > 0.5 * sq.area: continue
            for (p0, p1) in (((cx - cell / 2, cy - cell / 2), (cx + cell / 2, cy - cell / 2)), ((cx - cell / 2, cy + cell / 2), (cx + cell / 2, cy + cell / 2))):
                prim.obox(B, (p0[0], p0[1], z - 0.02), (p1[0], p1[1], z - 0.02), 0.16, 0.14, 'curb', tag='detail')
            if (i + j) % 2 == 0:
                hh = 0.65 + 0.12 * ((i * 7 + j * 3) % 3)
                s_ = cell * 0.47
                P = np.array([(cx - s_, cy - s_, z), (cx + s_, cy - s_, z), (cx + s_, cy + s_, z), (cx - s_, cy + s_, z),
                              (cx - s_ * 0.9, cy - s_ * 0.9, z + hh), (cx + s_ * 0.9, cy - s_ * 0.9, z + hh), (cx + s_ * 0.9, cy + s_ * 0.9, z + hh), (cx - s_ * 0.9, cy + s_ * 0.9, z + hh)])
                I = [[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7], [4, 5, 6], [4, 6, 7]]
                B.add(P, I, 'hedge')
    # a pair of upright stones at the north-west corner (as in the photo)
    gstone(B, x0 + 0.9, y1 - 0.9, z, 0.22, 0.95, 301); gstone(B, x0 + 1.3, y1 - 1.2, z, 0.18, 0.6, 302, shape='round')
    kerb(B, g, z)
    K.block_poly(B, [(x0 + 0.3, y0 + 0.3), (xr - 0.1, y0 + 0.3), (xr - 0.1, y1 - 0.3), (x0 + 0.3, y1 - 0.3)])
    return g

# ====================================================================== 北庭
def north(B, S):
    gp = lpoly(L.osm_poly(S, 'landuse', 775460456))
    x0, y0, x1, y1 = gp.bounds
    a, c, w = HL.HOJO_L / 2, HL.HOJO_D / 2, HL.HOJO_VER
    ut = loc().l(1383.0, -957.0)[0]
    xa = max(x0, ut + 2.9); xb = x1 - 0.2
    ya = c + w + 0.55; yb = max(y1 - 0.2, ya + 4.2)
    g = box(xa, ya, xb, yb)
    z = ZGARD - 0.05
    flat_poly(B, g, z, 'moss_mound')
    rng = np.random.default_rng(9)
    s = 0.62
    nx = int((xb - xa) / s); ny = int((yb - ya) / s)
    for i in range(nx):
        t = i / max(nx - 1, 1)
        keep_p = 1.0 if t < 0.45 else max(0.0, 1.0 - (t - 0.45) / 0.5) ** 1.4
        for j in range(ny):
            cx = xa + (i + 0.5) * s; cy = ya + (j + 0.5) * s
            if (i + j) % 2 == 0:
                if rng.random() > keep_p: continue
                hs = s * 0.46
                prim.box(B, cx - hs, cy - hs, z - 0.05, cx + hs, cy + hs, z + 0.035, 'stone', faces='xXyYZ', c1=(0, 3, int(rng.integers(255)), 0))
            else:
                if rng.random() < 0.6:                 # moss cushions
                    hs = s * 0.48; hh = rng.uniform(0.04, 0.09)
                    P = np.array([(cx - hs, cy - hs, z), (cx + hs, cy - hs, z), (cx + hs, cy + hs, z), (cx - hs, cy + hs, z),
                                  (cx - hs * 0.8, cy - hs * 0.8, z + hh), (cx + hs * 0.8, cy - hs * 0.8, z + hh), (cx + hs * 0.8, cy + hs * 0.8, z + hh), (cx - hs * 0.8, cy + hs * 0.8, z + hh)])
                    I = [[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7], [4, 5, 6], [4, 6, 7]]
                    B.add(P, I, 'moss_mound', tag='detail')
    # round clipped azaleas along the valley side, a few maples behind
    for x in np.arange(xa + 0.8, xb, 1.7):
        B.tree('tsutsuji', x + rng.uniform(-0.3, 0.3), yb + 0.6, z, rng.uniform(1.0, 1.4), rng.uniform(0, 6.28))
    for x in np.arange(xa + 3.0, xb, 6.0):
        B.tree('momiji', x, yb + 3.2, float(S.ground(*loc().w(x, yb + 3.2))), rng.uniform(1.0, 1.3), rng.uniform(0, 6.28))
    # the wavy iron edging along the veranda side (as in the photo): a low dark strip
    pts = np.array([(xa + t, ya + 0.08 + 0.05 * math.sin(t * 9.0), z + 0.05) for t in np.linspace(0, xb - xa, 120)])
    prim.sweep(B, pts, [(-0.02, -0.06), (0.02, -0.06), (0.02, 0.06), (-0.02, 0.06)], 'metal_dark', tag='detail')
    K.block_poly(B, [(xa, ya + 0.2), (xb, ya + 0.2), (xb, yb), (xa, yb)])
    return g

# ====================================================================== 東庭
DIPPER = [(11.062, 61.75), (11.031, 56.38), (11.897, 53.69), (12.257, 57.03), (12.900, 55.96), (13.399, 54.93), (13.792, 49.31)]

def east(B, S):
    gp = lpoly(L.osm_poly(S, 'landuse', 775460458))
    x0, y0, x1, y1 = gp.bounds
    g = box(x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2)
    z = ZGARD
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # Big Dipper in the plan (as seen in the sky: RA to the left), scaled into the garden, the bowl to the north
    dm = np.mean([d for _, d in DIPPER])
    P = np.array([(-(ra - 12.4) * 15 * math.cos(math.radians(dm)), dec - 55.5) for ra, dec in DIPPER])
    P = P @ np.array([[0, -1], [1, 0]])       # turn: handle runs south
    P = P - P.mean(0)
    ext = P.max(0) - P.min(0)
    k = min((x1 - x0 - 2.6) / max(ext[0], 1e-3), (y1 - y0 - 2.6) / max(ext[1], 1e-3))
    P = P * k + (cx, cy)
    # cloud band of raked sand through the stones, moss around
    band = LineString(L.chaikin(P, 2)).buffer(1.25, 24).union(unary_union([Point(*p).buffer(1.3, 24) for p in P])).intersection(g).buffer(0)
    moss = g.difference(band)
    flat_poly(B, moss, z + 0.03, 'moss_mound')
    done = Polygon()
    for p in P:
        rings_mesh(B, p[0], p[1], 0.3, 1.3, z, band, done, seg=36, nr=4)
        done = done.union(Point(*p).buffer(1.3, 24))
    flat_poly(B, band.difference(done).buffer(0), z, 'sand_raked', uvfn=lambda V: np.c_[V[:, 1], V[:, 0]])
    # the seven pillar bases (granite cylinders, 0.6-0.75 m, 0.45-1.1 m tall)
    rng = np.random.default_rng(77)
    for i, p in enumerate(P):
        r = rng.uniform(0.3, 0.38); h = rng.uniform(0.45, 1.1)
        prim.cyl(B, (p[0], p[1], z - 0.2), (p[0], p[1], z + h), r, r * 0.97, 20, 'stone', caps=(False, True), c1=(0, 3, i * 30, 0))
    kerb(B, g, z)
    # hedge on the outer (east) side
    lc = loc()
    arch.hedge(B, [(x1 + 0.3, y0 + 0.4), (x1 + 0.3, y1 - 0.4)], z, h=1.25, w=0.8)
    K.block_poly(B, [(x0 + 0.3, y0 + 0.3), (x1 - 0.3, y0 + 0.3), (x1 - 0.3, y1 - 0.3), (x0 + 0.3, y1 - 0.3)])
    return g

def build(B, S):
    lc = loc()
    out = {}
    with lc.frame(B):
        out['south'] = south(B, S)
        out['west'] = west(B, S)
        out['north'] = north(B, S)
        out['east'] = east(B, S)
    # paint the generic ground under / round the gardens (sand / moss) so its edges match
    for nm, sf in (('south', 'sand'), ('west', 'moss'), ('north', 'moss'), ('east', 'moss')):
        g = out[nm]
        S.paint.append({'poly': [list(map(float, lc.w(*p))) for p in np.array(g.exterior.coords)], 'surf': sf})
    return out
