import {extendedMaterials} from './extended-materials.js';
import {landscapeDetails, palaceDetails} from './landscape-detail.js';
import {detailMaterials,interiorShading} from './detail-materials.js';
import * as THREE from 'three';
import { CSM } from 'three/addons/csm/CSM.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { materials, random } from './materials.js';
import { Builder } from './geometry.js';
import { Navigation, EYE, terrainHeight, setTerrainSampler } from './navigation.js';
import { loadTerrain, sampler as terrainSampler, buildTerrain, buildRivers } from './terrain.js';
import { loadCity } from './city.js';
import { loadTrees } from './trees.js';
import { nasrid, gardens } from './palaces.js';
import { exterior } from './exterior.js';
import * as alcazaba from './heroes/alcazaba.js';
import * as carlos from './heroes/carlos.js';
import * as partal from './heroes/partal.js';
import * as gates from './heroes/gates.js';
import * as walls from './heroes/walls.js';
import * as grounds from './heroes/grounds.js';
import * as generalife from './heroes/generalife.js';
import * as mexuar from './heroes/mexuar.js';
import * as calderia from './heroes/calderia.js';
const HEROES=[alcazaba,carlos,partal,gates,walls,grounds,generalife];
import { PLACES, BY_ID, TOUR } from './places.js';
import { buildTourShots, sampleTourShot } from './tour.js';
import { createMusic } from './music.js';
import { createReferences } from './references.js';

