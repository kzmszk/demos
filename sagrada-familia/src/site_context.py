"""Restrained urban context; original geometry, surrounding street placement approximate."""
import math, random

def build(ctx):
    H,M=ctx['H'],ctx['M']
    if 'foliage' not in M:
        import bpy
        mat=bpy.data.materials.new('Matte plane-tree foliage · original context');mat.use_nodes=True
        p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.07,.145,.042,1);p.inputs['Roughness'].default_value=.92
        M['foliage']=mat
    H.collection('00 Barcelona ground and context')
    H.cube('Continuous accessible exterior',(44,0,-.35),(340,310,.4),M['concrete'])
    ctx['colliders'].append(dict(name='Exterior continuous ground',type='box',walkable_floor=True,center=[44,0,-.35],size=[340,310,.4]))
    H.cube('Temple block pavement',(45,0,-.19),(118,100,.1),M['stone_dark'])
    H.cube('Temple perimeter apron',(45,0,-.12),(106,83,.14),M['sandstone'])
    # Grid lines kept shallow and at human scale.
    for x in range(-12,103,3):
        for y in [-47,47]: H.cube('Pavement joint',(x,y,-.127),(.027,9,.012),M['stone_dark'])
    for y in range(-48,49,3):
        for x in [-11,101]: H.cube('Pavement joint',(x,y,-.127),(9,.027,.012),M['stone_dark'])
    for x in [-20,111]:
        H.cube('Roadway',(x,0,-.13),(12,150,.035),M['basalt'])
    for y in [-59,59]: H.cube('Roadway',(44,y,-.13),(190,12,.035),M['basalt'])
    # Barcelona plane trees as abstract context, do not obstruct reference views.
    random.seed(394)
    for i,(x,y) in enumerate([(x,s*78) for s in [-1,1] for x in [-10,8,84,104]]):
        h=random.uniform(6.3,9.0)
        H.cylinder('Plane tree trunk',(x,y,h*.38),.22,h*.78,M['timber'],12)
        for j in range(4):
            a=j*math.pi/2+.3
            end=(x+2*math.cos(a),y+2*math.sin(a),h)
            H.beam('Plane tree branch',(x,y,h*.5),end,.13,M['timber'])
            # Icosphere via bmesh-free low poly lathe geometry, soft irregular outline.
            verts=[];faces=[]
            for r in range(9):
                t=math.pi*r/8
                for q in range(12):
                    phi=2*math.pi*q/12;noise=1+random.uniform(-.13,.13)
                    verts.append((end[0]+2.4*math.sin(t)*math.cos(phi)*noise,end[1]+2.4*math.sin(t)*math.sin(phi)*noise,end[2]+2.5*math.cos(t)*noise))
            for r in range(8):
                for q in range(12):faces.append((r*12+q,r*12+(q+1)%12,(r+1)*12+(q+1)%12,(r+1)*12+q))
            ob=H.mesh('Plane tree foliage',verts,faces,M.get('foliage',M['mosaic_green']))
            for p in ob.data.polygons:p.use_smooth=True
    # Few park benches provide scale without inventing a literal surveyed cityscape.
    for x in [12,38,64,88]:
        for y in [-80,80]:
            for z in [.4,.55]:H.cube('Park bench slat',(x,y,z),(2.0,.42,.075),M['timber'])
            for dx in [-.8,.8]:H.cube('Park bench foot',(x+dx,y,.2),(.07,.4,.4),M['iron'])
