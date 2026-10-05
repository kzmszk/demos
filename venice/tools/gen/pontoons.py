"""Vaporetto stops (imbarcaderi) and moored museum ships.

OSM maps the ACTV stops in three ways: man_made=pier polygons (the floating pontoon or its roof; world.py used to drop
them, so many stops had nothing at all), public_transport=platform / ferry=yes buildings, and building=roof|hut|
transportation shelters standing in the water.  The generic generator turned the last two into plastered houses with
chimneys standing in the canal, their water-gate steps into odd little stairs into the water: in front of the station
it looked like a wrecked bridge.  Here every stop that floats (less than half of it on land) becomes
  - a near-black steel pontoon (the OSM outline, or the shelter's rectangle plus a margin) riding ZD above the water,
    with a rubber fender, a plank deck and a yellow edge on the boarding side,
  - a waiting cabin under the roof outline: pale grey steel posts, glazed back and ends, open to the water for boarding,
    benches, a flat roof with ACTV-yellow name boards (ferry stops) and lamps under it (lit in the night bake),
  - a gangway with steel side panels from the fondamenta, along the OSM gangway lines when there are any, else the
    shortest way to land,
and the deck and gangways are walkable.  building=ship outlines (a bragozzo off the Dogana, a tug at Sant'Elena) become
boats instead of houses.

collect(world) runs in World.__init__: it takes these outlines out of world.buildings and returns (stops, ships).
build(mb, item) adds one stop or ship to a tile; walk_areas(world) gives the decks and gangways for the walk raster."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import nearest_points
import shapely
from vk import geom as G
from vk.adapt import to_builder

GZ = 1.1                 # streets (world.GROUND_Z; not imported: world.py imports this module)
ZD = 0.80                # deck top above the water (the quay is at GZ)
ZH = -0.35               # hull bottom
WALL = 2.55              # cabin wall top above the deck
ROOF = 0.25              # roof slab thickness
OVER = 0.40              # roof overhang beyond the cabin walls
GW = 1.7                 # gangway width (outside the side panels)
GANG_MAX = 15.0          # longest gangway guessed straight across to the quay
GANG_OSM = 32.0          # longest gangway along an OSM line (some stops lie well out, on long jetties)
LINK_MAX = 5.0           # a pontoon this close to one already reached is moored to it
LAND_MAX = 0.5           # at most this share of an outline on land, else it is not floating
PEDESTRIAN = ('footway', 'pedestrian', 'path', 'steps', 'corridor', 'service', 'living_street')


# ================================================================================================ collect
def _largest(g):
    ps = [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon']
    return max(ps, key=lambda p: p.area) if ps else None

def _frame(poly):
    """centre, long axis u, short axis v, half sizes of the outline's minimum rotated rectangle."""
    r = poly.minimum_rotated_rectangle
    P = np.array(r.exterior.coords)[:4]
    e0 = P[1] - P[0]; e1 = P[2] - P[1]
    if np.linalg.norm(e0) < np.linalg.norm(e1): e0, e1 = e1, e0
    u = e0 / max(np.linalg.norm(e0), 1e-9)
    return P.mean(0), u, np.array([-u[1], u[0]]), np.linalg.norm(e0) / 2, np.linalg.norm(e1) / 2

def _rect(c, u, v, hu, hv):
    return Polygon([tuple(c + u * su * hu + v * sv * hv) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))])

