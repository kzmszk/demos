"""Cycles irradiance bake for Kyoto tiles (run in Blender):
blender -b --python bake.py -- BUILD_DIR --tiles t_6_16,t_6_15 [--samples 128] [--margin 1] [--sky autumn]

Per target tile writes t_i_j.bake.npz: IRR (n,3) float16 = sky light + all bounce light (the evening sun's direct
light is drawn live, or from SUN far away), SUN (n,) float16 = visibility of the sun (ray cast, 0/1 with a soft edge).
Neighbouring tiles within `margin` are loaded as occluders / reflectors.  Ground albedo comes from the surface raster."""
import bpy, sys, os, json, math, time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--') + 1:]
BUILD = argv[0]
def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
SAMPLES = int(opt('--samples', '128')); MARGIN = int(opt('--margin', '1')); SKYN = opt('--sky', 'autumn')
SKY = '/home/kazu/work/kyoto-assets/sky'
M = json.load(open(os.path.join(BUILD, 'materials.json')))
mats = M['mats']
ALB = np.array([m['albedo'] for m in mats], np.float32)
EMI = np.array([[c * m.get('emit', 0.0) for c in m['albedo']] for m in mats], np.float32)
KIND = np.array([m['kind'] for m in mats])
TINTED = np.isin(KIND, ['wall', 'roofmetal', 'cloth'])
SALB = np.array([s['albedo'] for s in M['surf']], np.float32)

def srgb2lin(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def make_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground'); env = nt.nodes.new('ShaderNodeTexEnvironment')
    info = json.load(open(os.path.join(SKY, SKYN + '.json')))
    env.image = bpy.data.images.load(os.path.join(SKY, SKYN + '.hdr'))
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    ld = bpy.data.lights.new('sun', 'SUN'); E = np.array(info['sun_rgb'])
    ld.energy = float(E.max()); ld.color = tuple((E / E.max()).tolist()); ld.angle = math.radians(0.53)
    sun = bpy.data.objects.new('sun', ld); sc.collection.objects.link(sun)
    az, el = math.radians(info['sun_az']), math.radians(max(info['sun_el'], 3.0))
    d = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])
    sun.rotation_euler = Vector(tuple(d)).to_track_quat('Z', 'Y').to_euler()
    return sun, d

