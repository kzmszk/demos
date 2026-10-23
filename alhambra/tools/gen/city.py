"""Granada around the Alhambra from OpenStreetMap (ODbL) building footprints and parts (cadastre
levels), standing on the IGN DEM: walls carry metre UVs (the viewer draws whitewashed / stucco / stone
facades storey by storey), roofs are tiled hips/gables (clay barrel tiles) or flat terraces.

Output: public/data/city.bin (gzip). Header JSON lists chunks; each chunk has three meshes (walls,
tiles, flats) as int16 positions (2 cm, relative to the chunk origin), int16 UVs (cm), uint8 RGBA
(tint + facade style), uint16/uint32 indices."""
import gzip, json, math, os, struct, sys
from collections import defaultdict
from multiprocessing import Pool
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box as sbox
from shapely.strtree import STRtree
from shapely.ops import unary_union
import osm, terrain
from frame import PUBLIC

EXTENT = (-3000, 2400, -2400, 2200)          # the main-pass terrain (ring 1)
CHUNK = 400.0
STOREY, GROUND_STOREY = 3.0, 3.5
OVERHANG = .32

def hero_zone():
    per = terrain.perimeter()
    # everything inside the enclosure is hand-built (tools/web/heroes/*), as is the Generalife
    zones = [per.buffer(2), Point(-56, 125).buffer(26), sbox(316, -142, 442, 208)]
    return unary_union(zones)

def historic(x, z):
    """0..1: Albaicín, Sacromonte, the old centre and the Realejo (whitewash, tiled roofs)."""
    a = np.clip(1 - (np.hypot((x + 450) / 1250, (z + 420) / 650) - .75) / .4, 0, 1)      # Albaicín/Sacromonte
    b = np.clip(1 - (np.hypot((x + 650) / 700, (z - 280) / 500) - .7) / .4, 0, 1)        # Realejo/centro
    return np.maximum(a, b)

def levels_of(t, default):
    for k in ('building:levels',):
        v = t.get(k)
        if v:
            try: return max(0.0, float(v.split(';')[0].replace(',', '.')))
            except ValueError: pass
    return default

def height_of(t, L):
    h = t.get('height')
    if h:
        try: return float(h.split()[0].replace(',', '.'))
        except ValueError: pass
    if L <= 0: return 0
    return GROUND_STOREY + STOREY * (L - 1) + .45

def rnd(seed):
    return np.random.default_rng(seed & 0xffffffff)