def collect(world):
    land = world.land
    def wet(b): return b.poly.intersection(land).area < LAND_MAX * b.poly.area
    def ferry_of(t):
        return (t.get('ferry') == 'yes' or t.get('public_transport') == 'platform' or t.get('amenity') == 'ferry_terminal'
                or t.get('operator', '').lower() == 'actv' or t.get('shop') == 'ticket')
    ships, cand = [], {}
    for b in world.buildings + world.piers:
        t = b.tags; bk = t.get('building', '')
        if ('building:part' in t or bk == 'bridge' or t.get('man_made') in ('monitoring_station', 'lighthouse')
                or b.poly.area > 1000 or not wet(b)): continue
        if bk == 'ship': ships.append(b); continue
        if ferry_of(t) or t.get('man_made') == 'pier' or bk in ('roof', 'hut', 'transportation', 'kiosk'):
            cand[b.id] = (b, ferry_of(t))
    # one-storey buildings in the water right next to a stop (ticket offices, landing huts) belong to it
    if cand:
        tree = shapely.STRtree([b.poly for b, _ in cand.values()]); vals = list(cand.values())
        for b in world.buildings:
            if b.id in cand or 'building:part' in b.tags or b.poly.area > 300 or b.levels > 1 or not wet(b): continue
            nb = [vals[k] for k in tree.query(b.poly.buffer(8.0))]
            if nb: cand[b.id] = (b, any(f for _, f in nb))
    def is_cabin(b):
        t = b.tags
        roofish = (t.get('building') in ('roof', 'hut', 'kiosk') or t.get('shelter') == 'yes' or t.get('covered') == 'yes'
                   or t.get('shop') == 'ticket')
        return (roofish or b.poly.area < 90) and b.poly.area < 160 and not _fixed(t)
    decks = [(b, f) for b, f in cand.values() if not is_cabin(b)]
    cabs = [(b, f) for b, f in cand.values() if is_cabin(b)]
    stops = []
    on_deck = {}
    for b, f in cabs:
        host = [k for k, (d, _) in enumerate(decks) if d.poly.intersection(b.poly).area >= 0.5 * b.poly.area]
        if host: on_deck.setdefault(host[0], []).append(b)
        else: stops.append(dict(id=b.id, ferry=f, fixed=False, name=b.tags.get('name', ''), hull=_frame_buf(b.poly), cabins=[b.poly]))
    for k, (d, f) in enumerate(decks):
        fixed = _fixed(d.tags)
        cb = [c.poly for c in on_deck.get(k, [])]
        if not cb and f and not fixed:                     # a ferry pontoon without a mapped roof: cabin on the inset deck
            c, u, v, hu, hv = _frame(d.poly)
            if hu > 2.5 and hv > 1.6: cb = [_rect(c, u, v, hu - 1.2, hv - 0.8)]
        stops.append(dict(id=d.id, ferry=f or bool(cb), fixed=fixed, name=d.tags.get('name', ''), hull=d.poly.simplify(0.1), cabins=cb))
    # hulls float clear of the quay and of each other; fixed piers (paved jetties on piles) meet the quay
    out = []; taken = []
    for s in sorted(stops, key=lambda s: (not s['fixed'], -s['hull'].area)):
        h = s['hull'].difference(land if s['fixed'] else land.buffer(0.35, join_style=2))
        for q in taken: h = h.difference(q.buffer(0.15, join_style=2))
        h0 = s['hull'].area; h = _largest(h.buffer(0))
        if h is None or h.area < 0.45 * h0 or h.area < 6: continue
        s['hull'] = h; s['z'] = GZ if s['fixed'] else ZD; s['arrive'] = []; taken.append(h)
        s['cabins'] = [cr for cr in (_cabin(c, h) for c in s['cabins']) if cr is not None]
        out.append(s)
    _gangways(world, out)
    for s in out:
        s['c'] = tuple(np.array(s['hull'].centroid.coords[0]))
        _openings(s)
    ships_out = []
    for b in ships:
        c, u, v, hu, hv = _frame(b.poly)
        ships_out.append(dict(id=b.id, ship=b.tags.get('ship:type', ''), name=b.tags.get('name', ''), c=tuple(c), u=tuple(u), L=2 * hu, B=2 * hv))
    drop = set(cand) | {b.id for b in ships}
    world.buildings = [b for b in world.buildings if b.id not in drop]
    return out, ships_out

PAVED = ('sett', 'paving_stones', 'stone', 'concrete', 'asphalt', 'paved')

def _fixed(t):
    """a jetty on piles paved like the quay (OSM: a pier that is also a street), not a floating pontoon."""
    return t.get('man_made') == 'pier' and (t.get('highway') in PEDESTRIAN or t.get('surface') in PAVED)

def _frame_buf(poly):
    """pontoon hull around a mapped roof / shelter: its rectangle with a margin."""
    c, u, v, hu, hv = _frame(poly)
    return _rect(c, u, v, hu + 0.6, hv + 0.6)

