"""金閣寺 (鹿苑寺 Rokuon-ji, Kita-ku) — the hero site.

Garden frame: origin = the 舎利殿's plan centre (OSM 3D parts), axes = world (x east, y north), z absolute (T.P.).
Parts (run_site --only accepts these names): kinkaku, pond, anmin, halls, gates, garden, hill, trees.
  kinkakuji_kinkaku.py  舎利殿 (金閣) + 漱清 + 鳳凰
  kinkakuji_pond.py     own ground / basin / islands / water / shore stones (鏡湖池, 安民沢)
  kinkakuji_halls.py    方丈, 庫裏, 書院, 総門, 唐門, 鐘楼, 不動堂, 夕佳亭, support buildings, walls
  kinkakuji_garden.py   龍門滝 + 鯉魚石, 銀河泉, 巌下水, 白蛇の塚, fences, steps, lanterns, paths
References: /home/kazu/work/kyoto-assets/refs/kinkakuji (dossier.md, manifest.json, photos)."""
import math, os
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
import jk
from jk import prim, Frame
from . import kinkakuji_kinkaku as KK
from . import kinkakuji_pond as PD
from . import kinkakuji_util as U
from . import kinkakuji_halls as HL
from . import kinkakuji_garden as GD

KX, KY = -2768.85, 5959.0                 # the 舎利殿's plan centre (OSM 3D parts)
KYAW = math.radians(-2.4)
WL = 95.45                                # 鏡湖池 water level (DEM shore ~95.6, banks ~95.7)
Z_BASE = WL + 0.5                         # top of the Kinkaku's stone base
WL2 = 100.75                              # 安民沢
def W(x, y, z): return (x + KX, y + KY, z)
def L2W(p): return [float(p[0] + KX), float(p[1] + KY)]

SHOTS = [('kinkaku_pond', W(30.4, -57.2, 97.45), W(-1.4, -6.3, 99.6), 34),         # the classic view from the south-shore viewpoint
         ('kinkaku_east', W(19.5, 2.8, 97.45), W(0, -0.5, 100.6), 26),           # close-up from the viewpoint east of the Kinkaku
         ('islands', W(17.0, -46.0, 97.3), W(-20, -28, 96.2), 30),               # 葦原島 and the rock islets
         ('sekkatei', W(66.0, 60.0, 105.4), W(75.5, 70.5, 105.6), 30),           # 夕佳亭 from the path below it
         ('somon', W(163.0, -52.0, 97.75), W(146.0, -50.3, 99.0), 32),           # 総門 from the forecourt
         ('aerial', W(130, -175, 200), W(20, 0, 100), 30)]
SHOTS_DEV = [('dev_kuri', W(97, -52, 97.8), W(82, -27, 101.5), 30), ('dev_karamon', W(70.5, -52.5, 97.6), W(70.2, -38.4, 99.2), 30),
             ('dev_shoro', W(100, -50, 97.8), W(107.9, -59.8, 99.5), 30), ('dev_fudodo', W(135.5, 83.0, 105.7), W(150.1, 77.1, 106.6), 30),
             ('dev_hojo', W(40, -45, 96.9), W(60, -18, 99.5), 30), ('dev_ryumon', W(10, 45, 98.0), W(14.5, 54.0, 97.8), 30),
             ('dev_anmin', W(42, 68, 103.9), W(46, 98, 101.0), 30), ('dev_cmp_vp', W(30.4, -57.2, 97.3), W(-0.8, 0, 101.5), 85), ('dev_cmp_se', W(26.0, -24.0, 96.8), W(0, 0, 100.3), 40), ('dev_sekka_hi', W(60, 55, 112), W(74, 70, 104.5), 30), ('dev_sekka_n', W(72, 85, 106.5), W(74, 70, 105.2), 30), ('dev_kk_sw', W(-16, -18, 97.0), W(0, 0, 100.5), 30), ('dev_kk_nw', W(-14, 16, 97.6), W(0, 0, 100.0), 30),
             ('dev_kk_top', W(9, -11, 104.5), W(0, 0, 104.0), 32), ('dev_kk_s', W(4, -30, 97.0), W(0, 0, 100.6), 40)]
SHOTS_ALL = list(SHOTS)
if os.environ.get('KK_DEV'): SHOTS = SHOTS + SHOTS_DEV
if os.environ.get('KK_SHOTS'):
    SHOTS = [s for s in SHOTS + SHOTS_DEV if s[0] in os.environ['KK_SHOTS'].split(',')]

# ------------------------------------------------------------------ OSM helpers (garden-local)
def osm_line(S, cat, wid):
    for w in S.osm[cat]:
        if w['id'] == wid:
            L = w.get('line') or w.get('poly')
            while isinstance(L[0][0], list): L = L[0]
            return np.array(L, float) - [KX, KY]
    return None

def osm_ring(S, wid):
    for b in S.osm['buildings']:
        if b['id'] == wid:
            L = b['poly']
            while isinstance(L[0][0], list): L = L[0]
            return [(x - KX, y - KY) for (x, y) in L]
    return None

