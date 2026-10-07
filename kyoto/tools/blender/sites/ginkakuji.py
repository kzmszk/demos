"""銀閣寺 (慈照寺 Jishō-ji, Higashiyama) — the hero site.

Built in a garden frame whose origin is the 銀閣's centroid (OSM way 87960601): x east, y north, z absolute (T.P.).
Parts (run_site --only accepts these names): ginkaku, halls, gates, approach, pond, garden, hill, trees.
  ginkakuji_ginkaku.py  観音殿 (銀閣)
  ginkakuji_halls.py    東求堂, 本堂 (方丈), 宝処関, corridor, 弄清亭, 庫裏, 書院, support buildings, gates, walls, shrines
  ginkakuji_pond.py     錦鏡池: own ground around the pond (the DEM has 3-6 m spikes in the water), water, islands, shore stones
  ginkakuji_garden.py   銀沙灘, 向月台, 銀閣寺垣, fences, bridges, 洗月泉, moss mounds
References: /home/kazu/work/kyoto-assets/refs/ginkakuji (dossier.md + photos)."""
import math, os
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
import jk
from jk import prim, arch, Frame
from . import ginkakuji_ginkaku as GK
from . import ginkakuji_pond as PD
from . import ginkakuji_halls as HL
from . import ginkakuji_garden as GD
from . import ginkakuji_util as U

GX, GY = 3581.30121009, 4520.28054924          # garden origin = the Ginkaku's centroid
def W(x, y, z): return (x + GX, y + GY, z)

SHOTS = [('ginkaku_pond', W(29, -9, 93.5), W(0, 0, 96.0), 42),        # 銀閣 across 錦鏡池 (Ginkaku-ji after being restored 2008)
         ('ginshadan', W(31.5, 33.3, 94.3), W(8, 6, 93.2), 26),         # 銀沙灘 + 向月台 with the 銀閣 behind, from the 本堂 veranda
         ('kogetsudai', W(11.6, 17.2, 93.4), W(17.5, 9.5, 92.4), 30),   # 向月台 close (Ginkakuji Kō getsudai)
         ('hedge', W(-21.7, 63.5, 93.1), W(-21.4, 20, 92.6), 24),       # the 銀閣寺垣 approach looking south
         ('viewpoint', W(87.7, 21.3, 113.0), W(12, 10, 94), 50),        # from the 展望所 over the roofs (Blick auf Ginkaku und Togu-do)
         ('togudo', W(33.5, 19.5, 93.4), W(38.5, 38.5, 94.0), 34),      # 東求堂 across the north pond
         ('somon', W(-49, 69.4, 92.6), W(-31, 69.2, 93.6), 34),         # 総門 from the forecourt
         ('hill_west', W(74.5, 42, 101.4), W(20, 38, 93), 36),          # the halls' roofs from the hill path (Blick auf Togu-do)
         ('togudo_close', W(30.5, 30.5, 93.4), W(38, 38.8, 94.5), 30),  # 東求堂 from the south-west (Ginkakuji Togudo)
         ('aerial', W(-55, -95, 195), W(22, 28, 92), 30)]               # aerial from the south-west
SHOTS_ALL = list(SHOTS)
if os.environ.get('GK_DEV'):
    SHOTS = SHOTS + [('dev_gk_se', W(14, -12, 93.0), W(0, 0, 95.5), 30), ('dev_gk_nw', W(-12, 12, 93.0), W(0, 0, 95.5), 30),
                     ('dev_gk_top', W(9, -9, 101.5), W(0, 0, 97.5), 35), ('dev_hojo', W(14, 22, 93.4), W(20.6, 38.9, 95.0), 32),
                     ('dev_hoshokan', W(2, 22.5, 93.2), W(11.5, 26.4, 93.8), 32), ('dev_chumon', W(-22, 21.5, 93.0), W(-15, 21, 93.3), 34),
                     ('dev_gk_up', W(9.5, -7.5, 97.0), W(0, 0, 97.6), 30), ('dev_gk_soffit', W(6.5, -3.5, 95.2), W(1.5, 0.5, 97.8), 28),
                     ('dev_steps', W(60, 24.5, 95.0), W(72, 22, 98.5), 30), ('dev_falls', W(45.5, -4.0, 92.9), W(51.8, -5.2, 92.6), 30),
                     ('dev_bridge', W(36, 14, 93.0), W(43, 23, 91.8), 32), ('dev_corner', W(-21.5, 30, 93.1), W(-15, 21, 93.0), 28),
                     ('dev_gate_in', W(-30.5, 69.5, 93.1), W(-19, 66, 93.0), 30)]
if os.environ.get('GK_SHOTS'):
    SHOTS = [s for s in SHOTS if s[0] in os.environ['GK_SHOTS'].split(',')]

def wring(poly):
    return [[float(x + GX), float(y + GY)] for (x, y) in list(poly.exterior.coords)[:-1]]

def osm_line(S, cat, wid):
    for w in S.osm[cat]:
        if w['id'] == wid:
            L = w.get('line') or w.get('poly')
            while isinstance(L[0][0], list): L = L[0]
            return np.array(L, float) - [GX, GY]
    return None

def osm_ring(S, wid):
    for b in S.osm['buildings']:
        if b['id'] == wid:
            L = b['poly']
            while isinstance(L[0][0], list): L = L[0]
            return [(x - GX, y - GY) for (x, y) in L]
    return None

