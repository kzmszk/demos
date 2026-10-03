"""Exterior zone: terrain + OSM city (minus hero buildings) + Piazza San Pietro + basilica + statues.
blender -b --python build_exterior.py -- <out_base> [--render] [--samples N]"""
import sys, math, random, json
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
import numpy as np
import bpy
from vb.geom import *
from vb import bl, bake, site, terrain, statues, veg
import build_city as BC
import build_square as BS
import build_basilica_ext as BE
import build_sistine as SX
import build_basilica_int as BI
import build_museums as MU

SUN = dict(sun_az_deg=120, sun_el_deg=30)

def pip(pt, poly):
    x, y = pt; inside = False
    for i in range(len(poly)):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): inside = not inside
    return inside

SIX_FP = [tuple(p[:2]) for p in apply(SX.world_matrix(), np.array([[-SX.HL - 3.2, -SX.HW - 4.0, 0], [SX.HL + 3.2, -SX.HW - 4.0, 0], [SX.HL + 3.2, SX.HW + 4.0, 0], [-SX.HL - 3.2, SX.HW + 4.0, 0]]))]

def hero_mask():
    """returns a function (x, y) -> True if a hero model replaces OSM geometry there."""
    out_loc = BE.outline()
    out_w = [site.B2W(u, v)[:2] for (u, v) in out_loc]
    fac = [site.B2W(u, v)[:2] for (u, v) in ((116.0, -BE.FAC_HALF - 1), (BE.U_FAC + 3, -BE.FAC_HALF - 1), (BE.U_FAC + 3, BE.FAC_HALF + 1), (116.0, BE.FAC_HALF + 1))]
    br = [p for p in BS.SQ['braccio']]
    def f(x, y):
        if pip((x, y), out_w) or pip((x, y), fac): return True
        for b in br:
            if pip((x, y), b): return True
        for sgn in (1, -1):
            r = math.hypot(x, y - sgn * BS.CY); a = math.atan2(sgn * (y - sgn * BS.CY), x)
            if BS.RADII[0] - 6 < r < BS.RADII[3] + 6 and BS.A0 - 0.12 < a < BS.A1 + 0.12: return True
        if math.hypot(x, y) < 9: return True
        if pip((x, y), SIX_FP): return True
        if -256 < x < -188 and 350 < y < 462: return True       # Cortile della Pigna (hero model)
        return False
    return f

def city_mesh():
    mask = hero_mask()
    ids = set()
    for wid, w in BC.o.ways.items():
        t = w.get('tags', {})
        if not ('building' in t or 'building:part' in t): continue
        P = BC.o.way_xy(wid)
        if not P: continue
        cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
        if mask(cx, cy): ids.add(wid)
    for rid, r in BC.o.rels.items():
        t = r.get('tags', {})
        if not ('building' in t or 'building:part' in t): continue
        rings = BC.o.rel_rings(rid)['outer']
        if not rings or not rings[0]: continue
        P = rings[0]; cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
        if mask(cx, cy): ids.add(rid)
    BC.HERO_WAYS.update(ids)
    print('hero-replaced OSM ids', len(ids), flush=True)
    return BC.build()

GREEN, WOODY, WATER = veg.polygons(BC.o)
GI, WI, AI = veg.PolyIndex(GREEN), veg.PolyIndex(WOODY), veg.PolyIndex(WATER)
VA = veg.PolyIndex([r[:-1] if r[0] == r[-1] else r for r in BC.o.rel_rings(36989)['outer']], cell=60.0)
BLD = veg.PolyIndex([BC.o.way_xy(w)[:-1] for w, ww in BC.o.ways.items() if 'building' in ww.get('tags', {}) and len(ww['nodes']) > 3 and ww['nodes'][0] == ww['nodes'][-1]], cell=40.0)
def garden(x, y):
    """the Vatican Gardens: inside the state's boundary, west and north-west of the basilica"""
    return (x < -335 or (x < -250 and y > 250)) and VA.inside(x, y)

ROADW = {'motorway': 14, 'trunk': 12, 'primary': 12, 'secondary': 10, 'tertiary': 8, 'residential': 6.5, 'unclassified': 6, 'living_street': 4.5,
         'service': 4, 'pedestrian': 6, 'footway': 2.2, 'path': 1.8, 'cycleway': 2.2, 'steps': 2.5}
