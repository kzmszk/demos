#!/usr/bin/env python3
"""Generate public/credits.html (standalone, Japanese by default, English via #en) from the data the build uses.

    python3 credits.py [OUT.html]          # python 3 standard library only; default OUT = ../public/credits.html

Everything about images, textures and the sky is read at run time, nothing is listed by hand here:
  * public/tex/art.json                       the images mapped onto walls and ceilings  ({key: {layer, aspect, src: "folder/file"}})
  * <assets>/commons/*/manifest.json          Wikimedia Commons licence records written by commons_fetch.py
                                              -> "images" = referenced by art.json, "references" = downloaded but only used for modelling
  * gen/materials.py  LAYERS                  the texture sets the build uses (second element of each tuple)
  * <assets>/textures/manifest.json           Poly Haven / ambientCG records
  * public/tex/sky_*.json (+ <assets>/sky)    which HDRI the sky was made from;  <assets>/hdri/manifest.json for its record
Re-run it after art_build.py: new images appear by themselves (La Fenice's move from "references" to "images").
Warnings (missing manifest entries, empty authors, ...) go to stderr; the exit status stays 0.
"""
import ast
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                                                # venice/
PUBLIC = ROOT / 'public'
ASSETS = Path(os.environ.get('VENICE_ASSETS', '/home/kazu/work/venice-assets'))   # raw assets, not in git
COMMONS, TEXTURES, HDRI = ASSETS / 'commons', ASSETS / 'textures', ASSETS / 'hdri'
WARN = []


def warn(msg):
    WARN.append(msg)
    print('credits: warning: ' + msg, file=sys.stderr)


