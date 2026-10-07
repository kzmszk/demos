"""東山 (Higashiyama): the old lanes between 清水寺 and 祇園 — 八坂通 with 八坂の塔 (法観寺五重塔) and 八坂庚申堂,
二年坂, 産寧坂 (with its stone steps), 一念坂, 清水坂 below the 仁王門 plaza, the top of 茶わん坂 / 五条坂, ねねの道 /
維新の道, 石塀小路 and the 台所坂 approach to 高台寺.

Town houses: sites/machiya.py on the PLATEAU footprints with the 東山 shop fronts (higashiyama_front), placed by
higashiyama_houses; lanes, paving, steps and gutters: higashiyama_lanes; the pagoda and 庚申堂: higashiyama_pagoda;
walls, gates, lamps, trees: higashiyama_props.
Run: blender -b --python blender/run_site.py -- higashiyama --shots [--only lanes,houses,pagoda,koshindo,props]"""
import sys, time, math
import numpy as np
import shapely
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
import sites.higashiyama_lanes as HL
import sites.higashiyama_houses as HH

SHOTS = []

def kiyomizu_exclude():
    import json, os
    p = '/home/kazu/work/kyoto-assets/heroes/kiyomizu.npz'
    if not os.path.exists(p): return []
    e = json.loads(bytes(np.load(p)['EDITS']).decode())
    return [Polygon(r) for r in e.get('exclude', [])]

def landuse(S, lid):
    for f in S.osm['landuse']:
        if f['id'] == lid: return Polygon(f['poly'][0][0])
    return None

def build(B, S, only=None):
    global SHOTS
    want = lambda p: only is None or p in only
    t0 = time.time()
    stats = {}
    kiyo = kiyomizu_exclude()
    hokanji = landuse(S, 371717423); koshin = landuse(S, 1316622873)
    protect = unary_union(kiyo + [g for g in (hokanji, koshin) if g is not None] + [sbox(1000, 1749.5, 3000, 3000)])
    lanes = HL.make(S, protect)
    lz = HL.LaneZ(S)
    HL.build(B, S, lanes, lz, stats, protect=unary_union(kiyo + [sbox(1000, 1749.5, 3000, 3000)]))
    print(f'lanes {time.time()-t0:.1f}s', stats, flush=True)
    if want('pagoda') or want('koshindo'):
        import sites.higashiyama_pagoda as HP
        if want('pagoda'): HP.pagoda(B, S, lz, stats)
        if want('koshindo'): HP.koshindo(B, S, lz, stats)
        print(f'pagoda {time.time()-t0:.1f}s', flush=True)
    if want('houses'):
        HH.build(B, S, lanes, lz, protect, stats)
        print(f'houses {time.time()-t0:.1f}s', stats, flush=True)
    if want('props'):
        import sites.higashiyama_props as HPR
        HPR.build(B, S, lanes, lz, protect, stats)
        print(f'props {time.time()-t0:.1f}s', flush=True)
    SHOTS = make_shots(S, lz, lanes)
    for sh in SHOTS: print('shot', sh[0], tuple(round(v, 1) for v in sh[1]), tuple(round(v, 1) for v in sh[2]), sh[3])
    if '--shots' in sys.argv:
        preview_tints(B, S)
    print('higashiyama stats', stats, 'excluded', len(S.exclude), 'paint', len(S.paint), f'{time.time()-t0:.1f}s', flush=True)

def make_shots(S, lz, lanes):
    import os
    sel = os.environ.get('HY_SHOTS')
    out = _shots(S, lz, lanes)
    return [s for s in out if s[0] in sel.split(',')] if sel else out

