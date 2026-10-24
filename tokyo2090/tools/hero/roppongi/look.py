"""Debug renders from geo.blend (or a given blend):
   blender -b -P look.py -- [--blend f] [--ctx] [--samples n] name x y z tx ty tz lens [name ...]
Writes work/scratch/<name>.png (1200x700)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import lib, render, bl

a = sys.argv[sys.argv.index('--') + 1:]
blend = lib.WORK + 'geo.blend'
with_ctx = False
samples = 16
W, H = 1200, 700
while a and a[0].startswith('--'):
    k = a.pop(0)
    if k == '--blend':
        blend = a.pop(0)
    elif k == '--ctx':
        with_ctx = True
    elif k == '--samples':
        samples = int(a.pop(0))
    elif k == '--ao':
        pass
    elif k == '--size':
        W = int(a.pop(0)); H = int(a.pop(0))
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
render.setup(scene, samples=samples)
if '--ao' in sys.argv:
    import stage_render
    for m in bpy.data.materials:
        if m.use_nodes:
            stage_render.preview_ao(m)
g = bpy.data.objects.get('ground')
if g is not None and not g.data.materials:
    g.data.materials.append(render.ground_material())
if with_ctx and bpy.data.objects.get('c_ctx') is None:
    objs = bl.import_obj(lib.SRC + 'context.obj', bl.collection('ref'))
    m = bpy.data.materials.new('ctxprev'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.42, 0.40, 1)
    for o in objs:
        o.data.materials.append(m)
while len(a) >= 8:
    name = a[0]; x, y, z, tx, ty, tz, lens = map(float, a[1:8]); a = a[8:]
    render.camera(scene, (x, y, z), (tx, ty, tz), lens=lens)
    render.shot(scene, lib.WORK + 'scratch/%s.png' % name, W, H)
