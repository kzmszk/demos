"""The railways above ground (OSM, each track mapped on its own), for the viewer to draw: ballast, sleepers, rails,
viaduct decks where the line is on a bridge, catenary masts, and a few trains left where they stopped in 2030.
  python -m gen.rails     -> PUBLIC/data/rails.json

tracks: [{l: line index (-1 unnamed), k: 0 rail / 1 light rail / 2 monorail, e: electrified, p: [x, y, bz, ...]}]
        bz = -999 where the track lies on the ground (the viewer drapes it on its terrain), else the rail height (T.P.)
        of the bridge deck, interpolated between where the bridge leaves the ground.
lines:  [[name shown, colour of the trains' band, osm name]]
labels: [[line index, x, y]]  every ~700 m along the line
trains: [[line index, track index, s (m along the track), cars]]"""
import os, json, math
import numpy as np
from shapely.geometry import box, LineString, Point
from .frame import PUBLIC, X0, Y0, X1, Y1
from .dem import Terrain
from . import osm

LINES = [   # osm name -> name shown, train band colour (faded), train body (0 silver, 1 painted)
    ('山手線', 'JR山手線', '#8fbf3a'), ('山手貨物線', 'JR埼京線・湘南新宿ライン', '#2e9c7c'), ('中央緩行線', 'JR中央・総武線', '#e3c22a'),
    ('中央・総武緩行線', 'JR中央・総武線', '#e3c22a'), ('中央本線', 'JR中央線快速', '#e2672a'), ('JR中央線', 'JR中央線快速', '#e2672a'),
    ('小田急小田原線', '小田急線', '#2f64b8'), ('京王電鉄井の頭線', '京王井の頭線', '#b85a8c'), ('東急東横線', '東急東横線', '#c43a4a'),
    ('京浜東北線', 'JR京浜東北線', '#3ea8d8'), ('東海道本線', 'JR東海道線', '#e0782f'), ('東海道新幹線', '東海道新幹線', '#2b55a8'),
    ('西武新宿線', '西武新宿線', '#d9a326'), ('東京メトロ銀座線', '東京メトロ銀座線', '#e89a2a'), ('京王電鉄京王線', '京王線', '#b84a6a'),
    ('京王電鉄京王線 (Keio Railway Keio Line)', '京王線', '#b84a6a'), ('京王新線', '京王新線', '#b84a6a'), ('東京モノレール', '東京モノレール', '#2b6cb0'),
    ('東京メトロ日比谷線', '東京メトロ日比谷線', '#9aa3ab'), ('東京メトロ千代田線', '東京メトロ千代田線', '#2e9a5a'),
    ('東京メトロ千代田線 (Tokyo Metro Chiyoda Line)', '東京メトロ千代田線', '#2e9a5a'), ('東京メトロ丸ノ内線', '東京メトロ丸ノ内線', '#c8323a'),
    ('JR埼京線', 'JR埼京線・湘南新宿ライン', '#2e9c7c'),
]
# trains left on the line: (osm line name, near x, y, cars)
TRAINS = [('山手線', 230, 1500, 11), ('山手線', 160, 2300, 11), ('山手線', 330, -700, 11), ('山手貨物線', 120, 2000, 10), ('中央緩行線', 1500, 2330, 10),
          ('中央本線', 2300, 2650, 10), ('小田急小田原線', -560, 2050, 10), ('京王電鉄井の頭線', -900, -200, 5), ('山手線', 560, -1100, 11),
          ('東京メトロ銀座線', 230, -40, 6)]
RES = 4.0


