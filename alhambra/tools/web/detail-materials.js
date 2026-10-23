import * as THREE from 'three';
import {random} from './materials.js';

// Photographic sources and licenses are kept next to the Commons-supplied JPEG renditions.
// Sampling rectangles are normalized source coordinates; the canvas is a runtime
// material atlas, not a claim that the photographs are measured displacement scans.
export function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function texture(c,color=true){const t=new THREE.CanvasTexture(c);t.colorSpace=color?THREE.SRGBColorSpace:THREE.NoColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.anisotropy=16;return t;}
export function atlas(image,rect){const [x,y,w,h]=rect,ow=Math.min(2048,Math.round(image.width*w)),oh=Math.min(2048,Math.round(image.height*h));const c=canvas(ow,oh);c.getContext('2d').drawImage(image,x*image.width,y*image.height,w*image.width,h*image.height,0,0,ow,oh);return c;}
export function make(M,name,c,w,h,{relief=.025,rough=.9,ambient=.42,color=0xffffff}={}){
 const m=new THREE.MeshStandardMaterial({color,roughness:rough,side:THREE.DoubleSide});m.name=name;m.userData={scale:1,interiorAmbient:ambient};
 m.map=texture(c);m.map.repeat.set(1/w,1/h);
 // Fine relief follows the carved light/dark recesses. It is deliberately modest:
 // a single photograph cannot recover metric depth or remove every baked shadow.
 if(relief){m.bumpMap=texture(c,false);m.bumpMap.repeat.copy(m.map.repeat);m.bumpScale=relief;}
 M[name]=m;return m;
}
function floor(){const c=canvas(1024,1024),g=c.getContext('2d'),r=random(89);g.fillStyle='#66584a';g.fillRect(0,0,1024,1024);for(let y=0;y<16;y++)for(let x=-1;x<9;x++){g.fillStyle=`hsl(${22+r()*6} 27% ${37+r()*11}%)`;g.fillRect(x*128+(y%2)*64+2,y*64+2,124,60);}for(let i=0;i<80000;i++){g.fillStyle=r()>.5?'#ffffff0d':'#24180812';g.fillRect(r()*1024,r()*1024,2,1);}return c;}
export async function detailMaterials(M){
 const files=['comares_tiles-2','comares_tiles-3','sisters_tiles-5','sisters_tiles-7','comares_ceiling-4','stucco_detail-5'];
 const images=await Promise.all(files.map(async f=>{const i=new Image();i.src=`textures/${f}.jpg`;await i.decode();return i;}));
 const photo=(name,n,rect,w,h,options)=>make(M,name,atlas(images[n],rect),w,h,options);
 photo('cEpigraphy',0,[.165,.155,.70,.17],2.2,.44);
 photo('cCarving',0,[.02,.35,.95,.43],3.6,1.45);
 photo('cTile',1,[.17,.09,.66,.73],1.15,.85,{rough:.47,relief:.0015});
 photo('sTile',2,[.015,.115,.97,.875],2.15,1.45,{rough:.43,relief:.0015});
 photo('sBorder',2,[.03,.005,.94,.11],2.1,.19,{rough:.48,relief:.001});
 photo('sEpigraphy',3,[.115,.18,.86,.15],2.8,.46,{color:0xeee9df});
 photo('sCarving',3,[.20,.35,.74,.40],3.1,1.1,{color:0xeee9df});
 photo('sRibbon',3,[.12,.10,.87,.062],2,.16);
 photo('cedar',4,[.05,.05,.9,.9],3.8,2.6,{rough:.78,relief:.009,ambient:.72});
 const foliage=atlas(images[5],[.01,.01,.98,.98]),fg=foliage.getContext('2d'),fd=fg.getImageData(0,0,foliage.width,foliage.height);for(let i=0;i<fd.data.length;i+=4){const l=fd.data[i]*.30+fd.data[i+1]*.59+fd.data[i+2]*.11;fd.data[i]=Math.min(255,(l-140)*1.35+165);fd.data[i+1]=Math.min(255,(l-140)*1.32+160);fd.data[i+2]=Math.min(255,(l-140)*1.25+149);}fg.putImageData(fd,0,0);make(M,'fineStucco',foliage,1.85,1.85,{relief:.018,ambient:.38});
 make(M,'terracotta',floor(),3.2,3.2,{relief:.007,rough:.86,ambient:.6});
 for(const [name,color,ambient] of [['sLime',0xe0d9ca,.38],['cLime',0xc8b79a,.38],['niche',0xd6c9b4,.40],['recess',0x76644d,.40],['screen',0x90816a,.55]]){const m=new THREE.MeshStandardMaterial({color,roughness:.92,side:THREE.DoubleSide});m.name=name;m.userData={scale:1,interiorAmbient:ambient};M[name]=m;}
 // Hall of the Ambassadors: golden, deeper relief (bump scaled up), warmer indirect light.
 const warm=(src,name,col,relief,ambient)=>{const m=M[src].clone();m.name=name;m.color.set(col);if(m.bumpMap)m.bumpScale=(M[src].bumpScale||.02)*relief;m.roughness=Math.min(1,m.roughness*.92);m.userData={...M[src].userData,interiorAmbient:ambient};M[name]=m;};
 warm('fineStucco','ambStucco',0xffdca6,3.2,.78);warm('cCarving','ambCarving',0xffe0a6,3.0,.78);warm('cEpigraphy','ambEpigraphy',0xffdeaa,2.6,.78);
 warm('cLime','ambLime',0xe9c08a,1,.6);warm('sBorder','ambBorder',0xf0d6a8,1,.6);
 M.nicheCell=M.fineStucco.clone();M.nicheCell.name='nicheCell';M.nicheCell.vertexColors=true;M.nicheCell.map=M.fineStucco.map.clone();M.nicheCell.map.repeat.set(.23,.23);M.nicheCell.map.offset.set(.10,.10);M.nicheCell.bumpMap=null;M.nicheCell.color.set(0xeee7d8);
}
// Preserve CSM's hook. Attenuate indirect light only, keeping the sun and the
// window lights directional instead of washing out every relief with ambient.
export function interiorShading(m){if(m.userData.interiorAmbient===undefined)return;const prior=m.onBeforeCompile;
 m.onBeforeCompile=function(s,...args){prior.call(this,s,...args);s.fragmentShader=s.fragmentShader.replace('#include <lights_fragment_end>',`#include <lights_fragment_end>\nreflectedLight.indirectDiffuse *= ${m.userData.interiorAmbient.toFixed(3)};`);};
 m.customProgramCacheKey=()=>`interior-${m.userData.interiorAmbient}`;
}
