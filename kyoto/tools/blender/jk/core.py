"""jk — a Japanese-architecture kit for Blender (bpy + numpy).  Geometry is accumulated in numpy per material
(fast), then turned into Blender objects (to inspect, render, save as .blend) and exported for the viewer.

Units: metres.  World frame: the Kyoto local frame (x east, y north, z = height above T.P.); site scripts usually
build in a building frame (u along the front, v depth, w up) and place it with Frame.

Every face carries a material NAME from the viewer's table (tools/gen/materials.py MATS) and UVs in metres.
Vertex colours: C0 = tint (rgb 0-255) + a, C1 = (param y, seed z, flags w) like the generic city (gen/city.py)."""
import math
import numpy as np

# ------------------------------------------------------------------ material names (must exist in gen/materials.py)
MATS = None
def mats():
    global MATS
    if MATS is None:
        import json, os
        p = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'public', 'data', 'materials.json')
        MATS = {m['name']: m for m in json.load(open(p))['mats']}
    return MATS

def face_normals(P, I):
    n = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
    return n / l

def vertex_normals(P, I):
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    N = np.zeros_like(P)
    for k in range(3): np.add.at(N, I[:, k], fn)
    l = np.linalg.norm(N, axis=1, keepdims=True); l[l == 0] = 1
    return N / l

def box_uv(P, N):
    """planar uv in metres by the dominant normal axis (walls: along / up; floors: x, y)"""
    a = np.abs(N)
    uv = np.zeros((len(P), 2))
    zx = a[:, 2] >= np.maximum(a[:, 0], a[:, 1])
    xx = ~zx & (a[:, 0] >= a[:, 1]); yy = ~zx & ~xx
    uv[zx] = P[zx][:, [0, 1]]
    uv[xx] = np.stack([P[xx][:, 1] * np.sign(N[xx][:, 0]), P[xx][:, 2]], 1)
    uv[yy] = np.stack([-P[yy][:, 0] * np.sign(N[yy][:, 1]), P[yy][:, 2]], 1)
    return uv

class Builder:
    """accumulates triangles per (material, tag).  tag groups geometry for export: 'main' (drawn + baked),
    'detail' (near-only small parts), 'walk' (walk surfaces, not drawn), 'block' (collision only, not drawn)."""
    def __init__(self, name='site'):
        self.name = name
        self.parts = []                         # dicts: P, N, UV, I, mat, tag, c0, c1
        self.lamps = []                         # (xyz, watts, rgb)
        self.trees = []                         # (species, x, y, z, scale, yaw)
        self.xf = None                          # optional 4x4 placement applied on add (see Frame)

    def add(self, P, I, mat, UV=None, N=None, smooth=False, tag='main', c0=(255, 255, 255, 0), c1=(0, 0, 0, 0)):
        P = np.asarray(P, np.float64).reshape(-1, 3); I = np.asarray(I, np.int64).reshape(-1, 3)
        if len(I) == 0: return
        if self.xf is not None:
            P = P @ self.xf[:3, :3].T + self.xf[:3, 3]
            if N is not None: N = np.asarray(N, np.float64).reshape(-1, 3) @ self.xf[:3, :3].T
        I = I[(I[:, 0] != I[:, 1]) & (I[:, 1] != I[:, 2]) & (I[:, 0] != I[:, 2])]
        if len(I) == 0: return
        if N is None and not smooth:
            fn = face_normals(P, I)
            idx = I.reshape(-1); P2 = P[idx]
            UV2 = (np.asarray(UV, np.float64).reshape(-1, 2)[idx] if UV is not None else None)
            N = np.repeat(fn, 3, axis=0); P = P2; UV = UV2; I = np.arange(len(P)).reshape(-1, 3)
            # per-vertex colours follow the corners too
            if np.asarray(c0).ndim == 2: c0 = np.asarray(c0, np.uint8)[idx]
            if np.asarray(c1).ndim == 2: c1 = np.asarray(c1, np.uint8)[idx]
        elif N is None:
            N = vertex_normals(P, I)
        N = np.asarray(N, np.float64).reshape(-1, 3)
        if UV is None: UV = box_uv(P, N)
        self.parts.append(dict(P=P.astype(np.float32), N=N.astype(np.float32), UV=np.asarray(UV, np.float32).reshape(-1, 2), I=I.astype(np.int64), mat=mat, tag=tag,
                               c0=np.broadcast_to(np.asarray(c0, np.uint8), (len(P), 4)).copy() if np.asarray(c0).ndim == 1 else np.asarray(c0, np.uint8),
                               c1=np.broadcast_to(np.asarray(c1, np.uint8), (len(P), 4)).copy() if np.asarray(c1).ndim == 1 else np.asarray(c1, np.uint8)))

    TREE_SPECIES = ['momiji', 'ichou', 'sakura', 'keyaki', 'matsu', 'sugi', 'hinoki', 'kashi', 'yanagi', 'tsutsuji', 'take']
    def tree(self, species, x, y, z, scale=1.0, yaw=0.0):
        """plant a tree of the viewer's species (drawn by the tree system, not part of the mesh): x, y, z world"""
        if self.xf is not None:
            p = self.xf[:3, :3] @ np.array([x, y, z], float) + self.xf[:3, 3]; x, y, z = p
            yaw += math.atan2(self.xf[1, 0], self.xf[0, 0])
        self.trees.append((self.TREE_SPECIES.index(species), float(x), float(y), float(z), float(scale), float(yaw)))
    def lamp(self, x, y, z, watts=10.0, rgb=(1.0, 0.62, 0.32)):
        if self.xf is not None:
            p = self.xf[:3, :3] @ np.array([x, y, z], float) + self.xf[:3, 3]; x, y, z = p
        self.lamps.append(((float(x), float(y), float(z)), float(watts), tuple(rgb)))

    def ntri(self, tag=None):
        return int(sum(len(p['I']) for p in self.parts if tag is None or p['tag'] == tag))

    def merged(self, tags=('main', 'detail')):
        """concatenate parts (by tag) -> arrays P, N, UV, I, MAT (names), C0, C1, TAG"""
        ps = [p for p in self.parts if p['tag'] in tags]
        if not ps: return None
        off = 0; I = []; names = []
        for p in ps:
            I.append(p['I'] + off); off += len(p['P'])
        out = dict(P=np.concatenate([p['P'] for p in ps]), N=np.concatenate([p['N'] for p in ps]), UV=np.concatenate([p['UV'] for p in ps]),
                   I=np.concatenate(I), C0=np.concatenate([p['c0'] for p in ps]), C1=np.concatenate([p['c1'] for p in ps]))
        out['MATN'] = np.concatenate([np.full(len(p['P']), p['mat'], dtype=object) for p in ps])
        out['TAG'] = np.concatenate([np.full(len(p['P']), p['tag'], dtype=object) for p in ps])
        return out

