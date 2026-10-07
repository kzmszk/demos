"""東福寺 bridges and corridors over the 洗玉澗: 通天橋 with its 舞台, the 歩廊 corridors from the 本堂 / 方丈 side and on to
the 常楽庵 (開山堂) 樓門, the 通天台, 臥雲橋 and 偃月橋.

通天橋 (rebuilt 1961, RC piers): 27 m long, 2.7 m clear width; a 切妻 本瓦 roof on two rows of slender posts, a low
railing outside the posts, a plank deck on a deep beige girder with white beam ends; on the west side the 舞台 projects
2.4 m under its own gable (懸魚, 蟇股).  Built in a frame on the main grid: u east, v north (along the bridge),
origin at the middle of the OSM way 775463879 across the ravine."""
import math
import numpy as np
import jk
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK

ZB = 47.75                      # 通天橋 deck top (T.P.)
TSU = (1358.4, -945.0)          # frame origin
V0, V1 = -13.4, 13.4            # bridge ends (v)
PU = 1.62                       # post lines (u = ±PU)
DHW = 1.95                      # deck half width
NB = 14                         # bays
ST_U = -4.0                     # 舞台 outer post line
ST_V = (-1.1, 2.9)              # 舞台 post lines (v)
GIRDER = (196, 180, 150, 35)    # beige paint of the RC girders / piers

def tsu_loc():
    return L.Loc(TSU[0], TSU[1], L.ROT)

def roof_kirizuma(Bt, L_, D, z_eave, o, pitch, verge, cover='hongawara', ends='oni', gable_wall='wood_dark', rafter=0.26, edge=0.3, teri=1.35):
    R = jroof.Roof(L_, D, z_eave, o, kind='kirizuma', cover=cover, pitch=pitch, verge=verge, rafter=rafter, rafter_mat='wood_dark',
                   rafter_end='white_paint', gable_wall=gable_wall, ends=ends, sori=0.0, edge=edge, teri=teri, tiers=1)
    R.build(Bt)
    return R

