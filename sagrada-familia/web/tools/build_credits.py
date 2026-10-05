#!/usr/bin/env python3
from pathlib import Path
import html,shutil,json
root=Path(__file__).resolve().parents[2]
output=root/'web/dist'
output.mkdir(parents=True,exist_ok=True)
links=[('公式・2026年9月22日 工事状況','https://sagradafamilia.org/es/-/la-sagrada-familia-avanca-en-la-darrera-fase-de-construccio-del-temple-projectat-per-antoni-gaudi'),('公式・イエス塔の十字架','https://sagradafamilia.org/en/-/una-creu-que-arriba-al-cel-de-barcelona'),('公式・工事の歩み','https://sagradafamilia.org/en/history-of-the-temple'),('公式・中央クレーンの現状','https://sagradafamilia.org/es/-/la-grua-central-de-la-sagrada-familia-inicia-una-nova-etapa-despres-de-completar-l-exterior-de-la-torre-de-jesucrist')]
body=''.join('<li><a href="'+url+'">'+label+'</a></li>' for label,url in links)
texture_attribution=''
material_file=root/'docs/MATERIAL_SOURCES.json'
if material_file.exists():
 data=json.loads(material_file.read_text())
 for item in data.get('references',[]):
  if not item.get('included_texture'): continue
  title=html.escape(item.get('title',item['included_texture']))
  author=html.escape(item.get('photographer','See ledger'))
  license_name=html.escape(item.get('license','See ledger'))
  url=html.escape(item.get('url') or item.get('source_page',''),quote=True)
  license_url=html.escape(item.get('license_url',''),quote=True)
  changes=html.escape(item.get('changes','See ledger'))
  texture_attribution+=f'<li><a href="{url}">{title}</a><br>© {author} / Wikimedia Commons / <a href="{license_url}">{license_name}</a><br>{changes}</li>'
if texture_attribution: texture_attribution='<h2>実際に使った窓ガラス写真</h2><ul>'+texture_attribution+'</ul>'
source=''
scope_docs=['MODEL_LIMITS.md','CURRENT_STATE.json','INTERIOR_ATTACHMENT_VERIFICATION.json','EAST_GLAZING_ADDITIONS.json','PORTAL_WEATHER_BACKING_FIX.json','YELLOWGREEN_DETAIL_VALIDATION.json','CAPITAL_FINISH_VERIFICATION.json']
documents=sorted((root/'docs').glob('*'),key=lambda doc:(scope_docs.index(doc.name) if doc.name in scope_docs else len(scope_docs),doc.name))
for doc in documents:
 if doc.suffix.lower() in ['.md','.json','.csv'] and (doc.name in scope_docs or 'SOURCE' in doc.name.upper() or 'EVIDENCE' in doc.name.upper()):
  source+='<h2>'+html.escape(doc.name)+'</h2><pre>'+html.escape(doc.read_text())+'</pre>'
(output/'credits.html').write_text('''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>資料と出典 · Sagrada Família</title><style>body{background:#15232a;color:#e9e7dd;font:16px/1.9 system-ui;max-width:950px;padding:5vw;margin:auto}a{color:#cbd8a9}h1{font:42px Georgia}pre{white-space:pre-wrap;font:13px/1.8 system-ui}li{margin:1em 0}</style><a href="index.html">← 見学に戻る</a><h1>Sagrada Família · 2026</h1><p>2026年10月1日版。最新の公式工事資料は2026年9月22日。完成予想図ではありません。</p><p>資料に基づく独立した建築再構成であり、公式計測モデルではありません。塔内部・立入制限区域、彫刻の細部、装飾、周辺環境に推定と簡略化を含みます。リアルタイムの光は鑑賞用の近似で、特定時刻の測定された採光を表すものではありません。</p><p>イエス塔の外装は172.5mで完成、内部は工事中です。栄光のファサードと被昇天礼拝堂は未完成として扱います。完成状況の文章は下記公式資料に基づきます。</p><ul>'''+body+'''</ul><h2>実装・素材</h2><p>独自の編集可能Blender建築モデル。Godot Engine 4.7.2 (MIT)、日本語フォントはNoto Sans CJKの改変サブセット (SIL OFL 1.1)。歩行制御と分割配信ローダーは同じワークスペース内の先行作品から再利用。窓ガラスには利用条件を確認した写真由来の素材を使用しています。同じ窓群の写真を繰り返す箇所と、後陣への解釈的な適用を含みます。原作者・ライセンス・加工内容は素材台帳を参照してください。</p><p><a href="font_license.txt">フォントライセンス全文</a> · <a href="godot_license.txt">Godotライセンス</a> · <a href="godot_copyright.txt">Godot第三者著作権表記</a></p>'''+texture_attribution+source+'</html>')
shutil.copy2(root/'web/tools/font_license.txt',output/'font_license.txt')
legal=root/'web/licenses/godot'
shutil.copy2(legal/'LICENSE.txt',output/'godot_license.txt')
shutil.copy2(legal/'COPYRIGHT.txt',output/'godot_copyright.txt')
