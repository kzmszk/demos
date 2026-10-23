import * as THREE from 'three';
import { segment, stairs } from './common.js';
import { leaves } from '../landscape-detail.js';
import { plant, CYPRESS, ELM, HOLM, OLIVE, ORANGE, PALM, SHRUB, PLANE } from '../trees.js';

// The Alcazaba of the Alhambra. Everything is generated from the OSM footprints and from the 5 m IGN DEM
// (table below): the wall mass is "outline minus Plaza de Armas", towers rise from it, the perimeter curtain
// walls follow the ground down to the Darro slope, and the surfaces carry procedurally generated tapial,
// lime-render, brick-and-cobble, rubble and gravel textures (public/textures/alcazaba, see credits.json).

// ======================================================================= data
const DEM={x0:-330,z0:-80,d:5,nx:47,nz:37,b64:'Vf5c/mL+Zv5v/nb+e/6H/pL+kv6U/pr+oP6n/q3+tP7B/s7+1v7b/tz+3P7g/uj+9v4H/xf/I/8s/zT/O/85/yb/A//a/r3+sv6w/rT+u/7G/t7+/f4X/yb/Kv8m/2X+cf52/nX+fP6D/oz+mf6l/qn+qP6u/rX+vf7D/sn+0/7d/uX+6/7t/u/+9P78/gf/FP8g/yv/Nf8+/0f/Sv8//yb/Av/f/s7+0f7b/uX+8P4G/x//Nv8//zz/NP91/oL+h/6F/ov+kf6c/qv+uP69/rz+wv7I/s/+1P7Z/t/+5/7v/vb++/4A/wb/Dv8W/yD/Kv80/z//Sv9S/1f/Uv9C/yb/B//4/gH/Ev8Y/yH/MP9A/0//Uv9L/0H/gv6L/pD+kv6a/qD+qP63/sP+yv7O/tL+1v7b/t7+4f7m/u7+9/4A/wj/Dv8V/xz/I/8r/zX/P/9L/1f/Xv9j/2T/Wv9G/zP/Lf87/0n/TP9S/1z/Yv9l/2H/WP9N/47+k/6Z/qD+qf6v/rb+w/7O/tX+2v7f/uL+5P7m/ur+7/73/gD/C/8U/xz/Iv8o/y//N/9A/0r/Vv9h/2n/cf92/3P/av9j/2T/bv92/3j/e/9//33/d/9u/2X/Wv+a/qH+qf6x/rn+vv7F/tH+2P7e/uL+5/7q/u3+8f72/vz+BP8L/xX/H/8p/y//NP87/0P/TP9W/2H/a/90/37/h/+M/43/j/+S/5f/mf+Z/5j/lv+R/4f/ff9z/2n/p/6x/rz+w/7J/s/+1/7e/uL+5v7r/vD+9P75/v/+BP8L/xH/F/8f/yv/Nf88/0H/SP9Q/1j/Yv9r/3X/f/+J/5X/oP+o/63/sv+0/7P/sP+t/6n/o/+Y/4z/gf92/7f+wv7M/tP+2v7i/un+6/7t/u/+9/7+/gL/CP8N/xT/Gf8e/yP/Kv82/0H/Sv9Q/1f/Xv9l/27/d/+A/4r/lf+i/67/uP+//8X/xv/F/8L/v/+6/7L/p/+b/4//g//I/tL+3P7j/ur+8v74/vj++f78/gX/Dv8S/xf/HP8i/yf/LP8x/zj/Qv9N/1j/YP9m/23/c/97/4T/jv+Y/6P/rv+6/8P/yv/R/9X/1P/R/87/yf/C/7b/qv+f/5P/2/7i/un+8P74/v/+Bv8G/wj/DP8U/xv/IP8m/yv/MP81/zr/QP9F/07/WP9j/2//d/99/4L/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'};
const OUTLINE=[[-202.3,-15.9],[-212,-14.3],[-211.3,-10],[-211.1,-8.5],[-210.4,-4.7],[-209.2,-4.9],[-207,8.9],[-206.5,11.6],[-218.7,14.8],[-219.5,10.7],[-238.4,12.3],[-242.4,12.8],[-240.2,35.8],[-235.4,35.8],[-234.4,45],[-228.5,45.2],[-229,53],[-221,53.5],[-220.5,45.7],[-220.1,40.1],[-217.8,40],[-207.5,39.4],[-207.5,41.5],[-198.7,41.5],[-198.7,39],[-147.3,38.9],[-147.8,43.5],[-138.7,44.3],[-137.8,34.5],[-139.5,34.3],[-138.4,19.1],[-134.4,19.4],[-133.3,3.4],[-137.7,3],[-138,-9.4],[-131.6,-9.4],[-131.6,-21.3],[-142.4,-21.3],[-142.4,-12.8],[-145,-13],[-150.4,-9.6],[-152.7,-13.2],[-157.3,-10.3],[-155.3,-6.8],[-176.8,5.6],[-179.2,2.6],[-185.4,6.4],[-183.6,8.8],[-195.8,14.5],[-199.5,10.5],[-199.9,7.7],[-202.2,-6.5],[-200.8,-6.7]];
// Plaza de Armas merged with the footprint of the Torre de la Vela (edges flagged silent have no wall face of their own).
const VELA={x0:-239.4,x1:-222.2,z0:14.2,z1:34.1};
const HOLE=[[-142.4,-10.8],[-145.3,-9.2],[-172.6,6.4],[-197,17.9],[-222.2,23.8],[-222.2,VELA.z0,1],[VELA.x0,VELA.z0,1],[VELA.x0,VELA.z1,1],[VELA.x1,VELA.z1,1],[-221.6,36.4],[-198.7,36.4],[-147.1,36.1],[-146.9,33.6],[-144.6,33.9],[-143.5,18.7],[-142.4,2.7],[-142.4,-9.4]];
const TOWERS={
  homenaje:{pts:[[-142.4,-9.4],[-131.6,-9.4],[-131.6,-21.3],[-142.4,-21.3]],top:25,lime:'A'},
  quebrada:{pts:[[-143.5,2.7],[-133.3,3.4],[-134.4,19.4],[-143.5,18.7]],top:23,lime:'B'},
  hueca:{pts:[[-147.1,33.6],[-137.8,34.5],[-138.7,44.3],[-147.8,43.5]],top:16.2,lime:'A'},
  alquiza:{pts:[[-179.2,2.6],[-185.4,6.4],[-183.6,8.8],[-176.8,5.6]],top:14.3,lime:null},
  criado:{pts:[[-157.3,-10.3],[-152.7,-13.2],[-150.4,-9.6],[-155.3,-6.8]],top:13.4,lime:null},
  sultana:{pts:[[-207.5,37.1],[-198.7,37.1],[-198.7,41.5],[-207.5,41.5]],top:13.6,lime:'B'},
  polvora:{pts:[[-228.5,45.2],[-229,53],[-221,53.5],[-220.5,45.7]],top:15,lime:null},
  armas:{pts:[[-212,-14.3],[-202.3,-15.9],[-200.8,-6.7],[-210.4,-4.7]],top:17,lime:null},
  hidalgos:{pts:[[-239.8,.5],[-250,1.6],[-248.7,13.5],[-238.4,12.3]],top:14.6,lime:null,full:true},
  cubo:{pts:[[-125.3,-34.9],[-123.4,-33.8],[-121.7,-31.6],[-121.5,-28.4],[-121.8,-23.5],[-134.8,-23.5],[-134.8,-28.6],[-134.8,-30.9],[-133.7,-32.9],[-132.3,-34.3],[-130,-35.3]],top:12.4,lime:null,full:true,round:true},
};

// ======================================================================= math / noise
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v)),lerp=(a,b,t)=>a+(b-a)*t;
const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t);};
function rng(seed){let s=seed>>>0;return()=>{s=(Math.imul(1664525,s)+1013904223)>>>0;return s/4294967296;};}
function h3(x,y,z){let h=Math.imul(x|0,374761393)^Math.imul(y|0,668265263)^Math.imul(z|0,1274126177);h=Math.imul(h^(h>>>13),1274126177);h^=h>>>16;return (h>>>0)/4294967296;}
function vn(x,y,z){const ix=Math.floor(x),iy=Math.floor(y),iz=Math.floor(z),fx=x-ix,fy=y-iy,fz=z-iz,u=fx*fx*(3-2*fx),v=fy*fy*(3-2*fy),w=fz*fz*(3-2*fz);
  const a=lerp(lerp(h3(ix,iy,iz),h3(ix+1,iy,iz),u),lerp(h3(ix,iy+1,iz),h3(ix+1,iy+1,iz),u),v),c=lerp(lerp(h3(ix,iy,iz+1),h3(ix+1,iy,iz+1),u),lerp(h3(ix,iy+1,iz+1),h3(ix+1,iy+1,iz+1),u),v);return lerp(a,c,w);}
const fbm=(x,y,z,o=3)=>{let s=0,a=.5,f=1,n=0;for(let i=0;i<o;i++){s+=a*vn(x*f,y*f,z*f);n+=a;a*=.5;f*=2.03;}return s/n;};
function inside(x,z,poly){let r=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>z)!==(b[1]>z)&&x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0])r=!r;}return r;}
function distSeg(x,z,a,b){const dx=b[0]-a[0],dz=b[1]-a[1],l=dx*dx+dz*dz,t=l?clamp(((x-a[0])*dx+(z-a[1])*dz)/l,0,1):0;return Math.hypot(x-a[0]-dx*t,z-a[1]-dz*t);}
function distPoly(x,z,poly,closed=true){let d=1e9;const n=closed?poly.length:poly.length-1;for(let i=0;i<n;i++)d=Math.min(d,distSeg(x,z,poly[i],poly[(i+1)%poly.length]));return d;}

// ground below the plateau, from the IGN 5 m DEM (metres relative to the Alhambra plateau)
let demArr=null;
function dem(x,z){
  if(!demArr){const bin=atob(DEM.b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);demArr=new Int16Array(u.buffer);}
  const fx=clamp((x-DEM.x0)/DEM.d,0,DEM.nx-1.001),fz=clamp((z-DEM.z0)/DEM.d,0,DEM.nz-1.001),ix=Math.floor(fx),iz=Math.floor(fz),tx=fx-ix,tz=fz-iz,g=(i,j)=>demArr[j*DEM.nx+i]/5;
  return lerp(lerp(g(ix,iz),g(ix+1,iz),tx),lerp(g(ix,iz+1),g(ix+1,iz+1),tx),tz);
}
let PER=null;
// y of the foot of a wall face at (x,z): inside the enclosure the plateau is flat, on the perimeter the face follows the slope
function footAt(x,z){
  const d=distPoly(x,z,PER),inn=inside(x,z,PER);
  let m=dem(x,z);for(let k=0;k<8;k++){const a=k*Math.PI/4;m=Math.min(m,dem(x+Math.cos(a)*3.5,z+Math.sin(a)*3.5));}
  const slope=Math.min(m,-.6)-1.4;
  if(!inn)return Math.min(slope,-2);
  return lerp(slope,-.35,smooth(1.2,4.2,d));
}

