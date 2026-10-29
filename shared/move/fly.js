// Core: free flight.  want = (f·forward + r·right) in the horizontal plane + u·up, scaled by speed (× fastMul),
// vel eased towards it with 1 - exp(-smooth·dt) (smooth null = vel takes want at once), then pos += vel·dt.
export function flyMode({ fastMul = 4, smooth = 4, normalizeXY = false, followPitch = false, clamp = null } = {}) {
  // kyoto's pitch-following flight comes with the kyoto migration (proposal §4.2), checked against its own trace
  if (followPitch) throw new Error('shared/move: flyMode followPitch is not implemented yet');
  return { kind: 'fly', fastMul, smooth, normalizeXY, clamp };
}

export function flyStep(state, frame, dt, world, m, axes) {
  let { f, r } = frame;
  const want = { x: 0, y: 0, z: 0 };
  if (m.normalizeXY) { const l = Math.hypot(f, r); if (l > 1) { f /= l; r /= l; } }
  const [fa, fb] = axes.forward(state.yaw), [ra, rb] = axes.right(state.yaw), [pa, pb] = axes.plane;
  const s = state.speed * (frame.fast ? m.fastMul : 1);
  want[pa] = (f * fa + r * ra) * s; want[pb] = (f * fb + r * rb) * s; want[axes.up] = frame.u * s;
  const vel = state.vel, pos = state.pos;
  if (m.smooth == null) vel.set(want.x, want.y, want.z);
  else vel.lerp(want, 1 - Math.exp(-dt * m.smooth));
  pos.x += vel.x * dt; pos.y += vel.y * dt; pos.z += vel.z * dt;
  if (m.clamp) m.clamp(pos, vel, world);
  state.status = 'ok';
}
