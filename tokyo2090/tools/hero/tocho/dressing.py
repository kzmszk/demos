"""Set dressing: trees (GPU-instanced 'foliage_' meshes), vines / roots / ivy on the buildings, abandoned vehicles,
street furniture and the civil servants' leftovers, placed from OSM where the real things are.
"""
import bpy, math, random, json
import numpy as np
from mathutils import Vector, Matrix, Euler
import common as C
import uvmap as U
import materials as M
import foliage as F

OSM = json.load(open(C.SRC + 'osm.json'))
X0, Y0, X1, Y1 = C.BOX


def inbox(x, y, m=0.0):
    return X0 + m < x < X1 - m and Y0 + m < y < Y1 - m


# ------------------------------------------------------------------------------------------------ footprints
class Blocked:
    """2D occupancy (0.5 m) of building footprints at ground level, the pool, the rubble pile, placed things"""

    def __init__(self, mass):
        self.s = 0.5
        self.nx = int((X1 - X0 + 40) / self.s); self.ny = int((Y1 - Y0 + 40) / self.s)
        self.g = np.zeros((self.ny, self.nx), bool)
        for name, b in mass.items():
            if not b['bands']: continue
            if name.endswith('br') or name == 'b015': continue
            for pr in b['bands'][0]['polys']:
                self.fill(pr['outer'], 1.0)

    def ij(self, x, y):
        return int((y - Y0 + 20) / self.s), int((x - X0 + 20) / self.s)

    def fill(self, ring, grow=0.0):
        xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
        for y in np.arange(min(ys) - grow, max(ys) + grow, self.s):
            for x in np.arange(min(xs) - grow, max(xs) + grow, self.s):
                if pin(ring, x, y) or (grow and any(pin(ring, x + dx, y + dy) for dx, dy in ((grow, 0), (-grow, 0), (0, grow), (0, -grow)))):
                    j, i = self.ij(x, y)
                    if 0 <= j < self.ny and 0 <= i < self.nx: self.g[j, i] = True

    def disc(self, x, y, r):
        for yy in np.arange(y - r, y + r + 0.01, self.s):
            for xx in np.arange(x - r, x + r + 0.01, self.s):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                    j, i = self.ij(xx, yy)
                    if 0 <= j < self.ny and 0 <= i < self.nx: self.g[j, i] = True

    def free(self, x, y, r=0.0):
        for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
            j, i = self.ij(x + dx, y + dy)
            if not (0 <= j < self.ny and 0 <= i < self.nx) or self.g[j, i]: return False
        return True


