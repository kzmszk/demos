"""Interior zones for the viewer's eye adaptation (exposure) and labels:  python interiors.py OUT.json"""
import sys, json
import numpy as np
from gen.hero import florian as F
import numpy as np

def main():
    out = []
    M, L, nb, W, flipped, a, b = F.nuove_frame()
    bays = F.florian_bays()
    x0, x1 = min(bays) * W, (max(bays) + 1) * W
    poly = [(M @ np.array([x, y, 0, 1.0]))[:2].round(2).tolist() for (x, y) in ((x0, F.Y0 - 0.2), (x1, F.Y0 - 0.2), (x1, F.Y1), (x0, F.Y1))]
    out.append({'id': 'florian', 'ja': 'カフェ・フローリアン', 'en': 'Caffè Florian', 'poly': poly, 'zmax': 6.0, 'exposure': 1.0})
    from gen.hero import basilica_int as BI
    out.append({'id': 'basilica', 'ja': 'サン・マルコ寺院', 'en': "St Mark's Basilica", 'poly': [list(p) for p in BI.interior_zone()], 'zmax': 40.0, 'exposure': 0.75})
    from gen.hero import fenice as FE
    out.append({'id': 'fenice', 'ja': 'フェニーチェ劇場', 'en': 'Teatro La Fenice', 'poly': FE.interior_zone(), 'zmax': 30.0, 'exposure': 0.85})
    out.append({'id': 'fenice', 'ja': 'フェニーチェ劇場', 'en': 'Teatro La Fenice', 'poly': FE.foyer_zone(), 'zmax': 8.0, 'exposure': 0.8})
    json.dump({'interiors': out}, open(sys.argv[1], 'w'), indent=1)

if __name__ == '__main__':
    main()
