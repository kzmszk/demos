"""Decompose every PLATEAU building into stacked prisms (2.5D wedding cakes) -> work/prisms.json.
Run with the kyoto-assets venv python (needs shapely).  Also writes the Mori Tower plan outline.
"""
import json, sys, math
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box as sbox
from shapely.ops import unary_union
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import lib

objs = lib.read_obj(lib.SRC + 'buildings.obj')
meta = lib.meta()
G = lib.Ground()


def raster(V, F, res):
    x0, y0 = V[:, 0].min() - res, V[:, 1].min() - res
    nx = int(math.ceil((V[:, 0].max() - x0) / res)) + 2
    ny = int(math.ceil((V[:, 1].max() - y0) / res)) + 2
    H = np.full((ny, nx), np.nan)
    for f in F:
        for k in range(1, len(f) - 1):
            p = V[[f[0], f[k], f[k + 1]]]
            ix0 = max(int((p[:, 0].min() - x0) / res), 0); ix1 = min(int((p[:, 0].max() - x0) / res) + 1, nx - 1)
            iy0 = max(int((p[:, 1].min() - y0) / res), 0); iy1 = min(int((p[:, 1].max() - y0) / res) + 1, ny - 1)
            xs, ys = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
            px = x0 + (xs + 0.5) * res; py = y0 + (ys + 0.5) * res
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = p
            det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(det) < 1e-9:
                continue
            l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
            l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            z = l1 * az + l2 * bz + l3 * cz
            H[ys[m], xs[m]] = np.fmax(H[ys[m], xs[m]], z[m])
    return H, x0, y0


def cells_to_poly(mask, x0, y0, res, simp):
    ys, xs = np.nonzero(mask)
    boxes = [sbox(x0 + i * res, y0 + j * res, x0 + (i + 1) * res, y0 + (j + 1) * res) for j, i in zip(ys, xs)]
    if not boxes:
        return []
    u = unary_union(boxes).buffer(0.01).simplify(simp)
    g = u.geoms if hasattr(u, 'geoms') else [u]
    out = []
    for p in g:
        if p.area < 4:
            continue
        p = Polygon(p.exterior)  # drop holes
        p = p.simplify(simp)
        if not p.is_valid or p.area < 4:
            continue
        c = list(p.exterior.coords)[:-1]
        if Polygon(c).exterior.is_ccw is False:
            c = c[::-1]
        out.append([[round(x, 2), round(y, 2)] for x, y in c])
    return out


def levels_of(H, gap=2.5):
    z = np.sort(H[~np.isnan(H)])
    if len(z) == 0:
        return []
    # cluster by gaps; representative = 80th percentile of cluster (roof heights)
    cl = [[z[0]]]
    for v in z[1:]:
        if v - cl[-1][-1] > gap:
            cl.append([v])
        else:
            cl[-1].append(v)
    lv = []
    for c in cl:
        if len(c) < 6 and len(cl) > 1:
            continue
        lv.append(float(np.percentile(c, 80)))
    return lv


out = {}
tower = None
for name in sorted(objs):
    V, F = objs[name]
    m = meta[name]
    area = np.ptp(V[:, 0]) * np.ptp(V[:, 1])
    res = 0.5 if area < 1500 else 1.0
    H, x0, y0 = raster(V, F, res)
    simp = 0.5 if res == 0.5 else (1.3 if name == 'b000' else 1.1)
    if name == 'b000':
        tmask = H > 240
        tower = cells_to_poly(tmask, x0, y0, res, 0.6)
        H = np.where(tmask, np.nan, H)
    lv = levels_of(H)
    if name == 'b000':
        lv = [37.5, 44.5, 50.0, 56.5, 63.0, 70.0, 108.0, 119.0]
    prisms = []
    zb = m['z0']
    for k, L in enumerate(lv):
        thr = (L - 1.2) if name != 'b000' else (0.5 * (L + (lv[k - 1] if k else 30.0)))
        mask = H >= thr
        polys = cells_to_poly(mask, x0, y0, res, simp)
        for p in polys:
            if name == 'b000' and abs(lib.poly_area(p)) < 30:
                continue
            prisms.append({'poly': p, 'z0': round(zb, 2), 'z1': round(L, 2)})
        zb = L
    # ground under footprint
    fp = cells_to_poly(~np.isnan(H), x0, y0, res, simp)
    gmin = 1e9; gmax = -1e9
    for p in fp:
        pts = np.array(p)
        P = Polygon(p)
        xs = np.linspace(P.bounds[0], P.bounds[2], 12); ys = np.linspace(P.bounds[1], P.bounds[3], 12)
        X, Y = np.meshgrid(xs, ys)
        zz = np.concatenate([G(pts[:, 0], pts[:, 1]), G(X.ravel(), Y.ravel())])
        gmin = min(gmin, float(zz.min())); gmax = max(gmax, float(zz.max()))
    out[name] = {'prisms': prisms, 'foot': fp, 'gmin': round(gmin, 2), 'gmax': round(gmax, 2),
                 'z0': m['z0'], 'z1': m['z1'], 'use': m['use'], 'lod2': m['lod2'], 'cx': m['cx'], 'cy': m['cy']}
    print(name, len(prisms), 'levels', [round(l, 1) for l in lv][:12], 'ground %.1f..%.1f' % (gmin, gmax))
out['_tower_plan'] = tower
json.dump(out, open(lib.WORK + 'prisms.json', 'w'))
print('tower plan polys', len(tower), [len(t) for t in tower])
