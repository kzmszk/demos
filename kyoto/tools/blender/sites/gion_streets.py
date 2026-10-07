"""Gion street rows: pick the PLATEAU buildings that front a street, split wide footprints into town-house lots, build
each with sites.machiya, exclude the generic buildings they replace."""
import math
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, box as sbox
import sites.machiya as M

def way_line(S, way_id):
    for w in S.osm['ways']:
        if w['id'] == way_id:
            pts = [p for l in w['line'] for p in l]
            return LineString(w['line'][0]) if len(w['line']) == 1 else shapely.ops.linemerge([LineString(l) for l in w['line']])
    raise KeyError(way_id)

def concat(lines):
    pts = []
    for l in lines:
        c = list(l.coords)
        if pts and np.hypot(pts[-1][0] - c[0][0], pts[-1][1] - c[0][1]) < 0.5: c = c[1:]
        pts += c
    return LineString(pts)

def footprint(b):
    r = np.asarray(b['poly'][0][0], float)
    return Polygon(r)

def front_of(P, L):
    """(street_edge, side) for footprint P along street line L: the tangent at the nearest point, side +1 left / -1 right"""
    c = P.representative_point()
    t = L.project(c)
    p = L.interpolate(t); q = L.interpolate(min(L.length, t + 1.0)); r = L.interpolate(max(0.0, t - 1.0))
    d = np.array([q.x - r.x, q.y - r.y]); d /= np.linalg.norm(d)
    side = 1 if (d[0] * (c.y - p.y) - d[1] * (c.x - p.x)) > 0 else -1
    e0 = (p.x - d[0] * 3, p.y - d[1] * 3); e1 = (p.x + d[0] * 3, p.y + d[1] * 3)
    return (e0, e1), side, t

def select(S, L, dmax, kinds=('trad', 'house', 'mid', 'shed'), max_h=13.5, max_st=3, used=None, extra=None):
    """PLATEAU buildings whose footprint comes within dmax of line L (and is replaceable by town houses)"""
    out = []
    for b in S.plateau:
        if used is not None and b['id'] in used: continue
        P = footprint(b)
        if not P.is_valid: P = P.buffer(0)
        if P.geom_type != 'Polygon' or P.area < 12: continue
        d = P.distance(L)
        if d > dmax: continue
        h = float(b['h'] or 0); st = int(b['st'] or 0)
        if b['kind'] not in kinds: continue
        if h > max_h or st > max_st: continue
        if b['kind'] == 'mid' and (st >= 4 or h > 12.5): continue
        out.append((b, P))
    return out

def lot_slices(P, edge, target=6.2, min_w=3.6, rng=None):
    """split a footprint into town-house lots along the street: returns [ring (world)] (one if narrow)"""
    O, U, N, yaw, Lc = M._frame(np.asarray(P.exterior.coords), edge)
    W = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
    k = int(round(W / target))
    if W < 9.5 or k < 2: return [np.asarray(P.exterior.coords)[:-1]]
    rng = rng or np.random.default_rng(0)
    cuts = np.linspace(0, W, k + 1)
    cuts[1:-1] += rng.uniform(-0.6, 0.6, k - 1)
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    out = []
    for i in range(k):
        a = cuts[i] if i > 0 else -100.0; b = cuts[i + 1] if i < k - 1 else 100.0
        g = Pl.intersection(sbox(a, -100, b, 300))
        if g.is_empty: continue
        if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
        if g.area < 8: continue
        loc = np.asarray(g.exterior.coords)[:-1]
        world = O + np.outer(loc[:, 0], U) + np.outer(loc[:, 1], N)
        out.append(world)
    return out

def kind_for(h, st, prefer='ochaya'):
    if h < 5.4 or st == 1: return 'hiraya'
    if h > 11.0 or st >= 3: return 'sangai'
    if h < 7.4: return 'tsushi'
    return prefer

