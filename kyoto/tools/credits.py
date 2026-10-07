#!/usr/bin/env python3
"""Generate public/credits.html (standalone, Japanese by default, English via #en) from the data the build uses.

    python3 credits.py [OUT.html]          # python 3 standard library only; default OUT = ../public/credits.html

Same page, same CSS and markup as venice/tools/credits.py.  What is read at run time, not listed by hand:
  * gen/materials.py  LAYERS                  the texture sets the build uses (second element of each tuple)
  * <assets>/textures/manifest.json           Poly Haven / ambientCG records (source, page, licence, authors)
  * public/tex/sky_*.json (+ <assets>/sky)    which HDRI each evening sky was made from;  <assets>/hdri/manifest.json for its record
  * <assets>/score/CREDITS.txt                music and sound: the short lines and the full notes (CC BY-SA 4.0 attribution and changes)
Everything else (city data, software, the hand-modelled sites) is the data below.
Warnings (a texture set missing from the manifest, ...) go to stderr; the exit status stays 0.
"""
import ast
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                                                # kyoto/
PUBLIC = ROOT / 'public'
ASSETS = Path(os.environ.get('KYOTO_ASSETS', '/home/kazu/work/kyoto-assets'))     # raw assets, not in git
TEXTURES, HDRI, SCORE = ASSETS / 'textures', ASSETS / 'hdri', ASSETS / 'score'
BUILT = '2026-10-06'                                                              # shown in the footer
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
CC_BY = 'https://creativecommons.org/licenses/by/4.0/'
CC_BY_SA = 'https://creativecommons.org/licenses/by-sa/4.0/'
LICENSE_URLS = {
    'CC0': 'https://creativecommons.org/publicdomain/zero/1.0/',
    'MIT': 'https://opensource.org/license/mit',
    'Apache-2.0': 'https://www.apache.org/licenses/LICENSE-2.0',
    'BSD-3-Clause': 'https://opensource.org/license/bsd-3-clause',
    'ISC': 'https://opensource.org/license/isc-license-txt',
    'GPL': 'https://www.gnu.org/licenses/gpl-3.0.html',
    'LGPL-3.0': 'https://www.gnu.org/licenses/lgpl-3.0.html',
    'MIT-CMU': 'https://github.com/python-pillow/Pillow/blob/main/LICENSE',
    'ODbL': 'https://opendatacommons.org/licenses/odbl/',
    'CC BY-SA 3.0': 'https://creativecommons.org/licenses/by-sa/3.0/',
    'CC BY-SA 4.0': 'https://creativecommons.org/licenses/by-sa/4.0/',
}
SOURCE_URLS = {'Poly Haven': 'https://polyhaven.com', 'ambientCG': 'https://ambientcg.com'}
# what the build generates itself instead of downloading:  (JA name, EN name, JA note, EN note)
PROCEDURAL = [
    ('葉のテクスチャ', 'Leaf textures', 'この作品のために生成（樹木の葉）', 'Generated for this work (tree foliage)'),
    ('樹木のモデル', 'Tree models', 'この作品のために生成（樹種ごと）', 'Generated for this work (per species)'),
]
# the hand-modelled sites, in the order of the walk:  (JA name, EN name, JA what, EN what)
SITES = [
    ('京都駅・京都タワー', 'Kyoto Station and Kyoto Tower', '', ''),
    ('三十三間堂', 'Sanjūsangen-dō', '堂内の仏像も', 'with its statues'),
    ('伏見稲荷大社', 'Fushimi Inari Taisha', '千本鳥居', 'the Senbon Torii'),
    ('清水寺', 'Kiyomizu-dera', '', ''),
    ('東山の町並み', 'Higashiyama streets', '八坂の塔・二年坂・産寧坂', 'Yasaka Pagoda, Ninen-zaka, Sannen-zaka'),
    ('祇園', 'Gion', '花見小路・白川・八坂神社・南座', 'Hanamikōji, the Shirakawa, Yasaka Shrine, the Minamiza'),
    ('永観堂', 'Eikan-dō', '', ''),
    ('銀閣寺', 'Ginkaku-ji', '', ''),
]
# software:  ([(name, url), ...], JA use, EN use, [licences])   (versions: tools/package.json and the venv)
SOFTWARE_PAGE = [
    ([('three.js', 'https://threejs.org')], '3Dエンジン（WebGPU による描画とシェーダー）', '3D engine: WebGPU rendering and shaders', ['MIT']),
    ([('meshoptimizer', 'https://github.com/zeux/meshoptimizer')], 'メッシュの圧縮と展開', 'Mesh compression and decoding', ['MIT']),
    ([('Basis Universal', 'https://github.com/BinomialLLC/basis_universal')], 'テクスチャ（KTX2）のトランスコーダー', 'Texture (KTX2) transcoder', ['Apache-2.0']),
]
SOFTWARE_BUILD = [
    ([('Blender', 'https://www.blender.org')], 'ランドマークのモデリングと、光の焼き込み（Cycles。頂点ごとの間接光）。道具として使っただけで、モデルはこの作品のために作ったものです',
      'Modelling the landmarks, and light baking (Cycles, per-vertex indirect light). Used as a tool only; the models are made for this work', ['GPL']),
    ([('KTX-Software', 'https://github.com/KhronosGroup/KTX-Software')], 'KTX2 テクスチャの書き出し', 'KTX2 texture packing', ['Apache-2.0']),
    ([('esbuild', 'https://esbuild.github.io')], 'スクリプトのバンドル', 'Script bundling', ['MIT']),
    ([('shapely', 'https://shapely.readthedocs.io'), ('NumPy', 'https://numpy.org'), ('SciPy', 'https://scipy.org')], '形状と数値の処理', 'Geometry and numerics', ['BSD-3-Clause']),
    ([('pyproj', 'https://pyproj4.github.io/pyproj/')], '座標の変換', 'Coordinate transforms', ['MIT']),
    ([('lxml', 'https://lxml.de')], 'PLATEAU（CityGML）の読み込み', 'Reading PLATEAU (CityGML)', ['BSD-3-Clause']),
    ([('triangle', 'https://rufat.be/triangle')], '三角形分割（Shewchuk の Triangle の Python バインディング）', 'Triangulation (Python bindings to Shewchuk’s Triangle)', ['LGPL-3.0']),
    ([('mapbox_earcut', 'https://github.com/skogler/mapbox_earcut_python')], 'ポリゴンの三角形分割', 'Polygon triangulation', ['ISC']),
    ([('Pillow', 'https://python-pillow.github.io'), ('OpenCV', 'https://opencv.org')], '画像処理（質感、葉、空の加工）', 'Image processing (textures, foliage, sky)', ['MIT-CMU', 'Apache-2.0']),
]

