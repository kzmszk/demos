"""prop templates -> raw streams for pack.mjs (one 'tile-like' record per template):  python pack_templates.py BUILD STAGE"""
import sys, os, json
import numpy as np
build, stage = sys.argv[1], sys.argv[2]
os.makedirs(stage, exist_ok=True)
t = np.load(os.path.join(build, 'templates.npz'))
names = list(t['names'])
bufs = []; off = 0; hdr = {'name': 'props', 'templates': []}
def add(rec, name, arr, stride, kind='v'):
    global off
    a = np.ascontiguousarray(arr); by = a.tobytes()
    rec['streams'].append({'name': name, 'off': off, 'len': len(by), 'stride': stride, 'count': int(len(a)) if kind == 'v' else int(a.size), 'kind': kind})
    bufs.append(by); off += len(by)
for k, n in enumerate(names):
    P = t[f'P{k}']; rec = {'name': str(n), 'streams': [], 'nv': int(len(P))}
    add(rec, 'pos', P.astype('<f4'), 12)
    N = t[f'N{k}']; nn = np.zeros((len(P), 4), np.int8); nn[:, :3] = np.round(np.clip(N, -1, 1) * 127); nn[:, 3] = 127
    add(rec, 'nrm', nn, 4)
    T = t[f'T{k}']; tt = np.zeros((len(P), 4), np.int8); tt[:, :3] = np.round(np.clip(T[:, :3], -1, 1) * 127); tt[:, 3] = np.where(T[:, 3] < 0, -127, 127)
    add(rec, 'tan', tt, 4)
    add(rec, 'uv', t[f'UV{k}'].astype('<f4'), 8)
    add(rec, 'c0', t[f'C0{k}'].astype(np.uint8), 4)
    c1 = t[f'C1{k}'].astype(np.uint8); cc = np.zeros_like(c1); cc[:, 0] = t[f'MAT{k}']; cc[:, 1] = c1[:, 0]; cc[:, 2] = c1[:, 2]; cc[:, 3] = c1[:, 3]
    add(rec, 'c1', cc, 4)
    add(rec, 'idx', t[f'I{k}'].astype('<u4').ravel(), 4, kind='i')
    hdr['templates'].append(rec)
open(os.path.join(stage, 'props.raw'), 'wb').write(b''.join(bufs))
json.dump(hdr, open(os.path.join(stage, 'props.tpl.json'), 'w'))
print('templates', names, off // 1024, 'KB')