// ======================================================================= mesh accumulation
const MI={};let ACC=new Map(),TRIS=0;
function accFor(mat,x,z){const cx=Math.floor((x+330)/60),cz=Math.floor((z+100)/60),key=mat+'|'+cx+'_'+cz;let a=ACC.get(key);if(!a){a={mat,zone:'alc'+cx+'_'+cz,p:[],n:[],uv:[],c:MI[mat].vc?[]:null};ACC.set(key,a);}return a;}
function vtx(a,p,n,u,v,c){a.p.push(p[0],p[1],p[2]);a.n.push(n[0],n[1],n[2]);a.uv.push(u,v);if(a.c)a.c.push(c?c[0]:1,c?c[1]:1,c?c[2]:1);}
function tri(a,p0,p1,p2,n0,n1,n2,t0,t1,t2,c0,c1,c2){vtx(a,p0,n0,t0[0],t0[1],c0);vtx(a,p1,n1,t1[0],t1[1],c1);vtx(a,p2,n2,t2[0],t2[1],c2);TRIS++;}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const norm=v=>{const l=Math.hypot(v[0],v[1],v[2])||1;return [v[0]/l,v[1]/l,v[2]/l];};
// quad p0..p3 (any winding); wound counter-clockwise as seen from n
function quad(a,p0,p1,p2,p3,n,t0,t1,t2,t3,c){
  if(dot(cross(sub(p1,p0),sub(p2,p0)),n)<0){[p1,p3]=[p3,p1];[t1,t3]=[t3,t1];}
  tri(a,p0,p1,p2,n,n,n,t0,t1,t2,c,c,c);tri(a,p0,p2,p3,n,n,n,t0,t2,t3,c,c,c);
}
function flush(b){
    for(const a of ACC.values()){
    if(!a.p.length)continue;{let bad=0;for(let i=0;i<a.p.length;i++)if(!Number.isFinite(a.p[i])||(i<a.n.length&&!Number.isFinite(a.n[i])))bad++;if(bad)console.log('ALC NaN',a.mat,a.zone,bad);}const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(a.p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(a.n,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(a.uv,2));
    if(a.c)g.setAttribute('color',new THREE.Float32BufferAttribute(a.c,3));
    b.zone=a.zone;b.unique(g,a.mat);
  }
  ACC.clear();
}

// ======================================================================= surface tints (vertex colours: weathering that never repeats)
function tinter(kind,seed=0){
  const s=seed*7.13;
  return (x,y,z)=>{
    const big=fbm(x*.07+s,y*.1,z*.07)-.5,mid=fbm(x*.19,y*.17+s,z*.19)-.5,
      streak=vn((x+z)*.21+s,y*.035,0),drip=smooth(.62,.9,streak),
      base=1+big*.26+mid*.1-drip*.12;
    const low=smooth(-5,2.5,y),damp=1-.14*(1-low);
    let r=base*damp,g=base*damp,b=base*damp;
    if(kind==='lime'){const warm=fbm(x*.12,y*.2+s,z*.12)-.5;r*=1.02+warm*.06;b*=.98-warm*.07;}
    else if(kind==='tapial'){const warm=fbm(x*.11,y*.2,z*.11+s)-.5;r*=1.03+warm*.12;g*=1+warm*.03;b*=.96-warm*.1;}
    else if(kind==='ground'){const w=fbm(x*.05+s,0,z*.05)-.5,f=fbm(x*.31,0,z*.31)-.5;const k=1+w*.28+f*.10;r=g=b=k;g*=1-w*.05;b*=1-w*.12;}
    return [clamp(r,.5,1.4),clamp(g,.5,1.4),clamp(b,.5,1.4)];
  };
}

// ======================================================================= wall faces
const uniq=(a,eps)=>{const r=[];for(const v of a)if(!r.length||v-r[r.length-1]>eps)r.push(v);return r;};
// One planar-ish face along the edge A→B whose outward normal is the LEFT normal (-dz,dx). The foot follows the ground,
// the face may batter (bat), is displaced a little along the mitre vector so neighbouring faces stay joined, and can have
// rectangular openings with reveals.
function faceGrid(o){
  const {A,B,mA,mB,top}=o,foot=o.foot||(()=>0),dx=B[0]-A[0],dz=B[1]-A[1],L=Math.hypot(dx,dz);if(L<.05)return;
  const tx=dx/L,tz=dz/L,nx=-tz,nz=tx,ds=o.ds||1.4,dt=o.dt||1.5,bat=o.bat||(()=>0),dispA=o.disp??.04,holes=o.holes||[],tint=o.tint,uBase=o.u0||0;
  const nu=Math.max(1,Math.ceil(L/ds));let us=[0,L];for(let i=1;i<nu;i++)us.push(L*i/nu);for(const h of holes)us.push(clamp(h.u0,0,L),clamp(h.u1,0,L));
  us=uniq(us.sort((p,q)=>p-q),.02);
  const cols=us.map(u=>{const t=u/L,x=A[0]+dx*t,z=A[1]+dz*t;return {u,x,z,mx:lerp(mA[0],mB[0],t),mz:lerp(mA[1],mB[1],t),f:Math.min(foot(x,z),top-.05)};});
  const fmin=Math.min(...cols.map(c=>c.f));let ys=[fmin,top];
  if(o.rows)ys.push(...o.rows(fmin,top));else for(let k=Math.ceil(fmin/dt);k*dt<top;k++)ys.push(k*dt);
  if(o.ySplit!==undefined)ys.push(o.ySplit);for(const h of holes)ys.push(h.y0,h.y1);
  ys=uniq(ys.filter(y=>y>=fmin-1e-6&&y<=top+1e-6).sort((p,q)=>p-q),.02);
  const P=[],N=[];
  for(let i=0;i<cols.length;i++){const c=cols[i];P.push([]);
    for(let j=0;j<ys.length;j++){
      const yy=clamp(ys[j],c.f,top),k=bat(yy),fade=smooth(top,top-.7,yy)*smooth(c.f-.01,c.f+.6,yy)*0+smooth(top+.001,top-.6,yy);
      const d=(dispA?dispA*(fbm(c.x*.09,yy*.08,c.z*.09,1)*2-1)*fade:0)+(o.relief?o.relief(yy,c.x,c.z)*fade:0);
      P[i].push([c.x+c.mx*(k+d),yy,c.z+c.mz*(k+d)]);
    }}
  for(let i=0;i<cols.length;i++){N.push([]);for(let j=0;j<ys.length;j++){
    const a=P[Math.max(0,i-1)][j],b=P[Math.min(cols.length-1,i+1)][j],c=P[i][Math.max(0,j-1)],d=P[i][Math.min(ys.length-1,j+1)];
    let n=cross(sub(b,a),sub(d,c));if(Math.hypot(n[0],n[1],n[2])<1e-7)n=[nx,0,nz];n=norm(n);if(n[0]*nx+n[2]*nz<0)n=[-n[0],-n[1],-n[2]];N[i].push(n);}}
  const colr=(p)=>tint?tint(p[0],p[1],p[2]):null;
  for(let i=0;i<cols.length-1;i++){
    const uc=(cols[i].u+cols[i+1].u)/2;
    for(let j=0;j<ys.length-1;j++){
      const yc=(ys[j]+ys[j+1])/2;
      let skip=false;for(const h of holes)if(uc>h.u0&&uc<h.u1&&yc>h.y0&&yc<h.y1){skip=true;break;}
      if(skip)continue;
      const p00=P[i][j],p10=P[i+1][j],p11=P[i+1][j+1],p01=P[i][j+1];
      if(p00[1]>=p01[1]-1e-5&&p10[1]>=p11[1]-1e-5)continue;
      const mat=(o.matLow&&yc<(o.ySplit??0))?o.matLow:o.mat,a=accFor(mat,p00[0],p00[2]);
      const t00=[uBase+cols[i].u,p00[1]],t10=[uBase+cols[i+1].u,p10[1]],t11=[uBase+cols[i+1].u,p11[1]],t01=[uBase+cols[i].u,p01[1]];
      tri(a,p00,p10,p11,N[i][j],N[i+1][j],N[i+1][j+1],t00,t10,t11,colr(p00),colr(p10),colr(p11));
      tri(a,p00,p11,p01,N[i][j],N[i+1][j+1],N[i][j+1],t00,t11,t01,colr(p00),colr(p11),colr(p01));
    }}
  // reveals of the openings
  const face=(u,y)=>{const t=u/L,k=bat(y);return [A[0]+dx*t+lerp(mA[0],mB[0],t)*k,y,A[1]+dz*t+lerp(mA[1],mB[1],t)*k];};
  for(const h of holes){
    if(h.noReveal)continue;
    const dep=h.depth??.8,back=h.back??true,m=o.mat,ac=accFor(o.matLow&&h.y1<(o.ySplit??0)?o.matLow:m,face(h.u0,h.y0)[0],face(h.u0,h.y0)[2]),dark=[.62,.58,.55];
    const inw=(p)=>[p[0]-nx*dep,p[1],p[2]-nz*dep];
    const f00=face(h.u0,h.y0),f10=face(h.u1,h.y0),f11=face(h.u1,h.y1),f01=face(h.u0,h.y1);
    const uvw=(u,d)=>[uBase+u,d];
    quad(ac,f00,f01,inw(f01),inw(f00),[tx,0,tz],uvw(h.u0,0),uvw(h.u0,0),uvw(h.u0,dep),uvw(h.u0,dep),dark);
    quad(ac,f10,f11,inw(f11),inw(f10),[-tx,0,-tz],uvw(h.u1,0),uvw(h.u1,0),uvw(h.u1,dep),uvw(h.u1,dep),dark);
    quad(ac,f00,f10,inw(f10),inw(f00),[0,1,0],uvw(h.u0,0),uvw(h.u1,0),uvw(h.u1,dep),uvw(h.u0,dep),[.8,.78,.74]);
    quad(ac,f01,f11,inw(f11),inw(f01),[0,-1,0],uvw(h.u0,0),uvw(h.u1,0),uvw(h.u1,dep),uvw(h.u0,dep),[.5,.48,.46]);
    if(back){const bm=accFor('alcDark',f00[0],f00[2]);quad(bm,inw(f00),inw(f10),inw(f11),inw(f01),[nx,0,nz],[0,0],[1,0],[1,1],[0,1],null);}
  }
}
// Horizontal ribbon / thin prism along an edge between mitre offsets o0<o1 (positive = outward), from y0 up to y1.
function prism(e,o0,o1,y0,y1,mat,tint,o={}){
  const {A,B,mA,mB}=e,dx=B[0]-A[0],dz=B[1]-A[1],L=Math.hypot(dx,dz);if(L<.03)return;const tx=dx/L,tz=dz/L,nx=-tz,nz=tx,a=accFor(mat,(A[0]+B[0])/2,(A[1]+B[1])/2);
  const P=(side,u,y)=>{const m=u?mB:mA,b=u?B:A,off=side?o1:o0;return [b[0]+m[0]*off,y,b[1]+m[1]*off];};
  const uA=(o.u0||0),uB=uA+L,col=tint?tint((A[0]+B[0])/2,y1,(A[1]+B[1])/2):null,c=col,w=o1-o0;
  const topN=[0,1,0];
  if(!o.noTop)quad(a,P(0,0,y1),P(1,0,y1),P(1,1,y1),P(0,1,y1),topN,[uA,0],[uA,w],[uB,w],[uB,0],c);
  if(!o.noOuter)quad(a,P(1,0,y0),P(1,1,y0),P(1,1,y1),P(1,0,y1),[nx,0,nz],[uA,y0],[uB,y0],[uB,y1],[uA,y1],c);
  if(!o.noInner)quad(a,P(0,0,y0),P(0,1,y0),P(0,1,y1),P(0,0,y1),[-nx,0,-nz],[uA,y0],[uB,y0],[uB,y1],[uA,y1],c);
}
// edges of a closed path oriented so that the left normal points outward (out=true) or inward (out=false)
function orient(path,out){
  const n=path.length,p0=path[0],p1=path[1],mx=(p0[0]+p1[0])/2,mz=(p0[1]+p1[1])/2,L=Math.hypot(p1[0]-p0[0],p1[1]-p0[1]),lx=-(p1[1]-p0[1])/L,lz=(p1[0]-p0[0])/L;
  const leftInside=inside(mx+lx*.05,mz+lz*.05,path);
  const pts=(leftInside===out)?path.slice().reverse().map((p,i)=>({p,i:n-1-i})):path.map((p,i)=>({p,i}));
  const edges=[];
  const nrm=(a,b)=>{const dx=b[0]-a[0],dz=b[1]-a[1],l=Math.hypot(dx,dz)||1;return [-dz/l,dx/l];};
  const mit=(i)=>{const a=pts[(i+n-1)%n].p,b=pts[i].p,c=pts[(i+1)%n].p,n1=nrm(a,b),n2=nrm(b,c);let sx=n1[0]+n2[0],sz=n1[1]+n2[1];const l=Math.hypot(sx,sz);if(l<1e-4)return n1;sx/=l;sz/=l;const k=1/Math.max(.42,sx*n1[0]+sz*n1[1]);return [sx*Math.min(k,2.4),sz*Math.min(k,2.4)];};
  for(let i=0;i<n;i++){const a=pts[i],b=pts[(i+1)%n];edges.push({A:a.p,B:b.p,mA:mit(i),mB:mit((i+1)%n),idx:a.i,idx2:b.i});}
  return edges;
}
const edgeLen=e=>Math.hypot(e.B[0]-e.A[0],e.B[1]-e.A[1]);


// row spacing and relief that follow the texture structure so lifts and bands cast real shadows
const stepRows=(dt,lowDt=1.7,lowY=-2.5,off=0)=>(a,b)=>{const r=[];for(let k=Math.ceil((Math.max(a,lowY)-off)/dt);k*dt+off<b;k++)r.push(k*dt+off);for(let k=Math.ceil((a-off)/lowDt);k*lowDt+off<lowY;k++)r.push(k*lowDt+off);return r;};
const ROWS={tapial:stepRows(.425),lime:stepRows(.5625),bc:(a,b)=>{const r=[];for(let k=Math.floor(Math.max(a,-2.5)/.5);k*.5<b;k++){r.push(k*.5,k*.5+.227);}for(let k=Math.ceil(a/1.5);k*1.5<-2.5;k++)r.push(k*1.5);return r;},brick:stepRows(1.2)};
const fadeLow=y=>smooth(-7,-1,y);
const RELIEF={
  tapial:y=>{const p=((y/.85)%1+1)%1;return (-.03+.042*(1-Math.abs(2*p-1)))*fadeLow(y);},
  lime:y=>{const p=((y/.5625)%1+1)%1;return (-.018+.03*(1-Math.abs(2*p-1)))*fadeLow(y);},
  bc:y=>{const p=((y/.5)%1+1)%1;return (p<.454?.016:-.004)*fadeLow(y);},
  brick:()=>0};
const kindOf=m=>m.startsWith('alcTapial')?'tapial':m.startsWith('alcLime')?'lime':m.startsWith('alcBc')?'bc':'brick';
const surf=(m,extra={})=>({mat:m,rows:ROWS[kindOf(m)],relief:RELIEF[kindOf(m)],ds:1.0,...extra});

// ======================================================================= merlons (Nasrid: prismatic with pyramidal cap)
function merlonGeo(b){return b.geometry('alc-merlon',()=>{
  const w=.62,d=.5,h=.85,ch=.3,ov=.05,pos=[],nor=[],uv=[];
  const q=(p0,p1,p2,p3,n,u0,u1)=>{for(const k of [0,1,2,0,2,3]){const p=[p0,p1,p2,p3][k];pos.push(...p);nor.push(...n);uv.push(p[0]+p[2]+u0,p[1]*1+u1);}};
  const X=w/2,Z=d/2,Xc=X+ov,Zc=Z+ov;
  q([-X,0,Z],[X,0,Z],[X,h,Z],[-X,h,Z],[0,0,1],0,0);q([X,0,-Z],[-X,0,-Z],[-X,h,-Z],[X,h,-Z],[0,0,-1],0,0);q([X,0,Z],[X,0,-Z],[X,h,-Z],[X,h,Z],[1,0,0],0,0);q([-X,0,-Z],[-X,0,Z],[-X,h,Z],[-X,h,-Z],[-1,0,0],0,0);
  // cap: small ledge then pyramid
  const lh=.07;q([-Xc,h,Zc],[Xc,h,Zc],[Xc,h+lh,Zc],[-Xc,h+lh,Zc],[0,0,1],0,0);q([Xc,h,-Zc],[-Xc,h,-Zc],[-Xc,h+lh,-Zc],[Xc,h+lh,-Zc],[0,0,-1],0,0);q([Xc,h,Zc],[Xc,h,-Zc],[Xc,h+lh,-Zc],[Xc,h+lh,Zc],[1,0,0],0,0);q([-Xc,h,-Zc],[-Xc,h,Zc],[-Xc,h+lh,Zc],[-Xc,h+lh,-Zc],[-1,0,0],0,0);
  q([-Xc,h,Zc],[Xc,h,Zc],[Xc,h,Z],[-Xc,h,Z],[0,-1,0],0,0);
  const t=h+lh,ap=[0,t+ch,0],tri3=(a,b,c)=>{const n=norm(cross(sub(b,a),sub(c,a)));for(const p of [a,b,c]){pos.push(...p);nor.push(...n);uv.push(p[0]+p[2],p[1]);}};
  const c=[[-Xc,t,Zc],[Xc,t,Zc],[Xc,t,-Zc],[-Xc,t,-Zc]];
  tri3(c[0],c[1],ap);tri3(c[1],c[2],ap);tri3(c[2],c[3],ap);tri3(c[3],c[0],ap);
  q([-Xc,t,Zc],[Xc,t,Zc],[Xc,t,-Zc],[-Xc,t,-Zc],[0,1,0],0,0);
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));return g;});}
function merlons(b,e,off,y,mat,pitch=1.3,sc=1){
  const L=edgeLen(e);if(L<1.6)return;const n=Math.max(1,Math.round((L-.5)/pitch)),sp=L/n,tx=(e.B[0]-e.A[0])/L,tz=(e.B[1]-e.A[1])/L,rot=-Math.atan2(tz,tx),g=merlonGeo(b);
  for(let i=0;i<n;i++){const t=(i+.5)*sp/L,x=lerp(e.A[0],e.B[0],t)+lerp(e.mA[0],e.mB[0],t)*off,z=lerp(e.A[1],e.B[1],t)+lerp(e.mA[1],e.mB[1],t)*off;b.add(g,mat,[x,y,z],[sc,sc,sc],rot);}
}

