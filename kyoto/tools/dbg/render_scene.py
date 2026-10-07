"""helpers for quick Blender preview renders of jk builds"""
import bpy, math
from mathutils import Vector
def setup(res=(1600, 900), engine='EEVEE', sun=(240, 12), strength=4.0, sky=(0.45, 0.55, 0.75)):
    sc = bpy.context.scene
    names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
    if engine == 'CYCLES':
        sc.render.engine = 'CYCLES'; sc.cycles.samples = 64; sc.cycles.device = 'GPU'
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*sky, 1); bg.inputs['Strength'].default_value = 1.0
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = strength; ld.angle = math.radians(1.0)
    lo = bpy.data.objects.new('sun', ld); sc.collection.objects.link(lo)
    az, el = math.radians(sun[0]), math.radians(sun[1])
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    lo.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    try: sc.view_settings.view_transform = 'AgX'
    except Exception: pass
def shot(path, cam, tgt, lens=35):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get('cam') or bpy.data.cameras.new('cam'); cd.lens = lens; cd.clip_end = 5000
    co = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', cd)
    if co.name not in sc.collection.objects: sc.collection.objects.link(co)
    sc.camera = co; co.location = cam; co.rotation_euler = (Vector(tgt) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
