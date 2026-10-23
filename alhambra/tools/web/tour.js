// Four-second travelling shots. Offsets are metres in world X/Z, not camera pan.
// Each quadratic path is swept through the same collision model as walking.
const SHOTS={
  lions:       {via:[2,0],to:[2,-5],look:[42,3.6,16]},
  myrtles:     {via:[-3,0],to:[-7,0],look:[0,8,-24]},
  ambassadors:{via:[1.5,-1],to:[2,-3],look:[0,10,-36]},
  sisters:    {via:[1.6,0],to:[1.6,-3],look:[38,11,.4]},
  abencerrajes:{via:[-1.6,0],to:[-1.6,2.5],look:[38,10,36]},
  mexuar:     {via:[0,-3],to:[0,-7],look:[-33,5,-12]},
  kings:      {via:[0,-3],to:[0,-7],look:[59,7,16]},
  lindaraja:  {via:[.7,-1],to:[.7,-3],look:[38,2,-24]},
  alcazaba:   {via:[-4,0],to:[-10,0],look:[-218,8,18]},
  vela:       {via:[1.5,1],to:[3,0],look:[-160,4,70]},
  partal:     {via:[0,-3],to:[0,-7],look:[101,6,-18]},
  generalife: {via:[0,-4],to:[0,-9],look:[370,36,-75]},
  carlos:     {via:[3,-1],to:[5,-4],look:[-18,8,41]},
  justice:    {via:[0,-3],to:[1,-7],look:[-55,9,123]},
};
export function buildTourShots(places,nav){
  return Object.fromEntries(places.filter(p=>SHOTS[p.id]).map(p=>{
    const s=SHOTS[p.id],pos={x:p.p[0],y:p.p[1],z:p.p[2]},points=[[...p.p]];
    for(let i=1;i<=120;i++){
      const t=i/120,x=p.p[0]+2*(1-t)*t*s.via[0]+t*t*s.to[0],z=p.p[2]+2*(1-t)*t*s.via[1]+t*t*s.to[1];
      nav.move(pos,x-pos.x,z-pos.z);points.push([pos.x,pos.y,pos.z]);
    }
    return [p.id,{points,look:s.look}];
  }));
}
export function sampleTourShot(shot,p,t){
  // Gentle acceleration at the cut, with continuous travel through the shot.
  const u=t*t*(3-2*t),f=u*(shot.points.length-1),i=Math.min(shot.points.length-2,Math.floor(f)),a=f-i;
  return {position:shot.points[i].map((v,k)=>v+(shot.points[i+1][k]-v)*a),target:p.t.map((v,k)=>v+(shot.look[k]-v)*u)};
}
