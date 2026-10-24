"""Blender-side helpers: buckets -> objects, materials, images."""
import bpy, bmesh, math, os
import numpy as np
import lib

TEX = lib.WORK + 'tex/'

# material table. orm: which baked ORM atlas (None = constant ORM).  uv0 tiling textures.
MATS = {
    'fac':      dict(tex='fac', orm='arch', rough=0.80, metal=0.0, double=True),
    'tower':    dict(tex='fac', orm='tower', rough=0.70, metal=0.0, double=True),
    'conc':     dict(tex='conc', orm='arch', rough=0.92, metal=0.0, double=False),
    'tconc':    dict(tex='conc', orm='tower', rough=0.92, metal=0.0, double=True),
    'top':      dict(tex='top', orm='arch', rough=0.95, metal=0.0, double=False),
    'pave':     dict(tex='pave', orm='arch', rough=0.85, metal=0.0, double=False),
    'interior': dict(tex='conc', orm=None, ao=0.55, rough=0.95, metal=0.0, double=True, tint=(0.80, 0.78, 0.74)),
    'metal':    dict(tex='metal', orm='props', rough=0.70, metal=0.15, double=True),
    'bark':     dict(tex='bark', orm='props', rough=0.95, metal=0.0, double=False),
    'bronze':   dict(tex='bronze', orm='props', rough=0.55, metal=0.25, double=False),
    'car':      dict(tex='car', orm='props', rough=0.75, metal=0.10, double=True),
    'signs':    dict(tex='signs', orm='props', rough=0.80, metal=0.0, double=True),
    'leaves':   dict(tex='leaves', orm=None, ao=1.0, rough=0.85, metal=0.0, double=True, alpha=True),
    'decals':   dict(tex='decals', orm=None, ao=1.0, rough=0.95, metal=0.0, double=False, alpha=True),
    'glass':    dict(tex=None, color=(0.10, 0.12, 0.14), orm=None, ao=1.0, rough=0.12, metal=0.0, double=True),
    'cover':    dict(tex='top', orm=None, ao=0.85, rough=0.95, metal=0.0, double=False),
    'water':    dict(tex=None, color=(0.048, 0.072, 0.052), orm=None, ao=1.0, rough=0.035, metal=0.0, double=False, spec=0.5),
}
ORM_SIZE = {'arch': 2048, 'tower': 2048, 'props': 2048}

_images = {}


def image(name, path=None, size=None, color=(1, 1, 1, 1), colorspace='sRGB'):
    if name in _images:
        return _images[name]
    if path and os.path.exists(path):
        im = bpy.data.images.load(path)
        im.name = name
    else:
        im = bpy.data.images.new(name, size, size, alpha=False)
        im.generated_color = color
    im.colorspace_settings.name = colorspace
    _images[name] = im
    return im