def material_attr():
    m = bpy.data.materials.new('alb'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); dif = nt.nodes.new('ShaderNodeBsdfDiffuse')
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'alb'; at.attribute_type = 'GEOMETRY'
    nt.links.new(at.outputs['Color'], dif.inputs['Color'])
    em = nt.nodes.new('ShaderNodeEmission'); ea = nt.nodes.new('ShaderNodeAttribute'); ea.attribute_name = 'emi'; ea.attribute_type = 'GEOMETRY'
    nt.links.new(ea.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(dif.outputs['BSDF'], add.inputs[0]); nt.links.new(em.outputs['Emission'], add.inputs[1]); nt.links.new(add.outputs['Shader'], out.inputs['Surface'])
    return m

def mesh_obj(name, P, I, N, alb, mat, emi=None):
    I = I[(I[:, 0] != I[:, 1]) & (I[:, 1] != I[:, 2]) & (I[:, 0] != I[:, 2])]
    N = np.array(N, np.float32); N[np.linalg.norm(N, axis=1) < 1e-6] = (0.0, 0.0, 1.0)
    me = bpy.data.meshes.new(name)
    nv = len(P); nt = len(I)
    me.vertices.add(nv); me.vertices.foreach_set('co', P.astype(np.float32).ravel())
    me.loops.add(nt * 3); me.loops.foreach_set('vertex_index', I.astype(np.int32).ravel())
    me.polygons.add(nt); me.polygons.foreach_set('loop_start', np.arange(0, nt * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(nt, bool))
    me.normals_split_custom_set(N[I.ravel()].astype(np.float32).tolist())
    ca = me.color_attributes.new('alb', 'FLOAT_COLOR', 'POINT'); a4 = np.ones((nv, 4), np.float32); a4[:, :3] = alb; ca.data.foreach_set('color', a4.ravel())
    ce = me.color_attributes.new('emi', 'FLOAT_COLOR', 'POINT'); e4 = np.zeros((nv, 4), np.float32); e4[:, 3] = 1
    if emi is not None: e4[:, :3] = emi
    ce.data.foreach_set('color', e4.ravel())
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def albedo(n, d):
    MAT = d['MAT']; alb = ALB[MAT].copy()
    t = TINTED[MAT]
    if t.any(): alb[t] = np.clip(srgb2lin(d['C0'][t, :3]) * 0.75, 0, 1)
    g = KIND[MAT] == 'ground'
    if g.any() and 'SURF' in d:
        S = d['SURF']                                             # row 0 = south
        bb = d['BBOX']
        res = (bb[2] - bb[0]) / S.shape[1]
        P = d['P'][g]
        ix = np.clip(((P[:, 0] - bb[0]) / res).astype(int), 0, S.shape[1] - 1); iy = np.clip(((P[:, 1] - bb[1]) / res).astype(int), 0, S.shape[0] - 1)
        alb[g] = SALB[S[iy, ix]]
        vs = d['C1'][g][:, 3]
        alb[np.nonzero(g)[0][vs > 0]] = SALB[vs[vs > 0]]
    return alb

def inset_positions(P, N, I, depth=0.05, frac=0.3, lift=0.012):
    P = P.astype(np.float64); I = I.astype(np.int64)
    C = P[I].mean(axis=1)
    acc = np.zeros_like(P); cnt = np.zeros(len(P))
    for k in range(3):
        np.add.at(acc, I[:, k], C - P[I[:, k]]); np.add.at(cnt, I[:, k], 1)
    acc /= np.maximum(cnt, 1)[:, None]
    L = np.linalg.norm(acc, axis=1, keepdims=True)
    step = np.minimum(depth, L * frac)
    off = np.where(L > 1e-6, acc / np.maximum(L, 1e-9) * step, 0)
    return (P + off + N.astype(np.float64) * lift).astype(np.float32)

def bake_attr(objs, attr, passes):
    for o in bpy.context.scene.objects: o.select_set(False)
    for o in objs:
        me = o.data
        ca = me.color_attributes.get(attr) or me.color_attributes.new(attr, 'FLOAT_COLOR', 'CORNER')
        me.color_attributes.active_color = ca; me.attributes.active_color = ca
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE', pass_filter=set(passes), target='VERTEX_COLORS')

def corner_to_point(o, attr):
    me = o.data; nl = len(me.loops)
    c = np.zeros(nl * 4, np.float32); me.color_attributes[attr].data.foreach_get('color', c); c = c.reshape(-1, 4)[:, :3]
    lv = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
    acc = np.zeros((len(me.vertices), 3), np.float64); cnt = np.zeros(len(me.vertices))
    np.add.at(acc, lv, c); np.add.at(cnt, lv, 1)
    return (acc / np.maximum(cnt, 1)[:, None]).astype(np.float32)

def main():
    global TILES
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for dv in prefs.devices: dv.use = (dv.type == 'OPTIX')
    sc.cycles.device = 'GPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 0
    sc.render.bake.target = 'VERTEX_COLORS'; sc.render.bake.margin = 0
    sun, sdir = make_world()
    mat = material_attr()
    TILES = json.load(open(os.path.join(BUILD, 'tiles.json')))
    names = {m['name'] for m in TILES}
    targets = opt('--tiles').split(',')
    tij = lambda n: tuple(int(v) for v in n.split('_')[1:3])
    load = set()
    for n in targets:
        i, j = tij(n)
        for di in range(-MARGIN, MARGIN + 1):
            for dj in range(-MARGIN, MARGIN + 1):
                m = f't_{i + di}_{j + dj}'
                if m in names: load.add(m)
    objs = {}; data = {}; allP = []; allI = []; off = 0
    for n in sorted(load):
        d = dict(np.load(os.path.join(BUILD, n + '.npz')))
        if not len(d['I']): continue
        a = albedo(n, d)
        objs[n] = mesh_obj(n, inset_positions(d['P'], d['N'], d['I']), d['I'], d['N'], a, mat, EMI[d['MAT']])
        data[n] = d
        allP.append(d['P']); allI.append(d['I'] + off); off += len(d['P'])
    print(f'scene ready {time.time()-t0:.1f}s: {len(load)} tiles loaded, {len(targets)} to bake', flush=True)
    want = [n for n in targets if n in objs]
    t1 = time.time()
    bake_attr([objs[n] for n in want], 'ind', ['INDIRECT'])
    print(f'indirect {time.time()-t1:.1f}s', flush=True); t1 = time.time()
    e = sun.data.energy; sun.data.energy = 0.0
    bake_attr([objs[n] for n in want], 'dir', ['DIRECT'])
    sun.data.energy = e
    print(f'sky direct {time.time()-t1:.1f}s', flush=True); t1 = time.time()
    # sun visibility: rays toward the sun against everything loaded (plus a margin of terrain beyond)
    bvh = BVHTree.FromPolygons(np.concatenate(allP).tolist(), np.concatenate(allI).tolist(), all_triangles=True, epsilon=0.0)
    sd = Vector(tuple(sdir))
    for n in want:
        d = data[n]; P = d['P']; N = d['N']
        ndl = N @ sdir
        vis = np.zeros(len(P), np.float32)
        for k in np.nonzero(ndl > 0.01)[0]:
            o = Vector((float(P[k, 0] + N[k, 0] * 0.08), float(P[k, 1] + N[k, 1] * 0.08), float(P[k, 2] + N[k, 2] * 0.08)))
            hit = bvh.ray_cast(o, sd, 3000.0)
            vis[k] = 0.0 if hit[0] is not None else 1.0
        irr = corner_to_point(objs[n], 'ind') + corner_to_point(objs[n], 'dir')
        np.savez_compressed(os.path.join(BUILD, f'{n}.bake.npz'), IRR=irr.astype(np.float16), SUN=vis.astype(np.float16))
    print(f'sun rays {time.time()-t1:.1f}s; done {time.time()-t0:.1f}s', flush=True)

main()
