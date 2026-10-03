"""Blender bake stage: densify meshes, bake per-corner irradiance with Cycles, export arrays.

Irradiance convention: bake value B such that a white diffuse surface would render as B
(Cycles units).  The sun is baked only through its INDIRECT contribution; its direct light
is drawn in realtime (shadow maps) in the viewer.  Final: albedo * (irr + sun_direct)."""
import bpy, bmesh, math, os, time, json
import numpy as np
from mathutils import Vector


def densify(ob, max_edge, max_iter=12):
    """triangulate (ear clip for concave ngons) and split edges longer than max_edge."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    for it in range(max_iter):
        long = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long: break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(me); bm.free()
    me.update()


def gpu_setup(samples=256):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = (d.type == 'OPTIX')
    sc.cycles.device = 'GPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 4
    sc.render.bake.target = 'VERTEX_COLORS'
    sc.render.bake.margin = 0


def _bake(objs, attr, passes):
    for o in bpy.context.scene.objects:
        if o is not None: o.select_set(False)
    for o in objs:
        me = o.data
        ca = me.color_attributes.get(attr) or me.color_attributes.new(attr, 'FLOAT_COLOR', 'CORNER')
        me.color_attributes.active_color = ca
        me.attributes.active_color = ca
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='DIFFUSE', pass_filter=set(passes), target='VERTEX_COLORS')


def bake_irradiance(objs, sun_obj=None, samples=256, hide=()):
    """irr = sky direct + (sun+sky) indirect, stored in corner attribute 'irr'.  Objects in `hide` are excluded
    from the bake scene (they neither occlude nor reflect)."""
    for o in hide: o.hide_render = True
    gpu_setup(samples)
    t = time.time()
    _bake(objs, 'irr_ind', ['INDIRECT'])
    print(f'bake indirect {time.time()-t:.1f}s', flush=True)
    e = None
    if sun_obj is not None:
        e = sun_obj.data.energy; sun_obj.data.energy = 0.0
    t = time.time()
    _bake(objs, 'irr_dir', ['DIRECT'])
    print(f'bake sky-direct {time.time()-t:.1f}s', flush=True)
    if sun_obj is not None: sun_obj.data.energy = e
    for o in objs:
        me = o.data
        a = np.zeros(len(me.loops) * 4, np.float32); b = np.zeros_like(a)
        me.color_attributes['irr_ind'].data.foreach_get('color', a)
        me.color_attributes['irr_dir'].data.foreach_get('color', b)
        s = (a + b)
        ca = me.color_attributes.get('irr') or me.color_attributes.new('irr', 'FLOAT_COLOR', 'CORNER')
        ca.data.foreach_set('color', s)
    for o in hide: o.hide_render = False


def export_npz(objs, path, chunk=None):
    """write corner-level arrays per material: pos, nrm, irr, uv(optional), grouped.
    Output npz keys: mats (json), and per material i: p{i}, n{i}, c{i}, u{i}."""
    groups = {}
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        M = np.array(o.matrix_world)
        nl = len(me.loops)
        vco = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', vco); vco = vco.reshape(-1, 3)
        lv = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
        cn = np.zeros(nl * 3, np.float32); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
        irr = np.zeros(nl * 4, np.float32)
        if 'irr' in me.color_attributes: me.color_attributes['irr'].data.foreach_get('color', irr)
        irr = irr.reshape(-1, 4)
        uv = None
        if me.uv_layers.get('UVMap'):
            uv = np.zeros(nl * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
        tl = np.zeros(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
        tm = np.zeros(len(me.loop_triangles), np.int32); me.loop_triangles.foreach_get('material_index', tm)
        P = vco[lv] @ M[:3, :3].T + M[:3, 3]
        N = cn @ np.linalg.inv(M[:3, :3]).T
        N /= np.maximum(1e-9, np.linalg.norm(N, axis=1, keepdims=True))
        for mi, mat in enumerate(me.materials):
            sel = tl[tm == mi]
            if len(sel) == 0: continue
            name = mat.name
            g = groups.setdefault(name, {'p': [], 'n': [], 'c': [], 'u': []})
            corners = sel.ravel()
            g['p'].append(P[corners]); g['n'].append(N[corners]); g['c'].append(irr[corners])
            g['u'].append(uv[corners] if uv is not None else np.zeros((len(corners), 2), np.float32))
    names = sorted(groups)
    header = []; off = 0
    with open(path + '.raw', 'wb') as f:
        for name in names:
            g = groups[name]
            arrs = {'p': np.concatenate(g['p']).astype('<f4'), 'n': np.concatenate(g['n']).astype('<f4'),
                    'c': np.concatenate(g['c']).astype('<f4'), 'u': np.concatenate(g['u']).astype('<f4')}
            ent = {'mat': name, 'count': int(len(arrs['p']))}
            for k, a in arrs.items():
                b = a.tobytes(); f.write(b)
                ent[k] = [off, len(b)]; off += len(b)
            header.append(ent)
    json.dump(header, open(path + '.json', 'w'))
    tris = sum(e['count'] // 3 for e in header)
    print(f'export {path}: {len(names)} materials, {tris} triangles', flush=True)


_SUB = {}
def _sub_pattern(n):
    """barycentric corner coords (n*n, 3, 3) of the uniform subdivision of a triangle into n^2."""
    if n in _SUB: return _SUB[n]
    tris = []
    for i in range(n):
        for j in range(n - i):
            a = (i, j); b = (i + 1, j); c = (i, j + 1)
            tris.append((a, b, c))
            if i + j < n - 1:
                tris.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
    B = np.zeros((len(tris), 3, 3), np.float64)
    for t, tri in enumerate(tris):
        for k, (i, j) in enumerate(tri):
            B[t, k] = ((n - i - j) / n, i / n, j / n)
    _SUB[n] = B
    return B


def densify_soup(ob, max_edge, nmax=40):
    """replace ob's mesh with an unwelded triangle soup in which every triangle edge is shorter
    than ~max_edge (uniform per-triangle subdivision; T-junctions accepted).  Keeps materials,
    explicit UVs and shading normals (as custom corner normals)."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(me); bm.free(); me.update()
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    vco = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', vco); vco = vco.reshape(-1, 3)
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    cn = np.zeros(len(me.loops) * 3, np.float32); me.corner_normals.foreach_get('vector', cn); cn = cn.reshape(-1, 3)
    tl = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
    tm = np.zeros(nt, np.int32); me.loop_triangles.foreach_get('material_index', tm)
    has_uv = 'UVMap' in me.uv_layers
    if has_uv:
        uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    P = vco[lv[tl]]                     # (nt,3,3)
    N = cn[tl]
    U = uv[tl] if has_uv else None
    L = np.max(np.stack([np.linalg.norm(P[:, 1] - P[:, 0], axis=1), np.linalg.norm(P[:, 2] - P[:, 1], axis=1),
                         np.linalg.norm(P[:, 0] - P[:, 2], axis=1)], 1), axis=1)
    nsub = np.clip(np.ceil(L / max_edge), 1, nmax).astype(np.int32)
    outP, outN, outU, outM = [], [], [], []
    for n in np.unique(nsub):
        sel = np.where(nsub == n)[0]
        B = _sub_pattern(int(n))       # (k,3,3)
        # new corners: (len(sel), k, 3corners, 3xyz)
        outP.append(np.einsum('kcb,tbx->tkcx', B, P[sel]).reshape(-1, 3, 3))
        nn = np.einsum('kcb,tbx->tkcx', B, N[sel]).reshape(-1, 3, 3)
        outN.append(nn)
        if has_uv: outU.append(np.einsum('kcb,tbx->tkcx', B, U[sel]).reshape(-1, 3, 2))
        outM.append(np.repeat(tm[sel], B.shape[0]))
    P2 = np.concatenate(outP).reshape(-1, 3).astype(np.float32)
    N2 = np.concatenate(outN).reshape(-1, 3); N2 /= np.maximum(1e-9, np.linalg.norm(N2, axis=1, keepdims=True))
    M2 = np.concatenate(outM).astype(np.int32)
    ntri = len(M2)
    mats = list(me.materials)
    new = bpy.data.meshes.new(me.name + '_d')
    new.vertices.add(ntri * 3); new.vertices.foreach_set('co', P2.ravel())
    new.loops.add(ntri * 3); new.loops.foreach_set('vertex_index', np.arange(ntri * 3, dtype=np.int32))
    new.polygons.add(ntri); new.polygons.foreach_set('loop_start', np.arange(0, ntri * 3, 3, dtype=np.int32))
    for mt in mats: new.materials.append(mt)
    new.polygons.foreach_set('material_index', M2)
    new.polygons.foreach_set('use_smooth', np.ones(ntri, bool))
    if has_uv:
        U2 = np.concatenate(outU).reshape(-1, 2).astype(np.float32)
        new.uv_layers.new(name='UVMap').data.foreach_set('uv', U2.ravel())
    new.update(calc_edges=True)
    new.normals_split_custom_set(N2.astype(np.float32).tolist())
    old = ob.data; ob.data = new; bpy.data.meshes.remove(old)
    print(f'densify {ob.name}: {nt} -> {ntri} tris', flush=True)


