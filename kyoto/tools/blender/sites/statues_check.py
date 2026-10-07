"""re-render a check image from a saved LOD0 npz:  blender -b --python statues_check.py -- <id> <npz> [photo]"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
if ROOT not in sys.path: sys.path.insert(0, ROOT)
import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
import jk
from sites import statues_build as SB, statues_guardians as Gu
argv = sys.argv[sys.argv.index('--') + 1:]
sid, npz = argv[0], argv[1]
D = np.load(npz)
from jk.core import mats
id2 = {m['id']: n for n, m in mats().items()}
B = jk.Builder(sid)
I = D['I'].astype(np.int64); MATN = np.array([id2[k] for k in D['MAT']])
for n in set(MATN.tolist()):
    sel = np.nonzero(MATN[I[:, 0]] == n)[0]
    T = I[sel]; used = np.unique(T); remap = np.full(len(D['P']), -1); remap[used] = np.arange(len(used))
    B.add(D['P'][used], remap[T], n, N=D['N'][used], c0=D['C0'][used])
class Mo: pass
m = Mo(); m.id = sid
m.photo = argv[2] if len(argv) > 2 else (Gu.PHOTO.format(Gu.PHOTO_NO.index(sid) + 1) if sid in Gu.PHOTO_NO else None)
SB.render_check(m, B, os.path.join(SB.PREV, f'statues_check_{sid}.png'))
