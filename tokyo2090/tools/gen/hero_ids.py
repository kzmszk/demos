"""The PLATEAU ids the hand-built districts replace (ASSETS/hero/exclude.json from gen.hero_src), for the districts
that have been built (public/hero/<d>/near.glb exists). gen.city and gen.foot leave these buildings out."""
import os, json
from .frame import ASSETS, PUBLIC


def excluded():
    p = os.path.join(ASSETS, 'hero', 'exclude.json')
    if not os.path.exists(p): return set()
    ex = json.load(open(p)); out = set()
    for name, ids in ex.items():
        if all(os.path.exists(os.path.join(PUBLIC, 'hero', name, f)) for f in ('near.glb', 'collide.obj', 'hero.json')): out |= set(ids)
    return out
