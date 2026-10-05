"""Editable architectural glazing with attributed photographed window artwork.

API build(ctx): consumes interior.WINDOWS (metres, normal/tangent coordinates).
Actual glazed holes are round heads, oculi and petal rosettes documented in the
official Interior Booklet9, page8. Side banks map licensed source photographs;
apse/clerestory artwork remains an original interpretation. Front faces point
outside, so sided materials preserve interior colour and subdue daylight exterior.
See MATERIAL_SOURCES.json for artwork sources and model/lighting limitations.
"""
import math, random
from math import pi, sin, cos

PALETTES={
 'cool':[(.085,.20,.52),(.08,.36,.65),(.15,.57,.68),(.18,.50,.35),(.44,.67,.30),(.38,.57,.73),(.65,.77,.79),(.14,.26,.45),(.26,.40,.57)],
 'warm':[(.58,.08,.055),(.78,.18,.04),(.89,.37,.04),(.92,.56,.07),(.86,.71,.23),(.79,.35,.18),(.91,.79,.43),(.58,.22,.13),(.76,.51,.21)],
 'gold':[(.72,.52,.09),(.81,.67,.22),(.89,.77,.37),(.83,.80,.55),(.59,.64,.32),(.86,.71,.39),(.92,.88,.63),(.57,.63,.47),(.80,.84,.66)],
 'clear':[(.74,.83,.83),(.87,.89,.84),(.83,.86,.84),(.78,.84,.86),(.89,.89,.83),(.79,.85,.79),(.84,.87,.84),(.72,.79,.81),(.88,.89,.84)]}

# Model bay indices are approximate, not a surveyed artwork inventory.
# At the final Nativity side photo-right is decreasing X. The independently
# photographed yellowgreen -> palegreen -> blue relative progression is kept;
# Ribeiro's exact numbered location is unknown and explicitly remains estimated.
PHOTO_BANK_LAYOUT={
 'east':['east_blue_mortel2016','east','east_palegreen','east_yellowgreen','east_yellowgreen'],
 'west':['west_red','west_red','west','west','west_green'],
}

def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return (a[0]-b[0],a[1]-b[1])
def area(poly):return sum(cross(poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly)))/2

def ellipse(cx,cz,rx,rz,steps=48,rotate=0):
    c,s=cos(rotate),sin(rotate)
    return [(cx+c*rx*cos(i*2*pi/steps)-s*rz*sin(i*2*pi/steps),cz+s*rx*cos(i*2*pi/steps)+c*rz*sin(i*2*pi/steps)) for i in range(steps)]

def capsule(cx,bottom,width,height,steps=20):
    r=width/2; spring=bottom+height-r
    return [(cx-r,bottom),(cx+r,bottom)]+[(cx+r*cos(a*pi/steps),spring+r*sin(a*pi/steps)) for a in range(steps+1)]

def clip(poly, boundary):
    """Clip a polygon to a counterclockwise convex boundary."""
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)]; edge=sub(b,a)
        old=poly; poly=[]
        if not old:break
        for k,p in enumerate(old):
            q=old[(k+1)%len(old)]
            cp=cross(edge,sub(p,a)); cq=cross(edge,sub(q,a))
            if cp>=-1e-8:poly.append(p)
            if (cp<0)!=(cq<0):
                t=cp/(cp-cq);poly.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    return poly

def rayhit(center,d,poly):
    hits=[]
    for i,p in enumerate(poly):
        e=sub(poly[(i+1)%len(poly)],p);a=sub(p,center); den=cross(d,e)
        if abs(den)<1e-9:continue
        t=cross(a,e)/den;u=cross(a,d)/den
        if t>1e-7 and -.00001<=u<=1.00001:hits.append(t)
    if not hits:raise ValueError('No positive radial hit in convex aperture')
    t=min(hits);return (center[0]+t*d[0],center[1]+t*d[1])

