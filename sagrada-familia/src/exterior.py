"""Sagrada Familia exterior, reconstruction at evidence cutoff 2026-09-22.
Geometry is authored here; seven named sculpture groups use licensed masked
photographs on estimated-depth reliefs, with attribution in EXTERIOR_EVIDENCE.json.
Dimensions between official anchors are photo-derived approximations. Relief depth
and unseen sculpture surfaces are interpreted, not measured or photogrammetric.
"""
import math, random
from math import sin, cos, pi, sqrt
from mathutils import Vector

class Batch:
    """Collect little carved forms into one editable mesh per architectural zone."""
    def __init__(self,H,name,mat): self.H,self.name,self.mat,self.v,self.f=H,name,mat,[],[]
    def add(self,v,f):
        n=len(self.v);self.v.extend(v);self.f.extend(tuple(n+i for i in face) for face in f)
    def ellipsoid(self,c,s,segments=8,rings=5,phase=0):
        v=[]
        for j in range(rings+1):
            a=pi*j/rings
            for i in range(segments):
                b=2*pi*i/segments+phase
                v.append((c[0]+s[0]*sin(a)*cos(b),c[1]+s[1]*sin(a)*sin(b),c[2]+s[2]*cos(a)))
        self.add(v,[(j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i) for j in range(rings) for i in range(segments)])
    def box(self,c,s):
        x,y,z=c;a,b,d=[u/2 for u in s]
        self.add([(x+i*a,y+j*b,z+k*d) for i,j,k in [(-1,-1,-1),(-1,1,-1),(1,1,-1),(1,-1,1),(-1,-1,1),(-1,1,1),(1,1,1),(1,-1,1)]],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
    def carved_leaf(self,c,length,width,depth,angle=0,phase=0):
        """Authored curled, lobed stone foliage; not an identified sculptor's leaf.

        Continuous ridged surfaces replace faceted bead chains. Fine relief is
        interpretation of the facade's organic carving, not a copied sculpture.
        """
        v=[];rows=9;cols=5;along=(sin(angle),cos(angle));side=(cos(angle),-sin(angle))
        for back in (False,True):
            for j in range(rows):
                t=.015+.97*j/(rows-1);wave=sin(pi*t);reach=(t-.5)*length
                half=width*wave**.72*(.83+.17*cos(t*pi*6+phase))
                curl=.12*length*sin(t*pi*1.35+phase*.3)*wave
                for k in range(cols):
                    s=-1+2*k/(cols-1);across=s*half
                    raised=depth*wave*(.30+.70*(1-s*s))+.10*depth*sin(t*pi*5+phase)*abs(s)
                    yy=-.035 if back else raised
                    v.append((c[0]+along[0]*reach+side[0]*(across+curl),c[1]+yy,c[2]+along[1]*reach+side[1]*(across+curl)))
        n=rows*cols;f=[]
        for j in range(rows-1):
            for k in range(cols-1):
                a=j*cols+k;b=a+1;d=a+cols;cc=d+1
                f.extend([(a,d,cc,b),(a+n,b+n,cc+n,d+n)])
        boundary=list(range(cols))+[j*cols+cols-1 for j in range(1,rows)]+list(range(n-2,n-cols-1,-1))+[j*cols for j in range(rows-2,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):f.append((a,b,b+n,a+n))
        self.add(v,f)
    def finish(self,smooth=False):
        obj=self.H.mesh(self.name,self.v,self.f,self.mat) if self.v else None
        if obj and smooth:
            for polygon in obj.data.polygons:polygon.use_smooth=True
        return obj

def profile(H,name,c,levels,mat,sides=32,phase=0,close=True,twist=0):
    v=[]
    for j,(z,r) in enumerate(levels):
        v.extend((c[0]+r*cos(2*pi*i/sides+phase+twist*j/(len(levels)-1)),c[1]+r*sin(2*pi*i/sides+phase+twist*j/(len(levels)-1)),z) for i in range(sides))
    f=[(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(len(levels)-1) for i in range(sides)]
    if close:f.extend([tuple(reversed(range(sides))),tuple((len(levels)-1)*sides+i for i in range(sides))])
    return H.mesh(name,v,f,mat)

def spiky_star(H,name,c,r,mat,edge=None):
    """Twelve pentagonal rays, on the twelve directions of an icosahedron."""
    g=(1+sqrt(5))/2; directions=[]
    for a in (-1,1):
        for b in (-g,g): directions.extend([Vector((0,a,b)),Vector((a,b,0)),Vector((b,0,a))])
    v=[];f=[]
    for direction in directions:
        d=direction.normalized();ref=Vector((0,0,1)) if abs(d.z)<.95 else Vector((1,0,0));u=d.cross(ref).normalized();w=d.cross(u)
        n=len(v);v.append(tuple(Vector(c)+d*r))
        for k in range(5):v.append(tuple(Vector(c)+d*r*.20+(u*cos(2*pi*k/5)+w*sin(2*pi*k/5))*r*.26))
        for k in range(5):
            f.append((n,n+1+k,n+1+(k+1)%5))
            if edge:H.beam(name+'_seam',v[n],v[n+1+k],r*.011,edge,8)
    return H.mesh(name,v,f,mat)

def ribbon(H,name,points,width,depth,mat):
    """Stone edge in a facade plane; rectangular section gives cut arrises."""
    v=[]
    for i,p in enumerate(points):
        t=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        t.normalize();n=Vector((-t.z,0,t.x))*width/2
        for y,q in [(-depth/2,-n),(-depth/2,n),(depth/2,n),(depth/2,-n)]:v.append(tuple(Vector(p)+q+Vector((0,y,0))))
    f=[]
    for i in range(len(points)-1):
        for k in range(4):f.append((4*i+k,4*i+(k+1)%4,4*(i+1)+(k+1)%4,4*(i+1)+k))
    f.extend([(3,2,1,0),tuple(4*(len(points)-1)+k for k in range(4))]);return H.mesh(name,v,f,mat)

def niche_figure(H,batch,name,x,y,z,height,angular=False,pose=0):
    # Non-iconographic human relief massing: face/detail intentionally not invented.
    w=height*.19
    if angular:
        batch.add([(x-w,y-.18,z),(x+w,y-.18,z),(x+w*.7,y+.40,z),(x-w*.7,y+.40,z),(x-w*.72,y-.05,z+height*.71),(x+w*.7,y-.04,z+height*.67),(x+w*.48,y+.35,z+height*.68),(x-w*.6,y+.35,z+height*.73)],[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7),(0,3,2,1)])
        batch.ellipsoid((x,y,z+height*.88),(w*.65,w*.7,height*.14),5,3,phase=.3)
    else:
        batch.ellipsoid((x,y,z+height*.42),(w,height*.15,height*.42),10,7)
        batch.ellipsoid((x,y-.08,z+height*.86),(w*.64,w*.63,height*.135),10,6)
    for s in (-1,1):
        end=(x+s*w*1.1,y-.12,z+height*(.41+.16*(pose==s)))
        H.beam(name+'_arm',(x+s*w*.55,y,z+height*.66),end,height*.055,batch.mat,8)

def apostle_tower(H,M,c,height,label,old=False):
    stone=M.get('nativity_stone',M['stone']) if old else M['stone_light']
    light=M.get('nativity_stone_detail',M['stone_light']) if old else M['stone_light']
    H.collection('Exterior_'+label)
    x,y=c; top=height-14.2
    def r(z):
        t=max(0,min(1,(z-18)/(top-18)))
        return 4.10*(1-t)**.61+.83
    ribs=12 if old else 14
    # Solid masonry belfry foot. Narrow slit windows are actual openings;
    # the great majority of this mass is stone, unlike an exposed rib cage.
    for za,zb,open_slot in [(0,7.5,False),(7.5,12,False),(12,26,True),(26,32,False),(32,43,True)]:
        for k in range(ribs):
            a=2*pi*k/ribs;b=2*pi*(k+1)/ribs
            if za==0 and abs(x-52.5)<5 and (cos((a+b)/2)*(52.5-x))>1.8:continue
            strips=[(0,.38),(.62,1)] if open_slot else [(0,1)]
            for u0,u1 in strips:
                aa=a+(b-a)*u0;bb=a+(b-a)*u1
                def pos(z,t,offset=0):
                    # Nativity square-derived lower section; Passion elliptical plan.
                    rr=r(z)+offset
                    if old:rr*=1+.12*(1-min(z/43,1))*(1/max(abs(cos(t)),abs(sin(t)))-1)
                    return (x+rr*cos(t)*(1 if old else .95),y+rr*sin(t)*(1 if old else 1.06),z)
                vv=[pos(za,aa),pos(za,bb),pos(zb,bb),pos(zb,aa),pos(za,aa,-.48),pos(za,bb,-.48),pos(zb,bb,-.48),pos(zb,aa,-.48)]
                H.mesh(label+'_thick_lower_masonry_with_slits',vv,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(2,6,7,3),(0,3,7,4),(1,5,6,2)],stone)
            if open_slot:
                # Small sloping wedge closes each slit at a pointed head.
                am=(a+b)/2;rw=r(zb)
                H.mesh(label+'_slit_pointed_head',[(x+rw*cos(a+(b-a)*.38),y+rw*sin(a+(b-a)*.38),zb-1.2),(x+rw*cos(am),y+rw*sin(am),zb),(x+rw*cos(a+(b-a)*.62),y+rw*sin(a+(b-a)*.62),zb-1.2)],[(0,1,2)],stone)
    # Broad tower foot with real slit openings between masonry piers.
    for i in range(ribs):
        a=2*pi*i/ribs
        bottom=7.5 if abs(x-52.5)<5 and cos(a)*(52.5-x)>1.8 else 3
        pts=[(x+r(z)*cos(a),y+r(z)*sin(a),z) for z in [bottom,15,28,38,49,60,72,top]]
        # Massive lower mullions thin upward. Mesh rib rectangular radially.
        vs=[]
        for j,p in enumerate(pts):
            tang=.25 if j>3 else (.58 if j<2 else .38);rad=.65
            for q,b in [(-tang,-rad),(tang,-rad),(tang,rad),(-tang,rad)]:vs.append((p[0]+q*-sin(a)+b*cos(a),p[1]+q*cos(a)+b*sin(a),p[2]))
        fs=[(j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k) for j in range(len(pts)-1) for k in range(4)]
        H.mesh(label+'_continuous_stone_rib',vs,fs,stone)
    # Lower drum uses arch-headed slit panels; upper belfry a dense sequence of real louvres.
    for z in [8,17,26,35,43]:
        profile(H,label+'_masonry_belt',c,[(z,r(z)+.05),(z+1.5,r(z+1.5)+.04)],stone,48,close=False)
    for i in range(int((top-43)/1.12)):
        z=43+i*1.12;rr=r(z)
        # Each annular sloping sound louvre has thickness, inner underside and open slot above.
        vv=[]
        for zz,rad in [(z,rr+.13),(z+.32,rr-.04),(z+.61,rr-.66),(z+.30,rr-.72)]:vv.extend((x+rad*cos(2*pi*k/48),y+rad*sin(2*pi*k/48),zz) for k in range(48))
        ff=[(j*48+k,j*48+(k+1)%48,((j+1)%4)*48+(k+1)%48,((j+1)%4)*48+k) for j in range(4) for k in range(48)]
        H.mesh(label+'_open_sound_louvre_%02d'%i,vv,ff,stone)
    # Long lancet buttress edges across lower zones produce very deep shadows.
    for k in range(8):
        a=2*pi*k/8;rr=r(24)+.65
        H.beam(label+'_lancet_edge',(x+rr*cos(a),y+rr*sin(a),8),(x+(r(39)+.35)*cos(a),y+(r(39)+.35)*sin(a),39),.18,light)
    # Apostolic pinnacles: twisted polychrome mitre, gold crozier eye and white beads.
    profile(H,label+'_mosaic_stem',c,[(top-.2,1.05),(top+2.4,1.6),(top+5.8,.58),(top+9.6,.60)],M['mosaic_red'],8,twist=pi/4)
    for k in range(4):
        a=pi/4+k*pi/2
        H.curve(label+'_white_mitre_ridge',[(x+1.05*cos(a),y+1.05*sin(a),top),(x+1.65*cos(a+.2),y+1.65*sin(a+.2),top+2.5),(x+.65*cos(a),y+.65*sin(a),top+7.7),(x+.80*cos(a),y+.8*sin(a),top+11.3)],.13,M['ceramic_white'])
    H.torus(label+'_episcopal_gold_eye',(x,y,top+6.2),1.12,.34,M['mosaic_gold'],rotation=(pi/2,0,0),segments=24)
    # Mitre head, offset lobes clad in white ceramic and small golden cap.
    bs=Batch(H,label+'_mosaic_mitre_beads',M['ceramic_white'])
    for sign in (-1,1):
        for k in range(7):
            t=k/6;a=pi*t
            bs.ellipsoid((x+sign*(.25+1.15*sin(a)),y+.18*cos(a),top+8.8+4.0*t),(.34,.38,.42),10,6)
    bs.finish()
    profile(H,label+'_gold_mitre',c,[(top+9.2,.66),(height-.7,.9),(height,.17)],M['mosaic_gold'],6)
    # Small statues at bases of high belfries, visible from facade below.
    out=1 if y>0 else -1
    bx=x;by=y+out*(r(31)+.60)
    H.cube(label+'_statue_console',(bx,by,28.8),(2.0,1.0,.7),light)
    batch=Batch(H,label+'_apostle_relief',light);niche_figure(H,batch,label,bx,by,29.1,3.8,not old);batch.finish()

def panel_tower(H,M,name,c,z0,z1,r0,r1,sides=12,rows=12):
    """Tensioned stone panels with deep triangular/lozenge perforations, not cones."""
    H.collection('Exterior_'+name)
    x,y=c
    def radius(z):return r0+(r1-r0)*((z-z0)/(z1-z0))**.83
    for j in range(rows):
        low=z0+(z1-z0)*j/rows;high=z0+(z1-z0)*(j+1)/rows
        for k in range(sides):
            a=2*pi*k/sides;b=2*pi*(k+1)/sides
            # Each face has a tall triangular opening; alternating tip produces Gaudi's web.
            p=[Vector((x+radius(low)*cos(a),y+radius(low)*sin(a),low)),Vector((x+radius(low)*cos(b),y+radius(low)*sin(b),low)),Vector((x+radius(high)*cos(b),y+radius(high)*sin(b),high)),Vector((x+radius(high)*cos(a),y+radius(high)*sin(a),high))]
            center=sum(p,Vector())/4;t=(p[1]-p[0]).normalized();up=Vector((0,0,1));w=(p[1]-p[0]).length;h=high-low
            # Narrow hourglass/triangular apertures (official photos), generous stone corners.
            hole=[center-t*w*.24-up*h*.33,center+t*w*.24-up*h*.33,center+t*w*.075+up*h*.38,center-t*w*.075+up*h*.38]
            if (j+k)%2:hole=[Vector((q.x,q.y,2*center.z-q.z)) for q in hole][::-1]
            n=Vector((cos((a+b)/2),sin((a+b)/2),0))
            v=[tuple(q) for q in p+hole]+[tuple(q-n*.38) for q in p+hole]
            f=[]
            for l in range(4):
                m=(l+1)%4;f.extend([(l,m,4+m,4+l),(8+l,12+l,12+m,8+m),(4+l,4+m,12+m,12+l)])
            H.mesh(name+'_panel_%02d_%02d'%(j,k),v,f,M['stone_light'] if (j+k)%5==0 else M['stone'])
    # Pronounced vertical blade-buttresses taper to the crown.
    for k in range(sides):
        a=2*pi*k/sides
        H.curve(name+'_arris',[(x+(radius(z)+.15)*cos(a),y+(radius(z)+.15)*sin(a),z) for z in [z0,z0+(z1-z0)*.25,z0+(z1-z0)*.5,z0+(z1-z0)*.75,z1]],.16,M['stone_light'])
    for j in range(rows+1):
        z=z0+(z1-z0)*j/rows;rr=radius(z)
        profile(H,name+'_panel_joint',c,[(z-.07,rr+.06),(z+.09,rr+.06)],M['stone_dark'],sides,close=False)

def cross_arm(H,M,name,center,direction,length,radii):
    """Flared chamfered square arms matching the built white ceramic/glass cross."""
    d=Vector(direction);u=d.cross(Vector((0,1,0))) if abs(d.y)<.9 else d.cross(Vector((1,0,0)));u.normalize();w=d.cross(u)
    # Rounded concave flare is polygonally tessellated; diagonal valley panels are glass.
    sect=[(-1,-.66),(-.66,-1),(.66,-1),(1,-.66),(1,.66),(.66,1),(-.66,1),(-1,.66)]
    v=[];steps=9
    for j in range(steps):
        t=j/(steps-1);r=radii[0]+(radii[1]-radii[0])*(t*t)
        for a,b in sect:v.append(tuple(Vector(center)+d*length*t+u*a*r+w*b*r))
    fwhite=[];fglass=[]
    for j in range(steps-1):
        for k in range(8):
            face=(j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k)
            (fglass if k%2==0 and j>4 else fwhite).append(face)
    H.mesh(name+'_ceramic',v,fwhite,M['ceramic_white']);H.mesh(name+'_glazing',v,fglass,M['glass_white'])
    cap=[tuple(Vector(center)+d*length+u*a*radii[1]+w*b*radii[1]) for a,b in sect]
    H.mesh(name+'_glazed_end',cap,[tuple(range(8))],M['glass_white'])
    for k in range(8):H.beam(name+'_end_mullion',cap[k],cap[(k+1)%8],.075,M['ceramic_white'])
    # Surface triangular tile seams are real lightweight geometry, visually coherent up close.
    for j in range(1,steps):
        t=j/(steps-1);r=radii[0]+(radii[1]-radii[0])*t*t
        pts=[tuple(Vector(center)+d*length*t+u*a*(r+.015)+w*b*(r+.015)) for a,b in sect]
        H.curve(name+'_tile_course',pts,.013,M['stone_light'],cyclic=True)

def jesus(H,M):
    c=(52.5,0)
    panel_tower(H,M,'Jesus_lantern_base',c,60.5,85,12.0,9.9,12,5)
    panel_tower(H,M,'Jesus_twelve_panel_levels',c,85,142.5,9.9,3.2,12,12)
    H.collection('Exterior_Jesus_pinnacle_completed_20260220')
    profile(H,'Jesus_pinnacle_crown',c,[(141.8,3.3),(144,4.15),(145,2.55),(155.5,1.38)],M['mosaic_gold'],12,close=False)
    for i in range(12):
        a=2*pi*i/12
        pts=[(52.5+3.0*cos(a),3.0*sin(a),143),(52.5+2.15*cos(a+.06),2.15*sin(a+.06),149),(52.5+1.35*cos(a),1.35*sin(a),155.5)]
        H.curve('Jesus_white_ceramic_praise',pts,.22,M['ceramic_white'])
        for j in range(6):
            z=144+j*1.45;r=2.9-(z-144)*.11
            H.beam('Jesus_palm_frond',(52.5+r*cos(a),r*sin(a),z),(52.5+(r+.60)*cos(a+.20),(r+.60)*sin(a+.20),z+1.0),.09,M['mosaic_green'])
    center=(52.5,0,164.0)
    # 17m total from155.5 to172.5; horizontal terminal span13.5m.
    for axis in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0)]:cross_arm(H,M,'Jesus_four_arm',center,axis,6.75,(1.10,2.25))
    cross_arm(H,M,'Jesus_upper_arm',center,(0,0,1),8.5,(1.1,2.25))
    cross_arm(H,M,'Jesus_lower_arm',center,(0,0,-1),8.5,(1.1,1.85))
    # Interior construction scaffold, deliberately no visitor deck in the cross.
    H.collection('Construction_Jesus_interior_not_open')
    for x in [51.5,53.5]:
        for y in [-1,1]:H.beam('Interior_scaffold_upright',(x,y,86),(x,y,148),.07,M['scaffold'])
    for z in range(87,149,3):
        for y in [-1,1]:H.beam('Interior_scaffold_brace',(51.5,y,z),(53.5,y,z+2.8),.045,M['scaffold'])