def roads_mesh(mask):
    m = Mesh(); n = 0
    for wid, w in BC.o.ways.items():
        t = w.get('tags', {}); hw = t.get('highway')
        if hw not in ROADW or t.get('tunnel') in ('yes', 'building_passage') or t.get('indoor') == 'yes' or t.get('layer', '0').startswith('-'): continue
        P = BC.o.way_xy(wid)
        if len(P) < 2: continue
        wd = ROADW[hw]
        for i in range(len(P) - 1):
            a, b = np.array(P[i]), np.array(P[i + 1]); L = np.linalg.norm(b - a)
            if L < 0.2: continue
            mid = (a + b) / 2
            if mask(mid[0], mid[1]) or AI.inside(mid[0], mid[1]): continue
            gard = garden(mid[0], mid[1])
            mat = 'gravel' if (gard and hw in ('footway', 'path', 'service', 'living_street', 'steps', 'pedestrian')) else 'sampietrini' if hw in ('pedestrian', 'footway', 'steps', 'living_street') else 'asphalt'
            d = (b - a) / L; nrm = np.array([-d[1], d[0]]) * wd / 2
            ns = max(1, int(L / 4.0))
            for k in range(ns):
                p0 = a + (b - a) * k / ns - d * (wd * 0.25 if k == 0 else 0); p1 = a + (b - a) * (k + 1) / ns + d * (wd * 0.25 if k == ns - 1 else 0)
                q = [p0 + nrm, p0 - nrm, p1 - nrm, p1 + nrm]
                pts = [(p[0], p[1], terrain.height(p[0], p[1]) + 0.14) for p in q]
                o = m.add_v(pts); m.face([o + 3, o + 2, o + 1, o], mat)
            n += 1
    print('road segments', n, flush=True)
    return m
WATER_Z = -11.0

def ground_z(x, y):
    return WATER_Z - 1.5 if AI.inside(x, y) else terrain.height(x, y)

