"""Collect public/textures/<module>/credits.json of the outdoor hero modules into a section of
public/texture-credits.html (between <!-- heroes --> markers)."""
import html, json, os, re
ROOT = os.path.join(os.path.dirname(__file__), '..', 'public')
NAMES = {'alcazaba': 'アルカサバ / Alcazaba', 'carlos': 'カルロス5世宮殿 / Palace of Charles V', 'partal': 'パルタル / El Partal',
         'gates': '門と城壁 / Gates and walls', 'grounds': '敷地 / Grounds', 'generalife': 'ヘネラリフェ / Generalife'}
e = html.escape
rows = []
for mod, label in NAMES.items():
    p = os.path.join(ROOT, 'textures', mod, 'credits.json')
    if not os.path.exists(p): continue
    data = json.load(open(p))
    if isinstance(data, dict): data = data.get('sources') or data.get('textures') or []
    rows.append(f'<tr><th colspan="4">{e(label)}</th></tr>')
    for c in data:
        f = c.get('file', ''); src = c.get('source', ''); lic = c.get('license', ''); url = c.get('licenseUrl', '')
        name = e(c.get('originalTitle') or f)
        link = f'<a href="textures/{e(mod)}/{e(f)}">{name}</a>' if f else name
        srcl = f'<a href="{e(src)}">Wikimedia Commons</a>' if src.startswith('http') else e(src)
        licl = f'<a href="{e(url)}">{e(lic)}</a>' if url else e(lic)
        rows.append(f'<tr><td>{link}<br><small>{e(c.get("changes", ""))}</small></td><td>{e(c.get("author", ""))}</td><td>{licl}</td><td>{srcl}</td></tr>')
section = ('<!-- heroes --><h2>屋外の建築（2026-10-23の再構築） / Outdoor monuments</h2>'
           '<p>アルカサバ、カルロス5世宮殿、パルタル、門と城壁、敷地、ヘネラリフェの材質。多くはコードで生成した手続き的テクスチャで、'
           '写真は形や色の参考にのみ使用しています。写真から作った材質は元の写真と同じライセンスです。</p>'
           '<p lang="en">Materials of the rebuilt outdoor monuments. Most are procedural textures generated for this project, with '
           'Commons photographs used only as references; photo-derived textures keep the licence of their source.</p>'
           '<table><thead><tr><th>素材</th><th>作者・撮影者</th><th>ライセンス</th><th>出典</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table><!-- /heroes -->')
p = os.path.join(ROOT, 'texture-credits.html'); s = open(p).read()
if '<!-- heroes -->' in s: s = re.sub(r'<!-- heroes -->.*<!-- /heroes -->', lambda m: section, s, flags=re.S)
else: s = s.replace('</main>', section + '</main>') if '</main>' in s else s + section
open(p, 'w').write(s)
print(len(rows), 'rows')
