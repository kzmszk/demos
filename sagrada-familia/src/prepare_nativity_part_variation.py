"""CPU-only headroom maps for subtle Nativity part variations.

Original V11 PBR images are immutable. Four derived maps retain their exact
spatial grain/weather patterns, with only a neutral linear lightness headroom
or constant roughness headroom. Six bounded material factors in exterior.py
recover the desired +/-5% lightness and +/-0.02 roughness without the glTF
exporter's >1 factor clamp. No photograph, noise, stain or shadow is added.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear(a):
    return np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)


def srgb(a):
    return np.where(a <= .0031308, a*12.92, 1.055*np.maximum(a, 0)**(1/2.4)-.055)


def main():
    textures = ROOT/'assets/textures'
    dest = textures/'nativity_part_variation_v12'
    dest.mkdir(parents=True, exist_ok=True)
    source = json.loads((textures/'stone_pbr_web_v11/profile.json').read_text())
    manifest = {
        'name': 'nativity_part_variation_v12',
        'authorship': 'Original procedural derivatives of original V11 stone PBR; no photographic pixels.',
        'generator': 'src/prepare_nativity_part_variation.py',
        'purpose': 'Headroom permits valid glTF factors <=1 for small positive/negative part variation; maps are never displayed without calibrated factors.',
        'operation': {'base': 'Decode sRGB, multiply linear RGB by1.08, re-encode sRGB to8-bit PNG.',
                      'rough': 'Add0.03 to non-color roughness, clamp0..1 and encode8-bit PNG.',
                      'normal': 'Original normal image and shader strength reused unchanged.'},
        'approximation': 'Restrained photographic interpretation, not measured weathering, quarry albedo or roughness.',
        'materials': {},
    }
    for key in ('nativity_stone', 'nativity_stone_detail'):
        old = source['materials'][key]
        row = {'source_key': key, 'source': {}, 'derived': {},
               'normal': old['normal'], 'normal_strength': old['normal_strength']}
        for channel in ('base', 'rough'):
            p = textures/old[channel]['file']
            assert sha(p) == old[channel]['sha256']
            mode = 'RGB' if channel == 'base' else 'L'
            a = np.asarray(Image.open(p).convert(mode), dtype=float)/255
            if channel == 'base':
                out = np.round(np.clip(srgb(linear(a)*1.08), 0, 1)*255).astype('uint8')
                row['source_linear_rgb_mean'] = linear(a).mean((0, 1)).tolist()
                row['anchor_linear_rgb_mean'] = linear(out.astype(float)/255).mean((0, 1)).tolist()
            else:
                out = np.round(np.clip(a+.03, 0, 1)*255).astype('uint8')
                row['source_roughness_mean'] = float(a.mean())
                row['anchor_roughness_mean'] = float(out.mean()/255)
            target = dest/(key+'_anchor_'+channel+'.png')
            Image.fromarray(out).save(target, optimize=True)
            row['source'][channel] = {'file': old[channel]['file'], 'sha256': sha(p)}
            row['derived'][channel] = {'file': str(target.relative_to(textures)), 'sha256': sha(target), 'size_px': list(out.shape[:2])}
            assert sha(p) == old[channel]['sha256']
        manifest['materials'][key] = row
    (dest/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'maps': 4, 'manifest': str(dest/'manifest.json'), 'source_images_unchanged': True}))


if __name__ == '__main__':
    main()
