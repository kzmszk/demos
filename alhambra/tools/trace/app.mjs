// The movement glue of web/main.js on shared/move (web/controls.js), transcribed line for line like app.orig.mjs:
// the variables (:34, :42), orientation / setMode / go / startTour / stopTour (:71-88), drawMap's read of yaw (:109),
// wire()'s Controls and input listeners (:112-140), update()'s tour part and controls.update (:153-173) and
// ALH.filmFrame / look / move.  DOM, rendering, captions, URLs and buttons are left out.  Keep this in step with
// main.js.
import * as THREE from 'three';
import { EYE } from '../web/navigation.js';
import { BY_ID, TOUR } from '../web/places.js';
import { buildTourShots, sampleTourShot } from '../web/tour.js';
import { Controls } from '../web/controls.js';

export function makeApp({ camera, nav, win, doc, canvas, joy, rise, descend, dialogs, now }) {
  const performance = { now }, window = win, document = doc;
  const $ = (id) => ({ scene: canvas, joystick: joy, rise, descend, help: { open: dialogs.help }, references: { open: dialogs.references } })[id];
  const reduced = false;
  let mode = 'walk', place = BY_ID.lions, map = null;
  let controls, orbitTarget = new THREE.Vector3(80, 0, 30), orb = new THREE.Spherical(520, 1.08, -.8);
  let tour = false, tourTime = 0, tourIndex = 0, tourStart = 0, tourOrigin = 0;
  const tourShots = buildTourShots(Object.values(BY_ID), nav);
  const caption = (p) => { place = p; }, updateButtons = () => {}, closePlaces = () => {}, drawMap = () => { map = controls.yaw; };

  function orientation(){controls.orientation();}
  function setMode(next){
    stopTour();if(next==='orbit'){go('overview');return;}
    if(next==='walk'&&mode!=='walk'){
      const floor=nav.height(camera.position.x,camera.position.z,camera.position.y-EYE);
      if(camera.position.y-floor>6||nav.blocked(camera.position.x,camera.position.z,floor)){const p=place.id==='overview'?BY_ID.lions:place;camera.position.fromArray(p.p);camera.lookAt(...p.t);orientation();caption(p);}else camera.position.y=floor+EYE;
    }
    mode=controls.mode=next;updateButtons();
  }
  function go(id,fromTour=false){
    const p=BY_ID[id];if(!p||!camera)return false;
    if(!fromTour)stopTour();caption(p);camera.position.fromArray(p.p);camera.lookAt(...p.t);orientation();mode=controls.mode=p.mode||'walk';
    if(mode==='orbit'){orbitTarget.set(...p.t);orb.setFromVector3(camera.position.clone().sub(orbitTarget));}
    controls.keys.clear();controls.move.x=controls.move.y=0;updateButtons();
    drawMap();return true;
  }
  function startTour(){tour=true;tourTime=0;tourStart=performance.now();tourOrigin=tourIndex=Math.max(0,TOUR.indexOf(place.id));closePlaces();go(TOUR[tourIndex],true);updateButtons();}
  function stopTour(){if(!tour)return;tour=false;updateButtons();}
  let pauseInput;
  function wire(){
    const ignore=e=>$('help').open||$('references').open||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName);
    controls=new Controls(camera,$('scene'),{mode,nav,orb,orbitTarget,stopTour,ignore,win});
    const stick=controls.move;
    pauseInput=()=>{stopTour();controls.resetInput();stick.x=stick.y=0;controls.vert=0;$('joystick').firstElementChild.style.transform='';};
    window.addEventListener('keydown',e=>{
      if(ignore(e))return;
      const key=e.key.toLowerCase();
      if(e.repeat)return;if(key==='escape'){stopTour();}
    });
    window.addEventListener('blur',()=>{stick.x=stick.y=0;controls.vert=0;});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){stick.x=stick.y=0;controls.vert=0;}});
    const knob=joy.firstElementChild;let joyId=null;
    const joystick=e=>{const r=joy.getBoundingClientRect(),x=(e.clientX-r.left-r.width/2)/24,y=(e.clientY-r.top-r.height/2)/24,l=Math.max(1,Math.hypot(x,y));stick.x=x/l;stick.y=y/l;knob.style.transform=`translate(${stick.x*20}px,${stick.y*20}px)`;};
    joy.addEventListener('pointerdown',e=>{e.preventDefault();stopTour();if(mode==='orbit')setMode('walk');joyId=e.pointerId;joy.setPointerCapture(joyId);joystick(e);});joy.addEventListener('pointermove',e=>{if(e.pointerId===joyId)joystick(e);});
    for(const ev of ['pointerup','pointercancel','lostpointercapture'])joy.addEventListener(ev,()=>{joyId=null;stick.x=stick.y=0;knob.style.transform='';});
    for(const [id,n] of [['rise',1],['descend',-1]]){$(id).onpointerdown=e=>{e.preventDefault();stopTour();controls.vert=n;$(id).setPointerCapture(e.pointerId);};for(const ev of ['pointerup','pointercancel','lostpointercapture'])$(id).addEventListener(ev,()=>{controls.vert=0;});}
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
    controls.update(dt);
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
    look(x,y,z,tx,ty,tz){stopTour();mode=controls.mode='fly';camera.position.set(x,y,z);camera.lookAt(tx,ty,tz);orientation();updateButtons();},
    move(dx,dz){stopTour();nav.move(camera.position,dx,dz);return camera.position.toArray();},
  };
  return {
    init() { camera.position.fromArray(place.p); camera.lookAt(...place.t); wire(); go(place.id); },
    step: update, setMode, go, startTour, stopTour, pauseInput: () => pauseInput(), ...ALH,
    state: () => ({ mode, tour, place: place.id, yaw: controls.yaw, pitch: controls.pitch, orb: [orb.radius, orb.phi, orb.theta], stick: [controls.move.x, controls.move.y], alt: controls.vert, map }),
  };
}
