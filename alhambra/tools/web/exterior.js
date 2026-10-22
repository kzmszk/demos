import * as THREE from 'three';
import { random } from './materials.js';
import { terrainHeight, insidePolygon } from './navigation.js';
import { room } from './palaces.js';

function segment(b,a,c,h=8,d=1.4,mat='redwall',base=0,crenels=true){
  const dx=c[0]-a[0],dz=c[1]-a[1],len=Math.hypot(dx,dz),rot=-Math.atan2(dz,dx),x=(a[0]+c[0])/2,z=(a[1]+c[1])/2;
  b.box(x,base,z,len,h,d,mat,rot,true);
  if(crenels)for(let t=.6;t<len;t+=1.45)b.box(a[0]+dx*t/len,base+h,c[1]-(1-t/len)*dz,.7,.85,.7,mat,rot);
}
function stairs(b,x,z,width,length,y0,y1,reverse=false){
  const steps=Math.ceil(Math.abs(y1-y0)/.18),depth=length/steps;
  for(let i=0;i<steps;i++){const y=y0+(y1-y0)*(i+1)/steps,zz=z+(reverse?-1:1)*(-length/2+(i+.5)*depth);b.box(x,y-.25,zz,width,.25,depth+.02,'paving');}
  b.nav.ramp(x,z,width,length,reverse?y1:y0,reverse?y0:y1);
}