def _cabin(poly, hull):
    """cabin rectangle (c, u, v, hu, hv) inside the hull: the roof outline less the overhang."""
    c, u, v, hu, hv = _frame(poly)
    r = _rect(c, u, v, max(hu - 0.3, 0.8), max(hv - 0.3, 0.8)).intersection(hull.buffer(-0.3, join_style=2))
    r = _largest(r) if not r.is_empty else None
    if r is None or r.area < 4.0: return None
    c, u, v, hu, hv = _frame(r)
    if hv < 0.9: return None
    return dict(c=c, u=u, v=v, hu=hu, hv=hv)

def _gangways(world, stops):
    """s['gang'] = [{'a', 'za', 'b', 'zb'}]: from a (the quay, or a neighbouring pontoon already reached) to b on this
    hull.  To the quay: straight out from a side of the hull, square to it, as far as the quay (OSM draws gangways as
    fans of lines from one landing to several pontoons; they only say where along the hull the gangway is).  A gangway
    may not cross another pontoon nor land against a building.  Pontoons still unreached hang off the nearest reached
    one (San Zaccaria, the Giardinetti)."""
    land = world.land; o = world.o
    lines = []
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if 'building' in t or t.get('area') == 'yes': continue
        if t.get('highway') not in PEDESTRIAN and t.get('man_made') != 'pier': continue
        P = o.way_xy(wid)
        if len(P) >= 2: lines.append(LineString(P))
    tree = shapely.STRtree(lines)
    htree = shapely.STRtree([s['hull'] for s in stops])
    bpolys = [b.poly for b in world.buildings]; btree = shapely.STRtree(bpolys)
    def in_building(p):
        """inside a building with no mapped path through it there (a portico or a sottoportego is a way in)"""
        q = Point(*p)
        for k in btree.query(q):
            if not bpolys[k].contains(q): continue
            return not any(lines[i].distance(q) < 1.0 and lines[i].intersection(bpolys[k]).length > 2.0 for i in tree.query(q.buffer(1.0)))
        return False
    for si, s in enumerate(stops):
        h = s['hull']; s['gang'] = []
        loc = land.intersection(h.buffer(GANG_OSM + 10).envelope); lb = loc.boundary
        if loc.is_empty: continue                                   # out in the lagoon: reached by boat only
        if s['fixed'] and h.distance(loc) < 0.6: s['reached'] = True; continue
        hints = []; direct = []
        for k in tree.query(h.buffer(2.0)):
            g = lines[k].difference(loc).difference(h)
            for pc in (g.geoms if hasattr(g, 'geoms') else [g]):
                if pc.is_empty or pc.geom_type != 'LineString' or pc.length < 0.2 or pc.length > GANG_OSM: continue
                a, b = Point(pc.coords[0]), Point(pc.coords[-1])
                if a.distance(h) < b.distance(h): a, b = b, a
                if a.distance(lb) < 0.8 and b.distance(h) < 0.8:
                    hints.append(np.array(b.coords[0]))
                    direct.append((np.array(nearest_points(lb, a)[0].coords[0]), np.array(nearest_points(h.exterior, b)[0].coords[0])))
        c, u, v, hu, hv = _frame(h)
        cands = []
        def consider(score, t, nrm, p0, pl):
            L = float(np.linalg.norm(pl - p0))
            if L < 0.05: return
            dd = (pl - p0) / L
            lane = LineString([tuple(p0 + dd * 0.05), tuple(pl)]).buffer(GW / 2 - 0.25, cap_style=2)
            if any(k != si and stops[k]['hull'].intersects(lane) for k in htree.query(lane)): return
            if in_building(pl + dd * 1.2): return                                  # would land against a wall
            cands.append((score + L, t, nrm, p0, pl))
        # square to a side of the hull, where OSM puts the gangway (bonus) or along the side
        for nrm, along, ha, hn in ((v, u, hu, hv), (-v, u, hu, hv), (u, v, hv, hu), (-u, v, hv, hu)):
            if ha < 1.0: continue
            ts = [(float(np.clip(np.dot(q - c, along), -ha + 1.0, ha - 1.0)), True) for q in hints if np.dot(q - c, nrm) > hn - 1.5]
            ts += [(t, False) for t in (0.0, -(ha - 1.0) * 0.5, (ha - 1.0) * 0.5)]
            for t, hinted in ts:
                p0 = c + along * t + nrm * hn
                hit = LineString([tuple(p0), tuple(p0 + nrm * (GANG_OSM if hinted else GANG_MAX))]).intersection(lb)
                if hit.is_empty: continue
                consider(-3.0 if hinted else 0.0, t, nrm, p0, np.array(nearest_points(hit, Point(*p0))[0].coords[0]))
        # else along an OSM line, else the shortest way
        for pl, ph in direct: consider(2.0, 0.0, (pl - ph) / max(np.linalg.norm(pl - ph), 1e-9), ph, pl)
        if not cands:
            pa, pb = nearest_points(lb, h.exterior)
            if pa.distance(pb) <= GANG_MAX:
                pl = np.array(pa.coords[0]); ph = np.array(pb.coords[0])
                consider(4.0, 0.0, (pl - ph) / max(np.linalg.norm(pl - ph), 1e-9), ph, pl)
        cands.sort(key=lambda c_: c_[0])
        pick = []
        for cd in cands:
            if not pick or (h.area > 250 and len(pick) < 2 and all(abs(cd[1] - q[1]) > 8.0 or np.dot(cd[2], q[2]) < 0.5 for q in pick)):
                pick.append(cd)
        s['gang'] = [dict(a=tuple(pl), za=GZ, b=tuple(p0), zb=s['z']) for (_, _, _, p0, pl) in pick]
        s['reached'] = bool(s['gang'])
    # pontoons moored to other pontoons
    for _ in range(4):
        grew = False
        for s in stops:
            if s.get('reached'): continue
            best = None
            for o_ in stops:
                if o_ is s or not o_.get('reached'): continue
                d = s['hull'].distance(o_['hull'])
                if d <= LINK_MAX and (best is None or d < best[0]): best = (d, o_)
            if best is None: continue
            o_ = best[1]
            pa, pb = nearest_points(o_['hull'].exterior, s['hull'].exterior)
            a = np.array(pa.coords[0]); b = np.array(pb.coords[0])
            if np.linalg.norm(b - a) < 0.6:                     # side by side: a short bridge plate across the gap
                dvec = b - a if np.linalg.norm(b - a) > 1e-3 else np.array(s['hull'].centroid.coords[0]) - a
                dvec = dvec / max(np.linalg.norm(dvec), 1e-9); a = a - dvec * 0.3; b = b + dvec * 0.3
            s['gang'] = [dict(a=tuple(a), za=o_['z'], b=tuple(b), zb=s['z'])]
            o_['arrive'].append(tuple(a)); s['reached'] = True; grew = True
        if not grew: break

