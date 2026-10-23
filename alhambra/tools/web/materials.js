import * as THREE from 'three';

export function random(seed=42){return ()=>{seed=(Math.imul(1664525,seed)+1013904223)|0;return (seed>>>0)/4294967296;};}
function canvas(size=1024){const c=document.createElement('canvas');c.width=c.height=size;return [c,c.getContext('2d',{willReadFrequently:true})];}
function polygon(ctx,pts,fill,stroke='#d4c6a5',width=2){ctx.beginPath();pts.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle=fill;ctx.fill();if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke();}}
function star(cx,cy,r,n=8,inner=.46,rot=-Math.PI/2){return Array.from({length:n*2},(_,i)=>{const a=rot+i*Math.PI/n,rr=i%2?r*inner:r;return [cx+Math.cos(a)*rr,cy+Math.sin(a)*rr];});}
function noise(ctx,size,seed,amount=8,n=65000){
  // Speckle in one pass over the pixels (was tens of thousands of fillRect calls).
  const rand=random(seed),img=ctx.getImageData(0,0,size,size),d=img.data;
  for(let i=0;i<n;i++){const v=rand()>.5?255:0,a=rand()*amount/100,x0=rand()*size|0,y0=rand()*size|0,w=1+rand()*3|0,h=1+rand()*3|0;
    for(let y=y0;y<Math.min(size,y0+h);y++)for(let x=x0;x<Math.min(size,x0+w);x++){const k=(y*size+x)*4;d[k]+=(v-d[k])*a;d[k+1]+=(v-d[k+1])*a;d[k+2]+=(v-d[k+2])*a;}}
  ctx.putImageData(img,0,0);}
function tex(c,srgb=true){const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=srgb?THREE.SRGBColorSpace:THREE.NoColorSpace;t.anisotropy=8;return t;}
function normal(c,strength=3){const w=c.width,h=c.height,ctx=c.getContext('2d'),src=ctx.getImageData(0,0,w,h).data;const [out,oc]=canvas(w);const data=oc.createImageData(w,h);const val=(x,y)=>src[(((y+h)%h)*w+(x+w)%w)*4];for(let y=0;y<h;y++)for(let x=0;x<w;x++){const dx=(val(x-1,y)-val(x+1,y))*strength/255,dy=(val(x,y-1)-val(x,y+1))*strength/255,l=Math.hypot(dx,dy,1),k=(y*w+x)*4;data.data[k]=(dx/l*.5+.5)*255;data.data[k+1]=(dy/l*.5+.5)*255;data.data[k+2]=(1/l*.5+.5)*255;data.data[k+3]=255;}oc.putImageData(data,0,0);return tex(out,false);}

