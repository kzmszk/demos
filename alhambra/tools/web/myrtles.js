// Side elevations inferred from the bundled current photograph. Extra doors
// represent closed chambers; the established east/west walking passages stay open.
export function myrtlesSide(b,s){
 const x=1.5+s*11.75,rot=Math.PI/2,face=x-s*.42;
 const doors=s>0?[[-14,1.25],[-8,1.35],[0,1.65],[12,3],[15.4,1.3]]:[[-14,1.3],[-7,1.3],[0,3],[12,1.5],[15,1.3]];
 let prev=-19;
 for(const [z,w] of doors){const end=z-w/2;if(end>prev)b.wall(x,(prev+end)/2,end-prev,8.4,.75,0,'whiteLime',rot,0,null);b.arch(x,z,w,2.1,w*.52,8.4,.75,'whiteLime',rot,0,false);prev=z+w/2;
  const open=(s>0&&z===12)||(s<0&&z===0);
  if(!open)b.box(x+s*.12,0,z,.12,2.1+w*.52,w,'carvedDoor',0,true);
  // Thin carved rectangular surround; the opening remains empty through it.
  const top=2.1+w*.52+.35;
  for(const sign of [-1,1])b.box(face,0,z+sign*(w/2+.14),.07,top,.24,'fineStucco');
  b.box(face,top-.27,z,.07,.27,w+.52,'cEpigraphy');
  b.arch(face,z,w,2.1,w*.52,top-.27,.06,'fineStucco',rot,0,false);
 }
 if(prev<19)b.wall(x,(prev+19)/2,19-prev,8.4,.75,0,'whiteLime',rot,0,null);
 // Paired arched lattice windows sit high under the long eaves.
 for(const z of [-14,-7,0,13.3]){
  b.box(face-s*.025,6.20,z,.045,1.85,2.05,'fineStucco');
  for(const dz of [-.47,.47]){
   const xx=face-s*.06,zz=z+dz;
   b.box(xx,6.37,zz,.035,1.40,.78,'plainTimber');
   b.arch(xx-s*.025,zz,.78,.98,.39,1.5,.035,'fineStucco',rot,6.37,false);
   for(let k=0;k<5;k++)b.box(xx-s*.05,6.4,zz-.31+k*.155,.035,1.20,.025,'screen');
   for(let k=0;k<8;k++)b.box(xx-s*.06,6.4+k*.15,zz,.035,.025,.72,'screen');
  }
  b.box(face-s*.07,6.18,z,.14,.08,2.13,'sLime');
 }
 b.box(face,8.12,0,.09,.19,38,'cEpigraphy');
 for(let z=-18.8;z<19;z+=.42)b.box(x-s*.35,8.31,z,1.05,.13,.09,'plainTimber');
 b.roof(1.5+s*12.9,0,4,39,8.4,1.8);
}
