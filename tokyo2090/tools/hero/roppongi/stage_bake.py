"""UV1 lightmap layout + Cycles AO bake per ORM atlas -> work/bake/orm_<group>.png, baked.blend"""
import bpy, math, os
import numpy as np
import lib, bl

GROUPS = {}
for m, spec in bl.MATS.items():
    if spec.get('orm'):
        GROUPS.setdefault(spec['orm'], []).append(m)


def objects_of(mats):
    return [o for o in bpy.data.collections['near'].objects if o.type == 'MESH' and o.data.materials
            and o.data.materials[0].name in mats]


UVW = {'bark': 0.45, 'metal': 0.7, 'car': 2.2, 'bronze': 3.0, 'signs': 2.0, 'top': 0.6, 'pave': 0.8,
       'conc': 1.0, 'fac': 1.0, 'tower': 1.0, 'tconc': 0.8}


def weld(o):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bm.to_mesh(o.data); bm.free()


def uv1_layout(objs, margin):
    for o in objs:
        weld(o)
    for o in objs:
        me = o.data
        if 'UV1' not in me.uv_layers:
            me.uv_layers.new(name='UV1')
        me.uv_layers.active = me.uv_layers['UV1']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        w = UVW.get(o.data.materials[0].name, 1.0) ** 0.5
        uv = np.zeros(len(o.data.loops) * 2, np.float32); o.data.uv_layers['UV1'].data.foreach_get('uv', uv)
        o.data.uv_layers['UV1'].data.foreach_set('uv', uv * w)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, scale=True, margin_method='FRACTION',
                            margin=margin, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        o.data.uv_layers.active = o.data.uv_layers['UV0']
        o.data.uv_layers['UV0'].active_render = True


def run(log):
    sfx = '_mid' if lib.mid() else ''
    bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'geo%s.blend' % sfx)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type in ('OPTIX', 'CUDA')
        scene.cycles.device = 'GPU'
    except Exception as e:
        log('GPU setup failed', e)
    scene.cycles.samples = 96
    scene.world = scene.world or bpy.data.worlds.new('W')
    # foliage / decals / glass don't occlude in the AO bake
    for o in bpy.data.objects:
        if o.name.startswith(('foliage_', 'decal_', 'glass_')):
            o.hide_render = True
    for grp, mats in GROUPS.items():
        objs = objects_of(mats)
        if not objs:
            continue
        log('bake group', grp, [o.name for o in objs])
        size = bl.ORM_SIZE[grp] // (2 if lib.mid() else 1)
        uv1_layout(objs, 0.0015)
        log('  uv1 done')
        img = bpy.data.images.get('orm_' + grp)
        img.scale(size, size)
        img.colorspace_settings.name = 'Non-Color'
        # make the orm node active in each material
        for o in objs:
            nt = o.data.materials[0].node_tree
            nt.nodes.active = nt.nodes['orm']
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
            o.data.uv_layers.active = o.data.uv_layers['UV1']     # cycles bakes into the active UV map
        bpy.context.view_layer.objects.active = objs[0]
        scene.render.bake.margin = 6
        scene.render.bake.use_clear = True
        scene.world.light_settings.distance = 12.0
        bpy.ops.object.bake(type='AO', use_clear=True, margin=6)
        log('  ao baked')
        for o in objs:
            o.data.uv_layers.active = o.data.uv_layers['UV0']
        px = np.array(img.pixels[:], np.float32).reshape(size, size, 4)
        ao = px[..., 0].copy()
        # roughness / metal per material: rasterise UV1 islands per object into a material-id map
        rough = np.full((size, size), 0.9, np.float32); metal = np.zeros((size, size), np.float32)
        for o in objs:
            spec = bl.MATS[o.data.materials[0].name]
            me = o.data
            uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers['UV1'].data.foreach_get('uv', uv)
            uv = uv.reshape(-1, 2)
            # bounding boxes of islands are enough at this granularity: paint per polygon bbox
            ls = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
            lt = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', lt)
            for s, t in zip(ls, lt):
                q = uv[s:s + t]
                x0, y0 = (q.min(0) * size).astype(int); x1, y1 = (q.max(0) * size).astype(int) + 1
                rough[max(y0, 0):y1, max(x0, 0):x1] = spec['rough']
                metal[max(y0, 0):y1, max(x0, 0):x1] = spec['metal']
        # AO shaping: keep contact darkness, lift the floor a little
        ao = np.clip(ao, 0, 1) ** 1.1
        out = np.dstack([ao, rough, metal, np.ones_like(ao)])
        img.pixels.foreach_set(out.ravel())
        img.filepath_raw = lib.WORK + 'bake/orm_%s%s.png' % (grp, sfx)
        img.file_format = 'PNG'
        img.save()
        log('  saved', img.filepath_raw)
    for o in bpy.data.objects:
        o.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=lib.WORK + 'baked%s.blend' % sfx)
