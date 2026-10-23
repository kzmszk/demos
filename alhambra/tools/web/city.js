import * as THREE from 'three';

// Granada from OpenStreetMap footprints (tools/gen/city.py). Walls carry metre coordinates
// (along the wall, height above the street); the shader picks a facade style from an atlas drawn
// here, one storey at a time, so ground floors (doors, rejas, zócalo) never repeat upstairs.

const BAY=3.6,CELL_W=4*BAY,STOREY=3.0,GROUND=3.5;

function rng(seed){return ()=>((seed=Math.imul(seed,1664525)+1013904223|0)>>>0)/4294967296;}
function facadeAtlas(){
  const W=2048,H=768,c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');
  const STYLES=[
    {wall:'#f1ede3',shut:'#2f4b3c',frame:'#f7f4ec',plinth:'#c8a46c',bal:.25,blank:.25,door:'#5a3f2a',arch:true},
    {wall:'#efe9dc',shut:'#6e4a2e',frame:'#f6f1e6',plinth:'#9d9a92',bal:.5,blank:.15,door:'#4b3322',arch:false},
    {wall:'#e8d5ad',shut:'#3c5a46',frame:'#f6eedc',plinth:'#a89a80',bal:.5,blank:.05,door:'#5c3b26',cornice:true},
    {wall:'#d8aa62',shut:'#5a3a24',frame:'#f3e6c8',plinth:'#8d7a5c',bal:.5,blank:.05,door:'#4a2f1e',cornice:true},
    {wall:'#d9a28a',shut:'#41563f',frame:'#f5e8da',plinth:'#8f7d6c',bal:.4,blank:.05,door:'#4d3424',cornice:true},
    {wall:'#e9e6df',shut:null,frame:'#bdbab3',plinth:'#8e8b85',bal:.7,blank:0,door:'#3a3d40',modern:true},
    {wall:'#a85e3f',shut:null,frame:'#efe9dd',plinth:'#6e5a4c',bal:.4,blank:0,door:'#3a3d40',modern:true,brick:true},
    {wall:'#d8c39c',shut:null,frame:'#cdb68d',plinth:'#b49f7a',bal:0,blank:.6,door:'#4a3524',stone:true},
    {wall:'#b4704c',shut:null,frame:'#c99a72',plinth:'#8c5e44',bal:0,blank:.5,door:'#3e2a1c',brick:true,tower:true},
    {wall:'#b98a62',shut:null,frame:'#b98a62',plinth:'#94694a',bal:0,blank:1,door:'#b98a62',tapial:true},
  ];
  const r=rng(7);
  const noise=(x,y,w,h,a,n)=>{for(let i=0;i<n;i++){const v=r()>.5?255:0;g.fillStyle=`rgba(${v},${v},${v},${a*r()})`;g.fillRect(x+r()*w,y+r()*h,1+r()*2,1+r()*2);}};
  STYLES.forEach((s,i)=>{
    const x0=(i%4)*512,y0=Math.floor(i/4)*256;
    for(const ground of [false,true]){
      const y=y0+(ground?128:0),hm=ground?GROUND:STOREY,px=128/hm,py=v=>y+128-v*px; // metres up -> canvas y
      g.fillStyle=s.wall;g.fillRect(x0,y,512,128);noise(x0,y,512,128,.05,900);
      if(s.brick){for(let j=0;j<128;j+=4){g.fillStyle='rgba(60,30,20,.25)';g.fillRect(x0,y+j,512,1);for(let k=(j/4)%2*6;k<512;k+=12){g.fillRect(x0+k,y+j,1,4);}}}
      if(s.tapial){for(let j=0;j<128;j+=36){g.fillStyle='rgba(235,215,180,.35)';g.fillRect(x0,y+j,512,3);g.fillStyle='rgba(70,45,30,.25)';g.fillRect(x0,y+j+3,512,1);for(let k=(j/36)%2*40;k<512;k+=80){g.fillStyle='rgba(40,25,15,.55)';g.fillRect(x0+k,y+j+5,4,4);}}
        for(let k=0;k<40;k++){g.fillStyle=`rgba(${r()>.5?220:80},${r()>.5?190:60},${140},${.08+r()*.1})`;g.beginPath();g.ellipse(x0+r()*512,y+r()*128,6+r()*30,3+r()*10,0,0,7);g.fill();}}
      if(s.stone){for(let j=0;j<128;j+=18){g.fillStyle='rgba(90,70,40,.22)';g.fillRect(x0,y+j,512,1.5);for(let k=(j/18)%2*24;k<512;k+=48)g.fillRect(x0+k,y+j,1.5,18);}}
      if(ground){g.fillStyle=s.plinth;g.fillRect(x0,py(.75),512,.75*px+1);noise(x0,py(.75),512,.75*px,.12,300);}
      if(s.cornice&&!ground){g.fillStyle='rgba(255,250,235,.85)';g.fillRect(x0,py(2.95),512,4);g.fillStyle='rgba(60,45,30,.25)';g.fillRect(x0,py(2.84),512,2);}
      for(let b=0;b<4;b++){
        const cx=x0+b*128+64,mx=v=>v*128/BAY;
        if(r()<s.blank&&!(ground&&b===1))continue;
        if(ground&&b===1){ // door
          const dw=mx(s.modern?1.6:1.15),dh=(s.modern?2.6:2.35);
          g.fillStyle=s.frame;g.fillRect(cx-dw/2-4,py(dh+.12),dw+8,dh*px+6);
          g.fillStyle=s.door;if(s.arch){g.beginPath();g.moveTo(cx-dw/2,py(0));g.lineTo(cx-dw/2,py(dh-dw/2/px));g.arc(cx,py(dh-dw/2/px),dw/2,Math.PI,0);g.lineTo(cx+dw/2,py(0));g.fill();}else g.fillRect(cx-dw/2,py(dh),dw,dh*px);
          g.fillStyle='rgba(0,0,0,.25)';g.fillRect(cx-1,py(dh),2,dh*px);noise(cx-dw/2,py(dh),dw,dh*px,.15,80);continue;
        }
        if(s.tapial)continue;
        if(s.tower){if(ground)continue;const ww=mx(.9);g.fillStyle='#2a2420';g.beginPath();g.moveTo(cx-ww/2,py(.6));g.lineTo(cx-ww/2,py(1.9));g.arc(cx,py(1.9),ww/2,Math.PI,0);g.lineTo(cx+ww/2,py(.6));g.fill();
          g.strokeStyle='rgba(230,200,160,.6)';g.lineWidth=2;g.beginPath();g.arc(cx,py(1.9),ww/2+5,Math.PI,0);g.stroke();continue;}
        if(s.stone){g.fillStyle='#3b342c';g.fillRect(cx-5,py(2.1),10,26);continue;}
        const ww=mx(s.modern?(ground?2.4:1.8):(ground?.95:1.05)),wh=s.modern?(ground?2.2:1.5):(ground?1.25:1.45),wy=ground?1.0:.85;
        // reveal and frame
        g.fillStyle=s.frame;g.fillRect(cx-ww/2-5,py(wy+wh+.12),ww+10,(wh+.22)*px);
        g.fillStyle='#262a2e';g.fillRect(cx-ww/2,py(wy+wh),ww,wh*px);
        const gr=g.createLinearGradient(0,py(wy+wh),0,py(wy));gr.addColorStop(0,'rgba(170,190,205,.35)');gr.addColorStop(1,'rgba(20,24,28,0)');g.fillStyle=gr;g.fillRect(cx-ww/2,py(wy+wh),ww,wh*px);
        g.fillStyle=s.frame;g.fillRect(cx-1.5,py(wy+wh),3,wh*px);g.fillRect(cx-ww/2,py(wy+wh*.62),ww,2.5);
        if(s.shut&&r()<.85){const open=r()<.6;g.fillStyle=s.shut;
          if(open){g.fillRect(cx-ww/2-ww*.52,py(wy+wh),ww*.48,wh*px);g.fillRect(cx+ww/2+ww*.04,py(wy+wh),ww*.48,wh*px);}
          else{g.fillRect(cx-ww/2,py(wy+wh),ww,wh*px);g.fillStyle='rgba(0,0,0,.25)';for(let k=0;k<wh*px;k+=4)g.fillRect(cx-ww/2,py(wy+wh)+k,ww,1);}
        }
        if(ground&&!s.modern){g.strokeStyle='#1f1e1c';g.lineWidth=2;for(let k=1;k<5;k++){const xx=cx-ww/2+k*ww/5;g.beginPath();g.moveTo(xx,py(wy+wh+.05));g.lineTo(xx,py(wy-.05));g.stroke();}g.beginPath();g.moveTo(cx-ww/2-3,py(wy+wh*.5));g.lineTo(cx+ww/2+3,py(wy+wh*.5));g.stroke();}
        if(!ground&&r()<s.bal){ // balcony: slab shadow and iron railing
          const bw=ww+mx(.5);g.fillStyle='rgba(40,35,30,.45)';g.fillRect(cx-bw/2,py(wy-.02),bw,5);g.fillStyle='rgba(0,0,0,.18)';g.fillRect(cx-bw/2,py(wy-.12),bw,7);
          g.strokeStyle=s.modern?'#55595c':'#1d1c1a';g.lineWidth=1.6;g.strokeRect(cx-bw/2,py(wy+.95),bw,.95*px);for(let k=0;k<bw;k+=5){g.beginPath();g.moveTo(cx-bw/2+k,py(wy+.95));g.lineTo(cx-bw/2+k,py(wy));g.stroke();}
        }else if(!s.modern){g.fillStyle='rgba(255,252,240,.8)';g.fillRect(cx-ww/2-7,py(wy-.03),ww+14,4);
          const st=g.createLinearGradient(0,py(wy-.05),0,py(wy-.9));st.addColorStop(0,'rgba(90,80,60,.16)');st.addColorStop(1,'rgba(90,80,60,0)');g.fillStyle=st;g.fillRect(cx-ww/2,py(wy-.05),ww,.85*px);}
        if(r()<.2&&!ground&&!s.modern){g.fillStyle=['#b33a3a','#c45c8a','#d8742c','#3f7a3a'][Math.floor(r()*4)];for(let k=0;k<5;k++){g.beginPath();g.arc(cx-ww/2+r()*ww,py(wy+.12)-r()*6,2.5+r()*2,0,7);g.fill();}}
      }
      // weathering
      for(let k=0;k<6;k++){const xx=x0+r()*512,gr=g.createLinearGradient(0,y,0,y+128);gr.addColorStop(0,'rgba(80,70,55,0)');gr.addColorStop(1,`rgba(80,70,55,${.04+r()*.06})`);g.fillStyle=gr;g.fillRect(xx,y,10+r()*40,128);}
    }
  });
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;t.generateMipmaps=true;t.minFilter=THREE.LinearMipmapLinearFilter;return t;
}
function tileTexture(){
  const S=512,c=document.createElement('canvas');c.width=c.height=S;const g=c.getContext('2d'),r=rng(31);
  // 2 m square: 11 channels of Arab barrel tiles across, courses of ~0.4 m up the slope
  g.fillStyle='#7b3f28';g.fillRect(0,0,S,S);
  const cw=S/11,ch=S/5;
  for(let row=0;row<5;row++)for(let k=0;k<11;k++){
    const x=k*cw,y=row*ch+(k%2)*ch*.5,hue=[[166,86,58],[150,78,52],[178,104,70],[138,74,50],[160,96,66]][Math.floor(r()*5)];
    for(const yy of [y,y-S]){const gr=g.createLinearGradient(x,0,x+cw,0);gr.addColorStop(0,`rgb(${hue[0]*.55},${hue[1]*.55},${hue[2]*.55})`);gr.addColorStop(.45,`rgb(${hue[0]},${hue[1]},${hue[2]})`);gr.addColorStop(1,`rgb(${hue[0]*.6},${hue[1]*.6},${hue[2]*.6})`);
      g.fillStyle=gr;g.fillRect(x+1,yy+2,cw-2,ch-1);g.fillStyle='rgba(30,15,8,.55)';g.fillRect(x,yy+ch-3,cw,3);}
    if(r()<.25){g.fillStyle=`rgba(${120+r()*60},${120+r()*50},${80},${.25+r()*.3})`;g.beginPath();g.arc(x+cw/2,y+r()*ch,3+r()*8,0,7);g.fill();}
  }
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;t.repeat.set(.5,.5);return t;
}
function terraceTexture(){
  const S=256,c=document.createElement('canvas');c.width=c.height=S;const g=c.getContext('2d'),r=rng(5);
  g.fillStyle='#bdb5a6';g.fillRect(0,0,S,S);
  for(let j=0;j<8;j++)for(let i=0;i<8;i++){g.fillStyle=`rgba(${r()>.5?255:60},${r()>.5?250:55},${230},${.04+r()*.06})`;g.fillRect(i*32+1,j*32+1,30,30);}
  for(let i=0;i<30;i++){g.fillStyle=`rgba(70,60,45,${.05+r()*.1})`;g.beginPath();g.ellipse(r()*S,r()*S,4+r()*18,3+r()*12,r()*3,0,7);g.fill();}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=THREE.SRGBColorSpace;t.repeat.set(1/2.6,1/2.6);return t;
}

