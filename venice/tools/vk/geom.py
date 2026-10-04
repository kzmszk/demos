"""Procedural mesh building blocks (run inside Blender's python: needs numpy + mathutils).

Coordinates: metres, x east, y north, z up (Blender).  A Mesh is a soup of
polygons with a material name per face, an optional explicit UV per corner,
and a smooth flag per face.  Everything else (normals, box UVs, bake density)
is decided later in the Blender stage."""
import math
import numpy as np

TAU = math.tau


class Mesh:
    __slots__ = ('V', 'F', 'M', 'S', 'UV')

    def __init__(self):
        self.V = []      # [x,y,z]
        self.F = []      # [i0,i1,...]
        self.M = []      # material name per face
        self.S = []      # smooth flag per face
        self.UV = []     # None or [(u,v)...] per face (explicit uv)

    # ---------------------------------------------------------------- basics
    def add_v(self, pts):
        o = len(self.V)
        self.V.extend([float(p[0]), float(p[1]), float(p[2])] for p in pts)
        return o

    def face(self, idx, mat, smooth=False, uv=None):
        self.F.append(list(idx)); self.M.append(mat); self.S.append(smooth); self.UV.append(uv)

    def poly(self, pts, mat, smooth=False, uv=None):
        o = self.add_v(pts)
        self.face(range(o, o + len(pts)), mat, smooth, uv)

    def merge(self, other, xf=None):
        o = len(self.V)
        if xf is None:
            self.V.extend(other.V)
        else:
            self.V.extend(apply(xf, np.array(other.V)).tolist() if other.V else [])
        self.F.extend([[i + o for i in f] for f in other.F])
        self.M.extend(other.M); self.S.extend(other.S); self.UV.extend(other.UV)
        return self

    def transformed(self, xf):
        m = Mesh(); m.merge(self, xf); return m

    def recolor(self, mat_from, mat_to):
        self.M = [mat_to if m == mat_from else m for m in self.M]
        return self

    def setmat(self, mat):
        self.M = [mat] * len(self.F); return self

    def count(self):
        return len(self.V), len(self.F)

    def bbox(self):
        a = np.array(self.V); return a.min(0), a.max(0)


# -------------------------------------------------------------------- transforms
def mat4(t=(0, 0, 0), rz=0.0, s=1.0, rx=0.0, ry=0.0):
    """translate * rotZ * rotY * rotX * scale (s scalar or 3-vector)."""
    s = np.array(s, float) * np.ones(3)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    M = np.eye(4); M[:3, :3] = Rz @ Ry @ Rx @ np.diag(s); M[:3, 3] = t
    return M


def frame(origin, u, v, w=None):
    """matrix mapping local (x,y,z) -> origin + x*u + y*v + z*w."""
    u = np.array(u, float); v = np.array(v, float)
    w = np.cross(u, v) if w is None else np.array(w, float)
    M = np.eye(4); M[:3, 0] = u; M[:3, 1] = v; M[:3, 2] = w; M[:3, 3] = origin
    return M


def apply(M, P):
    P = np.asarray(P, float)
    if P.size == 0: return P
    return P @ M[:3, :3].T + M[:3, 3]


# -------------------------------------------------------------------- primitives
def box(x0, y0, z0, x1, y1, z1, mat, faces='all'):
    m = Mesh()
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    o = m.add_v(P)
    quads = {'-z': (0, 3, 2, 1), '+z': (4, 5, 6, 7), '-y': (0, 1, 5, 4),
             '+x': (1, 2, 6, 5), '+y': (2, 3, 7, 6), '-x': (3, 0, 4, 7)}
    for k, q in quads.items():
        if faces == 'all' or k in faces:
            m.face([o + i for i in q], mat)
    return m


def tess(loops):
    """triangulate a planar polygon with holes. loops: [outer, hole1, ...] of 2D pts.
    returns triangles as index triples into the concatenated loops (earcut; venv port of the Blender version)."""
    import mapbox_earcut as earcut
    flat = []; rings = []
    for L in loops:
        flat.extend([(float(p[0]), float(p[1])) for p in L]); rings.append(len(flat))
    if len(flat) < 3: return []
    tri = earcut.triangulate_float64(np.array(flat, np.float64).reshape(-1, 2), np.array(rings, np.uint32))
    return [tuple(int(v) for v in tri[i:i + 3]) for i in range(0, len(tri), 3)]


def signed_area(P):
    a = 0.0
    for i in range(len(P)):
        x0, y0 = P[i][:2]; x1, y1 = P[(i + 1) % len(P)][:2]
        a += x0 * y1 - x1 * y0
    return a / 2


def ccw(P):
    P = [tuple(p[:2]) for p in P]
    if len(P) > 1 and P[0] == P[-1]: P = P[:-1]
    return P if signed_area(P) > 0 else P[::-1]


