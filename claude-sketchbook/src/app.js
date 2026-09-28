// The whole thing: scene, book, tools, camera, and the two drivers (the film, and a person with a finger).
import * as THREE from 'three';
import { buildDesk, buildLamp, buildMug, buildEraser } from './three/desk.js';
import { Leaf, Cover, Spine, Band, penLoop, PW, PH, CW, CH, CT, T, HY, INSET, NL, LT } from './three/book.js';
import { Tools } from './three/tools.js';
import { buildBookData } from './bookdata.js';
import { buildTimeline, pageTau, leafTurn, smooth, clamp01 } from './timeline.js';
import { fbm1 } from './rng.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const lerp = (a, b, t) => a + (b - a) * t;
const DEG = Math.PI / 180;

export const SHOTS = {
  lamp: { t: [-2, 9, -8], dist: 72, elev: 13, azim: 8, roll: -1.2, fov: 32 },
  // portrait screens: swing round so the shade stands straight above the book
  lampTall: { t: [-3.5, 11, -8.5], dist: 84, elev: 12, azim: 50, roll: 0, fov: 34 },
  closed: { t: [7.8, 0.4, 0.4], dist: 62, elev: 50, azim: -5, roll: -1.0, fov: 30 },
  closedNear: { t: [7.8, 0.4, 0.6], dist: 56, elev: 52, azim: -4, roll: -0.8, fov: 30 },
  wide: { t: [0.0, 0.2, 0.8], dist: 60, elev: 60, azim: -2, roll: -0.4, fov: 30 },
  spread: { t: [0.0, 0.2, 0.5], dist: 55, elev: 66, azim: -1, roll: -0.3, fov: 30 },
  pageR: { t: [7.5, 0.3, 0.45], dist: 41.5, elev: 74, azim: 0, roll: -0.2, fov: 30 },
  pageL: { t: [-7.5, 0.3, 0.45], dist: 41.5, elev: 74, azim: 0, roll: 0.2, fov: 30 },
  blank: { t: [-5.2, 0.3, 1.2], dist: 50, elev: 67, azim: -2, roll: 0.1, fov: 30 },
  blankNear: { t: [-5.6, 0.3, 1.0], dist: 46, elev: 69, azim: -2, roll: 0.1, fov: 30 },
};

function mixShot(a, b, u) {
  return {
    t: [lerp(a.t[0], b.t[0], u), lerp(a.t[1], b.t[1], u), lerp(a.t[2], b.t[2], u)],
    dist: lerp(a.dist, b.dist, u), elev: lerp(a.elev, b.elev, u), azim: lerp(a.azim, b.azim, u), roll: lerp(a.roll, b.roll, u), fov: lerp(a.fov, b.fov, u),
  };
}

