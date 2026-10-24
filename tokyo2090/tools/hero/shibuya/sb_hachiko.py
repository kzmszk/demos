"""Hachiko: the bronze Akita sitting on its granite pedestal (green patina, moss).

Built from metaball ellipsoids -> mesh -> voxel remesh -> smooth -> decimate; unique UV and a baked
albedo (bronze with verdigris running down, moss on top; granite pedestal) into tex/bronze.png.
Local frame: the dog faces +Y, origin at the centre of the pedestal base on the ground.
"""
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler

from sb_common import TEX, WORK

PED_W, PED_D, PED_H = 1.05, 1.45, 1.30     # granite pedestal (top block)
MB_R, MB_T = 1.5, 0.45
BASE_W, BASE_D, BASE_H = 1.55, 1.95, 0.32   # lower step


def _ball(mb, co, r, rot=(0, 0, 0), kind='ELLIPSOID', stiff=2.0, neg=False):
    e = mb.elements.new(type=kind)
    e.co = co
    e.radius = MB_R
    e.size_x, e.size_y, e.size_z = r
    e.rotation = Euler(rot).to_quaternion()
    e.stiffness = stiff
    e.use_negative = neg
    return e


def dog_metaball():
    md = bpy.data.metaballs.new('hachi_mb')
    md.resolution = 0.012
    md.render_resolution = 0.012
    md.threshold = MB_T
    S = 1.0
    # body: rump sits on the ground; a stocky Akita: deep chest, thick neck, broad head
    _ball(md, (0, -0.19, 0.25), (0.215, 0.23, 0.21))                              # rump / haunches
    _ball(md, (0, -0.06, 0.44), (0.20, 0.20, 0.25), rot=(math.radians(-32), 0, 0))  # belly / back
    _ball(md, (0, 0.09, 0.59), (0.205, 0.18, 0.23), rot=(math.radians(-18), 0, 0))  # chest
    _ball(md, (0, 0.18, 0.52), (0.15, 0.09, 0.17))                                 # breastbone forward
    _ball(md, (0, 0.11, 0.80), (0.155, 0.15, 0.16), rot=(math.radians(-25), 0, 0))  # thick neck / ruff
    # head
    _ball(md, (0, 0.165, 0.975), (0.14, 0.13, 0.112))                              # skull
    _ball(md, (0, 0.30, 0.925), (0.072, 0.095, 0.06), rot=(math.radians(10), 0, 0))  # muzzle (broad)
    _ball(md, (0, 0.385, 0.935), (0.036, 0.03, 0.03), stiff=3)                     # nose tip
    for sx in (-1, 1):
        _ball(md, (sx * 0.082, 0.21, 0.915), (0.072, 0.07, 0.06))                   # cheeks
        _ball(md, (sx * 0.055, 0.265, 0.99), (0.032, 0.035, 0.022), stiff=1.5)     # brow
    # front legs: straight, thick columns, paws on the plinth
    for sx in (-1, 1):
        _ball(md, (sx * 0.095, 0.17, 0.30), (0.062, 0.064, 0.28), rot=(math.radians(-4), 0, 0))
        _ball(md, (sx * 0.10, 0.14, 0.50), (0.075, 0.085, 0.13))                   # elbow / upper arm
        _ball(md, (sx * 0.095, 0.24, 0.035), (0.058, 0.085, 0.038))                # paw
    # hind legs folded beside the rump, hind paws pointing forward
    for sx in (-1, 1):
        _ball(md, (sx * 0.16, -0.11, 0.21), (0.095, 0.20, 0.16), rot=(math.radians(-15), 0, 0))
        _ball(md, (sx * 0.165, 0.01, 0.07), (0.058, 0.115, 0.065))
        _ball(md, (sx * 0.165, 0.10, 0.035), (0.052, 0.075, 0.035))
    # tail: the Akita curl, rising from the croup and curling forward over the back onto the flank
    u = Vector((0, -1.0, 0.15)).normalized(); v = Vector((0.4, 0, 0.92)).normalized()
    c = Vector((0.05, -0.215, 0.585))
    for k in range(11):
        a = math.radians(-100 + k * 30)
        p = c + (u * math.cos(a) + v * math.sin(a)) * 0.085
        _ball(md, tuple(p), (0.052, 0.052, 0.052), stiff=2.0)
    ob = bpy.data.objects.new('hachi_mb', md)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ears(bm_target_obj):
    """erect triangular ears (pyramids) joined to the dog mesh"""
    me = bm_target_obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for sx in (-1, 1):
        base = Vector((sx * 0.082, 0.14, 1.045))
        tip = base + Vector((sx * 0.03, 0.045, 0.125))
        w = 0.06; d = 0.032
        v = [bm.verts.new(base + Vector((-w, -d, 0))), bm.verts.new(base + Vector((w, -d, 0))),
             bm.verts.new(base + Vector((w, d, 0))), bm.verts.new(base + Vector((-w, d, 0))), bm.verts.new(tip)]
        bm.faces.new((v[0], v[1], v[4])); bm.faces.new((v[1], v[2], v[4])); bm.faces.new((v[2], v[3], v[4])); bm.faces.new((v[3], v[0], v[4]))
        bm.faces.new((v[3], v[2], v[1], v[0]))
    bm.to_mesh(me)
    bm.free()


