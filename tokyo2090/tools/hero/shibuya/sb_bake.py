"""UV1 lightmap layout + Cycles AO bake into each material's ORM image."""
import math
import os
import time

import bpy
import numpy as np

import sb_mats


def select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def make_uv1(obj, margin=0.003):
    me = obj.data
    if 'UV1' in me.uv_layers:
        return
    if 'UV1' not in me.uv_layers:
        me.uv_layers.new(name='UV1')
    me.uv_layers.active = me.uv_layers['UV1']
    select_only([obj])
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=margin, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers['UVMap']
    for i, l in enumerate(me.uv_layers):
        l.active_render = (l.name == 'UVMap')


def bake_ao(objs, samples=128, distance=7.0, margin=6, gamma=1.0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.world.light_settings.distance = distance
    sc.render.bake.margin = margin
    sc.render.bake.margin_type = 'EXTEND'
    for obj in objs:
        t = time.time()
        mat = obj.active_material
        key = mat.name
        cfg = sb_mats.MATS.get(key, {})
        size = cfg.get('orm') or 1024
        node = mat.node_tree.nodes.get('orm')
        if node is None:
            continue
        ao = bpy.data.images.new(f'ao_{key}', size, size, alpha=False, float_buffer=True)
        ao.colorspace_settings.name = 'Non-Color'
        keep = node.image
        node.image = ao
        mat.node_tree.nodes.active = node
        me = obj.data
        me.uv_layers.active = me.uv_layers['UV1']
        select_only([obj])
        bpy.ops.object.bake(type='AO', margin=margin, use_clear=True)
        me.uv_layers.active = me.uv_layers['UVMap']
        a = np.empty(size * size * 4, np.float32)
        ao.pixels.foreach_get(a)
        a = a.reshape(size, size, 4)[..., 0]
        a = np.clip(a, 0, 1) ** gamma
        img = sb_mats.write_orm(key, a)
        node.image = img
        bpy.data.images.remove(ao)
        print(f'  baked {key} {size}px in {time.time() - t:.1f}s')
