import * as THREE from 'three';
import {canvas,atlas,make} from './detail-materials.js';
import {random} from './materials.js';

// Sources already included in the reference gallery. These are material studies,
// not rectified surveys: see texture-credits.html for attribution and limitations.
export async function extendedMaterials(M){
 const files=['mexuar-tiles','lindaraja-windows','myrtles-ornament','kings-painting','lindaraja-ceiling'];
 const images=await Promise.all(files.map(async f=>{const i=new Image();i.src=`photos/${f}.webp`;await i.decode();return i;}));
 make(M,'mexuarTile',atlas(images[0],[.01,.15,.98,.70]),3.1,1.35,{rough:.48,relief:.0015,ambient:.65});
 make(M,'lindarajaTile',atlas(images[1],[.24,.75,.49,.08]),1.35,.30,{rough:.48,relief:.001,ambient:.65});
 make(M,'carvedDoor',atlas(images[2],[.17,.44,.50,.52]),1.7,2.5,{rough:.83,relief:.012,ambient:.6});
 make(M,'kingsPainting',atlas(images[3],[.015,.245,.97,.64]),1,1,{rough:.94,relief:0,ambient:.80});
 const glass=make(M,'lindarajaGlass',atlas(images[4],[.31,.425,.37,.34]),1,1,{rough:.4,relief:0,ambient:.85});glass.emissive.set(0xffffff);glass.emissiveMap=glass.map;glass.emissiveIntensity=.26;
 // Abencerrajes dado: 16th-century Sevillian cuerda-seca azulejos, derived from R Prazeres' frontal
 // photograph by tools/abencerrajes_tiles.py (4 x 2 square pattern units of about 28 cm, lighting falloff
 // flattened). The border is the blue fillet and narrow frieze above the field.
 const load=async f=>{const i=new Image();i.src=`textures/${f}.jpg`;await i.decode();return i;};
 const [dado,dadoBorder,stucco]=await Promise.all([load('abencerrajes-dado'),load('abencerrajes-border'),load('abencerrajes-stucco')]);
 make(M,'abenTile',atlas(dado,[0,0,1,1]),1.12,.56,{rough:.34,relief:.0015,ambient:.65});
 make(M,'abenTileBorder',atlas(dadoBorder,[0,0,1,1]),.56,.18,{rough:.38,relief:.001,ambient:.65});
 // Upper walls: the room's rosette / blue-cross stucco lattice (Jebulon, public domain), two units of ~78 cm.
 make(M,'abenStucco',atlas(stucco,[0,0,1,1]),1.56,1.56,{relief:.022,rough:.9,ambient:.72});
 // Vault cells: chalk-white plaster lit by the drum windows, with faded blue paint on some cells
 // (José Luis Filpo Cabana's view from below). Per-cell colour, no photo patch repeated on every cell.
 for(const [name,col] of [['abenCell',0xf4ecdc],['abenCellShade',0xe0d3bb],['abenCellBlue',0x93a2c8]]){const m=new THREE.MeshStandardMaterial({color:col,roughness:.94,vertexColors:true,side:THREE.DoubleSide});m.name=name;m.userData={scale:1,interiorAmbient:.9};M[name]=m;}
 M.abenPlaster=M.abenCell.clone();M.abenPlaster.name='abenPlaster';M.abenPlaster.vertexColors=false;M.abenPlaster.color.set(0xd9ccb4);
 // Two Sisters vault: warm ivory plaster, deeper ochre in the recessed cells, faint green-turquoise paint
 // traces (R Prazeres' view of the vault from below, already in the reference gallery).
 for(const [name,col] of [['sisCell',0xf2e6d0],['sisCellShade',0xd6c2a0],['sisCellGreen',0xa9bfae]]){const m=M.abenCell.clone();m.name=name;m.color.set(col);M[name]=m;}
 M.sisPlaster=M.abenPlaster.clone();M.sisPlaster.name='sisPlaster';M.sisPlaster.color.set(0xd8c7a8);M.sisRecess=M.sisPlaster.clone();M.sisRecess.name='sisRecess';M.sisRecess.color.set(0xa48b68);
 M.sisStucco=M.fineStucco.clone();M.sisStucco.name='sisStucco';M.sisStucco.color.set(0xf6e7cc);M.sisStucco.userData={...M.fineStucco.userData,interiorAmbient:.6};
 // Two Sisters sebka: the carved lattice of the lower wall panels (R Prazeres' hall photograph), ~2 m
 // per crop, mirrored at the edges. Strong bump: the lattice stands proud of its ground by a few cm.
 const sebka=await load('sisters-sebka');const sm=make(M,'sisSebka',atlas(sebka,[0,0,1,1]),2.0,2.12,{relief:.045,rough:.9,ambient:.6});
 sm.map.wrapS=sm.map.wrapT=sm.bumpMap.wrapS=sm.bumpMap.wrapT=THREE.MirroredRepeatWrapping;
 M.sisTrim=M.sisStucco.clone();M.sisTrim.name='sisTrim';M.sisTrim.color.set(0xfff0d4);M.sisTrim.map=M.sisStucco.map.clone();M.sisTrim.map.repeat.set(4,4);M.sisTrim.userData={...M.sisStucco.userData,interiorAmbient:.75};
 // Other Nasrid surfaces use the photographed courtyard foliage as an analogue;
 // retain the two room-specific reconstructions and their original material scale.
 M.plaster=M.fineStucco.clone();M.plaster.name='plaster';M.plaster.userData.interiorAmbient=.65;
 M.frieze=M.sEpigraphy.clone();M.frieze.name='frieze';M.frieze.userData.interiorAmbient=.65;
 M.tile=M.cTile.clone();M.tile.name='tile';M.tile.userData.interiorAmbient=.65;
 M.tileRibbon=M.sTile.clone();M.tileRibbon.name='tileRibbon';M.tileRibbon.userData.interiorAmbient=.65;
 const r=random(2901),c=canvas(1024,1024),g=c.getContext('2d');
 // Weathered rammed earth: broad lime patches, lift joints and aggregate, not a
 // uniformly repeated modern brick grid. Noise wraps at the atlas boundaries.
 g.fillStyle='#b59576';g.fillRect(0,0,1024,1024);
 for(let i=0;i<600;i++){const x=r()*1024,y=r()*1024,rad=8+r()*95;for(const dx of [-1024,0,1024])for(const dy of [-1024,0,1024]){const q=g.createRadialGradient(x+dx,y+dy,0,x+dx,y+dy,rad);q.addColorStop(0,i%3?'#eee1c321':'#5b42251d');q.addColorStop(1,'#b5957600');g.fillStyle=q;g.fillRect(x+dx-rad,y+dy-rad,rad*2,rad*2);}}
 for(let y=0;y<1024;y+=128){g.fillStyle='#5a3d2216';g.fillRect(0,y,1024,2);for(let x=35;x<1024;x+=190){g.fillStyle='#58433260';g.fillRect(x,y+58,8,6);}}
 for(let i=0;i<120000;i++){g.fillStyle=r()>.5?'#ffefd22a':'#3a281e26';g.fillRect(r()*1024,r()*1024,1+r()*2,1+r()*2);}
 make(M,'redwall',c,7,7,{relief:.018,rough:1,ambient:1});
 for(const [name,col] of [['leaf',0x53683b],['leafLight',0x71804b],['leafDark',0x33452d]]){M[name]=new THREE.MeshStandardMaterial({color:col,roughness:.94,side:THREE.DoubleSide});M[name].name=name;M[name].userData.scale=1;}
 M.hedge.color.set(0xb3b28c);M.tree.color.set(0xa3aa86);M.cypress.color.set(0x8c9c79);
 M.water.color.set(0x527b70);M.water.roughness=.12;M.water.metalness=.05;
 M.jet.opacity=.28;
 const lime=canvas(512,512),lg=lime.getContext('2d'),lr=random(382);lg.fillStyle='#f3f0e8';lg.fillRect(0,0,512,512);for(let i=0;i<24000;i++){lg.fillStyle=lr()>.5?'#ffffff0a':'#81766208';lg.fillRect(lr()*512,lr()*512,1,1);}make(M,'whiteLime',lime,2,2,{rough:.95,relief:.002,ambient:1});
 M.archBrick=M.brick.clone();M.archBrick.name='archBrick';M.archBrick.color.set(0xf1cdb6);
 M.plainTimber=new THREE.MeshStandardMaterial({color:0x493527,roughness:.91});M.plainTimber.name='plainTimber';M.plainTimber.userData.scale=1;

 const rubble=canvas(1024,1024),rg=rubble.getContext('2d'),rr=random(982);rg.fillStyle='#a59b83';rg.fillRect(0,0,1024,1024);
 for(let row=0;row<12;row++)for(let col=-1;col<9;col++){const x=col*128+(row%2)*64,y=row*85.333,ww=104+rr()*17,hh=61+rr()*16;rg.fillStyle=`hsl(${26+rr()*12} ${10+rr()*12}% ${42+rr()*22}%)`;rg.beginPath();for(const [i,[u,v]] of [[.08,.1],[.85,0],[1,.2],[.93,.85],[.6,1],[.04,.8],[0,.4]].entries()){const px=x+u*ww+rr()*4,py=y+v*hh+rr()*4;i?rg.lineTo(px,py):rg.moveTo(px,py);}rg.closePath();rg.fill();rg.strokeStyle='#665c4640';rg.lineWidth=3;rg.stroke();}
 for(let i=0;i<90000;i++){rg.fillStyle=rr()>.5?'#fff5dd28':'#352e2428';rg.fillRect(rr()*1024,rr()*1024,1+rr()*3,1+rr()*2);}make(M,'rubble',rubble,3.2,3.2,{relief:.045,rough:1,ambient:1});

}
