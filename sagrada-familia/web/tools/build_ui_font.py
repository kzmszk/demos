"""Reuse the audited bundled Japanese UI font, or rebuild from SIL-OFL Noto CJK.

Rebuilding needs fontTools and brotli and refreshes the bundled font/audit/license.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('FONT_SOURCE', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')).expanduser()
LICENSE_SOURCE = Path(os.environ.get('FONT_LICENSE_SOURCE', '/usr/share/doc/fonts-noto-cjk/copyright')).expanduser()
OUT = ROOT / 'web/godot/assets/sagrada_familia_ui.woff2'
BUNDLED_FONT = ROOT / 'runtime/assets/sagrada_familia_ui.woff2'
BUNDLED_AUDIT = ROOT / 'web/tools/font_audit.json'
EXTRA = ('飛行 自由 上昇 下降 歩行に戻る 最後の安全な床へ 高度 読込中 準備完了 Web版 '
         '開始 再開 品質 標準 軽量 高品質 操作一覧 場所 移動 写真 保存 リセット 固定 FPS '
         '全画面 解除 視点 再読み込み 明るさ 近く 遠く 降りる 天井 窓 外観 内部 閉じる '
         'マウス クリック キーボード モード 切替 正面 身廊 北 南 東 西 礼拝堂 周歩廊 '
         '↑↓←→ · — – × … • ／ ＋ － ％ ℃ ①②③④⑤⑥ 2026年10月1日 サグラダ・ファミリア バルセロナ')

text = EXTRA
source_paths=set((ROOT/'runtime/scripts').glob('*.gd'))
for folder in [ROOT/'web/godot',ROOT/'web/qa']:
    for extension in ['*.gd','*.html','*.js']:
        source_paths.update(path for path in folder.rglob(extension) if '.godot' not in path.parts)
source_records=[]
for path in sorted(source_paths):
    source_text=path.read_text()
    text+=source_text
    source_records.append({'path':str(path.relative_to(ROOT)),
                           'sha256':hashlib.sha256(source_text.encode()).hexdigest()})
codepoints = set(map(ord, text))
for first,last in [(32,126),(160,255),(0x3000,0x303f),(0x3040,0x309f),(0x30a0,0x30ff)]:
    codepoints.update(range(first,last+1))

def reuse_verified_font():
    """A matching hash plus recorded cmap allows dependency-free UI coverage checks."""
    audit_path=ROOT/'web/qa/font_audit.json'
    if not (ROOT/'web/tools/font_license.txt').is_file():
        return False
    required={ord(c) for c in text if ord(c)>=32 and not c.isspace()}
    for font_path, metadata_path in [(OUT,audit_path),(BUNDLED_FONT,BUNDLED_AUDIT)]:
        if not font_path.is_file() or not metadata_path.is_file():
            continue
        audit=json.loads(metadata_path.read_text())
        covered=set(audit.get('covered_codepoints',[]))
        if not covered or hashlib.sha256(font_path.read_bytes()).hexdigest()!=audit.get('sha256') or required-covered:
            continue
        OUT.parent.mkdir(parents=True,exist_ok=True)
        audit_path.parent.mkdir(parents=True,exist_ok=True)
        if font_path != OUT:
            shutil.copy2(font_path,OUT)
            audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
        report={'reused_verified_font':True,'sha256':audit['sha256'],
                'checked_ui_codepoints':len(required),'missing_ui_codepoints':[],
                'input_sources':source_records,
                'font_source':str(font_path.relative_to(ROOT)),
                'method':'Recorded generated-font cmap and file SHA256; no fontTools/Brotli needed.'}
        (ROOT/'web/qa/font_reuse_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return True
    return False

if os.environ.get('FONT_REBUILD')!='1' and reuse_verified_font():
    raise SystemExit(0)
try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    import brotli
except ImportError as exc:
    raise SystemExit('The saved font cannot cover current UI text, or its hash/cmap audit is missing. '
                     'A font rebuild requires fontTools and Brotli plus the Noto CJK source font. '
                     'Set FONTTOOLS_PYTHONPATH to existing packages; no download/install was attempted. '
                     +str(exc))
if not SOURCE.is_file():
    raise SystemExit('Font rebuild needs the Noto CJK source: '+str(SOURCE))
if not LICENSE_SOURCE.is_file():
    raise SystemExit('Font rebuild needs its license file; set FONT_LICENSE_SOURCE: '+str(LICENSE_SOURCE))
font = TTFont(str(SOURCE), fontNumber=0)
source_cmap = font.getBestCmap()
requested = {c for c in codepoints if c in source_cmap}
options = subset.Options()
options.flavor = 'woff2'
options.layout_features = ['*']
options.name_IDs = ['*']
options.name_legacy = True
options.name_languages = ['*']
subsetter = subset.Subsetter(options=options)
subsetter.populate(unicodes=requested)
subsetter.subset(font)
names = {1:'Sagrada Familia UI Subset',2:'Regular',3:'SagradaFamiliaUISubset-Regular',
         4:'Sagrada Familia UI Subset Regular',6:'SagradaFamiliaUISubset-Regular',
         16:'Sagrada Familia UI Subset',17:'Regular'}
for record in font['name'].names:
    if record.nameID in names:
        record.string = names[record.nameID].encode(record.getEncoding())
if 'CFF ' in font:
    font['CFF '].cff.fontNames = ['SagradaFamiliaUISubset-Regular']
    top = font['CFF '].cff.topDictIndex[0]
    top.FamilyName = 'Sagrada Familia UI Subset'
    top.FullName = 'Sagrada Familia UI Subset Regular'
font.flavor = 'woff2'
OUT.parent.mkdir(parents=True,exist_ok=True)
font.save(str(OUT))
verified = TTFont(str(OUT))
missing = sorted(c for c in requested if c not in verified.getBestCmap())
assert not missing, missing
metadata = {
    'source':str(SOURCE), 'source_collection_font_index':0,
    'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'output':str(OUT.relative_to(ROOT)), 'bytes':OUT.stat().st_size,
    'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),
    'license':'SIL Open Font License 1.1', 'derived_family':'Sagrada Familia UI Subset',
    'unicode_count':len(verified.getBestCmap()), 'covered_requested_codepoints':len(requested),
    'covered_codepoints':sorted(verified.getBestCmap()),
    'missing_requested_codepoints':missing,
    'input_sources':source_records,
    'source_characters_not_supported_by_base_font':[c for c in sorted(set(text)) if ord(c)>=32 and not c.isspace() and ord(c) not in source_cmap],
    'note':'Subset includes current native scripts, all Web Godot/QA GDScript/HTML/JavaScript source characters, Latin-1, Hiragana, Katakana, Japanese punctuation, and Web flight UI vocabulary. Rebuild after adding new UI strings.',
    'source_url':'https://github.com/notofonts/noto-cjk',
}
(ROOT/'web/qa').mkdir(parents=True,exist_ok=True)
(ROOT/'web/qa/font_audit.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
BUNDLED_AUDIT.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
shutil.copy2(OUT,BUNDLED_FONT)
(ROOT/'web/qa/font_reuse_audit.json').unlink(missing_ok=True)
license_text = LICENSE_SOURCE.read_text()
(ROOT/'web/tools/font_license.txt').write_text('Sagrada Familia UI Subset is a modified subset of Noto Sans CJK JP Regular.\nThe font family has been renamed. Distributed under SIL OFL 1.1.\n\n'+license_text)
print(json.dumps(metadata,ensure_ascii=False,indent=2))
