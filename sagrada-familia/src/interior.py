"""Sagrada Familia forest interior; original editable procedural reconstruction.
Reference: official Information Booklet 9, pp2-8. Dimensions in metres.
NOT a laser survey. Repeated cells, branch coordinates, seating and decorative
mosaics are photo-guided approximations, recorded in INTERIOR_EVIDENCE.json.
"""
import math
from math import sin, cos, pi, sqrt
from mathutils import Vector

WINDOWS=[]
for side in (-1,1):
    for i in range(5):
        WINDOWS.append(dict(name=f'Side_{side}_{i}', center=(3.75+7.5*i,side*22.58,0), normal=(0,side,0), tangent=(1,0,0), width=6.1,z_bottom=3.3,z_top=27.8,kind='side',side=side))
        WINDOWS.append(dict(name=f'Clerestory_{side}_{i}', center=(3.75+7.5*i,side*7.65,0), normal=(0,side,0), tangent=(1,0,0), width=6.1,z_bottom=32.2,z_top=42.8,kind='clerestory',side=side))
for i in range(7):
    a=-pi/2+(i+.5)*pi/7; n=(cos(a),sin(a),0);t=(-sin(a),cos(a),0)
    WINDOWS.append(dict(name=f'Apse_{i}',center=(67.5+22.58*cos(a),22.58*sin(a),0),normal=n,tangent=t,width=8.2,z_bottom=3.3,z_top=28,kind='apse',side=1 if a>0 else -1 if a<0 else 0))
    WINDOWS.append(dict(name=f'Apse_upper_{i}',center=(67.5+12.85*cos(a),12.85*sin(a),0),normal=n,tangent=t,width=4.2,z_bottom=35,z_top=54,kind='apse_upper',side=1 if a>0 else -1 if a<0 else 0))


def _smooth(o):
    for p in o.data.polygons:p.use_smooth=True
    return o


def _ellipsoid(H,name,c,scale,mat,n=32,m=16):
    v=[];f=[]
    for j in range(m+1):
        a=-pi/2+pi*j/m
        for i in range(n):
            b=2*pi*i/n
            v.append((c[0]+scale[0]*cos(a)*cos(b),c[1]+scale[1]*cos(a)*sin(b),c[2]+scale[2]*sin(a)))
    for j in range(m):
        for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    return _smooth(H.mesh(name,v,f,mat))


def _loft(H,name,points,radii,mat,sides=20,twist=0,flutes=0):
    """Tapered curved structural branch, transported rings; no cylinder operators."""
    # Smooth branch centreline between structural control points; section
    # attenuation remains explicit rather than a generic constant-radius tube.
    src=[Vector(p) for p in points];rrsrc=list(radii);pts=[];rrs=[]
    for seg in range(len(src)-1):
        p0=src[max(seg-1,0)];p1=src[seg];p2=src[seg+1];p3=src[min(seg+2,len(src)-1)]
        for k in range(3):
            t=k/3;t2=t*t;t3=t2*t
            pts.append((p1*2+(p2-p0)*t+(p0*2-p1*5+p2*4-p3)*t2+((p1-p2)*3+p3-p0)*t3)*.5)
            rrs.append(rrsrc[seg]*(1-t)+rrsrc[seg+1]*t)
    pts.append(src[-1]);rrs.append(rrsrc[-1]);radii=rrs;v=[];f=[]
    for j,p in enumerate(pts):
        tangent=(pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]).normalized()
        ref=Vector((1,0,0)) if abs(tangent[0])<.95 else Vector((0,1,0))
        a=tangent.cross(ref).normalized();b=tangent.cross(a).normalized()
        for i in range(sides):
            t=2*pi*i/sides+twist*j/max(1,len(pts)-1)
            rr=radii[j]*(1+.045*cos(flutes*t)) if flutes else radii[j]
            v.append(tuple(p+rr*(a*cos(t)+b*sin(t))))
    for j in range(len(pts)-1):
        for i in range(sides):f.append((j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i))
    f.extend([tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+i for i in range(sides))])
    return _smooth(H.mesh(name,v,f,mat))


def _double_twist(H,name,x,y,r,h,n,mat,lean=(0,0),neck_ratio=.76):
    """Radial intersection of two opposite helicoidal polygon envelopes.
    Polygon directions twist in opposite senses; the cross-section becomes
    increasingly round aloft. Avoids merely twisting one extruded polygon.
    """
    nr=40;ns=n*8;v=[];f=[]
    def radial(t,rot):
        a=(t-rot+pi/n)%(2*pi/n)-pi/n
        return cos(pi/n)/cos(a)
    for j in range(nr+1):
        t=j/nr;z=.18+h*t
        angle=(pi/n)*min(t*1.25,1)
        # Photo-derived non-linear attenuation, not an asserted surveyed ratio.
        # Keep a substantial foot/low shaft, then reduce towards the branch knot.
        stations=((0,1.055),(.055,1.015),(.22,.968),(.52,.884),(.82,neck_ratio+.044),(1,neck_ratio))
        envelope=neck_ratio
        for (ta,ra),(tb,rb) in zip(stations,stations[1:]):
            if ta<=t<=tb:
                u=(t-ta)/(tb-ta);u=u*u*(3-2*u)
                envelope=ra*(1-u)+rb*u;break
        for k in range(ns):
            a=2*pi*k/ns
            rr=r*min(radial(a,angle)*(1+.055*cos(2*n*(a-angle))),radial(a,-angle)*(1+.055*cos(2*n*(a+angle))))
            # Gradual smoothing of the high-order double twist, not a spiral pole.
            rr=(rr*(1-.55*t)+r*.94*.55*t)*envelope
            v.append((x+lean[0]*t+rr*cos(a),y+lean[1]*t+rr*sin(a),z))
    for j in range(nr):
        for k in range(ns):f.append((j*ns+k,j*ns+(k+1)%ns,(j+1)*ns+(k+1)%ns,(j+1)*ns+k))
    f.extend([tuple(reversed(range(ns))),tuple(nr*ns+k for k in range(ns))])
    return _smooth(H.mesh(name,v,f,mat))


def _interior_local_finish(M,key,source,title,base,roughness,metallic=0,coat=0):
    """Local finish for capitals/optical fittings, never mutate window glass.
    No source image or unverified iconography is introduced by these finishes.
    """
    if key in M:return M[key]
    template=M.get(source)
    if template is None:return None  # Supports geometry-only audit contexts.
    mat=template.copy();mat.name=title
    mat.diffuse_color=tuple(base)+(1.,)
    p=mat.node_tree.nodes.get('Principled BSDF')
    for socket,value in [('Base Color',tuple(base)+(1.,)),('Roughness',roughness),
                         ('Metallic',metallic),('Emission Strength',0.),('Coat Weight',coat),
                         ('Coat Roughness',.12),('IOR',1.5)]:
        if socket not in p.inputs:continue
        for link in list(p.inputs[socket].links):mat.node_tree.links.remove(link)
        p.inputs[socket].default_value=value
    for node in mat.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.12
    M[key]=mat
    return mat


def _shallow_radial_oval(H,name,center,angle,depth,width,height,mat):
    """Closed low-relief ellipsoid oriented normal to the capital circumference.
    Depth is radial and much smaller than its oval face, avoiding bubble lobes.
    The two poles are single vertices, so every topological edge is closed.
    """
    v=[(center[0],center[1],center[2]-height)];f=[];ns=32;nr=16
    for j in range(1,nr):
        lat=-pi/2+pi*j/nr
        for i in range(ns):
            a=2*pi*i/ns
            radial=depth*cos(lat)*cos(a);tangent=width*cos(lat)*sin(a)
            v.append((center[0]+radial*cos(angle)-tangent*sin(angle),
                      center[1]+radial*sin(angle)+tangent*cos(angle),
                      center[2]+height*sin(lat)))
    top=len(v);v.append((center[0],center[1],center[2]+height))
    for i in range(ns):
        k=(i+1)%ns;f.append((0,1+k,1+i))
    for j in range(nr-2):
        for i in range(ns):
            k=(i+1)%ns
            f.append((1+j*ns+i,1+j*ns+k,1+(j+1)*ns+k,1+(j+1)*ns+i))
    last=1+(nr-2)*ns
    for i in range(ns):f.append((last+i,last+(i+1)%ns,top))
    return _smooth(H.mesh(name,v,f,mat))


