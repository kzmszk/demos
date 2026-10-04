"""Fast spatial/material mesh batching without repeated Blender context joins."""
import bpy, pathlib, time, json
from mathutils import Vector
import numpy as np

def export(root):
    started=time.monotonic();scene=bpy.context.scene;groups={}
    for ob in list(scene.objects):
        if ob.type!='MESH':continue
        center=sum((ob.matrix_world@Vector(p) for p in ob.bound_box),Vector())/8
        key=(tuple(m.name for m in ob.data.materials),int(center.x//15),int(center.y//15),int(center.z//25))
        groups.setdefault(key,[]).append(ob)
    destination=bpy.data.collections.new('Runtime spatial batches');scene.collection.children.link(destination)
    print('FAST BATCH groups',len(groups),flush=True)
    pending_delete=[]
    for gi,(key,obs) in enumerate(groups.items()):
        if len(obs)<2:continue
        coords=[];indices=[];starts=[];totals=[];mats=[];smooth=[];uvs=[];nv=nl=0
        for ob in obs:
            me=ob.data;v=len(me.vertices);l=len(me.loops);p=len(me.polygons)
            a=np.empty(v*3,np.float32);me.vertices.foreach_get('co',a)
            # The integration stage writes all geometry in world coordinates.
            if not ob.matrix_world.is_identity:
                a=a.reshape(-1,3);r=np.array(ob.matrix_world.to_3x3(),np.float32);t=np.array(ob.matrix_world.translation,np.float32);a=(a@r.T+t).ravel()
            coords.append(a)
            a=np.empty(l,np.int32);me.loops.foreach_get('vertex_index',a);indices.append(a+nv)
            a=np.empty(p,np.int32);me.polygons.foreach_get('loop_start',a);starts.append(a+nl)
            a=np.empty(p,np.int32);me.polygons.foreach_get('loop_total',a);totals.append(a)
            a=np.empty(p,np.int32);me.polygons.foreach_get('material_index',a);mats.append(a)
            a=np.empty(p,np.bool_);me.polygons.foreach_get('use_smooth',a);smooth.append(a)
            a=np.zeros(l*2,np.float32)
            if me.uv_layers:me.uv_layers.active.data.foreach_get('uv',a)
            uvs.append(a);nv+=v;nl+=l
        name=f'Zone {key[1:]} '+(key[0][0] if key[0] else 'plain')
        me=bpy.data.meshes.new(name);me.vertices.add(nv);me.vertices.foreach_set('co',np.concatenate(coords))
        me.loops.add(nl);me.loops.foreach_set('vertex_index',np.concatenate(indices))
        me.polygons.add(sum(len(x) for x in starts))
        me.polygons.foreach_set('loop_start',np.concatenate(starts));me.polygons.foreach_set('loop_total',np.concatenate(totals));me.polygons.foreach_set('material_index',np.concatenate(mats));me.polygons.foreach_set('use_smooth',np.concatenate(smooth))
        for name in key[0]:me.materials.append(bpy.data.materials[name])
        uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',np.concatenate(uvs));me.update(calc_edges=True)
        ob=bpy.data.objects.new(me.name,me);destination.objects.link(ob)
        for old in obs:pending_delete.extend([old,old.data])
        if gi%100==0:print('BATCH',gi,'/',len(groups),round(time.monotonic()-started,1),flush=True)
    bpy.data.batch_remove(ids=set(pending_delete))
    import lighting;lighting.configure_export_glass()
    bpy.ops.object.select_all(action='DESELECT')
    for ob in scene.objects:
        if ob.type=='MESH':ob.select_set(True)
    print('EXPORT GLB',flush=True)
    bpy.ops.export_scene.gltf(filepath=str(pathlib.Path(root)/'build/sagrada_familia.glb'),export_format='GLB',use_selection=True,export_apply=True,export_lights=False,export_cameras=False,export_animations=False,export_yup=True,export_materials='EXPORT',export_normals=True,export_texcoords=True,export_extras=False)
    data={'seconds':round(time.monotonic()-started,1),'spatial_groups':len(groups),'bytes':(pathlib.Path(root)/'build/sagrada_familia.glb').stat().st_size}
    (pathlib.Path(root)/'build/runtime_export.json').write_text(json.dumps(data,indent=2));print('FAST EXPORT FINISHED',data,flush=True)

if __name__=='__main__':
    import sys,os
    root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'));export(root)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
