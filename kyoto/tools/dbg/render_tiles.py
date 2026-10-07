"""Debug: render tile npz meshes in Blender (workbench, material colours).
blender -b --python dbg/render_tiles.py -- BUILD_DIR OUT.png cam_x cam_y cam_z tgt_x tgt_y tgt_z [tiles,...] [lens]"""
import bpy, sys, os, json, math
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
B, OUT = argv[0], argv[1]
cam = list(map(float, argv[2:5])); tgt = list(map(float, argv[5:8]))
names = argv[8].split(',') if len(argv) > 8 and argv[8] else [m['name'] for m in json.load(open(os.path.join(B, 'tiles.json')))]
lens = float(argv[9]) if len(argv) > 9 else 35
mats = json.load(open(os.path.join(B, 'materials.json')))['mats']
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def srgb(c): return [min(1, max(0, v)) ** (1 / 2.2) for v in c]
mlist = []
for m in mats:
    mm = bpy.data.materials.new(m['name']); a = [min(1.0, (v * 1.6) ** (1 / 2.2)) for v in m['albedo']]; mm.diffuse_color = (*a, 1) if m['kind'] not in ('ground',) else (0.55, 0.53, 0.5, 1)
    mlist.append(mm)
for n in names:
    p = os.path.join(B, n + '.npz')
    if not os.path.exists(p): continue
    d = np.load(p)
    P, I, M = d['P'], d['I'], d['MAT']
    me = bpy.data.meshes.new(n); me.vertices.add(len(P)); me.vertices.foreach_set('co', P.ravel())
    me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
    me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32))
    for mm in mlist: me.materials.append(mm)
    me.polygons.foreach_set('material_index', M[I[:, 0]].astype(np.int32))
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(n, me); sc.collection.objects.link(ob)
cd = bpy.data.cameras.new('c'); cd.lens = lens; cd.clip_end = 20000
co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
from mathutils import Vector
co.location = cam; co.rotation_euler = (Vector(tgt) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
sc.render.engine = 'BLENDER_WORKBENCH'
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.35, 0.55, 0.95)
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_shadows = True; sc.display.shading.show_cavity = True
sc.display.light_direction = (-0.6, -0.3, 0.75)
sc.render.resolution_x = 1600; sc.render.resolution_y = 900
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
