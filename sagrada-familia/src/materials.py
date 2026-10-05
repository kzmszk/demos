"""Original, deterministic, glTF-compatible material library.

build_materials(root) returns the shared M dict.  Run this module with an ordinary
Python containing numpy and Pillow, --textures-only, to regenerate original tiles.
Stone maps are authored procedural tiles. Separately attributed licensed photographs
provide the actual glass artwork; see docs/MATERIAL_SOURCES.json. Stone values are
kept below pure white; illumination is supplied by the lighting rig.

V10 remains the default. Opt in to the derived stone-only study with
SAGRADA_STONE_PROFILE=web_v11 or build_materials(root, stone_profile='web_v11').
"""
from pathlib import Path
import math

STONE_SPECS = {
    'sandstone': ((185, 170, 145), .78, 101, .80),
    'granite': ((173, 174, 171), .54, 103, 1.15),
    'basalt': ((101, 104, 101), .59, 107, .65),
    'porphyry': ((155, 126, 118), .48, 109, 1.05),
    'stone': ((180, 165, 143), .87, 113, 1.10),
    'stone_light': ((205, 195, 175), .80, 127, .72),
    'stone_dark': ((139, 127, 108), .90, 131, 1.15),
    'vault': ((222, 208, 182), .83, 137, .42),
    'floor': ((185, 180, 168), .37, 139, .36),
    'concrete': ((177, 177, 169), .90, 149, .66),
    # Older Nativity fabric, compared with the2026-08-09 exterior reference.
    # Retain warm ochre-grey stone; avoid black grime or uniform orange tint.
    'nativity_stone': ((158, 140, 111), .89, 173, 1.05),
    'nativity_stone_detail': ((170, 151, 121), .85, 179, .90),
}

