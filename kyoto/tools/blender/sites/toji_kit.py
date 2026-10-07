"""東寺 (教王護国寺): shared helpers for the site modules — plain geometry (slabs, quads, walk / block pieces), a
kirizuma / irimoya roof whose gable wall starts above the bracket zone, the 八脚門 gate type (南大門, 慶賀門, 東大門,
北大門, 蓮花門), a generic single-storey temple hall, the battered 築地塀 (大垣) with embedded posts, lanterns and
風鐸.  Local frames follow jk.Frame: u along the front, v depth (the front faces -v), z absolute (T.P.)."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof

WOOD = 'wood_dark'
PLASTER = (236, 232, 222, 35)
EARTH = (190, 160, 112, 35)          # 築地塀 (大垣): ochre earth plaster

def rect(hu, hv=None, cu=0.0, cv=0.0):
    hv = hu if hv is None else hv
    return [(cu - hu, cv - hv), (cu + hu, cv - hv), (cu + hu, cv + hv), (cu - hu, cv + hv)]

def slab(B, x0, y0, x1, y1, z0, z1, mat, tag='main', faces='all', **kw):
    prim.box(B, min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1), mat, tag=tag, faces=faces, **kw)

def quad(B, p0, p1, p2, p3, mat, tag='main', both=False, **kw):
    P = np.array([p0, p1, p2, p3], float)
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, tag=tag, **kw)
    if both: B.add(P, [[0, 2, 1], [0, 3, 2]], mat, tag=tag, **kw)

def walk_poly(B, pts, z):
    prim.polygon(B, pts, z, 'stone', tag='walk')

def walk_rect(B, x0, y0, x1, y1, z):
    walk_poly(B, [(min(x0, x1), min(y0, y1)), (max(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)), (min(x0, x1), max(y0, y1))], z)

def block_poly(B, pts, z):
    prim.polygon(B, pts, z, 'stone', tag='block')

def block_rect(B, x0, y0, x1, y1, z):
    block_poly(B, [(min(x0, x1), min(y0, y1)), (max(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)), (min(x0, x1), max(y0, y1))], z)

def block_line(B, pts, z, w=0.6):
    """a blocker strip along a 2D polyline (blockers are rasterised in plan: give them ≥ 0.5 m of width)"""
    pts = [np.asarray(p, float) for p in pts]
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a; L = np.linalg.norm(d)
        if L < 1e-6: continue
        d /= L; n = np.array([-d[1], d[0]]) * w / 2
        a2 = a - d * w / 4; b2 = b + d * w / 4
        P = np.array([np.r_[a2 - n, z], np.r_[b2 - n, z], np.r_[b2 + n, z], np.r_[a2 + n, z]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='block')

def beam(B, p0, p1, z, w, h, mat=WOOD, tag='main', ext=0.0):
    """a horizontal beam between two 2D points, top at z"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-9)
    prim.obox(B, np.r_[p0 - d * ext, z - h / 2], np.r_[p1 + d * ext, z - h / 2], w, h, mat, tag=tag)

def post(B, x, y, z0, z1, r, mat=WOOD, seg=12, base='stone', tag='main', base_h=0.25):
    if base:
        prim.cyl(B, (x, y, z0 - 0.08), (x, y, z0 + base_h * 0.5), r * 1.55, r * 1.4, 10, base, tag=tag, caps=(False, True))
    prim.cyl(B, (x, y, z0), (x, y, z1), r, r * 0.96, seg, mat, caps=(False, True), tag=tag)

def furin(B, x, y, z, s=1.0):
    """風鐸: a bronze bell under a roof corner"""
    prim.cyl(B, (x, y, z - 0.35 * s), (x, y, z), 0.012, 0.012, 4, 'metal_dark', tag='detail')
    prim.lathe(B, (x, y, z - 0.8 * s), [(0.0, 0.0), (0.16 * s, 0.03 * s), (0.15 * s, 0.22 * s), (0.11 * s, 0.4 * s), (0.0, 0.45 * s)], 8, 'bronze', tag='detail')
    prim.box(B, x - 0.08 * s, y - 0.01, z - 1.15 * s, x + 0.08 * s, y + 0.01, z - 0.82 * s, 'bronze', tag='detail')

