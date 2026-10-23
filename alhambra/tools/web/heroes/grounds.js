import * as THREE from 'three';
import { insidePolygon } from '../navigation.js';
import { plant, CYPRESS, ELM, PLANE, HOLM, OLIVE, PINE, STONEPINE, ORANGE, PALM, SHRUB, POPLAR } from '../trees.js';

// The grounds of the Alhambra enclosure outside the palaces and the other hero modules: Calle Real de la Alhambra with
// its houses, the church of Santa María, the Baño de la Mezquita, the Hotel América block, the Parador de San Francisco
// (former Franciscan convent), the Secano and the gardens, with real paving on every path.
//
// Everything is generated from OpenStreetMap footprints (ODbL; building:part massing and levels, highways, gardens, hedges,
// archaeological areas; tools/web/heroes data block at the end of this file), a seeded random generator for the facades,
// and procedural textures made for this project (public/textures/grounds, see credits.json).

let LOW=false;

// ======================================================================= small maths
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v)),lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
function rng(seed){let s=(seed>>>0)||1;return()=>{s=(Math.imul(1664525,s)+1013904223)>>>0;return s/4294967296;};}
function h2(x,y,s=0){let h=Math.imul(x|0,374761393)^Math.imul(y|0,668265263)^Math.imul(s|0,1274126177);h=Math.imul(h^(h>>>13),1274126177);h^=h>>>16;return (h>>>0)/4294967296;}
const D2=([a,b],[c,d])=>Math.hypot(c-a,d-b);
function ringArea(r){let s=0;for(let i=0,j=r.length-1;i<r.length;j=i++)s+=(r[j][0]*r[i][1]-r[i][0]*r[j][1]);return s/2;}
function inRing(x,z,r){let ins=false;for(let i=0,j=r.length-1;i<r.length;j=i++){const a=r[i],b=r[j];if(((a[1]>z)!==(b[1]>z))&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])ins=!ins;}return ins;}
function inPoly(x,z,o,holes=[]){if(!inRing(x,z,o))return false;for(const h of holes)if(inRing(x,z,h))return false;return true;}
function distSeg(x,z,a,b){const dx=b[0]-a[0],dz=b[1]-a[1],l=dx*dx+dz*dz,t=l?clamp(((x-a[0])*dx+(z-a[1])*dz)/l,0,1):0;return Math.hypot(x-a[0]-dx*t,z-a[1]-dz*t);}
function distPoly(x,z,r){let d=1e9;for(let i=0,j=r.length-1;i<r.length;j=i++)d=Math.min(d,distSeg(x,z,r[j],r[i]));return d;}
function bbox(r){let a=1e9,b=1e9,c=-1e9,d=-1e9;for(const [x,z] of r){a=Math.min(a,x);b=Math.min(b,z);c=Math.max(c,x);d=Math.max(d,z);}return [a,b,c,d];}
function centroid(r){let x=0,z=0;for(const p of r){x+=p[0];z+=p[1];}return [x/r.length,z/r.length];}
const sub3=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],cross3=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot3=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
function norm3(v){const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];}
// value noise for scattering decisions
function vn(x,y){const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy,u=fx*fx*(3-2*fx),v=fy*fy*(3-2*fy);return lerp(lerp(h2(ix,iy),h2(ix+1,iy),u),lerp(h2(ix,iy+1),h2(ix+1,iy+1),u),v);}

