"""normalise + decimate the sculpture scans into LOD meshes (npz: V float32 (n,3), F int32 (m,3)).
Each result stands on z=0, centred on x=y=0, height 1.0 (scaled at placement), front = -y."""
import bpy, sys, os, glob, math, json
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb import bl
SRC = '/home/kazu/work/vatican-assets/scans'
OUT = '/home/kazu/work/vatican-assets/scans/lod'
os.makedirs(OUT, exist_ok=True)
# key: (file prefix, rotation (rx, rz) degrees, lod targets)
SPEC = {
    'apollo':    ('Apollo_Belvedere', (90, 0), (300000, 60000, 8000)),
    'christ':    ('Michelangelo_Buonarroti_Den_genopstandne', (0, 0), (120000, 25000, 5000)),
    'pieta':     ('Michelangelo_Buonarroti_Maria_med', (90, 0), (400000, 80000, 10000)),
    'torso':     ('Scan_the_World_-_Belvedere_Torso', (0, 0), (97000, 40000, 6000)),
    'ariadne':   ('Ubekendt_Den_sovende_Ariadne', (0, 0), (300000, 60000, 8000)),
    'discobolus': ('Ubekendt_Diskoskasteren', (0, 0), (250000, 50000, 8000)),
    'ecclesia':  ('Ubekendt_Ecclesia_sancta', (90, 0), (120000, 25000, 5000)),
    'francis':   ('Ubekendt_Frans_af_Assisi', (0, 0), (120000, 25000, 5000)),
    'baptist':   ('Ubekendt_Johannes_Døberen', (0, 0), (120000, 25000, 5000)),
    'laocoon':   ('Ubekendt_Laokoon', (0, 0), (400000, 80000, 10000)),
    'niobid':    ('Ubekendt_Niobide_Chiaramonti', (0, 0), (150000, 25000, 5000)),
    'pudicitia': ('Ubekendt_Stående_kvinde', (0, 0), (120000, 25000, 5000)),
    'polyhymnia': ('Ubekendt_Stående_muse_Polyhymnia', (0, 0), (120000, 25000, 5000)),
    'doryphoros': ('Ubekendt_Stående_nøgen_ung_mand', (0, 0), (200000, 40000, 6000)),
}
only = [a for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else []
meta = json.load(open(OUT + '/meta.json')) if os.path.exists(OUT + '/meta.json') else {}
for key, (prefix, (rx, rz), lods) in SPEC.items():
    if only and key not in only: continue
    f = [p for p in glob.glob(SRC + '/*.stl') if os.path.basename(p).startswith(prefix)][0]
    bl.clear_scene()
    bpy.ops.wm.stl_import(filepath=f)
    ob = bpy.context.selected_objects[0]
    ob.rotation_euler = (math.radians(rx), 0, math.radians(rz))
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(rotation=True)
    me = ob.data
    V = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', V); V = V.reshape(-1, 3)
    mn, mx = V.min(0), V.max(0); h = mx[2] - mn[2]
    # centre on the footprint of the lowest 5% (the plinth) so placement is on the base
    low = V[V[:, 2] < mn[2] + 0.05 * h]
    cx, cy = (low[:, 0].min() + low[:, 0].max()) / 2, (low[:, 1].min() + low[:, 1].max()) / 2
    V = (V - np.array([cx, cy, mn[2]])) / h
    me.vertices.foreach_set('co', V.ravel()); me.update()
    nf0 = len(me.polygons)
    meta[key] = {'src': os.path.basename(f), 'faces': nf0, 'aspect': [float((V[:, 0].max() - V[:, 0].min())), float(V[:, 1].max() - V[:, 1].min())]}
    for li, tgt in enumerate(lods):
        cp = ob.copy(); cp.data = ob.data.copy(); bpy.context.scene.collection.objects.link(cp)
        if tgt < nf0:
            mod = cp.modifiers.new('d', 'DECIMATE'); mod.ratio = tgt / nf0
            for o in bpy.context.scene.objects: o.select_set(False)
            cp.select_set(True); bpy.context.view_layer.objects.active = cp
            bpy.ops.object.modifier_apply(modifier='d')
        m2 = cp.data; m2.calc_loop_triangles()
        VV = np.zeros(len(m2.vertices) * 3, np.float32); m2.vertices.foreach_get('co', VV)
        FF = np.zeros(len(m2.loop_triangles) * 3, np.int32); m2.loop_triangles.foreach_get('vertices', FF)
        np.savez_compressed(f'{OUT}/{key}_{li}.npz', V=VV.reshape(-1, 3), F=FF.reshape(-1, 3))
        print(key, 'lod', li, len(FF) // 3, flush=True)
        bpy.data.objects.remove(cp, do_unlink=True)
    json.dump(meta, open(OUT + '/meta.json', 'w'), indent=1)