def mary(H,M):
    c=(76,0)
    panel_tower(H,M,'Mary_completed2021',c,76,112.5,8.0,3.05,12,9)
    H.collection('Exterior_Mary_star')
    # Six stone legs gathering into three supporting arms; blue-white trencadis shaft.
    for k in range(6):
        a=2*pi*k/6
        H.curve('Mary_six_pinnacle_legs',[(76+3.0*cos(a),3.0*sin(a),112.5),(76+1.7*cos(a),1.7*sin(a),122),(76+1.0*cos(a+.2),1.0*sin(a+.2),128)],.31,M['ceramic_white'])
        for j in range(2):
            aa=a+j*pi/6;spiky_star(H,'Mary_crown_iron_star',(76+3.25*cos(aa),3.25*sin(aa),115.2),.65,M['iron'])
    profile(H,'Mary_pale_blue_white_trencadis_shaft',c,[(115,2.0),(119,1.68),(124,.85),(128,.6)],M['ceramic_white'],12,close=False)
    for k in range(3):
        a=2*pi*k/3
        H.curve('Mary_three_star_arms',[(76+.63*cos(a),.63*sin(a),126.5),(76+1.3*cos(a),1.3*sin(a),131.5),(76+.75*cos(a),.75*sin(a),133.5)],.24,M['ceramic_white'])
    spiky_star(H,'Mary_twelve_point_luminous_star',(76,0,134.511),4.1,M['glass_white'],M['iron'])

def evangelist(H,M,c,symbol):
    panel_tower(H,M,'Evangelist_'+symbol,c,64,114,5.0,1.95,8,11)
    H.collection('Exterior_Evangelist_'+symbol+'_completed2023')
    x,y=c
    profile(H,symbol+'_mosaic_pinnacle',c,[(113.5,2.0),(117,1.45),(122.8,.72)],M['mosaic_gold'],8)
    for k in range(4):
        a=k*pi/2
        H.curve(symbol+'_ceramic_pinnacle_rib',[(x+1.7*cos(a),y+1.7*sin(a),114),(x+1.1*cos(a),y+1.1*sin(a),119),(x+.6*cos(a),y+.6*sin(a),124)],.18,M['ceramic_white'])
    # Polyhedral gold symbol of the word, below the white winged tetramorph.
    profile(H,symbol+'_gold_polyhedron',c,[(122.3,.3),(124.0,1.85),(125.7,.3)],M['mosaic_gold'],4,phase=pi/4)
    H.cube(symbol+'_open_book',(x,y,126.6),(2.0,1.4,1.7),M['ceramic_white'])
    for s in (-1,1):
        v=[(x,y,127.4),(x+s*1.4,y-.5,127.1),(x+s*1.4,y+.5,127.1),(x,y+.4,127.65)]
        H.mesh(symbol+'_gospel_book_page',v,[(0,1,2,3)],M['ceramic_white'])
    bat=Batch(H,symbol+'_sculpture_massing',M['ceramic_white'])
    if symbol=='John_eagle':
        bat.ellipsoid((x,y,129.1),(.7,.95,1.4),10,6)
        bat.ellipsoid((x,y-.25,130.65),(.52,.63,.5),8,5)
        H.mesh('John_eagle_beak',[(x-.2,y-.6,130.7),(x+.2,y-.6,130.7),(x,y-1.25,130.35)],[(0,1,2)],M['ceramic_white'])
    elif symbol=='Matthew_man':
        niche_figure(H,bat,symbol,x,y,127.6,4.4,True)
    else:
        bat.ellipsoid((x,y,129.0),(1.3,.68,.8),10,6)
        bat.ellipsoid((x-1.0,y,130.0),(.7,.6,.67),8,5)
        for sx in (-.8,.7):
            for sy in (-.38,.38):H.beam(symbol+'_legs',(x+sx,y+sy,128.8),(x+sx-.18,y+sy,127.6),.19,M['ceramic_white'])
        if symbol=='Luke_bull':
            for sy in (-1,1):H.curve('Luke_horn',[(x-1.1,y+sy*.4,130.3),(x-1.1,y+sy*.8,130.8),(x-.8,y+sy*.9,131.15)],.12,M['ceramic_white'])
        else:
            for k in range(9):
                a=2*pi*k/9;bat.ellipsoid((x-1.0,y+.61*cos(a),130+.67*sin(a)),(.44,.29,.34),6,4)
    bat.finish()
    # Wings rise in vertical, serrated feather fans, not generic cross finials.
    for s in (-1,1):
        v=[(x+s*.5,y,128.1),(x+s*1.8,y+.2,131.0),(x+s*2.15,y+.15,135),(x+s*.75,y-.1,132.4)]
        H.mesh(symbol+'_wing',v,[(0,1,2,3)],M['ceramic_white'])
        for k in range(6):
            z=129.8+k*.72
            H.beam(symbol+'_wing_feather',(x+s*(.55+.1*k),y-.10,z),(x+s*(1.8+.055*k),y-.14,z+1.3),.18,M['ceramic_white'])

