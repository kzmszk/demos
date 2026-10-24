"""Materials: plain Principled BSDF wired the way Blender's glTF exporter understands.

  base colour  <- <set>_col  (UVMap)
  normal       <- <set>_nrm  (UVMap, Normal Map node)
  roughness/metal <- <set>_orm G/B (UVMap); R holds the tile's own micro occlusion
  occlusion    <- lm_<name> R  (UV 'LM', glTF texCoord 1) for the big tiled sets, or <set>_orm R for unique-UV sets

Texture files live in WORK/tex as PNG; the exporter writes WebP.
"""
import bpy, os
import common as C

SETS = {
    # name: (alpha MASK, lightmap image or None, use normal map)
    'facade': (False, 'lm_facade', True),
    'mat': (False, 'lm_mat', True),
    'detail': (False, 'lm_detail', True),  # same textures as 'mat', near-only small things with their own lightmap
    'matcut': (True, None, True),          # same textures as 'mat' (grid / torn edges), alpha clipped
    'props': (False, None, True),
    'leaf': (True, None, False),
    'decal': (True, None, True),
}
TEXSET = {'matcut': 'mat', 'detail': 'mat'}


def img(name, size=2048, color=(0.5, 0.5, 0.5, 1), noncolor=False):
    path = C.TEX + name + '.png'
    im = bpy.data.images.get(name)
    if im is None:
        if os.path.exists(path):
            im = bpy.data.images.load(path); im.name = name
        else:
            im = bpy.data.images.new(name, size, size, alpha=True)
            im.generated_color = color
    if noncolor: im.colorspace_settings.name = 'Non-Color'
    return im


def _glTF_output(nt):
    g = bpy.data.node_groups.get('glTF Material Output')
    if g is None:
        g = bpy.data.node_groups.new('glTF Material Output', 'ShaderNodeTree')
        g.interface.new_socket('Occlusion', in_out='INPUT', socket_type='NodeSocketFloat')
    n = nt.nodes.new('ShaderNodeGroup'); n.node_tree = g
    return n


def make(name):
    mname = 'M_' + name
    m = bpy.data.materials.get(mname)
    if m: return m
    mask, lm, nrm = SETS[name]
    ts = TEXSET.get(name, name)
    m = bpy.data.materials.new(mname)
    nt = m.node_tree if m.node_tree else None
    if nt is None:
        m.use_nodes = True; nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(bs.outputs[0], out.inputs[0])
    uv0 = nt.nodes.new('ShaderNodeUVMap'); uv0.uv_map = 'UVMap'
    col = nt.nodes.new('ShaderNodeTexImage'); col.image = img(ts + '_col'); col.name = 'col'
    nt.links.new(uv0.outputs[0], col.inputs[0]); nt.links.new(col.outputs['Color'], bs.inputs['Base Color'])
    if mask:
        rnd = nt.nodes.new('ShaderNodeMath'); rnd.operation = 'ROUND'      # -> glTF alphaMode MASK, cutoff 0.5
        nt.links.new(col.outputs['Alpha'], rnd.inputs[0]); nt.links.new(rnd.outputs[0], bs.inputs['Alpha'])
        try:
            m.surface_render_method = 'DITHERED'
        except Exception: pass
        m.blend_method = 'CLIP' if hasattr(m, 'blend_method') else None
        m.alpha_threshold = 0.5 if hasattr(m, 'alpha_threshold') else None
    orm = nt.nodes.new('ShaderNodeTexImage'); orm.image = img(ts + '_orm', color=(1, 0.8, 0, 1), noncolor=True); orm.name = 'orm'
    nt.links.new(uv0.outputs[0], orm.inputs[0])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[1], bs.inputs['Roughness']); nt.links.new(sep.outputs[2], bs.inputs['Metallic'])
    if nrm:
        nm = nt.nodes.new('ShaderNodeTexImage'); nm.image = img(ts + '_nrm', color=(0.5, 0.5, 1, 1), noncolor=True); nm.name = 'nrm'
        nt.links.new(uv0.outputs[0], nm.inputs[0])
        nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.uv_map = 'UVMap'
        nt.links.new(nm.outputs['Color'], nmap.inputs['Color']); nt.links.new(nmap.outputs[0], bs.inputs['Normal'])
    go = _glTF_output(nt)
    if lm:
        m['lm'] = lm
        uv1 = nt.nodes.new('ShaderNodeUVMap'); uv1.uv_map = 'LM'
        lmi = nt.nodes.new('ShaderNodeTexImage'); lmi.image = img(lm, color=(1, 1, 1, 1), noncolor=True); lmi.name = 'lm'
        nt.links.new(uv1.outputs[0], lmi.inputs[0])
        s2 = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(lmi.outputs['Color'], s2.inputs[0])
        nt.links.new(s2.outputs[0], go.inputs['Occlusion'])
    else:
        nt.links.new(sep.outputs[0], go.inputs['Occlusion'])
    m.use_backface_culling = not mask
    if name in ('leaf',):
        m.use_backface_culling = False
    return m


def glass():
    m = bpy.data.materials.get('glass_dark')
    if m: return m
    m = bpy.data.materials.new('glass_dark'); m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (0.05, 0.065, 0.075, 1)
    bs.inputs['Roughness'].default_value = 0.12; bs.inputs['Metallic'].default_value = 0.0
    m.use_backface_culling = False
    return m


def water():
    m = bpy.data.materials.get('M_water')
    if m: return m
    m = bpy.data.materials.new('M_water'); m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (0.035, 0.045, 0.035, 1)
    bs.inputs['Roughness'].default_value = 0.06; bs.inputs['Metallic'].default_value = 0.0
    return m


def all_mats():
    return {k: make(k) for k in SETS}