# ====================================================================== 通天橋
def tsutenkyo(B, S, valley=None):
    loc = tsu_loc()
    vs = np.linspace(V0, V1, NB + 1)
    rng = np.random.default_rng(4)
    Bm = jk.Builder('tsu_main'); Bs = jk.Builder('tsu_stage')
    with loc.frame(B):
        Bm.xf = B.xf; Bs.xf = B.xf
        # ---------------- deck: planks along v, edge boards, the stage planks along u
        xs = np.arange(-DHW, DHW - 1e-6, 0.26)
        for x in xs:
            prim.box(B, x + 0.006, V0, ZB - 0.07, min(x + 0.26, DHW) - 0.006, V1, ZB, 'wood_natural', faces='Z', c1=(0, 0, int(rng.integers(255)), 0))
        prim.box(B, -DHW, V0, ZB - 0.12, DHW, V1, ZB - 0.07, 'wood_dark', faces='Z')
        for sg in (-1, 1):
            prim.box(B, sg * DHW - 0.09, V0, ZB - 0.36, sg * DHW + 0.09, V1, ZB + 0.02, 'wood_dark')     # 縁葛
        su0, su1 = ST_U - 0.15, -DHW
        for v in np.arange(ST_V[0] - 0.15, ST_V[1] + 0.15 - 1e-6, 0.3):
            prim.box(B, su0, v + 0.006, ZB - 0.07, su1, min(v + 0.3, ST_V[1] + 0.15) - 0.006, ZB, 'wood_natural', faces='Zx', c1=(0, 0, int(rng.integers(255)), 0))
        prim.box(B, su0 - 0.1, ST_V[0] - 0.25, ZB - 0.36, su1, ST_V[1] + 0.25, ZB - 0.07, 'wood_dark')
        # ---------------- under the deck: beige girders, cross beams with white ends, stage cantilevers
        zg0 = ZB - 0.36
        for sg in (-1, 1):
            u = sg * 1.6
            prim.box(B, u - 0.24, V0 - 0.2, zg0 - 1.15, u + 0.24, V1 + 0.2, zg0, 'temple_wall', c0=GIRDER)
        for v in vs:
            prim.box(B, -2.1, v - 0.16, zg0 - 0.55, 2.1, v + 0.16, zg0 - 0.05, 'temple_wall', c0=GIRDER)
            for sg in (-1, 1):
                xa, xb = sorted((sg * 2.09, sg * 2.115))
                prim.box(B, xa, v - 0.165, zg0 - 0.555, xb, v + 0.165, zg0 - 0.045, 'white_paint', tag='detail')
        for v in (ST_V[0], (ST_V[0] + ST_V[1]) / 2, ST_V[1]):
            prim.box(B, ST_U - 0.25, v - 0.17, zg0 - 0.7, -1.4, v + 0.17, zg0, 'temple_wall', c0=GIRDER)
            prim.box(B, ST_U - 0.27, v - 0.175, zg0 - 0.705, ST_U - 0.24, v + 0.175, zg0 + 0.005, 'white_paint', tag='detail')
        # ---------------- RC piers (portal frames), clear of the stream
        def gz(u, v):
            x, y = loc.w(u, v)
            return float(valley.zfn(x, y)) if valley is not None else float(S.ground(x, y))
        piers = [-7.1, -1.6, 7.6]
        if valley is not None:
            for k_, v in enumerate(piers):
                x, y = loc.w(0, v); d, _ = valley.at(np.array([x]), np.array([y]))
                if d[0] < 2.2: piers[k_] = v + (2.4 - d[0]) * (1 if v > 2.0 else -1)
        for v in piers:
            zb_ = min(gz(-1.6, v), gz(1.6, v))
            for sg in (-1, 1):
                u = sg * 1.6
                zg_ = gz(u, v)
                prim.box(B, u - 0.26, v - 0.26, zg_ - 0.6, u + 0.26, v + 0.26, zg0 - 1.1, 'curb')
                prim.box(B, u - 0.55, v - 0.55, zg_ - 0.6, u + 0.55, v + 0.55, zg_ + 0.2, 'curb')
            prim.box(B, -1.95, v - 0.26, zg0 - 1.6, 1.95, v + 0.26, zg0 - 1.1, 'curb')
            if zg0 - zb_ > 6.0:
                zt = (zg0 - 1.1 + zb_) / 2
                prim.box(B, -1.35, v - 0.18, zt - 0.22, 1.35, v + 0.18, zt + 0.22, 'curb')
        # the stage on two columns from the valley floor
        for v in ST_V:
            u = ST_U + 0.3
            zg_ = gz(u, v)
            prim.box(B, u - 0.22, v - 0.22, zg_ - 0.5, u + 0.22, v + 0.22, zg0 - 0.7, 'curb')
            prim.box(B, u - 0.5, v - 0.5, zg_ - 0.5, u + 0.5, v + 0.5, zg_ + 0.2, 'curb')
        # abutments (stone) at both ends
        for v_, sgn in ((V0, -1), (V1, 1)):
            zt_ = zg0
            zbt = min(gz(-2.2, v_), gz(2.2, v_), gz(0, v_), gz(0, v_ - sgn * 0.5)) - 0.4
            prim.box(B, -2.3, min(v_, v_ + sgn * 1.8), zbt, 2.3, max(v_, v_ + sgn * 1.8), zt_, 'stone', c1=(0, 3, 0, 0))
        # ---------------- posts, beams, railings
        rails_w = [(V0, ST_V[0]), (ST_V[1], V1)]
        for v in vs:
            for sg in (-1, 1):
                u = sg * PU
                prim.cyl(B, (u, v, ZB - 0.02), (u, v, ZB + 0.12), 0.21, 0.19, 10, 'stone', tag='detail')
                prim.cyl(B, (u, v, ZB + 0.05), (u, v, ZB + 2.78), 0.135, 0.13, 12, 'wood_dark', caps=(False, True))
            # tie beam (虹梁-like) across, with 木鼻 ends
            prim.obox(B, (-PU - 0.35, v, ZB + 2.5), (PU + 0.35, v, ZB + 2.5), 0.17, 0.3, 'wood_dark')
            prim.obox(B, (-PU - 0.38, v, ZB + 2.5), (-PU - 0.34, v, ZB + 2.5), 0.172, 0.302, 'white_paint', tag='detail')
            prim.obox(B, (PU + 0.34, v, ZB + 2.5), (PU + 0.38, v, ZB + 2.5), 0.172, 0.302, 'white_paint', tag='detail')
            # 束 + 棟木 support
            prim.obox(B, (0, v, ZB + 2.65), (0, v, ZB + 3.85), 0.14, 0.14, 'wood_dark', tag='detail')
        for sg in (-1, 1):
            u = sg * PU
            prim.obox(B, (u, V0 - 0.3, ZB + 2.28), (u, V1 + 0.3, ZB + 2.28), 0.11, 0.2, 'wood_dark')      # 頭貫
            prim.obox(B, (u, V0 - 0.5, ZB + 2.86), (u, V1 + 0.5, ZB + 2.86), 0.2, 0.24, 'wood_dark')      # 桁
        prim.obox(B, (0, V0 - 0.6, ZB + 3.95), (0, V1 + 0.6, ZB + 3.95), 0.2, 0.22, 'wood_dark')          # 棟木
        # railing outside the posts: 地覆, 平桁, round handrail on 束
        def rail(p0, p1, h=0.78):
            p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
            Ln = np.linalg.norm(p1 - p0)
            if Ln < 0.2: return
            prim.obox(B, np.r_[p0, ZB + 0.06], np.r_[p1, ZB + 0.06], 0.12, 0.12, 'wood_dark')
            prim.obox(B, np.r_[p0, ZB + 0.42], np.r_[p1, ZB + 0.42], 0.06, 0.09, 'wood_dark', tag='detail')
            prim.cyl(B, np.r_[p0, ZB + h], np.r_[p1, ZB + h], 0.045, 0.045, 8, 'wood_natural', caps=(True, True), smooth=True)
            for t in np.arange(0.45, Ln - 0.2, 0.9):
                q = p0 + (p1 - p0) * t / Ln
                prim.obox(B, np.r_[q, ZB + 0.1], np.r_[q, ZB + h - 0.03], 0.08, 0.08, 'wood_dark', tag='detail')
                prim.obox(B, np.r_[q, ZB + h - 0.08], np.r_[q, ZB + h - 0.02], 0.12, 0.1, 'wood_dark', tag='detail')
        ur = PU + 0.22
        rail((ur, V0 + 0.1), (ur, V1 - 0.1))
        for (a, b) in rails_w: rail((-ur, a + 0.1 if a == V0 else a), (-ur, b - 0.1 if b == V1 else b))
        rail((-PU - 0.1, ST_V[0] - 0.05), (ST_U - 0.05, ST_V[0] - 0.05)); rail((ST_U - 0.05, ST_V[0] - 0.05), (ST_U - 0.05, ST_V[1] + 0.05))
        rail((ST_U - 0.05, ST_V[1] + 0.05), (-PU - 0.1, ST_V[1] + 0.05))
        # ---------------- the stage frame: corner posts, beams, 蟇股 under the gable beam
        for v in ST_V:
            prim.cyl(B, (ST_U, v, ZB - 0.02), (ST_U, v, ZB + 0.12), 0.23, 0.21, 10, 'stone', tag='detail')
            prim.cyl(B, (ST_U, v, ZB + 0.05), (ST_U, v, ZB + 2.78), 0.15, 0.145, 12, 'wood_dark', caps=(False, True))
            prim.obox(B, (ST_U - 0.35, v, ZB + 2.5), (-PU, v, ZB + 2.5), 0.17, 0.3, 'wood_dark')
        prim.obox(B, (ST_U, ST_V[0] - 0.4, ZB + 2.5), (ST_U, ST_V[1] + 0.4, ZB + 2.5), 0.2, 0.34, 'wood_dark')         # 虹梁 front
        prim.obox(B, (ST_U, ST_V[0] - 0.5, ZB + 2.86), (ST_U, ST_V[1] + 0.5, ZB + 2.86), 0.2, 0.24, 'wood_dark')
        vm = (ST_V[0] + ST_V[1]) / 2
        L.masu(B, (ST_U, vm, ZB + 2.67), 0.34, 'wood_dark')
        # 蟇股: two curved legs
        for sg in (-1, 1):
            pts = np.array([(ST_U, vm + sg * (0.55 - 0.45 * math.sin(t * math.pi / 2)), ZB + 2.67 + 0.3 * t) for t in np.linspace(0, 1, 6)])
            prim.sweep(B, pts, [(-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04)], 'wood_dark', tag='detail', caps=True)
        # ---------------- roofs: main 切妻 along v; stage 切妻 along -u, gable to the west
        with Frame(Bm, 0, 0, 0, math.pi / 2):
            Rm = roof_kirizuma(Bm, V1 - V0, 2 * PU, ZB + 3.05, 1.15, 0.62, 0.75)
        sw = (ST_V[1] - ST_V[0]) / 2
        vo_s = 0.85
        Lst = -ST_U - vo_s                  # the plate: west gable wall on the stage posts, east verge ends at the main ridge
        # stage ridge = main ridge: pick the pitch so that both ridges are level
        c_m = PU + 1.15; zr_m = float(Rm.z(Rm.c, Rm.a))
        c_s = sw + 0.95
        zE_s = float(Rm.zE0)
        H_s = zr_m - zE_s
        with Frame(Bs, (ST_U - vo_s) / 2, vm, 0, math.pi):
            Rs = jroof.Roof(Lst, 2 * sw, 0.0, 0.95, kind='kirizuma', cover='hongawara', pitch=H_s / c_s, verge=vo_s, rafter=0.26,
                            rafter_mat='wood_dark', rafter_end='white_paint', gable_wall='wood_dark', ends=None, sori=0.0, edge=0.3, teri=1.35, tiers=1)
            Rs.zE0 = zE_s; Rs.H = H_s
            Rs.build(Bs)
            # 鬼瓦 at the west end only
            zr_s = float(Rs.z(Rs.c, Rs.a))
            K.ridge_cap(Bs, np.array([(Lst / 2 + vo_s - 0.6, 0, zr_s + 0.06), (Lst / 2 + vo_s, 0, zr_s + 0.06)]), Rs.ridge_w, Rs.ridge_h, ends=(None, 'oni'))
    Zs = K.TriZ(K.tris_of(Bs, mats=('hongawara',)))
    Zm = K.TriZ(K.tris_of(Bm, mats=('hongawara',)))
    K.cull_below(Bm, Zs, mats=('hongawara', 'wood_dark', 'ridge', 'eave_wood', 'white_paint'), eps=0.04)
    K.cull_below(Bs, Zm, mats=('hongawara', 'wood_dark', 'ridge', 'eave_wood', 'white_paint'), eps=0.04)
    K.merge_into(B, Bm); K.merge_into(B, Bs)
    # ---------------- walk / block, lamps
    with loc.frame(B):
        K.walk_poly(B, [(-PU - 0.05, V0 - 0.5), (PU + 0.05, V0 - 0.5), (PU + 0.05, V1 + 0.5), (-PU - 0.05, V1 + 0.5)], ZB)
        K.walk_poly(B, [(ST_U + 0.1, ST_V[0]), (-PU, ST_V[0]), (-PU, ST_V[1]), (ST_U + 0.1, ST_V[1])], ZB)
        K.block_line(B, [(ur, V0), (ur, V1)], w=0.5)
        K.block_line(B, [(-ur, V0), (-ur, ST_V[0] + 0.05)], w=0.5); K.block_line(B, [(-ur, ST_V[1] - 0.05), (-ur, V1)], w=0.5)
        K.block_line(B, [(-PU, ST_V[0] - 0.1), (ST_U - 0.1, ST_V[0] - 0.1), (ST_U - 0.1, ST_V[1] + 0.1), (-PU, ST_V[1] + 0.1)], w=0.5)
        for v in (V0 + 1.0, 0.0, V1 - 1.0):
            prim.cyl(B, (0, v, ZB + 3.6), (0, v, ZB + 3.85), 0.01, 0.01, 4, 'metal_dark', tag='detail')
            arch.chochin(B, 0, v, ZB + 3.05, r=0.16, h=0.45, tag='detail')
    return dict(loc=loc, roof=Rm)

