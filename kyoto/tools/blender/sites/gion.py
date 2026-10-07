"""祇園 (Gion): 花見小路 ochaya rows and 一力亭, 四条通 shop fronts with the arcade and 南座, 八坂神社 (西楼門, 舞殿, 本殿,
南楼門 ...), 白川 / 新橋通 / 白川南通 with the canal, 巽橋 and 辰巳大明神.

Town houses come from sites/machiya.py (fitted to the PLATEAU footprints, which are excluded from the generic city);
landmarks from gion_*.py.  Run: blender -b --python blender/run_site.py -- gion --shots [--only part,part]
parts: hanami, shijo, shira, shrine, minamiza, ichiriki"""
import math
import numpy as np
from jk import prim, arch, roof, Frame
import sites.machiya as M
import sites.gion_streets as G

def gz(S, x, y, dz):
    return float(S.ground(x, y)) + dz

SHOTS = [
    # 花見小路 looking south from the 四条 corner at eye height (cf. hanamikoji__Gion6550, ichiriki__2017)
    ('hanamikoji', (1482.0, 1990.0, 40.25), (1466.0, 1880.0, 41.4), 26),
    # 一力亭 from the north pavement of 四条通: the red wall along Shijo and the Hanamikoji corner (ichiriki__Gionmachi_Kitagawa)
    ('ichiriki', (1514.0, 2006.6, 40.4), (1494.0, 1985.0, 42.0), 26),
    # 一力亭 along 花見小路: black plank 犬矢来 and red wall (ichiriki__Ichiriki_Ochaya_3)
    ('ichiriki_hana', (1483.2, 1962.0, 40.1), (1486.5, 1985.0, 41.6), 30),
    # 白川: 巽橋 and 辰巳大明神 at the bridge (shirakawa__Gion_Shinbashi_spring, tatsumi-daimyojin__panoramio_17)
    ('tatsumi', (1441.5, 2199.0, 40.1), (1424.0, 2207.0, 41.0), 26),
    # 巽橋 from its north end across the canal
    ('tatsumibashi', (1432.3, 2204.0, 40.2), (1434.6, 2184.0, 39.6), 26),
    # 新橋通 looking east (重伝建: uniform 庇, 千本格子, 2F 簾)
    ('shinbashi', (1300.0, 2225.0, 40.3), (1440.0, 2212.0, 41.2), 28),
    # the canal-side ochaya over the 白川 from the north bank (shirakawa__Kyoto_-_panoramio_7 / _9)
    ('shirakawa', (1364.0, 2181.2, 40.0), (1404.0, 2183.5, 38.6), 26),
    # 西楼門 across the 祇園 crossing from 四条通 (nishi-romon__Nishi-r_mon_Yasaka-jinja_20110910)
    ('nishiromon', (1662.0, 1987.0, 42.9), (1712.0, 1990.0, 46.8), 28),
    # 舞殿 lanterns with the 本殿 behind (yasaka-honden__Kyoto_Yasaka-jinja_Haupthalle_3)
    ('buden', (1786.0, 1938.0, 51.3), (1806.0, 1962.0, 54.0), 24),
    # 本殿 front with the 向拝
    ('honden', (1790.5, 1943.5, 51.4), (1804.0, 1972.0, 55.0), 26),
    # 南座 from 四条大橋 (shijo-ohashi__Kyoto_downtown_005)
    ('minamiza', (1180.0, 2008.0, 40.4), (1240.0, 1975.0, 50.0), 28),
    # 南座 front (minami-za__Kyoto_Theater_Minami-za_1)
    ('minamiza_front', (1243.0, 2003.0, 39.6), (1245.0, 1985.0, 50.0), 26),
    # 四条通 looking east with the arcade toward 八坂神社
    ('shijo', (1395.0, 1996.0, 40.3), (1560.0, 1993.0, 43.0), 30),
    # aerial over Gion from the north-west: 白川, 四条通, 花見小路, 八坂神社
    ('aerial', (1415.0, 2075.0, 92.0), (1600.0, 1972.0, 44.0), 30),
]

