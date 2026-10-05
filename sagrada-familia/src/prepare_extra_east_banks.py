"""Two observed east banks: unchanged licensed photos + traced glass boundaries.
CPU only. Creates independent proposed JSON; never edits window_banks.json.
Pixel coordinates below are measured at a 960px-wide viewing copy, then scaled
back to the exact downloaded photograph. No invented glass pattern or lettering.
"""
from pathlib import Path
import json,math,shutil,hashlib
from PIL import Image
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull
ROOT=Path(__file__).resolve().parents[1]

def ellipse(box):
 x0,y0,x1,y1=box;cx=(x0+x1)/2;cy=(y0+y1)/2
 return [[cx+(x1-x0)*.48*math.cos(i*math.tau/48),cy+(y1-y0)*.48*math.sin(i*math.tau/48)] for i in range(48)]
def cap(p):
 # top centre x/y, bottom y, top width, bottom centre x, bottom width
 cx,y0,y1,w,bx,bw=p;r=w/2;ry=r*.88
 return [[bx-bw/2,y1],[bx+bw/2,y1]]+[[cx+r*math.cos(i*math.pi/32),y0+ry-ry*math.sin(i*math.pi/32)] for i in range(33)]
def label_polys(filename,roi):
 im=Image.open(ROOT/'assets/reference'/filename).convert('RGB');scale=im.width/960;small=im.resize((960,round(im.height/scale)));a=np.array(small)/255;mx=a.max(2);mn=a.min(2);sat=(mx-mn)/np.maximum(mx,.001)
 m=((sat>.32)&(mx>.52)&((a[:,:,1]>a[:,:,0]*.9)|(a[:,:,2]>a[:,:,0]*.85)))|(mn>.85);region=np.zeros(m.shape,bool);x0,y0,x1,y1=roi;region[y0:y1,x0:x1]=True;m&=region;m=ndimage.binary_closing(m,iterations=2);lab,n=ndimage.label(m)
 def poly(ids):
  if not isinstance(ids,list):ids=[ids]
  yy,xx=np.where(np.isin(lab,ids));xy=np.stack([xx,yy],axis=1);v=xy[ConvexHull(xy).vertices];c=v.mean(0);return (c+(v-c)*.984).tolist()
 return im,scale,poly

def make(fam,file,roi,petals,core,angles,caps,circles,large,basis,ident,limits):
 im,scale,poly=label_polys(file,roi)
 d=dict(source=file,image_size=list(im.size),texture='glass_'+fam+'_meskens2016.jpg',attribution='© Ad Meskens / Wikimedia Commons / CC BY-SA 4.0',caps=[[cap(x) for x in row] for row in caps],circles=[[ellipse(x) for x in row] for row in circles],large=[ellipse(x) for x in large],core=poly(core),petals=[poly(i) for i in petals],petal_angles=angles,projection_basis=basis,identification=ident,limits=limits)
 def scale_poly(v):return [[round(float(x)*scale,3),round(float(y)*scale,3)] for x,y in v]
 for k in ['caps','circles']:d[k]=[[scale_poly(v) for v in row] for row in d[k]]
 for k in ['large','petals']:d[k]=[scale_poly(v) for v in d[k]]
 d['core']=scale_poly(d['core']);src=ROOT/'assets/reference'/file;dst=ROOT/'assets/textures'/d['texture'];shutil.copyfile(src,dst)
 d['derivation']={'method':'55 independently traced observed glass apertures. Rose hull from colour segmentation; capsules and circles manually traced against source. Per-aperture UV fan and affine projection basis; no whole-bank homography; no pattern invention, recolouring, text replacement, generative filling or pixel modification.','source_view_width_px':960,'coordinate_scale':scale,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'texture_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','geometry_limit':'Approximate source perspective correction and metric aperture placement; not surveyed.'}
 return d
