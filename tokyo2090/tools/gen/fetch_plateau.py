"""Download the PLATEAU building tiles (3D Tiles, LOD2, no texture; 国土交通省 Project PLATEAU, CC BY 4.0) that touch
the frame, ward by ward.  Leaves of each ward's tileset are kept when their region overlaps the frame bbox.
  python -m gen.fetch_plateau            -> ASSETS/plateau/<ward>/tileset.json + data/*.b3dm, ASSETS/plateau/tiles.json"""
import os, json, math, time, urllib.request
from .frame import ASSETS, bbox_lonlat

WARDS = ('13113', '13104', '13103', '13101', '13110', '13114', '13112', '13116')     # 渋谷 新宿 港 千代田 目黒 中野 世田谷 豊島
PL = os.path.join(ASSETS, 'plateau')

def leaves(node, acc):
    ch = node.get('children') or []
    if not ch:
        acc.append(node)
    else:
        for c in ch: leaves(c, acc)
    return acc

def overlaps(region, bb):
    w, s, e, n = [math.degrees(v) for v in region[:4]]
    return not (e < bb[0] or w > bb[2] or n < bb[1] or s > bb[3])

def main():
    bb = bbox_lonlat(150.0)
    index = {}
    for line in open(os.path.join(PL, 'wards.txt')):
        p = line.split()
        code = p[0][:5]
        if code not in WARDS: continue
        url = p[-1]; base = url.rsplit('/', 1)[0]
        d = os.path.join(PL, code); os.makedirs(os.path.join(d, 'data'), exist_ok=True)
        ts = os.path.join(d, 'tileset.json')
        if not os.path.exists(ts): urllib.request.urlretrieve(url, ts)
        t = json.load(open(ts))
        keep = [n for n in leaves(t['root'], []) if overlaps(n['boundingVolume']['region'], bb)]
        got = 0
        for n in keep:
            uri = n['content'].get('uri') or n['content'].get('url')
            dst = os.path.join(d, uri)
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                for k in range(3):
                    try: urllib.request.urlretrieve(base + '/' + uri, dst); break
                    except Exception as e: time.sleep(2)
            if os.path.exists(dst): got += 1
        index[code] = [dict(uri=n['content'].get('uri') or n['content'].get('url'), region=n['boundingVolume']['region']) for n in keep]
        print(code, 'leaves', len(leaves(t['root'], [])), 'in frame', len(keep), 'got', got, flush=True)
    json.dump(index, open(os.path.join(PL, 'tiles.json'), 'w'))

if __name__ == '__main__':
    main()
