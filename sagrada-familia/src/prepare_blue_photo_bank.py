"""Extract the verified Mont Athos/Kiev east bank, preserving source pixels.

CPU-only. Requires existing numpy, Pillow and scipy. Writes a separate candidate
JSON; the integration owner merges it into window_banks.json after UV review.
Richard Mortel,2016-11-12, CC BY2.0. See ARTWORK_SOURCES.json.
"""
from pathlib import Path
import json
import shutil

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[1]
source='artwork_east_2016_mortel2_high.jpg'
image=Image.open(ROOT/'assets/reference'/source).convert('RGB')
assert image.size==(3840,2560), 'Extraction is tied to the inspected immutable source dimensions'
a=np.asarray(image,dtype=np.float32)/255
mx=a.max(2);mn=a.min(2);sat=(mx-mn)/np.maximum(mx,.001)
mask=((sat>.28)&(mx>.45)&(a[:,:,2]>a[:,:,0]*1.10))|(mn>.78)
roi=np.zeros(mask.shape,bool);roi[255:2560,1750:2990]=True
labels,_=ndimage.label(ndimage.binary_closing(mask&roi,iterations=5))

def polygon(label, capsule=False, horizontal_slope=.10):
    y,x=np.where(labels==label)
    if len(x)<150:raise ValueError('Missing observed glass component '+str(label))
    points=np.stack([x,-y],axis=1)
    hull=points[ConvexHull(points).vertices].astype(float)
    center=hull.mean(0);hull=center+(hull-center)*.987
    result=[[round(float(px),2),round(float(-py),2)] for px,py in hull]
    if not capsule:return result
    # Recover each capsule's local vertical direction, since perspective makes
    # the six columns converge. A global skew cannot rectify all six at once.
    _,axes=np.linalg.eigh(np.cov(points.T))
    vertical=axes[:,-1]
    if vertical[1]<0:vertical=-vertical
    basis=[[1,horizontal_slope],[float(vertical[0]/vertical[1]),1]]
    return {'polygon':result,'projection_basis':basis}

caps=[[85,84,83,82,81,80],[70,69,68,67,63,62],[51,49,50,48,42,43]]
circles=[[76,75,74,73,72,71],[61,60,59,55,53,52],[45,38,39,37,29,30]]
bank={
    'source':source,'image_size':list(image.size),
    'texture':'glass_east_blue_mortel2016.jpg',
    'attribution':'Richard Mortel / CC BY2.0',
    'caps':[[polygon(i,True,(.067,.10,.16)[row]) for i in ids] for row,ids in enumerate(caps)],
    'circles':[[polygon(i) for i in ids] for ids in circles],
    'large':[polygon(i) for i in [25,22,19,21,20,16]],
    'core':polygon(7),
    'petals':[polygon(i) for i in [1,2,3,4,5,6,9,10,11,12,14,15]],
    'petal_angles':[60,90,30,120,0,150,330,180,300,210,270,240],
    'identification':'Distinct blue east/Nativity bank, matched in Ank Kumar2014 painting04/05/06 and Mortel2016 by Mont Athos,Kiev,S.Maria Maggiore,Einsiedeln medallions and all capsule art. Relative neighbor pale-green is visible left in Mortel2; absolute numbered bay remains unverified.',
    'limits':'The first two bottom source capsules reach the photograph frame edge; only visible glass is mapped. No invented bottom-edge continuation. Source photograph retains exposure/illumination, not measured spectral glass. Perspective rectification and metric openings are approximate.',
}
shutil.copyfile(ROOT/'assets/reference'/source,ROOT/'assets/textures'/bank['texture'])
out=ROOT/'assets/textures/east_blue_bank_candidate.json'
out.write_text(json.dumps({'east_blue_mortel2016':bank},indent=2))
print('BLUE_BANK_READY',out)