def pin(r, x, y):
    c = False; n = len(r)
    for i in range(n):
        x1, y1 = r[i]; x2, y2 = r[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1: c = not c
    return c


# ------------------------------------------------------------------------------------------------ trees
class Planter:
    def __init__(self, col, lib):
        self.col = col; self.lib = lib; self.sets = {}; self.n = {}; self.tris = 0

    def put(self, name, x, y, z, rot=None, scale=1.0, R=None, lod='both'):
        rot = rot if rot is not None else (R.uniform(0, 6.28) if R else 0)
        if lod == 'both' and name + '_lo' in self.lib:
            self.put(name + '_lo', x, y, z, rot, scale, None, 'mid')
            lod = 'near'
        src = self.lib[name]
        par = self.sets.get(name)
        if par is None:
            par = bpy.data.objects.new(name + '_set', None); self.col.objects.link(par)
            par['inst'] = True; par['lod'] = lod; self.sets[name] = par
        o = bpy.data.objects.new('%s.%03d' % (name, self.n.get(name, 0)), src.data)
        self.col.objects.link(o)
        o.parent = par
        o.location = (x, y, z)
        o.rotation_euler = (0, 0, rot)
        o.scale = (scale, scale, scale)
        o['inst'] = True; o['lod'] = lod
        self.n[name] = self.n.get(name, 0) + 1
        return o


def trees(col, lib, mass, blocked, rubble, pool, R):
    P = Planter(col, lib)
    occ = []
    import hero_meta
    SP = [(s['x'], s['y']) for s in hero_meta.SPAWNS]
    def ok(x, y, r):
        if not inbox(x, y, 1.0): return False
        if any((x - sx) ** 2 + (y - sy) ** 2 < 49 for sx, sy in SP): return False
        if not blocked.free(x, y, 0.6): return False
        for ox, oy, orr in occ:
            if (x - ox) ** 2 + (y - oy) ** 2 < (r * 0.6 + orr * 0.6) ** 2: return False
        return True
    def plant(name, x, y, r, scale=1.0, z=None, lod='both', check=True):
        if check and not ok(x, y, r): return False
        zz = (C.ground_min(x, y, 0.8) - 0.15) if z is None else z
        P.put(name, x, y, zz, R=R, scale=scale, lod=lod)
        occ.append((x, y, r * scale))
        return True
    # street trees from OSM and along the roads
    for t in OSM['trees']:
        x, y = t
        plant(R.choice(['foliage_zelkova0', 'foliage_zelkova1', 'foliage_street0']), x, y, 6, R.uniform(0.85, 1.15))
    for r in OSM['roads']:
        if r['hw'] not in ('secondary', 'tertiary') or r['bridge'] or r['tunnel']: continue
        line = [Vector(p) for p in r['line']]
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]; L = (b - a).length
            if L < 1: continue
            d = (b - a) / L; n = Vector((-d.y, d.x))
            for side in (-1, 1):
                t = R.uniform(0, 9)
                while t < L:
                    p = a + d * t + n * side * (r['width'] / 2 + 3.2 + R.uniform(-0.4, 0.6))
                    if R.random() < 0.45:
                        plant(R.choice(['foliage_zelkova0', 'foliage_zelkova1', 'foliage_street0', 'foliage_street1']), p.x, p.y, 6, R.uniform(0.8, 1.15))
                    t += R.uniform(11, 16)
    # the plaza: a clearing gone wild -- young trees, a big fig against the colonnade, shrubs
    from buildings import PLAZA_C, PLAZA_R
    import plaza
    spawn = Vector((72.0, 78.0))
    for k in range(70):
        a = math.radians(R.uniform(-85, 85)); rr = math.sqrt(R.uniform(0.02, 1)) * (PLAZA_R - 3)
        x = PLAZA_C.x + math.cos(a) * rr; y = PLAZA_C.y + math.sin(a) * rr
        if x < (plaza.wall_x(y) or 0) + 2: continue
        if (Vector((x, y)) - spawn).length < 9: continue
        if pool and (x - pool[0]) ** 2 / 100 + (y - pool[1]) ** 2 / 225 < 1.3: continue
        nm = R.choice(['foliage_young0', 'foliage_young1', 'foliage_shrub0', 'foliage_shrub0', 'foliage_young0', 'foliage_roof0'])
        plant(nm, x, y, 2.5, R.uniform(0.7, 1.2))
    for a in (-40, 25, 62):
        x = PLAZA_C.x + math.cos(math.radians(a)) * (PLAZA_R - 6); y = PLAZA_C.y + math.sin(math.radians(a)) * (PLAZA_R - 6)
        plant('foliage_fig0', x, y, 6, R.uniform(0.9, 1.1), check=False)
    # rubble pile: pioneers
    import rubble
    for k in range(60):
        x = R.uniform(-108, -18); y = R.uniform(95, 158)
        h = rubble.pile_height(x, y)
        if h < 0.8: continue
        nm = R.choice(['foliage_young0', 'foliage_young1', 'foliage_roof1', 'foliage_shrub0', 'foliage_shrub0'])
        z = rubble.surface(x, y) - 0.3
        if not any((x - sx) ** 2 + (y - sy) ** 2 < 49 for sx, sy in SP):
            P.put(nm, x, y, z, R=R, scale=R.uniform(0.7, 1.15)); occ.append((x, y, 2.5))
    # open ground around the towers (the podium, the deck): scattered trees
    for k in range(130):
        x = R.uniform(X0 + 2, X1 - 2); y = R.uniform(Y0 + 2, Y1 - 2)
        if R.random() < 0.45:
            plant(R.choice(['foliage_street0', 'foliage_young1', 'foliage_zelkova1', 'foliage_shrub0', 'foliage_roof0']), x, y, 4.5, R.uniform(0.75, 1.1))
    # roofs and setbacks: scrubby trees, denser on the low roofs
    for name, b in mass.items():
        for band in b['bands']:
            z = band['z1']
            for pr in band.get('roof', []):
                ring = pr['outer']
                area = abs(sum(ring[i][0] * ring[(i + 1) % len(ring)][1] - ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))) / 2
                if area < 25: continue
                dens = 1 / 150 if z < 80 else (1 / 240 if z < 200 else 1 / 200)
                if name == 'b000':
                    import buildings
                    # skip what the crown break removed
                n = int(area * dens + R.random())
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                for k in range(n * 4):
                    if n <= 0: break
                    x = R.uniform(min(xs), max(xs)); y = R.uniform(min(ys), max(ys))
                    if not pin(ring, x, y) or any(pin(h, x, y) for h in pr['holes']): continue
                    if name == 'b000' and CROWN and CROWN.region(x, y, z) and z > CROWN.hb(x, y) - 1: continue
                    nm = R.choice(['foliage_roof0', 'foliage_roof1', 'foliage_shrub0', 'foliage_young0'] + (['foliage_street1'] if z < 80 else []))
                    P.put(nm, x, y, z - 0.1, R=R, scale=R.uniform(0.7, 1.2))
                    n -= 1
    # ground cover: ferns and grass clumps (near only)
    for k in range(550):
        x = R.uniform(X0, X1); y = R.uniform(Y0, Y1)
        if not blocked.free(x, y, 0.3): continue
        h = rubble.pile_height(x, y)
        z = (rubble.surface(x, y) if h > 0.3 else C.ground(x, y)) - 0.05
        P.put(R.choice(['foliage_fern', 'foliage_grass', 'foliage_grass']), x, y, z, R=R, scale=R.uniform(0.7, 1.4), lod='near')
    return P, occ