# the page copy, (JA, EN).  <span class="nw"> keeps a licence name on one line.  (No & < > in here: it is inserted as is.)
NW = '<span class="nw">%s</span>'
TEXT = {
    'sub': ('出典とライセンス', 'Sources and licences'),
    'lede': ('京都駅から伏見稲荷、東福寺、東寺、三十三間堂、清水寺、東山、祇園、永観堂、銀閣寺まで、そして金閣寺と嵐山・嵯峨野。秋の夕暮れと雪の夕暮れの京都を、歩いて、空から巡る3D再構成です。'
             '主な名所は公開されている情報と写真をもとに Blender で手づくりし、街はオープンデータから生成しています。この作品が使っている出典とライセンスを、以下にまとめます。',
             'A 3D reconstruction of Kyoto that you can walk and fly through, from Kyoto Station to Fushimi Inari, Tōfuku-ji, Tō-ji, Sanjūsangen-dō, Kiyomizu-dera, Higashiyama, Gion, Eikan-dō and Ginkaku-ji, with Kinkaku-ji and Arashiyama–Sagano, '
             'on an autumn evening and a snowy one. The main sights are modelled by hand in Blender from public information and photographs; the city is generated from open data. '
             'The sources and licences of everything it uses are listed below.'),
    'lede2': ('非公式の、独立した再構成です。ここに登場する寺院・神社・企業・団体などとは関係がなく、公式なものでも、承認を受けたものでもありません。',
              'This is an unofficial, independent reconstruction. It is not affiliated with, approved by or endorsed by the temples, shrines, companies or other organisations it shows.'),
    'city': ('街の形と高さ、道、水、地形は、次の三つのオープンデータから生成しています。', 'The shape and height of the city, its streets, water and terrain are generated from three open datasets.'),
    'plateau_note': ('建物の形、高さ、屋根の形を取り出し、この作品用のメッシュに加工して使っています。加工はこの作品によるもので、国土交通省が作成したものではありません。',
                     'Building footprints, heights and roof shapes were extracted and rebuilt as our own meshes. The processing is ours; it was not made by MLIT.'),
    'plateau_dataset': ('G空間情報センターのデータセット', 'Dataset page at G-空間情報センター (G-spatial Information Center)'),
    'plateau_credit': ('出典：国土交通省 Project PLATEAU 京都市 3D都市モデル（2025年度）', 'Source: MLIT Project PLATEAU, Kyoto City 3D city model (FY2025)'),
    'osm_note': ('道、水面、土地利用、樹木、街路設備。Geofabrik で配布されている抽出データを使っています。', 'Roads, water, land use, trees and street furniture. From the extract distributed by Geofabrik.'),
    'gsi_name': ('標高タイル（DEM5A・DEM5B・DEM10B）', 'Elevation tiles (DEM5A, DEM5B, DEM10B)'),
    'gsi_note': ('街の地形と、遠くの山並みに使っています。', 'Used for the terrain of the city and for the far hills.'),
    'gsi_credit': ('出典：国土地理院 標高タイル', 'Source: Geospatial Information Authority of Japan (GSI), elevation tiles'),
    'textures': ('壁・屋根・舗装・地面・樹皮などの質感には、CC0 のテクスチャセットを使っています（下の二つのグループは、どちらもすべて CC0 です）。'
                 '葉のテクスチャと樹木のモデルは、ダウンロードしたものではなく、この作品のために手続き的に生成しました。',
                 'Walls, roofs, paving, ground and bark take their surface detail from CC0 texture sets; both groups below are CC0 throughout. '
                 'The leaf textures and the tree models are not downloaded: they are generated procedurally for this work.'),
    'other_cc0': ('その他の CC0', 'Other CC0'),
    'sky': ('秋と雪の夕暮れの空と環境光は、Poly Haven の HDRI をもとにしています。太陽の円盤は取り除き（太陽は別の光として描きます）、向きをそろえ、夕暮れの色に整えて、解像度を下げて使っています。',
            'The skies and ambient light of the autumn and the snowy evening are based on Poly Haven HDRI skies. The sun disc is removed (the sun is drawn as a separate, live light), '
            'the sky is rotated to match, graded to the evening colours, and the resolution is reduced.'),
    'sound': ('ピアノ独奏と、足音・水音・梵鐘などの音は、すべてブラウザの中で合成しています。録音した音は使っていません。',
              'The solo piano and the sounds of footsteps, water and the temple bell are all synthesised in the browser. No recordings are used.'),
    'software': ('ブラウザの中で動くものと、データをつくるために使った道具（作品には含まれません）に分けて記します。',
                 'Split into what runs in the page and the tools used offline to build the data, which are not part of the work.'),
    'sites': ('ランドマークは、公開されている情報・図面・写真を参考に、Blender で手づくりしました。写真をテクスチャとして使ってはいません。',
              'The landmarks are modelled by hand in Blender, using public information, plans and photographs for reference. No photograph is used as a texture.'),
    'note': ('この再構成は近似です。建物の大半は、PLATEAU と地図上の形から手続き的に生成したものです。手作りのランドマークも、資料や写真から細部・色・寸法を推定したもので、測量にもとづく公式のモデルではありません。'
             '寺院・神社などの名前は、場所を示すためにだけ使っています。',
             'This reconstruction is approximate. Most buildings are generated procedurally from PLATEAU and their footprints on the map. The hand-modelled landmarks, too, '
             'rest on references and photographs, with details, colours and proportions inferred; they are not official survey models. The names of temples, shrines and other places are used only to say where things are.'),
    'tagline': ('秋の夕暮れ、雪の夕暮れ。歩いて、空から。', 'An autumn evening, a snowy evening. On foot and from the air.'),
    'built': ('作成：' + BUILT + '。', 'Built ' + BUILT + '.'),
    'refs_not': ('モデル制作のために参照した写真は、配布していません。', 'The reference photographs used while modelling are not distributed.'),
    'col_data': ('データ', 'Data'), 'col_credit': ('出典', 'Credit'), 'col_licence': ('ライセンス', 'Licence'), 'col_set': ('テクスチャ', 'Texture set'),
    'col_author': ('作者', 'Author'), 'col_soft': ('ソフトウェア', 'Software'), 'col_use': ('用途', 'Used for'), 
    'in_page': ('ページの中で', 'In the page'), 'offline': ('制作時に', 'Offline, to build'), 'procedural': ('手続き生成', 'Procedural'),
    'autumn_sky': ('秋の空', 'autumn sky'), 'winter_sky': ('雪の空', 'snow sky'), 'unknown_src': ('出典不明', 'source unknown'),
}
SECTION_LABEL = {   # id -> (JA, EN) for the label column and the contents row
    'city': ('都市データ', 'City data'), 'textures': ('テクスチャ', 'Textures'), 'sky': ('空', 'Sky'), 'sound': ('音楽と音', 'Music and sound'),
    'software': ('ソフトウェア', 'Software'), 'sites': ('手作りのモデル', 'Hand-modelled'), 'note': ('注記', 'Note'),
}

