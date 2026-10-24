"""Export near / mid / far glb, collide.obj and hero.json to public/hero/tocho/."""
import bpy, os, json, math
import numpy as np
import common as C

GLTF = dict(export_format='GLB', export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
            export_tangents=False, export_materials='EXPORT', export_image_format='WEBP', export_image_quality=82,
            export_attributes=False, export_gpu_instances=True, export_cameras=False, export_lights=False,
            export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
            export_draco_position_quantization=16, export_draco_normal_quantization=10,
            export_draco_texcoord_quantization=14, export_draco_generic_quantization=12,
            export_extras=False, export_animations=False, export_skins=False, export_morph=False)


def tris(o):
    me = o.data; me.calc_loop_triangles(); return len(me.loop_triangles)


def stats(objs):
    """triangles drawn and draw calls (instanced meshes draw once per material)"""
    t = 0; dc = 0; seen = set()
    for o in objs:
        if o.type != 'MESH': continue
        n = tris(o)
        t += n
        if o.data.name in seen and o.get('inst'): continue
        seen.add(o.data.name)
        used = set(p.material_index for p in o.data.polygons)
        dc += max(1, len(used))
    return t, dc


def export_glb(path, objs, log=print):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in objs:
        o.hide_set(False); o.hide_viewport = False
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, **GLTF)
    mb = os.path.getsize(path) / 1e6
    t, dc = stats(objs)
    log('exported', os.path.basename(path), '%.2f MB' % mb, t, 'tris', dc, 'draw calls')
    return t, dc, mb


def scaled_images(max_px):
    """downscale every texture used by the exported materials (in memory) for the mid LOD"""
    for im in bpy.data.images:
        if im.size[0] > max_px and im.source in ('FILE', 'GENERATED'):
            im.scale(max_px, max_px)


def write_obj(path, objs, note=''):
    with open(path, 'w') as f:
        f.write('# TOKYO 2090 hero collision proxy, district tocho. x east, y north, z up (T.P. m), local origin = city (%d, %d). %s\n' % (C.ORIGIN[0], C.ORIGIN[1], note))
        base = 1; nt = 0
        dg = bpy.context.evaluated_depsgraph_get()
        for o in objs:
            me = o.evaluated_get(dg).to_mesh()
            me.calc_loop_triangles()
            mw = o.matrix_world
            f.write('o %s\n' % o.name)
            for v in me.vertices:
                p = mw @ v.co; f.write('v %.3f %.3f %.3f\n' % (p.x, p.y, p.z))
            for t in me.loop_triangles:
                a, b, c = t.vertices; f.write('f %d %d %d\n' % (a + base, b + base, c + base)); nt += 1
            base += len(me.vertices)
            o.evaluated_get(dg).to_mesh_clear()
    return nt


def run(log=print):
    bpy.ops.wm.open_mainfile(filepath=C.WORK + 'tocho.blend')
    import hero_meta
    st = {}
    inst = [o for o in bpy.data.collections['near'].all_objects if o.get('inst')]
    for o in inst:
        o.hide_render = False
    near = list(bpy.data.collections['merged_near'].objects) + [o for o in inst if o.get('lod', 'both') in ('both', 'near')]
    t, dc, mb = export_glb(C.PUB + 'near.glb', near, log)
    st.update(near_tris=t, draw_calls=dc, near_mb=round(mb, 2))
    if 'far' in bpy.data.collections and bpy.data.collections['far'].objects:
        t, dcf, mbf = export_glb(C.PUB + 'far.glb', list(bpy.data.collections['far'].objects), log)
        st.update(far_tris=t, far_mb=round(mbf, 2))
    if 'merged_mid' in bpy.data.collections:
        mid = list(bpy.data.collections['merged_mid'].objects) + [o for o in inst if o.get('lod', 'both') in ('both', 'mid')]
        scaled_images(1024)
        t, dcm, mbm = export_glb(C.PUB + 'mid.glb', mid, log)
        st.update(mid_tris=t, mid_mb=round(mbm, 2), mid_draw_calls=dcm)
    if 'collide' in bpy.data.collections:
        n = write_obj(C.PUB + 'collide.obj', list(bpy.data.collections['collide'].objects))
        st['collide_tris'] = n; log('collide.obj', n, 'tris')
    hero_meta.write(st)
    log('stats', st)
