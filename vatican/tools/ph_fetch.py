"""Poly Haven (CC0) texture fetcher: diffuse, normal (GL), roughness at the given resolution."""
import json, os, sys, time, urllib.request
UA = 'demos-vatican/0.1 (https://demos.kazumasa.workers.dev)'
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=120).read()
res = sys.argv[1]; ids = sys.argv[2:]
man = json.load(open('manifest.json')) if os.path.exists('manifest.json') else {}
for i in ids:
    files = json.loads(get(f'https://api.polyhaven.com/files/{i}'))
    info = json.loads(get(f'https://api.polyhaven.com/info/{i}'))
    out = {}
    for mp, key in (('Diffuse', 'diff'), ('nor_gl', 'nor'), ('Rough', 'rough')):
        if mp not in files: continue
        u = files[mp][res]['jpg']['url']
        dst = f'{i}_{key}_{res}.jpg'
        if not os.path.exists(dst):
            open(dst, 'wb').write(get(u)); time.sleep(0.5)
        out[key] = dst
    man[i] = {'files': out, 'license': 'CC0', 'authors': list(info.get('authors', {}).keys()), 'url': f'https://polyhaven.com/a/{i}'}
    print(i, out, man[i]['authors'])
json.dump(man, open('manifest.json', 'w'), indent=1)
