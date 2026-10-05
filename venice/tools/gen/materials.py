"""Material ids shared by the generator (python) and the viewer (public/data/materials.json).

Each material maps to a texture-array layer (see tex_build.py) plus shading flags.  'albedo' is the
average linear colour used for bounce light in the Cycles bake (tinted materials multiply it by the tint).
kind: wall | ground | roof | stone | wood | metal | glass | water | emissive | plain
"""
import json

# texture layers (2K city array): name -> source
LAYERS = [
    # name            source texture set                  size_m  flags
    ('plaster',       'painted_plaster_wall',              2.0,   {'neutral': True}),
    ('plaster_peel',  'PaintedPlaster014',                 2.0,   {'neutral_mask': True}),
    ('plaster_red',   'red_plaster_weathered',             2.0,   {}),
    ('plaster_yel',   'yellow_plaster',                    2.0,   {}),
    ('plaster_worn',  'worn_plaster_wall',                 1.8,   {}),
    ('brick',         'red_bricks_04',                     2.5,   {}),
    ('brick_old',     'red_brick_plaster_patch_02',        1.5,   {}),
    ('stone_block',   'marble_01',                         1.5,   {}),
    ('stone_rough',   'white_sandstone_blocks_02',         2.0,   {}),
    ('masegni',       'masegni',                           3.0,   {}),
    ('coppi',         'clay_roof_tiles_02',                2.5,   {}),
    ('coppi_old',     'RoofingTiles014C',                  2.0,   {}),
    ('wood_paint',    'green_rough_planks',                1.5,   {'neutral': True}),
    ('wood_raw',      'weathered_planks',                  2.0,   {}),
    ('algae',         'brick_moss_001',                    2.2,   {}),
    ('metal',         'rusty_metal',                       1.5,   {}),
]
LAYER = {n: i for i, (n, *_r) in enumerate(LAYERS)}

