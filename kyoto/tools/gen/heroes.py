"""Hand-built sites (Blender, tools/blender/sites/*.py -> ASSETS/heroes/<site>.npz) merged into the tiles:
geometry per tile (by triangle centroid), site edits (generic buildings to drop, terrain to cut, ground surfaces to paint),
walk surfaces and blockers for the walk map, trees and lamps."""
import os, glob, json
import numpy as np
import shapely
from shapely.geometry import Polygon
from .frame import ASSETS

DIR = os.path.join(ASSETS, 'heroes')
# OSM landuse areas a site plants itself (no generic trees there), beyond its exclude/cut rings
TREE_ZONES = {'fushimi_inari': [96291583], 'toji': [359896810], 'tofukuji': [768987591], 'tenryuji': [-17656638, 409723494, 319336216, 677236682, 925807376], 'kinkakuji': [98115917]}

class Heroes:
    def __init__(self):
        self.sites = []
        for f in sorted(glob.glob(os.path.join(DIR, '*.npz'))):
            for k in range(30):                    # a site being re-exported right now: wait for the file to be complete
                try: d = dict(np.load(f, allow_pickle=False)); break
                except Exception:
                    if k == 29: raise
                    import time; time.sleep(2.0)
            name = os.path.basename(f)[:-4]
            ed = json.loads(bytes(d['EDITS']).decode()) if 'EDITS' in d else {}
            s = dict(name=name, d=d, edits=ed)
            if 'I' in d and len(d['I']):
                C = d['P'][d['I']].mean(1)
                s['C'] = C
                # where the site has geometry (2 m cells): a generic building mostly covered by it is a double
                s['occ'] = np.unique(np.floor(C[:, 0] / 2.0).astype(np.int64) * 1_000_003 + np.floor(C[:, 1] / 2.0).astype(np.int64))
                s['bb'] = (float(C[:, 0].min()), float(C[:, 1].min()), float(C[:, 0].max()), float(C[:, 1].max()))
                # roof / ceiling candidates for the walk map's "covered" bit: sloped or flat, not tiny
                T = d['P'][d['I']].astype(np.float32)
                cr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ar = np.linalg.norm(cr, axis=1)
                nz = np.abs(cr[:, 2]) / np.maximum(ar, 1e-9)
                s["RT"] = T[(nz > 0.25) & (ar * 0.5 > 0.04)]
            def fix(g):
                """invalid rings (self-touching, bow-ties) from a site's edits: repair rather than fail the whole build"""
                if g.is_valid: return g
                g = shapely.make_valid(g)
                parts = [q for q in (g.geoms if hasattr(g, 'geoms') else [g]) if q.geom_type in ('Polygon', 'MultiPolygon')]
                return shapely.unary_union(parts) if parts else Polygon()
            def pg(lst): return [fix(Polygon(p[0], p[1:]) if isinstance(p[0][0], (list, tuple)) else Polygon(p)) for p in lst]
            s['exclude'] = shapely.unary_union(pg(ed.get('exclude', []))) if ed.get('exclude') else None
            s['cut'] = shapely.unary_union(pg(ed.get('cut', []))) if ed.get('cut') else None
            s['paint'] = [(pg([e['poly']])[0], e['surf']) for e in ed.get('paint', [])]
            self.sites.append(s)
        self.exclude = shapely.unary_union([s['exclude'] for s in self.sites if s['exclude'] is not None]) if any(s['exclude'] is not None for s in self.sites) else None
        if self.exclude is not None: shapely.prepare(self.exclude)

    def excluded(self, b):
        if self.exclude is not None and self.exclude.contains(b.poly.representative_point()): return True
        # a generic building whose footprint the hero geometry mostly covers (a site that forgot to exclude it)
        x0, y0, x1, y1 = b.poly.bounds
        for s in self.sites:
            if 'occ' not in s: continue
            a, c, e, f = s['bb']
            if x1 < a or x0 > e or y1 < c or y0 > f: continue
            xs = np.arange(x0 + 1.0, x1, 2.0); ys = np.arange(y0 + 1.0, y1, 2.0)
            if not len(xs) or not len(ys): continue
            X, Y = np.meshgrid(xs, ys); X = X.ravel(); Y = Y.ravel()
            ins = shapely.contains_xy(b.poly, X, Y)
            if ins.sum() < 3: continue
            keys = np.floor(X[ins] / 2.0).astype(np.int64) * 1_000_003 + np.floor(Y[ins] / 2.0).astype(np.int64)
            if np.isin(keys, s['occ']).mean() > 0.6: return True
        return False

    def cut(self, R):
        g = [s['cut'].intersection(R.buffer(5)) for s in self.sites if s['cut'] is not None and s['cut'].intersects(R)]
        return shapely.unary_union(g) if g else None

    def paint(self, R):
        return [(p, sid) for s in self.sites for (p, sid) in s['paint'] if p.intersects(R)]

    def add_geometry(self, mb, bounds):
        """triangles whose centroid lies in the tile -> mb (keeps attributes); returns the triangle count"""
        x0, y0, x1, y1 = bounds; n = 0; self.last_detail = []
        for s in self.sites:
            if 'C' not in s: continue
            C = s['C']; sel = (C[:, 0] >= x0) & (C[:, 0] < x1) & (C[:, 1] >= y0) & (C[:, 1] < y1)
            if not sel.any(): continue
            d = s['d']; T = d['I'][sel].astype(np.int64)
            vid, inv = np.unique(T.ravel(), return_inverse=True)
            mb.add(d['P'][vid], inv.reshape(-1, 3), N=d['N'][vid], UV=d['UV'][vid], mat=d['MAT'][vid], c0=d['C0'][vid], c1=d['C1'][vid])
            n += int(sel.sum())
            self.last_detail.append(d['DETAIL'][T[:, 0]] if 'DETAIL' in d else np.zeros(len(T), np.uint8))
        return n

    def walk_edits(self, bounds):
        """(walk triangles (k,3,3), block triangles (m,3,3)) near the tile"""
        x0, y0, x1, y1 = bounds; W = []; K = []
        for s in self.sites:
            d = s['d']
            for (pk, ik, out) in (('WP', 'WI', W), ('KP', 'KI', K)):
                if pk not in d or not len(d[ik]): continue
                T = d[pk][d[ik].astype(np.int64)]
                mn = T.min(1); mx = T.max(1)
                sel = (mx[:, 0] >= x0 - 1) & (mn[:, 0] <= x1 + 1) & (mx[:, 1] >= y0 - 1) & (mn[:, 1] <= y1 + 1)
                if sel.any(): out.append(T[sel])
        return (np.concatenate(W) if W else np.zeros((0, 3, 3))), (np.concatenate(K) if K else np.zeros((0, 3, 3)))

    def tree_zone(self, w):
        """where generic trees must not grow: excluded precincts, cut ground, the OSM areas in TREE_ZONES"""
        lu = {f['id']: f for f in w.osm['landuse']}
        g = [s[k] for s in self.sites for k in ('exclude', 'cut') if s[k] is not None]
        g += [lu[i]['poly'] for s in self.sites for i in TREE_ZONES.get(s['name'], []) if i in lu]
        if not g: return None
        z = shapely.unary_union(g); shapely.prepare(z); return z

    def roof_tris(self, bounds):
        x0, y0, x1, y1 = bounds; out = []
        for s in self.sites:
            if 'RT' not in s: continue
            T = s['RT']; mn = T.min(1); mx = T.max(1)
            sel = (mx[:, 0] >= x0) & (mn[:, 0] <= x1) & (mx[:, 1] >= y0) & (mn[:, 1] <= y1)
            if sel.any(): out.append(T[sel])
        return np.concatenate(out) if out else np.zeros((0, 3, 3), np.float32)

    def trees(self):
        out = []
        for s in self.sites:
            if 'TREES' in s['d'] and len(s['d']['TREES']):
                T = np.array(s['d']['TREES'], np.float32)
                for (a, b, za, zb, hw, s1) in VIEWS.get(s['name'], []): view_corridor(T, a, b, za, zb, hw, s1)
                out.append(T)
        return out

