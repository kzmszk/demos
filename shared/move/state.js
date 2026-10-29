// Core: the plain-data shapes (proposal §3.2).
//   MoverState  { v, mode, pos:{x,y,z}, yaw, pitch, vel:Vec3, speed, walk:{z:number|null, bob}, status:'ok'|'hold' }
//   InputFrame  { f, r, u, fast, yaw, pitch }   composed axes and this step's absolute view
//   Command     { type:'setMode', name } | { type:'setSpeed', value } | { type:'place', pos, yaw?, pitch?, walkZ? }
// A replayable tick is { dt, cmds:[...], frame }: apply cmds in order with command(), then step() (frame null =
// the controls were disabled and no step ran).
import { Vec3 } from './vec.js';

export const MOVE_SCHEMA = 1;

export function createState({ mode = 'fly', pos = { x: 0, y: 0, z: 0 }, yaw = 0, pitch = 0, speed = 1 } = {}) {
  return { v: MOVE_SCHEMA, mode, pos: { x: pos.x, y: pos.y, z: pos.z }, yaw, pitch, vel: new Vec3(), speed,
    walk: { z: null, bob: 0 }, status: 'ok' };
}

export function toPlain(s) {
  return { v: s.v, mode: s.mode, pos: { x: s.pos.x, y: s.pos.y, z: s.pos.z }, yaw: s.yaw, pitch: s.pitch,
    vel: { x: s.vel.x, y: s.vel.y, z: s.vel.z }, speed: s.speed, walk: { z: s.walk.z, bob: s.walk.bob }, status: s.status };
}

const num = (v, what) => {
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new Error(`shared/move: ${what} must be a finite number (got ${v})`);
  return v;
};
export const vec3Plain = (o, what) => {
  if (!o || typeof o !== 'object') throw new Error(`shared/move: ${what} must be {x, y, z}`);
  return { x: num(o.x, what + '.x'), y: num(o.y, what + '.y'), z: num(o.z, what + '.z') };
};

// Checks shape and values; the only null accepted is the intentional walk.z = null.  Always go through this after
// JSON or structured clone (neither keeps Vec3's methods; JSON also turns NaN/Infinity into null).
export function fromPlain(o) {
  if (!o || typeof o !== 'object') throw new Error('shared/move: state must be an object');
  if (o.v !== MOVE_SCHEMA) throw new Error(`shared/move: state schema ${o.v}, expected ${MOVE_SCHEMA}`);
  if (typeof o.mode !== 'string') throw new Error('shared/move: mode must be a string');
  if (o.status !== 'ok' && o.status !== 'hold') throw new Error(`shared/move: bad status ${o.status}`);
  if (!o.walk || typeof o.walk !== 'object') throw new Error('shared/move: walk must be an object');
  const p = vec3Plain(o.pos, 'pos'), v = vec3Plain(o.vel, 'vel');
  return { v: MOVE_SCHEMA, mode: o.mode, pos: p, yaw: num(o.yaw, 'yaw'), pitch: num(o.pitch, 'pitch'),
    vel: new Vec3(v.x, v.y, v.z), speed: num(o.speed, 'speed'),
    walk: { z: o.walk.z === null ? null : num(o.walk.z, 'walk.z'), bob: num(o.walk.bob, 'walk.bob') }, status: o.status };
}
