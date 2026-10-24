"""glTF export + stats."""
import json
import os

import bpy

from sb_common import OUT


def tri_count(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in objs:
        if o.type != 'MESH':
            continue
        me = o.evaluated_get(dg).data
        me.calc_loop_triangles()
        n += len(me.loop_triangles)
    return n


def draw_calls(objs):
    """one primitive per (mesh data, material slot used); instances of the same mesh count once"""
    seen = set()
    for o in objs:
        if o.type != 'MESH':
            continue
        for i, s in enumerate(o.material_slots):
            seen.add((o.data.name, i))
    return len(seen)


def export_glb(path, objs, draco=True, quality=82, instances=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_image_format='WEBP',
              export_image_quality=quality, export_vertex_color='MATERIAL', export_texcoords=True,
              export_normals=True, export_tangents=False, export_materials='EXPORT', export_yup=True,
              export_apply=True, export_cameras=False, export_lights=False, export_extras=False,
              export_gpu_instances=instances)
    if draco:
        kw.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                  export_draco_position_quantization=16, export_draco_normal_quantization=10,
                  export_draco_texcoord_quantization=16, export_draco_color_quantization=10)
    bpy.ops.export_scene.gltf(**kw)
    return os.path.getsize(path)
