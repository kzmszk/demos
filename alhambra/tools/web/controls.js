// Camera modes: walk (Navigation, 2.3 m/s), fly (17 m/s, E/Q and ▲▼, kept inside the grounds and 0.7 m above the
// terrain), orbit (around a target: drag turns, wheel zooms).  Shift ×2.4.
// A shared/move Mover takes the keys, the drag, the wheel and the view (move-config.js); moving stays here: all three
// modes are client-only and place the camera themselves.  main.js uses keys / move (stick) / vert (▲▼) / yaw / pitch.
import { Mover, alhambraView } from '../../../shared/move/index.js';
import { terrainHeight } from './navigation.js';
import { MOVE } from './move-config.js';

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
// the orbit turns .004 rad/px; Input hands over px × drag.mouse
const ORBIT = 0.004 / MOVE.input.drag.mouse;

function travel(mv, frame, dt, walk) {
  mv.show(frame);
  const p = mv.camera.position, yaw = frame.yaw;
  let forward = frame.f, right = frame.r;
  const len = Math.max(1, Math.hypot(forward, right)); forward /= len; right /= len;
  const speed = (walk ? MOVE.walkSpeed : MOVE.flySpeed) * (frame.fast ? MOVE.fastMul : 1) * dt;
  const dx = (-Math.sin(yaw) * forward + Math.cos(yaw) * right) * speed, dz = (-Math.cos(yaw) * forward - Math.sin(yaw) * right) * speed;
  if (walk) { if (dx || dz) mv.nav.move(p, dx, dz); return; }
  const b = MOVE.flyBox;
  p.x = clamp(p.x + dx, b.x[0], b.x[1]); p.z = clamp(p.z + dz, b.z[0], b.z[1]);
  p.y += frame.u * speed; p.y = clamp(p.y, terrainHeight(p.x, p.z) + b.aboveGround, b.top);
}

const noScroll = (e) => e.preventDefault();

export class Controls extends Mover {
  // o: { mode, nav, orb (THREE.Spherical), orbitTarget, stopTour(), ignore(e), win? }
  constructor(camera, dom, { mode, nav, orb, orbitTarget, stopTour, ignore, win }) {
    const orbit = {
      update(mv) { camera.position.setFromSpherical(orb).add(orbitTarget); camera.lookAt(orbitTarget); mv.orientation(); },
      look(dx, dy) { orb.theta -= dx * ORBIT; orb.phi = clamp(orb.phi + dy * ORBIT, 0.12, 1.55); },
      wheel(e) { e.preventDefault(); stopTour(); orb.radius = clamp(orb.radius * Math.exp(e.deltaY * 0.001), 30, 1200); },
    };
    super({
      view: alhambraView(camera), dom, win, mode, input: { ...MOVE.input, ignore },
      modes: {
        walk: { update: (mv, f, dt) => travel(mv, f, dt, true), wheel: noScroll },
        fly: { update: (mv, f, dt) => travel(mv, f, dt, false), wheel: noScroll },
        orbit,
      },
      onUserInput: (kind) => { stopTour(); if (kind === 'pointerdown') dom.focus(); },
    });
    this.camera = camera; this.nav = nav;
    this.shown = { yaw: this.yaw, pitch: this.pitch };
  }

  // after something placed the camera (lookAt): take yaw / pitch from it
  orientation() {
    this.camera.rotation.reorder('YXZ');
    this.syncFromCamera();
    this.shown.yaw = this.yaw; this.shown.pitch = this.pitch;
  }

  // the camera turns only when a drag changed the view (before, the drag handler set the rotation and nothing else did)
  show(frame) {
    const s = this.shown;
    if (frame.yaw === s.yaw && frame.pitch === s.pitch) return;
    s.yaw = frame.yaw; s.pitch = frame.pitch;
    this.view.apply({ pos: this.camera.position, yaw: frame.yaw, pitch: frame.pitch });
  }
}