def gltf_output_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def make_material(name, lod='near'):
    spec = MATS[name]
    mname = name if lod == 'near' else name + '_' + lod
    if mname in bpy.data.materials:
        return bpy.data.materials[mname]
    mat = bpy.data.materials.new(mname)
    mat.use_nodes = True
    nt = mat.node_tree
    P = nt.nodes['Principled BSDF']
    P.inputs['Specular IOR Level'].default_value = spec.get('spec', 0.4)
    out = nt.nodes['Material Output']
    # mid LOD: single-sided walls (double-sided walls self-shadow into diagonal acne at 350-900 m)
    mat.use_backface_culling = (not spec.get('double', False)) or (lib.mid() and name in ('fac', 'tower', 'tconc', 'metal'))
    if spec.get('tex'):
        t = nt.nodes.new('ShaderNodeTexImage'); t.name = 'base'
        tn = spec['tex'] + ('2' if (lib.mid() and spec['tex'] == 'fac') else '')
        t.image = image('tex_' + tn, TEX + tn + '.png')
        t.interpolation = 'Linear'
        uv0 = nt.nodes.new('ShaderNodeUVMap'); uv0.uv_map = 'UV0'
        nt.links.new(uv0.outputs[0], t.inputs[0])
        if spec.get('tint'):
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            mix.inputs['B'].default_value = (*spec['tint'], 1)
            nt.links.new(t.outputs['Color'], mix.inputs['A'])
            # glTF cannot express a tint node; bake tint into a factor instead
            nt.nodes.remove(mix)
            P.inputs['Base Color'].default_value = (*spec['tint'], 1)
            nt.links.new(t.outputs['Color'], P.inputs['Base Color'])
        else:
            nt.links.new(t.outputs['Color'], P.inputs['Base Color'])
        if spec.get('alpha'):
            mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'ROUND'
            nt.links.new(t.outputs['Alpha'], mth.inputs[0])
            nt.links.new(mth.outputs[0], P.inputs['Alpha'])
            mat.surface_render_method = 'DITHERED'
    else:
        P.inputs['Base Color'].default_value = (*spec['color'], 1)
    if spec.get('orm'):
        o = nt.nodes.new('ShaderNodeTexImage'); o.name = 'orm'
        sfx = '_mid' if lib.mid() else ''
        o.image = image('orm_' + spec['orm'],
                        lib.WORK + 'bake/orm_%s%s.png' % (spec['orm'], sfx), ORM_SIZE[spec['orm']] // (2 if lib.mid() else 1),
                        (1, spec['rough'], spec['metal'], 1), 'Non-Color')
        uv1 = nt.nodes.new('ShaderNodeUVMap'); uv1.uv_map = 'UV1'
        nt.links.new(uv1.outputs[0], o.inputs[0])
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(o.outputs['Color'], sep.inputs[0])
        nt.links.new(sep.outputs[1], P.inputs['Roughness'])
        nt.links.new(sep.outputs[2], P.inputs['Metallic'])
        g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = gltf_output_group()
        nt.links.new(sep.outputs[0], g.inputs['Occlusion'])
        nt.nodes.active = o
    else:
        P.inputs['Roughness'].default_value = spec['rough']
        P.inputs['Metallic'].default_value = spec['metal']
        if spec.get('ao', 1.0) < 0.99 and spec.get('tex'):
            # constant ORM via a tiny image on UV0
            key = 'ormc_%s' % name
            o = nt.nodes.new('ShaderNodeTexImage'); o.name = 'orm'
            im = bpy.data.images.get(key)
            if im is None:
                im = bpy.data.images.new(key, 4, 4, alpha=False)
                im.pixels = [spec['ao'], spec['rough'], spec['metal'], 1.0] * 16
                im.colorspace_settings.name = 'Non-Color'
                im.filepath_raw = lib.WORK + 'bake/%s.png' % key
                im.file_format = 'PNG'
                im.save()
            o.image = im
            sep = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(o.outputs['Color'], sep.inputs[0])
            nt.links.new(sep.outputs[1], P.inputs['Roughness'])
            nt.links.new(sep.outputs[2], P.inputs['Metallic'])
            g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = gltf_output_group()
            nt.links.new(sep.outputs[0], g.inputs['Occlusion'])
    return mat


def bucket_to_object(bk, name, mat, collection, origin=None):
    """bk: lib.Bucket -> blender object with UV0 (+ custom normals, colours)"""
    if bk.nv == 0:
        return None
    V = np.array(bk.V, np.float32)
    if origin is None:
        origin = (0.0, 0.0, 0.0)
    V = V - np.array(origin, np.float32)
    me = bpy.data.meshes.new(name)
    nl = np.array([len(f) for f in bk.F], np.int32)
    loops = np.fromiter((i for f in bk.F for i in f), np.int32, count=int(nl.sum()))
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(len(loops)); me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(len(nl))
    ls = np.zeros(len(nl), np.int32); ls[1:] = np.cumsum(nl)[:-1]
    me.polygons.foreach_set('loop_start', ls)
    uvl = me.uv_layers.new(name='UV0')
    uv = np.fromiter((c for f in bk.UV for u in f for c in u), np.float32, count=int(nl.sum()) * 2)
    uvl.data.foreach_set('uv', uv)
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    if bk.C is not None:
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', np.array(bk.C, np.float32).ravel())
    if bk.N is not None:
        Nv = np.array(bk.N, np.float32)
        me.normals_split_custom_set_from_vertices([tuple(n) for n in Nv])
    ob = bpy.data.objects.new(name, me)
    ob.location = origin
    me.materials.append(mat)
    for p in me.polygons:
        pass
    collection.objects.link(ob)
    return ob


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def import_obj(path, coll):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
    return new


def smooth_by_angle(ob, deg=40):
    me = ob.data
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(deg))
    except Exception:
        pass