def build(B, S, only=None):
    preview_tints(B, S)
    parts = only or ['hanami', 'ichiriki', 'shijo', 'minamiza', 'shira', 'shrine']
    stats = {}
    used = set()
    if 'ichiriki' in parts:
        import sites.gion_ichiriki as GI
        GI.build(B, S, used)
    if 'hanami' in parts:
        hanami(B, S, used, stats)
    if 'minamiza' in parts:
        import sites.gion_minamiza as GM
        GM.build(B, S, used)
    if 'shijo' in parts:
        import sites.gion_shijo as GS
        GS.build(B, S, used, stats)
    if 'shira' in parts:
        import sites.gion_shirakawa as GW
        GW.build(B, S, used, stats)
    if 'shrine' in parts:
        import sites.gion_shrine as GY
        GY.build(B, S, used)
    print('gion stats', stats, 'excluded', len(S.exclude))

# ------------------------------------------------------------------ 花見小路
def hanami(B, S, used, stats):
    L = G.way_line(S, 27908626)                 # 花見小路 south of 四条 (from the corner to 建仁寺)
    picks = G.select(S, L, 7.0, used=used)
    # the first block's side alleys (the lanes off Hanamikoji) carry ochaya too
    for wid in (28020522, 28020527, 28020517, 28020509, 28020518, 28020525):
        try: La = G.way_line(S, wid)
        except KeyError: continue
        seg = shapely_cut(La, L, 34.0)
        if seg is None: continue
        for (b, P) in G.select(S, seg, 4.2, used=used):
            if all(b['id'] != q[0]['id'] for q in picks): picks.append((b, P));
    main = [(b, P) for (b, P) in picks if P.distance(L) < 7.0]
    side = [(b, P) for (b, P) in picks if P.distance(L) >= 7.0]
    lanes = []
    for wid in (28020522, 28020527, 28020517, 28020509, 28020518, 28020525, 1272492598, 28158796):
        try: lanes.append(G.way_line(S, wid))
        except KeyError: pass
    G.build_row(B, S, main, L, prefer='ochaya', seed0=101, used=used, stats=stats, styler=hanami_style, corner_lines=lanes, need=2.4)
    for wid in (28020522, 28020527, 28020517, 28020509, 28020518, 28020525):
        try: La = G.way_line(S, wid)
        except KeyError: continue
        seg = shapely_cut(La, L, 34.0)
        if seg is None: continue
        mine = [(b, P) for (b, P) in side if P.distance(seg) < 4.5 and b['id'] not in used]
        G.build_row(B, S, mine, seg, prefer='ochaya', seed0=wid % 997, used=used, stats=stats, styler=hanami_style, corner_lines=[L], need=1.5)
    # granite paving of the street and the lanes
    corridor = L.buffer(4.6, cap_style='flat')
    S.paint.append({'poly': ring_of(corridor), 'surf': 'stone_sett'})
    G.street_lamps(B, L, lambda x, y: float(S.ground(x, y)), spacing=17.0, offset=3.9, start=14.0)

def hanami_style(b, P, ring, rng):
    st = {}
    r = rng.random()
    if r < 0.12: st['wall'] = (178, 70, 48)            # a few 弁柄 red walls
    elif r < 0.2: st['wood'] = 'bengara'
    st['chochin'] = rng.random() < 0.7
    st['inuyarai'] = rng.random() < 0.75
    return st

def shapely_cut(La, L, length):
    """the part of side lane La within `length` of its junction with street L"""
    import shapely
    from shapely.geometry import Point
    if La.distance(L) > 3.0: return None
    a = Point(La.coords[0]); b = Point(La.coords[-1])
    if a.distance(L) <= b.distance(L):
        return shapely.ops.substring(La, 0, min(length, La.length))
    return shapely.ops.substring(La, max(0, La.length - length), La.length)

