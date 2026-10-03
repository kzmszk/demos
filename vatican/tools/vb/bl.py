"""Blender side: Mesh -> objects, preview materials, quick renders."""
import bpy, math, os
import numpy as np
from mathutils import Vector, Euler

# preview albedos (linear) for material names (prefix match on 'name:...' too)
ALBEDO = {
    'travertine': (0.50, 0.44, 0.33), 'travertine_dark': (0.36, 0.31, 0.23), 'travertine_light': (0.58, 0.53, 0.43),
    'stucco': (0.70, 0.62, 0.48), 'plaster_ochre': (0.62, 0.45, 0.25), 'plaster_red': (0.48, 0.24, 0.14),
    'plaster_yellow': (0.70, 0.55, 0.30), 'facade_ochre': (0.60, 0.42, 0.24), 'facade_red': (0.50, 0.26, 0.16), 'facade_yellow': (0.68, 0.53, 0.30), 'facade_white': (0.70, 0.66, 0.58), 'facade_trav': (0.55, 0.50, 0.40), 'plaster_white': (0.75, 0.72, 0.65), 'brick': (0.42, 0.22, 0.13),
    'lead': (0.30, 0.31, 0.32), 'lead_dome': (0.30, 0.33, 0.36), 'lead_rib': (0.46, 0.47, 0.47), 'roof_tile': (0.50, 0.24, 0.13), 'marble_white': (0.80, 0.78, 0.74), 'marble_int': (0.42, 0.30, 0.26), 'marble_dark': (0.22, 0.12, 0.10), 'marble_pil': (0.58, 0.55, 0.52), 'stucco_white': (0.66, 0.62, 0.54), 'gold_dull': (0.55, 0.40, 0.15), 'gloria': (1.0, 0.85, 0.45), 'mosaic_blue': (0.06, 0.08, 0.16),
    'marble_grey': (0.50, 0.50, 0.50), 'bronze': (0.25, 0.17, 0.08), 'gold': (0.85, 0.65, 0.25),
    'glass': (0.05, 0.06, 0.07), 'granite': (0.35, 0.32, 0.30), 'sampietrini': (0.28, 0.27, 0.26),
    'asphalt': (0.12, 0.12, 0.12), 'grass': (0.12, 0.20, 0.06), 'lawn': (0.10, 0.17, 0.05), 'foliage': (0.07, 0.12, 0.04), 'foliage_dark': (0.04, 0.08, 0.03), 'foliage_light': (0.09, 0.15, 0.05), 'bark': (0.16, 0.11, 0.08), 'bark_light': (0.32, 0.29, 0.22), 'water': (0.02, 0.04, 0.05), 'water_fall': (0.55, 0.6, 0.62),
    'ground': (0.30, 0.26, 0.20), 'gravel': (0.45, 0.42, 0.36), 'iron': (0.05, 0.05, 0.05), 'wood': (0.25, 0.14, 0.07),
    'white': (0.8, 0.8, 0.8), 'statue': (0.56, 0.53, 0.47), 'porphyry': (0.25, 0.07, 0.07), 'gilt_bronze': (0.62, 0.45, 0.16), 'bronze_green': (0.12, 0.16, 0.12), 'stucco_ochre': (0.62, 0.45, 0.26), 'velarium': (0.92, 0.9, 0.85), 'terracotta': (0.5, 0.22, 0.12), 'glass_pane': (0.02, 0.025, 0.03), 'glass_dome': (0.55, 0.62, 0.66), 'momo_wall': (0.62, 0.58, 0.5), 'statue_marble': (0.78, 0.76, 0.72), 'obelisk': (0.55, 0.45, 0.38),
}


def albedo(name):
    if name in ALBEDO: return ALBEDO[name]
    base = name.split(':')[0]
    return ALBEDO.get(base, (0.6, 0.6, 0.6))


_mats = {}


