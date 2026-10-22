import {detailedComares,detailedSisters,detailedAbencerrajes} from './detail-rooms.js';
import {myrtlesSide} from './myrtles.js';
import {generalifeNorth} from './generalife.js';
import * as THREE from 'three';

export function room(b,x,z,w,d,h=6,{n=0,s=0,e=0,w:west=0,tile='tile',ceiling=true,wallMaterial='plaster'}={}){
  b.floor(x,z,w,d);b.wall(x,z-d/2,w,h,.65,n,wallMaterial,0,0,tile);b.wall(x,z+d/2,w,h,.65,s,wallMaterial,0,0,tile);
  b.wall(x-w/2,z,d,h,.65,west,wallMaterial,Math.PI/2,0,tile);b.wall(x+w/2,z,d,h,.65,e,wallMaterial,Math.PI/2,0,tile);
  if(ceiling){b.box(x,h,z,w,.18,d,'wood');b.roof(x,z,w+1,d+1,h+.2,2);}
}
function arcade(b,x,z,len,n,rot=0,h=2.8,r=.12,depth=3.0,columns=true){
  const step=len/n;
  const at=u=>[x+u*Math.cos(rot),z-u*Math.sin(rot)];
  for(let i=0;i<=n;i++){const [px,pz]=at(-len/2+i*step);if(columns)b.column(px,pz,h,r);}
  for(let i=0;i<n;i++){const [px,pz]=at(-len/2+(i+.5)*step);b.arch(px,pz,step-.10,h,step*.48,h+1.85,.42,'plaster',rot);}
  b.box(x,h+1.85,z,len+.25,.12,.72,'wood',rot);
}
function bassin(b,x,z,r=.7){b.cylinder(x,0,z,r,.12,'marble');b.cylinder(x,.12,z,r*.83,.16,'marble');b.cylinder(x,.28,z,r*.7,.015,'water');b.cylinder(x,.28,z,.06,.18,'ivory');b.jet(x,.45,z,0,.15,.2);b.nav.box(x+b.offset[0],z+b.offset[2],r*1.8,r*1.8,b.offset[1],b.offset[1]+.6);}


function lion(b,cx,cz,a){
  const origin=b.offset.slice();b.stats.lions++;
  const pt=(u,v)=>[cx+Math.cos(a)*u+Math.sin(a)*v,cz-Math.sin(a)*u+Math.cos(a)*v];
  const sphere=(u,y,v,sx,sy,sz,mat='marble')=>{const p=pt(u,v);b.sphere(p[0],y,p[1],sx,sy,sz,mat,a);};
  sphere(0,.88,-.08,.23,.28,.63);sphere(0,.89,.43,.27,.4,.28);
  sphere(0,1.16,.52,.205,.215,.29);sphere(0,1.08,.75,.18,.115,.18);
  sphere(0,1.0,.74,.165,.065,.19);
  for(const u of [-.18,.18])for(const v of [-.43,.4]){const p=pt(u,v);b.cylinder(p[0],.10,p[1],.075,.75,'marble',.105,9);sphere(u,.12,v+.08,.105,.06,.17);}
  for(const u of [-.15,.15]){sphere(u,1.32,.48,.06,.07,.045);sphere(u,1.20,.73,.023,.018,.019,'dark');sphere(u,1.23,.72,.065,.027,.028);}
  sphere(0,1.14,.89,.048,.035,.035,'ivory');
  // Four courses of carved locks, following the long-necked silhouette in Plate XVII.
  for(let row=0;row<4;row++)for(let k=0;k<11;k++){
    const th=-Math.PI*.8+k*Math.PI*1.6/10,rx=.28-row*.015,yy=1.12-row*.13;
    const points=[];for(let q=0;q<5;q++){const t=q/4,ang=th+Math.sin(t*Math.PI)*.12;const p=pt(Math.sin(ang)*rx,.42+Math.cos(ang)*.27);points.push([p[0],yy-t*.13,p[1]]);}for(let j=1;j<points.length;j++)b.line(points[j-1],points[j],.014,'ivory');
  }
  const tail=[];for(let i=0;i<18;i++){const t=i/17;const p=pt(.24+Math.sin(t*4)*.15,-.4-t*.45);tail.push([p[0],.69-t*.4,p[1]]);}for(let i=1;i<tail.length;i++)b.line(tail[i-1],tail[i],.035,'marble');
  const mouth=pt(0,.92);b.jet(mouth[0],1.05,mouth[1],Math.sin(a)*.5,Math.cos(a)*.5,.05);
  b.offset=origin;
}
function lionFountain(b,x,z){
  b.cylinder(x,.0,z,2.45,.05,'marble',2.45,12);
  for(let i=0;i<12;i++){const a=i*Math.PI/6;lion(b,x+Math.sin(a)*1.45,z+Math.cos(a)*1.45,a);}
  b.cylinder(x,1.2,z,1.55,.22,'marble',1.83,12);b.cylinder(x,1.42,z,1.83,.2,'frieze',1.83,12);b.cylinder(x,1.63,z,1.71,.02,'water',1.71,48);
  b.cylinder(x,1.64,z,.11,.23,'marble');b.jet(x,1.87,z,.07,.1,.35);
  b.nav.box(x,z,4.3,4.3,0,2.2);
}