def _capital_knot(H,M,name,x,y,z,r,neck_ratio,stone):
    """Photo-guided overlapping ellipsoidal capital, not a spherical ball.

    Official gallery qa_tree_vault: basalt knot width roughly1.45–1.55 times
    the immediate shaft width, height1.1–1.3 times its width (oblique photo
    estimates, not survey dimensions). Pale capitals have blended shoulders;
    dark capitals expose large elongated, mutually intersecting oval faces.
    """
    neck=r*neck_ratio*.97
    capmat=M['basalt'] if stone=='basalt' else M['stone_light']
    if stone=='basalt':
        coremat=_interior_local_finish(M,'_capital_basalt_core','basalt',
                 'Basalt capital connecting core · local finish',(.025,.028,.027),.64)
        facemat=_interior_local_finish(M,'_capital_basalt_polish','basalt',
                 'Polished basalt oval faces · local finish',(.065,.070,.068),.25,coat=.10)
        _ellipsoid(H,name+'_intersecting_capital_core',(x,y,z),
                   (neck*1.30,neck*1.30,neck*1.24),coremat,32,18)
        # Two staggered courses expose broad shallow polished oval cuts. The
        # buried radial backs overlap the existing core; the max radius1.45
        # and max half-height1.26 remain the same as the preceding capital.
        for row in (-1,1):
            for i in range(8):
                a=2*pi*i/8+(pi/8 if row>0 else 0)
                _shallow_radial_oval(H,name+f'_shallow_polished_oval_{row}_{i}',
                    (x+neck*1.27*cos(a),y+neck*1.27*sin(a),z+row*neck*.58),
                    a,neck*.18,neck*.48,neck*.68,facemat)
    else:
        # One continuous egg-shaped body with broad shallow vertical flutes.
        # The ribs blend into the shoulders; they are not separate beads.
        v=[];f=[];ns=48;nr=20
        for j in range(nr+1):
            lat=-pi/2+pi*j/nr
            for i in range(ns):
                a=2*pi*i/ns
                ribs=1+.055*cos(8*a)*cos(lat)**2+.025*cos(16*a)*cos(lat)**4
                rr=neck*1.46*cos(lat)*ribs
                v.append((x+rr*cos(a),y+rr*.96*sin(a),z+neck*1.25*sin(lat)))
        for j in range(nr):
            for i in range(ns):f.append((j*ns+i,j*ns+(i+1)%ns,(j+1)*ns+(i+1)%ns,(j+1)*ns+i))
        _smooth(H.mesh(name+'_ribbed_ellipsoid_capital',v,f,capmat))
        # Rear/side branch shoulders overlap the central ellipsoid and blend
        # the narrow emerging trunk into the wide knot visible in the photos.
        for side in (-1,1):
            _ellipsoid(H,name+f'_blended_elliptical_shoulder_{side}',
                       (x+side*neck*.56,y,z+neck*.47),
                       (neck*.82,neck*1.02,neck*.94),capmat,24,16)
    return neck


def _medallion(H,M,name,c,normal,r,colour):
    """Convex glazed lens with a deep bowl and 24 integral stone sunburst ribs.
    The lattice abstracts the photographed glazing; no invented saint/diocese
    insignia or lettering is represented as authentic iconography.
    """
    n=Vector(normal).normalized();a=Vector((0,0,1));b=n.cross(a).normalized();center=Vector(c)
    v=[];f=[];seg=48;nr=4
    def lens_point(rr,t):
        return center+a*(rr*cos(t))+b*(rr*sin(t))+n*(r*.22*(1-(rr/r)**2))
    for j in range(nr+1):
        rr=r*j/nr
        for i in range(seg):v.append(tuple(lens_point(rr,2*pi*i/seg)))
    for j in range(nr):
        for i in range(seg):f.append((j*seg+i,(j+1)*seg+i,(j+1)*seg+(i+1)%seg,j*seg+(i+1)%seg))
    lensmat=_interior_local_finish(M,'_capital_smoked_lens','glass_white',
              'Capital smoked reflective optical lens · no emblem',(.048,.052,.048),.19,metallic=.10,coat=.32)
    _smooth(H.mesh(name+'_convex_leaded_lens',v,f,lensmat))
    # Solid scalloped bowl: front stepped rings, then a rear return surface.
    v=[];f=[];rings=((1.00,.00),(1.10,.035),(1.34,-.19),(1.50,-.40),(1.03,-.36))
    for ri,(scale,depth) in enumerate(rings):
        for i in range(seg):
            t=2*pi*i/seg
            tooth=i%2
            relief=(.09*tooth if ri in (1,2,3) else 0)
            rr=r*(scale+relief)
            v.append(tuple(center+a*(rr*cos(t))+b*(rr*sin(t))+n*(r*(depth+(.17*tooth if ri==2 else 0)))))
    for j in range(len(rings)):
        for i in range(seg):
            k=(i+1)%seg;q=(j+1)%len(rings)
            f.append((j*seg+i,q*seg+i,q*seg+k,j*seg+k))
    H.mesh(name+'_solid_24_rib_scalloped_bowl',v,f,M['stone_light'])
    # Finer dark came around the bowl, not the old thick clock-like torus.
    H.curve(name+'_fine_bronze_lens_edge',
            [tuple(center+a*(r*cos(2*pi*i/64))+b*(r*sin(2*pi*i/64))) for i in range(65)],.0045,M['bronze'])
    # Sparse fine curved leads follow the inspected lens, not a diamond grid.
    for family in (1,):
        for offset in (-.42,.04,.46):
            pts=[]
            for i in range(17):
                u=-1+2*i/16;w=-.58*u+.14*u*u+offset
                if u*u+w*w<.96:
                    dep=r*.22*(1-u*u-w*w)
                    pts.append(tuple(center+a*(r*u)+b*(r*w)+n*(dep+.003)))
            if len(pts)>1:H.curve(name+'_curved_lead_lattice',pts,.0022,M['bronze'])


def _vault_cells():
    """Exact canopy descriptors shared by mesh generation and branch joins."""
    for i in range(5):
        for y in (-3.75,3.75):yield (f'Nave_Catalan_{i}_{y}',(3.75+7.5*i,y),3.75,3.75,45,4.8,'vault',8,.50)
        for y in (-18.75,-11.25,11.25,18.75):yield (f'Aisle_white_concrete_{i}_{y}',(3.75+7.5*i,y),3.75,3.75,30,4.6,'stone_light',8,.42)
    # Side branches of the transept, with 45m tall central strip.
    for s in (-1,1):
        for j in range(3):
            yy=s*(11.25+7.5*j)
            for xx in (41.25,48.75,56.25,63.75):
                hh=45 if xx in (48.75,56.25) else 30
                yield (f'Transept_{s}_{j}_{xx}',(xx,yy),3.75,3.75,hh,4.8,'vault' if hh==45 else 'stone_light',8,.47)
    # Rising transition bays bridge the nave and apse edges of the transept.
    for xx in (41.25,63.75):
        for yy in (-3.75,3.75):
            yield (f'Transition_{xx}_{yy}',(xx,yy),3.75,3.75,52.5 if xx<50 else 60,5.0,'vault',8,.55,1.8 if xx<50 else .2)
    # 60m crossing canopy, central hyperboloid with two concentric rings of 12 light wells.
    yield ('Crossing_great_central_hyperboloid',(52.5,0),7.5,7.5,60,5.7,'vault',12,1.1)
    for ring,r in enumerate((4.0,6.4)):
        for i in range(12):
            a=2*pi*i/12
            yield (f'Crossing_concentric_{ring}_{i}',(52.5+r*cos(a),r*sin(a)),.85,.85,59.1-ring*.8,1.6,'stone_light',8,.21)
    # Apse roof: genuine high throat and three rising radial tiers.
    for i in range(7):
        a=-pi/2+(i+.5)*pi/7
        for ring,r,h,half in ((0,19,30,3.4),(1,11.5,45,2.8),(2,7.0,60,2.3)):
            yield (f'Apse_radial_tier_{ring}_{i}',(67.5+r*cos(a),r*sin(a)),half,half,h,4.0,'stone_light' if ring==0 else 'vault',8,.40)


