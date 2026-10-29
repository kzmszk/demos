// Core: step(state, frame, dt, world, cfg) and command(state, cmd, world, cfg).  They read nothing but their
// arguments and write nothing but `state` (updated in place and returned; snapshot with toPlain first if needed).
//   cfg   { axes: 'zUp', modes: { fly: flyMode(…), … }, speedRange: [min, max] }   numbers and pure functions only
//   world the city's synchronous world queries (ground(x, y), sample(x, y), …), passed through to the modes
import { axesOf } from './vec.js';
import { flyStep } from './fly.js';
import { walkStep } from './raster-walk.js';
import { vec3Plain } from './state.js';

const STEPS = { fly: flyStep, rasterWalk: walkStep };

function coreMode(cfg, name) {
  const m = cfg.modes && cfg.modes[name];
  if (!m || !STEPS[m.kind]) throw new Error(`shared/move: '${name}' is not a core mode`);
  return m;
}

export function step(state, frame, dt, world, cfg) {
  const m = coreMode(cfg, state.mode);
  state.yaw = frame.yaw; state.pitch = frame.pitch;
  STEPS[m.kind](state, frame, dt, world, m, axesOf(cfg.axes));
  return state;
}

export function command(state, cmd, world, cfg) {
  switch (cmd.type) {
    case 'setMode': {
      if (typeof cmd.name !== 'string') throw new Error('shared/move: setMode needs a name');
      state.mode = cmd.name; state.vel.set(0, 0, 0); state.status = 'ok';
      const m = cfg.modes && cfg.modes[cmd.name];
      if (m && m.kind === 'rasterWalk') {
        state.walk.z = null;
        const lim = m.pitchOnEnter;
        if (lim != null) state.pitch = Math.max(-lim, Math.min(lim, state.pitch));
      }
      break;
    }
    case 'setSpeed': {
      const v = cmd.value;
      if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(`shared/move: setSpeed ${v}`);
      const [lo, hi] = cfg.speedRange || [-Infinity, Infinity];
      state.speed = Math.max(lo, Math.min(hi, v));
      break;
    }
    case 'place': {
      const p = vec3Plain(cmd.pos, 'place.pos');
      state.pos.x = p.x; state.pos.y = p.y; state.pos.z = p.z;
      if (cmd.yaw != null) state.yaw = cmd.yaw;
      if (cmd.pitch != null) state.pitch = cmd.pitch;
      if (cmd.walkZ !== undefined) {
        if (cmd.walkZ !== null && !Number.isFinite(cmd.walkZ)) throw new Error(`shared/move: place walkZ ${cmd.walkZ}`);
        state.walk.z = cmd.walkZ;
      }
      break;
    }
    default: throw new Error(`shared/move: unknown command ${cmd.type}`);
  }
  return state;
}
