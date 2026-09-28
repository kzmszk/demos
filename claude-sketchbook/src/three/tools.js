// The drawing tools: my pencil (the one clipped to the cover), a fineliner and a round brush.
import * as THREE from 'three';

function hexPencil() {
  const g = new THREE.Group();
  const L = 8.6, R = 0.36; // a well-used pencil
  const lacquer = new THREE.MeshPhysicalMaterial({ color: 0x1d3b2c, roughness: 0.28, clearcoat: 0.8, clearcoatRoughness: 0.2 });
  const wood = new THREE.MeshStandardMaterial({ color: 0xd9b48a, roughness: 0.8 });
  const lead = new THREE.MeshStandardMaterial({ color: 0x2b2b30, roughness: 0.35, metalness: 0.4 });
  const gold = new THREE.MeshStandardMaterial({ color: 0xc8a45a, roughness: 0.3, metalness: 0.9 });
  const rubber = new THREE.MeshStandardMaterial({ color: 0xe28d8d, roughness: 0.9 });
  // origin = graphite point, +Y runs up the pencil to the eraser
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.075, 0.34, 12), lead);
  tip.rotation.x = Math.PI; tip.position.y = 0.17;
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.98, 0.08, 1.75, 6), wood);
  cone.position.y = 0.34 + 0.875;
  const body = new THREE.Mesh(new THREE.CylinderGeometry(R, R, L, 6), lacquer);
  body.position.y = 0.34 + 1.75 + L / 2;
  const stamp = new THREE.Mesh(new THREE.CylinderGeometry(R * 1.002, R * 1.002, 0.12, 6), gold);
  stamp.position.y = 0.34 + 1.75 + L - 2.4;
  const ferrule = new THREE.Mesh(new THREE.CylinderGeometry(R * 1.04, R * 1.04, 1.0, 20), gold);
  ferrule.position.y = 0.34 + 1.75 + L + 0.5;
  const eraser = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.96, R * 0.96, 0.75, 20), rubber);
  eraser.position.y = 0.34 + 1.75 + L + 1.0 + 0.37;
  g.add(tip, cone, body, stamp, ferrule, eraser);
  g.userData.length = 0.34 + 1.75 + L + 1.75;
  return g;
}

function fineliner() {
  const g = new THREE.Group();
  const black = new THREE.MeshStandardMaterial({ color: 0x151518, roughness: 0.45 });
  const grey = new THREE.MeshStandardMaterial({ color: 0x6d6f73, roughness: 0.5 });
  const metal = new THREE.MeshStandardMaterial({ color: 0xb8bcc2, roughness: 0.25, metalness: 0.9 });
  const nib = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.3, 8), black);
  nib.position.y = 0.15;
  const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.2, 0.8, 16), metal);
  sleeve.position.y = 0.3 + 0.4;
  const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.22, 1.4, 20), black);
  cone.position.y = 1.1 + 0.7;
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.42, 11, 20), black);
  body.position.y = 2.5 + 5.5;
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 4.2, 20), grey);
  cap.position.y = 2.5 + 11 - 1.4;
  const clip = new THREE.Mesh(new THREE.BoxGeometry(0.16, 3.4, 0.08), metal);
  clip.position.set(0.52, 2.5 + 11 - 1.6, 0);
  g.add(nib, sleeve, cone, body, cap, clip);
  g.userData.length = 13.6;
  return g;
}

function roundBrush() {
  const g = new THREE.Group();
  const handle = new THREE.MeshPhysicalMaterial({ color: 0x7a2d24, roughness: 0.3, clearcoat: 0.7 });
  const metal = new THREE.MeshStandardMaterial({ color: 0xc4c6ca, roughness: 0.25, metalness: 0.9 });
  const hair = new THREE.MeshStandardMaterial({ color: 0x3a2a1e, roughness: 0.7 });
  const paint = new THREE.MeshStandardMaterial({ color: 0x4060a0, roughness: 0.3 });
  const tipP = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.9, 16), paint);
  tipP.rotation.x = Math.PI; tipP.position.y = 0.45;
  const belly = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 12), hair);
  belly.scale.set(1, 1.9, 1); belly.position.y = 1.15;
  const ferrule = new THREE.Mesh(new THREE.CylinderGeometry(0.33, 0.3, 2.2, 20), metal);
  ferrule.position.y = 1.6 + 1.1;
  const h = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.36, 15, 20), handle);
  h.position.y = 3.8 + 7.5;
  g.add(tipP, belly, ferrule, h);
  g.userData.length = 18.8;
  g.userData.paint = paint.material || paint;
  g.userData.paintMat = tipP.material;
  return g;
}

export class Tools {
  constructor(scene) {
    this.pencil = hexPencil();
    this.pen = fineliner();
    this.brush = roundBrush();
    this.group = new THREE.Group();
    for (const t of [this.pencil, this.pen, this.brush]) {
      t.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      t.visible = false;
      this.group.add(t);
    }
    scene.add(this.group);
    this.q = new THREE.Quaternion();
    this.up = new THREE.Vector3(0, 1, 0);
    this.tmp = new THREE.Vector3();
    this.dir = new THREE.Vector3();
  }
  hide() { this.pencil.visible = this.pen.visible = this.brush.visible = false; }
  // tip: world position of the point touching the paper; axis: unit vector from the tip up the tool.
  pose(kind, tip, axis, flip = 0, spin = 0, paint = null) {
    this.hide();
    const t = kind === 'pen' ? this.pen : kind === 'brush' ? this.brush : this.pencil;
    t.visible = true;
    if (kind === 'brush' && paint) t.userData.paintMat.color.setRGB(paint[0] / 255, paint[1] / 255, paint[2] / 255, THREE.SRGBColorSpace);
    // flip swings the pencil end over end about its middle, so the eraser meets the paper
    if (t === this.pencil && flip > 0) {
      const L = t.userData.length;
      const side = this.tmp.set(axis.z, 0, -axis.x);
      if (side.lengthSq() < 1e-6) side.set(1, 0, 0);
      side.normalize();
      const q = new THREE.Quaternion().setFromAxisAngle(side, flip * Math.PI);
      this.dir.copy(axis).applyQuaternion(q);
      const mid = new THREE.Vector3().copy(tip).addScaledVector(axis, L / 2);
      t.position.copy(mid).addScaledVector(this.dir, -L / 2);
      this.q.setFromUnitVectors(this.up, this.dir);
    } else {
      t.position.copy(tip);
      this.q.setFromUnitVectors(this.up, axis);
    }
    t.quaternion.copy(this.q);
    if (spin) t.rotateY(spin);
    return t;
  }
}