def _vault_profile(t,a,crown,drop,petals):
    # Continuous integrated star relief; slightly crisper v6 ridges remain
    # inside the solid curved shell, never detached paper-like appliques.
    u=1-(1-t)**1.28
    q=sqrt(max(0,u*(u+.52)))/sqrt(1.52)
    blend=t*t*(3-2*t)
    # Four/eight long ruled star roots, with three short teeth per primary
    # sector, match the hierarchy in qa_windows_vaults rather than an umbrella.
    # Relief belongs to the same closed shell; no floating triangular plates.
    envelope=sin(pi*t)**.85
    major=max(0,cos((petals/2)*a))**1.55
    secondary=max(0,cos(petals*3*a))**.80
    ridge=.36*blend*(.5+.5*cos(petals*a))**1.65
    ridge+=1.08*envelope*major+.42*envelope*secondary
    return crown-drop*q-ridge


def _canopy_attachment(ctx,label,point,min_z):
    """Find a real solid intrados near a proposed branch end.

    Endpoints are kept away from open light-well throats and cell edges so
    the flared haunch has full stone bearing. Small horizontal corrections
    take priority over stretching a branch through a different ceiling level.
    Returned point is 0.16m below the surface; the connected haunch penetrates
    it by 0.46m. This is an authored join, not an engineering measurement.
    """
    x,y,target=point;candidates=[]
    for spec in _vault_cells():
        name,(cx,cy),hx,hy,crown,drop,colour,petals,oculus,*opt=spec
        # Tiny secondary light wells are decoration inside the primary shell;
        # structural branches bear on the substantial large canopy segments.
        if min(hx,hy)<1.2:continue
        tilt=opt[0] if opt else 0
        px=max(cx-hx+.40,min(cx+hx-.40,x))
        py=max(cy-hy+.40,min(cy+hy-.40,y))
        # A high branch at a cell edge may need to move slightly up its
        # curved shoulder. Examine those nearby bearing locations as well,
        # avoiding a spurious attachment to the next, much taller nave.
        for inset in (0,.16,.32,.50):
            xx=px+(cx-px)*inset;yy=py+(cy-py)*inset
            dx=xx-cx;dy=yy-cy;a=math.atan2(dy,dx)
            rr=math.hypot(dx,dy);inner=oculus*(1+.025*cos(petals*a))
            if rr<inner+.65:
                rr=inner+.65;xx=cx+rr*cos(a);yy=cy+rr*sin(a)
            bound=1/max(abs(cos(a))/hx,abs(sin(a))/hy)
            t=(rr-inner)/(bound-inner)
            z=_vault_profile(t,a,crown,drop,petals)+tilt*(xx-cx)
            if z<min_z:continue
            move=math.hypot(xx-x,yy-y);dz=abs(z-target)
            score=move*3.0+dz*1.3+max(0,dz-4.0)
            candidates.append((score,name,xx,yy,z,move))
    # The tall apse funnel is a second, genuine solid visible surface. Its
    # throat-to-bell formula exactly matches _vaults below.
    dx=x-72;dy=y;rr=math.hypot(dx,dy)
    if 1.40<rr<8.70:
        a=math.atan2(dy,dx);t=sqrt((rr-.75)/8.4)
        z=75-20*t-.65*t*cos(12*a)
        if z>=min_z:
            dz=abs(z-target)
            candidates.append((dz*1.3+max(0,dz-4.0),'Apse_75m_hyperboloid_light_funnel',x,y,z,0))
    if not candidates:raise ValueError('No canopy bearing for '+label)
    _,surface,xx,yy,z,move=min(candidates)
    ctx.setdefault('interior_branch_attachments',[]).append(dict(
        name=label,surface=surface,proposed=point,bearing=(xx,yy,z),
        horizontal_adjustment=round(move,4)))
    return (xx,yy,z-.16)


def _tree_column(ctx,name,x,y,stone,r,h,top,n=8,branch_spread=3.0,inner=False):
    H=ctx['H'];M=ctx['M'];col=ctx.setdefault('colliders',[])
    H.cylinder(name+'_polygon_foot',(x,y,.18),r*1.115,.36,M[stone],vertices=n*2)
    neck_ratio={'sandstone':.72,'granite':.76,'basalt':.81,'porphyry':.84}[stone]
    _double_twist(H,name+'_double_helicoid',x,y,r,h,n,M[stone],neck_ratio=neck_ratio)
    col.append(dict(type='cylinder',name=name,center=(x,y,h/2),radius=r*1.12,height=h,walkable_floor=False))
    kz=h+.12
    neck=_capital_knot(H,M,name,x,y,kz,r,neck_ratio,stone)
    inward=(0,-1 if y>0 else 1,0)
    if stone!='basalt':
        _medallion(H,M,name+'_medallion',(x,y+inward[1]*neck*1.43,kz+.10),inward,neck*.56,M['glass_white'])
        for side in (-1,1):
            _medallion(H,M,name+f'_side_lens{side}',(x+side*neck*1.45,y,kz+.20),(side,0,0),neck*.46,M['glass_white'])
    # The substantial trunk continues almost vertically above the capital.
    # Shorter shoulder boughs support the lower neighbouring nave, while a
    # compact upper crown branches into the canopy. This hierarchy avoids
    # replacing Gaudi's trees with a uniform four-diagonal-strut truss.
    span=top-h;forkz=h+span*.71
    _loft(H,name+'_continuing_primary_trunk',[(x,y,h+.62),(x+.10,y,h+span*.35),(x,y,forkz)],
          [r*.70,r*.56,r*.40],M['stone_light'],sides=24,flutes=n)
    _ellipsoid(H,name+'_upper_branch_joint',(x,y,forkz),(r*.53,r*.53,r*.72),M['stone_light'],24,12)
    for j in range(4):
        a=pi/4+j*pi/2;dx=branch_spread*cos(a);dy=branch_spread*sin(a)
        fan=(-.95,-.38,.38,.95);depth=(.35,.90,.90,.35)
        if name.startswith('Nave_granite'):
            dx=branch_spread*fan[j];dy=(-1 if y>0 else 1)*branch_spread*depth[j]
        elif name.startswith('Crossing_porphyry'):
            dx=(1 if x<52.5 else -1)*branch_spread*(.35,.65,.95,.80)[j]
            dy=(-1 if y>0 else 1)*branch_spread*(.95,.80,.35,.65)[j]
        elif name.startswith(('Crossing_basalt','Transept_granite')):
            dx=(1 if x<52.5 else -1)*branch_spread*depth[j];dy=branch_spread*fan[j]
        elif name.startswith('Apse_horseshoe'):
            inward=Vector((67.5-x,-y,0)).normalized();tangent=Vector((-inward[1],inward[0],0))
            branch=inward*(branch_spread*depth[j])+tangent*(branch_spread*fan[j]);dx,dy=branch[0],branch[1]
        a=math.atan2(dy,dx)
        ends=[]
        for k in (-1,1):
            aa=a+k*.42
            proposed=(x+dx+1.05*cos(aa),y+dy+1.05*sin(aa),top+.35)
            ends.append((k,_canopy_attachment(ctx,name+f'_upper_{j}_{k}',proposed,forkz+.75)))
        # Set the branching shoulder below both actual bearings, rather than
        # using a nominal ceiling height that can leave the tips free in air.
        shoulderz=max(forkz+.35,min(end[2] for _,end in ends)-1.40)
        bearingx=sum(end[0] for _,end in ends)*.5; bearingy=sum(end[1] for _,end in ends)*.5
        shoulder=(x+(bearingx-x)*.68,y+(bearingy-y)*.68,shoulderz)
        _loft(H,name+f'_crown_bough_{j}',[(x+.12*cos(a),y+.12*sin(a),forkz-.35),
              (x+(shoulder[0]-x)*.46,y+(shoulder[1]-y)*.46,forkz+(shoulderz-forkz)*.44),shoulder],
              [r*.38,r*.28,r*.205],M['stone_light'],sides=18,flutes=6)
        for k,end in ends:
            _loft(H,name+f'_short_secondary_{j}_{k}',[shoulder,
                  ((shoulder[0]+end[0])*.5,(shoulder[1]+end[1])*.5,(shoulder[2]+end[2])*.5),end],
                  [r*.18,r*.14,r*.20],M['stone_light'],sides=12,flutes=4)
            # Short flaring stone haunch embeds the branch in the solid vault.
            # It is a connected volumetric section, not a free pointed twig.
            _loft(H,name+f'_vault_join_haunch_{j}_{k}',
                  [(end[0],end[1],end[2]-.35),(end[0],end[1],end[2]+.12),(end[0],end[1],end[2]+.62)],
                  [r*.18,r*.30,r*.46],M['stone_light'],sides=16,flutes=4)
    outward=1 if y>=0 else -1
    lowerz=(27.7 if h>17 and top<46 else top-3.5 if top<32 else 40.5 if top>53 else 42.5)
    lowerz=max(h+3.0,min(lowerz,forkz-1.2))
    for k in (-1,1):
        end=(x+k*2.25,y+outward*3.35,lowerz)
        if name.startswith(('Crossing_basalt','Transept_granite')):
            end=(x+(-1 if x<52.5 else 1)*3.35,y+k*2.25,lowerz)
        elif name.startswith('Crossing_porphyry'):
            end=(x+(1 if x<52.5 else -1)*2.25,y+outward*(2.6+k*.65),lowerz)
        end=_canopy_attachment(ctx,name+f'_lower_{k}',end,h+2.0)
        _loft(H,name+f'_lower_side_bough_{k}',[(x,y,h+.40),
              (x+.28*(end[0]-x),y+.28*(end[1]-y),h+(end[2]-h)*.40),end],
              [r*.46,r*.35,r*.22],M['stone_light'],sides=20,flutes=6)
        _loft(H,name+f'_lower_vault_join_haunch_{k}',
              [(end[0],end[1],end[2]-.35),(end[0],end[1],end[2]+.12),(end[0],end[1],end[2]+.62)],
              [r*.22,r*.32,r*.46],M['stone_light'],sides=16,flutes=4)
    return (x,y,kz)


