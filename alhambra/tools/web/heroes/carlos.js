import * as THREE from 'three';
import { random } from '../materials.js';

// Palacio de Carlos V (Pedro Machuca, 1527-). A 63 m square, 17.3 m high, two orders, around a 31 m circular
// courtyard of 32 Doric + 32 Ionic columns of Sierra Elvira pudding stone. Everything is written as merged
// triangle soups in building-local coordinates (u east-ish, v south-ish) rotated 11 degrees onto the OSM outline.
// Heights follow Uhde's measured plate (Baudenkmaeler in Spanien, pl. 6) and Machuca's west-front study (MET):
// plinth 0.8 / rusticated storey to 8.0 / string course to 8.55 / Ionic storey to 15.55 / cornice to 17.3.

const CX=-21.0, CZ=54.9, TH=11.0*Math.PI/180, H=31.5;      // centre of the courtyard, rotation, half side
const cT=Math.cos(TH), sT=Math.sin(TH);
const L2W=(u,v)=>[CX+u*cT-v*sT, CZ+u*sT+v*cT];
const LDIR=(u,v)=>[u*cT-v*sT, u*sT+v*cT];
const RC=15.4, RW=20.2, NCOL=32, DA=Math.PI*2/NCOL;           // column ring radius, gallery wall radius
const Y={plinth:.8, rusticTop:8.0, floor:8.55, pilTop:15.55, top:17.3};
const YG={lowTop:7.15, floor:7.2, upCol:8.65, upTop:13.75};     // courtyard gallery levels

// ---------------------------------------------------------------- noise / weathering
const ihash=(x,y,z)=>{let h=(Math.imul(x,374761393)+Math.imul(y,668265263)+Math.imul(z,1274126177))|0;h=Math.imul(h^(h>>>13),1274126177);return ((h^(h>>>16))>>>0)/4294967296;};
const sm=t=>t*t*(3-2*t);
function vn(x,y=0,z=0){
  const xi=Math.floor(x),yi=Math.floor(y),zi=Math.floor(z),xf=sm(x-xi),yf=sm(y-yi),zf=sm(z-zi);
  const a=(i,j,k)=>ihash(xi+i,yi+j,zi+k),l=(p,q,t)=>p+(q-p)*t;
  return l(l(l(a(0,0,0),a(1,0,0),xf),l(a(0,1,0),a(1,1,0),xf),yf),l(l(a(0,0,1),a(1,0,1),xf),l(a(0,1,1),a(1,1,1),xf),yf),zf);
}
// Multiplier applied through vertex colours: blotches, ground dirt, soot streaks under the ledges.
function weather(x,y,z,tint=[1,1,1]){
  const a=vn(x*.21,y*.09,z*.21), b=vn(x*1.1,y*.5,z*1.1), s=vn((x+z)*2.7,y*.12,(x-z)*.9);
  let k=.93+.12*a+.06*b;
  k*=1-.24*Math.exp(-Math.max(0,y)/1.5);
  for(const L of [Y.rusticTop,Y.floor+.3,Y.top-.4,8.4]){const q=L-y;if(q>0&&q<1.1)k*=1-.20*(1-q/1.1)*(.35+s);}
  k*=1-.10*Math.max(0,s-.55)*(y>3?1:0);
  return [k*1.0*tint[0],k*.985*tint[1],k*.955*tint[2]];
}
const FACE_TINT={carS:[1.03,1.0,.96],carW:[1.0,1.0,1.0],carN:[.9,.91,.95],carE:[.95,.94,.92],carCourt:[1,.99,.97],carVest:[.8,.8,.82],carRoof:[1,1,1]};
const NOWF=()=>[1,1,1];

// ---------------------------------------------------------------- triangle soup
class Soup{
  constructor(wf){this.p=[];this.n=[];this.t=[];this.c=[];this.wf=wf||NOWF;this.tone=1;this.hue=[1,1,1];this.count=0;}
  tri(A,B,C,ua,ub,uc,hint,na,nb,nc){
    let ax=B[0]-A[0],ay=B[1]-A[1],az=B[2]-A[2],bx=C[0]-A[0],by=C[1]-A[1],bz=C[2]-A[2];
    let nx=ay*bz-az*by,ny=az*bx-ax*bz,nz=ax*by-ay*bx;const l=Math.hypot(nx,ny,nz);if(l<1e-9)return;
    if(hint&&nx*hint[0]+ny*hint[1]+nz*hint[2]<0){[B,C]=[C,B];[ub,uc]=[uc,ub];[nb,nc]=[nc,nb];nx=-nx;ny=-ny;nz=-nz;}
    nx/=l;ny/=l;nz/=l;
    const V=[A,B,C],U=[ua,ub,uc],N=[na,nb,nc];
    for(let i=0;i<3;i++){const v=V[i],u=U[i]||[0,0],n=N[i]||[nx,ny,nz];this.p.push(v[0],v[1],v[2]);this.n.push(n[0],n[1],n[2]);this.t.push(u[0],u[1]);const c=this.wf(v[0],v[1],v[2]),k=this.tone,hu=this.hue;this.c.push(c[0]*k*hu[0],c[1]*k*hu[1],c[2]*k*hu[2]);}
    this.count++;
  }
  quad(A,B,C,D,ua,ub,uc,ud,hint,na,nb,nc,nd){this.tri(A,B,C,ua,ub,uc,hint,na,nb,nc);this.tri(A,C,D,ua,uc,ud,hint,na,nc,nd);}
  geometry(){
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(this.p,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(this.n,3));
    g.setAttribute('uv',new THREE.Float32BufferAttribute(this.t,2));g.setAttribute('color',new THREE.Float32BufferAttribute(this.c,3));return g;
  }
}

// ---------------------------------------------------------------- frames
// A frame sits on a wall: t = to the viewer's right, y up, d = out of the wall towards the viewer.
function makeFrame(ox,oz,nx,nz){
  const rx=nz,rz=-nx;
  return {ox,oz,nx,nz,rx,rz,pt:(t,y,d)=>[ox+rx*t+nx*d,y,oz+rz*t+nz*d],dt:[rx,0,rz],dd:[nx,0,nz],rot:Math.atan2(-rz,rx)};
}
const SIDE={S:[0,1],E:[1,0],N:[0,-1],W:[-1,0]};
function sideFrame(s){const [nu,nv]=SIDE[s],[ox,oz]=L2W(nu*H,nv*H),[nx,nz]=LDIR(nu,nv);const F=makeFrame(ox,oz,nx,nz);F.side=s;return F;}
// Gallery-wall frame at polar angle a (local u=r cos a, v=r sin a); faces the courtyard centre.
function wallFrame(a,r){const [ox,oz]=L2W(r*Math.cos(a),r*Math.sin(a)),[nx,nz]=LDIR(-Math.cos(a),-Math.sin(a));return makeFrame(ox,oz,nx,nz);}

