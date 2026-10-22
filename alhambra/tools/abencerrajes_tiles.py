"""Derive the Abencerrajes dado textures from R Prazeres' photograph (CC BY-SA 4.0).

Usage: python3 abencerrajes_tiles.py tools/research/abencerrajes-DSCF8810.jpg public/textures
Source: https://commons.wikimedia.org/wiki/File:Alhambra_Hall_of_the_Abencerrajes_DSCF8810.jpg
Crops 4 x 2 pattern units of the field and a four-tile run of the border, resamples the
foreshortened units to square, divides out the photo's broad lighting falloff (wrapped
blur, so the repeat stays seamless) and lifts the glazed white ground.
"""
import sys
from PIL import Image, ImageFilter, ImageEnhance

def flatten(img, radius, gain):
    w, h = img.size
    big = Image.new('RGB', (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            big.paste(img, (i * w, j * h))
    light = big.convert('L').filter(ImageFilter.GaussianBlur(radius)).crop((w, h, 2 * w, 2 * h))
    mean = sum(light.get_flattened_data() if hasattr(light, 'get_flattened_data') else light.getdata()) / (w * h)
    px = img.load(); lp = light.load(); res = Image.new('RGB', (w, h)); rp = res.load()
    for y in range(h):
        for x in range(w):
            k = gain * mean / max(8, lp[x, y])
            r, g, b = px[x, y]
            rp[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))
    return res

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
field = im.crop((20, 1190, 852, 1666)).resize((1024, 512), Image.LANCZOS)
field = flatten(field, 90, 1.55)
field = ImageEnhance.Color(field).enhance(1.25)
field = ImageEnhance.Contrast(field).enhance(1.12)
field.save(f'{out}/abencerrajes-dado.jpg', quality=88)
border = im.crop((1456, 452, 1872, 552)).resize((1024, 246), Image.LANCZOS)  # four well-glazed tiles
border = flatten(border, 40, 1.45)
border = ImageEnhance.Color(border).enhance(1.2)
border.save(f'{out}/abencerrajes-border.jpg', quality=88)