function zellige(variant=0){
  const [c,g]=canvas();const S=1024,palette=['#163f40','#c59b44','#1c355b','#e9dfc2','#272d2b','#e4e0c9'];
  g.fillStyle='#dfd8bc';g.fillRect(0,0,S,S);
  for(let y=-256;y<=S+256;y+=256)for(let x=-256;x<=S+256;x+=256){
    const k=(Math.round(x/256+y/256)+40)%4;
    if(variant===1){
      g.fillStyle='#eee5cb';g.fillRect(x-128,y-128,256,256);
      const ink=['#27466a','#47806a','#c4a040','#9d6049'];
      for(let a=0;a<4;a++){g.save();g.translate(x,y);g.rotate(a*Math.PI/2);g.beginPath();[[-128,-96],[-86,-96],[-54,-64],[-54,-16],[-22,16],[22,16],[54,-16],[54,-64],[86,-96],[128,-96]].forEach(([u,v],i)=>i?g.lineTo(u,v):g.moveTo(u,v));g.lineJoin='miter';g.lineWidth=16;g.strokeStyle='#f8efdb';g.stroke();g.lineWidth=8;g.strokeStyle=ink[a];g.stroke();g.beginPath();[[-116,-46],[-88,-18],[-88,18],[-116,46],[-144,18],[-144,-18],[-116,-46]].forEach(([u,v],i)=>i?g.lineTo(u,v):g.moveTo(u,v));g.lineWidth=15;g.strokeStyle='#f8efdb';g.stroke();g.lineWidth=7;g.strokeStyle=ink[(a+2)%4];g.stroke();g.restore();}
      polygon(g,star(x,y,26,8,.5),'#eee5cb','#325773',4);
    }else{
      for(let a=0;a<8;a++){const th=a*Math.PI/4;g.save();g.translate(x,y);g.rotate(th);polygon(g,[[68,-20],[107,-20],[128,0],[107,20],[68,20],[82,0]],palette[(a+k)%3],'#ddd1b5',3);g.restore();}
      polygon(g,star(x,y,96,8,.415),palette[(k+variant)%3],'#eee4cb',4);
      polygon(g,star(x+128,y+128,75,8,.42),palette[variant===2?1:4],'#eee4cb',4);
      polygon(g,star(x,y,25,8,.44),'#ddc080','#eee1bb',3);
    }
  }
  noise(g,S,22+variant,9);return c;
}
function plaster(){
  const [c,g]=canvas();g.fillStyle='#c7b79b';g.fillRect(0,0,1024,1024);
  // Interlacing sebka and vegetal relief, rendered as a height field as well as colour.
  for(let y=-128;y<1200;y+=128)for(let x=-128;x<1200;x+=128){
    g.lineWidth=10;g.strokeStyle='#eee0bc';g.beginPath();g.moveTo(x,y+64);g.bezierCurveTo(x+20,y+30,x+40,y+30,x+64,y);g.bezierCurveTo(x+88,y+30,x+108,y+30,x+128,y+64);g.bezierCurveTo(x+108,y+98,x+88,y+98,x+64,y+128);g.bezierCurveTo(x+40,y+98,x+20,y+98,x,y+64);g.stroke();
    g.strokeStyle='#d3c29f';g.lineWidth=3;g.stroke();
    g.save();g.translate(x+64,y+64);
    for(let a=0;a<8;a++){g.rotate(Math.PI/4);g.strokeStyle='#f3e4c0';g.lineWidth=5;g.beginPath();g.moveTo(0,2);g.bezierCurveTo(-28,-12,-20,-31,0,-40);g.bezierCurveTo(17,-24,14,-9,0,2);g.stroke();}
    polygon(g,star(0,0,13,8,.45),'#eee0b9',null);g.restore();
  }
  noise(g,1024,4,5);return c;
}
function stone(base,brick=false){
  const [c,g]=canvas();g.fillStyle=base;g.fillRect(0,0,1024,1024);const r=random(77);
  if(brick){for(let j=0;j<16;j++)for(let i=-1;i<9;i++){const x=i*128+(j%2)*64,y=j*64;g.fillStyle=`rgba(${r()>.5?'235,210,170':'75,53,33'},${.03+r()*.10})`;g.fillRect(x+3,y+2,123,60);g.strokeStyle='#704b3233';g.lineWidth=2;g.strokeRect(x,y,128,64);}}
  else{for(let j=0;j<4;j++)for(let i=0;i<4;i++){g.fillStyle=`rgba(110,90,60,${r()*.04})`;g.fillRect(i*256,j*256,256,256);g.strokeStyle='#8e8e7e30';g.lineWidth=2;g.strokeRect(i*256,j*256,256,256);}}
  noise(g,1024,89,11,110000);return c;
}
function roof(){const [c,g]=canvas();g.fillStyle='#9c5035';g.fillRect(0,0,1024,1024);const r=random(2);for(let j=0;j<16;j++)for(let i=0;i<20;i++){const x=i*52,y=j*64;const gr=g.createLinearGradient(x,0,x+52,0);gr.addColorStop(0,'#6e3f2b');gr.addColorStop(.35,`hsl(21,36%,${43+r()*11}%)`);gr.addColorStop(.85,'#b6734c');gr.addColorStop(1,'#79432d');g.fillStyle=gr;g.fillRect(x,y,52,64);g.fillStyle='#542c293a';g.fillRect(x,y+61,52,3);}noise(g,1024,3,8);return c;}
function timber(){const [c,g]=canvas();g.fillStyle='#513421';g.fillRect(0,0,1024,1024);for(let y=0;y<=1024;y+=128)for(let x=0;x<=1024;x+=128){polygon(g,star(x,y,58,8,.54),'#9d713d','#d3ae68',3);polygon(g,star(x,y,30,8,.44),'#3f3330','#bf9857',2);polygon(g,[[x+64,y+4],[x+122,y+64],[x+64,y+122],[x+6,y+64]],'#79603b','#c39a5c',3);}noise(g,1024,62,12);return c;}
function foliage(){const [c,g]=canvas(512);g.fillStyle='#36543a';g.fillRect(0,0,512,512);const r=random(6);for(let i=0;i<9000;i++){g.fillStyle=`hsl(${75+r()*35},${16+r()*25}%,${19+r()*21}%)`;g.beginPath();g.ellipse(r()*512,r()*512,2+r()*4,1+r()*4,r()*Math.PI,0,Math.PI*2);g.fill();}return c;}
function frieze(){const [c,g]=canvas();g.fillStyle='#bdab88';g.fillRect(0,0,1024,1024);g.strokeStyle='#f4e7c6';g.lineWidth=8;for(let y=0;y<1024;y+=256){g.strokeRect(5,y+9,1014,238);g.strokeRect(15,y+19,994,218);for(let x=0;x<1024;x+=512){polygon(g,star(x+54,y+128,35,8,.43),'#deceab','#f4e7c6',3);g.direction='rtl';g.textAlign='center';g.font='58px serif';g.fillStyle='#eee0be';g.fillText('ولا غالب إلا الله',x+300,y+145,380);g.direction='ltr';}}noise(g,1024,22,4);return c;}