// ======================================================================= materials
export async function materials(M){
  const load=async f=>{const i=new Image();i.src=`textures/alcazaba/${f}.jpg`;await i.decode();return i;};
  const defs=[['alcTapialA','alc-tapial-a',4,3.4,.95,1.2],['alcTapialB','alc-tapial-b',4,3.4,.95,1.2],['alcTapialC','alc-tapial-c',4,3.4,.95,1.2],
    ['alcLimeA','alc-lime-a',4.5,3.375,.92,1],['alcLimeB','alc-lime-b',4.5,3.375,.92,1],
    ['alcBcA','alc-brickcobble-a',4,3,.9,.7],['alcBcB','alc-brickcobble-b',4,3,.9,1.1],
    ['alcBrickA','alc-brick-a',4,4,.88,.9],['alcBrickB','alc-brick-b',4,4,.88,.9],
    ['alcRubble','alc-rubble',4,2,.97,1.6],['alcGravel','alc-gravel',4,4,.98,1.2],['alcEarth','alc-earth',4,4,.99,1],['alcCobble','alc-cobble',4,4,.95,1.4],['alcCoping','alc-coping',2,2,.95,.6],['alcGrass','alc-grass',4,4,1,.7]];
  await Promise.all(defs.map(async ([name,file,w,h,rough,bs])=>{
    const [img,himg]=await Promise.all([load(file),load(file+'-h')]);
    const tex=(i,srgb)=>{const t=new THREE.Texture(i);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=srgb?THREE.SRGBColorSpace:THREE.NoColorSpace;t.anisotropy=8;t.repeat.set(1/w,1/h);t.needsUpdate=true;return t;};
    const m=new THREE.MeshStandardMaterial({map:tex(img,true),bumpMap:tex(himg,false),bumpScale:bs,roughness:rough,metalness:0,vertexColors:true,color:name==='alcCoping'?0xe2d6c4:0xffffff});
    m.name=name;m.userData={scale:1};M[name]=m;MI[name]={vc:true};
    const p=m.clone();p.vertexColors=false;p.name=name+'P';p.userData={scale:1};M[name+'P']=p;MI[name+'P']={vc:false};
  }));
  const dark=new THREE.MeshStandardMaterial({color:0x2a1f18,roughness:1});dark.name='alcDark';dark.userData={scale:1};M.alcDark=dark;MI.alcDark={vc:false};
  const darkP=new THREE.MeshStandardMaterial({color:0x1d1510,roughness:1,side:THREE.DoubleSide});darkP.name='alcDarkP';darkP.userData={scale:1};M.alcDarkP=darkP;MI.alcDarkP={vc:false};
  const water=new THREE.MeshStandardMaterial({color:0x34493f,roughness:.12,metalness:.15,transparent:true,opacity:.9});water.name='alcWater';water.userData={scale:1};M.alcWater=water;MI.alcWater={vc:false};
  const core=new THREE.MeshStandardMaterial({color:0x6f8c4f,roughness:.97});core.name='alcHedgeCore';core.userData={scale:1};M.alcHedgeCore=core;MI.alcHedgeCore={vc:false};
  const crackM=new THREE.MeshStandardMaterial({color:0x4a382c,roughness:1,side:THREE.DoubleSide});crackM.name='alcCrackP';crackM.userData={scale:1};M.alcCrackP=crackM;MI.alcCrackP={vc:false};
  const bronze=new THREE.MeshStandardMaterial({color:0x5d5030,roughness:.42,metalness:.75});bronze.name='alcBronze';bronze.userData={scale:1};M.alcBronze=bronze;MI.alcBronze={vc:false};
  const flag=(name,draw)=>{const c=document.createElement('canvas');c.width=96;c.height=64;draw(c.getContext('2d'));const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;const m=new THREE.MeshStandardMaterial({map:t,roughness:.85,side:THREE.DoubleSide});m.name=name;m.userData={scale:1};M[name]=m;MI[name]={vc:false};};
  flag('alcFlag0',g=>{g.fillStyle='#0d3f94';g.fillRect(0,0,96,64);g.fillStyle='#f2c500';for(let i=0;i<12;i++){const a=i/12*Math.PI*2;g.beginPath();g.arc(48+Math.cos(a)*18,32+Math.sin(a)*18,2.4,0,7);g.fill();}});
  flag('alcFlag1',g=>{g.fillStyle='#0a7a3d';g.fillRect(0,0,96,64);g.fillStyle='#f4f4ee';g.fillRect(0,21,96,22);});
  flag('alcFlag2',g=>{g.fillStyle='#c4161c';g.fillRect(0,0,96,64);g.fillStyle='#f6c315';g.fillRect(0,16,96,32);});
  flag('alcFlag3',g=>{g.fillStyle='#bd2a3c';g.fillRect(0,0,96,64);g.fillStyle='#e6c24a';g.beginPath();g.arc(48,32,9,0,7);g.fill();});
}

// ======================================================================= solids
// axis-aligned block without a bottom: four sides + top, UV in metres
function boxMesh(x0,y0,z0,x1,y1,z1,mat,tint,o={}){
  const a=accFor(mat,(x0+x1)/2,(z0+z1)/2),cx=(x0+x1)/2,cz=(z0+z1)/2,c=o.col||(tint?tint(cx,(y0+y1)/2,cz):null),k=o.k||[1,1,1],cc=c?[c[0]*k[0],c[1]*k[1],c[2]*k[2]]:null;
  const u0=o.u0||0;
  if(!o.noSides){
  quad(a,[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],[0,0,1],[x0,y0],[x1,y0],[x1,y1],[x0,y1],cc);
  quad(a,[x1,y0,z0],[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[0,0,-1],[x1,y0],[x0,y0],[x0,y1],[x1,y1],cc);
  quad(a,[x1,y0,z1],[x1,y0,z0],[x1,y1,z0],[x1,y1,z1],[1,0,0],[z1,y0],[z0,y0],[z0,y1],[z1,y1],cc);
  quad(a,[x0,y0,z0],[x0,y0,z1],[x0,y1,z1],[x0,y1,z0],[-1,0,0],[z0,y0],[z1,y0],[z1,y1],[z0,y1],cc);}
  if(!o.noTop)quad(a,[x0,y1,z0],[x1,y1,z0],[x1,y1,z1],[x0,y1,z1],[0,1,0],[x0,z0],[x1,z0],[x1,z1],[x0,z1],cc);
}
function groundTri(a,p0,p1,p2,tint){if(cross(sub(p1,p0),sub(p2,p0))[1]<0)[p1,p2]=[p2,p1];tri(a,p0,p1,p2,[0,1,0],[0,1,0],[0,1,0],[p0[0],p0[2]],[p1[0],p1[2]],[p2[0],p2[2]],tint(p0[0],0,p0[2]),tint(p1[0],0,p1[2]),tint(p2[0],0,p2[2]));}
function fillPoly(poly,holes,y,mat,tint,down=false){
  const C=poly.map(p=>new THREE.Vector2(p[0],p[1])),H=holes.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1])));
  const all=C.concat(...H);
  for(const [i,j,k] of THREE.ShapeUtils.triangulateShape(C,H)){
    const p=[all[i],all[j],all[k]].map(v=>[v.x,y,v.y]);const n=cross(sub(p[1],p[0]),sub(p[2],p[0]));if((n[1]<0)!==down)p.reverse();
    const a=accFor(mat,p[0][0],p[0][2]),nn=[0,down?-1:1,0];
    tri(a,p[0],p[1],p[2],nn,nn,nn,[p[0][0],p[0][2]],[p[1][0],p[1][2]],[p[2][0],p[2][2]],tint(p[0][0],0,p[0][2]),tint(p[1][0],0,p[1][2]),tint(p[2][0],0,p[2][2]));
  }
}

// ======================================================================= curtain walls (open polylines along the enclosure perimeter)
function curtain(b,path,o){
  // left normal must point away from the enclosure
  const mid=[(path[0][0]+path[1][0])/2,(path[0][1]+path[1][1])/2],L=Math.hypot(path[1][0]-path[0][0],path[1][1]-path[0][1]),lx=-(path[1][1]-path[0][1])/L,lz=(path[1][0]-path[0][0])/L;
  if(inside(mid[0]+lx*.1,mid[1]+lz*.1,PER))path=path.slice().reverse();
  const n=path.length,nrm=(a,c)=>{const dx=c[0]-a[0],dz=c[1]-a[1],l=Math.hypot(dx,dz)||1;return [-dz/l,dx/l];};
  const mit=i=>{const n1=i>0?nrm(path[i-1],path[i]):nrm(path[i],path[i+1]),n2=i<n-1?nrm(path[i],path[i+1]):n1;let sx=n1[0]+n2[0],sz=n1[1]+n2[1];const l=Math.hypot(sx,sz);if(l<1e-4)return n1;sx/=l;sz/=l;const k=Math.min(2.4,1/Math.max(.42,sx*n1[0]+sz*n1[1]));return [sx*k,sz*k];};
  const T=o.T||2.4,top=o.top,tint=o.tint,par=o.par??.5;let u=o.u0||0;
  for(let i=0;i<n-1;i++){
    const e={A:path[i],B:path[i+1],mA:mit(i),mB:mit(i+1)},len=edgeLen(e);if(len<.2)continue;
    faceGrid({...e,...surf(o.mat),matLow:o.matLow||o.mat,ySplit:-3,top,foot:footAt,bat:y=>(o.batter??.06)*(top-y),tint,u0:u});
    // inner face (towards the enclosure)
    const ia=[e.A[0]-e.mA[0]*T,e.A[1]-e.mA[1]*T],ib=[e.B[0]-e.mB[0]*T,e.B[1]-e.mB[1]*T];
    if((o.parIn??.5)>.01)faceGrid({A:ib,B:ia,mA:[-e.mB[0],-e.mB[1]],mB:[-e.mA[0],-e.mA[1]],...surf(o.matIn||o.mat),top:top+(o.parIn??.5),foot:()=>0,bat:y=>.02*(top-y),tint,u0:u});
    {const bt=(o.batter??.06),bf=y=>bt*(top-y),mid=[(e.A[0]+e.B[0])/2,(e.A[1]+e.B[1])/2],ft=footAt(mid[0],mid[1]);
      if(top-ft>7)prism(e,bf(top-3.2)-.12,bf(top-3.2)+.13,top-3.45,top-3.15,'alcCoping',tint,{noInner:true,u0:u});
      if(len>9&&top-ft>11){const n=Math.floor(len/11);for(let k=0;k<n;k++){const uu=(k+.5)*len/n,px=lerp(e.A[0],e.B[0],uu/len),pz=lerp(e.A[1],e.B[1],uu/len);buttress(e,uu,1.5,.85,footAt(px,pz)-.6,top-.35,bf,o.mat,tint);}}}
    prism(e,-T,0,top-.3,top,'alcCobble',tint,{noOuter:true,noInner:true,u0:u});
    prism(e,-.5,0,top,top+par,o.mat,tint,{noTop:true,noOuter:true,u0:u});
    prism(e,-.58,.07,top+par,top+par+.1,'alcCoping',tint,{});
    if(o.merl)merlons(b,e,-.25,top+par+.1,o.mat+'P');
    if(o.parBlock)b.nav.box((e.A[0]+e.B[0])/2+((e.mA[0]+e.mB[0])/2)*-.25,(e.A[1]+e.B[1])/2+((e.mA[1]+e.mB[1])/2)*-.25,len+.3,.6,top,top+1.2,-Math.atan2(e.B[1]-e.A[1],e.B[0]-e.A[0]));
    if((o.parIn??.5)>.01)prism({A:ia,B:ib,mA:[-e.mA[0],-e.mA[1]],mB:[-e.mB[0],-e.mB[1]]},0,.45,top,top+(o.parIn??.5),o.matIn||o.mat,tint,{noOuter:true,noInner:true});
    blockEdge(b,e,.25,T+.25,-45,top);
    u+=len;
  }
}