export function nasrid(b,water,lights){
  b.zone='lions';
  const x=38,z=18,halfX=14.4,halfZ=8;
  b.floor(x,z,38,26);
  // 1:100 plan P-000158: 28.8 m x 16.0 m between the perimeter colonnades.
  for(const sign of [-1,1]){
    for(let i=0;i<=17;i++){const px=x-halfX+i*28.8/17;b.column(px,z+sign*halfZ,2.75,.105);if(i%3!==0)b.column(px+.24,z+sign*halfZ,2.75,.105);}
    arcade(b,x,z+sign*halfZ,28.8,17,0,2.75,.105,3,false);
    for(let i=1;i<11;i++){const pz=z-halfZ+i*16/11;b.column(x+sign*halfX,pz,2.75,.105);if(i%3!==0&&i!==10)b.column(x+sign*halfX,pz+.24,2.75,.105);}
    arcade(b,x+sign*halfX,z,16,11,Math.PI/2,2.75,.105,3,false);
    b.wall(x,z+sign*10.8,36.2,5.1,.65,3.0,'plaster',0,0,sign<0?'tileRibbon':'tile');
    b.wall(x+sign*18,z,21.6,5.1,.65,4.1,'plaster',Math.PI/2);
    b.roof(x,z+sign*9.6,36.4,3.5,5.05,1.2);b.roof(x+sign*16,z,4.8,19,5.05,1.2);
    // Projecting square pavilions, paired and tripled slender supports.
    const px=x+sign*12.25;
    for(const dx of [-2.1,2.1])for(const dz of [-2.1,2.1])for(const of of [-.22,0,.22])b.column(px+dx+of,z+dz,2.75,.09);
    for(const s of [-1,1]){b.column(px,z+s*2.1,2.75,.10);b.column(px+s*2.1,z,2.75,.10);arcade(b,px,z+s*2.1,4.2,2,0,2.75,.1,3,false);arcade(b,px+s*2.1,z,4.2,2,Math.PI/2,2.75,.1,3,false);}
    b.roof(px,z,5.0,5.0,5.05,1.65);
    for(let k=0;k<10;k++)for(let side=0;side<4;side++){const a=side*Math.PI/2;const u=-2.1+k*.46;b.cone(px+u*Math.cos(a)+2.12*Math.sin(a),4.55,z-u*Math.sin(a)+2.12*Math.cos(a),.16,.35,'ivory',4);}
  }
  // Cross channels are level with the paving and remain traversable.
  b.box(x,.006,z,34,.018,.16,'water');b.box(x,.006,z,.16,.018,24,'water');
  for(const side of [-1,1]){b.box(x,.008,z+side*.15,34,.015,.12,'marble');b.box(x+side*.15,.008,z,.12,.015,24,'marble');}
  lionFountain(b,x,z);
  b.floor(19,18,6,21);b.wall(22,18,21,5.8,.65,4,'plaster',Math.PI/2);
  b.wall(16,9,3,5.8,.65,0,'plaster',Math.PI/2);b.wall(16,21,15,5.8,.65,0,'plaster',Math.PI/2);b.arch(16,12,3,2.25,1.5,5.8,.65,'plaster',Math.PI/2);
  b.wall(19,7.5,6,5.8,.65,2.2);b.wall(19,28.5,6,5.8,.65,0);b.box(19,5.8,18,6,.18,21,'wood');b.roof(19,18,7,22,6,2);
  room(b,59,18,6,27,6.1,{w:4,s:2.4});
  for(const zz of [9,18,27]){b.arch(59,zz,5.6,3.4,1.8,6.1,.5,'plaster');for(const sx of [-1,1])b.column(59+sx*2.45,zz,3.4,.18);}
  // Side access from Comares to the Hall of Muqarnas.
  b.floor(13.4,12,7,6);b.wall(13.4,9,7,5.5,.5,0);b.wall(13.4,15,7,5.5,.5,0);b.box(13.4,5.5,12,7,.2,6,'wood');
  b.zone='sisters';
  detailedSisters(b);
  room(b,31.3,1.3,5,8.3,5.6,{e:2.5,tile:'sTile',wallMaterial:'fineStucco',ceiling:false});room(b,44.7,1.3,5,8.3,5.6,{w:2.5,tile:'sTile',wallMaterial:'fineStucco',ceiling:false});for(const xx of [31.3,44.7])b.roof(xx,1.3,5.4,9.3,5.8,2);
  b.floor(38,6.5,4,3);b.box(38,5.6,6.5,4,.2,3,'wood');
  b.wall(36,6.4,3,5.8,.4,0,'plaster',Math.PI/2);b.wall(40,6.4,3,5.8,.4,0,'plaster',Math.PI/2);
  bassin(b,38,1.3,.56);b.box(38,.01,4.4,.14,.02,7.8,'water');
  for(const xx of [-1,1])b.box(38+xx*1.4,.009,1.3,1.7,.012,3.6,'marble');
  // The Ajimeces hall and the projecting belvedere.
  room(b,38,-6.1,16,4.6,5.8,{s:2.8,n:2.4});room(b,38,-10.2,4.8,4,5.8,{s:2.4,n:3.5,e:2.3,w:2.3,ceiling:false,tile:'lindarajaTile'});
  b.box(38,5.8,-10.2,5,.2,4.2,'wood');b.roof(38,-10.2,5.8,5.0,6,1.5);
  b.column(38,-12.2,2.6,.10);b.arch(37.1,-12.2,1.65,2.6,1.0,4.8,.4);b.arch(38.9,-12.2,1.65,2.6,1.0,4.8,.4);
  b.box(38,0,-12.2,4.6,.8,.45,'lindarajaTile',0,true);
  b.zone='abencerrajes';
  room(b,38,34.5,8.2,7.2,6.7,{n:2.6,e:2.4,w:2.4,ceiling:false,tile:'abenTile'});
  b.floor(38,29.6,4,3.6);b.box(38,5.5,29.6,4,.2,3.6,'wood');
  for(const dx of [-1,1]){b.wall(38+dx*2,29.8,3.8,5.7,.5,0,'plaster',Math.PI/2,0,'abenTile');room(b,38+dx*6.1,34.5,4,7.2,5.4,{[dx<0?'e':'w']:2.4,tile:'abenTile'});}
  detailedAbencerrajes(b);

  b.roof(38,34.5,10,9.6,12.1,2.6);bassin(b,38,34.5,.85);
  b.zone='myrtles';
  b.floor(1.5,0,23.5,39);
  // The reflecting pool and its two myrtle hedges.
  b.box(1.5,-.08,0,7.4,.08,34.3,'dark');water.push({x:1.5,z:0,w:7.1,d:34,y:.015,reflect:true});
  b.nav.box(1.5,0,7.6,34.3,-1,.4);
  for(const s of [-1,1]){
    b.box(1.5+s*5.1,0,0,2.35,1,32.8,'hedge',0,true);b.box(1.5+s*3.7,0,0,.2,.12,34.5,'marble');
    myrtlesSide(b,s);
  }
  // Porticoes with seven bays, the centre wider than its neighbours.
  const xs=[-10.05,-7.1,-4.2,-1.7,4.7,7.2,10.1,13.05];
  for(const zz of [-18.3,18.3]){
    for(const xx of xs)b.column(xx,zz,2.95,.145);
    for(let i=0;i<7;i++)b.arch((xs[i]+xs[i+1])/2,zz,xs[i+1]-xs[i]-.12,2.95,i===3?1.9:1.2,5.3,.46);
    b.roof(1.5,zz,25.3,4.8,5.4,1.5);bassin(b,1.5,zz>0?18.9:-18.9,.62);
  }
  // Southern upper loggia.
  b.floor(1.5,21.3,25,5,5.6,'marble');for(let i=0;i<=9;i++)b.column(-10+i*2.55,19.2,2.35,.14,5.6);
  for(let i=0;i<9;i++)b.arch(-10+(i+.5)*2.55,19.2,2.45,2.35,.8,3.5,.4,'plaster',0,5.6);
  b.wall(1.5,23.8,25,9.2,.6,2.6,'ivory',0,0,null);b.roof(1.5,21.8,26,5.5,9.3,1.6);
  b.zone='comares';
  room(b,1.5,-23.5,24,5.2,6.1,{s:3,n:3,e:2.4,w:2.4});
  detailedComares(b);
  b.zone='mexuar';
  room(b,-29,-7,10,27,5.6,{s:2.7,n:2.3,e:3,tile:'mexuarTile'});
  for(const xx of [-31.5,-26.5])for(const zz of [-10,-3]){b.column(xx,zz,3.6,.21);}
  for(const zz of [-10,-3])b.box(-29,3.6,zz,6,.55,.6,'wood');for(const xx of [-31.5,-26.5])b.box(xx,3.6,-6.5,.5,.5,7,'wood');
  b.floor(-18.3,-15,10.3,11);b.wall(-18.3,-20.5,11,6,.6,3,'plaster');b.wall(-18.3,-9.5,11,7,.6,2.6,'plaster');
  b.wall(-23.5,-15,11,6,.5,3,'plaster',Math.PI/2);b.wall(-13.1,-15,11,6,.5,3,'plaster',Math.PI/2);
  bassin(b,-18.3,-15,.7);b.floor(-16.5,-4.6,7.7,12);b.box(-16.5,5.8,-4.6,8,.2,12,'wood');
  b.wall(-20.5,1,11,5.8,.6,3,'plaster',Math.PI/2);
  // Small light sources represent diffuse sky reflected into the rooms, not visible fixtures.
  for(const p of [[38,6,34.5,8],[-29,4,-7,7],[59,4,22.6,9]]){
    const l=new THREE.PointLight(0xffe7bf,p[3]*2.5,24,1.5);l.position.set(...p.slice(0,3));lights.push(l);b.root.add(l);
  }
}

