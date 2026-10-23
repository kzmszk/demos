import * as THREE from 'three';
import { toCreasedNormals, mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { random } from '../materials.js';
import { plant, CYPRESS, ORANGE, PALM, SHRUB, POPLAR } from '../trees.js';

// El Partal: Palacio del Partal / Torre de las Damas on its pool, the casas nazaríes, the Oratorio and Torre del
// Mihrab on the north wall, and the terraced Jardines del Partal. Footprints follow the OSM outlines
// (Palacio del Partal, Torre de las Damas, Oratorio, ponds, hedges); heights and details are taken from
// Wikimedia Commons photographs (see public/textures/partal/credits.json).
// Local frame of every facade: u to the right seen from outside, y up, w outward; yaw turns it into the world.

const TX='textures/partal/';
const loadImg=async f=>{try{const i=new Image();i.src=TX+f;await i.decode();return i;}catch(e){return null;}};

export async function materials(M){
  const names=['brick_a','brick_a_h','brick_b','brick_b_h','tile','tile_h','stone','stone_h','marble','marble_h','timber','timber_h','tapial','tapial_h','sand','gravel','pebble','hedge','grass','stucco','shutter'];
  const img={};await Promise.all(names.map(async n=>{img[n]=await loadImg(n+'.jpg');}));
  for(let k=0;k<4;k++)img['lattice'+k]=await loadImg('lattice'+k+'.png');
  const tex=(i,{color=true,tw=1,th=1,mirror=false}={})=>{
    const t=new THREE.Texture(i);t.wrapS=t.wrapT=mirror?THREE.MirroredRepeatWrapping:THREE.RepeatWrapping;
    t.colorSpace=color?THREE.SRGBColorSpace:THREE.NoColorSpace;t.repeat.set(1/tw,1/th);t.anisotropy=8;t.needsUpdate=true;return t;
  };
  const mat=(name,{map,bump,tw=1,th=1,color=0xffffff,rough=.92,bs=.03,side,alpha,metal=0,po=0,mirror=false}={})=>{
    const m=new THREE.MeshStandardMaterial({color,roughness:rough,metalness:metal});m.name=name;m.userData={scale:1};
    if(map)m.map=tex(map,{tw,th,mirror});if(bump){m.bumpMap=tex(bump,{color:false,tw,th,mirror});m.bumpScale=bs;}
    if(side!==undefined)m.side=side;if(alpha){m.alphaTest=alpha;}
    if(po){m.polygonOffset=true;m.polygonOffsetFactor=-po;m.polygonOffsetUnits=-po;}
    M[name]=m;return m;
  };
  const bumpOf=(a,b)=>b||a;
  mat('partalBrick',{map:img.brick_a,bump:img.brick_a_h,tw:1.32,th:1.32,bs:.05});
  mat('partalBrickOld',{map:img.brick_b,bump:img.brick_b_h,tw:1.32,th:1.32,bs:.05});
  mat('partalTile',{map:img.tile,bump:img.tile_h,tw:1.02,th:1.2,bs:.05,rough:.82});
  mat('partalStone',{map:img.stone,bump:img.stone_h,tw:1.8,th:1.8,bs:.05,rough:.88});
  mat('partalPaving',{map:img.stone,bump:img.stone_h,tw:1.8,th:1.8,bs:.04,rough:.88,po:1});
  mat('partalMarble',{map:img.marble,bump:img.marble_h,tw:1.6,th:1.6,bs:.02,rough:.45,po:1});
  mat('partalTimber',{map:img.timber,bump:img.timber_h,tw:1.0,th:1.0,bs:.03,rough:.75});
  mat('partalTapial',{map:img.tapial,bump:img.tapial_h,tw:3.6,th:3.6,bs:.07,rough:.98,color:0xffe4c8});
  mat('partalSand',{map:img.sand,tw:2.0,th:2.0,rough:1,po:1});
  mat('partalGravel',{map:img.gravel,bump:img.gravel,tw:1.6,th:1.6,bs:.04,rough:1,po:1});
  mat('partalPebble',{map:img.pebble,bump:img.pebble,tw:1.6,th:1.6,bs:.05,rough:.9,po:2});
  mat('partalHedge',{map:img.hedge,bump:img.hedge,tw:.6,th:.6,bs:.08,rough:.95});
  mat('partalGrass',{map:img.grass,tw:1.0,th:1.0,rough:1,po:1});
  mat('partalIvy',{map:img.hedge,bump:img.hedge,tw:.5,th:.5,bs:.08,rough:.95,color:0x9fb27c});
  mat('partalRoseLeaf',{map:img.hedge,bump:img.hedge,tw:.5,th:.5,bs:.06,rough:.9,color:0xb4c88a});mat('partalSoil',{color:0x5a4130,rough:1,po:1});mat('partalTilePot',{color:0xb5603a,rough:.85});mat('partalPoolBed',{color:0x7c9a93,rough:.6});mat('partalCorbel',{color:0x4a2d1d,rough:.8});mat('partalChannel',{color:0x4d7f7a,rough:.15,metal:.1});
  for(const [n,c] of [['partalRoseR',0xb02a3a],['partalRoseP',0xd98aa0],['partalRoseW',0xd9cfbd],['partalRoseY',0xd9ac35]]){const m=mat(n,{color:c,rough:.7});m.emissive=new THREE.Color(c).multiplyScalar(.12);}
  // plain materials
  mat('partalFlat',{color:0xc9a98a});mat('partalLion',{color:0xd8d0bd,rough:.8});
  mat('partalStucco',{map:img.stucco,bump:img.stucco,tw:1.364,th:.4545,bs:.05,color:0xe8ddc4,rough:.9});
  mat('partalStuccoPlain',{color:0xe6d8b8,rough:.92});mat('partalColumn',{color:0xf0eee6,rough:.45});
  mat('partalShutter',{map:img.shutter,bump:img.shutter,tw:.5,th:.8,bs:.04,rough:.75});
  mat('partalCapital',{color:0xd8b98a});
  mat('partalIron',{color:0x2d2622,rough:.6,metal:.3});mat('partalDark',{color:0x2a1d16});
  // Interior finishes: clones of the Nasrid interior materials with a higher indirect-light share (the portico and
  // hall are open to the south / lit through windows, and no extra point lights are added to the scene).
  for(const [n,src,amb,col] of [['partalStuccoInt','fineStucco',1.0,0xf0dfc0],['partalTileInt','tile',1.0,0xffffff],['partalFriezeInt','frieze',1.0,0xffffff],['partalCedarInt','cedar',1.0,0xffffff]]){
    if(!M[src])continue;const m=M[src].clone();m.name=n;m.userData={...M[src].userData,interiorAmbient:amb};m.color.set(col);if(n==='partalStuccoInt'&&m.map){m.emissive.set(0xffe6c0);m.emissiveMap=m.map;m.emissiveIntensity=.55;}M[n]=m;}
  for(let k=0;k<4;k++)mat('partalLat'+k,{map:img['lattice'+k],tw:1.8,th:1.24,alpha:.5,side:THREE.DoubleSide,rough:.9});
}

// ---------------------------------------------------------------------------------------------------------
// geometry helpers
const PI=Math.PI;
const F=(x,z,yaw=0,y=0)=>({x,z,yaw,y});
const xf=(g,f)=>{if(f.yaw)g.rotateY(f.yaw);g.translate(f.x,f.y||0,f.z);return g;};
// World-space planar UVs (metres), chosen per triangle by its dominant axis, then creased smooth normals.
function prep(g,crease=.62){
  const ng=g.index?g.toNonIndexed():g;ng.deleteAttribute('uv');ng.deleteAttribute('normal');
  const p=ng.attributes.position,n=p.count,uv=new Float32Array(n*2);
  const A=new THREE.Vector3(),B=new THREE.Vector3(),C=new THREE.Vector3(),e1=new THREE.Vector3(),e2=new THREE.Vector3(),N=new THREE.Vector3();
  for(let i=0;i<n;i+=3){
    A.fromBufferAttribute(p,i);B.fromBufferAttribute(p,i+1);C.fromBufferAttribute(p,i+2);
    N.crossVectors(e1.subVectors(B,A),e2.subVectors(C,A));const ax=Math.abs(N.x),ay=Math.abs(N.y),az=Math.abs(N.z);
    for(let k=0;k<3;k++){const v=k===0?A:k===1?B:C;let u,w;
      if(ay>=ax&&ay>=az){u=v.x;w=v.z;}else if(ax>=az){u=v.z;w=v.y;}else{u=v.x;w=v.y;}
      uv[(i+k)*2]=u;uv[(i+k)*2+1]=w;}
  }
  ng.setAttribute('uv',new THREE.BufferAttribute(uv,2));
  const out=toCreasedNormals(ng,crease);return out;
}
const put=(b,g,f,mat,crease)=>b.unique(prep(xf(g,f),crease),mat);
const V2=(a)=>a.map(p=>new THREE.Vector2(p[0],p[1]));
const rectPts=(u0,y0,u1,y1)=>[[u0,y0],[u1,y0],[u1,y1],[u0,y1]];
// Horseshoe-ish arch outline (local u,y) from y=yb up around a circle centred (cu,spring) of radius R.
function archPts(cu,yb,spring,R,phi=.15,n=22){
  const pts=[[cu-R*Math.cos(phi),yb]];
  for(let i=0;i<=n;i++){const a=PI+phi-i*(PI+2*phi)/n;pts.push([cu+R*Math.cos(a),spring+R*Math.sin(a)]);}
  pts.push([cu+R*Math.cos(phi),yb]);return pts;
}
// Spandrel outline: the rectangle [a,c]x[foot,ytop] minus everything under the arch (no sliver below the arch feet).
function spandrel(a,c,cu,sp,R,ytop,phi=.15,n=22){
  const yf=sp-R*Math.sin(phi),arc=archArc(cu,sp,R,phi,n).reverse();
  return [[a,yf],[a,ytop],[c,ytop],[c,yf],...arc];
}
function archArc(cu,spring,R,phi=.15,n=22){const pts=[];for(let i=0;i<=n;i++){const a=PI+phi-i*(PI+2*phi)/n;pts.push([cu+R*Math.cos(a),spring+R*Math.sin(a)]);}return pts;}
// Flat slab with holes, outward face at w=0, body at w in [-t,0].
function slab(b,f,mat,{u0,u1,y0,y1,t,holes=[]}){
  const s=new THREE.Shape(V2(rectPts(u0,y0,u1,y1)));for(const h of holes)s.holes.push(new THREE.Path(V2(h)));
  const g=new THREE.ExtrudeGeometry(s,{depth:t,bevelEnabled:false,curveSegments:1});g.translate(0,0,-t);put(b,g,f,mat);
}
// Extruded polygon (u,y) from w=w0 to w=w1.
function prism(b,f,mat,pts,w0,w1,crease){
  const g=new THREE.ExtrudeGeometry(new THREE.Shape(V2(pts)),{depth:Math.abs(w1-w0),bevelEnabled:false,curveSegments:1});g.translate(0,0,Math.min(w0,w1));put(b,g,f,mat,crease);
}
// Band following an arc (u,y points), offset outward by [r0,r1] from the arc's own circle.
function archBand(b,f,mat,cu,spring,R,bw,w0,w1,phi=.15,n=22){
  const o=[],i=[];for(let k=0;k<=n;k++){const a=PI+phi-k*(PI+2*phi)/n;o.push([cu+(R+bw)*Math.cos(a),spring+(R+bw)*Math.sin(a)]);i.push([cu+R*Math.cos(a),spring+R*Math.sin(a)]);}
  prism(b,f,mat,o.concat(i.reverse()),w0,w1,.9);
}
function box(b,f,mat,u0,y0,w0,u1,y1,w1){ // local axis-aligned box
  const g=new THREE.BoxGeometry(u1-u0,y1-y0,w1-w0);g.translate((u0+u1)/2,(y0+y1)/2,(w0+w1)/2);put(b,g,f,mat,.2);
}
const blk=(b,x,y,z,w,h,d,mat,rot=0,block=false)=>b.box(x,y,z,w,h,d,mat,rot,block);

// Quad strip along a polyline (u,y) from w0 to w1; faces turned toward the reference point `to` (u,y,w).
function strip(b,f,mat,pts,w0,w1,to,crease=.9){
  const pos=[];const A=new THREE.Vector3(),B=new THREE.Vector3(),C=new THREE.Vector3(),T=new THREE.Vector3(...to);
  const tri=(p,q,r)=>{A.set(...p);B.set(...q);C.set(...r);const n=new THREE.Vector3().crossVectors(B.clone().sub(A),C.clone().sub(A));const c=A.clone().add(B).add(C).multiplyScalar(1/3);
    if(n.dot(T.clone().sub(c))<0)pos.push(...p,...r,...q);else pos.push(...p,...q,...r);};
  for(let i=0;i<pts.length-1;i++){const [u0,y0]=pts[i],[u1,y1]=pts[i+1];
    tri([u0,y0,w0],[u1,y1,w0],[u1,y1,w1]);tri([u0,y0,w0],[u1,y1,w1],[u0,y0,w1]);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));put(b,g,f,mat,crease);
}
// Flat plate (u,y outline with optional holes) at depth w; UVs are the local (u,y) metres minus uvo (explicit, no re-projection).
function plate(b,f,mat,pts,holes,w,uvo=[0,0]){
  const s=new THREE.Shape(V2(pts));for(const h of holes||[])s.holes.push(new THREE.Path(V2(h)));
  const g=new THREE.ShapeGeometry(s,1);g.translate(0,0,w);
  const uv=g.attributes.uv,p=g.attributes.position;for(let i=0;i<p.count;i++)uv.setXY(i,p.getX(i)-uvo[0],p.getY(i)-uvo[1]);
  xf(g,f);g.computeVertexNormals();b.unique(g,mat);
}
// Lathe column: base, tapered shaft, astragal, bell capital.
function columnGeo(h=2.4){
  const pr=[[.0,0],[.17,0],[.17,.05],[.145,.07],[.145,.12],[.118,.14],[.118,.15],[.108,.2],[.098,h-.50],[.098,h-.42],[.112,h-.40],[.112,h-.37],[.094,h-.35],[.098,h-.30],[.135,h-.24],[.165,h-.16],[.18,h-.08],[.17,h-.06],[.17,h-.02],[.0,h-.02]];
  const g=new THREE.LatheGeometry(pr.map(p=>new THREE.Vector2(p[0],p[1])),14);return g;
}