def _vault_cell(H,M,name,c,hx,hy,crown,drop=5.1,colour='vault',petals=8,oculus=.48,tilt_x=0):
    """A solid, continuous intersected-star/hyperboloid canopy segment.

    v5 replaces all detached flat fan ribbons and triangular sheet appliques.
    The interior shell has smooth real curvature, an integrated star relief,
    an open steep-sided throat, a thick extrados and connected return rims.
    Shared boundary heights and opening centres preserve the weather enclosure.
    """
    cx,cy=c;small=min(hx,hy)<1.2
    ns=petals*12;nr=16 if small else 24
    v=[];f=[];surface_count=0;thickness=.24 if small else .46
    def point(t,a):
        inner=oculus*(1+.025*cos(petals*a))
        bound=1/max(abs(cos(a))/hx,abs(sin(a))/hy)
        r=inner+(bound-inner)*t
        return (cx+r*cos(a),cy+r*sin(a),_vault_profile(t,a,crown,drop,petals)+tilt_x*r*cos(a))
    for j in range(nr+1):
        # More rings near the throat for a curved neck rather than a cone.
        t=(j/nr)**1.35
        for i in range(ns):v.append(point(t,2*pi*i/ns))
    for j in range(nr):
        for i in range(ns):
            # Interior surface normals face down into the nave.
            f.append((j*ns+i,j*ns+(i+1)%ns,(j+1)*ns+(i+1)%ns,(j+1)*ns+i))
    surface_count=len(f)
    # The unseen backing is real solid volume, with0.24–0.46m minimum rims.
    top_inner=len(v)
    for i in range(ns):
        x,y,z=point(0,2*pi*i/ns);v.append((x,y,z+thickness))
    top_outer=len(v)
    for i in range(ns):
        x,y,z=point(1,2*pi*i/ns);v.append((x,y,z+thickness))
    for i in range(ns):
        k=(i+1)%ns
        f.append((top_inner+i,top_outer+i,top_outer+k,top_inner+k))
        f.append((i,top_inner+i,top_inner+k,k))
        f.append((nr*ns+i,nr*ns+k,top_outer+k,top_outer+i))
    obj=H.mesh(name+'_solid_smooth_star_hyperboloid',v,f,M[colour])
    obj.data.materials.append(M['stone_light'])
    obj.data.materials.append(M['mosaic_gold'])
    obj.data.materials.append(M['mosaic_green'])
    for j in range(nr):
        t=((j+.5)/nr)**1.35
        for i in range(ns):
            a=2*pi*(i+.5)/ns;poly=obj.data.polygons[j*ns+i]
            poly.use_smooth=not(.14<t<.82)
            # The structural star has thickness and curvature; only its
            # material boundary is sharp, as in tile/concrete construction.
            if cos((petals/2)*a)>.10 and .13<t<.88:
                poly.material_index=1
            # Main chapel mosaics are warm fields between white structural
            # stars; detached-looking green/gold outer wedges are omitted.
    for poly in obj.data.polygons[surface_count:]:
        poly.use_smooth=True;poly.material_index=1
    _vault_lightwell_center(H,M,name,c,hx,hy,crown,drop,petals,oculus,tilt_x)
    return obj


