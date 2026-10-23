import * as THREE from 'three';
import { random } from './materials.js';
import { terrainHeight, insidePolygon } from './navigation.js';
import { room } from './palaces.js';
import { segment, stairs } from './heroes/common.js';
import { plant, CYPRESS } from './trees.js';

export function exterior(b,ctx,low=false){
  const rand=random(9001);
  b.zone='landscape';
  // Level palace platform traced from the OSM perimeter, above the wooded slope.
  const boundary=ctx.perimeter;
  const shape=new THREE.Shape();boundary.forEach(([x,z],i)=>i?shape.lineTo(x,-z):shape.moveTo(x,-z));shape.closePath();const platform=new THREE.ShapeGeometry(shape);platform.rotateX(-Math.PI/2);// Compacted gravel (albero) between the monuments, drawn behind every modelled surface.
  if(b.m.grdGravel&&!b.m.platform){const m=b.m.grdGravel.clone();m.onBeforeCompile=b.m.grdGravel.onBeforeCompile;m.customProgramCacheKey=b.m.grdGravel.customProgramCacheKey;m.polygonOffset=true;m.polygonOffsetFactor=2;m.polygonOffsetUnits=8;m.name='platform';b.m.platform=m;}
  b.unique(platform,b.m.platform?'platform':'earth',[0,-.06,0]);
  return null;
}
