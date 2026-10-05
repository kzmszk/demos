"""Generate an opt-in, original stone PBR study without changing V10 assets.

CPU-only: run with the existing harbor Python (numpy/Pillow available).
Each1K tile represents the existing2m UV period. Periodic narrow-band mineral
fields replace nearly uniform microscopic noise; broad plaster-like clouds,
painted shadows, fake masonry joints and photograph processing are excluded.
These are photo-informed appearance estimates, not measured quarry scans.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from materials import STONE_SPECS

# Roughness and final normal tilt retain the distinction between polished
# structural stone, worked stone, concrete, and weathered historic fabric.
# Values are restrained visual estimates from the existing official photographs.
# roughness mean, roughness std, shader normal strength, final tilt RMS degrees
RESPONSE={
 'sandstone':(.73,.035,.55,3.2), 'granite':(.46,.048,.45,2.4),
 'basalt':(.50,.035,.45,2.2), 'porphyry':(.42,.045,.45,2.3),
 'stone':(.78,.045,.60,4.2), 'stone_light':(.74,.040,.55,3.4),
 'stone_dark':(.84,.050,.60,4.3), 'vault':(.79,.030,.48,2.8),
 'floor':(.34,.024,.32,1.4), 'concrete':(.86,.048,.55,3.7),
 'nativity_stone':(.86,.060,.65,5.0),
 'nativity_stone_detail':(.82,.055,.62,4.6),
}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    size=1024;tile_metres=2.0;texel=tile_metres/size
    base=ROOT/'assets/textures';dest=base/'stone_pbr_web_v11';dest.mkdir(exist_ok=True)
    protected=[base/(name+'_'+kind+'.png') for name in STONE_SPECS for kind in ('base','rough','normal')]
    protected+=list(base.glob('glass*'))+[base/'window_banks.json',ROOT/'src/glazing.py']
    protected=[p for p in protected if p.is_file()]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    fx=np.fft.fftfreq(size,d=texel)[None,:];fy=np.fft.fftfreq(size,d=texel)[:,None]
    frequency=np.sqrt(fx*fx+fy*fy)

    def standardize(a):
        a=a-a.mean();return a/max(float(a.std()),1e-8)

    def field(rng,wavelength,spread=.38):
        # No DC or very-low-frequency cloud layer: centered frequency bands
        # keep the texture granular rather than looking like peeling plaster.
        f0=1/wavelength
        spectrum=np.exp(-.5*(np.log(np.maximum(frequency,1e-8)/f0)/spread)**2)
        spectrum[frequency<f0*.42]=0
        a=np.fft.ifft2(np.fft.fft2(rng.normal(size=(size,size)))*spectrum).real
        return standardize(a)

    def save(a,path):
        image=Image.fromarray(a)
        temporary=path.with_name(path.name+'.pending')
        image.save(temporary,format='PNG',optimize=True);temporary.replace(path)
        with Image.open(path) as check:check.verify()

    rows=[];profiles={};comparison=Image.new('RGB',(960,12*134+74),(239,239,235));draw=ImageDraw.Draw(comparison)
    draw.text((16,12),'STONE PBR STUDY | V10 albedo / opt-in web_v11 albedo / web_v11 normal',fill=(30,30,30))
    draw.text((16,30),'Raw texture swatches, NOT rendered appearance. 2m tile; base RGB means preserved.',fill=(55,55,55))
    for index,(name,(rgb,oldrough,seed,grain_amount)) in enumerate(STONE_SPECS.items()):
        rng=np.random.default_rng(seed+11000)
        fine=field(rng,.008);grain=field(rng,.027)
        small=field(rng,.085);medium=field(rng,.22)
        original=np.asarray(Image.open(base/(name+'_base.png')).convert('RGB'),dtype=float)
        target=original.mean((0,1))
        detail=1.0*fine+2.1*grain+2.2*small+1.6*medium
        height=.045*fine+.25*grain+.18*small+.10*medium
        if name in ('granite','porphyry'):
            dark=np.maximum(0,-fine-.55)**1.20
            bright=np.maximum(0,grain-1.05)**1.15
            detail+=-5.6*dark+6.5*bright
            height+=.045*(bright-dark)
        elif name=='basalt':
            detail=.7*fine+1.6*grain+1.7*small+1.2*medium-2.2*np.maximum(0,-grain-1.3)
        elif name=='vault':
            detail=.7*fine+1.25*grain+1.7*small+1.1*medium
        elif name=='floor':
            detail=.45*fine+.9*grain+1.2*small+1.0*medium
        weather=np.zeros_like(detail)
        if name.startswith('nativity_stone') or name=='stone_dark':
            # Scattered neutral accumulated weathering, assembled from smaller
            # fields rather than a single huge stain. Mean color is restored
            # below; no whole-building brown multiplier or baked AO is used.
            weather=np.clip(np.maximum(0,-small-.25)*np.maximum(0,medium+.20),0,2.6)
            detail-=7.5*weather
            detail+=.65*grain
            height-=.09*weather
        detail-=detail.mean()
        colour=np.stack([target[c]+detail for c in range(3)],axis=-1)
        if name=='porphyry':
            tint=grain*.55;tint-=tint.mean()
            colour[:,:,0]+=tint;colour[:,:,2]-=tint*.35
        if name=='floor':
            # Retain the existing1m paving-grid location and modest4mm seams.
            y,x=np.indices((size,size));joint=(x%512<2)|(y%512<2)
            colour[joint]-=12;height[joint]-=.30
        colour+=target-colour.mean((0,1))
        colour=np.clip(np.rint(colour),0,255).astype('uint8')
        rough_mean,rough_std,normal_strength,tilt_target=RESPONSE[name]
        rough_field=standardize(.60*grain+.30*small+.35*medium+.40*weather)
        rough=np.clip(rough_mean+rough_std*rough_field,.15,.97)
        rough=np.rint(rough*255).astype('uint8')
        gx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*texel)
        gy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*texel)
        rms=max(float(np.sqrt((gx*gx+gy*gy).mean())),1e-8)
        gain=math.tan(math.radians(tilt_target))/(normal_strength*rms)
        normals=np.stack((-gx*gain,-gy*gain,np.ones_like(gx)),axis=-1)
        normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
        normal=np.clip(np.rint((normals*.5+.5)*255),0,255).astype('uint8')
        assets={}
        for channel,array in [('base',colour),('rough',rough),('normal',normal)]:
            path=dest/(name+'_'+channel+'.png');save(array,path)
            assets[channel]={'file':str(path.relative_to(base)),'sha256':sha(path)}
        rgb_mean=colour.mean((0,1));gray=colour.astype(float).mean(2)
        decoded=normal.astype(float)/255*2-1
        tilt=np.degrees(np.arctan2(np.linalg.norm(decoded[:,:,:2]*normal_strength,axis=2),decoded[:,:,2]))
        stats={'material':name,'base_mean_srgb255':rgb_mean.round(3).tolist(),
            'baseline_mean_srgb255':target.round(3).tolist(),
            'maximum_mean_channel_drift':round(float(np.max(np.abs(rgb_mean-target))),4),
            'albedo_std255':round(float(gray.std()),3),
            'albedo_mip16_std255':round(float(np.asarray(Image.fromarray(gray.astype('uint8')).resize((16,16),Image.Resampling.BOX)).std()),3),
            'roughness_mean':round(float(rough.mean()/255),4),'roughness_std':round(float(rough.std()/255),4),
            'normal_strength':normal_strength,'effective_normal_tilt_rms_degrees':round(float(np.sqrt((tilt**2).mean())),3)}
        assert stats['maximum_mean_channel_drift']<.05,(name,stats)
        rows.append(stats);profiles[name]={**assets,'normal_strength':normal_strength,'roughness':rough_mean}
        y=65+index*134
        draw.text((12,y+4),name,fill=(30,30,30))
        for x,a in [(190,original.astype('uint8')),(440,colour),(690,normal)]:
            # Small contiguous regions display real grain; not false distance QA.
            swatch=Image.fromarray(a).crop((0,0,256,128));comparison.paste(swatch,(x,y))
    after={str(p.relative_to(ROOT)):sha(p) for p in protected}
    assert before==after,'Protected V10/glazing assets changed during this study'
    profile={'schema_version':1,'name':'web_v11','opt_in':True,'tile_metres':tile_metres,'size_px':[size,size],
        'purpose':'Original photo-informed stone PBR detail study for actual Chrome A/B; not final approval.',
        'source_profile':'V10 base-color means preserved for all12 stone types.',
        'authorship':'Original deterministic procedural mineral fields; no photographs or purchased assets used.',
        'references':['assets/reference/qa_tree_vault.jpg','assets/reference/qa_nativity_2026_08_09_cc0.jpg','assets/reference/qa_passion_close.jpg'],
        'limitations':'Appearance estimates only. No painted cavity shadows or AO. Lighting/contact contrast must be evaluated separately. No giant cloud/noise fields or manufactured masonry joints.',
        'materials':profiles,'statistics':rows,'protected_v10_sha256':before,
        'protected_v10_unchanged':True,'generation_script':'src/prepare_stone_pbr_web_v11.py'}
    (dest/'profile.json').write_text(json.dumps(profile,indent=2,ensure_ascii=False)+'\n')
    comparison.save(dest/'raw_texture_comparison.png')
    print(json.dumps({'profile':str(dest/'profile.json'),'textures':36,'protected_assets_verified':len(before),'statistics':rows},indent=2))

if __name__=='__main__':main()