# ------------------------------------------------------------------ preview-only helpers (nothing reaches the npz)
def preview_patch(S, hf=None):
    """run_site draws the raw DEM as context terrain: drop it where we model the ground ourselves (S.cut, the DEM spikes in
    the pond) and light the shots from the south-east."""
    cut = unary_union([Polygon(r) for r in S.cut]) if S.cut else None
    orig = jk.to_objects
    def to_objects(b, *a, **k):
        if b.name == 'terrain' and cut is not None:
            for p in b.parts:
                if hf is not None:
                    inside = shapely.contains_xy(cut.buffer(2.0), p['P'][:, 0], p['P'][:, 1])
                    for i in np.where(inside)[0]:
                        p['P'][i, 2] = min(p['P'][i, 2], hf(p['P'][i, 0] - GX, p['P'][i, 1] - GY) - 0.12)
                else:
                    T = p['P'][p['I']]
                    ins = np.stack([shapely.contains_xy(cut, T[:, k_, 0], T[:, k_, 1]) for k_ in range(3)], 1)
                    p['I'] = p['I'][~ins.all(1)]
        objs = orig(b, *a, **k)
        try:                                   # the viewer culls back faces: show the previews the same way
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
            rng = np.random.default_rng(int(x * 10 + y))
            for k in range(4):
                a = rng.uniform(0, 6.28); r = H * rng.uniform(0.1, 0.3); zz = z + H * (0.45 + 0.13 * k)
                rr = H * (0.28 - 0.04 * k)
                prim.lathe(tb, (x + r * math.cos(a), y + r * math.sin(a), zz), [(0.0, 0.0), (rr, 0.05 * H), (rr * 0.8, 0.12 * H), (0.0, 0.15 * H)], 8, 'hedge', smooth=True)
        elif sp == 'take':
            prim.lathe(tb, (x, y, z + H * 0.4), [(0.0, 0.0), (H * 0.12, 0.2 * H), (H * 0.1, 0.5 * H), (0.0, 0.6 * H)], 6, 'hedge', smooth=True)
        else:
            rr = H * (0.36 if sp == 'momiji' else 0.3)
            prim.lathe(tb, (x, y, z + H * 0.35), [(0.0, 0.0), (rr * 0.8, 0.12 * H), (rr, 0.35 * H), (rr * 0.7, 0.58 * H), (0.0, 0.66 * H)], 8, 'hedge', smooth=True)
    col = bpy.data.collections.new('preview_trees'); bpy.context.scene.collection.children.link(col)
    jk.to_objects(tb, collection=col, tags=('main',))

# ------------------------------------------------------------------ the site
def build(B, S, only=None):
    want = lambda k: (not only) or (k in only)
    gz = lambda x, y: S.ground(np.asarray(x) + GX, np.asarray(y) + GY)
    G = PD.Ground(S, GX, GY)
    print(f'ginkakuji: water level {G.WL:.2f}, bank {G.bank:.2f}')
    shapely.prepare(G.region)
    def zg(x, y):
        """ground: ours near the pond, the DEM elsewhere"""
        if G.region.contains(Point(x, y)): return G.h(x, y)
        return float(gz(x, y))
    # ---- site edits
    prec = S.polygon
    while isinstance(prec[0][0][0], list): prec = prec[0]
    S.exclude.append(prec[0] if isinstance(prec[0][0], list) else prec)
    S.cut.append(wring(G.region))
    P_prec = Polygon(np.array(S.exclude[0]) - [GX, GY])
    # garden path network (OSM footways / paths / steps) inside the precinct
    ways = []
    for w in S.osm['ways']:
        hw = w['tags'].get('highway')
        if hw not in ('footway', 'path', 'steps'): continue
        L = w['line']
        while isinstance(L[0][0], list): L = L[0]
        a = np.array(L, float) - [GX, GY]
        if len(a) < 2 or not P_prec.buffer(2).contains(Point(a.mean(0))): continue
        ways.append((w, a))
    garden_box = box(-14, -48, 62, 34)
    paint = []
    def P(poly, surf): paint.append((poly, surf))
    P(P_prec.intersection(garden_box).buffer(0), 'moss')
    paths_low = []; paths_hill = []
    for (w, a) in ways:
        wd = 1.6 if w.get('width', 2.0) >= 1.5 else 1.1
        ln = LineString(a)
        zs = [zg(*q) for q in a]
        hill = (max(zs) > 93.2) or w['tags'].get('highway') == 'steps'
        (paths_hill if hill else paths_low).append((w, a, wd))
        P(ln.buffer(wd / 2, cap_style=2), 'stone_slab' if w['tags'].get('highway') == 'steps' else ('soil' if hill else 'sand'))
    COURT = Polygon([(10.2, 19.5), (11.6, 23.9), (16.0, 24.0), (16.6, 31.6), (32.0, 32.0), (33.2, 24), (34.2, 12.8), (31.0, 13.6), (28.0, 15.2),
                     (24.5, 15.4), (22.0, 13.0), (19.5, 8.4), (16.0, 7.2), (12.5, 8.2), (10.8, 11.5), (9.5, 16.0)])
    P(COURT, 'sand')
    P(Polygon([(-5.3, -5.4), (5.4, -5.4), (5.4, 5.4), (-5.3, 5.4)]).difference(G.outer.buffer(0.3)), 'stone_slab')      # apron round the Ginkaku
    corridor = unary_union([box(-23.8, 14.6, -19.6, 66.0), box(-31.2, 65.7, -18.8, 74.0), box(-24.8, 14.6, -14.7, 29.2)])
    P(corridor, 'sand')
    P(box(-56, 66.6, -33.2, 71.8), 'stone_sett')                                                      # forecourt of the 総門
    P(box(-14.7, 17.6, 11.8, 24.0).difference(box(-9.2, 14, 11, 20.4)), 'stone_sett')                # 中門 -> 宝処関 path
    P(Polygon([(85.6, 18.0), (93.6, 18.4), (94.6, 24.0), (86.8, 24.4)]), 'gravel')                   # 展望所
    garden_paths = unary_union([LineString(a).buffer(wd / 2) for (w, a, wd) in paths_low] + [COURT, corridor])
    for (poly, surf) in paint:
        for g in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if g.geom_type == 'Polygon' and g.area > 0.2:
                S.paint.append({'poly': wring(g), 'surf': surf})
    trees = []
    with Frame(B, GX, GY, 0.0, 0.0):
        if want('ginkaku'):
            GK.build(B, S, 0.0, 0.0, gz)
        if want('pond'):
            PD.build(B, G, garden_paths)
        if want('halls'): build_halls(B, S, gz, zg)
        if want('gates'): build_gates(B, S, gz)
        if want('approach'): build_approach(B, S, gz)
        if want('garden'): build_garden(B, S, G, gz, zg)
        if want('hill'): build_hill(B, S, gz, paths_hill)
        if want('trees'): trees = plant(B, S, G, gz, zg, P_prec, ways)
    print(f'ginkakuji: {len(trees)} trees')
    preview_patch(S, lambda x, y: G.h(x, y) if G.region.buffer(2.0).contains(Point(x, y)) else float(gz(x, y)))
    tree_proxies(B.trees)

