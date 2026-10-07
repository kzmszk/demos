"""永観堂: the exclusion zone (generic buildings and trees dropped), ground paint, and the trees — maples above all
(秋はもみじの永観堂): along the approach, around the 放生池, in the moss gardens before the 方丈, on the slopes behind the
halls and along the 臥龍廊, below the 多宝塔; pines in the gardens, cedars and evergreen oaks on the hill."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box

# generic buildings inside the precinct that stay generic (modern / not modelled): 会館, 本坊, 宗務所, 寺務所, 智福院,
# the kindergarten, toilets, the shop by the 中門, the library ...
KEEP = [316011167, 316011135, 865671904, 865671905, 291548877, 290087145, 291548880, 291548903, 316003671, 316003673, 316003675, 316011107, 316011091, 316011123,
        316011125, 316020333, 317735760, 482601744, 482601746, 482601748, 859984621, 860261789, 860261790, 291548898,
        291548913, 316011130, 292177691, 291548887, 291548921, 292383221]

# gravel courts (no trees), world polygons
COURTS = [
    [(3286.0, 3199.5), (3300.0, 3197.0), (3305.5, 3192.5), (3306.5, 3180.0), (3303.0, 3160.0), (3297.0, 3150.0), (3289.5, 3150.0), (3288.0, 3170.0), (3286.0, 3186.0)],
    [(3318.0, 3087.0), (3333.0, 3085.4), (3337.6, 3118.8), (3320.5, 3123.0)],
    [(3307.0, 3080.5), (3320.0, 3079.0), (3321.0, 3066.5), (3310.0, 3062.0), (3305.0, 3070.0)],
    [(3345.0, 3046.0), (3352.0, 3045.0), (3377.0, 3047.0), (3379.0, 3076.0), (3366.0, 3075.0), (3352.0, 3074.0), (3346.0, 3067.0)],
    [(3324.4, 3141.0), (3330.8, 3140.0), (3331.8, 3158.4), (3325.6, 3158.6)],
]
SAND = [[(3324.4, 3141.0), (3330.8, 3140.0), (3331.8, 3158.4), (3325.6, 3158.6)], [(3316.0, 3147.6), (3321.6, 3147.2), (3322.0, 3152.4), (3316.4, 3152.8)]]

PATHS_STONE = [
    ([(3188.0, 3202.6), (3205.7, 3202.3), (3218.2, 3201.9), (3241.0, 3200.7), (3247.7, 3200.2), (3267.3, 3198.4), (3282.1, 3197.1), (3288.2, 3196.9)], 3.2),
    ([(3288.2, 3196.9), (3291.3, 3195.7), (3299.9, 3193.6), (3315.1, 3189.6)], 2.4),
    ([(3299.9, 3193.6), (3307.4, 3175.8), (3309.9, 3167.9), (3312.0, 3157.8), (3310.4, 3139.3), (3314.1, 3125.1), (3315.2, 3118.3), (3316.8, 3108.6),
      (3316.3, 3083.2), (3315.4, 3073.5)], 2.2),
    ([(3307.4, 3175.8), (3318.0, 3162.0), (3318.6, 3160.6)], 2.0),
    ([(3314.1, 3125.1), (3328.2, 3122.8), (3357.4, 3119.9), (3361.3, 3120.7)], 1.8),
    ([(3291.3, 3195.7), (3290.4, 3208.0), (3290.5, 3212.8)], 2.0),
    ([(3187.8, 3202.6), (3189.4, 3160.9), (3189.7, 3135.3), (3202.4, 3135.0)], 2.0),
    ([(3350.0, 3068.0), (3354.0, 3064.0)], 3.0),
]
PATHS_GRAVEL_IDS = [291548953, 291548954, 291548955, 291548957, 291548958, 407490693, 859971106, 859972770, 859985807, 859985809, 859985811,
                    881575199, 881575201, 870598450, 870598451, 870598452, 870598454, 870598456, 865671894, 1330125732, 1330125733, 1330125734,
                    859979629, 865671888, 865671902, 860072435, 881624496, 881624498, 881624499, 881624501, 859979630]

# hand-placed specimen trees: (species, x, y, scale, yaw)
SPECIMENS = [
    ('matsu', 3215.0, 3206.8, 1.55, 0.3), ('matsu', 3238.5, 3192.8, 1.4, 1.2), ('matsu', 3260.2, 3203.0, 1.35, 2.0),
    ('matsu', 3279.0, 3203.6, 1.45, 0.7), ('matsu', 3208.5, 3209.0, 1.3, 2.4), ('matsu', 3304.5, 3191.5, 1.6, 0.9),
    ('matsu', 3369.9, 3091.6, 1.25, 0.0),                          # 三鈷の松
    ('keyaki', 3347.7, 3073.3, 0.7, 0.5),                          # ボダイジュ by the 阿弥陀堂
    ('sakura', 3326.0, 3130.2, 0.55, 1.0),                         # 悲田梅
    ('ichou', 3262.6, 3147.6, 1.05, 0.2),                          # the ginkgo by the pond
    ('sugi', 3252.0, 3168.8, 0.85, 0.0), ('sugi', 3246.5, 3170.4, 0.9, 1.0), ('sugi', 3262.6, 3169.6, 0.8, 2.0), ('sugi', 3240.0, 3168.0, 0.75, 0.5),
    ('matsu', 3286.4, 3154.4, 1.05, 2.6), ('matsu', 3281.2, 3155.0, 0.8, 1.2), ('matsu', 3270.6, 3136.0, 1.1, 0.4),
    ('sakura', 3351.0, 3075.4, 0.95, 0.8), ('sakura', 3326.4, 3062.2, 0.85, 2.2),
    ('sugi', 3301.5, 3163.0, 0.5, 0.0), ('sugi', 3333.0, 3137.0, 0.75, 0.0), ('sugi', 3335.5, 3128.4, 0.8, 1.0),
    ('matsu', 3318.8, 3145.0, 0.85, 0.4), ('matsu', 3333.6, 3152.8, 0.7, 1.6),
    ('momiji', 3270.0, 3167.4, 1.25, 0.1), ('momiji', 3266.4, 3150.6, 1.3, 1.1), ('momiji', 3266.0, 3141.8, 1.2, 2.2),
    ('momiji', 3285.6, 3147.6, 0.9, 0.4), ('momiji', 3279.2, 3153.2, 0.85, 2.9),
]

MIX = {
    'approach': [('momiji', 0.78), ('kashi', 0.08), ('matsu', 0.08), ('sakura', 0.04), ('sugi', 0.02)],
    'pond':     [('momiji', 0.72), ('matsu', 0.11), ('kashi', 0.07), ('sugi', 0.02), ('sakura', 0.05), ('ichou', 0.03)],
    'garden':   [('momiji', 0.74), ('matsu', 0.17), ('kashi', 0.06), ('sugi', 0.03)],
    'slope':    [('momiji', 0.55), ('kashi', 0.2), ('sugi', 0.12), ('hinoki', 0.06), ('keyaki', 0.04), ('sakura', 0.03)],
    'forest':   [('kashi', 0.42), ('sugi', 0.22), ('hinoki', 0.14), ('momiji', 0.16), ('keyaki', 0.06)],
    'other':    [('momiji', 0.35), ('kashi', 0.3), ('matsu', 0.12), ('sakura', 0.1), ('sugi', 0.06), ('keyaki', 0.07)],
}
SCALE = {'momiji': (0.95, 1.45), 'matsu': (0.8, 1.25), 'kashi': (0.8, 1.15), 'sugi': (0.75, 1.05), 'hinoki': (0.75, 1.0), 'keyaki': (0.7, 1.0),
         'sakura': (0.8, 1.1), 'ichou': (0.8, 1.05), 'tsutsuji': (0.8, 1.3)}

def pick(mix, u):
    acc = 0.0
    for n, w in mix:
        acc += w
        if u < acc: return n
    return mix[-1][0]

def poisson(poly, spacing, rng, limit=3000):
    if poly.is_empty: return np.zeros((0, 2))
    x0, y0, x1, y1 = poly.bounds
    n = min(limit, int(poly.area / (spacing * spacing) * 1.2) + 1)
    cand = np.column_stack([rng.uniform(x0, x1, n * 8), rng.uniform(y0, y1, n * 8)])
    cand = cand[shapely.contains_xy(poly, cand[:, 0], cand[:, 1])]
    out = []; grid = {}
    for p in cand:
        k = (int(p[0] // spacing), int(p[1] // spacing)); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grid.get((k[0] + dx, k[1] + dy), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < spacing * spacing: ok = False; break
                if not ok: break
            if not ok: break
        if ok:
            out.append(p); grid.setdefault(k, []).append(p)
            if len(out) >= limit: break
    return np.array(out) if out else np.zeros((0, 2))

CROWN = {'momiji': (6.5, 0.62), 'ichou': (14.0, 0.28), 'sakura': (7.5, 0.7), 'keyaki': (16.0, 0.46), 'matsu': (7.5, 0.45), 'sugi': (23.0, 0.17),
         'hinoki': (18.0, 0.22), 'kashi': (11.0, 0.48), 'yanagi': (8.5, 0.5), 'tsutsuji': (1.1, 0.9), 'take': (11.0, 0.18)}

def blocks_view(shots, S, name, x, y, z, sc, near=14.0):
    """True if the tree's crown would fill the foreground (closer than `near`) of one of the reference viewpoints:
    those spots are kept open as in the photos"""
    H0, R0 = CROWN[name]
    H = H0 * sc; r = R0 * H * 0.85
    C = np.array([x, y, z + 0.6 * H])
    for (_, cam, tgt, lens) in shots:
        cam = np.asarray(cam, float); tgt = np.asarray(tgt, float)
        if cam[2] - float(S.ground(cam[0], cam[1])) > 25: continue
        d = tgt - cam; d /= np.linalg.norm(d)
        right = np.cross(d, [0, 0, 1.0]); right /= max(np.linalg.norm(right), 1e-6); up = np.cross(right, d)
        v = C - cam; a = v @ d
        if a < -r or a > near + r: continue
        th = 18.0 / lens * 1.1; tv = 10.125 / lens * 1.1
        if abs(v @ right) - r < max(a, 0) * th + 0.5 and abs(v @ up) - r < max(a, 0) * tv + 0.5: return True
    return False

def zone(S):
    prec = Polygon(S.polygon[0][0])
    keep = [Polygon(b['poly'][0][0]).buffer(2.0) for b in S.osm['buildings'] if b['id'] in KEEP]
    return prec.difference(shapely.unary_union(keep)).buffer(0)

def blocked(S, extra=()):
    """where no tree may stand: buildings, the modelled halls' roofs, corridors, paths, courts, water, stairs"""
    g = []
    for b in S.osm['buildings']:
        g.append(Polygon(b['poly'][0][0]).buffer(1.6))
    for w in S.osm['ways']:
        hw = w['tags'].get('highway', '')
        for ln in w['line']:
            g.append(LineString(ln).buffer((w.get('width') or 1.6) / 2 + (0.5 if hw in ('path', 'footway', 'steps') else 1.5)))
    for w in S.osm['water']:
        for p in w['poly']:
            g.append(Polygon(p[0], p[1:]).buffer(0.6))
    for w in S.osm['barriers']:
        for ln in w['line']:
            g.append(LineString(ln).buffer(0.9))
    for c in COURTS: g.append(Polygon(c))
    for (pts, wd) in PATHS_STONE: g.append(LineString(pts).buffer(wd / 2 + 0.6))
    g += list(extra)
    return shapely.unary_union(g)