def main():
    o = osm.load(); T = Terrain(); B = box(X0 - 200, Y0 - 200, X1 + 200, Y1 + 200)
    names = {}; lines = []
    for osmname, shown, col in LINES:
        if shown not in names: names[shown] = len(lines); lines.append([shown, col])
    line_of = {osmname: names[shown] for osmname, shown, col in LINES}
    ways = []
    for r in o['rails']:
        if r['tunnel'] or r['layer'] < 0: continue
        if r['rw'] not in ('rail', 'light_rail', 'subway', 'monorail', 'narrow_gauge'): continue
        g = r['line'].intersection(B)
        if g.is_empty: continue
        for part in (g.geoms if hasattr(g, 'geoms') else [g]):
            if part.geom_type != 'LineString' or part.length < 2: continue
            ways.append(dict(xy=np.asarray(part.coords), bridge=r['bridge'], layer=r['layer'], name=r['tags'].get('name'),
                             k=1 if r['rw'] == 'light_rail' else 2 if r['rw'] == 'monorail' else 0, e=r['tags'].get('electrified') == 'contact_line' or r['rw'] == 'rail'))
    # bridge heights: the ends of every bridge way that touch a way on the ground sit on the ground; the rest of a chain of
    # bridge ways is relaxed between those ends (a viaduct runs straight between where it leaves and rejoins the ground)
    key = lambda p: (round(p[0], 1), round(p[1], 1))
    ground_nodes = set()
    for w in ways:
        if not w['bridge']: ground_nodes.add(key(w['xy'][0])); ground_nodes.add(key(w['xy'][-1]))
    z = {}; nb = {}
    for w in ways:
        if not w['bridge']: continue
        a, b = key(w['xy'][0]), key(w['xy'][-1]); L = LineString(w['xy']).length
        for n in (a, b):
            if n in ground_nodes: z[n] = (float(T(*n)) + 0.0, True)
            elif n not in z: z[n] = (float(T(*n)) + 6.0 * max(1, w['layer']), False)
        nb.setdefault(a, []).append((b, L)); nb.setdefault(b, []).append((a, L))
    for _ in range(300):
        for n, lst in nb.items():
            if z[n][1] or len(lst) < 2: continue
            wsum = sum(1 / max(L, 1) for _, L in lst); z[n] = (sum(z[m][0] / max(L, 1) for m, L in lst) / wsum, False)
    tracks = []
    for w in ways:
        xy = w['xy']
        # resample at RES m
        seg = np.hypot(*np.diff(xy, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]); L = s[-1]
        n = max(2, int(math.ceil(L / RES)) + 1); ss = np.linspace(0, L, n)
        px = np.interp(ss, s, xy[:, 0]); py = np.interp(ss, s, xy[:, 1])
        if w['bridge']:
            za, zb = z[key(xy[0])][0], z[key(xy[-1])][0]
            bz = za + (zb - za) * ss / max(L, 1e-6)
            g = T(px, py); bz = np.maximum(bz, g + 0.0)
            # a bridge that barely leaves the ground is drawn on the ground
            if (bz - g).max() < 1.2: bz = np.full(n, -999.0)
        else:
            bz = np.full(n, -999.0)
        # drop samples that a straight line between their neighbours describes to 3 cm (z handled by the viewer for ground)
        keep = [0]
        for i in range(1, n - 1):
            a = keep[-1]; c = i + 1
            t = (ss[i] - ss[a]) / (ss[c] - ss[a])
            ex = px[a] + (px[c] - px[a]) * t - px[i]; ey = py[a] + (py[c] - py[a]) * t - py[i]
            ez = 0 if bz[i] < -900 else bz[a] + (bz[c] - bz[a]) * t - bz[i]
            if math.hypot(ex, ey) > 0.03 or abs(ez) > 0.03 or bz[i] < -900 or ss[i] - ss[a] >= 24: keep.append(i)
        keep.append(n - 1)
        p = []
        for i in keep: p += [round(float(px[i]), 2), round(float(py[i]), 2), round(float(bz[i]), 2)]
        tracks.append(dict(l=line_of.get(w['name'], -1), k=w['k'], e=bool(w['e']), p=p))
    # line labels every ~700 m along the longest track of each line
    labels = []
    for li, (shown, col) in enumerate(lines):
        tr = [t for t in tracks if t['l'] == li]
        if not tr: continue
        placed = []
        for t in sorted(tr, key=lambda t: -len(t['p'])):
            P = np.asarray(t['p']).reshape(-1, 3)[:, :2]
            seg = np.hypot(*np.diff(P, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
            for d in np.arange(200, s[-1], 350):
                x = float(np.interp(d, s, P[:, 0])); y = float(np.interp(d, s, P[:, 1]))
                if not (X0 < x < X1 and Y0 < y < Y1): continue
                if any(math.hypot(x - a, y - b) < 700 for a, b in placed): continue
                placed.append((x, y)); labels.append([li, round(x, 1), round(y, 1)])
    # trains: on the nearest track of their line to the given point
    trains = []
    for osmname, x, y, cars in TRAINS:
        li = line_of.get(osmname)
        best = None
        for ti, t in enumerate(tracks):
            if t['l'] != li: continue
            P = np.asarray(t['p']).reshape(-1, 3)[:, :2]
            ls = LineString(P); d = ls.distance(Point(x, y))
            if ls.length > cars * 20.5 + 10 and (best is None or d < best[0]): best = (d, ti, ls.project(Point(x, y)), ls.length)
        if best and best[0] < 400:
            s0 = float(np.clip(best[2] - cars * 10.25, 2, best[3] - cars * 20.5 - 2))
            trains.append([li, best[1], round(s0, 1), cars])
        else: print('no track for train', osmname, x, y)
    # platforms (railway=platform areas above ground): outlines for the viewer to raise a metre off the ground
    plats = []
    for a in o['areas']:
        if a['kind'] != 'platform' or a['tags'].get('layer', '0').lstrip('-').isdigit() and int(a['tags'].get('layer', '0')) < 0: continue
        if a['tags'].get('location') == 'underground' or a['tags'].get('tunnel') == 'yes' or a['tags'].get('level', '0').startswith('-'): continue
        p_ = a['poly']
        if not p_.intersects(B) or p_.area < 30 or p_.area > 20000: continue
        ring = np.asarray(p_.exterior.simplify(0.3).coords)[:-1]
        plats.append(np.round(ring, 2).ravel().tolist())
    json.dump(dict(lines=lines, tracks=tracks, labels=labels, trains=trains, platforms=plats), open(os.path.join(PUBLIC, 'data', 'rails.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    nb_ = sum(1 for t in tracks if any(v > -900 for v in t['p'][2::3]))
    print(len(plats), 'platforms', len(tracks), 'tracks', sum(len(t['p']) // 3 for t in tracks), 'points', nb_, 'with bridges', len(labels), 'labels', len(trains), 'trains',
          os.path.getsize(os.path.join(PUBLIC, 'data', 'rails.json')), 'bytes')


if __name__ == '__main__':
    main()
