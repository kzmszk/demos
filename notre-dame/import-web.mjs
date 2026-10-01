#!/usr/bin/env node
/** Import a verified standalone Godot static package. Never publishes source/QA files. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const source=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw Error('Usage: node notre-dame/import-web.mjs /absolute/path/to/site_bundle');
const manifest=JSON.parse(fs.readFileSync(path.join(source,'package_manifest.json'),'utf8'));
if(manifest.application!=='notre-dame-static-package'||manifest.format_version!==1)throw Error('Unrecognized source package');
const out=path.join(root,'public');
const recordPath=path.join(root,'SOURCE.json');
if(fs.existsSync(out)&&(!fs.existsSync(recordPath)||JSON.parse(fs.readFileSync(recordPath)).application!=='demos-notre-dame'))throw Error('Refusing to replace unowned public/');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const files=[];
for(const entry of manifest.files){
 if(entry.file==='README.md')continue;
 if(entry.file.startsWith('/')||entry.file.split('/').some(p=>p==='..'||p.startsWith('.')))throw Error('Unsafe package path');
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
 const outputFiles=files.map(f=>{const b=fs.readFileSync(path.join(temp,f.name));return {path:f.name,bytes:b.length,sha256:sha(b)};});
 if(fs.existsSync(out))fs.rmSync(out,{recursive:true});
 fs.renameSync(temp,out);
 const record={application:'demos-notre-dame',source_package_id:manifest.package_id,source_bundle:source,source_manifest_sha256:sha(fs.readFileSync(path.join(source,'package_manifest.json'))),source_browser_validated:manifest.browser_tested===true,imported_at:new Date().toISOString(),local_adaptations:['DEMOS gallery return link','QA UI enabled only on loopback hostname'],file_count:outputFiles.length,total_bytes:outputFiles.reduce((n,f)=>n+f.bytes,0),max_file_bytes:Math.max(...outputFiles.map(f=>f.bytes)),files:outputFiles};
 fs.writeFileSync(recordPath,JSON.stringify(record,null,2)+'\n');
 console.log(JSON.stringify({package:record.source_package_id,files:record.file_count,total_bytes:record.total_bytes,max_file_bytes:record.max_file_bytes}));
}finally{if(fs.existsSync(temp))fs.rmSync(temp,{recursive:true});}