def nativity(H,M):
    H.collection('Exterior_Nativity_portals')
    stone=M.get('nativity_stone',M['stone']);detail=M.get('nativity_stone_detail',M['stone_light']);rnd=random.Random(103)
    # Deep continuous stone facade shares its structural mass with four tower feet.
    # The entries remain real openings through the 4m deep facade, never painted holes.
    for x,w,spring,rise in [(42.5,5.0,8.3,6.5),(52.5,14.0,10.0,14.0),(62.5,5.0,8.3,6.5)]:
        coords=H.point_arch(w,rise,28);nn=len(coords);vv=[]
        tip=39 if w>10 else 24
        for yy in [27.9,32.1]:
            for u,zz in coords:vv.append((x+u,yy,spring+zz))
            for u,zz in coords:
                top=spring+.9+(tip-spring-.9)*max(0,1-abs(u)/(w/2))**.68
                vv.append((x+u,yy,max(top,spring+zz+.65)))
        ff=[]
        for j in range(nn-1):ff.extend([(j,j+1,nn+j+1,nn+j),(2*nn+j,3*nn+j,3*nn+j+1,2*nn+j+1),(j,2*nn+j,2*nn+j+1,j+1),(nn+j,nn+j+1,3*nn+j+1,3*nn+j)])
        H.mesh('Nativity_continuous_carved_gable_mass',vv,ff,stone)
        for side in(-1,1):H.cube('Nativity_deep_carved_jamb',(x+side*(w/2+.4),30.0,spring/2),(.8,4.2,spring),stone)

    # Three sheltered ogival entrances. High facade does not occlude walking portals.
    for i,(x,w,spring,rise) in enumerate([(42.5,5.0,8.3,6.5),(52.5,14.0,10.,14.),(62.5,5.,8.3,6.5)]):
        for k in range(4):
            H.arch('Nativity_nested_carved_arch_%d_%d'%(i,k),(x,30.5+k*.30,0),w+1.08*k,spring,rise+.3*k,.40,1.1,stone,segments=22)
        for side in (-1,1):
            H.cylinder('Nativity_portal_shaft',(x+side*(w/2+.5),31.1,spring/2),.48,spring,stone,12)
            H.curve('Nativity_living_tree_column',[(x+side*(w/2+.65),31.5,.4),(x+side*(w/2+.3),31.7,3.4),(x+side*(w/2+.8),31.5,spring),(x+side*(w/2+.2),31.6,spring+3)],.26,detail)
    # Organic gables over portals, irregular stone lace in genuine depth.
    carve=Batch(H,'Nativity_carved_foliage_and_stone_lace',stone)
    flowers=Batch(H,'Nativity_highlight_leaf_carvings',detail)
    for center,width,base,top in [(42.5,9.0,10,24),(52.5,17.5,18,39),(62.5,9.,10,24)]:
        # Triangular stone gable thick side ribs, with porous center instead of solid triangles.
        for s in (-1,1):
            path=[]
            for j in range(48):
                t=j/47;x=center+s*width/2*(1-t)**.92;z=base+(top-base)*t
                path.append((x,32.65+.15*sin(t*11)+.06*sin(t*29),z))
                # Continuous slender woody moulding with occasional embedded
                # knots; no chain of uniform faceted boulders.
                if j%4==0:carve.ellipsoid((x,32.55,z),(.36,.30,.49),16,9)
                for branch in (-1,1):
                    angle=branch*(.55+rnd.random()*.4)-s*.16
                    flowers.carved_leaf((x+branch*rnd.uniform(.12,.40),32.98+rnd.uniform(-.10,.10),z+rnd.uniform(-.12,.18)),rnd.uniform(.72,1.08),rnd.uniform(.17,.25),rnd.uniform(.11,.19),angle,rnd.uniform(0,pi))
            H.curve('Nativity_continuous_organic_gable_stem',path,.31,stone,resolution=3)
        for j in range(115):
            z=rnd.uniform(base+2,top-1);frac=(top-z)/(top-base);x=center+rnd.uniform(-width*.48,width*.48)*frac
            # Retain the central aperture and portals. Foliage grows from a
            # sheltered shallow stone surface, not isolated polygonal pebbles.
            if abs(x-center)<1.7 and base+4<z<base+8:continue
            yy=32.0+rnd.random()*.55
            if j%3==0:carve.ellipsoid((x,yy-.08,z),(.32+rnd.random()*.23,.19,.36+rnd.random()*.28),14,8)
            flowers.carved_leaf((x,yy+.15,z),rnd.uniform(.65,1.15),rnd.uniform(.18,.32),rnd.uniform(.12,.22),rnd.uniform(-1.2,1.2),rnd.uniform(0,pi))
        for k in range(9):
            a=2*pi*k/9;flowers.carved_leaf((center+1.8*cos(a),32.98,base+6.3+1.8*sin(a)),.92,.27,.19,pi/2-a,a)
    carve.finish(smooth=True);flowers.finish(smooth=True)
    # Nativity Tree of Life: dark green cypress with white doves, iconic central silhouette.
    profile(H,'Nativity_Tree_of_Life',(52.5,32),[(34.8,1.65),(37,2),(40,1.5),(43,.9),(45.4,.12)],M['mosaic_green'],20)
    foliage=Batch(H,'Nativity_cypress_branches',M['mosaic_green']);doves=Batch(H,'Nativity_white_doves',M['ceramic_white'])
    for j in range(11):
        z=35.4+j*.83;r=1.7*(1-j/13)
        for k in range(7):
            a=2*pi*k/7+j*.57
            foliage.ellipsoid((52.5+r*cos(a),32+r*sin(a),z),(.38,.35,.75),7,4)
            if (j+k)%3==0:
                xx=52.5+(r+.25)*cos(a);yy=32+(r+.25)*sin(a)
                doves.ellipsoid((xx,yy,z),(.22,.13,.14),6,4)
                H.beam('Nativity_dove_wings',(xx-.4,yy,z+.15),(xx+.4,yy,z+.15),.065,M['ceramic_white'])
    foliage.finish();doves.finish()
    H.beam('Nativity_tree_cross_vertical',(52.5,32,45),(52.5,32,47.2),.16,M['bronze']);H.beam('Nativity_tree_cross_horizontal',(51.7,32,46.3),(53.3,32,46.3),.16,M['bronze'])
    # Flanking buttress/pier masses join tower bases without filling portal voids.
    for x in [37.0,46.5,58.5,68.0]:
        profile(H,'Nativity_organic_buttress',(x,29.2),[(0,1.5),(13,1.4),(24,.85),(33,.55)],stone,10)
        for z in range(3,31,3):
            for s in (-1,1):H.beam('Nativity_flying_stone_tendril',(x,30.0,z),(x+s*.8,30.6,z+2.3),.12,detail)
    # The central Charity opening is a double entrance divided by the carved
    # pillar bearing the Nativity capital (visible in the source photograph).
    # A5.9m background niche puts this group against carved stone rather than
    # exposing the belfry ribs and sky between them.
    profile(H,'Nativity_Charity_central_pier',(52.5,31.7),[(0,.72),(7.6,.67),(8.8,.90),(9.55,1.38),(9.8,1.34)],stone,16)
    # The capital carries the group through a recessed rounded support spine.
    # Do not surround a limited-view sculpture relief with a flat cutout board;
    # its unobserved back is kept behind the central mass and below the heads.
    profile(H,'Nativity_recessed_group_support_spine',(52.5,31.5),[(9.5,1.15),(11.4,1.1),(13.3,.86),(14.45,.42),(14.8,.08)],stone,24)
    # Project the portal sculpture in front of the broad belfry bases.

    # Surface coordinates are baked so the editable mesh/export share one datum.
    import bpy
    for obj in bpy.data.collections['Exterior_Nativity_portals'].objects:
        if obj.type=='MESH':
            for vert in obj.data.vertices:vert.co.y+=4.5

def passion(H,M):
    H.collection('Exterior_Passion_skeletal_portico')
    stone=M['stone_light']; y=-34.2
    for x,w,spring,rise in [(42.5,5,7,5),(52.5,14,10,14),(62.5,5,7,5)]:
        H.arch_wall('Passion_continuous_stone_backing',(x,-29.0,0),w,spring,rise,38,.5,3.4,M['stone'],base=0)
    # Six inclined branching bone columns. Tall triangular porch is two open tiers.
    bases=[37.8,43.5,49.1,55.9,61.5,67.2]
    for i,x in enumerate(bases):
        target=x+(52.5-x)*.22;top=19.5+(1-abs(target-52.5)/15)*9
        pts=[(x,y-1.6,0),(x+(target-x)*.38,y-1.0,8),(target,y,top)]
        # Sharply ridged quadrilateral bones, widening at the crown.
        v=[]
        for j,p in enumerate(pts):
            w=[.46,.60,1.15][j];d=[.67,.5,.86][j]
            v.extend([(p[0]-w,p[1],p[2]),(p[0],p[1]-d,p[2]),(p[0]+w,p[1],p[2]),(p[0],p[1]+d,p[2])])
        H.mesh('Passion_inclined_bone_column',v,[(j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k) for j in range(2) for k in range(4)],stone)
    lower=[(35.5,y,18.3),(52.5,y,30.8),(69.5,y,18.3)]
    upper=[(36.8,y+.35,25),(52.5,y+.35,40.5),(68.2,y+.35,25)]
    ribbon(H,'Passion_lower_sharp_pediment',lower,.72,1.4,stone)
    ribbon(H,'Passion_upper_pediment',upper,.75,1.45,stone)
    # Ribbed upper colonnade follows triangular roof, with 18 bone-like open supports.
    for i in range(19):
        x=37.8+i*(29.4/18);rel=abs(x-52.5)/17
        zlo=30.8-12.5*rel;zhi=40.5-16.8*rel
        pts=[(x,y+.3,zlo),(x+.25*(52.5-x)/15,y+.1,(zlo+zhi)/2),(x,y+.3,zhi)]
        H.curve('Passion_upper_bone_colonnade',pts,.21,stone)
        # Stepped ridge parapet on sloping tympanum.
        H.cube('Passion_stepped_cornice',(x,y+.2,zhi+.35),(1.12,.82,.55),stone)
    # Concave hollow behind open portico. Actual openings remain at ground level.
    for x,w,spring,rise in [(42.5,5,7,5),(52.5,14,10,14),(62.5,5,7,5)]:
        H.arch('Passion_inner_portal',(x,-29.8,0),w,spring,rise,.65,1.2,M['stone'],segments=14)
    # Crucifixion is central under canopy; faceted high cross over pediment, 2018 completion.
    H.beam('Passion_crucifixion_cross',(52.5,-32.0,23),(52.5,-32.0,29),.20,M['stone_dark'])
    H.beam('Passion_crucifixion_arms',(50.6,-32.0,27.6),(54.4,-32.0,27.6),.20,M['stone_dark'])
    H.beam('Passion_high_cross',(52.5,-30.2,40.8),(52.5,-30.2,47),.28,stone)
    H.beam('Passion_high_cross_arms',(50.4,-30.2,44.4),(54.6,-30.2,44.4),.28,stone)
    H.mesh('Passion_back_pyramid',[(48,-29,39),(57,-29,39),(52.5,-28.5,54.2),(52.5,-31,44)],[(0,1,3),(1,2,3),(2,0,3)],stone)