class Batch:
    def __init__(self, spec):
        self.spec=spec;self.data={};self.uvs={};self.relief=False;self.counts={'panes':0,'apertures':0}
    def world(self,p,depth=0):
        s=self.spec;t=s['tangent'];n=s['normal'];c=s['center']
        return (c[0]+t[0]*p[0]+n[0]*depth,c[1]+t[1]*p[0]+n[1]*depth,p[1])
    def polygon(self,key,points,depth=0,color=None):
        v,f,col=self.data.setdefault(key,([],[],[]));start=len(v)
        v.extend(self.world(p,depth) for p in points)
        face=tuple(range(start,len(v)))
        if key.startswith('glass_photo') or (key.startswith('glass_') and key.endswith('_colored')):
            # For CCW (u,z) coordinates, tangent×up is (ty,-tx,0).
            # Normalize against the outward aperture normal. Reverse indices
            # only: artwork UVs and vertex colours remain attached to vertices.
            t=self.spec['tangent'];n=self.spec['normal']
            if area(points)*(t[1]*n[0]-t[0]*n[1])<0:face=tuple(reversed(face))
        f.append(face)
        col.extend([color or (1,1,1,1)]*len(points))
    def spatial(self,key,pts,color=None):
        v,f,col=self.data.setdefault(key,([],[],[]));start=len(v)
        v.extend(pts);f.append(tuple(range(start,len(v))));col.extend([color or (1,1,1,1)]*len(pts))
    def photopoly(self,key,points,uvs):
        self.polygon(key,points)
        self.uvs.setdefault(key,[]).extend(uvs)
    def ring(self,inner,outer,key='stone_light',depth=.18):
        center=(sum(p[0] for p in inner)/len(inner),sum(p[1] for p in inner)/len(inner))
        angles=sorted(set(round(math.atan2(p[1]-center[1],p[0]-center[0]),8) for p in inner+outer))
        inn=[];out=[]
        for a in angles:
            d=(cos(a),sin(a));inn.append(rayhit(center,d,inner));out.append(rayhit(center,d,outer))
        for i in range(len(angles)):
            j=(i+1)%len(angles)
            if not self.relief:
                for dep in (-depth,depth):self.polygon(key,[inn[i],out[i],out[j],inn[j]],dep)
                self.spatial(key,[self.world(inn[i],-depth),self.world(inn[j],-depth),self.world(inn[j],depth),self.world(inn[i],depth)])
                continue
            # Photo-informed ruled, folded stone spandrels. The interior face
            # steps out from a narrow reveal, then returns through angular
            # shoulders towards tile corners. Adjoining tile edges retain the
            # same depth, so no open seams or overlapping raised strips occur.
            # 0.08-0.22m relief is a visual estimate, not surveyed moulding depth.
            def profile(k):
                p,q=inn[k],out[k];d=sub(q,p);length=math.hypot(*d)
                if length<1e-5:return [(p,-.12),(p,-.13),(q,-depth),(q,-depth)]
                lip=min(.050,length*.24);shoulder=min(.20,length*.62)
                u=(d[0]/length,d[1]/length)
                corner_angles=[math.atan2(v[1]-center[1],v[0]-center[0]) for v in outer]
                # Rectangular tile corners create the diagonal ribs seen in the
                # photographs; curved outer bounds use a more subdued shoulder.
                peak=0
                if len(outer)<=10:
                    for a in corner_angles:
                        delta=abs((angles[k]-a+pi)%(2*pi)-pi)
                        peak=max(peak,max(0,1-delta/.38))
                projection=min(1,length/.32)
                return [(p,-.12),((p[0]+u[0]*lip,p[1]+u[1]*lip),-.23),((p[0]+u[0]*shoulder,p[1]+u[1]*shoulder),-.25-projection*(.045+.10*peak)),(q,-depth)]
            ai,aj=profile(i),profile(j)
            for band in range(3):
                self.spatial(key,[self.world(ai[band][0],ai[band][1]),self.world(ai[band+1][0],ai[band+1][1]),self.world(aj[band+1][0],aj[band+1][1]),self.world(aj[band][0],aj[band][1])])
            self.polygon(key,[inn[i],out[i],out[j],inn[j]],depth)
            self.spatial(key,[self.world(inn[i],-.12),self.world(inn[j],-.12),self.world(inn[j],depth),self.world(inn[i],depth)])
    def finish(self,H,M):
        for key,(v,f,col) in self.data.items():
            o=H.mesh(self.spec['name']+'_'+key,v,f,M[key],uv=self.uvs.get(key))
            if key.startswith('glass_') and key.endswith('_colored'):
                attr=o.data.color_attributes.new(name='Col',type='FLOAT_COLOR',domain='POINT')
                for index,value in enumerate(col):attr.data[index].color=value
            o['source_note']=('Actual photographed glass; source key '+key+'; glass-only UV mapping; see ARTWORK_SOURCES.json for photographer/license and MATERIAL_SOURCES.json for location limits' if key.startswith('glass_photo') else 'Original modeled stone; official Booklet 9 p8 and CC BY-SA photograph reference')
            o['window_bay']=self.spec['name']
            if key.startswith('glass_photo') or (key.startswith('glass_') and key.endswith('_colored')):
                o['glass_front_face']='Exterior; geographic mirror with winding repair preserves outward normals'