def osm_point(S, pid):
    for p in S.osm['points']:
        if p['id'] == pid: return np.array(p['xy'], float) - [KX, KY]
    return None

def wring(poly):
    return [L2W(p) for p in list(poly.exterior.coords)[:-1]]

def krect(u0, v0, u1, v1, yaw=KYAW):
    """a rectangle in the Kinkaku's rotated frame -> garden-local polygon"""
    c, s = math.cos(yaw), math.sin(yaw)
    return Polygon([(u * c - v * s, u * s + v * c) for (u, v) in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])

# ------------------------------------------------------------------ the ponds
def kyoko_pond(S, gz):
    R = PD.osm_rings(S, -1407006, KX, KY)
    outer = Polygon(PD.chaikin(R[0], 2)).buffer(0)
    isl = [Polygon(PD.chaikin(r, 2)).buffer(0.1) for r in R[1:]]
    base = krect(-KK.A1 - 1.2, -KK.C1 - 1.1, KK.A1 + 1.2, KK.C1 + 1.0)
    # the water reaches the Kinkaku's base on the south and the west (under the 漱清)
    extra = unary_union([krect(-10.4, -7.2, KK.A1 + 1.2, -KK.C1 - 1.1), krect(-10.4, -7.2, -KK.A1 - 1.2, 1.7)])
    outer = unary_union([outer, extra]).buffer(0.3).buffer(-0.3).difference(base)
    outer = max(PD.polys(outer), key=lambda p: p.area)
    outer = Polygon(outer.exterior)
    # rock islets OSM lacks: the one with two pines off the south-shore viewpoint, two more to the east
    rng = np.random.default_rng(31)
    def blob(cx, cy, r, k=9, ax=1.0):
        a = np.linspace(0, 2 * math.pi, k, endpoint=False) + rng.uniform(0, 1)
        rr = r * rng.uniform(0.75, 1.2, k)
        return Polygon(PD.chaikin(np.c_[cx + rr * np.cos(a) * ax, cy + rr * np.sin(a)], 2))
    isl += [blob(22.4, -49.0, 2.3, ax=1.35), blob(27.0, -29.5, 1.5), blob(-20.0, -53.0, 1.7, ax=1.2)]
    flat = [(base.buffer(0.2), Z_BASE - 0.04, 2.2)]
    P = PD.Pond(gz, outer, isl, WL, band=4.5, bank_min=0.28, depth=0.7, flat=flat, seed=3)
    P.base = base
    return P

def anmin_pond(S, gz):
    R = PD.osm_rings(S, -7897070, KX, KY)
    outer = Polygon(PD.chaikin(R[0], 2)).buffer(0)
    isl = [Polygon(PD.chaikin(r, 2)).buffer(0.05) for r in R[1:]]
    return PD.Pond(gz, outer, isl, WL2, band=3.5, bank_min=0.3, depth=0.5, isl_h=0.45, seed=5, smooth_m=4.0)

# ------------------------------------------------------------------ preview-only helpers (nothing reaches the npz)
def preview_patch(S, ponds, gz):
    """run_site draws the raw DEM as context terrain: push it under our own ground where we model it (S.cut), light the
    shots from the south-east, cull back faces like the viewer"""
    cut = unary_union([Polygon(r) for r in S.cut]) if S.cut else None
    def hf(x, y):
        for p in ponds:
            if p.region.buffer(2.5).contains(Point(x - KX, y - KY)): return float(p.h(x - KX, y - KY)[0])
        return float(gz(x - KX, y - KY))
    orig = jk.to_objects
    def to_objects(b, *a, **k):
        if b.name == 'terrain' and cut is not None:
            cb = cut.buffer(3.0); shapely.prepare(cb); shapely.prepare(cut)
            for p in b.parts:
                C = p['P'][p['I']].mean(1)
                p['I'] = p['I'][~shapely.contains_xy(cut, C[:, 0], C[:, 1])]
                inside = shapely.contains_xy(cb, p['P'][:, 0], p['P'][:, 1])
                for i in np.where(inside)[0]:
                    p['P'][i, 2] = min(p['P'][i, 2], hf(p['P'][i, 0], p['P'][i, 1]) - 0.15)
        objs = orig(b, *a, **k)
        try:
            import bpy
            for m in bpy.data.materials:
                if m.name.startswith('jk_'): m.use_backface_culling = True
        except Exception:
            pass
        return objs
    jk.to_objects = to_objects
    try:
        import render_scene as R
        so = R.setup
        def setup(res=(1600, 900), engine='EEVEE', sun=(150, 38), strength=3.2, sky=(0.42, 0.5, 0.64)):
            return so(res=res, engine=engine, sun=sun, strength=strength, sky=sky)
        R.setup = setup
    except Exception as e:
        print('preview patch: no render_scene', e)