def tsu_world(u, v):
    return tsu_loc().w(u, v)

# ====================================================================== corridors (歩廊)
def corridor(B, S, pts, zs, **kw):
    kw.setdefault('w', 3.1); kw.setdefault('bay', 1.95); kw.setdefault('h', 2.75); kw.setdefault('rise', 1.15); kw.setdefault('o', 1.0)
    kw.setdefault('cover', 'hongawara'); kw.setdefault('floor_mat', 'stone'); kw.setdefault('rail_h', 0.7); kw.setdefault('skirt', False)
    return EK.corridor(B, S, pts, zs, **kw)

def corridors(B, S):
    """south: 通天橋 -> 本堂 (along the OSM way, a branch east to the 方丈 at y -977); north: 通天橋 -> 常楽庵 樓門"""
    loc = tsu_loc()
    out = {}
    # ---- south corridor
    a = np.array(loc.w(0, V0 + 0.05))
    way = L.osm_line(S, 775463879)
    south = [a] + [p for p in way if p[1] < a[1] - 1.0 and p[1] > -1029.0][::-1]
    south = [np.array(p) for p in south]
    south = sorted(south, key=lambda p: -p[1])
    south.append(np.array([south[-1][0] - 0.05, -1028.5]))
    sp = np.array(south)
    zg = S.ground(sp[:, 0], sp[:, 1])
    zs = np.maximum.accumulate(np.maximum(zg + 0.2, ZB))
    zs[0] = ZB
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sp, axis=0), axis=1))]
    t_br = float(np.interp(-977.2, sp[::-1, 1], seg[::-1]))
    t_x = float(np.interp(-1015.0, sp[::-1, 1], seg[::-1]))
    out['south'] = corridor(B, S, sp, zs, rail_gaps=[(1, t_br - 1.6, t_br + 1.6), (1, t_x - 1.5, t_x + 1.5), (-1, t_x - 1.5, t_x + 1.5)],
                            end_gables=(True, True), seed=3)
    # branch to the 方丈 (西唐門)
    b0 = np.array([sp[0][0], -977.2]); b0[0] = float(np.interp(-977.2, sp[::-1, 1], sp[::-1, 0])) + 1.6
    b1 = np.array([1365.6, -977.45])
    zb0 = float(np.interp(-977.2, sp[::-1, 1], zs[::-1]))
    out['branch'] = corridor(B, S, [b0, b1], [zb0, zb0 + 0.1], w=2.6, rail=True, end_gables=(False, True))
    # ---- north corridor: bridge end -> north -> east -> covered stairs to the 樓門
    n0 = np.array(loc.w(0, V1 - 0.05))
    n1 = np.array([1360.55, -895.6])
    npts = [n0] + [np.array(p) for p in way if a[1] < p[1] < n1[1] - 0.5 and p[1] > n0[1] + 0.5 and p[0] > 1358.0] + [n1]
    npts = np.array(sorted(npts, key=lambda p: p[1]))
    zg = S.ground(npts[:, 0], npts[:, 1])
    zn = np.maximum.accumulate(np.maximum(zg + 0.25, ZB)); zn[0] = ZB
    out['north'] = corridor(B, S, npts, zn, end_gables=(True, True), seed=5,
                            rail_gaps=[(-1, float(np.sum(np.linalg.norm(np.diff(npts, axis=0), axis=1))) - 3.4, 99.0), (1, 1.0, 3.2)])
    e0 = np.array([1361.4, -897.0]); e1 = np.array([1383.4, -897.7])
    zE0 = float(zn[-1]); zE1 = float(S.ground(*e1)) + 0.25
    xs = np.linspace(0, 1, 6)
    epts = np.array([e0 + (e1 - e0) * t for t in xs])
    ze = np.maximum.accumulate(np.maximum(S.ground(epts[:, 0], epts[:, 1]) + 0.25, zE0))
    out['east'] = corridor(B, S, epts, ze, end_gables=(True, False), seed=7, rail_gaps=[(-1, -1, 2.5), (1, float(np.linalg.norm(e1 - e0)) - 2.2, 99.0)])
    s0 = np.array([1383.55, -898.9]); s1 = np.array([1385.85, -885.2])          # up to the 樓門's platform
    zs0 = float(ze[-1]); zs1 = 53.87
    out['stairs'] = corridor(B, S, [s0, s1], [zs0, zs1], end_gables=(False, True), seed=9, smooth=0.8, rail_gaps=[(1, -1.0, 2.2)])
    # steps from the north corridor's west side down to the valley path
    q = np.array(loc.w(-PU - 0.2, V1 + 1.6)); q2 = np.array(loc.w(-PU - 4.6, V1 + 1.6))
    EK.terrain_steps(B, S, [q, q2], 1.4, z0=ZB, z1=float(S.ground(*q2)) + 0.05, rail=None, curb=True)
    return out

