"""三十三間堂 (蓮華王院): the main hall with its interior and statue stage, 南大門, 太閤塀, 東大門 and the vermilion
galleries, the bell tower, 手水舎 / 夜泣泉, the east garden ponds, walls, paths and trees.

Hall frame: origin on the hall axis at the veranda deck (FL), u = north along the axis (bearing 002°), v = west.
Statue slots -> /home/kazu/work/kyoto-assets/heroes/sanjusangendo_slots.json (world frame)."""
import json, math, os
import numpy as np
from jk import Frame
from . import sanjusangendo_parts as P
from . import sanjusangendo_hall as HALL
from . import sanjusangendo_stage as STAGE

SLOTS_PATH = '/home/kazu/work/kyoto-assets/heroes/sanjusangendo_slots.json'
HALL_OSM = 99185529
G0 = 38.55                 # reference ground at the hall (T.P., DEM)
FL_ABOVE = 1.30            # veranda deck above the ground

SHOTS = []

def hall_frame(S):
    """(origin x, y, z_FL, yaw, U, V): the OSM footprint is the roof outline; its east eave is set back except at the
    向拝, so the axis lies 2.5 m west of the rectangle's centre line"""
    cx, cy, L, W, yaw = S.rect(S.osm_building(HALL_OSM)['poly'][0])
    U = np.array([math.cos(yaw), math.sin(yaw)]); V = np.array([-math.sin(yaw), math.cos(yaw)])
    O = np.array([cx, cy]) + 2.5 * V + 0.5 * U
    return O, G0 + FL_ABOVE, yaw, U, V

def build(B, S, only=None):
    global SHOTS
    O, zfl, yaw, U, V = hall_frame(S)
    W = lambda u, v: O + u * U + v * V                       # hall frame -> world xy
    gz = lambda u, v: float(S.ground(*W(u, v))) - zfl          # local ground (relative to FL)
    want = lambda part: only is None or part in only
    M = None
    with Frame(B, O[0], O[1], zfl, yaw) as F:
        M = F.M.copy()
        if want('hall'): info = HALL.build(B, G0 - zfl, gz)
        if want('stage'):
            sl = STAGE.build(B)
            export_slots(sl, M, yaw)
    if want('grounds'):
        from . import sanjusangendo_grounds as GR
        GR.build(B, S, O, zfl, yaw, U, V)
    # ------------------------------------------------------------------ preview shots (world)
    def wp(u, v, z): q = W(u, v); return (float(q[0]), float(q[1]), float(z))
    g = G0
    SHOTS = [
        ('east_front', wp(0, -40, 0), wp(0, 0, 0), 24),
        ('east_oblique', wp(78, -24, 0), wp(10, -4, 0), 24),
        ('west_veranda', wp(-66.5, 12.5, 0), wp(30, 9.2, 0), 30),
        ('west_long', wp(-74, 24, 0), wp(10, 9, 0), 24),
        ('north_end', wp(84, -22, 0), wp(56, 0, 0), 28),
        ('aerial', wp(-150, -140, 0), wp(-10, 0, 0), 30),
        ('interior', wp(44, -7.6, 0), wp(24, -1.0, 0), 20),
        ('interior_end', wp(57.6, -7.2, 0), wp(42, 2.5, 0), 20),
        ('interior_centre', wp(9, -7.6, 0), wp(0, 0.2, 0), 22),
        ('south_gate', wp(-60, -57, 0), wp(-96, -55, 0), 28),
        ('taikobei', wp(-89.5, -26, 0), wp(-97.5, 2, 0), 28),
        ('south_gate_street', wp(-113.5, -40, 0), wp(-96, -56, 0), 26),
        ('southeast', wp(-84, -30, 0), wp(-40, 0, 0), 26),
        ('garden', wp(-18, -26, 0), wp(-34, -46, 0), 26),
        ('east_gate', wp(0.5, -20, 0), wp(0.5, -48, 0), 30),
        ('bell_tower', wp(-42, -24, 0), wp(-58, -36, 0), 30),
    ]
    zs = {'east_front': (g + 1.6, g + 6.0), 'east_oblique': (g + 1.7, g + 4.5), 'west_veranda': (g + 1.6, zfl + 1.6),
          'west_long': (g + 1.6, g + 5.0), 'north_end': (g + 1.6, g + 7.5), 'aerial': (g + 95, g + 4), 'interior': (zfl + 1.65, zfl + 2.2), 'interior_end': (zfl + 1.65, zfl + 2.4),
          'interior_centre': (zfl + 1.6, zfl + 3.6), 'south_gate': (g + 2.6, g + 6.5), 'taikobei': (g + 1.6, g + 3.4), 'south_gate_street': (g + 1.9, g + 6.5), 'southeast': (g + 1.6, g + 6.0), 'garden': (g + 1.7, g + 3.0), 'east_gate': (g + 1.6, g + 4.5), 'bell_tower': (g + 1.6, g + 4.5)}
    SHOTS = [(n, (c[0], c[1], zs[n][0]), (t[0], t[1], zs[n][1]), lens) for (n, c, t, lens) in SHOTS]