# ------------------------------------------------------------------------------------------ cleaning
_ZW = re.compile('[' + ''.join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF)) + ']')   # zero-width characters


def ws(s):
    """collapse every kind of whitespace (NBSP, thin spaces, newlines) to single spaces"""
    return re.sub(r'\s+', ' ', _ZW.sub('', s or '')).strip()


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


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


def row2(left, right, note=''):
    """title | one more column (author, use, ...)"""
    return '<li class="it"><span class="t">%s%s</span><span class="a">%s</span></li>' % (left, note, right)


def note(html_, block=True):
    return '<span class="note%s">%s</span>' % (' blk' if block else '', html_)


def head_row(a, b, c=None):
    cols = [a, b] + ([c] if c else [])
    return '<div class="th%s" aria-hidden="true">%s</div>' % ('' if c else ' two', ''.join('<span>%s</span>' % x for x in cols))


def group(title, count, inner, cls=''):
    c = ' ' + cls if cls else ''
    n = '<small>%s</small>' % count if count != '' else ''
    return '<div class="group%s"><h3>%s%s</h3>%s</div>' % (c, title, n, inner)


def section(sid, sub, count, body):
    label = L(*SECTION_LABEL[sid])
    n = '<span class="n">%s</span>' % count if count != '' else ''
    s = '<span class="s">%s</span>' % sub if sub else ''
    return ('<section class="sec" id="%s"><div class="hd"><h2 class="lab">%s</h2>%s%s</div><div class="body">%s</div></section>' % (sid, label, s, n, body))


