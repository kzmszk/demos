// Core (no DOM, three, time or randomness): a small Vec3 and the horizontal axes of each city's yaw convention.
// three's Vector3 is not used because shared/ cannot resolve a city's node_modules (proposal §3.1).
export class Vec3 {
  constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  lengthSq() { return this.x * this.x + this.y * this.y + this.z * this.z; }
  // same operation order as three's Vector3.lerp, so a migrated city integrates exactly as before
  lerp(v, a) { this.x += (v.x - this.x) * a; this.y += (v.y - this.y) * a; this.z += (v.z - this.z) * a; return this; }
}

// forward / right as [a, b] in the horizontal plane, and which components those are.  Both conventions turn left
// as yaw grows.  zUp: venice / kyoto / vatican, plane (x, y), up z.
export const AXES = {
  zUp: {
    plane: ['x', 'y'], up: 'z',
    forward: (yaw) => [Math.cos(yaw), Math.sin(yaw)],
    right: (yaw) => [Math.sin(yaw), -Math.cos(yaw)],
  },
};

export function axesOf(name) {
  const a = AXES[name];
  if (!a) throw new Error(`shared/move: unknown axes '${name}'`);
  return a;
}
