#!/usr/bin/env python3
"""Fetch files from Wikimedia Commons with their licence metadata.

usage: commons_fetch.py OUTDIR "File:Title 1" "File:Title 2" ...   (or --list file.txt)
Writes OUTDIR/<safe name> and appends/updates OUTDIR/manifest.json with
title, url, size, licence, artist, credit and the description page, so the
credits page can be generated from it. Already-downloaded files of the right
size are skipped. Sequential and throttled (Commons asks for that)."""
import json, os, re, sys, time, urllib.parse, urllib.request, html

UA = 'demos-venice/0.1 (https://demos.kazumasa.workers.dev; non-commercial demo)'

def api(**kw):
    kw.setdefault('format', 'json')
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(kw)
    for i in range(6):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503): time.sleep(15 * (i + 1)); continue
            raise
    raise RuntimeError('api failed')

def strip(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    return html.unescape(s).strip()

def safe(title):
    n = title.split(':', 1)[1]
    n = re.sub(r'[^\w.\-]+', '_', n, flags=re.UNICODE).strip('_')
    return n[:150]

def info(titles):
    out = {}
    for i in range(0, len(titles), 25):
        d = api(action='query', titles='|'.join(titles[i:i+25]), prop='imageinfo',
                iiprop='url|size|extmetadata|mime', redirects=1)
        q = d['query']
        redir = {r['to']: r['from'] for r in q.get('redirects', [])}
        norm = {n['to']: n['from'] for n in q.get('normalized', [])}
        for p in q['pages'].values():
            if 'imageinfo' not in p:
                print('MISSING', p.get('title')); continue
            ii = p['imageinfo'][0]; m = ii.get('extmetadata', {})
            g = lambda k: (m.get(k, {}) or {}).get('value', '')
            out[p['title']] = dict(
                title=p['title'], requested=norm.get(redir.get(p['title'], p['title']), redir.get(p['title'], p['title'])),
                url=ii['url'].split('?')[0], page=ii.get('descriptionurl'), size=ii['size'],
                width=ii.get('width'), height=ii.get('height'), mime=ii.get('mime'),
                license=strip(g('LicenseShortName')), license_url=strip(g('LicenseUrl')),
                artist=strip(g('Artist'))[:300], credit=strip(g('Credit'))[:300],
                object=strip(g('ObjectName'))[:200], date=strip(g('DateTimeOriginal'))[:80])
        time.sleep(1)
    return out

def main():
    outdir = sys.argv[1]; args = sys.argv[2:]
    if args and args[0] == '--list':
        args = [l.strip() for l in open(args[1]) if l.strip() and not l.startswith('#')]
    os.makedirs(outdir, exist_ok=True)
    mpath = os.path.join(outdir, 'manifest.json')
    man = json.load(open(mpath)) if os.path.exists(mpath) else {}
    meta = info(args)
    for t, m in meta.items():
        fn = safe(t); dst = os.path.join(outdir, fn); m['file'] = fn
        if os.path.exists(dst) and os.path.getsize(dst) == m['size']:
            print('have', fn); man[t] = m; continue
        print(f"get  {fn}  {m['size']/1e6:.1f} MB  [{m['license']}]", flush=True)
        for i in range(6):
            try:
                req = urllib.request.Request(m['url'], headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=300) as r, open(dst + '.part', 'wb') as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b: break
                        f.write(b)
                if os.path.getsize(dst + '.part') != m['size']: raise RuntimeError('short')
                os.replace(dst + '.part', dst); break
            except Exception as e:
                print('  retry', e, flush=True); time.sleep(20 * (i + 1))
        man[t] = m
        json.dump(man, open(mpath, 'w'), ensure_ascii=False, indent=1)
        time.sleep(2)
    json.dump(man, open(mpath, 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