// ======================================================================= barrio castrense: excavated houses
const PLAZA=[[-142.4,-10.8],[-145.3,-9.2],[-172.6,6.4],[-197,17.9],[-222.2,23.8],[-222.2,34.1],[-221.6,36.4],[-198.7,36.4],[-147.1,36.1],[-146.9,33.6],[-144.6,33.9],[-143.5,18.7],[-142.4,2.7],[-142.4,-9.4]];
const northWall=x=>x>-197?17.9+(x+197)*(-.524):17.9+(x+197)*(-.234);
function layoutHouses(){
  const r=rng(77),plots=[],G=1.5;
  let x=-219;
  while(x<-166){
    const w=[6,7.5,9,7.5][Math.floor(r()*4)],x1=Math.min(x+w,-165),wz=Math.max(northWall(x),northWall(x1));let z0=Math.ceil((wz+2.7)/G)*G;
    if(25.5-z0>=4.5)plots.push({x0:x,x1,z0,z1:25.5,band:'N'});
    x=x1+(r()<.18?G*2:0);
  }
  x=-219;
  while(x<-178){
    const w=[6,7.5,9,7.5][Math.floor(r()*4)],x1=Math.min(x+w,-177);
    plots.push({x0:x,x1,z0:28.5,z1:r()<.3?33:34.5,band:'S'});
    x=x1+(r()<.18?G*2:0);
  }
  return plots;
}
function houses(b,gT){
  const plots=layoutHouses(),r=rng(31),T=.55,wallTint=tinter('ground',9),G=1.5,segs=new Map(),holes=[],rooms=[];
  const wall=(x0,z0,x1,z1,door,tag)=>{
    const key=[x0,z0,x1,z1].map(v=>v.toFixed(2)).join(',');if(segs.has(key))return;segs.set(key,1);
    const horiz=Math.abs(z1-z0)<1e-6,len=horiz?Math.abs(x1-x0):Math.abs(z1-z0),lo=horiz?Math.min(x0,x1):Math.min(z0,z1);
    const pieces=door?[[0,door[0]],[door[1],len]]:[[0,len]];
    if(door){const a0=lo+door[0],a1=lo+door[1],f0=tag.floor-.08,f1=tag.floor+.05;
      if(horiz)boxMesh(a0,f0,z0-T/2-.12,a1,f1,z0+T/2+.12,'alcCopingP',wallTint,{});else boxMesh(x0-T/2-.12,f0,a0,x0+T/2+.12,f1,a1,'alcCopingP',wallTint,{});}
    for(const [s0,s1] of pieces){
      if(s1-s0<.25)continue;
      // split long walls so that tops and heights vary like real, partly collapsed foundations
      const nseg=Math.max(1,Math.round((s1-s0)/3.2));
      for(let k=0;k<nseg;k++){
        const a0=lo+s0+(s1-s0)*k/nseg,a1=lo+s0+(s1-s0)*(k+1)/nseg,top=.26+r()*.34+(r()<.12?-.2:0),jit=.9+r()*.16,bot=-1.15;
        const fl=tag.floor-.05;
        if(horiz){boxMesh(a0,fl,z0-T/2,a1,top-.06,z0+T/2,'alcRubble',wallTint,{k:[jit,jit,jit]});boxMesh(a0-.01,top-.06,z0-T/2-.025,a1+.01,top,z0+T/2+.025,'alcCoping',wallTint,{});b.nav.box((a0+a1)/2,z0,a1-a0,T,fl,top);}
        else{boxMesh(x0-T/2,fl,a0,x0+T/2,top-.06,a1,'alcRubble',wallTint,{k:[jit,jit,jit]});boxMesh(x0-T/2-.025,top-.06,a0-.01,x0+T/2+.025,top,a1+.01,'alcCoping',wallTint,{});b.nav.box(x0,(a0+a1)/2,T,a1-a0,fl,top);}
      }
    }
  };
  const room=(x0,z0,x1,z1,floorY,mat)=>{rooms.push({x0,z0,x1,z1,floorY,mat});};
  const door=(len,w=1.2)=>{const c=.9+r()*Math.max(.01,len-1.8-w);return [c,c+w];};
  for(const p of plots){
    const W=p.x1-p.x0,D=p.z1-p.z0,N=p.band==='N',streetZ=N?p.z1:p.z0,backZ=N?p.z0:p.z1,dir=N?-1:1;
    holes.push(p);
    const pat=Math.min(4.5,Math.round(D*.4/G)*G),partZ=streetZ+dir*pat;      // patio next to the street, rooms behind
    const fl={patio:-(.18+r()*.2),a:-(.45+r()*.5),b:-(.45+r()*.5),c:-(.4+r()*.4)};
    // perimeter
    wall(p.x0,streetZ,p.x1,streetZ,door(W,1.4),{floor:fl.patio});
    wall(p.x0,backZ,p.x1,backZ,null,{floor:fl.a});
    wall(p.x0,p.z0,p.x0,p.z1,null,{floor:fl.a});wall(p.x1,p.z0,p.x1,p.z1,null,{floor:fl.a});
    // patio / back rooms partition with a doorway, then the back rooms side by side
    wall(p.x0,partZ,p.x1,partZ,door(W,1.1),{floor:fl.a});
    const nb=W>=9?3:2,xs=[p.x0];for(let k=1;k<nb;k++)xs.push(p.x0+Math.round(W*k/nb/G)*G);xs.push(p.x1);
    const zr0=Math.min(partZ,backZ),zr1=Math.max(partZ,backZ);
    for(let k=1;k<nb;k++)wall(xs[k],zr0,xs[k],zr1,door(zr1-zr0,1.0),{floor:fl.b});
    const pz0=Math.min(streetZ,partZ),pz1=Math.max(streetZ,partZ);
    if(W>=7.5&&r()<.5){const cx=p.x0+Math.round(W*.5/G)*G;wall(cx,pz0,cx,pz1,door(pz1-pz0,1.2),{floor:fl.patio});room(p.x0,pz0,cx,pz1,fl.patio,'alcCobble');room(cx,pz0,p.x1,pz1,fl.patio-.1,'alcGravel');}
    else{room(p.x0,pz0,p.x1,pz1,fl.patio,r()<.6?'alcCobble':'alcGravel');
      if(r()<.5&&pat>=3){const wx=(p.x0+p.x1)/2+(r()-.5)*W*.3,wz=(pz0+pz1)/2;   // a well in the patio
        b.cylinder(wx,fl.patio-.05,wz,.62,.85,'alcRubbleP',.62,14);b.cylinder(wx,fl.patio+.78,wz,.7,.08,'alcCopingP',.7,14);b.cylinder(wx,fl.patio+.84,wz,.42,.02,'alcDark',.42,14);b.nav.box(wx,wz,1.4,1.4,fl.patio,fl.patio+.9);}}
    for(let k=0;k<nb;k++)room(xs[k],zr0,xs[k+1],zr1,k===0?fl.a:k===1?fl.b:fl.c,r()<.5?'alcEarth':'alcGravel');
  }
  for(const q of rooms){
    const a=accFor(q.mat,(q.x0+q.x1)/2,(q.z0+q.z1)/2),c=gT((q.x0+q.x1)/2,0,(q.z0+q.z1)/2),sh=[.92,.9,.86];
    quad(a,[q.x0,q.floorY,q.z0],[q.x1,q.floorY,q.z0],[q.x1,q.floorY,q.z1],[q.x0,q.floorY,q.z1],[0,1,0],[q.x0,q.z0],[q.x1,q.z0],[q.x1,q.z1],[q.x0,q.z1],[c[0]*sh[0],c[1]*sh[1],c[2]*sh[2]]);
  }
  return holes;
}

// ======================================================================= ground, paths and gardens
function stripPath(pts,w,mat,tint,y=.02,o={}){
  for(let i=0;i<pts.length-1;i++){
    const a=pts[i],c=pts[i+1],dx=c[0]-a[0],dz=c[1]-a[1],L=Math.hypot(dx,dz);if(L<.05)continue;const nx=-dz/L*w/2,nz=dx/L*w/2,ac=accFor(mat,(a[0]+c[0])/2,(a[1]+c[1])/2);
    const n=Math.max(1,Math.ceil(L/2));
    for(let k=0;k<n;k++){const t0=k/n,t1=(k+1)/n,p0=[a[0]+dx*t0,a[1]+dz*t0],p1=[a[0]+dx*t1,a[1]+dz*t1];
      quad(ac,[p0[0]+nx,y,p0[1]+nz],[p1[0]+nx,y,p1[1]+nz],[p1[0]-nx,y,p1[1]-nz],[p0[0]-nx,y,p0[1]-nz],[0,1,0],[p0[0]+nx,p0[1]+nz],[p1[0]+nx,p1[1]+nz],[p1[0]-nx,p1[1]-nz],[p0[0]-nx,p0[1]-nz],tint(p0[0],0,p0[1]));}
  }
}
function groundGrid(G,x0,x1,z0,z1,incl,matOf,tint,y=0){
  for(let x=x0;x<x1;x+=G)for(let z=z0;z<z1;z+=G){
    const cx=x+G/2,cz=z+G/2;if(!incl(cx,cz))continue;const a=accFor(matOf(cx,cz),cx,cz);
    groundTri(a,[x,y,z],[x+G,y,z],[x+G,y,z+G],tint);groundTri(a,[x,y,z],[x+G,y,z+G],[x,y,z+G],tint);
  }
}
const GARDEN={x0:-198.5,x1:-148.5,z0:40.2,z1:47.4};
function ground(b,holes,gT){
  const warm=(x,y,z)=>{const c=gT(x,y,z);return [c[0]*1.03,c[1],c[2]*.93];};
  // plaza: 1.5 m grid so that the excavated rooms are exact (overshoot hides under the wall mass)
  const G=1.5,inHole=(cx,cz)=>holes.some(p=>cx>p.x0&&cx<p.x1&&cz>p.z0&&cz<p.z1);
  const street=(x,y,z)=>{const c=warm(x,y,z),k=1+.1*(1-smooth(1.2,3,Math.abs(z-27)))*(x<-146?1:0);return [c[0]*k,c[1]*k,c[2]*k];};
  groundGrid(G,-224,-140,-12,40,(cx,cz)=>(inside(cx,cz,PLAZA)||distPoly(cx,cz,PLAZA)<1.4)&&cx>-222.2&&!inHole(cx,cz),()=>'alcGravel',street);
  // barbican, Revellin and the other enclosed ground west of the plaza: dry earth, with cobbled walks
  const ground2=(cx,cz)=>cx<-128&&inside(cx,cz,PER)&&distPoly(cx,cz,PER)>1.7&&(!inside(cx,cz,OUTLINE)||distPoly(cx,cz,OUTLINE)<1.4);
  groundGrid(1.5,-304,-126,-42,62,ground2,(cx,cz)=>(cz>39.5&&cx>-199&&cx<-137)?'alcGravel':(cx<-249&&cz>4)?'alcGrass':'alcEarth',warm);
  stripPath([[-143,26.5],[-160,27],[-190,27],[-221,26.2]],2.0,'alcEarth',(x,y,z)=>{const c=warm(x,y,z);return [c[0]*1.02,c[1]*1.0,c[2]*.97];},.012);
  stripPath([[-134.8,-28.6],[-139.9,-27.3],[-146.9,-23.6],[-199.9,7.7],[-204.9,8.3],[-207.8,-9.1],[-211.1,-8.5]],2.4,'alcCobble',gT);
  stripPath([[-218.9,36.5],[-218,39],[-217.8,40],[-215.6,46.2],[-136.8,47.6],[-136,41.6]],1.6,'alcGravel',street,.03);
  // Jardin de los Adarves: gravel walks, clipped box parterres, a basin
  adarves(b,gT);
}
function hedgeRun(b,x0,z0,x1,z1,seed,h=.62,t=.5){
  const L=Math.hypot(x1-x0,z1-z0),horiz=Math.abs(x1-x0)>Math.abs(z1-z0),cx=(x0+x1)/2,cz=(z0+z1)/2;
  // clipped core (rounded profile) so the hedge reads as a solid green mass, then leaf cards for the broken silhouette
  const w=horiz?L+t:t,d=horiz?t:L+t;
  b.box(cx,0,cz,w*.96,h*.78,d*.96,'alcHedgeCore',0);b.box(cx,h*.62,cz,w*.8,h*.38,d*.8,'alcHedgeCore',0);
  const n=Math.max(2,Math.round(L/.4));
  for(let i=0;i<n;i++){const f=(i+.5)/n,x=lerp(x0,x1,f),z=lerp(z0,z1,f);leaves(b,x,h*.62,z,horiz?L/n*.6:t*.5,h*.38,horiz?t*.5:L/n*.6,LOW?12:34,seed+i*3,.085);}
}
function adarves(b,gT){
  const g=GARDEN,zc=(g.z0+g.z1)/2,gt=(x,y,z)=>{const c=gT(x,y,z);return [c[0]*1.05,c[1]*1.0,c[2]*.9];};
  const r=rng(8);
  // central walk, cross walks and the basin
  boxMesh(g.x0,0,zc-.9,g.x1,.03,zc+.9,'alcGravel',gt,{noSides:true});
  const bx=(g.x0+g.x1)/2;
  // parterres: rectangles between the walks, bordered by box hedges
  for(const side of [-1,1]){
    const za=side<0?g.z0+.1:zc+1.2,zb=side<0?zc-1.2:g.z1-.1;
    for(let x=g.x0+1;x<g.x1-5;x+=5.6){if(Math.abs(x+2.8-bx)<4.6)continue;
      const x1=x+4.4;
      hedgeRun(b,x,za,x1,za,x*3+side,.6);hedgeRun(b,x,zb,x1,zb,x*5+side,.6);hedgeRun(b,x,za,x,zb,x*7+side,.6);hedgeRun(b,x1,za,x1,zb,x*11+side,.6);
      boxMesh(x+.25,0,za+.25,x1-.25,.04,zb-.25,'alcEarth',gt,{noSides:true});
      if(r()<.8)b.flowers((x+x1)/2-.8,.1,(za+zb)/2,r()<.5?'flower':'whiteFlower');if(r()<.6)b.flowers((x+x1)/2+.9,.1,(za+zb)/2,'flower');
    }
  }
  // basin
  const R=1.9,cx=bx,cz=zc;
  b.cylinder(cx,0,cz,R+.35,.55,'alcCopingP',R+.35,28);b.cylinder(cx,.55,cz,R-.1,.02,'water',R-.1,28);b.cylinder(cx,.55,cz,.22,1.0,'alcCopingP',.12,12);
  for(let k=0;k<4;k++){const a=k*Math.PI/2+.4;b.jet(cx+Math.cos(a)*.15,1.5,cz+Math.sin(a)*.15,Math.cos(a)*1.0,Math.sin(a)*1.0,.35);}
  // trees
  plant(g.x0+1.5,0,g.z0+1.5,CYPRESS,8.5);plant(g.x0+1.5,0,g.z1-1.5,CYPRESS,9);plant(g.x1-1.5,0,g.z0+1.5,CYPRESS,8);plant(g.x1-1.5,0,g.z1-1.5,CYPRESS,8.8);
  for(const dx of [-3.2,3.2])for(const dz of [-2.4,2.4])plant(bx+dx,0,zc+dz,ORANGE,3.4+r()*.6);
  for(let x=g.x0+9;x<g.x1-8;x+=13)plant(x,0,g.z1+.4,CYPRESS,7.5+r()*1.5);
  plant(g.x1+3,0,44,PALM,8);plant(g.x0-2,0,43.5,PALM,7);
}


// ======================================================================= Revellin (west artillery bastion)
function revellin(b,gT){
  const r=rng(19),gt=tinter('ground',13);
  // vaulted gallery under the terrace, seen as five arched openings in a masonry bank
  const bx0=-296.4,bx1=-290.4,z0=16,z1=34,top=3.3,nic=[],tw=Array.from({length:5},(_,k)=>17.4+3.4*k);
  const east={A:[bx1,z1],B:[bx1,z0],mA:[1,0],mB:[1,0]},L=z1-z0;
  faceGrid({...east,mat:'alcBcB',...surf('alcBcB'),top,foot:()=>0,bat:()=>0,tint:gt,disp:.015,holes:tw.map(z=>({u0:z1-z-1.35,u1:z1-z+1.35,y0:.5,y1:3.1,noReveal:true}))});
  for(const z of tw)nichePlate(b,bx1,z,1,0,2.0,2.55,2.8,.7,'alcBrickAP',.35);
  faceGrid({A:[bx1,z0],B:[bx0,z0],mA:[0,-1],mB:[0,-1],mat:'alcBcB',...surf('alcBcB'),top,foot:()=>0,bat:()=>0,tint:gt,disp:.015});
  faceGrid({A:[bx0,z1],B:[bx1,z1],mA:[0,1],mB:[0,1],mat:'alcBcB',...surf('alcBcB'),top,foot:()=>0,bat:()=>0,tint:gt,disp:.015});
  fillPoly([[bx0,z0],[bx1,z0],[bx1,z1],[bx0,z1]],[],top,'alcEarth',gt);
  prism({A:[bx1,z1],B:[bx1,z0],mA:[1,0],mB:[1,0]},-.5,.06,top,top+.5,'alcBcB',gt,{noTop:true,noOuter:true});
  prism({A:[bx1,z1],B:[bx1,z0],mA:[1,0],mB:[1,0]},-.56,.12,top+.5,top+.62,'alcCoping',gt,{});
  // trees and scrub on the dry terrace
  const spots=[];
  for(let i=0;i<220&&spots.length<26;i++){const x=-288+r()*38,z=8+r()*40;if(!inside(x,z,PER)||distPoly(x,z,PER)<4.5)continue;if(x<-289&&z>14&&z<36)continue;if(spots.some(p=>Math.hypot(p[0]-x,p[1]-z)<5.5))continue;spots.push([x,z]);}
  spots.forEach(([x,z],i)=>plant(x,0,z,[OLIVE,HOLM,CYPRESS,SHRUB,HOLM,OLIVE][i%6],[4.5,6,8.5,1.6,5.5,4][i%6]*(.85+r()*.3)));
}


