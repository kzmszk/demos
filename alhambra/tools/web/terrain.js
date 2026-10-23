import * as THREE from 'three';

// Real ground from the IGN 5/25/200 m DEM (CC BY 4.0), prepared by tools/gen/terrain.py as nested
// regular grids ("rings") blended into the flat palace plateau. Rings 0–1 (≤ 3 km) are drawn in the
// main scene with OSM landcover colour rasters; rings 2–3 (the Vega and the Sierra Nevada, out to
// ~40 km) are drawn in a separate far pass with their own depth range.

export async function loadTerrain(url){
  let buf=await (await fetch(url)).arrayBuffer();const head=new Uint8Array(buf,0,2);
  if(head[0]===0x1f&&head[1]===0x8b)buf=await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const length=new DataView(buf).getUint32(0,true),header=JSON.parse(new TextDecoder().decode(new Uint8Array(buf,4,length)));
  let offset=4+length;
  const rings=header.rings.map(r=>{
    const n=r.nx*r.nz,q=new Int16Array(buf.slice(offset,offset+n*2)),h=new Float32Array(n);offset+=n*2;
    for(let i=0;i<n;i++)h[i]=q[i]/10;
    let colour=null;if(r.colour){colour=new Uint8Array(buf.slice(offset,offset+n*3));offset+=n*3;}
    return {...r,h,colour};
  });
  return {E0:header.E0,rings};
}

// Height on the same triangles the mesh uses (diagonal from (c+1,r) to (c,r+1)).
export function sampler(terrain){
  const rings=terrain.rings;
  return (x,z)=>{
    for(const r of rings){
      const fx=(x-r.x0)/r.s,fz=(z-r.z0)/r.s;
      if(fx<0||fz<0||fx>=r.nx-1||fz>=r.nz-1)continue;
      const c=Math.floor(fx),w=Math.floor(fz),u=fx-c,v=fz-w,i=w*r.nx+c,h=r.h;
      const a=h[i],b=h[i+1],cc=h[i+r.nx],d=h[i+r.nx+1];
      return u+v<=1?a+u*(b-a)+v*(cc-a):d+(1-u)*(cc-d)+(1-v)*(b-d);
    }
    return -110;
  };
}

const DROP=.22; // the visible ground sits just below the walkable level, as before
function chunkGeometry(r,c0,c1,r0,r1,uvExtent){
  const nx=c1-c0+1,nz=r1-r0+1,pos=new Float32Array(nx*nz*3),nor=new Float32Array(nx*nz*3);
  const uv=uvExtent?new Float32Array(nx*nz*2):null,col=r.colour?new Float32Array(nx*nz*3):null;
  const H=(c,w)=>r.h[Math.min(r.nz-1,Math.max(0,w))*r.nx+Math.min(r.nx-1,Math.max(0,c))];
  let k=0;
  for(let w=r0;w<=r1;w++)for(let c=c0;c<=c1;c++,k++){
    const x=r.x0+c*r.s,z=r.z0+w*r.s,y=r.h[w*r.nx+c]-DROP;
    pos[k*3]=x;pos[k*3+1]=y;pos[k*3+2]=z;
    const dx=(H(c+1,w)-H(c-1,w))/(2*r.s),dz=(H(c,w+1)-H(c,w-1))/(2*r.s),l=Math.hypot(dx,1,dz);
    nor[k*3]=-dx/l;nor[k*3+1]=1/l;nor[k*3+2]=-dz/l;
    if(uv){uv[k*2]=(x-uvExtent[0])/(uvExtent[1]-uvExtent[0]);uv[k*2+1]=1-(z-uvExtent[2])/(uvExtent[3]-uvExtent[2]);}
    if(col){const j=(w*r.nx+c)*3;col[k*3]=(r.colour[j]/255)**2.2;col[k*3+1]=(r.colour[j+1]/255)**2.2;col[k*3+2]=(r.colour[j+2]/255)**2.2;}
  }
  const index=[];
  for(let w=r0;w<r1;w++)for(let c=c0;c<c1;c++){
    if(r.hole&&c>=r.hole[0]&&c<r.hole[1]&&w>=r.hole[2]&&w<r.hole[3])continue;
    const a=(w-r0)*nx+(c-c0),b=a+1,cc=a+nx,d=cc+1;index.push(a,cc,b,b,cc,d);
  }
  if(!index.length)return null;
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('normal',new THREE.BufferAttribute(nor,3));
  if(uv)g.setAttribute('uv',new THREE.BufferAttribute(uv,2));if(col)g.setAttribute('color',new THREE.BufferAttribute(col,3));
  g.setIndex(pos.length/3>65535?new THREE.Uint32BufferAttribute(index,1):new THREE.Uint16BufferAttribute(index,1));g.computeBoundingSphere();
  return g;
}
function ringMeshes(r,material,chunk,uvExtent){
  const meshes=[];
  for(let r0=0;r0<r.nz-1;r0+=chunk)for(let c0=0;c0<r.nx-1;c0+=chunk){
    const g=chunkGeometry(r,c0,Math.min(r.nx-1,c0+chunk),r0,Math.min(r.nz-1,r0+chunk),uvExtent);
    if(g)meshes.push(new THREE.Mesh(g,material));
  }
  return meshes;
}