def land(B, S, trees=True, shots=()):
    Z = zone(S)
    for p in (Z.geoms if hasattr(Z, 'geoms') else [Z]):
        if p.area < 10: continue
        S.exclude.append([list(p.exterior.coords)] + [list(r.coords) for r in p.interiors])
    # ---- ground paint
    def paint(poly, surf):
        polys = poly.geoms if hasattr(poly, 'geoms') else [poly]
        for p in polys:
            if p.is_empty or p.area < 0.5: continue
            S.paint.append({'poly': [list(p.exterior.coords)] + [list(r.coords) for r in p.interiors], 'surf': surf})
    hill = Z.intersection(Polygon([(3368, 3030), (3430, 3030), (3430, 3300), (3360, 3300), (3366, 3160), (3378, 3125), (3380, 3090), (3376, 3060)]))
    garden = Z.difference(hill)
    paint(garden, 'moss')
    paint(hill, 'forest')
    for c in COURTS: paint(Polygon(c), 'gravel')
    for c in SAND: paint(Polygon(c), 'sand')
    gw = []
    for w in S.osm['ways']:
        if w['id'] in PATHS_GRAVEL_IDS:
            for ln in w['line']: gw.append(LineString(ln).buffer((w.get('width') or 1.6) / 2 + 0.25))
    paint(shapely.unary_union(gw), 'gravel')
    paint(LineString(PATHS_STONE[0][0]).buffer(4.8, cap_style='flat'), 'gravel')
    for (pts, wd) in PATHS_STONE: paint(LineString(pts).buffer(wd / 2, cap_style='flat'), 'stone_slab')
    if not trees: return
    # ---- trees
    rng = np.random.default_rng(1203)
    extra = [LineString([(3364.6, 3100.2), (3374.4, 3098.9)]).buffer(2.4), LineString([(3374.4, 3100.6), (3373.0, 3104.2), (3372.5, 3108.6), (3373.9, 3113.6),
             (3373.1, 3119.0), (3373.9, 3124.2), (3372.6, 3128.8), (3372.2, 3131.4), (3371.8, 3135.4)]).buffer(3.0),
             LineString([(3362.9, 3087.5), (3366.4, 3085.0), (3367.3, 3078.2), (3367.9, 3070.7)]).buffer(2.6),
             LineString([(3359.6, 3140.0), (3362.0, 3137.2), (3363.3, 3129.0), (3362.3, 3115.5)]).buffer(2.6),
             Point(3351.3, 3102.7).buffer(21.5), Point(3364.1, 3061.7).buffer(13.5), Point(3386.9, 3136.7).buffer(7.5), Point(3340.2, 3146.4).buffer(13.0),
             Point(3376.0, 3131.6).buffer(5.2), Point(3374.6, 3083.9).buffer(8.0), Point(3346.8, 3046.0).buffer(5.0),
             LineString([(3369.6, 3141.4), (3369.4, 3144.4), (3374.4, 3153.2), (3382.2, 3146.3), (3381.6, 3141.2)]).buffer(1.8),
             LineString([(3318.5, 3072.8), (3332.0, 3069.6), (3346.6, 3066.2)]).buffer(3.6),
             Point(3246.2, 3121.4).buffer(9.0), Point(3325.4, 3175.2).buffer(12.0), Point(3326.6, 3160.6).buffer(8.5)]
    # the street front of the 総門 (only the two small gardens keep their maples)
    extra.append(box(3180, 3176, 3205.5, 3226).difference(Polygon([(3194, 3189.5), (3203.8, 3189.5), (3203.8, 3197.5), (3194, 3197.5)])))
    # the approach's gravel, a clear rim along the pond (only the hand-placed maples overhang the water), and the spots
    # visitors photograph from (the preview cameras stand there)
    extra.append(LineString(PATHS_STONE[0][0]).buffer(4.6, cap_style='flat'))
    w_ = [x for x in S.osm['water'] if x['id'] == -16642160][0]
    extra.append(Polygon(w_['poly'][0][0]).buffer(2.4))
    BL = blocked(S, extra)
    free = Z.difference(BL)
    wet = shapely.unary_union([Polygon(p[0], p[1:]) for w in S.osm['water'] for p in w['poly']])
    for (sp, x, y, sc, yaw) in SPECIMENS:
        if wet.contains(Point(x, y)):
            print('specimen in water, skipped', sp, x, y); continue
        B.tree(sp, x, y, float(S.ground(x, y)), sc, yaw)
    spec_pts = shapely.unary_union([Point(x, y).buffer(3.5) for (_, x, y, _, _) in SPECIMENS])
    free = free.difference(spec_pts)
    areas = [
        ('approach', box(3205, 3184, 3270, 3216), 5.2),
        ('pond', box(3196, 3086, 3306, 3182), 5.2),
        ('garden', box(3270, 3120, 3340, 3200), 5.0),
        ('garden', box(3300, 3080, 3345, 3125), 5.4),
        ('slope', Polygon([(3300, 3030), (3366, 3030), (3376, 3060), (3380, 3090), (3378, 3125), (3366, 3160), (3366, 3200), (3345, 3200), (3345, 3080), (3300, 3080)]), 5.0),
        ('slope', Polygon([(3366, 3060), (3400, 3060), (3404, 3160), (3366, 3160), (3378, 3125), (3380, 3090)]), 4.8),
        ('forest', Polygon([(3400, 3030), (3430, 3030), (3430, 3300), (3360, 3300), (3366, 3160), (3404, 3160)]), 6.0),
        ('forest', box(3366, 2980, 3430, 3060), 6.0),
        ('other', box(3180, 2980, 3366, 3086), 7.5),
        ('other', box(3180, 3184, 3366, 3300), 7.0),
    ]
    taken = None
    n = 0
    for (mix, poly, sp) in areas:
        region = free.intersection(poly)
        if taken is not None: region = region.difference(taken)
        if region.is_empty: continue
        pts = poisson(region, sp, rng)
        taken = poly if taken is None else taken.union(poly)
        for (x, y) in pts:
            name = pick(MIX[mix], rng.uniform())
            s0, s1 = SCALE[name]
            sc = rng.uniform(s0, s1)
            z = float(S.ground(x, y))
            if blocks_view(shots, S, name, x, y, z, sc): continue
            B.tree(name, float(x), float(y), z, float(sc), float(rng.uniform(0, 2 * math.pi)))
            n += 1
    # azalea shrubs along the pond shore and in the moss gardens
    w = [x for x in S.osm['water'] if x['id'] == -16642160][0]
    P = Polygon(w['poly'][0][0], w['poly'][0][1:])
    shore = P.buffer(2.6).difference(P.buffer(0.9)).difference(BL.difference(P.buffer(0.95)))
    for (x, y) in poisson(shore, 2.6, rng, limit=140):
        if blocks_view(shots, S, 'tsutsuji', x, y, float(S.ground(x, y)), 1.2, near=4.0): continue
        B.tree('tsutsuji', float(x), float(y), float(S.ground(x, y)), float(rng.uniform(0.9, 1.5)), float(rng.uniform(0, 6.28)))
    garden = free.intersection(box(3296, 3120, 3320, 3195))
    for (x, y) in poisson(garden, 3.2, rng, limit=50):
        B.tree('tsutsuji', float(x), float(y), float(S.ground(x, y)), float(rng.uniform(0.8, 1.3)), float(rng.uniform(0, 6.28)))
    print(f'eikando trees: {len(B.trees)} ({n} in areas)')