def cap(loops, z, mat, up=True, M=None):
    """flat cap (with holes) at height z. loops[0] outer (any winding)."""
    m = Mesh()
    L = [ccw(loops[0])] + [ccw(h)[::-1] for h in loops[1:]]
    flat = [p for l in L for p in l]
    o = m.add_v([(p[0], p[1], z) for p in flat])
    for t in tess(L):
        a, b, c = t
        # tessellate_polygon returns triangles in some winding: fix by signed area
        pa, pb, pc = flat[a], flat[b], flat[c]
        cr = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        tri = (a, b, c) if (cr > 0) == up else (a, c, b)
        m.face([o + i for i in tri], mat)
    return m if M is None else m.transformed(M)


def prism(loops, z0, z1, mat, mat_top=None, mat_bot=None, top=True, bottom=False, smooth=False):
    """extrude polygon (with holes) from z0 to z1."""
    m = Mesh()
    for k, L in enumerate(loops):
        L = ccw(L) if k == 0 else ccw(L)[::-1]
        n = len(L)
        o = m.add_v([(p[0], p[1], z0) for p in L] + [(p[0], p[1], z1) for p in L])
        for i in range(n):
            j = (i + 1) % n
            m.face([o + i, o + j, o + n + j, o + n + i], mat, smooth)
    if top: m.merge(cap(loops, z1, mat_top or mat, True))
    if bottom: m.merge(cap(loops, z0, mat_bot or mat, False))
    return m


def lathe(profile, seg=32, a0=0.0, a1=TAU, mat='stone', smooth=True, center=(0, 0, 0), caps=False):
    """revolve [(r,z),...] around z. profile ordered bottom->top gives outward faces."""
    m = Mesh()
    full = abs(a1 - a0 - TAU) < 1e-9
    na = seg if full else seg + 1
    cx, cy, cz = center
    rows = []
    for (r, z) in profile:
        row = []
        for k in range(na):
            a = a0 + (a1 - a0) * k / seg
            row.append((cx + r * math.cos(a), cy + r * math.sin(a), cz + z))
        rows.append(m.add_v(row))
    for i in range(len(profile) - 1):
        for k in range(seg):
            k1 = (k + 1) % na if full else k + 1
            a, b = rows[i] + k, rows[i] + k1
            c, d = rows[i + 1] + k1, rows[i + 1] + k
            if profile[i][0] < 1e-9 and profile[i + 1][0] < 1e-9: continue
            if profile[i][0] < 1e-9: m.face([a, c, d], mat, smooth)
            elif profile[i + 1][0] < 1e-9: m.face([a, b, c], mat, smooth)
            else: m.face([a, b, c, d], mat, smooth)
    return m


def sweep(profile, path, mat, closed=False, smooth=False, up=(0, 0, 1), caps=True, cap_mat=None):
    """sweep a 2D profile [(s,t)] along a 3D polyline.  s = outward (to the right of the
    direction of travel, i.e. path CCW seen from above -> s points outward), t = up.
    Corners are mitred.  Profile order: from bottom/inside to top so faces point out."""
    m = Mesh()
    P = [np.array(p, float) for p in path]
    n = len(P)
    upv = np.array(up, float)
    rings = []
    for i in range(n):
        if closed:
            d0 = P[i] - P[i - 1]; d1 = P[(i + 1) % n] - P[i]
        else:
            d0 = P[i] - P[i - 1] if i > 0 else P[1] - P[0]
            d1 = P[i + 1] - P[i] if i < n - 1 else P[i] - P[i - 1]
        d0 = d0 / np.linalg.norm(d0); d1 = d1 / np.linalg.norm(d1)
        r0 = np.cross(d0, upv); r0 /= np.linalg.norm(r0)
        r1 = np.cross(d1, upv); r1 /= np.linalg.norm(r1)
        rm = r0 + r1; rm /= np.linalg.norm(rm)
        k = 1.0 / max(0.2, float(np.dot(rm, r0)))  # mitre stretch
        rings.append(m.add_v([P[i] + rm * (s * k) + upv * t for (s, t) in profile]))
    np_ = len(profile)
    segs = n if closed else n - 1
    for i in range(segs):
        A = rings[i]; B = rings[(i + 1) % n]
        for j in range(np_ - 1):
            m.face([A + j, B + j, B + j + 1, A + j + 1], mat, smooth)
    if caps and not closed:
        cm = cap_mat or mat
        m.face([rings[0] + j for j in range(np_)][::-1], cm)
        m.face([rings[-1] + j for j in range(np_)], cm)
    return m


def extrude_xsection(pts2d, length, mat, M=None, caps=True, smooth=False):
    """extrude a closed 2D section (in local x,z plane) along +y by length."""
    m = Mesh()
    n = len(pts2d)
    o = m.add_v([(p[0], 0, p[1]) for p in pts2d] + [(p[0], length, p[1]) for p in pts2d])
    for i in range(n):
        j = (i + 1) % n
        m.face([o + i, o + j, o + n + j, o + n + i], mat, smooth)
    if caps:
        L = [(p[0], p[1]) for p in pts2d]
        cpos = cap([L], 0, mat, True)
        # cap in x-z plane: rotate (x,y,0)->(x,0,y)
        R = frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
        m.merge(cpos.transformed(R))
        m.merge(cap([L], 0, mat, False).transformed(frame((0, length, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))))
    return m if M is None else m.transformed(M)


