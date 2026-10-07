"""天龍寺 hero site (the Arashiyama enclave): 天龍寺 (gates, 放生池, 法堂, 大方丈 / 小方丈, 庫裏, 多宝殿, 北門) and the
曹源池庭園; 竹林の小径 from the north gate past 野宮神社 to 大河内山荘; 野宮神社; 大河内山荘 (gate, paths, tea house);
亀山公園 (paths, the viewpoint over the 保津川 gorge); 常寂光寺 (thatched 仁王門, the steps through the maples, 本堂,
多宝塔).  The street (長辻通), the river and 渡月橋 belong to the arashiyama site.

Modules: tenryuji_kit (helpers), tenryuji_temple (buildings), tenryuji_garden (曹源池), tenryuji_bamboo (the bamboo
path, its fences, the planting, 野宮神社), tenryuji_west (大河内山荘, 亀山公園, 常寂光寺), tenryuji_land (trees, paint,
exclusions).  Reference photos and the dossier: /home/kazu/work/kyoto-assets/refs/tenryuji/."""
import os
import numpy as np

_T = np.load('/home/kazu/work/kyoto-assets/sites/tenryuji/terrain.npz')
def gz(x, y):
    """terrain height (bilinear on the site's 1 m DEM)"""
    H = _T['H']; fx = (x - float(_T['x0'])) / float(_T['res']); fy = (y - float(_T['y0'])) / float(_T['res'])
    ix, iy = int(fx), int(fy); ax, ay = fx - ix, fy - iy
    return float(H[iy, ix] * (1 - ax) * (1 - ay) + H[iy, ix + 1] * ax * (1 - ay) + H[iy + 1, ix] * (1 - ax) * ay + H[iy + 1, ix + 1] * ax * ay)
def eye(x, y, h=1.6): return (x, y, gz(x, y) + h)
def at(x, y, h=1.6): return (x, y, gz(x, y) + h)

# preview cameras (also the viewer's places): (name, camera, target, lens mm)
SHOTS = [
    ('bamboo_path', eye(-7790.0, 3532.3), at(-7845.0, 3517.0, 3.2), 24),               # 竹林の小径 west of 野宮神社, looking west up the path
    ('bamboo_slope', eye(-7993.0, 3441.6), at(-8045.0, 3420.6, 3.0), 24),              # the climb towards 大河内山荘
    ('nonomiya_torii', eye(-7720.6, 3531.4, 1.55), at(-7722.6, 3542.5, 2.6), 26),      # 黒木鳥居 from the path
    ('sogenchi', (-7775.2, 3316.0, 45.05), (-7815.0, 3303.0, 46.2), 24),                # 曹源池 from the 大方丈 west veranda
    ('kuri', eye(-7728.0, 3343.0), (-7752.0, 3348.5, 49.0), 30),                       # 庫裏 gable from the forecourt
    ('jojakko_niomon', eye(-8160.0, 3753.6), at(-8185.0, 3754.4, 3.6), 28),            # 仁王門 and the steps
    ('tahoto', eye(-8255.0, 3737.5), at(-8271.2, 3746.0, 6.5), 26),                    # 多宝塔
    ('kameyama_gorge', eye(-8136.4, 3283.4, 1.75), (-8262.0, 3305.0, 46.0), 26),       # 亀山 viewpoint deck over the 保津川 gorge
    ('aerial', (-7560.0, 3130.0, 240.0), (-7820.0, 3420.0, 50.0), 30),
]
DEV_SHOTS = [
    ('dev_hatto', (-7660.0, 3300.0, 45.0), (-7701.0, 3312.0, 48.0), 30),
    ('dev_hojo', (-7720.0, 3290.0, 47.0), (-7763.0, 3313.0, 46.0), 30),
    ('dev_gates', (-7470.0, 3325.0, 46.0), (-7515.0, 3328.0, 41.0), 30),
    ('dev_pond', (-7525.0, 3330.0, 44.0), (-7548.0, 3312.0, 39.0), 30),
    ('dev_tahoden', (-7838.0, 3368.0, 52.0), (-7842.0, 3392.0, 51.0), 30),
    ('dev_temple_air', (-7600.0, 3200.0, 140.0), (-7720.0, 3330.0, 42.0), 35),
    ('dev_bamboo_air', (-7760.0, 3420.0, 110.0), (-7880.0, 3500.0, 50.0), 30),
    ('dev_kitamon', eye(-7911.0, 3496.4), at(-7897.0, 3478.6, 2.4), 30),
    ('dev_garden_air', (-7740.0, 3260.0, 75.0), (-7810.0, 3320.0, 44.0), 30),
    ('dev_okochi', eye(-8061.0, 3413.6), at(-8084.0, 3414.8, 2.6), 28),
    ('dev_hojo_west', (-7797.0, 3328.0, 45.6), (-7765.0, 3313.0, 45.4), 28),
    ('dev_kuri_close', (-7739.0, 3349.6, 45.1), (-7752.0, 3348.2, 46.0), 32),
    ('dev_choku', (-7494.0, 3319.0, 41.0), (-7513.0, 3315.0, 42.6), 30),
    ('dev_fence', eye(-7871.0, 3511.5), at(-7880.0, 3504.0, 0.6), 30),
    ('dev_niomon', (-8166.0, 3745.0, 74.0), (-8180.0, 3754.0, 71.5), 30),
    ('dev_tahoto_near', (-8256.0, 3734.0, 90.0), (-8271.2, 3746.0, 92.0), 30),
    ('dev_jojakko_air', (-8120.0, 3690.0, 140.0), (-8230.0, 3760.0, 75.0), 30),
    ('dev_west_air', (-7900.0, 3150.0, 260.0), (-8150.0, 3500.0, 60.0), 30),
]
MAIN_SHOTS = list(SHOTS)
if os.environ.get('TJ_DEV'):
    SHOTS = SHOTS + DEV_SHOTS
if os.environ.get('TJ_SHOTS'):
    want = os.environ['TJ_SHOTS'].split(',')
    SHOTS = [s for s in SHOTS + DEV_SHOTS if s[0] in want]

PARTS = ['temple', 'garden', 'bamboo', 'nonomiya', 'west', 'jojakkoji', 'land']

def build(B, S, only=None):
    from . import tenryuji_temple as T
    from . import tenryuji_kit as K
    K.SHOTS = list(MAIN_SHOTS)
    parts = only or PARTS
    ctx = {}
    if 'temple' in parts: ctx['temple'] = T.build(B, S)
    if 'garden' in parts:
        from . import tenryuji_garden as G
        ctx['garden'] = G.build(B, S)
    if 'bamboo' in parts or 'nonomiya' in parts:
        from . import tenryuji_bamboo as BB
        ctx['bamboo'] = BB.build(B, S, parts)
    if 'west' in parts or 'jojakkoji' in parts:
        from . import tenryuji_west as W
        ctx['west'] = W.build(B, S, parts)
    from . import tenryuji_land as LAND
    LAND.build(B, S, parts, ctx, SHOTS)
    # preview renders: tree proxies and tinted vertex colours (added after the .blend is saved)
    try:
        import render_scene
        from . import tenryuji_kit as K
        if not getattr(render_scene, '_tj_patched', False):
            orig = render_scene.setup
            def setup2(*a, **kw):
                orig(*a, **kw)
                K.add_preview_proxies(B, S, LAND.preview_ground(S))
            render_scene.setup = setup2; render_scene._tj_patched = True
    except Exception as e:
        print('preview patch failed', e)