def lead(key):
    return '<p class="lead">' + T(key) + '</p>'


URL_RE = re.compile(r'https?://[^\s,，、)）。」]+')


def rich(text, link_licence=False):
    """plain text from CREDITS.txt -> html: URLs become links, licence names stay on one line (and, if asked, link to their text)"""
    out, pos = [], 0
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip('.;:')
        out.append(_plain(text[pos:m.start()], link_licence))
        out.append(A(url, esc(url)))
        pos = m.start() + len(url)
    out.append(_plain(text[pos:], link_licence))
    return ''.join(out)


def _plain(s, link_licence):
    s = esc(s)
    if link_licence:
        s = re.sub(r'CC BY-SA 4\.0', lambda m: A(CC_BY_SA, 'CC BY-SA 4.0', 'lic'), s)
    s = re.sub(r'(?<![\w>])(CC0)(?![\w])', lambda m: NW % m.group(1), s)
    if not link_licence:
        s = re.sub(r'CC BY-SA 4\.0', lambda m: NW % m.group(0), s)
    return s


# ------------------------------------------------------------------------------------------ data
def collect_textures():
    """the texture sets of gen/materials.py LAYERS: [(set name, manifest record or None)] in layer order, no repeats"""
    src = (HERE / 'gen' / 'materials.py').read_text(encoding='utf-8')
    layers = None
    for node in ast.parse(src).body:                             # LAYERS = [(name, source set, size, flags), ...]
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LAYERS' for t in node.targets):
            layers = ast.literal_eval(node.value)
    if not layers:
        raise SystemExit('credits: LAYERS not found in gen/materials.py')
    man = load_json(TEXTURES / 'manifest.json')
    sets = []
    for layer in layers:
        name, set_name = layer[0], layer[1]
        if set_name in [s[0] for s in sets]:
            continue
        if set_name in man:
            sets.append((set_name, man[set_name]))
        else:
            warn('texture set "%s" (layer %s) is not in textures/manifest.json: listed under other CC0, source unknown' % (set_name, name))
            sets.append((set_name, None))
    return sets