function tower(b,x,z,w,d,h,open=false){
  if(open){b.floor(x,z,w,d);b.wall(x,z-d/2,w,h,1.0,0,'redwall',0,0,null);b.wall(x,z+d/2,w,h,1,0,'redwall',0,0,null);b.wall(x-w/2,z,d,h,1,0,'redwall',Math.PI/2,0,null);b.wall(x+w/2,z,d,h,1,3.2,'redwall',Math.PI/2,0,null);}
  else b.box(x,-4,z,w,h+4,d,'redwall',0,true);
  b.box(x-w/2+.5,h,z,1,.75,d,'redwall',0,true);b.box(x+w/2-.5,h,z,1,.75,d,'redwall',0,true);b.box(x,h,z-d/2+.5,w,.75,1,'redwall',0,true);b.box(x,h,z+d/2-.5,w,.75,1,'redwall',0,true);b.crenels(x,z,w,d,h+.75);
  if(open){
    // Opening above the last stair flight: walking down must remain possible.
    b.floor(x-4.15,z,11.7,d,h,'paving');b.floor(x+7.25,z,5.5,d,h,'paving');
    b.floor(x,z-9,w,2,h,'paving');b.floor(x,z+9,w,2,h,'paving');
  }else b.floor(x,z,w,d,h,'paving');
}
export function fortress(b){
  b.zone='alcazaba';
  b.floor(-185,22,97,42,0,'earth');
  const poly=[[-239,12],[-209,12],[-205,24],[-145,-11],[-137,-11],[-139,42],[-231,45],[-239,12]];
  for(let i=1;i<poly.length;i++){
    if(i===5){segment(b,poly[i-1],[-138,21],10,2.1);segment(b,[-138,25],poly[i],10,2.1);b.arch(-138,23,4,2.4,2,10,2.1,'redwall',Math.PI/2,0,false);}
    else segment(b,poly[i-1],poly[i],10,2.1);
  }
  // Continuous wall walk with a protected inside parapet.
  b.box(-184,0,41.3,85,10,3.7,'redwall',0,true);b.floor(-184,40.2,85,2.4,10,'paving');segment(b,[-226,39],[-148,39],.9,.35,'redwall',10,false);
  stairs(b,-146,30.3,2.2,17,0,10,false);b.floor(-146,39.9,4,3,10,'paving');
  tower(b,-228,24,20,20,26,true);
  // Five alternating internal flights, with broad landings at each end.
  for(let f=0;f<5;f++){
    const xx=-228+(f%2?-3.1:3.1);stairs(b,xx,24,2.4,15,f*5.2,(f+1)*5.2,f%2===0);
    b.floor(-228,24+(f%2===0?-8:8),12,2,(f+1)*5.2,'paving');
    // Rail follows the stair edge without obstructing walking.
    b.line([xx-1.3,f*5.2+.9,24+(f%2===0?7.5:-7.5)],[xx-1.3,(f+1)*5.2+.9,24+(f%2===0?-7.5:7.5)],.045,'dark');
  }
  // Bell gable at the summit of Torre de la Vela.
  b.box(-234,26,-0+19,1,4.8,1,'brick');b.box(-229,26,19,1,4.8,1,'brick');b.arch(-231.5,19,4,2.2,1.5,4.8,.7,'brick',0,26,false);b.roof(-231.5,19,7,3,30.8,1.2);b.cylinder(-231.5,28.8,19,.52,.8,'dark',.22,20);
  for(const xx of [-233,-230,-227]){b.cylinder(xx,26,30,.035,5.2,'dark');b.box(xx+.6,29.8,30,1.25,.85,.03,xx===-230?'gold':'redwall');}
  tower(b,-137,-17,13,13,24);tower(b,-143,41,11,10,19);tower(b,-211,-10,10,11,15);
  // Archaeological house walls, left deliberately roofless.
  for(const [x,z,w,d] of [[-197,18,11,8],[-184,12,10,9],[-170,6,9,8],[-157,0,9,8],[-201,35,10,8],[-187,35,10,8],[-173,35,10,8],[-159,35,10,8]]){
    const h=1.05;b.wall(x,z-d/2,w,h,.5,0,'rubble',0,0,null);b.wall(x,z+d/2,w,h,.5,1.5,'rubble',0,0,null);b.wall(x-w/2,z,d,h,.5,0,'rubble',Math.PI/2,0,null);b.wall(x+w/2,z,d,h,.5,0,'rubble',Math.PI/2,0,null);b.wall(x,z,Math.max(2,w*.45),h,.45,0,'rubble',Math.PI/2,0,null);b.floor(x,z,w,d,.02,'paving');
  }
  b.box(-176,0,25,12,.1,2,'paving');
  // The Adarves garden, along the southern defensive wall.
  b.floor(-183,51,88,8,0,'paving');for(let i=0;i<12;i++){const x=-225+i*7.5;b.box(x,0,54.0,5,.65,2.5,'hedge',0,true);for(const dx of [-1.5,0,1.5])b.flowers(x+dx,.8,54,'flower');}
  b.floor(-107,36,42,63,0,'paving');room(b,-93,67,11,12,9.0,{n:3.5,s:3.5,tile:null});b.roof(-93,67,12,13,9.2,1.8);
  b.zone='justice';b.floor(-55,132,36,40,0,'paving');
  b.wall(-55,123,18,20,3.3,5,'redwall',0,0,null);b.wall(-55,113,18,20,3,4,'redwall',0,0,null);b.wall(-64,118,10,20,2,0,'redwall',Math.PI/2,0,null);b.wall(-46,118,10,20,2,0,'redwall',Math.PI/2,0,null);b.box(-55,20,118,19,.5,13,'paving');b.crenels(-55,118,18,12,20.5);
  b.arch(-55,124.8,6.5,3.2,4.2,11,.12,'ivory',0,0,false);b.arch(-55,124.9,5,3.2,3.8,10,.08,'redwall',0,0,false);
}