// ======================================================================= Plaza de Armas: cistern, baths, dungeon pit, wells, weeds
function plazaFeatures(b,gT){
  const holes=[],r=rng(404),st=tinter('ground',21),brickT=(x,y,z)=>{const c=st(x,y,z);return [c[0]*.95,c[1]*.92,c[2]*.9];};
  const wat=(x0,z0,x1,z1,y)=>{const g=new THREE.PlaneGeometry(x1-x0,z1-z0);g.rotateX(-Math.PI/2);b.unique(g,'alcWater',[(x0+x1)/2,y,(z0+z1)/2]);};
  // ---- the aljibe: a brick-lined cistern with a stair down and a stone kerb
  {const x0=-162,x1=-154.5,z0=9,z1=18,fy=-1.7,wy=-.7;holes.push({x0,x1,z0,z1});
    const a=accFor('alcBrickA',x0,z0),c=brickT((x0+x1)/2,-1,(z0+z1)/2);
    quad(a,[x0,fy,z0],[x1,fy,z0],[x1,0,z0],[x0,0,z0],[0,0,1],[x0,fy],[x1,fy],[x1,0],[x0,0],c);quad(a,[x1,fy,z1],[x0,fy,z1],[x0,0,z1],[x1,0,z1],[0,0,-1],[x1,fy],[x0,fy],[x0,0],[x1,0],c);
    quad(a,[x0,fy,z1],[x0,fy,z0],[x0,0,z0],[x0,0,z1],[1,0,0],[z1,fy],[z0,fy],[z0,0],[z1,0],c);quad(a,[x1,fy,z0],[x1,fy,z1],[x1,0,z1],[x1,0,z0],[-1,0,0],[z0,fy],[z1,fy],[z1,0],[z0,0],c);
    quad(a,[x0,fy,z0],[x1,fy,z0],[x1,fy,z1],[x0,fy,z1],[0,1,0],[x0,z0],[x1,z0],[x1,z1],[x0,z1],c);
    wat(x0,z0,x1,z1,wy);
    // kerb and corner posts
    for(const [ax,az,bx,bz] of [[x0-.25,z0-.25,x1+.25,z0+.25],[x0-.25,z1-.25,x1+.25,z1+.25],[x0-.25,z0-.25,x0+.25,z1+.25],[x1-.25,z0-.25,x1+.25,z1+.25]])boxMesh(ax,0,az,bx,.3,bz,'alcCoping',st,{});
    // stair down along the west wall
    stairRun(x0+.8,z1-.5,x0+.8,z0+3.2,1.2,fy,-.05,brickT,fy-.1);
    b.nav.box((x0+x1)/2,(z0+z1)/2,x1-x0+.6,z1-z0+.6,-3,.3);
  }
  // ---- the baths: a sunken brick floor, low walls, a partition with two horseshoe arches and a plunge basin
  {const x0=-168,x1=-159,z0=28.5,z1=33,fy=-.9;holes.push({x0,x1,z0,z1});
    const a=accFor('alcBrickA',x0,z0),c=brickT((x0+x1)/2,-1,(z0+z1)/2);
    quad(a,[x0,fy,z0],[x1,fy,z0],[x1,.35,z0],[x0,.35,z0],[0,0,1],[x0,fy],[x1,fy],[x1,.35],[x0,.35],c);quad(a,[x1,fy,z1],[x0,fy,z1],[x0,.35,z1],[x1,.35,z1],[0,0,-1],[x1,fy],[x0,fy],[x0,.35],[x1,.35],c);
    quad(a,[x0,fy,z1],[x0,fy,z0],[x0,.35,z0],[x0,.35,z1],[1,0,0],[z1,fy],[z0,fy],[z0,.35],[z1,.35],c);quad(a,[x1,fy,z0],[x1,fy,z1],[x1,.35,z1],[x1,.35,z0],[-1,0,0],[z0,fy],[z1,fy],[z1,.35],[z0,.35],c);
    quad(accFor('alcBrickA',x0,z0),[x0,fy,z0],[x1,fy,z0],[x1,fy,z1],[x0,fy,z1],[0,1,0],[x0,z0],[x1,z0],[x1,z1],[x0,z1],[c[0]*.9,c[1]*.9,c[2]*.9]);
    for(const [ax,az,bx,bz] of [[x0-.2,z0-.2,x1+.2,z0+.2],[x0-.2,z1-.2,x1+.2,z1+.2],[x0-.2,z0-.2,x0+.2,z1+.2],[x1-.2,z0-.2,x1+.2,z1+.2]])boxMesh(ax,.35,az,bx,.45,bz,'alcCoping',st,{});
    // partition with two arches, brick piers and a small basin
    const px=-163.5,w=.55;
    for(const zc of [29.8,31.7])nichePlate(b,px,zc,1,0,1.3,1.9,w,fy,'alcBrickAP',.4);
    boxMesh(px-w/2,fy,28.5,px+w/2,.35,28.9,'alcBrickA',brickT,{});boxMesh(px-w/2,fy,32.6,px+w/2,.35,33,'alcBrickA',brickT,{});
    for(const zc of [29.8,31.7])boxMesh(px-w/2-.01,.35,zc-.9,px-w/2+.01,.36,zc+.9,'alcBrickA',brickT,{noSides:true});
    boxMesh(-166.8,fy,29,-165.1,fy+.55,30.7,'alcBrickA',brickT,{});wat(-166.7,29.1,-165.2,30.6,fy+.45);
    for(const [qx,qz] of [[-160.5,29.4],[-160.5,32.1]])boxMesh(qx-.25,fy,qz-.25,qx+.25,.9,qz+.25,'alcBrickA',brickT,{});
    b.nav.box((x0+x1)/2,(z0+z1)/2,x1-x0+.5,z1-z0+.5,-3,.4);
  }
  // ---- the dungeon pit (mazmorra): stone rim, an iron grille and the dark shaft
  {const cx=-149.25,cz=12.75,R=1.9,sq=[[-151.5,10.5],[-147,10.5],[-147,15],[-151.5,15]];holes.push({x0:-151.5,x1:-147,z0:10.5,z1:15});
    const ring=Array.from({length:28},(_,i)=>{const t=i/28*Math.PI*2;return [cx+Math.cos(t)*R,cz+Math.sin(t)*R];});
    fillPoly(sq,[ring],0,'alcGravel',gT);
    const sh=new THREE.Shape(),ho=new THREE.Path();for(let i=0;i<=28;i++){const t=i/28*Math.PI*2;(i?sh.lineTo.bind(sh):sh.moveTo.bind(sh))(Math.cos(t)*(R+.35),Math.sin(t)*(R+.35));(i?ho.lineTo.bind(ho):ho.moveTo.bind(ho))(Math.cos(t)*R,Math.sin(t)*R);}
    sh.holes.push(ho);const rg=new THREE.ExtrudeGeometry(sh,{depth:.34,bevelEnabled:false,curveSegments:2});rg.rotateX(-Math.PI/2);b.unique(rg,'alcCopingP',[cx,0,cz]);
    const cy=new THREE.CylinderGeometry(R,R,4.6,28,1,true);b.unique(cy,'alcDarkP',[cx,-2.3,cz]);const dk=new THREE.CircleGeometry(R,28);dk.rotateX(-Math.PI/2);b.unique(dk,'alcDarkP',[cx,-4.5,cz]);
    for(let k=-3;k<=3;k++){const o=k*.5,hw=Math.sqrt(Math.max(0,R*R-o*o));b.line([cx-hw,.22,cz+o],[cx+hw,.22,cz+o],.022,'alcDark');b.line([cx+o,.22,cz-hw],[cx+o,.22,cz+hw],.022,'alcDark');}
    b.nav.box(cx,cz,2*R+1.3,2*R+1.3,-5,.3);
  }
  // ---- two wells in the open ground and a few worked stones
  for(const [wx,wz] of [[-157.5,21.5]]){b.cylinder(wx,0,wz,.75,.8,'alcRubbleP',.75,16);b.cylinder(wx,.78,wz,.86,.1,'alcCopingP',.86,16);b.cylinder(wx,.84,wz,.52,.02,'alcDarkP',.52,16);b.nav.box(wx,wz,1.7,1.7,0,.95);}
  const blocks=b.geometry('alc-stone',()=>new THREE.BoxGeometry(1,1,1));
  for(let i=0;i<26;i++){const x=-216+r()*66,z=-6+r()*40;if(!inside(x,z,PLAZA)||distPoly(x,z,PLAZA)<2)continue;if(Math.abs(z-27)<1.6||holes.some(h=>x>h.x0-1&&x<h.x1+1&&z>h.z0-1&&z<h.z1+1))continue;
    const w=.4+r()*.6;b.add(blocks,'alcCopingP',[x,.08+w*.12,z],[w,.15+w*.25,w*(.6+r()*.5)],r()*3);}
  return holes;
}
function weeds(b,PLAZAholes){
  if(LOW)return;const r=rng(909),inH=(x,z)=>PLAZAholes.some(h=>x>h.x0-.2&&x<h.x1+.2&&z>h.z0-.2&&z<h.z1+.2);
  let n=0;
  for(let i=0;i<900&&n<110;i++){const x=-222+r()*80,z=-10+r()*50;if(!inside(x,z,PLAZA)||inH(x,z)||Math.abs(z-27)<1.7)continue;
    const near=distPoly(x,z,PLAZA);if(near>3.5&&r()>.18)continue;n++;
    leaves(b,x,.07,z,.2,.1,.2,10,300+n,.05+r()*.04);}
}

// ======================================================================= Torre de la Vela
const V={x0:VELA.x0,x1:VELA.x1,z0:VELA.z0,z1:VELA.z1,T:1.5,top:26};
// openings: face, centre (world coordinate along the face), y0, y1, width
const VWIN=[['E',31.6,0,3.0,1.8,'d'],['E',26.4,8.8,1.5,.24,'s'],['E',20.3,8.8,1.4,.24,'s'],['E',23.3,15.2,1.5,.8,'a'],['E',29.2,21,1.4,.24,'s'],['E',17.9,20.5,1.4,.24,'s'],
  ['S',-231.5,16.5,1.5,.8,'a'],['S',-227,9,1.4,.24,'s'],['S',-236,12.5,1.4,.24,'s'],['S',-233.5,21.5,1.4,.24,'s'],
  ['N',-229.5,11.2,1.4,.24,'s'],['N',-234,19,1.5,.8,'a'],['N',-226.5,14.5,1.4,.24,'s'],
  ['W',19.5,14,1.4,.24,'s'],['W',28.5,8,1.4,.24,'s'],['W',24,20,1.5,.8,'a'],['W',31,17,1.4,.24,'s']];
