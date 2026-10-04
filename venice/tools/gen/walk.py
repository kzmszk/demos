"""Walk / water rasters per tile (0.25 m): R = walkable surface height code (0 = blocked), G = 255 where a
boat can float (open water, including under bridges).  Height code c -> z = (c - 1) * 0.04 - 1.0 m.

Walkable: land minus buildings, plus building passages (sottoporteghi) and covered calli from OSM, bridge
decks (ramped profile), and hero overrides (porticoes, interiors) with their floor heights."""
import math
import numpy as np
import shapely
from shapely.geometry import box, LineString, Polygon
from PIL import Image, ImageDraw
from .world import GROUND_Z, polys_of

RES = 0.25
def zcode(z): return int(np.clip(round((z + 1.0) / 0.04) + 1, 1, 255))

class Passages:
    """OSM ways that run through/under buildings (tunnel=building_passage, covered=yes) as walkable strips."""
    def __init__(self, world):
        o = world.o; geoms = []
        for wid, w in o.ways.items():
            t = w.get('tags', {})
            if t.get('highway') in ('pedestrian', 'footway', 'steps', 'path', 'service') and (t.get('tunnel') in ('building_passage', 'yes') or t.get('covered') == 'yes'):
                P = o.way_xy(wid)
                if len(P) >= 2:
                    wd = 1.6 if t.get('highway') != 'steps' else 1.4
                    geoms.append(LineString(P).buffer(wd / 2, cap_style=2))
        # sottoporteghi found by streets.py (tagged ones and untagged calli passing right through a building)
        for (sg, k) in getattr(world, 'soto', []): geoms.append(sg)
        n_extra = len(getattr(world, 'soto', []))
        self.n_untagged = n_extra
        self.geoms = geoms
        self.tree = shapely.STRtree(geoms) if geoms else None
    def within(self, R):
        if not self.tree: return []
        return [self.geoms[i] for i in self.tree.query(R)]

def dead_bridges(world, bridges, blockers, passages, hero_walk):
    """indices of bridges that cannot be used: an end lands inside a building (no passage there) or in water.
    Their decks stay out of the walk raster, so nobody walks onto a private bridge and into a wall."""
    from shapely.geometry import Point
    btree = shapely.STRtree(blockers) if blockers else None
    hw = [(p, z) for (p, z) in hero_walk]
    decks = []
    for br in bridges:
        a = np.array(br['a']); d = np.array(br['d']); n = np.array([-d[1], d[0]]); s_lo, _, _, s_hi = br['s']; ti = br['ti']
        decks.append(Polygon([tuple(a + d * s_lo + n * ti), tuple(a + d * s_hi + n * ti), tuple(a + d * s_hi - n * ti), tuple(a + d * s_lo - n * ti)]))
    dtree = shapely.STRtree(decks) if decks else None
    def walkable(p, me):
        P = Point(*p)
        for (poly, z) in hw:
            if poly.contains(P): return z is not None
        if dtree is not None and any(k != me and decks[k].contains(P) for k in dtree.query(P)): return True
        if not world.land.contains(P): return False
        if btree is not None and any(blockers[k].contains(P) for k in btree.query(P)):
            return any(g.contains(P) for g in passages.within(P.buffer(0.01)))
        return True
    out = set()
    for k, br in enumerate(bridges):
        a = np.array(br['a']); d = np.array(br['d']); n = np.array([-d[1], d[0]]); s_lo, _, _, s_hi = br['s']; ti = br['ti']
        for (s, sg) in ((s_lo, -1.0), (s_hi, 1.0)):
            if not any(walkable(a + d * (s + sg * 0.8) + n * t, k) for t in (-ti * 0.5, 0.0, ti * 0.5)):
                out.add(k); break
    return out