# ====================================================================== 通天台 (the viewing platform north of the 方丈)
def tsutendai(B, S, zf=50.7):
    """the 通天台: a roofed platform on posts north of the 方丈, reached from its north veranda"""
    loc = L.Loc(1383.0, -957.0, L.ROT)
    with loc.frame(B):
        u0, u1, v0, vm, v1 = -2.6, 2.6, -3.6, 0.6, 7.0
        rng = np.random.default_rng(8)
        for v in np.arange(v0, v1 - 1e-6, 0.3):
            prim.box(B, u0, v + 0.005, zf - 0.07, u1, min(v + 0.3, v1) - 0.005, zf, 'wood_natural', faces='Zy', c1=(0, 0, int(rng.integers(255)), 0))
        prim.box(B, u0, v0, zf - 0.32, u1, v1, zf - 0.07, 'wood_dark', faces='xXyYz')
        for u in (u0 + 0.15, 0.0, u1 - 0.15):
            for v in np.linspace(v0 + 1.2, v1 - 0.15, 4):
                zg = loc.g(S, u, v)
                if zf - zg < 0.4: continue
                prim.cyl(B, (u, v, zg - 0.3), (u, v, zf - 0.3), 0.14, 0.14, 8, 'wood_dark')
                prim.box(B, u - 0.3, v - 0.3, zg - 0.3, u + 0.3, v + 0.3, zg + 0.15, 'stone')
                if zf - zg > 2.5:
                    prim.obox(B, (u0, v, (zg + zf) / 2), (u1, v, (zg + zf) / 2), 0.1, 0.18, 'wood_dark', tag='detail')
        posts = [(u0 + 0.15, v) for v in (v0 + 0.3, vm, v1 - 0.15)] + [(u1 - 0.15, v) for v in (v0 + 0.3, vm, v1 - 0.15)]
        for (u, v) in posts:
            prim.cyl(B, (u, v, zf), (u, v, zf + 2.6), 0.13, 0.12, 12, 'wood_dark')
        for v in (v0 + 0.3, vm, v1 - 0.15):
            prim.obox(B, (u0 - 0.3, v, zf + 2.45), (u1 + 0.3, v, zf + 2.45), 0.17, 0.28, 'wood_dark')
        for u in (u0 + 0.15, u1 - 0.15):
            prim.obox(B, (u, v0 - 0.3, zf + 2.6), (u, v1 + 0.3, zf + 2.6), 0.18, 0.22, 'wood_dark')
        # bamboo-topped railing round the platform
        for (p0, p1) in (((u0 + 0.1, vm), (u0 + 0.1, v1 - 0.1)), ((u0 + 0.1, v1 - 0.1), (u1 - 0.1, v1 - 0.1)), ((u1 - 0.1, v1 - 0.1), (u1 - 0.1, vm)),
                         ((u0 + 0.1, v0 + 0.3), (u0 + 0.1, vm)), ((u1 - 0.1, vm), (u1 - 0.1, v0 + 0.3))):
            p0 = np.array(p0); p1 = np.array(p1)
            prim.cyl(B, np.r_[p0, zf + 0.75], np.r_[p1, zf + 0.75], 0.045, 0.045, 8, 'bamboo')
            prim.obox(B, np.r_[p0, zf + 0.4], np.r_[p1, zf + 0.4], 0.06, 0.1, 'wood_dark', tag='detail')
            prim.obox(B, np.r_[p0, zf + 0.06], np.r_[p1, zf + 0.06], 0.12, 0.12, 'wood_dark')
            Ln = np.linalg.norm(p1 - p0)
            for t in np.arange(0.9, Ln - 0.3, 0.9):
                q = p0 + (p1 - p0) * t / Ln
                prim.obox(B, np.r_[q, zf], np.r_[q, zf + 0.72], 0.1, 0.1, 'wood_dark', tag='detail')
        with Frame(B, 0, (v0 + v1) / 2, 0, math.pi / 2):
            roof_kirizuma(B, v1 - v0 - 0.4, u1 - u0 - 0.3, zf + 3.0, 0.9, 0.62, 0.7)
        K.walk_poly(B, [(u0 + 0.2, v0 - 0.4), (u1 - 0.2, v0 - 0.4), (u1 - 0.2, v1 - 0.25), (u0 + 0.2, v1 - 0.25)], zf)
        K.block_line(B, [(u0 + 0.1, v0), (u0 + 0.1, v1 - 0.1), (u1 - 0.1, v1 - 0.1), (u1 - 0.1, v0)], w=0.4)

