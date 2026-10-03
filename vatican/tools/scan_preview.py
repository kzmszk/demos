"""import every STL, report size/axes, decimate to a preview and render a thumbnail from -Y (z up)."""
import bpy, sys, os, glob, math, json
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb import bl
from mathutils import Vector
SRC = '/home/kazu/work/vatican-assets/scans'
OUT = '/home/kazu/work/vatican-assets/scans/proc'
info = {}
for f in sorted(glob.glob(SRC + '/*.stl')):
    bl.clear_scene()
    bpy.ops.wm.stl_import(filepath=f)
    ob = bpy.context.selected_objects[0]
    me = ob.data
    nf = len(me.polygons)
    bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
    dims = [mx[i] - mn[i] for i in range(3)]
    mod = ob.modifiers.new('d', 'DECIMATE'); mod.ratio = min(1.0, 60000 / max(1, nf))
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='d')
    c = Vector([(mn[i] + mx[i]) / 2 for i in range(3)])
    s = 1.0 / max(dims)
    ob.location = -c * s; ob.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, scale=True)
    ob.data.materials.append(bl.material('statue'))
    bpy.ops.object.shade_smooth()
    bl.setup_world(sun_az_deg=150, sun_el_deg=40)
    name = os.path.basename(f)[:-4]
    for view, pos in (('y', (0, -2.6, 0.2)), ('z', (0, -0.01, 2.6))):
        bl.camera(pos, (0, 0, 0), 35)
        bl.render(f'{OUT}/{name}_{view}.jpg', 360, 360, 16)
    info[name] = {'faces': nf, 'dims': [round(d, 2) for d in dims]}
    print(name[:40], nf, [round(d, 1) for d in dims], flush=True)
json.dump(info, open(OUT + '/info.json', 'w'), indent=1)