def _fill(draw, g, R, val, S):
    x0, y0, x1, y1 = R.bounds
    for p in polys_of(g):
        ext = [((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords]
        if len(ext) >= 3: draw.polygon(ext, fill=val)
        for r in p.interiors:
            ints = [((x - x0) / RES, (y1 - y) / RES) for x, y in r.coords]
            if len(ints) >= 3: draw.polygon(ints, fill=0)

def raster(world, R, buildings, passages, bridges, hero_walk=()):
    """R: tile box.  buildings: list of shapely polygons that block.  bridges: walk dicts from gen_bridge.
    hero_walk: [(polygon, z)] walkable overrides (drawn last), or (polygon, None) to block."""
    x0, y0, x1, y1 = R.bounds
    S = int(round((x1 - x0) / RES))
    land = world.land.intersection(R)
    walk = Image.new('L', (S, S), 0); dw = ImageDraw.Draw(walk)
    _fill(dw, land, R, zcode(GROUND_Z), S)
    for b in buildings:
        if b.intersects(R): _fill(dw, b.intersection(R), R, 0, S)
    for g in passages.within(R):
        _fill(dw, g.intersection(land.buffer(0.3)).intersection(R), R, zcode(GROUND_Z), S)
    W = np.array(walk, np.uint8)
    # bridge decks: per-pixel ramp heights
    ys, xs = np.mgrid[0:S, 0:S]
    px = x0 + (xs + 0.5) * RES; py = y1 - (ys + 0.5) * RES
    for br in bridges:
        a = np.array(br['a']); d = np.array(br['d']); n = np.array([-d[1], d[0]])
        s_lo, s_l0, s_l1, s_hi = br['s']; ti = br['ti'] - 0.05; zt = br['ztop']
        cx = [a + d * s_lo + n * ti, a + d * s_hi + n * ti, a + d * s_hi - n * ti, a + d * s_lo - n * ti]
        bx = np.array(cx)
        if bx[:, 0].max() < x0 or bx[:, 0].min() > x1 or bx[:, 1].max() < y0 or bx[:, 1].min() > y1: continue
        i0 = max(0, int((y1 - bx[:, 1].max()) / RES) - 1); i1 = min(S, int((y1 - bx[:, 1].min()) / RES) + 2)
        j0 = max(0, int((bx[:, 0].min() - x0) / RES) - 1); j1 = min(S, int((bx[:, 0].max() - x0) / RES) + 2)
        if i1 <= i0 or j1 <= j0: continue
        qx = px[i0:i1, j0:j1] - a[0]; qy = py[i0:i1, j0:j1] - a[1]
        s = qx * d[0] + qy * d[1]; t = qx * n[0] + qy * n[1]
        inside = (np.abs(t) <= ti) & (s >= s_lo) & (s <= s_hi)
        z = np.where(s < s_l0, GROUND_Z + (s - s_lo) / max(s_l0 - s_lo, 1e-3) * (zt - GROUND_Z),
            np.where(s > s_l1, GROUND_Z + (s_hi - s) / max(s_hi - s_l1, 1e-3) * (zt - GROUND_Z), zt))
        code = np.clip(np.round((z + 1.0) / 0.04) + 1, 1, 255).astype(np.uint8)
        sub = W[i0:i1, j0:j1]
        sub[inside] = np.maximum(sub[inside], code[inside])
    for (poly, z) in hero_walk:
        if not poly.intersects(R): continue
        img = Image.new('L', (S, S), 0); d2 = ImageDraw.Draw(img)
        _fill(d2, poly.intersection(R), R, 255, S)
        m = np.array(img) > 0
        if isinstance(z, dict):            # ramp: z interpolated along a direction from a profile
            a = np.array(z['a']); d = np.array(z['d']); pr = np.array(z['prof'], float)
            sv = (px[m] - a[0]) * d[0] + (py[m] - a[1]) * d[1]
            zz = np.interp(sv, pr[:, 0], pr[:, 1])
            W[m] = np.clip(np.round((zz + 1.0) / 0.04) + 1, 1, 255).astype(np.uint8)
        else:
            W[m] = 0 if z is None else zcode(z)
    # water: everything that is not land (boats pass under bridges)
    wimg = Image.new('L', (S, S), 255); dwa = ImageDraw.Draw(wimg)
    _fill(dwa, land, R, 0, S)
    WA = np.array(wimg, np.uint8)
    rgb = np.zeros((S, S, 3), np.uint8); rgb[..., 0] = W; rgb[..., 1] = WA
    return rgb