export function gardens(b,water){
  b.zone='partal';
  b.floor(98,18,60,85,0,'paving');
  b.box(102,0,0,15,.09,26,'dark');water.push({x:102,z:0,w:14.4,d:25.4,y:.10,reflect:true});b.nav.box(102,0,15,26,-1,.5);
  room(b,101,-20,24,7,5.2,{s:3.2,ceiling:false});
  const px=[90.5,94.5,98.5,103.5,107.5,111.5];for(const xx of px)b.column(xx,-14.7,2.95,.16);for(let i=0;i<5;i++)b.arch((px[i]+px[i+1])/2,-14.7,px[i+1]-px[i]-.15,2.95,i===2?1.85:1.45,5.05,.45,'plaster');b.roof(101,-18,25.3,8.2,5.2,2.5);
  b.wall(104,-26,9,13,.8,0,'redwall',0,0,null);b.wall(99.5,-22.5,7,13,.8,0,'redwall',Math.PI/2,0,null);b.wall(108.5,-22.5,7,13,.8,0,'redwall',Math.PI/2,0,null);b.wall(104,-19,9,13,.8,2.4,'redwall',0,0,null);b.roof(104,-22.5,11,9,13,2.2);
  for(const x of [78,122,145,164,184])for(const z of [28,49,69]){
    b.floor(x,z,14,15,0,'earth');for(const s of [-1,1]){b.box(x+s*7,0,z,.65,.65,15,'hedge',0,true);b.box(x,0,z+s*7.5,14,.65,.65,'hedge',0,true);}
    b.sphere(x,2.1,z,2,1.6,2,'tree');b.cylinder(x,0,z,.17,2,'trunk');
    for(let i=0;i<10;i++){const a=i*Math.PI/5;b.flowers(x+Math.cos(a)*4,.5,z+Math.sin(a)*4,i%3?'flower':'whiteFlower');}
  }
  // Lindaraja garden beneath the belvedere; raised borders and a central basin.
  b.floor(38,-24,23,23,0,'paving');for(const x of [31,45])for(const z of [-17,-31]){b.box(x,0,z,5,.55,5,'hedge',0,true);b.cone(x,.55,z,1,9,'cypress');b.cylinder(x,.55,z,.15,2,'trunk');}bassin(b,38,-24,1.2);
  b.zone='generalife';b.offset=[370,32,-52];
  b.floor(0,0,30,65,0,'paving');b.floor(0,0,13,49,0,'paving');
  b.box(0,0,0,2.3,.1,41,'dark');water.push({x:370,z:-52,w:2.0,d:41,y:32.11,reflect:true});b.nav.box(370,-52,2.3,41,31,32.5);
  for(const s of [-1,1]){
    for(const zz of [-18,-6,6,18]){const end=Math.abs(zz)===18;b.box(s*3.35,0,zz,3,.45,end?5:10,'hedge',0,true);for(let i=0;i<13;i++)b.flowers(s*(2.2+(i%3)*.85),.68,zz+(end?-1.6+Math.floor(i/3)*.8:-4+Math.floor(i/3)*1.8),i%3===0?'whiteFlower':'flower');}
    for(let zz=-20;zz<=20;zz+=2.7)b.jet(s*1.12,.24,zz,-s*1.6,.25,1.05);
    if(s<0){
      b.box(-7,0,0,.55,.65,49,'whiteLime',0,true);
      for(let zz=-24;zz<=24;zz+=4)b.box(-7,.65,zz,.55,3.55,.40,'whiteLime',0,true);
      for(let zz=-22;zz<=22;zz+=4){b.arch(-7,zz,3.6,2.7,1.1,4.8,.55,'whiteLime',Math.PI/2,0,false);b.arch(-6.70,zz,3.6,2.7,1.1,4.05,.035,'archBrick',Math.PI/2,0,false);}
      b.roof(-8.3,0,3.7,51,4.8,1.3);
    }else {b.wall(7,12.25,24.5,4.1,.55,0,'archBrick',Math.PI/2,0,null);b.wall(7,-12.25,24.5,4.1,.55,0,'whiteLime',Math.PI/2,0,null);b.roof(8.2,-12.25,3.2,25,4.1,.7);}
  }
  for(const zz of [-25,25]){room(b,0,zz,17,6,zz<0?4.9:6.2,{n:4,s:4,tile:'tileRibbon',ceiling:false});arcade(b,0,zz+(zz<0?3:-3),13,5,0,3,.12);b.roof(0,zz,19,8,zz<0?5.0:6.2,zz<0?.9:2);}
  room(b,0,-32,8,8,8,{s:3,n:3.5,wallMaterial:'whiteLime'});generalifeNorth(b);
  b.offset=[0,0,0];
  // Terraced lower gardens. Walk surfaces are joined by a broad, climbable stair.
  b.floor(370,-10,8,26,32,'paving');
  for(let row=0;row<5;row++){
    const zz=10+row*19,level=32-row*1.7;
    for(const xx of [349.5,390.5])b.floor(xx,zz,31,19,level,'paving');
    b.floor(370,zz,10,14,level,'paving');
    if(row<4){
      for(let step=0;step<10;step++)b.box(370,level-(step+1)*.17-.15,zz+7+(step+.5)*.5,10,.15,.52,'paving');
      b.nav.ramp(370,zz+9.5,10,5,level,level-1.7);
    }
    for(const xx of [346,394]){b.box(xx,level,zz,15,.7,13,'hedge',0,true);b.box(xx,level+.71,zz,12,.03,10,'earth');for(const sx of [-1,1])b.cone(xx+sx*5,level+.75,zz,1,6,'cypress');}
    for(const xx of [335,405])b.cone(xx,level,zz,1.2,9,'cypress');
  }
  for(let i=0;i<8;i++)b.box(370,25.2-(i+1)*.15-.15,94+i*2,10,.15,2.02,'paving');
  b.nav.ramp(370,101,10,16,25.2,24);b.floor(370,112,12,6,24,'paving');
}

