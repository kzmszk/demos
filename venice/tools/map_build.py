"""The minimap image, drawn from the walk rasters themselves, so it shows exactly what can be walked on:
calli, campi and bridge decks (light), buildings and walls (dark), water (blue).

python map_build.py BUILD_DIR OUT_DIR [m_per_px]  ->  OUT_DIR/map.webp + map.json (world extent of the image)"""
import sys, os, glob, re, json
import numpy as np
from PIL import Image

X0, Y0, TS, RES = -3400.0, -1600.0, 200.0, 0.25
WATER = np.array([26, 39, 52], np.float32)
BUILD = np.array([58, 56, 54], np.float32)
STREET = np.array([156, 149, 137], np.float32)

def main():
    build, out = sys.argv[1], sys.argv[2]
    mpp = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    files = glob.glob(os.path.join(build, 't_*_*.walk.png'))
    ij = [tuple(map(int, re.findall(r't_(\d+)_(\d+)\.walk', f)[0])) for f in files]
    i0, i1 = min(i for i, _ in ij), max(i for i, _ in ij) + 1
    j0, j1 = min(j for _, j in ij), max(j for _, j in ij) + 1
    k = int(round(mpp / RES))                                   # raster pixels per map pixel
    S = int(TS / RES) // k                                      # map pixels per tile
    W, H = (i1 - i0) * S, (j1 - j0) * S
    walk = np.zeros((H, W), np.float32); water = np.ones((H, W), np.float32)
    for f, (i, j) in zip(files, ij):
        A = np.array(Image.open(f))
        n = (A.shape[0] // k) * k
        w = (A[:n, :n, 0] > 0).reshape(n // k, k, n // k, k).mean(axis=(1, 3))
        q = (A[:n, :n, 1] > 127).reshape(n // k, k, n // k, k).mean(axis=(1, 3))
        r0 = (j1 - 1 - j) * S; c0 = (i - i0) * S
        walk[r0:r0 + S, c0:c0 + S] = w[:S, :S]; water[r0:r0 + S, c0:c0 + S] = q[:S, :S]
    # land that is not walkable is a building or a wall; walkable wins over water (bridges)
    land = 1.0 - water
    img = WATER[None, None, :] * (1 - np.maximum(land, walk))[..., None] \
        + BUILD[None, None, :] * np.clip(land - walk, 0, 1)[..., None] + STREET[None, None, :] * walk[..., None]
    # crop to where there is anything but lagoon
    rows = np.nonzero((land + walk).max(axis=1) > 0)[0]; cols = np.nonzero((land + walk).max(axis=0) > 0)[0]
    pad = 40
    ra, rb = max(0, rows[0] - pad), min(H, rows[-1] + pad); ca, cb = max(0, cols[0] - pad), min(W, cols[-1] + pad)
    img = img[ra:rb, ca:cb]
    os.makedirs(out, exist_ok=True)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(out, 'map.webp'), quality=82, method=6)
    ext = [X0 + i0 * TS + ca * mpp, Y0 + j1 * TS - rb * mpp, X0 + i0 * TS + cb * mpp, Y0 + j1 * TS - ra * mpp]
    json.dump({'extent': [round(float(v), 2) for v in ext], 'mpp': mpp, 'size': [int(cb - ca), int(rb - ra)]}, open(os.path.join(out, 'map.json'), 'w'))
    print('map', cb - ca, 'x', rb - ra, 'px at', mpp, 'm/px; extent', [round(v) for v in ext],
          os.path.getsize(os.path.join(out, 'map.webp')) // 1024, 'KB')

if __name__ == '__main__':
    main()
