"""far.glb: the silhouette (<= 25k tris), one material, one 2048 atlas with albedo x AO baked from the mid LOD."""
import bpy, bmesh, json, math, os
import numpy as np
import lib

ARCH = ('fac', 'tower', 'top', 'conc', 'pave', 'tconc')
TARGET = 19000


def run(log):
    bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'baked_mid.blend')
    scene = bpy.context.scene
    near = bpy.data.collections['near']
    src = [o for o in near.objects if o.type == 'MESH']
    farc = bpy.data.collections.new('far'); scene.collection.children.link(farc)
    # ---- architecture: copy, join, weld, decimate
    parts = []
    for o in src:
        if o.name in ARCH:
            c = o.copy(); c.data = o.data.copy(); farc.objects.link(c); parts.append(c)
    bpy.ops.object.select_all(action='DESELECT')
    for c in parts:
        c.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    arch = bpy.context.view_layer.objects.active
    arch.name = 'far'
    me = arch.data
    for l in list(me.uv_layers):
        me.uv_layers.remove(l)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.08)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    n0 = len(me.polygons)
    m = arch.modifiers.new('dec', 'DECIMATE'); m.ratio = min(1.0, TARGET * 0.78 / max(n0, 1))
    bpy.ops.object.modifier_apply(modifier='dec')
    log('far arch', n0, '->', len(arch.data.polygons))
    # ---- tree crowns as low blobs
    ctx = json.load(open(lib.WORK + 'ctx.json'))
    bm = bmesh.new()
    for (x, y, z, R, Rz) in ctx.get('crowns', []):
        if R < 2.0:
            continue
        ico = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
        for v in ico['verts']:
            v.co = (x + v.co.x * R * 0.9, y + v.co.y * R * 0.9, z + v.co.z * Rz * 0.85)
    blobs = bpy.data.meshes.new('crowns'); bm.to_mesh(blobs); bm.free()
    bo = bpy.data.objects.new('crowns', blobs); farc.objects.link(bo)
    log('crowns', len(blobs.polygons))
    if len(blobs.polygons) + len(arch.data.polygons) > 24500:
        m = bo.modifiers.new('dec', 'DECIMATE'); m.ratio = max(0.2, (24500 - len(arch.data.polygons)) / len(blobs.polygons))
        bpy.context.view_layer.objects.active = bo; bpy.ops.object.modifier_apply(modifier='dec')
    bpy.ops.object.select_all(action='DESELECT')
    arch.select_set(True); bo.select_set(True); bpy.context.view_layer.objects.active = arch
    bpy.ops.object.join()
    far = arch
    far.name = 'far'; far.data.name = 'far'
    far.data.materials.clear()
    # ---- UVs
    far.data.uv_layers.new(name='UV0')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method='FRACTION', margin=0.002, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    # ---- material + bake targets
    S = 2048
    col_img = bpy.data.images.new('far_col', S, S, alpha=False)
    ao_img = bpy.data.images.new('far_ao', S, S, alpha=False); ao_img.colorspace_settings.name = 'Non-Color'
    mat = bpy.data.materials.new('far'); mat.use_nodes = True
    nt = mat.node_tree; P = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = col_img
    nt.links.new(t.outputs['Color'], P.inputs['Base Color'])
    P.inputs['Roughness'].default_value = 0.9; P.inputs['Metallic'].default_value = 0.0
    P.inputs['Specular IOR Level'].default_value = 0.3
    far.data.materials.append(mat)
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type in ('OPTIX', 'CUDA')
        scene.cycles.device = 'GPU'
    except Exception:
        pass
    scene.cycles.samples = 16
    for o in src:
        o.hide_render = False
    # albedo from the mid LOD (selected -> active)
    nt.nodes.active = t
    bpy.ops.object.select_all(action='DESELECT')
    for o in src:
        if not o.name.startswith(('glass_', 'decal_water')):
            o.select_set(True)
    far.select_set(True); bpy.context.view_layer.objects.active = far
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 2.5
    scene.render.bake.max_ray_distance = 9.0
    scene.render.bake.margin = 4
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=2.5,
                        max_ray_distance=9.0, margin=4)
    log('far albedo baked')
    # AO on the far mesh itself
    t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = ao_img; nt.nodes.active = t2
    for o in src:
        o.hide_render = True
    bpy.ops.object.select_all(action='DESELECT'); far.select_set(True); bpy.context.view_layer.objects.active = far
    scene.render.bake.use_selected_to_active = False
    scene.cycles.samples = 64
    scene.world.light_settings.distance = 25.0
    bpy.ops.object.bake(type='AO', use_selected_to_active=False, margin=4)
    log('far ao baked')
    c = np.array(col_img.pixels[:], np.float32).reshape(S, S, 4)
    a = np.array(ao_img.pixels[:], np.float32).reshape(S, S, 4)[..., :1]
    c[..., :3] = c[..., :3] * (0.35 + 0.65 * a)
    col_img.pixels.foreach_set(c.ravel())
    col_img.filepath_raw = lib.WORK + 'bake/far_col.png'; col_img.file_format = 'PNG'; col_img.save()
    nt.nodes.remove(t2)
    # export
    for o in src:
        o.hide_render = False
    bpy.ops.object.select_all(action='DESELECT'); far.select_set(True); bpy.context.view_layer.objects.active = far
    bpy.ops.export_scene.gltf(filepath=lib.OUT + 'far.glb', export_format='GLB', use_selection=True,
                              export_image_format='WEBP', export_image_quality=80,
                              export_draco_mesh_compression_enable=True, export_draco_position_quantization=16,
                              export_yup=True, export_apply=True)
    import stage_export
    s = stage_export.glb_stats(lib.OUT + 'far.glb')
    log('far', s)
    hj = lib.OUT + 'hero.json'
    if os.path.exists(hj):
        d = json.load(open(hj)); d['stats'].update({'far_tris': s['tris'], 'far_mb': s['mb']})
        json.dump(d, open(hj, 'w'), ensure_ascii=False, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=lib.WORK + 'far.blend')
