// Runs inside the real browser scene through snap.mjs --verify.
(routes) => routes.map(route => {
  ALH.go(route.start);
  for(const [x,z] of route.points){
    let pos=ALH.info().position,remaining=Math.hypot(x-pos[0],z-pos[2]);
    for(let i=0;remaining>.08&&i<12000;i++){
      const dx=x-pos[0],dz=z-pos[2],step=Math.min(.11,remaining);
      const next=ALH.move(dx/remaining*step,dz/remaining*step);
      if(Math.hypot(next[0]-pos[0],next[2]-pos[2])<.00001)return {name:route.name,ok:false,target:[x,z],position:next};
      pos=next;remaining=Math.hypot(x-pos[0],z-pos[2]);
    }
    if(remaining>.12)return {name:route.name,ok:false,target:[x,z],position:pos};
  }
  const info=ALH.info(),height=info.position[1]-1.65;
  return {name:route.name,ok:!info.blocked&&(route.height===undefined||Math.abs(height-route.height)<.2),height,position:info.position};
})