CROWN = None


# ------------------------------------------------------------------------------------------------ vines on the buildings
def vines(col, mass, R, crown):
    mb = C.MB()
    for name, b in mass.items():
        for bi, band in enumerate(b['bands']):
            z = band['z1']
            low = b['bands'][0]['z0']
            tall = z - low
            for pr in band['polys']:
                ring = pr['outer']; n = len(ring)
                for i in range(n):
                    a = Vector(ring[i] + [z]); bb = Vector(ring[(i + 1) % n] + [z])
                    L = (bb - a).length
                    if L < 2: continue
                    out = Vector(((bb - a).y, -(bb - a).x, 0)).normalized()
                    mid = (a + bb) / 2
                    if crown and name == 'b000' and crown.region(mid.x, mid.y, z) and z > crown.hb(mid.x, mid.y) - 1: continue
                    gz = C.ground(mid.x + out.x * 2, mid.y + out.y * 2)
                    # how far this edge's wall drops before the next band below sticks out: just hang to <= 30 m
                    if z < 80:
                        F.hang_vines(mb, a, bb, out, R, length=(3, min(20, z - gz - 0.5)), spacing=4.8, z_min=gz)
                    elif z < 200:
                        if R.random() < 0.4: F.hang_vines(mb, a, bb, out, R, length=(4, 18), spacing=4.5, z_min=gz)
                    else:
                        if R.random() < 0.3: F.hang_vines(mb, a, bb, out, R, length=(3, 12), spacing=6.0, z_min=gz)
                    # strangler-fig roots pouring down from planted roofs and setbacks
                    if L > 8 and R.random() < (0.16 if z < 80 else 0.1 if z < 200 else 0.04):
                        for k in range(1 + int(L / 25)):
                            p = a.lerp(bb, R.uniform(0.15, 0.85))
                            F.root_curtain(mb, p, out, R, n=R.randint(4, 8), length=(8, min(45, z - gz)), z_min=gz)
                    # ivy on the lowest band
                    if bi == 0 and z - gz > 4:
                        for k in range(int(L / 16) + 1):
                            if R.random() < 0.4:
                                t = R.uniform(0, 1)
                                p0 = a.lerp(bb, t); p0.z = gz - 0.3
                                F.ivy_patch(mb, p0 + out * 0.05, (bb - a).normalized(), out, R.uniform(3, 9), R.uniform(2, min(14, z - gz)), R)
    o = mb.build('vines', [M.make('leaf')], col)
    o['grp'] = 'vines'; o['lod'] = 'near'
    return o


# ------------------------------------------------------------------------------------------------ props
class Props:
    def __init__(self, lib, col, blocked):
        self.lib = lib; self.col = col; self.blocked = blocked
        self.objs = []; self.boxes = []

    def put(self, name, x, y, heading, z=None, tilt=(0, 0), lod='both', check=False, sink=0.0):
        """heading: radians, direction the model's +Y points (0 = north)"""
        if name not in self.lib: return None
        if check and not self.blocked.free(x, y, 1.0): return None
        src = self.lib[name]
        o = src.copy(); o.data = src.data   # linked; joined at export
        self.col.objects.link(o)
        if z is None:
            # follow the ground: pitch and roll from the terrain under the footprint
            dims = src.dimensions
            fx, fy = math.sin(heading), math.cos(heading)
            hl = dims.y / 2 * 0.8; hw = dims.x / 2 * 0.8
            zf = C.ground(x + fx * hl, y + fy * hl); zb = C.ground(x - fx * hl, y - fy * hl)
            zr = C.ground(x + fy * hw, y - fx * hw); zl = C.ground(x - fy * hw, y + fx * hw)
            z = (zf + zb + zr + zl) / 4 - sink
            pitch = math.atan2(zf - zb, 2 * hl) if hl > 0.2 else 0
            roll = math.atan2(zl - zr, 2 * hw) if hw > 0.2 else 0
            tilt = (pitch + tilt[0], roll + tilt[1])
        rz = -heading
        o.matrix_world = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(tilt[0], 4, 'X') @ Matrix.Rotation(tilt[1], 4, 'Y')
        o['lod'] = 'near'; o['grp'] = 'props'
        self.objs.append(o)
        self.blocked.disc(x, y, max(src.dimensions.x, src.dimensions.y) / 2 * 0.8)
        for bx in src.get('collide', []):
            self.boxes.append((o.matrix_world.copy(), list(bx)))
        return o