# ------------------------------------------------------------------ frames: build in a local frame, place in the world
class Frame:
    """a building frame: origin (x, y, z) in the world, yaw (radians, the local +u axis direction, ccw from east).
    Use `with Frame(b, ox, oy, oz, yaw):` to add geometry in local coordinates (u, v, w)."""
    def __init__(self, b, ox, oy, oz, yaw):
        self.b = b; c, s = math.cos(yaw), math.sin(yaw)
        self.M = np.array([[c, -s, 0, ox], [s, c, 0, oy], [0, 0, 1, oz], [0, 0, 0, 1.0]])
    def __enter__(self):
        self.prev = self.b.xf
        self.b.xf = self.M if self.prev is None else self.prev @ self.M
        return self
    def __exit__(self, *a):
        self.b.xf = self.prev
    def world(self, p):
        p = np.asarray(p, float)
        return (self.M[:3, :3] @ p) + self.M[:3, 3]

def frame_from_rect(rect):
    """(cx, cy, length, width, yaw) of a minimum rotated rectangle of a shapely polygon: length along yaw"""
    xs, ys = rect.exterior.coords.xy
    e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
    L0, L1 = np.linalg.norm(e0), np.linalg.norm(e1)
    d = e0 if L0 >= L1 else e1
    c = rect.centroid
    return c.x, c.y, max(L0, L1), min(L0, L1), math.atan2(d[1], d[0])

# ------------------------------------------------------------------ Blender side
def blender_materials():
    """one Blender material per viewer material, coloured roughly like the viewer (for renders)"""
    import bpy
    out = {}
    for name, m in mats().items():
        mm = bpy.data.materials.get('jk_' + name) or bpy.data.materials.new('jk_' + name)
        mm.use_nodes = True
        bs = mm.node_tree.nodes.get('Principled BSDF')
        a = m['albedo']
        bs.inputs['Base Color'].default_value = (a[0], a[1], a[2], 1)
        bs.inputs['Roughness'].default_value = {'gold': 0.3, 'metal': 0.5, 'paint': 0.55, 'glass': 0.05, 'water': 0.05}.get(m['kind'], 0.8)
        if m['kind'] in ('gold', 'metal'): bs.inputs['Metallic'].default_value = 1.0 if m['kind'] == 'gold' else 0.5
        if m['kind'] == 'emissive':
            bs.inputs['Emission Color'].default_value = (a[0], a[1], a[2], 1); bs.inputs['Emission Strength'].default_value = 6.0
        out[name] = mm
    return out

def to_objects(b, collection=None, tags=('main', 'detail'), name=None):
    """turn a Builder into Blender mesh objects (one per tag), material slots by name"""
    import bpy
    bm = blender_materials()
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
        for n in names: me.materials.append(bm[n])
        midx = {n: k for k, n in enumerate(names)}
        fm = np.array([midx[n] for n in M['MATN'][I[:, 0]]], np.int32)
        me.polygons.foreach_set('material_index', fm)
        me.polygons.foreach_set('use_smooth', np.ones(len(I), bool))
        me.normals_split_custom_set(M['N'][I.ravel()].tolist())
        uvl = me.uv_layers.new(name='uv'); uvl.data.foreach_set('uv', M['UV'][I.ravel()].ravel())
        ob = bpy.data.objects.new(me.name, me); col.objects.link(ob)
        ob['jk_tag'] = tag
        objs.append(ob)
    return objs

def export_npz(b, path, extra=None):
    """the viewer's format: P, N, UV, MAT (ids), C0, C1, I (+ TAGS: 0 main, 1 detail) and walk / block meshes, lamps, trees"""
    M = mats()
    out = {}
    D = b.merged(('main', 'detail'))
    if D is not None:
        out.update(P=D['P'], N=D['N'], UV=D['UV'], I=D['I'].astype(np.uint32), C0=D['C0'], C1=D['C1'],
                   MAT=np.array([M[n]['id'] for n in D['MATN']], np.uint8), DETAIL=(D['TAG'] == 'detail').astype(np.uint8))
    W = b.merged(('walk',))
    if W is not None: out.update(WP=W['P'], WI=W['I'].astype(np.uint32))
    K = b.merged(('block',))
    if K is not None: out.update(KP=K['P'], KI=K['I'].astype(np.uint32))
    if b.lamps: out['LAMPS'] = np.array([(*p, w, *c) for (p, w, c) in b.lamps], np.float32)
    if b.trees: out['TREES'] = np.array(b.trees, np.float32)
    if extra: out.update(extra)
    np.savez_compressed(path, **out)
    return out