D={}
D['east_yellowgreen']=make('east_yellowgreen','artwork_east_barcelona10_high.jpg',(170,185,660,1020),[9,12,15,18,24,26,29,27,25,[19,21,22],16,14],17,[90,60,30,0,-30,-60,-90,-120,-150,180,150,120],
 [
 [[219,875,995,30,198,31],[280,879,998,31,262,34],[345,879,1001,30,330,33],[468,880,1001,34,461,34],[534,881,1005,34,529,36],[598,880,1008,35,600,36]],
 [[258,664,774,28,241,29],[315,665,777,31,303,31],[371,665,777,32,362,33],[479,664,777,33,473,34],[537,663,777,33,535,34],[595,663,777,34,597,35]],
 [[291,488,580,28,282,29],[346,476,581,29,335,29],[392,485,578,30,381,31],[488,483,578,29,484,31],[539,469,578,30,537,31],[588,480,577,29,590,31]]
 ],
 [
 [[210,817,244,849],[270,821,303,851],[333,820,369,850],[453,819,488,849],[517,820,553,852],[580,819,616,852]],
 [[252,618,285,642],[307,618,340,642],[362,618,392,642],[465,617,496,642],[519,617,553,642],[578,617,608,642]],
 [[290,451,315,467],[338,439,363,455],[385,448,409,465],[478,446,502,462],[528,434,554,450],[577,446,601,462]]
 ],
 [[299,392,346,420],[370,389,414,416],[344,353,386,376],[484,383,528,412],[553,384,600,413],[522,344,565,371]],
 [[1,.025],[.10,1]],
 'East-aisle yellow/green bank left of pale-green bank in Ad Meskens 2016 interior10/11 and Richard Mortel 2016 photos4/5/10. Relative adjacency confirmed; absolute bay number unresolved.',
 'Bottom visitor rail touches the original lowest glass edges; crops stop just inside observed glazing. Perspective, dimensional placement and lighting exposure approximate; source photograph contains brighter highlights in upper-right panes.')
D['east_palegreen']=make('east_palegreen','artwork_east_barcelona11_high.jpg',(240,95,520,770),[1,4,7,12,14,17,20,15,13,8,5,2],9,[90,60,30,0,-30,-60,-90,-120,-150,180,150,120],
 [
 [[268,698,758,25,267,25],[308,697,758,24,308,25],[349,697,758,23,350,23],[424,698,758,23,424,23],[463,698,758,22,463,23],[501,697,755,23,501,24]],
 [[267,565,639,23,267,24],[309,567,640,23,309,24],[350,567,640,23,350,24],[424,570,641,23,424,24],[463,571,641,23,463,24],[501,569,640,23,501,24]],
 [[267,422,503,25,267,26],[309,413,506,25,309,26],[349,426,508,24,349,25],[424,431,511,25,424,26],[462,423,512,24,462,25],[500,434,512,23,500,24]]
 ],
 [
 [[257,664,279,681],[299,664,319,681],[337,663,359,681],[414,664,435,681],[451,665,474,681],[490,663,511,681]],
 [[257,531,279,550],[298,535,319,552],[337,535,359,553],[413,537,436,554],[452,538,474,555],[490,539,511,556]],
 [[257,387,280,405],[298,379,320,397],[337,392,360,410],[414,397,435,414],[452,389,474,407],[491,402,512,420]]
 ],
 [[258,329,299,357],[319,333,358,360],[290,287,330,316],[414,339,454,367],[473,344,511,371],[444,300,483,330]],
 [[1,-.025],[.005,1]],
 'East-aisle pale-green bank between yellowgreen and bluegreen banks in Ad Meskens 2016 interior11 and Richard Mortel2016 photos10/11/12; unique bottom blue-to-red capsules and Juan Sahagun oculus. Absolute bay number unresolved.',
 'Source upper panes and several oculi have strong daylight highlights; clipped photo information cannot be recovered. Actual retained glass pixels are not recoloured. Slight source perspective remains. No rail crosses these traced pane interiors.')