def load_json(path, required=True):
    try:
        with open(str(path), encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        if required:
            raise SystemExit('credits: missing ' + str(path))
        return None
    except ValueError as e:
        raise SystemExit('credits: invalid JSON in %s: %s' % (path, e))


# ------------------------------------------------------------------------------------------ presentation data
# Where the images are, by the folder they were downloaded into (commons/<folder>/).
PLACES = {
    'florian': ('カフェ・フローリアン', 'Caffè Florian'),
    'basilica': ('サン・マルコ寺院（内部）', 'St Mark’s Basilica, interior'),
    'lunettes': ('サン・マルコ寺院 西正面のルネット', 'St Mark’s Basilica, lunettes of the west front'),
    'fenice': ('フェニーチェ劇場', 'La Fenice'),
}
# Caffè Florian's rooms, in the order of the enfilade.  Patterns match art.json keys (they come from art_build.py);
# a key that matches none simply gets no room heading.
FLORIAN_ROOMS = [   # (key pattern, JA gloss, Italian name)
    (r'spring|summer|autumn|winter', '四季の間', 'Sala delle Stagioni'),
    (r'ui\d+', '偉人の間', 'Sala degli Uomini Illustri'),
    (r'progress|vigilance|charity|pescivendola|senato_ceiling', '元老院の間', 'Sala del Senato'),
    (r'chin\d+', '中国の間', 'Sala Cinese'),
    (r'orient\d+', '東洋の間', 'Sala Orientale'),
    (r'longhi\d+', 'リバティの間', 'Sala Liberty'),
]
KEY_NOTE = {        # art.json key -> note under the title: the three domes photographed from the floor
    'dome_pentecost': ('聖霊降臨のドーム', 'Dome of Pentecost'),
    'dome_emmanuel': ('エマヌエルのドーム', 'Dome of the Emmanuel'),
    'dome_ascension': ('昇天のドーム', 'Dome of the Ascension'),
}
# texture sets the build generates itself instead of downloading:  (JA name, EN name, JA note, EN note)
PROCEDURAL = {'masegni': ('マゼーニ（ヴェネツィアの石畳）', 'Masegni, Venetian trachyte paving', 'この作品のために生成', 'Generated for this work')}
LICENSE_URLS = {
    'CC0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'MIT': 'https://opensource.org/license/mit',
    'Apache-2.0': 'https://www.apache.org/licenses/LICENSE-2.0',
    'BSD-3-Clause': 'https://opensource.org/license/bsd-3-clause',
    'ISC': 'https://opensource.org/license/isc-license-txt',
    'GPL': 'https://www.gnu.org/licenses/gpl-3.0.html',
    'LGPL-3.0': 'https://www.gnu.org/licenses/lgpl-3.0.html',
    'MIT-CMU': 'https://github.com/python-pillow/Pillow/blob/main/LICENSE',
    'ODbL': 'https://opendatacommons.org/licenses/odbl/1-0/',
}
SOURCE_URLS = {'Poly Haven': 'https://polyhaven.com', 'ambientCG': 'https://ambientcg.com'}
# software:  ([(name, url), ...], JA use, EN use, [licences])   (versions: tools/package.json and the venv)
SOFTWARE_PAGE = [
    ([('three.js', 'https://threejs.org')], '3Dエンジン（WebGPU 描画、シェーダー、影、後処理）', '3D engine: WebGPU rendering, shaders, shadows, post-processing', ['MIT']),
    ([('meshoptimizer', 'https://github.com/zeux/meshoptimizer')], 'メッシュの圧縮と展開', 'Mesh compression and decoding', ['MIT']),
    ([('Basis Universal', 'https://github.com/BinomialLLC/basis_universal')], 'テクスチャ（KTX2）のトランスコーダー', 'Texture (KTX2) transcoder', ['Apache-2.0']),
]
SOFTWARE_BUILD = [
    ([('Blender', 'https://www.blender.org')], '光の焼き込み（Cycles。頂点ごとの間接光）', 'Light baking (Cycles, per-vertex indirect light)', ['GPL']),
    ([('KTX-Software', 'https://github.com/KhronosGroup/KTX-Software')], 'KTX2 テクスチャの書き出し', 'KTX2 texture packing', ['Apache-2.0']),
    ([('esbuild', 'https://esbuild.github.io')], 'スクリプトのバンドル', 'Script bundling', ['MIT']),
    ([('shapely', 'https://shapely.readthedocs.io'), ('NumPy', 'https://numpy.org'), ('SciPy', 'https://scipy.org')], '形状と数値の処理', 'Geometry and numerics', ['BSD-3-Clause']),
    ([('triangle', 'https://rufat.be/triangle')], '三角形分割（Shewchuk の Triangle の Python バインディング）', 'Triangulation (Python bindings to Shewchuk’s Triangle)', ['LGPL-3.0']),
    ([('mapbox_earcut', 'https://github.com/skogler/mapbox_earcut_python')], 'ポリゴンの三角形分割', 'Polygon triangulation', ['ISC']),
    ([('Pillow', 'https://python-pillow.github.io'), ('OpenCV', 'https://opencv.org')], '画像処理', 'Image processing', ['MIT-CMU', 'Apache-2.0']),
]

# the page copy, (JA, EN).  <span class="nw"> keeps a licence name on one line.
NW = '<span class="nw">%s</span>'
TEXT = {
    'sub': ('出典とライセンス', 'Sources and licences'),
    'lede': ('ヴェネツィア本島を、地図データと、公開されている写真・素材から組み立てた3D再構成です。この作品が使っている出典とライセンスを、以下にまとめます。',
             'A 3D reconstruction of the main island of Venice, assembled from map data and openly licensed photographs and materials. The sources and licences of everything it uses are listed below.'),
    'map': ('建物の形と高さ、道、橋、運河、水面は、OpenStreetMap のデータから生成しています。教会や鐘楼の立体は、OpenStreetMap の 3D 建物パーツ（building:part）をもとにしています。',
            'Building footprints and heights, streets, bridges, canals and water are generated from OpenStreetMap data; the volumes of churches and bell towers come from its 3D building parts (building:part).'),
    'map_extract': ('データの取得：Overpass API（overpass-api.de）。', 'Data extract: Overpass API (overpass-api.de).'),
    'images': ('壁や天井に貼った絵画・モザイク・ドームの写真は、Wikimedia Commons の画像です。切り抜き・縮小・圧縮して使っています。ライセンスは各画像のとおりで、'
               + NW % 'CC BY' + '・' + NW % 'CC BY-SA' + ' の画像から作った質感も、その条件に従います。',
               'The paintings, mosaics and dome photographs on the walls and ceilings are Wikimedia Commons images, cropped, downsized and compressed. Each keeps its own licence; textures made from '
               + NW % 'CC BY' + ' and ' + NW % 'CC BY-SA' + ' images remain under those terms.'),
    'refs': ('形や色づかいを確かめるために見ただけの画像です。作品の中には使っていません。',
             'Images looked at to check shapes and colours while modelling. None of them appear in the work.'),
    'textures': ('壁・屋根・石・木・金属の質感には、CC0 のテクスチャセットを使っています。ヴェネツィア特有の石畳（マゼーニ）だけは、この作品のために手続き的に生成しました。',
                 'Walls, roofs, stone, wood and metal take their surface detail from CC0 texture sets. Only the masegni, Venice’s trachyte paving, is generated procedurally for this work.'),
    'sky': ('空と環境光は Poly Haven の HDRI をもとにしています。太陽の円盤は取り除き（太陽は別の光として描きます）、向きをそろえ、解像度を下げて使っています。',
            'The sky and ambient light are based on Poly Haven HDRI skies. The sun disc is removed (the sun is drawn as a separate, live light), the sky is rotated to match, and the resolution is reduced.'),
    'software': ('ブラウザの中で動くものと、データをつくるために使った道具（作品には含まれません）に分けて記します。',
                 'Split into what runs in the page and the tools used offline to build the data, which are not part of the work.'),
    'sound': ('ピアノ独奏、水の音、鐘、鳩の声は、すべてブラウザの中で合成しています。録音した音は使っていません。',
              'The solo piano, the water, the bells and the pigeons are all synthesised in the browser. No recordings are used.'),
    'note': ('この再構成は近似です。建物の大半は、地図上の形から手続き的に生成したものです。手作りのランドマーク（サン・マルコ広場とその周辺、サン・マルコ寺院、鐘楼、ドゥカーレ宮殿、'
             '嘆きの橋、リアルト橋、カフェ・フローリアン、フェニーチェ劇場など）も、写真と資料から細部・色・寸法を推定したもので、測量にもとづく公式のモデルではありません。',
             'This reconstruction is approximate. Most buildings are generated procedurally from their footprints on the map. The hand-modelled landmarks (the piazza and its surroundings, '
             'St Mark’s Basilica, the Campanile, the Doge’s Palace, the Bridge of Sighs, the Rialto Bridge, Caffè Florian, La Fenice and others) rest on photographs and references, '
             'with details, colours and proportions inferred. It is not an official survey model.'),
    'tagline': ('ヴェネツィア本島を、歩いて、ゴンドラで。', 'Walk the island. Ride a gondola.'),
    'col_image': ('画像', 'Image'), 'col_set': ('テクスチャ', 'Texture set'), 'col_soft': ('ソフトウェア', 'Software'), 'col_author': ('作者', 'Author'),
    'col_licence': ('ライセンス', 'Licence'), 'col_use': ('用途', 'Used for'),
    'in_page': ('ページの中で', 'In the page'), 'offline': ('制作時に', 'Offline, to build'), 'procedural': ('手続き生成', 'Procedural'),
    'day_sky': ('昼の空', 'day sky'), 'night_sky': ('夜の空', 'night sky'),
}
SECTION_LABEL = {   # id -> (JA, EN) for the label column and the contents row
    'map': ('地図データ', 'Map data'), 'images': ('画像', 'Images'), 'refs': ('参照のみ', 'References'), 'textures': ('テクスチャ', 'Textures'),
    'sky': ('空', 'Sky'), 'software': ('ソフトウェア', 'Software'), 'sound': ('音', 'Sound'), 'note': ('注記', 'Note'),
}

# ------------------------------------------------------------------------------------------ cleaning
_ZW = re.compile('[' + ''.join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF)) + ']')   # zero-width characters