function stairFlight(x,z,w,len,y0,y1,rev,tint){
  const n=Math.ceil(Math.abs(y1-y0)/.18),d=len/n,dir=rev?-1:1,zs=z-dir*len/2,ac=accFor('alcBrickA',x,z),ap=accFor('alcCoping',x,z),th=.45;
  for(let i=0;i<n;i++){
    const ya=y0+(y1-y0)*i/n,yb=y0+(y1-y0)*(i+1)/n,za=zs+dir*i*d,zb=zs+dir*(i+1)*d,xa=x-w/2,xb=x+w/2,c=tint(x,yb,za);
    quad(ap,[xa,yb,za],[xb,yb,za],[xb,yb,zb],[xa,yb,zb],[0,1,0],[xa,za],[xb,za],[xb,zb],[xa,zb],c);
    quad(ac,[xa,ya,za],[xb,ya,za],[xb,yb,za],[xa,yb,za],[0,0,-dir],[xa,ya],[xb,ya],[xb,yb],[xa,yb],c);
    quad(ac,[xa,yb-th,za],[xa,yb-th,zb],[xa,yb,zb],[xa,yb,za],[-1,0,0],[za,yb-th],[zb,yb-th],[zb,yb],[za,yb],c);
    quad(ac,[xb,yb-th,za],[xb,yb-th,zb],[xb,yb,zb],[xb,yb,za],[1,0,0],[za,yb-th],[zb,yb-th],[zb,yb],[za,yb],c);
    if(i===n-1||true){const yl=yb-th;quad(ac,[xa,yl,za],[xb,yl,za],[xb,yl,zb],[xa,yl,zb],[0,-1,0],[xa,za],[xb,za],[xb,zb],[xa,zb],[c[0]*.6,c[1]*.6,c[2]*.6]);}
  }
}
function vela(b){
  const {x0,x1,z0,z1,T,top}=V,t=tinter('tapial',5),it=(x,y,z)=>{const c=t(x,y,z);return [c[0]*.78,c[1]*.78,c[2]*.78];},gT=tinter('ground',7),ct=(x,y,z)=>{const c=gT(x,y,z);return [c[0]*.9,c[1]*.9,c[2]*.9];};
  const outer=orient([[x0,z0],[x1,z0],[x1,z1],[x0,z1]],true),inner=orient([[x0+T,z0+T],[x1-T,z0+T],[x1-T,z1-T],[x0+T,z1-T]],false);
  const faceOf=e=>{const dx=e.B[0]-e.A[0],dz=e.B[1]-e.A[1],L=Math.hypot(dx,dz),nx=-dz/L,nz=dx/L;return Math.abs(nx)>.5?(nx>0?'E':'W'):(nz>0?'S':'N');};
  const uOf=(e,face,c)=>(face==='E'||face==='W')?(c-e.A[1])*Math.sign(e.B[1]-e.A[1]):(c-e.A[0])*Math.sign(e.B[0]-e.A[0]);
  const holesFor=(e,face,dep,outerSkin)=>{const res=[];for(const w of VWIN)if(w[0]===face){const u=uOf(e,face,w[1]),k=w[5];
    if(outerSkin&&k!=='s')res.push({u0:u-w[4]/2-(k==='d'?.5:.22),u1:u+w[4]/2+(k==='d'?.5:.22),y0:w[2]-(k==='d'?.35:.18),y1:w[2]+w[3]+.4,noReveal:true});
    else res.push({u0:u-w[4]/2,u1:u+w[4]/2,y0:w[2]+(k==='d'?.0:0),y1:w[2]+w[3],depth:dep,back:false});}return res;};
  const specsFor=(e,face,kind)=>VWIN.filter(w=>w[0]===face&&w[5]===kind).map(w=>({u:uOf(e,face,w[1]),y:w[2],w:w[4],h:w[3],through:kind==='a'}));
  let u=0;
  const BAND=top-7.6;
  for(const e of outer){
    const f=faceOf(e),east=f==='E',bat=y=>.028*(top-y);
    faceGrid({...e,mat:'alcBrickB',rows:ROWS.lime,relief:RELIEF.lime,matLow:'alcLimeA',ySplit:BAND,top:top+1,foot:()=>east?0:WALK-.5,bat,tint:t,u0:u,ds:1.3,disp:.02,holes:holesFor(e,f,T/2,true)});
    // eroded render: brick shows through in irregular patches; the brick band carries pale lime patches
    {const L=edgeLen(e),r=rng(Math.round(u*7)+3);for(let k=0;k<(LOW?5:11);k++){const w=1.2+r()*2.6,h=1+r()*2.3,uu=1.2+r()*(L-2.4),yy=2.5+r()*(BAND-5);facePatch(e,uu,yy,w,h,'alcBrickA',t,{bat,seed:k+17+Math.round(u)});}
      for(let k=0;k<(LOW?2:5);k++){const w=1+r()*1.8,h=.8+r()*1.4,uu=1+r()*(L-2),yy=BAND+1+r()*5;facePatch(e,uu,yy,w,h,'alcLimeA',t,{bat,seed:k+53+Math.round(u)});}}
    // brick pilasters up the corners, as on the real tower
    strip(e,0,1.15,east?0:WALK,top,bat,'alcBrickB',(x,y,z)=>{const c=t(x,y,z);return [c[0]*.95,c[1]*.9,c[2]*.86];},.05);strip(e,edgeLen(e)-1.15,edgeLen(e),east?0:WALK,top,bat,'alcBrickB',(x,y,z)=>{const c=t(x,y,z);return [c[0]*.95,c[1]*.9,c[2]*.86];},.05);
    if(east||f==='S')crackOn(e,edgeLen(e)*(east?.42:.58),3,BAND+2,bat,east?11:12);
    platesOn(b,e,specsFor(e,f,'a'),bat,.22,'alcBrickAP',true);platesOn(b,e,specsFor(e,f,'d'),bat,.5,'alcBrickAP',false);
    prism(e,-.5,0,top,top+1,'alcBrickB',t,{noTop:true,noOuter:true,u0:u});
    prism(e,-.62,.08,top+1,top+1.13,'alcCoping',t,{});
    prism(e,bat(top-2.4)-.1,bat(top-2.4)+.2,top-2.7,top-2.4,'alcCoping',t,{u0:u});               // upper string course
    prism(e,bat(top-.5)-.1,bat(top-.5)+.34,top-.6,top-.2,'alcCoping',t,{noTop:false,u0:u});        // cornice below the terrace
    // brick corbels under the cornice
    {const L=edgeLen(e),n=Math.floor(L/.62),dx=(e.B[0]-e.A[0])/L,dz=(e.B[1]-e.A[1])/L,rot=-Math.atan2(dz,dx);
      for(let k=0;k<n;k++){const tt=(k+.5)/n,k2=bat(top-.7)+.12;b.box(lerp(e.A[0],e.B[0],tt)+lerp(e.mA[0],e.mB[0],tt)*k2,top-.95,lerp(e.A[1],e.B[1],tt)+lerp(e.mA[1],e.mB[1],tt)*k2,.3,.34,.3,'alcBrickAP',rot);}}
    u+=edgeLen(e);
  }
  // interior faces and finishes
  u=0;
  for(const e of inner){const f=faceOf(e);const fo={E:'W',W:'E',N:'S',S:'N'}[f];
    faceGrid({...e,mat:'alcBrickA',top:top-.35,foot:()=>0,bat:()=>0,tint:it,u0:u,ds:1.3,dt:1.3,disp:0,holes:holesFor(e,fo,T/2,false)});u+=edgeLen(e);}
  const IN=[[x0+T,z0+T],[x1-T,z0+T],[x1-T,z1-T],[x0+T,z1-T]],OUT=[[x0,z0],[x1,z0],[x1,z1],[x0,z1]];
  fillPoly(IN,[],.02,'alcCobble',ct);
  // terrace: brick pavers, with the stair opening; ceiling below it
  const hole=[[-226.3,16.6],[-223.5,16.6],[-223.5,28],[-226.3,28]];
  fillPoly(OUT,[hole],top,'alcBrickA',ct);fillPoly(IN,[hole],top-.35,'alcBrickA',it,true);
  // stair flights and landings
  for(let f=0;f<5;f++){
    const xx=-228+(f%2?-3.1:3.1),y0=f*5.2,y1=(f+1)*5.2,rev=f%2===0,lz=24+(f%2===0?-8:8);
    stairFlight(xx,24,2.4,15,y0,y1,rev,it);b.nav.ramp(xx,24,2.4,15,rev?y1:y0,rev?y0:y1);
    b.nav.floor(-228,lz,12,2,y1);
    if(f<4)boxMesh(x0+T,y1-.4,lz-1,x1-T,y1,lz+1,'alcBrickA',it,{});
    // iron rail on the side that looks into the shaft
    const sx=xx+(f%2?1.3:-1.3);b.line([sx,y0+.95,rev?24+7.5:24-7.5],[sx,y1+.95,rev?24-7.5:24+7.5],.04,'alcDark');
  }
  b.nav.floor(-228,24,19,19,0);
  // terrace navigation: everything but the stair opening
  b.nav.floor((x0-226.3)/2,(z0+z1)/2,-226.3-x0,z1-z0,top);
  b.nav.floor((-223.5+x1)/2,(z0+z1)/2,x1+223.5,z1-z0,top);
  b.nav.floor(-224.9,(z0+16.6)/2,2.8,16.6-z0,top);b.nav.floor(-224.9,(28+z1)/2,2.8,z1-28,top);
  // walls block the walker; parapets and the stair-opening rail only matter on the terrace
  b.nav.box(x0+T/2,(z0+z1)/2,T,z1-z0,0,top);b.nav.box((x0+x1)/2,z0+T/2,x1-x0,T,0,top);b.nav.box((x0+x1)/2,z1-T/2,x1-x0,T,0,top);
  b.nav.box(x1-T/2,(z0+30.7)/2,T,30.7-z0,0,top);b.nav.box(x1-T/2,(32.5+z1)/2,T,z1-32.5,0,top);
  b.nav.box(x0+.25,(z0+z1)/2,.5,z1-z0,top,top+1);b.nav.box(x1-.25,(z0+z1)/2,.5,z1-z0,top,top+1);b.nav.box((x0+x1)/2,z0+.25,x1-x0,.5,top,top+1);b.nav.box((x0+x1)/2,z1-.25,x1-x0,.5,top,top+1);
  // iron guard rail around the stair opening (thin: it must not hide the panorama)
  {const rx0=-226.3,rx1=-223.5,rz0=16.6,rz1=28,rl=[[rx0,rz0,rx0,rz1],[rx1,rz0,rx1,rz1],[rx0,rz1,rx1,rz1]];
    for(const [ax,az,cx,cz] of rl){const L=Math.hypot(cx-ax,cz-az),n=Math.max(1,Math.round(L/1.4));for(let k=0;k<=n;k++){const x=lerp(ax,cx,k/n),z=lerp(az,cz,k/n);b.line([x,top,z],[x,top+.95,z],.02,'alcDark');}
      b.line([ax,top+.95,az],[cx,top+.95,cz],.015,'alcDark');b.line([ax,top+.5,az],[cx,top+.5,cz],.011,'alcDark');
      b.nav.box((ax+cx)/2,(az+cz)/2,Math.abs(cx-ax)+.25,Math.abs(cz-az)+.25,top,top+1.05);}}
  // putlog holes in rows
  const hole1=b.geometry('alc-putlog',()=>{const g=new THREE.BoxGeometry(.13,.13,.12);return g;}),r=rng(5);
  for(const [px,pz,nx,nz] of [[x0,0,-1,0],[x1,0,1,0]])for(let y=3.4;y<top-1;y+=1.7)for(let z=z0+1.2;z<z1-1;z+=1.6+r()*.9){if(r()<.25)continue;const zz=z+((y*7|0)%3)*.3;b.add(hole1,'alcDark',[px+nx*.02,y+(r()-.5)*.1,zz],[1,1,1],0);}
  for(const [pz,nz] of [[z0,-1],[z1,1]])for(let y=3.4;y<top-1;y+=1.7)for(let x=x0+1.2;x<x1-1;x+=1.6+r()*.9){if(r()<.25)continue;b.add(hole1,'alcDark',[x+((y*7|0)%3)*.3,y+(r()-.5)*.1,pz+nz*.02],[1,1,1],Math.PI/2);}
}


function velaTop(b){
  const {x0,x1,z0,z1,top}=V,gT=tinter('ground',8),ct=(x,y,z)=>{const c=gT(x,y,z);return [c[0]*.9,c[1]*.9,c[2]*.9];};
  const rt=top+1.13;
  // modern railing on the parapet
  const post=.9,sides=[[[x0+.25,z0+.25],[x1-.25,z0+.25]],[[x1-.25,z0+.25],[x1-.25,z1-.25]],[[x1-.25,z1-.25],[x0+.25,z1-.25]],[[x0+.25,z1-.25],[x0+.25,z0+.25]]];
  for(const [a,c] of sides){const L=Math.hypot(c[0]-a[0],c[1]-a[1]),n=Math.round(L/1.5);
    for(let i=0;i<=n;i++){const t=i/n,x=lerp(a[0],c[0],t),z=lerp(a[1],c[1],t);b.line([x,rt,z],[x,rt+post,z],.022,'alcDark');}
    b.line([a[0],rt+post,a[1]],[c[0],rt+post,c[1]],.016,'alcDark');b.line([a[0],rt+post*.5,a[1]],[c[0],rt+post*.5,c[1]],.012,'alcDark');}
  // belfry (campanario): rendered plinth, brick bell-chamber with the arch, crenellated crown
  const bx=-231,bz=21,hw=1.3,hd=.78,ph=1.35;
  boxMesh(bx-hd,top,bz-hw,bx+hd,top+ph,bz+hw,'alcBrickBP',null,{col:[1,1,1]});
  boxMesh(bx-hd-.12,top+ph,bz-hw-.12,bx+hd+.12,top+ph+.2,bz+hw+.12,'alcCopingP',null,{col:[1,1,1]});
  b.nav.box(bx,bz,hd*2+.2,hw*2+.2,top,top+3);
  const bh=3.4,sh=new THREE.Shape(),w2=hw-.12;
  sh.moveTo(-w2,0);sh.lineTo(w2,0);sh.lineTo(w2,bh);sh.lineTo(-w2,bh);sh.closePath();
  const ar=new THREE.Path();ar.moveTo(-.62,0);ar.lineTo(-.62,.9);ar.absarc(0,.9,.62,Math.PI,0,true);ar.lineTo(.62,0);ar.closePath();sh.holes.push(ar);
  const bg=new THREE.ExtrudeGeometry(sh,{depth:hd*2-.25,bevelEnabled:false,curveSegments:14});bg.translate(0,0,-(hd-.125));
  const uvs=bg.attributes.uv;for(let i=0;i<uvs.count;i++)uvs.setXY(i,uvs.getX(i),uvs.getY(i));
  b.unique(bg,'alcBrickAP',[bx,top+ph+.2,bz],Math.PI/2);
  boxMesh(bx-hd-.1,top+ph+.2+bh,bz-hw-.1,bx+hd+.1,top+ph+.2+bh+.18,bz+hw+.1,'alcCopingP',null,{col:[1,1,1]});
  const crown=orient([[bx-hd+.04,bz-w2],[bx+hd-.04,bz-w2],[bx+hd-.04,bz+w2],[bx-hd+.04,bz+w2]],true);
  for(const e of crown)merlons(b,e,-.02,top+ph+.2+bh+.18,'alcBrickAP',.52,.58);
  // bell and yoke
  const pts=[[.04,.86],[.1,.84],[.17,.7],[.22,.5],[.3,.26],[.38,.08],[.42,0],[.37,-.02],[.34,.04],[.28,.2],[.2,.42],[.12,.62],[.05,.78]].map(p=>new THREE.Vector2(p[0],p[1]));
  const bell=new THREE.LatheGeometry(pts,18);bell.translate(0,-.9,0);b.unique(bell,'alcBronze',[bx,top+ph+.2+bh-.35,bz]);
  b.line([bx,top+ph+.2+bh-.1,bz-.55],[bx,top+ph+.2+bh-.1,bz+.55],.05,'alcDark');
  // weather-vane and lightning rod
  const wy=top+ph+.2+bh+.18+.6;b.line([bx,wy,bz],[bx,wy+1.5,bz],.03,'alcDark');b.line([bx-.35,wy+1.1,bz],[bx+.35,wy+1.1,bz],.03,'alcDark');b.line([bx,wy+1.3,bz],[bx,wy+1.3,bz+.0001],.03,'alcDark');
  b.line([bx+.2,wy-.4,bz+.9],[bx+.2,wy+1.9,bz+.9],.022,'alcDark');
  // flags on poles along the east edge, blowing to the north-east
  const r=rng(41);
  [0,1,2,3].forEach(i=>{const px=x1-.7,pz=27.2+i*1.15;b.line([px,rt,pz],[px,rt+5.2,pz],.02,'alcDark');
    const g=new THREE.PlaneGeometry(1.5,1,14,4),p=g.attributes.position;for(let k=0;k<p.count;k++){const u=(p.getX(k)+.75)/1.5;p.setZ(k,Math.sin(u*5.2+i*1.3)*.12*u);}g.translate(.75,0,0);g.computeVertexNormals();g.rotateY(-Math.PI/2+.3+(r()-.5)*.3);b.unique(g,'alcFlag'+i,[px,rt+4.55,pz]);});
}

// ======================================================================= more building blocks
function subEdge(e,t0,t1){const l=(a,b,t)=>a+(b-a)*t;return {A:[l(e.A[0],e.B[0],t0),l(e.A[1],e.B[1],t0)],B:[l(e.A[0],e.B[0],t1),l(e.A[1],e.B[1],t1)],mA:[l(e.mA[0],e.mB[0],t0),l(e.mA[1],e.mB[1],t0)],mB:[l(e.mA[0],e.mB[0],t1),l(e.mA[1],e.mB[1],t1)]};}
// organic lime-render / repair patch laid on a face (outward offset 3.5 cm), with a darker rim
function facePatch(e,u,y,w,h,mat,tint,o={}){
  const {A,B,mA,mB}=e,L=edgeLen(e),dx=B[0]-A[0],dz=B[1]-A[1],nx=-dz/L,nz=dx/L,bat=o.bat||(()=>0),r=rng(o.seed||1),N=22,ring=[];
  const ph=[r()*6.28,r()*6.28,r()*6.28];
  for(let i=0;i<N;i++){const a=i/N*Math.PI*2,rr=.8+.2*Math.sin(2*a+ph[0])+.14*Math.sin(3*a+ph[1])+.08*Math.sin(5*a+ph[2])+(r()-.5)*.1;ring.push([u+Math.cos(a)*w/2*rr,y+Math.sin(a)*h/2*rr*(1+.25*Math.sin(a+ph[1]))]);}
  const pos=(uu,yy,off)=>{const t=clamp(uu,.02,L-.02)/L,k=bat(yy)+off;return [A[0]+dx*t+lerp(mA[0],mB[0],t)*k,yy,A[1]+dz*t+lerp(mA[1],mB[1],t)*k];};
  const n=[nx,0,nz],c=ring.reduce((s2,p)=>[s2[0]+p[0]/N,s2[1]+p[1]/N],[0,0]);
  for(const [sc,off,dark,warm] of [[1.06,.018,.84,[1.05,.92,.84]],[1,.036,.96,[1.02,.97,.93]]]){
    const a=accFor(mat,A[0],A[1]);
    for(let i=0;i<N;i++){const p=ring[i],q=ring[(i+1)%N],P=[c,[c[0]+(p[0]-c[0])*sc,c[1]+(p[1]-c[1])*sc],[c[0]+(q[0]-c[0])*sc,c[1]+(q[1]-c[1])*sc]];
      const W=P.map(v=>pos(v[0],v[1],off)),col=P.map((v,k)=>{const t=tint?tint(W[k][0],v[1],W[k][2]):[1,1,1];return [t[0]*dark*warm[0],t[1]*dark*warm[1],t[2]*dark*warm[2]];});
      tri(a,W[0],W[1],W[2],n,n,n,[P[0][0],P[0][1]],[P[1][0],P[1][1]],[P[2][0],P[2][1]],col[0],col[1],col[2]);}
  }
}