def road_vehicles(PR, R, rubble):
    cars = ['car_sedan', 'car_sedan_silver', 'car_sedan_blue', 'car_kei', 'car_minivan', 'taxi', 'truck_small', 'car_sedan', 'car_kei']
    n = 0
    for r in OSM['roads']:
        if r['hw'] not in ('secondary', 'tertiary', 'service', 'unclassified') or r['tunnel']: continue
        line = [Vector(p) for p in r['line']]
        nl = 2 if r['width'] >= 9 else 1
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]; L = (b - a).length
            if L < 3: continue
            d = (b - a) / L; nrm = Vector((d.y, -d.x))
            t = R.uniform(2, 20)
            while t < L - 2:
                lane = R.randrange(nl)
                off = (lane + 0.5 - nl / 2) * 3.3 if nl > 1 else 0
                p = a + d * t + nrm * (off + R.uniform(-0.3, 0.3))
                if inbox(p.x, p.y, 3) and rubble.pile_height(p.x, p.y) < 0.2:
                    hd = math.atan2(d.x, d.y) + (math.pi if (lane == 0 and nl > 1) else 0) + R.uniform(-0.12, 0.12)
                    if R.random() < 0.06: hd += R.uniform(0.5, 1.4)     # slewed across the lane
                    nm = R.choice(cars)
                    if n < 38 and PR.put(nm, p.x, p.y, hd, check=True, sink=0.05): n += 1
                t += R.uniform(40, 90) if R.random() < 0.75 else R.uniform(5.5, 7)     # gaps and short jams
    return n


def street_furniture(PR, R, rubble):
    pts = OSM['points']
    for p in pts:
        x, y = p['xy']; tg = p['tags']
        if not inbox(x, y, 1): continue
        if tg.get('highway') == 'bus_stop':
            h = road_heading(x, y)
            PR.put('bus_shelter', x, y, h + math.pi / 2, check=False)
            PR.put('bus_pole', x + math.sin(h) * 4.0, y + math.cos(h) * 4.0, h + math.pi / 2)
            # the last bus, still at the stop
            nrm = Vector((math.cos(h), -math.sin(h)))
            PR.put('bus', x + nrm.x * -3.6 + math.sin(h) * 2, y + nrm.y * -3.6 + math.cos(h) * 2, h + R.uniform(-0.05, 0.05), check=False, sink=0.08)
        elif tg.get('highway') == 'traffic_signals' or tg.get('crossing') == 'traffic_signals':
            h = road_heading(x, y)
            if R.random() < 0.35:   # fallen across the road
                PR.put('traffic_signal', x + 2, y, h + R.uniform(-1, 1), z=C.ground(x + 2, y) + 0.25, tilt=(math.pi / 2 - 0.05, 0))
            else:
                PR.put('traffic_signal', x + math.cos(h) * 5, y - math.sin(h) * 5, h + math.pi / 2, tilt=(R.uniform(-0.08, 0.08), R.uniform(-0.1, 0.1)))
        elif tg.get('amenity') == 'telephone':
            PR.put('phone_booth', x, y, R.uniform(0, 6.28), check=True)
        elif tg.get('amenity') == 'taxi':
            h = road_heading(x, y)
            for k in range(3):
                PR.put('taxi', x + math.sin(h) * k * 5.6, y + math.cos(h) * k * 5.6, h, check=True, sink=0.05)
        elif tg.get('amenity') in ('bicycle_rental', 'bicycle_parking'):
            for k in range(7):
                hh = R.uniform(-0.2, 0.2)
                if R.random() < 0.4:
                    PR.put('bicycle', x + k * 0.7, y + R.uniform(-0.3, 0.3), 1.57 + hh, z=C.ground(x + k * 0.7, y) + 0.12, tilt=(0, 1.45))
                else:
                    PR.put('bicycle', x + k * 0.7, y, hh, tilt=(0, R.uniform(-0.15, 0.15)))
        elif tg.get('amenity') == 'post_box' or tg.get('amenity') == 'drinking_water':
            PR.put('bollard', x, y, 0)
    # vending machines by the entrances, street lamps along the roads, a blue direction sign at the big corners
    for (x, y, h) in [(-12, -46, 0.3), (-10.8, -46, 0.3), (70, 116, 2.9), (-22, 152, 3.0), (50, 12, 1.2)]:
        PR.put(R.choice(['vending_machine', 'vending_machine_b']), x, y, h, tilt=(0, R.uniform(-0.05, 0.05)), check=False)
    for r in OSM['roads']:
        if r['hw'] not in ('secondary',) or r['tunnel']: continue
        line = [Vector(p) for p in r['line']]
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]; L = (b - a).length
            d = (b - a) / max(L, 1e-6); nrm = Vector((d.y, -d.x))
            t = R.uniform(0, 30)
            while t < L:
                p = a + d * t + nrm * (r['width'] / 2 + 0.8)
                if inbox(p.x, p.y, 1):
                    if R.random() < 0.2:
                        PR.put('street_lamp', p.x, p.y, math.atan2(-nrm.x, -nrm.y) + math.pi / 2, z=C.ground(p.x, p.y) + 0.3, tilt=(math.pi / 2 - 0.1, 0))
                    else:
                        PR.put('street_lamp', p.x, p.y, math.atan2(-nrm.x, -nrm.y) - math.pi / 2, tilt=(R.uniform(-0.06, 0.06), R.uniform(-0.06, 0.06)))
                t += R.uniform(60, 80)
    for x, y in [(-104, 158), (-93, -33), (40, -6), (112, 100)]:
        if inbox(x, y, 1): PR.put('sign_blue', x, y, road_heading(x, y) + math.pi, tilt=(R.uniform(-0.1, 0.1), 0))
    PR.put('sign_tocho', 52, 50, -1.4); PR.put('sign_tocho', -95, 64, 1.6)
    PR.put('sign_fallen_panel', 63, 96, 0.7, z=C.ground(63, 96) + 0.05)