def bronze_lantern(B, x, y, z, h=2.4, lit=True):
    """金銅灯籠 / 釣灯籠-style standing lantern on a stone base (in front of the halls)"""
    s = h / 2.4
    prim.cyl(B, (x, y, z), (x, y, z + 0.35 * s), 0.42 * s, 0.38 * s, 8, 'stone')
    prim.cyl(B, (x, y, z + 0.35 * s), (x, y, z + 1.25 * s), 0.09 * s, 0.08 * s, 10, 'bronze')
    prim.cyl(B, (x, y, z + 1.25 * s), (x, y, z + 1.35 * s), 0.3 * s, 0.32 * s, 6, 'bronze')
    prim.cyl(B, (x, y, z + 1.35 * s), (x, y, z + 1.8 * s), 0.25 * s, 0.25 * s, 6, 'lantern_paper' if lit else 'bronze', caps=(False, False), tag='detail')
    for k in range(6):
        a = k * math.pi / 3
        prim.obox(B, (x + 0.27 * s * math.cos(a), y + 0.27 * s * math.sin(a), z + 1.35 * s), (x + 0.27 * s * math.cos(a), y + 0.27 * s * math.sin(a), z + 1.8 * s), 0.03, 0.03, 'bronze', tag='detail')
    prim.lathe(B, (x, y, z + 1.8 * s), [(0.46 * s, 0.0), (0.48 * s, 0.05 * s), (0.25 * s, 0.25 * s), (0.08 * s, 0.38 * s), (0.12 * s, 0.46 * s), (0.0, 0.62 * s)], 6, 'bronze', smooth=False)
    if lit: B.lamp(x, y, z + 1.58 * s, 14.0, (1.0, 0.6, 0.3))

def stone_lantern(B, x, y, z, h=2.2, lit=True):
    arch.ishidoro(B, x, y, z, h=h, lamp=lit)
    if lit: B.lamp(x, y, z + h * 0.64, 7.0, (1.0, 0.58, 0.28))

def hanging_lantern(B, x, y, ztop, text=True, r=0.42, h=1.2):
    """the big white paper lanterns hung in the gates (東寺): white paper, black caps"""
    prim.cyl(B, (x, y, ztop - 0.25), (x, y, ztop), 0.015, 0.015, 4, 'metal_dark', tag='detail')
    z = ztop - 0.25 - h
    prim.lathe(B, (x, y, z), [(r * 0.72, 0.0), (r * 0.97, h * 0.18), (r, h * 0.5), (r * 0.97, h * 0.82), (r * 0.72, h)], 14, 'lantern_paper')
    prim.cyl(B, (x, y, z - 0.08), (x, y, z + 0.02), r * 0.75, r * 0.75, 12, 'black_lacquer', tag='detail')
    prim.cyl(B, (x, y, z + h - 0.02), (x, y, z + h + 0.1), r * 0.75, r * 0.75, 12, 'black_lacquer', tag='detail')
    prim.box(B, x - r * 0.75, y - r * 0.75, z + h + 0.1, x + r * 0.75, y + r * 0.75, z + h + 0.3, 'black_lacquer', tag='detail')
    B.lamp(x, y, z + h * 0.5, 9.0, (1.0, 0.62, 0.34))

