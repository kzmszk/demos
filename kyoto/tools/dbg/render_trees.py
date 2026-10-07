"""Debug: render tree templates in a row (Blender EEVEE).  blender -b --python dbg/render_trees.py -- NPZ ATLAS OUT.png [names]"""
import bpy, sys, math, numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
NPZ, ATLAS, OUT = argv[:3]
d = np.load(NPZ)
names = argv[3].split(',') if len(argv) > 3 else sorted({k.split('_')[0] for k in d.files})
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
img = bpy.data.images.load(ATLAS)
def leafmat(col_out, col_in):
    m = bpy.data.materials.new('leaf'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = img; tx.interpolation = 'Closest'
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tx.outputs['Color'], sep.inputs['Color'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (*col_in, 1); mix.inputs['B'].default_value = (*col_out, 1)
    nt.links.new(sep.outputs['Green'], mix.inputs['Factor'])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(mix.outputs['Result'], mul.inputs['A']); nt.links.new(sep.outputs['Red'], mul.inputs['B'])
    nt.links.new(mul.outputs['Result'], bs.inputs['Base Color']); nt.links.new(tx.outputs['Alpha'], bs.inputs['Alpha'])
    nt.links.new(bs.outputs['BSDF'], o.inputs['Surface'])
    m.blend_method = 'CLIP' if hasattr(m, 'blend_method') else None
    try: m.surface_render_method = 'DITHERED'
    except Exception: pass
    return m
COL = {'momiji': ((0.75, 0.05, 0.02), (0.8, 0.35, 0.03)), 'ichou': ((0.9, 0.7, 0.05), (0.8, 0.65, 0.1)), 'sakura': ((0.7, 0.2, 0.05), (0.5, 0.3, 0.08)),
       'keyaki': ((0.55, 0.22, 0.06), (0.45, 0.3, 0.1)), 'yanagi': ((0.55, 0.6, 0.15), (0.4, 0.5, 0.15))}
wood = bpy.data.materials.new('wood'); wood.use_nodes = True; wood.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.09, 0.07, 0.05, 1)
x = 0.0
for n in names:
    for part in ('wood', 'leaves'):
        P = d[f'{n}_{part}_P']; I = d[f'{n}_{part}_I'].reshape(-1, 3)
        me = bpy.data.meshes.new(n + part); me.vertices.add(len(P)); me.vertices.foreach_set('co', (P + [x, 0, 0]).ravel())
        me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
        me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32)); me.update(calc_edges=True)
        if part == 'leaves':
            UV = d[f'{n}_{part}_UV']; uvl = me.uv_layers.new(); uvl.data.foreach_set('uv', UV[I.ravel()].ravel())
            co, ci = COL.get(n, ((0.10, 0.22, 0.05), (0.08, 0.18, 0.04)))
            me.materials.append(leafmat(co, ci))
        else: me.materials.append(wood)
        ob = bpy.data.objects.new(n + part, me); sc.collection.objects.link(ob)
    x += 16.0
cd = bpy.data.cameras.new('c'); cd.lens = 28; co = bpy.data.objects.new('c', cd); sc.collection.objects.link(co); sc.camera = co
from mathutils import Vector
co.location = (x / 2 - 8, -0.55 * x - 10, 9); co.rotation_euler = (Vector((x / 2 - 8, 0, 8)) - Vector(co.location)).to_track_quat('-Z', 'Y').to_euler()
ld = bpy.data.lights.new('s', 'SUN'); ld.energy = 4; lo = bpy.data.objects.new('s', ld); sc.collection.objects.link(lo); lo.rotation_euler = (math.radians(50), 0, math.radians(-30))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.5, 0.6, 0.75, 1); w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 1800; sc.render.resolution_y = 520; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