def portal_weather_backing(H,M,colliders):
    """Minimal inferred enclosure behind the two ornamental transept fronts.

    The outer sculptural arches rise to24m but are not open-air holes through
    the basilica. V9ray audit found a sightline straight to sky because the
    interior module's existing end header begins at30.1m. Plain inner backing
    bridges that gap; detailed unseen glazing/layout remains unverified.
    Source coordinates deliberately bypass the Nativity ornament's+4.5m offset.
    """
    H.collection('Exterior_transept_inner_weather_backing_inferred')
    for side,name,outside in (
        (1,'Nativity',M.get('nativity_stone',M['stone'])),
        (-1,'Passion',M['stone'])):
        wall=H.cube(name+'_inner_weather_backing_above_entrance_clearance',
                    (52.5,side*29.85,20.25),(30.0,.80,20.50),M['stone_light'])
        # Ground0..10m stays untouched. Top30.5 overlaps the existing30.1m
        # end header, while the shallow layer remains behind exterior sculpture.
        wall.data.materials.append(outside)
        wall.data.polygons[3 if side>0 else 5].material_index=1
        wall['reconstruction']='Inferred plain inner weather enclosure; exact as-built inner-wall/window arrangement unresolved. No new ornamental artwork.'
        wall['entrance_clearance_m']=10.0
        # Normal walk physics matches the visible above-door weather layer.
        # Inspection flight keeps its existing noclip behavior.
        colliders.append(dict(type='box',
            name=name+'_inner_weather_backing_above_entrance_clearance',
            center=(52.5,side*29.85,20.25),size=(30.0,.80,20.50),
            walkable_floor=False))


def roofs(H,M):
    H.collection('Exterior_nave_roof_geometries')
    stone=M['stone_light']
    # External saddle roof segments preserve every interior ceiling volume.
    for x0 in [0,7.5,15,22.5,30]:
        for sy in (-1,1):
            for ya,yb,zlo,zhi in [(0,7.5,46.3,53.2),(7.5,15,31.3,35.1),(15,22.5,31.3,33.4)]:
                v=[(x0,sy*ya,zlo),(x0+7.5,sy*ya,zlo),(x0+7.5,sy*yb,zlo),(x0,sy*yb,zlo),(x0+3.75,sy*(ya+yb)/2,zhi)]
                H.mesh('Gaudi_ruled_roof_saddle',v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],M['stone'])
                for a,b in [(0,4),(1,4),(2,4),(3,4)]:H.beam('Roof_geometric_rib',v[a],v[b],.15,stone)
    # Geometric side nave crowns and polychrome fruit, documented in official gallery.
    fruit_colors=[M['mosaic_red'],M['mosaic_gold'],M['mosaic_green']]
    for sy in (-1,1):
        for i,x in enumerate([3.75,11.25,18.75,26.25,33.75]):
            y=sy*22.85
            # Triangular stone wall with a true circular oculus, substantial folded gable.
            vv=[];nseg=40;zc=34.4
            # Project rays from the circular opening to the triangular perimeter.
            tri=[Vector((-3.73,28.5-zc)),Vector((3.73,28.5-zc)),Vector((0,42.0-zc))]
            def cross2(a,b):return a.x*b.y-a.y*b.x
            for k in range(nseg):
                a=2*pi*k/nseg;d=Vector((cos(a),sin(a)));hits=[]
                for m in range(3):
                    p0=tri[m];edge=tri[(m+1)%3]-p0;den=cross2(d,edge)
                    if abs(den)>1e-7:
                        t=cross2(p0,edge)/den;u=cross2(p0,d)/den
                        if t>0 and 0<=u<=1:hits.append(t)
                ro=min(hits) if hits else 3.7
                vv.extend([(x+1.35*cos(a),y,zc+1.35*sin(a)),(x+ro*cos(a),y,zc+ro*sin(a))])
            H.mesh('Nave_solid_triangular_crown',vv,[(2*k,2*k+1,2*((k+1)%nseg)+1,2*((k+1)%nseg)) for k in range(nseg)],M['stone'])
            for s in (-1,1):ribbon(H,'Nave_crown_parabolic_ridge',[(x+s*3.6,y,28.6),(x+s*1.7,y,34.0),(x,y,40.7)],.42,.5,stone)
            H.torus('Nave_upper_oculus',(x,y,34.4),1.35,.22,stone,rotation=(pi/2,0,0),segments=24)
            for k in range(8):
                a=2*pi*k/8;H.beam('Nave_oculus_radiant',(x+1.6*cos(a),y,34.4+1.6*sin(a)),(x+2.5*cos(a),y,34.4+2.5*sin(a)),.18,stone)
            profile(H,'Fruit_pinnacle_base',(x,y),[(39.8,.62),(43,.36),(45,.44)],stone,8)
            fruit=Batch(H,'Ceramic_fruit_cluster',fruit_colors[(i+(sy>0))%3])
            for row in range(4):
                num=5-row
                for j in range(num):
                    a=2*pi*j/num+row*.5;r=.6*(1-row/5)
                    fruit.ellipsoid((x+r*cos(a),y+r*sin(a),44.7+row*.57),(.36,.36,.4),10,6)
            fruit.finish()
    # Crossing terraces enclose lantern bases; leave the interior crossing60m unobstructed.
    for sy in (-1,1):
        H.mesh('Transept_ruled_roof',[(37.5,sy*7.5,61),(67.5,sy*7.5,61),(67.5,sy*25,39),(37.5,sy*25,39),(52.5,sy*18,53)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],M['stone'])
    # Apse seven external chapel buttresses, genuine semi-circular eastern termination.
    for k in range(8):
        a=-pi/2+k*pi/7;x=67.5+23.25*cos(a);y=23.25*sin(a)
        profile(H,'Apse_exterior_buttress',(x,y),[(0,.85),(17,.75),(29,.6),(37,.22)],M['stone'],8)
        profile(H,'Apse_buttress_pinnacle',(x,y),[(36.5,.35),(40,.55),(43,.08)],stone,8)
    # High apse roof (not a dome under the internally visible75m crown).
    profile(H,'Apse_crown_roof',(76,0),[(75.8,8.0),(77.0,6.5)],M['stone'],24,close=False)

def construction(H,M):
    H.collection('Construction_Glory_as_of_20260922')
    # Current entrance wall / basement stage; explicitly no completed future Glory towers.
    # Side piers flank a clear 14m portal on x0; temporary upper work platform at28m.
    for y in [-18.5,-11.0,11.0,18.5]:
        H.cube('Glory_current_support',(0,y,11.5),(2.4,2.0,23),M['concrete'])
        H.cube('Glory_in_progress_top',(-1,y,25.0),(3.7,3.3,3.2),M['stone_light'])
        for dx in (-1,1):H.beam('Glory_exposed_reinforcement',(dx*.65,y,25),(dx*.65,y,28.2),.06,M['iron'])
    # Existing weather closure is visible in Canaan's2022-04-30 frontal photo:
    # concrete flanks, three stacked faceted glazed bays and a closed door screen.
    # This is the already-built envelope, not the future Glory sculpture design.
    import bpy
    glass=bpy.data.materials.new('Glory_existing_frosted_teal_weather_glass');glass.use_nodes=True
    bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.21,.34,.33,1);bs.inputs['Roughness'].default_value=.38;bs.inputs['Metallic'].default_value=.08
    door=bpy.data.materials.new('Glory_existing_closed_teal_entrance');door.use_nodes=True
    bs=door.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.018,.058,.054,1);bs.inputs['Roughness'].default_value=.73
    for side in (-1,1):
        # Flanks close the full nave width below the aisle roof. Narrow slits
        # have solid frosted infill; they are not open views to interior seating.
        for ya,yb,zt in [(4.35,7.5,45),(7.5,15,32.5),(15,22.5,30.8)]:
            yc=side*(ya+yb)/2;H.cube('Glory_existing_raw_concrete_flank',(-.46,yc,zt/2),(1.0,yb-ya,zt),M['concrete'])
        for yc,zc in [(side*10.6,22.0),(side*18.5,13.5)]:
            H.cube('Glory_narrow_frosted_slit',(-1.001,yc,zc),(.065,1.18,3.4),glass)
            for yy in (yc-.68,yc+.68):H.cube('Glory_slit_stone_reveal',(-1.16,yy,zc),(.4,.18,3.8),M['stone'])
            for zz in (zc-1.86,zc+1.86):H.cube('Glory_slit_stone_lintel',(-1.17,yc,zz),(.42,1.52,.22),M['stone'])
    H.cube('Glory_existing_closed_entrance_screen',(-.76,0,2.0),(.30,8.7,4.0),door)
    for y in (-4.35,-2.2,0,2.2,4.35):H.cube('Glory_door_screen_frame',(-.95,y,2),(.12,.12,4),M['iron'])
    # Straight mullions follow the photographed faceted glass wall. Captured
    # dimensions are approximated; the three-bay composition is photographic.
    for z0,z1 in [(4.8,15.2),(16.0,27.5),(28.4,44.7)]:
        cross=[(-4.35,-.66),(-3.55,-1.47),(3.55,-1.47),(4.35,-.66)]
        for k in range(3):
            ya,xa=cross[k];yb,xb=cross[k+1]
            H.mesh('Glory_existing_frosted_glazed_bay',[(xa,ya,z0),(xb,yb,z0),(xb,yb,z1),(xa,ya,z1)],[(0,1,2,3)],glass)
        for y in (-3.55,-1.18,1.18,3.55):H.beam('Glory_glass_vertical_mullion',(-1.51,y,z0),(-1.51,y,z1),.05,M['stone_light'])
        rows=round((z1-z0)/1.15)
        for j in range(rows+1):
            z=z0+(z1-z0)*j/rows
            H.curve('Glory_glass_horizontal_mullion',[(x-.045,y,z) for y,x in cross],.046,M['stone_light'])
    for z in (4.4,15.6,27.95,44.95):H.cube('Glory_existing_glazed_bay_spandrel',(-.83,0,z),(1.18,8.7,.8),M['concrete'])
    # The existing concrete entrance canopy is not a future monumental stair.
    H.mesh('Glory_existing_curved_entrance_canopy',[(-1.0,-4.6,4.15),(-1.0,4.6,4.15),(-4.0,4.6,4.15),(-4.0,-4.6,4.15),(-4.0,-2.3,5.1),(-4.0,0,5.65),(-4.0,2.3,5.1)],[ (0,1,2,6,5,4,3)],M['concrete'])
    for side in (-1,1):
        H.cube('Glory_existing_cylindrical_portal_pier',(-1.12,side*4.68,5.0),(1.6,1.1,10),M['stone_light'])
        for yy in (side*8.0,side*14.5,side*21.8):
            for z in (31.0,32.0):H.beam('Glory_current_work_rail',(-1.3,yy-.8,z),(-1.3,yy+.8,z),.045,M['scaffold'])
    for y in [-22.8,22.8]:
        for z in range(2,29,2):
            H.beam('Glory_scaffold_horizontal',(-3.2,y,z),(2.0,y,z),.05,M['scaffold'])
        for x in [-3.2,2.]:H.beam('Glory_scaffold_upright',(x,y,0),(x,y,30),.06,M['scaffold'])
    H.collection('Construction_Assumption_chapel_unfinished')
    # Sept22 evidence only assures tribune8m plus unfinished envelope, no future statues/dome.
    for sy in (-1,1):
        H.cube('Assumption_unfinished_sidewall',(96,sy*5.0,4.0),(8.0,1.0,8.0),M['stone_light'])
        for x in [92.5,96,99.5]:H.cube('Assumption_tribune_support',(x,sy*4.2,4.0),(.7,.7,8),M['concrete'])
    H.cube('Assumption_tribune_at8m',(96,0,8.1),(8.0,10.5,.4),M['stone_light'])
    for x in [91.8,100.2]:
        for y in [-5.7,5.7]:H.beam('Assumption_scaffold_post',(x,y,0),(x,y,11.3),.06,M['scaffold'])
    for z in [2,4,6,8,10]:
        for sy in (-1,1):H.beam('Assumption_scaffold_ledger',(91.8,sy*5.7,z),(100.2,sy*5.7,z),.06,M['scaffold'])
    crane(H,M)