def _vault_lightwell_center(H,M,name,c,hx,hy,crown,drop,petals,oculus,tilt_x):
    """Reference-based center hierarchy: scalloped rim, recessed lens and
    paired small lamp apertures. Subdued optical lenses deliberately omit
    unlicensed/unresolved sacred emblems, without inventing substitute icons.
    """
    cx,cy=c;small=min(hx,hy)<1.2;ns=petals*12
    # A closed thick annular bowl surrounds the existing daylight aperture.
    # Its outer edge is seated inside the canopy profile at matching radius.
    v=[];f=[]
    for j in range(5):
        for i in range(ns):
            a=2*pi*i/ns;tooth=max(0,cos(petals*a))**.7
            if j==0:rr=oculus*.91;z=crown+.02
            elif j in (1,2):
                rr=oculus*((1.03+.035*tooth) if j==1 else (1.34+.18*tooth))
                inner=oculus*(1+.025*cos(petals*a));bound=1/max(abs(cos(a))/hx,abs(sin(a))/hy)
                t=max(0,(rr-inner)/(bound-inner))
                z=_vault_profile(t,a,crown,drop,petals)-(.10 if j==1 else .16+.04*tooth)
            elif j==3:
                rr=oculus*(1.60+.20*tooth)
                inner=oculus*(1+.025*cos(petals*a));bound=1/max(abs(cos(a))/hx,abs(sin(a))/hy)
                t=(rr-inner)/(bound-inner);z=_vault_profile(t,a,crown,drop,petals)+.10
            else:rr=oculus*.92;z=crown+.20
            v.append((cx+rr*cos(a),cy+rr*sin(a),z+tilt_x*rr*cos(a)))
    for j in range(5):
        for i in range(ns):
            k=(i+1)%ns;q=(j+1)%5;f.append((j*ns+i,j*ns+k,q*ns+k,q*ns+i))
    H.mesh(name+'_solid_scalloped_lightwell_bowl',v,f,M['stone_light'])
    # Different positions have subdued reflective or plain dark lenses.
    # No invented lettering, painted wedges or emblem is presented as a copy.
    emblem=(sum(ord(ch) for ch in name)%4!=0 and not small)
    radius=oculus*.88;N=32;vv=[(cx,cy,crown+.075)];ff=[]
    for i in range(N):
        a=2*pi*i/N;vv.append((cx+radius*cos(a),cy+radius*sin(a),crown+.075+tilt_x*radius*cos(a)))
    for i in range(N):ff.append((0,(i+1)%N+1,i+1))
    # Exact sacred medallion artwork has not been licensed/verified here.
    # Use a subdued optical lens, never a made-up colored crest/pinwheel.
    optical=_interior_local_finish(M,'_vault_smoked_optics','glass_white',
              'Vault smoked optical lens · emblem deliberately unresolved',(.038,.052,.047),.22,metallic=.10,coat=.26)
    H.mesh(name+'_recessed_central_glass_lens',vv,ff,optical if emblem else M['iron'])
    # Fine cross-braced diffuser remains behind the dimensional stone rim.
    for k in range(4):
        a=pi*k/4
        H.beam(name+'_recessed_metal_diffuser',(cx-radius*cos(a),cy-radius*sin(a),crown+.065-tilt_x*radius*cos(a)),
               (cx+radius*cos(a),cy+radius*sin(a),crown+.065+tilt_x*radius*cos(a)),.013 if not small else .007,M['bronze'])
    if small:return
    # Eight paired dark lamp openings, seated within the folded canopy. Their
    # raised stone lips and recessed faces create depth without roof holes.
    for quadrant in range(4):
        for offset in (-.14,.14):
            a=quadrant*pi/2+offset+pi/4;rr=min(hx,hy)*.60
            dx=rr*cos(a);dy=rr*sin(a)
            inner=oculus*(1+.025*cos(petals*a));bound=1/max(abs(cos(a))/hx,abs(sin(a))/hy)
            t=(rr-inner)/(bound-inner);z=_vault_profile(t,a,crown,drop,petals)+tilt_x*dx
            width=.085 if min(hx,hy)<3 else .12;length=width*2.1
            # A dark inset triangular recess, with stone on all three sides.
            pts=[]
            for ux,uy in ((dx-length*cos(a),dy-length*sin(a)),
                          (dx+length*.7*cos(a)-width*sin(a),dy+length*.7*sin(a)+width*cos(a)),
                          (dx+length*.7*cos(a)+width*sin(a),dy+length*.7*sin(a)-width*cos(a))):
                angle=math.atan2(uy,ux);rad=math.hypot(ux,uy)
                ir=oculus*(1+.025*cos(petals*angle));br=1/max(abs(cos(angle))/hx,abs(sin(angle))/hy)
                zz=_vault_profile((rad-ir)/(br-ir),angle,crown,drop,petals)+tilt_x*ux
                pts.append((cx+ux,cy+uy,zz-.025))
            H.mesh(name+'_paired_triangular_lamp_reveal',pts,[(0,2,1)],M['stone_dark'])
            H.curve(name+'_lamp_reveal_stone_lip',pts+[pts[0]],.032,M['stone_light'])
            # Round dark optical opening inside the triangular reveal, as in
            # the official close photograph; it is backed by the solid roof.
            vv=[(cx+dx,cy+dy,z-.035)]
            for k in range(16):
                aa=2*pi*k/16
                ux=dx+width*.56*cos(aa)*cos(a)-width*.75*sin(aa)*sin(a)
                uy=dy+width*.56*cos(aa)*sin(a)+width*.75*sin(aa)*cos(a)
                angle=math.atan2(uy,ux);rad=math.hypot(ux,uy)
                ir=oculus*(1+.025*cos(petals*angle));br=1/max(abs(cos(angle))/hx,abs(sin(angle))/hy)
                zz=_vault_profile((rad-ir)/(br-ir),angle,crown,drop,petals)+tilt_x*ux
                vv.append((cx+ux,cy+uy,zz-.040))
            H.mesh(name+'_small_round_lamp_recess',vv,[(0,(k+1)%16+1,k+1) for k in range(16)],M['iron'])


def _wall_box(H,name,c,tangent,normal,width,depth,z0,z1,mat):
    v=[]
    for z in (z0,z1):
        for u,d in ((-width/2,-depth/2),(width/2,-depth/2),(width/2,depth/2),(-width/2,depth/2)):
            v.append((c[0]+tangent[0]*u+normal[0]*d,c[1]+tangent[1]*u+normal[1]*d,z))
    return H.mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)


def _rail(H,M,name,points,z):
    # Gregorian staff-inspired balcony guard, simplified motifs rather than copied music.
    for dz in (0,.23,.46,.69,.94):H.curve(name+'_staff',[(x,y,z+dz) for x,y in points],.020,M['iron'])
    for i,p in enumerate(points):
        if i%2:continue
        H.beam(name+'_post',(p[0],p[1],z-.10),(p[0],p[1],z+1.10),.032,M['bronze'])
        H.cube(name+'_square_note',(p[0],p[1],z+.23+.23*(i%4)),(.12,.055,.11),M['iron'])


def _floor_and_walls(ctx):
    H=ctx['H'];M=ctx['M'];cs=ctx.setdefault('colliders',[])
    H.collection('Interior_01_Floor_and_envelope')
    H.cube('Nave_walkable_polished_floor',(33.75,0,-.16),(67.5,45,.32),M['floor'])
    H.cube('Transept_walkable_floor',(52.5,0,-.16),(30,60,.32),M['floor'])
    cs.extend([dict(type='box',name='Nave_floor',center=(33.75,0,-.16),size=(67.5,45,.32),walkable_floor=True),dict(type='box',name='Transept_floor',center=(52.5,0,-.16),size=(30,60,.32),walkable_floor=True)])
    # Semicircular apse tessellation, retained as seven individually editable sectors.
    for i in range(7):
        a=-pi/2+i*pi/7;b=a+pi/7;v=[(67.5,0,-.01)]
        v.extend((67.5+22.5*cos(a+(b-a)*j/12),22.5*sin(a+(b-a)*j/12),-.01) for j in range(13))
        H.mesh('Apse_floor_sector',v,[(0,j+1,j+2) for j in range(12)],M['floor'])
    cs.append(dict(type='cylinder',name='Apse_floor',center=(67.5,0,-.16),radius=22.5,height=.30,walkable_floor=True))
    # Very fine floor joints at pedestrian scale; restrained dark inlaid circulation bands.
    for x in range(0,68,3):H.cube('Floor_expansion_joint_X',(x,0,.003),(.013,45,.005),M['stone_dark'])
    for y in range(-21,23,3):H.cube('Floor_expansion_joint_Y',(33.75,y,.004),(67.5,.013,.006),M['stone_dark'])
    for y in (-7.5,7.5):H.cube('Nave_longitudinal_floor_band',(33.75,y,.006),(67.5,.22,.008),M['granite'])
    # All window apertures are actual voids. Materials module supplies their infills.
    for s in (-1,1):
        for i in range(6):
            x=7.5*i
            H.cube('Side_wall_structural_pier',(x,s*22.5,15),(1.42,1.00,30),M['stone_light'])
            cs.append(dict(type='box',name='Sidewall_pier',center=(x,s*22.5,15),size=(1.42,1,30),walkable_floor=False))
        H.cube('Side_wall_low_sill',(18.75,s*22.5,1.62),(37.5,.85,3.24),M['stone'])
        H.cube('Side_wall_upper_band',(18.75,s*22.5,29.05),(37.5,.85,2.3),M['stone_light'])
        cs.append(dict(type='box',name='Sidewall_window_barrier',center=(18.75,s*22.5,14),size=(37.5,.55,28),walkable_floor=False))
        # Upper central clear clerestory above the side-aisle roof.
        for i in range(6):H.cube('Central_clerestory_pier',(7.5*i,s*7.5,37.5),(1.42,.85,15),M['stone_light'])
        H.cube('Central_clerestory_sill',(18.75,s*7.5,31.0),(37.5,.75,2.2),M['stone_light'])
        H.cube('Central_clerestory_top',(18.75,s*7.5,43.6),(37.5,.75,1.5),M['stone_light'])
        for x in (37.5,67.5):
            H.cube('Transept_return_wall',(x,s*26.25,15),(1,7.5,30),M['stone_light'])
            cs.append(dict(type='box',name='Transept_return',center=(x,s*26.25,15),size=(1,7.5,30),walkable_floor=False))
    for i in range(8):
        a=-pi/2+i*pi/7;x=67.5+22.5*cos(a);y=22.5*sin(a)
        _tree_pier=H.cylinder('Apse_envelope_polygon_pier',(x,y,15),.72,30,M['stone_light'],vertices=8)
    for w in WINDOWS:
        if w['kind']!='apse':continue
        _wall_box(H,w['name']+'_sill',w['center'],w['tangent'],w['normal'],9.9,.85,0,3.25,M['stone'])
        _wall_box(H,w['name']+'_upper_band',w['center'],w['tangent'],w['normal'],9.9,.85,28,30.6,M['stone_light'])
        for side in (-1,1):
            edgecenter=(w['center'][0]+side*4.55*w['tangent'][0],w['center'][1]+side*4.55*w['tangent'][1],0)
            _wall_box(H,w['name']+'_opaque_lateral_reveal',edgecenter,w['tangent'],w['normal'],.94,.85,3.25,28.04,M['stone_light'])
        a=math.atan2(w['normal'][1],w['normal'][0]);cs.append(dict(type='box',name=w['name']+'_wall',center=(w['center'][0],w['center'][1],14),size=(9.9,.60,28),rotation_z=a+pi/2,walkable_floor=False))