def corner_edges(ring, lines, main, tol=3.2):
    """footprint edges running along another street (corner houses): world segments to dress as extra fronts"""
    ring = np.asarray(ring, float)
    out = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        d = b - a; L = np.linalg.norm(d)
        if L < 3.0: continue
        m = Point((a + b) / 2)
        if main.distance(m) < 2.5: continue
        for ln in lines:
            if ln.distance(m) > tol + 2.3: continue
            t = ln.project(m); p = ln.interpolate(max(0, t - 1)); q = ln.interpolate(min(ln.length, t + 1))
            e = np.array([q.x - p.x, q.y - p.y]); e /= max(np.linalg.norm(e), 1e-9)
            if abs(np.dot(e, d / L)) > 0.85:
                out.append((tuple(a), tuple(b))); break
    return out

EAVE_SETBACK = 0.85      # PLATEAU footprints here are LOD2 roof outlines: walls stand this far behind them

def setback_ring(ring, edge, sb, back=False):
    """cut a strip sb deep off the front (v < sb) or the back (v > D - sb) of a lot in its house frame.
    Returns (ring, edge) of the wall line (a front cut moves the street edge with it)."""
    O, U, N, yaw, Lc = M._frame(ring, edge)
    D = float(Lc[:, 1].max())
    if D - sb < 3.5: sb = max(0.0, D - 3.5)
    if sb <= 0.01: return np.asarray(ring, float), edge
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    g = Pl.intersection(sbox(-500, sb, 500, 500) if not back else sbox(-500, -500, 500, D - sb))
    if g.is_empty: return np.asarray(ring, float), edge
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    loc = np.asarray(g.exterior.coords)[:-1]
    ring2 = O + np.outer(loc[:, 0], U) + np.outer(loc[:, 1], N)
    if back: return ring2, edge
    return ring2, (tuple(np.asarray(edge[0], float) + N * sb), tuple(np.asarray(edge[1], float) + N * sb))

def cut_edges(ring, edges, sb):
    """set the walls along corner edges back by sb (strips along those edges removed)"""
    P = Polygon(ring)
    if not P.is_valid: P = P.buffer(0)
    for (a, b) in edges:
        a = np.asarray(a, float); b = np.asarray(b, float); d = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        P = P.difference(LineString([tuple(a - d * 1.5), tuple(b + d * 1.5)]).buffer(sb, cap_style='flat'))
    if P.is_empty: return np.asarray(ring, float)
    if P.geom_type != 'Polygon': P = max(P.geoms, key=lambda q: q.area)
    return np.asarray(P.simplify(0.02).exterior.coords)[:-1]

def front_line(ring, edge):
    O, U, N, yaw, Lc = M._frame(ring, edge)
    Wq = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
    return LineString([tuple(O), tuple(O + U * Wq)])

def wall_lot(ring0, edge, L, need, corner_lines=(), back_lines=()):
    """the wall line of a lot from its roof outline: front set back EAVE_SETBACK (more if the front would come within
    `need` of the street centre line), corner sides and backs on a street set back too.  -> (ring, edge, corners, back)"""
    ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK)
    dq = front_line(ring, edge1).distance(L)
    if dq < need:
        ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK + (need - dq) + 0.05)
    ce = corner_edges(ring0, corner_lines, L) if corner_lines else []
    if ce:
        ring = cut_edges(ring, ce, EAVE_SETBACK)
        ce = corner_edges(ring, corner_lines, L, tol=4.2)
    back = False
    if back_lines:
        O, U, N, yaw, Lc = M._frame(ring, edge1)
        D = float(Lc[:, 1].max())
        bk = Lc[Lc[:, 1] > D - 0.9]
        bl = LineString([tuple(O + U * bk[:, 0].min() + N * D), tuple(O + U * bk[:, 0].max() + N * D)])
        if any(bl.distance(l) < 4.5 for l in back_lines):
            ring, edge1 = setback_ring(ring, edge1, EAVE_SETBACK, back=True); back = True
    return ring, edge1, ce, back