// Corrugated clay-tile roof face. `pts` is a convex polygon (3 or 4 world points); the first edge pts[0]->pts[1] is the eave.
// Ribs (cover tile + pan, `rw` wide) run down-slope and are clipped by the polygon, so hips and gables stay tight.
function roofFace(b,mat,pts,{rw=.17,amp=.032,steps=8,course=.33}={}){
  const P=pts.map(p=>new THREE.Vector3(...p)),a=P[1].clone().sub(P[0]),L=a.length();a.normalize();
  const cen=P.reduce((s,p)=>s.add(p),new THREE.Vector3()).multiplyScalar(1/P.length);
  const rel=cen.clone().sub(P[0]);const s=rel.clone().sub(a.clone().multiplyScalar(rel.dot(a))).normalize();
  let nrm=new THREE.Vector3().crossVectors(a,s).normalize();if(nrm.y<0)nrm.negate();
  const q=P.map(p=>{const d=p.clone().sub(P[0]);return [d.dot(a),d.dot(s)];});
  const amin=Math.min(...q.map(v=>v[0])),amax=Math.max(...q.map(v=>v[0]));
  const range=(x)=>{let lo=1e9,hi=-1e9;for(let i=0;i<q.length;i++){const [x0,y0]=q[i],[x1,y1]=q[(i+1)%q.length];
      if((x0<=x&&x<=x1)||(x1<=x&&x<=x0)){if(Math.abs(x1-x0)<1e-6){lo=Math.min(lo,y0,y1);hi=Math.max(hi,y0,y1);}else{const t=(x-x0)/(x1-x0),y=y0+(y1-y0)*t;lo=Math.min(lo,y);hi=Math.max(hi,y);}}}
    return [lo,hi];};
  const pos=[],nor=[],uv=[];
  const vert=(x,bb,h,dh)=>{const p=P[0].clone().addScaledVector(a,x).addScaledVector(s,bb).addScaledVector(nrm,h);
    const n=nrm.clone().addScaledVector(a,-dh).normalize();return {p,n,u:x-amin,v:bb};};
  const ribs=Math.ceil((amax-amin)/rw);
  for(let r=0;r<ribs;r++){
    const col=[];
    for(let j=0;j<=steps;j++){
      const x=Math.min(amax,Math.max(amin,amin+(r+j/steps)*rw));const t=j/steps;
      const h=amp*Math.cos(2*PI*t),dh=-amp*2*PI*Math.sin(2*PI*t)/rw;
      const [lo,hi]=range(Math.min(amax-1e-4,Math.max(amin+1e-4,x)));if(lo>hi)continue;
      col.push({lo,hi,x,h,dh});
    }
    for(let j=0;j<col.length-1;j++){
      const c0=col[j],c1=col[j+1];
      const A=vert(c0.x,c0.lo,c0.h,c0.dh),B=vert(c1.x,c1.lo,c1.h,c1.dh),C=vert(c1.x,c1.hi,c1.h,c1.dh),D=vert(c0.x,c0.hi,c0.h,c0.dh);
      for(const t of [[A,B,C],[A,C,D]])for(const v of t){pos.push(v.p.x,v.p.y,v.p.z);nor.push(v.n.x,v.n.y,v.n.z);uv.push(v.u,v.v);}
    }
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  // make sure faces point up
  const ip=g.attributes.position;for(let i=0;i<ip.count;i+=3){const A=new THREE.Vector3().fromBufferAttribute(ip,i),B=new THREE.Vector3().fromBufferAttribute(ip,i+1),C=new THREE.Vector3().fromBufferAttribute(ip,i+2);
    const n=new THREE.Vector3().crossVectors(B.sub(A),C.sub(A));if(n.dot(nrm)<0){const x=ip.getX(i+1),y=ip.getY(i+1),z=ip.getZ(i+1);ip.setXYZ(i+1,ip.getX(i+2),ip.getY(i+2),ip.getZ(i+2));ip.setXYZ(i+2,x,y,z);
      const un=g.attributes.uv,nn=g.attributes.normal;const tu=un.getX(i+1),tv=un.getY(i+1);un.setXY(i+1,un.getX(i+2),un.getY(i+2));un.setXY(i+2,tu,tv);const nx=nn.getX(i+1),ny=nn.getY(i+1),nz=nn.getZ(i+1);nn.setXYZ(i+1,nn.getX(i+2),nn.getY(i+2),nn.getZ(i+2));nn.setXYZ(i+2,nx,ny,nz);}}
  b.unique(g,mat);
  return {a,s,nrm};
}
// Hipped tile roof over a (possibly rotated) rectangle: centre cx,cz; local u axis (cos th,-sin th), front normal (sin th,cos th).
// The ridge runs along the longer side. Returns the ridge ends and height.
function hipRoofR(b,mat,cx,cz,th,W,D,y,pitch=.31,opt,skip=''){
  const ux=Math.cos(th),uz=-Math.sin(th),nx=Math.sin(th),nz=Math.cos(th);
  const P=(u,w,yy=y)=>[cx+ux*u+nx*w,yy,cz+uz*u+nz*w];
  const half=Math.min(W,D)/2,h=half*Math.tan(pitch),alongU=W>=D;
  const r0=alongU?[-(W/2-half),0]:[0,-(D/2-half)],r1=alongU?[W/2-half,0]:[0,D/2-half];
  const R0=P(r0[0],r0[1],y+h),R1=P(r1[0],r1[1],y+h);
  const F=(pts)=>roofFace(b,mat,pts,opt);
  if(alongU){
    if(!skip.includes('F'))F([P(-W/2,D/2),P(W/2,D/2),R1,R0]);
    if(!skip.includes('B'))F([P(W/2,-D/2),P(-W/2,-D/2),R0,R1]);
    if(!skip.includes('R'))F([P(W/2,D/2),P(W/2,-D/2),R1]);
    if(!skip.includes('L'))F([P(-W/2,-D/2),P(-W/2,D/2),R0]);
  }else{
    if(!skip.includes('R'))F([P(W/2,D/2),P(W/2,-D/2),R0,R1]);
    if(!skip.includes('L'))F([P(-W/2,-D/2),P(-W/2,D/2),R1,R0]);
    if(!skip.includes('F'))F([P(-W/2,D/2),P(W/2,D/2),R1]);
    if(!skip.includes('B'))F([P(W/2,-D/2),P(-W/2,-D/2),R0]);
  }
  return {R0,R1,ry:y+h,h,corners:[P(-W/2,D/2),P(W/2,D/2),P(W/2,-D/2),P(-W/2,-D/2)]};
}
function hipRoof(b,mat,x0,x1,z0,z1,y,pitch=.31,opt){return hipRoofR(b,mat,(x0+x1)/2,(z0+z1)/2,0,x1-x0,z1-z0,y,pitch,opt);}
// faces of a rotated rectangle: frame origin at the face centre, u in [-len/2,len/2] seen from outside
function rectSides(cx,cz,th,W,D){
  const ux=Math.cos(th),uz=-Math.sin(th),nx=Math.sin(th),nz=Math.cos(th);
  return [{n:'F',f:F(cx+nx*D/2,cz+nz*D/2,th),len:W},{n:'B',f:F(cx-nx*D/2,cz-nz*D/2,th+PI),len:W},
          {n:'R',f:F(cx+ux*W/2,cz+uz*W/2,th+PI/2),len:D},{n:'L',f:F(cx-ux*W/2,cz-uz*W/2,th-PI/2),len:D}];
}
// world point -> local u of a face frame
const uOf=(f,x,z)=>(x-f.x)*Math.cos(f.yaw)-(z-f.z)*Math.sin(f.yaw);

// ---------------------------------------------------------------------------------------------------------
// ground and planting helpers
function groundPoly(b,mat,pts,y=0,holes){
  const sh=new THREE.Shape(pts.map(p=>new THREE.Vector2(p[0],-p[1])));
  for(const h of holes||[])sh.holes.push(new THREE.Path(h.map(p=>new THREE.Vector2(p[0],-p[1]))));
  const g=new THREE.ShapeGeometry(sh,1);g.rotateX(-PI/2);g.translate(0,y,0);b.unique(prep(g,.2),mat);
}
const groundRect=(b,mat,x0,z0,x1,z1,y=0)=>groundPoly(b,mat,[[x0,z0],[x1,z0],[x1,z1],[x0,z1]],y);
// Clipped hedge along a polyline: rounded cross-section, irregular silhouette, leaf texture in metres.
function hedgeRun(b,mat,pts,{w=.9,h=1.2,closed=false,wob=.035,seg=.55,seed=1,nav=true,round=1,base=0}={}){if(LOW)seg*=1.6;
  const rnd=random(seed*977+13),prof=[];
  const hw=w/2,k=round;
  prof.push([-hw,0],[-hw,h*.50],[-hw*(1-.06*k),h*.80],[-hw*(1-.30*k),h*.955],[-hw*(1-.62*k),h*.995],[0,h],[hw*(1-.62*k),h*.995],[hw*(1-.30*k),h*.955],[hw*(1-.06*k),h*.80],[hw,h*.50],[hw,0]);
  // resample polyline
  const P=[];const n=pts.length;
  const segs=closed?n:n-1;
  for(let i=0;i<segs;i++){const a=pts[i],c=pts[(i+1)%n],L=Math.hypot(c[0]-a[0],c[1]-a[1]),m=Math.max(1,Math.round(L/seg));for(let j=0;j<m;j++)P.push({x:a[0]+(c[0]-a[0])*j/m,z:a[1]+(c[1]-a[1])*j/m,corner:j===0});}
  if(!closed){const l=pts[n-1];P.push({x:l[0],z:l[1],corner:true});}
  const N=P.length,pos=[],uv=[],idx=[];
  const dir=(i)=>{const a=P[i],c=P[closed?(i+1)%N:Math.min(i+1,N-1)];return [c.x-a.x,c.z-a.z];};
  let ul=0;
  for(let i=0;i<N;i++){
    let d0=dir(closed?(i-1+N)%N:Math.max(i-1,0)),d1=dir(i);if(!closed&&i===N-1)d1=d0;if(!closed&&i===0)d0=d1;
    const l0=Math.hypot(...d0)||1,l1=Math.hypot(...d1)||1;let n0=[-d0[1]/l0,d0[0]/l0],n1=[-d1[1]/l1,d1[0]/l1];
    let nx=n0[0]+n1[0],nz=n0[1]+n1[1];const nl=Math.hypot(nx,nz)||1;nx/=nl;nz/=nl;const dot=Math.max(.5,nx*n0[0]+nz*n0[1]);
    const ms=1/dot;const wb=1+(rnd()-.5)*2*wob/hw,hb=1+(rnd()-.5)*2*wob/h;
    let arc=0;
    if(i>0){const a=P[i-1],c=P[i];ul+=Math.hypot(c.x-a.x,c.z-a.z);}
    for(let j=0;j<prof.length;j++){
      const [ox,oy]=prof[j];if(j>0)arc+=Math.hypot(ox-prof[j-1][0],oy-prof[j-1][1]);
      pos.push(P[i].x+nx*ox*ms*wb,base+oy*hb,P[i].z+nz*ox*ms*wb);uv.push(ul,arc);
    }
  }
  const pl=prof.length,rings=closed?N:N-1;
  for(let i=0;i<rings;i++){const a=i*pl,c=((i+1)%N)*pl;
    for(let j=0;j<pl-1;j++){idx.push(a+j,c+j,c+j+1,a+j,c+j+1,a+j+1);}}
  // orient the side surface so that it faces outward (up on the crown), then add the end caps oriented along the run
  {const A=new THREE.Vector3().fromArray(pos,(0*pl+5)*3),B2=new THREE.Vector3().fromArray(pos,(1*pl+5)*3),C2=new THREE.Vector3().fromArray(pos,(1*pl+6)*3);
   const nrm=new THREE.Vector3().crossVectors(B2.sub(A),C2.sub(A));
   if(nrm.y<0)for(let i=0;i<idx.length;i+=3){const t=idx[i+1];idx[i+1]=idx[i+2];idx[i+2]=t;}}
  const caps=[];
  const cap=(ring,out)=>{const a=ring*pl,cu=pos.length/3;pos.push(P[ring].x,base+h*.5,P[ring].z);uv.push(0,0);
    for(let j=0;j<pl;j++)caps.push([cu,a+j,a+(j+1)%pl,out]);};
  if(!closed){const q0=P[1]||P[0],q1=P[N-2]||P[N-1];
    const o0=[P[0].x-q0.x,P[0].z-q0.z],o1=[P[N-1].x-q1.x,P[N-1].z-q1.z];cap(0,o0);cap(N-1,o1);}
  for(const [c,a1,a2,out] of caps){
    const A=[pos[c*3],pos[c*3+1],pos[c*3+2]],B=[pos[a1*3],pos[a1*3+1],pos[a1*3+2]],C=[pos[a2*3],pos[a2*3+1],pos[a2*3+2]];
    const e1=[B[0]-A[0],B[1]-A[1],B[2]-A[2]],e2=[C[0]-A[0],C[1]-A[1],C[2]-A[2]];
    const nx=e1[1]*e2[2]-e1[2]*e2[1],nz=e1[0]*e2[1]-e1[1]*e2[0];
    if(nx*out[0]+nz*out[1]>=0)idx.push(c,a1,a2);else idx.push(c,a2,a1);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
  b.unique(g,mat);
  if(nav)for(let i=0;i<segs;i++){const a=pts[i],c=pts[(i+1)%n],dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz);if(L<.2)continue;b.nav.box((a[0]+c[0])/2,(a[1]+c[1])/2,L+w*.6,w,base,base+h,-Math.atan2(dz,dx));}
}
// Stone lion of the Partal: crouching on a plinth (about 1.7 m long), head toward +w.
function lionGeo(){
  const parts=[];
  const S=(rx,ry,rz,x,y,z,rotX=0,rotZ=0,seg=[16,11])=>{const g=new THREE.SphereGeometry(1,seg[0],seg[1]);g.scale(rx,ry,rz);if(rotX)g.rotateX(rotX);if(rotZ)g.rotateZ(rotZ);g.translate(x,y,z);parts.push(g);};
  const C=(r0,r1,h,x,y,z,rotX=0,rotZ=0)=>{const g=new THREE.CylinderGeometry(r1,r0,h,9);if(rotX)g.rotateX(rotX);if(rotZ)g.rotateZ(rotZ);g.translate(x,y,z);parts.push(g);};
  {const g=new THREE.BoxGeometry(.80,.22,1.78);g.translate(0,.11,0);parts.push(g);const h=new THREE.BoxGeometry(.72,.1,1.70);h.translate(0,.27,0);parts.push(h);}
  S(.27,.26,.60,0,.66,-.14);
  S(.30,.33,.30,0,.74,.36);
  S(.30,.30,.34,0,.66,-.48);
  S(.22,.27,.26,0,.99,.44,-.35);
  S(.38,.41,.17,0,1.05,.60,.15,0,[20,14]);S(.31,.34,.15,0,1.04,.69,.1,0,[18,12]);
  S(.18,.19,.21,0,1.04,.76);
  S(.12,.10,.16,0,.97,.93);
  S(.04,.04,.05,0,1.0,1.08);
  for(const sx of [-1,1]){S(.045,.05,.04,sx*.10,1.13,.82);S(.05,.06,.035,sx*.17,1.2,.67,0,sx*.4);}
  for(const sx of [-1,1]){
    C(.075,.09,.55,sx*.15,.54,.66,Math.PI/2*.9);
    S(.095,.06,.13,sx*.15,.34,.93);
    S(.12,.17,.30,sx*.26,.50,-.46);
    S(.095,.05,.17,sx*.20,.34,-.22);
  }
  {const pts=[];for(let k=0;k<=10;k++){const t=k/10;pts.push(new THREE.Vector3(Math.sin(t*2.6)*.38,.40+t*.18,-.88-t*.1));}
   const g=new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),12,.032,6,false);parts.push(g);S(.06,.07,.1,pts[10].x,pts[10].y+.02,pts[10].z-.03);}
  return parts;
}
const lionMerged=()=>mergeGeometries(lionGeo().map(g=>{const q=g.index?g.toNonIndexed():g;if(!q.attributes.uv){const n=q.attributes.position.count;q.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(n*2),2));}return q;}),false);

