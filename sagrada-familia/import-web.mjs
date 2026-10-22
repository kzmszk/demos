#!/usr/bin/env node
/** Import a verified standalone Godot static package. Never publishes source/QA files. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const defaultRoot=path.dirname(fileURLToPath(import.meta.url));

export function importWebBundle(source,{root=defaultRoot}={}) {
if(!source)throw Error('Usage: node sagrada-familia/import-web.mjs /absolute/path/to/site_bundle');
source=path.resolve(source);
const manifest=JSON.parse(fs.readFileSync(path.join(source,'package_manifest.json'),'utf8'));
if(manifest.application!=='sagrada-familia-static-package'||manifest.format_version!==1)throw Error('Unrecognized source package');
if(manifest.browser_tested!==true)throw Error('Source package has not passed browser validation');
if(!/^[a-f0-9]{20}$/.test(manifest.package_id))throw Error('Invalid source package ID');
const out=path.join(root,'public');
const recordPath=path.join(root,'SOURCE.json');
if(fs.existsSync(out)&&(!fs.existsSync(recordPath)||JSON.parse(fs.readFileSync(recordPath)).application!=='demos-sagrada-familia'))throw Error('Refusing to replace unowned public/');
const demoPath=path.join(root,'demo.json');
const demo=fs.existsSync(demoPath)?JSON.parse(fs.readFileSync(demoPath,'utf8')):null;
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const files=[];
const adaptations=['DEMOS gallery return link','QA UI enabled only on loopback hostname','Godot 4.7.2 third-party copyright notice linked from Credits','Outdated local-only publication status updated; artwork rights notices retained'];
for(const entry of manifest.files){
 if(entry.file==='README.md')continue;
 if(typeof entry.file!=='string'||entry.file.includes('\\')||entry.file.startsWith('/')||entry.file.split('/').some(p=>!p||p.startsWith('.')))throw Error('Unsafe package path');
 const input=path.join(source,entry.file);
 if(fs.lstatSync(input).isSymbolicLink())throw Error('Unexpected symlink');
 const data=fs.readFileSync(input);
 if(data.length!==entry.bytes||sha(data)!==entry.sha256)throw Error('Source hash mismatch: '+entry.file);
 if(data.length>20*1024*1024)throw Error('Asset exceeds20MiB');
 files.push({name:entry.file,data});
}
const temp=fs.mkdtempSync(path.join(root,'.import-'));
try{
 for(const f of files){const target=path.join(temp,f.name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,f.data);}
 const index=path.join(temp,'index.html');let html=fs.readFileSync(index,'utf8');
 const marker='<a href="credits.html"';
 if(!html.includes(marker))throw Error('Credits link not found');
 html=html.replace(marker,'<a href="/" style="color:#b9ae99;padding:8px;font-size:12px" aria-label="DEMOS作品一覧に戻る">← DEMOS</a>'+marker);
 // Local-only diagnostics never POST device telemetry on the public gallery.
 html=html.replace(/const qaMode=([^;]+);/,"const qaMode=['127.0.0.1','localhost'].includes(location.hostname)&&new URLSearchParams(location.search).get('qa')==='1';");
 if(!html.includes("const qaMode=['127.0.0.1'"))throw Error('QA-mode guard missing');
 fs.writeFileSync(index,html);
 const creditFile='assets/'+manifest.package_id+'/credits.html';
 const creditPath=path.join(temp,creditFile);
 let credits=fs.readFileSync(creditPath,'utf8');
 const licenseLink='<a href="godot_license.txt">Godotライセンス</a>';
 if(!credits.includes(licenseLink))throw Error('Godot credits anchor missing');
 // Current source builds already link their bundled notice; the original V12 needs it added.
 if(!credits.includes('href="godot_copyright.txt"')&&!credits.includes('href="legal/Godot-COPYRIGHT.txt"'))
  credits=credits.replace(licenseLink,licenseLink+' · <a href="legal/Godot-COPYRIGHT.txt">Godot依存ライブラリの著作権・ライセンス通知</a>');
 const oldStatus='現在は非公開のローカルレビューで、demosへのコピー・公開・pushはしていません。';
 // Preserve the published V12 output, while accepting credits regenerated from current source.
 credits=credits.replace(oldStatus,'V12はレビュー後、ユーザーの依頼によりDEMOSギャラリーへ公開しています。Git pushは行っていません。');
 credits=credits.replaceAll('no external publication is authorized in this task.', 'the user authorized this DEMOS gallery publication, which does not add or imply a waiver of the underlying artwork rights.');
 for(const [before,after] of [["この作品は資料照合を重ねたローカルレビュー用の建築再構成です。", "この作品は資料照合を重ねた独立した建築再構成です。"], ["no external publication authorized in this task.", "project-level publication approval does not waive separate artwork rights."], ["current task is local review and no publication has occurred.", "this public edition retains that distinction."], ["No external publication performed.", "No external publication had been performed when this source record was prepared."], ["Final local-review candidate: four east and three west real window patterns; photo-guided capitals and star wells; weathered historic Nativity stone; known refinements integrated pending final scene/browser checks", "V12 public review release: four east and three west real window patterns; photo-guided capitals and star wells; weathered historic Nativity stone; completed checks and remaining limitations are recorded in the accompanying validation documents"]]) credits=credits.replaceAll(before,after);
 fs.writeFileSync(creditPath,credits);
 const copyright=fs.readFileSync(path.join(root,'legal','Godot-COPYRIGHT.txt'));
 if(sha(copyright)!=='cb1980c88089573bcacd7221d777c689bb8bbd778799f24c27fca0fe5f774d6d')throw Error('Unexpected Godot copyright notice');
 const legalName='assets/'+manifest.package_id+'/legal/Godot-COPYRIGHT.txt';
 fs.mkdirSync(path.dirname(path.join(temp,legalName)),{recursive:true});
 fs.writeFileSync(path.join(temp,legalName),copyright);
 files.push({name:legalName,data:copyright});
 const outputFiles=files.map(f=>{const b=fs.readFileSync(path.join(temp,f.name));return {path:f.name,bytes:b.length,sha256:sha(b)};});
 if(fs.existsSync(out))fs.rmSync(out,{recursive:true});
 fs.renameSync(temp,out);
 const record={application:'demos-sagrada-familia',source_package_id:manifest.package_id,source_bundle:source,source_manifest_sha256:sha(fs.readFileSync(path.join(source,'package_manifest.json'))),source_browser_validated:manifest.browser_tested===true,imported_at:new Date().toISOString(),local_adaptations:adaptations,file_count:outputFiles.length,total_bytes:outputFiles.reduce((n,f)=>n+f.bytes,0),max_file_bytes:Math.max(...outputFiles.map(f=>f.bytes)),files:outputFiles};
 fs.writeFileSync(recordPath,JSON.stringify(record,null,2)+'\n');
 if(Array.isArray(demo?.links)) {
  for(const link of demo.links)if(/^assets\/[a-f0-9]{20}\/credits\.html$/.test(link.href))link.href=creditFile;
  fs.writeFileSync(demoPath,JSON.stringify(demo,null,2)+'\n');
 }
 return record;
}finally{if(fs.existsSync(temp))fs.rmSync(temp,{recursive:true});}
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  const record=importWebBundle(process.argv[2]);
  console.log(JSON.stringify({package:record.source_package_id,files:record.file_count,total_bytes:record.total_bytes,max_file_bytes:record.max_file_bytes}));
 }catch(error){console.error(error.message);process.exitCode=1;}
}
