"""OSM massing for every building/part not replaced by a hero model.  Run inside Blender:
blender -b --python build_city.py -- <out_base> [--test]"""
import sys, math, json
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
import numpy as np
import bpy, bmesh
from osm import OSMData, num
from vb.geom import *
from vb import terrain

o = OSMData()

# hero replacements: OSM ids whose geometry we model by hand (filled in as heroes are built)
HERO_WAYS = set(json.load(open('/home/kazu/work/demos/vatican/tools/hero_ids.json'))) if __import__('os').path.exists('/home/kazu/work/demos/vatican/tools/hero_ids.json') else set()

ROOF_DEFAULT = 'hip'

def poly_area(P):
    return abs(signed_area(P))

def clean_ring(P):
    out = []
    for p in P:
        if not out or math.dist(p, out[-1]) > 0.05: out.append(p)
    if len(out) > 2 and math.dist(out[0], out[-1]) < 0.05: out.pop()
    return out

def material_for(t, part=False):
    c = (t.get('building:colour') or t.get('colour') or '').lower()
    mat = t.get('building:material', '')
    b = t.get('building', '')
    if mat in ('stone', 'marble') or c in ('lightyellow', 'beige', 'white', 'ivory'):
        return 'facade_trav'
    if mat == 'brick' or c in ('brown', 'darkred', 'maroon'):
        return 'brick'
    if c in ('orange', 'peru', 'sandybrown', 'darkorange', 'chocolate'):
        return 'facade_ochre'
    if c in ('red', 'indianred', 'firebrick', 'brown'):
        return 'facade_red'
    if c in ('yellow', 'gold', 'khaki', 'wheat'):
        return 'facade_yellow'
    return None

def pick_plaster(seed):
    r = (seed * 2654435761) % 1000 / 1000
    if r < 0.40: return 'facade_ochre'
    if r < 0.62: return 'facade_yellow'
    if r < 0.80: return 'facade_red'
    if r < 0.92: return 'facade_white'
    return 'facade_trav'

def hip_roof(m, loops, z, rise, mat):
    """inset-based roof: slopes from the outline to an inset ring, flat top (Roman terrace roof)."""
    outer = ccw(loops[0])
    # build a single ngon at z, inset it with bmesh for robustness on concave outlines
    bm = bmesh.new()
    vs = [bm.verts.new((p[0], p[1], z)) for p in outer]
    try:
        f = bm.faces.new(vs)
    except Exception:
        bm.free(); m.merge(cap(loops, z, mat, True)); return
    area = poly_area(outer)
    # short side estimate from area / perimeter
    per = sum(math.dist(outer[i], outer[(i + 1) % len(outer)]) for i in range(len(outer)))
    half_w = 2 * area / max(per, 1e-3)
    d = min(half_w * 0.95, 9.0)
    h = d * math.tan(math.radians(rise))
    res = bmesh.ops.inset_region(bm, faces=[f], thickness=d, depth=h, use_even_offset=True, use_boundary=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], ngon_method='EAR_CLIP')
    o0 = len(m.V)
    idx = {}
    for v in bm.verts:
        idx[v.index] = len(m.V); m.V.append(list(v.co))
    for fc in bm.faces:
        nz = fc.normal.z
        m.face([idx[v.index] for v in fc.verts], mat if nz < 0.999 else mat, False)
    bm.free()

def extrude(m, loops, zb, zt, wall_mat, roof, roof_mat, roof_h=None):
    loops = [clean_ring(L) for L in loops]
    loops = [L for L in loops if len(L) >= 3]
    if not loops or poly_area(loops[0]) < 2: return
    m.merge(prism(loops, zb, zt, wall_mat, top=False))
    if roof == 'flat' or roof_h == 0:
        m.merge(cap(loops, zt, roof_mat if roof_mat != 'roof_tile' else 'roof_flat', True))
    elif roof == 'dome':
        L = loops[0]
        cx = sum(p[0] for p in L) / len(L); cy = sum(p[1] for p in L) / len(L)
        r = sum(math.dist(p, (cx, cy)) for p in L) / len(L)
        rh = roof_h or r
        prof = [(r * math.cos(a), zt + rh * math.sin(a)) for a in np.linspace(0, math.pi / 2, 9)]
        m.merge(lathe(prof, 24, mat=roof_mat, center=(cx, cy, 0)))
    elif roof == 'pyramidal':
        L = ccw(loops[0])
        cx = sum(p[0] for p in L) / len(L); cy = sum(p[1] for p in L) / len(L)
        rh = roof_h or 3
        ap = m.add_v([(cx, cy, zt + rh)])
        o2 = m.add_v([(p[0], p[1], zt) for p in L])
        for i in range(len(L)):
            m.face([o2 + i, o2 + (i + 1) % len(L), ap], roof_mat)
    else:
        if len(loops) > 1:  # courtyards: slope toward both edges is hard; use flat + low parapet
            m.merge(cap(loops, zt, 'roof_flat', True)); return
        hip_roof(m, loops, zt, 24, roof_mat)