def tree_proxies(trees):
    """simple stand-ins for the viewer's trees so the previews show the planting (Blender collection 'preview_trees')"""
    try:
        import bpy
    except Exception:
        return
    tb = jk.Builder('preview_trees')
    names = jk.Builder.TREE_SPECIES
    for (si, x, y, z, s, yaw) in trees:
        sp = names[int(si)]
        H = {'momiji': 7.5, 'ichou': 16, 'sakura': 9, 'keyaki': 18, 'matsu': 9.5, 'sugi': 26, 'hinoki': 20, 'kashi': 13, 'yanagi': 9.5, 'tsutsuji': 1.3, 'take': 13}[sp] * s
        if sp == 'tsutsuji':
            prim.lathe(tb, (x, y, z), [(0.0, 0.0), (0.7 * s, 0.1 * H), (0.75 * s, 0.6 * H), (0.4 * s, H), (0.0, H)], 8, 'hedge', smooth=True)
            continue
        prim.cyl(tb, (x, y, z), (x, y, z + H * 0.6), 0.05 * H ** 0.8 * 0.4, 0.03 * H ** 0.8 * 0.4, 6, 'wood_dark')
        if sp in ('sugi', 'hinoki'):
            prim.lathe(tb, (x, y, z + H * 0.25), [(0.0, 0.0), (H * 0.17, 0.05 * H), (H * 0.1, 0.45 * H), (0.0, 0.75 * H)], 8, 'hedge', smooth=True)
        elif sp == 'matsu':
            rng = np.random.default_rng(int(abs(x) * 10 + abs(y)))
            for k in range(4):
                a = rng.uniform(0, 6.28); r = H * rng.uniform(0.1, 0.3); zz = z + H * (0.45 + 0.13 * k)
                rr = H * (0.28 - 0.04 * k)
                prim.lathe(tb, (x + r * math.cos(a), y + r * math.sin(a), zz), [(0.0, 0.0), (rr, 0.05 * H), (rr * 0.8, 0.12 * H), (0.0, 0.15 * H)], 8, 'hedge', smooth=True)
        else:
            rr = H * (0.36 if sp == 'momiji' else 0.3)
            prim.lathe(tb, (x, y, z + H * 0.35), [(0.0, 0.0), (rr * 0.8, 0.12 * H), (rr, 0.35 * H), (rr * 0.7, 0.58 * H), (0.0, 0.66 * H)], 8, 'hedge', smooth=True)
    col = bpy.data.collections.new('preview_trees'); bpy.context.scene.collection.children.link(col)
    jk.to_objects(tb, collection=col, tags=('main',))

# ------------------------------------------------------------------ paths, surfaces
MAIN = {1550559957, 552862318, 347463884, 552862316, 345435641, 1550559958, 346872606, 346872607, 345435754, 552862319, 105506007}
WIDE = {54371188: 5.0}
STEPS = {347463888, 347463885, 347786578, 345435640, 347407425, 347786580, 347786582, 190896387, 347463887}
BRIDGE_SOMON = 552862320

def site_paths(S, core):
    """(way, local polyline, width, kind) of the footways / paths / steps in the modelled core"""
    out = []
    for w in S.osm['ways']:
        hw = w['tags'].get('highway')
        if hw not in ('footway', 'path', 'steps', 'pedestrian'): continue
        if w['tags'].get('footway') in ('sidewalk', 'crossing'): continue
        a = osm_line(S, 'ways', w['id'])
        if a is None or len(a) < 2 or not core.buffer(3).intersects(LineString(a)): continue
        wd = WIDE.get(w['id'], 3.2 if w['id'] in MAIN else 2.0 if hw == 'steps' else 1.7)
        out.append((w, a, wd, 'steps' if hw == 'steps' else 'path'))
    return out

class Terraces:
    """levelled ground under buildings on slopes: zt inside each polygon, blended to the DEM over `margin`"""
    def __init__(self, gz, items):
        self.gz = gz; self.items = items                      # [(poly, zt, margin)]
        self.region = unary_union([p.buffer(m) for (p, z, m) in items]) if items else None
    def h(self, x, y):
        x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
        z = np.asarray(self.gz(x, y), float).copy()
        pts = shapely.points(x, y)
        for (p, zt, m) in self.items:
            d = shapely.distance(p, pts)
            k = np.clip(1 - d / m, 0, 1); w = k * k * (3 - 2 * k)
            z = z * (1 - w) + zt * w
        return z

