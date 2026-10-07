"""Split the files in public/ that are too big for the static host (Cloudflare: 25 MiB per asset) into parts
<name>.0, <name>.1, ... and list them in <dir>/split.json ({name: parts}); the viewer joins them (main.js loadKTX).
The originals stay in the build folders (kyoto-assets/build/tex1k).   python split_big.py [../public/tex]"""
import os, sys, json, math
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public', 'tex')
LIMIT, PART = 24 << 20, 16 << 20
sp_path = os.path.join(D, 'split.json')
sp = json.load(open(sp_path)) if os.path.exists(sp_path) else {}
for f in sorted(os.listdir(D)):
    p = os.path.join(D, f)
    if not os.path.isfile(p) or os.path.getsize(p) <= LIMIT or '.' not in f or f.rsplit('.', 1)[1].isdigit(): continue
    b = open(p, 'rb').read(); n = math.ceil(len(b) / PART)
    for k in range(n): open(f'{p}.{k}', 'wb').write(b[k * PART:(k + 1) * PART])
    os.remove(p); sp[f] = n; print(f, len(b), '->', n, 'parts')
json.dump(sp, open(sp_path, 'w'), indent=1)