def terrain_mesh():
    m = Mesh(); step = 8.0
    x0, y0, x1, y1 = -1300, -1000, 1300, 1000
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    o = m.add_v([(x0 + i * step, y0 + j * step, ground_z(x0 + i * step, y0 + j * step)) for j in range(ny + 1) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            xa, ya = x0 + i * step, y0 + j * step
            if -188 <= xa and xa + step <= 113 and -123 <= ya and ya + step <= 123: continue   # square paving replaces it
            a = o + j * (nx + 1) + i
            cx, cy = xa + step / 2, ya + step / 2
            mat = 'lawn' if (GI.inside(cx, cy) or garden(cx, cy)) else 'ground'
            m.face([a, a + 1, a + nx + 2, a + nx + 1], mat, True)
    # river surface
    for P in WATER:
        if len(P) >= 3: m.merge(cap([P], WATER_Z, 'water', True))
    return m

def apron_mesh():
    m = Mesh()
    # outer apron to the horizon: rings from the terrain rectangle out to 14 km, fading to flat
    rings = [1.0, 1.25, 1.6, 2.2, 3.2, 5.0, 8.0, 14.0, 30.0, 60.0]
    ns = 96
    def edge_pt(a, k):
        # point on a rounded rectangle scaled by k (k=1 sits inside the terrain grid edge)
        cx, cy = math.cos(a), math.sin(a)
        t = min(1290 / max(1e-6, abs(cx)), 990 / max(1e-6, abs(cy)))
        x, y = cx * t * k, cy * t * k
        z = terrain.height(max(-1295, min(1295, x)), max(-995, min(995, y))) if k <= 1.0 else -6.0 + (terrain.height(max(-1295, min(1295, x / k)), max(-995, min(995, y / k))) + 6.0) / (k * k)
        return (x, y, z)
    for r in range(len(rings) - 1):
        A = [edge_pt(2 * math.pi * i / ns, rings[r]) for i in range(ns)]
        B = [edge_pt(2 * math.pi * i / ns, rings[r + 1]) for i in range(ns)]
        oa = m.add_v(A); ob = m.add_v(B)
        for i in range(ns):
            j = (i + 1) % ns
            m.face([oa + i, ob + i, ob + j, oa + j], 'ground', True)
    return m

def statue_mesh(st, spots):
    rnd = random.Random(7)
    m = Mesh()
    for (x, y, z, a) in st:
        key = rnd.choice(statues.SAINTS)
        m.merge(statues.place(key, x, y, z, 3.1, a - math.pi / 2 + rnd.uniform(-0.25, 0.25), lod=2))
    for i, (x, y, z, a) in enumerate(spots):
        m.merge(statues.place(['francis', 'ecclesia'][i], x, y, z, 5.4, a + math.pi / 2, lod=1))
    # facade: 13 statues on the balustrade (Christ centre, John the Baptist, 11 apostles)
    keys = ['christ', 'baptist'] + [statues.SAINTS[(i * 5 + 2) % len(statues.SAINTS)] for i in range(11)]
    xs = BE.facade_statue_spots()
    order = [0.0, 5.5, -5.5, 12.0, -12.0, 17.0, -17.0, 27.5, -27.5, 35.0, -35.0, 39.5, -39.5]
    for k, xf in zip(keys, order):
        u, v = BE.U_FAC - 0.4, xf
        x, y, z = site.B2W(u, v, site.FLOOR + BE.ATTIC_Z1 + 1.6)
        m.merge(statues.place(k, x, y, z, 5.7, site.AXIS_ANG + math.pi / 2, lod=1))
    return m

if __name__ == '__main__':
    out = sys.argv[sys.argv.index('--') + 1]
    samples = int(sys.argv[sys.argv.index('--samples') + 1]) if '--samples' in sys.argv else 256
    bl.clear_scene()
    parts = {}
    parts['terrain'] = terrain_mesh()
    parts['apron'] = apron_mesh()
    parts['roads'] = roads_mesh(hero_mask())
    parts['city'] = city_mesh()
    mask = hero_mask()
    tm, nt = veg.trees(BC.o, terrain.height, lambda x, y: mask(x, y) or AI.inside(x, y) or BLD.inside(x, y), WI,
                       extra=lambda rnd: [(x, y) for x, y in ((rnd.uniform(-1000, -250), rnd.uniform(-350, 650)) for _ in range(9000)) if garden(x, y) and not BLD.inside(x, y)])
    print('trees', nt, tm.count(), flush=True)
    parts['trees'] = tm
    sq, st, spots = BS.build()
    parts['square'] = sq
    parts['statues'] = statue_mesh(st, spots)
    parts['basilica'] = BE.build()
    parts['sistine_int'], parts['sistine_shell'] = SX.build_parts()
    parts['bas_int'] = BI.build()
    parts['pigna'] = MU.pigna_court((-222.0, 452.0), 0.0)
    MROOMS = MU.rooms()
    mus = Mesh()
    for r_ in MROOMS: mus.merge(r_.world()['mesh'])
    parts['museums'] = mus
    obs = {}
    for k, m in parts.items():
        print(k, m.count(), flush=True)
        obs[k] = bl.to_object(m, k)
    bl.setup_world(**SUN)
    sun = bpy.data.objects['Sun']
    if '--render' in sys.argv:
        for k, (p, t, lens) in {'a': ((260, -330, 160), (-250, 0, 40), 30), 'b': ((-20, -55, 4), (-190, -6, 30), 24)}.items():
            bl.camera(p, t, lens); bl.render(out + f'-{k}.jpg', 1400, 800, 64)
        sys.exit(0)
    dens = {'roads': 99.0, 'terrain': 16.0, 'city': 7.0, 'square': 3.0, 'statues': 99.0, 'basilica': 2.0, 'apron': 1e9, 'trees': 99.0,
            'sistine_shell': 2.0, 'sistine_int': 0.55, 'bas_int': 1.2, 'pigna': 2.0, 'museums': 0.8}
    only = [a.split('=')[1] for a in sys.argv if a.startswith('only=')]
    want = lambda k: not only or k in only[0]
    if want('basilica'): bake.orient_faces(obs['bas_int'], BI.viewpoints())
    if want('museums'): bake.orient_faces(obs['museums'], [p for r_ in MROOMS for p in r_.world()['vp']])
    if want('sistine'): bake.orient_faces(obs['sistine_int'], SX.viewpoints())
    for k, ob in obs.items():
        bake.densify_soup(ob, dens[k])
    only = [a.split('=')[1] for a in sys.argv if a.startswith('only=')]
    if not only or 'ext' in only[0]:
        bake.bake_irradiance([o for k, o in obs.items() if k not in ('sistine_int', 'bas_int', 'museums')], sun, samples=samples,
                             hide=[obs['museums'], obs['sistine_int'], obs['bas_int']])
        bake.export_npz([obs['square'], obs['statues'], obs['basilica'], obs['sistine_shell'], obs['pigna']], out + '_core')
        bake.export_npz([obs['city'], obs['terrain'], obs['apron'], obs['trees'], obs['roads']], out + '_city')
    if not only or 'sistine' in only[0]:
        lights = []
        for L_ in SX.led_lights():
            ld = bpy.data.lights.new('led', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = L_['size']; ld.energy = L_['energy']
            ld.color = (1.0, 0.92, 0.82)
            lo = bpy.data.objects.new('led', ld); bpy.context.scene.collection.objects.link(lo)
            lo.location = L_['loc']; lo.rotation_euler = L_['rot']; lights.append(lo)
        bake.bake_irradiance([obs['sistine_int']], sun, samples=max(samples, 768), hide=[o for k, o in obs.items() if k not in ('sistine_int', 'sistine_shell')])
        bake.export_npz([obs['sistine_int']], out + '_sistine')
    if not only or 'basilica' in only[0]:
        lights = []
        M = site.basilica_matrix()
        def add_area(p_local, size, energy, rot=(0, 0, 0), color=(1.0, 0.95, 0.88)):
            ld = bpy.data.lights.new('bl', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size; ld.energy = energy; ld.color = color
            lo = bpy.data.objects.new('bl', ld); bpy.context.scene.collection.objects.link(lo)
            lo.location = tuple(apply(M, np.array([p_local]))[0]); lo.rotation_euler = (rot[0], rot[1], rot[2] + site.AXIS_ANG); lights.append(lo)
        # light from the nave/arm lunette windows: soft panels under the vault crowns, facing down
        add_area((68, 0, 40.0), (90, 18), 1.0e5)
        add_area((-38, 0, 40.0), (30, 18), 4.5e4)
        add_area((0, 38, 40.0), (18, 30), 4.5e4); add_area((0, -38, 40.0), (18, 30), 4.5e4)
        # aisles (lanterns of the oval domes), lantern of the main dome
        for cu in (32.6, 56.3, 80.0, 103.6):
            for sv in (-1, 1): add_area((cu, sv * 24.0, 26.0), (8, 5), 8e3)
        add_area((0, 0, 112.0), (10, 10), 1.5e5, color=(1.0, 0.97, 0.9))
        bake.bake_irradiance([obs['bas_int']], sun, samples=max(samples, 512))
        bake.export_npz([obs['bas_int']], out + '_basilica')
        for lo in lights: bpy.data.objects.remove(lo, do_unlink=True)
    if not only or 'museums' in only[0]:
        lights = []
        for r_ in MROOMS:
            for L_ in r_.world()['lights']:
                ld = bpy.data.lights.new('ml', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = L_['size']; ld.energy = L_['energy']; ld.color = L_['color']
                lo = bpy.data.objects.new('ml', ld); bpy.context.scene.collection.objects.link(lo)
                lo.location = L_['loc']; lo.rotation_euler = L_['rot']; lights.append(lo)
        bake.bake_irradiance([obs['museums']], sun, samples=max(samples, 512), hide=[o for k, o in obs.items() if k != 'museums'])
        bake.export_rooms(obs['museums'], [(r_.name, r_.origin, r_.rot, r_.box) for r_ in MROOMS], out + '_room_')
        for lo in lights: bpy.data.objects.remove(lo, do_unlink=True)
        meta = [dict(name=r_.name, origin=r_.origin, rot=r_.rot, box=r_.box, exposure=r_.exposure,
                     info=[dict(key=i['key'], pos=list(apply(r_.M, np.array([i['pos']]))[0])) for i in r_.info]) for r_ in MROOMS]
        json.dump(meta, open('/home/kazu/work/demos/vatican/tools/ref/rooms.json', 'w'), indent=1, default=float)
    sys.exit(0)
    bake.export_npz([obs['square'], obs['statues'], obs['basilica']], out + '_core')
    bake.export_npz([obs['city'], obs['terrain'], obs['apron'], obs['trees']], out + '_city')