def build_dog():
    ob = dog_metaball()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    dog = bpy.data.objects.new('hachi_dog', me)
    bpy.context.scene.collection.objects.link(dog)
    ears(dog)
    # unify: voxel remesh, smooth, decimate
    m = dog.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = 0.009
    m = dog.modifiers.new('sm', 'SMOOTH'); m.factor = 0.6; m.iterations = 6
    m = dog.modifiers.new('dc', 'DECIMATE'); m.ratio = 0.12
    bpy.context.view_layer.objects.active = dog
    for mod in list(dog.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in dog.data.polygons:
        p.use_smooth = True
    dog.scale = (1.1, 1.1, 1.1)
    return dog


def build_pedestal():
    bm = bmesh.new()
    def boxv(x0, x1, y0, y1, z0, z1, bev=0.0):
        r = bmesh.ops.create_cube(bm, size=1.0)
        vs = r['verts']
        for v in vs:
            v.co.x = x0 if v.co.x < 0 else x1
            v.co.y = y0 if v.co.y < 0 else y1
            v.co.z = z0 if v.co.z < 0 else z1
        return vs
    boxv(-BASE_W / 2, BASE_W / 2, -BASE_D / 2, BASE_D / 2, -0.4, BASE_H)
    boxv(-PED_W / 2, PED_W / 2, -PED_D / 2, PED_D / 2, BASE_H, BASE_H + PED_H - 0.08)
    boxv(-PED_W / 2 - 0.05, PED_W / 2 + 0.05, -PED_D / 2 - 0.05, PED_D / 2 + 0.05, BASE_H + PED_H - 0.08, BASE_H + PED_H)  # cap
    me = bpy.data.meshes.new('hachi_ped')
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('hachi_ped', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bake_material(objs, size=1024):
    """procedural bronze/granite -> baked albedo into tex/bronze.png via a joined unique-UV object"""
    from sb_nodes import NB
    import sb_surf as S
    m = bpy.data.materials.new('hachi_bake_src')
    nt = m.node_tree; nt.nodes.clear(); nb = NB(nt)
    tc = nb.node('ShaderNodeTexCoord')
    co = tc.outputs['Object']
    geo = nb.node('ShaderNodeNewGeometry')
    x, y, z = nb.sep(co)
    nx, ny, nz = nb.sep(geo.outputs['Normal'])
    at = nb.node('ShaderNodeAttribute', attribute_name='is_ped')
    isped = at.outputs['Fac']
    # bronze: dark brown base, verdigris (green-blue) running down from upper surfaces, darker in crevices
    n1 = nb.noise(co, scale=6.0, detail=6.0, rough=0.6, w=0.0, dim='4D')
    streak = nb.noise(nb.vmath('MULTIPLY', co, (14.0, 14.0, 2.0)), scale=1.0, detail=4.0, w=2.0)
    up = nb.smooth(-0.2, 0.8, nz)
    pat = nb.mx(nb.mul(up, 0.9), nb.smooth(0.45, 0.75, nb.add(nb.mul(streak, 0.8), nb.mul(n1, 0.4))))
    bronze = nb.mix(n1, (0.055, 0.035, 0.02), (0.11, 0.07, 0.04))
    verd = nb.mix(nb.noise(co, scale=20.0, w=4.0), (0.10, 0.20, 0.15), (0.20, 0.32, 0.25))
    col_b = nb.mix(nb.mul(pat, 0.85), bronze, verd)
    # polished bits (people touched the paws and the nose for decades before 2030): lighter brown
    paw = nb.mul(nb.smooth(0.12, 0.02, z), nb.smooth(0.05, 0.2, y))
    col_b = nb.mix(nb.mul(paw, 0.6), col_b, (0.20, 0.13, 0.07))
    # moss on top of the head/back
    mo = nb.mul(nb.smooth(0.55, 0.9, nz), nb.smooth(0.5, 0.65, nb.noise(co, scale=9.0, w=6.0)))
    col_b = nb.mix(nb.mul(mo, 0.7), col_b, S.MOSS)
    # granite: grey speckle, lichen, moss at the base and top
    sp = nb.voronoi(co, scale=180.0, w=1.0, out='Distance')
    gr = nb.mix(nb.smooth(0.0, 0.3, sp), (0.10, 0.10, 0.10), (0.36, 0.35, 0.33))
    gr = nb.mix(nb.mul(nb.noise(co, scale=3.0, w=3.0), 0.5), gr, (0.25, 0.25, 0.24))
    mo2 = nb.mx(nb.mul(nb.smooth(0.6, 0.0, z), nb.smooth(0.45, 0.6, nb.noise(co, scale=4.0, w=8.0))),
                nb.mul(nb.smooth(0.7, 1.0, nz), nb.smooth(0.4, 0.55, nb.noise(co, scale=5.0, w=9.0))))
    gr = nb.mix(nb.mul(mo2, 0.9), gr, nb.mix(nb.noise(co, scale=30.0, w=1.0), S.MOSS, S.MOSS2))
    streak2 = nb.noise(nb.vmath('MULTIPLY', co, (10.0, 10.0, 0.8)), scale=1.0, detail=3.0, w=5.0)
    gr = nb.mix(nb.mul(nb.smooth(0.55, 0.8, streak2), 0.5), gr, (0.08, 0.075, 0.06))
    col = nb.mix(isped, col_b, gr)
    em = nb.node('ShaderNodeEmission'); nb.link(col, em.inputs['Color'])
    out = nb.node('ShaderNodeOutputMaterial'); nb.link(em.outputs[0], out.inputs['Surface'])
    img = bpy.data.images.new('bronze_bake', size, size, alpha=False, float_buffer=True)
    tn = nb.node('ShaderNodeTexImage'); tn.image = img
    nt.nodes.active = tn
    # join a temporary copy with the attribute marking the pedestal
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        me = o.data
        a = me.attributes.new('is_ped', 'FLOAT', 'POINT')
        a.data.foreach_set('value', np.full(len(me.vertices), 1.0 if 'ped' in o.name else 0.0, np.float32))
        me.materials.clear(); me.materials.append(m)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    # unique UV
    for o in objs:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    j = bpy.context.view_layer.objects.active
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 4; sc.cycles.device = 'GPU'
    sc.render.bake.margin = 8
    bpy.ops.object.bake(type='EMIT', margin=8)
    a = np.empty(size * size * 4, np.float32); img.pixels.foreach_get(a)
    a = a.reshape(size, size, 4)[::-1]
    from sb_texlib import save_png
    save_png(a, os.path.join(TEX, 'bronze.png'))
    return j


def build(save=True):
    dog = build_dog()
    ped = build_pedestal()
    dog.location = (0, 0.02, BASE_H + PED_H)
    bpy.context.view_layer.objects.active = dog
    bpy.ops.object.select_all(action='DESELECT'); dog.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    j = bake_material([dog, ped])
    j.name = 'hachiko'
    j.data.name = 'hachiko'
    if save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, 'hachiko.blend'))
    print('hachiko tris', sum(len(p.vertices) - 2 for p in j.data.polygons))
    return j
