"""search Wikimedia Commons files:  python commons_search.py "query" [limit]  -> title, size, license"""
import sys, json, urllib.parse, urllib.request, time
UA = 'demos-venice/0.1 (https://demos.kazumasa.workers.dev; non-commercial demo)'
q = sys.argv[1]; lim = int(sys.argv[2]) if len(sys.argv) > 2 else 30
url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(action='query', format='json', generator='search', gsrsearch=q, gsrnamespace=6, gsrlimit=lim, prop='imageinfo', iiprop='size|extmetadata|url'))
d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60))
for p in sorted(d.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
    ii = (p.get('imageinfo') or [{}])[0]; m = ii.get('extmetadata', {})
    lic = (m.get('LicenseShortName') or {}).get('value', '')
    print(f"{ii.get('width')}x{ii.get('height')}\t{lic}\t{p['title']}")