# ====================================================================== 臥雲橋 / 偃月橋 (covered timber bridges)
def covered_bridge(B, S, a, b, za, zb, *, w=2.6, camber=0.3, bay=2.0, h=2.45, o=0.95, pitch=0.66, cover='sangawara', valley=None,
                   bents=(0.28, 0.72), braces=True, end_ext=(0.0, 0.0), gable_wall='wood_dark'):
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; Lb = float(np.linalg.norm(d)); d /= Lb
    yaw = math.atan2(d[1], d[0]) - math.pi / 2          # local v along the bridge
    c = (a + b) / 2
    loc = L.Loc(c[0], c[1], yaw)
    zc = lambda v: za + (zb - za) * (v / Lb + 0.5) + camber * (1 - (2 * v / Lb) ** 2)
    hw = w / 2
    gz = (lambda u, v: float(valley.zfn(*loc.w(u, v)))) if valley is not None else (lambda u, v: loc.g(S, u, v))
    v0, v1 = -Lb / 2 - end_ext[0], Lb / 2 + end_ext[1]
    nb = max(2, int(round((v1 - v0) / bay)))
    vs = np.linspace(v0, v1, nb + 1)
    rng = np.random.default_rng(int(c[0]))
    with loc.frame(B):
        # deck: boards across (along u), a curved surface
        fv = np.linspace(v0, v1, max(8, int((v1 - v0) / 0.6)) + 1)
        top = []; bot = []
        for v in fv:
            z = zc(v)
            top.append([(-hw - 0.15, v, z), (hw + 0.15, v, z)])
        T = np.array(top).reshape(-1, 3); I = []
        for i in range(len(fv) - 1):
            k = 2 * i; I += [[k, k + 1, k + 3], [k, k + 3, k + 2]]
        L.oadd(B, T, I, 'wood_natural', (0, 0, 1), UV=T[:, [0, 1]])
        Tb = T - [0, 0, 0.12]; L.oadd(B, Tb, I, 'wood_dark', (0, 0, -1))
        for sg in (-1, 1):
            E = np.array([(sg * (hw + 0.15), v, zc(v)) for v in fv])
            prim.sweep(B, E - [0, 0, 0.25], [(-0.1, -0.3), (0.1, -0.3), (0.1, 0.27), (-0.1, 0.27)], 'wood_dark', caps=True)
            # main timber girders
            prim.sweep(B, np.array([(sg * (hw - 0.3), v, zc(v) - 0.12) for v in fv]), [(-0.16, -0.5), (0.16, -0.5), (0.16, 0.0), (-0.16, 0.0)], 'wood_dark', caps=True)
        # posts, tie beams, knee braces, railing (the post tops and the roof follow a straight line)
        slope = (zb - za) / Lb
        ztop = lambda v: za + (zb - za) * (v / Lb + 0.5) + camber + h
        for v in vs:
            for sg in (-1, 1):
                u = sg * hw
                prim.box(B, u - 0.1, v - 0.1, zc(v) - 0.05, u + 0.1, v + 0.1, ztop(v), 'wood_dark')
                if braces:
                    prim.obox(B, (u, v, zc(v) + 0.95), (u + sg * 0.75, v, ztop(v) - 0.05), 0.09, 0.12, 'wood_dark', tag='detail')
            prim.obox(B, (-hw - 0.3, v, ztop(v) - 0.12), (hw + 0.3, v, ztop(v) - 0.12), 0.14, 0.26, 'wood_dark')
        for sg in (-1, 1):
            u = sg * hw
            prim.sweep(B, np.array([(u, v, ztop(v) + 0.1) for v in fv]), [(-0.1, -0.12), (0.1, -0.12), (0.1, 0.12), (-0.1, 0.12)], 'wood_dark', caps=True)
            prim.sweep(B, np.array([(u + sg * 0.75, v, ztop(v)) for v in fv]), [(-0.08, -0.1), (0.08, -0.1), (0.08, 0.1), (-0.08, 0.1)], 'wood_dark', caps=True)
            for zz, ww in ((0.72, 0.09), (0.4, 0.07)):
                prim.sweep(B, np.array([(u, v, zc(v) + zz) for v in fv]), [(-ww / 2, -0.05), (ww / 2, -0.05), (ww / 2, 0.05), (-ww / 2, 0.05)], 'wood_dark', tag='detail')
            for v in np.arange(v0 + 0.5, v1, 0.5):
                prim.obox(B, (u, v, zc(v) + 0.02), (u, v, zc(v) + 0.7), 0.05, 0.05, 'wood_dark', tag='detail')
        # roof: 切妻 following the (small) camber with a straight ridge (the kit roof is level)
        zr = ztop(0.0) + 0.32
        Bt = jk.Builder('cb_roof')
        with Frame(Bt, 0, (v0 + v1) / 2, 0, math.pi / 2):
            R = roof_kirizuma(Bt, v1 - v0, w, zr, o, pitch, 0.7, cover=cover, gable_wall=gable_wall)
        for p in Bt.parts:
            P = p['P'].astype(np.float64); P[:, 2] += slope * P[:, 1]
            B.add(P, p['I'], p['mat'], UV=p['UV'], N=p['N'], tag=p['tag'], c0=p['c0'], c1=p['c1'])
        # bents under the deck (timber posts on stone footings, cross-braced)
        for t in bents:
            v = v0 + (v1 - v0) * t
            zt = zc(v) - 0.62
            zgs = [gz(sg * (hw - 0.3), v) for sg in (-1, 1)]
            for sg, zg_ in zip((-1, 1), zgs):
                u = sg * (hw - 0.3)
                prim.box(B, u - 0.45, v - 0.45, zg_ - 0.4, u + 0.45, v + 0.45, zg_ + 0.35, 'stone')
                prim.box(B, u - 0.15, v - 0.15, zg_ + 0.3, u + 0.15, v + 0.15, zt, 'wood_dark')
            prim.obox(B, (-hw, v, zt - 0.1), (hw, v, zt - 0.1), 0.2, 0.25, 'wood_dark')
            zl = max(zgs) + 0.6
            if zt - zl > 1.5:
                prim.obox(B, (-(hw - 0.3), v, zl), ((hw - 0.3), v, zt - 0.3), 0.1, 0.14, 'wood_dark', tag='detail')
                prim.obox(B, ((hw - 0.3), v, zl), (-(hw - 0.3), v, zt - 0.3), 0.1, 0.14, 'wood_dark', tag='detail')
                prim.obox(B, (-hw, v, (zl + zt) / 2), (hw, v, (zl + zt) / 2), 0.1, 0.16, 'wood_dark', tag='detail')
        # stone abutments at the ends
        for (v, s) in ((v0, -1), (v1, 1)):
            zt = zc(v) - 0.25
            zbt = min(gz(-hw - 0.4, v), gz(hw + 0.4, v)) - 0.5
            prim.box(B, -hw - 0.5, min(v, v + s * 1.2), min(zbt, zt - 0.5), hw + 0.5, max(v, v + s * 1.2), zt, 'stone', c1=(0, 3, 0, 0))
        # walk + block
        W = np.array([(0, v, zc(v)) for v in fv])
        EK.ribbon(B, W, w - 0.25, 'walk')
        for sg in (-1, 1):
            EK.ribbon(B, np.array([(sg * (hw + 0.05), v, 0.0) for v in fv]), 0.45, 'block')
    return dict(loc=loc, zc=zc, R=R)

def gaunkyo(B, S, valley):
    """臥雲橋 (府指定): the west lane's covered bridge, 21 m; the classic view of the 通天橋 from its railing"""
    a = (1285.55, -933.4); b = (1287.85, -911.4)
    za = float(S.ground(*a)) + 0.15; zb = float(S.ground(*b)) + 0.15
    return covered_bridge(B, S, a, b, za, zb, w=2.7, camber=0.35, bay=2.2, h=2.5, o=0.95, pitch=0.7, cover='sangawara', valley=valley, bents=(0.3, 0.7))

def engetsukyo(B, S, valley):
    """偃月橋 (重文, 1603): 単層切妻造桟瓦葺 timber bridge corridor from the 庫裏 side to 龍吟庵 / 即宗院"""
    a = (1459.65, -988.4); b = (1461.75, -967.6)
    za = float(S.ground(*a)) + 0.12
    zb = za - 0.25
    return covered_bridge(B, S, a, b, za, zb, w=2.3, camber=0.25, bay=1.9, h=2.35, o=0.85, pitch=0.78, cover='sangawara', valley=valley, bents=(0.35, 0.68))