def rect(x0,x1,z0,z1):return [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]

def glass(batch,shape,family,rng,light=.0,density=4):
    """Small warped quadrilaterals and occasional diagonal shards, clipped to hole."""
    minx=min(p[0] for p in shape);maxx=max(p[0] for p in shape)
    minz=min(p[1] for p in shape);maxz=max(p[1] for p in shape)
    nx=max(3,int((maxx-minx)*density));nz=max(3,int((maxz-minz)*density))
    dx=(maxx-minx)/nx;dz=(maxz-minz)/nz
    grid=[]
    for j in range(nz+1):
        row=[]
        for i in range(nx+1):
            x=minx+i*dx;z=minz+j*dz
            if 0<i<nx:x+=rng.uniform(-.24,.24)*dx
            if 0<j<nz:z+=rng.uniform(-.24,.24)*dz
            row.append((x,z))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            p=[grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]]
            parts=[p] if rng.random()>.33 else [[p[0],p[1],p[2]],[p[0],p[2],p[3]]]
            for part in parts:
                poly=clip(part,shape)
                if len(poly)<3 or abs(area(poly))<.00005:continue
                wave=sin((i/nx)*4.5+(j/nz)*5.7+family.__len__())
                index=(int((wave+1)*2.5)+rng.choice([0,0,1,3]))%9
                rgb=PALETTES[family][index]
                mix=light+rng.uniform(-.055,.055)
                if family!='clear' and rng.random()<.08:mix=max(mix,.65)
                rgb=tuple(linear(max(.015,min(.96,c*(1-mix)+.88*mix))) for c in rgb)+(1,)
                batch.polygon('glass_'+family+'_colored',poly,0,rgb);batch.counts['panes']+=1
                # Slender lead ribbons, two-sided and raised from glazing. Width
                # 9mm is subordinate to the 18-30cm stone reveals.
                for k,a in enumerate(poly):
                    b=poly[(k+1)%len(poly)];vx=b[0]-a[0];vz=b[1]-a[1];l=math.hypot(vx,vz)
                    if l<.006:continue
                    d=.0045;off=(-vz/l*d,vx/l*d)
                    q=[(a[0]-off[0],a[1]-off[1]),(b[0]-off[0],b[1]-off[1]),(b[0]+off[0],b[1]+off[1]),(a[0]+off[0],a[1]+off[1])]
                    batch.polygon('glass_came',q,-.007)
                    batch.polygon('glass_came',q,.007)

def aperture(batch,shape,bounds,family,rng,light=0):
    if area(shape)<0:shape=list(reversed(shape))
    batch.ring(shape,bounds)
    glass(batch,shape,family,rng,light)
    batch.counts['apertures']+=1

def registers(batch,z0,z1,width,family,rng,rows=3,light=0):
    x0=-width/2;cols=6 if width<7 else 8;cw=width/cols;rh=(z1-z0)/rows
    for row in range(rows):
        b=z0+row*rh
        for col in range(cols):
            a=x0+col*cw;cx=a+cw/2
            split=b+rh*.71
            shape=capsule(cx,b+.11,cw*.57,rh*.62)
            aperture(batch,shape,rect(a,a+cw,b,split),family,rng,light+row*.035)
            shape=ellipse(cx,split+(b+rh-split)*.5,cw*.275,min(cw*.29,(b+rh-split)*.36),28)
            aperture(batch,shape,rect(a,a+cw,split,b+rh),family,rng,light+row*.035+.05)

