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