// ---------------------------------------------------------------------------------------------------------
let LOW=false;
export function build(b,a1,a2){
  const water=Array.isArray(a1)?a1:a2,ctx=Array.isArray(a1)?a2:a1;LOW=!!(ctx&&ctx.low);
  b.zone='partalPalace';
  palace(b);
  b.zone='partalHouses';
  casas(b);
  b.zone='partalWalls';
  northBase(b);walls(b);oratory(b);
  b.zone='partalCourt';
  court(b,water);
  patio(b);
  ruinsWest(b);
  eastGarden(b);
  terraceE(b,water);
  gardenW(b,water);
  gardenS(b,water);
  logTris(b);
}

const ARCH=[[102.85,104.62],[105.02,106.72],[107.12,109.44],[109.84,111.57],[111.97,113.71]];
const SPRING=[2.57,2.60,2.79,2.59,2.60],YIMP=2.44,YTOP=4.15,WT=4.62;
// four face frames of a rectangular building (u runs along each face seen from outside)
function sidesOf(x0,x1,z0,z1){return [
  {n:'S',f:F(0,z1,0),u0:x0,u1:x1},{n:'N',f:F(x0+x1,z0,PI),u0:x0,u1:x1},
  {n:'E',f:F(x1,z0+z1,PI/2),u0:z0,u1:z1},{n:'W',f:F(x0,0,-PI/2),u0:z0,u1:z1}];}
const toW=(f,u,y,w)=>{const c=Math.cos(f.yaw),s=Math.sin(f.yaw);return [f.x+u*c+w*s,y+(f.y||0),f.z-u*s+w*c];};
// Timber eave: beam course, carved corbels, soffit and fascia on all four sides of a (rotated) block; adds the tile roof.
function eaveR(b,cx,cz,th,W,D,yt,o,pitch=.314,{step=LOW?.5:.27,mat='partalTimber',corbel='partalCorbel',tile='partalTile',roof=true,opt,skip=''}={}){
  const cg=b.geometry('partal-corbel',()=>{
    const s=new THREE.Shape(V2([[0,-.24],[.38,-.24],[.62,-.16],[.76,-.05],[.76,.14],[0,.14]]));
    const g=new THREE.ExtrudeGeometry(s,{depth:.075,bevelEnabled:false,curveSegments:1});g.translate(0,0,-.0375);g.rotateY(-PI/2);return prep(g,.5);
  });
  for(const {n,f,len} of rectSides(cx,cz,th,W,D)){
    if(skip.includes(n))continue;
    const u0=-len/2,u1=len/2;
    box(b,f,mat,u0-.14,yt-.34,0,u1+.14,yt-.02,.14);box(b,f,'partalStuccoPlain',u0-.1,yt-.40,0,u1+.1,yt-.34,.1);
    const cnt=Math.floor(len/step);
    for(let k=0;k<=cnt;k++){const u=u0+.1+k*(len-.2)/cnt;b.add(cg,corbel,toW(f,u,yt-.02,.14),[1,1,1],f.yaw);}
    box(b,f,mat,u0-o,yt+.14,0,u1+o,yt+.18,o);
    box(b,f,mat,u0-o,yt+.14,o-.04,u1+o,yt+.42,o);
    box(b,f,mat,u0-o,yt+.12,.76,u1+o,yt+.2,o-.02);
  }
  if(roof)return hipRoofR(b,tile,cx,cz,th,W+2*o,D+2*o,yt+.42,pitch,opt,skip);
}
function eave(b,x0,x1,z0,z1,yt,o,pitch=.314,opt){return eaveR(b,(x0+x1)/2,(z0+z1)/2,0,x1-x0,z1-z0,yt,o,pitch,opt||{});}
function hipCaps(b,r,mat='partalTile',th=.075){
  b.line(r.R0,r.R1,th,mat);
  const [c0,c1,c2,c3]=r.corners;
  // each hip joins a ridge end to the nearest two eave corners
  const near=(R,cs)=>cs.map(c=>[Math.hypot(c[0]-R[0],c[2]-R[2]),c]).sort((p,q)=>p[0]-q[0]);
  const degenerate=Math.hypot(r.R0[0]-r.R1[0],r.R0[2]-r.R1[2])<.01;
  for(const R of (degenerate?[r.R0]:[r.R0,r.R1])){const ns=near(R,[c0,c1,c2,c3]);const use=degenerate?4:2;for(let k=0;k<use;k++)b.line(R,ns[k][1],th,mat);}
}

function palace(b){
  const f=F(0,-14.6,0); // south facade plane z=-14.6
  // one comb-shaped opening: arches rise from a common open base, brick strips hang between them
  const poly=[[ARCH[0][0],-.3],[ARCH[0][0],YTOP]];
  for(let i=0;i<5;i++){const [a,c]=ARCH[i];if(i>0)poly.push([a,YTOP]);poly.push([c,YTOP]);if(i<4){poly.push([c,YIMP]);poly.push([ARCH[i+1][0],YIMP]);}}
  poly.push([ARCH[4][1],-.3]);
  slab(b,f,'partalBrick',{u0:99.8,u1:114.7,y0:-.6,y1:WT+.14,t:.6,holes:[poly]});
  const LAT=[0,1,-1,2,3];
  ARCH.forEach(([a,c],i)=>{
    const cu=(a+c)/2,R=(c-a)/2,sp=SPRING[i],mid=[cu,3,-.2];
    const sp2=spandrel(a,c,cu,sp,R,YTOP);
    const yf=sp-R*Math.sin(.15);
    if(i===2){plate(b,f,'partalStucco',sp2,null,-.03);}
    else{plate(b,f,'partalLat'+LAT[i],sp2,null,-.08,[a,yf]);plate(b,f,'partalDark',sp2,null,-.35);}
    strip(b,f,'partalBrick',archArc(cu,sp,R,.15,22),-.08,-.6,mid);
    archBand(b,f,'partalStuccoPlain',cu,sp,R,.13,-.0,.06);
  });
  // alfiz frame around the central arch
  box(b,f,'partalStuccoPlain',107.04,YIMP,0,107.12,4.24,.05);box(b,f,'partalStuccoPlain',109.44,YIMP,0,109.52,4.24,.05);box(b,f,'partalStuccoPlain',107.04,YTOP,0,109.52,4.24,.05);
  // columns: lathe shaft and capital, ochre abacus
  const cg=b.geometry('partal-col',()=>columnGeo(2.3));
  for(const cx of [104.82,106.92,109.64,111.77]){
    b.add(cg,'partalColumn',[cx,0,-14.9]);b.nav.box(cx,-14.9,.4,.4,0,2.4);
    box(b,F(cx,-14.9,0),'partalCapital',-.19,2.28,-.19,.19,2.43,.19);
  }
  // west and east end piers behind the facade (solid brick)
  b.box(101.3,0,-17.1,3.0,WT+.14,5.0,'partalBrick');b.nav.box(101.3,-17.1,3.1,5.0,0,WT);
  b.box(114.2,0,-17.1,1.0,WT+.14,5.0,'partalBrick');b.nav.box(114.2,-17.1,1.1,5.0,0,WT);
  b.floor(107.25,-16.4,14.9,6.4,0,'partalMarble');
  const r=eave(b,99.8,114.7,-19.6,-14.6,WT,1.2);
  hipCaps(b,r);
  tower(b);
  hall(b);
  backWall(b);
}

// Torre de las Damas on its OSM footprint (x 101.5..108.2, z -25.5..-19.5): hall below, mirador with three-arched
// windows above, hipped tile roof with deep timber eaves.
const TW={x0:101.5,x1:108.2,z0:-25.5,z1:-19.5};
function tower(b){
  const {x0,x1,z0,z1}=TW,yb=4.4,yt=9.9,t=.6;
  const win=(cu,y0,sp,R)=>archPts(cu,y0,sp,R,.12,16);
  const sd=sidesOf(x0,x1,z0,z1);
  for(const {n,f,u0,u1} of sd){
    let a0=u0,a1=u1;if(n==='E'||n==='W'){a0=u0+t;a1=u1-t;}
    const cs=(u0+u1)/2;
    const cnt=n==='W'?2:3,pitch=.83;
    const holes=[];for(let i=0;i<cnt;i++)holes.push(win(cs+(i-(cnt-1)/2)*pitch,7.55,8.75,.27));
    const extra=[];if(n==='S'){extra.push({k:'win',u:cs-2.35,y:6.3,w:.44,h:.74},{k:'slit',u:cs+2.35,y:6.4,w:.4,h:.55});}
    if(n==='E')extra.push({k:'win',u:cs+1.2,y:5.9,w:.4,h:.6});
    for(const e of extra)holes.push(...openingsOf([e]));
    slab(b,f,'partalBrick',{u0:a0,u1:a1,y0:yb,y1:yt+.14,t,holes});fit(b,f,extra);
    // tapial plinth band and stucco string course where the brick tower leaves the roof of the portico
    box(b,f,'partalStuccoPlain',a0-.04,yb+.55,0,a1+.04,yb+.65,.06);box(b,f,'partalStuccoPlain',a0-.03,yt-.55,0,a1+.03,yt-.47,.05);
    // carved stucco panel behind the window group, with a stucco frame and dark room behind
    const half=cnt===3?1.45:1.0;
    const fr=(a,y0,c,y1)=>box(b,f,'partalStuccoPlain',a,y0,0,c,y1,.045);
    fr(cs-half,7.35,cs-half+.07,9.2);fr(cs+half-.07,7.35,cs+half,9.2);fr(cs-half,9.13,cs+half,9.2);fr(cs-half,7.35,cs+half,7.42);
    for(let i=0;i<cnt;i++){const cu=cs+(i-(cnt-1)/2)*pitch;
      plate(b,f,'partalDark',win(cu,7.55,8.75,.27),null,-.35);
      archBand(b,f,'partalStuccoPlain',cu,8.75,.27,.045,0,.04,.12,16);
      box(b,f,'partalStone',cu-.34,7.5,0,cu+.34,7.55,.1);}
  }
  b.box((x0+x1)/2,yb-.2,(z0+z1)/2,x1-x0-.2,.3,z1-z0-.2,'partalTimber');   // mirador floor
  b.box((x0+x1)/2,yt-.1,(z0+z1)/2,x1-x0-.2,.15,z1-z0-.2,'partalCedarInt');          // ceiling
  const r=eave(b,x0,x1,z0,z1,yt,.95,.36);
  hipCaps(b,r);
  // little finial
  b.cylinder((x0+x1)/2,r.ry-.05,(z0+z1)/2,.1,.5,'partalColumn',.04,8);b.sphere((x0+x1)/2,r.ry+.5,(z0+z1)/2,.11,.11,.11,'gold');
}

