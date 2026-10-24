"""Saki — rigged, textured, animated character for TOKYO 2090.

    blender -b --python tools/blender/saki.py                 # build, export, render the 3 previews (~80 s)
    blender -b --python tools/blender/saki.py -- --verify     # re-import the glb and print bones/actions/tris
    options after --: --no-previews, --extra (more preview angles), --keep-blend (save previews/saki.blend),
                      --fast (coarser voxels, for quick iteration)

Builds everything procedurally (no external assets):
  * body / head / hair / clothes as signed-distance fields (smooth unions of round
    cones and ellipsoids), meshed with surface nets, decimated;
  * harness, belt, sandal straps, wrist cuffs as ribbons projected on the body;
  * the cape as a quad grid between the arms and the ankle loops;
  * one 1024² colour atlas painted per texel from 3D position (PNG, embedded);
  * armature (names fixed by the game), automatic weights for the body, transferred /
    procedural weights for the rest, five looping actions: fly (2 s), sit (3 s), stand (3 s), walk (1.07 s), run (0.67 s).

Two helper bones beyond the game's list: cape.L / cape.R, children of shin.L / shin.R at the ankle
loops. The cape's hem is bound to them, so by default it follows the ankles (fly, stand); the sit
action moves them behind her onto the roof so the cape does not pass through the seat. The cape is two
halves (one per side) meeting down the back: with the legs apart in flight the back and legs show
between the wings; standing they hang together like a coat.

Output: public/models/saki.glb, previews in tools/blender/previews/.
Modelling frame: Blender Z up, character faces +Y (glTF -Z after export), left = -X,
feet on z=0; everything is shifted so the hips sit at the origin before export.
"""
import bpy, bmesh, sys, os, math, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion, Euler

sys.path.append('/home/kazu/work/kyoto-assets/blender_py')  # scipy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT_GLB = os.path.join(ROOT, 'public', 'models', 'saki.glb')
PREV_DIR = os.path.join(HERE, 'previews')
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FAST = '--fast' in ARGS
T0 = time.time()


def log(*a):
    print('[saki %6.1fs]' % (time.time() - T0), *a, flush=True)


# ----------------------------------------------------------------------------
# SDF primitives (numpy, broadcasting over X, Y, Z arrays)
# ----------------------------------------------------------------------------
def V(*a):
    return np.array(a, dtype=np.float64)


def nrm(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def frame_from(fwd, up_hint):
    """Rows: local x, y, z axes. local z = fwd."""
    z = nrm(fwd)
    x = np.cross(up_hint, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(V(1, 0, 0), z)
    x = nrm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z])


class P3:
    """Points as broadcastable arrays."""
    def __init__(self, X, Y, Z):
        self.X, self.Y, self.Z = X, Y, Z

    def sub(self, c):
        return self.X - c[0], self.Y - c[1], self.Z - c[2]

    def local(self, c, R):
        x, y, z = self.sub(c)
        return (R[0, 0] * x + R[0, 1] * y + R[0, 2] * z,
                R[1, 0] * x + R[1, 1] * y + R[1, 2] * z,
                R[2, 0] * x + R[2, 1] * y + R[2, 2] * z)


def sd_sphere(p, c, r):
    x, y, z = p.sub(c)
    return np.sqrt(x * x + y * y + z * z) - r


def _ellip(x, y, z, r):
    a, b, c = r
    k0 = np.sqrt((x / a) ** 2 + (y / b) ** 2 + (z / c) ** 2)
    k1 = np.sqrt((x / a / a) ** 2 + (y / b / b) ** 2 + (z / c / c) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_ellipsoid(p, c, r, R=None):
    if R is None:
        x, y, z = p.sub(c)
    else:
        x, y, z = p.local(c, R)
    return _ellip(x, y, z, r)


def sd_roundcone(p, a, b, r1, r2):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    px, py, pz = p.sub(a)
    y = px * ba[0] + py * ba[1] + pz * ba[2]
    z = y - l2
    qx = px * l2 - ba[0] * y
    qy = py * l2 - ba[1] * y
    qz = pz * l2 - ba[2] * y
    x2 = qx * qx + qy * qy + qz * qz
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d1 = np.sqrt(x2 + z2) * il2 - r2
    d2 = np.sqrt(x2 + y2) * il2 - r1
    d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
    return np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))


def sd_capsule(p, a, b, r):
    return sd_roundcone(p, a, b, r, r)


def sd_box(p, c, half, R=None, rnd=0.0):
    if R is None:
        x, y, z = p.sub(c)
    else:
        x, y, z = p.local(c, R)
    qx = np.abs(x) - half[0] + rnd
    qy = np.abs(y) - half[1] + rnd
    qz = np.abs(z) - half[2] + rnd
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - rnd


def sd_loft(p, sec, expo=2.0):
    """Vertical loft of (super)ellipse sections: sec = [(z, half_w, half_d, cy), ...]."""
    s = np.array(sec, float)
    Z = p.Z
    zs = s[:, 0]
    # Catmull-Rom-ish smooth interpolation via dense linear table
    zz = np.linspace(zs[0], zs[-1], 200)
    tab = []
    for col in (1, 2, 3):
        f = np.interp(zz, zs, s[:, col])
        f = np.convolve(np.pad(f, 6, mode='edge'), np.ones(13) / 13, mode='valid')
        tab.append(f)
    zc = np.clip(Z, zs[0], zs[-1])
    a = np.interp(zc, zz, tab[0]); b = np.interp(zc, zz, tab[1]); cy = np.interp(zc, zz, tab[2])
    x = p.X; y = p.Y - cy
    if expo == 2.0:
        k0 = np.sqrt((x / a) ** 2 + (y / b) ** 2)
        k1 = np.sqrt((x / a / a) ** 2 + (y / b / b) ** 2)
        d = k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    else:
        k0 = (np.abs(x / a) ** expo + np.abs(y / b) ** expo) ** (1.0 / expo)
        d = (k0 - 1.0) * np.minimum(a, b)
    dz = np.maximum(zs[0] - Z, Z - zs[-1])
    return np.maximum(d, dz)


def sd_egg_loft(p, sec, efront=2.4, eback=2.0):
    """Vertical loft of egg sections: sec = [(z, half_w, y0, front, back), ...]."""
    s = np.array(sorted(sec), float)
    if s.shape[1] == 5:
        s = np.hstack([s, np.full((len(s), 1), efront)])
    Z = p.Z
    zs = s[:, 0]
    zz = np.linspace(zs[0], zs[-1], 240)
    tab = []
    for col in (1, 2, 3, 4, 5):
        f = np.interp(zz, zs, s[:, col])
        f = np.convolve(np.pad(f, 7, mode='edge'), np.ones(15) / 15, mode='valid')
        tab.append(f)
    zc = np.clip(Z, zs[0], zs[-1])
    w = np.interp(zc, zz, tab[0]); y0 = np.interp(zc, zz, tab[1])
    yf = np.interp(zc, zz, tab[2]); yb = np.interp(zc, zz, tab[3]); ef = np.interp(zc, zz, tab[4])
    x = np.abs(p.X); y = p.Y - y0
    front = y > 0
    b = np.where(front, yf, yb)
    e = np.where(front, ef, eback)
    k0 = ((x / w) ** e + (np.abs(y) / b) ** e) ** (1.0 / e)
    d = (k0 - 1.0) * np.minimum(w, np.minimum(yf, yb)) * 0.9
    dz = np.maximum(zs[0] - Z, Z - zs[-1])
    return np.maximum(d, dz)


