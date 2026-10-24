"""Level-of-detail exports: mid (decimated, 1024 textures) and far (silhouette + one baked atlas)."""
import math
import os
import random

import bpy
import bmesh
import numpy as np

from sb_common import WORK, TEX, enable_gpu
import sb_mats

MID_DIR = os.path.join(WORK, 'mid_tex')
os.makedirs(MID_DIR, exist_ok=True)

MID_RATIO = {'facade_a': 0.5, 'facade_b': 0.5, 'concrete': 0.35, 'rubble': 0.3, 'metal': 0.3, 'props': 0.45,
             'signs': 1.0, 'decal_ground': 0.2, 'bronze': 0.2}


def _copy(ob, coll, name):
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    c.parent = None
    coll.objects.link(c)
    return c


def _decimate(ob, ratio):
    if ratio >= 0.999:
        return
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = ratio
    m.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier=m.name)


def _small_image(img, size):
    name = img.name.rsplit('.', 1)[0] + f'_{size}'
    path = os.path.join(MID_DIR, name + '.png')
    ex = bpy.data.images.get(name)
    if ex:
        return ex
    c = img.copy()
    c.name = name
    if c.size[0] > size:
        c.scale(size, size)
    c.filepath_raw = path
    c.file_format = 'PNG'
    c.save()
    return c


def _mid_material(m, size=1024):
    if m.name.endswith('_mid'):
        return m
    key = m.name + '_mid'
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    c = m.copy()
    c.name = key
    for n in c.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image is not None and n.image.size[0] > size:
            n.image = _small_image(n.image, size)
    return c


def thin_crown(me, keep=0.45, grow=1.3, seed=1):
    """a lighter crown: keep a fraction of the cards (quads), enlarged about their centres"""
    rnd = random.Random(seed)
    bm = bmesh.new(); bm.from_mesh(me)
    dele = []
    for f in bm.faces:
        if rnd.random() > keep:
            dele.append(f)
        else:
            c = f.calc_center_median()
            for v in f.verts:
                pass
    bmesh.ops.delete(bm, geom=dele, context='FACES')
    for f in bm.faces:
        c = f.calc_center_median()
        for l in f.loops:
            pass
    # grow each remaining face about its centre (verts are not shared between cards)
    for f in bm.faces:
        c = f.calc_center_median()
        for v in f.verts:
            v.co = c + (v.co - c) * grow
    new = me.copy()
    new.name = me.name + '_mid'
    bm.to_mesh(new); bm.free()
    return new


def make_mid(near_coll):
    mid = bpy.data.collections.get('MID') or bpy.data.collections.new('MID')
    if mid.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(mid)
    objs = []
    tree_meshes = {}
    for ob in list(near_coll.all_objects):
        if ob.type == 'EMPTY':
            continue
        if ob.name.startswith('foliage_plants'):
            continue
        if ob.parent is not None and ob.parent.type == 'EMPTY':
            # instanced tree part
            me = ob.data
            if me.name not in tree_meshes:
                if me.name.startswith('treeC_'):
                    tree_meshes[me.name] = thin_crown(me, keep=0.4, grow=1.32)
                else:
                    tm = me.copy(); tm.name = me.name + '_mid'
                    tmp = bpy.data.objects.new('tmp', tm); bpy.context.scene.collection.objects.link(tmp)
                    _decimate(tmp, 0.35)
                    bpy.data.objects.remove(tmp)
                    tree_meshes[me.name] = tm
            pe = ob.parent
            ename = pe.name + '_mid'
            e = bpy.data.objects.get(ename)
            if e is None:
                e = bpy.data.objects.new(ename, None); mid.objects.link(e)
            c = bpy.data.objects.new(ob.name + '_m', tree_meshes[me.name])
            mid.objects.link(c)
            c.parent = e
            c.matrix_world = ob.matrix_world.copy()
            objs.append(c)
            continue
        key = ob.active_material.name if ob.active_material else ''
        c = _copy(ob, mid, ob.name + '_mid')
        _decimate(c, MID_RATIO.get(key, 0.4))
        objs.append(c)
    for o in mid.all_objects:
        if o.type == 'MESH':
            for i, s in enumerate(o.material_slots):
                if s.material is not None:
                    o.data.materials[i] = _mid_material(s.material)
    for me in tree_meshes.values():
        for i, m in enumerate(me.materials):
            if m is not None:
                me.materials[i] = _mid_material(m)
    return [o for o in mid.all_objects]