let LOW=false;
const UP=[0,1,0];
const sc=(v,k)=>[v[0]*k,v[1]*k,v[2]*k], ad=(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const comb=(F,nt,ny,nd)=>[F.dt[0]*nt+F.dd[0]*nd,ny,F.dt[2]*nt+F.dd[2]*nd];

// ---------------------------------------------------------------- primitives (all in frame coordinates)
function fbox(S,F,t0,t1,y0,y1,d0,d1,o={}){
  const P=F.pt,uo=o.uo||0,vo=o.vo||0;
  S.quad(P(t0,y0,d1),P(t1,y0,d1),P(t1,y1,d1),P(t0,y1,d1),[t0+uo,y0+vo],[t1+uo,y0+vo],[t1+uo,y1+vo],[t0+uo,y1+vo],F.dd);
  if(!o.nt)S.quad(P(t0,y1,d1),P(t1,y1,d1),P(t1,y1,d0),P(t0,y1,d0),[t0+uo,d1],[t1+uo,d1],[t1+uo,d0],[t0+uo,d0],UP);
  if(!o.nb)S.quad(P(t0,y0,d0),P(t1,y0,d0),P(t1,y0,d1),P(t0,y0,d1),[t0+uo,d0],[t1+uo,d0],[t1+uo,d1],[t0+uo,d1],[0,-1,0]);
  if(!o.nl)S.quad(P(t0,y0,d0),P(t0,y0,d1),P(t0,y1,d1),P(t0,y1,d0),[d0,y0+vo],[d1,y0+vo],[d1,y1+vo],[d0,y1+vo],sc(F.dt,-1));
  if(!o.nr)S.quad(P(t1,y0,d1),P(t1,y0,d0),P(t1,y1,d0),P(t1,y1,d1),[d1,y0+vo],[d0,y0+vo],[d0,y1+vo],[d1,y1+vo],F.dt);
}
// Extrude a (d,y) profile polygon (solid on the left of travel = CCW) along t.
function moulding(S,F,t0,t1,prof,o={}){
  const n=prof.length,P=F.pt;let len=0;
  for(let i=0;i<n;i++){
    const p=prof[i],q=prof[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    const hint=comb(F,0,-ex/l,ey/l);   // right normal (ey,-ex) -> (d,y)
    const nd=ey/l,ny=-ex/l,h=comb(F,0,ny,nd);
    S.quad(P(t0,p[1],p[0]),P(t1,p[1],p[0]),P(t1,q[1],q[0]),P(t0,q[1],q[0]),[t0,len],[t1,len],[t1,len+l],[t0,len+l],h);
    len+=l;
  }
  if(o.caps){const pts=prof.map(p=>new THREE.Vector2(p[0],p[1]));let cl=pts.slice();if(THREE.ShapeUtils.isClockWise(cl))cl.reverse();const tr=THREE.ShapeUtils.triangulateShape(cl,[]);
    for(const [a,b,c] of tr){S.tri(P(t1,cl[a].y,cl[a].x),P(t1,cl[b].y,cl[b].x),P(t1,cl[c].y,cl[c].x),[cl[a].x,cl[a].y],[cl[b].x,cl[b].y],[cl[c].x,cl[c].y],F.dt);S.tri(P(t0,cl[a].y,cl[a].x),P(t0,cl[b].y,cl[b].x),P(t0,cl[c].y,cl[c].x),[cl[a].x,cl[a].y],[cl[b].x,cl[b].y],[cl[c].x,cl[c].y],sc(F.dt,-1));}}
}
// Vertical prism over a (t,d) polygon (CCW seen from above with t right, d up-the-page = outward).
function vprism(S,F,poly,y0,y1,o={}){
  const n=poly.length,P=F.pt;let len=0;
  let area=0;for(let i=0;i<n;i++){const p=poly[i],q=poly[(i+1)%n];area+=p[0]*q[1]-q[0]*p[1];}
  const pl=area<0?poly.slice().reverse():poly;
  for(let i=0;i<n;i++){
    const p=pl[i],q=pl[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    // viewed from above in (t,d): right normal of CCW edge is outward (ey,-ex)
    const h=comb(F,ey/l,0,-ex/l);
    S.quad(P(p[0],y0,p[1]),P(q[0],y0,q[1]),P(q[0],y1,q[1]),P(p[0],y1,p[1]),[len,y0],[len+l,y0],[len+l,y1],[len,y1],h);len+=l;
  }
  if(!o.notop){const cl=pl.map(p=>new THREE.Vector2(p[0],p[1]));const tr=THREE.ShapeUtils.triangulateShape(cl,[]);for(const [a,b,c] of tr)S.tri(P(pl[a][0],y1,pl[a][1]),P(pl[b][0],y1,pl[b][1]),P(pl[c][0],y1,pl[c][1]),[pl[a][0],pl[a][1]],[pl[b][0],pl[b][1]],[pl[c][0],pl[c][1]],UP);}
}
// Flat plate in the (t,y) plane with holes, thickness d0..d1; the front face is at d1.
function plate(S,F,cont,holes,d0,d1,o={}){
  const area=a=>{let s=0;for(let i=0;i<a.length;i++){const p=a[i],q=a[(i+1)%a.length];s+=p[0]*q[1]-q[0]*p[1];}return s/2;};
  const C=area(cont)<0?cont.slice().reverse():cont,Hs=holes.map(h=>area(h)>0?h.slice().reverse():h),pts=[...C,...Hs.flat()],P=F.pt;
  const tr=THREE.ShapeUtils.triangulateShape(C.map(p=>new THREE.Vector2(p[0],p[1])),Hs.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1]))));
  const uo=o.uo||0,vo=o.vo||0;
  for(const [a,b,c] of tr){const A=pts[a],B=pts[b],Cc=pts[c];
    if(!o.nofront)S.tri(P(A[0],A[1],d1),P(B[0],B[1],d1),P(Cc[0],Cc[1],d1),[A[0]+uo,A[1]+vo],[B[0]+uo,B[1]+vo],[Cc[0]+uo,Cc[1]+vo],F.dd);
    if(o.back)S.tri(P(A[0],A[1],d0),P(B[0],B[1],d0),P(Cc[0],Cc[1],d0),[A[0]+uo,A[1]+vo],[B[0]+uo,B[1]+vo],[Cc[0]+uo,Cc[1]+vo],sc(F.dd,-1));}
  if(d1-d0<1e-4)return;
  for(const loop of [C,...Hs]){let len=0;for(let i=0;i<loop.length;i++){const p=loop[i],q=loop[(i+1)%loop.length],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    S.quad(P(p[0],p[1],d0),P(q[0],q[1],d0),P(q[0],q[1],d1),P(p[0],p[1],d1),[len,d0],[len+l,d0],[len+l,d1],[len,d1],comb(F,ey/l,-ex/l,0));len+=l;}}
}
// Revolve a (r,dd) profile around an axis along d at frame point (t,y) (round things on walls: oculi, tondi, rings).
function frev(S,F,tc,yc,prof,seg=24,o={}){
  if(LOW)seg=Math.max(8,seg*.6|0);
  const n=prof.length,P=F.pt,close=o.closed!==false;const m=close?n:n-1;
  for(let i=0;i<m;i++){
    const p=prof[i],q=prof[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    const nr=ey/l,nd=-ex/l;
    for(let j=0;j<seg;j++){
      const a0=j/seg*Math.PI*2,a1=(j+1)/seg*Math.PI*2,c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1);
      const A=P(tc+p[0]*c0,yc+p[0]*s0,p[1]),B=P(tc+q[0]*c0,yc+q[0]*s0,q[1]),C=P(tc+q[0]*c1,yc+q[0]*s1,q[1]),D=P(tc+p[0]*c1,yc+p[0]*s1,p[1]);
      const n0=comb(F,nr*c0,nr*s0,nd),n1=comb(F,nr*c1,nr*s1,nd),hint=ad(n0,n1);
      S.quad(A,B,C,D,[a0*p[0],p[1]],[a0*q[0],q[1]],[a1*q[0],q[1]],[a1*p[0],p[1]],hint,o.flat?undefined:n0,o.flat?undefined:n0,o.flat?undefined:n1,o.flat?undefined:n1);
    }
  }
}
// Revolve a (r,y) profile about the vertical axis at building-local (u0,v0) (columns, courtyard rings).
function rev(S,u0,v0,prof,seg=32,o={}){
  if(LOW&&seg>40)seg>>=1;else if(LOW)seg=Math.max(10,seg*.6|0);
  const n=prof.length,close=o.closed!==false,m=close?n:n-1,a0=o.a0||0,a1=o.a1===undefined?Math.PI*2:o.a1,R0=o.uvr||prof[0][0]||1;
  for(let i=0;i<m;i++){
    const p=prof[i],q=prof[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    const nr=ey/l,ny=-ex/l;
    for(let j=0;j<seg;j++){
      const b0=a0+(a1-a0)*j/seg,b1=a0+(a1-a0)*(j+1)/seg,c0=Math.cos(b0),s0=Math.sin(b0),c1=Math.cos(b1),s1=Math.sin(b1);
      const W=(r,y,c,s)=>{const [x,z]=L2W(u0+r*c,v0+r*s);return [x,y,z];};
      const A=W(p[0],p[1],c0,s0),B=W(q[0],q[1],c0,s0),C=W(q[0],q[1],c1,s1),D=W(p[0],p[1],c1,s1);
      const N0=(c,s)=>{const [x,z]=LDIR(nr*c,nr*s);return [x,ny,z];},n0=N0(c0,s0),n1=N0(c1,s1),hint=ad(n0,n1);
      const ua=b0*R0,ub=b1*R0;
      S.quad(A,B,C,D,[ua,p[1]],[ua,q[1]],[ub,q[1]],[ub,p[1]],hint,o.flat?undefined:n0,o.flat?undefined:n0,o.flat?undefined:n1,o.flat?undefined:n1);
    }
  }
}
function ellipsoid(S,F,t,y,d,rt,ry,rd,nl=6,nm=10){
  if(LOW){nl=Math.min(nl,3);nm=Math.min(nm,5);}
  const P=(la,lo)=>{const cl=Math.cos(la),sl=Math.sin(la);return [F.pt(t+rt*cl*Math.cos(lo),y+ry*sl,d+rd*cl*Math.sin(lo)),comb(F,cl*Math.cos(lo)/rt,sl/ry,cl*Math.sin(lo)/rd)];};
  for(let i=0;i<nl;i++){const la0=-Math.PI/2+Math.PI*i/nl,la1=-Math.PI/2+Math.PI*(i+1)/nl;
    for(let j=0;j<nm;j++){const lo0=Math.PI*2*j/nm,lo1=Math.PI*2*(j+1)/nm,a=P(la0,lo0),b=P(la0,lo1),c=P(la1,lo1),dd=P(la1,lo0);
      S.quad(a[0],b[0],c[0],dd[0],[lo0,la0],[lo1,la0],[lo1,la1],[lo0,la1],ad(a[1],c[1]),a[1],b[1],c[1],dd[1]);}}
}
function disc(S,F,tc,yc,r,d,seg=24){
  for(let j=0;j<seg;j++){const a0=j/seg*Math.PI*2,a1=(j+1)/seg*Math.PI*2;
    S.tri(F.pt(tc,yc,d),F.pt(tc+r*Math.cos(a0),yc+r*Math.sin(a0),d),F.pt(tc+r*Math.cos(a1),yc+r*Math.sin(a1),d),[.5,.5],[.5+.5*Math.cos(a0),.5+.5*Math.sin(a0)],[.5+.5*Math.cos(a1),.5+.5*Math.sin(a1)],F.dd);}
}
const circ=(tc,yc,r,n=16,rev=false)=>{const a=[];for(let i=0;i<n;i++){const t=(rev?-1:1)*i/n*Math.PI*2;a.push([tc+r*Math.cos(t),yc+r*Math.sin(t)]);}return a;};
const rectp=(t0,t1,y0,y1)=>[[t0,y0],[t1,y0],[t1,y1],[t0,y1]];

// Chamfered block with a trapezoidal front (bottom edge t0..t1, top edge u0..u1).
function cblock(S,F,t0,t1,y0,y1,dF,c,u0=t0,u1=t1,o={}){
  const P=F.pt,O=[[t0,y0],[t1,y0],[u1,y1],[u0,y1]],jd=o.jit||0,cx=o.cx!==undefined?o.cx:c*1.5;
  const I=[[t0+cx,y0+c],[t1-cx,y0+c],[u1-cx,y1-c],[u0+cx,y1-c]];
  if(o.cl)I[0][0]=I[3][0]=O[0][0];if(o.cr)I[1][0]=I[2][0]=O[1][0];
  if(!o.nofront)S.quad(P(I[0][0],I[0][1],dF+jd),P(I[1][0],I[1][1],dF+jd),P(I[2][0],I[2][1],dF+jd),P(I[3][0],I[3][1],dF+jd),I[0],I[1],I[2],I[3],F.dd);
  for(let i=0;i<4;i++){const j=(i+1)%4,ex=O[j][0]-O[i][0],ey=O[j][1]-O[i][1],l=Math.hypot(ex,ey),h=ad(sc(F.dd,.7),comb(F,ey/l,-ex/l,0));
    if((i===3&&o.cl)||(i===1&&o.cr)){ // the plain end of a corner block: a square return
      S.quad(P(O[i][0],O[i][1],0),P(O[j][0],O[j][1],0),P(I[j][0],I[j][1],dF+jd),P(I[i][0],I[i][1],dF+jd),O[i],O[j],I[j],I[i],h);continue;}
    S.quad(P(O[i][0],O[i][1],0),P(O[j][0],O[j][1],0),P(I[j][0],I[j][1],dF+jd),P(I[i][0],I[i][1],dF+jd),O[i],O[j],I[j],I[i],h);}
}

// A profile running round the whole square (mitred corners); prof = (d,y) polygon CCW.
function ringLoop(S,prof,o={}){
  const n=prof.length;let len=0;
  for(const s of ['S','E','N','W']){
    const F=sideFrame(s);len=0;
    for(let i=0;i<n;i++){
      const p=prof[i],q=prof[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
      const e0=H+p[0],e1=H+q[0],h=comb(F,0,-ex/l,ey/l);
      S.quad(F.pt(-e0,p[1],p[0]),F.pt(e0,p[1],p[0]),F.pt(e1,q[1],q[0]),F.pt(-e1,q[1],q[0]),[-e0,len],[e0,len],[e1,len+l],[-e1,len+l],h);len+=l;
    }
  }
}


// ---------------------------------------------------------------- procedural stone textures
const cv=(w,h=w)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c;};
const ctex=(c,srgb=true)=>{const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=srgb?THREE.SRGBColorSpace:THREE.NoColorSpace;t.anisotropy=16;return t;};
const rgb=(c,k=1,a=1)=>`rgba(${Math.max(0,Math.min(255,c[0]*k))|0},${Math.max(0,Math.min(255,c[1]*k))|0},${Math.max(0,Math.min(255,c[2]*k))|0},${a})`;
function wrapDraw(S,x,y,r,fn){for(const dx of [-S,0,S])for(const dy of [-S,0,S])if(x+dx>-r&&x+dx<S+r&&y+dy>-r&&y+dy<S+r)fn(x+dx,y+dy);}
function blotches(g,S,rnd,n,rmin,rmax,cols,alpha){
  for(let i=0;i<n;i++){const x=rnd()*S,y=rnd()*S,r=rmin+rnd()*(rmax-rmin),c=cols[(rnd()*cols.length)|0];
    wrapDraw(S,x,y,r,(xx,yy)=>{const q=g.createRadialGradient(xx,yy,0,xx,yy,r);q.addColorStop(0,rgb(c,1,alpha*(.4+.6*rnd())));q.addColorStop(1,rgb(c,1,0));g.fillStyle=q;g.fillRect(xx-r,yy-r,r*2,r*2);});}
}
function speckle(g,S,rnd,n,alpha,size=2){for(let i=0;i<n;i++){const v=rnd()>.5?255:0;g.fillStyle=`rgba(${v},${v},${v},${rnd()*alpha})`;g.fillRect(rnd()*S,rnd()*S,1+rnd()*size,1+rnd()*size);}}
// Coursed ashlar: returns [colour, height]. rows = courses per tile.
function ashlarTex({S=1024,rows=4,seed=1,base=[200,166,112],spread=.07,joint=[96,78,54],jw=3,lenk=[1.7,3.0],patch=.5,streak=.5}){
  const rnd=random(seed),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle=rgb(joint);g.fillRect(0,0,S,S);hg.fillStyle='#262626';hg.fillRect(0,0,S,S);
  const ch=S/rows;
  for(let j=0;j<rows;j++){
    let x=-rnd()*ch*2;
    while(x<S){
      const bw=ch*(lenk[0]+rnd()*(lenk[1]-lenk[0])),k=1+(rnd()-.5)*2*spread,tint=[(rnd()-.5)*10,(rnd()-.5)*8,(rnd()-.5)*6];
      const col=[base[0]*k+tint[0],base[1]*k+tint[1],base[2]*k+tint[2]];
      for(const dx of [-S,0,S]){
        const xx=x+dx;if(xx>S||xx+bw<0)continue;
        g.fillStyle=rgb(col);g.fillRect(xx+jw/2,j*ch+jw/2,bw-jw,ch-jw);
        const hv=150+rnd()*40;hg.fillStyle=`rgb(${hv|0},${hv|0},${hv|0})`;hg.fillRect(xx+jw/2,j*ch+jw/2,bw-jw,ch-jw);
        // arris wear: lighter lower edge, darker top edge
        g.fillStyle='rgba(255,236,200,.07)';g.fillRect(xx+jw/2,j*ch+ch-jw/2-4,bw-jw,3);g.fillStyle='rgba(60,40,20,.10)';g.fillRect(xx+jw/2,j*ch+jw/2,bw-jw,3);
      }
      x+=bw;
    }
  }
  blotches(g,S,rnd,70,S*.03,S*.16,[[255,238,200],[120,90,56],[150,150,120],[214,176,112]],.06*patch);
  blotches(hg,S,rnd,160,S*.01,S*.06,[[60,60,60],[200,200,200]],.25);
  // vertical weathering streaks
  for(let i=0;i<60*streak;i++){const x=rnd()*S,len=S*(.1+rnd()*.35),y=rnd()*S,w=2+rnd()*6;const q=g.createLinearGradient(0,y,0,y+len);q.addColorStop(0,'rgba(60,45,30,0)');q.addColorStop(.3,`rgba(60,45,30,${.05+rnd()*.07})`);q.addColorStop(1,'rgba(60,45,30,0)');g.fillStyle=q;g.fillRect(x,y,w,len);}
  speckle(g,S,rnd,70000,.07,3);speckle(hg,S,rnd,50000,.18,3);
  return [c,h];
}
// Rusticated block face: chisel punch marks (small wedge-shaped pits, ~3.5 cm, irregular) on a 0.9 m tile.
function rusticTex(){
  const S=1024,rnd=random(77),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d'),base=[200,172,132];
  g.fillStyle=rgb(base);g.fillRect(0,0,S,S);hg.fillStyle='#9a9a9a';hg.fillRect(0,0,S,S);
  blotches(g,S,rnd,220,S*.02,S*.14,[[238,208,166],[130,104,80],[170,146,122],[208,174,128]],.2);
  // fine tooling: many short strokes along one diagonal
  for(let i=0;i<9000;i++){const x=rnd()*S,y=rnd()*S,l=4+rnd()*10;g.strokeStyle=rnd()>.5?'rgba(255,230,190,.07)':'rgba(70,40,20,.08)';g.lineWidth=1+rnd()*1.5;g.beginPath();g.moveTo(x,y);g.lineTo(x+l*.8,y+l*.6);g.stroke();}
  const n=18,st=S/n;
  for(let r=0;r<n;r++)for(let q=0;q<n;q++){
    if(rnd()<.05)continue;
    const x=(q+.5+(r%2)*.5)*st+(rnd()-.5)*st*.7,y=(r+.5)*st+(rnd()-.5)*st*.7,w=st*(.12+rnd()*.12),hh=st*(.1+rnd()*.1),tilt=(rnd()-.5)*1.4;
    for(const dx of [-S,0,S])for(const dy of [-S,0,S]){const xx=x+dx,yy=y+dy;if(xx<-w||xx>S+w||yy<-hh*2||yy>S+hh*2)continue;
      g.save();g.translate(xx,yy);g.rotate(tilt);
      g.fillStyle='rgba(60,38,24,.38)';g.beginPath();g.moveTo(-w,-hh*.5);g.lineTo(w,-hh*.5);g.lineTo(w*.15,hh);g.closePath();g.fill();
      g.fillStyle='rgba(255,226,186,.12)';g.beginPath();g.moveTo(-w*.9,hh*.65);g.lineTo(w*.15,hh*1.15);g.lineTo(w*.95,-hh*.3);g.lineTo(w*1.1,-hh*.3);g.lineTo(w*.25,hh*1.25);g.closePath();g.fill();
      hg.save();hg.translate(xx,yy);hg.rotate(tilt);hg.fillStyle='#383838';hg.beginPath();hg.moveTo(-w,-hh*.5);hg.lineTo(w,-hh*.5);hg.lineTo(w*.15,hh);hg.closePath();hg.fill();hg.restore();g.restore();}
  }
  blotches(hg,S,rnd,240,S*.008,S*.04,[[120,120,120],[190,190,190]],.3);
  speckle(g,S,rnd,90000,.09,3);speckle(hg,S,rnd,60000,.2,3);
  return [c,h];
}
// Sierra Elvira stone of the portals: blue-grey limestone, iron staining, fine joints.
function marbleTex(){
  const S=1024,rnd=random(31),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle='rgb(158,156,150)';g.fillRect(0,0,S,S);hg.fillStyle='#b4b4b4';hg.fillRect(0,0,S,S);
  blotches(g,S,rnd,140,S*.04,S*.25,[[190,185,170],[120,125,130],[196,150,110],[140,142,140]],.22);
  for(let i=0;i<70;i++){const x=rnd()*S,y=rnd()*S,len=S*(.08+rnd()*.3);const q=g.createLinearGradient(0,y,0,y+len);const col=rnd()>.4?'176,120,76':'70,66,62';q.addColorStop(0,`rgba(${col},0)`);q.addColorStop(.4,`rgba(${col},${.05+rnd()*.1})`);q.addColorStop(1,`rgba(${col},0)`);g.fillStyle=q;g.fillRect(x,y,2+rnd()*7,len);}
  g.strokeStyle='rgba(70,66,60,.55)';g.lineWidth=2.5;hg.strokeStyle='#505050';hg.lineWidth=3;
  for(const [a,bb] of [[0,512],[512,1024]]){g.beginPath();g.moveTo(0,a);g.lineTo(S,a);g.stroke();hg.beginPath();hg.moveTo(0,a);hg.lineTo(S,a);hg.stroke();}
  for(let j=0;j<2;j++){const off=j*512,xs=j?[256,768]:[0,512];for(const x of xs){g.beginPath();g.moveTo(x,off);g.lineTo(x,off+512);g.stroke();hg.beginPath();hg.moveTo(x,off);hg.lineTo(x,off+512);hg.stroke();}}
  speckle(g,S,rnd,60000,.07,2);speckle(hg,S,rnd,40000,.14,2);
  return [c,h];
}
// Pudding stone (conglomerate): a mauve-brown matrix full of fine reddish and grey grains with a few big pale pebbles
// (colours sampled by eye from Jl FilpoC's/ Kasia's column photographs).
function puddingTex(){
  const S=1024,rnd=random(55),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle='rgb(182,160,142)';g.fillRect(0,0,S,S);hg.fillStyle='#707070';hg.fillRect(0,0,S,S);
  blotches(g,S,rnd,120,S*.04,S*.16,[[200,180,160],[150,126,110],[186,174,166]],.22);
  const fine=[[148,104,88],[148,104,88],[134,96,84],[176,172,172],[180,176,178],[224,216,202],[140,146,158],[196,166,142],[112,88,80]];
  for(let i=0;i<24000;i++){
    const x=rnd()*S,y=rnd()*S,r=.9+Math.pow(rnd(),2.6)*7.5,e=.55+rnd()*.45,a=rnd()*Math.PI,col=fine[(rnd()*fine.length)|0],k=.88+rnd()*.24;
    wrapDraw(S,x,y,r*1.2,(xx,yy)=>{g.fillStyle=rgb(col,k,.92);g.beginPath();g.ellipse(xx,yy,r,r*e,a,0,7);g.fill();
      hg.fillStyle=rnd()>.5?'#9a9a9a':'#505050';hg.beginPath();hg.ellipse(xx,yy,r,r*e,a,0,7);hg.fill();});
  }
  for(let i=0;i<110;i++){
    const x=rnd()*S,y=rnd()*S,r=7+Math.pow(rnd(),1.8)*17,e=.6+rnd()*.4,a=rnd()*Math.PI,col=[[214,208,196],[190,186,178],[160,160,166],[176,150,132]][(rnd()*4)|0];
    wrapDraw(S,x,y,r*1.2,(xx,yy)=>{g.fillStyle='rgba(60,46,40,.35)';g.beginPath();g.ellipse(xx+.8,yy+.8,r+1.2,r*e+1.2,a,0,7);g.fill();g.fillStyle=rgb(col,1,.96);g.beginPath();g.ellipse(xx,yy,r,r*e,a,0,7);g.fill();
      hg.fillStyle='#2e2e2e';hg.beginPath();hg.ellipse(xx,yy,r+1.5,r*e+1.5,a,0,7);hg.fill();hg.fillStyle='#bdbdbd';hg.beginPath();hg.ellipse(xx,yy,r*.92,r*e*.92,a,0,7);hg.fill();});
  }
  speckle(g,S,rnd,40000,.07,2);
  return [c,h];
}
function cobbleTex(){
  const S=1024,rnd=random(12),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle='rgb(104,98,90)';g.fillRect(0,0,S,S);hg.fillStyle='#202020';hg.fillRect(0,0,S,S);
  const n=11,st=S/n;
  for(let r=0;r<n;r++)for(let q=-1;q<=n;q++){
    const x=(q+(r%2)*.5)*st+(rnd()-.5)*st*.08,y=r*st+(rnd()-.5)*st*.08,w=st*(.84+rnd()*.1),hh=st*(.84+rnd()*.1),k=.8+rnd()*.4,tint=rnd();
    const col=tint>.85?[190,168,134]:tint>.5?[168,160,150]:[150,144,138];
    for(const dx of [-S,0,S])for(const dy of [-S,0,S]){
      g.fillStyle=rgb(col,k);g.beginPath();g.roundRect(x+dx+st*.05,y+dy+st*.05,w,hh,st*.16);g.fill();
      hg.fillStyle=`rgb(${(150+rnd()*50)|0},${(150+rnd()*50)|0},${(150+rnd()*50)|0})`;hg.beginPath();hg.roundRect(x+dx+st*.05,y+dy+st*.05,w,hh,st*.2);hg.fill();}
  }
  blotches(g,S,rnd,60,S*.05,S*.2,[[200,190,170],[40,36,30]],.12);speckle(g,S,rnd,40000,.08,2);
  return [c,h];
}
function slabTex({seed=5,base=[206,192,160],rows=2,wide=2.0,jc=[110,98,80]}){
  const S=1024,rnd=random(seed),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d'),ch=S/rows;
  g.fillStyle=rgb(jc);g.fillRect(0,0,S,S);hg.fillStyle='#303030';hg.fillRect(0,0,S,S);
  for(let j=0;j<rows;j++){let x=-rnd()*ch*2;while(x<S){const bw=ch*(wide*.8+rnd()*wide*.5),k=.92+rnd()*.16;
    for(const dx of [-S,0,S]){g.fillStyle=rgb(base,k);g.fillRect(x+dx+3,j*ch+3,bw-6,ch-6);hg.fillStyle='#b0b0b0';hg.fillRect(x+dx+3,j*ch+3,bw-6,ch-6);}x+=bw;}}
  blotches(g,S,rnd,80,S*.04,S*.2,[[240,230,205],[120,110,95],[160,150,140]],.14);speckle(g,S,rnd,60000,.07,2);speckle(hg,S,rnd,40000,.1,2);
  return [c,h];
}
function roofTex(){
  const S=1024,rnd=random(23),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle='rgb(110,64,46)';g.fillRect(0,0,S,S);hg.fillStyle='#202020';hg.fillRect(0,0,S,S);
  const pairs=6,pw=S/pairs,rows=2,rh=S/rows;
  for(let r=0;r<rows;r++)for(let p=0;p<pairs;p++){
    const k=.8+rnd()*.4,hueShift=rnd()*22,col=[184+hueShift,112+hueShift*.5,76+hueShift*.2],x0=p*pw,y0=r*rh;
    // pan (valley) tile
    let gr=g.createLinearGradient(x0,0,x0+pw,0);gr.addColorStop(0,rgb(col,.4));gr.addColorStop(.3,rgb(col,.62*k));gr.addColorStop(.7,rgb(col,.62*k));gr.addColorStop(1,rgb(col,.4));g.fillStyle=gr;g.fillRect(x0,y0,pw,rh);
    // cover (ridge) tile
    const cw=pw*.52,cx=x0+pw/2-cw/2;gr=g.createLinearGradient(cx,0,cx+cw,0);gr.addColorStop(0,rgb(col,.62*k));gr.addColorStop(.28,rgb(col,1.12*k));gr.addColorStop(.62,rgb(col,.95*k));gr.addColorStop(1,rgb(col,.55*k));g.fillStyle=gr;g.fillRect(cx,y0,cw,rh*.96);
    g.fillStyle='rgba(40,18,12,.55)';g.fillRect(cx,y0+rh*.94,cw,rh*.06);
    gr=hg.createLinearGradient(cx,0,cx+cw,0);gr.addColorStop(0,'#404040');gr.addColorStop(.5,'#f0f0f0');gr.addColorStop(1,'#404040');hg.fillStyle=gr;hg.fillRect(cx,y0,cw,rh*.96);
    hg.fillStyle='#101010';hg.fillRect(cx,y0+rh*.94,cw,rh*.06);
    if(rnd()<.18){g.fillStyle='rgba(176,178,150,.26)';g.beginPath();g.ellipse(cx+cw*rnd(),y0+rh*rnd(),cw*.3,rh*.12,0,0,7);g.fill();}
  }
  blotches(g,S,rnd,50,S*.03,S*.2,[[220,150,110],[60,30,20]],.1);speckle(g,S,rnd,50000,.07,2);
  return [c,h];
}
function woodTex(){
  const S=1024,rnd=random(64),c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d');
  g.fillStyle='rgb(88,58,38)';g.fillRect(0,0,S,S);hg.fillStyle='#909090';hg.fillRect(0,0,S,S);
  for(let i=0;i<260;i++){const y=rnd()*S,w=.8+rnd()*3;g.fillStyle=`rgba(${rnd()>.5?'40,24,14':'150,104,66'},${.06+rnd()*.14})`;g.fillRect(0,y,S,w);}
  for(let i=0;i<8;i++){g.fillStyle='rgba(30,16,8,.7)';g.fillRect(0,i*S/8,S,3);hg.fillStyle='#202020';hg.fillRect(0,i*S/8,S,4);}
  blotches(g,S,rnd,40,S*.05,S*.2,[[140,98,60],[40,26,16]],.18);
  return [c,h];
}
function doorTex(){
  const W=512,Hh=1024,c=cv(W,Hh),g=c.getContext('2d'),h=cv(W,Hh),hg=h.getContext('2d'),rnd=random(8);
  g.fillStyle='rgb(92,60,40)';g.fillRect(0,0,W,Hh);hg.fillStyle='#707070';hg.fillRect(0,0,W,Hh);
  for(let i=0;i<300;i++){g.fillStyle=`rgba(${rnd()>.5?'25,14,8':'120,80,50'},${.05+rnd()*.12})`;g.fillRect(rnd()*W,0,1+rnd()*3,Hh);}
  const cols=2,rows=4,pw=W/cols,ph=Hh/rows;
  for(let r=0;r<rows;r++)for(let q=0;q<cols;q++){
    const x=q*pw+pw*.12,y=r*ph+ph*.08,w=pw*.76,hh=ph*.84;
    g.fillStyle='rgba(20,10,6,.55)';g.fillRect(x-4,y-4,w+8,hh+8);g.fillStyle='rgb(112,74,48)';g.fillRect(x,y,w,hh);
    g.fillStyle='rgb(128,86,56)';g.fillRect(x+w*.14,y+hh*.14,w*.72,hh*.72);g.fillStyle='rgb(94,62,40)';g.fillRect(x+w*.3,y+hh*.28,w*.4,hh*.44);
    hg.fillStyle='#303030';hg.fillRect(x-4,y-4,w+8,hh+8);hg.fillStyle='#a8a8a8';hg.fillRect(x,y,w,hh);hg.fillStyle='#d0d0d0';hg.fillRect(x+w*.14,y+hh*.14,w*.72,hh*.72);hg.fillStyle='#909090';hg.fillRect(x+w*.3,y+hh*.28,w*.4,hh*.44);
    for(const [sx,sy] of [[.06,.05],[.94,.05],[.06,.95],[.94,.95],[.5,.5]]){g.fillStyle='rgb(30,26,22)';g.beginPath();g.arc(x+w*sx,y+hh*sy,6,0,7);g.fill();g.fillStyle='rgba(255,230,190,.35)';g.beginPath();g.arc(x+w*sx-1.5,y+hh*sy-1.5,2,0,7);g.fill();hg.fillStyle='#f0f0f0';hg.beginPath();hg.arc(x+w*sx,y+hh*sy,6,0,7);hg.fill();}
  }
  g.fillStyle='rgba(20,12,8,.7)';g.fillRect(W/2-3,0,6,Hh);hg.fillStyle='#202020';hg.fillRect(W/2-3,0,6,Hh);
  return [c,h];
}

function glassTex(){
  const W=256,Hh=512,c=cv(W,Hh),g=c.getContext('2d');
  const q=g.createLinearGradient(0,0,0,Hh);q.addColorStop(0,'rgb(118,142,164)');q.addColorStop(.35,'rgb(62,80,98)');q.addColorStop(1,'rgb(22,30,38)');g.fillStyle=q;g.fillRect(0,0,W,Hh);
  g.fillStyle='rgba(255,255,255,.07)';g.beginPath();g.moveTo(0,0);g.lineTo(W*.55,0);g.lineTo(0,Hh*.45);g.closePath();g.fill();
  g.fillStyle='rgba(16,14,12,.92)';for(let i=0;i<=2;i++)g.fillRect(i*(W-8)/2,0,8,Hh);for(let j=0;j<=6;j++)g.fillRect(0,j*(Hh-8)/6,W,8);
  return c;
}
function stdMat(name,pair,tw,th,{rough=.92,bump=.05,tint=0xffffff,vc=true,metal=0,side=THREE.FrontSide}={}){
  const m=new THREE.MeshStandardMaterial({color:tint,roughness:rough,metalness:metal,vertexColors:vc,side});
  m.name=name;m.userData.scale=1;
  if(pair){const t=ctex(pair[0]);t.repeat.set(1/tw,1/th);m.map=t;if(pair[1]){const hh=ctex(pair[1],false);hh.repeat.set(1/tw,1/th);m.bumpMap=hh;m.bumpScale=bump;}}
  return m;
}
export async function materials(M){
  const rel=new Image();rel.src='textures/carlos/portal-reliefs.jpg';await rel.decode();
  const relc=cv(2048,1024);relc.getContext('2d').drawImage(rel,0,0);
  M.carPhoto=stdMat('carPhoto',[relc,relc],1,1,{bump:.10,rough:.85});
  M.carStone=stdMat('carStone',ashlarTex({seed:3,rows:4,base:[226,200,152],spread:.05,joint:[132,108,76],jw:3,lenk:[1.8,3.2],patch:.8}),2.0,2.0,{bump:.07,rough:.9});
  M.carBack=stdMat('carBack',ashlarTex({seed:9,rows:4,base:[150,112,78],spread:.1,joint:[70,52,36],jw:3,lenk:[1.8,3]}),2.2,2.2,{bump:.05,rough:.95});
  M.carAshlar=stdMat('carAshlar',ashlarTex({seed:15,rows:4,base:[216,180,122],spread:.07,joint:[112,86,58],jw:4,lenk:[1.6,3.2],patch:1.0}),2.3,2.3,{bump:.09,rough:.95});
  M.carRustic=stdMat('carRustic',rusticTex(),.9,.9,{bump:.07,rough:.96});
  M.carMarble=stdMat('carMarble',marbleTex(),3.2,3.2,{bump:.03,rough:.8});
  M.carPudding=stdMat('carPudding',puddingTex(),1.2,1.2,{bump:.08,rough:.9});
  M.carCobble=stdMat('carCobble',cobbleTex(),.9,.9,{bump:.06,rough:.95,vc:false});
  M.carSlab=stdMat('carSlab',slabTex({seed:5,base:[212,198,170],jc:[116,104,88]}),2.4,2.4,{bump:.04,rough:.9,vc:false});M.carSlab.polygonOffset=true;M.carSlab.polygonOffsetFactor=-2;M.carSlab.polygonOffsetUnits=-2;
  M.carFloor=stdMat('carFloor',slabTex({seed:7,base:[172,166,156],rows:4,wide:2.2,jc:[92,88,84]}),1.8,1.8,{bump:.04,rough:.55,vc:false});
  M.carRoof=stdMat('carRoof',roofTex(),1.0,.84,{bump:.09,rough:.92,vc:false});
  M.carWood=stdMat('carWood',woodTex(),1.2,1.2,{bump:.03,rough:.8,vc:false});
  M.carDoor=stdMat('carDoor',doorTex(),1,1,{bump:.05,rough:.7,vc:false});
  M.carVault=stdMat('carVault',ashlarTex({seed:21,rows:6,base:[104,92,80],spread:.12,joint:[60,52,44],jw:2,lenk:[2,3.5]}),2.4,2.4,{bump:.03,rough:.97,vc:false});
  M.carRidge=new THREE.MeshStandardMaterial({color:0xc4724e,roughness:.85});M.carRidge.name='carRidge';M.carRidge.userData.scale=1;
  M.carBronze=new THREE.MeshStandardMaterial({color:0x44695a,roughness:.5,metalness:.45});M.carBronze.name='carBronze';M.carBronze.userData.scale=1;
  M.carGlass=stdMat('carGlass',[glassTex()],1,1,{rough:.14,vc:false});
  M.carSlate=new THREE.MeshStandardMaterial({color:0x5d666f,roughness:.8,metalness:.1});M.carSlate.name='carSlate';M.carSlate.userData.scale=1;
  M.carDark=new THREE.MeshStandardMaterial({color:0x1a1612,roughness:1});M.carDark.name='carDark';M.carDark.userData.scale=1;
}

// ================================================================= build
let ZONE='carS';const soups=new Map();
const SO=mat=>{const k=ZONE+'|'+mat;let s=soups.get(k);if(!s){const tn=FACE_TINT[ZONE]||[1,1,1];s=new Soup(STONE.has(mat)?(x,y,z)=>weather(x,y,z,tn):NOWF);soups.set(k,s);}return s;};
const STONE=new Set(['carPhoto','carStone','carBack','carAshlar','carRustic','carMarble','carPudding','carVault']);
const rnd0=random(2027);
const NROW=12,CH=(Y.rusticTop-Y.plinth)/NROW;           // rustication course height
const EXT=s=>(s==='S'||s==='N')?.27:0;

// bay layout of each front: boundary lines (pilaster axes), bay centres, and what sits in the middle
function layout(side){
  if(side==='S'||side==='W'){
    const pw=side==='S'?7.0:9.0,n=side==='S'?7:6,p=(H-pw)/n,bd=[],bays=[];
    for(let i=0;i<=n;i++){bd.push(-H+p*i);bd.push(H-p*i);}
    for(let i=0;i<n;i++){bays.push(-H+p*(i+.5));bays.push(H-p*(i+.5));}
    return {pw,p,bd:bd.sort((a,b)=>a-b),bays:bays.sort((a,b)=>a-b),door:null};
  }
  const n=17,p=2*H/n,bd=[],bays=[];
  for(let i=0;i<=n;i++)bd.push(-H+p*i);
  for(let i=0;i<n;i++)bays.push(-H+p*(i+.5));
  return {pw:0,p,bd,bays,door:bays[8]};
}
const WIN={w:1.16,y0:Y.plinth+2*CH,y1:Y.plinth+5*CH};
const OCU={y0:Y.plinth+6*CH,y1:Y.plinth+9*CH,yc:Y.plinth+7.5*CH,r:.6};
const UWIN={w:1.36,y0:Y.floor+.15,y1:Y.floor+2.9};
const UOC={yc:14.05,r:.58};

function rusticLayer(F,lay,side){
  const S=SO('carRustic'),ext=EXT(side),y0=Y.plinth;
  const strips=lay.bd.filter(t=>Math.abs(t)<=H+1e-6);
  for(let k=0;k<NROW;k++){
    const ya=y0+k*CH,yb=ya+CH,wS=k%2?1.7:1.1,edges=[];
    for(const t of strips){
      let a=t-wS/2,b=t+wS/2;
      const cw=k%2?.78:.56;
      if(t<=-H+1e-6){a=-H-ext;b=-H+cw;}
      if(t>=H-1e-6){a=H-cw;b=H+ext;}
      S.tone=.9+rnd0()*.16;S.hue=[1,.98+rnd0()*.06,.95+rnd0()*.12];
      cblock(S,F,a,b,ya,yb,.32,.07,a,b,{jit:(rnd0()-.5)*.02,cl:t<=-H+1e-6&&ext===0,cr:t>=H-1e-6&&ext===0});
      edges.push([a,b]);
    }
    edges.sort((p,q)=>p[0]-q[0]);
    for(let i=0;i<edges.length-1;i++){
      const a=edges[i][1],b=edges[i+1][0];if(b-a<.1)continue;
      if(lay.pw>0&&a>=-lay.pw&&b<=lay.pw)continue;                 // the portal wall is dressed stone, not rustication
      const cuts=[];
      for(const tc of lay.bays){if(tc<a||tc>b)continue;
        if(k>=2&&k<=4&&tc!==lay.door)cuts.push({a:tc-WIN.w/2,b:tc+WIN.w/2});
        if(k>=6&&k<=8)cuts.push({a:tc-1.03,b:tc+1.03});
        if(k===5&&tc!==lay.door)cuts.push({a:tc-.3,b:tc+.3,key:true});
      }
      if(lay.door!==null&&lay.door>=a&&lay.door<=b&&k<=5)cuts.push({a:lay.door-1.3,b:lay.door+1.3});
      cuts.sort((p,q)=>p.a-q.a);let cur=a;
      for(const c of cuts){fillRange(S,F,cur,c.a,ya,yb);if(c.key){S.tone=.95+rnd0()*.08;cblock(S,F,c.a,c.b,ya,yb,.25,.06,c.a-.18,c.b+.18);}cur=c.b;}
      fillRange(S,F,cur,b,ya,yb);
    }
  }
  S.tone=1;S.hue=[1,1,1];
}
function fillRange(S,F,a,b,ya,yb){
  const len=b-a;if(len<.12)return;
  const n=Math.max(1,Math.round(len/(1.0+rnd0()*.4)));let w=[],sum=0;for(let i=0;i<n;i++){const v=.7+rnd0()*.7;w.push(v);sum+=v;}
  let t=a;
  for(let i=0;i<n;i++){const l=len*w[i]/sum;S.tone=.88+rnd0()*.2;S.hue=[1,.97+rnd0()*.07,.93+rnd0()*.14];
    cblock(S,F,t,t+l,ya,yb,.2+(rnd0()-.5)*.03,.085,undefined,undefined,{jit:(rnd0()-.5)*.03});t+=l;}
}

// ---- bronze tie rings held by eagle / lion heads
function tieRing(F,t,y,d,kind){
  const S=SO('carBronze'),R=.14,r=.026,seg=18,sg=6,cy=y-R+.02;
  for(let i=0;i<seg;i++)for(let j=0;j<sg;j++){
    const a0=i/seg*Math.PI*2,a1=(i+1)/seg*Math.PI*2,b0=j/sg*Math.PI*2,b1=(j+1)/sg*Math.PI*2;
    const pt=(a,b)=>{const cr=R+r*Math.cos(b);return [F.pt(t+cr*Math.cos(a),cy+cr*Math.sin(a),d+r*Math.sin(b)),comb(F,Math.cos(b)*Math.cos(a),Math.cos(b)*Math.sin(a),Math.sin(b))];};
    const A=pt(a0,b0),B=pt(a1,b0),C=pt(a1,b1),D=pt(a0,b1);S.quad(A[0],B[0],C[0],D[0],[0,0],[1,0],[1,1],[0,1],ad(A[1],C[1]),A[1],B[1],C[1],D[1]);
  }
  if(kind===0){ellipsoid(S,F,t,y,d+.0,.065,.065,.06,5,8);ellipsoid(S,F,t,y-.02,d+.1,.03,.04,.09,4,6);}
  else{ellipsoid(S,F,t,y,d+.0,.09,.09,.055,5,8);ellipsoid(S,F,t,y-.03,d+.05,.045,.04,.045,4,6);}
}

// ---- windows, oculi
function oculusRing(F,tc,yc,r,d0,mat,rings){
  const S=SO(mat);
  frev(S,F,tc,yc,[[r,d0],[r,d0+.1],[r+.08,d0+.15],[r+.2,d0+.1],[r+.26,d0+.2],[r+.36,d0+.2],[r+.4,d0+.12],[r+.4,d0]],28);
  frev(S,F,tc,yc,[[r+.4,d0+.12],[r+.5,d0+.12],[r+.5,d0]],28,{closed:false});
}
function glassQuad(F,t0,t1,y0,y1,d){SO('carGlass').quad(F.pt(t0,y0,d),F.pt(t1,y0,d),F.pt(t1,y1,d),F.pt(t0,y1,d),[0,0],[1,0],[1,1],[0,1],F.dd);}
function glassDisc(F,tc,yc,r,d){disc(SO('carGlass'),F,tc,yc,r,d,20);}

function upperBay(F,tc,p,d0,odd){
  const S=SO('carStone'),w=UWIN.w,y0=UWIN.y0,y1=UWIN.y1;
  // jambs and lintel (architrave), sill
  fbox(S,F,tc-w/2-.18,tc-w/2,y0-.07,y1+.17,d0,d0+.12,{nb:true});fbox(S,F,tc+w/2,tc+w/2+.18,y0-.07,y1+.17,d0,d0+.12,{nb:true});
  fbox(S,F,tc-w/2-.18,tc+w/2+.18,y1,y1+.17,d0,d0+.12);
  fbox(S,F,tc-w/2-.3,tc+w/2+.3,Y.floor,y0-.07,d0,d0+.3);                        // sill / threshold block
  // frieze and cornice shelf with side consoles
  fbox(S,F,tc-w/2-.3,tc+w/2+.3,y1+.17,y1+.5,d0,d0+.2,{uo:rnd0()*3});
  fbox(S,F,tc-w/2-.42,tc+w/2+.42,y1+.5,y1+.65,d0,d0+.42);
  for(const s of [-1,1]){fbox(S,F,tc+s*(w/2+.2)-.07,tc+s*(w/2+.2)+.07,y1-.5,y1+.5,d0,d0+.26);}
  const pw=w/2+.5,yb=y1+.65;
  if(!odd){
    // triangular pediment: raking frame + recessed tympanum, acroterion and two balls
    const ph=.88;
    plate(S,F,[[tc-pw,yb],[tc+pw,yb],[tc,yb+ph]],[[[tc-pw+.2,yb+.06],[tc+pw-.2,yb+.06],[tc,yb+ph-.22]]],d0,d0+.3,{});
    plate(S,F,[[tc-pw+.2,yb+.06],[tc+pw-.2,yb+.06],[tc,yb+ph-.22]],[],d0,d0+.14);
    fbox(S,F,tc-.09,tc+.09,yb+ph-.02,yb+ph+.3,d0+.04,d0+.2);ellipsoid(S,F,tc-pw+.05,yb+.1,d0+.2,.1,.1,.1,4,6);ellipsoid(S,F,tc+pw-.05,yb+.1,d0+.2,.1,.1,.1,4,6);
  }else{
    // segmental pediment with a carved scroll in the tympanum
    segGable(S,F,tc,yb,pw-.02,.62,d0,d0+.3);
    ellipsoid(S,F,tc,yb+.2,d0+.18,.26,.12,.05,4,8);
    ellipsoid(S,F,tc-pw+.05,yb+.05,d0+.2,.09,.09,.09,3,6);ellipsoid(S,F,tc+pw-.05,yb+.05,d0+.2,.09,.09,.09,3,6);
  }
  // oculus in a circular recess above
  oculusRing(F,tc,UOC.yc,UOC.r,d0,'carStone');
}

function pilaster(F,tb,d0){
  const S=SO('carStone'),pw=.34;
  // pedestal with moulded base and cap, carved panel
  fbox(S,F,tb-.58,tb+.58,Y.floor,Y.floor+.2,d0,d0+.44);
  fbox(S,F,tb-.5,tb+.5,Y.floor+.2,Y.floor+1.3,d0,d0+.36);
  fbox(S,F,tb-.56,tb+.56,Y.floor+1.3,Y.floor+1.5,d0,d0+.43);
  fbox(S,F,tb-.3,tb+.3,Y.floor+.45,Y.floor+1.1,d0+.36,d0+.4,{nb:true,nt:true,nl:true,nr:true});
  // shaft with a long recessed panel
  const yb=Y.floor+1.5,yt=Y.pilTop-.4,hw=pw,pn=.17;
  vprism(S,F,[[tb-hw,d0],[tb+hw,d0],[tb+hw,d0+.26],[tb+pn,d0+.26],[tb+pn,d0+.23],[tb-pn,d0+.23],[tb-pn,d0+.26],[tb-hw,d0+.26]],yb+.18,yt-.0,{notop:true});
  fbox(S,F,tb-hw-.05,tb+hw+.05,yb,yb+.18,d0,d0+.3);
  // Ionic capital: echinus, volutes, abacus
  fbox(S,F,tb-.34,tb+.34,yt,yt+.14,d0,d0+.32);
  fbox(S,F,tb-.42,tb+.42,yt+.14,yt+.3,d0,d0+.34);
  for(const s of [-1,1]){frev(S,F,tb+s*.34,yt+.2,[[.0,d0+.34],[.0,d0+.4],[.12,d0+.4],[.14,d0+.34]],14);frev(S,F,tb+s*.34,yt+.2,[[.14,d0+.34],[.14,d0+.42],[.08,d0+.44],[.0,d0+.44]],14,{closed:false});}
  fbox(S,F,tb-.5,tb+.5,yt+.3,yt+.4,d0,d0+.36);
}

function crownDetails(F,ext){
  const S=SO('carStone'),a=-H-ext,b=H+ext;
  let i=0;
  for(let t=a+.3;t<b-.2;t+=.56,i++){
    fbox(S,F,t-.085,t+.085,16.56,16.78,.42,1.12,{nt:true});
    fbox(S,F,t-.1,t+.1,16.52,16.58,.9,1.12,{nt:true});
    if(i%2===0&&!LOW){const m=SO('carStone');ellipsoid(m,F,t+.28,16.9,1.2,.1,.12,.1,4,8);ellipsoid(m,F,t+.28,16.84,1.28,.045,.05,.06,3,6);}
  }
}
function facade(side){
  ZONE='car'+side;
  const F=sideFrame(side),lay=layout(side),ext=EXT(side),x0=-H-ext,x1=H+ext;
  const lowHoles=[],upHoles=[];
  for(const tc of lay.bays){
    if(tc!==lay.door)lowHoles.push(rectp(tc-WIN.w/2,tc+WIN.w/2,WIN.y0,WIN.y1));lowHoles.push(circ(tc,OCU.yc,OCU.r,20));
    upHoles.push(rectp(tc-UWIN.w/2,tc+UWIN.w/2,UWIN.y0,UWIN.y1));upHoles.push(circ(tc,UOC.yc,UOC.r,18));
  }
  const portal=PORTALS[side]?PORTALS[side](F,lay,lowHoles,upHoles):null;
  plate(SO('carBack'),F,rectp(x0,x1,-.3,Y.rusticTop),lowHoles,-.35,0);
  plate(SO('carStone'),F,rectp(x0,x1,Y.floor,Y.pilTop),upHoles,-.35,.10);
  for(const tc of lay.bays){
    if(tc!==lay.door)glassQuad(F,tc-WIN.w/2,tc+WIN.w/2,WIN.y0,WIN.y1,-.33);glassDisc(F,tc,OCU.yc,OCU.r,-.33);
    glassQuad(F,tc-UWIN.w/2,tc+UWIN.w/2,UWIN.y0,UWIN.y1,-.33);glassDisc(F,tc,UOC.yc,UOC.r,-.33);
  }
  rusticLayer(F,lay,side);
  const R=SO('carRustic');
  for(const tc of lay.bays){
    // lower window sill and the smooth panel with the oculus
    if(tc!==lay.door){const w=WIN.w/2;fbox(R,F,tc-w-.04,tc+w+.04,WIN.y0-.04,WIN.y0,-.02,.17);}   // plain stone sill
    R.tone=.95+rnd0()*.08;cblock(R,F,tc-1.03,tc+1.03,OCU.y0,OCU.y1,.2,.07,undefined,undefined,{nofront:true});
    plate(R,F,rectp(tc-1.03+.07,tc+1.03-.07,OCU.y0+.07,OCU.y1-.07),[circ(tc,OCU.yc,OCU.r,20)],0,.2,{vo:rnd0()*3});R.tone=1;
    frev(R,F,tc,OCU.yc,[[OCU.r,.2],[OCU.r,.28],[OCU.r+.1,.31],[OCU.r+.2,.28],[OCU.r+.2,.2]],24);
  }
  // upper order
  const SS=SO('carStone');
  for(const tb of lay.bd){
    if(lay.pw>0&&Math.abs(tb)<lay.pw-1e-6)continue;
    if(Math.abs(tb)>=H-1e-6){
      const sg=Math.sign(tb);pilaster(F,sg*(H-.5),.10);
      fbox(SS,F,sg===1?H-.15:-H-ext,sg===1?H+ext:-H+.15,Y.floor,Y.pilTop,.10,.34,{nl:sg===1,nr:sg===-1});
      continue;
    }
    pilaster(F,tb,.10);
    // ring at the foot of every rusticated pilaster
    if(!(lay.pw>0&&Math.abs(tb)<=lay.pw+.01))tieRing(F,tb,1.5,.27+.01,Math.abs(Math.round(tb*7))%2);
  }
  lay.bays.forEach((tc,i)=>upperBay(F,tc,lay.p,.10,i%2===1));
  // base, string course, crown cornice are rings (below); modillions here
  crownDetails(F,ext);
}
const PORTALS={};

function plinth(){
  const R=SO('carRustic');
  for(const sd of ['S','E','N','W']){
    ZONE='car'+sd;const F=sideFrame(sd),e=sd==='S'||sd==='N'?H+.58:H,gap=sd==='W'?1.7:sd==='S'?1.7:0;
    const rs=gap?[[-e,-gap],[gap,e]]:[[-e,e]];
    for(const [a,b] of rs){fbox(R,F,a,b,-.3,.32,0,.58,{uo:rnd0()*4});fbox(R,F,a,b,.32,Y.plinth,0,.34,{uo:rnd0()*4,nl:a<-gap+.01&&!!gap?false:false});}
  }
  ZONE='carS';
}
function rings(){
  ZONE='carS';
  const S=SO('carStone'),R=SO('carRustic');
  ringLoop(S,[[0,8.0],[.62,8.0],[.62,8.12],[.66,8.12],[.66,8.3],[.52,8.38],[.34,8.46],[.12,Y.floor],[0,Y.floor]]);
  ringLoop(S,[[0,Y.pilTop],[.30,Y.pilTop],[.30,15.78],[.36,15.78],[.36,15.98],[.43,15.98],[.43,16.04],[.34,16.04],[.34,16.55],[.42,16.55],[.42,16.62],[.60,16.62],[.60,16.78],[1.17,16.78],[1.17,17.04],[1.10,17.08],[1.02,17.14],[.9,17.22],[.82,Y.top],[0,Y.top]]);
}

function flush(b){
  for(const [k,s] of soups){
    if(!s.count)continue;const [zone,mat]=k.split('|');
    if(s.p.some(Number.isNaN))console.warn('NaN in',k,s.p.findIndex(Number.isNaN)/9|0);
    if(!b.m[mat]){console.warn('missing material',mat);continue;}
    const g=s.geometry();b.zone=zone;b.unique(g,mat,[0,0,0],0);
  }
  let t=0;for(const s of soups.values())t+=s.count;soups.clear();return t;
}

// ================================================================= frontispieces (portals)
const W2L=(x,z)=>[(x-CX)*cT+(z-CZ)*sT,-(x-CX)*sT+(z-CZ)*cT];
// revolve a (r,y) profile about a vertical axis at frame point (tc,dc)
function revF(S,F,tc,dc,prof,seg=20,o={}){
  if(LOW)seg=Math.max(8,seg*.6|0);
  const n=prof.length,m=o.closed===false?n-1:n;
  for(let i=0;i<m;i++){
    const p=prof[i],q=prof[(i+1)%n],ex=q[0]-p[0],ey=q[1]-p[1],l=Math.hypot(ex,ey);if(l<1e-6)continue;
    const nr=ey/l,ny=-ex/l,k=o.uvr||p[0]||1;
    for(let j=0;j<seg;j++){
      const a0=j/seg*Math.PI*2,a1=(j+1)/seg*Math.PI*2,c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1);
      const A=F.pt(tc+p[0]*c0,p[1],dc+p[0]*s0),B=F.pt(tc+q[0]*c0,q[1],dc+q[0]*s0),C=F.pt(tc+q[0]*c1,q[1],dc+q[0]*s1),D=F.pt(tc+p[0]*c1,p[1],dc+p[0]*s1);
      const n0=comb(F,nr*c0,ny,nr*s0),n1=comb(F,nr*c1,ny,nr*s1);
      S.quad(A,B,C,D,[a0*k,p[1]],[a0*k,q[1]],[a1*k,q[1]],[a1*k,p[1]],ad(n0,n1),n0,n0,n1,n1);
    }
  }
}
// fluted shaft with entasis: 'flutes' hollows round the circumference
function flutedCol(S,F,tc,dc,y0,y1,r0,r1,flutes=20,depth=.035){
  if(LOW)flutes=Math.max(8,flutes*.6|0);
  const levels=LOW?3:5,per=3,N=flutes*per;
  const rad=(i,lv)=>{const t=lv/(levels-1),r=r0+(r1-r0)*t+Math.sin(t*Math.PI)*r0*.02,f=(i%per)/per;
    const hollow=Math.sin(Math.PI*f)>.0?Math.sin(Math.PI*f)**1.2:0;return r-depth*(hollow>.4?hollow:0)*(r/r0);};
  for(let lv=0;lv<levels-1;lv++){
    const ya=y0+(y1-y0)*lv/(levels-1),yb=y0+(y1-y0)*(lv+1)/(levels-1);
    for(let i=0;i<N;i++){
      const a0=i/N*Math.PI*2,a1=(i+1)/N*Math.PI*2,pt=(a,y,r)=>F.pt(tc+r*Math.cos(a),y,dc+r*Math.sin(a)),
        nrm=(a)=>comb(F,Math.cos(a),0,Math.sin(a));
      S.quad(pt(a0,ya,rad(i,lv)),pt(a0,yb,rad(i,lv+1)),pt(a1,yb,rad(i+1,lv+1)),pt(a1,ya,rad(i+1,lv)),[a0*r0,ya],[a0*r0,yb],[a1*r0,yb],[a1*r0,ya],ad(nrm(a0),nrm(a1)));
    }
  }
}
function doricCapF(S,F,tc,dc,y,r){
  revF(S,F,tc,dc,[[0,y],[r*1.0,y],[r*1.04,y+.03],[r*1.0,y+.05],[r*1.04,y+.09],[r*1.0,y+.12],[r*1.12,y+.18],[r*1.25,y+.27],[r*1.3,y+.32],[0,y+.32]],24);
  fbox(S,F,tc-r*1.42,tc+r*1.42,y+.32,y+.45,dc-r*1.42,dc+r*1.42);
}
function baseF(S,F,tc,dc,y,r,attic=true){
  revF(S,F,tc,dc,[[0,y],[r*1.5,y],[r*1.5,y+.07],[r*1.35,y+.12],[r*1.3,y+.2],[r*1.15,y+.27],[r*1.0,y+.29],[0,y+.29]],24);
  fbox(S,F,tc-r*1.62,tc+r*1.62,y-.07,y+.0,dc-r*1.62,dc+r*1.62);
}
function ionicCapF(S,F,tc,dc,y,r){
  revF(S,F,tc,dc,[[0,y],[r*1.0,y],[r*1.08,y+.05],[r*1.18,y+.11],[r*1.2,y+.16],[0,y+.16]],20);
  fbox(S,F,tc-r*1.5,tc+r*1.5,y+.16,y+.3,dc-r*.85,dc+r*.85);                    // cushion
  for(const sg of [-1,1]){for(const dd of [-1,1]){const d0=dc+dd*r*.85;frev(S,F,tc+sg*r*1.5,y+.2,dd>0?[[0,d0],[r*.5,d0],[r*.55,d0+.04],[r*.42,d0+.07],[r*.22,d0+.07],[0,d0+.04]]:[[0,d0],[r*.5,d0],[r*.55,d0-.04],[r*.42,d0-.07],[r*.22,d0-.07],[0,d0-.04]],14);}}
  fbox(S,F,tc-r*1.7,tc+r*1.7,y+.3,y+.4,dc-r*1.05,dc+r*1.05);
}
// couple of reclining figures (river gods, Victories) lying on a raking cornice
function reclining(S,F,t,y,d,dir,sz=1,wing=false){
  ellipsoid(S,F,t,y+.18*sz,d,.36*sz,.12*sz,.1*sz,4,8);                         // torso
  ellipsoid(S,F,t+dir*.34*sz,y+.3*sz,d,.1*sz,.1*sz,.09*sz,4,6);                // head
  ellipsoid(S,F,t-dir*.35*sz,y+.1*sz,d,.28*sz,.07*sz,.08*sz,4,6);              // legs
  ellipsoid(S,F,t+dir*.12*sz,y+.34*sz,d,.14*sz,.07*sz,.07*sz,3,6);             // raised arm
  if(wing)ellipsoid(S,F,t-dir*.05*sz,y+.42*sz,d-.06*sz,.3*sz,.2*sz,.03*sz,4,8);
}
function gable(S,F,tc,yb,hw,h,d0,d1,figs){
  // raking cornice frame + recessed tympanum
  const b=.2;
  plate(S,F,[[tc-hw,yb],[tc+hw,yb],[tc,yb+h]],[[[tc-hw+b*1.9,yb+b*.85],[tc+hw-b*1.9,yb+b*.85],[tc,yb+h-b*1.55]]],d0,d1);
  plate(S,F,[[tc-hw+b*1.9,yb+b*.85],[tc+hw-b*1.9,yb+b*.85],[tc,yb+h-b*1.55]],[],d0,d0+(d1-d0)*.45);
  fbox(S,F,tc-hw-.12,tc+hw+.12,yb-.1,yb,d0,d1+.08);
  if(figs){const sl=h/hw;reclining(S,F,tc-hw*.5,yb+h*.5-.02,d1+.1,-1,figs,figs>.8);reclining(S,F,tc+hw*.5,yb+h*.5-.02,d1+.1,1,figs,figs>.8);}
}
// ---- relief sculpture from the photograph atlas (5 roundels in the top row, 4 pedestal frieze strips below)
function photoDisc(F,tc,yc,R,d,idx,seg=28){
  const S=SO('carPhoto'),u0=idx*.1875+.09375,v0=.8125,ru=.87*.09375,rv=.87*.1875;
  for(let j=0;j<seg;j++){const a0=j/seg*Math.PI*2,a1=(j+1)/seg*Math.PI*2;
    S.tri(F.pt(tc,yc,d),F.pt(tc+R*Math.cos(a0),yc+R*Math.sin(a0),d),F.pt(tc+R*Math.cos(a1),yc+R*Math.sin(a1),d),[u0,v0],[u0+ru*Math.cos(a0),v0+rv*Math.sin(a0)],[u0+ru*Math.cos(a1),v0+rv*Math.sin(a1)],F.dd);}
}
function photoPanel(F,t0,t1,y0,y1,d,idx,flip=false){
  const S=SO('carPhoto'),ua=idx*.25+.003,ub=(idx+1)*.25-.003,va=.4375+.003,vb=.625-.003,[l,r]=flip?[ub,ua]:[ua,ub];
  S.quad(F.pt(t0,y0,d),F.pt(t1,y0,d),F.pt(t1,y1,d),F.pt(t0,y1,d),[l,va],[r,va],[r,vb],[l,vb],F.dd);
}
function segGable(S,F,tc,yb,hw,h,d0,d1){
  const arc=(w,hh,y)=>Array.from({length:13},(_,i)=>{const a=Math.PI*i/12;return [tc-w*Math.cos(a),y+hh*Math.sin(a)];});
  plate(S,F,arc(hw,h,yb),[arc(hw-.22,h-.2,yb+.06)],d0,d1);
  plate(S,F,arc(hw-.22,h-.2,yb+.06),[],d0,d0+(d1-d0)*.45);
  fbox(S,F,tc-hw-.1,tc+hw+.1,yb-.1,yb,d0,d1+.06);
}
function tondoRelief(S,F,tc,yc,r,d,idx){
  frev(S,F,tc,yc,[[r*1.1,d],[r*1.1,d+.06],[r*1.05,d+.1],[r*.98,d+.06],[r*.98,d]],28);
  photoDisc(F,tc,yc,r*1.08,d+.03,idx);
}
function balcony(S,F,tc,w,yb,d1){
  fbox(S,F,tc-w/2-.2,tc+w/2+.2,yb,yb+.2,.1,d1);
  fbox(S,F,tc-w/2-.2,tc+w/2+.2,yb+.2,yb+.28,.1,d1+.05);
  const B=SO('carDark');
  for(let t=tc-w/2-.1;t<=tc+w/2+.1;t+=.14)fbox(B,F,t-.012,t+.012,yb+.28,yb+1.05,d1-.08,d1-.056,{nb:true});
  fbox(B,F,tc-w/2-.15,tc+w/2+.15,yb+1.05,yb+1.09,d1-.1,d1-.04);
  for(const sg of [-1,1]){fbox(S,F,tc+sg*(w/2+.1)-.07,tc+sg*(w/2+.1)+.07,yb+.28,yb+1.2,d1-.14,d1-.0);ellipsoid(S,F,tc+sg*(w/2+.1),yb+1.27,d1-.07,.08,.08,.08,3,6);}
}
// Doric frieze: triglyph (three bars) and metope (rosette / bucranium) every 'step'
function doricFrieze(S,F,t0,t1,y0,y1,d,step=.62){
  let i=0;
  for(let t=t0+step*.35;t<t1-step*.2;t+=step,i++){
    for(const k of [-.07,0,.07])fbox(S,F,t+k-.025,t+k+.025,y0+.03,y1-.05,d,d+.055,{nb:true});
    fbox(S,F,t-.12,t+.12,y1-.05,y1,d,d+.06);
    const tm=t+step*.5,yc=(y0+y1)/2-.015;
    if(tm+.16>t1)break;
    if(i%2===0)frev(S,F,tm,yc,[[0,d+.025],[.05,d+.07],[.1,d+.045],[.16,d+.025],[.17,d]],10);
    else{ellipsoid(S,F,tm,yc-.03,d+.05,.07,.13,.05,3,6);for(const sg of [-1,1])ellipsoid(S,F,tm+sg*.12,yc+.09,d+.04,.06,.03,.03,3,5);}
  }
}
function threshold(F,t0,t1){SO('carMarble').tone=1;const S=SO('carMarble');fbox(S,F,t0,t1,0,.12,0,1.0,{nb:true});fbox(S,F,t0+.3,t1-.3,.0,.24,.0,.55,{nb:true});}
function portalW(F,lay,lowHoles,upHoles){
  const S=SO('carMarble');
  const dW=.16;                                              // wall plane of the dressed stone
  S.tone=1;
  // wall: openings
  lowHoles.push(rectp(-1.5,1.5,-.3,4.9));
  for(const sg of [-1,1])lowHoles.push(rectp(sg*5.35-.6,sg*5.35+.6,Y.plinth,Y.plinth+2.85));
  upHoles.push(rectp(-.7,.7,UWIN.y0,11.6));for(const sg of [-1,1])upHoles.push(rectp(sg*5.35-.7,sg*5.35+.7,UWIN.y0,11.6));
  // marble facing of the lower and upper storeys over the portal width
  plate(S,F,rectp(-9,9,Y.plinth-.8,Y.rusticTop+.1),[rectp(-1.5,1.5,Y.plinth-.8,4.9),...[-1,1].map(sg=>rectp(sg*5.35-.6,sg*5.35+.6,Y.plinth,Y.plinth+2.85))],0,dW,{});
  for(const sg of [-1,1]){darkQuad(F,sg*5.35-.6,sg*5.35+.6,Y.plinth,Y.plinth+2.85,-.33);doorLeaf(F,sg*5.35-.6,sg*5.35+.6,Y.plinth,Y.plinth+2.85,-.12);}
  // pedestals with relief panels, bases, fluted Doric columns (4 pairs)
  for(const sg of [-1,1])for(const pc of [3.2,7.5]){
    const tc=sg*pc,t0=tc-1.35,t1=tc+1.35;
    fbox(S,F,t0-.12,t1+.12,-.1,.28,dW,1.5+.12);fbox(S,F,t0,t1,.28,1.62,dW,1.5);fbox(S,F,t0-.1,t1+.1,1.62,1.9,dW,1.5+.1);fbox(S,F,t0+.1,t1-.1,1.9,1.98,dW,1.62);
    photoPanel(F,t0+.2,t1-.2,.45,1.45,1.512,sg<0?(pc>5?0:1):(pc<5?2:3));
    for(const k of [-.5,.5]){const cx=tc+k;baseF(S,F,cx,.85,1.98,.4);flutedCol(S,F,cx,.85,2.27,6.55,.4,.345,20,.03);doricCapF(S,F,cx,.85,6.55,.345);}
  }
  // entablature: architrave, frieze, cornice (continuous, projecting)
  fbox(S,F,-9.15,9.15,7.0,7.5,dW,1.4);fbox(S,F,-9.2,9.2,7.5,7.58,dW,1.46);
  fbox(S,F,-9.15,9.15,7.58,8.12,dW,1.36);doricFrieze(S,F,-9.0,9.0,7.58,8.12,1.36,.6);
  fbox(S,F,-9.25,9.25,8.12,8.32,dW,1.55);fbox(S,F,-9.3,9.3,8.32,8.55,dW,1.62);
  // central doorway: jambs with carved bands, lintel, triangular pediment crowned by two Victories
  fbox(S,F,-1.5-.42,-1.5,-.3,5.0,dW,.55);fbox(S,F,1.5,1.5+.42,-.3,5.0,dW,.55);fbox(S,F,-1.92,1.92,4.9,5.3,dW,.62);fbox(S,F,-2.1,2.1,5.3,5.5,dW,.72);
  gable(S,F,0,5.5,2.35,1.45,dW,.62,.95);
  ellipsoid(S,F,0,6.45,.62,.2,.16,.05,4,8);
  threshold(F,-1.5,1.5);
  // side doors: frame with pediments and river gods, tondi above
  for(const sg of [-1,1]){
    const tc=sg*5.35;fbox(S,F,tc-.6-.2,tc-.6,Y.plinth,Y.plinth+3.0,dW,.5);fbox(S,F,tc+.6,tc+.8,Y.plinth,Y.plinth+3.0,dW,.5);fbox(S,F,tc-.85,tc+.85,Y.plinth+2.85,Y.plinth+3.1,dW,.6);
    gable(S,F,tc,Y.plinth+3.2,1.0,.62,dW,.55,.5);
    tondoRelief(S,F,tc,5.55,.95,dW,sg<0?0:1);
  }
  // upper storey: Ionic pairs, marble panels, three balconied windows with pediments, tondi
  S.tone=1;
  for(const sg of [-1,1])for(const pc of [3.2,7.5]){
    const tc=sg*pc,t0=tc-1.35,t1=tc+1.35;
    fbox(S,F,t0-.1,t1+.1,Y.floor,Y.floor+.28,.1,1.28);fbox(S,F,t0,t1,Y.floor+.28,Y.floor+1.75,.1,1.2);fbox(S,F,t0-.08,t1+.08,Y.floor+1.75,Y.floor+1.95,.1,1.28);
    photoPanel(F,t0+.2,t1-.2,Y.floor+.5,Y.floor+1.5,1.212,sg<0?(pc>5?1:2):(pc<5?1:2),sg>0);
    for(const k of [-.5,.5]){const cx=tc+k;baseF(S,F,cx,.7,Y.floor+1.95,.36);flutedCol(S,F,cx,.7,Y.floor+2.24,15.15,.36,.31,20,.028);ionicCapF(S,F,cx,.7,15.15,.31);}
  }
  fbox(S,F,-9.2,9.2,Y.pilTop,Y.pilTop+.05,.1,.95);
  // upper wall of the frontispiece is dressed marble too
  plate(S,F,rectp(-9,9,Y.floor,Y.pilTop),[rectp(-.7,.7,UWIN.y0,11.6),rectp(5.35-.7,5.35+.7,UWIN.y0,11.6),rectp(-5.35-.7,-5.35+.7,UWIN.y0,11.6)],0,.16);
  for(const sg of [-1,1]){const tc=sg*5.35;
    balcony(S,F,tc,1.4,Y.floor+.0,.85);
    fbox(S,F,tc-.7-.18,tc-.7,Y.floor+.2,11.7,.1,.28);fbox(S,F,tc+.7,tc+.88,Y.floor+.2,11.7,.1,.28);fbox(S,F,tc-.95,tc+.95,11.6,11.85,.1,.42);
    segGable(S,F,tc,11.85,1.05,.55,.1,.34);
    tondoRelief(S,F,tc,13.75,.95,.17,sg<0?2:4);
    fbox(S,F,tc-1.25,tc+1.25,12.7,12.82,.1,.25);
  }
  balcony(S,F,0,1.4,Y.floor,.85);
  fbox(S,F,-.7-.18,-.7,Y.floor+.2,11.7,.1,.28);fbox(S,F,.7,.88,Y.floor+.2,11.7,.1,.28);fbox(S,F,-.95,.95,11.6,11.85,.1,.42);
  gable(S,F,0,11.85,1.05,.9,.1,.34,0);
  tondoRelief(S,F,0,13.75,.95,.17,3);
  for(const sg of [-1,1])for(const pc of [3.2,7.5]){const [x,,z]=F.pt(sg*pc,0,.85);NAV.box(x,z,2.8,1.4,0,9,F.rot);}
  // brackets under the cornice of the frontispiece
  glassQuad(F,-.7,.7,UWIN.y0,11.6,-.33);for(const sg of [-1,1])glassQuad(F,sg*5.35-.7,sg*5.35+.7,UWIN.y0,11.6,-.33);
  return true;
}
PORTALS.W=portalW;
function lion(S,F,t,y,d,dir){
  ellipsoid(S,F,t,y+.28,d,.5,.26,.2,4,8);ellipsoid(S,F,t+dir*.46,y+.5,d,.22,.22,.2,4,8);ellipsoid(S,F,t+dir*.68,y+.42,d,.12,.1,.1,3,6);
  ellipsoid(S,F,t+dir*.36,y+.18,d+.0,.1,.18,.28,3,6);ellipsoid(S,F,t-dir*.4,y+.12,d,.2,.14,.28,3,6);ellipsoid(S,F,t-dir*.7,y+.2,d,.22,.05,.05,3,6);
}
function portalS(F,lay,lowHoles,upHoles){
  const S=SO('carMarble'),dW=.16;S.tone=1;
  lowHoles.push(rectp(-1.5,1.5,-.3,4.6));
  upHoles.push(archContour(0,UWIN.y0,2.7,12.6,14));
  for(const sg of [-1,1])upHoles.push(rectp(sg*2.2-.5,sg*2.2+.5,UWIN.y0,12.0));
  plate(S,F,rectp(-5.4,5.4,Y.plinth-.8,Y.rusticTop+.1),[rectp(-1.5,1.5,Y.plinth-.8,4.6)],0,dW,{});
  // pedestal bases with lions and relief panels; paired Ionic columns
  for(const sg of [-1,1]){
    const t0=sg>0?2.15:-5.0,t1=sg>0?5.0:-2.15,tc=sg*3.58;
    fbox(S,F,t0-.1,t1+.1,-.1,.3,dW,1.55);fbox(S,F,t0+.05,t1-.05,.3,1.6,dW,1.45);fbox(S,F,t0,t1,1.6,1.8,dW,1.55);
    photoPanel(F,t0+.25,t1-.25,.5,1.4,1.462,sg<0?1:2,sg>0);
    lion(S,F,sg*4.5,1.8,.95,sg);
    for(const k of [-.62,.62]){const cx=tc+k;baseF(S,F,cx,.85,1.8,.37);flutedCol(S,F,cx,.85,2.09,6.7,.37,.32,20,.03);ionicCapF(S,F,cx,.85,6.7,.32);}
    NAV.box(...[F.pt((t0+t1)/2,0,.9)].map(p=>p[0]).concat([F.pt((t0+t1)/2,0,.9)[2]]),t1-t0,1.4,0,9,F.rot);
  }
  // entablature with the carved frieze and the broken cornice over the portal
  fbox(S,F,-5.3,5.3,7.1,7.5,dW,1.35);fbox(S,F,-5.3,5.3,7.5,8.05,dW,1.3);
  photoPanel(F,-4.9,-1.2,7.55,8.0,1.312,3);photoPanel(F,1.2,4.9,7.55,8.0,1.312,0,true);
  fbox(S,F,-5.4,5.4,8.05,8.3,dW,1.55);fbox(S,F,-5.45,5.45,8.3,8.55,dW,1.6);
  // doorway and its pediment with two winged figures
  fbox(S,F,-1.9,-1.5,-.3,4.7,dW,.55);fbox(S,F,1.5,1.9,-.3,4.7,dW,.55);fbox(S,F,-2.1,2.1,4.6,5.0,dW,.62);fbox(S,F,-2.3,2.3,5.0,5.2,dW,.72);
  gable(S,F,0,5.2,2.55,1.4,dW,.62,.95);
  doorLeaf(F,-1.5,1.5,0,4.6,-.12);threshold(F,-1.5,1.5);
  // upper storey: pedestals with reliefs, Ionic pairs, arched window with side lights
  for(const sg of [-1,1]){
    const tc=sg*3.58,t0=tc-1.4,t1=tc+1.4;
    fbox(S,F,t0-.1,t1+.1,Y.floor,Y.floor+.25,.1,1.3);fbox(S,F,t0,t1,Y.floor+.25,Y.floor+1.6,.1,1.2);fbox(S,F,t0-.08,t1+.08,Y.floor+1.6,Y.floor+1.8,.1,1.3);
    photoPanel(F,t0+.25,t1-.25,Y.floor+.45,Y.floor+1.4,1.212,sg<0?2:1,sg<0);
    for(const k of [-.58,.58]){const cx=tc+k;baseF(S,F,cx,.65,Y.floor+1.8,.35);flutedCol(S,F,cx,.65,Y.floor+2.1,15.1,.35,.3,20,.028);ionicCapF(S,F,cx,.65,15.1,.3);}
    fbox(S,F,sg*2.2-.62,sg*2.2+.62,Y.floor,Y.floor+.5,.1,.35);photoPanel(F,sg*2.2-.5,sg*2.2+.5,Y.floor+.08,Y.floor+.45,.352,sg<0?0:3);
    fbox(S,F,sg*2.2-.62,sg*2.2-.5,Y.floor+.5,12.1,.1,.3);fbox(S,F,sg*2.2+.5,sg*2.2+.62,Y.floor+.5,12.1,.1,.3);fbox(S,F,sg*2.2-.7,sg*2.2+.7,12.0,12.2,.1,.4);
    glassQuad(F,sg*2.2-.5,sg*2.2+.5,UWIN.y0,12.0,-.33);
    fbox(S,F,sg*1.5-.07,sg*1.5+.07,Y.floor+.6,12.0,.15,.3);ionicCapF(S,F,sg*1.5,.22,12.0,.1);
    
  }
  // large round-headed window
  const arch=[];for(let i=0;i<=24;i++){const a=Math.PI*i/24;arch.push([-1.35*Math.cos(a)*-1*0+1.35*Math.cos(Math.PI-a)*-1,12.6+1.35*Math.sin(a)]);}
  frev(S,F,0,12.6,[[1.35,.1],[1.35,.2],[1.5,.26],[1.7,.2],[1.72,.1]],28,{closed:true,flat:false});
  fbox(S,F,-1.72,-1.35,UWIN.y0,12.6,.1,.26);fbox(S,F,1.35,1.72,UWIN.y0,12.6,.1,.26);
  glassQuad(F,-1.35,1.35,UWIN.y0,12.6,-.33);glassDisc(F,0,12.6,1.35,-.33);
  reclining(S,F,-1.55,14.3,.3,-1,1.0,true);reclining(S,F,1.55,14.3,.3,1,1.0,true);
  plate(S,F,rectp(-5.4,5.4,Y.floor,Y.pilTop),[archContour(0,UWIN.y0,2.7,12.6,14),...[-1,1].map(sg=>rectp(sg*2.2-.5,sg*2.2+.5,UWIN.y0,12.0))],0,.16);
  // upper entablature and the stepped crown of the portal
  fbox(S,F,-5.3,5.3,Y.pilTop,16.0,.1,.95);fbox(S,F,-5.35,5.35,16.0,16.55,.1,.9);
  fbox(S,F,-5.5,5.5,16.55,16.8,.1,1.55);fbox(S,F,-5.6,5.6,16.8,17.05,.1,1.75);fbox(S,F,-5.7,5.7,17.05,17.3,.1,1.85);
  fbox(S,F,-5.0,5.0,17.3,17.8,.1,1.55);fbox(S,F,-5.15,5.15,17.8,17.95,.1,1.7);
  for(let t=-4.9;t<5.0;t+=.62){fbox(S,F,t-.1,t+.1,17.3,17.8,1.55,1.66,{nb:true});ellipsoid(S,F,t,17.5,1.6,.09,.11,.07,3,6);}
  return true;
}
PORTALS.S=portalS;
function sideDoor(F,lay){
  const P=SO('carPudding'),S=SO('carStone'),tc=lay.door,sill=Y.plinth;
  // door set in the rusticated wall: two pudding-stone columns carry a heavy cornice slab
  darkQuad(F,tc-.75,tc+.75,sill,sill+3.7,-.4);doorLeaf(F,tc-.75,tc+.75,sill,sill+3.3,-.15);
  fbox(S,F,tc-.75,tc+.75,sill,sill+.06,-.15,.5);
  for(const sg of [-1,1]){const cx=tc+sg*1.02;baseF(S,F,cx,.2,sill,.2);revF(P,F,cx,.2,[[0,sill+.29],[.2,sill+.29],[.185,sill+.5],[.17,sill+3.0],[.185,sill+3.15],[0,sill+3.15]],18,{uvr:.2});
    revF(S,F,cx,.2,[[0,sill+3.15],[.23,sill+3.15],[.24,sill+3.22],[.26,sill+3.3],[0,sill+3.3]],18);}
  fbox(S,F,tc-1.25,tc+1.25,sill+3.3,sill+3.65,-.05,.5);fbox(S,F,tc-1.3,tc+1.3,sill+3.65,sill+3.85,-.05,.62);fbox(S,F,tc-1.45,tc+1.45,sill+3.85,sill+4.1,-.05,.9);
  fbox(S,F,tc-1.55,tc+1.55,sill+4.1,sill+4.18,-.05,.96);
  photoPanel(F,tc-1.0,tc+1.0,sill+3.36,sill+3.6,.512,(Math.abs(Math.round(tc))%4));
  NAV.box(...F.pt(tc,0,.2).filter((_,i)=>i!==1),3.2,.9,0,5,F.rot);
}
PORTALS.N=(F,lay,lh,uh)=>{lh.push(rectp(lay.door-.75,lay.door+.75,Y.plinth,Y.plinth+3.6));sideDoor(F,lay);};
PORTALS.E=PORTALS.N;


