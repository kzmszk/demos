"""Photograph-coloured shadow transmission for offline review, with glTF fallback.

This uses photographed visible RGB as a shadow filter. It is not a measured
spectral glass simulation. The camera sees the same photographed artwork.
"""
import bpy

def configure_glass_shadows():
    count=0
    for mat in bpy.data.materials:
        if 'photographed bank' not in mat.name or not mat.use_nodes:continue
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        p=nodes.get('Principled BSDF');out=next((n for n in nodes if n.type=='OUTPUT_MATERIAL'),None)
        if not p or not out:continue
        transparent=nodes.get('Photographic shadow filter') or nodes.new('ShaderNodeBsdfTransparent')
        transparent.name='Photographic shadow filter'
        path=nodes.get('Shadow ray selector') or nodes.new('ShaderNodeLightPath');path.name='Shadow ray selector'
        mix=nodes.get('Offline coloured transmission') or nodes.new('ShaderNodeMixShader');mix.name='Offline coloured transmission'
        colorlink=p.inputs['Base Color'].links
        if colorlink:links.new(colorlink[0].from_socket,transparent.inputs['Color'])
        else:transparent.inputs['Color'].default_value=p.inputs['Base Color'].default_value
        camera_surface=nodes.get('Window interior/exterior') or p
        links.new(path.outputs['Is Shadow Ray'],mix.inputs[0]);links.new(camera_surface.outputs[0],mix.inputs[1]);links.new(transparent.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])
        mat['offline_light_model']='Visible photographic RGB used as coloured transparent shadow filter; spectral transmission not measured.'
        count+=1
    return count

def configure_export_glass():
    for mat in bpy.data.materials:
        if not mat.use_nodes:continue
        nodes=mat.node_tree.nodes
        if not (nodes.get('Offline coloured transmission') or nodes.get('Window interior/exterior')):continue
        p=nodes.get('Principled BSDF');out=next((n for n in nodes if n.type=='OUTPUT_MATERIAL'),None)
        if p and out:mat.node_tree.links.new(p.outputs[0],out.inputs['Surface'])

def refine_existing_scene():
    """Apply the same v3 light balance when comparing a saved earlier model."""
    from mathutils import Vector
    scene=bpy.context.scene
    if scene.world and scene.world.use_nodes:
        nodes=scene.world.node_tree.nodes;links=scene.world.node_tree.links
        nodes['Background'].inputs[1].default_value=.22
        # Displayed blue sky is separated from the lower-intensity diffuse fill.
        sky=nodes.get('Visible Mediterranean sky') or nodes.new('ShaderNodeBackground')
        sky.name='Visible Mediterranean sky';sky.inputs[0].default_value=(.075,.23,.5,1);sky.inputs[1].default_value=1.
        ray=nodes.get('Sky camera selector') or nodes.new('ShaderNodeLightPath');ray.name='Sky camera selector'
        mix=nodes.get('Camera sky mix') or nodes.new('ShaderNodeMixShader');mix.name='Camera sky mix'
        out=next(n for n in nodes if n.type=='OUTPUT_WORLD')
        links.new(ray.outputs['Is Camera Ray'],mix.inputs[0]);links.new(nodes['Background'].outputs[0],mix.inputs[1]);links.new(sky.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs[0])
    for ob in scene.objects:
        if ob.type!='LIGHT':continue
        if ob.name.startswith('Window broad sky fill'):ob.data.energy=500
        elif ob.name.startswith('Window colored transmission'):ob.data.energy=650 if ob.location.y>0 else 480
        elif ob.name.startswith('Vault diffuse sky fill'):ob.data.energy=850
        elif ob.name.startswith('Apse warm daylight'):ob.data.energy=1600
        elif ob.name.startswith('Glory entrance fill'):ob.data.energy=900
        elif ob.data.type=='SUN':
            ob.data.energy=3.0;ob.data.angle=.010
            ob.rotation_euler=Vector((.22,-.84,-.495)).normalized().to_track_quat('-Z','Y').to_euler()
    # A large north-eastern sky source restores readable shade-side stone.
    # It represents diffuse open sky, not another sun, and is explicitly artistic.
    fill=bpy.data.objects.get('Nativity open sky diffuse')
    if not fill:
        data=bpy.data.lights.new('Nativity open sky diffuse','AREA')
        fill=bpy.data.objects.new(data.name,data);scene.collection.objects.link(fill)
    fill.data.energy=65000;fill.data.shape='DISK';fill.data.size=90
    fill.data.color=(.84,.91,1.)
    fill.location=(52,-105,105)
    fill.rotation_euler=(Vector((52,-25,55))-fill.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.exposure=.20
    return configure_glass_shadows()