def ws(s):
    """collapse every kind of whitespace (NBSP, thin spaces, newlines) to single spaces"""
    return re.sub(r'\s+', ' ', _ZW.sub('', s or '')).strip()


def clean_artist(a):
    a = ws(a)
    if not a:
        return ''
    m = re.match(r'(?i)^this\s+photo(?:graph)?\s+was\s+taken\s+by\s+(.+?)(?:\s*[.(\[]|$)', a)     # "This photo was taken by X. Feel free to ..."
    if m:
        a = m.group(1)
    a = re.sub(r'(?i)^(?:users?|photo|photographer|creator|author|autore)\s*:\s*', '', a)         # "user:Testus", "Photo: X", "Creator:X"
    a = re.sub(r'(?i)\s+-\s+incisore\s*:\s*', ', engraved by ', a)                                # "Autore: A - Incisore: B"
    a = ws(a)
    if len(a) > 120:
        a = a[:117].rsplit(' ', 1)[0] + '…'
    return a


def title_from_file(m):
    t = ws(m.get('title', ''))
    t = t.split(':', 1)[1] if t.lower().startswith('file:') else t
    t = re.sub(r'\.(?:jpe?g|png|tiff?|webp|gif|svg)$', '', t, flags=re.I)
    return ws(t.replace('_', ' '))


def clean_title(m, artist):
    raw = m.get('object', '') or ''
    o = ws(raw)
    if not o or 'QS:' in o:                                      # leftover Wikidata structured-data text
        en = re.search(r'label QS:Len,"([^"]+)"', raw)           # its English label, if it carries one
        o = ws(en.group(1)) if en else ''
    if not o:
        o = title_from_file(m)
    o = re.sub(r'^\((?:Venice|Venezia)\)\s*', '', o)             # "(Venice) St. Mark's Basilica, ..."
    by = ' by ' + artist
    if artist and by in o and o.split(by)[0].strip():
        o = o.split(by)[0].strip()                               # "Spring by Rosalba Carriera Rijksdienst ..." -> "Spring"
    o = re.sub(r'(?<=[A-Za-z0-9])\(', ' (', o)                   # "Pozzo(1728)"
    o = re.sub(r'(?<=[a-z]{6})(\d{1,2})$', r' \1', o)            # "Illustri1" -> "Illustri 1"
    return o


def https(u):
    return re.sub(r'^http://(creativecommons\.org)', r'https://\1', u or '')


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