// Aerial perspective: exponential (not squared) haze so the Sierra Nevada stays visible at 30 km.
THREE.ShaderChunk.fog_fragment=THREE.ShaderChunk.fog_fragment.replace('fogDensity * fogDensity * vFogDepth * vFogDepth','fogDensity * vFogDepth');
const $=id=>document.getElementById(id),query=new URLSearchParams(location.search);
let lang=location.hash==='#en'?'en':'ja',mode='walk',place=BY_ID[query.get('place')]||BY_ID.lions;
const touch=matchMedia('(pointer: coarse)').matches;
const low=query.get('q')==='low'||(query.get('q')!=='high'&&touch);
const filming=query.get('film')==='1';
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
document.body.dataset.touch=String(touch);document.body.dataset.mode=mode;
let trees,farScene,farCamera,skyCube,skyCubeCamera,farSun,farHemi,renderer,scene,camera,csm,nav,world,sky,sun,materialsMap,waterObjects=[],reflectors=[],hemi;
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
  const groupNames={nasrid:['ナスル朝宮殿','Nasrid palaces'],fortress:['アルカサバ','The Alcazaba'],gardens:['水と庭園','Water & gardens'],grounds:['宮殿と敷地','Palace & grounds'],city:['グラナダ旧市街','Old Granada']};
  $('placeList').replaceChildren();let group='';
  for(const p of PLACES){if(p.group!==group){group=p.group;const label=document.createElement('div');label.className='place-group';label.textContent=groupNames[group][lang==='ja'?0:1];$('placeList').append(label);}const button=document.createElement('button');button.className='place';button.dataset.id=p.id;button.innerHTML=`<span class="num">${p.no}</span><span>${p[lang]}</span>`;button.addEventListener('click',()=>{stopTour();go(p.id);closePlaces();});$('placeList').append(button);}
  caption(place);references?.localize();music.localize();updateButtons();drawMap();
}
function closePlaces(){document.body.classList.remove('places-open');$('placesToggle').setAttribute('aria-expanded','false');}
function updateButtons(){
  for(const m of ['walk','fly']){$(m).classList.toggle('active',mode===m);$(m).setAttribute('aria-pressed',String(mode===m));}
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
  // Evening: a low west-south-west sun (about 12 degrees) with a warmer, denser sky; afternoon is high and neutral.
  const az=day?[-.86,.21,.42]:[-.7,.95,.5];sun=new THREE.Vector3(...az).normalize();
  csm.lightDirection.copy(sun).negate();csm.lightIntensity=day?3.7:3.3;
  for(const l of csm.lights){l.color.set(day?0xffc58e:0xffefdc);l.intensity=csm.lightIntensity;}
  const u=sky.material.uniforms;u.sunPosition.value.copy(sun);u.turbidity.value=day?5:3;u.rayleigh.value=day?1.6:.9;u.mieCoefficient.value=day?.006:.003;u.mieDirectionalG.value=day?.86:.8;
  hemi.intensity=day?.82:1.45;hemi.color.set(day?0xb3bfdc:0xd7e9f1);hemi.groundColor.set(day?0x8f765c:0xb4a58a);scene.fog.color.set(day?0xdcd4ca:0xcfd6d4);farScene.fog.color.set(day?0xc2bfc4:0xc3ccd6);renderer.toneMappingExposure=day?1.1:1.07;
  farSun.position.copy(sun).multiplyScalar(1000);farSun.color.copy(csm.lights[0].color);farSun.intensity=csm.lightIntensity;farHemi.color.copy(hemi.color);farHemi.groundColor.copy(hemi.groundColor);farHemi.intensity=hemi.intensity;
  skyCubeCamera.update(renderer,farScene);shadowDirty=true;updateButtons();
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
  $('walk').onclick=()=>setMode('walk');$('fly').onclick=()=>setMode('fly');
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
  c.addEventListener('pointermove',e=>{if(!pointer||e.pointerId!==pointer.id)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;pointer.x=e.clientX;pointer.y=e.clientY;if(mode==='orbit'){orb.theta-=dx*.004;orb.phi=clamp(orb.phi+dy*.004,.12,1.55);}else{yaw+=dx*.003;pitch=clamp(pitch+dy*.003,-1.48,1.48);/* drag the scene: the view follows the hand */camera.rotation.set(pitch,yaw,0,'YXZ');}});
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
    if(mode==='walk'){if(dx||dz)nav.move(camera.position,dx,dz);}else{camera.position.x=clamp(camera.position.x+dx,-2200,1800);camera.position.z=clamp(camera.position.z+dz,-1800,1700);camera.position.y+=((keys.has('e')?1:0)-(keys.has('q')?1:0)+alt.value)*speed;camera.position.y=clamp(camera.position.y,terrainHeight(camera.position.x,camera.position.z)+.7,850);}
  }
  const nearest=reflectors.reduce((a,r)=>camera.position.distanceToSquared(r.position)<camera.position.distanceToSquared(a.position)?r:a,reflectors[0]);
  for(const r of reflectors)r.visible=r===nearest&&camera.position.distanceTo(r.position)<90&&camera.position.y<r.position.y+55;
  for(const o of waterObjects){if(o.material.userData.shader)o.material.userData.shader.uniforms.uTime.value=now;}
  if(++mapFrame%5===0)drawMap();
  trees?.update(camera);
  const camKey=camera.position.toArray().concat(camera.quaternion.toArray()).map(v=>v.toFixed(3)).join(),moved=camKey!==lastCam;
  if(moved||shadowDirty){csm.update();renderer.shadowMap.needsUpdate=true;lastCam=camKey;shadowDirty=false;}
  render();
}
let lastCam='',shadowDirty=true;
function render(){
  farCamera.position.copy(camera.position);farCamera.quaternion.copy(camera.quaternion);if(farCamera.aspect!==camera.aspect||farCamera.fov!==camera.fov){farCamera.aspect=camera.aspect;farCamera.fov=camera.fov;farCamera.updateProjectionMatrix();}
  renderer.setRenderTarget(null);renderer.clear();const upd=renderer.shadowMap.needsUpdate;renderer.shadowMap.needsUpdate=false;renderer.render(farScene,farCamera);renderer.clearDepth();renderer.shadowMap.needsUpdate=upd;renderer.render(scene,camera);
}
async function init(){
  const T0=performance.now(),mark=label=>{if(query.has('timing'))console.log('timing',label,Math.round(performance.now()-T0));};
  renderer=new THREE.WebGLRenderer({canvas:$('scene'),antialias:!low,powerPreference:'high-performance'});renderer.setPixelRatio(Math.min(devicePixelRatio,low?1:1.6));renderer.setSize(innerWidth,innerHeight);renderer.toneMapping=THREE.AgXToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.autoUpdate=false;renderer.shadowMap.type=THREE.PCFShadowMap;
  scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0xcbd4ce,3.6e-5);camera=new THREE.PerspectiveCamera(63,innerWidth/innerHeight,.08,6500);
  farScene=new THREE.Scene();farScene.fog=new THREE.FogExp2(0xbcc4cf,2.7e-5);farCamera=new THREE.PerspectiveCamera(63,innerWidth/innerHeight,600,420000);renderer.autoClear=false;
  farSun=new THREE.DirectionalLight(0xffffff,3);farHemi=new THREE.HemisphereLight(0xd7e9f1,0xb4a58a,1.45);farScene.add(farSun,farSun.target,farHemi);
  skyCube=new THREE.WebGLCubeRenderTarget(256,{type:THREE.HalfFloatType});skyCubeCamera=new THREE.CubeCamera(10,420000,skyCube);skyCubeCamera.position.set(0,8,0);camera.position.fromArray(place.p);camera.lookAt(...place.t);
  sky=new Sky();sky.scale.setScalar(560000);sky.renderOrder=-10;sky.material.uniforms.rayleigh.value=.9;sky.material.uniforms.mieCoefficient.value=.003;farScene.add(sky);
  hemi=new THREE.HemisphereLight(0xd7e9f1,0xb4a58a,1.45);scene.add(hemi);
  nav=new Navigation();materialsMap=materials();mark('canvas materials');await detailMaterials(materialsMap);mark('detail materials');await extendedMaterials(materialsMap);mark('base materials');
  $('loadingText').textContent=lang==='ja'?'柱廊と庭園をつないでいます':'Connecting the colonnades and gardens';
  await new Promise(r=>setTimeout(r,0));
  const response=await fetch('data/context.json');if(!response.ok)throw new Error('The local map data could not be loaded');const context=await response.json();context.low=low;
  const terrain=await loadTerrain('data/terrain.bin');setTerrainSampler(terrainSampler(terrain));buildTerrain(terrain,scene,farScene,low);mark('terrain');await buildRivers('data/rivers.json',scene);
  {let buf=await (await fetch('data/citynav.bin')).arrayBuffer();const h=new Uint8Array(buf,0,2);if(h[0]===0x1f&&h[1]===0x8b)buf=await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   const dv=new DataView(buf),n=dv.getUint32(0,true),polys=[];let o=4;for(let i=0;i<n;i++){const k=dv.getUint32(o,true);o+=4;polys.push(new Float32Array(buf.slice(o,o+k*8)));o+=k*8;}nav.setFootprints(polys);}
  for(const p of PLACES)if(p.ground){p.eye=p.p[1];p.p[1]+=terrainHeight(p.p[0],p.p[2]);p.t[1]+=terrainHeight(p.t[0],p.t[2]);}
  // modelled lanes (steps, paving) may stand a little above the terrain: re-seat the old-town places
  const reseat=()=>{for(const p of PLACES)if(p.ground){const g=terrainHeight(p.p[0],p.p[2]);p.p[1]=nav.height(p.p[0],p.p[2],g+1.5)+p.eye;}};
  if(place.ground){camera.position.fromArray(place.p);camera.lookAt(...place.t);}
  // Stage 1: the palaces (and the monument of the arrival place) behind the loading screen.
  // Stage 2: the other monuments nearest first, then the city and the trees, while the visitor looks around.
  const root=new THREE.Group();scene.add(root);const water=[],lights=[];
  const b=new Builder(root,materialsMap,nav);
  exterior(b,context,low);await mexuar.materials(materialsMap);nasrid(b,water,lights);try{mexuar.build(b,context);}catch(e){console.error('hero mexuar failed',e);}gardens(b,water);landscapeDetails(b);palaceDetails(b);b.finish();world={root,stats:b.stats,context};
  csm=new CSM({camera,parent:scene,cascades:low?2:3,maxFar:low?160:280,mode:'practical',shadowMapSize:low?1024:2048,lightDirection:new THREE.Vector3(-1,-1,-1),lightIntensity:3.3,lightMargin:180});
  for(const l of csm.lights){l.shadow.bias=-.00008;l.shadow.normalBias=.06;}
  const prepared=new Set();
  const prepare=()=>{for(const m of Object.values(materialsMap))if(m.isMeshStandardMaterial&&!prepared.has(m)){prepared.add(m);csm.setupMaterial(m);interiorShading(m);}};
  const addWater=list=>{for(const w of list){
    const m=materialsMap.water.clone();m.opacity=w.reflect?.28:.7;
    m.onBeforeCompile=shader=>{shader.uniforms.uTime={value:0};shader.fragmentShader='uniform float uTime;\n'+shader.fragmentShader;shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_begin>','#include <normal_fragment_begin>\n normal.x += sin(gl_FragCoord.x * .05 + uTime*.6) * .025; normal.z += cos(gl_FragCoord.y * .06 - uTime*.4) * .025; normal = normalize(normal);');m.userData.shader=shader;};
    const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w.w,w.d),m);mesh.rotation.x=-Math.PI/2;mesh.position.set(w.x,w.y+.015,w.z);mesh.receiveShadow=true;scene.add(mesh);waterObjects.push(mesh);
    if(w.reflect){const reflector=new Reflector(new THREE.PlaneGeometry(w.w,w.d),{textureWidth:low?512:1024,textureHeight:low?512:1024,color:0xb2baba,clipBias:.002});reflector.rotation.x=-Math.PI/2;reflector.position.set(w.x,w.y,w.z);{const draw=reflector.onBeforeRender;reflector.onBeforeRender=(r,s,c,...rest)=>{const bg=s.background;s.background=skyCube.texture;draw.call(reflector,r,s,c,...rest);s.background=bg;};}scene.add(reflector);reflectors.push(reflector);reflector.visible=false;}
  }list.length=0;};
  // A failing hero module is reported but does not take the whole site down.
  const heroBuild={walls:bb=>walls.build(bb,context),alcazaba:bb=>alcazaba.build(bb,context),gates:bb=>gates.build(bb,context),partal:bb=>partal.build(bb,water,context),carlos:bb=>carlos.build(bb,context),grounds:bb=>grounds.build(bb,context),generalife:bb=>generalife.build(bb,water,context),calderia:bb=>calderia.build(bb,context)};
  const heroModule={walls,alcazaba,gates,partal,carlos,grounds,generalife,calderia};
  const heroAt={walls:[60,180],alcazaba:[-185,20],gates:[-80,90],carlos:[-22,52],partal:[110,10],grounds:[150,140],generalife:[370,-50],calderia:[-640,-40]};
  const firstHeroes={alcazaba:['alcazaba','walls'],vela:['alcazaba','walls'],carlos:['carlos'],partal:['partal'],justice:['walls','gates'],generalife:['generalife'],calderia:['calderia'],overview:['walls']}[place.id]||[];
  const matsDone=new Set();
  async function loadHero(name,parent,compile){
    const g=new THREE.Group();g.name='hero:'+name;
    try{for(const dep of name==='walls'?['gates','walls']:[name])if(!matsDone.has(dep)){matsDone.add(dep);await heroModule[dep].materials(materialsMap);}const bb=new Builder(g,materialsMap,nav);heroBuild[name](bb);bb.finish();}catch(e){console.error(`hero ${name} failed`,e);return;}
    prepare();if(compile)await renderer.compileAsync(g,camera,scene);parent.add(g);addWater(water);mark('hero '+name);
  }
  for(const h of firstHeroes)await loadHero(h,scene,false);
  reseat();if(place.ground){camera.position.fromArray(place.p);camera.lookAt(...place.t);}
  prepare();addWater(water);
  tourShots=buildTourShots(PLACES,nav);mark('stage 1 build');
  setLight();wire();localize();go(place.id);await renderer.compileAsync(scene,camera);mark('compile');
  const rest=Object.keys(heroAt).filter(h=>!firstHeroes.includes(h)).sort((a,c)=>Math.hypot(heroAt[a][0]-place.p[0],heroAt[a][1]-place.p[2])-Math.hypot(heroAt[c][0]-place.p[0],heroAt[c][1]-place.p[2]));
  // gates.js stands its feet on the ground registered by walls.js
  if(rest.includes('gates')&&rest.includes('walls')&&rest.indexOf('walls')>rest.indexOf('gates')){rest.splice(rest.indexOf('walls'),1);rest.splice(rest.indexOf('gates'),0,'walls');}
  async function stage2(){
    await new Promise(r=>setTimeout(r,600));
    for(const h of rest){await new Promise(r=>setTimeout(r,30));await loadHero(h,scene,true);shadowDirty=true;}
    tourShots=buildTourShots(PLACES,nav);
    const city=await loadCity('data/city.bin',null,low);await renderer.compileAsync(city.group,camera,scene);scene.add(city.group);mark('city');
    // Generic trees on the Generalife hill give way to the modelled gardens, walls and buildings.
    const onModel=(x,z)=>x>300&&x<460&&z>-160&&z<220&&(nav.blocked(x,z,terrainHeight(x,z),2)||nav.surfaces.some(f=>{const [u,v]=nav.local(f,x,z);return Math.abs(u)<=f.w+2&&Math.abs(v)<=f.d+2;}));
    // Keep the sight lines of the old-town viewpoints open (no generic tree right in front of the visitor).
    const views=PLACES.filter(p=>p.ground).map(p=>{const dx=p.t[0]-p.p[0],dz=p.t[2]-p.p[2],l=Math.hypot(dx,dz);return [p.p[0],p.p[2],dx/l,dz/l];});
    const inView=(x,z)=>views.some(([px,pz,dx,dz])=>{const u=(x-px)*dx+(z-pz)*dz,v=Math.abs((x-px)*dz-(z-pz)*dx);return u>-4&&u<90&&v<6+u*.35;});
    trees=await loadTrees('data/trees.bin',renderer,scene,terrainHeight,low,(x,z)=>onModel(x,z)||inView(x,z));mark('trees');
    reseat();shadowDirty=true;window.ALH.ready=true;
  }
  window.ALH.shown=true;
  $('loading').classList.add('done');setTimeout(()=>$('loading')?.remove(),1000);
  stage2().catch(e=>console.error('stage 2 failed',e));
  // Dynamic resolution: keep slower GPUs (laptops, phones) near 45-60 fps by trading pixel density.
  const maxPR=Math.min(devicePixelRatio,low?1:1.6),minPR=Math.min(maxPR,low?.7:1);let pr=maxPR,acc=0,frames=0;
  function adapt(ms){if(filming||query.has('pr'))return;acc+=ms;if(++frames<40)return;const avg=acc/frames;acc=frames=0;
    const next=avg>24?Math.max(minPR,pr-.15):avg<15?Math.min(maxPR,pr+.1):pr;if(Math.abs(next-pr)>.01){pr=next;renderer.setPixelRatio(pr);renderer.setSize(innerWidth,innerHeight);}}
  function loop(t){const raw=t-last,dt=Math.min(.05,raw/1000);last=t;if(raw<200)adapt(raw);if(!filming&&!document.hidden&&!$('references').open)update(dt);requestAnimationFrame(loop);}requestAnimationFrame(loop);
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
  heavy(){const rows=[];scene.traverse(o=>{if(!o.isMesh)return;const g=o.geometry,t=(g.index?g.index.count:g.attributes.position.count)/3,n=o.isInstancedMesh?o.count:1;rows.push([o.name||g.type,Array.isArray(o.material)?'multi':o.material.name||o.material.type,Math.round(t),n,Math.round(t*n),o.castShadow]);});return rows.sort((a,b)=>b[4]-a[4]).slice(0,25);},
  pick(x,y){camera.updateMatrixWorld();const r=new THREE.Raycaster();r.setFromCamera(new THREE.Vector2(x*2-1,1-y*2),camera);return r.intersectObjects(scene.children,true).slice(0,3).map(h=>[h.object.material.name,h.object.geometry.type,+h.distance.toFixed(2),h.point.toArray().map(v=>+v.toFixed(2))]);},
  debug(){return {scene,farScene,camera,renderer};},
  THREE,ground:(x,z)=>nav.height(x,z),blockedAt:(x,z,g)=>nav.blocked(x,z,g),blockedAtR:(x,z,g,r)=>nav.blocked(x,z,g,r),
  bench(n=30){const gl=renderer.getContext();render();gl.finish();const t=performance.now();for(let i=0;i<n;i++){csm.update();renderer.shadowMap.needsUpdate=true;render();}gl.finish();return +((performance.now()-t)/n).toFixed(2);},
  fps(ms=3000){return new Promise(res=>{let n=0,worst=0,prev=performance.now();const t0=prev;const f=t=>{n++;worst=Math.max(worst,t-prev);prev=t;if(t-t0<ms)requestAnimationFrame(f);else res({fps:+(n/((t-t0)/1000)).toFixed(1),worstMs:+worst.toFixed(1),calls:renderer.info.render.calls,tris:renderer.info.render.triangles});};requestAnimationFrame(f);});},
  far(){let n=0,t=0;farScene.traverse(o=>{if(o.isMesh){n++;t+=o.geometry.index?o.geometry.index.count/3:0;}});return {meshes:n,tris:t,ground:[terrainHeight(20800,13400),terrainHeight(24700,13800),terrainHeight(-260,24)]};},
  move(dx,dz){stopTour();nav.move(camera.position,dx,dz);return camera.position.toArray();},
  placeCheck(){return PLACES.filter(p=>p.mode!=='orbit').map(p=>({id:p.id,blocked:nav.blocked(p.p[0],p.p[2],p.p[1]-EYE),ground:nav.height(p.p[0],p.p[2],p.p[1]-EYE),feet:p.p[1]-EYE}));},
};
init().catch(e=>{console.error(e);fatal(lang==='ja'?`3D画面を開始できませんでした。WebGL 2 対応ブラウザーで開いてください。 (${e.message})`:`The 3D view could not start. Please use a WebGL 2 browser. (${e.message})`);});
