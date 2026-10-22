"""Convert a downloaded Overpass `out geom` response to compact local metre coordinates.

Network access is separate. This produces the ODbL database distributed with the demo.
Usage: python3 prepare_context.py /tmp/alhambra-osm.json [relations.json]
"""
import json, math, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
origin=(37.17725,-3.5897)
def xy(p): return [round((p['lon']-origin[1])*88700,2),round((origin[0]-p['lat'])*111320,2)]
def area(p): return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2)
raw=json.loads(Path(sys.argv[1]).read_text())
elements=raw['elements']
if len(sys.argv)>2: elements+=json.loads(Path(sys.argv[2]).read_text())['elements']
result={'origin':origin,'attribution':'© OpenStreetMap contributors','license':'ODbL-1.0','source':'https://www.openstreetmap.org/copyright','retrieved':'2026-10-22','buildings':[],'gardens':[],'walls':[]}
for e in elements:
    tags=e.get('tags',{})
    if e['type']=='relation':
        rings=[m['geometry'] for m in e.get('members',[]) if m.get('role')=='outer' and m.get('geometry')]
    else:rings=[e.get('geometry',[])]
    for ring in rings:
        if len(ring)<3:continue
        p=[xy(v) for v in ring]
        if p[-1]==p[0]:p=p[:-1]
        x=sum(v[0] for v in p)/len(p);z=sum(v[1] for v in p)/len(p)
        if e['id']==92528618:result['perimeter']=p;continue
        if tags.get('leisure')=='garden':result['gardens'].append({'p':p,'name':tags.get('name','')});continue
        if tags.get('barrier')=='city_wall' or tags.get('historic')=='citywalls':result['walls'].append(p);continue
        if not tags.get('building') or tags.get('building')=='roof' or area(p)<8:continue
        if not (-800<x<700 and -700<z<600):continue
        try:h=float(tags.get('height',float(tags.get('building:levels','2'))*3.2))
        except ValueError:h=7
        result['buildings'].append({'id':e['id'],'name':tags.get('name',''),'p':p,'h':max(3,min(24,h))})
out=ROOT/'public/data/context.json'
out.write_text(json.dumps(result,separators=(',',':'),ensure_ascii=False))
print(f'{len(result["buildings"])} footprints, {len(result["gardens"])} gardens, {out.stat().st_size:,} bytes')