def _openings(s):
    """each cabin: which of its walls face land (glazed) and water (open), and the doorways where gangways arrive."""
    pts = [np.array(g['b']) for g in s['gang']] + [np.array(p) for p in s['arrive']]
    for cb in s['cabins']:
        c, u, v, hu, hv = cb['c'], cb['u'], cb['v'], cb['hu'], cb['hv']
        # land side of the cabin: towards the gangways (else the -v side)
        if pts:
            m = np.mean(pts, axis=0)
            cb['land'] = 1 if np.dot(m - c, v) > 0 else -1
        else: cb['land'] = -1
        doors = {('v', 1): [], ('v', -1): [], ('u', 1): [], ('u', -1): []}
        for ph in pts:
            q = ph - c; pu, pv = np.dot(q, u), np.dot(q, v)
            if abs(pu) <= hu + 0.3:
                doors[('v', 1 if pv > 0 else -1)].append(float(np.clip(pu, -hu + 1.1, hu - 1.1)))
            else:
                doors[('u', 1 if pu > 0 else -1)].append(float(np.clip(pv, -hv + 0.9, hv - 0.9)))
        cb['doors'] = {f'{a}{b}': d for (a, b), d in doors.items()}


# ================================================================================================ geometry
def _post(m, p, z0, z1, r, mat):
    m.merge(G.box(p[0] - r, p[1] - r, z0, p[0] + r, p[1] + r, z1, mat))

def _plate(m, a, b, z0, z1, t, mat):
    """a vertical plate along a->b (2D), thickness t, from z0 to z1."""
    a = np.array(a, float); b = np.array(b, float); d = b - a; L = np.linalg.norm(d)
    if L < 0.02: return
    d /= L; n = np.array([-d[1], d[0]]) * t / 2
    q = [a - n, b - n, b + n, a + n]
    m.merge(G.prism([[tuple(p) for p in q]], z0, z1, mat, top=True, bottom=True))