# ------------------------------------------------------------------------------------------ data
def commons_entry(folder, f, m, keys=()):
    artist = clean_artist(m.get('artist', ''))
    if not artist:
        warn('%s/%s: no author in the manifest' % (folder, f))
    page = m.get('page') or 'https://commons.wikimedia.org/wiki/' + quote(m.get('title', f).replace(' ', '_'), safe=':/(),')
    return {'folder': folder, 'file': f, 'keys': list(keys), 'title': clean_title(m, artist), 'artist': artist,
            'lic': ws(m.get('license', '')), 'lic_url': https(m.get('license_url', '')), 'page': page}


def collect_images():
    """(used, references): used = list in art.json layer order, references = {folder: [entries]}"""
    manifests = {}
    for p in sorted(COMMONS.glob('*/manifest.json')):
        folder = p.parent.name
        manifests[folder] = {}
        for title, m in load_json(p).items():
            f = m.get('file') or re.sub(r'[^\w.\-]+', '_', title.split(':', 1)[-1], flags=re.UNICODE).strip('_')[:150]
            manifests[folder][f] = m
            if not (p.parent / f).exists():
                warn('%s/%s: listed in the manifest but not on disk' % (folder, f))
    art = load_json(PUBLIC / 'tex' / 'art.json')['items']
    used, order = {}, []
    for key, it in sorted(art.items(), key=lambda kv: kv[1].get('layer', 0)):
        folder, _, f = it['src'].partition('/')
        m = manifests.get(folder, {}).get(f)
        if m is None:
            warn('art.json item "%s" (%s) has no manifest entry: credited by file name only' % (key, it['src']))
            m = {'title': 'File:' + f, 'object': f, 'artist': '', 'license': '', 'license_url': ''}
        if (folder, f) in used:                                  # one file mapped twice (two crops): one credit
            used[(folder, f)]['keys'].append(key)
            continue
        used[(folder, f)] = commons_entry(folder, f, m, [key])
        order.append((folder, f))
    refs = {}
    for folder, files in manifests.items():
        for f, m in files.items():
            if (folder, f) not in used:
                refs.setdefault(folder, []).append(commons_entry(folder, f, m))
    for folder in refs:
        refs[folder].sort(key=lambda e: natural_key(e['title']))
    return [used[k] for k in order], refs


def collect_textures():
    """the texture sets of gen/materials.py LAYERS: ([(set name, manifest record)], [procedural set names])"""
    src = (HERE / 'gen' / 'materials.py').read_text(encoding='utf-8')
    layers = None
    for node in ast.parse(src).body:                             # LAYERS = [(name, source set, size, flags), ...]
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LAYERS' for t in node.targets):
            layers = ast.literal_eval(node.value)
    if not layers:
        raise SystemExit('credits: LAYERS not found in gen/materials.py')
    man = load_json(TEXTURES / 'manifest.json')
    sets, procedural = [], []
    for layer in layers:
        name, set_name = layer[0], layer[1]
        if set_name in PROCEDURAL:
            if set_name not in procedural:
                procedural.append(set_name)
        elif set_name in man:
            if set_name not in [s[0] for s in sets]:
                sets.append((set_name, man[set_name]))
        else:
            warn('texture set "%s" (layer %s) is not in textures/manifest.json' % (set_name, name))
    return sets, procedural


def collect_sky():
    """[(hdri key, manifest record, 'day'|'night'|...)] for the HDRIs the viewer ships and the bake used"""
    hdri = load_json(HDRI / 'manifest.json', required=False) or {}
    found = {}
    for d in (PUBLIC / 'tex', ASSETS / 'sky'):                   # what the viewer ships first, then what the bake used
        for p in (sorted(d.glob('*.json')) if d.exists() else []):
            j = load_json(p, required=False)
            if isinstance(j, dict) and str(j.get('src', '')).lower().endswith('.hdr'):
                found.setdefault(re.sub(r'^sky_', '', p.stem), j)
    out = []
    for stem, j in sorted(found.items()):
        base = re.sub(r'(_\d+k)?\.hdr$', '', os.path.basename(j['src']), flags=re.I)
        key = base if base in hdri else next((k for k in hdri if base.startswith(k)), None)
        if key is None:
            warn('sky "%s" is not in hdri/manifest.json' % base)
        elif key not in [o[0] for o in out]:
            out.append((key, hdri[key], stem))
    return out


def hdri_name(key):
    n = re.sub(r'_puresky$', '', key)
    return ' '.join(w.capitalize() for w in n.split('_')) + (' (Pure Sky)' if key.endswith('_puresky') else '')


# ------------------------------------------------------------------------------------------ html helpers
def esc(s):
    return html.escape(str(s), quote=True)


def L(ja, en):
    """a bilingual text: both spans are in the page, CSS shows the one that matches <html lang>"""
    return '<span lang="ja">' + ja + '</span><span lang="en">' + en + '</span>'


def T(key):
    return L(*TEXT[key])