// Hall of the tower (ground floor): marble floor, tile dado, stucco walls, cedar ceiling, window to the valley.
function hall(b){
  const {x0,x1,z0,z1}=TW,tw=.95;
  // foundations and walls (tapial outside)
  b.box((x0+x1)/2,-50,(z0+z1)/2,x1-x0,49.6,z1-z0,'partalTapial',0,true);
  for(const {n,f,u0,u1} of sidesOf(x0,x1,z0,z1)){
    if(n==='S')continue;
    const holes=n==='N'?[archPts((u0+u1)/2,1.25,2.7,.55,.12,14)]:n==='W'?[rectPts((u0+u1)/2-.3,1.4,(u0+u1)/2+.3,2.4)]:[];
    slab(b,f,'partalTapial',{u0,u1,y0:-.4,y1:4.4,t:tw,holes});
    if(n==='N'){const cu=(u0+u1)/2;archBand(b,f,'partalStuccoPlain',cu,2.7,.55,.1,0,.06,.12,14);plate(b,f,'partalDark',archPts(cu,1.25,2.7,.55,.12,14),null,-.5);
      for(const dx of [-.4,-.13,.13,.4])b.line(toW(f,cu+dx,1.3,.03),toW(f,cu+dx,2.55,.03),.016,'partalIron');b.line(toW(f,cu-.55,1.6,.03),toW(f,cu+.55,1.6,.03),.016,'partalIron');}
  }
  b.nav.box((x0+x1)/2,(z0+z1)/2,x1-x0,z1-z0,-60,4.4);
  // clear the hall volume for walking (nav boxes are additive, so register the walls individually instead)
  b.nav.blocks.pop();
  const ix0=x0+tw,ix1=x1-tw,iz0=z0+tw,iz1=z1-.6-.9+.9; // inner room: x 102.45..107.25, z -24.55..-19.5
  b.nav.box((x0+ix0)/2,(z0+z1)/2,tw,z1-z0,-60,4.4);b.nav.box((ix1+x1)/2,(z0+z1)/2,tw,z1-z0,-60,4.4);b.nav.box((x0+x1)/2,(z0+iz0)/2,x1-x0,tw,-60,4.4);
  b.floor((ix0+ix1)/2,(iz0+z1)/2,ix1-ix0,z1-iz0,0,'partalMarble');
  // lining
  const w=ix1-ix0,d=z1-iz0,cx=(ix0+ix1)/2,cz=(iz0+z1)/2,L=.04;
  const wallsL=[[cx,iz0+L/2,w,L,0],[ix0+L/2,cz,L,d,1],[ix1-L/2,cz,L,d,1]];
  for(const [x,z,ww,dd] of wallsL){
    b.box(x,0,z,ww,1.15,dd,'partalTileInt');b.box(x,1.15,z,ww,.3,dd,'partalFriezeInt');b.box(x,1.45,z,ww,2.65,dd,'partalStuccoInt');b.box(x,4.1,z,ww,.2,dd,'partalFriezeInt');
  }
  b.box(cx,4.2,cz,w,.14,d,'partalCedarInt');
}

function backWall(b){
  const f=F(0,-18.0,0),t=1.6,DOOR=105.2;
  const win=(cu)=>[-.9,0,.9].map(d=>archPts(cu+d,1.35,2.2,.3,.12,14));
  const door=archPts(DOOR,-.3,2.35,.65,.1,18);
  slab(b,f,'partalStuccoInt',{u0:102.85,u1:113.71,y0:-.6,y1:WT+.14,t,holes:[...win(111.0),door]});
  // lower band: glazed-tile dado (the room's own Nasrid tile material) broken by door and windows; carved stucco panel above the dado
  const seg=(a,c)=>{if(c-a>.02){box(b,f,'partalTileInt',a,0,0,c,1.2,.05);box(b,f,'partalFriezeInt',a,1.2,0,c,1.5,.05);}};
  seg(102.85,DOOR-.65-.02);seg(DOOR+.65+.02,109.4-.0);seg(109.4,110.1-.0);seg(111.9+.02,113.71);
  box(b,f,'partalTileInt',110.1,0,0,111.9,1.25,.05);
  // central arch: the carved stucco panel and its arched frame, timber lintel
  plate(b,f,'partalStucco',rectPts(107.15,1.55,109.4,3.95),null,.055);
  box(b,f,'partalTimber',107.1,3.95,0,109.45,4.15,.12);box(b,f,'partalTimber',107.1,1.5,0,109.45,1.6,.1);
  box(b,f,'partalStuccoPlain',107.1,1.6,0,107.2,3.95,.08);box(b,f,'partalStuccoPlain',109.35,1.6,0,109.45,3.95,.08);
  // door leaves
  plate(b,f,'partalShutter',archPts(DOOR,0,2.35,.62,.1,18),null,-.2,[DOOR-.62,0]);archBand(b,f,'partalStuccoPlain',DOOR,2.35,.65,.14,0,.06,.1,18);
  // iron grilles of the north windows (outer plane of the wall)
  const z=-19.55;
  for(const cu of [110.1,111.0,111.9]){
    for(const x of [cu-.25,cu-.08,cu+.08,cu+.25])b.line([x,1.38,z],[x,2.3,z],.014,'partalIron');
    b.line([cu-.3,1.9,z],[cu+.3,1.9,z],.014,'partalIron');
  }
  // gallery ceiling: cedar planking between painted beams
  b.box(108.3,4.27,-16.8,10.9,.12,3.6,'partalCedarInt');
  for(let x=103.2;x<113.8;x+=.6)b.box(x,4.15,-16.8,.12,.14,3.6,'partalTimber');
  // nav: the wall with its doorway, the gallery floor is already walkable
  b.nav.box((102.85+DOOR-.65)/2,-18.8,DOOR-.65-102.85,1.6,0,WT);b.nav.box((DOOR+.65+113.71)/2,-18.8,113.71-DOOR-.65,1.6,0,WT);
}

// ---------------------------------------------------------------------------------------------------------
// houses, wall, oratory
// Openings on a face: {k:'win'|'arch'|'door'|'slit', u, y, w, h}; returns the holes for the wall slab and builds the fittings.
function openingsOf(list){
  const out=[];
  for(const o of list){
    if(o.k==='arch')out.push(archPts(o.u,o.y,o.y+o.h-o.w/2,o.w/2,.14,14));
    else if(o.k==='twin'||o.k==='lat3'){const n=o.k==='twin'?2:3,pw=o.k==='twin'?(o.w-.28)/2:.42,pitch=o.k==='twin'?pw+.28:.62;
      for(let i=0;i<n;i++){const cu=o.u+(i-(n-1)/2)*pitch;out.push(archPts(cu,o.y,o.y+o.h-pw/2,pw/2,.14,12));}}
    else out.push(rectPts(o.u-o.w/2,o.y,o.u+o.w/2,o.y+o.h));
  }
  return out;
}
function fit(b,f,list){
  for(const o of list){
    const {k,u,y,w,h}=o,a=u-w/2,c=u+w/2;
    if(k==='arch'){
      const R=w/2,sp=y+h-R;
      plate(b,f,'partalShutter',archPts(u,y,sp,R,.14,14),null,-.16,[a,y]);
      archBand(b,f,'partalStuccoPlain',u,sp,R,.09,0,.05,.14,14);
      // little wooden balcony in front of the sill
      box(b,f,'partalTimber',a-.14,y-.06,0,c+.14,y,.38);
      box(b,f,'partalTimber',a-.14,y+.80,.30,c+.14,y+.86,.38);
      const n=Math.max(3,Math.round((w+.28)/.13));for(let i=0;i<=n;i++){const x=a-.12+i*(w+.24)/n;box(b,f,'partalTimber',x-.018,y,.32,x+.018,y+.82,.356);}
    }else if(k==='win'){
      plate(b,f,'partalShutter',rectPts(a,y,c,y+h),null,-.14,[a,y]);
      box(b,f,'partalTimber',a-.12,y+h,0,c+.12,y+h+.12,.07);
      box(b,f,'partalStone',a-.07,y-.07,0,c+.07,y,.13);
    }else if(k==='door'){
      plate(b,f,'partalShutter',rectPts(a,y,c,y+h),null,-.14,[a,y]);
      box(b,f,'partalTimber',a-.14,y+h,0,c+.14,y+h+.15,.08);
      box(b,f,'partalStone',a-.12,y-.12,0,c+.12,y,.28);
    }else if(k==='twin'||k==='lat3'){
      const n=k==='twin'?2:3,pw=k==='twin'?(w-.28)/2:.42,pitch=k==='twin'?pw+.28:.62;
      // carved stucco panel around the group, lattice or dark interior behind the arches
      const ph=k==='twin'?h+.5:h+.34,pw2=w+(k==='twin'?.9:.5),y0=y-(k==='twin'?.22:.17);
      const holes=[];for(let i=0;i<n;i++){const cu=u+(i-(n-1)/2)*pitch;holes.push(archPts(cu,y,y+h-pw/2,pw/2,.14,12));}
      plate(b,f,'partalStucco',rectPts(u-pw2/2,y0,u+pw2/2,y0+ph),holes,.03);
      box(b,f,'partalStuccoPlain',u-pw2/2-.05,y0-.05,0,u+pw2/2+.05,y0,.08);box(b,f,'partalStuccoPlain',u-pw2/2-.05,y0+ph,0,u+pw2/2+.05,y0+ph+.06,.08);
      for(let i=0;i<n;i++){const cu=u+(i-(n-1)/2)*pitch,sp=y+h-pw/2;
        if(k==='lat3')plate(b,f,'partalLat3',archPts(cu,y,sp,pw/2,.14,12),null,-.1,[cu-pw/2,y]);
        plate(b,f,'partalDark',archPts(cu,y,sp,pw/2,.14,12),null,-.3);
        archBand(b,f,'partalStuccoPlain',cu,sp,pw/2,.05,0,.05,.14,12);}
      if(k==='twin')box(b,f,'partalColumn',u-.035,y,-.12,u+.035,y+h-.2,-.05);
    }else if(k==='slit'){
      plate(b,f,'partalLat3',rectPts(a,y,c,y+h),null,-.12,[a,y]);plate(b,f,'partalDark',rectPts(a,y,c,y+h),null,-.3);
      box(b,f,'partalTimber',a-.05,y+h,0,c+.05,y+h+.08,.06);
    }
  }
}
// One brick/rendered house face with its openings; y0..y1, t thick.
function houseFace(b,f,mat,u0,u1,y0,y1,t,list){
  slab(b,f,mat,{u0,u1,y0,y1,t,holes:openingsOf(list)});fit(b,f,list);
}
// A two-storey block with four faces, hip roof and eave. spec: {F:[openings], B:[..], R:[..], L:[..]} in local u (centre of each face = 0).
function house(b,cx,cz,th,W,D,yb,yt,spec,{mat='partalBrickOld',o=.8,pitch=.33,t=.55,skip=''}={}){
  for(const {n,f,len} of rectSides(cx,cz,th,W,D)){
    const list=spec[n]||[];
    houseFace(b,f,mat,-len/2,len/2,yb,yt+.14,t,list);
  }
  b.box(cx,yb,cz,W-2*t+.02,yt-yb,D-2*t+.02,'partalDark',th,false);
  const r=eaveR(b,cx,cz,th,W,D,yt,o,pitch,{skip});hipCaps(b,r);return r;
}