def _columns(ctx):
    H=ctx['H'];H.collection('Interior_02_Forest_columns')
    for x in (7.5,15,22.5,30,37.5):
        for s in (-1,1):
            _tree_column(ctx,f'Nave_granite_{x}_{s}',x,s*7.5,'granite',.72,19.6,42.0,n=8,branch_spread=3.1)
            _tree_column(ctx,f'Aisle_Montjuic_{x}_{s}',x,s*15,'sandstone',.58,13.65,27.6,n=6,branch_spread=2.65)
    for x in (45,60):
        for s in (-1,1):
            _tree_column(ctx,f'Crossing_porphyry_{x}_{s}',x,s*7.5,'porphyry',1.04,22.7,56.0,n=12,branch_spread=4.3)
            _tree_column(ctx,f'Crossing_basalt_{x}_{s}',x,s*15,'basalt',.87,20.0,42.0,n=10,branch_spread=3.2)
            _tree_column(ctx,f'Transept_granite_{x}_{s}',x,s*22.5,'granite',.69,15.0,28.5,n=8,branch_spread=2.6)
    # Ten columns bound the raised presbytery; curved distribution departs from the nave grid.
    for i in range(10):
        a=-pi/2+i*pi/9;x=67.5+12.5*cos(a);y=12.5*sin(a)
        _tree_column(ctx,f'Apse_horseshoe_{i}',x,y,'basalt' if i in (0,9) else 'granite',.68,22.6,56.0,n=8,branch_spread=2.0)
    for i in range(7):
        a=-pi/2+(i+.5)*pi/7;x=67.5+18.6*cos(a);y=18.6*sin(a)
        _tree_column(ctx,f'Ambulatory_{i}',x,y,'sandstone',.52,14.7,28.5,n=6,branch_spread=1.7)


def _vaults(ctx):
    H=ctx['H'];M=ctx['M'];H.collection('Interior_03_Hyperbolic_vaults')
    for spec in _vault_cells():_vault_cell(H,M,*spec)
    # Very tall flared apse skylight, gold generatrices and Trinity triangle.
    cx,cy=72.0,0;ns=96;nr=24;v=[];f=[]
    for j in range(nr+1):
        t=j/nr;rr=.75+8.4*t*t;z=75-20*t
        for i in range(ns):
            a=2*pi*i/ns;v.append((cx+rr*cos(a),cy+rr*sin(a),z-.65*t*cos(12*a)))
    for j in range(nr):
        for i in range(ns):f.append((j*ns+i,(j+1)*ns+i,(j+1)*ns+(i+1)%ns,j*ns+(i+1)%ns))
    H.mesh('Apse_75m_hyperboloid_light_funnel',v,f,M['vault'])
    for i in range(48):
        a=2*pi*i/48;pts=[]
        for j in range(25):
            t=j/24;rr=.75+8.4*t*t;pts.append((cx+rr*cos(a),rr*sin(a),75-20*t-.08))
        H.curve('Apse_gold_glass_generatrix',pts,.034,M['mosaic_gold'])
    for i in range(3):
        a=2*pi*i/3+pi/2;b=a+2*pi/3
        H.beam('Apse_golden_Trinity_triangle',(cx+3.7*cos(a),3.7*sin(a),66),(cx+3.7*cos(b),3.7*sin(b),66),.14,M['mosaic_gold'])


def _choirs(ctx):
    H=ctx['H'];M=ctx['M'];H.collection('Interior_04_Elevated_choirs')
    for s in (-1,1):
        H.cube('Side_choir_balcony',(18.75,s*20.25,14.82),(37.5,4.2,.46),M['stone_light'])
        # Curving concave balcony lip, staff rail and 3 stepped rows.
        edge=[(j*.375,s*(18.05+.12*cos(2*pi*j/20))) for j in range(101)]
        _rail(H,M,f'Choir_Gregorian_{s}',edge,15.05)
        H.curve('Choir_curved_front_lip',[(x,y,14.90) for x,y in edge],.15,M['stone_light'])
        for i in range(3):H.cube('Choir_tier',(18.75,s*(18.6+.9*i),15.03+i*.20),(37.5,.88,.25+i*.40),M['stone'])
        for i in range(5):
            x=3.75+7.5*i
            H.beam('Choir_diagonal_bracket_at_structural_pier',(x-3.75,s*21.5,10.4),(x-3.75,s*18.2,14.6),.20,M['stone_light'])
            # Ceramic monstrance finials above the front of each choir bay.
            H.cylinder('Monstrance_stem',(x,s*18.25,17.0),.12,2.0,M['mosaic_gold'],vertices=12)
            _ellipsoid(H,'Glazed_ceramic_monstrance',(x,s*18.25,18.3),(.40,.24,.78),M['mosaic_gold'],24,12)
    # Children's choir in a horseshoe above the ambulatory, z15.
    v=[];f=[];segs=84
    for i in range(segs+1):
        a=-pi/2+pi*i/segs
        for r in (18.0,22.25):v.append((67.5+r*cos(a),r*sin(a),14.9))
        if i:f.append((2*i-2,2*i,2*i+1,2*i-1))
    H.mesh('Apse_children_choir_platform',v,f,M['stone_light'])
    pts=[(67.5+18*cos(-pi/2+pi*i/84),18*sin(-pi/2+pi*i/84)) for i in range(85)]
    _rail(H,M,'Apse_children_choir_Gregorian',pts,15.02)


