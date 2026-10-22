// Deterministic real-GPU browser capture, following kyoto/tools/film.mjs.
// node alhambra/tools/film/render.mjs [scout|render] [/tmp/alhambra-film]
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import http from 'node:http';
import {spawn,execFileSync} from 'node:child_process';
const mode=process.argv[2]||'scout',out=process.argv[3]||'/tmp/alhambra-film';
const root=path.resolve(import.meta.dirname,'../../public'),W=1280,H=720,FPS=24;
const shots=['overview','justice','alcazaba','vela','carlos','mexuar','myrtles','ambassadors','lions','kings','abencerrajes','sisters','lindaraja','partal','generalife'];
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(path.join(out,'frames'),{recursive:true});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const server=http.createServer((req,res)=>{const url=new URL(req.url,'http://x');let p=decodeURIComponent(url.pathname);if(p.endsWith('/'))p+='index.html';const f=path.resolve(root,'.'+p);if(!f.startsWith(root+'/')||!fs.existsSync(f)){res.writeHead(404).end();return;}const type={'.html':'text/html','.js':'text/javascript','.json':'application/json','.jpg':'image/jpeg','.mp3':'audio/mpeg'}[path.extname(f)]||'application/octet-stream';res.writeHead(200,{'Content-Type':type});fs.createReadStream(f).pipe(res);});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'alh-film-'));
const chrome=spawn('google-chrome',['--headless=new','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--no-first-run','--hide-scrollbars','--mute-audio',`--window-size=${W},${H}`,'--use-gl=angle','--use-angle=gl-egl','--ignore-gpu-blocklist','--enable-gpu','about:blank'],{stdio:'ignore'});
let ws;
try{
 const pf=path.join(profile,'DevToolsActivePort');for(let i=0;i<100&&!fs.existsSync(pf);i++)await sleep(100);
 const port=fs.readFileSync(pf,'utf8').split('\n')[0];const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 let seq=0;const pending=new Map();const errors=[];
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){const [r,j]=pending.get(m.id);pending.delete(m.id);m.error?j(Error(m.error.message)):r(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails);};
 const send=(method,params={})=>new Promise((r,j)=>{const id=++seq;pending.set(id,[r,j]);ws.send(JSON.stringify({id,method,params}));});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value;};
 await send('Page.enable');await send('Runtime.enable');await send('Emulation.setDeviceMetricsOverride',{width:W,height:H,deviceScaleFactor:1,mobile:false});
 await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/?film=1&q=high&place=overview#ja`});
 const start=Date.now();while(!await ev('window.ALH?.ready')){if(Date.now()-start>120000)throw Error('Scene load timeout');await sleep(300);}
 await ev(`document.getElementById('musicTrack').pause();document.body.classList.add('hide-ui');document.getElementById('loading')?.remove();
 const style=document.createElement('style');style.textContent='#restoreUI,#toast{display:none!important} #filmCaption{position:fixed;inset:0;pointer-events:none;background:linear-gradient(transparent 62%,rgba(6,17,16,.7));color:#fff7e8;font-family:serif} #filmCaption .place{position:absolute;left:48px;bottom:48px;display:block;border:0;padding:0;color:inherit} #filmJa{font-size:36px;letter-spacing:.07em;text-shadow:0 2px 12px #000} #filmEn{font:16px sans-serif;letter-spacing:.14em;margin-top:9px;color:#e7dcc6} #filmBrand{position:absolute;top:35px;left:48px;font-size:23px;letter-spacing:.27em;text-shadow:0 1px 8px #000} #filmCount{position:absolute;bottom:48px;right:48px;font:14px sans-serif;letter-spacing:.14em}';document.head.append(style);
 const panel=document.createElement('div');panel.id='filmCaption';panel.innerHTML='<div id="filmBrand">ALHAMBRA</div><div class="place"><div id="filmJa"></div><div id="filmEn"></div></div><div id="filmCount"></div>';document.body.append(panel);`);
 const manifest=[];
 for(const [n,id] of shots.entries()){
   const count=mode==='scout'?3:4*FPS;
   for(let i=0;i<count;i++){
     const u=mode==='scout'?i/2:i/(count-1),t=n*4+u*4;
     const labels=await ev(`(()=>{const p=ALH.filmFrame('${id}',${u},${t});document.getElementById('filmJa').textContent=p.ja;document.getElementById('filmEn').textContent=p.en;document.getElementById('filmCount').textContent='${String(n+1).padStart(2,'0')} / 15';return p;})()`);
     const shot=await send('Page.captureScreenshot',{format:'jpeg',quality:92});
     const name=mode==='scout'?`${String(n).padStart(2,'0')}-${id}-${i}.jpg`:`frames/${String(n*4*FPS+i).padStart(5,'0')}.jpg`;
     fs.writeFileSync(path.join(out,name),Buffer.from(shot.data,'base64'));
     if(i===0)manifest.push({id,start:n*4,duration:4,...labels});
   }
   console.log(`${mode} ${n+1}/15 ${id}`);
 }
 fs.writeFileSync(path.join(out,'shots.json'),JSON.stringify(manifest,null,2));
 if(errors.length)throw Error(JSON.stringify(errors));
}finally{ws?.close();chrome.kill();server.close();try{fs.rmSync(profile,{recursive:true,force:true});}catch{}}
if(mode==='render'){
 const movie=path.join(root,'movie/alhambra.mp4');
 execFileSync('ffmpeg',['-hide_banner','-loglevel','warning','-y','-framerate',String(FPS),'-i',path.join(out,'frames/%05d.jpg'),'-i',path.join(root,'audio/asturias-full.mp3'),'-t','60','-vf','fade=t=in:st=0:d=0.5,fade=t=out:st=59:d=1','-af','afade=t=in:st=0:d=0.5,afade=t=out:st=57:d=3','-c:v','libx264','-preset','slow','-crf','24','-maxrate','2200k','-bufsize','4400k','-pix_fmt','yuv420p','-profile:v','high','-level','3.1','-c:a','aac','-b:a','128k','-ar','48000','-movflags','+faststart',movie],{stdio:'inherit'});
 execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-ss','25','-i',movie,'-frames:v','1',path.join(root,'movie/poster.jpg')]);
 console.log(`Wrote ${movie} (${(fs.statSync(movie).size/1e6).toFixed(1)} MB)`);
}
