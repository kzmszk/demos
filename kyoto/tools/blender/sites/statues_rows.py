"""preview: a section of the tiered stage with the standing Kannon variants (and optionally the guardians in front)
    blender -b --python blender/sites/statues_rows.py -- [lod] [out.png] [cam]"""
import sys, os, math
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
from sites import statues_mesh as M
OUT = '/home/kazu/work/kyoto-assets/heroes/statues'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
lod = int(argv[0]) if argv else 0
path = argv[1] if len(argv) > 1 else '/home/kazu/work/kyoto-assets/heroes/previews/statues_rows.png'
cam_kind = argv[2] if len(argv) > 2 else 'aisle'
sfx = '' if lod == 0 else f'_lod{lod}'
meshes = [M.npz_mesh(os.path.join(OUT, f'kannon_standing_{v}{sfx}.npz'), v) for v in 'abc']
col = bpy.context.scene.collection
rng = np.random.default_rng(3)
mat_st = bpy.data.materials.new('stage'); mat_st.use_nodes = True
mat_st.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.012, 0.01, 0.009, 1)
mat_st.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.3
ncol, ntier = 14, 6
for t in range(ntier):
    y = -t * 0.95; z = t * 0.23
    me = bpy.data.meshes.new(f'tier{t}')
    x0, x1 = -1.0, ncol * 1.0 + 1
    me.from_pydata([(x0, y - 0.95 + 0.47, z), (x1, y - 0.95 + 0.47, z), (x1, y + 0.47, z), (x0, y + 0.47, z), (x0, y + 0.47, z - 0.23), (x1, y + 0.47, z - 0.23)], [], [(0, 1, 2, 3), (3, 2, 5, 4)])
    ob = bpy.data.objects.new(f'tier{t}', me); col.objects.link(ob); me.materials.append(mat_st)
    for i in range(ncol):
        x = i * 1.0 + (0.5 if t % 2 else 0.0)
        mesh = meshes[int(rng.integers(0, 3))]
        ob = bpy.data.objects.new(f's{t}_{i}', mesh); col.objects.link(ob)
        ob.location = (x, y, z); ob.rotation_euler = (0, 0, rng.uniform(-0.04, 0.04))
M.setup_render(res=(1600, 1000), samples=32)
for o in [o for o in bpy.data.objects if o.name.startswith('pvL')]: bpy.data.objects.remove(o)
from mathutils import Vector
def area(name, pos, tgt, energy, colr, size):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = colr; ld.size = size
    lo = bpy.data.objects.new(name, ld); col.objects.link(lo)
    lo.location = pos; lo.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
# daylight through the east doors (in front of the stage), warm and dim
area('k1', (6, 6, 3.5), (6, -2, 1.5), 2500, (1.0, 0.8, 0.6), 6)
area('k2', (14, 5, 2.5), (8, -2, 1.5), 900, (1.0, 0.75, 0.5), 3)
area('fill', (-4, 2, 4), (6, -3, 1), 300, (0.8, 0.85, 1.0), 4)
if cam_kind == 'aisle':
    M.camera((-0.5, 3.2, 1.7), (6.5, -1.2, 1.6), 30, path)
else:
    M.camera((6.5, 4.0, 1.6), (6.5, -1.5, 1.9), 35, path)