# ------------------------------------------------------------------ the site
def build(B, S, only=None):
    want = lambda k: (not only) or (k in only)
    gz = lambda x, y: S.ground(np.asarray(x) + KX, np.asarray(y) + KY)
    # ---- the modelled core: the precinct west of the shops / parking, north of the southern woods' edge
    prec = S.polygon
    while isinstance(prec[0][0][0], list): prec = prec[0]
    prec = prec[0] if isinstance(prec[0][0], list) else prec
    P_prec = Polygon(np.array(prec) - [KX, KY]).buffer(0)
    core = P_prec.intersection(box(-200, -110, 165.85, 250)).buffer(0)
    S.exclude.append(wring(max(PD.polys(core), key=lambda p: p.area)))
    # ---- ponds, terraces
    P1 = kyoko_pond(S, gz)
    P2 = anmin_pond(S, gz)
    print(f'kinkakuji: 鏡湖池 {P1.water.area:.0f} m2, {len(P1.islands)} islands; 安民沢 {P2.water.area:.0f} m2')
    ring = lambda wid: osm_ring(S, wid)
    terr = {}; titems = []
    for wid, pct, fpad in ((337340500, 10, (0, 0)), (180453976, 30, (0, 0)), (180453978, 35, (0, 0)), (180453977, 40, (0, 0)), (188772158, 40, (0, 0)),
                           (345464006, 35, (0, 0)), (345443495, 30, (0, 0)), (345432675, 40, (0, 0)), (188772173, 40, (0, 0))):
        r = ring(wid)
        if r is None: continue
        poly = Polygon(r).buffer(1.2, join_style=2)
        X, Y = np.meshgrid(np.linspace(poly.bounds[0], poly.bounds[2], 12), np.linspace(poly.bounds[1], poly.bounds[3], 12))
        m = shapely.contains_xy(poly, X, Y)
        zt = float(np.percentile(gz(X[m], Y[m]), pct))
        terr[wid] = zt + 0.02
        titems.append((poly, zt + 0.02, 3.0))
    # the 不動堂's stone forecourt: extend its terrace to the front (south-south-east)
    c = Polygon([(146.52, 85.13), (158.11, 80.87), (153.75, 69.12), (142.16, 73.4)]).centroid; f = np.array([math.cos(math.radians(159.6)), math.sin(math.radians(159.6))])
    fc = Polygon([np.array([c.x, c.y]) + f * 6.0 + np.array([-f[1], f[0]]) * s_ for s_ in (-7.5, 7.5)] + [np.array([c.x, c.y]) + f * 15 + np.array([-f[1], f[0]]) * s_ for s_ in (7.5, -7.5)])
    titems.append((fc.buffer(0), terr[337340500], 2.5))
    T = Terraces(gz, titems)
    # ---- paths and surfaces (painted on the generic ground, and used by our own meshes)
    ways = site_paths(S, core)
    layers = []
    def L_(poly, surf): layers.append((poly, surf))
    L_(core, 'moss')
    L_(core.intersection(box(-200, 22, 170, 250)).difference(box(40, 0, 100, 40)), 'forest')
    L_(core.intersection(box(-200, -130, 170, -78)), 'forest')
    L_(Polygon([(44, -50), (100, -50), (100, -27), (73, -27), (72, -9), (44, -9)]), 'gravel')          # the 方丈 / 唐門 / 庫裏 front
    L_(box(96, -45, 166, -27).union(box(73, 0, 100, 36)), 'gravel')
    for (w, a, wd, kind) in ways:
        L_(LineString(a).buffer(wd / 2, cap_style=2 if kind == 'steps' else 1), 'stone_slab' if kind == 'steps' else 'gravel')
    L_(Polygon([(140.6, -49.0), (166, -52), (166, -47), (141, -46.5)]).buffer(1.0), 'stone_sett')     # the approach to the 総門
    L_(fc, 'stone_slab')
    for (poly, zt, m) in titems[:-1]: L_(poly, 'gravel')
    for (poly, surf) in layers:
        for g in PD.polys(poly.buffer(0)):
            if g.area > 0.3: S.paint.append({'poly': wring(g), 'surf': surf})
    prep = [(g, PD.SID[s_]) for (g, s_) in layers]
    for (g, _) in prep: shapely.prepare(g)
    def surf_at(x, y, water=None):
        out = np.full(len(x), PD.SID['moss'])
        for (g, sid) in prep:
            out[shapely.contains_xy(g, x, y)] = sid
        if water is not None: out[shapely.contains_xy(water, x, y)] = PD.SID['riverbed']
        return out
    # ---- our own ground: the ponds' basins + banks, the terraces
    for p in (P1, P2): S.cut.append(wring(p.region))
    t_region = T.region.difference(P1.region).difference(P2.region).buffer(0)
    for g in PD.polys(t_region):
        if g.area > 1: S.cut.append(wring(Polygon(g.exterior)))
    # the 総門's ditch: a stone-lined channel under the slab bridge
    ditch = osm_line(S, 'waterways', 346872603)
    D_ch = LineString(ditch).buffer(0.85, cap_style=2) if ditch is not None else None
    D_reg = LineString(ditch).buffer(2.6, cap_style=2) if ditch is not None else None
    if D_reg is not None: S.cut.append(wring(D_reg))
    trees = []
    with Frame(B, KX, KY, 0.0, 0.0):
        if want('kinkaku'):
            KK.build(B, S, 0.0, 0.0, Z_BASE, KYAW)
        if want('pond'):
            PD.mesh_region(B, P1.region, P1.h, 0.6, surf_of=lambda x, y: surf_at(x, y, P1.water), walk_of=lambda x, y: ~shapely.contains_xy(P1.water.buffer(0.3), x, y))
            PD.water(B, P1)
            n = PD.shore_stones(B, P1, seed=7, skip=P1.base.buffer(0.6), gap=(1.6, 5.0), run=(2.5, 8))
            stones_kyoko(B, P1)
            print(f'kinkakuji: {n} shore stones')
        if want('anmin'):
            PD.mesh_region(B, P2.region, P2.h, 0.6, surf_of=lambda x, y: surf_at(x, y, P2.water), walk_of=lambda x, y: ~shapely.contains_xy(P2.water.buffer(0.3), x, y))
            PD.water(B, P2)
            PD.shore_stones(B, P2, seed=11, gap=(2.5, 6.0), run=(1.5, 5), mossy=0.5)
            isl = max(P2.islands, key=lambda i: i.area)
            hp = osm_point(S, 3525976647)
            q = hp if (hp is not None and isl.contains(Point(hp))) else np.array(isl.centroid.coords[0])
            GD.hakuja(B, q[0], q[1], float(P2.h(*q)[0]) + 0.05)
        if want('halls'):
            for g in PD.polys(t_region):
                if g.area > 1: PD.mesh_region(B, Polygon(g.exterior), T.h, 0.7, surf_of=lambda x, y: surf_at(x, y), walk_of=lambda x, y: np.ones(len(x), bool))
            HL.build(B, S, lambda x, y: float(T.h(x, y)[0]) if T.region.contains(Point(x, y)) else float(gz(x, y)), ring, lambda cat, wid: osm_line(S, cat, wid), terr)
        if want('garden'):
            build_garden(B, S, gz, T, P1, P2, ways)
            if D_reg is not None: somon_ditch(B, gz, ditch, D_reg, D_ch, surf_at)
        if want('trees'): trees = plant(B, S, P1, P2, T, gz, core, ways, P_prec)
    print(f'kinkakuji: {len(B.trees)} trees, {len(B.lamps)} lamps')
    preview_patch(S, (P1, P2, T), gz)
    tree_proxies(B.trees)