// brick-framed blind arch (niche) set into a wall: plate with an arched hole extruded into the wall, dark back
function nichePlate(b,px,pz,nx,nz,w,h,depth,y0=0,mat='alcBrickAP',margin=.5,through=false,backAt=null){
  const sh=new THREE.Shape(),hw=w/2+margin,top=h+.4;
  sh.moveTo(-hw,y0-.35);sh.lineTo(hw,y0-.35);sh.lineTo(hw,y0+top);sh.lineTo(-hw,y0+top);sh.closePath();
  const r=w/2,spring=y0+h-r,ho=new THREE.Path();ho.moveTo(-r,y0);ho.lineTo(-r,spring);
  const N=22;for(let i=1;i<N;i++){const a=Math.PI-i*Math.PI/N;ho.lineTo(Math.cos(a)*r,spring+Math.sin(a)*r);}
  ho.lineTo(r,spring);ho.lineTo(r,y0);ho.closePath();sh.holes.push(ho);
  const g=new THREE.ExtrudeGeometry(sh,{depth,bevelEnabled:false,curveSegments:8}),th=Math.atan2(-nx,-nz);
  b.unique(g,mat,[px+nx*.04,0,pz+nz*.04],th);
  if(through)return;
  const bk=new THREE.PlaneGeometry(w+.1,h);bk.translate(0,y0+h/2,0);bk.rotateY(Math.atan2(nx,nz));
  const bd=backAt??(depth-.02);b.unique(bk,'alcDark',[px-nx*bd,0,pz-nz*bd]);
}
// vertical buttress on a battered face
function buttress(e,u,w,proj,yb,yt,bat,mat,tint,o={}){
  const {A,B,mA,mB}=e,L=edgeLen(e),dx=B[0]-A[0],dz=B[1]-A[1],tx=dx/L,tz=dz/L,nx=-tz,nz=tx,a=accFor(mat,A[0],A[1]);
  const P=(uu,y,off)=>{const t=clamp(uu,0,L)/L,k=bat(y)+off;return [A[0]+dx*t+lerp(mA[0],mB[0],t)*k+tx*0,y,A[1]+dz*t+lerp(mA[1],mB[1],t)*k];};
  const u0=u-w/2,u1=u+w/2,c=tint?tint(A[0]+dx*u/L,yt-3,A[1]+dz*u/L):null;
  quad(a,P(u0,yb,proj),P(u1,yb,proj),P(u1,yt,proj),P(u0,yt,proj),[nx,0,nz],[u0,yb],[u1,yb],[u1,yt],[u0,yt],c);
  // sides
  quad(a,P(u0,yb,0),P(u0,yb,proj),P(u0,yt,proj),P(u0,yt,0),[-tx,0,-tz],[0,yb],[proj,yb],[proj,yt],[0,yt],c);
  quad(a,P(u1,yb,0),P(u1,yb,proj),P(u1,yt,proj),P(u1,yt,0),[tx,0,tz],[0,yb],[proj,yb],[proj,yt],[0,yt],c);
  // sloping cap
  quad(a,P(u0,yt,proj),P(u1,yt,proj),P(u1,yt+.7,.1),P(u0,yt+.7,.1),[nx*.5,.85,nz*.5],[u0,0],[u1,0],[u1,.7],[u0,.7],c);
}


// small arched windows with brick surrounds; specs are generated per edge so that holes and plates agree
function winSpecs(e,seed,y0,y1,per=6.5,w=.8,h=1.5){
  const L=edgeLen(e),r=rng(seed),n=Math.floor(L/per),res=[];
  for(let k=0;k<n;k++){const u=(k+.5)*L/n+(r()-.5)*.8;if(u<1.5||u>L-1.5)continue;res.push({u,y:y0+(y1-y0)*(.15+.6*r()),w,h});}
  return res;
}
const specHoles=(specs,m=.22)=>specs.map(s=>({u0:s.u-s.w/2-m,u1:s.u+s.w/2+m,y0:s.y-.18,y1:s.y+s.h+.4,noReveal:true}));
function platesOn(b,e,specs,bat,m=.22,mat='alcBrickAP',through=false){
  const L=edgeLen(e),dx=e.B[0]-e.A[0],dz=e.B[1]-e.A[1],nx=-dz/L,nz=dx/L;
  for(const s of specs){const t=s.u/L,k=bat(s.y);nichePlate(b,e.A[0]+dx*t+lerp(e.mA[0],e.mB[0],t)*k,e.A[1]+dz*t+lerp(e.mA[1],e.mB[1],t)*k,nx,nz,s.w,s.h,.95,s.y,mat,m,through||s.through);}
}
// a portal (tunnel mouth) on whichever edge passes through (x,z)
const onEdge=(e,x,z)=>distSeg(x,z,e.A,e.B)<.4;
function uOn(e,x,z){const L=edgeLen(e);return ((x-e.A[0])*(e.B[0]-e.A[0])+(z-e.A[1])*(e.B[1]-e.A[1]))/L;}
// the Torre Quebrada's crack: a dark, zig-zag fissure running down the face with a slight step in the render
function crackOn(e,u,y0,y1,bat,seed){
  const L=edgeLen(e),dx=e.B[0]-e.A[0],dz=e.B[1]-e.A[1],nx=-dz/L,nz=dx/L,r=rng(seed),a=accFor('alcDarkP',e.A[0],e.A[1]);
  const pts=[];let cu=u;for(let y=y1;y>=y0-.01;y-=.55){cu+=(r()-.5)*.28+Math.sin(y*1.3)*.05;pts.push([cu,y,.1+r()*.12]);}
  const P=(uu,y,off)=>{const t=clamp(uu,.02,L-.02)/L,k=bat(y)+off;return [e.A[0]+dx*t+lerp(e.mA[0],e.mB[0],t)*k,y,e.A[1]+dz*t+lerp(e.mA[1],e.mB[1],t)*k];};
  for(let i=0;i<pts.length-1;i++){const p=pts[i],q=pts[i+1],w0=.04+p[2]*.32,w1=.04+q[2]*.32;
    quad(a,P(p[0]-w0,p[1],.02),P(p[0]+w0,p[1],.02),P(q[0]+w1,q[1],.02),P(q[0]-w1,q[1],.02),[nx,0,nz],[0,0],[1,0],[1,1],[0,1],null);}
}


// vertical strip proud of a battered face (corner quoins, pilaster-like bands)
function strip(e,u0,u1,y0,y1,bat,mat,tint,off=.035,col){
  const {A,B,mA,mB}=e,L=edgeLen(e),dx=B[0]-A[0],dz=B[1]-A[1],nx=-dz/L,nz=dx/L,a=accFor(mat,A[0],A[1]);
  const P=(uu,y)=>{const t=clamp(uu,0,L)/L,k=bat(y)+off;return [A[0]+dx*t+lerp(mA[0],mB[0],t)*k,y,A[1]+dz*t+lerp(mA[1],mB[1],t)*k];};
  const ys=[y0];for(const yy of [-3,3]) if(yy>y0+.1&&yy<y1-.1)ys.push(yy);ys.push(y1);
  for(let i=0;i<ys.length-1;i++){const ya=ys[i],yb=ys[i+1],c=tint?tint(A[0]+dx*(u0+u1)/2/L,(ya+yb)/2,A[1]+dz*(u0+u1)/2/L):col;
    quad(a,P(u0,ya),P(u1,ya),P(u1,yb),P(u0,yb),[nx,0,nz],[u0,ya],[u1,ya],[u1,yb],[u0,yb],c);}
}

// masonry stair rising from (x0,z0) to (x1,z1): treads, risers and solid sides
function stairRun(x0,z0,x1,z1,w,y0,y1,tint,base=-.1,sideMat='alcBrickA'){
  const L=Math.hypot(x1-x0,z1-z0),dx=(x1-x0)/L,dz=(z1-z0)/L,px=-dz,pz=dx,n=Math.ceil((y1-y0)/.17),d=L/n,ap=accFor('alcCoping',x0,z0),ac=accFor('alcBrickA',x0,z0),asd=accFor(sideMat,x0,z0);
  for(let i=0;i<n;i++){
    const sa=i*d,sb=(i+1)*d,ya=y0+(y1-y0)*i/n,yb=y0+(y1-y0)*(i+1)/n,ca=[x0+dx*sa,z0+dz*sa],cb=[x0+dx*sb,z0+dz*sb],hw=w/2,c=tint(ca[0],yb,ca[1]);
    const P=(cc,sgn,y)=>[cc[0]+px*hw*sgn,y,cc[1]+pz*hw*sgn];
    quad(ap,P(ca,-1,yb),P(ca,1,yb),P(cb,1,yb),P(cb,-1,yb),[0,1,0],[0,sa],[w,sa],[w,sb],[0,sb],c);
    quad(ac,P(ca,-1,ya),P(ca,1,ya),P(ca,1,yb),P(ca,-1,yb),[-dx,0,-dz],[0,ya],[w,ya],[w,yb],[0,yb],c);
    quad(asd,P(ca,1,base),P(cb,1,base),P(cb,1,yb),P(ca,1,yb),[px,0,pz],[sa,base],[sb,base],[sb,yb],[sa,yb],c);
    quad(asd,P(ca,-1,base),P(cb,-1,base),P(cb,-1,yb),P(ca,-1,yb),[-px,0,-pz],[sa,base],[sb,base],[sb,yb],[sa,yb],c);
  }
}
// openings of the east gate: horseshoe passage through the wall mass, portal plates brick
function gatePassage(b,xm,zm,len,rot){
  const sh=new THREE.Shape();sh.moveTo(-2.9,-.4);sh.lineTo(2.9,-.4);sh.lineTo(2.9,5.35);sh.lineTo(-2.9,5.35);sh.closePath();
  const R=2.05,spring=2.55,h=new THREE.Path();h.moveTo(-1.9,0);h.lineTo(-1.9,1.8);
  const N=26;for(let i=0;i<=N;i++){const th=Math.PI*1.12-i*(Math.PI*1.24)/N;h.lineTo(Math.cos(th)*R,spring+Math.sin(th)*R);}
  h.lineTo(1.9,0);h.closePath();sh.holes.push(h);
  const g=new THREE.ExtrudeGeometry(sh,{depth:len,bevelEnabled:false,curveSegments:10});g.translate(0,0,-len/2);
  b.unique(g,'alcBrickAP',[xm,0,zm],rot);
}
// deterministic slits and small windows for a solid tower face
function towerHoles(e,seed,y0,y1){
  const L=edgeLen(e),r=rng(seed),n=Math.floor(L/4.2),res=[];
  for(let k=0;k<n;k++){const u=(k+.5)*L/n+(r()-.5)*1.2;if(u<1.1||u>L-1.1)continue;const win=r()<.3,y=y0+2+r()*(y1-y0-6),w=win?.55:.22,h=win?.7:1.1;res.push({u0:u-w/2,u1:u+w/2,y0:y,y1:y+h,depth:.9,back:true});}
  return res;
}

