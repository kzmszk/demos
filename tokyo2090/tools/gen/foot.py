"""Walking data: where the buildings stand, at 1 m, and the rubble mounds at their feet.
  python -m gen.foot [N]   -> PUBLIC/data/foot.bin (gzip: 4-byte header length, JSON header, packed bits row-major,
                              row 0 = y0, bit order big-endian per byte as numpy.packbits), PUBLIC/data/rubble.json

The roof raster (4 m) is good enough for a glider but not for someone walking along a facade: a wall can sit up to a
cell inside an empty cell. This re-runs the same deterministic decay as gen.city (no tiles are written) and draws the
xy shadow of every roof and broken-floor cap of every building into a 1 m mask, so the footprint of what still stands
is exact to a metre. The mounds of fallen floors (roof_furniture) are listed as cones: [x, y, z base, radius, height]."""
import os, sys, json, gzip, pickle, glob, struct, time
import numpy as np
from PIL import Image, ImageDraw
from .frame import ASSETS, PUBLIC, X0, Y0, X1, Y1, NTX, NTY, tile_of
from .city import decay, roof_furniture, tag_landmarks, seed_of

RES = 1.0


def one(args):
    bl, tags = args
    polys, mounds = [], []
    for b in bl:
        rng = np.random.default_rng(seed_of(b['id']) ^ 0x5bd1e995)
        V, F, kind, zcut = decay(b, tags.get(b['id'], 0))
        if len(F) == 0: continue
        H = b['z1'] - b['z0']
        extra = roof_furniture(b, V, F, kind, zcut, rng, tags.get(b['id'], 0))
        for t in F[(kind == 1) | (kind == 2)]: polys.append(V[t][:, :2].astype(np.float32))
        if extra is not None and zcut is not None and H > 20:
            Ve = extra[0]; m = Ve[-21:]                     # the mound is the last thing roof_furniture adds: apex + 10 x (outer, inner)
            apex = m[0]; outer = m[1::2]
            R = float(np.mean(np.hypot(outer[:, 0] - apex[0], outer[:, 1] - apex[1])))
            mounds.append([round(float(apex[0]), 1), round(float(apex[1]), 1), round(float(outer[:, 2].mean()), 2), round(R, 1), round(float(apex[2] - outer[:, 2].mean()), 2)])
    return polys, mounds


def hero_mask(a, W, H):
    hj = os.path.join(PUBLIC, 'data', 'heroes.json')
    if not os.path.exists(hj): return a
    from .hero_src import ground_grid, ground_at
    r, gh = ground_grid()
    for d in json.load(open(hj)):
        raw = gzip.open(os.path.join(PUBLIC, 'hero', d['name'], 'field.bin')).read()
        n = struct.unpack('<I', raw[:4])[0]; hd = json.loads(raw[4:4 + n])
        q = np.frombuffer(raw[4 + n:], np.int16).reshape(hd['h'], hd['w'])
        X, Y = np.meshgrid(hd['x0'] + (np.arange(hd['w']) + 0.5) * hd['res'], hd['y0'] + (np.arange(hd['h']) + 0.5) * hd['res'])
        up = (q != -32768) & (q / 10.0 > ground_at(r, gh, X, Y) + 1.0)
        # 0.5 m -> the 1 m mask: a metre is solid when any of its four cells is
        k = int(round(RES / hd['res']))
        up = up[:hd['h'] // k * k, :hd['w'] // k * k].reshape(hd['h'] // k, k, hd['w'] // k, k).any(axis=(1, 3))
        i0 = int(round((hd['x0'] - X0) / RES)); j0 = int(round((hd['y0'] - Y0) / RES))
        sub = a[j0:j0 + up.shape[0], i0:i0 + up.shape[1]]
        sub |= up[:sub.shape[0], :sub.shape[1]].astype(a.dtype)
        print('hero mask', d['name'], int(up.sum()), 'm2')
    return a


def main(nproc=8):
    from multiprocessing import Pool
    bs = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'cache', 'plateau', '*.pkl'))): bs += pickle.load(open(f, 'rb'))
    tags = tag_landmarks(bs)
    from .hero_ids import excluded
    ex = excluded()
    tiles = {}
    for b in bs:
        if b['id'] in ex: continue
        i, j = tile_of(b['cx'], b['cy'])
        if 0 <= i < NTX and 0 <= j < NTY: tiles.setdefault((i, j), []).append(b)
    W = int((X1 - X0) / RES); H = int((Y1 - Y0) / RES)
    im = Image.new('1', (W, H), 0); dr = ImageDraw.Draw(im)
    mounds = []; t0 = time.time(); n = 0
    with Pool(nproc) as pool:
        for k, (polys, mm) in enumerate(pool.imap_unordered(one, [(bl, tags) for _, bl in sorted(tiles.items())], chunksize=4)):
            for p in polys:
                dr.polygon([((x - X0) / RES, (y - Y0) / RES) for x, y in p], fill=1)
            n += len(polys); mounds += mm
            if k % 100 == 0: print(k, 'tiles', n, 'polys', round(time.time() - t0), 's', flush=True)
    a = np.asarray(im, dtype=np.uint8)
    # close the 1-pixel seams between buildings that touch (a walker could slip into them): dilate, then erode, 3 x 3
    def shift_or(m, op):
        out = m.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy: out = op(out, np.roll(np.roll(m, dy, 0), dx, 1))
        return out
    a = shift_or(shift_or(a, np.maximum), np.minimum)
    # then grow it by a pixel: a pixel is set when its centre is inside, so up to ~0.7 m of a slanted wall can lie in an
    # empty pixel; grown, every wall is inside the mask and the walker's eye never ends up in a facade
    a = shift_or(a, np.maximum)
    # the hand-built districts: wherever their collision field stands more than a metre above the ground (gen.hero_collide)
    a = hero_mask(a, W, H)
    print('foot mask', a.shape, 'covered', float(a.mean()), 'mounds', len(mounds), flush=True)
    bits = np.packbits(a, axis=1)                       # rows of ceil(W / 8) bytes
    head = json.dumps(dict(x0=X0, y0=Y0, res=RES, w=W, h=H, stride=int(bits.shape[1]))).encode()
    with gzip.open(os.path.join(PUBLIC, 'data', 'foot.bin'), 'wb', compresslevel=9) as f: f.write(struct.pack('<I', len(head)) + head + bits.tobytes())
    json.dump(mounds, open(os.path.join(PUBLIC, 'data', 'rubble.json'), 'w'), separators=(',', ':'))
    print('foot.bin', os.path.getsize(os.path.join(PUBLIC, 'data', 'foot.bin')), 'rubble.json', len(mounds), round(time.time() - t0), 's')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
