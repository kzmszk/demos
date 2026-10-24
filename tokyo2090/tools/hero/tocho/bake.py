"""Merge the near collection per draw group, lay out lightmap UVs ('LM') and bake ambient occlusion (Cycles, GPU).

Objects in 'near' carry a custom property 'grp' (export group = one mesh = one draw call per material) and
'lod' ('near', 'mid' or 'both'). Objects with 'inst' stay separate (linked duplicates -> GPU instancing).
"""
import bpy, bmesh, math, os
import numpy as np
import common as C
import materials as M

LM_GROUPS = {'facade': ('lm_facade', 2048), 'mat': ('lm_mat', 2048), 'detail': ('lm_detail', 2048)}


def merged(lod):
    return C.coll('merged_' + lod)


def merge(lod='near', log=print):
    src = bpy.data.collections['near']
    dst = merged(lod)
    for o in list(dst.objects): bpy.data.objects.remove(o, do_unlink=True)
    groups = {}
    for o in src.all_objects:
        if o.type != 'MESH' or o.get('inst'): continue
        l = o.get('lod', 'both')
        if l != 'both' and l != lod: continue
        groups.setdefault(o.get('grp', o.active_material.name.replace('M_', '') if o.active_material else 'misc'), []).append(o)
    out = {}
    for g, obs in groups.items():
        cps = []
        for o in obs:
            c = o.copy(); c.data = o.data.copy(); dst.objects.link(c); cps.append(c)
            if c.modifiers:
                bpy.context.view_layer.objects.active = c
                for m in list(c.modifiers):
                    with bpy.context.temp_override(object=c, active_object=c):
                        bpy.ops.object.modifier_apply(modifier=m.name)
        # join
        with bpy.context.temp_override(active_object=cps[0], selected_editable_objects=cps, selected_objects=cps):
            bpy.ops.object.join()
        j = cps[0]; j.name = g + ('' if lod == 'near' else '_' + lod); j.data.name = j.name
        out[g] = j
        log('merged', lod, g, len(obs), 'objects', len(j.data.polygons), 'faces')
    return out


def lightmap_uv(ob, margin=0.004):
    me = ob.data
    if 'LM' in me.uv_layers: me.uv_layers.remove(me.uv_layers['LM'])
    uv0 = me.uv_layers[0].name
    lm = me.uv_layers.new(name='LM')
    me.uv_layers.active = lm
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin_method='FRACTION', margin=margin, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers[uv0]
    for i, l in enumerate(me.uv_layers):
        l.active_render = (l.name == uv0)


def bake_ao(ob, image_name, size, samples=128, dist=12.0, log=print):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    sc.cycles.device = 'GPU'; sc.cycles.samples = samples
    if sc.world is None: sc.world = bpy.data.worlds.new('bakeworld')
    sc.world.light_settings.distance = dist
    im = bpy.data.images.get(image_name)
    if im is None or im.size[0] != size or im.source != 'GENERATED':
        if im: bpy.data.images.remove(im)
        im = bpy.data.images.new(image_name, size, size, alpha=False, float_buffer=False)
    im.colorspace_settings.name = 'Non-Color'
    me = ob.data
    me.uv_layers.active = me.uv_layers['LM']
    # make the LM image node active in every material of the object
    for m in me.materials:
        nt = m.node_tree
        n = nt.nodes.get('__bake') or nt.nodes.new('ShaderNodeTexImage'); n.name = '__bake'
        n.image = im; nt.nodes.active = n
    for o in bpy.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    sc.render.bake.margin = 6
    sc.render.bake.use_clear = True
    bpy.ops.object.bake(type='AO', margin=6, use_clear=True)
    # contrast curve: keep the open sky white, deepen crevices a little
    px = np.array(im.pixels[:]).reshape(size, size, 4)
    a = px[..., 0]
    a = np.clip(a, 0, 1) ** 1.25
    px[..., 0] = px[..., 1] = px[..., 2] = a
    im.pixels.foreach_set(px.ravel().astype(np.float32))
    im.filepath_raw = C.TEX + image_name + '.png'; im.file_format = 'PNG'; im.save()
    for m in me.materials:
        n = m.node_tree.nodes.get('__bake')
        if n: m.node_tree.nodes.remove(n)
    me.uv_layers.active = me.uv_layers[0]
    log('baked', image_name, ob.name)
    return im


def hide_for_bake(keep):
    """render visibility during AO bakes: geometry yes, foliage cards no (alpha would read as solid)"""
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        o.hide_render = o.name.startswith(('foliage_', 'vines', 'decal_', 'leaf')) or o.get('noao', False)


def run(log=print):
    bpy.ops.wm.open_mainfile(filepath=C.WORK + 'tocho.blend')
    near = merge('near', log)
    for o in bpy.data.objects:
        if o.type == 'MESH': o.hide_render = True
    for o in merged('near').objects: o.hide_render = False
    g = bpy.data.objects.get('ground')
    if g: g.hide_render = False
    for o in merged('near').objects:
        if o.name.startswith(('foliage_', 'vines', 'decal_', 'glass_', 'water')): o.hide_render = True
    for grp, (img, size) in LM_GROUPS.items():
        if grp in near:
            lightmap_uv(near[grp])
            bake_ao(near[grp], img, size, log=log)
    for name, _ in LM_GROUPS.values():
        im = bpy.data.images.get(name)
        if im and os.path.exists(C.TEX + name + '.png'):
            im.filepath = C.TEX + name + '.png'; im.source = 'FILE'; im.reload()
    for m in bpy.data.materials:
        if m.get('lm') and m.node_tree and m.node_tree.nodes.get('lm'):
            m.node_tree.nodes['lm'].image = bpy.data.images.get(m['lm'])
    # mid: same meshes for the lightmapped groups (lod 'both' only), its own merge for the rest
    mid = merge('mid', log)
    for grp in LM_GROUPS:
        if grp in near and grp in mid:
            mid[grp].data = near[grp].data.copy(); mid[grp].data.name = grp + '_mid'
    # mid budget: collapse the MAT shell meshes (LM uvs are interpolated; fine at 350-900 m)
    def tri(o):
        o.data.calc_loop_triangles(); return len(o.data.loop_triangles)
    inst_mid = 0
    for o in bpy.data.collections['near'].all_objects:
        if o.get('inst') and o.type == 'MESH' and o.get('lod') in ('mid', 'both'): inst_mid += tri(o)
    rest = sum(tri(o) for k, o in mid.items() if k != 'mat')
    if 'mat' in mid:
        room = 116000 - inst_mid - rest
        r = max(0.2, min(1.0, room / max(1, tri(mid['mat']))))
        log('mid: instanced', inst_mid, 'rest', rest, 'mat ratio', round(r, 2))
        if r < 1.0:
            o = mid['mat']
            m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = r
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_apply(modifier='dec')
    for o in bpy.data.objects:
        o.hide_render = False
    import far
    far.run(log)
    C.save()