# Pale-green replacement: the same bank with lower exposure in Mortel2016.
# Its final six capsules extend below the photo, so those exact six observed
# capsules come from Meskens2016. Both image blocks retain every original pixel;
# only atlas placement changes. No seams are stitched inside a glass aperture.
pale=D['east_palegreen'];original_bottom=pale['caps'][0]
file='artwork_east_mortel_2016_11_high.jpg';im,scale,poly=label_polys(file,(305,80,675,570))
def S(p):return [[round(x*scale,3),round(y*scale,3)] for x,y in p]
pale['caps'][1]=[S(cap(v)) for v in [[355,418,502,26,350,29],[399,419,502,26,397,28],[441,418,502,25,440,27],[527,416,500,26,530,28],[569,417,500,27,576,28],[610,415,499,26,618,29]]]
pale['caps'][2]=[S(poly(i)) for i in [55,46,52,53,47,51]]
pale['circles'][1]=[S(poly(i)) for i in [65,67,66,63,64,62]]
pale['circles'][2]=[S(poly(i)) for i in [44,39,43,41,38,42]]
pale['circles'][0]=[S(ellipse(b)) for b in [[330,535,356,558],[378,535,405,558],[428,534,453,557],[522,531,546,556],[568,532,593,557],[617,532,640,555]]]
pale['large']=[S(poly(i)) for i in [31,32,26,29,30,25]]
pale['core']=S(poly(7));pale['petals']=[S(poly(i)) for i in [1,3,5,9,[12,14],16,18,15,10,8,6,2]]
base=Image.open(ROOT/'assets/reference/artwork_east_barcelona11_high.jpg').convert('RGB')
atlas=Image.new('RGB',(max(im.width,base.width),im.height+base.height));atlas.paste(im,(0,0));atlas.paste(base,(0,im.height))
pale['caps'][0]=[[[x,y+im.height] for x,y in p] for p in original_bottom]
pale['texture']='glass_east_palegreen_mortel_meskens_atlas.png';dest=ROOT/'assets/textures'/pale['texture'];atlas.save(dest,optimize=True)
pale['source']='artwork_east_mortel_2016_11_high.jpg + artwork_east_barcelona11_high.jpg'
pale['image_size']=list(atlas.size);pale['attribution']='Richard Mortel / CC BY2.0; © Ad Meskens / Wikimedia Commons / CC BY-SA4.0. Atlas/UV derivative CC BY-SA4.0.'
pale['projection_basis']=[[1,0],[0,1]]
pale['limits']='Mortel upper49 apertures preserve lower-exposure real motifs; six complete lower capsules come from the same identified bank in Meskens2016. Exact matching confirmed by unique blue/green/red lower pattern and Juan Sahagun oculus. Photograph lighting differs between source blocks, with residual highlights. No generated fill, individual-glass colour change or cross-bank substitution.'
pale['derivation']={'method':'Lossless vertical pixel atlas: Mortel1920x1280 at[0,0], Meskens1920x1706 at[0,1280]. All49 upper/oculus/rose polygons refer to Mortel; only six bottom capsule polygons refer to Meskens, offset1280px. Each complete aperture belongs to one unchanged photo block. Affine per-aperture UV, no global homography.','atlas_license':'CC BY-SA4.0','atlas_license_url':'https://creativecommons.org/licenses/by-sa/4.0/','sources':[{'path':'assets/reference/'+file,'photographer':'Richard Mortel','license':'CC BY2.0','license_url':'https://creativecommons.org/licenses/by/2.0/','offset_px':[0,0],'sha256':hashlib.sha256((ROOT/'assets/reference'/file).read_bytes()).hexdigest()},{'path':'assets/reference/artwork_east_barcelona11_high.jpg','photographer':'Ad Meskens','license':'CC BY-SA4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','offset_px':[0,im.height],'sha256':hashlib.sha256((ROOT/'assets/reference/artwork_east_barcelona11_high.jpg').read_bytes()).hexdigest()}],'atlas_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'underlying_artist':'Joan Vila-Grau, separately attributed glass designer; photographer licenses do not establish separate artwork copyright waiver.'}
p=ROOT/'assets/textures/east_bank_candidates.json';p.write_text(json.dumps(D,indent=2));print('Wrote',p, list(D))