export function materials(){
  const M={};const make=(name,color,roughness=0.85,texture=null,scale=1,relief=.15)=>{
    const m=new THREE.MeshStandardMaterial({color,roughness,metalness:0});m.name=name;m.userData.scale=scale;
    if(texture){m.map=tex(texture);if(relief){m.bumpMap=m.map;m.bumpScale=relief*.05;}} // GPU bump from the colour: no CPU normal-map pass at start-up
    M[name]=m;return m;
  };
  make('plaster',0xfff4dd,.92,plaster(),1.25,.55);
  make('ivory',0xf4e6cb,.86,stone('#e2d5b6'),2,.11);
  make('marble',0xffffff,.42,stone('#deddd1'),4,.055);
  make('tile',0xffffff,.39,zellige(),1.8,.18);
  make('tileBlue',0xffffff,.39,zellige(2),1.6,.18);
  make('tileRibbon',0xffffff,.44,zellige(1),1.5,.18);
  make('frieze',0xfff3dc,.88,frieze(),1.3,.38);
  make('redwall',0xf1cbb3,.96,stone('#af8264',true),7,.31);
  make('brick',0xe0be9a,.94,stone('#b38666',true),3.2,.24);
  make('roof',0xffffff,.9,roof(),3,.38);
  make('wood',0xf5dfbc,.8,timber(),2.2,.2);
  M.wood.side=THREE.DoubleSide;M.plaster.side=THREE.DoubleSide;
  make('earth',0xcebc93,.99,stone('#b3a17a'),6,.1);
  make('paving',0xf0e8d4,.95,stone('#c4bca5'),4,.13);
  make('hedge',0xa4af70,.97,foliage(),3,.28);
  make('tree',0x798a58,.97,foliage(),4,.23);
  make('cypress',0x55754a,.96,foliage(),3,.2);
  make('trunk',0x665243);make('gold',0xc8a15d,.5);
  make('muqar',0xe6d7ba,.93);M.muqar.side=THREE.DoubleSide;
  make('dark',0x374838);make('flower',0xdca9b0,.9);make('whiteFlower',0xeee4cf,.9);
  make('city',0xe4d8bf,.94,stone('#d6cdb8'),6,.1);
  M.water=new THREE.MeshPhysicalMaterial({color:0x477e73,roughness:.18,metalness:.2,transparent:true,opacity:.68,clearcoat:1,side:THREE.DoubleSide});M.water.name='water';
  M.jet=new THREE.MeshBasicMaterial({color:0xc9e4de,transparent:true,opacity:.48,depthWrite:false});M.jet.name='jet';
  M.shadow=new THREE.MeshBasicMaterial({color:0x3d4032,transparent:true,opacity:.12,depthWrite:false});M.shadow.name='shadow';
  return M;
}
