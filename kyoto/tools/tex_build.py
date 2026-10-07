"""Build the city texture arrays (venv python):  python tex_build.py OUT_DIR [--size 2048] [--ktx]
Per layer (materials.LAYERS): albedo RGBA (sRGB; A = tint mask: 1 = tint/paint this pixel), normal RGB
(OpenGL, +Y up), ORM RGBA (R = AO, G = roughness, B = metalness, A = height).  With --ktx the layers are packed into KTX2 array textures
(UASTC + zstd) city_albedo_<size>.ktx2, city_normal_<size>.ktx2, city_orm_<size>.ktx2."""
import os, sys, json, math, subprocess, argparse
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from gen.materials import LAYERS

TEX = '/home/kazu/work/kyoto-assets/textures'
KTX = '/home/kazu/work/venice-assets/tools/KTX-Software-4.4.2-Linux-x86_64/bin/ktx'

def rd(path, size, gray=False):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None: raise FileNotFoundError(path)
    if im.dtype == np.uint16: im = (im / 257).astype(np.uint8)
    if gray:
        if im.ndim == 3: im = im[:, :, 0] if im.shape[2] in (3, 4) else im
    else:
        if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        im = im[:, :, :3][:, :, ::-1]
    return cv2.resize(im, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def load_set(src, size):
    m = json.load(open(os.path.join(TEX, 'manifest.json')))[src]['maps']
    g = lambda k: os.path.join(TEX, m[k]) if k in m else None
    alb = rd(g('diff'), size)
    nor = rd(g('nor'), size) if g('nor') else np.dstack([np.full((size, size), .5), np.full((size, size), .5), np.ones((size, size))])
    rough = rd(g('rough'), size, gray=True) if g('rough') else np.full((size, size), 0.8, np.float32)
    ao = rd(g('ao'), size, gray=True) if g('ao') else None
    if ao is None and g('arm'): ao = rd(g('arm'), size)[:, :, 0]
    if ao is None: ao = np.ones((size, size), np.float32)
    disp = rd(g('disp'), size, gray=True) if g('disp') else np.full((size, size), 0.5, np.float32)
    metal = rd(g('metal'), size, gray=True) if g('metal') else np.zeros((size, size), np.float32)
    return alb, nor, rough, ao, disp, metal

def neutralize(alb, mask=None):
    """make a colour texture neutral (white-ish) so it can be tinted; keeps luminance variation."""
    lin = s2l(alb)
    sel = mask > 0.5 if mask is not None else np.ones(lin.shape[:2], bool)
    mean = lin[sel].mean(axis=0) if sel.any() else lin.reshape(-1, 3).mean(0)
    lum = (lin @ np.array([0.2126, 0.7152, 0.0722])) / max(1e-4, float(mean @ np.array([0.2126, 0.7152, 0.0722])))
    neutral = np.clip(lum[..., None] * 0.80, 0, 1) * np.ones(3)
    out = lin.copy()
    out[sel] = neutral[sel]
    return l2s(out)

def plaster_mask(alb):
    """1 where the pixel is plaster/paint (light, unsaturated), 0 where it is brick/stone underneath."""
    hsv = cv2.cvtColor((alb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    s = hsv[..., 1] / 255; v = hsv[..., 2] / 255; h = hsv[..., 0] * 2
    vb = cv2.GaussianBlur(v, (0, 0), 3.0)
    paint = np.clip((vb - 0.60) / 0.10, 0, 1)
    brick = ((h < 30) | (h > 330)) & (s > 0.25)
    paint[brick] = 0
    return cv2.GaussianBlur(paint.astype(np.float32), (0, 0), 1.0)

def paint_mask(alb, hue_lo, hue_hi):
    hsv = cv2.cvtColor((alb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[..., 0] * 2; s = hsv[..., 1] / 255
    m = ((h > hue_lo) & (h < hue_hi) & (s > 0.12)).astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), 1.0)

def wblur(a, sigma):
    p = int(math.ceil(sigma * 4)) + 1
    b = cv2.GaussianBlur(np.pad(a, ((p, p), (p, p)) + ((0, 0),) * (a.ndim - 2), mode='wrap'), (0, 0), sigma)
    return b[p:-p, p:-p]

def height_to_normal(hgt, scale):
    hp = np.pad(hgt, 2, mode='wrap')
    gx = cv2.Sobel(hp, cv2.CV_32F, 1, 0, ksize=3)[2:-2, 2:-2]
    gy = cv2.Sobel(hp, cv2.CV_32F, 0, 1, ksize=3)[2:-2, 2:-2]
    n = np.dstack([-gx * scale, gy * scale, np.ones_like(hgt)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5

def wrap_noise(size, cells, seed, octaves=4):
    rng = np.random.default_rng(seed); acc = np.zeros((size, size), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        c = cells * 2 ** o
        g = rng.random((c, c)).astype(np.float32)
        g = np.pad(g, ((0, 1), (0, 1)), mode='wrap')
        up = cv2.resize(g, (size + size // c, size + size // c), interpolation=cv2.INTER_CUBIC)[:size, :size]
        acc += up * amp; tot += amp; amp *= 0.5
    return acc / tot

def masegni(size, seed=7, metres=3.0):
    """Venetian trachyte paving: rows across the street, staggered slabs, worn bevels, dark joints."""
    rng = np.random.default_rng(seed)
    px = size / metres
    # rows (v): heights 0.30-0.45 m summing to `metres`
    rows = []
    while True:
        h = rng.uniform(0.30, 0.46)
        if sum(rows) + h > metres - 0.28: rows.append(metres - sum(rows)); break
        rows.append(h)
    slab_id = np.zeros((size, size), np.int32); dist = np.full((size, size), 1e9, np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    sid = 0; slabs = []
    v0 = 0.0
    for rh in rows:
        y0 = int(round(v0 * px)); y1 = int(round((v0 + rh) * px))
        off = rng.uniform(0, metres)
        lens = []
        while True:
            l = rng.uniform(0.42, 0.95)
            if sum(lens) + l > metres - 0.38: lens.append(metres - sum(lens)); break
            lens.append(l)
        u = off
        for l in lens:
            x0 = u; x1 = u + l
            for sh in (-metres, 0.0, metres):
                a = int(round((x0 + sh) * px)); b = int(round((x1 + sh) * px))
                aa, bb = max(a, 0), min(b, size)
                if aa >= bb: continue
                slab_id[y0:y1, aa:bb] = sid
                # distance to slab edge in pixels
                X = xx[y0:y1, aa:bb]; Y = yy[y0:y1, aa:bb]
                d = np.minimum(np.minimum(X - a, b - 1 - X), np.minimum(Y - y0, y1 - 1 - Y))
                dist[y0:y1, aa:bb] = d
            slabs.append(dict(l=rng.uniform(-1, 1), t=(rng.uniform(-1, 1), rng.uniform(-1, 1)), w=rng.random()))
            sid += 1
            u += l
        v0 += rh
    nsl = len(slabs)
    L = np.array([s['l'] for s in slabs], np.float32); TX = np.array([s['t'][0] for s in slabs], np.float32); TY = np.array([s['t'][1] for s in slabs], np.float32); WR = np.array([s['w'] for s in slabs], np.float32)
    grain = wrap_noise(size, 64, seed + 1, 4)
    fine = wrap_noise(size, 256, seed + 2, 3)
    big = wrap_noise(size, 6, seed + 3, 3)
    joint_px = 0.006 * px
    bevel_px = 0.022 * px
    d = dist
    edge = np.clip((d - joint_px) / bevel_px, 0, 1)
    bev = np.sin(edge * math.pi / 2) ** 0.7
    tilt = (TX[slab_id] * (xx / size) + TY[slab_id] * (yy / size)) * 0.15
    chis = (fine - 0.5) * 0.35 + (grain - 0.5) * 0.25
    hgt = np.where(d < joint_px, 0.05 + fine * 0.05, 0.35 + 0.55 * bev + chis * bev * 0.6 + tilt * 0.2)
    hgt = wblur(hgt.astype(np.float32), 0.6)
    # colour: trachyte grey with per-slab variation, joints dark, wear lighter near the middle of slabs
    base = np.array([0.125, 0.12, 0.112])           # linear (Euganean trachyte, worn)
    lv = 1.0 + L[slab_id] * 0.22 + (big - 0.5) * 0.35
    warm = (WR[slab_id] - 0.5) * 0.04
    col = base[None, None, :] * lv[..., None]
    col[..., 0] *= (1 + warm); col[..., 2] *= (1 - warm)
    col *= (0.82 + 0.36 * grain[..., None]) * (0.92 + 0.16 * fine[..., None])
    jt = d < joint_px * 1.3
    col[jt] = col[jt] * 0.7 + np.array([0.045, 0.042, 0.037]) * 0.3
    alb = l2s(col)
    rough = np.clip(0.86 - 0.18 * (bev * (big > 0.55)) + (fine - 0.5) * 0.08, 0.45, 0.95)
    rough[jt] = 0.95
    ao = np.clip(0.55 + 0.45 * np.clip(hgt * 1.6, 0, 1), 0, 1)
    nor = height_to_normal(hgt, scale=size / 2048 * 4.5)
    return alb.astype(np.float32), nor.astype(np.float32), rough.astype(np.float32), ao.astype(np.float32), hgt.astype(np.float32), np.zeros_like(rough)

def save(path, arr):
    a = np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8)
    if a.ndim == 3: a = a[:, :, ::-1] if a.shape[2] == 3 else a[:, :, [2, 1, 0, 3]]
    cv2.imwrite(path, a)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--size', type=int, default=2048); ap.add_argument('--ktx', action='store_true')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); S = a.size
    files = {'albedo': [], 'normal': [], 'orm': []}
    for li, (name, src, sz, fl) in enumerate(LAYERS):
        alb, nor, rough, ao, disp, metal = load_set(src, S)
        mask = np.zeros(alb.shape[:2], np.float32)
        if fl.get('neutral'):
            mask = np.ones(alb.shape[:2], np.float32); alb = neutralize(alb)
        if fl.get('neutral_mask'):
            mask = plaster_mask(alb); alb = neutralize(alb, mask)
        A = np.dstack([alb, mask]); O = np.dstack([ao, rough, metal, disp])
        for k, arr in (('albedo', A), ('normal', nor), ('orm', O)):
            p = os.path.join(a.out, f'{k}_{li:02d}_{name}.png'); save(p, arr); files[k].append(p)
        print('layer', li, name, alb.shape, 'mask mean', round(float(mask.mean()), 3), flush=True)
    if a.ktx:
        for k, fs in files.items():
            fmt = 'R8G8B8A8_SRGB' if k == 'albedo' else 'R8G8B8A8_UNORM'
            out = os.path.join(a.out, f'city_{k}_{S}.ktx2')
            cmd = [KTX, 'create', '--format', fmt, '--layers', str(len(fs)), '--generate-mipmap', '--encode', 'uastc', '--uastc-quality', '2',
                   '--uastc-rdo', '--uastc-rdo-l', '1.0' if k != 'normal' else '0.5', '--zstd', '15'] + (['--assign-tf', 'linear'] if k != 'albedo' else []) + fs + [out]
            print(' '.join(cmd[:14]), '...', flush=True)
            subprocess.run(cmd, check=True)
            print(out, os.path.getsize(out) // 1024, 'KB', flush=True)

if __name__ == '__main__':
    main()