def collect_sky():
    """[(hdri key, manifest record, 'autumn'|'winter'|...)] for the HDRIs the viewer ships and the bake used"""
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


def collect_score():
    """score/CREDITS.txt -> {'short': (ja, en), 'long': [(ja label, ja text, en label, en text), ...]}"""
    path = SCORE / 'CREDITS.txt'
    if not path.exists():
        raise SystemExit('credits: missing ' + str(path))
    lines = [ln.rstrip() for ln in path.read_text(encoding='utf-8').splitlines()]
    heads = {'short_ja': r'^日本語（ページ用', 'short_en': r'^English \(for the page', 'long_ja': r'^日本語（詳細', 'long_en': r'^English \(long'}
    at = {}
    for k, pat in heads.items():
        idx = [i for i, ln in enumerate(lines) if re.match(pat, ln)]
        if len(idx) != 1:
            raise SystemExit('credits: score/CREDITS.txt: expected exactly one heading matching %s' % pat)
        at[k] = idx[0]
    order = sorted(at.values()) + [len(lines)]

    def block(k):
        i = at[k]
        end = next(o for o in order if o > i)
        body = lines[i + 1:end]
        body = [ln for ln in body if not re.match(r'^-{10,}\s*$', ln)]
        return body

    def short(k):
        text = []
        for ln in block(k):
            if not ln.strip():
                if text:
                    break
                continue
            text.append(ln.strip())
        return ws(' '.join(text))

    def items(k, marker):
        out = []
        for ln in block(k):
            if ln.startswith(marker):
                out.append(ln[len(marker):].strip())
            elif ln.strip() and out:
                out[-1] += ' ' + ln.strip()
        res = []
        for it in out:
            label, sep, text = it.partition(': ')
            res.append((ws(label), ws(text)) if sep else ('', ws(it)))
        return res

    ja, en = items('long_ja', '・'), items('long_en', '- ')
    if len(ja) != len(en) or not ja:
        raise SystemExit('credits: score/CREDITS.txt: %d Japanese notes but %d English ones' % (len(ja), len(en)))
    return {'short': (short('short_ja'), short('short_en')), 'long': [(a[0], a[1], b[0], b[1]) for a, b in zip(ja, en)]}


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
.lede+.lede{margin-top:1em;font-size:14px;color:var(--dim)}
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
.group>h3{display:flex;flex-wrap:wrap;align-items:baseline;gap:0 14px;margin:0 0 10px;font-size:15px;font-weight:600;letter-spacing:.02em;line-height:1.5}
.group>h3 small{font-size:11px;font-weight:400;letter-spacing:.14em;color:var(--faint);font-variant-numeric:tabular-nums}
.group>h3 .gl{font-size:11px;font-weight:400;letter-spacing:.14em;color:var(--dim)}
.group>h3 .gl a{text-decoration:none}
.group>h3 .gl a:hover{color:var(--ink);text-decoration:underline;text-underline-offset:.24em}

