"""Preview renders with the game's light (EEVEE, AgX)."""
import bpy, math
import numpy as np
from mathutils import Vector, Euler
import lib

SUN_DIR = np.array([-0.76, -0.40, 0.24])      # direction towards the sun (sun sits in the WSW, 15 deg high)
SUN_COL = np.array([1.48, 1.12, 0.80])
SKY = np.array([0.46, 0.55, 0.70]); GND = np.array([0.26, 0.28, 0.20]); HAZE = np.array([0.80, 0.72, 0.62])


def setup(scene, fog_density=0.0006, samples=32):
    scene.render.engine = 'BLENDER_EEVEE'
    ee = scene.eevee
    try:
        ee.taa_render_samples = samples
        ee.use_shadows = True
        ee.shadow_ray_count = 2
        ee.use_raytracing = False
        ee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    except Exception:
        pass
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.render.film_transparent = False
    # sun
    sd = bpy.data.lights.get('sun') or bpy.data.lights.new('sun', 'SUN')
    m = max(SUN_COL)
    sd.color = tuple(SUN_COL / m)
    sd.energy = float(m) * math.pi        # game: albedo x sun colour (hero colours x pi)
    sd.angle = math.radians(0.6)
    so = bpy.data.objects.get('sun') or bpy.data.objects.new('sun', sd)
    if so.name not in scene.collection.objects:
        scene.collection.objects.link(so)
    d = Vector(tuple(-SUN_DIR)).normalized()      # light travels away from the sun
    so.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    # world: hemisphere gradient (radiance = game hemisphere colour / pi), haze via volume-free mist mix
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W')
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value = -0.25; mr.inputs[2].default_value = 0.35
    nt.links.new(sep.outputs['Z'], mr.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(mr.outputs[0], mix.inputs['Factor'])
    mix.inputs["A"].default_value = (*(GND * 0.9), 1)
    mix.inputs["B"].default_value = (*(SKY * 0.9), 1)
    # camera-visible sky: hazy gradient brighter near the horizon (only for the backdrop)
    lp = nt.nodes.new('ShaderNodeLightPath')
    mr2 = nt.nodes.new('ShaderNodeMapRange'); mr2.inputs[1].default_value = -0.02; mr2.inputs[2].default_value = 0.22
    nt.links.new(sep.outputs['Z'], mr2.inputs[0])
    mixc = nt.nodes.new('ShaderNodeMix'); mixc.data_type = 'RGBA'
    nt.links.new(mr2.outputs[0], mixc.inputs['Factor'])
    mixc.inputs['A'].default_value = (*(HAZE * 0.95), 1)
    mixc.inputs['B'].default_value = (0.30, 0.45, 0.72, 1)
    mcam = nt.nodes.new('ShaderNodeMix'); mcam.data_type = 'RGBA'
    nt.links.new(lp.outputs['Is Camera Ray'], mcam.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], mcam.inputs['A'])
    nt.links.new(mixc.outputs['Result'], mcam.inputs['B'])
    bg = nt.nodes.new('ShaderNodeBackground'); nt.links.new(mcam.outputs['Result'], bg.inputs[0])
    out = nt.nodes.new('ShaderNodeOutputWorld'); nt.links.new(bg.outputs[0], out.inputs['Surface'])
    # fog: compositor mist mix
    scene.view_layers[0].use_pass_mist = True
    scene.view_layers[0].use_pass_z = True
    w.mist_settings.start = 30.0
    w.mist_settings.depth = 1.0 / fog_density
    w.mist_settings.falloff = 'QUADRATIC'
    _compositor(scene)


