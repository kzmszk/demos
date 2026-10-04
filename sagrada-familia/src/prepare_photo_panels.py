"""Reproduce glass-only source-UV traces; photography attribution in ARTWORK_SOURCES.json. Requires numpy, scipy and Pillow. Source JPGs remain byte-for-byte unchanged."""
from PIL import Image
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull
from pathlib import Path
import json, shutil,math
root=Path(__file__).resolve().parents[1]
specs={
'east':dict(file='artwork_glass_east_2014_ribeiro.jpg',rose=[1,2,3,4,5,7,10,11,12,13,14,15],core=6,
large=[27,24,18,22,21,16],
caps=[[[168,2522,245,2778],[291,2518,367,2781],[413,2514,493,2779],[681,2515,749,2776],[794,2506,875,2777],[926,2497,1004,2775]],[[161,2070,237,2348],[286,2068,364,2350],[411,2061,491,2346],[678,2053,745,2337],[798,2052,875,2337],[925,2046,1005,2335]],[[158,1574,239,1884],[282,1548,365,1885],[408,1558,492,1875],[664,1546,749,1865],[795,1517,877,1864],[927,1532,1010,1855]]],
circles=[[[175,2405,241,2473],[295,2407,363,2468],[411,2403,481,2470],[675,2396,745,2468],[793,2391,863,2462],[917,2386,987,2456]],[[159,1953,233,2018],[287,1952,359,2018],[414,1944,484,2008],[671,1933,739,2001],[800,1934,871,1999],[928,1931,1000,2001]],[[167,1458,235,1521],[287,1428,360,1496],[410,1444,485,1508],[670,1430,742,1492],[799,1404,873,1467],[931,1418,1006,1483]]]),
'west':dict(file='artwork_glass_west_2014_ribeiro_3.jpg',rose=[8,9,10,11,12,15,16,18,[19,22],20,21,23],core=13,
large=[51,52,31,50,49,28],
caps=[[[321,2460,473,2898],[542,2466,688,2905],[766,2467,909,2900],[1194,2459,1337,2896],[1410,2468,1560,2893],[1625,2457,1787,2890]],[[385,1724,525,2144],[581,1729,718,2145],[786,1722,911,2144],[1158,1718,1310,2141],[1370,1721,1513,2141],[1563,1710,1715,2133]],[[441,1075,572,1448],[623,1027,746,1449],[805,1070,920,1444],[1152,1061,1278,1441],[1326,1020,1461,1443],[1501,1062,1644,1440]]],
circles=[[[361,2266,488,2387],[572,2270,697,2392],[781,2267,906,2388],[1190,2256,1318,2381],[1401,2263,1530,2384],[1605,2253,1736,2377]],[[425,1561,534,1654],[610,1561,722,1659],[801,1555,911,1652],[1172,1552,1284,1649],[1363,1561,1471,1649],[1549,1550,1659,1643]],[[483,943,579,1016],[654,898,751,971],[819,938,917,1010],[1153,932,1251,1006],[1321,890,1418,962],[1493,925,1591,1005]]])}
existing=root/'assets/textures/window_banks.json'
out=json.loads(existing.read_text()) if existing.exists() else {}
for family,s in specs.items():
 src=root/'assets/reference'/s['file'];im=Image.open(src).convert('RGB');arr=np.array(im)/255;mx=arr.max(2);mn=arr.min(2);sat=(mx-mn)/np.maximum(mx,.001)
 mask=((sat>.36)&(mx>.33))|(mx>.82)
 if family=='west':mask=((sat>.41)&(mx>.42))|(mx>.80)
 mask=ndimage.binary_closing(mask,iterations=7);lab,n=ndimage.label(mask)
 def poly(ids):
  if not isinstance(ids,list):ids=[ids]
  y,x=np.where(np.isin(lab,ids));coords=np.stack([x,-y],axis=1);h=ConvexHull(coords);v=coords[h.vertices]
  # Average hull vertices are an adequate center for star-shaped apertures.
  c=v.mean(0);v=c+(v-c)*.985
  return [[round(float(x),2),round(float(-y),2)] for x,y in v]
 def bboxpoly(b,kind):
  x0,y0,x1,y1=b;cx=(x0+x1)/2;cy=(y0+y1)/2;r=(x1-x0)/2*.96
  if kind=='circle':
   return [[cx+r*math.cos(i*math.tau/48),cy+(y1-y0)/2*.96*math.sin(i*math.tau/48)] for i in range(48)]
  # Oval source top / square bottom, omitting photographed stone arris.
  ry=r*.91;spring=y0+ry
  return [[x0+2,y1-2],[x1-2,y1-2]]+[[cx+r*math.cos(i*math.pi/32),spring-ry*math.sin(i*math.pi/32)] for i in range(33)]
 item={'source':s['file'],'image_size':im.size,'texture':'glass_'+family+'_ribeiro2014.jpg','core':poly(s['core']),'petals':[poly(i) for i in s['rose']],'large':[poly(i) for i in s['large']], 'caps':[[bboxpoly(b,'cap') for b in row] for row in s['caps']], 'circles':[[bboxpoly(b,'circle') for b in row] for row in s['circles']]}
 # Preserve original image unchanged: only UV coordinates rectify the glass.
 shutil.copyfile(src,root/'assets/textures'/item['texture']);out[family]=item
destination=root/'assets/textures/window_banks.json'
temporary=destination.with_suffix('.json.pending');temporary.write_text(json.dumps(out,indent=2));temporary.replace(destination)
print({k:{'size':v['image_size'],'apertures':1+len(v.get('rose_source',v)['petals'])+len(v['large'])+sum(map(len,v['caps']))+sum(map(len,v['circles']))} for k,v in out.items()})