# famous views kept open over the trees: (from xy, to xy, eye z at each end, half width, how far along (0-1) to act)
VIEWS = {
    # Tsūten-kyō from Gaun-kyō: the bridge above a sea of maples; the near crowns stayed at eye height and filled the view
    'tofukuji': [((1287.5, -925.8), (1356.0, -944.5), 43.45, 48.2, 7.0, 0.62)],
}
TREE_H = {0: 7.4, 1: 15.8, 2: 8.8, 3: 17.8, 4: 9.0, 5: 26.1, 6: 20.5, 7: 12.8, 8: 9.4, 9: 1.3, 10: 13.0}   # template heights (m) by species

def view_corridor(T, a, b, za, zb, hw, s1):
    """scale down the trees (species, x, y, z, scale, yaw) whose crowns rise into a sight line, near its start: their tops
    end 1.2 m (growing to 2.5 m at the near end) under the eye"""
    a = np.asarray(a, float); b = np.asarray(b, float); ab = b - a; L2 = float(ab @ ab)
    s = np.clip(((T[:, 1:3] - a) @ ab) / L2, 0, 1)
    d = np.linalg.norm(T[:, 1:3] - (a + s[:, None] * ab), axis=1)
    H = np.array([TREE_H.get(int(k), 8.0) for k in T[:, 0]])
    eye = za + (zb - za) * s - (2.5 - 1.3 * s / s1)
    sel = (d < hw) & (s < s1) & (T[:, 3] + H * T[:, 4] > eye)
    T[sel, 4] = np.maximum((eye[sel] - T[sel, 3]) / H[sel], 0.35)

