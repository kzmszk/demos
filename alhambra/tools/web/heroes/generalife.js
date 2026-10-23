import * as THREE from 'three';
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js';
import { random } from '../materials.js';
import { plant, CYPRESS, ELM, PLANE, HOLM, OLIVE, ORANGE, PALM, SHRUB, POPLAR } from '../trees.js';
import { terrainHeight } from '../navigation.js';
import { stairs } from './common.js';
import { hedge, leaves, tree } from '../landscape-detail.js';

// The Generalife (Cerro del Sol): Patio de la Acequia and its pavilions, the Patio del Cipres de la Sultana,
// the Escalera del Agua, the upper gardens and the terraced Jardines Nuevos. Everything is modelled axis-aligned
// around the Patio de la Acequia, whose floor is at y = 32 and whose canal runs north-south at x = 370.
// Local patio frame: lx east, lz south, ly up from the court floor; world = (370 + lx, 32 + ly, -52 + lz).
// Proportions follow Wikimedia Commons photographs (see public/textures/generalife/credits.json).
const PI=Math.PI,X0=370,Y0=32,Z0=-52;
const TX='textures/generalife/';
const loadImg=async f=>{try{const i=new Image();i.src=TX+f;await i.decode();return i;}catch(e){return null;}};

// ---------------------------------------------------------------------------------------------------------
// procedural texture toolkit (all textures wrap)
const cv=(w,h=w)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c;};
function wrapDraw(S,x,y,r,fn){for(const dx of [-S,0,S])for(const dy of [-S,0,S]){if(x+dx+r<0||x+dx-r>S||y+dy+r<0||y+dy-r>S)continue;fn(x+dx,y+dy);}}
function blobs(g,S,r,n,r0,r1,cols){
  for(let i=0;i<n;i++){const x=r()*S,y=r()*S,rad=r0+r()*(r1-r0),col=cols[Math.floor(r()*cols.length)];
    wrapDraw(S,x,y,rad,(X,Y)=>{const q=g.createRadialGradient(X,Y,0,X,Y,rad);q.addColorStop(0,col);q.addColorStop(1,col.replace(/[\d.]+\)$/,'0)'));g.fillStyle=q;g.fillRect(X-rad,Y-rad,rad*2,rad*2);});}
}
function specks(g,S,r,n,cols,smin=1,smax=3){for(let i=0;i<n;i++){g.fillStyle=cols[Math.floor(r()*cols.length)];g.fillRect(r()*S,r()*S,smin+r()*(smax-smin),smin+r()*(smax-smin));}}
function tex(c,srgb=true,mirror=false){const t=new THREE.CanvasTexture(c);t.colorSpace=srgb?THREE.SRGBColorSpace:THREE.NoColorSpace;t.wrapS=t.wrapT=mirror?THREE.MirroredRepeatWrapping:THREE.RepeatWrapping;t.anisotropy=8;return t;}
const hsl=(h,s,l,a=1)=>`hsla(${h},${s}%,${l}%,${a})`;
const rr=(r,a,b)=>a+r()*(b-a);

function down(c,S){if(c.width<=S)return c;const o=cv(S,Math.round(c.height*S/c.width)),g=o.getContext('2d');g.imageSmoothingQuality='high';g.drawImage(c,0,0,o.width,o.height);return o;}
function limeTex(seed,base,warm=0){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle=base;g.fillRect(0,0,S,S);
  blobs(g,S,r,300,30,150,['rgba(255,250,236,.11)','rgba(168,146,108,.055)','rgba(100,92,80,.045)',`rgba(${190+warm},${150+warm},100,.04)`]);
  g.lineCap='round';
  for(let i=0;i<110;i++){const x=r()*S,y=r()*S,l=70+r()*180,a=(r()-.5)*.6;g.strokeStyle=r()>.5?'rgba(255,255,250,.06)':'rgba(120,104,84,.05)';g.lineWidth=8+r()*26;g.beginPath();g.moveTo(x,y);g.lineTo(x+Math.cos(a)*l,y+Math.sin(a)*l);g.stroke();}
  for(let i=0;i<14;i++){const x=r()*S,y=r()*S;g.strokeStyle='rgba(90,76,60,.16)';g.lineWidth=1;g.beginPath();g.moveTo(x,y);let px=x,py=y;for(let k=0;k<7;k++){px+=(r()-.5)*40;py+=r()*34;g.lineTo(px,py);}g.stroke();}
  specks(g,S,r,26000,['rgba(255,255,255,.10)','rgba(80,70,55,.09)','rgba(150,130,100,.08)'],1,2.4);
  return down(c,512);
}
// Brick (or paver) courses. Returns [colour, height] canvases covering tw x th metres.
function brickTex(seed,{tw=1.2,th=1.2,bw=.30,rows=17,joint=.016,hue=[14,30],sat=[28,52],lig=[44,66],mortar='#cdbfa6',S=1024,lime=.0,bond=1,burnt=.08}={}){
  const c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d'),r=random(seed);
  g.fillStyle=mortar;g.fillRect(0,0,S,S);hg.fillStyle='#303030';hg.fillRect(0,0,S,S);
  const bwp=bw/tw*S,chp=S/rows,jp=Math.max(2,joint/th*S);
  for(let j=0;j<rows;j++){
    const y=j*chp,off=bond?(j%2)*bwp/2+Math.floor(r()*2)*bwp*.0:0,n=Math.ceil(S/bwp)+2;
    for(let i=-1;i<n;i++){
      const x=i*bwp+off+(r()-.5)*2,w=bwp-jp,hh=chp-jp;
      const dark=r()<burnt,hu=rr(r,hue[0],hue[1])-(dark?4:0),sa=rr(r,sat[0],sat[1])-(dark?10:0),li=rr(r,lig[0],lig[1])-(dark?14:0);
      for(const dx of [0,-S,S]){
        g.fillStyle=hsl(hu,sa,li);g.fillRect(x+dx,y+jp/2,w,hh);
        g.fillStyle='rgba(255,240,220,.10)';g.fillRect(x+dx,y+jp/2,w,hh*.22);g.fillStyle='rgba(60,30,20,.12)';g.fillRect(x+dx,y+jp/2+hh*.78,w,hh*.22);
        hg.fillStyle=`rgb(${150+r()*70|0},${150+r()*70|0},${150+r()*70|0})`;hg.fillRect(x+dx,y+jp/2,w,hh);
      }
    }
  }
  blobs(g,S,r,90,10,70,['rgba(80,60,40,.10)','rgba(240,225,200,.09)','rgba(60,70,40,.05)']);
  if(lime>0)blobs(g,S,r,Math.round(60*lime),20,110,['rgba(236,226,208,.5)','rgba(226,214,194,.35)']);
  specks(g,S,r,22000,['rgba(255,255,255,.10)','rgba(40,30,20,.12)'],1,2.2);
  return [c,h];
}
function rubbleTex(seed,{tw=2.4,th=2.4,S=1024,rows=9,brickBand=3,tone=0}={}){
  const c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d'),r=random(seed);
  g.fillStyle='#8b7e68';g.fillRect(0,0,S,S);hg.fillStyle='#202020';hg.fillRect(0,0,S,S);
  const rowH=S/rows;let y=0;
  for(let j=0;j<rows;j++){
    const band=(j%brickBand)===brickBand-1,hh=(band?rowH*.62:rowH*(.85+r()*.35)),yy=y;y+=hh;
    if(yy>S+20)break;
    let x=-r()*60;
    while(x<S){
      const w=band?S/tw*.28*(.9+r()*.2):(S/tw*(.30+r()*.38));const col=band?hsl(rr(r,16,26),rr(r,28,42),rr(r,44,58)):hsl(rr(r,26,42)+tone,rr(r,10,26),rr(r,44,68));
      const ph=band?hh*.46:hh;
      for(const dx of [0,-S]){
        g.fillStyle=col;g.beginPath();
        if(band){g.rect(x+dx+2,yy+3,w-4,hh-6);}else{const k=.1+r()*.12;const pts=[[x+w*k,yy+hh*.06],[x+w*(1-k*.8),yy+hh*(.0+.08*r())],[x+w-2,yy+hh*.3],[x+w-3,yy+hh*.88],[x+w*.6,yy+hh-2],[x+w*.1,yy+hh*.92],[x+3,yy+hh*.5]];pts.forEach(([px,py],i)=>i?g.lineTo(px+dx,py):g.moveTo(px+dx,py));g.closePath();}
        g.fill();
        g.fillStyle='rgba(255,245,225,.10)';g.fillRect(x+dx+4,yy+4,w-8,hh*.18);g.fillStyle='rgba(40,25,15,.14)';g.fillRect(x+dx+4,yy+hh*.78,w-8,hh*.16);
        hg.fillStyle=`rgb(${160+r()*60|0},${160+r()*60|0},${160+r()*60|0})`;hg.fillRect(x+dx+3,yy+3,w-6,hh-6);
      }
      x+=w;
    }
  }
  blobs(g,S,r,120,12,90,['rgba(60,45,30,.10)','rgba(235,225,205,.08)','rgba(70,80,45,.05)']);
  specks(g,S,r,26000,['rgba(255,255,255,.09)','rgba(30,25,20,.12)'],1,2.4);
  return [c,h];
}
// Curved clay tiles: 5 ribs per metre, 3 courses per metre (matches roofFace with rw = .2).
function roofTex(seed,{tone=0,moss=.5}={}){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed),cols=5,rows=3,cw=S/cols,rh=S/rows;
  g.fillStyle='#3d2a22';g.fillRect(0,0,S,S);
  for(let j=-1;j<rows+1;j++)for(let i=0;i<cols;i++){
    const x=i*cw,y=j*rh,hu=rr(r,12,22)+tone,sa=rr(r,28,46),li=rr(r,32,47),grey=r()<.22;
    const base=grey?hsl(rr(r,18,30),rr(r,8,18),rr(r,34,46)):hsl(hu,sa,li);
    for(const dy of [0,S]){
      const gr=g.createLinearGradient(x,0,x+cw,0);gr.addColorStop(0,'rgba(30,16,12,.62)');gr.addColorStop(.22,'rgba(0,0,0,0)');gr.addColorStop(.62,'rgba(255,225,190,.18)');gr.addColorStop(1,'rgba(30,16,12,.62)');
      g.fillStyle=base;g.fillRect(x+1,y+dy,cw-2,rh);g.fillStyle=gr;g.fillRect(x+1,y+dy,cw-2,rh);
      const vg=g.createLinearGradient(0,y+dy,0,y+dy+rh);vg.addColorStop(0,'rgba(20,10,8,.42)');vg.addColorStop(.30,'rgba(20,10,8,0)');vg.addColorStop(.92,'rgba(255,230,200,.06)');vg.addColorStop(1,'rgba(10,5,4,.55)');
      g.fillStyle=vg;g.fillRect(x+1,y+dy,cw-2,rh);
    }
  }
  blobs(g,S,r,Math.round(120*moss),8,50,['rgba(120,128,60,.22)','rgba(190,180,110,.16)','rgba(40,36,30,.18)','rgba(215,200,170,.10)']);
  specks(g,S,r,18000,['rgba(255,255,255,.07)','rgba(10,6,4,.13)'],1,2.2);
  return c;
}
function stoneTex(seed,{tw=1.2,th=1.2,base=[34,30,72],cols=2,rows=2,S=1024,pink=0}={}){
  const c=cv(S),g=c.getContext('2d'),h=cv(S),hg=h.getContext('2d'),r=random(seed);
  g.fillStyle='#7d725f';g.fillRect(0,0,S,S);hg.fillStyle='#303030';hg.fillRect(0,0,S,S);
  const cw=S/cols,rh=S/rows;
  for(let j=0;j<rows;j++)for(let i=0;i<cols;i++){
    const off=(j%2)*cw*.5;
    for(const dx of [0,-S]){const x=i*cw+off+dx,y=j*rh;
      g.fillStyle=hsl(rr(r,base[0],base[0]+8)+pink,rr(r,base[1]-8,base[1]+6),rr(r,base[2]-4,base[2]+5));g.fillRect(x+3,y+3,cw-6,rh-6);
      hg.fillStyle=`rgb(${170+r()*50|0},${170+r()*50|0},${170+r()*50|0})`;hg.fillRect(x+3,y+3,cw-6,rh-6);}
  }
  blobs(g,S,r,140,10,100,['rgba(255,244,222,.10)','rgba(120,96,70,.08)','rgba(80,86,56,.04)']);
  specks(g,S,r,30000,['rgba(255,255,255,.12)','rgba(60,45,30,.14)'],1,2.2);
  return [c,h];
}
function timberTex(seed,{planks=8,hue=24,lig=33}={}){
  const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);const ph=S/planks;
  for(let j=0;j<planks;j++){g.fillStyle=hsl(hue+rr(r,-3,3),rr(r,38,52),lig+rr(r,-4,5));g.fillRect(0,j*ph,S,ph-1.5);
    for(let k=0;k<26;k++){g.strokeStyle=r()>.5?'rgba(255,220,170,.10)':'rgba(20,8,2,.22)';g.lineWidth=.6+r()*1.4;g.beginPath();const y=j*ph+r()*ph;g.moveTo(0,y);g.bezierCurveTo(S*.3,y+(r()-.5)*4,S*.7,y+(r()-.5)*4,S,y+(r()-.5)*3);g.stroke();}}
  g.fillStyle='rgba(10,4,2,.65)';for(let j=0;j<planks;j++)g.fillRect(0,j*ph-1,S,2);
  return c;
}
function doorTex(seed){
  const W=512,H=1024,c=cv(W,H),g=c.getContext('2d'),r=random(seed);
  g.fillStyle='#6e3a1e';g.fillRect(0,0,W,H);
  for(let x=0;x<W;x+=26){g.fillStyle=`rgba(${r()>.5?'255,190,130':'20,6,0'},${.05+r()*.07})`;g.fillRect(x,0,10+r()*14,H);}
  const leaf=(x0,w)=>{
    g.fillStyle='#8a4c26';g.fillRect(x0+6,6,w-12,H-12);
    g.strokeStyle='#3a1b0c';g.lineWidth=5;g.strokeRect(x0+6,6,w-12,H-12);
    const cx=2,cy=5,pw=(w-56)/cx,ph=(H-90)/cy;
    for(let j=0;j<cy;j++)for(let i=0;i<cx;i++){const x=x0+22+i*(pw+12),y=22+j*(ph+12);
      g.fillStyle='#74401f';g.fillRect(x,y,pw,ph);g.fillStyle='rgba(255,200,140,.30)';g.fillRect(x,y,pw,4);g.fillRect(x,y,4,ph);g.fillStyle='rgba(15,5,0,.50)';g.fillRect(x,y+ph-4,pw,4);g.fillRect(x+pw-4,y,4,ph);
      g.fillStyle='#9a5a2c';g.fillRect(x+14,y+14,pw-28,ph-28);g.fillStyle='rgba(15,5,0,.38)';g.fillRect(x+14,y+14,pw-28,3);g.fillRect(x+14,y+14,3,ph-28);}
    g.fillStyle='#2a2420';for(let j=0;j<=cy;j++)for(let i=0;i<=cx;i++){g.beginPath();g.arc(x0+22-6+i*(pw+12),22-6+j*(ph+12),3.4,0,7);g.fill();}
  };
  leaf(0,W/2);leaf(W/2,W/2);g.fillStyle='#1b0d05';g.fillRect(W/2-2,0,4,H);
  return c;
}
// Tileable dense leaf mat with transparent gaps (laurel / ivy): size px, coverage by count.
function leafTileTex(seed,{n=2600,hue=[88,118],lig=[14,34],size=[9,17],S=512}={}){
  const c=cv(S),g=c.getContext('2d'),r=random(seed);
  for(let i=0;i<n;i++){const x=r()*S,y=r()*S,sz=size[0]+r()*(size[1]-size[0]),a=r()*6.28;
    wrapDraw(S,x,y,sz,(X,Y)=>{g.save();g.translate(X,Y);g.rotate(a);g.fillStyle=hsl(rr(r,hue[0],hue[1]),rr(r,26,46),rr(r,lig[0],lig[1]));g.beginPath();g.ellipse(0,0,sz,sz*.42,0,0,7);g.fill();g.strokeStyle='rgba(180,220,120,.22)';g.lineWidth=1;g.beginPath();g.moveTo(-sz*.8,0);g.lineTo(sz*.8,0);g.stroke();g.restore();});}
  return c;
}
// One rib of a radially ribbed voussoir band (fluted stucco), 64 px per rib.
function ribTex(){const c=cv(64),g=c.getContext('2d');const gr=g.createLinearGradient(0,0,64,0);gr.addColorStop(0,'#b5a487');gr.addColorStop(.2,'#e9dcbd');gr.addColorStop(.5,'#fbf3da');gr.addColorStop(.8,'#e9dcbd');gr.addColorStop(1,'#b5a487');g.fillStyle=gr;g.fillRect(0,0,64,64);return c;}
function barkTex(seed){const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#9a9387';g.fillRect(0,0,S,S);
  for(let i=0;i<500;i++){const x=r()*S,w=2+r()*9,l=60+r()*220,y=r()*S;g.fillStyle=r()>.5?`rgba(${40+r()*30|0},${34+r()*24|0},${28+r()*20|0},${.25+r()*.35})`:`rgba(200,190,172,${.12+r()*.2})`;for(const dy of [0,-S,S])g.fillRect(x,y+dy,w,l);}
  specks(g,S,r,5000,['rgba(255,255,255,.12)','rgba(20,15,10,.25)'],1,3);return c;}