def material(name):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    c = albedo(name)
    bsdf.inputs['Base Color'].default_value = (*c, 1)
    rough = 0.8
    if name in ('bronze', 'gold', 'iron'): rough = 0.4      # baked as dielectrics (a metallic BSDF has no diffuse pass)
    if name in ('glass', 'water'): rough = 0.05
    if name.startswith('marble'): rough = 0.3
    bsdf.inputs['Roughness'].default_value = rough
    if name == 'gloria':
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.8, 0.35, 1); bsdf.inputs['Emission Strength'].default_value = 25.0
    if name.startswith('art:'):
        import os
        f = f'/home/kazu/work/demos/vatican/public/art/{name[4:]}.jpg'
        if os.path.exists(f):
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(f, check_existing=True)
            tex.extension = 'REPEAT'
            nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
            bsdf.inputs['Roughness'].default_value = 0.9
    _mats[name] = m
    return m


def to_object(mesh, name, collection=None, smooth_angle=35.0):
    V = np.array(mesh.V, dtype=np.float32).reshape(-1, 3)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', V.ravel())
    sizes = np.array([len(f) for f in mesh.F], dtype=np.int32)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32)
    me.loops.add(int(sizes.sum()))
    me.loops.foreach_set('vertex_index', np.concatenate(mesh.F).astype(np.int32) if mesh.F else np.zeros(0, np.int32))
    me.polygons.add(len(mesh.F))
    me.polygons.foreach_set('loop_start', starts)
    # materials
    names = sorted(set(mesh.M))
    for n in names: me.materials.append(material(n))
    lut = {n: i for i, n in enumerate(names)}
    me.polygons.foreach_set('material_index', np.array([lut[m] for m in mesh.M], dtype=np.int32))
    me.polygons.foreach_set('use_smooth', np.array(mesh.S, dtype=bool))
    # explicit uvs
    if any(u is not None for u in mesh.UV):
        uvl = me.uv_layers.new(name='UVMap')
        arr = np.zeros((int(sizes.sum()), 2), np.float32)
        for fi, uv in enumerate(mesh.UV):
            if uv is not None:
                arr[starts[fi]:starts[fi] + sizes[fi]] = uv
        uvl.data.foreach_set('uv', arr.ravel())
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    if any(mesh.S):
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def clear_scene():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    _mats.clear()


def setup_world(sun_az_deg=115, sun_el_deg=38, strength=1.0, sun=True):
    """Nishita sky + matching sun lamp. azimuth measured from north, clockwise (115 = ESE)."""
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new('World'); sc.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    sky = nt.nodes.new('ShaderNodeTexSky')
    try: sky.sky_type = 'NISHITA'
    except Exception: pass
    try:
        sky.sun_elevation = math.radians(sun_el_deg)
        # Nishita rotation: 0 = sun toward +y? blender: sun_rotation rotates around z from +x
        sky.sun_rotation = math.radians(90 - sun_az_deg)
        sky.sun_disc = False
        sky.air_density = 1.0; sky.dust_density = 2.0
    except Exception as e: print('sky', e)
    bg.inputs['Strength'].default_value = strength * 0.065
    nt.links.new(sky.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o, do_unlink=True)
    if sun:
        ld = bpy.data.lights.new('Sun', 'SUN'); ld.energy = 4.0 * strength; ld.angle = math.radians(0.53)
        ob = bpy.data.objects.new('Sun', ld); sc.collection.objects.link(ob)
        az = math.radians(sun_az_deg); el = math.radians(sun_el_deg)
        d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))  # toward sun
        ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return w


def camera(pos, look, lens=24, name='Cam'):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens; cd.clip_start = 0.1; cd.clip_end = 20000
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob)
    ob.location = pos
    d = Vector(look) - Vector(pos)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = ob
    return ob


def render(path, w=1600, h=900, samples=64, engine='CYCLES'):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    if engine == 'CYCLES':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
            for d in prefs.devices: d.use = (d.type == 'OPTIX')
            sc.cycles.device = 'GPU'
        except Exception as e: print('gpu', e)
        sc.cycles.samples = samples; sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 4
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
