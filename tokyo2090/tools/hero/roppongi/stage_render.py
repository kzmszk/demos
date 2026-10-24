"""Preview renders (public/hero/roppongi/previews/): street level from the spawns, aerial 3/4, aerial with context."""
import bpy, math, json, os
import lib, render, bl
import stage_export


def preview_ao(mat):
    """EEVEE ignores glTF occlusion: for previews multiply base colour by AO (ORM.R, or the foliage vertex colour)"""
    nt = mat.node_tree
    P = nt.nodes.get('Principled BSDF')
    base = nt.nodes.get('base')
    if P is None or base is None:
        return
    src = None
    orm = nt.nodes.get('orm')
    if orm is not None and mat.name not in ('interior',):
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sep.inputs[0]); src = sep.outputs[0]
    elif mat.name == 'leaves':
        a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'Col'; src = a.outputs['Color']
    if src is None:
        return
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 0.75
    nt.links.new(base.outputs['Color'], mix.inputs['A']); nt.links.new(src, mix.inputs['B'])
    nt.links.new(mix.outputs['Result'], P.inputs['Base Color'])


def run(log):
    bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'baked.blend')
    scene = bpy.context.scene
    render.setup(scene, samples=48)
    for m in bpy.data.materials:
        if m.use_nodes:
            preview_ao(m)
    g = bpy.data.objects.get('ground')
    if g is not None and not g.data.materials:
        g.data.materials.append(render.ground_material())
    out = lib.OUT + 'previews/'
    os.makedirs(out, exist_ok=True)
    G = lib.Ground()
    shots = []
    for i, sp in enumerate(stage_export.SPAWNS):
        x, y, h = sp['x'], sp['y'], sp['heading']
        z = lib.PLAZA_Z if i == 0 else float(G(x, y))
        pitch = (0.30, -0.06, 0.05)[i]
        lens = (17, 22, 22)[i]
        shots.append(('street_%d_%s' % (i + 1, ['plaza', 'garden', 'keyakizaka'][i]), (x, y, z + 1.6), None, h + (0.0, 0.15, 0.0)[i], pitch, lens))
    shots.append(('aerial_34', (230.0, -235.0, 125.0), (-25.0, 25.0, 55.0), None, 0, 26))
    shots.append(('aerial_tower_tear', (-300.0, 260.0, 210.0), (-49.0, 49.0, 200.0), None, 0, 30))
    for name, pos, tgt, h, pitch, lens in shots:
        render.camera(scene, pos, tgt, heading=h, pitch=pitch, lens=lens)
        render.shot(scene, out + name + '.png', 1600, 900)
        log('preview', name)
    # with the neighbourhood
    objs = bl.import_obj(lib.SRC + 'context.obj', bl.collection('ref'))
    m = bpy.data.materials.new('ctxprev'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.45, 0.45, 0.43, 1)
    for o in objs:
        o.data.materials.append(m)
    render.camera(scene, (420.0, -380.0, 260.0), (-20.0, 20.0, 40.0), lens=26)
    render.shot(scene, out + 'aerial_context.png', 1600, 900)
    log('preview aerial_context')