export function charlesV(b){
  b.zone='charles';const x=-40,z=65,R=15.4; b.floor(x,z,63,63,0,'paving');
  for(const sign of [-1,1]){b.wall(x+sign*31.5,z,63,15.5,2.5,5.5,'brick',Math.PI/2,0,null);b.wall(x,z+sign*31.5,63,15.5,2.5,5.5,'brick',0,0,null);}
  // Square exterior, circular open courtyard, two orders of columns.
  const n=32;for(let i=0;i<n;i++){
    const a=i*Math.PI*2/n,px=x+Math.sin(a)*R,pz=z+Math.cos(a)*R;
    b.column(px,pz,5.0,.28,0,'ivory');b.column(px,pz,4.7,.25,6.3,'ivory');
    const an=a+Math.PI/n,seg=2*R*Math.tan(Math.PI/n);
    b.box(x+Math.sin(an)*R,5,z+Math.cos(an)*R,seg+.1,1.2,1.2,'ivory',an);
    b.box(x+Math.sin(an)*R,11,z+Math.cos(an)*R,seg+.1,1.2,1.2,'ivory',an);
    b.wall(x+Math.sin(a)*20,z+Math.cos(a)*20,4.2,12.3,1.2,i%8===0?3.0:0,'brick',a,0,null);
  }
  const ring=(inner,outer,y,mat)=>{const shape=new THREE.Shape();shape.moveTo(-31.5,-31.5);shape.lineTo(31.5,-31.5);shape.lineTo(31.5,31.5);shape.lineTo(-31.5,31.5);shape.closePath();const hole=new THREE.Path();hole.absarc(0,0,inner,0,Math.PI*2,true);shape.holes.push(hole);const g=new THREE.ShapeGeometry(shape,64);g.rotateX(-Math.PI/2);b.unique(g,mat,[x,y,z]);};
  ring(16,31,6.25,'paving');ring(20.8,31,15.5,'roof');
  for(const s of [-1,1])for(let i=0;i<12;i++){
    const u=-27+i*4.9;b.box(x+u,6.5,z+s*32,1.8,3,.2,'dark');b.box(x+s*32,6.5,z+u,.2,3,1.8,'dark');
    b.box(x+u,10.3,z+s*32,1.7,2,.2,'dark');b.box(x+s*32,10.3,z+u,.2,2,1.7,'dark');
  }
}