# ------------------------------------------------------------------ roofs
class TRoof(jroof.Roof):
    """jk.roof.Roof with the gable wall (妻壁) cut off below `gable_base` (absolute z) so that it does not slice
    through the bracket sets on the end pillars; optionally a 虹梁 + 大瓶束 frame across the gable (gable_frame)."""
    gable_base = None
    gable_frame = None              # (z_beam, width) of a 虹梁 across the gable at the pillar line

    def gable(self, B, u_g, s_from, vo):
        if self.gable_base is None:
            return super().gable(B, u_g, s_from, vo)
        c = self.c
        zb0 = max(float(self.z(s_from, s_from)) - 0.05, self.gable_base)
        ss = np.linspace(s_from, c, 14)
        for sgn in (-1, 1):
            u = sgn * u_g
            top = [(u, -c + s, float(self.z(s, c)) - self.edge - 0.05) for s in ss]
            top += [(u, c - s, float(self.z(s, c)) - self.edge - 0.05) for s in ss[::-1][1:]]
            top = [p for p in top if p[2] > zb0 + 0.02]
            if len(top) >= 2:
                y0, y1 = top[0][1], top[-1][1]
                poly = np.array(top + [(u, y1, zb0), (u, y0, zb0)])
                cen = np.array([u, 0.0, zb0])
                Pall = np.concatenate([[cen], poly]); n = len(poly)
                I = [[0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
                fn = np.cross(Pall[I[0][1]] - Pall[0], Pall[I[0][2]] - Pall[0])
                if fn[0] * sgn < 0: I = [t[::-1] for t in I]
                B.add(Pall, I, self.gable_wall, UV=np.c_[Pall[:, 1], Pall[:, 2]], tag=self.tag, c0=PLASTER, c1=(0, 0, 0, 0))
                B.add(Pall, [t[::-1] for t in I], self.gable_wall, UV=np.c_[Pall[:, 1], Pall[:, 2]], tag=self.tag, c0=PLASTER, c1=(0, 0, 0, 0))
                # the gable's frame: a beam along the base, a strut (大瓶束) up the middle
                prim.obox(B, (u + sgn * 0.02, y0, zb0 + 0.12), (u + sgn * 0.02, y1, zb0 + 0.12), 0.24, 0.3, self.bargeboard_mat, tag=self.tag)
                zt = float(self.z(c, c)) - self.edge - 0.3
                if zt > zb0 + 0.6:
                    prim.obox(B, (u + sgn * 0.04, 0, zb0 + 0.25), (u + sgn * 0.04, 0, zt), 0.26, 0.26, self.bargeboard_mat, tag='detail')
                    for fz in (0.42, 0.72):
                        zz = zb0 + (zt - zb0) * fz
                        w_ = (c - (zz - zb0) / max(zt - zb0, 1e-3) * c) * 0.9
                        if w_ > 0.6: prim.obox(B, (u + sgn * 0.04, -w_, zz), (u + sgn * 0.04, w_, zz), 0.14, 0.18, self.bargeboard_mat, tag='detail')
            ue = u + sgn * vo
            for side in (-1, 1):
                pts = np.array([(ue, side * (c - s), float(self.z(s, c)) - self.edge * 0.6) for s in ss])
                prim.sweep(B, pts, [(-0.07, 0.0), (0.07, 0.0), (0.07, -0.5), (-0.07, -0.5)], self.bargeboard_mat, up=(0, 0, 1), tag=self.tag, caps=True)
                pe = np.array([(ue, side * (c - s), float(self.z(s, c))) for s in ss])
                prim.sweep(B, pe, [(-0.13, -self.edge * 0.55), (0.13, -self.edge * 0.55), (0.13, 0.03), (-0.13, 0.03)], self.mat, up=(0, 0, 1), tag=self.tag, caps=True)
                self.ridge(B, pe[::-1] + np.array([-sgn * 0.27, 0, 0.02]), self.ridge_w * 0.55, self.ridge_h * 0.5, ends=(None, 'oni' if self.ends else None))
            # 懸魚 (a large one, three-lobed) under the apex
            za = float(self.z(c, c)) - self.edge - 0.55
            k = max(0.8, min(1.8, c / 5.0))
            gp = [(-0.55, 0.3), (0.55, 0.3), (0.62, -0.1), (0.4, -0.45), (0.0, -0.85), (-0.4, -0.45), (-0.62, -0.1)]
            P = np.array([(ue + sgn * 0.06, y * k, za + zz * k) for (y, zz) in gp])
            I = [[0, j, j + 1] for j in range(1, len(gp) - 1)]
            if sgn < 0: I = [t[::-1] for t in I]
            B.add(P, I, self.bargeboard_mat, tag='detail')
            B.add(P - [sgn * 0.08, 0, 0], [t[::-1] for t in I], self.bargeboard_mat, tag='detail')

def troof(B, L, D, z_eave, o, gable_base=None, **kw):
    r = TRoof(L, D, z_eave, o, **kw)
    r.gable_base = gable_base
    return r, r.build(B)

def bracket_h(kind, s):
    """height (incl. the purlin) and reach of arch.kumimono / bracket_row, for planning"""
    mh = 0.17 * s; hh = 0.17 * s; arm = 0.55 * s
    if kind == 'funa': return 0.17 * s + 0.24 * s, 0.0
    if kind == 'hira': return mh * 1.5 + hh + mh + 0.24 * s, 0.0
    steps = {'demitsudo': 1, 'degumi': 1, 'futatesaki': 2, 'mitesaki': 3}[kind]
    n = steps + (0 if kind == 'demitsudo' else 1)
    return mh * 1.5 + n * (hh + mh) + 0.24 * s, n * arm

def nakazonae(B, p0, p1, z, s, out, mat=WOOD, n=1):
    """間斗束: short posts with a bearing block between bracket sets (on the wall line p0 -> p1, 2D)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    for k in range(n):
        t = (k + 1) / (n + 1)
        q = p0 + (p1 - p0) * t
        prim.box(B, q[0] - 0.08 * s, q[1] - 0.08 * s, z, q[0] + 0.08 * s, q[1] + 0.08 * s, z + 0.48 * s, mat, tag='detail')
        prim.box(B, q[0] - 0.15 * s, q[1] - 0.15 * s, z + 0.48 * s, q[0] + 0.15 * s, q[1] + 0.15 * s, z + 0.66 * s, mat, tag='detail')

# ------------------------------------------------------------------ 八脚門
def gate8(B, cx, cy, zf, yaw, bays=(3.0, 4.2, 3.0), depth=5.0, h=5.0, r_main=0.3, r_back=0.24, bracket=('demitsudo', 0.9), o=2.0,
          pitch=0.5, teri=1.4, sori=0.3, verge=1.0, cover='hongawara', side='plaster', door='open', mat=WOOD, plinth=(0.0, 0.0),
          ridge_h=None, ridge_w=None, edge=0.28, rafter=0.24, tiers=2, lanterns=False, lantern_r=0.45, kaeru=True, tag='main', info=None, gable_mat='temple_wall',
          end_walls=False):
    """a 三間一戸八脚門 in its own frame: main posts on the v = 0 line (doors in the middle bay), 控柱 at v = ±depth/2,
    頭貫 / 虹梁 ties, bracket sets, a 切妻 roof with bargeboards and 懸魚.  The front faces -v.  zf: floor (the gate's
    stone floor top).  plinth = (half-width beyond the posts, height below zf) of the stone base.  Returns a dict."""
    L = sum(bays); us = [-L / 2]
    for b in bays: us.append(us[-1] + b)
    vs = [-depth / 2, 0.0, depth / 2]
    kind, s = bracket
    bh, reach = bracket_h(kind, s)
    out = {}
    with Frame(B, cx, cy, zf, yaw):
        # stone base (基壇) with the walk surface over it
        pm, ph = plinth
        if ph > 0.01:
            slab(B, -L / 2 - pm, -depth / 2 - pm, L / 2 + pm, depth / 2 + pm, -ph - 0.3, 0.0, 'stone', faces='xXyYZ')
        walk_rect(B, -L / 2 - pm - 0.3, -depth / 2 - pm - 0.3, L / 2 + pm + 0.3, depth / 2 + pm + 0.3, 0.0)
        # posts
        for u in us:
            for v in vs:
                r = r_main if v == 0 else r_back
                post(B, u, v, 0.0, h, r, mat, seg=14 if v == 0 else 12)
                block_rect(B, u - r - 0.12, v - r - 0.12, u + r + 0.12, v + r + 0.12, 0.0)
        # 頭貫 along each line, 腰貫 / 飛貫 ties front-back, 虹梁 over the passage
        for v in vs:
            beam(B, (us[0], v), (us[-1], v), h, 0.22, 0.34, mat, ext=0.35)
        for u in us:
            beam(B, (u, vs[0]), (u, vs[-1]), h - 0.05, 0.2, 0.32, mat, ext=0.25)
            beam(B, (u, vs[0]), (u, vs[-1]), h * 0.42, 0.14, 0.24, mat)
        beam(B, (us[1], 0.0), (us[2], 0.0), h * 0.82, 0.24, 0.42, mat)            # 冠木 over the doors
        # side bays: walls on the main line (plaster or boards) with a sill; the middle bay: doors
        for i in (0, 2):
            a = (us[i], 0.0); b = (us[i + 1], 0.0)
            if side == 'plaster':
                arch.infill(B, a, b, 0.25, h - 0.18, 'plaster', out=(0, -1), mat=mat, seed=40 + i)
                beam(B, a, b, 0.3, 0.16, 0.3, mat)
                beam(B, a, b, h * 0.42 + 0.12, 0.13, 0.22, mat)
            elif side == 'board':
                arch.infill(B, a, b, 0.25, h - 0.18, 'board', out=(0, -1), mat=mat)
                beam(B, a, b, h * 0.42 + 0.12, 0.13, 0.22, mat)
            if side != 'open':
                block_line(B, [(us[i], 0.0), (us[i + 1], 0.0)], 0.0, 0.7)
        if end_walls:          # the gable ends boarded up between the three posts (南大門)
            for u in (us[0], us[-1]):
                for (va, vb) in ((vs[0], vs[1]), (vs[1], vs[2])):
                    arch.infill(B, (u, va), (u, vb), 0.2, h - 0.2, 'board', out=(1 if u > 0 else -1, 0), mat=mat)
                block_line(B, [(u, vs[0]), (u, vs[-1])], 0.0, 0.6)
        if door in ('open', 'closed'):
            w = (bays[1] - 2 * r_main) / 2
            for sgn in (-1, 1):
                hinge = np.array([sgn * (bays[1] / 2 - r_main - 0.02), 0.25])
                if door == 'open':      # leaves swung back against the posts (inward, +v)
                    a0 = hinge; a1 = hinge + np.array([0.0, w])
                else:
                    a0 = hinge; a1 = hinge + np.array([-sgn * w, 0.0])
                d = a1 - a0; n = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
                P = np.array([np.r_[a0, 0.05], np.r_[a1, 0.05], np.r_[a1, h * 0.8 - 0.15], np.r_[a0, h * 0.8 - 0.15]])
                quad(B, *P, mat, both=True)
                for zz in np.linspace(0.3, h * 0.8 - 0.4, 5):
                    prim.obox(B, np.r_[a0 + n * 0.05, zz], np.r_[a1 + n * 0.05, zz], 0.05, 0.12, mat, tag='detail')
                    prim.obox(B, np.r_[a0 - n * 0.05, zz], np.r_[a1 - n * 0.05, zz], 0.05, 0.12, mat, tag='detail')
                if door == 'closed': block_line(B, [a0, a1], 0.0, 0.6)
            prim.obox(B, (us[1], 0.0, 0.08), (us[2], 0.0, 0.08), 0.22, 0.16, mat)          # 蹴放 (threshold)
        # brackets on the posts + 間斗束 between, the purlin
        top, rr = arch.bracket_row(B, L, depth, h, kind, s, mat, mat, us=np.array(us), vs=np.array(vs), purlin=True)
        for i in range(3):
            for v in (vs[0], vs[-1]):
                nakazonae(B, (us[i], v), (us[i + 1], v), h, s, (0, -1 if v < 0 else 1), mat, n=1 if bays[i] < 4.5 else 2)
        # the two inner main posts carry a simple set too
        for u in us[1:-1]:
            arch.kumimono(B, u, 0.0, h, (0, -1), (1, 0), 'hira', s, mat, tag='detail')
        # boards between the brackets on the outer lines (小壁), both faces
        for v in (vs[0], vs[-1]):
            for i in range(3):
                quad(B, (us[i] + 0.2, v, h + 0.02), (us[i + 1] - 0.2, v, h + 0.02), (us[i + 1] - 0.2, v, top - 0.2), (us[i] + 0.2, v, top - 0.2), 'temple_wall', both=True, c0=PLASTER)
        # ceiling over the passage (化粧屋根裏: a flat board at the bracket top)
        slab(B, us[0] - 0.2, vs[0] - 0.2, us[-1] + 0.2, vs[-1] + 0.2, top - 0.08, top + 0.02, mat, faces='z')
        Lr = L; Dr = depth + 2 * reach
        z_eave = top + 0.32
        rf, res = troof(B, Lr, Dr, z_eave, o, gable_base=top + 0.25, kind='kirizuma', cover=cover, pitch=pitch, teri=teri, sori=sori, verge=verge + reach,
                        edge=edge, rafter=rafter, rafter_mat=mat, rafter_end=mat, fascia_mat=mat, ends='oni', ridge_h=ridge_h, ridge_w=ridge_w,
                        tiers=tiers, bargeboard_mat=mat, gable_wall=gable_mat, tag=tag)
        out.update(res); out['top'] = top; out['L'] = L; out['us'] = us
        if lanterns:
            for u in (-bays[1] / 2 - 0.05, bays[1] / 2 + 0.05):
                hanging_lantern(B, u * 0.62, -0.6, h * 0.8, r=lantern_r, h=lantern_r * 2.6)
        if kaeru:
            # 蟇股 between the 頭貫 and 冠木 in the middle bay, both faces
            for v in (vs[0], vs[-1]):
                prim.box(B, -0.35, v - 0.08, h + 0.02, 0.35, v + 0.08, h + 0.42, mat, tag='detail')
    if info is not None: info.update(out)
    return out

# ------------------------------------------------------------------ 築地塀 (大垣)
def tsuiji(B, S, pts, h=3.1, base=1.5, top=0.85, post_every=2.75, tint=EARTH, coping='hongawara', gaps=(), lines=0, tag='main', block=True,
           outer=1, zfn=None):
    """the earthen precinct wall: battered (base `base` wide, `top` at the coping), a cut-stone footing, dark posts
    set into the outer face (寄柱) every `post_every`, a tiled coping (本瓦 with a ridge), optional white 定規筋.
    pts: 2D polyline; gaps: list of (t0, t1) distances along the line to leave open (gates).  outer: +1 = the posts
    face the left of the line direction, -1 the right."""
    zfn = zfn or (lambda x, y: float(S.ground(x, y)))
    pts = [np.asarray(p, float) for p in pts]
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a; L = float(np.linalg.norm(d))
        if L < 0.2: acc += L; continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(round(L / post_every)))
        for j in range(k):
            t0 = L * j / k; t1 = L * (j + 1) / k
            ga, gb = acc + t0, acc + t1
            skip = False
            for (g0, g1) in gaps:
                if gb > g0 and ga < g1:
                    # partial: clip the segment
                    if ga >= g0 and gb <= g1: skip = True; break
                    if ga < g0: t1 = g0 - acc
                    else: t0 = g1 - acc
            if skip or t1 - t0 < 0.15: continue
            p = a + d * t0; q = a + d * t1
            zp_ = zfn(*p); zq_ = zfn(*q); zz = min(zp_, zq_)
            hb, ht = base / 2, top / 2
            # faces (both sides), battered
            for side in (-1, 1):
                A0 = p + n * side * hb; B0 = q + n * side * hb; A1 = p + n * side * ht; B1 = q + n * side * ht
                P = np.array([np.r_[A0, zz + 0.35], np.r_[B0, zz + 0.35], np.r_[B1, zz + h], np.r_[A1, zz + h]])
                I = [[0, 2, 1], [0, 3, 2]] if side > 0 else [[0, 1, 2], [0, 2, 3]]
                B.add(P, I, 'temple_wall', UV=np.array([[0, zz], [t1 - t0, zz], [t1 - t0, zz + h], [0, zz + h]]) + [[acc + t0, 0]] * 4, tag=tag, c0=tint, c1=(0, 0, 0, 0))
                # cut-stone footing
                Pf = np.array([np.r_[p + n * side * (hb + 0.06), zz - 0.3], np.r_[q + n * side * (hb + 0.06), zz - 0.3], np.r_[q + n * side * (hb + 0.03), zz + 0.38], np.r_[p + n * side * (hb + 0.03), zz + 0.38]])
                B.add(Pf, I, 'stone', tag=tag)
                if lines:
                    for li in range(lines):
                        zl = zz + h * (0.5 + 0.075 * li)
                        f = (zl - zz - 0.35) / (h - 0.35)
                        off = hb + (ht - hb) * f + 0.01
                        prim.obox(B, np.r_[p + n * side * off, zl], np.r_[q + n * side * off, zl], 0.02, 0.06, 'white_paint', tag='detail')
            # the post at the segment start (outer face), leaning with the batter
            if j > 0 or (acc + t0) > 0.05:
                pb = p + n * outer * (hb - 0.06); pt = p + n * outer * (ht - 0.06)
                prim.obox(B, np.r_[pb, zz + 0.3], np.r_[pt, zz + h - 0.05], 0.22, 0.2, WOOD, up=(n[0] * outer, n[1] * outer, 0), tag='detail')
            # coping: a small gable roof with tile courses, eaves ~0.45 m beyond the wall top
            oh = ht + 0.5
            for side in (-1, 1):
                A = p + n * side * oh; Bq = q + n * side * oh
                Pc = np.array([np.r_[A, zz + h - 0.08], np.r_[Bq, zz + h - 0.08], np.r_[q, zz + h + 0.42], np.r_[p, zz + h + 0.42]])
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(Pc, I, 'hongawara' if coping == 'hongawara' else 'kawara', UV=np.array([[acc + t0, 0], [acc + t1, 0], [acc + t1, oh], [acc + t0, oh]]), tag=tag)
                # the soffit + fascia under the coping eave
                Ps = np.array([np.r_[p + n * side * ht, zz + h - 0.05], np.r_[q + n * side * ht, zz + h - 0.05], np.r_[Bq, zz + h - 0.2], np.r_[A, zz + h - 0.2]])
                B.add(Ps, [[0, 2, 1], [0, 3, 2]] if side < 0 else [[0, 1, 2], [0, 2, 3]], WOOD, tag=tag)
                Pe = np.array([np.r_[A, zz + h - 0.2], np.r_[Bq, zz + h - 0.2], np.r_[Bq, zz + h - 0.06], np.r_[A, zz + h - 0.06]])
                B.add(Pe, [[0, 2, 1], [0, 3, 2]] if side < 0 else [[0, 1, 2], [0, 2, 3]], 'hongawara', tag=tag)
            prim.obox(B, np.r_[p, zz + h + 0.5], np.r_[q, zz + h + 0.5], 0.3, 0.2, 'ridge', tag=tag)
            if block: block_line(B, [p, q], zz, max(0.8, base))
        acc += L

# ------------------------------------------------------------------ a generic single-storey hall
def bays_on(us, vs):
    """the four outer walls as (side, list of (p0, p1), out normal): 0 front (v-), 1 right (u+), 2 back (v+), 3 left (u-)"""
    a, c = us[-1], vs[-1]
    return [(0, [((us[i], vs[0]), (us[i + 1], vs[0])) for i in range(len(us) - 1)], (0, -1)),
            (1, [((us[-1], vs[i]), (us[-1], vs[i + 1])) for i in range(len(vs) - 1)], (1, 0)),
            (2, [((us[i + 1], vs[-1]), (us[i], vs[-1])) for i in range(len(us) - 1)][::-1], (0, 1)),
            (3, [((us[0], vs[i + 1]), (us[0], vs[i])) for i in range(len(vs) - 1)][::-1], (-1, 0))]

def default_infill(B, side, i, n, p0, p1, out, z0, z1, frame=WOOD):
    """board walls with a 連子窓 band; a 桟唐戸 in the middle bay of the front"""
    if side == 0 and i == n // 2:
        arch.infill(B, p0, p1, z0 + 0.25, z0 + (z1 - z0) * 0.78, 'karado', out=out, mat=frame)
        arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.8, z1 - 0.15, 'plaster', out=out, mat=frame, seed=i)
    else:
        arch.infill(B, p0, p1, z0 + 0.25, z1 - 0.15, 'plaster', out=out, mat=frame, seed=i + 7 * side)

def hall(B, cx, cy, yaw, zp, us, vs, eave, bracket=('degumi', 1.0), o=2.0, pillar_mat=WOOD, frame_mat=WOOD, r=0.27,
         roof_kw=None, infill=default_infill, nageshi=((0.04, 0.24), (0.74, 0.22)), plaster_band=True, ceiling=True, block=True,
         rafter_end=None, roof_class=TRoof, gable_base=False, info=None, end_mat=None):
    """a hall on its own frame: pillars on the outer grid (us, vs, centred), 長押 / 頭貫, wall infills via `infill`,
    bracket sets + 間斗束, plaster between them, a ceiling ring under the eave, the roof (kind / cover in roof_kw) with
    its eave edge at `eave` (absolute z) and `o` metres of rafters beyond the purlin.  zp: floor (platform top)."""
    kw = dict(kind='irimoya', cover='hongawara', pitch=0.6, teri=1.5, sori=0.45, sori_len=0.4, gable_frac=0.55, verge=0.8, edge=0.32,
              rafter=0.26, tiers=2, ends='oni')
    kw.update(roof_kw or {})
    kind, s = bracket
    bh, reach = bracket_h(kind, s)
    L = us[-1] - us[0]; D = vs[-1] - vs[0]
    Lr = L + 2 * reach; Dr = D + 2 * reach
    c = Dr / 2 + o if kw['kind'] != 'hogyo' else max(Lr, Dr) / 2 + o
    H = c * kw['pitch']
    z_eave = eave + H * (o / c) ** kw['teri']
    top = z_eave - 0.32
    h = top - bh
    out = dict(h=h, top=top, z_eave=z_eave, reach=reach, L=L, D=D)
    with Frame(B, cx, cy, 0.0, yaw):
        for u in us:
            for v in vs:
                if u in (us[0], us[-1]) or v in (vs[0], vs[-1]):
                    post(B, u, v, zp, h, r, pillar_mat, seg=12, base='stone', base_h=0.2)
        for (fz, nh) in nageshi:
            zz = zp + (h - zp) * fz
            arch.nageshi(B, L, D, zz + nh / 2, h=nh, w=0.12, out=0.08, mat=frame_mat)
        arch.nageshi(B, L, D, h, h=0.3, w=0.2, out=0.02, mat=frame_mat)            # 頭貫
        for (side, segs, nrm) in bays_on(us, vs):
            for i, (p0, p1) in enumerate(segs):
                infill(B, side, i, len(segs), p0, p1, nrm, zp, h - 0.3, frame_mat)
        top2, rr = arch.bracket_row(B, L, D, h, kind, s, frame_mat, end_mat or frame_mat, us=np.array(us), vs=np.array(vs), purlin=True)
        for (side, segs, nrm) in bays_on(us, vs):
            for (p0, p1) in segs:
                if kind not in ('funa',):
                    nakazonae(B, p0, p1, h, s, nrm, frame_mat, n=1)
                if plaster_band:
                    a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a)
                    quad(B, (*(a + d * 0.2), h + 0.02), (*(b - d * 0.2), h + 0.02), (*(b - d * 0.2), top - 0.15), (*(a + d * 0.2), top - 0.15), 'temple_wall', both=True,
                         c0=PLASTER)
        if ceiling and reach > 0.3:
            a0, c0_ = L / 2 - 0.05, D / 2 - 0.05; a1, c1_ = L / 2 + reach + 0.3, D / 2 + reach + 0.3
            outer = [(-a1, -c1_), (a1, -c1_), (a1, c1_), (-a1, c1_)]; inner = [(-a0, -c0_), (a0, -c0_), (a0, c0_), (-a0, c0_)]
            for i in range(4):
                j = (i + 1) % 4
                P = np.array([(*outer[i], top - 0.12), (*outer[j], top - 0.12), (*inner[j], top - 0.12), (*inner[i], top - 0.12)])
                B.add(P, [[0, 2, 1], [0, 3, 2]], frame_mat)
        rf = roof_class(Lr, Dr, z_eave, o, rafter_mat=frame_mat, rafter_end=rafter_end or frame_mat, fascia_mat=frame_mat, bargeboard_mat=frame_mat, **kw)
        if gable_base: rf.gable_base = top + 0.25
        res = rf.build(B)
        out.update(res); out['roof'] = rf
        if block:
            block_rect(B, -L / 2 - 0.3, -D / 2 - 0.3, L / 2 + 0.3, D / 2 + 0.3, zp + 0.05)
    if info is not None: info.update(out)
    return out

def stone_platform(B, cx, cy, yaw, pts, zg, zp, steps=(), curb=True, edge_block=True):
    """基壇 over a local polygon (CCW) from below the ground to zp, a dressed curb course, a walk surface; steps =
    [(u, v, du, dv, width)] flights going outward from (u, v) on the edge toward (u+du, v+dv) (ground level there)"""
    with Frame(B, cx, cy, 0.0, yaw):
        prim.prism(B, pts, zg - 0.4, zp - 0.15, 'stone', top=False)
        prim.prism(B, pts, zp - 0.15, zp, 'curb', top=False)
        prim.polygon(B, pts, zp, 'stone')
        walk_poly(B, pts, zp)
        gaps = []
        for (u, v, du, dv, w) in steps:
            p0 = np.array([u, v]); p1 = p0 + np.array([du, dv])
            arch.stairs(B, p1, p0, zg, zp, w, 'stone', riser=0.16, walk=True)
            # cheek stones
            d = (p0 - p1) / np.linalg.norm(p0 - p1); n = np.array([-d[1], d[0]])
            for sg in (-1, 1):
                q0 = p1 + n * sg * (w / 2 + 0.2); q1 = p0 + n * sg * (w / 2 + 0.2)
                prim.obox(B, np.r_[q0, zg + 0.1], np.r_[q1, zp - 0.05], 0.4, 0.45, 'curb')
            gaps.append((p0, w))
        if edge_block:
            pts2 = list(pts) + [pts[0]]
            for a, b in zip(pts2[:-1], pts2[1:]):
                a = np.asarray(a, float); b = np.asarray(b, float); L = np.linalg.norm(b - a); d = (b - a) / L
                n_out = np.array([d[1], -d[0]])
                # split the edge around the stair gaps
                cuts = [(0.0, L)]
                for (g, w) in gaps:
                    t = (g - a) @ d; off = abs((g - a) @ n_out)
                    if off < 0.3 and -w < t < L + w:
                        new = []
                        for (t0, t1) in cuts:
                            if t + w / 2 + 0.3 <= t0 or t - w / 2 - 0.3 >= t1: new.append((t0, t1)); continue
                            if t - w / 2 - 0.3 > t0: new.append((t0, t - w / 2 - 0.3))
                            if t + w / 2 + 0.3 < t1: new.append((t + w / 2 + 0.3, t1))
                        cuts = new
                for (t0, t1) in cuts:
                    if t1 - t0 < 0.3: continue
                    q0 = a + d * t0 + n_out * 0.2; q1 = a + d * t1 + n_out * 0.2
                    block_line(B, [q0, q1], zg, 0.5)

def rock(B, c, size, seed, mat='stone', tag='main', flat=0.6):
    """a garden stone: jk.prim.rock with one subdivision (80 faces) instead of two"""
    rng = np.random.default_rng(seed)
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    mid = {}; F2 = []; V = list(V)
    def m(a, b):
        k = (min(a, b), max(a, b))
        if k not in mid:
            p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
        return mid[k]
    for a, b_, c_ in F:
        ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
        F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
    V = np.array(V)
    d = 1 + 0.2 * np.sin(V @ rng.normal(0, 3, 3)) + 0.1 * np.sin(V @ rng.normal(0, 6, 3))
    V = V * d[:, None]
    sx, sy, sz = size * rng.uniform(0.8, 1.2), size * rng.uniform(0.7, 1.1), size * flat * rng.uniform(0.7, 1.2)
    V = V * [sx, sy, sz]
    yaw = rng.uniform(0, 2 * math.pi); cy, sy_ = math.cos(yaw), math.sin(yaw)
    V = V @ np.array([[cy, -sy_, 0], [sy_, cy, 0], [0, 0, 1]]).T
    V = V + np.asarray(c, float) - [0, 0, sz * 0.25]
    B.add(V, F2, mat, smooth=True, tag=tag)

def skirt_roof(B, L, D, z_eave, o, depth, cover='hiwada', pitch=0.3, teri=1.1, sori=0.2, edge=0.28, rafter=0.26, tiers=1, mat=WOOD, hips=True):
    """a 庇 / 錣 skirt round a core: a hip roof whose plan (L x D at its eave posts) is cut off `depth` in from the
    eave line (at the core wall); no ridge.  Returns the jk Roof."""
    rf = jroof.Roof(L, D, z_eave, o, kind='yosemune', cover=cover, pitch=pitch, teri=teri, sori=sori, sori_len=0.35, rafter=rafter, rafter_mat=mat,
                    rafter_end=mat, fascia_mat=mat, tiers=tiers, ends='oni' if cover not in ('hiwada', 'copper') else None, edge=edge, ridge_h=0.4,
                    ridge_w=0.4, truncate=depth)
    smax = lambda xs, dc: np.minimum(np.minimum(dc, rf.c), depth)
    for k in range(4):
        rf.face(B, k, smax=smax); rf.eave(B, k, 0.0, rf.sides()[k][3])
    if hips:
        for k in range(4):
            hl = rf.hip_line(k, depth * 0.97)
            rf.ridge(B, hl[1:][::-1], rf.ridge_w * 0.6, rf.ridge_h * 0.55, ends=(None, 'oni' if rf.ends else None))
    return rf
