"""The minimap image from the tiles' surface and walk rasters (what is street, garden, forest, water, building),
shaded by the hills:  python map_build.py BUILD_DIR OUT_DIR [m_per_px]  ->  OUT_DIR/map.webp (the core) + map_<region>.webp (the
enclaves, loaded by the viewer only when you are there) + map.json"""
import sys, os, glob, re, json
import numpy as np
from PIL import Image
from gen.frame import X0, Y0, TILE, REGIONS, region_of
from gen.materials import SID

RES = 0.5
PAL = {'none': (150, 143, 132), 'asphalt': (186, 180, 170), 'asphalt_lane': (176, 170, 160), 'sidewalk': (186, 180, 170), 'stone_sett': (196, 186, 166),
       'gravel': (200, 192, 172), 'soil': (164, 150, 124), 'grass': (110, 128, 84), 'moss': (92, 116, 72), 'forest': (64, 86, 56), 'riverbed': (48, 70, 88),
       'ballast': (120, 116, 110), 'concrete': (160, 155, 146), 'sand': (206, 198, 178), 'graves': (140, 136, 128), 'farm': (130, 124, 90), 'tactile': (180, 170, 120),
       'stone_slab': (196, 186, 166), 'wood_deck': (150, 120, 90)}
BUILD = np.array([62, 58, 56], np.float32)
WATER = np.array([46, 72, 96], np.float32)

def region_map(build, out, region, files_ij, mpp, lut):
    files, ij = zip(*files_ij)
    i0, i1 = min(i for i, _ in ij), max(i for i, _ in ij) + 1; j0, j1 = min(j for _, j in ij), max(j for _, j in ij) + 1
    k = int(round(mpp / RES)); S = int(TILE / RES) // k
    W, H = (i1 - i0) * S, (j1 - j0) * S
    img = np.zeros((H, W, 3), np.float32)
    for f, (i, j) in zip(files, ij):
        A = np.array(Image.open(f)); Sf = np.array(Image.open(f.replace('.walk.png', '.surf.png')))
        n = (A.shape[0] // k) * k
        col = lut[Sf[:n, :n] & 31]
        blk = ((A[:n, :n, 2] & 128) > 0) & ((A[:n, :n, 2] & 64) == 0)
        wat = (A[:n, :n, 2] & 64) > 0
        col = np.where(blk[..., None], BUILD, col); col = np.where(wat[..., None], WATER, col)
        c = col.reshape(n // k, k, n // k, k, 3).mean(axis=(1, 3))
        r0 = (j1 - 1 - j) * S; c0 = (i - i0) * S
        img[r0:r0 + S, c0:c0 + S] = c[:S, :S]
    # hill shading from the DEM
    d = np.load('/home/kazu/work/kyoto-assets/build/dem_core.npz'); Hm = d['H']; res = float(d['res']); hx0 = float(d['x0']); hy0 = float(d['y0'])
    xs = X0 + i0 * TILE + (np.arange(W) + 0.5) * mpp; ys = Y0 + j1 * TILE - (np.arange(H) + 0.5) * mpp
    ix = np.clip(((xs - hx0) / res).astype(int), 1, Hm.shape[1] - 2); iy = np.clip(((ys - hy0) / res).astype(int), 1, Hm.shape[0] - 2)
    Z = Hm[np.ix_(iy, ix)]
    gy, gx = np.gradient(Z, mpp)
    shade = np.clip(0.75 + (-gx * 0.6 + gy * 0.6) * 0.35, 0.45, 1.15)
    img = img * shade[..., None]
    fn = 'map.webp' if region == 'core' else f'map_{region}.webp'
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(out, fn), quality=80, method=6)
    ext = [X0 + i0 * TILE, Y0 + j0 * TILE, X0 + i1 * TILE, Y0 + j1 * TILE]
    print('map', region, W, 'x', H, os.path.getsize(os.path.join(out, fn)) // 1024, 'KB', flush=True)
    return {'name': region, 'file': fn, 'extent': ext, 'size': [W, H]}

def main():
    build, out = sys.argv[1], sys.argv[2]
    mpp = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    lut = np.zeros((32, 3), np.float32)
    for n, c in PAL.items(): lut[SID[n]] = c
    by = {}
    for f in glob.glob(os.path.join(build, 't_*_*.walk.png')):
        i, j = map(int, re.findall(r't_(-?\d+)_(-?\d+)\.walk', f)[0])
        r = region_of(i, j)
        if r: by.setdefault(r, []).append((f, (i, j)))
    os.makedirs(out, exist_ok=True)
    regs = [region_map(build, out, r, by[r], mpp, lut) for r in REGIONS if r in by]
    core = next(r for r in regs if r['name'] == 'core')
    # top level = the core (as before); the enclaves listed with their own images
    json.dump({'extent': core['extent'], 'mpp': mpp, 'size': core['size'], 'regions': regs}, open(os.path.join(out, 'map.json'), 'w'))

if __name__ == '__main__':
    main()