// ================================================================= courtyard
let NAV=null;
const POL=(r,a)=>[r*Math.cos(a),r*Math.sin(a)];
const W3=(u,y,v)=>{const [x,z]=L2W(u,v);return [x,y,z];};
// flat ring of the floor / ceiling; cart UVs for cobbles, polar UVs (arcs) for slabs
function annulus(S,r0,r1,y,seg,{up=true,polar=false,tile=1.8}={}){
  const Rm=(r0+r1)/2,N=Math.max(1,Math.round(2*Math.PI*Rm/tile)),k=N*tile/(2*Math.PI);
  for(let j=0;j<seg;j++){
    const a0=j/seg*Math.PI*2,a1=(j+1)/seg*Math.PI*2;
    const q=(r,a)=>{const [u,v]=POL(r,a);return {p:W3(u,y,v),uv:polar?[a*k,r]:[u,v]};};
    const A=q(r0,a0),B=q(r1,a0),C=q(r1,a1),D=q(r0,a1);
    if(r0<1e-6)S.tri(A.p,C.p,D.p,A.uv,C.uv,D.uv,up?UP:[0,-1,0]);else S.quad(A.p,B.p,C.p,D.p,A.uv,B.uv,C.uv,D.uv,up?UP:[0,-1,0]);
    if(r0<1e-6)S.tri(A.p,B.p,C.p,A.uv,B.uv,C.uv,up?UP:[0,-1,0]);
  }
}
function slabRect(S,u0,u1,v0,v1,y){   // axis-aligned in the building frame
  const q=(u,v)=>W3(u,y,v);S.quad(q(u0,v0),q(u1,v0),q(u1,v1),q(u0,v1),[u0,v0],[u1,v0],[u1,v1],[u0,v1],UP);
}

