// The desk, the lamp and a few things that live on the desk.
import * as THREE from 'three';
import { Rng, noise2 } from '../rng.js';

function woodCanvas(seed) {
  const W = 2048, H = 2048; // 150 × 150 cm, boards run left–right
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d', { willReadFrequently: true });
  const img = g.createImageData(W, H);
  const n1 = noise2(seed), n2 = noise2(seed + 1), n3 = noise2(seed + 2), n4 = noise2(seed + 3);
  const r = new Rng(seed);
  const plankW = 232;
  const planks = [];
  for (let p = 0; p < H / plankW + 1; p++) planks.push({ tone: r.range(-0.07, 0.07), ph: r.range(0, 50), freq: r.range(16, 26), off: r.range(0, 1), bow: r.range(0.4, 1.2), end: r.range(0.1, 0.9) * W });
  const light = [120, 80, 50], dark = [52, 32, 20];
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  for (let y = 0; y < H; y++) {
    const pi = Math.floor(y / plankW), pl = planks[pi];
    const py = (y % plankW) / plankW;
    for (let x = 0; x < W; x++) {
      // growth rings: long, slowly wandering lines with the odd cathedral arch
      const wander = (n1(x / 520 + pl.ph, pi * 3.1) - 0.5) * 2.2 * pl.bow + (n2(x / 150 + pl.ph, py * 2) - 0.5) * 0.5;
      const arch = Math.exp(-Math.pow((x - pl.end) / 380, 2)) * 0.9 * Math.pow(Math.abs(py - 0.5) * 2, 1.5);
      const ring = (py + pl.off) * pl.freq * 0.25 + wander + arch * 1.6;
      const f = ring - Math.floor(ring);
      const late = smooth(0.7, 0.9, f) * (1 - smooth(0.93, 1.0, f));
      // pores: short dark dashes along the grain
      const pore = Math.max(0, n3(x / 22, y / 0.9) - 0.62) * 2.4;
      const cloud = (n4(x / 300 + pl.ph, y / 90) - 0.5) * 0.18;
      let t = 0.72 - late * 0.55 - pore * 0.35 + cloud + pl.tone;
      t = Math.min(1, Math.max(0, t));
      const seam = py < 0.005 || py > 0.995 ? 0.35 : 1;
      const k = (y * W + x) * 4;
      img.data[k] = (dark[0] + (light[0] - dark[0]) * t) * seam;
      img.data[k + 1] = (dark[1] + (light[1] - dark[1]) * t) * seam;
      img.data[k + 2] = (dark[2] + (light[2] - dark[2]) * t) * seam;
      img.data[k + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  g.globalCompositeOperation = 'screen';
  for (let i = 0; i < 60; i++) {
    g.strokeStyle = `rgba(255,225,190,${r.range(0.02, 0.06)})`;
    g.lineWidth = r.range(0.4, 1.1);
    const x = r.range(0, W), y = r.range(0, H), a = r.range(-0.25, 0.25), L = r.range(20, 120);
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
  }
  g.globalCompositeOperation = 'multiply';
  g.strokeStyle = 'rgba(70,45,25,0.22)';
  g.lineWidth = 2;
  g.beginPath(); g.arc(W * 0.8, H * 0.28, 55, 0.4, 5.5); g.stroke();
  g.globalCompositeOperation = 'source-over';
  return c;
}

export function buildDesk(scene, anisotropy) {
  const woodTex = new THREE.CanvasTexture(woodCanvas(31));
  woodTex.colorSpace = THREE.SRGBColorSpace;
  woodTex.anisotropy = anisotropy;
  woodTex.wrapS = woodTex.wrapT = THREE.ClampToEdgeWrapping;
  const desk = new THREE.Mesh(
    new THREE.PlaneGeometry(150, 150),
    new THREE.MeshPhysicalMaterial({ map: woodTex, roughness: 0.52, clearcoat: 0.35, clearcoatRoughness: 0.35 }),
  );
  desk.rotation.x = -Math.PI / 2;
  desk.position.set(4, 0, -40);
  woodTex.repeat.set(1, 1);
  desk.receiveShadow = true;
  scene.add(desk);
  return desk;
}

export function buildLamp(scene) {
  const g = new THREE.Group();
  // an enamel dome shade, open at the bottom, and the arm leaving the frame
  const prof = [];
  for (let i = 0; i <= 16; i++) { const t = i / 16; prof.push(new THREE.Vector2(0.6 + 7.4 * Math.sin(t * Math.PI * 0.5) ** 1.3, 6 - t * 8)); }
  const shadeGeo = new THREE.LatheGeometry(prof, 48);
  const outer = new THREE.MeshPhysicalMaterial({ color: 0x1f3a33, roughness: 0.32, metalness: 0.1, clearcoat: 0.6, side: THREE.FrontSide });
  const inner = new THREE.MeshStandardMaterial({ color: 0xf2e6cf, roughness: 0.6, side: THREE.BackSide, emissive: 0xffc27a, emissiveIntensity: 1.1 });
  const shade = new THREE.Mesh(shadeGeo, outer);
  const shadeIn = new THREE.Mesh(shadeGeo, inner);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(8.0, 0.18, 8, 64), new THREE.MeshStandardMaterial({ color: 0xc9b27c, metalness: 0.8, roughness: 0.3 }));
  rim.rotation.x = Math.PI / 2; rim.position.y = -2;
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(2.4, 24, 16), new THREE.MeshBasicMaterial({ color: 0xffe1b0 }));
  bulb.position.y = -0.2;
  // a soft glow around the bulb (additive sprite drawn from a radial gradient)
  const gc = document.createElement('canvas'); gc.width = gc.height = 128;
  const gg = gc.getContext('2d');
  const gr = gg.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,220,170,0.9)'); gr.addColorStop(0.25, 'rgba(255,190,120,0.35)'); gr.addColorStop(1, 'rgba(255,170,90,0)');
  gg.fillStyle = gr; gg.fillRect(0, 0, 128, 128);
  const glowTex = new THREE.CanvasTexture(gc); glowTex.colorSpace = THREE.SRGBColorSpace;
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: 0.8 }));
  glow.scale.set(26, 26, 1);
  glow.position.y = -1.5;
  g.add(shade, shadeIn, rim, bulb, glow);
  const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 60, 12), new THREE.MeshStandardMaterial({ color: 0x1d1d1b, roughness: 0.4, metalness: 0.6 }));
  arm.position.set(-10, 26, -4); arm.rotation.z = 0.75; arm.rotation.x = -0.2;
  g.add(arm);
  const knuckle = new THREE.Mesh(new THREE.SphereGeometry(1.1, 16, 12), arm.material);
  knuckle.position.set(0, 6.4, 0);
  g.add(knuckle);
  scene.add(g);
  return { group: g, bulb };
}

