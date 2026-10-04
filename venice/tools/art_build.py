"""Artworks (paintings, mosaics, dials) as one KTX2 texture array (ETC1S, 1024², mipmapped) + art.json.
python art_build.py OUT_DIR      -> OUT_DIR/art.ktx2, OUT_DIR/art.json   (layer per item; aspect stored for UVs)

Items reference files downloaded with commons_fetch.py (licences in each folder's manifest.json); the credits
page is generated from the same list."""
import os, sys, json, subprocess
from PIL import Image, ImageOps

KTX = '/home/kazu/work/venice-assets/tools/KTX-Software-4.4.2-Linux-x86_64/bin/ktx'
C = '/home/kazu/work/venice-assets/commons'
S = 1024

# key: (folder, file, crop (x0, y0, x1, y1) as fractions or None)
ITEMS = {
    # Caffè Florian — Sala degli Uomini Illustri: the ten portraits in their gilded oval frames
    **{f'ui{i}': ('florian', f'Sala_degli_Uomini_Illustri{i}.jpg', None) for i in range(1, 11)},
    # Sala delle Stagioni: Rosalba Carriera's Four Seasons
    'spring': ('florian', 'Spring_by_Rosalba_Carriera_Rijksdienst_voor_het_Cultureel_Erfgoed_NK1710.jpg', None),
    'summer': ('florian', 'Summer_by_Rosalba_Carriera_Rijksdienst_voor_het_Cultureel_Erfgoed_NK1711.jpg', None),
    'autumn': ('florian', 'Autumn_by_Rosalba_Carriera_Rijksdienst_voor_het_Cultureel_Erfgoed_NK1708.jpg', None),
    'winter': ('florian', 'Rosalba_Carriera_-_Winter_-_WGA04501.jpg', None),
    # Sala del Senato: allegories (Carlini's Progress from the room itself) and its painted ceiling
    'progress': ('florian', 'Sala_Senato_Caffè_Florian.jpg', None),
    'vigilance': ('florian', 'Rosalba_Carriera_-_Allegorie_der_Wachsamkeit.jpg', None),
    'charity': ('florian', 'Rosalba_Carriera_-_Charity_and_Justice.jpg', None),
    'pescivendola': ('florian', 'La_pescivendola_quadro_del_signor_Giulio_Carlini.jpg', None),
    'senato_ceiling': ('florian', 'Sala_del_Senato_soffitto_Caffè_Florian.jpg', (0.0, 0.0, 1.0, 1.0)),
    # Sala Cinese: chinoiseries
    'chin1': ('florian', 'François_Boucher_-_Chinoiserie_-_2573_OK_-_Museum_Boijmans_Van_Beuningen.jpg', None),
    'chin2': ('florian', 'Boucher-chinoiserie-Besançon.jpg', None),
    'chin3': ('florian', 'Chinoiserie_with_Figures_in_a_Landscape_MET_DP826913.jpg', None),
    'chin4': ('florian', 'Chinoiserie_scene_with_figures_in_a_landscape_MET_DP826703.jpg', None),
    'chin5': ('florian', 'François_Boucher_Der_galante_Chinese.jpg', None),
    # Sala Orientale
    'orient1': ('florian', 'Marastoni_Greek_woman_1850.jpg', None),
    'orient2': ('florian', 'Young_Woman_in_Oriental_Garb_1871_-_Edouard_Manet_Kunsthaus_Zürich_.jpg', None),
    'orient3': ('florian', 'Bathsheba_c.1827_by_Francesco_Hayez.jpg', None),
    # Pietro Longhi genre scenes (Sala Liberty / corridor)
    'longhi1': ('florian', 'Ca_Rezzonico_-_Il_rinoceronte_1751_-_Pietro_Longhi_.jpg', None),
    'longhi2': ('florian', 'Ca_Rezzonico_-_La_venditrice_di_essenze_-_Pietro_Longhi.jpg', None),
    'longhi3': ('florian', 'Ca_Rezzonico_-_Il_Ciarlatano_-_Pietro_Longhi.jpg', None),
    # Basilica di San Marco: three domes photographed from the floor (mapped back onto the hemispheres)
    'dome_pentecost': ('basilica', 'Mosaico_della_cupola_di_San_Marco_prima_del_1976_-_Archivio_Accademia_delle_Scienze_Torino_Millon_48_13_252.jpg', None),
    'dome_emmanuel': ('basilica', 'Venezia_Basilica_di_San_Marco_Innen_Emmanuelkuppel_3.jpg', None),
    'dome_ascension': ('basilica', 'Venezia_Basilica_di_San_Marco_Innen_Auferstehungskuppel_4.jpg', None),
}

def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    tmp = os.path.join('/home/kazu/work/venice-assets/build', 'art'); os.makedirs(tmp, exist_ok=True)
    extra = json.load(open(os.path.join(C, 'extra_items.json'))) if os.path.exists(os.path.join(C, 'extra_items.json')) else {}
    items = {**ITEMS, **{k: tuple(v) for k, v in extra.items()}}
    files = []; meta = {}
    for li, (key, (folder, fn, crop)) in enumerate(items.items()):
        im = Image.open(os.path.join(C, folder, fn)); im = ImageOps.exif_transpose(im).convert('RGB')
        if crop:
            w, h = im.size; im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
        aspect = im.width / im.height
        im = im.resize((S, S), Image.LANCZOS).transpose(Image.FLIP_TOP_BOTTOM); im.info = {}   # uv v=0 at the bottom
        p = os.path.join(tmp, f'{li:03d}_{key}.png'); im.save(p)
        files.append(p); meta[key] = {'layer': li, 'aspect': round(aspect, 4), 'src': f'{folder}/{fn}'}
        print(li, key, round(aspect, 3), flush=True)
    dst = os.path.join(out, 'art.ktx2')
    cmd = [KTX, 'create', '--format', 'R8G8B8_SRGB', '--layers', str(len(files)), '--generate-mipmap', '--encode', 'basis-lz', '--clevel', '2', '--qlevel', '160', '--assign-primaries', 'bt709'] + files + [dst]
    subprocess.run(cmd, check=True)
    json.dump({'size': S, 'items': meta}, open(os.path.join(out, 'art.json'), 'w'), indent=1)
    print(dst, os.path.getsize(dst) // 1024, 'KB')

if __name__ == '__main__':
    main()
