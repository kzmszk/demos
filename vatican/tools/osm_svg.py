# usage: python3 osm_svg.py out.svg x0 y0 x1 y1 [scale px/m]
import sys
from osm import *
o = OSMData()
x0, y0, x1, y1 = map(float, sys.argv[2:6]); s = float(sys.argv[6]) if len(sys.argv) > 6 else 2
W, H = (x1 - x0) * s, (y1 - y0) * s
def P(p): return f"{(p[0]-x0)*s:.1f},{(y1-p[1])*s:.1f}"
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}"><rect width="100%" height="100%" fill="#fff"/>']
def inside(pts): return any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pts)
for wid, w in o.ways.items():
    t = w.get('tags', {})
    pts = o.way_xy(wid)
    if not pts or not inside(pts): continue
    if 'building:part' in t:
        col = '#c00' if t['building:part'] == 'column' else '#06c'
        out.append(f'<polygon points="{" ".join(P(p) for p in pts)}" fill="none" stroke="{col}" stroke-width="0.6"/>')
    elif 'building' in t:
        out.append(f'<polygon points="{" ".join(P(p) for p in pts)}" fill="#eee" stroke="#000" stroke-width="1"/>')
    elif 'highway' in t or 'area:highway' in t:
        out.append(f'<polyline points="{" ".join(P(p) for p in pts)}" fill="none" stroke="#999" stroke-width="0.5"/>')
    elif t.get('natural') or t.get('leisure') or t.get('landuse'):
        out.append(f'<polyline points="{" ".join(P(p) for p in pts)}" fill="none" stroke="#3a3" stroke-width="0.5"/>')
    elif t.get('amenity') == 'fountain' or t.get('man_made'):
        out.append(f'<polygon points="{" ".join(P(p) for p in pts)}" fill="none" stroke="#f0f" stroke-width="0.8"/>')
# grid every 50 m
import math
for gx in range(int(math.ceil(x0 / 50)) * 50, int(x1) + 1, 50):
    out.append(f'<line x1="{(gx-x0)*s}" y1="0" x2="{(gx-x0)*s}" y2="{H}" stroke="#0a0" stroke-width="0.3"/><text x="{(gx-x0)*s+2}" y="12" font-size="10" fill="#0a0">{gx}</text>')
for gy in range(int(math.ceil(y0 / 50)) * 50, int(y1) + 1, 50):
    out.append(f'<line x1="0" y1="{(y1-gy)*s}" x2="{W}" y2="{(y1-gy)*s}" stroke="#0a0" stroke-width="0.3"/><text x="2" y="{(y1-gy)*s-2}" font-size="10" fill="#0a0">{gy}</text>')
out.append('</svg>')
open(sys.argv[1], 'w').write('\n'.join(out))