export function buildMug(scene) {
  const g = new THREE.Group();
  const prof = [];
  const R = 4.2, Hh = 9.4;
  prof.push(new THREE.Vector2(0.001, 0));
  prof.push(new THREE.Vector2(R - 0.5, 0));
  prof.push(new THREE.Vector2(R - 0.1, 0.35));
  prof.push(new THREE.Vector2(R, 1.2));
  prof.push(new THREE.Vector2(R + 0.1, Hh - 0.4));
  prof.push(new THREE.Vector2(R + 0.05, Hh));
  prof.push(new THREE.Vector2(R - 0.35, Hh));
  prof.push(new THREE.Vector2(R - 0.45, Hh - 0.5));
  prof.push(new THREE.Vector2(R - 0.4, 1.0));
  prof.push(new THREE.Vector2(0.001, 0.9));
  const glaze = new THREE.MeshPhysicalMaterial({ color: 0xe9e2d3, roughness: 0.25, clearcoat: 0.8, clearcoatRoughness: 0.15 });
  const body = new THREE.Mesh(new THREE.LatheGeometry(prof, 56), glaze);
  const coffee = new THREE.Mesh(new THREE.CircleGeometry(R - 0.42, 40), new THREE.MeshPhysicalMaterial({ color: 0x2b170b, roughness: 0.08, clearcoat: 1 }));
  coffee.rotation.x = -Math.PI / 2; coffee.position.y = Hh - 1.6;
  const handle = new THREE.Mesh(new THREE.TorusGeometry(2.3, 0.45, 12, 32, Math.PI * 1.25), glaze);
  handle.position.set(R + 0.6, Hh * 0.52, 0); handle.rotation.z = -Math.PI * 0.62;
  g.add(body, coffee, handle);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  scene.add(g);
  return g;
}

export function buildEraser(scene) {
  const g = new THREE.Group();
  const block = new THREE.Mesh(new THREE.BoxGeometry(4.2, 1.1, 2.1), new THREE.MeshStandardMaterial({ color: 0xf4f1ea, roughness: 0.85 }));
  block.position.y = 0.55;
  const sleeve = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.16, 2.16), new THREE.MeshStandardMaterial({ color: 0x2f5e9e, roughness: 0.7 }));
  sleeve.position.set(0.7, 0.55, 0);
  g.add(block, sleeve);
  // crumbs
  const r = new Rng(9);
  const crumbGeo = new THREE.SphereGeometry(0.09, 6, 4);
  for (let i = 0; i < 14; i++) {
    const m = new THREE.Mesh(crumbGeo, block.material);
    m.position.set(-3 + r.range(-2, 2), 0.06, r.range(-2, 3));
    m.scale.set(r.range(1, 2.4), 0.7, r.range(0.8, 1.4));
    g.add(m);
  }
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  scene.add(g);
  return g;
}
