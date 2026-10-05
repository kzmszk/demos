"""CPU orthographic geometry/UV verification. Not a Cycles or runtime screenshot.
The solid background is schematic stone. No source photos are modified.
"""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'));import glazing
D=json.loads((Path(sys.argv[1]) if len(sys.argv)>1 else root/'assets/textures/window_banks.json').read_text())
for fam,data in D.items():
 spec=dict(name='reference_uv_'+fam,center=(0,0,0),normal=(0,1,0),tangent=(1,0,0),width=6.1,z_bottom=0,z_top=11.85,side=-1)
 B=glazing.Batch(spec);glazing.photographed_bank(B,0,11.85,6.1,data,fam)
 W,H=650,1350;bg=np.zeros((H,W,3),dtype=np.uint8);bg[:]=[189,179,158]
 def pxy(p):return [(p[0]+3.25)/6.5*W,(12.35-p[2])/13.5*H]
 triangles=0
 for key,uv in B.uvs.items():
  v,faces,col=B.data[key];source=data['rose_source'] if key.endswith('_rose') else data
  tex=np.array(Image.open(root/'assets/textures'/source['texture']).convert('RGB'));th,tw=tex.shape[:2]
  for face in faces:
   p=np.array([pxy(v[i]) for i in face]);t=np.array([[uv[i][0]*tw,(1-uv[i][1])*th] for i in face]);low=np.maximum(p.min(0).astype(int),0);high=np.minimum(np.ceil(p.max(0)).astype(int),[W-1,H-1])
   if np.any(high<low):continue
   xx,yy=np.meshgrid(np.arange(low[0],high[0]+1),np.arange(low[1],high[1]+1));a=p[1]-p[0];b=p[2]-p[0];det=a[0]*b[1]-a[1]*b[0]
   if abs(det)<1e-8:continue
   qx=xx-p[0,0];qy=yy-p[0,1];l1=(qx*b[1]-qy*b[0])/det;l2=(a[0]*qy-a[1]*qx)/det;m=(l1>=0)&(l2>=0)&(l1+l2<=1)
   tx=np.clip(t[0,0]+l1*(t[1,0]-t[0,0])+l2*(t[2,0]-t[0,0]),0,tw-1).astype(int);ty=np.clip(t[0,1]+l1*(t[1,1]-t[0,1])+l2*(t[2,1]-t[0,1]),0,th-1).astype(int)
   bg[yy[m],xx[m]]=tex[ty[m],tx[m]];triangles+=1
 im=Image.fromarray(bg);draw=ImageDraw.Draw(im)
 draw.text((18,H-66),'GLASS UV QA - '+fam+' - photographed artwork',fill=(35,35,35))
 draw.text((18,H-49),'Metric placement/stone background schematic. Not final render.',fill=(35,35,35))
 draw.text((18,H-32),'Photo credits/limits: docs/ARTWORK_SOURCES.json',fill=(35,35,35))
 dest=root/'screenshots/materials';dest.mkdir(parents=True,exist_ok=True);im.save(dest/('window_bank_'+fam+'_uv.png'))
 print(fam,triangles,'mapped triangles')