def _runs(L, doors, dw):
    """solid runs [s0, s1] of a wall 0..L with doorways of width dw centred at the door positions (0 = wall middle)."""
    cuts = sorted((L / 2 + d - dw / 2, L / 2 + d + dw / 2) for d in doors)
    runs = []; s = 0.0
    for a, b in cuts:
        if a > s + 0.05: runs.append((s, a))
        s = max(s, b)
    if s < L - 0.05: runs.append((s, L))
    return runs

def _glazed_wall(m, a, b, doors, z, posts_every=1.8, dw=2.0):
    """a pontoon cabin wall a->b: steel posts, a painted lower panel, glass, a top rail; doorways left open."""
    a = np.array(a, float); b = np.array(b, float); d = b - a; L = np.linalg.norm(d); d /= L
    at = lambda s: a + d * s
    for s0, s1 in _runs(L, doors, dw):
        n = max(1, int(math.ceil((s1 - s0) / posts_every)))
        for k in range(n + 1): _post(m, at(s0 + (s1 - s0) * k / n), z, z + WALL, 0.05, 'actv_paint')
        _plate(m, at(s0), at(s1), z, z + 0.95, 0.05, 'actv_paint')
        _plate(m, at(s0), at(s1), z + 0.95, z + 2.40, 0.02, 'glass')
    _plate(m, a, b, z + 2.40, z + WALL, 0.10, 'actv_paint')            # header over walls and doorways alike

def _open_side(m, a, b, z, ferry):
    """the boarding side: posts and a waist-high rail with every other bay open."""
    a = np.array(a, float); b = np.array(b, float); d = b - a; L = np.linalg.norm(d); d /= L
    n = max(2, int(round(L / 2.6)))
    for k in range(n + 1):
        p = a + d * (L * k / n)
        _post(m, p, z, z + WALL, 0.06, 'actv_paint')
        if k < n and k % 2 == 1:
            q = a + d * (L * (k + 1) / n)
            _plate(m, p, q, z + 0.95, z + 1.05, 0.06, 'actv_yellow' if ferry else 'actv_paint')
            _plate(m, p, q, z + 0.45, z + 0.50, 0.04, 'cast_iron')
    _plate(m, a, b, z + 2.40, z + WALL, 0.10, 'actv_paint')

def _quad(m, q, want, mat):
    """a planar quad turned to face the direction want."""
    nrm = np.cross(q[1] - q[0], q[2] - q[0])
    m.poly([tuple(p) for p in (q if np.dot(nrm, want) >= 0 else q[::-1])], mat)

def _slab(m, pts, hw, th, mat, top_mat=None):
    """a gangway floor: centre line pts [(x, y, z)], half width hw, thickness th (quads between stations)."""
    P = np.array(pts, float)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; d = (b - a)[:2]; d = d / max(np.linalg.norm(d), 1e-9); n = np.array([-d[1], d[0], 0.0]) * hw
        A0, A1, B0, B1 = a - n, a + n, b - n, b + n
        dz = np.array([0, 0, th])
        m.poly([tuple(A0), tuple(B0), tuple(B1), tuple(A1)], top_mat or mat)                         # top
        m.poly([tuple(A1 - dz), tuple(B1 - dz), tuple(B0 - dz), tuple(A0 - dz)], mat)                # bottom
        m.poly([tuple(A0 - dz), tuple(B0 - dz), tuple(B0), tuple(A0)], mat)
        m.poly([tuple(B1 - dz), tuple(A1 - dz), tuple(A1), tuple(B1)], mat)

def _run(g):
    """length of a gangway's slope: at least 1 in 6, so a pontoon moored right at the quay gets a ramp onto its deck."""
    return max(float(np.linalg.norm(np.array(g['b']) - np.array(g['a']))), abs(g['za'] - g['zb']) * 6.0)

