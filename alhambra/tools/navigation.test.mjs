import test from 'node:test';
import assert from 'node:assert/strict';
import {Navigation,EYE} from './web/navigation.js';

test('a large movement cannot tunnel through a wall or water barrier',()=>{
  const n=new Navigation();n.floor(0,0,40,40,0);n.box(0,-3,12,.5,0,6);
  const p={x:0,y:EYE,z:0};n.move(p,0,-20);assert.ok(p.z>-2.55&&p.z<-2);
});
test('walk through a doorway, but not through its jamb',()=>{
  const n=new Navigation();n.floor(0,0,40,40);n.box(-3,0,4,.6);n.box(3,0,4,.6);
  const a={x:0,y:EYE,z:3};n.move(a,0,-6);assert.ok(a.z<-2.9);
  const b={x:1.5,y:EYE,z:3};n.move(b,0,-6);assert.ok(b.z>.5);
});
test('stairs can be climbed and descended without a jump',()=>{
  const n=new Navigation();n.floor(0,0,40,40);n.ramp(0,5,3,10,0,3);n.floor(0,11,3,2,3);
  const p={x:0,y:EYE,z:-1};n.move(p,0,12);assert.ok(Math.abs(p.y-(3+EYE))<.05);
  n.move(p,0,-12);assert.ok(Math.abs(p.y-EYE)<.05);assert.ok(p.z<-.8);
});
test('a visitor cannot step over a dangerous drop',()=>{
  const n=new Navigation();n.floor(0,0,4,4,5);const p={x:0,y:5+EYE,z:0};n.move(p,0,9);assert.ok(p.z<=2.1);assert.equal(p.y,5+EYE);
});
test('diagonal input slides along a wall instead of getting stuck',()=>{
  const n=new Navigation();n.floor(0,0,40,40);n.box(0,-3,20,.5,0,6);const p={x:0,y:EYE,z:0};n.move(p,4,-7);assert.ok(p.x>3.9);assert.ok(p.z>-2.55);
});
// walking strides (2.3 m/s at 60 fps, as controls.js moves): slanted walls, slanted lanes and doorways
const walkFor=(n,p,yaw,seconds=5)=>{for(let t=0;t<seconds*60;t++)n.move(p,Math.cos(yaw)*2.3/60,Math.sin(yaw)*2.3/60);return p;};
test('a slanted wall met at 45°: the walk runs along it, never faster than walking into it allows',()=>{
  for(const a of [0,.5,.8]){
    const n=new Navigation();n.floor(0,0,60,60);n.box(-Math.sin(a)*1.45,Math.cos(a)*1.45,40,.5,0,6,-a);
    const p=walkFor(n,{x:0,y:EYE,z:0},a+Math.PI/4),along=p.x*Math.cos(a)+p.z*Math.sin(a),ideal=2.3*5*Math.cos(Math.PI/4);
    assert.ok(along>.85*ideal&&along<ideal*1.01,`wall at ${a} rad: ${along.toFixed(2)} m along, ideal ${ideal.toFixed(2)}`);
    assert.ok(p.x*-Math.sin(a)+p.z*Math.cos(a)<1.2-.2,'went into the wall');
  }
});
test('a lane slanted 25° off the way is followed, not stuck in',()=>{
  const a=25*Math.PI/180,n=new Navigation();n.floor(0,0,60,60);
  for(const s of [1,-1])n.box(-Math.sin(a)*1.05*s,Math.cos(a)*1.05*s,40,.5,0,6,-a);
  const p=walkFor(n,{x:0,y:EYE,z:0},0,6);assert.ok(p.x*Math.cos(a)+p.z*Math.sin(a)>8);
});
test('a doorway met off its middle is slipped through; a wall met head-on still stops the walk',()=>{
  const n=new Navigation();n.floor(0,0,60,60);n.box(3.25,5.45,.5,10,0,6);n.box(3.25,-5.45,.5,10,0,6);   // 0.9 m doorway at z=0
  assert.ok(walkFor(n,{x:0,y:EYE,z:.6},0,6).x>4);
  const w=new Navigation();w.floor(0,0,60,60);w.box(3.25,0,.5,20,0,6);
  const p=walkFor(w,{x:0,y:EYE,z:.3},0,6);assert.ok(p.x<3.25-.25+.01&&Math.abs(p.z-.3)<.05,`moved to ${p.x.toFixed(2)}, ${p.z.toFixed(2)}`);
});
