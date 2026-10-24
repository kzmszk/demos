"""far.glb: the silhouette (<= 25 k triangles, one material, one 2048 atlas with colour x AO baked from the near model).

Buildings + plaza structures + rubble come from the merged near meshes, planar-dissolved (the atlas grid cuts go
away) and collapsed where still too dense; tree canopies become low blobs coloured from a reserved strip of the atlas.
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector
import common as C
import textures as T

ATL = 2048
TARGET = 23500
STRIP = 0.06          # top 6 % of the atlas: foliage colours for the canopy blobs


def tris(o):
    o.data.calc_loop_triangles(); return len(o.data.loop_triangles)


def simplify_copy(src, name, col, ratio=None):
    o = src.copy(); o.data = src.data.copy(); o.name = name; o.data.name = name
    col.objects.link(o)
    for k in list(o.keys()): del o[k]
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2.0), verts=bm.verts, edges=bm.edges, delimit=set())
    bm.to_mesh(o.data); bm.free()
    if ratio:
        m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = ratio
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_apply(modifier='dec')
    while len(o.data.uv_layers): o.data.uv_layers.remove(o.data.uv_layers[0])
    return o


def blobs(col, R):
    """canopy blobs for the instanced trees (near objects), 8-12 triangles each"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    n = 0
    for o in bpy.data.collections['near'].all_objects:
        if o.type != 'MESH' or not o.get('inst') or o.get('lod') == 'mid': continue
        nm = o.data.name
        if any(k in nm for k in ('fern', 'grass')): continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(p.x for p in bb), min(p.y for p in bb), min(p.z for p in bb)))
        hi = Vector((max(p.x for p in bb), max(p.y for p in bb), max(p.z for p in bb)))
        c = (lo + hi) / 2; r = (hi - lo) / 2
        if r.z < 0.6: continue
        cz = lo.z + (hi.z - lo.z) * 0.62; rz = (hi.z - lo.z) * 0.4
        rx, ry = r.x * 0.9, r.y * 0.9
        top = bm.verts.new((c.x, c.y, cz + rz)); bot = bm.verts.new((c.x, c.y, cz - rz * 0.8))
        ring = [bm.verts.new((c.x + math.cos(a) * rx, c.y + math.sin(a) * ry, cz + R.uniform(-0.15, 0.15) * rz))
                for a in [k * 2 * math.pi / 5 + R.uniform(-0.2, 0.2) for k in range(5)]]
        u = R.uniform(0.05, 0.95); v = 1 - STRIP * R.uniform(0.2, 0.8)
        for k in range(5):
            for f in (bm.faces.new((ring[k], ring[(k + 1) % 5], top)), bm.faces.new((ring[(k + 1) % 5], ring[k], bot))):
                for l in f.loops: l[uvl].uv = (u + R.uniform(-0.01, 0.01), v)
        n += 1
    me = bpy.data.meshes.new('far_trees'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('far_trees', me); col.objects.link(o)
    return o, n


def run(log=print):
    R = random.Random(9)
    far = C.coll('far')
    for o in list(far.objects): bpy.data.objects.remove(o, do_unlink=True)
    mn = bpy.data.collections['merged_near']
    src = {o.name: o for o in mn.objects}
    parts = []
    for name, ratio in (('facade', None), ('mat', 0.45), ('decal_ground', 0.2), ('decal_ground.001', 0.2), ('water', None)):
        if name in src:
            parts.append(simplify_copy(src[name], 'far_' + name, far, ratio))
    tot = sum(tris(o) for o in parts)
    log('far parts', [(o.name, tris(o)) for o in parts], tot)
    # bring the building part down to budget
    budget = TARGET - 3500
    if tot > budget:
        for o in parts:
            if o.name in ('far_mat', 'far_facade'):
                r = max(0.15, budget / tot)
                m = o.modifiers.new('dec', 'DECIMATE'); m.ratio = r
                with bpy.context.temp_override(object=o, active_object=o):
                    bpy.ops.object.modifier_apply(modifier='dec')
    # join, unwrap into the lower 94 % of the atlas
    with bpy.context.temp_override(active_object=parts[0], selected_editable_objects=parts, selected_objects=parts):
        bpy.ops.object.join()
    fo = parts[0]; fo.name = 'far_tocho'; fo.data.name = 'far_tocho'
    me = fo.data
    for m in list(me.materials): pass
    me.materials.clear()
    uv = me.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = fo
    for o in bpy.context.view_layer.objects: o.select_set(False)
    fo.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.002, shape_method='AABB')
    bpy.ops.object.mode_set(mode='OBJECT')
    for l in uv.data: l.uv = (l.uv[0], l.uv[1] * (1 - STRIP - 0.005))
    # material with the atlas
    im = bpy.data.images.get('far_col')
    if im: bpy.data.images.remove(im)
    im = bpy.data.images.new('far_col', ATL, ATL, alpha=False)
    mat = bpy.data.materials.new('M_far'); mat.use_nodes = True
    nt = mat.node_tree; bs = nt.nodes['Principled BSDF']
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
    nt.links.new(tn.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.88; bs.inputs['Metallic'].default_value = 0.0
    me.materials.append(mat); nt.nodes.active = tn
    log('far mesh', tris(fo))
    # bake diffuse colour from the near model
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    sc.cycles.device = 'GPU'; sc.cycles.samples = 8
    srcs = [src[n] for n in ('facade', 'mat', 'decal_ground', 'water', 'detail', 'matcut') if n in src]
    for o in bpy.data.objects: o.hide_render = True
    for o in srcs + [fo]: o.hide_render = False
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in srcs: o.select_set(True)
    fo.select_set(True); bpy.context.view_layer.objects.active = fo
    b = sc.render.bake
    b.use_selected_to_active = True; b.cage_extrusion = 0.8; b.max_ray_distance = 2.5; b.margin = 4
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True, cage_extrusion=0.8, max_ray_distance=2.5, margin=4)
    col_px = np.array(im.pixels[:]).reshape(ATL, ATL, 4).copy()
    # AO of the far shell itself (plus ground) multiplied in
    g = bpy.data.objects.get('ground')
    if g: g.hide_render = False
    for o in bpy.context.view_layer.objects: o.select_set(False)
    fo.select_set(True)
    sc.world.light_settings.distance = 20.0
    sc.cycles.samples = 64
    bpy.ops.object.bake(type='AO', use_selected_to_active=False, margin=4)
    ao = np.array(im.pixels[:]).reshape(ATL, ATL, 4)[..., 0]
    out = col_px.copy()
    out[..., :3] = col_px[..., :3] * (0.35 + 0.65 * ao[..., None])
    # foliage strip
    y0 = int(ATL * (1 - STRIP))
    h = ATL - y0
    n1 = T.fbm(h, ATL, 6, 3, 77)
    green = T.mix(T.lin((0.24, 0.33, 0.10)), T.lin((0.14, 0.21, 0.07)), n1)
    out[y0:, :, :3] = green
    out[..., 3] = 1
    im.pixels.foreach_set(out.astype(np.float32).ravel())
    im.filepath_raw = C.TEX + 'far_col.png'; im.file_format = 'PNG'; im.save()
    im.source = 'FILE'; im.filepath = C.TEX + 'far_col.png'; im.reload()
    tb, n = blobs(far, R)
    tb.data.materials.append(mat)
    log('far trees', n, tris(tb))
    with bpy.context.temp_override(active_object=fo, selected_editable_objects=[fo, tb], selected_objects=[fo, tb]):
        bpy.ops.object.join()
    for p in fo.data.polygons: p.use_smooth = False
    fo.data.validate()
    for o in bpy.data.objects: o.hide_render = False
    log('far total', tris(fo))
    return fo
