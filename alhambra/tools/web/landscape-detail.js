import * as THREE from 'three';
import {nicheGeometry} from './detail-rooms.js';
import {random} from './materials.js';

// Folded, pointed leaves give real silhouettes and cast broken shadows. The
// same six-triangle geometry is instanced, including in light quality mode.
function leaves(b,x,y,z,rx,ry,rz,count,seed,size=.12){
 const r=random(seed),geo=b.geometry('garden-leaf',()=>{
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute([0,0,-1,-.46,.08,0,0,.23,0, 0,0,-1,0,.23,0,.46,.08,0, -.46,.08,0,0,0,1,0,.23,0, 0,.23,0,0,0,1,.46,.08,0],3));g.setAttribute('uv',new THREE.Float32BufferAttribute([.5,0,0,.5,.5,.5,.5,0,.5,.5,1,.5,0,.5,.5,1,.5,.5,.5,.5,.5,1,1,.5],2));g.computeVertexNormals();return g;
 });
 for(let i=0;i<count;i++){const a=r()*Math.PI*2,v=r()*2-1,k=Math.sqrt(1-v*v),rad=.75+r()*.25;const scale=size*(.6+r()*.8);b.add(geo,i%5===0?'leafLight':i%4===0?'leafDark':'leaf',[x+Math.sin(a)*k*rx*rad,y+v*ry*rad,z+Math.cos(a)*k*rz*rad],[scale,scale*(1+r()*3),scale],r()*6.28);}
}
function tree(b,x,y,z,r=1.8,h=4,seed=4){
 b.cylinder(x,y,z,.095,h*.68,'trunk',.06,9);
 const rand=random(seed);for(let i=0;i<6;i++){const a=i*2.399,xx=x+Math.cos(a)*r*.6,zz=z+Math.sin(a)*r*.6,yy=y+h*(.65+rand()*.25);b.line([x,y+h*.42,z],[xx,yy,zz],.035,'trunk');leaves(b,xx,yy,zz,r*.6,h*.22,r*.6,460,seed+i,.085);}
}
function hedge(b,x,y,z,w,d,seed){
 for(let i=0;i<Math.ceil(d/.8);i++)leaves(b,x,y+.48,z-d/2+(i+.5)*d/Math.ceil(d/.8),w*.58,.18,.55,60,seed+i,.065);
}
export function landscapeDetails(b){
 b.zone='myrtles';for(const s of [-1,1])hedge(b,1.5+s*4.65,0,0,1.1,30.3,145+s);
 b.zone='partal';
 for(const s of [-1,1]){b.box(102+s*7.55,0,0,.38,.18,26.4,'terracotta');b.box(102+s*9,0,0,1,.5,27,'hedge');hedge(b,102+s*9,0,0,1,27,48+s);}
 for(const [x,z,h] of [[87,-15,8],[120,-12,10],[123,15,8]]){b.cone(x,0,z,1.05,h,'cypress',16);for(let j=0;j<14;j++)leaves(b,x,.6+j*h/15,z,1.1*(1-j/16),.4,1.1*(1-j/16),110,230+j,.12);}
 for(const x of [78,122,145,164,184])for(const z of [28,49,69])tree(b,x,0,z,2.0,4.5,x+z);
 b.zone='generalife';b.offset=[370,32,-52];
 for(const s of [-1,1]){
  b.box(s*1.15,.04,0,.22,.14,41.4,'terracotta');
  for(const zz of [-18,-6,6,18]){const d=Math.abs(zz)===18?5:10;hedge(b,s*3.35,0,zz,3,d,400+zz+s);}
  for(const z of [-16,-7,4,15])tree(b,s*3.8,0,z,.85,3.1,680+z+s);
 }
 // Climbing foliage follows the east retaining wall rather than filling the paths.
 for(let z=-22;z<23;z+=.85){leaves(b,6.65,3.8+.25*Math.sin(z),z,.45,.55,.75,85,1100+Math.round(z*10),.085);if(Math.round(z)%3===0)b.flowers(6.5,4.25,z,'flower');}
 b.offset=[0,0,0];
}
export function palaceDetails(b){
 b.zone='kings';
 // Photograph mapped once onto a gently curved central ceiling panel. The two
 // other narrative paintings have not been inferred from this one image.
 const painting=new THREE.PlaneGeometry(4.5,6.3,30,40);painting.rotateX(-Math.PI/2);const pos=painting.attributes.position;
 for(let i=0;i<pos.count;i++){const x=pos.getX(i),z=pos.getZ(i);pos.setY(i,.65*(1-(x/2.25)**2)*(1-(z/3.15)**2));}painting.computeVertexNormals();b.unique(painting,'kingsPainting',[59,5.24,13.5]);
 for(const s of [-1,1]){b.box(59+s*2.34,5.12,13.5,.18,.2,6.6,'frieze');b.box(59,5.12,13.5+s*3.25,4.8,.2,.18,'frieze');}
 b.zone='lindaraja';const glass=new THREE.PlaneGeometry(2.8,2.6);glass.rotateX(-Math.PI/2);b.unique(glass,'lindarajaGlass',[38,5.72,-10.2]);
 for(const s of [-1,1]){b.box(38+s*1.48,5.55,-10.2,.13,.2,2.95,'wood');b.box(38,5.55,-10.2+s*1.38,3.1,.2,.13,'wood');}
 const cell=b.geometry('sisters-concave-niche',nicheGeometry);
 for(let side=0;side<4;side++){const a=side*Math.PI/2;for(let j=0;j<3;j++)for(let i=0;i<12;i++){const u=(i-5.5)*.28,v=1.9-j*.16;b.add(cell,'nicheCell',[38+Math.cos(a)*u+Math.sin(a)*v,4.75+j*.24,-10.2-Math.sin(a)*u+Math.cos(a)*v],[.30,.40,.28],a);b.stats.muqarnas++;}}
 // Layered friezes and exposed joists produce scale and portico shade.
 b.zone='lions';for(const sign of [-1,1]){
  for(const y of [3.65,4.35])b.box(38,y,18+sign*8,28.8,.17,.47,'frieze');
  for(let i=0;i<44;i++)b.box(23.8+i*.66,4.84,18+sign*9.6,.105,.15,3.2,'wood');
  for(let i=0;i<28;i++)b.box(38+sign*16,4.84,10+i*.59,3.8,.15,.105,'wood');
 }
 b.zone='myrtles';for(const zz of [-18.3,18.3]){
  b.box(1.5,5.12,zz,24,.17,.55,'frieze');
  for(let i=0;i<45;i++)b.box(-10.4+i*.54,5.05,zz,.10,.18,4.1,'wood');
 }
 // Carved doors remain outside the traversable entrances.
 b.zone='mexuar';for(const s of [-1,1])b.box(-29+s*2.5,0,-20.17,1.7,2.5,.045,'carvedDoor');
 for(let x=-33.5;x<-24;x+=.65)b.box(x,5.35,-7,.10,.16,26,'wood');
 b.zone='charles';
 for(let i=0;i<32;i++){const a=(i+.5)*Math.PI/16,r=15.4,x=-40+Math.sin(a)*r,z=65+Math.cos(a)*r,w=2*r*Math.tan(Math.PI/32);
  for(const y of [4.92,5.18,6.08,10.92,11.18,12.08])b.box(x,y,z,w+.16,.12,1.42,'ivory',a);
  b.box(x,6.35,z,w-.40,.78,.25,'ivory',a);b.box(x,7.13,z,w,.14,.43,'ivory',a);
  // Radial beams in both covered galleries.
  for(const y of [5.0,11.0])for(const d of [-.7,0,.7]){const aa=a+d/15.4;b.box(-40+Math.sin(aa)*17.8,y,65+Math.cos(aa)*17.8,.12,.18,4.6,'wood',aa);}
 }
}