def ring_of(g):
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda p: p.area)
    return [list(map(float, c)) for c in list(g.exterior.coords)[:-1]]

# ------------------------------------------------------------------ preview colours
def preview_tints(B, S):
    """The kit's preview materials ignore the vertex tint (C0: plaster colours, 弁柄, noren, signs).  For truthful
    previews this registers a render_pre handler that adds the tint as a colour attribute to our meshes and multiplies
    it into every jk_ material (objects without a tint get white).  Only affects the Blender renders / .blend."""
    try:
        import bpy
    except Exception:
        return
    def s2l(c):
        c = c / 255.0
        return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    def apply(*_a):
        try:
            for ob in bpy.data.objects:
                if ob.type != 'MESH' or 'tint' in ob.data.color_attributes: continue
                me = ob.data
                tag = ob.get('jk_tag')
                col = None
                if tag and ob.name.startswith(B.name + '_'):
                    Mg = B.merged((tag,))
                    if Mg is not None and len(Mg['I']) == len(me.polygons):
                        c = s2l(Mg['C0'][Mg['I'].ravel()][:, :3].astype(float))
                        col = np.c_[c, np.ones(len(c))].astype(np.float32)
                at = me.color_attributes.new('tint', 'FLOAT_COLOR', 'CORNER')
                if col is None: col = np.ones((len(me.loops), 4), np.float32)
                at.data.foreach_set('color', col.ravel())
            # the preview terrain ignores S.cut (the canal would be buried): drop its faces inside the cuts
            import shapely
            from shapely.geometry import Polygon
            if S.cut:
                cut = shapely.unary_union([Polygon(r) for r in S.cut])
                zone = cut.buffer(9.0)
                done = False
                for ob in list(bpy.data.objects):
                    if ob.type != 'MESH' or not ob.name.startswith('terrain') or ob.get('cut_done'): continue
                    import bmesh
                    bm = bmesh.new(); bm.from_mesh(ob.data)
                    dead = [f for f in bm.faces if shapely.contains_xy(zone, *f.calc_center_median()[:2])]
                    bmesh.ops.delete(bm, geom=dead, context='FACES')
                    bm.to_mesh(ob.data); bm.free(); ob['cut_done'] = 1; done = True
                if done:
                    # a 1 m terrain patch around the cuts (the coarse 4 m preview grid cannot follow the canal)
                    x0, y0, x1, y1 = zone.bounds
                    xs = np.arange(math.floor(x0) - 4, x1 + 5, 1.0); ys = np.arange(math.floor(y0) - 4, y1 + 5, 1.0)
                    X, Y = np.meshgrid(xs, ys); Z = S.ground(X, Y) - 0.05
                    nx = len(xs)
                    cx = (X[:-1, :-1] + 0.5).ravel(); cy = (Y[:-1, :-1] + 0.5).ravel()
                    keep = shapely.contains_xy(zone.buffer(4.5), cx, cy) & ~shapely.contains_xy(cut, cx, cy)
                    jj, ii = np.divmod(np.nonzero(keep)[0], nx - 1)
                    a = jj * nx + ii
                    F = np.stack([a, a + 1, a + nx + 1, a + nx], 1)
                    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
                    me = bpy.data.meshes.new('terrain_patch'); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
                    me.materials.append(bpy.data.materials.get('jk_ground'))
                    for p in me.polygons: p.use_smooth = True
                    ob = bpy.data.objects.new('terrain_patch', me); ob['cut_done'] = 1
                    bpy.context.scene.collection.objects.link(ob)
                    at = me.color_attributes.new('tint', 'FLOAT_COLOR', 'CORNER'); at.data.foreach_set('color', np.ones(len(me.loops) * 4, np.float32))
            preview_trees(B)
            for m in bpy.data.materials:
                if not m.name.startswith('jk_') or m.get('tinted'): continue
                nt = m.node_tree; bs = nt.nodes.get('Principled BSDF')
                if bs is None: continue
                base = tuple(bs.inputs['Base Color'].default_value)
                rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = base
                at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'tint'
                mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
                nt.links.new(rgb.outputs[0], mx.inputs[6]); nt.links.new(at.outputs['Color'], mx.inputs[7])
                nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
                m['tinted'] = 1
        except Exception as e:
            print('preview tint failed', repr(e))
    for h in list(bpy.app.handlers.render_pre):
        if getattr(h, '__name__', '') == 'gion_tints': bpy.app.handlers.render_pre.remove(h)
    apply.__name__ = 'gion_tints'
    bpy.app.handlers.render_pre.append(apply)

