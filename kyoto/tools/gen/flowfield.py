"""The rivers' flow (venv python):  python -m gen.flowfield [OUT.npz]
OSM waterways are drawn downstream, so each line gives its water's direction.  Points every 2 m along every river,
canal, stream and ditch (not in tunnels): P (x, y), D (unit direction), S (speed, m/s; by kind and by name).
pack.py gives every water vertex the flow of the nearest point (c0: direction, speed); the shader moves the ripples."""
import sys, os
import numpy as np
from . import world as W

OUT = '/home/kazu/work/kyoto-assets/build/flow.npz'
KIND = {'river': 0.8, 'stream': 0.9, 'canal': 0.55, 'ditch': 0.4, 'drain': 0.4}
NAME = {'鴨川': 0.9, '高野川': 1.0, '白川': 1.0, '高瀬川': 0.35, '東高瀬川': 0.35, '琵琶湖疏水': 0.6, '疏水分線': 0.6, '桂川': 0.7, '大堰川': 0.7, '保津川': 0.9}

def build(out=OUT):
    w = W.load()
    P, D, S = [], [], []
    for f in w.osm['waterways']:
        if f['tunnel'] or f['ww'] not in KIND: continue
        sp = NAME.get(f['name'] or f['tags'].get('name'), KIND[f['ww']])
        c = np.asarray(f['line'].coords, np.float64)[:, :2]
        for a, b in zip(c[:-1], c[1:]):
            d = b - a; L = float(np.hypot(*d))
            if L < 1e-3: continue
            k = max(1, int(L / 2.0))
            t = (np.arange(k) + 0.5) / k
            P.append(a + d * t[:, None]); D.append(np.repeat((d / L)[None], k, 0)); S.append(np.full(k, sp))
    P = np.concatenate(P).astype(np.float32); D = np.concatenate(D).astype(np.float32); S = np.concatenate(S).astype(np.float32)
    np.savez_compressed(out, P=P, D=D, S=S)
    print(out, len(P), 'points')

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else OUT)
