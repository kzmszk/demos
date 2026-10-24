"""Atlas UV mapping: every face is cut along its own tiling grid and mapped into one atlas cell.

Two atlases (2048 px):
  FACADE: 2x2 cells of 1024 px, each a 12.8 m x 16 m (4 floors) tile of the Tange granite grid
  MAT:    4x4 cells of 512 px, materials of different physical tile sizes (see MAT_CELLS)
Cells are seamless tiles inset by a wrap-padded gutter, so a face that lies inside one tile repetition can be mapped
with plain (non-repeating) UVs. Big flat walls are cheap to cut (a 240 m facade becomes ~15 x 20 quads).
"""
import bmesh, math
from mathutils import Vector

ATLAS = 2048
G = 8          # gutter px

FACADE_CELLS = {   # id: (col, row, size_px, Su, Sv)    rows counted from the image bottom (Blender convention)
    0: (0, 1, 1024, 12.8, 16.0),   # A pier zone (paired narrow windows, dark granite blocks)
    1: (1, 1, 1024, 12.8, 16.0),   # B window-band zone (wide windows, dark spandrels)
    2: (0, 0, 1024, 12.8, 16.0),   # A, sixty years on: glass gone, panels missing, streaks, moss
    3: (1, 0, 1024, 12.8, 16.0),   # B, ruined
}
MAT_NAMES = ['granite', 'granite_dark', 'assembly', 'concrete', 'broken', 'interior', 'rust', 'moss',
             'roof', 'paving', 'bark', 'asphalt', 'soil', 'grid', 'panel', 'glazing']
_ms = {'granite': (4, 4), 'granite_dark': (4, 4), 'assembly': (6.4, 8), 'concrete': (4, 4), 'broken': (3, 3),
       'interior': (4, 4), 'rust': (2, 2), 'moss': (3, 3), 'roof': (8, 8), 'paving': (4, 4), 'bark': (2, 4),
       'asphalt': (8, 8), 'soil': (4, 4), 'grid': (3.2, 4), 'panel': (3.2, 4), 'glazing': (4, 4)}
MAT_CELLS = {i: (i % 4, 3 - i // 4, 512) + _ms[n] for i, n in enumerate(MAT_NAMES)}
MC = {n: i for i, n in enumerate(MAT_NAMES)}


def frame(n):
    n = Vector(n)
    if n.length < 1e-9: return Vector((1, 0, 0)), Vector((0, 1, 0))
    n.normalize()
    if abs(n.z) > 0.95:
        return Vector((1, 0, 0)), Vector((0, 1 if n.z > 0 else -1, 0))
    t = Vector((0, 0, 1)).cross(n).normalized()
    return t, n.cross(t).normalized()


def _key(t, b):
    return (round(t.x, 3), round(t.y, 3), round(t.z, 3), round(b.x, 3), round(b.y, 3), round(b.z, 3))


def cut_and_map(ob, cells, variant=None, cut=True, uv_name='UVMap', offset=None):
    """ob: mesh with an int face attribute 'cell'. cells: FACADE_CELLS or MAT_CELLS.
    variant(face_centre, cell, ku, kv, t) -> cell (optional, e.g. to swap in damaged facade tiles).
    offset(cell) -> (du, dv) metres added before tiling (optional)"""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    lay = bm.faces.layers.int.get('cell')
    if lay is None: lay = bm.faces.layers.int.new('cell')
    if cut:
        gl = bm.faces.layers.int.get('grp') or bm.faces.layers.int.new('grp')
        groups = {}
        for f in bm.faces:
            t, b = frame(f.normal)
            c = f[lay]; su, sv = cells[c][3], cells[c][4]
            k = _key(t, b) + (su, sv)
            if k not in groups: groups[k] = (len(groups), t, b, su, sv)
            f[gl] = groups[k][0]
        for key, (gi, t, b, su, sv) in groups.items():
            for axis, s in ((t, su), (b, sv)):
                fs = [f for f in bm.faces if f[gl] == gi]
                if not fs: continue
                vals = [v.co.dot(axis) for f in fs for v in f.verts]
                k0, k1 = math.floor(min(vals) / s) + 1, math.ceil(max(vals) / s) - 1
                for k in range(k0, k1 + 1):
                    fs = [f for f in bm.faces if f[gl] == gi]
                    geom = list(set([e for f in fs for e in f.edges])) + fs + list(set([v for f in fs for v in f.verts]))
                    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * (k * s), plane_no=axis, dist=1e-4)
    uvl = bm.loops.layers.uv.get(uv_name) or bm.loops.layers.uv.new(uv_name)
    for f in bm.faces:
        t, b = frame(f.normal)
        c = f[lay]
        su, sv = cells[c][3], cells[c][4]
        cen = f.calc_center_median()
        du, dv = offset(c) if offset else (0.0, 0.0)
        uc, vc = cen.dot(t) + du, cen.dot(b) + dv
        ku, kv = math.floor(uc / su), math.floor(vc / sv)
        if variant:
            c2 = variant(cen, c, ku, kv, t)
            if c2 != c: f[lay] = c = c2
        col, row, px = cells[c][0], cells[c][1], cells[c][2]
        su, sv = cells[c][3], cells[c][4]
        x0 = col * px + G; y0 = row * px + G; w = px - 2 * G
        for l in f.loops:
            p = l.vert.co
            lu = (p.dot(t) + du - ku * su) / su; lv = (p.dot(b) + dv - kv * sv) / sv
            lu = min(max(lu, 0.0), 1.0); lv = min(max(lv, 0.0), 1.0)
            l[uvl].uv = ((x0 + lu * w) / ATLAS, (y0 + lv * w) / ATLAS)
    bm.to_mesh(me); bm.free()
    me.update()


DECAL_NAMES = ['paving', 'band', 'grass', 'litter', 'wet', 'cracks', 'zebra', 'rubble', 'mud', 'line', 'moss', 'leaves',
               'gravel', 'roots', 'stain', 'tile']
_ds = {'paving': (4, 4), 'band': (2, 2), 'grass': (6, 6), 'litter': (4, 4), 'wet': (6, 6), 'cracks': (5, 5), 'zebra': (3.6, 3.6),
       'rubble': (5, 5), 'mud': (5, 5), 'line': (4, 4), 'moss': (5, 5), 'leaves': (4, 4), 'gravel': (4, 4), 'roots': (6, 6),
       'stain': (6, 6), 'tile': (3, 3)}
DECAL_CELLS = {i: (i % 4, 3 - i // 4, 512) + _ds[n] for i, n in enumerate(DECAL_NAMES)}
DC = {n: i for i, n in enumerate(DECAL_NAMES)}