def A(href, text, cls=''):
    c = ' class="' + cls + '"' if cls else ''
    return '<a' + c + ' href="' + esc(href) + '" target="_blank" rel="noopener">' + text + '</a>'


def lic_html(name, url=''):
    """licence short name, linked to its text where we know where that is (nowrap: 'CC BY-SA 4.0' never breaks)"""
    if not name:
        return '<span class="none">—</span>'
    url = url or LICENSE_URLS.get(name, '')
    return A(url, esc(name), 'lic') if url else '<span class="lic">' + esc(name) + '</span>'


def row(left, mid, right, note=''):
    return '<li class="it"><span class="t">%s%s</span><span class="a">%s</span><span class="l">%s</span></li>' % (left, note, mid, right)


def head_row(a, b, c):
    return '<div class="th" aria-hidden="true"><span>%s</span><span>%s</span><span>%s</span></div>' % (a, b, c)


def image_row(e):
    note = ''
    for k in e['keys']:
        if k in KEY_NOTE:
            note = '<span class="note blk">' + L(*KEY_NOTE[k]) + '</span>'
    return row(A(e['page'], esc(e['title'])), esc(e['artist']) or '<span class="none">—</span>', lic_html(e['lic'], e['lic_url']), note)


def group(folder, count, inner):
    ja, en = PLACES.get(folder) or (folder.title(), folder.title())
    return '<div class="group"><h3>' + L(esc(ja), esc(en)) + '<small>' + str(count) + '</small></h3>' + inner + '</div>'


def florian_rooms(entries):
    """the florian entries split by room (art.json key), in the order of the enfilade; whatever matches no room last"""
    out, left = [], list(entries)
    for pat, ja, it in FLORIAN_ROOMS:
        mine = [e for e in left if any(re.fullmatch(pat, k) for k in e['keys'])]
        left = [e for e in left if e not in mine]
        if mine:
            out.append(('<h4 class="room">' + L(esc(ja) + ' <i>' + esc(it) + '</i>', esc(it)) + '</h4>', mine))
    if left:
        out.append(('', left))
    return out


def section(sid, sub, count, body):
    label = L(*SECTION_LABEL[sid])
    n = '<span class="n">%s</span>' % count if count != '' else ''
    s = '<span class="s">%s</span>' % sub if sub else ''
    return ('<section class="sec" id="%s"><div class="hd"><h2 class="lab">%s</h2>%s%s</div><div class="body">%s</div></section>' % (sid, label, s, n, body))


def lead(key):
    return '<p class="lead">' + T(key) + '</p>'