function hedgeTex(seed,{hue=[90,116],lig=[22,42]}={}){
  const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#2f4a24';g.fillRect(0,0,S,S);
  for(let i=0;i<5200;i++){const x=r()*S,y=r()*S,s=3+r()*6;wrapDraw(S,x,y,s,(X,Y)=>{g.fillStyle=hsl(rr(r,hue[0],hue[1]),rr(r,28,50),rr(r,lig[0],lig[1]));g.beginPath();g.ellipse(X,Y,s,s*.55,r()*3.14,0,7);g.fill();g.fillStyle='rgba(220,255,180,.07)';g.beginPath();g.ellipse(X-s*.2,Y-s*.15,s*.5,s*.2,0,0,7);g.fill();});}
  blobs(g,S,r,40,10,50,['rgba(0,0,0,.14)','rgba(150,190,90,.07)']);
  return c;
}
function soilTex(seed){const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#4a3a2b';g.fillRect(0,0,S,S);blobs(g,S,r,90,6,50,['rgba(30,20,12,.28)','rgba(150,120,85,.14)']);specks(g,S,r,9000,['rgba(220,200,170,.30)','rgba(20,12,6,.35)','rgba(110,90,66,.35)'],1,3);return c;}
function gravelTex(seed,{base='#b49a76',cols=['#d6c3a0','#8d7658','#c1a67c','#6f5d46','#e1d2b5']}={}){const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle=base;g.fillRect(0,0,S,S);blobs(g,S,r,70,10,60,['rgba(90,70,45,.14)','rgba(240,225,195,.12)']);for(let i=0;i<9000;i++){const x=r()*S,y=r()*S,s=1.4+r()*3.4;g.fillStyle=cols[Math.floor(r()*cols.length)];g.beginPath();g.ellipse(x,y,s,s*.7,r()*3,0,7);g.fill();}return c;}
// Black-and-white pebble mosaic paving (empedrado granadino): 2 x 2 m of concentric rosettes joined by diagonal bands.
function pebbleTex(seed){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#5b5246';g.fillRect(0,0,S,S);
  const pat=(x,y)=>{ // 0 dark, 1 light, 2 ochre
    const cell=S/4,u=((x%cell)+cell)%cell/cell-.5,v=((y%cell)+cell)%cell/cell-.5,d=Math.hypot(u,v),dm=Math.abs(u)+Math.abs(v);
    if(d<.09)return 0;if(d<.17)return 1;if(d<.25)return 0;if(d<.31)return 2;
    if(dm>.8)return 0;if(dm>.64)return 1;
    const diag=Math.min(Math.abs(u-v),Math.abs(u+v));if(diag<.05)return 0;
    return ((Math.floor((x+y)/cell*2)%2)?2:1);};
  for(let i=0;i<30000;i++){const x=r()*S,y=r()*S,k=pat(x,y),s2=4.2+r()*3.6;
    const col=k===1?hsl(rr(r,36,46),rr(r,6,18),rr(r,74,90)):k===0?hsl(rr(r,20,34),rr(r,4,14),rr(r,12,26)):hsl(rr(r,28,38),rr(r,18,30),rr(r,52,68));
    wrapDraw(S,x,y,s2,(X,Y)=>{g.fillStyle='rgba(0,0,0,.30)';g.beginPath();g.ellipse(X+1.2,Y+1.6,s2*.95,s2*.7,0,0,7);g.fill();g.fillStyle=col;g.beginPath();g.ellipse(X,Y,s2*.9,s2*.68,r()*3,0,7);g.fill();g.fillStyle='rgba(255,255,255,.10)';g.beginPath();g.ellipse(X-s2*.2,Y-s2*.2,s2*.4,s2*.22,0,0,7);g.fill();});}
  return c;
}
function marbleTex(seed){const S=512,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#e8e4da';g.fillRect(0,0,S,S);blobs(g,S,r,60,20,90,['rgba(255,255,255,.2)','rgba(160,150,135,.10)']);g.lineWidth=1;for(let i=0;i<14;i++){g.strokeStyle='rgba(120,110,100,.16)';g.beginPath();let x=r()*S,y=0;g.moveTo(x,y);for(let k=0;k<12;k++){x+=(r()-.5)*50;y+=S/12;g.lineTo(x,y);}g.stroke();}specks(g,S,r,5000,['rgba(255,255,255,.12)','rgba(100,90,80,.08)']);return c;}
// Carved-stucco sebka lattice (fallback when the photo-derived panel is missing).
function stuccoTex(seed){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed);g.fillStyle='#d9c7a2';g.fillRect(0,0,S,S);
  const n=4,st=S/n;g.lineWidth=14;g.strokeStyle='#efe0bc';
  for(let j=-1;j<=n;j++)for(let i=-1;i<=n;i++){const x=i*st,y=j*st;g.beginPath();g.moveTo(x,y+st/2);g.lineTo(x+st/2,y);g.lineTo(x+st,y+st/2);g.lineTo(x+st/2,y+st);g.closePath();g.stroke();
    g.fillStyle='#e9d9b3';g.beginPath();g.ellipse(x+st/2,y+st/2,st*.13,st*.2,0,0,7);g.fill();g.strokeStyle='#bba67e';g.lineWidth=3;g.stroke();g.lineWidth=14;g.strokeStyle='#efe0bc';}
  specks(g,S,r,20000,['rgba(255,255,255,.12)','rgba(90,70,40,.12)'],1,2.4);return c;
}
// Sprite atlas of flowering clumps (3 x 3 cells of 341 px) for crossed-card planting.
function plantAtlas(seed){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed),N=3,cs=S/N;
  const sets=[
    {leaf:[96,118],lg:[16,34],fl:['#c53a46','#d9566a','#b52e3d'],n:34,fr:7,tall:.74},      // roses
    {leaf:[92,112],lg:[22,38],fl:['#6c5ab8','#8570cf','#5a4aa8'],n:56,fr:4,tall:.95,spike:1}, // salvia / lavender spikes
    {leaf:[84,104],lg:[22,38],fl:['#f1a533','#f6c14a','#e98a2b'],n:44,fr:6,tall:.62},      // marigold
    {leaf:[100,122],lg:[20,36],fl:[],n:0,fr:0,tall:.82},                                     // green shrub
    {leaf:[98,116],lg:[22,40],fl:['#f5f1e6','#ece6d6','#fffaf0'],n:46,fr:5,tall:.78},      // white flowers
    {leaf:[96,112],lg:[22,36],fl:['#e8763a','#d65a2a','#f08b4e'],n:36,fr:6,tall:.7},       // orange geranium
    {leaf:[104,124],lg:[24,42],fl:[],n:0,fr:0,tall:1.0,grass:1},                              // tall grass / canna
    {leaf:[96,118],lg:[22,38],fl:['#f2b8c6','#e898ac','#f6cdd8'],n:40,fr:6,tall:.7},      // pink
    {leaf:[92,110],lg:[20,34],fl:['#d8d34a','#e9e270','#c7c23a'],n:40,fr:5,tall:.66}       // yellow
  ];
  sets.forEach((s,k)=>{
    const ox=(k%N)*cs,oy=Math.floor(k/N)*cs,bx=ox+cs/2,by=oy+cs-6,H=cs*s.tall;
    const leafAt=(x,y,a,len,w)=>{g.save();g.translate(x,y);g.rotate(a);g.fillStyle=hsl(rr(r,s.leaf[0],s.leaf[1]),rr(r,30,52),rr(r,s.lg[0],s.lg[1]));g.beginPath();g.moveTo(0,0);g.quadraticCurveTo(w,-len*.5,0,-len);g.quadraticCurveTo(-w,-len*.5,0,0);g.fill();g.restore();};
    if(s.grass){for(let i=0;i<46;i++){const a=(r()-.5)*1.1;leafAt(bx+(r()-.5)*cs*.4,by,a,H*(.4+r()*.6),3+r()*3);}return;}
    for(let i=0;i<70;i++){const a=(r()-.5)*2.5,len=H*(.18+r()*.55);leafAt(bx+(r()-.5)*cs*.55,by-r()*cs*.1,a,len,5+r()*8);}
    if(s.spike){for(let i=0;i<s.n;i++){const x=bx+(r()-.5)*cs*.6,top=by-H*(.5+r()*.5);g.strokeStyle='#4d6b3a';g.lineWidth=1.6;g.beginPath();g.moveTo(x,by-4);g.lineTo(x+(r()-.5)*10,top);g.stroke();for(let q=0;q<9;q++){g.fillStyle=s.fl[Math.floor(r()*s.fl.length)];g.beginPath();g.ellipse(x+(r()-.5)*7,top+q*5,3.2,2.6,0,0,7);g.fill();}}return;}
    for(let i=0;i<s.n;i++){const a=r()*6.28,rad=Math.sqrt(r())*cs*.34,x=bx+Math.cos(a)*rad*1.1,y=by-H*(.38+r()*.52)-Math.abs(Math.sin(a))*rad*.2,sz=s.fr*(.8+r()*.7);
      g.fillStyle=s.fl[Math.floor(r()*s.fl.length)];g.beginPath();g.arc(x,y,sz,0,7);g.fill();g.fillStyle='rgba(255,255,255,.18)';g.beginPath();g.arc(x-sz*.25,y-sz*.25,sz*.45,0,7);g.fill();g.fillStyle='rgba(60,20,20,.3)';g.beginPath();g.arc(x,y,sz*.28,0,7);g.fill();}
  });
  return c;
}
// Bougainvillea / climbing foliage atlas (4 cells of 512): magenta bracts, green ivy, white jasmine, rose.
// blob = true draws each cell as a soft-edged clump (for loose cards), otherwise it fills the cell edge to edge (wall mats).
function climberAtlas(seed,blob=false){
  const S=1024,c=cv(S),g=c.getContext('2d'),r=random(seed),cs=S/2;
  const cell=(k,colors,leafc,dens,size)=>{
    const ox=(k%2)*cs,oy=Math.floor(k/2)*cs;
    const pt=()=>{if(!blob)return [r()*cs,r()*cs];for(;;){const x=(r()*2-1),y=(r()*2-1),d=x*x+y*y;if(d<1&&r()<(1-d)*1.3+.1)return [cs/2+x*cs*.47,cs/2+y*cs*.47];}};
    const rich=blob?1.35:1;
    for(let i=0;i<dens*.5*rich;i++){const [x,y]=pt(),s2=size*(.9+r()*.9);g.save();g.translate(ox+x,oy+y);g.rotate(r()*6.28);g.fillStyle=hsl(rr(r,leafc[0],leafc[1]),rr(r,30,50),rr(r,16,34));g.beginPath();g.ellipse(0,0,s2*1.4,s2*.7,0,0,7);g.fill();g.restore();}
    for(let i=0;i<dens*.5*rich;i++){if(!colors.length)break;const [x,y]=pt(),s2=size*(.9+r()*.8);g.save();g.translate(ox+x,oy+y);g.rotate(r()*6.28);g.fillStyle=colors[Math.floor(r()*colors.length)];g.beginPath();g.ellipse(0,0,s2*1.1,s2*.85,0,0,7);g.fill();g.fillStyle='rgba(255,255,255,.12)';g.beginPath();g.ellipse(-s2*.2,-s2*.2,s2*.5,s2*.35,0,0,7);g.fill();g.restore();}
  };
  cell(0,['#b3267f','#c93a97','#9c1d6e','#d85aa8'],[85,110],900,9);
  cell(1,[],[92,118],blob?1100:2600,blob?8:5.5);
  cell(2,['#f7f3ea','#efe9dc'],[90,112],900,6);
  cell(3,['#c8384a','#da5368','#b02a3a'],[92,112],760,8);
  return c;
}
// ---------------------------------------------------------------------------------------------------------
export async function materials(M){
  const q=new URLSearchParams(location.search).get('q'),lowQ=q==='low'||(q!=='high'&&matchMedia('(pointer: coarse)').matches);
  const mat=(name,o={})=>{
    let {map,bump,tw=1,th=tw,color=0xffffff,rough=.92,bs=.03,side,alpha,po=0,metal=0,mirror=false,emissive,max=1024}=o;
    if(lowQ)max=Math.min(max,512);
    if(map&&map.width>max){const m2=down(map,max);if(bump===map)bump=m2;map=m2;}
    if(bump&&bump!==map&&bump.width>max)bump=down(bump,max);
    if(lowQ&&bump!==map)bump=null;
    const m=new THREE.MeshStandardMaterial({color,roughness:rough,metalness:metal});m.name=name;m.userData={scale:1};
    const mk=(c,srgb)=>{const t=tex(c,srgb,mirror);t.repeat.set(1/tw,1/th);return t;};
    if(map)m.map=mk(map,true);if(bump){m.bumpMap=bump===map?m.map:mk(bump,false);m.bumpScale=bs;}
    if(side!==undefined)m.side=side;if(alpha){m.alphaTest=alpha;}
    if(po){m.polygonOffset=true;m.polygonOffsetFactor=-po;m.polygonOffsetUnits=-po;}
    if(emissive){m.emissive.set(emissive);}
    M[name]=m;return m;
  };
  const lime=limeTex(11,'#f1ede2'),limeW=limeTex(12,'#ebe3cf',14),limeD=limeTex(13,'#d3c9b4',8),pink=limeTex(14,'#d8ab8c',30),gold=limeTex(15,'#cdb07a',30);
  mat('gnLime',{map:lime,bump:lime,tw:3,bs:.012,rough:.95});
  mat('gnLimeWarm',{map:limeW,bump:limeW,tw:3,bs:.012,rough:.95});
  mat('gnLimeDirty',{map:limeD,bump:limeD,tw:3,bs:.02,rough:.97});
  mat('gnPink',{map:pink,bump:pink,tw:2,bs:.02,rough:.9});
  
  let [c,h]=brickTex(21,{hue:[18,30],sat:[26,40],lig:[64,78],mortar:'#dccfb8',lime:.9,burnt:.04});mat('gnBrickPale',{map:c,bump:h,tw:1.2,bs:.035,rough:.95});
  [c,h]=brickTex(22,{hue:[10,22],sat:[40,58],lig:[40,56],mortar:'#c6b79d',lime:.25,burnt:.12});mat('gnBrickRed',{map:c,bump:h,tw:1.2,bs:.04,rough:.94});
  [c,h]=brickTex(23,{tw:1.2,th:1.2,bw:.30,rows:9,joint:.014,hue:[16,28],sat:[26,40],lig:[66,78],mortar:'#d6cab2',bond:1,burnt:.03});mat('gnPaver',{map:c,bump:h,tw:1.2,bs:.02,rough:.9,max:512});
  [c,h]=brickTex(24,{tw:1.2,th:1.2,bw:.30,rows:4,joint:.012,hue:[7,16],sat:[46,62],lig:[36,48],mortar:'#bda88c',bond:0,burnt:.1});mat('gnTerra',{map:c,bump:h,tw:1.2,bs:.015,rough:.8,max:512});
  [c,h]=rubbleTex(31);mat('gnRubble',{map:c,bump:h,tw:2.4,bs:.06,rough:1});
  [c,h]=rubbleTex(32,{brickBand:4,tone:-4});mat('gnRubbleB',{map:c,bump:h,tw:2.4,bs:.06,rough:1,max:512});
  const rt=roofTex(41);mat('gnRoof',{map:rt,bump:rt,tw:1,bs:.05,rough:.88,side:THREE.DoubleSide});
  const rt2=roofTex(42,{tone:-4,moss:1});mat('gnRoofOld',{map:rt2,bump:rt2,tw:1,bs:.05,rough:.9,side:THREE.DoubleSide,max:512});
  [c,h]=stoneTex(51,{pink:6});mat('gnCoping',{map:c,bump:h,tw:1.2,bs:.02,rough:.82,max:512});
  [c,h]=stoneTex(52,{base:[36,12,70],cols:3,rows:3});mat('gnStone',{map:c,bump:h,tw:1.8,bs:.03,rough:.9,max:512});
  const mb=marbleTex(53);mat('gnMarble',{map:mb,bump:mb,tw:1.6,bs:.006,rough:.38});
  const tb=timberTex(61);mat('gnTimber',{map:tb,bump:tb,tw:1,bs:.02,rough:.78});
  const tb2=timberTex(62,{planks:6,hue:20,lig:17});mat('gnTimberDark',{map:tb2,bump:tb2,tw:1,bs:.02,rough:.8});
  mat('gnDoor',{map:doorTex(63),tw:1,th:1,rough:.7,bump:null});
  const [stars,frieze]=await Promise.all([loadImg('stucco-stars.jpg'),loadImg('frieze-kufic.jpg')]);
  if(stars){mat('gnStucco',{map:stars,bump:stars,tw:1.8,th:1.86,bs:.2,rough:.9,mirror:true});mat('gnGold',{map:stars,bump:stars,tw:1.3,th:1.35,bs:.1,rough:.88,color:0xf3e6c6,mirror:true});}
  else{const st=stuccoTex(71);mat('gnStucco',{map:st,bump:st,tw:1.2,bs:.05,rough:.88});mat('gnGold',{map:gold,bump:gold,tw:2,bs:.02,rough:.85});}
  if(frieze)mat('gnFrieze',{map:frieze,bump:frieze,tw:1,th:1,bs:.1,rough:.9});else{const st=stuccoTex(72);mat('gnFrieze',{map:st,tw:1,th:1,rough:.9});}
  const hg=hedgeTex(81,{hue:[92,118],lig:[24,44]});mat('gnHedge',{map:hg,bump:hg,tw:.6,bs:.06,rough:.95});
  const hg2=hedgeTex(82,{hue:[78,104],lig:[22,38]});mat('gnHedgeLight',{map:hg2,bump:hg2,tw:.6,bs:.06,rough:.95});
  const so=soilTex(91);mat('gnSoil',{map:so,bump:so,tw:1,bs:.05,rough:1});
  const gr=gravelTex(92);mat('gnGravel',{map:gr,bump:gr,tw:1,bs:.05,rough:1});
  const pb=pebbleTex(93);mat('gnPebble',{map:pb,bump:pb,tw:2,bs:.05,rough:.85});
  mat('gnLawn',{map:hedgeTex(94,{hue:[78,98],lig:[34,52]}),tw:1.2,rough:1,color:0xf2f2d8});
  const pa=plantAtlas(95);mat('gnPlant',{map:pa,tw:1,th:1,alpha:.45,side:THREE.DoubleSide,rough:.85});
  const ca=climberAtlas(96);mat('gnClimb',{map:ca,tw:1,th:1,alpha:.45,side:THREE.DoubleSide,rough:.85});
  const cb=climberAtlas(97,true);mat('gnBlob',{map:cb,tw:1,th:1,alpha:.45,side:THREE.DoubleSide,rough:.85});
  const oc=limeTex(17,'#d8bb86',50);mat('gnOcher',{map:oc,bump:oc,tw:3,bs:.02,rough:.95});
  const bk=barkTex(64);mat('gnBark',{map:bk,tw:1,th:1.4,rough:.97,bump:bk,bs:.08,color:0xd6cfc4});
  {const hc=hedgeTex(83,{hue:[96,120],lig:[16,28]});mat('gnTunnel',{map:hc,bump:hc,tw:.5,bs:.08,rough:.95,side:THREE.DoubleSide});}
  {const gt=hedgeTex(84,{hue:[52,76],lig:[30,46]});mat('gnBank',{map:gt,bump:gt,tw:1.4,bs:.05,rough:1,color:0xe4d8b0});}
  {const lt=leafTileTex(85);mat('gnLeafMat',{map:lt,tw:1,th:1,alpha:.4,side:THREE.DoubleSide,rough:.9});const lt2=leafTileTex(86,{hue:[80,104],lig:[22,44],n:2200});mat('gnLeafMat2',{map:lt2,tw:1,th:1,alpha:.4,side:THREE.DoubleSide,rough:.9});}
  mat('gnWaterStrip',{color:0x5b8c8f,rough:.12,metal:.25});
  {const rb=ribTex();mat('gnRib',{map:rb,bump:rb,tw:1,th:1,bs:.06,rough:.88});const rp=ribTex();mat('gnRibPink',{map:rp,bump:rp,tw:1,th:1,bs:.06,rough:.88,color:0xeec3a4});}
  mat('gnIron',{color:0x24211e,rough:.55,metal:.35});
  mat('gnTrellis',{color:0x3c4a33,rough:.8});
  mat('gnGlassDark',{color:0x4a3b2f,rough:.9});
  mat('gnRidge',{color:0xb06a48,rough:.85});
  M.gnJet=new THREE.MeshBasicMaterial({color:0xe6f3f0,transparent:true,opacity:.5,depthWrite:false});M.gnJet.name='jet';
  M.gnBasin=new THREE.MeshStandardMaterial({color:0x3f6f68,roughness:.2,metalness:.1});M.gnBasin.name='gnBasin';M.gnBasin.userData={scale:1};
}