def somon_ditch(B, gz, line, reg, ch, surf_at, depth=1.1):
    """ground round the ditch, the channel's stone walls and bed, a little water"""
    PD.mesh_region(B, reg.difference(ch), lambda x, y: np.asarray(gz(x, y), float), 0.5, surf_of=lambda x, y: surf_at(x, y), walk_of=lambda x, y: np.ones(len(x), bool))
    p, _ = U.resample(line, 0.8)
    N, Tg = U.normals2(p)
    z = np.array([float(gz(*q)) for q in p])
    for sg in (-1, 1):
        e = p + N * sg * 0.85
        top = np.c_[e, z + 0.02]; bot = np.c_[e, z - depth]
        P = np.concatenate([top, bot]); n = len(p)
        I = [[i, i + 1, i + n + 1] for i in range(n - 1)] + [[i, i + n + 1, i + n] for i in range(n - 1)]
        out_ = np.c_[-N * sg, np.zeros(n)].mean(0)
        U.oadd(B, P, I, 'stone', out_, UV=np.c_[np.r_[np.arange(n), np.arange(n)] * 0.8, P[:, 2]])
        cap = np.concatenate([np.c_[e, z + 0.06], np.c_[p + N * sg * 1.15, z + 0.06]])
        U.oadd(B, cap, I, 'stone', (0, 0, 1))
    bed = np.concatenate([np.c_[p - N * 0.86, z - depth + 0.02], np.c_[p + N * 0.86, z - depth + 0.02]]); n = len(p)
    I = [[i, i + 1, i + n + 1] for i in range(n - 1)] + [[i, i + n + 1, i + n] for i in range(n - 1)]
    U.oadd(B, bed, I, 'ground', (0, 0, 1), c1=(0, 0, 0, PD.SID['riverbed']))
    wat = bed.copy(); wat[:, 2] += 0.18
    U.oadd(B, wat, I, 'water', (0, 0, 1))