def _gangway(m, g, ferry):
    pl = np.array(g['a'], float); ph = np.array(g['b'], float); za, zb = g['za'], g['zb']
    d = ph - pl; L = _run(g); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
    s0, s1 = -0.5, L + 0.6
    z = lambda s: za + 0.03 if s <= 0 else zb + 0.03 if s >= L else za + 0.03 + (zb - za) * s / L
    st = [s0, 0.0, L, s1]
    _slab(m, [(*(pl + d * s), z(s)) for s in st], GW / 2, 0.12, 'actv_paint', 'wood_raw')
    for side in (-1, 1):
        o = n * side * (GW / 2 - 0.03)
        # steel side panels following the slope, with a yellow band (ACTV) and a dark handrail on top
        for (sa, sb) in ((0.0, L),):
            A = pl + d * sa + o; B = pl + d * sb + o
            q = [np.array(p) for p in ((*A, z(sa)), (*B, z(sb)), (*B, z(sb) + 1.0), (*A, z(sa) + 1.0))]
            nn = np.array([*(n * side), 0.0])
            _quad(m, q, nn, 'actv_paint')                                                            # outer face
            _quad(m, [p - nn * 0.04 for p in q], -nn, 'actv_paint')                                  # inner face
            if ferry:
                yb = [np.array(p) + nn * 0.006 for p in ((*A, z(sa) + 0.70), (*B, z(sb) + 0.70), (*B, z(sb) + 0.86), (*A, z(sa) + 0.86))]
                _quad(m, yb, nn, 'actv_yellow')
            _slab(m, [(*A - n * side * 0.02, z(sa) + 1.06), (*B - n * side * 0.02, z(sb) + 1.06)], 0.04, 0.06, 'cast_iron')