// Tapial wall segment between a and c (centred on the line), from y0 to y1; plain stone coping.
function wallSeg(b,a,c,y1,{y0=-50,t=1.4,mat='partalTapial',cap=true,ext=.35}={}){
  const dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz),rot=-Math.atan2(dz,dx),mx=(a[0]+c[0])/2,mz=(a[1]+c[1])/2;
  b.box(mx,y0,mz,L+ext*2,y1-y0,t,mat,rot,true);
  if(cap){b.box(mx,y1,mz,L+ext*2+.1,.08,t+.26,'partalBrick',rot);b.box(mx,y1+.08,mz,L+ext*2+.06,.1,t+.12,'partalTile',rot);b.box(mx,y1+.18,mz,L+ext*2,.1,t-.22,'partalTile',rot);b.box(mx,y1+.28,mz,L+ext*2,.06,.22,'partalTile',rot);}
}
// Brick-faced tower base and the high tapial base under the north front of the palace and houses.
function northBase(b){
  b.box(90.1,-50,-18.45,19.5,49.7,2.5,'partalTapial',0,true);                 // under the casas, ledge face z=-19.7
  b.box(107.0,-50,-18.7,15.4,49.7,2.1,'partalTapial',0,true);                  // under the palace block (z -19.75..-17.65)
  // putlog holes on the tapial faces
  const hole=b.geometry('putlog',()=>prep(new THREE.BoxGeometry(.11,.11,.1),.1));
  for(const y of [-6,-3.2,-.4])for(let x=102.1;x<108;x+=1.35)b.add(hole,'partalDark',[x,y,-25.51]);
  for(const y of [-8,-4.6,-1.4])for(let x=81;x<113;x+=1.5)b.add(hole,'partalDark',[x+((y*7)%.4),y,-19.72]);
}
// The north enclosure wall west of the casas, and the garden wall east of the portico running past the Oratorio.
function walls(b){
  const west=[[60.9,-27.2],[73.5,-18.8],[77.3,-21.1],[83.8,-20.9],[83.9,-19.6]];
  for(let i=0;i<west.length-1;i++)wallSeg(b,west[i],west[i+1],5.7,{t:1.5});
  const east=[[114.7,-14.8],[120.1,-12.0],[132.1,-1.6],[143.2,4.6],[153.7,10.5]];
  const tops=[3.1,3.3,4.6,6.6];
  for(let i=0;i<east.length-1;i++)wallSeg(b,east[i],east[i+1],tops[i],{t:1.4});
}
// Oratorio del Partal (carved window front) and the taller Torre del Mihrab on the wall, facing the garden.
function oratory(b){
  const A=[120.1,-12.0],B=[132.1,-1.6],L=Math.hypot(B[0]-A[0],B[1]-A[1]),d=[(B[0]-A[0])/L,(B[1]-A[1])/L],n=[-d[1],d[0]]; // n points into the garden
  const th=Math.atan2(n[0],n[1]);
  const mk=(s0,s1,D,yt,spec,o)=>{const W=s1-s0,sc=(s0+s1)/2,cx=A[0]+d[0]*sc+n[0]*(D/2-.7),cz=A[1]+d[1]*sc+n[1]*(D/2-.7);
    const r=house(b,cx,cz,th,W,D,-.35,yt,spec,o);b.nav.box(cx,cz,W,D,-1,yt,th);return r;};
  // main block with the great carved window; tower block with the door and shutters
  mk(3.1,9.2,3.9,5.0,{F:[{k:'twin',u:-.15,y:1.45,w:1.45,h:1.55},{k:'lat3',u:-.1,y:3.45,w:1.9,h:.8},{k:'slit',u:2.35,y:3.45,w:.5,h:.8}],B:[],R:[],L:[{k:'twin',u:0,y:1.6,w:1.3,h:1.5},{k:'lat3',u:0,y:3.5,w:1.4,h:.8}]},{o:.9,pitch:.31});
  mk(9.2,12.6,3.8,5.9,{F:[{k:'door',u:.55,y:.3,w:1.0,h:2.35},{k:'win',u:-.55,y:3.5,w:.8,h:1.2},{k:'win',u:.7,y:3.5,w:1.0,h:1.2}],B:[],R:[{k:'win',u:0,y:3.4,w:.7,h:1.0}],L:[]},{o:.85,pitch:.32});
}

// --- the casas nazaríes west of the portico: an L-shaped two-storey house on the sand patio
function casas(b){
  // arm 1 (E-W) between the western pier and x=80.4; faces: F(south) onto the patio, B(north) to the ravine
  const y1=4.35;
  const c1x=(80.4+99.8)/2,c1z=(-19.3-14.4)/2;
  const spec1={
    F:[ // front, u relative to centre x=c1x
      {k:'door',u:88.3-c1x,y:0,w:.95,h:2.1},{k:'win',u:91.6-c1x,y:.9,w:.5,h:.7},{k:'door',u:94.6-c1x,y:0,w:1.3,h:2.2},{k:'slit',u:97.6-c1x,y:1.2,w:.5,h:.55},
      {k:'win',u:87.2-c1x,y:2.85,w:.6,h:.85},{k:'arch',u:90.0-c1x,y:2.55,w:.9,h:1.55},{k:'win',u:92.7-c1x,y:2.75,w:1.35,h:1.1},{k:'arch',u:95.3-c1x,y:2.55,w:.9,h:1.55},{k:'win',u:98.1-c1x,y:2.85,w:.6,h:.85}],
    B:[{k:'win',u:-(83-c1x),y:2.85,w:.7,h:.9},{k:'arch',u:-(87.5-c1x),y:2.45,w:1.0,h:1.7},{k:'win',u:-(92-c1x),y:2.85,w:.7,h:.9},{k:'arch',u:-(96.5-c1x),y:2.45,w:1.0,h:1.7},{k:'slit',u:-(90-c1x),y:1.1,w:.5,h:.6}],
    L:[{k:'win',u:0,y:2.85,w:.8,h:.9}],R:[]};
  house(b,c1x,c1z,0,99.8-80.4,19.3-14.4,-.35,y1,spec1,{o:.85});
  // arm 2 (N-S) along the east side of the patio: x 80.6..85.7, z -14.4..-2.3
  const c2x=83.15,c2z=-8.35;
  const spec2={
    R:[ // east face (u runs northward on the 'R' side)
      {k:'door',u:-( -11.7-c2z),y:0,w:.95,h:2.1},{k:'door',u:-( -6.9-c2z),y:0,w:.95,h:2.1},{k:'slit',u:-(-9.3-c2z),y:1.3,w:.5,h:.55},
      {k:'win',u:-(-12.4-c2z),y:2.65,w:.95,h:1.15},{k:'win',u:-(-9.9-c2z),y:2.65,w:.95,h:1.15},{k:'win',u:-(-7.4-c2z),y:2.65,w:.95,h:1.15},{k:'arch',u:-(-4.3-c2z),y:2.5,w:.9,h:1.6}],
    F:[{k:'win',u:0,y:2.7,w:.8,h:1.0},{k:'door',u:1.3,y:0,w:.95,h:2.0}],
    L:[{k:'win',u:-3,y:2.7,w:.8,h:1.0},{k:'win',u:2,y:2.7,w:.8,h:1.0}],B:[]};
  // rotate frames: for th=0 the 'R' face runs with u toward -z (north) which matches the list above
  house(b,c2x,c2z,0,85.7-80.6,14.4-2.3,-.35,4.1,spec2,{o:.8,pitch:.34,skip:'B'});
  b.nav.box(c1x,c1z,99.8-80.4,4.9,-1,y1);b.nav.box(c2x,c2z,5.1,12.1,-1,4.1);
}

const OSM={hedges:[[[136.2,35.4],[136.0,35.1],[135.4,34.7],[135.0,34.5],[134.3,34.4],[133.9,34.5],[133.4,34.7],[132.9,35.1],[132.6,35.4],[132.4,35.9],[132.4,36.5],[132.4,37.0],[132.6,37.5],[132.8,37.8],[133.0,37.9],[133.4,38.2],[133.9,38.5],[134.3,38.5],[135.0,38.5],[135.5,38.2],[135.9,37.9],[136.2,37.5],[136.4,37.0],[136.5,36.5],[136.4,35.9]],[[89.0,54.1],[89.0,61.3],[100.2,61.3],[100.3,54.2]],[[100.3,52.8],[100.3,45.6],[89.1,45.5],[89.1,52.7]],[[87.9,34.2],[88.0,42.5],[97.6,42.4],[97.5,34.2]],[[67.9,37.9],[67.8,42.4],[82.7,42.4],[82.7,38.0]],[[87.6,32.5],[106.4,32.4],[106.3,23.3],[87.5,23.4]],[[66.8,32.8],[82.4,32.8],[82.3,23.7],[66.8,23.8]],[[68.0,57.2],[72.8,53.3],[77.8,56.8],[73.4,60.5]],[[68.0,47.4],[72.8,43.5],[77.8,47.0],[73.3,50.6]],[[109.5,28.6],[109.7,31.7],[118.0,31.3],[117.9,28.3]],[[126.2,27.9],[126.0,24.4],[117.7,24.8],[117.9,28.3]],[[117.9,28.3],[117.7,24.8],[109.4,25.1],[109.5,28.6]],[[134.1,27.5],[133.9,24.0],[126.0,24.4],[126.2,27.9]],[[117.9,28.3],[118.0,31.3],[126.3,30.9],[126.2,27.9]],[[142.7,27.1],[142.6,23.6],[133.9,24.0],[134.1,27.5]],[[134.1,27.5],[134.2,30.6],[142.9,30.2],[142.7,27.1]],[[137.5,41.4],[134.9,38.6],[134.9,41.3]],[[128.2,41.0],[125.8,38.1],[125.8,40.8]],[[143.3,41.7],[143.3,38.2],[139.6,41.5]],[[134.8,32.1],[134.9,34.3],[137.7,32.0]],[[139.9,31.9],[143.1,35.1],[143.1,31.8]],[[144.9,35.0],[149.0,31.6],[144.9,31.8]],[[156.6,36.6],[152.1,31.5],[156.7,31.3]],[[144.6,41.7],[144.6,38.2],[148.2,41.9]],[[156.6,42.4],[151.8,42.1],[156.7,37.5]],[[133.6,34.4],[131.1,32.2],[133.6,32.2]],[[133.5,41.2],[133.5,38.6],[130.7,41.1]],[[146.8,35.3],[146.8,38.0],[148.7,40.0],[151.4,40.0],[153.3,38.0],[153.3,35.3],[151.4,33.4],[148.7,33.4]],[[136.9,35.6],[136.9,37.6],[138.3,39.1],[140.4,39.1],[141.8,37.7],[141.8,35.6],[140.4,34.1],[138.3,34.1]],[[127.1,35.2],[127.0,37.3],[128.5,38.8],[130.6,38.8],[132.0,37.3],[132.0,35.3],[130.6,33.8],[128.5,33.8]],[[125.9,32.4],[125.9,34.4],[128.1,32.4]],[[122.4,32.6],[124.5,34.5],[124.5,32.5]],[[124.7,40.7],[124.8,38.1],[121.6,40.5]],[[118.4,40.4],[123.5,37.2],[123.5,35.1],[121.0,32.6],[118.3,32.7]],[[126.2,27.9],[126.3,30.9],[134.2,30.6],[134.1,27.5]]],water:[[[131.5,57.8],[130.1,83.4],[136.2,83.7],[137.6,58.1]],[[82.1,49.9],[82.1,54.8],[85.7,54.9],[85.7,49.9]],[[109.3,52.4],[109.4,57.4],[112.0,57.3],[112.0,52.3]],[[108.5,67.8],[108.5,73.6],[110.4,73.6],[110.4,67.8]],[[109.0,34.1],[109.1,36.8],[113.4,36.7],[113.6,41.4],[116.4,41.3],[116.1,33.8]],[[99.6,34.0],[99.7,42.3],[102.4,42.3],[102.3,36.8],[106.8,36.7],[106.8,33.9]]],foot:[[[94.3,79.9],[120.7,80.2],[120.9,62.6],[121.1,44.1]],[[85.2,43.8],[96.5,44.0],[101.6,44.0],[107.4,44.1],[117.0,44.2],[121.1,44.1]],[[85.2,48.4],[87.7,48.4],[87.7,53.4],[87.6,56.2],[84.0,56.1],[80.2,56.1],[80.3,51.8],[80.3,48.3],[85.2,48.4]],[[107.6,23.1],[107.5,32.6],[107.4,44.1]],[[85.2,31.4],[85.2,43.8]],[[157.6,43.5],[150.1,43.1],[143.9,42.8],[138.7,42.6],[134.2,42.4],[129.1,42.1],[125.1,41.9],[117.6,41.5]],[[63.8,69.9],[84.3,71.5],[94.4,72.2],[94.3,79.9]],[[117.0,44.2],[116.8,62.6]],[[101.5,53.6],[101.4,62.4],[116.8,62.6],[120.9,62.6]],[[64.0,61.8],[61.5,60.5]],[[84.1,60.5],[84.1,60.0],[84.0,56.1]],[[84.3,71.5],[84.2,68.4],[84.2,63.9]],[[87.7,53.4],[101.5,53.6],[101.6,45.4],[101.6,44.0]],[[85.2,48.4],[85.2,43.8]],[[63.8,69.9],[64.0,61.8],[64.2,51.9],[80.3,51.8]],[[134.8,52.4],[134.4,57.2],[155.7,59.4]],[[130.9,42.7],[130.8,44.2],[130.1,52.0]],[[130.1,52.0],[134.8,52.4],[139.0,52.8],[139.9,43.5]],[[121.1,44.1],[123.1,44.1],[130.8,44.2]],[[124.0,35.0],[121.0,31.9]],[[134.3,35.3],[134.3,34.4],[134.2,31.2]],[[135.7,37.7],[135.9,37.9],[138.7,41.2],[142.5,38.0]],[[156.1,37.3],[157.7,37.4]],[[138.7,41.2],[138.7,42.6]],[[129.2,40.6],[129.1,42.1]],[[129.5,32.0],[129.5,31.5]],[[150.5,30.4],[150.6,31.1]],[[142.5,35.6],[139.3,32.1],[136.0,35.1],[135.7,35.4]],[[134.2,42.4],[134.3,38.5],[134.3,37.6]],[[133.1,35.3],[133.0,37.6],[134.3,37.6],[135.7,37.7],[135.7,35.4],[134.3,35.3],[133.1,35.3]],[[125.2,37.4],[125.1,41.9]],[[125.2,31.7],[125.3,35.0]],[[126.5,35.0],[129.5,32.0],[132.9,35.1],[133.1,35.3]],[[117.6,41.5],[124.0,37.4]],[[133.0,37.6],[132.8,37.8],[129.2,40.6],[126.5,37.4]],[[124.0,35.0],[124.0,37.4],[125.2,37.4],[126.5,37.4],[126.5,35.0],[125.3,35.0],[124.0,35.0]],[[143.9,38.0],[143.9,42.8]],[[144.0,30.7],[144.1,35.6]],[[145.2,35.6],[150.6,31.1],[156.1,37.3]],[[142.5,35.6],[142.5,38.0],[143.9,38.0],[145.1,38.0],[145.2,35.6],[144.1,35.6],[142.5,35.6]],[[139.3,31.0],[139.3,32.1]],[[117.6,41.5],[117.4,32.1]],[[157.8,30.0],[157.7,37.4],[157.6,43.5]],[[145.1,38.0],[150.1,43.1],[156.1,37.3]],[[100.0,33.0],[107.5,32.6],[117.4,32.1],[121.0,31.9],[125.2,31.7],[129.5,31.5],[134.2,31.2],[139.3,31.0],[144.0,30.7],[150.5,30.4],[157.8,30.0]],[[81.3,68.4],[84.2,68.4],[86.7,68.4]],[[86.7,60.0],[84.1,60.0],[81.3,60.0]]],lawn:[[[96.0,64.5],[65.6,64.2],[66.0,23.3],[160.0,21.1],[158.4,44.0],[123.2,42.0],[122.3,54.4],[145.1,56.2],[143.4,73.5],[157.4,74.8],[160.3,77.1],[160.6,83.0],[159.5,87.6],[136.8,86.0],[136.6,89.2],[118.9,88.4],[119.0,85.3],[95.9,84.3],[95.9,82.7],[96.1,78.2]],[[124.1,58.8],[122.6,86.6],[142.7,87.7],[144.2,60.1],[138.2,59.8],[136.9,84.8],[129.2,84.4],[130.5,59.1]],[[68.0,53.3],[68.0,57.2],[68.0,60.5],[73.4,60.5],[77.8,60.5],[77.8,56.8],[77.8,53.3],[72.8,53.3]],[[68.0,43.5],[68.0,47.4],[68.0,50.6],[73.3,50.6],[77.8,50.6],[77.8,47.0],[77.8,43.5],[72.8,43.5]]]};