def orient_faces(ob, viewpoints, max_vp=6, eps=0.02):
    """flip faces that are seen from their back side by an unobstructed viewpoint (interior spaces where the
    generators' winding is not trustworthy).  viewpoints: list of world (x,y,z)."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    import time
    t0 = time.time()
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm, epsilon=0.0)
    VP = np.array(viewpoints, float)
    flips = []; seen = 0
    for f in bm.faces:
        c = f.calc_center_median(); n = f.normal
        if n.length < 1e-9: continue
        d = np.linalg.norm(VP - np.array(c), axis=1)
        order = np.argsort(d)[:max_vp]
        vote = 0
        for k in order:
            p = Vector(VP[k]); dirv = p - c; dist = dirv.length
            if dist < 1e-3: continue
            dirv.normalize()
            side = n.dot(dirv)
            if abs(side) < 0.02: continue
            start = c + dirv * eps
            hit = tree.ray_cast(start, dirv, dist - eps * 2)
            if hit[0] is None:
                vote += 1 if side > 0 else -1
                if abs(vote) >= 2: break
        if vote != 0: seen += 1
        if vote < 0: flips.append(f)
    bmesh.ops.reverse_faces(bm, faces=flips)
    bm.transform(ob.matrix_world.inverted())
    bm.to_mesh(me); bm.free(); me.update()
    print(f'orient {ob.name}: {len(flips)} flipped of {seen} seen ({len(me.polygons)} faces) {time.time()-t0:.1f}s', flush=True)


def export_rooms(ob, rooms, base):
    """split a baked object into per-room exports by face centre inside each room's local box."""
    me = ob.data
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    vco = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', vco); vco = vco.reshape(-1, 3)
    tv = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', tv); tv = tv.reshape(-1, 3)
    C = vco[tv].mean(1) @ np.array(ob.matrix_world)[:3, :3].T + np.array(ob.matrix_world)[:3, 3]
    poly = np.zeros(nt, np.int32); me.loop_triangles.foreach_get('polygon_index', poly)
    owner = np.full(len(me.polygons), -1, np.int32)
    best = np.full(nt, 1e18)
    own_t = np.full(nt, -1, np.int32)
    for ri, (name, origin, rot, box) in enumerate(rooms):
        c, s = math.cos(rot), math.sin(rot)
        dx, dy = C[:, 0] - origin[0], C[:, 1] - origin[1]
        u = dx * c + dy * s; v = -dx * s + dy * c; z = C[:, 2] - origin[2]
        pad = 2.5
        inside = (u > box['u0'] - pad) & (u < box['u1'] + pad) & (v > box['v0'] - pad) & (v < box['v1'] + pad) & (z > box['z0'] - pad) & (z < box['z1'] + pad)
        # distance outside the tight box (0 inside) — the nearest room wins where boxes overlap
        du = np.maximum(0, np.maximum(box['u0'] - u, u - box['u1'])); dv = np.maximum(0, np.maximum(box['v0'] - v, v - box['v1']))
        d = du + dv + np.hypot(u - (box['u0'] + box['u1']) / 2, v - (box['v0'] + box['v1']) / 2) * 1e-3
        take = inside & (d < best)
        best[take] = d[take]; own_t[take] = ri
    owner[poly] = own_t
    print('room ownership: unassigned polys', int((owner < 0).sum()), flush=True)
    for ri, (name, origin, rot, box) in enumerate(rooms):
        sel = np.where(owner == ri)[0]
        if not len(sel): continue
        bpy.ops.object.select_all(action='DESELECT')
        dup = ob.copy(); dup.data = ob.data.copy(); bpy.context.scene.collection.objects.link(dup)
        bm = bmesh.new(); bm.from_mesh(dup.data); bm.faces.ensure_lookup_table()
        keep = set(sel.tolist())
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
        bm.to_mesh(dup.data); bm.free()
        export_npz([dup], base + name)
        bpy.data.objects.remove(dup, do_unlink=True)