def preview_trees(B):
    """stand-in crowns for the trees (the viewer draws them with its tree system; Blender previews would show none)"""
    import bpy
    if bpy.data.objects.get('gion_preview_trees') or not B.trees: return
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    # species: momiji ichou sakura keyaki matsu sugi hinoki kashi yanagi tsutsuji take -> (height, crown radius, crown base, colour)
    SP = {0: (7, 3.5, 2.0, (0.10, 0.20, 0.05)), 1: (14, 4.5, 3.0, (0.14, 0.22, 0.04)), 2: (7, 3.4, 2.8, (0.55, 0.42, 0.45)), 3: (14, 6.5, 3.5, (0.08, 0.16, 0.04)),
          4: (9, 3.8, 3.5, (0.04, 0.10, 0.03)), 5: (20, 3.0, 5.0, (0.03, 0.08, 0.03)), 6: (16, 3.0, 4.0, (0.03, 0.08, 0.03)), 7: (12, 5.5, 3.0, (0.04, 0.10, 0.03)),
          8: (8, 2.6, 2.6, (0.20, 0.34, 0.07)), 9: (1.2, 1.0, 0.0, (0.06, 0.14, 0.04)), 10: (8, 1.5, 2.0, (0.10, 0.20, 0.05))}
    groups = {}
    for (sp, x, y, z, s, yaw) in B.trees:
        h, r, cb, col = SP.get(int(sp), SP[3])
        P = V.copy()
        if int(sp) in (5, 6): P[:, 2] = P[:, 2] * (h - cb) / 2 * s; P[:, :2] *= r * s * np.clip(0.5 - V[:, 2:3] * 0.5, 0.05, 1.0)
        elif int(sp) == 8: P[:, :2] *= r * s; P[:, 2] *= (h - cb) / 2 * s; P[:, :2] *= np.clip(1.0 - V[:, 2:3] * 0.35, 0.6, 1.4)
        else: P[:, :2] *= r * s; P[:, 2] *= (h - cb) / 2 * s * 0.8
        P += [x, y, z + cb * s + (h - cb) / 2 * s]
        trunk = np.array([[x - 0.15 * s, y, z], [x + 0.15 * s, y, z], [x, y, z + (cb + 1.0) * s]])
        g = groups.setdefault(col, ([], []))
        off = sum(len(p) for p in g[0])
        g[0].append(P); g[1].append(F + off)
        g[0].append(trunk); g[1].append(np.array([[0, 1, 2]]) + off + len(P))
    for k, (col, (Ps, Fs)) in enumerate(groups.items()):
        Pv = np.concatenate(Ps); Fv = np.concatenate(Fs)
        me = bpy.data.meshes.new(f'gion_preview_trees_{k}')
        me.from_pydata(Pv.tolist(), [], Fv.tolist()); me.update()
        mat = bpy.data.materials.new(f'prev_leaf_{k}'); mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = 0.9
        me.materials.append(mat)
        ob = bpy.data.objects.new(f'gion_preview_trees' if k == 0 else f'gion_preview_trees_{k}', me)
        bpy.context.scene.collection.objects.link(ob)