# ------------------------------------------------------------------ halls
def build_halls(B, S, gz, zg):
    # 東求堂: 6.9 m square (三間半), faces south; floor 0.6, 檜皮葺 入母屋, ridge 6.7 (PLATEAU)
    tx, ty = 38.1, 38.85
    z0 = float(gz(tx, ty)) - 0.05
    g = [-3.45, -2.46, -0.49, 1.48, 3.45]
    tog = {0: ['plaster', 'renji', 'karado_open', 'renji'], 1: ['mairado', 'plaster', 'shoji', 'plaster'], 2: ['plaster', 'mairado', 'plaster', 'plaster'],
           3: ['plaster', 'shoji', 'mairado', 'plaster']}
    HL.hall(B, tx, ty, 0.0, z0, 6.9, 6.9, nb=(4, 4), grid=(g, g), fit=lambda k, i: tog[k][i], floor=0.6, wall=2.75, nage=1.76, ver=(0, 3), ver_w=1.2,
            roof='irimoya', cover='hiwada', o=1.55, ridge=z0 + 6.7, teri=1.45, rafter=0.42, tiers=1, sori=0.25, sori_len=0.6)
    # 本堂 (方丈): roof 17.6 x 13.6 (OSM), walls 14 x 10, faces the sand garden (south), ridge 7.9 (PLATEAU)
    hx, hy = 20.6, 38.9
    z0h = float(gz(hx, hy)) - 0.05
    hon = {0: ['mairado', 'mairado', 'shoji_open', 'shoji', 'mairado', 'mairado'], 1: ['mairado', 'plaster', 'mairado', 'plaster'],
           2: ['plaster', 'mairado', 'plaster', 'plaster', 'mairado', 'plaster'], 3: ['plaster', 'mairado', 'mairado', 'plaster']}
    HL.hall(B, hx, hy, 0.0, z0h, 14.0, 10.0, nb=(6, 4), fit=lambda k, i: hon[k][i], floor=0.75, wall=3.3, nage=1.9, ver=(0, 1, 3), ver_w=1.1,
            roof='irimoya', cover='hiwada', o=1.8, ridge=z0h + 7.9, teri=1.4, rafter=0.4, tiers=1, sori=0.3, sori_len=0.6)
    # corridor 本堂 -> 東求堂
    corridor(B, (27.0 + 1.1, 40.6), (34.65 - 1.2, 40.6), z0h + 0.62, 1.7, cover='hiwada')
    # 宝処関: the entrance hall, white walls with a 花頭 doorway on the west, open to the south; and the link to the 本堂
    bx, by = 11.78, 26.4
    z0b = float(gz(bx, by)) - 0.05
    def hfit(k, i):
        return {0: 'open', 1: 'plaster', 2: 'plaster', 3: 'open'}[k]
    info = HL.hall(B, bx, by, 0.0, z0b, 6.6, 3.3, nb=(3, 1), fit=hfit, floor=0.15, wall=2.75, nage=2.2, roof='yosemune', cover='hiwada', o=0.55,
                   ridge=z0b + 4.9, teri=1.3, rafter=0.35, sori=0.1, base_h=0.12, funa=False)
    kato_door(B, (bx - 3.3, by + 1.65), (bx - 3.3, by - 1.65), (-1, 0), z0b + 0.15, z0b + 2.9)
    for (p, q) in (((bx - 3.3, by - 1.65), (bx - 3.3, by + 1.65)), ((bx - 3.3, by + 1.65), (bx + 3.3, by + 1.65)), ((bx + 3.3, by + 1.65), (bx + 3.3, by - 1.65))):
        prim.obox(B, (*p, z0b + 1.2), (*q, z0b + 1.2), 0.3, 2.4, 'stone', tag='block')
    corridor(B, (13.7, 28.6), (13.7, 32.2), z0b + 0.3, 3.4, cover='hiwada', walls=True)
    # 弄清亭
    rx, ry = 36.65, 54.4
    z0r = float(gz(rx, ry)) - 0.05
    rfit = lambda k, i: ['shoji', 'mairado', 'plaster', 'shoji', 'plaster'][(i + k) % 5]
    HL.hall(B, rx, ry, 0.0, z0r, 11.5, 8.8, nb=(5, 4), fit=rfit, floor=0.55, wall=2.9, ver=(0,), ver_w=0.9, roof='irimoya', cover='sangawara', o=0.9,
            ridge=z0r + 6.2, teri=1.3, rafter=0.0, sori=0.1)
    HL.hall(B, 34.75, 47.85, 0.0, z0r, 8.0, 1.9, nb=(4, 1), fit=lambda k, i: 'mairado' if k == 0 else 'plaster', floor=0.5, wall=2.4, roof='kirizuma',
            cover='sangawara', o=0.45, ridge=z0r + 4.0, teri=1.2, rafter=0, funa=False, detail=False, verge=0.4)
    # 庫裏: three tiled blocks with stacked gables facing east, the 玄関 gable facing south
    z0k = float(gz(-2.0, 45.0)) - 0.05
    kfit = lambda k, i: ['plaster', 'mairado', 'plaster', 'koshi', 'shoji', 'plaster'][(i * 2 + k) % 6]
    HL.hall(B, -2.8, 39.55, 0.0, z0k, 16.6, 10.3, nb=(7, 4), fit=kfit, floor=0.5, wall=3.6, roof='irimoya', cover='sangawara', o=1.0,
            ridge=z0k + 8.6, teri=1.25, rafter=0.0, sori=0.05)
    HL.hall(B, -2.85, 54.0, 0.0, z0k, 16.5, 14.7, nb=(7, 6), fit=kfit, floor=0.5, wall=4.2, roof='irimoya', cover='sangawara', o=1.0,
            ridge=z0k + 9.6, teri=1.25, rafter=0.0, sori=0.05)
    HL.hall(B, 8.75, 39.6, math.pi / 2, z0k, 11.2, 3.6, nb=(5, 1), fit=kfit, floor=0.5, wall=3.0, roof='kirizuma', cover='sangawara', o=0.6,
            ridge=z0k + 6.0, teri=1.2, rafter=0.0, sori=0.0, funa=False, verge=0.5)
    HL.hall(B, 5.5, 32.15, math.pi / 2, z0k, 2.6, 4.4, nb=(1, 2), fit=lambda k, i: 'karado' if k == 3 else 'koshi' if k == 0 else 'plaster', floor=0.2, wall=3.0,
            roof='kirizuma', cover='hongawara', o=0.7, ridge=z0k + 6.4, teri=1.3, rafter=0.3, sori=0.0, verge=0.6)
    # 書院 (1993), the hall west of it, 研修道場
    z0s = float(gz(12.75, 68.15)) - 0.05
    HL.hall(B, 12.75, 68.15, 0.0, z0s, 24.5, 9.7, nb=(10, 4), fit=lambda k, i: ['shoji', 'mairado', 'shoji', 'plaster'][(i + k) % 4], floor=0.6, wall=3.2,
            ver=(0,), ver_w=1.0, roof='irimoya', cover='sangawara', o=0.95, ridge=z0s + 7.4, teri=1.3, rafter=0.0, sori=0.1)
    z0t = float(gz(-5.8, 69.6)) - 0.05
    HL.hall(B, -5.8, 69.6, 0.0, z0t, 8.2, 5.8, nb=(4, 3), fit=lambda k, i: ['plaster', 'mairado'][(i + k) % 2], floor=0.6, wall=3.2, roof='irimoya',
            cover='sangawara', o=0.85, ridge=z0t + 7.3, teri=1.3, rafter=0.0, sori=0.1)
    z0d = float(gz(5.0, 90.0)) - 0.05
    HL.hall(B, -5.05, 91.5, math.pi / 2, z0d, 20.2, 9.2, nb=(8, 4), fit=lambda k, i: ['plaster', 'mairado', 'shoji'][(i + k) % 3], floor=0.6, wall=3.6,
            roof='irimoya', cover='sangawara', o=0.9, ridge=z0d + 8.2, teri=1.3, rafter=0.0, sori=0.1)
    HL.hall(B, 12.35, 86.7, 0.0, z0d, 22.0, 5.8, nb=(9, 2), fit=lambda k, i: ['mairado', 'plaster', 'shoji'][(i + k) % 3], floor=0.6, wall=3.2,
            roof='irimoya', cover='sangawara', o=0.9, ridge=z0d + 7.0, teri=1.3, rafter=0.0, sori=0.1)
    # support buildings (simple)
    simple = {87960608: 6.0, 87960610: 6.5, 351185872: 6.5, 351185908: 5.0, 352168403: 5.5, 352168408: 5.5, 1073258255: 6.0, 1073258256: 5.5,
              354978163: 4.0, 353381316: 3.6, 353574387: 3.4}
    for k, (wid, h) in enumerate(simple.items()):
        ring = osm_ring(S, wid)
        if ring is None: continue
        HL.simple_building(B, S, ring, gz, h_ridge=h, wall=min(3.0, h * 0.45), seed=k)
    # 八幡社 (a small shrine hall), 八幡神 and 弁財天 (祠 on rock bases), the 銀閣寺形手水鉢
    z = float(gz(-45.8, -0.1)) - 0.05
    HL.hall(B, -45.8, -0.1, -math.pi / 2, z, 3.6, 3.0, nb=(2, 2), fit=lambda k, i: 'karado' if k == 0 else 'board', floor=0.7, wall=2.2, ver=(0,), ver_w=0.7,
            roof='kirizuma', cover='copper', o=0.7, ridge=z + 4.4, teri=1.4, rafter=0.3, funa=False, verge=0.5, ends=None)
    HL.hokora(B, -5.3, 13.0, float(gz(-5.3, 13.0)), -math.pi / 2, w=0.7, d=0.55, h=0.65, base=0.7)
    HL.hokora(B, 65.1, 44.1, float(gz(65.1, 44.1)), math.pi, w=0.9, d=0.7, h=0.8, base=1.1)
    zc = float(gz(30.3, 38.3))
    U.rock(B, (30.3, 38.0, zc + 0.15), 0.6, 4401, flat=0.6, sub=1, sink=0.3)
    prim.box(B, 29.95, 37.65, zc + 0.3, 30.65, 38.35, zc + 0.85, 'stone')
    prim.box(B, 30.05, 37.75, zc + 0.75, 30.55, 38.25, zc + 0.86, 'water')

