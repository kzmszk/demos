"""三十三間堂 statues: build, LOD, export, preview.

    cd /home/kazu/work/demos/kyoto/tools
    blender -b --python blender/sites/statues_build.py -- [ids ...] [--all] [--render] [--blend] [--lineup] [--rows]

Every statue is a Model: organic SDF fields (meshed with OpenVDB, decimated per LOD), instanced sub-meshes
(hands, the small heads of the 十一面 crown) and explicit geometry (pedestals, halos, rods, ribbons, attributes)
rebuilt per LOD.  Output: /home/kazu/work/kyoto-assets/heroes/statues/<id>.npz, <id>_lod1.npz, <id>_lod2.npz
(local frame: origin at the bottom centre of the pedestal, facing +y, z up, metres) + index.json; previews in
heroes/previews/statues_<id>.png; all statues lined up in blender/sanjusangendo_statues.blend."""
import sys, os, time, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import numpy as np
import bpy
import jk
from sites import statues_sdf as S, statues_mesh as M, statues_body as Bd, statues_props as X, statues_wood as W

OUT = '/home/kazu/work/kyoto-assets/heroes/statues'
PREV = '/home/kazu/work/kyoto-assets/heroes/previews'
BLEND = '/home/kazu/work/kyoto-assets/blender/sanjusangendo_statues.blend'
CLOSE = os.environ.get('STATUES_CLOSE', '/tmp/statues_close')
LODQ = [1.0, 0.4, 0.12]

class Model:
    def __init__(self, id, name_ja, name_en, budget=(60000, 12000, 1800), lift=0.0, figure_h=None):
        self.id = id; self.name_ja = name_ja; self.name_en = name_en
        self.budget = list(budget); self.lift = lift; self.figure_h = figure_h
        self.fields = []        # [field, h, share, adapt]
        self.inst = []          # [key, maker, share_each, xfs]
        self.xm_fn = None       # q -> XM (in figure coordinates)
        self.pal = {}
        self.cache = {}
        self.min_tris = {}
        import zlib; self.weather = weather_fn(zlib.crc32(id.encode()) % 997, 1.0)
        self.shade = False          # SDF cavity/ridge shading of tinted materials (aged wood)
        self.photo = None           # reference photo for the side-by-side check render
    def field(self, f, h, share=1.0, lods=(0, 1, 2)): self.fields.append([f, h, share, tuple(lods)]); return f
    def instance(self, key, maker, share, xfs, maxlod=2): self.inst.append([key, maker, share, list(xfs), maxlod])

def weather_fn(seed, amount=1.0):
    """faded polychrome: per-vertex tint variation for 'cloth' parts (patchy fading, dark wood showing through)"""
    def fn(PP, c0):
        P = np.asarray(PP, np.float32)
        n1 = S.fbm(P, 0.09, 3, seed); n2 = S.fbm(P, 0.035, 2, seed + 50)
        base = np.asarray(c0[:3], np.float32)[None, :]
        k = (0.86 + 0.16 * n1 + 0.06 * n2)[:, None]
        dark = np.array([52, 42, 34], np.float32)[None, :]
        t = (np.clip((n1 * 0.7 + n2 * 0.5) - 0.15, 0, 0.6) * amount)[:, None]
        col = (base * k) * (1 - t) + dark * t
        out = np.zeros((len(P), 4), np.uint8); out[:, :3] = np.clip(col, 0, 255); out[:, 3] = c0[3] if len(c0) > 3 else 0
        return out
    return fn

def palette(**kw):
    """slot -> (mat, c0); defaults: everything 'cloth' grey"""
    pal = {i: ('cloth', (120, 110, 100, 0)) for i in range(len(Bd.LABELS))}
    for k, v in kw.items():
        if isinstance(v, str): v = (v, (255, 255, 255, 0))
        elif len(v) == 2 and isinstance(v[0], str): v = (v[0], tuple(v[1]) + (0,) * (4 - len(v[1])))
        else: v = ('cloth', tuple(v) + (0,) * (4 - len(v)))
        pal[Bd.L[k]] = v
    return pal