def rose(batch,zc,width,height,family,rng,light=0):
    r=min(height*.465,width*.305);cx=0
    outer=ellipse(cx,zc,r,r,96)
    batch.ring(outer,rect(-width/2,width/2,zc-height/2,zc+height/2))
    # Round core, twelve leaf-shaped radial panes, with genuine solid stone ribs.
    aperture(batch,ellipse(0,zc,r*.20,r*.20,32),ellipse(0,zc,r*.27,r*.27,48),family,rng,light+.08)
    n=12
    for k in range(n):
        a=2*pi*k/n;delta=pi/n
        boundary=[(r*.235*cos(a-delta),zc+r*.235*sin(a-delta))]
        boundary += [(r*cos(a-delta+2*delta*j/8),zc+r*sin(a-delta+2*delta*j/8)) for j in range(9)]
        boundary += [(r*.235*cos(a+delta),zc+r*.235*sin(a+delta))]
        # Long oval petals, not Gothic tracery. Their mild taper is supplied by
        # an original convex lens outline fitted between radial stone webs.
        center=(r*.61*cos(a),zc+r*.61*sin(a))
        shape=ellipse(center[0],center[1],r*.31,r*.125,32,a)
        aperture(batch,shape,boundary,family,rng,light+.08)

def side_window(spec,H,M,index):
    rng=random.Random(6801+index*101);batch=Batch(spec)
    family='cool' if spec['side']>0 else ('warm' if spec['side']<0 else 'gold')
    width=spec['width'];bot=spec['z_bottom'];top=spec['z_top']
    registers(batch,bot,11.55,width,family,rng,rows=3,light=.015)
    rose(batch,13.35,width,3.6,family,rng,.07)
    # A solid separation concealed by the gallery floor and parapet.
    for d in (-.18,.18):batch.polygon('stone_light',rect(-width/2,width/2,15.15,18.05),d)
    registers(batch,18.05,23.85,width,family,rng,rows=2,light=.29)
    # Upper window light is less saturated. Only central nave clerestory is clear.
    rose(batch,25.70,width,3.7,family,rng,.39)
    # Inset taper shoulders so our panel fits interior's wall envelope exactly.
    # Upper corners are stone, never stray coloured panes outside the opening.
    if top>27.55:
        for d in (-.18,.18):batch.polygon('stone_light',rect(-1.90,1.90,27.55,top),d)
    batch.finish(H,M)
    return batch.counts

def photo_aperture(batch,shape,bounds,source_shape,image_size,key,angle_delta=0,mapping='radial',source_basis=None):
    """Map an unchanged licensed photograph only over the individual glass hole.
    A triangle fan explicitly maps the aperture centre as well as its perimeter;
    the stone remains 3D geometry and is not photo-projected.
    """
    if isinstance(source_shape,dict):
        # Optional per-aperture rectification for strongly oblique photographs.
        # Existing list-form photographed banks follow the unchanged path.
        source_basis=source_shape.get('projection_basis',source_basis)
        source_shape=source_shape['polygon']
    if area(shape)<0:shape=list(reversed(shape))
    batch.ring(shape,bounds)
    src=[(p[0],-p[1]) for p in source_shape]
    if area(src)<0:src.reverse()
    center=((min(p[0] for p in shape)+max(p[0] for p in shape))/2,(min(p[1] for p in shape)+max(p[1] for p in shape))/2)
    sc=((min(p[0] for p in src)+max(p[0] for p in src))/2,(min(p[1] for p in src)+max(p[1] for p in src))/2)
    w,h=image_size
    basis_data=None
    if source_basis:
        # The two projected architectural directions need not be perpendicular
        # in an oblique photograph. Remove that skew before fitting each hole;
        # otherwise a narrow slanted source pane would smear into diagonal bands.
        U,V=source_basis;det=U[0]*V[1]-U[1]*V[0]
        coords=[]
        for q in src:
            dx=q[0]-sc[0];dy=q[1]-sc[1]
            coords.append(((dx*V[1]-dy*V[0])/det,(U[0]*dy-U[1]*dx)/det))
        u0,u1=min(q[0] for q in coords),max(q[0] for q in coords)
        v0,v1=min(q[1] for q in coords),max(q[1] for q in coords)
        sc=(sc[0]+U[0]*(u0+u1)/2+V[0]*(v0+v1)/2,sc[1]+U[1]*(u0+u1)/2+V[1]*(v0+v1)/2)
        mx=max(p[0] for p in shape)-min(p[0] for p in shape)
        mz=max(p[1] for p in shape)-min(p[1] for p in shape)
        basis_data=(U,V,(u1-u0)/max(mx,1e-5),(v1-v0)/max(mz,1e-5))
    uv=[]
    for i,p in enumerate(shape):
        if basis_data:
            U,V,sx,sz=basis_data;dx=(p[0]-center[0])*sx;dz=(p[1]-center[1])*sz
            d=(U[0]*dx+V[0]*dz,U[1]*dx+V[1]*dz)
            q=rayhit(sc,d,src);uv.append((q[0]/w,1+q[1]/h));continue
        if mapping=='capsule' and len(shape)==len(src):
            q=src[i];uv.append((q[0]/w,1+q[1]/h));continue
        d=sub(p,center);a=math.atan2(d[1],d[0])+angle_delta
        q=rayhit(sc,(cos(a),sin(a)),src);uv.append((q[0]/w,1+q[1]/h))
    uc=(sc[0]/w,1+sc[1]/h)
    for j in range(len(shape)):
        k=(j+1)%len(shape)
        batch.photopoly(key,[center,shape[j],shape[k]],[uc,uv[j],uv[k]])
    batch.counts['apertures']+=1;batch.counts['panes']+=1