const T1=1.35;
const inPoly=(x,z,p)=>{let c=false;for(let i=0,j=p.length-1;i<p.length;j=i++){const a=p[i],q=p[j];if((a[1]>z)!==(q[1]>z)&&x<(q[0]-a[0])*(z-a[1])/(q[1]-a[1])+a[0])c=!c;}return c;};
const bbox=p=>{let x0=1e9,z0=1e9,x1=-1e9,z1=-1e9;for(const [x,z] of p){x0=Math.min(x0,x);x1=Math.max(x1,x);z0=Math.min(z0,z);z1=Math.max(z1,z);}return [x0,z0,x1,z1];};
const cen=p=>[p.reduce((s,q)=>s+q[0],0)/p.length,p.reduce((s,q)=>s+q[1],0)/p.length];
const edgeDist=(x,z,p)=>{let m=1e9;for(let i=0;i<p.length;i++){const a=p[i],c=p[(i+1)%p.length],dx=c[0]-a[0],dz=c[1]-a[1],L2=dx*dx+dz*dz||1,t=Math.max(0,Math.min(1,((x-a[0])*dx+(z-a[1])*dz)/L2));m=Math.min(m,Math.hypot(x-a[0]-dx*t,z-a[1]-dz*t));}return m;};
function curbPoly(b,poly,{y=0,w=.18,h=.16,mat='partalBrick',closed=true}={}){
  const n=poly.length;
  for(let i=0;i<(closed?n:n-1);i++){const a=poly[i],c=poly[(i+1)%n],dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz);if(L<.05)continue;
    b.box((a[0]+c[0])/2,y,(a[1]+c[1])/2,L+w*.7,h,w,mat,-Math.atan2(dz,dx));}
}
// vertical wall strip around a polygon (faces toward its centre)
function vwall(b,mat,poly,y0,y1){
  const [cx,cz]=cen(poly),pos=[];const A=new THREE.Vector3(),B=new THREE.Vector3(),C=new THREE.Vector3(),T=new THREE.Vector3();
  const tri=(p,q,r)=>{A.set(...p);B.set(...q);C.set(...r);const n=new THREE.Vector3().crossVectors(B.clone().sub(A),C.clone().sub(A));T.set(cx-(p[0]+q[0]+r[0])/3,0,cz-(p[2]+q[2]+r[2])/3);if(n.dot(T)<0)pos.push(...p,...r,...q);else pos.push(...p,...q,...r);};
  for(let i=0;i<poly.length;i++){const a=poly[i],c=poly[(i+1)%poly.length];tri([a[0],y0,a[1]],[c[0],y0,c[1]],[c[0],y1,c[1]]);tri([a[0],y0,a[1]],[c[0],y1,c[1]],[a[0],y1,a[1]]);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));b.unique(prep(g,.5),mat);
}
// rose bush + flower cluster geometry
const roseGeo=()=>{const parts=[];for(const [x,y,z,r,sy,d] of [[0,.30,0,.36,.8,1],[.22,.2,.12,.2,.8,0],[-.2,.22,-.1,.19,.8,0]]){const g=new THREE.IcosahedronGeometry(r,d);g.scale(1,sy,1);g.translate(x,y,z);parts.push(g.toNonIndexed());}return mergeGeometries(parts,false);};
const flowerGeo=()=>{const parts=[];const r=random(55);for(let i=0;i<13;i++){const a=r()*6.28,d=Math.sqrt(r())*.34,y=.32+Math.sqrt(1-(d/.38)**2)*.2+r()*.05;const g=new THREE.OctahedronGeometry(.036+r()*.012,0);g.translate(Math.cos(a)*d,y,Math.sin(a)*d);parts.push(g);}return mergeGeometries(parts,false);};
function roses(b,poly,y,seed,{sp=.85,inset=.42,cols=['partalRoseR','partalRoseP','partalRoseW','partalRoseY'],mono=-1}={}){
  if(LOW)sp*=1.3;const bb=bbox(poly),r=random(seed*131+7),g1=b.geometry('rose',roseGeo),g2=b.geometry('roseFl',flowerGeo);
  for(let x=bb[0]+inset;x<bb[2];x+=sp)for(let z=bb[1]+inset;z<bb[3];z+=sp){
    const px=x+(r()-.5)*.22,pz=z+(r()-.5)*.22;if(!inPoly(px,pz,poly)||edgeDist(px,pz,poly)<inset)continue;
    const sc=.8+r()*.45,rot=r()*6.28;b.add(g1,'partalRoseLeaf',[px,y,pz],[sc,sc*(.9+r()*.3),sc],rot);
    b.add(g2,mono>=0?cols[mono]:cols[Math.floor(r()*cols.length)],[px,y,pz],[sc,sc,sc],rot);
  }
}
function retWall(b,a,c,y1,{t=.55,side=1,ivy=true,mat='partalBrickOld',y0=0}={}){
  const dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz),rot=-Math.atan2(dz,dx),mx=(a[0]+c[0])/2,mz=(a[1]+c[1])/2;
  b.box(mx,y0,mz,L,y1-y0,t,mat,rot,true);
  b.box(mx,y1,mz,L+.1,.1,t+.16,'partalStone',rot);
  if(ivy){const nx=-dz/L*side,nz=dx/L*side;b.box(mx+nx*(t/2+.045),y0+.35,mz+nz*(t/2+.045),L-.4,y1-y0-.2,.09,'partalIvy',rot);}
}
// straight flight along z (ascending from zLow to zHigh) or along x
function stairsZ(b,x,zLow,zHigh,w,yLow,yHigh,mat='partalStone',channel=false){
  const n=Math.max(2,Math.round((yHigh-yLow)/.15)),run=(zHigh-zLow)/n,sgn=Math.sign(zHigh-zLow);
  for(let k=0;k<n;k++){const zc=zLow+(k+.5)*run,top=yLow+(yHigh-yLow)*(k+1)/n;b.box(x,0,zc,w,top,Math.abs(run)+.04,mat);b.box(x,top-.045,zc-sgn*.03,w+.08,.045,Math.abs(run)+.06,'partalStone');if(channel){for(const sx of [-1,1])b.box(x+sx*.17,top,zc,.04,.05,Math.abs(run)+.05,'partalStone');b.box(x,top-.012,zc,.3,.03,Math.abs(run)+.05,'partalChannel');if(k>0)b.box(x,top-(yHigh-yLow)/n+.005,zc-sgn*(Math.abs(run)/2-.0),.3,(yHigh-yLow)/n,.03,'partalChannel');}}
  const z0=Math.min(zLow,zHigh),z1=Math.max(zLow,zHigh);
  if(zHigh>zLow)b.nav.ramp(x,(z0+z1)/2,w,z1-z0,yLow,yHigh);else b.nav.ramp(x,(z0+z1)/2,w,z1-z0,yHigh,yLow);
}
function pondShape(b,water,poly,rects,y,{coping=.28,raise=0}={}){
  const wy=y+raise*.55;
  for(const [x0,z0,x1,z1] of rects)water.push({x:(x0+x1)/2,z:(z0+z1)/2,w:x1-x0,d:z1-z0,y:wy-.06,reflect:false});
  if(raise>0){
    groundPoly(b,'partalPoolBed',poly,y+.02);
    vwall(b,'partalStone',poly,y,y+raise);
    curbPoly(b,poly,{y:y+raise-.02,w:coping,h:.1,mat:'partalStone'});
  }else{
    groundPoly(b,'partalPoolBed',poly,y-.45);
    vwall(b,'partalStone',poly,y-.45,y);
    curbPoly(b,poly,{y:y,w:coping,h:.12,mat:'partalStone'});
  }
  for(const [x0,z0,x1,z1] of rects)b.nav.box((x0+x1)/2,(z0+z1)/2,x1-x0,z1-z0,y-.5,y+raise+.5);
}

// --- raised upper terrace (+1.35 m): pebble parterres, two L-ponds, rose octagons, reached by the water stair
function terraceE(b,water){
  b.zone='partalGardenE';
  const X0=94.5,X1=160.6,Z0=23.1,Z1=44.3;
  groundPoly(b,'partalPebble',[[X0,Z0],[X1,Z0],[X1,Z1],[X0,Z1]],T1+.012,[OSM.water[4],OSM.water[5]]);
  b.nav.floor((X0+X1)/2,(Z0+Z1)/2,X1-X0,Z1-Z0,T1);
  // retaining walls: ivy on the outer faces, openings for the stairs
  retWall(b,[X0,Z0],[105.7,Z0],T1,{side:-1});retWall(b,[109.5,Z0],[X1,Z0],T1,{side:-1});
  retWall(b,[X0,Z1],[105.7,Z1],T1,{side:1});retWall(b,[109.5,Z1],[X1,Z1],T1,{side:1});
  retWall(b,[X0,Z0],[X0,Z1],T1,{side:-1});retWall(b,[X1,Z0],[X1,Z1],T1,{side:1});
  // the water stair (north) with cheek walls and the south stair
  stairsZ(b,107.6,20.0,23.1,3.4,0,T1,'partalStone',true);
  for(const sx of [-1,1]){b.box(107.6+sx*1.85,0,21.55,.4,T1+.25,3.2,'partalBrickOld',0,true);}
  stairsZ(b,107.4,46.0,Z1-.25,3.4,0,T1);
  for(const sx of [-1,1]){b.box(107.4+sx*1.85,0,45.1,.4,T1+.25,1.9,'partalBrickOld',0,true);}
  // ponds (L-shaped) and the cross channel with its round basin
  pondShape(b,water,OSM.water[5],[[99.6,34.0,106.8,36.8],[99.7,36.7,102.4,42.3]],T1);
  pondShape(b,water,OSM.water[4],[[109.0,33.9,116.2,36.8],[113.5,36.7,116.3,41.4]],T1);
  water.push({x:107.5,z:33.7,w:.26,d:20.2,y:T1-.05,reflect:false});
  curbPoly(b,[[107.35,23.4],[107.35,43.9]],{y:T1,w:.07,h:.05,mat:'partalBrick',closed:false});curbPoly(b,[[107.65,23.4],[107.65,43.9]],{y:T1,w:.07,h:.05,mat:'partalBrick',closed:false});
  b.cylinder(107.5,T1,38.5,1.15,.14,'partalStone',1.15,28);b.cylinder(107.5,T1+.02,38.5,.95,.14,'water',.95,28);b.cylinder(107.5,T1,38.5,.12,.5,'partalStone',.1,10);
  // brick bands along the main paths
  for(const pts of [OSM.foot[44],OSM.foot[3]])curbPoly(b,pts.map(p=>[p[0],p[1]]),{y:T1,w:.14,h:.03,mat:'partalBrick',closed:false});
  // parterres: lawn rectangles, rose triangles and octagons, each in a low clipped hedge ring
  const H=OSM.hedges,rings=[];
  const add=(poly,kind,seed)=>rings.push({poly,kind,seed});
  add([[95.3,23.8],[106.3,23.7],[106.2,32.3],[95.3,32.4]],'lawn',1);
  for(const i of [9,10,11,12,13,14,15,34])add(H[i],'lawn',i);
  add(H[33],'lawn',33);
  for(const i of [16,17,18,19,20,21,22,23,24,25,26,30,31,32])add(H[i],'rose',i);
  for(const i of [27,28,29])add(H[i],'octa',i);
  add(H[0],'round',0);
  for(const {poly,kind,seed} of rings){
    const yy=T1+.012;
    if(kind==='lawn'){groundPoly(b,'partalGrass',poly,yy+.012);}
    else if(kind==='round'){groundPoly(b,'partalGravel',poly,yy+.012);}
    else{groundPoly(b,'partalSoil',poly,yy+.012);roses(b,poly,yy+.012,seed,{sp:kind==='octa'?.78:.7,inset:.36,mono:kind==='octa'?seed%4:-1});}
    hedgeRun(b,'partalHedge',poly,{w:.5,h:kind==='lawn'?.55:.62,closed:true,seed:seed+10,seg:.7,base:T1+.012,round:.9,nav:true});
  }
  // central fountain of the octagon garden (round basin) at the old OSM circle
  const [cx,cz]=cen(H[0]);b.cylinder(cx,T1,cz,1.35,.18,'partalStone',1.35,28);b.cylinder(cx,T1+.04,cz,1.15,.16,'water',1.15,28);b.cylinder(cx,T1,cz,.16,.9,'partalStone',.1,10);
  // orange trees and cypresses of the terrace
  for(const [x,z] of [[97.2,27.5],[97.2,40.0],[113.0,28.5],[118.5,43.2],[128.5,43.2],[139.0,43.4],[149.5,43.3],[158.8,26.5],[158.8,41.0],[112.2,31.0]])plant(x,T1,z,ORANGE,3.7);
  for(const [x,z,h] of [[104.0,22.2,9.5],[111.0,22.2,9.5],[104.0,45.8,8.8],[111.0,45.8,8.8],[159.0,33,10.5]])plant(x,T1<0?0:(z>44?0:T1),z,CYPRESS,h);
}