def crane(H,M):
    H.collection('Construction_central_crane_174m_July2026')
    # Exact slew angle is time-dependent. Approximate site placement, verified174m height.
    cx,cy=31.0,0.0;mat=M['mosaic_gold'];dark=M['iron'];h=112.0
    # Official crane mounting elevation54m. Temporary support stool connects to
    # this model's approximate folded roof, keeping all steel above the45m vault.
    # Support-member dimensions are interpreted, not an engineering survey.
    H.cube('Crane_roof_support_lower_spreader',(cx,cy,46.55),(4.2,4.2,.42),M['concrete'])
    H.cube('Crane_roof_mount_platform_54m',(cx,cy,53.78),(4.2,4.2,.44),dark)
    for dx in (-1.5,1.5):
        for dy in (-1.5,1.5):H.beam('Crane_roof_support_leg',(cx+dx,cy+dy,46.45),(cx+dx,cy+dy,53.8),.16,dark)
    for side in (-1.5,1.5):
        H.beam('Crane_roof_support_brace',(cx-1.5,cy+side,46.65),(cx+1.5,cy+side,53.6),.09,dark)
        H.beam('Crane_roof_support_brace',(cx+side,cy-1.5,46.65),(cx+side,cy+1.5,53.6),.09,dark)
    for dx in (-1,1):
        for dy in (-1,1):H.beam('Crane_mast_chord',(cx+dx*1.0,cy+dy*1.0,54),(cx+dx*1.0,cy+dy*1.0,h),.10,mat)
    for z in range(54,112,3):
        for sy in (-1,1):
            H.beam('Crane_lattice',(cx-1,cy+sy,z),(cx+1,cy+sy,z+3),.055,mat)
            H.beam('Crane_lattice',(cx+sy,cy-1,z),(cx+sy,cy+1,z+3),.055,mat)
        for sy in (-1,1):H.beam('Crane_mast_tie',(cx-1,cy+sy,z),(cx+1,cy+sy,z),.065,mat)
    H.cube('Crane_turntable',(cx,cy,h),(4.5,4.5,1.0),dark)
    H.cube('Crane_operator_cab',(cx,cy-2.7,h+1.2),(2,1.8,2.2),M['ceramic_white'])
    H.cube('Crane_cab_window',(cx,cy-3.62,h+1.45),(1.4,.05,1.25),M['glass_blue'])
    # Luffing jib (tip174m), counterjib and its pack; no obsolete Jesus tie/bridge.
    start=Vector((cx,cy,h+1));end=Vector((cx-25,cy+2,174));d=end-start;side=Vector((0,1.1,0));up=d.cross(side).normalized()*1.1
    corners=[]
    for k in range(4):
        off=(side if k%2 else -side)+(up if k//2 else -up)
        corners.append(off);H.beam('Crane_jib_longitudinal',tuple(start+off),tuple(end+off*.38),.095,mat)
    n=18
    for j in range(n):
        a=start+d*j/n;b=start+d*(j+1)/n
        for k in range(4):H.beam('Crane_jib_crossbrace',tuple(a+corners[k]*(1-.62*j/n)),tuple(b+corners[(k+1)%4]*(1-.62*(j+1)/n)),.052,mat)
    H.beam('Crane_counterjib',(cx,cy,h),(cx+10,cy,h),.4,dark)
    H.cube('Crane_counterweight',(cx+8.5,cy,h+1),(4.0,4.0,3.5),M['concrete'])
    H.beam('Crane_Aframe',(cx+3,cy,h),(cx+4,cy,h+11),.15,dark)
    H.beam('Crane_cable',(cx+4,cy,h+11),tuple(end),.038,dark)
    hook=Vector((cx-17,cy+1.3,154))
    H.beam('Crane_hook_cable',tuple(hook),(hook.x,hook.y,96),.032,dark)
    H.cylinder('Crane_hook_weight',(hook.x,hook.y,95.6),.38,.8,M['mosaic_red'],10)

def leaf_doors(H,M):
    """Sotoo's 2014–15 bronze doors: individually raised cast botanical relief.
    Authored leaf placement is an approximation; motif families/height are sourced.
    Central leaves are held clear of the pedestrian passage in this walkthrough.
    """
    H.collection('Exterior_Nativity_Sotoo_botanical_bronze_doors')
    mat=M.get('bronze_leaf',M['bronze']);light=M.get('bronze_leaf_light',M['bronze'])
    rnd=random.Random(1978)
    def leaf(batch,c,size,angle,ivy=True):
        # Lobed ivy outline, cupped center and raised folded veins; not flat sprites.
        shape=[(0,-1),(-.62,-.47),(-.88,-.12),(-.48,.12),(-.65,.66),(-.23,.53),(0,1),(.24,.51),(.68,.66),(.49,.12),(.9,-.12),(.59,-.48)] if ivy else [(0,-1),(-.35,-.7),(-.52,-.1),(-.35,.55),(0,1),(.35,.55),(.52,-.1),(.35,-.7)]
        ca,sa=cos(angle),sin(angle)
        v=[(c[0],c[1]+.065*size,c[2])]
        for a,b in shape:v.append((c[0]+size*(a*ca-b*sa),c[1]+size*.035*(b*b-a*a),c[2]+size*(a*sa+b*ca)))
        batch.add(v,[(0,i+1,(i+1)%len(shape)+1) for i in range(len(shape))])
        H.beam('Door_leaf_midvein',(c[0]+size*sa*.87,c[1]+.07*size,c[2]-size*ca*.87),(c[0]-size*sa*.78,c[1]+.07*size,c[2]+size*ca*.78),.009,light,8)
        for j in [-1,1]:
            H.beam('Door_leaf_vein',(c[0],c[1]+.07*size,c[2]),(c[0]+size*(j*.50*ca-.4*sa),c[1]+.045*size,c[2]+size*(j*.5*sa+.4*ca)),.005,light,8)
    # Four7m panels, central pair beside a clear passage. Upper openings glazed.
    for idx,(xc,width,family) in enumerate([(42.5,2.6,'Hope'),(48.7,2.8,'Charity_left'),(56.3,2.8,'Charity_right'),(62.5,2.6,'Faith')]):
        y=36.75
        H.cube('Sotoo_'+family+'_cast_bronze_backing',(xc,y,3.52),(width,.16,7.0),mat)
        H.cube('Sotoo_'+family+'_upper_glass',(xc,y-.10,8.0),(width,.035,1.95),M['glass_green'])
        foliage=Batch(H,'Sotoo_'+family+'_individual_cast_leaves',mat)
        for row in range(23):
            z=.18+row*.29
            for col in range(9):
                x=xc-width/2+.14+col*(width-.28)/8+rnd.uniform(-.08,.08)
                size=rnd.uniform(.19,.29)
                leaf(foliage,(x,y+.105+rnd.uniform(0,.055),z),size,rnd.uniform(-pi,pi),family.startswith('Charity'))
        foliage.finish()
        for k in range(6):
            x=xc-width*.42+k*width*.168
            pts=[(x+.15*sin(j*.63+k),y+.13,.15+j*.34) for j in range(21)]
            H.curve('Sotoo_'+family+'_intertwined_vine',pts,.022,light)
        flowers=Batch(H,'Sotoo_'+family+'_cast_flowers',light)
        for j in range(11):
            x=xc+rnd.uniform(-width*.41,width*.41);z=rnd.uniform(.25,6.8)
            petals=5 if family=='Faith' else 6
            for k in range(petals):
                a=2*pi*k/petals;flowers.ellipsoid((x+.115*cos(a),y+.21,z+.115*sin(a)),(.09,.055,.13),8,5,a)
            flowers.ellipsoid((x,y+.22,z),(.055,.04,.055),8,5)
        flowers.finish()
        # Cast beetles/bee/butterfly details are pedestrian-scale and not texture decals.
        bugs=Batch(H,'Sotoo_'+family+'_insects',M['bronze'])
        for j in range(6):
            x=xc+rnd.uniform(-width*.36,width*.36);z=.7+j*.95
            bugs.ellipsoid((x,y+.25,z),(.045,.046,.082),10,7)
            bugs.ellipsoid((x,y+.25,z+.077),(.03,.035,.032),8,5)
            for side in (-1,1):
                for k in range(3):H.curve('Sotoo_cast_insect_leg',[(x+side*.03,y+.25,z-.038+k*.035),(x+side*.07,y+.24,z-.055+k*.05),(x+side*.105,y+.19,z-.065+k*.06)],.005,M['bronze'])
            if j%2:
                for side in (-1,1):bugs.ellipsoid((x+side*.09,y+.235,z+.015),(.08,.014,.125),9,5)
        bugs.finish()

def draped_person(H,M,name,c,h=2.7,pose='standing',look=-.12,arms=None):
    """Individually posed naturalistic sculpture with sculpted drapery/head/hands.
    Overall pose photo-informed; subtle anatomy is authored, not a scan.
    """
    x,y,z=c;stone=M['stone_light'];bat=Batch(H,name+'_anatomical_details',stone)
    seated=pose in ('seated','kneeling');ch= h*(.66 if seated else 1)
    # Flowing robe has asymmetrical folded profile and knee projection.
    levels=[(0,.36,.24),(.15,.41,.28),(.38,.29,.32),(.62,.22,.18),(.77,.31,.18)]
    v=[];n=32
    for j,(t,rx,ry) in enumerate(levels):
        zz=z+t*ch
        for k in range(n):
            a=2*pi*k/n;fold=1+.10*cos(9*a+j*.23)+.05*cos(15*a-j*.4)
            forward=(.35*h*sin(pi*t)*(.7 if seated else .10))
            v.append((x+h*rx*cos(a)*fold,y+h*ry*sin(a)*fold+forward,zz))
    f=[(j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k) for j in range(len(levels)-1) for k in range(n)]
    obj=H.mesh(name+'_flowing_folded_robe',v,f,stone)
    for face in obj.data.polygons:face.use_smooth=True
    # Deeper sweeping drapery across the knee, distinct in seated angels.
    for k in range(6):
        dx=(k-2.5)*h*.085
        H.curve(name+'_drapery_crease',[(x+dx,y+h*.25,z+.06),(x+dx*.9,y+h*(.3 if seated else .21),z+ch*.31),(x+dx*.55,y+h*.18,z+ch*.64)],h*.012,M['stone'])
    head=(x+look*h*.25,y+h*.08,z+ch*.89)
    bat.ellipsoid(head,(h*.12,h*.105,ch*.14),16,10)
    bat.ellipsoid((head[0],head[1],head[2]+ch*.06),(h*.131,h*.111,ch*.11),16,8)
    # Brows, nose, mouth and subtly recessed eyes remain carved stone (no painted pupils).
    hx,hy,hz=head
    H.mesh(name+'_sculpted_nose',[(hx-h*.022,hy+h*.098,hz+ch*.015),(hx+h*.022,hy+h*.098,hz+ch*.015),(hx+look*.1,hy+h*.155,hz-ch*.04),(hx,hy+h*.10,hz-ch*.055)],[(0,1,2),(0,2,3),(1,3,2)],stone)
    for ss in (-1,1):
        bat.ellipsoid((hx+ss*h*.043,hy+h*.092,hz+ch*.018),(h*.028,h*.012,ch*.014),10,5)
        H.curve(name+'_brow',[(hx+ss*h*.02,hy+h*.101,hz+ch*.040),(hx+ss*h*.055,hy+h*.100,hz+ch*.047),(hx+ss*h*.081,hy+h*.085,hz+ch*.034)],h*.009,stone)
    H.curve(name+'_mouth',[(hx-h*.03,hy+h*.094,hz-ch*.072),(hx,hy+h*.110,hz-ch*.077),(hx+h*.03,hy+h*.094,hz-ch*.072)],h*.006,M['stone'])
    # Hair ringlets with quiet irregular rhythm.
    for j in range(14):
        a=2*pi*j/14;bat.ellipsoid((hx+h*.117*cos(a),hy+h*.1*sin(a),hz+ch*.06+.025*sin(j)),(h*.035,h*.03,ch*.053),8,5)
    if arms is None:arms=[(-.34,.28,.55),(.18,.34,.53)]
    for side,target in zip((-1,1),arms):
        shoulder=(x+side*h*.24,y+.05*h,z+ch*.7)
        hand=(x+h*target[0],y+h*target[1],z+ch*target[2]);elbow=((shoulder[0]+hand[0])*.5+side*.06*h,(shoulder[1]+hand[1])*.5,hand[2]-.12*h)
        H.curve(name+'_posed_arm',[shoulder,elbow,hand],h*.043,stone, resolution=3)
        bat.ellipsoid(hand,(h*.043,h*.027,h*.071),10,6)
        for finger in range(4):
            xx=hand[0]+(finger-1.5)*h*.018
            H.curve(name+'_fingers',[(xx,hand[1],hand[2]),(xx,hand[1]+h*.03,hand[2]+h*.05),(xx+h*.01,hand[1]+h*.055,hand[2]+h*.066)],h*.008,stone)
    for side in(-1,1):bat.ellipsoid((x+side*h*.17,y+h*.27,z+.06*h),(h*.105,h*.19,h*.07),12,6)
    bat.finish()

def nativity_named_sculptures(H,M):
    H.collection('Exterior_Nativity_selected_named_sculptures')
    # Relative positions are the official facade's central Charity composition;
    # source-image viewing rays differ, so local metric placements remain estimates.
    y=37.8;stone=M['stone_light']
    # Busquets Holy Family: Joseph standing, Mary bent toward infant/manger.
    draped_person(H,M,'Busquets_Nativity_Mary',(51.45,y,12.9),2.65,'kneeling',look=.5,arms=[(.12,.36,.52),(.30,.31,.51)])
    draped_person(H,M,'Busquets_Nativity_Joseph',(53.70,y-.12,12.9),3.1,'standing',look=-.5,arms=[(-.30,.27,.57),(-.09,.3,.5)])
    H.cube('Busquets_Nativity_manger',(52.4,y+.70,13.23),(1.65,.78,.6),M['stone'])
    baby=Batch(H,'Busquets_Nativity_infant',stone);baby.ellipsoid((52.4,y+.75,13.6),(.5,.2,.17),14,8);baby.ellipsoid((52.02,y+.78,13.75),(.21,.17,.19),12,8);baby.finish()
    # Magi left, shepherds right; crowns, offering vessels and staff distinguish groups.
    for i,x in enumerate([46.15,47.65,48.8]):
        z=11.9+.25*(i==0)
        draped_person(H,M,'Ros_i_Bofarull_Magi_%d'%i,(x,y+.1,z),2.55,'kneeling' if i==2 else 'standing',look=.5,arms=[(.18,.34,.53),(.30,.35,.53)])
        H.cylinder('Magi_offering_vessel',(x+.4,y+1.0,z+1.30),.22,.27,M['stone_light'],12)
        crownz=z+(2.55*.66 if i==2 else 2.55)*1.03
        H.torus('Magi_carved_crown',(x,y+.25,crownz),.29,.07,stone,segments=20)
        for k in range(5):H.beam('Magi_crown_tip',(x+.28*cos(2*pi*k/5),y+.25+.28*sin(2*pi*k/5),crownz),(x+.30*cos(2*pi*k/5),y+.25+.30*sin(2*pi*k/5),crownz+.21),.04,stone)
    for i,x in enumerate([56.1,57.6,59.1]):
        draped_person(H,M,'Ros_i_Bofarull_Shepherd_%d'%i,(x,y-.1,11.9),2.6,'kneeling' if i==0 else 'standing',look=-.5)
    H.curve('Shepherd_staff',[(59.65,y+.3,12),(59.65,y+.3,15),(59.5,y+.3,15.4),(59.20,y+.3,15.2)],.075,stone)
    lamb=Batch(H,'Shepherd_lamb',stone);lamb.ellipsoid((57.5,y+.6,12.4),(.6,.28,.31),12,8);lamb.ellipsoid((57.0,y+.6,12.7),(.2,.17,.23),10,6);lamb.finish()
    # Sotoo harp player1984: seated, instrument on the left, hands on strings.
    x,z=46.9,19.2
    draped_person(H,M,'Sotoo_1984_harp_angel',(x,y,z),3.0,'seated',look=-.6,arms=[(-.35,.35,.58),(-.21,.47,.52)])
    H.curve('Sotoo_harp_ornate_column',[(x-1.55,y+.38,z),(x-1.55,y+.38,z+3.75),(x-1.35,y+.38,z+3.95)],.12,stone)
    H.curve('Sotoo_harp_curved_neck',[(x-1.55,y+.38,z+3.75),(x-.95,y+.38,z+3.45),(x-.40,y+.38,z+2.5),(x-.30,y+.38,z+1.9)],.13,stone)
    H.curve('Sotoo_harp_soundbox',[(x-.30,y+.38,z+1.9),(x-.85,y+.38,z+.85),(x-1.55,y+.38,z+.12)],.20,stone)
    for k in range(9):
        t=k/8;H.beam('Sotoo_harp_carved_string',(x-1.48+1.07*t,y+.43,z+3.72-1.65*t),(x-1.48+.6*t,y+.43,z+.22+.66*t),.014,stone)
    # Sotoo guitar angel1988 uses an individual seated pose and diagonal neck.
    x,z=58.0,19.2
    draped_person(H,M,'Sotoo_1988_guitar_angel',(x,y,z),2.85,'seated',look=-.25,arms=[(-.12,.42,.54),(.32,.40,.74)])
    guitar=Batch(H,'Sotoo_guitar_body',stone)
    guitar.ellipsoid((x+.0,y+1.04,z+1.18),(.48,.12,.56),16,10);guitar.ellipsoid((x+.15,y+1.04,z+1.67),(.35,.12,.37),14,8);guitar.finish()
    H.beam('Sotoo_guitar_neck',(x+.2,y+1.05,z+1.55),(x+.87,y+1.02,z+2.58),.09,stone)
    H.torus('Sotoo_guitar_soundhole',(x+.1,y+1.17,z+1.47),.17,.035,M['stone'],rotation=(pi/2,0,0),segments=24)
    # Nine distinct choir figures: four left and five right around central star trail.
    choir=[(-3.2,25.2,'standing'),(-2.6,23.5,'seated'),(-1.7,24.2,'standing'),(-1.15,22.7,'seated'),(1.2,22.7,'seated'),(1.9,23.4,'seated'),(2.4,24.2,'seated'),(3.15,25.2,'standing'),(4.0,25.35,'standing')]
    for i,(dx,z,pose) in enumerate(choir):
        draped_person(H,M,'Sotoo_1999_singing_child_%02d'%i,(52.5+dx,y-.1,z),1.85,pose,look=(-.35 if dx>0 else .35),arms=[(-.13,.32,.54),(.20,.36,.78 if i%3==0 else .52)])
    # Terraced carved ledges visibly carry the groups rather than floating figures.
    for cx,zz,width in [(52.5,12.4,6.0),(47.5,11.6,5.8),(57.7,11.6,5.8),(46.1,18.9,3.7),(58,18.9,3.7),(49.6,22.3,4.7),(55.4,22.3,5.7)]:
        H.mesh('Nativity_carved_scene_plinth',[(cx-width/2,y-1.0,zz),(cx+width/2,y-1.,zz),(cx+width*.48,y+.9,zz),(cx-width*.48,y+.9,zz),(cx,y+.1,zz-1.0)],[(0,1,2,3),(0,4,1),(1,4,2),(2,4,3),(3,4,0)],M['stone'])

def passion_named_sculptures(H,M):
    H.collection('Exterior_Passion_Subirachs_selected_groups')
    stone=M['stone_light'];x,y,z=43.2,-33.0,4.4
    # Judas kiss: close parallel heads with severe plane cuts; fused sweeping robes.
    for j in range(2):
        xx=x+j*.73;top=z+3.25-j*.16
        v=[(xx-.70,y,z),(xx+.75,y,z),(xx+.36,y-.15,top-.50),(xx-.26,y-.18,top-.25),(xx+.10,y-.65,top-.10),(xx-.4,y-.6,z+.2)]
        H.mesh('Subirachs_Judas_kiss_sharp_drapery',v,[(0,1,4,5),(1,2,4),(2,3,4),(3,0,5,4)],stone)
        # Chiselled 3D head not a sphere; forehead/nose/chin planes.
        hx=xx+(.16 if j==0 else -.1);hz=top
        v=[(hx-.24,y-.13,hz+.46),(hx+.2,y-.15,hz+.46),(hx+.28,y-.35,hz+.23),(hx+.19,y-.55,hz-.07),(hx-.07,y-.54,hz-.14),(hx-.26,y-.29,hz+.04),(hx,y-.69,hz+.13),(hx-.2,y+.1,hz+.28),(hx+.15,y+.1,hz+.28)]
        H.mesh('Subirachs_Judas_kiss_faceted_face',v,[(0,1,2,6,5),(2,3,6),(3,4,6),(4,5,6),(0,7,8,1),(0,5,7),(1,8,2),(5,4,3,2,8,7)],stone)
    # Exact 4x4 numerical square, photographed next to Judas; sums33.
    nums=[[1,14,14,4],[11,7,6,9],[8,10,10,5],[13,2,3,15]]
    import bpy
    for row in range(4):
        for col in range(4):
            xx=x-2.35+col*.48;zz=z+.9+(3-row)*.49
            H.cube('Subirachs_magic_square_cell',(xx,y+.1,zz),(.465,.2,.465),M['stone'])
            curve=bpy.data.curves.new('Magic_square_%s'%nums[row][col],'FONT');curve.body=str(nums[row][col]);curve.size=.31;curve.align_x='CENTER';curve.align_y='CENTER';curve.extrude=.003
            obj=bpy.data.objects.new('Subirachs_magic_square_number',curve);H.ACTIVE.objects.link(obj);obj.location=(xx,y-.012,zz);obj.rotation_euler=(pi/2,0,0);curve.materials.append(M['stone_dark'])
    # Central crucifix: sculpted body with straight stretched arms, head bowed.
    x,y,z=52.5,-33.1,25.3
    body=Batch(H,'Subirachs_crucified_Christ_body',stone)
    body.add([(x-.24,y,z+.3),(x+.20,y,z+.3),(x+.35,y,z+1.48),(x+.15,y-.26,z+1.68),(x-.37,y,z+1.49),(x-.12,y-.32,z+.45)],[(0,1,2,3,4),(0,5,1),(0,4,5),(1,5,3,2),(4,3,5)])
    body.ellipsoid((x-.13,y-.1,z+1.92),(.23,.20,.29),5,4)
    body.finish()
    for side in(-1,1):H.curve('Subirachs_crucified_outstretched_arm',[(x+side*.28,y,z+1.5),(x+side*.86,y,z+1.74),(x+side*1.68,y,z+1.86)],.115,stone)
    for side in(-1,1):H.curve('Subirachs_crucified_leg',[(x+side*.17,y,z+.4),(x+side*.21,y-.12,z-.17),(x+side*.08,y,z-.76)],.13,stone)
    # Crown/loincloth angular folds; no invented narrative beyond the named group.
    H.mesh('Subirachs_crucifixion_loincloth',[(x-.38,y-.05,z+.55),(x+.38,y-.05,z+.55),(x+.28,y-.28,z+.15),(x-.10,y-.35,z+.04)],[(0,1,2,3)],stone)


def _closed_relief_geometry(spec,transition_data=False):
    """Closed estimated relief with a rounded, thin rim, never a cut photo board.

    Front photographic samples are preserved. Only the silhouette coordinates
    receive sub-cell smoothing. The unobserved back is explicitly plain stone.
    Kept free of Blender dependencies so topology can be checked before a build.
    """
    from collections import defaultdict,deque
    nx,ny=spec['nx'],spec['ny'];fld=spec['field'];front=[];oriented={};counts={};adj=defaultdict(set)
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;d=a+nx+1;c=d+1
            if min(fld[a],fld[b],fld[c],fld[d])<=0:continue
            front.append((a,b,c,d))
            for aa,bb in ((a,b),(b,c),(c,d),(d,a)):
                key=tuple(sorted((aa,bb)));counts[key]=counts.get(key,0)+1;oriented[key]=(aa,bb);adj[aa].add(bb);adj[bb].add(aa)
    boundary=[oriented[e] for e,n in counts.items() if n==1]
    border=defaultdict(list)
    for a,b in boundary:border[a].append(b);border[b].append(a)
    used=sorted(adj);remap={k:i for i,k in enumerate(used)}
    # Exact separable Euclidean distance avoids corrugated Manhattan-distance
    # terraces along oblique outlines. Distances are measured in physical metres
    # before conversion to the common cell unit used by the rounded edge band.
    def edt1d(values,spacing):
        nn=len(values);sites=[0]*nn;breaks=[0.0]*(nn+1);sites[0]=0;breaks[0]=-float('inf');breaks[1]=float('inf');kk=0;ss=spacing*spacing
        for qq in range(1,nn):
            while True:
                pp=sites[kk];cross=((values[qq]+ss*qq*qq)-(values[pp]+ss*pp*pp))/(2*ss*(qq-pp))
                if cross>breaks[kk]:break
                kk-=1
            kk+=1;sites[kk]=qq;breaks[kk]=cross;breaks[kk+1]=float('inf')
        result=[];kk=0
        for qq in range(nn):
            while breaks[kk+1]<qq:kk+=1
            pp=sites[kk];result.append(ss*(qq-pp)*(qq-pp)+values[pp])
        return result
    sx=spec['width']/nx;sz=spec['h']/ny;cell=min(sx,sz);large=1e12
    samples=[0.0 if k in border else large for k in range((nx+1)*(ny+1))]
    for j in range(ny+1):samples[j*(nx+1):(j+1)*(nx+1)]=edt1d(samples[j*(nx+1):(j+1)*(nx+1)],sx)
    for i in range(nx+1):
        column=edt1d([samples[j*(nx+1)+i] for j in range(ny+1)],sz)
        for j,val in enumerate(column):samples[j*(nx+1)+i]=val
    dist={k:samples[k]**.5/cell for k in used}
    pos={k:((k%(nx+1))/nx,(k//(nx+1))/ny) for k in used}
    for _ in range(14):
        adjusted={}
        for k,nb in border.items():
            if len(nb)!=2:continue
            u,t=pos[k];au=sum(pos[n][0] for n in nb)/2;at=sum(pos[n][1] for n in nb)/2
            adjusted[k]=(.65*u+.35*au,.65*t+.35*at)
        pos.update(adjusted)
    verts=[];uv=[]
    # Consistent18cm edge treatment across differently sampled assets prevents
    # a96-cell musician or thin Crucifixion limb becoming mostly neutral return.
    rim_cells=max(1.8,min(8.0,.18/min(spec['width']/nx,spec['h']/ny)))
    depths={}
    for k in used:
        edge=min(1,dist[k]/rim_cells);ease=edge*edge*(3-2*edge);depths[k]=.075+(fld[k]-.075)*ease
    # Smooth only the authored return band, never the photograph itself. This
    # removes small row-to-row depth stripes while preserving central relief.
    for _ in range(12):
        adjusted={}
        for k in used:
            if k in border or dist[k]>rim_cells+3:continue
            neighbourhood=adj[k];mean=sum(depths[b] for b in neighbourhood)/len(neighbourhood)
            adjusted[k]=.5*depths[k]+.5*mean
        depths.update(adjusted)
    for k in used:
        u,t=pos[k];dd=depths[k]
        verts.append((spec['cx']+spec['sign']*(u-.5)*spec['width'],spec['y']+spec['sign']*dd,spec['z']+(1-t)*spec['h']));uv.append((u,1-t))
    faces=[tuple(remap[k] for k in f) for f in front];material_ids=[0]*len(faces)
    # The outer surface now has one smoothly blended diffuse image. Binary face
    # material switching produced a sawtooth border even with a smooth mesh.
    # Record area-weighted vertex normals for the CPU image-transition baker.
    vertex_normals={k:[0.,0.,0.] for k in used};estimated_return_faces=0
    for original,face in zip(front,faces):
        a,b,c=[verts[k] for k in face[:3]]
        ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
        nn=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        length=sum(x*x for x in nn)**.5;facing=abs(nn[1])/length if length else 1
        is_return=min(dist[k] for k in original)<rim_cells and facing<.88
        estimated_return_faces+=int(is_return)
        for k in original:
            for axis in range(3):vertex_normals[k][axis]+=nn[axis]
    blend_field=[0.0]*len(fld)
    for k in used:
        normal=vertex_normals[k];length=sum(x*x for x in normal)**.5;alignment=abs(normal[1])/length if length else 1
        t=max(0.,min(1.,(alignment-.70)/.27));weight=t*t*(3-2*t)
        if dist[k]>rim_cells+2:weight=1.
        if k in border:weight=0.
        blend_field[k]=weight
    # Rear cap repeats front topology with reversed winding. Every edge belongs
    # to two faces; no separate open strips or unclosed rear surface remain.
    nfront=len(verts)
    for k in used:
        u,t=pos[k];verts.append((spec['cx']+spec['sign']*(u-.5)*spec['width'],spec['y']-spec['sign']*.075,spec['z']+(1-t)*spec['h']));uv.append((u,1-t))
    for f in front:faces.append(tuple(nfront+remap[k] for k in reversed(f)));material_ids.append(1)
    previous={k:remap[k] for k in border}
    # Two shared intermediate rings softly round the 15cm silhouette thickness.
    for dd in (.035,-.035,-.075):
        current={}
        for k in border:
            if dd==-.075:current[k]=nfront+remap[k];continue
            u,t=pos[k];current[k]=len(verts)
            verts.append((spec['cx']+spec['sign']*(u-.5)*spec['width'],spec['y']+spec['sign']*dd,spec['z']+(1-t)*spec['h']));uv.append((u,1-t))
        for a,b in boundary:faces.append((previous[b],previous[a],current[a],current[b]));material_ids.append(1)
        previous=current
    # Topological validation is cheap relative to mesh generation and stops a
    # regression before a render/export. Vertex-only pinches are reported too.
    edge_counts=defaultdict(int)
    for f in faces:
        for a,b in zip(f,f[1:]+f[:1]):edge_counts[tuple(sorted((a,b)))]+=1
    bad=sum(n!=2 for n in edge_counts.values())
    if bad:raise ValueError('%s relief has %d non-closed edges'%(spec['id'],bad))
    result=(verts,faces,uv,material_ids,dict(vertices=len(verts),faces=len(faces),boundary_vertices=len(border),non_closed_edges=bad,boundary_pinches=sum(len(nb)!=2 for nb in border.values()),neutral_front_returns=0,estimated_return_faces=estimated_return_faces,photo_front_faces=len(front),smooth_baked_edge_transition=True))
    return result+(blend_field,) if transition_data else result


def licensed_sculpture_reliefs(ctx):
    """Actual named artworks preserved in licensed photographic relief surfaces.
    Hand masks and authored 0.45–0.85m depth preserve scene identity and pose.
    This is a limited-view relief reconstruction, explicitly NOT photogrammetry.
    Each cut silhouette has a stone return to its architectural backing.
    """
    import bpy,json
    from pathlib import Path
    H,M=ctx['H'],ctx['M'];root=Path(ctx['root'])
    path=root/'assets/textures/exterior_sculpture/reliefs.json'
    if not path.exists():return
    for spec in json.loads(path.read_text()):
        name=spec['id'];H.collection('Exterior_artwork_relief_'+name)
        mat=bpy.data.materials.new(name+'_licensed_diffuse');mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.89
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');img=bpy.data.images.load(str(root/spec.get('render_texture',spec['texture'])),check_existing=True);img.pack();tex.image=img
        mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
        mat['source_author']=spec['author'];mat['source_license']=spec['license'];mat['source_capture_date']=spec['date']
        mat['reconstruction']=spec['reconstruction'];mat.use_backface_culling=False
        v,f,uv,material_ids,stats=_closed_relief_geometry(spec)
        obj=H.mesh(name+'_closed_sculpture_photo_relief_ESTIMATED_DEPTH',v,f,mat,uv)
        obj.data.materials.append(M[spec.get('return_material','stone_light')])
        for poly,mi in zip(obj.data.polygons,material_ids):poly.material_index=mi
        for poly in obj.data.polygons:poly.use_smooth=True
        obj['method']='Closed hand-masked licensed photographic relief; rounded edge and rear estimated. Limited-view reconstruction, not photogrammetry or a surveyed complete sculpture.'
        for key,value in stats.items():obj['topology_'+key]=value
        # Lower relief surfaces are carried by discreet stone ledges, whose depth is honest.
        w=spec['width'];z=spec['z']-.08;cx=spec['cx'];yy=spec['y']-spec['sign']*.10
        if name=='Sotoo_Singing_Children_1999':
            # The photograph now follows two actual groups, not a rectangular
            # window sheet. Separate recessed consoles avoid an invented plank
            # connecting their empty central opening; support shape is estimated.
            for side in (-1,1):
                xx=cx+side*w*.26;zz=spec['z']+.24
                H.cube(name+'_recessed_group_console',(xx,yy-.48,zz),(w*.30,.62,.24),M['stone'])
                H.beam(name+'_console_root',(xx,yy-1.5,zz-1.35),(xx,yy-.48,zz-.03),.28,M['stone'])
        else:H.cube(name+'_carved_niche_support',(cx,yy,z),(w*.84,.95,.22),M['stone'])


def apse_crane(H,M):
    # Second crane is visible in the dated2026-08-09 NE photograph. Its exact
    # height and slew angle are not documented; these approximate silhouette only.
    H.collection('Construction_apse_crane_photo20260809_approximate')
    x,y,h=91,27,61;mat=M['mosaic_gold']
    for dx in (-.75,.75):
        for dy in(-.75,.75):H.beam('Apse_crane_mast',(x+dx,y+dy,0),(x+dx,y+dy,h),.085,mat)
    for z in range(0,61,3):
        for ss in(-.75,.75):
            H.beam('Apse_crane_lattice',(x-.75,y+ss,z),(x+.75,y+ss,z+3),.05,mat)
            H.beam('Apse_crane_lattice',(x+ss,y-.75,z),(x+ss,y+.75,z+3),.05,mat)
    H.cube('Apse_crane_operator_platform',(x,y,h),(5,3,1),M['iron'])
    H.cube('Apse_crane_counterweight',(x-3,y,h+1.4),(2.8,3,2.4),M['concrete'])
    a=Vector((x,y,h+1));b=Vector((x+18,y,126));perp=Vector((.65,0,-.18));side=Vector((0,.65,0))
    offsets=[perp+side,perp-side,-perp-side,-perp+side]
    for off in offsets:H.beam('Apse_crane_luffing_chord',tuple(a+off),tuple(b+off*.40),.075,mat)
    for j in range(20):
        p=a+(b-a)*j/20;q=a+(b-a)*(j+1)/20
        for k in range(4):H.beam('Apse_crane_jib_lattice',tuple(p+offsets[k]),tuple(q+offsets[(k+1)%4]),.04,mat)
    H.beam('Apse_crane_hook_cable',(x+13,y,108),(x+13,y,47),.028,M['iron'])


def apply_nativity_part_variation(ctx):
    """Small, area-balanced part differences on historic Nativity fabric only.

    Existing V11 texture files, photographed reliefs and shared source materials
    remain unchanged. Four authored headroom maps make all six copy-material
    factors valid glTF values <=1. Roughness/colour are appearance estimates.
    No new stains, procedural dirt, global tint or per-tower horizontal stripes.
    """
    import bpy, json, hashlib
    from pathlib import Path
    import numpy as np
    root = Path(ctx['root']);M = ctx['M']
    data = json.loads((root/'assets/textures/nativity_part_variation_v12/manifest.json').read_text())
    allowed = {
        'Exterior_Nativity_portals', 'Exterior_Nativity_Barnabas',
        'Exterior_Nativity_Simon', 'Exterior_Nativity_Jude', 'Exterior_Nativity_Matthias',
    }
    families = ('nativity_stone', 'nativity_stone_detail')
    source_by_material = {M[key]: key for key in families}
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH'
               and any(c.name in allowed for c in o.users_collection)
               and any(m in source_by_material for m in o.data.materials)]
    if any(o.get('nativity_part_variation') for o in objects):
        raise ValueError('Nativity part variation already applied; refusing repeated tint.')
    groups = {key: [] for key in families}

    def connected_parts(mesh, indices):
        # Batch foliage contains separate authored leaves/knots. Give each whole
        # connected carving one response, never random colours on its polygons.
        parent = list(range(len(mesh.vertices)))
        def find(v):
            while parent[v] != v:
                parent[v] = parent[parent[v]];v = parent[v]
            return v
        for i in indices:
            vs = mesh.polygons[i].vertices;a = find(vs[0])
            for v in vs[1:]:
                b = find(v)
                if a != b:parent[b] = a
        parts = {}
        for i in indices:parts.setdefault(find(mesh.polygons[i].vertices[0]), []).append(i)
        return list(parts.values())

    for obj in objects:
        mesh = obj.data
        areas = np.empty(len(mesh.polygons));mesh.polygons.foreach_get('area', areas)
        centers = np.empty(len(mesh.polygons)*3);mesh.polygons.foreach_get('center', centers)
        centers = centers.reshape((-1, 3))
        for source in families:
            indices = [p.index for p in mesh.polygons if mesh.materials[p.material_index] == M[source]]
            if not indices:continue
            if '_open_sound_louvre_' in obj.name:
                # Original 48 angular strips, four connected faces per strip.
                # Twelve sectors avoid assigning a whole louvre one tonal ring.
                sectors = {}
                for i in indices:sectors.setdefault((i % 48)//4, []).append(i)
                parts = list(sectors.values())
            elif obj.name in ('Nativity_carved_foliage_and_stone_lace', 'Nativity_highlight_leaf_carvings'):
                parts = connected_parts(mesh, indices)
            else:
                parts = [indices]
            for part in parts:
                area = float(areas[part].sum())
                center = (centers[part]*areas[part, None]).sum(0)/max(area, 1e-12)
                x, y, z = center;y = abs(y)
                # Smooth regional variation sampled per existing stone part.
                # No added texture pattern, pure height band, or same-colour tower.
                score = (sin(x*.41+y*.27+z*.16)
                         + .52*sin(x*.93-y*.33+z*.41)
                         + .26*cos(x*1.73+z*.67))
                groups[source].append(dict(obj=obj, faces=part, area=area, score=score))

    copies = {}
    report = {'name': 'Nativity restrained part variation', 'source_manifest': 'assets/textures/nativity_part_variation_v12/manifest.json',
              'object_count': len(objects), 'allowed_collections': sorted(allowed),
              'excluded': 'All photographic relief meshes including their stone returns; glass, bronze, mosaics, Passion, new towers, interior weather backing and all shared source material users outside these five collections.',
              'method': 'Three small area-balanced neutral levels per original stone; entire carved leaves/knots and louvre angular sectors vary as parts, not per-polygon noise or complete tower rings.',
              'materials': {}, 'objects': []}
    for key in families:
        rows = sorted(groups[key], key=lambda g: (g['score'], g['obj'].name, g['faces'][0]))
        total = sum(g['area'] for g in rows)
        if total <= 0:raise ValueError('No Nativity surface area for '+key)
        weights = [0., 0., 0.];running = 0.
        for g in rows:
            tier = min(2, int(3*(running+g['area']/2)/total))
            g['tier'] = tier;weights[tier] += g['area'];running += g['area']
        initial = [-.05, 0., .05]
        bias = sum(a*d for a, d in zip(weights, initial))/total
        deltas = [d-bias for d in initial]
        info = data['materials'][key]
        # Verify all source/derived bytes before referring to the authored maps.
        for section in ('source', 'derived'):
            for channel in ('base', 'rough'):
                item = info[section][channel];p = root/'assets/textures'/item['file']
                if hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError('Nativity PBR provenance mismatch: '+str(p))
        source = M[key]
        for tier, delta in enumerate(deltas):
            mat = source.copy();mat.name = source.name+' | local part '+str(tier+1)
            p = mat.node_tree.nodes.get('Principled BSDF');nodes = mat.node_tree.nodes;links = mat.node_tree.links
            color_node = p.inputs['Base Color'].links[0].from_node
            rough_node = p.inputs['Roughness'].links[0].from_node
            if color_node.type != 'TEX_IMAGE' or rough_node.type != 'TEX_IMAGE':
                raise ValueError('Unexpected Nativity source PBR topology: '+source.name)
            for channel, node in (('base', color_node), ('rough', rough_node)):
                node.image = bpy.data.images.load(str(root/'assets/textures'/info['derived'][channel]['file']), check_existing=True)
                node.image.colorspace_settings.name = 'sRGB' if channel == 'base' else 'Non-Color'
            factor = [a*(1+delta)/b for a, b in zip(info['source_linear_rgb_mean'], info['anchor_linear_rgb_mean'])]
            rough_delta = .02*delta/.05
            rough_factor = (info['source_roughness_mean']+rough_delta)/info['anchor_roughness_mean']
            if not all(0 < v <= 1 for v in factor+[rough_factor]):
                raise ValueError('Nativity factors exceed valid glTF bounds.')
            multiply = nodes.new('ShaderNodeMix');multiply.name = 'Bounded Nativity part colour'
            multiply.data_type = 'RGBA';multiply.blend_type = 'MULTIPLY';multiply.clamp_result = False
            multiply.inputs[0].default_value = 1
            ca = next(s for s in multiply.inputs if s.name == 'A' and s.type == 'RGBA')
            cb = next(s for s in multiply.inputs if s.name == 'B' and s.type == 'RGBA')
            co = next(s for s in multiply.outputs if s.type == 'RGBA')
            cb.default_value = tuple(factor)+(1.,)
            links.new(color_node.outputs['Color'], ca);links.new(co, p.inputs['Base Color'])
            multiply_rough = nodes.new('ShaderNodeMath');multiply_rough.operation = 'MULTIPLY'
            multiply_rough.name = 'Bounded Nativity part roughness';multiply_rough.inputs[1].default_value = rough_factor
            links.new(rough_node.outputs['Color'], multiply_rough.inputs[0]);links.new(multiply_rough.outputs[0], p.inputs['Roughness'])
            mat['nativity_part_variation'] = True;mat['photographic_measurement'] = False
            mat['area_balanced_linear_delta'] = delta;mat['roughness_mean_delta'] = rough_delta
            copies[key, tier] = mat
        report['materials'][key] = {'part_count': len(rows), 'surface_area_m2': total,
                                    'tier_areas_m2': weights, 'linear_lightness_deltas': deltas,
                                    'roughness_mean_deltas': [.02*d/.05 for d in deltas],
                                    'area_weighted_linear_mean_delta': sum(a*d for a, d in zip(weights, deltas))/total}
    by_object = {}
    for key, rows in groups.items():
        for g in rows:by_object.setdefault(g['obj'], []).append((key, g))
    for obj, rows in by_object.items():
        if obj.data.users > 1:obj.data = obj.data.copy()
        slots = {};counts = {}
        for key, g in rows:
            identity = key, g['tier']
            if identity not in slots:
                slots[identity] = len(obj.data.materials);obj.data.materials.append(copies[identity])
            for i in g['faces']:obj.data.polygons[i].material_index = slots[identity]
            counts[str(identity)] = counts.get(str(identity), 0)+len(g['faces'])
        obj['nativity_part_variation'] = True
        report['objects'].append({'name': obj.name, 'faces_by_variant': counts})
    report['copied_material_count'] = len(copies)
    ctx['nativity_part_variation_report'] = report
    (root/'logs/nativity_part_variation_apply.json').write_text(json.dumps(report, indent=2)+'\n')
    print('NATIVITY PART VARIATION', len(objects), 'objects', len(copies), 'copied materials', flush=True)
    return report

def build(ctx):
    H,M=ctx['H'],ctx['M']
    roofs(H,M)
    # Array rhythm is unequal-height central pair and slightly inset outside pair.
    for c,h,name in [((40.4,28.7),98,'Nativity_Barnabas'),((48.2,30.4),107,'Nativity_Simon'),((56.8,30.4),107,'Nativity_Jude'),((64.6,28.7),98,'Nativity_Matthias')]:apostle_tower(H,M,c,h,name,True)
    for c,h,name in [((40.4,-24.9),108,'Passion_James'),((48.2,-26.6),118,'Passion_Thomas'),((56.8,-26.6),118,'Passion_Philip'),((64.6,-24.9),108,'Passion_Bartholomew')]:apostle_tower(H,M,c,h,name,False)
    nativity(H,M);passion(H,M);portal_weather_backing(H,M,ctx.setdefault('colliders',[]))
    ctx.setdefault('colliders',[]).append(dict(type='cylinder',name='Nativity_Charity_central_pier',center=(52.5,36.2,4.9),radius=.74,height=9.8,walkable_floor=False))
    leaf_doors(H,M)
    licensed_sculpture_reliefs(ctx)
    jesus(H,M);mary(H,M)
    for c,symbol in [((42,10.5),'Matthew_man'),((42,-10.5),'Mark_lion'),((63,10.5),'John_eagle'),((63,-10.5),'Luke_bull')]:evangelist(H,M,c,symbol)
    # The four bridge connections are installed architecture, not paths offered to visitors.
    H.collection('Exterior_central_tower_bridges')
    for x in [42,63]:
        for y in [-10.5,10.5]:
            a=Vector((x,y,88));b=Vector((52.5,0,88));d=(b-a).normalized();a+=d*3.5;b-=d*8
            H.beam('Evangelist_Jesus_bridge_underside',tuple(a),tuple(b),.55,M['stone'])
            for z in [89.0,89.7]:H.beam('Bridge_parapet',tuple(a+Vector((0,0,z-88))),tuple(b+Vector((0,0,z-88))),.12,M['stone_light'])
    construction(H,M)
    # Existing Glory doors/weather screen are closed in the dated frontal photo.
    # Access for the experience is via the Nativity portals, as in runtime.
    ctx.setdefault('colliders',[]).extend([
        dict(type='box',name='Glory_existing_closed_weather_wall_lower',center=(-.46,0,15.0),size=(1.3,45,30),walkable_floor=False),
        dict(type='box',name='Glory_existing_closed_weather_wall_upper',center=(-.46,0,37.5),size=(1.3,15,15),walkable_floor=False)])
    apse_crane(H,M)
    apply_nativity_part_variation(ctx)
