"""Preview renders (Cycles, lit like the game, see render.py) -> public/hero/tocho/previews/."""
import bpy, math
import common as C
import render as R
import hero_meta

OUT = C.PUB + 'previews/'


def ground_material():
    m = bpy.data.materials.get('pv_ground') or bpy.data.materials.new('pv_ground')
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.05; nz.inputs['Detail'].default_value = 8
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.055, 0.055, 0.05, 1)
    ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (0.06, 0.09, 0.03, 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.92
    return m


def visibility(context=False):
    for o in bpy.data.objects: o.hide_render = True
    for o in bpy.data.collections['near'].all_objects:
        o.hide_render = o.get('lod') == 'mid'
    g = bpy.data.objects.get('ground')
    if g:
        g.hide_render = False
        g.data.materials.clear(); g.data.materials.append(ground_material())
    if context:
        for o in bpy.data.collections['context'].objects: o.hide_render = False
    if bpy.data.objects.get('SUN'): bpy.data.objects['SUN'].hide_render = False
    if bpy.data.objects.get('CAM'): bpy.data.objects['CAM'].hide_render = False


def run(log=print):
    bpy.ops.wm.open_mainfile(filepath=C.WORK + 'tocho.blend')
    R.setup(samples=64, res=(1600, 900))
    visibility(context=True)
    sp = {s['name']: s for s in hero_meta.SPAWNS}
    shots = []
    for i, s in enumerate(hero_meta.SPAWNS):
        pitch = 0.32 if i in (0, 2) else 0.16
        R.heading_shot(OUT + 'street_%d.png' % (i + 1), s['x'], s['y'], s['heading'], pitch, eye=1.6, lens=16)
        log('preview street', i + 1)
    R.shot(OUT + 'aerial_sw.png', (-230, -135, 160), (-25, 45, 95), 26)
    log('preview aerial')
    R.shot(OUT + 'aerial_east_800m.png', (800, 40, 185), (-38, 58, 160), 30)
    log('preview east 800')
    R.shot(OUT + 'context_ne.png', (330, 420, 300), (-20, 20, 60), 24)
    R.shot(OUT + 'context_sw.png', (-420, -420, 330), (-10, 10, 70), 24)
    log('preview context')
    # crown close-up from the air (north-east, the broken side)
    R.shot(OUT + 'crown.png', (60, 230, 262), (-42, 92, 232), 32)
    log('preview crown')