def generate_textures(root, size=1024, only=None):
    """Seamless Fourier noise + mineral-scale inclusions, original procedural art."""
    import numpy as np
    from PIL import Image
    dest=Path(root)/'assets'/'textures'; dest.mkdir(parents=True, exist_ok=True)
    def noise(rng, cutoff):
        v=rng.normal(0,1,(size,size))
        fy=np.fft.fftfreq(size)[:,None]; fx=np.fft.fftfreq(size)[None,:]
        f=np.exp(-(fx*fx+fy*fy)/(cutoff*cutoff))
        n=np.fft.ifft2(np.fft.fft2(v)*f).real
        return n/max(float(n.std()),.0001)
    def save_atomic(image,path):
        tmp=path.with_name(path.name+'.pending')
        image.save(tmp,format='PNG',optimize=True);tmp.replace(path)
    for name,(rgb,rough,seed,grain) in STONE_SPECS.items():
        if only and name not in only:continue
        rng=np.random.default_rng(seed)
        cloud=noise(rng,.011); medium=noise(rng,.13); fine=noise(rng,.43)
        height=.28*medium+.30*fine+.06*cloud
        variation=1.6*cloud+grain*(2.6*medium+1.5*fine)
        if name in ('granite','porphyry'):
            crystals=noise(rng,.27)
            dark=np.maximum(0,-crystals-1.05)*10
            light=np.maximum(0,crystals-1.35)*12
            variation+=light-dark; height+=(light-dark)/35
        if name in ('sandstone','stone','stone_dark'):
            y=np.arange(size)[:,None]/size
            variation+=1.2*np.sin(y*math.tau*31+.35*cloud)
        patina=None
        if name.startswith('nativity_stone'):
            # Original anisotropic low-frequency mottling. Long vertical UV
            # streaks suggest accumulated weather exposure without painting
            # artificial cracks, black outlines, or high-contrast speckle.
            fy=np.fft.fftfreq(size)[:,None];fx=np.fft.fftfreq(size)[None,:]
            weather=np.fft.ifft2(np.fft.fft2(rng.normal(0,1,(size,size)))*np.exp(-(fx/.020)**2-(fy/.0025)**2)).real
            weather/=max(float(weather.std()),.0001)
            patina=np.clip(.48*cloud+.32*weather+.10*medium,-1.8,1.8)
            variation+=4.2*patina
            pits=np.maximum(0,-fine-1.45)
            variation-=2.4*pits;height-=.23*pits
        base=np.empty((size,size,3),dtype=np.float64)
        for c in range(3):base[:,:,c]=rgb[c]+variation*(1.0 if c==0 else .92)
        if patina is not None:
            base[:,:,0]+=.55*patina;base[:,:,2]-=.70*patina
        if name=='porphyry':
            base[:,:,0]+=1.8*medium; base[:,:,2]-=.4*cloud
        if name=='floor':
            y,x=np.indices((size,size)); seam=(x%512<2)|(y%512<2)
            base[seam]*=.88; height[seam]-=2.0
            variation[seam]+=12
        save_atomic(Image.fromarray(np.clip(base,0,255).astype('uint8'),'RGB'),dest/(name+'_base.png'))
        rv=np.clip(rough*255+variation*.55+(3.0*patina if patina is not None else 0),0,255).astype('uint8')
        save_atomic(Image.fromarray(rv,'L'),dest/(name+'_rough.png'))
        dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.14
        dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.14
        normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        save_atomic(Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8'),'RGB'),dest/(name+'_normal.png'))

def _linear(c):
    return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4

def configure_window_sides(material):
    """Keep the approved interior surface, add subdued reflective daylight glass.

    Pane front faces point OUTSIDE (glazing.py normalizes their winding before
    the integrator's Y reflection/winding repair). Geometry.Backfacing therefore
    selects the existing interior Principled without changing any of its inputs.
    The glTF exporter uses that interior shader as a fallback; the runtime applies
    the equivalent FRONT_FACING selection. This is an appearance approximation,
    not measured transmission or an exterior photographic texture.
    """
    nodes=material.node_tree.nodes;links=material.node_tree.links
    inside=nodes.get('Principled BSDF')
    out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    outside=nodes.new('ShaderNodeBsdfPrincipled');outside.name='Daylight exterior glass'
    outside.label='Exterior: no emission, subdued colour, sky reflections'
    outside.inputs['Roughness'].default_value=.22
    outside.inputs['Metallic'].default_value=0
    outside.inputs['IOR'].default_value=1.5
    outside.inputs['Specular IOR Level'].default_value=.5
    outside.inputs['Coat Weight'].default_value=.25
    outside.inputs['Coat Roughness'].default_value=.12
    outside.inputs['Emission Strength'].default_value=0
    scale=nodes.new('ShaderNodeVectorMath');scale.name='Exterior artwork attenuation';scale.operation='SCALE'
    scale.inputs['Scale'].default_value=.045
    tint=nodes.new('ShaderNodeVectorMath');tint.name='Exterior neutral sky-grey glass';tint.operation='ADD'
    tint.inputs[1].default_value=(.012,.018,.022)
    if inside.inputs['Base Color'].is_linked:
        links.new(inside.inputs['Base Color'].links[0].from_socket,scale.inputs[0])
    else:scale.inputs[0].default_value=inside.inputs['Base Color'].default_value[:3]
    links.new(scale.outputs['Vector'],tint.inputs[0]);links.new(tint.outputs['Vector'],outside.inputs['Base Color'])
    geometry=nodes.new('ShaderNodeNewGeometry');geometry.name='Window face direction'
    mix=nodes.new('ShaderNodeMixShader');mix.name='Window interior/exterior'
    mix.label='Front=daylight exterior; Back=approved interior'
    links.new(geometry.outputs['Backfacing'],mix.inputs[0])
    links.new(outside.outputs['BSDF'],mix.inputs[1]);links.new(inside.outputs['BSDF'],mix.inputs[2])
    links.new(mix.outputs[0],out.inputs['Surface'])
    material['window_sidedness']='Outward normal: front=dark reflective exterior, back=unchanged approved interior'
    material['exterior_response']='linear base=sourceRGB*0.045+(0.012,0.018,0.022); emission0; roughness0.22; coat0.25; IOR1.5'

def build_materials(root, stone_profile=None):
    import bpy
    root=Path(root); M={}
    # V10 is the unchanged default. The stone-only study is explicitly opt-in,
    # leaving all glazing/photo/emission material construction below untouched.
    import os,json
    selected=stone_profile or os.environ.get('SAGRADA_STONE_PROFILE','v10')
    stone_override={}
    if selected!='v10':
        if selected!='web_v11':raise ValueError('Unknown stone profile: '+str(selected))
        profile_path=root/'assets/textures/stone_pbr_web_v11/profile.json'
        profile=json.loads(profile_path.read_text())
        stone_override=profile['materials']
        if set(stone_override)!=set(STONE_SPECS):raise ValueError('Incomplete stone PBR profile')
    def mat(key, title, color, rough=.75, metal=0., emission=0.):
        m=bpy.data.materials.new(title); m.use_nodes=True
        rgba=tuple(_linear(v) for v in color)+(1.,)
        m.diffuse_color=rgba; m.use_backface_culling=False
        p=m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=rgba
        p.inputs['Roughness'].default_value=rough
        p.inputs['Metallic'].default_value=metal
        if emission:
            p.inputs['Emission Color'].default_value=rgba
            p.inputs['Emission Strength'].default_value=emission
        M[key]=m
        return m
    def image_input(m, filename, socket, noncolor=False, normal_strength=.34):
        path=root/'assets'/'textures'/filename
        if not path.exists():raise FileNotFoundError('Generate material tiles first: '+str(path))
        p=m.node_tree.nodes.get('Principled BSDF')
        n=m.node_tree.nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(str(path),check_existing=True)
        n.image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
        n.interpolation='Linear'; n.extension='REPEAT'
        if socket=='Normal':
            b=m.node_tree.nodes.new('ShaderNodeNormalMap'); b.inputs['Strength'].default_value=normal_strength
            m.node_tree.links.new(n.outputs['Color'],b.inputs['Color']); m.node_tree.links.new(b.outputs['Normal'],p.inputs['Normal'])
        else:m.node_tree.links.new(n.outputs['Color'],p.inputs[socket])
    for key,(rgb,rough,seed,grain) in STONE_SPECS.items():
        title={'sandstone':'Montjuïc sandstone · side-aisle columns','granite':'Light grey granite · main nave columns',
        'basalt':'Dark grey basalt · crossing perimeter','porphyry':'Red porphyry · four crossing columns',
        'vault':'Pale warm Catalan tiled vault surface','stone':'Warm worked exterior stone',
        'stone_light':'Fresh pale stone arrises','stone_dark':'Sheltered weathered stone',
        'floor':'Honed pale stone paving','concrete':'Unfinished construction concrete',
        'nativity_stone':'Weathered warm Nativity sandstone · historic fabric',
        'nativity_stone_detail':'Weathered warm Nativity arrises · historic carved detail'}[key]
        override=stone_override.get(key)
        m=mat(key,title,tuple(v/255 for v in rgb),override['roughness'] if override else rough)
        image_input(m,override['base']['file'] if override else key+'_base.png','Base Color')
        image_input(m,override['rough']['file'] if override else key+'_rough.png','Roughness',True)
        image_input(m,override['normal']['file'] if override else key+'_normal.png','Normal',True,
                    normal_strength=override['normal_strength'] if override else .34)
        if override:m['stone_profile']=selected
    mat('bronze','Patinated bronze',(.35,.29,.16),.46,.72)
    mat('bronze_leaf','Green patinated cast bronze · Nativity doors',(.19,.30,.20),.69,.50)
    mat('bronze_leaf_light','Raised green bronze leaf veins',(.32,.42,.27),.62,.43)
    mat('iron','Dark architectural metal',(.17,.18,.17),.54,.68)
    mat('glass_came','Slender blackened lead cames',(.075,.080,.072),.56,.32)
    mat('ceramic_white','White ceramic and glass cross surface',(.92,.925,.91),.25,.06)
    mat('mosaic_gold','Gold Venetian glass mosaic',(.72,.55,.22),.25,.65)
    mat('mosaic_green','Green Venetian glass mosaic',(.29,.47,.31),.27,.12)
    mat('mosaic_red','Red ceramic fruit mosaic',(.64,.22,.15),.3,.03)
    mat('scaffold','Galvanised scaffold steel',(.53,.55,.55),.43,.74)
    mat('timber','Warm construction and furnishing timber',(.37,.245,.13),.66)
    mat('shadow','Shadowed deep opening',(.105,.106,.10),.95)
    mat('floor_border','Paving border',(.47,.46,.42),.40)
    mat('brass','Satin gilded bronze',(.66,.52,.23),.35,.70)
    # Base named materials used by other modelling modules.
    glass={'blue':(.10,.33,.70),'green':(.21,.58,.39),'red':(.69,.115,.075),
           'orange':(.90,.42,.09),'gold':(.89,.72,.27),'white':(.80,.87,.85)}
    for key,color in glass.items():mat('glass_'+key,'Glass · '+key,color,.30,0,.34)
    # 36 pieces in each palette, shared by all windows. Lower panes remain rich,
    # high pieces blend towards clear; they are original interpretations, not
    # facsimiles or scans of Vila-Grau's protected artworks.
    palettes={
        'cool':[(.085,.20,.52),(.08,.36,.65),(.15,.57,.68),(.18,.50,.35),(.44,.67,.30),(.38,.57,.73),(.65,.77,.79),(.14,.26,.45),(.26,.40,.57)],
        'warm':[(.58,.08,.055),(.78,.18,.04),(.89,.37,.04),(.92,.56,.07),(.86,.71,.23),(.79,.35,.18),(.91,.79,.43),(.58,.22,.13),(.76,.51,.21)],
        'gold':[(.72,.52,.09),(.81,.67,.22),(.89,.77,.37),(.83,.80,.55),(.59,.64,.32),(.86,.71,.39),(.92,.88,.63),(.57,.63,.47),(.80,.84,.66)],
        'clear':[(.74,.83,.83),(.87,.89,.84),(.83,.86,.84),(.78,.84,.86),(.89,.89,.83),(.79,.85,.79),(.84,.87,.84),(.72,.79,.81),(.88,.89,.84)],
    }
    for family,colors in palettes.items():
        # The actual pane geometry uses vertex colour to retain subtle variance
        # with one glTF draw material per palette, rather than 36 draw calls.
        m=mat('glass_'+family+'_colored','Original abstract '+family+' glazing · vertex colour',(.7,.7,.7),.27,0,.40 if family!='clear' else .10)
        v=m.node_tree.nodes.new('ShaderNodeVertexColor');v.layer_name='Col'
        p=m.node_tree.nodes.get('Principled BSDF')
        m.node_tree.links.new(v.outputs['Color'],p.inputs['Base Color'])
        m.node_tree.links.new(v.outputs['Color'],p.inputs['Emission Color'])
        configure_window_sides(m)
        for tint in range(4):
            for index,color in enumerate(colors):
                mix=tint*.15
                color=tuple(c*(1-mix)+.87*mix for c in color)
                key='glass_%s_%02d'%(family,tint*9+index)
                mat(key,'Vila-Grau-inspired %s pane %02d · original'%(family,tint*9+index),color,.27,0,.40 if family!='clear' else .10)
    # Photographed artwork remains intact. Modelled glass apertures use UV
    # rectification; source stone, people and rails are never used as facade art.
    import json
    bank_path=root/'assets/textures/window_banks.json'
    banks=json.loads(bank_path.read_text()) if bank_path.exists() else {}
    photo_sources={key:data for key,data in banks.items()}
    photo_sources.update({key+'_rose':data['rose_source'] for key,data in banks.items() if 'rose_source' in data})
    for family,data in photo_sources.items():
        filename=data['texture']
        if (root/'assets/textures'/filename).exists():
            credit=data.get('attribution','Ribeiro2014 CC BY-SA3.0')
            m=mat('glass_photo_'+family,'Vila-Grau '+family+' photographed bank · '+credit,(.8,.8,.8),.29,0,.80)
            image_input(m,filename,'Base Color')
            p=m.node_tree.nodes.get('Principled BSDF')
            n=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE')
            m.node_tree.links.new(n.outputs['Color'],p.inputs['Emission Color'])
            configure_window_sides(m)
    return M

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--textures-only',action='store_true')
    parser.add_argument('--only',nargs='+',choices=tuple(STONE_SPECS),help='Regenerate only selected material tiles')
    parser.add_argument('--root',default=str(Path(__file__).resolve().parents[1])); args=parser.parse_args()
    if args.textures_only:generate_textures(args.root,only=args.only)
