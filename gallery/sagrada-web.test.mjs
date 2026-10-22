import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {importWebBundle} from '../sagrada-familia/import-web.mjs';
import {restoreWeb,verifyPublic} from '../sagrada-familia/restore-web.mjs';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../sagrada-familia');
const packageId='0123456789abcdef0123';
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
const legacyStatus='現在は非公開のローカルレビューで、demosへのコピー・公開・pushはしていません。';

function fixture(t,{modern=false}={}) {
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'sagrada-web-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 fs.mkdirSync(path.join(root,'legal'));
 fs.copyFileSync(path.join(project,'legal/Godot-COPYRIGHT.txt'),path.join(root,'legal/Godot-COPYRIGHT.txt'));
 const source=path.join(root,'bundle');
 const assets=`assets/${packageId}/`;
 const data=new Map([
  ['index.html',Buffer.from('<!doctype html><a href="credits.html">資料と出典</a><script>const qaMode=new URLSearchParams(location.search).has("qa");</script>')],
  [assets+'credits.html',Buffer.from('<a href="godot_license.txt">Godotライセンス</a>'+(modern?'<a href="godot_copyright.txt">Godot第三者著作権表記</a>':legacyStatus))],
  [assets+'index.pck.sample.part00',Buffer.from('unchanged model data')],
  ['README.md',Buffer.from('package instructions')],
 ]);
 for(const [name,bytes] of data) {
  const target=path.join(source,name);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,bytes);
 }
 const manifest={application:'sagrada-familia-static-package',format_version:1,package_id:packageId,browser_tested:true,
  files:[...data].map(([file,bytes])=>({file,bytes:bytes.length,sha256:sha(bytes)}))};
 const saveManifest=()=>fs.writeFileSync(path.join(source,'package_manifest.json'),JSON.stringify(manifest));
 saveManifest();
 return {root,source,assets,data,manifest,saveManifest};
}

test('the original validated package keeps its model bytes and receives gallery/QA/license adaptations',t=>{
 const f=fixture(t);
 const record=importWebBundle(f.source,{root:f.root});
 const out=path.join(f.root,'public');
 assert.equal(record.source_browser_validated,true);
 assert.equal(fs.existsSync(path.join(out,'README.md')),false);
 assert.deepEqual(fs.readFileSync(path.join(out,f.assets+'index.pck.sample.part00')),f.data.get(f.assets+'index.pck.sample.part00'));
 const html=fs.readFileSync(path.join(out,'index.html'),'utf8');
 assert.match(html,/aria-label="DEMOS作品一覧に戻る"/);
 assert.match(html,/\['127\.0\.0\.1','localhost'\]\.includes\(location\.hostname\)/);
 const credits=fs.readFileSync(path.join(out,f.assets+'credits.html'),'utf8');
 assert.equal(credits.includes(legacyStatus),false);
 assert.match(credits,/legal\/Godot-COPYRIGHT\.txt/);
 assert.equal(verifyPublic({root:f.root}).files,record.files.length);
});

test('credits generated from the committed source import without the obsolete status sentence or a duplicate license link',t=>{
 const f=fixture(t,{modern:true});
 fs.writeFileSync(path.join(f.root,'demo.json'),JSON.stringify({links:[{label:'見学',href:'index.html'},{label:'資料',href:'assets/ffffffffffffffffffff/credits.html'}]}));
 importWebBundle(f.source,{root:f.root});
 const credits=fs.readFileSync(path.join(f.root,'public',f.assets+'credits.html'),'utf8');
 assert.equal(credits,f.data.get(f.assets+'credits.html').toString());
 const demo=JSON.parse(fs.readFileSync(path.join(f.root,'demo.json')));
 assert.equal(demo.links[0].href,'index.html');
 assert.equal(demo.links[1].href,f.assets+'credits.html');
});

test('an untested package or damaged input cannot replace an existing public export',t=>{
 const f=fixture(t);
 importWebBundle(f.source,{root:f.root});
 const before=fs.readFileSync(path.join(f.root,'SOURCE.json'));
 f.manifest.browser_tested=false;f.saveManifest();
 assert.throws(()=>importWebBundle(f.source,{root:f.root}),/has not passed browser validation/);
 f.manifest.browser_tested=true;f.saveManifest();
 fs.appendFileSync(path.join(f.source,f.assets+'index.pck.sample.part00'),'damaged');
 assert.throws(()=>importWebBundle(f.source,{root:f.root}),/Source hash mismatch/);
 assert.deepEqual(fs.readFileSync(path.join(f.root,'SOURCE.json')),before);
 verifyPublic({root:f.root});
});

test('a fresh checkout restores the exact recorded export and subsequent builds work offline',async t=>{
 const f=fixture(t);
 const record=importWebBundle(f.source,{root:f.root});
 const data=new Map(record.files.map(file=>[file.path,fs.readFileSync(path.join(f.root,'public',file.path))]));
 fs.rmSync(path.join(f.root,'public'),{recursive:true});
 let requests=0;
 const options={root:f.root,baseUrl:'https://example.test/sagrada-familia/',log:()=>{},fetchImpl:async url=>{
  requests++;
  const name=decodeURIComponent(url.pathname.slice('/sagrada-familia/'.length));
  assert.ok(data.has(name));
  return new Response(data.get(name));
 }};
 const restored=await restoreWeb(options);
 assert.equal(restored.restored,true);
 assert.equal(requests,record.files.length);
 verifyPublic({root:f.root});
 const cached=await restoreWeb({...options,fetchImpl:()=>{throw Error('must work offline');}});
 assert.equal(cached.restored,false);
});

test('a changed published file fails verification and leaves no partial public directory',async t=>{
 const f=fixture(t);
 importWebBundle(f.source,{root:f.root});
 fs.rmSync(path.join(f.root,'public'),{recursive:true});
 await assert.rejects(restoreWeb({root:f.root,log:()=>{},fetchImpl:async()=>new Response('different release')}),/differs from SOURCE.json/);
 assert.equal(fs.existsSync(path.join(f.root,'public')),false);
 assert.equal(fs.readdirSync(f.root).some(name=>name.startsWith('.restore-web-')),false);
});

test('an existing export with an extra private file is rejected without downloads or replacement',async t=>{
 const f=fixture(t);
 importWebBundle(f.source,{root:f.root});
 const extra=path.join(f.root,'public','private-qa.json');
 fs.writeFileSync(extra,'local diagnostics');
 await assert.rejects(restoreWeb({root:f.root,fetchImpl:()=>{throw Error('must not download');}}),/inventory differs/);
 assert.equal(fs.readFileSync(extra,'utf8'),'local diagnostics');
});