# ----------------------------------------------------------------------------
# SDF scene: an ordered list of ops, each limited to a bounding box
# ----------------------------------------------------------------------------
class SDF:
    def __init__(self):
        self.ops = []   # (mode, k, fn, lo, hi)

    def add(self, fn, lo, hi, k=0.0, mode='u'):
        lo = np.asarray(lo, float) - 1.5 * k - 0.006
        hi = np.asarray(hi, float) + 1.5 * k + 0.006
        self.ops.append((mode, k, fn, lo, hi))

    # convenience
    def sphere(self, c, r, k=0.0, mode='u'):
        c = np.asarray(c, float)
        self.add(lambda p: sd_sphere(p, c, r), c - r, c + r, k, mode)

    def ellipsoid(self, c, r, k=0.0, mode='u', R=None):
        c = np.asarray(c, float); m = max(r)
        self.add(lambda p: sd_ellipsoid(p, c, r, R), c - m, c + m, k, mode)

    def cone(self, a, b, r1, r2, k=0.0, mode='u'):
        a = np.asarray(a, float); b = np.asarray(b, float); m = max(r1, r2)
        self.add(lambda p: sd_roundcone(p, a, b, r1, r2),
                 np.minimum(a, b) - m, np.maximum(a, b) + m, k, mode)

    def chain(self, pts, rads, k=0.0, mode='u', kin=None):
        """Poly round-cone; joints of the chain blended with kin."""
        pts = [np.asarray(q, float) for q in pts]
        lo = np.min(pts, 0) - max(rads); hi = np.max(pts, 0) + max(rads)
        segs = list(zip(pts[:-1], pts[1:], rads[:-1], rads[1:]))
        kk = kin if kin is not None else 0.0

        def fn(p):
            d = None
            for a, b, r1, r2 in segs:
                e = sd_roundcone(p, a, b, r1, r2)
                d = e if d is None else smin(d, e, kk)
            return d
        self.add(fn, lo, hi, k, mode)

    def grid_eval(self, lo, hi, h, F=None):
        lo = np.asarray(lo, float); hi = np.asarray(hi, float)
        n = np.ceil((hi - lo) / h).astype(int) + 1
        if F is None:
            F = np.full(tuple(n), 0.5, dtype=np.float32)
        for mode, k, fn, olo, ohi in self.ops:
            if mode == 'shift':
                F -= np.float32(k)
                continue
            i0 = np.clip(np.floor((olo - lo) / h).astype(int), 0, n)
            i1 = np.clip(np.ceil((ohi - lo) / h).astype(int) + 1, 0, n)
            if np.any(i1 <= i0):
                continue
            xs = lo[0] + h * np.arange(i0[0], i1[0])
            ys = lo[1] + h * np.arange(i0[1], i1[1])
            zs = lo[2] + h * np.arange(i0[2], i1[2])
            # evaluate in z-chunks to bound memory
            step = max(1, int(6e6 // (len(xs) * len(ys))))
            for z0 in range(0, len(zs), step):
                zc = zs[z0:z0 + step]
                p = P3(xs[:, None, None], ys[None, :, None], zc[None, None, :])
                d = fn(p)
                d = np.broadcast_to(d, (len(xs), len(ys), len(zc))).astype(np.float32)
                sl = (slice(i0[0], i1[0]), slice(i0[1], i1[1]),
                      slice(i0[2] + z0, i0[2] + z0 + len(zc)))
                cur = F[sl]
                if mode == 'u':
                    F[sl] = smin(cur, d, k)
                elif mode == 's':        # subtract
                    F[sl] = smax(cur, -d, k)
                elif mode == 'i':        # intersect
                    F[sl] = smax(cur, d, k)
                elif mode == 'set':
                    F[sl] = d
        return F, lo, n

    def extend(self):
        T = SDF(); T.ops = list(self.ops)
        if hasattr(self, 'mesh_sdf'):
            T.mesh_sdf = self.mesh_sdf
        return T

    def shift(self, v):
        self.ops.append(('shift', v, None, V(-9, -9, -9), V(9, 9, 9)))

    def eval_points(self, pts):
        """Evaluate at scattered points (N,3) (no bbox culling, slower)."""
        pts = np.asarray(pts, float)
        d = np.full(len(pts), 0.5)
        p = P3(pts[:, 0], pts[:, 1], pts[:, 2])
        for mode, k, fn, olo, ohi in self.ops:
            if mode == 'shift':
                d -= k
                continue
            inside = np.all((pts >= olo) & (pts <= ohi), axis=1)
            if not inside.any():
                continue
            q = P3(pts[inside, 0], pts[inside, 1], pts[inside, 2])
            e = np.broadcast_to(fn(q), (inside.sum(),))
            cur = d[inside]
            if mode == 'u':
                d[inside] = smin(cur, e, k)
            elif mode == 's':
                d[inside] = smax(cur, -e, k)
            elif mode == 'i':
                d[inside] = smax(cur, e, k)
            elif mode == 'set':
                d[inside] = e
        return d


def surface_nets(F, lo, h):
    """Naive surface nets on grid F (inside < 0). Returns verts (N,3), quads (M,4)."""
    nx, ny, nz = F.shape
    s = F < 0
    cx, cy, cz = nx - 1, ny - 1, nz - 1

    def cid(i, j, k):
        return (i.astype(np.int64) * cy + j) * cz + k

    keys, poss = [], []
    quads = []
    for axis in range(3):
        if axis == 0:
            e = np.nonzero(s[:-1, :, :] != s[1:, :, :])
        elif axis == 1:
            e = np.nonzero(s[:, :-1, :] != s[:, 1:, :])
        else:
            e = np.nonzero(s[:, :, :-1] != s[:, :, 1:])
        i, j, k = e
        f0 = F[i, j, k]
        if axis == 0:
            f1 = F[i + 1, j, k]
        elif axis == 1:
            f1 = F[i, j + 1, k]
        else:
            f1 = F[i, j, k + 1]
        t = f0 / (f0 - f1)
        pos = np.stack([i, j, k], 1).astype(np.float64)
        pos[:, axis] += t
        inside0 = f0 < 0
        # the four cells around the edge
        if axis == 0:
            nb = [(0, -1, -1), (0, 0, -1), (0, 0, 0), (0, -1, 0)]
        elif axis == 1:
            nb = [(-1, 0, -1), (-1, 0, 0), (0, 0, 0), (0, 0, -1)]
        else:
            nb = [(-1, -1, 0), (0, -1, 0), (0, 0, 0), (-1, 0, 0)]
        cells = []
        valid = np.ones(len(i), bool)
        for di, dj, dk in nb:
            ii, jj, kk = i + di, j + dj, k + dk
            valid &= (ii >= 0) & (jj >= 0) & (kk >= 0) & (ii < cx) & (jj < cy) & (kk < cz)
            cells.append((ii, jj, kk))
        for (ii, jj, kk) in cells:
            ok = (ii >= 0) & (jj >= 0) & (kk >= 0) & (ii < cx) & (jj < cy) & (kk < cz)
            keys.append(cid(ii[ok], jj[ok], kk[ok]))
            poss.append(pos[ok])
        q = np.stack([cid(*c) for c in cells], 1)[valid]
        flip = ~inside0[valid]
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    keys = np.concatenate(keys)
    poss = np.concatenate(poss)
    uk, inv = np.unique(keys, return_inverse=True)
    cnt = np.bincount(inv)
    V_ = np.stack([np.bincount(inv, poss[:, a]) for a in range(3)], 1) / cnt[:, None]
    verts = lo + V_ * h
    quads = np.concatenate(quads)
    qi = np.searchsorted(uk, quads)
    return verts, qi


# ----------------------------------------------------------------------------
# Blender helpers
# ----------------------------------------------------------------------------
def mesh_from(name, verts, faces, coll=None):
    """faces: (M,k) int array (uniform k) or list of lists."""
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', verts.ravel())
    if isinstance(faces, np.ndarray):
        M, k = faces.shape
        me.loops.add(M * k)
        me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
        me.polygons.add(M)
        me.polygons.foreach_set('loop_start', (np.arange(M) * k).astype(np.int32))
    else:
        flat = [i for f in faces for i in f]
        starts = np.cumsum([0] + [len(f) for f in faces[:-1]])
        me.loops.add(len(flat))
        me.loops.foreach_set('vertex_index', np.array(flat, np.int32))
        me.polygons.add(len(faces))
        me.polygons.foreach_set('loop_start', starts.astype(np.int32))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def ntris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def get_co(ob):
    a = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3).astype(np.float64)


def set_co(ob, co):
    ob.data.vertices.foreach_set('co', np.asarray(co, np.float32).ravel())
    ob.data.update()


def decimate(ob, ratio=None, target=None, vgroup=None, vfac=1.0, invert=True, sym=False):
    if target is not None:
        ratio = min(1.0, target / max(1, ntris(ob)))
    m = ob.modifiers.new('dec', 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = ratio
    m.use_collapse_triangulate = True
    if sym:
        m.use_symmetry = True
        m.symmetry_axis = 'X'
    if vgroup:
        m.vertex_group = vgroup
        m.vertex_group_factor = vfac
        m.invert_vertex_group = invert
    apply_mods(ob)


def smooth(ob, factor=0.5, iters=2, vgroup=None):
    m = ob.modifiers.new('sm', 'SMOOTH')
    m.factor = factor
    m.iterations = iters
    if vgroup:
        m.vertex_group = vgroup
    apply_mods(ob)


def shade_smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


def sdf_mesh(name, sdf, lo, hi, h, keep=None, smooth_iters=1):
    t = time.time()
    F, glo, n = sdf.grid_eval(lo, hi, h)
    F[0], F[-1], F[:, 0], F[:, -1], F[:, :, 0], F[:, :, -1] = 0.5, 0.5, 0.5, 0.5, 0.5, 0.5
    v, q = surface_nets(F, glo, h)
    del F
    if keep is not None:   # face filter on face centres -> open sheet
        c = v[q].mean(1)
        m = keep(c)
        q = q[m]
        used = np.unique(q)
        remap = -np.ones(len(v), np.int64); remap[used] = np.arange(len(used))
        v = v[used]; q = remap[q]
    ob = mesh_from(name, v, q)
    log('mesh %-10s grid %s  %d verts  %.1fs' % (name, tuple(n), len(v), time.time() - t))
    if smooth_iters:
        smooth(ob, 0.5, smooth_iters)
    return ob


# ----------------------------------------------------------------------------
# Anatomy (rest pose: A-pose, arms 40 deg below horizontal, facing +Y)
# ----------------------------------------------------------------------------
ARM_DROP = math.radians(40)
H_EYE = 1.505             # eye level
HEADC = V(0, 0.0, H_EYE)  # head frame origin


class Skel:
    """Joint positions for side s (-1 = left, +1 = right). With J set (measured on the base mesh,
    right side), the methods return those, mirrored for the left."""
    def __init__(self):
        self.J = None
        self.pelvis = V(0, 0, 0.90)
        self.hipc = V(0, -0.005, 0.89)       # rig origin (hips)
        self.neck0 = V(0, -0.012, 1.335)
        self.neck1 = V(0, -0.016, 1.445)
        self.head0 = V(0, -0.016, 1.445)
        self.head1 = V(0, -0.010, 1.625)

    def set(self, J):
        self.J = {k: np.asarray(v, float) for k, v in J.items()}
        for k in ('neck0', 'neck1', 'head0', 'head1', 'hipc', 'pelvis'):
            if k in J:
                setattr(self, k, np.asarray(J[k], float))

    def _j(self, k, s):
        p = self.J[k].copy()
        p[0] *= s
        return p

    def arm_dir(self, s):
        if self.J is not None:
            return nrm(self._j('wrist', s) - self._j('elbow', s))
        return nrm(V(s * math.cos(ARM_DROP), 0.0, -math.sin(ARM_DROP)))

    def clav(self, s):
        if self.J is not None and 'clav' in self.J:
            return self._j('clav', s)
        return V(s * 0.022, 0.0, 1.318)

    def shoulder(self, s):
        if self.J is not None and 'shoulder' in self.J:
            return self._j('shoulder', s)
        return V(s * 0.168, -0.014, 1.302)

    def elbow(self, s):
        if self.J is not None and 'elbow' in self.J:
            return self._j('elbow', s)
        return self.shoulder(s) + 0.268 * self.arm_dir(s)

    def wrist(self, s):
        if self.J is not None and 'wrist' in self.J:
            return self._j('wrist', s)
        return self.elbow(s) + 0.232 * self.arm_dir(s)

    def hand_end(self, s):
        if self.J is not None and 'hand_end' in self.J:
            return self._j('hand_end', s)
        return self.wrist(s) + 0.165 * self.arm_dir(s)

    def palm_n(self, s):
        """Palm normal in rest pose (palms toward the thighs)."""
        d = self.arm_dir(s)
        return nrm(np.cross(d, V(0, 1, 0)) * (-s)) * 1.0

    def hip(self, s):
        if self.J is not None and 'hip' in self.J:
            return self._j('hip', s)
        return V(s * 0.084, 0.002, 0.865)

    def knee(self, s):
        if self.J is not None and 'knee' in self.J:
            return self._j('knee', s)
        return V(s * 0.098, 0.014, 0.478)

    def ankle(self, s):
        if self.J is not None and 'ankle' in self.J:
            return self._j('ankle', s)
        return V(s * 0.112, -0.012, 0.088)

    def toe(self, s):
        if self.J is not None and 'toe' in self.J:
            return self._j('toe', s)
        return V(s * 0.128, 0.150, 0.022)


SK = Skel()


# ----------------------------------------------------------------------------
# Base mesh (Blender Studio "Human Base Meshes" v1.4.1, CC0): body, head, hands, feet, eyes
# ----------------------------------------------------------------------------
BASE_MODE = True   # False: the old all-procedural body (SDF), kept for reference
BASE_BLEND = '/home/kazu/work/tokyo2090-assets/basemesh/unz/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
BASE_BODY = 'GEO-body_female_realistic'
BASE_HEIGHT = 1.620


def load_base(level=2):
    """Append the realistic female body + eyes, apply multires at `level`, convert to the modelling frame
    (faces +Y, feet on z=0, centred on x, 1.62 m). Returns (body, [eyeL, eyeR])."""
    names = [BASE_BODY, BASE_BODY + '.eye.L', BASE_BODY + '.eye.R']
    with bpy.data.libraries.load(BASE_BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    obs = {o.name: o for o in dst.objects}
    for o in obs.values():
        bpy.context.scene.collection.objects.link(o)
    body = obs[BASE_BODY]
    for m in list(body.modifiers):
        if m.type == 'MULTIRES':
            m.levels = level
            m.render_levels = level
    activate(body)
    for m in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    eyes = [obs[BASE_BODY + '.eye.L'], obs[BASE_BODY + '.eye.R']]
    allv = [body] + eyes
    for o in allv:   # bake world transforms (eyes are parented) into the mesh
        o.data = o.data.copy()
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    co = get_co(body)
    lo, hi = co.min(0), co.max(0)
    sc = BASE_HEIGHT / (hi[2] - lo[2])
    cx = 0.5 * (lo[0] + hi[0])
    for o in allv:
        c = get_co(o)
        c = np.stack([-(c[:, 0] - cx), -c[:, 1], c[:, 2] - lo[2]], 1) * sc   # rotate 180 deg about z
        set_co(o, c)
        o.data.flip_normals() if False else None
        o.data.update()
    body.name = 'Body'
    eyes[0].name, eyes[1].name = 'EyeL', 'EyeR'
    # character's left is +X in the base (facing -Y); after the rotation it is -X: name follows geometry
    if get_co(eyes[0])[:, 0].mean() > 0:
        eyes = eyes[::-1]
    log('base mesh: %d verts, %d faces, scale %.3f' % (len(body.data.vertices), len(body.data.polygons), sc))
    return body, eyes


# joints measured on the loaded base mesh (right side; modelling frame, before the arm re-pose)
BASE_J = {
    'clav': (0.025, 0.005, 1.330), 'shoulder': (0.160, -0.020, 1.290), 'elbow': (0.245, -0.025, 1.035),
    'wrist': (0.345, 0.030, 0.835), 'hand_end': (0.392, 0.062, 0.712),
    'hip': (0.085, 0.000, 0.835), 'knee': (0.105, 0.005, 0.465), 'ankle': (0.122, -0.040, 0.080),
    'toe': (0.141, 0.144, 0.016),
    'neck0': (0, 0.005, 1.345), 'neck1': (0, 0.022, 1.435), 'head0': (0, 0.022, 1.435), 'head1': (0, 0.030, 1.620),
    'hipc': (0, 0.000, 0.890), 'pelvis': (0, 0.0, 0.90)}
ARM_RAISE = 24.0   # degrees: base A-pose (arms ~65 deg below horizontal) -> ~41 deg


def laplace_smooth_field(me, w, iters=30, lam=0.5, fixed=None):
    from scipy import sparse
    ev = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ev); ev = ev.reshape(-1, 2)
    n = len(me.vertices)
    A = sparse.coo_matrix((np.ones(len(ev) * 2), (np.r_[ev[:, 0], ev[:, 1]], np.r_[ev[:, 1], ev[:, 0]])), shape=(n, n)).tocsr()
    deg = np.asarray(A.sum(1)).ravel()
    w = w.copy()
    for _ in range(iters):
        avg = (A @ w) / np.maximum(deg, 1)
        nw = w + lam * (avg - w)
        if fixed is not None:
            nw[fixed] = w[fixed]
        w = nw
    return w


def repose_arms(body, deg=ARM_RAISE):
    """Raise both arms about the shoulder joints (y axis) with a smooth shoulder blend."""
    co = get_co(body)
    me = body.data
    zt = np.array([1.17, 1.16, 1.12, 1.08, 1.04, 1.00, 0.96, 0.92, 0.88, 0.84, 0.80, 0.76, 0.72, 0.68])
    gap = np.array([0.147, 0.147, 0.146, 0.150, 0.155, 0.166, 0.186, 0.207, 0.226, 0.241, 0.252, 0.272, 0.283, 0.283])
    W = np.zeros(len(co))
    for s in (-1, 1):
        x = co[:, 0] * s; z = co[:, 2]
        sh = np.array(BASE_J['shoulder']) * [s, 1, 1]; el = np.array(BASE_J['elbow']) * [s, 1, 1]
        d = nrm(el - sh)
        t = (co - sh) @ d
        low = (z <= 1.17) & (z > 0.60) & (x > np.interp(z, zt[::-1], gap[::-1]))
        up = (z > 1.17) & (x > 0.09)
        w = np.zeros(len(co))
        w[low] = 1.0
        w[up] = sstep(-0.02, 0.08, t[up]) * sstep(0.08, 0.19, x[up])
        W += w * s
    fixed = np.abs(W) > 0.999
    Ws = laplace_smooth_field(me, np.abs(W), 120, 0.5, fixed)
    sign = np.sign(co[:, 0])
    out = co.copy()
    for s in (-1, 1):
        m = (sign == s) & (Ws > 1e-4)
        sh = np.array(BASE_J['shoulder']) * [s, 1, 1]
        ang = np.radians(-s * deg) * Ws[m]
        r = co[m] - sh
        c, sn = np.cos(ang), np.sin(ang)
        out[m, 0] = sh[0] + r[:, 0] * c + r[:, 2] * sn
        out[m, 2] = sh[2] - r[:, 0] * sn + r[:, 2] * c
    set_co(body, out)
    J = dict(BASE_J)
    sh = np.array(BASE_J['shoulder'])
    th = math.radians(-deg)
    for k in ('elbow', 'wrist', 'hand_end'):
        r = np.array(BASE_J[k]) - sh
        J[k] = tuple(sh + np.array([r[0] * math.cos(th) + r[2] * math.sin(th), r[1], -r[0] * math.sin(th) + r[2] * math.cos(th)]))
    log('arms raised %.0f deg' % deg)
    return J


# face landmarks on the base head (modelling frame, measured after loading)
BASE_EYE_C = (0.0325, 0.1204, 1.5143)
FACE_WARPS = [   # (kind, centre, radius, params) applied in order to the dense head; mirrored where x != 0
    ('scale', (0.0325, 0.1204, 1.5143), 0.028, (1.10, 1.08, 1.14)),     # larger, rounder eyes
    ('scale', (0.0, 0.150, 1.478), 0.026, (0.86, 0.92, 0.90)),         # smaller, narrower nose
    ('move', (0.0, 0.165, 1.486), 0.012, (0.0, -0.002, 0.0006)),        # tip: shorter
    ('move', (0.0, 0.152, 1.446), 0.022, (0.0, 0.0, 0.0030)),           # mouth closer to the nose
    ('scale', (0.0, 0.153, 1.447), 0.020, (0.92, 1.0, 0.95)),           # smaller mouth
    ('smile', (0.0, 0.140, 1.4495), 0.0235, (0.0050, 0.010)),          # corners up: faint smile
    ('push', (0.036, 0.135, 1.468), 0.026, 0.0022),                     # round, youthful cheeks
    ('jaw', (0.0, 0.0, 0.0), 0.0, (0.075, 1.475, 1.430, 1.385, 1.410)),  # narrower lower face (V-line)
    ('scale', (0.0, 0.128, 1.412), 0.030, (0.86, 0.96, 0.93)),          # small chin
    # flat, soft Japanese profile (のっぺり): mouth/muzzle back, lips thinner, chin back, flatter bones
    ('move', (0.0, 0.135, 1.452), 0.055, (0.0, -0.0035, 0.0)),          # whole lower midface back
    ('move', (0.0, 0.150, 1.451), 0.030, (0.0, -0.0040, 0.0)),          # muzzle / mouth further back
    ('scale', (0.0, 0.148, 1.4505), 0.017, (0.90, 0.82, 0.88)),         # lips: narrower, thinner, flatter
    ('move', (0.0, 0.152, 1.4555), 0.008, (0.0, -0.0012, 0.0)),         # upper lip less protruding
    ('move', (0.0, 0.132, 1.412), 0.026, (0.0, -0.0030, 0.0)),          # chin back
    ('move', (0.0, 0.142, 1.506), 0.016, (0.0, -0.0020, 0.0)),          # lower, flatter nose root
    ('scale', (0.0, 0.150, 1.476), 0.014, (0.88, 1.0, 1.0)),            # narrower nostrils
    ('move', (0.056, 0.100, 1.488), 0.030, (-0.0030, -0.0010, 0.0)),    # flatter, softer cheekbones
    ('move', (0.026, 0.132, 1.532), 0.022, (0.0, -0.0018, 0.0)),        # flatter brow ridge
    ('move', (0.0, 0.140, 1.532), 0.018, (0.0, -0.0012, 0.0)),
    ('move', (0.050, 0.035, 1.418), 0.030, (0.0020, 0.0, 0.0025)),      # soft, rounded jaw angle
    ('scale', (0.0, 0.070, 1.470), 0.075, (1.022, 1.0, 1.0)),           # a touch rounder overall
    ('scale', (0.085, 0.100, 1.190), 0.085, (0.94, 0.86, 0.93)),        # smaller bust (lean, athletic)
]


def falloff(d, r):
    t = np.clip(1 - (d / r) ** 2, 0, 1)
    return t * t


def warp_face(obs, warps=None):
    """Apply FACE_WARPS to the given objects (body, eyes), mirrored on the left side."""
    warps = FACE_WARPS if warps is None else warps
    for ob in obs:
        co = get_co(ob)
        nn = np.empty(len(co) * 3, np.float32); ob.data.vertices.foreach_get('normal', nn); nn = nn.reshape(-1, 3)
        for kind, c, r, prm in warps:
            cs = [np.array(c, float)]
            if abs(c[0]) > 1e-6:
                cs.append(np.array(c, float) * [-1, 1, 1])
            for cc in cs:
                sx = 1 if cc[0] >= 0 else -1
                d = np.linalg.norm(co - cc, axis=1)
                m = d < r
                if not m.any():
                    continue
                w = falloff(d[m], r)[:, None]
                if kind == 'scale':
                    f = np.array(prm, float)
                    co[m] = cc + (co[m] - cc) * (1 + (f - 1) * w)
                elif kind == 'move':
                    dv = np.array(prm, float) * [sx, 1, 1]
                    co[m] = co[m] + dv * w
                elif kind == 'push':
                    co[m] = co[m] + nn[m] * prm * w
            if kind == 'jaw':     # x-scale of the lower face, fading out above the mouth and into the neck
                a, z0, z1, z2, z3 = prm
                w = sstep(z0, z1, co[:, 2]) * sstep(z2, z3, co[:, 2]) * sstep(-0.03, 0.02, co[:, 1])
                co[:, 0] *= 1 - a * w
            if kind == 'smile':   # raise the mouth corners progressively along the mouth (no lumps)
                a, rz = prm
                x = np.abs(co[:, 0]); dz = co[:, 2] - c[2]
                w = np.minimum(x / r, 1.0) ** 2 * sstep(r + 0.010, r + 0.002, x) * falloff(np.abs(dz), rz) \
                    * sstep(c[1] - 0.02, c[1], co[:, 1])
                co[:, 2] += a * w
        set_co(ob, co)


class MeshSDF:
    """Signed distance to a closed-ish triangle mesh (the base body + eyeballs) on nested grids: exact
    (BVH) in a narrow band around the surface, EDT outside it, sign by flood fill from the border."""
    def __init__(self, obs, grids):
        from mathutils.bvhtree import BVHTree
        from scipy import ndimage
        t0 = time.time()
        V_, F_ = [], []
        off = 0
        for ob in obs:
            ob.data.calc_loop_triangles()
            co = get_co(ob)
            tri = np.empty(len(ob.data.loop_triangles) * 3, np.int32)
            ob.data.loop_triangles.foreach_get('vertices', tri)
            V_.append(co); F_.append(tri.reshape(-1, 3) + off); off += len(co)
        self.V = np.vstack(V_); self.F = np.vstack(F_)
        self.bvh = BVHTree.FromPolygons([Vector(v) for v in self.V], self.F.tolist())
        # surface samples for the shell: vertices, edge midpoints and centres of triangles
        T = self.V[self.F]
        samp = np.vstack([self.V, T.mean(1), 0.5 * (T[:, 0] + T[:, 1]), 0.5 * (T[:, 1] + T[:, 2]), 0.5 * (T[:, 2] + T[:, 0])])
        self.grids = []
        for lo, hi, h in grids:
            lo = np.asarray(lo, float); hi = np.asarray(hi, float)
            n = np.ceil((hi - lo) / h).astype(int) + 1
            idx = np.round((samp - lo) / h).astype(int)
            ok = np.all((idx >= 0) & (idx < n), 1)
            shell = np.zeros(n, bool)
            shell[idx[ok, 0], idx[ok, 1], idx[ok, 2]] = True
            band = ndimage.binary_dilation(shell, iterations=2)
            if not self.grids:   # the first (coarse, whole-body) grid: sign by flood fill from the border
                lab, nl = ndimage.label(~band)
                border = np.unique(np.concatenate([lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                                                   lab[:, :, 0].ravel(), lab[:, :, -1].ravel()]))
                outside = np.isin(lab, border[border > 0])
            else:                # finer grids (the body crosses their borders): sign from the coarse grid
                glo, ghi, gh, GF = self.grids[0]
                ii = np.indices(n).reshape(3, -1).T
                pts = lo + ii * h
                outside = (ndimage.map_coordinates(GF, ((pts - glo) / gh).T, order=1, mode='nearest') > 0).reshape(n)
            far = ndimage.distance_transform_edt(~band) * h + 2 * h
            F = np.where(outside, far, -far).astype(np.float32)
            bi = np.argwhere(band)
            P = lo + bi * h
            F[band] = self._exact(P)
            self.grids.append((lo, hi, h, F))
            log('mesh SDF grid %s h=%.4f: %d band voxels %.1fs' % (tuple(n), h, len(bi), time.time() - t0))

    def _exact(self, P):
        d = np.empty(len(P))
        fn = self.bvh.find_nearest
        for i, p in enumerate(P):
            loc, nor, fi, dist = fn(Vector(p))
            if loc is None:
                d[i] = 1.0
                continue
            dv = Vector(p) - loc
            d[i] = dist if dv.dot(nor) >= 0 else -dist
        return d

    def sample(self, X, Y, Z):
        from scipy import ndimage
        X, Y, Z = np.broadcast_arrays(X, Y, Z)
        shp = X.shape
        pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        out = np.full(len(pts), 1.0)
        done = np.zeros(len(pts), bool)
        for lo, hi, h, F in sorted(self.grids, key=lambda g: g[2]):   # finest first
            m = ~done & np.all((pts >= lo + h) & (pts <= hi - h), 1)
            if m.any():
                out[m] = ndimage.map_coordinates(F, ((pts[m] - lo) / h).T, order=1, mode='nearest')
                done |= m
        return out.reshape(shp)

    def as_sdf(self):
        S = SDF()
        lo = np.min([g[0] for g in self.grids], 0); hi = np.max([g[1] for g in self.grids], 0)
        S.add(lambda p: self.sample(p.X, p.Y, p.Z), lo, hi, 0.0)
        S.mesh_sdf = self
        return S


SDF_GRIDS = [((-0.70, -0.20, -0.02), (0.70, 0.25, 1.66), 0.004),
             ((-0.30, -0.18, 0.60), (0.30, 0.22, 1.42), 0.002),
             ((-0.12, -0.10, 1.36), (0.12, 0.22, 1.66), 0.0012)]


def setup_anatomy(J, eyes):
    """Set the module-level anatomy (skeleton, head frame, eye centres) from the base mesh."""
    global HEADC, EYE_C, EYE_R, HAIR_C, NECK_CUT, ORIGIN
    SK.set(J)
    ec = [get_co(e).mean(0) for e in eyes]          # eyes[0] = left (-x)
    EYE_C = [np.array(ec[0]), np.array(ec[1])]
    EYE_R = float(np.ptp(get_co(eyes[0]), 0).max() / 2)
    HEADC = V(0.0, 0.5 * (ec[0][1] + ec[1][1]) - 0.0755, 0.5 * (ec[0][2] + ec[1][2]))
    HAIR_C = HEADC + V(0, -0.015, 0.012)
    NECK_CUT = 1.400
    ORIGIN = V(0, 0.0, 0.89)
    log('anatomy: eyes %s r=%.4f, head centre %s' % (np.round(EYE_C[1], 4), EYE_R, np.round(HEADC, 4)))


def build_body_sdf():
    S = SDF()
    # --- torso loft (z, half width, half depth, centre y)
    S.add(lambda p: sd_loft(p, [
        (0.736, 0.040, 0.030, -0.008),
        (0.752, 0.105, 0.072, -0.012),
        (0.780, 0.145, 0.090, -0.016),
        (0.815, 0.160, 0.098, -0.020),
        (0.870, 0.157, 0.094, -0.014),
        (0.925, 0.141, 0.087, -0.006),
        (0.980, 0.121, 0.080, -0.002),
        (1.020, 0.116, 0.078, -0.000),
        (1.070, 0.121, 0.083, 0.002),
        (1.120, 0.130, 0.089, 0.002),
        (1.180, 0.137, 0.091, -0.002),
        (1.240, 0.139, 0.088, -0.008),
        (1.290, 0.128, 0.079, -0.012),
        (1.330, 0.092, 0.062, -0.014),
        (1.362, 0.036, 0.032, -0.014)], expo=2.0),
        V(-0.17, -0.12, 0.72), V(0.17, 0.10, 1.38), 0.0)
    for s in (-1, 1):
        # glutes
        S.ellipsoid(V(s * 0.068, -0.068, 0.825), (0.074, 0.058, 0.088), k=0.035)
        # breasts (modest)
        R = frame_from(V(s * 0.25, 1, -0.15), V(0, 0, 1))
        S.ellipsoid(V(s * 0.058, 0.064, 1.168), (0.052, 0.050, 0.044), k=0.032, R=R)
        # trapezius / neck slope
        S.cone(V(s * 0.030, -0.028, 1.385), V(s * 0.150, -0.020, 1.322), 0.030, 0.024, k=0.035)
        # clavicles
        S.cone(V(s * 0.020, 0.050, 1.322), V(s * 0.150, 0.010, 1.333), 0.0085, 0.0085, k=0.014)
        # shoulder blades
        S.ellipsoid(V(s * 0.072, -0.072, 1.225), (0.050, 0.022, 0.064), k=0.03)
        # deltoid
        sh = SK.shoulder(s); d = SK.arm_dir(s)
        Rd = frame_from(d, V(0, 1, 0))
        S.ellipsoid(sh + 0.028 * d + V(0, 0, 0.004), (0.046, 0.047, 0.07), k=0.03, R=Rd)
        # upper arm
        el = SK.elbow(s); wr = SK.wrist(s)
        S.cone(sh, el, 0.042, 0.031, k=0.03)
        S.ellipsoid(sh + 0.13 * d + V(0, 0.010, 0), (0.033, 0.034, 0.075), k=0.02, R=Rd)  # biceps
        # forearm (flattening toward the wrist)
        S.cone(el, el + 0.075 * d, 0.032, 0.034, k=0.02)
        S.cone(el + 0.075 * d, wr, 0.034, 0.021, k=0.02)
        Rw = frame_from(d, SK.palm_n(s))   # local x = thumb side (front), y = palm normal
        S.ellipsoid(wr - 0.01 * d, (0.026, 0.018, 0.03), k=0.015, R=Rw)
        add_hand(S, s)
        # legs
        hp = SK.hip(s); kn = SK.knee(s); an = SK.ankle(s)
        S.cone(hp + V(s * 0.006, -0.004, 0.02), kn, 0.084, 0.047, k=0.04)
        dl = nrm(kn - hp)
        Rl = frame_from(dl, V(0, 1, 0))
        S.ellipsoid(hp + 0.42 * (kn - hp) + V(s * 0.012, 0.022, 0), (0.064, 0.062, 0.16), k=0.03, R=Rl)  # quads
        S.ellipsoid(kn + V(-s * 0.020, 0.012, 0.065), (0.034, 0.034, 0.055), k=0.025)   # vastus medialis
        S.ellipsoid(hp + 0.45 * (kn - hp) + V(s * 0.006, -0.025, 0), (0.055, 0.05, 0.15), k=0.03, R=Rl)  # hamstrings
        S.ellipsoid(hp + 0.30 * (kn - hp) + V(-s * 0.032, 0.0, 0), (0.045, 0.05, 0.12), k=0.03, R=Rl)  # adductors
        S.sphere(kn + V(0, 0.004, 0.0), 0.046, k=0.03)
        S.ellipsoid(kn + V(0, 0.040, 0.012), (0.022, 0.012, 0.026), k=0.016)   # patella
        S.cone(kn, an, 0.045, 0.029, k=0.03)
        S.ellipsoid(kn + V(-s * 0.006, -0.026, -0.125), (0.041, 0.040, 0.095), k=0.03)  # calf
        S.ellipsoid(kn + V(s * 0.012, -0.020, -0.16), (0.032, 0.034, 0.075), k=0.03)
        add_foot(S, s)
    # neck
    S.cone(SK.neck0 + V(0, 0, -0.03), SK.neck1 + V(0, 0.000, 0.0), 0.046, 0.041, k=0.025)
    # navel
    S.sphere(V(0, 0.079, 0.985), 0.0055, k=0.006, mode='s')
    # spine groove
    S.cone(V(0, -0.084, 0.98), V(0, -0.086, 1.30), 0.007, 0.007, k=0.02, mode='s')
    return S


def add_hand(S, s):
    wr = SK.wrist(s); d = SK.arm_dir(s); n = SK.palm_n(s)   # n: palm normal (toward thigh)
    side = nrm(np.cross(n, d)) * s * -1.0                    # thumb side (front +Y)
    if side[1] < 0:
        side = -side
    Rh = np.stack([side, n, d])
    # palm
    S.add(lambda p, c=wr + 0.048 * d, R=Rh: sd_box(p, c, (0.036, 0.012, 0.043), R, 0.011),
          np.minimum(wr, wr + 0.1 * d) - 0.05, np.maximum(wr, wr + 0.1 * d) + 0.05, k=0.012)
    S.ellipsoid(wr + 0.030 * d + 0.020 * side + 0.007 * n, (0.016, 0.014, 0.026), k=0.01, R=Rh)  # thenar
    # fingers: offset across, length, radius, splay
    fingers = [(0.025, 0.073, 0.0083, 0.10), (0.008, 0.080, 0.0086, 0.02),
               (-0.009, 0.075, 0.0081, -0.06), (-0.025, 0.060, 0.0072, -0.14)]
    curls = (0.25, 0.40, 0.30) if s < 0 else (0.12, 0.22, 0.17)   # right hand relaxed open (held in flight)
    for off, L, r, spl in fingers:
        base = wr + 0.088 * d + off * side
        dirv = nrm(d + spl * side)
        segs = (0.45, 0.30, 0.25)
        pts = [base - 0.006 * dirv]; ang = 0.0
        cur = base.copy()
        for sl, cu in zip(segs, curls):
            ang += cu
            dv = nrm(math.cos(ang) * dirv + math.sin(ang) * n)
            cur = cur + sl * L * dv
            pts.append(cur.copy())
        S.chain(pts, [r * 1.05, r, r * 0.92, r * 0.82], k=0.006, kin=0.003)
    # thumb
    tb = wr + 0.022 * d + 0.024 * side + 0.004 * n
    t1 = nrm(0.75 * d + 0.55 * side + 0.25 * n) if s < 0 else nrm(0.70 * d + 0.68 * side + 0.15 * n)
    t2 = nrm(0.85 * d + 0.25 * side + 0.45 * n) if s < 0 else nrm(0.88 * d + 0.32 * side + 0.30 * n)
    p1 = tb + 0.038 * t1; p2 = p1 + 0.030 * t2
    S.chain([tb, p1, p2], [0.0115, 0.0092, 0.0078], k=0.01, kin=0.003)


def add_foot(S, s):
    an = SK.ankle(s); toe = SK.toe(s)
    fwd = nrm(V(toe[0] - an[0], toe[1] - an[1], 0))
    lat = nrm(np.cross(fwd, V(0, 0, 1))) * 1.0  # outward for right... sign per side below
    if lat[0] * s < 0:
        lat = -lat
    sole = 0.013
    heel = an + V(0, 0, 0) - 0.030 * fwd
    heel[2] = sole + 0.028
    ball = an + 0.150 * fwd; ball[2] = sole + 0.018

    def foot(p, an=an, heel=heel, ball=ball):
        d = sd_roundcone(p, heel, ball, 0.030, 0.021)
        d = smin(d, sd_roundcone(p, an + V(0, 0.0, -0.01), ball + V(0, 0, 0.006) - 0.03 * fwd, 0.031, 0.020), 0.03)
        d = smax(d, sole - p.Z, 0.006)
        return d
    S.add(foot, np.minimum(heel, ball) - 0.06, np.maximum(an, ball) + 0.06, k=0.025)
    S.sphere(an + 0.012 * lat + V(0, 0, 0.004), 0.017, k=0.012)   # outer ankle bone
    S.sphere(an - 0.012 * lat + V(0, 0, 0.010), 0.016, k=0.012)
    # toes (big toe + 4)
    toes = [(-0.024, 0.050, 0.0115), (-0.006, 0.040, 0.0080), (0.008, 0.035, 0.0075),
            (0.020, 0.030, 0.0070), (0.031, 0.024, 0.0065)]
    for off, L, r in toes:
        b = ball + off * lat - 0.004 * fwd + V(0, 0, -0.002)
        dr = nrm(fwd + off * 2.0 * lat)
        e = b + L * dr; e[2] = sole + r * 0.85
        b2 = b.copy(); b2[2] = sole + r * 1.1
        S.cone(b2, e, r, r * 0.9, k=0.006)


# ---------------------------------------------------------------- head
def hp_(x, y, z):
    return HEADC + V(x, y, z)


EYE_C = [hp_(s * 0.0312, 0.0490, 0.0) for s in (-1, 1)]
EYE_R = 0.0136
EYE_HALF, EYE_HU, EYE_HL = 0.0156, 0.0069, 0.0047


def eye_lens(u, w, s):
    """2D almond opening in eye-local (u outward, w up), <0 inside."""
    tilt = math.radians(7)
    uu = u * math.cos(tilt) + w * math.sin(tilt)
    ww = -u * math.sin(tilt) + w * math.cos(tilt)
    half = EYE_HALF
    hu, hl = EYE_HU, EYE_HL
    Ru = (half ** 2 + hu ** 2) / (2 * hu)
    Rl = (half ** 2 + hl ** 2) / (2 * hl)
    ww = ww + 0.0006 * (uu / half)  # outer corner up
    du = np.sqrt((uu + 0.0012) ** 2 + (ww + Ru - hu) ** 2) - Ru
    dl = np.sqrt(uu ** 2 + (ww - Rl + hl) ** 2) - Rl
    return np.maximum(du, dl)


HEAD_SECTIONS = [  # z, half width, y0, front, back[, front exponent]   (head frame, metres)
    # widths and fronts measured from the silhouettes of boards/saki-ref/face-front.png and face-side.png
    (+0.112, 0.012, -0.024, 0.012, 0.012),
    (+0.100, 0.048, -0.022, 0.066, 0.058),
    (+0.080, 0.064, -0.020, 0.090, 0.080),
    (+0.050, 0.0695, -0.019, 0.095, 0.088),
    (+0.030, 0.0690, -0.018, 0.100, 0.088),
    (+0.012, 0.0670, -0.018, 0.101, 0.087),
    (-0.005, 0.0645, -0.018, 0.099, 0.083, 2.2),
    (-0.025, 0.0615, -0.016, 0.098, 0.075, 2.20),
    (-0.045, 0.0580, -0.012, 0.096, 0.064, 2.35),
    (-0.063, 0.0510, -0.005, 0.085, 0.052, 2.45),
    (-0.072, 0.0465, 0.000, 0.0805, 0.048, 2.35),
    (-0.081, 0.0400, 0.006, 0.0745, 0.044, 2.20),
    (-0.090, 0.0320, 0.016, 0.0650, 0.040, 2.25),
    (-0.097, 0.0260, 0.028, 0.0510, 0.032, 2.15),
    (-0.1015, 0.0140, 0.042, 0.0330, 0.020, 2.10),
    (-0.1040, 0.0060, 0.050, 0.0200, 0.010, 2.05)]
MOUTH_Z = -0.0625


def mouth_line(x):
    q = x / 0.0215
    return MOUTH_Z + 0.0020 * q ** 2 + 0.0010 * q ** 4


def upper_lid_curve(i, s, n=15, lift=0.0, rad=None, span=0.98):
    """3D points along the upper lid margin of eye i (inner -> outer corner)."""
    c = EYE_C[i]
    rad = EYE_R + 0.0011 if rad is None else rad
    tilt = math.radians(7); half = EYE_HALF; hu = EYE_HU
    Ru = (half ** 2 + hu ** 2) / (2 * hu)
    uu = np.linspace(-half * span, half * span, n)
    ww = np.sqrt(np.maximum(Ru ** 2 - (uu + 0.0012) ** 2, 0)) - Ru + hu - 0.0006 * uu / half + lift
    u = uu * math.cos(tilt) - ww * math.sin(tilt)
    w = uu * math.sin(tilt) + ww * math.cos(tilt)
    y = np.sqrt(np.maximum(rad ** 2 - u ** 2 - w ** 2, 0.004 ** 2))
    return np.stack([c[0] + s * u, c[1] + y, c[2] + w], 1), uu / half


def build_head_sdf(S):
    sec = [(r[0] + HEADC[2], r[1], r[2] + HEADC[1], r[3], r[4]) + (tuple(r[5:]) if len(r) > 5 else (2.15,)) for r in HEAD_SECTIONS]
    S.add(lambda p: sd_egg_loft(p, sec, 2.15, 2.0), HEADC + V(-0.08, -0.12, -0.115),
          HEADC + V(0.08, 0.10, 0.115), 0.025)
    for s in (-1, 1):
        S.ellipsoid(hp_(s * 0.043, 0.046, -0.012), (0.017, 0.017, 0.012), k=0.022)      # cheekbones (soft)
        S.ellipsoid(hp_(s * 0.030, 0.066, -0.024), (0.015, 0.009, 0.014), k=0.022)      # apples of the cheeks
        S.ellipsoid(hp_(s * 0.030, 0.066, -0.052), (0.013, 0.010, 0.016), k=0.026)      # soft fill beside the mouth
        # ear: vertical, tilted back, lower and further back (as in the profile reference)
        ang = math.radians(12)
        Rz = np.array([[1, 0, 0], [0, math.cos(ang), math.sin(ang)], [0, -math.sin(ang), math.cos(ang)]])
        ec = (s * 0.0640, -0.036, -0.016)
        S.ellipsoid(hp_(*ec), (0.0070, 0.0175, 0.0285), k=0.006, R=Rz)
        S.ellipsoid(hp_(s * 0.0710, -0.033, -0.017), (0.0040, 0.0095, 0.0125), k=0.003, R=Rz, mode='s')
        S.ellipsoid(hp_(s * 0.0705, -0.036, -0.011), (0.0030, 0.0135, 0.0225), k=0.002, R=Rz, mode='s')  # scapha
        S.ellipsoid(hp_(s * 0.0630, -0.030, -0.042), (0.0042, 0.0068, 0.0068), k=0.004)               # lobe
    for s in (-1, 1):   # soft eye sockets
        S.ellipsoid(hp_(s * 0.0312, 0.077, 0.002), (0.019, 0.015, 0.012), k=0.012, mode='s')
    for i, s in enumerate((-1, 1)):   # lids over the eyeball (opening cut below)
        S.sphere(EYE_C[i], EYE_R + 0.0011, k=0.005)
    for i, s in enumerate((-1, 1)):   # upper lid margin and crease
        rim, t = upper_lid_curve(i, s, 11, lift=0.0004, span=0.80)
        S.chain(list(rim), [0.0011] * len(rim), k=0.0012, kin=0.001)
        cr, t = upper_lid_curve(i, s, 11, lift=0.0050, rad=EYE_R + 0.0020, span=0.85)
        cr[:, 2] -= 0.0010 * (np.abs(t) ** 2)
        S.chain(list(cr), [0.0009] * len(cr), k=0.0016, kin=0.001, mode='s')
    # nose: small, soft bridge, slightly upturned tip
    S.cone(hp_(0, 0.0745, 0.000), hp_(0, 0.0930, -0.028), 0.0034, 0.0060, k=0.011)
    S.sphere(hp_(0, 0.0918, -0.0335), 0.0078, k=0.006)
    for s in (-1, 1):
        S.ellipsoid(hp_(s * 0.0098, 0.0835, -0.0385), (0.0049, 0.0058, 0.0045), k=0.007)
    S.cone(hp_(0, 0.0895, -0.0390), hp_(0, 0.0850, -0.0440), 0.0036, 0.0036, k=0.008)   # columella
    for s in (-1, 1):   # nostrils
        S.ellipsoid(hp_(s * 0.0062, 0.0878, -0.0408), (0.0029, 0.0044, 0.0017), k=0.0015, mode='s')
    # lips (soft, small, following the faint smile)
    def lip(c, r):
        def f(p):   # follows the smile curve and the curve of the face (corners set back)
            x = p.X - HEADC[0]
            return _ellip(x, p.Y - c[1] + 0.010 * (x / 0.022) ** 2, p.Z - c[2] - (mouth_line(x) - MOUTH_Z), r)
        return f
    for c, r, k in ((hp_(0, 0.0840, MOUTH_Z + 0.0046), (0.0192, 0.0040, 0.0046), 0.006),
                    (hp_(0, 0.0812, MOUTH_Z - 0.0056), (0.0160, 0.0048, 0.0058), 0.0065)):
        S.add(lip(c, r), c - 0.035, c + 0.035, k)

    def slit(p):   # mouth line with a faint smile
        x = p.X - HEADC[0]; z = p.Z - HEADC[2]; y = p.Y - HEADC[1]
        d = np.abs(z - mouth_line(x)) - 0.0006
        d = np.maximum(d, np.abs(x) - 0.0210)
        d = np.maximum(d, 0.080 - 0.010 * (x / 0.022) ** 2 - y)
        return d
    S.add(slit, hp_(-0.035, 0.06, -0.08), hp_(0.035, 0.10, -0.05), k=0.0012, mode='s')
    for s in (-1, 1):
        S.sphere(hp_(s * 0.0210, 0.0735, float(mouth_line(0.0210)) + 0.0002), 0.0012, k=0.003, mode='s')
    S.ellipsoid(hp_(0, 0.0655, -0.0890), (0.0135, 0.0110, 0.0100), k=0.024)       # chin (small, round)
    S.ellipsoid(hp_(0, 0.0450, -0.0975), (0.0240, 0.0320, 0.0060), k=0.016)       # chin underside

    def opening(p):   # eye openings: cut lids + socket in front of the eyeball
        out = None
        for i, s in enumerate((-1, 1)):
            c = EYE_C[i]
            d = eye_lens((p.X - c[0]) * s, p.Z - c[2], s)
            d = np.maximum(d, (c[1] + 0.0035) - p.Y)
            out = d if out is None else np.minimum(out, d)
        return out
    S.add(opening, hp_(-0.05, 0.04, -0.012), hp_(0.05, 0.09, 0.012), k=0.0008, mode='s')
    return S


# ----------------------------------------------------------------------------
# Hair: volume cap above a hairline + flattened tapered locks
# ----------------------------------------------------------------------------
HAIR_C = HEADC + V(0, -0.015, 0.012)


def head_only_sdf():
    S = SDF()
    sec = [(r[0] + HEADC[2], r[1], r[2] + HEADC[1], r[3], r[4]) + (tuple(r[5:]) if len(r) > 5 else (2.15,)) for r in HEAD_SECTIONS]
    S.add(lambda p: sd_egg_loft(p, sec, 2.15, 2.0), HEADC + V(-0.08, -0.12, -0.11),
          HEADC + V(0.08, 0.10, 0.115), 0.0)
    return S


def scalp_points(H, theta, phi):
    """Points on the skin along rays from HAIR_C (theta: azimuth, 0 = front; phi: from the top), arrays."""
    theta = np.asarray(theta, float); phi = np.asarray(phi, float)
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta) * np.sin(phi), np.cos(phi)], -1)
    lo = np.zeros(len(theta)); hi = np.full(len(theta), 0.2)
    for _ in range(26):
        m = 0.5 * (lo + hi)
        inside = H.eval_points(HAIR_C + m[:, None] * d) < 0
        lo = np.where(inside, m, lo); hi = np.where(inside, hi, m)
    return HAIR_C + lo[:, None] * d, d


def hairline_z(theta):
    """Hairline height (head frame) by azimuth (deg)."""
    a = abs(math.degrees(theta)) if np.isscalar(theta) else np.abs(np.degrees(theta))
    return np.interp(a, [0, 35, 60, 72, 86, 104, 118, 135, 180],
                     [0.074, 0.062, 0.040, 0.026, 0.020, 0.016, -0.010, -0.062, -0.080])


def sd_lock(p, pts, rads, n, flat=1.8):
    """Chain of round cones flattened along n (thin across the scalp normal)."""
    n = nrm(n)
    c = pts[0]
    def tr(x, y, z):
        t = (x - c[0]) * n[0] + (y - c[1]) * n[1] + (z - c[2]) * n[2]
        return x + (flat - 1) * t * n[0], y + (flat - 1) * t * n[1], z + (flat - 1) * t * n[2]
    X, Y, Z = tr(p.X, p.Y, p.Z)
    q = P3(X, Y, Z)
    tp = [np.array(tr(*pt)) for pt in pts]
    d = None
    for a, b, r1, r2 in zip(tp[:-1], tp[1:], rads[:-1], rads[1:]):
        e = sd_roundcone(q, a, b, r1, r2)
        d = e if d is None else smin(d, e, 0.004)
    return d / flat ** 0.5


