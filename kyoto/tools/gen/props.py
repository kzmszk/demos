"""Street furniture for a tile (venv python, uses the jk kit's numpy shapes): road markings (crosswalks from OSM
footway=crossing, centre and lane lines), utility poles with their tangle of wires, street lamps, vending machines,
traffic signals, walls / fences / hedges / retaining walls / guard rails (OSM barriers), torii (OSM ceremonial gates),
wayside shrines (祠), post boxes, benches.  Not baked: pack.py lights them from the nearest baked vertices."""
import math, sys, os
import numpy as np
import shapely
from shapely.geometry import Point, LineString
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'blender'))
import jk
from jk import prim, arch
from .world import h32
from .osm import ROAD_RANK
from .ground import CAR

def rnd(*a): return h32(*a) / 2 ** 32

class Props:
    def __init__(self, w, tg, blocked, no_poles=None, hero_zone=None):
        self.hero_zone = hero_zone
        self.w = w; self.tg = tg; self.T = tg.T; self.R = tg.R
        self.B = jk.Builder('props')
        self.blocked = blocked                         # buildings + water (shapely, prepared)
        self.no_poles = no_poles                       # zones without overhead lines (Gion, hero precincts)

    def z(self, x, y): return float(self.T(x, y))

    # ------------------------------------------------------------------ markings
    def markings(self):
        B = self.B; R = self.R
        roads = {r['id']: r for r in self.tg.roads}
        car_lines = [r for r in self.tg.roads if r['hw'] in CAR and not r['bridge']]
        # crosswalks: footway=crossing ways across carriageways
        for r in self.tg.roads:
            if r['footway'] != 'crossing' and r['tags'].get('crossing') not in ('marked', 'zebra', 'traffic_signals', 'uncontrolled'): continue
            ln = r['line']
            if not ln.intersects(R) or ln.length < 3: continue
            cs = np.array(ln.coords)
            a, b = cs[0], cs[-1]; d = b - a; L = np.linalg.norm(d)
            if L < 2.5: continue
            d /= L; n = np.array([-d[1], d[0]])
            for t in np.arange(0.6, L - 0.3, 0.9):
                c = a + d * t
                if not R.contains(Point(c)): continue
                P = [c - d * 0.225 - n * 1.6, c + d * 0.225 - n * 1.6, c + d * 0.225 + n * 1.6, c - d * 0.225 + n * 1.6]
                Z = [self.z(*p) + 0.025 for p in P]
                B.add(np.c_[np.array(P), Z], [[0, 1, 2], [0, 2, 3]], 'paint', N=np.tile([0, 0, 1.0], (4, 1)))
        # centre / lane / edge lines on the carriageways
        for r in car_lines:
            lanes = r['lanes'] or (2 if r['width'] >= 6 else 1)
            if lanes < 2 or r['width'] < 5.5: continue
            ln = r['line']
            if not ln.intersects(R.buffer(5)): continue
            dashed = lanes == 2 and ROAD_RANK.get(r['hw'], 0) < 7
            offs = [(0.0, 'paint', dashed)]
            if lanes >= 4:
                offs = [(0.0, 'paint', False)] + [(s * r['width'] / 4, 'paint', True) for s in (-1, 1)]
            offs += [(s * (r['width'] / 2 - 0.3), 'paint', False) for s in (-1, 1)] if ROAD_RANK.get(r['hw'], 0) >= 5 else []
            for (off, mat, dash) in offs:
                try: sl = ln.offset_curve(off) if off else ln
                except Exception: continue
                if sl.is_empty or sl.geom_type != 'LineString': continue
                step = 5.0
                for t in np.arange(0, sl.length, step * (2 if dash else 1)):
                    p0 = sl.interpolate(t); p1 = sl.interpolate(min(sl.length, t + step))
                    if not R.contains(p0): continue
                    a = np.array(p0.coords[0]); b = np.array(p1.coords[0]); dd = b - a; LL = np.linalg.norm(dd)
                    if LL < 0.5: continue
                    nn = np.array([-dd[1], dd[0]]) / LL * 0.075
                    P = [a - nn, b - nn, b + nn, a + nn]
                    Z = [self.z(*p) + 0.02 for p in P]
                    B.add(np.c_[np.array(P), Z], [[0, 1, 2], [0, 2, 3]], 'paint', N=np.tile([0, 0, 1.0], (4, 1)))

    # ------------------------------------------------------------------ utility poles + wires
    def poles(self):
        B = self.B; R = self.R
        poles = []
        for r in self.tg.roads:
            if r['hw'] not in ('residential', 'unclassified', 'tertiary', 'service', 'living_street', 'secondary') or r['bridge'] or r['tunnel']: continue
            ln = r['line']
            if not ln.intersects(R.buffer(40)) or ln.length < 20: continue
            side = 1 if rnd(r['id'], 'side') < 0.5 else -1
            try: sl = ln.offset_curve(side * (r['width'] / 2 + 0.35))
            except Exception: continue
            if sl.is_empty or sl.geom_type != 'LineString': continue
            prev = None
            sp = 31.0 + rnd(r['id'], 'sp') * 6
            for t in np.arange(rnd(r['id'], 'o') * sp, sl.length, sp):
                p = sl.interpolate(t)
                if self.blocked.contains(p) or (self.no_poles is not None and self.no_poles.contains(p)): prev = None; continue
                q = (p.x, p.y, self.z(p.x, p.y), h32(r['id'], round(t)))
                if prev is not None and math.dist(prev[:2], q[:2]) < 45: poles.append((prev, q))
                else: poles.append((None, q))
                prev = q
        drawn = set()
        for (a, q) in poles:
            if R.contains(Point(q[0], q[1])) and q[3] not in drawn:
                drawn.add(q[3]); self.pole(q)
            if a is not None and (R.contains(Point(a[0], a[1])) or R.contains(Point(q[0], q[1]))):
                # wires belong to the tile holding the span's start
                if R.contains(Point(a[0], a[1])): self.wires(a, q)

    def pole(self, q):
        B = self.B; x, y, z, sd = q
        H = 11.5 + (sd % 7) * 0.2
        prim.cyl(B, (x, y, z - 0.3), (x, y, z + H), 0.19, 0.12, 8, 'wall_concrete', c0=(176, 174, 168, 30))
        for k, (zz, L) in enumerate(((H - 0.5, 1.6), (H - 1.4, 1.2))):
            prim.obox(B, (x - L / 2, y, z + zz), (x + L / 2, y, z + zz), 0.08, 0.08, 'metal_grey', tag='detail')
            for s in (-0.45, 0.0, 0.45):
                prim.cyl(B, (x + s * L / 1.6, y, z + zz + 0.04), (x + s * L / 1.6, y, z + zz + 0.2), 0.05, 0.035, 6, 'white_paint', tag='detail')
        if sd % 3 == 0:     # transformer
            prim.cyl(B, (x + 0.35, y + 0.2, z + H - 4.6), (x + 0.35, y + 0.2, z + H - 3.4), 0.3, 0.3, 8, 'metal_grey')
        if sd % 5 == 1:
            prim.box(B, x - 0.25, y + 0.15, z + H - 5.6, x + 0.25, y + 0.45, z + H - 4.9, 'metal_grey', tag='detail')
        # the yellow-black guard sleeve at the foot
        prim.cyl(B, (x, y, z), (x, y, z + 1.8), 0.205, 0.2, 8, 'paint', c0=(220, 190, 40, 0), tag='detail')
        # service drops toward the nearest buildings
        for k in range(1 + sd % 3):
            ang = (sd % 360) * math.pi / 180 + k * 2.1
            tx, ty = x + math.cos(ang) * 6.5, y + math.sin(ang) * 6.5
            if not self.blocked.contains(Point(tx, ty)): continue
            self.wire((x, y, z + H - 3.8 - k * 0.3), (tx, ty, self.z(tx, ty) + 5.2), sag=0.15)

    def wire(self, a, b, sag=0.35, r=0.012):
        a = np.asarray(a, float); b = np.asarray(b, float)
        n = 8
        pts = [a + (b - a) * t - np.array([0, 0, sag * 4 * t * (1 - t)]) for t in np.linspace(0, 1, n + 1)]
        prim.sweep(self.B, np.array(pts), [(-r, -r), (r, -r), (0.0, r)], 'wire', tag='detail')

    def wires(self, a, b):
        H1 = 11.5 + (a[3] % 7) * 0.2; H2 = 11.5 + (b[3] % 7) * 0.2
        d = np.array([b[0] - a[0], b[1] - a[1]]); L = np.linalg.norm(d)
        if L < 3: return
        n = np.array([-d[1], d[0]]) / L
        for (dz, off, sag) in ((-0.42, -0.5, 0.45), (-0.42, 0.0, 0.45), (-0.42, 0.5, 0.45), (-1.32, -0.4, 0.5), (-1.32, 0.4, 0.5), (-3.9, 0.15, 0.7), (-4.5, -0.15, 0.8)):
            p = (a[0] + n[0] * off, a[1] + n[1] * off, a[2] + H1 + dz); q = (b[0] + n[0] * off, b[1] + n[1] * off, b[2] + H2 + dz)
            self.wire(p, q, sag, 0.013 if dz > -2 else 0.02)

    # ------------------------------------------------------------------ point features
    def points(self):
        B = self.B; R = self.R
        for p in self.w.osm['points']:
            x, y = p['xy']
            if not R.contains(Point(x, y)): continue
            if self.hero_zone is not None and self.hero_zone.contains(Point(x, y)): continue
            t = p['tags']; z = self.z(x, y); sd = h32(p['id'])
            yaw = self.face_road(x, y)
            if t.get('highway') == 'street_lamp' or t.get('man_made') == 'lamp':
                prim.cyl(B, (x, y, z), (x, y, z + 5.5), 0.08, 0.06, 8, 'metal_grey')
                hx, hy = x + math.cos(yaw) * 0.9, y + math.sin(yaw) * 0.9
                prim.obox(B, (x, y, z + 5.4), (hx, hy, z + 5.6), 0.06, 0.06, 'metal_grey', tag='detail')
                prim.box(B, hx - 0.25, hy - 0.12, z + 5.42, hx + 0.25, hy + 0.12, z + 5.6, 'metal_grey')
                prim.box(B, hx - 0.2, hy - 0.09, z + 5.4, hx + 0.2, hy + 0.09, z + 5.43, 'lamp', faces='z')
            elif t.get('amenity') == 'vending_machine':
                with jk.Frame(B, x, y, z, yaw - math.pi / 2):
                    col = [(236, 236, 232), (190, 30, 30), (30, 70, 160), (236, 236, 232)][sd % 4]
                    prim.box(B, -0.5, -0.35, 0, 0.5, 0.35, 1.83, 'cloth', c0=(*col, 0))
                    prim.box(B, -0.42, 0.35, 0.95, 0.42, 0.37, 1.7, 'screen', faces='Y')
                    prim.box(B, -0.42, 0.35, 0.25, 0.42, 0.37, 0.9, 'glass', faces='Y')
            elif t.get('highway') == 'traffic_signals':
                self.signal(x, y, z, yaw, sd)
            elif t.get('man_made') == 'ceremonial_gate':
                stone = t.get('material') == 'stone' or sd % 4 == 0
                arch.torii(B, x, y, z, self.along_path(x, y), h=3.2 if not stone else 3.6, span=2.6, color='stone' if stone else 'vermilion',
                           top='stone' if stone else 'black_lacquer', base='stone' if stone else 'black_lacquer')
            elif t.get('historic') == 'wayside_shrine':
                with jk.Frame(B, x, y, z, yaw - math.pi / 2):
                    prim.box(B, -0.45, -0.4, 0, 0.45, 0.4, 0.55, 'stone')
                    prim.box(B, -0.38, -0.32, 0.55, 0.38, 0.32, 1.25, 'wood_dark')
                    prim.box(B, -0.3, 0.32, 0.65, 0.3, 0.34, 1.15, 'vermilion', faces='Y', tag='detail')
                    for s in (-1, 1):
                        P = np.array([(-0.55, s * 0.55, 1.2), (0.55, s * 0.55, 1.2), (0.55, 0, 1.55), (-0.55, 0, 1.55)])
                        I = [[0, 1, 2], [0, 2, 3]] if s < 0 else [[0, 2, 1], [0, 3, 2]]
                        B.add(P, I, 'kawara', UV=np.array([[0, 0], [1.1, 0], [1.1, 0.6], [0, 0.6]]))
            elif t.get('amenity') == 'post_box':
                prim.cyl(B, (x, y, z), (x, y, z + 1.25), 0.2, 0.2, 10, 'vermilion')
            elif t.get('amenity') == 'bench':
                with jk.Frame(B, x, y, z, yaw):
                    prim.box(B, -0.8, -0.2, 0.42, 0.8, 0.2, 0.46, 'wood_natural')
                    for s in (-0.7, 0.7): prim.box(B, s - 0.04, -0.18, 0, s + 0.04, 0.18, 0.42, 'metal_dark')

    def signal(self, x, y, z, yaw, sd):
        B = self.B
        prim.cyl(B, (x, y, z), (x, y, z + 5.8), 0.11, 0.09, 8, 'metal_grey')
        hx, hy = x + math.cos(yaw) * 2.5, y + math.sin(yaw) * 2.5
        prim.obox(B, (x, y, z + 5.5), (hx, hy, z + 5.5), 0.08, 0.08, 'metal_grey', tag='detail')
        with jk.Frame(B, hx, hy, z + 5.25, yaw):
            prim.box(B, -0.17, -0.62, -0.18, 0.17, 0.62, 0.18, 'metal_grey')
            on = sd % 2
            for k, m in enumerate(('sig_green' if on else 'metal_dark', 'metal_dark', 'sig_red' if not on else 'metal_dark')):
                prim.box(B, 0.17, -0.5 + k * 0.42 - 0.13, -0.13, 0.19, -0.5 + k * 0.42 + 0.13, 0.13, m, faces='X')

    def face_road(self, x, y):
        best = None
        for r in self.tg.roads:
            if r['hw'] in ('footway', 'path', 'steps'): continue
            d = r['line'].distance(Point(x, y))
            if best is None or d < best[0]: best = (d, r['line'])
        if best is None: return 0.0
        q = best[1].interpolate(best[1].project(Point(x, y)))
        return math.atan2(q.y - y, q.x - x)

    def along_path(self, x, y):
        best = None
        for r in self.tg.roads:
            d = r['line'].distance(Point(x, y))
            if best is None or d < best[0]: best = (d, r['line'])
        if best is None or best[0] > 8: return 0.0
        ln = best[1]; t = ln.project(Point(x, y))
        a = ln.interpolate(max(0, t - 1)); b = ln.interpolate(min(ln.length, t + 1))
        return math.atan2(b.y - a.y, b.x - a.x) + math.pi / 2

    # ------------------------------------------------------------------ barriers
    def barriers(self, in_temple):
        B = self.B; R = self.R
        for f in self.w.osm['barriers']:
            ln = f['line']
            if not ln.intersects(R): continue
            g = ln.intersection(R)
            if self.hero_zone is not None: g = g.difference(self.hero_zone)
            for part in (g.geoms if hasattr(g, 'geoms') else [g]):
                if part.geom_type != 'LineString' or part.length < 0.5: continue
                pts = [np.array(c) for c in part.coords]
                k = f['kind']; h = f['height']
                if k == 'wall':
                    if in_temple is not None and in_temple.intersects(part):
                        arch.tsuiji(B, pts, 0, h=h or 2.2, th=0.5, ground=self.z)
                    else:
                        self.wall(pts, h or 1.6)
                elif k == 'hedge': arch.hedge(B, pts, 0, h=h or 1.1, w=0.7, ground=self.z)
                elif k == 'fence': self.fence(pts, h or 1.2)
                elif k == 'retaining_wall': self.retaining(pts)
                elif k == 'guard_rail': self.fence(pts, 0.75, rail=True)

    def wall(self, pts, h, th=0.15):
        B = self.B
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
            if L < 0.1: continue
            n = np.array([-d[1], d[0]]) / L
            za, zb = self.z(*a), self.z(*b)
            for s in (-1, 1):
                P = np.array([np.r_[a + n * s * th / 2, za - 0.3], np.r_[b + n * s * th / 2, zb - 0.3], np.r_[b + n * s * th / 2, zb + h], np.r_[a + n * s * th / 2, za + h]])
                I = [[0, 1, 2], [0, 2, 3]] if s > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'wall_concrete', UV=np.array([[0, -0.3], [L, -0.3], [L, h], [0, h]]), c0=(196, 192, 184, 30))
            P = np.array([np.r_[a + n * th / 2, za + h], np.r_[b + n * th / 2, zb + h], np.r_[b - n * th / 2, zb + h], np.r_[a - n * th / 2, za + h]])
            B.add(P, [[0, 2, 1], [0, 3, 2]], 'curb')

    def fence(self, pts, h, rail=False):
        B = self.B
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]; L = np.linalg.norm(b - a)
            if L < 0.1: continue
            za, zb = self.z(*a), self.z(*b)
            for t in np.arange(0, L + 0.01, 2.0):
                p = a + (b - a) * t / L; zp = self.z(*p)
                prim.cyl(B, (p[0], p[1], zp - 0.1), (p[0], p[1], zp + h), 0.03, 0.03, 5, 'metal_dark' if not rail else 'metal_grey', tag='detail')
            for k in ((0.9,) if rail else (0.35, 0.95)):
                prim.obox(B, (a[0], a[1], za + h * k), (b[0], b[1], zb + h * k), 0.03 if not rail else 0.05, 0.03 if not rail else 0.3, 'metal_dark' if not rail else 'white_paint', tag='detail')

    def retaining(self, pts):
        B = self.B
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
            if L < 0.2: continue
            n = np.array([-d[1], d[0]]) / L
            k = max(1, int(L / 2.0))
            for j in range(k):
                p = a + d * j / k; q = a + d * (j + 1) / k
                zs = [self.z(*(p + n * 2.5)), self.z(*(p - n * 2.5)), self.z(*(q + n * 2.5)), self.z(*(q - n * 2.5))]
                top = max(zs) + 0.1; bot = min(zs) - 0.3
                if top - bot < 0.8: continue
                side = 1 if self.z(*(p + n * 2.5)) < self.z(*(p - n * 2.5)) else -1
                P = np.array([np.r_[p + n * side * 0.05, bot], np.r_[q + n * side * 0.05, bot], np.r_[q + n * side * 0.05, top], np.r_[p + n * side * 0.05, top]])
                I = [[0, 1, 2], [0, 2, 3]] if side > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'stone', UV=np.array([[0, bot], [L / k, bot], [L / k, top], [0, top]]))

def build(w, tg, buildings, water_geom, temple_zones, no_poles, hero_zone=None):
    blocked = shapely.unary_union([b.poly for b in buildings] + ([water_geom] if water_geom is not None else []))
    shapely.prepare(blocked)
    P = Props(w, tg, blocked, no_poles, hero_zone)
    P.markings()
    P.poles()
    P.points()
    P.barriers(temple_zones)
    return P.B