def pip(pt, poly):
    x, y = pt; inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): inside = not inside
    return inside

def part_centroids():
    cs = []
    for wid, w in o.ways.items():
        if 'building:part' in w.get('tags', {}):
            P = o.way_xy(wid)
            if P: cs.append((sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P)))
    for rid, r in o.rels.items():
        if 'building:part' in r.get('tags', {}):
            for ring in o.rel_rings(rid)['outer']:
                if ring: cs.append((sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)))
    return cs

def build(test=False):
    m = Mesh()
    n = 0
    PC = part_centroids()
    def has_parts(L):
        xs = [p[0] for p in L]; ys = [p[1] for p in L]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        return any(x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and pip(c, L) for c in PC)
    def emit(eid, loops, t, is_part):
        nonlocal n
        if eid in HERO_WAYS: return
        if t.get('building') in ('no',) or t.get('building:part') in ('no',): return
        if t.get('location') == 'underground' or t.get('layer', '0').startswith('-'): return
        lv = num(t.get('building:levels'))
        h = num(t.get('height')) or (lv * 3.6 + 2 if lv else None)
        if h is None:
            h = 7 if t.get('building') in ('roof', 'shed', 'kiosk', 'garage', 'hut') else 17
        if t.get('building') == 'roof': return
        if not is_part and has_parts(loops[0]): return
        mh = num(t.get('min_height')) or 0
        if h - mh < 0.3: return
        L0 = loops[0]
        cx = sum(p[0] for p in L0) / len(L0); cy = sum(p[1] for p in L0) / len(L0)
        g = terrain.height(cx, cy)
        gmin = min(terrain.height(p[0], p[1]) for p in L0)
        zb = (gmin - 3) if mh == 0 else g + mh
        roof = t.get('roof:shape') or (ROOF_DEFAULT if not is_part else 'flat')
        rh = num(t.get('roof:height'))
        zt = g + h - (rh if roof in ('dome', 'pyramidal', 'gabled', 'hipped') and rh else 0)
        wall = material_for(t) or pick_plaster(eid)
        rc = (t.get('roof:colour') or '').lower()
        rmat = 'roof_tile'
        if rc in ('grey', 'gray', 'darkgrey', 'silver', 'lightgrey'): rmat = 'lead'
        if roof == 'dome': rmat = 'lead'
        if roof in ('gabled', 'hipped'): roof = 'hip'
        extrude(m, loops, zb, zt, wall, roof, rmat, rh)
        n += 1
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if not ('building' in t or 'building:part' in t): continue
        if w['nodes'][0] != w['nodes'][-1]: continue
        # skip a building outline if it has parts (parts carry the 3D shape)
        pts = o.way_xy(wid)[:-1]
        if len(pts) < 3: continue
        emit(wid, [pts], t, 'building:part' in t)
    for rid, r in o.rels.items():
        t = r.get('tags', {})
        if not ('building' in t or 'building:part' in t) or t.get('type') != 'multipolygon': continue
        rings = o.rel_rings(rid)
        for outer in rings['outer']:
            if len(outer) < 4: continue
            emit(rid, [outer[:-1] if outer[0] == outer[-1] else outer] + [h[:-1] for h in rings['inner'] if len(h) > 3], t, 'building:part' in t)
    print('buildings', n, 'mesh', m.count())
    return m

if __name__ == '__main__':
    out = sys.argv[sys.argv.index('--') + 1]
    from vb import bl, bake
    bl.clear_scene()
    m = build()
    ob = bl.to_object(m, 'city')
    g = terrain.mesh(-1100, -900, 1100, 900, 8)
    gob = bl.to_object(g, 'ground')
    w = bl.setup_world()
    sun = bpy.data.objects['Sun']
    if '--render' in sys.argv:
        bl.camera((300, -500, 300), (-200, 0, 30), 30)
        bl.render(out + '.jpg', 1600, 900, 32)
    else:
        bake.densify_soup(ob, 5.0); bake.densify_soup(gob, 10.0)
        bake.bake_irradiance([ob, gob], sun, samples=128)
        bake.export_npz([ob, gob], out)