# ------------------------------------------------------------------------------------------ the page
CSS = r'''
:root{--bg:#0d0f12;--ink:#f6f1e7;--dim:rgba(246,241,231,.62);--faint:rgba(246,241,231,.42);--line:rgba(246,241,231,.28);--hair:rgba(246,241,231,.12);
  --sans:"Helvetica Neue","Helvetica","Arial","Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;--gut:clamp(16px,4vw,56px);color-scheme:dark}
*{box-sizing:border-box}
html{background:var(--bg);-webkit-text-size-adjust:100%;text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.8 var(--sans);-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;overflow-wrap:break-word}
html[lang=ja] body{letter-spacing:.03em;line-height:1.9}
html[lang=ja] .lede,html[lang=ja] .body p{word-break:auto-phrase;line-break:strict;text-wrap:pretty}
html[lang=en] .lede,html[lang=en] .body p{text-wrap:pretty}
.nw,.lic{white-space:nowrap}
html[lang=en] [lang=ja],html:not([lang=en]) [lang=en]{display:none!important}
a{color:inherit;text-decoration:underline;text-decoration-color:rgba(246,241,231,.22);text-decoration-thickness:1px;text-underline-offset:.24em;transition:color .2s,text-decoration-color .2s}
a:hover{text-decoration-color:var(--ink)}
a:focus-visible,button:focus-visible{outline:1px solid var(--ink);outline-offset:3px}
::selection{background:var(--ink);color:var(--bg)}
i{font-style:normal;color:var(--faint)}
.wrap{max-width:1400px;margin:0 auto;padding:0 var(--gut)}

/* top strip: back to the work, language */
.top{display:flex;align-items:center;justify-content:space-between;padding-top:20px}
.back{font-size:12px;letter-spacing:.14em;color:var(--dim);text-decoration:none;padding:6px 0}
.back:hover{color:var(--ink)}
.lang{display:flex;gap:2px;margin-right:-10px}
.lang button{background:none;border:0;padding:6px 10px;font:inherit;font-size:12px;letter-spacing:.1em;color:var(--dim);cursor:pointer}
.lang button.on,.lang button:hover{color:var(--ink)}

/* title: one huge cropped word, small restrained text */
.hero{padding-top:clamp(48px,11vh,132px)}
.word{margin:0 0 0 -.055em;font-weight:700;font-size:clamp(56px,19.5vw,300px);line-height:.8;letter-spacing:-.055em;color:var(--ink);user-select:none}
@supports ((-webkit-background-clip:text) or (background-clip:text)){
  .word{background:linear-gradient(180deg,#f6f1e7 18%,rgba(246,241,231,.2) 112%);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent}}
.sub{margin:clamp(20px,3.6vh,36px) 0 0 .25vw;font-size:15px;letter-spacing:.08em;color:var(--dim)}
.lede{max-width:38em;margin:clamp(28px,5vh,52px) 0 0;font-size:16px;color:var(--ink)}
.toc{display:flex;flex-wrap:wrap;gap:6px 26px;list-style:none;margin:clamp(36px,7vh,72px) 0 0;padding:0}
.toc a{display:block;padding:4px 0;font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);text-decoration:none}
.toc a:hover{color:var(--ink)}

/* sections: label column + content column, hairline rules, one strong rule on top */
main{margin-top:clamp(56px,10vh,112px)}
.sec{display:grid;grid-template-columns:minmax(150px,21%) minmax(0,1fr);column-gap:clamp(20px,4vw,72px);padding:34px 0 60px;border-top:1px solid var(--hair)}
.sec:first-child{border-top-color:var(--line)}
.hd{align-self:start;position:sticky;top:26px;padding-right:8px}
.lab{margin:0;font-size:11px;font-weight:400;letter-spacing:.18em;line-height:1.7;text-transform:uppercase;color:var(--ink)}
html[lang=ja] .lab,html[lang=ja] .toc a,html[lang=ja] .th{font-size:12px}
.hd .s{display:block;margin-top:2px;font-size:11px;letter-spacing:.1em;color:var(--faint)}
.hd .n{display:block;margin-top:14px;font-size:11px;letter-spacing:.14em;color:var(--faint);font-variant-numeric:tabular-nums}
.body{min-width:0}
.body p{margin:0 0 1em;max-width:42em}
.lead{color:var(--dim)}
.credit{font-size:16px;margin-top:1.1em!important}
.small{font-size:12px;color:var(--faint)}
.group{margin-top:46px}
.th+.group{margin-top:18px}
.lead+.group{margin-top:30px}
.lead+.th{margin-top:30px}
.group>h3{display:flex;align-items:baseline;gap:14px;margin:0 0 10px;font-size:15px;font-weight:600;letter-spacing:.02em;line-height:1.5}
.group>h3 small{font-size:11px;font-weight:400;letter-spacing:.14em;color:var(--faint);font-variant-numeric:tabular-nums}
.room{margin:26px 0 4px;font-size:11px;font-weight:400;letter-spacing:.16em;line-height:1.6;text-transform:uppercase;color:var(--dim)}
.room i{margin-left:.6em;letter-spacing:.06em;text-transform:none}

/* entries: image | author | licence */
.list{list-style:none;margin:0;padding:0}
.it,.th{display:grid;grid-template-columns:minmax(0,1.9fr) minmax(0,1.1fr) minmax(8.5em,.6fr);column-gap:clamp(14px,2.2vw,32px);align-items:baseline}
.it{padding:9px 0;border-top:1px solid var(--hair);font-size:14px;line-height:1.55}
.it .t{min-width:0;overflow-wrap:anywhere}
.it .a{min-width:0;color:var(--dim);font-size:13px}
.it .l{min-width:0;color:var(--dim);font-size:12px;letter-spacing:.04em}
.it .l a{text-decoration:none}
.it .l a:hover{color:var(--ink);text-decoration:underline;text-underline-offset:.24em}
.it .note{margin-left:.7em;font-size:12px;color:var(--faint)}
.it .note.blk{display:block;margin:1px 0 0}
.none{color:var(--faint)}
.th{padding:0 0 8px;font-size:10.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--faint)}

/* references: quieter, set small in columns */
.refs .group>h3{font-size:13px;font-weight:500;color:var(--dim)}
.refs .group ul{list-style:none;margin:0;padding:0;columns:2 340px;column-gap:56px}
.refs li{break-inside:avoid;padding:3px 0;font-size:12px;line-height:1.55;color:var(--faint);overflow-wrap:anywhere}
.refs li a{color:var(--dim)}
.refs li a.lic{text-decoration:none}
.refs li a.lic:hover{color:var(--ink);text-decoration:underline}
.refs li .sep{margin:0 .35em;color:var(--line)}

.foot{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px 32px;padding:30px 0 64px;border-top:1px solid var(--hair);font-size:12px;letter-spacing:.08em;color:var(--faint)}
.foot a{color:var(--dim);text-decoration:none;letter-spacing:.14em}
.foot a:hover{color:var(--ink)}

@media (max-width:860px){
  .sec{grid-template-columns:minmax(0,1fr);padding:28px 0 48px}
  .hd{position:static;display:flex;flex-wrap:wrap;align-items:baseline;gap:0 14px;margin-bottom:20px}
  .hd .s,.hd .n{margin-top:0}
  .it{grid-template-columns:minmax(0,1fr) auto;row-gap:1px}
  .it .t{grid-column:1/-1}
  .th{display:none}
  .group{margin-top:38px}
  .refs .group ul{columns:1}
}
@media (max-width:420px){.lede{font-size:15px}.it .a{font-size:12.5px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
'''

