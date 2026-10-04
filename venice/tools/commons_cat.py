"""list files (and subcategories) of a Commons category:  python commons_cat.py "Category:Name" [files|subcats]"""
import sys, json, urllib.parse, urllib.request
UA = 'demos-venice/0.1 (https://demos.kazumasa.workers.dev; non-commercial demo)'
cat = sys.argv[1]; kind = sys.argv[2] if len(sys.argv) > 2 else 'files'
cont = {}
while True:
    params = dict(action='query', format='json', list='categorymembers', cmtitle=cat, cmlimit=200, cmtype='file' if kind == 'files' else 'subcat', **cont)
    d = json.load(urllib.request.urlopen(urllib.request.Request('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params), headers={'User-Agent': UA}), timeout=60))
    for m in d['query']['categorymembers']: print(m['title'])
    if 'continue' in d: cont = {'cmcontinue': d['continue']['cmcontinue']}
    else: break