def pieces():
    data = osm.load()
    x0, x1, z0, z1 = EXTENT
    ext = sbox(x0, z0, x1, z1)
    hero = hero_zone()
    blds = [a for a in data['areas'] if 'building' in a['tags'] and a['tags'].get('building') not in ('roof', 'carport', 'ruins', 'construction', 'no')
            and a['g'].geom_type in ('Polygon', 'MultiPolygon') and a['g'].representative_point().within(ext)]
    parts = [a for a in data['areas'] if 'building:part' in a['tags'] and a['tags'].get('building:part') not in ('roof', 'no')
             and a['g'].geom_type in ('Polygon', 'MultiPolygon') and a['g'].representative_point().within(ext)]
    tree = STRtree([b['g'] for b in blds])
    owner = defaultdict(list)
    for p in parts:
        rp = p['g'].representative_point()
        for i in tree.query(rp, predicate='within'):
            owner[int(i)].append(p); break
    out = []
    towers = [p['g'].centroid for p in parts + blds if p['tags'].get('tower:type') == 'bell_tower' or p['tags'].get('building') == 'tower']
    for i, b in enumerate(blds):
        t = b['tags']; rp = b['g'].representative_point()
        name = t.get('name', '')
        if rp.within(hero): continue
        if name.startswith('Torre') and name != 'Torres Bermejas' and abs(rp.x) < 700 and abs(rp.y) < 500: continue
        kind = t.get('building')
        church = kind in ('church', 'cathedral', 'chapel', 'basilica', 'monastery', 'convent') or t.get('amenity') == 'place_of_worship'
        monument = church or 'historic' in t or kind in ('public',) and t.get('historic')
        hz = float(historic(rp.x, rp.y))
        default = 2 if hz > .5 else 3
        L = levels_of(t, default)
        list_ = owner.get(i) or [b]
        if math.hypot(rp.x, rp.y) > 1500 and len(list_) > 1:
            # far away: one volume per building, parts' levels averaged by area
            tot = sum(p['g'].area for p in list_)
            L = sum(levels_of(p['tags'], L) * p['g'].area for p in list_) / max(tot, 1e-6)
            list_ = [b]
        for p in list_:
            pt = p['tags'] if p is not b else t
            Lp = levels_of(pt, L if p is b else 1)
            if p is not b and pt.get('building:levels') is None: Lp = L
            h = height_of(pt, Lp)
            if h <= .5: continue
            minh = 0.0
            if pt.get('building:min_level'):
                try: minh = GROUND_STOREY + STOREY * (float(pt['building:min_level']) - 1)
                except ValueError: pass
            geoms = [p['g']] if p['g'].geom_type == 'Polygon' else list(p['g'].geoms)
            tower = pt.get('tower:type') == 'bell_tower' or pt.get('building') == 'tower' or pt.get('man_made') == 'tower' and pt.get('tower:type') != 'defensive'
            if church and not pt.get('height') and not tower:
                h = max(h, 9.0 if b['g'].area < 900 else 14.0 if b['g'].area < 3000 else 26.0)
            for g in geoms:
                if g.area < 6: continue
                out.append({'id': b['id'] * 64 + len(out) % 64, 'bid': b['id'], 'g': g, 'h': h, 'L': Lp, 'minh': minh,
                            'roof': 'pyramid' if tower else pt.get('roof:shape') or (t.get('roof:shape') if p is b else None),
                            'church': church, 'monument': bool(monument), 'hz': hz, 'kind': kind, 'tower': tower})
        # most churches of the Albaicín and the centre carry a bell tower that OSM does not map
        if church and 250 < b['g'].area < 4000 and not any(tw.distance(b['g']) < 25 for tw in towers):
            ctr, ax, nx_, L_, W_ = obb(b['g'])
            side = max(3.6, min(6.5, W_ * .32))
            c = ctr + ax * (L_ / 2 - side / 2) + nx_ * (W_ / 2 - side / 2) * (1 if b['id'] % 2 else -1)
            sq = Polygon([tuple(c + ax * a * side / 2 + nx_ * bb * side / 2) for a, bb in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            th = max(14.0, (L * 3.2 if L else 9) * 1.9) if b['g'].area < 3000 else 42.0
            out.append({'id': b['id'] * 64 + 63, 'bid': b['id'] + 1, 'g': sq, 'h': th, 'L': max(4, int(th / 3)), 'minh': 0.0, 'roof': 'pyramid',
                        'church': True, 'monument': True, 'hz': hz, 'kind': 'tower', 'tower': True})
    # the Nasrid and Zirid walls of the Albaicín and the Alcazaba Qadima (outside the Alhambra)
    per = terrain.perimeter()
    for l in data['lines']:
        t = l['tags']
        if not (t.get('barrier') == 'city_wall' or t.get('historic') == 'citywalls'): continue
        g = l['g'].intersection(ext)
        if g.is_empty or g.distance(per) < 5: continue
        # short pieces, so the wall steps down the hillside instead of standing as one slab
        from shapely.ops import substring
        k = 0
        for seg in getattr(g, 'geoms', [g]):
            if seg.geom_type != 'LineString' or seg.length < 4: continue
            n = max(1, int(math.ceil(seg.length / 7)))
            for j in range(n):
                piece = substring(seg, j / n, (j + 1) / n, normalized=True)
                if piece.length < .5: continue
                poly = piece.buffer(1.1, cap_style='flat', join_style='mitre')
                for q in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
                    out.append({'id': l['id'] * 64 + k % 64, 'bid': -l['id'], 'g': q, 'h': 8.5, 'L': 3, 'minh': 0.0, 'roof': 'flat', 'church': False,
                                'monument': True, 'hz': 1.0, 'kind': 'wall', 'tower': False, 'citywall': True}); k += 1
    return out

# ------------------------------------------------------------------ geometry helpers
class Mesh:
    def __init__(self): self.p = []; self.uv = []; self.c = []; self.i = []; self.face = None
    def add(self, pts, uvs, col, tris):
        base = len(self.p)
        self.p.extend(pts); self.uv.extend(uvs); self.c.extend([col] * len(pts))
        self.i.extend([base + t for t in tris])
    def begin_face(self): self.face = {}
    def add_shared(self, pts, uvs, col, tris):
        """Like add, but vertices repeat within the current face are shared."""
        ids = []
        for p, uv in zip(pts, uvs):
            k = (round(p[0], 2), round(p[1], 2), round(p[2], 2))
            j = self.face.get(k)
            if j is None:
                j = len(self.p); self.face[k] = j; self.p.append(p); self.uv.append(uv); self.c.append(col)
            ids.append(j)
        self.i.extend([ids[t] for t in tris])

def obb(poly):
    r = poly.minimum_rotated_rectangle
    c = np.array(r.exterior.coords[:4])
    e1, e2 = c[1] - c[0], c[2] - c[1]
    l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
    if l1 >= l2: ax, L, W = e1 / l1, l1, l2
    else: ax, L, W = e2 / l2, l2, l1
    ctr = c.mean(0)
    return ctr, ax, np.array([-ax[1], ax[0]]), L, W

def roof_fn(kind, L, W, tanp):
    if kind == 'hip':
        return lambda s, t: np.minimum(W / 2 - np.abs(t), L / 2 - np.abs(s)) * tanp
    return lambda s, t: (W / 2 - np.abs(t)) * tanp

def face_polys(kind, L, W, o):
    """Plan faces of the roof on the OBB expanded by the overhang, in (s, t) coordinates."""
    a, b = L / 2 + o, W / 2 + o
    if kind == 'hip':
        r = max(0.0, L / 2 - W / 2)
        return [('s+', [(-a, b), (a, b), (r, 0), (-r, 0)]), ('s-', [(a, -b), (-a, -b), (-r, 0), (r, 0)]),
                ('e+', [(a, b), (a, -b), (r, 0)]), ('e-', [(-a, -b), (-a, b), (-r, 0)])]
    return [('s+', [(-a, 0), (a, 0), (a, b), (-a, b)]), ('s-', [(-a, -b), (a, -b), (a, 0), (-a, 0)])]

def tri_polygon(poly):
    """Triangles (list of 3 xy tuples) of a polygon, respecting holes."""
    out = []
    try: tris = shapely.constrained_delaunay_triangles(poly)
    except Exception: return out
    for t in getattr(tris, 'geoms', []):
        if t.area < 1e-4: continue
        out.append(list(t.exterior.coords)[:3])
    return out

def build_piece(pc, ground_fn, mesh_w, mesh_r, mesh_f, shared, rng):
    far = math.hypot(pc['g'].centroid.x, pc['g'].centroid.y) > 1200
    g = pc['g'].simplify(.5 if far else .15, preserve_topology=True)
    if g.is_empty or g.area < 6 or g.geom_type != 'Polygon': return 0
    coords = np.array(g.exterior.coords[:-1])
    gnd = ground_fn(coords[:, 0], coords[:, 1])
    ref = float(np.median(gnd))
    near = abs(g.centroid.x) < 650 and abs(g.centroid.y) < 450
    base = float(gnd.min()) - (1.2 if near else 2.6) + pc['minh'] * 0
    top = ref + pc['h']
    bottom_vis = ref + pc['minh']
    area = g.area
    # roof choice
    hz = pc['hz']; tag = pc['roof']
    if tag == 'pyramid': kind = 'hip'
    elif tag in ('flat',): kind = 'flat'
    elif tag in ('gabled', 'side_hipped', 'skillion'): kind = 'gable'
    elif tag in ('hipped', 'pyramidal', 'many', 'multi'): kind = 'hip'
    elif pc['church']: kind = 'gable'
    elif area > 1600 or pc['L'] >= 7: kind = 'flat' if rng.random() < .9 else 'hip'
    elif pc['L'] >= 5: kind = 'flat' if rng.random() < .7 else 'hip'
    else:
        p_pitch = .55 + .35 * hz
        kind = ('hip' if rng.random() < .35 else 'gable') if rng.random() < p_pitch else 'flat'
    ctr, ax, nx_, L, W = obb(g)
    if kind != 'flat' and (W < 2.2 or L / max(W, 1e-3) > 9): kind = 'flat' if W < 2.2 else 'gable'
    tanp = math.tan(math.radians(rng.uniform(19, 25) if not pc['church'] else rng.uniform(26, 32)))
    if pc.get('tower'): tanp = math.tan(math.radians(rng.uniform(38, 50)))
    elif kind != 'flat' and W / 2 * tanp > (9 if pc['church'] else 4.5): tanp = (9 if pc['church'] else 4.5) / (W / 2)
    f = roof_fn(kind, L, W, tanp) if kind != 'flat' else (lambda s, t: np.zeros_like(np.asarray(s, float)))
    def st(x, z):
        d = np.stack([np.asarray(x) - ctr[0], np.asarray(z) - ctr[1]], -1)
        return d @ ax, d @ nx_
    def roof_h(x, z):
        s, t = st(x, z); return f(s, t)
    # style and tints
    style = pc['style']; tint = pc['tint']; rtint = pc['rtint']
    tris = 0
    # ------------------------------------------------ walls
    rings = [np.array(g.exterior.coords)] + [np.array(r.coords) for r in g.interiors]
    partition = []
    if kind == 'gable':
        partition = [LineString([ctr - ax * (L / 2 + 5), ctr + ax * (L / 2 + 5)])]
    elif kind == 'hip':
        r = max(0.0, L / 2 - W / 2)
        e1, e2 = ctr - ax * r, ctr + ax * r
        partition = [LineString([e1, e2])]
        for sx in (-1, 1):
            for sy in (-1, 1):
                corner = ctr + ax * sx * (L / 2 + 3) + nx_ * sy * (W / 2 + 3)
                partition.append(LineString([e2 if sx > 0 else e1, corner]))
    for ring in rings:
        for k in range(len(ring) - 1):
            a, b = ring[k], ring[k + 1]
            seg = b - a; ln = float(np.hypot(*seg))
            if ln < .05: continue
            nrm = np.array([seg[1], -seg[0]]) / ln
            mid = (a + b) / 2
            if g.contains(Point(mid + nrm * .05)): nrm = -nrm
            key = (round(b[0], 2), round(b[1], 2), round(a[0], 2), round(a[1], 2))
            floor = base
            if key in shared:
                other_top = shared[key]
                floor = max(base, other_top)
            # kinks of the roof profile along the edge
            ts = [0.0, 1.0]
            if kind != 'flat':
                edge = LineString([a, b])
                for line in partition:
                    ip = edge.intersection(line)
                    if ip.is_empty or ip.geom_type != 'Point': continue
                    ts.append(float(np.hypot(ip.x - a[0], ip.y - a[1]) / ln))
            ts = sorted(set(min(1, max(0, t)) for t in ts))
            pts = np.array([a + seg * t for t in ts])
            tops = top + np.maximum(0, roof_h(pts[:, 0], pts[:, 1])) if kind != 'flat' else np.full(len(ts), top)
            if np.all(tops <= floor + .05): continue
            # whole bays along the wall: scale u so a 3.6 m bay pattern ends cleanly
            nb = round(ln / 3.6)
            uscale = (nb * 3.6 / ln) if nb >= 1 else .3
            u0 = pc['u0']
            P, UV, T = [], [], []
            for j in range(len(ts) - 1):
                p0, p1 = pts[j], pts[j + 1]; t0, t1 = tops[j], tops[j + 1]
                if max(t0, t1) <= floor: continue
                q = len(P)
                ua, ub = u0 + ts[j] * ln * uscale, u0 + ts[j + 1] * ln * uscale
                P += [(p0[0], floor, p0[1]), (p1[0], floor, p1[1]), (p1[0], max(t1, floor), p1[1]), (p0[0], max(t0, floor), p0[1])]
                UV += [(ua, floor - ref), (ub, floor - ref), (ub, max(t1, floor) - ref), (ua, max(t0, floor) - ref)]
                # winding: outward normal
                e = np.array([p1[0] - p0[0], 0, p1[1] - p0[1]]); up = np.array([0, 1, 0])
                n = np.cross(e, up)  # points to one side
                if n[0] * nrm[0] + n[2] * nrm[1] > 0: T += [q, q + 1, q + 2, q, q + 2, q + 3]
                else: T += [q, q + 2, q + 1, q, q + 3, q + 2]
            if P:
                mesh_w.add(P, UV, (*tint, style), T); tris += len(T) // 3
    # ------------------------------------------------ roof
    if kind == 'flat':
        mesh_f.begin_face()
        for tri in tri_polygon(g):
            P = [(x, top, z) for x, z in tri]
            UV = [(x, z) for x, z in tri]
            # wind upwards
            (ax_, az_), (bx_, bz_), (cx_, cz_) = tri
            cross = (bx_ - ax_) * (cz_ - az_) - (bz_ - az_) * (cx_ - ax_)
            mesh_f.add_shared(P, UV, (*rtint, 0), [0, 2, 1] if cross > 0 else [0, 1, 2]); tris += 1
    else:
        fp = g.buffer(OVERHANG, join_style='mitre', mitre_limit=2.0)
        for name, poly in face_polys(kind, L, W, OVERHANG):
            wp = Polygon([tuple(ctr + ax * s + nx_ * t) for s, t in poly])
            if not wp.is_valid or wp.area < .01: continue
            part = wp.intersection(fp)
            if part.is_empty: continue
            polys = [part] if part.geom_type == 'Polygon' else [q for q in getattr(part, 'geoms', []) if q.geom_type == 'Polygon']
            for q in polys:
                mesh_r.begin_face()
                for tri in tri_polygon(q):
                    xs = np.array([p[0] for p in tri]); zs = np.array([p[1] for p in tri])
                    s, t = st(xs, zs); hh = f(s, t)
                    P = [(xs[k], top + hh[k], zs[k]) for k in range(3)]
                    if name[0] == 's':  # long faces: u along the eave, v up the slope
                        UV = [(s[k], (W / 2 - abs(t[k])) / math.cos(math.atan(tanp))) for k in range(3)]
                    else:
                        UV = [(t[k], (L / 2 - abs(s[k])) / math.cos(math.atan(tanp))) for k in range(3)]
                    (ax_, az_), (bx_, bz_), (cx_, cz_) = tri
                    cross = (bx_ - ax_) * (cz_ - az_) - (bz_ - az_) * (cx_ - ax_)
                    mesh_r.add_shared(P, UV, (*rtint, 0), [0, 2, 1] if cross > 0 else [0, 1, 2]); tris += 1
    return tris

STYLE_WEIGHTS_HIST = [(0, .34), (1, .30), (2, .16), (3, .11), (4, .06), (6, .03)]
STYLE_WEIGHTS_CITY = [(0, .10), (1, .08), (2, .26), (3, .16), (4, .12), (5, .18), (6, .10)]
def choose_style(pc, rng):
    if pc.get('citywall'): return 9
    if pc.get('tower'): return 8 if pc['hz'] > .3 or rng.random() < .5 else 7
    if pc['church'] and pc['hz'] > .4: return 1 if rng.random() < .6 else 7
    if pc['church'] or pc['monument']: return 7
    w = STYLE_WEIGHTS_HIST if rng.random() < pc['hz'] else STYLE_WEIGHTS_CITY
    if pc['L'] >= 6: w = [(5, .45), (2, .2), (6, .2), (3, .15)]
    r = rng.random() * sum(x for _, x in w)
    for s, x in w:
        r -= x
        if r <= 0: return s
    return w[-1][0]

def tints(style, rng):
    if style in (0, 1, 5):
        v = rng.uniform(.9, 1.0); warm = rng.uniform(-.03, .03)
        tint = (v * (1 + warm), v, v * (1 - warm * 1.5))
    else:
        v = rng.uniform(.82, 1.0); tint = (v * rng.uniform(.95, 1.05), v, v * rng.uniform(.92, 1.04))
    tint = tuple(int(np.clip(c, 0, 1) * 255) for c in tint)
    rv = rng.uniform(.72, 1.0); age = rng.uniform(0, 1)
    rtint = tuple(int(np.clip(c, 0, 1) * 255) for c in (rv, rv * (.92 + .1 * age), rv * (.85 + .2 * age)))
    return tint, rtint

def work(args):
    ci, items = args
    gfn = lambda x, z: terrain.heights(np.asarray(x, float), np.asarray(z, float))
    mw, mr, mf = Mesh(), Mesh(), Mesh()
    total = 0
    for pc, shared in items:
        rng = rnd(pc['id'])
        total += build_piece(pc, gfn, mw, mr, mf, shared, rng)
    return ci, mw, mr, mf, total

def pack(mesh, origin):
    if not mesh.p: return None
    p = np.array(mesh.p, np.float64); p[:, 0] -= origin[0]; p[:, 2] -= origin[1]
    q = np.clip(np.round(p / .02), -32767, 32767).astype('<i2')
    uv = np.clip(np.round(np.array(mesh.uv) * 100), -32767, 32767).astype('<i2')
    c = np.array(mesh.c, np.uint8)
    idx = np.array(mesh.i, '<u4' if len(mesh.p) > 65535 else '<u2')
    return q, uv, c, idx

def terrace(pcs):
    """Pieces on steep ground are cut into 6 m strips across the slope, each standing on its own
    ground, so hillside houses step down (as in the Sacromonte and the Realejo) instead of
    standing on one tall wall."""
    out = []
    for pc in pcs:
        g = pc['g']
        if pc.get('citywall') or pc.get('tower') or pc['church']:
            out.append(pc); continue
        c = np.array(g.exterior.coords)
        h = terrain.heights(c[:, 0], c[:, 1])
        if h.max() - h.min() < 6:
            out.append(pc); continue
        A = np.c_[c[:, 0] - c[:, 0].mean(), c[:, 1] - c[:, 1].mean(), np.ones(len(c))]
        gx, gz, _ = np.linalg.lstsq(A, h, rcond=None)[0]
        d = np.array([gx, gz]); n = np.linalg.norm(d)
        if n < 1e-6: out.append(pc); continue
        d /= n; t = c @ d
        steps = max(2, int(math.ceil((t.max() - t.min()) / 6)))
        w = (t.max() - t.min()) / steps; ctr = c.mean(0); perp = np.array([-d[1], d[0]])
        for k in range(steps):
            a0, a1 = t.min() + k * w, t.min() + (k + 1) * w
            band = Polygon([tuple(d * a0 + perp * -1e4), tuple(d * a1 + perp * -1e4), tuple(d * a1 + perp * 1e4), tuple(d * a0 + perp * 1e4)])
            part = g.intersection(band)
            for q in ([part] if part.geom_type == 'Polygon' else [x for x in getattr(part, 'geoms', []) if x.geom_type == 'Polygon']):
                if q.area < 6: continue
                out.append({**pc, 'g': q, 'id': pc['id'] * 7 + k})
    return out

def main():
    pcs = terrace(pieces())
    print('pieces', len(pcs), flush=True)
    # per-piece style/tint shared by all pieces of a building
    by_b = {}
    for pc in pcs:
        if pc['bid'] not in by_b:
            rng = rnd(abs(pc['bid']))
            st_ = choose_style(pc, rng); by_b[pc['bid']] = (st_, *tints(st_, rng))
        pc['style'], pc['tint'], pc['rtint'] = by_b[pc['bid']]
        pc['u0'] = float(rnd(abs(pc['bid']) + 7).integers(0, 4) * 3.6)
    # shared edges: the neighbour's eave level, so party walls are only drawn where they show
    gfn = lambda x, z: terrain.heights(np.asarray(x, float), np.asarray(z, float))
    cent = np.array([[pc['g'].centroid.x, pc['g'].centroid.y] for pc in pcs])
    refs = gfn(cent[:, 0], cent[:, 1])
    edges = {}
    for k, pc in enumerate(pcs):
        top = refs[k] + pc['h']
        g = pc['g'].simplify(.5 if math.hypot(cent[k, 0], cent[k, 1]) > 1200 else .15, preserve_topology=True)
        if g.geom_type != 'Polygon': continue
        for ring in [g.exterior] + list(g.interiors):
            c = list(ring.coords)
            for a, b in zip(c[:-1], c[1:]):
                kk = (round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2))
                edges[kk] = max(edges.get(kk, -1e9), top)
    chunks = defaultdict(list)
    for k, pc in enumerate(pcs):
        ci = (int(math.floor(cent[k, 0] / CHUNK)), int(math.floor(cent[k, 1] / CHUNK)))
        g = pc['g'].simplify(.5 if math.hypot(cent[k, 0], cent[k, 1]) > 1200 else .15, preserve_topology=True)
        shared = {}
        if g.geom_type == 'Polygon':
            for ring in [g.exterior] + list(g.interiors):
                c = list(ring.coords)
                for a, b in zip(c[:-1], c[1:]):
                    kk = (round(b[0], 2), round(b[1], 2), round(a[0], 2), round(a[1], 2))
                    if kk in edges: shared[kk] = edges[kk]
        chunks[ci].append((pc, shared))
    print('chunks', len(chunks), flush=True)
    header = {'chunks': [], 'styles': 10, 'source': 'OpenStreetMap contributors (ODbL), IGN MDT05 (CC BY 4.0)'}
    blobs = []; offset = 0; total = 0
    with Pool(min(16, os.cpu_count() or 4)) as pool:
        for ci, mw, mr, mf, tris in pool.imap_unordered(work, sorted(chunks.items()), chunksize=1):
            total += tris
            origin = ((ci[0] + .5) * CHUNK, (ci[1] + .5) * CHUNK)
            entry = {'o': origin}
            for name, m in (('w', mw), ('r', mr), ('f', mf)):
                pk = pack(m, origin)
                if pk is None: continue
                q, uv, c, idx = pk
                ent = {'n': len(q), 'ni': len(idx), 'i32': idx.dtype.itemsize == 4, 'off': offset}
                for arr in (q, uv, c, idx):
                    b = arr.tobytes(); pad = (-len(b)) % 4
                    blobs.append(b + b'\0' * pad); offset += len(b) + pad
                entry[name] = ent
            header['chunks'].append(entry)
    hb = json.dumps(header).encode(); hb += b' ' * ((-len(hb)) % 4)
    raw = struct.pack('<I', len(hb)) + hb + b''.join(blobs)
    open(f'{PUBLIC}/data/city.bin', 'wb').write(gzip.compress(raw, 6))
    print('triangles', total, 'raw', len(raw), 'gz', os.path.getsize(f'{PUBLIC}/data/city.bin'))

if __name__ == '__main__':
    main()