HEAD_SCRIPT = "(function(){var h=(location.hash||'').toLowerCase();document.documentElement.lang=h==='#en'?'en':'ja';})();"

BODY_SCRIPT = r'''
(function () {
  var root = document.documentElement, T = { ja: 'クレジット — VENEZIA', en: 'Credits — VENEZIA' };
  function set(l, write) {
    root.lang = l; document.title = T[l];
    [].forEach.call(document.querySelectorAll('.back-link'), function (a) { a.href = 'index.html#' + l; });
    [].forEach.call(document.querySelectorAll('.lang button'), function (b) { var on = b.getAttribute('data-l') === l; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
    if (write) { try { history.replaceState(null, '', '#' + l); } catch (e) {} }
  }
  [].forEach.call(document.querySelectorAll('.lang button'), function (b) { b.addEventListener('click', function () { set(b.getAttribute('data-l'), true); }); });
  window.addEventListener('hashchange', function () { var h = location.hash.toLowerCase(); if (h === '#en' || h === '#ja') set(h.slice(1), false); });
  // the hash carries the language, so in-page links scroll without touching it
  [].forEach.call(document.querySelectorAll('a[data-go]'), function (a) {
    a.addEventListener('click', function (e) {
      var t = document.getElementById(a.getAttribute('data-go')); if (!t) return;
      e.preventDefault(); var calm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
      t.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
    });
  });
  set(root.lang === 'en' ? 'en' : 'ja', false);
})();
'''

PAGE = '''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0d0f12">
<meta name="description" content="VENEZIA — 出典とライセンス / Sources and licences">
<title>クレジット — VENEZIA</title>
<link rel="icon" href="data:,">
<!-- generated by tools/credits.py from the asset manifests; do not edit by hand -->
<script>%(head_script)s</script>
<style>%(css)s</style>
</head>
<body>
<div class="wrap">
<header class="top">
<a class="back back-link" href="index.html#ja">← VENEZIA</a>
<div class="lang" role="group" aria-label="Language"><button type="button" data-l="ja">JA</button><button type="button" data-l="en">EN</button></div>
</header>
<div class="hero">
<h1 class="word">CREDITS</h1>
<p class="sub">%(sub)s</p>
<p class="lede">%(lede)s</p>
<ul class="toc">%(toc)s</ul>
</div>
<main>
%(sections)s
</main>
<footer class="foot"><a class="back-link" href="index.html#ja">← VENEZIA</a><span>%(tagline)s</span></footer>
</div>
<script>%(body_script)s</script>
</body>
</html>
'''


def images_section(images):
    by_folder = {}
    for e in images:
        by_folder.setdefault(e['folder'], []).append(e)
    body = [lead('images'), head_row(T('col_image'), T('col_author'), T('col_licence'))]
    for folder in [f for f in PLACES if f in by_folder] + sorted(f for f in by_folder if f not in PLACES):
        es = by_folder[folder]
        if folder == 'florian':
            inner = ''.join(h + '<ul class="list">' + ''.join(image_row(e) for e in mine) + '</ul>' for h, mine in florian_rooms(es))
        else:
            inner = '<ul class="list">' + ''.join(image_row(e) for e in es) + '</ul>'
        body.append(group(folder, len(es), inner))
    return section('images', L('Wikimedia Commons', 'Wikimedia Commons'), len(images), ''.join(body))


def refs_section(refs):
    body = [lead('refs')]
    n = 0
    for folder in [f for f in PLACES if f in refs] + sorted(f for f in refs if f not in PLACES):
        es = refs[folder]
        n += len(es)
        sep = '<span class="sep">/</span>'
        lis = ''.join('<li>' + A(e['page'], esc(e['title'])) + sep + (esc(e['artist']) or '—') + sep + lic_html(e['lic'], e['lic_url']) + '</li>' for e in es)
        body.append(group(folder, len(es), '<ul>' + lis + '</ul>'))
    return section('refs', L('作品には表示しません', '(not shown)'), n, '<div class="refs">' + ''.join(body) + '</div>'), n


