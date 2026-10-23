export const EYE = 1.65;
export function insidePolygon(x,z,poly) {
  let inside=false;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++) {
    const a=poly[i],b=poly[j];
    if(((a[1]>z)!==(b[1]>z)) && x < (b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]) inside=!inside;
  }
  return inside;
}
// The real ground (terrain.js) once loaded; until then (and in node tests) the procedural model.
let ground=null;
export function setTerrainSampler(f){ground=f;}
export function terrainHeight(x,z) {
  if(ground)return ground(x,z);
  return modelHeight(x,z);
}
export function modelHeight(x,z) {
  const center=20+Math.max(0,x)*.43;
  const cliff = Math.max(0,Math.abs(z-center)-(x<0?75:85))/1.65 + Math.max(0,-x-260)/3;
  const plateau = -Math.min(66,cliff);
  const g = Math.exp(-(((x-370)/115)**4+((z+52)/155)**4));
  return Math.max(plateau, -45+77*g);
}
export class Navigation {
  constructor(){ this.blocks=[]; this.surfaces=[]; this.limit=950; }
  box(x,z,w,d,bottom=0,top=5,angle=0){this.blocks.push({x,z,w:w/2,d:d/2,bottom,top,c:Math.cos(angle),s:Math.sin(angle)});}
  floor(x,z,w,d,y=0,angle=0){this.surfaces.push({x,z,w:w/2,d:d/2,y,c:Math.cos(angle),s:Math.sin(angle)});}
  ramp(x,z,w,d,y0,y1,angle=0){this.surfaces.push({x,z,w:w/2,d:d/2,y:y0,y1,c:Math.cos(angle),s:Math.sin(angle)});}
  local(s,x,z){const dx=x-s.x,dz=z-s.z;return [dx*s.c-dz*s.s,dx*s.s+dz*s.c];}
  height(x,z,feet=Infinity){
    let best=terrainHeight(x,z);
    for(const s of this.surfaces){const [u,v]=this.local(s,x,z);if(Math.abs(u)<=s.w&&Math.abs(v)<=s.d){const y=s.y1===undefined?s.y:s.y+(s.y1-s.y)*(v/s.d+1)/2;if(y<=feet+0.42 && y>best)best=y;}}
    return best;
  }
  blocked(x,z,feet,r=.23){
    if(Math.abs(x)>this.limit || Math.abs(z)>this.limit) return true;
    for(const b of this.blocks){if(feet+1.4<b.bottom || feet>=b.top-.12) continue;const [u,v]=this.local(b,x,z);if(Math.abs(u)<b.w+r&&Math.abs(v)<b.d+r)return true;}
    return false;
  }
  move(pos,dx,dz) {
    const n=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.14));
    let feet=pos.y-EYE;
    for(let i=0;i<n;i++) {
      for(const axis of ['x','z']) {
        const x=pos.x+(axis==='x'?dx/n:0),z=pos.z+(axis==='z'?dz/n:0);
        const ground=this.height(x,z,feet);
        if(ground-feet>.43 || feet-ground>.9 || this.blocked(x,z,Math.max(feet,ground))) continue;
        pos.x=x;pos.z=z;feet=ground;
      }
    }
    pos.y=feet+EYE;return pos;
  }
}