def photographed_bank(batch,z0,z1,width,data,family):
    """A measured photograph's 55 glazed apertures: 3×6 capsules,18 small
    circles,2 triangular groups of3 large oculi,and12-petal flower+centre.
    Panel artwork is exact photographed content; metric spacing is approximate.
    """
    height=z1-z0;key='glass_photo_'+family;size=data['image_size']
    bankwidth=width*.90
    xs=[v*bankwidth for v in (-.45,-.30,-.15,.15,.30,.45)]
    bounds=[-width/2]+[(xs[i]+xs[i+1])/2 for i in range(5)]+[width/2]
    row_info=[(0,.172,.007,.114,.143),(.172,.360,.182,.128,.335),(.360,.595,.378,.149,.559)]
    for row,(low,high,b,h,cc) in enumerate(row_info):
        for col,x in enumerate(xs):
            split=z0+height*(cc-.027)
            target=capsule(x,z0+b*height,bankwidth*.090,h*height,32)
            photo_aperture(batch,target,rect(bounds[col],bounds[col+1],z0+low*height,split),data['caps'][row][col],size,key,mapping='capsule',source_basis=data.get('projection_basis'))
            r=min(bankwidth*.044,height*.023)
            target=ellipse(x,z0+cc*height,r,r,48)
            photo_aperture(batch,target,rect(bounds[col],bounds[col+1],split,z0+high*height),data['circles'][row][col],size,key,source_basis=data.get('projection_basis'))
    # Two distinct triangular groups of larger medallions (absent from prototype).
    for group,sign in enumerate((-1,1)):
        groupx=sign*width*.25;left=-width/2 if sign<0 else 0;right=0 if sign<0 else width/2
        r=min(width*.061,height*.0285)
        for j in range(2):
            x=groupx+(j-.5)*width*.20;z=z0+height*.642
            outer=rect(left if j==0 else groupx,groupx if j==0 else right,z0+height*.595,z0+height*.672)
            photo_aperture(batch,ellipse(x,z,r,r,48),outer,data['large'][group*3+j],size,key,source_basis=data.get('projection_basis'))
        photo_aperture(batch,ellipse(groupx,z0+height*.704,r,r,48),rect(left,right,z0+height*.672,z0+height*.743),data['large'][group*3+2],size,key,source_basis=data.get('projection_basis'))
    # Photo-grounded radial 12-petal shape, fitted with a narrow inner stalk and
    # softly rounded outer bulb. Each source petal keeps its real artwork.
    zc=z0+height*.869;r=height*.121
    if r>width*.38:r=width*.38
    batch.ring(ellipse(0,zc,r,r,96),rect(-width/2,width/2,z0+height*.743,z1))
    rose_data=data.get('rose_source',data)
    rose_key=key+'_rose' if 'rose_source' in data else key
    rose_size=rose_data['image_size']
    core=rose_data['core'];sc=(sum(p[0] for p in core)/len(core),sum(p[1] for p in core)/len(core))
    # Oblique source images can push adjacent petals into the same rounded
    # sector. Require an explicit correction instead of silently leaving a
    # hole in both the glass and its enclosing stone.
    occupied=[]
    for i,source in enumerate(rose_data['petals']):
        pc=(sum(p[0] for p in source)/len(source),sum(p[1] for p in source)/len(source))
        a=math.degrees(math.atan2(sc[1]-pc[1],pc[0]-sc[0]))
        occupied.append(rose_data['petal_angles'][i] if 'petal_angles' in rose_data else round(a/30)*30)
    if sorted(round(a)%360 for a in occupied)!=list(range(0,360,30)):
        raise ValueError(f'{family}: rose petals must cover all twelve distinct sectors')
    photo_aperture(batch,ellipse(0,zc,r*.222,r*.222,48),ellipse(0,zc,r*.267,r*.267,48),core,rose_size,rose_key)
    for petal_index,source in enumerate(rose_data['petals']):
        pc=(sum(p[0] for p in source)/len(source),sum(p[1] for p in source)/len(source))
        sa=math.atan2(sc[1]-pc[1],pc[0]-sc[0]);a=round(sa/(pi/6))*(pi/6);delta=pi/12
        if 'petal_angles' in rose_data:a=math.radians(rose_data['petal_angles'][petal_index])
        outer=[(r*.235*cos(a-delta),zc+r*.235*sin(a-delta))]
        outer += [(r*cos(a-delta+2*delta*j/8),zc+r*sin(a-delta+2*delta*j/8)) for j in range(9)]
        outer += [(r*.235*cos(a+delta),zc+r*.235*sin(a+delta))]
        points=[]
        for j in range(48):
            t=2*pi*j/48;u=r*(.63+.335*cos(t));v=r*.133*sin(t)*(1+.40*cos(t))
            points.append((u*cos(a)-v*sin(a),zc+u*sin(a)+v*cos(a)))
        photo_aperture(batch,points,outer,source,rose_size,rose_key,sa-a)

