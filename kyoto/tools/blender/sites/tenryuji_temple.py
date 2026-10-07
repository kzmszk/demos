"""天龍寺: the gates (総門, 中門, 勅使門, 北門), 放生池 with its stone bridge, 法堂 (選佛場, with the cloud dragon on its
ceiling), 唐門, 大方丈 (広縁 + 落縁, the garden veranda), 小方丈 (書院), 庫裏 (the great white gable with its timber
grid, 越屋根 and the 達磨図 screen), 多宝殿 with its 向拝 and the climbing covered corridor.

Orientation: the temple faces east (勅使門 → 放生池 → 法堂 → 大方丈 → 曹源池 on one axis at y ≈ 3313); the approach from
the 総門 on 長辻通 runs west to the 庫裏.  Heights from the DEM (T.P.); PLATEAU: 法堂 13.4 m, hojo complex 12.6 m,
勅使門 7.0 m, 中門 7.3 m, 多宝殿 10.7 m."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from jk import prim, arch, Frame
from jk import roof as jroof
from . import tenryuji_kit as K
from .tenryuji_kit import Loc, facing, ribbon, quad, rect_walk, WD, WHITE, nrm

# generic (PLATEAU) buildings replaced here, by OSM way id of the matching footprint
REPLACED = [319572959, 319185106, 319572984, 319185054, 319185116, 427255578, 427255580, 319185029, 427255583, 319572922, 430453487,
            319572991, 319572996, 319572999, 319572997]

HOJO_ZF = 43.70          # 大方丈 floor (the garden ground by its west veranda is ~43.25, the pond 42.75)

class Roof2(jroof.Roof):
    """a jk roof that can leave out its gable walls (the 庫裏 builds its own timber-framed gables)"""
    def __init__(self, *a, no_gable_wall=False, **k):
        super().__init__(*a, **k); self.no_gable_wall = no_gable_wall
    def gable(self, B, u_g, s_from, vo):
        if not self.no_gable_wall: return super().gable(B, u_g, s_from, vo)
        # bargeboards + verge + 降棟 + 懸魚 only (copied from jk.roof.Roof.gable without the wall)
        c = self.c
        ss = np.linspace(s_from, c, 10)
        for sgn in (-1, 1):
            u = sgn * u_g
            ue = u + sgn * vo
            for side in (-1, 1):
                pts = np.array([(ue, side * (c - s), float(self.z(s, c)) - self.edge * 0.6) for s in ss])
                prim.sweep(B, pts, [(-0.07, 0.0), (0.07, 0.0), (0.07, -0.5), (-0.07, -0.5)], self.bargeboard_mat, up=(0, 0, 1), tag=self.tag, caps=True)
                pe = np.array([(ue, side * (c - s), float(self.z(s, c))) for s in ss])
                prim.sweep(B, pe, [(-0.12, -self.edge * 0.55), (0.12, -self.edge * 0.55), (0.12, 0.03), (-0.12, 0.03)], self.mat, up=(0, 0, 1), tag=self.tag, caps=True)
                self.ridge(B, pe[::-1] + np.array([-sgn * 0.25, 0, 0.02]), self.ridge_w * 0.55, self.ridge_h * 0.5, ends=(None, 'oni' if self.ends else None))
            # 懸魚 (a carved pendant, larger) under the apex
            za = float(self.z(c, c)) - self.edge - 0.55
            gp = [(-0.75, 0.3), (0.75, 0.3), (0.6, -0.2), (0.3, -0.55), (0.0, -0.95), (-0.3, -0.55), (-0.6, -0.2)]
            P = np.array([(ue + sgn * 0.06, y, za + z) for (y, z) in gp])
            I = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5], [0, 5, 6]]
            if sgn < 0: I = [t[::-1] for t in I]
            B.add(P, I, self.bargeboard_mat, tag='main')
            for (y, z) in ((-0.42, -0.1), (0.42, -0.1), (0.0, -0.45)):
                prim.cyl(B, (ue + sgn * 0.08, y, za + z), (ue + sgn * 0.16, y, za + z), 0.1, 0.1, 8, 'metal_dark', tag='detail')

# ------------------------------------------------------------------ wall planes with openings (timber-framed facades)
def wall_poly(B, p0, d, n, ring, mat, holes=(), off=0.0, tag='main', **kw):
    """a vertical polygon in the plane through p0 spanned by d (2D unit, along) and z: ring = [(s, z)], facing n"""
    import mapbox_earcut as earcut
    rings = [np.asarray(ring, float)] + [np.asarray(h, float) for h in holes]
    V = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
    p0 = np.asarray(p0, float); d = np.asarray(d, float); n = np.asarray(n, float)
    P = np.c_[p0[0] + d[0] * V[:, 0] + n[0] * off, p0[1] + d[1] * V[:, 0] + n[1] * off, V[:, 1]]
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if (fn[:, :2] @ n).sum() < 0: I = I[:, ::-1]
    B.add(P, I, mat, UV=V.copy(), tag=tag, **kw)

def timber_facade(B, p0, d, n, z0, top, posts, beams, windows=(), doors=(), plaster=WHITE, post_w=0.24, beam_h=0.2, beam_w=0.16, top_beams=None, tag='main', door_depth=2.5):
    """a white plaster wall with a dark timber grid in front (庫裏 style).  Coordinates along the wall: s from p0
    (direction d), z absolute; top(s) gives the wall's top (flat or a gable); posts = [s], beams = [(z, s0, s1)],
    windows = [(s0, s1, z0, z1)] (dark lattice 連子), doors = [(s0, s1, z0, z1)] (dark openings)"""
    p0 = np.asarray(p0, float); d = np.asarray(d, float); n = np.asarray(n, float)
    s0, s1 = min(posts), max(posts)
    ss = np.linspace(s0, s1, 25)
    ring = [(s0, z0), (s1, z0)] + [(s, top(s)) for s in ss[::-1]]
    holes = [[(a, b), (c, b), (c, e), (a, e)][::-1] for (a, c, b, e) in list(windows) + list(doors)]
    wall_poly(B, p0, d, n, ring, 'temple_wall', holes=holes, c0=plaster, tag=tag)
    wall_poly(B, p0, d, -n, ring, 'temple_wall', holes=holes, off=-0.12, c0=plaster, tag=tag)
    P = lambda s, z, o=0.0: np.r_[p0 + d * s + n * o, z]
    for s in posts:
        prim.obox(B, P(s, z0 - 0.05, 0.02), P(s, top(s) - 0.05, 0.02), post_w, 0.14, WD, up=(n[0], n[1], 0), tag=tag)
    for (z, a, b) in beams:
        za, zb = min(z, top(a) - 0.1), min(z, top(b) - 0.1)
        prim.obox(B, P(a - 0.08, za, 0.06), P(b + 0.08, zb, 0.06), beam_h, beam_w, WD, up=(n[0], n[1], 0), tag=tag)
    for (a, c, b, e) in windows:
        wall_poly(B, P(0, 0, -0.25)[:2], d, n, [(a, b), (c, b), (c, e), (a, e)], 'glass', tag=tag)
        for k in range(4):            # reveals
            pass
        for s in np.arange(a + 0.06, c - 0.02, 0.11):
            prim.obox(B, P(s, b, -0.05), P(s, e, -0.05), 0.04, 0.05, WD, up=(n[0], n[1], 0), tag='detail', ends=False)
        prim.obox(B, P(a, b - 0.04, 0.0), P(c, b - 0.04, 0.0), 0.08, 0.14, WD, up=(n[0], n[1], 0), tag=tag)
        prim.obox(B, P(a, e + 0.04, 0.0), P(c, e + 0.04, 0.0), 0.08, 0.14, WD, up=(n[0], n[1], 0), tag=tag)
        for s in (a, c):
            quad(B, P(s, b, 0.0), P(s, e, 0.0), P(s, e, -0.25), P(s, b, -0.25), WD, tag=tag, out=np.r_[d * (1 if s == a else -1), 0])
    for (a, c, b, e) in doors:
        dd_ = door_depth
        wall_poly(B, P(0, 0, -dd_)[:2], d, n, [(a, b), (c, b), (c, e), (a, e)], WD, tag=tag)
        for s in (a, c):
            quad(B, P(s, b, 0.0), P(s, e, 0.0), P(s, e, -dd_), P(s, b, -dd_), WD, tag=tag, out=np.r_[d * (1 if s == a else -1), 0])
        quad(B, P(a, e, 0.0), P(c, e, 0.0), P(c, e, -dd_), P(a, e, -dd_), WD, tag=tag, out=(0, 0, -1))

# ------------------------------------------------------------------ gates
def somon(B, S):
    """総門: the gate on 長辻通 (高麗門-like 薬医門 with the 大本山天龍寺 sign), facing east"""
    yaw = facing(12.0)
    c = np.array([-7468.2, 3347.6]); dvec = np.array([math.cos(yaw + math.pi / 2), math.sin(yaw + math.pi / 2)])       # local v (west-ish)
    o = c - dvec * 0.9
    loc = Loc(o[0], o[1], yaw)
    zg = 39.25
    K.gate(B, S, loc, zg=zg, span=3.3, depth=1.8, H=3.5, r=0.24, roof_L=6.6, roof_D=3.9, pitch=0.7, cover='hongawara', doors='open', wings=(1.0, 2.6))
    with loc.frame(B):
        # the sign board 大本山天龍寺 on the right pillar
        prim.box(B, 1.65 - 0.2, -0.32, zg + 0.6, 1.65 + 0.2, -0.26, zg + 3.0, 'wood_natural', tag='detail')
    return loc

def chumon(B, S):
    """中門 (慶長): 薬医門 in white walls, on the approach, facing east"""
    yaw = facing(-6.0)
    c = np.array([-7510.8, 3342.4])
    loc = Loc(c[0] + 1.2, c[1], yaw)
    zg = 39.2
    K.gate(B, S, loc, zg=zg, span=3.8, depth=2.4, H=3.9, r=0.27, roof_L=8.2, roof_D=6.0, pitch=0.72, teri=1.5, cover='hongawara', doors='open')
    # white walls (築地塀 with tiled coping) north and south of the gate
    for sgn in (-1, 1):
        a = loc.w(sgn * 2.6, 1.2); b = loc.w(sgn * (11.0 if sgn > 0 else 17.2), 1.2)
        K.wall(B, S, [a, b], h=2.3, th=0.55, stripes=0)
    return loc

def chokushimon(B, S):
    """勅使門 (四脚門, 慶長, moved here 1641; the oldest building of the temple): heavy curved kirizuma roof, closed
    doors, a lattice fence in front and 練塀 (earthen walls with tile courses) to the sides"""
    yaw = facing(-7.0)
    c = np.array([-7513.0, 3314.7])
    depth = 3.0
    dv = np.array([-math.sin(yaw), math.cos(yaw)])
    o = c - dv * depth / 2
    loc = Loc(o[0], o[1], yaw)
    zg = 39.1
    K.gate(B, S, loc, zg=zg, span=4.3, depth=depth, H=4.1, r=0.3, back_r=0.24, roof_L=9.2, roof_D=7.4, pitch=0.78, teri=1.8, sori=0.22,
           cover='hongawara', doors='closed', block_doors=True, kabuki_h=0.55)
    # the lattice fence (柵) in front, world coordinates
    for (u0, u1) in ((-5.2, -0.9), (0.9, 5.2)):
        K.simple_rail(B, [loc.w(u0, -2.6), loc.w(u1, -2.6)], lambda x, y: zg, h=1.25, post=0.14, rails=2, block=False)
    # the fence as world geometry lines (block)
    K.block_line(B, [loc.w(-5.2, -2.6), loc.w(5.2, -2.6)], 0.4)
    for sgn in (-1, 1):
        a = loc.w(sgn * 2.8, depth / 2); b = loc.w(sgn * 9.6, depth / 2)
        K.earth_wall(B, S, [a, b], h=2.4, th=0.7)
    return loc

def kitamon(B, S):
    """北門 (1983): the gate from the garden onto the bamboo path"""
    yaw = math.radians(200.6)
    c = np.array([-7897.0, 3478.6])
    loc = Loc(c[0], c[1], yaw)
    zg = float(S.ground(*c))
    K.gate(B, S, loc, zg=zg, span=3.0, depth=1.8, H=3.3, r=0.2, roof_L=6.0, roof_D=4.2, pitch=0.72, cover='sangawara', doors='open', wings=(0.9, 2.3))
    return loc

# ------------------------------------------------------------------ 放生池 (lotus pond) and the stone bridge on the axis
def hojoike(B, S):
    f = [w for w in S.osm['water'] if w['id'] == 427163570][0]
    P = K.osm_poly(f)
    pond = P.buffer(-0.3).buffer(0.3)
    WL = 38.75
    region = pond.buffer(2.6)
    zb = lambda x, y: float(S.ground(x, y))
    shapely.prepare(pond)
    def h(x, y):
        p = Point(x, y)
        if pond.contains(p):
            dd = pond.exterior.distance(p)
            return WL - 0.5 - 0.5 * min(1.0, dd / 2.5)
        return max(zb(x, y), WL + 0.5)
    def surf(x, y):
        return K.SID['riverbed'] if pond.contains(Point(x, y)) else K.SID['gravel']
    K.mesh_region(B, region, h, 0.7, surf_of=surf, walk_of=lambda x, y: not pond.buffer(0.2).contains(Point(x, y)))
    S.cut.append([list(map(list, region.exterior.coords))])
    K.water(B, pond, WL)
    # cut-stone revetment (a vertical stone edge 0.55 m)
    ring = np.array(pond.exterior.coords)
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        za, zb_ = max(zb(*a), WL + 0.5), max(zb(*b), WL + 0.5)
        quad(B, (a[0], a[1], WL - 0.3), (b[0], b[1], WL - 0.3), (b[0], b[1], zb_), (a[0], a[1], za), 'stone', both=True, c1=(0, 3, 0, 0))
        prim.obox(B, (a[0], a[1], za + 0.02), (b[0], b[1], zb_ + 0.02), 0.35, 0.06, 'curb', tag='detail')
    K.block_poly(B, pond.buffer(-0.1).difference(box(-7556.0, 3310.6, -7541.0, 3314.6)))
    # the stone bridge on the axis (y ≈ 3312.6) across the middle channel
    y0 = 3312.6; xa, xb = -7553.5, -7543.5
    zt = WL + 0.95
    w = 3.2
    pts = []
    for t in np.linspace(0, 1, 9):
        x = xa + (xb - xa) * t
        pts.append((x, zt + 0.25 * math.sin(math.pi * t)))
    for (x0_, z0_), (x1_, z1_) in zip(pts[:-1], pts[1:]):
        quad(B, (x0_, y0 - w / 2, z0_), (x1_, y0 - w / 2, z1_), (x1_, y0 + w / 2, z1_), (x0_, y0 + w / 2, z0_), 'stone', out=(0, 0, 1))
        for sg in (-1, 1):
            quad(B, (x0_, y0 + sg * w / 2, z0_), (x1_, y0 + sg * w / 2, z1_), (x1_, y0 + sg * w / 2, WL - 0.2), (x0_, y0 + sg * w / 2, WL - 0.2), 'stone', out=(0, sg, 0))
            # parapet (low stone rail)
            prim.obox(B, (x0_, y0 + sg * (w / 2 - 0.15), z0_ + 0.38), (x1_, y0 + sg * (w / 2 - 0.15), z1_ + 0.38), 0.22, 0.18, 'stone', tag='detail')
    for x in (xa, xb):
        for sg in (-1, 1):
            prim.box(B, x - 0.15, y0 + sg * (w / 2 - 0.15) - 0.15, zt - 0.2, x + 0.15, y0 + sg * (w / 2 - 0.15) + 0.15, zt + 0.75, 'stone')
    W = np.array([(x, y0, z + 0.02) for (x, z) in pts])
    ribbon(B, np.r_[[[xa - 1.2, y0, zt - 0.05]], W, [[xb + 1.2, y0, zt - 0.05]]], w - 0.6, 'walk')
    for sg in (-1, 1):
        ribbon(B, [(xa - 0.2, y0 + sg * (w / 2 - 0.1)), (xb + 0.2, y0 + sg * (w / 2 - 0.1))], 0.3, 'block')
    # ramps from the gravel onto the bridge
    for (xe, sgn) in ((xa, -1), (xb, 1)):
        ze = float(S.ground(xe + sgn * 3.0, y0))
        quad(B, (xe, y0 - w / 2, zt), (xe + sgn * 2.6, y0 - w / 2, ze + 0.05), (xe + sgn * 2.6, y0 + w / 2, ze + 0.05), (xe, y0 + w / 2, zt), 'stone', out=(0, 0, 1))
        ribbon(B, [(xe, y0, zt), (xe + sgn * 2.8, y0, ze)], w - 0.4, 'walk')
    # lotus pads (flat discs on the water)
    rng = np.random.default_rng(3)
    for k in range(70):
        x = rng.uniform(-7563, -7529); y = rng.uniform(3293, 3333)
        if not pond.buffer(-0.8).contains(Point(x, y)) or abs(y - y0) < 3: continue
        r = rng.uniform(0.18, 0.4)
        prim.cyl(B, (x, y, WL + 0.005), (x, y, WL + 0.03), r, r, 7, 'hedge', caps=(False, True), tag='detail')
    return pond

# ------------------------------------------------------------------ 法堂
def hatto(B, S):
    """法堂 (選佛場): a 禅堂 moved here in 1899; 寄棟 本瓦, white plaster between dark posts and tie beams, 花頭窓,
    on a 1.1 m stone 基壇 with steps on the axis; inside: stone floor, the 雲龍図 (加山又造 1997, 9 m circle) on the ceiling"""
    yaw = facing(0.3)
    loc = Loc(-7701.5, 3312.0, yaw)
    zg = 41.3
    zf = 42.45
    L, D = 21.0, 15.6
    us, vs = arch.grid(L, D, 7, 5)
    with loc.frame(B):
        # 基壇: rubble masonry with a dressed coping
        Pl = [(-L / 2 - 1.6, -D / 2 - 1.6), (L / 2 + 1.6, -D / 2 - 1.6), (L / 2 + 1.6, D / 2 + 1.6), (-L / 2 - 1.6, D / 2 + 1.6)]
        prim.prism(B, Pl, zg - 0.4, zf - 0.12, 'stone', top=False)
        for (a, b) in zip(Pl, Pl[1:] + Pl[:1]):
            prim.obox(B, (a[0], a[1], zf - 0.06), (b[0], b[1], zf - 0.06), 0.4, 0.14, 'curb')
        prim.polygon(B, Pl, zf, 'stone')
        prim.polygon(B, Pl, zf, 'stone', tag='walk')
        # steps on the axis (front = v-) and at the back
        K.stairs_build(B, (0, -D / 2 - 1.6 - 1.9), (0, -D / 2 - 1.6), zg, zf, 4.6, 'stone', riser=0.16)
        for sx in (-1, 1):
            prim.obox(B, (sx * 2.45, -D / 2 - 1.6 - 1.9, zg + 0.25), (sx * 2.45, -D / 2 - 1.6, zf + 0.1), 0.3, 0.3, 'curb')
        K.stairs_build(B, (0, D / 2 + 1.6 + 1.6), (0, D / 2 + 1.6), zg + 0.4, zf, 2.4, 'stone', riser=0.16)
    walls = {0: ['white', 'katomado', 'board', 'open', 'board', 'katomado', 'white'],
             1: ['white', 'katomado', 'board', 'katomado', 'white'],
             2: ['white', 'white', 'white', 'board', 'white', 'white', 'white'],
             3: ['white', 'katomado', 'board', 'katomado', 'white']}
    res = K.hall(B, S, loc, L=L, D=D, nu=7, nv=5, zf=zf, H=6.3, r=0.27, walls=walls, head=zf + 2.7, band='white', ver=0, ver_sides=(),
                 skirt=None, bracket='demitsudo', bs=0.9, roofkw=dict(kind='yosemune', cover='hongawara', o=2.6, pitch=0.58, teri=1.5, sori=0.45, ridge_h=0.85, ridge_w=0.75,
                 rafter=0.26, rafter_end='white_paint'), floor_mat='stone', pillar_round=False, plinth=(zf, 1.6), extra_band=[zf + 1.0, zf + 4.1, zf + 5.3],
                 block_sides=(1, 2, 3), walk_floor=False)
    ztop = res['ztop']
    with loc.frame(B):
        # the open central bay: 桟唐戸 swung back against the inner side of the wall
        x0, x1 = us[3], us[4]
        for sx, x in ((-1, x0 + 0.3), (1, x1 - 0.3)):
            prim.box(B, x - 0.05, -D / 2 + 0.1, zf + 0.05, x + 0.05, -D / 2 + 1.35, zf + 2.6, 'wood_dark')
            for zz in np.linspace(zf + 0.4, zf + 2.4, 9):
                prim.box(B, x - sx * 0.06 - 0.02, -D / 2 + 0.15, zz - 0.02, x - sx * 0.06 + 0.02, -D / 2 + 1.3, zz + 0.02, 'wood_natural', tag='detail')
        # ceiling and the dragon: a 9 m double circle on a flat boarded ceiling
        zc = ztop - 0.35
        prim.polygon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)], zc, 'wood_natural', up=False)
        cx, cy = 0.0, 0.6
        for (r0, r1, m) in ((4.5, 4.62, 'black_lacquer'), (4.2, 4.28, 'black_lacquer')):
            a = np.linspace(0, 2 * math.pi, 49)
            V = np.array([(cx + r * math.cos(t), cy + r * math.sin(t), zc - 0.01) for t in a for r in (r0, r1)])
            I = [[2 * i, 2 * i + 3, 2 * i + 1] for i in range(48)] + [[2 * i, 2 * i + 2, 2 * i + 3] for i in range(48)]
            B.add(V, I, m, tag='detail')
        a = np.linspace(0, 2 * math.pi, 49)
        Vd = np.array([(cx, cy, zc - 0.005)] + [(cx + 4.18 * math.cos(t), cy + 4.18 * math.sin(t), zc - 0.005) for t in a[:-1]])
        B.add(Vd, [[0, 1 + (i + 1) % 48, 1 + i] for i in range(48)], 'white_paint', tag='detail')
        # the dragon: a coiling body (an S-spiral of tapering black strokes), head with horns and the 八方睨み eyes
        t = np.linspace(0, 1, 70)
        ang = 1.2 + t * 4.6 * math.pi
        rad = 3.6 * (1 - t) ** 0.8 + 0.4
        body = np.array([(cx + rr * math.cos(q) * (1 + 0.08 * math.sin(9 * q)), cy + rr * math.sin(q), zc - 0.02) for rr, q in zip(rad, ang)])
        for i in range(len(body) - 1):
            w = 0.55 * (1 - 0.8 * t[i]) + 0.08
            dd = nrm(body[i + 1][:2] - body[i][:2]); nn = np.array([-dd[1], dd[0]])
            P4 = np.array([np.r_[body[i][:2] + nn * w / 2, zc - 0.02], np.r_[body[i][:2] - nn * w / 2, zc - 0.02],
                           np.r_[body[i + 1][:2] - nn * w / 2, zc - 0.02], np.r_[body[i + 1][:2] + nn * w / 2, zc - 0.02]])
            quad(B, *P4, 'black_lacquer', tag='detail', out=(0, 0, -1))
            if i % 3 == 0:          # scales / claws as small strokes off the body
                q = body[i][:2] + nn * (w / 2 + 0.25)
                quad(B, np.r_[body[i][:2] + nn * w / 2, zc - 0.022], np.r_[q, zc - 0.022], np.r_[q + dd * 0.12, zc - 0.022], np.r_[body[i][:2] + nn * w / 2 + dd * 0.2, zc - 0.022], 'black_lacquer', tag='detail', out=(0, 0, -1))
        hx, hy = body[0][:2]
        for (dx, dy, r) in ((0.0, 0.0, 0.75), (0.5, 0.3, 0.3), (-0.4, 0.45, 0.25)):
            Vh = np.array([(hx + dx, hy + dy, zc - 0.025)] + [(hx + dx + r * math.cos(q), hy + dy + r * math.sin(q), zc - 0.025) for q in np.linspace(0, 2 * math.pi, 13)[:-1]])
            B.add(Vh, [[0, 1 + (i + 1) % 12, 1 + i] for i in range(12)], 'black_lacquer', tag='detail')
        for (dx, dy) in ((-0.25, 0.15), (0.2, 0.2)):
            Ve = np.array([(hx + dx, hy + dy, zc - 0.03)] + [(hx + dx + 0.12 * math.cos(q), hy + dy + 0.12 * math.sin(q), zc - 0.03) for q in np.linspace(0, 2 * math.pi, 9)[:-1]])
            B.add(Ve, [[0, 1 + (i + 1) % 8, 1 + i] for i in range(8)], 'gold', tag='detail')
        # 須弥壇 with the 釈迦三尊 (gilded silhouettes) at the back
        prim.box(B, -4.5, D / 2 - 3.4, zf, 4.5, D / 2 - 1.0, zf + 1.0, 'black_lacquer')
        for (x, s) in ((0.0, 1.0), (-2.6, 0.7), (2.6, 0.7)):
            prim.lathe(B, (x, D / 2 - 2.2, zf + 1.0), [(0.9 * s, 0.0), (0.85 * s, 0.35 * s), (0.55 * s, 0.6 * s), (0.5 * s, 1.15 * s), (0.32 * s, 1.35 * s), (0.36 * s, 1.6 * s), (0.2 * s, 1.85 * s), (0.0, 1.95 * s)], 12, 'gold')
        prim.box(B, -4.6, D / 2 - 3.5, zf, 4.6, D / 2 - 0.9, zf + 0.02, 'stone', tag='block')
        # 選佛場 plaque over the central bay
        prim.box(B, -1.6, -D / 2 - 0.35, zf + 4.4, 1.6, -D / 2 - 0.25, zf + 5.3, 'black_lacquer')
        prim.box(B, -1.45, -D / 2 - 0.37, zf + 4.5, 1.45, -D / 2 - 0.35, zf + 5.2, 'wood_natural', tag='detail')
        # inside floor (walk) and the front wall blocked except the open bay
        prim.polygon(B, [(-L / 2 + 0.3, -D / 2 + 0.3), (L / 2 - 0.3, -D / 2 + 0.3), (L / 2 - 0.3, D / 2 - 0.3), (-L / 2 + 0.3, D / 2 - 0.3)], zf, 'stone', tag='walk')
        ribbon(B, [(-L / 2, -D / 2), (x0 - 0.1, -D / 2)], 0.5, 'block')
        ribbon(B, [(x1 + 0.1, -D / 2), (L / 2, -D / 2)], 0.5, 'block')
    res['loc'] = loc
    return res

# ------------------------------------------------------------------ 唐門 (in front of the 大方丈)
def karamon(B, S):
    """向唐門 east of the 大方丈 (karahafu roof, hiwada), closed"""
    yaw = facing(0.0)
    loc = Loc(-7732.9, 3312.8, yaw)
    zg = 42.48
    span, depth, H, r, W, Dr, hump = 2.6, 2.4, 3.1, 0.16, 4.4, 4.6, 1.15
    mat = WD
    with loc.frame(B):
        prim.box(B, -span / 2 - 1.0, -depth / 2 - 1.2, zg - 0.4, span / 2 + 1.0, depth / 2 + 1.2, zg + 0.14, 'stone')
        z0 = zg + 0.14
        for sx in (-1, 1):
            for sv in (-1, 1):
                x, v = sx * span / 2, sv * depth / 2
                prim.box(B, x - r * 1.5, v - r * 1.5, z0 - 0.02, x + r * 1.5, v + r * 1.5, z0 + 0.12, 'stone')
                prim.box(B, x - r, v - r, z0 + 0.1, x + r, v + r, z0 + H, mat)
                arch.kumimono(B, x, v, z0 + H, (0, sv), (1, 0), 'demitsudo', 0.6, mat, 'white_paint')
            prim.box(B, sx * (span / 2) - r * 0.8, -r * 0.8, z0, sx * (span / 2) + r * 0.8, r * 0.8, z0 + H - 0.5, mat)
            prim.obox(B, (sx * span / 2, -depth / 2, z0 + H - 0.75), (sx * span / 2, depth / 2, z0 + H - 0.75), 0.14, 0.28, mat)
        for sv in (-1, 1):
            prim.obox(B, (-span / 2 - 0.35, sv * depth / 2, z0 + H - 0.28), (span / 2 + 0.35, sv * depth / 2, z0 + H - 0.28), 0.2, 0.44, mat)
        dw = span / 2 - r * 0.8
        for sx in (-1, 1):
            x0, x1 = sorted((0.0, sx * dw))
            prim.box(B, x0 + 0.01, -0.06, z0 + 0.05, x1 - 0.01, 0.06, z0 + H - 0.55, mat)
            for xx in np.linspace(x0 + 0.16, x1 - 0.16, 6):
                prim.box(B, xx - 0.018, -0.1, z0 + H - 1.6, xx + 0.018, -0.07, z0 + H - 0.75, 'wood_natural', tag='detail')
        zc = z0 + H + 0.6
        def zf_(u):
            t = min(abs(u) / (W / 2), 1.0)
            return zc + hump * (0.5 + 0.5 * math.cos(math.pi * t)) + 0.16 * max(0.0, (t - 0.8) / 0.2) ** 2
        us_ = np.linspace(-W / 2, W / 2, 29); vs_ = np.linspace(-Dr / 2, Dr / 2, 7)
        P = np.array([(u, v, zf_(u)) for v in vs_ for u in us_]); nu_ = len(us_) - 1
        I = []
        for j in range(len(vs_) - 1):
            for i in range(nu_):
                a_ = j * (nu_ + 1) + i
                I += [[a_, a_ + nu_ + 2, a_ + 1], [a_, a_ + nu_ + 1, a_ + nu_ + 2]]
        I = np.array(I)
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(P, I, 'hiwada', UV=P[:, [0, 1]], smooth=True)
        S2 = P.copy(); S2[:, 2] -= 0.36
        B.add(S2, I[:, ::-1], 'eave_wood', UV=P[:, [0, 1]], smooth=True)
        for sv in (-1, 1):
            v = sv * Dr / 2
            top = np.array([(u, v, zf_(u)) for u in us_]); bot = top - [0, 0, 0.36]
            Pq = np.concatenate([top, bot]); Iq = []
            for i in range(nu_): Iq += [[i, i + nu_ + 1, i + 1], [i + 1, i + nu_ + 1, i + nu_ + 2]]
            Iq = np.array(Iq)
            fn = np.cross(Pq[Iq[:, 1]] - Pq[Iq[:, 0]], Pq[Iq[:, 2]] - Pq[Iq[:, 0]])
            if (fn[:, 1].sum() * sv) < 0: Iq = Iq[:, ::-1]
            B.add(Pq, Iq, 'hiwada')
            pts = np.array([(u, v - sv * 0.1, zf_(u) - 0.4) for u in us_])
            prim.sweep(B, pts, [(-0.07, -0.4), (0.07, -0.4), (0.07, 0.0), (-0.07, 0.0)], mat, up=(0, 1, 0))
            gp = [(-0.5, 0.0), (0.5, 0.0), (0.32, -0.4), (0.0, -0.6), (-0.32, -0.4)]
            Pg = np.array([(x, v - sv * 0.1, zc + hump - 0.42 + z) for (x, z) in gp])
            Ig = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
            B.add(Pg, Ig, mat, tag='detail'); B.add(Pg, [t[::-1] for t in Ig], mat, tag='detail')
        for su in (-1, 1):
            u = su * W / 2
            pts = np.array([(u, v, zf_(u) - 0.08) for v in vs_])
            prim.sweep(B, pts, [(-0.05, -0.3), (0.05, -0.3), (0.05, 0.0), (-0.05, 0.0)], mat, up=(1, 0, 0))
        zt = zf_(0.0)
        prim.box(B, -0.2, -Dr / 2 + 0.25, zt - 0.1, 0.2, Dr / 2 - 0.25, zt + 0.36, 'ridge')
        ribbon(B, [(-span / 2, -depth / 2 - 0.5), (-span / 2, depth / 2 + 0.5)], 0.6, 'block')
        ribbon(B, [(span / 2, -depth / 2 - 0.5), (span / 2, depth / 2 + 0.5)], 0.6, 'block')
        ribbon(B, [(-span / 2, 0), (span / 2, 0)], 0.6, 'block')
        ze = loc.g(S, 0, -depth / 2 - 3.6)
        K.stairs_build(B, (0, -depth / 2 - 1.2 - 2.2), (0, -depth / 2 - 1.2), ze, zg + 0.14, 3.2, 'stone', riser=0.15)
    # white walls from the gate to the 大方丈 corners (the front court of the hojo is closed)
    for sgn in (-1, 1):
        K.wall(B, S, [loc.w(sgn * 1.6, 0.0), loc.w(sgn * (15.0 if sgn > 0 else 28.0), 0.0)], h=2.1, th=0.45)
    return loc

# ------------------------------------------------------------------ 大方丈
def daihojo(B, S):
    """大方丈 (1899): 入母屋 本瓦, eleven bays along the garden, a wide 広縁 inside the outer pillars east and west, a
    lower 落縁 all round; the west 広縁 looks over 曹源池"""
    yaw = facing(1.8)
    loc = Loc(-7763.4, 3313.4, yaw)
    zf = HOJO_ZF
    L, D = 31.0, 22.2
    hiro = 2.5
    nu, nv = 12, 8
    us, vs = arch.grid(L, D, nu, nv)
    walls = {0: ['open'] * nu, 2: ['open'] * nu,
             1: ['white', 'maira', 'maira', 'white', 'white', 'maira', 'maira', 'white'],
             3: ['white', 'maira', 'maira', 'white', 'white', 'maira', 'maira', 'white']}
    res = K.hall(B, S, loc, L=L, D=D, nu=nu, nv=nv, zf=zf, H=3.75, r=0.17, walls=walls, head=zf + 2.0, band='white', ver=1.0, ver_drop=0.28,
                 ver_sides=(0, 1, 2, 3), skirt='white', bracket='funa', bs=0.8, roofkw=dict(kind='irimoya', cover='hongawara', o=2.7, pitch=0.6, teri=1.45, ridge_h=0.95, ridge_w=0.8, gable_wall='wood_dark',
                 sori=0.5, gable_frac=0.6, rafter=0.24, rafter_end='white_paint'), block_sides=(), floor_mat='wood_natural')
    zv = res['zv']
    with loc.frame(B):
        # inner walls (the rooms behind the 広縁): 舞良戸 / 障子 / open fusuma onto dark tatami rooms
        for sgn in (-1, 1):
            v = sgn * (D / 2 - hiro)
            kinds = ['maira', 'shoji', 'shoji', 'dark', 'shoji', 'shoji', 'dark', 'shoji', 'shoji', 'dark', 'shoji', 'maira']
            pts = [(x, v) for x in us]
            if sgn > 0: pts = pts[::-1]; kinds = kinds[::-1]
            for i in range(nu):
                a, b = pts[i], pts[i + 1]
                prim.box(B, a[0] - 0.12, a[1] - 0.12, zf, a[0] + 0.12, a[1] + 0.12, zf + 3.5, WD)
                K.infill(B, a, b, zf + 0.02, zf + 1.95, kinds[i], mat=WD, r=0.12)
                K.infill(B, a, b, zf + 2.15, zf + 3.4, 'white', r=0.12)
            prim.obox(B, (-L / 2, v, zf + 2.05), (L / 2, v, zf + 2.05), 0.12, 0.2, WD)
            # the rooms: dark interior behind, tatami floor
            ra, rb = (v, v + 3.0) if sgn < 0 else (v - 3.0, v)
            prim.box(B, -L / 2 + 0.3, ra, zf - 0.01, L / 2 - 0.3, rb, zf + 0.005, 'tatami', faces='Z', tag='detail')
        prim.box(B, -L / 2 + 0.4, -D / 2 + hiro + 2.9, zf, L / 2 - 0.4, D / 2 - hiro - 2.9, zf + 3.4, WD, faces='yY')
        # ceiling of the 広縁 (boards) and the 方丈 plaque on the front
        for sgn in (-1, 1):
            v0 = sgn * (D / 2 - hiro); v1 = sgn * D / 2
            prim.polygon(B, [(-L / 2, min(v0, v1)), (L / 2, min(v0, v1)), (L / 2, max(v0, v1)), (-L / 2, max(v0, v1))], zf + 3.45, 'wood_natural', up=False)
        prim.box(B, -1.3, -D / 2 - 0.3, zf + 2.6, 1.3, -D / 2 - 0.2, zf + 3.3, 'black_lacquer')
        prim.box(B, -1.15, -D / 2 - 0.32, zf + 2.7, 1.15, -D / 2 - 0.3, zf + 3.2, 'gold', tag='detail')
        # rooms are not walkable: block the inner block (offset inward so the 広縁 stays free)
        rect = Polygon([(-L / 2 + 0.6, -D / 2 + hiro + 0.5), (L / 2 - 0.6, -D / 2 + hiro + 0.5), (L / 2 - 0.6, D / 2 - hiro - 0.5), (-L / 2 + 0.6, D / 2 - hiro - 0.5)])
        prim.polygon(B, np.array(rect.exterior.coords)[:-1], zf, 'stone', tag='block')
        # front steps (east, centre) from the court up to the 落縁 and the 広縁
        zgf = loc.g(S, 0, -D / 2 - 3.5)
        zo = zv
        K.stairs_build(B, (0, -D / 2 - 1.0 - 2.2), (0, -D / 2 - 1.0), zgf, zo, 3.0, 'wood_natural', cheek=WD, riser=0.18)
        rect_walk(B, -1.5, -D / 2 - 4.0, 1.5, -D / 2 - 3.2, zgf + 0.03)
        # the outer edge of the 落縁: open (visitors sit there); a thin hand rail on the garden side as in the photos
        for k, v in ((2, D / 2 + 1.0 - 0.06),):
            for (u0, u1) in ((-L / 2 - 1.0, -2.0), (2.0, L / 2 + 1.0)):
                prim.obox(B, (u0, v, zv + 0.42), (u1, v, zv + 0.42), 0.05, 0.05, WD, tag='detail')
                for u in np.arange(u0 + 0.1, u1, 2.6):
                    prim.box(B, u - 0.03, v - 0.03, zv, u + 0.03, v + 0.03, zv + 0.42, WD, tag='detail')
            ribbon(B, [(-L / 2 - 1.0, v + 0.25), (L / 2 + 1.0, v + 0.25)], 0.2, 'block')
    res['loc'] = loc
    return res

def hojo_court(B, S):
    """the white-sand court in front of the 大方丈 (raised a little above the DEM: the veranda stands ~0.8 m above it as
    in the photos), with a stone edge where it stands above the generic ground"""
    zc = 42.62
    court = box(-7751.4, 3297.5, -7734.6, 3330.0).difference(box(-7735.8, 3309.5, -7730.0, 3316.1))
    hf = lambda x, y: max(float(S.ground(x, y)) + 0.04, zc)
    K.mesh_region(B, court, hf, 1.0, surf_of=lambda x, y: K.SID['sand'], walk_of=lambda x, y: True)
    ring = np.array(court.exterior.coords)
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        L = np.linalg.norm(b - a); k = max(1, int(L / 1.0))
        for j in range(k):
            p = a + (b - a) * j / k; q = a + (b - a) * (j + 1) / k
            za, zb = float(S.ground(*p)), float(S.ground(*q))
            ha, hb = hf(*p), hf(*q)
            if max(ha - za, hb - zb) < 0.06: continue
            quad(B, (p[0], p[1], za - 0.2), (q[0], q[1], zb - 0.2), (q[0], q[1], hb), (p[0], p[1], ha), 'stone', both=True, c1=(0, 3, 0, 0))
    for (x0, x1) in ((-7751.0, -7735.0),):
        for y in (3297.6, 3329.9):
            prim.obox(B, (x0, y, zc + 0.03), (x1, y, zc + 0.03), 0.25, 0.08, 'curb', tag='detail')

def kuri_annex(B, S):
    """the kitchen wing behind the 庫裏 (north): a lower 切妻 block, white walls in a timber grid"""
    loc = Loc(-7759.2, 3361.6, math.radians(1.6))
    zg = float(S.ground(-7759.2, 3361.6))
    K.hall(B, S, loc, L=12.6, D=9.6, nu=5, nv=4, zf=zg + 0.3, H=3.6, r=0.14, walls={0: ['white', 'renji', 'white', 'renji', 'white'], 1: ['white', 'renji', 'renji', 'white'],
           2: ['white'] * 5, 3: ['white'] * 4}, head=zg + 2.2, ver=0, ver_sides=(), skirt=None, bracket=None,
           roofkw=dict(kind='kirizuma', cover='sangawara', o=1.0, pitch=0.62, verge=0.8, rafter=0.26, rafter_end='white_paint', ridge_h=0.55, ridge_w=0.5), walk_floor=False)

# ------------------------------------------------------------------ 小方丈 (書院)
def kohojo(B, S):
    yaw = math.radians(-2.0)
    loc = Loc(-7779.6, 3347.3, yaw)
    zf = 44.65
    L, D = 22.0, 12.6
    walls = {0: ['shoji'] * 8, 1: ['white', 'maira', 'maira', 'white', 'white'], 2: ['white', 'maira', 'white', 'white', 'maira', 'white', 'white', 'white'],
             3: ['white', 'shoji', 'shoji', 'shoji', 'white']}
    res = K.hall(B, S, loc, L=L, D=D, nu=8, nv=5, zf=zf, H=3.5, r=0.16, walls=walls, head=zf + 1.9, ver=1.0, ver_sides=(0, 3), ver_drop=0.05,
                 bracket='funa', bs=0.7, roofkw=dict(kind='irimoya', cover='hongawara', o=2.2, pitch=0.62, teri=1.4, sori=0.4, rafter=0.24, rafter_end='white_paint', ridge_h=0.75, ridge_w=0.7, gable_wall='wood_dark', gable_frac=0.58),
                 block_sides=(0, 1, 2, 3))
    return res

# ------------------------------------------------------------------ 庫裏
def kuri(B, S):
    """庫裏 (1899): the 切妻 gable facing east over the end of the approach: white plaster in a dark timber grid,
    lattice bands, the entrance in the middle (the 達磨図 screen inside), 虹梁 + 大瓶束 and a large 懸魚 in the gable;
    a smoke turret (越屋根) on the ridge.  Plan ~14 x 14 m, ridge ~12.5 m"""
    yaw = math.radians(1.6)
    loc = Loc(-7758.6, 3348.2, yaw)                    # u = east (towards the front gable), v = north
    zg = 43.45
    L, D = 13.6, 14.0
    z_eave = zg + 5.6
    o, vo, pitch = 1.35, 1.25, 0.8
    R = Roof2(L, D, z_eave, o, kind='kirizuma', cover='hongawara', pitch=pitch, teri=1.6, sori=0.0, verge=vo, rafter=0.26, rafter_mat=WD,
              rafter_end='white_paint', ends='oni', no_gable_wall=True, ridge_h=0.85, ridge_w=0.65, edge=0.3)
    with loc.frame(B):
        zz = R.build(B)
        zr = zz['z_ridge']
        under = lambda v: float(R.z(R.c - abs(v), R.a)) - R.edge - 0.35          # underside of the roof at the gable line
        # stone base (土台石) all round
        prim.prism(B, [(-L / 2 - 0.25, -D / 2 - 0.25), (L / 2 + 0.25, -D / 2 - 0.25), (L / 2 + 0.25, D / 2 + 0.25), (-L / 2 - 0.25, D / 2 + 0.25)], zg - 0.4, zg + 0.18, 'stone')
        # ---- front (east) gable at u = +L/2, facing +u: s runs along v from -D/2 (south) to +D/2 (north)
        posts = [-7.0, -4.6, -1.9, 1.9, 4.6, 7.0]
        top = lambda s: min(z_eave - 0.15, under(s)) if abs(s) > 6.9 else under(s)
        zb = lambda h: zg + h
        beams = [(zb(0.3), -7.0, 7.0), (zb(1.05), -7.0, -1.9), (zb(1.05), 1.9, 7.0), (zb(1.65), -7.0, -1.9), (zb(1.65), 1.9, 7.0), (zb(2.75), -7.0, 7.0),
                 (zb(3.7), -7.0, 7.0), (zb(4.6), -7.0, 7.0), (zb(6.38), -5.6, 5.6), (zb(8.7), -2.9, 2.9)]
        windows = [(-6.75, -4.85, zb(1.7), zb(2.65)), (-4.35, -2.15, zb(1.7), zb(2.65)), (2.15, 4.35, zb(1.7), zb(2.65)), (4.85, 6.75, zb(1.7), zb(2.65)),
                   (-2.6, -0.15, zb(5.5), zb(6.3)), (0.15, 2.6, zb(5.5), zb(6.3))]
        doors = [(-1.7, 1.7, zb(0.12), zb(2.6))]
        p0 = np.array([L / 2, 0.0]); dvec = np.array([0.0, 1.0]); nvec = np.array([1.0, 0.0])
        timber_facade(B, p0, dvec, nvec, zg + 0.1, top, posts, beams, windows, doors, door_depth=4.7)
        # the heavy eave beam (桁) across the gable at the eave level, its ends carried on brackets past the corners
        prim.obox(B, (L / 2 + 0.12, -D / 2 - 1.2, zb(5.25)), (L / 2 + 0.12, D / 2 + 1.2, zb(5.25)), 0.42, 0.3, WD)
        for s in (-7.0, -4.6, -1.9, 1.9, 4.6, 7.0):
            arch.kumimono(B, L / 2 + 0.1, s, zb(4.95), (1, 0), (0, 1), 'funa', 0.9, WD)
        # 虹梁 (curved tie beam) with its 眉 and 大瓶束 struts, a beam above, the central 束 to the ridge
        nb = 13
        for i in range(nb - 1):
            t0, t1 = i / (nb - 1), (i + 1) / (nb - 1)
            s0, s1 = -5.4 + 10.8 * t0, -5.4 + 10.8 * t1
            z0_, z1_ = zb(6.45) + 0.3 * math.sin(math.pi * t0), zb(6.45) + 0.3 * math.sin(math.pi * t1)
            prim.obox(B, (L / 2 + 0.16, s0, z0_), (L / 2 + 0.16, s1, z1_), 0.5, 0.24, WD)
        for s in (-2.6, 2.6):
            prim.lathe(B, (L / 2 + 0.2, s, zb(6.95)), [(0.28, 0.0), (0.32, 0.25), (0.24, 0.65), (0.16, 0.95), (0.16, 1.55), (0.22, 1.7)], 8, WD)
            for sg in (-1, 1):                  # 笈形 (scroll brackets) beside the struts
                quad(B, (L / 2 + 0.22, s + sg * 0.15, zb(7.0)), (L / 2 + 0.22, s + sg * 0.85, zb(7.05)), (L / 2 + 0.22, s + sg * 0.6, zb(7.6)), (L / 2 + 0.22, s + sg * 0.15, zb(8.2)), WD, out=(1, 0, 0))
        prim.obox(B, (L / 2 + 0.18, -3.4, zb(8.75)), (L / 2 + 0.18, 3.4, zb(8.75)), 0.36, 0.22, WD)
        prim.obox(B, (L / 2 + 0.18, 0, zb(8.9)), (L / 2 + 0.18, 0, zr - 1.5), 0.3, 0.2, WD)
        for s in (-1.3, 1.3):
            prim.lathe(B, (L / 2 + 0.2, s, zb(9.05)), [(0.2, 0.0), (0.24, 0.2), (0.18, 0.5), (0.12, 0.7), (0.14, 0.95)], 8, WD, tag='detail')
        # ---- back (west) gable: plaster with a plainer grid
        top_b = lambda s: under(s)
        timber_facade(B, np.array([-L / 2, 0.0]), np.array([0.0, -1.0]), np.array([-1.0, 0.0]), zg + 0.1, lambda s: top_b(-s),
                      [-7.0, -3.5, 0.0, 3.5, 7.0], [(zb(0.3), -7, 7), (zb(2.6), -7, 7), (zb(4.6), -7, 7), (zb(6.5), -5, 5)], windows=[(-2.9, -0.5, zb(1.4), zb(2.2))])
        # ---- side walls (south v = -D/2 facing -v, north facing +v) up to the eave
        for sgn in (-1, 1):
            p0s = np.array([-L / 2 if sgn < 0 else L / 2, sgn * D / 2]); ds = np.array([1.0 if sgn < 0 else -1.0, 0.0]); ns = np.array([0.0, float(sgn)])
            timber_facade(B, p0s, ds, ns, zg + 0.1, lambda s: z_eave - 0.25, [0.0, 2.27, 4.53, 6.8, 9.07, 11.33, 13.6],
                          [(zb(0.3), 0, 13.6), (zb(1.8), 0, 13.6), (zb(2.75), 0, 13.6), (zb(3.9), 0, 13.6), (zb(5.0), 0, 13.6)],
                          windows=[(2.5, 4.3, zb(1.85), zb(2.7)), (9.3, 11.1, zb(1.85), zb(2.7))])
        # 越屋根 (smoke turret) on the ridge: a box with lattice sides and a little gable roof
        tu, tL, tD = -1.0, 4.2, 2.6
        zt0 = zr + 0.2
        prim.box(B, tu - tL / 2, -tD / 2, zt0 - 1.2, tu + tL / 2, tD / 2, zt0 + 1.35, 'temple_wall', c0=WHITE)
        for sv in (-1, 1):
            for x in np.arange(tu - tL / 2 + 0.2, tu + tL / 2, 0.18):
                prim.box(B, x - 0.03, sv * tD / 2 - 0.05, zt0 + 0.25, x + 0.03, sv * tD / 2 + 0.05, zt0 + 1.15, WD, tag='detail')
        with Frame(B, tu, 0, 0, 0):
            jroof.roof(B, tL, tD, zt0 + 1.45, 0.85, kind='kirizuma', cover='hongawara', pitch=0.72, verge=0.6, rafter=0.22, rafter_mat=WD, rafter_end='white_paint',
                       gable_wall='temple_wall', ends='oni', sori=0.0, edge=0.2, ridge_h=0.45, ridge_w=0.4)
        # the entrance: 土間 inside (dark), the 達磨図 衝立 (平田精耕 筆) 3 m behind the door
        prim.box(B, L / 2 - 5.0, -2.2, zg + 0.1, L / 2 - 0.15, 2.2, zg + 0.12, 'stone', faces='Z')
        rect_walk(B, L / 2 - 4.6, -1.6, L / 2 + 2.5, 1.6, zg + 0.12)
        sx_ = L / 2 - 3.2
        prim.box(B, sx_ - 0.12, -1.25, zg + 0.1, sx_ + 0.12, 1.25, zg + 0.35, WD)          # foot
        prim.box(B, sx_ - 0.06, -1.15, zg + 0.35, sx_ + 0.06, 1.15, zg + 2.35, WD)          # frame
        prim.box(B, sx_ + 0.06, -1.05, zg + 0.45, sx_ + 0.065, 1.05, zg + 2.25, 'white_paint')
        def stroke(pts, w, z_off=0.07):
            pts = np.asarray(pts, float)
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                dd = nrm(b - a); nn = np.array([-dd[1], dd[0]]) * w / 2
                quad(B, (sx_ + z_off, a[0] + nn[0], a[1] + nn[1]), (sx_ + z_off, b[0] + nn[0], b[1] + nn[1]), (sx_ + z_off, b[0] - nn[0], b[1] - nn[1]), (sx_ + z_off, a[0] - nn[0], a[1] - nn[1]),
                     'black_lacquer', tag='detail', out=(1, 0, 0))
        # Daruma: a bold hooded outline, heavy brows, round staring eyes, the beard
        zc_ = zg + 1.35
        hood = [(0.85 * math.sin(t), zc_ + 0.15 + 0.78 * math.cos(t)) for t in np.linspace(-2.4, 2.4, 22)]
        stroke(hood, 0.12)
        stroke([(-0.45, zc_ + 0.45), (-0.12, zc_ + 0.38)], 0.09); stroke([(0.12, zc_ + 0.38), (0.45, zc_ + 0.45)], 0.09)
        for ex in (-0.28, 0.28):
            stroke([(ex + 0.12 * math.cos(t), zc_ + 0.22 + 0.1 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 10)], 0.04)
        stroke([(-0.42, zc_ - 0.1), (-0.25, zc_ - 0.35), (0.0, zc_ - 0.42), (0.25, zc_ - 0.35), (0.42, zc_ - 0.1)], 0.07)
        stroke([(-0.08, zc_ + 0.12), (0.0, zc_ - 0.05), (0.08, zc_ + 0.12)], 0.05)
        B.lamp(L / 2 - 1.2, 0.0, zg + 2.4, 6.0, (1.0, 0.7, 0.45))
        # the building is solid apart from the entrance hall
        ribbon(B, [(-L / 2 + 0.3, -D / 2 + 0.3), (-L / 2 + 0.3, D / 2 - 0.3)], 0.5, 'block')
        ribbon(B, [(-L / 2, -D / 2), (L / 2, -D / 2)], 0.5, 'block'); ribbon(B, [(-L / 2, D / 2), (L / 2, D / 2)], 0.5, 'block')
        ribbon(B, [(L / 2, -D / 2), (L / 2, -1.8)], 0.5, 'block'); ribbon(B, [(L / 2, 1.8), (L / 2, D / 2)], 0.5, 'block')
        ribbon(B, [(L / 2 - 4.8, -2.2), (L / 2 - 4.8, 2.2)], 0.5, 'block')
        prim.polygon(B, [(-L / 2 + 0.6, -D / 2 + 0.6), (L / 2 - 5.4, -D / 2 + 0.6), (L / 2 - 5.4, D / 2 - 0.6), (-L / 2 + 0.6, D / 2 - 0.6)], zg, 'stone', tag='block')
    # the stone garden in front of the 大方丈's entrance (the tall 立石 group by the kuri, photo kuri_d)
    gx, gy = -7745.0, 3335.6
    zgg = float(S.ground(gx, gy))
    K.rock(B, (gx, gy, zgg), 0.55, 11, tall=4.4, angular=0.6, sink=0.15)
    for k, (dx, dy, s) in enumerate(((-1.6, -0.6, 0.55), (1.3, 0.4, 0.6), (2.4, -0.5, 0.45), (-2.6, 0.8, 0.4), (0.4, -1.3, 0.35))):
        K.rock(B, (gx + dx, gy + dy, zgg), s, 30 + k, flat=0.9, angular=0.5)
    K.ribbon(B, [(gx - 4.0, gy), (gx + 4.0, gy)], 3.6, 'block')
    return dict(loc=loc, z_ridge=zr)

# ------------------------------------------------------------------ 多宝殿 + the climbing corridor
def tahoden(B, S):
    """多宝殿 (1934, 鎌倉 style 紫宸殿 form): 入母屋 檜皮葺 with a one-bay 向拝 and stairs on the south front"""
    yaw = math.radians(10.0)
    loc = Loc(-7842.6, 3390.4, yaw)
    zg = 48.25
    zf = zg + 1.15
    L, D = 12.4, 9.6
    walls = {0: ['white', 'renji', 'karado', 'renji', 'white'], 1: ['white', 'white', 'board', 'white'], 2: ['white'] * 5, 3: ['white', 'board', 'white', 'white']}
    res = K.hall(B, S, loc, L=L, D=D, nu=5, nv=4, zf=zf, H=3.6, r=0.18, pillar_round=True, walls=walls, head=zf + 2.2, ver=1.2, ver_sides=(0, 1, 3),
                 rail=True, rail_h=0.7, rail_gaps=[(0, -1.5, 1.5)], bracket='hira', bs=0.75,
                 roofkw=dict(kind='irimoya', cover='hiwada', o=2.3, pitch=0.62, teri=1.6, sori=0.55, rafter=0.22, rafter_end='white_paint', gable_frac=0.55),
                 block_sides=(1, 2, 3))
    R = res['roof']
    with loc.frame(B):
        # 向拝: two pillars, a beam with 木鼻, a lean-to roof running out of the main front eave
        vk = -D / 2 - 1.2 - 2.0
        v_wall = -R.c + 0.9
        zt = float(R.z(0.9, R.a)) - 0.06
        vE = vk - 0.75
        drop = 0.42 * (v_wall - vE)
        zEp = zt - drop
        ztop_p = zEp - 0.75
        for x in (-1.6, 1.6):
            prim.box(B, x - 0.24, vk - 0.24, zg - 0.1, x + 0.24, vk + 0.24, zg + 0.12, 'stone')
            prim.box(B, x - 0.13, vk - 0.13, zg + 0.1, x + 0.13, vk + 0.13, ztop_p, WD)
            arch.kumimono(B, x, vk, ztop_p, (0, -1), (1, 0), 'demitsudo', 0.55, WD, 'white_paint')
            prim.obox(B, (x, vk + 0.1, ztop_p - 0.2), (x, -D / 2 - 0.2, zf + 2.6), 0.12, 0.24, WD, tag='detail')
        prim.obox(B, (-2.3, vk, ztop_p - 0.22), (2.3, vk, ztop_p - 0.22), 0.2, 0.4, WD)
        K.pent(B, -2.2, 2.2, v_wall, zt, v_wall - vE, drop, cover='hiwada', mat=WD)
        # stairs from the gravel to the veranda under the 向拝
        K.stairs_build(B, (0, vk + 0.2), (0, -D / 2 - 1.2), zg, zf - 0.05, 2.6, 'wood_natural', cheek=WD, riser=0.18)
        rect_walk(B, -1.6, vk - 0.8, 1.6, vk + 0.3, zg + 0.03)
        # 祠堂 (奥殿) behind: a smaller hiwada hall joined by a short 相の間
        with Frame(B, 0, D / 2 + 4.4, 0, 0):
            prim.box(B, -3.2, -2.4, zg - 0.2, 3.2, 2.4, zf, 'stone')
            for x in (-3.0, 3.0):
                for y in (-2.2, 2.2):
                    prim.cyl(B, (x, y, zf), (x, y, zf + 3.0), 0.16, 0.16, 10, WD)
            for (a, b) in (((-3, -2.2), (3, -2.2)), ((3, -2.2), (3, 2.2)), ((3, 2.2), (-3, 2.2)), ((-3, 2.2), (-3, -2.2))):
                K.infill(B, a, b, zf + 0.05, zf + 2.8, 'white', r=0.12)
            arch.nageshi(B, 6.0, 4.4, zf + 3.0, WD, h=0.26, w=0.18, out=0.0)
            jroof.roof(B, 6.4, 4.8, zf + 3.35, 1.6, kind='irimoya', cover='hiwada', pitch=0.64, teri=1.6, sori=0.45, rafter=0.22, rafter_mat=WD, rafter_end='white_paint')
        prim.box(B, -1.5, D / 2, zf, 1.5, D / 2 + 2.0, zf + 2.6, 'temple_wall', c0=WHITE)
        prim.box(B, -1.8, D / 2 - 0.2, zf + 2.6, 1.8, D / 2 + 2.2, zf + 3.0, 'hiwada')
        ribbon(B, [(-3.4, D / 2 + 4.4), (3.4, D / 2 + 4.4)], 5.0, 'block')
    return res

def corridor(B, S, pts, zs, *, w=2.6, bay=2.0, h=2.45, cover='hongawara', tag='main'):
    """a roofed corridor along a world polyline with floor heights zs at the points (steps where it climbs): posts,
    floor boards, a low railing, kirizuma roof segments following the slope"""
    P = np.asarray(pts, float); zs = np.asarray(zs, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; Lt = s[-1]
    pos = lambda t: np.array([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])])
    zfl = lambda t: float(np.interp(t, s, zs))
    def tan(t):
        return nrm(pos(min(t + 0.5, Lt)) - pos(max(t - 0.5, 0)))
    # floor: treads (rise 0.17) where it climbs
    tt = np.arange(0, Lt + 1e-6, 0.1)
    zq = []; zc = zfl(0.0)
    for t in tt:
        z = zfl(t)
        while z - zc >= 0.17: zc += 0.17
        while zc - z >= 0.17: zc -= 0.17
        zq.append(zc)
    zq = np.array(zq)
    edges = [0] + [i for i in range(1, len(tt)) if zq[i] != zq[i - 1]] + [len(tt) - 1]
    for k in range(len(edges) - 1):
        i0, i1 = edges[k], edges[k + 1]
        ta, tb = tt[i0], tt[i1]; z = zq[i0]
        pa, pb = pos(ta), pos(tb); na = np.array([-tan(ta)[1], tan(ta)[0]]); nb = np.array([-tan(tb)[1], tan(tb)[0]])
        V = [np.r_[pa - na * w / 2, z], np.r_[pa + na * w / 2, z], np.r_[pb + nb * w / 2, z], np.r_[pb - nb * w / 2, z]]
        quad(B, *V, 'wood_natural', out=(0, 0, 1))
        if k > 0 and abs(zq[i0] - zq[i0 - 1]) > 0.01:
            lo, hi = min(zq[i0], zq[i0 - 1]), max(zq[i0], zq[i0 - 1])
            quad(B, np.r_[pa - na * w / 2, lo], np.r_[pa + na * w / 2, lo], np.r_[pa + na * w / 2, hi], np.r_[pa - na * w / 2, hi], 'wood_natural',
                 out=np.r_[-tan(ta) * np.sign(zq[i0] - zq[i0 - 1]), 0])
    W = np.c_[[pos(t) for t in tt[::3]], zq[::3]]
    ribbon(B, W, w - 0.5, 'walk')
    # posts every bay, beams, roof
    nb_ = max(1, int(round(Lt / bay)))
    ts = np.linspace(0, Lt, nb_ + 1)
    zsm = np.convolve(np.pad([zfl(t) for t in tt], 8, mode='edge'), np.ones(17) / 17, mode='same')[8:-8]
    zr = lambda t: float(np.interp(t, tt, zsm)) + h
    for t in ts:
        p = pos(t); n = np.array([-tan(t)[1], tan(t)[0]])
        for sg in (-1, 1):
            q = p + n * sg * (w / 2 - 0.08)
            zg = float(S.ground(*q))
            zfloor = float(np.interp(t, tt, zq))
            prim.box(B, q[0] - 0.09, q[1] - 0.09, min(zg, zfloor) - 0.3, q[0] + 0.09, q[1] + 0.09, zr(t), WD)
            if zfloor - zg > 0.3:
                prim.box(B, q[0] - 0.07, q[1] - 0.07, zg - 0.2, q[0] + 0.07, q[1] + 0.07, zfloor - 0.05, 'stone', tag='detail')
    for sg in (-1, 1):
        R_ = np.array([np.r_[pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * (w / 2 - 0.08), zr(t)] for t in tt[::4]])
        prim.sweep(B, R_, [(-0.1, -0.24), (0.1, -0.24), (0.1, 0.0), (-0.1, 0.0)], WD)
        Rl = np.array([np.r_[pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * (w / 2 - 0.08), float(np.interp(t, tt, zq)) + 0.6] for t in tt[::4]])
        prim.sweep(B, Rl, [(-0.05, -0.1), (0.05, -0.1), (0.05, 0.0), (-0.05, 0.0)], WD, tag='detail')
        ribbon(B, [pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * (w / 2) for t in tt[::4]], 0.3, 'block')
    # roof: two slopes, eaves 0.7 m out, pitch 0.55, along the smoothed line
    cm = jroof.COVER_MAT[cover]
    for sg in (-1, 1):
        V = []
        for t in tt[::4]:
            p = pos(t); n = np.array([-tan(t)[1], tan(t)[0]])
            z = zr(t) + 0.15
            V.append([np.r_[p, z + (w / 2 + 0.7) * 0.55], np.r_[p + n * sg * (w / 2 + 0.7), z]])
        V = np.array(V)
        m = len(V)
        Pf = V.reshape(-1, 3); I = []
        for i in range(m - 1):
            a = 2 * i
            I += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
        I = np.array(I)
        fn = np.cross(Pf[I[:, 1]] - Pf[I[:, 0]], Pf[I[:, 2]] - Pf[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(Pf, I, cm, smooth=True, tag=tag)
        Ps = Pf - [0, 0, 0.2]
        B.add(Ps, I[:, ::-1], 'eave_wood', smooth=True, tag=tag)
        E = V[:, 1]
        prim.sweep(B, E - [0, 0, 0.1], [(-0.04, -0.1), (0.04, -0.1), (0.04, 0.12), (-0.04, 0.12)], WD, tag=tag)
    Rg = np.array([np.r_[pos(t), zr(t) + 0.15 + (w / 2 + 0.7) * 0.55] for t in tt[::4]])
    prim.sweep(B, Rg, [(-0.18, -0.05), (0.18, -0.05), (0.18, 0.25), (-0.18, 0.25)], 'ridge', tag=tag)

def corridors(B, S):
    pts = [(-7793.8, 3354.6), (-7805.4, 3366.4), (-7808.3, 3369.4), (-7819.8, 3392.6), (-7831.9, 3390.4)]
    zs = [44.65, 46.3, 46.6, 49.0, 49.35]
    corridor(B, S, pts, zs, w=2.5, bay=2.1, h=2.4)

# ------------------------------------------------------------------ approach paving (paint) and the court
def approach(B, S):
    # 参道: 総門 → 中門 → the 庫裏 forecourt (stone slabs in gravel), the axis 勅使門 → bridge → 法堂 → 唐門
    pa = LineString([(-7463.0, 3346.6), (-7511.0, 3343.4), (-7600.0, 3345.6), (-7690.0, 3346.4), (-7745.0, 3348.0)])
    S.paint.append({'poly': [list(map(list, pa.buffer(1.6, cap_style='flat').exterior.coords))], 'surf': 'stone_slab'})
    ax = LineString([(-7508.0, 3313.6), (-7553.0, 3312.8), (-7686.0, 3312.3)])
    S.paint.append({'poly': [list(map(list, ax.buffer(1.7, cap_style='flat').exterior.coords))], 'surf': 'stone_slab'})
    ax2 = LineString([(-7712.0, 3312.4), (-7748.0, 3312.9)])
    S.paint.append({'poly': [list(map(list, ax2.buffer(1.4, cap_style='flat').exterior.coords))], 'surf': 'stone_slab'})
    # the forecourt of the 庫裏 and the 大方丈 front court: white gravel
    court = Polygon([(-7751.5, 3330.8), (-7731.0, 3330.8), (-7728.0, 3362.0), (-7751.5, 3362.0)])
    S.paint.append({'poly': [list(map(list, court.exterior.coords))], 'surf': 'gravel'})
    hojo_front = Polygon([(-7748.5, 3297.0), (-7737.0, 3297.0), (-7737.0, 3330.0), (-7748.5, 3330.0)])
    S.paint.append({'poly': [list(map(list, hojo_front.exterior.coords))], 'surf': 'sand'})

def lanterns(B, S):
    """stone lanterns along the 参道 and the axis (lit in the evening)"""
    pa = LineString([(-7463.0, 3346.6), (-7511.0, 3343.4), (-7600.0, 3345.6), (-7690.0, 3346.4), (-7745.0, 3348.0)])
    for t in np.arange(16.0, pa.length - 20.0, 21.0):
        if 40.0 < t < 58.0: continue
        p = np.array(pa.interpolate(t).coords[0]); q2 = np.array(pa.interpolate(t + 1.0).coords[0])
        d = nrm(q2 - p); n = np.array([-d[1], d[0]])
        for sg in (-1, 1):
            q = p + n * sg * 2.8
            K.lantern(B, q[0], q[1], float(S.ground(*q)), h=1.9)
    for x in (-7522.0, -7532.0, -7570.0, -7590.0, -7660.0, -7680.0):
        for sg in (-1, 1):
            q = (x, 3313.0 + sg * 2.8)
            K.lantern(B, q[0], q[1], float(S.ground(*q)), h=1.9)

def build(B, S):
    out = {}
    lanterns(B, S)
    out['somon'] = somon(B, S)
    out['chumon'] = chumon(B, S)
    out['chokushimon'] = chokushimon(B, S)
    out['pond'] = hojoike(B, S)
    out['hatto'] = hatto(B, S)
    out['karamon'] = karamon(B, S)
    out['hojo'] = daihojo(B, S)
    hojo_court(B, S)
    out['kohojo'] = kohojo(B, S)
    out['kuri'] = kuri(B, S)
    kuri_annex(B, S)
    out['tahoden'] = tahoden(B, S)
    corridors(B, S)
    out['kitamon'] = kitamon(B, S)
    approach(B, S)
    # areas whose generic props (OSM walls / fences drawn by the city) and PLATEAU walls-as-sheds we replace
    out['zones'] = [box(-7518, 3300, -7505, 3326), box(-7516, 3326, -7505, 3358), box(-7737, 3278, -7727, 3345), box(-7752, 3296, -7731, 3331),
                    Point(-7897, 3478).buffer(9.0), Point(-7468.2, 3347.6).buffer(4.5)]
    return out