def export_slots(sl, M, yaw):
    """hall-frame slots -> world JSON.  yaw: radians ccw from east, the direction the statue faces"""
    def w(p):
        q = M[:3, :3] @ np.array(p[:3], float) + M[:3, 3]
        return [round(float(q[0]), 3), round(float(q[1]), 3), round(float(q[2]), 3)]
    face = {'E': yaw - math.pi / 2, 'W': yaw + math.pi / 2}
    def yw(c): a = face[c]; return round(math.atan2(math.sin(a), math.cos(a)), 5)
    out = {
        'kannon_standing': [w(s) + [yw(s[3])] for s in sl['kannon_standing']],
        'kannon_seated': [w(s) + [yw(s[3])] for s in sl['kannon_seated']],
        'attendants': [],
        'fujin': w(sl['fujin']) + [yw(sl['fujin'][3])],
        'raijin': w(sl['raijin']) + [yw(sl['raijin'][3])],
        'kannon_rear_1001': [w(s) + [yw(s[3])] for s in sl['kannon_rear']],
    }
    for a in sl['attendants']:
        p = w((a['u'], a['v'], a['z']))
        out['attendants'].append(dict(name=a['name'], jp=a['jp'], pos=a['pos'], x=p[0], y=p[1], z=p[2], yaw=yw('E'), height_m=a['h']))
    out['_notes'] = ('World frame (x east, y north, z T.P.). z = top of the dais under the statue (pedestal bottom); yaw = facing '
                     'direction, radians ccw from east (they face east, toward the visitors\' aisle). kannon_standing is in the temple\'s '
                     'numbering order (index = number - 1): no. 1 = south end, top (back) tier; 10 = south end, front tier; 11 = 2nd column '
                     'from the south ...; 1000 = north end, front tier; 10 rows x 50 columns per side, rows staggered by half a column. '
                     'attendants: 2018 arrangement in walking order north -> south (N1 = north end ... N12, the four round the 中尊 '
                     '(CFN front-north, CRN rear-north, CRS rear-south, CFS front-south, on the 須弥壇), S1 ... S12 = south end); '
                     '風神 at the north end, 雷神 at the south end. kannon_rear_1001: the 1001st statue behind the 中尊, facing west.')
    out['_frame'] = dict(hall_origin=[round(float(M[0, 3]), 3), round(float(M[1, 3]), 3), round(float(M[2, 3]), 3)], hall_yaw=round(yaw, 6),
                         floor_z=round(float(M[2, 3]) + P.FLI, 3))
    os.makedirs(os.path.dirname(SLOTS_PATH), exist_ok=True)
    json.dump(out, open(SLOTS_PATH, 'w'), ensure_ascii=False, indent=1)
    print('slots:', len(out['kannon_standing']), 'standing,', len(out['attendants']), 'attendants ->', SLOTS_PATH, flush=True)