def _altar_and_furnishings(ctx):
    H=ctx['H'];M=ctx['M'];cs=ctx.setdefault('colliders',[]);H.collection('Interior_05_Altar_and_furnishings')
    # Raised sanctuary with shallow approach steps; all flagged as floor for safe return.
    for i in range(10):
        x=62.3+i*.32;z=.10+.20*i;width=19.4-.38*i;length=16.0-i*.32
        H.cube('Presbytery_approach_step',(x+length/2,0,z),(length,width,.20),M['floor'])
        cs.append(dict(type='box',name='Presbytery_step',center=(x+length/2,0,z),size=(length,width,.20),walkable_floor=True))
    H.cube('Porphyry_altar_monolith',(69.8,0,2.64),(1.30,2.72,1.20),M['porphyry'])
    cs.append(dict(type='box',name='Altar',center=(69.8,0,2.64),size=(1.3,2.72,1.2),walkable_floor=False))
    H.cube('Altar_cloth',(69.8,0,3.25),(1.4,2.80,.035),M['stone_light'])
    # Five-metre heptagonal suspended baldachin; parchment fascia and bronze leaves.
    cx=69.8;z=10.5;N=7;v=[];f=[]
    for zz,r in ((z-.30,2.5),(z+.30,2.50),(z+.60,1.65)):
        for i in range(N):
            a=2*pi*i/N;v.append((cx+r*cos(a),r*sin(a),zz))
    for j in range(2):
        for i in range(N):f.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    f.append(tuple(range(2*N,3*N)))
    H.mesh('Heptagonal_parchment_baldachin_5m',v,f,M['mosaic_gold'])
    for i in range(N):
        a=2*pi*i/N;b=2*pi*(i+1)/N
        H.beam('Baldachin_suspension',(cx+1.5*cos(a),1.5*sin(a),z+.6),(cx+.3*cos(a),.3*sin(a),30),.018,M['iron'])
        for j in range(7):
            t=(j+.5)/7;px=cx+2.5*((1-t)*cos(a)+t*cos(b));py=2.5*((1-t)*sin(a)+t*sin(b));lz=z-.65-.12*sin(pi*t)
            H.beam('Baldachin_lamp_chain',(px,py,z-.28),(px,py,lz),.012,M['bronze'])
            _ellipsoid(H,'Baldachin_glass_lamp',(px,py,lz-.08),(.068,.068,.095),M['glass_gold'],12,6)
        # Copper grape clusters, leaf blades and pale wheat crown; small hand-built references.
        px=cx+2.28*cos(a);py=2.28*sin(a)
        for j in range(7):_ellipsoid(H,'Baldachin_glass_grape',(px+.065*(j%3),py+.06*((j//3)%2),z-.45-j*.055),(.060,.06,.069),M['glass_green'],10,6)
        for j in range(3):H.beam('Baldachin_wheat',(px,py,z+.23),(px+.15*cos(a+j*.2),py+.15*sin(a+j*.2),z+1.05+j*.12),.019,M['stone_light'])
    _ellipsoid(H,'Baldachin_fiftieth_central_lamp',(cx,0,z-.40),(.080,.080,.11),M['glass_gold'],12,6)
    # Simplified suspended terracotta crucifix, original sculptural approximation.
    H.beam('Suspended_crucifix_vertical',(69.6,0,7.0),(69.6,0,9.9),.045,M['bronze'])
    H.beam('Suspended_crucifix_crossbar',(69.6,-1.25,9.25),(69.6,1.25,9.25),.045,M['bronze'])
    _ellipsoid(H,'Christ_terracotta_torso',(69.52,0,8.60),(.18,.30,.65),M['sandstone'],24,12)
    _ellipsoid(H,'Christ_terracotta_head',(69.48,-.02,9.36),(.20,.20,.26),M['sandstone'],20,10)
    for s in (-1,1):
        _loft(H,'Christ_extended_arm',[(69.5,s*.22,9.02),(69.5,s*.78,9.16),(69.5,s*1.15,9.28)],[.105,.08,.045],M['sandstone'],12)
        _loft(H,'Christ_leg',[(69.5,s*.13,8.2),(69.46,s*.11,7.65),(69.5,s*.05,7.15)],[.11,.08,.05],M['sandstone'],12)
    # Twin organ pipe banks behind altar, scaled from official photographs.
    for s in (-1,1):
        for i in range(19):
            y=s*(2.0+i*.145);hh=3.2+3.0*sin(pi*i/18)
            H.cylinder('Apse_organ_pipe',(75.8,y,2.5+hh/2),.06,hh,M['bronze'],vertices=12)
        H.cube('Organ_wood_case',(76.0,s*3.30,2.4),(.6,3.0,.85),M['timber'])
    # Pale individual chairs, arranged to retain the longitudinal and crossing aisles.
    # Build each bank into one mesh via static box merging, to keep drawcalls modest.
    verts=[];faces=[]
    def box(c,sc):
        k=len(verts);x,y,z=c;a,b,d=[q/2 for q in sc]
        verts.extend((x+u*a,y+v*b,z+w*d) for u,v,w in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)))
        faces.extend(tuple(k+i for i in face) for face in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)))
    for x in [12+i*1.25 for i in range(21)]:
        for s in (-1,1):
            for j in range(5):
                y=s*(2.1+j*.70)
                box((x,y,.48),(.47,.50,.055));box((x-.21,y,.78),(.055,.50,.45))
                for dx in (-.19,.19):
                    for dy in (-.19,.19):box((x+dx,y+dy,.24),(.036,.036,.46))
    H.mesh('Seating_original_simplified_chair_banks',verts,faces,M['timber'])
    # Seating banks use conservative colliders, preserving central visitor route.
    for s in (-1,1):cs.append(dict(type='box',name='Chair_bank',center=(24.5,s*3.5,.5),size=(26,3.4,1),walkable_floor=False))


def _transition_roof_returns(ctx):
    """Local closed roof returns at the rising axial bays.

    V11 omitted these four side connections: the longitudinal clerestory ends
    at x37.5 while the transverse clerestories start at x45/60. The ornamental
    rising vaults therefore had no weather return to the adjacent30m roofs.
    Join their existing backing edges outside the axial vaults, without adding
    a sheet across the nave/apse sightline or touching any authored lightwell,
    window, or glass. This hidden-to-oblique roof section is an approximation,
    not a claim to survey the real construction detail.
    """
    H=ctx['H'];M=ctx['M']
    H.collection('Interior_06_Continuous_roof_and_apse_enclosure')
    for cx,crown,tilt in ((41.25,52.9,1.8),(63.75,60.4,.2)):
        for side in (-1,1):
            # Inner edge follows the existing inclined roofcell exactly. Outer
            # edge meets the existing low roof behind its ornament. The sheet
            # occupies only x37.5..45 or60..67.5 and |y|7.5..7.82.
            # Keep the return inside the existing end pier (to7.925): a broad
            # shoulder to11.25 would cross the transverse clear-glass opening
            # beginning at7.91. This narrow folded edge preserves that opening.
            v=[];N=24
            for j in range(N+1):
                x=cx-3.75+7.5*j/N;high=crown+tilt*(x-cx)
                v.extend(((x,side*7.5,high),(x,side*7.82,30.45)))
            count=len(v);v += [(x,y,z+.24) for x,y,z in v]
            f=[]
            for j in range(N):
                a=2*j;b=a+2
                f.extend(((a,a+1,b+1,b),(count+a,count+b,count+b+1,count+a+1),
                          (a,b,count+b,count+a),(a+1,count+a+1,count+b+1,b+1)))
            f.extend(((0,count,count+1,1),(2*N,2*N+1,count+2*N+1,count+2*N)))
            H.mesh(f'Transition_roof_side_return_{cx}_{side}',v,f,M['stone_light'])