// --- ground-level gardens west of the lane (box-hedge parterres, diamonds, pond plaza, little garden house)
function gardenW(b,water){
  b.zone='partalGardenW';
  const H=OSM.hedges,L=OSM.lawn;
  // rectangular beds
  groundPoly(b,'partalGrass',H[6],.016);hedgeRun(b,'partalHedge',H[6],{w:.55,h:.7,closed:true,seed:61,seg:.8,round:.9});
  // narrow bed pairs west of the N-S lane (the east halves lie on the raised terrace); the x=92.8 route and the pergola alley (z=40) stay open
  for(const [poly,seed,kind] of [[[[87.9,34.2],[91.3,34.2],[91.3,38.2],[87.9,38.2]],65,'rose'],[[[87.6,23.5],[91.3,23.5],[91.3,32.4],[87.6,32.4]],66,'lawn']]){
    groundPoly(b,kind==='rose'?'partalSoil':'partalGrass',poly,.016);if(kind==='rose')roses(b,poly,.016,seed,{sp:.8,inset:.34});
    hedgeRun(b,'partalHedge',poly,{w:.5,h:.65,closed:true,seed,seg:.8,round:.9});}
  // diamonds inside their lawns
  for(const [lawn,ring,seed] of [[L[3],H[8],63],[L[2],H[7],64]]){
    groundPoly(b,'partalGrass',lawn,.016);curbPoly(b,lawn,{y:0,w:.14,h:.07});
    groundPoly(b,'partalSoil',ring,.022);roses(b,ring,.022,seed,{sp:.8,mono:seed%4});
    hedgeRun(b,'partalHedge',ring,{w:.5,h:.62,closed:true,seed:seed+5,seg:.7,round:.9});
  }
  // plaza with the little pond
  groundPoly(b,'partalPaving',[[80.2,48.4],[87.7,48.4],[87.7,56.1],[80.2,56.1]],.022,[OSM.water[1]]);
  pondShape(b,water,OSM.water[1],[[82.1,49.9,85.7,54.9]],0,{raise:.3});
  for(const [x,z] of [[81.0,49.3],[87.0,49.3],[81.0,55.3],[87.0,55.3]])plant(x,0,z,ORANGE,3.2);
  // small garden house on its terrace, entered by steps from the north and south
  b.box(84.0,0,64.2,6.0,.9,8.6,'partalBrickOld',0,true);b.box(84.0,.9,64.2,6.2,.08,8.8,'partalStone');groundRect(b,'partalPaving',81.0,60.0,87.0,68.4,.98);
  stairsZ(b,84.0,57.9,60.0,3.0,0,.98);stairsZ(b,84.0,70.5,68.4,3.0,0,.98);
  b.nav.floor(84.0,64.2,6.0,8.4,.98);
  const hr=house(b,84.2,62.3,0,4.0,3.4,.98,3.9,{F:[{k:'door',u:0,y:1.08,w:1.0,h:2.1},{k:'win',u:-1.3,y:2.1,w:.6,h:.8}],B:[{k:'win',u:0,y:2.2,w:.6,h:.7}],R:[{k:'arch',u:0,y:2.0,w:.7,h:1.2}],L:[{k:'win',u:0,y:2.2,w:.6,h:.7}]},{o:.6,pitch:.35,t:.4});
  for(const [x,z,h] of [[88.6,24.0,7.5],[88.6,34.0,7.5],[63.6,33,8],[63.6,60,8.5]])plant(x,0,z,CYPRESS,h);
  for(const z of [29,38,47,56,65])plant(89.9,0,z,ORANGE,3.4);
  // pergola over the path along the Kings route (z=40): stuccoed pillars, timber beams and rafters, vine canopy
  groundRect(b,'partalGravel',66.2,38.9,92.0,41.1,.03);
  for(let x=68;x<=90;x+=3){for(const z of [38.75,41.25]){b.box(x,0,z,.3,2.75,.3,'partalStuccoPlain',0,false);b.nav.box(x,z,.3,.3,0,2.75);b.box(x,2.75,z,.42,.1,.42,'partalStone');}
    b.box(x,2.85,40,.16,.2,3.4,'partalTimber');}
  for(const z of [38.75,41.25])b.box(79,2.85,z,22.5,.2,.14,'partalTimber');
  for(let x=67.5;x<90.5;x+=.62)b.box(x,3.05,40,.07,.1,3.9,'partalTimber');
  b.box(79,3.16,40,22.8,.1,3.1,'partalIvy');
  for(let x=68;x<=90;x+=3)for(const z of [38.75,41.25])b.box(x,.6,z+(z<40?-.2:.2),.5,1.9,.18,'partalIvy');
}

// --- middle gardens (lawns, ponds) and the long pond with the Yusuf III remains
function gardenS(b,water){
  b.zone='partalGardenS';
  const H=OSM.hedges,L=OSM.lawn;
  // clipped beds beside the lane
  for(const [poly,seed] of [[[[95.2,45.8],[100.3,45.8],[100.2,52.2],[95.2,52.2]],71],[[[95.2,54.8],[100.3,54.8],[100.2,61.2],[95.2,61.2]],72]]){
    groundPoly(b,'partalGrass',poly,.016);hedgeRun(b,'partalHedge',poly,{w:.55,h:.75,closed:true,seed,seg:.8,round:.9});}
  for(const [poly,seed] of [[[[89.1,45.8],[91.4,45.8],[91.4,52.2],[89.1,52.2]],75],[[[89.1,54.8],[91.4,54.8],[91.4,61.2],[89.1,61.2]],76]]){groundPoly(b,'partalSoil',poly,.016);roses(b,poly,.016,seed,{sp:.8,inset:.3});hedgeRun(b,'partalHedge',poly,{w:.45,h:.6,closed:true,seed,seg:.8,round:.9});}
  // lawn compartments with ponds
  const m1=[[104.6,47.6],[114.8,47.6],[114.8,60.2],[104.6,60.2]],m2=[[104.8,64.2],[113.2,64.2],[113.2,75.6],[104.8,75.6]];
  for(const [poly,seed] of [[m1,73],[m2,74]]){groundPoly(b,'partalGrass',poly,.016);curbPoly(b,poly,{y:0,w:.18,h:.09});hedgeRun(b,'partalHedge',poly.map(p=>[p[0]+(p[0]<110?.5:-.5),p[1]+(p[1]<55?.5:p[1]<62?-.5:-.5)]),{w:.5,h:.6,closed:true,seed,seg:.8,round:.9});}
  pondShape(b,water,OSM.water[2],[[109.3,52.4,112.0,57.4]],0,{raise:.3});pondShape(b,water,OSM.water[3],[[108.5,67.8,110.4,73.6]],0,{raise:.3});
  for(const [x,z] of [[106.4,47.5],[113.0,47.5],[106.4,58.4],[113.0,58.4],[107.0,66.2],[111.2,66.2],[107.0,74.0],[111.2,74.0]])plant(x,0,z,ORANGE,3.3);
  // east lawn with the long pond
  const lawn=L[1];groundPoly(b,'partalGrass',lawn,.016);
  const longp=OSM.water[0];pondShape(b,water,longp,[[130.4,57.9,137.4,83.6]],0,{coping:.34,raise:.34});
  curbPoly(b,lawn,{y:0,w:.2,h:.08,mat:'partalBrick'});
  for(let z=61;z<84;z+=5.6){plant(127.0,0,z,CYPRESS,6.5+(z%3));plant(141.0,0,z,CYPRESS,6.5+((z+1)%3));}
  for(const z of [62,70,78])for(const x of [126.4,142.2])plant(x,0,z+2.2,ORANGE,3.3);
  yusuf(b);
}
function yusuf(b){
  // Palace of Yusuf III: low brick and rubble foundations around a court with a rectangular pool
  const poly=[[143.4,73.5],[145.1,56.2],[146.2,44.5],[165.1,46.2],[164.3,54.5],[154.7,53.6],[154.0,61.1],[158.6,61.5],[157.4,74.8]];
  const r=random(777);
  for(let i=0;i<poly.length;i++){const a=poly[i],c=poly[(i+1)%poly.length];const dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz),n=Math.max(1,Math.round(L/5));
    for(let k=0;k<n;k++){const t0=k/n,t1=(k+1)/n;if(r()<.15)continue;const h=.55+r()*.7,ax=a[0]+dx*t0,az=a[1]+dz*t0,bx=a[0]+dx*t1,bz=a[1]+dz*t1;
      const rot=-Math.atan2(dz,dx);b.box((ax+bx)/2,0,(az+bz)/2,L/n+.1,h,.7,k%2?'partalTapial':'partalBrickOld',rot,h>.9);}}
  for(const [x0,z0,x1,z1,h] of [[147,52.6,154.4,53.2,.9],[150,60,153.9,60.6,.7],[146.4,66.5,156.5,67.1,.8],[150.4,44.8,150.9,52.8,1.0],[155.2,53.4,155.8,61,.7],[150.6,61,151.2,73.8,.8]])
    b.box((x0+x1)/2,0,(z0+z1)/2,x1-x0,h,z1-z0,'partalBrickOld');
  b.box(157.5,0,49.8,6.6,.12,3.4,'partalDark');b.floor(157.5,49.8,8,5,0,'partalPaving');
  for(const [x,z] of [[148.4,57],[158.2,68.5]])plant(x,0,z,CYPRESS,6);
  plant(152,0,57,ORANGE,3.2);
}

// --- patio of the casas nazaríes, west of the pool: gravel walk on the x=92.8 axis, brick-edged parterres, pots, orange trees
function patio(b){
  b.zone='partalPatio';
  groundRect(b,'partalGravel',91.35,-14.3,94.25,20.5,.03);
  for(const x of [91.35,94.25])b.box(x,0,3.1,.2,.06,34.8,'partalBrick');
  groundRect(b,'partalPaving',85.7,-14.3,98.4,-12.6,.025);
  for(const [poly,seed,mono] of [[[[86.4,-10.5],[90.3,-10.5],[90.3,-1.5],[86.4,-1.5]],81,0],[[[86.4,0.6],[90.3,0.6],[90.3,9.0],[86.4,9.0]],82,2],[[[86.4,11.2],[90.3,11.2],[90.3,19.4],[86.4,19.4]],83,1],
      [[[95.4,-10.5],[97.2,-10.5],[97.2,-1.5],[95.4,-1.5]],84,3],[[[95.4,0.6],[97.2,0.6],[97.2,9.0],[95.4,9.0]],85,-1]]){
    groundPoly(b,'partalSoil',poly,.034);roses(b,poly,.034,seed,{sp:LOW?1.0:.74,inset:.3,mono});
    hedgeRun(b,'partalHedge',poly,{w:.45,h:.6,closed:true,seed:seed+3,seg:.75,round:.9,base:.0});}
  const pot=b.geometry('partal-pot',()=>mergeGeometries([(()=>{const g=new THREE.CylinderGeometry(.24,.16,.42,12);g.translate(0,.21,0);return g.toNonIndexed();})(),(()=>{const g=new THREE.CylinderGeometry(.27,.25,.07,12);g.translate(0,.44,0);return g.toNonIndexed();})()],false));
  const shrub=b.geometry('rose',roseGeo);
  for(const x of [87.2,89.4,92.0,95.2,97.6]){b.add(pot,'partalTilePot',[x,0,-14.1]);b.add(shrub,'partalHedge',[x,.4,-14.1],[1.1,1.3,1.1],x*7);}
  for(const [x,z] of [[88.3,-12],[96.4,-12],[88.3,20.2],[97.0,20.2]])plant(x,0,z,ORANGE,3.4);
  for(const [x,z,h] of [[85.6,-10,7.5],[85.6,17,7.5],[98.0,-12.5,8.5]])plant(x,0,z,CYPRESS,h);
  for(const [x0,x1,h] of [[82.2,86.0,3.8],[89.3,92.6,3.2],[95.2,98.9,3.6]]){b.box((x0+x1)/2,.3,-14.43,x1-x0,h,.07,'partalIvy');}
  for(const z of [-4,6]){b.box(97.3,.2,z,.5,.08,1.6,'partalStone');b.box(97.3,0,z-.6,.4,.28,.15,'partalStone');b.box(97.3,0,z+.6,.4,.28,.15,'partalStone');}
}

