"""Site data for a hero script (exported by tools/site_data.py): terrain lookup, OSM / PLATEAU features, helpers."""
import json, math, os
import numpy as np

ASSETS = '/home/kazu/work/kyoto-assets'

class Site:
    def __init__(self, name):
        d = os.path.join(ASSETS, 'sites', name)
        self.name = name; self.dir = d
        self.data = json.load(open(os.path.join(d, 'site.json')))
        t = np.load(os.path.join(d, 'terrain.npz'))
        self.H = t['H'].astype(np.float64); self.x0 = float(t['x0']); self.y0 = float(t['y0']); self.res = float(t['res'])
        self.bounds = self.data['bounds']; self.osm = self.data['osm']; self.plateau = self.data['plateau']
        self.polygon = self.data['polygon']
        # what the site hands to the tile builder besides geometry (see export): generic buildings to drop, generic terrain
        # to cut away, ground surfaces to paint (gravel, moss, stone ...), walk overrides
        self.exclude = []; self.cut = []; self.paint = []

    def ground(self, x, y):
        """terrain height (T.P., m) at x, y (scalars or arrays): bilinear on the 1 m grid"""
        x = np.asarray(x, float); y = np.asarray(y, float)
        fx = (x - self.x0) / self.res; fy = (y - self.y0) / self.res
        ix = np.clip(np.floor(fx).astype(int), 0, self.H.shape[1] - 2); iy = np.clip(np.floor(fy).astype(int), 0, self.H.shape[0] - 2)
        ax = np.clip(fx - ix, 0, 1); ay = np.clip(fy - iy, 0, 1); H = self.H
        z = H[iy, ix] * (1 - ax) * (1 - ay) + H[iy, ix + 1] * ax * (1 - ay) + H[iy + 1, ix] * (1 - ax) * ay + H[iy + 1, ix + 1] * ax * ay
        return float(z) if z.ndim == 0 else z

    def osm_building(self, way_id):
        for b in self.osm['buildings']:
            if b['id'] == way_id: return b
        return None

    def find(self, cat, **tags):
        """OSM features of a category whose tags contain the given substrings, e.g. find('buildings', name='本堂')"""
        out = []
        for f in self.osm[cat]:
            t = f.get('tags', {})
            if all(v in str(t.get(k, '')) for k, v in tags.items()): out.append(f)
        return out

    def rect(self, poly):
        """minimum rotated rectangle of a footprint (outer ring list) -> (cx, cy, length, width, yaw): length along yaw"""
        import shapely
        from shapely.geometry import Polygon
        if hasattr(poly, 'exterior'): p = poly
        else:
            while isinstance(poly[0][0], (list, tuple)): poly = poly[0]       # [[ring, holes...], ...] -> outer ring
            p = Polygon(poly)
        r = p.minimum_rotated_rectangle
        xs, ys = r.exterior.coords.xy
        e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
        L0, L1 = np.linalg.norm(e0), np.linalg.norm(e1)
        d = e0 if L0 >= L1 else e1
        return r.centroid.x, r.centroid.y, max(L0, L1), min(L0, L1), math.atan2(d[1], d[0])

    def terrain_mesh(self, B, poly, mat='ground', res=1.0, surf=None, tag='main', offset=0.0):
        """the site's own ground over a polygon (outer ring), following the terrain; surf = a ground surface name
        (materials.SURF) drawn by the ground program (bridge-deck style override); also adds a walk surface"""
        import shapely
        from shapely.geometry import Polygon
        P = Polygon(poly)
        x0, y0, x1, y1 = P.bounds
        xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
        X, Y = np.meshgrid(xs, ys); Z = self.ground(X, Y) + offset
        inside = shapely.contains_xy(P.buffer(res), X, Y)
        V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        nx = len(xs); I = []
        for j in range(len(ys) - 1):
            for i in range(nx - 1):
                a = j * nx + i
                if inside[j, i] and inside[j, i + 1] and inside[j + 1, i] and inside[j + 1, i + 1]:
                    I += [[a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]]
        from .core import mats
        SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
                'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
        c1 = (0, 0, 0, SURF.index(surf) if surf else 0)
        B.add(V, I, mat, UV=V[:, :2], smooth=True, tag=tag, c1=c1)
        B.add(V, I, mat, UV=V[:, :2], smooth=True, tag='walk')