function paving(){
  const cob=SO('carCobble'),slab=SO('carSlab');
  annulus(cob,0,RC+.25,0,72,{});
  annulus(SO('carFloor'),RC+.25,RW+.05,0,96,{polar:true,tile:1.8});
  // pale limestone bands over the cobbles: central ring, outer ring, and the cross of the axes
  const y=.012;
  annulus(SO('carFloor'),RC+.1,RC+.55,.01,96,{polar:true,tile:1.8});annulus(slab,3.3,4.6,y,64,{polar:true,tile:2.4});annulus(slab,RC-2.0,RC-.7,y,96,{polar:true,tile:2.4});
  for(const [du,dv] of [[1,0],[0,1]]){
    const w=.7,a=4.6,b=RC-2.0;
    for(const sg of [-1,1])slabRect(slab,du?sg*a:-w,du?sg*b:w,du?-w:sg*a,du?w:sg*b,y);
  }
  for(let k=0;k<4;k++){const a=Math.PI/4+k*Math.PI/2;   // diagonal bands in the gaps between the axes
    const c=Math.cos(a),s=Math.sin(a),px=-s,pz=c,w=.45,r0=4.6,r1=RC-2.0,q=(r,t)=>W3(r*c+px*t,y,r*s+pz*t);
    slab.quad(q(r0,-w),q(r1,-w),q(r1,w),q(r0,w),[0,0],[1,0],[1,1],[0,1],UP);}
}