/* entries: title | author | licence   (two-column lists drop the last; facts: a label and a wide text) */
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
.two .it,.th.two{grid-template-columns:minmax(0,1.9fr) minmax(0,1.7fr)}
.facts .it{grid-template-columns:minmax(9em,.5fr) minmax(0,2.5fr);align-items:start;padding:12px 0}
.facts .it .t{color:var(--dim);font-size:12px;letter-spacing:.04em}
.facts .it .a{color:var(--ink);font-size:14px}

.foot{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:12px 32px;padding:30px 0 64px;border-top:1px solid var(--hair);font-size:12px;letter-spacing:.08em;color:var(--faint)}
.foot a{color:var(--dim);text-decoration:none;letter-spacing:.14em}
.foot a:hover{color:var(--ink)}
.foot .fine{flex:1 1 28em;text-align:right}

@media (max-width:860px){
  .sec{grid-template-columns:minmax(0,1fr);padding:28px 0 48px}
  .hd{position:static;display:flex;flex-wrap:wrap;align-items:baseline;gap:0 14px;margin-bottom:20px}
  .hd .s,.hd .n{margin-top:0}
  .it{grid-template-columns:minmax(0,1fr) auto;row-gap:1px}
  .it .t{grid-column:1/-1}
  .facts .it{grid-template-columns:minmax(0,1fr)}
  .th{display:none}
  .group{margin-top:38px}
  .foot .fine{text-align:left}
}
@media (max-width:420px){.lede{font-size:15px}.it .a{font-size:12.5px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
'''

HEAD_SCRIPT = "(function(){var h=(location.hash||'').toLowerCase();document.documentElement.lang=h==='#en'?'en':'ja';})();"

BODY_SCRIPT = r'''
(function () {
  var root = document.documentElement, T = { ja: 'クレジット — 京都', en: 'Credits — KYOTO' };
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
<meta name="description" content="KYOTO 京都 — 出典とライセンス / Sources and licences">
<title>クレジット — 京都</title>
<link rel="icon" href="data:,">
<!-- generated by tools/credits.py from the asset manifests; do not edit by hand -->
<script>%(head_script)s</script>
<style>%(css)s</style>
</head>
<body>
<div class="wrap">
<header class="top">
<a class="back back-link" href="index.html#ja">← %(name)s</a>
<div class="lang" role="group" aria-label="Language"><button type="button" data-l="ja">JA</button><button type="button" data-l="en">EN</button></div>
</header>
<div class="hero">
<h1 class="word">CREDITS</h1>
<p class="sub">%(sub)s</p>
<p class="lede">%(lede)s</p>
<p class="lede">%(lede2)s</p>
<ul class="toc">%(toc)s</ul>
</div>
<main>
%(sections)s
</main>
<footer class="foot"><a class="back-link" href="index.html#ja">← %(name)s</a><span class="fine">%(fine)s</span></footer>
</div>
<script>%(body_script)s</script>
</body>
</html>
'''


def city_section():
    plateau = row(
        A('https://www.mlit.go.jp/plateau/', L('3D都市モデル（Project PLATEAU）京都市 2025年度', '3D city model, Project PLATEAU: Kyoto City, FY2025')),
        T('plateau_credit'),
        L('PLATEAU サイトポリシー／政府標準利用規約（第2.0版）', 'PLATEAU site policy / Japanese Government Standard Terms of Use v2.0') + '<br>'
        + A(CC_BY, L('CC BY 4.0 互換', 'compatible with CC BY 4.0'), 'lic'),
        note(A('https://www.geospatial.jp/ckan/dataset/plateau-26100-kyoto-shi-2025', T('plateau_dataset'))) + note(T('plateau_note')))
    osm = row(
        A('https://www.openstreetmap.org/copyright', 'OpenStreetMap'),
        '© ' + A('https://www.openstreetmap.org/copyright', 'OpenStreetMap contributors'),
        A(LICENSE_URLS['ODbL'], 'ODbL 1.0', 'lic'),
        note(A('https://www.geofabrik.de/', 'Geofabrik') + ' · ' + T('osm_note')))
    gsi = row(
        A('https://maps.gsi.go.jp/development/ichiran.html', T('gsi_name')),
        T('gsi_credit'),
        A('https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html', L('国土地理院コンテンツ利用規約', 'GSI Terms of Use for content')) + '<br>'
        + A(CC_BY, L('CC BY 4.0 互換', 'compatible with CC BY 4.0'), 'lic'),
        note(T('gsi_note')))
    body = [lead('city'), head_row(T('col_data'), T('col_credit'), T('col_licence')), '<ul class="list">' + plateau + osm + gsi + '</ul>']
    return section('city', 'PLATEAU · OSM · GSI', 3, ''.join(body))


def textures_section(tex_sets):
    body = [lead('textures'), head_row(T('col_set'), T('col_author'))]
    by_src, other = {}, []
    for name, m in tex_sets:
        if m is None:
            other.append(name)
        else:
            by_src.setdefault(m.get('source', ''), []).append((name, m))
    for src in sorted(by_src, key=lambda s: -len(by_src[s])):
        lis, lics = '', set()
        for name, m in sorted(by_src[src], key=lambda x: natural_key(x[1].get('name', x[0]))):
            authors = ', '.join(re.sub(r'\s*\((?:ambientCG|Poly Haven)\)\s*$', '', a) for a in m.get('authors', []))
            lis += row2(A(m['url'], esc(m.get('name', name))), esc(authors))
            lics.add((ws(m.get('license', '')), m.get('license_url', '')))
        if len(lics) != 1:
            warn('%s: the texture sets do not share one licence: %s' % (src, sorted(lics)))
        lic, lic_url = sorted(lics)[0]
        h = A(SOURCE_URLS[src], esc(src)) if src in SOURCE_URLS else esc(src)
        tag = '<span class="gl">%s</span>' % A(lic_url or LICENSE_URLS.get(lic, ''), esc(lic)) if lic else ''
        body.append(group(h + tag, len(by_src[src]), '<ul class="list two">%s</ul>' % lis))
    if other:
        lis = ''.join(row2(esc(n), T('unknown_src')) for n in sorted(other, key=natural_key))
        body.append(group(T('other_cc0'), len(other), '<ul class="list two">%s</ul>' % lis))
    lis = ''.join(row2(L(esc(ja), esc(en)), L(esc(nja), esc(nen))) for ja, en, nja, nen in PROCEDURAL)
    body.append(group(T('procedural'), len(PROCEDURAL), '<ul class="list two">%s</ul>' % lis))
    return section('textures', '', len(tex_sets) + len(PROCEDURAL), ''.join(body))


def sky_section(skies):
    body = [lead('sky'), head_row('HDRI', T('col_author'))]
    lis, lics = '', set()
    for key, m, stem in skies:
        which = {'autumn': 'autumn_sky', 'winter': 'winter_sky'}.get(stem)
        lis += row2(A(m['url'], esc(hdri_name(key))) + note(T(which) if which else esc(stem), False), esc(', '.join(m.get('authors', []))))
        lics.add((ws(m.get('license', '')), m.get('license_url', '')))
    lic, lic_url = sorted(lics)[0] if lics else ('', '')
    tag = '<span class="gl">%s</span>' % A(lic_url or LICENSE_URLS.get(lic, ''), esc(lic)) if lic else ''
    body.append(group(A(SOURCE_URLS['Poly Haven'], 'Poly Haven') + tag, len(skies), '<ul class="list two">%s</ul>' % lis))
    return section('sky', '', len(skies), ''.join(body))


def sound_section(score):
    ja, en = score['short']
    body = [lead('sound'), '<p class="credit">' + L(rich(ja, True), rich(en, True)) + '</p>']
    lis = ''
    for lja, tja, len_, ten in score['long']:
        lis += '<li class="it"><span class="t">%s</span><span class="a">%s</span></li>' % (L(rich(lja), rich(len_)), L(rich(tja), rich(ten)))
    body.append('<div class="group facts"><ul class="list">%s</ul></div>' % lis)
    return section('sound', '', '', ''.join(body))


def software_section():
    def rows(items):
        out = ''
        for names, ja, en, lics in items:
            out += row(' · '.join(A(u, esc(n)) for n, u in names), L(esc(ja), esc(en)), ' · '.join(lic_html(x) for x in lics))
        return out
    body = [lead('software'), head_row(T('col_soft'), T('col_use'), T('col_licence')),
            group(T('in_page'), '', '<ul class="list">%s</ul>' % rows(SOFTWARE_PAGE)),
            group(T('offline'), '', '<ul class="list">%s</ul>' % rows(SOFTWARE_BUILD))]
    return section('software', '', '', ''.join(body))


def reference_photos():
    """freely licensed photographs looked at while modelling (Wikimedia Commons; manifests next to the downloads)"""
    import glob
    out = []
    for f in sorted(glob.glob('/home/kazu/work/kyoto-assets/refs/*/commons_*/manifest.json')):
        for m in json.load(open(f)):
            a = m.get('artist', '').strip(); h = len(a) // 2
            if h and a[:h] == a[h:]: a = a[:h]                       # Commons metadata sometimes repeats the name
            m['artist'] = a; out.append(m)
    return out


def sites_section():
    lis = ''.join(row2(L(esc(ja), esc(en)), L(esc(wja), esc(wen)) if wja else '') for ja, en, wja, wen in SITES)
    body = [lead('sites'), '<div class="group"><ul class="list two">%s</ul></div>' % lis]
    refs = reference_photos()
    if refs:
        rows_ = ''.join(row(A(m['url'], esc(m['title'].rsplit('.', 1)[0])), esc(m['artist'].split(' (talk)')[0] or '—'),
                            lic_html('Public domain' if m['license'].lower().startswith('public domain') else m['license']))
                        for m in refs)
        body.append(group(L('参考にした写真（Wikimedia Commons）', 'Reference photographs (Wikimedia Commons)'), len(refs),
                          note(L('形を見るためだけに参照し、画像そのものは使っていません。像高は文化遺産オンライン（文化庁）による。',
                                 'Looked at for the forms only; the images themselves are not used. Statue heights from Cultural Heritage Online (Agency for Cultural Affairs).'))
                          + '<ul class="list">%s</ul>' % rows_))
    return section('sites', '', len(SITES), ''.join(body))


def build(tex_sets, skies, score):
    sections = [
        city_section(),
        textures_section(tex_sets),
        sky_section(skies),
        sound_section(score),
        software_section(),
        sites_section(),
        section('note', '', '', '<p class="lead">' + T('note') + '</p>'),
    ]
    toc = ''.join('<li><a href="#%s" data-go="%s">%s</a></li>' % (sid, sid, L(*SECTION_LABEL[sid])) for sid in SECTION_LABEL)
    fine = T('built') + ' ' + T('refs_not')
    lede = T('lede')
    return PAGE % {'head_script': HEAD_SCRIPT, 'css': CSS, 'name': L('京都', 'KYOTO'), 'sub': T('sub'), 'lede': lede, 'lede2': T('lede2'), 'toc': toc,
                   'sections': '\n'.join(sections), 'fine': fine, 'body_script': BODY_SCRIPT}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else PUBLIC / 'credits.html'
    tex_sets = collect_textures()
    skies = collect_sky()
    score = collect_score()
    page = build(tex_sets, skies, score)
    out.write_text(page, encoding='utf-8')
    per = {}
    for _, m in tex_sets:
        per[m['source'] if m else 'unknown'] = per.get(m['source'] if m else 'unknown', 0) + 1
    print('credits: wrote %s (%d KB)' % (out, len(page.encode('utf-8')) // 1024))
    print('  texture sets    %d downloaded (%s) + %d procedural' % (len(tex_sets), ', '.join('%s %d' % kv for kv in per.items()), len(PROCEDURAL)))
    print('  sky             %d   %s' % (len(skies), ', '.join(k for k, _, _ in skies)))
    print('  music notes     %d' % len(score['long']))
    print('  warnings        %d' % len(WARN))


if __name__ == '__main__':
    main()