export class App {
  constructor(canvas, opts = {}) {
    this.mode = opts.mode || 'live';
    this.canvas = canvas;
    const video = this.mode === 'video';
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: video, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(video ? 1 : Math.min(2, window.devicePixelRatio || 1));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.VSMShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x070504);
    this.scene.fog = new THREE.Fog(0x070504, 90, 190);
    this.camera = new THREE.PerspectiveCamera(30, 1, 1, 600);
    this.aniso = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
    this.buildLights();
    this.data = buildBookData();
    this.buildBook();
    this.tools = new Tools(this.scene);
    this.drift = [fbm1(101, 3), fbm1(202, 3), fbm1(303, 3), fbm1(404, 3), fbm1(505, 3), fbm1(606, 3)];
    this.tmpV = V(0, 0, 0);
    this.resize(opts.width || canvas.clientWidth || 1080, opts.height || canvas.clientHeight || 1080);
  }

  buildLights() {
    const s = this.scene;
    const lampPos = V(-19, 29, -21);
    this.lamp = buildLamp(s);
    this.lamp.group.position.copy(lampPos).add(V(0, 2.2, 0));
    // point the shade's opening at the book
    const aim = V(4, 0, 3).sub(lampPos).normalize();
    this.lamp.group.quaternion.setFromUnitVectors(V(0, -1, 0), aim);
    const spot = new THREE.SpotLight(0xffd2a4, 6200, 0, 0.62, 0.72, 2);
    spot.position.copy(lampPos);
    spot.target.position.set(4, 0, 3);
    spot.castShadow = true;
    spot.shadow.mapSize.set(2048, 2048);
    spot.shadow.camera.near = 8;
    spot.shadow.camera.far = 110;
    spot.shadow.bias = -0.0004;
    spot.shadow.normalBias = 0.06;
    spot.shadow.radius = 9;
    spot.shadow.blurSamples = 16;
    s.add(spot, spot.target);
    this.spot = spot;
    const hemi = new THREE.HemisphereLight(0x5d6882, 0x24180e, 0.45);
    s.add(hemi);
    const bounce = new THREE.PointLight(0xffb27a, 90, 0, 2);
    bounce.position.set(30, 14, 30);
    s.add(bounce);
    this.desk = buildDesk(s, this.aniso);
    this.mug = buildMug(s);
    this.mug.position.set(27, 0, -9);
    this.mug.rotation.y = 0.9;
    this.eraser = buildEraser(s);
    this.eraser.position.set(-24, 0, 12);
    this.eraser.rotation.y = 0.5;
  }

  tex(canvas) {
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = this.aniso;
    t.generateMipmaps = true;
    t.minFilter = THREE.LinearMipmapLinearFilter;
    return t;
  }

  buildBook() {
    const d = this.data;
    const cloth = 0x26383a;
    this.pageTex = d.pages.map((p) => this.tex(p.canvas));
    const cv = d.covers;
    this.coverTex = { frontOut: this.tex(cv.frontOut), frontIn: this.tex(cv.frontIn), backIn: this.tex(cv.backIn), backOut: this.tex(cv.backOut) };
    // the -y faces are seen after the board swings over: turn their images round
    for (const k of ['frontIn', 'backOut']) { this.coverTex[k].center.set(0.5, 0.5); this.coverTex[k].rotation = Math.PI; }
    this.front = new Cover('front', this.coverTex.frontOut, this.coverTex.frontIn, cloth);
    this.back = new Cover('back', this.coverTex.backOut, this.coverTex.backIn, cloth);
    this.scene.add(this.front.pivot, this.back.pivot);
    const aF = new THREE.CanvasTexture(d.tear.alphaF), aB = new THREE.CanvasTexture(d.tear.alphaB);
    this.alphaTex = [aF, aB];
    this.leaves = [];
    for (let i = 0; i < NL; i++) {
      const opts = i === 2 ? { alphaF: aF, alphaB: aB, rot: 0.006, shift: 0.05 } : {};
      const leaf = new Leaf(i, this.pageTex[i * 2], this.pageTex[i * 2 + 1], opts);
      this.scene.add(leaf.group);
      this.leaves.push(leaf);
    }
    this.lampView = { value: new THREE.Vector3() };
    const lampCol = new THREE.Color(0xffd2a4).multiplyScalar(6200 * 0.1);
    for (const leaf of this.leaves) {
      const patch = (mat, other) => {
        mat.onBeforeCompile = (sh) => {
          sh.uniforms.uOther = { value: other };
          sh.uniforms.uLampView = this.lampView;
          sh.uniforms.uLampCol = { value: lampCol };
          sh.fragmentShader = sh.fragmentShader
            .replace('#include <common>', '#include <common>\nuniform sampler2D uOther;\nuniform vec3 uLampView;\nuniform vec3 uLampCol;')
            .replace('#include <opaque_fragment>', `{
              vec3 fp = -vViewPosition;
              vec3 ld = uLampView - fp;
              float dd = dot(ld, ld);
              float back = max(0.0, dot(-normal, normalize(ld)));
              vec3 other = texture2D(uOther, vec2(1.0 - vMapUv.x, vMapUv.y)).rgb;
              outgoingLight += diffuseColor.rgb * mix(vec3(1.0), other, 0.85) * uLampCol * back / dd;
            }
            #include <opaque_fragment>`);
        };
        mat.needsUpdate = true;
      };
      patch(leaf.matF, leaf.matB.map);
      patch(leaf.matB, leaf.matF.map);
    }
    this.spine = new Spine(cloth);
    this.scene.add(this.spine.mesh);
    this.band = new Band();
    this.scene.add(this.band.mesh);
    this.loop = penLoop();
    this.loop.position.set(CW / 2 + 0.42, 0.05, 0);
    this.front.mesh.add(this.loop);
    this.texVersion = this.data.pages.map(() => -1);
    this.tearVersion = 0;
  }

  resize(w, h) {
    this.W = w; this.H = h;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  // ---------- applying a state ----------
  setCamera(shot, t) {
    const c = this.camera;
    // handheld: slow drift plus a faint tremor
    const dz = this.drift;
    const dx = dz[0](t * 0.21) * 0.34 + dz[3](t * 1.3) * 0.03;
    const dy = dz[1](t * 0.17) * 0.26 + dz[4](t * 1.1) * 0.025;
    const dd = dz[2](t * 0.13) * 0.5;
    const e = shot.elev * DEG, a = shot.azim * DEG;
    const tgt = V(shot.t[0] + dz[5](t * 0.19) * 0.16, shot.t[1], shot.t[2] + dz[3](t * 0.16) * 0.16);
    const dist = shot.dist + dd;
    c.position.set(tgt.x + dist * Math.cos(e) * Math.sin(a) + dx, tgt.y + dist * Math.sin(e) + dy, tgt.z + dist * Math.cos(e) * Math.cos(a));
    c.up.set(0, 1, 0);
    c.lookAt(tgt);
    c.rotateZ((shot.roll + dz[1](t * 0.23) * 0.32) * DEG);
    if (c.fov !== shot.fov) { c.fov = shot.fov; c.updateProjectionMatrix(); }
  }

  updateLampView() { this.lampView.value.copy(this.spot.position).applyMatrix4(this.camera.matrixWorldInverse); }

  syncTextures() {
    const pages = this.data.pages;
    for (let i = 0; i < pages.length; i++) {
      const p = pages[i], tx = this.pageTex[i];
      if (p.overlay) { tx.image = p.display; tx.needsUpdate = true; this.texVersion[i] = -1; continue; }
      if (tx.image !== p.canvas) { tx.image = p.canvas; tx.needsUpdate = true; }
      if (this.texVersion[i] !== p.version) { tx.needsUpdate = true; this.texVersion[i] = p.version; }
    }
    if (this.data.tear.version !== this.tearVersion) { this.tearVersion = this.data.tear.version; for (const a of this.alphaTex) a.needsUpdate = true; }
  }

  // a point on page n (0..9) in world space, (x, y) in mm
  pageWorld(n, x, y, out) {
    const leaf = this.leaves[n >> 1];
    return leaf.pagePoint(n % 2 ? 'back' : 'front', x, y, out);
  }

  // ---------- the film ----------
  initVideo() {
    this.tl = buildTimeline(this.data.pages.slice(0, 9));
    return this.tl;
  }

  // everything at time t (seconds). Must be called with non-decreasing t.
  videoFrame(t) {
    const tl = this.tl, ev = tl.ev;
    // pages draw
    for (let i = 0; i < 9; i++) this.data.pages[i].advanceTo(pageTau(tl, i, t));
    // band, cover
    const bt = clamp01((t - ev.band[0]) / (ev.band[1] - ev.band[0]));
    const wob = bt >= 1 ? Math.exp(-(t - ev.band[1]) * 6) * Math.sin((t - ev.band[1]) * 26) * 0.35 : 0;
    this.band.set(bt, wob);
    const ct = clamp01((t - ev.cover[0]) / (ev.cover[1] - ev.cover[0]));
    const ce = ct < 1 ? 0.5 - 0.5 * Math.cos(Math.PI * ct) : 1;
    const settle = t > ev.cover[1] ? Math.exp(-(t - ev.cover[1]) * 5) * Math.sin((t - ev.cover[1]) * 17) * 0.012 : 0;
    this.front.set(Math.PI * ce - settle);
    this.back.set(0);
    // leaves
    for (let l = 0; l < NL; l++) {
      const p = leafTurn(tl, l, t);
      const e = p < 1 ? 1 - Math.pow(1 - smooth(p), 1.35) : 1;
      const turn = l < 4 ? tl.sec[l * 2 + 1].turn : tl.end.turn;
      const after = t - turn[1];
      const flutter = after > 0 && after < 1.2 ? Math.exp(-after * 4) * Math.sin(after * 18) * 0.05 : 0;
      // the first leaf lifts a breath when the cover swings past
      const breath = l === 0 && ct > 0 && ct < 1 ? Math.sin(Math.PI * ct) * 0.035 : 0;
      this.leaves[l].set(Math.min(1, e + breath), 0.34, 0.24, flutter);
    }
    this.spine.update(this.front, this.back);
    // tool
    this.videoTool(t);
    // camera
    this.setCamera(this.shotOverride || this.videoShot(t), t);
    this.syncTextures();
    this.camera.updateMatrixWorld();
    this.updateLampView();
    this.renderer.render(this.scene, this.camera);
  }

  videoShot(t) {
    const tl = this.tl, ev = tl.ev, S = SHOTS;
    const keys = [[0, S.lamp], [1.2, S.lamp], [ev.pencilOut[0] + 0.3, S.closed], [ev.band[1], S.closedNear], [ev.cover[1] - 0.4, S.wide], [tl.sec[0].s0 + 0.6, S.pageR]];
    for (let i = 1; i < 9; i++) {
      const s = tl.sec[i];
      if (s.turn) { keys.push([s.s0 - 0.2, i % 2 ? S.pageR : S.pageL]); keys.push([s.turn[0] + 0.9, S.spread]); keys.push([s.d0 + 0.3, S.pageL]); }
      else { keys.push([s.s0 - 0.25, S.pageL]); keys.push([s.d0 + 0.2, S.pageR]); }
    }
    keys.push([tl.end.s0 - 0.2, S.pageR]);
    keys.push([tl.end.turn[0] + 0.9, S.spread]);
    keys.push([tl.end.turn[1] + 1.6, S.blank]);
    keys.push([tl.total, S.blankNear]);
    let k = 0;
    while (k < keys.length - 2 && keys[k + 1][0] <= t) k++;
    const [t0, a] = keys[k], [t1, b] = keys[k + 1];
    const u = clamp01((t - t0) / Math.max(1e-3, t1 - t0));
    const shot = mixShot(a, b, 0.5 - 0.5 * Math.cos(Math.PI * u));
    // follow the pencil a little while it writes
    const f = this.follow;
    if (f) { shot.t[0] += f.x * 0.07; shot.t[2] += f.z * 0.07; }
    return shot;
  }

  // where the pencil has been over the last second and a half, averaged (so the camera doesn't twitch)
  followAt(i, t, w) {
    const pg = this.data.pages[i];
    let x = 0, z = 0;
    const n = 10;
    for (let k = 0; k < n; k++) {
      const tt = t - (k / (n - 1)) * 1.6;
      const a = pg.toolAt(pageTau(this.tl, i, tt));
      x += (a.x - 74) / 10; z += (a.y - 105) / 10;
    }
    return { x: (x / n) * w, z: (z / n) * w };
  }

  videoTool(t) {
    const tl = this.tl, ev = tl.ev;
    const L = this.tools.pencil.userData.length;
    const hover = { tip: V(19.5, 7.5, 9.5), axis: V(0.3, 0.85, 0.43).normalize() };
    // 1. in its loop on the closed book, then pulled out and lifted
    if (t < ev.pencilOut[1]) {
      const u = clamp01((t - ev.pencilOut[0]) / (ev.pencilOut[1] - ev.pencilOut[0]));
      const c0 = V(INSET + CW + 0.42, T - CT / 2 + 0.05, 0);
      const axis0 = V(0, 0, -1);
      const tip0 = c0.clone().addScaledVector(axis0, -L / 2 + 0.6);
      const slide = smooth(clamp01(u / 0.55));
      const tipS = tip0.clone().add(V(0, 0, 10.8 * slide));
      const lift = smooth(clamp01((u - 0.5) / 0.5));
      const tip = tipS.clone().lerp(hover.tip, lift);
      tip.y += Math.sin(Math.PI * lift) * 4;
      const axis = axis0.clone().lerp(hover.axis, lift).normalize();
      this.tools.pose('pencil', tip, axis);
      this.follow = null;
      return;
    }
    // 2. writing, or hovering between pages
    let pose = null;
    for (let i = 0; i < 9; i++) {
      const s = tl.sec[i];
      if (t < s.d0 - 1.1 || t > s.d1 + 1.3) continue;
      const pg = this.data.pages[i];
      const tau = pageTau(tl, i, t);
      const tl2 = pg.toolAt(tau);
      const p = this.pageWorld(i, tl2.x, tl2.y, V(0, 0, 0));
      const liftCm = (tl2.lift || 0) / 10;
      let kind = tl2.tool;
      let flip = 0;
      if (kind === 'eraser') { flip = 1; kind = 'pencil'; }
      let extra = 0;
      if (kind === 'finger' || kind === 'hand' || kind === 'none') { kind = 'pencil'; extra = 5; }
      const tip = p.clone().add(V(0, liftCm + extra + 0.02, 0));
      // approach and leave from the hover point
      const ina = smooth(clamp01((t - (s.d0 - 1.1)) / 1.0));
      const outa = smooth(clamp01((t - s.d1 - 0.2) / 1.1));
      const w = ina * (1 - outa);
      const axis = V(0.44, 0.7, 0.56).normalize();
      pose = { tip: hover.tip.clone().lerp(tip, w), axis: hover.axis.clone().lerp(axis, w).normalize(), kind, flip: flip * w, paint: tl2.op && tl2.op.rgbTip };
      this.follow = this.followAt(i, t, w);
      break;
    }
    if (!pose) {
      // the end: set the pencil down across the blank page, an offer
      const e0 = tl.end.turn[1] + 0.4;
      const u = smooth(clamp01((t - e0) / 2.2));
      const restTip = V(-12.6, CT + NL * LT + 0.36, 7.4);
      const restAxis = V(0.8, 0.0, -0.6).normalize();
      pose = { tip: hover.tip.clone().lerp(restTip, u), axis: hover.axis.clone().lerp(restAxis, u).normalize(), kind: 'pencil', flip: 0 };
      if (u > 0) pose.tip.y += Math.sin(Math.PI * u) * 3.5;
      this.follow = null;
    }
    this.tools.pose(pose.kind, pose.tip, pose.axis, pose.flip, 0, pose.paint);
  }
}

