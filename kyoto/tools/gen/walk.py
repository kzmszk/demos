"""Walk map of a tile (0.5 m): RGBA PNG.  R,G = height (uint16, cm above -20 m T.P.), B = surface id (low 5 bits) +
flags (bit 7 blocked, bit 6 water), A = 255.  The viewer's walker follows these heights and stops at blocked cells and
at steps higher than ~0.45 m."""
import numpy as np
import shapely
from shapely.geometry import Point
from PIL import Image, ImageDraw
from .ground import RES

ZOFF = 20.0

def raster(tg, surf, buildings, wg, wl, bridges, extra=None, hero=None):
    x0, y0, x1, y1 = tg.b
    n = int(round((x1 - x0) / RES))
    xs = x0 + (np.arange(n) + 0.5) * RES; ys = y0 + (np.arange(n) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys)
    Z = tg.T(X.ravel(), Y.ravel()).reshape(n, n)
    blocked = np.zeros((n, n), bool); water = np.zeros((n, n), bool)
    def mask(g):
        img = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(img)
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.geom_type != 'Polygon' or p.is_empty: continue
            dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords], fill=255)
            for r in p.interiors: dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in r.coords], fill=0)
        return np.asarray(img)[::-1] > 0
    if buildings:
        g = shapely.unary_union([b.poly for b in buildings]).buffer(0.15)
        blocked |= mask(g.intersection(tg.R.buffer(1)))
    if wg is not None and not wg.is_empty:
        m = mask(wg.intersection(tg.R.buffer(1)))
        water |= m; blocked |= m
        if wl is not None and m.any():
            Z[m] = wl(np.stack([X[m], Y[m]], 1))
    for br in bridges:
        g = br['line'].buffer(br['w'] / 2 - 0.4, cap_style='flat')
        m = mask(g.intersection(tg.R.buffer(1)))
        if m.any():
            # deck height: project cells onto the bridge line
            ln = br['line']; Lt = ln.length
            t = shapely.line_locate_point(ln, shapely.points(X[m], Y[m]))
            zz = np.interp(t, np.linspace(0, Lt, len(br['zz'])), br['zz'])
            Z[m] = zz; blocked[m] = False; water[m] = False
    if extra:
        for (g, zf, walk) in extra:
            m = mask(g.intersection(tg.R.buffer(1)))
            if m.any():
                if zf is not None: Z[m] = zf(X[m], Y[m])
                blocked[m] = not walk
    covered = np.zeros((n, n), bool)
    if hero is not None:
        from .heroes import raster_tris
        Wt, Kt = hero[:2]
        if len(Wt):
            # walk surfaces (floors, stairs, stages, paths): the topmost one wins (images rows go south -> north here)
            hit, zz = raster_tris(Wt, x0, y1, RES, n)
            hit = hit[::-1]; zz = zz[::-1]
            raised = hit & (zz > Z + 0.3)                     # floors, verandas, stages: wooden underfoot
            Z[hit] = zz[hit]; blocked[hit] = False; water[hit] = False
            surf = surf.copy(); surf[raised] = 18
        if len(Kt):
            from .heroes import raster_edges
            hitk, _ = raster_tris(Kt, x0, y1, RES, n)
            hitk |= raster_edges(Kt, x0, y1, RES, n)          # thin vertical blockers (walls, railings) by their footprint lines
            # seams between blockers (a wall's panels meeting with a hand's breadth between them) closed, walls kept thin
            from scipy import ndimage
            hitk |= ndimage.binary_closing(hitk, structure=np.ones((3, 3), bool))
            blocked |= hitk[::-1]
        if len(hero) > 2 and len(hero[2]):
            # covered: a hero roof or ceiling 2.2 .. 30 m above the walk surface (the viewer adapts its exposure indoors)
            Rt = hero[2]
            cx = np.clip(((Rt[:, :, 0].mean(1) - x0) / RES).astype(int), 0, n - 1); cy = np.clip(((Rt[:, :, 1].mean(1) - y0) / RES).astype(int), 0, n - 1)
            zf = Z[cy, cx]; zl = Rt[:, :, 2].min(1)
            Rt = Rt[(zl > zf + 1.9) & (zl < zf + 30.0)]
            img = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(img)
            for t in Rt: dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in t[:, :2]], fill=255)
            covered = (np.asarray(img) > 0)[::-1] & ~blocked
    h = np.clip(np.round((Z + ZOFF) * 100), 0, 65535).astype(np.uint16)
    B = (surf & 31).astype(np.uint8) | (blocked.astype(np.uint8) << 7) | (water.astype(np.uint8) << 6) | (covered.astype(np.uint8) << 5)
    rgba = np.stack([(h >> 8).astype(np.uint8), (h & 255).astype(np.uint8), B, np.full((n, n), 255, np.uint8)], -1)
    return rgba[::-1]          # image row 0 = north
