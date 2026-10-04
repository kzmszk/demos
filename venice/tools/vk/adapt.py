"""Convert vatican-kit Mesh objects (polygon soup with material names) into the Venice MeshBuilder."""
import numpy as np
from gen.materials import MAT
from gen.mesh import face_normals

# vatican material names -> venice material ids (heroes add their own names to MAT)
ALIAS = {'stone': 'trim', 'travertine': 'trim', 'marble': 'trim', 'istrian': 'trim', 'glass': 'glass', 'dark': 'dark', 'metal': 'metal', 'bronze': 'metal',
         'brick': 'wall_brick', 'plaster': 'wall_plaster', 'wood': 'wood_raw', 'roof': 'roof', 'lead': 'metal'}

def mat_id(name):
    if name in MAT: return MAT[name]
    if name.startswith('lunette'): return MAT['mosaic_gold']
    return MAT[ALIAS.get(name, 'trim')]

_SUB = {}
def _pattern(n):
    if n in _SUB: return _SUB[n]
    tris = []
    for i in range(n):
        for j in range(n - i):
            tris.append(((i, j), (i + 1, j), (i, j + 1)))
            if i + j < n - 1: tris.append(((i + 1, j), (i + 1, j + 1), (i, j + 1)))
    B = np.zeros((len(tris), 3, 3))
    for t, tri in enumerate(tris):
        for k, (i, j) in enumerate(tri): B[t, k] = ((n - i - j) / n, i / n, j / n)
    _SUB[n] = B; return B

def subdivide(P, I, UV, max_edge):
    """uniform per-triangle subdivision so that big flat faces get interior vertices for the bake."""
    T = P[I]; U = UV[I]
    L = np.max(np.stack([np.linalg.norm(T[:, 1] - T[:, 0], axis=1), np.linalg.norm(T[:, 2] - T[:, 1], axis=1), np.linalg.norm(T[:, 0] - T[:, 2], axis=1)], 1), axis=1)
    nsub = np.clip(np.ceil(L / max_edge), 1, 24).astype(int)
    if nsub.max() == 1: return P, I, UV
    outP, outU = [], []
    for n in np.unique(nsub):
        sel = np.where(nsub == n)[0]
        B = _pattern(int(n))
        outP.append(np.einsum('kcb,tbx->tkcx', B, T[sel]).reshape(-1, 3, 3))
        outU.append(np.einsum('kcb,tbx->tkcx', B, U[sel]).reshape(-1, 3, 2))
    P2 = np.concatenate(outP).reshape(-1, 3); U2 = np.concatenate(outU).reshape(-1, 2)
    I2 = np.arange(len(P2)).reshape(-1, 3)
    return P2, I2, U2

def weld(P, I, UV, eps=1e-4):
    """merge coincident corners (same position and uv) — flat groups only, normals come from faces."""
    key = np.concatenate([np.round(P / eps), np.round(UV / eps)], axis=1).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return P[first], inv.reshape(-1)[I], UV[first]

def to_builder(m, mb, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), M=None, uvscale=1.0, matmap=None, max_edge=2.0):
    """m: vk.geom.Mesh. Triangulates faces (fan), keeps explicit UVs or makes planar world UVs,
    smooth faces share averaged normals per (vertex, material)."""
    V = np.array(m.V, np.float64)
    if M is not None and len(V): V = V @ M[:3, :3].T + M[:3, 3]
    groups = {}
    for fi, f in enumerate(m.F):
        if len(f) < 3: continue
        name = m.M[fi]
        if matmap and name in matmap: name = matmap[name]
        groups.setdefault((name, bool(m.S[fi])), []).append(fi)
    for (name, smooth), fis in groups.items():
        mid = mat_id(name)
        P = []; UV = []; I = []; smooth_key = []
        for fi in fis:
            f = m.F[fi]; uv = m.UV[fi]
            pts = V[f]
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            for k in range(2, len(f) - 1):
                n2 = np.cross(pts[k] - pts[0], pts[k + 1] - pts[0])
                if np.linalg.norm(n2) > np.linalg.norm(n): n = n2
            ln = np.linalg.norm(n); n = n / ln if ln > 0 else np.array([0, 0, 1.0])
            if uv is None:
                a = np.argmax(np.abs(n))
                ax = [(1, 2), (0, 2), (0, 1)][a]
                uvs = pts[:, ax] * uvscale
            else:
                uvs = np.array(uv, np.float64)
            base = len(P)
            for k in range(len(f)):
                P.append(pts[k]); UV.append(uvs[k]); smooth_key.append(f[k])
            for k in range(1, len(f) - 1):
                I.append([base, base + k, base + k + 1])
        P = np.array(P); I = np.array(I, np.int64); UV = np.array(UV)
        if not smooth:
            P, I, UV = subdivide(P, I, UV, max_edge)
            P, I, UV = weld(P, I, UV)
            smooth_key = list(range(len(P)))
        fn = face_normals(P, I)
        if smooth:
            # average face normals over the original shared vertex ids
            keys = np.array(smooth_key); acc = {}
            for t, tri in enumerate(I):
                w = np.linalg.norm(np.cross(P[tri[1]] - P[tri[0]], P[tri[2]] - P[tri[0]]))
                for k in tri: acc.setdefault(keys[k], np.zeros(3)); acc[keys[k]] += fn[t] * max(w, 1e-9)
            N = np.array([acc[k] / max(np.linalg.norm(acc[k]), 1e-9) for k in keys])
            mb.add(P, I, N=N, UV=UV, mat=mid, c0=c0, c1=c1)
        else:
            from gen.mesh import vertex_normals
            mb.add(P, I, N=vertex_normals(P, I), UV=UV, mat=mid, c0=c0, c1=c1)