# ------------------------------------------------------------------ far
def make_far(near_coll, ratio_bldg=0.05, atlas=2048, samples=64):
    """silhouette level: decimated buildings + blob crowns, one baked atlas (albedo x AO)"""
    import time
    T0 = time.time()
    far = bpy.data.collections.get('FAR') or bpy.data.collections.new('FAR')
    if far.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(far)
    src = [o for o in near_coll.all_objects if o.type == 'MESH' and o.parent is None and not o.name.startswith(('decal', 'foliage', 'roots'))]
    parts = []
    for ob in src:
        key = ob.active_material.name if ob.active_material else ''
        if key in ('signs', 'metal'):
            continue
        c = _copy(ob, far, ob.name + '_far')
        r = {'facade_a': ratio_bldg, 'facade_b': ratio_bldg, 'concrete': ratio_bldg * 0.8, 'rubble': 0.03,
             'props': 0.05, 'bronze': 0.02}.get(key, 0.05)
        _decimate(c, r)
        parts.append(c)
    print(f'  far: decimated {len(parts)} parts {time.time() - T0:.0f}s', flush=True)
    # tree crowns as low blobs with a plain green material
    green = bpy.data.materials.new('far_green')
    green.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.055, 0.085, 0.022, 1)
    bm = bmesh.new()
    for ob in near_coll.all_objects:
        if ob.type == 'MESH' and ob.parent is not None and ob.data.name.startswith('treeC_'):
            me = ob.data
            vs = np.array([ob.matrix_world @ v.co for v in me.vertices])
            lo = vs.min(0); hi = vs.max(0)
            c = (lo + hi) / 2; r = (hi - lo) / 2 * 0.85
            ico = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
            for v in ico['verts']:
                v.co.x = c[0] + v.co.x * r[0]; v.co.y = c[1] + v.co.y * r[1]; v.co.z = c[2] + v.co.z * r[2] * 0.8
    tme = bpy.data.meshes.new('far_trees'); bm.to_mesh(tme); bm.free()
    tme.uv_layers.new(name='UVMap')
    tme.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER').data.foreach_set('color', np.ones(len(tme.loops) * 4, np.float32))
    tme.materials.append(green)
    to = bpy.data.objects.new('far_trees', tme); far.objects.link(to); parts.append(to)
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    fo = bpy.context.view_layer.objects.active
    fo.name = 'far'
    me = fo.data
    if 'UV1' in me.uv_layers:
        me.uv_layers.remove(me.uv_layers['UV1'])
    uvf = me.uv_layers.new(name='UVFar')
    me.uv_layers.active = uvf
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002)
    bpy.ops.object.mode_set(mode='OBJECT')
    print('far tris', sum(len(p.vertices) - 2 for p in me.polygons), f'{time.time() - T0:.0f}s', flush=True)
    # bake the diffuse colour of its own (near) materials into the atlas through UVFar
    img = bpy.data.images.new('far_atlas', atlas, atlas, alpha=False, float_buffer=True)
    targets = []
    for m in me.materials:
        if m is None:
            continue
        tn = m.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = img
        m.node_tree.nodes.active = tn
        targets.append((m, tn))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'GPU'; sc.cycles.samples = 8
    sc.render.bake.margin = 4
    for o in near_coll.all_objects:
        if o is not None:
            o.hide_render = True
    bpy.ops.object.select_all(action='DESELECT'); fo.select_set(True); bpy.context.view_layer.objects.active = fo
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=False, margin=4)
    print(f'  far: albedo baked {time.time() - T0:.0f}s', flush=True)
    alb = np.empty(atlas * atlas * 4, np.float32); img.pixels.foreach_get(alb); alb = alb.reshape(atlas, atlas, 4)
    ao = bpy.data.images.new('far_ao', atlas, atlas, alpha=False, float_buffer=True)
    for m, tn in targets:
        tn.image = ao
    sc.cycles.samples = samples
    sc.world.light_settings.distance = 10.0
    bpy.ops.object.bake(type='AO', use_selected_to_active=False, margin=4)
    print(f'  far: ao baked {time.time() - T0:.0f}s', flush=True)
    a2 = np.empty(atlas * atlas * 4, np.float32); ao.pixels.foreach_get(a2); a2 = a2.reshape(atlas, atlas, 4)
    for o in near_coll.all_objects:
        if o is not None:
            o.hide_render = False
    out = alb.copy()
    out[..., :3] = alb[..., :3] * (0.35 + 0.65 * a2[..., :1])
    out[..., 3] = 1
    from sb_texlib import save_png
    p = os.path.join(TEX, 'far.png')
    save_png(out[::-1], p)
    # one material, one UV set
    final = bpy.data.images.load(p)
    mat = bpy.data.materials.new('far')
    nt = mat.node_tree
    bs = nt.nodes['Principled BSDF']
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = final
    nt.links.new(tn.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.92
    me.materials.clear(); me.materials.append(mat)
    for l in [l for l in me.uv_layers if l.name != 'UVFar']:
        me.uv_layers.remove(l)
    me.uv_layers['UVFar'].name = 'UVMap'
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    bpy.data.images.remove(img); bpy.data.images.remove(ao)
    return fo
