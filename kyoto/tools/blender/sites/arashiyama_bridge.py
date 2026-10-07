"""渡月橋 (155 m, 12.2 m, 14 bents), 渡月小橋 (19 m, one bent) and 中ノ島橋 (30 m, arched): the 1934 concrete bridges
dressed as the old wooden one.  Deck with a 1 m bow, asphalt carriageway and raised granite-slab sidewalks with a row
of low lit bollards, the wooden lattice railing (posts, top rail with metal plates, mid rail, diagonal braces), the grey
concrete fascia and the sloped skirt of timber slats under it, girders on heavy cap beams whose ends show under the
deck, round grey columns with tie beams, the upstream raking struts to short piles with plank sills, and the
free-standing fender pairs upstream of every bent.

Local frame per bridge: u along the axis (0 at the start end), v across (+v to the left = upstream for 渡月橋)."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from jk import prim, Frame
import sites.machiya as M
import sites.arashiyama_util as U

def osm_line(S, wid):
    for w in S.osm['ways']:
        if w['id'] == wid: return np.asarray(w['line'][0], float)
    raise KeyError(wid)

class Bridge:
    def __init__(self, S, A, Bp, width, spans, bow, river, road=7.2, kerb=0.15, sw_h=0.18, upstream=1, fenders=True, cols=4, name='bridge',
                 rail_h=1.08, zA=None, zB=None, skirt=0.7, carriage=True, lift=0.03):
        self.S = S; self.river = river; self.name = name
        A = np.asarray(A, float); Bp = np.asarray(Bp, float)
        d = Bp - A; self.L = float(np.linalg.norm(d)); self.d = d / self.L; self.n = np.array([-self.d[1], self.d[0]])
        self.A = A; self.yaw = math.atan2(d[1], d[0])
        self.W = width; self.hw = width / 2; self.road = road; self.kerb = kerb; self.sw_h = sw_h
        self.spans = spans; self.bow = bow; self.up = upstream; self.fenders = fenders; self.cols = cols
        self.rail_h = rail_h; self.skirt = skirt; self.carriage = carriage
        self.zA = (zA if zA is not None else float(S.ground(*(A - self.d * 1.2)))) + lift
        self.zB = (zB if zB is not None else float(S.ground(*(Bp + self.d * 1.2)))) + lift
        self.bents = [self.L * k / spans for k in range(1, spans)]

    def z(self, u):
        t = np.clip(np.asarray(u, float) / self.L, 0, 1)
        return self.zA + (self.zB - self.zA) * t + self.bow * np.sin(math.pi * t)

    def world(self, u, v):
        return self.A + self.d * u + self.n * v

    def footprint(self, pad=0.0):
        c = [self.world(-pad, -self.hw - pad), self.world(self.L + pad, -self.hw - pad), self.world(self.L + pad, self.hw + pad), self.world(-pad, self.hw + pad)]
        return Polygon(c)

    def opening(self, pad_u=3.0, pad_v=0.2):
        """the deck's plan area, run on past both ends: kept free of the water / embankment blockers"""
        c = [self.world(-pad_u, -self.hw - pad_v), self.world(self.L + pad_u, -self.hw - pad_v), self.world(self.L + pad_u, self.hw + pad_v), self.world(-pad_u, self.hw + pad_v)]
        return Polygon(c)

    def zwater(self, u, v=0.0):
        p = self.world(u, v)
        return self.river.level_at(p[0], p[1])

    # ------------------------------------------------------------------------------------------------
    def build(self, B):
        with Frame(B, self.A[0], self.A[1], 0.0, self.yaw):
            self.deck(B)
            for s in (-1, 1):
                self.railing(B, s)
                self.edge(B, s)
            self.under(B)
            for u in self.bents: self.bent(B, u)
            self.ends(B)

    def strip(self, B, v0, v1, dz, mat, tag='main', c1=(0, 0, 0, 0), step=2.0, up=True, u0=0.0, u1=None, walk=False, uv_world=True):
        """a surface strip along the deck between v0 and v1 at z(u) + dz"""
        u1 = self.L if u1 is None else u1
        us = np.linspace(u0, u1, max(2, int(math.ceil((u1 - u0) / step)) + 1))
        P = []; UV = []
        for u in us:
            for v in (v0, v1):
                P.append((u, v, float(self.z(u)) + (dz(u) if callable(dz) else dz)))
                w = self.world(u, v); UV.append((w[0], w[1]) if uv_world else (u, v))
        P = np.array(P); UV = np.array(UV); I = []
        for i in range(len(us) - 1):
            a = 2 * i
            I += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
        I = np.array(I)
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if (fn[:, 2].sum() < 0) == up: I = I[:, ::-1]
        B.add(P, I, mat, UV=UV, tag=tag, c1=c1)
        if walk: B.add(P, I, 'ground', tag='walk')

    def wall(self, B, v, za, zb, mat, facing, tag='main', step=2.0, u0=0.0, u1=None, c0=(255, 255, 255, 0)):
        """a vertical strip at constant v between z(u)+za and z(u)+zb, facing +v (facing=1) or -v"""
        u1 = self.L if u1 is None else u1
        us = np.linspace(u0, u1, max(2, int(math.ceil((u1 - u0) / step)) + 1))
        Q = []; UV = []
        for a, b in zip(us[:-1], us[1:]):
            za_, zb_ = float(self.z(a)), float(self.z(b))
            q = [(a, v, za_ + za), (b, v, zb_ + za), (b, v, zb_ + zb), (a, v, za_ + zb)]
            if facing > 0: q = [q[1], q[0], q[3], q[2]]
            Q.append(q); UV.append([(a, za), (b, za), (b, zb), (a, zb)] if facing < 0 else [(b, za), (a, za), (a, zb), (b, zb)])
        M.quads(B, Q, mat, UV=UV, tag=tag, c0=c0)

    def deck(self, B):
        hw = self.hw; r = self.road / 2; k = self.kerb; h = self.sw_h
        if self.carriage:
            self.strip(B, -r, r, 0.0, 'ground', c1=(0, 0, 0, 1), walk=True)
            # dashed centre line
            Q = []
            for u in np.arange(4.0, self.L - 4.0, 6.0):
                a, b = u, min(u + 3.0, self.L - 4)
                Q.append([(a, -0.07, float(self.z(a)) + 0.012), (b, -0.07, float(self.z(b)) + 0.012), (b, 0.07, float(self.z(b)) + 0.012), (a, 0.07, float(self.z(a)) + 0.012)])
            M.quads(B, Q, 'white_paint', tag='detail', c0=M.paint_tint((225, 225, 220), base=(0.7, 0.68, 0.62)))
            for s in (-1, 1):
                # kerb (top + the face to the road)
                self.strip(B, s * r, s * (r + k), h, 'curb', uv_world=False)
                self.wall(B, s * r, 0.0, h, 'curb', facing=-s)
            sw0 = r + k
        else:
            sw0 = 0.0
        for s in (-1, 1):
            if self.carriage:
                self.strip(B, s * sw0, s * (hw - 0.02), h, 'ground', c1=(0, 0, 0, 17), walk=True)
            else:
                self.strip(B, 0.0, s * (hw - 0.02), h, 'ground', c1=(0, 0, 0, 17), walk=True)
        # walk beyond the ends onto the land
        for (u0, u1) in ((-1.5, 0.0), (self.L, self.L + 1.5)):
            self.strip(B, -hw + 0.3, hw - 0.3, h * 0.5, 'ground', tag='walk', u0=u0, u1=u1, step=1.5)
        # blockers: the railings
        for s in (-1, 1):
            pts = [np.array([u, s * (hw - 0.17)]) for u in np.linspace(0.0, self.L, 12)]
            U.block_strip(B, pts, float(self.z(self.L / 2)) + 0.6, 0.4)
        # lit bollards along the kerbs (stone cylinders with a light slot)
        if self.carriage:
            for s in (-1, 1):
                for u in np.arange(3.0, self.L - 2.0, 6.0):
                    v = s * (sw0 + 0.25); z0 = float(self.z(u)) + h
                    prim.cyl(B, (u, v, z0), (u, v, z0 + 0.5), 0.12, 0.12, 8, 'curb', caps=(False, False), tag='main')
                    prim.cyl(B, (u, v, z0 + 0.5), (u, v, z0 + 0.6), 0.115, 0.115, 8, 'lamp', caps=(False, False), tag='main')
                    prim.lathe(B, (u, v, z0 + 0.6), [(0.12, 0.0), (0.12, 0.08), (0.08, 0.16), (0.0, 0.19)], 8, 'curb', tag='main')
                    B.lamp(u, v, z0 + 0.55, 1.6, (1.0, 0.8, 0.55))

    def railing(self, B, s):
        hw = self.hw; h = self.sw_h; H = self.rail_h
        v = s * (hw - 0.17)
        n = max(2, int(round((self.L - 0.6) / 1.95)))
        us = np.linspace(0.35, self.L - 0.35, n + 1)
        zs = self.z(us) + h
        # 地覆 (bottom curb board) and the rails: continuous sweeps along the posts
        uu = np.linspace(0.1, self.L - 0.1, max(8, int(self.L / 2.5)))
        zz = self.z(uu) + h
        def rail(zoff, w, hh, mat='wood_dark', tag='main', dv=0.0):
            path = np.c_[uu, np.full(len(uu), v + dv), zz + zoff]
            prim.sweep(B, path, [(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2), (-w / 2, hh / 2)], mat, tag=tag, caps=True)
        rail(0.09, 0.26, 0.18)                                   # 地覆
        rail(H - 0.055, 0.25, 0.11)                              # 笠木 (top rail)
        rail(H * 0.7, 0.12, 0.1)                                 # mid rail
        rail(0.24, 0.1, 0.09, tag='detail')                      # lower rail
        # posts
        M.bars(B, np.c_[us, np.full(len(us), v), zs + 0.18], np.c_[us, np.full(len(us), v), zs + H - 0.1], (1, 0, 0), 0.17, 0.17, 'wood_dark', tag='main', caps=False)
        # metal joint plates on the top rail at every post
        M.bars(B, np.c_[us - 0.16, np.full(len(us), v), zs + H + 0.005], np.c_[us + 0.16, np.full(len(us), v), zs + H + 0.005], (0, 0, 1), 0.02, 0.27, 'metal_dark', tag='detail', caps=True)
        # diagonal braces rising in each panel, a short strut between mid and top rail
        a = us[:-1]; b = us[1:]
        if s < 0: a, b = b, a                                    # mirror on the other side
        p0 = np.c_[a + (b - a) * 0.08, np.full(len(a), v), self.z(a + (b - a) * 0.08) + h + 0.3]
        p1 = np.c_[a + (b - a) * 0.5, np.full(len(a), v), self.z(a + (b - a) * 0.5) + h + H * 0.7 - 0.05]
        M.bars(B, p0, p1, (0, 1, 0), 0.075, 0.09, 'wood_dark', tag='detail')
        m = (us[:-1] + us[1:]) / 2
        M.bars(B, np.c_[m, np.full(len(m), v), self.z(m) + h + H * 0.7 + 0.05], np.c_[m, np.full(len(m), v), self.z(m) + h + H - 0.11], (1, 0, 0), 0.08, 0.08, 'wood_dark', tag='detail')

    def edge(self, B, s):
        """fascia and the sloped skirt of timber slats"""
        hw = self.hw; sk = self.skirt
        self.wall(B, s * hw, -0.24, self.sw_h, 'curb', facing=s)
        # the skirt: from under the fascia (hw, -0.24) down and in to (hw - 0.7, -0.24 - sk)
        vi = s * (hw - 0.72); vo = s * (hw - 0.02)
        us = np.linspace(0.0, self.L, max(2, int(self.L / 2.0)) + 1)
        Q = []
        for a, b in zip(us[:-1], us[1:]):
            q = [(a, vo, float(self.z(a)) - 0.24), (b, vo, float(self.z(b)) - 0.24), (b, vi, float(self.z(b)) - 0.24 - sk), (a, vi, float(self.z(a)) - 0.24 - sk)]
            fn = np.cross(np.subtract(q[1], q[0]), np.subtract(q[2], q[0]))
            if fn[1] * s < 0: q = [q[1], q[0], q[3], q[2]]
            Q.append(q)
        M.quads(B, Q, 'wood_dark', tag='main', c1=(0, 0, 0, 0))
        n = int(self.L / 0.24)
        uu = (np.arange(n) + 0.5) * self.L / n
        z0 = self.z(uu) - 0.22; z1 = self.z(uu) - 0.24 - sk + 0.02
        P0 = np.c_[uu, np.full(n, s * (hw + 0.02)), z0]; P1 = np.c_[uu, np.full(n, s * (hw - 0.7)), z1]
        M.bars(B, P0, P1, (1, 0, 0), 0.09, 0.07, 'wood_dark', tag='detail')
        # the beam under the skirt's foot
        M.bars(B, [(0.0, s * (hw - 0.75), float(self.z(0)) - 0.3 - sk)], [(self.L, s * (hw - 0.75), float(self.z(self.L)) - 0.3 - sk)], (0, 0, 1), 0.25, 0.2, 'curb', tag='detail')

    def under(self, B):
        hw = self.hw; sk = self.skirt
        self.strip(B, -(hw - 0.72), hw - 0.72, -0.24 - sk, 'curb', up=False, uv_world=False)
        # longitudinal girders between the bents
        stations = [0.0] + self.bents + [self.L]
        gv = [-(hw - 1.4), -(hw - 1.4) / 3, (hw - 1.4) / 3, hw - 1.4]
        for a, b in zip(stations[:-1], stations[1:]):
            P0 = []; P1 = []
            for v in gv:
                P0.append((a, v, float(self.z(a)) - 0.24 - sk - 0.2)); P1.append((b, v, float(self.z(b)) - 0.24 - sk - 0.2))
            M.bars(B, P0, P1, (0, 1, 0), 0.42, 0.4, 'curb', tag='main', caps=False)

    def bent(self, B, u):
        hw = self.hw; sk = self.skirt; up = self.up
        zd = float(self.z(u)); zc = zd - 0.24 - sk - 0.4           # cap top
        zw = self.zwater(u)
        zbed = zw - 1.3
        # cap beam with ends proud of the deck edge
        M.hbox(B, u - 0.34, u + 0.34, -(hw + 0.62), hw + 0.62, zc - 0.55, zc, 'curb', tag='main')
        # columns
        vs = np.linspace(-(hw - 1.0), hw - 1.0, self.cols)
        for v in vs:
            prim.cyl(B, (u, v, zbed), (u, v, zc - 0.55), 0.28, 0.27, 12, 'curb', caps=(False, False), tag='main')
        # tie beams (貫): upper and lower
        zt = zc - 0.55 - (zc - 0.55 - zw) * 0.42
        M.hbox(B, u - 0.15, u + 0.15, -(hw - 0.5), hw - 0.5, zt - 0.36, zt, 'curb', tag='main')
        M.hbox(B, u - 0.14, u + 0.14, -(hw - 0.6), hw - 0.6, zw + 0.35, zw + 0.68, 'curb', tag='detail')
        # the upstream raking strut down to a short pile, plank sills either side of the columns
        vo = up * (hw - 1.0); vp = up * (hw + 2.1)
        prim.cyl(B, (u, vo, zc - 0.9), (u, vp, zw + 0.5), 0.17, 0.17, 8, 'curb', caps=(True, True), tag='main')
        prim.cyl(B, (u, vp, zbed), (u, vp, zw + 0.95), 0.2, 0.2, 10, 'curb', caps=(False, True), tag='main')
        for du in (-0.36, 0.36):
            M.hbox(B, u + du - 0.05, u + du + 0.05, min(vo, vp) - 0.3, max(vo, vp) + 0.3, zw + 0.3, zw + 0.6, 'wood_natural', tag='detail', c0=(170, 160, 140, 0))
        # the fender pair upstream (流木除け)
        if self.fenders:
            va = up * (hw + 6.4); vb = up * (hw + 9.0)
            pa = self.world(u, va); pb = self.world(u, vb)
            if self.river.all.contains(Point(*pb)) or self.river.all.contains(Point(*pa)):
                zf = self.zwater(u, vb)
                prim.cyl(B, (u, vb, zf - 1.2), (u, vb, zf + 2.25), 0.27, 0.26, 12, 'curb', caps=(False, True), tag='main')
                prim.cyl(B, (u, va, zf - 1.2), (u, va, zf + 1.05), 0.25, 0.25, 12, 'curb', caps=(False, True), tag='main')
                prim.cyl(B, (u, vb, zf + 1.95), (u, va, zf + 0.95), 0.19, 0.19, 8, 'curb', caps=(True, True), tag='main')
                M.hbox(B, u - 0.15, u + 0.15, min(va, vb), max(va, vb), zf + 0.22, zf + 0.55, 'curb', tag='main')

    def ends(self, B):
        """親柱 (end posts) with name plates, the stone abutments"""
        hw = self.hw; h = self.sw_h
        for u, e in ((0.0, -1), (self.L, 1)):
            z = float(self.z(u)) + h
            for s in (-1, 1):
                v = s * (hw - 0.2)
                M.hbox(B, u - 0.2, u + 0.2, v - 0.2, v + 0.2, z, z + 1.45, 'wood_dark', tag='main')
                M.hbox(B, u - 0.24, u + 0.24, v - 0.24, v + 0.24, z + 1.45, z + 1.55, 'wood_dark', tag='main')
                prim.lathe(B, (u, v, z + 1.55), [(0.2, 0.0), (0.14, 0.12), (0.0, 0.2)], 4, 'metal_dark', tag='detail', smooth=False)
                # name plate on the inner face
                M.oquad(B, [(u - 0.12, v - s * 0.205, z + 0.5), (u + 0.12, v - s * 0.205, z + 0.5), (u + 0.12, v - s * 0.205, z + 1.25), (u - 0.12, v - s * 0.205, z + 1.25)],
                        (0, -s, 0), 'white_paint', tag='detail', uv=np.array([(0, 0), (0.5, 0), (0.5, 1.1), (0, 1.1)]), c1=(0, 7, 31 + s * 7 + e * 3, 0))
        # abutments: stone faced, where the axis meets the water, from the deck down to the bed
        us = np.arange(0.0, self.L, 0.5)
        wet = np.array([self.river.all.contains(Point(*self.world(u, 0.0))) for u in us])
        if wet.any():
            for ue, e in ((us[np.argmax(wet)], -1), (us[len(us) - 1 - np.argmax(wet[::-1])], 1)):
                zw = self.zwater(ue - e * 3.0)
                ua, ub = (ue - 2.0, ue + 0.2) if e < 0 else (ue - 0.2, ue + 2.0)
                M.hbox(B, ua, ub, -(hw + 0.4), hw + 0.4, zw - 1.4, float(self.z(ue)) - 0.3, 'stone', tag='main', faces='xXyY')

