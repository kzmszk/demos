import * as THREE from 'three';

// Shared by the hero modules and the outer walls in exterior.js.
export function segment(b,a,c,h=8,d=1.4,mat='redwall',base=0,crenels=true){
  const dx=c[0]-a[0],dz=c[1]-a[1],len=Math.hypot(dx,dz),rot=-Math.atan2(dz,dx),x=(a[0]+c[0])/2,z=(a[1]+c[1])/2;
  b.box(x,base,z,len,h,d,mat,rot,true);
  if(crenels)for(let t=.6;t<len;t+=1.45)b.box(a[0]+dx*t/len,base+h,c[1]-(1-t/len)*dz,.7,.85,.7,mat,rot);
}
export function stairs(b,x,z,width,length,y0,y1,reverse=false){
  const steps=Math.ceil(Math.abs(y1-y0)/.18),depth=length/steps;
  for(let i=0;i<steps;i++){const y=y0+(y1-y0)*(i+1)/steps,zz=z+(reverse?-1:1)*(-length/2+(i+.5)*depth);b.box(x,y-.25,zz,width,.25,depth+.02,'paving');}
  b.nav.ramp(x,z,width,length,reverse?y1:y0,reverse?y0:y1);
}