def _shots(S, lz, lanes):
    def lp(key, s, off=0.0):
        L = lanes[key]; s = s if s >= 0 else L.line.length + s
        p, d, n = L.frame(s); q = p + n * off
        return float(q[0]), float(q[1])
    def eye(key, s, off=0.0, h=1.6):
        x, y = lp(key, s, off); return (x, y, lz(x, y) + h)
    def look(key, s, off=0.0, dz=1.6):
        x, y = lp(key, s, off); return (x, y, lz(x, y) + dz)
    def at(x, y, dz): return (x, y, float(S.ground(x, y)) + dz)
    PAG = (1866.7, 1415.4)
    return [
        # 八坂通 looking east up to the pagoda (yasaka-to__GIO_..., Hokanji_Kyoto01n4272)
        ('yasaka_east', eye('yasaka', 15.0), at(*PAG, 17.0), 30),
        ('yasaka_east_near', eye('yasaka', 105.0), at(*PAG, 19.0), 24),
        # the upper 八坂通 looking down (west) to the pagoda (yasaka-to__Yasaka-dori_early_morning)
        ('yasaka_down', eye('yasaka_up', 112.0, 0.8), at(1866.0, 1413.0, 13.0), 26),
        # 二年坂 looking south toward the steps; and north down the lane
        ('ninen_south', eye('ninen', 62.0), look('ninen', 118.0, 0.0, 3.5), 26),
        ('ninen_north', eye('ninen', 112.0, 0.0, 1.8), look('ninen', 50.0, 0.0, 0.5), 26),
        # 産寧坂 steps looking up (sannen-zaka__JP_..._78a0, sannen-zaka__Dans_le_quartier)
        ('sannen_steps', eye('sannen', 38.5, 0.6), look('sannen', 8.0, 0.0, 1.8), 26),
        ('sannen_down', eye('sannen', 6.0, 0.0, 1.7), look('sannen', 60.0, 0.0, 0.0), 26),
        ('sannen_lane', eye('sannen', 190.0), look('sannen', 110.0, 0.0, 2.0), 28),
        # 清水坂 shops looking up to the 仁王門 (kiyomizu-zaka__Kiyomizuzaka_50910218063)
        ('kiyomizu_shops', eye('kiyomizu', 70.0), look('kiyomizu', 205.0, 0.0, 5.0), 28),
        # 石塀小路
        ('ishibe', eye('ishibe', 50.0), look('ishibe', 32.0, 0.0, 1.5), 26),
        ('ishibe_w', eye('ishibe', 95.0), look('ishibe', 68.0, 0.0, 1.5), 26),
        # ねねの道 looking north
        ('nene', eye('nene', 30.0, 1.5), look('nene', 150.0, 0.0, 2.0), 28),
        # 一念坂
        ('ichinen', eye('ichinen', 8.0), look('ichinen', 70.0, 0.0, 1.0), 26),
        # the pagoda from the lane south of it
        ('pagoda', eye('yasaka_up', 28.0), at(*PAG, 17.0), 22),
        # 八坂庚申堂 from 八坂通 (the gate with the くくり猿), the hall from the courtyard
        ('koshindo', (1823.0, 1420.5, lz(1823.0, 1420.5) + 1.6), (1822.6, 1405.0, lz(1822.6, 1405.0) + 2.2), 26),
        ('koshindo_hall', (1822.6, 1407.5, lz(1822.6, 1407.5) + 1.6), (1820.0, 1392.0, lz(1822.6, 1399.0) + 3.0), 24),
        # the pagoda over the roofs from the east (yasaka-to__Yasaka_pagoda_Kyoto_13406125105)
        ('pagoda_far', (1930.0, 1452.0, float(S.ground(1930.0, 1452.0)) + 14.0), at(*PAG, 22.0), 30),
        # shop fronts close up (二年坂, 産寧坂)
        ('ninen_shops', eye('ninen', 92.0, -0.8), look('ninen', 99.0, 3.0, 1.4), 24),
        ('sannen_shops', eye('sannen', 70.0, 0.8), look('sannen', 77.0, -3.0, 1.6), 24),
        # the top of 茶わん坂 and 五条坂 (shops below the 清水寺 approach)
        ('chawan', eye('chawan', 15.0), look('chawan', 70.0, 0.0, 1.5), 26),
        ('gojo', eye('gojo', 12.0), look('gojo', 90.0, 0.0, 0.0), 26),
        # 台所坂 from ねねの道 up to the 高台寺 gate
        ('daidokoro', eye('daidokoro', 1.0, 0.0, 1.6), look('daidokoro', 45.0, 0.0, 2.5), 26),
        # aerials
        ('aerial', (1760.0, 1250.0, 175.0), (1960.0, 1390.0, 65.0), 30),
        ('aerial_south', (2090.0, 1160.0, 150.0), (2020.0, 1280.0, 72.0), 28),
    ]