def leftovers(PR, R):
    """a civil servant's office dragged out under the colonnade, and things dropped across the plaza"""
    base = Vector((84.0, 64.0))
    PR.put('office_desk', base.x, base.y, 2.0); PR.put('office_chair', base.x - 1.1, base.y + 0.6, 1.2, tilt=(0, 0.1))
    PR.put('pc_monitor', base.x + 0.1, base.y, 2.0, z=C.ground(base.x, base.y) + 0.71)
    PR.put('binders', base.x - 0.3, base.y - 0.2, 2.3, z=C.ground(base.x, base.y) + 0.71)
    PR.put('filing_cabinet', base.x + 1.3, base.y - 0.9, 2.1, tilt=(0, 0.05))
    PR.put('doc_boxes', base.x + 0.6, base.y + 1.4, 1.0)
    PR.put('filing_cabinet', base.x + 2.4, base.y + 0.8, 0.2, z=C.ground(base.x + 2.4, base.y + 0.8) + 0.25, tilt=(0, 1.57))
    for nm, x, y in [('briefcase', 62, 70), ('umbrella', 66, 88), ('office_chair', 55, 60), ('doc_boxes', 46, 104),
                     ('binders', 58, 66), ('umbrella', -60, 150), ('briefcase', -20, -30)]:
        PR.put(nm, x, y, R.uniform(0, 6.28), tilt=(0, 1.5) if nm == 'briefcase' else (0, 0))
    for (x, y, h) in [(50, 40, 0.9), (52, 108, 2.4), (75, 90, 1.6), (-30, 150, 3.1), (16, -40, 0.0)]:
        PR.put('bench', x, y, h)
    for (x, y) in [(55, 44), (-18, 150), (22, -50)]:
        PR.put('trash_bin', x, y, R.uniform(0, 6.28))


def road_heading(x, y):
    best = None
    for r in OSM['roads']:
        if r['hw'] in ('footway', 'steps', 'path'): continue
        line = r['line']
        for i in range(len(line) - 1):
            a, b = Vector(line[i]), Vector(line[i + 1])
            d = b - a; L = d.length
            if L < 1e-3: continue
            t = max(0, min(1, (Vector((x, y)) - a).dot(d) / (L * L)))
            q = a + d * t
            dist = (Vector((x, y)) - q).length
            if best is None or dist < best[0]: best = (dist, math.atan2(d.x, d.y))
    return best[1] if best else 0.0
