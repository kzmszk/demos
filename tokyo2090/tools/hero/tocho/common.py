"""Shared helpers for the tocho hero build (runs inside Blender 5.2).

Frame: x east, y north, z up = absolute height (T.P. m), local to the district origin (-760, 3270).
"""
import bpy, bmesh, math, os, json, random
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = '/home/kazu/work/tokyo2090-assets/hero/tocho/'
WORK = SRC + 'work/'
TEX = WORK + 'tex/'
PUB = os.path.abspath(os.path.join(HERE, '../../../public/hero/tocho')) + '/'
for d in (WORK, TEX, PUB, PUB + 'previews/'):
    os.makedirs(d, exist_ok=True)

ORIGIN = (-760, 3270)
BOX = (-120, -170, 115, 170)       # local x0 y0 x1 y1

# --------------------------------------------------------------------------------------------- ground
_g = np.load(SRC + 'ground.npz')
GH, GX0, GY0, GS = _g['h'].astype(np.float64), float(_g['x0']), float(_g['y0']), float(_g['s'])


def ground(x, y):
    """the game's terrain surface: 10 m cells split along the (x+10,y)-(x,y+10) diagonal"""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    fx = (x - GX0) / GS; fy = (y - GY0) / GS
    c = np.clip(np.floor(fx).astype(int), 0, GH.shape[1] - 2); w = np.clip(np.floor(fy).astype(int), 0, GH.shape[0] - 2)
    u = fx - c; v = fy - w
    h00 = GH[w, c]; h10 = GH[w, c + 1]; h01 = GH[w + 1, c]; h11 = GH[w + 1, c + 1]
    lo = h00 + u * (h10 - h00) + v * (h01 - h00)
    hi = h11 + (1 - u) * (h01 - h11) + (1 - v) * (h10 - h11)
    r = np.where(u + v <= 1, lo, hi)
    return float(r) if r.ndim == 0 else r


def ground_min(x, y, r):
    """lowest ground under a disc (so props never float)"""
    a = np.linspace(0, 2 * math.pi, 9)[:-1]
    return min(ground(x, y), float(np.min(ground(x + r * np.cos(a), y + r * np.sin(a)))))


# --------------------------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(ob, c):
    for u in list(ob.users_collection): u.objects.unlink(ob)
    c.objects.link(ob)
    return ob


def import_obj(path, name=None):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    return new


def rng(seed):
    return random.Random(seed)


# --------------------------------------------------------------------------------------------- mesh builder
class MB:
    """accumulates geometry for one object: faces with a material slot and per-face 'cell' tags.
    UVs are written later by atlas mapping (see uvmap.py), from the per-face cell attribute."""

    def __init__(self):
        self.V = []; self.F = []; self.cell = []; self.mat = []; self.uv = []   # uv: per-face list or None

    def v(self, p):
        self.V.append(tuple(p)); return len(self.V) - 1

    def face(self, idx, mat=0, cell=0, uv=None):
        self.F.append(list(idx)); self.mat.append(mat); self.cell.append(cell); self.uv.append(uv)

    def poly(self, pts, mat=0, cell=0, uv=None):
        i = [self.v(p) for p in pts]; self.face(i, mat, cell, uv); return i

    def quad(self, a, b, c, d, mat=0, cell=0, uv=None):
        return self.poly([a, b, c, d], mat, cell, uv)

    def box(self, c, size, rot=0.0, mat=0, cell=0, bottom=True):
        """axis box centred at c (x,y,z-centre), size (sx,sy,sz), rotated about z by rot"""
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
        R = Matrix.Rotation(rot, 3, 'Z')
        P = [Vector(c) + R @ Vector((x, y, z)) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
        i = [self.v(p) for p in P]
        fs = [(0, 1, 3, 2)[::-1], (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]
        if not bottom: fs = fs[1:]
        for f in fs: self.face([i[k] for k in f], mat, cell)

    def prism(self, ring, z0, z1, mat=0, cell=0, top=True, bottom=False, cell_top=None):
        """vertical prism over a ccw ring of (x,y)"""
        n = len(ring)
        lo = [self.v((x, y, z0)) for x, y in ring]; hi = [self.v((x, y, z1)) for x, y in ring]
        for k in range(n):
            a, b = k, (k + 1) % n
            self.face([lo[a], lo[b], hi[b], hi[a]], mat, cell)
        if top: self.face(hi, mat, cell if cell_top is None else cell_top)
        if bottom: self.face(lo[::-1], mat, cell)

    def extend(self, o, off=(0, 0, 0)):
        base = len(self.V)
        self.V += [(p[0] + off[0], p[1] + off[1], p[2] + off[2]) for p in o.V]
        self.F += [[i + base for i in f] for f in o.F]
        self.mat += o.mat; self.cell += o.cell; self.uv += o.uv

    def build(self, name, mats, col=None, smooth=False):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.V, [], self.F)
        me.validate(clean_customdata=False)
        for m in mats: me.materials.append(m)
        if len(me.polygons) == len(self.F):
            me.polygons.foreach_set('material_index', self.mat)
            a = me.attributes.new('cell', 'INT', 'FACE'); a.data.foreach_set('value', self.cell)
            if any(u is not None for u in self.uv):
                uvl = me.uv_layers.new(name='UVMap')
                k = 0
                for fi, p in enumerate(me.polygons):
                    u = self.uv[fi]
                    for j, li in enumerate(p.loop_indices):
                        uvl.data[li].uv = u[j] if u is not None else (0, 0)
        else:
            print('WARN mesh', name, 'validate changed face count', len(me.polygons), len(self.F))
        for p in me.polygons: p.use_smooth = smooth
        ob = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(ob)
        return ob


def obj_tris(ob):
    me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh() if ob.type == 'MESH' else None
    if me is None: return 0
    me.calc_loop_triangles(); n = len(me.loop_triangles)
    ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return n


def massing():
    return json.load(open(WORK + 'massing.json'))


def save(path=WORK + 'tocho.blend'):
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
