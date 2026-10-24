"""hero.json: spawns (local x, y; heading 0 = north, +pi/2 = east), labels, stats."""
import json, math
import common as C

SPAWNS = [
    dict(name='都民広場', x=72.0, y=78.0, heading=-1.72,
         note="Citizens' Plaza, the overgrown semicircle inside the Assembly colonnade, looking up at the twin towers"),
    dict(name='都庁前 北の瓦礫', x=-92.0, y=150.0, heading=2.4,
         note='the street at the foot of the towers: the bus stop, the rubble ramp from the fallen north crown'),
    dict(name='公園通り', x=-101.0, y=64.0, heading=1.35,
         note='west side along Chuo Park, the sheer west face of No.1 above the street trees'),
    dict(name='第二本庁舎前', x=22.0, y=-30.0, heading=-2.6,
         note='the deck between No.1 and No.2, bus stop and taxi rank'),
]
LABELS = [
    dict(name='東京都庁 第一本庁舎', x=-38.0, y=58.0, z=282.0, kind='building'),
    dict(name='第二本庁舎', x=-4.0, y=-112.0, z=200.0, kind='building'),
    dict(name='都議会議事堂', x=100.0, y=86.0, z=78.0, kind='building'),
    dict(name='都民広場', x=62.0, y=80.0, z=38.0, kind='place'),
]


def write(stats):
    d = dict(district='tocho', origin=list(C.ORIGIN), spawns=SPAWNS, labels=LABELS, stats=stats)
    json.dump(d, open(C.PUB + 'hero.json', 'w'), ensure_ascii=False, indent=1)