def _roof_backing_and_transitions(ctx):
    """Continuous weather enclosure behind the ornamental vaulted canopy.
    The roof is an explicitly approximate geometric envelope, not an as-built
    construction survey; primary floor and daylight aperture dimensions remain.
    """
    H=ctx['H'];M=ctx['M'];H.collection('Interior_06_Continuous_roof_and_apse_enclosure')
    def roofcell(name,x,y,hx,hy,z,hole,tilt=0):
        v=[];f=[];N=64
        for ring in (0,1):
            for i in range(N):
                a=2*pi*i/N;r=hole if not ring else 1/max(abs(cos(a))/hx,abs(sin(a))/hy)
                v.append((x+r*cos(a),y+r*sin(a),z+tilt*r*cos(a)))
        for i in range(N):f.append((i,(i+1)%N,N+(i+1)%N,N+i))
        H.mesh(name+'_open_oculus_roof',v,f,M['stone_light'])
        # A translucent collector sits above, preserving the architectural void.
        vv=[(x,y,z+.06)]+[(x+hole*cos(2*pi*i/N),y+hole*sin(2*pi*i/N),z+.06+tilt*hole*cos(2*pi*i/N)) for i in range(N)]
        H.mesh(name+'_daylight_collector',vv,[(0,i+1,(i+1)%N+1) for i in range(N)],M['glass_white'])
    for i in range(5):
        x=3.75+7.5*i
        for y in (-3.75,3.75):roofcell(f'Nave_roof_{i}_{y}',x,y,3.75,3.75,45.45,.56)
        for y in (-18.75,-11.25,11.25,18.75):roofcell(f'Aisle_roof_{i}_{y}',x,y,3.75,3.75,30.45,.47)
    for x in (41.25,63.75):
        for y in (-3.75,3.75):roofcell(f'Transition_roof_{x}_{y}',x,y,3.75,3.75,52.9 if x<50 else 60.4,.61,tilt=1.8 if x<50 else .2)
    _transition_roof_returns(ctx)
    # Faceted folded risers join ceiling levels; no accidental open-sky seams.
    for x,lo,hi in ((37.5,39.3,40.4),(45,53.5,54.7),(60,53.5,55.2)):
        v=[];f=[];N=40
        for j in range(N+1):
            y=-7.5+15*j/N;sc=.42*(1-cos(2*pi*j/5))
            v.extend(((x,y,lo+sc),(x,y,hi)))
            if j:f.append((2*j-2,2*j,2*j+1,2*j-1))
        H.mesh(f'Continuous_folded_vault_riser_{x}',v,f,M['stone_light'])
    # The existing Glory weather envelope is authored in exterior.py from
    # the photographed current concrete wall and stacked glazed bays.
    # Transverse high-nave clerestory at the genuine 30/45m height step.
    # These are x45/x60 side planes, not an invented 45m outer transept box.
    # Their solid sill reaches24.5m:30m is the low-vault CROWN, while its
    # perimeter skirts are at25m. QA rays cross x60 at z27.6..27.9m.
    for xx in (45,60):
        for side in (-1,1):
            for yy0 in (7.5,15,22.5,30):
                H.cube('Transept_clerestory_stone_pier',(xx,side*yy0,34.95),(.8,.85,20.1),M['stone_light'])
            H.cube('Transept_clerestory_sill',(xx,side*18.75,28.05),(.8,22.5,7.1),M['stone_light'])
            H.cube('Transept_clerestory_header',(xx,side*18.75,44.5),(.8,22.5,1.2),M['stone_light'])
            for yy0 in (11.25,18.75,26.25):
                yy=side*yy0
                # Clear upper glazing follows the official highest-nave material
                # principle. Exact transom subdivisions are original approximations.
                H.mesh('Transept_clear_clerestory_glass',[(xx,yy-3.34,31.65),(xx,yy+3.34,31.65),(xx,yy+3.34,43.85),(xx,yy-3.34,43.85)],[(0,1,2,3)],M['glass_white'])
                for dz in (35.8,39.8):H.cube('Transept_clear_glass_transom',(xx,yy,dz),(.17,6.70,.15),M['stone_light'])
                for dy in (-1.12,1.12):H.cube('Transept_clear_glass_mullion',(xx,yy+dy,37.75),(.17,.14,12.25),M['stone_light'])
            # Every roof cell over the high strip has a true oculus; neighbouring
            # low strips remain at30m, allowing the clerestory light to enter.
            for yy0 in (11.25,18.75,26.25):
                for xxx in (41.25,48.75,56.25,63.75):
                    if xx==45:roofcell(f'Transept_weather_roof_{xxx}_{side}_{yy0}',xxx,side*yy0,3.75,3.75,45.45 if xxx in (48.75,56.25) else 30.45,.52)
    for xx in (37.5,67.5):
        for side in (-1,1):H.cube('Transept_return_weather_cap',(xx,side*26.25,30.2),(1,7.5,.60),M['stone_light'])
    # Close only the top of the transept ends, preserving the exterior owner's
    # broad portals below24m and the current facade heights.
    for side in (-1,1):
        H.cube('Transept_high_end_weather_header',(52.5,side*30,37.8),(15,.65,15.4),M['stone_light'])
    # Broad roof shoulder closes onto the completed Jesus tower base.
    N=96;v=[];f=[]
    for j in range(7):
        t=j/6
        for i in range(N):
            a=2*pi*i/N;edge=15/max(abs(cos(a)),abs(sin(a)));r=12*(1-t)+edge*t
            v.append((52.5+r*cos(a),r*sin(a),60.4*(1-t)+45.55*t))
    for j in range(6):
        for i in range(N):
            # Only lateral roof shoulders descend toward the lower transept.
            # The +/-X axial naves rise into the crossing/apse and must remain
            # open underneath their separate inclined vaults/weather backings.
            # Scene-ray QA identified the former rear axial sheet as a false
            # rectangular wall across the tall apse sightline atx66.6..67.1.
            a=2*pi*(i+.5)/N
            if abs(cos(a))>.80:continue
            f.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    H.mesh('Crossing_lateral_roof_shoulders_to_Jesus_base',v,f,M['stone_light'])
    vv=[];ff=[]
    for r in (1.18,12):
        vv.extend((52.5+r*cos(2*pi*i/96),r*sin(2*pi*i/96),60.48) for i in range(96))
    for i in range(96):ff.append((i,(i+1)%96,96+(i+1)%96,96+i))
    H.mesh('Crossing_circular_roof_crown',vv,ff,M['stone_light'])
    # Real infill between the upper apse windows, which previously looked like
    # a detached frame. Leave the exact glazing width4.2, z35..54 unobstructed.
    for w in WINDOWS:
        if w['kind']!='apse_upper':continue
        _wall_box(H,w['name']+'_upper_sill',w['center'],w['tangent'],w['normal'],5.80,.75,30.3,35.0,M['stone_light'])
        _wall_box(H,w['name']+'_upper_header',w['center'],w['tangent'],w['normal'],5.80,.75,54.0,60.0,M['stone_light'])
        for sign in (-1,1):
            c=(w['center'][0]+sign*2.50*w['tangent'][0],w['center'][1]+sign*2.50*w['tangent'][1],0)
            _wall_box(H,w['name']+'_upper_side_reveal',c,w['tangent'],w['normal'],.80,.75,35.0,54.0,M['stone_light'])
    # Lower ambulatory roof slopes gently toward the upper window drum.
    v=[];f=[];N=84
    for j in range(5):
        t=j/4;r=22.5*(1-t)+13.1*t;z=30.5+3.0*t
        for i in range(N+1):
            a=-pi/2+pi*i/N;v.append((67.5+r*cos(a),r*sin(a),z))
    for j in range(4):
        for i in range(N):f.append((j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i))
    H.mesh('Apse_ambulatory_weather_roof',v,f,M['stone_light'])
    # Continuous curved transition from the upper apse drum to the Mary tower
    # plinth; seven-edged shell follows the chapel arc and closes behind it.
    # Only +X half of the apse enclosure is authored; the nave/crossing meets
    # its open front. Preserve the highest 75m interior funnel inside.
    v=[];f=[];N=84
    for j in range(13):
        t=j/12
        for i in range(N+1):
            a=-pi/2+pi*i/N
            outer=Vector((67.5+13.2*cos(a),13.2*sin(a),60.0))
            inner=Vector((76+8*cos(2*a),8*sin(2*a),76.15))
            p=outer*(1-t)+inner*t
            v.append(tuple(p))
    for j in range(12):
        for i in range(N):f.append((j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i))
    H.mesh('Apse_continuous_roof_to_Mary_tower_base',v,f,M['stone_light'])
    # Two folded front cheeks bridge the nave-to-apse vault height change.
    for sign in (-1,1):
        vv=[(67.5,sign*13.2,60),(68,sign*7.5,68),(67.5,sign*7.5,60),(67.5,sign*7.5,52.8)]
        H.mesh('Apse_front_folded_roof_cheek',vv,[(0,1,2),(0,2,3)],M['stone_light'])

def build(ctx):
    _floor_and_walls(ctx)
    _columns(ctx)
    _vaults(ctx)
    _roof_backing_and_transitions(ctx)
    _choirs(ctx)
    _altar_and_furnishings(ctx)
    ctx['interior_windows']=WINDOWS
    print('INTERIOR: original double-twist forest, seven-chapel apse, open hyperboloid vaults, choir and altar complete; photo-derived layout approximation.')
