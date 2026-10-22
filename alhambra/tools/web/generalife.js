import * as THREE from 'three';

// A long hipped ridge, rather than the generic pavilion's single pyramid apex.
function ridgeRoof(b,x,z,w,d,y,h){
 const a=w/2,c=d/2,r=Math.max(0,a-c),v=[],uv=[];
 const faces=[ [[-a,0,c],[a,0,c],[r,h,0],[-r,h,0]], [[a,0,-c],[-a,0,-c],[-r,h,0],[r,h,0]], [[a,0,c],[a,0,-c],[r,h,0]], [[-a,0,-c],[-a,0,c],[-r,h,0]] ];
 for(const f of faces)for(const i of f.length===4?[0,1,2,0,2,3]:[0,1,2]){const p=f[i];v.push(...p);uv.push(p[0]/3,(p[2]+p[1])/3);}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(v,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();b.unique(g,'roof',[x,y,z]);b.box(x,y-.12,z,w,.14,d,'plainTimber');
}
export function generalifeNorth(b){
 // White upper facade behind the lower five-arch portico, as in the bundled
 // Generalife photograph. Dimensions are inferred, not a measured elevation.
 const z=-25.9;
 for(const sign of [-1,1])b.box(sign*8.35,5.9,z-1.9,.3,4.95,4.35,'whiteLime');
 b.box(0,5.9,z-4,17,4.95,.3,'whiteLime');
 b.box(0,5.9,z,17,.42,.55,'whiteLime');
 b.box(0,7.55,z,17,.48,.55,'whiteLime');
 for(const x of [-7,7])b.box(x,6.32,z,3,4.53,.55,'whiteLime');
 // Six small arched windows in three pairs, with genuinely recessed dark backs.
 for(const center of [-3.6,0,3.6])for(const dx of [-.63,.63]){
  const x=center+dx;b.box(x,6.4,z-.20,.83,1.14,.08,'dark');b.arch(x,z,.83,.77,.36,1.23,.55,'whiteLime',0,6.32,false);
 }
 const gaps=[[-5.5,-4.645],[-3.815,-3.385],[-2.555,-1.045],[-.215,.215],[1.045,2.555],[3.385,3.815],[4.645,5.5]];
 for(const [l,r] of gaps)b.box((l+r)/2,6.32,z,r-l,1.23,.55,'whiteLime');
 // Three deep open loggias separated by substantial white piers.
 for(const x of [-5.5,-1.8,1.8,5.5])b.box(x,8.03,z,.65,2.82,.65,'whiteLime');
 b.box(0,8.03,z-3.8,11.7,2.82,.3,'whiteLime');b.box(0,8.03,z-1.9,11.7,.15,4,'plainTimber');
 for(const x of [-3.65,0,3.65]){
  b.box(x,8.80,z+.07,3.03,.09,.12,'plainTimber');b.box(x,8.08,z+.07,3.03,.09,.12,'plainTimber');
  for(let k=0;k<=14;k++)b.box(x-1.42+k*.203,8.17,z+.07,.045,.63,.055,'plainTimber');
  b.box(x,8.87,z+.04,.09,1.75,.09,'plainTimber');
 }
 b.box(0,10.6,z,17,.25,.7,'whiteLime');ridgeRoof(b,0,z-1.6,18.2,5.6,10.9,1.2);
 // The small left tower rises slightly above the main eaves, with paired arches.
 b.box(-7,10.85,z,3,1.05,.55,'whiteLime');
 for(const x of [-7.55,-6.45]){b.box(x,10.95,z+.30,.62,.74,.04,'dark');b.arch(x,z+.36,.62,.43,.3,.9,.06,'whiteLime',0,10.9,false);}
 ridgeRoof(b,-7,z-1.25,3.6,3.5,12, .65);
 // The right end has small square openings, not an all-timber balcony.
 for(const [x,y,w,h] of [[7,6.7,.45,.55],[7.5,9,.48,.68],[7.5,10,.18,.2]])b.box(x,y,z+.29,w,h,.035,'dark');
}