def photo_side_window(spec,H,M,index,data):
    # Root applies one global Y reflection (x unchanged) to orient actual east/
    # west correctly. A viewer inside faces final -Y at the Nativity glazing;
    # its entire bank must therefore run in -X to keep names and pane order
    # readable, while the Passion bank runs +X. This is a bank-level reversal,
    # never a texture flip inside individual panes.
    if spec['side']>0:
        spec=dict(spec);spec['tangent']=tuple(-v for v in spec['tangent'])
    batch=Batch(spec);batch.relief=True;family='east' if spec['side']>0 else 'west'
    # Preserve source-supported relative progression while admitting the
    # unresolved absolute bay positions and repeated upper-level placement.
    bay_index=int(round((spec['center'][0]-3.75)/7.5))
    candidate=PHOTO_BANK_LAYOUT[family][max(0,min(4,bay_index))]
    if candidate in data:family=candidate
    photographed_bank(batch,spec['z_bottom'],15.15,spec['width'],data[family],family)
    for d in (-.18,.18):batch.polygon('stone_light',rect(-spec['width']/2,spec['width']/2,15.15,18.05),d)
    photographed_bank(batch,18.05,spec['z_top']-.10,spec['width'],data[family],family)
    batch.finish(H,M);return batch.counts

def clerestory(spec,H,M,index,gold=False):
    rng=random.Random(27001+index);batch=Batch(spec);w=spec['width']
    b=spec['z_bottom'];top=spec['z_top'];family='gold' if gold else 'clear'
    cols=3;cw=w/cols
    for i in range(cols):
        x=-w/2+i*cw;cx=x+cw/2
        shape=capsule(cx,b+.16,cw*.72,top-b-.32,24)
        aperture(batch,shape,rect(x,x+cw,b,top),family,rng,.60 if gold else .2)
    batch.finish(H,M);return batch.counts

def build(ctx):
    H=ctx['H'];M=ctx['M']
    import interior
    H.collection('Glazing_Original_Abstract')
    totals={'panes':0,'apertures':0}
    windows=getattr(interior,'WINDOWS',[])
    import json
    from pathlib import Path
    path=Path(ctx['root'])/'assets/textures/window_banks.json'
    photo_data=json.loads(path.read_text()) if path.exists() else None
    if not windows:raise RuntimeError('interior.WINDOWS must be ready before glazing.build')
    for i,spec in enumerate(windows):
        if spec.get('kind') in ('clerestory','apse_upper'):
            counts=clerestory(spec,H,M,i,gold=spec.get('kind')=='apse_upper')
        elif photo_data and spec.get('kind')=='side':
            counts=photo_side_window(spec,H,M,i,photo_data)
        else:counts=side_window(spec,H,M,i)
        for k in totals:totals[k]+=counts[k]
    print('GLAZING_STATS',totals)
    return totals
