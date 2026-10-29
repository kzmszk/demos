// Core: walking on a city's walk raster (world.sample).  The common part — eased velocity, the spiral search for a
// place to stand, the eye following the ground, the bob, 'hold' while no data is loaded — with passability left to a
// strategy (walk-glide.js, walk-strict.js).  walk.z is the ground under the walker; null = look for a place to stand first.
import { glide } from './walk-glide.js';
import { strict } from './walk-strict.js';

const STRATEGIES = { glide, strict };

export function rasterWalkMode({ strategy, eye = 1.6, speed = 1.5, runSpeed = 4.2, smooth = 8, follow = 10, searchRadius = 60,
  bob = { amp: 0.012, rate: 1.15, ref: 1.4 }, pitchOnEnter = null } = {}) {
  if (!strategy || !STRATEGIES[strategy.kind]) throw new Error('shared/move: rasterWalkMode needs a strategy');
  return { kind: 'rasterWalk', strategy, eye, speed, runSpeed, smooth, follow, searchRadius, bob, pitchOnEnter };
}

function findWalkable(world, m, S, x, y) {
  if (world.sample(x, y).z === undefined) return null;
  for (let r = 0; r < m.searchRadius; r += 0.5) for (let a = 0; a < 6.283; a += 0.35 / Math.max(1, r)) {
    const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r, w = world.sample(px, py);
    if (S.accept(m.strategy, world, px, py, w)) return [px, py, w.z];
  }
  return null;
}

export function walkStep(state, frame, dt, world, m, axes) {
  const S = STRATEGIES[m.strategy.kind], g = m.strategy, p = state.pos, W = state.walk, vel = state.vel;
  if (W.z === null) {
    const w = findWalkable(world, m, S, p.x, p.y);
    if (!w) { state.status = 'hold'; return; }
    p.x = w[0]; p.y = w[1]; p.z = w[2] + m.eye; W.z = w[2];
  }
  state.status = 'ok';
  const [fa, fb] = axes.forward(state.yaw), [ra, rb] = axes.right(state.yaw);
  let wx = fa * frame.f + ra * frame.r, wy = fb * frame.f + rb * frame.r;
  const l2 = wx * wx + wy * wy;
  if (l2 > 1) { const k = 1 / Math.sqrt(l2); wx *= k; wy *= k; }
  const sp = frame.fast ? m.runSpeed : m.speed;
  vel.lerp({ x: wx * sp, y: wy * sp, z: 0 }, 1 - Math.exp(-dt * m.smooth));
  const z0 = W.z;
  S.move(g, world, p, vel, vel.x * dt, vel.y * dt, z0);
  const z = S.ground(g, world, p.x, p.y, W.z);
  if (z != null) W.z += (z - W.z) * Math.min(1, dt * m.follow);
  const v = Math.hypot(vel.x, vel.y), b = m.bob;
  if (b) {
    W.bob += dt * v * b.rate * Math.PI;
    p.z = W.z + m.eye + Math.sin(W.bob * 2) * b.amp * Math.min(1, v / b.ref);
  } else p.z = W.z + m.eye;
}
