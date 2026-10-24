"""Preview renders lit like the game.

Game model: one sun (1.48, 1.12, 0.80) toward WSW 15 deg high with shadows, a hemisphere light sky (0.46, 0.55, 0.70) /
ground (0.26, 0.28, 0.20), the baked AO darkening only that ambient term, ACES filmic (exposure 1.05), FogExp2 0.00034.
Cycles with no diffuse bounces reproduces exactly that: direct sun + sky light occluded by the geometry (the 'true'
version of the baked AO), nothing else. The game multiplies hero albedo by pi, so: sun strength = 1.48*pi, world strength 1 (radiance = albedo * irradiance).
"""
import bpy, math
from mathutils import Vector
import common as C

SUN_DIR = Vector((-0.76, -0.40, 0.24)).normalized()   # direction TO the sun (WSW, 15 deg high); light travels -SUN_DIR
SUN_COL = (1.48, 1.12, 0.80)
SKY = (0.46, 0.55, 0.70)
GND = (0.26, 0.28, 0.20)
FOG = (0.80, 0.72, 0.62)
FOG_DEN = 0.00034


def setup(samples=48, res=(1600, 900)):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 1
    sc.cycles.transparent_max_bounces = 16; sc.cycles.transmission_bounces = 0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'ACES 1.3'
    sc.view_settings.exposure = math.log2(1.05 / 0.6)
    sc.view_settings.look = 'None'
    # world: lighting gradient seen by surfaces, a hazy sky seen by the camera
    w = bpy.data.worlds.get('game') or bpy.data.worlds.new('game')
    sc.world = w
    w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sepz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sepz.inputs[0])
    # hemisphere: smooth mix like three's 0.5 + 0.5 * n.z over the visible half -> step at horizon is fine for a sky
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.05; mr.inputs['From Max'].default_value = 0.05
    nt.links.new(sepz.outputs[2], mr.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = GND + (1,); mix.inputs[7].default_value = SKY + (1,)
    nt.links.new(mr.outputs[0], mix.inputs[0])
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs[1].default_value = 1.0
    nt.links.new(mix.outputs[2], bg.inputs[0])
    # camera sky: haze at the horizon to blue overhead
    mr2 = nt.nodes.new('ShaderNodeMapRange'); mr2.inputs['From Min'].default_value = 0.0; mr2.inputs['From Max'].default_value = 0.6
    nt.links.new(sepz.outputs[2], mr2.inputs['Value'])
    mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'
    mix2.inputs[6].default_value = (0.86, 0.76, 0.62, 1); mix2.inputs[7].default_value = (0.34, 0.47, 0.68, 1)
    nt.links.new(mr2.outputs[0], mix2.inputs[0])
    bg2 = nt.nodes.new('ShaderNodeBackground'); bg2.inputs[1].default_value = 0.62
    nt.links.new(mix2.outputs[2], bg2.inputs[0])
    lp = nt.nodes.new('ShaderNodeLightPath')
    ms = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], ms.inputs[0]); nt.links.new(bg.outputs[0], ms.inputs[1]); nt.links.new(bg2.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    # sun
    so = bpy.data.objects.get('SUN')
    if so is None:
        L = bpy.data.lights.new('SUN', 'SUN'); so = bpy.data.objects.new('SUN', L); sc.collection.objects.link(so)
    L = so.data
    mx = max(SUN_COL)
    L.color = tuple(c / mx for c in SUN_COL); L.energy = mx * math.pi; L.angle = math.radians(0.6)
    so.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    # fog in the compositor from the depth pass
    sc.view_layers[0].use_pass_z = True
    ng = bpy.data.node_groups.get('fog') or bpy.data.node_groups.new('fog', 'CompositorNodeTree')
    ng.nodes.clear()
    if not ng.interface.items_tree:
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers')
    m1 = ng.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = FOG_DEN
    ng.links.new(rl.outputs['Depth'], m1.inputs[0])
    m2 = ng.nodes.new('ShaderNodeMath'); m2.operation = 'POWER'; m2.inputs[1].default_value = 2.0
    ng.links.new(m1.outputs[0], m2.inputs[0])
    m3 = ng.nodes.new('ShaderNodeMath'); m3.operation = 'EXPONENT'
    m4 = ng.nodes.new('ShaderNodeMath'); m4.operation = 'MULTIPLY'; m4.inputs[1].default_value = -1
    ng.links.new(m2.outputs[0], m4.inputs[0]); ng.links.new(m4.outputs[0], m3.inputs[0])
    m5 = ng.nodes.new('ShaderNodeMath'); m5.operation = 'SUBTRACT'; m5.inputs[0].default_value = 1.0
    ng.links.new(m3.outputs[0], m5.inputs[1])
    m6 = ng.nodes.new('ShaderNodeMath'); m6.operation = 'MINIMUM'; m6.inputs[1].default_value = 0.85
    ng.links.new(m5.outputs[0], m6.inputs[0])
    mx_ = ng.nodes.new('ShaderNodeMix'); mx_.data_type = 'RGBA'
    ng.links.new(m6.outputs[0], mx_.inputs[0]); ng.links.new(rl.outputs['Image'], mx_.inputs[6])
    # fog colour in scene-linear radiance comparable to the lit scene (three adds fogColor after lighting, pre-tonemap)
    mx_.inputs[7].default_value = FOG + (1,)
    go = ng.nodes.new('NodeGroupOutput'); ng.links.new(mx_.outputs[2], go.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    cam = bpy.data.objects.get('CAM')
    if cam is None:
        cd = bpy.data.cameras.new('CAM'); cam = bpy.data.objects.new('CAM', cd); sc.collection.objects.link(cam)
    cam.data.clip_start = 0.1; cam.data.clip_end = 20000
    sc.camera = cam
    return cam


def shot(path, pos, target, lens=24, res=None):
    sc = bpy.context.scene
    cam = sc.camera
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.filepath = path
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)


def heading_shot(path, x, y, heading, pitch=0.0, eye=1.6, lens=20, res=None):
    """street-level view: heading 0 = north, +pi/2 = east (game convention)"""
    z = C.ground(x, y) + eye
    d = Vector((math.sin(heading) * math.cos(pitch), math.cos(heading) * math.cos(pitch), math.sin(pitch)))
    shot(path, (x, y, z), Vector((x, y, z)) + d * 100, lens, res)
