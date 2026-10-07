"""Material ids shared by the generator (python), the bake (Blender) and the viewer (public/data/materials.json).

Every material names a 'kind' (the shader program in web/kyomat.js) and a texture-array layer (tex_build.py).
albedo: average linear colour for bounce light in the Cycles bake (c0-tinted kinds multiply by the tint).
Vertex attributes (gen/mesh.py): MAT = id; C0 = tint rgb + a param; C1 = (y param, z seed, w flags) — see each kind."""
import json

LAYERS = [
    # name            texture set (ASSETS/textures)        size_m   flags
    ('plaster',       'Plaster003',                        2.0,  {'neutral': True}),
    ('wood_old',      'old_planks_02',                     2.0,  {}),
    ('wood_grey',     'wood_planks_grey',                  1.5,  {}),
    ('wood_fresh',    'hinoki_planks',                     1.9,  {}),
    ('concrete',      'concrete_wall_006',                 2.0,  {'neutral': True}),
    ('tile_facade',   'rectangular_facade_tiles_02',       2.1,  {'neutral': True}),
    ('corrugated',    'worn_corrugated_iron',              1.8,  {'neutral': True}),
    ('asphalt',       'Asphalt031',                        2.0,  {}),
    ('paving',        'PavingStones070',                   1.15, {}),
    ('stone_sett',    'PavingStones109',                   1.0,  {}),
    ('gravel',        'Gravel026',                         1.5,  {}),
    ('soil',          'Ground016',                         3.0,  {}),
    ('grass',         'Grass004',                          1.4,  {}),
    ('withered',      'withered_grass',                    2.0,  {}),
    ('moss',          'Moss002',                           1.0,  {}),
    ('leaves',        'ScatteredLeaves009',                1.7,  {}),
    ('forest',        'forest_floor',                      2.1,  {}),
    ('stone_wall',    'japanese_stone_wall',               1.9,  {}),
    ('pebbles',       'ganges_river_pebbles',              2.2,  {}),
    ('roof_tiles',    'grey_roof_tiles',                   3.0,  {}),
    ('metal',         'Metal034',                          1.0,  {}),
    ('bark_cedar',    'japanese_cedar_bark',               1.0,  {}),
    ('bark_sakura',   'sakura_bark',                       1.6,  {}),
    ('bamboo',        'Bamboo001A',                        1.3,  {}),
    ('tatami',        'tatami_mat',                        1.8,  {}),
    ('snow',          'Snow006',                           2.5,  {}),
]
LAYER = {n: i for i, (n, *_r) in enumerate(LAYERS)}

# (name, layer, kind, albedo lin rgb)
MATS = [
    # ---- generic building walls (facade programs in the shader; u along the wall, v height above the building's ground)
    ('wall_plaster',   'plaster',     'wall',     (0.62, 0.60, 0.55)),   # tinted plaster / render, windows by c1
    ('wall_earth',     'plaster',     'wall',     (0.45, 0.36, 0.25)),   # 聚楽 / 土壁
    ('wall_board',     'wood_grey',    'wall',     (0.06, 0.05, 0.04)),   # 焼杉板 dark cedar boards
    ('wall_siding',    'concrete',    'wall',     (0.55, 0.52, 0.47)),   # 窯業系サイディング (tinted)
    ('wall_tile',      'tile_facade', 'wall',     (0.45, 0.38, 0.30)),   # mid-rise tile facade (tinted)
    ('wall_concrete',  'concrete',    'wall',     (0.45, 0.44, 0.42)),
    ('wall_metal',     'corrugated',       'wall',     (0.35, 0.36, 0.36)),   # corrugated sheet 波板
    ('machiya_front',  'wood_old',    'machiya',  (0.12, 0.08, 0.05)),   # street front of a machiya: lattice, doors, upper band
    ('glass_curtain',  'concrete',    'wall',     (0.05, 0.06, 0.07)),
    ('temple_wall',    'plaster',     'wall',     (0.66, 0.64, 0.60)),   # white plaster between dark posts and tie beams
    # ---- roofs (u along the eave, v down the slope from the ridge)
    ('kawara',         'roof_tiles',    'kawara',   (0.12, 0.12, 0.13)),   # 桟瓦 smoked grey tiles
    ('hongawara',      'roof_tiles',    'kawara',   (0.11, 0.11, 0.12)),   # 本瓦 (round + flat), temples
    ('roof_metal',     'metal',       'roofmetal',(0.20, 0.20, 0.20)),   # coloured steel with standing seams (tinted)
    ('roof_flat',      'concrete',    'roofflat', (0.35, 0.34, 0.32)),
    ('copper',         'metal',       'copper',   (0.18, 0.36, 0.30)),
    ('hiwada',         'wood_old',    'hiwada',   (0.10, 0.06, 0.04)),   # 檜皮葺 cypress bark
    ('ridge',          'roof_tiles',    'ridge',    (0.11, 0.11, 0.12)),   # 棟 / 鬼瓦
    ('eave_wood',      'wood_old',    'wood',     (0.09, 0.06, 0.04)),   # soffit with rafters, fascia
    # ---- ground (the tile raster picks the surface; the mesh is terrain)
    ('ground',         'asphalt',     'ground',   (0.12, 0.12, 0.12)),
    ('curb',           'concrete',    'stone',    (0.40, 0.39, 0.37)),
    ('paint',          None,          'paint',    (0.70, 0.70, 0.68)),
    ('stone',          'stone_wall',  'stone',    (0.32, 0.31, 0.29)),   # 石垣 / granite
    ('water',          None,          'water',    (0.02, 0.03, 0.03)),
    # ---- woods and paints (props + heroes)
    ('wood_dark',      'wood_old',    'wood',     (0.07, 0.05, 0.035)),
    ('wood_natural',   'wood_fresh',  'wood',     (0.35, 0.25, 0.16)),
    ('vermilion',      'wood_fresh',  'paint',    (0.55, 0.10, 0.04)),   # 丹塗り
    ('black_lacquer',  'wood_fresh',  'paint',    (0.02, 0.02, 0.02)),
    ('white_paint',    'wood_fresh',  'paint',    (0.70, 0.68, 0.62)),   # 胡粉
    ('bamboo',         'bamboo',      'wood',     (0.30, 0.25, 0.12)),
    ('metal_dark',     'metal',       'metal',    (0.05, 0.05, 0.05)),
    ('metal_grey',     'metal',       'metal',    (0.40, 0.40, 0.40)),
    ('glass',          None,          'glass',    (0.02, 0.02, 0.02)),
    ('lamp',           None,          'emissive', (1.00, 0.72, 0.42)),
    ('lantern_paper',  None,          'emissive', (1.00, 0.55, 0.25)),   # 提灯 (red-orange paper, lit)
    ('gold',           None,          'gold',     (0.90, 0.62, 0.25)),
    ('bronze',         'metal',       'metal',    (0.12, 0.09, 0.06)),
    ('cloth',          None,          'cloth',    (0.20, 0.10, 0.08)),   # 暖簾 etc. (tinted)
    ('tatami',         'tatami',      'floor',    (0.38, 0.35, 0.20)),
    ('snowcap',        'snow',        'snow',     (0.85, 0.87, 0.90)),   # winter only: snow slabs on roofs
    ('rail',           'metal',       'metal',    (0.10, 0.09, 0.08)),
    ('hedge',          'grass',       'hedge',    (0.05, 0.09, 0.03)),   # clipped hedges and shrubs as masses
    ('sand_raked',     'gravel',      'ground',   (0.60, 0.58, 0.54)),   # 銀沙灘 / raked gravel (uv along the rake)
    ('moss_mound',     'moss',        'ground',   (0.07, 0.12, 0.04)),
    ('screen',         None,          'emissive', (0.80, 0.92, 1.00)),   # vending machine fronts, shop light boxes
    ('sig_red',        None,          'emissive', (1.00, 0.10, 0.04)),
    ('sig_green',      None,          'emissive', (0.10, 1.00, 0.65)),
    ('wire',           'metal',       'metal',    (0.02, 0.02, 0.02)),   # overhead wires
]
MAT = {m[0]: i for i, m in enumerate(MATS)}
# emissive strength in the bake (evening: lamps are on)
EMIT = {'lamp': 30.0, 'lantern_paper': 8.0, 'screen': 12.0, 'sig_red': 10.0, 'sig_green': 10.0}

