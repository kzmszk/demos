import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const axis=new THREE.Vector3(0,1,0), dummy=new THREE.Object3D();
export class Builder {
  constructor(root,mats,nav){this.root=root;this.m=mats;this.nav=nav;this.merged=new Map();this.instances=new Map();this.cache=new Map();this.offset=[0,0,0];this.zone='core';this.stats={columns:0,muqarnas:0,lions:0};}
  geometry(key,fn){if(!this.cache.has(key))this.cache.set(key,fn());return this.cache.get(key);}
  add(g,mat,pos=[0,0,0],scale=[1,1,1],rot=0){
    const key=this.zone+'|'+g.uuid+'|'+mat;
    if(!this.instances.has(key))this.instances.set(key,{g,m:this.m[mat],mat,transforms:[]});
    dummy.position.set(pos[0]+this.offset[0],pos[1]+this.offset[1],pos[2]+this.offset[2]);dummy.scale.set(...scale);dummy.rotation.set(0,rot,0);dummy.updateMatrix();this.instances.get(key).transforms.push(dummy.matrix.clone());
  }
  unique(g,mat,pos=[0,0,0],rot=0){
    dummy.position.set(pos[0]+this.offset[0],pos[1]+this.offset[1],pos[2]+this.offset[2]);dummy.scale.set(1,1,1);dummy.rotation.set(0,rot,0);dummy.updateMatrix();g.applyMatrix4(dummy.matrix);g.clearGroups();
    const k=this.zone+'|'+mat;if(!this.merged.has(k))this.merged.set(k,{m:this.m[mat],list:[]});this.merged.get(k).list.push(g);
  }
  box(x,y,z,w,h,d,mat='ivory',rot=0,block=false){
    const unit=this.m[mat].userData.scale||1;const key=`box:${w.toFixed(3)}:${h.toFixed(3)}:${d.toFixed(3)}:${unit}`;
    const g=this.geometry(key,()=>{const g=new THREE.BoxGeometry(w,h,d),uv=g.attributes.uv;for(let i=0;i<24;i++){const face=Math.floor(i/4),sx=(face<2?d:w)/unit,sy=(face===2||face===3?d:h)/unit;uv.setXY(i,uv.getX(i)*sx,uv.getY(i)*sy);}return g;});
    this.add(g,mat,[x,y+h/2,z],[1,1,1],rot);
    if(block)this.nav.box(x+this.offset[0],z+this.offset[2],w,d,y+this.offset[1],y+h+this.offset[1],rot);
  }
  floor(x,z,w,d,y=0,mat='marble',rot=0){this.box(x,y-.18,z,w,.18,d,mat,rot);this.nav.floor(x+this.offset[0],z+this.offset[2],w,d,y+this.offset[1],rot);}
  cylinder(x,y,z,r,h,mat='marble',top=r,segments=16){const key=`cyl:${segments}:${top/r}`;const g=this.geometry(key,()=>new THREE.CylinderGeometry(top/r,1,1,segments));this.add(g,mat,[x,y+h/2,z],[r,h,r]);}
  sphere(x,y,z,sx,sy,sz,mat='marble',rot=0){const plant=['tree','hedge'].includes(mat),bud=['flower','whiteFlower','gold'].includes(mat)&&sx<.1;const g=bud?this.geometry('bud',()=>new THREE.IcosahedronGeometry(1,0)):this.geometry(plant?'foliage':'sphere',()=>plant?new THREE.IcosahedronGeometry(1,1):new THREE.SphereGeometry(1,14,9));this.add(g,mat,[x,y,z],[sx,sy,sz],rot);}
  flowers(x,y,z,mat='flower'){
    this.sphere(x,y-.15,z,.4,.4,.4,'hedge');
    for(let i=0;i<9;i++){const a=i*2.399,dx=Math.cos(a)*.3,dz=Math.sin(a)*.3,yy=y+.08+Math.sin(i*2)*.15;for(let k=0;k<5;k++){const t=k*Math.PI*.4;this.sphere(x+dx+Math.cos(t)*.055,yy,z+dz+Math.sin(t)*.055,.05,.028,.05,mat);}this.sphere(x+dx,yy+.02,z+dz,.025,.025,.025,'gold');}
  }
  cone(x,y,z,r,h,mat='cypress',n=10){const g=this.geometry('cone:'+n,()=>new THREE.ConeGeometry(1,1,n));this.add(g,mat,[x,y+h/2,z],[r,h,r]);}
  column(x,z,h=3.1,r=.13,y=0,mat='marble'){
    this.stats.columns++;this.cylinder(x,y,z,r*1.65,.11,mat);this.cylinder(x,y+.11,z,r*1.32,.13,mat);
    this.cylinder(x,y+.24,z,r,h-.66,mat,r*.78,16);
    for(let k=0;k<3;k++)this.cylinder(x,y+h-.45+k*.065,z,r*1.15,.045,mat);
    this.box(x,y+h-.3,z,r*2.8,.22,r*2.8,'plaster');this.box(x,y+h-.08,z,r*3.5,.08,r*3.5,mat);
    this.nav.box(x+this.offset[0],z+this.offset[2],r*2,r*2,y+this.offset[1],y+h+this.offset[1]);
  }
  arch(x,z,w,spring=3.1,rise=1.0,top=5.2,depth=.38,mat='plaster',rot=0,y=0,lobes=true){
    const key=`arch:${w}:${spring}:${rise}:${top}:${depth}:${lobes}`;
    const g=this.geometry(key,()=>{
      const s=new THREE.Shape();s.moveTo(-w/2,spring);s.lineTo(-w/2,top);s.lineTo(w/2,top);s.lineTo(w/2,spring);
      for(let i=0;i<=48;i++){const a=Math.PI*i/48,rr=lobes?Math.sin(a*11)**2*.045:0;s.lineTo(Math.cos(a)*(w/2-rr),spring+Math.sin(a)**.82*rise-rr);}
      s.closePath();const g=new THREE.ExtrudeGeometry(s,{depth,bevelEnabled:false,curveSegments:16});g.translate(0,0,-depth/2);const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)/1.25,uv.getY(i)/1.25);g.clearGroups();return g;
    });
    this.add(g,mat,[x,y,z],[1,1,1],rot);
    const trimKey=`trim:${w}:${spring}:${rise}:${depth}:${lobes}`;
    const trim=this.geometry(trimKey,()=>{const pts=[];for(let i=0;i<=48;i++){const a=Math.PI*i/48;pts.push(new THREE.Vector3(Math.cos(a)*w/2,spring+Math.sin(a)**.82*rise,.5*depth+.025));}return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),48,.025,5,false);});
    this.add(trim,'ivory',[x,y,z],[1,1,1],rot);
  }
  wall(x,z,w,h=6,depth=.6,door=0,mat='plaster',rot=0,y=0,tile='tile'){
    const world=(u,v=0)=>[x+u*Math.cos(rot)+v*Math.sin(rot),z-u*Math.sin(rot)+v*Math.cos(rot)];
    const panel=(cx,ww)=>{
      const [px,pz]=world(cx);this.box(px,y,pz,ww,h,depth,mat,rot,true);
      if(tile){for(const sign of [-1,1]){const [tx,tz]=world(cx,sign*(depth/2+.018));this.box(tx,y+.1,tz,ww,1.35,.025,tile,rot);this.box(tx,y+1.49,tz,ww,.18,.05,'frieze',rot);this.box(tx,y+h-.6,tz,ww,.32,.04,'frieze',rot);}}
    };
    if(door){panel(-(w+door)/4,(w-door)/2);panel((w+door)/4,(w-door)/2);if(h>3)this.arch(x,z,door,2.25,door*.52,h,depth,mat,rot,y,false);}
    else panel(0,w);
  }
  roof(x,z,w,d,y=6,h=2,mat='roof'){
    const s=new THREE.BufferGeometry();const v=[-w/2,0,-d/2,w/2,0,-d/2,0,h,0,w/2,0,-d/2,w/2,0,d/2,0,h,0,w/2,0,d/2,-w/2,0,d/2,0,h,0,-w/2,0,d/2,-w/2,0,-d/2,0,h,0];
    s.setAttribute('position',new THREE.Float32BufferAttribute(v,3));const uv=[];for(let i=0;i<v.length;i+=3)uv.push(v[i]/3,v[i+2]/3+v[i+1]/3);s.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));s.setIndex([0,2,1,3,5,4,6,8,7,9,11,10]);s.computeVertexNormals();this.unique(s,mat,[x,y,z]);this.box(x,y-.16,z,w+.25,.18,d+.25,'wood');
  }
  line(a,b,thick=.05,mat='ivory'){
    const A=new THREE.Vector3(...a),B=new THREE.Vector3(...b),dir=B.clone().sub(A),mid=A.clone().add(B).multiplyScalar(.5);
    const g=this.geometry('rod',()=>new THREE.CylinderGeometry(1,1,1,6));const k=this.zone+'|'+g.uuid+'|'+mat;
    if(!this.instances.has(k))this.instances.set(k,{g,m:this.m[mat],mat,transforms:[]});
    dummy.position.copy(mid).add(new THREE.Vector3(...this.offset));dummy.scale.set(thick,dir.length(),thick);dummy.quaternion.setFromUnitVectors(axis,dir.normalize());dummy.updateMatrix();this.instances.get(k).transforms.push(dummy.matrix.clone());
  }
  jet(x,y,z,dx,dz,rise=1.4){const pts=[];for(let i=0;i<=24;i++){const t=i/24;pts.push(new THREE.Vector3(x+dx*t,y+Math.sin(t*Math.PI)*rise,z+dz*t));}const geo=new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),24,.018,4,false);this.unique(geo,'jet');}
  crenels(x,z,w,d,top,mat='redwall'){
    for(let i=-w/2;i<=w/2;i+=1.3)for(const s of [-1,1])this.box(x+i,top,z+s*d/2,.65,.9,.65,mat);
    for(let j=-d/2+1.2;j<d/2;j+=1.3)for(const s of [-1,1])this.box(x+s*w/2,top,z+j,.65,.9,.65,mat);
  }
  finish(){
    for(const [key,{g,m,transforms,mat}] of this.instances){
      if(transforms.length<24){
        const k=key.split('|')[0]+'|'+mat;if(!this.merged.has(k))this.merged.set(k,{m,list:[]});
        for(const transform of transforms)this.merged.get(k).list.push(g.clone().applyMatrix4(transform));
        continue;
      }
      const mesh=new THREE.InstancedMesh(g,m,transforms.length);transforms.forEach((t,i)=>mesh.setMatrixAt(i,t));mesh.computeBoundingSphere();mesh.castShadow=!['jet','water','shadow','flower','whiteFlower','gold'].includes(mat);mesh.receiveShadow=true;this.root.add(mesh);
    }
    for(const {m,list} of this.merged.values()){
      // Normalize indexing; ExtrudeGeometry and simple primitives use different representations.
      const normalized=list.map(g=>g.index?g.toNonIndexed():g);const merged=mergeGeometries(normalized,false);
      if(!merged)throw new Error('Incompatible architectural geometry');const mesh=new THREE.Mesh(merged,m);mesh.castShadow=m.name!=='jet';mesh.receiveShadow=true;this.root.add(mesh);
      for(const g of new Set([...list,...normalized]))g.dispose();
    }
    this.merged.clear();this.instances.clear();
  }
}