FAST = float(os.environ.get('STATUES_FAST', '1.0'))

def _hires(model, key, f, h):
    if key not in model.cache:
        model.cache[key] = f.mesh(h * FAST)
    return model.cache[key]

def build_lods(model, lods=(0, 1, 2), verbose=True):
    """-> list of jk.Builder (one per LOD) + tri counts"""
    t0 = time.time()
    builders = []
    # hi-res meshes once
    hi_f = [_hires(model, f'f{i}', f, h) for i, (f, h, sh, fl) in enumerate(model.fields)]
    hi_i = []
    for key, maker, sh, xfs, ml in model.inst:
        f, h = maker()
        hi_i.append((f, h, _hires(model, 'i_' + key, f, h)))
    for l in lods:
      q = LODQ[l]
      xm = model.xm_fn(q) if model.xm_fn else X.XM()
      nx = xm.ntri()
      rest = max(model.budget[l] * 0.9 - nx, model.budget[l] * 0.2)
      for attempt in range(3):
          tot_share = sum(sh for (_, _, sh, fl) in model.fields if l in fl) + sum(sh * len(xfs) for (_, _, sh, xfs, ml) in model.inst if l <= ml)
          B = jk.Builder(model.id)
          lift = np.array([0, 0, model.lift], np.float32)
          for (f, h, sh, fl), (P, T, LAB) in zip(model.fields, hi_f):
              if l not in fl: continue
              tgt = int(rest * sh / tot_share)
              vw = None
              if getattr(model, 'back_bias', 0) > 0:
                  Nv = M.vnormals(P, T)
                  vw = 0.95 + 0.05 * np.clip(-Nv[:, 1] * 1.5, 0, 1)          # every vertex weighted (else unweighted ones are never collapsed)
              (P2, T2, l2, N2), = M.decimate(P, T, M.face_labels(T, LAB), [max(tgt, 200)], vweight=vw, vfactor=0.1 * getattr(model, 'back_bias', 0) / 0.7)
              if l < 2: P2, T2, N2, l2 = M.refine_labels(P2, T2, N2, f, h)
              else: l2 = f.labels_at(P2[T2].mean(1), h).astype(np.int32)
              sh = W.shading(f, P2, N2, h, T2) if model.shade else None
              M.add_labeled(B, P2 + lift, T2, l2, N2, model.pal, c0fn=model.weather, shade=sh)
          for (key, maker, sh, xfs, ml), (f, h, (P, T, LAB)) in zip(model.inst, hi_i):
              if l > ml: continue
              tgt = int(rest * sh / tot_share)
              tgt = max(tgt, 12 if l == 2 else 24)
              (P2, T2, l2, N2), = M.decimate(P, T, M.face_labels(T, LAB), [tgt])
              if l < 2: P2, T2, N2, l2 = M.refine_labels(P2, T2, N2, f, h)
              sh = W.shading(f, P2, N2, h, T2) if model.shade else None
              for (R, t) in xfs:
                  M.add_labeled(B, P2, T2, l2, N2, model.pal, xf=(np.asarray(R, np.float32), np.asarray(t, np.float32) + lift), c0fn=model.weather, shade=sh)
          A_ = xm.arrays()
          if A_ is not None:
              P, T, N, Lb = A_
              M.add_labeled(B, P + lift, T, Lb, N, model.pal, c0fn=model.weather)
          if B.ntri() <= model.budget[l] or attempt == 2: break
          rest -= (B.ntri() - model.budget[l]) * 1.15 + 50
      builders.append(B)
      if verbose: print(f'  {model.id} LOD{l}: {B.ntri()} tris (explicit {nx}) budget {model.budget[l]}  [{time.time()-t0:.1f}s]', flush=True)
    return builders