# ground surfaces (tile raster B channel) -> drawn by the ground program
SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck', 'masa']
SID = {n: i for i, n in enumerate(SURF)}
SURF_ALB = {'none': (0.20, 0.17, 0.13), 'asphalt': (0.075, 0.075, 0.075), 'asphalt_lane': (0.10, 0.10, 0.095), 'sidewalk': (0.30, 0.28, 0.25), 'stone_sett': (0.28, 0.27, 0.25),
            'gravel': (0.45, 0.43, 0.40), 'soil': (0.30, 0.24, 0.17), 'grass': (0.12, 0.16, 0.06), 'moss': (0.08, 0.13, 0.04), 'forest': (0.13, 0.09, 0.05),
            'riverbed': (0.20, 0.19, 0.16), 'ballast': (0.22, 0.21, 0.20), 'concrete': (0.38, 0.37, 0.35), 'sand': (0.55, 0.53, 0.48), 'graves': (0.32, 0.31, 0.30),
            'farm': (0.15, 0.12, 0.08), 'tactile': (0.55, 0.45, 0.05), 'stone_slab': (0.35, 0.34, 0.32), 'wood_deck': (0.20, 0.14, 0.09),
            'masa': (0.42, 0.36, 0.27)}     # decomposed granite (まさ土): the riverside paths

def export(path):
    out = {'layers': [{'name': n, 'src': s, 'size': sz, **f} for (n, s, sz, f) in LAYERS],
           'mats': [{'id': i, 'name': n, 'layer': (LAYER[l] if l else -1), 'kind': k, 'albedo': a, 'emit': EMIT.get(n, 0.0)} for i, (n, l, k, a) in enumerate(MATS)],
           'surf': [{'id': i, 'name': n, 'albedo': SURF_ALB[n]} for i, n in enumerate(SURF)]}
    json.dump(out, open(path, 'w'), indent=1)

# palettes (sRGB 0-255)
PLASTER = [(226, 222, 210), (214, 206, 186), (200, 190, 168), (232, 228, 218), (190, 176, 150), (176, 160, 132)]
EARTH = [(170, 132, 88), (152, 118, 80), (186, 150, 104), (140, 104, 70)]
SIDING = [(214, 208, 196), (196, 186, 170), (172, 160, 142), (220, 214, 200), (150, 140, 128), (120, 112, 104), (200, 196, 190)]
TILE = [(196, 176, 150), (170, 140, 112), (140, 110, 86), (214, 200, 176), (120, 96, 80), (186, 182, 176), (160, 158, 154)]
ROOF_METAL = [(60, 70, 84), (84, 60, 48), (52, 72, 60), (90, 90, 92), (110, 70, 52), (48, 56, 70)]
BENGARA = (128, 52, 36)
