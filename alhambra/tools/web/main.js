import {extendedMaterials} from './extended-materials.js';
import {landscapeDetails, palaceDetails} from './landscape-detail.js';
import {detailMaterials,interiorShading} from './detail-materials.js';
import * as THREE from 'three';
import { CSM } from 'three/addons/csm/CSM.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { materials, random } from './materials.js';
import { Builder } from './geometry.js';
import { Navigation, EYE, terrainHeight } from './navigation.js';
import { nasrid, gardens, charlesV } from './palaces.js';
import { fortress, exterior } from './exterior.js';
import { PLACES, BY_ID, TOUR } from './places.js';
import { buildTourShots, sampleTourShot } from './tour.js';
import { createMusic } from './music.js';
import { createReferences } from './references.js';

const $=id=>document.getElementById(id),query=new URLSearchParams(location.search);
let lang=location.hash==='#en'?'en':'ja',mode='walk',place=BY_ID[query.get('place')]||BY_ID.lions;
const touch=matchMedia('(pointer: coarse)').matches;
const low=query.get('q')==='low'||(query.get('q')!=='high'&&touch);
const filming=query.get('film')==='1';
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
document.body.dataset.touch=String(touch);document.body.dataset.mode=mode;
let renderer,scene,camera,csm,nav,world,sky,sun,materialsMap,waterObjects=[],reflectors=[],hemi;
let yaw=0,pitch=0,orbitTarget=new THREE.Vector3(80,0,30),orb=new THREE.Spherical(520,1.08,-.8);
let tour=false,tourTime=0,tourIndex=0,tourStart=0,tourOrigin=0,day=1,now=0,last=performance.now(),mapFrame=0,audio=null;
const keys=new Set(),stick={x:0,y:0},alt={value:0};let pointer=null;
const clamp=THREE.MathUtils.clamp;
let toastTimer,references,tourShots;
const music=createMusic({getLanguage:()=>lang,toast});
function toast(ja,en){$('toast').textContent=lang==='ja'?ja:en;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2600);}
function caption(p){place=p;$('placeNumber').textContent=p.no;$('placeTitle').textContent=p[lang];$('referenceOpen').setAttribute('aria-label',lang==='ja'?`${p.ja}の実際の写真を見る`:`View real photographs of ${p.en}`);$('placeSpanish').textContent=p.es;$('placeDescription').textContent=p.desc[lang];for(const button of document.querySelectorAll('.place')){const active=button.dataset.id===p.id;button.classList.toggle('active',active);button.setAttribute('aria-current',active?'location':'false');}}
function localize(){
  document.documentElement.lang=lang;document.title=lang==='ja'?'ALHAMBRA · 水と光の宮殿':'ALHAMBRA · A palace of water and light';
  for(const e of document.querySelectorAll('[data-ja]'))e.textContent=e.dataset[lang];
  $('language').textContent=lang==='ja'?'EN':'JA';$('language').setAttribute('aria-label',lang==='ja'?'Switch to English':'日本語に切り替える');
  const labels={musicToggle:['音楽','Music'],musicClose:['音楽パネルを閉じる','Close music panel'],scene:['アルハンブラ宮殿の3D風景','3D view of the Alhambra'],sound:['水の環境音','Water ambience'],helpButton:['操作方法','Controls'],mapToggle:['地図を拡大','Expand map'],map:['現在地と宮殿全体の案内図','Map of the grounds and your location'],uiToggle:['UIを隠す','Hide interface'],restoreUI:['UIを表示','Show interface'],rise:['上昇','Ascend'],descend:['下降','Descend']};
  for(const [id,names] of Object.entries(labels))$(id).setAttribute('aria-label',names[lang==='ja'?0:1]);
  document.querySelector('.back').setAttribute('aria-label',lang==='ja'?'ギャラリーに戻る':'Return to gallery');
  document.querySelector('.modes').setAttribute('aria-label',lang==='ja'?'移動方法':'Travel mode');
  document.querySelector('#help .close').setAttribute('aria-label',lang==='ja'?'閉じる':'Close');
  const groupNames={nasrid:['ナスル朝宮殿','Nasrid palaces'],fortress:['アルカサバ','The Alcazaba'],gardens:['水と庭園','Water & gardens'],grounds:['宮殿と敷地','Palace & grounds']};
  $('placeList').replaceChildren();let group='';
  for(const p of PLACES){if(p.group!==group){group=p.group;const label=document.createElement('div');label.className='place-group';label.textContent=groupNames[group][lang==='ja'?0:1];$('placeList').append(label);}const button=document.createElement('button');button.className='place';button.dataset.id=p.id;button.innerHTML=`<span class="num">${p.no}</span><span>${p[lang]}</span>`;button.addEventListener('click',()=>{stopTour();go(p.id);closePlaces();});$('placeList').append(button);}
  caption(place);references?.localize();music.localize();updateButtons();drawMap();
}
function closePlaces(){document.body.classList.remove('places-open');$('placesToggle').setAttribute('aria-expanded','false');}
function updateButtons(){
  for(const m of ['walk','fly','orbit']){$(m).classList.toggle('active',mode===m);$(m).setAttribute('aria-pressed',String(mode===m));}
  $('quality').textContent=lang==='ja'?(low?'軽量':'高画質'):(low?'Light':'High detail');
  $('tour').textContent=tour?(lang==='ja'?'Ⅱ 案内を停止':'Ⅱ Pause visit'):(lang==='ja'?'▷ 自動案内':'▷ Guided visit');$('tour').setAttribute('aria-pressed',String(tour));
  $('light').textContent=day?(lang==='ja'?'☼ 夕暮れ':'☼ Golden hour'):(lang==='ja'?'☼ 午後':'☼ Afternoon');
  $('controlHint').textContent=mode==='orbit'?(lang==='ja'?'ドラッグで回転 · ホイールで拡大':'Drag to orbit · Scroll to zoom'):mode==='fly'?(lang==='ja'?'W A S D 移動 · Q E 上下 · ドラッグで見回す':'W A S D move · Q E up / down · Drag to look'):(lang==='ja'?'W A S D 移動 · ドラッグで見回す':'W A S D move · Drag to look');
  document.body.dataset.mode=mode;document.body.classList.toggle('touring',tour);
}
function orientation(){camera.rotation.order='YXZ';yaw=camera.rotation.y;pitch=camera.rotation.x;}
function setMode(next){
  stopTour();if(next==='orbit'){go('overview');return;}
  if(next==='walk'&&mode!=='walk'){
    const floor=nav.height(camera.position.x,camera.position.z,camera.position.y-EYE);
    if(camera.position.y-floor>6||nav.blocked(camera.position.x,camera.position.z,floor)){const p=place.id==='overview'?BY_ID.lions:place;camera.position.fromArray(p.p);camera.lookAt(...p.t);caption(p);}else camera.position.y=floor+EYE;
  }
  mode=next;orientation();updateButtons();
}
function go(id,fromTour=false){
  const p=BY_ID[id];if(!p||!camera)return false;
  if(!fromTour)stopTour();caption(p);camera.position.fromArray(p.p);camera.lookAt(...p.t);orientation();mode=p.mode||'walk';
  if(mode==='orbit'){orbitTarget.set(...p.t);orb.setFromVector3(camera.position.clone().sub(orbitTarget));}
  keys.clear();stick.x=stick.y=0;updateButtons();
  const u=new URL(location.href);u.searchParams.set('place',p.id);u.hash=lang;history.replaceState(null,'',u);drawMap();return true;
}
function startTour(){tour=true;tourTime=0;tourStart=performance.now();tourOrigin=tourIndex=Math.max(0,TOUR.indexOf(place.id));closePlaces();go(TOUR[tourIndex],true);updateButtons();toast('全15地点を1分で巡ります。操作すると停止します。','All 15 highlights in one minute. Interact to stop.');}
function stopTour(){if(!tour)return;tour=false;updateButtons();}
function setLight(){
  const az=day?[-.8,.32,.5]:[-.7,.95,.5];sun=new THREE.Vector3(...az).normalize();
  csm.lightDirection.copy(sun).negate();csm.lightIntensity=day?3.5:3.3;
  for(const l of csm.lights){l.color.set(day?0xffdab0:0xffefdc);l.intensity=csm.lightIntensity;}
  sky.material.uniforms.sunPosition.value.copy(sun);sky.material.uniforms.turbidity.value=day?3.5:3;
  hemi.intensity=day?.88:1.45;hemi.color.set(day?0xb8d0ee:0xd7e9f1);hemi.groundColor.set(day?0x8d7a62:0xb4a58a);scene.fog.color.set(day?0xd8cabc:0xcbd4ce);renderer.toneMappingExposure=day?1.08:1.07;updateButtons();
}
function drawMap(){
  if(!camera)return;const canvas=$('map'),g=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
  const xy=(x,z)=>[(x+305)/780*W,(z+140)/500*H];g.clearRect(0,0,W,H);
  if(world?.context?.perimeter){g.beginPath();world.context.perimeter.forEach(([x,z],i)=>{const p=xy(x,z);i?g.lineTo(...p):g.moveTo(...p);});g.closePath();g.fillStyle='#d5c7ac';g.fill();g.strokeStyle='#947654';g.lineWidth=2;g.stroke();}
  g.fillStyle='#aab49b';g.fillRect(...xy(326,-108),95/780*W,213/500*H);
  for(const [x,z,w,d,c] of [[-239,12,100,33,'#b99d7a'],[-71.5,33.5,63,63,'#bca58b'],[-34,-40,100,80,'#bdac91'],[78,-20,110,96,'#b1b799']]){const p=xy(x,z);g.fillStyle=c;g.fillRect(p[0],p[1],w/780*W,d/500*H);}
  g.strokeStyle='#f5f1e6';g.lineWidth=4;g.beginPath();for(const [i,p] of [[-95,50],[65,68],[70,97],[200,97],[200,252],[350,252],[396,218],[396,202],[370,177],[370,-52]].entries()){const v=xy(...p);i?g.lineTo(...v):g.moveTo(...v);}g.stroke();
  const labels=[['alcazaba',lang==='ja'?'アルカサバ':'ALCAZABA',-14,28],['lions',lang==='ja'?'ナスル朝宮殿':'NASRID',25,-20],['generalife',lang==='ja'?'ヘネラリフェ':'GENERALIFE',-35,-22],['partal',lang==='ja'?'パルタル':'PARTAL',23,20]];
  for(const [id,label,dx,dz] of labels){const p=BY_ID[id],v=xy(p.p[0],p.p[2]);g.fillStyle='#4b5c46';g.font='15px system-ui';g.fillText(label,v[0]+dx,v[1]+dz);}
  for(const p of PLACES){if(p.id==='overview')continue;const v=xy(p.p[0],p.p[2]);g.beginPath();g.arc(...v,p.id===place.id?6:3.2,0,Math.PI*2);g.fillStyle=p.id===place.id?'#a56f31':'#77785f';g.fill();}
  const p=xy(camera.position.x,camera.position.z);g.save();g.translate(...p);g.rotate(-yaw);g.fillStyle='#294c42';g.beginPath();g.moveTo(0,-9);g.lineTo(6,6);g.lineTo(0,3);g.lineTo(-6,6);g.closePath();g.fill();g.restore();
  g.fillStyle='#6e7b69';g.font='14px system-ui';g.fillText('N ↑',W-40,22);g.strokeStyle='#7f8973';g.lineWidth=2;g.beginPath();g.moveTo(20,H-18);g.lineTo(20+100/780*W,H-18);g.stroke();g.font='12px system-ui';g.fillText('100 m',20,H-24);
}
function wire(){
  const pauseInput=()=>{stopTour();keys.clear();stick.x=stick.y=0;alt.value=0;pointer=null;$('joystick').firstElementChild.style.transform='';};
  references=createReferences({getPlace:()=>place,getLanguage:()=>lang,onOpen:pauseInput});
  $('referenceOpen').onclick=()=>references.open();
  $('walk').onclick=()=>setMode('walk');$('fly').onclick=()=>setMode('fly');$('orbit').onclick=()=>setMode('orbit');
  $('language').onclick=()=>{lang=lang==='ja'?'en':'ja';history.replaceState(null,'',`${location.pathname}${location.search}#${lang}`);localize();};
  $('tour').onclick=()=>tour?stopTour():startTour();$('light').onclick=()=>{day=1-day;setLight();};
  $('quality').onclick=()=>{const u=new URL(location.href);u.searchParams.set('q',low?'high':'low');location.assign(u);};
  const hide=()=>{document.body.classList.toggle('hide-ui');$('restoreUI').focus();};$('uiToggle').onclick=hide;$('restoreUI').onclick=hide;
  $('helpButton').onclick=()=>{pauseInput();$('help').showModal();};$('help').querySelector('.close').onclick=()=>$('help').close();
  $('placesToggle').onclick=()=>{const visible=document.body.classList.toggle('places-open');$('placesToggle').setAttribute('aria-expanded',String(visible));};
  $('mapToggle').onclick=()=>{const expanded=document.body.classList.toggle('map-expanded');$('mapToggle').setAttribute('aria-expanded',String(expanded));};
  $('map').onclick=e=>{const r=e.currentTarget.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*780-305,z=(e.clientY-r.top)/r.height*500-140;const p=PLACES.filter(p=>p.id!=='overview').sort((a,b)=>Math.hypot(a.p[0]-x,a.p[2]-z)-Math.hypot(b.p[0]-x,b.p[2]-z))[0];if(Math.hypot(p.p[0]-x,p.p[2]-z)<60)go(p.id);};
  const c=$('scene');
  c.addEventListener('pointerdown',e=>{if(e.button!==0)return;stopTour();c.focus();pointer={id:e.pointerId,x:e.clientX,y:e.clientY};c.setPointerCapture(e.pointerId);});
  c.addEventListener('pointermove',e=>{if(!pointer||e.pointerId!==pointer.id)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;pointer.x=e.clientX;pointer.y=e.clientY;if(mode==='orbit'){orb.theta-=dx*.004;orb.phi=clamp(orb.phi+dy*.004,.12,1.55);}else{yaw-=dx*.003;pitch=clamp(pitch-dy*.003,-1.48,1.48);camera.rotation.set(pitch,yaw,0,'YXZ');}});
  for(const ev of ['pointerup','pointercancel','lostpointercapture'])c.addEventListener(ev,()=>{pointer=null;});
  c.addEventListener('wheel',e=>{e.preventDefault();if(mode==='orbit'){stopTour();orb.radius=clamp(orb.radius*Math.exp(e.deltaY*.001),30,1200);}}, {passive:false});
  window.addEventListener('keydown',e=>{
    if($('help').open||$('references').open||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
    const key=e.key.toLowerCase();if(['w','a','s','d','q','e','shift','arrowup','arrowdown','arrowleft','arrowright'].includes(key)){e.preventDefault();stopTour();keys.add(key);}
    if(e.repeat)return;if(key==='m')$('mapToggle').click();if(key==='h')hide();if(key==='escape'){stopTour();closePlaces();document.body.classList.remove('map-expanded');$('mapToggle').setAttribute('aria-expanded','false');}
  });
  window.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));window.addEventListener('blur',()=>{keys.clear();stick.x=stick.y=0;alt.value=0;pointer=null;});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){keys.clear();stick.x=stick.y=0;alt.value=0;}});
  const joy=$('joystick'),knob=joy.firstElementChild;let joyId=null;
  const joystick=e=>{const r=joy.getBoundingClientRect(),x=(e.clientX-r.left-r.width/2)/24,y=(e.clientY-r.top-r.height/2)/24,l=Math.max(1,Math.hypot(x,y));stick.x=x/l;stick.y=y/l;knob.style.transform=`translate(${stick.x*20}px,${stick.y*20}px)`;};
  joy.addEventListener('pointerdown',e=>{e.preventDefault();stopTour();if(mode==='orbit')setMode('walk');joyId=e.pointerId;joy.setPointerCapture(joyId);joystick(e);});joy.addEventListener('pointermove',e=>{if(e.pointerId===joyId)joystick(e);});
  for(const ev of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(ev,()=>{joyId=null;stick.x=stick.y=0;knob.style.transform='';});
  for(const [id,n] of [['rise',1],['descend',-1]]){$(id).onpointerdown=e=>{e.preventDefault();stopTour();alt.value=n;$(id).setPointerCapture(e.pointerId);};for(const ev of ['pointerup','pointercancel','lostpointercapture'])$(id).addEventListener(ev,()=>{alt.value=0;});}
  $('sound').onclick=async()=>{
    try{
      if(!audio){const ac=new AudioContext(),buffer=ac.createBuffer(1,ac.sampleRate*3,ac.sampleRate),r=random(52),data=buffer.getChannelData(0);for(let i=0;i<data.length;i++)data[i]=(r()-.5)*.25;const source=ac.createBufferSource();source.buffer=buffer;source.loop=true;const filter=ac.createBiquadFilter();filter.type='lowpass';filter.frequency.value=1500;const gain=ac.createGain();gain.gain.value=.12;source.connect(filter).connect(gain).connect(ac.destination);source.start();audio={ac,gain,on:true};}else{audio.on=!audio.on;audio.gain.gain.setTargetAtTime(audio.on?.12:0,audio.ac.currentTime,.15);}
      await audio.ac.resume();$('sound').setAttribute('aria-pressed',String(audio.on));toast(audio.on?'水の環境音を再生しています':'環境音を停止しました',audio.on?'Water ambience on':'Sound off');
    }catch{toast('このブラウザーでは音声を開始できません','Audio could not start in this browser');}
  };
  window.addEventListener('resize',resize);
  c.addEventListener('webglcontextlost',e=>{e.preventDefault();fatal(lang==='ja'?'描画が中断されました。軽量モードで再読み込みしてください。':'Graphics interrupted. Reload in light mode.');});
}
function resize(){if(!renderer)return;camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);csm?.updateFrustums();}
function fatal(message){$('loading')?.classList.add('done');const div=document.createElement('div');div.className='fatal';const p=document.createElement('p');p.textContent=message;div.append(p);const a=document.createElement('a');const u=new URL(location.href);u.searchParams.set('q','low');a.href=u;a.textContent=lang==='ja'?'軽量モードで再読み込み':'Reload in light mode';div.append(a);document.body.append(div);}
function update(dt){
  now+=dt;
  if(tour){
    tourTime=(performance.now()-tourStart)/1000;
    const step=Math.min(TOUR.length-1,Math.floor(tourTime/4));
    const index=(tourOrigin+step)%TOUR.length;
    if(index!==tourIndex){tourIndex=index;go(TOUR[tourIndex],true);}
    const p=BY_ID[TOUR[tourIndex]],phase=Math.min(1,(tourTime-step*4)/4);
    if(!reduced){
      if(mode==='orbit'){
        camera.position.fromArray(p.p);
        orb.setFromVector3(camera.position.clone().sub(orbitTarget));
        orb.theta+=phase*.5;orb.radius*=1-phase*.16;orb.phi-=Math.sin(phase*Math.PI/2)*.08;
      }else{
        const shot=sampleTourShot(tourShots[p.id],p,phase);
        camera.position.fromArray(shot.position);camera.lookAt(...shot.target);orientation();
      }
    }
    $('tourProgress').firstElementChild.style.width=`${Math.min(100,tourTime/60*100)}%`;
    if(tourTime>=60)stopTour();
  }
  if(mode==='orbit'){camera.position.setFromSpherical(orb).add(orbitTarget);camera.lookAt(orbitTarget);orientation();}
  else {
    let forward=(keys.has('w')||keys.has('arrowup')?1:0)-(keys.has('s')||keys.has('arrowdown')?1:0)-stick.y;
    let right=(keys.has('d')||keys.has('arrowright')?1:0)-(keys.has('a')||keys.has('arrowleft')?1:0)+stick.x;
    const len=Math.max(1,Math.hypot(forward,right));forward/=len;right/=len;
    const speed=(mode==='walk'?2.3:17)*(keys.has('shift')?2.4:1)*dt;
    const dx=(-Math.sin(yaw)*forward+Math.cos(yaw)*right)*speed,dz=(-Math.cos(yaw)*forward-Math.sin(yaw)*right)*speed;
    if(mode==='walk'){if(dx||dz)nav.move(camera.position,dx,dz);}else{camera.position.x=clamp(camera.position.x+dx,-900,900);camera.position.z=clamp(camera.position.z+dz,-900,900);camera.position.y+=((keys.has('e')?1:0)-(keys.has('q')?1:0)+alt.value)*speed;camera.position.y=clamp(camera.position.y,terrainHeight(camera.position.x,camera.position.z)+.7,850);}
  }
  const nearest=reflectors.reduce((a,r)=>camera.position.distanceToSquared(r.position)<camera.position.distanceToSquared(a.position)?r:a,reflectors[0]);
  for(const r of reflectors)r.visible=r===nearest&&camera.position.distanceTo(r.position)<90&&camera.position.y<r.position.y+55;
  for(const o of waterObjects){if(o.material.userData.shader)o.material.userData.shader.uniforms.uTime.value=now;}
  if(++mapFrame%5===0)drawMap();
  csm.update();renderer.render(scene,camera);
}
async function init(){
  renderer=new THREE.WebGLRenderer({canvas:$('scene'),antialias:!low,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,low?1:1.6));renderer.setSize(innerWidth,innerHeight);renderer.toneMapping=THREE.AgXToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
  scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0xcbd4ce,.00038);camera=new THREE.PerspectiveCamera(63,innerWidth/innerHeight,.08,6500);camera.position.fromArray(place.p);camera.lookAt(...place.t);
  sky=new Sky();sky.scale.setScalar(4800);sky.material.uniforms.rayleigh.value=.9;sky.material.uniforms.mieCoefficient.value=.003;scene.add(sky);
  hemi=new THREE.HemisphereLight(0xd7e9f1,0xb4a58a,1.45);scene.add(hemi);
  nav=new Navigation();materialsMap=materials();await detailMaterials(materialsMap);await extendedMaterials(materialsMap);
  $('loadingText').textContent=lang==='ja'?'柱廊と庭園をつないでいます':'Connecting the colonnades and gardens';
  await new Promise(r=>setTimeout(r,0));
  const response=await fetch('data/context.json');if(!response.ok)throw new Error('The local map data could not be loaded');const context=await response.json();
  const root=new THREE.Group();scene.add(root);const b=new Builder(root,materialsMap,nav),water=[],lights=[];
  exterior(b,context,low);fortress(b);nasrid(b,water,lights);gardens(b,water);charlesV(b);landscapeDetails(b);palaceDetails(b);b.finish();world={root,stats:b.stats,context};
  csm=new CSM({camera,parent:scene,cascades:low?2:3,maxFar:low?160:280,mode:'practical',shadowMapSize:low?1024:2048,lightDirection:new THREE.Vector3(-1,-1,-1),lightIntensity:3.3,lightMargin:180});
  for(const l of csm.lights){l.shadow.bias=-.00008;l.shadow.normalBias=.06;}
  for(const m of Object.values(materialsMap))if(m.isMeshStandardMaterial){csm.setupMaterial(m);interiorShading(m);}
  for(const w of water){
    const m=materialsMap.water.clone();m.opacity=w.reflect?.28:.7;
    m.onBeforeCompile=shader=>{shader.uniforms.uTime={value:0};shader.fragmentShader='uniform float uTime;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_begin>','#include <normal_fragment_begin>\n normal.x += sin(gl_FragCoord.x * .05 + uTime*.6) * .025; normal.z += cos(gl_FragCoord.y * .06 - uTime*.4) * .025; normal = normalize(normal);');m.userData.shader=shader;};
    const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w.w,w.d),m);mesh.rotation.x=-Math.PI/2;mesh.position.set(w.x,w.y+.015,w.z);mesh.receiveShadow=true;scene.add(mesh);waterObjects.push(mesh);
    if(w.reflect){const reflector=new Reflector(new THREE.PlaneGeometry(w.w,w.d),{textureWidth:low?512:1024,textureHeight:low?512:1024,color:0xb2baba,clipBias:.002});reflector.rotation.x=-Math.PI/2;reflector.position.set(w.x,w.y,w.z);scene.add(reflector);reflectors.push(reflector);reflector.visible=false;}
  }
  tourShots=buildTourShots(PLACES,nav);
  setLight();wire();localize();go(place.id);await renderer.compileAsync(scene,camera);
  $('loading').classList.add('done');setTimeout(()=>$('loading')?.remove(),1000);
  window.ALH.ready=true;
  function loop(t){const dt=Math.min(.05,(t-last)/1000);last=t;if(!filming&&!document.hidden&&!$('references').open)update(dt);requestAnimationFrame(loop);}requestAnimationFrame(loop);
}
window.ALH={ready:false,go,
  filmFrame(id,phase,time){
    if(!filming)throw new Error('Film capture requires ?film=1');
    const p=BY_ID[id];if(place.id!==id)go(id);stopTour();
    if(p.mode==='orbit'){
      camera.position.fromArray(p.p);orb.setFromVector3(camera.position.clone().sub(orbitTarget));
      orb.theta+=phase*.5;orb.radius*=1-phase*.16;orb.phi-=Math.sin(phase*Math.PI/2)*.08;
    }else{
      const shot=sampleTourShot(tourShots[id],p,phase);
      camera.position.fromArray(shot.position);camera.lookAt(...shot.target);orientation();
    }
    now=time;update(0);
    return {ja:p.ja,en:p.en};
  },
  tourCheck(){return Object.entries(tourShots).map(([id,shot])=>{
    const p=BY_ID[id];let blocked=0,offGround=0;
    for(let i=0;i<=400;i++){const {position:[x,y,z]}=sampleTourShot(shot,p,i/400);if(nav.blocked(x,z,y-EYE))blocked++;if(Math.abs(nav.height(x,z,y-EYE)-(y-EYE))>.1)offGround++;}
    const end=shot.points.at(-1);return {id,travel:Math.hypot(end[0]-p.p[0],end[2]-p.p[2]),blocked,offGround};
  });},look(x,y,z,tx,ty,tz){stopTour();mode='fly';camera.position.set(x,y,z);camera.lookAt(tx,ty,tz);orientation();updateButtons();},
  info(){return {ready:this.ready,mode,place:place.id,position:camera?.position.toArray(),yaw,pitch,drawCalls:renderer?.info.render.calls,triangles:renderer?.info.render.triangles,geometries:renderer?.info.memory.geometries,stats:world?.stats,blocks:nav?.blocks.length,surfaces:nav?.surfaces.length,blocked:nav?nav.blocked(camera.position.x,camera.position.z,camera.position.y-EYE):null};},
  move(dx,dz){stopTour();nav.move(camera.position,dx,dz);return camera.position.toArray();},
  placeCheck(){return PLACES.filter(p=>p.mode!=='orbit').map(p=>({id:p.id,blocked:nav.blocked(p.p[0],p.p[2],p.p[1]-EYE),ground:nav.height(p.p[0],p.p[2],p.p[1]-EYE),feet:p.p[1]-EYE}));},
};
init().catch(e=>{console.error(e);fatal(lang==='ja'?`3D画面を開始できませんでした。WebGL 2 対応ブラウザーで開いてください。 (${e.message})`:`The 3D view could not start. Please use a WebGL 2 browser. (${e.message})`);});
