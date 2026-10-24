"""ASSETS/build/roof.npz -> PUBLIC/data/roof.bin (gzip): int16 top-of-building heights (0.1 m, -32768 = none) on the
4 m grid, with a small JSON header.  The viewer uses it for collisions, landing rings and the updrafts along walls."""
import os, json, gzip, struct
import numpy as np
from .frame import ASSETS, PUBLIC

if __name__ == '__main__':
    d = np.load(os.path.join(ASSETS, 'build', 'roof.npz'))
    R = d['roof']; q = np.where(R > -999, np.clip(np.round(R * 10), -32767, 32767), -32768).astype(np.int16)
    head = json.dumps(dict(x0=float(d['x0']), y0=float(d['y0']), res=float(d['res']), w=int(R.shape[1]), h=int(R.shape[0]))).encode()
    with gzip.open(os.path.join(PUBLIC, 'data', 'roof.bin'), 'wb') as f: f.write(struct.pack('<I', len(head)) + head + q.tobytes())
    print('roof.bin', R.shape, os.path.getsize(os.path.join(PUBLIC, 'data', 'roof.bin')))
