// Coordinate frames shared with the Blender build (tools/vb/site.py, build_sistine.py, ref/rooms.json).
// World: metres, x east, y north, z up; origin = centre of the Vatican obelisk at its base.
export const DOME = [-321.5, -8.7];
export const AXIS = Math.atan2(8.7, 321.5);
export const FLOOR = 6.0;
const ca = Math.cos(AXIS), sa = Math.sin(AXIS);
/** basilica frame: u east along the axis (0 = dome axis), v north, z above the basilica floor */
export const B = (u, v, z = 0) => [DOME[0] + u * ca - v * sa, DOME[1] + u * sa + v * ca, FLOOR + z];
export const toB = (x, y) => { const dx = x - DOME[0], dy = y - DOME[1]; return [dx * ca + dy * sa, -dx * sa + dy * ca]; };
const SX0 = [-236.7, 77.25, 14.0], SXR = 0.8 * Math.PI / 180;
/** Sistine Chapel frame: x toward the entrance (east), y north, z above the chapel floor; altar wall at x = -20.1 */
export const S = (x, y, z = 0) => [SX0[0] + x * Math.cos(SXR) - y * Math.sin(SXR), SX0[1] + x * Math.sin(SXR) + y * Math.cos(SXR), SX0[2] + z];
export const toS = (X, Y, Z) => { const dx = X - SX0[0], dy = Y - SX0[1]; return [dx * Math.cos(SXR) + dy * Math.sin(SXR), -dx * Math.sin(SXR) + dy * Math.cos(SXR), Z - SX0[2]]; };
export let ROOMS = {};
export function setRooms(list) { ROOMS = {}; for (const r of list) ROOMS[r.name] = r; }
/** museum room frame */
export const R = (name, x, y, z = 0) => {
  const r = ROOMS[name]; const c = Math.cos(r.rot), s = Math.sin(r.rot);
  return [r.origin[0] + x * c - y * s, r.origin[1] + x * s + y * c, r.origin[2] + z];
};
export const toR = (r, X, Y, Z) => { const dx = X - r.origin[0], dy = Y - r.origin[1], c = Math.cos(r.rot), s = Math.sin(r.rot); return [dx * c + dy * s, -dx * s + dy * c, Z - r.origin[2]]; };
