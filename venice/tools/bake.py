"""Cycles irradiance bake for city tiles (run in Blender):
blender -b --python bake.py -- BUILD_DIR [--tiles t_14_7,t_15_7] [--mode day|night] [--samples 256] [--margin 1]

For every target tile: reads t_i_j.npz (+ .fac.json), bakes per-vertex irradiance on the static mesh and the
facade grids, writes t_i_j.<mode>.npz with IRR (n,3) and GIRR (m,3) float16.  Neighbouring tiles within
`margin` are loaded as occluders/reflectors but not baked.

Day: irr = sky direct + all indirect (the sun's direct light is drawn live with shadow maps).
Night: irr = everything (lamps, windows, moon sky)."""
import bpy, bmesh, sys, os, json, math, time
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
BUILD = argv[0]
def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default
MODE = opt('--mode', 'day'); SAMPLES = int(opt('--samples', '256')); MARGIN = int(opt('--margin', '1'))
SKY = '/home/kazu/work/venice-assets/sky'
mats = json.load(open(os.path.join(BUILD, 'materials.json')))['mats']
ALB = np.array([m['albedo'] for m in mats], np.float32)
EMI = np.array([[c * m.get('emit', (0, 0))[0 if MODE == 'day' else 1] for c in m['albedo']] for m in mats], np.float32)
TINTED = np.array([m['name'] in ('wall_plaster', 'wood_paint') for m in mats])

def srgb2lin(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def make_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    info = json.load(open(os.path.join(SKY, MODE + '.json')))
    env.image = bpy.data.images.load(os.path.join(SKY, MODE + '.hdr'))
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    bg.inputs['Strength'].default_value = 1.0
    sun = None
    if MODE in ('day', 'night'):              # night: the moon (direct moonlight is baked, the viewer turns its light off)
        ld = bpy.data.lights.new('sun', 'SUN'); E = np.array(info['sun_rgb'])
        ld.energy = float(E.max()); ld.color = tuple((E / E.max()).tolist()); ld.angle = math.radians(0.53)
        sun = bpy.data.objects.new('sun', ld); sc.collection.objects.link(sun)
        az, el = math.radians(info['sun_az']), math.radians(info['sun_el'])
        d = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])   # towards the sun
        # a sun lamp shines along its local -Z: orient -Z to -d
        from mathutils import Vector
        sun.rotation_euler = Vector(tuple(d)).to_track_quat('Z', 'Y').to_euler()
    return sun