// ---------------------------------------------------------------------------------------------------------
// geometry helpers. A "frame" f = {x,y,z,yaw}: local u runs to the right as seen from outside, y up, w outward;
// yaw turns the local +w axis to world (sin yaw, cos yaw).
const F=(x,z,yaw=0,y=0)=>({x,y,z,yaw});
const xf=(g,f)=>{if(f.yaw)g.rotateY(f.yaw);g.translate(f.x,f.y||0,f.z);return g;};
const V2=a=>a.map(p=>new THREE.Vector2(p[0],p[1]));
// World-space planar UVs (metres) chosen per triangle by its dominant axis, then creased smooth normals.
function prep(g,crease=.7){
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
  return toCreasedNormals(ng,crease);
}
const put=(b,g,f,mat,crease)=>b.unique(prep(xf(g,f),crease),mat);
const rectPts=(u0,y0,u1,y1)=>[[u0,y0],[u1,y0],[u1,y1],[u0,y1]];
// Pointed (optionally horseshoe) arch outline from the left foot over the apex to the right foot, in (u,y).
function archPts(cu,yb,w,ys,rise,{hs=0,n=12}={}){
  const hw=w/2,pts=[];
  if(rise<=hw){pts.push([cu-hw,yb],[cu-hw,ys]);for(let i=1;i<n*2;i++){const a=PI-i*PI/(n*2);pts.push([cu+Math.cos(a)*hw,ys+Math.sin(a)*rise]);}pts.push([cu+hw,ys],[cu+hw,yb]);return pts;}
  const s=(rise*rise-hw*hw)/w,R=hw+s,ta=Math.atan2(rise,s),left=[];
  for(let i=0;i<=n;i++){const a=PI+hs-i*(hs+ta)/n;left.push([cu+s+R*Math.cos(a),ys+R*Math.sin(a)]);}
  const right=left.slice(0,-1).reverse().map(([x,y])=>[2*cu-x,y]);
  return [[left[0][0],yb],...left,...right,[right[right.length-1][0],yb]];
}
// Flat slab with holes, outward face at w=0, body at w in [-t,0].
function slab(b,f,mat,{u0,u1,y0,y1,t,holes=[]},crease=.5){
  const s=new THREE.Shape(V2(rectPts(u0,y0,u1,y1)));for(const h of holes)s.holes.push(new THREE.Path(V2(h)));
  const g=new THREE.ExtrudeGeometry(s,{depth:t,bevelEnabled:false,curveSegments:1});g.translate(0,0,-t);put(b,g,f,mat,crease);
}
// Extruded polygon (u,y) from w=w0 to w=w1; `holes` as for slab.
function prism(b,f,mat,pts,w0,w1,holes=[],crease=.9){
  const s=new THREE.Shape(V2(pts));for(const h of holes)s.holes.push(new THREE.Path(V2(h)));
  const g=new THREE.ExtrudeGeometry(s,{depth:Math.abs(w1-w0),bevelEnabled:false,curveSegments:1});g.translate(0,0,Math.min(w0,w1));put(b,g,f,mat,crease);
}
// Axis-aligned local box.
function lbox(b,f,mat,u0,y0,w0,u1,y1,w1,crease=.2){
  const g=new THREE.BoxGeometry(u1-u0,y1-y0,w1-w0);g.translate((u0+u1)/2,(y0+y1)/2,(w0+w1)/2);put(b,g,f,mat,crease);
}
// Flat plate with explicit UVs: local (u,y) outline at depth w; uv = ((u-uo)/uw,(y-yo)/uh).
function plate(b,f,mat,pts,holes,w,uo=0,yo=0,uw=1,uh=1){
  const s=new THREE.Shape(V2(pts));for(const h of holes||[])s.holes.push(new THREE.Path(V2(h)));
  const g=new THREE.ShapeGeometry(s,1);g.translate(0,0,w);
  const uv=g.attributes.uv,p=g.attributes.position;for(let i=0;i<p.count;i++)uv.setXY(i,(p.getX(i)-uo)/uw,(p.getY(i)-yo)/uh);
  xf(g,f);g.computeVertexNormals();b.unique(g,mat);
}
// Windows cut through a slab: list of [u,y0,w,ys,rise]; adds the frame, the recessed pane and a stone sill. Returns the hole outlines.
function windows(list){return list.map(([u,y0,w,ys,rise])=>archPts(u,y0,w,ys,rise));}
function windowTrim(b,f,list,{mat='gnLime',pane='gnGlassDark',depth=.4,grille=true}={}){
  for(const [u,y0,w,ys,rise] of list){
    archBand(b,f,mat,u,y0,w,ys,rise,.07,0,.05);plate(b,f,pane,archPts(u,y0,w,ys,rise),null,-depth,0,0,1,1);
    lbox(b,f,'gnStone',u-w/2-.1,y0-.08,0,u+w/2+.1,y0,.14);
    if(grille)for(let k=-1;k<=1;k++)lbox(b,f,'gnIron',u+k*w*.28-.012,y0+.05,-.05,u+k*w*.28+.012,ys+rise*.6,-.02);
  }
}
// Foliage card: rectangle (u0..u1, y0..y1) at depth w, UVs mapped to the atlas window uvr = [ua,va,ub,vb].
function card(b,f,mat,u0,y0,u1,y1,w,uvr){
  const g=new THREE.PlaneGeometry(u1-u0,y1-y0);g.translate((u0+u1)/2,(y0+y1)/2,w);
  const uv=g.attributes.uv;for(let i=0;i<uv.count;i++)uv.setXY(i,uvr[0]+uv.getX(i)*(uvr[2]-uvr[0]),uvr[1]+uv.getY(i)*(uvr[3]-uvr[1]));
  xf(g,f);b.unique(g,mat);
}
const CLIMB={bougain:[0,.5,.5,1],ivy:[.5,.5,1,1],jasmine:[0,0,.5,.5],rose:[.5,0,1,.5]};
// Band following an arch outline: outer = arch grown by fw, inner = the arch itself.
function archBand(b,f,mat,cu,yb,w,ys,rise,fw,w0,w1,opt){
  const o=archPts(cu,yb,w+2*fw,ys,rise+fw*1.1,opt),i=archPts(cu,yb,w,ys,rise,opt);
  prism(b,f,mat,o.concat(i.slice().reverse()),w0,w1,[],.9);
}
// Ribbed strips: radial ribs of a voussoir band. `outer`/`inner` are matching (u,y) polylines; ribs `pitch` m apart.
function ribFace(b,f,mat,outer,inner,w,pitch=.06){
  if(LOW)pitch*=1.6;
  const pos=[],nor=[],uv=[];let su=0;
  for(let i=0;i<inner.length-1;i++){
    const a0=inner[i],a1=inner[i+1],b0=outer[i],b1=outer[i+1],L=Math.hypot(a1[0]-a0[0],a1[1]-a0[1]),u0=su/pitch,u1=(su+L)/pitch;su+=L;
    const Q=[[a0,u0,0],[a1,u1,0],[b1,u1,1],[b0,u0,1]];
    for(const k of [0,1,2,0,2,3]){pos.push(Q[k][0][0],Q[k][0][1],w);nor.push(0,0,1);uv.push(Q[k][1],Q[k][2]);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  xf(g,f);b.unique(g,mat);
}
// Soffit of an arch: the surface of the opening between depths w0 and w1 (normals pointing into the opening).
function ribSoffit(b,f,mat,inner,w0,w1,pitch=.06,open=[0,0]){
  if(LOW)pitch*=1.6;
  const pos=[],nor=[],uv=[];let su=0;const cx=open[0],cy=open[1];
  for(let i=0;i<inner.length-1;i++){
    const a0=inner[i],a1=inner[i+1],L=Math.hypot(a1[0]-a0[0],a1[1]-a0[1]),u0=su/pitch,u1=(su+L)/pitch;su+=L;
    const n0=new THREE.Vector3(cx-a0[0],cy-a0[1],0).normalize(),n1=new THREE.Vector3(cx-a1[0],cy-a1[1],0).normalize();
    const Q=[[a0,w0,u0,0,n0],[a1,w0,u1,0,n1],[a1,w1,u1,1,n1],[a0,w1,u0,1,n0]];
    for(const k of [0,1,2,0,2,3]){const q=Q[k];pos.push(q[0][0],q[0][1],q[1]);nor.push(q[4].x,q[4].y,0);uv.push(q[2],q[3]);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  xf(g,f);b.unique(g,mat);
}
// Lathe column with base, tapered shaft, astragal and flared capital (Nasrid proportions).
function columnGeo(h=2.4,r=.1){
  const k=r/.1,pr=[[0,0],[.17,0],[.17,.05],[.145,.07],[.145,.12],[.118,.14],[.118,.15],[.108,.2],[.098,h-.50],[.098,h-.42],[.112,h-.40],[.112,h-.37],[.094,h-.35],[.098,h-.30],[.135,h-.24],[.165,h-.16],[.18,h-.08],[.17,h-.06],[.17,h-.02],[0,h-.02]];
  return new THREE.LatheGeometry(pr.map(p=>new THREE.Vector2(p[0]*k,p[1])),14);
}
// Corrugated clay-tile roof face. `pts` is a convex polygon (3 or 4 world points), pts[0]->pts[1] the eave. Ribs (rw wide) run
// down-slope and are clipped to the polygon so hips and gables stay tight. UV: u across ribs, v up the slope (metres).
function roofFace(b,mat,pts,{rw=.2,amp=.03,steps=6}={}){
  const P=pts.map(p=>new THREE.Vector3(...p)),a=P[1].clone().sub(P[0]).normalize();
  const cen=P.reduce((s,p)=>s.add(p),new THREE.Vector3()).multiplyScalar(1/P.length),rel=cen.clone().sub(P[0]);
  const s=rel.clone().sub(a.clone().multiplyScalar(rel.dot(a))).normalize();
  let nrm=new THREE.Vector3().crossVectors(a,s).normalize();if(nrm.y<0)nrm.negate();
  const q=P.map(p=>{const d=p.clone().sub(P[0]);return [d.dot(a),d.dot(s)];});
  const amin=Math.min(...q.map(v=>v[0])),amax=Math.max(...q.map(v=>v[0]));
  const range=x=>{let lo=1e9,hi=-1e9;for(let i=0;i<q.length;i++){const [x0,y0]=q[i],[x1,y1]=q[(i+1)%q.length];
    if((x0<=x&&x<=x1)||(x1<=x&&x<=x0)){if(Math.abs(x1-x0)<1e-6){lo=Math.min(lo,y0,y1);hi=Math.max(hi,y0,y1);}else{const t=(x-x0)/(x1-x0),y=y0+(y1-y0)*t;lo=Math.min(lo,y);hi=Math.max(hi,y);}}}return [lo,hi];};
  const pos=[],nor=[],uv=[],vert=(x,bb,h,dh)=>{const p=P[0].clone().addScaledVector(a,x).addScaledVector(s,bb).addScaledVector(nrm,h);return {p,n:nrm.clone().addScaledVector(a,-dh).normalize(),u:x-amin,v:bb};};
  const ribs=Math.ceil((amax-amin)/rw);
  for(let r=0;r<ribs;r++){
    const col=[];
    for(let j=0;j<=steps;j++){const x=Math.min(amax,Math.max(amin,amin+(r+j/steps)*rw)),t=j/steps,h=amp*Math.cos(2*PI*t),dh=-amp*2*PI*Math.sin(2*PI*t)/rw;
      const [lo,hi]=range(Math.min(amax-1e-4,Math.max(amin+1e-4,x)));if(lo>hi)continue;col.push({lo,hi,x,h,dh});}
    for(let j=0;j<col.length-1;j++){const c0=col[j],c1=col[j+1];
      const A=vert(c0.x,c0.lo,c0.h,c0.dh),B=vert(c1.x,c1.lo,c1.h,c1.dh),C=vert(c1.x,c1.hi,c1.h,c1.dh),D=vert(c0.x,c0.hi,c0.h,c0.dh);
      for(const t of [[A,B,C],[A,C,D]]){
        const n=new THREE.Vector3().crossVectors(t[1].p.clone().sub(t[0].p),t[2].p.clone().sub(t[0].p)),order=n.dot(nrm)<0?[0,2,1]:[0,1,2];
        for(const k of order){const v=t[k];pos.push(v.p.x,v.p.y,v.p.z);nor.push(v.n.x,v.n.y,v.n.z);uv.push(v.u,v.v);}}
    }
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  b.unique(g,mat);return {a,s,nrm};
}
// Hipped roof over a rectangle (cx,cz) rotated by th; W along local u, D along w; eave height y; ridge along the longer side.
function hipRoof(b,mat,cx,cz,th,W,D,y,pitch=.34,opt){
  const ux=Math.cos(th),uz=-Math.sin(th),nx=Math.sin(th),nz=Math.cos(th);
  const P=(u,w,yy=y)=>[cx+ux*u+nx*w,yy,cz+uz*u+nz*w];
  const half=Math.min(W,D)/2,h=half*pitch,alongU=W>=D;
  const r0=alongU?[-(W/2-half),0]:[0,-(D/2-half)],r1=alongU?[W/2-half,0]:[0,D/2-half];
  const R0=P(r0[0],r0[1],y+h),R1=P(r1[0],r1[1],y+h);
  roofFace(b,mat,[P(-W/2,D/2),P(W/2,D/2),R1,R0],opt);roofFace(b,mat,[P(W/2,-D/2),P(-W/2,-D/2),R0,R1],opt);
  roofFace(b,mat,[P(W/2,D/2),P(W/2,-D/2),R1],opt);roofFace(b,mat,[P(-W/2,-D/2),P(-W/2,D/2),R0],opt);
  if(W!==D)b.line(R0,R1,.15,'gnRidge');
  for(const [c,r] of [[[-W/2,D/2],R0],[[W/2,D/2],R1],[[W/2,-D/2],R1],[[-W/2,-D/2],R0]])b.line(P(c[0],c[1]),r,.1,'gnRidge');
  return {R0,R1,h};
}
// Gabled roof, ridge along u; the gable ends are left to the walls.
function gableRoof(b,mat,cx,cz,th,W,D,y,pitch=.34,opt){
  const ux=Math.cos(th),uz=-Math.sin(th),nx=Math.sin(th),nz=Math.cos(th);
  const P=(u,w,yy=y)=>[cx+ux*u+nx*w,yy,cz+uz*u+nz*w],h=D/2*pitch;
  roofFace(b,mat,[P(-W/2,D/2),P(W/2,D/2),P(W/2,0,y+h),P(-W/2,0,y+h)],opt);
  roofFace(b,mat,[P(W/2,-D/2),P(-W/2,-D/2),P(-W/2,0,y+h),P(W/2,0,y+h)],opt);
  b.line(P(-W/2,0,y+h),P(W/2,0,y+h),.15,'gnRidge');return {h};
}
// Single pitched roof rising away from the front (w>0) edge: eave at w=D/2 height y, upper edge at w=-D/2 height y+rise.
function shedRoof(b,mat,cx,cz,th,W,D,y,rise,opt){
  const ux=Math.cos(th),uz=-Math.sin(th),nx=Math.sin(th),nz=Math.cos(th);
  const P=(u,w,yy)=>[cx+ux*u+nx*w,yy,cz+uz*u+nz*w];
  roofFace(b,mat,[P(-W/2,D/2,y),P(W/2,D/2,y),P(W/2,-D/2,y+rise),P(-W/2,-D/2,y+rise)],opt);
  b.line(P(-W/2,-D/2,y+rise),P(W/2,-D/2,y+rise),.15,'gnRidge');
}
// Timber eave: rafter ends along a straight run (u0->u1 in local frame f at height y, projecting `ov` outward).
function eave(b,f,u0,u1,y,ov,{mat='gnTimberDark',pitch=.36,step=.5}={}){
  const len=u1-u0,n=Math.max(2,Math.round(len/step)),ca=Math.cos(f.yaw),sa=Math.sin(f.yaw);
  for(let i=0;i<=n;i++){const u=u0+len*i/n,x=f.x+u*ca+ov/2*sa,z=f.z-u*sa+ov/2*ca;b.box(x,f.y+y-.09,z,.07,.09,ov,mat,f.yaw);}
  const cx=f.x+(u0+u1)/2*ca+ov*sa,cz=f.z-(u0+u1)/2*sa+ov*ca;b.box(cx,f.y+y-.04,cz,len+.1,.14,.07,mat,f.yaw);
}
let LOW=false;
// Clipped hedge: a rounded-section run along a polyline of (x,z) points, base at height y, gently wobbling.
function hedgeRun(b,pts,y,h,w,mat='gnHedge',seed=1,segLen=.7){
  const r=random(seed),prof=[[-1,0],[-1,.62],[-.88,.88],[-.55,1],[.55,1],[.88,.88],[1,.62],[1,0]];
  const rows=[];let acc=0;
  for(let i=0;i<pts.length-1;i++){
    const [x0,z0]=pts[i],[x1,z1]=pts[i+1],L=Math.hypot(x1-x0,z1-z0),nx=-(z1-z0)/L,nz=(x1-x0)/L,n=Math.max(1,Math.round(L/segLen));
    for(let k=(i?1:0);k<=n;k++){const t=k/n,cx=x0+(x1-x0)*t,cz=z0+(z1-z0)*t;
      rows.push({cx,cz,nx,nz,s:acc+L*t,wob:1+(r()-.5)*.1*Math.min(1,.7/Math.max(.5,h)*1.0+.3),hob:1+(r()-.5)*.12*Math.min(1,.8/h)});}
    acc+=L;
  }
  const pos=[],uv=[];
  for(let i=0;i<rows.length-1;i++){
    const A=rows[i],B=rows[i+1];
    for(let j=0;j<prof.length-1;j++){
      const v=(row,k)=>{const [pu,ph]=prof[k];return [row.cx+row.nx*pu*w/2*row.wob,y+ph*h*row.hob,row.cz+row.nz*pu*w/2*row.wob];};
      const p0=v(A,j),p1=v(A,j+1),p2=v(B,j+1),p3=v(B,j),u0=A.s,u1=B.s,v0=j*.35,v1=(j+1)*.35;
      pos.push(...p0,...p2,...p3,...p0,...p1,...p2);uv.push(u0,v0,u1,v1,u1,v0,u0,v0,u0,v1,u1,v1);
    }
  }
  const e=rows[0],q=rows[rows.length-1];
  for(const [row,sg] of [[e,-1],[q,1]]){ // end caps (fan over the profile)
    const c=[row.cx,y+h*.5,row.cz];
    for(let j=0;j<prof.length-1;j++){const v=k=>{const [pu,ph]=prof[k];return [row.cx+row.nx*pu*w/2,y+ph*h,row.cz+row.nz*pu*w/2];};
      const a=v(j),b2=v(j+1);if(sg>0)pos.push(...c,...a,...b2);else pos.push(...c,...b2,...a);uv.push(0,0,.3,0,.3,.3);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.computeVertexNormals();
  const ng=toCreasedNormals(g.toNonIndexed?g:g,.9);
  b.unique(ng,mat);
}
// Crossed-card flowering clump, base at y = 0, size 1; cell (0..8) selects the sprite in the atlas.
function clumpGeo(b,cell){
  return b.geometry('gn-clump-'+cell,()=>{
    const col=cell%3,row=Math.floor(cell/3),u0=col/3,v0=1-(row+1)/3,u1=u0+1/3,v1=v0+1/3,pos=[],nor=[],uv=[];
    for(let k=0;k<3;k++){const a=k*PI/3,cx=Math.cos(a)*.5,cz=Math.sin(a)*.5;
      const P=[[-cx,0,-cz],[cx,0,cz],[cx,1,cz],[-cx,1,-cz]],U=[[u0,v0],[u1,v0],[u1,v1],[u0,v1]];
      for(const i of [0,1,2,0,2,3]){pos.push(...P[i]);const nx=-Math.sin(a)*.3,nz=Math.cos(a)*.3;nor.push(nx,.95,nz);uv.push(...U[i]);}}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(nor,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));return g;});
}
// Scatter flowering clumps over a rectangle (world x/z), jittered grid, bed centre taller.
function bed(b,x0,z0,x1,z1,y,{seed=1,step=.55,cells=[0,1,2,3,4,5,7,8],hmin=.45,hmax=1.0,skip=null}={}){
  const r=random(seed);if(LOW)step*=1.55;
  for(let x=x0+step/2;x<x1;x+=step)for(let z=z0+step/2;z<z1;z+=step){
    const px=x+(r()-.5)*step*.9,pz=z+(r()-.5)*step*.9;if(skip&&skip(px,pz))continue;
    const cell=cells[Math.floor(r()*cells.length)],h=hmin+r()*(hmax-hmin),w=h*(.85+r()*.6);
    b.add(clumpGeo(b,cell),'gnPlant',[px,y-.02,pz],[w*1.1,h,w*1.1],r()*PI);
  }
}
// Clipped ball (box / myrtle topiary) standing in a terracotta pot.
function topiary(b,x,y,z,r=.28,pot=true){
  const g=b.geometry('gn-ball',()=>new THREE.IcosahedronGeometry(1,2));
  b.add(g,'gnHedge',[x,y+(pot?.4:0)+r*.92,z],[r,r*.95,r],x*7.1+z*3.3);
  if(pot){b.cylinder(x,y,z,.2,.42,'gnTerra',.26,12);b.cylinder(x,y+.42,z,.26,.05,'gnTerra',.26,12);b.cylinder(x,y+.4,z,.24,.05,'gnSoil',.24,10);}
}

// ---------------------------------------------------------------------------------------------------------
// shared constants of the Patio de la Acequia (local lx east, lz south)
const PW=6.7,PL=24.4,CAN=.72,COP=.40,COPH=.20;
const wx=lx=>X0+lx,wz=lz=>Z0+lz,wy=ly=>Y0+ly;
function jetArc(b,x0,y0,z0,x1,y1,z1,apex,r=.011){
  const N=LOW?12:28;const pts=[];for(let i=0;i<=N;i++){const t=i/N;pts.push(new THREE.Vector3(x0+(x1-x0)*t,y0+(y1-y0)*t+4*apex*t*(1-t),z0+(z1-z0)*t));}
  const g=new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),N,r,4,false);b.unique(g,'gnJet');
}
function nav(b,x,z,w,d,y0,y1,rot=0){b.nav.box(x,z,w,d,y0,y1,rot);}

// Canal, paths, hedges, beds and jets of the Patio de la Acequia.
function patioGround(b,water){
  const r=random(7);
  b.zone='gnCourt';
  // base earth of the whole court and the walkable surface (the old model's level)
  b.nav.floor(X0,Z0,2*PW+.2,2*PL+.2,Y0);b.nav.floor(X0,Z0,30,66,Y0);
  b.box(X0,Y0-.4,Z0,2*PW+.2,.4,2*PL+.2,'gnSoil');
  // canal: coping stones, sloped dark tile inner faces and bottom
  const cl=PL-4.2;
  for(const s of [-1,1]){
    b.box(X0+s*(CAN+COP/2),Y0,Z0,COP,COPH,2*cl,'gnCoping');
    b.box(X0+s*(CAN+.01),Y0-.1,Z0,.05,COPH,2*cl,'gnStone');
  }
  b.box(X0,Y0-.1,Z0,2*CAN,.1,2*cl,'gnBasin');
  for(const z of [-cl-.2,cl+.2])b.box(X0,Y0-.1,Z0+z,2*(CAN+COP),COPH+.1,.4,'gnCoping');
  water.push({x:X0,z:Z0,w:2*CAN,d:2*cl,y:Y0+.12,reflect:true});
  nav(b,X0,Z0-(cl+.55)/2-.4,2*(CAN+COP),cl-.55,Y0-1,Y0+COPH+.3);
  nav(b,X0,Z0+(cl+.55)/2+.4,2*(CAN+COP),cl-.55,Y0-1,Y0+COPH+.3);
  // central stone slab bridge (walkable) joining the two paths
  b.box(X0,Y0+.1,Z0,2*(CAN+COP)+.5,.1,1.5,'gnCoping');b.nav.floor(X0,Z0,2*(CAN+COP)+.5,1.5,Y0+.2);
  // paved paths beside the canal and along both buildings
  const pathY=.02;
  for(const s of [-1,1]){
    b.box(X0+s*(CAN+COP+.75),Y0,Z0,1.5,pathY,2*cl,'gnPaver');
    b.box(X0+s*5.95,Y0,Z0,1.5,pathY,2*(PL-3.2),'gnPaver');
  }
  // end courts (terracotta) with the shell fountains
  for(const s of [-1,1]){
    b.box(X0,Y0,Z0+s*(PL-2.1),2*PW,.03,4.2,'gnTerra');
    if(s<0){const zf=Z0+s*(cl+1.3);
      b.cylinder(X0,Y0+.01,zf,.95,.2,'gnCoping',.7,24);b.cylinder(X0,Y0+.2,zf,.62,.05,'gnBasin',.62,20);
      b.cylinder(X0,Y0+.02,zf,.12,.62,'gnCoping',.07,10);b.cylinder(X0,Y0+.6,zf,.35,.05,'gnCoping',.4,16);
      b.nav.box(X0,zf,1.9,1.9,Y0,Y0+.7);}
  }
  // hedges: clipped boxwood along each path (blocked, open at both ends)
  for(const s of [-1,1]){
    const x=s*(CAN+COP+1.5+.33),zs=cl-.7;
    hedgeRun(b,[[wx(x),wz(-zs)],[wx(x),wz(zs)]],Y0,.56,.66,'gnHedge',50+s,.6);
    nav(b,wx(x),Z0,.66,2*zs,Y0,Y0+.6);
  }
  // flowering beds, orange/laurel trees and topiary in pots
  for(const s of [-1,1]){
    const xa=s>0?3.3:-5.4,xb=s>0?5.4:-3.3;
    bed(b,wx(xa),wz(-cl),wx(xb),wz(cl),Y0,{seed:30+s,step:.5,hmin:.5,hmax:1.15});
    for(const z of [-17,-11,-4,5,12,18])bed(b,wx(s>0?3.4:-5.3),wz(z)-.4,wx(s>0?3.9:-3.8),wz(z)+.4,Y0,{seed:70+z,step:.45,cells:[3,6],hmin:1.1,hmax:1.9});
    for(const z of [-23.0,23.0])for(const k of [-1,1])topiary(b,wx(s*(2.4+k*.9)),Y0+.03,wz(z),.3);
  }
  plant(wx(-4.3),Y0,wz(-14.5),ORANGE,3.2);plant(wx(4.1),Y0,wz(-9),ORANGE,3.0);plant(wx(-4.4),Y0,wz(9),ORANGE,3.1);plant(wx(4.1),Y0,wz(8),ORANGE,3.3);
  plant(wx(-4.1),Y0,wz(-19.2),SHRUB,2.8);plant(wx(4.1),Y0,wz(-19.4),SHRUB,2.8);plant(wx(-4.2),Y0,wz(17.5),SHRUB,2.4);
  // jets: thin arching streams across the canal, staggered from both coping edges
  for(let i=0;i<22;i++){
    const z=-cl+1.2+i*(2*cl-2.4)/21;
    for(const s of [-1,1]){const zz=z+(s>0?0:.95);if(Math.abs(zz)<1.0||zz>cl-.3)continue;
      jetArc(b,wx(s*(CAN+.15)),Y0+COPH+.03,wz(zz),wx(-s*.45),Y0+.12,wz(zz+(r()-.5)*.4),.9+r()*.35);}
  }
}

// Western gallery: 18 pointed arches with peach alfiz frames, white piers, a terracotta floor and a tiled gable roof.
function westGallery(b){
  b.zone='gnCourt';
  const fx=X0-PW,f=F(fx,Z0,PI/2,Y0),H=4.15,T=.75,N=18,pitch=2*PL/N,AW=1.6,YS=2.35,RISE=1.0;
  const holes=[],cen=[];
  for(let i=0;i<N;i++){const u=-PL+(i+.5)*pitch;cen.push(u);holes.push(archPts(u,0,AW,YS,RISE,{hs:.3}));}
  slab(b,f,'gnLime',{u0:-PL,u1:PL,y0:-.3,y1:H,t:T,holes});
  for(const u of cen){
    const o={hs:.3};
    archBand(b,f,'gnPink',u,.95,AW+.1,YS,RISE+.04,.18,0,.06,o);
    ribFace(b,f,'gnRibPink',archPts(u,0,AW+.2,YS,RISE+.1,o),archPts(u,0,AW,YS,RISE,o),.068,.05);
    ribSoffit(b,f,'gnRibPink',archPts(u,0,AW,YS,RISE,o),-T,.068,.06,[u,1.8]);
  }
  // plinths on the piers and a moulded cornice
  for(let i=1;i<N;i++){const u=-PL+i*pitch;lbox(b,f,'gnLimeDirty',u-.58,0,0,u+.58,.5,.04);}
  lbox(b,f,'gnLimeWarm',-PL,H-.22,0,PL,H,.12);lbox(b,f,'gnLimeWarm',-PL,H-.34,0,PL,H-.22,.06);
  eave(b,f,-PL,PL,H,.5);
  // west wall with the window arches looking over the Alhambra, floor, ceiling
  const bx=fx-T-3.0,fb=F(bx-.6,Z0,-PI/2,Y0),wh=[];
  for(let i=0;i<N;i++)wh.push(archPts(cen[i]*-1,.95,1.05,2.0,.8,{hs:.18}));
  slab(b,fb,'gnLime',{u0:-PL,u1:PL,y0:-.3,y1:H,t:.6,holes:wh});
  for(let i=0;i<N;i++){const u=-cen[i];archBand(b,fb,'gnPink',u,.95,1.05,2.0,.8,.18,0,.06,{hs:.18});archBand(b,fb,'gnPink',u,.95,1.05-.1,2.0,.8-.06,.05,-.6,0,{hs:.18});
    lbox(b,fb,'gnStone',u-.6,.88,-.1,u+.6,.96,.12);}
  lbox(b,fb,'gnLimeWarm',-PL,H-.22,0,PL,H,.12);
  b.box(bx+1.5,Y0+.0,Z0,3.0,.03,2*PL,'gnTerra');b.nav.floor(bx+1.5,Z0,3.0+.8,2*PL,Y0);
  b.box(bx+1.5,Y0+H-.2,Z0,3.0,.14,2*PL,'gnTimber');
  b.box(bx+1.5,Y0+H-.1,Z0,3.1,.05,2*PL,'gnTimberDark');
  for(let k=0;k<=48;k++)b.box(bx+1.5,Y0+H-.3,Z0-PL+k*(2*PL/48),3.0,.12,.12,'gnTimberDark');
  // piers block the way, arches stay open
  for(let i=1;i<N;i++){const u=-PL+i*pitch;nav(b,fx-T/2,Z0-u,T,pitch-AW,Y0,Y0+H);}
  nav(b,bx-.3,Z0,.6,2*PL,Y0,Y0+H);
  gableRoof(b,'gnRoof',X0-8.9,Z0,PI/2,2*PL+.5,5.1,Y0+H-.02,.34);
}

// East wing (north part of the east side): two storeys of pale brick with tall double doors, arched windows, rose trellises.
function eastWing(b){
  b.zone='gnCourt';
  const f=F(X0+PW,Z0,-PI/2,Y0),u0=-PL,u1=5.6,H=6.3,T=.9;
  const doors=[-19.2,-12.6,-6.0,.6],mid=[-15.9,-9.3,-2.7],holes=[];
  for(const u of doors)holes.push(rectPts(u-1.05,0,u+1.05,3.15));
  for(const u of mid)holes.push(archPts(u,.8,.62,1.7,.62));
  const upper=[];for(let i=0;i<7;i++){const u=-19.2+i*3.3;upper.push(u);holes.push(archPts(u,4.2,.66,4.9,.6));}
  slab(b,f,'gnBrickPale',{u0,u1,y0:-.3,y1:H,t:T,holes});
  for(const u of doors){
    if(u===-19.2){ // open passage through the wing to the Court of the Sultana's Cypress, door leaves swung back
      const hx=X0+PW+.45;
      plate(b,F(hx,Z0+u-1.0+.04,0,Y0),'gnDoor',rectPts(0,0,1.0,3.1),null,0,0,0,2.0,3.1);
      plate(b,F(hx,Z0+u+1.0-.04,PI,Y0),'gnDoor',rectPts(-1.0,0,0,3.1),null,0,-1.0,0,2.0,3.1);
      lbox(b,f,'gnTimberDark',u-1.2,3.15,-.12,u+1.2,3.38,.08);
      continue;
    }
    plate(b,f,'gnDoor',rectPts(u-1.0,0,u+1.0,3.1),null,-.45,u-1.0,0,2.0,3.1);
    lbox(b,f,'gnTimberDark',u-1.2,3.15,-.12,u+1.2,3.38,.08);lbox(b,f,'gnStone',u-1.18,0,.0,u+1.18,.06,.38);
    lbox(b,f,'gnBrickRed',u-1.18,3.38,-.05,u+1.18,3.46,.06);
  }
  for(const u of mid){archBand(b,f,'gnLimeWarm',u,.8,.62,1.7,.62,.1,0,.05);plate(b,f,'gnGlassDark',archPts(u,.8,.62,1.7,.62),null,-.5,0,0,1,1);}
  for(const u of upper){archBand(b,f,'gnLimeWarm',u,4.2,.66,4.9,.6,.1,0,.05);plate(b,f,'gnGlassDark',archPts(u,4.2,.66,4.9,.6),null,-.5,0,0,1,1);lbox(b,f,'gnStone',u-.5,4.12,0,u+.5,4.2,.14);}
  lbox(b,f,'gnLimeWarm',u0,3.62,0,u1,3.82,.1);
  lbox(b,f,'gnLimeWarm',u0,H-.2,0,u1,H,.1);lbox(b,f,'gnLimeDirty',u0,0,0,u1,.35,.04);
  eave(b,f,u0,u1,H,.55);
  // back (east) wall
  const fb=F(X0+PW+6.6,Z0,PI/2,Y0);
  {const wl=[-3,-2,-1,0,1,2,3].map(k=>[19.2+3.2*k,5.0,1.1,5.65,.5]);
    slab(b,fb,'gnOcher',{u0:-u1,u1:34,y0:-.3,y1:H,t:.6,holes:[archPts(19.2,0,2.1,2.3,.9),...windows(wl)]});windowTrim(b,fb,wl,{mat:'gnLimeWarm',pane:'gnTimberDark'});}
  archBand(b,fb,'gnLimeWarm',19.2,0,2.1,2.3,.9,.18,0,.06);
  gableRoof(b,'gnRoofOld',X0+PW+3.4,Z0+(-34+u1)/2,PI/2,(u1+34)+.6,7.4,Y0+H-.02,.3);
  {const za=Z0-19.2-1.2,zb=Z0-19.2+1.2,zn=Z0+u0,zs=Z0+u1;
    nav(b,X0+PW+3.3,(zn+za)/2,6.6,za-zn,Y0,Y0+H);nav(b,X0+PW+3.3,(zb+zs)/2,6.6,zs-zb,Y0,Y0+H);
    for(const sz of [-1,1]){b.box(X0+PW+3.3,Y0,Z0-19.2+sz*1.2,6.6,3.4,.18,'gnLimeWarm');}
    b.box(X0+PW+3.3,Y0,Z0-19.2,6.6,.04,2.2,'gnTerra');b.box(X0+PW+3.3,Y0+3.35,Z0-19.2,6.6,.14,2.4,'gnTimber');b.nav.floor(X0+PW+3.3,Z0-19.2,6.8,2.4,Y0);}
  for(const [zz,yaw] of [[Z0-34,PI],[Z0+u1,0]]){const g=F(X0+PW+3.3,zz,yaw,Y0);prism(b,g,'gnBrickPale',[[-3.3,H],[3.3,H],[0,H+1.0]],-.6,0);}
  slab(b,F(X0+PW+3.3,Z0+u1,0,Y0),'gnBrickPale',{u0:-3.3,u1:3.3,y0:-.3,y1:H,t:.7,holes:[archPts(-1.5,4.3,.66,5.0,.6),archPts(1.5,4.3,.66,5.0,.6)]});
  // rose trellises with climbers between the doors (soft clusters of blossom on a slim wooden lattice)
  for(const u of [-16.0,-9.4,-2.8,3.9]){
    const fz=F(X0+PW-.1,Z0+u,-PI/2,Y0);
    lbox(b,fz,'gnTrellis',-.5,.15,-.02,.5,3.3,.03);for(let k=0;k<=4;k++)lbox(b,fz,'gnTrellis',-.5,.2+k*.8,-.03,.5,.26+k*.8,.04);
    bloom(b,X0+PW-.4,Y0+2.0,Z0+u,.28,1.5,.55,LOW?9:16,CLIMB.rose,Math.round(u*10),.95);
    bloom(b,X0+PW-.35,Y0+1.2,Z0+u,.25,1.2,.5,LOW?5:9,CLIMB.ivy,Math.round(u*10)+7,.8);
  }
}
// ---------------------------------------------------------------------------------------------------------
// North pavilion (Sala Regia with the Mirador de Ismail): five-arch portico, tiled pent roof, white upper storey with
// windows, the three-bay timber loggia under a hipped roof and the taller tower to the west.
function northPavilion(b){
  b.zone='gnCourt';
  const f=F(X0,Z0-PL,0,Y0);
  // arches: outer 1.8, mid 2.3, centre 3.5 wide, all springing at 3.0
  const arches=[[-5.67,1.8,1.0],[-3.26,2.3,1.25],[0,3.5,1.6],[3.26,2.3,1.25],[5.67,1.8,1.0]];
  const holes=arches.map(([u,w,r])=>archPts(u,0,w,3.0,r,{hs:.12}));
  slab(b,f,'gnStucco',{u0:-PW,u1:PW,y0:-.3,y1:5.55,t:.55,holes});
  for(const [u,w,r] of arches){
    const o={hs:.12},inner=archPts(u,0,w,3.0,r,o);
    archBand(b,f,'gnGold',u,0,w+.04,3.0,r+.02,.34,0,.06,o);
    ribFace(b,f,'gnRib',archPts(u,0,w+.5,3.0,r+.25,o),archPts(u,0,w,3.0,r,o),.075);
    ribSoffit(b,f,'gnRib',inner,-.55,.075,.06,[u,2.2]);
  }
  // impost blocks and paired marble columns at the four supports
  const col=b.geometry('gn-col',()=>columnGeo(2.7,.1));
  for(const u of [-4.59,-1.93,1.93,4.59]){
    for(const du of [-.1,.1])b.add(col,'gnMarble',[X0+u+du,Y0,Z0-PL+.14]);
    lbox(b,f,'gnGold',u-.27,2.72,-.12,u+.27,3.15,.28);lbox(b,f,'gnGold',u-.2,2.5,-.06,u+.2,2.72,.2);
    lbox(b,f,'gnGold',u-.22,3.15,-.08,u+.22,3.6,.12);
    nav(b,X0+u,Z0-PL+.1,.5,.45,Y0,Y0+4);
  }
  lbox(b,f,'gnStucco',-PW,5.0,0,PW,5.55,.07);plate(b,f,'gnFrieze',rectPts(-PW,5.02,PW,5.53),null,.075,-PW,5.02,1.31,.55);
  eave(b,f,-PW,PW,5.6,.85);lbox(b,f,'gnTimberDark',-PW-.15,5.55,-.1,PW+.15,5.85,.5);
  // portico interior: floor, ceiling, back wall with the door to the Sala Regia and flanking wood doors
  const dpt=4.2,fb=F(X0,Z0-PL-dpt,0,Y0);
  b.box(X0,Y0,Z0-PL-dpt/2,2*PW,.04,dpt,'gnTerra');b.nav.floor(X0,Z0-PL-dpt/2,2*PW,dpt,Y0);
  b.box(X0,Y0+5.3,Z0-PL-dpt/2,2*PW,.2,dpt,'gnTimber');
  for(let k=0;k<=14;k++)b.box(X0,Y0+5.15,Z0-PL-.1-k*dpt/14,2*PW,.16,.14,'gnTimberDark');
  slab(b,fb,'gnLimeWarm',{u0:-PW,u1:PW,y0:-.3,y1:5.8,t:.6,holes:[archPts(0,0,2.2,2.3,.95),...[-1.2,0,1.2].map(u=>archPts(u*1.3,3.6,.7,4.1,.5))]});
  for(const s of [-1,1]){
    const u=s*3.25;
    plate(b,fb,'gnDoor',rectPts(u-1.1,0,u+1.1,3.0),null,.01,u-1.1,0,2.2,3.0);
    lbox(b,fb,'gnStucco',u-1.25,3.0,0,u+1.25,3.9,.04);lbox(b,fb,'gnGold',u-1.25,3.85,0,u+1.25,3.98,.07);
    archBand(b,fb,'gnGold',u,3.95,1.0,4.3,.35,.1,0,.05);
    plate(b,fb,'gnStucco',archPts(u,3.95,1.0,4.3,.35),null,.02,u-.6,3.95,1.2,1.2);
  }
  archBand(b,fb,'gnGold',0,0,2.2,2.3,.95,.25,0,.07);
  // Sala Regia behind the central arch: a small chamber with carved walls, a tile dado, a tile floor and a cedar ceiling
  {const rw=4.6,rd=4.2,zc=Z0-PL-dpt-rd/2;
    b.box(X0,Y0,zc,rw,.04,rd+.2,'gnTerra');b.nav.floor(X0,zc,rw,rd,Y0);
    b.box(X0,Y0+4.9,zc,rw+.4,.2,rd+.4,'gnTimber');
    slab(b,F(X0,Z0-PL-dpt-rd,0,Y0),'gnStucco',{u0:-rw/2,u1:rw/2,y0:0,y1:4.9,t:.3},.5);lbox(b,F(X0,Z0-PL-dpt-rd,0,Y0),'cTile',-rw/2,0,.0,rw/2,1.25,.03);
    for(const sx of [-1,1]){slab(b,F(X0+sx*rw/2,zc,-sx*PI/2,Y0),'gnStucco',{u0:-rd/2,u1:rd/2,y0:0,y1:4.9,t:.3},.5);lbox(b,F(X0+sx*rw/2,zc,-sx*PI/2,Y0),'cTile',-rd/2,0,0,rd/2,1.25,.03);}}
  nav(b,X0,Z0-PL-dpt-.3,2*PW,.6,Y0,Y0+6);
  for(const s of [-1,1])nav(b,X0+s*(PW+.3),Z0-PL-dpt/2,.6,dpt,Y0,Y0+6);
  // flanking ground-floor walls (west: gallery end, east: wing end) and the shell of the whole ground floor
  for(const [x0,x1] of [[-11.1,-PW],[PW,13.2]]){
    const fw=F(X0+(x0+x1)/2,Z0-PL,0,Y0);
    slab(b,fw,x0<0?'gnLime':'gnBrickPale',{u0:-(x1-x0)/2,u1:(x1-x0)/2,y0:-.3,y1:x0<0?6.4:6.3,t:.7});
    nav(b,X0+(x0+x1)/2,Z0-PL-4.7,x1-x0,9.4,Y0,Y0+6);
  }
  {const wl=[...[-9,-5.2,-1.4,2.4,6.2,10].map(u=>[u,2.6,.6,3.4,.4]),...[-7.1,-3.3,.5,4.3,8.1].map(u=>[u,4.55,.5,5.2,.3])],fN=F(X0+1.05,Z0-PL-9.6,PI,Y0);
    slab(b,fN,'gnLimeWarm',{u0:-12.15,u1:12.15,y0:-.3,y1:6.4,t:.7,holes:windows(wl)});windowTrim(b,fN,wl);lbox(b,fN,'gnLimeDirty',-12.15,0,0,12.15,.5,.05);lbox(b,fN,'gnLimeWarm',-12.15,6.1,0,12.15,6.4,.14);}
  {const wl=[[-2.6,2.4,.55,3.2,.35],[0,1.0,.7,1.8,.55],[2.6,2.4,.55,3.2,.35],[-2.6,4.5,.5,5.1,.3],[2.6,4.5,.5,5.1,.3]],fW=F(X0-11.1,Z0-PL-4.8,-PI/2,Y0);slab(b,fW,'gnLime',{u0:-4.8,u1:4.8,y0:-.3,y1:6.4,t:.7,holes:windows(wl)});windowTrim(b,fW,wl);lbox(b,fW,'gnLimeWarm',-4.8,6.1,0,4.8,6.4,.14);}
  // lean-to roofs over the two flanking wings, from the front wall up to the upper storey
  shedRoof(b,'gnRoof',X0-8.9,Z0-PL-1.2,0,4.4+.8,2.4+.4,Y0+6.35,.8);
  // pent roof over the portico, rising to the upper wall
  shedRoof(b,'gnRoof',X0,Z0-PL-1.9,0,2*PW+1.4,5.0,Y0+5.85,1.6);
  // upper storey: white front wall with six arched windows and the three-bay loggia
  const zU=-PL-2.2,fu=F(X0,Z0+zU,0,Y0),uh=[];
  const cent=[-3.65,0,3.65];
  for(const c of cent)for(const d of [-.52,.52])uh.push(archPts(c+d,8.0,.62,8.65,.34));
  for(const c of cent)uh.push(rectPts(c-1.45,10.15,c+1.45,12.3));
  slab(b,fu,'gnLimeWarm',{u0:-10.8,u1:7.2,y0:6.2,y1:12.5,t:.8,holes:uh});
  for(const c of cent)for(const d of [-.52,.52]){const u=c+d;archBand(b,fu,'gnLime',u,8.0,.62,8.65,.34,.08,0,.05);plate(b,fu,'gnGlassDark',archPts(u,8.0,.62,8.65,.34),null,-.4,0,0,1,1);lbox(b,fu,'gnStone',u-.45,7.92,0,u+.45,8.0,.14);}
  lbox(b,fu,'gnLime',-10.8,9.55,0,7.2,9.8,.12);lbox(b,fu,'gnLime',-10.8,12.3,0,7.2,12.5,.1);
  for(const c of cent){
    lbox(b,fu,'gnTimberDark',c-1.5,12.15,-.1,c+1.5,12.4,.1);
    lbox(b,fu,'gnTimberDark',c-1.45,10.15,-.12,c+1.45,10.25,.14);lbox(b,fu,'gnTimberDark',c-1.45,11.15,-.12,c+1.45,11.24,.12);
    for(let k=0;k<=14;k++)lbox(b,fu,'gnTimberDark',c-1.42+k*.203-.02,10.25,-.1,c-1.42+k*.203+.02,11.15,-.06);
    lbox(b,fu,'gnLimeDirty',c-1.45,10.0,-2.2,c+1.45,12.3,-2.15);
  }
  b.box(X0-1.8,Y0+10.12,Z0+zU-1.1,10.5,.08,2.4,'gnTimber');
  b.box(X0-1.8,Y0+12.3,Z0+zU-1.1,10.5,.1,2.4,'gnTimber');
  // tower and its belfry
  const ft=F(X0,Z0+zU,0,Y0);
  slab(b,ft,'gnLimeWarm',{u0:-10.8,u1:-6.9,y0:12.4,y1:15.3,t:.8,holes:[archPts(-9.6,13.4,.5,14.0,.4),archPts(-8.3,13.4,.5,14.0,.4)]});
  for(const u of [-9.6,-8.3]){archBand(b,ft,'gnLime',u,13.4,.5,14.0,.4,.07,0,.05);plate(b,ft,'gnGlassDark',archPts(u,13.4,.5,14.0,.4),null,-.4,0,0,1,1);}
  lbox(b,ft,'gnLime',-10.8,15.1,0,-6.9,15.3,.1);
  // side and rear walls of the upper block, hipped roofs
  const cz=Z0+zU-3.6;
  {const wl=[-5.2,-1.6,2.0,5.6,9.0].map(u=>[u,8.2,.62,8.9,.34]),fU=F(X0,Z0+zU-7.2,Math.PI,Y0);
    slab(b,fU,'gnLimeWarm',{u0:-7.2,u1:10.8,y0:6.2,y1:12.5,t:.8,holes:windows(wl)});windowTrim(b,fU,wl);lbox(b,fU,'gnLime',-7.2,12.25,0,10.8,12.5,.1);}
  {const wl=[[-1.2,8.0,.62,8.65,.34],[1.2,8.0,.62,8.65,.34]],fE=F(X0+7.2,cz,PI/2,Y0);slab(b,fE,'gnLimeWarm',{u0:-3.6,u1:3.6,y0:6.2,y1:12.5,t:.8,holes:windows(wl)});windowTrim(b,fE,wl);}
  {const wl=[[0,8.0,.62,8.65,.34],[-1.1,10.6,.5,11.2,.3],[1.1,10.6,.5,11.2,.3],[0,13.1,.55,13.7,.3]],fT=F(X0-10.8,cz,-PI/2,Y0);slab(b,fT,'gnLimeWarm',{u0:-3.6,u1:3.6,y0:6.2,y1:15.3,t:.8,holes:windows(wl)});windowTrim(b,fT,wl);lbox(b,fT,'gnLime',-3.6,12.2,0,3.6,12.4,.12);lbox(b,fT,'gnLime',-3.6,15.1,0,3.6,15.3,.12);}
  hipRoof(b,'gnRoof',X0-1.8,cz,0,18.8,8.0,Y0+12.45,.3);
  hipRoof(b,'gnRoof',X0-8.85,cz,0,4.6,8.0,Y0+15.25,.3);
  nav(b,X0-1.8,cz,18,7.2,Y0+5,Y0+16);
}
// ---------------------------------------------------------------------------------------------------------
// South pavilion (entrance): a brick tower with a three-opening ground floor and a vestibule through which the way leads
// to the lower gardens, a timber-and-brick mirador under a hipped roof, and white wings.
function southPavilion(b){
  b.zone='gnCourt';
  const f=F(X0,Z0+PL,PI,Y0),D=8.0,H1=6.5;       // facing the patio (north); local u runs west
  const holes=[archPts(0,0,2.8,2.35,1.1,{hs:.1}),archPts(-2.75,.9,1.0,2.0,.5),archPts(2.75,.9,1.0,2.0,.5),archPts(0,4.4,1.0,5.15,.5)];
  slab(b,f,'gnBrickRed',{u0:-3.9,u1:3.9,y0:-.3,y1:H1,t:.9,holes});
  archBand(b,f,'gnLimeWarm',0,0,2.8,2.35,1.1,.28,0,.06,{hs:.1});
  for(const u of [-2.75,2.75]){archBand(b,f,'gnLimeWarm',u,.9,1.0,2.0,.5,.1,0,.05);plate(b,f,'gnGlassDark',archPts(u,.9,1.0,2.0,.5),null,-.5,0,0,1,1);lbox(b,f,'gnStone',u-.65,.82,0,u+.65,.9,.2);
    for(let k=-2;k<=2;k++)lbox(b,f,'gnIron',u+k*.2-.012,.95,.0,u+k*.2+.012,2.3,.04);}
  archBand(b,f,'gnLimeWarm',0,4.4,1.0,5.15,.5,.12,0,.05);plate(b,f,'gnGlassDark',archPts(0,4.4,1.0,5.15,.5),null,-.5,0,0,1,1);lbox(b,f,'gnStone',-.7,4.32,0,.7,4.4,.2);
  lbox(b,f,'gnLimeWarm',-3.9,3.55,0,3.9,3.75,.1);lbox(b,f,'gnLimeWarm',-3.9,H1-.3,0,3.9,H1+.28,.4);lbox(b,f,'gnLimeWarm',-4.05,H1-.05,-.2,4.05,H1+.3,.45);
  // side brick walls and the rear (south) face with its own arch
  for(const sx of [-1,1])slab(b,F(X0+sx*3.9,Z0+PL+D/2,sx*PI/2,Y0),'gnBrickRed',{u0:-D/2,u1:D/2,y0:-.3,y1:H1+.8,t:.6});
  slab(b,F(X0,Z0+PL+D,0,Y0),'gnBrickRed',{u0:-3.9,u1:3.9,y0:-.3,y1:H1+.8,t:.9,holes:[archPts(0,0,2.8,2.35,1.1,{hs:.1}),archPts(0,4.4,1.0,5.15,.5)]});
  archBand(b,F(X0,Z0+PL+D,0,Y0),'gnLimeWarm',0,0,2.8,2.35,1.1,.28,0,.06,{hs:.1});
  // vestibule: floor, timber ceiling, side walls
  b.box(X0,Y0,Z0+PL+D/2,4.0,.04,D,'gnTerra');b.nav.floor(X0,Z0+PL+D/2,4.4,D+.8,Y0);
  b.box(X0,Y0+3.62,Z0+PL+D/2,4.2,.16,D,'gnTimber');
  for(let k=0;k<=8;k++)b.box(X0,Y0+3.5,Z0+PL+k*D/8,4.2,.14,.14,'gnTimberDark');
  for(const sx of [-1,1]){b.box(X0+sx*2.05,Y0,Z0+PL+D/2,.2,3.6,D,'gnLimeWarm');b.box(X0+sx*1.93,Y0,Z0+PL+D/2,.04,1.2,D,'cTile');nav(b,X0+sx*2.9,Z0+PL+D/2,1.9,D,Y0,Y0+8);}
  // pent roof, then the mirador storey set back behind it
  shedRoof(b,'gnRoof',X0,Z0+PL+.9,PI,8.6,2.6,Y0+H1+.25,.8);
  const fm=F(X0,Z0+PL+2.4,PI,Y0),mh=[archPts(0,7.6,1.15,8.8,.58),archPts(-2.15,7.7,.7,8.5,.34),archPts(-2.95,7.7,.7,8.5,.34),archPts(2.15,7.7,.7,8.5,.34),archPts(2.95,7.7,.7,8.5,.34)];
  slab(b,fm,'gnLimeWarm',{u0:-3.9,u1:3.9,y0:7.0,y1:10.55,t:.6,holes:mh});
  for(const [u,w,y0,ys,r] of [[0,1.15,7.6,8.8,.58],[-2.15,.7,7.7,8.5,.34],[-2.95,.7,7.7,8.5,.34],[2.15,.7,7.7,8.5,.34],[2.95,.7,7.7,8.5,.34]]){archBand(b,fm,'gnLime',u,y0,w,ys,r,.09,0,.05);plate(b,fm,'gnGlassDark',archPts(u,y0,w,ys,r),null,-.4,0,0,1,1);lbox(b,fm,'gnStone',u-w/2-.15,y0-.08,0,u+w/2+.15,y0,.16);}
  for(const u of [-3.9,3.9,-1.4,1.4]){lbox(b,fm,'gnTimberDark',u-.17,7.0,-.05,u+.17,10.55,.25);}
  lbox(b,fm,'gnTimberDark',-4.05,10.3,-.1,4.05,10.6,.3);
  slab(b,F(X0,Z0+PL+D-1.6,0,Y0),'gnLimeWarm',{u0:-3.9,u1:3.9,y0:7.0,y1:10.55,t:.6,holes:[archPts(0,7.6,1.15,8.8,.58)]});
  for(const sx of [-1,1])slab(b,F(X0+sx*3.9,Z0+PL+4.8+1.6,sx*PI/2,Y0),'gnLimeWarm',{u0:-3.2,u1:3.2,y0:7.0,y1:10.55,t:.5,holes:[archPts(0,7.7,.7,8.5,.34)]});
  hipRoof(b,'gnRoof',X0,Z0+PL+5.2,0,9.0,8.2,Y0+10.5,.33);
  // white wings with small windows and hipped roofs
  for(const sx of [-1,1]){
    const x0=sx>0?3.9:-11.1,x1=sx>0?13.2:-3.9,fw=F(X0+(x0+x1)/2,Z0+PL,PI,Y0),wh=[];
    for(let k=0;k<2;k++)wh.push(rectPts(-2.1+k*4.2-.45+0,1.5,-2.1+k*4.2+.45,2.6));
    slab(b,fw,'gnLime',{u0:-(x1-x0)/2,u1:(x1-x0)/2,y0:-.3,y1:4.6,t:.7,holes:sx>0?[rectPts(-(x1-x0)/2+1.6,1.6,-(x1-x0)/2+2.5,2.7),rectPts(-(x1-x0)/2+4.6,1.6,-(x1-x0)/2+5.5,2.7)]:[rectPts(-(x1-x0)/2+1.6,1.6,-(x1-x0)/2+2.5,2.7)]});
    {const fs=F(X0+(x0+x1)/2,Z0+PL+D,0,Y0),hw=(x1-x0)/2,wl=[];for(let u=-hw+1.9;u<hw-1;u+=2.9)wl.push([u,1.5,.62,2.35,.4]);
      slab(b,fs,'gnLime',{u0:-hw,u1:hw,y0:-.3,y1:4.6,t:.7,holes:windows(wl)});windowTrim(b,fs,wl);lbox(b,fs,'gnLimeWarm',-hw,4.3,0,hw,4.6,.13);lbox(b,fs,'gnLimeDirty',-hw,0,0,hw,.45,.05);}
    slab(b,F(X0+(sx>0?13.2:-11.1),Z0+PL+D/2,sx*PI/2,Y0),'gnLime',{u0:-D/2,u1:D/2,y0:-.3,y1:4.6,t:.7});
    hipRoof(b,'gnRoof',X0+(x0+x1)/2,Z0+PL+D/2,0,x1-x0+.9,D+.9,Y0+4.55,.3);
    nav(b,X0+(x0+x1)/2,Z0+PL+D/2,x1-x0,D,Y0,Y0+6);
  }
}
// ---------------------------------------------------------------------------------------------------------
// Terraced lower gardens (Jardines Nuevos). The hill is a smooth slope here, so every terrace is a built-up platform whose
// level is chosen at or above the ground at its north edge, with retaining walls down to the actual terrain.
const G=(x,z)=>terrainHeight(x,z);
// Retaining wall along a straight axis-aligned run, built from segments that reach the real ground, with coping and buttresses.
function retWall(b,x0,z0,x1,z1,top,{t=.9,mat='gnRubble',seg=1.9,buttress=0,coping=true,minTop=.0}={}){
  const len=Math.hypot(x1-x0,z1-z0),n=Math.max(1,Math.round(len/seg)),dx=(x1-x0)/n,dz=(z1-z0)/n,alongX=Math.abs(dx)>Math.abs(dz);
  for(let i=0;i<n;i++){
    const xa=x0+dx*i,za=z0+dz*i,xb=xa+dx,zb=za+dz,xc=(xa+xb)/2,zc=(za+zb)/2;
    const gmin=Math.min(G(xa,za),G(xb,zb),G(xc,zc))-.9,h=top-gmin;if(h<.2)continue;
    const w=alongX?Math.abs(dx)+.03:t,d=alongX?t:Math.abs(dz)+.03;
    b.box(xc,gmin,zc,w,h,d,mat);
    if(coping)b.box(xc,top,zc,w+(alongX?.02:.16),.13,d+(alongX?.16:.02),'gnCoping');
    if(buttress&&h>3&&i%buttress===0){const bw=alongX?.9:.7,bd=alongX?.7:.9;b.box(xc+(alongX?0:(dx>0?1:-1)*0),gmin,zc+(alongX?.5*(z0>=0?1:1):0),bw,h-.4,bd,mat);}
  }
}
// Flight of steps along the garden axis (descending towards +z), solid down to the ground, with parapet cheeks.
function flight(b,xc,width,zA,LA,zB,LB,{mat='gnStone',cheek=true}={}){
  const drop=LA-LB,n=Math.max(2,Math.round(Math.abs(drop)/.18)),dz=(zB-zA)/n;
  for(let i=0;i<n;i++){
    const zc=zA+dz*(i+.5),y=LA-drop*(i+1)/n,g=Math.min(G(xc-width/2,zc),G(xc+width/2,zc),G(xc,zc))-.7;
    b.box(xc,g,zc,width,y-g,dz+.015,mat);
    b.box(xc,y-.04,zc-dz/2+.05,width+.06,.06,.1,'gnCoping');
  }
  b.nav.ramp(xc,(zA+zB)/2,width,zB-zA,LA,LB);
  if(!cheek)return;
  let gm=1e9;for(let z=zA;z<=zB;z+=1)gm=Math.min(gm,G(xc-width/2,z),G(xc+width/2,z));gm-=.8;
  for(const s of [-1,1]){
    const sh=new THREE.Shape(V2([[zA,LA+.95],[zB,LB+.95],[zB,gm],[zA,gm]])),g=new THREE.ExtrudeGeometry(sh,{depth:.5,bevelEnabled:false,curveSegments:1});
    g.rotateY(-PI/2);g.translate(s>0?xc+width/2+.5:xc-width/2,0,0);
    put(b,g,F(0,0,0,0),'gnRubble',.5);
  }
}
// A rectangular (or any closed) clipped hedge.
function hedgeLoop(b,pts,y,h=.55,w=.55,seed=1){hedgeRun(b,[...pts,pts[0]],y,h,w,'gnHedge',seed,.7);}
const rectLoop=(x0,z0,x1,z1)=>[[x0,z0],[x1,z0],[x1,z1],[x0,z1]];
function lawn(b,x0,z0,x1,z1,y,mat='gnLawn'){b.box((x0+x1)/2,y-.06,(z0+z1)/2,x1-x0,.08,z1-z0,mat);}
function pool(b,x,z,w,d,y,water,{depth=.12}={}){
  b.box(x,y,z,w+.9,.28,d+.9,'gnCoping');b.box(x,y+.0,z,w,.29,d,'gnBasin');
  water.push({x,z,w:w-.02,d:d-.02,y:y+.2,reflect:false});
}
function roundPool(b,x,z,r,y){
  b.cylinder(x,y,z,r+.45,.3,'gnCoping',r+.45,40);b.cylinder(x,y+.29,z,r,.01,'gnBasin',r,40);b.cylinder(x,y+.3,z,r-.02,.02,'water',r-.02,40);
}
function pebblePatch(b,x0,z0,x1,z1,y){b.box((x0+x1)/2,y-.02,(z0+z1)/2,x1-x0,.05,z1-z0,'gnPebble');}
function cypressRow(b,x0,z0,x1,z1,y,step,h,jit=.8,seed=3){
  const r=random(seed),n=Math.max(1,Math.round(Math.hypot(x1-x0,z1-z0)/step));
  for(let i=0;i<=n;i++){const t=i/n,x=x0+(x1-x0)*t,z=z0+(z1-z0)*t,yy=y===null?G(x,z):y;plant(x+(r()-.5)*jit*.4,yy,z+(r()-.5)*jit*.4,CYPRESS,h*(.9+r()*.25));}
}

const TERR=[ // x0,x1,z0,z1,level
  [344,396,11,25,30.0],[342,398,35,46,25.0],[342,398,58,66,16.0],[342,398,76,84,8.0],[350,390,94,104,0.0]];
const FLIGHTS=[[3,32.0,11,30.0],[25,30.0,35,25.0],[46,25.0,58,16.0],[66,16.0,76,8.0],[84,8.0,94,0.0]];
function lowerGardens(b,water){
  b.zone='gnLower';
  const AX=370,FW=8;
  // --- Patio de la Guardia: the entrance court south of the pavilion, level with the patio
  const P0=-19.6,P1=3;
  b.nav.floor(AX,(P0+P1)/2,36,P1-P0,Y0);
  b.box(AX,Y0-.4,(P0+P1)/2,36,.4,P1-P0,'gnSoil');
  b.box(AX,Y0,(P0+P1)/2,36,.03,P1-P0,'gnPaver');
  pebblePatch(b,AX-3.2,P0+.2,AX+3.2,P1,Y0+.03);
  for(const sx of [-1,1]){
    roundPool(b,AX+sx*8.5,-9,Y0,1.5);
    b.nav.box(AX+sx*8.5,-9,3.9,3.9,Y0,Y0+.4);
    hedgeRun(b,[[AX+sx*13.2,P0+1],[AX+sx*13.2,P1-1]],Y0,.6,.7,'gnHedge',200+sx);
    for(const z of [-16,-4,2])topiary(b,AX+sx*5,Y0+.03,z,.32);
    retWall(b,AX+sx*18,P0,AX+sx*18,P1,Y0+3.0,{buttress:3});
    cypressRow(b,AX+sx*16.4,P0+3,AX+sx*16.4,P1-1,Y0,6,9,1);
  }
  retWall(b,AX-18,P1,AX-4,P1,Y0+.9,{t:.7,coping:true});retWall(b,AX+4,P1,AX+18,P1,Y0+.9,{t:.7});
  // the court's four quadrants: orange trees in lawn squares with flowering edges
  for(const sx of [-1,1]){
    for(const [za,zb] of [[P0+2.2,-12.2],[-6.2,P1-1.8]]){
      const a=sx<0?AX-16.2:AX+4.6,c=sx<0?AX-4.6:AX+16.2;
      hedgeLoop(b,rectLoop(a,za,c,zb),Y0,.5,.5,Math.round(a*2+za));lawn(b,a+.3,za+.3,c-.3,zb-.3,Y0+.02);
      bed(b,a+.9,za+.9,c-.9,zb-.9,Y0+.02,{seed:Math.round(a+za*3),step:.6,cells:[0,4,7,1],hmin:.35,hmax:.7,skip:(x,z)=>Math.hypot(x-(a+c)/2,z-(za+zb)/2)<2.2});
      plant((a+c)/2,Y0,(za+zb)/2,ORANGE,3.6);
    }
  }
  // stone benches along the entrance wall
  for(const sx of [-1,1])for(const z of [-14,-8]){b.box(AX+sx*17.2,Y0,z,.5,.45,1.8,'gnCoping');b.box(AX+sx*17.5,Y0+.45,z,.15,.5,1.8,'gnCoping');}
  // --- terraces and flights
  TERR.forEach(([x0,x1,z0,z1,L],k)=>{
    const xm=(x0+x1)/2,zm=(z0+z1)/2;
    b.nav.floor(xm,zm,x1-x0,z1-z0,L);b.box(xm,L-.35,zm,x1-x0,.35,z1-z0,'gnSoil');
    b.box(xm,L-.02,zm,x1-x0,.04,z1-z0,'gnGravel');
    const wm=['gnLime','gnRubble','gnRubbleB','gnBrickPale','gnRubble'][k];
    retWall(b,x0,z1,x1,z1,L+.1,{buttress:3,t:1.0,mat:wm});
    retWall(b,x0,z0,x0,z1,L+.1,{t:.9,buttress:4,mat:wm});retWall(b,x1,z0,x1,z1,L+.1,{t:.9,buttress:4,mat:wm});
    // a lime string course and coping stones tie each retaining wall together
    if(k<4)for(const xs of [[x0,AX-FW/2-.6],[AX+FW/2+.6,x1]]){const xm2=(xs[0]+xs[1])/2;b.box(xm2,L-1.5,z1+.55,xs[1]-xs[0],.14,.2,'gnCoping');}
  });
  FLIGHTS.forEach(([zA,LA,zB,LB])=>flight(b,AX,FW,zA,LA,zB,LB));
  for(const [zA,LA,zB,LB] of FLIGHTS)for(const sx of [-1,1]){const x=AX+sx*(FW/2+.55);b.box(x,LA+.95,zA+.3,.5,.18,.5,'gnCoping');b.box(x,LA+1.13,zA+.3,.34,.3,.34,'gnStone');b.sphere(x,LA+1.55,zA+.3,.17,.17,.17,'gnStone');b.box(x,LB+.95,zB-.3,.5,.18,.5,'gnCoping');b.sphere(x,LB+1.4,zB-.3,.17,.17,.17,'gnStone');}
  terraceGardens(b,water);
}
function terraceGardens(b,water){
  const AX=370,r=random(404);
  // cypress rows and boundary hedges on every terrace
  TERR.forEach(([x0,x1,z0,z1,L],k)=>{
    if(k<4){for(const sx of [-1,1]){const x=sx<0?x0+1.4:x1-1.4;cypressRow(b,x,z0+1.5,x,z1-1.5,L,6.5,8.5+k*.6,1,10+k);}}
    if(k<4)for(const x of [x0+2.8,x1-2.8])hedgeRun(b,[[x,z0+.8],[x,z1-.8]],L,.6,.6,'gnHedge',300+k*7+x,.8);
  });
  const path=(x0,z0,x1,z1,L)=>pebblePatch(b,x0,z0,x1,z1,L);
  // T0: rose garden, four hedged parterres around a pebble axis
  {const [x0,x1,z0,z1,L]=TERR[0];path(AX-3.6,z0,AX+3.6,z1,L);path(x0+4,(z0+z1)/2-1,x1-4,(z0+z1)/2+1,L);
    for(const [a,c] of [[x0+5.4,AX-5],[AX+5,x1-5.4]]){
      for(const [za,zb] of [[z0+1.3,(z0+z1)/2-1.5],[(z0+z1)/2+1.5,z1-1.3]]){
        hedgeLoop(b,rectLoop(a,za,c,zb),L,.5,.5,Math.round(a*3+za));lawn(b,a+.3,za+.3,c-.3,zb-.3,L+.02);
        bed(b,a+1.0,za+.9,c-1.0,zb-.9,L+.02,{seed:Math.round(a+za),step:.5,cells:[0,7,4,0],hmin:.45,hmax:.9});
        topiary(b,(a+c)/2,L+.02,(za+zb)/2,.34,false);
      }}}
  // T1: water garden — rectangular pool with jets, lawns with orange trees
  {const [x0,x1,z0,z1,L]=TERR[1];const zm=(z0+z1)/2;path(AX-3.6,z0,AX+3.6,z1,L);
    pool(b,AX,zm,4.6,7.2,L,water);
    for(let k=0;k<5;k++){const x=AX-1.8+k*.9;jetArc(b,x,L+.32,zm,x+.04,L+.32,zm,1.0+(k%2)*.5,.012);}
    for(const sx of [-1,1])for(const [za,zb] of [[z0+1.4,z1-1.4]]){
      const a=sx<0?x0+5.4:AX+5,c=sx<0?AX-5:x1-5.4;hedgeLoop(b,rectLoop(a,za,c,zb),L,.5,.5,Math.round(a+zb));lawn(b,a+.3,za+.3,c-.3,zb-.3,L+.02);
      for(const [fx,fz] of [[.3,.3],[.7,.3],[.3,.7],[.7,.7]])plant(a+(c-a)*fx,L,za+(zb-za)*fz,ORANGE,3.4);}}
  // T2: box-hedge lattice parterres with topiary
  {const [x0,x1,z0,z1,L]=TERR[2];path(AX-3.6,z0,AX+3.6,z1,L);
    for(const [a,c] of [[x0+5.4,AX-5],[AX+5,x1-5.4]]){
      const za=z0+1.2,zb=z1-1.2;hedgeLoop(b,rectLoop(a,za,c,zb),L,.45,.45,Math.round(a+5));lawn(b,a+.3,za+.3,c-.3,zb-.3,L+.02);
      const cx=(a+c)/2,cz=(za+zb)/2;hedgeLoop(b,[[cx,za+.8],[c-1.6,cz],[cx,zb-.8],[a+1.6,cz]],L,.4,.4,Math.round(a+9));
      for(const [fx,fz] of [[cx,cz],[a+.9,za+.9],[c-.9,za+.9],[a+.9,zb-.9],[c-.9,zb-.9]])topiary(b,fx,L+.02,fz,.3,false);}}
  // T3: great circular pool with a central jet and pebble rings
  {const [x0,x1,z0,z1,L]=TERR[3];const zm=(z0+z1)/2;path(AX-3.6,z0,AX+3.6,z1,L);
    b.cylinder(AX,L,zm,5.6,.03,'gnPebble',5.6,48);roundPool(b,AX,zm,3.0,L);
    for(let k=0;k<7;k++){const a=k*PI*2/7;jetArc(b,AX+Math.cos(a)*1.0,L+.32,zm+Math.sin(a)*1.0,AX+Math.cos(a)*.08,L+.32,zm+Math.sin(a)*.08,1.0,.011);}
    jetArc(b,AX,L+.32,zm,AX+.03,L+.32,zm,2.2,.016);
    for(const sx of [-1,1]){const a=sx<0?x0+5.4:AX+8,c=sx<0?AX-8:x1-5.4,za=z0+1,zb=z1-1;hedgeLoop(b,rectLoop(a,za,c,zb),L,.5,.5,Math.round(a+11));lawn(b,a+.3,za+.3,c-.3,zb-.3,L+.02);
      bed(b,a+1.2,za+.8,c-1.2,zb-.8,L+.02,{seed:Math.round(a),step:.5,cells:[1,2,4,5,8],hmin:.4,hmax:.8});}}
  pergola(b,AX,TERR[0][2]+1.5,TERR[0][3]-1.5,TERR[0][4],{seed:3});pergola(b,AX,TERR[2][2]+1.0,TERR[2][3]-1.0,TERR[2][4],{seed:5,cells:[CLIMB.bougain,CLIMB.jasmine]});
  // T4: arrival plaza at ground level with the cypress gate to the avenue
  {const [x0,x1,z0,z1,L]=TERR[4];pebblePatch(b,x0+1,z0+.5,x1-1,z1-.5,L+.02);
    for(const sx of [-1,1]){roundPool(b,AX+sx*9,(z0+z1)/2,1.3,L);for(const z of [96,100,104])plant(AX+sx*5.5,L,z,CYPRESS,11);}}
}
// ---------------------------------------------------------------------------------------------------------
// Mass of climber foliage / blossom built from loose cards (bougainvillea, jasmine, roses).
function bloom(b,x,y,z,rx,ry,rz,n,cell,seed,size=.9){
  const r=random(seed);
  for(let k=0;k<n;k++){const a=r()*PI*2,v=r()*2-1,q=Math.sqrt(1-v*v),rad=.55+r()*.45;
    const f=F(x+Math.cos(a)*q*rx*rad,z+Math.sin(a)*q*rz*rad,r()*PI,y+v*ry*rad);const sz=size*(.7+r()*.6);
    card(b,f,'gnBlob',-sz/2,-sz/2,sz/2,sz/2,0,cell);}
}
// East side of the patio, south half: a tall rubble-and-brick garden wall with brick piers carrying an iron railing, and the
// planted terrace behind it.
function eastWall(b){
  b.zone='gnCourt';
  const f=F(X0+PW,Z0,-PI/2,Y0),u0=5.6,u1=PL,H=3.7;
  slab(b,f,'gnRubble',{u0,u1,y0:-.3,y1:H,t:.9});
  lbox(b,f,'gnBrickRed',u0-.1,H,-1.0,u1+.1,H+.14,.1);lbox(b,f,'gnCoping',u0-.1,H+.14,-.95,u1+.1,H+.22,.06);
  // brick piers and railing
  const n=7,step=(u1-u0)/n;
  for(let k=0;k<=n;k++){const u=u0+k*step;lbox(b,f,'gnBrickRed',u-.3,H+.22,-.75,u+.3,H+1.9,-.15);lbox(b,f,'gnCoping',u-.36,H+1.9,-.81,u+.36,H+2.0,-.09);}
  for(let k=0;k<n;k++){const ua=u0+k*step+.3,ub=u0+(k+1)*step-.3,cnt=Math.round((ub-ua)/.13);
    lbox(b,f,'gnIron',ua,H+.4,-.5,ub,H+.46,-.44);lbox(b,f,'gnIron',ua,H+1.55,-.5,ub,H+1.61,-.44);
    for(let q=0;q<=cnt;q++){const u=ua+(ub-ua)*q/cnt;lbox(b,f,'gnIron',u-.011,H+.4,-.49,u+.011,H+1.61,-.45);}}
  nav(b,X0+PW+.45,Z0+(u0+u1)/2,.9,u1-u0,Y0,Y0+H+2);
  // vines and a bougainvillea mass over the wall
  ivyWall(b,F(X0+PW-.04,Z0+(u0+u1)/2,-PI/2,Y0),-(u1-u0)/2,(u1-u0)/2,.2,H+.4,{layers:2,w:.04,tile:1.1,cover:.62,seed:41});
  bloom(b,X0+PW+.3,Y0+H+1.2,Z0+11,.9,.8,3.0,60,CLIMB.bougain,611,1.0);bloom(b,X0+PW+.3,Y0+H+1.0,Z0+19.5,.8,.6,2.2,40,CLIMB.bougain,612,1.0);
  // terrace behind: soil, lawn parterres and orange trees (seen over the wall and from the high gardens)
  const px=X0+17.5,pz=Z0+(-7.6+PL)/2,pw=2*(22.4-PW)-8.0;
  b.box(X0+(PW+.9+29.4)/2,Y0+H-.5,Z0+(5.6+PL)/2,29.4-PW-.9,.5,PL-5.6,'gnSoil');
  b.box(X0+(13.3+29.4)/2,Y0+H-.5,Z0+(-7.6+5.6)/2,29.4-13.3,.5,13.2,'gnSoil');
  const y=Y0+H;
  lawn(b,X0+PW+1.4,Z0+7,X0+27.6,Z0+PL-1.4,y,'gnLawn');
  hedgeLoop(b,rectLoop(X0+PW+2.2,Z0+8,X0+PW+7.6,Z0+PL-2),y,.5,.5,812);bed(b,X0+PW+2.8,Z0+8.6,X0+PW+7.0,Z0+PL-2.6,y,{seed:81,step:.55,cells:[0,7,4,1],hmin:.45,hmax:1.0});
  hedgeLoop(b,rectLoop(X0+PW+10.4,Z0+8,X0+PW+17.8,Z0+PL-2),y,.5,.5,813);bed(b,X0+PW+11,Z0+8.6,X0+PW+17.2,Z0+PL-2.6,y,{seed:82,step:.55,cells:[2,5,8,1],hmin:.45,hmax:.95});
  for(const [x,z] of [[X0+PW+8.9,Z0+9],[X0+PW+8.9,Z0+14],[X0+PW+8.9,Z0+19.5],[X0+25,Z0+10],[X0+25,Z0+17]])plant(x,y,z,ORANGE,3.5);
  cypressRow(b,X0+28.2,Z0-6.4,X0+28.2,Z0+PL-1.5,y,6.2,9.5,1,21);
  retWall(b,X0+13.2,Z0+PL+.45,X0+29.4,Z0+PL+.45,y+.05,{t:.9,buttress:3});
  for(const [x,z] of [[X0+27,Z0-3],[X0+20,Z0-3]])plant(x,y,z,CYPRESS,8.5);
  lawn(b,X0+14,Z0-6.8,X0+27.6,Z0+4.8,y,'gnLawn');
  hedgeLoop(b,rectLoop(X0+15,Z0-5.4,X0+26,Z0+3.4),y,.5,.5,814);
  bed(b,X0+15.6,Z0-4.8,X0+25.4,Z0+2.8,y,{seed:83,step:.55,cells:[0,3,7,4,2],hmin:.5,hmax:1.2});
}
// ---------------------------------------------------------------------------------------------------------
// Ivy mat over a wall: cards stacked in a local frame (u0..u1, y0..y1) at distance w from the wall.
function ivyWall(b,f,u0,u1,y0,y1,{cell=CLIMB.ivy,layers=2,w=.05,tile=1.6,skip=[],cover=1,seed=5}={}){
  if(LOW){layers=1;tile*=1.4;}
  const r=random(seed),hit=(a,c,d,e)=>skip.some(([ua,ub,ya,yb])=>a<ub&&c>ua&&d<yb&&e>ya);
  for(let k=0;k<layers;k++){const off=k*tile*.5;
    for(let u=u0-off*(k%2);u<u1;u+=tile)for(let y=y0-off*(k%2)*.5;y<y1;y+=tile){
      const a=Math.max(u,u0),c=Math.min(u+tile,u1),d=Math.max(y,y0),e=Math.min(y+tile,y1);if(c-a<.3||e-d<.3||hit(a,c,d,e))continue;
      // ragged edge: cover thins out towards the top of the wall
      if(cover<1&&r()>cover*(1.15-.5*((d-y0)/Math.max(1,y1-y0))))continue;
      card(b,f,'gnClimb',a,d,c,e,w+k*.045,cell);}}
}
// Court of the Sultana's Cypress: walled, ivy-clad garden with a rectangular pool, hedged island, jets and the old cypress trunk.
function sultanaCourt(b,water){
  b.zone='gnCourt';
  const x0=X0+13.3,x1=X0+29.4,zn=Z0-34.4,zs=Z0-7.6,xm=(x0+x1)/2,zm=(zn+zs)/2,W=x1-x0,D=zs-zn;
  b.nav.floor(xm,zm,W,D,Y0);b.box(xm,Y0-.4,zm,W,.4,D,'gnSoil');b.box(xm,Y0-.02,zm,W,.05,D,'gnGravel');
  // walls: north, south, east (ochre plaster with a coping and a tile cap), gates
  const wallH=4.4;
  slab(b,F(xm,zn,PI,Y0),'gnOcher',{u0:-W/2,u1:W/2,y0:-.3,y1:wallH,t:.6});
  slab(b,F(xm,zs,0,Y0),'gnOcher',{u0:-W/2,u1:W/2,y0:-.3,y1:wallH-.4,t:.6,holes:[archPts(-W/2+3.6,0,1.3,2.1,.6)]});
  slab(b,F(x1,zm,PI/2,Y0),'gnOcher',{u0:-D/2,u1:D/2,y0:-.3,y1:wallH,t:.6,holes:[archPts(zm-(Z0-21),0,2.3,2.2,.95)]});
  archBand(b,F(x1,zm,PI/2,Y0),'gnBrickRed',zm-(Z0-21),0,2.3,2.2,.95,.3,0,.08);
  for(const [x,z,w,d] of [[xm,zn-.2,W+1,.9],[xm,zs+.2,W+1,.9],[x1+.1,zm,.9,D+1]])b.box(x,Y0+wallH-.02,z,w,.12,d,'gnCoping');
  nav(b,xm,zn,W,.6,Y0,Y0+wallH);nav(b,xm,zs,W,.6,Y0,Y0+wallH);
  {const gz=Z0-21,ga=gz-1.25,gb=gz+1.25;nav(b,x1,(zn+ga)/2,.6,ga-zn,Y0,Y0+wallH);nav(b,x1,(gb+zs)/2,.6,zs-gb,Y0,Y0+wallH);}
  // ivy over the inner faces
  ivyWall(b,F(xm,zn+.6,0,Y0),-W/2,W/2,0,wallH-.3);ivyWall(b,F(xm,zs-.6,PI,Y0),-W/2,W/2,0,wallH-.7);ivyWall(b,F(x1-.6,zm,-PI/2,Y0),-D/2,D/2,0,wallH-.3,{skip:[[(Z0-21-zm)-1.9,(Z0-21-zm)+1.9,0,3.6]]});
  sultanaArcade(b,x0,zn,zs);
  // pool with coping, jets and a hedged island
  const px=xm,pz=zm+.5,pw=6.4,pd=18.0,cw=.55;
  for(const s of [-1,1]){b.box(px+s*(pw/2+cw/2),Y0,pz,cw,.3,pd+2*cw,'gnCoping');b.box(px,Y0,pz+s*(pd/2+cw/2),pw,.3,cw,'gnCoping');}
  b.box(px,Y0-.1,pz,pw,.12,pd,'gnBasin');water.push({x:px,z:pz,w:pw,d:pd,y:Y0+.2,reflect:false});
  nav(b,px,pz,pw+2*cw,pd+2*cw,Y0-1,Y0+.9);
  // the planted island runs south from the middle of the pool to its end wall, so the water wraps it in a U
  const iz0=pz+1.0,iz1=pz+pd/2,iz=(iz0+iz1)/2,id=iz1-iz0;b.box(px,Y0,iz,3.2,.5,id,'gnCoping');b.box(px,Y0+.5,iz,2.8,.06,id-.4,'gnSoil');hedgeLoop(b,rectLoop(px-1.4,iz0+.2,px+1.4,iz1-.2),Y0+.5,.75,.8,77);
  bed(b,px-1.0,iz0+.9,px+1.0,iz1-.9,Y0+.54,{seed:12,step:.45,cells:[0,0,7,4],hmin:.5,hmax:1.0});
  for(const z of [iz0+1.5,iz+.5,iz1-1.5])topiary(b,px,Y0+.5,z,.34,false);
  b.box(px,Y0-.1,pz+pd/2-.2,pw,.12,.4,'gnBasin');
  const fz=pz-4.0;b.box(px,Y0,fz,2.4,.34,2.4,'gnCoping');b.box(px,Y0+.34,fz,1.9,.03,1.9,'gnBasin');
  b.cylinder(px,Y0+.3,fz,.14,.75,'gnStone',.1,10);b.cylinder(px,Y0+1.0,fz,.5,.1,'gnStone',.62,18);b.cylinder(px,Y0+1.08,fz,.42,.03,'gnBasin',.42,16);
  jetArc(b,px,Y0+1.1,fz,px+.02,Y0+1.1,fz,.85,.012);
  // little stone pilones on the coping carry the jets
  for(let z=pz-pd/2+1.2;z<pz+pd/2-.6;z+=1.8)for(const sx of [-1,1]){const fx=px+sx*(pw/2+cw*.25);
    b.cylinder(fx,Y0+.3,z,.07,.07,'gnStone',.1,8);b.cylinder(fx,Y0+.37,z,.045,.2,'gnStone',.045,8);b.cylinder(fx,Y0+.57,z,.09,.04,'gnStone',.05,8);
    jetArc(b,fx-sx*.05,Y0+.62,z,px+sx*(pw/2-1.7),Y0+.2,z+.1,.55,.01);}
  // hedges, topiary, roses
  for(const sx of [-1,1]){const x=px+sx*(pw/2+cw+1.5);hedgeRun(b,[[x,zn+1.6],[x,zs-1.6]],Y0,.85,.9,'gnHedge',400+sx,.8);
    bed(b,x+sx*.5,zn+2.2,x+sx*3.0,zs-2.2,Y0,{seed:60+sx,step:.55,hmin:.5,hmax:1.2});}
  for(const z of [zn+2.2,zs-2.2])for(const sx of [-1,1])topiary(b,px+sx*(pw/2+cw+.7),Y0,z,.34,false);
  // the old cypress of the Sultana: a pale, dead, leaning trunk strapped with iron bands, broken at the top
  {const cx=x1-2.0,cz=zn+2.0,seg=[[0,0,0],[.3,1.8,-.1],[.7,3.9,-.3],[1.15,6.3,-.55],[1.55,8.6,-.8],[1.8,10.2,-.95]],rad=[.62,.5,.42,.34,.26,.18];
    for(let k=0;k<seg.length-1;k++){const a=seg[k],c=seg[k+1];b.line([cx+a[0],Y0+a[1],cz+a[2]],[cx+c[0],Y0+c[1],cz+c[2]],rad[k]*2,'gnBark');}
    b.line([cx+.7,Y0+3.9,cz-.3],[cx-.7,Y0+5.4,cz-.9],.13,'gnBark');b.line([cx+1.15,Y0+6.3,cz-.55],[cx+2.3,Y0+7.3,cz-.1],.1,'gnBark');b.line([cx+1.55,Y0+8.6,cz-.8],[cx+.9,Y0+9.8,cz-1.4],.08,'gnBark');
    for(const t of [.9,2.6]){const k=Math.min(seg.length-2,Math.floor(t/1.9)),a=seg[k],c=seg[k+1],u=(t-k*1.9)/1.9,x=cx+a[0]+(c[0]-a[0])*u,y=a[1]+(c[1]-a[1])*u,z=cz+a[2]+(c[2]-a[2])*u;b.cylinder(x,Y0+y-.05,z,rad[k]+.04,.12,'gnIron',rad[k]+.04,10);}
    nav(b,cx,cz,1.2,1.2,Y0,Y0+12);}
  plant(x1-3.0,Y0,zs-2.4,ORANGE,3.6);
  // corner stair of brick up to the high garden (decor) and a stone bench
  for(let k=0;k<8;k++)b.box(x0+1.4+k*.0,Y0+k*.19,zn+1.6+k*.3,2.0,.19,.34,'gnBrickRed');
  b.box(x0+1.4,Y0,zn+1.6,2.0,.01,.01,'gnBrickRed');
}

// Two-storey arcaded side of the court (white plaster, round arches on slender columns, tiled lean-to roof) facing the pool.
function sultanaArcade(b,x0,zn,zs){
  const fx=x0+2.3,ff=F(fx,Z0,PI/2,Y0),cen=[];for(let k=-3;k<=3;k++)cen.push(19.2+3.2*k);
  const u0=8.2,u1=30.2,holes=cen.map(u=>archPts(u,0,2.5,2.2,1.25));
  slab(b,ff,'gnLime',{u0,u1,y0:-.3,y1:3.95,t:.45,holes});
  for(const u of cen){archBand(b,ff,'gnLimeWarm',u,0,2.5,2.2,1.25,.1,0,.05);}
  lbox(b,ff,'gnLimeWarm',u0,3.7,0,u1,3.95,.14);lbox(b,ff,'gnLimeDirty',u0,0,0,u1,.3,.05);
  const col=b.geometry('gn-colS',()=>columnGeo(2.2,.1));
  for(let k=0;k<=6;k++){const u=cen[0]-1.6+k*3.2,z=Z0-u;b.add(col,'gnMarble',[fx+.28,Y0,z]);lbox(b,ff,'gnLimeDirty',u-.18,0,.0,u+.18,.5,.1);}
  for(const sz of [-1,1]){const u=sz<0?u0:u1,z=Z0-u;b.box(x0+1.15,Y0,z,2.3,3.95,.3,'gnLimeWarm');}
  b.box(x0+1.15,Y0,Z0-(u0+u1)/2,2.3,.04,u1-u0,'gnTerra');b.nav.floor(x0+1.15,Z0-(u0+u1)/2,2.5,u1-u0,Y0);
  b.box(x0+1.15,Y0+3.7,Z0-(u0+u1)/2,2.3,.14,u1-u0,'gnTimber');
  for(let k=0;k<cen.length+1;k++){const u=cen[0]-1.6+k*3.2;nav(b,fx,Z0-u,.5,.8,Y0,Y0+4);}
  {const pa=19.2-1.25,pb=19.2+1.25;nav(b,x0+.15,Z0-(u0+pa)/2,.3,pa-u0,Y0,Y0+4);nav(b,x0+.15,Z0-(pb+u1)/2,.3,u1-pb,Y0,Y0+4);}nav(b,x0+1.15,Z0-u0,2.3,.3,Y0,Y0+4);nav(b,x0+1.15,Z0-u1,2.3,.3,Y0,Y0+4);
  shedRoof(b,'gnRoof',x0+1.3,Z0-(u0+u1)/2,PI/2,u1-u0+.8,2.8,Y0+3.95,.85);
}
// Escalera del Agua: a steep stair with chunky handrail channels carrying running water, round pebble-mosaic landings with
// small fountains and a tunnel of laurel; it climbs east from the Sultana's court to the high gardens.
const ESC={z:Z0-21,x0:400.0,flights:[[400.0,403.6,32.0,33.8],[408.4,412.0,33.8,35.6],[416.8,420.4,35.6,37.4],[425.2,428.8,37.4,39.2]],landings:[[403.6,408.4,33.8],[412.0,416.8,35.6],[420.4,425.2,37.4]],top:39.2};
function escalera(b,water){
  b.zone='gnCourt';
  const z=ESC.z,SW=1.9,CH=.55;
  for(const [xa,xb,ya,yb] of ESC.flights){
    const n=Math.round((yb-ya)/.18),dx=(xb-xa)/n;
    for(let i=0;i<n;i++){const xc=xa+dx*(i+.5),y=ya+(yb-ya)*(i+1)/n,g=Math.min(G(xc,z-1.2),G(xc,z+1.2))-.7;
      b.box(xc,g,z,dx+.01,y-g,SW+2*CH+.2,'gnLimeDirty');b.box(xc,y-.03,z,dx+.012,.04,SW,'gnBrickRed');}
    b.nav.ramp((xa+xb)/2,z,SW,xb-xa,ya,yb,PI/2);
    // handrail cheeks: sloped lime channel with a water ribbon
    for(const sz of [-1,1]){
      const cz=z+sz*(SW/2+CH/2),sh=new THREE.Shape(V2([[xa-.1,ya+.85],[xb+.1,yb+.85],[xb+.1,Math.min(G(xb,cz),G(xa,cz))-.8],[xa-.1,Math.min(G(xb,cz),G(xa,cz))-.8]]));
      const g=new THREE.ExtrudeGeometry(sh,{depth:CH,bevelEnabled:false,curveSegments:1});g.translate(0,0,cz-CH/2);put(b,g,F(0,0,0,0),'gnLime',.5);
      const x0=xa-.1,x1=xb+.1,y0=ya+.87,y1=yb+.87,pos=[],nrm=[],uvs=[];const wz=CH*.36;
      const P=[[x0,y0,cz-wz/2],[x1,y1,cz-wz/2],[x1,y1,cz+wz/2],[x0,y0,cz+wz/2]];
      for(const k of [0,1,2,0,2,3]){pos.push(...P[k]);nrm.push(0,1,0);uvs.push(P[k][0],P[k][2]);}
      const wg=new THREE.BufferGeometry();wg.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));wg.setAttribute('normal',new THREE.Float32BufferAttribute(nrm,3));wg.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));b.unique(wg,'gnWaterStrip');
      // curled horn at the top end of each cheek
      b.cylinder(xb+.15,yb+.45,cz,CH*.62,.62,'gnLime',CH*.5,12);
    }
  }
  for(const [xa,xb,y] of ESC.landings){
    const xc=(xa+xb)/2;
    b.box(xc,Math.min(G(xa,z-2),G(xb,z+2))-.7,z,xb-xa+.1,y-Math.min(G(xa,z-2),G(xb,z+2))+.7,4.6,'gnLimeDirty');
    b.cylinder(xc,y-.04,z,2.4,.06,'gnPebble',2.4,40);
    b.nav.floor(xc,z,xb-xa+.2,3.7,y);
    b.cylinder(xc,y,z,.55,.16,'gnCoping',.5,18);b.cylinder(xc,y+.15,z,.38,.02,'gnBasin',.38,16);b.cylinder(xc,y,z,.09,.38,'gnCoping',.07,8);
    jetArc(b,xc,y+.38,z,xc+.02,y+.38,z,.6,.012);
    b.nav.box(xc,z,.7,.7,y,y+.4);
  }
  // laurel tunnel along the whole stair
  const path=[];for(let xx=ESC.x0+.2;xx<=428.8;xx+=1.2){let yy=32;for(const [xa,xb,ya,yb] of ESC.flights)if(xx>=xa&&xx<=xb)yy=ya+(yb-ya)*(xx-xa)/(xb-xa);for(const [xa,xb,y] of ESC.landings)if(xx>xb-.01&&xx<xa+.01)yy=y;
    for(const [xa,xb,y] of ESC.landings)if(xx>=xa&&xx<=xb)yy=y;for(const [xa,xb,ya,yb] of ESC.flights)if(xx>xb&&xx<xb+.1)yy=yb;path.push([xx,yy]);}
  tunnel(b,path.map(([x,y])=>[x,y+.0,z]),1.55,2.3,'gnTunnel',991);
}
// Foliage tunnel following a path of (x,y,z) points: smooth vertex-displaced vault, with alpha leaf layers inside and out.
function tunnel(b,path,r,h,mat,seed){
  const rn=random(seed),n=14,prof=[];
  for(let i=0;i<=n;i++){const a=PI*i/n;prof.push([Math.cos(a)*r,h*.45+Math.sin(a)*r*.95]);}
  prof.unshift([r,0],[r,h*.2]);prof.push([-r,h*.2],[-r,0]);
  const rows=path.length,cols=prof.length,D=[];for(let i=0;i<rows;i++){D.push([]);for(let j=0;j<cols;j++)D[i].push(1+(rn()-.5)*.16);}
  const build=(grow,layerMat,uvs)=>{
    const pos=[],uv=[],idx=[];
    for(let i=0;i<rows;i++)for(let j=0;j<cols;j++){const P=path[i],e=D[i][j]*grow;pos.push(P[0],P[1]+prof[j][1]*e,P[2]+prof[j][0]*e);uv.push(P[0]*uvs,j*.35*uvs);}
    for(let i=0;i<rows-1;i++)for(let j=0;j<cols-1;j++){const a=i*cols+j,c=a+1,d=a+cols,e=d+1;idx.push(a,d,c,c,d,e);}
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
    b.unique(g.toNonIndexed(),layerMat);
  };
  build(1.0,mat,.5);if(!LOW){build(1.07,'gnLeafMat',.8);build(.93,'gnLeafMat2',.9);}
}
// ---------------------------------------------------------------------------------------------------------
// The high gardens: the hill spur that carries the water stair, shaped as a smooth earth mound that merges with the terrain,
// the planted platform at its crest and the Mirador Romantico.
const PLAT={x0:428.8,x1:442,z0:-88,z1:-58,y:ESC.top};
const sstep=t=>{t=Math.max(0,Math.min(1,t));return t*t*(3-2*t);};
function stairLevel(x){
  let y=Y0;for(const [xa,xb,ya,yb] of ESC.flights){if(x>=xa&&x<=xb)return ya+(yb-ya)*(x-xa)/(xb-xa);}
  for(const [xa,xb,y2] of ESC.landings)if(x>=xa&&x<=xb)return y2;
  if(x>428.8)return ESC.top;if(x<ESC.x0)return Y0;return y;
}
function moundHeight(x,z){
  const base=G(x,z);let extra=0;
  // spur along the stair
  if(x>=396){const hr=stairLevel(Math.min(x,429))-.45,wl=4.2+.62*(Math.max(0,x-398)),lat=sstep(1-Math.abs(z-ESC.z)/wl),fade=sstep((x-396)/4);extra=Math.max(extra,(hr-base)*lat*fade);}
  // plateau of the high gardens
  const dx=Math.max(PLAT.x0-x,0,x-PLAT.x1),dz=Math.max(PLAT.z0-z,0,z-PLAT.z1),d=Math.hypot(dx,dz);
  extra=Math.max(extra,(PLAT.y-.45-base)*sstep(1-d/13));
  return base+Math.max(0,extra);
}
function mound(b){
  b.zone='gnHigh';
  const x0=394,x1=458,z0=-112,z1=-34,st=1.6,nx=Math.round((x1-x0)/st),nz=Math.round((z1-z0)/st),pos=[],uv=[],idx=[];
  const H=[];for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++)H.push(moundHeight(x0+i*st,z0+j*st));
  for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){const x=x0+i*st,z=z0+j*st;pos.push(x,H[j*(nx+1)+i]-.205,z);uv.push(x,z);}
  for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,c=a+1,d=a+nx+1,e=d+1;
    // skip cells entirely on the natural ground
    const g=(k)=>H[k]-G(x0+(k%(nx+1))*st,z0+Math.floor(k/(nx+1))*st);if(g(a)<.02&&g(c)<.02&&g(d)<.02&&g(e)<.02)continue;
    idx.push(a,d,c,c,d,e);}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
  b.unique(g.toNonIndexed(),'gnBank');
  // keep walkers off the slopes: blocks either side of the stair corridor (wider at the round landings)
  {const zc=ESC.z,segs=[[399.6,ESC.flights[0][0],1.15],...ESC.flights.map(f=>[f[0],f[1],1.15]),...ESC.landings.map(l=>[l[0],l[1],1.95])];
    const all=[[399.6,400,1.15],...ESC.flights.map(f=>[f[0],f[1],1.15]),...ESC.landings.map(l=>[l[0],l[1],1.95]),[428.8,PLAT.x0,1.15]].sort((a,b)=>a[0]-b[0]);
    for(const [xa,xb,c] of all){if(xb<=xa)continue;
      b.nav.box((xa+xb)/2,(zc-c-110)/2,xb-xa,Math.abs(zc-c+110),Y0-1,Y0+14);b.nav.box((xa+xb)/2,(zc+c-38)/2,xb-xa,Math.abs(zc+c+38),Y0-1,Y0+14);}}
}
function highGardens(b,water){
  b.zone='gnHigh';
  const {x0,x1,z0,z1,y}=PLAT,xm=(x0+x1)/2,zm=(z0+z1)/2;
  b.nav.floor(xm,zm,x1-x0,z1-z0,y);b.box(xm,y-.5,zm,x1-x0,.5,z1-z0,'gnSoil');b.box(xm,y-.02,zm,x1-x0,.04,z1-z0,'gnGravel');
  for(const [bx,bz,w,d] of [[xm,z0-6,x1-x0+30,12],[xm,z1+6,x1-x0+30,12],[x1+6,zm,12,z1-z0+24]])b.nav.box(bx,bz,w,d,y-3,y+10);
  pebblePatch(b,x0,zm-3,x1-1.5,zm+3,y);
  // parterres north and south of the axis
  for(const [za,zb] of [[z0+2,zm-5.5],[zm+5.5,z1-2]]){
    hedgeLoop(b,rectLoop(x0+1.6,za,x1-1.6,zb),y,.5,.5,Math.round(za));lawn(b,x0+1.9,za+.3,x1-1.9,zb-.3,y+.02);
    bed(b,x0+3,za+1.2,x1-3,zb-1.2,y+.02,{seed:Math.round(za*3),step:.5,cells:[0,7,4,1,2],hmin:.45,hmax:.95});
    for(const x of [x0+1.0,x1-1.0])plant(x,y,(za+zb)/2,CYPRESS,9);}
  // Mirador Romantico: a small neo-Nasrid kiosk with open arches and a pyramidal tile roof
  const mx=x1-3.4,mz=zm,S=5.4,H=3.4;
  b.box(mx,y,mz,S+1.0,.35,S+1.0,'gnCoping');b.box(mx,y+.35,mz,S,.04,S,'gnTerra');
  for(let k=0;k<4;k++){const yaw=k*PI/2,fx=mx+Math.sin(yaw)*S/2,fz=mz+Math.cos(yaw)*S/2,f=F(fx,fz,yaw,y+.35);
    slab(b,f,'gnLimeWarm',{u0:-S/2,u1:S/2,y0:0,y1:H,t:.5,holes:[archPts(0,.0+.01,2.2,2.1,.95,{hs:.15})]},.5);
    archBand(b,f,'gnPink',0,.01,2.2,2.1,.95,.22,0,.06,{hs:.15});archBand(b,f,'gnPink',0,.01,2.1,2.1,.9,.05,-.5,0,{hs:.15});
    lbox(b,f,'gnLimeWarm',-S/2,H-.2,0,S/2,H,.14);
    if(k!==1)continue;}
  hipRoof(b,'gnRoof',mx,mz,0,S+1.0,S+1.0,y+.35+H,.5);
  b.cylinder(mx,y+.35+H+.9,mz,.08,.7,'gnIron',.04,8);
  nav(b,mx-S/2+.25,mz,.5,S,y,y+4);nav(b,mx+S/2-.25,mz,.5,S,y,y+4);nav(b,mx,mz-S/2+.25,S,.5,y,y+4);nav(b,mx,mz+S/2-.25,S,.5,y,y+4);
  // slopes: cypresses and olive trees on the mound
  const r=random(55);
  for(let k=0;k<26;k++){const x=398+r()*52,z=-106+r()*68;if(x<429&&Math.abs(z-ESC.z)<7)continue;if(x>=PLAT.x0-1&&x<=PLAT.x1+1&&z>=PLAT.z0-1&&z<=PLAT.z1+1)continue;if(x<400&&z>-87&&z<-59)continue;
    plant(x,moundHeight(x,z)-.1,z,r()>.45?CYPRESS:OLIVE,r()>.45?8+r()*4:4.5);}
}
// ---------------------------------------------------------------------------------------------------------
// Open-air theatre (Teatro del Generalife) and the cypress / oleander avenues of the outer gardens.
// Annular sector, base y0, height h, between radii r0..r1 and polar angles a0..a1 (0 = +z, positive towards +x).
function sector(b,mat,cx,cz,r0,r1,a0,a1,y0,h,n=18){
  const sh=new THREE.Shape(),pt=(r,a)=>[cx+Math.sin(a)*r,-(cz+Math.cos(a)*r)];
  sh.moveTo(...pt(r1,a0));for(let k=1;k<=n;k++)sh.lineTo(...pt(r1,a0+(a1-a0)*k/n));
  for(let k=n;k>=0;k--)sh.lineTo(...pt(r0,a0+(a1-a0)*k/n));sh.closePath();
  const g=new THREE.ExtrudeGeometry(sh,{depth:h,bevelEnabled:false,curveSegments:1});g.rotateX(-PI/2);g.translate(0,y0,0);
  b.unique(prep(g,.5),mat);
}
function teatro(b){
  b.zone='gnFar';
  const cx=420,cz=147,N=11,rise=.42,run=.95,r0=9.5,y0=0,low=y0-2.2;
  // stage: a raised stone platform with clipped cypress wings
  b.box(cx,low,cz+7.5,22,y0+.55-low,13,'gnCoping');b.box(cx,y0+.55,cz+7.5,21.4,.04,12.4,'gnGravel');b.nav.floor(cx,cz+7.5,22,13,y0+.55);
  b.box(cx,low,cz+16.2,22,y0+3.8-low,2.2,'gnRubble');
  for(const sx of [-1,1]){hedgeRun(b,[[cx+sx*8.5,cz+3],[cx+sx*8.5,cz+14]],y0+.55,4.0,1.4,'gnHedge',700+sx,.9);hedgeRun(b,[[cx+sx*4.5,cz+6],[cx+sx*4.5,cz+14]],y0+.55,3.6,1.3,'gnHedge',710+sx,.9);}
  hedgeRun(b,[[cx-9.5,cz+15],[cx+9.5,cz+15]],y0+.55,4.4,1.6,'gnHedge',720,.9);
  for(let k=0;k<N;k++){const a=k*run;sector(b,'gnCoping',cx,cz,r0+a,r0+a+run,PI-1.62,PI+1.62,low,y0-low+rise*(k+1),22);}
  b.nav.box(cx,cz-10,2*(r0+N*run)*.92,20,low,y0+rise*N+1);
  // pebble apron between stage and the first tier, cypress backdrop
  b.cylinder(cx,y0,cz,r0-.2,.04,'gnPebble',r0-.2,36);
  for(let k=0;k<=12;k++){const a=PI-1.9+3.8*k/12,r=r0+N*run+2.2;plant(cx+Math.sin(a)*r,y0,cz+Math.cos(a)*r,CYPRESS,9+((k*7)%3));}
}
function avenues(b){
  b.zone='gnFar';
  const line=(pts,step,fn)=>{let rem=0;for(let i=0;i<pts.length-1;i++){const [x0,z0]=pts[i],[x1,z1]=pts[i+1],L=Math.hypot(x1-x0,z1-z0);for(let d=rem;d<L;d+=step)fn(x0+(x1-x0)*d/L,z0+(z1-z0)*d/L,(z1-z0)/L,-(x1-x0)/L);rem=((rem-L)%step+step)%step;}};
  // Paseo de los Cipreses: double rows along the OSM footways
  for(const pts of [[[493,158],[486,162],[446,217]],[[501,152],[478,115],[445,83],[437,75]],[[446,217],[436,233],[432,244],[430,254],[431,265],[432,273],[437,285],[452,310]]])
    line(pts,5.6,(x,z,nx,nz)=>{for(const sd of [-1,1]){const xx=x+nx*3.2*sd,zz=z+nz*3.2*sd;plant(xx,G(xx,zz),zz,CYPRESS,12+((Math.round(x*3+z*5))%4));}});
  // Paseo de las Adelfas: plane trees in two rows and oleanders along the path
  line([[438,72],[396,-39]],8.5,(x,z)=>{plant(x,G(x,z),z,PLANE,13+((Math.round(x+z))%3));});
  line([[433,73],[391,-38]],8.5,(x,z)=>{plant(x+4,G(x+4,z),z,PLANE,13+((Math.round(x*2+z))%3));});
  line([[437,75],[391,-43]],2.6,(x,z,nx,nz)=>{const xx=x+nx*1.6,zz=z+nz*1.6;plant(xx,G(xx,zz),zz,SHRUB,2.2+((Math.round(x*7+z))%3)*.3);});
}
// ---------------------------------------------------------------------------------------------------------
// Garden pergola: iron hoops with climbing roses and bougainvillea over a path (axis along z).
function pergola(b,xc,za,zb,y,{width=4.0,step=2.2,h=2.6,seed=1,cells=[CLIMB.rose,CLIMB.bougain,CLIMB.jasmine]}={}){
  const r=random(seed),n=Math.max(2,Math.round((zb-za)/step)),R=width/2;
  for(let k=0;k<=n;k++){
    const z=za+(zb-za)*k/n,pts=[];
    for(let q=0;q<=12;q++){const a=PI*q/12;pts.push([xc+Math.cos(a)*R,y+h+Math.sin(a)*R*.95,z]);}
    for(let q=0;q<12;q++)b.line(pts[q],pts[q+1],.04,'gnIron');
    b.line([xc-R,y,z],[xc-R,y+h,z],.04,'gnIron');b.line([xc+R,y,z],[xc+R,y+h,z],.04,'gnIron');
    // blossom clusters on the hoop
    for(let q=1;q<12;q+=2){const p=pts[q];const f=F(p[0]+(r()-.5)*.25,p[2]+(r()-.5)*.3,r()*PI,p[1]+(r()-.5)*.2),c=cells[Math.floor(r()*cells.length)],sz=1.2+r()*.5;card(b,f,'gnBlob',-sz/2,-sz/2,sz/2,sz/2,0,c);}
    for(const sx of [-1,1])for(let q=0;q<3;q++){const f=F(xc+sx*(R+.05),z+(r()-.5)*.2,r()*PI,y+.4+q*.8),c=cells[Math.floor(r()*cells.length)],sz=.95;card(b,f,'gnBlob',-sz/2,-sz/2,sz/2,sz/2,0,c);}
  }
  for(const sx of [-1,1])b.line([xc+sx*R,y+h*.55,za],[xc+sx*R,y+h*.55,zb],.025,'gnIron');
  for(let q=0;q<=6;q++){const a=PI*q/6,p=[xc+Math.cos(a)*R,y+h+Math.sin(a)*R*.95];b.line([p[0],p[1],za],[p[0],p[1],zb],.025,'gnIron');}
}
// A low battered plinth of rubble masonry around the foot of a wall (x0,z0)-(x1,z1), reaching down to the ground.
function plinth(b,x0,z0,x1,z1,top,t=.8){retWall(b,x0,z0,x1,z1,top,{t,mat:'gnRubble',coping:false,seg:2.2});}
function foundations(b){
  b.zone='gnCourt';
  const T=Y0+.5,xW=X0-PW-.75-3.0-.6-.1,zN=Z0-PL-9.6-.3;
  plinth(b,xW-.15,Z0-PL-9.6,xW-.15,Z0+PL+8,T,.75);               // west gallery + pavilions, west face
  plinth(b,X0-11.1,zN-.1,X0+13.4,zN-.1,T,.8);                     // north back wall
  plinth(b,X0+13.4,zN,X0+13.4,Z0-34,T,.8);                        // east end of north block / court corner
  plinth(b,X0-11.2,Z0+PL+8.15,X0+13.3,Z0+PL+8.15,T,.8);           // south pavilion rear
  plinth(b,X0-11.2,Z0+PL,X0-11.2,Z0+PL+8,T,.8);plinth(b,X0+13.3,Z0+PL,X0+13.3,Z0+PL+8,T,.8);
  plinth(b,X0+13.3,Z0-34.4-.1,X0+29.5,Z0-34.4-.1,T,.9);           // Sultana court north wall
}
// ---------------------------------------------------------------------------------------------------------
export function build(b,water,ctx){
  b.offset=[0,0,0];LOW=!!(ctx&&ctx.low);
  patioGround(b,water);westGallery(b);eastWing(b);northPavilion(b);southPavilion(b);
  eastWall(b);sultanaCourt(b,water);escalera(b,water);mound(b);highGardens(b,water);lowerGardens(b,water);teatro(b);avenues(b);foundations(b);
}
function oldSouth(b){
  b.zone='gnLower';
  b.floor(370,-10,8,26,32,'paving');
  for(let row=0;row<5;row++){
    const zz=10+row*19,level=32-row*1.7;
    for(const xx of [349.5,390.5])b.floor(xx,zz,31,19,level,'paving');
    b.floor(370,zz,10,14,level,'paving');
    if(row<4){
      for(let step=0;step<10;step++)b.box(370,level-(step+1)*.17-.15,zz+7+(step+.5)*.5,10,.15,.52,'paving');
      b.nav.ramp(370,zz+9.5,10,5,level,level-1.7);
    }
    for(const xx of [346,394]){b.box(xx,level,zz,15,.7,13,'hedge',0,true);b.box(xx,level+.71,zz,12,.03,10,'earth');for(const sx of [-1,1])plant(xx+sx*5,level+.75,zz,CYPRESS,6.5);}
    for(const xx of [335,405])plant(xx,level,zz,CYPRESS,10);
  }
  for(let i=0;i<8;i++)b.box(370,25.2-(i+1)*.15-.15,94+i*2,10,.15,2.02,'paving');
  b.nav.ramp(370,101,10,16,25.2,24);b.floor(370,112,12,6,24,'paving');
  stairs(b,370,145,8,64,24,0);b.floor(370,112,10,5,24,'paving');b.floor(370,178,10,6,0,'paving');
}