# material id -> (name, layer, kind, albedo(lin rgb) , extra)
MATS = [
    ('wall_plaster',   'plaster',     'wall',   (0.62, 0.58, 0.52)),   # tinted
    ('wall_brick',     'brick',       'wall',   (0.30, 0.15, 0.10)),
    ('wall_stone',     'stone_block', 'wall',   (0.62, 0.58, 0.50)),
    ('ground',         'masegni',     'ground', (0.20, 0.19, 0.18)),
    ('coping',         'stone_rough', 'stone',  (0.55, 0.52, 0.46)),
    ('riva',           'brick_old',   'wall',   (0.28, 0.17, 0.12)),
    ('roof',           'coppi',       'roof',   (0.38, 0.17, 0.09)),
    ('roof_old',       'coppi_old',   'roof',   (0.25, 0.14, 0.10)),
    ('trim',           'stone_block', 'stone',  (0.65, 0.62, 0.55)),
    ('wood_paint',     'wood_paint',  'wood',   (0.20, 0.30, 0.22)),   # tinted
    ('wood_raw',       'wood_raw',    'wood',   (0.18, 0.13, 0.09)),
    ('metal',          'metal',       'metal',  (0.08, 0.07, 0.06)),
    ('glass',          None,          'glass',  (0.02, 0.02, 0.02)),
    ('bridge_brick',   'brick',       'wall',   (0.30, 0.15, 0.10)),
    ('bridge_stone',   'stone_rough', 'stone',  (0.58, 0.55, 0.48)),
    ('flat_roof',      'stone_rough', 'roof',   (0.35, 0.33, 0.30)),
    ('lawn',           None,          'plain',  (0.08, 0.16, 0.05)),
    ('dark',           None,          'plain',  (0.03, 0.03, 0.03)),
    # hero materials
    ('portico_floor',  'stone_block', 'ground', (0.45, 0.42, 0.38)),
    ('portico_wall',   'plaster',     'wall',   (0.60, 0.57, 0.52)),   # tinted
    ('shop_wood',      'wood_raw',    'wood',   (0.12, 0.08, 0.05)),
    ('florian_wood',   'wood_raw',    'wood',   (0.10, 0.05, 0.03)),
    ('shop_sign',      None,          'plain',  (0.05, 0.05, 0.05)),
    ('florian_sign',   None,          'plain',  (0.12, 0.02, 0.02)),
    ('istrian',        'stone_rough', 'stone',  (0.62, 0.60, 0.55)),
    ('campanile_brick','brick',       'wall',   (0.32, 0.14, 0.08)),
    ('copper',         'stone_block', 'marble', (0.20, 0.40, 0.31)),
    ('gold',           None,          'gold',   (0.95, 0.70, 0.32)),
    ('relief',         'stone_block', 'stone',  (0.60, 0.57, 0.50)),
    ('marble_white',   'stone_block', 'marble', (0.47, 0.45, 0.42)),
    ('marble_red',     'stone_block', 'marble', (0.55, 0.22, 0.16)),
    ('marble_verde',   'stone_block', 'marble', (0.06, 0.12, 0.09)),
    ('marble_pink',    'stone_block', 'marble', (0.78, 0.55, 0.50)),
    ('mosaic_gold',    None,          'mosaic', (0.52, 0.33, 0.08)),
    ('bronze',         'metal',       'metal',  (0.10, 0.08, 0.05)),
    ('bronze_gilt',    None,          'gold',   (0.60, 0.42, 0.18)),
    ('lead',           'stone_rough', 'roof',   (0.20, 0.21, 0.22)),
    ('basilica_wall',  'stone_block', 'marble', (0.40, 0.37, 0.33)),
    ('glass_lattice',  None,          'glass',  (0.02, 0.02, 0.02)),
    ('lion_field',     None,          'plain',  (0.03, 0.06, 0.20)),
    ('mosaic_photo',   None,          'photo',  (0.50, 0.40, 0.25)),
    ('ducale_wall',    'stone_block', 'lozenge', (0.70, 0.50, 0.44)),
    ('granite_grey',   'stone_rough', 'marble', (0.30, 0.30, 0.31)),
    ('granite_pink',   'stone_rough', 'marble', (0.42, 0.30, 0.28)),
    ('clock_blue',     None,          'plain',  (0.02, 0.05, 0.22)),
    # interiors (no weathering)
    ('parquet',        'wood_raw',    'interior', (0.13, 0.075, 0.04)),
    ('walnut',         'wood_raw',    'interior', (0.065, 0.035, 0.02)),
    ('velvet',         None,          'interior', (0.15, 0.010, 0.016)),
    ('cream',          'plaster',     'interior', (0.70, 0.62, 0.48)),
    ('pale_blue',      'plaster',     'interior', (0.52, 0.62, 0.66)),
    ('gilt',           None,          'interior', (0.58, 0.41, 0.15)),
    ('mirror',         None,          'mirror',   (0.75, 0.75, 0.74)),
    ('lamp_glass',     None,          'emissive', (1.00, 0.72, 0.42)),
    ('painting',       None,          'photo',    (0.40, 0.32, 0.22)),
    ('terrazzo',       'stone_rough', 'interior', (0.42, 0.30, 0.25)),
    ('cast_iron',      None,          'metal',    (0.04, 0.04, 0.04)),
    ('linen',          None,          'interior', (0.78, 0.76, 0.72)),
    ('basilica_marble','stone_block', 'interior', (0.46, 0.41, 0.36)),
    ('basilica_floor', 'stone_rough', 'floor',    (0.45, 0.40, 0.35)),
    ('daylight',       None,          'emissive', (0.92, 0.96, 1.00)),
    ('street_glass',   None,          'emissive', (1.00, 0.74, 0.46)),     # outdoor lamps: lit only at night
    ('basilica_front', 'stone_block', 'marble',   (0.40, 0.37, 0.32)),     # San Marco's west front: warm, weathered
    ('basilica_marble_ext', 'stone_block', 'marble', (0.33, 0.31, 0.29)),  # its grey veined panels
    ('porphyry',       'stone_block', 'marble',   (0.20, 0.07, 0.07)),     # imperial red porphyry (Tetrarchs, Pietra del Bando)
    ('actv_paint',     None,          'plain',    (0.56, 0.58, 0.58)),     # vaporetto stops (pontoons.py): pale grey painted steel
    ('actv_yellow',    None,          'plain',    (0.78, 0.55, 0.04)),     # ACTV yellow: name boards, boarding edges
    ('hull_paint',     None,          'plain',    (0.035, 0.04, 0.045)),   # pontoon hulls: near-black painted steel
]
# emissive strength (Blender emission strength) per material in the bake: (day, night)
EMIT = {'lamp_glass': (60.0, 60.0), 'daylight': (45.0, 0.0), 'street_glass': (0.0, 60.0)}
MAT = {m[0]: i for i, m in enumerate(MATS)}

def export(path):
    out = {'layers': [{'name': n, 'src': s, 'size': sz, **f} for (n, s, sz, f) in LAYERS],
           'mats': [{'id': i, 'name': n, 'layer': (LAYER[l] if l else -1), 'kind': k, 'albedo': a, 'emit': EMIT.get(n, (0, 0))} for i, (n, l, k, a) in enumerate(MATS)]}
    json.dump(out, open(path, 'w'), indent=1)

# Venetian plaster palette (sRGB 0-255): ochre, apricot, terracotta, venetian red, salmon, cream, pale yellow, grey-white, rose
PALETTE = [
    (214, 160, 102), (226, 176, 124), (199, 120, 82), (176, 84, 62), (222, 150, 120),
    (232, 214, 178), (226, 196, 128), (205, 200, 190), (214, 168, 150), (190, 110, 70),
    (236, 190, 140), (168, 96, 74), (220, 205, 170), (200, 150, 96),
]
SHUTTERS = [(52, 84, 58), (44, 72, 54), (60, 92, 70), (70, 56, 40), (88, 96, 84), (40, 60, 52)]
