"""Preview-only: replaces jk.to_objects (in THIS process) with a version that honours the vertex tint C0 on the viewer's
tinted material kinds (wall / cloth / roofmetal / ground), so the EEVEE previews show the colours the viewer will draw.
The shared kit is untouched; the exported .npz is not affected."""
import os
import numpy as np
import jk
from jk import core

TINTED = ('wall', 'machiya', 'roofmetal', 'cloth', 'roofflat')

def _s2l(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _tint_material(name, m):
    import bpy
    mm = bpy.data.materials.get('jkt_' + name)
    if mm: return mm
    mm = bpy.data.materials.new('jkt_' + name)
    mm.use_nodes = True
    nt = mm.node_tree
    bs = nt.nodes.get('Principled BSDF')
    at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeVectorMath'); mul.operation = 'SCALE'
    mul.inputs['Scale'].default_value = 0.85 if m['kind'] != 'cloth' else 1.0
    nt.links.new(at.outputs['Color'], mul.inputs[0])
    nt.links.new(mul.outputs[0], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.8
    return mm

def to_objects(b, collection=None, tags=('main', 'detail'), name=None):
    import bpy
    bm = core.blender_materials()
    M_ = core.mats()
    col = collection or bpy.context.scene.collection
    objs = []
    for tag in tags:
        M = b.merged((tag,))
        if M is None: continue
        P, I = M['P'], M['I']
        me = bpy.data.meshes.new(f'{name or b.name}_{tag}')
        me.vertices.add(len(P)); me.vertices.foreach_set('co', P.ravel())
        me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
        me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32))
        me.update(calc_edges=True)
        names = sorted(set(M['MATN']))
        for n in names:
            m = M_[n]
            me.materials.append(_tint_material(n, m) if m['kind'] in TINTED else bm[n])
        midx = {n: k for k, n in enumerate(names)}
        fm = np.array([midx[n] for n in M['MATN'][I[:, 0]]], np.int32)
        me.polygons.foreach_set('material_index', fm)
        me.polygons.foreach_set('use_smooth', np.ones(len(I), bool))
        me.normals_split_custom_set(M['N'][I.ravel()].tolist())
        uvl = me.uv_layers.new(name='uv'); uvl.data.foreach_set('uv', M['UV'][I.ravel()].ravel())
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        rgb = _s2l(M['C0'][I.ravel()][:, :3])
        ca.data.foreach_set('color', np.c_[rgb, np.ones(len(rgb))].ravel().astype(np.float32))
        ob = bpy.data.objects.new(me.name, me); col.objects.link(ob)
        ob['jk_tag'] = tag
        objs.append(ob)
    # STATION_DEBUG=1: draw the ground paint polygons (S.paint) as thin coloured plates (preview only; not exported)
    if os.environ.get('STATION_DEBUG') and getattr(b, 'paint_debug', None) and not getattr(b, '_dbg_done', False):
        b._dbg_done = True
        from jk import prim
        tb = type(b)('paint_debug')
        MAPM = {'stone_slab': ('wall_tile', (200, 120, 90)), 'tactile': ('gold', (255, 255, 255)), 'asphalt': ('wall_tile', (60, 60, 70)),
                'concrete': ('wall_tile', (120, 190, 120)), 'sidewalk': ('wall_tile', (200, 200, 120))}
        for (poly, surf, z) in b.paint_debug:
            mat, tint = MAPM.get(surf, ('wall_plaster', (255, 255, 255)))
            prim.polygon(tb, [tuple(p) for p in poly], z, mat, up=True, c0=(*tint, 0))
        M_ = tb.merged(('main',)); print('paint debug plates:', len(b.paint_debug), tb.ntri(), M_['P'].min(0), M_['P'].max(0), set(M_['MATN']), flush=True)
        objs += to_objects(tb, collection=col)
    return objs

jk.to_objects = to_objects

# a higher sun from the north-east so the north faces of the station read in the previews (the default is a 12 deg
# evening sun whose long shadows cover the plaza)
try:
    import render_scene as _R
    _orig_setup = _R.setup
    def _setup(res=(1600, 900), engine='EEVEE', sun=(55, 38), strength=4.5, sky=(0.45, 0.55, 0.75)):
        return _orig_setup(res=res, engine=engine, sun=sun, strength=strength, sky=sky)
    _R.setup = _setup
except Exception as _e:
    print('preview sun patch skipped:', _e)


# '*_night*' shots: a dark sky and a faint moon, so the emissive 'lamp' / 'lantern_paper' panes read as they will in the evening
try:
    import bpy
    from mathutils import Vector
    _orig_shot = _R.shot
    def _shot(path, cam, tgt, lens=35):
        night = '_night' in str(path)
        sc = bpy.context.scene
        if night:
            w = sc.world; bg = w.node_tree.nodes['Background']
            old = (tuple(bg.inputs['Color'].default_value), bg.inputs['Strength'].default_value)
            bg.inputs['Color'].default_value = (0.02, 0.03, 0.08, 1); bg.inputs['Strength'].default_value = 0.6
            suns = [o for o in sc.objects if o.type == 'LIGHT']
            olds = [(o, o.data.energy) for o in suns]
            for o in suns: o.data.energy = 0.25
        _orig_shot(path, cam, tgt, lens)
        if night:
            bg.inputs['Color'].default_value = old[0]; bg.inputs['Strength'].default_value = old[1]
            for o, e in olds: o.data.energy = e
    _R.shot = _shot
except Exception as _e:
    print('night patch skipped:', _e)