export function exterior(b,ctx,low=false){
  const rand=random(9001);
  b.zone='landscape';
  const ground=new THREE.PlaneGeometry(2400,2200,170,155);ground.rotateX(-Math.PI/2);
  const colors=[],pos=ground.attributes.position;
  for(let i=0;i<pos.count;i++){
    const x=pos.getX(i),z=pos.getZ(i),h=terrainHeight(x,z)-.22;pos.setY(i,h);
    const c=new THREE.Color().setHSL(.19+rand()*.035,.26+rand()*.12,.21+rand()*.06);colors.push(c.r,c.g,c.b);
  }
  ground.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));ground.computeVertexNormals();
  const groundMat=new THREE.MeshStandardMaterial({vertexColors:true,roughness:1});groundMat.name='terrain';b.m.terrain=groundMat;const gm=new THREE.Mesh(ground,groundMat);gm.receiveShadow=true;b.root.add(gm);
  // Level palace platform traced from the OSM perimeter, above the wooded slope.
  const boundary=ctx.perimeter;
  const shape=new THREE.Shape();boundary.forEach(([x,z],i)=>i?shape.lineTo(x,-z):shape.moveTo(x,-z));shape.closePath();const platform=new THREE.ShapeGeometry(shape);platform.rotateX(-Math.PI/2);b.unique(platform,'earth',[0,-.04,0]);
  for(let i=0;i<boundary.length;i++){
    const a=boundary[i],c=boundary[(i+1)%boundary.length],mx=(a[0]+c[0])/2,mz=(a[1]+c[1])/2;
    if(mx<-130 || (mx>-67&&mx<140&&mz<35) || Math.hypot(mx+55,mz-123)<18 || Math.hypot(mx-370,mz-180)<13)continue;
    const dx=c[0]-a[0],dz=c[1]-a[1],len=Math.hypot(dx,dz);
    const t=((396-a[0])*dx+(208-a[1])*dz)/(len*len),gx=a[0]+dx*t,gz=a[1]+dz*t;
    if(t>0&&t<1&&Math.hypot(gx-396,gz-208)<2){
      // Interpretive eastern visitor connection, beside the access-pavilion end of the wall.
      const before=[gx-dx/len*4.5,gz-dz/len*4.5],after=[gx+dx/len*4.5,gz+dz/len*4.5];
      segment(b,a,before,7.5,1.5);segment(b,after,c,7.5,1.5);b.arch(gx,gz,9,3.8,2.8,7.5,1.5,'redwall',-Math.atan2(dz,dx),0,false);
    }else if(len>.6)segment(b,a,c,7.5,1.5);
  }
  // Northern retaining wall below the palace windows.
  segment(b,[-126,-28],[-7,-39],20,2,'redwall',-23);segment(b,[10,-39],[41,-40],18,1.8,'redwall',-22);
  // Walkable connections through the planted eastern grounds.
  const gardenPath=[[70,40],[70,97],[200,97],[200,252],[350,252],[380,240],[396,218],[396,202],[385,185],[370,177]];
  for(let i=1;i<gardenPath.length;i++){
    const a=gardenPath[i-1],c=gardenPath[i],dx=c[0]-a[0],dz=c[1]-a[1];b.floor((a[0]+c[0])/2,(a[1]+c[1])/2,Math.hypot(dx,dz)+4,6,0,'paving',-Math.atan2(dz,dx));
  }
  stairs(b,370,145,8,64,24,0);b.floor(370,112,10,5,24,'paving');b.floor(370,178,10,6,0,'paving');
  // Church of Santa María, the historic street and small service buildings.
  b.zone='church';
  b.box(39,0,93,13,13,39,'ivory',0,true);b.roof(39,93,15,41,13,5);b.box(39,0,85,33,12,12,'ivory',0,true);b.roof(39,85,35,14,12,3);b.box(46,0,80,9,26,9,'brick',0,true);b.roof(46,80,11,11,26,5);
  for(const x of [35,43]){b.box(x,3,113,2,3,.05,'dark');b.arch(x,113.1,2.4,5,1.4,7,.1,'brick');}
  b.zone='context';let count=0;
  for(const f of ctx.buildings){
    const p=f.p,cx=p.reduce((s,v)=>s+v[0],0)/p.length,cz=p.reduce((s,v)=>s+v[1],0)/p.length;
    // Hand-modelled monuments replace, rather than overlap, their generic extrusion.
    if(cx>-265&&cx<152&&cz>-70&&cz<157)continue;
    if(cx>324&&cx<416&&cz>-115&&cz<112)continue;
    if(f.id===26935518 || /Silla del Moro/.test(f.name))continue;
    if(low && ++count%2===0 && Math.hypot(cx,cz)>550)continue;
    const h=f.h,base=insidePolygon(cx,cz,boundary)?0:terrainHeight(cx,cz);
    const shape=new THREE.Shape();p.forEach(([x,z],i)=>i?shape.lineTo(x,-z):shape.moveTo(x,-z));shape.closePath();
    const geo=new THREE.ExtrudeGeometry(shape,{depth:h,bevelEnabled:false});geo.rotateX(-Math.PI/2);b.unique(geo,'city',[0,base,0]);
    const roof=new THREE.ShapeGeometry(shape);roof.rotateX(-Math.PI/2);b.unique(roof,'roof',[0,base+h+.05,0]);
    if(insidePolygon(cx,cz,boundary)){
      const minX=Math.min(...p.map(v=>v[0])),maxX=Math.max(...p.map(v=>v[0])),minZ=Math.min(...p.map(v=>v[1])),maxZ=Math.max(...p.map(v=>v[1]));
      b.nav.box((minX+maxX)/2,(minZ+maxZ)/2,maxX-minX,maxZ-minZ,base,base+h);
    }
  }
  b.zone='grounds';
  // Parador / former Franciscan convent: courtyard wings and tiled roofs.
  for(const [x,z,w,d] of [[166,110,48,10],[166,143,48,10],[145,126,10,32],[187,126,10,32]]){b.box(x,0,z,w,9,d,'ivory',0,true);b.roof(x,z,w+1,d+1,9,3);}
  b.floor(166,126,32,23,0,'paving');
  for(let j=0;j<4;j++)for(let i=0;i<7;i++){
    const x=214+i*20,z=165+j*25;
    if(!insidePolygon(x,z,boundary))continue;
    b.box(x,0,z,15,.55,18,'hedge',0,true);b.box(x,.55,z,12,.02,15,'earth');
    b.cone(x,0,z,1.25,8.5,'cypress');
  }
  // Trees are deterministic, batched and excluded from buildings and open courts.
  b.zone='forest';
  const trees=low?900:3500;
  for(let i=0;i<trees;i++){
    const x=-400+rand()*1080,z=-200+rand()*760;
    const main=insidePolygon(x,z,boundary),general=x>318&&x<430&&z>-132&&z<195;
    if(main || general || (x<0&&z<-110))continue;
    if(Math.abs(x-370)<12&&z>105&&z<205)continue;
    const y=terrainHeight(x,z),h=4+rand()*8;
    b.cylinder(x,y,z,.16,h*.45,'trunk',.11,7);
    if(rand()>.55){b.cone(x,y+1,z,h*.14,h,'cypress',9);b.cone(x,y+2,z,h*.12,h*.88,'cypress',9);}
    else {b.sphere(x,y+h*.65,z,h*.35,h*.44,h*.31,'tree');b.sphere(x+h*.18,y+h*.55,z+h*.12,h*.26,h*.28,h*.29,'hedge');}
  }
  for(let i=0;i<40;i++){
    const x=120+i*6,z=80+i*2.5;if(i>9&&i<18)continue;b.cone(x,0,z,1.25,8+rand()*3,'cypress');
  }
  // Distant, low-contrast Sierra foothills; never presented as measured topography.
  const hillMat=new THREE.MeshStandardMaterial({color:0x7c8c7a,roughness:1});
  const hills=new THREE.PlaneGeometry(5200,3000,104,60);hills.rotateX(-Math.PI/2);
  const hp=hills.attributes.position;
  for(let i=0;i<hp.count;i++){
    const x=hp.getX(i),z=hp.getZ(i),ridge=Math.exp(-(((z+80)/730)**2));
    const envelope=Math.max(0,1-(x/2600)**6);
    const shape=300+100*Math.sin(x*.0021)+70*Math.cos(x*.0062)+35*Math.sin(x*.014+z*.004);
    hp.setY(i,-76+ridge*envelope*shape);
  }
  hills.computeVertexNormals();const distant=new THREE.Mesh(hills,hillMat);distant.position.set(2500,-60,2200);b.root.add(distant);
  const horizon=new THREE.Mesh(new THREE.PlaneGeometry(12000,12000),hillMat);horizon.rotation.x=-Math.PI/2;horizon.position.y=-77;b.root.add(horizon);
  return groundMat;
}
