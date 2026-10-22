import * as THREE from 'three';

const PI=Math.PI;
let trim='sLime'; // frame/fillet material; rooms may switch it while they build
function frame(cx,cz,r,a){const x=cx+Math.sin(a)*r,z=cz+Math.cos(a)*r;return {a,x,z,at:(u,v=0)=>[x+u*Math.cos(a)+v*Math.sin(a),z-u*Math.sin(a)+v*Math.cos(a)]};}
function box(b,f,u,y,v,w,h,d,mat,block=false){const [x,z]=f.at(u,v);b.box(x,y,z,w,h,d,mat,f.a,block);}
function band(b,f,y,w,mat,h=.35,v=-.34){box(b,f,0,y,v,w,h,.028,mat);for(const dy of [-.025,h])box(b,f,0,y+dy,v-.022,w,.028,.065,trim);}
function panel(b,f,u,y,w,h,mat,v=-.34){box(b,f,u,y,v,w,h,.025,mat);for(const s of [-1,1]){box(b,f,u+s*(w/2+.035),y,v-.035,.045,h,.065,trim);box(b,f,u,y+(s<0?-.045:h),v-.035,w+.12,.045,.065,trim);}}
function screenMaterial(b){if(b.m.lattice)return;
 const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d');g.fillStyle='white';g.fillRect(0,0,512,512);g.fillStyle='black';
 for(let y=16;y<512;y+=32)for(let x=16;x<512;x+=32){g.beginPath();for(let i=0;i<16;i++){const a=i*PI/8,r=i%2?7.5:11.5;const u=x+Math.cos(a)*r,v=y+Math.sin(a)*r;i?g.lineTo(u,v):g.moveTo(u,v);}g.closePath();g.fill();g.fillRect(x+14.5,y-2.5,3.5,5);}
 const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(1,1.8);t.anisotropy=8;
 const m=new THREE.MeshStandardMaterial({color:0xc4b393,roughness:.87,alphaMap:t,alphaTest:.5,side:THREE.DoubleSide});m.userData={scale:1,interiorAmbient:.55};m.name='lattice';b.m.lattice=m;
}
function window(b,f,u,y,w,h,v=.05){screenMaterial(b);const [x,z]=f.at(u,v),spring=h-w/2;
 const shape=new THREE.Shape();shape.moveTo(-w/2,0);shape.lineTo(w/2,0);shape.lineTo(w/2,spring);shape.absarc(0,spring,w/2,0,PI,false);shape.lineTo(-w/2,0);
 const geo=new THREE.ShapeGeometry(shape,16),uv=geo.attributes.uv,pos=geo.attributes.position;for(let i=0;i<uv.count;i++)uv.setXY(i,pos.getX(i)/w+.5,pos.getY(i)/h);
 b.unique(geo,'lattice',[x,y,z],f.a);
 for(const s of [-1,1])box(b,f,u+s*(w/2+.07),y,v,.12,h,.24,trim);
 box(b,f,u,y-.10,v,w+.26,.1,.30,trim);
 const points=[];for(let i=0;i<=20;i++){const a=i*PI/20;const p=f.at(u+Math.cos(a)*(w/2+.055),v-.035);points.push([p[0],y+spring+Math.sin(a)*(w/2+.055),p[1]]);}for(let i=1;i<points.length;i++)b.line(points[i-1],points[i],.045,trim);
}
function portalLight(b,f,y,power=12){const [x,z]=f.at(0,-.75);const l=new THREE.PointLight(0xe3ebff,power,16,1.6);l.position.set(x,y,z);b.root.add(l);}
function sunPatch(b,cx,cz,r,y){
 // A narrow, room-local shadow camera resolves the actual perforated screens.
 // Static geometry: update once rather than rendering the palace a second time each frame.
 const l=new THREE.SpotLight(0xffe4b8,220,30,.54,.30,1.5);l.position.set(cx-r-2,y+2,cz-2);l.target.position.set(cx+2,.1,cz+1);l.castShadow=true;l.shadow.mapSize.set(1024,1024);l.shadow.bias=-.00015;l.shadow.normalBias=.018;l.shadow.camera.near=.3;l.shadow.camera.far=30;l.shadow.autoUpdate=false;l.shadow.needsUpdate=true;b.root.add(l,l.target);
}
export function detailedComares(b){const cx=1.5,cz=-34.8,r=5.75;
 b.floor(cx,cz,11.5,11.5,0,'terracotta');
 for(let side=0;side<4;side++){
  const f=frame(cx,cz,r,side*PI/2);
  if(side===0){const [x,z]=f.at(0);b.wall(x,z,11.5,8.8,.6,3,'fineStucco',f.a,0,null);for(const u of [-3.7,3.7]){panel(b,f,u,.08,4.1,1.35,'cTile');panel(b,f,u,2.15,3.9,2,'cCarving');}}
  else{
   for(const u of [-5.15,-1.8,1.8,5.15]){const w=Math.abs(u)>5?1.2:1.3;box(b,f,u,0,.9,w,8.8,2.4,'fineStucco',true);panel(b,f,u,.08,w-.08,1.35,'cTile');panel(b,f,u,2.05,w-.14,2.25,'cCarving');}
   for(const u of [-3.5,0,3.5]){const [x,z]=f.at(u);b.arch(x,z,2.2,2.9,1.45,8.8,.62,'fineStucco',f.a);const [ax,az]=f.at(u,1.25);b.floor(ax,az,2.2,2.9,0,'terracotta',f.a);
    box(b,f,u,4.4,1.25,2.25,.20,2.9,'cCarving');box(b,f,u,3.88,2.5,2.28,.58,.38,'fineStucco');for(const sg of [-1,1]){box(b,f,u+sg*1.05,.08,1.25,.025,1.35,2.5,'cTile');box(b,f,u+sg*1.05,1.48,1.25,.035,.18,2.5,'sBorder');}box(b,f,u,0,2.5,2.2,.75,.35,'cTile',true);
    for(const e of [-1,0,1])box(b,f,u+e*1.08,.75,2.5,.10,3.15,.38,'cLime');for(const s of [-1,1]){const [px,pz]=f.at(u+s*.55,2.5);b.arch(px,pz,1.03,2.05,.51,3.9,.3,'fineStucco',f.a,.75,false);window(b,f,u+s*.55,.80,.91,2.62,2.52);}
    const [px,pz]=f.at(u,2.5);b.column(px,pz,2.05,.065,.75);
   }
  }
  for(const u of side===0?[-3.7,3.7]:[-5.15,-1.8,1.8,5.15]){const w=side===0?4.1:(Math.abs(u)>5?1.12:1.22);panel(b,f,u,1.44,w,.18,'sBorder');panel(b,f,u,1.72,w,.30,'cEpigraphy');}
  band(b,f,4.55,11.45,'cEpigraphy',.40);panel(b,f,0,5.08,11.25,1.45,'cCarving');band(b,f,6.70,11.45,'cEpigraphy',.32);
  panel(b,f,0,7.17,11.25,1.33,'fineStucco');band(b,f,8.55,11.45,'cEpigraphy',.30);
  // Five pierced clerestory windows, separated by deeply carved piers.
  for(let k=0;k<5;k++){const u=(k-2)*2.05;const [x,z]=f.at(u);b.arch(x,z,1.04,1.25,.52,2.5,.6,'fineStucco',f.a,8.9,false);window(b,f,u,8.95,.98,1.72);}
  for(let k=0;k<6;k++)box(b,f,(k-2.5)*2.05,8.9,0,k===0||k===5?.64:1.01,2.5,.6,'fineStucco');
  band(b,f,11.15,11.55,'cedar',.35,-.44);
  for(let k=0;k<72;k++)box(b,f,-5.6+k*.158,10.95,-.42,.075,.18,.13,'cLime');
  portalLight(b,f,9.4,6);
 }
 // Hip ceiling in three inclinations, with world-scale UVs for the cedar inlay.
 const radii=[5.80,5.32,2.6,.5],ys=[11.5,12.5,16.65,17.75];
 for(let side=0;side<4;side++)for(let j=0;j<3;j++){
  const a=side*PI/2,f=frame(cx,cz,0,a),vs=[],uv=[];
  const coords=[[-radii[j],ys[j],radii[j]],[radii[j],ys[j],radii[j]],[-radii[j+1],ys[j+1],radii[j+1]],[radii[j+1],ys[j+1],radii[j+1]]];
  for(const i of [0,2,1,1,2,3]){const [u,y,v]=coords[i],p=f.at(u,v);vs.push(p[0],y,p[1]);uv.push(u,y*1.2);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vs,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();b.add(g,'cedar');
  for(const s of [-1,1]){const p=f.at(s*radii[j],radii[j]),q=f.at(s*radii[j+1],radii[j+1]);b.line([p[0],ys[j]-.025,p[1]],[q[0],ys[j+1]-.025,q[1]],.055,'cLime');}
 }
 b.box(cx,17.75,cz,1,.12,1,'cedar');
 b.box(cx,20,cz,16.7,.4,16.7,'paving');b.crenels(cx,cz,16.6,16.6,20.4);
 // The outer tower above the window zone; its lower wall remains open at the embrasures.
 for(let side=0;side<4;side++){const f=frame(cx,cz,7.45,side*PI/2);box(b,f,0,11.5,0,16.3,8.5,1.3,'redwall');box(b,f,0,-23,0,16.3,23,1.3,'redwall');}
 for(let side=0;side<4;side++){const f=frame(cx,cz,8.45,side*PI/2);if(side===0){const [x,z]=f.at(0);b.wall(x,z,16.3,8.9,.30,3,'redwall',f.a,0,null);}else{for(const [u,w] of [[-6.375,3.55],[-1.75,1.30],[1.75,1.30],[6.375,3.55]])box(b,f,u,0,0,w,8.9,.30,'redwall');box(b,f,0,3.88,0,16.3,5.02,.30,'redwall');box(b,f,0,0,0,16.3,.75,.30,'redwall');}for(const [u,w] of [[-6.385,3.53],[-3.075,1.01],[-1.025,1.01],[1.025,1.01],[3.075,1.01],[6.385,3.53]])box(b,f,u,8.9,0,w,2.6,.30,'redwall');box(b,f,0,10.72,0,16.3,.78,.30,'redwall');}
 sunPatch(b,cx,cz,r,9);
}

export function nicheGeometry(){const v=[],uv=[],colors=[];const p=(i,j)=>{const a=PI*i/8,t=j/4,r=1-.88*t;return [Math.cos(a)*r*.5,Math.sin(a)*r*.65+t*.65,t*.60];};
 for(let j=0;j<4;j++)for(let i=0;i<8;i++)for(const q of [p(i,j),p(i,j+1),p(i+1,j),p(i+1,j),p(i,j+1),p(i+1,j+1)]){v.push(...q);uv.push(q[0],q[1]);const shade=.98-.60*Math.pow(q[2]/.60,.7);colors.push(shade,shade*.98,shade*.94);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(v,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));g.computeVertexNormals();return g;
}
// About one cell in four is a deeper recess and one in fourteen keeps green-turquoise paint.
const sisTint=(i,j,k)=>{const h=Math.abs(Math.sin(i*12.9898+j*78.233+k*37.719)*43758.5453)%1;return h<.07?'sisCellGreen':h<.32?'sisCellShade':'sisCell';};
function vault(b,cx,cz){const cell=b.geometry('sisters-concave-niche',nicheGeometry),levels=18;
 for(let j=0;j<levels;j++){const t=j/levels,r=4.05*(1-t*.96),y=8.65+4.9*(1-(1-t)**1.3),per=Math.max(2,Math.round(16*(1-t))),w=2*r*Math.tan(PI/8)/per;
  for(let side=0;side<8;side++){const f=frame(cx,cz,r,side*PI/4);
   // Backing terraces cover every gap, with small vertical risers instead of long cones.
   box(b,f,0,y+.60,.10,2*r*Math.tan(PI/8)+.10,.24,.70,'sisPlaster');
   // Odd tiers sit half a cell over, so the cells interlock as in the real vault instead of forming rings.
   const odd=j%2&&per>2;for(let k=0;k<per-(odd?1:0);k++){const u=(k+(odd?1:.5)-per/2)*w,p=f.at(u);b.add(cell,sisTint(side,j,k),[p[0],y,p[1]],[w*1.12,.86,.52],f.a);b.stats.muqarnas++;
    const q=f.at(u+w*.48,-.13);b.add(cell,sisTint(side,j,k+31),[q[0],y+.22,q[1]],[w*.86,.48,.40],f.a);b.stats.muqarnas++;
    for(const s of [-1,1]){const z=f.at(u+s*w*.46,-.025);b.line([z[0],y,z[1]],[z[0],y+.20,z[1]],.012,'sisPlaster');}
   }
  }
 }
 for(const [radius,y,size] of [[3.55,8.95,.46],[2.65,10.55,.35],[1.55,12.0,.26]])for(let sector=0;sector<8;sector++){const a=sector*PI/4,px=cx+Math.sin(a)*radius,pz=cz+Math.cos(a)*radius;for(let k=0;k<8;k++){const q=k*PI/4;b.add(cell,k%2?'sisCellShade':'sisCell',[px+Math.sin(q)*size,y,pz+Math.cos(q)*size],[size*.88,.60,size*.7],q);b.stats.muqarnas++;}b.cylinder(px,y+.52,pz,size*.7,.08,'sisRecess',size*.7,8);}
 b.cylinder(cx,13.45,cz,.45,.18,'sisPlaster',.45,16);
}
export function detailedSisters(b){const cx=38,cz=1.3,r=4.15;trim='sisTrim';
 b.floor(cx,cz,8.3,8.3);
 for(let side=0;side<4;side++){
  const f=frame(cx,cz,r,side*PI/2),door=side%2?2.5:2.8,[x,z]=f.at(0);
  b.wall(x,z,8.3,7.1,.65,door,'sisSebka',f.a,0,null);
  for(const s of [-1,1]){const u=s*(door/4+2.075),w=(8.3-door)/2-.12;panel(b,f,u,.06,w,1.40,'sTile');panel(b,f,u,1.72,w,1.10,'sisSebka');panel(b,f,u,3.45,w,1.5,'sisSebka');}
  // Continuous inscription and carved strapwork mark the horizontal wall registers.
  for(const sign of [-1,1]){const u=sign*(door/4+2.075),w=(8.3-door)/2-.12;panel(b,f,u,1.47,w,.19,'sBorder');panel(b,f,u,2.94,w,.43,'sEpigraphy');}band(b,f,5.18,8.25,'sRibbon',.17);band(b,f,6.58,8.25,'sEpigraphy',.36);
  panel(b,f,0,3.7,2.3,1.32,'sCarving');
  window(b,f,0,5.45,1.2,1.02,-.38);
  // Hanging muqarnas: a fan spilling from each corner over both walls and a lobed curtain over the
  // central window, as in the hall photograph; pendants hang from the lower tiers.
  const fan=(c,half,base,tiers,seed)=>{for(let j=0;j<tiers;j++){const span=half*(1-j/(tiers+2)),n=Math.max(3,Math.round(span/.12));for(let k=0;k<=n;k++){
   const t=k/n,u=c+(t*2-1)*span,drop=Math.cos((t*2-1)*PI/2)**.8,y=base+j*.2+(1-drop)*(tiers-j)*.06+(k%2)*.07,p=f.at(u,-.36-j*.11-drop*.08);
   if(Math.abs(u)>4.12)continue;
   b.add(b.geometry('sisters-concave-niche',nicheGeometry),sisTint(seed,j,k),[p[0],y,p[1]],[.22,.30,.22],f.a);b.stats.muqarnas++;
   if(j<3&&k%2===0){const q=f.at(u,-.44-j*.11);b.cone(q[0],y-.17,q[1],.026,.17,'sisTrim',5);}
  }}};
  for(const s of [-1,1])fan(s*4.15,2.3,4.95,9,side*3+(s+1)/2);
  fan(0,1.55,5.05,6,side*3+2);
  // Pilaster bands framing the corners and the door, carved in relief.
  for(const u of [-4.02,4.02,-(door/2+.18),door/2+.18])box(b,f,u,.0,-.36,.16,4.7,.06,'sisSebka');
 }
 const transition=new THREE.Shape();transition.moveTo(-4.5,-4.5);transition.lineTo(4.5,-4.5);transition.lineTo(4.5,4.5);transition.lineTo(-4.5,4.5);transition.closePath();const hole=new THREE.Path();for(let i=0;i<8;i++){const a=(i+.5)*PI/4,x=Math.sin(a)*4.02/Math.cos(PI/8),y=Math.cos(a)*4.02/Math.cos(PI/8);i?hole.lineTo(x,y):hole.moveTo(x,y);}hole.closePath();transition.holes.push(hole);const tg=new THREE.ExtrudeGeometry(transition,{depth:.24,bevelEnabled:false});tg.rotateX(PI/2);b.add(tg,'sisStucco',[cx,7.2,cz]);
 // Sixteen real apertures in an octagonal clerestory.
 for(let side=0;side<8;side++){
  const f=frame(cx,cz,3.98,side*PI/4),width=2*3.98*Math.tan(PI/8);
  box(b,f,0,7.10,0,width+.12,.35,.45,'sCarving');
  for(const u of [-.78,.78]){const [x,z]=f.at(u);b.arch(x,z,.84,.82,.42,1.35,.4,'sisStucco',f.a,7.48,false);window(b,f,u,7.48,.79,1.2);}
  for(const [u,w] of [[0,.70],[-1.45,.52],[1.45,.52]])box(b,f,u,7.45,0,w,1.40,.45,'sisStucco');
  band(b,f,8.82,width,'sRibbon',.14,-.26);portalLight(b,f,8,2.4);
 }
 for(let side=0;side<8;side++){const f=frame(cx,cz,4.32,side*PI/4),w=2*4.32*Math.tan(PI/8);box(b,f,0,6.45,0,w+.08,1,.22,'sisStucco');box(b,f,0,8.82,0,w+.08,5.28,.22,'sisStucco');for(const [u,pw] of [[0,.70],[-1.58,.76],[1.58,.76]])box(b,f,u,7.45,0,pw,1.37,.22,'sisStucco');for(const u of [-.78,.78]){const [x,z]=f.at(u);b.arch(x,z,.84,.82,.42,1.37,.22,'sisStucco',f.a,7.45,false);}}
 trim='sLime';vault(b,cx,cz);b.roof(cx,cz,10.5,10.5,14.1,2.4);sunPatch(b,cx,cz,r,8);
}

// Abencerrajes has an eight-pointed star, distinct from the Sisters' octagon.
// The geometry follows the photographed silhouette; individual cells are an
// interpretive reconstruction, not a measured conservation model.
export function detailedAbencerrajes(b){
 // About one cell in nine keeps faded blue paint and one in four sits in deeper shade, as in the photographs.
 const tint=(i,j,k)=>{const h=Math.abs(Math.sin(i*12.9898+j*78.233+k*37.719)*43758.5453)%1;return h<.08?'abenCellBlue':h<.36?'abenCellShade':'abenCell';};
 const cx=38,cz=34.5,cell=b.geometry('sisters-concave-niche',nicheGeometry);
 const points=Array.from({length:16},(_,i)=>{const a=i*PI/8,r=i%2?2.8:3.55;return [Math.sin(a)*r,Math.cos(a)*r];});
 const edge=(i,scale=1)=>{const p=points[i],q=points[(i+1)%16],dx=q[0]-p[0],dz=q[1]-p[1];return {a:Math.atan2(-dz,dx),w:Math.hypot(dx,dz)*scale,x:cx+(p[0]+q[0])*.5*scale,z:cz+(p[1]+q[1])*.5*scale};};
 const shape=new THREE.Shape();shape.moveTo(-4.15,-3.65);shape.lineTo(4.15,-3.65);shape.lineTo(4.15,3.65);shape.lineTo(-4.15,3.65);shape.closePath();const hole=new THREE.Path();points.forEach((p,i)=>i?hole.lineTo(...p):hole.moveTo(...p));hole.closePath();shape.holes.push(hole);const g=new THREE.ExtrudeGeometry(shape,{depth:.16,bevelEnabled:false});g.rotateX(PI/2);b.add(g,'abenStucco',[cx,6.75,cz]);
 for(let i=0;i<16;i++){
  const e=edge(i),f={...e,at:(u,v=0)=>[e.x+Math.cos(e.a)*u+Math.sin(e.a)*v,e.z-Math.sin(e.a)*u+Math.cos(e.a)*v]};
  box(b,f,0,6.7,0,e.w+.08,.3,.35,'sCarving');
  for(const sign of [-1,1])box(b,f,sign*(e.w+.64)/4,7,0,(e.w-.64)/2,1.35,.35,'abenStucco');
  b.arch(e.x,e.z,.64,.70,.32,1.35,.35,'abenStucco',e.a,7,false);window(b,f,0,7.02,.60,.99);
  band(b,f,8.2,e.w+.06,'sRibbon',.16,-.22);
  if(i%4===0)portalLight(b,f,7.5,3);
 }
 for(let j=0;j<16;j++){
  const t=j/16,scale=1-.96*t,y=8.22+3.65*(1-(1-t)**1.25);
  for(let i=0;i<16;i++){
   const e=edge(i,scale),per=Math.max(2,Math.round(e.w/.21)),w=e.w/per;
   b.box(e.x+Math.sin(e.a)*(.32*scale+.10),y+.60,e.z+Math.cos(e.a)*(.32*scale+.10),e.w+.08,.16,.30*scale+.10,'abenPlaster',e.a);
   for(let k=0;k<per;k++){const u=(k+.5-per/2)*w,x=e.x+Math.cos(e.a)*u,z=e.z-Math.sin(e.a)*u;b.add(cell,tint(i,j,k),[x,y,z],[w*1.16,.74-t*.2,.46*scale+.10],e.a);b.add(cell,tint(i,j,k+7),[x-Math.sin(e.a)*.12,y+.17,z-Math.cos(e.a)*.12],[w*.80,.44-t*.12,.30*scale+.07],e.a);b.stats.muqarnas+=2;}
  }
 }
 for(let i=0;i<8;i++){const a=i*PI/4,x=cx+Math.sin(a)*2.7,z=cz+Math.cos(a)*2.7;for(let k=0;k<8;k++){const q=k*PI/4;b.add(cell,tint(i,k,99),[x+Math.sin(q)*.32,8.05,z+Math.cos(q)*.32],[.35,.55,.3],q);b.stats.muqarnas++;}}
 b.cylinder(cx,11.85,cz,.32,.12,'abenPlaster',.32,8);
 for(let i=0;i<16;i++){const e=edge(i);b.box(e.x+Math.sin(e.a)*.3,8.3,e.z+Math.cos(e.a)*.3,e.w+.55,3.8,.25,'abenStucco',e.a);}
 sunPatch(b,cx,cz,3.6,7.2);
}