def _compositor(scene):
    try:
        ng = bpy.data.node_groups.new('comp', 'CompositorNodeTree')
        scene.compositing_node_group = ng
        nt = ng
        new_api = True
    except Exception:
        scene.use_nodes = True
        nt = scene.node_tree
        nt.nodes.clear()
        new_api = False
    rl = nt.nodes.new('CompositorNodeRLayers')
    mix = nt.nodes.new('ShaderNodeMix') if new_api else nt.nodes.new('CompositorNodeMixRGB')
    if new_api:
        mix.data_type = 'RGBA'
        mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MINIMUM'; mm.inputs[1].default_value = 0.6
        nt.links.new(rl.outputs['Mist'], mm.inputs[0])
        geo = nt.nodes.new('ShaderNodeMath'); geo.operation = 'LESS_THAN'; geo.inputs[1].default_value = 5000.0
        nt.links.new(rl.outputs['Depth'], geo.inputs[0])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
        nt.links.new(mm.outputs[0], mul.inputs[0]); nt.links.new(geo.outputs[0], mul.inputs[1])
        nt.links.new(mul.outputs[0], mix.inputs['Factor'])
        nt.links.new(rl.outputs['Image'], mix.inputs['A'])
        mix.inputs['B'].default_value = (*(HAZE * 0.75), 1)
        if not nt.interface.items_tree:
            nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
        go = nt.nodes.new('NodeGroupOutput')
        nt.links.new(mix.outputs['Result'], go.inputs[0])
    else:
        nt.links.new(rl.outputs['Mist'], mix.inputs[0])
        nt.links.new(rl.outputs['Image'], mix.inputs[1])
        mix.inputs[2].default_value = (*(HAZE * 0.75), 1)
        co = nt.nodes.new('CompositorNodeComposite')
        nt.links.new(mix.outputs[0], co.inputs[0])


def camera(scene, pos, target=None, heading=None, pitch=0.0, lens=24.0, name='cam'):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 6000
    co = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if co.name not in scene.collection.objects:
        scene.collection.objects.link(co)
    co.location = pos
    if target is not None:
        d = Vector(target) - Vector(pos)
    else:
        d = Vector((math.sin(heading) * math.cos(pitch), math.cos(heading) * math.cos(pitch), math.sin(pitch)))
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    return co


def shot(scene, path, w=1600, h=900):
    scene.render.resolution_x = w; scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)


def ground_material():
    """preview stand-in for the game's ground shader: asphalt on roads, moss/litter elsewhere (cover.png)"""
    m = bpy.data.materials.new('groundprev'); m.use_nodes = True
    nt = m.node_tree; P = nt.nodes['Principled BSDF']
    P.inputs['Roughness'].default_value = 0.95
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.vector_type = 'POINT'
    mp.inputs['Location'].default_value = (300.0 / 600.0, 310.0 / 620.0, 0)
    mp.inputs['Scale'].default_value = (1 / 600.0, 1 / 620.0, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    cv = nt.nodes.new('ShaderNodeTexImage'); cv.image = bpy.data.images.load(lib.SRC + 'cover.png'); cv.interpolation = 'Linear'
    cv.image.colorspace_settings.name = 'Non-Color'
    nt.links.new(mp.outputs['Vector'], cv.inputs['Vector'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(cv.outputs['Color'], sep.inputs[0])
    tm = nt.nodes.new('ShaderNodeMapping'); tm.inputs['Scale'].default_value = (1 / 9.0, 1 / 9.0, 1)
    nt.links.new(tc.outputs['Object'], tm.inputs['Vector'])
    top = nt.nodes.new('ShaderNodeTexImage'); top.image = bpy.data.images.load(lib.WORK + 'tex/top.png')
    nt.links.new(tm.outputs['Vector'], top.inputs['Vector'])
    road = nt.nodes.new('ShaderNodeMix'); road.data_type = 'RGBA'
    nt.links.new(sep.outputs[0], road.inputs['Factor'])
    nt.links.new(top.outputs['Color'], road.inputs['A'])
    road.inputs['B'].default_value = (0.13, 0.13, 0.12, 1)
    nt.links.new(road.outputs['Result'], P.inputs['Base Color'])
    return m