function facadeMaterial(atlas){
  const m=new THREE.MeshStandardMaterial({vertexColors:true,roughness:.93,metalness:0});m.name='cityWall';
  m.onBeforeCompile=s=>{
    s.uniforms.uAtlas={value:atlas};
    s.vertexShader=s.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 facade;attribute float fstyle;varying vec2 vFacade;varying float vStyle;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvFacade=facade*0.01;vStyle=fstyle;');
    s.fragmentShader=s.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D uAtlas;varying vec2 vFacade;varying float vStyle;')
      .replace('#include <map_fragment>',`
      float hm=vFacade.y,um=vFacade.x;
      float row=hm<${GROUND.toFixed(2)}?1.0:0.0;
      float cv=hm<${GROUND.toFixed(2)}?clamp(hm,0.0,${GROUND.toFixed(2)})/${GROUND.toFixed(2)}:fract((hm-${GROUND.toFixed(2)})/${STOREY.toFixed(2)});
      float cu=fract(um/${CELL_W.toFixed(2)});
      float st=floor(vStyle+0.5),col=mod(st,4.0),blk=floor(st/4.0);
      vec2 auv=vec2((col+0.004+cu*0.992)/4.0,1.0-(blk*256.0+row*128.0+(1.0-cv)*126.0+1.0)/768.0);
      vec2 cont=vec2(um/${CELL_W.toFixed(2)}/4.0,hm/${STOREY.toFixed(2)}*(128.0/768.0));
      vec4 fc=textureGrad(uAtlas,auv,dFdx(cont),dFdy(cont));
      diffuseColor.rgb*=fc.rgb*mix(0.62,1.0,smoothstep(-0.4,0.9,hm));`);
  };
  m.customProgramCacheKey=()=>'city-facade';
  return m;
}