const COLP=[[0,.16],[.40,.16],[.425,.2],[.41,.26],[.36,.32],[.33,.36],[.325,2.0],[.31,3.6],[.286,4.96],[.286,5.02],[.30,5.04],[.30,5.09],[.286,5.1],[.33,5.14],[.38,5.2],[.41,5.27],[.41,5.3],[0,5.3]];
const IONP=[[0,0],[.285,0],[.30,.04],[.28,.1],[.25,.16],[.245,.2],[.24,2.3],[.225,3.15],[.21,3.4],[.225,3.44],[.20,3.5],[0,3.5]];
function colonnade(){
  const P=SO('carPudding'),St=SO('carStone');
  for(let k=0;k<NCOL;k++){
    const a=(k+.5)*DA,[u0,v0]=POL(RC,a),[x,z]=L2W(u0,v0),[nx,nz]=LDIR(-Math.cos(a),-Math.sin(a)),F=makeFrame(x,z,nx,nz);
    // lower Tuscan/Doric column on a square plinth, square abacus
    fbox(P,F,-.46,.46,0,.16,-.46,.46);
    rev(P,u0,v0,COLP.map(q=>[q[0],q[1]]),28,{uvr:.33});
    fbox(P,F,-.43,.43,5.3,5.44,-.43,.43);
    NAV.box(x,z,.8,.8,0,6.4,F.rot);
    // pedestal, attic base, Ionic column, capital with volutes
    const yb=YG.floor;
    fbox(St,F,-.43,.43,yb,yb+.18,-.43,.43);fbox(St,F,-.36,.36,yb+.18,YG.upCol-.15,-.36,.36);fbox(St,F,-.41,.41,YG.upCol-.15,YG.upCol,-.41,.41);
    fbox(St,F,-.25,.25,yb+.4,yb+1.15,.36,.385,{nb:true,nt:true,nl:true,nr:true});fbox(St,F,-.25,.25,yb+.4,yb+1.15,-.385,-.36,{nb:true,nt:true,nl:true,nr:true});
    rev(P,u0,v0,IONP.map(q=>[q[0],q[1]+YG.upCol]),24,{uvr:.24});
    const yc=YG.upCol+3.5;
    fbox(St,F,-.46,.46,yc,yc+.12,-.2,.2);                       // cushion
    for(const sg of [-1,1]){const tt=sg*.43;frev(St,F,tt,yc+.09,[[0,.2],[.13,.2],[.15,.12],[.13,.0]],14);frev(St,F,tt,yc+.09,[[0,-.2],[.13,-.2],[.15,-.12],[.13,.0]],14);}
    fbox(St,F,-.5,.5,yc+.12,yc+.22,-.26,.26);
    NAV.box(x,z,.6,.6,YG.floor,YG.upTop,F.rot);
  }
}

