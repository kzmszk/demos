"""all statues lined up: saves /home/kazu/work/kyoto-assets/blender/sanjusangendo_statues.blend (LOD0 in the visible
collection, LOD1/LOD2 in hidden collections) and renders heroes/previews/statues_lineup.png (three strips)
    blender -b --python blender/sites/statues_lineup.py -- [--no-blend] [--no-render]"""
import sys, os, math, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
from sites import statues_mesh as M
OUT = '/home/kazu/work/kyoto-assets/heroes/statues'
PREV = '/home/kazu/work/kyoto-assets/heroes/previews'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
index = json.load(open(os.path.join(OUT, 'index.json')))
order_n = ['narayana_kengo', 'nanda_ryuo', 'magora', 'kinnara', 'karura', 'kendatsuba', 'bishaja', 'sanshi_taisho', 'manzen_shahatsu', 'manibadara', 'bishamonten', 'daizurata_o']
order_c = ['basu_sen', 'daibon_tenno', 'taishaku_tenno', 'daibenkudoku_ten']
order_s = ['birurokusha', 'birubakusha', 'sasha_mawara', 'gobu_jogo', 'konjiki_kujaku_o', 'jinmo_nyo', 'konpira', 'hibakara', 'ashura', 'ihatsura', 'sagara_ryuo', 'misshaku_kongoshi']
allatt = order_n + order_c + order_s
rows = [['fujin', 'kannon_standing_a', 'kannon_standing_b', 'kannon_seated', 'kannon_standing_c', 'raijin'], allatt[0:7], allatt[7:14], allatt[14:21], allatt[21:28]]
rows = [[i for i in r if i in index] for r in rows]
sc = bpy.context.scene
cols = {}
for l in (0, 1, 2):
    c = bpy.data.collections.new(f'LOD{l}'); sc.collection.children.link(c); cols[l] = c
placed = {}
y0 = 0.0
for ri, row in enumerate(rows):
    x = 0.0
    for sid in row:
        bb = index[sid]['bbox']; w = bb[1][0] - bb[0][0]
        x += w / 2 + 0.25
        for l, fn in enumerate(index[sid]['lods']):
            me = M.npz_mesh(os.path.join(OUT, fn), f'{sid}_lod{l}')
            ob = bpy.data.objects.new(f'{sid}_lod{l}', me); cols[l].objects.link(ob)
            ob.location = (x, y0 - ri * 0.0, 0); ob['statue'] = sid; ob['lod'] = l
            if l: ob.hide_render = True; ob.hide_viewport = True
        placed[sid] = (ri, x)
        x += w / 2 + 0.25
    y0 -= 0.0
    for o in cols[0].objects:
        pass
# rows sit at different y so the .blend opens as a tidy grid
for o in list(bpy.data.objects):
    sid = o.get('statue')
    if sid is None: continue
    ri, x = placed[sid]
    o.location = (-x, -ri * 6.0, 0)
for l in (1, 2):
    cols[l].hide_viewport = True; cols[l].hide_render = True
if '--no-blend' not in argv:
    os.makedirs(os.path.dirname('/home/kazu/work/kyoto-assets/blender/'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath='/home/kazu/work/kyoto-assets/blender/sanjusangendo_statues.blend', compress=True)
    print('saved blend', flush=True)
if '--no-render' not in argv:
    M.setup_render(res=(3200, 1000), samples=24)
    me = bpy.data.meshes.new('floor'); s = 200
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new('floor', me); sc.collection.objects.link(fl)
    mm = bpy.data.materials.new('pv_floor'); mm.use_nodes = True
    mm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.016, 0.012, 1)
    mm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.4
    me.materials.append(mm)
    from mathutils import Vector
    strips = []
    for ri, row in enumerate(rows):
        xs = [-placed[i][1] for i in row]; x0, x1 = min(xs) - 0.8, max(xs) + 0.8
        hmax = max(index[i]['height_m'] for i in row)
        for o in bpy.data.objects:
            if o.get('statue') is not None and o.get('lod') == 0:
                o.hide_render = placed[o['statue']][0] != ri
        for o in [o for o in bpy.data.objects if o.name.startswith('pvL')]: bpy.data.objects.remove(o)
        cx = (x0 + x1) / 2; yrow = -ri * 6.0
        def area(name, pos, energy, col, size):
            ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = col; ld.size = size
            lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo)
            lo.location = pos; lo.rotation_euler = (Vector((cx, yrow, hmax * 0.45)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        span = x1 - x0
        gk = 1.0 if ri == 0 else 0.3          # the gilded strip vs the dark-wood strips
        area('pvL_key', (cx + span * 0.35, yrow + 9, hmax * 1.2 + 2), 7000 * span / 20 * gk, (1.0, 0.74, 0.48), span * 0.6)
        area('pvL_fill', (cx - span * 0.5, yrow + 6, hmax * 0.5 + 1), 1200 * span / 20 * gk, (0.78, 0.82, 1.0), span * 0.5)
        cd = bpy.data.cameras.get('lc') or bpy.data.cameras.new('lc'); cd.type = 'ORTHO'
        aspect = 3200 / 1000
        cd.ortho_scale = max(span * 1.02, hmax * 1.12 * aspect)
        co = bpy.data.objects.get('lc') or bpy.data.objects.new('lc', cd)
        if co.name not in sc.collection.objects: sc.collection.objects.link(co)
        sc.camera = co
        tgt = Vector((cx, yrow, cd.ortho_scale / aspect * 0.47)); cam = tgt + Vector((0, 30, 4.0))
        co.location = cam; co.rotation_euler = (tgt - cam).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(os.environ.get('STATUES_CLOSE', '/tmp'), f'statues_strip{ri}.png')
        sc.render.filepath = p; bpy.ops.render.render(write_still=True); strips.append(p)
    print('STRIPS', ' '.join(strips), flush=True)
