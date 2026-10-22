#!/usr/bin/env node
/** Restore the published, hash-pinned Web export without running Blender or Godot. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const defaultRoot=path.dirname(fileURLToPath(import.meta.url));
export const publicUrl='https://demos.polynous.io/sagrada-familia/';
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');

function sourceRecord(root) {
 const record=JSON.parse(fs.readFileSync(path.join(root,'SOURCE.json'),'utf8'));
 if(record.application!=='demos-sagrada-familia'||!Array.isArray(record.files)||!record.files.length)
  throw Error('Invalid Sagrada Família SOURCE.json');
 const names=new Set();
 for(const file of record.files) {
  if(typeof file.path!=='string'||file.path.includes('\\')||file.path.startsWith('/')||
     file.path.split('/').some(part=>!part||part.startsWith('.'))||names.has(file.path)||
     !Number.isSafeInteger(file.bytes)||file.bytes<0||file.bytes>20*1024*1024||
     !/^[a-f0-9]{64}$/.test(file.sha256))throw Error('Invalid file record in SOURCE.json');
  names.add(file.path);
 }
 if(!names.has('index.html'))throw Error('SOURCE.json has no entry HTML');
 return record;
}

function inventory(directory,prefix='') {
 const files=[];
 for(const entry of fs.readdirSync(directory,{withFileTypes:true})) {
  const name=prefix+entry.name;
  if(entry.isDirectory())files.push(...inventory(path.join(directory,entry.name),name+'/'));
  else if(entry.isFile())files.push(name);
  else throw Error('Unexpected file type in Web export: '+name);
 }
 return files.sort();
}

export function verifyPublic({root=defaultRoot,directory=path.join(root,'public')}={}) {
 const record=sourceRecord(root);
 if(!fs.existsSync(directory))throw Error('Sagrada Família public/ is missing; run node sagrada-familia/restore-web.mjs');
 const expected=record.files.map(file=>file.path).sort();
 if(JSON.stringify(inventory(directory))!==JSON.stringify(expected))
  throw Error('Sagrada Família public/ file inventory differs from SOURCE.json');
 for(const file of record.files) {
  const data=fs.readFileSync(path.join(directory,file.path));
  if(data.length!==file.bytes||sha(data)!==file.sha256)
   throw Error('Sagrada Família public/ hash mismatch: '+file.path);
 }
 return {package:record.source_package_id,files:record.files.length,total_bytes:record.files.reduce((sum,file)=>sum+file.bytes,0)};
}

export async function restoreWeb({root=defaultRoot,baseUrl=publicUrl,fetchImpl=fetch,log=console.log}={}) {
 const out=path.join(root,'public');
 if(fs.existsSync(out))return {...verifyPublic({root}),restored:false};
 const record=sourceRecord(root);
 const stage=fs.mkdtempSync(path.join(root,'.restore-web-'));
 let next=0,completed=0;
 try {
  log(`Restoring Sagrada Família from ${baseUrl} (${record.total_bytes} bytes); Blender/Godot are not needed.`);
  const results=await Promise.allSettled(Array.from({length:4},async()=>{
   while(next<record.files.length) {
    const file=record.files[next++];
    const response=await fetchImpl(new URL(file.path,baseUrl),{
     headers:{'Accept-Encoding':'identity'},signal:AbortSignal.timeout(30_000),
    });
    if(!response.ok)throw Error(`Cannot restore ${file.path}: HTTP ${response.status}`);
    const data=Buffer.from(await response.arrayBuffer());
    if(data.length!==file.bytes||sha(data)!==file.sha256)
     throw Error('Published file differs from SOURCE.json: '+file.path+'; import a verified source package instead.');
    const target=path.join(stage,file.path);
    fs.mkdirSync(path.dirname(target),{recursive:true});
    fs.writeFileSync(target,data);
    completed++;
    if(completed%8===0||completed===record.files.length)log(`Restored ${completed}/${record.files.length} files.`);
   }
  }));
  const failed=results.find(result=>result.status==='rejected');
  if(failed)throw failed.reason;
  const summary=verifyPublic({root,directory:stage});
  fs.renameSync(stage,out);
  return {...summary,restored:true};
 }finally{
  fs.rmSync(stage,{recursive:true,force:true});
 }
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.slice(2).some(arg=>arg!=='--check'))throw Error('Usage: node sagrada-familia/restore-web.mjs [--check]');
  const summary=process.argv.includes('--check')?verifyPublic():await restoreWeb();
  console.log(JSON.stringify(summary));
 }catch(error){console.error(error.message);process.exitCode=1;}
}