def stones_kyoko(B, P1):
    """(also: big dressed stones along the Kinkaku's base at the waterline) the named stones: 九山八海石 on its islet in front of the Kinkaku, a row of flat 夜泊石, standing stones on 葦原島"""
    rng = np.random.default_rng(91)
    c_, s_ = math.cos(KYAW), math.sin(KYAW)
    for k, u in enumerate(np.arange(-KK.A1 - 1.6, KK.A1 + 1.6, 0.85)):          # south face
        v = -KK.C1 - 1.25 - rng.uniform(0, 0.25)
        U.rock(B, (u * c_ - v * s_, u * s_ + v * c_, WL + 0.1), rng.uniform(0.38, 0.62), 9200 + k, flat=0.75, sub=1, sink=0.45, aniso=(1.4, 1.0))
    for k, v in enumerate(np.arange(-KK.C1 - 1.1, 1.5, 0.9)):                 # west face, under the 漱清
        u = -KK.A1 - 1.35 - rng.uniform(0, 0.25)
        U.rock(B, (u * c_ - v * s_, u * s_ + v * c_, WL + 0.1), rng.uniform(0.36, 0.58), 9260 + k, flat=0.75, sub=1, sink=0.45, aniso=(1.4, 1.0))
    isl = sorted(P1.islands, key=lambda i: i.centroid.distance(Point(-6.6, -18.2)))[0]
    c = isl.centroid
    U.rock(B, (c.x, c.y, WL + 0.55), 0.75, 9101, flat=1.5, sub=2, sink=0.1, aniso=(0.9, 0.7), tilt=0.2)              # 九山八海石
    for k, (x, y) in enumerate(((-14.0, -20.5), (-16.4, -21.4), (-18.9, -22.0), (-21.2, -22.9))):
        U.rock(B, (x, y, WL + 0.12), 0.45, 9110 + k, flat=0.35, sub=1, sink=0.4, aniso=(1.3, 1.0))                     # 夜泊石
    big = max(P1.islands, key=lambda i: i.area)
    bc = big.centroid
    for k, (dx, dy, s) in enumerate(((-6.0, 1.5, 0.9), (4.5, -2.0, 0.8), (9.0, 1.0, 0.7), (-1.0, -3.0, 0.65))):
        q = (bc.x + dx, bc.y + dy)
        if big.buffer(-0.6).contains(Point(q)):
            U.rock(B, (q[0], q[1], float(P1.h(*q)[0]) + 0.3), s, 9120 + k, flat=1.1, sub=2, sink=0.25, tilt=0.15)          # 細川石, 畠山石 ...
    for k, (x, y, s) in enumerate(((10.0, -36.0, 0.6), (-27.0, -38.0, 0.55), (3.0, -27.0, 0.5), (24.0, -18.0, 0.6), (-36.0, -12.0, 0.55))):
        if P1.water.contains(Point(x, y)):
            U.rock(B, (x, y, WL + 0.3), s, 9140 + k, flat=0.9, sub=2, sink=0.3)                                           # rock islets (岩島)

# ------------------------------------------------------------------ garden: features, steps, rails, lanterns
def route_lines(ways):
    return unary_union([LineString(a) for (w, a, wd, kind) in ways if w['id'] in MAIN or kind == 'steps'])

def build_garden(B, S, gz, T, P1, P2, ways):
    zf = lambda x, y: float(T.h(x, y)[0])
    # stone steps on the hill
    for (w, a, wd, kind) in ways:
        if kind == 'steps': GD.steps(B, a, zf, width=max(1.6, wd), seed=w['id'] % 997)
    # the features at their OSM points
    pt = lambda pid: osm_point(S, pid)
    q = pt(3525976650)                                          # 龍門滝: the fall faces south-west down the slope
    if q is not None: GD.ryumon(B, gz, q[0], q[1], math.radians(-115), float(gz(*q)) - 0.25)
    q = pt(3525976649)
    if q is not None: GD.gingasen(B, gz, q[0], q[1], math.radians(-95))
    q = pt(3525976644)
    if q is not None: GD.gankasui(B, gz, q[0], q[1], math.radians(-100))
    q = pt(3525976646)
    if q is not None: GD.sakaki_shrine(B, q[0], q[1], float(gz(*q)), math.radians(-90))
    q = pt(3537880797)
    if q is not None: GD.fuji_chozubachi(B, q[0], q[1], zf(*q))
    q = pt(3525976648)
    if q is not None: GD.kijinto(B, q[0], q[1], zf(*q))
    # the 総門's stone bridge over the ditch
    a = osm_line(S, 'ways', BRIDGE_SOMON)
    if a is not None:
        d = (a[-1] - a[0]) / np.linalg.norm(a[-1] - a[0])
        GD.somon_bridge(B, a[0] + d * 0.6, a[-1] - d * 0.6, float(gz(*a.mean(0))) + 0.08)
    # 陸舟の松: low props under its trained branches
    for k, (dx, dy) in enumerate(((-2.0, 0.8), (-0.5, 2.2), (1.6, 1.4), (2.8, -0.4), (-3.2, -1.0), (0.4, -1.8))):
        x, y = 51.66 + dx, -5.47 + dy
        z = float(gz(x, y))
        prim.cyl(B, (x, y, z), (x, y, z + 1.0 + 0.1 * k), 0.05, 0.05, 6, 'wood_natural', tag='detail')
        prim.obox(B, (x - 0.35, y, z + 1.0 + 0.1 * k), (x + 0.35, y, z + 1.0 + 0.1 * k), 0.06, 0.06, 'wood_natural', tag='detail')
    # granite curbs edging the main gravel paths (on the ground they follow; sunk a little)
    for (w, a, wd, kind) in ways:
        if kind != 'path' or w['id'] not in MAIN: continue
        p, _ = U.resample(a, 1.0)
        if len(p) < 2: continue
        N, Tg = U.normals2(p)
        for sg in (-1, 1):
            e = p + N * sg * (wd / 2 + 0.06)
            z = np.array([zf(*q) for q in e])
            for i in range(len(e) - 1):
                if P1.water.buffer(0.5).contains(Point(e[i])): continue
                prim.obox(B, np.r_[e[i], z[i] - 0.03], np.r_[e[i + 1], z[i + 1] - 0.03], 0.12, 0.2, 'curb', tag='detail', ends=False)
    # the low rails along the paths (OSM split-rail fences), never across the route
    route = route_lines(ways).buffer(1.3)
    skip_ids = set()
    for w in S.osm['barriers']:
        if w['tags'].get('barrier') != 'fence' or w['tags'].get('fence_type') not in ('split_rail', None): continue
        a = osm_line(S, 'barriers', w['id'])
        if a is None or len(a) < 2 or w['id'] in skip_ids: continue
        ln = LineString(a)
        if not Polygon(box(-120, -110, 165, 160)).contains(ln.centroid): continue
        if w['tags'].get('name') == '金閣寺垣':
            for seg in PD_lines(ln.difference(route)): GD.kenninji(B, np.array(seg.coords), zf, h=1.0)
            continue
        for seg in PD_lines(ln.difference(route)):
            if seg.length > 0.8: GD.rails(B, np.array(seg.coords), zf)
    # lit stone lanterns along the way
    for (x, y, h, kind) in ((24.5, -2.0, 1.9, 'kasuga'), (-11.0, 12.5, 1.4, 'yukimi'), (36.0, -35.0, 2.1, 'kasuga'), (72.0, 71.5, 1.8, 'kasuga'),
                            (15.0, 50.5, 1.8, 'kasuga'), (48.0, -52.0, 2.0, 'kasuga'), (126.0, -40.5, 2.2, 'kasuga'), (60.0, 79.0, 1.6, 'kasuga'),
                            (-25.0, 22.0, 1.5, 'yukimi'), (100.5, 56.5, 1.9, 'kasuga')):
        if P1.region.contains(Point(x, y)) and P1.water.contains(Point(x, y)): continue
        GD.lantern(B, x, y, zf(x, y), h=h, kind=kind)