def material_attr():
    m = bpy.data.materials.new('alb'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); dif = nt.nodes.new('ShaderNodeBsdfDiffuse')
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'alb'; at.attribute_type = 'GEOMETRY'
    nt.links.new(at.outputs['Color'], dif.inputs['Color'])
    # emissive surfaces (lamps) light the scene: emission colour*strength in the 'emi' attribute
    em = nt.nodes.new('ShaderNodeEmission'); ea = nt.nodes.new('ShaderNodeAttribute'); ea.attribute_name = 'emi'; ea.attribute_type = 'GEOMETRY'
    nt.links.new(ea.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(dif.outputs['BSDF'], add.inputs[0]); nt.links.new(em.outputs['Emission'], add.inputs[1]); nt.links.new(add.outputs['Shader'], out.inputs['Surface'])
    return m

def mesh_obj(name, P, I, N, alb, mat, emi=None):
    me = bpy.data.meshes.new(name)
    nv = len(P); nt = len(I)
    me.vertices.add(nv); me.vertices.foreach_set('co', P.astype(np.float32).ravel())
    me.loops.add(nt * 3); me.loops.foreach_set('vertex_index', I.astype(np.int32).ravel())
    me.polygons.add(nt); me.polygons.foreach_set('loop_start', np.arange(0, nt * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(nt, bool))
    ln = N[I.ravel()].astype(np.float32)
    me.normals_split_custom_set(ln.tolist())
    ca = me.color_attributes.new('alb', 'FLOAT_COLOR', 'POINT')
    a4 = np.ones((nv, 4), np.float32); a4[:, :3] = alb
    ca.data.foreach_set('color', a4.ravel())
    ce = me.color_attributes.new('emi', 'FLOAT_COLOR', 'POINT')
    e4 = np.zeros((nv, 4), np.float32); e4[:, 3] = 1
    if emi is not None: e4[:, :3] = emi
    ce.data.foreach_set('color', e4.ravel())
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def tile_albedo(d):
    alb = ALB[d['MAT']]
    t = TINTED[d['MAT']]
    if t.any():
        alb = alb.copy()
        tint = srgb2lin(d['C0'][:, :3])
        alb[t] = np.clip(tint[t] * 0.62, 0, 1)
    return alb

def facade_albedo(fac, n):
    alb = np.zeros((n, 3), np.float32)
    for f in fac:
        nu, nz, zs = f['g']; k = nu * nz
        a = ALB[f['mat']]
        if mats[f['mat']]['name'] == 'wall_plaster': a = srgb2lin(f['tint']) * 0.62
        alb[f['go']:f['go'] + k] = a
    return alb

def inset_positions(P, N, I, depth=0.06, frac=0.3, lift=0.012):
    """bake sample points pulled a few cm into the faces that use them (away from creases and corners, like
    a lightmap texel centre) and lifted along the normal."""
    P = P.astype(np.float64); I = I.astype(np.int64)
    C = P[I].mean(axis=1)
    acc = np.zeros_like(P); cnt = np.zeros(len(P))
    for k in range(3):
        v = C - P[I[:, k]]
        np.add.at(acc, I[:, k], v); np.add.at(cnt, I[:, k], 1)
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

LANTERN = 3                                # props.T_NAMES.index('lantern')
def night_lights(n, d, fac, mat_emit):
    """street lanterns (point lights at the glass) and lit windows (emissive panes just in front of the facade)."""
    if 'IT' in d and len(d['IT']):
        sel = np.nonzero(d['IT'] == LANTERN)[0]
        for k in sel:
            p = d['IP'][k]; yaw = float(d['IY'][k])
            q = (float(p[0] + math.cos(yaw) * 0.55), float(p[1] + math.sin(yaw) * 0.55), float(p[2] - 0.45))
            ld = bpy.data.lights.new(f'{n}_l{k}', 'POINT'); ld.energy = 45.0; ld.color = (1.0, 0.70, 0.40); ld.shadow_soft_size = 0.08
            ob = bpy.data.objects.new(f'{n}_l{k}', ld); ob.location = q; bpy.context.scene.collection.objects.link(ob)
    # hand-modelled lamps (portico lanterns, lamp posts, chandeliers): a point light in each cluster of lamp glass
    GL = {m['id']: (40.0 if m['name'] == 'street_glass' else 14.0) for m in mats if m['name'] in ('street_glass', 'lamp_glass')}
    if GL and len(d['I']):
        T = d['I'].reshape(-1, 3); fm = d['MAT'][T[:, 0]]
        sel = np.isin(fm, list(GL))
        if sel.any():
            C = d['P'][T[sel]].mean(1); E = np.array([GL[int(k)] for k in fm[sel]])
            cells = {}
            for c, e in zip(C, E):
                key = tuple(np.floor(c / 0.7).astype(int))
                hit = None
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            q = (key[0] + dx, key[1] + dy, key[2] + dz)
                            for cl in cells.get(q, ()):
                                if np.linalg.norm(cl[0] / cl[1] - c) < 0.6: hit = cl; break
                            if hit: break
                        if hit: break
                    if hit: break
                if hit: hit[0] += c; hit[1] += 1
                else: cells.setdefault(key, []).append([c.astype(np.float64).copy(), 1, e])
            k = 0
            for lst in cells.values():
                for (s_, cnt, e) in lst:
                    q = s_ / cnt
                    ld = bpy.data.lights.new(f'{n}_h{k}', 'POINT'); ld.energy = float(e); ld.color = (1.0, 0.70, 0.40); ld.shadow_soft_size = 0.06
                    ob = bpy.data.objects.new(f'{n}_h{k}', ld); ob.location = (float(q[0]), float(q[1]), float(q[2])); bpy.context.scene.collection.objects.link(ob)
                    k += 1
            print(f'  {n}: {k} hero lamps', flush=True)
    V = []; I = []
    for f in fac:
        p0 = np.array(f['p0']); p1 = np.array(f['p1']); L = max(f['L'], 1e-6); dr = (p1 - p0) / L; nn = np.array(f['n'])
        for o in f['open']:
            t, u, z, w, h, fl = o
            if not (fl & 128) or t in (5, 6, 7): continue
            c = p0 + dr * u + nn * 0.04
            a = c - dr * w * 0.42; b = c + dr * w * 0.42
            base = len(V)
            V += [(a[0], a[1], z + 0.05), (b[0], b[1], z + 0.05), (b[0], b[1], z + h * 0.9), (a[0], a[1], z + h * 0.9)]
            # winding so the pane faces out of the wall (along n)
            if np.dot(np.cross(np.array(V[base + 1]) - np.array(V[base]), np.array(V[base + 2]) - np.array(V[base])), np.r_[nn, 0]) >= 0:
                I += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
            else:
                I += [(base, base + 2, base + 1), (base, base + 3, base + 2)]
    if V:
        V = np.array(V, np.float32); I = np.array(I, np.int32)
        me = bpy.data.meshes.new(n + '_win'); me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
        me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel())
        me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32))
        me.update(calc_edges=True); me.materials.append(mat_emit)
        ob = bpy.data.objects.new(n + '_win', me); bpy.context.scene.collection.objects.link(ob)