function entablatures(){
  const St=SO('carStone');
  // lower Doric entablature: architrave 5.42-6.0, frieze 6.0-6.75 (triglyphs added below), cornice 6.75-7.15
  rev(St,0,0,[[RC+.5,5.42],[RC+.5,7.15],[RC-.62,7.15],[RC-.62,7.06],[RC-.52,7.03],[RC-.52,6.92],[RC-.44,6.88],[RC-.44,6.75],[RC-.40,6.75],[RC-.40,6.0],[RC-.46,5.98],[RC-.46,5.80],[RC-.42,5.78],[RC-.42,5.62],[RC-.48,5.60],[RC-.48,5.45],[RC-.40,5.45],[RC-.40,5.42]],160,{uvr:RC});
  // floor slab edge and the parapet of the upper gallery
  rev(St,0,0,[[RC+.5,7.15],[RC+.5,7.22],[RC-.66,7.22],[RC-.66,7.15]],160,{uvr:RC});
  rev(St,0,0,[[RC+.14,7.22],[RC+.14,8.35],[RC-.24,8.35],[RC-.24,8.22],[RC-.32,8.19],[RC-.32,8.05],[RC-.24,8.03],[RC-.24,7.6],[RC-.32,7.57],[RC-.32,7.22]],160,{uvr:RC});
  // upper entablature (plain architrave and frieze, small cornice)
  rev(St,0,0,[[RC+.4,12.4],[RC+.4,13.75],[RC-.66,13.75],[RC-.66,13.65],[RC-.56,13.62],[RC-.56,13.45],[RC-.46,13.42],[RC-.46,13.0],[RC-.5,12.98],[RC-.5,12.68],[RC-.44,12.66],[RC-.44,12.4]],160,{uvr:RC});
  // balustrade panels: raised tables between the pedestals
  for(let k=0;k<NCOL;k++){
    const a=(k+1)*DA,F=wallFrame(a,RC-.24);
    fbox(St,F,-.86,.86,7.73,7.93,-.04,.025,{nb:true});
    fbox(St,F,-1.0,1.0,7.93,8.03,-.04,.06,{nb:true});fbox(St,F,-1.0,1.0,7.63,7.73,-.04,.06,{nb:true});
    fbox(St,F,-1.0,-.86,7.73,7.93,-.04,.06,{nb:true});fbox(St,F,.86,1.0,7.73,7.93,-.04,.06,{nb:true});
  }
}
function triglyphs(){
  const St=SO('carStone');let n=0;
  for(let k=0;k<NCOL;k++)for(let j=0;j<5;j++){
    const a=(k+.5)*DA+j*DA/5,F=wallFrame(a,RC-.40),yf=6.0,yh=6.75;
    // triglyph: three raised bars (centre column of each bay over the column axis)
    for(const t of [-.1,0,.1])fbox(St,F,t-.034,t+.034,yf+.03,yh-.06,-.01,.065,{nb:true});
    fbox(St,F,-.15,.15,yh-.06,yh-.0,-.01,.075);
    // metope between this triglyph and the next
    const am=a+DA/10,Fm=wallFrame(am,RC-.40),yc=(yf+yh)/2-.01;
    if(j%2===0)frev(St,Fm,0,yc,[[0,.02],[.06,.08],[.11,.05],[.19,.03],[.2,.0]],10);
    else{ellipsoid(St,Fm,0,yc-.04,.04,.08,.15,.06,3,6);ellipsoid(St,Fm,-.13,yc+.1,.03,.06,.035,.035,3,5);ellipsoid(St,Fm,.13,yc+.1,.03,.06,.035,.035,3,5);
      for(const sg of [-1,1]){fbox(St,Fm,sg*.22-.014,sg*.22+.014,yc-.27,yc+.24,.0,.025);}}
    n++;
  }
}
function galleryShell(){
  const A=SO('carAshlar'),V=SO('carVault'),St=SO('carStone'),W=SO('carWood');
  // annular vault of the lower gallery: springs from the wall at 4.6 and from the architrave at 5.4
  const vp=[];for(let i=0;i<=16;i++){const t=i/16,r=RC+.5+t*(RW-RC-.5);vp.push([r,5.42*(1-t)+5.2*t+1.25*Math.sin(Math.PI*t)]);}
  rev(V,0,0,vp,160,{closed:false,uvr:RW});
  rev(SO('carFloor'),0,0,[[RW,YG.floor],[RC-.1,YG.floor]],160,{closed:false,uvr:RW});          // upper gallery floor
  // upper gallery ceiling: planked ring with radial joists
  rev(W,0,0,[[RC-.0,12.4],[RW,12.4]],160,{closed:false,uvr:RW});
  for(let i=0;i<192;i++){const a=(i+.5)/192*Math.PI*2,F=wallFrame(a,RW);
    // radial beam seen from below: a box running from the wall to the colonnade
    const [ux,uz]=L2W(Math.cos(a)*(RC+RW)/2,Math.sin(a)*(RC+RW)/2),Fr=makeFrame(ux,uz,...LDIR(Math.cos(a),Math.sin(a)));
    fbox(W,Fr,-.09,.09,12.2,12.4,-(RW-RC)/2,(RW-RC)/2,{});
  }
  rev(W,0,0,[[RC-.0,12.4],[RC-.0,12.22],[RC+.2,12.22],[RC+.2,12.4]],160,{uvr:RC});
}