def build(B, S, river):
    """the three bridges; returns their deck footprints (for the water blockers)"""
    out = []
    # 渡月橋: the road line (OSM 28640677) from the 中之島 end (south) to the north end
    c = osm_line(S, 28640677)
    A, Bp = (c[0], c[-1]) if c[0][1] < c[-1][1] else (c[-1], c[0])
    tg = Bridge(S, A, Bp, 12.2, 15, 1.0, river, road=7.2, name='togetsukyo', upstream=1)
    tg.build(B); out.append(tg)
    # 渡月小橋 (OSM 59377345): 19 m, 11 m wide, one bent; north end on 中之島
    c = osm_line(S, 59377345)
    A, Bp = (c[0], c[-1]) if c[0][1] < c[-1][1] else (c[-1], c[0])
    d = (Bp - A) / np.linalg.norm(Bp - A)
    ko = Bridge(S, A - d * 0.5, Bp + d * 0.5, 11.0, 2, 0.1, river, road=6.4, name='kobashi', upstream=1 if d[1] > 0 else -1, fenders=False)
    ko.build(B); out.append(ko)
    # 中ノ島橋 (OSM 59379040): a 30 m footbridge, gentle arch (太鼓橋), 5.5 m wide
    c = osm_line(S, 59379040)
    A, Bp = (c[0], c[-1]) if c[0][1] < c[-1][1] else (c[-1], c[0])
    d = (Bp - A) / np.linalg.norm(Bp - A)
    nk = Bridge(S, A - d * 1.0, Bp + d * 1.0, 5.5, 3, 0.9, river, road=0.0, carriage=False, name='nakanoshima', fenders=False, cols=3, skirt=0.6, rail_h=1.0)
    nk.build(B); out.append(nk)
    print('bridges:', [(b.name, round(b.L, 1), round(b.zA, 2), round(float(b.z(b.L / 2)), 2), round(b.zB, 2)) for b in out])
    return out
