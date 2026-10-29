// A deterministic stand-in for the palace: the real Navigation (web/navigation.js) on the procedural terrain (flat at
// y=0 around the Court of the Lions; no setTerrainSampler) with a few registered shapes near the start place
// (lions, p=[27, 1.65, 25]): a wall with a doorway, a pillar, a 0.3 m step, a 0.6 m step (too high), a ramp up to a
// 3 m terrace that ends in a drop, and a raised 6 m platform (the walk-mode fallback case).
import { Navigation } from '../web/navigation.js';

export function makeNav() {
  const n = new Navigation();
  n.box(22, 17, 10, 0.5, 0, 6); n.box(34, 17, 10, 0.5, 0, 6);   // wall at z=17, doorway x 27..29
  n.box(31, 22, 0.6, 0.6, 0, 4);                                 // pillar
  n.floor(22, 28, 4, 4, 0.3);                                    // low step west of the start
  n.floor(33, 28, 4, 4, 0.6);                                    // too high
  n.ramp(28, 33, 3, 6, 0, 3); n.floor(28, 38, 3, 4, 3);          // ramp south to a terrace (drop at its end)
  n.floor(60, 60, 10, 10, 6);                                    // raised platform
  return n;
}