// ======================================================================= mesh accumulation
// One Soup per (material, chunk). Everything is written in world coordinates; at the end each soup becomes an
// indexed mesh, so a building is a handful of draw calls and frustum culling works per chunk.
const SOUPS=new Map();let CHUNK='g',TRIS=0;
const NOCAST=new Set(['grdGrass','grdGrassDry','grdSoil','grdGravel','grdCobble','grdPebble','grdPaving','grdAsphalt','grdCrop','grdGlass','grdGroundDark','grdFlowerBed','grdWater']);
function S(mat){const k=mat+'|'+CHUNK;let s=SOUPS.get(k);if(!s){s={mat,chunk:CHUNK,pos:[],nor:[],uv:[],idx:[]};SOUPS.set(k,s);}return s;}
function vert(s,p,n,u,v){s.pos.push(p[0],p[1],p[2]);s.nor.push(n[0],n[1],n[2]);s.uv.push(u,v);return s.pos.length/3-1;}
// triangle with an explicit outward normal; winding fixed to match it
function tri(mat,p0,p1,p2,uv0,uv1,uv2,n){
  const s=S(mat),c=cross3(sub3(p1,p0),sub3(p2,p0));let m=n;
  if(!m){m=norm3(c);}else if(dot3(c,m)<0){[p1,p2]=[p2,p1];[uv1,uv2]=[uv2,uv1];}
  const a=vert(s,p0,m,uv0[0],uv0[1]),b=vert(s,p1,m,uv1[0],uv1[1]),d=vert(s,p2,m,uv2[0],uv2[1]);s.idx.push(a,b,d);TRIS++;
}
function quad(mat,p0,p1,p2,p3,uv0,uv1,uv2,uv3,n){
  if(!n)n=norm3(cross3(sub3(p1,p0),sub3(p2,p0)));
  tri(mat,p0,p1,p2,uv0,uv1,uv2,n);tri(mat,p0,p2,p3,uv0,uv2,uv3,n);
}
// quad with UVs in metres measured along its two edges (p0->p1 is u, p0->p3 is v), plus offsets
function quadM(mat,p0,p1,p2,p3,n,u0=0,v0=0,su=1,sv=1){
  const lu=Math.hypot(p1[0]-p0[0],p1[1]-p0[1],p1[2]-p0[2])*su,lv=Math.hypot(p3[0]-p0[0],p3[1]-p0[1],p3[2]-p0[2])*sv;
  quad(mat,p0,p1,p2,p3,[u0,v0],[u0+lu,v0],[u0+lu,v0+lv],[u0,v0+lv],n);
}
// smooth-shaded strip between two polylines (hedges, cornices); winding follows the supplied normals
function strip3(mat,A,B,nA,nB,uvA,uvB){
  const s=S(mat),base=s.pos.length/3;
  for(let i=0;i<A.length;i++){vert(s,A[i],nA[i],uvA[i][0],uvA[i][1]);vert(s,B[i],nB[i],uvB[i][0],uvB[i][1]);}
  for(let i=0;i<A.length-1;i++){
    const a=base+i*2,b=a+1,c=a+2,d=a+3;
    const cr=cross3(sub3(A[i+1],A[i]),sub3(B[i],A[i]));const want=[nA[i][0]+nB[i][0],nA[i][1]+nB[i][1],nA[i][2]+nB[i][2]];
    if(dot3(cr,want)>=0)s.idx.push(a,c,b,b,c,d);else s.idx.push(a,b,c,b,d,c);
    TRIS+=2;
  }
}
// horizontal polygon with holes at height y, normal up (or down), world-planar UVs (metres / scale)
function polyH(mat,outer,holes,y,scale=1,up=true,uo=0,vo=0){
  const V=[...outer,...holes.flat()].map(p=>new THREE.Vector2(p[0],p[1]));
  const tris=THREE.ShapeUtils.triangulateShape(outer.map(p=>new THREE.Vector2(p[0],p[1])),holes.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1]))));
  const s=S(mat),base=s.pos.length/3,ny=up?1:-1;
  for(const q of V)vert(s,[q.x,y,q.y],[0,ny,0],(q.x+uo)/scale,(q.y+vo)/scale);
  for(const [a,b,c] of tris){const A=V[a],B=V[b],C=V[c],cr=(B.x-A.x)*(C.y-A.y)-(B.y-A.y)*(C.x-A.x);// cr>0: (x,z) ccw => normal -y in this frame
    if((cr>0)===!up)s.idx.push(base+a,base+b,base+c);else s.idx.push(base+a,base+c,base+b);TRIS++;}
}
// ribbon along a polyline with width w at height y (mitre joins), world-planar UV
function ribbon(mat,pts,w,y,scale=1,off=0){
  if(pts.length<2)return;
  const L=[],R=[];
  for(let i=0;i<pts.length;i++){
    const p=pts[i],a=pts[Math.max(0,i-1)],b=pts[Math.min(pts.length-1,i+1)];
    let dx1=p[0]-a[0],dz1=p[1]-a[1],dx2=b[0]-p[0],dz2=b[1]-p[1];
    const l1=Math.hypot(dx1,dz1),l2=Math.hypot(dx2,dz2);
    if(l1>1e-6){dx1/=l1;dz1/=l1;}else{dx1=dx2;dz1=dz2;}if(l2>1e-6){dx2/=l2;dz2/=l2;}else{dx2=dx1;dz2=dz1;}
    let nx=-(dz1+dz2),nz=dx1+dx2;const nl=Math.hypot(nx,nz)||1;nx/=nl;nz/=nl;
    const c=Math.max(.35,nx*(-dz1)+nz*dx1);const k=(w/2)/c,kk=Math.min(k,w*1.2);
    L.push([p[0]+nx*(kk+off),p[1]+nz*(kk+off)]);R.push([p[0]-nx*(kk-off),p[1]-nz*(kk-off)]);
  }
  const s=S(mat),base=s.pos.length/3;
  for(let i=0;i<pts.length;i++){vert(s,[L[i][0],y,L[i][1]],[0,1,0],L[i][0]/scale,L[i][1]/scale);vert(s,[R[i][0],y,R[i][1]],[0,1,0],R[i][0]/scale,R[i][1]/scale);}
  for(let i=0;i<pts.length-1;i++){const a=base+i*2,b=a+1,c=a+2,d=a+3;s.idx.push(a,c,b,b,c,d);TRIS+=2;}
}
// oriented box from a centre line: (cx,cz) centre, direction (dx,dz) unit, half sizes along/across, y0..y1
function obox(mat,cx,cz,dx,dz,hl,hw,y0,y1,uvs=1,top=true,bottom=false,uo=0){
  const tx=dx,tz=dz,nx=-dz,nz=dx;
  const c=(a,b,y)=>[cx+tx*a+nx*b,y,cz+tz*a+nz*b];
  const p=[c(-hl,-hw,y0),c(hl,-hw,y0),c(hl,hw,y0),c(-hl,hw,y0),c(-hl,-hw,y1),c(hl,-hw,y1),c(hl,hw,y1),c(-hl,hw,y1)];
  const h=y1-y0;
  // four sides
  quadM(mat,p[0],p[1],p[5],p[4],[-nx,0,-nz],uo,y0*uvs,uvs,uvs);
  quadM(mat,p[1],p[2],p[6],p[5],[tx,0,tz],uo,y0*uvs,uvs,uvs);
  quadM(mat,p[2],p[3],p[7],p[6],[nx,0,nz],uo,y0*uvs,uvs,uvs);
  quadM(mat,p[3],p[0],p[4],p[7],[-tx,0,-tz],uo,y0*uvs,uvs,uvs);
  if(top)quad(mat,p[4],p[5],p[6],p[7],[cx*uvs,cz*uvs],[(cx+hl)*uvs,cz*uvs],[(cx+hl)*uvs,(cz+hw)*uvs],[cx*uvs,(cz+hw)*uvs],[0,1,0]);
  if(bottom)quad(mat,p[0],p[3],p[2],p[1],[0,0],[0,1],[1,1],[1,0],[0,-1,0]);
}
// axis-aligned box helper
function abox(mat,x0,y0,z0,x1,y1,z1,uvs=1,top=true){obox(mat,(x0+x1)/2,(z0+z1)/2,1,0,(x1-x0)/2,(z1-z0)/2,y0,y1,uvs,top);}
// a straight bar between two 3D points with a square cross section
function bar(mat,a,b,t,uvs=1,caps=0){
  const d=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],l=Math.hypot(...d);if(l<1e-6)return;const u=[d[0]/l,d[1]/l,d[2]/l];
  let r=Math.abs(u[1])>.9?[1,0,0]:[0,1,0];let s=norm3(cross3(u,r));r=norm3(cross3(s,u));
  const h=t/2,c=(i,j)=>[0,1,2].map(k=>(i*s[k]+j*r[k])*h);
  const corners=[[-1,-1],[1,-1],[1,1],[-1,1]];
  for(let k=0;k<4;k++){const [i0,j0]=corners[k],[i1,j1]=corners[(k+1)%4],o0=c(i0,j0),o1=c(i1,j1);
    const A0=[a[0]+o0[0],a[1]+o0[1],a[2]+o0[2]],A1=[a[0]+o1[0],a[1]+o1[1],a[2]+o1[2]],B0=[b[0]+o0[0],b[1]+o0[1],b[2]+o0[2]],B1=[b[0]+o1[0],b[1]+o1[1],b[2]+o1[2]];
    const nn=norm3([(i0+i1)*s[0]+(j0+j1)*r[0],(i0+i1)*s[1]+(j0+j1)*r[1],(i0+i1)*s[2]+(j0+j1)*r[2]]);
    quad(mat,A0,A1,B1,B0,[0,0],[t*uvs,0],[t*uvs,l*uvs],[0,l*uvs],nn);}
  if(caps){
    const ends=caps>1?[[b,u],[a,[-u[0],-u[1],-u[2]]]]:[[b,u]];
    for(const [e,nn] of ends){const q=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([i,j])=>[e[0]+(i*s[0]+j*r[0])*h,e[1]+(i*s[1]+j*r[1])*h,e[2]+(i*s[2]+j*r[2])*h]);
      quad(mat,q[0],q[1],q[2],q[3],[0,0],[t*uvs,0],[t*uvs,t*uvs],[0,t*uvs],nn);}
  }
}
function flush(b){
  for(const s of SOUPS.values()){
    const m=b.m[s.mat];if(!m)throw new Error(`Unknown material "${s.mat}" in grounds`);
    if(!s.idx.length)continue;
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(s.pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(s.nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(s.uv,2));
    g.setIndex(s.pos.length/3>65535?new THREE.Uint32BufferAttribute(s.idx,1):new THREE.Uint16BufferAttribute(s.idx,1));g.computeBoundingSphere();
    const mesh=new THREE.Mesh(g,m);mesh.name=`grounds:${s.mat}:${s.chunk}`;mesh.castShadow=!NOCAST.has(s.mat)&&!m.transparent;mesh.receiveShadow=true;b.root.add(mesh);
  }
  SOUPS.clear();
}

// ======================================================================= materials
const SRGB=THREE.SRGBColorSpace;
async function loadImg(f){const i=new Image();i.src=`textures/grounds/${f}`;await i.decode();return i;}
function tex(img,size,srgb=true,ratio=1){const t=new THREE.Texture(img);t.needsUpdate=true;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=srgb?SRGB:THREE.NoColorSpace;t.anisotropy=8;t.repeat.set(1/size,1/(size*ratio));return t;}
// World-space colour variation: a slow value noise multiplies the albedo, so a texture repeated over a whole wall,
// roof or lawn never reads as one tile. CSM replaces onBeforeCompile, so the patch is chained through an accessor.
function macro(m,{mode='ground',scale=9,amp=.14,tint=null}={}){
  let base=null;
  const patch=shader=>{
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vMW;').replace('#include <begin_vertex>','#include <begin_vertex>\nvMW=position;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>',`#include <common>
varying vec3 vMW;
float mhash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float mvn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mhash(i),mhash(i+vec2(1,0)),f.x),mix(mhash(i+vec2(0,1)),mhash(i+vec2(1,1)),f.x),f.y);}`)
    .replace('#include <map_fragment>',`#include <map_fragment>
{vec2 q=${mode==='ground'?'vMW.xz':'vec2(vMW.x*.8+vMW.z*.6,vMW.y+(vMW.x*.6-vMW.z*.8)*.15)'};
float mn=mvn(q/${scale.toFixed(2)})*.55+mvn(q/${(scale*.29).toFixed(2)}+7.3)*.30+mvn(q/${(scale*.09).toFixed(2)}+3.1)*.15;
diffuseColor.rgb*=1.0+${amp.toFixed(3)}*(mn*2.0-1.0);
${tint?`diffuseColor.rgb=mix(diffuseColor.rgb,diffuseColor.rgb*vec3(${tint.map(v=>v.toFixed(3)).join(',')}),smoothstep(.55,.85,mvn(q/${(scale*2.7).toFixed(2)}+11.7)));`:''}}`);
  };
  const wrapper=function(shader,renderer){if(base)base.call(this,shader,renderer);patch(shader);};
  Object.defineProperty(m,'onBeforeCompile',{get(){return wrapper;},set(f){base=f;},configurable:true});
  const key=`grdmacro-${mode}-${scale}-${amp}-${tint?tint.join('_'):''}`;m.customProgramCacheKey=()=>key;
  return m;
}
function std(name,color,rough=.9,extra={}){const m=new THREE.MeshStandardMaterial({color,roughness:rough,metalness:0,...extra});m.name=name;m.userData.scale=1;return m;}

function cvsAgave(){const c=document.createElement('canvas');c.width=32;c.height=64;const g=c.getContext('2d');const q=g.createLinearGradient(0,64,0,0);q.addColorStop(0,'#5d7a5a');q.addColorStop(.6,'#7f9a7b');q.addColorStop(1,'#a2b08a');g.fillStyle=q;g.fillRect(0,0,32,64);g.fillStyle='rgba(30,40,30,.35)';g.fillRect(14,0,4,64);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;}
export async function materials(M){
  const L=async n=>loadImg(n);
  const [cobble,pebble,gravel,grass,grassDry,soil,crop,pave,hedge,brickA,brickC,stone,church,rendB,plA,plB,roof,wood,louver,grille,railing]=await Promise.all(
    ['cobble.jpg','pebbleFine.jpg','gravel.jpg','grass.jpg','grassDry.jpg','soil.jpg','crop.jpg','paveSlab.jpg','hedge.jpg','brickA.jpg','brickC.jpg','stoneA.jpg','churchWall.jpg','renderBrick.jpg','plasterA.jpg','plasterB.jpg','roofTile.jpg','wood.jpg','louver.jpg','grille.png','railing.png'].map(L));
  const H=await Promise.all(['cobble','pebbleFine','gravel','grass','soil','crop','paveSlab','hedge','brickA','brickC','stoneA','churchWall','renderBrick','plasterA','plasterB','roofTile','wood'].map(n=>loadImg(n+'-h.jpg')));
  const hm=Object.fromEntries(['cobble','pebble','gravel','grass','soil','crop','pave','hedge','brickA','brickC','stone','church','rendB','plA','plB','roof','wood'].map((n,i)=>[n,H[i]]));
  // textured standard material: colour map (size = metres per repeat), optional bump (height in metres)
  const mk=(name,img,size,{h=null,bump=0,color=0xffffff,rough=.9,side=THREE.FrontSide,macroOpt=null,ratio=1}={})=>{
    const m=std(name,color,rough,{map:tex(img,size,true,ratio),side});
    if(h&&bump){m.bumpMap=tex(h,size,false,ratio);m.bumpScale=bump;}
    if(macroOpt)macro(m,macroOpt);M[name]=m;return m;
  };
  const G={mode:'ground',scale:11,amp:.16};
  mk('grdCobble',cobble,3,{h:hm.cobble,bump:.028,rough:.86,color:0xfae9cf,macroOpt:{...G,amp:.12}});
  mk('grdPebble',pebble,3,{h:hm.pebble,bump:.018,rough:.88,macroOpt:{...G,amp:.12}});
  mk('grdGravel',gravel,3,{h:hm.gravel,bump:.006,rough:.97,color:0xfbe9c6,macroOpt:{...G,amp:.14}});
  mk('grdGrass',grass,4,{h:hm.grass,bump:.02,rough:1,macroOpt:{...G,scale:13,amp:.22,tint:[.86,.9,.7]}});
  mk('grdGrassDry',grassDry,4,{h:hm.grass,bump:.02,rough:1,macroOpt:{...G,scale:15,amp:.24,tint:[.95,.82,.66]}});
  mk('grdSoil',soil,3,{h:hm.soil,bump:.015,rough:1,macroOpt:{...G,amp:.16}});
  mk('grdCrop',crop,4,{h:hm.crop,bump:.03,rough:1,macroOpt:{...G,scale:7,amp:.12}});
  mk('grdPaving',pave,2.4,{h:hm.pave,bump:.008,rough:.8,color:0xf6e4c6,macroOpt:{...G,scale:7,amp:.12}});
  mk('grdAsphalt',gravel,3,{h:hm.gravel,bump:.004,color:0x948f86,rough:.95,macroOpt:{...G,amp:.1}});
  mk('grdGroundDark',soil,3,{h:hm.soil,bump:.01,color:0xcdb89a,rough:1,macroOpt:{...G,amp:.12}});
  mk('grdHedge',hedge,1,{h:hm.hedge,bump:.05,rough:1,color:0xffffff,macroOpt:{mode:'wall',scale:5,amp:.2}});
  const W={mode:'wall',scale:8,amp:.12};
  mk('grdBrickA',brickA,2,{h:hm.brickA,bump:.008,rough:.93,macroOpt:{...W,amp:.15}});
  mk('grdBrickB',brickA,2,{h:hm.brickA,bump:.008,rough:.93,color:0xc9a89a,macroOpt:{...W,amp:.15}});
  mk('grdBrickC',brickC,2,{h:hm.brickC,bump:.008,rough:.93,macroOpt:{...W,amp:.13}});
  mk('grdRender',rendB,2,{h:hm.rendB,bump:.007,rough:.95,color:0xf4e0c4,macroOpt:{...W,amp:.16,tint:[.94,.9,.84]}});
  mk('grdRenderTrim',plA,2.4,{h:hm.plA,bump:.004,color:0xe9d2ae,rough:.95,macroOpt:{...W,amp:.1}});
  mk('grdStone',stone,2.4,{h:hm.stone,bump:.012,rough:.9,macroOpt:{...W,amp:.12}});
  mk('grdChurch',church,2.4,{h:hm.church,bump:.014,rough:.93,macroOpt:{...W,amp:.10}});
  const pl=[['grdWhite',0xfff3dc],['grdCream',0xf6e2b8],['grdOchre',0xe6bd7e],['grdRose',0xe2ab92],['grdSalmon',0xdc9c82],['grdSand',0xe5d2a8]];
  for(const [n,c] of pl){mk(n,plA,2.4,{h:hm.plA,bump:.004,color:c,rough:.95,macroOpt:{...W,amp:.10}});}
  mk('grdWhiteB',plB,2.4,{h:hm.plB,bump:.006,color:0xf2ecdf,rough:.95,macroOpt:{...W,amp:.10}});
  mk('grdOchreB',plB,2.4,{h:hm.plB,bump:.006,color:0xe0b676,rough:.95,macroOpt:{...W,amp:.10}});
  mk('grdRoseB',plB,2.4,{h:hm.plB,bump:.006,color:0xd9a58a,rough:.95,macroOpt:{...W,amp:.10}});
  mk('grdRoof',roof,1.6,{h:hm.roof,bump:.05,rough:.82,macroOpt:{mode:'ground',scale:12,amp:.18,tint:[.9,.88,.84]}});
  mk('grdRoofOld',roof,1.6,{h:hm.roof,bump:.05,rough:.85,color:0xd8cbc2,macroOpt:{mode:'ground',scale:9,amp:.2}});
  {const c=document.createElement('canvas');c.width=c.height=256;const g=c.getContext('2d'),rr=rng(5);g.fillStyle='#55626c';g.fillRect(0,0,256,256);
    for(let r=0;r<8;r++){const white=r%4===3;for(let k=-1;k<9;k++){const x=k*32+(r%2)*16,y=r*32,v=rr();g.fillStyle=white?`hsl(45 ${8+v*8}% ${82+v*8}%)`:`hsl(${200+v*12} ${10+v*8}% ${34+v*14}%)`;g.fillRect(x+1,y+1,30,30);
      g.fillStyle='rgba(0,0,0,.28)';g.fillRect(x,y+29,32,3);g.fillRect(x+30,y,2,32);g.fillStyle='rgba(255,255,255,.12)';g.fillRect(x+2,y+2,28,3);}}
    const t=new THREE.CanvasTexture(c);t.colorSpace=SRGB;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.anisotropy=8;t.repeat.set(1,1);const sm=std('grdSlate',0xffffff,.45,{map:t});M.grdSlate=sm;}
  mk('grdCypress',hedge,1,{h:hm.hedge,bump:.07,rough:1,color:0xa8bf9a,side:THREE.DoubleSide,macroOpt:{mode:'wall',scale:7,amp:.22}});
  mk('grdHedgeBox',hedge,.5,{h:hm.hedge,bump:.03,rough:1,color:0xd0e0b0,macroOpt:{mode:'wall',scale:4,amp:.16}});
  {const t=cvsAgave();M.grdAgave=std('grdAgave',0xffffff,.6,{map:t,side:THREE.DoubleSide});}
  mk('grdRuin',stone,2.4,{h:hm.stone,bump:.02,rough:1,color:0xe6d3b4,macroOpt:{...W,amp:.18}});
  mk('grdWood',wood,1,{h:hm.wood,bump:.01,rough:.8});
  mk('grdWoodDoor',wood,1,{h:hm.wood,bump:.012,rough:.78,color:0xe8c9a4});
  mk('grdBeam',wood,1,{h:hm.wood,bump:.008,rough:.85,color:0xffe2c4});
  for(const [n,c] of [['grdShutterG',0x41614b],['grdShutterB',0x6b4a30],['grdShutterN',0x3d556b],['grdShutterW',0xe9e4d6]]){mk(n,louver,1,{rough:.7,color:c,side:THREE.DoubleSide});}
  const cv=(w,h,f)=>{const c=document.createElement('canvas');c.width=w;c.height=h;f(c.getContext('2d'),w,h);const t=new THREE.CanvasTexture(c);t.colorSpace=SRGB;t.wrapS=t.wrapT=THREE.RepeatWrapping;return t;};
  const skyTex=cv(64,128,(g,w,h)=>{const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'#c6d6e2');q.addColorStop(.38,'#8fa6b8');q.addColorStop(.62,'#4a5964');q.addColorStop(1,'#1f272d');g.fillStyle=q;g.fillRect(0,0,w,h);
    g.fillStyle='rgba(255,255,255,.12)';g.beginPath();g.moveTo(0,h*.1);g.lineTo(w*.55,0);g.lineTo(w,0);g.lineTo(w*.2,h*.7);g.closePath();g.fill();});
  M.grdGlass=std('grdGlass',0xffffff,.1,{map:skyTex,emissive:0xffffff,emissiveMap:skyTex,emissiveIntensity:.5,metalness:.1});
  const curtainTex=cv(64,64,(g,w,h)=>{g.fillStyle='#e8dcc2';g.fillRect(0,0,w,h);for(let x=0;x<w;x+=6){g.fillStyle=`rgba(120,100,70,${.10+((x*7)%5)*.02})`;g.fillRect(x,0,3,h);}const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'rgba(0,0,0,.35)');q.addColorStop(.35,'rgba(0,0,0,0)');g.fillStyle=q;g.fillRect(0,0,w,h);});
  M.grdCurtain=std('grdCurtain',0xffffff,1,{map:curtainTex,emissive:0xffffff,emissiveMap:curtainTex,emissiveIntensity:.18});
  const curtainTex2=cv(64,64,(g,w,h)=>{g.fillStyle='#bfc9c0';g.fillRect(0,0,w,h);for(let x=0;x<w;x+=5){g.fillStyle='rgba(60,80,60,.12)';g.fillRect(x,0,2,h);}const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'rgba(0,0,0,.4)');q.addColorStop(.4,'rgba(0,0,0,0)');g.fillStyle=q;g.fillRect(0,0,w,h);});
  M.grdCurtain2=std('grdCurtain2',0xffffff,1,{map:curtainTex2,emissive:0xffffff,emissiveMap:curtainTex2,emissiveIntensity:.15});
  M.grdFrame=std('grdFrame',0xf0ece2,.7);M.grdFrameD=std('grdFrameD',0x4a3828,.7);
  M.grdIron=std('grdIron',0x222221,.55,{metalness:.5});M.grdBush=std('grdBush',0x4a6c34,.95);M.grdVine=std('grdVine',0x5d8a3a,.95,{side:THREE.DoubleSide});M.grdRose2=std('grdRose2',0xe0657d,.9);M.grdRed=std('grdRed',0xb52a2f,.9);M.grdYellowF=std('grdYellowF',0xe6c640,.9);M.grdYellow=std('grdYellow',0xd9b92e,.6);M.grdYellow.polygonOffset=true;M.grdYellow.polygonOffsetFactor=-1;M.grdYellow.polygonOffsetUnits=-18;M.grdFrameG=std('grdFrameG',0x41614b,.7);M.grdLamp=std('grdLamp',0x24342b,.5,{metalness:.35});M.grdGlassLamp=std('grdGlassLamp',0xf2e8c8,.2,{emissive:0xffe6a8,emissiveIntensity:.25,transparent:true,opacity:.85});M.grdTerracotta=std('grdTerracotta',0xc9733f,.85);M.grdBlind=std('grdBlind',0xd7cfb9,.9);M.grdDoorPanel=std('grdDoorPanel',0x3d2a1b,.75);M.grdZinc=std('grdZinc',0x8a8d8c,.5,{metalness:.5});
  M.grdDark=std('grdDark',0x15110f,.95);
  M.grdWater=std('grdWater',0x4f7f78,.1,{metalness:.1,transparent:true,opacity:.82});
  M.grdWater.userData.noShadow=true;
  const cvs=(w,h,f)=>{const c=document.createElement('canvas');c.width=w;c.height=h;f(c.getContext('2d'),w,h);return c;};
  const signCanvas=cvs(512,512,(g,w,h)=>{
    SIGNS.forEach((txt,i)=>{const c=i%2,r=Math.floor(i/2),x=c*256,y=r*128,[bg,fg]=SIGN_COL[i];g.fillStyle=bg;g.fillRect(x,y,256,128);g.strokeStyle=fg;g.lineWidth=4;g.strokeRect(x+6,y+6,244,116);g.fillStyle=fg;g.font='bold 40px Georgia, serif';g.textAlign='center';g.textBaseline='middle';
      g.fillText(txt,x+128,y+66,226);});
  });
  {const t=new THREE.CanvasTexture(signCanvas);t.colorSpace=SRGB;t.anisotropy=8;t.wrapS=t.wrapT=THREE.ClampToEdgeWrapping;M.grdSign=std('grdSign',0xffffff,.55,{map:t,side:THREE.DoubleSide});}
  AWN.forEach(([c1,c2],i)=>{const cv2=cvs(64,64,(g,w,h)=>{for(let k=0;k<8;k++){g.fillStyle=k%2?c2:c1;g.fillRect(k*8,0,8,h);}});const t=new THREE.CanvasTexture(cv2);t.colorSpace=SRGB;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(1/8,1/8);t.anisotropy=4;M['grdAwning'+i]=std('grdAwning'+i,0xffffff,.95,{map:t,side:THREE.DoubleSide});});
  {const t=new THREE.CanvasTexture(cvs(64,64,(g,w,h)=>{g.fillStyle='#e9e1cd';g.fillRect(0,0,w,h);g.fillStyle='#1e4a7a';g.fillRect(3,3,w-6,h-6);g.fillStyle='#e9e1cd';g.font='bold 36px sans-serif';g.textAlign='center';g.textBaseline='middle';g.fillText('12',w/2,h/2+2);}));t.colorSpace=SRGB;M.grdTilePlaque=std('grdTilePlaque',0xffffff,.4,{map:t,side:THREE.DoubleSide});}
  const al=(name,img)=>{const t=tex(img,1,true);t.repeat.set(1,1);const m=std(name,0xffffff,.6,{map:t,side:THREE.DoubleSide,transparent:false,alphaTest:.45,metalness:.4});M[name]=m;return m;};
  al('grdGrille',grille);al('grdRailing',railing);
  M.grdGrille.map.wrapT=M.grdGrille.map.wrapS=THREE.RepeatWrapping;
  M.grdHedge.side=THREE.DoubleSide;
  applyOffsets(M);M.grdAsphalt.color.set(0x8c8a86);
}

// ======================================================================= ground cover, paths, hedges
const OFFSETS={grdGrassDry:-4,grdGrass:-8,grdSoil:-8,grdCrop:-8,grdGroundDark:-8,grdGravel:-12,grdCobble:-12,grdPaving:-12,grdAsphalt:-12,grdPebble:-16};
function applyOffsets(M){for(const [n,u] of Object.entries(OFFSETS)){const m=M[n];if(m){m.polygonOffset=true;m.polygonOffsetFactor=-1;m.polygonOffsetUnits=u;}}}
const YG={base:-.020,l1:-.016,l2:-.012,l3:-.008};

// clipped hedge: a rounded-shoulder profile swept along a polyline (closed rings repeat the first point)
const HEDGE_PROFILE=[[-.5,0],[-.5,.72],[-.40,.93],[-.2,1],[.2,1],[.40,.93],[.5,.72],[.5,0]];
const HEDGE_N=[[-1,0],[-1,.35],[-.7,.7],[-.15,1],[.15,1],[.7,.7],[1,.35],[1,0]];
function hedgeRun(pts,w,h,mat='grdHedge',y0=0,closed=false){
  const P=closed?[...pts,pts[0]]:pts;if(P.length<2)return;
  const cols=HEDGE_PROFILE.map(()=>[]),nors=HEDGE_PROFILE.map(()=>[]),us=[];let acc=0;
  for(let i=0;i<P.length;i++){
    const p=P[i],a=P[i===0?(closed?P.length-2:0):i-1],c=P[i===P.length-1?(closed?1:i):i+1];
    let dx1=p[0]-a[0],dz1=p[1]-a[1],dx2=c[0]-p[0],dz2=c[1]-p[1];const l1=Math.hypot(dx1,dz1),l2=Math.hypot(dx2,dz2);
    if(l1>1e-6){dx1/=l1;dz1/=l1;}else{dx1=dx2;dz1=dz2;}if(l2>1e-6){dx2/=l2;dz2/=l2;}else{dx2=dx1;dz2=dz1;}
    let nx=-(dz1+dz2),nz=dx1+dx2;const nl=Math.hypot(nx,nz)||1;nx/=nl;nz/=nl;const cs=Math.max(.5,nx*(-dz1)+nz*dx1);
    if(i>0)acc+=Math.hypot(p[0]-P[i-1][0],p[1]-P[i-1][1]);us.push(acc);
    HEDGE_PROFILE.forEach(([o,v],k)=>{const ww=o*w/cs;cols[k].push([p[0]+nx*ww,y0+v*h,p[1]+nz*ww]);const [an,av]=HEDGE_N[k];nors[k].push(norm3([nx*an,av,nz*an]));});
  }
  let vacc=0;const vs=[0];for(let k=1;k<HEDGE_PROFILE.length;k++){vacc+=Math.hypot((HEDGE_PROFILE[k][0]-HEDGE_PROFILE[k-1][0])*w,(HEDGE_PROFILE[k][1]-HEDGE_PROFILE[k-1][1])*h);vs.push(vacc);}
  for(let k=0;k<HEDGE_PROFILE.length-1;k++){
    strip3(mat,cols[k],cols[k+1],nors[k],nors[k+1],us.map(u=>[u,vs[k]]),us.map(u=>[u,vs[k+1]]));
  }
  // end caps of open runs are hidden by the ground; closed rings need none
}

function pathStyle(p){
  const n=p.n||'',hw=p.hw,sf=p.s||'';
  const calle=/Calle Real/.test(n);
  let w=hw==='pedestrian'?(calle?(sf==='asphalt'?7:5.4):3.6):hw==='service'?3.0:hw==='steps'?2.0:hw==='path'?1.6:/Paseo/.test(n)?3.2:2.2;
  let mat='grdGravel';
  if(calle||sf==='unhewn_cobblestone'||sf==='sett'||sf==='cobblestone')mat='grdCobble';
  else if(sf==='paving_stones')mat='grdPaving';
  else if(sf==='asphalt'||sf==='concrete')mat=hw==='service'?'grdAsphalt':'grdGravel';
  return {w,mat,calle};
}
function buildGround(b,ctx){
  const T=DATA.T;
  CHUNK='gnd-base';
  for(const t of T)polyH('grdGrassDry',t.o,t.h,YG.base,4);
  // beds, lawns, kitchen gardens and archaeological ground
  for(const g of DATA.BEDS){
    const c=centroid(g.o);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    if(g.k==='bed'){polyH('grdGrass',g.o,g.h,YG.l1,4);}
    else if(g.k==='garden'){polyH('grdGrass',g.o,g.h,YG.l1,4);}
    else if(g.k==='kitchen'){polyH('grdCrop',g.o,g.h,YG.l1,4);}
    else if(g.k==='parking'){polyH('grdGravel',g.o,g.h,YG.l1,3);}
    else if(g.k==='plaza'){polyH('grdPebble',g.o,g.h,YG.l1,3);}
  }
  for(const g of DATA.RUINS){
    const c=centroid(g.o);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    if(/Secano/.test(g.n||''))continue;
    polyH('grdGravel',g.o,g.h,YG.l1,3);
  }
  // paths
  for(const p of DATA.PATHS){
    const st=pathStyle(p);const c=centroid(p.p);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    if(st.calle&&p.s==='asphalt'){
      // the tarmac Calle Real: yellow edge lines and a pebble pavement on either side (see the Commons photographs)
      ribbon('grdAsphalt',p.p,4.4,YG.l2,3);
      for(const sg of [-1,1]){ribbon('grdYellow',p.p,.12,YG.l3,3,sg*(2.2-.25));ribbon('grdCobble',p.p,1.3,YG.l2,3,sg*(2.2+.65));}
      continue;
    }
    ribbon(st.mat,p.p,st.w,YG.l2,3);
    if(st.mat==='grdGravel'&&p.hw!=='service'){const e=.34;ribbon('grdPebble',p.p,e,YG.l3,3,st.w/2-e/2);ribbon('grdPebble',p.p,e,YG.l3,3,-(st.w/2-e/2));}
    else if(st.calle){const e=.55;ribbon('grdPaving',p.p,e,YG.l3,2.4,st.w/2-e/2);ribbon('grdPaving',p.p,e,YG.l3,2.4,-(st.w/2-e/2));}
  }
}

// ======================================================================= walls and facades
const STOREY0=3.4,STOREY=3.05;
const floorY=k=>k<=0?0:STOREY0+(k-1)*STOREY;
const unitH=lv=>floorY(Math.max(1,lv)+0)||STOREY0;      // eave height for `lv` storeys

// frame of an edge: A,B in plan; t along, n outward. P(s,y,d) = A + t*s + n*d at height y
function edgeFrame(A,B){
  const dx=B[0]-A[0],dz=B[1]-A[1],L=Math.hypot(dx,dz),tx=dx/L,tz=dz/L;
  return {A,B,L,tx,tz,nx:tz,nz:-tx,P:(s,y,d=0)=>[A[0]+tx*s+tz*d,y,A[1]+tz*s-tx*d],N:[tz,0,-tx],T:[tx,0,tz]};
}
// polygon in (s,y) on an edge plane. mat UV = metres (+ offsets)
function wallPoly(mat,F,contour,holes,d,uo,vo,scale=1){
  const C=contour.map(p=>new THREE.Vector2(p[0],p[1])),Hs=holes.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1])));
  const V=[...C,...Hs.flat()];const tris=THREE.ShapeUtils.triangulateShape(C,Hs);
  for(const [a,b,c] of tris){
    const pa=V[a],pb=V[b],pc=V[c];
    tri(mat,F.P(pa.x,pa.y,d),F.P(pb.x,pb.y,d),F.P(pc.x,pc.y,d),[(pa.x+uo)/scale,(pa.y+vo)/scale],[(pb.x+uo)/scale,(pb.y+vo)/scale],[(pc.x+uo)/scale,(pc.y+vo)/scale],F.N);
  }
}
// rectangular reveal around an opening (inside faces)
function reveal(mat,F,s0,s1,y0,y1,depth,uo,vo,withSill=true){
  const P=(s,y,d)=>F.P(s,y,-d);
  // left, right, top, bottom
  quad(mat,P(s0,y0,0),P(s0,y0,depth),P(s0,y1,depth),P(s0,y1,0),[uo,y0],[uo+depth,y0],[uo+depth,y1],[uo,y1],[F.T[0],0,F.T[2]]);
  quad(mat,P(s1,y0,0),P(s1,y1,0),P(s1,y1,depth),P(s1,y0,depth),[uo,y0],[uo,y1],[uo+depth,y1],[uo+depth,y0],[-F.T[0],0,-F.T[2]]);
  quad(mat,P(s0,y1,0),P(s0,y1,depth),P(s1,y1,depth),P(s1,y1,0),[s0,0],[s0,depth],[s1,depth],[s1,0],[0,-1,0]);
  if(withSill)quad(mat,P(s0,y0,0),P(s1,y0,0),P(s1,y0,depth),P(s0,y0,depth),[s0,0],[s1,0],[s1,depth],[s0,depth],[0,1,0]);
}
// arched variant: rectangle with a semicircular head. returns the hole polyline (counter-clockwise in s,y)
function archHole(s0,s1,y0,y1,n=10){
  const r=(s1-s0)/2,cx=(s0+s1)/2,yc=y1-r,pts=[[s0,y0],[s1,y0],[s1,yc]];
  for(let i=1;i<n;i++){const a=Math.PI*i/n;pts.push([cx+Math.cos(a)*r,yc+Math.sin(a)*r]);}
  pts.push([s0,yc]);return pts;
}

// Which part of an edge is outside (visible)? Sample along the edge: the point 0.35 m out must not lie inside a neighbour.
function visiblePanels(u,F,H,others){
  const step=.25,n=Math.max(1,Math.ceil(F.L/step)),res=[];let cur=null;
  for(let i=0;i<n;i++){
    const s=(i+.5)*F.L/n,px=F.A[0]+F.tx*s+F.nx*.35,pz=F.A[1]+F.tz*s+F.nz*.35;
    let blk=0;
    if(u.under&&distPoly(F.A[0]+F.tx*s,F.A[1]+F.tz*s,u.under.o)<.3)blk=u.under.H;for(const o of others){if(px<o.bb[0]-(o.cover||0)||px>o.bb[2]+(o.cover||0)||pz<o.bb[1]-(o.cover||0)||pz>o.bb[3]+(o.cover||0))continue;if(inPoly(px,pz,o.o,o.h)||(o.cover&&distPoly(px,pz,o.o)<o.cover))blk=Math.max(blk,o.H);}
    if(blk>=H-.06){cur=null;continue;}
    const key=Math.round(blk*10);
    if(cur&&cur.key===key){cur.s1=(i+1)*F.L/n;}else{cur={key,y0:blk,s0:i*F.L/n,s1:(i+1)*F.L/n};res.push(cur);}
  }
  return res.filter(p=>p.s1-p.s0>.3);
}

function circleHole(cx,cy,r,n=14){const p=[];for(let i=0;i<n;i++){const a=2*Math.PI*i/n;p.push([cx+Math.cos(a)*r,cy+Math.sin(a)*r]);}return p;}
// reveal of an arched opening that starts at the ground
function revealArch(mat,F,o,depth){
  const r=o.w/2,yc=o.h-r,s0=o.s-r,s1=o.s+r,arc=archPts(o.s,yc,r,10);
  quad(mat,F.P(s0,0,0),F.P(s0,0,-depth),F.P(s0,yc,-depth),F.P(s0,yc,0),[0,0],[depth,0],[depth,yc],[0,yc],F.T);
  quad(mat,F.P(s1,0,0),F.P(s1,yc,0),F.P(s1,yc,-depth),F.P(s1,0,-depth),[0,0],[0,yc],[depth,yc],[depth,0],[-F.T[0],0,-F.T[2]]);
  for(let k=0;k<arc.length-1;k++){const am=Math.PI*(1-(k+.5)/(arc.length-1));quad(mat,F.P(arc[k][0],arc[k][1],0),F.P(arc[k+1][0],arc[k+1][1],0),F.P(arc[k+1][0],arc[k+1][1],-depth),F.P(arc[k][0],arc[k][1],-depth),[k*.3,0],[(k+1)*.3,0],[(k+1)*.3,depth],[k*.3,depth],norm3([-Math.cos(am)*F.T[0],-Math.sin(am),-Math.cos(am)*F.T[2]]));}
}

// ======================================================================= roofs
// Footprints are covered by maximal rectangles (found on a 25 cm raster in the building's own axes). Each rectangle gets
// a hipped or gabled tile roof; the union of such roofs is exactly the straight-skeleton roof of an orthogonal footprint,
// so overlaps only need the depth buffer: valleys appear where two roofs cross. Planar roof UVs are computed from world
// positions, so coplanar overlapping facets (two wings sharing a plane) are pixel-identical.
function dominantAngle(ring){
  let sx=0,sz=0;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const dx=ring[i][0]-ring[j][0],dz=ring[i][1]-ring[j][1],l=Math.hypot(dx,dz),a=Math.atan2(dz,dx);sx+=l*Math.cos(4*a);sz+=l*Math.sin(4*a);}
  return Math.atan2(sz,sx)/4;
}
function distRings(x,z,rings){let d=1e9;for(const r of rings)d=Math.min(d,distPoly(x,z,r));return d;}
function rectCover(u,cell=.25,minDim=2.0,excl=null,maxIt=10,minNew=5.5){
  const th=u.theta,c=Math.cos(th),s=Math.sin(th),rings=[u.o,...u.h];
  const loc=p=>[p[0]*c+p[1]*s,-p[0]*s+p[1]*c];
  let a0=1e9,b0=1e9,a1=-1e9,b1=-1e9;for(const p of u.o){const [a,b]=loc(p);a0=Math.min(a0,a);a1=Math.max(a1,a);b0=Math.min(b0,b);b1=Math.max(b1,b);}
  const nx=Math.ceil((a1-a0)/cell),ny=Math.ceil((b1-b0)/cell),mask=new Uint8Array(nx*ny);let total=0;
  for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const a=a0+(i+.5)*cell,b=b0+(j+.5)*cell,x=a*c-b*s,z=a*s+b*c;
    if(excl&&excl(x,z))continue;
    if(inPoly(x,z,u.o,u.h)||distRings(x,z,rings)<.17){mask[j*nx+i]=1;total++;}}
  const unc=Uint8Array.from(mask),rects=[],W=nx+1;
  for(let it=0;it<maxIt;it++){
    const P=new Int32Array((nx+1)*(ny+1));
    for(let j=0;j<ny;j++){let row=0;for(let i=0;i<nx;i++){row+=unc[j*nx+i];P[(j+1)*W+i+1]=P[j*W+i+1]+row;}}
    const cnt=(x0,y0,x1,y1)=>P[y1*W+x1]-P[y0*W+x1]-P[y1*W+x0]+P[y0*W+x0];
    const hts=new Int32Array(nx);let best=null,bs=0;
    for(let j=0;j<ny;j++){
      for(let i=0;i<nx;i++)hts[i]=mask[j*nx+i]?hts[i]+1:0;
      const st=[];
      for(let i=0;i<=nx;i++){
        const h=i<nx?hts[i]:0;let start=i;
        while(st.length&&st[st.length-1][0]>h){
          const [h0,s0]=st.pop(),x0=s0,x1=i,y0=j-h0+1,y1=j+1;start=s0;
          if((x1-x0)*cell<minDim||(y1-y0)*cell<minDim)continue;
          const nw=cnt(x0,y0,x1,y1);if(nw<=0)continue;const sc=nw+.0005*(x1-x0)*(y1-y0);
          if(sc>bs){bs=sc;best=[x0,y0,x1,y1,nw];}
        }
        if(!st.length||st[st.length-1][0]<h)st.push([h,start]);
      }
    }
    if(!best||best[4]*cell*cell<(it===0?1:minNew)||(minNew>2&&best[4]<.03*total&&it>0))break;
    const [x0,y0,x1,y1]=best;rects.push([a0+x0*cell,b0+y0*cell,a0+x1*cell,b0+y1*cell]);
    for(let j=y0;j<y1;j++)for(let i=x0;i<x1;i++)unc[j*nx+i]=0;
  }
  return rects.map(([aa,bb,ac,bc])=>{
    const ca=(aa+ac)/2,cb=(bb+bc)/2,w=ac-aa,d=bc-bb,cx=ca*c-cb*s,cz=ca*s+cb*c;
    return w>=d?{cx,cz,ux:c,uz:s,hl:w/2,hw:d/2}:{cx,cz,ux:-s,uz:c,hl:d/2,hw:w/2};
  });
}
// planar facet with tile UVs. pts: 3D points ccw seen from above; slope: rise/run; (dnx,dnz): downslope direction
function roofFacet(mat,pts,dnx,dnz,slope,uo,vo){
  const k=Math.sqrt(1+slope*slope),tx=-dnz,tz=dnx;
  const uv=pts.map(p=>[(p[0]*tx+p[2]*tz+uo),(-(p[0]*dnx+p[2]*dnz)*k+vo)]);
  const n=norm3(cross3(sub3(pts[1],pts[0]),sub3(pts[2],pts[0])));const nn=n[1]<0?[-n[0],-n[1],-n[2]]:n;
  for(let i=1;i<pts.length-1;i++)tri(mat,pts[0],pts[i],pts[i+1],uv[0],uv[i],uv[i+1],nn);
}
// one hipped / gabled wing. rc: rectangle (ridge along (ux,uz)); H: wall top
function wing(u,rc,H,st,R,uo,vo){
  const {cx,cz,ux,uz,hl,hw}=rc,ov=st.overhang,slope=st.slope,vx=-uz,vz=ux;
  const wp=(a,b,y)=>[cx+ux*a+vx*b,y,cz+uz*a+vz*b];
  const rings=[u.o,...u.h];
  const endExposed=sgn=>distRings(cx+ux*sgn*hl,cz+uz*sgn*hl,rings)<.55;
  const gable=[0,0];
  if(st.gable&&hl>hw*1.25){for(const k of [0,1])gable[k]=endExposed(k?1:-1)&&R()<st.gable?1:0;}
  const ye=H+.07-ov*slope;                      // height of the eave edge
  const ew=hw+ov;
  const exL=hl+(gable[0]?.18:ov),exR=hl+(gable[1]?.18:ov);
  const rise=Math.min(slope*ew,st.maxRise),rw=Math.max(0,ew-rise/slope);
  const ridgeL=gable[0]?exL:Math.max(0,exL-rise/slope),ridgeR=gable[1]?exR:Math.max(0,exR-rise/slope);
  const yr=ye+rise,mat=st.roof;
  for(const sg of [-1,1]){
    const pts=sg<0?[wp(-exL,-ew,ye),wp(exR,-ew,ye),wp(ridgeR,-rw,yr),wp(-ridgeL,-rw,yr)]:[wp(exR,ew,ye),wp(-exL,ew,ye),wp(-ridgeL,rw,yr),wp(ridgeR,rw,yr)];
    roofFacet(mat,pts,vx*sg,vz*sg,slope,uo,vo);
  }
  for(const k of [0,1]){
    if(gable[k])continue;const sg=k?1:-1,ex=k?exR:exL,rl=k?ridgeR:ridgeL;
    const pts=sg>0?[wp(ex,-ew,ye),wp(ex,ew,ye),wp(rl,rw,yr),wp(rl,-rw,yr)]:[wp(-ex,ew,ye),wp(-ex,-ew,ye),wp(-rl,-rw,yr),wp(-rl,rw,yr)];
    if(rl<.001&&rw<.001)pts.splice(3,1);
    roofFacet(mat,pts,ux*sg,uz*sg,slope,uo,vo);
  }
  if(rw>.05&&ridgeL+ridgeR>.05){
    const p=[wp(-ridgeL,-rw,yr),wp(ridgeR,-rw,yr),wp(ridgeR,rw,yr),wp(-ridgeL,rw,yr)];
    for(let i=1;i<3;i++)tri(mat,p[0],p[i],p[i+1],[p[0][0]+uo,p[0][2]+vo],[p[i][0]+uo,p[i][2]+vo],[p[i+1][0]+uo,p[i+1][2]+vo],[0,1,0]);
  }
  // gable end walls above the eaves
  for(const k of [0,1]){
    if(!gable[k])continue;const sg=k?1:-1,a=sg*hl;
    const poly=[wp(a,-hw,H-.02),wp(a,hw,H-.02),wp(a,hw,H+.07),wp(a,rw,yr),wp(a,-rw,yr),wp(a,-hw,H+.07)];
    const uvf=p=>[(p[0]*ux+p[2]*uz)*1+uo*.3,p[1]];
    for(let i=1;i<poly.length-1;i++)tri(u.st.wall,poly[0],poly[i],poly[i+1],uvf(poly[0]),uvf(poly[i]),uvf(poly[i+1]),[ux*sg,0,uz*sg]);
    bar(mat,wp(a+sg*.1,-ew,ye),wp(a+sg*.1,-rw,yr),.11,1);bar(mat,wp(a+sg*.1,ew,ye),wp(a+sg*.1,rw,yr),.11,1);
  }
  // ridge and hip caps
  const capT=.2;
  if(ridgeL+ridgeR>.2)bar(mat,wp(-ridgeL,0,yr+.05),wp(ridgeR,0,yr+.05),capT,2);
  for(const sg of [-1,1]){
    if(!gable[0])bar(mat,wp(-exL,sg*ew,ye+.05),wp(-ridgeL,sg*rw,yr+.05),capT*.85,2);
    if(!gable[1])bar(mat,wp(exR,sg*ew,ye+.05),wp(ridgeR,sg*rw,yr+.05),capT*.85,2);
  }
  // chimney near a ridge end
  if(st.chimney&&R()<st.chimney&&ridgeL+ridgeR>1.0&&!u.noChimney){
    const a=(R()<.5?1:-1)*Math.max(0,(R()<.5?ridgeR:ridgeL)-.7),p=wp(a,.15,0);chimney(u,p[0],p[2],yr-.2,yr+1.15,st,R,ux,uz);
  }
  // eaves where the edge lies on the building outline: fascia, soffit, rafter ends
  const doEdge=(a0,b0,a1,b1,nx,nz)=>{
    const L=Math.hypot(a1-a0,b1-b0),n=Math.max(1,Math.round(L/1.0));
    for(let i=0;i<n;i++){
      const t0=i/n,t1=(i+1)/n,P0=wp(lerp(a0,a1,t0),lerp(b0,b1,t0),ye),P1=wp(lerp(a0,a1,t1),lerp(b0,b1,t1),ye);
      const mx=(P0[0]+P1[0])/2-nx*ov,mz=(P0[2]+P1[2])/2-nz*ov;
      if(distRings(mx,mz,rings)>.65)continue;
      quad(mat,[P0[0],ye-.15,P0[2]],[P1[0],ye-.15,P1[2]],[P1[0],ye,P1[2]],[P0[0],ye,P0[2]],[0,0],[1,0],[1,.15],[0,.15],[nx,0,nz]);
      quad('grdWood',[P0[0]-nx*ov,H,P0[2]-nz*ov],[P1[0]-nx*ov,H,P1[2]-nz*ov],[P1[0],ye-.15,P1[2]],[P0[0],ye-.15,P0[2]],[0,0],[1,0],[1,ov],[0,ov],[0,-1,0]);
      if(st.rafters&&!LOW){
        const len=Math.hypot(P1[0]-P0[0],P1[2]-P0[2]),m=Math.max(1,Math.round(len/.6));
        for(let k=0;k<m;k++){const t=(k+.5)/m,px=lerp(P0[0],P1[0],t),pz=lerp(P0[2],P1[2],t);
          bar('grdBeam',[px-nx*ov,H-.09,pz-nz*ov],[px+nx*.07,ye-.23,pz+nz*.07],.1,1,1);}
      }
    }
  };
  doEdge(-exL,-ew,exR,-ew,-vx,-vz);doEdge(exR,ew,-exL,ew,vx,vz);
  if(!gable[0])doEdge(-exL,ew,-exL,-ew,-ux,-uz);
  if(!gable[1])doEdge(exR,-ew,exR,ew,ux,uz);
}

// ======================================================================= path index (front facades, trees, nav)
let PIDX=null;
function pathIndex(){
  if(PIDX)return PIDX;const cell=16,g=new Map();
  for(const p of DATA.PATHS){const st=pathStyle(p);for(let i=1;i<p.p.length;i++){const a=p.p[i-1],b=p.p[i],x0=Math.floor((Math.min(a[0],b[0])-st.w)/cell),x1=Math.floor((Math.max(a[0],b[0])+st.w)/cell),z0=Math.floor((Math.min(a[1],b[1])-st.w)/cell),z1=Math.floor((Math.max(a[1],b[1])+st.w)/cell);
    for(let x=x0;x<=x1;x++)for(let z=z0;z<=z1;z++){const k=x+','+z;if(!g.has(k))g.set(k,[]);g.get(k).push([a,b,st.w/2,st.calle]);}}}
  return PIDX={cell,g};
}
// distance to the edge of the nearest path (negative on it) and whether it is Calle Real
function pathNear(x,z){
  const {cell,g}=pathIndex();let best=1e9,calle=false;const cx=Math.floor(x/cell),cz=Math.floor(z/cell);
  for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++){const l=g.get((cx+dx)+','+(cz+dz));if(!l)continue;for(const [a,b,hw,c] of l){const d=distSeg(x,z,a,b)-hw;if(d<best){best=d;calle=c;}}}
  return {d:best,calle};
}

// ======================================================================= styles
const PLASTERS=[['grdWhite','grdWhiteB',.26],['grdCream','grdWhiteB',.2],['grdOchre','grdOchreB',.2],['grdRose','grdRoseB',.14],['grdSalmon','grdRoseB',.1],['grdSand','grdWhiteB',.1]];
function pick(list,r){let t=0;for(const x of list)t+=x[2]??1;let v=r*t;for(const x of list){v-=x[2]??1;if(v<=0)return x;}return list[list.length-1];}
function inParador(u){return u.cx>165&&u.cx<290&&u.cx>0&&u.cz>115&&u.cz<200;}
function styleFor(u){
  const R=rng(u.id*31+7);
  const parador=inParador(u);
  const st={slope:.34+R()*.08,maxRise:3.4,overhang:.6,rafters:true,gable:.35,bay:2.7+R()*.7,plinth:R()<.55,quoins:R()<.4,surround:true,balcony:.55,shutters:true,front:true,
    surroundW:.13,surroundRelief:R()<.35,archDoor:.3,archTop:R()<.35,archAll:false,round:.25,shops:true,sill:'grdStone',slab:R()<.5?'grdStone':'grdWhite',doorStone:'grdStone',doorMat:'grdWoodDoor'};
  const shut=[['grdShutterG',.5],['grdShutterB',.25],['grdShutterN',.1],[null,.15]];let r=R(),acc=0;st.shutter=null;for(const [m,p] of shut){acc+=p;if(r<=acc){st.shutter=m;break;}}
  st.frame=st.shutter==='grdShutterB'?'grdFrameD':R()<.7?'grdFrame':'grdFrameD';
  st.roof=R()<.65?'grdRoof':'grdRoofOld';
  if(R()<.4){st.eave='cornice';st.rafters=false;st.overhang=.38;}else st.eave='beams';
  if(parador){
    st.wall='grdRender';st.wallB='grdRender';st.trim='grdRenderTrim';st.plinthMat='grdBrickB';st.brick=true;st.plinth=true;st.quoins=false;st.surround=true;st.surroundRelief=false;
    st.shutter=null;st.frame='grdFrameD';st.balcony=.75;st.gable=.4;st.slope=.28;st.maxRise=2.6;st.overhang=.55;st.roof='grdRoofOld';st.eave='dentil';st.rafters=false;st.shops=false;
    st.doorStone='grdBrickB';st.sill='grdBrickB';st.slab='grdBrickB';st.archDoor=.5;st.archTop=false;st.round=0;st.stringCourse=false;st.flowers=.15;st.chimney=.7;st.surroundW=.1;st.plinthH=.55;
  }else{
    const p=pick(PLASTERS,R());st.wall=p[0];st.wallB=p[1];st.trim=p[0]==='grdWhite'?'grdStone':'grdWhite';st.plinthMat=R()<.5?'grdStone':'grdBrickB';
    st.stringCourse=R()<.55;st.chimney=.55;st.flowers=.35;
  }
  return st;
}

const DEFAULT_ST={slope:.4,maxRise:3,overhang:.6,rafters:true,gable:0,bay:3.2,plinth:false,quoins:false,surround:true,balcony:0,shutter:null,frame:'grdFrame',roof:'grdRoof',wall:'grdWhite',wallB:'grdWhiteB',trim:'grdStone',plinthMat:'grdStone',eave:'beams',
  surroundW:.13,surroundRelief:false,archDoor:.3,archTop:false,archAll:false,round:0,shops:false,sill:'grdStone',slab:'grdStone',doorStone:'grdStone',doorMat:'grdWoodDoor',stringCourse:false,chimney:0,flowers:0};

// ======================================================================= openings
// Edge types: 'street' (Calle Real), 'lane' (any other path), 'back'. Every ground-floor bay is a door, a shop, a barred
// window or blank; upper bays are balcony doors, sash windows, arched or round attic lights. Axes line up between floors.
function layoutEdge(u,F,kind,R,st){
  const ops=tunnelOps(F),L=F.L;if(L<2.1)return ops;
  const front=kind!=='back';
  const bay=st.bay*(.88+R()*.26),margin=Math.min(.95,L*.27),usable=L-2*margin,nb=Math.max(1,Math.round(usable/bay));
  const doorBay=front&&L>3.4?Math.min(nb-1,Math.floor(R()*nb)):(L>7&&R()<.25?Math.floor(R()*nb):-1);
  let shopBays=new Set();
  if(kind==='street'&&st.shops&&nb>=3){const n=nb>=5&&R()<.5?2:1;for(let k=0;k<n;k++){let i=Math.floor(R()*nb);if(i!==doorBay)shopBays.add(i);}}
  for(let i=0;i<nb;i++){
    const c=nb===1?L/2:margin+usable*(i+.5)/nb,w=Math.min(usable/nb-.8,1.2);
    for(let k=0;k<u.lv;k++){
      const yf=floorY(k),top=k===u.lv-1;
      if(k===0){
        if(i===doorBay)ops.push({type:'door',s:c,w:1.1+R()*.35,y0:0,h:2.45+R()*.25,arch:R()<st.archDoor,double:R()<.35});
        else if(shopBays.has(i)&&usable/nb>2.4)ops.push({type:'shop',s:c,w:Math.min(2.5,usable/nb-.7),y0:0,h:2.7,arch:R()<.5,sign:Math.floor(R()*SIGNS.length),awn:R()<.6,awnCol:Math.floor(R()*AWN.length)});
        else if(R()<(front?.9:.55))ops.push({type:'reja',s:c,w:.9+R()*.15,y0:yf+.98,h:1.25+R()*.15,bulge:R()<.3});
        continue;
      }
      if(front){
        if(k===1&&R()<st.balcony&&u.lv>=2)ops.push({type:'balcony',s:c,w:1.0+R()*.1,y0:yf+.04,h:2.1+R()*.1,arch:st.archTop&&R()<.3});
        else if(R()<.93){
          const attic=top&&u.lv>=3&&R()<.4,round=top&&u.lv>=2&&R()<st.round;
          if(round)ops.push({type:'round',s:c,w:.7,y0:yf+1.3,h:.7});
          else ops.push({type:'win',s:c,w:attic?.8:.95+R()*.12,y0:yf+(attic?1.0:.92),h:attic?1.1:1.4+R()*.1,shut:!!st.shutter&&R()<.85,arch:(top||st.archAll)&&st.archTop&&R()<.55});
        }
      }else if(R()<.55){ops.push({type:'win',s:c,w:.9,y0:yf+.95,h:1.3,shut:false});}
    }
  }
  return ops;
}

// ---------- shop signs: one canvas atlas, per-sign UV rectangles (generic trades, no brands)
const SIGNS=['CERÁMICA','LIBRERÍA','ARTESANÍA','SOUVENIRS','TABERNA','HELADOS','BAR','JOYERÍA'];
const SIGN_COL=[['#2f5b4a','#f3e6c4'],['#7a2f2b','#f1dfb5'],['#24415f','#f0e8d2'],['#5b3b22','#ecd9a8'],['#1f1f1f','#e8c36a'],['#2c5c68','#f6efe0'],['#8a5a1c','#f6e8c8'],['#43304f','#e9d9a6']];
const AWN=[['#b8372f','#f4ead4'],['#2d5d7a','#f4ead4'],['#3c6b3e','#f4ead4'],['#d19a2a','#f4ead4'],['#7b3b2a','#e9d7b3']];
let MAT_SIGN_UV=null;
function signRect(i){const c=i%2,r=Math.floor(i/2);return [c*.5,1-(r+1)*.25,(c+1)*.5,1-r*.25];}
// ---------- opening building blocks
function frameBars(F,s0,s1,y0,y1,d,mat,panes=2){
  const P=(s,y)=>F.P(s,y,-d);
  if(panes>=2){const sm=(s0+s1)/2;quad(mat,P(sm-.022,y0),P(sm+.022,y0),P(sm+.022,y1),P(sm-.022,y1),[0,0],[1,0],[1,1],[0,1],F.N);}
  const ym=y0+(y1-y0)*.64;quad(mat,P(s0,ym-.022),P(s1,ym-.022),P(s1,ym+.022),P(s0,ym+.022),[0,0],[1,0],[1,1],[0,1],F.N);
}
function frameRing(F,s0,s1,y0,y1,d,t,mat){
  const P=(s,y)=>F.P(s,y,-d),N=F.N,Q=(a,b,c,e)=>quad(mat,P(a,b),P(c,b),P(c,e),P(a,e),[0,0],[1,0],[1,1],[0,1],N);
  Q(s0,y0,s0+t,y1);Q(s1-t,y0,s1,y1);Q(s0+t,y1-t,s1-t,y1);Q(s0+t,y0,s1-t,y0+t);
}
function glazing(F,s0,s1,y0,y1,gd,R,st){
  const kind=R();
  const gm=kind<.52?'grdGlass':kind<.70?'grdCurtain':kind<.82?'grdCurtain2':kind<.9?'grdBlind':'grdDark',gu=R()*.5;
  quad(gm,F.P(s0,y0,-gd),F.P(s1,y0,-gd),F.P(s1,y1,-gd),F.P(s0,y1,-gd),[gu,0],[gu+.5,0],[gu+.5,1],[gu,1],F.N);
}
function pot(x,y,z,s=1){
  if(LOW)return;
  obox('grdTerracotta',x,z,1,0,.1*s,.1*s,y,y+.07*s,1,true);prismN('grdTerracotta',x,z,.13*s,y+.07*s,y+.27*s,8,0,1,true);
  prismN('grdHedge',x,z,.12*s,y+.27*s,y+.33*s,8,0,1,true);
  const bl=[[.12,.1],[-.1,.13],[.02,-.14]];
  for(let i=0;i<3;i++)blob(i%2?'flower':'whiteFlower',x+bl[i][0]*s,y+.36*s,z+bl[i][1]*s,.06*s);
}
function windowDecor(u,F,o,st,uo,front,R){
  const s0=o.s-o.w/2,s1=o.s+o.w/2,y0=o.y0,y1=o.y0+o.h,N=F.N,fm=st.frame;
  const gd=.2;
  glazing(F,s0,s1,y0,y1,gd,R,st);
  frameRing(F,s0,s1,y0,y1,gd-.03,.055,fm);frameBars(F,s0,s1,y0,y1,gd-.03,fm,o.w>.85?2:1);
  // sash relief: a thin step round the glass towards the room
  if(st.surround&&(front||R()<.4)){
    const b=st.surroundW,d=.012+(st.surroundRelief?.02:0),tm=st.trim;
    const Q=(a0,b0,a1,b1)=>quad(tm,F.P(a0,b0,d),F.P(a1,b0,d),F.P(a1,b1,d),F.P(a0,b1,d),[a0+uo,b0],[a1+uo,b0],[a1+uo,b1],[a0+uo,b1],N);
    Q(s0-b,y0-b,s0,y1+b);Q(s1,y0-b,s1+b,y1+b);Q(s0,y1,s1,y1+b);
    if(o.type!=='balcony')Q(s0,y0-b,s1,y0);
    if(st.surroundRelief){const e=d,sd=(a,b2,c,e2,dd)=>quad(tm,F.P(a,b2,dd),F.P(c,b2,dd),F.P(c,e2,dd),F.P(a,e2,dd),[0,0],[1,0],[1,1],[0,1],N);
      // projecting lintel
      const lc=F.P(o.s,0,d+.03);obox(tm,lc[0],lc[2],F.tx,F.tz,o.w/2+b+.05,.03,y1+b,y1+b+.1,1,true);}
  }
  if((o.type==='win'||o.type==='reja')&&front&&st.flowers&&R()<st.flowers&&!o.shut){flowerBox(F,o.s,y0-.02,o.w*.9,R);}
  if(o.type==='win'||o.type==='reja'){const sc=F.P(o.s,y0-.03,.06);obox(st.sill,sc[0],sc[2],F.tx,F.tz,o.w/2+.1,.08,y0-.07,y0+.0,1,true);}
  if(o.type==='reja'){
    const d=o.bulge?.17:.07,uu=o.w/.5;
    if(o.bulge){ // reja volada: the grille bellies out
      const dd=.16,A=F.P(s0-.02,y0-.02,dd),B=F.P(s1+.02,y0-.02,dd),C=F.P(s1+.02,y1+.02,dd),D=F.P(s0-.02,y1+.02,dd);
      quad('grdGrille',A,B,C,D,[0,0],[uu,0],[uu,1],[0,1],N);
      for(const sg of [0,1]){const sx=sg?s1+.02:s0-.02;quad('grdGrille',F.P(sx,y0-.02,.0),F.P(sx,y0-.02,dd),F.P(sx,y1+.02,dd),F.P(sx,y1+.02,.0),[0,0],[.35,0],[.35,1],[0,1],[sg?F.T[0]:-F.T[0],0,sg?F.T[2]:-F.T[2]]);}
      quad('grdIron',F.P(s0-.02,y1+.02,0),F.P(s1+.02,y1+.02,0),F.P(s1+.02,y1+.02,dd),F.P(s0-.02,y1+.02,dd),[0,0],[1,0],[1,1],[0,1],[0,1,0]);
    }else quad('grdGrille',F.P(s0-.02,y0-.02,d),F.P(s1+.02,y0-.02,d),F.P(s1+.02,y1+.02,d),F.P(s0-.02,y1+.02,d),[0,0],[uu,0],[uu,1],[0,1],N);
  }
  if((o.type==='win')&&o.shut&&st.shutter){
    const w2=o.w/2,d=.05,mat=st.shutter;
    quad(mat,F.P(s0-w2,y0,d),F.P(s0,y0,d),F.P(s0,y1,d),F.P(s0-w2,y1,d),[.5,0],[0,0],[0,o.h],[.5,o.h],N);
    quad(mat,F.P(s1,y0,d),F.P(s1+w2,y0,d),F.P(s1+w2,y1,d),F.P(s1,y1,d),[0,0],[.5,0],[.5,o.h],[0,o.h],N);
    // hinges
    if(!LOW)    for(const [x,sg] of [[s0,-1],[s1,1]])for(const yy of [y0+.25,y1-.25]){const h=F.P(x,yy,.06);bar('grdIron',[h[0],h[1],h[2]],[h[0]+F.tx*sg*.16,h[1],h[2]+F.tz*sg*.16],.025,1);}
  }
  if(o.type==='balcony'){
    const proud=.55,slabW=o.w+.7,yf=y0-.04;
    const c=F.P(o.s,0,proud/2);
    obox(st.slab,c[0],c[2],F.tx,F.tz,slabW/2,proud/2,yf-.13,yf,1,true,true);
    for(const sg of [-1,1]){const cc=F.P(o.s+sg*(slabW/2-.2),0,.2);obox('grdStone',cc[0],cc[2],F.tx,F.tz,.07,.2,yf-.38,yf-.13,1,false,false);}
    const rh=.95,ry=yf,ww=slabW-.06;
    quad('grdRailing',F.P(o.s-ww/2,ry,proud-.03),F.P(o.s+ww/2,ry,proud-.03),F.P(o.s+ww/2,ry+rh,proud-.03),F.P(o.s-ww/2,ry+rh,proud-.03),[0,0],[ww/.5,0],[ww/.5,1],[0,1],N);
    for(const sg of [-1,1]){const sx=o.s+sg*(ww/2);quad('grdRailing',F.P(sx,ry,0),F.P(sx,ry,proud-.03),F.P(sx,ry+rh,proud-.03),F.P(sx,ry+rh,0),[0,0],[(proud)/.5,0],[(proud)/.5,1],[0,1],[F.T[0]*sg,0,F.T[2]*sg]);}
    if(st.shutter&&R()<.85){const w2=o.w/2,d2=.05;
      quad(st.shutter,F.P(s0-w2,y0,d2),F.P(s0,y0,d2),F.P(s0,y1,d2),F.P(s0-w2,y1,d2),[.5,0],[0,0],[0,o.h],[.5,o.h],N);
      quad(st.shutter,F.P(s1,y0,d2),F.P(s1+w2,y0,d2),F.P(s1+w2,y1,d2),F.P(s1,y1,d2),[0,0],[.5,0],[.5,o.h],[0,o.h],N);}
    if(R()<.7){const n=1+Math.floor(R()*3);for(let k=0;k<n;k++){const px=o.s+(R()-.5)*(ww-.4),pp=F.P(px,yf,proud-.12);pot(pp[0],yf,pp[2],1);}}
  }
}
// round attic light (oculus) and arched windows
function roundDecor(u,F,o,st,uo,R){
  const r=o.w/2,y=o.y0+r,n=12,N=F.N,rr=r+.1;
  for(let i=0;i<n;i++){const a0=2*Math.PI*i/n,a1=2*Math.PI*(i+1)/n;
    tri('grdGlass',F.P(o.s,y,-.15),F.P(o.s+Math.cos(a0)*r,y+Math.sin(a0)*r,-.15),F.P(o.s+Math.cos(a1)*r,y+Math.sin(a1)*r,-.15),[.25,y*.4],[.25+Math.cos(a0)*r*.4,(y+Math.sin(a0)*r)*.4],[.25+Math.cos(a1)*r*.4,(y+Math.sin(a1)*r)*.4],N);
    quad(st.trim,F.P(o.s+Math.cos(a0)*r,y+Math.sin(a0)*r,.015),F.P(o.s+Math.cos(a1)*r,y+Math.sin(a1)*r,.015),F.P(o.s+Math.cos(a1)*rr,y+Math.sin(a1)*rr,.015),F.P(o.s+Math.cos(a0)*rr,y+Math.sin(a0)*rr,.015),[i*.2,0],[(i+1)*.2,0],[(i+1)*.2,.1],[i*.2,.1],N);
    quad(st.frame,F.P(o.s+Math.cos(a0)*r,y+Math.sin(a0)*r,-.12),F.P(o.s+Math.cos(a1)*r,y+Math.sin(a1)*r,-.12),F.P(o.s+Math.cos(a1)*(r-.05),y+Math.sin(a1)*(r-.05),-.12),F.P(o.s+Math.cos(a0)*(r-.05),y+Math.sin(a0)*(r-.05),-.12),[0,0],[1,0],[1,1],[0,1],N);
    // reveal
    {const am=(a0+a1)/2;quad(st.wall,F.P(o.s+Math.cos(a0)*r,y+Math.sin(a0)*r,0),F.P(o.s+Math.cos(a1)*r,y+Math.sin(a1)*r,0),F.P(o.s+Math.cos(a1)*r,y+Math.sin(a1)*r,-.15),F.P(o.s+Math.cos(a0)*r,y+Math.sin(a0)*r,-.15),[0,0],[1,0],[1,1],[0,1],norm3([-Math.cos(am)*F.T[0],-Math.sin(am),-Math.cos(am)*F.T[2]]));}
  }
  const bb=F.P(o.s,y,-.12);bar(st.frame,F.P(o.s-r,y,-.12),F.P(o.s+r,y,-.12),.04,1);bar(st.frame,F.P(o.s,y-r,-.12),F.P(o.s,y+r,-.12),.04,1);
}
function doorDecor(u,F,o,st,uo,R){
  const s0=o.s-o.w/2,s1=o.s+o.w/2,y1=o.h,N=F.N;
  if(o.tunnel){tunnelMouth(F,o);return;}
  const d=.22,yh=o.arch?y1-o.w/2:y1,wm=st.doorMat||'grdWoodDoor';
  quad(wm,F.P(s0,0,-d),F.P(s1,0,-d),F.P(s1,yh,-d),F.P(s0,yh,-d),[0,0],[o.w,0],[o.w,yh],[0,yh],N);
  // door leaf detailing: raised panels / studs / central joint
  const ds=-d+.02;
  if(o.double)bar('grdDark',F.P(o.s,.05,ds),F.P(o.s,yh-.05,ds),.025,1);
  const pw=(o.w-.3)/(o.double?2:1)-.1,ph=(yh-.5)/2-.1;
  for(let c=0;c<(o.double?2:1);c++){const cx=o.double?o.s+(c?1:-1)*(o.w/4):o.s;for(const py of [.2,.2+ph+.1]){const q0=py,q1=py+ph;
    quad('grdDoorPanel',F.P(cx-pw/2,q0,ds),F.P(cx+pw/2,q0,ds),F.P(cx+pw/2,q1,ds),F.P(cx-pw/2,q1,ds),[0,0],[1,0],[1,1],[0,1],N);}}
  if(R()<.6)for(let k=0;k<5;k++){const sp=F.P(o.s+(o.double?0:o.w*.28)+(k-2)*.0,.9+k*.22,ds);}
  // handle ring
  const hp=F.P(o.s+(o.double?.12:o.w*.32),1.05,ds+.01);prismN('grdIron',hp[0],hp[2],.035,1.02,1.08,6,0,1,true);
  if(o.arch){ // fanlight and stone voussoirs
    const r=o.w/2,yc=y1-r,n=10;
    for(let i=0;i<n;i++){const a0=Math.PI*i/n,a1=Math.PI*(i+1)/n;
      const p0=F.P(o.s+Math.cos(a0)*r,yc+Math.sin(a0)*r,-d),p1=F.P(o.s+Math.cos(a1)*r,yc+Math.sin(a1)*r,-d),c=F.P(o.s,yc,-d);
      tri('grdGlass',c,p0,p1,[.25,yc*.4],[.25+Math.cos(a0)*r*.4,(yc+Math.sin(a0)*r)*.4],[.25+Math.cos(a1)*r*.4,(yc+Math.sin(a1)*r)*.4],N);
      const q0=F.P(o.s+Math.cos(a0)*(r+.22),yc+Math.sin(a0)*(r+.22),.03),q1=F.P(o.s+Math.cos(a1)*(r+.22),yc+Math.sin(a1)*(r+.22),.03),r0=F.P(o.s+Math.cos(a0)*r,yc+Math.sin(a0)*r,.03),r1=F.P(o.s+Math.cos(a1)*r,yc+Math.sin(a1)*r,.03);
      quad(st.doorStone,r0,r1,q1,q0,[a0,0],[a1,0],[a1,.3],[a0,.3],N);}
    bar(st.doorMat||'grdWoodDoor',F.P(s0,yc,-d+.01),F.P(s1,yc,-d+.01),.05,1);
  }else{
    const hw=.2,lc=F.P(o.s,0,.05);
    obox(st.doorStone,lc[0],lc[2],F.tx,F.tz,o.w/2+hw+.04,.07,y1,y1+.22,1,true);
    for(const sg of [-1,1]){const jc=F.P(o.s+sg*(o.w/2+hw/2),0,.05);obox(st.doorStone,jc[0],jc[2],F.tx,F.tz,hw/2,.07,0,y1,1,false);}
    // transom light above the door
    glazing(F,s0+.05,s1-.05,y1-.5,y1-.04,.2,R,st);
  }
  const sc=F.P(o.s,0,.25);obox('grdStone',sc[0],sc[2],F.tx,F.tz,o.w/2+.1,.28,-.1,.13,1,true);
  // doorstep lantern / number plaque
  if(R()<.5){const pp=F.P(s1+.5,1.7,.02);quad('grdTilePlaque',pp,F.P(s1+.5+.2,1.7,.02),F.P(s1+.5+.2,1.9,.02),F.P(s1+.5,1.9,.02),[1,0],[0,0],[0,1],[1,1],N);}
}
function shopDecor(u,F,o,st,uo,R){
  const s0=o.s-o.w/2,s1=o.s+o.w/2,N=F.N,h=o.h,dd=.28;
  // recess: glass, door and a dark interior
  const arch=o.arch,yh=arch?h-o.w/2:h;
  quad('grdGlass',F.P(s0+.08,.45,-dd),F.P(s1-.08,.45,-dd),F.P(s1-.08,yh-.1,-dd),F.P(s0+.08,yh-.1,-dd),[0,0],[1,0],[1,1],[0,1],N);
  quad('grdFrameD',F.P(s0,0,-dd+.01),F.P(s1,0,-dd+.01),F.P(s1,.45,-dd+.01),F.P(s0,.45,-dd+.01),[0,0],[1,0],[1,1],[0,1],N);
  const vm=F.P(o.s,0,-dd+.02);
  const dw=.82,dx=o.s+(o.w/2-dw/2-.1);
  quad('grdWoodDoor',F.P(dx-dw/2,0,-dd+.03),F.P(dx+dw/2,0,-dd+.03),F.P(dx+dw/2,2.15,-dd+.03),F.P(dx-dw/2,2.15,-dd+.03),[0,0],[1,0],[1,1],[0,1],N);
  quad('grdGlass',F.P(dx-dw/2+.12,1.0,-dd+.04),F.P(dx+dw/2-.12,1.0,-dd+.04),F.P(dx+dw/2-.12,2.0,-dd+.04),F.P(dx-dw/2+.12,2.0,-dd+.04),[0,0],[1,0],[1,1],[0,1],N);
  for(const x of [o.s-o.w*.2,o.s+o.w*.05])bar('grdFrameD',F.P(x,.45,-dd+.02),F.P(x,yh-.1,-dd+.02),.05,1);
  bar('grdFrameD',F.P(s0+.08,yh*.78,-dd+.02),F.P(s1-.08,yh*.78,-dd+.02),.05,1);
  // goods on the sill: pots and ceramic plates (shop windows)
  for(let k=0;k<4;k++){const x=s0+.3+R()*(o.w-1.4),p=F.P(x,.5,-dd+.2);prismN('grdTerracotta',p[0],p[2],.12+R()*.06,.45,.45+.2+R()*.15,8,0,1,true);}
  // jambs and lintel round the opening
  const hw=.2;
  for(const sg of [-1,1]){const c=F.P(o.s+sg*(o.w/2+hw/2),0,-.02);obox(st.doorStone,c[0],c[2],F.tx,F.tz,hw/2,.17,0,yh,1,false);}
  if(arch){const r=o.w/2,yc=h-r,n=12;
    for(let i=0;i<n;i++){const a0=Math.PI*i/n,a1=Math.PI*(i+1)/n;
      tri('grdGlass',F.P(o.s,yc,-dd),F.P(o.s+Math.cos(a0)*(r-.08),yc+Math.sin(a0)*(r-.08),-dd),F.P(o.s+Math.cos(a1)*(r-.08),yc+Math.sin(a1)*(r-.08),-dd),[.25,yc*.4],[.25+Math.cos(a0)*r*.4,(yc+Math.sin(a0)*r)*.4],[.25+Math.cos(a1)*r*.4,(yc+Math.sin(a1)*r)*.4],N);
      quad(st.doorStone,F.P(o.s+Math.cos(a0)*r,yc+Math.sin(a0)*r,.03),F.P(o.s+Math.cos(a1)*r,yc+Math.sin(a1)*r,.03),F.P(o.s+Math.cos(a1)*(r+.24),yc+Math.sin(a1)*(r+.24),.03),F.P(o.s+Math.cos(a0)*(r+.24),yc+Math.sin(a0)*(r+.24),.03),[0,0],[1,0],[1,1],[0,1],N);}
  }else{const lc=F.P(o.s,0,.05);obox(st.doorStone,lc[0],lc[2],F.tx,F.tz,o.w/2+hw+.04,.17,h,h+.2,1,true);}
  // awning over the opening, hanging sign on an iron bracket
  if(o.awn){
    const [c1,c2]=AWN[o.awnCol],yA=h+.02,yB=h-.55,out=1.1,aw=o.w+.5,A0=F.P(o.s-aw/2,yA,.04),A1=F.P(o.s+aw/2,yA,.04),B1=F.P(o.s+aw/2,yB,out),B0=F.P(o.s-aw/2,yB,out);
    quad('grdAwning'+o.awnCol,A0,A1,B1,B0,[0,0],[aw*3,0],[aw*3,1.2],[0,1.2],null);
    quad('grdAwning'+o.awnCol,B0,B1,[B1[0],B1[1]-.18,B1[2]],[B0[0],B0[1]-.18,B0[2]],[0,1.2],[aw*3,1.2],[aw*3,1.5],[0,1.5],F.N);
    for(const sg of [-1,1]){const x=o.s+sg*aw/2;quad('grdAwning'+o.awnCol,F.P(x,yA,.04),F.P(x,yB,out),F.P(x,yB-.18,out),F.P(x,yA-.0,.04),[0,0],[1,0],[1,1],[0,1],[sg*F.T[0],0,sg*F.T[2]]);}
  }else{
    const [sx0,sy0,sx1,sy1]=signRect(o.sign),sw=Math.min(o.w+.2,2.2),sh=.34,y=h+.4;
    const A=F.P(o.s-sw/2,y,.06),B=F.P(o.s+sw/2,y,.06),C=F.P(o.s+sw/2,y+sh,.06),D=F.P(o.s-sw/2,y+sh,.06);
    quad('grdSign',A,B,C,D,[sx1,sy0],[sx0,sy0],[sx0,sy1],[sx1,sy1],N);
  }
  // hanging flag sign (bandera) for some shops
  if(!o.awn||R()<.4){const [sx0,sy0,sx1,sy1]=signRect((o.sign+3)%SIGNS.length),bx=o.s+(R()<.5?-1:1)*(o.w/2+.55),by=2.9,arm=.75;
    const base=F.P(bx,by,.02),tip=F.P(bx,by,arm);bar('grdIron',base,tip,.03,1);bar('grdIron',[base[0],by-.28,base[2]],[tip[0]-F.nx*.06,by,tip[2]-F.nz*.06],.02,1);
    for(const sg of [1,-1]){const A=F.P(bx-F.tx*0+(sg>0?-.0:0),by-.1,arm-.1),a=F.P(bx-.3,by-.1,arm-.05),b=F.P(bx+.3,by-.1,arm-.05),c2=F.P(bx+.3,by-.5,arm-.05),d2=F.P(bx-.3,by-.5,arm-.05);
      if(sg>0)quad('grdSign',a,b,c2,d2,[sx1,sy0],[sx0,sy0],[sx0,sy1],[sx1,sy1],N);else quad('grdSign',b,a,d2,c2,[sx1,sy0],[sx0,sy0],[sx0,sy1],[sx1,sy1],[-F.N[0],0,-F.N[2]]);}}
}
function tunnelMouth(F,o){
  const r=o.w/2,yc=o.h-r,n=12;
  for(let i=0;i<n;i++){const a0=Math.PI*i/n,a1=Math.PI*(i+1)/n,
    r0=F.P(o.s+Math.cos(a0)*r,yc+Math.sin(a0)*r,.04),r1=F.P(o.s+Math.cos(a1)*r,yc+Math.sin(a1)*r,.04),q0=F.P(o.s+Math.cos(a0)*(r+.3),yc+Math.sin(a0)*(r+.3),.04),q1=F.P(o.s+Math.cos(a1)*(r+.3),yc+Math.sin(a1)*(r+.3),.04);
    quad('grdStone',r0,r1,q1,q0,[i*.3,0],[(i+1)*.3,0],[(i+1)*.3,.3],[i*.3,.3],F.N);}
  for(const sg of [-1,1])quad('grdStone',F.P(o.s+sg*r,0,.04),F.P(o.s+sg*(r+.3),0,.04),F.P(o.s+sg*(r+.3),yc,.04),F.P(o.s+sg*r,yc,.04),[0,0],[.3,0],[.3,yc],[0,yc],F.N);
}

// ======================================================================= building units
function mkUnit(o){
  const ring=ringArea(o.o)<0?[...o.o].reverse():o.o,h=(o.h||[]).map(r=>ringArea(r)>0?[...r].reverse():r);
  const [cx,cz]=centroid(ring);
  const u={lv:1,name:'',part:true,bt:'',ru:'',...o,o:ring,h,cx,cz,bb:bbox(ring)};if(o.st)u.st={...DEFAULT_ST,...o.st};
  u.theta=o.theta??dominantAngle(ring);u.H=o.H;return u;
}
function rectPoly(cx,cz,ux,uz,hl,hw){const vx=-uz,vz=ux;return [[cx-ux*hl-vx*hw,cz-uz*hl-vz*hw],[cx+ux*hl-vx*hw,cz+uz*hl-vz*hw],[cx+ux*hl+vx*hw,cz+uz*hl+vz*hw],[cx-ux*hl+vx*hw,cz-uz*hl+vz*hw]];}
function prepUnits(){
  const units=[];
  for(const d of DATA.BLD){
    if(d.id===28627||d.id===92528627)continue;       // stray wall tower in the north wall
    const o=ringArea(d.o)<0?[...d.o].reverse():d.o,h=d.h.map(r=>ringArea(r)>0?[...r].reverse():r);
    const [cx,cz]=centroid(o);
    const u={id:d.id,lv:Math.max(1,d.lv||1),name:d.n,part:d.part,bt:d.bt,ru:d.ru,o,h,cx,cz,bb:bbox(o)};
    u.theta=dominantAngle(o);u.H=unitH(u.lv);u.brick=false;
    units.push(u);
  }
  return units;
}
function buildPanelWall(u,F,pn,ops,H,st,uo,front,R){
  const mat=st.wall;const doors=ops.filter(o=>(o.type==='door'||o.type==='shop')&&pn.y0<.05&&o.s-o.w/2>pn.s0+.35&&o.s+o.w/2<pn.s1-.35).sort((a,b)=>a.s-b.s);
  const holes=[],placed=[];
  for(const o of ops){
    const s0=o.s-o.w/2,s1=o.s+o.w/2,y1=o.y0+o.h;
    if(o.type==='door'||o.type==='shop')continue;
    if(s0<pn.s0+.4||s1>pn.s1-.4||o.y0<pn.y0+.3||y1>H-.3)continue;
    if(o.type==='balcony'&&(s0-.35<pn.s0+.2||s1+.35>pn.s1-.2))continue;
    holes.push(o.type==='belfry'?archHole(s0,s1,o.y0,y1):o.type==='round'?circleHole(o.s,o.y0+o.w/2,o.w/2):o.type==='slit'?archHole(s0,s1,o.y0,y1,6):[[s0,o.y0],[s1,o.y0],[s1,y1],[s0,y1]]);placed.push(o);
  }
  const plH=st.plinth&&pn.y0<.05?(st.plinthH||.9):0,yl=plH||pn.y0;
  // plinth band between doors
  if(plH){
    let x=pn.s0;const cuts=[...doors.map(d=>[d.s-d.w/2,d.s+d.w/2]),[pn.s1,pn.s1]];
    for(const [a,b] of cuts){if(a-x>.05)wallPoly(st.plinthMat,F,[[x,pn.y0],[a,pn.y0],[a,plH],[x,plH]],[],0.03,uo*.5,0,1);x=b;}
    // plinth cap
  }
  const c=[[pn.s0,yl]];
  for(const d of doors){const a=d.s-d.w/2,b=d.s+d.w/2;c.push([a,yl]);
    if(d.arch){const r=d.w/2,yc=d.h-r;c.push([a,yc]);for(let i=1;i<10;i++){const t=Math.PI*(1-i/10);c.push([d.s+Math.cos(t)*r,yc+Math.sin(t)*r]);}c.push([b,yc]);}
    else{c.push([a,d.h]);c.push([b,d.h]);}
    c.push([b,yl]);}
  c.push([pn.s1,yl],[pn.s1,H],[pn.s0,H]);
  wallPoly(mat,F,c,holes,0,uo,0,1);
  // upper part of a door that is below the plinth line: nothing to do
  for(const o of placed){
    const s0=o.s-o.w/2,s1=o.s+o.w/2,y1=o.y0+o.h;
    if(o.type==='belfry'){const r=(s1-s0)/2,yc=y1-r,arc=archPts(o.s,yc,r);
      quad(mat,F.P(s0,o.y0,0),F.P(s0,o.y0,-.75),F.P(s0,yc,-.75),F.P(s0,yc,0),[0,0],[.75,0],[.75,yc-o.y0],[0,yc-o.y0],F.T);
      quad(mat,F.P(s1,o.y0,0),F.P(s1,yc,0),F.P(s1,yc,-.75),F.P(s1,o.y0,-.75),[0,0],[0,yc-o.y0],[.75,yc-o.y0],[.75,0],[-F.T[0],0,-F.T[2]]);
      quad(mat,F.P(s0,o.y0,0),F.P(s1,o.y0,0),F.P(s1,o.y0,-.75),F.P(s0,o.y0,-.75),[0,0],[1,0],[1,.75],[0,.75],[0,1,0]);
      for(let k=0;k<arc.length-1;k++)quad(mat,F.P(arc[k][0],arc[k][1],0),F.P(arc[k+1][0],arc[k+1][1],0),F.P(arc[k+1][0],arc[k+1][1],-.75),F.P(arc[k][0],arc[k][1],-.75),[k*.3,0],[(k+1)*.3,0],[(k+1)*.3,.75],[k*.3,.75],[0,-1,0]);
      belfryDecor(F,o,st,uo);continue;}
    if(o.type==='round'){roundDecor(u,F,o,st,uo,R);continue;}
    if(o.type==='slit'){quad('grdDark',F.P(s0,o.y0,-.4),F.P(s1,o.y0,-.4),F.P(s1,y1,-.4),F.P(s0,y1,-.4),[0,0],[1,0],[1,1],[0,1],F.N);continue;}
    reveal(mat,F,s0,s1,o.y0,y1,.2,uo,0,o.type!=='balcony');
    windowDecor(u,F,o,st,uo,front,R);
  }
  for(const d of doors){
    const s0=d.s-d.w/2,s1=d.s+d.w/2;
    if(d.portal){portalDecor(F,d,st,uo);continue;}
    if(d.tunnel){doorDecor(u,F,d,st,uo,R);continue;}
    if(d.gallery){reveal(mat,F,s0,s1,0,d.h,1.6,uo,0,false);galleryOpening(F,d,st,uo);continue;}
    if(d.type==='shop'){revealArch(mat,F,d,.28);shopDecor(u,F,d,st,uo,R);continue;}
    if(d.arch)revealArch(mat,F,d,.22);else reveal(mat,F,s0,s1,0,d.h,.22,uo,0,false);
    doorDecor(u,F,d,st,uo,R);
  }
  // quoins
  if(st.quoins&&front){
    for(const [s,k] of [[0,1],[F.L,-1]]){if(Math.abs((k>0?pn.s0:pn.s1)-s)>.3)continue;
      const cc=F.P(s+k*.2,0,.02);obox(st.trim,cc[0],cc[2],F.tx,F.tz,.2,.02,yl,H-.05,1,false);}
  }
  // string course between storeys, drain pipes, wall lamps and the paved apron on public facades
  if(front&&!u.noDetail){
    const Rd=rng(Math.round(pn.s0*100)+u.id);
    if(st.stringCourse&&u.lv>=2)for(let k=1;k<u.lv;k++)stringCourse(F,pn,floorY(k)-.2,ops,st);
    if(pn.y0<.05){
      if(Rd()<.5&&pn.s0<.3)drainPipe(F,pn.s0+.12,H);
      if(Rd()<.5&&pn.s1>F.L-.3)drainPipe(F,pn.s1-.12,H);
      for(const d of doors){if(Rd()<.6){wallLamp(F,d.s+(Rd()<.5?-1:1)*(d.w/2+.55),2.45,st);}}
      const apr=1.0,A=F.P(pn.s0,0,0),B=F.P(pn.s1,0,0);
      quad('grdPaving',[A[0],YG.l3,A[2]],[B[0],YG.l3,B[2]],[B[0]+F.nx*apr,YG.l3,B[2]+F.nz*apr],[A[0]+F.nx*apr,YG.l3,A[2]+F.nz*apr],[A[0]/2.4,A[2]/2.4],[B[0]/2.4,B[2]/2.4],[(B[0]+F.nx*apr)/2.4,(B[2]+F.nz*apr)/2.4],[(A[0]+F.nx*apr)/2.4,(A[2]+F.nz*apr)/2.4],[0,1,0]);
    }
  }
  // brick dentil cornice (Parador): a band, a row of corbel heads and a flat top
  if(st.eave==='dentil'){
    const hl=(pn.s1-pn.s0)/2,sm=(pn.s0+pn.s1)/2,m=F.P(sm,0,.05);
    obox('grdBrickB',m[0],m[2],F.tx,F.tz,hl,.05,H-.62,H-.38,1,true);
    const m2=F.P(sm,0,.2);obox('grdRenderTrim',m2[0],m2[2],F.tx,F.tz,hl,.2,H-.18,H,1,true);
    const nD=Math.max(1,Math.floor((pn.s1-pn.s0)/.3));
    for(let k=0;k<nD;k++){const s=pn.s0+(k+.5)*(pn.s1-pn.s0)/nD;if(k%2)continue;const d=F.P(s,0,.11);obox('grdBrickB',d[0],d[2],F.tx,F.tz,.07,.07,H-.38,H-.18,1,true);}
  }
  // eave cornice
  if(st.eave==='cornice'){
    const hl=(pn.s1-pn.s0)/2,sm=(pn.s0+pn.s1)/2;
    if(st.cornice3){for(const [y0,y1,p] of [[H-.95,H-.7,.1],[H-.7,H-.38,.2],[H-.38,H,.34]]){const m=F.P(sm,0,p/2);obox(st.trim,m[0],m[2],F.tx,F.tz,hl,p/2,y0,y1,1,true);}}
    else{const m=F.P(sm,0,.1);obox(st.trim,m[0],m[2],F.tx,F.tz,hl,.13,H-.28,H+.0,1,true);
      const m2=F.P(sm,0,.04);obox(st.trim,m2[0],m2[2],F.tx,F.tz,hl,.05,H-.45,H-.28,1,false);}
  }
}
function buildUnit(u,others,out){
  const st=u.st,R=rng(u.id*131+5),uo=R()*20,H=u.H;
  CHUNK=`c${Math.floor(u.cx/90)}_${Math.floor(u.cz/90)}`;
  const rings=[u.o,...u.h];
  for(const r of rings){
    for(let i=0;i<r.length;i++){
      const A=r[i],B=r[(i+1)%r.length],L=D2(A,B);if(L<.3)continue;
      const F=edgeFrame(A,B);const mid=[(A[0]+B[0])/2+F.nx*2,(A[1]+B[1])/2+F.nz*2];
      const pn=pathNear(mid[0],mid[1]);const front=pn.d<3.2||u.allFront;
      const kind=!front?'back':pn.calle?'street':'lane';
      const Rg=rng(u.id*977+i*13);
      const ops=u.layout?u.layout(u,F,front,Rg,st,i,r===u.o):layoutEdge(u,F,kind,Rg,st);
      for(const pan of visiblePanels(u,F,H,others))buildPanelWall(u,F,pan,ops.filter(o=>o.s-o.w/2>=pan.s0-.01&&o.s+o.w/2<=pan.s1+.01),H,st,uo,front,Rg);
    }
  }
  // roofs
  if(!u.noRoof){const rects=u.rects;const Rr=rng(u.id*17+3);const uo2=Rr()*5,vo2=Rr()*5;
    for(const rc of rects)wing(u,rc,H,st,Rr,uo2,vo2);}
  if(u.extras)u.extras(u);
}
function buildAllUnits(b){
  let units=prepUnits();for(const u of units){u.st=styleFor(u);}
  units=specialUnits(units);
  for(const u of units)if(!u.rects)u.rects=rectCover(u);
  for(const u of units){buildUnit(u,units.filter(o=>o!==u&&!(o.bb[2]<u.bb[0]-1||o.bb[0]>u.bb[2]+1||o.bb[3]<u.bb[1]-1||o.bb[1]>u.bb[3]+1)),null);}
  // navigation: the rectangles of the roof decomposition block walking
  for(const u of units){if(u.noNav)continue;for(const rc of navRects(u)){
    const w=rc.hl*2+.3,d=rc.hw*2+.3;b.nav.box(rc.cx,rc.cz,w,d,rc.bottom,u.H+3,Math.atan2(-rc.uz,rc.ux));
  }}
  buildTunnels();tunnelNav(b);
  return units;
}

// ======================================================================= façade details, street furniture
const ICO0=(()=>{const t=(1+Math.sqrt(5))/2;const v=[[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]].map(norm3);
  const f=[[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]];return {v,f};})();
function blob(mat,x,y,z,r){ // low icosahedron bud, flattened like a flower head
  const P=ICO0.v.map(([a,b,c])=>[x+a*r*1.15,y+b*r*.8,z+c*r*1.15]);
  for(const [a,b,c] of ICO0.f)tri(mat,P[a],P[b],P[c],[.5,.5],[.5,.5],[.5,.5],null);
}
function flowerBox(F,s,y,w,R,proud=.17){
  if(LOW)return;
  const c=F.P(s,0,proud);
  obox('grdBrickA',c[0],c[2],F.tx,F.tz,w/2,.1,y,y+.2,1,true);
  obox('grdHedge',c[0],c[2],F.tx,F.tz,w/2-.02,.085,y+.2,y+.33,1,true);
  const mat=R()<.6?'flower':'whiteFlower';
  for(let i=0;i<6;i++){const ss=s-w/2+.12+(w-.24)*(i+R()*.4)/6,p=F.P(ss,y+.36+R()*.06,proud+(R()-.5)*.06);blob(mat,p[0],p[1],p[2],.065);}
}
function drainPipe(F,s,y1,mat='grdZinc'){
  if(LOW)return;
  const p=F.P(s,0,.05);bar(mat,[p[0],-.1,p[2]],[p[0],y1-.2,p[2]],.07,1);
  bar(mat,[p[0],y1-.2,p[2]],[p[0]+F.nx*.17,y1+.02,p[2]+F.nz*.17],.07,1);
  for(let y=1.2;y<y1-.4;y+=1.6){const q=F.P(s,y,.02);bar('grdIron',[q[0],y,q[2]],[q[0]+F.nx*.04,y,q[2]+F.nz*.04],.1,1);}
}
function wallLamp(F,s,y,st){
  if(LOW)return;
  // wrought-iron bracket with a small four-sided lantern
  const p=F.P(s,y,0),out=.36,tip=F.P(s,y,out),rot=Math.atan2(F.tz,F.tx)+Math.PI/4;
  bar('grdIron',[p[0],y,p[2]],[tip[0],y+.04,tip[2]],.03,1);
  bar('grdIron',[p[0],y-.3,p[2]],[tip[0]-F.nx*.05,y,tip[2]-F.nz*.05],.022,1);
  bar('grdIron',[tip[0],y+.04,tip[2]],[tip[0],y+.1,tip[2]],.03,1);
  prismN('grdGlass',tip[0],tip[2],.095,y+.1,y+.36,4,rot,1,false);
  for(let i=0;i<4;i++){const a=rot+i*Math.PI/2,x1=tip[0]+Math.cos(a)*.1,z1=tip[2]+Math.sin(a)*.1;bar('grdIron',[x1,y+.1,z1],[x1,y+.36,z1],.02,1);}
  prismN('grdIron',tip[0],tip[2],.12,y+.36,y+.4,4,rot,1,true);pyrN('grdIron',tip[0],tip[2],.14,y+.4,y+.52,4,rot);
}
function stringCourse(F,pn,y,ops,st){
  // a thin projecting band, interrupted where a balcony or door crosses it
  const cuts=[];for(const o of ops){if(o.type==='balcony'||o.type==='door')cuts.push([o.s-o.w/2-.3,o.s+o.w/2+.3]);}
  cuts.sort((a,b)=>a[0]-b[0]);let x=pn.s0;
  const seg=(a,b)=>{if(b-a<.4)return;const m=F.P((a+b)/2,0,.04);obox(st.trim,m[0],m[2],F.tx,F.tz,(b-a)/2,.04,y,y+.16,1,true);};
  for(const [a,b] of cuts){if(b<pn.s0||a>pn.s1)continue;seg(x,Math.min(a,pn.s1));x=Math.max(x,b);}seg(x,pn.s1);
}
function chimney(u,wx,wz,y0,y1,st,R,ux,uz){
  const mat=R()<.5?'grdBrickA':st.wall;
  obox(mat,wx,wz,ux,uz,.3,.3,y0,y1,1,false);
  obox('grdStone',wx,wz,ux,uz,.4,.4,y1,y1+.1,1,true);
  const k=R();
  if(k<.5){for(const d of [-.14,.14])prismN('grdBrickA',wx+ux*d,wz+uz*d,.12,y1+.1,y1+.5,8,0,1);}
  else{ // tiled hood
    pyrN('grdRoof',wx,wz,.52,y1+.1,y1+.55,4,Math.atan2(uz,ux)+Math.PI/4,0,0);
    for(const sg of [-1,1])obox('grdBrickA',wx+ux*sg*.3,wz+uz*sg*.3,ux,uz,.04,.3,y1+.1,y1+.34,1,false);
  }
}
function streetLamp(x,z){
  obox('grdLamp',x,z,1,0,.2,.2,0,.5,1,true);prismN('grdLamp',x,z,.13,.5,.8,8,0,1,true);prismN('grdLamp',x,z,.065,.8,3.35,8,0,1,false);prismN('grdLamp',x,z,.1,2.6,2.7,8,0,1,true);
  prismN('grdLamp',x,z,.16,3.3,3.45,6,0,1,true);prismN('grdGlassLamp',x,z,.17,3.45,3.95,6,0,1,false);
  for(let i=0;i<6;i++){const a=i*Math.PI/3,x1=x+Math.cos(a)*.17,z1=z+Math.sin(a)*.17;bar('grdLamp',[x1,3.45,z1],[x1,3.95,z1],.03,1);}
  pyrN('grdLamp',x,z,.26,3.95,4.25,6,0);prismN('grdLamp',x,z,.04,4.25,4.4,6,0,1,true);
}
function buildFurniture(b,units){
  const R=rng(31337);CHUNK='c0_1';
  // cast-iron lamps along the streets
  for(const p of DATA.PATHS){
    const st=pathStyle(p);if(!(st.calle||(p.hw==='pedestrian'&&!st.calle)))continue;
    let acc=R()*10,side=1;
    for(let i=1;i<p.p.length;i++){
      const a=p.p[i-1],c=p.p[i],L=D2(a,c),dx=(c[0]-a[0])/L,dz=(c[1]-a[1])/L;
      for(let s=acc;s<L;s+=26){
        const off=st.w/2+.45,x=a[0]+dx*s-dz*off*side,z=a[1]+dz*s+dx*off*side;side=-side;
        if(!inT(x,z)||!freeSpot(x,z,units,.9,-.2))continue;CHUNK=`c${Math.floor(x/90)}_${Math.floor(z/90)}`;streetLamp(x,z);
      }
      acc=((acc-L)%26+26)%26;
    }
  }
  // stone cross on its column in front of the west portal of Santa María
  {CHUNK='c0_0';const x=17.6,z=90.2,ux=.98,uz=.2;
    for(let k=0;k<3;k++)obox('grdStone',x,z,ux,uz,1.2-k*.28,1.2-k*.28,k*.2,k*.2+.2,1,true);
    prismN('grdStone',x,z,.36,.6,.75,8,0,1,true);prismN('grdStone',x,z,.28,.75,3.9,8,0,1,true);prismN('grdStone',x,z,.38,3.9,4.1,8,0,1,true);
    obox('grdStone',x,z,ux,uz,.07,.06,4.1,5.0,1,true);obox('grdStone',x,z,ux,uz,.07,.4,4.5,4.65,1,true);}
}

// ======================================================================= covered passages
// The garden walk of the visit (tools/walk-routes.json) crosses the Hotel América block along z = 97 and the west range of
// the Parador along x = 200. Real footprints block those lines, so each crossing is a vaulted passage (a "cobertizo"),
// which Granada's old quarters are full of: arched mouths in the façades, plaster walls, a brick barrel vault and a
// cobbled floor, with walkable clearance under the bridging block.
const TUNNELS=[];   // the walk routes are kept open by alleys cut in gen_data.py instead of covered passages
const TUNNEL_SPRING=2.35,TUNNEL_TOP=TUNNEL_SPRING+1.5;
function tunnelOps(F){
  const ops=[];
  for(const t of TUNNELS){
    const d=[t.b[0]-t.a[0],t.b[1]-t.a[1]],L=Math.hypot(...d),dn=[d[0]/L,d[1]/L];
    for(const [P,din] of [[t.a,dn],[t.b,[-dn[0],-dn[1]]]]){
      const nd=F.nx*din[0]+F.nz*din[1];if(nd>-.85)continue;
      const dist=distSeg(P[0],P[1],F.A,F.B);if(dist>.6)continue;
      const s=(P[0]-F.A[0])*F.tx+(P[1]-F.A[1])*F.tz;if(s<t.w/2+.4||s>F.L-t.w/2-.4)continue;
      ops.push({type:'door',tunnel:true,s,w:t.w,h:TUNNEL_TOP,arch:true});
    }
  }
  return ops;
}
function buildTunnels(){
  for(const t of TUNNELS){
    CHUNK=`c${Math.floor(t.a[0]/90)}_${Math.floor(t.a[1]/90)}`;
    const d=[t.b[0]-t.a[0],t.b[1]-t.a[1]],L=Math.hypot(...d),dx=d[0]/L,dz=d[1]/L,nx=-dz,nz=dx,hw=t.w/2;
    const P=(s,o,y)=>[t.a[0]+dx*s+nx*o,y,t.a[1]+dz*s+nz*o];
    // floor and side walls
    ribbon('grdCobble',[t.a,t.b],t.w,YG.l3+.001,3);
    for(const sg of [-1,1]){
      quad('grdWhite',P(0,sg*hw,0),P(L,sg*hw,0),P(L,sg*hw,TUNNEL_SPRING),P(0,sg*hw,TUNNEL_SPRING),[0,0],[L,0],[L,TUNNEL_SPRING],[0,TUNNEL_SPRING],[-nx*sg,0,-nz*sg]);
    }
    // barrel vault in brick
    const n=12;
    for(let i=0;i<n;i++){
      const a0=Math.PI*i/n,a1=Math.PI*(i+1)/n,o0=-Math.cos(a0)*hw,o1=-Math.cos(a1)*hw,y0=TUNNEL_SPRING+Math.sin(a0)*hw,y1=TUNNEL_SPRING+Math.sin(a1)*hw;
      const nm=[-(nx*(o0+o1)/2)/hw*-1*0+nx*((-(o0+o1)/2)/hw),-(y0+y1-2*TUNNEL_SPRING)/2/hw,nz*((-(o0+o1)/2)/hw)];
      quad('grdBrickC',P(0,o0,y0),P(L,o0,y0),P(L,o1,y1),P(0,o1,y1),[0,i*.5],[L,i*.5],[L,(i+1)*.5],[0,(i+1)*.5],norm3(nm));
    }
    // a lantern at each end
    for(const [s,k] of [[.6,1],[L-.6,-1]]){const p=P(s,hw-.1,2.05);prismN('grdGlass',p[0],p[2],.1,1.9,2.2,4,Math.PI/4,1,true);}
  }
}
// nav rectangles of a unit; where a passage crosses it the footprint is re-covered with the corridor masked out
function inTunnelBand(x,z,pad=0){
  for(const t of TUNNELS){const d=[t.b[0]-t.a[0],t.b[1]-t.a[1]],L=Math.hypot(...d),tx=d[0]/L,tz=d[1]/L,s=(x-t.a[0])*tx+(z-t.a[1])*tz,o=Math.abs(-(x-t.a[0])*tz+(z-t.a[1])*tx);
    if(s>-.6&&s<L+.6&&o<t.w/2+pad)return true;}
  return false;
}
const NAV_FINE=new Map();
function navRects(u){
  const touched=TUNNELS.some(t=>{const x0=Math.min(t.a[0],t.b[0])-2,x1=Math.max(t.a[0],t.b[0])+2,z0=Math.min(t.a[1],t.b[1])-2,z1=Math.max(t.a[1],t.b[1])+2;return !(x1<u.bb[0]||x0>u.bb[2]||z1<u.bb[1]||z0>u.bb[3]);});
  if(!touched&&NAV_FINE.has(u))return NAV_FINE.get(u);
  const out=rectCover(u,.25,.5,touched?(x,z)=>inTunnelBand(x,z,.02):null,40,.3).map(r=>({...r,bottom:-60}));NAV_FINE.set(u,out);return out;
}
function tunnelNav(b){
  for(const t of TUNNELS){const d=[t.b[0]-t.a[0],t.b[1]-t.a[1]],L=Math.hypot(...d),tx=d[0]/L,tz=d[1]/L;
    b.nav.box((t.a[0]+t.b[0])/2,(t.a[1]+t.b[1])/2,L,t.w+.04,TUNNEL_TOP-.3,TUNNEL_TOP+8,Math.atan2(-tz,tx));}
}

// ======================================================================= special geometry helpers
// regular n-gon prism (side faces) around (cx,cz), radius r (circumradius), rotated by rot
function prismN(mat,cx,cz,r,y0,y1,n,rot=0,uvs=1,cap=true){
  const P=i=>[cx+Math.cos(rot+i*2*Math.PI/n)*r,cz+Math.sin(rot+i*2*Math.PI/n)*r];
  for(let i=0;i<n;i++){const a=P(i),c=P(i+1),mx=(a[0]+c[0])/2-cx,mz=(a[1]+c[1])/2-cz,l=Math.hypot(mx,mz),len=Math.hypot(c[0]-a[0],c[1]-a[1]);
    quad(mat,[a[0],y0,a[1]],[c[0],y0,c[1]],[c[0],y1,c[1]],[a[0],y1,a[1]],[i*len*uvs,y0*uvs],[(i+1)*len*uvs,y0*uvs],[(i+1)*len*uvs,y1*uvs],[i*len*uvs,y1*uvs],[mx/l,0,mz/l]);}
  if(cap){const pts=[];for(let i=0;i<n;i++)pts.push(P(i));polyH(mat,pts,[],y1,1,true);}
}
// pyramid on an n-gon: roof facets with planar tile UVs (slope derived from the geometry)
function pyrN(mat,cx,cz,r,y0,y1,n,rot=0,uo=0,vo=0,ridge=false){
  const P=i=>[cx+Math.cos(rot+i*2*Math.PI/n)*r,cz+Math.sin(rot+i*2*Math.PI/n)*r];
  const ap=Math.cos(Math.PI/n)*r,slope=(y1-y0)/ap;
  for(let i=0;i<n;i++){const a=P(i),c=P(i+1),am=rot+(i+.5)*2*Math.PI/n;
    roofFacet(mat,[[a[0],y0,a[1]],[c[0],y0,c[1]],[cx,y1,cz]],Math.cos(am),Math.sin(am),slope,uo,vo);
    if(ridge)bar('grdStone',[a[0],y0,a[1]],[cx,y1,cz],.12,1);}
}
function cap4(mat,cx,cz,hw,y0,y1,rot=0){pyrN(mat,cx,cz,hw*Math.SQRT2,y0,y1,4,rot+Math.PI/4);}
function pinnacle(cx,cz,y0,rot,mat='grdStone'){
  const ux=Math.cos(rot),uz=Math.sin(rot);
  obox(mat,cx,cz,ux,uz,.46,.46,y0,y0+1.3,1,true);
  obox(mat,cx,cz,ux,uz,.56,.56,y0+1.3,y0+1.5,1,true);
  pyrN(mat,cx,cz,.55*Math.SQRT2,y0+1.5,y0+3.4,4,rot+Math.PI/4,0,0);
  bar('grdIron',[cx,y0+3.3,cz],[cx,y0+4.1,cz],.05,1);bar('grdIron',[cx-.18,y0+3.85,cz],[cx+.18,y0+3.85,cz],.04,1);
}
// ======================================================================= portals and belfry openings
function archPts(cx,yc,r,n=12){const p=[];for(let i=0;i<=n;i++){const a=Math.PI*(1-i/n);p.push([cx+Math.cos(a)*r,yc+Math.sin(a)*r]);}return p;}  // left -> right
function portalDecor(F,o,st,uo){
  const dn=.42,s0=o.s-o.w/2,s1=o.s+o.w/2,r=o.w/2,yc=o.h-r,dr=o.dw/2,dyc=o.dh-dr;
  // niche back wall with the door opening
  const arc=archPts(o.s,yc,r),darc=archPts(o.s,dyc,dr);
  const c=[[s0,0],[o.s-dr,0],[o.s-dr,dyc],...darc.slice(1,-1).map(p=>p),[o.s+dr,dyc],[o.s+dr,0],[s1,0],[s1,yc],...arc.slice(1,-1).reverse().map(p=>p),[s0,yc]];
  wallPoly('grdCream',F,c,[],-dn,uo,0,1);
  // jambs and arch soffit of the niche
  quad('grdCream',F.P(s0,0,0),F.P(s0,0,-dn),F.P(s0,yc,-dn),F.P(s0,yc,0),[0,0],[dn,0],[dn,yc],[0,yc],F.T);
  quad('grdCream',F.P(s1,0,0),F.P(s1,yc,0),F.P(s1,yc,-dn),F.P(s1,0,-dn),[0,0],[0,yc],[dn,yc],[dn,0],[-F.T[0],0,-F.T[2]]);
  for(let i=0;i<arc.length-1;i++){const a=arc[i],b=arc[i+1];
    quad('grdCream',F.P(a[0],a[1],0),F.P(b[0],b[1],0),F.P(b[0],b[1],-dn),F.P(a[0],a[1],-dn),[i*.5,0],[(i+1)*.5,0],[(i+1)*.5,dn],[i*.5,dn],[0,-1,0]);}
  // brick archivolt around the niche (flat band proud of the wall)
  const outer=archPts(o.s,yc,r+.38);
  for(let i=0;i<arc.length-1;i++){
    quad('grdBrickC',F.P(arc[i][0],arc[i][1],.025),F.P(arc[i+1][0],arc[i+1][1],.025),F.P(outer[i+1][0],outer[i+1][1],.025),F.P(outer[i][0],outer[i][1],.025),[i*.4,0],[(i+1)*.4,0],[(i+1)*.4,.38],[i*.4,.38],F.N);}
  for(const sg of [-1,1]){quad('grdBrickC',F.P(o.s+sg*r,0,.025),F.P(o.s+sg*(r+.38),0,.025),F.P(o.s+sg*(r+.38),yc,.025),F.P(o.s+sg*r,yc,.025),[0,0],[.38,0],[.38,yc],[0,yc],F.N);}
  // door leaf, fanlight and stone frame
  const dd=-dn-.06;
  quad('grdWoodDoor',F.P(o.s-dr,0,dd),F.P(o.s+dr,0,dd),F.P(o.s+dr,dyc,dd),F.P(o.s-dr,dyc,dd),[0,0],[o.dw,0],[o.dw,dyc],[0,dyc],F.N);
  for(let i=0;i<darc.length-1;i++){const a=darc[i],b=darc[i+1];tri('grdWoodDoor',F.P(o.s,dyc,dd),F.P(a[0],a[1],dd),F.P(b[0],b[1],dd),[.5,0],[0,1],[1,1],F.N);}
  const frame=darc.map(p=>[o.s+(p[0]-o.s)*(1+.17/dr),dyc+(p[1]-dyc)*(1+.17/dr)]);
  for(let i=0;i<darc.length-1;i++)quad('grdStone',F.P(darc[i][0],darc[i][1],-dn+.02),F.P(darc[i+1][0],darc[i+1][1],-dn+.02),F.P(frame[i+1][0],frame[i+1][1],-dn+.02),F.P(frame[i][0],frame[i][1],-dn+.02),[i*.3,0],[(i+1)*.3,0],[(i+1)*.3,.2],[i*.3,.2],F.N);
  for(const sg of [-1,1])quad('grdStone',F.P(o.s+sg*dr,0,-dn+.02),F.P(o.s+sg*(dr+.17),0,-dn+.02),F.P(o.s+sg*(dr+.17),dyc,-dn+.02),F.P(o.s+sg*dr,dyc,-dn+.02),[0,0],[.2,0],[.2,dyc],[0,dyc],F.N);
  // step
  const sc=F.P(o.s,0,.5);obox('grdStone',sc[0],sc[2],F.tx,F.tz,o.w/2+.3,.5,-.1,.15,1,true);
}
function belfryDecor(F,o,st,uo){
  const s0=o.s-o.w/2,s1=o.s+o.w/2,r=o.w/2,yc=o.y0+o.h-r;
  const arc=archPts(o.s,yc,r),outer=archPts(o.s,yc,r+.22);
  // dark interior and a stone arch band
  const gd=.75;
  quad('grdDark',F.P(s0,o.y0,-gd),F.P(s1,o.y0,-gd),F.P(s1,yc,-gd),F.P(s0,yc,-gd),[0,0],[1,0],[1,1],[0,1],F.N);
  for(let i=0;i<arc.length-1;i++)tri('grdDark',F.P(o.s,yc,-gd),F.P(arc[i][0],arc[i][1],-gd),F.P(arc[i+1][0],arc[i+1][1],-gd),[0,0],[1,0],[1,1],F.N);
  for(let i=0;i<arc.length-1;i++)quad('grdStone',F.P(arc[i][0],arc[i][1],.03),F.P(arc[i+1][0],arc[i+1][1],.03),F.P(outer[i+1][0],outer[i+1][1],.03),F.P(outer[i][0],outer[i][1],.03),[i*.3,0],[(i+1)*.3,0],[(i+1)*.3,.22],[i*.3,.22],F.N);
  for(const sg of [-1,1])quad('grdStone',F.P(o.s+sg*r,o.y0,.03),F.P(o.s+sg*(r+.22),o.y0,.03),F.P(o.s+sg*(r+.22),yc,.03),F.P(o.s+sg*r,yc,.03),[0,0],[.22,0],[.22,yc-o.y0],[0,yc-o.y0],F.N);
  // bell
  const bc=F.P(o.s,0,-gd+.35);prismN('grdIron',bc[0],bc[2],.34,yc-1.15,yc-.2,8,0,1);
  const sill=F.P(o.s,0,.1);obox('grdStone',sill[0],sill[2],F.tx,F.tz,o.w/2+.2,.14,o.y0-.08,o.y0+.04,1,true);
}

// ======================================================================= church of Santa María, Baño de la Mezquita, convent tower
function churchStyle(){return {slope:.5,maxRise:5.5,overhang:.62,rafters:false,gable:0,bay:4.4,plinth:false,quoins:false,surround:true,balcony:0,shutter:null,roof:'grdRoofOld',wall:'grdChurch',wallB:'grdChurch',trim:'grdStone',plinthMat:'grdStone',eave:'cornice',cornice3:true,front:true};}
function dirOf(F){return [F.N[0],F.N[2]];}
function churchLayout(kind){
  return (u,F,front,R,st)=>{
    const ops=[],L=F.L;if(L<2.2)return ops;
    const [nx,nz]=dirOf(F);
    if(kind==='low'){
      // portals: west facade and the long south wall
      const west=nx<-.85&&L>8,south=nz>.9&&L>10;
      if(west)ops.push({type:'door',portal:true,s:L*.5,w:3.4,h:5.9,arch:true,dw:1.9,dh:3.25});
      if(south)ops.push({type:'door',portal:true,s:L*.34,w:2.9,h:5.0,arch:true,dw:1.6,dh:2.9});
      const nb=Math.max(1,Math.round((L-2)/4.2));
      for(let i=0;i<nb;i++){const c=1+(L-2)*(i+.5)/nb;
        if((west||south)&&Math.abs(c-(west?L*.5:L*.34))<(west?2.6:2.4))continue;
        ops.push({type:R()<.5?'reja':'win',s:c,w:.62,y0:3.35,h:1.0});}
    }else if(kind==='tall'){
      const nb=Math.max(1,Math.round((L-2)/4.6));
      for(let i=0;i<nb;i++){const c=1.2+(L-2.4)*(i+.5)/nb;
        ops.push({type:'win',s:c,w:.78,y0:u.H-5.6,h:1.45});
        if(R()<.7)ops.push({type:'win',s:c+(R()<.5?-1:1)*1.3,w:.5,y0:u.H-9.0,h:.8});}
    }else if(kind==='tower'){
      const c=L/2;
      ops.push({type:'reja',s:c,w:.42,y0:5.6,h:1.35});ops.push({type:'reja',s:c,w:.42,y0:11.0,h:1.25});
      ops.push({type:'reja',s:c,w:.5,y0:13.6,h:.9});
      for(const dx of [-.95,.95])ops.push({type:'belfry',s:c+dx,w:1.15,y0:u.H-4.7,h:3.3});
    }
    return ops;
  };
}
function churchUnits(u0){
  const st=churchStyle(),th=dominantAngle(u0.o),ux=Math.cos(th),uz=Math.sin(th);
  const low=mkUnit({id:u0.id*10+1,o:u0.o,h:u0.h,H:8.4,st:{...st,slope:.46},layout:churchLayout('low')});
  const rects=rectCover(low);
  const nave=rects[0];
  const tall=mkUnit({id:u0.id*10+2,o:rectPoly(nave.cx,nave.cz,nave.ux,nave.uz,nave.hl,nave.hw),H:15.8,st:{...st,slope:.52,maxRise:5.6,overhang:.75},layout:churchLayout('tall'),under:low,theta:Math.atan2(nave.uz,nave.ux),
    extras:(t)=>{for(const [sa,sb] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const rc=t.rects[0],vx=-rc.uz,vz=rc.ux;pinnacle(rc.cx+rc.ux*sa*(rc.hl+.35)+vx*sb*(rc.hw+.35),rc.cz+rc.uz*sa*(rc.hl+.35)+vz*sb*(rc.hw+.35),t.H-.9,Math.atan2(rc.uz,rc.ux));}}});
  // bell tower on the north-east jut of the plan
  const tc=[47.4,85.6],tw=3.4;
  const tower=mkUnit({id:u0.id*10+3,o:rectPoly(tc[0],tc[1],ux,uz,tw,tw),H:22.2,st:{...st,wall:'grdBrickC',wallB:'grdBrickC',slope:.6},layout:churchLayout('tower'),under:low,noRoof:true,theta:th,
    extras:(t)=>towerTop(t,tc,ux,uz,tw)});
  return [low,tall,tower];
}
function towerTop(t,tc,ux,uz,tw){
  const H=t.H,vx=-uz,vz=ux,rot=Math.atan2(uz,ux);
  // string courses and the belfry cornice, wrapped round the shaft
  const band=(y,h,p)=>{for(const [dx,dz,hl,hw] of [[0,tw,tw+p,p/2],[0,-tw,tw+p,p/2],[tw,0,p/2,tw+p],[-tw,0,p/2,tw+p]]){}
    const c=(a,b)=>[tc[0]+ux*a+vx*b,tc[1]+uz*a+vz*b];
    for(const [a,b,al,bw,dir] of [[tw+p/2,0,p/2,tw+p,0],[-(tw+p/2),0,p/2,tw+p,0],[0,tw+p/2,tw+p,p/2,1],[0,-(tw+p/2),tw+p,p/2,1]]){
      const cc=c(a,b);obox('grdStone',cc[0],cc[1],dir?ux:vx,dir?uz:vz,dir?al:bw,dir?bw:al,y,y+h,1,true);}};
  band(9.2,.28,.1);band(14.2,.28,.1);band(17.0,.3,.14);
  band(H-.9,.3,.16);band(H-.55,.3,.3);band(H-.25,.25,.46);
  // octagonal drum with round windows, cornice, slate spire and cross
  const r=tw*.86,y0=H,y1=H+2.6;
  prismN('grdBrickC',tc[0],tc[1],r,y0,y1,8,rot+Math.PI/8,1);
  prismN('grdStone',tc[0],tc[1],r+.28,y1,y1+.3,8,rot+Math.PI/8,1);
  for(let i=0;i<8;i+=2){const a=rot+Math.PI/8+(i+.5)*Math.PI/4,cx=tc[0]+Math.cos(a)*(r*Math.cos(Math.PI/8)+.01),cz=tc[1]+Math.sin(a)*(r*Math.cos(Math.PI/8)+.01);
    const nx=Math.cos(a),nz=Math.sin(a),tx=-nz,tz=nx,n=10;
    for(let k=0;k<n;k++){const a0=2*Math.PI*k/n,a1=2*Math.PI*(k+1)/n;tri('grdDark',[cx,y0+1.3,cz],[cx+tx*Math.cos(a0)*.34,y0+1.3+Math.sin(a0)*.34,cz+tz*Math.cos(a0)*.34],[cx+tx*Math.cos(a1)*.34,y0+1.3+Math.sin(a1)*.34,cz+tz*Math.cos(a1)*.34],[0,0],[1,0],[1,1],[nx,0,nz]);}}
  pyrN('grdSlate',tc[0],tc[1],(r+.55)/Math.cos(Math.PI/8)*.97,y1+.3,y1+6.4,8,rot+Math.PI/8,0,0,true);
  bar('grdIron',[tc[0],y1+6.2,tc[1]],[tc[0],y1+8.2,tc[1]],.07,1);bar('grdIron',[tc[0]-.35,y1+7.5,tc[1]],[tc[0]+.35,y1+7.5,tc[1]],.06,1);
  for(const [sa,sb] of [[-1,-1],[1,-1],[1,1],[-1,1]])pinnacle(tc[0]+ux*sa*(tw+.1)+vx*sb*(tw+.1),tc[1]+uz*sa*(tw+.1)+vz*sb*(tw+.1),H-.1,rot);
}
function bathUnits(u0){
  // Baño de la Mezquita: brick base storey with a plastered upper hall, tile roofs on exposed beams and a roof lantern
  const th=dominantAngle(u0.o);
  const st={slope:.4,maxRise:3,overhang:.7,rafters:true,gable:0,bay:3.4,plinth:false,quoins:false,surround:true,balcony:0,shutter:'grdShutterB',roof:'grdRoofOld',wall:'grdBrickA',wallB:'grdBrickA',trim:'grdCream',plinthMat:'grdStone',eave:'beams',front:true};
  const low=mkUnit({id:u0.id*10+1,o:u0.o,h:u0.h,H:3.9,st});
  const rects=rectCover(low),big=rects[0];
  const up=mkUnit({id:u0.id*10+2,o:rectPoly(big.cx,big.cz,big.ux,big.uz,big.hl-.8,big.hw-.8),H:7.2,st:{...st,wall:'grdOchre',wallB:'grdOchreB',overhang:.8,eave:'beams',rafters:true,plinth:false,surround:false},under:low,theta:Math.atan2(big.uz,big.ux),layout:(uu,F,front,R)=>{const L=F.L,ops=[];if(L<4)return ops;const n=Math.max(1,Math.floor((L-1.6)/2.8));for(let i=0;i<n;i++){const s=.8+(L-1.6)*(i+.5)/n;ops.push({type:'win',s,w:.85,y0:5.0,h:1.25,shut:false});if(i%2===0)ops.push({type:'round',s,w:.6,y0:6.4,h:.6});}return ops;},
    extras:(t)=>{const rc=t.rects[0],vx=-rc.uz,vz=rc.ux,H=t.H;
      // lantern (mirador) on the ridge: a timber-slatted box with its own small hipped roof
      const lw=1.5,lc=[rc.cx,rc.cz],yb=H+2.0;
      obox('grdOchre',lc[0],lc[1],rc.ux,rc.uz,lw,lw,yb,yb+1.9,1,false);
      for(let k=-2;k<=2;k++){obox('grdBeam',lc[0]+rc.ux*lw*.42*k*.8,lc[1]+rc.uz*lw*.42*k*.8,rc.ux,rc.uz,.07,lw+.03,yb+.5,yb+1.6,1,false);obox('grdBeam',lc[0]+vx*lw*.42*k*.8,lc[1]+vz*lw*.42*k*.8,vx,vz,.07,lw+.03,yb+.5,yb+1.6,1,false);}
      obox('grdDark',lc[0],lc[1],rc.ux,rc.uz,lw-.05,lw-.05,yb+.55,yb+1.55,1,false);
      const lr={cx:lc[0],cz:lc[1],ux:rc.ux,uz:rc.uz,hl:lw,hw:lw};
      wing({o:t.o,h:t.h,st:t.st},lr,yb+1.9,{...t.st,overhang:.6,slope:.45,rafters:true,maxRise:2},rng(7),0,0);
    }});
  return [low,up];
}
function towerUnit(u){
  // convent bell tower of the Parador: tan brick shaft with flat pilasters, a pointed slit light, a belfry with one arched
  // opening per face under a stepped cornice, and a low hipped tile roof with an iron cross
  const st={...u.st,wall:'grdRender',wallB:'grdRender',trim:'grdRenderTrim',plinth:true,plinthMat:'grdStone',slope:.5,maxRise:2.6,overhang:.7,rafters:false,gable:0,eave:'dentil',balcony:0,shutter:null,surround:false,chimney:0};
  return mkUnit({id:u.id,o:u.o,h:u.h,H:17.4,st,theta:u.theta,noDetail:true,allFront:true,layout:(uu,F,front,R)=>{
    const L=F.L,ops=[];if(L<2)return ops;
    ops.push({type:'reja',s:L/2,w:.5,y0:4.4,h:1.3});
    ops.push({type:'slit',s:L/2,w:.55,y0:9.0,h:1.7});
    ops.push({type:'belfry',s:L/2,w:1.35,y0:uu.H-4.6,h:3.2});
    return ops;},
    extras:(t)=>{const rc=t.rects[0],vx=-rc.uz,vz=rc.ux,H=t.H;
      const P=(a,b)=>[rc.cx+rc.ux*a+vx*b,rc.cz+rc.uz*a+vz*b];
      // pilasters up each corner and a belt course at the foot of the belfry
      for(const [sa,sb] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const p=P(sa*(rc.hl-.2),sb*(rc.hw-.2));obox('grdBrickB',p[0],p[1],rc.ux,rc.uz,.2,.2,.0,H-4.9,1,true);}
      for(const [a,b,al,bw,d] of [[rc.hl+.06,0,.06,rc.hw+.1,0],[-(rc.hl+.06),0,.06,rc.hw+.1,0],[0,rc.hw+.06,rc.hl+.1,.06,1],[0,-(rc.hw+.06),rc.hl+.1,.06,1]]){
        const c=P(a,b);for(const y of [H-4.95,H-.32]){obox('grdStone',c[0],c[1],d?rc.ux:vx,d?rc.uz:vz,d?al:bw,d?bw:al,y,y+.26,1,true);}}
      // iron cross on the apex
      const apex=P(0,0);const rise=Math.min(.5*(Math.min(rc.hl,rc.hw)+.7),2.6);bar('grdIron',[apex[0],H+rise-.1,apex[1]],[apex[0],H+rise+1.2,apex[1]],.06,1);bar('grdIron',[apex[0]-vx*.3,H+rise+.8,apex[1]-vz*.3],[apex[0]+vx*.3,H+rise+.8,apex[1]+vz*.3],.05,1);
    }});
}
function miradorUnit(u){
  // the mirador turret over the garden range: plastered box with paired brown windows on every face, hipped roof
  const st={...u.st,slope:.34,maxRise:1.6,overhang:.75,rafters:true,eave:'beams',gable:0,balcony:0,chimney:.8};
  return mkUnit({id:u.id,o:u.o,h:u.h,H:12.4,st,theta:u.theta,noDetail:true,allFront:true,under:null,layout:(uu,F,front,R)=>{
    const L=F.L,ops=[];if(L<2)return ops;
    for(const dx of [-.8,.8]){ops.push({type:'win',s:L/2+dx,w:.9,y0:uu.H-3.2,h:1.5,shut:false});}
    ops.push({type:'reja',s:L/2,w:.8,y0:2.0,h:1.2});ops.push({type:'win',s:L/2,w:.9,y0:6.6,h:1.4,shut:false});
    return ops;}});
}
function specialUnits(units){
  const out=[];
  for(const u of units){
    if(u.id===17369758)out.push(...churchUnits(u));
    else if(u.id===96485675)out.push(...bathUnits(u));
    else if(u.id===76959770)out.push(towerUnit(u));
    else if(u.id===76959771)out.push(miradorUnit(u));
    else if(u.id===20204470){u.layout=cloisterLayout;out.push(u);}
    else out.push(u);
  }
  return out;
}

// ======================================================================= planting, hedges, garden furniture
const TREE_H={[CYPRESS]:[9,15],[ELM]:[11,17],[PLANE]:[12,18],[POPLAR]:[14,20],[HOLM]:[5,8],[OLIVE]:[3.5,5.5],[PINE]:[9,13],[STONEPINE]:[10,14],[ORANGE]:[3,4.2],[PALM]:[8,13],[SHRUB]:[1.4,2.4]};
function plantT(R,x,z,sp){const [a,b]=TREE_H[sp];plant(x,0,z,sp,a+(b-a)*R());TREES_PLANTED++;}
let TREES_PLANTED=0;
function pickSp(R,table){let t=0;for(const [,w] of table)t+=w;let v=R()*t;for(const [s,w] of table){v-=w;if(v<=0)return s;}return table[0][0];}
function freeSpot(x,z,units,pad=2.4,pathPad=1.2){
  if(pathNear(x,z).d<pathPad)return false;
  if(pathPad>0&&nearWalk(x,z,pathPad+1.6))return false;
  if(x>205&&x<345&&Math.abs(z-252)<7)return false;       // inside the cypress walk
  for(const u of units){if(x<u.bb[0]-pad||x>u.bb[2]+pad||z<u.bb[1]-pad||z>u.bb[3]+pad)continue;if(inPoly(x,z,u.o,u.h)||distPoly(x,z,u.o)<pad)return false;}
  return true;
}
function inT(x,z){for(const t of DATA.T)if(inPoly(x,z,t.o,t.h))return true;return false;}
function scatterIn(R,poly,spacing,table,units,{margin=1.4,keep=1}={}){
  const [x0,z0,x1,z1]=bbox(poly.o);
  for(let z=z0+spacing*R();z<z1;z+=spacing)for(let x=x0+spacing*R();x<x1;x+=spacing){
    const px=x+(R()-.5)*spacing*.7,pz=z+(R()-.5)*spacing*.7;
    if(R()>keep)continue;
    if(!inPoly(px,pz,poly.o,poly.h)||distPoly(px,pz,poly.o)<margin)continue;
    if(!freeSpot(px,pz,units))continue;
    plantT(R,px,pz,pickSp(R,table));
  }
}
let ctx_per=null;
function buildPlanting(b,units){
  const R=rng(4242);
  // mapped trees
  for(const [x,z,sp] of DATA.TREES){if(!freeSpot(x,z,units,1.8,.6))continue;plantT(R,x,z,pickSp(R,[[PLANE,.4],[ELM,.25],[POPLAR,.1],[HOLM,.1],[ORANGE,.15]]));}
  // gardens, lawns and kitchen gardens
  for(const g of DATA.BEDS){
    const area=Math.abs(ringArea(g.o));
    if(g.k==='garden'){
      if(area<260)continue;
      const big=area>3000;
      scatterIn(R,g,big?9:7,[[ELM,.14],[PLANE,.14],[ORANGE,.28],[OLIVE,.14],[CYPRESS,.2],[PALM,.04],[HOLM,.06]],units,{keep:big?.55:.7});
    }else if(g.k==='kitchen'){
      scatterIn(R,g,11,[[OLIVE,.35],[ORANGE,.35],[HOLM,.1],[SHRUB,.2]],units,{keep:.35,margin:1.8});
    }else if(g.k==='bed'&&area>150){
      // clipped cypress at the corners of the larger parterres
      for(let i=0;i<g.o.length;i++){if(R()<.18){const [x,z]=g.o[i];const c=centroid(g.o);const px=x+(c[0]-x)*.05,pz=z+(c[1]-z)*.05;if(freeSpot(px,pz,units,2,.5))plantT(R,px,pz,CYPRESS);}}
    }
  }
  // avenues along the wide walks
  for(const p of DATA.PATHS){
    const st=pathStyle(p);if(!(/Paseo/.test(p.n||'')&&p.hw==='footway')&&!(p.hw==='pedestrian'&&!st.calle))continue;
    let acc=R()*6;
    for(let i=1;i<p.p.length;i++){
      const a=p.p[i-1],c=p.p[i],L=D2(a,c),dx=(c[0]-a[0])/L,dz=(c[1]-a[1])/L;
      for(let s=acc;s<L;s+=10){
        const side=((Math.floor(s/10)+i)%2)?1:-1,off=st.w/2+2.2;
        const x=a[0]+dx*s-dz*off*side,z=a[1]+dz*s+dx*off*side;
        if(inT(x,z)&&freeSpot(x,z,units,2,1.0)&&R()<.8)plantT(R,x,z,pickSp(R,[[ELM,.4],[PLANE,.3],[POPLAR,.15],[CYPRESS,.15]]));
      }
      acc=((acc-L)%10+10)%10;
    }
  }
  // the inner foot of the walls: scattered shrubs, olives and a few stone pines
  {const per=ctx_per;for(let i=0;i<per.length;i++){const a=per[i],c=per[(i+1)%per.length],L=D2(a,c);if(L<2)continue;const dx=(c[0]-a[0])/L,dz=(c[1]-a[1])/L;
    for(let s=R()*7;s<L;s+=7+R()*9){const off=4.2+R()*5,x=a[0]+dx*s+dz*off,z=a[1]+dz*s-dx*off;
      if(!inT(x,z)||!freeSpot(x,z,units,3,1.8))continue;let inBed=false;for(const g of DATA.BEDS)if(g.k!=='parking'&&inPoly(x,z,g.o,g.h)){inBed=true;break;}if(inBed)continue;
      plantT(R,x,z,pickSp(R,[[SHRUB,.45],[OLIVE,.2],[HOLM,.15],[STONEPINE,.1],[CYPRESS,.1]]));}}}
  // church precinct: cypresses at the portal, poplars and palms
  for(const [x,z,sp] of [[19.2,101,CYPRESS],[18.4,97.6,CYPRESS],[63.2,98.5,POPLAR],[64.5,92,POPLAR],[56.5,109.5,PALM],[54,111,PALM],[26.5,108.5,CYPRESS],[20.8,89.5,CYPRESS]])if(freeSpot(x,z,units,1.5,.6))plantT(R,x,z,sp);
  // open ground: olives, holm oaks and shrubs (the Secano and the wall gardens)
  for(let i=0;i<(LOW?500:1500);i++){
    const t=DATA.T[0],[x0,z0,x1,z1]=bbox(t.o),x=x0+R()*(x1-x0),z=z0+R()*(z1-z0);
    if(!inT(x,z)||!freeSpot(x,z,units,4.4,2.0))continue;
    let inBed=false;for(const g of DATA.BEDS)if(g.k!=='parking'&&inPoly(x,z,g.o,g.h)){inBed=true;break;}
    if(inBed)continue;
    if(vn(x/26,z/26)<.46)continue;
    plantT(R,x,z,pickSp(R,[[OLIVE,.28],[HOLM,.22],[SHRUB,.3],[STONEPINE,.06],[CYPRESS,.06],[PLANE,.04],[ELM,.04]]));
  }
}
// clipped hedges round the parterres and kitchen gardens; they are opened where the garden walk crosses them
function nearWalk(x,z,r){for(let i=1;i<GARDEN_WALK.length;i++)if(distSeg(x,z,GARDEN_WALK[i-1],GARDEN_WALK[i])<r)return true;return false;}
function buildHedges(b){
  for(const g of DATA.BEDS){
    if(g.k!=='bed'&&g.k!=='kitchen')continue;
    const c=centroid(g.o);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    const R=rng(g.id%100000+3),w=g.k==='kitchen'?.5:.55,h=(g.k==='kitchen'?.7:.9)+R()*.15;
    const o=g.o,n=o.length,keep=[];
    for(let i=0;i<n;i++){const a=o[i],q=o[(i+1)%n];keep.push(!nearWalk(a[0],a[1],2.6)&&!nearWalk(q[0],q[1],2.6)&&!nearWalk((a[0]+q[0])/2,(a[1]+q[1])/2,2.6));}
    if(keep.every(v=>v)){hedgeRun(o,w,h,'grdHedge',-.02,true);}
    else{
      // split into open runs of consecutive kept edges
      let start=keep.findIndex(v=>!v);let run=null;
      for(let k=1;k<=n;k++){const i=(start+k)%n,ke=keep[i];
        if(ke){if(!run)run=[o[i]];run.push(o[(i+1)%n]);}
        else if(run){if(run.length>=2)hedgeRun(run,w,h,'grdHedge',-.02,false);run=null;}}
      if(run&&run.length>=2)hedgeRun(run,w,h,'grdHedge',-.02,false);
    }
    for(let i=0;i<n;i++){if(!keep[i])continue;const a=o[i],q=o[(i+1)%n],L=D2(a,q);if(L<.2)continue;const ex=(q[0]-a[0])/L,ez=(q[1]-a[1])/L;b.nav.box((a[0]+q[0])/2,(a[1]+q[1])/2,L+w,w+.1,0,1.1,Math.atan2(-ez,ex));}
  }
}

// ======================================================================= excavated houses and palace foundations
function ruinWall(R,a,b,t,hmax,mat='grdRuin'){
  const L=D2(a,b);if(L<.4)return;
  if(b_nav)b_nav.box((a[0]+b[0])/2,(a[1]+b[1])/2,L+t,t,0,Math.max(.7,hmax*.9),Math.atan2(-(b[1]-a[1]),b[0]-a[0]));const dx=(b[0]-a[0])/L,dz=(b[1]-a[1])/L,n=Math.max(1,Math.round(L/.7)),ph=R()*50;
  // coursed rubble wall whose top wanders: smooth noise for the height, short pieces so the line steps like broken masonry
  let prev=null;
  for(let i=0;i<n;i++){
    const t0=i/n,t1=(i+1)/n,cx=lerp(a[0],b[0],(t0+t1)/2),cz=lerp(a[1],b[1],(t0+t1)/2);
    const h=Math.max(.22,hmax*(.4+.9*vn(ph+i*.38,ph*.3)+(R()-.5)*.12)),hl=(L/n)/2+.02;
    obox(mat,cx,cz,dx,dz,hl,t/2,-.1,h,1,true,false,R()*9);
    if(prev!==null&&h>.35&&R()<.18)obox('grdBrickB',cx,cz,dx,dz,hl*.8,t/2+.012,h-.14,h-.02,1,false,false,R()*5);
    prev=h;
  }
}
function ruinHouse(R,cx,cz,ux,uz,w,d,hmax,openings=true){
  const vx=-uz,vz=ux,P=(a,b)=>[cx+ux*a+vx*b,cz+uz*a+vz*b],hw=w/2,hd=d/2,t=.55;
  // outer walls with doorways
  const sides=[[P(-hw,-hd),P(hw,-hd)],[P(hw,-hd),P(hw,hd)],[P(hw,hd),P(-hw,hd)],[P(-hw,hd),P(-hw,-hd)]];
  const door=Math.floor(R()*4);
  sides.forEach(([a,b],i)=>{
    if(i===door&&openings){const m=[(a[0]+b[0])/2,(a[1]+b[1])/2],l=D2(a,b),dx=(b[0]-a[0])/l,dz=(b[1]-a[1])/l;
      ruinWall(R,a,[m[0]-dx*.8,m[1]-dz*.8],t,hmax);ruinWall(R,[m[0]+dx*.8,m[1]+dz*.8],b,t,hmax);}
    else ruinWall(R,a,b,t,hmax);
  });
  // a central patio, with a basin, and rooms on two sides
  const pw=w*.34,pd=d*.34;
  for(const [a,b] of [[P(-pw,-pd),P(pw,-pd)],[P(pw,-pd),P(pw,pd)],[P(pw,pd),P(-pw,pd)],[P(-pw,pd),P(-pw,-pd)]])if(R()<.8)ruinWall(R,a,b,t*.8,hmax*.6,'grdBrickB');
  ruinWall(R,P(-hw,-pd),P(-pw,-pd),t*.8,hmax*.8);ruinWall(R,P(pw,pd),P(hw,pd),t*.8,hmax*.8);
  ruinWall(R,P(0,-hd),P(0,-pd),t*.8,hmax*.8);
  // paved patio floor and a small basin
  const f=[P(-pw+.3,-pd+.3),P(pw-.3,-pd+.3),P(pw-.3,pd-.3),P(-pw+.3,pd-.3)];
  polyH('grdPaving',f,[],.0,2.4);
  const bw=Math.min(1.4,pw*.45),bd=Math.min(1.0,pd*.45),bs=[P(-bw,-bd),P(bw,-bd),P(bw,bd),P(-bw,bd)];
  polyH('grdWater',bs,[],-.05,1,true);
  for(const [a,b] of [[bs[0],bs[1]],[bs[1],bs[2]],[bs[2],bs[3]],[bs[3],bs[0]]]){const l=D2(a,b),dx=(b[0]-a[0])/l,dz=(b[1]-a[1])/l;obox('grdStone',(a[0]+b[0])/2,(a[1]+b[1])/2,dx,dz,l/2+.06,.1,-.1,.18,1,true);}
}
function buildRuins(b,units){
  for(const g of DATA.RUINS){
    const R=rng(g.id%99991+5),c=centroid(g.o);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    const th=dominantAngle(g.o),ux=Math.cos(th),uz=Math.sin(th),vx=-uz,vz=ux;
    const loc=p=>[p[0]*ux+p[1]*uz,-p[0]*uz+p[1]*ux];
    let a0=1e9,b0=1e9,a1=-1e9,b1=-1e9;for(const p of g.o){const [a,bb]=loc(p);a0=Math.min(a0,a);a1=Math.max(a1,a);b0=Math.min(b0,bb);b1=Math.max(b1,bb);}
    const isPalace=/Abencerraj/.test(g.n||''),big=isPalace||/Secano/.test(g.n||'');
    // pack rooms of varied size on a loose grid; a room is kept when its four corners are in the polygon
    const placed=[];
    const tries=big?260:80;
    for(let t=0;t<tries;t++){
      const pw=(isPalace?7+R()*9:5.5+R()*5.5),pd=(isPalace?8+R()*11:6+R()*6),a=a0+pw/2+R()*(a1-a0-pw),bb=b0+pd/2+R()*(b1-b0-pd),x=a*ux-bb*uz,z=a*uz+bb*ux;
      const ok=[[-1,-1],[1,-1],[1,1],[-1,1]].every(([sa,sb])=>{const px=x+ux*sa*pw/2+vx*sb*pd/2,pz=z+uz*sa*pw/2+vz*sb*pd/2;return inPoly(px,pz,g.o,g.h)||distPoly(px,pz,g.o)<1.0;});
      if(!ok||!inPoly(x,z,g.o,g.h))continue;
      // keep the garden walk open: no room within 2.8 m of its centre line
      if([[-1,-1],[1,-1],[1,1],[-1,1],[0,-1],[0,1],[-1,0],[1,0],[0,0]].some(([sa,sb])=>nearWalk(x+ux*sa*pw/2+vx*sb*pd/2,z+uz*sa*pw/2+vz*sb*pd/2,2.8)))continue;
      if(placed.some(q=>Math.abs(q.a-a)<(q.pw+pw)/2+1.4&&Math.abs(q.b-bb)<(q.pd+pd)/2+1.4))continue;
      placed.push({a,b:bb,pw,pd,x,z});
    }
    for(const q of placed)ruinHouse(R,q.x,q.z,ux,uz,q.pw,q.pd,isPalace?1.25:.95);
    // loose stones and a few standing fragments between the rooms
    if(big)for(let i=0;i<14;i++){const a=a0+R()*(a1-a0),bb=b0+R()*(b1-b0),x=a*ux-bb*uz,z=a*uz+bb*ux;if(inPoly(x,z,g.o,g.h)&&!placed.some(q=>Math.abs(q.a-a)<q.pw/2+1&&Math.abs(q.b-bb)<q.pd/2+1))rock(x,z,.3+R()*.5,R);}
  }
}

// ======================================================================= cloister of the convent, courtyard garden
function cloisterLayout(u,F,front,R,st,i,isOuter){
  if(isOuter)return layoutEdge(u,F,front,R,st);
  const ops=[],L=F.L;if(L<3)return ops;
  const nb=Math.max(1,Math.floor((L-.8)/3.1)),span=L-.8;
  for(let k=0;k<nb;k++){const c=.4+span*(k+.5)/nb;
    ops.push({type:'door',gallery:true,arch:true,s:c,w:2.3,h:3.7});
    ops.push({type:'win',s:c,w:.95,y0:floorY(1)+.95,h:1.4,shut:true});}
  return ops;
}
function galleryOpening(F,o,st,uo){
  // arched mouth of the cloister walk: dark depth behind, stone arch band and column bases
  const r=o.w/2,yc=o.h-r,dep=1.6,s0=o.s-r,s1=o.s+r;
  quad('grdDark',F.P(s0,0,-dep),F.P(s1,0,-dep),F.P(s1,yc,-dep),F.P(s0,yc,-dep),[0,0],[1,0],[1,1],[0,1],F.N);
  const arc=archPts(o.s,yc,r);
  for(let i=0;i<arc.length-1;i++)tri('grdDark',F.P(o.s,yc,-dep),F.P(arc[i][0],arc[i][1],-dep),F.P(arc[i+1][0],arc[i+1][1],-dep),[0,0],[1,0],[1,1],F.N);
  // soffit tiles and floor
  quad('grdPaving',F.P(s0,0,-dep),F.P(s1,0,-dep),F.P(s1,0,0),F.P(s0,0,0),[0,0],[1,0],[1,1],[0,1],[0,1,0]);
  const outer=archPts(o.s,yc,r+.28);
  for(let i=0;i<arc.length-1;i++)quad('grdStone',F.P(arc[i][0],arc[i][1],.04),F.P(arc[i+1][0],arc[i+1][1],.04),F.P(outer[i+1][0],outer[i+1][1],.04),F.P(outer[i][0],outer[i][1],.04),[i*.3,0],[(i+1)*.3,0],[(i+1)*.3,.28],[i*.3,.28],F.N);
  for(const sg of [-1,1]){quad('grdStone',F.P(o.s+sg*r,0,.04),F.P(o.s+sg*(r+.28),0,.04),F.P(o.s+sg*(r+.28),yc,.04),F.P(o.s+sg*r,yc,.04),[0,0],[.28,0],[.28,yc],[0,yc],F.N);
    const c=F.P(o.s+sg*(r+.14),0,.06);prismN('grdStone',c[0],c[2],.18,0,.5,8,0,1,true);}
}
function buildExtras(b,units){
  const R=rng(2024);
  for(const u of units){
    if(u.id!==20204470)continue;
    for(const hole of u.h){
      const [cx,cz]=centroid(hole),th=u.theta,ux=Math.cos(th),uz=Math.sin(th);
      CHUNK=`c${Math.floor(cx/90)}_${Math.floor(cz/90)}`;
      // paved court with cross-axis walks, hedged quarters and a central basin
      polyH('grdPaving',hole,[],YG.l3,2.4);
      const bb=bbox(hole),w=bb[2]-bb[0],d=bb[3]-bb[1];
      const vx=-uz,vz=ux;
      for(const sa of [-1,1])for(const sb of [-1,1]){
        const q=[[.7,.7],[.7,.7]];
        const c=[cx+ux*sa*Math.min(w,d)*.2+vx*sb*Math.min(w,d)*.2,cz+uz*sa*Math.min(w,d)*.2+vz*sb*Math.min(w,d)*.2];
        const hs=Math.min(w,d)*.17;
        const sq=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,bq])=>[c[0]+ux*a*hs+vx*bq*hs,c[1]+uz*a*hs+vz*bq*hs]);
        if(sq.every(p=>inRing(p[0],p[1],hole)))polyH('grdGrass',sq,[],YG.l3+.002,4);
        hedgeRun(sq,.4,.55,'grdHedge',-.02,true);
        plant(c[0],0,c[1],ORANGE,3.4);TREES_PLANTED++;
      }
      const n=8,r0=Math.min(w,d)*.09,pts=[];for(let i=0;i<n;i++)pts.push([cx+Math.cos(i*2*Math.PI/n+Math.PI/8)*r0,cz+Math.sin(i*2*Math.PI/n+Math.PI/8)*r0]);
      polyH('grdWater',pts,[],.1,1,true);
      for(let i=0;i<n;i++){const a=pts[i],c2=pts[(i+1)%n],l=D2(a,c2);obox('grdStone',(a[0]+c2[0])/2,(a[1]+c2[1])/2,(c2[0]-a[0])/l,(c2[1]-a[1])/l,l/2+.05,.14,0,.32,1,true);}
      prismN('grdStone',cx,cz,.22,.1,1.1,8,0,1,true);prismN('grdStone',cx,cz,.45,1.1,1.2,8,0,1,true);
    }
  }
}

// ======================================================================= walking surface
// Inside the enclosure the visible ground is the flat platform at y = 0, but the terrain sampler still follows the old
// procedural slope in the south-east (the Secano), so every walkable area is registered as nav floor at y = 0:
// the territory is rastered at 2 m and merged into long runs; the garden walk of tools/walk-routes.json is added explicitly.
const GARDEN_WALK=[[70,40],[70,97],[200,97],[200,252],[350,252],[380,240],[396,218],[396,202],[385,185],[370,177]];
function buildNavFloors(b,units){
  const cell=2,T=DATA.T[0],[x0,z0,x1,z1]=bbox(T.o),nx=Math.ceil((x1-x0)/cell),nz=Math.ceil((z1-z0)/cell),grid=new Uint8Array(nx*nz);
  for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){
    const x=x0+(i+.5)*cell,z=z0+(j+.5)*cell;let ok=false;for(const t of DATA.T)if(inPoly(x,z,t.o,t.h)){ok=true;break;}
    grid[j*nx+i]=ok?1:0;
  }
  // merge into rectangles: horizontal runs, then stack identical runs vertically
  const runs=[];
  for(let j=0;j<nz;j++){let i=0;while(i<nx){if(!grid[j*nx+i]){i++;continue;}let k=i;while(k<nx&&grid[j*nx+k])k++;runs.push({i,k,j,j2:j+1});i=k;}}
  const open=new Map(),out=[];
  for(let j=0;j<=nz;j++){
    const row=runs.filter(r=>r.j===j),nextOpen=new Map();
    for(const r of row){const key=r.i+'_'+r.k,o=open.get(key);if(o){o.j2=j+1;nextOpen.set(key,o);}else{const n={...r};nextOpen.set(key,n);out.push(n);}}
    open.clear();for(const [k,v] of nextOpen)open.set(k,v);
  }
  for(const r of out){const w=(r.k-r.i)*cell+.4,d=(r.j2-r.j)*cell+.4;b.nav.floor(x0+(r.i+r.k)/2*cell,z0+(r.j+r.j2)/2*cell,w,d,0,0);}
  for(let i=1;i<GARDEN_WALK.length;i++){const a=GARDEN_WALK[i-1],c=GARDEN_WALK[i],dx=c[0]-a[0],dz=c[1]-a[1];b.nav.floor((a[0]+c[0])/2,(a[1]+c[1])/2,Math.hypot(dx,dz)+4,6,0,-Math.atan2(dz,dx));}
  return out.length;
}

// ======================================================================= cypress walls, terrace, agaves, Rauda
// A tall clipped hedge wall with arched niches on its path side (the cypress walks of the Alhambra gardens), standing on the
// +n side of the segment A->B. Built in the same edge frame as the façades: a face polygon with arched holes, niche reveals,
// a back wall, ends and a top.
function hedgeWallSeg(A,B,thick,H,spacing,nicheW=2.5,nicheH=3.4,mat='grdCypress',side=1){
  const F=edgeFrame(side>0?A:B,side>0?B:A),L=F.L,nn=Math.max(1,Math.floor((L-1.5)/spacing)),ops=[];
  for(let i=0;i<nn;i++)ops.push({s:1.2+(L-2.4)*(i+.5)/nn,w:nicheW,h:nicheH});
  // front face: rectangle with arched holes
  const holes=ops.map(o=>{const r=o.w/2,yc=o.h-r,pts=[[o.s-r,0],[o.s+r,0]];for(let k=0;k<=8;k++){const a=Math.PI*k/8;pts.push([o.s+Math.cos(a)*r,yc+Math.sin(a)*r]);}return pts.filter((p,i,arr)=>true).reverse().reverse();});
  // arch hole contours must start at the base: use explicit ccw list
  const holeC=ops.map(o=>{const r=o.w/2,yc=o.h-r,pts=[[o.s-r,.001],[o.s+r,.001],[o.s+r,yc]];for(let k=1;k<8;k++){const a=Math.PI*k/8;pts.push([o.s+Math.cos(a)*r,yc+Math.sin(a)*r]);}pts.push([o.s-r,yc]);return pts;});
  // the face cannot have holes touching the bottom edge in the triangulator: lift the face by .02
  const topY=s=>H+.14*Math.sin(s*.9+L)+.1*Math.sin(s*2.3)+.12*(vn(s*1.3,L*.01)-.5)-.1;
  const topPts=[];for(let s=L;s>=0;s-=.5)topPts.push([s,topY(s)]);topPts.push([0,topY(0)]);
  const contour=[[0,0],[L,0],...topPts];
  wallPoly(mat,F,contour,holeC.map(h=>h.map(p=>[p[0],Math.max(p[1],.02)])),0,0,0,1.2);
  // niche reveals and back
  for(const o of ops){
    const r=o.w/2,yc=o.h-r,dep=.9,s0=o.s-r,s1=o.s+r,arc=archPts(o.s,yc,r,8);
    quad(mat,F.P(s0,0,0),F.P(s0,0,-dep),F.P(s0,yc,-dep),F.P(s0,yc,0),[0,0],[dep,0],[dep,yc],[0,yc],F.T);
    quad(mat,F.P(s1,0,0),F.P(s1,yc,0),F.P(s1,yc,-dep),F.P(s1,0,-dep),[0,0],[0,yc],[dep,yc],[dep,0],[-F.T[0],0,-F.T[2]]);
    for(let k=0;k<arc.length-1;k++){const am=Math.PI*(1-(k+.5)/(arc.length-1));quad(mat,F.P(arc[k][0],arc[k][1],0),F.P(arc[k+1][0],arc[k+1][1],0),F.P(arc[k+1][0],arc[k+1][1],-dep),F.P(arc[k][0],arc[k][1],-dep),[k*.3,0],[(k+1)*.3,0],[(k+1)*.3,dep],[k*.3,dep],norm3([-Math.cos(am)*F.T[0],-Math.sin(am),-Math.cos(am)*F.T[2]]));}
    quad('grdGroundDark',F.P(s0,.02,0),F.P(s1,.02,0),F.P(s1,.02,-dep),F.P(s0,.02,-dep),[0,0],[1,0],[1,1],[0,1],[0,1,0]);
    const pc=[[s0,0],[s1,0],[s1,yc]];for(let k=1;k<8;k++){const a=Math.PI*k/8;pc.push([o.s+Math.cos(a)*r,yc+Math.sin(a)*r]);}pc.push([s0,yc]);
    wallPoly(mat,F,pc,[],-dep,0,0,1.2);
  }
  // back, top and ends
  wallPoly(mat,F,[[L,0],[0,0],...[...topPts].reverse()],[],-thick,0,0,1.2);
  for(let i=0;i<topPts.length-1;i++){const a=topPts[i],c=topPts[i+1];quad(mat,F.P(a[0],a[1],0),F.P(c[0],c[1],0),F.P(c[0],c[1],-thick),F.P(a[0],a[1],-thick),[0,0],[.5,0],[.5,thick],[0,thick],[0,1,0]);}
  {const e=topPts[topPts.length-1],h0=topPts[0];
    quad(mat,F.P(0,0,0),F.P(0,e[1],0),F.P(0,e[1],-thick),F.P(0,0,-thick),[0,0],[H,0],[H,thick],[0,thick],[-F.T[0],0,-F.T[2]]);
    quad(mat,F.P(L,0,0),F.P(L,0,-thick),F.P(L,h0[1],-thick),F.P(L,h0[1],0),[0,0],[thick,0],[thick,H],[0,H],[F.T[0],0,F.T[2]]);}
  // clipped boxwood plinths in front, between the niches
  for(let i=0;i<=ops.length;i++){
    const a=i===0?0:ops[i-1].s+ops[i-1].w/2+.15,c=i===ops.length?L:ops[i].s-ops[i].w/2-.15;if(c-a<.8)continue;
    const m=F.P((a+c)/2,0,.45);obox('grdHedgeBox',m[0],m[2],F.tx,F.tz,(c-a)/2,.45,0,.95,1,true);
  }
  // a stone bench in the back of every niche
  for(const o of ops){const c=F.P(o.s,0,-.55);obox('grdStone',c[0],c[2],F.tx,F.tz,.8,.22,0,.42,1,true);obox('grdStone',c[0],c[2],F.tx,F.tz,.86,.26,.42,.5,1,true);}
  // the wall blocks walking; the niches are too shallow to enter
  const mid=F.P(L/2,0,-thick/2+.45);b_nav.box(mid[0],mid[2],L,thick+.9,0,H,Math.atan2(-F.tz,F.tx));
}
let b_nav=null;
function buildCypressWalk(b){
  b_nav=b.nav;
  const z=252,x0=216,x1=338;
  CHUNK='c2_2';
  for(const sg of [-1,1]){
    const zz=z+sg*(2.3+.45+1.0);       // wall front face at 2.3 m + plinth
    hedgeWallSeg([x0,zz],[x1,zz],1.9,6.4,6.2,2.5,3.4,'grdCypress',sg);
  }
}
// ---------------------------------------------------------------- terrace in front of the convent garden façade
function buildTerrace(b,units){
  const par=units.find(u=>u.id===20204470);if(!par)return;
  CHUNK='c2_1';
  const o=par.o;
  for(const i of [18,19,30,31,0,1]){/* handled below */}
  // two long fronts: north-west facade (221.8,137.5)->(245,146) and the north-east one (244.9,146.7)->(253.9,149.3)->(249.2,167.2)
  const runs=[[[221.8,137.5],[229.1,139.4]],[[231.4,143.1],[245.1,145.9]],[[244.9,146.7],[253.9,149.3]],[[253.9,149.3],[249.2,167.2]]];
  for(const [A,B2] of runs){
    const F=edgeFrame(A,B2),off=2.8,L=F.L;if(L<4)continue;
    const P=(s,y,d)=>F.P(s,y,d+off);
    // retaining wall of rubble with a brick coping, .75 m high
    const wall=(s0,s1)=>{const m=P((s0+s1)/2,0,0);obox('grdStone',m[0],m[2],F.tx,F.tz,(s1-s0)/2,.22,0,.75,1,false);obox('grdBrickB',m[0],m[2],F.tx,F.tz,(s1-s0)/2+.02,.27,.75,.85,1,true);};
    wall(0,L);
    const n=Math.max(1,Math.round(L/4));
    for(let k=0;k<=n;k++){const s=L*k/n,p=P(s,0,0);obox('grdBrickB',p[0],p[2],F.tx,F.tz,.2,.2,0,1.1,1,false);obox('grdStone',p[0],p[2],F.tx,F.tz,.26,.26,1.1,1.18,1,true);pot(p[0],1.18,p[2],1.5);}
    // iron railing between the pillars
    for(let k=0;k<n;k++){const s0=L*k/n+.25,s1=L*(k+1)/n-.25,A1=P(s0,.85,0),B1=P(s1,.85,0),C=P(s1,1.35,0),D=P(s0,1.35,0);quad('grdRailing',A1,B1,C,D,[0,0],[(s1-s0)/.5,0],[(s1-s0)/.5,1],[0,1],null);}
    const m=P(L/2,0,0);b.nav.box(m[0],m[2],L,.7,0,1.35,Math.atan2(-F.tz,F.tx));
  }
}
// ---------------------------------------------------------------- agaves and rubble on the dry slopes
function agave(x,z,s,R){
  const n=13;
  for(let i=0;i<n;i++){
    const a=i*2.399+R()*.3,len=(.8+R()*.5)*s,up=.5+.5*(i/n),dx=Math.cos(a),dz=Math.sin(a);
    const tip=[x+dx*len*.9,len*.55*(.4+up)+.02,z+dz*len*.9],base=[x,.02,z],wv=.09*s;
    const mid=[x+dx*len*.4,len*.38*(.3+up*.8),z+dz*len*.4],px=-dz*wv,pz=dx*wv;
    const col='grdAgave';
    tri(col,[base[0]-px*.6,base[1],base[2]-pz*.6],[base[0]+px*.6,base[1],base[2]+pz*.6],[mid[0]+px,mid[1],mid[2]+pz],[0,0],[1,0],[1,.5],null);
    tri(col,[base[0]-px*.6,base[1],base[2]-pz*.6],[mid[0]+px,mid[1],mid[2]+pz],[mid[0]-px,mid[1],mid[2]-pz],[0,0],[1,.5],[0,.5],null);
    tri(col,[mid[0]-px,mid[1],mid[2]-pz],[mid[0]+px,mid[1],mid[2]+pz],tip,[0,.5],[1,.5],[.5,1],null);
    // reverse faces so the blade is seen from below as well
    tri(col,[base[0]+px*.6,base[1],base[2]+pz*.6],[base[0]-px*.6,base[1],base[2]-pz*.6],[mid[0]-px,mid[1],mid[2]-pz],[1,0],[0,0],[0,.5],null);
    tri(col,[base[0]+px*.6,base[1],base[2]+pz*.6],[mid[0]-px,mid[1],mid[2]-pz],[mid[0]+px,mid[1],mid[2]+pz],[1,0],[0,.5],[1,.5],null);
    tri(col,[mid[0]+px,mid[1],mid[2]+pz],[mid[0]-px,mid[1],mid[2]-pz],tip,[1,.5],[0,.5],[.5,1],null);
  }
}
function rock(x,z,r,R,mat='grdRuin'){
  ball(mat,x,r*.18,z,r*(.8+R()*.5),r*(.35+R()*.25),r*(.7+R()*.4),R()*6);
}
function buildDryGround(b,units){
  if(LOW)return;
  const R=rng(555);CHUNK='c2_2';
  // the Secano and the wall gardens: agaves, boulders and stone heaps
  for(let i=0;i<900;i++){
    const x=170+R()*250,z=100+R()*190;
    if(!inT(x,z)||!freeSpot(x,z,units,3,2.4))continue;
    let inBed=false;for(const g of DATA.BEDS)if(g.k!=='parking'&&inPoly(x,z,g.o,g.h)){inBed=true;break;}if(inBed)continue;
    const d=vn(x/22,z/22);
    CHUNK=`c${Math.floor(x/90)}_${Math.floor(z/90)}`;
    if(d>.62&&R()<.12)agave(x,z,.9+R()*.7,R);
    else if(d>.55&&R()<.1)rock(x,z,.35+R()*.7,R);
  }
}
// ---------------------------------------------------------------- the Rauda: cemetery garden foundations
function buildRauda(b){
  const c=[23.5,50.5],ux=.97,uz=-.24,vx=-uz,vz=ux,hw=7.5,hd=9.5;
  CHUNK='c0_0';
  const Pp=(a,bb)=>[c[0]+ux*a+vx*bb,c[1]+uz*a+vz*bb];
  const ring=[Pp(-hw,-hd),Pp(hw,-hd),Pp(hw,hd),Pp(-hw,hd)];
  polyH('grdGravel',ring,[],YG.l1+.001,3);
  const R=rng(88);
  for(let i=0;i<4;i++){const a=ring[i],q=ring[(i+1)%4];ruinWall(R,a,q,.6,.8);}
  // rows of low box hedges and cypresses in the cemetery garden
  for(const sa of [-1,1])for(const sb of [-1,0,1]){
    const p=Pp(sa*3.6,sb*5.4);plant(p[0],0,p[1],CYPRESS,10+R()*3);TREES_PLANTED++;
    const sq=[[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,bb])=>Pp(sa*3.6+a*1.7,sb*5.4+bb*2.2));polyH('grdGrass',sq,[],YG.l3,4);hedgeRun(sq,.4,.5,'grdHedge',-.02,true);}
  // a central ablution basin
  const bs=[[-1.2,-.9],[1.2,-.9],[1.2,.9],[-1.2,.9]].map(([a,bb])=>Pp(a,bb));polyH('grdWater',bs,[],-.02,1,true);
  for(let i=0;i<4;i++){const a=bs[i],q=bs[(i+1)%4],L=D2(a,q);obox('grdStone',(a[0]+q[0])/2,(a[1]+q[1])/2,(q[0]-a[0])/L,(q[1]-a[1])/L,L/2+.06,.12,-.1,.2,1,true);}
}

// ======================================================================= rose bushes, benches, pergola
const ICO=(()=>{const t=(1+Math.sqrt(5))/2;let v=[[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]].map(norm3);
  let f=[[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]];
  const cache=new Map(),mid=(a,b)=>{const k=a<b?a+'_'+b:b+'_'+a;if(cache.has(k))return cache.get(k);v.push(norm3([(v[a][0]+v[b][0])/2,(v[a][1]+v[b][1])/2,(v[a][2]+v[b][2])/2]));cache.set(k,v.length-1);return v.length-1;};
  const f2=[];for(const [a,b,c] of f){const ab=mid(a,b),bc=mid(b,c),ca=mid(c,a);f2.push([a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca]);}return {v,f:f2};})();
function ball(mat,x,y,z,rx,ry,rz,rot=0){
  const c=Math.cos(rot),s=Math.sin(rot);
  const P=ICO.v.map(([a,b,d])=>{const px=a*rx,pz=d*rz;return [x+px*c-pz*s,y+b*ry,z+px*s+pz*c];});
  for(const [a,b,d] of ICO.f){const na=ICO.v[a],nb=ICO.v[b],nd=ICO.v[d];
    tri(mat,P[a],P[b],P[d],[na[0]*.5+.5,na[1]*.5+.5],[nb[0]*.5+.5,nb[1]*.5+.5],[nd[0]*.5+.5,nd[1]*.5+.5],null);}
}
let BUSHES=0;
const FLOWER_MATS=['flower','whiteFlower','grdRose2','grdRed','grdYellowF','flower'];
function roseBush(R,x,z,s=1){
  ball('grdBush',x,.32*s,z,.5*s,.34*s,.5*s,R()*6);BUSHES++;
  const m=FLOWER_MATS[Math.floor(R()*FLOWER_MATS.length)],n=LOW?4:7;
  for(let i=0;i<n;i++){const a=R()*6.283,rr=R()*.42*s,y=.34*s+R()*.3*s;blob(m,x+Math.cos(a)*rr,y,z+Math.sin(a)*rr,.055*s);}
}
function bench(x,z,ux,uz,len=1.8){
  const vx=-uz,vz=ux;
  for(const sg of [-1,1])obox('grdStone',x+ux*sg*(len/2-.12),z+uz*sg*(len/2-.12),ux,uz,.07,.22,0,.42,1,true);
  obox('grdStone',x,z,ux,uz,len/2,.26,.42,.5,1,true);
  // back rest: slab on two posts
  obox('grdStone',x-vx*.23,z-vz*.23,ux,uz,len/2-.1,.04,.5,.95,1,true);
  for(const sg of [-1,1])obox('grdStone',x-vx*.23+ux*sg*(len/2-.2),z-vz*.23+uz*sg*(len/2-.2),ux,uz,.05,.05,.5,.98,1,true);
}
function pergola(a,c,w,h){
  const L=D2(a,c),ux=(c[0]-a[0])/L,uz=(c[1]-a[1])/L,vx=-uz,vz=ux,n=Math.max(2,Math.round(L/2.6));
  for(let i=0;i<=n;i++){const s=L*i/n,px=a[0]+ux*s,pz=a[1]+uz*s;
    for(const sg of [-1,1]){const qx=px+vx*sg*w/2,qz=pz+vz*sg*w/2;obox('grdBrickB',qx,qz,ux,uz,.14,.14,0,h-.2,1,true);b_nav.box(qx,qz,.34,.34,0,h);}
    obox('grdBeam',px,pz,vx,vz,w/2+.4,.07,h-.2,h-.04,1,true);}
  for(const sg of [-1,.0,1]){const qx=a[0]+vx*sg*(w/2+.1),qz=a[1]+vz*sg*(w/2+.1);obox('grdBeam',(a[0]+c[0])/2+vx*sg*(w/2+.1),(a[1]+c[1])/2+vz*sg*(w/2+.1),ux,uz,L/2+.4,.07,h-.04,h+.1,1,true);}
  // cross rafters and the vine: irregular leaf masses, thicker over the rafters, trailing at the sides
  const m=Math.round(L/.5);for(let i=0;i<=m;i++){const s=L*i/m,px=a[0]+ux*s,pz=a[1]+uz*s;obox('grdBeam',px,pz,vx,vz,w/2+.35,.025,h+.1,h+.16,1,true);}
  const R=rng(Math.round(a[0]*7+a[1])),cnt=Math.round(L*(LOW?1.2:2.4));
  for(let i=0;i<cnt;i++){const s=R()*L,o=(R()-.5)*(w+.5),px=a[0]+ux*s+vx*o,pz=a[1]+uz*s+vz*o,r=.3+R()*.45;ball('grdHedge',px,h+.2+R()*.16,pz,r,r*.42,r,R()*6);}
  for(let i=0;i<Math.round(cnt*.5);i++){const s=R()*L,sg=R()<.5?-1:1,o=sg*(w/2+.2+R()*.2),px=a[0]+ux*s+vx*o,pz=a[1]+uz*s+vz*o,r=.18+R()*.2;ball('grdHedge',px,h-.25-R()*.5,pz,r,r*1.6,r,R()*6);}
}
function buildLife(b,units){
  const R=rng(8080);
  // rose bushes: a regular planting inside the clipped parterres and kitchen beds
  for(const g of DATA.BEDS){
    if(g.k!=='bed')continue;const area=Math.abs(ringArea(g.o));if(area<18)continue;
    const c=centroid(g.o);CHUNK=`c${Math.floor(c[0]/90)}_${Math.floor(c[1]/90)}`;
    const [x0,z0,x1,z1]=bbox(g.o),sp=area>120?3.1:2.4;let n=0;
    for(let z=z0+sp/2;z<z1;z+=sp)for(let x=x0+sp/2;x<x1;x+=sp){
      if(n>14)break;const px=x+(R()-.5)*.35,pz=z+(R()-.5)*.35;
      if(!inPoly(px,pz,g.o,g.h)||distPoly(px,pz,g.o)<.9)continue;if(R()<.18)continue;
      if(nearWalk(px,pz,2.4))continue;roseBush(R,px,pz,.7+R()*.5);n++;}
  }
  // stone benches along the quieter paths and on the church square
  const spots=[];
  for(const p of DATA.PATHS){const st=pathStyle(p);if(st.calle||p.hw==='steps')continue;let acc=8+R()*12;
    for(let i=1;i<p.p.length;i++){const a=p.p[i-1],q=p.p[i],L=D2(a,q),ux=(q[0]-a[0])/L,uz=(q[1]-a[1])/L;
      for(let s=acc;s<L;s+=34){const side=R()<.5?1:-1,off=st.w/2+.45,x=a[0]+ux*s-uz*off*side,z=a[1]+uz*s+ux*off*side;
        if(inT(x,z)&&freeSpot(x,z,units,1.5,-.3)&&R()<.55)spots.push([x,z,ux,uz]);}
      acc=((acc-L)%34+34)%34;}}
  for(const [x,z,ux,uz] of spots.slice(0,40)){CHUNK=`c${Math.floor(x/90)}_${Math.floor(z/90)}`;bench(x,z,ux,uz);}
  // a vine pergola over the long straight walk in the convent garden
  let best=null;
  for(const p of DATA.PATHS){if(p.hw!=='footway'&&p.hw!=='path')continue;for(let i=1;i<p.p.length;i++){const a=p.p[i-1],q=p.p[i],L=D2(a,q);if(L<22||a[0]<165||a[0]>235||a[1]<157||a[1]>205)continue;if(!best||L>best.L)best={a,q,L};}}
  if(best){const {a,q,L}=best,ux=(q[0]-a[0])/L,uz=(q[1]-a[1])/L,len=Math.min(L-4,20),a2=[a[0]+ux*2,a[1]+uz*2],c2=[a2[0]+ux*len,a2[1]+uz*len];
    if(freeSpot(a2[0],a2[1],units,1.5,-2)&&freeSpot(c2[0],c2[1],units,1.5,-2)){CHUNK=`c${Math.floor(a2[0]/90)}_${Math.floor(a2[1]/90)}`;pergola(a2,c2,2.8,2.7);}}
}

// ======================================================================= entry point
export function build(b,ctx){
  LOW=!!ctx.low;ctx_per=ctx.perimeter;b_nav=b.nav;b.zone='grounds';
  buildGround(b,ctx);
  const units=buildAllUnits(b);
  buildHedges(b);buildRuins(b,units);buildPlanting(b,units);buildFurniture(b,units);buildExtras(b,units);buildCypressWalk(b);buildTerrace(b,units);buildDryGround(b,units);buildRauda(b);buildLife(b,units);
  const nf=buildNavFloors(b,units);
  flush(b);
  console.log('grounds triangles',TRIS,'units',units.length,'trees',TREES_PLANTED,'bushes',BUSHES,'navfloors',nf);
}

// ======================================================================= data (OpenStreetMap, ODbL)
const DATA=JSON.parse(`{"T":[{"o":[[-67.7,129.74],[-54.83,135.12],[-53.54,132.06],[-52.03,128.45],[-50.03,123.64],[-49.29,121.88],[-48.08,118.7],[-20.87,130.9],[-22.4,134.05],[-12.23,138.97],[-10.71,135.82],[30.18,150.05],[32.03,150.85],[34.46,151.89],[38.52,153.62],[44.0,155.87],[65.77,164.8],[78.19,172.99],[86.18,179.72],[93.76,186.94],[95.49,184.96],[129.5,211.59],[113.4,230.97],[117.44,237.03],[123.56,240.23],[140.77,219.99],[175.9,247.02],[172.34,252.77],[177.8,256.15],[181.35,250.38],[213.23,264.47],[210.54,271.09],[216.76,273.82],[219.95,267.21],[253.11,275.02],[252.18,303.47],[252.77,306.98],[255.1,309.7],[258.22,311.06],[261.92,311.45],[266.41,311.45],[268.94,309.89],[271.08,307.37],[271.48,303.08],[271.76,276.18],[325.25,279.78],[324.8,288.09],[330.16,288.37],[330.61,280.07],[358.24,282.84],[361.64,291.35],[367.44,289.02],[364.01,280.42],[374.82,275.64],[383.33,271.14],[393.94,271.03],[393.89,272.44],[405.07,272.91],[405.51,262.24],[402.02,262.09],[401.38,260.03],[402.36,249.57],[403.38,238.67],[405.78,237.42],[405.9,233.95],[407.54,220.32],[409.31,219.45],[411.52,221.04],[415.79,218.91],[415.35,214.11],[411.52,211.8],[406.44,212.97],[404.24,213.48],[360.39,184.06],[359.25,183.3],[346.33,177.09],[351.61,168.12],[343.08,163.11],[338.24,171.33],[320.94,156.84],[306.83,138.42],[298.0,121.92],[310.08,115.29],[306.17,108.18],[294.09,114.8],[274.79,97.39],[261.92,75.1],[257.81,71.21],[264.42,64.98],[260.75,61.07],[254.13,67.3],[247.95,62.42],[218.18,42.2],[224.89,36.75],[227.19,34.84],[227.44,31.01],[222.42,25.04],[229.99,19.87],[226.07,14.75],[231.91,10.2],[226.77,3.48],[220.85,7.95],[220.36,7.3],[209.24,14.89],[200.0,4.34],[200.0,80.0],[60.0,80.0],[60.0,45.0],[13.2,45.0],[10.4,59.42],[4.27,90.94],[4.25,91.0],[4.24,91.06],[4.21,91.11],[4.18,91.16],[4.15,91.21],[4.11,91.25],[4.06,91.29],[4.02,91.33],[3.97,91.36],[3.91,91.38],[3.86,91.4],[3.8,91.42],[3.74,91.43],[3.68,91.43],[3.62,91.43],[3.57,91.42],[-26.97,85.48],[-57.95,79.46],[-58.01,79.44],[-58.07,79.43],[-58.12,79.4],[-58.17,79.37],[-58.22,79.34],[-58.26,79.3],[-58.3,79.25],[-58.34,79.21],[-58.37,79.16],[-58.39,79.1],[-58.41,79.05],[-58.43,78.99],[-58.44,78.93],[-58.44,78.87],[-58.44,78.81],[-58.43,78.76],[-52.27,47.12],[-51.86,45.0],[-75.0,45.0],[-75.0,111.17],[-62.16,116.51]],"h":[]}],"BLD":[{"o":[[224.63,15.76],[219.5,9.06],[226.77,3.48],[231.91,10.2]],"h":[],"id":92528627,"lv":1,"n":"","part":false,"bt":"yes","ru":""},{"o":[[37.65,86.13],[41.62,86.96],[42.87,81.03],[53.56,83.28],[51.96,90.97],[59.22,92.52],[56.92,103.58],[51.37,102.4],[50.19,108.04],[37.72,105.4],[38.93,99.63],[35.56,98.93],[35.32,100.07],[33.3,99.64],[33.55,98.4],[29.71,97.57],[29.48,98.65],[27.74,98.28],[27.98,97.12],[21.54,95.76],[24.16,83.22],[30.59,84.58],[30.89,83.13],[32.46,83.46],[32.18,84.89],[36.2,85.73],[36.47,84.4],[37.94,84.71]],"h":[],"id":17369758,"lv":1,"n":"Iglesia de Santa Mar\u00eda de la Alhambra","part":false,"bt":"church","ru":""},{"o":[[157.58,109.66],[168.72,109.84],[168.49,122.82],[159.33,122.66],[159.16,133.01],[147.68,132.82],[147.98,115.07],[157.49,115.24]],"h":[],"id":17369768,"lv":1,"n":"","part":false,"bt":"residential","ru":""},{"o":[[64.16,100.22],[72.91,102.63],[71.3,107.92],[78.7,110.18],[77.49,113.98],[80.89,114.96],[79.9,118.18],[89.23,120.35],[85.4,130.24],[65.34,123.39],[65.44,123.02],[61.62,121.74],[62.79,117.95],[60.8,117.29],[62.22,112.83],[60.79,112.36]],"h":[],"id":96485675,"lv":1,"n":"Ba\u00f1o de la Mezquita","part":false,"bt":"public","ru":""},{"o":[[37.13,116.72],[48.24,121.54],[45.62,128.07],[34.57,123.24]],"h":[],"id":15086687,"lv":2,"n":"","part":false,"bt":"apartments","ru":""},{"o":[[74.74,133.06],[71.84,139.75],[62.87,135.82],[65.68,129.12]],"h":[],"id":15086692,"lv":2,"n":"","part":false,"bt":"residential","ru":""},{"o":[[171.47,131.13],[175.27,131.88],[173.77,138.5],[170.39,137.87]],"h":[],"id":15086697,"lv":1,"n":"","part":false,"bt":"retail","ru":""},{"o":[[35.5,116.02],[33.97,119.69],[27.3,117.23],[26.18,119.74],[22.69,118.4],[25.57,111.71]],"h":[],"id":49978124,"lv":2,"n":"Casa de la Estafeta","part":false,"bt":"residential","ru":""},{"o":[[33.97,119.69],[35.5,116.02],[37.13,116.72],[35.7,120.33]],"h":[],"id":76959799,"lv":1,"n":"","part":false,"bt":"residential","ru":""},{"o":[[66.22,152.95],[71.84,139.75],[75.59,141.41],[73.75,145.81],[88.05,153.76],[82.82,162.44]],"h":[],"id":76959801,"lv":1,"n":"","part":false,"bt":"ruins","ru":"industrial"},{"o":[[186.12,135.4],[197.61,138.64],[196.63,142.71],[198.1,143.15],[198.1,154.06],[177.82,148.51],[180.1,138.87],[184.78,140.2]],"h":[],"id":76959766,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[210.06,157.37],[201.9,155.11],[201.9,139.92],[206.13,141.14],[205.08,145.14],[210.96,146.95],[210.43,148.6],[212.22,149.21]],"h":[],"id":76959766,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[180.1,138.87],[177.82,148.51],[174.24,147.54],[177.36,132.85],[175.67,132.35],[176.92,126.65],[184.97,129.0],[185.29,127.81],[188.07,128.52],[190.02,121.49],[198.1,123.62],[198.1,136.56],[197.61,138.64],[186.12,135.4],[184.78,140.2]],"h":[],"id":76959768,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[220.32,171.15],[201.9,166.13],[201.9,155.11],[210.06,157.37],[212.22,149.21],[210.43,148.6],[211.36,145.61],[216.34,146.96],[217.05,144.46],[220.07,145.26],[219.83,146.39],[226.98,148.79],[222.71,166.07],[221.47,165.73]],"h":[],"id":76959769,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[221.47,165.73],[226.52,167.07],[225.44,172.53],[220.32,171.15]],"h":[],"id":76959770,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[247.38,173.45],[242.35,171.74],[244.16,165.67],[249.15,167.19]],"h":[],"id":76959771,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[116.01,116.82],[116.21,113.28],[120.8,113.4],[120.61,116.98],[123.53,117.0],[123.44,120.17],[112.62,119.74],[112.78,116.73]],"h":[],"id":76959772,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[95.44,95.1],[95.49,91.77],[114.59,92.2],[114.4,95.1]],"h":[],"id":76959774,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[123.61,113.48],[123.53,117.0],[120.61,116.98],[120.8,113.4]],"h":[],"id":76959775,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[109.04,135.68],[110.17,127.58],[121.78,126.23],[122.2,133.95]],"h":[],"id":76959776,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[114.4,95.1],[114.59,92.2],[117.82,92.27],[117.61,95.1]],"h":[],"id":76959777,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[108.93,136.49],[109.04,135.68],[122.2,133.95],[122.41,137.96],[107.6,139.77],[107.63,136.68]],"h":[],"id":76959778,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[109.31,119.58],[109.43,116.64],[112.78,116.73],[112.35,124.62],[103.8,124.19],[104.02,119.29]],"h":[],"id":76959779,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[95.33,101.33],[95.37,98.9],[114.14,98.9],[113.94,101.96]],"h":[],"id":76959782,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[113.94,101.96],[114.14,98.9],[117.43,98.9],[117.15,104.93],[113.72,104.76],[113.07,111.49],[108.12,111.29],[108.62,101.78]],"h":[],"id":76959783,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[94.94,123.61],[95.15,110.75],[113.07,111.49],[112.78,116.73],[104.14,116.52],[103.8,124.19]],"h":[],"id":76959784,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[112.99,113.2],[113.72,104.76],[117.15,104.93],[116.77,113.3]],"h":[],"id":76959786,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[112.78,116.73],[112.99,113.2],[116.21,113.28],[116.01,116.82]],"h":[],"id":76959787,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[54.2,144.95],[53.1,147.48],[50.38,146.32],[52.78,140.78],[50.43,139.8],[49.1,142.79],[45.23,141.05],[48.9,133.46],[53.92,135.7],[55.67,132.08],[63.06,135.38],[58.26,146.79]],"h":[],"id":76959791,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[92.9,147.43],[88.05,153.76],[85.03,152.07],[90.12,145.99]],"h":[],"id":76959792,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[49.1,142.79],[48.0,145.28],[44.0,143.56],[45.23,141.05]],"h":[],"id":76959793,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[26.18,119.74],[27.51,120.29],[24.19,127.95],[27.37,129.18],[30.63,121.59],[34.57,123.24],[30.11,134.52],[17.98,129.19],[21.36,121.41],[24.95,122.73]],"h":[],"id":76959794,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[48.24,121.54],[56.5,125.12],[53.74,131.24],[50.64,129.85],[48.04,135.24],[45.5,134.13],[44.47,136.04],[47.1,137.18],[45.23,141.05],[41.27,138.92]],"h":[],"id":76959795,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[24.19,127.95],[27.51,120.29],[30.63,121.59],[27.37,129.18]],"h":[],"id":76959797,"lv":4,"n":"","part":true,"bt":"","ru":""},{"o":[[53.1,147.48],[54.2,144.95],[58.26,146.79],[57.23,149.28]],"h":[],"id":76959798,"lv":1,"n":"","part":true,"bt":"","ru":""},{"o":[[55.67,132.08],[53.92,135.7],[48.9,133.46],[50.64,129.85]],"h":[],"id":76959800,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[65.68,129.12],[63.06,135.38],[58.25,133.23],[60.89,127.04]],"h":[],"id":76959802,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[83.65,142.59],[77.1,139.92],[76.38,141.61],[71.84,139.75],[74.74,133.06],[85.88,137.91],[85.48,138.8],[95.81,143.61],[92.9,147.43]],"h":[],"id":76959803,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[53.74,131.24],[56.5,125.12],[60.89,127.04],[58.25,133.23]],"h":[],"id":76959804,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[135.75,118.28],[135.47,112.63],[139.97,112.42],[140.42,121.83],[125.79,122.53],[125.33,113.12],[129.34,112.93],[129.62,118.58]],"h":[],"id":76959810,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[129.62,118.58],[129.34,112.93],[135.47,112.63],[135.75,118.28]],"h":[],"id":76959811,"lv":3,"n":"","part":true,"bt":"","ru":""},{"o":[[139.97,112.42],[125.33,113.12],[125.14,109.05],[139.77,108.34]],"h":[],"id":76959812,"lv":2,"n":"","part":true,"bt":"","ru":""},{"o":[[244.93,146.73],[253.9,149.27],[249.15,167.19],[244.16,165.67],[242.35,171.74],[247.38,173.45],[248.27,170.3],[249.67,170.87],[251.76,166.84],[278.84,179.25],[273.84,189.31],[246.61,176.74],[246.24,178.31],[225.44,172.53],[226.52,167.07],[222.71,166.07],[226.98,148.79],[219.83,146.39],[221.81,137.5],[229.07,139.39],[228.42,142.29],[231.42,143.12],[231.64,142.21],[233.92,142.96],[233.72,143.55],[236.32,144.29],[236.62,143.59],[238.93,144.25],[238.75,144.95],[241.98,145.78],[242.19,145.19],[245.1,145.92]],"h":[[[240.05,155.29],[230.04,152.58],[227.34,162.56],[237.34,165.28]]],"id":20204470,"lv":2,"n":"","part":true,"bt":"","ru":""}],"BEDS":[{"o":[[96.05,79.0],[160.41,79.0],[160.58,83.03],[159.49,87.59],[136.75,86.02],[136.61,89.18],[118.9,88.43],[119.03,85.32],[95.87,84.35]],"h":[],"k":"garden","n":"Jardines del Partal","id":17357971},{"o":[[-75.91,44.58],[-69.44,45.85],[-71.98,59.33],[-60.73,61.6],[-62.92,73.33],[-76.0,68.66]],"h":[],"k":"bed","n":"","id":96481159},{"o":[[40.06,62.68],[43.39,45.0],[61.0,47.77],[61.0,67.08]],"h":[],"k":"bed","n":"","id":96485667},{"o":[[220.29,236.04],[202.64,226.88],[220.99,197.53],[251.9,207.3],[257.05,192.02],[283.11,199.34],[277.83,217.69],[262.62,214.64],[258.41,246.87],[251.71,246.13],[236.85,242.73],[226.62,239.05]],"h":[],"k":"garden","n":"Jard\u00edn del Secano y Tener\u00edas","id":96500584},{"o":[[180.03,91.83],[181.47,79.0],[199.0,79.0],[199.0,30.8],[220.47,50.03],[250.48,69.73],[259.59,76.21],[273.38,99.46],[293.55,116.4],[292.98,127.21],[284.76,143.44],[293.06,149.0],[286.42,163.7],[254.13,148.48],[232.66,137.85],[218.32,134.05],[217.26,141.21],[200.65,136.71],[204.27,123.06],[175.84,115.33],[181.13,93.36]],"h":[],"k":"garden","n":"Jard\u00edn del Convento de San Francisco","id":2256623},{"o":[[8.85,98.25],[14.93,66.06],[59.81,74.12],[59.32,76.3],[61.0,76.61],[61.0,79.0],[65.55,79.0],[65.04,81.36],[68.67,82.08],[64.16,100.22],[60.79,112.36],[62.22,112.83],[60.8,117.29],[62.79,117.95],[61.62,121.74]],"h":[],"k":"plaza","n":"","id":15086688},{"o":[[165.37,174.27],[166.29,168.73],[187.93,173.67],[187.16,177.0],[190.31,177.86],[190.06,180.27],[186.29,180.53],[186.29,190.12],[161.94,190.87],[159.64,185.54],[158.13,180.55],[157.32,175.4]],"h":[],"k":"parking","n":"","id":15086698},{"o":[[257.85,201.13],[265.75,204.15],[264.15,209.08],[255.97,205.92]],"h":[],"k":"bed","n":"","id":81947209},{"o":[[253.31,212.06],[255.08,207.55],[258.93,208.91],[257.79,212.72]],"h":[],"k":"bed","n":"","id":81947210},{"o":[[260.08,218.05],[254.66,220.05],[254.4,219.41],[258.37,215.37],[260.23,215.64]],"h":[],"k":"bed","n":"","id":81947212},{"o":[[256.01,215.15],[252.6,218.13],[250.83,217.06],[251.93,214.4]],"h":[],"k":"bed","n":"","id":81947213},{"o":[[232.75,233.73],[235.42,227.39],[246.1,232.22],[244.18,239.89],[241.57,239.36],[241.04,240.68],[233.61,238.43],[235.06,234.62]],"h":[],"k":"bed","n":"","id":81947214},{"o":[[248.21,240.73],[246.14,240.31],[248.07,232.74],[258.03,231.66],[256.4,243.46],[247.95,242.09]],"h":[],"k":"bed","n":"","id":81947215},{"o":[[254.05,230.13],[248.71,230.63],[249.06,228.75],[251.03,228.14]],"h":[],"k":"bed","n":"","id":81947216},{"o":[[246.71,227.99],[246.35,230.0],[240.86,227.65],[244.89,227.03]],"h":[],"k":"bed","n":"","id":81947217},{"o":[[242.85,223.93],[243.11,225.68],[236.9,226.59],[236.64,224.86]],"h":[],"k":"bed","n":"","id":81947218},{"o":[[237.47,222.9],[238.49,220.52],[242.67,222.22]],"h":[],"k":"bed","n":"","id":81947219},{"o":[[245.56,218.24],[244.28,220.16],[239.49,218.2],[241.15,213.53]],"h":[],"k":"bed","n":"","id":81947220},{"o":[[249.5,216.66],[246.72,217.23],[242.86,213.12],[250.49,214.24]],"h":[],"k":"bed","n":"","id":81947221},{"o":[[259.62,220.08],[259.11,223.79],[255.78,223.21],[255.32,221.97]],"h":[],"k":"bed","n":"","id":81947222},{"o":[[258.9,225.31],[258.75,227.09],[255.04,224.88]],"h":[],"k":"bed","n":"","id":81947223},{"o":[[258.23,230.17],[256.77,230.27],[251.99,227.32],[253.49,226.07],[258.41,228.89]],"h":[],"k":"bed","n":"","id":81947224},{"o":[[273.13,215.15],[274.19,211.74],[276.89,212.64],[276.27,215.65]],"h":[],"k":"bed","n":"","id":81947225},{"o":[[277.25,210.94],[274.77,210.06],[275.68,207.41],[277.82,208.24]],"h":[],"k":"bed","n":"","id":81947226},{"o":[[273.25,209.52],[267.2,207.37],[268.22,204.61],[274.25,206.91]],"h":[],"k":"bed","n":"","id":81947227},{"o":[[270.73,214.77],[264.37,213.76],[266.12,209.01],[272.01,211.01]],"h":[],"k":"bed","n":"","id":81947233},{"o":[[263.63,210.65],[262.71,213.49],[259.53,213.0],[260.58,209.52]],"h":[],"k":"bed","n":"","id":81947234},{"o":[[235.21,220.45],[217.5,212.26],[220.84,205.06],[225.24,207.1],[223.59,210.67],[236.88,216.82]],"h":[],"k":"bed","n":"","id":81947235},{"o":[[227.85,227.2],[230.57,220.87],[234.97,222.75],[232.25,229.1]],"h":[],"k":"bed","n":"","id":81947236},{"o":[[222.19,217.17],[219.51,223.42],[213.34,220.78],[216.02,214.52]],"h":[],"k":"bed","n":"","id":81947237},{"o":[[228.26,238.1],[206.95,228.27],[209.94,221.77],[218.34,225.65],[217.93,226.53],[226.02,230.25],[226.73,228.71],[231.56,230.93]],"h":[],"k":"bed","n":"","id":81947238},{"o":[[188.26,172.98],[178.29,170.82],[178.77,168.54],[181.06,169.03],[181.53,166.85],[189.22,168.51]],"h":[],"k":"bed","n":"","id":82005369},{"o":[[170.38,168.88],[171.33,164.69],[175.92,165.72],[175.48,167.66],[177.44,168.12],[176.93,170.36]],"h":[],"k":"bed","n":"","id":82005370},{"o":[[179.39,159.99],[178.93,162.09],[176.9,161.65],[176.51,163.44],[172.08,162.46],[173.31,156.88],[177.68,157.84],[177.31,159.53]],"h":[],"k":"bed","n":"","id":82005371},{"o":[[180.63,160.28],[182.11,160.59],[182.39,159.25],[189.61,160.78],[189.3,162.24],[190.56,162.5],[189.65,166.78],[181.94,165.14],[182.41,162.91],[180.18,162.44]],"h":[],"k":"bed","n":"","id":82005372},{"o":[[230.59,177.77],[231.37,174.75],[236.01,176.03],[235.21,178.95]],"h":[],"k":"bed","n":"","id":82005374},{"o":[[234.51,181.02],[233.6,184.69],[229.06,183.56],[229.97,179.89]],"h":[],"k":"bed","n":"","id":82005375},{"o":[[217.23,180.83],[218.21,176.9],[227.71,179.28],[226.72,183.21]],"h":[],"k":"bed","n":"","id":82005376},{"o":[[228.42,177.25],[218.73,174.79],[219.57,171.52],[229.21,174.16]],"h":[],"k":"bed","n":"","id":82005377},{"o":[[216.29,174.13],[209.09,172.3],[209.96,168.88],[217.12,170.84]],"h":[],"k":"bed","n":"","id":82005378},{"o":[[214.92,180.64],[207.51,178.75],[208.6,174.49],[216.0,176.39]],"h":[],"k":"bed","n":"","id":82005379},{"o":[[206.15,174.02],[205.05,178.32],[191.08,174.76],[192.18,170.46]],"h":[],"k":"bed","n":"","id":82005380},{"o":[[190.47,157.22],[190.3,157.92],[183.12,156.19],[183.29,155.51],[181.76,155.14],[182.25,153.09],[180.72,152.72],[180.21,154.82],[178.52,154.41],[178.36,155.05],[174.08,154.01],[175.36,148.59],[199.99,155.4],[197.61,165.5],[207.5,168.2],[206.69,171.51],[192.59,168.1],[193.77,163.22],[194.8,163.47],[195.99,158.55]],"h":[],"k":"bed","n":"","id":82005382},{"o":[[140.25,150.76],[145.18,150.67],[145.45,159.24],[140.08,157.22]],"h":[],"k":"bed","n":"","id":82273590},{"o":[[140.32,142.88],[145.17,142.46],[145.35,148.26],[140.18,148.38]],"h":[],"k":"bed","n":"","id":82273591},{"o":[[122.34,144.4],[137.83,143.09],[137.54,156.14],[122.25,149.78]],"h":[],"k":"bed","n":"","id":82273593},{"o":[[122.63,86.63],[123.04,79.0],[129.45,79.0],[129.17,84.36],[136.91,84.77],[137.21,79.0],[143.2,79.0],[142.74,87.69]],"h":[],"k":"garden","n":"","id":82273607},{"o":[[248.85,99.25],[199.0,61.5],[199.0,54.76],[252.26,94.73]],"h":[],"k":"bed","n":"","id":82273616},{"o":[[210.73,46.6],[203.36,56.42],[199.0,53.14],[199.0,44.73],[202.33,40.3]],"h":[],"k":"bed","n":"","id":82273637},{"o":[[263.24,126.92],[267.07,120.83],[274.08,125.22],[270.26,131.32]],"h":[],"k":"bed","n":"","id":82273638},{"o":[[261.59,125.82],[255.53,122.02],[260.52,114.06],[266.59,117.87]],"h":[],"k":"bed","n":"","id":82273639},{"o":[[253.62,121.37],[243.81,114.36],[249.83,105.94],[259.64,112.96]],"h":[],"k":"bed","n":"","id":82273640},{"o":[[242.81,113.7],[234.94,108.07],[241.07,99.5],[248.94,105.13]],"h":[],"k":"bed","n":"","id":82273641},{"o":[[234.05,107.11],[226.19,101.49],[232.23,93.02],[240.1,98.65]],"h":[],"k":"bed","n":"","id":82273642},{"o":[[225.36,101.03],[217.49,95.4],[223.68,86.75],[231.55,92.37]],"h":[],"k":"bed","n":"","id":82273643},{"o":[[216.54,94.7],[208.68,89.07],[214.93,80.33],[222.8,85.96]],"h":[],"k":"bed","n":"","id":82273644},{"o":[[207.88,88.49],[200.01,82.87],[206.33,74.03],[214.2,79.65]],"h":[],"k":"bed","n":"","id":82273645},{"o":[[253.93,93.8],[248.3,88.74],[254.16,81.84],[259.6,88.99]],"h":[],"k":"bed","n":"","id":82273646},{"o":[[247.48,88.6],[239.78,82.38],[247.11,73.23],[253.79,80.02]],"h":[],"k":"bed","n":"","id":82273647},{"o":[[238.49,82.1],[231.33,76.72],[239.06,66.45],[246.21,71.82]],"h":[],"k":"bed","n":"","id":82273648},{"o":[[230.14,75.83],[221.63,69.44],[229.27,59.28],[237.78,65.67]],"h":[],"k":"bed","n":"","id":82273649},{"o":[[220.39,68.78],[213.63,63.7],[221.17,53.66],[227.94,58.74]],"h":[],"k":"bed","n":"","id":82273650},{"o":[[212.14,62.97],[204.52,57.24],[211.98,47.31],[219.61,53.04]],"h":[],"k":"bed","n":"","id":82273651},{"o":[[244.93,188.6],[249.71,178.17],[273.84,189.31],[286.42,163.7],[293.06,149.0],[299.52,153.34],[281.85,195.16]],"h":[],"k":"garden","n":"","id":83149329},{"o":[[251.16,101.02],[254.36,96.19],[273.61,113.45],[272.04,115.74]],"h":[],"k":"bed","n":"","id":83149332},{"o":[[175.58,80.95],[163.56,79.0],[175.9,79.0]],"h":[],"k":"garden","n":"","id":83149334},{"o":[[159.87,193.77],[155.51,181.37],[158.13,180.55],[159.64,185.54],[161.94,190.87],[167.82,190.76],[167.9,205.14],[164.99,202.13],[162.24,198.08]],"h":[],"k":"garden","n":"","id":47894712}],"RUINS":[{"o":[[244.93,188.6],[257.05,192.02],[251.9,207.3],[220.99,197.53],[202.64,226.88],[171.24,207.5],[167.9,205.14],[167.82,190.76],[186.29,190.12],[186.29,180.53],[190.06,180.27],[190.31,177.86]],"h":[],"k":"ruin","n":"Secano","id":96500562},{"o":[[95.81,143.61],[148.32,169.77],[149.05,180.38],[152.27,189.51],[155.0,195.2],[131.9,213.26],[129.5,211.59],[95.49,184.96],[98.36,181.65],[80.91,166.11],[82.82,162.44],[88.05,153.76]],"h":[],"k":"ruin","n":"\u00c1rea Arqueol\u00f3gica del Palacio de Abencerrajes","id":96500578},{"o":[[-37.0,102.59],[-33.62,91.4],[-9.81,96.73],[-14.61,109.52]],"h":[],"k":"ruin","n":"Palacio del Mufti","id":96500582},{"o":[[25.46,59.61],[16.64,57.75],[17.53,54.78],[15.24,54.01],[18.25,44.0],[31.7,44.0]],"h":[],"k":"ruin","n":"","id":70349180},{"o":[[347.02,233.5],[344.37,240.73],[318.32,230.58],[321.24,221.53]],"h":[],"k":"ruin","n":"","id":67204702},{"o":[[353.32,248.2],[357.47,238.16],[365.25,241.33],[361.77,249.64]],"h":[],"k":"ruin","n":"","id":67204703}],"PATHS":[{"p":[[-75.5,98.52],[-74.32,94.72]],"hw":"steps","s":"","n":"","a":false},{"p":[[6.77,95.3],[13.91,60.12]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[94.31,79.88],[120.74,80.16],[120.75,79.5]],"hw":"footway","s":"","n":"","a":false},{"p":[[152.37,167.75],[152.89,176.73]],"hw":"footway","s":"asphalt","n":"","a":false},{"p":[[-54.02,46.78],[-65.6,44.5]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[9.69,103.16],[106.42,144.14],[118.88,151.54],[152.37,167.75]],"hw":"pedestrian","s":"asphalt","n":"Calle Real de la Alhambra","a":false},{"p":[[-75.5,72.13],[-67.46,74.41],[-61.37,82.04]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[94.31,79.88],[91.98,138.23]],"hw":"pedestrian","s":"unhewn_cobblestone","n":"","a":false},{"p":[[-49.44,84.69],[-50.98,92.56],[-47.76,100.63],[-38.81,110.95],[-6.4,124.73]],"hw":"service","s":"concrete","n":"","a":false},{"p":[[-56.6,118.73],[-56.16,124.38],[-52.03,128.45]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[-56.6,118.73],[-54.22,112.51],[-75.5,104.99]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[-47.76,100.63],[-64.41,94.91],[-61.37,82.04]],"hw":"footway","s":"","n":"","a":false},{"p":[[-70.21,92.94],[-64.41,94.91]],"hw":"steps","s":"","n":"","a":false},{"p":[[-74.32,94.72],[-73.25,91.81],[-70.21,92.94]],"hw":"footway","s":"","n":"","a":false},{"p":[[34.85,147.68],[35.47,146.42],[23.35,139.37],[-3.32,126.05]],"hw":"service","s":"asphalt","n":"","a":false},{"p":[[-61.37,82.04],[-53.55,44.5]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[152.89,176.73],[153.36,181.59],[157.42,192.83],[160.52,199.41],[163.8,203.82],[169.51,208.68],[194.41,225.42]],"hw":"footway","s":"concrete","n":"","a":false},{"p":[[16.12,60.56],[60.5,69.27]],"hw":"footway","s":"","n":"","a":false},{"p":[[152.37,167.75],[165.03,163.11],[167.43,162.65]],"hw":"footway","s":"","n":"","a":false},{"p":[[167.43,162.65],[177.04,165.01]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[208.11,172.94],[235.78,179.98]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[231.84,243.55],[248.41,248.37],[252.79,248.77]],"hw":"footway","s":"concrete","n":"","a":false},{"p":[[194.41,225.42],[225.17,241.45],[231.84,243.55]],"hw":"footway","s":"concrete","n":"","a":false},{"p":[[252.79,248.77],[257.16,249.18],[266.42,248.44],[273.79,247.07],[290.19,242.82],[299.97,242.2],[312.99,243.3],[347.79,250.99],[366.04,253.72],[372.06,252.82],[376.5,250.76],[392.16,233.04],[405.9,233.95]],"hw":"footway","s":"concrete","n":"","a":false},{"p":[[202.42,229.72],[220.28,203.14]],"hw":"footway","s":"","n":"","a":false},{"p":[[-61.37,82.04],[-49.44,84.69],[-9.21,92.64]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[9.69,103.16],[-3.81,98.84],[-9.21,92.64]],"hw":"pedestrian","s":"unhewn_cobblestone","n":"Calle Real de la Alhambra","a":false},{"p":[[9.69,103.16],[11.07,99.88]],"hw":"footway","s":"","n":"","a":false},{"p":[[12.34,94.86],[13.93,87.34],[22.9,89.26]],"hw":"footway","s":"","n":"","a":false},{"p":[[11.07,99.88],[12.34,94.86]],"hw":"steps","s":"","n":"","a":false},{"p":[[-9.21,92.64],[6.77,95.3]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[199.5,54.34],[203.8,57.37]],"hw":"footway","s":"","n":"","a":false},{"p":[[203.8,57.37],[253.91,94.71]],"hw":"footway","s":"dirt","n":"","a":false},{"p":[[266.42,248.44],[267.89,251.83],[274.07,257.45],[273.68,269.03],[263.08,268.68],[262.97,275.61]],"hw":"footway","s":"","n":"","a":false},{"p":[[273.68,269.03],[273.68,275.61]],"hw":"steps","s":"","n":"","a":false},{"p":[[273.68,275.61],[270.99,275.37],[270.83,280.53]],"hw":"steps","s":"","n":"","a":false},{"p":[[270.83,280.53],[254.02,279.34],[254.1,274.37]],"hw":"footway","s":"","n":"","a":false},{"p":[[254.1,274.37],[249.04,273.47]],"hw":"steps","s":"","n":"","a":false},{"p":[[249.04,273.47],[220.22,266.69]],"hw":"footway","s":"","n":"","a":false},{"p":[[220.22,266.69],[213.45,263.94]],"hw":"footway","s":"","n":"","a":false},{"p":[[273.68,275.61],[325.26,279.16]],"hw":"footway","s":"","n":"","a":false},{"p":[[325.26,279.16],[330.66,279.41]],"hw":"footway","s":"","n":"","a":false},{"p":[[330.66,279.41],[358.03,282.32]],"hw":"footway","s":"","n":"","a":false},{"p":[[358.03,282.32],[363.8,279.9]],"hw":"footway","s":"","n":"","a":false},{"p":[[363.8,279.9],[374.58,274.86],[382.76,270.35],[393.97,270.39]],"hw":"footway","s":"","n":"","a":false},{"p":[[58.15,44.5],[60.47,44.84]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[13.91,60.12],[13.99,54.29],[15.97,44.5]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[13.91,60.12],[16.12,60.56]],"hw":"footway","s":"","n":"","a":false},{"p":[[254.29,206.45],[260.03,208.49]],"hw":"footway","s":"","n":"","a":false},{"p":[[278.63,206.69],[267.48,202.75]],"hw":"footway","s":"","n":"","a":false},{"p":[[273.92,210.43],[277.89,211.78]],"hw":"footway","s":"","n":"","a":false},{"p":[[275.62,205.62],[271.95,216.03]],"hw":"footway","s":"","n":"","a":false},{"p":[[271.95,216.03],[263.05,214.79]],"hw":"footway","s":"","n":"","a":false},{"p":[[271.95,216.03],[277.14,216.74],[278.63,206.69]],"hw":"footway","s":"","n":"","a":false},{"p":[[230.14,219.16],[226.54,227.57]],"hw":"footway","s":"","n":"","a":false},{"p":[[223.95,216.47],[230.14,219.16]],"hw":"footway","s":"","n":"","a":false},{"p":[[223.95,216.47],[214.16,212.25]],"hw":"footway","s":"","n":"","a":false},{"p":[[230.14,219.16],[236.47,221.88]],"hw":"footway","s":"","n":"","a":false},{"p":[[220.33,224.91],[223.95,216.47]],"hw":"footway","s":"","n":"","a":false},{"p":[[231.84,239.67],[257.37,245.17]],"hw":"footway","s":"","n":"","a":false},{"p":[[253.65,221.48],[260.79,218.86]],"hw":"footway","s":"","n":"","a":false},{"p":[[237.34,227.45],[248.44,225.72],[257.04,231.03]],"hw":"footway","s":"dirt","n":"","a":false},{"p":[[237.98,218.31],[244.68,221.04]],"hw":"footway","s":"","n":"","a":false},{"p":[[252.67,224.77],[259.49,228.84]],"hw":"footway","s":"","n":"","a":false},{"p":[[252.7,219.12],[258.31,214.19]],"hw":"footway","s":"","n":"","a":false},{"p":[[244.76,223.14],[235.37,224.49]],"hw":"footway","s":"","n":"","a":false},{"p":[[246.6,218.16],[240.7,211.88]],"hw":"footway","s":"","n":"","a":false},{"p":[[257.17,199.12],[249.97,217.46]],"hw":"footway","s":"","n":"","a":false},{"p":[[264.67,210.34],[265.75,207.65]],"hw":"footway","s":"","n":"","a":false},{"p":[[265.75,207.65],[273.92,210.43]],"hw":"footway","s":"","n":"","a":false},{"p":[[264.67,210.34],[263.05,214.79]],"hw":"footway","s":"","n":"","a":false},{"p":[[240.7,211.88],[263.05,214.79]],"hw":"footway","s":"","n":"","a":false},{"p":[[232.18,239.75],[233.84,235.81],[231.08,234.65],[240.7,211.88]],"hw":"footway","s":"","n":"","a":false},{"p":[[265.75,207.65],[267.48,202.75],[257.17,199.12]],"hw":"footway","s":"","n":"","a":false},{"p":[[260.03,208.49],[264.67,210.34]],"hw":"footway","s":"","n":"","a":false},{"p":[[258.31,214.19],[260.03,208.49]],"hw":"footway","s":"","n":"","a":false},{"p":[[232.92,230.3],[208.94,220.01]],"hw":"footway","s":"","n":"","a":false},{"p":[[253.44,223.35],[260.06,224.49]],"hw":"footway","s":"dirt","n":"","a":false},{"p":[[253.65,221.48],[252.7,219.12],[249.97,217.46],[246.6,218.16],[244.68,221.04],[244.76,223.14],[248.44,225.72],[252.67,224.77],[253.44,223.35],[253.65,221.48]],"hw":"footway","s":"","n":"","a":false},{"p":[[259.23,230.83],[247.29,231.95],[234.64,226.22]],"hw":"footway","s":"","n":"","a":false},{"p":[[257.37,245.17],[261.35,214.59]],"hw":"footway","s":"","n":"","a":false},{"p":[[243.5,246.94],[247.29,231.95],[248.44,225.72]],"hw":"footway","s":"","n":"","a":false},{"p":[[182.35,157.75],[190.7,159.82]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[180.89,155.42],[181.28,153.62]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[179.21,163.5],[180.11,159.15]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[191.16,157.94],[190.23,161.66],[194.24,162.65],[195.16,158.93],[191.16,157.94]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[178.94,154.97],[178.08,158.69],[181.92,159.58],[182.78,155.87],[178.94,154.97]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[177.9,169.67],[178.4,167.33]],"hw":"footway","s":"","n":"","a":false},{"p":[[180.76,165.96],[190.7,168.48]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[177.43,163.13],[176.62,166.95],[180.38,167.74],[181.19,163.92],[177.43,163.13]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[189.01,175.86],[188.37,178.68]],"hw":"steps","s":"","n":"","a":false},{"p":[[190.7,168.48],[208.11,172.94]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[192.12,162.14],[189.01,175.86]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[170.12,163.25],[172.1,155.22],[178.52,156.81]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[234.43,185.45],[236.67,176.36]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[227.64,184.01],[229.98,174.56]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[215.66,181.5],[218.2,171.21]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[206.48,179.56],[209.11,168.88]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[189.01,175.86],[234.43,185.45]],"hw":"footway","s":"unhewn_cobblestone","n":"","a":false},{"p":[[139.23,149.51],[165.01,149.16]],"hw":"footway","s":"","n":"","a":false},{"p":[[150.44,166.81],[149.71,139.08],[139.48,139.53]],"hw":"footway","s":"","n":"","a":false},{"p":[[138.94,161.25],[139.48,139.53],[106.42,144.14]],"hw":"footway","s":"asphalt","n":"","a":false},{"p":[[-75.5,76.93],[-70.78,78.09],[-73.93,93.66],[-49.13,101.53],[-51.59,110.54],[-47.32,111.94],[-47.79,113.5],[-11.81,128.73],[-7.61,117.78],[-37.49,106.52],[-40.3,103.72],[-43.45,98.71],[-40.7,83.4],[-58.89,79.91],[-52.02,44.5]],"hw":"pedestrian","s":"paving_stones","n":"Placeta Carlos V","a":true},{"p":[[50.82,54.75],[41.35,49.65]],"hw":"footway","s":"","n":"","a":false},{"p":[[49.56,64.68],[51.99,57.69]],"hw":"footway","s":"","n":"","a":false},{"p":[[60.5,59.98],[54.28,56.71]],"hw":"footway","s":"","n":"","a":false},{"p":[[55.72,46.93],[56.56,44.5]],"hw":"footway","s":"","n":"","a":false},{"p":[[42.32,44.5],[38.46,64.94]],"hw":"footway","s":"","n":"","a":false},{"p":[[53.11,53.87],[55.72,46.93]],"hw":"footway","s":"","n":"","a":false},{"p":[[54.49,55.58],[54.05,54.51],[53.11,53.87],[51.97,53.82],[50.98,54.4],[50.47,55.43],[50.59,56.56],[51.3,57.46],[52.4,57.82],[53.5,57.54],[54.28,56.71],[54.49,55.58]],"hw":"footway","s":"","n":"","a":false},{"p":[[48.69,66.95],[49.56,64.68]],"hw":"footway","s":"","n":"","a":false},{"p":[[283.42,143.56],[288.68,132.08]],"hw":"footway","s":"","n":"","a":false},{"p":[[189.75,82.22],[182.19,79.5]],"hw":"footway","s":"","n":"","a":false},{"p":[[213.23,108.46],[208.67,105.58]],"hw":"footway","s":"","n":"","a":false},{"p":[[216.71,107.6],[220.34,101.52]],"hw":"footway","s":"","n":"","a":false},{"p":[[212.51,114.63],[214.06,112.04]],"hw":"footway","s":"","n":"","a":false},{"p":[[214.06,112.04],[216.08,113.32],[218.84,108.95],[216.71,107.6]],"hw":"footway","s":"","n":"","a":false},{"p":[[218.81,118.17],[279.46,152.24],[283.42,143.56],[226.81,105.61]],"hw":"footway","s":"","n":"","a":false},{"p":[[213.82,97.42],[205.45,110.66]],"hw":"footway","s":"","n":"","a":false},{"p":[[201.86,89.87],[193.13,103.74]],"hw":"footway","s":"","n":"","a":false},{"p":[[195.55,85.88],[186.62,100.09]],"hw":"footway","s":"","n":"","a":false},{"p":[[216.71,107.6],[214.61,106.28],[211.85,110.65],[214.06,112.04]],"hw":"footway","s":"","n":"","a":false},{"p":[[259.1,132.38],[261.25,128.69]],"hw":"footway","s":"","n":"","a":false},{"p":[[255.62,138.84],[256.93,136.3]],"hw":"footway","s":"","n":"","a":false},{"p":[[269.87,141.98],[281.01,148.85]],"hw":"footway","s":"","n":"","a":false},{"p":[[246.86,127.9],[256.02,133.54]],"hw":"footway","s":"","n":"","a":false},{"p":[[233.95,119.94],[242.6,125.27]],"hw":"footway","s":"","n":"","a":false},{"p":[[218.11,110.08],[230.27,117.75]],"hw":"footway","s":"","n":"","a":false},{"p":[[267.66,142.2],[268.8,142.46],[269.87,141.98],[270.45,140.98],[270.32,139.83],[269.56,138.96],[268.43,138.72],[267.37,139.17],[266.77,140.16],[266.88,141.33],[267.66,142.2]],"hw":"footway","s":"","n":"","a":false},{"p":[[256.93,136.3],[258.29,136.57],[259.55,135.98],[260.22,134.76],[260.05,133.39],[259.1,132.38],[257.74,132.11],[256.48,132.7],[255.82,133.92],[255.99,135.29],[256.93,136.3]],"hw":"footway","s":"","n":"","a":false},{"p":[[243.53,128.88],[245.13,129.14],[246.58,128.42],[246.86,127.9],[247.33,126.98],[247.08,125.39],[245.95,124.23],[244.36,123.97],[242.9,124.69],[242.16,126.13],[242.4,127.73],[243.53,128.88]],"hw":"footway","s":"","n":"","a":false},{"p":[[230.81,121.04],[232.16,121.34],[233.44,120.79],[233.95,119.94],[234.02,118.22],[233.1,117.18],[231.75,116.87],[230.27,117.75],[229.77,118.61],[229.89,119.99],[230.81,121.04]],"hw":"footway","s":"","n":"","a":false},{"p":[[267.55,132.93],[262.28,142.58]],"hw":"footway","s":"","n":"","a":false},{"p":[[254.92,124.44],[248.76,134.99]],"hw":"footway","s":"","n":"","a":false},{"p":[[235.97,127.81],[242.46,116.1]],"hw":"footway","s":"","n":"","a":false},{"p":[[222.6,120.29],[229.92,107.69]],"hw":"footway","s":"","n":"","a":false},{"p":[[259.66,135.78],[266.77,140.16]],"hw":"footway","s":"","n":"","a":false},{"p":[[189.75,82.22],[226.81,105.61],[218.81,118.17],[180.66,96.74],[189.75,82.22]],"hw":"footway","s":"","n":"","a":false},{"p":[[163.14,177.81],[183.2,181.95]],"hw":"service","s":"asphalt","n":"","a":false},{"p":[[183.2,181.95],[188.37,178.68]],"hw":"footway","s":"","n":"","a":false},{"p":[[152.37,167.75],[160.35,172.41],[160.9,174.88],[163.14,177.81]],"hw":"service","s":"asphalt","n":"","a":false},{"p":[[-6.4,124.73],[-3.32,126.05],[9.69,103.16]],"hw":"service","s":"asphalt","n":"","a":false},{"p":[[288.68,132.08],[290.9,135.71],[323.28,166.88],[395.93,219.43],[392.16,233.04]],"hw":"footway","s":"compacted","n":"Paseo de las Torres","a":false},{"p":[[33.71,147.15],[34.3,145.74]],"hw":"footway","s":"","n":"","a":false},{"p":[[153.36,181.59],[156.62,180.23],[155.74,174.18],[152.8,174.52]],"hw":"footway","s":"","n":"","a":false},{"p":[[9.91,59.33],[13.91,60.12]],"hw":"footway","s":"","n":"","a":false},{"p":[[-51.78,47.21],[-54.02,46.78]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[-26.88,84.99],[-27.7,88.99]],"hw":"footway","s":"paving_stones","n":"","a":false},{"p":[[67.0,129.69],[67.79,127.92]],"hw":"footway","s":"","n":"","a":false},{"p":[[0.42,119.48],[28.87,137.03],[41.56,143.32],[40.84,144.88],[57.42,152.21],[64.24,136.42]],"hw":"footway","s":"","n":"","a":false},{"p":[[199.5,39.2],[201.1,36.35],[214.01,47.62],[244.36,68.72],[254.87,80.03],[260.76,88.96],[253.91,94.71]],"hw":"footway","s":"","n":"","a":false},{"p":[[194.48,79.5],[270.85,132.47],[281.11,124.89]],"hw":"footway","s":"","n":"","a":false},{"p":[[199.5,66.1],[281.11,124.89],[287.92,131.31]],"hw":"footway","s":"","n":"","a":false},{"p":[[256.4,96.63],[285.58,124.11]],"hw":"footway","s":"dirt","n":"","a":false},{"p":[[199.5,28.05],[212.23,41.62],[248.9,68.7],[258.57,78.59],[269.56,97.79],[277.52,107.01],[292.26,119.4],[290.85,123.05]],"hw":"footway","s":"dirt","n":"Paseo de las Torres","a":false},{"p":[[253.91,94.71],[256.4,96.63]],"hw":"steps","s":"dirt","n":"","a":false},{"p":[[290.85,123.05],[292.82,124.46],[287.92,131.31],[288.68,132.08]],"hw":"footway","s":"dirt","n":"Paseo de las Torres","a":false},{"p":[[285.58,124.11],[288.51,126.23],[290.85,123.05]],"hw":"steps","s":"dirt","n":"Paseo de las Torres","a":false},{"p":[[-49.61,123.92],[-50.03,123.64],[-53.54,132.06]],"hw":"pedestrian","s":"","n":"Plaza de la Explanada","a":true}],"TREES":[[143.06,154.99,""],[143.55,143.83,""],[135.57,144.46,""],[130.51,149.56,""],[154.54,150.4,""],[125.52,145.26,""],[130.55,144.86,""],[22.1,135.0,""],[14.65,130.04,""],[7.21,125.1,""],[-8.76,115.44,""],[-13.95,113.1,""],[-19.06,110.8,""],[-26.57,107.41,""],[-33.55,104.27,""],[-39.28,101.09,""],[-42.95,95.37,""],[-46.63,89.65,""],[162.65,172.94,""],[167.08,159.21,""],[168.14,148.28,""],[168.81,145.01,""],[166.26,133.64,""],[162.84,133.54,""],[151.96,133.83,""],[95.0,132.34,""],[89.15,124.97,""],[88.36,128.02,""],[89.85,122.31,""]]}`);
