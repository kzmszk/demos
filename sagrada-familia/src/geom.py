"""Editable metre-scale geometry toolkit. Deterministic mesh and UV construction."""
import bpy, math
from mathutils import Vector
from math import sin,cos,pi,sqrt
ACTIVE=None

def collection(name):
 global ACTIVE
 c=bpy.data.collections.get(name)
 if not c:
  c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
 ACTIVE=c
 return c

def link(obj):
 if ACTIVE:
  for c in list(obj.users_collection):c.objects.unlink(obj)
  ACTIVE.objects.link(obj)
 return obj

def uv_auto(obj,scale=2.0):
 if obj.type!='MESH':return
 me=obj.data
 layer=me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
 for p in me.polygons:
  n=p.normal; axis=max(range(3),key=lambda k:abs(n[k]))
  dims=[i for i in range(3) if i!=axis]
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co
   layer.data[li].uv=(co[dims[0]]/scale,co[dims[1]]/scale)

def mesh(name,verts,faces,mat,uv=None):
 me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
 obj=bpy.data.objects.new(name,me); (ACTIVE or bpy.context.scene.collection).objects.link(obj)
 if mat:me.materials.append(mat)
 if uv:
  lay=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   for li in p.loop_indices:lay.data[li].uv=uv[me.loops[li].vertex_index]
 else:uv_auto(obj)
 return obj

def cube(name,location,scale,mat,bevel=0):
 x,y,z=location; a,b,c=[s/2 for s in scale]
 v=[(x+i*a,y+j*b,z+k*c) for i,j,k in [(-1,-1,-1),(-1,1,-1),(1,1,-1),(1,-1,-1),(-1,-1,1),(-1,1,1),(1,1,1),(1,-1,1)]]
 o=mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
 if bevel:
  mod=o.modifiers.new('Worn arris','BEVEL');mod.width=bevel;mod.segments=2
 return o

def cylinder(name,location,radius,depth,mat,vertices=24):
 x,y,z=location;v=[]
 for zz in (z-depth/2,z+depth/2):
  v.extend((x+radius*cos(2*pi*i/vertices),y+radius*sin(2*pi*i/vertices),zz) for i in range(vertices))
 f=[tuple(reversed(range(vertices))),tuple(range(vertices,2*vertices))]
 f.extend((i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices))
 o=mesh(name,v,f,mat)
 for p in o.data.polygons[2:]:p.use_smooth=True
 return o

def curve(name,points,radius,mat,cyclic=False,resolution=2):
 # Mesh tube with parallel transported section; exportable without modifiers.
 pts=[Vector(p) for p in points]; n=len(pts); sides=8 if resolution<3 else 12
 v=[]
 prev=None
 for i,p in enumerate(pts):
  tangent=(pts[(i+1)%n]-pts[i-1]) if cyclic else (pts[min(i+1,n-1)]-pts[max(0,i-1)])
  if tangent.length<1e-8:tangent=Vector((0,0,1))
  tangent.normalize(); ref=Vector((0,0,1)) if abs(tangent.z)<.95 else Vector((1,0,0))
  a=tangent.cross(ref).normalized(); b=tangent.cross(a).normalized()
  if prev is not None and a.dot(prev)<0:a=-a;b=-b
  prev=a
  v.extend(tuple(p+radius*(a*cos(2*pi*j/sides)+b*sin(2*pi*j/sides))) for j in range(sides))
 f=[]
 for i in range(n if cyclic else n-1):
  for j in range(sides):f.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
 if not cyclic:f.extend([tuple(reversed(range(sides))),tuple((n-1)*sides+j for j in range(sides))])
 o=mesh(name,v,f,mat)
 for p in o.data.polygons:p.use_smooth=True
 return o

def beam(name,a,b,radius,mat,vertices=12):return curve(name,[a,b],radius,mat,resolution=3 if vertices>=12 else 2)

def torus(name,center,major,minor,mat,rotation=(0,0,0),segments=64):
 from mathutils import Euler
 R=Euler(rotation).to_matrix(); c=Vector(center)
 pts=[tuple(c+R@Vector((major*cos(2*pi*i/segments),major*sin(2*pi*i/segments),0))) for i in range(segments)]
 return curve(name,pts,minor,mat,cyclic=True)

def point_arch(span,rise,steps=32):
 # Two-centered Gothic arch through (-a,0), (0,rise), (+a,0).
 a=span/2; c=(rise*rise-a*a)/(2*a); r=a+c
 result=[]
 theta=math.atan2(rise,-c)
 for i in range(steps+1):
  t=pi+(theta-pi)*i/steps
  result.append((c+r*cos(t),r*sin(t)))
 return result+[(-x,z) for x,z in reversed(result[:-1])]

def arch(name,center,span,spring,rise,thickness,depth,mat,plane='XZ',segments=24):
 # ring profile continuous so no coplanar layered z-fighting
 inner=point_arch(span,rise,segments); outer=point_arch(span+2*thickness,rise+thickness,segments); n=len(inner)
 def pt(u,d,z):
  return (center[0]+u,center[1]+d,center[2]+spring+z) if plane=='XZ' else (center[0]+d,center[1]+u,center[2]+spring+z)
 v=[]
 for d in (-depth/2,depth/2):v.extend(pt(u,d,z) for u,z in inner);v.extend(pt(u,d,z) for u,z in outer)
 f=[]
 for i in range(n-1):
  f.extend([(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)])
 f.extend([(0,n,3*n,2*n),(n-1,2*n-1,4*n-1,3*n-1)])
 return mesh(name,v,f,mat)

def arch_wall(name,center,span,spring,rise,walltop,pier,depth,mat,plane='XZ',base=0):
 coords=point_arch(span,rise,24); n=len(coords); v=[]
 def pt(u,d,z):return (center[0]+u,center[1]+d,center[2]+z) if plane=='XZ' else (center[0]+d,center[1]+u,center[2]+z)
 for d in (-depth/2,depth/2):
  v.extend(pt(u,d,spring+z) for u,z in coords);v.extend(pt(u,d,walltop) for u,z in coords)
 f=[]
 for i in range(n-1):f.extend([(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)])
 o=mesh(name,v,f,mat)
 for sign in (-1,1):
  loc=list(center);loc[0 if plane=='XZ' else 1]+=sign*(span/2+pier/2);loc[2]+=(walltop+base)/2
  scale=(pier,depth,walltop-base) if plane=='XZ' else (depth,pier,walltop-base)
  cube(name+'_pier',loc,scale,mat)
 return o

def disk(name,center,radius,mat,plane='YZ',segments=128):
 v=[center];uv=[(.5,.5)]
 for i in range(segments):
  a=2*pi*i/segments;u=radius*cos(a);z=radius*sin(a)
  v.append((center[0],center[1]+u,center[2]+z) if plane=='YZ' else (center[0]+u,center[1],center[2]+z));uv.append((.5+.5*cos(a),.5+.5*sin(a)))
 return mesh(name,v,[(0,i+1,(i+1)%segments+1) for i in range(segments)],mat,uv)

def join_collection(name):
 c=bpy.data.collections.get(name)
 if not c:return
 obs=[o for o in c.objects if o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 if obs:
  bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();bpy.context.object.name=name+'_MESH'