// Fine grain over the landcover raster, in world space, fading out with distance.
function detailTexture(){
  const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d');g.fillStyle='#808080';g.fillRect(0,0,512,512);
  let seed=91;const rnd=()=>((seed=Math.imul(seed,1664525)+1013904223|0)>>>0)/4294967296;
  for(let i=0;i<26000;i++){const v=90+rnd()*80|0;g.fillStyle=`rgba(${v},${v},${v},${.25+rnd()*.35})`;const s=1+rnd()*3.5;g.beginPath();g.ellipse(rnd()*512,rnd()*512,s,s*(.5+rnd()*.6),rnd()*3,0,7);g.fill();}
  for(let i=0;i<500;i++){g.fillStyle=`rgba(40,36,24,${.12+rnd()*.15})`;g.beginPath();g.ellipse(rnd()*512,rnd()*512,4+rnd()*14,3+rnd()*9,rnd()*3,0,7);g.fill();}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=THREE.NoColorSpace;t.anisotropy=8;return t;
}
function groundMaterial(map,detail){
  const m=new THREE.MeshStandardMaterial({map,roughness:1,metalness:0});m.name='ground';
  m.onBeforeCompile=s=>{
    s.uniforms.uDetail={value:detail};
    s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vGroundWorld;').replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nvGroundWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
    s.fragmentShader=s.fragmentShader.replace('#include <common>','#include <common>\nvarying vec3 vGroundWorld;uniform sampler2D uDetail;')
      .replace('#include <map_fragment>',`#include <map_fragment>
      float gd=length(vGroundWorld-cameraPosition);
      float d1=texture2D(uDetail,vGroundWorld.xz/3.1).r,d2=texture2D(uDetail,vGroundWorld.xz/17.3).r;
      diffuseColor.rgb*=mix(1.0,(0.55+0.9*d1)*(0.75+0.5*d2),clamp(1.0-gd/420.0,0.0,1.0)*0.9);`);
  };
  m.customProgramCacheKey=()=>'ground-detail';
  return m;
}

export function buildTerrain(terrain,scene,farScene,low){
  const loader=new THREE.TextureLoader(),detail=detailTexture(),near=[];
  terrain.rings.forEach((r,i)=>{
    if(i<2){
      const tex=loader.load(`data/ground${i}.jpg`);tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=8;
      const extent=[r.x0,r.x0+(r.nx-1)*r.s,r.z0,r.z0+(r.nz-1)*r.s];
      for(const m of ringMeshes(r,groundMaterial(tex,detail),low?48:64,extent)){m.receiveShadow=true;m.name='terrain';scene.add(m);near.push(m);}
    }else{
      const mat=new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0});mat.name='farTerrain';
      for(const m of ringMeshes(r,mat,48))farScene.add(m);
    }
  });
  // An apron to the horizon beyond the outermost grid, lost in the haze.
  const r=terrain.rings.at(-1),x0=r.x0,x1=r.x0+(r.nx-1)*r.s,z0=r.z0,z1=r.z0+(r.nz-1)*r.s,R=260000,y=-130;
  const shape=new THREE.Shape([new THREE.Vector2(-R,-R),new THREE.Vector2(R,-R),new THREE.Vector2(R,R),new THREE.Vector2(-R,R)]);
  shape.holes.push(new THREE.Path([new THREE.Vector2(x0+200,-(z0+200)),new THREE.Vector2(x0+200,-(z1-200)),new THREE.Vector2(x1-200,-(z1-200)),new THREE.Vector2(x1-200,-(z0+200))]));
  const apron=new THREE.ShapeGeometry(shape);apron.rotateX(-Math.PI/2);
  const am=new THREE.MeshStandardMaterial({color:0x7d7a5c,roughness:1});am.name='apron';const a=new THREE.Mesh(apron,am);a.position.y=y;farScene.add(a);
  return near;
}

// Open stretches of the Darro and the Genil as gently moving water ribbons.
export async function buildRivers(url,scene){
  const rivers=await (await fetch(url)).json(),pos=[],uv=[],idx=[];
  for(const r of rivers){
    const p=r.p;let along=0;
    for(let i=0;i<p.length;i++){
      const a=p[Math.max(0,i-1)],b=p[Math.min(p.length-1,i+1)],dx=b[0]-a[0],dz=b[2]-a[2],l=Math.hypot(dx,dz)||1,nx=-dz/l*r.w/2,nz=dx/l*r.w/2;
      if(i)along+=Math.hypot(p[i][0]-p[i-1][0],p[i][2]-p[i-1][2]);
      const base=pos.length/3;pos.push(p[i][0]-nx,p[i][1],p[i][2]-nz,p[i][0]+nx,p[i][1],p[i][2]+nz);uv.push(0,along/8,1,along/8);
      if(i)idx.push(base-2,base,base-1,base-1,base,base+1);
    }
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
  for(let i=0;i<g.attributes.normal.count;i++)g.attributes.normal.setXYZ(i,0,1,0);
  const m=new THREE.MeshStandardMaterial({color:0x5d7470,roughness:.12,metalness:.1,side:THREE.DoubleSide});m.name='river';
  const mesh=new THREE.Mesh(g,m);mesh.receiveShadow=true;mesh.name='rivers';scene.add(mesh);return mesh;
}
