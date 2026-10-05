"""Build photo-UV data for two further observed west-aisle window banks.
Source photos remain unchanged. License and identification: ARTWORK_SOURCES.json.
Requires numpy, Pillow, scipy. The lower edges in the green bank photograph are
partially cropped; only observed pixels are mapped, and that limit is recorded.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull
import math,json,shutil
root=Path(__file__).resolve().parents[1]

def shape(b,kind):
 x0,y0,x1,y1=b;cx=(x0+x1)/2;cy=(y0+y1)/2;r=(x1-x0)/2*.95
 if kind=='circle':return [[cx+r*math.cos(i*math.tau/48),cy+(y1-y0)/2*.95*math.sin(i*math.tau/48)] for i in range(48)]
 ry=r*.92;spring=y0+ry
 return [[x0+2,y1-2],[x1-2,y1-2]]+[[cx+r*math.cos(i*math.pi/32),spring-ry*math.sin(i*math.pi/32)] for i in range(33)]

def load_labels(filename,roi,threshold):
 im=Image.open(root/'assets/reference'/filename).convert('RGB');a=np.array(im)/255
 mx=a.max(2);mn=a.min(2);sat=(mx-mn)/np.maximum(mx,.001)
 st,vt,white=threshold;m=((sat>st)&(mx>vt))|(mx>white)
 region=np.zeros(m.shape,bool);x0,y0,x1,y1=roi;region[y0:y1,x0:x1]=True;m&=region
 m=ndimage.binary_closing(m,iterations=5);lab,n=ndimage.label(m)
 def poly(ids):
  if not isinstance(ids,list):ids=[ids]
  y,x=np.where(np.isin(lab,ids));coords=np.stack([x,-y],axis=1);h=ConvexHull(coords);v=coords[h.vertices]
  c=v.mean(0);v=c+(v-c)*.987
  return [[round(float(x),2),round(float(-y),2)] for x,y in v]
 return im,poly

p=root/'assets/textures/window_banks.json';data=json.loads(p.read_text())
# Anusha Alikhan2022 full lower bank. Its rose top is behind the gallery; the
# matched complete Mortel photo supplies all13 observed rose pieces.
file='artwork_glass_candidate_west_2022.jpg';im=Image.open(root/'assets/reference'/file)
red=dict(source=file,image_size=im.size,texture='glass_west_red_alikhan2022.jpg',attribution='Anusha Alikhan2022 / CC BY-SA4.0',
 caps=[
 [[705,1975,773,2196],[801,1975,874,2198],[904,1970,978,2194],[1111,1968,1183,2195],[1209,1970,1290,2197],[1310,1969,1390,2194]],
 [[711,1580,780,1812],[811,1581,881,1817],[908,1575,983,1810],[1103,1572,1177,1809],[1203,1572,1281,1810],[1302,1572,1384,1810]],
 [[714,1187,779,1435],[811,1160,879,1440],[910,1185,979,1434],[1090,1184,1161,1430],[1191,1152,1267,1433],[1290,1180,1368,1430]]],
 circles=[
 [[708,1866,775,1934],[806,1868,876,1938],[908,1865,980,1937],[1110,1864,1183,1934],[1212,1865,1285,1937],[1314,1862,1385,1933]],
 [[713,1490,777,1550],[810,1489,880,1555],[904,1484,977,1550],[1096,1484,1170,1548],[1197,1483,1275,1547],[1298,1480,1373,1547]],
 [[716,1096,779,1158],[810,1067,869,1129],[900,1096,969,1159],[1091,1093,1158,1155],[1188,1061,1250,1126],[1280,1093,1347,1158]]],
 large=[[704,945,820,1048],[846,944,963,1049],[787,841,899,936],[1078,944,1196,1049],[1214,941,1330,1044],[1170,832,1290,932]])
def luminous_hull(box,kind):
 a=np.array(im.convert('RGB'))/255;mx=a.max(2);mn=a.min(2);sat=(mx-mn)/np.maximum(mx,.001)
 x0,y0,x1,y1=box
 inside=np.zeros(mx.shape,bool);inside[y0:y1,x0:x1]=True
 good=inside&(((mx>.70)&(sat>.40))|(mn>.73))
 y,x=np.where(good)
 if len(x)<20:return shape(box,kind)
 coords=np.stack([x,-y],axis=1);h=ConvexHull(coords);v=coords[h.vertices];c=v.mean(0);v=c+(v-c)*.965
 return [[round(float(x),2),round(float(-y),2)] for x,y in v]
red['caps']=[[luminous_hull(b,'cap') for b in row] for row in red['caps']]
red['circles']=[[luminous_hull(b,'circle') for b in row] for row in red['circles']]
red['large']=[luminous_hull(b,'circle') for b in red['large']]
red['projection_basis']=[[1,-.025],[-.015,1]]
shutil.copyfile(root/'assets/reference'/file,root/'assets/textures'/red['texture'])
file='artwork_glass_candidate_west_mortel6.jpg';im,poly=load_labels(file,(1500,445,2250,900),(.44,.40,.82))
rose=dict(source=file,image_size=im.size,texture='glass_west_red_rose_mortel.jpg',attribution='Richard Mortel / CC BY2.0',core=poly(6),petals=[poly(i) for i in [1,2,3,4,5,7,8,10,11,12,13,14]])
# Perspective compresses the two upper-left petals into the same nearest
# 30-degree sector. Preserve their observed circular order explicitly so every
# actual petal and its stone surround occupies one unique sector.
rose['petal_angles']=[90,60,120,30,150,0,180,-30,-150,-60,-120,-90]
shutil.copyfile(root/'assets/reference'/file,root/'assets/textures'/rose['texture']);red['rose_source']=rose
# The source confirms this is immediately on the red side of Ribeiro's bank.
red['identification']='Matched by Lujan/Copecabana/Maria Congo oculi and blue lower-left capsule; adjacent red bank toward Glory. Relative order verified, absolute bay index approximate.'
data['west_red']=red
# Smiley.toerist2023 matching green-transition bank immediately to the other side.
file='artwork_glass_candidate_2023_3.jpg';im,poly=load_labels(file,(2250,520,3340,2559),(.40,.44,.84))
green=dict(source=file,image_size=im.size,texture='glass_west_green_smiley2023.jpg',attribution='Smiley.toerist2023 / CC BY-SA4.0',core=poly(63),petals=[poly(i) for i in [7,8,9,24,37,61,64,72,75,79,84,85]],
 large=[poly(i) for i in [110,115,99,120,121,113]],
 caps=[[poly(i) for i in [255,256,[257,292],258,[260,294],263]],[poly(i) for i in [185,189,194,200,203,[210,242]]],[poly(i) for i in [136,132,143,154,152,157]]],
 circles=[[poly(i) for i in [249,250,251,252,253,254]],[poly(i) for i in [171,176,180,182,184,187]],[poly(i) for i in [123,122,127,140,137,145]]])
# Recover full observed silhouettes of the dark-green final lower panes from
# low-threshold colours inside manually checked quadrilaterals; the earlier
# bright-pixel connected components captured only their illuminated tops.
a=np.array(im.convert('RGB'))/255;mx=a.max(2);mn=a.min(2);sat=(mx-mn)/np.maximum(mx,.001)
for col,quad in [(3,[(3005,2225),(3100,2235),(3220,2558),(3110,2558)]),(4,[(3130,2230),(3220,2235),(3350,2558),(3250,2558)]),(5,[(3240,2250),(3320,2247),(3460,2558),(3370,2558)])]:
 mask=Image.new('L',im.size,0);ImageDraw.Draw(mask).polygon(quad,fill=255)
 good=(np.array(mask)>0)&(sat>.27)&(mx>.23)
 y,x=np.where(good);coords=np.stack([x,-y],axis=1);hull=ConvexHull(coords);v=coords[hull.vertices];c=v.mean(0);v=c+(v-c)*.985
 green['caps'][0][col]=[[round(float(x),2),round(float(-y),2)] for x,y in v]
green['projection_basis']=[[1,-.27],[-.23,1]]
green['petal_angles']=[120,90,150,60,180,30,-150,0,-120,-30,-90,-60]
green['identification']='Green-transition bank immediately next to Ribeiro warm bank in Bracons2015 and Smiley2023. Exact numbered bay unknown.'
green['limits']='Last3 bottom source pane ends approach or cross the frame edge; only observed source pixels are used. Model does not claim full unseen bottom-edge artwork. Source hull UV fits are perspective approximations.'
shutil.copyfile(root/'assets/reference'/file,root/'assets/textures'/green['texture']);data['west_green']=green
q=p.with_suffix('.json.pending');q.write_text(json.dumps(data,indent=2));q.replace(p)
print('Added red and green verified west variants to',p)