// ================================================================= roof
const ROOF={eave:H+.55,yE:17.4,ko:.2,rin:RC-.55,yin:13.9,ki:.5};
function roofY(r,a){const m=Math.max(Math.abs(Math.cos(a)),Math.abs(Math.sin(a)));return Math.min(ROOF.yE+(ROOF.eave-r*m)*ROOF.ko,ROOF.yin+(r-ROOF.rin)*ROOF.ki);}
function chapel(){
  // octagonal drum with a slate pyramid and a cross, rising above the roof of the north-east wing
  ZONE='carRoof';const St=SO('carStone'),Sl=SO('carSlate'),cu=21.5,cv=-11.5,R0=3.3,N=8;
  const [wx,wz]=L2W(cu,cv),y0=roofY(Math.hypot(cu,cv),Math.atan2(cv,cu))-1.0,yD=y0+4.7;
  const P=(r,a,y)=>{const [x,z]=L2W(cu+r*Math.cos(a),cv+r*Math.sin(a));return [x,y,z];};
  for(let i=0;i<N;i++){
    const a0=(i+.5)*Math.PI*2/N,a1=(i+1.5)*Math.PI*2/N,am=(a0+a1)/2,rr=R0/Math.cos(Math.PI/N),n=LDIR(Math.cos(am),Math.sin(am));
    const hint=[n[0],0,n[1]];
    St.quad(P(rr,a0,y0),P(rr,a1,y0),P(rr,a1,yD),P(rr,a0,yD),[0,0],[1,0],[1,1],[0,1],hint);
    // arched window panel on each face
    const wxm=P(rr+.02,am,0),tx=-Math.sin(am),tz=Math.cos(am);
    const q=(t,y,d)=>{const [x,z]=L2W(cu+(rr+d)*Math.cos(am)-t*Math.sin(am),cv+(rr+d)*Math.sin(am)+t*Math.cos(am));return [x,y,z];};
    const yb=yD-2.9;
    SO('carDark').quad(q(-.4,yb,.03),q(.4,yb,.03),q(.4,yb+1.5,.03),q(-.4,yb+1.5,.03),[0,0],[1,0],[1,1],[0,1],hint);
    for(let k=0;k<8;k++){const t0=Math.PI*k/8,t1=Math.PI*(k+1)/8;SO('carDark').tri(q(0,yb+1.5,.03),q(.4*Math.cos(t0),yb+1.5+.4*Math.sin(t0),.03),q(.4*Math.cos(t1),yb+1.5+.4*Math.sin(t1),.03),[0,0],[1,0],[0,1],hint);}
    St.quad(q(-.7,yb-.1,.0),q(.7,yb-.1,.0),q(.7,yb,.14),q(-.7,yb,.14),[0,0],[1,0],[1,1],[0,1],hint);
  }
  // cornice ring and pyramid
  const ring=[[R0/Math.cos(Math.PI/N)+.0,yD],[R0/Math.cos(Math.PI/N)+.5,yD],[R0/Math.cos(Math.PI/N)+.5,yD+.35],[R0/Math.cos(Math.PI/N)+.1,yD+.45],[R0/Math.cos(Math.PI/N)+.0,yD+.45]];
  for(let i=0;i<N;i++){const a0=(i+.5)*Math.PI*2/N,a1=(i+1.5)*Math.PI*2/N;
    for(let j=0;j<ring.length-1;j++){const p=ring[j],q=ring[j+1];St.quad(P(p[0],a0,p[1]),P(p[0],a1,p[1]),P(q[0],a1,q[1]),P(q[0],a0,q[1]),[0,0],[1,0],[1,1],[0,1],[Math.cos((a0+a1)/2)*LDIR(1,0)[0],0.2,0]);}}
  const ap=P(0,0,yD+4.6);
  for(let i=0;i<N;i++){const a0=(i+.5)*Math.PI*2/N,a1=(i+1.5)*Math.PI*2/N,r0=R0/Math.cos(Math.PI/N)+.45;Sl.tri(P(r0,a0,yD+.4),P(r0,a1,yD+.4),ap,[0,0],[1,0],[.5,1],[0,1,0]);}
  const F0=makeFrame(wx,wz,0,1);fbox(SO('carBronze'),F0,-.05,.05,yD+4.5,yD+6.0,-.05,.05);fbox(SO('carBronze'),F0,-.4,.4,yD+5.3,yD+5.45,-.04,.04);
}
function roof(){
  ZONE='carRoof';const S=SO('carRoof'),N=128;
  const ridge=a=>{const m=Math.max(Math.abs(Math.cos(a)),Math.abs(Math.sin(a)));return (ROOF.yE+ROOF.eave*ROOF.ko-ROOF.yin+ROOF.rin*ROOF.ki)/(ROOF.ki+m*ROOF.ko);};
  const out=a=>ROOF.eave/Math.max(Math.abs(Math.cos(a)),Math.abs(Math.sin(a)));
  const kS=Math.hypot(1,ROOF.ko),kC=Math.hypot(1,ROOF.ki);
  for(let j=0;j<N;j++){
    const a0=j/N*Math.PI*2,a1=(j+1)/N*Math.PI*2;
    const V=(r,a)=>{const [u,v]=POL(r,a);return W3(u,roofY(r,a),v);};
    const uvC=(r,a)=>[a*ROOF.rin*1.3,(r-ROOF.rin)*kC],uvS=(r,a,al)=>{const [u,v]=POL(r,a),m=Math.max(Math.abs(Math.cos(a)),Math.abs(Math.sin(a))),sd=r*m;
      // tangential coordinate along the facing edge, slope distance from the eave
      const am=((Math.round(a/(Math.PI/2)))*Math.PI/2),t=Math.abs(Math.cos(am))>.5?v:u;return [t,(ROOF.eave-sd)*kS];};
    const am0=(a0+a1)/2,r0a=ridge(a0),r1a=ridge(a1),o0=out(a0),o1=out(a1);
    // inner slope (cone) between the courtyard eave and the ridge
    S.quad(V(ROOF.rin,a0),V(r0a,a0),V(r1a,a1),V(ROOF.rin,a1),uvC(ROOF.rin,a0),uvC(r0a,a0),uvC(r1a,a1),uvC(ROOF.rin,a1),UP);
    // outer hip planes between the ridge and the outer eave
    S.quad(V(r0a,a0),V(o0,a0),V(o1,a1),V(r1a,a1),uvS(r0a,a0),uvS(o0,a0),uvS(o1,a1),uvS(r1a,a1),UP);
  }
  // ridge tiles: the ring ridge and the four hips (rounded cap on a mortar bed)
  const RS=SO('carRidge'),rw=.26,rh=.2,NR=N;
  const cap=(A0,A1,B0,B1,d0,d1)=>{ // A*,B* = left/right base points of two successive sections, lifted ridge in the middle
    const mid=(L,R)=>[(L[0]+R[0])/2,Math.max(L[1],R[1])+rh,(L[2]+R[2])/2];
    const m0=mid(A0,A1),m1=mid(B0,B1);
    RS.quad(A0,m0,m1,B0,[0,0],[1,0],[1,1],[0,1],UP);RS.quad(m0,A1,B1,m1,[0,0],[1,0],[1,1],[0,1],UP);};
  for(let j=0;j<NR;j++){
    const a0=j/NR*Math.PI*2,a1=(j+1)/NR*Math.PI*2,r0=ridge(a0),r1=ridge(a1);
    const q=(a,r)=>{const [u,v]=POL(r,a);return W3(u,roofY(r,a)+.02,v);};
    cap(q(a0,r0-rw),q(a0,r0+rw),q(a1,r1-rw),q(a1,r1+rw));
  }
  for(let k=0;k<4;k++){const a=Math.PI/4+k*Math.PI/2,r0=ridge(a),o=out(a),n=24,px=-Math.sin(a),pz=Math.cos(a);
    const P=(r,sg)=>{const [u,v]=POL(r,a);const [x,z]=L2W(u+px*sg*rw,v+pz*sg*rw);return [x,roofY(r,a)+.02,z];};
    for(let i=0;i<n;i++){const ra=r0+(o-r0)*i/n,rb=r0+(o-r0)*(i+1)/n;cap(P(ra,-1),P(ra,1),P(rb,-1),P(rb,1));}}
  // eave boards (wooden fascia) round the courtyard opening
  const W=SO('carWood');rev(W,0,0,[[ROOF.rin,13.72],[ROOF.rin,13.92],[ROOF.rin+.12,13.96],[ROOF.rin+.12,13.72]],160,{uvr:RC});
}