// --- the garden east of the pool, between the oratory wall and the Paseo de las Torres, and the walk itself
function pathRibbon(b,mat,pts,w,y){
  const pos=[],uv=[],idx=[];let u=0;
  for(let i=0;i<pts.length;i++){
    const a=pts[Math.max(0,i-1)],c=pts[Math.min(pts.length-1,i+1)],dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz)||1,nx=-dz/L,nz=dx/L;
    if(i>0)u+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);
    pos.push(pts[i][0]-nx*w/2,y,pts[i][1]-nz*w/2,pts[i][0]+nx*w/2,y,pts[i][1]+nz*w/2);uv.push(u,0,u,w);
    if(i>0){const k=i*2;idx.push(k-2,k,k-1,k-1,k,k+1);}}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
  if(g.attributes.normal.getY(0)<0){const a=g.index.array;for(let i=0;i<a.length;i+=3){const t=a[i+1];a[i+1]=a[i+2];a[i+2]=t;}g.computeVertexNormals();}
  b.unique(g,mat);
}
// Polyline offset by d to the right of travel (x,z plane, mitred).
function offsetLine(pts,d){
  const out=[];
  for(let i=0;i<pts.length;i++){
    const a=pts[Math.max(0,i-1)],c=pts[i],e=pts[Math.min(pts.length-1,i+1)];
    const d0=[c[0]-a[0],c[1]-a[1]],d1=[e[0]-c[0],e[1]-c[1]];
    const n0=Math.hypot(...d0)||1,n1=Math.hypot(...d1)||1;
    const p0=[-d0[1]/n0,d0[0]/n0],p1=[-d1[1]/n1,d1[0]/n1];
    let nx=p0[0]+p1[0],nz=p0[1]+p1[1];const nl=Math.hypot(nx,nz)||1;nx/=nl;nz/=nl;
    const k=1/Math.max(.6,nx*p0[0]+nz*p0[1]);
    out.push([c[0]+nx*d*k,c[1]+nz*d*k]);
  }
  return out;
}
function eastGarden(b){
  b.zone='partalGardenEast';
  const walk=[[115.9,-10.3],[118.9,-7.5],[129.7,3.4],[141.5,8.7],[153.4,13.0],[160.6,19.8]];
  pathRibbon(b,'partalPaving',walk,2.0,.03);
  for(const o of [1.1,-1.1])curbPoly(b,offsetLine(walk,o),{y:0,w:.14,h:.05,mat:'partalBrick',closed:false});
  // lawn south of the walk, bounded by a clipped hedge 1.9 m from the walk axis, with two openings
  const hl=offsetLine(walk,1.9).slice(1,5);   // 4 points along the walk
  const lawn=[...hl,[154.4,16.2],[154.4,13.9],[119.1,14.1],[118.7,-3.6]];
  groundPoly(b,'partalGrass',lawn,.02);
  curbPoly(b,[[154.4,16.2],[154.4,13.9],[119.1,14.1],[118.7,-3.6],hl[0]],{y:0,w:.18,h:.07,mat:'partalBrick',closed:false});
  const cut=(pts,t0,t1)=>{ // sub-polyline between arc positions t0..t1
    const out=[];let acc=0;for(let i=0;i<pts.length-1;i++){const L=Math.hypot(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1]);
      const lo=Math.max(t0,acc),hi=Math.min(t1,acc+L);if(hi>lo){const A=(lo-acc)/L,B=(hi-acc)/L;if(!out.length)out.push([pts[i][0]+(pts[i+1][0]-pts[i][0])*A,pts[i][1]+(pts[i+1][1]-pts[i][1])*A]);out.push([pts[i][0]+(pts[i+1][0]-pts[i][0])*B,pts[i][1]+(pts[i+1][1]-pts[i][1])*B]);}acc+=L;}
    return out;};
  const HL=hl.reduce((s,p,i)=>i?s+Math.hypot(p[0]-hl[i-1][0],p[1]-hl[i-1][1]):0,0);
  const g1=HL*.30,g2=HL*.68;
  [[0,g1-1.4,95],[g1+1.4,g2-1.4,96],[g2+1.4,HL,97]].forEach(([a,c,sd])=>{const q=cut(hl,a,c);if(q.length>1)hedgeRun(b,'partalHedge',q,{w:.55,h:.8,seed:sd,seg:.7,round:.9});});
  const isl=[[124,6.5],[129.5,9.2],[128.0,12.0],[122.0,11.4]];
  groundPoly(b,'partalSoil',isl,.034);roses(b,isl,.034,92,{sp:.8,inset:.3});hedgeRun(b,'partalHedge',isl,{w:.45,h:.55,closed:true,seed:92,seg:.7,round:.9});
  for(const [x,z] of [[121.5,12.0],[133.5,12.4],[140.0,12.3],[146.5,12.6],[126.5,3.6],[135.0,9.4]])plant(x,0,z,ORANGE,3.5);
  for(let k=0;k<7;k++){const t=k/6,x=127+t*28,z=4.2+t*12.6;plant(x+1.1,0,z,CYPRESS,8+((k*5)%3));}
}

// --- open ground west of the casas: the footway from the Nasrid palaces, grass patches and the excavated foundations
function ruinsWest(b){
  b.zone='partalRuins';
  groundPoly(b,'partalGravel',[[59.6,-23.4],[61.1,-26.4],[73.5,-18.8],[77.3,-20.9],[80.4,-20.9],[80.4,-14.4],[85.7,-14.4],[85.7,20.5],[59.6,20.5]],.004);
  const walk=[[59.6,-3.2],[65.8,0.0],[65.8,3.0],[75.6,2.6],[85.3,2.4]];
  pathRibbon(b,'partalPaving',walk,2.2,.03);
  for(const o of [-1.2,1.2])curbPoly(b,walk.map((p,k)=>[p[0],p[1]+o]),{y:0,w:.14,h:.05,mat:'partalBrick',closed:false});
  pathRibbon(b,'partalPaving',[[85.2,2.4],[85.2,20.5]],2.2,.03);
  groundPoly(b,'partalGrass',[[66.8,4.4],[84.0,4.4],[84.0,19.8],[66.8,19.8]],.02);curbPoly(b,[[66.8,4.4],[84.0,4.4],[84.0,19.8],[66.8,19.8]],{y:0,w:.16,h:.06,mat:'partalBrick'});
  groundPoly(b,'partalGrass',[[67.5,-5.2],[79.0,-5.2],[79.0,-.9],[67.5,-.9]],.02);
  const O=[56.3,-10],U=[.846,.533],V=[.531,-.848],L=15,W=14.5,r=random(4242);
  const P=(u,v)=>[O[0]+U[0]*u+V[0]*v,O[1]+U[1]*u+V[1]*v];
  const wall=(u0,v0,u1,v1,h)=>{const a=P(u0,v0),c=P(u1,v1),dx=c[0]-a[0],dz=c[1]-a[1],len=Math.hypot(dx,dz);if(len<.3)return;
    const mid=[(a[0]+c[0])/2,(a[1]+c[1])/2],rot=-Math.atan2(dz,dx);b.box(mid[0],0,mid[1],len,h,.55,r()<.5?'partalTapial':'partalBrickOld',rot,true);if(h>.5)b.box(mid[0],h,mid[1],len+.04,.07,.62,'partalStone',rot);};
  const seg=(u0,v0,u1,v1,gaps=[])=>{
    const horiz=Math.abs(u1-u0)>Math.abs(v1-v0),a0=horiz?u0:v0,a1=horiz?u1:v1;let cur=a0;
    for(const [g0,g1] of [...gaps,[a1,a1]]){const h=.35+r()*.75;if(g0>cur)horiz?wall(cur,v0,g0,v1,h):wall(u0,cur,u1,g0,h);cur=g1;}};
  seg(0,0,L,0,[[3.4,4.6],[9.5,10.7]]);seg(0,W,L,W,[[5.5,6.7]]);seg(0,0,0,W,[[4,5.2],[10,11]]);seg(L,0,L,W,[[6,7.2]]);
  seg(5.2,0,5.2,W,[[2,3.1],[8.5,9.6]]);seg(10,0,10,W,[[4.5,5.6],[11.4,12.5]]);seg(0,7.3,5.2,7.3,[]);seg(10,6.4,L,6.4,[[12.5,13.6]]);
  for(const [u,v] of [[2.5,3],[7.6,10],[12.5,3.3],[12.4,10.4],[2.5,10.5]]){const q=P(u,v);b.box(q[0],0,q[1],3.4,.03,3.4,'partalSand');}
  b.floor((P(0,0)[0]+P(L,W)[0])/2,(P(0,0)[1]+P(L,W)[1])/2,18,18,0,'partalGravel',0);
  for(const [x,z,h] of [[72.5,-16.5,8.5],[63.2,-3,7],[79.5,9,8],[67.2,12.5,6.5]])plant(x,0,z,CYPRESS,h);
  for(const [x,z] of [[73.5,7],[70.5,16.5],[81,15]])plant(x,0,z,ORANGE,3.4);
}

function logTris(b){
  const by={};const add=(k,n)=>{by[k]=(by[k]||0)+n;};
  for(const [k,{list}] of b.merged){if(!k.startsWith('partal'))continue;const z=k.split('|')[0],m=k.split('|')[1];for(const g of list)add(z+'/'+m,(g.index?g.index.count:g.attributes.position.count)/3);}
  for(const [k,v] of b.instances){if(!k.startsWith('partal'))continue;const g=v.g;add(k.split('|')[0]+'/'+v.mat,((g.index?g.index.count:g.attributes.position.count)/3)*v.transforms.length);}
  let t=0;for(const n of Object.values(by))t+=n;
  const top=Object.entries(by).sort((a,c)=>c[1]-a[1]).slice(0,14).map(([k,n])=>k+':'+Math.round(n/1000)+'k').join(' ');
  if(typeof location!=='undefined'&&/partalTris/.test(location.search))console.log('partal tris',Math.round(t),top);
}
function court(b,water){
  // base ground (gravel) inside the enclosure, clipped by the wall line
  groundPoly(b,'partalGravel',[[85.7,-14.3],[114.7,-14.3],[114.7,-14.8],[120.1,-12.0],[132.1,-1.6],[153.7,10.5],[158.7,13.3],[160.6,13.9],[160.6,90],[66,90],[66,20.5],[85.7,20.5]],.004,[[[99.45,-13.65],[114.15,-13.65],[114.15,14.05],[99.45,14.05]]]);
  groundRect(b,'partalSand',85.7,-12.6,97.45,20.5,.012);
  // the pool
  water.push({x:106.8,z:.2,w:13.8,d:26.8,y:-.015,reflect:true});
  b.nav.box(106.8,.2,13.8,26.8,-1,.5);
  b.box(106.8,-.05,.2,13.8,.03,26.8,'partalPoolBed');
  for(const [x,z,w,d] of [[106.8,-13.36,14.44,.32],[106.8,13.76,14.44,.32],[99.74,.2,.32,27.12],[113.86,.2,.32,27.12]])b.box(x,0,z,w,.075,d,'partalStone');
  // paving: margins of the pool, apron of the portico, south terrace
  groundRect(b,'partalPaving',98.4,-13.52,99.58,13.92,.02);
  groundRect(b,'partalPaving',114.02,-13.52,115.35,13.92,.02);
  groundRect(b,'partalMarble',99.8,-14.6,114.7,-13.52,.025);
  groundRect(b,'partalPaving',98.4,13.92,115.35,17.7,.02);
  // hedges around the pool: clipped box/myrtle, about 1.3 m high
  hedgeRun(b,'partalHedge',[[97.95,-10],[97.95,14.1]],{w:.9,h:.95,seed:1});
  hedgeRun(b,'partalHedge',[[115.8,-8.5],[115.8,13.5]],{w:.9,h:.95,seed:2});
  hedgeRun(b,'partalHedge',[[98.0,18.4],[105.9,18.4]],{w:.9,h:.95,seed:3});
  hedgeRun(b,'partalHedge',[[109.3,18.4],[115.8,18.4]],{w:.9,h:.95,seed:4});
  // lions
  const lg=b.geometry('partal-lion',lionMerged);
  for(const [x,z] of [[104.6,15.2],[110.6,15.2]]){b.add(lg,'partalLion',[x,0,z],[1,1,1],PI);b.nav.box(x,z,.8,1.7,0,1.3);}
}
