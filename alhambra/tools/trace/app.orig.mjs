// The movement glue of web/main.js BEFORE the shared/move migration, transcribed line for line from main.js as of the
// commit that adds this file: the variables (:34, :41-44), orientation / setMode / go / startTour / stopTour
// (:72-89), drawMap's read of yaw (:110), wire()'s input listeners (:113-142), update()'s tour and movement part
// (:154-183) and ALH.go / filmFrame / look / info / move (:274-301).  DOM, rendering, captions, URLs and buttons are
// left out.  init() reproduces the camera sequence of init() for a non-ground place (:204, :248: lookAt, wire, go).
// The golden trace (golden.json) is recorded from this file; do not edit it.
import * as THREE from 'three';
import { EYE, terrainHeight } from '../web/navigation.js';
import { BY_ID, TOUR } from '../web/places.js';
import { buildTourShots, sampleTourShot } from '../web/tour.js';

export function makeApp({ camera, nav, win, doc, canvas, joy, rise, descend, dialogs, now }) {
  const performance = { now };
  const $ = (id) => ({ joystick: joy, rise, descend, help: { open: dialogs.help }, references: { open: dialogs.references } })[id];
  const reduced = false, filming = true;
  let mode = 'walk', place = BY_ID.lions, map = null;
  let yaw = 0, pitch = 0, orbitTarget = new THREE.Vector3(80, 0, 30), orb = new THREE.Spherical(520, 1.08, -.8);
  let tour = false, tourTime = 0, tourIndex = 0, tourStart = 0, tourOrigin = 0;
  const keys = new Set(), stick = { x: 0, y: 0 }, alt = { value: 0 }; let pointer = null;
  const clamp = THREE.MathUtils.clamp;
  const tourShots = buildTourShots(Object.values(BY_ID), nav);
  const caption = (p) => { place = p; }, updateButtons = () => {}, closePlaces = () => {}, drawMap = () => { map = yaw; };

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
    drawMap();return true;
  }
  function startTour(){tour=true;tourTime=0;tourStart=performance.now();tourOrigin=tourIndex=Math.max(0,TOUR.indexOf(place.id));closePlaces();go(TOUR[tourIndex],true);updateButtons();}
  function stopTour(){if(!tour)return;tour=false;updateButtons();}
  let pauseInput;
  function wire(){
    pauseInput=()=>{stopTour();keys.clear();stick.x=stick.y=0;alt.value=0;pointer=null;$('joystick').firstElementChild.style.transform='';};
    const c=canvas;
    c.addEventListener('pointerdown',e=>{if(e.button!==0)return;stopTour();c.focus();pointer={id:e.pointerId,x:e.clientX,y:e.clientY};c.setPointerCapture(e.pointerId);});
    c.addEventListener('pointermove',e=>{if(!pointer||e.pointerId!==pointer.id)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;pointer.x=e.clientX;pointer.y=e.clientY;if(mode==='orbit'){orb.theta-=dx*.004;orb.phi=clamp(orb.phi+dy*.004,.12,1.55);}else{yaw+=dx*.003;pitch=clamp(pitch+dy*.003,-1.48,1.48);/* drag the scene: the view follows the hand */camera.rotation.set(pitch,yaw,0,'YXZ');}});
    for(const ev of ['pointerup','pointercancel','lostpointercapture'])c.addEventListener(ev,()=>{pointer=null;});
    c.addEventListener('wheel',e=>{e.preventDefault();if(mode==='orbit'){stopTour();orb.radius=clamp(orb.radius*Math.exp(e.deltaY*.001),30,1200);}}, {passive:false});
    win.addEventListener('keydown',e=>{
      if($('help').open||$('references').open||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
      const key=e.key.toLowerCase();if(['w','a','s','d','q','e','shift','arrowup','arrowdown','arrowleft','arrowright'].includes(key)){e.preventDefault();stopTour();keys.add(key);}
      if(e.repeat)return;if(key==='escape'){stopTour();}
    });
    win.addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));win.addEventListener('blur',()=>{keys.clear();stick.x=stick.y=0;alt.value=0;pointer=null;});
    doc.addEventListener('visibilitychange',()=>{if(doc.hidden){keys.clear();stick.x=stick.y=0;alt.value=0;}});
    const knob=joy.firstElementChild;let joyId=null;
    const joystick=e=>{const r=joy.getBoundingClientRect(),x=(e.clientX-r.left-r.width/2)/24,y=(e.clientY-r.top-r.height/2)/24,l=Math.max(1,Math.hypot(x,y));stick.x=x/l;stick.y=y/l;knob.style.transform=`translate(${stick.x*20}px,${stick.y*20}px)`;};
    joy.addEventListener('pointerdown',e=>{e.preventDefault();stopTour();if(mode==='orbit')setMode('walk');joyId=e.pointerId;joy.setPointerCapture(joyId);joystick(e);});joy.addEventListener('pointermove',e=>{if(e.pointerId===joyId)joystick(e);});
    for(const ev of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(ev,()=>{joyId=null;stick.x=stick.y=0;knob.style.transform='';});
    for(const [id,n] of [['rise',1],['descend',-1]]){$(id).onpointerdown=e=>{e.preventDefault();stopTour();alt.value=n;$(id).setPointerCapture(e.pointerId);};for(const ev of ['pointerup','pointercancel','lostpointercapture'])$(id).addEventListener(ev,()=>{alt.value=0;});}
  }
  function update(dt){
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
    drawMap();
  }
  const ALH = {
    filmFrame(id,phase){
      const p=BY_ID[id];if(place.id!==id)go(id);stopTour();
      if(p.mode==='orbit'){
        camera.position.fromArray(p.p);orb.setFromVector3(camera.position.clone().sub(orbitTarget));
        orb.theta+=phase*.5;orb.radius*=1-phase*.16;orb.phi-=Math.sin(phase*Math.PI/2)*.08;
      }else{
        const shot=sampleTourShot(tourShots[id],p,phase);
        camera.position.fromArray(shot.position);camera.lookAt(...shot.target);orientation();
      }
      update(0);
    },
    look(x,y,z,tx,ty,tz){stopTour();mode='fly';camera.position.set(x,y,z);camera.lookAt(tx,ty,tz);orientation();updateButtons();},
    move(dx,dz){stopTour();nav.move(camera.position,dx,dz);return camera.position.toArray();},
  };
  return {
    init() { camera.position.fromArray(place.p); camera.lookAt(...place.t); wire(); go(place.id); },
    step: update, setMode, go, startTour, stopTour, pauseInput: () => pauseInput(), ...ALH,
    state: () => ({ mode, tour, place: place.id, yaw, pitch, orb: [orb.radius, orb.phi, orb.theta], stick: [stick.x, stick.y], alt: alt.value, map }),
  };
}