def kato_door(B, p0, p1, n, z0, z1):
    """the 花頭窓-shaped doorway in the 宝処関's west wall (plaster with a dark frame), a dark interior behind"""
    bay = U.Bay(B, p0, p1, n)
    L = bay.L
    ring = U.katomado_ring(L / 2, 1.5, z0 + 0.02, z0 + 2.3)
    ring = [(s, max(z, z0 + 0.02)) for (s, z) in ring]
    bay.plane(0.1, L - 0.1, z0, z1, 'temple_wall', off=0.02, holes=[ring], c0=(238, 234, 224, 35), c1=(0, 0, 0, 0))
    pts = np.array([bay.P(s, z, 0.05) for (s, z) in ring + [ring[0]]])
    prim.sweep(B, pts, [(-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04)], WD, up=(n[0], n[1], 0))

def corridor(B, a, b, zf, w, cover='hiwada', walls=False, h=2.4):
    """渡廊下: a covered gallery between two buildings: floor, posts, a small gable roof"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = float(np.linalg.norm(d)); yaw = math.atan2(d[1], d[0])
    c = (a + b) / 2
    with Frame(B, c[0], c[1], zf, yaw):
        prim.box(B, -L / 2, -w / 2, -0.12, L / 2, w / 2, 0.0, 'eave_wood')
        prim.polygon(B, [(-L / 2, -w / 2), (L / 2, -w / 2), (L / 2, w / 2), (-L / 2, w / 2)], 0.0, 'wood_natural', tag='walk')
        for x in np.linspace(-L / 2 + 0.1, L / 2 - 0.1, max(2, int(L / 1.8)) + 1):
            for s in (-1, 1):
                prim.box(B, x - 0.08, s * (w / 2 - 0.08) - 0.08, -0.7, x + 0.08, s * (w / 2 - 0.08) + 0.08, h, WD)
        for s in (-1, 1):
            prim.box(B, -L / 2, s * (w / 2 - 0.08) - 0.1, h, L / 2, s * (w / 2 - 0.08) + 0.1, h + 0.18, WD)
            if walls:
                bay = U.Bay(B, (-L / 2, s * (w / 2 - 0.08)), (L / 2, s * (w / 2 - 0.08)), (0, s))
                bay.plaster(0.1, L - 0.1, 0.0, h, off=-0.02)
            else:
                prim.obox(B, (-L / 2, s * (w / 2 - 0.08), 0.45), (L / 2, s * (w / 2 - 0.08), 0.45), 0.06, 0.08, WD, tag='detail')
                prim.obox(B, (-L / 2, s * (w / 2 - 0.08), 0.4), (L / 2, s * (w / 2 - 0.08), 0.4), 0.1, 0.8, 'stone', tag='block')
        from jk import roof as jroof
        jroof.roof(B, L, w, h + 0.2, 0.6, kind='kirizuma', cover=cover, pitch=0.62, teri=1.3, sori=0.0, rafter=0.4, tiers=1, rafter_mat=WD,
                   rafter_end=WD, ends='oni', verge=0.15, edge=0.25, bargeboard_mat=WD)
WD = 'wood_dark'

# ------------------------------------------------------------------ gates and walls
def build_gates(B, S, gz):
    # 石標 "史蹟 慈照寺 (銀閣寺) 旧境内" at the forecourt, a granite post on a plinth (Stele and Sando of Jishoji)
    zs = float(gz(-38.6, 66.6))
    prim.box(B, -38.95, 66.25, zs - 0.1, -38.25, 66.95, zs + 0.18, 'stone')
    prim.box(B, -38.8, 66.4, zs + 0.18, -38.4, 66.8, zs + 2.45, 'stone')
    prim.obox(B, (-38.6, 66.6, zs), (-38.6, 66.6, zs + 1.2), 0.6, 0.6, 'stone', tag='block')
    # 総門: front pillars at x = -32.2 facing west, roof over -33.25..-29.6 x 66.6..71.8 (OSM), ridge 4.5 (PLATEAU)
    HL.yakuimon(B, -32.2, 69.2, -math.pi / 2, float(gz(-31.4, 69.2)) - 0.03, span=3.3, depth=1.6, h=3.0, ridge=4.6, cover='hongawara')
    HL.white_wall(B, [(-32.2, 71.15), (-32.2, 74.4)], gz, h=2.3, koshi=0.9)
    HL.white_wall(B, [(-32.2, 67.25), (-32.2, 64.6)], gz, h=2.3, koshi=0.9)
    # 中門 (寛永): faces west at x = -16.4, kawara, ridge 3.9
    HL.yakuimon(B, -16.4, 20.9, -math.pi / 2, float(gz(-14.6, 20.9)) - 0.03, span=2.9, depth=1.7, h=2.65, ridge=3.95, cover='hongawara')
    walls = [[(-14.71, 23.84 + 0.45), (-14.63, 29.27)], [(-14.8, 17.94 - 0.45), (-14.78, 14.51), (-9.05, 14.57), (-9.06, 16.37)],
             [(-9.07, 18.77), (-9.08, 20.46), (9.55, 20.51)], [(11.74, 24.25), (11.75, 21.1)]]
    for wl in walls: HL.white_wall(B, wl, gz, h=2.2)
    HL.munemon(B, 10.65, 20.8, 0.0, float(gz(10.65, 20.8)), span=1.8, h=2.5)
    HL.munemon(B, -9.07, 17.57, math.pi / 2, float(gz(-9.07, 17.57)), span=1.9, h=2.5)

# ------------------------------------------------------------------ the 銀閣寺垣 approach
def build_approach(B, S, gz):
    HW = osm_line(S, 'barriers', 353383035)     # west / south: stone wall + kenninji + tall hedge on the corridor side
    HE = osm_line(S, 'barriers', 353377546)     # north / east: low hedge + tall hedge
    zpath = lambda x, y: float(gz(x, y))
    # west hedge: tall mass a little outside the OSM line, the stone wall and bamboo fence on the corridor side
    tall_w = U.offset_line(HW, -0.25)
    U.hedge_mass(B, tall_w, zpath, h=6.2, w=1.7, seed=11, step=0.6)
    wall_w = U.offset_line(HW, 1.05)
    U.stone_wall(B, wall_w, zpath, h=0.78, top_w=0.55, seed=12, side=1)
    U.kenninji(B, U.offset_line(HW, 0.72), lambda q: zpath(*q) + 0.78, h=1.3, side=1)
    for i in range(len(HW) - 1):
        prim.obox(B, np.r_[HW[i], zpath(*HW[i]) + 2.0], np.r_[HW[i + 1], zpath(*HW[i + 1]) + 2.0], 2.2, 4.0, 'stone', tag='block')
    # east hedge: tall mass; opposite the 総門 the same stone wall + fence, along the corridor a low clipped hedge
    tall_e = U.offset_line(HE, 0.25)
    U.hedge_mass(B, tall_e, zpath, h=5.6, w=1.7, seed=13, step=0.6)
    north = np.array([HE[0], HE[1], (HE[1][0] + 0.01, 64.0)])
    U.stone_wall(B, U.offset_line(north, -1.05), zpath, h=0.78, top_w=0.55, seed=14, side=-1)
    U.kenninji(B, U.offset_line(north, -0.72), lambda q: zpath(*q) + 0.78, h=1.3, side=-1)
    south = np.array([(HE[1][0] + 0.01, 64.0), HE[2], HE[3]])
    U.hedge_mass(B, U.offset_line(south, -0.95), zpath, h=1.15, w=0.85, seed=15, step=0.5, top_round=0.2)
    for i in range(len(HE) - 1):
        prim.obox(B, np.r_[HE[i], zpath(*HE[i]) + 2.0], np.r_[HE[i + 1], zpath(*HE[i + 1]) + 2.0], 2.4, 4.0, 'stone', tag='block')
    # the hedge north of the forecourt (OSM 355079870) and the camellia hedge south of the 中門 forecourt (356947903, 5 m)
    U.hedge_mass(B, osm_line(S, 'barriers', 355079870), zpath, h=3.0, w=1.1, seed=16)
    U.hedge_mass(B, osm_line(S, 'barriers', 356947903), zpath, h=4.6, w=1.4, seed=17)
    U.hedge_mass(B, osm_line(S, 'barriers', 354978160), zpath, h=1.6, w=0.9, seed=18)

# ------------------------------------------------------------------ the garden
def build_garden(B, S, G, gz, zg):
    zb = G.bank
    GD.ginshadan(B, zg, max(zg(24.5, 24.0), zb) - 0.02)
    kx, ky = 16.3, 10.9
    GD.kogetsudai(B, kx, ky, zg(kx, ky) + 0.02)
    # the standing stone on its moss islet by the 向月台 (Kogetsudai photo), 北斗石 by the pond
    GD.moss_mound(B, (12.9, 11.8), 1.4, 1.0, 0.2, zg(12.9, 11.8), seed=3)
    U.rock(B, (12.8, 11.9, zg(12.8, 11.9) + 0.35), 0.42, 5101, flat=2.3, sub=2, sink=0.12, aniso=(1.0, 0.75))
    U.rock(B, (7.7, 2.6, G.WL + 0.45), 0.8, 5102, flat=1.4, sub=2, sink=0.25)
    # bridges
    for w in S.osm['ways']:
        if w['tags'].get('bridge') != 'yes': continue
        a = osm_line(S, 'ways', w['id'])
        if a is None or not (-20 < a[:, 0].mean() < 80 and -50 < a[:, 1].mean() < 60): continue
        p0, p1 = a[0], a[-1]
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        p0 = p0 - d * 0.6; p1 = p1 + d * 0.6
        z0, z1 = zg(*p0) + 0.05, zg(*p1) + 0.05
        if w['id'] == 353566741: GD.wood_bridge(B, p0, p1, z0, z1, w=1.5)
        elif w['id'] in (190869562, 356688514, 356688509): GD.slab_bridge(B, p0, p1, z0, z1, w=0.75 if w['id'] != 356688509 else 1.1, n=1 if w['id'] == 190869562 else 2)
        else: GD.slab_bridge(B, p0, p1, z0, z1, w=1.2, n=2, arch_h=0.03)
    # 洗月泉 at the south-east corner
    GD.sengetsusen(B, 50.4, -5.2, zg, G.WL)
    # rope and low bamboo fences along the paths (OSM)
    skip = {353377546, 353383035, 355079870, 356947903, 354978160}
    for w in S.osm['barriers']:
        if w['id'] in skip: continue
        kind = w['tags'].get('barrier');
        if kind not in ('rope', 'fence'): continue
        a = osm_line(S, 'barriers', w['id'])
        if a is None or not (-30 < a[:, 0].mean() < 110 and -50 < a[:, 1].mean() < 70): continue
        if kind == 'rope': GD.rope_fence(B, a, zg)
        else: GD.bamboo_fence(B, a, zg, h=0.6 if w['tags'].get('height') == '0.5' else 1.0)
    # moss hummocks
    mounds = [((-8.5, -6.0), 3.2, 2.2, 0.45), ((-7.0, -15.0), 3.5, 2.5, 0.5), ((3.0, -19.0), 3.0, 2.0, 0.4), ((11.5, -24.0), 2.6, 1.8, 0.35),
              ((-9.0, 4.5), 2.2, 1.6, 0.35), ((44.5, -12.5), 2.8, 2.0, 0.45), ((56.0, 8.0), 2.5, 3.5, 0.5), ((55.5, 20.0), 2.0, 2.6, 0.45),
              ((36.5, -20.0), 2.4, 1.6, 0.35), ((20.0, -28.0), 2.6, 1.8, 0.35), ((-2.0, -27.0), 3.0, 2.2, 0.45), ((26.5, 1.5), 1.6, 1.0, 0.35)]
    for i, (c, rx, ry, h) in enumerate(mounds):
        GD.moss_mound(B, c, rx, ry, h, zg(*c), seed=40 + i)
    # scattered garden stones in the moss
    rng = np.random.default_rng(4242)
    for i in range(36):
        for _ in range(20):
            p = (rng.uniform(-11, 60), rng.uniform(-42, 32))
            if G.region.contains(Point(p)) and G.outer.buffer(1.0).contains(Point(p)): continue
            if Polygon(GD.GINSHADAN).buffer(2).contains(Point(p)) or box(-6, -6, 6, 6).contains(Point(p)): continue
            if box(10, 18, 34, 47).contains(Point(p)): continue
            s = rng.uniform(0.35, 0.8)
            U.rock(B, (p[0], p[1], zg(*p) + s * 0.1), s, 6000 + i, flat=rng.uniform(0.4, 0.7), sub=1 if s < 0.6 else 2, sink=0.45)
            break

# ------------------------------------------------------------------ the hill: steps and paths up to the 展望所
def build_hill(B, S, gz, paths_hill):
    for (w, a, wd) in paths_hill:
        zf = lambda x, y: float(gz(x, y))
        zs = np.array([zf(*q) for q in U.resample(a, 1.0)[0]])
        L = float(np.sum(np.linalg.norm(np.diff(a, axis=0), axis=1)))
        if L < 1.0: continue
        slope = (zs.max() - zs.min()) / max(L, 1)
        if w['tags'].get('highway') == 'steps' or slope > 0.1:
            U.steps_along(B, a, max(1.1, wd), zf, riser=0.16, mat='stone', seed=w['id'] % 1000)
        else:
            U.ribbon(B, a, wd, zf, mat=None, walk=True, off=0.02)
    # 展望所: a levelled gravel pad with a log edge and a rail on the downhill side
    vx, vy = 90.6, 21.2
    z = float(gz(vx, vy))
    pad = [(vx - 4.2, vy - 2.6), (vx + 2.6, vy - 2.6), (vx + 2.6, vy + 2.8), (vx - 4.2, vy + 2.8)]
    prim.prism(B, pad, z - 1.2, z + 0.08, 'ground', c1=(0, 0, 0, SID('gravel')))
    rail = [(vx - 4.0, vy - 2.4), (vx - 4.0, vy + 2.6)]
    for y in np.linspace(rail[0][1], rail[1][1], 4):
        prim.box(B, vx - 4.08, y - 0.06, z, vx - 3.96, y + 0.06, z + 0.85, WD)
    for zz in (0.45, 0.8):
        prim.obox(B, (vx - 4.02, rail[0][1], z + zz), (vx - 4.02, rail[1][1], z + zz), 0.07, 0.07, WD)
    prim.obox(B, (vx - 4.02, rail[0][1], z + 0.6), (vx - 4.02, rail[1][1], z + 0.6), 0.1, 1.2, 'stone', tag='block')
    prim.polygon(B, pad, z + 0.1, 'stone', tag='walk')

def SID(n):
    from .ginkakuji_pond import SID as _S
    return _S[n]

# ------------------------------------------------------------------ planting
def plant(B, S, G, gz, zg, P_prec, ways):
    rng = np.random.default_rng(2026)
    trees = []
    def add(sp, x, y, s, yaw=None):
        z = zg(x, y)
        B.tree(sp, x, y, z, s, rng.uniform(0, 6.283) if yaw is None else yaw)
        trees.append((sp, x, y))
    # keep-outs: buildings, sand, water, paths, the 展望所 view corridor
    blocked = unary_union([box(-5.5, -5.0, 5.0, 5.5), box(10.5, 31, 31, 47.5), box(32.5, 33, 44, 44.5), box(-13, 30, 11.5, 65), box(-1, 62, 26.5, 74.5),
                           box(-11, 65, -0.5, 74), box(29, 45.5, 44, 60.5), box(-11, 79.5, 25, 103), box(7.5, 23.5, 16, 32), box(-17, 17.5, -12, 24.5),
                           box(-34, 65, -28.5, 73.5), Polygon(GD.GINSHADAN).buffer(1.2), Point(16.3, 10.9).buffer(3.2), G.outer.buffer(-0.2),
                           box(-26, 14, -17.5, 75), box(-26, 13, -14, 30.5)])
    rings = [osm_ring(S, wid) for wid in (87960608, 87960610, 351185872, 351185908, 352168403, 352168408, 1073258255, 1073258256, 354978163,
                                          353381316, 353574387, 356947908, 87960618, 87960606, 351185920)]
    blocked = unary_union([blocked] + [Polygon(r).buffer(1.5) for r in rings if r])
    walkways = unary_union([LineString(a).buffer(1.3) for (w, a) in ways])
    view = Polygon([(91, 21), (60, 34), (12, 22), (8, 0), (60, 6)])
    cones = []
    for (name, cam, tgt, lens) in SHOTS_ALL:
        if name == 'aerial': continue
        c = np.array(cam[:2]) - [GX, GY]; t = np.array(tgt[:2]) - [GX, GY]
        d = t - c; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
        far = c + d * L * 0.75
        cones.append(Polygon([c - d * 3 - n * 3, c - d * 3 + n * 3, far + n * L * 0.75 * 0.2, far - n * L * 0.75 * 0.2]))
    cones = unary_union(cones)
    def ok(x, y, clear=2.0, low=False):
        p = Point(x, y)
        if blocked.contains(p) or walkways.contains(p) or not P_prec.contains(p): return False
        if cones.contains(p) and not low: return False
        return all((x - tx) ** 2 + (y - ty) ** 2 > clear ** 2 for (_, tx, ty) in trees[-400:])
    # named and photo-placed trees
    key = [('matsu', 8.5, 9.5, 0.75), ('matsu', -7.0, -2.5, 0.9), ('matsu', -6.0, 6.5, 0.8), ('matsu', 6.5, -11.0, 0.85), ('matsu', 24.0, 1.0, 0.7),
           ('matsu', 26.8, -0.5, 0.6), ('matsu', 42.0, 23.5, 0.55), ('matsu', 18.2, 29.4, 0.7), ('matsu', 31.3, 29.1, 0.65), ('matsu', 35.5, 19.0, 0.9),
           ('matsu', 37.0, 13.0, 0.85), ('matsu', 34.5, 26.5, 0.75), ('matsu', 12.0, -3.5, 0.6), ('matsu', 2.0, 9.5, 0.7), ('matsu', 20.0, -16.0, 0.8),
           ('matsu', 30.5, -12.0, 0.75), ('matsu', 45.5, 5.0, 0.7), ('hinoki', 42.1, -7.1, 0.55), ('matsu', 48.5, 28.5, 0.7), ('matsu', -10.0, -12.0, 0.9)]
    for (sp, x, y, s) in key:
        add(sp, x, y, s)
    # banks of the pond: maples, azaleas, camellias (kashi kept small), pines
    for i in range(150):
        L = G.outer.exterior
        q = L.interpolate(rng.uniform(0, L.length)); n = rng.uniform(1.0, 4.0)
        x, y = q.x + rng.normal(0, n), q.y + rng.normal(0, n)
        if G.outer.contains(Point(x, y)) or not ok(x, y, 1.6): continue
        r = rng.random()
        if r < 0.45: add('tsutsuji', x, y, rng.uniform(0.8, 1.5))
        elif r < 0.75: add('momiji', x, y, rng.uniform(0.55, 0.9))
        elif r < 0.88: add('kashi', x, y, rng.uniform(0.28, 0.42))
        else: add('matsu', x, y, rng.uniform(0.55, 0.8))
    # the moss garden south and west of the 銀閣, the courtyard edges
    for i in range(160):
        x, y = rng.uniform(-12, 58), rng.uniform(-45, 33)
        if not ok(x, y, 3.0): continue
        if G.region.contains(Point(x, y)) and not G.outer.buffer(5).contains(Point(x, y)): continue
        r = rng.random()
        if r < 0.4: add('momiji', x, y, rng.uniform(0.6, 1.0))
        elif r < 0.62: add('tsutsuji', x, y, rng.uniform(0.9, 1.6))
        elif r < 0.8: add('matsu', x, y, rng.uniform(0.6, 0.95))
        else: add('kashi', x, y, rng.uniform(0.35, 0.6))
    # the hill: cedars and cypress with oaks and maples, thinner in the view corridor
    hill = P_prec.difference(box(-60, -70, 52, 160))
    x0, y0, x1, y1 = hill.bounds
    n = 0
    for i in range(2600):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if not hill.contains(Point(x, y)) or not ok(x, y, 5.6): continue
        z = gz(x, y)
        r = rng.random()
        if view.contains(Point(x, y)):
            if rng.random() < 0.6: add('momiji', x, y, rng.uniform(0.5, 0.75))
            continue
        low = z < 97
        if low and r < 0.35: add('momiji', x, y, rng.uniform(0.7, 1.1))
        elif r < 0.5: add('sugi', x, y, rng.uniform(0.6, 1.0))
        elif r < 0.72: add('hinoki', x, y, rng.uniform(0.6, 1.0))
        elif r < 0.9: add('kashi', x, y, rng.uniform(0.6, 1.0))
        else: add('momiji', x, y, rng.uniform(0.7, 1.0))
        n += 1
    # the woods west of the approach and the north of the precinct (bamboo groves, oaks)
    for i in range(500):
        x, y = rng.uniform(-55, 60), rng.uniform(30, 150)
        if not ok(x, y, 4.0): continue
        if box(-55, 30, -26, 66).contains(Point(x, y)) or y > 104 or (x > 30 and y > 60):
            r = rng.random()
            add('take' if r < 0.3 else 'kashi' if r < 0.6 else 'momiji' if r < 0.8 else 'sugi', x, y, rng.uniform(0.6, 1.0))
    # trees rising behind the east hedge of the approach (Garden of Ginkaku-ji 01)
    for (x, y, sp, sc) in ((-15.0, 35.0, 'kashi', 0.7), (-14.6, 42.5, 'momiji', 0.95), (-15.2, 50.0, 'kashi', 0.8), (-14.8, 57.5, 'sugi', 0.55),
                           (-15.3, 63.0, 'kashi', 0.65), (-27.5, 20.0, 'momiji', 0.9), (-28.0, 28.0, 'kashi', 0.75)):
        add(sp, x, y, sc)
    # small bushes along the approach's outer sides and around the halls
    for i in range(60):
        x, y = rng.uniform(-14, 45), rng.uniform(-48, 60)
        if ok(x, y, 2.0) and not G.outer.buffer(0.5).contains(Point(x, y)): add('tsutsuji', x, y, rng.uniform(0.8, 1.4))
    return trees