def build_row(B, S, picks, L, prefer='ochaya', style=None, seed0=0, used=None, stats=None, h_scale=1.0, styler=None, corner_lines=(),
              need=1.9, back_lines=()):
    """build town houses for picked (b, P) along street line L; excludes the replaced generic buildings.
    The PLATEAU outlines are roof outlines: walls are set back (wall_lot) so the eaves land on them.
    corner_lines: other streets; footprint edges along them become extra (corner) fronts.  back_lines: streets behind
    the row (the backs facing them are set back too and get an eave)."""
    rng = np.random.default_rng(seed0)
    n = 0
    for (b, P) in picks:
        edge, side, t = front_of(P, L)
        h = float(b['h'] or 8.5) * h_scale; st = int(b['st'] or 0)
        h = min(max(h, 4.2), 12.8)
        rings = lot_slices(P, edge, rng=rng)
        for k, ring0 in enumerate(rings):
            seed = int(rng.integers(1 << 30))
            hh = h + (rng.uniform(-0.45, 0.35) if len(rings) > 1 else 0.0)
            kind = kind_for(hh, st, prefer)
            try:
                ring, edge1, ce, back = wall_lot(ring0, edge, L, need, corner_lines, back_lines)
            except Exception as e:
                print('lot fail', b['id'], repr(e)); continue
            stl = dict(kind=kind)
            stl['party'] = 'wall_board' if rng.random() < 0.45 else 'wall_plaster'
            stl['ground'] = S.ground
            if style: stl.update(style)
            if styler: stl.update(styler(b, P, ring, rng) or {})
            if ce:
                stl['facade_edges'] = ce
                stl['facade_style'] = dict(door=-1, degoshi=False, chochin=False, nameboard=False, **(stl.get('facade_style') or {}))
            if back and stl.get('back', 'plain') == 'plain': stl['back_o'] = 0.7
            # front ground height: at the middle of the front, half a metre out
            O, U, N, yaw, Lc = M._frame(ring, edge1)
            Wf = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
            if Wf < 2.2: continue
            fc = O + U * Wf / 2 - N * 0.5
            z0 = float(S.ground(fc[0], fc[1]))
            try:
                M.build(B, ring, edge1, z0, hh, st, stl, seed=seed)
                n += 1
            except Exception as e:
                print('machiya fail', b['id'], repr(e))
        S.exclude.append([list(map(float, c)) for c in np.asarray(P.exterior.coords)[:-1]])
        if used is not None: used.add(b['id'])
    if stats is not None: stats['machiya'] = stats.get('machiya', 0) + n
    return n

def street_lamps(B, L, z_of, spacing=16.0, offset=3.6, h=3.5, start=6.0, side0=1):
    """the unified 3.5 m lamp posts of Hanamikoji: a dark post with a square paper-glass lantern head"""
    from jk import prim
    t = start; side = side0
    while t < L.length - 3:
        p = L.interpolate(t); q = L.interpolate(min(L.length, t + 1))
        d = np.array([q.x - p.x, q.y - p.y]); d /= max(np.linalg.norm(d), 1e-6)
        nrm = np.array([-d[1], d[0]]) * side
        x, y = p.x + nrm[0] * offset, p.y + nrm[1] * offset
        z = z_of(x, y)
        prim.cyl(B, (x, y, z), (x, y, z + h - 0.5), 0.07, 0.06, 8, 'metal_dark', tag='main')
        prim.box(B, x - 0.2, y - 0.2, z + h - 0.5, x + 0.2, y + 0.2, z + h - 0.02, 'lamp', tag='main')
        prim.box(B, x - 0.26, y - 0.26, z + h - 0.02, x + 0.26, y + 0.26, z + h + 0.06, 'metal_dark', tag='main')
        prim.box(B, x - 0.24, y - 0.24, z + h - 0.56, x + 0.24, y + 0.24, z + h - 0.5, 'metal_dark', tag='detail')
        B.lamp(x, y, z + h - 0.25, 25.0, (1.0, 0.78, 0.55))
        prim.polygon(B, [(x - 0.3, y - 0.3), (x + 0.3, y - 0.3), (x + 0.3, y + 0.3), (x - 0.3, y + 0.3)], z + 0.05, 'stone', tag='block')
        t += spacing; side = -side
