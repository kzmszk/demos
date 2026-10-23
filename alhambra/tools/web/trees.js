import * as THREE from 'three';

// Procedural trees by species (ids shared with tools/gen/trees.py): leaf-card crowns with
// volumetric normals, bark branches, three levels of detail. Near trees (< LOD_FAR) are re-binned
// into instanced templates as the camera moves; every tree also has a camera-facing impostor
// rendered from its own template, which the vertex shader hides when the tree is near.
export const SPECIES=['cypress','elm','plane','holm','olive','pine','stonepine','orange','palm','shrub','poplar'];
export const CYPRESS=0,ELM=1,PLANE=2,HOLM=3,OLIVE=4,PINE=5,STONEPINE=6,ORANGE=7,PALM=8,SHRUB=9,POPLAR=10;
const LOD0=75,LOD_FAR=270,VARIANTS=2;

// Trees added by the hand-built gardens (Generalife, Partal, grounds): {x,y,z,species,h}.
export const gardenTrees=[];
export function plant(x,y,z,species,h){gardenTrees.push({x,y,z,s:species,h});}

function rng(seed){return ()=>((seed=Math.imul(seed,1664525)+1013904223|0)>>>0)/4294967296;}

// ------------------------------------------------------------------ textures
const LEAF={
  cypress:{kind:'scale',c:[[36,58,40],[48,72,46],[28,46,34],[58,82,52]]},
  elm:{kind:'broad',c:[[62,90,42],[76,104,48],[50,74,36],[90,114,52],[58,84,40],[70,98,44],[132,130,58]],leaf:[5,9],n:1700},
  plane:{kind:'broad',c:[[86,110,50],[100,120,54],[72,96,44],[118,126,58],[92,114,50],[150,138,62],[168,134,56]],leaf:[7,12],n:1100},
  poplar:{kind:'broad',c:[[150,146,60],[176,160,66],[118,128,56],[196,170,72],[100,118,52]],leaf:[5,8],n:1500},
  holm:{kind:'broad',c:[[52,66,44],[64,80,50],[44,56,40],[78,90,60]],leaf:[3,6],n:2600},
  olive:{kind:'broad',c:[[110,122,96],[132,142,112],[92,106,84],[150,156,128]],leaf:[2,7],n:2200,narrow:true},
  pine:{kind:'needle',c:[[52,76,46],[66,92,54],[42,62,40],[84,104,62]]},
  stonepine:{kind:'needle',c:[[48,70,42],[62,86,50],[40,58,36],[74,96,56]]},
  orange:{kind:'broad',c:[[36,62,36],[50,82,44],[30,52,32],[64,96,52]],leaf:[4,8],n:2000,fruit:'#e48a22'},
  shrub:{kind:'broad',c:[[86,96,58],[104,110,64],[70,80,50],[122,118,72]],leaf:[3,6],n:2200},
};
function leafTexture(name){
  const p=LEAF[name],S=512,c=document.createElement('canvas');c.width=c.height=S;const g=c.getContext('2d'),r=rng(name.length*977+13);
  const col=k=>{const q=p.c[k%p.c.length];const v=.82+r()*.3;return `rgb(${q[0]*v|0},${q[1]*v|0},${q[2]*v|0})`;};
  const inBlob=(x,y)=>{const dx=(x-S/2)/(S*.46),dy=(y-S/2)/(S*.46);const a=Math.atan2(dy,dx),rad=.78+.18*Math.sin(a*5+1.3)+.08*Math.sin(a*11);return dx*dx+dy*dy<rad*rad;};
  if(p.kind==='broad'){
    for(let i=0;i<p.n*2.6;i++){const x=r()*S,y=r()*S;if(!inBlob(x,y))continue;
      const s=(p.leaf[0]+r()*(p.leaf[1]-p.leaf[0]))*1.6;g.save();g.translate(x,y);g.rotate(r()*7);g.fillStyle=col(Math.floor(r()*9));
      g.beginPath();g.ellipse(0,0,s,s*(p.narrow?.28:.55),0,0,7);g.fill();g.fillStyle='rgba(255,255,230,.06)';g.beginPath();g.ellipse(-s*.2,-s*.12,s*.5,s*.2,0,0,7);g.fill();g.restore();}
    if(p.fruit)for(let i=0;i<140;i++){const x=r()*S,y=r()*S;if(!inBlob(x,y))continue;g.fillStyle=p.fruit;g.beginPath();g.arc(x,y,5+r()*3,0,7);g.fill();}
    // twig hints
    g.strokeStyle='rgba(60,46,32,.5)';g.lineWidth=2;for(let i=0;i<14;i++){g.beginPath();g.moveTo(S/2,S/2);g.lineTo(S/2+(r()-.5)*S*.8,S/2+(r()-.5)*S*.8);g.stroke();}
  }else if(p.kind==='scale'){
    for(let i=0;i<9000;i++){const x=r()*S,y=r()*S;const dx=(x-S/2)/(S*.48),dy=(y-S/2)/(S*.5);if(dx*dx+dy*dy*.7>(.75+.25*Math.sin(y*.13+x*.05))**2)continue;
      g.fillStyle=col(Math.floor(r()*9));g.beginPath();g.ellipse(x,y,3+r()*6,2+r()*4,r()*3,0,7);g.fill();}
  }else{
    for(let k=0;k<34;k++){const cx=S*(.2+r()*.6),cy=S*(.2+r()*.6);if(!inBlob(cx,cy))continue;
      for(let i=0;i<80;i++){const a=r()*7,l=20+r()*44;g.strokeStyle=col(Math.floor(r()*9));g.lineWidth=2.2;g.beginPath();g.moveTo(cx,cy);g.lineTo(cx+Math.cos(a)*l,cy+Math.sin(a)*l);g.stroke();}}
  }
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=4;return t;
}
function frondTexture(){
  const W=256,H=128,c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d'),r=rng(77);
  g.strokeStyle='#5b5a3a';g.lineWidth=3;g.beginPath();g.moveTo(4,H/2);g.quadraticCurveTo(W*.5,H*.45,W-4,H*.55);g.stroke();
  for(let i=0;i<70;i++){const t=i/70,x=4+t*(W-10),y=H/2+(Math.sin(t*3)*3);const l=(1-t*.6)*H*.48;
    for(const s of [-1,1]){g.strokeStyle=`rgb(${60+r()*30},${86+r()*30},${46+r()*16})`;g.lineWidth=2.4;g.beginPath();g.moveTo(x,y);g.lineTo(x+l*.55,y+s*l);g.stroke();}}
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function barkTexture(){
  const S=128,c=document.createElement('canvas');c.width=c.height=S;const g=c.getContext('2d'),r=rng(3);
  g.fillStyle='#5b5147';g.fillRect(0,0,S,S);for(let i=0;i<600;i++){const v=r()>.5;g.fillStyle=v?`rgba(150,140,124,${.12+r()*.2})`:`rgba(28,24,20,${.2+r()*.25})`;g.fillRect(r()*S,r()*S,1+r()*2,5+r()*16);}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=THREE.SRGBColorSpace;return t;
}

// ------------------------------------------------------------------ templates
class G{
  constructor(){this.b={p:[],n:[],uv:[],i:[]};this.l={p:[],n:[],uv:[],i:[]};}
  tube(pts,radii,sides=6){
    const B=this.b,base=B.p.length/3;
    for(let k=0;k<pts.length;k++){
      const p=pts[k],q=pts[Math.min(k+1,pts.length-1)],o=pts[Math.max(k-1,0)];
      const d=new THREE.Vector3(q[0]-o[0],q[1]-o[1],q[2]-o[2]).normalize(),a=Math.abs(d.y)<.9?new THREE.Vector3(0,1,0):new THREE.Vector3(1,0,0);
      const u=new THREE.Vector3().crossVectors(d,a).normalize(),v=new THREE.Vector3().crossVectors(d,u);
      for(let s=0;s<=sides;s++){const t=s/sides*Math.PI*2,n=u.clone().multiplyScalar(Math.cos(t)).addScaledVector(v,Math.sin(t));
        B.p.push(p[0]+n.x*radii[k],p[1]+n.y*radii[k],p[2]+n.z*radii[k]);B.n.push(n.x,n.y,n.z);B.uv.push(s/sides,k*.8);}
    }
    for(let k=0;k<pts.length-1;k++)for(let s=0;s<sides;s++){const a=base+k*(sides+1)+s,b=a+1,c=a+sides+1,d=c+1;B.i.push(a,c,b,b,c,d);}
  }
  card(c,size,n,centre,soft=.75,aspect=1,cell=[0,0,1,1]){
    const L=this.l,base=L.p.length/3,N=new THREE.Vector3(...n).normalize();
    const up=Math.abs(N.y)>.95?new THREE.Vector3(1,0,0):new THREE.Vector3(0,1,0);
    const u=new THREE.Vector3().crossVectors(up,N).normalize().multiplyScalar(size/2),v=new THREE.Vector3().crossVectors(N,u).normalize().multiplyScalar(size/2*aspect);
    const corners=[[-1,-1],[1,-1],[1,1],[-1,1]];
    for(const [a,b] of corners){
      const p=new THREE.Vector3(...c).addScaledVector(u,a).addScaledVector(v,b);
      const sph=p.clone().sub(new THREE.Vector3(...centre)).normalize(),nn=sph.multiplyScalar(soft).addScaledVector(N,1-soft).normalize();
      L.p.push(p.x,p.y,p.z);L.n.push(nn.x,nn.y,nn.z);L.uv.push(cell[0]+(a+1)/2*cell[2],cell[1]+(b+1)/2*cell[3]);
    }
    L.i.push(base,base+1,base+2,base,base+2,base+3);
  }
  geometry(){
    const g=new THREE.BufferGeometry(),B=this.b,L=this.l,nb=B.p.length/3;
    g.setAttribute('position',new THREE.Float32BufferAttribute([...B.p,...L.p],3));g.setAttribute('normal',new THREE.Float32BufferAttribute([...B.n,...L.n],3));
    g.setAttribute('uv',new THREE.Float32BufferAttribute([...B.uv,...L.uv],2));
    g.setIndex([...B.i,...L.i.map(i=>i+nb)]);g.addGroup(0,B.i.length,0);g.addGroup(B.i.length,L.i.length,1);g.computeBoundingBox();g.computeBoundingSphere();return g;
  }
}
function crownCards(G_,r,{cx=0,cy,cz=0,rx,ry,rz,count,size,soft=.75,bias=.45,flat=false}){
  for(let i=0;i<count;i++){
    const a=r()*Math.PI*2,v=r()*2-1,k=Math.sqrt(1-v*v),d=Math.pow(r(),bias);
    const p=[cx+Math.cos(a)*k*rx*d,cy+v*ry*d,cz+Math.sin(a)*k*rz*d];
    const out=[p[0]-cx,(p[1]-cy)*.6,p[2]-cz],n=flat?[out[0]*.3+(r()-.5)*.4,1,out[2]*.3+(r()-.5)*.4]:[out[0]+(r()-.5)*1.2,out[1]+(r()-.5)*1.2+.2,out[2]+(r()-.5)*1.2];
    if(Math.hypot(...n)<1e-3)n[1]=1;
    G_.card(p,size*(.75+r()*.5),n,[cx,cy,cz],soft);
  }
}
function branches(G_,r,trunkTop,n,crown,spread,rad){
  for(let i=0;i<n;i++){const a=i/n*Math.PI*2+r()*.6,e=[Math.cos(a)*spread*(.6+r()*.4),crown+(r()-.3)*spread*.5,Math.sin(a)*spread*(.6+r()*.4)];
    const m=[e[0]*.45,trunkTop+(e[1]-trunkTop)*.55,e[2]*.45];G_.tube([[0,trunkTop-.5,0],m,e],[rad,rad*.6,rad*.2],5);}
}
function template(species,seed,lod){
  const r=rng(seed*7919+species*31+lod*3),G_=new G(),hi=lod===0,f=hi?1.7:.38,sz=hi?.78:1.45;
  switch(species){
    case CYPRESS:{G_.tube([[0,0,0],[0,1.6,0]],[.26,.2],hi?7:5);
      const H=14,ring=hi?.42:1.05;for(let y=.9;y<H;y+=ring){const t=(y-.9)/(H-.9),R=1.3*Math.pow(Math.sin(Math.PI*Math.min(1,t*1.08+.04)),.65)*(1-.25*t)+.12;
        const n=hi?5:3;for(let k=0;k<n;k++){const a=k/n*Math.PI*2+r()*1.2+y;const p=[Math.cos(a)*R*.55,y+(r()-.5)*.3,Math.sin(a)*R*.55];G_.card(p,(R*1.25+.5)*(hi?1:1.25),[Math.cos(a),.35+(r()-.5)*.3,Math.sin(a)],[0,y,0],.6,1.3);}}
      break;}
    case ELM:case PLANE:case POPLAR:{
      const H=species===POPLAR?18:species===PLANE?18:17,tt=species===POPLAR?3:5.5,cr=species===POPLAR?2.6:species===PLANE?6.2:5.6;
      G_.tube([[0,0,0],[(r()-.5)*.3,tt*.5,(r()-.5)*.3],[0,tt,0]],[.42,.34,.28],hi?8:5);
      if(hi)branches(G_,r,tt,6,H*.66,cr*.75,.22);
      crownCards(G_,r,{cy:H*.64,rx:cr,ry:species===POPLAR?H*.38:H*.3,rz:cr,count:Math.round((species===POPLAR?60:75)*f),size:(species===POPLAR?2.4:3.1)*sz,soft:.8});break;}
    case HOLM:{G_.tube([[0,0,0],[.2,1.2,0],[0,1.9,.1]],[.22,.18,.15],hi?6:5);if(hi)branches(G_,r,1.9,5,4.2,2.2,.1);
      crownCards(G_,r,{cy:4.3,rx:3,ry:2.3,rz:3,count:Math.round(46*f),size:2*sz,soft:.82,bias:.35});break;}
    case OLIVE:{G_.tube([[0,0,0],[.25,.7,.1],[-.1,1.3,0]],[.24,.2,.16],hi?6:5);if(hi)branches(G_,r,1.3,4,2.9,1.7,.08);
      crownCards(G_,r,{cy:3.0,rx:2.3,ry:1.6,rz:2.3,count:Math.round(34*f),size:1.6*sz,soft:.7,bias:.4});break;}
    case PINE:{const lean=[(r()-.5)*1.2,0,(r()-.5)*1.2];G_.tube([[0,0,0],[lean[0]*.5,5,lean[2]*.5],[lean[0],9,lean[2]]],[.3,.22,.12],hi?6:5);
      const clumps=hi?7:4;for(let i=0;i<clumps;i++){const y=6+r()*5.5,a=r()*7,R=r()*2.2;const c=[lean[0]+Math.cos(a)*R,y,lean[2]+Math.sin(a)*R];if(hi)G_.tube([[lean[0]*.7,y-1.2,lean[2]*.7],c],[.08,.04],4);
        crownCards(G_,r,{cx:c[0],cy:c[1],cz:c[2],rx:1.5,ry:.9,rz:1.5,count:hi?7:3,size:1.9*sz,soft:.7,bias:.6});}break;}
    case STONEPINE:{G_.tube([[0,0,0],[.2,5,0],[0,9.5,.1]],[.34,.27,.18],hi?7:5);if(hi)branches(G_,r,9,6,10.4,3.6,.12);
      crownCards(G_,r,{cy:10.8,rx:5,ry:1.3,rz:5,count:Math.round(55*f),size:2.6*sz,soft:.8,bias:.3,flat:true});break;}
    case ORANGE:{G_.tube([[0,0,0],[0,1,0]],[.12,.1],hi?6:4);crownCards(G_,r,{cy:2.35,rx:1.7,ry:1.45,rz:1.7,count:Math.round(32*f),size:1.35*sz,soft:.8,bias:.3});break;}
    case PALM:{const H=11;G_.tube([[0,0,0],[.2,H*.5,0],[.3,H,0]],[.34,.3,.28],hi?8:5);
      const n=hi?18:10;for(let i=0;i<n;i++){const a=i/n*Math.PI*2+r()*.3,droop=-.2-r()*.6,L=3.4;
        const d=[Math.cos(a),droop,Math.sin(a)],c=[.3+d[0]*L*.5,H+.2+d[1]*L*.5,d[2]*L*.5];
        const N=new THREE.Vector3(-d[1]*Math.cos(a),1,-d[1]*Math.sin(a)).normalize();
        const L_=G_.l,base=L_.p.length/3,u=new THREE.Vector3(d[0],d[1],d[2]).normalize().multiplyScalar(L/2),v=new THREE.Vector3().crossVectors(N,u).normalize().multiplyScalar(.55);
        for(const [x,y] of [[-1,-1],[1,-1],[1,1],[-1,1]]){const p=new THREE.Vector3(...c).addScaledVector(u,x).addScaledVector(v,y);L_.p.push(p.x,p.y,p.z);L_.n.push(N.x,N.y,N.z);L_.uv.push((x+1)/2,(y+1)/2);}
        L_.i.push(base,base+1,base+2,base,base+2,base+3);}
      break;}
    case SHRUB:default:{crownCards(G_,r,{cy:.8,rx:1.3,ry:.9,rz:1.3,count:Math.round(16*f)+3,size:1.4*sz,soft:.85,bias:.3});break;}
  }
  return G_.geometry();
}
const REF_H={[CYPRESS]:14,[ELM]:17,[PLANE]:18,[POPLAR]:18,[HOLM]:7,[OLIVE]:4.6,[PINE]:12,[STONEPINE]:12.5,[ORANGE]:3.8,[PALM]:11.5,[SHRUB]:2};

function foliageMaterial(map,shadows){
  const m=new THREE.MeshStandardMaterial({map,alphaTest:.5,side:THREE.DoubleSide,roughness:.9,metalness:0});m.name='leaves';
  // Keep the crown's volumetric normals on back faces (no flip) so crowns read as masses.
  m.onBeforeCompile=s=>{s.fragmentShader=s.fragmentShader.replace('#include <normal_fragment_begin>','float faceDirection=gl_FrontFacing?1.0:-1.0;\nvec3 normal=normalize(vNormal);\nvec3 nonPerturbedNormal=normal;');};
  m.customProgramCacheKey=()=>'leaves';
  return m;
}

// ------------------------------------------------------------------ impostors
function bakeImpostors(renderer,templates,leafMaps,barkMap,frondMap){
  const C=4,R=3,cell=256,rt=new THREE.WebGLRenderTarget(C*cell,R*cell,{samples:0});
  rt.texture.generateMipmaps=true;rt.texture.minFilter=THREE.LinearMipmapLinearFilter;
  const scene=new THREE.Scene(),cam=new THREE.OrthographicCamera(-1,1,1,-1,.1,200),info=[];
  const prevTarget=renderer.getRenderTarget(),prevColor=renderer.getClearColor(new THREE.Color()),prevAlpha=renderer.getClearAlpha(),prevAuto=renderer.autoClear;
  renderer.setRenderTarget(rt);renderer.setClearColor(0x000000,0);renderer.clear();renderer.autoClear=false;
  SPECIES.forEach((name,s)=>{
    const g=templates[s][0][0],bb=g.boundingBox,w=Math.max(bb.max.x-bb.min.x,bb.max.z-bb.min.z),h=bb.max.y,size=Math.max(w,h)*1.04;
    const shade=new THREE.ShaderMaterial({uniforms:{map:{value:s===PALM?frondMap:leafMaps[name]},bark:{value:barkMap}},vertexShader:'varying vec2 vUv;varying float vL;void main(){vUv=uv;vL=0.55+0.45*clamp(normal.y*0.6+0.5+normal.z*0.25,0.0,1.0);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
      fragmentShader:'uniform sampler2D map;varying vec2 vUv;varying float vL;void main(){vec4 c=texture2D(map,vUv);if(c.a<0.5)discard;gl_FragColor=vec4(c.rgb*vL,1.0);}',side:THREE.DoubleSide});
    const barkM=new THREE.ShaderMaterial({vertexShader:'void main(){gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'void main(){gl_FragColor=vec4(0.09,0.07,0.05,1.0);}'});
    const mesh=new THREE.Mesh(g,[barkM,shade]);scene.clear();scene.add(mesh);
    cam.left=-size/2;cam.right=size/2;cam.bottom=0;cam.top=size;cam.position.set((bb.min.x+bb.max.x)/2,0,60);cam.lookAt((bb.min.x+bb.max.x)/2,0,0);cam.updateProjectionMatrix();
    const cx=s%C,cy=Math.floor(s/C);rt.viewport.set(cx*cell,cy*cell,cell,cell);rt.scissor.set(cx*cell,cy*cell,cell,cell);rt.scissorTest=true;
    renderer.setRenderTarget(rt);renderer.render(scene,cam);info[s]=size;
  });
  rt.scissorTest=false;rt.viewport.set(0,0,C*cell,R*cell);
  renderer.setRenderTarget(prevTarget);renderer.setClearColor(prevColor,prevAlpha);renderer.autoClear=prevAuto;
  return {texture:rt.texture,size:info,C,R};
}
function impostorMaterial(atlas,near){
  const m=new THREE.MeshStandardMaterial({map:atlas.texture,alphaTest:.5,roughness:.95,metalness:0});m.name='treeImpostor';
  m.onBeforeCompile=s=>{
    s.uniforms.uNear={value:near};
    s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nattribute float aCell;uniform float uNear;')
      .replace('#include <uv_vertex>',`#include <uv_vertex>\nvMapUv=vec2((mod(aCell,${atlas.C}.0)+uv.x)/${atlas.C}.0,(floor(aCell/${atlas.C}.0)+uv.y)/${atlas.R}.0);`)
      .replace('#include <beginnormal_vertex>',`vec3 iC=(instanceMatrix*vec4(0.0,0.0,0.0,1.0)).xyz;vec3 toC=cameraPosition-iC;toC.y=0.0;vec3 fwd=normalize(toC+vec3(1e-4,0.0,0.0));vec3 objectNormal=normalize(mix(fwd,vec3(0.0,1.0,0.0),0.45));`)
      .replace('#include <defaultnormal_vertex>','vec3 transformedNormal=normalMatrix*objectNormal;')
      .replace('#include <project_vertex>',`float sx=length(instanceMatrix[0].xyz),sy=length(instanceMatrix[1].xyz);
        vec3 rightV=vec3(fwd.z,0.0,-fwd.x);vec3 wpos=iC+rightV*position.x*sx+vec3(0.0,1.0,0.0)*position.y*sy;
        vec4 mvPosition=viewMatrix*vec4(wpos,1.0);gl_Position=projectionMatrix*mvPosition;
        if(length(cameraPosition-iC)<uNear)gl_Position=vec4(2.0,2.0,2.0,1.0);`);
  };
  m.customProgramCacheKey=()=>'tree-impostor';
  return m;
}

export async function loadTrees(url,renderer,scene,heightAt,low,reject=null){
  let buf=await (await fetch(url)).arrayBuffer();const head=new Uint8Array(buf,0,2);
  if(head[0]===0x1f&&head[1]===0x8b)buf=await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const n=new DataView(buf).getUint32(0,true),dv=new DataView(buf,4);
  const total=n+gardenTrees.length,X=new Float32Array(total),Y=new Float32Array(total),Z=new Float32Array(total),S=new Uint8Array(total),H=new Float32Array(total),SEED=new Uint8Array(total);
  for(let i=0;i<n;i++){const o=i*7;X[i]=dv.getInt16(o,true)/10;Z[i]=dv.getInt16(o+2,true)/10;S[i]=dv.getUint8(o+4);H[i]=dv.getUint8(o+5)/10;SEED[i]=dv.getUint8(o+6);Y[i]=heightAt(X[i],Z[i])-.15;if(reject&&reject(X[i],Z[i]))H[i]=0;}
  gardenTrees.forEach((t,k)=>{const i=n+k;X[i]=t.x;Y[i]=t.y;Z[i]=t.z;S[i]=t.s;H[i]=t.h;SEED[i]=(k*37)&255;});
  const leafMaps=Object.fromEntries(Object.keys(LEAF).map(k=>[k,leafTexture(k)])),barkMap=barkTexture(),frondMap=frondTexture();
  const barkMat=new THREE.MeshStandardMaterial({map:barkMap,roughness:1});barkMat.name='bark';
  const leafMats=SPECIES.map(name=>foliageMaterial(name==='palm'?frondMap:leafMaps[name]));
  if(!low)for(const m of leafMats)m.alphaToCoverage=true;
  // templates[species][lod][variant]
  const templates=SPECIES.map((_,s)=>[0,1].map(lod=>Array.from({length:VARIANTS},(_,v)=>template(s,v+1,lod))));
  const atlas=bakeImpostors(renderer,templates,leafMaps,barkMap,frondMap);
  // impostors: every tree, static
  const quad=new THREE.PlaneGeometry(1,1);quad.translate(0,.5,0);
  const imp=new THREE.InstancedMesh(quad,impostorMaterial(atlas,LOD_FAR-8),total);
  const cells=new Float32Array(total),m4=new THREE.Matrix4(),col=new THREE.Color();
  for(let i=0;i<total;i++){const s=S[i],k=H[i]/REF_H[s],size=atlas.size[s]*k||1e-4;m4.makeScale(size,size,size);m4.setPosition(X[i],Y[i],Z[i]);imp.setMatrixAt(i,m4);cells[i]=s;}
  quad.setAttribute('aCell',new THREE.InstancedBufferAttribute(cells,1));
  imp.frustumCulled=false;imp.name='treeImpostors';scene.add(imp);
  // near trees: per species, LOD and variant
  const near=[];
  for(let s=0;s<SPECIES.length;s++)for(let lod=0;lod<2;lod++)for(let v=0;v<VARIANTS;v++){
    let cap=0;for(let i=0;i<total;i++)if(S[i]===s)cap++;cap=Math.min(cap,lod===0?1500:6000);if(!cap)continue;
    const mesh=new THREE.InstancedMesh(templates[s][lod][v],[barkMat,leafMats[s]],cap);mesh.count=0;mesh.frustumCulled=false;mesh.castShadow=lod===0&&!low;mesh.receiveShadow=true;
    mesh.instanceColor=new THREE.InstancedBufferAttribute(new Float32Array(cap*3),3);mesh.name=`tree-${SPECIES[s]}-${lod}`;
    scene.add(mesh);near.push({s,lod,v,mesh,cap});
  }
  const bins=new Map(near.map(e=>[`${e.s}|${e.lod}|${e.v}`,e]));
  // spatial grid for quick near queries
  const CELL=64,grid=new Map();for(let i=0;i<total;i++){if(!H[i])continue;const key=Math.floor(X[i]/CELL)+','+Math.floor(Z[i]/CELL);if(!grid.has(key))grid.set(key,[]);grid.get(key).push(i);}
  let lastX=1e9,lastZ=1e9,lastY=1e9;
  function update(camera){
    const cx=camera.position.x,cz=camera.position.z,cy=camera.position.y;
    if(Math.hypot(cx-lastX,cz-lastZ)<3&&Math.abs(cy-lastY)<3)return;lastX=cx;lastZ=cz;lastY=cy;
    for(const e of near)e.mesh.count=0;
    const R=LOD_FAR,g0=Math.floor((cx-R)/CELL),g1=Math.floor((cx+R)/CELL),h0=Math.floor((cz-R)/CELL),h1=Math.floor((cz+R)/CELL);
    for(let gx=g0;gx<=g1;gx++)for(let gz=h0;gz<=h1;gz++){const list=grid.get(gx+','+gz);if(!list)continue;
      for(const i of list){const dx=X[i]-cx,dz=Z[i]-cz,dy=Y[i]-cy,d=Math.sqrt(dx*dx+dz*dz+dy*dy);if(d>=R)continue;
        const e=bins.get(`${S[i]}|${d<LOD0?0:1}|${SEED[i]%VARIANTS}`);if(!e||e.mesh.count>=e.cap)continue;
        const k=H[i]/REF_H[S[i]],w=k*(.88+(SEED[i]%13)/50);m4.makeRotationY(SEED[i]*.0246);m4.scale(new THREE.Vector3(w,k,w));m4.setPosition(X[i],Y[i],Z[i]);
        e.mesh.setMatrixAt(e.mesh.count,m4);const t=.84+(SEED[i]%17)/60;col.setRGB(t,t*(.97+(SEED[i]%5)/60),t*.95);e.mesh.setColorAt(e.mesh.count,col);e.mesh.count++;}
    }
    for(const e of near){e.mesh.instanceMatrix.needsUpdate=true;if(e.mesh.instanceColor)e.mesh.instanceColor.needsUpdate=true;}
  }
  return {update,count:total};
}