# night: floodlights on the Basilica's west front (from the piazza) and on the Campanile, as in Venice
# (world xyz of the lamp, xyz it aims at, watts, cone degrees); lights only, nothing drawn
FLOOD = [((-2.31, 22.70, 14.1), (27.15, 33.85, 12.1), 1500.0, 46.0), ((-4.66, 30.87, 14.1), (25.28, 40.39, 12.1), 1500.0, 46.0),
         ((-7.14, 39.52, 14.1), (23.29, 47.31, 12.1), 1500.0, 46.0), ((-9.48, 47.69, 14.1), (21.42, 53.84, 12.1), 1500.0, 46.0),
         ((-30.0, 8.0, 4.0), (0.0, 0.0, 48.0), 2500.0, 34.0), ((14.0, -32.0, 4.0), (0.0, 0.0, 48.0), 2500.0, 34.0)]

def floodlights():
    from mathutils import Vector
    for k, (p, t, w, deg) in enumerate(FLOOD):
        ld = bpy.data.lights.new(f'flood{k}', 'SPOT'); ld.energy = w; ld.color = (1.0, 0.84, 0.66)
        ld.spot_size = math.radians(deg); ld.spot_blend = 0.6; ld.shadow_soft_size = 0.3
        ob = bpy.data.objects.new(f'flood{k}', ld); ob.location = p
        ob.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.collection.objects.link(ob)

def material_window():
    m = bpy.data.materials.new('win'); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.72, 0.42, 1.0); em.inputs['Strength'].default_value = 3.0
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m

