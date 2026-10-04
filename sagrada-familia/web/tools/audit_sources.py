#!/usr/bin/env python3
"""Audit embedded model ingredients and generated attribution (requires Pillow).

Run only after the final GLB and credits are frozen. Writes the source-audit JSON;
there are no model edits, network requests, rendering operations or publication.
"""
import pathlib,json,hashlib,struct,io,html,datetime,urllib.parse
from PIL import Image
R=pathlib.Path(__file__).resolve().parents[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads((R/p).read_text())
A=load('docs/ARTWORK_SOURCES.json');M=load('docs/MATERIAL_SOURCES.json');E=load('docs/EXTERIOR_EVIDENCE.json');D=load('assets/textures/exterior_sculpture/reliefs.json')
byname={pathlib.Path(x['local_path']).name:x for x in A['entries']};byhash={x['sha256']:x for x in A['entries']};ext={x['id']:x for x in E['derived_artwork_assets']};v8={x['id']:x for x in E.get('v8_photo_edge_derivatives',[])}
items=[];issues=[]
bank_documents=[load('assets/textures/window_banks.json')]
for candidate in ['assets/textures/east_bank_candidates.json','docs/EAST_GLAZING_ADDITIONS.json']:
 if (R/candidate).exists():bank_documents.append(load(candidate))
def walk_records(value):
 if isinstance(value,dict):
  yield value
  for child in value.values():yield from walk_records(child)
 elif isinstance(value,list):
  for child in value:yield from walk_records(child)
def polygons(value):
 if not isinstance(value,list) or not value:return
 if len(value)>=3 and all(isinstance(p,list) and len(p)==2 and all(isinstance(n,(float,int)) for n in p) for p in value):
  yield value
 else:
  for child in value:yield from polygons(child)
def audit_atlas(path,digest):
 bank=next((record for doc in bank_documents for record in walk_records(doc)
            if pathlib.Path(record.get('texture','')).name==path.name and record.get('derivation',{}).get('sources')),None)
 if not bank:return None
 derivation=bank['derivation'];atlas=Image.open(path).convert('RGBA');components=[];bounds=[]
 for source in derivation['sources']:
  original=R/source['path'];original_hash=sha(original);registered=byhash.get(original_hash)
  pixels=Image.open(original).convert('RGBA');ox,oy=source['offset_px'];w,h=pixels.size
  match=atlas.crop((ox,oy,ox+w,oy+h)).tobytes()==pixels.tobytes()
  bounds.append((ox,oy,ox+w,oy+h))
  components.append({'path':source['path'],'sha256':original_hash,'declared_hash_matches':original_hash==source['sha256'],
   'registered_source_id':registered['id'] if registered else None,'offset_px':[ox,oy],'size_px':[w,h],
   'decoded_pixel_block_identical':match,'source_url':registered.get('source_page') if registered else None,
   'photographer':source.get('photographer'),'license':source.get('license'),'license_url':source.get('license_url'),
   'underlying_artwork_note':registered.get('underlying_artwork_note') if registered else None})
 aperture_checks=[]
 for key in ['caps','circles','large','core','petals']:
  for polygon in polygons(bank.get(key,[])):
   owners=[i for i,(x0,y0,x1,y1) in enumerate(bounds) if all(x0<=x<=x1 and y0<=y<=y1 for x,y in polygon)]
   aperture_checks.append({'group':key,'source_block_indices':owners,'within_one_source_block':len(owners)==1})
 passed=digest==derivation.get('atlas_sha256') and bool(components) and all(c['declared_hash_matches'] and c['registered_source_id'] and c['decoded_pixel_block_identical'] for c in components)
 passed=passed and bool(aperture_checks) and all(c['within_one_source_block'] for c in aperture_checks)
 return {'passed':bool(passed),'atlas_sha256':digest,'atlas_license':derivation.get('atlas_license'),
  'atlas_license_url':derivation.get('atlas_license_url'),'method':derivation.get('method'),
  'components':components,'apertures_checked':len(aperture_checks),'aperture_checks':aperture_checks}
for x in M['references']:
 if not x.get('included_texture'):continue
 p=R/x['included_texture'];digest=sha(p);a=byhash.get(digest);url=x.get('url') or x.get('source_page');missing=[k for k in ['photographer','license','license_url','changes'] if not x.get(k)]
 if not url:missing.append('source URL')
 atlas=audit_atlas(p,digest) if not a else None
 chain_ok=bool(a) or bool(atlas and atlas['passed'])
 items.append({'kind':'glass','texture':x['included_texture'],'texture_sha256':digest,'source_id':a['id'] if a else x.get('id'),
  'source_url':url,'photographer':x.get('photographer'),'license':x.get('license'),'license_url':x.get('license_url'),
  'modifications':x.get('changes'),'original_file_bytes_match':bool(a),'source_chain_verified':chain_ok,'atlas_validation':atlas,
  'underlying_artist':'Joan Vila-Grau, separately attributed in MATERIAL_SOURCES.redistribution.photograph_attribution',
  'underlying_rights_distinguished':bool(a and a.get('underlying_artwork_note')) or bool(atlas and all(c['underlying_artwork_note'] for c in atlas['components'])),
  'missing_metadata':missing})
 if missing or not chain_ok:issues.append({'severity':'error','asset':p.name,'detail':'Missing source chain or metadata, or atlas pixel/polygon mismatch','fields':missing})
for x in D:
 a=byname[x['source']];e=ext[x['id']];chain=v8.get(x['id'],{});p=R/x.get('render_texture',x['texture']);missing=[k for k in ['original_photo_page','author','license','license_url','adaptation','adaptation_license'] if not e.get(k)]
 checks={}
 for k,hk in [('source_texture','source_sha256'),('derivative_texture','derivative_sha256'),('transition_mask','transition_mask_sha256'),('stone_tile','stone_tile_sha256')]:
  if chain.get(k):checks[k]={'path':chain[k],'sha256':sha(R/chain[k]),'matches_record':sha(R/chain[k])==chain.get(hk)}
 items.append({'kind':'sculpture','id':x['id'],'texture':str(p.relative_to(R)),'texture_sha256':sha(p),'source_id':a['id'],'source_url':a['source_page'],'photographer':a['photographer'],'license':a['photo_license'],'license_url':a['license_url'],'modifications':e['adaptation']+' '+chain.get('method',''),'adaptation_license':e['adaptation_license'],'underlying_artist':a.get('sculptor'),'underlying_rights_distinguished':bool(a.get('underlying_artwork_note')),'source_chain':checks,'missing_metadata':missing})
 if missing or not all(c['matches_record'] for c in checks.values()):issues.append({'severity':'error','asset':x['id'],'detail':'Derivative metadata or hash-chain mismatch','fields':missing})
# Independently inspect currently available GLB, recording exactly which version was read.
p=R/'build/sagrada_familia.glb';before=p.stat();image_rows=[]
with p.open('rb') as f:
 magic,version,total=struct.unpack('<4sII',f.read(12));jlen,jtype=struct.unpack('<II',f.read(8));g=json.loads(f.read(jlen));blen,btype=struct.unpack('<II',f.read(8));bstart=f.tell()
 for n,im in enumerate(g.get('images',[])):
  bv=g['bufferViews'][im['bufferView']];f.seek(bstart+bv.get('byteOffset',0));data=f.read(bv['byteLength']);h=hashlib.sha256(data).hexdigest();name=im.get('name','');matches=[]
  # Prefer exact bytes; Blender image export may encode PNG differently, so allow exact decoded RGBA comparison.
  candidates=[R/i['texture'] for i in items if pathlib.Path(i['texture']).stem==name or i.get('id')==name or (i.get('id') and name.startswith(i['id']))]
  for x in D:
   if name in [x['id'],pathlib.Path(x['texture']).stem,pathlib.Path(x.get('render_texture',x['texture'])).stem]:candidates +=[R/x['texture'],R/x.get('render_texture',x['texture'])]
  if not candidates:
   # Stone studies keep authored PNGs in versioned subdirectories. Compare
   # every literal filename match; a familiar name alone never validates it.
   candidates=[c for c in (R/'assets/textures').rglob('*.png') if c.is_file() and c.name==name+'.png']
  for c in sorted(set(candidates)):
   if sha(c)==h:matches.append({'path':str(c.relative_to(R)),'comparison':'identical_bytes'})
   elif name.endswith('_rough'):
    aa=Image.open(io.BytesIO(data)).convert('RGB');bb=Image.open(c).convert('L')
    if aa.size==bb.size and aa.getchannel('G').tobytes()==bb.tobytes() and aa.getchannel('R').getextrema()==(255,255) and aa.getchannel('B').getextrema()==(255,255):matches.append({'path':str(c.relative_to(R)),'comparison':'roughness green channel identical, red/blue constant255'})
   else:
    aa=Image.open(io.BytesIO(data)).convert('RGBA');bb=Image.open(c).convert('RGBA')
    if aa.size==bb.size and aa.tobytes()==bb.tobytes():matches.append({'path':str(c.relative_to(R)),'comparison':'identical_decoded_RGBA'})
  photo_paths={i['texture'] for i in items};photo=(name.startswith('glass_') or any(name.startswith(x['id']) for x in D) or any(m['path'] in photo_paths for m in matches));image_rows.append({'index':n,'name':name,'bytes':len(data),'sha256':h,'classification':'licensed_photo_derivative' if photo else 'authored_procedural','source_candidates_checked':[str(c.relative_to(R)) for c in sorted(set(candidates))],'source_matches':matches})
  if photo and not matches:issues.append({'severity':'error','asset':name,'detail':'Embedded photo image does not match known source/derivative.'})
  if not photo and not matches:issues.append({'severity':'error','asset':name,'detail':'Embedded image unknown, not matched to procedural asset.'})
after=p.stat();stable=(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
if not stable:issues.append({'severity':'error','detail':'GLB changed during read; rerun after export freezes.'})
# Official photographs are forbidden ingredients; compare byte hashes as an independent check.
official=[]
for d in [R/'references/exterior',R/'assets/reference']:
 if d.exists():
  for x in d.iterdir():
   if x.is_file() and x.suffix.lower() in ['.jpg','.png','.jpeg'] and ('official' in x.name or x.name.startswith('qa_')):official.append((str(x.relative_to(R)),sha(x)))
collisions=[{'image':x['name'],'reference':p} for x in image_rows for p,h in official if h==x['sha256']]
if collisions:issues.append({'severity':'error','detail':'Official reference image hash matches an embedded image.','matches':collisions})
credits=R/'web/dist/credits.html';text=html.unescape(credits.read_text());credit_checks=[]
for x in items:
 c={'texture':x['texture'],'photographer_present':x['photographer'] in text or x['photographer'].replace('Jose ','José ') in text,'source_url_present':x['source_url'] in text,'license_url_present':x['license_url'] in text,'underlying_artist_present':('Joan Vila-Grau' in text if x['kind']=='glass' else x['underlying_artist'] in text if x['underlying_artist'] else False)}
 credit_checks.append(c)
 if not all(v for k,v in c.items() if k!='texture'):issues.append({'severity':'error','asset':x['texture'],'detail':'Missing visible attribution field in generated credits','checks':c})
v8_embedded=all(any(m['path']==x['texture'] for row in image_rows for m in row['source_matches']) for x in items if x['kind']=='sculpture')
credits_v8='v8_photo_edge_derivatives' in text
if not v8_embedded:issues.append({'severity':'pending_final_build','detail':'Current GLB still uses pre-V8 sculptures; recheck final exported V8.'})
if not credits_v8:issues.append({'severity':'pending_final_build','detail':'Current credits lack V8 derivative record; runtime will regenerate at freeze.'})
report={'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Source/attribution integrity for local review build. This does not grant new underlying-artwork reproduction rights or authorize publication.','status':'pending_final_export' if not(v8_embedded and credits_v8) else 'pass' if not issues else 'issues','inputs':{p:sha(R/p) for p in ['docs/ARTWORK_SOURCES.json','docs/MATERIAL_SOURCES.json','docs/EXTERIOR_EVIDENCE.json','assets/textures/window_banks.json','assets/textures/exterior_sculpture/reliefs.json','assets/textures/east_bank_candidates.json','docs/EAST_GLAZING_ADDITIONS.json'] if (R/p).exists()},'used_photo_textures':items,'glb':{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size,'stable_during_read':stable,'image_count':len(image_rows),'material_count':len(g.get('materials',[])),'photo_image_count':sum(x['classification']=='licensed_photo_derivative' for x in image_rows),'images':image_rows,'final_v8_derivatives_embedded':v8_embedded},'official_reference_exclusion':{'known_reference_image_hashes_checked':len(official),'embedded_reference_byte_matches':collisions,'ingredient_set':f"{len(image_rows)} embedded images; {sum(x['classification']=='licensed_photo_derivative' for x in image_rows)} photo-derived and {sum(x['classification']=='authored_procedural' for x in image_rows)} procedural. Every image is compared to known source/derivative bytes or decoded pixels; roughness packing is checked channel by channel.",'conclusion':'No official reference image identified among GLB ingredients.' if not collisions else 'ERROR reference image embedded'},'user_attribution':{'path':'web/dist/credits.html','photo_credits':credit_checks,'v8_changes_included':credits_v8,'access':'UI 資料と出典 opens credits.html; split bundle copies same credit file, verified separately by runtime agent.'},'issues':issues,'limits':['Whole official reference folder is absent from runtime ingredient manifest; this audit separately verifies exact embedded image content.','Final static split-package credits hash must be checked after packaging.','Source documents distinguish original photographer licenses from Joan Vila-Grau, Etsuro Sotoo, Jaume Busquets and Josep Maria Subirachs underlying artwork. Existing local-review scope retained.']}
(R/'docs/FINAL_SOURCE_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'images':len(image_rows),'photos':report['glb']['photo_image_count'],'source_rows':len(items),'issues':issues},ensure_ascii=False))
