"""Derive the Two Sisters wall stucco (sebka lattice) from the bundled reference photograph.

Usage: python3 tools/sisters_stucco.py public/photos/sisters-hall.webp public/textures
Source: https://commons.wikimedia.org/wiki/File:Alhambra_Hall_of_Two_Sisters_DSCF6969.jpg (R Prazeres, CC BY-SA 4.0)
Crops the lower-left wall panel (about 2.0 x 2.1 m at ~180 px/m), flattens the lamp falloff and
lifts it to the cream of the carved plaster. The runtime mirrors it at the edges (the lattice is
mirror-symmetric), so no seamless period has to be found.
"""
import sys
from PIL import Image, ImageEnhance
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from abencerrajes_tiles import flatten

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB')
panel = im.crop((250, 1010, 608, 1390)).resize((1024, 1087), Image.LANCZOS)
panel = flatten(panel, 70, 1.85)
panel = ImageEnhance.Color(panel).enhance(.55)
panel = ImageEnhance.Contrast(panel).enhance(1.25)
panel.save(f'{out}/sisters-sebka.jpg', quality=86)