def PD_lines(g):
    if g.is_empty: return []
    return [l for l in (g.geoms if hasattr(g, 'geoms') else [g]) if l.geom_type == 'LineString']

# ------------------------------------------------------------------ planting
def plant(B, S, P1, P2, T, gz, core, ways, P_prec):
    rng = np.random.default_rng(2026)
    out = []
    zf = lambda x, y: float(T.h(x, y)[0])
    def add(sp, x, y, s, z=None):
        if z is None:
            z = float(P1.h(x, y)[0]) if P1.region.contains(Point(x, y)) else float(P2.h(x, y)[0]) if P2.region.contains(Point(x, y)) else zf(x, y)
        B.tree(sp, x, y, z, s, rng.uniform(0, 6.283)); out.append((sp, x, y))
    # keep-outs: buildings, walls, water, paths, terraces' flats, the view cones of the shots
    bl = []
    for b in S.osm['buildings']:
        r = osm_ring(S, b['id'])
        if r and P_prec.buffer(5).contains(Point(np.mean(r, axis=0))): bl.append(Polygon(r).buffer(1.8))
    for w in S.osm['landuse']:                       # parking, retail yards
        if w['tags'].get('amenity') in ('parking', 'bicycle_parking') or w['tags'].get('landuse') == 'retail':
            L = w['poly']
            while isinstance(L[0][0], list): L = L[0]
            bl.append(Polygon(np.array(L) - [KX, KY]).buffer(1.0))
    for w in S.osm['ways']:                          # roads and the wide approach
        if w['tags'].get('highway') in ('primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'service', 'pedestrian'):
            a_ = osm_line(S, 'ways', w['id'])
            if a_ is not None and len(a_) > 1: bl.append(LineString(a_).buffer(w.get('width', 4.0) / 2 + 1.2))
    blocked = unary_union(bl + [P1.water.buffer(0.4), P2.water.buffer(0.4), P1.base.buffer(4.0), box(44, -50, 100, -27), box(-12, 8, 30, 20)])
    walk = unary_union([LineString(a).buffer(wd / 2 + 0.9) for (w, a, wd, kind) in ways])
    cones = []
    for (name, cam, tgt, lens) in SHOTS_ALL:
        if name == 'aerial': continue
        c = np.array(cam[:2]) - [KX, KY]; t = np.array(tgt[:2]) - [KX, KY]
        d = t - c; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
        far = c + d * L * 0.9
        cones.append(Polygon([c - d * 3 - n * 4.5, c - d * 3 + n * 4.5, c + d * 8 + n * 5.5, far + n * L * 0.12, far - n * L * 0.12, c + d * 8 - n * 5.5]))
    cones = unary_union(cones)
    for g in (blocked, walk, cones, core, P_prec): shapely.prepare(g)
    def ok(x, y, clear=2.5, cone=True):
        p = Point(x, y)
        if blocked.contains(p) or walk.contains(p) or not P_prec.contains(p): return False
        if cone and cones.contains(p): return False
        return all((x - tx) ** 2 + (y - ty) ** 2 > clear ** 2 for (_, tx, ty) in out[-300:])
    # pines on the islands of 鏡湖池 (several on 葦原島), the rock islet off the viewpoint keeps its two
    for isl in P1.islands:
        a = isl.area
        k = 1 if a < 9 else 2 if a < 30 else 3 if a < 60 else 8
        pts = []
        for t in range(300):
            if len(pts) >= k: break
            q = (rng.uniform(isl.bounds[0], isl.bounds[2]), rng.uniform(isl.bounds[1], isl.bounds[3]))
            if isl.buffer(-0.45).contains(Point(q)) and all(math.dist(q, p) > 2.4 for p in pts): pts.append(q)
        for q in pts: add('matsu', q[0], q[1], rng.uniform(0.5, 0.82))
    # named trees: 陸舟の松, the イチイガシ, the 侘助椿, the pine by the 庫裏
    add('matsu', 51.66, -5.47, 0.62)
    add('kashi', 90.85, -48.1, 1.5)
    add('kashi', 64.85, -36.7, 0.3)
    add('matsu', 95.55, -33.4, 0.8)
    # the banks of 鏡湖池: pines first, maples and azaleas between, a few oaks
    L = P1.outer.exterior
    for i in range(420):
        q = L.interpolate(rng.uniform(0, L.length)); dn = rng.uniform(1.2, 7.0)
        x, y = q.x + rng.normal(0, dn), q.y + rng.normal(0, dn)
        if P1.outer.buffer(0.6).contains(Point(x, y)) or not ok(x, y, 2.4): continue
        r = rng.random()
        if r < 0.42: add('matsu', x, y, rng.uniform(0.55, 0.95))
        elif r < 0.62: add('tsutsuji', x, y, rng.uniform(0.8, 1.5))
        elif r < 0.84: add('momiji', x, y, rng.uniform(0.6, 1.0))
        else: add('kashi', x, y, rng.uniform(0.4, 0.7))
    # 安民沢's banks: maples and oaks, cedars behind
    L = P2.outer.exterior
    for i in range(120):
        q = L.interpolate(rng.uniform(0, L.length)); dn = rng.uniform(1.0, 6.0)
        x, y = q.x + rng.normal(0, dn), q.y + rng.normal(0, dn)
        if P2.outer.buffer(0.5).contains(Point(x, y)) or not ok(x, y, 3.0): continue
        r = rng.random()
        add('momiji' if r < 0.4 else 'kashi' if r < 0.7 else 'sugi' if r < 0.88 else 'matsu', x, y, rng.uniform(0.6, 1.0))
    # the moss garden round the pond and the halls: pines, maples, oaks
    for i in range(1500):
        x, y = rng.uniform(-120, 110), rng.uniform(-100, 25)
        if not ok(x, y, 4.2): continue
        r = rng.random()
        if r < 0.38: add('matsu', x, y, rng.uniform(0.6, 1.05))
        elif r < 0.62: add('momiji', x, y, rng.uniform(0.6, 1.05))
        elif r < 0.85: add('kashi', x, y, rng.uniform(0.55, 1.0))
        elif r < 0.93: add('sugi', x, y, rng.uniform(0.6, 0.9))
        else: add('tsutsuji', x, y, rng.uniform(0.9, 1.6))
    # the hill behind (north): cedars, cypress, oaks, maples on the lower slopes
    for i in range(5000):
        x, y = rng.uniform(-130, 170), rng.uniform(20, 160)
        if not ok(x, y, 5.2): continue
        z = float(gz(x, y)); r = rng.random()
        if -45 < x < 45 and y < 60:                            # right behind the Kinkaku: pines and round oaks, cedars only further up
            add('matsu' if r < 0.4 else 'kashi' if r < 0.75 else 'momiji' if r < 0.92 else 'hinoki', x, y, rng.uniform(0.7, 1.05)); continue
        if z < 101.5 and r < 0.3: add('momiji', x, y, rng.uniform(0.65, 1.05))
        elif r < 0.44: add('sugi', x, y, rng.uniform(0.7, 1.1))
        elif r < 0.58: add('hinoki', x, y, rng.uniform(0.65, 1.0))
        elif r < 0.84: add('kashi', x, y, rng.uniform(0.6, 1.05))
        elif r < 0.92: add('momiji', x, y, rng.uniform(0.65, 1.0))
        else: add('matsu', x, y, rng.uniform(0.7, 1.0))
    # the southern woods (to the precinct's edge)
    for i in range(4200):
        x, y = rng.uniform(-130, 230), rng.uniform(-185, -78)
        if not ok(x, y, 5.0): continue
        r = rng.random()
        add('kashi' if r < 0.35 else 'sugi' if r < 0.55 else 'matsu' if r < 0.75 else 'momiji' if r < 0.92 else 'hinoki', x, y, rng.uniform(0.65, 1.05))
    # the east, round the offices, the exit, the shops and the car parks: scattered
    for i in range(1400):
        x, y = rng.uniform(95, 330), rng.uniform(-80, 200)
        if not ok(x, y, 5.5): continue
        r = rng.random()
        add('matsu' if r < 0.35 else 'momiji' if r < 0.65 else 'kashi', x, y, rng.uniform(0.6, 1.0))
    return out