# ------------------------------------------------------------------ preview colours (copied from gion.preview_tints, cloth = tint)
def preview_tints(B, S):
    """The kit's preview materials ignore the vertex tint (C0).  A render_pre handler adds the tint as a colour
    attribute to our meshes and multiplies it into the jk_ materials (cloth takes the tint as its colour, like the viewer).
    Low-poly crowns stand in for the trees.  Only affects the Blender renders / .blend."""
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
            preview_trees(B)
            preview_neighbours()
            for m in bpy.data.materials:
                if not m.name.startswith('jk_') or m.get('tinted'): continue
                nt = m.node_tree; bs = nt.nodes.get('Principled BSDF')
                if bs is None: continue
                base = tuple(bs.inputs['Base Color'].default_value)
                if m.name == 'jk_cloth': base = (1.0, 1.0, 1.0, 1.0)
                if m.name in ('jk_lamp', 'jk_lantern_paper'):
                    bs.inputs['Emission Strength'].default_value = 2.5
                rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = base
                at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'tint'
                mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
                nt.links.new(rgb.outputs[0], mx.inputs[6]); nt.links.new(at.outputs['Color'], mx.inputs[7])
                nt.links.new(mx.outputs[2], bs.inputs['Base Color'])
                m['tinted'] = 1
        except Exception as e:
            print('preview tint failed', repr(e))
    for h in list(bpy.app.handlers.render_pre):
        if getattr(h, '__name__', '') == 'hy_tints': bpy.app.handlers.render_pre.remove(h)
    apply.__name__ = 'hy_tints'
    bpy.app.handlers.render_pre.append(apply)

def preview_neighbours():
    """the neighbouring hero sites (清水寺, 祇園) as plain context in the previews (not part of this site's export)"""
    import bpy, json, os
    if bpy.data.objects.get('hy_ctx_kiyomizu'): return
    mats = {m['id']: m for m in json.load(open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'public', 'data', 'materials.json')))['mats']}
    for name, box_ in (('kiyomizu', (2150, 1000, 2300, 1140)), ('gion', (1850, 1740, 2000, 1800))):
        p = f'/home/kazu/work/kyoto-assets/heroes/{name}.npz'
        if not os.path.exists(p): continue
        d = np.load(p)
        I = d['I'].astype(np.int64); P = d['P']
        C = P[I].mean(1)
        sel = (C[:, 0] > box_[0]) & (C[:, 0] < box_[2]) & (C[:, 1] > box_[1]) & (C[:, 1] < box_[3]) & (d['DETAIL'][I[:, 0]] == 0)
        I = I[sel]
        if not len(I): continue
        vid, inv = np.unique(I.ravel(), return_inverse=True)
        me = bpy.data.meshes.new('hy_ctx_' + name)
        me.from_pydata(P[vid].tolist(), [], inv.reshape(-1, 3).tolist()); me.update()
        mids = d['MAT'][vid][inv.reshape(-1, 3)[:, 0]]
        slots = {}
        for mid in np.unique(mids):
            m = bpy.data.materials.get('jk_' + mats[int(mid)]['name'])
            if m is None: continue
            slots[int(mid)] = len(me.materials); me.materials.append(m)
        me.polygons.foreach_set('material_index', np.array([slots.get(int(m_), 0) for m_ in mids], np.int32))
        ob = bpy.data.objects.new('hy_ctx_' + name, me); bpy.context.scene.collection.objects.link(ob)
        at = me.color_attributes.new('tint', 'FLOAT_COLOR', 'CORNER'); at.data.foreach_set('color', np.ones(len(me.loops) * 4, np.float32))

def preview_trees(B):
    import bpy
    if bpy.data.objects.get('hy_preview_trees') or not B.trees: return
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    SP = {0: (7, 3.5, 2.0, (0.45, 0.08, 0.03)), 1: (14, 4.5, 3.0, (0.5, 0.38, 0.05)), 2: (7, 3.4, 2.8, (0.3, 0.12, 0.08)), 3: (14, 6.5, 3.5, (0.25, 0.14, 0.04)),
          4: (9, 3.8, 3.5, (0.04, 0.10, 0.03)), 5: (20, 3.0, 5.0, (0.03, 0.08, 0.03)), 6: (16, 3.0, 4.0, (0.03, 0.08, 0.03)), 7: (12, 5.5, 3.0, (0.04, 0.10, 0.03)),
          8: (8, 2.6, 2.6, (0.25, 0.30, 0.07)), 9: (1.2, 1.0, 0.0, (0.06, 0.14, 0.04)), 10: (8, 1.5, 2.0, (0.10, 0.20, 0.05))}
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
        me = bpy.data.meshes.new(f'hy_preview_trees_{k}')
        me.from_pydata(Pv.tolist(), [], Fv.tolist()); me.update()
        mat = bpy.data.materials.new(f'hy_prev_leaf_{k}'); mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (*col, 1); bs.inputs['Roughness'].default_value = 0.9
        me.materials.append(mat)
        ob = bpy.data.objects.new('hy_preview_trees' if k == 0 else f'hy_preview_trees_{k}', me)
        bpy.context.scene.collection.objects.link(ob)