// ================================================================= entrance vestibules
function vestibule(side,width){
  ZONE='carVest';const F=sideFrame(side),A=SO('carVault'),L=H-RW-.6-.35,hw=width/2,sp=3.6;
  const sec=[[-hw,-.02],[hw,-.02],[hw,sp]];for(let i=1;i<12;i++){const a=i/12*Math.PI;sec.push([hw*Math.cos(a),sp+hw*Math.sin(a)]);}sec.push([-hw,sp]);
  plate(A,F,rectp(-hw-1.2,hw+1.2,-.3,sp+hw+1.2),[sec],-L-.35,-.35,{nofront:true});
  const fl=SO('carFloor');fl.quad(F.pt(-hw,.01,-L-.35),F.pt(hw,.01,-L-.35),F.pt(hw,.01,-.35),F.pt(-hw,.01,-.35),[0,0],[hw*2,0],[hw*2,L],[0,L],UP);
  // walkable floor and the blocking side walls
  
}

// ================================================================= gallery walls: doors, niches, tondi, pilasters
function archContour(tc,y0,w,ySpring,n=12){
  const pts=[[tc-w/2,y0],[tc+w/2,y0],[tc+w/2,ySpring]];
  for(let i=1;i<n;i++){const a=i/n*Math.PI;pts.push([tc+w/2*Math.cos(a),ySpring+w/2*Math.sin(a)]);}
  pts.push([tc-w/2,ySpring]);return pts;
}
function doorLeaf(F,t0,t1,y0,y1,d){SO('carDoor').quad(F.pt(t0,y0,d),F.pt(t1,y0,d),F.pt(t1,y1,d),F.pt(t0,y1,d),[0,0],[1,0],[1,1],[0,1],F.dd);}
function darkQuad(F,t0,t1,y0,y1,d){SO('carDark').quad(F.pt(t0,y0,d),F.pt(t1,y0,d),F.pt(t1,y1,d),F.pt(t0,y1,d),[0,0],[1,0],[1,1],[0,1],F.dd);}
function shell(F,tc,yc,r,d,mat){
  const S=SO(mat),n=9;
  for(let i=0;i<n;i++){const a0=Math.PI*i/n,a1=Math.PI*(i+1)/n,am=(a0+a1)/2,f=i%2?.82:1;
    const P=(rr,a,dd)=>F.pt(tc+rr*Math.cos(a),yc+rr*Math.sin(a),dd);
    S.tri(P(0,0,d),P(r*f,a0,d+.03+.015*(i%2)),P(r*f,a1,d+.03+.015*(i%2)),[0,0],[1,0],[0,1],F.dd);
    S.tri(P(0,0,d),P(r*f,a0,d+.03+.015*(i%2)),P(r*f*.0+0.0001,am,d+.12),[0,0],[1,0],[0,1],F.dd);}
}
function tondoPlaque(F,tc,yc,r,d,mat='carStone'){
  const S=SO(mat);
  frev(S,F,tc,yc,[[r,d],[r,d+.07],[r+.05,d+.1],[r+.12,d+.07],[r+.14,d+.03],[r+.14,d]],24);
  frev(S,F,tc,yc,[[0,d+.03],[r*.9,d+.04],[r*.92,d+.0]],20);
  ellipsoid(S,F,tc,yc,d+.06,r*.5,r*.55,.05,4,8);ellipsoid(S,F,tc-r*.3,yc+r*.3,d+.06,r*.2,r*.2,.04,3,6);
}
function docFrame(F,t0,t1,y0,y1,d0,d1,w=.14){
  const S=SO('carStone');
  fbox(S,F,t0-w,t0,y0,y1+w,d0,d1,{nb:true});fbox(S,F,t1,t1+w,y0,y1+w,d0,d1,{nb:true});
  fbox(S,F,t0-w*1.3,t1+w*1.3,y1,y1+w,d0,d1+.04);fbox(S,F,t0-w*1.8,t1+w*1.8,y1+w,y1+w*1.6,d0,d1+.12);
}
function galleryBay(j,level){
  const a=j*DA,F=wallFrame(a,RW),pb=2*RW*Math.sin(DA/2),A=SO('carAshlar'),St=SO('carStone');
  const y0=level?YG.floor:0,y1=level?12.4:5.3;
  const type=BAYT[j][level];
  const holes=[],post=[];
  const lh=level?0:0;
  const rel=y=>y0+y;
  if(type==='pass'){holes.push(archContour(0,y0,3.0,y0+2.9));post.push(()=>{});}
  else if(type==='gate'){
    holes.push(archContour(0,y0,2.6,y0+2.6));
    post.push(()=>{darkQuad(F,-1.3,1.3,y0,y0+4,-.55);doorLeaf(F,-1.3,0,y0,y0+3.3,-.25);doorLeaf(F,0,1.3,y0,y0+3.3,-.25);});
  }
  else if(type==='door'){
    const w=.66,h=2.7;holes.push(rectp(-w,w,y0,y0+h));
    post.push(()=>{doorLeaf(F,-w,w,y0,y0+h,-.25);docFrame(F,-w,w,y0,y0+h,-.0,.1);
      // blind arch above the door
      });
  }
  else if(type==='arch'){
    holes.push(archContour(0,y0+.0,2.1,y0+2.0,12));
    post.push(()=>{darkQuad(F,-1.1,1.1,y0,y0+4,-.16);fbox(St,F,-1.1,1.1,y0,y0+.2,-.16,.02);
      const w=.6,h=2.5;doorLeaf(F,-w,w,y0+.2,y0+h,-.1);docFrame(F,-w,w,y0+.2,y0+h,-.1,.06,.12);});
  }
  else if(type==='niche'){
    holes.push(archContour(0,y0+1.0,.95,y0+2.7,12));
    post.push(()=>{darkQuad(F,-.5,.5,y0+1.0,y0+3.4,-.38);shell(F,0,y0+2.7,.46,-.34,'carStone');
      fbox(St,F,-.62,.62,y0+.0,y0+1.0,0,.14);fbox(St,F,-.7,.7,y0+.95,y0+1.05,0,.2);fbox(St,F,-.7,.7,y0+.0,y0+.15,0,.18);
      frev(St,F,0,y0+2.7,[[.5,0],[.5,.09],[.63,.1],[.66,.0]],18);});
  }
  else if(type==='tondo'){
    post.push(()=>{fbox(St,F,-1.1,1.1,y0+.5,y0+.62,0,.07);fbox(St,F,-1.1,-1.0,y0+.5,y0+3.8,0,.07);fbox(St,F,1.0,1.1,y0+.5,y0+3.8,0,.07);fbox(St,F,-1.1,1.1,y0+3.68,y0+3.8,0,.07);
      tondoPlaque(F,0,y0+2.2,.55,.03);fbox(St,F,-.35,.35,y0+.62,y0+1.2,0,.05);});
  }
  else if(type==='window'){
    const w=.5;holes.push(archContour(0,y0+1.2,w*2,y0+2.6,10));
    post.push(()=>{darkQuad(F,-w,w,y0+1.2,y0+4,-.5);frev(St,F,0,y0+2.6,[[w,0],[w,.07],[w+.1,.1],[w+.14,0]],14);fbox(St,F,-w-.14,w+.14,y0+1.05,y0+1.2,0,.14);});
  }
  plate(A,F,rectp(-pb/2-.12,pb/2+.12,y0,y1),holes,-.6,0);
  for(const f of post)f();
}
// what stands in each bay of the lower / upper gallery wall (j = angle index; axes at 0, 8, 16, 24)
const BAYT=[];
(function(){
  const r=random(88),lo=['door','niche','tondo','arch','window','door','niche','tondo'],up=['door','niche','tondo','window','arch','tondo','niche','window'];
  let pl=null,pu=null;
  for(let j=0;j<NCOL;j++){
    let l=lo[(r()*lo.length)|0],u=up[(r()*up.length)|0];
    while(l===pl)l=lo[(r()*lo.length)|0];while(u===pu||(u==='door'&&j%4===0))u=up[(r()*up.length)|0];
    pl=l;pu=u;BAYT.push([l,u]);
  }
  BAYT[0][0]='gate';BAYT[24][0]='gate';BAYT[8][0]='pass';BAYT[16][0]='pass';
  for(const j of [0,8,16,24])BAYT[j][1]='gate';
  for(const j of [4,12,20,28])BAYT[j][0]='arch';
})();
function galleryWalls(){
  ZONE='carCourt';
  for(let j=0;j<NCOL;j++){galleryBay(j,0);galleryBay(j,1);}
  const St=SO('carStone');
  // pilasters aligned with the columns, with pedestals, caps and bases
  for(let k=0;k<NCOL;k++){
    const F=wallFrame((k+.5)*DA,RW);
    for(const [yb,yt] of [[0,5.2],[YG.floor,12.3]]){
      fbox(St,F,-.3,.3,yb,yb+.12,-.1,.2);fbox(St,F,-.26,.26,yb+.12,yb+.9,-.1,.15);fbox(St,F,-.3,.3,yb+.9,yb+1.0,-.1,.18);
      fbox(St,F,-.22,.22,yb+1.0,yt-.18,-.1,.14);fbox(St,F,-.3,.3,yt-.18,yt,-.1,.2);
    }
  }
}

// ================================================================= paved apron (Placeta Carlos V: OSM way 1082273597 clipped near the palace, plus the strips along the west and south fronts)
const PLAZA=[{"outer":[[-45.97,13.37],[-45.43,10.59],[-74.87,9.7],[-87.37,74.02],[-72.3,77.72],[-73.02,81.46],[-71.52,81.75],[-73.93,93.66],[-49.13,101.53],[-51.59,110.54],[-47.32,111.94],[-47.46,112.41],[-8.46,119.99],[-7.61,117.78],[-37.49,106.52],[-40.3,103.72],[-43.45,98.71],[-43.22,97.44],[5.56,106.92],[8.19,93.38],[-58.75,80.36],[-45.74,13.42]],"holes":[]}];
function plaza(){
  ZONE='carPlaza';const S=SO('carSlab');
  for(const pg of PLAZA){
    const C=pg.outer.map(p=>new THREE.Vector2(p[0],p[1])),Hs=pg.holes.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1])));
    const pts=[...pg.outer,...pg.holes.flat()],tr=THREE.ShapeUtils.triangulateShape(C,Hs);
    for(const [a,b,c] of tr){const A=pts[a],B=pts[b],D=pts[c];S.tri([A[0],.02,A[1]],[B[0],.02,B[1]],[D[0],.02,D[1]],[A[0],A[1]],[B[0],B[1]],[D[0],D[1]],UP);}
  }
}

// ================================================================= collision
function collision(){
  for(const sd of ['S','E','N','W']){
    const F=sideFrame(sd),ext=EXT(sd),gate=(sd==='S'||sd==='W')?1.5:0;
    const segs=gate?[[-H-ext,-gate],[gate,H+ext]]:[[-H-ext,H+ext]];
    for(const [a,b] of segs){const [x,,z]=F.pt((a+b)/2,0,-.71);NAV.box(x,z,b-a,2.58,0,18,F.rot);}
    if(gate){ // vestibule side walls
      const L=H-RW-.6;
      for(const sg of [-1,1]){const [x,,z]=F.pt(sg*(gate+.5),0,-L/2);NAV.box(x,z,1.0,L,0,18,F.rot);}
    }
  }
  // walkable floors at y = 0 under the courtyard + gallery ring and in both vestibules (independent of the terrain sampler)
  {const [x,z]=L2W(0,0);NAV.floor(x,z,2*RW+.2,2*RW+.2,0,-TH);}
  for(const sd of ['S','W']){const F=sideFrame(sd),L=H-RW-.95+.35,[x,,z]=F.pt(0,0,-(L+.35)/2+.35);NAV.floor(x,z,3.0,L+.35,0,F.rot);}
  const N=64;
  for(let i=0;i<N;i++){
    const a=(i+.5)/N*Math.PI*2,dS=Math.abs(Math.atan2(Math.sin(a-Math.PI/2),Math.cos(a-Math.PI/2))),dW=Math.abs(Math.atan2(Math.sin(a-Math.PI),Math.cos(a-Math.PI)));
    if(dS<.09||dW<.09)continue;
    const F=wallFrame(a,RW),[x,,z]=F.pt(0,0,-.9);NAV.box(x,z,2*(RW+1.7)*Math.sin(Math.PI/N)+.2,1.8,0,18,F.rot);
  }
}

export function build(b,ctx){
  LOW=!!(ctx&&ctx.low);
  const nb0=b.nav.blocks.length;NAV=b.nav;
  for(const s of ['S','W','N','E'])facade(s);
  rings();plinth();
  ZONE='carCourt';paving();colonnade();entablatures();triglyphs();galleryShell();galleryWalls();
  roof();chapel();plaza();
  vestibule('W',3.0);vestibule('S',3.0);
  collision();
  const tris=flush(b);
  if(typeof window!=='undefined')window.CAR={tris,nav:b.nav.blocks.slice(nb0)};
  
}
