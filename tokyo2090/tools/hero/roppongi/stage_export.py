"""Export near.glb / mid.glb / far.glb, collide.obj, hero.json (stats)."""
import bpy, json, os, pickle, math
import numpy as np
import lib

SPAWNS = [
    {'name': '66プラザ ママン', 'x': 27.0, 'y': 106.5, 'heading': 4.08,
     'note': '66 Plaza in front of Maman, Mori Tower behind (looking SW)'},
    {'name': '毛利庭園の池', 'x': 60.0, 'y': 27.0, 'heading': 1.3,
     'note': 'Mohri Garden: the still pool with lilies and scum, wild cherries on the island (looking ENE)'},
    {'name': 'けやき坂', 'x': -72.0, 'y': -87.0, 'heading': 1.62,
     'note': 'Keyakizaka-dori under the zelkova canopy, looking east down the slope'},
]


def gltf(path, objs, draco=True, quality=82):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_image_format='WEBP',
                              export_image_quality=quality, export_draco_mesh_compression_enable=draco,
                              export_draco_mesh_compression_level=7, export_draco_position_quantization=16,
                              export_draco_normal_quantization=10, export_draco_texcoord_quantization=16,
                              export_draco_color_quantization=8, export_vertex_color='ACTIVE',
                              export_all_vertex_colors=False, export_yup=True, export_apply=True,
                              export_extras=False, export_tangents=False, export_unused_images=False)


def tri_count(objs):
    n = 0
    for o in objs:
        me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        n += sum(len(p.vertices) - 2 for p in me.polygons)
        o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return n


def glb_stats(path):
    """triangles, draw calls (primitives) and texture count straight from the glb json"""
    import struct
    b = open(path, 'rb').read()
    jl = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    prims = sum(len(m['primitives']) for m in j['meshes'])
    tris = 0
    for m in j['meshes']:
        for p in m['primitives']:
            if 'indices' in p:
                tris += j['accessors'][p['indices']]['count'] // 3
    return {'tris': tris, 'draw_calls': prims, 'images': len(j.get('images', [])), 'mb': round(len(b) / 1048576, 2)}


def write_collide(path):
    polys = pickle.load(open(lib.WORK + 'collide_polys.pkl', 'rb'))
    V = []; F = []
    for p in polys:
        if len(p) < 3:
            continue
        base = len(V) + 1
        V.extend(p)
        for k in range(1, len(p) - 1):
            F.append((base, base + k, base + k + 1))
    with open(path, 'w') as f:
        f.write('# roppongi hero collision proxy (local coords, z absolute)\no collide\n')
        for v in V:
            f.write('v %.3f %.3f %.3f\n' % v)
        for t in F:
            f.write('f %d %d %d\n' % t)
    return len(F)


def run(log, lods=None):
    lods = lods or (('mid',) if lib.mid() else ('near',))
    os.makedirs(lib.OUT, exist_ok=True)
    stats = {}
    hj = lib.OUT + 'hero.json'
    old = json.load(open(hj)) if os.path.exists(hj) else {}
    if 'near' in lods:
        bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'baked.blend')
        objs = [o for o in bpy.data.collections['near'].objects if o.type == 'MESH']
        gltf(lib.OUT + 'near.glb', objs)
        s = glb_stats(lib.OUT + 'near.glb')
        log('near', s)
        stats.update({'near_tris': s['tris'], 'near_mb': s['mb'], 'draw_calls': s['draw_calls'], 'near_images': s['images']})
    if 'mid' in lods:
        bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'baked_mid.blend')
        for im in bpy.data.images:
            if im.size[0] > 1024:
                im.scale(1024, 1024 * im.size[1] // im.size[0])
        objs = [o for o in bpy.data.collections['near'].objects if o.type == 'MESH']
        gltf(lib.OUT + 'mid.glb', objs, quality=78)
        s = glb_stats(lib.OUT + 'mid.glb')
        log('mid', s)
        stats.update({'mid_tris': s['tris'], 'mid_mb': s['mb'], 'mid_draw_calls': s['draw_calls']})
    nc = write_collide(lib.OUT + 'collide.obj')
    stats['collide_tris'] = nc
    for k in ('mid', 'far'):
        p = lib.OUT + k + '.glb'
        if os.path.exists(p):
            s = glb_stats(p)
            stats['%s_tris' % k] = s['tris']; stats['%s_mb' % k] = s['mb']
    ctx = json.load(open(lib.WORK + 'ctx.json'))
    out = {'district': 'roppongi', 'origin': [2650, 50], 'spawns': SPAWNS, 'labels': ctx['labels'],
           'stats': dict(old.get('stats', {}), **stats)}
    out['labels'].insert(0, {'name': '六本木ヒルズ森タワー', 'x': -49.6, 'y': 49.4, 'z': 278.0, 'kind': 'building'})
    json.dump(out, open(hj, 'w'), ensure_ascii=False, indent=1)
    log('hero.json', out['stats'])