def export(model, builders):
    os.makedirs(OUT, exist_ok=True)
    files = []; tris = []
    for l, B in enumerate(builders):
        fn = f'{model.id}.npz' if l == 0 else f'{model.id}_lod{l}.npz'
        jk.export_npz(B, os.path.join(OUT, fn))
        files.append(fn); tris.append(B.ntri())
    M_ = builders[0].merged(('main', 'detail'))
    P = M_['P']
    info = dict(name_ja=model.name_ja, name_en=model.name_en, height_m=round(float(P[:, 2].max()), 3),
                figure_height_m=model.figure_h, pedestal_m=round(float(model.lift), 3),
                bbox=[[round(float(v), 3) for v in P.min(0)], [round(float(v), 3) for v in P.max(0)]], lods=files, tris=tris)
    if getattr(model, 'slot', None): info.update(model.slot)
    return info

def render_preview(model, B, path, wide=False):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    ob = M.to_object(B, model.id)
    P = B.merged(('main', 'detail'))['P']
    lo, hi = P.min(0), P.max(0); hgt = hi[2] - lo[2]; wid = max(hi[0] - lo[0], 0.5)
    M.setup_render(res=(900, 1200) if not wide else (1400, 1000), samples=32)
    c = (0, 0, lo[2] + hgt * 0.5)
    M.lights(center=c, dist=max(hgt, wid) * 1.6, side=1)
    # floor
    me = bpy.data.meshes.new('floor'); s = 20
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new('floor', me); bpy.context.scene.collection.objects.link(fl)
    mm = bpy.data.materials.get('pv_floor') or bpy.data.materials.new('pv_floor'); mm.use_nodes = True
    mm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.016, 0.012, 1)
    mm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.35
    me.materials.append(mm)
    d = max(hgt, wid * 1.2) * 1.55
    lens = 50
    cam = (d * 0.42, d * 0.95, lo[2] + hgt * 0.58)
    M.camera(cam, (0, 0, lo[2] + hgt * 0.47), lens, path)

def render_close(model, B, path, tgt, dist, lens=60, az=0.35, res=(800, 1000)):
    import bpy
    if model.id not in bpy.data.objects:
        for o in list(bpy.data.objects): bpy.data.objects.remove(o)
        M.to_object(B, model.id)
    M.setup_render(res=res, samples=32)
    M.lights(center=tgt, dist=max(dist, 1.0) * 1.5, side=1)
    cam = (tgt[0] + dist * math.sin(az), tgt[1] + dist * math.cos(az), tgt[2] + dist * 0.08)
    M.camera(cam, tgt, lens, path)

ORDER = ['kannon_standing_a', 'kannon_standing_b', 'kannon_standing_c', 'kannon_seated', 'fujin',
         'narayana_kengo', 'nanda_ryuo', 'magora', 'kinnara', 'karura', 'kendatsuba', 'bishaja', 'sanshi_taisho', 'manzen_shahatsu', 'manibadara',
         'bishamonten', 'daizurata_o', 'basu_sen', 'daibon_tenno', 'taishaku_tenno', 'daibenkudoku_ten', 'birurokusha', 'birubakusha', 'sasha_mawara',
         'gobu_jogo', 'konjiki_kujaku_o', 'jinmo_nyo', 'konpira', 'hibakara', 'ashura', 'ihatsura', 'sagara_ryuo', 'misshaku_kongoshi', 'raijin']

CHK_EXPOSURE = float(os.environ.get('CHK_EXPOSURE', '0.0'))
CHK_LIGHT = [float(v) for v in os.environ.get('CHK_LIGHT', '150,40,40').split(',')]