export async function loadCity(url,scene,low){
  let buf=await (await fetch(url)).arrayBuffer();const head=new Uint8Array(buf,0,2);
  if(head[0]===0x1f&&head[1]===0x8b)buf=await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const hl=new DataView(buf).getUint32(0,true),header=JSON.parse(new TextDecoder().decode(new Uint8Array(buf,4,hl))),base=4+hl;
  const wall=facadeMaterial(facadeAtlas());
  const tiles=new THREE.MeshStandardMaterial({map:tileTexture(),vertexColors:true,roughness:.88});tiles.name='cityTiles';
  const flat=new THREE.MeshStandardMaterial({map:terraceTexture(),vertexColors:true,roughness:.95});flat.name='cityFlat';
  const group=new THREE.Group();group.name='city';let triangles=0;
  for(const ch of header.chunks){
    if(low&&Math.hypot(ch.o[0],ch.o[1])>1700)continue; // phones: the nearer city only
    for(const [key,mat] of [['w',wall],['r',tiles],['f',flat]]){
      const e=ch[key];if(!e)continue;let o=base+e.off;
      const pad=n=>n+((4-n%4)%4);
      const pos=new Int16Array(buf,o,e.n*3);o+=pad(e.n*6);
      const uv=new Int16Array(buf,o,e.n*2);o+=pad(e.n*4);
      const rgba=new Uint8Array(buf,o,e.n*4);o+=pad(e.n*4);
      const idx=e.i32?new Uint32Array(buf,o,e.ni):new Uint16Array(buf,o,e.ni);
      const g=new THREE.BufferGeometry();
      g.setAttribute('position',new THREE.BufferAttribute(pos,3));
      const ib=new THREE.InterleavedBuffer(rgba,4);
      g.setAttribute('color',new THREE.InterleavedBufferAttribute(ib,3,0,true));
      if(key==='w'){g.setAttribute('facade',new THREE.BufferAttribute(uv,2));g.setAttribute('fstyle',new THREE.InterleavedBufferAttribute(ib,1,3,false));}
      else{const f=new Float32Array(e.n*2);for(let i=0;i<f.length;i++)f[i]=uv[i]/100;g.setAttribute('uv',new THREE.BufferAttribute(f,2));}
      g.setIndex(new THREE.BufferAttribute(idx,1));g.computeVertexNormals();g.computeBoundingSphere();
      const mesh=new THREE.Mesh(g,mat);mesh.position.set(ch.o[0],0,ch.o[1]);mesh.scale.setScalar(.02);mesh.receiveShadow=true;mesh.castShadow=false;
      mesh.matrixAutoUpdate=false;mesh.updateMatrix();group.add(mesh);triangles+=e.ni/3;
    }
  }
  scene.add(group);return {group,triangles};
}