def textures_section(tex_sets, tex_proc):
    body = [lead('textures'), head_row(T('col_set'), T('col_author'), T('col_licence'))]
    by_src = {}
    for name, m in tex_sets:
        by_src.setdefault(m.get('source', ''), []).append((name, m))
    for src in sorted(by_src, key=lambda s: -len(by_src[s])):
        lis = ''
        for name, m in sorted(by_src[src], key=lambda x: natural_key(x[1].get('name', x[0]))):
            authors = ', '.join(re.sub(r'\s*\((?:ambientCG|Poly Haven)\)\s*$', '', a) for a in m.get('authors', []))
            lis += row(A(m['url'], esc(m.get('name', name))), esc(authors), lic_html(ws(m.get('license', ''))))
        h = A(SOURCE_URLS[src], esc(src)) if src in SOURCE_URLS else esc(src)
        body.append('<div class="group"><h3>%s<small>%d</small></h3><ul class="list">%s</ul></div>' % (h, len(by_src[src]), lis))
    if tex_proc:
        lis = ''.join(row(L(esc(PROCEDURAL[p][0]), esc(PROCEDURAL[p][1])), L(esc(PROCEDURAL[p][2]), esc(PROCEDURAL[p][3])), '<span class="none">—</span>') for p in tex_proc)
        body.append('<div class="group"><h3>%s<small>%d</small></h3><ul class="list">%s</ul></div>' % (T('procedural'), len(tex_proc), lis))
    return section('textures', '', len(tex_sets) + len(tex_proc), ''.join(body))


def sky_section(skies):
    body = [lead('sky'), head_row('HDRI', T('col_author'), T('col_licence'))]
    lis = ''
    for key, m, stem in skies:
        which = 'day_sky' if stem == 'day' else 'night_sky' if stem == 'night' else None
        note = ' <span class="note">' + (T(which) if which else esc(stem)) + '</span>'
        lis += row(A(m['url'], esc(hdri_name(key))), esc(', '.join(m.get('authors', []))), lic_html(ws(m.get('license', ''))), note)
    body.append('<div class="group"><ul class="list">' + lis + '</ul></div>')
    return section('sky', '', len(skies), ''.join(body))


def software_section():
    def rows(items):
        out = ''
        for names, ja, en, lics in items:
            out += row(' · '.join(A(u, esc(n)) for n, u in names), L(esc(ja), esc(en)), ' · '.join(lic_html(x) for x in lics))
        return out
    body = [lead('software'), head_row(T('col_soft'), T('col_use'), T('col_licence')),
            '<div class="group"><h3>%s</h3><ul class="list">%s</ul></div>' % (T('in_page'), rows(SOFTWARE_PAGE)),
            '<div class="group"><h3>%s</h3><ul class="list">%s</ul></div>' % (T('offline'), rows(SOFTWARE_BUILD))]
    return section('software', '', '', ''.join(body))


def build(images, refs, tex_sets, tex_proc, skies):
    credit = '© ' + A('https://www.openstreetmap.org/copyright', 'OpenStreetMap contributors') + ' · Open Database License (' + A(LICENSE_URLS['ODbL'], 'ODbL') + ') 1.0'
    refs_html, n_refs = refs_section(refs)
    sections = [
        section('map', '', '', '<p>' + T('map') + '</p><p class="credit">' + credit + '</p><p class="small">' + T('map_extract') + '</p>'),
        images_section(images),
        refs_html,
        textures_section(tex_sets, tex_proc),
        sky_section(skies),
        software_section(),
        section('sound', '', '', '<p>' + T('sound') + '</p>'),
        section('note', '', '', '<p class="lead">' + T('note') + '</p>'),
    ]
    toc = ''.join('<li><a href="#%s" data-go="%s">%s</a></li>' % (sid, sid, L(*SECTION_LABEL[sid])) for sid in SECTION_LABEL)
    page = PAGE % {'head_script': HEAD_SCRIPT, 'css': CSS, 'sub': T('sub'), 'lede': T('lede'), 'toc': toc, 'sections': '\n'.join(sections),
                   'tagline': T('tagline'), 'body_script': BODY_SCRIPT}
    return page, n_refs


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else PUBLIC / 'credits.html'
    images, refs = collect_images()
    tex_sets, tex_proc = collect_textures()
    skies = collect_sky()
    page, n_refs = build(images, refs, tex_sets, tex_proc, skies)
    out.write_text(page, encoding='utf-8')
    per = {}
    for e in images:
        per[e['folder']] = per.get(e['folder'], 0) + 1
    print('credits: wrote %s (%d KB)' % (out, len(page.encode('utf-8')) // 1024))
    print('  images          %d   %s' % (len(images), ', '.join('%s %d' % kv for kv in per.items())))
    print('  references      %d   %s' % (n_refs, ', '.join('%s %d' % (k, len(v)) for k, v in sorted(refs.items()))))
    print('  texture sets    %d downloaded + %d procedural' % (len(tex_sets), len(tex_proc)))
    print('  sky             %d   %s' % (len(skies), ', '.join(k for k, _, _ in skies)))
    print('  warnings        %d' % len(WARN))


if __name__ == '__main__':
    main()