def build_hair_locks(skin):
    """Lock SDF ops (added onto the cap). skin: full body SDF for projection."""
    S = SDF()
    rng = np.random.default_rng(11)
    specs = []   # theta0, theta1, phi0, phi1, off0, off1, r0, flick, flat, k, npts

    # back: layered to the nape
    for th in np.linspace(128, 232, 10):
        j = rng.uniform(-1, 1)
        specs.append((th + 4 * j, th + 4 * j + rng.uniform(-10, 10), 16, 136 + 7 * j, 0.016, 0.012, 0.0160,
                      0.018 * max(0, j), 2.6, 0.010, 5))
    # project all chain points in one go
    thetas, phis, offs, meta = [], [], [], []
    for sp in specs:
        th0, th1, ph0, ph1, o0, o1, r0, fl, flat, k, npts = sp
        for i in range(npts):
            t = i / (npts - 1)
            thetas.append(math.radians(th0 + (th1 - th0) * t))
            phis.append(math.radians(ph0 + (ph1 - ph0) * t))
            offs.append(o0 + (o1 - o0) * t + fl * t ** 3)
    P_, D_ = scalp_points(skin, thetas, phis)
    P_ = P_ + np.array(offs)[:, None] * D_
    c = 0
    for sp in specs:
        th0, th1, ph0, ph1, o0, o1, r0, fl, flat, k, npts = sp
        pts = [P_[c + i] for i in range(npts)]
        c += npts
        prof = np.interp(np.linspace(0, 1, npts), [0, 0.5, 0.8, 1.0], [1.0, 0.95, 0.70, 0.12])
        rads = list(r0 * prof)
        mid = pts[npts // 2] - HAIR_C
        lo = np.min(pts, 0) - r0; hi = np.max(pts, 0) + r0
        S.add(lambda p, pts=pts, rads=rads, n=mid, flat=flat: sd_lock(p, pts, rads, n, flat), lo, hi, k)
    return S


def hair_offset(X, Y, Z):
    """Thickness of the hair mass over the scalp (X, Y rel. HAIR_C, Z rel. HEADC): fluffy, as in the refs."""
    th = np.arctan2(X, Y)
    front = np.clip(np.cos(th), 0, 1) ** 2
    back = np.clip(-np.cos(th), 0, 1)
    side = np.exp(-((Z - 0.030) / 0.060) ** 2)          # widest around the temples, as in the refs
    return 0.008 + 0.010 * np.clip(Z / 0.11, 0, 1) + (0.016 * side + 0.012 * back * side) * (1 - 0.70 * front)


class HairVolume:
    """SDF of the hair mass (skin offset by hair_offset, cut at the hairline) for strand placement."""
    def __init__(self, skin):
        self.skin = skin

    def eval_points(self, pts):
        X = pts[:, 0] - HAIR_C[0]; Y = pts[:, 1] - HAIR_C[1]; Z = pts[:, 2] - HEADC[2]
        # no hairline cut here: strands that run past the hairline (fringe, sides) lie just off the skin
        return self.skin.eval_points(pts) - np.maximum(hair_offset(X, Y, Z), 0.004)


def make_hair(skin):
    h = 0.0022 if FAST else 0.0011
    lo = HEADC + V(-0.13, -0.16, -0.14); hi = HEADC + V(0.13, 0.14, 0.18)
    t = time.time()
    Fs, glo, n = skin.grid_eval(lo, hi, h)
    xs = glo[0] + h * np.arange(n[0]); ys = glo[1] + h * np.arange(n[1]); zs = glo[2] + h * np.arange(n[2])
    X = xs[:, None, None] - HAIR_C[0]; Y = ys[None, :, None] - HAIR_C[1]; Z = zs[None, None, :] - HEADC[2]
    th = np.arctan2(X, Y)
    off = 0.55 * hair_offset(X, Y, Z) + 0.0015   # the cap sits under the strands (they ride on the full volume)
    # surface ripples: grooves between clumps
    rip = 0.0018 * np.sin(th * 26 + 3 * np.sin(Z * 40)) * np.clip((Z + 0.03) / 0.08, 0, 1)
    F = smax(Fs - off + rip, hairline_z(th) - Z, 0.012).astype(np.float32)
    # (the earlier SDF locks are no longer used: the ribbon strands carry the layered cut)
    Fvol = F.copy()
    F = smax(F, -(Fs - 0.0012), 0.002).astype(np.float32)
    F[0], F[-1], F[:, 0], F[:, -1], F[:, :, -1] = 0.5, 0.5, 0.5, 0.5, 0.5
    v, q = surface_nets(F, glo, h)
    ob = mesh_from('Hair', v, q)
    log('mesh Hair %d verts %.1fs' % (len(v), time.time() - t))
    smooth(ob, 0.5, 1)
    return ob, (Fvol, glo, h)


HAIR_TIP_Z = ([0, 25, 40, 55, 70, 90, 110, 130, 160, 180],          # strand tip height by azimuth (deg)
              [0.018, 0.014, 0.004, -0.018, -0.036, -0.046, -0.054, -0.070, -0.088, -0.094])


def make_hair_strands(skin):
    """Shaggy layered short cut: ~300 narrow tapered ribbons (single-sided, ridged; the hair material is
    double-sided) flowing from the crown over the hair mass, hanging straight below the widest point."""
    rng = np.random.default_rng(23)
    HV = HairVolume(skin)
    # tip polar angle for a target height, per azimuth: march down each meridian once
    th_tab = np.radians(np.arange(-180, 181, 5)); ph_tab = np.radians(np.arange(4, 176, 2))
    TT, PP = np.meshgrid(th_tab, ph_tab, indexing='ij')
    Ps, _ = scalp_points(HV, TT.ravel(), PP.ravel())
    Zs = (Ps[:, 2] - HEADC[2]).reshape(TT.shape)

    def tip_phi(th, z):
        i = int(np.argmin(np.abs(th_tab - th)))
        zz = Zs[i]
        k = np.argmax(zz < z) if np.any(zz < z) else len(zz) - 1
        return ph_tab[max(k, 1)]

    specs = []   # th0, th1, ph0, ph1, lift, width, flick
    def add(th, ph0, ztip, w, lift, flick, drift):
        ph1 = tip_phi(th + drift, ztip)
        if ph1 <= ph0 + math.radians(12):
            return
        specs.append((th, th + drift, ph0, ph1, lift, w, flick))
    zt = lambda th: np.interp(abs(math.degrees(th)), *HAIR_TIP_Z)
    for k in range(30):                                         # soft wispy fringe, parted near the centre
        th = math.radians(rng.uniform(-48, 48))
        part = math.copysign(math.radians(rng.uniform(6, 18)), th) * math.exp(-(math.degrees(th) / 25) ** 2)
        add(th, math.radians(rng.uniform(12, 32)), zt(th) + rng.uniform(-0.008, 0.016), rng.uniform(0.005, 0.013),
            rng.uniform(0.0, 0.002), rng.uniform(0.0, 0.004), math.radians(rng.uniform(-10, 10)) + 0.15 * th + part)
    for k in range(300):                                        # the layered mass
        th = math.radians(rng.uniform(-180, 180))
        layer = rng.random()
        ztip = zt(th) + (0.040 * rng.random() if layer < 0.40 else rng.uniform(-0.012, 0.010))
        add(th, math.radians(rng.uniform(13, 42)), ztip, rng.uniform(0.007, 0.014),
            0.001 + 0.005 * layer, rng.uniform(0.004, 0.018) * (1 + 0.5 * (abs(th) > 0.9)), math.radians(rng.uniform(-16, 16)))
    for k in range(60):                                         # loose fine wisps, flying out at the edges
        th = math.radians(rng.choice([-1, 1]) * rng.uniform(25, 180))
        add(th, math.radians(rng.uniform(25, 55)), zt(th) + rng.uniform(-0.018, 0.010), rng.uniform(0.003, 0.006),
            0.004, rng.uniform(0.010, 0.026), math.radians(rng.uniform(-18, 18)))
    npts = 7
    thetas, phis = [], []
    for th0, th1, ph0, ph1, lift, w, fl in specs:
        for i in range(npts):
            t = i / (npts - 1)
            thetas.append(th0 + (th1 - th0) * t)
            phis.append(ph0 + (ph1 - ph0) * t)
    P_, D_ = scalp_points(HV, thetas, phis)
    verts, faces = [], []
    for k, (th0, th1, ph0, ph1, lift, w, fl) in enumerate(specs):
        pts = P_[k * npts:(k + 1) * npts].copy(); nn = D_[k * npts:(k + 1) * npts]
        tt = np.linspace(0, 1, npts)
        pts += nn * (lift * tt ** 0.7 + fl * tt ** 3)[:, None]
        # below the widest point the hair hangs: never move back in toward the head axis
        rel = pts - HAIR_C
        r = np.hypot(rel[:, 0], rel[:, 1]); ang = np.arctan2(rel[:, 1], rel[:, 0])
        for i in range(1, npts):
            if r[i] < r[i - 1]:
                r[i] = max(r[i], r[i - 1] - 0.0045 * (1 - tt[i]))
        pts[:, 0] = HAIR_C[0] + r * np.cos(ang); pts[:, 1] = HAIR_C[1] + r * np.sin(ang)
        tg = np.gradient(pts, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
        bb = np.cross(tg, nn); bb /= np.maximum(np.linalg.norm(bb, axis=1), 1e-9)[:, None]
        nrm2 = np.cross(bb, tg)
        wid = w * np.clip(1 - tt ** 1.3, 0.05, 1) ** 0.9 * (0.75 + 0.25 * np.sin(np.pi * np.minimum(tt * 1.6, 1)))
        base = sum(len(v) for v in verts)
        Lf = pts - bb * (wid / 2)[:, None]
        M = pts + nrm2 * (0.14 * wid)[:, None]
        R = pts + bb * (wid / 2)[:, None]
        vs = np.stack([Lf, M, R], 1).reshape(-1, 3)
        verts.append(vs)
        for i in range(npts - 1):
            a0 = base + 3 * i; a1 = a0 + 3
            for q in ([a0, a0 + 1, a1 + 1, a1], [a0 + 1, a0 + 2, a1 + 2, a1 + 1]):
                fn = np.cross(vs[q[1] - base] - vs[q[0] - base], vs[q[3] - base] - vs[q[0] - base])
                faces.append(q if (fn @ nrm2[i]) > 0 else q[::-1])
    ob = mesh_from('HairStrands', np.vstack(verts), np.array(faces))
    log('hair strands: %d strands, %d tris' % (len(specs), ntris(ob)))
    return ob


# ----------------------------------------------------------------------------
# Ponytail (ひとつ結び・ストレート): scalp cap shell, fringe cards, loose strands, tapered tail + cord
# ----------------------------------------------------------------------------
TIE = V(0.0, -0.074, 1.502)                 # the tie at the back of the head, about ear height
TAIL_PTS = np.array([[0, -0.074, 1.502], [0, -0.090, 1.476], [0, -0.100, 1.442], [0, -0.1015, 1.402],
                     [0, -0.0975, 1.362], [0, -0.0965, 1.328], [0, -0.0990, 1.304]])   # short, gentle S
TAIL_LEN = 0.195
EAR_C = V(0.077, 0.038, 1.500)
HAIR_BONES = ['hair.001', 'hair.002', 'hair.003']
HAIRLINE = ([0, 30, 45, 58, 70, 82, 95, 115, 135, 160, 180],
            [0.066, 0.062, 0.046, 0.020, -0.004, -0.022, -0.030, -0.045, -0.062, -0.076, -0.084])


def hair_weight(co):
    """0..1: how much a skin point is covered by the pulled-back hair (soft at the hairline, ears excluded)."""
    th = np.degrees(np.abs(np.arctan2(co[:, 0], co[:, 1] - HAIR_C[1])))
    zr = co[:, 2] - HEADC[2]
    hl = np.interp(th, *HAIRLINE)
    w = sstep(hl, hl + 0.007, zr)
    e = ((co[:, 1] - EAR_C[1]) / 0.033) ** 2 + ((co[:, 2] - EAR_C[2] + 0.002) / 0.055) ** 2
    ear = (np.abs(co[:, 0]) > 0.0705) & (e < 1.0)
    w = np.where(ear, w * sstep(0.75, 1.0, e), w)
    w *= (co[:, 2] > 1.40) & (co[:, 1] < HEADC[1] + 0.13)
    return w


def cap_thickness(co, w):
    zr = co[:, 2] - HEADC[2]
    th = np.degrees(np.abs(np.arctan2(co[:, 0], co[:, 1] - HAIR_C[1])))
    depth = np.clip((zr - np.interp(th, *HAIRLINE)) / 0.045, 0, 1)
    t = 0.0012 + 0.0095 * sstep(0, 1, depth)
    t += 0.016 * np.exp(-np.sum((co - TIE) ** 2, 1) / 0.040 ** 2)        # gathered hair at the tie
    return t * np.minimum(w * 1.4, 1)


def make_cap(body):
    """Shell over the scalp: a copy of the dense head faces under the hair, offset along the normals."""
    me = body.data
    co = get_co(body)
    nn = np.empty(len(co) * 3, np.float32); me.vertices.foreach_get('normal', nn); nn = nn.reshape(-1, 3)
    w = hair_weight(co)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    lt = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', lt)
    ls = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', ls)
    fv = [lv[a:a + n] for a, n in zip(ls, lt)]
    keep = np.array([np.all(w[f] > 0.002) for f in fv])
    faces = [fv[i] for i in np.nonzero(keep)[0]]
    used = np.unique(np.concatenate(faces))
    remap = -np.ones(len(co), np.int64); remap[used] = np.arange(len(used))
    t = cap_thickness(co[used], w[used])
    P = co[used] + nn[used] * t[:, None]
    ob = mesh_from('HairCap', P, [list(remap[f]) for f in faces])
    smooth_boundary(ob, lambda c: np.ones(len(c), bool), iters=25, fac=0.5)
    smooth(ob, 0.5, 6)
    log('hair cap: %d faces from the head' % len(faces))
    return ob, (co, w, t, used)


def delete_under_cap(body, info, min_t=0.005):
    co, w, t, used = info
    tt = np.zeros(len(co)); tt[used] = t
    under = tt > min_t
    bm = bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if all(under[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(body.data); bm.free()
    log('deleted %d scalp faces under the cap' % len(dead))


def strip_mesh(rows, faces, verts):
    """Append a grid strip (list of rows of points) to verts/faces."""
    base = sum(len(v) for v in verts)
    R = np.array(rows); nr, nc = R.shape[:2]
    verts.append(R.reshape(-1, 3))
    for i in range(nr - 1):
        for j in range(nc - 1):
            a = base + i * nc + j
            faces.append([a, a + 1, a + nc + 1, a + nc])


def tube_mesh(path, rad, sides, faces, verts, ell=(1.0, 1.0), groove=0.0, up=V(0, 1, 0), cap_end=True):
    path = np.asarray(path, float)
    tg = np.gradient(path, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
    base = sum(len(v) for v in verts)
    vs = []
    for i, (p, d) in enumerate(zip(path, tg)):
        R = frame_from(d, up)
        for j in range(sides):
            a = 2 * math.pi * j / sides
            g = 1 - groove * (0.5 - 0.5 * math.cos(5 * a)) ** 2
            vs.append(p + rad[i] * g * (ell[0] * math.cos(a) * R[0] + ell[1] * math.sin(a) * R[1]))
    if cap_end:
        vs.append(path[-1] + tg[-1] * rad[-1] * 0.5)
    verts.append(np.array(vs))
    n = len(path)
    for i in range(n - 1):
        for j in range(sides):
            a = base + i * sides + j; b = base + i * sides + (j + 1) % sides
            faces.append([a, b, b + sides, a + sides])
    if cap_end:
        tip = base + n * sides
        for j in range(sides):
            faces.append([base + (n - 1) * sides + j, base + (n - 1) * sides + (j + 1) % sides, tip])


def surface_bvh(objs):
    from mathutils.bvhtree import BVHTree
    Vs, Fs, off = [], [], 0
    for ob in objs:
        co = get_co(ob)
        for p in ob.data.polygons:
            Fs.append([i + off for i in p.vertices])
        Vs.append(co); off += len(co)
    Vs = np.vstack(Vs)
    return BVHTree.FromPolygons([Vector(v) for v in Vs], Fs)


def drop_onto(bvh, pts, dvec, start_back=0.2):
    """Cast rays from pts - dvec*start_back along dvec; return hit points and normals (facing back)."""
    P, N = [], []
    d = Vector(dvec).normalized()
    for p in pts:
        o = Vector(p) - d * start_back
        hit = bvh.ray_cast(o, d, 1.0)
        if hit[0] is None:
            P.append(np.array(p)); N.append(-np.array(d))
        else:
            n = hit[1]
            if n.dot(d) > 0:
                n = -n
            P.append(np.array(hit[0])); N.append(np.array(n))
    return np.array(P), np.array(N)


FRINGE_PART = 0.005        # x of the slight centre part


def fringe_card(bvh, xr, zr0, xt, zt, w0, w1, layer, rng, dirs=V(0, -1, 0), nr=10, nc=5, fray=0.06):
    """One soft fringe card from the root (xr, zr0) to the tip (xt, zt) (head frame z), width w0 -> w1,
    lying on the cap/forehead, with a rounded, slightly frayed end (columns end at different lengths)."""
    us = np.linspace(-0.5, 0.5, nc)
    tend = 0.80 + 0.20 * np.sqrt(np.clip(1 - (2 * us) ** 2, 0, 1)) + rng.uniform(-fray, fray, nc) * (np.abs(us) < 0.45)
    tend = np.clip(tend, 0.7, 1.0)
    pts = []
    for i in range(nr):
        ti = i / (nr - 1)
        row = []
        for j, u in enumerate(us):
            t = ti * tend[j]
            x = xr + (xt - xr) * t ** 1.35
            z = HEADC[2] + zr0 + (zt - zr0) * t
            wid = w0 + (w1 - w0) * sstep(0.2, 1.0, t)
            row.append(V(x + u * wid, HEADC[1] + 0.05, z))
        pts.append(row)
    flat = np.array(pts).reshape(-1, 3)
    surf, nn = drop_onto(bvh, flat, dirs, 0.25)
    tt = np.repeat(np.linspace(0, 1, nr), nc)
    uu = np.tile(us, nr)
    edge = 1 - 4 * uu ** 2                 # lie flatter at the long edges (no visible plate edge)
    off = 0.0013 + 0.0014 * sstep(0.15, 0.55, tt) + 0.0010 * sstep(0.45, 0.8, tt) * edge - 0.0006 * tt ** 2 \
        + 0.0007 * layer * sstep(0.2, 0.6, tt) + 0.0004 * edge * sstep(0.1, 0.4, tt)
    off = np.where(tt < 0.12, off - 0.0025 * (1 - tt / 0.12), off)     # the root tucks under the cap edge
    surf = surf + nn * off[:, None]
    R = surf.reshape(nr, nc, 3)
    for _ in range(2):
        R[1:-1] = 0.25 * R[:-2] + 0.5 * R[1:-1] + 0.25 * R[2:]
    return R


def make_fringe(cap, body):
    """Airy see-through fringe (前髪): 14 wide overlapping cards springing from the hairline, following the
    forehead, with rounded/frayed ends at uneven heights between and just above the brows, a slight centre
    part with strands sweeping left/right, tips narrowing so the skin shows through; 2 side pieces per side."""
    rng = np.random.default_rng(37)
    bvh = surface_bvh([cap, body])
    verts, faces = [], []
    # (root x, tip x, tip z (head frame), width at root, width at tip, layer)
    specs = []
    roots = [-0.050, -0.040, -0.030, -0.021, -0.012, -0.004, 0.012, 0.020, 0.029, 0.038, 0.047, 0.055]
    for k, xr in enumerate(roots):
        side = min(abs(xr - FRINGE_PART) / 0.055, 1.0)
        sweep = math.copysign(1, xr - FRINGE_PART) * (0.008 + 0.010 * (1 - side)) + rng.uniform(-0.002, 0.002)
        zt = 0.019 - 0.008 * side ** 2 + rng.uniform(-0.004, 0.005)
        w0 = rng.uniform(0.020, 0.032); w1 = w0 * rng.uniform(0.40, 0.55)
        specs.append((xr, xr + sweep, zt, w0, w1, k % 2))
    for xr in (-0.034, 0.030):            # two longer centre-ish wisps reaching between the brows
        specs.append((xr, xr + math.copysign(0.004, xr), 0.010 + rng.uniform(-0.002, 0.002), 0.016, 0.006, 2))
    for k, (xr, xt, zt, w0, w1, layer) in enumerate(specs):
        zr0 = 0.078 - 0.010 * min(abs(xr) / 0.055, 1) ** 2
        R = fringe_card(bvh, xr, zr0, xt, zt, w0, w1, layer, rng)
        strip_mesh(R, faces, verts)
    for sgn in (-1, 1):                    # side pieces framing the face to the cheekbones
        for xr, zt, w in ((0.058, -0.018, 0.013), (0.064, -0.030, 0.010)):
            R = fringe_card(bvh, sgn * xr, 0.050, sgn * (xr + 0.004), zt + rng.uniform(-0.004, 0.004), w, w * 0.5,
                            1, rng, dirs=nrm(V(-sgn * 0.5, -1, 0)), nc=4)
            strip_mesh(R, faces, verts)
    ob = mesh_from('Fringe', np.vstack(verts), faces)
    log('fringe: %d cards, %d tris' % (len(specs) + 4, ntris(ob)))
    return ob


def project_out(bvh, pts):
    """Outermost surface point along the ray from far outside toward HAIR_C; returns points, normals."""
    P, N = [], []
    for p in pts:
        d = nrm(np.asarray(p) - HAIR_C)
        o = Vector(HAIR_C + d * 0.30)
        hit = bvh.ray_cast(o, Vector(-d), 0.35)
        if hit[0] is None:
            loc, nor, _, _ = bvh.find_nearest(Vector(p))
            n = np.array(nor)
            if n @ d < 0:
                n = -n
            P.append(np.array(loc)); N.append(n)
        else:
            n = np.array(hit[1])
            if n @ d < 0:
                n = -n
            P.append(np.array(hit[0])); N.append(n)
    return np.array(P), np.array(N)


def dir_at(th, zr):
    """Direction from HAIR_C to a scalp point at azimuth th (rad, 0 = front) and head-frame height zr."""
    z = HEADC[2] + zr - HAIR_C[2]
    return nrm(V(math.sin(th) * 0.075, math.cos(th) * 0.085, z))


def slerp_dirs(a, b, n):
    a = nrm(a); b = nrm(b)
    om = math.acos(np.clip(a @ b, -1, 1))
    if om < 1e-4:
        return np.tile(a, (n, 1))
    t = np.linspace(0, 1, n)[:, None]
    return (np.sin((1 - t) * om) * a + np.sin(t * om) * b) / math.sin(om)


def ribbon(P, N, w, verts, faces, uvs, ncol=2, ridge=0.0):
    """Ribbon along P (lying on normals N), width profile w (per row), ncol quads across."""
    tg = np.gradient(P, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1), 1e-9)[:, None]
    bb = np.cross(N, tg); bb /= np.maximum(np.linalg.norm(bb, axis=1), 1e-9)[:, None]
    us = np.linspace(-0.5, 0.5, ncol + 1)
    base = sum(len(v) for v in verts)
    rows = []
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    for i in range(len(P)):
        for u in us:
            rows.append(P[i] + bb[i] * u * w[i] + N[i] * ridge * w[i] * (0.25 - u * u))
    verts.append(np.array(rows))
    nc = ncol + 1
    for i in range(len(P) - 1):
        for j in range(ncol):
            a = base + i * nc + j
            faces.append([a, a + 1, a + nc + 1, a + nc])
            uvs.append([(us[j] * 0.01, arc[i]), (us[j + 1] * 0.01, arc[i]), (us[j + 1] * 0.01, arc[i + 1]),
                        (us[j] * 0.01, arc[i + 1])])


def make_cap_strands(cap, body):
    """Break the helmet: ~110 strand ribbons combed over the cap toward the tie (some gathered into bunches
    near it), 12 flyaway wisps, and ~50 fine short strands growing from the hairline over the skin."""
    rng = np.random.default_rng(41)
    bvh_cap = surface_bvh([cap])
    bvh_all = surface_bvh([cap, body])
    tie_dir = nrm(TIE + V(0, 0.010, 0) - HAIR_C)
    verts, faces, uvs = [], [], []
    hl = lambda th: np.interp(abs(math.degrees(th)), *HAIRLINE)
    nr = 8
    n_main = 0
    for k in range(76):
        th = math.radians(rng.uniform(-180, 180))
        if abs(math.degrees(th)) < 8 and rng.random() < 0.7:
            continue                                    # keep the part clear
        if k < 5 and not (40 < abs(math.degrees(th)) < 140):
            th = math.radians(math.copysign(rng.uniform(45, 135), math.degrees(th)))
        zr = hl(th) + rng.uniform(0.006, 0.030 if abs(math.degrees(th)) < 150 else 0.012)
        d0 = dir_at(th, zr)
        if abs(math.degrees(th)) < 50:                  # front strands start behind the fringe roots
            d0 = dir_at(th, max(zr, 0.090))
        endf = rng.uniform(0.72, 1.0)
        tgt = nrm(tie_dir + V(rng.uniform(-0.12, 0.12), rng.uniform(-0.05, 0.05), rng.uniform(-0.12, 0.10)))
        D = slerp_dirs(d0, tgt, nr)[: max(3, int(round(nr * endf)))]
        P, N = project_out(bvh_cap, HAIR_C + D * 0.12)
        t = np.linspace(0, 1, len(P))
        fly = k < 5
        lift = rng.uniform(0.0005, 0.0020) + (rng.uniform(0.0025, 0.0050) * np.sin(np.pi * t) ** 1.5 if fly else 0)
        near_tie = np.exp(-np.sum((P - TIE) ** 2, 1) / 0.03 ** 2)
        lift = lift + 0.0025 * near_tie * (k % 3 == 0)  # gathered bunches near the tie
        P = P + N * np.asarray(lift)[:, None]
        w = (rng.uniform(0.004, 0.006) if fly else rng.uniform(0.004, 0.009)) * (0.30 + 0.70 * np.sin(np.pi * np.clip(t * 0.9 + 0.08, 0, 1)) ** 0.6)
        if fly:
            w = w * np.clip(1 - t, 0.02, 1) ** 0.7     # tapered to a point
        ribbon(P, N, w, verts, faces, uvs, ncol=1 if fly else 2, ridge=0.25)
        n_main += 1
    # fine short strands from the hairline over the skin (denser at temples and nape)
    n_fine = 0
    for k in range(400):
        if n_fine >= 54:
            break
        a = rng.uniform(0, 180)
        dens = 0.25 + 0.75 * (0.55 * np.exp(-((a - 62) / 12) ** 2) + np.exp(-((a - 170) / 25) ** 2))
        if a < 42 or 74 < a < 132 or rng.random() > dens:     # not over / in front of the ears
            continue
        th = math.radians(a * rng.choice([-1, 1]))
        d0 = dir_at(th, hl(th) - rng.uniform(0.002, 0.006))
        L = rng.uniform(0.02, 0.04)
        tgt = nrm(tie_dir + V(0, 0, 0.9 if a < 100 else 0.4))   # temples: up and back onto the cap
        ang = min(L / 0.085, math.acos(np.clip(d0 @ tgt, -1, 1)))
        D = slerp_dirs(d0, tgt, 12)
        frac = ang / max(math.acos(np.clip(d0 @ tgt, -1, 1)), 1e-3)
        D = slerp_dirs(d0, D[min(11, max(2, int(round(11 * frac))))], 5)
        P, N = project_out(bvh_all, HAIR_C + D * 0.12)
        P = P + N * 0.0008
        t = np.linspace(0, 1, len(P))
        w = rng.uniform(0.0012, 0.0020) * (0.35 + 0.65 * np.sin(np.pi * np.clip(t * 0.85 + 0.1, 0, 1)))
        ribbon(P, N, w, verts, faces, uvs, ncol=1)
        n_fine += 1
    ob = mesh_from('CapStrands', np.vstack(verts), faces)
    uv = ob.data.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', np.array([c for f in uvs for c in f], np.float32).ravel())
    log('cap strands: %d combed + %d hairline, %d tris' % (n_main, n_fine, ntris(ob)))
    return ob


def make_loose_strands(S):
    """後れ毛: two thin tapered strands in front of each ear, three short ones at the nape."""
    verts, faces = [], []
    for s in (-1, 1):
        for k, (y0, zend, bend) in enumerate(((0.088, -0.078, 0.008), (0.074, -0.058, 0.010))):
            zs = np.linspace(HEADC[2] + 0.036, HEADC[2] + zend, 10)
            pts = []
            for i, z in enumerate(zs):
                t = i / (len(zs) - 1)
                pts.append(V(s * 0.20, y0 + bend * math.sin(math.pi * t) - 0.004 * t, z))
            pts = np.array(pts)
            o = pts.copy(); dvec = V(-s, 0, 0)
            lo_, hi_ = np.zeros(len(o)), np.full(len(o), 0.2)
            for _ in range(28):
                m = 0.5 * (lo_ + hi_)
                inside = S.eval_points(o + m[:, None] * dvec) < 0
                hi_ = np.where(inside, m, hi_); lo_ = np.where(inside, lo_, m)
            surf = o + lo_[:, None] * dvec
            tt = np.linspace(0, 1, len(zs))
            surf[:, 0] += s * (0.0040 + 0.007 * tt ** 1.4)
            surf[:, 1] += 0.004 * np.sin(np.pi * tt) * (1 if k % 2 else -1)
            rad = 0.0019 * (1 - 0.85 * tt ** 0.8)
            tube_mesh(surf, rad, 5, faces, verts, ell=(1.0, 0.55), up=V(s, 0, 0))
    for xk in (-0.030, 0.0, 0.032):
        z0 = HEADC[2] - 0.075; zs = np.linspace(z0, z0 - 0.035, 5)
        pts = np.array([V(xk, -0.03, z) for z in zs])
        o = pts.copy(); dvec = V(0, 1, 0)
        lo_, hi_ = np.zeros(len(o)), np.full(len(o), 0.2)
        o[:, 1] -= 0.15
        for _ in range(28):
            m = 0.5 * (lo_ + hi_)
            inside = S.eval_points(o + m[:, None] * dvec) < 0
            hi_ = np.where(inside, m, hi_); lo_ = np.where(inside, lo_, m)
        surf = o + lo_[:, None] * dvec
        tt = np.linspace(0, 1, len(zs))
        surf[:, 1] -= 0.003 + 0.004 * tt
        tube_mesh(surf, 0.0012 * (1 - 0.8 * tt), 4, faces, verts)
    ob = mesh_from('LooseHair', np.vstack(verts), faces)
    return ob


def tail_curve(n=28):
    seg = np.linalg.norm(np.diff(TAIL_PTS, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    tt = np.linspace(0, arc[-1], n)
    P = np.stack([np.interp(tt, arc, TAIL_PTS[:, a]) for a in range(3)], 1)
    return smooth_path(P, False, 3), tt


def make_tail():
    """The tail: an elongated, slightly flattened tube with shallow grooves, tapering to a soft tip;
    it starts inside the cap at the tie. Plus the leather cord (a small torus)."""
    verts, faces = [], []
    P, arc = tail_curve(22)
    P = np.vstack([P[:1] + V(0, 0.030, 0.006), P[:1] + V(0, 0.014, 0.003), P])   # root buried in the cap
    arc = np.concatenate([[-0.030, -0.014], arc])
    u = np.clip(arc / arc[-1], 0, 1)
    rad = 0.022 * (1 - 0.30 * u) * (1 + 0.32 * np.exp(-((arc - 0.030) / 0.026) ** 2))     # flare below the tie
    rad *= np.sqrt(np.clip(1 - (np.clip(u - 0.78, 0, None) / 0.22) ** 2, 0.02, 1))           # soft rounded tip
    rad = np.maximum(rad, 0.0025)
    rad[:2] = (0.012, 0.016)
    tube_mesh(P, rad, 18, faces, verts, ell=(0.60, 1.10), groove=0.14, up=V(1, 0, 0))
    tail = mesh_from('Tail', np.vstack(verts), faces)
    # cord
    Rb = Ribbons()
    d = nrm(P[3] - P[1])
    Rb.torus(TIE + d * 0.008, d, 0.0168, 0.0030, seg=12, sseg=5, part=0)
    Rb.torus(TIE + d * 0.015, d, 0.0170, 0.0026, seg=12, sseg=5, part=0)
    cord = Rb.obj('Cord')
    log('tail: %d tris, cord %d' % (ntris(tail), ntris(cord)))
    return tail, cord


def tail_weights(ob, head_blend=0.02):
    """Weights along the tail: smooth hat functions over hair.001..004 (bones 11 cm, straight down from the tie)."""
    co = get_co(ob) + ORIGIN
    W = np.zeros((len(co), len(BONE_ORDER)))
    d = np.clip(TIE[2] - co[:, 2], -0.05, 1.0)          # distance down from the tie (bones hang straight)
    nb_ = len(HAIR_BONES)
    L = TAIL_LEN / nb_
    for k, b in enumerate(HAIR_BONES):
        c = (k + 0.5) * L
        W[:, BONE_ORDER.index(b)] = np.clip(1 - np.abs(d - c) / L, 0, 1)
    W[d < 0.5 * L, BONE_ORDER.index(HAIR_BONES[0])] = 1.0
    W[d > (nb_ - 0.5) * L, BONE_ORDER.index(HAIR_BONES[-1])] = 1.0
    hb = sstep(head_blend, -0.01, d)
    W *= (1 - hb)[:, None]
    W[:, BONE_ORDER.index('head')] += hb
    return W


def delete_inside(ob, grid, thresh):
    """Delete faces whose vertices all lie inside the SDF grid volume by more than -thresh."""
    from scipy import ndimage
    F, glo, h = grid
    co = get_co(ob)
    idx = ((co - glo) / h).T
    val = ndimage.map_coordinates(F, idx, order=1, mode='constant', cval=1.0)
    inside = val < -thresh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    dead = [f for f in bm.faces if all(inside[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(ob.data); bm.free()
    log('deleted %d hidden faces from %s' % (len(dead), ob.name))


HAIR_HEIGHT = {}          # filled by the painters: per-texel streak height (for the hair normal map)


def hair_streaks(P):
    """Streak value 0..1 (fine strands combed toward the tie / along the tail / down the fringe)."""
    zr = P[:, 2] - HEADC[2]
    ax = nrm(TIE - HAIR_C)
    e1 = nrm(np.cross(ax, V(0, 0, 1))) if abs(ax[2]) < 0.9 else V(1, 0, 0)
    e2 = np.cross(ax, e1)
    q = P - HAIR_C
    a = np.arctan2(q @ e2, q @ e1)
    st = 0.5 + 0.5 * np.sin(a * 64 + 2.5 * np.sin(a * 11)) * (0.6 + 0.4 * np.sin(a * 23 + 1.3))
    tc, _ = tail_curve(60)
    k = np.argmin(np.abs(P[:, 2][:, None] - tc[None, :, 2]), axis=1)
    rel = P - tc[k]
    tail = (np.linalg.norm(rel[:, :2], axis=1) < 0.04) & (P[:, 2] < TIE[2] - 0.004) & (P[:, 1] < -0.04)
    at = np.arctan2(rel[:, 1], rel[:, 0])
    st = np.where(tail, 0.5 + 0.5 * np.sin(at * 34 + 1.5 * np.sin(P[:, 2] * 40)) * (0.6 + 0.4 * np.sin(at * 9 + 0.7)), st)
    front = (P[:, 1] > HEADC[1] + 0.06) | ((np.abs(P[:, 0]) > 0.06) & (zr < 0.02) & (P[:, 1] > 0.02))
    st = np.where(front, 0.5 + 0.5 * np.sin(P[:, 0] * 1300 + np.sin(P[:, 2] * 200)), st)
    return np.clip(st, 0, 1), tail, front, q, ax


def paint_hair(P, N, UV=None, lifted=0.0):
    st, tail, front, q, ax = hair_streaks(P)
    zr = P[:, 2] - HEADC[2]
    base = np.array([0.050, 0.038, 0.032])
    var = hash3(P, 180.0, 5.0)                                # strand-to-strand colour variation
    col = base[None] * (0.70 + 0.55 * st)[:, None]
    col = mixc(col, (0.15, 0.10, 0.075), np.clip(var - 0.55, 0, 1) * 1.6 * (0.4 + lifted))
    col = mixc(col, (0.20, 0.14, 0.11), np.clip(st - 0.70, 0, 1) * 1.6)
    # narrow, streaky sheen band on the crown
    el = (q @ ax) / np.maximum(np.linalg.norm(q, axis=1), 1e-6)
    band = np.exp(-((el + 0.12) / 0.08) ** 2) * (~tail) * (~front) * np.clip(N[:, 2] + 0.3, 0, 1)
    col = mixc(col, (0.32, 0.25, 0.20), band * sstep(0.45, 0.9, st) * 0.55)
    col = mixc(col, (0.24, 0.18, 0.14), tail * np.clip(N[:, 0] * 0.5 + N[:, 2] * 0.3 + 0.2, 0, 1) * sstep(0.4, 0.9, st) * 0.3)
    # centre/side part from the fringe back to the crown: thin dark groove with a hint of skin
    xp = P[:, 0] - FRINGE_PART
    on = (zr > 0.055) & (P[:, 1] > HAIR_C[1] - 0.035) & (~tail)
    g = np.exp(-(xp / 0.0011) ** 2) * on * sstep(HAIR_C[1] - 0.035, HAIR_C[1] - 0.005, P[:, 1])
    col = mixc(col, (0.020, 0.015, 0.013), np.exp(-(xp / 0.0026) ** 2) * on * 0.6)
    col = mixc(col, (0.42, 0.30, 0.24), g * 0.55)
    q2 = P - HAIR_C
    a2 = np.arctan2(q2 @ np.cross(ax, nrm(np.cross(ax, V(0, 0, 1)))), q2 @ nrm(np.cross(ax, V(0, 0, 1))))
    jit = hash3(P, 60.0, 11.0)
    fine = np.sin(a2 * (90 + 30 * jit) + 3.0 * np.sin(a2 * 7 + el * 9) + 2.0 * np.sin(el * 23 + a2 * 3)) \
        * (0.5 + 0.5 * hash3(P, 140.0, 2.0))
    fine = np.where(tail | front, np.sin(st * 6.0 + jit * 4) * (0.5 + 0.5 * hash3(P, 140.0, 2.0)), fine)
    HAIR_HEIGHT['last'] = 0.5 * fine * (1 - 0.85 * band) - 0.8 * np.exp(-(xp / 0.0022) ** 2) * on
    return np.clip(col, 0, 1)


def paint_strand(P, N, UV=None):
    col = paint_hair(P, N, UV, lifted=1.0)
    # hairline fuzz: blend to the skin at the root (reads as fine, slightly translucent baby hair)
    th = np.degrees(np.abs(np.arctan2(P[:, 0], P[:, 1] - HAIR_C[1])))
    dz = P[:, 2] - HEADC[2] - np.interp(th, *HAIRLINE)
    skin = paint_skin(P, N)
    return np.clip(mixc(col, skin, sstep(0.012, -0.002, dz) * 0.80), 0, 1)


# ----------------------------------------------------------------------------
# Clothes: offset surfaces of the body SDF, cut to a region (open sheets)
# ----------------------------------------------------------------------------
def jag(x, period, amp, seed=0):
    """Ragged edge: saw teeth with random-ish amplitude."""
    t = x / period
    f = t - np.floor(t)
    tooth = np.abs(f - 0.5) * 2.0
    var = 0.6 + 0.4 * np.sin(np.floor(t) * 12.9898 + seed) ** 2
    return amp * tooth * var


def build_top_sdf(body):
    T = body.extend()
    T.ellipsoid(V(0, 0.062, 1.170), (0.105, 0.045, 0.052), k=0.05)      # bridge the cleavage
    T.shift(0.0045)
    return T


def top_keep(c):
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    th = np.arctan2(x, y + 0.005)
    ax = np.abs(x)
    hem = 1.104 + 0.004 * np.sin(th * 3 + 0.5) + jag(th, 0.21, 0.016, 1.0)
    neck_front = 1.252 - 0.034 * np.exp(-(x / 0.048) ** 2)
    top_b = np.where(y > 0, neck_front, 1.272 - 0.012 * np.exp(-(x / 0.05) ** 2))
    torso = (z > hem) & (z < top_b) & ~((z > 1.212) & (ax > 0.116)) & (ax < 0.150)
    strap = (np.abs(ax - 0.094) < 0.020 - 0.004 * np.clip((z - 1.30) / 0.05, 0, 1)) & (z >= top_b - 0.01) & (ax < 0.13)
    return torso | strap


def build_skirt_sdf(body):
    T = body.extend()
    T.shift(0.0065)
    T.add(lambda p: sd_loft(p, [(0.655, 0.212, 0.146, -0.016), (0.70, 0.200, 0.138, -0.016),
                                (0.75, 0.186, 0.128, -0.016), (0.80, 0.168, 0.114, -0.016),
                                (0.85, 0.140, 0.094, -0.014), (0.89, 0.090, 0.060, -0.012)]),
          V(-0.24, -0.2, 0.64), V(0.24, 0.2, 0.90), 0.025)
    # knot + tails on the left hip
    kp = V(-0.112, 0.062, 0.905)
    T.ellipsoid(kp, (0.016, 0.012, 0.014), k=0.008)
    for dx, L in ((-0.012, 0.11), (0.010, 0.085)):
        a = kp + V(dx * 0.5, 0.004, -0.008)
        b = kp + V(dx, 0.010, -L)
        T.add(lambda p, a=a, b=b: sd_lock(p, [a, 0.5 * (a + b) + V(0, 0.004, 0), b], [0.010, 0.009, 0.004],
                                          V(-0.6, 0.8, 0), 2.2), np.minimum(a, b) - 0.02, np.maximum(a, b) + 0.02, 0.006)
    return T


def skirt_keep(c):
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    th = np.arctan2(x, y + 0.016)
    waist = 0.934 - 0.014 * np.clip(np.cos(th), 0, 1)
    hem = 0.712 + 0.022 * np.cos(th - 0.5) + 0.012 * np.cos(2 * th) + jag(th, 0.17, 0.030, 2.0)
    return (z > hem) & (z < waist) & (np.abs(x) < 0.26)


def shorts_keep(c):
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    zo = 0.742 + 0.050 * np.clip(np.abs(x) / 0.17, 0, 1)
    return (z > zo) & (z < 0.925) & (np.abs(x) < 0.2)


def smooth_boundary(ob, where, iters=12, fac=0.5):
    """1D Laplacian along open boundary loops (vertices where where(co) is true)."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bv = [v for v in bm.verts if v.is_boundary]
    nb = {v.index: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bv}
    co = np.array([v.co[:] for v in bm.verts])
    sel = [v for v in bv if where(np.array(v.co[:])[None])[0] and len(nb[v.index]) == 2]
    for _ in range(iters):
        new = {}
        for v in sel:
            a, b = nb[v.index]
            new[v.index] = (1 - fac) * co[v.index] + fac * 0.5 * (co[a.index] + co[b.index])
        for i, c in new.items():
            co[i] = c
    for v in sel:
        v.co = co[v.index]
    bm.to_mesh(ob.data); bm.free()


def make_clothes(body):
    hc = 0.0032 if FAST else 0.0016
    top = sdf_mesh('Top', build_top_sdf(body), V(-0.20, -0.15, 1.06), V(0.20, 0.17, 1.42), hc, keep=top_keep)
    smooth_boundary(top, lambda c: c[:, 2] > 1.17)
    sk = build_skirt_sdf(body)
    skirt = sdf_mesh('Wrap', sk, V(-0.26, -0.20, 0.63), V(0.26, 0.20, 0.97), hc, keep=skirt_keep)
    smooth_boundary(skirt, lambda c: c[:, 2] > 0.86)
    sh = body.extend(); sh.shift(0.0028)
    shorts = sdf_mesh('Shorts', sh, V(-0.22, -0.18, 0.70), V(0.22, 0.16, 0.95), hc, keep=shorts_keep)
    smooth_boundary(shorts, lambda c: c[:, 2] > 0)
    return top, skirt, shorts, sk


# ----------------------------------------------------------------------------
# Ribbons (straps) projected onto a surface
# ----------------------------------------------------------------------------
def project(S, pts, off=0.0, iters=6):
    pts = np.array(pts, float)
    e = 0.0004
    for _ in range(iters):
        f = S.eval_points(pts)
        g = np.stack([(S.eval_points(pts + V(*(e * np.eye(3)[a]))) - f) / e for a in range(3)], 1)
        gn = g / np.maximum(np.linalg.norm(g, axis=1), 1e-9)[:, None]
        pts = pts - (f - off)[:, None] * gn
    f = S.eval_points(pts)
    g = np.stack([(S.eval_points(pts + V(*(e * np.eye(3)[a]))) - f) / e for a in range(3)], 1)
    return pts, g / np.maximum(np.linalg.norm(g, axis=1), 1e-9)[:, None]


def resample(pts, step, closed=False):
    pts = np.array(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(2, int(math.ceil(L[-1] / step)) + 1)
    t = np.linspace(0, L[-1], n)
    out = np.stack([np.interp(t, L, pts[:, a]) for a in range(3)], 1)
    if closed:
        out = out[:-1]
    return out


def smooth_path(pts, closed, it=3):
    p = np.array(pts, float)
    for _ in range(it):
        if closed:
            p = 0.25 * np.roll(p, 1, 0) + 0.5 * p + 0.25 * np.roll(p, -1, 0)
        else:
            q = p.copy(); q[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]; p = q
    return p


class Ribbons:
    """Flat straps, tubes and tori with their own strip UVs (metres; packed later)."""
    def __init__(self):
        self.V = []; self.F = []; self.part = []; self.UV = []

    def _base(self):
        return sum(len(v) for v in self.V)

    def strap(self, S, ctrl, width, off, closed=False, step=0.02, thick=0.0025, part=0):
        pts = resample(smooth_path(resample(ctrl, step * 0.5, closed), closed, 4), step, closed)
        pts, n = project(S, pts, off)
        pts = smooth_path(pts, closed, 2)
        pts, n = project(S, pts, off)
        if closed:   # duplicate the first point: the strip stays open in UV space
            t = np.roll(pts, -1, 0) - np.roll(pts, 1, 0)
            pts = np.vstack([pts, pts[:1]]); n = np.vstack([n, n[:1]]); t = np.vstack([t, t[:1]])
        else:
            t = np.gradient(pts, axis=0)
        t /= np.linalg.norm(t, axis=1)[:, None]
        b = np.cross(n, t); b /= np.linalg.norm(b, axis=1)[:, None]
        hw = width / 2
        m = len(pts)
        base = self._base()
        lift = n * (thick * 0.7)
        verts = np.empty((m * 2, 3))
        verts[0::2] = pts + b * hw + lift
        verts[1::2] = pts - b * hw + lift
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
        for i in range(m - 1):
            q = [base + 2 * i, base + 2 * i + 1, base + 2 * i + 3, base + 2 * i + 2]
            self.F.append(q); self.part.append(part)
            self.UV.append([(arc[i], width), (arc[i], 0), (arc[i + 1], 0), (arc[i + 1], width)])
        self.V.append(verts)

    def tube(self, a, b, r, seg=8, part=0):
        a = np.asarray(a, float); b = np.asarray(b, float)
        d = nrm(b - a); R = frame_from(d, V(0, 0, 1) if abs(d[2]) < 0.9 else V(1, 0, 0))
        L = np.linalg.norm(b - a)
        base = self._base()
        verts = []
        for e in (a, b):
            for i in range(seg + 1):
                ang = 2 * math.pi * i / seg
                verts.append(e + r * (math.cos(ang) * R[0] + math.sin(ang) * R[1]))
        c = 2 * math.pi * r
        for i in range(seg):
            self.F.append([base + i, base + i + 1, base + seg + 1 + i + 1, base + seg + 1 + i]); self.part.append(part)
            self.UV.append([(c * i / seg, 0), (c * (i + 1) / seg, 0), (c * (i + 1) / seg, L), (c * i / seg, L)])
        self.V.append(np.array(verts))

    def torus(self, c, axis, R, r, seg=10, sseg=5, part=0):
        Rm = frame_from(axis, V(0, 0, 1) if abs(nrm(axis)[2]) < 0.9 else V(1, 0, 0))
        base = self._base()
        verts = []
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            cdir = math.cos(a) * Rm[0] + math.sin(a) * Rm[1]
            for j in range(sseg + 1):
                bb = 2 * math.pi * j / sseg
                verts.append(c + R * cdir + r * (math.cos(bb) * cdir + math.sin(bb) * Rm[2]))
        L1 = 2 * math.pi * R; L2 = 2 * math.pi * r
        k = sseg + 1
        for i in range(seg):
            for j in range(sseg):
                self.F.append([base + i * k + j, base + (i + 1) * k + j, base + (i + 1) * k + j + 1, base + i * k + j + 1])
                self.part.append(part)
                self.UV.append([(L1 * i / seg, L2 * j / sseg), (L1 * (i + 1) / seg, L2 * j / sseg),
                                (L1 * (i + 1) / seg, L2 * (j + 1) / sseg), (L1 * i / seg, L2 * (j + 1) / sseg)])
        self.V.append(np.array(verts))

    def obj(self, name):
        ob = mesh_from(name, np.vstack(self.V), self.F)
        uv = ob.data.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.array([c for f in self.UV for c in f], np.float32).ravel())
        return ob


def ring_around(c, axis, rx, ry, n=24, up=V(0, 1, 0)):
    R = frame_from(axis, up)
    return [c + rx * math.cos(2 * math.pi * i / n) * R[0] + ry * math.sin(2 * math.pi * i / n) * R[1] for i in range(n)]


def make_leather(body, top_sdf, skirt_sdf):
    """Harness, belt, wrist cuffs, sandal straps, rods (+ part ids: 0 leather, 1 wood, 2 metal)."""
    Rb = Ribbons()
    harness = SDF(); harness.ops = list(top_sdf.ops)
    for s in (-1, 1):
        # shoulder strap: under-bust front, over the shoulder, down the back
        ctrl = [V(s * 0.082, 0.10, 1.128), V(s * 0.088, 0.11, 1.20), V(s * 0.094, 0.07, 1.30),
                V(s * 0.100, 0.0, 1.372), V(s * 0.096, -0.07, 1.31), V(s * 0.086, -0.10, 1.20), V(s * 0.080, -0.10, 1.128)]
        Rb.strap(harness, ctrl, 0.017, 0.0030)
    # under-bust ring and chest strap
    Rb.strap(harness, ring_around(V(0, 0.0, 1.128), V(0, 0, 1), 0.16, 0.13, 28), 0.020, 0.0030, closed=True)
    Rb.strap(harness, [V(-0.094, 0.10, 1.262), V(0, 0.115, 1.250), V(0.094, 0.10, 1.262)], 0.015, 0.0030)
    Rb.strap(harness, [V(-0.090, -0.10, 1.250), V(0, -0.11, 1.245), V(0.090, -0.10, 1.250)], 0.015, 0.0030)
    # belt on the wrap
    belt = [V(0.25 * math.sin(a), 0.2 * math.cos(a) - 0.016, 0.898 + 0.022 * (1 - math.cos(a)) * 0.5)
            for a in np.linspace(0, 2 * math.pi, 32, endpoint=False)]
    Rb.strap(skirt_sdf, belt, 0.022, 0.0025, closed=True)
    for s in (-1, 1):
        # wrist cuffs and forearm strap holding the rod
        d = SK.arm_dir(s); wr = SK.wrist(s); el = SK.elbow(s); n = SK.palm_n(s)
        for t, w in ((-0.012, 0.030), (0.45, 0.016), (0.80, 0.014)):
            c = wr - t * (wr - el) if t > 0 else wr + 0.012 * d
            Rb.strap(body, ring_around(c, d, 0.05, 0.05, 16, n), w, 0.0012, closed=True)
        # rod (wood) on the back of the forearm, from the hand to past the elbow
        a = wr + 0.075 * d - 0.030 * n; b = el - 0.030 * d - 0.036 * n
        Rb.tube(a, b, 0.0065, 8, part=1)
        # sandal straps
        an = SK.ankle(s); toe = SK.toe(s)
        fwd = nrm(V(toe[0] - an[0], toe[1] - an[1], 0)); lat = nrm(np.cross(fwd, V(0, 0, 1)))
        if lat[0] * s < 0:
            lat = -lat
        sh_ax = nrm(SK.knee(s) - an)
        for z, w in ((0.115, 0.014), (0.155, 0.013), (0.198, 0.012)):
            c = an + sh_ax * ((z - an[2]) / sh_ax[2])
            Rb.strap(body, ring_around(c, sh_ax, 0.06, 0.06, 16), w, 0.0010, closed=True)
        ball = an + 0.150 * fwd
        mid = an + 0.075 * fwd
        for pth in ([V(*(ball - 0.045 * lat)) * V(1, 1, 0) + V(0, 0, 0.012), ball + V(0, 0, 0.05), V(*(ball + 0.045 * lat)) * V(1, 1, 0) + V(0, 0, 0.012)],
                    [mid - 0.045 * lat + V(0, 0, -mid[2] + 0.012), mid + 0.02 * fwd + V(0, 0, 0.06 - mid[2]), an + 0.04 * lat + V(0, 0, 0.0)],
                    [mid + 0.045 * lat + V(0, 0, -mid[2] + 0.012), mid + 0.02 * fwd + V(0, 0, 0.06 - mid[2]), an - 0.04 * lat + V(0, 0, 0.0)],
                    [an - 0.04 * fwd + V(0, 0, -an[2] + 0.014), an - 0.04 * fwd + V(0, 0, 0.04 - an[2] + 0.06)]):
            Rb.strap(body, pth, 0.012, 0.0010)
        # toe loop
        Rb.strap(body, ring_around(ball + 0.04 * fwd - 0.024 * lat + V(0, 0, -ball[2] + 0.018), fwd, 0.02, 0.02, 12), 0.007, 0.0008, closed=True)
        # wing loop ring on the outside of the ankle strap
        c = an + V(s * 0.040, -0.006, 0.037)
        Rb.torus(c, V(0, 1, 0.15), 0.009, 0.0022, part=2)
    ob = Rb.obj('Leather')
    ob['part'] = 0
    pa = ob.data.attributes.new('part', 'INT', 'FACE')
    pa.data.foreach_set('value', np.array(Rb.part, np.int32))
    return ob


def make_soles():
    S = SDF()
    for s in (-1, 1):
        an = SK.ankle(s); toe = SK.toe(s)
        fwd = nrm(V(toe[0] - an[0], toe[1] - an[1], 0))
        heel = an - 0.030 * fwd; heel[2] = 0.0065
        ball = an + 0.150 * fwd; ball[2] = 0.0065
        tip = an + 0.205 * fwd; tip[2] = 0.0065
        def f(p, heel=heel, ball=ball, tip=tip):
            q = P3(p.X, p.Y, p.Z * 0 + 0.0065)
            d = smin(sd_roundcone(q, heel, ball, 0.036, 0.046), sd_roundcone(q, ball, tip, 0.046, 0.030), 0.02)
            return np.maximum(d, np.abs(p.Z - 0.0065) - 0.0065)
        S.add(f, np.minimum(heel, tip) - 0.06, np.maximum(heel, tip) + 0.06, 0.0)
    ob = sdf_mesh('Soles', S, V(-0.25, -0.12, -0.004), V(0.25, 0.30, 0.02), 0.0015 if not FAST else 0.003)
    return ob


# ----------------------------------------------------------------------------
# Cape: quad grid between the top edge (rods, arms, shoulder rings, nape) and the ankle loops
# ----------------------------------------------------------------------------
WING_NU, WING_NV = 30, 12   # per wing: columns along the body seam, rows out to the free edge
WING_REST = {}              # per side: rest seam ends etc. (shifted frame) for the cape.* free-edge bones


def ankle_loop(s):
    an = SK.ankle(s); toe = SK.toe(s)
    fwd = nrm(V(toe[0] - an[0], toe[1] - an[1], 0)); lat = nrm(np.cross(fwd, V(0, 0, 1)))
    if lat[0] * s < 0:
        lat = -lat
    sh_ax = nrm(SK.knee(s) - an)
    return an + sh_ax * ((0.125 - an[2]) / sh_ax[2]) - V(0, 0.032, 0) + 0.012 * lat


def wing_seam_keys(s):
    """Seam of one wing (wrist -> underside of the arm -> armpit -> side of the torso -> outer leg -> ankle)
    with the bones that carry it."""
    sx = '.L' if s < 0 else '.R'
    d = SK.arm_dir(s); wr = SK.wrist(s); el = SK.elbow(s); n = SK.palm_n(s); sh = SK.shoulder(s)
    hp, kn, an = SK.hip(s), SK.knee(s), SK.ankle(s)
    fo, up, th, sn = 'forearm' + sx, 'upperarm' + sx, 'thigh' + sx, 'shin' + sx
    return [
        (wr + 0.010 * d + 0.020 * n, {fo: 1.0}),
        (wr + 0.45 * (el - wr) + 0.030 * n, {fo: 1.0}),
        (el + 0.033 * n, {fo: 0.5, up: 0.5}),
        (el + 0.5 * (sh - el) + 0.040 * n, {up: 1.0}),
        (sh + 0.060 * d + 0.046 * n, {up: 0.45, 'chest': 0.55}),
        (V(s * 0.140, -0.012, 1.165), {'chest': 1.0}),
        (V(s * 0.121, -0.008, 1.030), {'spine': 0.7, 'chest': 0.3}),
        (V(s * 0.160, -0.016, 0.900), {'hips': 1.0}),
        (V(s * 0.172, -0.010, 0.800), {'hips': 0.5, th: 0.5}),
        (hp + 0.5 * (kn - hp) + V(s * 0.070, 0, 0), {th: 1.0}),
        (kn + V(s * 0.048, 0, 0), {th: 0.5, sn: 0.5}),
        (kn + 0.5 * (an - kn) + V(s * 0.042, -0.008, 0), {sn: 1.0}),
        (an + V(s * 0.034, -0.006, 0.040), {sn: 1.0}),
    ]


def wing_build(S, top_sdf, skirt_sdf):
    """Two bat-wing membranes (one per side), each between the seam and a free edge wrist -> ankle.
    Returns the mesh and the rest-pose layout used to fit the skin weights."""
    rng = np.random.default_rng(5)
    verts, faces, uvs, info = [], [], [], []
    nb = len(BONE_ORDER)
    for s in (-1, 1):
        keys = wing_seam_keys(s)
        kp = np.array([k[0] for k in keys])
        kw = np.array([[k[1].get(b, 0.0) for b in BONE_ORDER] for k in keys])
        # dense seam, smoothed, projected on the outermost surface (skin, top, wrap)
        arcd = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(kp, axis=0), axis=1))])
        tt = np.linspace(0, arcd[-1], 160)
        dense = np.stack([np.interp(tt, arcd, kp[:, a]) for a in range(3)], 1)
        dense = smooth_path(dense, False, 6)
        dense, _ = project(S, dense, 0.003)
        z = dense[:, 2]; ax = np.abs(dense[:, 0])
        mt = (z > 1.10) & (z < 1.21) & (ax < 0.15)
        if mt.any():
            dense[mt], _ = project(top_sdf, dense[mt], 0.002)
        ms = (z > 0.735) & (z < 0.935)
        if ms.any():
            dense[ms], _ = project(skirt_sdf, dense[ms], 0.002)
        dense = smooth_path(dense, False, 3)
        dw = np.stack([np.interp(tt, arcd, kw[:, j]) for j in range(nb)], 1)
        al = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]); al /= al[-1]
        U = np.linspace(0, 1, WING_NU + 1)
        A = np.stack([np.interp(U, al, dense[:, a]) for a in range(3)], 1)
        Aw = np.stack([np.interp(U, al, dw[:, j]) for j in range(nb)], 1)
        # free edge: wrist -> ankle, concave (bat-wing scallops) and ragged
        t = 0.03 + 0.94 * U
        Lr = A[0][None] + t[:, None] * (A[-1] - A[0])[None]
        ld = nrm(A[-1] - A[0])
        k = A - Lr; k -= (k @ ld)[:, None] * ld[None]
        k[0] = k[1]; k[-1] = k[-2]
        kh = k / np.maximum(np.linalg.norm(k, axis=1), 1e-9)[:, None]
        c = 0.055 * np.sin(np.pi * t) + 0.022 * (1 - np.cos(2 * np.pi * 4 * t)) / 2
        teeth = np.array([(0.25 + 0.75 * rng.random()) * (0.014 if j % 2 else 0.003) for j in range(len(U))])
        teeth[[0, -1]] = 0
        c = c + teeth
        F = Lr + c[:, None] * kh
        Vv = np.linspace(0, 1, WING_NV + 1)
        P = A[None] * (1 - Vv)[:, None, None] + F[None] * Vv[:, None, None]
        base = sum(len(v) for v in verts)
        nu = WING_NU + 1
        for i in range(WING_NV):
            for j in range(WING_NU):
                q0 = base + i * nu + j
                q = [q0, q0 + nu, q0 + nu + 1, q0 + 1]
                faces.append(q if s < 0 else q[::-1])
        ii, jj = np.meshgrid(np.arange(WING_NV + 1), np.arange(WING_NU + 1), indexing='ij')
        uu = U[jj.ravel()]; vv = Vv[ii.ravel()]
        Ux = np.where(s < 0, 0.003 + 0.494 * uu, 0.997 - 0.494 * uu)
        uvs.append(np.stack([Ux, 1 - vv], 1))
        verts.append(P.reshape(-1, 3))
        info.append(dict(s=s, A=A, Aw=Aw, F=F, c=c, t=t, U=U, Vv=Vv, base=base,
                         i=ii.ravel(), j=jj.ravel()))
        jm = WING_NU // 2
        A0, A1, Am = A[0] - ORIGIN, A[-1] - ORIGIN, A[jm] - ORIGIN
        dd = nrm(A1 - A0); km = Am - A0; km -= (km @ dd) * dd
        WING_REST[s] = dict(A0=A0, A1=A1, Am=Am, L=float(np.linalg.norm(A1 - A0)), d=dd, k=nrm(km),
                            Amw={b: float(Aw[jm, j]) for j, b in enumerate(BONE_ORDER) if Aw[jm, j] > 0},
                            fo='forearm' + ('.L' if s < 0 else '.R'), sn='shin' + ('.L' if s < 0 else '.R'))
    verts = np.vstack(verts)
    ob = mesh_from('Cape', verts, np.array(faces))
    uv = ob.data.uv_layers.new(name='UVMap')
    lv = np.empty(len(ob.data.loops), np.int32); ob.data.loops.foreach_get('vertex_index', lv)
    uv.data.foreach_set('uv', np.vstack(uvs)[lv].astype(np.float32).ravel())
    return ob, info


def pose_skin_mats(rig, fn, t):
    """Skinning matrices (posed @ rest^-1, armature space) of every bone for pose fn(t)."""
    R = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    pose = fn(t)
    out, P = solve(rig, pose)
    if pose.get('ground'):
        sb = pose['ground']
        ank = P[sb] @ Vector((0, rig.data.bones[sb].length, 0))
        rest_ank = R[sb] @ Vector((0, rig.data.bones[sb].length, 0))
        pose['root_loc'] = (0, 0, rest_ank.z - ank.z)
        out, P = solve(rig, pose)
    return np.array([np.array(P[b] @ R[b].inverted()) for b in BONE_ORDER])


def lbs(K, W, X):
    """Linear blend skinning of points X (n,3) with weights W (n,nb) and matrices K (nb,4,4)."""
    Xh = np.hstack([X, np.ones((len(X), 1))])
    Y = np.einsum('bij,nj->nbi', K[:, :3, :], Xh)
    return (W[:, :, None] * Y).sum(1)


def fit_wing_weights(rig, info):
    """Skin weights for the wings, fitted so that the membrane is taut in the plane of arm and leg in
    `fly` and hangs as slack cloth behind/beside her in `stand` and `sit`. The seam row keeps the
    weights of the bones it is sewn to; the rest is a small non-negative least-squares fit per vertex,
    regularised toward a smooth arm -> body -> leg blend."""
    from scipy.optimize import nnls
    poses = [(pose_fly, f / 30.0, 1.0, 'fly') for f in (0, 15, 30, 45)] + \
            [(pose_stand, 1.5, 0.6, 'stand'), (pose_sit, 1.5, 0.6, 'sit')]
    Ks = [(pose_skin_mats(rig, fn, t), a, kind) for fn, t, a, kind in poses]
    nb = len(BONE_ORDER)
    Wout = []
    lam, beta = 3e-4, 3.0
    roof_z = SEAT_Z - ORIGIN[2]; roof_y = 0.055 - ORIGIN[1]
    for w in info:
        s = w['s']; sx = '.L' if s < 0 else '.R'
        A, Aw, F, c, t, U, Vv = (w[k] - (ORIGIN if k in ('A', 'F') else 0) for k in ('A', 'Aw', 'F', 'c', 't', 'U', 'Vv'))
        P = (A[None] * (1 - Vv)[:, None, None] + F[None] * Vv[:, None, None]).reshape(-1, 3)
        ii, jj = w['i'], w['j']
        L0 = np.linalg.norm(F - A, axis=1)
        Fw = np.zeros((len(U), nb))
        Fw[:, BONE_ORDER.index('cape' + sx)] = 1.0
        W0 = Aw[jj] * (1 - Vv[ii])[:, None] + Fw[jj] * Vv[ii][:, None]
        targets = []
        for K, a, kind in Ks:
            Ap = lbs(K, Aw, A)
            ci = BONE_ORDER.index('cape' + sx)
            Fp = (K[ci, :3, :3] @ F.T).T + K[ci, :3, 3]
            T = Ap[jj] * (1 - Vv[ii])[:, None] + Fp[jj] * Vv[ii][:, None]
            sv = np.sin(np.pi * Vv[ii])
            if kind == 'fly':
                T[:, 2] += 0.010 * sv * np.sin(np.pi * U[jj])          # slight upward camber, never sagging
            else:
                Lc = np.linalg.norm(Fp - Ap, axis=1)
                h = 0.5 * np.sqrt(np.maximum(L0 ** 2 - Lc ** 2, 0))
                D = nrm(V(s * 0.35, -1, -0.1)) if kind == 'stand' else nrm(V(s * 0.5, -0.8, -0.35))
                T += (0.9 * h[jj] * sv)[:, None] * D[None]
                if kind == 'sit':
                    m = (T[:, 1] < roof_y) & (T[:, 2] < roof_z + 0.006)
                    T[m, 2] = roof_z + 0.006
            targets.append((K, a, T))
        cand = [BONE_ORDER.index(b + sx) for b in ('forearm', 'upperarm', 'shoulder', 'thigh', 'shin', 'cape')] + \
               [BONE_ORDER.index(b) for b in ('chest', 'spine', 'hips')]
        Ph = np.hstack([P, np.ones((len(P), 1))])
        Wv = np.zeros((len(P), nb))
        err = {kind: 0.0 for _, _, kind in Ks}
        for vi in range(len(P)):
            if Vv[ii[vi]] == 0:
                Wv[vi] = W0[vi]
                continue
            rows, rhs = [], []
            for K, a, T in targets:
                Y = (K[cand, :3, :] @ Ph[vi]).T          # 3 x nc
                rows.append(a * Y); rhs.append(a * T[vi])
            rows.append(math.sqrt(lam) * np.eye(len(cand))); rhs.append(math.sqrt(lam) * W0[vi, cand])
            rows.append(beta * np.ones((1, len(cand)))); rhs.append(np.array([beta]))
            x, _ = nnls(np.vstack(rows), np.concatenate(rhs))
            Wv[vi, cand] = x
        # one smoothing pass over the grid (not the seam row), then 4 influences
        G = Wv.reshape(len(Vv), len(U), nb)
        Gs = G.copy()
        Gs[1:, 1:-1] = 0.5 * G[1:, 1:-1] + 0.125 * (G[1:, :-2] + G[1:, 2:] + G[:-1, 1:-1] + np.vstack([G[2:, 1:-1], G[-1:, 1:-1]]))
        Wv = Gs.reshape(-1, nb)
        idx = np.argsort(-Wv, axis=1)[:, 4:]
        np.put_along_axis(Wv, idx, 0.0, axis=1)
        Wv /= np.maximum(Wv.sum(1, keepdims=True), 1e-9)
        for K, a, T in targets:
            kind = [kd for KK, _, kd in Ks if KK is K][0]
            e = np.linalg.norm(lbs(K, Wv, P) - T, axis=1)
            err[kind] = max(err[kind], float(e.max()))
        log('wing %s fit: max error %s' % (sx, ', '.join('%s %.3f m' % kv for kv in err.items())))
        if os.environ.get('WINGDBG'):
            for K, a, T in targets:
                kind = [kd for KK, _, kd in Ks if KK is K][0]
                e0 = np.linalg.norm(lbs(K, W0, P) - T, axis=1); e1 = np.linalg.norm(lbs(K, Wv, P) - T, axis=1)
                log('  %s  W0 med %.3f p95 %.3f max %.3f | fit med %.3f p95 %.3f max %.3f at v=%.2f u=%.2f' % (
                    kind, np.median(e0), np.percentile(e0, 95), e0.max(), np.median(e1), np.percentile(e1, 95),
                    e1.max(), Vv[ii[e1.argmax()]], U[jj[e1.argmax()]]))
        Wout.append(Wv)
    return np.vstack(Wout)


# ----------------------------------------------------------------------------
# Paint: colour as a function of rest-pose position (sRGB 0..1)
# ----------------------------------------------------------------------------
def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mixc(a, b, t):
    a = np.asarray(a, float); b = np.asarray(b, float)
    t = np.asarray(t, float)[:, None]
    return a * (1 - t) + b * t


def hash3(P, scale, seed=0.0):
    """Cheap smooth-ish value noise in [0,1] from positions."""
    q = P * scale + seed
    v = np.sin(q[:, 0] * 1.7 + np.sin(q[:, 1] * 2.3) * 1.3) * np.sin(q[:, 1] * 1.9 + np.sin(q[:, 2] * 1.1) * 1.7) \
        * np.sin(q[:, 2] * 2.1 + np.sin(q[:, 0] * 1.5) * 1.2)
    return 0.5 + 0.5 * v


def fbm(P, scale, seed=0.0):
    return (hash3(P, scale, seed) * 0.5 + hash3(P, scale * 2.1, seed + 3.1) * 0.3
            + hash3(P, scale * 4.3, seed + 7.7) * 0.2)


SKIN = (0.805, 0.595, 0.440)
SKIN_SUN = (0.790, 0.560, 0.405)
LIP = (0.78, 0.50, 0.47)
BROW = (0.21, 0.15, 0.115)


def paint_skin(P, N, UV=None):
    n = len(P)
    col = np.tile(np.array(SKIN, float), (n, 1))
    # sun tan: darker on top-facing surfaces (shoulders, nose, forearms), lighter underneath
    up = np.clip(N[:, 2], -1, 1)
    col = mixc(col, SKIN_SUN, np.clip(0.10 + 0.20 * up, 0, 0.3))
    col = mixc(col, (0.88, 0.69, 0.57), np.clip(-up, 0, 1) * 0.12)
    col *= (0.97 + 0.06 * hash3(P, 25.0))[:, None]
    d = P - HEADC
    face = (np.abs(d[:, 0]) < 0.09) & (d[:, 2] > -0.12) & (d[:, 2] < 0.08) & (d[:, 1] > 0.0)
    if BASE_MODE:
        if face.any():
            col[face] = paint_face_base(P[face], N[face], col[face])
        hd = P[:, 2] > 1.40
        if hd.any():   # fine baby hair just below the hairline, fading into the skin
            q = P[hd]
            th = np.degrees(np.abs(np.arctan2(q[:, 0], q[:, 1] - HAIR_C[1])))
            dz = q[:, 2] - HEADC[2] - np.interp(th, *HAIRLINE)
            a = np.arctan2(q[:, 0], q[:, 1] - HAIR_C[1])
            st = 0.5 + 0.5 * np.sin(a * 160 + np.sin(q[:, 2] * 300) * 2)
            m = sstep(-0.015, 0.0, dz) ** 1.6 * (0.80 + 0.20 * st) * 0.75
            m *= hair_weight(q + V(0, 0, 0.010)) > 0.05
            col[hd] = mixc(col[hd], (0.16, 0.115, 0.09), np.clip(m, 0, 1) * 0.85)
        return np.clip(col, 0, 1)
    if face.any():
        q = d[face]; c = col[face]
        x, y, z = q[:, 0], q[:, 1], q[:, 2]
        ax = np.abs(x)
        # blush + sunburnt nose
        bl = np.exp(-(((ax - 0.040) / 0.016) ** 2 + ((z + 0.024) / 0.014) ** 2))
        c = mixc(c, (0.84, 0.52, 0.44), bl * 0.16)
        nz = np.exp(-((x / 0.011) ** 2 + ((z + 0.030) / 0.011) ** 2)) * (y > 0.085)
        c = mixc(c, (0.80, 0.47, 0.38), nz * 0.2)
        nos = np.exp(-(((ax - 0.0060) / 0.0028) ** 2 + ((z + 0.0408) / 0.0017) ** 2)) * (N[face][:, 2] < -0.2)
        c = mixc(c, (0.30, 0.16, 0.13), np.clip(nos * 1.2, 0, 1))
        # lips
        zl = mouth_line(x)
        zz = z - (zl - MOUTH_Z)
        bow = 0.0010 * np.exp(-(x / 0.0035) ** 2) - 0.0004 * np.exp(-((ax - 0.0058) / 0.004) ** 2)
        e1 = (x / 0.0195) ** 2 + ((zz - MOUTH_Z - 0.0040 + bow) / 0.0044) ** 2
        e2 = (x / 0.0165) ** 2 + ((zz - MOUTH_Z + 0.0052) / 0.0058) ** 2
        up_m = sstep(1.5, 0.55, e1) * (z > zl - 0.0004)
        lo_m = sstep(1.5, 0.55, e2) * (z < zl + 0.0004)
        c = mixc(c, np.array(LIP) * 0.93, up_m * (y > 0.074) * 0.85)
        c = mixc(c, LIP, lo_m * (y > 0.074) * 0.80)
        c = mixc(c, (0.80, 0.55, 0.52), (sstep(0.5, 0.0, e2) * (y > 0.085)) * 0.25)     # lower-lip sheen
        mline = sstep(0.0012, 0.0002, np.abs(z - zl)) * sstep(0.0222, 0.0195, ax) * (y > 0.074)
        c = mixc(c, (0.34, 0.16, 0.15), mline * 0.85)
        corner = np.exp(-(((ax - 0.0212) / 0.0020) ** 2 + ((z - zl) / 0.0020) ** 2))
        c = mixc(c, (0.45, 0.26, 0.22), corner * 0.5)
        # brows
        for s in (-1, 1):
            u = x * s
            t = (u - 0.013) / 0.038
            tc = np.clip(t, 0, 1)
            zc = 0.0145 + 0.0045 * np.sin(np.pi / 2 * np.clip(tc / 0.6, 0, 1)) \
                - 0.0038 * np.clip((tc - 0.6) / 0.4, 0, 1) ** 1.3
            th = 0.0021 - 0.0008 * tc - 0.0006 * tc ** 2
            m = sstep(th, th * 0.35, np.abs(z - zc)) * (y > 0.030)
            m *= sstep(-0.10, 0.06, t) * sstep(1.03, 0.92, t)
            dens = 0.55 + 0.45 * sstep(0.0, 0.35, tc)
            ang = np.radians(72 - 55 * tc)
            strokes = 0.72 + 0.28 * np.sin(2 * np.pi * (u * np.cos(ang) + z * np.sin(ang)) / 0.0009)
            c = mixc(c, BROW, np.clip(m * dens * strokes, 0, 1) * 0.95)
            # eyes: lash line, lid shadow, inner socket
            ec = EYE_C[0 if s < 0 else 1] - HEADC
            eu = (x - ec[0]) * s; ew = z - ec[2]
            L = eye_lens(eu, ew, s)
            above = ew > -0.0005 + 0.0002 * eu / 0.014
            lash = sstep(0.0026, 0.0003, L) * above * (y > ec[1] - 0.006)
            wing = np.exp(-(((eu - 0.0150) / 0.0028) ** 2 + ((ew - 0.0024) / 0.0012) ** 2))
            c = mixc(c, (0.07, 0.05, 0.05), np.clip(lash * 0.95 + wing * 0.8, 0, 1))
            low = sstep(0.0012, 0.0002, L) * (~above) * (y > ec[1] - 0.004)
            c = mixc(c, (0.40, 0.26, 0.22), low * 0.6)
            lid = np.exp(-((eu / 0.016) ** 2 + ((ew - 0.0070) / 0.0035) ** 2))
            c = mixc(c, (0.62, 0.40, 0.32), lid * 0.35)
            inside = (L < 0) & (y < ec[1] + 0.0045)
            c = np.where(inside[:, None], np.array([0.62, 0.36, 0.33]), c)
        col[face] = c
    return np.clip(col, 0, 1)


# ---------------------------------------------------------------- base-mesh face: lids, lashes, paint
LIDS = {}                  # s -> (u, upper w, lower w): eyelid margins relative to the eye centre (u outward)
MOUTH = dict(z=-0.0635, w=0.0212, up=0.0068, lo=0.0068)   # head frame (HEADC), measured on the warped base


def measure_lids(body):
    co = get_co(body)
    for i, s in enumerate((-1, 1)):
        ec = EYE_C[i]
        d = np.linalg.norm(co - ec, axis=1)
        P = co[(d < EYE_R + 0.0025) & (co[:, 1] > ec[1] + 0.002)]
        u_all = (P[:, 0] - ec[0]) * s; w_all = P[:, 2] - ec[2]
        us = np.arange(-0.0135, 0.0141, 0.001)
        up, lo = [], []
        for u in us:
            k = np.abs(u_all - u) < 0.0007
            a = w_all[k & (w_all > -0.002)]; b = w_all[k & (w_all <= -0.002)]
            up.append(a.min() if len(a) else np.nan); lo.append(b.max() if len(b) else np.nan)
        up = np.array(up); lo = np.array(lo)
        ok = ~np.isnan(up) & ~np.isnan(lo) & (up > lo + 0.0005)
        us, up, lo = us[ok], up[ok], lo[ok]
        up = np.convolve(np.pad(up, 1, mode='edge'), [0.25, 0.5, 0.25], 'valid')
        lo = np.convolve(np.pad(lo, 1, mode='edge'), [0.25, 0.5, 0.25], 'valid')
        LIDS[s] = (us, up, lo)
    u, a, b = LIDS[1]
    log('eyelids: opening u %.4f..%.4f, upper %.4f lower %.4f' % (u[0], u[-1], a.max(), b.min()))


def make_lashes_base():
    """Upper lashes along the measured lid margins: a curled double-sided strip, longer at the outer end."""
    verts, faces = [], []
    for i, s in enumerate((-1, 1)):
        c = EYE_C[i]
        us, up, lo = LIDS[s]
        uu = np.linspace(us[0] + 0.0008, us[-1] - 0.0002, 14)
        ww = np.interp(uu, us, up) + 0.0002
        rr = EYE_R + 0.0012
        yy = np.sqrt(np.maximum(rr ** 2 - uu ** 2 - ww ** 2, 0.003 ** 2))
        base = np.stack([c[0] + s * uu, c[1] + yy, c[2] + ww], 1)
        tt = (uu - uu[0]) / (uu[-1] - uu[0])
        nl = base - c; nl /= np.linalg.norm(nl, axis=1)[:, None]
        upv = V(0, 0, 1); out = V(s, 0, 0)
        d1 = nl * 0.75 + upv[None] * 0.45 + out[None] * (0.2 * tt + 0.35 * sstep(0.75, 1.0, tt))[:, None]
        d1 /= np.linalg.norm(d1, axis=1)[:, None]
        L = 0.0022 + 0.0048 * tt ** 1.2
        mid = base + d1 * (L * 0.55)[:, None]
        d2 = d1 + upv[None] * 0.8; d2 /= np.linalg.norm(d2, axis=1)[:, None]
        tip = mid + d2 * (L * 0.5)[:, None]
        rows = [base, mid, tip]
        n = len(base)
        for flip, off in ((False, 0.0), (True, -0.00012)):
            b0 = sum(len(v) for v in verts)
            for r in rows:
                verts.append(r + nl * off)
            for ri in range(2):
                for j in range(n - 1):
                    q = [b0 + ri * n + j, b0 + ri * n + j + 1, b0 + (ri + 1) * n + j + 1, b0 + (ri + 1) * n + j]
                    if (s > 0) != flip:
                        q = q[::-1]
                    faces.append(q)
    return mesh_from('Lashes', np.vstack(verts), np.array(faces))


def paint_face_base(P, N, col):
    """Brows, lash line, lids, lips, blush on the base head (P modelling frame)."""
    d = P - HEADC
    x, y, z = d[:, 0], d[:, 1], d[:, 2]
    ax = np.abs(x)
    front = sstep(0.05, 0.35, N[:, 1])
    c = col
    # soft blush on the cheeks and a little on the nose (sun)
    bl = np.exp(-(((ax - 0.038) / 0.017) ** 2 + ((z + 0.030) / 0.014) ** 2)) * front
    c = mixc(c, (0.86, 0.52, 0.45), bl * 0.22)
    nz = np.exp(-((x / 0.010) ** 2 + ((z + 0.031) / 0.010) ** 2)) * front
    c = mixc(c, (0.84, 0.52, 0.42), nz * 0.18)
    zone = np.exp(-((x / 0.050) ** 2 + ((z + 0.026) / 0.016) ** 2)) * front
    fr = hash3(P * [1.0, 1.0, 1.0], 900.0, 3.0) * hash3(P, 1700.0, 7.0)
    c = mixc(c, (0.62, 0.40, 0.29), sstep(0.62, 0.80, fr) * zone * 0.55)
    # lips
    M = MOUTH
    q = np.clip(ax / M['w'], 0, 1.4)
    zl = M['z'] + 0.0005 * q ** 2
    bow = 0.0010 * np.exp(-(x / 0.0035) ** 2) - 0.0005 * np.exp(-((ax - 0.0060) / 0.004) ** 2)
    top = M['up'] * np.clip(1 - q ** 2.2, 0, 1) ** 0.6 + bow * (q < 1)
    bot = M['lo'] * np.clip(1 - q ** 2.0, 0, 1) ** 0.7
    inner = (z > zl - bot) & (z < zl + top) & (q < 1)
    edge = np.minimum(np.where(z >= zl, zl + top - z, z - (zl - bot)), (1 - q) * 0.012)
    lipm = sstep(0.0, 0.0012, edge) * inner * front
    c = mixc(c, LIP, lipm * 0.88)
    c = mixc(c, (0.86, 0.60, 0.56), lipm * sstep(0.003, 0.0, np.abs(z - (zl - 0.45 * bot))) * 0.2)   # sheen
    mline = sstep(0.0010, 0.0002, np.abs(z - zl)) * sstep(1.05, 0.9, q) * front
    c = mixc(c, (0.42, 0.20, 0.18), mline * 0.8)
    corner = np.exp(-(((ax - M['w']) / 0.0018) ** 2 + ((z - zl) / 0.0018) ** 2)) * front
    c = mixc(c, (0.55, 0.32, 0.27), corner * 0.45)
    for i, s in enumerate((-1, 1)):
        ec = EYE_C[i] - HEADC
        u = (x - ec[0]) * s; w = z - ec[2]
        near = (np.abs(u) < 0.03) & (w > -0.02) & (w < 0.035) & (y > ec[1] - 0.012)
        if not near.any():
            continue
        # brows: thin, natural, gently arched
        tb = (u + 0.0185) / 0.0415
        tc = np.clip(tb, 0, 1)
        zc = 0.0168 + 0.0040 * np.sin(np.pi / 2 * np.clip(tc / 0.62, 0, 1)) - 0.0042 * np.clip((tc - 0.62) / 0.38, 0, 1) ** 1.3
        th = 0.0024 - 0.0008 * tc - 0.0006 * tc ** 2
        m = sstep(th, th * 0.3, np.abs(w - zc)) * sstep(-0.08, 0.06, tb) * sstep(1.03, 0.92, tb) * front
        dens = 0.55 + 0.45 * sstep(0.0, 0.35, tc)
        ang = np.radians(70 - 55 * tc)
        strokes = 0.72 + 0.28 * np.sin(2 * np.pi * (u * np.cos(ang) + w * np.sin(ang)) / 0.0009)
        c = mixc(c, BROW, np.clip(m * dens * strokes, 0, 1) * 0.92)
        # lid margins from the mesh
        us, up, lo = LIDS[s]
        wu = np.interp(u, us, up); wl = np.interp(u, us, lo)
        inside_u = (u > us[0] - 0.0015) & (u < us[-1] + 0.0025)
        r3 = np.linalg.norm(P - EYE_C[i], axis=1)
        close = sstep(EYE_R + 0.006, EYE_R + 0.0015, r3)
        tt = np.clip((u - us[0]) / (us[-1] - us[0]), 0, 1)
        lw = 0.0010 + 0.0010 * tt
        lash = sstep(lw, 0.0002, w - wu) * (w > wu - 0.0006) * inside_u * close
        wing = np.exp(-(((u - us[-1] - 0.0018) / 0.0022) ** 2 + ((w - wu[-1] - 0.0012) / 0.0010) ** 2)) * close
        c = mixc(c, (0.08, 0.055, 0.05), np.clip(lash + 0.7 * wing, 0, 1) * 0.95)
        low = sstep(0.0010, 0.0, wl - w) * (w < wl + 0.0003) * inside_u * close
        c = mixc(c, (0.52, 0.34, 0.29), low * 0.55)
        crease = np.exp(-((u / 0.014) ** 2 + ((w - wu - 0.0045) / 0.0018) ** 2)) * close
        c = mixc(c, (0.66, 0.45, 0.37), crease * 0.25)
        lidsh = np.exp(-((u / 0.016) ** 2 + ((w - wu - 0.0030) / 0.0035) ** 2)) * front
        c = mixc(c, (0.70, 0.48, 0.40), lidsh * 0.18)
    return c


def paint_eye(P, N, UV=None):
    col = np.zeros((len(P), 3))
    for i, s in enumerate((-1, 1)):
        m = (P[:, 0] * s) > 0
        d = P[m] - EYE_C[i]
        d /= np.linalg.norm(d, axis=1)[:, None]
        g = nrm(V(-s * 0.04, 1, 0.0))
        ang = np.degrees(np.arccos(np.clip(d @ g, -1, 1)))
        c = np.tile(np.array([0.90, 0.88, 0.84]), (len(d), 1))
        c = mixc(c, (0.80, 0.70, 0.66), sstep(40, 75, ang) * 0.6)
        iris = sstep(34.0, 32.0, ang)
        tone = 0.5 + 0.5 * np.sin(np.arctan2(d[:, 2], d[:, 0]) * 23) * 0.4
        ic = mixc(np.tile(np.array([0.36, 0.22, 0.13]), (len(d), 1)), (0.21, 0.13, 0.085), sstep(15, 28, ang))
        ic = ic * (0.85 + 0.3 * tone)[:, None]
        c = mixc(c, ic, iris)
        c = mixc(c, (0.09, 0.06, 0.045), sstep(29.5, 32.5, ang) * iris)   # limbal ring
        c = mixc(c, (0.02, 0.015, 0.015), sstep(13.0, 11.5, ang))         # pupil
        hl = nrm(g + V(s * 0.0, 0, 0) + V(-0.18 * s, 0, 0.22))
        hang = np.degrees(np.arccos(np.clip(d @ hl, -1, 1)))
        c = mixc(c, (1, 1, 1), sstep(5.0, 3.5, hang) * 0.9)
        col[m] = c
    return col


TOP_COL = (0.80, 0.70, 0.60)
WRAP_COL = (0.50, 0.42, 0.35)


def cloth_base(P, base, seed, grime=0.12):
    n = len(P)
    col = np.tile(np.array(base, float), (n, 1))
    f = fbm(P, 22.0, seed)
    col *= (0.91 + 0.16 * f)[:, None]
    col = mixc(col, (0.32, 0.28, 0.22), np.clip((fbm(P, 12.0, seed + 5) - 0.55) * 2.0, 0, 1) * grime)
    return col


def stitches(col, dist, along, color=(0.25, 0.20, 0.16), width=0.0012, period=0.008, mask=None):
    on = (np.abs(dist) < width) & ((along / period) % 1.0 < 0.55)
    if mask is not None:
        on &= mask
    return np.where(on[:, None], np.array(color), col)


def paint_top(P, N, UV=None):
    col = cloth_base(P, TOP_COL, 1.0, 0.10)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # dirtier and frayed toward the hem, faded on top
    col = mixc(col, (0.55, 0.47, 0.40), sstep(1.15, 1.105, z) * 0.45)
    col = mixc(col, (0.88, 0.80, 0.70), np.clip(N[:, 2], 0, 1) * 0.25)
    # a mended patch under the left breast and a seam down the side
    pm = (np.abs(x + 0.075) < 0.026) & (np.abs(z - 1.135) < 0.018) & (y > 0)
    col = np.where(pm[:, None], col * np.array([0.92, 0.86, 0.78]), col)
    near = (np.abs(x + 0.075) < 0.029) & (np.abs(z - 1.135) < 0.021) & (y > 0)
    edge = np.minimum(np.abs(np.abs(x + 0.075) - 0.026), np.abs(np.abs(z - 1.135) - 0.018))
    col = stitches(col, edge, x + z, mask=near)
    col = stitches(col, np.abs(np.abs(x) - 0.128), z, width=0.0010)
    return np.clip(col, 0, 1)


def paint_wrap(P, N, UV=None):
    col = cloth_base(P, WRAP_COL, 2.0, 0.18)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    col = mixc(col, (0.32, 0.26, 0.21), sstep(0.80, 0.72, z) * 0.45)
    col = mixc(col, (0.60, 0.52, 0.44), np.clip(N[:, 2], 0, 1) * 0.3)
    # diagonal wrap edge on the front left
    dl = (x + 0.02) + (0.93 - z) * 0.55
    over = (y > 0) & (np.abs(dl) < 0.006)
    col = mixc(col, (0.25, 0.25, 0.19), over.astype(float) * 0.6)
    # patches with stitches
    for cx, cz, hw, hz, tint in ((0.10, 0.80, 0.03, 0.022, (0.95, 0.88, 0.75)), (-0.06, 0.86, 0.022, 0.018, (0.82, 0.86, 0.80)),
                                 (0.02, 0.78, 0.028, 0.02, (1.05, 1.0, 0.85))):
        side = np.sign(y) if cx > 0 else -np.sign(y)
        pm = (np.abs(x - cx) < hw) & (np.abs(z - cz) < hz)
        if cx == 0.02:
            pm &= y < 0
        col = np.where(pm[:, None], col * np.array(tint), col)
        near = (np.abs(x - cx) < hw + 0.003) & (np.abs(z - cz) < hz + 0.003)
        if cx == 0.02:
            near &= y < 0
        e = np.minimum(np.abs(np.abs(x - cx) - hw), np.abs(np.abs(z - cz) - hz))
        col = stitches(col, e, x * 1.3 + z, mask=near)
    return np.clip(col, 0, 1)


def paint_shorts(P, N, UV=None):
    return np.clip(cloth_base(P, (0.40, 0.34, 0.28), 3.0, 0.15), 0, 1)


def paint_leather(P, N, UV=None):
    n = len(P)
    col = np.tile(np.array([0.40, 0.29, 0.21]), (n, 1))
    f = hash3(P, 40.0, 4.0)
    col *= (0.85 + 0.25 * f)[:, None]
    col = mixc(col, (0.50, 0.36, 0.24), np.clip(N[:, 2], 0, 1) * 0.25 * f)
    return np.clip(col, 0, 1)


def paint_sole(P, N, UV=None):
    col = paint_leather(P, N) * 0.75
    return np.clip(col, 0, 1)


def paint_wood(P, N, UV=None):
    n = len(P)
    g = 0.5 + 0.5 * np.sin((P[:, 0] * 0.3 + P[:, 2]) * 900 + np.sin(P[:, 1] * 300) * 2)
    col = mixc(np.tile(np.array([0.62, 0.40, 0.29]), (n, 1)), (0.45, 0.29, 0.20), g * 0.6)
    return np.clip(col, 0, 1)


def paint_metal(P, N, UV=None):
    n = len(P)
    return np.tile(np.array([0.46, 0.43, 0.39]), (n, 1)) * (0.8 + 0.3 * fbm(P, 200.0))[:, None]


CAPE_RED = (0.74, 0.29, 0.21)
CAPE_FADE = (0.86, 0.72, 0.62)


def paint_cape(P, N, UV):
    U0 = np.clip((UV[:, 0] - 0.003) / 0.994, 0, 1)
    uu = np.where(U0 < 0.5, U0 / 0.4970, (1 - U0) / 0.4970)              # 0 wrist .. 1 ankle (along the seam)
    vv = 1 - np.clip((UV[:, 1] - 0.003) / (CAPE_STRIP - 0.008), 0, 1)     # 0 seam .. 1 free edge
    side = np.where(U0 < 0.5, 0.0, 7.0)
    n = len(P)
    q = np.stack([uu * 4 + side, vv * 2, uu * 0], 1)
    f = fbm(q, 3.0, 9.0)
    col = np.tile(np.array(CAPE_RED, float), (n, 1)) * (0.88 + 0.22 * f)[:, None]
    # sun-bleached toward the free edge and the wrist / ankle tips, blotchy
    fade = np.clip(sstep(0.50, 1.0, vv + (f - 0.5) * 0.35) + sstep(0.08, 0.0, uu) * 0.6 + sstep(0.92, 1.0, uu) * 0.6, 0, 1)
    col = mixc(col, CAPE_FADE, fade * 0.82)
    col = mixc(col, (0.60, 0.19, 0.13), sstep(0.06, 0.0, vv) * 0.6)          # binding along the body seam
    # stitched spars and a mended patch or two
    for su in (0.30, 0.62):
        dd = np.abs(uu - su - 0.05 * vv)
        col = mixc(col, (0.58, 0.18, 0.12), ((dd < 0.0026) & (vv < 0.92)).astype(float) * 0.4)
    for cu, cv, hu, hv in ((0.33, 0.55, 0.035, 0.12), (0.62, 0.30, 0.025, 0.10)):
        pm = (np.abs(uu - cu) < hu) & (np.abs(vv - cv) < hv)
        col = np.where(pm[:, None], col * np.array([1.06, 0.92, 0.86]), col)
        e = np.minimum(np.abs(np.abs(uu - cu) - hu), np.abs(np.abs(vv - cv) - hv) * 0.5)
        col = mixc(col, (0.45, 0.14, 0.10), ((e < 0.0022) & (((uu + vv) * 260) % 1 < 0.55)).astype(float) * 0.8)
    return np.clip(col, 0, 1)


def fix_flipped(ob, S):
    """Flip faces whose normal points into the SDF (decimation folds)."""
    me = ob.data
    cen = np.empty(len(me.polygons) * 3, np.float32); me.polygons.foreach_get('center', cen)
    nor = np.empty(len(me.polygons) * 3, np.float32); me.polygons.foreach_get('normal', nor)
    cen = cen.reshape(-1, 3).astype(np.float64); nor = nor.reshape(-1, 3)
    e = 0.0005
    f = S.eval_points(cen)
    g = np.stack([(S.eval_points(cen + V(*(e * np.eye(3)[a]))) - f) / e for a in range(3)], 1)
    bad = (np.einsum('ij,ij->i', g, nor) < -0.3 * np.linalg.norm(g, axis=1)) & (np.abs(f) < 0.003)
    if bad.any():
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in np.nonzero(bad)[0]])
        bm.to_mesh(me); bm.free()
    log('flipped %d inverted faces' % bad.sum())


def refine_face(ob, S):
    """Subdivide the face (twice around eyes, nose and mouth) and put the new vertices on the SDF."""
    passes = [lambda c: (c[:, 2] > 1.395) & (c[:, 1] > -0.040),
              lambda c: (c[:, 2] > 1.445) & (c[:, 2] < 1.522) & (np.abs(c[:, 0]) < 0.046) & (c[:, 1] > 0.058)]
    for sel in passes:
        ob.data.validate()
        bm = bmesh.new(); bm.from_mesh(ob.data)
        cen = np.array([f.calc_center_median()[:] for f in bm.faces])
        m = sel(cen)
        faces = [f for f, k in zip(bm.faces, m) if k]
        edges = list({e for f in faces for e in f.edges})
        n0 = len(bm.faces)
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        log('refine pass: %d of %d faces selected, now %d' % (len(faces), n0, len(bm.faces)))
        bm.to_mesh(ob.data); bm.free()
        co = get_co(ob)
        vm = (co[:, 2] > 1.385) & (co[:, 1] > -0.07)      # every head vertex goes onto the true surface
        p = co[vm]
        e = 0.0003
        for _ in range(4):
            f = S.eval_points(p)
            g = np.stack([(S.eval_points(p + V(*(e * np.eye(3)[a]))) - f) / e for a in range(3)], 1)
            step = f[:, None] * g / np.maximum((g * g).sum(1), 1e-9)[:, None]
            ln = np.linalg.norm(step, axis=1)
            step *= np.minimum(1.0, 0.002 / np.maximum(ln, 1e-12))[:, None]
            p = p - step
        co[vm] = p
        set_co(ob, co)
    log('face refined: body now %d tris' % ntris(ob))


def make_lashes():
    """Upper lashes: a curled double-sided strip along each upper lid margin."""
    verts, faces = [], []
    for i, s in enumerate((-1, 1)):
        c = EYE_C[i]
        base, t = upper_lid_curve(i, s, 14, lift=0.0003, rad=EYE_R + 0.0013, span=0.97)
        tt = (t + 1) / 2
        nl = base - c; nl /= np.linalg.norm(nl, axis=1)[:, None]
        up = V(0, 0, 1); out = V(s, 0, 0)
        d1 = nl * 0.70 + up[None] * 0.55 + out[None] * (0.25 * tt + 0.35 * sstep(0.8, 1.0, tt))[:, None]
        d1 /= np.linalg.norm(d1, axis=1)[:, None]
        L = 0.0020 + 0.0042 * tt ** 1.3
        mid = base + d1 * (L * 0.55)[:, None]
        d2 = d1 + up[None] * 0.7; d2 /= np.linalg.norm(d2, axis=1)[:, None]
        tip = mid + d2 * (L * 0.5)[:, None]
        rows = [base, mid, tip]
        n = len(base)
        for flip, off in ((False, 0.0), (True, -0.00012)):
            b0 = sum(len(v) for v in verts)
            nrm_off = nl * off
            for r in rows:
                verts.append(r + nrm_off)
            for ri in range(2):
                for j in range(n - 1):
                    q = [b0 + ri * n + j, b0 + ri * n + j + 1, b0 + (ri + 1) * n + j + 1, b0 + (ri + 1) * n + j]
                    if (s > 0) != flip:
                        q = q[::-1]
                    faces.append(q)
    ob = mesh_from('Lashes', np.vstack(verts), np.array(faces))
    return ob


def make_eyes():
    obs = []
    for i, s in enumerate((-1, 1)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=18, ring_count=11, radius=EYE_R, location=tuple(EYE_C[i]))
        ob = bpy.context.active_object
        ob.rotation_euler = (math.pi / 2, 0, 0)   # poles along Y: rings around the gaze
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obs.append(ob)
    activate(obs[0]); obs[1].select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = 'Eyes'
    shade_smooth(ob)
    return ob


# ----------------------------------------------------------------------------
# Preview (workbench quick look)
# ----------------------------------------------------------------------------
def quick_render(path, cam_loc, target, lens=50, res=800, engine='BLENDER_WORKBENCH', roll=0.0):
    sc = bpy.context.scene
    sc.render.engine = engine
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.film_transparent = False
    if engine == 'BLENDER_WORKBENCH':
        sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'MATERIAL'
    cam = bpy.data.objects.get('PrevCam')
    if cam is None:
        cam = bpy.data.objects.new('PrevCam', bpy.data.cameras.new('PrevCam'))
        sc.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.01
    cam.location = Vector(cam_loc)
    dvec = Vector(target) - Vector(cam_loc)
    q = dvec.to_track_quat('-Z', 'Y')
    if roll:
        q = q @ Quaternion((0, 0, 1), math.radians(roll))
    cam.rotation_euler = q.to_euler()
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


NECK_CUT = 1.378


def bm_cut(ob, z, keep_above):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                           plane_co=(0, 0, z), plane_no=(0, 0, 1),
                           clear_inner=keep_above, clear_outer=not keep_above)
    bm.to_mesh(ob.data); bm.free()
    ob.data.update()


def mesh_body(S):
    """Body at 1.6 mm, head + neck at 0.8 mm, bridged at the neck."""
    hb = 0.0032 if FAST else 0.0016
    hh = 0.0016 if FAST else 0.0008
    body = sdf_mesh('Body', S, V(-0.76, -0.20, -0.004), V(0.76, 0.24, NECK_CUT + 0.012), hb, smooth_iters=0)
    head = sdf_mesh('HeadHi', S, V(-0.12, -0.14, NECK_CUT - 0.012), V(0.12, 0.13, 1.632), hh, smooth_iters=0)
    bm_cut(body, NECK_CUT - 0.002, keep_above=False)
    bm_cut(head, NECK_CUT + 0.001, keep_above=True)
    activate(body); head.select_set(True)
    bpy.ops.object.join()
    ob = body
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bnd = [e for e in bm.edges if e.is_boundary and abs(e.verts[0].co.z - NECK_CUT) < 0.01]
    res = bmesh.ops.bridge_loops(bm, edges=bnd)
    log('neck bridge faces', len(res['faces']))
    bm.to_mesh(ob.data); bm.free()
    # smooth across the seam
    co = get_co(ob)
    vg = ob.vertex_groups.new(name='seam')
    w = np.clip(1.0 - np.abs(co[:, 2] - NECK_CUT) / 0.006, 0, 1)
    for i in np.nonzero(w > 0)[0]:
        vg.add([int(i)], float(w[i]), 'REPLACE')
    smooth(ob, 0.8, 6, 'seam')
    ob.vertex_groups.remove(ob.vertex_groups['seam'])
    smooth(ob, 0.4, 1)
    return ob


def detail_group(ob):
    """Decimation guard: face > hands/feet > rest."""
    co = get_co(ob)
    w = np.zeros(len(co))
    d = co - HEADC
    face = np.clip(1.0 - (np.sqrt((d[:, 0] / 0.06) ** 2 + (d[:, 2] / 0.085) ** 2)), 0, 1) * (d[:, 1] > 0.02)
    w = np.maximum(w, np.clip(face * 2.5, 0, 1))
    w = np.maximum(w, 0.35 * (co[:, 2] > NECK_CUT))
    for s in (-1, 1):
        dh = np.linalg.norm(co - (SK.wrist(s) + 0.07 * SK.arm_dir(s)), axis=1)
        w = np.maximum(w, 0.8 * np.clip(1 - dh / 0.09, 0, 1) ** 0.3)
        df = np.linalg.norm(co - (SK.ankle(s) + V(0, 0.08, -0.05)), axis=1)
        w = np.maximum(w, 0.5 * np.clip(1 - df / 0.12, 0, 1) ** 0.3)
    vg = ob.vertex_groups.new(name='detail')
    for val in np.unique(np.round(w, 2)):
        idx = np.nonzero(np.round(w, 2) == val)[0].tolist()
        vg.add(idx, float(val), 'REPLACE')
    return 'detail'


# ----------------------------------------------------------------------------
# Full build
# ----------------------------------------------------------------------------
ORIGIN = V(0, -0.005, 0.89)     # hips: the model's origin after export
PARTS = ['skin', 'eyes', 'hair', 'top', 'wrap', 'shorts', 'leather', 'wood', 'metal', 'cape', 'sole', 'strand']
MATS = {'skin': ('Skin', 0.7), 'eyes': ('Eyes', 0.3), 'hair': ('Hair', 0.6), 'top': ('Cloth', 0.9),
        'wrap': ('Cloth', 0.9), 'shorts': ('Cloth', 0.9), 'leather': ('Leather', 0.65), 'wood': ('Leather', 0.65),
        'metal': ('Leather', 0.65), 'cape': ('Cape', 0.9), 'sole': ('Leather', 0.65), 'strand': ('Hair', 0.45)}


def set_part(ob, part):
    a = ob.data.attributes.get('part') or ob.data.attributes.new('part', 'INT', 'FACE')
    vals = np.full(len(ob.data.polygons), PARTS.index(part), np.int32)
    a.data.foreach_set('value', vals)


def shift_origin(ob):
    set_co(ob, get_co(ob) - ORIGIN)


def bone_table():
    """name -> (head, tail, parent) in the shifted (hips = 0) frame."""
    O = ORIGIN
    T = {
        'root': (V(0, 0, 0.89), V(0, -0.12, 0.89), None),
        'hips': (V(0, -0.005, 0.89), V(0, -0.010, 0.99), 'root'),
        'spine': (V(0, -0.010, 0.99), V(0, -0.010, 1.13), 'hips'),
        'chest': (V(0, -0.010, 1.13), V(0, -0.014, 1.335), 'spine'),
        'neck': (SK.neck0.copy(), SK.neck1.copy(), 'chest'),
        'head': (SK.head0.copy(), SK.head1.copy(), 'neck'),
    }
    T['chest'] = (V(0, -0.010, 1.13), SK.neck0.copy(), 'spine')
    for s, sx in ((-1, '.L'), (1, '.R')):
        T['shoulder' + sx] = (SK.clav(s), SK.shoulder(s), 'chest')
        T['upperarm' + sx] = (SK.shoulder(s), SK.elbow(s), 'shoulder' + sx)
        T['forearm' + sx] = (SK.elbow(s), SK.wrist(s), 'upperarm' + sx)
        T['hand' + sx] = (SK.wrist(s), SK.hand_end(s), 'forearm' + sx)
        T['thigh' + sx] = (SK.hip(s), SK.knee(s), 'hips')
        T['shin' + sx] = (SK.knee(s), SK.ankle(s), 'thigh' + sx)
        ball = SK.ankle(s) + 0.15 * nrm(V(SK.toe(s)[0] - SK.ankle(s)[0], SK.toe(s)[1] - SK.ankle(s)[1], 0))
        ball[2] = 0.025
        T['foot' + sx] = (SK.ankle(s), ball, 'shin' + sx)
        if WING_REST:
            wr = WING_REST[s]
            T['cape' + sx] = (wr['A0'] + O, wr['A1'] + O, 'root')
        else:
            al = ankle_loop(s)
            T['cape' + sx] = (al, al + V(0, -0.07, 0.0), 'shin' + sx)
    par = 'head'
    for k, b in enumerate(HAIR_BONES):      # the ponytail chain hangs straight down from the tie at rest
        L = TAIL_LEN / len(HAIR_BONES)
        T[b] = (TIE - V(0, 0, L * k), TIE - V(0, 0, L * (k + 1)), par)
        par = b
    return {k: (h - O, t - O, p) for k, (h, t, p) in T.items()}


BONE_ORDER = ['root', 'hips', 'spine', 'chest', 'neck', 'head'] + \
    [b + sx for sx in ('.L', '.R') for b in ('shoulder', 'upperarm', 'forearm', 'hand')] + \
    [b + sx for sx in ('.L', '.R') for b in ('thigh', 'shin', 'foot', 'cape')] + \
    ['hair.001', 'hair.002', 'hair.003']


def make_armature():
    arm = bpy.data.armatures.new('SakiRig')
    ob = bpy.data.objects.new('Saki', arm)
    bpy.context.scene.collection.objects.link(ob)
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    T = bone_table()
    for name in BONE_ORDER:
        h, t, par = T[name]
        eb = arm.edit_bones.new(name)
        eb.head = Vector(h); eb.tail = Vector(t)
        # roll: z axis toward the front (+Y) where possible, for tidy local axes
        eb.align_roll(Vector((0, 1, 0)) if abs(nrm(t - h)[1]) < 0.9 else Vector((0, 0, 1)))
        if par:
            eb.parent = arm.edit_bones[par]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.display_type = 'STICK'
    return ob


# ---------------------------------------------------------------- weights
def weights_get(ob, bones):
    W = np.zeros((len(ob.data.vertices), len(bones)))
    gi = {g.index: bones.index(g.name) for g in ob.vertex_groups if g.name in bones}
    for v in ob.data.vertices:
        for g in v.groups:
            j = gi.get(g.group)
            if j is not None:
                W[v.index, j] = g.weight
    return W


def weights_set(ob, bones, W, limit=4):
    W = np.array(W, float)
    if limit:
        idx = np.argsort(-W, axis=1)[:, limit:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    W[W < 0.01] = 0
    W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    for j, b in enumerate(bones):
        g = ob.vertex_groups.new(name=b)
        nz = np.nonzero(W[:, j] > 0)[0]
        for val in np.unique(np.round(W[nz, j], 3)):
            ids = nz[np.round(W[nz, j], 3) == val].tolist()
            g.add(ids, float(val), 'REPLACE')


def body_weights(body, rig):
    """Automatic (heat) weights solved on an evenly decimated proxy (the dense face makes the heat
    solver fail), transferred to the body, then L/R leak and hand/head cleanup."""
    for n in ('cape.L', 'cape.R', 'root') + tuple(HAIR_BONES):
        rig.data.bones[n].use_deform = False
    proxy = bpy.data.objects.new('BodyProxy', body.data.copy())
    bpy.context.scene.collection.objects.link(proxy)
    # a watertight, evenly meshed proxy for the heat solver: merge close verts, fill the scalp hole
    bm = bmesh.new(); bm.from_mesh(proxy.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0004)
    bnd = [e for e in bm.edges if e.is_boundary]
    if bnd:
        bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(proxy.data); bm.free()
    decimate(proxy, target=12000)
    # the heat solver is unreliable at human scale in metres: solve at 10x
    proxy.scale = (10, 10, 10); rig.scale = (10, 10, 10)
    bpy.context.view_layer.update()
    activate(proxy); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    rig.scale = (1, 1, 1); proxy.parent = None; proxy.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    for n in ('cape.L', 'cape.R') + tuple(HAIR_BONES):
        rig.data.bones[n].use_deform = True
    bones = BONE_ORDER
    Wp = weights_get(proxy, bones)
    lost = Wp.sum(1) < 1e-6
    if lost.any():
        log('heat weights: %d proxy verts unsolved' % lost.sum())
    W = transfer_weights(proxy, Wp, body)
    bpy.data.objects.remove(proxy)
    body.parent = rig
    md = body.modifiers.new('Armature', 'ARMATURE'); md.object = rig
    co = get_co(body) + ORIGIN
    x = co[:, 0]
    for j, b in enumerate(bones):
        if b.endswith('.L'):
            W[x > 0.025, j] = 0
        if b.endswith('.R'):
            W[x < -0.025, j] = 0
    # hands: everything past the wrist belongs to the hand
    for s, sx in ((-1, '.L'), (1, '.R')):
        d = SK.arm_dir(s); t = (co - SK.wrist(s)) @ d
        near = np.linalg.norm(co - SK.wrist(s), axis=1) < 0.20
        m = near & (t > 0.012)
        W[m] = 0; W[m, bones.index('hand' + sx)] = 1
        blend = near & (t > -0.02) & (t <= 0.012)
        f = np.clip((t[blend] + 0.02) / 0.032, 0, 1)
        W[blend] *= (1 - f)[:, None]; W[blend, bones.index('hand' + sx)] += f
        # feet below the ankle
        an = SK.ankle(s)
        m = (np.abs(x - an[0]) < 0.09) & (co[:, 2] < an[2] - 0.02)
        W[m] = 0; W[m, bones.index('foot' + sx)] = 1
    # the whole head (jaw and chin included) is rigid on the head bone, blending into the neck
    d = co - HEADC
    wh = np.where(d[:, 1] > 0.015, sstep(-0.118, -0.092, d[:, 2]), sstep(-0.075, -0.035, d[:, 2]))
    W = W * (1 - wh)[:, None]; W[:, bones.index('head')] += wh
    empty = W.sum(1) < 1e-6
    if empty.any():
        log('weights: %d verts without weight -> nearest bone (z %.2f..%.2f)' % (empty.sum(), co[empty, 2].min(), co[empty, 2].max()))
        T = bone_table()
        segs = [(b, T[b][0] + ORIGIN, T[b][1] + ORIGIN) for b in bones if b not in ('root', 'cape.L', 'cape.R') + tuple(HAIR_BONES)]
        for i in np.nonzero(empty)[0]:
            best = min(segs, key=lambda sg: np.linalg.norm(co[i] - (sg[1] + np.clip((co[i] - sg[1]) @ (sg[2] - sg[1]) / ((sg[2] - sg[1]) @ (sg[2] - sg[1])), 0, 1) * (sg[2] - sg[1]))))
            W[i, bones.index(best[0])] = 1
    weights_set(body, bones, W)
    return W


def transfer_weights(src, Wsrc, ob):
    from mathutils.bvhtree import BVHTree
    sco = get_co(src)
    tris = np.array([p.vertices[:] for p in src.data.polygons])
    bvh = BVHTree.FromPolygons([Vector(v) for v in sco], tris.tolist())
    co = get_co(ob)
    W = np.zeros((len(co), Wsrc.shape[1]))
    for i, p in enumerate(co):
        loc, nor, fi, dist = bvh.find_nearest(Vector(p))
        a, b, c = sco[tris[fi]]
        # barycentric
        v0, v1, v2 = b - a, c - a, np.array(loc) - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-14:
            bw = np.array([1 / 3, 1 / 3, 1 / 3])
        else:
            v_ = (d11 * d20 - d01 * d21) / den; w_ = (d00 * d21 - d01 * d20) / den
            bw = np.clip(np.array([1 - v_ - w_, v_, w_]), 0, 1); bw /= bw.sum()
        W[i] = bw @ Wsrc[tris[fi]]
    return W


def rigid_weights(ob, bone):
    W = np.zeros((len(ob.data.vertices), len(BONE_ORDER)))
    W[:, BONE_ORDER.index(bone)] = 1
    return W


def wrap_weights(ob, Wt):
    """Skirt: transferred near the waist, blending to hips/thighs toward the hem."""
    co = get_co(ob) + ORIGIN
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    t = np.clip((0.90 - z) / 0.17, 0, 1)
    back = sstep(0.02, -0.06, y)
    share = t * (0.65 - 0.35 * back)
    fL = sstep(0.03, -0.06, x); fR = sstep(-0.03, 0.06, x); fC = np.clip(1 - fL - fR, 0, 1)
    Wp = np.zeros_like(Wt)
    Wp[:, BONE_ORDER.index('hips')] = 1 - share
    Wp[:, BONE_ORDER.index('thigh.L')] = share * (fL + 0.5 * fC)
    Wp[:, BONE_ORDER.index('thigh.R')] = share * (fR + 0.5 * fC)
    f = sstep(0.86, 0.80, z)[:, None]
    return Wt * (1 - f) + Wp * f


# ---------------------------------------------------------------- UV atlas + texture
TEX = 2048
CAPE_STRIP = 0.16


def select_faces(me, mask):
    mask = np.asarray(mask, bool)
    me.polygons.foreach_set('select', mask)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    ltot = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', ltot)
    vs = np.zeros(len(me.vertices), bool); vs[lv[np.repeat(mask, ltot)]] = True
    me.vertices.foreach_set('select', vs)
    ev = np.empty(len(me.edges) * 2, np.int32); me.edges.foreach_get('vertices', ev); ev = ev.reshape(-1, 2)
    me.edges.foreach_set('select', vs[ev[:, 0]] & vs[ev[:, 1]])


def body_charts(cen):
    """Chart label per body face (modelling coords): 0 torso front, 1 torso back, 2 face, 3 head back,
    4/5 arm L/R, 6/7 hand L/R, 8/9 leg L/R, 10/11 foot L/R. Also returns a per-face angle for tube charts."""
    x, y, z = cen[:, 0], cen[:, 1], cen[:, 2]
    lab = np.where(y > -0.012, 0, 1)
    head = z > 1.395
    lab[head] = np.where(y[head] > -0.010, 2, 3)
    phi = np.zeros(len(cen))
    for k, s in enumerate((-1, 1)):
        sh = SK.shoulder(s); d = SK.arm_dir(s); n = SK.palm_n(s)
        v = cen - sh; t = v @ d
        rp = np.linalg.norm(v - t[:, None] * d, axis=1)
        arm = (t > 0.02) & (rp < 0.075) & (x * s > 0.12)
        lab[arm] = 4 + k
        lab[arm & (t > 0.497)] = 6 + k
        e1 = -n; e2 = np.cross(d, e1)
        phi[arm] = np.arctan2(v[arm] @ e2, v[arm] @ e1)
        hp = SK.hip(s); dl = nrm(SK.knee(s) - hp)
        leg = (z < 0.748 + 0.30 * np.maximum(0, np.abs(x) - 0.045)) & (x * s > 0) & ~head
        lab[leg] = 8 + k
        lab[leg & (z < 0.095)] = 10 + k
        w = cen - hp
        e1 = V(s, 0, 0); e1 = nrm(e1 - (e1 @ dl) * dl); e2 = np.cross(dl, e1)
        lg = leg & (z >= 0.095)
        phi[lg] = np.arctan2(w[lg] @ e2, w[lg] @ e1)
    return lab, phi


def mark_seams(me, faces_mask, seam_fn):
    """seam_fn(fa, fb) on face index arrays -> bool; edges between two masked faces."""
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    ea, fa, fb = [], [], []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2 and faces_mask[lf[0].index] and faces_mask[lf[1].index]:
            ea.append(e); fa.append(lf[0].index); fb.append(lf[1].index)
    if ea:
        cut = seam_fn(np.array(fa), np.array(fb))
        for e, c in zip(ea, cut):
            if c:
                e.seam = True
    bm.to_mesh(me); bm.free()


def uv_islands(uv, lv, loop_poly, nfaces):
    """Face -> UV island id (faces sharing a vertex with the same UV are connected)."""
    parent = np.arange(nfaces)
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    key = {}
    q = np.round(uv * 1e5).astype(np.int64)
    for li in range(len(lv)):
        k = (int(lv[li]), int(q[li, 0]), int(q[li, 1]))
        f = loop_poly[li]
        g = key.get(k)
        if g is None:
            key[k] = f
        else:
            ra, rb = find(f), find(g)
            if ra != rb:
                parent[ra] = rb
    return np.array([find(f) for f in range(nfaces)])


def uv_atlas(ob):
    me = ob.data
    part = np.empty(len(me.polygons), np.int32); me.attributes['part'].data.foreach_get('value', part)
    cen = np.empty(len(me.polygons) * 3, np.float32); me.polygons.foreach_get('center', cen)
    cen = cen.reshape(-1, 3).astype(np.float64) + ORIGIN
    P = lambda k: part == PARTS.index(k)
    lstart = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_start', lstart)
    ltot = np.empty(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', ltot)
    loop_poly = np.repeat(np.arange(len(me.polygons)), ltot)
    lv = np.empty(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
    co = get_co(ob) + ORIGIN
    # --- seams: body charts, back seams of top / wrap
    skin = P('skin')
    lab = np.full(len(part), -1); phi = np.zeros(len(part))
    if not BASE_MODE:
        lab[skin], phi[skin] = body_charts(cen[skin])
        def body_seam(fa, fb):
            tube = (lab[fa] >= 4) & (lab[fa] <= 9) & ((lab[fa] < 6) | (lab[fa] > 7))
            return (lab[fa] != lab[fb]) | (tube & (lab[fa] == lab[fb]) & (np.abs(phi[fa] - phi[fb]) > np.pi))
        mark_seams(me, skin, body_seam)
    for k in ('top', 'wrap', 'shorts'):
        m = P(k)
        mark_seams(me, m, lambda fa, fb: (cen[fa, 1] < 0) & (np.sign(cen[fa, 0]) != np.sign(cen[fb, 0])))
    keep = P('cape') | P('leather') | P('wood') | P('metal') | P('eyes') | P('strand') | (skin if BASE_MODE else False)
    cuv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', cuv)
    cuv = cuv.reshape(-1, 2).astype(np.float64)
    # eyes: the two spheres' own UVs overlap -> shift the right eye by one tile
    em = P('eyes')[loop_poly] & (co[lv, 0] > 0)
    cuv[em, 0] += 1.2
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='FACE')
    for m, how in (((skin if not BASE_MODE else np.zeros_like(skin)), 'unwrap'), (P('top'), 'unwrap'), (P('wrap'), 'unwrap'), (P('shorts'), 'unwrap'),
                   (P('sole'), 'smart')):
        bpy.ops.object.mode_set(mode='OBJECT')
        if not np.any(m):
            bpy.ops.object.mode_set(mode='EDIT')
            continue
        select_faces(me, m)
        bpy.ops.object.mode_set(mode='EDIT')
        if how == 'unwrap':
            bpy.ops.uv.unwrap(method='ANGLE_BASED', fill_holes=True, margin=0.0)
        else:
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0,
                                     scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    km = keep[loop_poly]
    uv[km] = cuv[km]
    # hair: equal-area spherical projection about the head (one seam at the back)
    hm = P('hair')[loop_poly]
    d = co[lv[hm]] - HAIR_C
    th = np.arctan2(d[:, 0], d[:, 1]); r = np.linalg.norm(d, axis=1)
    hu = th / (2 * np.pi) + 0.5; hv = (1 + d[:, 2] / r) / 2
    hl = np.nonzero(hm)[0]
    huv = np.stack([hu * 0.6, hv * 0.3], 1)
    lp = loop_poly[hl]
    for f in np.unique(lp):
        sel = lp == f
        us = huv[sel, 0]
        if us.max() - us.min() > 0.3:
            us = np.where(us < 0.3, us + 0.6, us); huv[sel, 0] = us
    uv[hl] = huv
    me.uv_layers['UVMap'].data.foreach_set('uv', uv.astype(np.float32).ravel())
    # --- equalise texel density, then favour the face and eyes
    bpy.ops.object.mode_set(mode='OBJECT')
    select_faces(me, ~P('cape'))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    if BASE_MODE:   # the base mesh's head island(s): those containing the face
        isl = uv_islands(uv, lv, loop_poly, len(me.polygons))
        facef = skin & (cen[:, 2] > 1.43) & (cen[:, 1] > HEADC[1] + 0.03)
        head_isl = np.unique(isl[facef])
        lab[skin & np.isin(isl, head_isl)] = 2
        log('uv: %d skin islands, face in %d' % (len(np.unique(isl[skin])), len(head_isl)))
    for m, f in ((skin & (lab == 2), 3.0 if BASE_MODE else 4.2), (P('eyes'), 2.8), (skin & (lab == 3), 0.7), (P('hair'), 0.9),
                 (P('shorts'), 0.5), (P('sole'), 0.5), (P('leather') | P('metal') | P('wood'), 0.9)):
        lm = m[loop_poly]
        if lm.any():
            c0 = uv[lm].mean(0)
            uv[lm] = c0 + (uv[lm] - c0) * f
    me.uv_layers['UVMap'].data.foreach_set('uv', uv.astype(np.float32).ravel())
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.003, shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    lc = P('cape')[loop_poly]
    uv[:, 1] = CAPE_STRIP + (1 - CAPE_STRIP) * uv[:, 1]
    uv[lc, 0] = 0.003 + 0.994 * cuv[lc, 0]
    uv[lc, 1] = 0.003 + (CAPE_STRIP - 0.008) * cuv[lc, 1]
    me.uv_layers['UVMap'].data.foreach_set('uv', uv.ravel())
    # clear seams (not needed downstream)
    bm = bmesh.new(); bm.from_mesh(me)
    for e in bm.edges:
        e.seam = False
    bm.to_mesh(me); bm.free()


def rasterize(ob, with_bary=False):
    """Per texel: part, rest position (modelling frame), normal, atlas uv."""
    me = ob.data
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tl = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl); tl = tl.reshape(-1, 3)
    tv = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', tv); tv = tv.reshape(-1, 3)
    tp = np.empty(nt, np.int32); me.loop_triangles.foreach_get('polygon_index', tp)
    part = np.empty(len(me.polygons), np.int32); me.attributes['part'].data.foreach_get('value', part)
    uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers['UVMap'].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    co = get_co(ob) + ORIGIN
    nn = np.empty(len(co) * 3, np.float32); me.vertices.foreach_get('normal', nn); nn = nn.reshape(-1, 3)
    PI = -np.ones((TEX, TEX), np.int32)
    BW = np.zeros((TEX, TEX, 3), np.float32)
    T = uv[tl] * TEX - 0.5     # pixel centres at integers
    for i in range(nt):
        t = T[i]
        x0 = int(max(0, math.floor(t[:, 0].min() - 0.5))); x1 = int(min(TEX - 1, math.ceil(t[:, 0].max() + 0.5)))
        y0 = int(max(0, math.floor(t[:, 1].min() - 0.5))); y1 = int(min(TEX - 1, math.ceil(t[:, 1].max() + 0.5)))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1 - w0 - w1
        e = 0.7 / max(1.0, math.sqrt(abs(den)))
        m = (w0 > -e) & (w1 > -e) & (w2 > -e)
        if not m.any():
            continue
        PI[ys[m], xs[m]] = i
        BW[ys[m], xs[m]] = np.stack([w0[m], w1[m], w2[m]], 1)
    filled = PI >= 0
    idx = PI[filled]
    bw = np.clip(BW[filled], 0, 1); bw /= np.maximum(bw.sum(1, keepdims=True), 1e-9)
    P = (co[tv[idx]] * bw[:, :, None]).sum(1)
    N = (nn[tv[idx]] * bw[:, :, None]).sum(1); N /= np.maximum(np.linalg.norm(N, axis=1), 1e-9)[:, None]
    UV = (uv[tl[idx]] * bw[:, :, None]).sum(1)
    if with_bary:
        return filled, part[tp[idx]], P, N, UV, tv[idx], bw
    return filled, part[tp[idx]], P, N, UV


REF_DIR = os.path.join(ROOT, 'boards', 'saki-ref')
# landmarks: 3D spec on the model (head frame) and pixel positions measured on the reference images
REF_LANDMARKS = [
    ('eyeR_pup', ('e', 1), {'front': (422.5, 321.5), 'side': (355, 305), '34': (485, 321.5)}),
    ('eyeL_pup', ('e', -1), {'front': (577.5, 321.5), '34': (337.5, 330)}),
    ('eyeR_out', ('f', 0.0473, 0.0018), {'front': (382.5, 317.5), 'side': (377.5, 302.5), '34': (525, 317.5)}),
    ('eyeR_in', ('f', 0.0177, -0.0015), {'front': (455, 325), '34': (445, 330)}),
    ('eyeL_out', ('f', -0.0473, 0.0018), {'front': (620, 317.5), '34': (305, 325)}),
    ('eyeL_in', ('f', -0.0177, -0.0015), {'front': (545, 326), '34': (362.5, 339)}),
    ('browR', ('f', 0.034, 0.0186), {'front': (415, 275), '34': (480, 270)}),
    ('browL', ('f', -0.034, 0.0186), {'front': (580, 272), '34': (335, 282)}),
    ('nose', ('f', 0.0, -0.0345), {'front': (500, 400), 'side': (261, 385), '34': (390, 405)}),
    ('subn', ('f', 0.0, -0.0465), {'front': (500, 420), 'side': (290, 410), '34': (407.5, 427.5)}),
    ('alaR', ('f', 0.0148, -0.0405), {'front': (462, 415), '34': (435, 420)}),
    ('alaL', ('f', -0.0148, -0.0405), {'front': (537, 415)}),
    ('mouthR', ('f', 0.0210, -0.0595), {'front': (432, 475), 'side': (352, 465), '34': (465, 477.5)}),
    ('mouthL', ('f', -0.0210, -0.0595), {'front': (557, 475), '34': (355, 482.5)}),
    ('ulip', ('f', 0.0, -0.0565), {'front': (500, 463), 'side': (286, 450), '34': (400, 465)}),
    ('llip', ('f', 0.0, -0.0700), {'front': (500, 497), 'side': (294, 482), '34': (405, 507.5)}),
    ('chin', ('f', 0.0, -0.0900), {'front': (500, 552), 'side': (307, 540), '34': (410, 577.5)}),
    ('chinb', ('f', 0.0, -0.1010), {'front': (500, 575), 'side': (332, 564)}),
    ('earR', ('ear', 1), {'front': (318, 365), 'side': (597, 343), '34': (665, 360)}),
    ('earL', ('ear', -1), {'front': (688, 365)}),
    ('nasion', ('f', 0.0, 0.002), {'side': (297.5, 300)}),
    ('forehead', ('f', 0.0, 0.037), {'side': (295, 210)}),
]


class RefProjector:
    """Camera-projection of the reference photos onto the head: per view an affine camera fitted to
    landmarks plus a thin-plate correction, soft view masks, hair/background rejection, colour matching."""
    VIEWS = {'front': ('face-front.png', V(0, 1, 0), 1.3), '34': ('face-34.png', nrm(V(0.6, 0.8, 0)), 1.0),
             'side': ('face-side.png', V(1, 0, 0), 0.8)}

    def __init__(self, S):
        from scipy.interpolate import RBFInterpolator
        from scipy import ndimage
        self.ok = all(os.path.exists(os.path.join(REF_DIR, f)) for f, _, _ in self.VIEWS.values())
        if not self.ok:
            log('reference images missing: procedural head skin only')
            return
        pts = {}
        for name, spec, _ in REF_LANDMARKS:
            pts[name] = self.surface_point(S, spec)
        self.cams = {}
        for v, (fn, dexp, bias) in self.VIEWS.items():
            im = bpy.data.images.load(os.path.join(REF_DIR, fn))
            w, h = im.size
            a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
            img = a.reshape(h, w, 4)[::-1, :, :3].copy()
            bpy.data.images.remove(im)
            R, G, B = img[..., 0], img[..., 1], img[..., 2]
            Lum = 0.3 * R + 0.59 * G + 0.11 * B
            valid = (R > 0.47) & (R - B > 0.14) & (Lum > 0.45)
            valid = ndimage.binary_erosion(valid, iterations=6)
            valid = ndimage.gaussian_filter(valid.astype(np.float32), 14.0)
            valid = sstep(0.55, 0.95, valid)
            X, Y = [], []
            for name, spec, pix in REF_LANDMARKS:
                if v in pix:
                    X.append(pts[name] - HEADC); Y.append(pix[v])
            X = np.array(X); Y = np.array(Y, float)
            Xh = np.hstack([X, np.ones((len(X), 1))])
            A, *_ = np.linalg.lstsq(Xh, Y, rcond=None)          # (4, 2)
            proj = Xh @ A
            res = Y - proj
            tps = RBFInterpolator(proj, res, kernel='thin_plate_spline', smoothing=4.0)
            d = np.cross(A[:3, 0], A[:3, 1]); d = d / np.linalg.norm(d)
            if d @ dexp < 0:
                d = -d
            log('ref view %s: %d landmarks, affine rms %.1f px' % (v, len(X), np.sqrt((res ** 2).sum(1).mean())))
            vm = (valid > 0.5).astype(np.float32)
            sig = 5.0     # keep only fine skin detail (freckles, pores, faint blemishes); the shading stays out
            den = ndimage.gaussian_filter(vm, sig)
            low = np.stack([ndimage.gaussian_filter(img[..., k] * vm, sig) for k in range(3)], -1) / np.maximum(den, 1e-3)[..., None]
            ratio = np.clip(img / np.maximum(low, 1e-3), 0.82, 1.18)
            self.cams[v] = dict(img=ratio, valid=valid, A=A, tps=tps, d=d, bias=bias)

    @staticmethod
    def surface_point(S, spec):
        if spec[0] == 'e':
            c = EYE_C[0 if spec[1] < 0 else 1]
            return c + V(0, EYE_R, 0)
        if spec[0] == 'ear':
            o = HEADC + V(spec[1] * 0.2, -0.036, -0.016); dvec = V(-spec[1], 0, 0)   # ear
        else:
            o = HEADC + V(spec[1], 0.2, spec[2]); dvec = V(0, -1, 0)
        lo, hi = 0.0, 0.2
        for _ in range(40):
            m = 0.5 * (lo + hi)
            if S.eval_points((o + m * dvec)[None])[0] > 0:
                lo = m
            else:
                hi = m
        return o + lo * dvec

    def sample(self, v, Ph, Nh):
        from scipy import ndimage
        c = self.cams[v]
        Xh = np.hstack([Ph, np.ones((len(Ph), 1))])
        uv = Xh @ c['A']
        uv = uv + c['tps'](uv)
        h, w = c['valid'].shape
        coords = [uv[:, 1], uv[:, 0]]
        col = np.stack([ndimage.map_coordinates(c['img'][..., k], coords, order=1, mode='nearest') for k in range(3)], 1)
        val = ndimage.map_coordinates(c['valid'], coords, order=1, mode='constant', cval=0.0)
        inside = (uv[:, 0] > 2) & (uv[:, 0] < w - 3) & (uv[:, 1] > 2) & (uv[:, 1] < h - 3)
        wgt = np.clip(Nh @ c['d'] - 0.2, 0, 1) ** 1.5 * np.clip(val, 0, 1) * inside * c['bias']
        return col, wgt

    def apply(self, P, N, col):
        """P, N: skin texels (modelling frame); col: procedural colour. Returns blended colour."""
        if not self.ok:
            return col
        Ph = P - HEADC
        acc = np.zeros((len(P), 3)); wsum = np.zeros(len(P))
        cols = {}
        for v in ('front',):     # side photos disagree in shading; the front alone covers the face
            if v == 'front':
                c, wgt = self.sample(v, Ph, N)
            else:   # the right-side photos also serve the left side, mirrored
                mir = Ph[:, 0] < 0
                Pm = Ph.copy(); Nm = N.copy()
                Pm[mir, 0] *= -1; Nm[mir, 0] *= -1
                c, wgt = self.sample(v, Pm, Nm)
            cols[v] = (c, wgt)
        cf, wf = cols['front']
        for v, (c, wgt) in cols.items():
            if v != 'front':   # side photos only where the front photo cannot see
                wgt = wgt * np.clip(1 - wf / 0.25, 0, 1)
            acc += c * wgt[:, None]; wsum += wgt
        # photo detail (freckles, lips, lid shading) as a ratio over the procedural skin tone
        ratio = acc / np.maximum(wsum, 1e-6)[:, None]
        proj = np.clip(col * ratio, 0, 1)
        # a soft oval over the face (no hard patch edges), front-facing only
        oval = ((Ph[:, 0] / 0.056) ** 2 + ((Ph[:, 2] + 0.048) / 0.058) ** 2)
        alpha = sstep(1.0, 0.55, oval) * sstep(0.25, 0.65, N @ V(0, 1, 0)) * np.clip(wsum / 0.5, 0, 1)
        alpha *= 1 - sstep(0.022, 0.005, np.abs(Ph[:, 0])) * sstep(-0.024, -0.010, Ph[:, 2])   # hair strand over the bridge in the photo
        for i, s in enumerate((-1, 1)):       # eyes and lids: procedural (lid line, lashes match the geometry)
            c = EYE_C[i]
            e = ((P[:, 0] - c[0]) / 0.024) ** 2 + ((P[:, 2] - c[2] + 0.001) / 0.013) ** 2
            alpha *= np.where(P[:, 1] > c[1] - 0.01, sstep(0.75, 1.15, e), 1.0)
        # mouth and nostrils: procedural too (the photo's features do not sit exactly on the geometry's)
        em = (Ph[:, 0] / 0.030) ** 2 + ((Ph[:, 2] - MOUTH_Z) / 0.012) ** 2
        en = (Ph[:, 0] / 0.018) ** 2 + ((Ph[:, 2] + 0.040) / 0.008) ** 2
        alpha *= sstep(0.8, 1.6, em) * sstep(0.8, 1.6, en)
        alpha *= 0.75
        log('projection: %.0f%% of head texels from the photos' % (100 * (alpha > 0.5).mean()))
        return proj, alpha


def write_png(path, rgb):
    """Minimal PNG writer: per-row best of the five filters, zlib level 9."""
    import zlib, struct
    h, w, c = rgb.shape
    x = rgb.reshape(h, w * c).astype(np.int16)
    up = np.vstack([np.zeros((1, w * c), np.int16), x[:-1]])
    left = np.hstack([np.zeros((h, c), np.int16), x[:, :-c]])
    ul = np.hstack([np.zeros((h, c), np.int16), up[:, :-c]])
    pa = np.abs(up - ul); pb = np.abs(left - ul); pc = np.abs(left + up - 2 * ul)
    paeth = np.where((pa <= pb) & (pa <= pc), left, np.where(pb <= pc, up, ul))
    cands = [x, x - left, x - up, x - (left + up) // 2, x - paeth]
    cands = [(cd % 256).astype(np.uint8) for cd in cands]
    cost = np.stack([np.abs(cd.astype(np.int8).astype(np.int16)).sum(1) for cd in cands], 1)
    best = cost.argmin(1)
    raw = bytearray()
    for r in range(h):
        raw.append(int(best[r])); raw += cands[best[r]][r].tobytes()
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def vertex_ao(ob, S, hair_grid=None):
    """Cheap SDF ambient occlusion per vertex (rest pose, modelling frame): 0 open .. 1 occluded."""
    co = get_co(ob) + ORIGIN
    nn = np.empty(len(co) * 3, np.float32); ob.data.vertices.foreach_get('normal', nn)
    nn = nn.reshape(-1, 3).astype(np.float64)
    occ = np.zeros(len(co))
    tot = 0.0
    for d, w in ((0.006, 1.0), (0.014, 0.7), (0.028, 0.45), (0.05, 0.2)):
        q = co + nn * d
        f = S.eval_points(q)
        if hair_grid is not None:
            from scipy import ndimage
            F, glo, h = hair_grid
            fh = ndimage.map_coordinates(F, ((q - glo) / h).T, order=1, mode='constant', cval=1.0)
            f = np.minimum(f, fh)
        occ += w * np.clip((d - f) / d, 0, 1)
        tot += w
    return np.clip(occ / tot, 0, 1)


def paint_atlas(ob, ao=None, proj=None):
    t = time.time()
    filled, part, P, N, UV, TV, BW = rasterize(ob, with_bary=True)
    log('raster %d texels %.1fs' % (filled.sum(), time.time() - t))
    col = np.zeros((len(P), 3))
    fns = {'skin': paint_skin, 'eyes': paint_eye, 'hair': paint_hair, 'strand': paint_strand, 'top': paint_top, 'wrap': paint_wrap,
           'shorts': paint_shorts, 'leather': paint_leather, 'wood': paint_wood, 'metal': paint_metal,
           'cape': paint_cape, 'sole': paint_sole}
    hgt = np.zeros(len(P))
    for k, fn in fns.items():
        m = part == PARTS.index(k)
        if m.any():
            col[m] = fn(P[m], N[m], UV[m])
            if k in ('hair', 'strand'):
                hgt[m] = HAIR_HEIGHT['last']
    if proj is not None and proj.ok:
        from scipy import ndimage
        m = (part == PARTS.index('skin')) & (P[:, 2] > 1.33)
        pc, al = proj.apply(P[m], N[m], col[m])
        fy, fx = np.nonzero(filled)
        fy, fx = fy[m], fx[m]
        A = np.zeros((TEX, TEX), np.float32); Mk = np.zeros((TEX, TEX), np.float32)
        A[fy, fx] = al; Mk[fy, fx] = 1
        sig = 2.5 * TEX / 1024
        Ab = ndimage.gaussian_filter(A, sig) / np.maximum(ndimage.gaussian_filter(Mk, sig), 1e-4)
        col[m] = mixc(col[m], pc, np.clip(Ab[fy, fx], 0, 1))
    if ao is not None:
        ao_body, ao_hair = ao
        a = (ao_body[TV] * BW).sum(1)
        ah = (ao_hair[TV] * BW).sum(1)
        hm = part == PARTS.index('hair')
        a[hm] = ah[hm]
        facem = (part == PARTS.index('skin')) & (P[:, 2] > 1.40) & (P[:, 1] > -0.01)
        a[facem] *= 0.35
        strength = np.zeros(len(PARTS))
        for k, v in (('skin', 0.24), ('hair', 0.45), ('strand', 0.30), ('top', 0.30), ('wrap', 0.30), ('shorts', 0.30),
                     ('leather', 0.2), ('sole', 0.2)):
            strength[PARTS.index(k)] = v
        shade = 1 - strength[part] * a ** 0.8
        col *= shade[:, None]
    bad = ~np.isfinite(col).all(1)
    if bad.any():
        log('paint: %d NaN texels' % bad.sum())
        col[bad] = 0.5
    img = np.zeros((TEX, TEX, 3), np.float32)
    img[filled] = col
    from scipy import ndimage
    _, (iy, ix) = ndimage.distance_transform_edt(~filled, return_indices=True)
    img = img[iy, ix]
    # quantise lightly and write a well-compressed PNG ourselves (rows top-down)
    q = np.clip(np.round(img * 255), 0, 255).astype(np.int32)
    q = np.clip((q // 4) * 4 + 2, 0, 255).astype(np.uint8)
    import tempfile
    path = os.path.join(tempfile.mkdtemp(prefix='saki_'), 'saki_atlas.png')
    write_png(path, q[::-1])
    im = bpy.data.images.load(path)
    im.name = 'saki_atlas'
    im.colorspace_settings.name = 'sRGB'
    im.pack()
    log('atlas png %.0f KB' % (os.path.getsize(path) / 1024))
    import shutil
    shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    # hair normal map from the streak height (tangent space = UV axes); flat elsewhere
    hm = np.isin(part, [PARTS.index('hair'), PARTS.index('strand')])
    H = np.zeros((TEX, TEX), np.float32); M = np.zeros((TEX, TEX), bool)
    fy, fx = np.nonzero(filled)
    H[fy[hm], fx[hm]] = hgt[hm]; M[fy[hm], fx[hm]] = True
    Mi = ndimage.binary_erosion(M, iterations=1)
    gx = np.zeros_like(H); gy = np.zeros_like(H)
    gx[:, 1:-1] = (H[:, 2:] - H[:, :-2]) * 0.5; gy[1:-1] = (H[2:] - H[:-2]) * 0.5
    gx[~Mi] = 0; gy[~Mi] = 0
    H = ndimage.gaussian_filter(H, 0.7) * Mi
    k = 0.32
    nmap = np.stack([-gx * k, -gy * k, np.ones_like(H)], -1)
    nmap = nmap.reshape(TEX // 2, 2, TEX // 2, 2, 3).mean((1, 3))       # 1024²
    nmap /= np.linalg.norm(nmap, axis=-1, keepdims=True)
    q = np.clip(np.round((nmap * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    path = os.path.join(tempfile.mkdtemp(prefix='saki_'), 'saki_hair_normal.png')
    write_png(path, q[::-1])
    nim = bpy.data.images.load(path)
    nim.name = 'saki_hair_normal'
    nim.colorspace_settings.name = 'Non-Color'
    nim.pack()
    log('hair normal map png %.0f KB' % (os.path.getsize(path) / 1024))
    shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    im['normal'] = nim.name
    log('atlas painted %.1fs' % (time.time() - t))
    return im


def make_materials(ob, img):
    me = ob.data
    names = []
    for p in PARTS:
        if MATS[p][0] not in names:
            names.append(MATS[p][0])
    mats = {}
    for nm in names:
        m = bpy.data.materials.new(nm)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = img; tx.interpolation = 'Linear'
        nt.links.new(tx.outputs['Color'], bsdf.inputs['Base Color'])
        rough = {'Skin': 0.7, 'Eyes': 0.3, 'Hair': 0.45, 'Cloth': 0.9, 'Leather': 0.65, 'Cape': 0.9}[nm]
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = 0.0
        m.use_backface_culling = nm not in ('Cape', 'Hair')
        if nm == 'Hair' and img.get('normal') in bpy.data.images:
            nt_ = nt.nodes.new('ShaderNodeTexImage'); nt_.image = bpy.data.images[img['normal']]
            nm_ = nt.nodes.new('ShaderNodeNormalMap'); nm_.inputs['Strength'].default_value = 1.0
            nt.links.new(nt_.outputs['Color'], nm_.inputs['Color'])
            nt.links.new(nm_.outputs['Normal'], bsdf.inputs['Normal'])
        mats[nm] = m
        me.materials.append(m)
    part = np.empty(len(me.polygons), np.int32); me.attributes['part'].data.foreach_get('value', part)
    mi = np.array([names.index(MATS[PARTS[p]][0]) for p in part], np.int32)
    me.polygons.foreach_set('material_index', mi)


# ---------------------------------------------------------------- animation
def Rx(d): return Quaternion((1, 0, 0), math.radians(d))
def Ry(d): return Quaternion((0, 1, 0), math.radians(d))
def Rz(d): return Quaternion((0, 0, 1), math.radians(d))


def vnorm(*a):
    return Vector(a).normalized()


def toward(d, target, deg):
    d = Vector(d).normalized(); t = Vector(target).normalized()
    ax = d.cross(t)
    if ax.length < 1e-6:
        return d
    return (Quaternion(ax.normalized(), math.radians(deg)) @ d).normalized()


def q_aim(rest_d, rest_u, new_d, new_u):
    def frame(d, u):
        d = Vector(d).normalized(); u = Vector(u); u = (u - d * u.dot(d)).normalized(); w = d.cross(u)
        return Matrix((d, u, w)).transposed()
    return (frame(new_d, new_u) @ frame(rest_d, rest_u).transposed()).to_quaternion()


def rest_frames():
    T = bone_table()
    out = {}
    for b, (h, t, p) in T.items():
        d = Vector(nrm(t - h))
        if b.startswith(('upperarm', 'forearm', 'hand')):
            u = Vector(SK.palm_n(-1 if b.endswith('.L') else 1))
        elif b.startswith('foot'):
            u = Vector((0, 0, 1))
        elif b.startswith(('thigh', 'shin')):
            u = Vector((0, 1, 0))
        else:
            u = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((0, 0, 1))
        out[b] = (d, u)
    return out


RF = None


def aim(b, d, u):
    return q_aim(RF[b][0], RF[b][1], Vector(d), Vector(u))


def hair_rot(kind, t):
    """Ponytail chain (body frame): fly streams back over her back with a wave travelling down it;
    sit hangs down her back with a small sway; stand hangs straight."""
    r = {}
    for k, b in enumerate(HAIR_BONES):
        if kind == 'fly':     # short tail flicks up and back, a lively 2-beat wave (2 waves per 2 s loop)
            w = 2 * math.pi * t / 1.0
            d = Rx(14 * math.sin(w - 1.4 * k)) @ Ry(8 * math.sin(w - 1.4 * k + 0.9)) @ vnorm(0, -0.62 + 0.22 * k, -1)
        elif kind == 'sit':
            w = 2 * math.pi * t / 3.0
            d = Ry(3.0 * math.sin(w - 0.7 * k)) @ Rx(2.0 * math.sin(w - 0.7 * k + 1.0)) @ vnorm(0, -0.12, -1)
        elif kind in ('walk', 'run'):   # swings side to side twice a stride, a little behind her as she moves
            P, A, back = (WALK_T, 5.0, -0.12) if kind == 'walk' else (RUN_T, 9.0, -0.35)
            w = 2 * math.pi * t / P
            d = Ry(A * math.sin(2 * w - 0.8 * k)) @ Rx(0.6 * A * math.sin(2 * w - 0.8 * k + 0.9)) @ vnorm(0, back, -1)
        else:
            w = 2 * math.pi * t / 3.0
            d = Ry(1.6 * math.sin(w - 0.6 * k)) @ Rx(1.0 * math.sin(w - 0.6 * k + 0.7)) @ vnorm(0, -0.05, -1)
        r[b] = aim(b, d, (0, 1, 0))
    return r


def pose_fly(t):
    w = 2 * math.pi * t / 2.0
    r = {'spine': Rx(6), 'chest': Rx(14 + 1.0 * math.sin(w)), 'neck': Rx(36), 'head': Rx(72 + 2 * math.sin(w + 1))}
    for s, sx in ((-1, '.L'), (1, '.R')):
        el = math.radians(15 + 5 * math.sin(w))
        du = vnorm(s * math.cos(el), -0.30, -math.sin(el))
        r['shoulder' + sx] = Ry(-s * 6) @ Rx(6)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (0, 1, 0))
        df = toward(du, (0, 0.35, -1), 7 + 5 * math.sin(w + 0.6))
        dh = toward(df, (0, 0.2, -1), 4)
        if s > 0:   # right hand: palm toward the direction of flight, open, to be held
            r['forearm' + sx] = aim('forearm' + sx, df, (0, 0.75, 0.66))
            r['hand' + sx] = aim('hand' + sx, toward(df, (0, 0, 1), 6), (0, 0.15, 1))
        else:
            r['forearm' + sx] = aim('forearm' + sx, df, (0, 1, 0))
            r['hand' + sx] = aim('hand' + sx, dh, (0, 1, 0))
        ph = 0.0 if s < 0 else math.pi
        dt = Rx(-6 + 5 * math.sin(w + ph)) @ vnorm(s * math.sin(math.radians(13)), 0, -math.cos(math.radians(13)))
        r['thigh' + sx] = aim('thigh' + sx, dt, (0, 1, 0))
        ds = toward(dt, (0, -1, 0), 5 + 6 * (0.5 + 0.5 * math.sin(w + ph + 0.9)))
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        dfo = toward(ds, (0, 1, 0), 28)
        r['foot' + sx] = aim('foot' + sx, dfo, (0, 1, 0))
    r.update(hair_rot('fly', t))
    return {'root_rot': Rx(-90) @ Rz(2 * math.sin(w)), 'rot': r}


def pose_stand(t):
    w = 2 * math.pi * t / 3.0
    b = math.sin(w)
    r = {'hips': Rz(-4) @ Ry(-7), 'spine': Ry(2), 'chest': Rz(-2) @ Ry(4) @ Rx(1.2 * b), 'neck': Ry(2) @ Rx(-3),
         'head': Rz(6 + 2.5 * math.sin(w + 0.5)) @ Ry(4) @ Rx(-7)}
    for s, sx in ((-1, '.L'), (1, '.R')):
        r['shoulder' + sx] = Ry(s * 3) @ Rx(0.6 * b)
        du = vnorm(s * 0.17, -0.10 + 0.006 * b, -1)
        df = vnorm(s * 0.11, -0.03 + 0.01 * b, -1)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 0.25, 0))
        r['forearm' + sx] = aim('forearm' + sx, df, (-s, 0.4, 0))
        r['hand' + sx] = aim('hand' + sx, toward(df, (s * 0.2, 0.3, -1), 4), (-s, 0.45, 0))
    # weight on the right leg, left leg relaxed
    r['thigh.R'] = aim('thigh.R', vnorm(-0.02, 0.0, -1), (0, 1, 0))
    r['shin.R'] = aim('shin.R', vnorm(-0.01, -0.02, -1), (0, 1, 0))
    r['thigh.L'] = aim('thigh.L', vnorm(-0.11, 0.12, -1), (-0.15, 1, 0))
    r['shin.L'] = aim('shin.L', vnorm(-0.07, -0.08, -1), (-0.15, 1, 0))
    for sx, yaw in (('.L', 14), ('.R', -6)):
        r['foot' + sx] = Rz(yaw) @ (Rx(8) if sx == '.L' else Quaternion())
    r.update(hair_rot('stand', t))
    return {'rot': r, 'ground': 'shin.R', 'cape_off': ((0.02, -0.07, -0.02), (0.05, -0.16, 0.03))}


WALK_T, RUN_T = 32 / 30, 20 / 30    # stride periods (s), whole even frame counts so the exported loop (every 2nd frame) closes


def gait(t, run=False):
    """A walk (or run) cycle in place: legs swing about the hips, the knee folds in the swing, the foot rolls heel to
    toe, the arms swing against the legs, the hips and chest twist against each other. The lower ankle is pinned to
    the ground by bake_action ('ground' lists both shins)."""
    P = RUN_T if run else WALK_T
    w = 2 * math.pi * t / P
    r = {}
    lean = 9 if run else 2.5
    r['hips'] = Rz((7 if run else 5) * math.sin(w)) @ Ry((2 if run else 3) * math.sin(w + math.pi / 2)) @ Rx(-lean * 0.4)
    r['spine'] = Rx(-lean * 0.5) @ Rz(-2.0 * math.sin(w))
    r['chest'] = Rx(-lean * 0.4 + 1.0 * math.sin(2 * w)) @ Rz(-(6 if run else 4) * math.sin(w))
    r['neck'] = Rx(lean * 0.6) @ Rz(1.5 * math.sin(w))
    r['head'] = Rx(-3 + lean * 0.5 + 1.2 * math.sin(2 * w + 0.6)) @ Rz(1.5 * math.sin(w))
    for s, sx in ((-1, '.L'), (1, '.R')):
        ph = w if s < 0 else w + math.pi                   # left leg forward at w = pi/2
        phw = math.atan2(math.sin(ph), math.cos(ph))
        if run:
            a = 30 * math.sin(ph) + 6
            k = 18 + 88 * max(0.0, math.cos(ph + 0.45)) ** 1.6
        else:
            a = 22 * math.sin(ph)
            k = 6 + 52 * max(0.0, math.cos(ph + 0.35)) ** 2.2
        dt = vnorm(s * 0.035, math.sin(math.radians(a)), -math.cos(math.radians(a)))
        r['thigh' + sx] = aim('thigh' + sx, dt, (0, 1, 0))
        ds = toward(dt, (0, -1, 0), k)
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        # heel to toe: flat in the stance, toes down at the push-off, up at the heel strike
        td = (40 if run else 30) * math.exp(-((phw + 1.25) / 0.55) ** 2)
        tu = (8 if run else 14) * math.exp(-((phw - 1.45) / 0.5) ** 2)
        df = Rx(tu - td) @ vnorm(s * 0.08, 0.87, -0.50)
        r['foot' + sx] = aim('foot' + sx, df, (0, 0, 1))
        # the arm swings with the opposite leg
        b = (28 if run else 16) * math.sin(ph + math.pi) + (-6 if run else 2)
        r['shoulder' + sx] = Ry(s * 3) @ Rx(-0.15 * b)
        du = vnorm(s * (0.22 if run else 0.16), math.sin(math.radians(b)), -math.cos(math.radians(b)))
        el = (72 if run else 14) + (6 if run else 10) * max(0.0, math.sin(math.radians(b)) * 2)
        dfa = toward(du, (0, 1, 0.15), el)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 0.25, 0))
        r['forearm' + sx] = aim('forearm' + sx, dfa, (-s, 0.4, 0))
        r['hand' + sx] = aim('hand' + sx, toward(dfa, (s * 0.2, 0.3, -1), 4 if not run else 20), (-s, 0.45, 0))
    r.update(hair_rot('run' if run else 'walk', t))
    bob = (0.035 * math.cos(2 * w)) if run else 0.0
    return {'rot': r, 'ground': ['shin.L', 'shin.R'], 'bob': bob, 'cape_off': ((0.02, -0.09, -0.02), (0.05, -0.22 if run else -0.17, 0.03))}


def pose_walk(t):
    return gait(t, False)


def pose_run(t):
    return gait(t, True)


SEAT_Z = 0.770


def pose_sit(t):
    w = 2 * math.pi * t / 3.0
    b = math.sin(w)
    r = {'hips': Rx(8), 'spine': Rx(2), 'chest': Rx(-1 + 1.2 * b), 'neck': Rx(-3),
         'head': Rz(17 + 3 * math.sin(w + 0.4)) @ Ry(-3) @ Rx(-7 + 1.5 * math.sin(w + 1.3))}
    pos = {}
    for s, sx in ((-1, '.L'), (1, '.R')):
        r['shoulder' + sx] = Ry(-s * 4) @ Rx(0.6 * b)
        du = vnorm(s * 0.12, -0.10, -1)
        df = vnorm(s * 0.05, -0.10, -1)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 1, 0))
        r['forearm' + sx] = aim('forearm' + sx, df, (0, 1, 0))
        r['hand' + sx] = aim('hand' + sx, vnorm(s * 0.25, 0.97, -0.05), (0, 0, -1))
        r['thigh' + sx] = aim('thigh' + sx, vnorm(s * 0.10, 1, -0.06), (0, 0, 1))
        sw = 5 * math.sin(w + (0 if s < 0 else 2.2))
        ds = Rx(sw) @ vnorm(s * 0.03, 0.10, -1)
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        r['foot' + sx] = aim('foot' + sx, Rx(sw) @ vnorm(s * 0.10, 0.62, -0.78), Rx(sw) @ Vector((0, 0.78, 0.62)))
    r.update(hair_rot('sit', t))
    return {'rot': r, 'pos': pos}


def solve(rig, pose):
    R = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    Qr = pose.get('root_rot', Quaternion()); Lr = Vector(pose.get('root_loc', (0, 0, 0)))
    rot = pose.get('rot', {}); pos = pose.get('pos', {})
    rh = R['root'].translation.copy()
    P, out = {}, {}
    for name in BONE_ORDER:
        bone = rig.data.bones[name]
        Rb = R[name]
        if name == 'root':
            Pb = Matrix.Translation(rh + Lr) @ (Qr @ Rb.to_quaternion()).to_matrix().to_4x4()
            L = Rb.inverted() @ Pb
        else:
            par = bone.parent.name
            if name.startswith('cape') and WING_REST:
                wr = WING_REST[-1 if name.endswith('.L') else 1]
                Kb = lambda b: P[b] @ R[b].inverted()
                a0 = Kb(wr['fo']) @ Vector(wr['A0']); a1 = Kb(wr['sn']) @ Vector(wr['A1'])
                off = pose.get('cape_off')
                if off:   # let the free edge hang away from the wrist/ankle line (slack cloth)
                    sd = -1 if name.endswith('.L') else 1
                    a0 = a0 + Qr @ Vector((sd * off[0][0], off[0][1], off[0][2]))
                    a1 = a1 + Qr @ Vector((sd * off[1][0], off[1][1], off[1][2]))
                am = Vector((0, 0, 0))
                for b, wgt in wr['Amw'].items():
                    am += wgt * (Kb(b) @ Vector(wr['Am']))
                dn = a1 - a0; ln = dn.length; dn.normalize()
                kn = am - a0; kn -= dn * kn.dot(dn)
                q = q_aim(Vector(wr['d']), Vector(wr['k']), dn, kn)
                Pb = Matrix.Translation(a0) @ (q @ Rb.to_quaternion()).to_matrix().to_4x4() @ \
                    Matrix.Diagonal((1.0, ln / wr['L'], 1.0, 1.0))
            else:
                if name in pos:
                    head = rh + Lr + Qr @ (Vector(pos[name]) - rh)
                else:
                    head = P[par] @ (R[par].inverted() @ Rb.translation)
                q = Qr @ rot.get(name, Quaternion())
                Pb = Matrix.Translation(head) @ (q @ Rb.to_quaternion()).to_matrix().to_4x4()
            L = (P[par] @ R[par].inverted() @ Rb).inverted() @ Pb
        P[name] = Pb
        loc, q, sc = L.decompose()
        out[name] = (loc, q, sc)
    return out, P


def bake_action(rig, name, fn, seconds, fps=30):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    nf = int(round(seconds * fps))
    prev = {}
    R = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    for f in range(nf + 1):
        t = (f % nf) / fps
        pose = fn(t)
        out, P = solve(rig, pose)
        if pose.get('ground'):
            # keep the standing foot on the ground (with several candidates, the lower ankle is the standing one)
            gl = pose['ground'] if isinstance(pose['ground'], list) else [pose['ground']]
            dz = None
            for sb in gl:
                ank = (P[sb] @ (R[sb].inverted() @ (R[sb] @ Vector((0, rig.data.bones[sb].length, 0)))))
                rest_ank = R[sb] @ Vector((0, rig.data.bones[sb].length, 0))
                d = rest_ank.z - ank.z
                dz = d if dz is None else max(dz, d)
            pose['root_loc'] = (0, 0, dz + pose.get('bob', 0.0))
            out, P = solve(rig, pose)
        for bn, (loc, q, sc) in out.items():
            pb = rig.pose.bones[bn]
            pb.rotation_mode = 'QUATERNION'
            if bn in prev and prev[bn].dot(q) < 0:
                q = -q
            prev[bn] = q.copy()
            pb.location = loc
            pb.rotation_quaternion = q
            pb.keyframe_insert('location', frame=f, group=bn)
            pb.keyframe_insert('rotation_quaternion', frame=f, group=bn)
            if bn.startswith('cape'):
                pb.scale = sc
                pb.keyframe_insert('scale', frame=f, group=bn)
    act.frame_range = (0, nf)
    act.use_frame_range = True
    tr = rig.animation_data.nla_tracks.new()
    tr.name = name
    st = tr.strips.new(name, 0, act)
    tr.mute = True
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    log('action %s: %d frames' % (name, nf + 1))
    return act


# ---------------------------------------------------------------- previews (EEVEE)
def setup_preview_scene():
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev in ('OPTIX', 'CUDA'):
            try:
                prefs.compute_device_type = dev
                prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == dev
                    sc.cycles.device = 'GPU'
                    break
            except Exception:
                pass
    except Exception:
        pass
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = 800
    sc.render.film_transparent = False
    world = bpy.data.worlds.new('PrevWorld'); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.40, 0.41, 0.43, 1); bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 3.2; sun.data.color = (1.0, 0.90, 0.78); sun.data.angle = math.radians(20)
    sun.rotation_euler = (math.radians(55), 0, math.radians(155))
    sc.collection.objects.link(sun)
    fill = bpy.data.objects.new('Fill', bpy.data.lights.new('Fill', 'SUN'))
    fill.data.energy = 1.3; fill.data.color = (0.80, 0.86, 1.0); fill.data.angle = math.radians(30)
    fill.rotation_euler = (math.radians(70), 0, math.radians(-150))
    sc.collection.objects.link(fill)
    rim = bpy.data.objects.new('Rim', bpy.data.lights.new('Rim', 'SUN'))
    rim.data.energy = 1.5; rim.data.color = (1.0, 0.85, 0.7); rim.data.angle = math.radians(10)
    rim.rotation_euler = (math.radians(60), 0, math.radians(20))
    sc.collection.objects.link(rim)
    try:
        sc.view_settings.view_transform = 'Standard'
        sc.view_settings.look = 'None'
        sc.view_settings.exposure = 0.0
    except Exception:
        pass


def preview(rig, action, frame, cam, target, path, lens=50, box=None, fit=False, roll=0.0, hfrac=0.38):
    """Render a pose. With fit=True, cam is a view direction and the camera frames the posed mesh;
    with fit='head', cam is (direction, distance) from the posed head."""
    sc = bpy.context.scene
    rig.animation_data.action = bpy.data.actions[action] if action else None
    sc.frame_set(frame)
    if fit == 'head':
        pb = rig.pose.bones['head']
        h = rig.matrix_world @ (pb.head + hfrac * (pb.tail - pb.head))
        target = tuple(h)
        cam = tuple(np.array(h) + nrm(np.asarray(cam[0], float)) * cam[1])
    elif fit:
        mesh = [o for o in rig.children if o.type == 'MESH'][0]
        dg = bpy.context.evaluated_depsgraph_get()
        ev = mesh.evaluated_get(dg)
        me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co)
        ev.to_mesh_clear()
        co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        c = (lo + hi) / 2; rad = np.linalg.norm(hi - lo) / 2
        fov = 2 * math.atan(18.0 / lens)
        dist = rad / math.tan(fov / 2) * 1.02
        dv = nrm(np.asarray(cam, float))
        target = tuple(c)
        cam = tuple(c + dv * dist)
    tmp = []
    if box:
        bpy.ops.mesh.primitive_cube_add(size=1, location=box[0])
        b = bpy.context.active_object; b.scale = box[1]
        m = bpy.data.materials.new('box'); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.41, 0.39, 1)
        b.data.materials.append(m); tmp.append(b)
    quick_render(path, cam, target, lens, 800, sc.render.engine, roll=roll)
    for b in tmp:
        bpy.data.objects.remove(b)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)


# ---------------------------------------------------------------- main
BUDGET = {'eye': 320, 'body': 25000, 'hair': 1500, 'top': 700, 'wrap': 1100, 'shorts': 300, 'soles': 240}


def build():
    global RF
    clear_scene()
    body, base_eyes = load_base(2)
    J = repose_arms(body)
    warp_face([body] + base_eyes)
    setup_anatomy(J, base_eyes)
    measure_lids(body)
    S = MeshSDF([body] + base_eyes, SDF_GRIDS).as_sdf()
    hair, cap_info = make_cap(body)
    delete_under_cap(body, cap_info)
    hair_grid = None
    decimate(body, target=64000, sym=True)
    decimate(body, target=BUDGET['body'], vgroup=detail_group(body), vfac=0.4, sym=True)
    body.vertex_groups.clear()
    log('body tris', ntris(body))
    if body.data.validate():
        log('body mesh validated (fixed)')
    co = get_co(body)
    log('face triangles (approx): %d' % int(((co[:, 2] > 1.395) & (co[:, 1] > -0.03)).sum() * 2))
    decimate(hair, target=BUDGET['hair'])
    top, wrap, shorts, sk = make_clothes(S)
    for ob, k in ((top, 'top'), (wrap, 'wrap'), (shorts, 'shorts')):
        decimate(ob, target=BUDGET[k])
    lea = make_leather(S, build_top_sdf(S), sk)
    soles = make_soles(); decimate(soles, target=BUDGET['soles'])
    for e in base_eyes:
        decimate(e, target=BUDGET['eye'])
    activate(base_eyes[0]); base_eyes[1].select_set(True)
    bpy.ops.object.join()
    eyes = bpy.context.active_object; eyes.name = 'Eyes'
    lashes = make_lashes_base()
    fringe = make_fringe(hair, body)
    loose = make_loose_strands(S)
    tail, cord = make_tail()
    capstr = make_cap_strands(hair, body)
    strands = fringe
    activate(fringe); loose.select_set(True); bpy.ops.object.join(); strands = bpy.context.active_object
    cape, wing_info = wing_build(S, build_top_sdf(S), sk)
    for ob, k in ((body, 'skin'), (hair, 'hair'), (top, 'top'), (wrap, 'wrap'), (shorts, 'shorts'),
                  (soles, 'sole'), (eyes, 'eyes'), (cape, 'cape'), (lashes, 'hair'), (strands, 'hair'),
                  (tail, 'hair'), (cord, 'leather'), (capstr, 'strand')):
        set_part(ob, k)
    lp = np.empty(len(lea.data.polygons), np.int32); lea.data.attributes['part'].data.foreach_get('value', lp)
    lea.data.attributes['part'].data.foreach_set('value', np.array([PARTS.index(('leather', 'wood', 'metal')[i]) for i in lp], np.int32))
    objs = [body, hair, top, wrap, shorts, lea, soles, eyes, cape, lashes, strands, tail, cord, capstr]
    for ob in objs:
        shade_smooth(ob)
        if not ob.data.uv_layers:
            ob.data.uv_layers.new(name='UVMap')
        shift_origin(ob)
    log('parts:', ', '.join('%s %d' % (o.name, ntris(o)) for o in objs))
    rig = make_armature()
    RF = rest_frames()
    Wb = body_weights(body, rig)
    weights_set(hair, BONE_ORDER, rigid_weights(hair, 'head'))
    weights_set(eyes, BONE_ORDER, rigid_weights(eyes, 'head'))
    weights_set(lashes, BONE_ORDER, rigid_weights(lashes, 'head'))
    weights_set(strands, BONE_ORDER, rigid_weights(strands, 'head'))
    weights_set(tail, BONE_ORDER, tail_weights(tail))
    weights_set(capstr, BONE_ORDER, rigid_weights(capstr, 'head'))
    Wc = np.zeros((len(cord.data.vertices), len(BONE_ORDER)))
    Wc[:, BONE_ORDER.index('head')] = 0.5; Wc[:, BONE_ORDER.index('hair.001')] = 0.5
    weights_set(cord, BONE_ORDER, Wc)
    for ob in (top, shorts, soles):
        weights_set(ob, BONE_ORDER, transfer_weights(body, Wb, ob))
    weights_set(wrap, BONE_ORDER, wrap_weights(wrap, transfer_weights(body, Wb, wrap)))
    Wl = transfer_weights(body, Wb, lea)
    # rods: rigid on the forearm
    lv = np.empty(len(lea.data.loops), np.int32); lea.data.loops.foreach_get('vertex_index', lv)
    lt = np.empty(len(lea.data.polygons), np.int32); lea.data.polygons.foreach_get('loop_total', lt)
    lp = np.empty(len(lea.data.polygons), np.int32); lea.data.attributes['part'].data.foreach_get('value', lp)
    rod_v = np.unique(lv[np.repeat(lp == PARTS.index('wood'), lt)])
    lco = get_co(lea)
    for i in rod_v:
        sx = '.L' if lco[i, 0] < 0 else '.R'
        Wl[i] = 0; Wl[i, BONE_ORDER.index('forearm' + sx)] = 1
    weights_set(lea, BONE_ORDER, Wl)
    weights_set(cape, BONE_ORDER, fit_wing_weights(rig, wing_info))
    # join everything into the body (keeps its armature modifier and parent)
    activate(body)
    for ob in objs[1:]:
        ob.select_set(True)
    bpy.ops.object.join()
    mesh = bpy.context.active_object
    mesh.name = 'SakiMesh'; mesh.data.name = 'SakiMesh'
    if mesh.data.validate(verbose=True):
        log('mesh validate fixed problems')
    log('total tris', ntris(mesh), 'verts', len(mesh.data.vertices))
    uv_atlas(mesh)
    ao = (vertex_ao(mesh, S), vertex_ao(mesh, S))
    img = paint_atlas(mesh, ao, None if BASE_MODE else RefProjector(S))
    make_materials(mesh, img)
    bake_action(rig, 'fly', pose_fly, 2.0)
    bake_action(rig, 'sit', pose_sit, 3.0)
    bake_action(rig, 'stand', pose_stand, 3.0)
    bake_action(rig, 'walk', pose_walk, WALK_T)
    bake_action(rig, 'run', pose_run, RUN_T)
    bpy.context.scene.render.fps = 30
    return rig, mesh


def export(rig, mesh):
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    activate(rig); mesh.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
        export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
        export_image_format='AUTO', export_skins=True, export_all_influences=False, export_def_bones=False,
        export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
        export_optimize_animation_size=True, export_frame_range=False, export_anim_single_armature=True,
        export_frame_step=2, export_morph=False, export_lights=False, export_cameras=False, export_extras=False)
    log('exported %s (%.0f KB)' % (OUT_GLB, os.path.getsize(OUT_GLB) / 1024))


def previews(rig):
    os.makedirs(PREV_DIR, exist_ok=True)
    setup_preview_scene()
    seat = SEAT_Z - ORIGIN[2]
    preview(rig, 'fly', 30, (0.6, 1.0, 0.45), None, os.path.join(PREV_DIR, 'saki-fly.png'), 58, fit=True)
    preview(rig, 'sit', 45, (2.6, 0.55, 0.15), (0, 0.12, -0.12), os.path.join(PREV_DIR, 'saki-sit.png'), 50,
            box=((0, -0.55, seat - 0.6), (1.6, 1.2, 1.2)))
    preview(rig, 'stand', 45, (0.0, 3.4, 0.05), (0, 0, -0.08), os.path.join(PREV_DIR, 'saki-stand.png'), 50)
    preview(rig, 'stand', 45, (0.35, -1.6, 0.45), (0, 0, 0.42), os.path.join(PREV_DIR, 'saki-back.png'), 50)
    preview(rig, 'stand', 45, ((0.72, 0.68, 0.08), 0.8), None, os.path.join(PREV_DIR, 'saki-face.png'), 85, fit='head')
    # the reference images are mirrored relative to their captions (face-close shows the nose to image-right,
    # face-34 / face-side to image-left), so the cameras below match the pictures, not the words
    preview(rig, None, 0, ((0.42, 0.88, 0.20), 0.6), None, os.path.join(PREV_DIR, 'saki-close.png'), 70, fit='head', roll=8,
            hfrac=0.30)
    if '--gait' in ARGS:
        for nm, fr in (('walk', (0, 8, 16, 24)), ('run', (0, 5, 10, 15))):
            for f in fr:
                preview(rig, nm, f, (2.9, 0.4, 0.05), (0, 0, -0.08), os.path.join(PREV_DIR, 'g-%s-%02d.png' % (nm, f)), 50)
            preview(rig, nm, fr[1], (1.6, 2.4, 0.3), (0, 0, -0.08), os.path.join(PREV_DIR, 'g-%s-34.png' % nm), 50)
    if '--refs' in ARGS or '--extra' in ARGS:
        for nm, dv, ln in (('front', (0, 1, 0.02), 85), ('34', (-0.62, 0.78, 0.04), 85), ('side', (-1, 0, 0.02), 85)):
            preview(rig, None, 0, (dv, 0.9), None, os.path.join(PREV_DIR, 'x-ref-%s.png' % nm), ln, fit='head')
    if '--extra' in ARGS:
        preview(rig, 'fly', 30, (0.1, 0.25, 1.0), None, os.path.join(PREV_DIR, 'x-fly-above.png'), 45, fit=True)
        preview(rig, 'fly', 30, (0.15, 0.3, -1.0), None, os.path.join(PREV_DIR, 'x-fly-below.png'), 45, fit=True)
        preview(rig, 'fly', 30, (1.0, -0.25, 0.35), None, os.path.join(PREV_DIR, 'x-fly-right.png'), 45, fit=True)
        for nm, dv in (('side', (1.0, -0.35, 0.0)), ('sideup', (0.8, -0.35, 0.6)), ('sidedown', (0.8, -0.35, -0.6))):
            c = np.array([0.0, 0.1, 0.0]) + nrm(np.array(dv)) * 1.3
            preview(rig, 'fly', 30, tuple(c), (0.0, 0.1, 0.0), os.path.join(PREV_DIR, 'x-player-%s.png' % nm), 24)
        preview(rig, 'stand', 45, ((0.1, 1.0, 0.05), 0.8), None, os.path.join(PREV_DIR, 'x-face-front.png'), 85, fit='head')
        preview(rig, 'stand', 1, (0.05, 0.85, 0.60), (0, 0, 0.575), os.path.join(PREV_DIR, 'x-face.png'), 90)
        preview(rig, 'stand', 1, (-0.55, 0.62, 0.64), (0, 0.02, 0.575), os.path.join(PREV_DIR, 'x-face34.png'), 90)
        preview(rig, 'stand', 45, (-1.8, -2.6, 0.4), (0, 0, -0.1), os.path.join(PREV_DIR, 'x-back.png'), 50)
        preview(rig, 'fly', 30, (0.0, -1.0, 2.6), (0, 0.1, 0.0), os.path.join(PREV_DIR, 'x-flytop.png'), 35)
        preview(rig, 'sit', 45, (1.2, 1.9, 0.5), (0, 0.15, -0.05), os.path.join(PREV_DIR, 'x-sit34.png'), 50,
                box=((0, -0.55, seat - 0.6), (1.6, 1.2, 1.2)))


def verify():
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=OUT_GLB)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    print('VERIFY file size: %.1f KB' % (os.path.getsize(OUT_GLB) / 1024))
    for a in arms:
        print('VERIFY armature', a.name, 'bones:', [b.name for b in a.data.bones])
    print('VERIFY actions:', [a.name for a in bpy.data.actions])
    for act in bpy.data.actions:
        print('VERIFY   %s frame_range %s' % (act.name, tuple(act.frame_range)))
    tris = 0
    for m in meshes:
        m.data.calc_loop_triangles()
        tris += len(m.data.loop_triangles)
        print('VERIFY mesh', m.name, 'verts', len(m.data.vertices), 'tris', len(m.data.loop_triangles),
              'materials', [s.material.name for s in m.material_slots if s.material],
              'groups', len(m.vertex_groups))
    print('VERIFY triangles total', tris)
    for im in bpy.data.images:
        print('VERIFY image', im.name, tuple(im.size), im.file_format)


if __name__ == '__main__':
    if '--verify' in ARGS:
        verify()
    else:
        rig, mesh = build()
        export(rig, mesh)
        if '--no-previews' not in ARGS:
            previews(rig)
        if '--keep-blend' in ARGS:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PREV_DIR, 'saki.blend'))
        log('done')