def raster_edges(T, x0, y1, res, n, hw=0.1):
    """mark the cells along the plan projection of the triangles' edges (vertical blockers have no plan area)"""
    hit = np.zeros((n, n), bool)
    for t in T:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            L = float(np.hypot(*(b[:2] - a[:2])))
            k = max(2, int(L / (res * 0.5)) + 1)
            xs = np.linspace(a[0], b[0], k); ys = np.linspace(a[1], b[1], k)
            for dx in (-hw, 0.0, hw):
                for dy in (-hw, 0.0, hw):
                    ii = np.floor((xs + dx - x0) / res).astype(int); jj = np.floor((y1 - ys - dy) / res).astype(int)
                    ok = (ii >= 0) & (ii < n) & (jj >= 0) & (jj < n)
                    hit[jj[ok], ii[ok]] = True
    return hit

def raster_tris(T, x0, y1, res, n, Z=None, mask=None):
    """rasterise triangles (k,3,3) onto an n x n grid (row 0 = north edge y1, col 0 = x0): returns (hit mask, z of the
    topmost surface).  Cell centres are tested with barycentric coordinates."""
    hit = np.zeros((n, n), bool) if mask is None else mask
    zz = np.full((n, n), -1e9) if Z is None else Z
    for t in T:
        xs = (t[:, 0] - x0) / res - 0.5; ys = (y1 - t[:, 1]) / res - 0.5
        i0 = max(0, int(np.floor(xs.min()))); i1 = min(n - 1, int(np.ceil(xs.max()))); j0 = max(0, int(np.floor(ys.min()))); j1 = min(n - 1, int(np.ceil(ys.max())))
        if i1 < i0 or j1 < j0: continue
        I, J = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
        px = I.astype(float); py = J.astype(float)
        (ax, bx, cx), (ay, by, cy) = xs, ys
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12: continue
        l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
        l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
        l3 = 1 - l1 - l2
        ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not ins.any(): continue
        z = l1 * t[0, 2] + l2 * t[1, 2] + l3 * t[2, 2]
        jj, ii = J[ins], I[ins]
        hit[jj, ii] = True
        zz[jj, ii] = np.maximum(zz[jj, ii], z[ins])
    return hit, zz