// ======================================================================= build
const WALK=10.4,PAR=1.0,PARm=.34;let LOW=false;
const oldTower=(b,x,z,w,d,h)=>{
  b.floor(x,z,w,d);b.wall(x,z-d/2,w,h,1.0,0,'redwall',0,0,null);b.wall(x,z+d/2,w,h,1,0,'redwall',0,0,null);b.wall(x-w/2,z,d,h,1,0,'redwall',Math.PI/2,0,null);b.wall(x+w/2,z,d,h,1,3.2,'redwall',Math.PI/2,0,null);
  b.box(x-w/2+.5,h,z,1,.75,d,'redwall',0,true);b.box(x+w/2-.5,h,z,1,.75,d,'redwall',0,true);b.box(x,h,z-d/2+.5,w,.75,1,'redwall',0,true);b.box(x,h,z+d/2-.5,w,.75,1,'redwall',0,true);
  b.floor(x-4.15,z,11.7,d,h,'paving');b.floor(x+7.25,z,5.5,d,h,'paving');b.floor(x,z-9,w,2,h,'paving');b.floor(x,z+9,w,2,h,'paving');
};
function blockEdge(b,e,depthIn,depthOut,y0=-45,y1=WALK){
  // block along the edge: depthOut toward the mass (right of the left normal), depthIn toward the open side
  const dx=e.B[0]-e.A[0],dz=e.B[1]-e.A[1],L=Math.hypot(dx,dz);if(L<.05)return;const nx=-dz/L,nz=dx/L,mid=(depthOut-depthIn)/2;
  b.nav.box((e.A[0]+e.B[0])/2-nx*mid,(e.A[1]+e.B[1])/2-nz*mid,L+.5,depthIn+depthOut,y0,y1,-Math.atan2(dz,dx));
}
export function build(b,ctx){try{build0(b,ctx);}catch(e){console.log('ALC ERR '+e.stack);throw e;}}
function build0(b,ctx){
  PER=ctx.perimeter;demArr=null;ACC.clear();TRIS=0;LOW=!!ctx.low;
  b.zone='alcazaba';
  const outEdges=orient(OUTLINE,true),holeEdges=orient(HOLE.map(p=>[p[0],p[1]]),false);
  const nH=HOLE.length,towerList=Object.values(TOWERS);
  const covered=e=>{const mx=(e.A[0]+e.B[0])/2,mz=(e.A[1]+e.B[1])/2;return towerList.some(t=>inside(mx,mz,t.pts)||distPoly(mx,mz,t.pts)<1.1);};
  const tapT=tinter('tapial',1),limT=tinter('lime',2),gT=tinter('ground',3);
  const GZ=[24,29],GH=5.3,GZc=26.5;               // the east gate (z range of the plates, height, passage axis)
  const gateU=(e)=>{const L=edgeLen(e),t0=(GZ[0]-e.A[1])/(e.B[1]-e.A[1]),t1=(GZ[1]-e.A[1])/(e.B[1]-e.A[1]);return {u0:Math.min(t0,t1)*L,u1:Math.max(t0,t1)*L,y0:0,y1:GH,noReveal:true};};
  const isGateEdge=(e,xlo,xhi)=>e.A[0]>xlo&&e.A[0]<xhi&&e.B[0]>xlo&&e.B[0]<xhi&&Math.min(e.A[1],e.B[1])<GZ[0]&&Math.max(e.A[1],e.B[1])>GZ[1];
  const arcadeHoles=e=>{const L=edgeLen(e),res=[];for(let k=0;k<5;k++){const z=4.9+3*k,u=Math.abs(z-e.A[1])/Math.abs(e.B[1]-e.A[1])*L;res.push({u0:u-1.4,u1:u+1.4,y0:1.4,y1:5.35,noReveal:true});}return res;};
  const patchRng=rng(1234);
  const patches=(e,u0,yLo,yHi,mat,tint,bat,per=9)=>{if(LOW)return;const L=edgeLen(e),n=Math.floor(L/per);for(let k=0;k<n;k++){const w=2+patchRng()*3.2,h=1.4+patchRng()*2.4,u=(k+.2+patchRng()*.6)*L/n;if(u<w/2+.3||u>L-w/2-.3)continue;facePatch(e,u,yLo+patchRng()*(yHi-yLo),w,h,mat,tint,{bat,seed:k+u0|0});}};
  // portals (tunnel mouths with brick surrounds): Puerta de las Armas (north face of its tower) and the Puerta de la Tahona (Cubo)
  const PORTALS=[{x:-210.85,z:-6.9,w:2.2,h:3.8,m:.3},{x:-134.8,z:-26,w:2.6,h:4.0},{x:-121.6,z:-26,w:2.6,h:4.0}];
  const portalHoles=(e,yBase)=>{const res=[],pl=[];for(const p of PORTALS)if(onEdge(e,p.x,p.z)){const u=uOn(e,p.x,p.z),y=(yBase??footAt(p.x,p.z))+.3;res.push({u0:u-p.w/2-(p.m??.5),u1:u+p.w/2+(p.m??.5),y0:y-.35,y1:y+p.h+.4,noReveal:true});pl.push({u,y,w:p.w,h:p.h,m:p.m??.5});}return {res,pl};};
  // ---- wall mass: outer faces (outline) -------------------------------------------------------
  let u=0,gateOut=null;
  for(const e of outEdges){
    const cv=covered(e),mx=(e.A[0]+e.B[0])/2,mz=(e.A[1]+e.B[1])/2,north=mz<10&&mx>-215&&mx<-150;
    const mat=north?'alcTapialA':mx<-215?'alcTapialC':'alcTapialB',bat=y=>.05*(WALK-y);
    const gate=isGateEdge(e,-140.2,-137.5);if(gate)gateOut=e;
    const por=portalHoles(e);
    faceGrid({...e,...surf(mat),matLow:'alcTapialC',ySplit:-3,top:WALK+(cv?0:PARm),foot:footAt,bat,tint:tapT,u0:u,holes:gate?[gateU(e)]:por.res});
    for(const p of por.pl)platesOn(b,e,[p],bat,p.m);
    if(!cv){
      prism(e,-.5,0,WALK,WALK+PARm,mat,tapT,{u0:u,noTop:true,noOuter:true,noInner:false});prism(e,-.58,.07,WALK+PARm,WALK+PARm+.07,'alcCoping',tapT,{});
      merlons(b,e,-.25,WALK+PARm+.07,mat+'P');
    }
    if(!cv&&!gate&&edgeLen(e)>6)patches(e,u,2,WALK-2.5,'alcLimeB',limT,bat,12);
    {const len=edgeLen(e),ft=footAt(mx,mz);
      if(!LOW&&!cv&&len>9&&WALK-ft>13){const n=Math.floor(len/11);for(let k=0;k<n;k++){const uu=(k+.5)*len/n,px=lerp(e.A[0],e.B[0],uu/len),pz=lerp(e.A[1],e.B[1],uu/len);buttress(e,uu,1.5,.85,footAt(px,pz)-.6,WALK-.35,bat,mat,tapT);}}}
    u+=edgeLen(e);
  }
  // ---- wall mass: plaza faces ---------------------------------------------------------------
  u=0;let gateIn=null;
  const gapX=[-155.5,-150];
  for(const e of holeEdges){
    const k=((e.idx+1)%nH===e.idx2)?e.idx2:e.idx,silent=!!HOLE[k][2];
    if(silent){u+=edgeLen(e);continue;}
    const cv=covered(e),mx=(e.A[0]+e.B[0])/2,mz=(e.A[1]+e.B[1])/2,mat=mz>30?'alcTapialB':mx<-190?'alcTapialC':mx>-150?'alcBcA':'alcTapialA',bat=y=>.02*(WALK-y);
    const gate=isGateEdge(e,-145.5,-143),south=Math.abs(e.A[1]-36.2)<.5&&Math.abs(e.B[1]-36.2)<.5&&edgeLen(e)>40;
    if(gate)gateIn=e;
    const arcade=e.A[0]>-144&&e.A[0]<-142&&e.B[0]>-144&&e.B[0]<-142&&Math.max(e.A[1],e.B[1])>15&&Math.min(e.A[1],e.B[1])<5;
    faceGrid({...e,...surf(mat),top:WALK+(cv?0:.55),foot:()=>0,bat,tint:mat==='alcBcA'?limT:tapT,u0:u,holes:gate?[gateU(e)]:arcade?arcadeHoles(e):[]});
    if(arcade)for(let k=0;k<5;k++){const z=4.9+3*k,t=(z-e.A[1])/(e.B[1]-e.A[1]),px=lerp(e.A[0],e.B[0],t),pz=z,nl=Math.hypot(e.B[0]-e.A[0],e.B[1]-e.A[1]);nichePlate(b,px+.05,pz,-(e.B[1]-e.A[1])/nl,(e.B[0]-e.A[0])/nl,1.9,3.5,1.1,1.75);}
    if(!cv&&!gate&&!arcade&&edgeLen(e)>8)patches(e,u,1.5,WALK-2.5,'alcLimeB',limT,bat,10);
    if(south){
      const L=edgeLen(e),ta=(e.A[0]-gapX[1])/(e.A[0]-e.B[0]),tb=(e.A[0]-gapX[0])/(e.A[0]-e.B[0]);
      prism(subEdge(e,0,ta),-.4,0,WALK,WALK+.55,mat,tapT,{noTop:true,noOuter:true});prism(subEdge(e,tb,1),-.4,0,WALK,WALK+.55,mat,tapT,{noTop:true,noOuter:true});
      prism(subEdge(e,0,ta),-.5,.07,WALK+.55,WALK+.65,'alcCoping',tapT,{});prism(subEdge(e,tb,1),-.5,.07,WALK+.55,WALK+.65,'alcCoping',tapT,{});
      blockEdge(b,subEdge(e,0,ta),.25,3);blockEdge(b,subEdge(e,ta,tb),.25,3);blockEdge(b,subEdge(e,tb,1),.25,3);
      b.nav.floor(-173.5,37.6,50.4,1.55,WALK);
      b.nav.box(-177.1,36.6,43.2,.45,WALK,WALK+.55);b.nav.box(-148.55,36.5,2.9,.45,WALK,WALK+.55);b.nav.box(-173.6,38.65,50.4,.5,WALK,WALK+1.3);
    }else if(gate){
      const t0=(GZ[0]-e.A[1])/(e.B[1]-e.A[1]),t1=(GZ[1]-e.A[1])/(e.B[1]-e.A[1]);
      if(!cv){prism(subEdge(e,0,Math.min(t0,t1)),-.4,0,WALK,WALK+.55,mat,tapT,{noTop:true,noOuter:true});prism(subEdge(e,Math.max(t0,t1),1),-.4,0,WALK,WALK+.55,mat,tapT,{noTop:true,noOuter:true});}
      const tl=(24.6-e.A[1])/(e.B[1]-e.A[1]),tr=(28.4-e.A[1])/(e.B[1]-e.A[1]),lo=Math.min(tl,tr),hi=Math.max(tl,tr);
      blockEdge(b,subEdge(e,0,lo),.25,5.6);blockEdge(b,subEdge(e,hi,1),.25,5.6);
    }else{
      if(!cv)prism(e,-.4,0,WALK,WALK+.55,mat,tapT,{noTop:true,noOuter:true});
      blockEdge(b,e,.25,3);
    }
    u+=edgeLen(e);
  }
  if(gateIn&&gateOut){
    const zi=GZc,xi=lerp(gateIn.A[0],gateIn.B[0],(zi-gateIn.A[1])/(gateIn.B[1]-gateIn.A[1])),xo=lerp(gateOut.A[0],gateOut.B[0],(zi-gateOut.A[1])/(gateOut.B[1]-gateOut.A[1]));
    gatePassage(b,(xi+xo)/2,zi,xo-xi,Math.PI/2);
    boxMesh(xi-.05,0,zi-1.9,xo+.05,.02,zi+1.9,'alcCobble',gT,{noSides:true});
  }
  // ---- top surface of the mass ---------------------------------------------------------------
  fillPoly(OUTLINE,[HOLE.map(p=>[p[0],p[1]])],WALK,'alcCobble',gT);
  // ---- stair to the south wall walk ------------------------------------------------------------
  {
    const st=tinter('ground',11);
    stairRun(-173,34.9,-153.4,34.9,2.0,0,WALK,st,-.1,'alcLimeA');
    for(const [ax,ah] of [[-166.6,2.3],[-162.6,3.4],[-158.6,4.5]])nichePlate(b,ax,33.9,0,-1,1.7,ah,1.0,0,'alcBrickAP',.45,false,-.02);
    boxMesh(-153.4,0,33.9,-147.7,WALK,36.15,'alcBrickA',st,{});
    b.nav.ramp(-163.2,34.9,2,19.6,0,WALK,Math.PI/2);b.nav.floor(-150.5,35.9,5.8,4.9,WALK);
    b.line([-173,.95,33.95],[-153.4,WALK+.95,33.95],.04,'alcDark');for(let k=0;k<=10;k++){const x=lerp(-173,-153.4,k/10);b.line([x,lerp(0,WALK,k/10),33.95],[x,lerp(0,WALK,k/10)+.95,33.95],.035,'alcDark');}
    b.line([-153.4,WALK+.95,33.95],[-147.7,WALK+.95,33.95],.04,'alcDark');
  }
  // ---- towers: upper bodies (towers standing outside the wall mass rise from the slope) --------------------------
  let ti=0;
  for(const [name,t] of Object.entries(TOWERS)){
    const edges=orient(t.pts,true),mat=t.round?'alcBcB':t.lime?'alcLime'+t.lime:'alcTapialA',tint=t.lime?limT:tapT,full=!!t.full,base=full?footAt:()=>WALK;
    const bat=full?(y=>.05*(t.top-y)+(y<3?(3-y)*.18:0)):(y=>-.02*(y-WALK));let uu=0;ti++;
    for(const e of edges){
      const L=edgeLen(e),y0w=full?3:WALK+1.5,specs=t.round?[]:winSpecs(e,ti*31+edges.indexOf(e),y0w,t.top-3.4,name==='homenaje'||name==='quebrada'?4.6:6.5,.8,name==='homenaje'?1.7:1.3);
      const por=full?portalHoles(e):{res:[],pl:[]};
      const holes=[...specHoles(specs),...por.res,...(t.round||t.lime?[]:towerHoles(e,ti*17+edges.indexOf(e),WALK,t.top).filter(h=>!specs.some(sp=>Math.abs((h.u0+h.u1)/2-sp.u)<2)))];
      faceGrid({...e,...surf(mat),matLow:full?'alcTapialC':undefined,ySplit:-3,top:t.top,foot:base,bat,tint,u0:uu,disp:.03,holes});
      platesOn(b,e,specs,bat);for(const p of por.pl)platesOn(b,e,[p],bat,p.m);
      if(name==='quebrada'&&e.A[0]<-143&&e.B[0]<-143)crackOn(e,L*.62,WALK+.2,t.top-.2,bat,7);
      if(!t.round&&L>3&&!LOW||(!t.round&&L>3&&t.top>20)){const yq0=full?footAt(e.A[0],e.A[1])-.3:WALK,yq1=t.top-.95;strip(e,0,.85,yq0,yq1,bat,'alcBrickB',(x,y,z)=>{const c=tint(x,y,z);return [c[0]*.92,c[1]*.88,c[2]*.84];});strip(e,L-.85,L,yq0,yq1,bat,'alcBrickB',(x,y,z)=>{const c=tint(x,y,z);return [c[0]*.92,c[1]*.88,c[2]*.84];});}
      if(!t.round&&L>5)patches(e,uu,(full?3:WALK)+2,t.top-2,t.lime?'alcBrickA':'alcLimeA',t.lime?tapT:limT,bat,t.lime?8:7);
      prism(e,-.25,.1,t.top-.95,t.top-.6,'alcCoping',tint,{u0:uu});   // string course below the parapet
      if(t.round||full){prism(e,bat(t.top-5.6)-.1,bat(t.top-5.6)+.16,t.top-5.9,t.top-5.55,'alcCoping',tint,{noInner:true,u0:uu});}
      prism(e,-.55,.0,t.top,t.top+PARm,mat,tint,{u0:uu,noTop:true,noOuter:false});
      prism(e,-.62,.07,t.top+PARm,t.top+PARm+.07,'alcCoping',tint,{noInner:false});
      if(t.round){/* gun platform parapet: solid with cannon embrasures */prism(e,-.55,0,t.top+PARm+.07,t.top+PARm+1.0,mat,tint,{noTop:false,noOuter:false,noInner:false});}
      else merlons(b,e,-.27,t.top+PARm+.07,mat+'P');
      if(!full)blockEdge(b,e,0,0.01,WALK,t.top);
      uu+=L;
    }
    fillPoly(t.pts,[],t.top,'alcCobble',gT);
  }
  // ---- perimeter curtain walls --------------------------------------------------------------------
  const cm={mat:'alcTapialB',matIn:'alcBcB',tint:tapT,merl:true};
  curtain(b,[[-132,-36],[-147,-38],[-147,-35],[-166,-22],[-191,-8],[-193,-11],[-201,-7]],{...cm,top:7.6,T:2.6,mat:'alcTapialA'});
  curtain(b,[[-211,-9],[-210,-5],[-239.8,.5]],{...cm,top:7.6,T:2.4,mat:'alcTapialC'});
  curtain(b,[[-249.2,4.3],[-289,15],[-290,11],[-294,13],[-297,16],[-299,20],[-299,24],[-298,28],[-296,32],[-287,37],[-289,39],[-276,50],[-272,51],[-271,47],[-260,46],[-254,46],[-248,47],[-235,48]],{...cm,top:5.6,T:2.4,mat:'alcBcA',matIn:'alcBcA',batter:.08});
  curtain(b,[[-235,48],[-233,48],[-232,57],[-215,58],[-214,48]],{...cm,top:6.6,T:2.4,mat:'alcBcB',matIn:'alcBcB'});
  // the outer wall of the Jardin de los Adarves: its walk is level with the garden, with a parapet to look over the city
  curtain(b,[[-214,48],[-134,52]],{...cm,top:-.03,T:2.4,par:1.0,parIn:0,parBlock:true,merl:false,mat:'alcBcB',matIn:'alcBcB'});
  // ---- barrio castrense ------------------------------------------------------------------------------
  const holes=houses(b,gT),fh=plazaFeatures(b,gT),allHoles=holes.concat(fh.filter((_,k)=>k<2));
  ground(b,allHoles,gT);revellin(b,gT);weeds(b,holes.concat(fh));
  vela(b);velaTop(b);
  flush(b);
  console.log('alcazaba tris',TRIS);
}