def _cabin_geom(m, s, cb):
    c, u, v, hu, hv = cb['c'], cb['u'], cb['v'], cb['hu'], cb['hv']
    land = cb['land']; ferry = s['ferry']; doors = cb['doors']
    P = lambda a, b: c + u * a + v * b
    z = s['z']
    # land side (glazed), ends (glazed), water side (open)
    _glazed_wall(m, P(-hu, land * hv), P(hu, land * hv), doors[f'v{land}'], z)
    _open_side(m, P(-hu, -land * hv), P(hu, -land * hv), z, ferry)
    for su in (-1, 1):
        _glazed_wall(m, P(su * hu, -hv), P(su * hu, hv), doors[f'u{su}'], z)
    # benches along the glazed back between doorways
    for a0, a1 in _runs(2 * hu, doors[f'v{land}'], 2.4):
        if a1 - a0 < 2.0: continue
        a0 += 0.3 - hu; a1 += -0.3 - hu
        b0 = land * (hv - 0.55); b1 = land * (hv - 0.12)
        q = [tuple(P(a0, b0)), tuple(P(a1, b0)), tuple(P(a1, b1)), tuple(P(a0, b1))]
        m.merge(G.prism([q], z + 0.42, z + 0.47, 'wood_raw', bottom=True))
        k = max(1, int((a1 - a0) / 1.6))
        for i in range(k + 1):
            p = P(a0 + (a1 - a0) * i / k, land * (hv - 0.33)); _post(m, p, z, z + 0.42, 0.03, 'cast_iron')
    # roof: slab with painted fascia and soffit, lead-grey top; lamps under it
    R = [tuple(P(su * (hu + OVER), sv * (hv + OVER))) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    zr = z + WALL
    m.merge(G.prism([R], zr, zr + ROOF, 'actv_paint', mat_top='lead', bottom=True))
    if ferry:
        # name boards on both long sides, standing on the roof edge
        bl = min(2 * hu * 0.7, 7.0)
        for sv in (-1, 1):
            a = P(-bl / 2, sv * (hv + OVER - 0.05)); b = P(bl / 2, sv * (hv + OVER - 0.05))
            _plate(m, a, b, zr + ROOF, zr + ROOF + 0.42, 0.07, 'actv_yellow')
    nl = max(1, int(round(2 * hu / 4.0)))
    for i in range(nl):
        a = -hu + 2 * hu * (i + 0.5) / nl
        q = [tuple(P(a - 0.35, -0.07)), tuple(P(a + 0.35, -0.07)), tuple(P(a + 0.35, 0.07)), tuple(P(a - 0.35, 0.07))]
        m.merge(G.prism([q], zr - 0.06, zr, 'street_glass', bottom=True))

def _hull(m, s):
    h = s['hull']; ring = [list(h.exterior.coords)[:-1]]
    if s['fixed']:
        # a paved jetty on piles: brick sides with an Istrian coping, paved like the quay
        m.merge(G.prism(ring, -0.4, GZ - 0.14, 'riva', top=False))
        m.merge(G.prism(ring, GZ - 0.14, GZ, 'coping', mat_top='ground'))
        return
    m.merge(G.prism(ring, ZH, ZD - 0.08, 'hull_paint', top=False))
    m.merge(G.prism(ring, ZD - 0.08, ZD, 'hull_paint', mat_top='wood_raw'))
    f = h.buffer(0.10, join_style=2)
    m.merge(G.prism([list(f.exterior.coords)[:-1], list(h.exterior.coords)[:-1]], 0.28, 0.54, 'dark', top=True, bottom=True))
    c, u, v, hu, hv = _frame(h)
    # the boarding side: away from the gangways (else away from land)
    pts = [np.array(g['b']) for g in s['gang']] + [np.array(p) for p in s['arrive']]
    if pts:
        m_ = np.mean(pts, axis=0); sd = -1 if np.dot(m_ - c, v) > 0 else 1
    else: sd = 1
    if s['ferry']:
        e0 = c + v * sd * (hv - 0.09) - u * (hu - 0.3); e1 = c + v * sd * (hv - 0.09) + u * (hu - 0.3)
        _plate(m, e0, e1, ZD, ZD + 0.012, 0.14, 'actv_yellow')
    for su in (-1, 1):
        p = c + v * sd * (hv - 0.35) + u * su * (hu - 0.9)
        m.merge(G.cylinder(0.11, ZD, ZD + 0.32, 10, 'cast_iron', top=True, center=(p[0], p[1])))

def _ship(mb, sh):
    """a moored boat filling the OSM outline: a bragozzo (two masts, furled ochre sails) or a tug (wheelhouse)."""
    from .props import hull_sections, loft, box as pbox, lathe
    from .mesh import MeshBuilder
    from .materials import MAT
    L, B = sh['L'], sh['B']
    t = MeshBuilder()
    if 'tug' in sh['ship']:
        secs = hull_sections(L * 0.97, B * 0.95, 2.0, 0.25, 0.35, bow_up=0.4)
        loft(t, secs, MAT['wood_paint'], c0=(28, 30, 34, 0))
        pbox(t, -L * 0.30, -B * 0.42, 1.95, L * 0.30, B * 0.42, 2.05, MAT['wood_raw'])
        pbox(t, -L * 0.12, -B * 0.30, 2.05, L * 0.18, B * 0.30, 3.9, MAT['wood_paint'], c0=(232, 228, 220, 0))
        pbox(t, L * 0.05, -B * 0.31, 3.0, L * 0.18, B * 0.31, 3.6, MAT['glass'])
        pbox(t, -L * 0.15, -B * 0.34, 3.9, L * 0.22, B * 0.34, 4.05, MAT['wood_paint'], c0=(150, 30, 26, 0))
        lathe(t, [(0.28, 0), (0.28, 1.5), (0.24, 1.6)], 12, MAT['wood_paint'], c0=(150, 30, 26, 0), x=-L * 0.05, z=3.9, cap_top=True)
        zoff = -1.0
    else:
        secs = hull_sections(L * 0.97, B * 0.95, 1.6, 0.3, 0.45, bow_up=0.5, stern_up=0.3)
        loft(t, secs, MAT['wood_paint'], c0=(36, 26, 20, 0))
        pbox(t, -L * 0.40, -B * 0.40, 1.55, L * 0.40, B * 0.40, 1.62, MAT['wood_raw'])
        for x, h in ((L * 0.22, 11.0), (-L * 0.18, 8.5)):
            lathe(t, [(0.13, 0), (0.09, h)], 10, MAT['wood_raw'], x=x, z=1.6, cap_top=True)
            # furled sail along a yard: an ochre-red roll
            lathe(t, [(0.0, 0), (0.22, 0.3), (0.25, h * 0.55), (0.0, h * 0.62)], 10, MAT['wood_paint'], c0=(176, 84, 40, 0), x=x - 0.3, z=1.9)
        zoff = -0.8
    yaw = math.atan2(sh['u'][1], sh['u'][0])
    cz, sz = math.cos(yaw), math.sin(yaw)
    Rm = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1.0]])
    for p in t.parts:
        p['P'] = (p['P'] @ Rm.T + np.array([sh['c'][0], sh['c'][1], zoff])).astype(np.float32)
        p['N'] = (p['N'] @ Rm.T).astype(np.float32)
    mb.merge(t)