def cylinder(r, z0, z1, seg=24, mat='stone', top=True, bottom=False, center=(0, 0)):
    prof = [(0, z0)] if bottom else []
    prof += [(r, z0), (r, z1)]
    if top: prof += [(0, z1)]
    m = lathe(prof, seg, mat=mat, center=(center[0], center[1], 0))
    return m


def arc_pts(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def opening_shape(w, h, kind='rect', n=12, x=0.0, y=0.0):
    """2D outline (ccw) of an opening with bottom-left at (x,y): rect | arch (semicircular top) | seg (segmental)."""
    if kind == 'rect':
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if kind == 'arch':
        r = w / 2; spring = h - r
        pts = [(x, y), (x + w, y)]
        pts += [(x + r + r * math.cos(a), y + spring + r * math.sin(a)) for a in np.linspace(0, math.pi, n + 1)]
        return pts
    if kind == 'oval':
        return [(x + w / 2 + w / 2 * math.cos(a), y + h / 2 + h / 2 * math.sin(a)) for a in np.linspace(0, TAU, n * 2, endpoint=False)]
    if kind == 'circle':
        return [(x + w / 2 + w / 2 * math.cos(a), y + w / 2 + w / 2 * math.sin(a)) for a in np.linspace(0, TAU, n * 2, endpoint=False)]
    raise ValueError(kind)


def wall(width, height, thick, mat, openings=(), M=None, reveal_mat=None, back=True, sides=True, top=False, bottom=False):
    """a straight wall in local coords: x along [0,width], z up [0,height], y = thickness
    from 0 (front face, facing -y) to thick (back). openings: list of 2D outlines in (x,z)."""
    m = Mesh()
    rm = reveal_mat or mat
    outer = [(0, 0), (width, 0), (width, height), (0, height)]
    holes = [list(o) for o in openings]
    # front (normal -y): map (x,z) -> (x, 0, z)
    Ffront = frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    m.merge(cap([outer] + holes, 0, mat, True, Ffront))
    if back:
        Fback = frame((0, thick, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))
        m.merge(cap([outer] + holes, 0, mat, False, Fback))
    for h in holes:  # reveals, facing into the opening
        L = ccw(h)
        n = len(L)
        o = m.add_v([(p[0], 0, p[1]) for p in L] + [(p[0], thick, p[1]) for p in L])
        for i in range(n):
            j = (i + 1) % n
            m.face([o + i, o + n + i, o + n + j, o + j], rm)
    if sides:
        m.merge(box(0, 0, 0, width, thick, height, mat, faces=('-x', '+x') + (('+z',) if top else ()) + (('-z',) if bottom else ())))
    return m if M is None else m.transformed(M)


def grid_quad(p0, pu, pv, nu, nv, mat, uvfn=None, smooth=False):
    """subdivided quad p0 + s*pu + t*pv; optional uv function (s,t)->(u,v)."""
    m = Mesh()
    p0 = np.array(p0, float); pu = np.array(pu, float); pv = np.array(pv, float)
    o = m.add_v([p0 + pu * (i / nu) + pv * (j / nv) for j in range(nv + 1) for i in range(nu + 1)])
    for j in range(nv):
        for i in range(nu):
            a = o + j * (nu + 1) + i
            idx = [a, a + 1, a + nu + 2, a + nu + 1]
            uv = None
            if uvfn:
                uv = [uvfn(i / nu, j / nv), uvfn((i + 1) / nu, j / nv), uvfn((i + 1) / nu, (j + 1) / nv), uvfn(i / nu, (j + 1) / nv)]
            m.face(idx, mat, smooth, uv)
    return m


def polyline_len(P):
    return sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1))


def resample(P, step):
    """resample a 2D/3D polyline at roughly equal spacing (keeps ends)."""
    out = [tuple(P[0])]
    for i in range(len(P) - 1):
        a = np.array(P[i], float); b = np.array(P[i + 1], float)
        L = np.linalg.norm(b - a); n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            out.append(tuple(a + (b - a) * k / n))
    return out


def simplify_ring(P, eps):
    """Douglas-Peucker for a closed ring (no repeated end point)."""
    def dp(pts):
        if len(pts) < 3: return list(pts)
        a, b = pts[0], pts[-1]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        def d(p): return abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / L
        i = max(range(1, len(pts) - 1), key=lambda k: d(pts[k]))
        if d(pts[i]) > eps: return dp(pts[:i + 1])[:-1] + dp(pts[i:])
        return [a, b]
    P = list(P)
    far = max(range(len(P)), key=lambda k: math.dist(P[k], P[0]))
    A = dp(P[:far + 1]); B = dp(P[far:] + [P[0]])
    return A[:-1] + B[:-1]
