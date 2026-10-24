"""Mesh accumulator (geometry built in python lists, turned into a Blender mesh at the end)."""
import math
import numpy as np
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


WRAP = {'decal_moss': 'uv', 'concrete': 'uv', 'rubble': 'uv', 'metal': 'uv', 'bark': 'uv', 'facade_a': 'u', 'facade_b': 'u'}


class MB:
    """Faces with a material key, per-corner UV0 and per-corner colour."""

    def __init__(self):
        self.V = []
        self.F = []
        self.UV = []
        self.C = []
        self.M = []

    def face(self, pts, uvs, mat, col=(1, 1, 1, 1)):
        i0 = len(self.V)
        self.V.extend(tuple(p) for p in pts)
        self.F.append(list(range(i0, i0 + len(pts))))
        self.UV.append([tuple(u) for u in uvs])
        if not isinstance(col[0], (tuple, list)) and len(col) == 3:
            col = (*col, 1.0)
        if isinstance(col[0], (tuple, list)):
            self.C.append([tuple(c) if len(c) == 4 else (*c, 1.0) for c in col])
        else:
            self.C.append([tuple(col)] * len(pts))
        self.M.append(mat)

    def quad(self, a, b, c, d, uvs, mat, col=(1, 1, 1, 1)):
        self.face([a, b, c, d], uvs, mat, col)

    def poly_flat(self, ring2d, z, mat, uvfun, col=(1, 1, 1, 1), up=True, zfun=None):
        """triangulated (possibly concave) polygon at height z (or zfun(x,y))."""
        if len(ring2d) < 3:
            return
        pts = [Vector((p[0], p[1], 0)) for p in ring2d]
        try:
            tris = tessellate_polygon([pts])
        except Exception:
            return
        for t in tris:
            tri = [ring2d[i] for i in t]
            a = (tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[1][1] - tri[0][1]) * (tri[2][0] - tri[0][0])
            if abs(a) < 1e-6:
                continue
            if (a > 0) != up:
                tri = tri[::-1]
            P = [(p[0], p[1], zfun(p[0], p[1]) if zfun else z) for p in tri]
            self.face(P, [uvfun(p) for p in P], mat, col)

    def extend(self, other):
        for f, uv, c, m in zip(other.F, other.UV, other.C, other.M):
            self.face([other.V[i] for i in f], uv, m, c)

    def nfaces(self):
        return len(self.F)

    def ntris(self):
        return sum(len(f) - 2 for f in self.F)

    def to_objects(self, prefix, collection, mats, merge=True, uv1=None):
        """one object per material key -> {key: object}. uv1: {key: atlas size} -> planar lightmap UVs."""
        out = {}
        keys = sorted(set(self.M))
        for k in keys:
            idx = [i for i, m in enumerate(self.M) if m == k]
            V = []
            F = []
            UV = []
            C = []
            remap = {}
            for i in idx:
                f = self.F[i]
                nf = []
                for vi in f:
                    if vi not in remap:
                        remap[vi] = len(V)
                        V.append(self.V[vi])
                    nf.append(remap[vi])
                F.append(nf)
                uv = self.UV[i]
                wr = WRAP.get(k)
                if wr:
                    du = math.floor(min(t[0] for t in uv))
                    dv = math.floor(min(t[1] for t in uv)) if wr == 'uv' else 0
                    uv = [(t[0] - du, t[1] - dv) for t in uv]
                UV.extend(uv)
                C.extend(self.C[i])
            name = f'{prefix}_{k}'
            me = bpy.data.meshes.new(name)
            me.from_pydata(V, [], F)
            uvl = me.uv_layers.new(name='UVMap')
            uvl.data.foreach_set('uv', np.array(UV, dtype=np.float32).ravel())
            if uv1 and k in uv1:
                import sb_uv1
                lay, dens = sb_uv1.layout([[self.V[vi] for vi in self.F[i]] for i in idx], size=uv1[k])
                print(f'    uv1 {name}: {len(idx)} faces, {dens:.1f} px/m')
                l1 = me.uv_layers.new(name='UV1')
                l1.data.foreach_set('uv', np.array([t for f in lay for t in f], dtype=np.float32).ravel())
                me.uv_layers.active = me.uv_layers['UVMap']
                me.uv_layers['UVMap'].active_render = True
            ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
            ca.data.foreach_set('color', np.array(C, dtype=np.float32).ravel())
            if merge:
                import bmesh
                bm = bmesh.new()
                bm.from_mesh(me)
                bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
                bm.to_mesh(me)
                bm.free()
            me.validate(clean_customdata=False)
            if mats and k in mats:
                me.materials.append(mats[k])
            ob = bpy.data.objects.new(name, me)
            collection.objects.link(ob)
            out[k] = ob
        return out


# --------------------------------------------------------------- noise
def _hash(ix, iy, seed):
    h = (np.asarray(ix, dtype=np.int64) * 374761393 + np.asarray(iy, dtype=np.int64) * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0


def vnoise(x, y, scale=1.0, seed=0):
    """smooth value noise in [0,1]; vectorised."""
    x = np.asarray(x, dtype=float) / scale
    y = np.asarray(y, dtype=float) / scale
    ix = np.floor(x); iy = np.floor(y)
    fx = x - ix; fy = y - iy
    sx = fx * fx * (3 - 2 * fx); sy = fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed); b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed); d = _hash(ix + 1, iy + 1, seed)
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy


def fbm(x, y, scale=1.0, seed=0, octaves=3):
    s = 0.0; amp = 0.5; tot = 0.0
    for o in range(octaves):
        s = s + amp * vnoise(x, y, scale / (2 ** o), seed + o * 17)
        tot += amp; amp *= 0.5
    return s / tot