def render_check(model, B, out_path, res=(464, 670)):
    """the photo, then renders: front (framed like the photo), and model.check_views extras: 'q34' (three-quarter from
    the statue's right) and 'low' (a kneeling visitor's view from the aisle, eye ~1 m above the hall floor)"""
    import bpy
    from mathutils import Vector
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    M.to_object(B, model.id)
    P = B.merged(('main', 'detail'))['P']
    lo, hi = P.min(0), P.max(0); Ht = hi[2] - lo[2]; Wd = hi[0] - lo[0]
    M.setup_render(res=res, samples=32, exposure=CHK_EXPOSURE)
    w = bpy.context.scene.world; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.045, 0.045, 0.048, 1)
    for o in [o for o in bpy.data.objects if o.name.startswith('pvL')]: bpy.data.objects.remove(o)
    c = Vector((0, 0, lo[2] + Ht * 0.5))
    def area(name, pos, energy, col, size):
        ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = col; ld.size = size
        lo_ = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(lo_)
        lo_.location = pos; lo_.rotation_euler = (c - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    area('pvL_key', c + Vector((-1.6, 2.6, 1.6)), CHK_LIGHT[0], (1.0, 0.95, 0.88), 2.0)
    area('pvL_fill', c + Vector((2.0, 2.2, 0.2)), CHK_LIGHT[1], (0.9, 0.93, 1.0), 2.5)
    area('pvL_top', c + Vector((0.3, 0.5, 2.6)), CHK_LIGHT[2], (1.0, 0.95, 0.9), 1.5)
    asp = res[1] / res[0]
    fit = max(Ht, Wd * asp) / 0.92
    dist = (fit / 2) / math.tan(math.atan(18 / 85))
    sc = bpy.context.scene
    views = [('front', None)] + [(v, None) for v in getattr(model, 'check_views', [])]
    tmps = []
    for k, (v, _) in enumerate(views):
        if v == 'front':
            M.camera((0, dist, lo[2] + Ht * 0.5), (0, 0, lo[2] + Ht * 0.5), 85, None)
        elif v == 'q34':
            a = math.radians(45)
            M.camera((dist * math.sin(a), dist * math.cos(a), lo[2] + Ht * 0.55), (0, 0, lo[2] + Ht * 0.5), 85, None)
        elif v == 'q34l':
            a = math.radians(-45)
            M.camera((dist * math.sin(a), dist * math.cos(a), lo[2] + Ht * 0.55), (0, 0, lo[2] + Ht * 0.5), 85, None)
        elif v == 'low':
            fz = getattr(model, 'face_z', lo[2] + Ht * 0.75)
            eye = 1.0 - getattr(model, 'dais_above_floor', 0.35)
            M.camera((0.35, 1.7, eye), (0, 0, fz - 0.15), 35, None)
        elif v == 'trace':      # orthographic at the photo's scale, for an overlay with the photo
            K, CX, SOLE, Wp, Hp = model.trace
            cd = bpy.data.cameras.get('pvcam'); cd.type = 'ORTHO'; cd.ortho_scale = max(Wp, Hp) / K
            sc.render.resolution_x, sc.render.resolution_y = Wp // 2, Hp // 2
            cx = (CX - Wp / 2) / K; cz = (SOLE - Hp / 2) / K + getattr(model, 'trace_z0', model.lift)
            M.camera((cx, 6.0, cz), (cx, 0.0, cz), 50, None)
            sc.render.film_transparent = True
        tmp = out_path + f'.{v}.png'
        sc.render.filepath = tmp; bpy.ops.render.render(write_still=True); tmps.append(tmp)
        if v == 'trace':
            bpy.data.cameras.get('pvcam').type = 'PERSP'; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.film_transparent = False
    imgs = []
    if model.photo and os.path.exists(model.photo): imgs.append(model.photo)
    imgs += tmps
    loaded = []
    overlay = None
    if 'trace' in [v for v, _ in views] and model.photo:
        ti = [t for t in tmps if t.endswith('.trace.png')][0]
        a = bpy.data.images.load(model.photo); b = bpy.data.images.load(ti)
        pa = np.empty(a.size[0] * a.size[1] * 4, np.float32); a.pixels.foreach_get(pa); pa = pa.reshape(a.size[1], a.size[0], 4)
        pb = np.empty(b.size[0] * b.size[1] * 4, np.float32); b.pixels.foreach_get(pb); pb = pb.reshape(b.size[1], b.size[0], 4)
        pa = pa[::2, ::2][:pb.shape[0], :pb.shape[1]]
        ov = pa.copy(); mask = pb[..., 3:4]
        edge = np.zeros_like(mask)
        edge[1:-1, 1:-1] = (np.abs(mask[2:, 1:-1] - mask[:-2, 1:-1]) + np.abs(mask[1:-1, 2:] - mask[1:-1, :-2])) > 0.3
        lum = pb[..., :3].mean(-1, keepdims=True)
        ov[..., :3] = pa[..., :3] * (1 - 0.45 * mask) + np.array([0.95, 0.45, 0.15]) * 0.45 * mask * np.clip(lum * 4, 0.35, 1)
        ov[..., :3] = ov[..., :3] * (1 - edge) + np.array([1.0, 0.9, 0.2]) * edge
        overlay = ov
        imgs = [p for p in imgs if not p.endswith('.trace.png')]
    for pth in imgs:
        im = bpy.data.images.load(pth); wa, ha = im.size
        px = np.empty(wa * ha * 4, np.float32); im.pixels.foreach_get(px); px = px.reshape(ha, wa, 4)
        if ha != res[1]:      # resize the photo to the render height (nearest, it is only a preview)
            yi = (np.arange(res[1]) * ha / res[1]).astype(int); xi = (np.arange(int(wa * res[1] / ha)) * ha / res[1]).astype(int)
            px = px[yi][:, xi]
        loaded.append(px)
    if overlay is not None:
        ha, wa = overlay.shape[:2]
        yi = (np.arange(res[1]) * ha / res[1]).astype(int); xi = (np.arange(int(wa * res[1] / ha)) * ha / res[1]).astype(int)
        loaded.append(overlay[yi][:, xi])
    Hh = max(p.shape[0] for p in loaded); Wt = sum(p.shape[1] for p in loaded)
    out = np.zeros((Hh, Wt, 4), np.float32); out[..., 3] = 1; x = 0
    for p in loaded:
        out[Hh - p.shape[0]:, x:x + p.shape[1]] = p; x += p.shape[1]
    im = bpy.data.images.new('chk', Wt, Hh, alpha=True); im.pixels.foreach_set(out.ravel())
    im.filepath_raw = out_path; im.file_format = 'PNG'; im.save()
    for t in tmps: os.remove(t)

def statue_ids():
    from sites import statues_defs as D
    return list(D.REGISTRY.keys())

def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    from sites import statues_defs as D
    ids = [a for a in argv if not a.startswith('--')]
    if '--all' in argv or not ids: ids = list(D.REGISTRY.keys())
    os.makedirs(OUT, exist_ok=True); os.makedirs(PREV, exist_ok=True)
    idx_path = os.path.join(OUT, 'index.json')
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    lods = (0,) if '--lod0' in argv else (0, 1, 2)
    for sid in ids:
        t0 = time.time()
        model = D.REGISTRY[sid]()
        builders = build_lods(model, lods)
        if len(builders) == 3:
            info = export(model, builders)
            import fcntl
            with open(idx_path + '.lock', 'w') as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                index = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
                index[sid] = info
                index = {k: index[k] for k in sorted(index, key=lambda k: ORDER.index(k) if k in ORDER else 999)}
                tmp = idx_path + '.tmp'; json.dump(index, open(tmp, 'w'), ensure_ascii=False, indent=1); os.replace(tmp, idx_path)
                fcntl.flock(lk, fcntl.LOCK_UN)
        if '--render' in argv:
            render_preview(model, builders[0], os.path.join(PREV, f'statues_{sid}.png'))
            if '--render-lods' in argv and len(builders) == 3:
                for l in (1, 2): render_preview(model, builders[l], os.path.join(PREV, f'statues_{sid}_lod{l}.png'))
        if '--check' in argv:
            render_check(model, builders[0], os.path.join(PREV, f'statues_check_{sid}.png'))
            jk.export_npz(builders[0], os.path.join(CLOSE, f'{sid}_lod0tmp.npz'))
        if '--close' in argv:
            for (nm, tz, dist, az) in getattr(model, 'closeups', []):
                render_close(model, builders[0], os.path.join(CLOSE, f'{sid}_{nm}.png'), (0, 0, tz), dist, az=az)
        print(f'{sid}: done in {time.time()-t0:.1f}s', flush=True)

if __name__ == '__main__':
    main()