def build(mb, item):
    if 'ship' in item:
        _ship(mb, item); return {'ship': item['name'] or item['id']}
    m = G.Mesh()
    _hull(m, item)
    for cb in item['cabins']: _cabin_geom(m, item, cb)
    for g in item['gang']: _gangway(m, g, item['ferry'])
    to_builder(m, mb, max_edge=1.5)
    return {'stop': item['name'] or item['id'], 'cabins': len(item['cabins']), 'gangways': len(item['gang'])}


def drop_stop_bridges(stops, brs):
    """OSM tags the gangways out to the stops as bridges (a fan of them at the Ferrovia); the stops bring their own.
    Bridges reaching a hull, and every piece joined end to end to one, are left out."""
    hulls = [s['hull'] for s in stops]; htree = shapely.STRtree(hulls)
    def to_stop(br):
        g = LineString([tuple(br['a']), tuple(br['b'])]).buffer(1.0)
        return any(hulls[k].intersects(g) for k in htree.query(g))
    drop = {k for k, br in enumerate(brs) if to_stop(br)}
    ends = [(tuple(np.round(br['a'] * 2) / 2), tuple(np.round(br['b'] * 2) / 2)) for br in brs]
    grew = True
    while grew:
        grew = False
        live = {e for k in drop for e in ends[k]}
        for k, (ea, eb) in enumerate(ends):
            if k not in drop and (ea in live or eb in live): drop.add(k); grew = True
    return [br for k, br in enumerate(brs) if k not in drop]


# ================================================================================================ walking
def walk_areas(world):
    """decks (flat at ZD), cabin walls (blocked), gangways (ramps from the quay down to the deck)."""
    out = []
    for s in world.stops:
        out.append((s['hull'].buffer(-0.22, join_style=2) if not s['fixed'] else s['hull'], s['z']))
        for cb in s['cabins']:
            c, u, v, hu, hv = cb['c'], cb['u'], cb['v'], cb['hu'], cb['hv']
            P = lambda a, b: tuple(c + u * a + v * b)
            land = cb['land']
            walls = [(P(-hu, land * hv), P(hu, land * hv), cb['doors'][f'v{land}'])]
            for su in (-1, 1):
                walls.append((P(su * hu, -hv), P(su * hu, hv), cb['doors'][f'u{su}']))
            for a, b, doors in walls:
                a = np.array(a); b = np.array(b); L = np.linalg.norm(b - a); d = (b - a) / L
                for s0, s1 in _runs(L, doors, 2.0):
                    out.append((LineString([tuple(a + d * s0), tuple(a + d * s1)]).buffer(0.14, cap_style=2), None))
            # the open side's posts and rails do not block: boarding is along it
        for g in s['gang']:
            pl = np.array(g['a']); ph = np.array(g['b']); L = _run(g); d = (ph - pl) / np.linalg.norm(ph - pl)
            ph = pl + d * L
            lane = LineString([tuple(pl - d * 0.6), tuple(ph + d * 0.7)]).buffer(GW / 2 - 0.12, cap_style=2)
            out.append((lane, {'a': [float(pl[0]), float(pl[1])], 'd': [float(d[0]), float(d[1])],
                               'prof': [(-0.6, g['za']), (0.0, g['za']), (L, g['zb']), (L + 0.7, g['zb'])]}))
    return out


if __name__ == '__main__':
    from .world import load
    w = load()
    print(len(w.stops), 'stops', len(w.ships), 'ships')
    for s in w.stops:
        c = s['c']
        print(f"{s['id']:12s} ({c[0]:7.0f},{c[1]:6.0f}) hull {s['hull'].area:5.0f} m2  cabins {len(s['cabins'])}  gangways {len(s['gang'])}  ferry {int(s['ferry'])}  {s['name']}")
    for sh in w.ships: print('ship', sh)