def main():
    t0 = time.time()
    clear()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for dv in prefs.devices: dv.use = (dv.type == 'OPTIX')
    sc.cycles.device = 'GPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 0
    sc.render.bake.target = 'VERTEX_COLORS'; sc.render.bake.margin = 0
    sun = make_world()
    mat = material_attr()
    mat_win = material_window() if MODE == 'night' else None
    if MODE == 'night': floodlights()
    allt = json.load(open(os.path.join(BUILD, 'tiles.json')))
    names = {m['name'] for m in allt}
    targets = opt('--tiles').split(',') if opt('--tiles') else sorted(names)
    tij = lambda n: tuple(int(v) for v in n.split('_')[1:3])
    want = set(targets)
    load = set()
    for n in targets:
        i, j = tij(n)
        for di in range(-MARGIN, MARGIN + 1):
            for dj in range(-MARGIN, MARGIN + 1):
                m = f't_{i + di}_{j + dj}'
                if m in names: load.add(m)
    objs = {}
    xs = []
    for n in sorted(load):
        d = np.load(os.path.join(BUILD, n + '.npz'))
        fac = json.load(open(os.path.join(BUILD, n + '.fac.json')))['fac']
        # bake positions are nudged off coincident geometry (1 cm along the normal; facade grids also pulled
        # 15 cm under the eave and 10 cm in from the corners) — the results belong to the original vertices
        ob = mesh_obj(n + '_m', inset_positions(d['P'], d['N'], d['I']), d['I'], d['N'], tile_albedo(d), mat, EMI[d['MAT']]) if len(d['I']) else None
        GP = d['GP'].copy()
        for f in fac:
            nu, nz, zs = f['g']; o = f['go']; k = nu * nz
            p0 = np.array(f['p0']); p1 = np.array(f['p1']); L = max(f['L'], 1e-3); dr = (p1 - p0) / L
            q = GP[o:o + k]
            u = np.clip((q[:, 0] - p0[0]) * dr[0] + (q[:, 1] - p0[1]) * dr[1], min(0.1, L / 2), max(L - 0.1, L / 2))
            q[:, 0] = p0[0] + dr[0] * u + f['n'][0] * 0.02; q[:, 1] = p0[1] + dr[1] * u + f['n'][1] * 0.02
            q[:, 2] = np.minimum(q[:, 2], max(zs, f['zt'] - 0.18))
        gb = mesh_obj(n + '_g', GP, d['GI'], d['GN'], facade_albedo(fac, len(d['GP'])), mat) if len(d['GI']) else None
        pb = None
        if 'PP' in d and len(d['PP']):
            # one tiny triangle per prop instance, facing the probe normal (results averaged per instance)
            PP = d['PP'].astype(np.float64); PN = d['PN'].astype(np.float64)
            a = np.cross(PN, np.array([0.0, 0.0, 1.0])); bad = np.linalg.norm(a, axis=1) < 1e-3
            a[bad] = np.array([1.0, 0, 0]); a /= np.linalg.norm(a, axis=1, keepdims=True); b2 = np.cross(PN, a)
            V = np.stack([PP + a * 0.03, PP - a * 0.015 + b2 * 0.026, PP - a * 0.015 - b2 * 0.026], 1).reshape(-1, 3)
            I = np.arange(len(V)).reshape(-1, 3)
            pb = mesh_obj(n + '_p', V, I, np.repeat(PN, 3, axis=0), np.full((len(V), 3), 0.3, np.float32), mat)
        objs[n] = (ob, gb, pb)
        if MODE == 'night': night_lights(n, d, fac, mat_win)
        if len(d['P']): xs.append(d['P'].min(0)); xs.append(d['P'].max(0))
    # water plane (dark, slightly glossy is ignored in a diffuse bake)
    lo = np.min(xs, axis=0) - 300; hi = np.max(xs, axis=0) + 300
    wp = np.array([[lo[0], lo[1], 0], [hi[0], lo[1], 0], [hi[0], hi[1], 0], [lo[0], hi[1], 0]], np.float32)
    mesh_obj('water', wp, np.array([[0, 1, 2], [0, 2, 3]]), np.tile([0, 0, 1.0], (4, 1)), np.full((4, 3), 0.035, np.float32), mat)
    print(f'scene ready {time.time()-t0:.1f}s: {len(load)} tiles loaded, {len(want)} to bake', flush=True)
    bake_objs = [o for n in sorted(want) if n in objs for o in objs[n] if o is not None]
    t1 = time.time()
    if MODE == 'day':
        bake_attr(bake_objs, 'ind', ['INDIRECT'])
        print(f'indirect {time.time()-t1:.1f}s', flush=True); t1 = time.time()
        e = sun.data.energy; sun.data.energy = 0.0
        bake_attr(bake_objs, 'dir', ['DIRECT'])
        sun.data.energy = e
        print(f'sky direct {time.time()-t1:.1f}s', flush=True)
        parts = ('ind', 'dir')
    else:
        bake_attr(bake_objs, 'all', ['DIRECT', 'INDIRECT'])
        print(f'night {time.time()-t1:.1f}s', flush=True)
        parts = ('all',)
    for n in sorted(want):
        if n not in objs: continue
        ob, gb, pb = objs[n]
        res = {}
        if pb is not None: res['PIRR'] = sum(corner_to_point(pb, p) for p in parts).reshape(-1, 3, 3).mean(1).astype(np.float16)
        if ob is not None: res['IRR'] = sum(corner_to_point(ob, p) for p in parts).astype(np.float16)
        if gb is not None: res['GIRR'] = sum(corner_to_point(gb, p) for p in parts).astype(np.float16)
        np.savez_compressed(os.path.join(BUILD, f'{n}.{MODE}.npz'), **res)
    print(f'done {time.time()-t0:.1f}s', flush=True)

main()
