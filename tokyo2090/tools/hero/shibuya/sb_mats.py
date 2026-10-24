"""glTF-exportable materials: base colour (UV0) x vertex colour, ORM (UV1: R=AO, G=rough, B=metal),
optional tangent-space normal (UV0), optional alpha clip."""
import os
import bpy
import numpy as np

from sb_common import TEX, WORK

ORM_DIR = os.path.join(WORK, 'orm')
os.makedirs(ORM_DIR, exist_ok=True)

# material key -> settings
MATS = {
    'facade_a': dict(base='facade_a.png', normal='facade_a_n.png', rough=0.88, orm=2048),
    'facade_b': dict(base='facade_b.png', normal='facade_b_n.png', rough=0.85, orm=2048),
    'concrete': dict(base='concrete.png', normal='concrete_n.png', rough=0.92, orm=2048),
    'rubble': dict(base='rubble.png', normal='rubble_n.png', rough=0.95, orm=1024),
    'metal': dict(base='metal.png', rough=0.8, metal=0.0, orm=1024),
    'bark': dict(base='bark.png', normal='bark_n.png', rough=0.9, orm=None),
    'props': dict(base='props.png', rough=0.75, orm=1024, clip=True, double=True),
    'signs': dict(base='signs.png', rough=0.7, orm=1024, clip=True, double=True),
    'glass_': dict(base=None, color=(0.02, 0.026, 0.032), rough=0.12, orm=None),
    'bronze': dict(base='bronze.png', rough=0.55, metal=0.25, orm=512),
    'decal_ground': dict(base='decals.png', rough=0.95, orm=None, clip=True, vcol=False),
    'decal_moss': dict(base='mosscarpet.png', rough=0.95, orm=None, clip=True, vcol=True),
    'foliage_leaves': dict(base='foliage.png', normal='foliage_n.png', rough=0.8, orm=None, clip=True, double=True, vcol=True),
}

_imgs = {}


def image(path, colorspace='sRGB'):
    key = (path, colorspace)
    if key in _imgs:
        return _imgs[key]
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    _imgs[key] = img
    return img


def gltf_output_group():
    g = bpy.data.node_groups.get('glTF Material Output')
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
        g.interface.new_socket('Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    return g


def orm_image(key, size):
    name = f'orm_{key}'
    img = bpy.data.images.get(name)
    if img is None:
        p = os.path.join(ORM_DIR, f'{name}.png')
        if os.path.exists(p):
            img = bpy.data.images.load(p)
            img.name = name
        else:
            img = bpy.data.images.new(name, size, size, alpha=False)
            img.generated_color = (1, 0.9, 0, 1)
        img.colorspace_settings.name = 'Non-Color'
    return img


def make(key, cfg=None):
    cfg = dict(MATS[key] if cfg is None else cfg)
    m = bpy.data.materials.get(key)
    if m is not None:
        return m
    m = bpy.data.materials.new(key)
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes; L = nt.links
    out = N.new('ShaderNodeOutputMaterial'); out.location = (900, 0)
    bs = N.new('ShaderNodeBsdfPrincipled'); bs.location = (500, 0)
    L.new(bs.outputs[0], out.inputs['Surface'])
    uv0 = N.new('ShaderNodeUVMap'); uv0.uv_map = 'UVMap'; uv0.location = (-900, 0)
    if cfg.get('base'):
        tb = N.new('ShaderNodeTexImage'); tb.image = image(os.path.join(TEX, cfg['base'])); tb.location = (-600, 200)
        tb.name = 'base'
        L.new(uv0.outputs[0], tb.inputs[0])
        col = tb.outputs['Color']
        if cfg.get('vcol', True):
            ca = N.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'; ca.location = (-600, 450)
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.location = (-200, 300)
            mx.inputs['Factor'].default_value = 1.0
            L.new(col, mx.inputs[6]); L.new(ca.outputs['Color'], mx.inputs[7])
            col = mx.outputs[2]
        L.new(col, bs.inputs['Base Color'])
        if cfg.get('clip'):
            rd = N.new('ShaderNodeMath'); rd.operation = 'ROUND'; rd.location = (100, -300)
            L.new(tb.outputs['Alpha'], rd.inputs[0])
            L.new(rd.outputs[0], bs.inputs['Alpha'])
    else:
        bs.inputs['Base Color'].default_value = (*cfg['color'], 1)
    bs.inputs['Roughness'].default_value = cfg.get('rough', 0.9)
    bs.inputs['Metallic'].default_value = cfg.get('metal', 0.0)
    if cfg.get('normal'):
        tn = N.new('ShaderNodeTexImage'); tn.image = image(os.path.join(TEX, cfg['normal']), 'Non-Color'); tn.location = (-600, -500)
        L.new(uv0.outputs[0], tn.inputs[0])
        nm = N.new('ShaderNodeNormalMap'); nm.uv_map = 'UVMap'; nm.location = (-200, -500)
        nm.inputs['Strength'].default_value = cfg.get('nstr', 1.0)
        L.new(tn.outputs['Color'], nm.inputs['Color'])
        L.new(nm.outputs[0], bs.inputs['Normal'])
    if cfg.get('orm'):
        uv1 = N.new('ShaderNodeUVMap'); uv1.uv_map = 'UV1'; uv1.location = (-900, -250)
        to = N.new('ShaderNodeTexImage'); to.image = orm_image(key, cfg['orm']); to.location = (-600, -200)
        to.name = 'orm'
        L.new(uv1.outputs[0], to.inputs[0])
        sp = N.new('ShaderNodeSeparateColor'); sp.location = (-250, -200)
        L.new(to.outputs['Color'], sp.inputs[0])
        L.new(sp.outputs[1], bs.inputs['Roughness'])
        L.new(sp.outputs[2], bs.inputs['Metallic'])
        g = N.new('ShaderNodeGroup'); g.node_tree = gltf_output_group(); g.location = (500, -400)
        L.new(sp.outputs[0], g.inputs['Occlusion'])
    m.use_backface_culling = not cfg.get('double', False)
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        pass
    return m


def all_mats():
    return {k: make(k) for k in MATS}


def write_orm(key, ao, rough=None, metal=None):
    """ao: (h,w) float [0,1] -> save ORM png and reload into the material's image"""
    cfg = MATS[key]
    h, w = ao.shape
    r = np.full((h, w), cfg.get('rough', 0.9), np.float32) if rough is None else rough
    mt = np.full((h, w), cfg.get('metal', 0.0), np.float32) if metal is None else metal
    a = np.ones((h, w, 4), np.float32)
    a[..., 0] = ao; a[..., 1] = r; a[..., 2] = mt
    name = f'orm_{key}'
    img = bpy.data.images.get(name)
    if img is None or tuple(img.size) != (w, h):
        if img is not None:
            bpy.data.images.remove(img)
        img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(a.ravel())
    p = os.path.join(ORM_DIR, f'{name}.png')
    img.filepath_raw = p
    img.file_format = 'PNG'
    img.save()
    return img
